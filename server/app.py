# =========================================
# app.py — CPE Control API (Refatorado / Limpo)
# =========================================

from __future__ import annotations

import os
import hmac
import time
import secrets
from pathlib import Path
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response, Request, Header, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, ConfigDict
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext


# =========================================
# ENV (carrega .env do MESMO diretório)
# =========================================
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)


# =========================================
# Configuração
# =========================================
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DB", "cpe_control")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

APP_SECRET = os.getenv("APP_SECRET", "change_me")

# CORS: aceita lista separada por vírgula
CORS_ORIGINS_RAW = os.getenv("CORS_ORIGINS", "http://localhost").strip()
CORS_ORIGINS: List[str] = [o.strip() for o in CORS_ORIGINS_RAW.split(",") if o.strip()]

# DEV guard
DEV_API_KEY = os.getenv("DEV_API_KEY", "").strip()

# Sessão
COOKIE_NAME = "cpe_session"
SESSION_MAX_AGE_SECONDS = 7 * 24 * 3600  # 7 dias

DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
)

print("=" * 60)
print("CPE Control API - Iniciando")
print("=" * 60)
print(f"Banco de dados: {MYSQL_DB}")
print(f"Host: {MYSQL_HOST}:{MYSQL_PORT}")
print(f"DEV_API_KEY carregada? {'SIM' if DEV_API_KEY else 'NÃO'}")
print(f"CORS_ORIGINS: {CORS_ORIGINS}")
print(f"SESSION_MAX_AGE: {SESSION_MAX_AGE_SECONDS} segundos ({SESSION_MAX_AGE_SECONDS // 3600} horas)")
print("=" * 60)


# =========================================
# DB / Crypto
# =========================================
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)


# =========================================
# App + CORS
# =========================================
app = FastAPI(title="CPE Control API", version="0.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Set-Cookie", "Content-Type"],
    max_age=600,
)

print(f"✓ CORS habilitado para: {CORS_ORIGINS}")


# =========================================
# Sessão (cookie assinado com HMAC)
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


def set_session_cookie(response: Response, token: str) -> None:
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
    print(f"[SESSION] Cookie 'cpe_session' definido no response")


def clear_session_cookie(response: Response) -> None:
    """Remove o cookie de sessão"""
    response.delete_cookie(COOKIE_NAME, path="/")
    print(f"[SESSION] Cookie 'cpe_session' removido")


# =========================================
# DEV guard (X-DEV-KEY)
# =========================================
def require_dev_key(x_dev_key: Optional[str]) -> None:
    """
    Protege endpoints /api/dev/*
    Exige header: X-DEV-KEY
    """
    if not DEV_API_KEY:
        print("[DEV] ✗ DEV endpoints desabilitados")
        raise HTTPException(status_code=403, detail="DEV endpoints desabilitados")

    if not x_dev_key or not hmac.compare_digest(x_dev_key, DEV_API_KEY):
        print(f"[DEV] ✗ DEV key inválida (fornecida: {x_dev_key[:10] if x_dev_key else 'None'}...)")
        raise HTTPException(status_code=403, detail="DEV key inválida")

    print("[DEV] ✓ DEV key válida")


# =========================================
# Pydantic models
# =========================================
class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    ok: bool
    user: Dict[str, Any]


class MeResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    sector: Optional[str] = None
    unit: Optional[str] = None


class CreateUserRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    email: EmailStr
    username: Optional[str] = None
    password: str
    role: str = "USER"
    sector: Optional[str] = None
    unit: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: EmailStr
    new_password: str


# =========================================
# Helpers (DB)
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
            else:
                print(f"[DB] ✗ Usuário não encontrado: {email}")
            
            return dict(result) if result else None
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
                print(f"[DB] ✓ Usuário encontrado: ID={user_id}")
            else:
                print(f"[DB] ✗ Usuário não encontrado: ID={user_id}")
            
            return dict(result) if result else None
    except Exception as e:
        print(f"[DB] ✗ Erro ao buscar usuário por ID: {e}")
        return None


def ensure_bcrypt_password_ok(raw_password: str) -> None:
    """Valida comprimento da senha para bcrypt (máx 72 bytes)"""
    if len(raw_password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha muito longa. O máximo para bcrypt é 72 bytes."
        )


# =========================================
# Dependency: get_current_user
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

    print(f"[AUTH/DEPENDENCY] ✓ Usuário autenticado: {user['name']}")

    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "department_id": user.get("department_id"),
        "group_id": user.get("group_id"),
    }


# =========================================
# Routes — Health Check
# =========================================
@app.get("/api/health")
def health_check():
    """Health check do servidor"""
    return {"ok": True, "message": "CPE Control API está online"}


# =========================================
# Routes — Auth
# =========================================
@app.post("/api/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response):
    """
    Autentica o usuário e cria uma sessão
    """
    print("\n" + "=" * 60)
    print("[AUTH/LOGIN] Tentativa de login")
    print("=" * 60)
    
    email = payload.email.lower().strip()
    password = payload.password

    print(f"[AUTH/LOGIN] Email: {email}")

    # Busca o usuário
    user = get_user_by_email(email)
    if not user:
        print("[AUTH/LOGIN] ✗ Usuário não encontrado")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos."
        )

    # Verifica se está ativo
    if user.get("is_active") != 1:
        print("[AUTH/LOGIN] ✗ Usuário inativo")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos."
        )

    # Verifica o hash da senha
    db_hash = (user.get("password_hash") or "").strip()
    if len(db_hash) < 20:
        print(f"[AUTH/LOGIN] ✗ Hash inválido (comprimento: {len(db_hash)})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos."
        )

    # Verifica a senha
    try:
        if not pwd_context.verify(password, db_hash):
            print("[AUTH/LOGIN] ✗ Senha incorreta")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário ou senha inválidos."
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH/LOGIN] ✗ Erro ao verificar hash: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos."
        )

    # Cria a sessão
    token = make_session_token(int(user["id"]))
    set_session_cookie(response, token)

    print(f"[AUTH/LOGIN] ✓ Login bem-sucedido para: {email}")
    print(f"[AUTH/LOGIN] User ID: {user['id']}")
    print("=" * 60 + "\n")

    return {
        "ok": True,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
        }
    }


@app.post("/api/auth/logout")
def logout(response: Response):
    """
    Faz logout do usuário
    """
    print("\n[AUTH/LOGOUT] Processando logout...")
    clear_session_cookie(response)
    print("[AUTH/LOGOUT] ✓ Logout concluído\n")
    return {"ok": True, "message": "Logout realizado com sucesso"}


@app.get("/api/auth/me", response_model=MeResponse)
def me(request: Request):
    """
    Retorna os dados do usuário autenticado
    """
    print("\n[AUTH/ME] Verificando autenticação...")
    
    # Busca o cookie de sessão
    token = request.cookies.get(COOKIE_NAME)
    print(f"[AUTH/ME] Cookie 'cpe_session' encontrado? {bool(token)}")
    
    if not token:
        print("[AUTH/ME] ✗ Cookie de sessão não encontrado")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado. Por favor, faça login."
        )

    # Parse do token
    user_id = parse_session_token(token)
    if not user_id:
        print("[AUTH/ME] ✗ Token de sessão inválido ou expirado")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida ou expirada."
        )

    # Busca o usuário no banco
    user = get_user_by_id(user_id)
    if not user or user.get("is_active") != 1:
        print(f"[AUTH/ME] ✗ Usuário inválido ou inativo (ID: {user_id})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida."
        )

    print(f"[AUTH/ME] ✓ Usuário autenticado: {user['name']} ({user['email']})\n")

    return MeResponse(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        sector=user.get("sector"),
        unit=user.get("unit"),
    )


# =========================================
# Routes — DEV (MVP) (REMOVER/PROTEGER em produção)
# =========================================
@app.post("/api/dev/create-user")
def dev_create_user(
    payload: CreateUserRequest,
    x_dev_key: Optional[str] = Header(default=None, alias="X-DEV-KEY"),
):
    """Cria um novo usuário (DEV ONLY)"""
    print("\n[DEV/CREATE-USER] Criando novo usuário...")
    
    require_dev_key(x_dev_key)

    email = payload.email.lower().strip()
    ensure_bcrypt_password_ok(payload.password)
    password_hash = pwd_context.hash(payload.password)

    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO users (name, email, password_hash, role, sector, unit, is_active)
                VALUES (:name, :email, :password_hash, :role, :sector, :unit, 1)
            """), {
                "name": payload.name,
                "email": email,
                "password_hash": password_hash,
                "role": payload.role,
                "sector": payload.sector,
                "unit": payload.unit,
            })
        
        print(f"[DEV/CREATE-USER] ✓ Usuário criado: {email}\n")
        return {"ok": True}
        
    except IntegrityError:
        print(f"[DEV/CREATE-USER] ✗ Email já cadastrado: {email}\n")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado."
        )
    except Exception as e:
        print(f"[DEV/CREATE-USER] ✗ Erro: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar usuário: {str(e)}"
        )


@app.post("/api/dev/reset-password")
def dev_reset_password(
    payload: ResetPasswordRequest,
    x_dev_key: Optional[str] = Header(default=None, alias="X-DEV-KEY"),
):
    """Reseta a senha de um usuário (DEV ONLY)"""
    print("\n[DEV/RESET-PASSWORD] Resetando senha...")
    
    require_dev_key(x_dev_key)

    email = payload.email.lower().strip()
    ensure_bcrypt_password_ok(payload.new_password)
    password_hash = pwd_context.hash(payload.new_password)

    try:
        with engine.begin() as conn:
            res = conn.execute(text("""
                UPDATE users
                SET password_hash = :password_hash
                WHERE email = :email
                LIMIT 1
            """), {
                "password_hash": password_hash,
                "email": email,
            })

            if res.rowcount == 0:
                print(f"[DEV/RESET-PASSWORD] ✗ Usuário não encontrado: {email}\n")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuário não encontrado."
                )

        print(f"[DEV/RESET-PASSWORD] ✓ Senha resetada para: {email}\n")
        return {"ok": True}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DEV/RESET-PASSWORD] ✗ Erro: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao resetar senha: {str(e)}"
        )


@app.get("/api/dev/debug-user")
def dev_debug_user(
    email: str,
    x_dev_key: Optional[str] = Header(default=None, alias="X-DEV-KEY"),
):
    """Debug de usuário (DEV ONLY)"""
    require_dev_key(x_dev_key)

    e = email.lower().strip()
    
    try:
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT id, name, email, role, is_active,
                       LENGTH(password_hash) AS hash_len,
                       LEFT(password_hash, 4) AS hash_prefix
                FROM users
                WHERE email = :email
                LIMIT 1
            """), {"email": e}).mappings().first()

        if not row:
            print(f"[DEV/DEBUG-USER] ✗ Usuário não encontrado: {e}")
            return {"found": False, "email": e}

        ok = True if row.get("hash_len", 0) >= 20 else False

        print(f"[DEV/DEBUG-USER] ✓ Debug para: {e}")
        print(f"  - Hash length: {row.get('hash_len')}")
        print(f"  - Hash valid: {ok}")

        return {
            "found": True,
            "id": row["id"],
            "name": row["name"],
            "email": row["email"],
            "role": row["role"],
            "is_active": row["is_active"],
            "hash_len": row["hash_len"],
            "hash_prefix": row["hash_prefix"],
            "hash_ok": ok,
        }
    except Exception as e:
        print(f"[DEV/DEBUG-USER] ✗ Erro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao fazer debug: {str(e)}"
        )


# =========================================
# Routes — Usuários (Protegido - Apenas Admin)
# =========================================

@app.get("/api/users")
def list_users(request: Request):
    """
    Lista todos os usuários (Admin only)
    """
    print("\n[USERS/LIST] Listando usuários...")
    
    # Verifica autenticação
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")

    user_id = parse_session_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Sessão inválida")

    # Busca o usuário
    user = get_user_by_id(user_id)
    if not user or user.get("role") != "ADMIN":
        print("[USERS/LIST] ✗ Acesso negado: não é administrador")
        raise HTTPException(status_code=403, detail="Acesso negado")

    try:
        with engine.connect() as conn:
            q = text("""
                SELECT id, name, email, username, role, is_active, department_id, group_id
                FROM users
                ORDER BY name ASC
            """)
            results = conn.execute(q).mappings().all()

            users_list = [dict(row) for row in results]

            print(f"[USERS/LIST] ✓ {len(users_list)} usuários encontrados\n")
            return users_list

    except Exception as e:
        print(f"[USERS/LIST] ✗ Erro: {e}\n")
        raise HTTPException(status_code=500, detail=f"Erro ao listar usuários: {str(e)}")


@app.post("/api/users")
def create_user(
    payload: CreateUserRequest,
    request: Request,
):
    """
    Cria um novo usuário (Admin only)
    """
    print("\n[USERS/CREATE] Criando novo usuário...")
    
    # Verifica autenticação
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")

    user_id = parse_session_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Sessão inválida")

    # Busca o usuário logado
    current_user = get_user_by_id(user_id)
    if not current_user or current_user.get("role") != "ADMIN":
        print("[USERS/CREATE] ✗ Acesso negado: não é administrador")
        raise HTTPException(status_code=403, detail="Acesso negado")

    email = payload.email.lower().strip()
    
    print(f"[USERS/CREATE] Email: {email}")

    # Valida a senha
    try:
        ensure_bcrypt_password_ok(payload.password)
    except HTTPException as e:
        raise e

    password_hash = pwd_context.hash(payload.password)

    try:
        with engine.begin() as conn:
            # Verifica se o email já existe
            existing = conn.execute(
                text("SELECT id FROM users WHERE email = :email LIMIT 1"),
                {"email": email}
            ).mappings().first()

            if existing:
                print(f"[USERS/CREATE] ✗ Email já cadastrado: {email}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Este e-mail já está cadastrado no sistema"
                )

            # Insere o novo usuário
            conn.execute(text("""
                INSERT INTO users (name, email, username, password_hash, role, is_active)
                VALUES (:name, :email, :username, :password_hash, :role, 1)
            """), {
                "name": payload.name.strip(),
                "email": email,
                "username": payload.username.lower().strip() if payload.username else None,
                "password_hash": password_hash,
                "role": payload.role,
            })

        print(f"[USERS/CREATE] ✓ Usuário criado: {email}\n")
        return {"ok": True, "message": f"Usuário '{payload.name}' criado com sucesso"}

    except HTTPException:
        raise
    except IntegrityError:
        print(f"[USERS/CREATE] ✗ Email duplicado: {email}\n")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está cadastrado no sistema"
        )
    except Exception as e:
        print(f"[USERS/CREATE] ✗ Erro: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar usuário: {str(e)}"
        )


@app.delete("/api/users/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
):
    """
    Deleta um usuário (Admin only)
    """
    print(f"\n[USERS/DELETE] Deletando usuário ID: {user_id}")
    
    # Verifica autenticação
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")

    current_user_id = parse_session_token(token)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Sessão inválida")

    # Busca o usuário logado
    current_user = get_user_by_id(current_user_id)
    if not current_user or current_user.get("role") != "ADMIN":
        print("[USERS/DELETE] ✗ Acesso negado: não é administrador")
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Impede que um admin delete a si mesmo
    if current_user_id == user_id:
        print("[USERS/DELETE] ✗ Impossível deletar a si mesmo")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode deletar sua própria conta"
        )

    try:
        with engine.begin() as conn:
            res = conn.execute(
                text("DELETE FROM users WHERE id = :id LIMIT 1"),
                {"id": user_id}
            )

            if res.rowcount == 0:
                print(f"[USERS/DELETE] ✗ Usuário não encontrado: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuário não encontrado"
                )

        print(f"[USERS/DELETE] ✓ Usuário deletado: {user_id}\n")
        return {"ok": True, "message": "Usuário deletado com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[USERS/DELETE] ✗ Erro: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar usuário: {str(e)}"
        )


# =========================================
# Endpoints de Grupos (CRUD)
# =========================================

@app.get("/api/groups")
async def list_groups(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Lista grupos do departamento do usuário"""
    print("[GROUPS/LIST] Listando grupos...")
    
    try:
        with engine.connect() as conn:
            results = conn.execute(text("""
                SELECT id, name, description
                FROM `groups`
                WHERE department_id = :dept_id
                ORDER BY name ASC
            """), {"dept_id": current_user.get("department_id")}).mappings().all()

            groups = [dict(row) for row in results]
            print(f"[GROUPS/LIST] ✓ {len(groups)} grupos encontrados\n")
            return {"data": groups}

    except Exception as e:
        print(f"[GROUPS/LIST] ✗ Erro: {e}\n")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@app.post("/api/groups")
async def create_group(
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Cria um novo grupo (Admin only)"""
    print("[GROUPS/CREATE] Criando novo grupo...")
    
    # Verifica se é admin
    if current_user.get("role") != "ADMIN":
        print("[GROUPS/CREATE] ✗ Acesso negado: não é administrador")
        raise HTTPException(status_code=403, detail="Apenas administradores podem criar grupos")
    
    # ✅ Verifica department_id
    if not current_user.get("department_id"):
        print("[GROUPS/CREATE] ✗ Usuário sem departamento atribuído")
        raise HTTPException(
            status_code=400,
            detail="Usuário não tem departamento atribuído. Contate um administrador."
        )
    
    try:
        name = data.get("name", "").strip()
        description = data.get("description", "").strip()
        
        if not name:
            raise HTTPException(status_code=400, detail="Nome do grupo é obrigatório")
        
        with engine.begin() as conn:
            # Verifica se o grupo já existe neste departamento
            existing = conn.execute(text("""
                SELECT id FROM `groups`
                WHERE department_id = :dept_id AND name = :name
                LIMIT 1
            """), {
                "dept_id": current_user.get("department_id"),
                "name": name
            }).mappings().first()
            
            if existing:
                print(f"[GROUPS/CREATE] ✗ Grupo já existe: {name}")
                raise HTTPException(status_code=409, detail="Este grupo já existe neste departamento")
            
            # Insere o novo grupo
            conn.execute(text("""
                INSERT INTO `groups` (department_id, name, description)
                VALUES (:dept_id, :name, :description)
            """), {
                "dept_id": current_user.get("department_id"),
                "name": name,
                "description": description,
            })
        
        print(f"[GROUPS/CREATE] ✓ Grupo criado: {name}\n")
        return {"ok": True, "message": f"Grupo '{name}' criado com sucesso"}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[GROUPS/CREATE] ✗ Erro: {e}\n")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@app.put("/api/groups/{group_id}")
async def update_group(
    group_id: int,
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Atualiza um grupo (Admin only)"""
    print(f"[GROUPS/UPDATE] Atualizando grupo {group_id}...")
    
    # Verifica se é admin
    if current_user.get("role") != "ADMIN":
        print("[GROUPS/UPDATE] ✗ Acesso negado: não é administrador")
        raise HTTPException(status_code=403, detail="Apenas administradores podem atualizar grupos")
    
    try:
        name = data.get("name", "").strip()
        description = data.get("description", "").strip()
        
        if not name:
            raise HTTPException(status_code=400, detail="Nome do grupo é obrigatório")
        
        with engine.begin() as conn:
            # Verifica se o grupo existe e pertence ao departamento
            group = conn.execute(text("""
                SELECT id, department_id FROM `groups`
                WHERE id = :id
                LIMIT 1
            """), {"id": group_id}).mappings().first()
            
            if not group:
                raise HTTPException(status_code=404, detail="Grupo não encontrado")
            
            if group["department_id"] != current_user.get("department_id"):
                print("[GROUPS/UPDATE] ✗ Acesso negado: grupo de outro departamento")
                raise HTTPException(status_code=403, detail="Acesso negado")
            
            # Atualiza o grupo
            conn.execute(text("""
                UPDATE `groups`
                SET name = :name, description = :description
                WHERE id = :id
            """), {
                "name": name,
                "description": description,
                "id": group_id,
            })
        
        print(f"[GROUPS/UPDATE] ✓ Grupo atualizado\n")
        return {"ok": True, "message": "Grupo atualizado com sucesso"}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[GROUPS/UPDATE] ✗ Erro: {e}\n")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@app.delete("/api/groups/{group_id}")
async def delete_group(
    group_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Deleta um grupo (Admin only)"""
    print(f"[GROUPS/DELETE] Deletando grupo {group_id}...")
    
    # Verifica se é admin
    if current_user.get("role") != "ADMIN":
        print("[GROUPS/DELETE] ✗ Acesso negado: não é administrador")
        raise HTTPException(status_code=403, detail="Apenas administradores podem deletar grupos")
    
    try:
        with engine.begin() as conn:
            # Verifica se o grupo existe e pertence ao departamento
            group = conn.execute(text("""
                SELECT id, department_id FROM `groups`
                WHERE id = :id
                LIMIT 1
            """), {"id": group_id}).mappings().first()
            
            if not group:
                raise HTTPException(status_code=404, detail="Grupo não encontrado")
            
            if group["department_id"] != current_user.get("department_id"):
                print("[GROUPS/DELETE] ✗ Acesso negado: grupo de outro departamento")
                raise HTTPException(status_code=403, detail="Acesso negado")
            
            # Deleta o grupo
            conn.execute(text("""
                DELETE FROM `groups`
                WHERE id = :id
            """), {"id": group_id})
        
        print(f"[GROUPS/DELETE] ✓ Grupo deletado\n")
        return {"ok": True, "message": "Grupo deletado com sucesso"}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[GROUPS/DELETE] ✗ Erro: {e}\n")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


# =========================================
# Endpoints do Cofre de Senhas
# =========================================

@app.get("/api/passwords")
async def list_passwords(
    department_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Lista senhas do departamento"""
    print(f"\n[VAULT/LIST] Listando senhas do departamento {department_id}...")
    
    try:
        with engine.connect() as conn:
            # Senhas públicas OU criadas pelo usuário OU compartilhadas com seu grupo
            query = text("""
                SELECT DISTINCT
                    p.id,
                    p.client,
                    p.description,
                    p.email,
                    p.link,
                    p.observation,
                    p.is_public,
                    p.group_id,
                    g.name as group_name,
                    p.device_id,
                    d.name as device_name,
                    p.created_by,
                    p.created_at,
                    p.updated_at
                FROM passwords p
                LEFT JOIN `groups` g ON p.group_id = g.id
                LEFT JOIN devices d ON p.device_id = d.id
                WHERE p.department_id = :dept_id
                AND (
                    p.is_public = TRUE
                    OR p.created_by = :user_id
                    OR EXISTS (
                        SELECT 1 FROM password_shares ps
                        WHERE ps.password_id = p.id
                        AND ps.group_id = :group_id
                    )
                )
                ORDER BY p.created_at DESC
            """)

            results = conn.execute(query, {
                "dept_id": department_id,
                "user_id": current_user["id"],
                "group_id": current_user.get("group_id"),
            }).mappings().all()

            passwords = [dict(row) for row in results]

            print(f"[VAULT/LIST] ✓ {len(passwords)} senhas encontradas\n")
            return {"data": passwords}

    except Exception as e:
        print(f"[VAULT/LIST] ✗ Erro: {e}\n")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@app.post("/api/passwords")
async def create_password(
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Cria nova senha no cofre"""
    print("[VAULT/CREATE] Criando nova senha...")
    
    try:
        # Encripta a senha (TODO: implementar encriptação real)
        encrypted_password = data.get("password")

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO passwords (
                    department_id, group_id, client, description, email,
                    password_encrypted, link, observation, is_public,
                    device_id, created_by
                ) VALUES (
                    :dept_id, :group_id, :client, :description, :email,
                    :password, :link, :observation, :is_public,
                    :device_id, :user_id
                )
            """), {
                "dept_id": current_user.get("department_id"),
                "group_id": data.get("group_id"),
                "client": data.get("client"),
                "description": data.get("description"),
                "email": data.get("email"),
                "password": encrypted_password,
                "link": data.get("link"),
                "observation": data.get("observation"),
                "is_public": data.get("is_public", False),
                "device_id": data.get("device_id"),
                "user_id": current_user["id"],
            })

            # Registra em auditoria
            conn.execute(text("""
                INSERT INTO audit_logs (
                    user_id, department_id, module, action, object_type
                ) VALUES (
                    :user_id, :dept_id, 'PASSWORD_VAULT', 'CREATE', 'PASSWORD'
                )
            """), {
                "user_id": current_user["id"],
                "dept_id": current_user.get("department_id"),
            })

        print("[VAULT/CREATE] ✓ Senha criada com sucesso\n")
        return {"ok": True, "message": "Senha criada com sucesso"}

    except Exception as e:
        print(f"[VAULT/CREATE] ✗ Erro: {e}\n")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@app.put("/api/passwords/{password_id}")
async def update_password(
    password_id: int,
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Atualiza uma senha"""
    print(f"[VAULT/UPDATE] Atualizando senha {password_id}...")
    
    try:
        with engine.begin() as conn:
            # Verifica permissão (apenas criador ou admin)
            pwd = conn.execute(
                text("SELECT created_by FROM passwords WHERE id = :id"),
                {"id": password_id}
            ).mappings().first()

            if not pwd:
                raise HTTPException(status_code=404, detail="Senha não encontrada")

            if pwd["created_by"] != current_user["id"] and current_user.get("role") != "ADMIN":
                raise HTTPException(status_code=403, detail="Acesso negado")

            # Atualiza
            conn.execute(text("""
                UPDATE passwords SET
                    client = :client,
                    description = :description,
                    email = :email,
                    link = :link,
                    observation = :observation,
                    is_public = :is_public,
                    device_id = :device_id
                WHERE id = :id
            """), {
                "client": data.get("client"),
                "description": data.get("description"),
                "email": data.get("email"),
                "link": data.get("link"),
                "observation": data.get("observation"),
                "is_public": data.get("is_public", False),
                "device_id": data.get("device_id"),
                "id": password_id,
            })

        print(f"[VAULT/UPDATE] ✓ Senha atualizada\n")
        return {"ok": True, "message": "Senha atualizada com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[VAULT/UPDATE] ✗ Erro: {e}\n")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@app.delete("/api/passwords/{password_id}")
async def delete_password(
    password_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Deleta uma senha"""
    print(f"[VAULT/DELETE] Deletando senha {password_id}...")
    
    try:
        with engine.begin() as conn:
            pwd = conn.execute(
                text("SELECT created_by FROM passwords WHERE id = :id"),
                {"id": password_id}
            ).mappings().first()

            if not pwd:
                raise HTTPException(status_code=404, detail="Senha não encontrada")

            if pwd["created_by"] != current_user["id"] and current_user.get("role") != "ADMIN":
                raise HTTPException(status_code=403, detail="Acesso negado")

            conn.execute(
                text("DELETE FROM passwords WHERE id = :id"),
                {"id": password_id}
            )

        print(f"[VAULT/DELETE] ✓ Senha deletada\n")
        return {"ok": True, "message": "Senha deletada com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[VAULT/DELETE] ✗ Erro: {e}\n")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@app.get("/api/users/me/department")
async def get_user_department(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Obtém departamento do usuário logado"""
    print("[DEPT/GET] Obtendo departamento...")
    
    try:
        with engine.connect() as conn:
            dept = conn.execute(text("""
                SELECT id, name, description
                FROM departments
                WHERE id = :id
            """), {"id": current_user.get("department_id")}).mappings().first()

            if not dept:
                raise HTTPException(status_code=404, detail="Departamento não encontrado")

            print(f"[DEPT/GET] ✓ Departamento: {dept['name']}\n")
            return dict(dept)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[DEPT/GET] ✗ Erro: {e}\n")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@app.post("/api/audit-logs")
async def create_audit_log(
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Registra ação de auditoria"""
    print("[AUDIT/CREATE] Registrando auditoria...")
    
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO audit_logs (
                    user_id, department_id, module, action, object_type,
                    object_id, ip_address, description
                ) VALUES (
                    :user_id, :dept_id, :module, :action, :object_type,
                    :object_id, :ip_address, :description
                )
            """), {
                "user_id": current_user["id"],
                "dept_id": current_user.get("department_id"),
                "module": data.get("module"),
                "action": data.get("action"),
                "object_type": data.get("object_type"),
                "object_id": data.get("object_id"),
                "ip_address": data.get("ip_address"),
                "description": data.get("description"),
            })

        print("[AUDIT/CREATE] ✓ Auditoria registrada\n")
        return {"ok": True}

    except Exception as e:
        print(f"[AUDIT/CREATE] ✗ Erro (ignorado): {e}\n")
        return {"ok": True}  # Não interrompe o fluxo


# =========================================
# Startup event
# =========================================
@app.on_event("startup")
async def startup_event():
    print("\n" + "=" * 60)
    print("✓ CPE Control API iniciada com sucesso!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)