# Gotchas — bugs históricos e o que NÃO fazer de novo

Cada seção aqui foi um bug real que custou tempo. Lê antes de mexer em código próximo pra não redescobrir.

---

## MySQL segfault (Application Error 1000)

**Sintoma:** CPEControlAPI cai a cada 10-15min. Event Viewer mostra `Application Error 1000` com exit code `3221225477` (0xC0000005 ACCESS_VIOLATION).

**Causa:** `mysql-connector-python` 9.x + C-extension. Falha imprevisível.

**Fix:** todo `mysql.connector.connect(...)` **precisa** `use_pure=True` + `charset` + `collation`. Ver `docs/CONVENCOES.md#mysql-use_pureTrue-obrigatório`.

**Histórico:**
- 2026-07-16: descoberto na primeira vez após crash em cascata
- 2026-07-23: descoberto de novo em `fleet_scheduler.py:_get_db_config` que estava sem — fix específico

**Verificar periodicamente:** uptime do processo Python via WinRM + Event Viewer.

---

## routes/groups.py órfão

**Sintoma:** correção em `server/routes/groups.py` "não faz efeito" — request continua caindo no comportamento antigo.

**Causa:** o arquivo `routes/groups.py` **NUNCA foi importado** em `app.py`. Endpoints de grupo estão embutidos em `app.py` (`groups_router = APIRouter(prefix="/api/groups")` na linha 719+).

**Fix:** editar `app.py` (handler ativo), não `routes/groups.py`.

**Descoberto:** 2026-08-04, num fix de bloqueio 409 no delete de grupo.

**Ação recomendada:** ou (a) deletar `routes/groups.py` pra evitar confusão, ou (b) importar corretamente e remover do `app.py`. Ainda não feito.

---

## Rate-limit de login bloqueia IP NAT

**Sintoma:** usuário reporta "sistema caiu" mas health check está 200. `/api/auth/login` retorna 429.

**Causa:** dict in-memory em `server/app.py` bloqueia (credential+IP) por 15min após 5 falhas. Se uma empresa tem NAT (múltiplos users com mesmo IP público) e vários erram senha, todos ficam bloqueados.

**Fix imediato:** `Restart-Service CPEControlAPI` zera o dict.

**Fix permanente pendente:** chave por `credential+ip+timestamp_bucket` mais granular. Ou usar Redis. Ainda não implementado.

**Descoberto:** 2026-06-16.

---

## Caddy travamento

**Sintoma:** porta 443 mostra LISTENING mas requests externos retornam Cloudflare Error 1033. Localhost:443 responde OK, mas via Cloudflare tunnel dá erro.

**Causa:** bug crônico do Caddy — porta abre, mas processo não responde.

**Fix:** `Start-ScheduledTask CaddyServer` (existe task no Task Scheduler pra isso).

**Ordem de diagnóstico:**
1. **Verificar Caddy PRIMEIRO** — se Caddy está travado, mexer no cloudflared não adianta
2. `Get-Service Caddy | Restart-Service` OU `Start-ScheduledTask CaddyServer`
3. Se ainda falhar, testar cloudflared: `Get-Service Cloudflared | Restart-Service`

**Histórico:** 2026-05-29, 2026-06-01.

---

## Alterações em prazos fleet

**Sintoma:** ao mudar `INTERVAL X MINUTE` de algum job do fleet, o próximo tick pode cancelar em massa reservas que antes estavam OK.

**Motivo:** o job compara `NOW() >= condição`. Se você reduz o prazo (ex: 40min → 15min), reservas que antes estavam na janela passam a ser elegíveis.

**Regra:** antes de fazer deploy de mudança em prazo:
```sql
-- Dry-run: quantas reservas SERIAM canceladas com a NOVA regra?
SELECT COUNT(*) FROM fleet_reservations r
 WHERE r.status='aprovado'
   AND TIMESTAMP(r.data_reserva, r.horario_inicio) < DATE_SUB(NOW(), INTERVAL 4 HOUR)  -- ← novo prazo
   AND NOT EXISTS (...);
```
Mostrar ao usuário antes do deploy. Se der número alto, discutir.

**Histórico:** 2026-08-03 mudou de 40min/15min → 4h/4h. Dry-run mostrou 0 afetadas naquela hora.

---

## dev vs staging: manager de WS separado

**Sintoma:** convidado clica no link da reunião mas fica preso em "Aguardando aprovação" mesmo após host aprovar. Log do backend mostra `send_to_peer FAIL — peer nao esta no room`.

**Causa:** `meet.html` decide qual API chamar (`localhost:8000` = dev, `localhost:8001` = staging) via `localStorage.cpe_env`. Aba anônima não herda localStorage → cai em `dev` por padrão. Se host está em staging (`:8001`) e guest em dev (`:8000`), cada uvicorn tem seu próprio `manager` in-memory de WebSockets. As conexões estão em processos diferentes.

**Fix:** link do meet inclui `&env=staging` quando gerado em staging local. `config.js` reconhece `?env=X` na URL e persiste em localStorage.

**Aplicado em:** `web/assests/js/config.js`, `web/pages/comercial.html:meetingUrl()`, `web/pages/meet.html:copiarLink()`.

**Prod não tem esse problema** — só existe UMA API (8000).

---

## `cpe_chat` compartilhado dev+staging

**Sintoma:** você cria uma sala em staging local, testa OK. Alguém faz o mesmo em dev e o code aparece nas 2 APIs.

**Causa:** `.env` e `.env.staging` **não** sobrescrevem `MYSQL_CHAT_DB` — ambos apontam pro mesmo `cpe_chat`. Só o `MYSQL_DB` (principal) muda.

**Impacto:** compartilhamento é OK pra testes, mas se algum código depender de isolamento do chat entre ambientes, vai furar.

**Prod não tem esse problema** — está em outro servidor MySQL.

---

## Grupos duplicados por case

**Sintoma:** dois grupos com nome parecido (ex: "Faturamento" id=5 e "faturamento" id=10). Deleção de um bloqueia por dependências.

**Causa:** sistema não trata case-insensitive. Grupos criados historicamente com nomes divergentes convivem.

**Fix caso a caso:**
1. Identificar qual é o "canônico" (geralmente o mais usado)
2. Migrar dependências pro canônico (users, contratos, pré-cadastros, permissões)
3. Deletar o duplicado

**Regra futura:** sempre criar grupo com Capitalized First Letter. Ver `docs/REGRAS_NEGOCIO.md#convenções-de-nomenclatura`.

**Delete de grupo agora bloqueia com 409** e lista dependências (fix 2026-08-04). Ver `server/app.py:delete_group`.

---

## Meetings: race no reconnect WS

**Sintoma:** guest reconecta WS após queda de rede breve. Host aprova. Aprovação chega no peer errado (o antigo que já caiu) → guest fica preso.

**Causa:** `finally` do handler WS chama `disconnect(peer_id)` incondicional. Se a WS antiga caiu depois que a nova reconectou, o disconnect deleta a NOVA no mapa.

**Fix:** `manager.disconnect(peer_id, only_if_ws=websocket)` — só remove se a WS registrada é a mesma que caiu. Aplicado em `server/routes/meetings.py`.

---

## TURN pendente (reuniões internacionais)

**Sintoma:** reunião conecta OK no Brasil, mas convidado internacional (França, EUA) não recebe áudio/vídeo.

**Causa:** WebRTC mesh usa STUN público apenas. Sem TURN server, conexões atrás de NAT restrito (comum fora do BR) falham silenciosamente.

**Fix pendente:** subir TURN server (coturn) e configurar credenciais efêmeras. Sistema já tem cache de `iceServers` em `meet.html` (`_ICE_CACHE`) — só falta o backend devolver TURN via `/api/meetings/turn-credentials`.

**Prioridade:** próxima fase de reuniões.

---

## Capacidade máxima da reunião

WebRTC mesh escala mal — cada peer envia seu stream pra TODOS os outros. Com ~8 pessoas, cada peer manda 7 streams = 7× uplink. Além disso, encoding CPU vira gargalo.

**Config atual:** `MAX_MEETING_PARTICIPANTS = 8` (default em `.env`).

**Pra escalar >10:** precisa SFU (mediasoup, janus). Muito trabalho — não previsto ainda.

---

## Autofill do Chrome em campos de busca

**Sintoma:** ao entrar em qualquer página com campo de busca, o Chrome preenche automaticamente com a senha salva do login. Usuário tem que apagar toda vez.

**Causa:** Chrome ignora `autocomplete="off"` em `type="text"`. Analisa a página como um todo e "acha" que é login.

**Fix real:** hack `readonly` + `onfocus`. Chrome NÃO preenche input readonly. Ao clicar, JS remove readonly.

**Aplicado em:** todos os HTMLs do sistema via script Python — 31 inputs em 18 páginas. Cada HTML tem `<script id="cpe-autofill-guard-v1">` no fim do body.

**Login preservado:** `login.html` não tem `data-lpignore` → autofill continua funcionando lá.

---

## Cloudflare cache stale

**Sintoma:** você fez deploy do JS novo, testou local OK. Em prod continua rodando o antigo mesmo após Ctrl+F5.

**Causa:** Cloudflare cacheia por padrão. `Cache-Control: max-age=3600` (padrão) = 1h stale.

**Fix:**
1. Cache-buster `?v=data` em quem carrega o JS (URL nova = cache miss)
2. **Em emergência:** purge cache no dashboard da Cloudflare

---

## Uploads: tempo de streaming

Material apoio (comercial) aceita até 100MB. Se o upload demora muito (>60s), Uvicorn pode dropar. Verificar `keep_alive_timeout` no boot do uvicorn (não configurado hoje — usa default 5s).

Ainda não deu problema em prod, mas fica de olho.

---

## Firewall porta 8000 CPEDC22

Regra "CPE Control API - porta 8000" libera 172.16.0.0/16 → 8000 (agente inventário Windows + termo notebook).

**Sintoma:** agente parou de reportar hardware/software.

**Causa:** Windows Update às vezes reseta regras de firewall custom.

**Fix:** recriar via PowerShell:
```powershell
New-NetFirewallRule -DisplayName "CPE Control API - porta 8000" `
  -Direction Inbound -Protocol TCP -LocalPort 8000 `
  -RemoteAddress 172.16.0.0/16 -Action Allow
```

Verificar periodicamente (mensalmente é OK).

---

## Component NÃO é serviço Windows

Alguns componentes históricos rodavam atrelados ao logon do jonathan.lopes — se ele deslogava, tudo caía.

**Status atual:** TUDO migrado pra serviço Windows autônomo (CPEControlAPI, Caddy, Cloudflared). XAMPP MySQL como serviço.

**Verificar se novos componentes seguem isso.** Task Scheduler + Startup Registry não são substitutos aceitáveis.

---

## Healthcheck auto-restart

- SCM Failure Actions do serviço `CPEControlAPI`: 1ª falha = restart, 2ª = restart, 3ª = alerta
- Task Scheduler externo (a cada 2min): `healthcheck.ps1` pinga `/health`, restart se 3 falhas seguidas
- Cobrem tanto crash quanto travamento silencioso (API viva mas health hangando)

**Log:** `\\CPEDC22\E$\CPE\logs\healthcheck-api.log`

---

## XAMPP Control Panel: erros vermelhos falsos

Painel mostra erros/serviços offline mesmo com sistema funcionando. **Não confiar no XAMPP Control** — tudo virou serviço Windows autônomo.

Pode fechar o painel.

---

## SMTP: 2 perfis obrigatórios

- `SMTP_*` — transacional default (reset senha, tickets, frota, etc.)
- `AGENDA_SMTP_*` — módulo agenda (convites de reunião via Carbonio)

Ambos precisam estar preenchidos em `.env` de prod. Conferir antes de deployar nova feature de email.

---

## Deleção de user com FK

**Sintoma:** `DELETE FROM users WHERE id=X` falha com `Cannot delete or update a parent row: a foreign key constraint fails`.

**Causa:** users têm dezenas de FKs vindas de tabelas (fleet_reservations, tickets, comercial_reunioes, etc). Só `ON DELETE SET NULL` cobre algumas.

**Fix:** **soft delete** — `UPDATE users SET is_active=0, email=CONCAT('DEL_', email) WHERE id=X`. Preserva histórico, tira do sistema.

Padrão usado em testes locais e recomendado pra prod.

---

## Modais empilhando campos verticalmente

**Sintoma:** modal com 4-5 campos empilhados, feio, aproveita mal a tela.

**Fix:** sempre `row + col-md-6` (2 colunas), modais em `modal-lg` ou `modal-xl`.

Regra rígida do sistema. Ver `docs/CONVENCOES.md#frontend-modais-sempre-com-grid-bootstrap`.

---

## API `/api/users/me` inexistente

**Sintoma:** frontend tenta chamar `/api/users/me` e recebe 404.

**Causa:** endpoint canônico é `/api/auth/me`, não `/api/users/me`. Existem outros `/me` em outros routers (`chat.py`, `dashboard.py`) com propósitos diferentes.

**Fix:** usar `/api/auth/me` — retorna `{success, user: {id, name, email, role, group_id}}`.

---

## Checklist de fotos do fleet — ordem no frontend (2026-08-05)

**Sintoma:** condutor clica em "Finalizar devolução" e recebe erro "Faltam fotos: retorno_frente, retorno_lateral..." mesmo tendo tirado todas.

**Causa:** o `PUT /checklists/{id}/devolver` valida server-side que existam 7 fotos com `angulo` prefixado `retorno_`. Antes de 2026-08-05, o fluxo do frontend era: PUT devolver → depois upload das fotos. Com a nova validação, PUT rejeita porque as fotos ainda não subiram.

**Fix aplicado (fleet.html `saveDevolver`):** upload das fotos ANTES do PUT devolver. Fotos que falham (ex: duplicata rejeitada por hash) ficam no buffer `RET_INSPECTION_FILES` — condutor refaz e clica de novo, só reenvia as pendentes. PUT devolver só roda se todas subiram.

**Mesmo padrão vale pra `saveChecklist` (saída):** frontend valida `REQUIRED_ANGLES` antes de POST /checklists, mas o backend NÃO valida na criação (fotos ainda não existem). A validação server-side de saída acontece só no `vistoriar-saida` (bloqueio ao vistoriador). Se você mexer no fluxo de criação e precisar validar antes de vistoriar, use `_missing_checklist_angles(cursor, checklist_id, 'saida', needs_painel)`.

---

## Anti-burla de foto no checklist — hash SHA-256 (2026-08-05)

**Comportamento:** `POST /api/fleet/checklists/{id}/photos` calcula SHA-256 dos bytes e rejeita `400` se a mesma imagem já foi enviada nesse checklist (índice único `uq_checklist_hash`). Foto pode ser reusada em CHECKLISTS DIFERENTES (ex: caso de recusa + reenvio) — a chave é (checklist_id, file_hash).

**Não detecta:** foto ligeiramente diferente (mudança de 1 byte quebra o hash). Usuário determinado ainda consegue tirar screenshot recompactada. Mitigação real seria `getUserMedia` (câmera direta) — não foi aplicada nesta iteração pra evitar retrabalho de UX; ver 2026-08-05 pela decisão.

**Coluna nova:** `fleet_checklist_photos.file_hash CHAR(64)`. Uploads antigos ficam NULL — não bloqueiam nada, só não têm proteção retroativa.

---

## Convenção `docs/`

Já existe:
- `docs/PLANO_PERMISSOES.md` — histórico da refatoração de permissões
- `docs/TESTE_PERMISSOES.md` — checklist manual

Adicionados 2026-08-04:
- `AGENTS.md` (raiz)
- `docs/ARQUITETURA.md`
- `docs/DEPLOY.md`
- `docs/MODULOS.md`
- `docs/REGRAS_NEGOCIO.md`
- `docs/CONVENCOES.md`
- `docs/GOTCHAS.md`
- `docs/ENDPOINTS.md`

**Manter atualizado.** Toda mudança relevante em regra/convenção/bug histórico → adiciona aqui no mesmo PR.
