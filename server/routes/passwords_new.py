"""
Rotas do novo Cofre de Senhas (Password Vault)
Endpoints: /api/passwords/*
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import text
from database import engine
from security import get_current_user
from utils import normalize_string

router = APIRouter(prefix="/api/passwords", tags=["Passwords"])

# =========================================
# 📋 LIST PASSWORDS
# =========================================

@router.get("/")
async def list_passwords(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Lista todas as senhas do usuário (ou todas se ADMIN)"""
    print(f"[VAULT/LIST] Listando senhas do usuário: {current_user['id']}")
    print(f"[VAULT/LIST] É ADMIN: {current_user.get('is_admin')}")
    
    try:
        with engine.connect() as conn:
            # ✅ NOVO: Se ADMIN, lista TODAS as senhas. Senão, apenas as do usuário
            if current_user.get("is_admin") or current_user.get("role") == "ADMIN":
                print("[VAULT/LIST] ✓ ADMIN - Carregando TODAS as senhas")
                q = text("""
                    SELECT 
                        id, user_id, client, email, description, password,
                        link, observation, group_id, is_public, is_exclusive,
                        allowed_group_id, created_at, updated_at
                    FROM passwords
                    ORDER BY created_at DESC
                """)
                results = conn.execute(q).mappings().all()
            else:
                print(f"[VAULT/LIST] Usuário normal - Carregando senhas do grupo: {current_user.get('group_id')}")
                q = text("""
                    SELECT 
                        id, user_id, client, email, description, password,
                        link, observation, group_id, is_public, is_exclusive,
                        allowed_group_id, created_at, updated_at
                    FROM passwords
                    WHERE user_id = :user_id 
                       OR allowed_group_id = :group_id
                       OR (is_exclusive = 0 AND group_id = :group_id)
                    ORDER BY created_at DESC
                """)
                results = conn.execute(q, {
                    "user_id": current_user["id"],
                    "group_id": current_user.get("group_id")
                }).mappings().all()
            
            passwords = [
                {
                    "id": p["id"],
                    "user_id": p["user_id"],
                    "user_name": get_user_name(conn, p["user_id"]),
                    "client": p["client"],
                    "email": p["email"],
                    "description": p["description"],
                    "password": p["password"],
                    "link": p["link"],
                    "observation": p["observation"],
                    "group_id": p["group_id"],
                    "is_public": p["is_public"],
                    "is_exclusive": p.get("is_exclusive", 0),
                    "allowed_group_id": p.get("allowed_group_id"),
                    "created_at": p["created_at"].isoformat() if p["created_at"] else None,
                    "updated_at": p["updated_at"].isoformat() if p["updated_at"] else None,
                }
                for p in results
            ]
            
            print(f"[VAULT/LIST] ✓ {len(passwords)} senhas carregadas")
            return passwords
            
    except Exception as e:
        print(f"[VAULT/LIST] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


# =========================================
# ➕ CREATE PASSWORD
# =========================================

@router.post("/")
async def create_password(
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Cria uma nova senha"""
    print(f"[VAULT/CREATE] Criando senha para: {current_user['id']}")
    print(f"[VAULT/CREATE] Dados: {data}")
    print(f"[VAULT/CREATE] É ADMIN: {current_user.get('is_admin')}")
    
    try:
        # ✅ Validações
        if not data.get("client") or not data.get("description") or not data.get("password"):
            raise HTTPException(
                status_code=400,
                detail="Cliente, descrição e senha são obrigatórios"
            )
        
        # ✅ NOVO: Validar grupo (EXCETO ADMIN)
        is_admin = current_user.get("is_admin") or current_user.get("role") == "ADMIN"
        group_id = data.get("group_id")
        
        if not is_admin and not current_user.get("group_id"):
            print("[VAULT/CREATE] ✗ Usuário não pertence a nenhum grupo")
            raise HTTPException(
                status_code=403,
                detail="Você não pertence a nenhum grupo!"
            )
        
        # ✅ Se não for ADMIN, usar o grupo do usuário
        if not is_admin:
            group_id = current_user.get("group_id")
        
        # ✅ Verifica se grupo existe (se informado e não for ADMIN)
        if group_id and not is_admin:
            with engine.connect() as conn:
                group_check = conn.execute(
                    text("""
                        SELECT id FROM password_groups 
                        WHERE id = :id AND id IN (
                            SELECT group_id FROM users WHERE id = :user_id
                        )
                    """),
                    {"id": group_id, "user_id": current_user["id"]}
                ).mappings().first()
            
            if not group_check:
                raise HTTPException(
                    status_code=404,
                    detail="Grupo não encontrado ou você não tem permissão"
                )
        
        # ✅ NOVO: Definir allowed_group_id (null para ADMIN, group_id para usuário normal)
        allowed_group_id = None if is_admin else current_user.get("group_id")
        is_exclusive = data.get("is_exclusive", False)
        
        print(f"[VAULT/CREATE] group_id: {group_id}")
        print(f"[VAULT/CREATE] allowed_group_id: {allowed_group_id}")
        print(f"[VAULT/CREATE] is_exclusive: {is_exclusive}")
        
        # ✅ Cria nova senha
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO passwords (
                    user_id, client, email, description, password,
                    link, observation, group_id, is_public, is_exclusive,
                    allowed_group_id
                ) VALUES (
                    :user_id, :client, :email, :description, :password,
                    :link, :observation, :group_id, :is_public, :is_exclusive,
                    :allowed_group_id
                )
            """), {
                "user_id": current_user["id"],
                "client": data.get("client"),
                "email": data.get("email"),
                "description": data.get("description"),
                "password": data.get("password"),
                "link": data.get("link"),
                "observation": data.get("observation"),
                "group_id": group_id,
                "is_public": data.get("is_public", False),
                "is_exclusive": is_exclusive,
                "allowed_group_id": allowed_group_id,
            })
        
        print(f"[VAULT/CREATE] ✓ Senha criada com sucesso")
        return {
            "success": True,
            "message": "Senha salva com sucesso!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[VAULT/CREATE] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


# =========================================
# 🔍 GET PASSWORD
# =========================================

@router.get("/{password_id}")
async def get_password(
    password_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Obtém uma senha específica"""
    print(f"[VAULT/GET] Obtendo senha: {password_id}")
    
    try:
        is_admin = current_user.get("is_admin") or current_user.get("role") == "ADMIN"
        
        with engine.connect() as conn:
            q = text("""
                SELECT 
                    id, user_id, client, email, description, password,
                    link, observation, group_id, is_public, is_exclusive,
                    allowed_group_id, created_at, updated_at
                FROM passwords
                WHERE id = :id
            """)
            result = conn.execute(q, {"id": password_id}).mappings().first()
            
            if not result:
                raise HTTPException(status_code=404, detail="Senha não encontrada")
            
            # ✅ NOVO: Validar permissão
            if not is_admin:
                # Usuário normal só pode ver:
                # 1. Senhas que criou
                # 2. Senhas do seu grupo
                if result["user_id"] != current_user["id"] and result["allowed_group_id"] != current_user.get("group_id"):
                    raise HTTPException(status_code=403, detail="Você não tem permissão para acessar esta senha")
            
            return {
                "id": result["id"],
                "user_id": result["user_id"],
                "client": result["client"],
                "email": result["email"],
                "description": result["description"],
                "password": result["password"],
                "link": result["link"],
                "observation": result["observation"],
                "group_id": result["group_id"],
                "is_public": result["is_public"],
                "is_exclusive": result.get("is_exclusive", 0),
                "allowed_group_id": result.get("allowed_group_id"),
                "created_at": result["created_at"].isoformat() if result["created_at"] else None,
                "updated_at": result["updated_at"].isoformat() if result["updated_at"] else None,
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"[VAULT/GET] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


# =========================================
# ✏️ UPDATE PASSWORD
# =========================================

@router.put("/{password_id}")
async def update_password(
    password_id: int,
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Atualiza uma senha existente"""
    print(f"[VAULT/UPDATE] Atualizando senha: {password_id}")
    
    try:
        is_admin = current_user.get("is_admin") or current_user.get("role") == "ADMIN"
        
        with engine.begin() as conn:
            # ✅ NOVO: Verifica permissão (dono ou ADMIN)
            pwd = conn.execute(
                text("SELECT id, user_id FROM passwords WHERE id = :id"),
                {"id": password_id}
            ).mappings().first()
            
            if not pwd:
                raise HTTPException(status_code=404, detail="Senha não encontrada")
            
            if not is_admin and pwd["user_id"] != current_user["id"]:
                raise HTTPException(status_code=403, detail="Você não pode editar senhas de outros usuários")
            
            # ✅ NOVO: Definir allowed_group_id corretamente
            allowed_group_id = None if is_admin else current_user.get("group_id")
            group_id = data.get("group_id")
            
            if not is_admin:
                group_id = current_user.get("group_id")
            
            # Atualiza
            conn.execute(text("""
                UPDATE passwords SET
                    client = COALESCE(:client, client),
                    email = COALESCE(:email, email),
                    description = COALESCE(:description, description),
                    password = COALESCE(:password, password),
                    link = COALESCE(:link, link),
                    observation = COALESCE(:observation, observation),
                    group_id = COALESCE(:group_id, group_id),
                    is_public = COALESCE(:is_public, is_public),
                    is_exclusive = COALESCE(:is_exclusive, is_exclusive),
                    allowed_group_id = COALESCE(:allowed_group_id, allowed_group_id),
                    updated_at = NOW()
                WHERE id = :id
            """), {
                "client": data.get("client"),
                "email": data.get("email"),
                "description": data.get("description"),
                "password": data.get("password"),
                "link": data.get("link"),
                "observation": data.get("observation"),
                "group_id": group_id,
                "is_public": data.get("is_public"),
                "is_exclusive": data.get("is_exclusive"),
                "allowed_group_id": allowed_group_id,
                "id": password_id,
            })
        
        print(f"[VAULT/UPDATE] ✓ Senha atualizada")
        return {
            "success": True,
            "message": "Senha atualizada com sucesso!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[VAULT/UPDATE] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


# =========================================
# 🗑️ DELETE PASSWORD
# =========================================

@router.delete("/{password_id}")
async def delete_password(
    password_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Deleta uma senha"""
    print(f"[VAULT/DELETE] Deletando senha: {password_id}")
    
    try:
        is_admin = current_user.get("is_admin") or current_user.get("role") == "ADMIN"
        
        with engine.begin() as conn:
            # ✅ NOVO: Verifica permissão (dono ou ADMIN)
            pwd = conn.execute(
                text("SELECT id, user_id FROM passwords WHERE id = :id"),
                {"id": password_id}
            ).mappings().first()
            
            if not pwd:
                raise HTTPException(status_code=404, detail="Senha não encontrada")
            
            if not is_admin and pwd["user_id"] != current_user["id"]:
                raise HTTPException(status_code=403, detail="Você não pode deletar senhas de outros usuários")
            
            result = conn.execute(
                text("DELETE FROM passwords WHERE id = :id"),
                {"id": password_id}
            )
            
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Senha não encontrada")
        
        print(f"[VAULT/DELETE] ✓ Senha deletada")
        return {
            "success": True,
            "message": "Senha deletada com sucesso!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[VAULT/DELETE] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


# =========================================
# 📁 ROTAS: GRUPOS DE SENHAS
# =========================================

@router.get("/groups/list")
async def list_groups(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Lista todos os grupos"""
    print(f"[VAULT/GROUPS/LIST] Listando grupos")
    
    try:
        is_admin = current_user.get("is_admin") or current_user.get("role") == "ADMIN"
        
        with engine.connect() as conn:
            if is_admin:
                # ✅ ADMIN vê TODOS os grupos
                print("[VAULT/GROUPS/LIST] ADMIN - Carregando TODOS os grupos")
                q = text("""
                    SELECT id, name, created_at
                    FROM password_groups
                    ORDER BY name ASC
                """)
                results = conn.execute(q).mappings().all()
            else:
                # ✅ Usuário normal vê seu grupo
                print(f"[VAULT/GROUPS/LIST] Usuário - Carregando grupo do usuário: {current_user.get('group_id')}")
                q = text("""
                    SELECT id, name, created_at
                    FROM password_groups
                    WHERE id = :group_id
                    ORDER BY name ASC
                """)
                results = conn.execute(q, {"group_id": current_user.get("group_id")}).mappings().all()
            
            groups = [
                {
                    "id": g["id"],
                    "name": g["name"],
                    "created_at": g["created_at"].isoformat() if g["created_at"] else None,
                }
                for g in results
            ]
            
            print(f"[VAULT/GROUPS/LIST] ✓ {len(groups)} grupos carregados")
            return groups
            
    except Exception as e:
        print(f"[VAULT/GROUPS/LIST] ✗ Erro: {e}")
        return []


@router.post("/groups/create")
async def create_group(
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Cria um novo grupo de senhas"""
    print(f"[VAULT/GROUPS/CREATE] Criando grupo: {data.get('name')}")
    
    try:
        name = normalize_string(data.get("name", ""))
        
        if not name:
            raise HTTPException(
                status_code=400,
                detail="Nome do grupo é obrigatório"
            )
        
        # ✅ NOVO: Apenas ADMIN pode criar grupos globais
        is_admin = current_user.get("is_admin") or current_user.get("role") == "ADMIN"
        
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO password_groups (name)
                VALUES (:name)
            """), {
                "name": name,
            })
        
        print(f"[VAULT/GROUPS/CREATE] ✓ Grupo criado: {name}")
        return {
            "success": True,
            "message": "Grupo criado com sucesso!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[VAULT/GROUPS/CREATE] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Deleta um grupo de senhas"""
    print(f"[VAULT/GROUPS/DELETE] Deletando grupo: {group_id}")
    
    try:
        is_admin = current_user.get("is_admin") or current_user.get("role") == "ADMIN"
        
        if not is_admin:
            raise HTTPException(status_code=403, detail="Apenas administradores podem deletar grupos")
        
        with engine.begin() as conn:
            # Verifica se existe
            group = conn.execute(
                text("SELECT id FROM password_groups WHERE id = :id"),
                {"id": group_id}
            ).mappings().first()
            
            if not group:
                raise HTTPException(status_code=404, detail="Grupo não encontrado")
            
            # Remove grupo de todas as senhas
            conn.execute(
                text("UPDATE passwords SET group_id = NULL WHERE group_id = :id"),
                {"id": group_id}
            )
            
            # Deleta o grupo
            conn.execute(
                text("DELETE FROM password_groups WHERE id = :id"),
                {"id": group_id}
            )
        
        print(f"[VAULT/GROUPS/DELETE] ✓ Grupo deletado")
        return {
            "success": True,
            "message": "Grupo deletado com sucesso!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[VAULT/GROUPS/DELETE] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


# =========================================
# ✅ FUNÇÕES AUXILIARES
# =========================================

def get_user_name(conn, user_id: int) -> str:
    """Obtém o nome do usuário pelo ID"""
    try:
        result = conn.execute(
            text("SELECT name FROM users WHERE id = :id"),
            {"id": user_id}
        ).mappings().first()
        return result["name"] if result else "Desconhecido"
    except:
        return "Desconhecido"