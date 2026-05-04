"""
Router do módulo Agenda — integração com Carbonio Community Edition.

Endpoints (prefixo /api/agenda):
    POST /login      Conecta o usuário ao Carbonio (email + senha → token)
    POST /logout     Limpa o token salvo
    GET  /status     Diz se o usuário está conectado e até quando
    GET  /eventos    Lista eventos do Carbonio no intervalo (inicio, fim)

A senha do Carbonio NUNCA é armazenada — só é usada uma vez para gerar
o authToken, que é guardado criptografado em users.carbonio_token.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field

from database import get_db_or_404, convert_datetime_to_string
from services.carbonio_service import (
    autenticar,
    listar_eventos,
    criar_evento,
    obter_detalhes_evento,
    reenviar_convite,
    CarbonioError,
    CarbonioOfflineError,
)
from services.crypto_helper import encrypt_str, decrypt_str

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agenda", tags=["agenda"])


# ============================================================
# SCHEMAS
# ============================================================

class LoginPayload(BaseModel):
    usuario_id: int = Field(..., gt=0)
    email:      EmailStr
    senha:      str = Field(..., min_length=1)


class LogoutPayload(BaseModel):
    usuario_id: int = Field(..., gt=0)


class EventoCreate(BaseModel):
    usuario_id: int   = Field(..., gt=0)
    titulo:     str   = Field(..., min_length=2, max_length=200)
    inicio:     str   = Field(..., description="ISO 8601 com timezone")
    fim:        str   = Field(..., description="ISO 8601 com timezone")
    local:      Optional[str]       = Field(None, max_length=200)
    descricao:  Optional[str]       = Field(None, max_length=2000)
    convidados: Optional[list[str]] = Field(default_factory=list)
    all_day:    bool                = False


class ReenviarPayload(BaseModel):
    usuario_id:    int       = Field(..., gt=0)
    destinatarios: list[str] = Field(..., min_length=1)


# ============================================================
# HELPERS
# ============================================================

def _get_token_valido(cursor, usuario_id: int) -> str:
    """Busca o token do usuário, valida expiração e devolve em texto plano.
    Levanta HTTPException 401 se ausente/expirado."""
    cursor.execute(
        "SELECT carbonio_email, carbonio_token, carbonio_token_exp "
        "FROM users WHERE id = %s",
        (usuario_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if not row["carbonio_token"]:
        raise HTTPException(
            status_code=401,
            detail="Você ainda não conectou sua agenda Carbonio. Faça login.",
        )

    if row["carbonio_token_exp"] and row["carbonio_token_exp"] < datetime.now():
        raise HTTPException(
            status_code=401,
            detail="Sessão Carbonio expirou. Faça login novamente.",
        )

    token = decrypt_str(row["carbonio_token"])
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Token Carbonio inválido (faça login novamente).",
        )
    return token


# ============================================================
# ENDPOINTS
# ============================================================

@router.post("/login")
async def login_carbonio(payload: LoginPayload):
    """Autentica no Carbonio e guarda o token criptografado."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE id = %s", (payload.usuario_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        try:
            resultado = autenticar(payload.email, payload.senha)
        except CarbonioError as err:
            raise HTTPException(status_code=401, detail=f"Carbonio: {err}")
        except CarbonioOfflineError as err:
            raise HTTPException(status_code=502, detail=str(err))

        token_cifrado = encrypt_str(resultado["token"])
        # Margem de segurança: expira 5 min antes do tempo real
        exp = datetime.now() + timedelta(seconds=resultado["lifetime_segundos"] - 300)

        cursor.execute(
            "UPDATE users SET carbonio_email=%s, carbonio_token=%s, carbonio_token_exp=%s "
            "WHERE id=%s",
            (resultado["email"], token_cifrado, exp, payload.usuario_id),
        )
        conn.commit()

        return {
            "ok":         True,
            "email":      resultado["email"],
            "expira_em":  exp.isoformat(sep=" "),
        }
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[AGENDA/LOGIN] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao autenticar: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.post("/logout")
async def logout_carbonio(payload: LogoutPayload):
    """Limpa o token Carbonio do usuário."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "UPDATE users SET carbonio_token=NULL, carbonio_token_exp=NULL WHERE id=%s",
            (payload.usuario_id,),
        )
        conn.commit()
        return {"ok": True}
    except Exception as err:
        logger.error(f"[AGENDA/LOGOUT] {err}")
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.get("/status")
async def status_agenda(usuario_id: int = Query(..., gt=0)):
    """Diz se o usuário está conectado ao Carbonio e até quando."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT carbonio_email, carbonio_token, carbonio_token_exp "
            "FROM users WHERE id = %s",
            (usuario_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        conectado = bool(row["carbonio_token"]) and (
            not row["carbonio_token_exp"] or row["carbonio_token_exp"] > datetime.now()
        )
        return {
            "conectado": conectado,
            "email":     row["carbonio_email"],
            "expira_em": row["carbonio_token_exp"].isoformat(sep=" ") if row["carbonio_token_exp"] else None,
        }
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[AGENDA/STATUS] {err}")
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.get("/eventos")
async def eventos_agenda(
    usuario_id: int = Query(..., gt=0),
    inicio:     str = Query(..., description="ISO 8601 — ex: 2026-05-01T00:00:00"),
    fim:        str = Query(..., description="ISO 8601 — ex: 2026-05-31T23:59:59"),
):
    """Lista eventos do Carbonio no intervalo dado."""
    # Converte ISO para epoch ms (formato esperado pelo Carbonio)
    try:
        # FullCalendar manda no formato "2026-05-01T00:00:00-03:00" (com TZ)
        # ou "2026-05-01T00:00:00.000Z". datetime.fromisoformat aceita ambos no 3.11+.
        ini_dt = datetime.fromisoformat(inicio.replace("Z", "+00:00"))
        fim_dt = datetime.fromisoformat(fim.replace("Z", "+00:00"))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=f"Formato de data inválido: {err}")

    inicio_ms = int(ini_dt.timestamp() * 1000)
    fim_ms    = int(fim_dt.timestamp() * 1000)

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        token = _get_token_valido(cursor, usuario_id)

        try:
            eventos = listar_eventos(token, inicio_ms, fim_ms)
        except CarbonioError as err:
            # Se o token foi invalidado no servidor (revogado, etc), marca como expirado
            msg = str(err).lower()
            if "auth" in msg or "expir" in msg:
                cursor.execute(
                    "UPDATE users SET carbonio_token=NULL, carbonio_token_exp=NULL WHERE id=%s",
                    (usuario_id,),
                )
                conn.commit()
                raise HTTPException(status_code=401, detail="Sessão Carbonio inválida — refaça login.")
            raise HTTPException(status_code=502, detail=f"Carbonio: {err}")
        except CarbonioOfflineError as err:
            raise HTTPException(status_code=502, detail=str(err))

        return {"total": len(eventos), "eventos": eventos}
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[AGENDA/EVENTOS] {err}")
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.post("/eventos", status_code=status.HTTP_201_CREATED)
async def criar_evento_endpoint(payload: EventoCreate):
    """Cria um compromisso na agenda Carbonio do usuário."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT carbonio_email FROM users WHERE id = %s",
            (payload.usuario_id,),
        )
        row = cursor.fetchone()
        if not row or not row.get("carbonio_email"):
            raise HTTPException(status_code=400, detail="Usuário não tem email Carbonio configurado")

        token = _get_token_valido(cursor, payload.usuario_id)

        try:
            resultado = criar_evento(
                token=token,
                organizador_email=row["carbonio_email"],
                titulo=payload.titulo,
                inicio_iso=payload.inicio,
                fim_iso=payload.fim,
                local=payload.local,
                descricao=payload.descricao,
                convidados=payload.convidados,
                all_day=payload.all_day,
            )
        except CarbonioError as err:
            msg = str(err).lower()
            if "auth" in msg or "expir" in msg:
                cursor.execute(
                    "UPDATE users SET carbonio_token=NULL, carbonio_token_exp=NULL WHERE id=%s",
                    (payload.usuario_id,),
                )
                conn.commit()
                raise HTTPException(status_code=401, detail="Sessão Carbonio inválida — refaça login.")
            raise HTTPException(status_code=502, detail=f"Carbonio: {err}")
        except CarbonioOfflineError as err:
            raise HTTPException(status_code=502, detail=str(err))

        return resultado
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[AGENDA/EVENTOS/CREATE] {err}")
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.get("/eventos/{evento_id}/detalhes")
async def detalhes_evento(evento_id: str, usuario_id: int = Query(..., gt=0)):
    """Retorna detalhes completos de um evento (incluindo convidados e RSVP)."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        token = _get_token_valido(cursor, usuario_id)
        try:
            return obter_detalhes_evento(token, evento_id)
        except CarbonioError as err:
            raise HTTPException(status_code=502, detail=f"Carbonio: {err}")
        except CarbonioOfflineError as err:
            raise HTTPException(status_code=502, detail=str(err))
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[AGENDA/EVENTOS/DETALHES] {err}")
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.post("/eventos/{evento_id}/reenviar")
async def reenviar_evento(evento_id: str, payload: ReenviarPayload):
    """Reenvia o convite do evento para os destinatários informados (que ainda não confirmaram)."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        token = _get_token_valido(cursor, payload.usuario_id)
        try:
            return reenviar_convite(token, evento_id, payload.destinatarios)
        except CarbonioError as err:
            raise HTTPException(status_code=502, detail=f"Carbonio: {err}")
        except CarbonioOfflineError as err:
            raise HTTPException(status_code=502, detail=str(err))
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[AGENDA/EVENTOS/REENVIAR] {err}")
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
