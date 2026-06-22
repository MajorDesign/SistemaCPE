"""
email_preferencias.py — preferencias de email transacional por usuario.

Cada usuario pode optar OUT de receber determinado tipo de email
(notificacao de novo ticket no grupo, status alterado, etc).

Default: tudo ATIVO. Se nao ha row em user_email_preferencias pro
par (user_id, tipo_evento), considera ativo. Linhas com ativo=0
sao opt-outs explicitos.

Endpoints:
  GET  /api/users/{user_id}/email-preferencias
       -> {tipo_evento: bool, ...} com TODOS os tipos
  PUT  /api/users/{user_id}/email-preferencias
       body: {tipo_evento: bool, ...}
       -> upsert dos tipos enviados (omitidos = inalterados)

Permissoes:
  - O proprio usuario pode ler/escrever suas preferencias
  - ADMIN/TI/MANAGER pode ler/escrever preferencias de qualquer usuario
  - Outros = 403
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import BaseModel

try:
    from database import get_db_connection
except Exception:
    from server.database import get_db_connection  # fallback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["email-preferencias"])

# Tipos de evento expostos (1 por template em services/email_service.py).
# Default ativo. Reorganizar/expandir essa lista NAO requer migration.
TIPOS_EVENTO_EMAIL = [
    "ticket_criado",
    "ticket_aberto_grupo",
    "ticket_atribuido",
    "ticket_status_alterado",
    "ticket_resposta_publica",
    "ticket_comentario_interno",
    "ticket_encaminhado",
    "ticket_devolvido",
    "ticket_reaberto",
    "ticket_finalizado",
]

# Rotulos amigaveis pra UI (frontend usa estes; backend so retorna o slug).
TIPOS_EVENTO_LABEL = {
    "ticket_criado":             "Confirmação de chamado criado (pra você)",
    "ticket_aberto_grupo":       "Novo chamado na fila do seu grupo",
    "ticket_atribuido":          "Quando um chamado for atribuído a você",
    "ticket_status_alterado":    "Mudança de status em chamado que acompanho",
    "ticket_resposta_publica":   "Nova resposta no chat de chamado",
    "ticket_comentario_interno": "Comentário interno (só equipe)",
    "ticket_encaminhado":        "Chamado encaminhado para/de seu grupo",
    "ticket_devolvido":          "Chamado devolvido para a fila do grupo",
    "ticket_reaberto":           "Chamado reaberto",
    "ticket_finalizado":         "Chamado finalizado",
}


def _validar_acesso(cursor, requisitante_id: int, alvo_user_id: int) -> None:
    """Lanca 403 se requisitante nao for o proprio user nem admin."""
    if requisitante_id == alvo_user_id:
        return
    cursor.execute("SELECT role FROM users WHERE id = %s", (requisitante_id,))
    row = cursor.fetchone()
    role = (row or {}).get("role") if row else None
    if role in {"ADMIN", "TI", "MANAGER"}:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Sem permissão para acessar preferências de outro usuário",
    )


class PrefsUpdate(BaseModel):
    """Body do PUT. Aceita um dict {tipo_evento: bool}."""
    preferencias: dict[str, bool]


@router.get("/{user_id}/email-preferencias")
def obter_preferencias(
    user_id: int = Path(..., gt=0),
    requisitante_id: int = Query(..., gt=0, description="ID do usuário que está pedindo"),
):
    """Retorna preferencias do usuario. Defaults ATIVO pra tipos sem row."""
    con = get_db_connection()
    if not con:
        raise HTTPException(status_code=500, detail="DB indisponível")
    cur = None
    try:
        cur = con.cursor(dictionary=True)
        _validar_acesso(cur, requisitante_id, user_id)

        cur.execute(
            "SELECT tipo_evento, ativo FROM user_email_preferencias WHERE user_id = %s",
            (user_id,),
        )
        salvas = {r["tipo_evento"]: bool(r["ativo"]) for r in cur.fetchall()}

        # Defaults: tudo ativo. Inclui rotulos amigaveis pra UI.
        preferencias = {}
        for tipo in TIPOS_EVENTO_EMAIL:
            preferencias[tipo] = {
                "ativo": salvas.get(tipo, True),
                "label": TIPOS_EVENTO_LABEL.get(tipo, tipo),
            }
        return {"user_id": user_id, "preferencias": preferencias}
    finally:
        if cur:
            cur.close()
        con.close()


@router.put("/{user_id}/email-preferencias")
def atualizar_preferencias(
    payload: PrefsUpdate,
    user_id: int = Path(..., gt=0),
    requisitante_id: int = Query(..., gt=0),
):
    """Upsert das preferencias enviadas. Tipos omitidos ficam inalterados.

    Tipos invalidos (fora de TIPOS_EVENTO_EMAIL) sao silenciosamente
    ignorados — evita 400 quando frontend e backend divergem.
    """
    con = get_db_connection()
    if not con:
        raise HTTPException(status_code=500, detail="DB indisponível")
    cur = None
    try:
        cur = con.cursor(dictionary=True)
        _validar_acesso(cur, requisitante_id, user_id)

        atualizados = 0
        for tipo, ativo in (payload.preferencias or {}).items():
            if tipo not in TIPOS_EVENTO_EMAIL:
                logger.warning(f"[EMAIL-PREFS] tipo desconhecido ignorado: {tipo}")
                continue
            cur.execute(
                """
                INSERT INTO user_email_preferencias (user_id, tipo_evento, ativo)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE ativo = VALUES(ativo)
                """,
                (user_id, tipo, 1 if ativo else 0),
            )
            atualizados += 1
        con.commit()
        logger.info(
            f"[EMAIL-PREFS] user_id={user_id} -> {atualizados} preferencias upserted"
        )
        return {"user_id": user_id, "atualizados": atualizados, "ok": True}
    finally:
        if cur:
            cur.close()
        con.close()


# ========================================
# HELPER USADO POR tickets.py
# Filtra uma lista de user_ids removendo quem optou OUT do tipo_evento.
# ========================================

def filtrar_optouts(cursor, user_ids: list[int], tipo_evento: str) -> set[int]:
    """Retorna SET dos user_ids QUE OPTARAM OUT do tipo_evento.

    Uso no caller:
        opt_outs = filtrar_optouts(cursor, [u1, u2, u3], 'ticket_atribuido')
        # ignora quem esta em opt_outs
        destinatarios = [u for u in [u1,u2,u3] if u not in opt_outs]

    Linhas inexistentes na tabela = ativo (default). Apenas ativo=0
    explicito conta como opt-out.
    """
    if not user_ids:
        return set()
    placeholders = ",".join(["%s"] * len(user_ids))
    cursor.execute(
        f"""SELECT user_id FROM user_email_preferencias
            WHERE tipo_evento = %s AND ativo = 0
              AND user_id IN ({placeholders})""",
        [tipo_evento, *user_ids],
    )
    return {r["user_id"] for r in cursor.fetchall()}
