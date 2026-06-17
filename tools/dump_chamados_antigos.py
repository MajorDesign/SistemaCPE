"""
Gera um dump SQL da tabela `chamados_antigos` para importar em outro ambiente
(ex.: servidor de produção) sem precisar copiar o CSV original.

Uso (raiz do repo):
    server/.venv/Scripts/python.exe tools/dump_chamados_antigos.py

Saída: "Chamados antigos/dump_chamados_antigos.sql"

Pra importar em produção:
    1) Aplicar a migration 033 (cria a tabela vazia)
    2) phpMyAdmin → banco cpe_plus → aba Importar → escolher esse .sql
       (ou via CLI: mysql -u root -p cpe_plus < dump_chamados_antigos.sql)
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=ROOT / "server" / ".env")
except Exception:
    pass

import mysql.connector

OUT = ROOT / "Chamados antigos" / "dump_chamados_antigos.sql"
OUT.parent.mkdir(exist_ok=True)


def escape_sql(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    if hasattr(value, "strftime"):
        return "'" + value.strftime("%Y-%m-%d %H:%M:%S") + "'"
    s = str(value)
    s = s.replace("\\", "\\\\").replace("'", "\\'")
    s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")
    return "'" + s + "'"


def main():
    conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DB", "cpe_plus"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        charset="utf8mb4",
    )
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM chamados_antigos")
    total = cur.fetchone()[0]
    print(f"📦 Exportando {total} registros...")

    cur.execute("SELECT * FROM chamados_antigos ORDER BY id")
    cols = [c[0] for c in cur.description]
    cols_sql = ", ".join(f"`{c}`" for c in cols)

    BATCH = 200
    escritos = 0

    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        f.write("-- Dump da tabela chamados_antigos\n")
        f.write("-- IMPORTANTE: aplique a migration 033 ANTES de rodar este arquivo.\n")
        f.write("SET NAMES utf8mb4;\n")
        f.write("SET FOREIGN_KEY_CHECKS=0;\n")
        f.write("TRUNCATE TABLE `chamados_antigos`;\n\n")

        while True:
            rows = cur.fetchmany(BATCH)
            if not rows:
                break
            vals = []
            for r in rows:
                esc = [escape_sql(v) for v in r]
                vals.append("(" + ",".join(esc) + ")")
            f.write(f"INSERT INTO `chamados_antigos` ({cols_sql}) VALUES\n")
            f.write(",\n".join(vals))
            f.write(";\n\n")
            escritos += len(rows)
            if escritos % 5000 == 0:
                print(f"  ... {escritos} registros")

        f.write("SET FOREIGN_KEY_CHECKS=1;\n")

    cur.close()
    conn.close()

    size_mb = OUT.stat().st_size / 1024 / 1024
    print(f"✅ Pronto: {OUT}")
    print(f"   {escritos} registros, {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
