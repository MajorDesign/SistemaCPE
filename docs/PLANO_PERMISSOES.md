# Refatoração do Sistema de Permissões

**Iniciado:** 2026-05-05
**Modo:** Opção B — refatoração completa em 4 fases
**Status atual:** _atualizar conforme avança_

> Este arquivo é a **fonte da verdade** do progresso. Cada sessão deve atualizar esta tabela.

| Fase | Status | Data |
|------|--------|------|
| Setup (memórias + plano + testes) | ✅ done | 2026-05-05 |
| 1. Banco + Backend | ✅ done (12/12 smoke-test) | 2026-05-05 |
| 2. Front (permissions.html refatorado) | ✅ done | 2026-05-05 |
| 3. Page-guard único + migrar páginas | ✅ done (20/20 páginas) | 2026-05-05 |
| 4. Limpeza | ✅ done (13/13 smoke-test) | 2026-05-05 |

## ✨ REFATORAÇÃO COMPLETA

Resumo final:
- **1541 → 228 linhas** de scripts de access control (-85%)
- **17 → 21 páginas** no catálogo (cobertura completa do sistema)
- **CSV → relacional** no modelo de dados
- **Hardcoded em 2 lugares → fonte única no banco** + seeder Python
- **0 endpoints legados** restantes
- **Tabela `page_permissions` renomeada** pra `_legacy_page_permissions` (rollback possível)
- **13/13 smoke-tests passando**

---

## Diagnóstico do legado (problemas a resolver)

1. `PAGES_CONFIG` hardcoded em `permissions.html` linhas ~477-573 (16 páginas) **e** `page_permissions` no banco (17 entradas) — desincronizados
2. Páginas existentes na pasta sem cadastro: **AGENDA, AVALIACOES, CONTRATOS, FLEET, RECEPCAO**
3. `page_permissions.allowed_roles` é string CSV (`"ADMIN,TI"`) — anti-pattern relacional
4. 4 scripts coexistindo (1541 linhas):
   - `web/assests/js/per_usuario/access-config.js` (418)
   - `web/assests/js/per_usuario/page-access-control.js` (118)
   - `web/assests/js/per_usuario/role-permissions.js` (236)
   - `web/assests/js/route-protection.js` (769)
5. `localStorage.PAGE_PERMISSIONS` como canal de configuração entre usuários — desatualiza
6. `MANAGE_CATEGORIES` está em `page_permissions` mas é uma feature, não página (mistura conceitos)
7. Não há checagem por `cpe_grupo` — só role
8. Bug: UI mostra `MANAGER` mas o enum no banco não tem (USER, TI, ADMIN, RESPONSAVEL_GRUPO)

---

## Arquitetura alvo

### Banco (3 tabelas novas)

```sql
permission_pages (
  page_key VARCHAR(50) PRIMARY KEY,
  display_name VARCHAR(100) NOT NULL,
  description VARCHAR(255),
  category VARCHAR(20) DEFAULT 'operational',  -- 'admin' | 'operational' | 'config'
  icon VARCHAR(50) DEFAULT 'bi-file-earmark',
  url VARCHAR(150),
  ordem INT DEFAULT 100,
  is_active TINYINT(1) DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)

permission_page_role (
  page_key VARCHAR(50),
  role ENUM('USER','RESPONSAVEL_GRUPO','TI','MANAGER','ADMIN'),
  PRIMARY KEY (page_key, role),
  FK page_key → permission_pages ON DELETE CASCADE
)

permission_page_group (
  page_key VARCHAR(50),
  group_id INT,
  PRIMARY KEY (page_key, group_id),
  FK page_key → permission_pages ON DELETE CASCADE,
  FK group_id → cpe_grupo ON DELETE CASCADE
)
```

`user_access_exceptions` permanece intacta (já modela bem).
`page_permissions` velha vira `_legacy_page_permissions` na fase 4.

### Lógica canônica de checagem

```
1. user.role == 'ADMIN' → ALLOW
2. exists exception(user, page, 'block') → DENY
3. exists exception(user, page, 'allow') → ALLOW
4. user.role IN allowed_roles(page) → ALLOW
5. user.group_id IN allowed_groups(page) → ALLOW
6. else → DENY
```

### Backend (endpoints reformulados em `server/routes/permissions.py`)

- `GET /api/permissions/catalog` — pages + roles + groups (resposta única, consumida pelo front)
- `PUT /api/permissions/pages/{page_key}` — body `{roles, group_ids}` (substitui)
- `POST /api/permissions/pages` — admin cadastra página manual (raro)
- `GET /api/permissions/check?page=X&user_id=Y` — `{allowed, reason}` (canônica)
- `GET /api/permissions/me/menu?user_id=Y` — páginas que user pode ver (pra menu)
- (mantidos) `GET/POST/DELETE /api/permissions/exceptions/...`

### Frontend

- `permissions.html` refatorado: 4 abas (Por Role / Por Grupo / Exceções / Matriz). Auto-save com toast. Toggle iOS-like azul nos grupos.
- Novo `web/assests/js/page-guard.js` (~150 linhas) substitui os 4 scripts antigos.
- Cada página chama `<script>pageGuard('AGENDA')</script>` no head.

---

## FASE 1: Banco + Backend

### Critérios de aceitação

- [ ] Migration 024 aplica sem erro em dev
- [ ] Tabelas novas criadas: `permission_pages`, `permission_page_role`, `permission_page_group`
- [ ] Seeder popula `permission_pages` com **21 páginas** (16 atuais + 5 novas)
- [ ] Migrador copia regras de `page_permissions` (CSV) → `permission_page_role` sem perder nada
- [ ] `_legacy_page_permissions` mantida intacta (rollback possível)
- [ ] `GET /api/permissions/catalog` retorna lista completa
- [ ] `GET /api/permissions/check` aplica lógica canônica (testado p/ admin, user, exceção, grupo)
- [ ] Smoke-test `python server/tests/test_permissions.py` retorna **TODOS OK**

### Arquivos criados/alterados

- `server/migrations/024_permissions_refactor.sql` — NOVO
- `server/services/permission_seeder.py` — NOVO (PAGES_CATALOG)
- `server/services/permission_migrator.py` — NOVO (CSV → tabelas)
- `server/routes/permissions.py` — endpoints refatorados (mantém antigos como compat)
- `server/app.py` — chama seeder + migrator no startup
- `server/tests/__init__.py` — NOVO
- `server/tests/test_permissions.py` — NOVO (smoke-test)

---

## FASE 2: `permissions.html` refatorado

### Critérios de aceitação

- [ ] Carrega tudo via `GET /api/permissions/catalog` (zero hardcoded)
- [ ] 4 abas funcionais: **Por Role** / **Por Grupo** / **Exceções** / **Matriz**
- [ ] Toggle iOS-like azul nos grupos (parecido com a imagem que o usuário enviou)
- [ ] Auto-save em cada toggle com toast de confirmação
- [ ] Aba "Por Grupo" agrupa por departamento
- [ ] Mostra todas as 21 páginas (incluindo AGENDA, FLEET, etc.)
- [ ] Checklist visual em `docs/TESTE_PERMISSOES.md` passa todos os itens

### Arquivos alterados

- `web/pages/permissions.html` — reescrita completa
- `docs/TESTE_PERMISSOES.md` — checklist manual

---

## FASE 3: `page-guard.js` único + migrar páginas

### Critérios de aceitação

- [ ] `web/assests/js/page-guard.js` criado (~150 linhas)
- [ ] Funciona: token check + chama `/api/permissions/check` + redireciona/avisa
- [x] Páginas migradas (20/20 — `grep -l pageGuard web/pages/*.html | wc -l`):
  - [x] users.html, groups.html, permissions.html, tickets.html, tasks.html
  - [x] projects.html, inventory.html, password-vault.html, reports.html, billing.html
  - [x] knowledge-base.html, registrations.html, settings.html, download-agents.html
  - [x] chat.html, avaliacoes.html, agenda.html, fleet.html, recepcao.html, contratos.html

### Arquivos criados/alterados

- `web/assests/js/page-guard.js` — NOVO
- Cada `*.html` em `web/pages/` — substitui scripts antigos por page-guard

---

## FASE 4: Limpeza

### Critérios de aceitação

- [ ] `page_permissions` renomeada pra `_legacy_page_permissions` (após validação total)
- [ ] Scripts deletados:
  - [ ] `web/assests/js/per_usuario/access-config.js`
  - [ ] `web/assests/js/per_usuario/page-access-control.js`
  - [ ] `web/assests/js/per_usuario/role-permissions.js`
- [ ] `route-protection.js` reduzido (mantém só auth, delega permissões pro page-guard)
- [ ] Bloco `PAGES_CONFIG` removido de `permissions.html` (já carrega da API)
- [ ] Smoke-test e checklist visual continuam passando

---

## Como rodar os testes

```bash
# Smoke-test backend (precisa API rodando em :8000)
python server/tests/test_permissions.py

# Aplicar migrations no dev
/c/xampp/mysql/bin/mysql.exe -u root -p'Cpe@7482' cpe_plus < server/migrations/024_permissions_refactor.sql
```

## Rollback (se algo der errado em produção)

```sql
-- Volta a usar a tabela legacy
DROP TABLE permission_page_group;
DROP TABLE permission_page_role;
DROP TABLE permission_pages;
RENAME TABLE _legacy_page_permissions TO page_permissions;
```

E reverter via `git revert` os commits da refatoração.
