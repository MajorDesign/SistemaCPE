"""
lembrar_avaliacoes.py — one-shot pra notificar solicitantes que deixaram
de avaliar chamados finalizados (dentro do prazo de 7 dias).

USO:
    E:/xampp/htdocs/SistemaCPE/server/.venv/Scripts/python.exe ^
      E:/xampp/htdocs/SistemaCPE/server/tools/lembrar_avaliacoes.py

    Adicione --dry-run pra so ver o que faria, sem enviar nada.

O que faz:
  1. Consulta ticket_avaliacoes onde avaliado_em IS NULL e expira_em > NOW()
  2. Agrupa por solicitante_id
  3. Pra cada solicitante:
     a) Cria 1 notificacao in-app por ticket pendente
     b) Envia 1 email agrupando TODOS os tickets pendentes dele

Ideal rodar 1x quando quiser lembrar (nao e automatizado).
"""
import os
import sys
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.dirname(HERE)
sys.path.insert(0, SERVER_DIR)

from database import get_db_or_404
from services.email_service import email_lembrete_avaliacoes, enviar_email

try:
    from config import PUBLIC_BASE_URL
except Exception:
    PUBLIC_BASE_URL = "https://cpecontrol.cpetecnologia.com.br"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Mostra o que faria sem enviar nada")
    args = ap.parse_args()

    print(f"PUBLIC_BASE_URL = {PUBLIC_BASE_URL}")
    if args.dry_run:
        print("*** DRY-RUN: nada sera enviado ***\n")

    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)

    # Busca todas as pendentes dentro do prazo, com dados do ticket + user
    cur.execute("""
        SELECT
            a.id AS aval_id, a.ticket_id, a.solicitante_id, a.expira_em,
            t.numero, t.id_alfanumerica, t.assunto,
            u.name AS user_nome, u.email AS user_email
        FROM ticket_avaliacoes a
        JOIN tickets t ON t.id = a.ticket_id
        JOIN users u ON u.id = a.solicitante_id
        WHERE a.avaliado_em IS NULL
          AND a.expira_em > NOW()
          AND u.is_active = 1
        ORDER BY a.solicitante_id, a.expira_em
    """)
    rows = cur.fetchall() or []
    print(f"Pendentes de avaliacao dentro do prazo: {len(rows)}")

    # Agrupa por solicitante_id
    por_user: dict[int, dict] = {}
    for r in rows:
        uid = r["solicitante_id"]
        if uid not in por_user:
            por_user[uid] = {
                "nome": r["user_nome"],
                "email": r["user_email"],
                "tickets": [],
            }
        por_user[uid]["tickets"].append({
            "numero": r["id_alfanumerica"] or r["numero"],
            "assunto": r["assunto"],
            "expira_em": r["expira_em"].strftime("%d/%m/%Y") if r["expira_em"] else "",
            "ticket_id": r["ticket_id"],
        })

    print(f"Solicitantes unicos: {len(por_user)}\n")
    print("=" * 70)

    total_notif = 0
    total_email = 0
    total_email_falha = 0

    for uid, info in por_user.items():
        nome = info["nome"]
        email = info["email"]
        n = len(info["tickets"])
        print(f"\n[{uid}] {nome} — {n} ticket(s) pendente(s)")
        print(f"   → {email}")

        for t in info["tickets"]:
            print(f"      • {t['numero']} — {t['assunto'][:50]}"
                  f" (expira {t['expira_em']})")

        if args.dry_run:
            continue

        # 1) Cria N notificacoes in-app (1 por ticket)
        for t in info["tickets"]:
            try:
                cur.execute(
                    """INSERT INTO notificacoes
                         (ticket_id, usuario_id, tipo, mensagem, lido,
                          created_at, updated_at)
                       VALUES (%s, %s, %s, %s, 0, NOW(), NOW())""",
                    (
                        t["ticket_id"], uid, "avaliacao_pendente",
                        f"⭐ Chamado {t['numero']} aguarda sua avaliação — "
                        f"leva menos de 30 segundos.",
                    ),
                )
                total_notif += 1
            except Exception as e:
                print(f"      ⚠️ Falha notif ticket #{t['ticket_id']}: {e}")
        conn.commit()

        # 2) Envia 1 email agrupado
        if not email:
            print(f"   ⚠️ Sem email — pulou envio")
            continue
        try:
            subject, html = email_lembrete_avaliacoes(
                solicitante_nome=nome,
                tickets=info["tickets"],
                link_sistema=f"{PUBLIC_BASE_URL}/SistemaCPE/web/pages/tickets.html",
            )
            enviar_email(email, subject, html)
            total_email += 1
            print(f"   ✅ Email enviado")
        except Exception as e:
            total_email_falha += 1
            print(f"   ❌ Falha ao enviar email: {e}")

    cur.close()
    conn.close()

    print("\n" + "=" * 70)
    print(f"RESUMO:")
    print(f"  Solicitantes processados:    {len(por_user)}")
    print(f"  Notificacoes in-app criadas: {total_notif}")
    print(f"  Emails enviados com sucesso: {total_email}")
    if total_email_falha:
        print(f"  Emails com falha:            {total_email_falha}")


if __name__ == "__main__":
    main()
