"""hook_chat_e2e.py — invocado pelo pre-commit quando chat.py/meetings.py mudam.

Dispara o e2e agente do desktop (2 clientes reais Playwright + WS + msg + hide).

SOFT: nao bloqueia commit quando:
  - API dev local (:8000) esta off
  - Repo cpecontrol-desktop nao esta no sistema
  - Node nao esta instalado

BLOQUEIA quando tudo esta pronto e o e2e falha (algo regrediu).

Exit codes: 0 = ok (ou skipped com warning), 1 = e2e falhou.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import time
import urllib.request

API = os.environ.get("CPE_E2E_API", "http://127.0.0.1:8000")
UA = os.environ.get("CPE_E2E_USER_A", "e2e.alfa")
PA = os.environ.get("CPE_E2E_PASS_A", "e2e12345678")
UB = os.environ.get("CPE_E2E_USER_B", "e2e.bravo")
PB = os.environ.get("CPE_E2E_PASS_B", "e2e12345678")

Y = "\033[33m"; R = "\033[31m"; G = "\033[32m"; X = "\033[0m"

# Windows CMD (cp1252) nao renderiza checkmarks unicode — usa ASCII
OK_MARK = "[OK]"
FAIL_MARK = "[X]"
WARN_MARK = "[!]"


def api_up() -> bool:
    try:
        urllib.request.urlopen(f"{API}/api/pre-cadastro/grupos-publicos", timeout=3)
        return True
    except Exception:
        return False


def ensure_e2e_users():
    """Recria os users de teste se nao existem. Falha silencioso — a
    hook nao vai adicionar dependencia obrigatoria."""
    try:
        HERE = os.path.dirname(os.path.abspath(__file__))
        SERVER = os.path.dirname(HERE)
        sys.path.insert(0, SERVER)
        from database import get_db_or_404  # type: ignore
        from utils import hash_password  # type: ignore
        conn = get_db_or_404(); cur = conn.cursor()
        pwd = hash_password(PA)
        for uname, email, name in [
            (UA, f"{UA}@cpetecnologia.com.br", "E2E Alfa"),
            (UB, f"{UB}@cpetecnologia.com.br", "E2E Bravo"),
        ]:
            cur.execute("SELECT id FROM users WHERE username=%s", (uname,))
            if not cur.fetchone():
                cur.execute("""INSERT INTO users (name,email,username,password_hash,role,is_active,group_id,department_id)
                              VALUES (%s,%s,%s,%s,'USER',1,1,1)""",
                            (name, email, uname, pwd))
        conn.commit(); cur.close(); conn.close()
        return True
    except Exception as e:
        print(f"{Y}⚠{X} nao pude criar users e2e: {e}")
        return False


def main() -> int:
    print(f"{Y}== chat-e2e-agente ==\ninicio: rodando 2 clientes reais...{X}")

    if not api_up():
        print(f"{Y}{WARN_MARK} API dev off em {API} - pulando e2e (nao bloqueia commit).{X}")
        print(f"{Y}  Suba: cd server && .venv\\Scripts\\python.exe app.py{X}")
        return 0

    HERE = os.path.dirname(os.path.abspath(__file__))
    REPO_SISTEMA = os.path.dirname(os.path.dirname(HERE))
    DESKTOP = os.path.join(os.path.dirname(REPO_SISTEMA), "cpecontrol-desktop")
    e2e_script = os.path.join(DESKTOP, "scripts", "e2e-chat-presence.mjs")

    if not os.path.exists(e2e_script):
        print(f"{Y}{WARN_MARK} e2e script nao encontrado ({e2e_script}) - pulando.{X}")
        return 0

    ensure_e2e_users()

    node = "node"
    try:
        rc = subprocess.run([node, "--version"], capture_output=True, timeout=5)
        if rc.returncode != 0:
            raise Exception("node nao respondeu")
    except Exception:
        print(f"{Y}{WARN_MARK} Node nao instalado - pulando.{X}")
        return 0

    print(f"{Y}rodando {e2e_script}...{X}")
    t0 = time.time()
    proc = subprocess.run(
        [node, e2e_script,
         "--api", API,
         "--user-a", UA, "--pass-a", PA,
         "--user-b", UB, "--pass-b", PB],
        cwd=DESKTOP,
        capture_output=True, text=True, timeout=120,
    )
    dt = time.time() - t0
    # Reencoda pra ansi/cp1252 substituindo unicode nao-representavel
    try:
        print(proc.stdout)
    except UnicodeEncodeError:
        print(proc.stdout.encode('ascii', 'replace').decode())
    if proc.returncode == 0:
        print(f"{G}{OK_MARK} e2e passou em {dt:.1f}s{X}")
        return 0
    try:
        print(proc.stderr)
    except UnicodeEncodeError:
        print(proc.stderr.encode('ascii', 'replace').decode())
    print(f"{R}{FAIL_MARK} e2e FALHOU exit={proc.returncode} - bloqueando commit ({dt:.1f}s){X}")
    print(f"{R}  Se for falso positivo, use: git commit --no-verify -m ...{X}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
