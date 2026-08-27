"""
Segurança: sessões, tokens, autenticação
"""

import hmac
import time
import secrets
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from passlib.context import CryptContext
from config import APP_SECRET, COOKIE_NAME, SESSION_MAX_AGE_SECONDS
from database import engine
from sqlalchemy import text

# =========================================
# CRYPTO
# =========================================
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

# =========================================
# SESSÃO (HMAC)
# =========================================

def _sign(payload: str) -> str:
    """Assina um payload com HMAC-SHA256"""
    return hmac.new(
        APP_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        "sha256"
    ).hexdigest()


def make_session_token(user_id: int) -> str:
    """
    Cria um token de sessão assinado
    Formato: userId.timestamp.random.signature
    """
    ts = str(int(time.time()))
    rnd = secrets.token_hex(16)
    payload = f"{user_id}.{ts}.{rnd}"
    sig = _sign(payload)
    token = f"{payload}.{sig}"
    # Não logar o token (mesmo truncado): expõe estrutura e prefixo do user_id.
    return token


# 2026-08-27: IMPERSONATE (modo suporte) — token especial usado quando um
# ADMIN entra "como" outro usuario pra diagnostico. Formato:
#   IMP-<realId>-<targetId>.<ts>.<rnd>.<sig>
# Parse continua funcionando pra tokens normais (compat). TTL 60min.
IMPERSONATE_TTL_SECONDS = 60 * 60
_IMP_PREFIX = "IMP-"


def make_impersonation_token(real_user_id: int, target_user_id: int) -> str:
    """Gera token de impersonate (SO chamado por endpoint que ja validou
    que real_user_id e ADMIN)."""
    ts  = str(int(time.time()))
    rnd = secrets.token_hex(16)
    head = f"{_IMP_PREFIX}{real_user_id}-{target_user_id}"
    payload = f"{head}.{ts}.{rnd}"
    sig = _sign(payload)
    return f"{payload}.{sig}"


def parse_session_token(token: str) -> Optional[int]:
    """
    Parse de token de sessao. Retorna o user_id "efetivo":
      - Token normal: retorna o user_id
      - Token de impersonate: retorna o TARGET (impersonated) user_id
        (o real_user_id fica dispoinvel via parse_session_token_full).
    Retorna None se invalido/expirado.
    """
    d = parse_session_token_full(token)
    return d["user_id"] if d else None


def parse_session_token_full(token: str) -> Optional[Dict[str, Any]]:
    """Parse completo. Retorna dict:
      {user_id: int, impersonated_by: Optional[int]}
    ou None se invalido/expirado."""
    try:
        parts = token.split(".")
        if len(parts) != 4:
            return None

        head, ts, rnd, sig = parts
        payload = f"{head}.{ts}.{rnd}"

        expected_sig = _sign(payload)
        if not hmac.compare_digest(expected_sig, sig):
            return None

        ts_i = int(ts)
        age = int(time.time()) - ts_i

        # Impersonate ou sessao normal?
        if head.startswith(_IMP_PREFIX):
            # IMP-<real>-<target>
            try:
                _, ids = head.split("-", 1)  # <real>-<target>
                real_id_str, target_id_str = ids.split("-", 1)
                real_id = int(real_id_str)
                target_id = int(target_id_str)
            except (ValueError, IndexError):
                return None
            if age > IMPERSONATE_TTL_SECONDS:
                return None
            return {"user_id": target_id, "impersonated_by": real_id}

        # sessao normal
        if age > SESSION_MAX_AGE_SECONDS:
            return None
        return {"user_id": int(head), "impersonated_by": None}

    except Exception:
        return None


import os as _os
# secure=True quando rodando atrás de HTTPS. Controlado por env: COOKIE_SECURE=1
_COOKIE_SECURE = _os.getenv("COOKIE_SECURE", "0").lower() in ("1", "true", "yes")

def set_session_cookie(response, token: str) -> None:
    """Define o cookie de sessão na resposta"""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
        path="/",
    )


def clear_session_cookie(response) -> None:
    """Remove o cookie de sessão"""
    response.delete_cookie(COOKIE_NAME, path="/")


# =========================================
# DEV GUARD
# =========================================

def require_dev_key(x_dev_key: Optional[str]) -> None:
    """
    Protege endpoints /api/dev/*
    Exige header: X-DEV-KEY
    """
    from config import DEV_API_KEY
    
    if not DEV_API_KEY:
        print("[DEV] DESABILITADO: DEV endpoints desabilitados")
        raise HTTPException(status_code=403, detail="DEV endpoints desabilitados")

    if not x_dev_key or not hmac.compare_digest(x_dev_key, DEV_API_KEY):
        print("[DEV] FALHA: DEV key invalida")
        raise HTTPException(status_code=403, detail="DEV key inválida")

    print("[DEV] OK: DEV key valida")


# =========================================
# DATABASE HELPERS
# =========================================

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Busca um usuário pelo email"""
    try:
        with engine.connect() as conn:
            q = text("""
                SELECT id, name, email, password_hash, role, sector, unit, is_active, 
                       department_id, group_id
                FROM users
                WHERE email = :email
                LIMIT 1
            """)
            result = conn.execute(q, {"email": email}).mappings().first()
            
            if result:
                print(f"[DB] OK usuario encontrado: {email}")
                return dict(result)
            else:
                print(f"[DB] NAO encontrado: {email}")
                return None

    except Exception as e:
        print(f"[DB] ERRO ao buscar usuario: {e}")
        return None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Busca um usuário pelo ID"""
    try:
        with engine.connect() as conn:
            q = text("""
                SELECT id, name, email, role, sector, unit, is_active,
                       department_id, group_id
                FROM users
                WHERE id = :id
                LIMIT 1
            """)
            result = conn.execute(q, {"id": user_id}).mappings().first()

            if result:
                print(f"[DB] OK usuario ID={user_id}, Role={result.get('role')}")
                return dict(result)
            else:
                print(f"[DB] NAO encontrado: ID={user_id}")
                return None

    except Exception as e:
        print(f"[DB] ERRO ao buscar usuario por ID: {e}")
        return None


# =========================================
# AUTHENTICATION DEPENDENCY
# =========================================

def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Extrai o usuário autenticado da sessão.
    Aceita o token via (em ordem):
      1. Cookie de sessão
      2. Header X-Auth-Token
      3. Header Authorization: Bearer <token>
    """
    print("[AUTH/DEPENDENCY] Verificando autenticacao...")

    token = request.cookies.get(COOKIE_NAME)
    if not token:
        token = request.headers.get("X-Auth-Token") or request.headers.get("x-auth-token")
    if not token:
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization") or ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

    if not token:
        print("[AUTH/DEPENDENCY] FALHA: token nao encontrado")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nao autenticado. Por favor, faca login."
        )

    parsed = parse_session_token_full(token)
    if not parsed:
        print("[AUTH/DEPENDENCY] FALHA: token invalido")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao invalida ou expirada."
        )
    user_id       = parsed["user_id"]
    impersonator  = parsed.get("impersonated_by")

    user = get_user_by_id(user_id)
    if not user or user.get("is_active") != 1:
        print("[AUTH/DEPENDENCY] FALHA: usuario invalido ou inativo")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao invalida."
        )

    # Se e impersonate: valida que o real user ainda existe, esta ativo, e
    # continua sendo ADMIN. Se algum criterio quebrou (real user foi
    # despromovido/desativado), invalida a sessao.
    imp_user = None
    if impersonator is not None:
        imp_user = get_user_by_id(impersonator)
        if not imp_user or imp_user.get("is_active") != 1 \
           or (imp_user.get("role") or "").upper() != "ADMIN":
            print(f"[AUTH/DEPENDENCY] FALHA: impersonator {impersonator} nao e mais ADMIN valido")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessao de suporte invalida."
            )
        print(f"[AUTH/DEPENDENCY] IMPERSONATE: {imp_user['name']} vendo como {user['name']}")
    else:
        print(f"[AUTH/DEPENDENCY] OK usuario autenticado: {user['name']} (Role: {user.get('role')})")

    # Multi-grupo (Fase 2 PLANO_MULTIGRUPO.md):
    # Carrega TODOS os grupos do user com o papel em cada um.
    # `group_id` continua sendo o primario (retrocompat).
    groups = _load_user_groups(user["id"])

    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "department_id": user.get("department_id"),
        "group_id": user.get("group_id"),
        "groups": groups,                                              # list[dict]
        "group_ids": [g["group_id"] for g in groups],                  # list[int]
        "responsavel_group_ids": [g["group_id"] for g in groups
                                  if g["role_in_grp"] == "RESPONSAVEL_GRUPO"],
        # 2026-08-27 modo suporte: quando setado, request e read-only
        # (middleware bloqueia POST/PUT/PATCH/DELETE fora da whitelist).
        "impersonated_by":      impersonator,
        "impersonated_by_name": imp_user["name"] if imp_user else None,
    }


def _load_user_groups(user_id: int) -> list:
    """
    Retorna a lista de grupos do usuario com role em cada um.
    Fallback: se user_groups estiver vazio pra esse user (edge case
    de migracao incompleta), sintetiza a partir de users.group_id.
    """
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT ug.group_id, ug.role_in_grp,
                       (ug.is_primary = 1) AS is_primary,
                       g.name AS group_name
                  FROM user_groups ug
                  JOIN cpe_grupo g ON g.id = ug.group_id
                 WHERE ug.user_id = :uid
                 ORDER BY ug.is_primary DESC, g.name ASC
            """), {"uid": user_id}).mappings().all()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[AUTH/GROUPS] erro ao carregar user_groups({user_id}): {e}")
        return []