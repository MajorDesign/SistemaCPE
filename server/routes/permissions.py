"""
Rotas de Permissões.

Modelo (refatoração 2026-05-05):
    permission_pages          -> catálogo de páginas
    permission_page_role      -> M:N página↔role
    permission_page_group     -> M:N página↔grupo
    user_access_exceptions    -> overrides allow/block por usuário

Endpoints expostos:
    /api/permissions/catalog                   -> GET  (catálogo completo)
    /api/permissions/catalog/{page_key}        -> PUT  (atualizar roles/grupos)
    /api/permissions/check                     -> GET  (lógica canônica)
    /api/permissions/me/menu                   -> GET  (páginas do usuário)
    /api/permissions/exceptions                -> GET/POST/DELETE
    /api/permissions/exceptions/user/{id}      -> GET/DELETE
"""

from fastapi import APIRouter, HTTPException, status
from database import get_db_connection
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/permissions", tags=["Permissions"])


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


# =====================================================================
# CATÁLOGO E CHECAGEM CANÔNICA (modelo relacional)
# =====================================================================

# ---------------------------------------------------------------------
# GET /api/permissions/catalog
#   Retorna o catálogo completo: páginas + roles + grupos liberados.
#   Resposta: { pages: [{page_key, display_name, ..., roles, group_ids}] }
# ---------------------------------------------------------------------
@router.get("/catalog")
async def get_catalog():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT page_key, display_name, description, category, icon,
                   url, ordem, is_active
              FROM permission_pages
             WHERE is_active = 1
             ORDER BY ordem, display_name
        """)
        pages = cursor.fetchall()

        # Roles por página
        cursor.execute("SELECT page_key, role FROM permission_page_role")
        roles_rows = cursor.fetchall()
        roles_map: dict[str, list[str]] = {}
        for r in roles_rows:
            roles_map.setdefault(r["page_key"], []).append(r["role"])

        # Grupos por página
        cursor.execute("SELECT page_key, group_id FROM permission_page_group")
        groups_rows = cursor.fetchall()
        groups_map: dict[str, list[int]] = {}
        for g in groups_rows:
            groups_map.setdefault(g["page_key"], []).append(g["group_id"])

        # Anexa às páginas
        for p in pages:
            p["roles"]     = roles_map.get(p["page_key"], [])
            p["group_ids"] = groups_map.get(p["page_key"], [])

        # Lista de grupos pra UI montar a aba "Por Grupo"
        cursor.execute("""
            SELECT g.id, g.name, g.description, g.department_id,
                   d.name AS department_name
              FROM cpe_grupo g
              LEFT JOIN departments d ON d.id = g.department_id
             ORDER BY d.name, g.name
        """)
        grupos = cursor.fetchall()

        return {
            "pages": pages,
            "groups": grupos,
            "roles": ["USER", "RESPONSAVEL_GRUPO", "TI", "MANAGER", "ADMIN"],
        }

    except Exception as e:
        logger.error(f"[PERM/CATALOG] ❌ {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao carregar catálogo: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ---------------------------------------------------------------------
# PUT /api/permissions/catalog/{page_key}
#   Substitui roles e/ou grupos liberados de uma página.
#   Body: { "roles": ["ADMIN","TI"], "group_ids": [1, 3] }
#
#   Se uma das chaves não vier no body, o lado correspondente NÃO muda.
#   Para "limpar" basta passar lista vazia ([]).
# ---------------------------------------------------------------------
@router.put("/catalog/{page_key}")
async def update_catalog_page(page_key: str, data: dict):
    page_key = (page_key or "").strip().upper()
    if not page_key:
        raise HTTPException(status_code=400, detail="page_key obrigatório")

    roles     = data.get("roles")
    group_ids = data.get("group_ids")

    valid_roles = {"USER", "RESPONSAVEL_GRUPO", "TI", "MANAGER", "ADMIN"}

    if roles is not None:
        if not isinstance(roles, list):
            raise HTTPException(status_code=400, detail="'roles' deve ser lista")
        invalidos = [r for r in roles if r not in valid_roles]
        if invalidos:
            raise HTTPException(status_code=400, detail=f"Roles inválidos: {invalidos}")

    if group_ids is not None:
        if not isinstance(group_ids, list):
            raise HTTPException(status_code=400, detail="'group_ids' deve ser lista")
        if not all(isinstance(g, int) for g in group_ids):
            raise HTTPException(status_code=400, detail="'group_ids' deve conter apenas inteiros")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Página existe?
        cursor.execute("SELECT page_key FROM permission_pages WHERE page_key = %s", (page_key,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Página '{page_key}' não encontrada")

        # Atualiza roles (replace)
        if roles is not None:
            cursor.execute("DELETE FROM permission_page_role WHERE page_key = %s", (page_key,))
            for r in set(roles):
                cursor.execute(
                    "INSERT INTO permission_page_role (page_key, role) VALUES (%s, %s)",
                    (page_key, r),
                )

        # Atualiza grupos (replace)
        if group_ids is not None:
            cursor.execute("DELETE FROM permission_page_group WHERE page_key = %s", (page_key,))
            for gid in set(group_ids):
                # Valida grupo existe (FK protege, mas erro fica mais claro)
                cursor.execute("SELECT 1 FROM cpe_grupo WHERE id = %s", (gid,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=400, detail=f"Grupo {gid} não existe")
                cursor.execute(
                    "INSERT INTO permission_page_group (page_key, group_id) VALUES (%s, %s)",
                    (page_key, gid),
                )

        conn.commit()
        return {"ok": True, "page_key": page_key}

    except HTTPException:
        if conn: conn.rollback()
        raise
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"[PERM/CATALOG/PUT] ❌ {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar página: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ---------------------------------------------------------------------
# GET /api/permissions/check?page=X&user_id=Y
#   Lógica canônica de checagem de acesso.
#   Resposta: { allowed: bool, reason: str }
# ---------------------------------------------------------------------
@router.get("/check")
async def check_access(page: str, user_id: int):
    page = (page or "").strip().upper()
    if not page or not user_id:
        raise HTTPException(status_code=400, detail="page e user_id obrigatórios")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1) Usuário existe e está ativo?
        cursor.execute(
            "SELECT id, role, group_id, is_active FROM users WHERE id = %s",
            (user_id,),
        )
        user = cursor.fetchone()
        if not user or not user["is_active"]:
            return {"allowed": False, "reason": "Usuário inexistente ou inativo"}

        # 2) Página existe e está ativa?
        cursor.execute(
            "SELECT is_active FROM permission_pages WHERE page_key = %s",
            (page,),
        )
        pg = cursor.fetchone()
        if not pg or not pg["is_active"]:
            return {"allowed": False, "reason": "Página desconhecida ou desativada"}

        # 3) ADMIN sempre acessa
        if user["role"] == "ADMIN":
            return {"allowed": True, "reason": "Usuário ADMIN"}

        # 4) Exceção block sempre vence
        cursor.execute("""
            SELECT exception_type FROM user_access_exceptions
             WHERE user_id = %s AND page_name = %s
        """, (user_id, page))
        excs = cursor.fetchall()
        if any(e["exception_type"] == "block" for e in excs):
            return {"allowed": False, "reason": "Bloqueado por exceção individual"}
        if any(e["exception_type"] == "allow" for e in excs):
            return {"allowed": True, "reason": "Liberado por exceção individual"}

        # 5) Role permitido?
        cursor.execute(
            "SELECT 1 FROM permission_page_role WHERE page_key = %s AND role = %s",
            (page, user["role"]),
        )
        if cursor.fetchone():
            return {"allowed": True, "reason": f"Role '{user['role']}' liberado"}

        # 6) Grupo permitido?
        if user["group_id"]:
            cursor.execute(
                "SELECT 1 FROM permission_page_group WHERE page_key = %s AND group_id = %s",
                (page, user["group_id"]),
            )
            if cursor.fetchone():
                return {"allowed": True, "reason": f"Grupo {user['group_id']} liberado"}

        return {"allowed": False, "reason": "Sem permissão por role nem por grupo"}

    except Exception as e:
        logger.error(f"[PERM/CHECK] ❌ {e}")
        raise HTTPException(status_code=500, detail=f"Erro na checagem: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ---------------------------------------------------------------------
# GET /api/permissions/me/menu?user_id=Y
#   Retorna apenas as páginas que o usuário PODE acessar.
#   Útil pra renderizar menu/sidebar sem expor páginas bloqueadas.
# ---------------------------------------------------------------------
@router.get("/me/menu")
async def get_my_menu(user_id: int):
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id obrigatório")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, role, group_id, is_active FROM users WHERE id = %s",
            (user_id,),
        )
        user = cursor.fetchone()
        if not user or not user["is_active"]:
            return {"pages": []}

        cursor.execute("""
            SELECT page_key, display_name, description, category, icon, url, ordem
              FROM permission_pages
             WHERE is_active = 1
             ORDER BY ordem, display_name
        """)
        pages = cursor.fetchall()

        # Bulk fetch das exceções, roles e grupos
        cursor.execute("""
            SELECT page_name, exception_type FROM user_access_exceptions WHERE user_id = %s
        """, (user_id,))
        excs = cursor.fetchall()
        block_set = {e["page_name"] for e in excs if e["exception_type"] == "block"}
        allow_set = {e["page_name"] for e in excs if e["exception_type"] == "allow"}

        cursor.execute("SELECT page_key FROM permission_page_role WHERE role = %s", (user["role"],))
        role_pages = {r["page_key"] for r in cursor.fetchall()}

        group_pages: set[str] = set()
        if user["group_id"]:
            cursor.execute(
                "SELECT page_key FROM permission_page_group WHERE group_id = %s",
                (user["group_id"],),
            )
            group_pages = {r["page_key"] for r in cursor.fetchall()}

        is_admin = (user["role"] == "ADMIN")
        liberadas = []
        for p in pages:
            key = p["page_key"]
            if key in block_set:                          continue
            if is_admin or key in allow_set:              liberadas.append(p); continue
            if key in role_pages or key in group_pages:   liberadas.append(p); continue

        return {"pages": liberadas}

    except Exception as e:
        logger.error(f"[PERM/ME/MENU] ❌ {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao montar menu: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
