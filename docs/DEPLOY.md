# Deploy

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
