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
# 🏢 LIST DEPARTMENTS
# =========================================

@router.get("/departments")
async def list_departments():
    """Lista todos os departamentos disponíveis"""
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id, name FROM departments ORDER BY name")
            ).mappings().all()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DEPARTMENTS/LIST] ✗ Erro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar departamentos: {str(e)}"
        )


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
                    FROM `cpe_grupo`
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
                    FROM `cpe_grupo`
                    WHERE id = :id
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
        department_id = data.get("department_id")

        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nome do grupo obrigatório"
            )
        if not department_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Departamento obrigatório"
            )

        # Verifica se já existe
        with engine.connect() as conn:
            existing = conn.execute(
                text("SELECT id FROM `cpe_grupo` WHERE name = :name AND department_id = :dept_id LIMIT 1"),
                {"name": name, "dept_id": department_id}
            ).mappings().first()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Grupo com este nome já existe neste departamento"
                )

        # Cria novo grupo
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO `cpe_grupo` (department_id, name, description, is_active)
                    VALUES (:department_id, :name, :description, 1)
                """),
                {
                    "department_id": department_id,
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
                text(f"UPDATE `cpe_grupo` SET {set_clause}, updated_at = NOW() WHERE id = :id"),
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
    """Deleta um grupo (apenas ADMIN).

    Comportamento:
      - Users que estao no grupo: group_id vira NULL (nao bloqueia).
      - permission_page_group: apagado em cascata (grants triviais).
      - Se tem contratos/pre-cadastros/tickets/passwords/categorias
        vinculados: RETORNA 409 com a lista das dependencias.
        User precisa remanejar antes.

    Rationale: pastas de contrato, pre-cadastros, tickets historicos
    e senhas do cofre representam dados de negocio — deletar cegamente
    seria destrutivo. Melhor forcar o ADMIN a decidir manualmente.
    """
    print(f"[GROUPS/DELETE] Deletando grupo: {group_id}")

    try:
        if current_user["role"] != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas ADMINs podem deletar grupos"
            )

        with engine.begin() as conn:
            group = conn.execute(
                text("SELECT id, name FROM `cpe_grupo` WHERE id = :id LIMIT 1"),
                {"id": group_id}
            ).mappings().first()

            if not group:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Grupo não encontrado"
                )

            # Checa dependencias que BLOQUEIAM o delete.
            # Cada tupla: (label_amigavel_singular, plural, SQL de count)
            # SQL usa :id (bound via dict) — NADA de string concat.
            checks = [
                ("pasta de contratos",     "pastas de contratos",
                 "SELECT COUNT(*) AS n FROM contrato_pastas WHERE group_id = :id"),
                ("pré-cadastro pendente",  "pré-cadastros pendentes",
                 "SELECT COUNT(*) AS n FROM pre_cadastro_pendentes WHERE group_id = :id"),
                ("ticket",                 "tickets",
                 "SELECT COUNT(*) AS n FROM tickets WHERE group_id = :id"),
                ("senha no cofre",         "senhas no cofre",
                 "SELECT COUNT(*) AS n FROM passwords WHERE group_id = :id"),
                ("categoria",              "categorias",
                 "SELECT COUNT(*) AS n FROM categorias WHERE group_id = :id"),
            ]
            blocks = []
            for singular, plural, sql in checks:
                n = conn.execute(text(sql), {"id": group_id}).scalar() or 0
                if n:
                    blocks.append({
                        "quantidade": int(n),
                        "descricao":  singular if n == 1 else plural,
                    })

            if blocks:
                partes = [f"{b['quantidade']} {b['descricao']}" for b in blocks]
                msg = (f"Não é possível excluir o grupo '{group['name']}' — ainda tem "
                       + " e ".join([", ".join(partes[:-1]), partes[-1]]) if len(partes) > 1
                       else f"Não é possível excluir o grupo '{group['name']}' — ainda tem {partes[0]}")
                msg += ". Remaneje antes de excluir."
                # Log detalhado pra rastreabilidade
                print(f"[GROUPS/DELETE] BLOQUEADO grupo={group_id}: {blocks}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": msg,
                        "dependencias": blocks,
                    }
                )

            # Depedencias removiveis triviais: users desvincula, grants apaga
            conn.execute(
                text("UPDATE users SET group_id = NULL WHERE group_id = :id"),
                {"id": group_id}
            )
            conn.execute(
                text("DELETE FROM permission_page_group WHERE group_id = :id"),
                {"id": group_id}
            )
            # Delete final (BUG anterior: :id sem bind — corrigido)
            conn.execute(
                text("DELETE FROM `cpe_grupo` WHERE id = :id"),
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