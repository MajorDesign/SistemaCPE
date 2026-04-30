"""
Job em background do módulo Recepção.

A cada 60 segundos:
  1) Marca como 'expirada' qualquer reserva pendente cujo prazo de
     confirmação (40 min após criação) já passou — liberando a sala.
  2) Marca como 'concluida' reservas confirmadas cujo horário fim passou.

Usa thread daemon (sem nova dependência) — iniciada no startup do FastAPI.
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
    """Executa as duas atualizações e retorna quantas linhas foram afetadas.

    Se a tabela `recepcao_reservas` ainda não existir (migração 014 não rodada),
    silencia o erro depois do primeiro aviso para não floodar o log.
    """
    global _warned_missing_table
    expiradas = 0
    concluidas = 0
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE recepcao_reservas SET status='expirada', cancelada_em=NOW(), "
            "motivo_cancel='Confirmação não recebida em 40min' "
            "WHERE status='pendente' AND confirmacao_prazo < NOW()"
        )
        expiradas = cursor.rowcount or 0

        cursor.execute(
            "UPDATE recepcao_reservas SET status='concluida' "
            "WHERE status='confirmada' AND fim < NOW()"
        )
        concluidas = cursor.rowcount or 0

        if expiradas or concluidas:
            if expiradas:
                cursor.execute(
                    "SELECT id, usuario_id FROM recepcao_reservas "
                    "WHERE status='expirada' AND cancelada_em >= NOW() - INTERVAL 2 MINUTE"
                )
                for rid, uid in cursor.fetchall():
                    try:
                        cursor.execute(
                            "INSERT INTO notificacoes (usuario_id, mensagem, tipo, lido) "
                            "VALUES (%s, %s, 'aviso', 0)",
                            (uid, f"Reserva #{rid} expirou (não confirmada em 40min)."),
                        )
                    except Exception as err:
                        logger.warning(f"[RECEPCAO/SCHED] notif fail: {err}")
            conn.commit()
        # Se chegou até aqui sem erro, reseta a flag para voltar a logar
        # caso a tabela seja removida no futuro.
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

    return {"expiradas": expiradas, "concluidas": concluidas}


def _loop():
    logger.info(f"[RECEPCAO/SCHED] thread iniciada — tick a cada {INTERVALO_SEGUNDOS}s")
    while not _stop_event.is_set():
        try:
            r = _processar_uma_vez()
            if r["expiradas"] or r["concluidas"]:
                logger.info(
                    f"[RECEPCAO/SCHED] expiradas={r['expiradas']} concluidas={r['concluidas']}"
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
