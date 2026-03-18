"""
Rotas de autenticação: login, logout, me
"""

from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, status, Header
from fastapi.responses import JSONResponse
from sqlalchemy import text
from database import engine
from security import (
    make_session_token,
    set_session_cookie,
    clear_session_cookie,
    get_current_user,
    require_dev_key,
    parse_session_token,
    get_user_by_email,
    get_user_by_id,
    COOKIE_NAME,
)
from utils import (
    normalize_email,
    validate_email_format,
    validate_password_strength,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# =========================================
# 🔐 LOGIN
# =========================================

@router.post("/login")
async def login(request: Request, data: dict):
    """
    Login do usuário
    Body: { "email": "user@example.com", "password": "senha123" }
    """
    print("[AUTH/LOGIN] Iniciando login...")
    
    try:
        email = normalize_email(data.get("email", ""))
        password = data.get("password", "")

        # Validações
        if not email or not validate_email_format(email):
            print("[AUTH/LOGIN] ✗ Email inválido")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email inválido"
            )

        if not password:
            print("[AUTH/LOGIN] ✗ Senha não fornecida")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Senha obrigatória"
            )

        # Busca usuário
        user = get_user_by_email(email)

        if not user:
            print(f"[AUTH/LOGIN] ✗ Usuário não encontrado: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos"
            )

        # Verifica senha
        if not verify_password(password, user["password_hash"]):
            print(f"[AUTH/LOGIN] ✗ Senha incorreta para: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos"
            )

        # Verifica se está ativo
        if user["is_active"] != 1:
            print(f"[AUTH/LOGIN] ✗ Usuário inativo: {email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário inativo"
            )

        # Cria token de sessão
        token = make_session_token(user["id"])

        # Cria response
        response = JSONResponse({
            "success": True,
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "message": "Login realizado com sucesso!"
        })

        # Define cookie
        set_session_cookie(response, token)

        print(f"[AUTH/LOGIN] ✓ Login bem-sucedido: {email}\n")
        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH/LOGIN] ✗ Erro: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro no login: {str(e)}"
        )


# =========================================
# 🚪 LOGOUT
# =========================================

@router.post("/logout")
async def logout(request: Request):
    """Logout do usuário"""
    token = request.cookies.get(COOKIE_NAME)
    email = "anônimo"
    
    if token:
        user_id = parse_session_token(token)
        if user_id:
            user = get_user_by_id(user_id)
            if user:
                email = user.get("email", "anônimo")
    
    print(f"[AUTH/LOGOUT] Logout para: {email}")

    response = JSONResponse({
        "success": True,
        "message": "Logout realizado com sucesso!"
    })

    clear_session_cookie(response)

    print("[AUTH/LOGOUT] ✓ Logout bem-sucedido\n")
    return response


# =========================================
# 👤 ME (Usuário atual)
# =========================================

@router.get("/me")
async def me(request: Request):
    """Retorna dados do usuário autenticado"""
    print("[AUTH/ME] Buscando dados do usuário...")
    
    try:
        token = request.cookies.get(COOKIE_NAME)
        
        if not token:
            print("[AUTH/ME] ✗ Token não encontrado")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Não autenticado"
            )

        user_id = parse_session_token(token)
        if not user_id:
            print("[AUTH/ME] ✗ Token inválido")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessão inválida"
            )

        user = get_user_by_id(user_id)
        if not user or user.get("is_active") != 1:
            print("[AUTH/ME] ✗ Usuário não encontrado ou inativo")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário inválido"
            )

        print(f"[AUTH/ME] ✓ Usuário obtido: {user['name']}\n")

        return {
            "success": True,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "department_id": user.get("department_id"),
                "group_id": user.get("group_id"),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH/ME] ✗ Erro: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro: {str(e)}"
        )


# =========================================
# 🧪 DEV ENDPOINTS
# =========================================

@router.post("/dev/login-as")
async def dev_login_as(data: dict, x_dev_key: str = Header(None)):
    """
    [DEV] Faz login como qualquer usuário
    Headers: X-DEV-KEY
    Body: { "user_id": 1 }
    """
    print("[AUTH/DEV/LOGIN-AS] Requisição de login forçado...")
    
    try:
        require_dev_key(x_dev_key)
        
        user_id = data.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id obrigatório"
            )

        # Busca usuário
        user = get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )

        # Cria token
        token = make_session_token(user["id"])

        response = JSONResponse({
            "success": True,
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "message": f"[DEV] Login como {user['name']}"
        })

        set_session_cookie(response, token)

        print(f"[AUTH/DEV/LOGIN-AS] ✓ Login forçado como: {user['name']}\n")
        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH/DEV/LOGIN-AS] ✗ Erro: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro: {str(e)}"
        )


@router.get("/dev/list-users")
async def dev_list_users(x_dev_key: str = Header(None)):
    """
    [DEV] Lista todos os usuários
    Headers: X-DEV-KEY
    """
    print("[AUTH/DEV/LIST-USERS] Listando usuários...")
    
    try:
        require_dev_key(x_dev_key)

        with engine.connect() as conn:
            users_result = conn.execute(
                text("""
                    SELECT id, name, email, role, is_active, created_at
                    FROM users
                    ORDER BY id ASC
                """)
            ).mappings().all()

        users = [dict(u) for u in users_result]

        print(f"[AUTH/DEV/LIST-USERS] ✓ {len(users)} usuários listados\n")
        return {
            "success": True,
            "total": len(users),
            "users": users
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH/DEV/LIST-USERS] ✗ Erro: {e}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro: {str(e)}"
        )