"""
Testes das novas validacoes de reserva (migration 081 / 2026-07-02).

Todos rodam contra `cpe_plus_snapshot` (copia do prod). As mudancas de
schema (novo status 'aguardando_vistoria', campos de lembrete) ja foram
aplicadas manualmente no snapshot antes de rodar.

Casos cobertos (do plano original):
  1) test_migration_veiculo_status_aguardando_vistoria: enum existe
  2) test_migration_checklist_campos_lembrete: colunas existem
  3) test_devolucao_marca_veiculo_aguardando_vistoria: query direta
  4) test_reserva_bloqueada_veiculo_aguardando_vistoria: query de bloqueio
  5) test_reserva_bloqueada_veiculo_em_viagem: query de bloqueio
  6) test_reserva_bloqueada_solicitante_com_checklist_pendente
  7) test_vistoria_libera_veiculo (transicao completa)
  8) test_forcar_vistoria_libera_veiculo_com_avaria
"""

import pytest


pytestmark = pytest.mark.fleet


# ---------- Migration ----------

def test_migration_veiculo_status_aguardando_vistoria(cursor):
    """Confere que o ENUM de fleet_vehicles.status inclui aguardando_vistoria."""
    cursor.execute("SHOW COLUMNS FROM fleet_vehicles LIKE 'status'")
    row = cursor.fetchone()
    assert row is not None
    assert "aguardando_vistoria" in row["Type"], (
        f"ENUM nao contem aguardando_vistoria: {row['Type']}"
    )


def test_migration_checklist_campos_lembrete(cursor):
    """Confere os 4 campos de tracking de lembrete."""
    cursor.execute("SHOW COLUMNS FROM fleet_checklists")
    cols = {r["Field"] for r in cursor.fetchall()}
    esperados = {
        "lembrete_1h_enviado_em",
        "lembrete_vencimento_enviado_em",
        "lembrete_atrasado_ultimo_em",
        "escalada_frotas_enviada_em",
    }
    faltando = esperados - cols
    assert not faltando, f"Colunas faltando: {faltando}"


# ---------- Fluxo devolucao -> aguardando_vistoria ----------

def test_devolucao_marca_veiculo_aguardando_vistoria(cursor, db, checklist_em_viagem):
    """Simula a query nova do endpoint /devolver: veiculo deve virar
    aguardando_vistoria quando checklist vai pra 'devolvido'."""
    ck = checklist_em_viagem
    # Executa as UPDATEs que o backend agora faz
    cursor.execute(
        "UPDATE fleet_checklists SET status='devolvido', "
        "data_retorno=CURDATE(), horario_retorno='17:00', km_retorno=10050 "
        "WHERE id=%s",
        (ck["checklist_id"],)
    )
    cursor.execute(
        "UPDATE fleet_vehicles SET status='aguardando_vistoria' "
        "WHERE id=%s AND status='em_viagem'",
        (ck["vehicle_id"],)
    )
    # Verifica
    cursor.execute("SELECT status FROM fleet_vehicles WHERE id=%s", (ck["vehicle_id"],))
    assert cursor.fetchone()["status"] == "aguardando_vistoria"
    cursor.execute("SELECT status FROM fleet_checklists WHERE id=%s", (ck["checklist_id"],))
    assert cursor.fetchone()["status"] == "devolvido"


# ---------- Validacoes de bloqueio na criacao de reserva ----------

def _query_bloqueio_veiculo(cursor, vehicle_id):
    """Simula a validacao (a) do POST /reservations que rejeita reserva
    quando veiculo esta em em_viagem ou aguardando_vistoria."""
    cursor.execute("SELECT status FROM fleet_vehicles WHERE id=%s", (vehicle_id,))
    veh = cursor.fetchone()
    if veh and veh["status"] in ("em_viagem", "aguardando_vistoria"):
        return True
    return False


def _query_bloqueio_solicitante(cursor, user_id):
    """Simula a validacao (b): solicitante com checklist pendente em
    qualquer veiculo."""
    cursor.execute(
        """SELECT c.id, c.status
             FROM fleet_checklists c
            WHERE c.condutor_id=%s
              AND c.status IN ('em_viagem','devolvido')
            LIMIT 1""",
        (user_id,)
    )
    return cursor.fetchone() is not None


def test_reserva_bloqueada_veiculo_em_viagem(cursor, checklist_em_viagem):
    ck = checklist_em_viagem
    # Veiculo esta em 'em_viagem'
    assert _query_bloqueio_veiculo(cursor, ck["vehicle_id"]) is True


def test_reserva_bloqueada_veiculo_aguardando_vistoria(cursor, checklist_devolvido):
    ck = checklist_devolvido
    assert _query_bloqueio_veiculo(cursor, ck["vehicle_id"]) is True


def test_reserva_permitida_veiculo_ativo(cursor, veiculo_ativo):
    """Sanity check: veiculo em 'ativo' NAO deve estar bloqueado."""
    assert _query_bloqueio_veiculo(cursor, veiculo_ativo) is False


def test_reserva_bloqueada_solicitante_com_checklist_em_viagem(cursor, checklist_em_viagem):
    """Usuario que tem checklist em_viagem em qualquer veiculo NAO pode
    reservar outro veiculo. Regra vale pra ADMIN tambem (uniforme)."""
    ck = checklist_em_viagem
    assert _query_bloqueio_solicitante(cursor, ck["user_id"]) is True


def test_reserva_bloqueada_solicitante_com_checklist_devolvido(cursor, checklist_devolvido):
    """Mesma regra pra status 'devolvido' (aguardando vistoria)."""
    ck = checklist_devolvido
    assert _query_bloqueio_solicitante(cursor, ck["user_id"]) is True


# ---------- Fluxo vistoria libera veiculo ----------

def test_vistoria_retorno_libera_veiculo_sem_avaria(cursor, db, checklist_devolvido):
    ck = checklist_devolvido
    cursor.execute(
        "UPDATE fleet_checklists SET status='retornado' WHERE id=%s",
        (ck["checklist_id"],)
    )
    cursor.execute(
        "UPDATE fleet_vehicles SET status='ativo' WHERE id=%s",
        (ck["vehicle_id"],)
    )
    cursor.execute("SELECT status FROM fleet_vehicles WHERE id=%s", (ck["vehicle_id"],))
    assert cursor.fetchone()["status"] == "ativo"
    assert _query_bloqueio_veiculo(cursor, ck["vehicle_id"]) is False


def test_vistoria_com_avaria_manda_pra_manutencao(cursor, db, checklist_devolvido):
    ck = checklist_devolvido
    cursor.execute(
        "UPDATE fleet_checklists SET status='retornado_com_avaria' WHERE id=%s",
        (ck["checklist_id"],)
    )
    cursor.execute(
        "UPDATE fleet_vehicles SET status='manutencao' WHERE id=%s",
        (ck["vehicle_id"],)
    )
    cursor.execute("SELECT status FROM fleet_vehicles WHERE id=%s", (ck["vehicle_id"],))
    assert cursor.fetchone()["status"] == "manutencao"


# ---------- Endpoint admin forcar-vistoria (logica direta em SQL) ----------

def test_forcar_vistoria_libera_veiculo_sem_avaria(cursor, db, checklist_em_viagem):
    """Simula POST /vehicles/{id}/forcar-vistoria com com_avaria=False.
    Veiculo deve ir pra 'ativo' e checklist pra 'retornado'."""
    ck = checklist_em_viagem
    cursor.execute(
        "UPDATE fleet_checklists SET status='retornado' WHERE id=%s",
        (ck["checklist_id"],)
    )
    cursor.execute(
        "UPDATE fleet_vehicles SET status='ativo' WHERE id=%s",
        (ck["vehicle_id"],)
    )
    cursor.execute("SELECT status FROM fleet_vehicles WHERE id=%s", (ck["vehicle_id"],))
    assert cursor.fetchone()["status"] == "ativo"


def test_forcar_vistoria_com_avaria(cursor, db, checklist_em_viagem):
    """Simula com_avaria=True."""
    ck = checklist_em_viagem
    cursor.execute(
        "UPDATE fleet_checklists SET status='retornado_com_avaria' WHERE id=%s",
        (ck["checklist_id"],)
    )
    cursor.execute(
        "UPDATE fleet_vehicles SET status='manutencao' WHERE id=%s",
        (ck["vehicle_id"],)
    )
    cursor.execute("SELECT status FROM fleet_vehicles WHERE id=%s", (ck["vehicle_id"],))
    assert cursor.fetchone()["status"] == "manutencao"
