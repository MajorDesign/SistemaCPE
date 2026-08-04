# AGENTS.md — Guia pra IA / dev novo neste repo

> Este arquivo é a **primeira coisa** a ler. Leia-o inteiro (5 min).
> Todo o resto é referência sob demanda.

## O que é este sistema

**CPE Control** é o sistema interno da CPE Tecnologia — plataforma monolítica web que consolida vários módulos operacionais da empresa:
tickets de suporte, frota de veículos, agendamento comercial, chat interno com reuniões, tarefas em quadros kanban, contratos, cofre de senhas, controle de inventário TI e celulares corporativos, recepção de visitantes, gestão de usuários/grupos/permissões, entre outros.

- **URL pública:** https://cpecontrol.cpetecnologia.com.br
- **Repo GitHub:** `MajorDesign/SistemaCPE`
- **Branch principal:** `main` (deploy) — trabalho fica em `dev`
- **Servidor prod:** `CPEDC22` (Windows Server, disco E:, tudo rodando como serviço Windows)

## Stack

- **Backend:** Python 3.11 + FastAPI + Uvicorn + SQLAlchemy (core) + mysql-connector-python
- **Banco:** MariaDB 10.4 (2 databases: `cpe_plus` [principal] + `cpe_chat` [reuniões/chat])
- **Frontend:** HTML/CSS/JS puro (sem framework), Bootstrap 5 pra layout, Bootstrap Icons
- **Proxy:** Caddy → Cloudflare Tunnel (sem NAT porta 80/443)
- **Realtime:** WebSocket nativo (`/api/meetings/ws`, `/api/chat/ws`) + polling curto pra notificações
- **WebRTC mesh (P2P):** reuniões até ~8 pessoas sem SFU

## Estrutura de pastas

```
server/
  app.py              ← boot do FastAPI + alguns endpoints legados (users, groups, tickets, etc.)
  config.py           ← env vars centralizadas (PUBLIC_BASE_URL, MYSQL_*, JWT_*)
  database.py         ← conexão MySQL (get_db_connection, get_chat_db_connection)
  security.py         ← tokens de sessão (parse_session_token, make_session_token)
  utils.py            ← hash de senha, helpers
  routes/*.py         ← 35 routers modulares (fleet, comercial, chat, meetings, tasks, ...)
  services/*.py       ← lógica agendada + emails + integrações (fleet_scheduler, email_service, ...)
  migrations/*.sql    ← 87+ migrations numeradas — aplica com apply_migrations.sh
  tests/*.py          ← smoke-tests (baixa cobertura, hits pontuais)
  .venv/              ← virtualenv Python (NUNCA commit)
  .env                ← credenciais dev (NUNCA commit — está no .gitignore)
  .env.staging        ← credenciais staging local (NUNCA commit)

web/
  login.html          ← ÚNICA página SEM nav.js e SEM autofill-guard
  index.html          ← dashboard
  pages/*.html        ← 30+ páginas do sistema
  assests/            ← [sic] typo perpetuado; NÃO renomear
    css/              ← estilos globais + por módulo
    js/               ← config.js, nav.js, page-guard.js, api.js e módulos
  uploads/            ← arquivos de usuários (comercial, tickets, contratos, avatares)
    comercial/        ← materiais de apoio
    tickets/          ← anexos
    ...

docs/                 ← esta documentação
CPE Control.bat       ← painel local pra dev/staging (menus [1]-[12])
deploy.sh             ← git pull + apply_migrations (roda no servidor prod)
apply_migrations.sh   ← aplica NNN_*.sql pendentes conforme _migrations_log
```

## Regras de ouro (violar essas quebra o sistema ou perde autorização)

1. **Nunca commit/push sem autorização explícita do usuário.** Isso vale pra qualquer branch.
2. **Deploy pra `main` ou servidor CPEDC22 exige autorização explícita** — dev local é livre.
3. **Sempre verificar branch antes de commit** (`git branch --show-current`). Merges terminam com `git checkout dev`.
4. **Todo `mysql.connector.connect()` precisa `use_pure=True` + charset/collation** — sem isso, C-extension segfalta e derruba processo. Bug crônico do driver 9.x. Ver `docs/CONVENCOES.md`.
5. **Toda mudança em `nav.js` / `config.js` / `page-guard.js` exige bump de `?v=AAAA-MM-DD`** em todas as páginas que os carregam (~15 HTMLs). Sem isso, Cloudflare serve versão antiga por horas.
6. **Testar antes de dizer que funciona** — nunca dizer "pronto/deve funcionar" sem executar teste real no ambiente-alvo (browser real, curl com headers reais, DB).
7. **Modais sempre com grid Bootstrap** (`row + col-md-6`) — campos lado a lado, nunca empilhados.
8. **Email de teste vai SÓ pro Jonathan** (`jonathan.lopes@cpetecnologia.com.br`) — mesmo que o `userEmail` do harness aponte pra outro.

## Ambientes

| Nome | Porta API | Banco | Onde | Como derrubar |
|---|---|---|---|---|
| Dev local | 8000 | `cpe_plus` | XAMPP no PC do jonathan | `CPE Control.bat` [2] |
| Staging local | 8001 | `cpe_plus_staging` (dump de prod) | XAMPP no PC do jonathan | `CPE Control.bat` [7] |
| Produção | 8000 | `cpe_plus` | CPEDC22 (serviço Windows `CPEControlAPI`) | `Restart-Service CPEControlAPI` via WinRM |

**Detalhe crítico:** dev e staging **compartilham** o banco `cpe_chat` local. Prod usa outro MySQL. Ver `docs/GOTCHAS.md`.

## Como fazer coisas comuns

- **Adicionar endpoint** → cria/edita arquivo em `server/routes/*.py`, importa e registra em `server/app.py` (nem todo router é auto-registrado — sempre checar).
- **Adicionar página** → cria em `web/pages/`. Sempre incluir `config.js?v=…`, `nav.js?v=…`, `page-guard.js?v=…`. Registrar no menu em `web/assests/js/nav.js` (`globalMenu`) + criar entrada em `permission_pages` via migration.
- **Rodar migration** → cria `server/migrations/NNN_descricao.sql` (NNN = próximo número livre). Aplicar: `bash apply_migrations.sh server/.env` (dev) ou opção [10] do bat (staging) ou `bash deploy.sh` no servidor (prod).
- **Deploy prod** → ver `docs/DEPLOY.md` (fluxo completo git → WinRM → restart).
- **Ver o que aconteceu num erro** → logs em `\\CPEDC22\E$\CPE\logs\` (prod) ou console do CPE Control.bat (dev).

## Onde procurar coisa específica

| Preciso… | Arquivo |
|---|---|
| Overview do sistema, ambientes, stack | `docs/ARQUITETURA.md` |
| Como fazer deploy passo a passo | `docs/DEPLOY.md` |
| O que cada módulo faz e endpoints principais | `docs/MODULOS.md` |
| Prazos, permissões por role, decisões de negócio | `docs/REGRAS_NEGOCIO.md` |
| Convenções técnicas (cache-buster, use_pure, etc.) | `docs/CONVENCOES.md` |
| Bugs históricos e o que **não** fazer de novo | `docs/GOTCHAS.md` |
| Todos os endpoints da API | `docs/ENDPOINTS.md` (gerado do OpenAPI) |
| Estado do sistema de permissões | `docs/PLANO_PERMISSOES.md` |

## Se você for uma IA

- **Antes de mudar código de sistema global** (`config.js`, `nav.js`, `page-guard.js`, `app.py`): **leia o arquivo inteiro primeiro**. Já quebrou por não fazer isso.
- **Nunca faça "correção defensiva" em código que você não entende** — pergunta ao usuário. O sistema tem várias camadas com history, e uma mudança "óbvia" pode ter razão de ser.
- **Antes de mexer em banco de prod** (UPDATE/DELETE): **rode SELECT dry-run primeiro** e mostra ao usuário o que vai mudar. Ver `docs/DEPLOY.md#dados-em-prod`.
- **Se descobrir um gotcha novo**: adiciona em `docs/GOTCHAS.md` no mesmo PR.
- **Windows shell**: use PowerShell pra operações no CPEDC22 (WinRM). Bash pra scripts locais.
- **Emojis nos commits/docs**: OK e usado (padrão do repo).

---

**Última revisão desta documentação:** 2026-08-04
