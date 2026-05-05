# Checklist de Teste — Permissões (Fase 2)

> Use este roteiro para validar a UI de `permissions.html` após cada mudança.
> Tempo estimado: ~5 min.

## Pré-requisitos

- [ ] API rodando em `http://127.0.0.1:8000`
- [ ] Smoke-test passando: `python -X utf8 server/tests/test_permissions.py`
- [ ] Logado como ADMIN no sistema (ex: `admin@cpe.com.br`)
- [ ] Ter ao menos 1 grupo cadastrado em `groups.html`

---

## Aba "Por Role"

- [ ] A aba abre com a lista de **21 páginas** (incluindo AGENDA, FLEET, RECEPCAO, CONTRATOS, AVALIACOES)
- [ ] Cada card mostra: ícone, nome de exibição, page_key, descrição
- [ ] Página DASHBOARD tem 5 toggles ligados (todos os roles)
- [ ] Página AGENDA tem todos os toggles desligados (era uma das faltantes — admin precisa configurar)
- [ ] Clicar em um toggle muda a cor pra azul (ligado) ou cinza (desligado)
- [ ] Após mudar um toggle, aparece **toast verde** "Roles de '...' atualizados" no topo direito
- [ ] Recarregando a página (F5), o estado do toggle **permanece** (foi salvo no banco)
- [ ] Aba "Matriz" reflete a mudança imediatamente

## Aba "Por Grupo"

- [ ] Aba abre com a mesma lista de 21 páginas
- [ ] Cada página mostra os grupos **agrupados por departamento** (ex: "TI", "Financeiro")
- [ ] Toggle azul iOS funciona igual à aba "Por Role"
- [ ] Auto-save funciona com toast
- [ ] Recarregando, o estado dos toggles permanece
- [ ] Se nenhum grupo estiver liberado, header diz "0 grupo(s) liberado(s)"

## Aba "Exceções"

- [ ] Lista mostra exceções existentes (se houver)
- [ ] Botão "Nova Exceção" abre modal
- [ ] Modal popula select de usuários e select de páginas
- [ ] Selecionar usuário + 2+ páginas + tipo "block" + motivo + Salvar → cria exceções
- [ ] Aba volta atualizada com os badges vermelhos (block) ou verdes (allow)
- [ ] Botão lixeira ao lado da exceção remove TODAS do usuário

## Aba "Matriz"

- [ ] Tabela mostra todas as 21 páginas
- [ ] Colunas: Página | Categoria | USER | RESP.GRUPO | TI | MANAGER | ADMIN | Grupos liberados
- [ ] Páginas com role liberado aparecem com check verde
- [ ] Páginas sem role liberado aparecem com traço cinza
- [ ] Coluna "Grupos liberados" mostra badges azuis com nome dos grupos (ou "—" se vazio)

## Validação cruzada com endpoint /check

Abra outra aba do navegador e cole:
```
http://127.0.0.1:8000/api/permissions/check?page=AGENDA&user_id=15
```

- [ ] Retorna `{"allowed": true, "reason": "Usuário ADMIN"}` (admin sempre passa)

```
http://127.0.0.1:8000/api/permissions/check?page=PERMISSIONS&user_id=23
```

- [ ] Retorna `{"allowed": false, "reason": "Sem permissão por role nem por grupo"}` (user comum)

Configure agora **AGENDA → toggle USER ligado** na aba "Por Role" e teste:
```
http://127.0.0.1:8000/api/permissions/check?page=AGENDA&user_id=23
```

- [ ] Retorna `{"allowed": true, "reason": "Role 'USER' liberado"}`

Volte e desligue o toggle USER. Teste de novo:

- [ ] Volta a retornar `allowed: false`

## Validação por grupo

Configure **AGENDA → grupo "Suporte" ligado** na aba "Por Grupo" e teste com um usuário do grupo Suporte:

```
http://127.0.0.1:8000/api/permissions/check?page=AGENDA&user_id=<id_de_user_do_grupo_suporte>
```

- [ ] Retorna `{"allowed": true, "reason": "Grupo X liberado"}`

## Performance / UX

- [ ] Auto-save é instantâneo (toast aparece em <1s após clique)
- [ ] Trocar de aba é instantâneo (não recarrega da API)
- [ ] Console do navegador (F12) não mostra erros vermelhos
- [ ] Layout responsivo: redimensionar a janela pra tela estreita reorganiza os toggles

---

## Se algo falhar

1. F12 → Console → procurar erro em vermelho
2. F12 → Network → ver se chamadas pra `/api/permissions/...` estão retornando 200
3. Rodar `python -X utf8 server/tests/test_permissions.py` no terminal
4. Conferir se a API está rodando: `curl http://127.0.0.1:8000/api/permissions/catalog`
