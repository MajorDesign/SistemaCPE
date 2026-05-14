"""
sync_staging.py — Copia o banco de produção (CPEDC22) para um banco staging local.

Uso:
    server/.venv/Scripts/python.exe tools/sync_staging.py

O que faz:
  1. Conecta ao MySQL de PRODUÇÃO em 172.16.0.11:3306
  2. Lê todas as tabelas e dados
  3. Recria tudo no banco LOCAL cpe_plus_staging (apaga e reimporta)

Pré-requisito:
  - MySQL de produção acessível nesta máquina (mesma rede que o CPEDC22)
  - Se a conexão falhar, veja a seção "ACESSO REMOTO" abaixo

ACESSO REMOTO (caso o MySQL do CPEDC22 não aceite conexões externas):
  No CPEDC22, execute uma vez no MySQL (como root):
      CREATE USER IF NOT EXISTS 'cpe_sync'@'172.16.12.%'
          IDENTIFIED BY 'SyncCpe@2026';
      GRANT SELECT ON cpe_plus.* TO 'cpe_sync'@'172.16.12.%';
      FLUSH PRIVILEGES;
  Depois ajuste PROD_USER/PROD_PASSWORD abaixo (ou via variáveis de ambiente).
"""
from __future__ import annotations
import os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=ROOT / "server" / ".env")
except Exception:
    pass

import mysql.connector
from mysql.connector import Error as MySQLError

# ─── Configuração de produção ────────────────────────────────────────────────
PROD_HOST     = os.getenv("PROD_MYSQL_HOST",     "172.16.0.11")
PROD_PORT     = int(os.getenv("PROD_MYSQL_PORT", "3306"))
PROD_DB       = os.getenv("PROD_MYSQL_DB",       "cpe_plus")
PROD_USER     = os.getenv("PROD_MYSQL_USER",     os.getenv("MYSQL_USER", "root"))
PROD_PASSWORD = os.getenv("PROD_MYSQL_PASSWORD", os.getenv("MYSQL_PASSWORD", ""))

# ─── Configuração local (staging) ────────────────────────────────────────────
LOCAL_HOST     = os.getenv("MYSQL_HOST",     "127.0.0.1")
LOCAL_PORT     = int(os.getenv("MYSQL_PORT", "3306"))
LOCAL_DB       = os.getenv("STAGING_DB",     "cpe_plus_staging")
LOCAL_USER     = os.getenv("MYSQL_USER",     "root")
LOCAL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

# Tabelas que NÃO devem ser copiadas (dados exclusivos do ambiente de produção)
TABELAS_IGNORADAS: set[str] = set()


def _conectar(host, port, database, user, password, label):
    try:
        conn = mysql.connector.connect(
            host=host, port=port, database=database,
            user=user, password=password,
            charset="utf8mb4", use_pure=True,
            connection_timeout=10,
        )
        print(f"  [OK] {label} conectado ({host}:{port}/{database})")
        return conn
    except MySQLError as e:
        print(f"  [ERRO] Falha ao conectar em {label}: {e}")
        return None


def _listar_tabelas(cur) -> list[str]:
    cur.execute("SHOW TABLES")
    return [row[0] for row in cur.fetchall()
            if row[0] not in TABELAS_IGNORADAS]


def _create_statement(cur, tabela: str) -> str:
    cur.execute(f"SHOW CREATE TABLE `{tabela}`")
    return cur.fetchone()[1]


def _escape_val(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (bytes, bytearray)):
        return "0x" + v.hex()
    if hasattr(v, "strftime"):
        return "'" + v.strftime("%Y-%m-%d %H:%M:%S") + "'"
    s = str(v)
    s = s.replace("\\", "\\\\").replace("'", "\\'")
    s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")
    s = s.replace("\x00", "\\0")
    return "'" + s + "'"


def _copiar_tabela(cur_prod, cur_local, tabela: str) -> int:
    cur_prod.execute(f"SELECT * FROM `{tabela}`")
    rows = cur_prod.fetchall()
    if not rows:
        return 0

    cols = [c[0] for c in cur_prod.description]
    cols_sql = ", ".join(f"`{c}`" for c in cols)

    BATCH = 500
    total = 0
    for i in range(0, len(rows), BATCH):
        lote = rows[i:i + BATCH]
        vals = []
        for row in lote:
            escaped = [_escape_val(v) for v in row]
            vals.append("(" + ", ".join(escaped) + ")")
        sql = (f"INSERT INTO `{tabela}` ({cols_sql}) VALUES\n"
               + ",\n".join(vals) + ";")
        cur_local.execute(sql)
        total += len(lote)

    return total


def main():
    t0 = time.time()
    print("\n" + "=" * 60)
    print("  CPE Control — Sync Produção → Staging")
    print("=" * 60)
    print(f"\n  Origem : {PROD_USER}@{PROD_HOST}:{PROD_PORT}/{PROD_DB}")
    print(f"  Destino: {LOCAL_USER}@{LOCAL_HOST}:{LOCAL_PORT}/{LOCAL_DB}\n")

    # ── Conectar ao banco de PRODUÇÃO ────────────────────────────
    prod = _conectar(PROD_HOST, PROD_PORT, PROD_DB,
                     PROD_USER, PROD_PASSWORD, "producao")
    if not prod:
        print("\n[!] Nao foi possivel conectar ao banco de producao.")
        print("    Verifique a conectividade com CPEDC22 (ping 172.16.0.11)")
        print("    e as permissoes de acesso remoto do MySQL.\n")
        print("    Consulte a secao ACESSO REMOTO no cabecalho deste script.")
        sys.exit(1)

    # ── Criar/preparar banco STAGING local ───────────────────────
    local_sem_db = mysql.connector.connect(
        host=LOCAL_HOST, port=LOCAL_PORT,
        user=LOCAL_USER, password=LOCAL_PASSWORD,
        charset="utf8mb4", use_pure=True,
    )
    cur_admin = local_sem_db.cursor()
    cur_admin.execute(
        f"CREATE DATABASE IF NOT EXISTS `{LOCAL_DB}` "
        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    local_sem_db.commit()
    cur_admin.close()
    local_sem_db.close()

    local = _conectar(LOCAL_HOST, LOCAL_PORT, LOCAL_DB,
                      LOCAL_USER, LOCAL_PASSWORD, "staging local")
    if not local:
        prod.close()
        sys.exit(1)

    cur_prod  = prod.cursor()
    cur_local = local.cursor()

    # ── Listar tabelas de produção ────────────────────────────────
    tabelas = _listar_tabelas(cur_prod)
    print(f"\n  {len(tabelas)} tabela(s) encontrada(s) em producao\n")

    cur_local.execute("SET FOREIGN_KEY_CHECKS = 0")
    cur_local.execute("SET NAMES utf8mb4")

    copiadas = 0
    falhas   = []

    for tabela in tabelas:
        try:
            # Recriar tabela no staging
            create_sql = _create_statement(cur_prod, tabela)
            cur_local.execute(f"DROP TABLE IF EXISTS `{tabela}`")
            cur_local.execute(create_sql)

            # Copiar dados
            n = _copiar_tabela(cur_prod, cur_local, tabela)
            local.commit()

            print(f"  {tabela:<45} {n:>6} linhas")
            copiadas += 1

        except Exception as e:
            local.rollback()
            falhas.append((tabela, str(e)))
            print(f"  {tabela:<45} [FALHA] {e}")

    cur_local.execute("SET FOREIGN_KEY_CHECKS = 1")
    local.commit()

    cur_prod.close();  prod.close()
    cur_local.close(); local.close()

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  Concluido em {elapsed:.1f}s")
    print(f"  Tabelas copiadas : {copiadas}/{len(tabelas)}")
    if falhas:
        print(f"  Falhas           : {len(falhas)}")
        for t, e in falhas:
            print(f"    - {t}: {e}")
    print(f"\n  Banco staging pronto: {LOCAL_DB}")
    print(f"  Para usar: server/iniciar_staging.bat")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
