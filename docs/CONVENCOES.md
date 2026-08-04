# Convenções técnicas

Regras que vão te salvar de bug se seguir, ou custar horas se ignorar.

---

## Antes de MELHORAR / ATUALIZAR função existente: consulte a doc

**Regra global (2026-08-04):** toda vez que for melhorar ou atualizar uma função que já existe, **antes de escrever qualquer código**:

1. Ler `docs/MODULOS.md` — onde vive o módulo/função
2. Ler `docs/REGRAS_NEGOCIO.md` — regras aplicáveis (permissões, prazos, workflow)
3. Ler `docs/GOTCHAS.md` — bugs históricos naquela área
4. Ler este arquivo (`docs/CONVENCOES.md`) — se envolve JS global, MySQL, cache-buster, etc.
5. Consultar `docs/ENDPOINTS.md` — rotas vizinhas pra não duplicar/conflitar

Se descobrir contexto novo durante a mudança (regra que não estava documentada, gotcha novo, decisão), **atualize o `.md` correspondente no MESMO commit**.

Detalhamento do workflow em `AGENTS.md#se-você-for-uma-ia`.

**Por que existe:** manutenção sem consulta prévia já causou retrabalho múltiplas vezes — ver `docs/GOTCHAS.md` (routes/groups.py órfão, race WS, autofill "resolvido" 3x, etc.).

---

## MySQL: `use_pure=True` obrigatório

O `mysql-connector-python` 9.x tem uma C-extension com bug crônico — segfalta o processo Python quando usada. Toda `mysql.connector.connect()` **precisa** de `use_pure=True`.

```python
# ✅ CORRETO
conn = mysql.connector.connect(
    host=MYSQL_HOST, port=int(MYSQL_PORT),
    user=MYSQL_USER, password=MYSQL_PASSWORD,
    database=MYSQL_DB,
    use_pure=True,               # ← OBRIGATÓRIO
    charset="utf8mb4",           # ← evita mismatch com tabelas
    collation="utf8mb4_unicode_ci",
)

# ❌ QUEBRA — segfault imprevisível
conn = mysql.connector.connect(host=..., user=..., password=..., database=...)
```

**Sintoma quando esquece:** Event Viewer mostra Application Error 1000 (Access Violation 0xC0000005), serviço `CPEControlAPI` cai a cada 10-15min, healthcheck reinicia mas usuário vê "sistema fora do ar" intermitente.

**Todos os arquivos que abrem conexão MySQL devem seguir isso:**
- `server/database.py` (função canônica — sempre usar)
- `server/services/fleet_scheduler.py` (`_get_db_config`)
- Qualquer script novo

---

## Cache-buster em assets JS críticos

Cloudflare cacheia arquivos estáticos por horas. Se você alterar `nav.js` / `config.js` / `page-guard.js` sem mudar a URL, usuários vão continuar rodando versão antiga até o cache expirar.

**Regra:** todos os `<script src="…nav.js?v=AAAA-MM-DD">` precisam bumpar a data quando o arquivo mudar.

**Comando pra bumpar tudo de uma vez:**
```bash
cd c:/xampp/htdocs/SistemaCPE
OLD="2026-08-04"
NEW="$(date +%Y-%m-%d)"
for f in web/pages/*.html web/*.html; do
  [ -f "$f" ] && sed -i "s|?v=$OLD|?v=$NEW|g" "$f"
done
git diff --stat web/
```

**Não precisa bumpar** quando muda:
- CSS (baixa criticidade, tolerância a stale maior)
- HTML das pages (o próprio arquivo tem sua URL única — Ctrl+F5 resolve)
- Assets de módulo específico (só afeta 1 tela)

**Precisa bumpar** quando muda:
- `web/assests/js/nav.js`
- `web/assests/js/config.js`
- `web/assests/js/page-guard.js`
- `web/assests/js/api.js`
- Outros scripts referenciados por múltiplas páginas com `?v=`

---

## Ambiente: dev vs staging vs prod

### Como o backend sabe qual é
- Todos os 3 rodam do MESMO código
- Diferença é o `.env` passado no boot: `.env` (dev/prod) ou `.env.staging`
- `.env` local aponta pra `cpe_plus`; `.env.staging` aponta pra `cpe_plus_staging`
- **Não há flag "AMBIENTE=prod"** — o código não sabe onde está rodando

### Como o frontend sabe (`web/assests/js/config.js`)
```javascript
// Em localhost: seletor via localStorage.cpe_env ou ?env=X na URL
localStorage.cpe_env = 'dev'      // → chama API porta 8000
localStorage.cpe_env = 'staging'  // → chama API porta 8001

// Em domínio público (cpecontrol.cpetecnologia.com.br):
// Sempre 'dev' — força porta 8000. Não expõe staging pra externos.
```

### Passar `?env=staging` na URL
Aba anônima não herda `localStorage`. Se você mandar um link `.../meet.html?code=XXX` de staging pra um convidado externo abrir em anônima, ele cai em dev (padrão). O `?env=staging` força o config a ir pra 8001. Ver [comercial.html:meetingUrl()](web/pages/comercial.html) — o gerador de link injeta esse param quando está em staging local.

---

## `PUBLIC_BASE_URL` vs `Origin` do request

`config.py:PUBLIC_BASE_URL` é a URL pública padrão (`https://cpecontrol.cpetecnologia.com.br`). Serve pra emails transacionais (não têm request pra pegar origem).

**Mas pra links gerados a partir de um request** (ex: meeting_url do módulo Comercial), usar `Origin`/`Referer` do request:

```python
def _base_url_do_request(request: Request) -> Optional[str]:
    origin = (request.headers.get("origin") or "").strip()
    if origin:
        return origin.rstrip("/")
    referer = (request.headers.get("referer") or "").strip()
    if referer:
        from urllib.parse import urlparse
        p = urlparse(referer)
        if p.scheme and p.netloc:
            return f"{p.scheme}://{p.netloc}"
    return None

# Uso:
base = _base_url_do_request(request) or (PUBLIC_BASE_URL or "").rstrip("/")
meeting_url = f"{base}/SistemaCPE/web/pages/meet.html?code={code}"
```

**Por quê:** se você cria reunião em staging local (`localhost:80`) e o link volta com `PUBLIC_BASE_URL` (prod), o cliente clica → cai em prod → prod não tem a sala no banco → "Sala não encontrada".

---

## `/api/auth/me` pra revalidar role

Frontend guarda `localStorage.cpe_user` (setado no LOGIN). Se admin muda role/grupo do user, cache do browser fica stale — user precisa deslogar/logar pra ver botões novos.

**Fix defensivo:** no boot das páginas críticas, chamar `/api/auth/me` e resincronizar. Padrão:

```javascript
let ME = JSON.parse(localStorage.getItem('cpe_user') || 'null');
let ROLE = ME?.role || '';
let ELEVATED = ['RESPONSAVEL_GRUPO','ADMIN','TI','MANAGER'].includes(ROLE);
// ← 'let' (não const) porque syncMeFromServer() pode atualizar

async function syncMeFromServer() {
  try {
    const res = await fetch(`${_API_HOST}/api/auth/me`, { credentials: 'include' });
    if (!res.ok) return false;
    const { user } = await res.json();
    if (!user) return false;
    ME = { ...ME, ...user };
    ROLE = ME.role || '';
    ELEVATED = ['RESPONSAVEL_GRUPO','ADMIN','TI','MANAGER'].includes(ROLE);
    localStorage.setItem('cpe_user', JSON.stringify(ME));
    return true;
  } catch (e) { return false; }
}

document.addEventListener('DOMContentLoaded', async () => {
  await syncMeFromServer();
  // ... resto da inicialização (agora ROLE/ELEVATED estão frescos)
});
```

Aplicado em `tasks.html`. **Considerar aplicar** em outras páginas com gate de UI baseado em role (users.html, groups.html, permissions.html).

---

## Autofill guard nos inputs de busca

Chrome/Edge insistem em preencher inputs `type="text"` com credencial salva do login, mesmo com `autocomplete="off"`. O único hack que funciona 100% é **`readonly` + `onfocus`**.

**Como está implementado:**
1. Script Python varreu HTMLs e adicionou 3 atributos em cada input de busca: `autocomplete="off" data-lpignore="true" data-1p-ignore="true"`
2. Cada HTML tem um `<script id="cpe-autofill-guard-v1">` no fim do body que:
   - Encontra inputs com `data-lpignore="true"`
   - Aplica `readonly` no boot
   - Remove `readonly` no `focus`, recoloca no `blur` se vazio
   - `MutationObserver` cobre inputs criados dinamicamente

**Detecção conservadora:** só toca em inputs cujo id/name/class/placeholder contém `busca|buscar|search|filtro|filter|pesquisa|pesquisar`. Nunca em campos de formulário (email, senha, cpf).

**Login preservado:** `login.html` não tem `data-lpignore` → autofill de credencial continua funcionando lá.

---

## MariaDB 10.4 gotchas

- `TIMESTAMP` sem `NULL DEFAULT NULL` explícito quebra migration:
  ```sql
  -- ❌ ERRO
  `classificado_em` TIMESTAMP DEFAULT NULL,
  -- ✅ OK
  `classificado_em` TIMESTAMP NULL DEFAULT NULL,
  ```
- Não tem `WITH RECURSIVE` em versões muito antigas — check
- JSON functions funcionam mas com nomes diferentes de MySQL 8

---

## SQLAlchemy: sempre bind params

`text()` com `:placeholder` **precisa** de dict de bind — senão SQLAlchemy explode com `StatementError`.

```python
# ❌ QUEBRA
conn.execute(text("DELETE FROM tabela WHERE id = :id"))

# ✅ CORRETO
conn.execute(text("DELETE FROM tabela WHERE id = :id"), {"id": item_id})
```

Bug já capturou 1 vez: [server/app.py:groups delete](server/app.py) tinha esse bug — usuário reportou como "excluir não funciona" pois o `except Exception` engolia o erro.

**Cursor MySQL cru** (`cursor.execute`) usa `%s`:
```python
cursor.execute("DELETE FROM tabela WHERE id = %s", (item_id,))
```

---

## Frontend: modais sempre com grid Bootstrap

Regra rígida. Campos **lado a lado**, nunca empilhados.

```html
<!-- ✅ CORRETO -->
<div class="row">
  <div class="col-md-6">
    <label>Nome</label>
    <input type="text" class="form-control">
  </div>
  <div class="col-md-6">
    <label>Empresa</label>
    <input type="text" class="form-control">
  </div>
</div>

<!-- ❌ ERRADO -->
<div>
  <label>Nome</label>
  <input type="text" class="form-control">
</div>
<div>
  <label>Empresa</label>
  <input type="text" class="form-control">
</div>
```

Modais grandes: `modal-lg` ou `modal-xl` — usar generosamente. Sistema é intranet, tela grande.

---

## Rate-limit de login (não desativar)

Existe por segurança — impede brute-force. **Nunca comentar/desativar** sem discutir. Ver `docs/GOTCHAS.md#rate-limit-login` pra fix permanente sugerido.

---

## Emojis nos commits

Padrão do repo usa emoji nos logs (`✅ ❌ 🗑️ 📥 🔍`). Manter. Não precisa exagero.

---

## Sistema `NÃO PODE` falhar silencioso

**Regra global:** todo `except Exception` deve logar antes de raise. Nunca `except: pass`. Nunca "return default silencioso" sem log.

Se algo falhar em prod, precisamos rastrear via `\\CPEDC22\E$\CPE\logs\`. Silêncio = tempo perdido em diagnóstico.

```python
# ❌
try:
    fazer_coisa()
except:
    pass

# ✅
try:
    fazer_coisa()
except Exception as e:
    logger.error(f"[MODULO] falha em fazer_coisa: {e}")
    raise  # ou tratamento explícito
```

---

## Convenção de arquivos

- **Nunca criar `*.md` novo** sem pedido explícito do user (regra global do sistema Claude Code)
- **Docs** ficam em `docs/` (já existe)
- **Scripts one-shot** vão no scratchpad, não no repo
- **Migrations** numeradas sequencialmente — nunca reutilizar número
- **Nome de tabela nova** — se possível prefixar por módulo (ex: `comercial_*`, `fleet_*`)

---

## Comentários no código

- **Default: sem comentário.** Nome bom explica.
- **Comentar QUANDO:** WHY é não-óbvio — hidden constraint, workaround pra bug específico, invariant sutil
- **Nunca comentar:** referência a issue/PR fechada, "adicionado em X", "usado por Y"

---

## Testes

- **Não existe cobertura ampla.** `server/tests/` tem smoke pontual.
- **Estratégia atual:** ruff + pre-commit + smoke test manual. Pytest só quando bug reportado pelo user.
- Sistema não pode falhar silencioso — logs são o "teste em produção".

---

## Emails de teste

Regra rígida: **SEMPRE** pra `jonathan.lopes@cpetecnologia.com.br`. Mesmo que `userEmail` do harness aponte pra outro. Motivo: evita spam durante desenvolvimento.

---

## Backup e recuperação

- Backup MySQL diário — automação **pendente** (task memory de 2026-05-26)
- Snapshot atual: `cpe_plus_snapshot` no MySQL local (usado pra staging)
- Restore destrutivo: `mysql -uroot -pXXX cpe_plus < backup.sql`

---

## Coisas que parecem convenção mas não são

- Diretório `web/assests/` — typo perpetuado. **Não renomear** — quebra ~200 referências.
- `cpe_grupo` em vez de `cpe_grupos` — singular, mantido por compat.
- Alguns endpoints com prefix duplicado (ex: `/api/api/…`) — legado, evitar mas não corrigir hoje.
