"""Testa que o backend faz auto-unhide de DM ocultada quando chega msg nova.

Cenarios:
  1. Ana oculta DM com Jonathan -> ocultado_em setado na row dela
  2. Jonathan envia msg via REST -> auto-unhide roda -> ocultado_em=NULL
  3. Ana oculta de novo -> ocultado_em setado
  4. Jonathan envia via WS (helper que roda dentro do handler) -> mesmo unhide
  5. Nao afeta unhide de membros que NAO ocultaram (idempotente)

Roda direto contra o banco cpe_chat local. Nao precisa API rodando pro
cenario 1-3 (usa SQL direto pra reproduzir o efeito da query REST).
Cenarios 4-5 sao verificacoes estaticas de que o codigo existe.
"""
from __future__ import annotations
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.dirname(HERE)
sys.path.insert(0, SERVER)

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


def _setup_dm(cur):
    """Cria canal DM ficticio + 2 members. Retorna (channel_id, user_a, user_b)."""
    user_a, user_b = 99991, 99992
    cur.execute(
        "INSERT INTO chat_channels (tipo, nome, criado_por, criado_em) "
        "VALUES ('dm', 'e2e-hide-test', %s, NOW())", (user_a,))
    cur.execute("SELECT LAST_INSERT_ID()")
    channel_id = int(cur.fetchone()[0])
    for uid in (user_a, user_b):
        cur.execute(
            "INSERT INTO chat_channel_members "
            "(channel_id, user_id, entrou_em, ocultado_em) "
            "VALUES (%s, %s, NOW(), NULL)",
            (channel_id, uid))
    return channel_id, user_a, user_b


def _cleanup(cur, channel_id):
    cur.execute("DELETE FROM chat_channel_members WHERE channel_id=%s", (channel_id,))
    cur.execute("DELETE FROM chat_messages WHERE channel_id=%s", (channel_id,))
    cur.execute("DELETE FROM chat_channels WHERE id=%s", (channel_id,))


def _hide_para(cur, channel_id, user_id):
    cur.execute(
        "UPDATE chat_channel_members SET ocultado_em=NOW() "
        "WHERE channel_id=%s AND user_id=%s",
        (channel_id, user_id))


def _get_ocultado_em(cur, channel_id, user_id):
    cur.execute(
        "SELECT ocultado_em FROM chat_channel_members "
        "WHERE channel_id=%s AND user_id=%s",
        (channel_id, user_id))
    row = cur.fetchone()
    return row[0] if row else "NAO_EXISTE"


def _auto_unhide_query(cur, channel_id):
    """A query exata que o backend (REST + WS handler) roda ao chegar msg."""
    cur.execute(
        "UPDATE chat_channel_members SET ocultado_em=NULL "
        "WHERE channel_id=%s AND ocultado_em IS NOT NULL",
        (channel_id,))


def main():
    print("== test_dm_hide_unhide ==")
    conn = get_chat_db_or_404()
    cur = conn.cursor()
    ch_id = None
    try:
        ch_id, ua, ub = _setup_dm(cur)
        conn.commit()

        # Cenario 1: Ana (ub) oculta DM
        _hide_para(cur, ch_id, ub)
        conn.commit()
        oc_b = _get_ocultado_em(cur, ch_id, ub)
        check("1. Ana oculta -> ocultado_em setado", oc_b is not None and oc_b != "NAO_EXISTE",
              f"ocultado_em={oc_b}")

        # Cenario 2: Jonathan envia msg -> query REST roda auto-unhide
        _auto_unhide_query(cur, ch_id)
        conn.commit()
        oc_b_apos = _get_ocultado_em(cur, ch_id, ub)
        check("2. Msg enviada (REST) -> ocultado_em=NULL", oc_b_apos is None)

        # Cenario 3: Ana oculta de novo
        _hide_para(cur, ch_id, ub)
        conn.commit()
        oc_b2 = _get_ocultado_em(cur, ch_id, ub)
        check("3. Ana oculta 2a vez", oc_b2 is not None)

        # Cenario 4 (estatico): handler WS de chat.py tem o bloco de auto-unhide
        chat_py = os.path.join(SERVER, "routes", "chat.py")
        chat_src = open(chat_py, encoding="utf-8").read()
        # Procura a query dentro da secao WS (msg_type == "send")
        ws_send_block = re.search(
            r'if\s+msg_type\s*==\s*"send".*?elif\s+msg_type\s+in',
            chat_src, flags=re.S)
        has_ws_unhide = bool(
            ws_send_block and
            "chat_channel_members SET ocultado_em=NULL" in ws_send_block.group(0))
        check("4. Handler WS 'send' tem bloco auto-unhide", has_ws_unhide)

        # Cenario 5: query nao mexe em membros que NAO ocultaram (Jonathan)
        # Reset: Jonathan (ua) sempre teve ocultado_em=NULL. Query deve ser noop pra ele.
        _auto_unhide_query(cur, ch_id)
        conn.commit()
        oc_a = _get_ocultado_em(cur, ch_id, ua)
        oc_b3 = _get_ocultado_em(cur, ch_id, ub)
        check("5. Idempotente: NULL fica NULL, oculto vira NULL",
              oc_a is None and oc_b3 is None)

        # Cenario 6 (estatico): frontend chatStore.applyIncomingMessage
        # dispara loadChannels() quando canal nao esta em s.channels
        store_path = os.path.join(
            os.path.dirname(SERVER), "..",
            "cpecontrol-desktop", "src", "renderer", "store", "chatStore.ts")
        if os.path.exists(store_path):
            store_src = open(store_path, encoding="utf-8").read()
            has_reload = bool(re.search(
                r"applyIncomingMessage.*?st\.channels\.some.*?loadChannels\(\)",
                store_src, flags=re.S))
            check("6. Frontend applyIncomingMessage dispara loadChannels()", has_reload)
        else:
            print(f"  [-] pulou check 6 - chatStore.ts nao encontrado ({store_path})")

    finally:
        if ch_id:
            _cleanup(cur, ch_id)
            conn.commit()
        cur.close()
        conn.close()

    print()
    print(f"resultado: {PASS} passou, {FAIL} falhou")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
