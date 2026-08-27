# Multi-Grupo por Usuário

**Iniciado:** 2026-08-26
**Motivação:** Um usuário pode participar de mais de um grupo com role independente por grupo (ex: Giselle Lins é RESPONSAVEL_GRUPO em "Gente e Gestão" **e** RESPONSAVEL_GRUPO em "Financeiro"; outros podem ser RESPONSAVEL num grupo e USER em outro).
**Autorização:** Apenas ADMIN (admin master) pode adicionar/remover grupos de um usuário. Ninguém mais — nem TI, nem RESPONSAVEL_GRUPO.

> **Status vivo:** atualizar esta tabela a cada fase concluída.

| Fase | Escopo | Ambiente | Status | Data |
|------|--------|----------|--------|------|
| 1. Banco + UI admin | `user_groups`, migração dos dados atuais, endpoints CRUD, seção multi-grupo em `/users.html` (só ADMIN), botão "Membros" em `/groups.html` | dev local | ✅ concluída (smoke OK) | 2026-08-26 |
| 2. Leitura | Tickets, categorias, avaliações, relatórios passam a considerar `IN (grupos)` | dev local | ✅ concluída (smoke OK) | 2026-08-26 |
| 3. Escrita / permissões | SLA, `permission_page_group`, contratos, cofre de senhas | dev local | ⏳ pendente | — |
| 4. Deploy staging + prod | Smoke test completo, deploy | staging → prod | ⏳ pendente | — |

### Fase 2 — entregas

- `server/security.py`: `get_current_user` agora carrega `groups`, `group_ids`, `responsavel_group_ids` do banco (via `_load_user_groups`). Fallback pra `users.group_id` se `user_groups` vazio.
- `server/app.py` `POST /api/auth/login`: `UserResponse.groups` populado com lista completa.
- `server/routes/tickets.py` `obter_tickets`: filtro reescrito usando `user_groups` — RESPONSAVEL vê tudo dos grupos onde é responsável, USER vê tickets dos grupos onde é usuário (respeita restrição por categoria da migration 089).
- `server/routes/categorias.py` `_verificar_permissao`: valida via `user_groups WHERE role_in_grp = 'RESPONSAVEL_GRUPO'` (não só `users.group_id`).
- `server/routes/avaliacoes.py`: novo helper `_aplica_filtro_grupo_avaliacoes` substitui 3 blocos duplicados nos endpoints `/`, `/resumo`, `/por-responsavel`. RESPONSAVEL_GRUPO vê agregado de todos os grupos onde responde.
- `web/pages/reports.html`: dropdown de grupos filtrado — RESPONSAVEL só vê os grupos onde responde (via `/api/user-groups/{id}`).

Smoke test: fernanda (RESPONSAVEL em Financeiro + USER em Comercial) viu tickets dos 2 grupos + próprios; ADMIN viu todos; tickets em grupos alheios não vazaram.

### Fase 1 — entregas

- Migration `server/migrations/090_user_groups.sql` (tabela + backfill).
- Endpoints em `server/routes/user_groups.py` sob prefixo `/api/user-groups`:
  - `GET  /{user_id}`             — lista grupos (ADMIN/TI ou próprio user)
  - `GET  /by-group/{group_id}`   — membros do grupo (ADMIN/TI/membro do próprio grupo)
  - `POST /{user_id}`             — adiciona grupo (**ADMIN**)
  - `PATCH /{user_id}/{group_id}` — muda role_in_grp ou promove a primary (**ADMIN**)
  - `DELETE /{user_id}/{group_id}` — remove (**ADMIN**, bloqueia se único)
- `web/pages/users.html` seção **02b — Grupos adicionais** (só aparece para ADMIN).
- `web/pages/groups.html` botão **Membros** em cada card + modal com role por grupo.
- Smoke test cobriu: 200/403/404/409/400, ping-pong de primary, sincronização `users.group_id` ← `user_groups`.

---

## Decisões de produto (travadas)

1. **Role por grupo, não global.** Só `USER` e `RESPONSAVEL_GRUPO` viram por-grupo. `ADMIN` e `TI` continuam globais em `users.role` (não faz sentido "admin só num grupo").
2. **Cross-department permitido.** Admin pode colocar user em grupos de departamentos diferentes.
3. **Apenas ADMIN edita.** Endpoint gated por `role_global = 'ADMIN'`. RESPONSAVEL_GRUPO só visualiza os membros do próprio grupo.
4. **Grupo primário obrigatório.** Todo user tem exatamente 1 `is_primary = 1` — usado como default em UI e retrocompatibilidade com `users.group_id`.

## Modelo de dados

```sql
CREATE TABLE user_groups (
  user_id      BIGINT       NOT NULL,
  group_id     INT          NOT NULL,
  role_in_grp  ENUM('USER','RESPONSAVEL_GRUPO') NOT NULL DEFAULT 'USER',
  is_primary   TINYINT(1)   NOT NULL DEFAULT 0,
  added_by     BIGINT       NULL,      -- FK users.id, quem adicionou
  added_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, group_id),
  FOREIGN KEY (user_id)  REFERENCES users(id)     ON DELETE CASCADE,
  FOREIGN KEY (group_id) REFERENCES cpe_grupo(id) ON DELETE CASCADE,
  FOREIGN KEY (added_by) REFERENCES users(id)     ON DELETE SET NULL,
  UNIQUE KEY uk_primary  (user_id, is_primary)    -- garante 1 primário/user (com trigger)
);
```

Coluna `users.group_id` **mantida** como cache do grupo primário (retrocompat + queries rápidas). Fase 4 decide se remove ou continua sincronizada por trigger.

## Fluxo de payload do login (Fase 2 em diante)

```json
{
  "id": 111,
  "role_global": "USER",
  "primary_group_id": 17,
  "groups": [
    { "id": 17, "name": "Gente e Gestão", "role": "RESPONSAVEL_GRUPO", "primary": true },
    { "id": 5,  "name": "Financeiro",     "role": "RESPONSAVEL_GRUPO", "primary": false }
  ]
}
```

Helper no backend: `def user_group_ids(user_id) -> list[int]` — usado em todas as queries que hoje fazem `WHERE ... = current_user.group_id`.

## Endpoints (Fase 1)

| Método | Rota | Autorização | Descrição |
|--------|------|-------------|-----------|
| GET    | `/users/{id}/groups`             | ADMIN, TI, o próprio user | Lista grupos + role por grupo |
| POST   | `/users/{id}/groups`             | **ADMIN apenas**          | Adiciona grupo `{group_id, role_in_grp}` |
| PUT    | `/users/{id}/groups/{group_id}`  | **ADMIN apenas**          | Muda role no grupo ou marca primary |
| DELETE | `/users/{id}/groups/{group_id}`  | **ADMIN apenas**          | Remove grupo (bloqueia se for o único) |
| GET    | `/groups/{id}/members`           | ADMIN, TI, RESPONSAVEL_GRUPO do próprio grupo | Lista membros do grupo com role |

## Regras técnicas

- Deletar o único grupo do user → erro 400 ("todo usuário precisa estar em pelo menos 1 grupo").
- Adicionar grupo já existente → erro 409.
- Marcar `is_primary=1` num grupo → automaticamente desmarca o antigo primário do user + atualiza `users.group_id`.
- Ao remover o grupo primário → o próximo grupo (ordem `added_at ASC`) vira primário automaticamente.

## Impacto por área (mapa pra Fase 2/3)

| Área | Arquivo(s) | Complexidade | Fase |
|------|------------|--------------|------|
| Tickets — listagem | `server/routes/tickets.py` | Média | 2 |
| Tickets — encaminhar | `server/routes/tickets.py` | Baixa | 2 |
| Categorias — dropdown | `server/routes/categorias.py` | Baixa | 2 |
| Avaliações | `server/routes/avaliacoes.py` (`ROLES_REPORTS`, `_por_responsavel`) | Média | 2 |
| Relatórios | `web/pages/reports.html` | Baixa | 2 |
| SLA — edição | `server/routes/ticket_sla.py` | Baixa | 3 |
| Permissão de página | `server/routes/permissions.py`, `permission_page_group` | Média | 3 |
| Contratos | `server/routes/contratos.py`, `contrato_pastas` | Baixa | 3 |
| Cofre de senhas | `server/routes/password_vault.py`, `passwords.group_id` | **Alta (dado sensível)** | 3 |
| Chat — grupos herdados | `server/routes/chat.py` | Baixa | 3 |
| Login / JWT | `server/app.py` (`/auth/login`, `/me`) | Média | 2 |

## Riscos e mitigação

- **Vazamento entre grupos** → antes de cada deploy, smoke-test que loga como user-com-2-grupos e valida que só vê os 2. Ver `docs/TESTE_MULTIGRUPO.md` (a criar na Fase 4).
- **Cofre de senhas** → confirmar com quem cuida (Patrícia) que compartilhamento por grupo composto é o desejado antes de mexer.
- **Sessão desatualizada** → quando admin adiciona/remove grupo de outro user, esse user só vê a mudança no próximo login. Aviso na UI.
