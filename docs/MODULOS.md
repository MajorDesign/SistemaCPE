# Módulos do sistema

Cada seção descreve um módulo: propósito, arquivos, tabelas, endpoints principais e quem pode acessar.
Pra lista COMPLETA de endpoints, ver `docs/ENDPOINTS.md` (gerado do OpenAPI).

Ordem alfabética.

---

## 🔐 Auth / Session

**Propósito:** login, /me, forgot-password, reset-password.

**Arquivo:** `server/routes/auth.py` — prefix `/api/auth`

**Endpoints principais:**
- `POST /login` — body `{credential, password}` → `{success, user, access_token}` + cookie `cpe_session`
- `GET /me` — devolve user atual (id/name/email/role/group_id) — usado pra revalidar role após admin promover
- `POST /forgot-password` — dispara email com link (via `AGENDA_SMTP_*` ou `SMTP_*`)
- `POST /reset-password` + `GET /reset-password/validate` — fluxo de link em email

**Detalhes:**
- Token custom, não JWT. Ver `server/security.py`.
- Cookie `cpe_session` (SameSite=Lax, 12h).
- Também aceita header `X-Auth-Token` (usado por scripts / integrações).
- Rate-limit interno em `app.py`: 5 falhas/5min por (credential+IP) → 15min bloqueio.

---

## 📊 Dashboard

**Propósito:** overview inicial pós-login. Cards, KPIs e notificações.

**Arquivo:** `server/routes/dashboard.py` — prefix `/api/dashboard`
**Frontend:** `web/index.html`

**Acesso:** todos os roles.

---

## 🎫 Tickets (suporte)

**Propósito:** helpdesk interno — usuário cria ticket, TI/Suporte atende, comentários, avaliação.

**Arquivos:**
- `server/routes/tickets.py`, `server/routes/ticket_interacoes.py`, `server/routes/atendimentos.py`, `server/routes/avaliacoes.py`
- `server/routes/categorias.py`, `server/routes/subcategorias.py`, `server/routes/categoria_campos.py` (formulário dinâmico)
- `server/routes/ticket_permissoes.py` (permissão por categoria por membro — migration 089)

**Tabelas:** `tickets`, `ticket_interacoes`, `avaliacoes`, `categorias`, `subcategorias`, `categoria_campos`, `ticket_membro_categorias`

**Frontend:** `web/pages/tickets.html`

**Regras:**
- USER cria e vê os próprios tickets
- RESPONSAVEL_GRUPO do grupo dono da categoria vê tickets desse grupo
- ADMIN/TI/MANAGER veem tudo
- **Reabrir chamado:** ADMIN/TI/MANAGER + o próprio solicitante (regras: até 3x, dentro de 2 meses, status `Resolvido`)
- Categoria tem `group_id` — quem responde é o RESPONSAVEL_GRUPO desse grupo
- **Excluir categoria/subcategoria** (2026-08-14): bloqueia com 409 se existir qualquer ticket vinculado (mesmo resolvido/fechado). Reclassifique antes.
- **Permissão por categoria por membro** (2026-08-14, migration 089): RESPONSAVEL_GRUPO (ou ADMIN) pode restringir quais categorias/subcategorias cada USER do grupo enxerga na lista de tickets. Ver `REGRAS_NEGOCIO.md` (seção "Permissões por categoria").

---

## 🚗 Frotas (Fleet)

**Propósito:** gestão de veículos corporativos — reserva, aprovação, checklist de saída/devolução, manutenção, vistoria.

**Arquivos:**
- `server/routes/fleet.py` — endpoints CRUD, aprovação, checklist
- `server/services/fleet_scheduler.py` — jobs periódicos (lembretes, escaladas, auto-cancelamento)
- `server/services/email_service.py` — templates de email da frota

**Tabelas:** `fleet_vehicles`, `fleet_reservations`, `fleet_checklists`, `fleet_maintenance`, `fleet_vistoria_lembrete`

**Frontend:** `web/pages/fleet.html`

**Grupo Frotas:** `id=13` (constante `_FLEET_GROUP_ID`)

**Regras críticas:**
- Reserva pendente + sem aprovação em 4h após horário início → cancela automaticamente + email
- Reserva aprovada + condutor não fez checklist em 4h após horário → cancela + email
- RESPONSAVEL_GRUPO Frotas aprova/rejeita reservas + inicia viagem em nome do condutor
- Condutor precisa fazer checklist DE SAÍDA e DEVOLUÇÃO com **7 fotos obrigatórias**
  (6 ângulos do carro + painel mostrando KM). Backend valida (v083, 2026-08-05).
- **Anti-burla**: SHA-256 impede reusar a mesma foto em ângulos diferentes.
  Foto do painel confere se o KM digitado bate com o mostrador.
- Mobile: fleet.html tem layout responsivo em cards + botão "devolver" gigante

**Ver:** `docs/REGRAS_NEGOCIO.md#frotas`

---

## 💼 Comercial

**Propósito:** módulo pro grupo Comercial — agenda de vendedores, marcação de reuniões com clientes, cadastro de clientes com histórico, material de apoio pra apresentação, classificação pós-reunião.

**Arquivo:** `server/routes/comercial.py` — prefix `/api/comercial`

**Tabelas:**
- `comercial_vendedor_slots` — até 3 horários fixos por vendedor
- `comercial_clientes` — cadastro com dedup por email (UNIQUE permite NULL)
- `comercial_reunioes` — agendamentos + meeting_url gerado no chat
- `comercial_material_apoio` — arquivos globais pra usar em reunião

**Frontend:** `web/pages/comercial.html` (SPA com 6 abas)

**Regras:**
- Vendedor USER: vê SÓ a própria agenda; marca reunião só pra si mesmo; vê SÓ suas reuniões
- RESPONSAVEL_GRUPO Comercial + ADMIN/TI/MANAGER: veem tudo, marcam pra qualquer vendedor, editam horários de outros
- Reunião gera meeting_url via `chat_meeting_rooms` (código único)
- meeting_url usa Origin/Referer do request (não `PUBLIC_BASE_URL` hardcoded) — evita link staging apontar pra prod
- Material apoio: upload até 100MB, extensões whitelist (pdf, ppt, doc, xls, imagens, vídeos)
- Classificação pós-reunião: quente/morno/frio + comentário

**Ver:** `docs/REGRAS_NEGOCIO.md#comercial`

---

## 💬 Chat + Meetings

**Propósito:** chat interno (Discord-like: servidores/canais/cargos) + reuniões WebRTC.

**Arquivos:**
- `server/routes/chat.py` — mensagens, canais, servidores
- `server/routes/meetings.py` — salas WebRTC, WS, ata
- `server/services/email_service.py` — email de convite

**Tabelas (banco `cpe_chat`):**
- `chat_meeting_rooms`, `chat_meeting_participants`
- `chat_channels`, `chat_messages`, `chat_servers`
- `chat_meeting_atas`, `chat_voice_atas`

**Frontend:**
- `web/pages/chat.html` — chat completo
- `web/pages/meet.html` — sala de reunião

**Regras:**
- Sala é criada quando alguém chama `POST /api/meetings` com nome
- Externo (guest sem login) entra via lobby: `POST /request-entry` com nome → status=aguardando → WS aberta → host aprova → `meeting_join_approved`
- Host = quem criou a sala (`criado_por`). Único que pode aprovar/rejeitar/encerrar.
- WebRTC mesh P2P — signaling via WS (`meeting_offer`, `meeting_answer`, `meeting_ice`)
- Limite de participantes: `MAX_MEETING_PARTICIPANTS` (default 8, config em `.env`)
- Gravação: só host, client-side via `getDisplayMedia` (grava a aba do meet), baixa .webm no PC
- Banner "Fulano está gravando" via WS `meeting_recording`
- Legendas: Web Speech API (só Chrome/Edge, não Firefox)
- Material de apoio na sala: botão aparece se user tem acesso ao módulo Comercial (probe via `/api/comercial/material-apoio`)

**Ver:** `docs/REGRAS_NEGOCIO.md#reunioes` + `docs/GOTCHAS.md#meetings`

---

## ✅ Tasks (quadros kanban)

**Propósito:** gestão de projetos/tarefas em quadros configuráveis por template (Kanban/Scrum/Gestão/Tarefas).

**Arquivo:** `server/routes/tasks.py` — prefix `/api/tasks`

**Tabelas:** todas terminam em `_TASK`:
- `espacos_TASK` — quadros
- `tarefas_TASK` — cards
- `colunas_TASK`, `subtarefas_TASK`, `comentarios_TASK`
- `espaco_grupos_TASK`, `espaco_grupo_sla_TASK`, `convites_espaco_TASK`
- `templates_TASK` — templates de espaço salvos

**Frontend:** `web/pages/tasks.html`

**Regras:**
- USER pode criar tarefa em espaço onde é membro; só criar NOVO espaço se ELEVATED (RESPONSAVEL_GRUPO/ADMIN/TI/MANAGER)
- Fix crítico 2026-08-04: `syncMeFromServer()` no boot da página revalida role/grupo via `/api/auth/me` — mudança de role no admin não exige logout do user pra ver botão "Novo espaço"
- Colunas personalizáveis por espaço (backend valida se editor é membro do grupo)
- Convites entre grupos: notificação in-app + sino
- Encaminhar/devolver tarefa: só ELEVATED + owner
- Reabrir: só RESPONSAVEL_GRUPO do grupo da tarefa (ou ADMIN/TI) quando finalizada

---

## 📅 Agenda

**Propósito:** integração com Carbonio (webmail corporativo) — cada user conecta sua conta.

**Arquivos:** `server/routes/agenda.py`, `server/services/carbonio_*.py`

**Frontend:** `web/pages/agenda.html`

**Regras:**
- Login separado em Carbonio (endpoint `/api/agenda/login`)
- Lembretes disparam notificação in-app tipo `lembrete_agenda`
- SMTP dedicado: `AGENDA_SMTP_*` (perfil separado do transacional default `SMTP_*`)
- Endpoint `/agendar.html` público (sem login) pra convidados externos marcarem — subdomínio pendente (`agenda.cpecontrol.com.br`)

---

## 👋 Recepção

**Propósito:** controle de visitantes na portaria + reservas de salas físicas + envios de correspondência.

**Arquivo:** `server/routes/recepcao.py`

**Tabelas:** `recepcao_visitantes`, `recepcao_reservas`, `recepcao_envios`, `recepcao_convidados`, `recepcao_salas`

**Frontend:** `web/pages/recepcao.html`

**Regras:**
- Qualquer USER agenda sala/cadastra envio
- Só ADMIN/RESPONSAVEL_GRUPO cria sala
- Reserva de sala tem `confirmacao_prazo` — visitante confirma via link em email

---

## 🎧 Equipe de Suporte (agendas de atendimento)

**Propósito:** módulo dedicado pro grupo Suporte gerenciar agendas de atendimento (feriados, bloqueios, capacidade).

**Arquivo:** `server/routes/atendimentos.py`

**Frontend:** `web/pages/equipe-suporte.html` + `web/pages/agendar.html` (público)

**Níveis de acesso:**
- `admin`: ADMIN/TI/RESPONSAVEL_GRUPO Suporte/grupo "Suporte ti" — CRUD de estrutura
- `op`: USER do grupo Suporte — administra a PRÓPRIA agenda (aprova/recusa pendentes só dela)
- `view`: Comercial — somente leitura

**Migration 084 (2026-08-05) — agenda por instrutor + link direto:**
- `atend_agendas.instrutor_id` (FK users, UNIQUE): dono da agenda. NULL = agenda de unidade coletiva (só admin gerencia)
- `atend_agendas.slug` (UNIQUE): URL amigável — `agendar.html?agenda=<slug>` cai direto no formulário do instrutor
- `atend_agendas.oferece_presencial`/`oferece_online` (TINYINT): substituem restrição do antigo `atend_agendas.tipo`. Toda agenda oferece as duas modalidades por padrão
- Capacidade unificada: 1 slot = 1 vaga total (não separa presencial/online). `cap_presencial`/`cap_online` de `atend_servicos`/`atend_treinamentos` ficam no banco mas são ignorados por `_checar_vaga`/`_slot_tem_vaga`
- Notificação in-app + email quando cai agendamento novo: instrutor dono + todos os RESPONSAVEL_GRUPO Suporte (função `_notificar_novo_agendamento`)
- USER Suporte que é dono aprova só a própria agenda (helper `_pode_aceitar_agendamento`)
- `/pendentes` filtra por `instrutor_id = user.id` quando nível é `op`
- Rota pública nova: `GET /api/atendimentos/publico/agendas/slug/{slug}`

---

## 📦 Inventário TI

**Propósito:** cadastro de equipamentos TI (notebooks, monitores, periféricos), controle de patrimônio, alocação por user.

**Arquivos:** `server/routes/inventory.py`, `server/routes/inventario.py`, `server/routes/agente_inventario.py` (agent Windows envia hardware/software)

**Tabelas:** `inventario_*`, `equipamento_*`

**Frontend:**
- `web/pages/inventory.html` — financeiro TI (visão contábil)
- `web/pages/inventory-ti.html` — inventário técnico

**Acesso:** ADMIN/TI/MANAGER

**Detalhe:** agente Windows envia via porta 8000, firewall CPEDC22 libera 172.16.0.0/16. Ver `docs/GOTCHAS.md#firewall-porta-8000`.

---

## 📱 Celulares Corporativos

**Propósito:** cadastro de celulares corporativos, chip, plano, user responsável, termo de responsabilidade.

**Arquivo:** `server/routes/celulares.py`

**Frontend:** `web/pages/celulares.html`

**Acesso:** ADMIN/TI/MANAGER

---

## 🌐 Network (monitoramento de rede)

**Propósito:** ping/uptime de hosts internos, alertas.

**Arquivo:** `server/routes/network.py`

**Frontend:** `web/pages/network.html`

**Acesso:** ADMIN/TI

---

## 🔒 Cofre de Senhas (Password Vault)

**Propósito:** cofre compartilhado por grupo — senhas com criptografia adicional via PIN.

**Arquivos:** `server/routes/passwords_new.py`, `server/routes/password_pin.py`

**Tabelas:** `passwords`, `password_categorias`, `password_shares`

**Frontend:** `web/pages/password-vault.html`

**Regras:**
- Cada user tem `vault_pin_hash` (setado na primeira vez que acessa)
- Senha só é descriptografada após digitar PIN correto (2ª factor local)
- Compartilhamento: dentro do grupo ou pra user específico

**Acesso:** todos os roles (mas cada senha tem escopo — group_id ou user_id)

---

## 📄 Contratos e Termos

**Propósito:** gestão de contratos por pastas (cada pasta é de um grupo/setor), upload PDF, vencimento.

**Arquivo:** `server/routes/contratos.py`

**Tabelas:** `contratos`, `contrato_pastas`

**Frontend:** `web/pages/contratos.html`

**Acesso:** todos veem sua pasta (via `contrato_pastas.group_id`)

---

## 📚 Base de Conhecimento

**Propósito:** wiki interna — artigos técnicos, procedimentos.

**Arquivo:** `server/routes/knowledge_base.py`

**Frontend:** `web/pages/base_conhecimento.html`

**Acesso:** todos leem; só ADMIN/TI/MANAGER edita

---

## 📈 Relatórios

**Propósito:** dashboards agregados de tickets, frota, tarefas.

**Arquivo:** `server/routes/reports.py`

**Frontend:** `web/pages/reports.html`

**Acesso:** RESPONSAVEL_GRUPO (só do seu grupo) + ADMIN/TI/MANAGER (todos)

---

## 👥 Usuários / Grupos / Permissões

**Arquivos:**
- `server/app.py` (embutido — routers `users_router`, `groups_router`)
- `server/routes/permissions.py`

**Frontend:**
- `web/pages/users.html` — CRUD de users, reset de senha, aprovação de pré-cadastro
- `web/pages/groups.html` — CRUD de grupos + departamentos
- `web/pages/permissions.html` — matriz de permissões (page × role/grupo)

**Regras:**
- Só ADMIN cria/edita/deleta users e grupos
- **Reset de senha:** admin resetando OUTRO user (sem senha atual) OU user resetando própria (com senha atual OU se `must_change_password=1`)
- Users no grupo faturamento (id=10 vs 5): tem duplicação legado, ver `docs/GOTCHAS.md#grupos-duplicados`
- **Deletar grupo:** bloqueia com 409 se houver contratos/pré-cadastros/tickets/passwords/categorias vinculados; users e permissões trivialmente desvinculados

---

## 📧 Pré-cadastro pendente

**Propósito:** admin autoriza um email pra ele conseguir criar conta (1º acesso).

**Arquivo:** `server/routes/pre_cadastro.py`

**Tabelas:** `pre_cadastro_pendentes` (com `status='pendente|aprovado|recusado'` + `user_id` após criar)

**Frontend:** aba dentro de `users.html` ("E-mails Autorizados aguardando 1º Acesso")

---

## 🔔 Notificações

**Propósito:** notif in-app (sino no header) + trigger de email.

**Arquivo:** `server/routes/notificacoes.py`

**Tabela:** `notificacoes` (com `tipo`, `mensagem`, `lida`, `usuario_id`, `ticket_id` [reused pra outros ids])

**Tipos válidos** (validados em `notificacoes.py`):
- `ticket_criado`, `nova_resposta`, `status_alterado`, `atribuido`, `comentario_interno`
- `avaliacao_pendente`
- `convite_task`, `convite_aceito_task`, `convite_recusado_task`
- `convite_reuniao`, `convite_aceito_reuniao`, `convite_recusado_reuniao`
- `lembrete_agenda`, `pre_cadastro_pendente`
- `info`, `aviso`, `erro`, `sucesso`

---

## 📥 Download de Agentes

**Propósito:** página de download do agente Windows de inventário + termo notebook.

**Arquivo:** `server/routes/download_agents.py`

**Frontend:** `web/pages/download-agents.html`

**Acesso:** todos os roles

---

## 📖 Docs (documentos técnicos)

**Propósito:** repositório interno de documentos técnicos (manuais, especificações).

**Frontend:** `web/docs.html` + `web/docs_detail.html`

**Acesso:** todos leem

---

## Módulos que aparecem em rotas mas não têm página dedicada

- `preferencias.py` / `email_preferencias.py` — configurações do usuário por email (opt-in/out)
- `permission_pages.py` — CRUD do catálogo de páginas (usado pelo admin em `permissions.html`)
- `chat_translations.py` — tradução de mensagens do chat
- `dashboard.py` — endpoints de KPIs para o index.html
- `webhook*.py` — endpoints pra callback de sistemas externos

Ver `docs/ENDPOINTS.md` pra lista completa.
