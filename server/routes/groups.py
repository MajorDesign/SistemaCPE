"""
Rotas de grupos: CRUD
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import text
from database import engine
from security import get_current_user
from utils import normalize_string

router = APIRouter(prefix="/api/groups", tags=["Groups"])

# =========================================
# 👥 LIST GROUPS
# =========================================

@router.get("/")
async def list_groups(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Lista todos os grupos"""
    print(f"[GROUPS/LIST] Listando grupos (solicitado por: {current_user['id']})")
    
    try:
        with engine.connect() as conn:
            groups_result = conn.execute(
                text("""
                    SELECT id, name, description, is_active, created_at
                    FROM groups
                    ORDER BY name ASC
                """)
            ).mappings().all()

        groups = [dict(g) for g in groups_result]

        print(f"[GROUPS/LIST] ✓ {len(groups)} grupos listados")
        return {
            "success": True,
            "total": len(groups),
            "groups": groups
        }

    except Exception as e:
        print(f"[GROUPS/LIST] ✗ Erro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro: {str(e)}"
        )


# =========================================
# 📋 GET GROUP BY ID
# =========================================

@router.get("/{group_id}")
async def get_group(
    group_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Obtém dados de um grupo"""
    print(f"[GROUPS/GET] Obtendo grupo: {group_id}")
    
    try:
        with engine.connect() as conn:
            group_result = conn.execute(
                text("""
                    SELECT id, name, description, is_active, created_at, updated_at
                    FROM groups
                    WHERE id = :id
                    LIMIT 1
                """),
                {"id": group_id}
            ).mappings().first()

        if not group_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Grupo não encontrado"
            )

        group = dict(group_result)

        print(f"[GROUPS/GET] ✓ Grupo obtido: {group['name']}")
        return {
            "success": True,
            "group": group
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[GROUPS/GET] ✗ Erro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro: {str(e)}"
        )


# =========================================
# ➕ CREATE GROUP
# =========================================

@router.post("/")
async def create_group(
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Cria um novo grupo (apenas ADMIN)"""
    print(f"[GROUPS/CREATE] Criando novo grupo...")
    
    try:
        # Verifica permissão
        if current_user["role"] != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas ADMINs podem criar grupos"
            )

        name = normalize_string(data.get("name", ""))
        description = normalize_string(data.get("description", ""))

        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nome do grupo obrigatório"
            )

        # Verifica se já existe
        with engine.connect() as conn:
            existing = conn.execute(
                text("SELECT id FROM groups WHERE name = :name LIMIT 1"),
                {"name": name}
            ).mappings().first()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Grupo com este nome já existe"
                )

        # Cria novo grupo
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO groups (name, description, is_active)
                    VALUES (:name, :description, 1)
                """),
                {
                    "name": name,
                    "description": description or None,
                }
            )

        print(f"[GROUPS/CREATE] ✓ Grupo criado: {name}")
        return {
            "success": True,
            "message": "Grupo criado com sucesso!"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[GROUPS/CREATE] ✗ Erro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro: {str(e)}"
        )


# =========================================
# ✏️ UPDATE GROUP
# =========================================

@router.put("/{group_id}")
async def update_group(
    group_id: int,
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Atualiza um grupo (apenas ADMIN)"""
    print(f"[GROUPS/UPDATE] Atualizando grupo: {group_id}")
    
    try:
        # Verifica permissão
        if current_user["role"] != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas ADMINs podem atualizar grupos"
            )

        updates = {}

        if "name" in data:
            name = normalize_string(data["name"])
            if not name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nome não pode estar vazio"
                )
            updates["name"] = name

        if "description" in data:
            updates["description"] = normalize_string(data["description"]) or None

        if "is_active" in data:
            updates["is_active"] = 1 if data["is_active"] else 0

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum campo para atualizar"
            )

        # Constrói SQL dinamicamente
        set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
        updates["id"] = group_id

        with engine.begin() as conn:
            result = conn.execute(
                text(f"UPDATE groups SET {set_clause}, updated_at = NOW() WHERE id = :id"),
                updates
            )

            if result.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Grupo não encontrado"
                )

        print(f"[GROUPS/UPDATE] ✓ Grupo atualizado: {group_id}")
        return {
            "success": True,
            "message": "Grupo atualizado com sucesso"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[GROUPS/UPDATE] ✗ Erro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro: {str(e)}"
        )


# =========================================
# 🗑️ DELETE GROUP
# =========================================

@router.delete("/{group_id}")
async def delete_group(
    group_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Deleta um grupo (apenas ADMIN)"""
    print(f"[GROUPS/DELETE] Deletando grupo: {group_id}")
    
    try:
        # Verifica permissão
        if current_user["role"] != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas ADMINs podem deletar grupos"
            )

        with engine.begin() as conn:
            # Verifica se existe
            group = conn.execute(
                text("SELECT id FROM groups WHERE id = :id LIMIT 1"),
                {"id": group_id}
            ).mappings().first()

            if not group:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Grupo não encontrado"
                )

            # Remove usuários do grupo
            conn.execute(
                text("UPDATE users SET group_id = NULL WHERE group_id = :id"),
                {"id": group_id}
            )

            # Deleta o grupo
            conn.execute(
                text("DELETE FROM groups WHERE id = :id"),
                {"id": group_id}
            )

        print(f"[GROUPS/DELETE] ✓ Grupo deletado: {group_id}")
        return {
            "success": True,
            "message": "Grupo deletado com sucesso"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[GROUPS/DELETE] ✗ Erro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro: {str(e)}"
        )