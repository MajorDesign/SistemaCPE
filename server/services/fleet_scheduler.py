"""
fleet_scheduler.py — jobs periodicos de lembrete/escalada de devolucao.

Rodam DENTRO do processo do CPEControlAPI via APScheduler.
Ativado no startup do FastAPI (server/app.py -> startup event).

Jobs:
  * job_lembretes (a cada 10 min):
      - 1h antes do fim -> email "falta 1h"
      - No horario do fim -> email "venceu"
      - Atrasado, ultimo lembrete >3h -> email "atrasado" (repete a cada 3h)
  * job_escalada (a cada 1h):
      - Atrasado >= 6h -> notifica RESPONSAVEL_GRUPO(Frotas)
  * job_cleanup (a cada 30 min):
      - Auto-cancela reservas aprovadas sem checklist apos 40 min
        (o que hoje so roda on-demand quando alguem chama /notifications)

Idempotencia via campos de tracking em fleet_checklists:
    lembrete_1h_enviado_em, lembrete_vencimento_enviado_em,
    lembrete_atrasado_ultimo_em, escalada_frotas_enviada_em.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, time as _time, date as _date
from typing import Optional


def _hf_to_str(hf) -> Optional[str]:
    """Normaliza horario_fim do MySQL (pode vir como timedelta, time ou str)
    pra 'HH:MM:SS' com zero-pad correto. Retorna None se nao der.
    """
    if hf is None:
        return None
    if isinstance(hf, timedelta):
        total = int(hf.total_seconds())
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
    if isinstance(hf, _time):
        return hf.strftime("%H:%M:%S")
    s = str(hf).strip()
    if not s:
        return None
    parts = s.split(":")
    if len(parts) == 2:
        parts.append("00")
    return ":".join(f"{int(p):02d}" for p in parts[:3])


def _combinar_dt(data_val, horario_val) -> Optional[datetime]:
    """Combina data + hora (varios formatos) num datetime. Robusto contra
    valores None ou tipos inesperados."""
    if not data_val or not horario_val:
        return None
    if isinstance(data_val, datetime):
        d = data_val.date()
    elif isinstance(data_val, _date):
        d = data_val
    else:
        try:
            d = datetime.fromisoformat(str(data_val)).date()
        except Exception:
            return None
    hf_str = _hf_to_str(horario_val)
    if not hf_str:
        return None
    try:
        return datetime.fromisoformat(f"{d.isoformat()}T{hf_str}")
    except Exception:
        return None

logger = logging.getLogger(__name__)

# Import lazy dos servicos de email/db pra evitar circular
def _get_db_config():
    from config import (
        MYSQL_HOST, MYSQL_PORT, MYSQL_DB, MYSQL_USER, MYSQL_PASSWORD
    )
    return {
        "host": MYSQL_HOST, "port": int(MYSQL_PORT),
        "user": MYSQL_USER, "password": MYSQL_PASSWORD,
        "database": MYSQL_DB,
        # CRITICO: sem use_pure=True o mysql-connector 9.x C extension
        # segfalta (ACCESS_VIOLATION 0xC0000005) — derruba o processo
        # inteiro do uvicorn, NSSM restart e os jobs de 10min/30min/1h
        # nunca completam intervalo. Bug identificado em 2026-07-16 (14
        # crashes/2h). Ver database.py:34 pra config canonica.
        "use_pure": True,
        "charset":  "utf8mb4",
        "collation": "utf8mb4_unicode_ci",
    }


def _connect():
    import mysql.connector
    return mysql.connector.connect(**_get_db_config())


# =====================================================================
# JOB 1: lembretes (a cada 10 min)
# =====================================================================

def job_lembretes():
    """Envia emails de lembrete pra condutor com devolucao pendente.

    Regra: usa lembrete_*_enviado_em pra idempotencia. Nao envia 2x o mesmo
    email pro mesmo checklist. O 'atrasado' repete a cada 3h enquanto o
    checklist continuar em 'em_viagem'.
    """
    logger.info("[FLEET-SCHED] job_lembretes rodando")
    try:
        from services.email_service import (
            enviar_email,
            email_lembrete_devolver_veiculo_1h,
            email_devolver_veiculo_vencido,
        )
    except Exception as e:
        logger.error(f"[FLEET-SCHED] falha import email_service: {e}")
        return

    conn = None; cur = None
    enviados_1h = enviados_venc = enviados_atr = 0
    try:
        conn = _connect()
        cur = conn.cursor(dictionary=True)

        # Busca checklists em_viagem com condutor + veiculo + reserva mais
        # recente (subquery evita duplicar linhas se houver N reservas).
        cur.execute("""
            SELECT
                c.id           AS checklist_id,
                c.vehicle_id,
                c.condutor_id,
                c.data_saida,
                c.horario_saida,
                c.lembrete_1h_enviado_em,
                c.lembrete_vencimento_enviado_em,
                c.lembrete_atrasado_ultimo_em,
                v.modelo, v.placa,
                u.name AS condutor_nome,
                u.email AS condutor_email,
                (SELECT r.data_reserva FROM fleet_reservations r
                  WHERE r.vehicle_id=c.vehicle_id AND r.solicitante_id=c.condutor_id
                    AND r.status='aprovado'
                  ORDER BY r.id DESC LIMIT 1) AS data_reserva,
                (SELECT r.data_fim FROM fleet_reservations r
                  WHERE r.vehicle_id=c.vehicle_id AND r.solicitante_id=c.condutor_id
                    AND r.status='aprovado'
                  ORDER BY r.id DESC LIMIT 1) AS data_fim,
                (SELECT r.horario_fim FROM fleet_reservations r
                  WHERE r.vehicle_id=c.vehicle_id AND r.solicitante_id=c.condutor_id
                    AND r.status='aprovado'
                  ORDER BY r.id DESC LIMIT 1) AS horario_fim
            FROM fleet_checklists c
            JOIN fleet_vehicles  v ON v.id = c.vehicle_id
            JOIN users u ON u.id = c.condutor_id
            WHERE c.status = 'em_viagem'
              AND u.email IS NOT NULL AND u.email <> ''
        """)
        agora = datetime.now()
        for row in cur.fetchall():
            # Usa reserva pra saber horario_fim; se nao, data_saida/horario_saida
            data_fim = row.get("data_fim") or row.get("data_reserva") or row.get("data_saida")
            horario_fim = row.get("horario_fim") or row.get("horario_saida")
            dt_fim = _combinar_dt(data_fim, horario_fim)
            if dt_fim is None:
                continue
            hf_str = _hf_to_str(horario_fim) or "00:00"

            delta = dt_fim - agora  # positivo = futuro, negativo = atrasado
            checklist_id = row["checklist_id"]

            # (A) Lembrete "1h antes" — janela: 45min a 75min pra vencer
            if timedelta(minutes=45) < delta < timedelta(minutes=75) \
                    and not row.get("lembrete_1h_enviado_em"):
                subj, html = email_lembrete_devolver_veiculo_1h(
                    condutor_nome=row["condutor_nome"] or "",
                    veiculo_modelo=row["modelo"] or "",
                    veiculo_placa=row["placa"] or "",
                    horario_fim=hf_str,
                    data_fim=str(data_fim),
                    checklist_id=checklist_id,
                )
                enviar_email(row["condutor_email"], subj, html)
                cur.execute(
                    "UPDATE fleet_checklists SET lembrete_1h_enviado_em=NOW() WHERE id=%s",
                    (checklist_id,)
                )
                enviados_1h += 1

            # (B) Vencimento (0-30min pra vencer OU vencido 0-30min)
            elif abs(delta.total_seconds()) < 1800 \
                    and not row.get("lembrete_vencimento_enviado_em"):
                subj, html = email_devolver_veiculo_vencido(
                    condutor_nome=row["condutor_nome"] or "",
                    veiculo_modelo=row["modelo"] or "",
                    veiculo_placa=row["placa"] or "",
                    horario_fim=hf_str,
                    data_fim=str(data_fim),
                    checklist_id=checklist_id,
                    horas_atraso=0,
                )
                enviar_email(row["condutor_email"], subj, html)
                cur.execute(
                    "UPDATE fleet_checklists SET lembrete_vencimento_enviado_em=NOW() WHERE id=%s",
                    (checklist_id,)
                )
                enviados_venc += 1

            # (C) Atrasado (delta < -30min); repete a cada 3h
            elif delta < timedelta(minutes=-30):
                ultimo = row.get("lembrete_atrasado_ultimo_em")
                pode_reenviar = (
                    ultimo is None
                    or (agora - ultimo) >= timedelta(hours=3)
                )
                if pode_reenviar:
                    horas_atraso = int(abs(delta.total_seconds()) // 3600)
                    subj, html = email_devolver_veiculo_vencido(
                        condutor_nome=row["condutor_nome"] or "",
                        veiculo_modelo=row["modelo"] or "",
                        veiculo_placa=row["placa"] or "",
                        horario_fim=hf_str,
                        data_fim=str(data_fim),
                        checklist_id=checklist_id,
                        horas_atraso=horas_atraso,
                    )
                    enviar_email(row["condutor_email"], subj, html)
                    cur.execute(
                        "UPDATE fleet_checklists SET lembrete_atrasado_ultimo_em=NOW() WHERE id=%s",
                        (checklist_id,)
                    )
                    enviados_atr += 1

        conn.commit()
        logger.info(
            f"[FLEET-SCHED] job_lembretes: 1h={enviados_1h} venc={enviados_venc} atr={enviados_atr}"
        )
    except Exception as e:
        logger.exception(f"[FLEET-SCHED] job_lembretes erro: {e}")
    finally:
        if cur:  cur.close()
        if conn: conn.close()


# =====================================================================
# JOB 2: escalada pra RESPONSAVEL_GRUPO(Frotas) (a cada 1h)
# =====================================================================

def job_escalada():
    """Se atraso >= 6h e ainda nao escalou, envia email pra todos os
    RESPONSAVEL_GRUPO do grupo Frotas."""
    logger.info("[FLEET-SCHED] job_escalada rodando")
    try:
        from services.email_service import enviar_email, email_escalada_atraso_veiculo
    except Exception as e:
        logger.error(f"[FLEET-SCHED] falha import email_service: {e}")
        return

    conn = None; cur = None
    enviados = 0
    try:
        conn = _connect()
        cur = conn.cursor(dictionary=True)

        # Descobre grupo Frotas
        cur.execute("SELECT id FROM cpe_grupo WHERE LOWER(name)='frotas' LIMIT 1")
        g = cur.fetchone()
        if not g:
            logger.warning("[FLEET-SCHED] grupo 'Frotas' nao encontrado — pulando escalada")
            return
        frotas_group_id = g["id"]

        # Responsaveis do grupo Frotas
        cur.execute(
            "SELECT id, name, email FROM users "
            "WHERE group_id=%s AND role='RESPONSAVEL_GRUPO' AND is_active=1 "
            "  AND email IS NOT NULL AND email <> ''",
            (frotas_group_id,)
        )
        responsaveis = cur.fetchall()
        if not responsaveis:
            logger.warning("[FLEET-SCHED] sem RESPONSAVEL_GRUPO de Frotas — pulando")
            return

        # Checklists atrasados >= 6h sem escalada (subquery evita duplicacao)
        cur.execute("""
            SELECT
                c.id AS checklist_id, c.vehicle_id, c.condutor_id,
                v.modelo, v.placa,
                u.name AS condutor_nome,
                (SELECT r.data_reserva FROM fleet_reservations r
                  WHERE r.vehicle_id=c.vehicle_id AND r.solicitante_id=c.condutor_id
                    AND r.status='aprovado'
                  ORDER BY r.id DESC LIMIT 1) AS data_reserva,
                (SELECT r.data_fim FROM fleet_reservations r
                  WHERE r.vehicle_id=c.vehicle_id AND r.solicitante_id=c.condutor_id
                    AND r.status='aprovado'
                  ORDER BY r.id DESC LIMIT 1) AS data_fim,
                (SELECT r.horario_fim FROM fleet_reservations r
                  WHERE r.vehicle_id=c.vehicle_id AND r.solicitante_id=c.condutor_id
                    AND r.status='aprovado'
                  ORDER BY r.id DESC LIMIT 1) AS horario_fim,
                c.data_saida, c.horario_saida
            FROM fleet_checklists c
            JOIN fleet_vehicles  v ON v.id = c.vehicle_id
            JOIN users u ON u.id = c.condutor_id
            WHERE c.status = 'em_viagem'
              AND c.escalada_frotas_enviada_em IS NULL
        """)
        agora = datetime.now()
        for row in cur.fetchall():
            data_fim = row.get("data_fim") or row.get("data_reserva") or row.get("data_saida")
            horario_fim = row.get("horario_fim") or row.get("horario_saida")
            if not data_fim or not horario_fim:
                continue
            dt_fim = _combinar_dt(data_fim, horario_fim)
            if dt_fim is None:
                continue
            hf_str = _hf_to_str(horario_fim) or "00:00"
            atraso = agora - dt_fim
            if atraso < timedelta(hours=6):
                continue

            horas_atraso = int(atraso.total_seconds() // 3600)
            for resp in responsaveis:
                subj, html = email_escalada_atraso_veiculo(
                    destinatario_nome=resp["name"] or "",
                    condutor_nome=row["condutor_nome"] or "",
                    veiculo_modelo=row["modelo"] or "",
                    veiculo_placa=row["placa"] or "",
                    data_fim=str(data_fim),
                    horario_fim=hf_str,
                    checklist_id=row["checklist_id"],
                    horas_atraso=horas_atraso,
                )
                enviar_email(resp["email"], subj, html)
            cur.execute(
                "UPDATE fleet_checklists SET escalada_frotas_enviada_em=NOW() WHERE id=%s",
                (row["checklist_id"],)
            )
            enviados += 1

        conn.commit()
        logger.info(f"[FLEET-SCHED] job_escalada: {enviados} escaladas")
    except Exception as e:
        logger.exception(f"[FLEET-SCHED] job_escalada erro: {e}")
    finally:
        if cur:  cur.close()
        if conn: conn.close()


# =====================================================================
# JOB 3: cleanup — auto-cancela reservas fantasmas (>=40 min sem checklist)
# =====================================================================

def job_cleanup_fantasmas():
    """Auto-cancela reservas 'aprovado' que ja passaram do horario de
    inicio ha mais de 40 min sem checklist criado. Mantem consistencia
    do estado — antes so rodava on-demand quando alguem abria /notifications.
    """
    logger.info("[FLEET-SCHED] job_cleanup_fantasmas rodando")
    conn = None; cur = None
    try:
        conn = _connect()
        cur = conn.cursor()
        cur.execute("""
            UPDATE fleet_reservations r
               SET r.status='cancelado'
             WHERE r.status='aprovado'
               AND TIMESTAMP(r.data_reserva, r.horario_inicio) < DATE_SUB(NOW(), INTERVAL 40 MINUTE)
               AND NOT EXISTS (
                   SELECT 1 FROM fleet_checklists c
                    WHERE c.vehicle_id = r.vehicle_id
                      AND c.condutor_id = r.solicitante_id
                      AND DATE(c.data_saida) = r.data_reserva
               )
        """)
        n = cur.rowcount
        conn.commit()
        logger.info(f"[FLEET-SCHED] job_cleanup: {n} reservas fantasmas canceladas")
    except Exception as e:
        logger.exception(f"[FLEET-SCHED] job_cleanup erro: {e}")
    finally:
        if cur:  cur.close()
        if conn: conn.close()


# =====================================================================
# JOB 4: cancela reservas pendentes que expiraram sem aprovacao (2026-07-16)
# =====================================================================
# Regra de negocio (definida com o usuario em 2026-07-16):
#   - Reserva 'pendente' que atingiu o horario de INICIO sem aprovacao
#     deve ser cancelada automaticamente.
#   - Excecao: reservas criadas com menos de 15 min de antecedencia
#     ganham uma janela de 15 min pra aprovacao (evita cancelar
#     imediato uma reserva de ultima hora que acabou de ser criada).
#
# Motivo do cancelamento fica gravado em fleet_reservations.motivo_rejeicao
# com prefixo "EXPIRED_NO_APPROVAL::<nome do resp>" — o endpoint
# /notifications no fleet.py detecta esse prefixo pra mostrar mensagem
# especifica no frontend, sem depender de coluna nova.
#
# Notifica via email tanto o condutor quanto TODOS os Resp Frotas.
# Notif in-app: seta notif_lida=0 pro condutor ver ao abrir /notifications.

# Nome da constante deve bater com FLEET_GROUP_ID em server/routes/fleet.py
# e no frontend (fleet.html). Se mudar, mudar nos 3 lugares.
_FLEET_GROUP_ID = 13

def job_cancelar_reservas_sem_aprovacao():
    """A cada 5 min: cancela pendentes cujo prazo (max(inicio, created+15min))
    ja passou. Notifica condutor + responsavel(is) Frotas por email."""
    logger.info("[FLEET-SCHED] job_cancelar_reservas_sem_aprovacao rodando")
    try:
        from services.email_service import (
            enviar_email,
            email_reserva_expirada_condutor,
            email_reserva_expirada_responsavel,
        )
    except Exception as e:
        logger.error(f"[FLEET-SCHED] falha import email_service: {e}")
        return

    conn = None; cur = None
    try:
        conn = _connect()
        cur = conn.cursor(dictionary=True)

        # Busca resp(s) Frotas ativos — email/name usados nos avisos e no
        # motivo gravado. Se houver mais de 1, o primeiro (menor id) vira
        # o "nome oficial" no motivo; todos recebem email.
        cur.execute("""
            SELECT id, name, email
              FROM users
             WHERE role='RESPONSAVEL_GRUPO' AND group_id=%s AND is_active=1
             ORDER BY id
        """, (_FLEET_GROUP_ID,))
        resp_frotas = cur.fetchall() or []
        if not resp_frotas:
            logger.warning("[FLEET-SCHED] nenhum Resp Frotas ativo — mensagem generica")
            resp_nome_oficial = "Responsável do grupo Frotas"
        else:
            resp_nome_oficial = resp_frotas[0]["name"] or "Responsável Frotas"

        # Busca reservas elegiveis
        cur.execute("""
            SELECT r.id, r.solicitante_id, r.vehicle_id, r.destino,
                   r.data_reserva, r.horario_inicio, r.created_at,
                   v.placa, v.modelo,
                   u.name AS condutor_nome, u.email AS condutor_email,
                   TIMESTAMPDIFF(MINUTE, TIMESTAMP(r.data_reserva, r.horario_inicio), NOW()) AS min_atraso
              FROM fleet_reservations r
              JOIN fleet_vehicles v ON v.id = r.vehicle_id
              JOIN users u          ON u.id = r.solicitante_id
             WHERE r.status='pendente'
               AND NOW() >= TIMESTAMP(r.data_reserva, r.horario_inicio)
               AND NOW() >= (r.created_at + INTERVAL 15 MINUTE)
        """)
        elegiveis = cur.fetchall() or []
        if not elegiveis:
            logger.info("[FLEET-SCHED] nenhuma reserva pendente expirada")
            return

        # Grava motivo com prefixo detectavel pelo frontend
        motivo_prefixo = f"EXPIRED_NO_APPROVAL::{resp_nome_oficial}"

        canceladas = 0
        for r in elegiveis:
            # Cancela + reseta notif_lida pro condutor ver ao abrir o sistema
            cur.execute("""
                UPDATE fleet_reservations
                   SET status='cancelado',
                       motivo_rejeicao=%s,
                       notif_lida=0
                 WHERE id=%s AND status='pendente'
            """, (motivo_prefixo, r["id"]))
            if cur.rowcount == 0:
                # Alguem cancelou/aprovou entre a query e o UPDATE — skip
                continue

            data_str = str(r["data_reserva"])
            hora_str = _hf_to_str(r["horario_inicio"]) or "—"
            minutos_atraso = max(0, int(r.get("min_atraso") or 0))

            # Email pro condutor
            try:
                assunto, html = email_reserva_expirada_condutor(
                    condutor_nome=r["condutor_nome"] or "Condutor",
                    veiculo_modelo=r["modelo"] or "",
                    veiculo_placa=r["placa"] or "",
                    destino=r["destino"] or "",
                    data_reserva=data_str,
                    horario_inicio=hora_str,
                    resp_frotas_nome=resp_nome_oficial,
                )
                if r["condutor_email"]:
                    enviar_email(para=r["condutor_email"], assunto=assunto, html=html)
                    logger.info(f"[FLEET-SCHED/EXPIRE] email condutor -> {r['condutor_email']} (res={r['id']})")
            except Exception as e:
                logger.error(f"[FLEET-SCHED/EXPIRE] email condutor falhou: {e}")

            # Email pra cada Resp Frotas
            for resp in resp_frotas:
                if not resp.get("email"):
                    continue
                try:
                    assunto, html = email_reserva_expirada_responsavel(
                        resp_frotas_nome=resp["name"] or "Responsável",
                        condutor_nome=r["condutor_nome"] or "Condutor",
                        veiculo_modelo=r["modelo"] or "",
                        veiculo_placa=r["placa"] or "",
                        destino=r["destino"] or "",
                        data_reserva=data_str,
                        horario_inicio=hora_str,
                        minutos_atraso=minutos_atraso,
                    )
                    enviar_email(para=resp["email"], assunto=assunto, html=html)
                    logger.info(f"[FLEET-SCHED/EXPIRE] email resp -> {resp['email']} (res={r['id']})")
                except Exception as e:
                    logger.error(f"[FLEET-SCHED/EXPIRE] email resp {resp['email']} falhou: {e}")

            canceladas += 1

        conn.commit()
        logger.info(f"[FLEET-SCHED/EXPIRE] {canceladas} reserva(s) canceladas por prazo")
    except Exception as e:
        logger.exception(f"[FLEET-SCHED] job_cancelar_reservas_sem_aprovacao erro: {e}")
        try:
            if conn: conn.rollback()
        except Exception:
            pass
    finally:
        if cur:  cur.close()
        if conn: conn.close()


# =====================================================================
# BOOTSTRAP: registra jobs no APScheduler
# =====================================================================

_scheduler = None


def iniciar_scheduler():
    """Chamado no startup event do FastAPI (server/app.py).
    Idempotente — se ja iniciado, retorna sem duplicar."""
    global _scheduler
    if _scheduler is not None:
        logger.info("[FLEET-SCHED] scheduler ja iniciado — skip")
        return _scheduler

    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        job_lembretes, IntervalTrigger(minutes=10),
        id="fleet_lembretes", replace_existing=True, coalesce=True,
    )
    _scheduler.add_job(
        job_escalada, IntervalTrigger(hours=1),
        id="fleet_escalada", replace_existing=True, coalesce=True,
    )
    _scheduler.add_job(
        job_cleanup_fantasmas, IntervalTrigger(minutes=30),
        id="fleet_cleanup", replace_existing=True, coalesce=True,
    )
    _scheduler.add_job(
        job_cancelar_reservas_sem_aprovacao, IntervalTrigger(minutes=5),
        id="fleet_cancel_pending", replace_existing=True, coalesce=True,
    )
    _scheduler.start()
    logger.info("[FLEET-SCHED] scheduler iniciado (4 jobs: lembretes/escalada/cleanup/cancel_pending)")
    return _scheduler


def parar_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
