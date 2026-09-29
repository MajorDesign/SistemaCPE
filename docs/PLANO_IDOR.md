# PLANO IDOR — Correcao de autorizacao de endpoints

**Data inicio:** 2026-09-29
**Status geral:** Fase 0 e 1 em execucao (ambiente local)
**Referencia:** `docs/REGRAS_NEGOCIO.md#autorizacao-de-endpoints`

## Motivacao

Auditoria de 2026-09-29 confirmou (via curl real) que ~82 handlers do backend
aceitam `usuario_id` como **query param** ou **body Pydantic** em vez de
derivar a identidade do session token. Isso permite:

- **Anonimo** (sem cookie/token): chamar `GET /api/tickets/by-numero/{X}` e
  receber o ticket completo, incluindo email do solicitante, descricao e
  campos personalizados.
- **User autenticado**: passar `?usuario_id=<id_de_um_admin>` e escalar
  permissao (spoof de role via query string).

Prova real registrada:

```
GET https://cpecontrol.cpetecnologia.com.br/api/tickets/by-numero/SUP-2026-00001
-> 200 OK
-> vazou: assunto, solicitante_nome, solicitante_email, group_name, descricao
```

## Estrategia

Substituir toda leitura de `usuario_id` do cliente por `Depends(get_current_user)`
(ja existente em `server/security.py:222`). Mantido como compat:

```python
# Ainda aceita o query param antigo mas IGNORA (evita 422 no frontend legado)
_deprecated_usuario_id: Optional[int] = Query(None, alias="usuario_id",
                                              include_in_schema=False)
```

Para endpoints R3 (admin override legitimo), usar helper novo
`security.require_admin_override(current_user, requested_user_id)`.

## Faseamento

| Fase | Foco | Endpoints | Frontend? | Status |
|---|---|---:|---|---|
| **0** | Helpers em security.py + docs | 0 | nao | **em execucao** |
| **1** | 6 GETs criticos ja vazando | 6 | nao (compat) | **em execucao** |
| 2 | Notificacoes + avaliacoes + categorias | 12 | nao (compat) | pendente |
| 3 | Tickets restantes + limpa frontend | ~14 + 4 arqs JS | **sim** | pendente |
| 4 | Agenda + recepcao | ~13 | **sim** | pendente |
| 5 | Tasks (39 handlers, maior volume) | 39 | **sim** | pendente |

## Escopo Fase 1 (em execucao)

Endpoints refatorados (backend somente, sem tocar frontend):

| Arquivo | Linha | Endpoint |
|---|---:|---|
| server/routes/tickets.py | 1524 | GET /api/tickets/by-numero/{numero} |
| server/routes/tickets.py | 1555 | GET /api/tickets/{ticket_id} |
| server/routes/tickets.py | 3461 | GET /api/tickets/{ticket_id}/linha-do-tempo |
| server/routes/tickets.py | 3518 | GET /api/ticket-interacoes/{ticket_id} |
| server/routes/chamados_antigos.py | 29 | GET /api/chamados-antigos/stats |
| server/routes/chamados_antigos.py | 180 | GET /api/chamados-antigos/ |

## Validacao Fase 1 (agente e2e, ambiente local porta 8010)

Casos obrigatorios pra aprovar Fase 1 pra producao:

1. `curl` sem cookie -> **401** em todos os 6 endpoints
2. `curl` com cookie de USER + `?usuario_id=<admin>` -> retorna dados do USER (Query ignorada)
3. USER autenticado abre modal do proprio ticket -> **200**
4. USER autenticado tenta abrir ticket alheio via URL -> **403**
5. Bot Discord com session token -> continua funcionando (aceita X-Auth-Token)
6. Fluxo completo de ticket (criar, comentar, anexar, encaminhar, status, relatorio) -> sem regressao

## Historico

- **2026-09-29**: auditoria confirmou vazamento, plano criado, Fase 0 e 1 iniciadas em local.
