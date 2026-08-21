# Gotchas — bugs históricos e o que NÃO fazer de novo

Cada seção aqui foi um bug real que custou tempo. Lê antes de mexer em código próximo pra não redescobrir.

---

## Reset de senha "com sucesso" mas usuário não conseguia logar (2026-08-21)

**Sintoma:** usuário pedia "esqueci minha senha", recebia email, definia senha nova, sistema mostrava "Senha redefinida com sucesso" — mas login com a nova senha continuava falhando. Log de reset dizia OK (`[AUTH/RESET] ✅ senha trocada user_id=X`). Usuários faziam 3-4 resets em minutos tentando resolver.

**Causa:** duas famílias de hash coexistindo no banco.
- `hash_password` em `utils.py` usa `pwd_context` (passlib) com `schemes=["argon2", "bcrypt"]` — o **primeiro** é o esquema padrão de HASH → reset gerava `$argon2id$...`
- O endpoint `/auth/login` em `app.py` usava **`bcrypt.checkpw` direto** — só entende `$2b$...`; num hash argon2 lança exceção "Invalid salt", cai no `except`, retorna 401.
- Users antigos com hash bcrypt continuavam logando OK. Quem resetasse virava hash argon2 → nunca mais logava → resetava de novo → loop.

O mesmo bug afetava `PUT /users/{id}/password` (endpoint de trocar senha logado): usava `bcrypt.checkpw` pra validar a senha atual — travava quem já tinha argon2.

**Fix aplicado (2026-08-21):**
- `login` e `change_password` agora chamam `utils.verify_password()` — que usa `pwd_context.verify()` (passlib) e aceita ambos os schemes.
- Cadastro de user novo trocado de `bcrypt.hashpw` pra `utils.hash_password` — padroniza tudo em argon2. Login/verify aceitam bcrypt histórico via passlib.
- Users que já resetaram (hash argon2 no banco) passaram a conseguir logar retroativamente com a última senha que digitaram — sem precisar migração de dados.

**Se voltar a acontecer:**
- Grep `bcrypt.checkpw\|bcrypt.hashpw` em `server/` — não deve retornar nada em código executável.
- Todo hash/verify de senha passa por `utils.hash_password` / `utils.verify_password`.
- `pwd_context` fica em `security.py` e é a única autoridade sobre esquemas aceitos.

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

**Causa:** o arquivo `routes/groups.py` **NUNCA foi importado** em `app.py`. Endpoints de grupo estão embutidos em `app.py` (`groups_router = APIRouter(prefix="/api/groups")` na linha 757+).

**Fix:** editar `app.py` (handler ativo), não `routes/groups.py`. **Atualização 2026-08-14** (commit 8e3b8cf): os dois arquivos foram endurecidos com as mesmas regras de permissão por role, então mudanças de comportamento agora batem em ambos os lugares. Se um dia o duplicado for removido, o outro já está pronto — mas siga cuidando de manter os dois iguais até isso acontecer.

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

## Função dentro de IIFE + `onclick=` inline não funciona

**Sintoma:** console imprime `Uncaught ReferenceError: nomeFuncao is not defined` ao clicar num botão que tem `onclick="nomeFuncao(...)"`. A função obviamente EXISTE no arquivo — grep encontra.

**Causa:** a função foi declarada como `function nomeFuncao() {}` **dentro de uma IIFE** (`(function(){ ... })();`). Toda declaração `function` dentro de IIFE fica no escopo da closure e **não** no `window`. O parser do `onclick=` inline no HTML só consegue resolver nomes que estão no escopo global (`window.*`).

**Fix:** expor no `window.*` antes do fechamento da IIFE, no mesmo padrão que as outras funções já expostas:
```javascript
(function () {
  async function liberarSolicitacao(id, email) { /* ... */ }

  // Antes do })():
  window.liberarSolicitacao = liberarSolicitacao;
})();
```

**Padrão alternativo** (usado no resto do mesmo bloco): declarar direto como `window.xxx = function() {}` ou `window.xxx = async function() {}`. Mantém o handler visível globalmente sem precisar de exposição separada.

**Como pegar antes de bugar:**
- Se você adicionar handler novo pra `onclick=` inline dentro de um `<script>` que abre com `(function(){` — SEMPRE expõe em `window.` no fim.
- Considera usar `addEventListener` em vez de `onclick=` — não sofre desse escopo.

**Descoberto:** 2026-08-07, no botão "Liberar" das solicitações de pré-cadastro em `users.html` (funções `liberarSolicitacao`/`recusarSolicitacao` presas na IIFE `<script>` do bloco pré-cadastro, linhas 2331-2803).

---

## Python 3.11 é requisito rígido — 3.12+ quebra na instalação

**Sintoma:** ao rodar `pip install -r server/requirements.txt` num venv de Python 3.12/3.13/3.14, falha em `pydantic-core` com erro do `link.exe` / `rustc` / `maturin failed`.

**Causa:** `pydantic-core==2.20.1` (dependência transitiva de `pydantic==2.8.2`) só publica wheels pré-compiladas até Python 3.11. Em versões mais novas o pip cai no fallback de compilação via Rust/maturin, que exige toolchain MSVC + rustup — nada disso vem por padrão no Windows.

**Fix:**
```bash
# 1. Instala 3.11 se não tiver
winget install --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
py -0                                # confirma que 3.11 aparece

# 2. Recria venv com 3.11
mv server/.venv server/.venv.old     # backup, deleta depois
py -3.11 -m venv server/.venv
server/.venv/Scripts/python.exe --version   # deve dizer 3.11.x

# 3. Instala deps normalmente
server/.venv/Scripts/python.exe -m pip install --upgrade pip
server/.venv/Scripts/python.exe -m pip install -r server/requirements.txt
```

**Prod usa 3.11.** Manter dev igual pra evitar bugs sutis (behavior de `asyncio`, `typing`, walrus edge cases).

**Descoberto:** 2026-08-07, em setup de máquina antiga que tinha só Python 3.14.

---

## `apply_migrations.sh` trava com `MYSQL_PASSWORD=` vazio no Windows

**Sintoma:** script imprime `============ Aplicando migrations em: cpe_plus ============` e nunca imprime mais nada. Task Manager mostra `mysql.exe` vivo consumindo 0% CPU indefinidamente.

**Causa:** o script chama `mysql -u root -p"$PASS"` — quando `$PASS` é vazio, vira `mysql -u root -p ""`. No Windows/Git Bash, `-p` sem valor (ou `-p ""`) faz o cliente MySQL **abrir prompt interativo** pedindo senha. Sem TTY conectado ao processo, fica bloqueado pra sempre.

**Fix (opção A — recomendada, alinha com prod):** setar senha real no MySQL local + `MYSQL_PASSWORD=senha` no `server/.env`. XAMPP padrão vem sem senha, mas nada impede setar uma só pro dev.

**Fix (opção B — quando não puder mexer no MySQL):** rodar migrations manualmente, uma por uma, omitindo `-p`:
```bash
for f in server/migrations/056_*.sql server/migrations/057_*.sql ... ; do
  name=$(basename "$f")
  "c:/xampp/mysql/bin/mysql.exe" -u root cpe_plus < "$f" \
    && "c:/xampp/mysql/bin/mysql.exe" -u root cpe_plus \
       -e "INSERT IGNORE INTO _migrations_log (nome) VALUES ('$name');"
done
```

**Fix (opção C — futuro):** patch no `apply_migrations.sh` pra montar comando sem `-p` quando `$PASS` vazio. Ainda não aplicado — se você fizer, teste em prod primeiro (onde a senha SEMPRE tem valor).

**Descoberto:** 2026-08-07, em setup de máquina onde XAMPP MySQL tinha root sem senha.

---

## `/api/groups` filtrada por role quebra dropdowns públicos (2026-08-17)

**Sintoma:** ao abrir o modal "Novo Ticket" em `tickets.html`, o dropdown "Setor de destino" mostra **só o próprio grupo do usuário** — impossível abrir chamado pra outro setor. Reportado por USER do Comercial.

**Causa:** o fix `8e3b8cf` (2026-08-14) tornou `GET /api/groups/` filtrado por role — USER/RESPONSAVEL_GRUPO só vê o próprio grupo. Faz sentido pra página de gestão (`groups.html`), mas quebrou os consumidores públicos: modal Novo Ticket, Encaminhar ticket, aba de grupos em `inventory.html` e `users.html`.

**Fix:** parâmetro `?scope=all` no `GET /api/groups/`. Consumidores públicos passam a chamar com `scope=all` (ignora filtro de role, lista todos os grupos ativos). O default `scope=managed` mantém o comportamento restritivo pra `groups.html`.

**Consumidores atualizados:**
- `tickets.js loadGroups()` → `/api/groups?scope=all`
- `inventory.html` → `/api/groups?scope=all`
- `users.html` → `API_GROUPS_URL + '?scope=all'`

**Regra pra futuros consumidores:** se o dropdown é usado por qualquer usuário pra escolher grupo (não é gestão), use `scope=all`.

---

## Ghost click após `input file capture=environment` fecha modal (2026-08-18)

**Sintoma:** condutor abre o modal de checklist em `fleet.html` no celular, toca em "Fotografar", tira a foto, dá OK — e o modal fecha, voltando pra listagem. Toda foto que tira, o form some. Não acontece no desktop.

**Reproduz em:** iOS Safari + Android Chrome (qualquer modal `.fleet-modal-overlay` que contém `<input type="file" capture="environment">`).

**Causa raiz:** o browser mobile dispara um **click sintético** ("ghost click") no ponto onde o dedo estava quando o intent da câmera termina. Se esse click cai sobre o overlay do modal (`.fleet-modal-overlay`) — muito comum, porque o modal ocupa a tela inteira e o overlay preenche qualquer área vazia — o listener global de "click fora fecha" dispara e derruba o modal. O usuário perde o form inteiro do checklist e volta pra lista.

Não tem `<form>` no arquivo. Não é submit implícito. Não é `page-guard.js`. É estritamente o ghost click no listener:

```js
document.addEventListener('click', e => {
  if (e.target.classList.contains('fleet-modal-overlay')) {
    e.target.classList.remove('open');
  }
});
```

**Fix aplicado (commit deste dia):** guard temporal.
1. Novo listener global captura `change` em qualquer `<input type="file">` e grava o timestamp em `_lastPhotoSelectedTs`.
2. Listener de click-fora consulta esse timestamp: se aconteceu há menos de **800ms**, ignora o click (ghost). Se não, fecha o modal normalmente.

```js
let _lastPhotoSelectedTs = 0;
document.addEventListener('change', e => {
  if (e.target?.type === 'file') _lastPhotoSelectedTs = Date.now();
}, true);

document.addEventListener('click', e => {
  if (e.target.classList.contains('fleet-modal-overlay')) {
    if (Date.now() - _lastPhotoSelectedTs < 800) return; // ghost click
    e.target.classList.remove('open');
  }
});
```

**Por que 800ms:** o ghost click chega tipicamente entre 100ms e 500ms depois do `change` do input. 800ms cobre com folga sem impedir o usuário de fechar o modal legitimamente (nenhum humano dá `change` + `click` em menos que isso conscientemente).

**Se voltar a acontecer**, checar nessa ordem:
1. O listener de `change` do input file continua no arquivo? (`_lastPhotoSelectedTs`)
2. O `if (Date.now() - _lastPhotoSelectedTs < 800) return;` continua no listener de click? Algum refactor pode ter apagado.
3. Novos modais `.fleet-modal-overlay` que contenham input file estão cobertos automaticamente (o guard é global). Se criaram outro tipo de overlay/modal fora dessa class, o listener não protege — precisa replicar o padrão.
4. O intervalo 800ms é conservador — se algum browser novo demorar mais que isso, aumentar. Testar com iOS Safari + Android Chrome + WebView de app corporativo.

**Como testar sem o celular:** difícil reproduzir no desktop porque desktop não tem intent de câmera. Testar em prod com um celular real. Um dev pode simular emulando `pointer:coarse` no Chrome DevTools + trigger manual `input.files = ...` + dispatch de click no overlay imediatamente depois — mas não é fiel ao bug real.

**Aplica também em `web/pages/tickets.html`?** Não — o `ticketDetailModal` é Bootstrap com `data-bs-backdrop="static"` (nunca fecha por click-fora). O bug é específico do padrão custom `.fleet-modal-overlay` do fleet.html.

---

## Checklist de saída zerava fotos quando algum upload falhava (2026-08-18)

**Sintoma:** condutor tira as 7 fotos no celular, aperta Enviar. Em 4G/wifi ruim, 1-2 fotos falhavam no upload. Sistema mostrava "algumas fotos falharam" e **limpava TODAS as fotos do buffer** — condutor precisava tirar as 7 de novo. Enquanto isso, no modal "Corrigir / adicionar fotos" (após vistoriador recusar) o upload funcionava bem porque é upload individual imediato.

**Causa:** dois fluxos assimétricos.
- `submitChecklist` (envio inicial): loop `for...of` sequencial + `Object.keys(CL_INSPECTION_FILES).forEach(k => delete ...)` incondicional no fim. Zerava até as que falharam.
- `abrirCorrigirFotos` (após recusa): upload imediato ao selecionar cada foto, tile fica "Erro" e user retenta só aquela.

**Fix aplicado:**
1. Helper `_tentarUpload(angKey, file)` faz **4 tentativas** (imediata + 3 retries com backoff 500ms/1500ms/4500ms). Erros 4xx (formato inválido, duplicata) não retentam — sem sentido. 5xx e falhas de rede retentam.
2. Só deleta do buffer as fotos que subiram OK. `anguloOK.forEach(k => delete CL_INSPECTION_FILES[k])`.
3. Se sobrou alguma pendente, **abre AUTOMATICAMENTE o modal `Corrigir/Adicionar`** com as fotos pendentes pré-carregadas nos inputs correspondentes (via `DataTransfer` + `dispatchEvent('change')`). User só precisa clicar em cada tile pra reenviar naquele fluxo robusto.

Mesmo padrão aplicado no fluxo de retorno (`RET_INSPECTION_FILES`).

**Se voltar a acontecer:**
1. Verificar console: `[FLEET UPLOAD]` mostra 4xx (falha permanente — não retenta) ou timeout?
2. Se 4xx recorrente: pode ser bug de conteúdo (foto duplicada por hash, formato inválido). Ver `api-stdout.log` do CPEDC22 com `[FLEET UPLOAD 400]`.
3. Se timeout persistente: rede do condutor está ruim demais pra 800KB de upload. Considerar redimensionar client-side antes de subir (não implementado).

---

## Devolução acusava "faltam fotos" mesmo com todas gravadas (2026-08-18)

**Sintoma:** condutor tenta finalizar devolução, upload de todas as 7 fotos completa (rows em `fleet_checklist_photos` com prefixo `retorno_`). Depois disso o PUT `/devolver` falha por outro motivo (ex: assinatura, KM). Ele fecha e reabre o modal — vê os previews das fotos já enviadas (`retornoByAng`), clica Registrar Devolução sem tirar foto de novo, e o sistema mostra "Faltam fotos da devolução: frente, lateral, ..." pintando todos os slots de vermelho.

**Caso real:** checklist 39, Evandro Vieira (2026-08-18 17:19-17:25). Todas 7 fotos gravadas às 17:19-17:20 (ids 326-332), depois ele reabriu o modal e o front pediu tudo de novo.

**Causa:** `handleRegistrarDevolucao` filtrava só o buffer JS `RET_INSPECTION_FILES` — que era zerado ao reabrir o modal em `openModalDevolucao`. O backend valida no banco e teria aceitado (via `_missing_checklist_angles`), mas o front bloqueava antes do PUT.

**Fix aplicado:** novo `RET_JA_ENVIADAS` (Set global) populado por `buildRetornoPhotoGrid` a partir de `retornoByAng` (fotos já no banco). Filtro passou a ser:
```js
REQUIRED_ANGLES.filter(k => !RET_INSPECTION_FILES[k] && !RET_JA_ENVIADAS.has(k))
```
Também marca no set após upload OK, cobrindo tentativa dupla sem reabrir.

**Se voltar a acontecer:** conferir se `buildRetornoPhotoGrid` está sendo chamado (ele popula `RET_JA_ENVIADAS`). Se sim, ver console: `RET_INSPECTION_FILES` + `RET_JA_ENVIADAS` juntos devem cobrir os 7 ângulos.

---

## Desistir do próprio checklist (2026-08-18)

Novo endpoint `DELETE /api/fleet/checklists/{id}` — condutor apaga próprio checklist antes da vistoria.

**Regras:**
- Autorizado: próprio condutor OU ADMIN/TI/MANAGER
- Status obrigatório: `aguardando_vistoria`. Depois de vistoriado, só gestor apaga
- Apaga registros (`fleet_checklists` + `fleet_checklist_photos` + `fleet_checklist_problems`) + arquivos físicos no disco (`os.remove` com tratamento de FileNotFoundError)
- **Não mexe na reserva vinculada** — se tinha reserva aprovada, continua ativa e o condutor pode refazer o checklist quando quiser

**Frontend:** botão vermelho "Desistir do checklist" no footer do modal detalhe, aparece só se `status='aguardando_vistoria'` E `currentUser.id === condutor_id`. Confirm dialog explica que reserva continua ativa.

---

## UI da chamada de voz some ao trocar de canal (2026-08-18)

**Sintoma:** você está em ligação com usuário A pelo chat, clica em outro canal (usuário B) pra responder mensagem — a UI da chamada desaparece. Áudio continua funcionando (você ouve, é ouvido), mas não tem como voltar a ver os botões (mute, encerrar, câmera, share). Voltar pra DM com A também não traz de volta (na verdade traz porque o `chatVoiceRoom` mora no canal aberto).

**Causa:** o container `<div id="chatVoiceRoom">` da UI de voz vive **dentro do main-content** — é filho da área do canal atualmente aberto. Quando o usuário chama `abrirCanal(B)`, o main-content re-renderiza pra mostrar B, e o `chatVoiceRoom` fica escondido. O estado `window._voiceState.canalId = A` e as PeerConnections WebRTC continuam vivas — por isso o áudio não para — mas a interface não segue o usuário.

**Fix aplicado (commit deste dia):** mini dock flutuante fixo (padrão Discord/Teams).
- Nova `<div id="chatCallDock">` `position:fixed; bottom-right`, `display:none` por default
- JS `window._atualizarCallDock()` decide mostrar/esconder:
  - Mostra se `_voiceState.canalId != null` **e** `_canalAtivo.id != _voiceState.canalId`
  - Esconde nos outros casos
- Dock tem: foto/inicial do peer, duração (mm:ss), botões **Voltar** (chama `abrirCanal(_voiceState.canalId)`), **Mute** (toggle mic), **Convidar** (abre modal), **Desligar**
- `abrirCanal` foi monkey-patched pra chamar `_atualizarCallDock()` no fim de cada troca
- `setInterval(1500ms)` como fallback (garante consistência se algum caminho esqueceu de chamar o hook)

**Bridge de escopo:** o dock mora em `<script>` separado após `</body>`. Como as vars principais do chat usam `let` no top-level do script principal, elas **não** vão pra `window` automaticamente. Foram expostas via `Object.defineProperty(window, '_canais', {get() { return _canais; }})` etc no fim do script principal.

**Se voltar a acontecer:**
1. Console: `window._voiceState.canalId` retorna número? Se `null`, a chamada não está ativa — outro bug (não é este).
2. `window._canalAtivo?.id` retorna número? Se `undefined`, o bridge de escopo quebrou (getter apagado).
3. `document.getElementById('chatCallDock')` existe? Se `null`, o HTML foi removido.
4. Ver console pra erros no `_atualizarCallDock`.

---

## Convidar 3º participante numa chamada 1-on-1 (2026-08-18)

Chamadas do chat usam a sala de voz do **canal DM entre os 2 users**. O 3º convidado não é membro do DM — se tentasse `voice_join`, backend bloqueava com 403 (`_usuario_pertence_ao_canal` = false).

**Fix:** whitelist in-memory + endpoint `POST /api/chat/channels/{id}/voice/invite`:
- `_voice_temp_invites: dict[int, set[int]]` em `routes/chat.py` (memória do processo — some se API reinicia; chamada cai junto de qualquer jeito)
- `voice_invite` valida que o chamador tem sessão de voz aberta no canal (só quem tá na call pode convidar), grava `user_id_alvo` no set e dispara WS `call_invite` pro alvo com o `channel_id`
- `voice_join` aceita se user é membro **OU** está no set de convidados temporários
- `voice_leave` remove o user do set — grant é efêmero por sessão
- WS broadcasts (`voice_join`, `voice_leave`) incluem os convidados no destino, senão o 3º não recebia notif dos outros peers

**Fluxo:** chamador clica no botão "Convidar" no dock → modal lista users ativos → seleciona → POST invite → alvo recebe modal de chamada tocando → aceita → `voiceEntrar(channel_id)` → vira 3º peer, todo o mesh WebRTC funciona normal (N-peers).

**Não persiste em DB** — refactor futuro pra tabela `chat_voice_temp_grants` se precisar auditoria/reinício resiliente. Por ora suficiente.

---

## Chamados antigos: vocabulário de status diferente do sistema novo (2026-08-17)

**Sintoma:** filtro por status na aba "Chamados antigos" de `tickets.html` retorna 0 pra qualquer opção que não seja "Resolvido". User seleciona "Aberto" ou "Em andamento" → tabela vazia.

**Causa:** as opções do select estavam hardcoded no HTML com o vocabulário do sistema NOVO (`Aberto`, `Em andamento`, `Resolvido`, `Fechado` — tabela `ticket_status`). Mas os `chamados_antigos` vieram do sistema legado, onde `nome_status` usa outro vocabulário: `Novo`, `Respondido`, `Em Progresso`, `Aguardando Resposta`, `Em Espera`, `Resolvido`.

Backend faz `WHERE nome_status = ?` (comparação exata case-sensitive). Só "Resolvido" batia por acidente. "Em andamento" ≠ "Em Progresso" (palavra + caixa alta diferentes).

**Fix (commit atual):** novo endpoint `GET /api/chamados-antigos/status` retorna `[{nome_status, total}]` distintos da própria tabela. Frontend popula o select dinamicamente ao entrar na aba (mesmo padrão de `/categorias`). Nunca mais desalinha, independente do vocabulário do legado.

**Regra:** ao popular dropdown com valores de tabela importada de outro sistema, prefira endpoint dinâmico em vez de hardcode — ou documente o mapeamento explicitamente.

---

## Auto-grant silencioso de permissão de categoria (2026-08-14)

**Sintoma:** membro do grupo aparece com uma restrição de categoria em `ticket_membro_categorias` que ninguém configurou manualmente. Responsável do grupo abre a modal "Permissões" e vê badge "N restrição(ões)" onde antes era "vê tudo".

**Causa:** feature de auto-grant. Quando um gestor **atribui** um ticket cuja categoria o novo responsável não tem permissão pra ver (ou quando o próprio user **assume** um ticket via `POST /tickets/{id}/assumir`), `conceder_acesso_auto()` em `routes/ticket_permissoes.py` insere uma linha em `ticket_membro_categorias` cobrindo aquela (sub)categoria. **Silencioso** — não avisa e não interrompe a atribuição.

**Regras do auto-grant:**
- Só dispara se o user já tem 1+ restrições (se ele "vê tudo", não mexe).
- Se ticket tem `subcategoria_id`, cria linha específica; senão, categoria inteira.
- Se cobertura já existe (categoria inteira ou subcategoria exata), não duplica.
- Falha silenciosa (log warning) — nunca bloqueia a atribuição.

**Não é bug — é feature.** Documentado em `REGRAS_NEGOCIO.md` (Tickets → Permissões por categoria).

**Como remover essa permissão auto-adicionada:** modal "Permissões" → membro → desmarcar → Salvar. Ou botão "Voltar ao padrão (ver tudo)" pra zerar todas.

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
