#!/bin/bash
# =============================================================
# Script de deploy: atualiza código + aplica migrations pendentes
# NÃO reinicia a API automaticamente — faça isso pelo iniciar_servidor.bat
#
# Uso: bash /e/xampp/htdocs/SistemaCPE/deploy.sh
# =============================================================

MYSQL="/e/xampp/mysql/bin/mysql"
REPO="/e/xampp/htdocs/SistemaCPE"
MIGRATIONS_DIR="$REPO/server/migrations"

# Carrega credenciais do .env do servidor (mesmo arquivo usado pela API)
ENV_FILE="$REPO/server/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "ERRO: $ENV_FILE nao encontrado. Crie o arquivo .env antes de rodar o deploy."
  exit 1
fi

DB=$(grep -E "^MYSQL_DB=" "$ENV_FILE" | head -1 | cut -d'=' -f2 | tr -d '"' | tr -d "'")
USER=$(grep -E "^MYSQL_USER=" "$ENV_FILE" | head -1 | cut -d'=' -f2 | tr -d '"' | tr -d "'")
PASS=$(grep -E "^MYSQL_PASSWORD=" "$ENV_FILE" | head -1 | cut -d'=' -f2 | tr -d '"' | tr -d "'")

if [ -z "$DB" ] || [ -z "$USER" ] || [ -z "$PASS" ]; then
  echo "ERRO: MYSQL_DB / MYSQL_USER / MYSQL_PASSWORD precisam estar em $ENV_FILE"
  exit 1
fi

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "============================================="
echo " CPE Deploy - $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================="

# ----------------------------------------------------------
# 1. Atualizar código
# ----------------------------------------------------------
echo ""
echo -e "${YELLOW}[1/2] Atualizando código do repositório...${NC}"
cd "$REPO"
git pull origin main
echo -e "${GREEN}✓ Código atualizado${NC}"

# ----------------------------------------------------------
# 2. Aplicar migrations pendentes
# ----------------------------------------------------------
echo ""
echo -e "${YELLOW}[2/2] Verificando migrations pendentes...${NC}"

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

for sql_file in $(ls "$MIGRATIONS_DIR"/*.sql 2>/dev/null | sort); do
  nome=$(basename "$sql_file")

  # Verifica se já foi aplicada
  aplicada=$("$MYSQL" -u "$USER" -p"$PASS" "$DB" -se \
    "SELECT COUNT(*) FROM _migrations_log WHERE nome='$nome';" 2>/dev/null)

  if [ "$aplicada" = "0" ]; then
    echo -n "  → Aplicando $nome ... "
    if "$MYSQL" -u "$USER" -p"$PASS" "$DB" < "$sql_file" 2>/dev/null; then
      "$MYSQL" -u "$USER" -p"$PASS" "$DB" -e \
        "INSERT IGNORE INTO _migrations_log (nome) VALUES ('$nome');" 2>/dev/null
      echo -e "${GREEN}✓${NC}"
      APLICADAS=$((APLICADAS + 1))
    else
      echo -e "${RED}✗ ERRO${NC}"
      ERROS=$((ERROS + 1))
    fi
  else
    echo "  · Já aplicada: $nome"
    PULADAS=$((PULADAS + 1))
  fi
done

# ----------------------------------------------------------
# Resumo
# ----------------------------------------------------------
echo ""
echo "============================================="
echo -e " Migrations aplicadas : ${GREEN}$APLICADAS${NC}"
echo -e " Já estavam ok        : $PULADAS"
if [ "$ERROS" -gt 0 ]; then
  echo -e " Erros                : ${RED}$ERROS${NC}"
fi
echo "============================================="
echo ""
echo -e "${YELLOW}⚠ Reinicie a API manualmente pelo iniciar_servidor.bat${NC}"
echo ""
