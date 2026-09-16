"""
meeting_agenda_sync.py — espelha `chat_meeting_schedules` na Agenda V2.

Quando o host cria/edita/cancela um schedule de reuniao, replica o
mesmo evento em `ag_eventos` do calendario pessoal do host + convida
os invitees internos como `ag_participantes`. Assim o Calendario da
Agenda V2 mostra as reunioes junto com os outros compromissos.

O vinculo e mantido em `chat_meeting_schedules.agenda_evento_id`
(migration 096).

Cada funcao aqui aceita um `cur` DB opcional (pra rodar dentro da
mesma transacao do routes/meetings.py), mas se nao passar, abre
conexao propria. Isso simplifica o call-site sem obrigar a passar
conexao em toda chamada.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, Optional

from server.database import get_db_connection as _get_db

logger = logging.getLogger(__name__)


def _ensure_calendario_pessoal(cur, user_id: int) -> int:
    """Espelha `_ensure_default_calendario_pessoal` de routes/agenda_v2.py
    mas em versao portatil (sem lock de thread), suficiente pra uso interno
    apos a primeira carga do renderer ja ter criado o registro."""
    cur.execute("""
        SELECT id FROM ag_calendarios
        WHERE tipo_dono='user' AND dono_user_id=%s AND is_default=1
          AND deleted_at IS NULL
        LIMIT 1
    """, (user_id,))
    row = cur.fetchone()
    if row:
        return row["id"] if isinstance(row, dict) else row[0]
    cur.execute("""
        INSERT INTO ag_calendarios
          (nome, cor, tipo_dono, dono_user_id, is_default, criado_por)
        VALUES (%s, %s, 'user', %s, 1, %s)
    """, ("Meu calendario", "#1f6feb", user_id, user_id))
    return cur.lastrowid


def criar_evento_reuniao(
    *,
    host_id: int,
    titulo: str,
    descricao: Optional[str],
    start_at: datetime,
    end_at: datetime,
    meeting_code: str,
    link_publico: str,
    invitees_user_ids: Iterable[int] = (),
) -> Optional[int]:
    """Cria evento em ag_eventos + adiciona participantes internos.
    Retorna o id do evento criado, ou None em caso de falha
    (nao levanta — replicacao na agenda e best-effort)."""
    try:
        conn = _get_db()
        if not conn:
            logger.warning("[meet-agenda-sync] sem conexao DB — pulando")
            return None
        cur = conn.cursor(dictionary=True)
        try:
            cal_id = _ensure_calendario_pessoal(cur, host_id)
            cur.execute("""
                INSERT INTO ag_eventos
                  (calendario_id, titulo, descricao_html, local, link_online,
                   meeting_code, dia_inteiro, inicio, fim, cor, visibilidade,
                   disponibilidade, status_op, organizador_id, criado_por)
                VALUES (%s,%s,%s,%s,%s,%s, 0,%s,%s, %s,'default','ocupado',
                        'agendado', %s, %s)
            """, (
                cal_id, titulo[:200], (descricao or "")[:8000] or None,
                None, link_publico, meeting_code,
                start_at, end_at, "#FFC107",
                host_id, host_id,
            ))
            ev_id = cur.lastrowid
            _sync_participantes(cur, ev_id, invitees_user_ids)
            cur.execute(
                "INSERT INTO ag_audit (evento_id, actor_id, action) VALUES (%s,%s,'created')",
                (ev_id, host_id),
            )
            conn.commit()
            return ev_id
        finally:
            cur.close(); conn.close()
    except Exception as e:
        logger.warning(f"[meet-agenda-sync] criar_evento falhou: {e}")
        return None


def atualizar_evento_reuniao(
    *,
    evento_id: int,
    host_id: int,
    titulo: Optional[str] = None,
    descricao: Optional[str] = None,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    invitees_user_ids: Optional[Iterable[int]] = None,
) -> bool:
    """Aplica update parcial no evento espelhado. Se invitees_user_ids
    vier, substitui a lista de participantes internos."""
    try:
        conn = _get_db()
        if not conn:
            return False
        cur = conn.cursor(dictionary=True)
        try:
            sets, params = [], []
            if titulo is not None:
                sets.append("titulo=%s"); params.append(titulo[:200])
            if descricao is not None:
                sets.append("descricao_html=%s"); params.append((descricao or "")[:8000] or None)
            if start_at is not None:
                sets.append("inicio=%s"); params.append(start_at)
            if end_at is not None:
                sets.append("fim=%s"); params.append(end_at)
            if sets:
                sets.append("alterado_em=NOW()"); sets.append("alterado_por=%s")
                params.append(host_id); params.append(evento_id)
                cur.execute(
                    f"UPDATE ag_eventos SET {', '.join(sets)} WHERE id=%s",
                    tuple(params),
                )
            if invitees_user_ids is not None:
                _sync_participantes(cur, evento_id, invitees_user_ids)
            cur.execute(
                "INSERT INTO ag_audit (evento_id, actor_id, action) VALUES (%s,%s,'updated')",
                (evento_id, host_id),
            )
            conn.commit()
            return True
        finally:
            cur.close(); conn.close()
    except Exception as e:
        logger.warning(f"[meet-agenda-sync] atualizar_evento falhou: {e}")
        return False


def cancelar_evento_reuniao(*, evento_id: int, host_id: int) -> bool:
    """Marca o evento como cancelado (soft-delete via status_op='cancelado')."""
    try:
        conn = _get_db()
        if not conn:
            return False
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                "UPDATE ag_eventos SET status_op='cancelado', alterado_em=NOW(), alterado_por=%s WHERE id=%s",
                (host_id, evento_id),
            )
            cur.execute(
                "INSERT INTO ag_audit (evento_id, actor_id, action) VALUES (%s,%s,'cancelled')",
                (evento_id, host_id),
            )
            conn.commit()
            return True
        finally:
            cur.close(); conn.close()
    except Exception as e:
        logger.warning(f"[meet-agenda-sync] cancelar_evento falhou: {e}")
        return False


def _sync_participantes(cur, evento_id: int, invitees_user_ids: Iterable[int]) -> None:
    """Substitui a lista de participantes internos do evento."""
    ids = [int(u) for u in invitees_user_ids if u]
    cur.execute("DELETE FROM ag_participantes WHERE evento_id=%s", (evento_id,))
    for uid in ids:
        cur.execute("""
            INSERT INTO ag_participantes
              (evento_id, user_id, papel, convite_enviado_em)
            VALUES (%s, %s, 'convidado', NOW())
        """, (evento_id, uid))
