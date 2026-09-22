"""
Smoke test do router Discord (routes/discord.py).

Foco: comportamento observavel dos endpoints — auth, rate-limits,
timing constante, respostas certas nos happy/edge paths. NAO testa
SQL real; usa mocks pra cursor MySQL e captura de emails.

Rodar (do dir server/):
    .venv\\Scripts\\pytest.exe tests/test_discord_router.py -v
"""

import os
import time
import types
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------
# Setup: monta um app FastAPI so com o router discord + fixtures
# ---------------------------------------------------------------

BOT_KEY = "test-bot-key-abcdef1234567890"
VALID_DISCORD_ID = "123456789012345678"  # 18 digitos
OTHER_DISCORD_ID = "987654321098765432"


@pytest.fixture(autouse=True)
def _env_and_state_reset(monkeypatch):
    """Cada teste comeca do zero — env, buckets de rate-limit resetados."""
    monkeypatch.setenv("DISCORD_BOT_API_KEY", BOT_KEY)
    # Reseta buckets in-memory entre testes
    import routes.discord as d
    d._challenge_hits.clear()
    d._verify_hits.clear()
    yield


@pytest.fixture
def emails_sent():
    """Captura chamadas de enviar_email."""
    sent = []
    with patch("routes.discord.enviar_email",
               side_effect=lambda **kwargs: sent.append(kwargs)):
        yield sent


@pytest.fixture
def mock_db():
    """Mocka get_db_or_404 pra devolver um cursor controlavel.

    Uso: mock_db.rows = [row1, row2, ...]  # queue de rows pra fetchone
         mock_db.lastrowid = 42
    """
    ctx = types.SimpleNamespace()
    ctx.rows_queue = []
    ctx.executed = []
    ctx.lastrowid = 1

    cursor = MagicMock()

    def execute(sql, params=None):
        ctx.executed.append((sql, params))

    def fetchone():
        return ctx.rows_queue.pop(0) if ctx.rows_queue else None

    cursor.execute = MagicMock(side_effect=execute)
    cursor.fetchone = MagicMock(side_effect=fetchone)
    cursor.lastrowid = ctx.lastrowid

    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.commit = MagicMock()
    conn.close = MagicMock()

    with patch("routes.discord.get_db_or_404", return_value=conn):
        ctx.cursor = cursor
        ctx.conn = conn
        yield ctx


@pytest.fixture
def client():
    """App minimo so com o router de discord — sem middleware, sem outros routers."""
    from routes.discord import router
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# ---------------------------------------------------------------
# Autenticacao (bot-key)
# ---------------------------------------------------------------

class TestAuth:
    def test_challenge_sem_key_retorna_401(self, client, mock_db):
        r = client.post("/api/discord/link/challenge",
                        json={"discord_id": VALID_DISCORD_ID, "email": "x@cpetecnologia.com.br"})
        assert r.status_code == 401

    def test_challenge_key_errada_retorna_401(self, client, mock_db):
        r = client.post("/api/discord/link/challenge",
                        headers={"X-Discord-Bot-Key": "chave-errada"},
                        json={"discord_id": VALID_DISCORD_ID, "email": "x@cpetecnologia.com.br"})
        assert r.status_code == 401

    def test_key_nao_configurada_retorna_503(self, client, mock_db, monkeypatch):
        monkeypatch.delenv("DISCORD_BOT_API_KEY", raising=False)
        r = client.post("/api/discord/link/challenge",
                        headers={"X-Discord-Bot-Key": "qualquer"},
                        json={"discord_id": VALID_DISCORD_ID, "email": "x@cpetecnologia.com.br"})
        assert r.status_code == 503

    def test_todos_endpoints_exigem_key(self, client, mock_db):
        endpoints = [
            ("POST", "/api/discord/link/challenge",
             {"discord_id": VALID_DISCORD_ID, "email": "x@cpetecnologia.com.br"}),
            ("POST", "/api/discord/link/verify",
             {"discord_id": VALID_DISCORD_ID, "code": "123456"}),
            ("GET",  f"/api/discord/link/{VALID_DISCORD_ID}", None),
            ("POST", f"/api/discord/link/{VALID_DISCORD_ID}/session", None),
        ]
        for method, path, body in endpoints:
            r = client.request(method, path, json=body) if body else client.request(method, path)
            assert r.status_code == 401, f"{method} {path} deveria exigir key"


# ---------------------------------------------------------------
# /challenge — anti-enumeracao, spam, rate-limit
# ---------------------------------------------------------------

class TestChallenge:
    def test_email_valido_envia_email(self, client, mock_db, emails_sent):
        mock_db.rows_queue = [
            # SELECT user
            {"id": 42, "name": "Jonathan", "email": "jonathan@cpetecnologia.com.br", "is_active": 1},
            # SELECT 1 FROM discord_link_challenges WHERE code — nao existe (None)
            None,
        ]
        r = client.post("/api/discord/link/challenge",
                        headers={"X-Discord-Bot-Key": BOT_KEY},
                        json={"discord_id": VALID_DISCORD_ID, "email": "jonathan@cpetecnologia.com.br"})
        assert r.status_code == 200
        assert r.json()["sent"] is True
        assert len(emails_sent) == 1
        assert "Código" in emails_sent[0]["assunto"]

    def test_email_inexistente_retorna_200_mas_nao_envia(self, client, mock_db, emails_sent):
        mock_db.rows_queue = [
            None,      # SELECT user — nao existe
            None,      # SELECT code check — nao colide
        ]
        r = client.post("/api/discord/link/challenge",
                        headers={"X-Discord-Bot-Key": BOT_KEY},
                        json={"discord_id": VALID_DISCORD_ID, "email": "naoexiste@cpetecnologia.com.br"})
        assert r.status_code == 200
        assert r.json()["sent"] is True   # anti-enumeracao — msg identica
        assert len(emails_sent) == 0       # mas nao spamma email

    def test_email_invalido_retorna_422(self, client, mock_db):
        r = client.post("/api/discord/link/challenge",
                        headers={"X-Discord-Bot-Key": BOT_KEY},
                        json={"discord_id": VALID_DISCORD_ID, "email": "nao-e-email"})
        assert r.status_code == 422

    def test_discord_id_com_menos_digitos_retorna_422(self, client, mock_db):
        r = client.post("/api/discord/link/challenge",
                        headers={"X-Discord-Bot-Key": BOT_KEY},
                        json={"discord_id": "12345", "email": "x@cpetecnologia.com.br"})
        assert r.status_code == 422

    def test_rate_limit_por_email(self, client, mock_db, emails_sent):
        # 4 pedidos pro mesmo email — o 4o deve estourar (limite 3/hora)
        mock_db.rows_queue = [None] * 8   # 4x (user None + code check None)
        email = "spam@cpetecnologia.com.br"
        for i in range(3):
            r = client.post("/api/discord/link/challenge",
                            headers={"X-Discord-Bot-Key": BOT_KEY},
                            json={"discord_id": VALID_DISCORD_ID, "email": email})
            assert r.status_code == 200, f"pedido {i+1} deveria passar"
        r = client.post("/api/discord/link/challenge",
                        headers={"X-Discord-Bot-Key": BOT_KEY},
                        json={"discord_id": VALID_DISCORD_ID, "email": email})
        assert r.status_code == 429


# ---------------------------------------------------------------
# /verify — codigo, hijack, rate-limit anti-brute
# ---------------------------------------------------------------

class TestVerify:
    def test_codigo_invalido_404(self, client, mock_db):
        mock_db.rows_queue = [None]     # challenge nao existe
        r = client.post("/api/discord/link/verify",
                        headers={"X-Discord-Bot-Key": BOT_KEY},
                        json={"discord_id": VALID_DISCORD_ID, "code": "999999"})
        assert r.status_code == 404

    def test_codigo_expirado_410(self, client, mock_db):
        mock_db.rows_queue = [{
            "code": "111111", "discord_id": VALID_DISCORD_ID,
            "email": "x@cpetecnologia.com.br",
            "expires_at": None, "used_at": None, "is_expired": 1,
        }]
        r = client.post("/api/discord/link/verify",
                        headers={"X-Discord-Bot-Key": BOT_KEY},
                        json={"discord_id": VALID_DISCORD_ID, "code": "111111"})
        assert r.status_code == 410
        assert "expirado" in r.json()["detail"].lower()

    def test_codigo_ja_usado_410(self, client, mock_db):
        mock_db.rows_queue = [{
            "code": "222222", "discord_id": VALID_DISCORD_ID,
            "email": "x@cpetecnologia.com.br",
            "expires_at": None,
            "used_at": "2026-09-22 10:00:00",
            "is_expired": 0,
        }]
        r = client.post("/api/discord/link/verify",
                        headers={"X-Discord-Bot-Key": BOT_KEY},
                        json={"discord_id": VALID_DISCORD_ID, "code": "222222"})
        assert r.status_code == 410

    def test_hijack_codigo_de_outro_discord_id_403(self, client, mock_db):
        # Codigo pertence a OUTHER_DISCORD_ID mas user tenta com VALID_DISCORD_ID
        mock_db.rows_queue = [{
            "code": "333333", "discord_id": OTHER_DISCORD_ID,
            "email": "x@cpetecnologia.com.br",
            "expires_at": None, "used_at": None, "is_expired": 0,
        }]
        r = client.post("/api/discord/link/verify",
                        headers={"X-Discord-Bot-Key": BOT_KEY},
                        json={"discord_id": VALID_DISCORD_ID, "code": "333333"})
        assert r.status_code == 403

    def test_codigo_valido_cria_vinculo(self, client, mock_db):
        mock_db.rows_queue = [
            {   # challenge encontrada
                "code": "444444", "discord_id": VALID_DISCORD_ID,
                "email": "jonathan@cpetecnologia.com.br",
                "expires_at": None, "used_at": None, "is_expired": 0,
            },
            {   # user resolvido
                "id": 42, "name": "Jonathan",
                "email": "jonathan@cpetecnologia.com.br",
            },
        ]
        r = client.post("/api/discord/link/verify",
                        headers={"X-Discord-Bot-Key": BOT_KEY},
                        json={"discord_id": VALID_DISCORD_ID, "code": "444444"})
        assert r.status_code == 200
        body = r.json()
        assert body["linked"] is True
        assert body["user"]["id"] == 42
        # Sanity: houve UPDATE used_at + DELETE de vinculo antigo + INSERT novo
        sqls = " ".join(s for s, _ in mock_db.executed).upper()
        assert "UPDATE DISCORD_LINK_CHALLENGES" in sqls
        assert "INSERT INTO DISCORD_LINKS" in sqls

    def test_rate_limit_por_discord_id_no_verify(self, client, mock_db):
        # 6 tentativas com codigo errado — a 6a deve estourar (limite 5)
        mock_db.rows_queue = [None] * 6
        for i in range(5):
            r = client.post("/api/discord/link/verify",
                            headers={"X-Discord-Bot-Key": BOT_KEY},
                            json={"discord_id": VALID_DISCORD_ID, "code": f"00000{i}"})
            assert r.status_code == 404, f"tentativa {i+1} deveria voltar 404 (codigo errado)"
        r = client.post("/api/discord/link/verify",
                        headers={"X-Discord-Bot-Key": BOT_KEY},
                        json={"discord_id": VALID_DISCORD_ID, "code": "000005"})
        assert r.status_code == 429


# ---------------------------------------------------------------
# /link/{id} + /session
# ---------------------------------------------------------------

class TestLinkAndSession:
    def test_get_link_inexistente_404(self, client, mock_db):
        mock_db.rows_queue = [None]
        r = client.get(f"/api/discord/link/{VALID_DISCORD_ID}",
                       headers={"X-Discord-Bot-Key": BOT_KEY})
        assert r.status_code == 404

    def test_get_link_existente_devolve_user(self, client, mock_db):
        from datetime import datetime
        mock_db.rows_queue = [{
            "discord_id": VALID_DISCORD_ID, "user_id": 42,
            "verified_at": datetime(2026, 9, 22, 10, 0, 0),
            "last_seen": None,
            "name": "Jonathan",
            "email": "jonathan@cpetecnologia.com.br",
            "role": "ADMIN",
        }]
        r = client.get(f"/api/discord/link/{VALID_DISCORD_ID}",
                       headers={"X-Discord-Bot-Key": BOT_KEY})
        assert r.status_code == 200
        body = r.json()
        assert body["user_id"] == 42
        assert body["name"] == "Jonathan"
        assert body["role"] == "ADMIN"
        assert body["verified_at"].startswith("2026-09-22")

    def test_session_emite_token(self, client, mock_db, monkeypatch):
        mock_db.rows_queue = [{
            "user_id": 42, "name": "Jonathan",
            "email": "jonathan@cpetecnologia.com.br",
        }]
        # Mock make_session_token pra evitar dependencia de APP_SECRET
        monkeypatch.setattr("routes.discord.make_session_token",
                            lambda uid: f"fake-token-uid{uid}")
        r = client.post(f"/api/discord/link/{VALID_DISCORD_ID}/session",
                        headers={"X-Discord-Bot-Key": BOT_KEY})
        assert r.status_code == 200
        body = r.json()
        assert body["user_id"] == 42
        assert body["token"] == "fake-token-uid42"
        assert body["token_type"] == "bearer"

    def test_session_user_nao_vinculado_404(self, client, mock_db):
        mock_db.rows_queue = [None]
        r = client.post(f"/api/discord/link/{VALID_DISCORD_ID}/session",
                        headers={"X-Discord-Bot-Key": BOT_KEY})
        assert r.status_code == 404


# ---------------------------------------------------------------
# Path validation (regex do Field)
# ---------------------------------------------------------------

class TestPathValidation:
    def test_get_link_path_com_letras_422(self, client, mock_db):
        r = client.get("/api/discord/link/abc123def456ghi789",
                       headers={"X-Discord-Bot-Key": BOT_KEY})
        assert r.status_code == 422

    def test_session_path_muito_curto_422(self, client, mock_db):
        r = client.post("/api/discord/link/12345/session",
                        headers={"X-Discord-Bot-Key": BOT_KEY})
        assert r.status_code == 422
