"""
Rotas de Permissões: page_permissions e user_access_exceptions
"""

from fastapi import APIRouter, HTTPException, status
from database import get_db_connection
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/permissions", tags=["Permissions"])


# ==================================================
# GET /api/permissions/pages
# Retorna todas as permissões de páginas
# ==================================================

@router.get("/pages")
async def get_page_permissions():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT page_name, allowed_roles FROM page_permissions ORDER BY page_name ASC")
        rows = cursor.fetchall()

        result = {}
        for row in rows:
            roles = [r.strip() for r in row["allowed_roles"].split(",") if r.strip()]
            result[row["page_name"]] = roles

        logger.info(f"[PERMISSIONS/PAGES] ✅ {len(result)} páginas retornadas")
        return {"success": True, "permissions": result}

    except Exception as e:
        logger.error(f"[PERMISSIONS/PAGES] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar permissões: {str(e)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ==================================================
# PUT /api/permissions/pages/{page_name}
# Atualiza roles de uma página (apenas ADMIN)
# ==================================================

@router.put("/pages/{page_name}")
async def update_page_permission(page_name: str, data: dict):
    allowed_roles = data.get("allowed_roles", [])

    if not isinstance(allowed_roles, list) or len(allowed_roles) == 0:
        raise HTTPException(status_code=400, detail="allowed_roles deve ser uma lista com pelo menos um role")

    valid_roles = {"USER", "RESPONSAVEL_GRUPO", "TI", "MANAGER", "ADMIN"}
    invalid = [r for r in allowed_roles if r not in valid_roles]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Roles inválidos: {invalid}")

    roles_str = ",".join(allowed_roles)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE page_permissions SET allowed_roles = %s WHERE page_name = %s",
            (roles_str, page_name)
        )

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Página '{page_name}' não encontrada")

        conn.commit()
        logger.info(f"[PERMISSIONS/PAGES] ✅ '{page_name}' atualizado: {roles_str}")
        return {"success": True, "message": f"Permissões de '{page_name}' atualizadas"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PERMISSIONS/PAGES] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar permissão: {str(e)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ==================================================
# GET /api/permissions/exceptions
# Retorna todas as exceções individuais
# ==================================================

@router.get("/exceptions")
async def get_exceptions():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                e.id,
                e.user_id,
                u.name   AS user_name,
                u.email  AS user_email,
                u.role   AS user_role,
                e.page_name,
                e.exception_type,
                e.reason,
                e.created_by,
                e.created_at
            FROM user_access_exceptions e
            JOIN users u ON u.id = e.user_id
            ORDER BY e.user_id, e.page_name
        """)
        rows = cursor.fetchall()

        for row in rows:
            if row.get("created_at"):
                row["created_at"] = str(row["created_at"])

        logger.info(f"[PERMISSIONS/EXCEPTIONS] ✅ {len(rows)} exceções retornadas")
        return {"success": True, "exceptions": rows}

    except Exception as e:
        logger.error(f"[PERMISSIONS/EXCEPTIONS] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar exceções: {str(e)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ==================================================
# GET /api/permissions/exceptions/user/{user_id}
# Retorna exceções de um usuário específico
# Usado pelo access-config.js para verificar bloqueios
# ==================================================

@router.get("/exceptions/user/{user_id}")
async def get_user_exceptions(user_id: int):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT page_name, exception_type FROM user_access_exceptions WHERE user_id = %s",
            (user_id,)
        )
        rows = cursor.fetchall()

        block_pages = [r["page_name"] for r in rows if r["exception_type"] == "block"]
        allow_pages = [r["page_name"] for r in rows if r["exception_type"] == "allow"]

        return {
            "success": True,
            "user_id": user_id,
            "blockPages": block_pages,
            "allowPages": allow_pages
        }

    except Exception as e:
        logger.error(f"[PERMISSIONS/EXCEPTIONS/USER] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar exceções do usuário: {str(e)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ==================================================
# POST /api/permissions/exceptions
# Cria uma nova exceção individual
# ==================================================

@router.post("/exceptions", status_code=status.HTTP_201_CREATED)
async def create_exception(data: dict):
    user_id    = data.get("user_id")
    page_names = data.get("page_names", [])
    ex_type    = data.get("exception_type")
    reason     = data.get("reason", "")
    created_by = data.get("created_by")

    if not user_id or not page_names or ex_type not in ("block", "allow"):
        raise HTTPException(status_code=400, detail="user_id, page_names e exception_type (block/allow) são obrigatórios")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        inserted = 0
        skipped  = 0
        for page_name in page_names:
            try:
                cursor.execute(
                    """
                    INSERT INTO user_access_exceptions
                        (user_id, page_name, exception_type, reason, created_by)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE reason = VALUES(reason)
                    """,
                    (user_id, page_name, ex_type, reason, created_by)
                )
                inserted += 1
            except Exception:
                skipped += 1

        conn.commit()
        logger.info(f"[PERMISSIONS/EXCEPTIONS] ✅ {inserted} exceção(ões) criada(s) para userId {user_id}")
        return {
            "success": True,
            "message": f"{inserted} exceção(ões) criada(s)",
            "inserted": inserted,
            "skipped": skipped
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PERMISSIONS/EXCEPTIONS] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar exceção: {str(e)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ==================================================
# DELETE /api/permissions/exceptions/{exception_id}
# Remove uma exceção individual
# ==================================================

@router.delete("/exceptions/{exception_id}")
async def delete_exception(exception_id: int):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_access_exceptions WHERE id = %s", (exception_id,))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Exceção não encontrada")

        conn.commit()
        logger.info(f"[PERMISSIONS/EXCEPTIONS] ✅ Exceção #{exception_id} deletada")
        return {"success": True, "message": "Exceção deletada com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PERMISSIONS/EXCEPTIONS] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao deletar exceção: {str(e)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ==================================================
# DELETE /api/permissions/exceptions/user/{user_id}
# Remove TODAS as exceções de um usuário
# ==================================================

@router.delete("/exceptions/user/{user_id}")
async def delete_user_exceptions(user_id: int):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_access_exceptions WHERE user_id = %s", (user_id,))
        deleted = cursor.rowcount
        conn.commit()

        logger.info(f"[PERMISSIONS/EXCEPTIONS] ✅ {deleted} exceção(ões) do userId {user_id} deletada(s)")
        return {"success": True, "message": f"{deleted} exceção(ões) deletada(s)", "deleted": deleted}

    except Exception as e:
        logger.error(f"[PERMISSIONS/EXCEPTIONS] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao deletar exceções: {str(e)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
