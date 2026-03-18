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
    
    print(f"[SESSION] Token criado para user_id={user_id}")
    print(f"[SESSION] Token: {token[:50]}...")
    
    return token


def parse_session_token(token: str) -> Optional[int]:
    """
    Parse de um token de sessão
    Retorna user_id se válido, None caso contrário
    """
    try:
        parts = token.split(".")
        if len(parts) != 4:
            print(f"[SESSION] ✗ Token inválido (partes: {len(parts)})")
            return None

        user_id, ts, rnd, sig = parts
        payload = f"{user_id}.{ts}.{rnd}"

        # Verifica a assinatura
        expected_sig = _sign(payload)
        if not hmac.compare_digest(expected_sig, sig):
            print(f"[SESSION] ✗ Assinatura inválida")
            return None

        # Verifica a expiração
        ts_i = int(ts)
        age = int(time.time()) - ts_i
        
        if age > SESSION_MAX_AGE_SECONDS:
            print(f"[SESSION] ✗ Token expirado (idade: {age}s, máx: {SESSION_MAX_AGE_SECONDS}s)")
            return None

        user_id_int = int(user_id)
        print(f"[SESSION] ✓ Token válido para user_id={user_id_int} (idade: {age}s)")
        
        return user_id_int
        
    except Exception as e:
        print(f"[SESSION] ✗ Erro ao fazer parse: {e}")
        return None


def set_session_cookie(response, token: str) -> None:
    """Define o cookie de sessão na resposta"""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
        path="/",
    )
    print(f"[SESSION] ✓ Cookie 'cpe_session' definido no response")


def clear_session_cookie(response) -> None:
    """Remove o cookie de sessão"""
    response.delete_cookie(COOKIE_NAME, path="/")
    print(f"[SESSION] ✓ Cookie 'cpe_session' removido")


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
        print("[DEV] ✗ DEV endpoints desabilitados")
        raise HTTPException(status_code=403, detail="DEV endpoints desabilitados")

    if not x_dev_key or not hmac.compare_digest(x_dev_key, DEV_API_KEY):
        print(f"[DEV] ✗ DEV key inválida")
        raise HTTPException(status_code=403, detail="DEV key inválida")

    print("[DEV] ✓ DEV key válida")


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
                print(f"[DB] ✓ Usuário encontrado: {email}")
                return dict(result)
            else:
                print(f"[DB] ✗ Usuário não encontrado: {email}")
                return None
                
    except Exception as e:
        print(f"[DB] ✗ Erro ao buscar usuário: {e}")
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
                print(f"[DB] ✓ Usuário encontrado: ID={user_id}, Role={result.get('role')}")
                return dict(result)
            else:
                print(f"[DB] ✗ Usuário não encontrado: ID={user_id}")
                return None
                
    except Exception as e:
        print(f"[DB] ✗ Erro ao buscar usuário por ID: {e}")
        return None


# =========================================
# AUTHENTICATION DEPENDENCY
# =========================================

def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Extrai o usuário autenticado da sessão
    Usado como Depends() em endpoints protegidos
    """
    print("[AUTH/DEPENDENCY] Verificando autenticação...")
    
    token = request.cookies.get(COOKIE_NAME)
    
    if not token:
        print("[AUTH/DEPENDENCY] ✗ Token não encontrado")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado. Por favor, faça login."
        )

    user_id = parse_session_token(token)
    if not user_id:
        print("[AUTH/DEPENDENCY] ✗ Token inválido")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida ou expirada."
        )

    user = get_user_by_id(user_id)
    if not user or user.get("is_active") != 1:
        print("[AUTH/DEPENDENCY] ✗ Usuário inválido ou inativo")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida."
        )

    print(f"[AUTH/DEPENDENCY] ✓ Usuário autenticado: {user['name']} (Role: {user.get('role')})")

    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "department_id": user.get("department_id"),
        "group_id": user.get("group_id"),
    }