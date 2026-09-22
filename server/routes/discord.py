"""
Endpoints consumidos exclusivamente pelo bot Discord (CPEControlBot).

Todos os endpoints exigem o header X-Discord-Bot-Key com o valor de
DISCORD_BOT_API_KEY (.env). Sem essa key, retorna 401 — nao ha outra
forma de authenticar aqui, esses endpoints nao sao pra frontend humano.

Fluxo tipico do bot:
  1. User no Discord chama /consultachamado
  2. Bot -> GET /api/discord/link/{discord_id}
       - Se 404: bot pede pra usar /vincular primeiro
       - Se 200: pega user_id, name
  3. Bot -> POST /api/discord/link/{discord_id}/session
       - Recebe session token curto (TTL padrao do sistema)
  4. Bot -> chama a API do CPE Control (ex: /api/tickets/by-numero/X)
       usando esse token no header X-Auth-Token — respeita permissoes
       do user real.
"""

import os
import json
import time
import logging
import secrets
import threading
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Header, Path, Query
from pydantic import BaseModel, EmailStr, Field

from database import get_db_or_404
from security import make_session_token
from services.email_service import enviar_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/discord", tags=["discord"])

# TTL do codigo de vinculacao (15min) — usado em SQL (INTERVAL 15 MINUTE)
CHALLENGE_TTL_MIN = 15
# Snowflake do Discord tem 17-20 digitos hoje; validacao larga.
DISCORD_ID_MIN = 17
DISCORD_ID_MAX = 20

# =========================================
# RATE LIMITS (in-memory — reset a cada restart da API)
# =========================================
# Anti-spam por email: qualquer bot-key holder poderia spamar usuarios com
# "codigo de vinculacao"; limita 3 pedidos por email por hora.
_CHALLENGE_LIMIT_PER_HOUR = 3
_CHALLENGE_WINDOW_SEC     = 3600
_challenge_hits: dict[str, list[float]] = {}
# Anti-brute-force por discord_id no /verify: 5 tentativas em 15min.
_VERIFY_LIMIT_PER_WINDOW = 5
_VERIFY_WINDOW_SEC       = 15 * 60
_verify_hits: dict[str, list[float]] = {}
_rl_lock = threading.Lock()


def _rate_limit_check(bucket: dict, key: str, limit: int, window_sec: int) -> bool:
    """Retorna True se o request pode passar; False se estourou o limite.
    Slide window simples (in-memory, sem Redis)."""
    now = time.time()
    with _rl_lock:
        hits = bucket.get(key, [])
        # Purga hits fora da janela
        hits = [t for t in hits if now - t < window_sec]
        if len(hits) >= limit:
            bucket[key] = hits
            return False
        hits.append(now)
        bucket[key] = hits
    return True


def _require_bot_key(x_discord_bot_key: Optional[str]) -> None:
    """Valida a API key do bot. Sem ela ou errada -> 401."""
    expected = os.environ.get("DISCORD_BOT_API_KEY", "")
    if not expected:
        # Fail-closed: sem key configurada, endpoints ficam desligados.
        raise HTTPException(status_code=503, detail="Bot Discord nao configurado no servidor")
    if not x_discord_bot_key:
        raise HTTPException(status_code=401, detail="Header X-Discord-Bot-Key ausente")
    # Comparacao constant-time pra evitar timing attack
    if not secrets.compare_digest(x_discord_bot_key, expected):
        logger.warning("[DISCORD] Bot API key invalida rejeitada")
        raise HTTPException(status_code=401, detail="Bot key invalida")


# _valid_discord_id() foi removido — pydantic Field(pattern) faz o mesmo
# no ChallengeBody/VerifyBody/Path e devolve 422 automatico se o formato
# nao bater. Menos codigo pra manter.


# =========================================
# MODELS
# =========================================

class ChallengeBody(BaseModel):
    discord_id: str = Field(..., pattern=r"^\d{17,20}$")
    email:      EmailStr


class VerifyBody(BaseModel):
    discord_id: str = Field(..., pattern=r"^\d{17,20}$")
    code:       str = Field(..., pattern=r"^\d{6}$")


class MarkDeliveredBody(BaseModel):
    ids:   List[int] = Field(..., min_length=1, max_length=200)
    error: Optional[str] = Field(None, max_length=255)  # se DM falhou pra esses ids


# =========================================
# ENDPOINTS
# =========================================

@router.post("/link/challenge")
async def link_challenge(
    body: ChallengeBody,
    x_discord_bot_key: Optional[str] = Header(None),
):
    """Gera codigo de vinculacao e envia por email.

    Sempre retorna 200 com `sent=True` mesmo se o email nao existir em
    users — evita enumeracao de emails validos (mesmo padrao do
    /forgot-password).
    """
    _require_bot_key(x_discord_bot_key)

    email_norm = body.email.strip().lower()

    # 2026-09-22 (review agente #HIGH): rate-limit por email — evita que
    # quem tem a bot-key spamme usuarios com "codigos de vinculacao"
    # nao solicitados. 3 tentativas por hora, in-memory (reset em restart).
    if not _rate_limit_check(_challenge_hits, email_norm,
                              _CHALLENGE_LIMIT_PER_HOUR, _CHALLENGE_WINDOW_SEC):
        logger.warning(f"[DISCORD] rate-limit challenge por email={email_norm}")
        raise HTTPException(
            status_code=429,
            detail=f"Muitos pedidos pra este email. Tente novamente em 1h.",
        )

    logger.info(f"[DISCORD] challenge solicitado discord_id={body.discord_id} email={email_norm}")

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        # 2026-09-22 (review agente #HIGH): trabalho constante — o insert +
        # geracao de codigo roda pra QUALQUER email pra igualar timing entre
        # "email existe" e "nao existe". Se nao houver user ativo, o codigo
        # e descartado e o email NAO e enviado.
        cursor.execute(
            "SELECT id, name, email, is_active FROM users WHERE LOWER(email) = %s LIMIT 1",
            (email_norm,),
        )
        user = cursor.fetchone()

        # Limpa challenges antigos deste discord_id (evita acumular lixo).
        # 2026-09-22 (review agente #MEDIUM): usa NOW() do MySQL em vez de
        # datetime.utcnow() Python — MySQL server nao esta em UTC (Brasilia).
        cursor.execute(
            "DELETE FROM discord_link_challenges "
            "WHERE discord_id = %s OR expires_at < NOW()",
            (body.discord_id,),
        )

        # Gera codigo de 6 digitos evitando colisao (raro, mas seguro)
        for _ in range(10):
            code = f"{secrets.randbelow(1_000_000):06d}"
            cursor.execute("SELECT 1 FROM discord_link_challenges WHERE code = %s", (code,))
            if not cursor.fetchone():
                break
        else:
            raise HTTPException(status_code=500, detail="Nao foi possivel gerar codigo unico")

        # expires_at via SQL (NOW() do banco, mesma referencia que o cleanup)
        cursor.execute(
            "INSERT INTO discord_link_challenges (code, discord_id, email, expires_at) "
            "VALUES (%s, %s, %s, DATE_ADD(NOW(), INTERVAL %s MINUTE))",
            (code, body.discord_id, email_norm, CHALLENGE_TTL_MIN),
        )
        conn.commit()

        # SO envia email quando ha user ativo. O trabalho SQL rodou pros dois
        # ramos entao o timing e igual; o email async em background nao afeta
        # a latencia da response.
        if user and user.get("is_active"):
            assunto = "CPE Control · Código de vinculação Discord"
            html = f"""
              <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
                <h2 style="color: #f5b342;">Vincular sua conta ao Discord</h2>
                <p>Olá, {user.get('name') or 'colaborador(a)'}!</p>
                <p>Alguém pediu pra vincular sua conta CPE Control a um usuário do Discord.
                   Se foi você, use este código no comando <code>/vincular-confirmar</code>:</p>
                <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px;
                            background: #f4f4f5; padding: 16px; text-align: center;
                            border-radius: 8px; margin: 24px 0; color: #1a1a1a;">
                  {code}
                </div>
                <p style="color: #666; font-size: 13px;">
                  O código expira em {CHALLENGE_TTL_MIN} minutos.
                  Se não foi você que solicitou, ignore este email —
                  ninguém consegue vincular sem ter acesso a esta caixa.
                </p>
              </div>
            """
            enviar_email(para=user["email"], assunto=assunto, html=html)
            logger.info(f"[DISCORD] codigo enviado user_id={user['id']} email={email_norm}")
        else:
            logger.info(f"[DISCORD] challenge pra email inexistente/inativo: {email_norm} (codigo descartado)")

        # Sempre 200 — nao expor se email existe ou nao
        return {
            "sent": True,
            "expires_in_minutes": CHALLENGE_TTL_MIN,
            "message": "Se o email estiver cadastrado, você receberá o código em instantes.",
        }
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[DISCORD] erro em challenge: {err}")
        # 2026-09-22 (review agente #LOW): nao vaza stack detail pro caller
        raise HTTPException(status_code=500, detail="Erro interno ao processar vinculacao")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@router.post("/link/verify")
async def link_verify(
    body: VerifyBody,
    x_discord_bot_key: Optional[str] = Header(None),
):
    """Consuma o codigo e cria o vinculo. Idempotente: se ja havia vinculo
    pra esse discord_id, atualiza; se ja havia pra esse user_id (bind
    UNIQUE), o insert falha e a resposta descreve o conflito."""
    _require_bot_key(x_discord_bot_key)

    # 2026-09-22 (review agente #MEDIUM): rate-limit anti-brute-force por
    # discord_id — 5 tentativas em 15min. 10^6 combos e o TTL do challenge
    # e 15min, entao esse teto tira a viabilidade estatistica do brute.
    if not _rate_limit_check(_verify_hits, body.discord_id,
                              _VERIFY_LIMIT_PER_WINDOW, _VERIFY_WINDOW_SEC):
        logger.warning(f"[DISCORD] rate-limit verify discord_id={body.discord_id}")
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas erradas. Aguarde 15 minutos ou solicite novo código.",
        )

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        # Busca challenge pelo codigo (unique pk).
        # 2026-09-22 (review agente #MEDIUM): usa NOW() do banco pra comparar
        # expires_at — evita skew de timezone com datetime.utcnow() Python.
        cursor.execute(
            "SELECT code, discord_id, email, expires_at, used_at, "
            "       (expires_at < NOW()) AS is_expired "
            "FROM discord_link_challenges WHERE code = %s LIMIT 1",
            (body.code,),
        )
        chall = cursor.fetchone()

        if not chall:
            raise HTTPException(status_code=404, detail="Código inválido")
        if chall["used_at"] is not None:
            raise HTTPException(status_code=410, detail="Código já usado")
        if chall["is_expired"]:
            raise HTTPException(status_code=410, detail="Código expirado, solicite um novo")
        if chall["discord_id"] != body.discord_id:
            # Codigo veio de outro discord_id — evita user malicioso "roubar"
            # o codigo se de alguma forma vazar (log, screenshot).
            raise HTTPException(status_code=403, detail="Código não pertence a este usuário Discord")

        # Resolve o user_id pelo email do challenge (ja normalizado no insert)
        cursor.execute(
            "SELECT id, name, email FROM users WHERE LOWER(email) = %s AND is_active = 1 LIMIT 1",
            (chall["email"],),
        )
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=410, detail="Usuário do CPE não existe mais")

        # Marca challenge como usado
        cursor.execute(
            "UPDATE discord_link_challenges SET used_at = NOW() WHERE code = %s",
            (body.code,),
        )

        # Insere ou atualiza vinculo (REPLACE por conta do UNIQUE user_id)
        # Se este user_id ja tinha outro discord_id, remove o antigo primeiro
        cursor.execute("DELETE FROM discord_links WHERE user_id = %s AND discord_id != %s",
                       (user["id"], body.discord_id))
        cursor.execute(
            "INSERT INTO discord_links (discord_id, user_id, verified_at) "
            "VALUES (%s, %s, NOW()) "
            "ON DUPLICATE KEY UPDATE user_id = VALUES(user_id), verified_at = NOW()",
            (body.discord_id, user["id"]),
        )
        conn.commit()

        logger.info(f"[DISCORD] vinculado discord_id={body.discord_id} -> user_id={user['id']}")

        return {
            "linked": True,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
            },
        }
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[DISCORD] erro em verify: {err}")
        raise HTTPException(status_code=500, detail="Erro interno ao verificar codigo")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@router.get("/link/{discord_id}")
async def get_link(
    discord_id: str = Path(..., pattern=r"^\d{17,20}$"),
    x_discord_bot_key: Optional[str] = Header(None),
):
    """Retorna quem esta vinculado a este discord_id, ou 404."""
    _require_bot_key(x_discord_bot_key)

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT l.discord_id, l.user_id, l.verified_at, l.last_seen, "
            "       u.name, u.email, u.role "
            "FROM discord_links l JOIN users u ON u.id = l.user_id "
            "WHERE l.discord_id = %s AND u.is_active = 1 LIMIT 1",
            (discord_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Discord user nao vinculado")
        # Serializa datas
        for f in ("verified_at", "last_seen"):
            if row.get(f):
                row[f] = row[f].isoformat()
        return row
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[DISCORD] erro em get_link: {err}")
        raise HTTPException(status_code=500, detail="Erro interno ao consultar vinculo")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@router.post("/link/{discord_id}/session")
async def get_session_token(
    discord_id: str = Path(..., pattern=r"^\d{17,20}$"),
    x_discord_bot_key: Optional[str] = Header(None),
):
    """Gera um session token pro bot agir em nome do user vinculado.
    Token respeita SESSION_MAX_AGE_SECONDS do sistema (padrao 12h).

    O bot deve chamar isto sob demanda (nao cachear por muito tempo) e
    usar como header X-Auth-Token nas chamadas subsequentes pra API do
    CPE Control.
    """
    _require_bot_key(x_discord_bot_key)

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT l.user_id, u.name, u.email FROM discord_links l "
            "JOIN users u ON u.id = l.user_id "
            "WHERE l.discord_id = %s AND u.is_active = 1 LIMIT 1",
            (discord_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Discord user nao vinculado")

        token = make_session_token(row["user_id"])

        # Atualiza last_seen — util pra debug "quando foi a ultima vez que o bot usou?"
        cursor.execute(
            "UPDATE discord_links SET last_seen = NOW() WHERE discord_id = %s",
            (discord_id,),
        )
        conn.commit()

        # Audit trail explicito — session emitida em nome de outro user via bot.
        # Se algum dia a bot-key vazar, os logs mostram quais discord_ids
        # pediram sessao pra quem e quando.
        logger.warning(
            f"[DISCORD-AUDIT] session_issued user_id={row['user_id']} "
            f"user_email={row['email']} discord_id={discord_id}"
        )

        return {
            "token": token,
            "user_id": row["user_id"],
            "user_name": row["name"],
            "token_type": "bearer",
        }
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[DISCORD] erro em session: {err}")
        raise HTTPException(status_code=500, detail="Erro interno ao emitir sessao")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# =========================================
# NOTIFICACOES PUSH (Fase 4 do bot Discord)
# =========================================
# Backend enfileira DMs pendentes; bot polla a cada 15s e envia.
# Chamado dos handlers de tickets.py via _notify_discord_if_linked().

_EVENT_TYPES = ("resposta", "atribuido", "status_changed", "ticket_resolvido")


def notify_discord_if_linked(
    cursor,
    user_id: int,
    event_type: str,
    ticket_id: int,
    payload: Optional[dict] = None,
) -> None:
    """Enfileira uma DM Discord SE o user esta vinculado. Silent noop se nao.

    Chamado dos handlers de tickets.py (criar_interacao, assumir, atualizar,
    finalizar). NAO deve levantar excecao — falha aqui nao pode derrubar o
    fluxo principal do backend. Usa o cursor da conexao ja aberta pra
    aproveitar a transacao em curso.

    Args:
      cursor:     mysql.connector cursor ja aberto (dictionary=True ideal)
      user_id:    ID do CPE user destinatario (ex: solicitante_id do ticket)
      event_type: 'resposta' | 'atribuido' | 'status_changed' | 'ticket_resolvido'
      ticket_id:  ID interno do ticket
      payload:    dict serializavel — dados extras pro bot montar o embed
                  (autor da msg, nome novo do responsavel, novo status label...)
    """
    if event_type not in _EVENT_TYPES:
        logger.warning(f"[DISCORD-NOTIFY] event_type invalido: {event_type}")
        return
    try:
        # 1. Checa vinculo (LIMIT 1, indexado)
        cursor.execute(
            "SELECT discord_id FROM discord_links WHERE user_id = %s LIMIT 1",
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return  # user nao vinculado — nada a fazer

        discord_id = row["discord_id"] if isinstance(row, dict) else row[0]

        # 2. Insere na fila
        payload_str = json.dumps(payload or {}, ensure_ascii=False)[:8000]
        cursor.execute(
            "INSERT INTO discord_notifications_pending "
            "(discord_id, ticket_id, event_type, payload_json) "
            "VALUES (%s, %s, %s, %s)",
            (discord_id, ticket_id, event_type, payload_str),
        )
        logger.info(
            f"[DISCORD-NOTIFY] enfileirada event={event_type} "
            f"user_id={user_id} discord_id={discord_id} ticket_id={ticket_id}"
        )
    except Exception as e:
        # NUNCA propaga — evita derrubar POST /tickets se tabela ausente etc
        logger.warning(f"[DISCORD-NOTIFY] falha silenciosa: {e}")


@router.get("/notifications/pending")
async def list_pending_notifications(
    limit: int = Query(50, ge=1, le=200),
    x_discord_bot_key: Optional[str] = Header(None),
):
    """Bot chama a cada 15s pra pegar batch de DMs pendentes.
    Retorna lista ordenada por created_at ASC (FIFO)."""
    _require_bot_key(x_discord_bot_key)

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT n.id, n.discord_id, n.ticket_id, n.event_type,
                   n.payload_json, n.created_at,
                   t.numero, t.id_alfanumerica, t.assunto, t.status_id
              FROM discord_notifications_pending n
              JOIN tickets t ON t.id = n.ticket_id
             WHERE n.delivered_at IS NULL
             ORDER BY n.created_at ASC
             LIMIT %s
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        # Serializa datas + parse do payload_json
        for r in rows:
            if r.get("created_at"):
                r["created_at"] = r["created_at"].isoformat()
            try:
                r["payload"] = json.loads(r.pop("payload_json") or "{}")
            except Exception:
                r["payload"] = {}
        return rows
    except Exception as err:
        logger.error(f"[DISCORD-NOTIFY] erro em list_pending: {err}")
        raise HTTPException(status_code=500, detail="Erro interno ao listar notificacoes")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@router.post("/notifications/mark-delivered")
async def mark_delivered(
    body: MarkDeliveredBody,
    x_discord_bot_key: Optional[str] = Header(None),
):
    """Bot chama depois de enviar (ou falhar em enviar) as DMs.
    Se `error` vier preenchido, marca todas com esse erro (bot NAO retentara
    porque delivered_at fica setado)."""
    _require_bot_key(x_discord_bot_key)

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        placeholders = ",".join(["%s"] * len(body.ids))
        params = list(body.ids)
        if body.error:
            cursor.execute(
                f"UPDATE discord_notifications_pending "
                f"SET delivered_at = NOW(), delivery_error = %s "
                f"WHERE id IN ({placeholders}) AND delivered_at IS NULL",
                [body.error[:255], *params],
            )
        else:
            cursor.execute(
                f"UPDATE discord_notifications_pending "
                f"SET delivered_at = NOW() "
                f"WHERE id IN ({placeholders}) AND delivered_at IS NULL",
                params,
            )
        conn.commit()
        return {"marked": cursor.rowcount}
    except Exception as err:
        logger.error(f"[DISCORD-NOTIFY] erro em mark_delivered: {err}")
        raise HTTPException(status_code=500, detail="Erro interno ao marcar entrega")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()
