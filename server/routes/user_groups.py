"""
Multi-grupo por usuario (Fase 1 do PLANO_MULTIGRUPO.md).

Autorizacao:
- LEITURA (GET): ADMIN, TI, o proprio user, ou RESPONSAVEL_GRUPO
  quando consultando membros do proprio grupo.
- ESCRITA (POST/PATCH/DELETE): APENAS ADMIN global (admin master).
  Nem TI, nem RESPONSAVEL_GRUPO podem alterar composicao de grupos.

Invariantes garantidas:
- Todo user tem exatamente 1 grupo com is_primary=1.
- users.group_id espelha o grupo primario (sincronizado a cada
  mudanca de primary).
- Nao e possivel remover o unico grupo do user (erro 400).
"""

from typing import Any, Dict

from database import engine
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from security import get_current_user
from sqlalchemy import text

router = APIRouter(prefix="/api/user-groups", tags=["UserGroups"])


# =========================================
# Guards
# =========================================

def _require_admin(current_user: Dict[str, Any]) -> None:
    """So role global ADMIN pode escrever. Ninguem mais."""
    role = (current_user.get("role") or "").upper()
    if role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas ADMIN pode gerenciar grupos de usuarios.",
        )


def _can_read_user_groups(current_user: Dict[str, Any], target_user_id: int) -> bool:
    """Le grupos de outro user: ADMIN ou TI. Ou o proprio user."""
    role = (current_user.get("role") or "").upper()
    if role in ("ADMIN", "TI"):
        return True
    return int(current_user.get("id") or 0) == int(target_user_id)


# =========================================
# Schemas
# =========================================

class AddUserGroupBody(BaseModel):
    group_id: int
    role_in_grp: str = Field(default="USER", pattern="^(USER|RESPONSAVEL_GRUPO)$")
    is_primary: bool = False


class UpdateUserGroupBody(BaseModel):
    role_in_grp: str | None = Field(default=None, pattern="^(USER|RESPONSAVEL_GRUPO)$")
    is_primary: bool | None = None


# =========================================
# Helpers
# =========================================

def _sync_users_group_id(conn, user_id: int) -> None:
    """Sincroniza users.group_id com o grupo primario do user."""
    row = conn.execute(text("""
        SELECT group_id FROM user_groups
         WHERE user_id = :uid AND is_primary = 1
         LIMIT 1
    """), {"uid": user_id}).mappings().first()
    if row:
        conn.execute(text("UPDATE users SET group_id = :gid WHERE id = :uid"),
                     {"gid": row["group_id"], "uid": user_id})


def _set_primary(conn, user_id: int, new_primary_group_id: int) -> None:
    """
    Marca (user_id, new_primary_group_id) como is_primary=1 e desmarca
    o antigo. UNIQUE(user_id, is_primary) exige que a limpeza venha ANTES
    do set.
    """
    conn.execute(text("""
        UPDATE user_groups SET is_primary = NULL
         WHERE user_id = :uid AND is_primary = 1
    """), {"uid": user_id})
    conn.execute(text("""
        UPDATE user_groups SET is_primary = 1
         WHERE user_id = :uid AND group_id = :gid
    """), {"uid": user_id, "gid": new_primary_group_id})


# =========================================
# GET /api/user-groups/{user_id} — lista grupos do user
# =========================================

@router.get("/all")
async def list_all_user_groups(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Endpoint agregado (para populacao rapida de tabelas): retorna
    {user_id: [grupos]} de TODOS os usuarios. So ADMIN/TI podem ler.
    """
    role = (current_user.get("role") or "").upper()
    if role not in ("ADMIN", "TI"):
        raise HTTPException(status_code=403, detail="Apenas ADMIN/TI podem ler o agregado.")

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT ug.user_id, ug.group_id, g.name AS group_name,
                   ug.role_in_grp,
                   (ug.is_primary = 1) AS is_primary
              FROM user_groups ug
              JOIN cpe_grupo g ON g.id = ug.group_id
             ORDER BY ug.user_id, is_primary DESC, g.name ASC
        """)).mappings().all()

    by_user = {}
    for r in rows:
        d = dict(r)
        by_user.setdefault(d["user_id"], []).append(d)
    return {"items": by_user}


@router.get("/{user_id}")
async def list_user_groups(user_id: int,
                            current_user: Dict[str, Any] = Depends(get_current_user)):
    if not _can_read_user_groups(current_user, user_id):
        raise HTTPException(status_code=403, detail="Sem permissao para ver os grupos deste usuario.")

    with engine.connect() as conn:
        # user existe?
        u = conn.execute(text("SELECT id, name, role FROM users WHERE id = :id"),
                         {"id": user_id}).mappings().first()
        if not u:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado.")

        rows = conn.execute(text("""
            SELECT ug.group_id,
                   g.name        AS group_name,
                   d.name        AS department_name,
                   ug.role_in_grp,
                   (ug.is_primary = 1) AS is_primary,
                   ug.added_at,
                   ug.added_by,
                   ab.name AS added_by_name
              FROM user_groups ug
              JOIN cpe_grupo   g  ON g.id  = ug.group_id
              LEFT JOIN departments d  ON d.id  = g.department_id
              LEFT JOIN users       ab ON ab.id = ug.added_by
             WHERE ug.user_id = :uid
             ORDER BY is_primary DESC, g.name ASC
        """), {"uid": user_id}).mappings().all()

    return {
        "user_id":     u["id"],
        "user_name":   u["name"],
        "role_global": u["role"],
        "groups": [dict(r) for r in rows],
    }


# =========================================
# GET /api/user-groups/by-group/{group_id} — lista membros
# =========================================

@router.get("/by-group/{group_id}")
async def list_group_members(group_id: int,
                              current_user: Dict[str, Any] = Depends(get_current_user)):
    role = (current_user.get("role") or "").upper()
    if role not in ("ADMIN", "TI"):
        # RESPONSAVEL_GRUPO so ve membros do proprio grupo.
        # (usa users.group_id como grupo primario; se ele nao e responsavel
        # nem membro do grupo, nega.)
        with engine.connect() as conn:
            r = conn.execute(text("""
                SELECT 1 FROM user_groups
                 WHERE user_id = :uid AND group_id = :gid
                 LIMIT 1
            """), {"uid": current_user["id"], "gid": group_id}).first()
        if not r:
            raise HTTPException(status_code=403, detail="Sem permissao para ver membros deste grupo.")

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT u.id, u.name, u.email, u.role AS role_global,
                   ug.role_in_grp,
                   (ug.is_primary = 1) AS is_primary,
                   u.is_active
              FROM user_groups ug
              JOIN users u ON u.id = ug.user_id
             WHERE ug.group_id = :gid
             ORDER BY u.name ASC
        """), {"gid": group_id}).mappings().all()

    return {"group_id": group_id, "members": [dict(r) for r in rows]}


# =========================================
# POST /api/user-groups/{user_id} — adiciona grupo (ADMIN only)
# =========================================

@router.post("/{user_id}", status_code=201)
async def add_user_group(user_id: int, body: AddUserGroupBody,
                          current_user: Dict[str, Any] = Depends(get_current_user)):
    _require_admin(current_user)

    with engine.begin() as conn:
        # validacoes
        u = conn.execute(text("SELECT id FROM users WHERE id = :id"),
                         {"id": user_id}).first()
        if not u:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado.")

        g = conn.execute(text("SELECT id FROM cpe_grupo WHERE id = :id"),
                         {"id": body.group_id}).first()
        if not g:
            raise HTTPException(status_code=404, detail="Grupo nao encontrado.")

        exists = conn.execute(text("""
            SELECT 1 FROM user_groups WHERE user_id = :uid AND group_id = :gid
        """), {"uid": user_id, "gid": body.group_id}).first()
        if exists:
            raise HTTPException(status_code=409, detail="Usuario ja participa deste grupo.")

        # Auto-primary: se user nao tinha nenhum grupo, este vira primary
        has_any = conn.execute(text("""
            SELECT 1 FROM user_groups WHERE user_id = :uid LIMIT 1
        """), {"uid": user_id}).first()
        will_be_primary = body.is_primary or not has_any

        # Se este vai ser primary E ja existe outro primary, precisa
        # desmarcar o antigo ANTES do INSERT (UNIQUE(user_id, is_primary=1))
        if will_be_primary:
            conn.execute(text("""
                UPDATE user_groups SET is_primary = NULL
                 WHERE user_id = :uid AND is_primary = 1
            """), {"uid": user_id})

        conn.execute(text("""
            INSERT INTO user_groups (user_id, group_id, role_in_grp, is_primary, added_by)
            VALUES (:uid, :gid, :role, :is_primary, :added_by)
        """), {
            "uid": user_id,
            "gid": body.group_id,
            "role": body.role_in_grp,
            "is_primary": 1 if will_be_primary else None,
            "added_by": current_user["id"],
        })

        _sync_users_group_id(conn, user_id)

    return {"success": True, "message": "Grupo adicionado."}


# =========================================
# PATCH /api/user-groups/{user_id}/{group_id} — muda role/primary
# =========================================

@router.patch("/{user_id}/{group_id}")
async def update_user_group(user_id: int, group_id: int, body: UpdateUserGroupBody,
                             current_user: Dict[str, Any] = Depends(get_current_user)):
    _require_admin(current_user)

    if body.role_in_grp is None and body.is_primary is None:
        raise HTTPException(status_code=400, detail="Nada a atualizar.")

    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT is_primary FROM user_groups WHERE user_id = :uid AND group_id = :gid
        """), {"uid": user_id, "gid": group_id}).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario nao esta neste grupo.")

        if body.role_in_grp is not None:
            conn.execute(text("""
                UPDATE user_groups SET role_in_grp = :role
                 WHERE user_id = :uid AND group_id = :gid
            """), {"role": body.role_in_grp, "uid": user_id, "gid": group_id})

        if body.is_primary is True and not row["is_primary"]:
            _set_primary(conn, user_id, group_id)
        elif body.is_primary is False and row["is_primary"]:
            raise HTTPException(status_code=400,
                                detail="Nao e possivel desmarcar o primario. Marque outro grupo como primario.")

        _sync_users_group_id(conn, user_id)

    return {"success": True, "message": "Atualizado."}


# =========================================
# DELETE /api/user-groups/{user_id}/{group_id}
# =========================================

@router.delete("/{user_id}/{group_id}")
async def remove_user_group(user_id: int, group_id: int,
                             current_user: Dict[str, Any] = Depends(get_current_user)):
    _require_admin(current_user)

    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT is_primary FROM user_groups WHERE user_id = :uid AND group_id = :gid
        """), {"uid": user_id, "gid": group_id}).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario nao esta neste grupo.")

        total = conn.execute(text("""
            SELECT COUNT(*) AS n FROM user_groups WHERE user_id = :uid
        """), {"uid": user_id}).mappings().first()["n"]
        if total <= 1:
            raise HTTPException(status_code=400,
                                detail="Todo usuario precisa estar em pelo menos 1 grupo.")

        was_primary = bool(row["is_primary"])

        conn.execute(text("""
            DELETE FROM user_groups WHERE user_id = :uid AND group_id = :gid
        """), {"uid": user_id, "gid": group_id})

        if was_primary:
            # promove o proximo (ordem: adicao mais antiga)
            nxt = conn.execute(text("""
                SELECT group_id FROM user_groups
                 WHERE user_id = :uid
                 ORDER BY added_at ASC
                 LIMIT 1
            """), {"uid": user_id}).mappings().first()
            if nxt:
                _set_primary(conn, user_id, nxt["group_id"])

        _sync_users_group_id(conn, user_id)

    return {"success": True, "message": "Grupo removido."}
