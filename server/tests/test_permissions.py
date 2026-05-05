"""
Smoke-test do sistema de permissões.

Roda contra a API real em http://127.0.0.1:8000.
Use durante o desenvolvimento da refatoração de permissões.

Como rodar:
    python server/tests/test_permissions.py

O script é "tudo ou nada": se algum teste falha, sai com exit code 1.
Cobertura cresce conforme as fases avançam (ver docs/PLANO_PERMISSOES.md).
"""

from __future__ import annotations

import io
import sys
import json
import time
from typing import Any

# Garante UTF-8 mesmo no console cp1252 do Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import requests
except ImportError:
    print("ERRO: pacote 'requests' nao instalado. Rode: pip install requests")
    sys.exit(1)


API = "http://127.0.0.1:8000"
TIMEOUT = 5

_resultados: list[tuple[str, bool, str]] = []


def _ok(label: str, detalhe: str = "") -> None:
    _resultados.append((label, True, detalhe))
    print(f"  [OK]   {label}" + (f"   ({detalhe})" if detalhe else ""))


def _fail(label: str, motivo: str) -> None:
    _resultados.append((label, False, motivo))
    print(f"  [FAIL] {label}   ->  {motivo}")


def _secao(titulo: str) -> None:
    print(f"\n--- {titulo} ---")


def _get(path: str, **kw) -> tuple[int, Any]:
    r = requests.get(API + path, timeout=TIMEOUT, **kw)
    try:    body = r.json()
    except: body = r.text
    return r.status_code, body


def _post(path: str, json_body: dict | None = None, **kw) -> tuple[int, Any]:
    r = requests.post(API + path, json=json_body, timeout=TIMEOUT, **kw)
    try:    body = r.json()
    except: body = r.text
    return r.status_code, body


def _put(path: str, json_body: dict | None = None) -> tuple[int, Any]:
    r = requests.put(API + path, json=json_body, timeout=TIMEOUT)
    try:    body = r.json()
    except: body = r.text
    return r.status_code, body


# =====================================================================
# TESTES — adicionar conforme as fases avançam
# Cada função recebe o catálogo do GET /catalog e usa pra validar
# =====================================================================

def teste_api_no_ar() -> bool:
    """Garante que a API está respondendo antes de rodar o resto."""
    _secao("API no ar")
    try:
        code, body = _get("/api/groups/")
        if code == 200:
            _ok("API responde em :8000", f"groups={len(body) if isinstance(body, list) else '?'}")
            return True
        _fail("API responde em :8000", f"HTTP {code}")
        return False
    except Exception as err:
        _fail("API responde em :8000", str(err))
        return False


# =====================================================================
# FASE 1 — endpoints de permissões refatorados
# =====================================================================

def teste_fase1_catalog() -> None:
    """GET /api/permissions/catalog deve retornar páginas + roles + groups."""
    _secao("Fase 1 — GET /api/permissions/catalog")
    code, body = _get("/api/permissions/catalog")

    if code != 200:
        _fail("GET /catalog responde 200", f"HTTP {code}: {body}")
        return
    _ok("GET /catalog responde 200")

    if not isinstance(body, dict) or "pages" not in body:
        _fail("Resposta tem chave 'pages'", str(body)[:120])
        return
    _ok("Resposta tem chave 'pages'", f"len={len(body['pages'])}")

    # Páginas obrigatórias (faltavam no catálogo antigo)
    keys = {p.get("page_key") for p in body["pages"]}
    obrig = {"AGENDA", "FLEET", "RECEPCAO", "CONTRATOS", "TICKETS", "USERS", "GROUPS", "PERMISSIONS"}
    falta = obrig - keys
    if falta:
        _fail("Catálogo contém páginas críticas", f"faltam: {falta}")
    else:
        _ok("Catálogo contém páginas críticas (8/8)")

    # Cada page tem roles[] e group_ids[]
    sem_roles = [p["page_key"] for p in body["pages"] if "roles" not in p]
    if sem_roles:
        _fail("Cada página tem 'roles'", f"sem roles: {sem_roles[:3]}")
    else:
        _ok("Cada página tem 'roles' (lista)")

    sem_groups = [p["page_key"] for p in body["pages"] if "group_ids" not in p]
    if sem_groups:
        _fail("Cada página tem 'group_ids'", f"sem group_ids: {sem_groups[:3]}")
    else:
        _ok("Cada página tem 'group_ids' (lista)")


def teste_fase1_check_admin() -> None:
    """GET /api/permissions/check para usuário ADMIN sempre libera."""
    _secao("Fase 1 — GET /check (admin sempre acessa)")
    # admin@cpe.com.br tem id=15
    code, body = _get("/api/permissions/check", params={"page": "PERMISSIONS", "user_id": 15})
    if code != 200:
        _fail("Endpoint responde 200", f"HTTP {code}: {body}")
        return
    if body.get("allowed") is True:
        _ok("Admin tem acesso a PERMISSIONS", body.get("reason", ""))
    else:
        _fail("Admin tem acesso a PERMISSIONS", str(body))


def teste_fase1_update_page() -> None:
    """PUT /api/permissions/catalog/{key} substitui roles e groups da página."""
    _secao("Fase 1 — PUT /catalog/{key} (atualizar)")
    code_atual, atual = _get("/api/permissions/catalog")
    if code_atual != 200:
        _fail("Lê catálogo antes de atualizar", "catalog falhou")
        return
    pagina_orig = next((p for p in atual["pages"] if p["page_key"] == "AGENDA"), None)
    if not pagina_orig:
        _fail("Página AGENDA existe", "não encontrada")
        return

    code, body = _put("/api/permissions/catalog/AGENDA",
                      {"roles": ["ADMIN", "TI"], "group_ids": []})
    if code not in (200, 204):
        _fail("PUT /catalog/AGENDA responde 200/204", f"HTTP {code}: {body}")
        return
    _ok("PUT /catalog/AGENDA aceita atualização")

    # Confere que persistiu
    _, novo = _get("/api/permissions/catalog")
    pagina_nova = next((p for p in novo["pages"] if p["page_key"] == "AGENDA"), {})
    if set(pagina_nova.get("roles", [])) == {"ADMIN", "TI"}:
        _ok("Roles persistidos no banco")
    else:
        _fail("Roles persistidos no banco", f"got: {pagina_nova.get('roles')}")

    # Restaura estado original
    _put("/api/permissions/catalog/AGENDA",
         {"roles": pagina_orig.get("roles", []),
          "group_ids": pagina_orig.get("group_ids", [])})


def teste_fase1_check_user_normal() -> None:
    """GET /check pra usuário comum (USER) deve respeitar role."""
    _secao("Fase 1 — GET /check (usuário comum)")
    # camila (id=23, role=USER) — verifica acesso a TICKETS (USER tem) e PERMISSIONS (USER não tem)
    code, body = _get("/api/permissions/check", params={"page": "TICKETS", "user_id": 23})
    if code == 200 and body.get("allowed") is True:
        _ok("USER tem acesso a TICKETS", body.get("reason", ""))
    else:
        _fail("USER tem acesso a TICKETS", str(body))

    code, body = _get("/api/permissions/check", params={"page": "PERMISSIONS", "user_id": 23})
    if code == 200 and body.get("allowed") is False:
        _ok("USER NÃO tem acesso a PERMISSIONS", body.get("reason", ""))
    else:
        _fail("USER NÃO tem acesso a PERMISSIONS", str(body))


def teste_fase1_menu() -> None:
    """GET /me/menu retorna apenas páginas que o user pode ver."""
    _secao("Fase 1 — GET /me/menu")
    code, body = _get("/api/permissions/me/menu", params={"user_id": 15})  # admin
    if code != 200:
        _fail("GET /me/menu responde 200", f"HTTP {code}")
        return
    if not isinstance(body, dict) or "pages" not in body:
        _fail("Resposta tem 'pages'", str(body)[:120])
        return
    keys = {p["page_key"] for p in body["pages"]}
    if len(keys) >= 20 and "PERMISSIONS" in keys:
        _ok("Admin vê todas as páginas no menu", f"{len(keys)} páginas")
    else:
        _fail("Admin vê todas as páginas no menu", f"got {len(keys)} pages, missing? {('PERMISSIONS' in keys)}")


def teste_fase4_endpoint_legado_removido() -> None:
    """Endpoint legado GET /api/permissions/pages NÃO deve mais existir."""
    _secao("Fase 4 — Endpoint legado removido")
    code, body = _get("/api/permissions/pages")
    if code == 404:
        _ok("GET /pages retorna 404 (endpoint removido)")
    elif code == 405:
        _ok("GET /pages retorna 405 (método não permitido)")
    else:
        _fail("GET /pages deve estar removido", f"ainda retorna HTTP {code}")


def teste_fase1_legacy_intacta() -> None:
    """A tabela _legacy_page_permissions DEVE existir (rollback)."""
    # Esse teste roda direto no banco — pulamos quando smoke é "API only"
    pass


# =====================================================================
# RUNNER
# =====================================================================

def main() -> int:
    print(f"\n=== Smoke-test de permissoes — {API} ===\n")

    if not teste_api_no_ar():
        print("\nAPI nao esta rodando. Inicie e tente novamente.")
        return 1

    # Roda os testes da fase 1
    try:
        teste_fase1_catalog()
        teste_fase1_check_admin()
        teste_fase1_check_user_normal()
        teste_fase1_update_page()
        teste_fase1_menu()
        teste_fase4_endpoint_legado_removido()
    except Exception as err:
        _fail("Exceção inesperada", repr(err))

    # Resumo
    total = len(_resultados)
    ok    = sum(1 for _, p, _ in _resultados if p)
    fail  = total - ok

    print("\n" + "=" * 60)
    print(f"  Total: {total}   OK: {ok}   Falhas: {fail}")
    print("=" * 60 + "\n")

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
