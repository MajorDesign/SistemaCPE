# Arquitetura

## Visão geral

Monólito web tradicional: backend FastAPI + banco MariaDB + frontend HTML/JS estático servido pelo mesmo host.
Não há microserviços. Não há SPA framework — cada página HTML se auto-inicializa via seus scripts.

```
                          Internet
                              │
                        Cloudflare (DNS + TLS + WAF + DDoS)
                              │
                       Cloudflare Tunnel
                              │
                   [CPEDC22 — Windows Server]
                              │
     ┌────────────────────────┼─────────────────────────┐
     │                        │                         │
   Caddy :443             XAMPP Apache :80           MariaDB :3306
   (reverse proxy)       (arquivos estáticos)       (cpe_plus + cpe_chat)
     │                        │                         │
     └──> /api/* → FastAPI Uvicorn :8000 (serviço Windows CPEControlAPI)
                             │
                    WS: /api/meetings/ws
                        /api/chat/ws
```

Caddy roteia `/api/*` pro Uvicorn 8000 e o resto (HTML/CSS/JS) direto pro XAMPP Apache 80. Isso deixa a API rodar independente do servidor web.

## Stack completo

**Backend**
- Python 3.11 (venv em `server/.venv`)
- FastAPI + Uvicorn (`app:app`)
- SQLAlchemy 2.x (só o core, sem ORM completo — usa `engine.begin()` + `text()`)
- `mysql-connector-python` **9.x** — mas sempre com `use_pure=True` (ver `CONVENCOES.md`)
- APScheduler (jobs periódicos em `services/fleet_scheduler.py`, etc.)
- `bcrypt` pra hash de senha
- `argon2-cffi` (legacy — algumas rotas usam)

**Frontend**
- HTML5 puro sem framework
- Bootstrap 5 (via CDN? não — arquivos locais em `web/assests/css/`)
- Bootstrap Icons
- WebRTC nativo (mesh P2P nas reuniões)
- Fetch API pra requests
- `localStorage` pra sessão do usuário (`cpe_user`, `cpe_token`, `cpe_env`)

**Infra**
- Windows Server 2019/2022 (CPEDC22, IP interno 172.16.1.10/11)
- Serviços Windows: `CPEControlAPI`, `Caddy`, `Cloudflared`
- WinRM habilitado pra deploy remoto
- Git for Windows instalado no servidor (`git pull` roda lá)

## Bancos de dados

Dois databases no MariaDB local:

### `cpe_plus` (principal)
Tudo do sistema — users, permissões, tickets, frota, comercial, tasks, contratos, cofre, inventário, etc.
Mais de 100 tabelas. 87+ migrations aplicadas.

Principais namespaces por prefixo:
- `fleet_*` — frota
- `comercial_*` — módulo comercial
- `contratos*`, `contrato_pastas` — contratos
- `password*` — cofre de senhas
- `inventario_*`, `celulares_*` — inventário
- `recepcao_*` — visitantes/reuniões físicas
- `permission_pages`, `permission_page_role`, `permission_page_group` — sistema de permissões refatorado
- `*_TASK` — módulo tarefas
- `pre_cadastro_pendentes` — solicitações de 1º acesso
- Sem prefixo: `users`, `cpe_grupo`, `departamentos`, `unidades_cpe`, `tickets`, `notificacoes`

### `cpe_chat` (chat + reuniões)
- `chat_meeting_rooms` — salas WebRTC (código, nome, host, encerrada_em)
- `chat_meeting_participants` — quem tá dentro (peer_id, user_id/guest_token, status)
- `chat_channels`, `chat_messages`, `chat_servers`, `chat_meeting_atas`, `chat_voice_atas`

**Detalhe importante:** dev local (8000) e staging local (8001) **compartilham** o mesmo MySQL/`cpe_chat`. Prod (CPEDC22) tem outro MySQL. Isso significa que criar reunião local + abrir link em prod = "sala não encontrada" — o code está no chat local, prod nunca viu.

## Ambientes

| Nome | API porta | DB principal | DB chat | Host frontend | Uso |
|---|---|---|---|---|---|
| **Dev local** | 8000 | `cpe_plus` local | `cpe_chat` local | XAMPP em `localhost` | desenvolvimento no PC do jonathan |
| **Staging local** | 8001 | `cpe_plus_staging` local (dump de prod) | `cpe_chat` local (mesmo) | XAMPP em `localhost` | testar antes de prod |
| **Produção** | 8000 | `cpe_plus` em CPEDC22 | `cpe_chat` em CPEDC22 | Caddy/XAMPP em CPEDC22 | usuários finais |

**Seletor de ambiente no browser:** frontend usa `localStorage.cpe_env = 'dev'|'staging'` pra decidir qual porta chamar. Só vale em `localhost`. Em domínio público (cpecontrol…) força sempre `dev` (porta 8000). Ver `web/assests/js/config.js`.

**Pra abrir aba anônima em staging local** (`localStorage` vazio → cai em dev): passar `?env=staging` na URL. `config.js` reconhece.

## Autenticação

- **Endpoint de login:** `POST /api/auth/login` — body `{credential, password}`
- **Token:** formato próprio `{user_id}.{ts}.{random}.{hash}` — decodifica com `security.parse_session_token()`. Não é JWT.
- **Como enviar:** cookie `cpe_session` (default) OU header `X-Auth-Token` OU query `?token=…`
- **Validação servidor:** cada rota chama `_user_from_request()` / `_exigir_user()` de `security.py`
- **Sessão:** 12h de TTL (era 7 dias, reduzido por risco). Frontend não renova; ao expirar → 401 → auth-guard.js redireciona pra login.
- **Revalidação frontend:** `/api/auth/me` devolve `{id, name, email, role, group_id}` — chamado no boot de páginas críticas pra pegar mudança de role sem exigir logout (ex: `tasks.html`).

## Rate-limit de login

`server/app.py` mantém dict in-memory por (credential+IP): 5 falhas em 5min → 15min de bloqueio.
Quando "sistema caiu" mas tudo está UP → provavelmente é 429 no login. `Restart-Service CPEControlAPI` zera o dict.
Ver `docs/GOTCHAS.md#rate-limit-de-login`.

## Sistema de permissões

Fase completa em 2026-05. **Fonte da verdade única no banco** (não mais em CSVs/hardcoded).

**Tabelas:**
- `permission_pages` — catálogo de páginas (page_key, url, ícone, categoria)
- `permission_page_role` — quais roles têm acesso a cada page (ADMIN/TI/MANAGER/RESPONSAVEL_GRUPO/USER)
- `permission_page_group` — grupos com acesso adicional a uma page (além do que role já dá)

**Fluxo:**
1. Frontend chama `/api/permissions/me/menu?user_id=X` — backend devolve lista de `page_keys` permitidas
2. `nav.js` filtra `globalMenu` (hardcoded pra UI só) contra essa lista
3. `page-guard.js` (carregado em cada página) valida no boot que o user pode ver aquela page — senão redireciona

**Detalhes vivos:** `docs/PLANO_PERMISSOES.md` tem histórico da refatoração.

## Estrutura em runtime — o que roda quando

**Boot da API (`app.py`):**
1. Carrega `.env`
2. Cria FastAPI + CORS
3. Importa e registra routers (30+ `include_router`)
4. Inicializa scheduler APScheduler + jobs (`fleet_scheduler.iniciar_scheduler()`)
5. Escuta em `0.0.0.0:8000`

**Jobs periódicos ativos:**
- `job_lembretes_checklist` (10min) — email pro condutor lembrar do checklist
- `job_escalada_frotas` (1h) — se atrasado >6h, avisa RESPONSAVEL_GRUPO Frotas
- `job_cleanup_fantasmas` (30min) — cancela reservas aprovadas sem checklist após 4h
- `job_cancelar_reservas_sem_aprovacao` (5min) — cancela pendentes onde passou horário + janela 4h
- `job_lembrete_vistoria_pendente` — lembrete de vistoria de veículo

**Healthcheck externo (Task Scheduler do Windows):**
- `\\CPEDC22\E$\CPE\scripts\healthcheck.ps1` (roda a cada 2min) — pinga `/health` e reinicia serviço se der 3 falhas
- SCM Failure Actions também restart automático em crash
- Log em `\\CPEDC22\E$\CPE\logs\healthcheck-api.log`

## Componentes externos (in-house)

- **Caddy** — reverse proxy TLS, roda como serviço Windows. Bug crônico: às vezes porta 443 listening mas não responde → `Start-ScheduledTask CaddyServer` desbloqueia. Ver `docs/GOTCHAS.md#caddy-travamento`.
- **Cloudflared** — tunnel público, também serviço Windows.
- **Agente inventário Windows** — collector rodando em endpoints, envia hardware/software pra `/api/inventario/*`. Firewall CPEDC22 libera 172.16.0.0/16 → 8000.

## O que NÃO existe (pra não perder tempo procurando)

- Docker / containers
- CI/CD (GitHub Actions, etc.) — deploy é manual via WinRM
- Testes automatizados robustos — só smoke pontual em `server/tests/`
- ORM completo (Django, SQLAlchemy full) — apenas `text()` + bind params
- Queue system (Redis, Celery, etc.) — jobs são APScheduler in-process
- SFU pra reuniões — WebRTC mesh direto, max ~8 pessoas (config `MAX_MEETING_PARTICIPANTS`)
- TURN server — só STUN público (limitação pra conexões atrás de NAT restrito internacional)
