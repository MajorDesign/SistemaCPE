"""
Job em background do módulo Agenda.

A cada 60 segundos:
  Para cada usuário com sessão Carbonio ativa, busca os eventos que
  começam nos próximos 60 segundos e cria uma notificação no sino
  do sistema (uma vez por evento).

A tabela `agenda_lembretes_enviados` impede duplicação — um mesmo
evento (uid + inicio) só dispara um lembrete por usuário.

Usa thread daemon — iniciada no startup do FastAPI.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from database import get_db_connection
from services.carbonio_service import (
    listar_eventos,
    CarbonioError,
    CarbonioOfflineError,
)
from services.crypto_helper import decrypt_str

logger = logging.getLogger(__name__)

INTERVALO_SEGUNDOS = 60         # roda a cada minuto
JANELA_MIN_LEMBRETE = 60        # disparar lembrete dos eventos que começam nos próximos 60s
_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


def _processar_uma_vez() -> int:
    """Verifica todos os usuários conectados e dispara lembretes
    para eventos que começam agora. Retorna quantos lembretes foram criados."""
    enviados = 0
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Lista usuários com token Carbonio válido
        cursor.execute(
            "SELECT id, carbonio_email, carbonio_token "
            "FROM users WHERE carbonio_token IS NOT NULL "
            "  AND (carbonio_token_exp IS NULL OR carbonio_token_exp > NOW())"
        )
        usuarios = cursor.fetchall()

        if not usuarios:
            return 0

        # Janela de tempo: agora até daqui JANELA_MIN_LEMBRETE segundos
        agora = datetime.now()
        ini_ms = int(agora.timestamp() * 1000)
        fim_ms = int((agora + timedelta(seconds=JANELA_MIN_LEMBRETE)).timestamp() * 1000)

        for u in usuarios:
            uid = u["id"]
            token = decrypt_str(u["carbonio_token"])
            if not token:
                continue

            try:
                eventos = listar_eventos(token, ini_ms, fim_ms)
            except (CarbonioError, CarbonioOfflineError) as err:
                logger.debug(f"[AGENDA/SCHED] usuário {uid}: {err}")
                continue
            except Exception as err:
                logger.warning(f"[AGENDA/SCHED] erro listando eventos do usuário {uid}: {err}")
                continue

            for ev in eventos:
                # Só dispara para eventos que começam realmente nesta janela
                # (a busca pode trazer também eventos que já estão em curso)
                ini_evt = datetime.fromtimestamp(ev["inicio_ms"] / 1000)
                if ini_evt < agora - timedelta(seconds=30):
                    continue
                if ini_evt > agora + timedelta(seconds=JANELA_MIN_LEMBRETE):
                    continue

                evento_uid = ev.get("uid") or str(ev.get("id") or "")
                if not evento_uid:
                    continue

                # Insere na tabela de controle (ignora se já existe)
                try:
                    cursor.execute(
                        "INSERT IGNORE INTO agenda_lembretes_enviados "
                        "(usuario_id, evento_uid, inicio_evt) VALUES (%s, %s, %s)",
                        (uid, evento_uid, ini_evt),
                    )
                    if cursor.rowcount == 0:
                        # Já tinha sido enviado — pula sem criar notificação duplicada
                        continue
                except Exception as err:
                    logger.warning(f"[AGENDA/SCHED] insert controle fail: {err}")
                    continue

                # Cria notificação no sino
                titulo = ev.get("titulo") or "(sem título)"
                local  = ev.get("local")
                hora   = ini_evt.strftime("%H:%M")
                msg = f"🔔 {titulo} — começa às {hora}"
                if local:
                    msg += f" ({local})"

                try:
                    cursor.execute(
                        "INSERT INTO notificacoes (usuario_id, mensagem, tipo, lido) "
                        "VALUES (%s, %s, 'lembrete_agenda', 0)",
                        (uid, msg),
                    )
                    enviados += 1
                except Exception as err:
                    logger.warning(f"[AGENDA/SCHED] insert notificação fail: {err}")

        if enviados:
            conn.commit()
    except Exception as err:
        msg = str(err).lower()
        if "1146" in msg or "doesn't exist" in msg:
            # tabela ausente — silencia (migrations 020/021 não rodaram)
            pass
        else:
            logger.error(f"[AGENDA/SCHED] erro no tick: {err}")
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

    return enviados


def _loop():
    logger.info(f"[AGENDA/SCHED] thread iniciada — tick a cada {INTERVALO_SEGUNDOS}s")
    while not _stop_event.is_set():
        try:
            n = _processar_uma_vez()
            if n:
                logger.info(f"[AGENDA/SCHED] {n} lembrete(s) enviado(s)")
        except Exception as err:
            logger.error(f"[AGENDA/SCHED] erro inesperado: {err}")
        _stop_event.wait(INTERVALO_SEGUNDOS)
    logger.info("[AGENDA/SCHED] thread encerrada")


def iniciar():
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_loop, name="agenda-scheduler", daemon=True)
    _thread.start()
    logger.info("[AGENDA/SCHED] iniciado")


def parar():
    _stop_event.set()
