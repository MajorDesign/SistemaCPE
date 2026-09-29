# PLANO IDOR — Correcao de autorizacao de endpoints

**Status geral:** Fases 0-5 EM PRODUCAO desde 2026-09-29
**Backup pre-deploy:** tag `pre-idor-fix-2026-09-29` em origin
**Validacao final:** e2e 92/92 em local + smoke real HTTPS 10/10 na URL publica
**Bot Discord:** validado apos deploy (/vincular + /consultachamado OK)

## Motivacao

Auditoria de 2026-09-29 confirmou (via curl real) que ~100 handlers do
backend aceitavam `usuario_id` como **query param** ou **body Pydantic**
em vez de derivar a identidade do session token. Permitia:

- **Anonimo** (sem cookie/token): chamar `GET /api/tickets/by-numero/{X}`
  e receber o ticket completo, incluindo email do solicitante, descricao
  e campos personalizados.
- **User autenticado**: passar `?usuario_id=<id_de_um_admin>` e escalar
  permissao (spoof de role via query string).

Prova real (agora bloqueada):

```
Antes (2026-09-29 09:00):
  GET https://cpecontrol.cpetecnologia.com.br/api/tickets/by-numero/SUP-2026-00001
  -> 200 OK
  -> vazou: assunto, solicitante_nome, solicitante_email, group_name, descricao

Depois (2026-09-29 14:22):
  GET https://cpecontrol.cpetecnologia.com.br/api/tickets/by-numero/SUP-2026-00001
  -> 401 (Nao autenticado)
```

## Estrategia aplicada

Substituir toda leitura de `usuario_id` do cliente por `Depends(get_current_user)`
(ja existente em `server/security.py:222`). Mantido como compat pra frontend
legado que ainda passa o param:

```python
# Ainda aceita o query param antigo mas IGNORA (evita 422 no frontend legado)
_deprecated_usuario_id: Optional[int] = Query(None, alias="usuario_id",
                                              include_in_schema=False)
```

Para endpoints R3 (admin override legitimo — ex: ADMIN abrindo ticket em
nome de outro), usar helper novo `security.require_admin_override(current_user,
requested_user_id)` — retorna o `user_id` alvo se OK, 403 se USER comum tentou
spoofar.

## Faseamento final (todas concluidas)

| Fase | Foco | Handlers | Frontend? | Status |
|---|---|---:|---|---|
| **0** | Helpers em security.py + docs | 0 | nao | **em prod 2026-09-29** |
| **1** | 6 GETs criticos ja vazando | 6 | nao (compat) | **em prod 2026-09-29** |
| **2** | Notificacoes + avaliacoes + categorias | 12 | nao (compat) | **em prod 2026-09-29** |
| **3** | tickets.py restantes (Query + Body Pydantic + upload attachment) | 14 | nao (compat, cleanup adiado) | **em prod 2026-09-29** |
| **4** | Agenda + recepcao | 13 | nao (compat) | **em prod 2026-09-29** |
| **5** | Tasks (maior volume) | 55 | nao (compat) | **em prod 2026-09-29** |
| | **TOTAL** | **~100** | | |

## Endpoints refatorados por arquivo

- `server/routes/tickets.py` — 20 handlers (5 Query + 9 Body + upload + 4 Fase 1)
- `server/routes/notificacoes.py` — 3 Query
- `server/routes/avaliacoes.py` — 6 (2 Query + 4 R3)
- `server/routes/categorias.py` — 3 Query
- `server/routes/chamados_antigos.py` — 2 Query
- `server/routes/agenda.py` — 9 (8 R1 + 1 R3 special `dono_id` na Path)
- `server/routes/recepcao.py` — 4 (3 Query + 1 Body)
- `server/routes/tasks.py` — 55 (39 Query + 16 Body)

## Bot Discord — nao muda

`server/routes/discord.py` continua usando `X-Discord-Bot-Key`. O bot chama
`/api/tickets/*` com `X-Auth-Token` (session token do user vinculado); como
`get_current_user` aceita esse header, refactor **funciona nativamente**
para o bot sem tocar `discord.py`. Confirmado pos-deploy: `/vincular` +
`/consultachamado` funcionaram sem alteracao.

## Validacao pre-deploy (ambiente local, porta 8010)

4 scripts e2e reusaveis em `cpecontrol-desktop/scripts/`:

- `e2e-idor-tickets-fase1.mjs` — 30 checks (fluxo completo ticket + RBAC)
- `e2e-idor-fase2.mjs` — 20 checks (notif + avaliacoes + categorias)
- `e2e-idor-fase3-fase4.mjs` — 22 checks (body spoof + admin override + agenda + recepcao)
- `e2e-idor-fase5.mjs` — 20 checks (tasks CRUD basico + spoof rejeitado)

**Resultado**: 92/92 passando. Zero regressao, RBAC funcionando, spoof rejeitado, admin override correto.

## Smoke pos-deploy (URL publica HTTPS)

10 endpoints testados sem cookie: **10/10 retornaram 401** (antes vazavam).

## Debitos ainda pendentes (rastrear em prox onda)

### Fase 6 — extras descobertos pelo agente Fase 4

Handlers adicionais fora do escopo original que tambem aceitam
`usuario_id`/`solicitante_id`/`convidador_id`/etc no body sem validar:

**agenda.py:**
- `POST /api/agenda/login` — `body.usuario_id`
- `POST /api/agenda/logout` — `body.usuario_id`
- `POST /api/agenda/eventos` — criar evento com `usuario_id` no body
- `POST /api/agenda/compartilhar/solicitar` — `solicitante_id`
- `POST /api/agenda/compartilhar/{id}/responder` — `usuario_id`
- `POST /api/agenda/eventos/{id}/reenviar` — `usuario_id`

**recepcao.py:**
- `POST /api/recepcao/reservas/{id}/cancelar` — `body.usuario_id`
- `POST /api/recepcao/reservas/{id}/convidar` — `body.usuario_id` + `convidador_id`
- `POST /api/recepcao/convites/{id}/responder` — `body.usuario_id`
- `SalaCreate.criado_por`, `SalaUpdate.atualizado_por`
- `EscritorioCreate/Update.criado_por/atualizado_por`
- `EnvioCreate.remetente_id`

Mesmo padrao de bug, mesmo padrao de fix (`require_admin_override`).

### tasks.py:707 `adicionar_membro_espaco`

Excluido do refactor: o `body.usuario_id` tem uso ambiguo (e ao mesmo
tempo o requester E o target do INSERT em `espaco_membros_TASK`). Aparenta
bug de design do handler original (so permite manager que se auto-adiciona).
Troca silenciosa mudaria semantica sem consertar. Precisa revisao humana.

### Frontend cleanup (opcional, zero impacto funcional)

Remover `?usuario_id=` residual das ~24 chamadas em:
- `web/assests/js/tickets.js` (16)
- `web/assests/js/nav.js` (6)
- `web/assests/js/dashboard-sla.js` (1)
- `web/assests/js/agenda.js`, `recepcao.js`, `pages/tasks.html`, `reports.html`

Bumpar `?v=YYYY-MM-DD` de nav.js em todas as paginas (regra global de
cache-buster). Zero impacto no comportamento — backend ja ignora — so limpeza
+ reducao de log-noise.

## Historico

- **2026-09-29 09:00** — Auditoria security-auditor identifica IDOR
- **2026-09-29 10:00** — Plan agent mapeia 5 fases, ~82 handlers previstos
- **2026-09-29 11:30** — Fase 0 + 1 aplicadas em local, e2e 30/30
- **2026-09-29 12:00** — Fase 2 aplicada em local, e2e 20/20
- **2026-09-29 12:30** — Fase 3 aplicada em local (backend only, cleanup FE adiado)
- **2026-09-29 13:00** — Fases 4 e 5 aplicadas em paralelo (agentes background)
- **2026-09-29 14:00** — e2e master consolida 92/92 checks
- **2026-09-29 14:15** — Tag `pre-idor-fix-2026-09-29` criada em GitHub
- **2026-09-29 14:20** — Commit `4961053` em dev, merge `0645d1d` em main, push
- **2026-09-29 14:22** — Deploy SMB no CPEDC22 + Restart-Service CPEControlAPI
- **2026-09-29 14:23** — Smoke publico 10/10 = 401. Buraco fechado.
- **2026-09-29 14:30** — Bot Discord validado pelo usuario (/vincular + /consultachamado).
