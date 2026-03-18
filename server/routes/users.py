"""
Rotas de usuários: CRUD
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import text
from database import engine
from security import get_current_user
from utils import (
    normalize_email,
    normalize_string,
    validate_email_format,
    validate_password_strength,
    hash_password,
)

router = APIRouter(prefix="/api/users", tags=["Users"])

# =========================================
# ➕ CREATE USER
# =========================================

@router.post("/")
async def create_user(
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Cria um novo usuário (apenas ADMIN)"""
    print(f"[USERS/CREATE] Criando novo usuário (solicitado por: {current_user['id']})")
    
    try:
        # ✅ Verifica permissão
        if current_user["role"] != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas ADMINs podem criar usuários"
            )

        # ✅ VALIDAÇÕES
        required_fields = ["name", "email", "username", "password", "role"]
        for field in required_fields:
            if field not in data or not data[field]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Campo '{field}' é obrigatório"
                )

        # Normalizar e validar nome
        name = normalize_string(data["name"])
        if not name or len(name) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nome deve ter no mínimo 3 caracteres"
            )

        # Normalizar e validar email
        email = normalize_email(data["email"])
        if not validate_email_format(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email inválido"
            )

        # Normalizar e validar username
        username = normalize_string(data["username"]).lower()
        if not username or len(username) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username deve ter no mínimo 3 caracteres"
            )

        # Validar role
        if data["role"] not in ["USER", "ADMIN", "TI"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role inválido. Use: USER, ADMIN ou TI"
            )

        # Validar senha
        password = data["password"]
        if not validate_password_strength(password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Senha deve ter no mínimo 8 caracteres"
            )

        # Hash da senha
        password_hash = hash_password(password)

        with engine.begin() as conn:
            # Verificar se email já existe
            existing_email = conn.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email}
            ).first()

            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email já cadastrado no sistema"
                )

            # Verificar se username já existe
            existing_username = conn.execute(
                text("SELECT id FROM users WHERE username = :username"),
                {"username": username}
            ).first()

            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username já cadastrado no sistema"
                )

            # ✅ USAR NOW() PARA MYSQL (não datetime('now') do SQLite)
            conn.execute(
                text("""
                    INSERT INTO users 
                    (name, email, username, password_hash, role, is_active, created_at)
                    VALUES (:name, :email, :username, :password_hash, :role, :is_active, NOW())
                """),
                {
                    "name": name,
                    "email": email,
                    "username": username,
                    "password_hash": password_hash,
                    "role": data["role"],
                    "is_active": 1
                }
            )

        print(f"[USERS/CREATE] ✓ Novo usuário criado: {email}")
        return {
            "success": True,
            "message": f"Usuário '{name}' criado com sucesso"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[USERS/CREATE] ✗ Erro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar usuário: {str(e)}"
        )


# =========================================
# 🗑️ DELETE USER
# =========================================

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Deleta um usuário (apenas ADMIN)"""
    print(f"[USERS/DELETE] Deletando usuário: {user_id} (solicitado por: {current_user['id']})")
    
    try:
        # ✅ Verifica permissão
        if current_user["role"] != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas ADMINs podem deletar usuários"
            )

        # ✅ Não permitir deletar a si mesmo
        if current_user["id"] == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Você não pode deletar sua própria conta"
            )

        with engine.begin() as conn:
            # Verificar se usuário existe
            user_exists = conn.execute(
                text("SELECT id, name FROM users WHERE id = :id"),
                {"id": user_id}
            ).first()

            if not user_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuário não encontrado"
                )

            user_name = user_exists[1]

            # Deletar usuário
            conn.execute(
                text("DELETE FROM users WHERE id = :id"),
                {"id": user_id}
            )

        print(f"[USERS/DELETE] ✓ Usuário deletado: {user_name}")
        return {
            "success": True,
            "message": f"Usuário '{user_name}' deletado com sucesso"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[USERS/DELETE] ✗ Erro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar usuário: {str(e)}"
        )


# =========================================
# 👥 LIST USERS
# =========================================

@router.get("/")
async def list_users(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Lista todos os usuários (apenas para ADMIN)"""
    print(f"[USERS/LIST] Listando usuários (solicitado por: {current_user['id']})")
    
    try:
        # ✅ Verifica permissão
        if current_user["role"] != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas ADMINs podem listar usuários"
            )

        with engine.connect() as conn:
            users_result = conn.execute(
                text("""
                    SELECT id, name, email, username, role, sector, unit, is_active,
                           department_id, group_id, created_at
                    FROM users
                    ORDER BY id ASC
                """)
            ).mappings().all()

        users = [dict(u) for u in users_result]

        print(f"[USERS/LIST] ✓ {len(users)} usuários listados")
        return {
            "success": True,
            "total": len(users),
            "users": users
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[USERS/LIST] ✗ Erro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar usuários: {str(e)}"
        )


# =========================================
# 👤 GET USER BY ID
# =========================================

@router.get("/{user_id}")
async def get_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Obtém dados de um usuário"""
    print(f"[USERS/GET] Obtendo usuário: {user_id}")
    
    try:
        # ✅ Verifica se é ADMIN ou está acessando a si mesmo
        if current_user["role"] != "ADMIN" and current_user["id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado"
            )

        with engine.connect() as conn:
            user_result = conn.execute(
                text("""
                    SELECT id, name, email, username, role, sector, unit, is_active,
                           department_id, group_id, created_at
                    FROM users
                    WHERE id = :id
                    LIMIT 1
                """),
                {"id": user_id}
            ).mappings().first()

        if not user_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )

        user = dict(user_result)

        print(f"[USERS/GET] ✓ Usuário obtido: {user['name']}")
        return {
            "success": True,
            "user": user
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[USERS/GET] ✗ Erro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter usuário: {str(e)}"
        )


# =========================================
# ✏️ UPDATE USER
# =========================================

@router.put("/{user_id}")
async def update_user(
    user_id: int,
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Atualiza dados de um usuário"""
    print(f"[USERS/UPDATE] Atualizando usuário: {user_id}")
    
    try:
        # ✅ Verifica permissão
        if current_user["role"] != "ADMIN" and current_user["id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado"
            )

        # ✅ Valida campos
        updates = {}
        
        if "name" in data and data["name"]:
            name = normalize_string(data["name"])
            if not name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nome não pode estar vazio"
                )
            updates["name"] = name

        if "email" in data and data["email"]:
            email = normalize_email(data["email"])
            if not validate_email_format(email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email inválido"
                )
            
            # ✅ Verificar se email já existe (em outro usuário)
            with engine.connect() as conn:
                existing_email = conn.execute(
                    text("SELECT id FROM users WHERE email = :email AND id != :user_id"),
                    {"email": email, "user_id": user_id}
                ).first()
                
                if existing_email:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email já cadastrado por outro usuário"
                    )
            
            updates["email"] = email

        if "username" in data and data["username"]:
            username = normalize_string(data["username"]).lower()
            if not username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username não pode estar vazio"
                )
            
            # ✅ Verificar se username já existe (em outro usuário)
            with engine.connect() as conn:
                existing_username = conn.execute(
                    text("SELECT id FROM users WHERE username = :username AND id != :user_id"),
                    {"username": username, "user_id": user_id}
                ).first()
                
                if existing_username:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username já cadastrado por outro usuário"
                    )
            
            updates["username"] = username

        if "sector" in data and data["sector"]:
            updates["sector"] = normalize_string(data["sector"])

        if "unit" in data and data["unit"]:
            updates["unit"] = normalize_string(data["unit"])

        # ✅ Apenas ADMIN pode alterar role e is_active
        if current_user["role"] == "ADMIN":
            if "role" in data and data["role"]:
                if data["role"] not in ["USER", "ADMIN", "TI"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Role inválido"
                    )
                updates["role"] = data["role"]

            if "is_active" in data:
                updates["is_active"] = 1 if data["is_active"] else 0

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum campo para atualizar"
            )

        # ✅ Constrói SQL dinamicamente
        set_clause = ", ".join([f"`{k}` = :{k}" for k in updates.keys()])
        updates["id"] = user_id

        with engine.begin() as conn:
            result = conn.execute(
                text(f"UPDATE users SET {set_clause} WHERE id = :id"),
                updates
            )

            if result.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuário não encontrado"
                )

        print(f"[USERS/UPDATE] ✓ Usuário atualizado: {user_id}")
        return {
            "success": True,
            "message": "Usuário atualizado com sucesso"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[USERS/UPDATE] ✗ Erro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar usuário: {str(e)}"
        )


# =========================================
# 🔑 CHANGE PASSWORD
# =========================================

@router.put("/{user_id}/password")
async def change_password(
    user_id: int,
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Muda a senha de um usuário"""
    print(f"[USERS/CHANGE-PASSWORD] Alterando senha do usuário: {user_id}")
    
    try:
        # ✅ Verifica permissão
        if current_user["role"] != "ADMIN" and current_user["id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado"
            )

        new_password = data.get("password", "").strip()

        if not new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nova senha obrigatória"
            )

        if not validate_password_strength(new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Senha deve ter pelo menos 8 caracteres"
            )

        # ✅ Hash da nova senha
        password_hash = hash_password(new_password)

        with engine.begin() as conn:
            result = conn.execute(
                text("UPDATE users SET password_hash = :hash WHERE id = :id"),
                {"hash": password_hash, "id": user_id}
            )

            if result.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuário não encontrado"
                )

        print(f"[USERS/CHANGE-PASSWORD] ✓ Senha alterada para usuário: {user_id}")
        return {
            "success": True,
            "message": "Senha alterada com sucesso"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[USERS/CHANGE-PASSWORD] ✗ Erro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao alterar senha: {str(e)}"
        )