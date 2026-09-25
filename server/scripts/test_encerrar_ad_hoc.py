"""Testa _encerrar_se_ad_hoc_e_vazio contra o banco local.

Cenarios:
  1. Sala ad-hoc com 2 dentro -> NAO encerra
  2. Sala ad-hoc com 1 dentro  -> ENCERRA (bug fix principal)
  3. Sala ad-hoc com 0 dentro  -> ENCERRA
  4. Sala agendada com 1 dentro -> NAO encerra (reuniao pode ter host esperando)
  5. Idempotencia: chamar 2x nao rebota encerrada_em (segunda chamada devolve False)

Roda com API PARADA. Cria salas fake, testa, deleta tudo.
"""
from __future__ import annotations
import os
import sys
import uuid
from datetime import datetime, timedelta

# Adiciona server/ ao path pra importar meetings.py
HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.dirname(HERE)
sys.path.insert(0, SERVER)

from routes.meetings import _encerrar_se_ad_hoc_e_vazio  # noqa: E402
from database import get_chat_db_or_404  # noqa: E402

FAIL = 0
PASS = 0


def check(label, condition, detail=""):
    global FAIL, PASS
    mark = "\x1b[32mOK \x1b[0m" if condition else "\x1b[31mFAIL\x1b[0m"
    print(f"  [{mark}] {label}{f' - {detail}' if detail else ''}")
    if condition:
        PASS += 1
    else:
        FAIL += 1


def _cria_sala(cur, code, criado_por=1):
    cur.execute(
        "INSERT INTO chat_meeting_rooms (codigo, nome, criado_por, criado_em) "
        "VALUES (%s, %s, %s, NOW())",
        (code, f"e2e-hangup-{code}", criado_por),
    )
    cur.execute("SELECT LAST_INSERT_ID()")
    return int(cur.fetchone()[0])


def _add_participant(cur, meeting_id, status="dentro"):
    peer = uuid.uuid4().hex[:32]
    cur.execute(
        "INSERT INTO chat_meeting_participants "
        "(meeting_id, peer_id, user_id, guest_name, status, entrou_em) "
        "VALUES (%s, %s, NULL, %s, %s, NOW())",
        (meeting_id, peer, f"guest-{peer[:6]}", status),
    )
    return peer


def _add_schedule(cur, meeting_id, host_id=1):
    cur.execute(
        "INSERT INTO chat_meeting_schedules "
        "(meeting_id, titulo, host_id, start_at, end_at) "
        "VALUES (%s, %s, %s, %s, %s)",
        (meeting_id, "e2e schedule", host_id,
         datetime.now(), datetime.now() + timedelta(hours=1)),
    )


def _cleanup(cur, meeting_id):
    cur.execute("DELETE FROM chat_meeting_schedules WHERE meeting_id=%s", (meeting_id,))
    cur.execute("DELETE FROM chat_meeting_participants WHERE meeting_id=%s", (meeting_id,))
    cur.execute("DELETE FROM chat_meeting_rooms WHERE id=%s", (meeting_id,))


def _encerrada_em(cur, meeting_id):
    cur.execute("SELECT encerrada_em FROM chat_meeting_rooms WHERE id=%s", (meeting_id,))
    row = cur.fetchone()
    return row[0] if row else None


def main():
    print("== test_encerrar_ad_hoc ==")
    conn = get_chat_db_or_404()
    cur = conn.cursor()

    salas = []
    try:
        # Cenario 1: ad-hoc com 2 dentro -> NAO encerra
        code1 = f"E2E1{uuid.uuid4().hex[:8]}".upper()
        mid1 = _cria_sala(cur, code1)
        _add_participant(cur, mid1, "dentro")
        _add_participant(cur, mid1, "dentro")
        conn.commit()
        salas.append(mid1)
        r1 = _encerrar_se_ad_hoc_e_vazio(cur, mid1)
        conn.commit()
        check("1. Ad-hoc + 2 dentro -> NAO encerra", r1 is False and _encerrada_em(cur, mid1) is None)

        # Cenario 2: ad-hoc com 1 dentro -> ENCERRA (bug fix)
        code2 = f"E2E2{uuid.uuid4().hex[:8]}".upper()
        mid2 = _cria_sala(cur, code2)
        _add_participant(cur, mid2, "dentro")
        conn.commit()
        salas.append(mid2)
        r2 = _encerrar_se_ad_hoc_e_vazio(cur, mid2)
        conn.commit()
        enc2 = _encerrada_em(cur, mid2)
        check("2. Ad-hoc + 1 dentro -> ENCERRA (bug fix)", r2 is True and enc2 is not None,
              f"encerrada_em={enc2}")

        # Cenario 3: ad-hoc com 0 dentro -> ENCERRA
        code3 = f"E2E3{uuid.uuid4().hex[:8]}".upper()
        mid3 = _cria_sala(cur, code3)
        conn.commit()
        salas.append(mid3)
        r3 = _encerrar_se_ad_hoc_e_vazio(cur, mid3)
        conn.commit()
        check("3. Ad-hoc + 0 dentro -> ENCERRA", r3 is True and _encerrada_em(cur, mid3) is not None)

        # Cenario 4: sala agendada com 1 dentro -> NAO encerra
        code4 = f"E2E4{uuid.uuid4().hex[:8]}".upper()
        mid4 = _cria_sala(cur, code4)
        _add_participant(cur, mid4, "dentro")
        _add_schedule(cur, mid4)
        conn.commit()
        salas.append(mid4)
        r4 = _encerrar_se_ad_hoc_e_vazio(cur, mid4)
        conn.commit()
        check("4. Agendada + 1 dentro -> NAO encerra", r4 is False and _encerrada_em(cur, mid4) is None)

        # Cenario 5: idempotencia -> segunda chamada em sala ja encerrada devolve False
        # (usa a sala 2 que ja foi encerrada acima)
        r5 = _encerrar_se_ad_hoc_e_vazio(cur, mid2)
        conn.commit()
        check("5. Idempotente: 2a chamada em sala encerrada -> False", r5 is False)

    finally:
        for mid in salas:
            _cleanup(cur, mid)
        conn.commit()
        cur.close()
        conn.close()

    print()
    print(f"resultado: {PASS} passou, {FAIL} falhou")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
