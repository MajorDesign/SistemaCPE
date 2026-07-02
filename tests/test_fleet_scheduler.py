"""
Testes dos jobs do fleet_scheduler.

Foco em logica de decisao (quando envia, quando pula) — o envio de email
real e mockado pra nao spammar SMTP.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest


pytestmark = [pytest.mark.fleet, pytest.mark.scheduler]


def _dt_futuro(minutos):
    """Datetime futuro em N minutos."""
    return datetime.now() + timedelta(minutes=minutos)


def _dt_passado(horas):
    return datetime.now() - timedelta(hours=horas)


def _preparar_reserva_com_fim(cursor, db, checklist_id, vehicle_id, user_id, dt_fim):
    """Cria/atualiza reserva pra ter horario_fim = dt_fim."""
    data_fim = dt_fim.strftime("%Y-%m-%d")
    horario_fim = dt_fim.strftime("%H:%M:%S")
    cursor.execute(
        """INSERT INTO fleet_reservations
             (vehicle_id, solicitante_id, destino, data_reserva, data_fim,
              horario_inicio, horario_fim, status)
           VALUES (%s, %s, 'teste', CURDATE(), %s, '08:00', %s, 'aprovado')""",
        (vehicle_id, user_id, data_fim, horario_fim)
    )
    res_id = cursor.lastrowid
    db.commit()
    return res_id


# ---------- job_lembretes ----------

def test_lembrete_1h_dispara_dentro_da_janela(cursor, db, checklist_em_viagem):
    """Reserva termina em 60min (dentro da janela 45-75min) -> lembrete_1h_enviado_em vira NOW()."""
    ck = checklist_em_viagem
    _preparar_reserva_com_fim(cursor, db, ck["checklist_id"], ck["vehicle_id"],
                              ck["user_id"], _dt_futuro(60))
    from services.fleet_scheduler import job_lembretes
    with patch("services.email_service.enviar_email") as mock_send:
        job_lembretes()
    db.rollback()   # limpa MVCC snapshot da fixture pra pegar update do job
    cursor.execute("SELECT lembrete_1h_enviado_em FROM fleet_checklists WHERE id=%s",
                   (ck["checklist_id"],))
    row = cursor.fetchone()
    assert row["lembrete_1h_enviado_em"] is not None, (
        "Lembrete 1h deveria ter sido marcado quando reserva termina em 60min"
    )


def test_lembrete_1h_nao_dispara_fora_da_janela(cursor, db, checklist_em_viagem):
    """Reserva termina em 200min (fora da janela) -> nao envia."""
    ck = checklist_em_viagem
    _preparar_reserva_com_fim(cursor, db, ck["checklist_id"], ck["vehicle_id"],
                              ck["user_id"], _dt_futuro(200))
    from services.fleet_scheduler import job_lembretes
    with patch("services.email_service.enviar_email"):
        job_lembretes()
    db.rollback()   # limpa MVCC snapshot da fixture
    cursor.execute("SELECT lembrete_1h_enviado_em FROM fleet_checklists WHERE id=%s",
                   (ck["checklist_id"],))
    row = cursor.fetchone()
    assert row["lembrete_1h_enviado_em"] is None


def test_lembrete_nao_dispara_apos_devolucao(cursor, db, checklist_devolvido):
    """Checklist ja em 'devolvido' -> nao aciona lembrete de em_viagem."""
    ck = checklist_devolvido
    _preparar_reserva_com_fim(cursor, db, ck["checklist_id"], ck["vehicle_id"],
                              ck["user_id"], _dt_futuro(60))
    from services.fleet_scheduler import job_lembretes
    with patch("services.email_service.enviar_email"):
        job_lembretes()
    db.rollback()   # limpa MVCC snapshot da fixture
    cursor.execute(
        "SELECT lembrete_1h_enviado_em, lembrete_vencimento_enviado_em, lembrete_atrasado_ultimo_em "
        "FROM fleet_checklists WHERE id=%s",
        (ck["checklist_id"],)
    )
    row = cursor.fetchone()
    # Nenhum dos 3 lembretes devia ter disparado
    assert row["lembrete_1h_enviado_em"] is None
    assert row["lembrete_vencimento_enviado_em"] is None
    assert row["lembrete_atrasado_ultimo_em"] is None


def test_lembrete_atrasado_dispara_apos_30min_vencido(cursor, db, checklist_em_viagem):
    """Reserva venceu ha 2h -> envia lembrete de atraso."""
    ck = checklist_em_viagem
    _preparar_reserva_com_fim(cursor, db, ck["checklist_id"], ck["vehicle_id"],
                              ck["user_id"], _dt_passado(2))
    from services.fleet_scheduler import job_lembretes
    with patch("services.email_service.enviar_email"):
        job_lembretes()
    db.rollback()   # limpa MVCC snapshot da fixture
    cursor.execute("SELECT lembrete_atrasado_ultimo_em FROM fleet_checklists WHERE id=%s",
                   (ck["checklist_id"],))
    row = cursor.fetchone()
    assert row["lembrete_atrasado_ultimo_em"] is not None


# ---------- job_escalada ----------

def test_escalada_dispara_apos_6h_atraso(cursor, db, checklist_em_viagem):
    """Reserva atrasada 7h + tem RESPONSAVEL_GRUPO Frotas -> escalada_enviada."""
    ck = checklist_em_viagem
    _preparar_reserva_com_fim(cursor, db, ck["checklist_id"], ck["vehicle_id"],
                              ck["user_id"], _dt_passado(7))
    # Garante que existe RESPONSAVEL_GRUPO em Frotas
    cursor.execute("SELECT id FROM cpe_grupo WHERE LOWER(name)='frotas' LIMIT 1")
    g = cursor.fetchone()
    if not g:
        pytest.skip("Snapshot nao tem grupo Frotas")
    cursor.execute(
        "SELECT COUNT(*) AS c FROM users WHERE group_id=%s AND role='RESPONSAVEL_GRUPO' AND is_active=1",
        (g["id"],)
    )
    if cursor.fetchone()["c"] == 0:
        pytest.skip("Snapshot nao tem RESPONSAVEL_GRUPO em Frotas")

    from services.fleet_scheduler import job_escalada
    with patch("services.email_service.enviar_email"):
        job_escalada()
    db.rollback()   # limpa MVCC snapshot da fixture
    cursor.execute(
        "SELECT escalada_frotas_enviada_em FROM fleet_checklists WHERE id=%s",
        (ck["checklist_id"],)
    )
    row = cursor.fetchone()
    assert row["escalada_frotas_enviada_em"] is not None


def test_escalada_nao_dispara_antes_de_6h(cursor, db, checklist_em_viagem):
    """3h atraso -> ainda nao escalou."""
    ck = checklist_em_viagem
    _preparar_reserva_com_fim(cursor, db, ck["checklist_id"], ck["vehicle_id"],
                              ck["user_id"], _dt_passado(3))
    from services.fleet_scheduler import job_escalada
    with patch("services.email_service.enviar_email"):
        job_escalada()
    db.rollback()   # limpa MVCC snapshot da fixture
    cursor.execute(
        "SELECT escalada_frotas_enviada_em FROM fleet_checklists WHERE id=%s",
        (ck["checklist_id"],)
    )
    row = cursor.fetchone()
    assert row["escalada_frotas_enviada_em"] is None
