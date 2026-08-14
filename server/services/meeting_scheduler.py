"""
meeting_scheduler.py — jobs periodicos de lembrete de reunioes agendadas.

Roda a cada 5 minutos e dispara:
  - Lembrete 24h antes (janela de tolerancia +/- 5min pra pegar em qualquer tick)
  - Lembrete 15min antes (mesma logica)

Marca a coluna lembrete_*_enviado_em pra idempotencia — mesmo se o job
rodar 2x no mesmo minuto, so envia 1 vez.

Sem estado in-memory — se a API reiniciar, o job continua funcionando
porque a query filtra por (start_at proximo) AND (flag ainda NULL).
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from database import get_chat_db_or_404, get_db_or_404
from config import PUBLIC_BASE_URL

logger = logging.getLogger(__name__)

_scheduler = None


def _link_meeting(code: Optional[str]) -> str:
    if not code:
        return ""
    return f"{PUBLIC_BASE_URL}/SistemaCPE/web/pages/meet.html?code={code}"


def _host_nome(user_id: int) -> str:
    plus = get_db_or_404()
    pcur = plus.cursor(dictionary=True)
    try:
        pcur.execute("SELECT name FROM users WHERE id=%s", (user_id,))
        u = pcur.fetchone()
        return (u or {}).get("name") or "CPE Tecnologia"
    finally:
        pcur.close(); plus.close()


def _enviar_lembretes(quando: str, min_ini: int, min_fim: int, coluna: str) -> int:
    """quando: '24h' ou '15min'. min_ini/fim: janela em MINUTOS a partir de agora.
    coluna: 'lembrete_24h_enviado_em' ou 'lembrete_15min_enviado_em'.
    Retorna quantos lembretes disparou.
    """
    now = datetime.now()
    ini = now + timedelta(minutes=min_ini)
    fim = now + timedelta(minutes=min_fim)

    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    enviados = 0
    try:
        cur.execute(f"""
            SELECT s.id, s.titulo, s.host_id, s.start_at,
                   m.codigo AS meeting_code
              FROM chat_meeting_schedules s
              LEFT JOIN chat_meeting_rooms m ON m.id = s.meeting_id
             WHERE s.status = 'agendada'
               AND s.{coluna} IS NULL
               AND s.start_at BETWEEN %s AND %s
        """, (ini, fim))
        schedules = cur.fetchall() or []

        for s in schedules:
            # Convidados
            cur.execute("""
                SELECT nome, email FROM chat_meeting_schedule_invitees
                 WHERE schedule_id = %s
            """, (s["id"],))
            invitees = cur.fetchall() or []
            if not invitees:
                # Sem convidados — marca como enviado pra nao ficar retentando
                cur.execute(
                    f"UPDATE chat_meeting_schedules SET {coluna}=NOW() WHERE id=%s",
                    (s["id"],),
                )
                conn.commit()
                continue

            # Marca ANTES de enviar (evita duplo envio em race conditions)
            cur.execute(
                f"UPDATE chat_meeting_schedules SET {coluna}=NOW() WHERE id=%s",
                (s["id"],),
            )
            conn.commit()

            link = _link_meeting(s.get("meeting_code"))
            host = _host_nome(s["host_id"])
            try:
                from services.email_service import enviar_email, email_meeting_lembrete
                for inv in invitees:
                    subject, html = email_meeting_lembrete(
                        dest_nome=inv["nome"], host_nome=host,
                        titulo=s["titulo"], start_at=s["start_at"],
                        link=link, quando=quando,
                    )
                    enviar_email(inv["email"], subject, html)
                    enviados += 1
            except Exception as e:
                logger.warning(f"[MEET-SCHED] falha enviar lembrete {quando} sched={s['id']}: {e}")
    finally:
        cur.close(); conn.close()

    return enviados


def job_lembretes():
    """Chamado pelo scheduler a cada 5 minutos."""
    try:
        n24 = _enviar_lembretes("24h", 23 * 60 + 55, 24 * 60 + 5, "lembrete_24h_enviado_em")
        n15 = _enviar_lembretes("15min", 10, 20, "lembrete_15min_enviado_em")
        if n24 or n15:
            logger.info(f"[MEET-SCHED] tick: {n24} lembretes 24h + {n15} lembretes 15min")
    except Exception as e:
        logger.exception(f"[MEET-SCHED] job_lembretes crash: {e}")


def job_marcar_concluidas():
    """Marca como 'concluida' agendamentos cujo end_at passou ha mais de 30min.
    Roda a cada 30min. Nao apaga sala — user pode consultar a reuniao depois.
    """
    try:
        conn = get_chat_db_or_404()
        cur = conn.cursor()
        try:
            cur.execute("""
                UPDATE chat_meeting_schedules
                   SET status='concluida'
                 WHERE status='agendada'
                   AND end_at < DATE_SUB(NOW(), INTERVAL 30 MINUTE)
            """)
            n = cur.rowcount
            conn.commit()
            if n:
                logger.info(f"[MEET-SCHED] marcadas {n} reunioes como concluidas")
        finally:
            cur.close(); conn.close()
    except Exception as e:
        logger.exception(f"[MEET-SCHED] job_marcar_concluidas crash: {e}")


def iniciar_scheduler():
    """Idempotente."""
    global _scheduler
    if _scheduler is not None:
        logger.info("[MEET-SCHED] scheduler ja iniciado — skip")
        return _scheduler

    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        job_lembretes, IntervalTrigger(minutes=5),
        id="meet_lembretes", replace_existing=True, coalesce=True,
    )
    _scheduler.add_job(
        job_marcar_concluidas, IntervalTrigger(minutes=30),
        id="meet_concluidas", replace_existing=True, coalesce=True,
    )
    _scheduler.start()
    logger.info("[MEET-SCHED] scheduler iniciado (2 jobs: lembretes/concluidas)")
    return _scheduler


def parar_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
