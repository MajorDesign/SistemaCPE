"""
Importa o CSV "Backup Chamados 5.csv" para a tabela chamados_antigos.

Uso (na raiz do repo, com o venv ativado):
    python tools/import_chamados_antigos.py

O script:
  - Lê o .env do servidor para conexão MySQL
  - Lê o CSV em "Chamados antigos/Backup Chamados 5.csv"
  - Faz INSERT IGNORE em lotes de 500 linhas (preserva registros já importados
    pela chave única `trackid`).
  - Imprime resumo ao final.

Para reimportar do zero (caso queira limpar dados anteriores):
    DELETE FROM chamados_antigos;
    e depois rode novamente.
"""

from __future__ import annotations

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

# Força UTF-8 no stdout (Windows usa cp1252 por padrão e quebra com emojis)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Garante import do server/.env e mysql.connector
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=ROOT / "server" / ".env")
except Exception:
    pass

import mysql.connector

CSV_PATH = ROOT / "Chamados antigos" / "Backup Chamados 5.csv"
BATCH_SIZE = 500


def _parse_dt(s: str | None):
    if not s:
        return None
    s = s.strip().strip('"').strip()
    if not s or s in ("0", "0000-00-00", "0000-00-00 00:00:00"):
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _clean(s: str | None) -> str | None:
    if s is None:
        return None
    s = s.strip()
    return s or None


def _to_int(s: str | None):
    if not s:
        return None
    try:
        return int(str(s).strip().strip('"'))
    except (ValueError, TypeError):
        return None


def main():
    if not CSV_PATH.exists():
        print(f"❌ CSV não encontrado em: {CSV_PATH}")
        sys.exit(1)

    cfg = dict(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DB", "cpe_plus"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        charset="utf8mb4",
        autocommit=False,
    )

    print(f"🔌 Conectando em {cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['database']} ...")
    conn = mysql.connector.connect(**cfg)
    cur = conn.cursor()

    sql = """
        INSERT IGNORE INTO chamados_antigos
            (trackid, nome_status, email, solicitante, categoria, prioridade,
             assunto, aberto_em, primeira_resp, duracao_pri_resp,
             fechado_em, fechado_por, atribuido_a,
             mensagem, respondido_por, resposta, dh_resposta, created_at)
        VALUES (%s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, NOW())
    """

    total      = 0
    inseridos  = 0
    pulados    = 0
    erros      = 0
    batch: list[tuple] = []

    print(f"📂 Lendo {CSV_PATH.name} ...")
    with CSV_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            total += 1
            try:
                trackid = _clean(row.get("trackid"))
                if not trackid:
                    pulados += 1
                    continue
                params = (
                    trackid,
                    _clean(row.get("Nome_status")),
                    _clean(row.get("email")),
                    _clean(row.get("NAME")),
                    _clean(row.get("CATEGORIA")),
                    _clean(row.get("PRIORITY")),
                    _clean(row.get("SUBJECT")),
                    _parse_dt(row.get("DT")),
                    _parse_dt(row.get("FIRSTREPLY")),
                    _to_int(row.get("DURACAOPRIRESP")),
                    _parse_dt(row.get("CLOSEDAT")),
                    _clean(row.get("FechadoPor")),
                    _clean(row.get("Atribuido")),
                    _clean(row.get("message")),
                    _clean(row.get("Respondido_Por")),
                    _clean(row.get("RespostaS")),
                    _parse_dt(row.get("DH_Resposta")),
                )
                batch.append(params)
            except Exception as e:
                erros += 1
                if erros < 10:
                    print(f"  ⚠️  linha {total}: {e}")
                continue

            if len(batch) >= BATCH_SIZE:
                cur.executemany(sql, batch)
                inseridos += cur.rowcount
                conn.commit()
                batch.clear()
                if total % 5000 == 0:
                    print(f"  ... {total} linhas processadas")

    if batch:
        cur.executemany(sql, batch)
        inseridos += cur.rowcount
        conn.commit()

    cur.execute("SELECT COUNT(*) FROM chamados_antigos")
    total_na_tabela = cur.fetchone()[0]

    cur.close()
    conn.close()

    print("─" * 60)
    print(f"📊 Linhas lidas do CSV:      {total}")
    print(f"✅ INSERT executados:         {inseridos}   (já existentes foram ignorados)")
    print(f"⏭️  Linhas puladas (vazias): {pulados}")
    print(f"❌ Erros de parse:            {erros}")
    print(f"📦 Total na tabela agora:     {total_na_tabela}")
    print("─" * 60)
    print("Pronto. Os chamados antigos já podem ser consultados em /tickets.html.")


if __name__ == "__main__":
    main()
