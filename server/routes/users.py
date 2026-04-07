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

# ================================================== 
# ➕ CREATE USER
# Data: 02/04/2026 18:00
# ==================================================

@router.post("/")
async def create_user(
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Cria um novo usuário (apenas ADMIN, TI e MANAGER)"""
    print(f"[USERS/CREATE] Criando novo usuário (solicitado por: {current_user['id']} - {current_user['role']})")
    
    try:
        # ================================================== 
        # VALIDAÇÃO DE PERMISSÃO
        # Data: 02/04/2026 18:00
        # ==================================================
        if current_user["role"] not in ["ADMIN", "TI", "MANAGER"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas ADMIN, TI e MANAGER podem criar usuários"
            )
        # ================================================== 
        # [FIM] VALIDAÇÃO DE PERMISSÃO
        # Data: 02/04/2026 18:00
        # ==================================================

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
        if data["role"] not in ["USER", "RESPONSAVEL_GRUPO", "ADMIN", "TI", "MANAGER"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role inválido. Use: USER, RESPONSAVEL_GRUPO, ADMIN, TI ou MANAGER"
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

            # ✅ Validar group_id se fornecido
            group_id = None
            if "group_id" in data and data["group_id"]:
                group_id = int(data["group_id"])
                # Verificar se grupo existe
                group_exists = conn.execute(
                    text("SELECT id FROM `cpe_grupo` WHERE id = :id"),
                    {"id": group_id}
                ).first()

                if not group_exists:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Grupo/Setor não encontrado"
                    )

            # ✅ USAR NOW() PARA MYSQL
            conn.execute(
                text("""
                    INSERT INTO users 
                    (name, email, username, password_hash, role, group_id, is_active, created_at)
                    VALUES (:name, :email, :username, :password_hash, :role, :group_id, :is_active, NOW())
                """),
                {
                    "name": name,
                    "email": email,
                    "username": username,
                    "password_hash": password_hash,
                    "role": data["role"],
                    "group_id": group_id,
                    "is_active": 1
                }
            )

        print(f"[USERS/CREATE] ✓ Novo usuário criado: {email} (por: {current_user['id']} - {current_user['role']})")
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

# ================================================== 
# [FIM] CREATE USER
# Data: 02/04/2026 18:00
# ==================================================
        


# ================================================== 
# 🗑️ DELETE USER
# Data: 02/04/2026 18:05
# ==================================================

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Deleta um usuário (apenas ADMIN, TI e MANAGER)"""
    print(f"[USERS/DELETE] Deletando usuário: {user_id} (solicitado por: {current_user['id']} - {current_user['role']})")
    
    try:
        # ================================================== 
        # VALIDAÇÃO DE PERMISSÃO
        # Data: 02/04/2026 18:05
        # ==================================================
        if current_user["role"] not in ["ADMIN", "TI", "MANAGER"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas ADMIN, TI e MANAGER podem deletar usuários"
            )
        # ================================================== 
        # [FIM] VALIDAÇÃO DE PERMISSÃO
        # Data: 02/04/2026 18:05
        # ==================================================

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

        print(f"[USERS/DELETE] ✓ Usuário deletado: {user_name} (por: {current_user['id']} - {current_user['role']})")
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

# ================================================== 
# [FIM] DELETE USER
# Data: 02/04/2026 18:05
# ==================================================


# ================================================== 
# 👥 LIST USERS
# Data: 02/04/2026 18:10
# ==================================================

@router.get("/")
async def list_users(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Lista usuários conforme permissão do role"""
    print(f"[USERS/LIST] Listando usuários (solicitado por: {current_user['id']} - {current_user['role']})")
    
    try:
        # ================================================== 
        # VALIDAÇÃO DE PERMISSÃO
        # Data: 02/04/2026 18:10
        # ==================================================
        if current_user["role"] not in ["ADMIN", "TI", "MANAGER", "RESPONSAVEL_GRUPO"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para listar usuários"
            )
        # ================================================== 
        # [FIM] VALIDAÇÃO DE PERMISSÃO
        # Data: 02/04/2026 18:10
        # ==================================================

        with engine.connect() as conn:
            # ✅ Se RESPONSAVEL_GRUPO, filtra apenas usuários do seu grupo
            if current_user["role"] == "RESPONSAVEL_GRUPO":
                users_result = conn.execute(
                    text("""
                        SELECT id, name, email, username, role, sector, unit, is_active,
                               department_id, group_id, created_at
                        FROM users
                        WHERE group_id = :group_id
                        ORDER BY name ASC
                    """),
                    {"group_id": current_user.get("group_id")}
                ).mappings().all()
                
                print(f"[USERS/LIST] Filtrando por grupo: {current_user.get('group_id')}")
            
            # ✅ Se ADMIN, TI ou MANAGER, lista TODOS os usuários
            else:
                users_result = conn.execute(
                    text("""
                        SELECT id, name, email, username, role, sector, unit, is_active,
                               department_id, group_id, created_at
                        FROM users
                        ORDER BY name ASC
                    """)
                ).mappings().all()

        users = [dict(u) for u in users_result]

        print(f"[USERS/LIST] ✓ {len(users)} usuários listados (por: {current_user['id']} - {current_user['role']})")
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

# ================================================== 
# [FIM] LIST USERS
# Data: 02/04/2026 18:10
# ==================================================


# ================================================== 
# 👤 GET USER BY ID
# Data: 02/04/2026 18:15
# ==================================================

@router.get("/{user_id}")
async def get_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Obtém dados de um usuário conforme permissão do role"""
    print(f"[USERS/GET] Obtendo usuário: {user_id} (solicitado por: {current_user['id']} - {current_user['role']})")
    
    try:
        # ================================================== 
        # VALIDAÇÃO DE PERMISSÃO
        # Data: 02/04/2026 18:15
        # ==================================================
        
        # ✅ ADMIN, TI e MANAGER = vêem qualquer usuário
        if current_user["role"] in ["ADMIN", "TI", "MANAGER"]:
            pass  # Permitir acesso total
        
        # ✅ RESPONSAVEL_GRUPO = vê apenas usuários do seu grupo
        elif current_user["role"] == "RESPONSAVEL_GRUPO":
            with engine.connect() as conn:
                user_to_check = conn.execute(
                    text("SELECT group_id FROM users WHERE id = :id"),
                    {"id": user_id}
                ).first()
                
                if not user_to_check or user_to_check[0] != current_user.get("group_id"):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Você só pode ver usuários do seu grupo"
                    )
        
        # ✅ USER = vê apenas a si mesmo
        elif current_user["id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você só pode ver seus próprios dados"
            )
        
        # ❌ Outros roles são bloqueados
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado"
            )
        
        # ================================================== 
        # [FIM] VALIDAÇÃO DE PERMISSÃO
        # Data: 02/04/2026 18:15
        # ==================================================

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

        print(f"[USERS/GET] ✓ Usuário obtido: {user['name']} (por: {current_user['id']} - {current_user['role']})")
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

# ================================================== 
# [FIM] GET USER BY ID
# Data: 02/04/2026 18:15
# ==================================================

# ================================================== 
# ✏️ UPDATE USER
# Data: 02/04/2026 18:20
# ==================================================

@router.put("/{user_id}")
async def update_user(
    user_id: int,
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Atualiza dados de um usuário conforme permissão do role"""
    print(f"[USERS/UPDATE] Atualizando usuário: {user_id} (solicitado por: {current_user['id']} - {current_user['role']})")
    
    try:
        # ================================================== 
        # VALIDAÇÃO DE PERMISSÃO
        # Data: 02/04/2026 18:20
        # ==================================================
        
        # ✅ ADMIN, TI e MANAGER = editam QUALQUER usuário
        if current_user["role"] in ["ADMIN", "TI", "MANAGER"]:
            can_edit_all_fields = True
        
        # ✅ RESPONSAVEL_GRUPO = edita APENAS usuários do seu grupo
        elif current_user["role"] == "RESPONSAVEL_GRUPO":
            with engine.connect() as conn:
                user_to_check = conn.execute(
                    text("SELECT group_id FROM users WHERE id = :id"),
                    {"id": user_id}
                ).first()
                
                if not user_to_check or user_to_check[0] != current_user.get("group_id"):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Você só pode editar usuários do seu grupo"
                    )
            
            can_edit_all_fields = False  # RESPONSAVEL_GRUPO só edita campos básicos
        
        # ✅ USER = edita apenas a si mesmo
        elif current_user["id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você só pode editar seus próprios dados"
            )
        else:
            can_edit_all_fields = False  # USER só edita campos básicos
        
        # ❌ Outros roles são bloqueados
        if current_user["role"] not in ["ADMIN", "TI", "MANAGER", "RESPONSAVEL_GRUPO", "USER"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado"
            )
        
        # ================================================== 
        # [FIM] VALIDAÇÃO DE PERMISSÃO
        # Data: 02/04/2026 18:20
        # ==================================================

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

        # ================================================== 
        # CAMPOS RESTRITOS - APENAS ADMIN E TI
        # Data: 02/04/2026 18:20
        # ==================================================
        
        # ✅ Apenas ADMIN, TI e MANAGER podem alterar role e group_id
        if can_edit_all_fields:
            if "role" in data and data["role"]:
                if data["role"] not in ["USER", "RESPONSAVEL_GRUPO", "ADMIN", "TI", "MANAGER"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Role inválido. Use: USER, RESPONSAVEL_GRUPO, ADMIN, TI ou MANAGER"
                    )
                updates["role"] = data["role"]

            if "group_id" in data and data["group_id"]:
                group_id = int(data["group_id"])
                # Verificar se grupo existe
                with engine.connect() as conn_check:
                    group_exists = conn_check.execute(
                        text("SELECT id FROM `cpe_grupo` WHERE id = :id"),
                        {"id": group_id}
                    ).first()

                    if not group_exists:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Grupo/Setor não encontrado"
                        )
                updates["group_id"] = group_id

            if "is_active" in data:
                updates["is_active"] = 1 if data["is_active"] else 0
        
        else:
            # ❌ RESPONSAVEL_GRUPO e USER NÃO podem alterar role, group_id ou is_active
            if "role" in data:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Você não tem permissão para alterar role"
                )
            
            if "group_id" in data:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Você não tem permissão para alterar grupo"
                )
            
            if "is_active" in data:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Você não tem permissão para alterar status"
                )
        
        # ================================================== 
        # [FIM] CAMPOS RESTRITOS
        # Data: 02/04/2026 18:20
        # ==================================================

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

        print(f"[USERS/UPDATE] ✓ Usuário atualizado: {user_id} (por: {current_user['id']} - {current_user['role']})")
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

# ================================================== 
# [FIM] UPDATE USER
# Data: 02/04/2026 18:20
# ==================================================


# ================================================== 
# 🔑 CHANGE PASSWORD
# Data: 02/04/2026 18:25
# ==================================================

@router.put("/{user_id}/password")
async def change_password(
    user_id: int,
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Altera a senha de um usuário conforme permissão do role"""
    print(f"[USERS/CHANGE-PASSWORD] Alterando senha do usuário: {user_id} (solicitado por: {current_user['id']} - {current_user['role']})")
    
    try:
        # ================================================== 
        # VALIDAÇÃO DE PERMISSÃO
        # Data: 02/04/2026 18:25
        # ==================================================
        
        # ✅ ADMIN, TI e MANAGER = alteram senha de QUALQUER usuário
        if current_user["role"] in ["ADMIN", "TI", "MANAGER"]:
            can_change_all = True
        
        # ✅ RESPONSAVEL_GRUPO = altera senha APENAS de usuários do seu grupo
        elif current_user["role"] == "RESPONSAVEL_GRUPO":
            with engine.connect() as conn:
                user_to_check = conn.execute(
                    text("SELECT group_id FROM users WHERE id = :id"),
                    {"id": user_id}
                ).first()
                
                if not user_to_check or user_to_check[0] != current_user.get("group_id"):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Você só pode alterar senha de usuários do seu grupo"
                    )
            
            can_change_all = False
        
        # ✅ USER = altera apenas sua própria senha
        elif current_user["id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você só pode alterar sua própria senha"
            )
        else:
            can_change_all = False
        
        # ❌ Outros roles são bloqueados
        if current_user["role"] not in ["ADMIN", "TI", "MANAGER", "RESPONSAVEL_GRUPO", "USER"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado"
            )
        
        # ================================================== 
        # [FIM] VALIDAÇÃO DE PERMISSÃO
        # Data: 02/04/2026 18:25
        # ==================================================

        # ✅ Valida nova senha
        new_password = data.get("password", "").strip()

        if not new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nova senha é obrigatória"
            )

        if not validate_password_strength(new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Senha deve ter no mínimo 8 caracteres"
            )

        # ✅ Hash da nova senha
        password_hash = hash_password(new_password)

        with engine.begin() as conn:
            # ✅ Verificar se usuário existe
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

            # ✅ Atualizar senha
            result = conn.execute(
                text("UPDATE users SET password_hash = :hash WHERE id = :id"),
                {"hash": password_hash, "id": user_id}
            )

            if result.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Erro ao atualizar senha"
                )

        print(f"[USERS/CHANGE-PASSWORD] ✓ Senha alterada para usuário: {user_name} (por: {current_user['id']} - {current_user['role']})")
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

# ================================================== 
# [FIM] CHANGE PASSWORD
# Data: 02/04/2026 18:25
# ==================================================