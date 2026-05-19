#!/bin/bash
# =============================================================
# apply_migrations.sh — Aplica migrations SQL pendentes em um banco.
#
# Uso:
#   bash apply_migrations.sh [server/.env]              # default: .env (dev)
#   bash apply_migrations.sh server/.env.staging        # staging local
#
# O que faz:
#   1. Lê MYSQL_DB / MYSQL_USER / MYSQL_PASSWORD do .env informado
#   2. Garante que a tabela _migrations_log existe
#   3. Roda cada server/migrations/*.sql que ainda não está no log
# =============================================================

# Detecta MySQL local (xampp Windows vs Linux padrão)
if [ -x "/e/xampp/mysql/bin/mysql" ]; then
  MYSQL="/e/xampp/mysql/bin/mysql"
elif [ -x "/c/xampp/mysql/bin/mysql" ]; then
  MYSQL="/c/xampp/mysql/bin/mysql"
else
  MYSQL="mysql"
fi

REPO="$(cd "$(dirname "$0")" && pwd)"
MIGRATIONS_DIR="$REPO/server/migrations"

ENV_FILE_REL="${1:-server/.env}"
ENV_FILE="$REPO/$ENV_FILE_REL"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERRO: $ENV_FILE nao encontrado."
  exit 1
fi

DB=$(grep -E "^MYSQL_DB="       "$ENV_FILE" | head -1 | cut -d'=' -f2- | tr -d '"' | tr -d "'")
USER=$(grep -E "^MYSQL_USER="   "$ENV_FILE" | head -1 | cut -d'=' -f2- | tr -d '"' | tr -d "'")
PASS=$(grep -E "^MYSQL_PASSWORD=" "$ENV_FILE" | head -1 | cut -d'=' -f2- | tr -d '"' | tr -d "'")

if [ -z "$DB" ] || [ -z "$USER" ]; then
  echo "ERRO: MYSQL_DB / MYSQL_USER precisam estar definidos em $ENV_FILE"
  exit 1
fi

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "============================================="
echo " Aplicando migrations em: $DB"
echo " Arquivo de env         : $ENV_FILE_REL"
echo "============================================="

# Garante que a tabela de controle existe
"$MYSQL" -u "$USER" -p"$PASS" "$DB" -e "
  CREATE TABLE IF NOT EXISTS _migrations_log (
    nome VARCHAR(100) PRIMARY KEY,
    aplicada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  ) ENGINE=InnoDB;
" 2>/dev/null

APLICADAS=0
PULADAS=0
ERROS=0

# Só aceita arquivos com padrão NNN_*.sql (migrations numeradas).
# Qualquer outro .sql na pasta (scripts manuais, resets, dumps) é
# ignorado de proposito — esses não devem ser aplicados automaticamente.
for sql_file in $(ls "$MIGRATIONS_DIR"/[0-9][0-9][0-9]_*.sql 2>/dev/null | sort); do
  nome=$(basename "$sql_file")

  aplicada=$("$MYSQL" -u "$USER" -p"$PASS" "$DB" -se \
    "SELECT COUNT(*) FROM _migrations_log WHERE nome='$nome';" 2>/dev/null)

  if [ "$aplicada" = "0" ]; then
    echo -n "  -> Aplicando $nome ... "
    if "$MYSQL" -u "$USER" -p"$PASS" "$DB" < "$sql_file" 2>/dev/null; then
      "$MYSQL" -u "$USER" -p"$PASS" "$DB" -e \
        "INSERT IGNORE INTO _migrations_log (nome) VALUES ('$nome');" 2>/dev/null
      echo -e "${GREEN}OK${NC}"
      APLICADAS=$((APLICADAS + 1))
    else
      echo -e "${RED}ERRO${NC}"
      ERROS=$((ERROS + 1))
    fi
  else
    PULADAS=$((PULADAS + 1))
  fi
done

echo ""
echo "============================================="
echo -e " Aplicadas      : ${GREEN}$APLICADAS${NC}"
echo -e " Ja estavam ok  : $PULADAS"
if [ "$ERROS" -gt 0 ]; then
  echo -e " Erros          : ${RED}$ERROS${NC}"
  exit 1
fi
echo "============================================="
exit 0
