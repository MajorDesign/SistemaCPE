"""
Job em background do módulo Recepção.

A cada 60 segundos:
  1) Notifica o usuário responsável quando faltam <= 40min para o início
     de sua reserva pendente (uma única vez por reserva).
  2) Expira (libera a sala) reservas pendentes cujo horário de início
     já passou sem confirmação.
  3) Marca como 'concluida' reservas confirmadas cujo horário fim passou.

Usa thread daemon — iniciada no startup do FastAPI.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from database import get_db_connection

logger = logging.getLogger(__name__)

INTERVALO_SEGUNDOS = 60
_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


_warned_missing_table = False  # log "tabela ausente" só uma vez


def _processar_uma_vez() -> dict:
    """Executa os 3 ticks da política de reservas:
       1) Notifica T-40min antes do início (uma vez por reserva)
       2) Expira reservas pendentes cujo início já passou
       3) Conclui reservas confirmadas cujo fim já passou
    """
    global _warned_missing_table
    notificadas = 0
    expiradas = 0
    concluidas = 0
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1) Notificar quem tem reunião começando em <= 40min e ainda não foi notificado
        cursor.execute(
            "SELECT id, usuario_id, titulo, inicio FROM recepcao_reservas "
            "WHERE status='pendente' "
            "  AND notificou_confirmacao = 0 "
            "  AND inicio <= NOW() + INTERVAL 40 MINUTE "
            "  AND inicio > NOW()"
        )
        para_notificar = cursor.fetchall()
        for rid, uid, titulo, inicio in para_notificar:
            try:
                hora = inicio.strftime("%H:%M")
                cursor.execute(
                    "INSERT INTO notificacoes (usuario_id, mensagem, tipo, ticket_id, lido) "
                    "VALUES (%s, %s, 'confirmar_reserva', %s, 0)",
                    (uid,
                     f"Confirme sua reserva '{titulo}' — começa às {hora} (em até 40 min). "
                     f"Se não confirmar até lá, a sala será liberada.",
                     rid),
                )
                cursor.execute(
                    "UPDATE recepcao_reservas SET notificou_confirmacao = 1 WHERE id = %s",
                    (rid,),
                )
                notificadas += 1
            except Exception as err:
                logger.warning(f"[RECEPCAO/SCHED] notif T-40min fail: {err}")

        # 2) Expirar reservas pendentes cujo início já passou (sala liberada)
        cursor.execute(
            "UPDATE recepcao_reservas SET status='expirada', cancelada_em=NOW(), "
            "       motivo_cancel='Confirmação não recebida até o início da reunião' "
            "WHERE status='pendente' AND inicio <= NOW()"
        )
        expiradas = cursor.rowcount or 0

        if expiradas:
            cursor.execute(
                "SELECT id, usuario_id FROM recepcao_reservas "
                "WHERE status='expirada' AND cancelada_em >= NOW() - INTERVAL 2 MINUTE"
            )
            for rid, uid in cursor.fetchall():
                try:
                    cursor.execute(
                        "INSERT INTO notificacoes (usuario_id, mensagem, tipo, ticket_id, lido) "
                        "VALUES (%s, %s, 'aviso', %s, 0)",
                        (uid,
                         f"Reserva #{rid} expirou — não foi confirmada até o início da reunião.",
                         rid),
                    )
                except Exception as err:
                    logger.warning(f"[RECEPCAO/SCHED] notif expirada fail: {err}")

        # 3) Marcar como concluída reservas confirmadas cujo fim passou
        cursor.execute(
            "UPDATE recepcao_reservas SET status='concluida' "
            "WHERE status='confirmada' AND fim < NOW()"
        )
        concluidas = cursor.rowcount or 0

        if notificadas or expiradas or concluidas:
            conn.commit()
        _warned_missing_table = False
    except Exception as err:
        # 1146 = ER_NO_SUCH_TABLE — migração 014_recepcao.sql ainda não aplicada
        msg = str(err)
        if "1146" in msg or "doesn't exist" in msg.lower():
            if not _warned_missing_table:
                logger.warning(
                    "[RECEPCAO/SCHED] tabela 'recepcao_reservas' não existe — "
                    "rode a migração server/migrations/014_recepcao.sql. "
                    "Suprimindo este aviso até a tabela ser criada."
                )
                _warned_missing_table = True
        else:
            logger.error(f"[RECEPCAO/SCHED] erro no tick: {err}")
        if conn:
            try: conn.rollback()
            except: pass
    finally:
        if cursor:
            try: cursor.close()
            except: pass
        if conn:
            try: conn.close()
            except: pass

    return {"notificadas": notificadas, "expiradas": expiradas, "concluidas": concluidas}


def _loop():
    logger.info(f"[RECEPCAO/SCHED] thread iniciada — tick a cada {INTERVALO_SEGUNDOS}s")
    while not _stop_event.is_set():
        try:
            r = _processar_uma_vez()
            if r["notificadas"] or r["expiradas"] or r["concluidas"]:
                logger.info(
                    f"[RECEPCAO/SCHED] notificadas={r['notificadas']} "
                    f"expiradas={r['expiradas']} concluidas={r['concluidas']}"
                )
        except Exception as err:
            logger.error(f"[RECEPCAO/SCHED] erro inesperado: {err}")
        # espera respeitando shutdown
        _stop_event.wait(INTERVALO_SEGUNDOS)
    logger.info("[RECEPCAO/SCHED] thread encerrada")


def iniciar():
    """Inicia o thread em background (idempotente)."""
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_loop, name="recepcao-scheduler", daemon=True)
    _thread.start()
    logger.info("[RECEPCAO/SCHED] iniciado")


def parar():
    """Sinaliza o thread para encerrar. Não bloqueia."""
    _stop_event.set()
