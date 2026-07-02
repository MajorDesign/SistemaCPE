"""
conftest.py — fixtures compartilhadas dos testes do SistemaCPE.

Estratégia:
    * Testes rodam contra o DB `cpe_plus_snapshot` local (copia de prod).
    * Cada teste roda dentro de uma TRANSACTION que faz rollback no
      teardown, garantindo isolamento sem precisar de fixtures pesadas.
    * TESTING=1 impede que app.py inicie o fleet_scheduler
      automaticamente durante import.
"""

import os
import sys
from pathlib import Path

# Marca ambiente de teste ANTES de qualquer import do server
os.environ["TESTING"] = "1"

# Adiciona `server/` ao PYTHONPATH pra imports funcionarem como no runtime
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))

import pytest
import mysql.connector
from dotenv import load_dotenv

# Carrega o .env DO PROJETO
load_dotenv(ROOT / "server" / ".env")


# =====================================================================
# Config de DB — snapshot local (cpe_plus_snapshot) copia de prod
# =====================================================================

@pytest.fixture(scope="session")
def db_config():
    """Config do MySQL local apontando pro cpe_plus_snapshot."""
    return {
        "host":     os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port":     int(os.getenv("MYSQL_PORT", "3306")),
        "user":     os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": "cpe_plus_snapshot",   # NAO cpe_plus real
    }


@pytest.fixture(autouse=True)
def _monkey_scheduler_db(db_config, monkeypatch):
    """Faz o fleet_scheduler conectar no cpe_plus_snapshot durante os testes."""
    try:
        import services.fleet_scheduler as sched
        monkeypatch.setattr(sched, "_get_db_config", lambda: db_config)
    except ImportError:
        pass   # se ainda nao carregou, tudo bem


@pytest.fixture
def db(db_config):
    """Conexao MySQL isolada por teste. Rollback no teardown."""
    conn = mysql.connector.connect(**db_config)
    conn.autocommit = False
    yield conn
    try:
        conn.rollback()
    finally:
        conn.close()


@pytest.fixture
def cursor(db):
    """Cursor dict-based com rollback automatico."""
    cur = db.cursor(dictionary=True)
    yield cur
    cur.close()


# =====================================================================
# Helpers de setup — pra criar cenarios rapidamente
# =====================================================================

@pytest.fixture
def veiculo_ativo(cursor, db):
    """Retorna id de um veiculo em status='ativo'."""
    cursor.execute("SELECT id FROM fleet_vehicles WHERE status='ativo' LIMIT 1")
    row = cursor.fetchone()
    if not row:
        pytest.skip("Sem veiculo 'ativo' no snapshot pra usar no teste")
    return row["id"]


@pytest.fixture
def user_regular(cursor):
    """Retorna id de um user comum ativo (nao admin/frotas)."""
    cursor.execute("""
        SELECT id FROM users
         WHERE is_active=1
           AND role NOT IN ('ADMIN','TI','MANAGER','RESPONSAVEL_GRUPO')
         LIMIT 1
    """)
    row = cursor.fetchone()
    if not row:
        pytest.skip("Sem user regular no snapshot")
    return row["id"]


@pytest.fixture
def user_admin(cursor):
    """Retorna id de um user ADMIN."""
    cursor.execute("SELECT id FROM users WHERE role='ADMIN' AND is_active=1 LIMIT 1")
    row = cursor.fetchone()
    if not row:
        pytest.skip("Sem ADMIN no snapshot")
    return row["id"]


@pytest.fixture
def checklist_em_viagem(cursor, db, veiculo_ativo, user_regular):
    """Cria um checklist em 'em_viagem' pra veiculo/user + coloca veiculo
    em 'em_viagem'. Retorna dict com {checklist_id, vehicle_id, user_id}.

    Antes de criar: deleta reservas antigas do (veiculo, user) e coloca
    checklists antigos em 'retornado' pra garantir isolamento do teste.
    """
    # Isolamento — limpa lixo de testes anteriores
    cursor.execute(
        "DELETE FROM fleet_reservations WHERE vehicle_id=%s AND solicitante_id=%s "
        "AND destino='teste'",
        (veiculo_ativo, user_regular)
    )
    cursor.execute(
        "UPDATE fleet_checklists SET status='retornado' "
        "WHERE vehicle_id=%s AND condutor_id=%s "
        "  AND status IN ('em_viagem','devolvido') "
        "  AND destino='Teste automatizado'",
        (veiculo_ativo, user_regular)
    )
    cursor.execute("""
        INSERT INTO fleet_checklists
            (vehicle_id, condutor_id, data_saida, horario_saida,
             km_saida, status, destino,
             lembrete_1h_enviado_em, lembrete_vencimento_enviado_em,
             lembrete_atrasado_ultimo_em, escalada_frotas_enviada_em)
        VALUES (%s, %s, CURDATE(), '08:00', 10000, 'em_viagem', 'Teste automatizado',
                NULL, NULL, NULL, NULL)
    """, (veiculo_ativo, user_regular))
    checklist_id = cursor.lastrowid
    cursor.execute(
        "UPDATE fleet_vehicles SET status='em_viagem' WHERE id=%s",
        (veiculo_ativo,)
    )
    db.commit()   # commit pra outra conexao (scheduler) enxergar
    yield {
        "checklist_id": checklist_id,
        "vehicle_id":   veiculo_ativo,
        "user_id":      user_regular,
    }
    # Teardown: limpa TUDO que a fixture criou
    cursor.execute(
        "DELETE FROM fleet_reservations WHERE vehicle_id=%s AND solicitante_id=%s "
        "AND destino='teste'",
        (veiculo_ativo, user_regular)
    )
    cursor.execute("DELETE FROM fleet_checklists WHERE id=%s", (checklist_id,))
    cursor.execute("UPDATE fleet_vehicles SET status='ativo' WHERE id=%s", (veiculo_ativo,))
    db.commit()


@pytest.fixture
def checklist_devolvido(cursor, db, checklist_em_viagem):
    """Extende checklist_em_viagem pra status='devolvido' + veiculo
    aguardando_vistoria."""
    ck = checklist_em_viagem
    cursor.execute(
        "UPDATE fleet_checklists SET status='devolvido', data_retorno=CURDATE(), "
        "horario_retorno='17:00', km_retorno=10100 WHERE id=%s",
        (ck["checklist_id"],)
    )
    cursor.execute(
        "UPDATE fleet_vehicles SET status='aguardando_vistoria' WHERE id=%s",
        (ck["vehicle_id"],)
    )
    db.commit()
    return ck
