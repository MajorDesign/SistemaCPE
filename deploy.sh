#!/bin/bash
# =============================================================
# deploy.sh — git pull + aplicar migrations no banco DEV.
#
# Para migrations em STAGING (sem git pull):
#   bash apply_migrations.sh server/.env.staging
#
# NÃO reinicia a API automaticamente — faça isso pelo CPE Control.bat.
# =============================================================

REPO="$(cd "$(dirname "$0")" && pwd)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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
# 2. Aplicar migrations no banco DEV
# ----------------------------------------------------------
echo ""
echo -e "${YELLOW}[2/2] Verificando migrations pendentes...${NC}"
bash "$REPO/apply_migrations.sh" server/.env

echo ""
echo -e "${YELLOW}⚠ Reinicie a API manualmente pelo CPE Control.bat (opção [3] Reiniciar)${NC}"
echo ""
