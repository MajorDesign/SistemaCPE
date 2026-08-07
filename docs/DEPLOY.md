# Deploy

## Setup de máquina nova (ou desatualizada há muito tempo)

Ordem obrigatória. Pular passos causa problemas sutis depois.

### 1. Pré-requisitos de sistema

- **Python 3.11** — versão RÍGIDA. 3.12/3.13/3.14 quebram na instalação por causa do `pydantic-core` (ver `docs/GOTCHAS.md#python-311-é-requisito-rígido`). Instala:
  ```bash
  winget install --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
  py -0     # confirma "3.11" na lista
  ```
- **Git for Windows** (com Git Bash).
- **XAMPP** com MariaDB 10.4+ rodando (porta 3306).
- **MySQL client acessível**: `c:/xampp/mysql/bin/mysql.exe`.

### 2. Repositório

```bash
cd c:/xampp/htdocs/SistemaCPE
git fetch origin
git status                            # se houver mudanças locais, stash antes
git stash push -m "wip antes de update" 2>/dev/null
git pull origin dev
git stash pop 2>/dev/null || true     # reaplica se stashou
```

### 3. Banco de dados

Se a máquina ficou muito tempo sem uso, o schema local está desatualizado. Reset com dump fresco:

```bash
# Backup do estado atual (por segurança)
mkdir -p backups
"c:/xampp/mysql/bin/mysqldump.exe" -u root cpe_plus > "backups/local_pre_update_$(date +%Y%m%d_%H%M%S).sql"

# Drop + reimport do dump do repo
"c:/xampp/mysql/bin/mysql.exe" -u root -e "DROP DATABASE IF EXISTS cpe_plus; CREATE DATABASE cpe_plus CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
"c:/xampp/mysql/bin/mysql.exe" -u root cpe_plus < cpe_plus.sql

# Cria _migrations_log e marca as NÃO-chat como aplicadas (schema já no dump)
"c:/xampp/mysql/bin/mysql.exe" -u root cpe_plus -e "CREATE TABLE IF NOT EXISTS _migrations_log (nome VARCHAR(100) PRIMARY KEY, aplicada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB;"

# Marca todas EXCETO as de chat (056-064, 066-067, 078-079) como aplicadas
VALUES=""; for f in server/migrations/[0-9][0-9][0-9]_*.sql; do
  name=$(basename "$f")
  case "$name" in 056_*|057_*|058_*|059_*|060_*|061_*|062_*|063_*|064_*|066_*|067_*|078_*|079_*) continue ;; esac
  VALUES="$VALUES('$name'),"
done; VALUES="${VALUES%,}"
"c:/xampp/mysql/bin/mysql.exe" -u root cpe_plus -e "INSERT IGNORE INTO _migrations_log (nome) VALUES $VALUES;"

# Roda as migrations de cpe_chat (criam o database do zero)
for f in server/migrations/056_*.sql server/migrations/057_*.sql server/migrations/058_*.sql \
         server/migrations/059_*.sql server/migrations/060_*.sql server/migrations/061_*.sql \
         server/migrations/062_*.sql server/migrations/063_*.sql server/migrations/064_*.sql \
         server/migrations/066_*.sql server/migrations/067_*.sql server/migrations/078_*.sql \
         server/migrations/079_*.sql; do
  name=$(basename "$f")
  "c:/xampp/mysql/bin/mysql.exe" -u root cpe_plus < "$f" \
    && "c:/xampp/mysql/bin/mysql.exe" -u root cpe_plus -e "INSERT IGNORE INTO _migrations_log (nome) VALUES ('$name');"
done
```

⚠️ **Se o MySQL local NÃO tem senha em root**, o `apply_migrations.sh` trava — por isso rodamos os comandos direto acima. Ver `docs/GOTCHAS.md#apply_migrations-sh-trava`.

### 4. Virtualenv Python

```bash
# Se existir venv em outra versão de Python, apaga
[ -d server/.venv ] && mv server/.venv server/.venv.old

py -3.11 -m venv server/.venv
server/.venv/Scripts/python.exe --version     # deve ser 3.11.x
server/.venv/Scripts/python.exe -m pip install --upgrade pip
server/.venv/Scripts/python.exe -m pip install -r server/requirements.txt

# Depois de confirmar que instalou tudo:
rm -rf server/.venv.old
```

### 5. Arquivo `.env`

Compare com `server/.env.example` — hoje tem 40+ chaves (integrações opcionais: SMTP, Carbonio, Clicksign, Gemini, Mikrotik, Omada, Cloudflare TURN, etc). Copiar do env da empresa. Se faltar, o servidor sobe mas com essas integrações desativadas — só quebra quando você chamar a feature específica.

```bash
grep -E "^[A-Z_]+=" server/.env.example | cut -d= -f1 | sort > /tmp/example_keys.txt
grep -E "^[A-Z_]+=" server/.env         | cut -d= -f1 | sort > /tmp/local_keys.txt
comm -23 /tmp/example_keys.txt /tmp/local_keys.txt    # lista o que falta
```

### 6. Smoke test

```bash
cd server
.venv/Scripts/python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000 --log-level info &
sleep 8
curl -s http://127.0.0.1:8000/health
# esperado: {"status":"ok","api":"CPE Control API","version":"2.0.0",...,"database":"✅ OK"}

# Para parar
"c:/Windows/System32/taskkill.exe" //F //IM python.exe
```

Se `/health` responder 200 e log mostrar `✅ TODOS OS ROUTERS REGISTRADOS!`, ambiente OK pra codar.

---

## Fluxo padrão (dev → prod)

1. Trabalha na branch `dev`
2. Commit
3. `git checkout main && git merge --no-ff dev && git push origin main && git checkout dev`
4. WinRM no CPEDC22: `git pull` + `apply_migrations.sh` + `Restart-Service CPEControlAPI`
5. Smoke: `/health` deve dar 200

**Nunca commit em `main` direto.** Sempre trabalhar em `dev` e mergear.

## Commit local

```bash
cd c:/xampp/htdocs/SistemaCPE
git branch --show-current    # confere que está em dev
git add <arquivos_especificos>   # NUNCA git add -A
git status --short           # revisa antes
git commit -m "$(cat <<'EOF'
tipo(escopo): descricao curta

Detalhes do que mudou.
Motivo se relevante.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

**Não incluir no commit:**
- `.claude/settings.local.json` (permissões locais minhas)
- `web/favicon-opcoes/` (rascunhos)
- `server/.venv/` (já no .gitignore)
- `server/.env` / `server/.env.staging` (credenciais)
- `server/__pycache__/`

**Pre-commit hook:** roda `ruff check` só em `.py` — pega F821/F401/sintaxe. Se falhar, corrige e re-commit (**nunca** `--no-verify`).

## Merge pra main + push

```bash
cd c:/xampp/htdocs/SistemaCPE
git push origin dev
git checkout main
git merge --no-ff dev -m "Merge dev: <descricao>"
git push origin main
git checkout dev             # SEMPRE voltar pra dev
git branch --show-current    # confere
```

## Deploy remoto CPEDC22

**Requer WinRM habilitado** (já está). PowerShell:

```powershell
Invoke-Command -ComputerName CPEDC22 -ScriptBlock {
  Set-Location 'E:\xampp\htdocs\SistemaCPE'

  # 1. Puxa código
  & git pull origin main
  & git log --oneline -1                                    # confere commit

  # 2. Aplica migrations pendentes (se houver)
  $bash = 'C:\Program Files\Git\bin\bash.exe'
  & $bash 'E:\xampp\htdocs\SistemaCPE\apply_migrations.sh' 'server/.env'

  # 3. Reinicia serviço (só se o backend mudou)
  Restart-Service -Name CPEControlAPI -Force
  Start-Sleep -Seconds 8

  # 4. Smoke
  Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing -TimeoutSec 8
}
```

**Quando pular o restart:** se só arquivos `web/*.html`, `web/assests/*` mudaram — frontend puro, Caddy serve direto. Só o navegador precisa de Ctrl+F5.

## Cache-buster (não pular)

`nav.js`, `config.js`, `page-guard.js` são referenciados por ~15 HTMLs com `?v=AAAA-MM-DD`. Quando qualquer um deles mudar, **bumpar a data em todas as ocorrências** — Cloudflare cacheia agressivo e serve versão antiga por horas se a URL não mudar.

Comando pra bumpar em massa (ajusta a data):
```bash
cd c:/xampp/htdocs/SistemaCPE
OLD="2026-08-04"
NEW="$(date +%Y-%m-%d)"
for f in web/pages/*.html web/*.html; do
  [ -f "$f" ] && sed -i "s|?v=$OLD|?v=$NEW|g" "$f"
done
git diff --stat web/
```

Ver `docs/CONVENCOES.md#cache-buster` pra detalhes.

## Migrations SQL

**Formato:** `server/migrations/NNN_descricao_curta.sql` — NNN = próximo número livre (últimas foram 082, 083, …).

**Regras:**
- **Idempotente:** `CREATE TABLE IF NOT EXISTS`, `INSERT … ON DUPLICATE KEY UPDATE`
- **MariaDB 10.4:** `TIMESTAMP NULL DEFAULT NULL` (explícito) — sem `DEFAULT NULL` sozinho quebra
- **Sempre com `use_pure=True`** implicitamente (o script `apply_migrations.sh` passa o `.env` que já configura)
- Loga em `_migrations_log` (tabela criada automaticamente). Duas vezes o mesmo NNN = ignora.

**Aplicar manualmente:**
```bash
# dev
bash apply_migrations.sh server/.env

# staging local (opção [10] do CPE Control.bat faz o mesmo)
bash apply_migrations.sh server/.env.staging

# prod (via WinRM dentro do CPEDC22)
bash E:\xampp\htdocs\SistemaCPE\apply_migrations.sh server/.env
```

**Se aparece "ERRO" em migrations antigas (059, 062, 063…):** normal — várias já foram parcialmente aplicadas em snapshots antigos. Só falha quando o próprio schema já tem o que ela quer criar. Verificar caso a caso; geralmente ignora.

## Dados em prod (UPDATE / DELETE manual)

Regra: **sempre dry-run SELECT primeiro**, mostra ao user, executa em transação.

```powershell
Invoke-Command -ComputerName CPEDC22 -ScriptBlock {
  $sql = @'
START TRANSACTION;

-- 1. Dry-run: quantos registros vão ser afetados?
SELECT COUNT(*) FROM tabela WHERE condicao;

-- 2. Confirma no output antes de commit
UPDATE tabela SET campo = valor WHERE condicao;
SELECT ROW_COUNT();

-- Se tudo OK:
COMMIT;
-- Se algo errado:
-- ROLLBACK;
'@
  $sql | & 'E:\xampp\mysql\bin\mysql.exe' -uroot -pCpe@7482 cpe_plus
}
```

**Nunca** executar UPDATE/DELETE sem WHERE. **Nunca** rodar `DROP TABLE` em prod sem múltiplo double-check.

## Painel local: CPE Control.bat

Menu interativo pra dev/staging local. Opções principais:

| Opção | O que faz |
|---|---|
| [1] | Iniciar API Dev (8000) |
| [2] | Parar API Dev |
| [3] | Reiniciar API Dev |
| [4] | Deploy Dev (git pull + migrations) |
| [5] | Deploy + Reiniciar Dev |
| [6] | Iniciar API Staging (8001) |
| [7] | Parar API Staging |
| [8] | Reiniciar API Staging |
| [9] | Sincronizar prod → staging (dump + restore) |
| [10] | Aplicar migrations no Staging |
| [11] | Verificar/Iniciar/Reiniciar Caddy |
| [12] | Verificar/Iniciar/Reiniciar Cloudflared |

Sem WinRM aqui — [11]/[12] só valem se você **estiver no CPEDC22**. No PC do dev os checks retornam MISSING.

## Rollback

**Código:**
```powershell
Invoke-Command -ComputerName CPEDC22 -ScriptBlock {
  Set-Location 'E:\xampp\htdocs\SistemaCPE'
  & git log --oneline -5
  # anote o commit anterior ao problemático (ex: XXXXX)
  & git reset --hard XXXXX
  Restart-Service -Name CPEControlAPI -Force
}
```
⚠️ `--hard` descarta commits — só faz se tem certeza. Depois, no dev, precisa `git reset --hard origin/main` também pra sincronizar.

**Banco:**
- Migrations não têm rollback automático.
- Backup diário do MySQL fica em `\\CPEDC22\backups\` (verificar politica — task memory diz que ainda tá pendente automação).
- Restore via `mysql -uroot -pXXX cpe_plus < backup.sql` (destrutivo — dropa e recria).

## Erros comuns no deploy

| Sintoma | Causa | Fix |
|---|---|---|
| `/health` demora 8s+ pra responder após restart | uvicorn subindo | espera mais 10s |
| `/health` 500 "database" | MySQL não subiu ou senha errada | check `.env` MYSQL_* e serviço MariaDB |
| Push rejeita: `non-fast-forward` | main mudou em outro lugar | `git pull origin main --rebase` antes |
| Pre-commit ruff falha | erro real de F821/F401 | corrige, re-add, re-commit — nunca `--no-verify` |
| WinRM `Test-WSMan` retorna erro | credencial expirou / firewall | tenta por IP `172.16.1.10` em vez de nome |
| Frontend não atualiza no browser | cache CDN | bump `?v=…` E Ctrl+F5 |
| Reserva de veículo canceladas todas junto | job_cleanup rodou após alteração | ver `docs/GOTCHAS.md#alteracoes-em-prazos-fleet` |

## Autorização por escopo

| Escopo | Precisa aprovação explícita? |
|---|---|
| Editar dev local | não |
| Rodar script que modifica DB dev local | não (mas cuidado) |
| Commit em `dev` | **sim** |
| Merge `dev → main` + push | **sim** |
| `git pull` no CPEDC22 | **sim** (afeta prod) |
| `Restart-Service CPEControlAPI` | **sim** (~10s de downtime) |
| UPDATE/DELETE em prod | **sim** (dry-run primeiro) |
| Aplicar migration em prod | **sim** (mostra o SQL antes) |
