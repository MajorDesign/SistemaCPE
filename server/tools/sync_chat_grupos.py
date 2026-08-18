"""
sync_chat_grupos.py — one-shot pra popular retroativamente o server
'CPE TECNOLOGIA' com todos os users ativos + criar canal por grupo.

USO:
    E:/xampp/htdocs/SistemaCPE/server/.venv/Scripts/python.exe ^
      E:/xampp/htdocs/SistemaCPE/server/tools/sync_chat_grupos.py

    (--dry-run mostra o que faria sem gravar)

Idempotente — rodar N vezes tem mesmo efeito de rodar 1x. Baseado em
INSERT IGNORE e checagens de existencia. Nao apaga nada; so cria/inclui.
"""
import os
import sys
import argparse

# Bootstrap do venv/paths — permite rodar de qualquer cwd
HERE = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.dirname(HERE)
sys.path.insert(0, SERVER_DIR)

from database import get_db_or_404, get_chat_db_or_404
from services.chat_bootstrap import (
    CPE_CHAT_SERVER_ID,
    garantir_server_membro,
    garantir_canal_do_grupo,
    garantir_membro_canal,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Mostra o que faria sem gravar nada")
    args = ap.parse_args()

    print(f"CPE_CHAT_SERVER_ID = {CPE_CHAT_SERVER_ID}")
    if args.dry_run:
        print("*** DRY-RUN: nada sera gravado ***\n")

    # Confirma server existe
    chat = get_chat_db_or_404()
    c = chat.cursor(dictionary=True)
    c.execute("SELECT id, nome FROM chat_servers WHERE id=%s", (CPE_CHAT_SERVER_ID,))
    srv = c.fetchone()
    c.close(); chat.close()
    if not srv:
        print(f"ERRO: server id={CPE_CHAT_SERVER_ID} nao existe.")
        sys.exit(1)
    print(f"Server: '{srv['nome']}' (id={srv['id']})\n")

    # ---- Users ativos ----
    plus = get_db_or_404()
    p = plus.cursor(dictionary=True)
    p.execute("SELECT id, name, group_id FROM users WHERE is_active=1 ORDER BY id")
    users = p.fetchall() or []

    # ---- Grupos ----
    p.execute("SELECT id, name FROM cpe_grupo ORDER BY name")
    grupos = p.fetchall() or []
    p.close(); plus.close()

    print(f"USERS ativos: {len(users)}")
    print(f"GRUPOS: {len(grupos)}\n")

    # === FASE 1: server members ===
    print("=" * 60)
    print("FASE 1: adicionando users ao server")
    print("=" * 60)
    novos_server = 0
    for u in users:
        if args.dry_run:
            print(f"  [DRY] server_member <- user {u['id']} {u['name']!r}")
            continue
        if garantir_server_membro(u["id"]):
            novos_server += 1
    print(f"  Novos membros do server: {novos_server}\n"
          if not args.dry_run else "")

    # === FASE 2: criar canais por grupo ===
    print("=" * 60)
    print("FASE 2: criando canais por grupo")
    print("=" * 60)
    canais_por_grupo = {}
    novos_canais = 0
    for g in grupos:
        if args.dry_run:
            print(f"  [DRY] canal do grupo #{g['id']} '{g['name']}'")
            canais_por_grupo[g["id"]] = None
            continue
        cid = garantir_canal_do_grupo(g["id"], g["name"])
        canais_por_grupo[g["id"]] = cid
        if cid:
            novos_canais += 1  # inclui os que ja existiam (nao distingue —
                               # log ja separa "canal criado" vs nada)
    print(f"  Canais garantidos: {len(canais_por_grupo)}\n"
          if not args.dry_run else "")

    # === FASE 3: adicionar users aos canais dos seus grupos ===
    print("=" * 60)
    print("FASE 3: adicionando users aos canais dos grupos")
    print("=" * 60)
    novos_membros_canal = 0
    for u in users:
        gid = u["group_id"]
        if not gid:
            continue
        cid = canais_por_grupo.get(gid)
        if not cid:
            if args.dry_run:
                print(f"  [DRY] user {u['id']} {u['name']!r} -> canal do grupo {gid}")
            continue
        if args.dry_run:
            print(f"  [DRY] user {u['id']} {u['name']!r} -> canal #{cid} (grupo {gid})")
            continue
        if garantir_membro_canal(cid, u["id"]):
            novos_membros_canal += 1
    print(f"  Novos membros de canal: {novos_membros_canal}\n"
          if not args.dry_run else "")

    print("=" * 60)
    print("FIM")
    print("=" * 60)
    if args.dry_run:
        print("Reode SEM --dry-run pra aplicar.")


if __name__ == "__main__":
    main()
