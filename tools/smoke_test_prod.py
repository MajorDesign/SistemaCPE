#!/usr/bin/env python3
"""
Smoke test pós-deploy do SistemaCPE.

Bate em endpoints essenciais e falha se alguma rota crítica sumir.
Criado após o incidente 2026-06-17 onde rotas /api/atendimentos/* ficaram
fora do registro silenciosamente (NameError em routes/atendimentos.py
foi engolido por try/except em app.py).

Uso:
    # Contra produção (default)
    python tools/smoke_test_prod.py

    # Contra ambiente local/staging
    python tools/smoke_test_prod.py --base http://127.0.0.1:8000
    python tools/smoke_test_prod.py --base http://127.0.0.1:8001

Exit code 0 = todos endpoints respondem. != 0 = falha.

Roda automaticamente como parte do fluxo de deploy.
"""

import sys
import time
import json
import argparse
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Força stdout em UTF-8 no Windows (cp1252 não suporta acentos do PT-BR)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# User-Agent identificável para Cloudflare não bloquear urllib como bot
UA = "SistemaCPE-SmokeTest/1.0 (+deploy validation)"

# =====================================================================
# Endpoints essenciais — se algum vier 404, o deploy está QUEBRADO.
#
# Cada tupla: (método, path, códigos aceitos, descrição)
# - 200 = rota retorna dados sem auth
# - 401 = rota EXIGE auth, mas existe e responde adequadamente
# - 4xx = validação (rota viva, payload inválido)
#
# IMPORTANTE: aceitar 401 confirma "rota existe e middleware de auth
# está respondendo". 404 significa rota DESREGISTRADA — o bug que queremos
# detectar. NUNCA aceitar 404 numa rota essencial.
# =====================================================================
# PRINCÍPIO: qualquer código que NÃO seja 404 confirma que a rota EXISTE.
# 401 (sem token), 405 (método errado), 422 (validação) — todos significam
# "rota viva, middleware respondendo". 404 é o sinal de router desmontado.
# Por isso usamos LISTA AMPLA de códigos aceitos — preferimos zero falso
# positivo a falhar por causa de mudança de comportamento da API.
ENDPOINTS = [
    # Sanidade básica
    ("GET",  "/",                                          (200, 301, 302),       "redirect raiz"),
    ("GET",  "/SistemaCPE/web/login.html",                 (200,),                "página de login"),

    # Autenticação
    ("POST", "/api/auth/login",                            (400, 422),            "rota /auth/login viva (payload vazio → validation)"),

    # Dados públicos/leves (sem auth)
    ("GET",  "/api/unidades/",                             (200,),                "lista unidades CPE"),
    ("GET",  "/api/permissions/catalog",                   (200,),                "catálogo de permissões"),

    # Users (admin existe)
    ("GET",  "/api/users/15",                              (200,),                "user admin (id=15)"),
    ("GET",  "/api/groups",                                (200, 307),            "lista grupos"),

    # ROTAS QUE FICARAM FORA DO AR EM 17/06 (regressão protegida)
    # 401 = rota existe e exige auth (PRINCIPAL canary que queremos)
    ("GET",  "/api/atendimentos/agendas",                  (200, 401, 422),       "[CRÍTICO] equipe-suporte agendas"),
    ("GET",  "/api/atendimentos/dashboard",                (200, 401, 422),       "[CRÍTICO] equipe-suporte dashboard"),
    ("GET",  "/api/atendimentos/clientes",                 (200, 401, 422),       "[CRÍTICO] equipe-suporte clientes"),

    # Outros módulos (exigem auth, mas devem existir)
    ("GET",  "/api/passwords/groups/list",                 (200, 401),            "cofre de senhas — grupos"),
    ("GET",  "/api/chat/me",                               (401,),                "chat — me (auth obrigatório)"),
    ("GET",  "/api/dashboard/me",                          (200, 401, 422),       "dashboard /me"),
    ("GET",  "/api/notificacoes/",                         (200, 401, 405, 422),  "notificações (rota viva)"),
    ("GET",  "/api/agenda/status?usuario_id=15",           (200, 401, 500),       "agenda Carbonio status"),
]

# Snapshot: nº mínimo de rotas no openapi. Útil rodando contra LOCAL onde
# /openapi.json é acessível. Em PROD o Caddy não expõe (security) — usar
# --skip-openapi-count nesse caso. Baseline atual: ~330+ rotas.
MIN_ROUTES = 250


def check_endpoint(base: str, method: str, path: str, expected: tuple, timeout: int = 10):
    """Bate num endpoint e devolve (ok, mensagem, ms)."""
    url = base + path
    req = Request(url, method=method)
    req.add_header("User-Agent", UA)
    req.add_header("Accept", "application/json, text/html, */*")
    body = None
    if method == "POST":
        req.add_header("Content-Type", "application/json")
        body = b"{}"

    t0 = time.time()
    try:
        with urlopen(req, data=body, timeout=timeout) as r:
            status = r.status
    except HTTPError as e:
        status = e.code
    except URLError as e:
        dt = (time.time() - t0) * 1000
        return False, f"NETWORK ERROR: {e.reason}", dt
    except Exception as e:
        dt = (time.time() - t0) * 1000
        return False, f"EXCEPTION: {e}", dt

    dt = (time.time() - t0) * 1000
    ok = status in expected
    return ok, f"HTTP {status} (esperado {expected})", dt


def check_route_count(base: str, min_routes: int):
    """Lê /openapi.json e conta as rotas. Se < min, alerta."""
    try:
        req = Request(f"{base}/openapi.json")
        req.add_header("User-Agent", UA)
        with urlopen(req, timeout=15) as r:
            schema = json.load(r)
            n = len(schema.get("paths", {}))
            ok = n >= min_routes
            return ok, n
    except Exception as e:
        return False, f"erro: {e}"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default="https://cpecontrol.cpetecnologia.com.br",
                        help="URL base (default: produção)")
    parser.add_argument("--min-routes", type=int, default=MIN_ROUTES,
                        help=f"Mínimo de rotas no openapi.json (default: {MIN_ROUTES})")
    parser.add_argument("--skip-openapi-count", action="store_true",
                        help="Pula contagem de rotas (use em prod onde /openapi.json é bloqueado)")
    parser.add_argument("--timeout", type=int, default=10,
                        help="Timeout por request em segundos (default: 10)")
    args = parser.parse_args()

    base = args.base.rstrip("/")
    print()
    print(f"{'=' * 78}")
    print(f"  Smoke test SistemaCPE — {base}")
    print(f"{'=' * 78}")
    print()

    failures = []
    total_ms = 0

    for method, path, expected, comment in ENDPOINTS:
        ok, msg, dt = check_endpoint(base, method, path, expected, args.timeout)
        total_ms += dt
        sym = "[OK]  " if ok else "[FAIL]"
        # path truncado pra ficar dentro do terminal
        path_disp = path if len(path) <= 50 else path[:47] + "..."
        print(f"  {sym}  {method:4s}  {path_disp:50s}  {msg:32s}  {dt:5.0f}ms  | {comment}")
        if not ok:
            failures.append((method, path, msg, comment))

    if not args.skip_openapi_count:
        print()
        print(f"  -> Contagem de rotas no openapi.json:")
        ok_count, n = check_route_count(base, args.min_routes)
        if ok_count:
            print(f"     [OK]    {n} rotas (>= {args.min_routes} esperado)")
        else:
            print(f"     [FAIL]  apenas {n} rotas (< {args.min_routes} esperado - algum router nao montou)")
            failures.append(("openapi", "count", str(n), f"esperado >= {args.min_routes}"))

    print()
    print(f"  Total: {len(ENDPOINTS)} endpoints testados em {total_ms:.0f}ms")
    print()

    if failures:
        print(f"  ##### FALHOU ##### - {len(failures)} problema(s):")
        for m, p, msg, c in failures:
            print(f"     {m} {p}: {msg}  ({c})")
        print()
        sys.exit(1)
    else:
        print(f"  ##### OK ##### - deploy validado.")
        print()
        sys.exit(0)


if __name__ == "__main__":
    main()
