# Regras de Negócio

Decisões que **não existem no código como constante óbvia** — vieram de conversa e são as fontes da verdade quando houver dúvida.

## Matriz global de roles

| Role | Escopo | Poderes gerais |
|---|---|---|
| **USER** | próprio contexto | Cria ticket próprio, agenda reserva de veículo pra si, marca reunião comercial pra si, acessa cofre do seu grupo, edita perfil |
| **RESPONSAVEL_GRUPO** | grupo onde está atrelado (`group_id`) | Tudo do USER + gestão do próprio grupo: aprova reservas frota (se grupo=Frotas), aprova pré-cadastros do grupo, vê agenda de todos no grupo, edita horários dos vendedores (se grupo=Comercial), aprova/rejeita entrada em sala de reunião que criou, cria/edita colunas/tarefas em espaços do grupo |
| **MANAGER** | multi-grupo (gestão) | Idêntico a ADMIN em quase tudo mas sem gerência de infra. Vê todos os módulos operacionais. |
| **TI** | irrestrito operacional | Igual ADMIN operacionalmente. Manteve role separada por convenção histórica. |
| **ADMIN** | irrestrito | Único que cria/edita/deleta users e grupos. Único que pode entrar em `permissions.html`. |

**Grupos especiais** (`_GRUPOS_RESP_ADMIN`):
- `Suporte` → RESPONSAVEL_GRUPO desse grupo vira **admin do módulo Atendimentos** (não do sistema)
- `Frotas` (id=13) → RESPONSAVEL_GRUPO aprova reservas + inicia viagem em nome do condutor
- `Comercial` (id=28 em prod, varia em dev/staging) → RESPONSAVEL_GRUPO edita horários de outros vendedores + vê agenda de todos + marca reunião pra qualquer vendedor

---

## Frotas

### Fluxo padrão de reserva
1. USER cria reserva de veículo pra data/horário X (status `pendente`)
2. Resp Frotas recebe notificação in-app + email → aprova ou rejeita
3. Se aprovada → status `aprovado`, condutor recebe confirmação
4. No dia da viagem, condutor abre fleet.html → banner amarelo lembra do checklist de saída
5. Faz checklist com fotos → status vira `em_uso`
6. Ao devolver → checklist de devolução (também com fotos)
7. Status vira `finalizado` OU `manutencao_solicitada` se marcou problemas

### Prazos automáticos (job scheduler)
- **Pendente sem aprovação após horário início + janela 4h** → cancela + email condutor + email Resp Frotas
  - Motivo gravado: `EXPIRED_NO_APPROVAL::<nome do resp>`
  - Frontend detecta esse prefixo em `/notifications` pra mostrar mensagem específica
- **Aprovada sem checklist após 4h do horário início** → cancela + motivo "checklist nao realizado em 4 horas apos o horario de inicio"
- Rodam a cada 5min (JOB 4) e 30min (JOB 3). Ver `server/services/fleet_scheduler.py`

### Regras extras
- Condutor tira **7 fotos obrigatórias na saída E na devolução** (a partir de 2026-08-05):
  frente, lateral, para-choque dianteiro, para-choque traseiro, quatro portas,
  para-lama traseiro e **painel (mostrando KM)**. Backend rejeita `vistoriar-saida`
  e `devolver` se algum ângulo obrigatório estiver faltando. Checklists criados
  antes de 2026-08-05 aceitam 6 fotos (sem painel) — compat retroativa.
- **Anti-reuso de foto** (2026-08-05): cada upload calcula SHA-256; a mesma
  imagem não pode ser usada duas vezes no mesmo checklist (índice único
  `uq_checklist_hash` em `fleet_checklist_photos`). Evita a burla de mandar
  a mesma foto de saída como se fosse do retorno.
- **Foto do painel confere KM** (2026-08-05): o KM digitado precisa bater com
  a foto do painel. Vistoriador vê os dois lado a lado e recusa se não confere.
- Resp Frotas pode iniciar viagem em nome do condutor (útil se o condutor está no volante e não vai abrir o sistema)
- Mobile: layout responsivo em cards + botão "devolver" gigante
- Histórico de checklist mostra APENAS as viagens do próprio condutor (USER não vê de outros)
- Lembretes por email escalam: 1h antes, no horário do fim, atrasado a cada 3h. RESPONSAVEL_GRUPO é acionado se atraso >= 6h.
- Vistoria periódica do veículo tem lembrete próprio (`fleet_vistoria_lembrete`)

---

## Comercial

### Visão restrita por role
- **Vendedor USER** — vê SÓ:
  - A si mesmo em "Vendedores"
  - Suas reuniões em "Reuniões" (backend filtra por `vendedor_id=eu OR agendado_por=eu`)
  - Seus 3 slots em "Meus Horários"
  - Todos os clientes (pra dedup por email funcionar)
  - Todos os materiais de apoio
- **RESPONSAVEL_GRUPO Comercial + ADMIN/TI/MANAGER** — veem tudo, marcam reunião pra qualquer vendedor, editam horários de outros

### Slots (3 por vendedor)
- Cada vendedor define seus próprios 3 horários fixos (ex: 09:00, 14:00, 17:00)
- Aplicam-se a todos os dias úteis
- Slot livre pode ser reservado por qualquer pessoa do grupo Comercial (ou só o próprio se USER)

### Cliente
- Dedup por email (UNIQUE key permite NULL — clientes sem email não colidem)
- Cadastrado 1x, historicamente aparece em todas as reuniões vinculadas
- Modal "Nova Reunião" busca cliente existente via `/clientes/buscar?email=X` antes de criar novo

### Reunião
- Sempre gera meeting_url automático via `chat_meeting_rooms` (código único aleatório)
- URL usa `Origin`/`Referer` do request → link cai no MESMO ambiente que criou (não hardcoded prod)
- Frontend também reescreve `meeting_url` com `location.origin` como blindagem
- Em localhost com staging: adiciona `&env=staging` na URL pra aba anônima cair na API certa

### Classificação pós-reunião
- Após realizada, vendedor classifica: `quente` / `morno` / `frio` + comentário
- Aba Clientes tem filtro por classificação (última reunião do cliente)

### Material de apoio
- Upload até 100MB, extensões whitelist (pdf, ppt, doc, xls, imagens, vídeos)
- Global — todo mundo do Comercial usa
- Botão "Material" aparece na sala de reunião pra quem tem acesso ao módulo Comercial
- Ao clicar num material → overlay fullscreen na aba do meet → vendedor compartilha tela pra ver

---

## Reuniões (meet.html)

### Lobby / aprovação
- **Host** = quem criou a sala. Único que aprova/rejeita/encerra.
- **Interno logado** (com session_token) — ainda passa pelo lobby (pediu decisão)
- **Externo** (guest) — informa nome, `POST /request-entry` retorna `guest_token`, WS aberta
- Ao aprovar: backend `send_to_peer` envia `meeting_join_approved` via WS → cliente entra
- **Race condition tratada:** `manager.disconnect(only_if_ws=ws)` só remove peer se a WS registrada for a mesma que caiu — evita dropar reconexão nova

### Gravação
- Só o **host** vê o botão gravar
- Client-side: `getDisplayMedia` (usuário escolhe aba/janela/tela) + mic próprio via `getUserMedia`
- Áudios mixados via AudioContext, vídeo do displayMedia direto
- MediaRecorder → download `.webm` no PC do host
- Broadcast WS `meeting_recording` faz aparecer banner "Fulano está gravando" nos outros (LGPD)

### Limites
- Max participantes: `MAX_MEETING_PARTICIPANTS` (default 8, config em `.env`)
- Sem TURN server — só STUN público. Conexões atrás de NAT restrito internacional podem falhar. Ver `docs/GOTCHAS.md#turn-pendente`.

---

## Tickets

### Categorias e responsabilidade
- Categoria/subcategoria tem `group_id`
- Ticket criado em categoria X é atendido pelo grupo dono
- Ticket comum: USER vê os próprios; RESPONSAVEL_GRUPO vê do grupo; ADMIN/TI/MANAGER vê tudo

### Reabertura
- Quem pode: ADMIN/TI/MANAGER + o próprio solicitante
- Limites técnicos: até **3 reaberturas**, dentro de **2 meses** da última resolução, status `Resolvido`

### Formulário dinâmico
- Cada subcategoria pode ter campos extras (`categoria_campos`): text/select/checkbox/date/número
- Backend salva serializado em `tickets.campos_customizados` (JSON)

### Excluir categoria/subcategoria (2026-08-14)
- Backend bloqueia com 409 se algum ticket referencia a categoria (direto OU via subcategoria filha) ou a subcategoria.
- Mesmo tickets `Resolvido`/`Fechado` bloqueiam — histórico precisa manter a referência.
- Fluxo esperado: reclassificar tickets pra outra (sub)categoria antes de excluir.

### Avaliação de atendimento (fluxo confirmado 2026-08-14)
Ao finalizar um ticket (`POST /api/tickets/{id}/finalizar`) o backend faz **3 coisas**:
1. Cria linha em `ticket_avaliacoes` com `expira_em = NOW + 7 dias` (`INSERT IGNORE` — idempotente).
2. **Notif in-app** `avaliacao_pendente` em `notificacoes`. Aparece no sino do topo E dispara popup automático quando o solicitante abre `/tickets.html` (via `verificarAvaliacoesPendentes()` → `GET /api/avaliacoes/pendentes?usuario_id=X`).
3. **Email** `email_ticket_finalizado` com bloco âmbar "⭐ Avaliar atendimento" + botão que aponta pra `/tickets.html?ticket_id=X` — abrir esse link dispara o popup direto (sem precisar navegar).

Quando conferir se o user está recebendo:
- notif in-app: `SELECT * FROM notificacoes WHERE usuario_id=X AND tipo='avaliacao_pendente' ORDER BY id DESC`
- registro pendente: `SELECT * FROM ticket_avaliacoes WHERE solicitante_id=X AND avaliado_em IS NULL AND expira_em > NOW()`
- email enviado: `api-stdout.log` do CPEDC22 tem linhas `[EMAIL] ✓ ... assunto='[Chamado ...] Finalizado — ...'`

### Filtros salvos como preferência (2026-08-14)
- Painel "Filtros" (`advancedFilters`) inclui status, prioridade, **categoria** e **subcategoria** (subcategorias em cascata a partir da categoria escolhida).
- Categorias vêm do próprio grupo do user (`GET /api/categorias?group_id={users.group_id}`); admin sem grupo definido não vê categorias filtráveis.
- **Filtragem é client-side** — filtra `tickets` já carregado; backend não recebe params novos.
- Aplicou filtro? Banner âmbar pergunta se quer salvar como padrão. **Sim** → grava em `localStorage['tickets_filter_prefs_v1_<userId>']` (por user, por browser). **Agora não** → suprime o banner só naquela combinação, na sessão atual.
- Ao abrir `/tickets.html`, se há pref salva, aplica automaticamente + abre o painel + mostra "Remover preferência".

### Permissões por categoria por membro (2026-08-14, migration 089)
Tabela `ticket_membro_categorias` (`user_id`, `group_id`, `categoria_id`, `subcategoria_id` NULL, `created_by`).

**Quem configura:** ADMIN ou RESPONSAVEL_GRUPO do MESMO grupo do USER alvo. Endpoints em `/api/tickets/permissoes/*`.

**Regra de leitura** (aplicada em `GET /api/tickets/`):
- USER sem nenhuma linha → **vê tudo do grupo** (default; não quebra comportamento antigo).
- USER com 1+ linhas → vê SÓ tickets que caem em alguma restrição dele + os próprios (`solicitante_id = self`).
- Por linha: `subcategoria_id IS NULL` = categoria inteira liberada; se preenchida = só aquela subcategoria.
- ADMIN, TI, MANAGER, RESPONSAVEL_GRUPO **não** são filtrados por esta tabela (por design — gestores veem tudo do escopo).
- Tentar restringir role ≠ USER retorna **400** ("não é possível restringir um {role}").

**Auto-grant ao atribuir** (`PUT /api/tickets/{id}` com `responsavel_id`, e `POST /api/tickets/{id}/assumir`):
- Se o responsável indicado tem restrições e o ticket NÃO cai em nenhuma, backend cria automaticamente uma linha em `ticket_membro_categorias` cobrindo aquela (sub)categoria.
- Silencioso — não interrompe a atribuição se o auto-grant falhar.
- Se user tem 0 linhas (vê tudo) → não mexe.

**Frontend:** botão "Permissões" na action-bar de `tickets.html`, visível só pra ADMIN e RESPONSAVEL_GRUPO. Modal com lista de membros + árvore de categorias/subcategorias com checkboxes.

---

## Tasks (kanban)

### Templates de espaço
- 4 templates fixos: `gestao`, `kanban`, `scrum`, `tarefa`
- Cada um vem com colunas predefinidas (ex: Backlog/A Fazer/Em Andamento/Concluído)
- Templates customizados podem ser salvos por user

### Permissões dentro do espaço
- USER da lista de membros: cria e edita tarefas próprias
- RESPONSAVEL_GRUPO do grupo dono: cria/edita/finaliza qualquer tarefa
- Só ELEVATED cria NOVO espaço (RESPONSAVEL_GRUPO/ADMIN/TI/MANAGER)

### Convites e encaminhamento
- Encaminhar tarefa entre espaços/grupos: notificação in-app + registro em `convites_espaco_TASK`
- Devolver (reverter encaminhamento): só ELEVATED + owner + tarefa com status_final

### Fix crítico 2026-08-04
Frontend agora chama `/api/auth/me` no boot (`syncMeFromServer`). Sem isso, mudança de role feita pelo admin não valia sem o user deslogar/logar.

---

## Cofre de senhas

- Cada senha tem escopo: `user_id` OR `group_id`
- 2ª factor local: user define PIN na primeira vez (`vault_pin_hash`)
- Senha só descriptografa após digitar PIN correto
- Compartilhamento por link temporário: possível
- ADMIN NÃO vê senhas de outros users por padrão — auditoria pode ser adicionada

---

## Contratos

- Cada pasta tem `group_id` — quem vê a pasta é o grupo dono
- Contratos dentro da pasta herdam permissão
- Ao deletar grupo, pasta bloqueia o delete (409) se tiver contratos vinculados
- Vencimento: alerta N dias antes (config no arquivo)

---

## Equipe de Suporte / Atendimentos

Módulo `equipe-suporte.html` gerencia agendas de atendimento (treinamentos, cursos, drones) e o link público de agendamento (`agendar.html`).

### Modelo agenda × instrutor (2026-08-05, migration 084)
- 1 agenda por instrutor (UNIQUE em `atend_agendas.instrutor_id`)
- Agenda de unidade coletiva: `instrutor_id NULL` — só admin gerencia
- Cada agenda tem `slug` único → link direto `agendar.html?agenda=<slug>` cai direto no formulário do instrutor
- Link público geral `/agendar.html` continua funcionando (cliente escolhe agenda no passo 1)

### Modalidade (unificada internamente)
- Antes: `atend_agendas.tipo` restringia a agenda a `fisica` OU `online`; capacidade separada
- **Agora:** toda agenda oferece as duas modalidades por padrão (campos `oferece_presencial`/`oferece_online`, ambos 1 por default)
- Cliente escolhe presencial ou online no público
- **Internamente 1 slot = 1 vaga total**: um agendamento (qualquer modalidade) ocupa o horário inteiro. Instrutor faz 1 atendimento por vez
- Curso e drone continuam sendo APENAS presenciais (regra física — precisa laboratório/drone real)

### Aprovação
- ADMIN/TI/RESPONSAVEL_GRUPO Suporte: aprova/recusa qualquer agendamento
- USER do Suporte (`op`): aprova/recusa APENAS os da própria agenda (helper `_pode_aceitar_agendamento`)
- `/pendentes` filtra por `instrutor_id = user.id` quando nível é `op` — cada instrutor vê só a sua fila
- Backend garante o guardrail via 403; frontend também filtra pra UX

### Notificação quando cai agendamento novo (público → pendente)
- **Cliente** recebe email "recebido, aguardando confirmação" (`_dispatch_email_agendamento`)
- **Instrutor dono da agenda + todos RESPONSAVEL_GRUPO Suporte** recebem:
  - Notificação in-app (`notificacoes` tipo `atend_novo_agendamento`)
  - Email do agendamento (mesmo template `email_equipe_novo_agendamento`)
- Legado `EQUIPE_AGENDA_EMAILS` continua ativo se configurado no .env (dispara email adicional pra caixa coletiva)
- Todas as falhas de email/notif são silenciosas (não bloqueiam o endpoint)

---

## Permissões / Autoriazação de páginas

Sistema refatorado em 2026-05 (`docs/PLANO_PERMISSOES.md`). Fonte da verdade é o banco.

### Fluxo
1. Admin cadastra page em `permission_pages` (ou já vem via migration)
2. Concede acesso via role (`permission_page_role`) OU via grupo (`permission_page_group`)
3. Frontend chama `/api/permissions/me/menu?user_id=X` — devolve page_keys permitidas
4. `nav.js` filtra sidebar contra essa lista
5. `page-guard.js` (em cada HTML) valida no boot que user tem acesso — redireciona senão

### page_key vs URL
- Convenção: page_key = nome do arquivo em UPPERCASE (`comercial.html` → `COMERCIAL`)
- Overrides pontuais em `nav.js:_PAGE_KEY_OVERRIDES` (ex: `/SistemaCPE/index.html` → `DASHBOARD`)

### Adicionar página nova
1. Cria HTML em `web/pages/`
2. Migration cria row em `permission_pages` + `permission_page_role` (ADMIN default)
3. Adiciona entrada no `globalMenu` de `nav.js`
4. Bump `?v=` do nav.js em todos os HTMLs

---

## E-mail transacional

### Dois perfis SMTP (necessário nos .env)
- `SMTP_*` — transacional default (reset senha, notificações de ticket/frota)
- `AGENDA_SMTP_*` — agendamento (convites de reunião via módulo Agenda)

### Regra rígida de teste
- Emails de teste vão **SEMPRE** pra `jonathan.lopes@cpetecnologia.com.br`
- Mesmo que o userEmail do harness aponte pra outro
- Motivo: evitar spam pra outros users durante desenvolvimento

---

## Rate-limit de login

Dict in-memory por (credential+IP):
- 5 falhas em 5min → 15min bloqueio
- Não persiste entre restarts (é in-memory)
- Se "sistema caiu" mas tudo tá UP → é 429 no login. `Restart-Service CPEControlAPI` zera.

**Bug crônico:** IP público NAT compartilhado — se 5 users diferentes de uma mesma empresa erram senha no mesmo horário, todos ficam presos. Fix permanente (chave por credential+ip) pendente. Ver `docs/GOTCHAS.md#rate-limit-login`.

---

## Notificações in-app

- Sino no header do sistema (renderizado por `nav.js`)
- Polling a cada 15s (não usa WS)
- Convites de task têm ID negativo (sintético) — não persistem no banco de `notificacoes`, vêm de `convites_espaco_TASK`
- Ao clicar: marca lida + redireciona pra origem (ticket, tarefa, reunião, agenda)

---

## Uploads

- **Frotas** (fotos do checklist): `web/uploads/fleet/`
- **Tickets** (anexos): `web/uploads/tickets/`
- **Comercial** (material apoio): `web/uploads/comercial/`
- **Avatares**: `web/uploads/avatars/`
- **Contratos** (PDFs): `web/uploads/contratos/`

Limite: 100MB por arquivo (config no endpoint). Streaming upload no material apoio (não carrega tudo em memória).

---

## Convenções de nomenclatura (por que "Faturamento" e "faturamento" coexistem)

- **Grupos antigos** foram criados com nomes inconsistentes (às vezes minúsculo, às vezes com acento, às vezes plural)
- Sistema **não trata** case-insensitivo — é literal
- Duplicações históricas viraram problema recorrente (ver GOTCHAS)
- **Regra atual:** sempre criar grupo com **Capitalized First Letter** — ex: "Faturamento", "Comercial"

---

## O que EXIGE autorização explícita do usuário

| Ação | Ok pra tocar sozinho? |
|---|---|
| Editar código dev local | Sim |
| Rodar SELECT em prod | Sim |
| UPDATE/DELETE em prod | **NÃO — pedir + dry-run primeiro** |
| Aplicar migration em prod | **NÃO** |
| Commit em qualquer branch | **NÃO** |
| Merge/push pra main | **NÃO** |
| Restart de serviço em prod | **NÃO** |
| Enviar email em prod | **NÃO** (mesmo que a lógica esteja pronta) |
