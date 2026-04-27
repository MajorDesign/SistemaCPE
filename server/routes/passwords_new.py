"""
Rotas do Cofre de Senhas (Password Vault)
Endpoints: /api/passwords/*

Tabelas utilizadas:
  - cofre_senhas (colunas prefixadas cofre_*) — senhas armazenadas
  - cpe_grupo    (grupos do sistema)          — referenciado por cofre_user_id/grupo

IMPORTANTE: todos os endpoints são def (sync), não async def.
SQLAlchemy síncrono não pode ser chamado de dentro de async def no FastAPI
(causa MissingGreenlet em SQLAlchemy 2.x). Usando def, o FastAPI executa
automaticamente em thread pool, resolvendo o problema.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import text
import bcrypt as _bcrypt
from database import engine
from security import get_current_user

router = APIRouter(prefix="/api/passwords", tags=["Passwords"])


# =========================================
# LIST PASSWORDS
# =========================================

@router.get("/")
def list_passwords(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Lista as senhas visíveis ao usuário (ou todas se ADMIN)."""
    print(f"[VAULT/LIST] Listando senhas do usuário: {current_user['id']}")

    try:
        is_admin = current_user.get("is_admin") or current_user.get("role") == "ADMIN"

        base_select = """
            SELECT
                id,
                cofre_user_id          AS user_id,
                cofre_client           AS client,
                cofre_email            AS email,
                cofre_description      AS description,
                cofre_password         AS password,
                cofre_link             AS link,
                cofre_observation      AS observation,
                cofre_group_id         AS group_id,
                cofre_is_public        AS is_public,
                cofre_is_exclusive     AS is_exclusive,
                cofre_allowed_group_id AS allowed_group_id,
                cofre_created_at       AS created_at,
                cofre_updated_at       AS updated_at
            FROM cofre_senhas
        """

        with engine.connect() as conn:
            if is_admin:
                print("[VAULT/LIST] ADMIN - Carregando TODAS as senhas")
                results = conn.execute(
                    text(base_select + " ORDER BY cofre_created_at DESC")
                ).mappings().all()
            else:
                print(f"[VAULT/LIST] Usuário - grupo: {current_user.get('group_id')}")
                q = text(base_select + """
                    WHERE cofre_user_id = :user_id
                       OR cofre_allowed_group_id = :group_id
                       OR (cofre_is_exclusive = 0 AND cofre_group_id = :group_id)
                    ORDER BY cofre_created_at DESC
                """)
                results = conn.execute(q, {
                    "user_id": current_user["id"],
                    "group_id": current_user.get("group_id"),
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
                    "is_public": bool(p["is_public"]),
                    "is_exclusive": bool(p["is_exclusive"]) if p["is_exclusive"] else False,
                    "allowed_group_id": p["allowed_group_id"],
                    "created_at": p["created_at"].isoformat() if p["created_at"] else None,
                    "updated_at": p["updated_at"].isoformat() if p["updated_at"] else None,
                }
                for p in results
            ]

            print(f"[VAULT/LIST] ✓ {len(passwords)} senhas carregadas")
            return passwords

    except Exception as e:
        print(f"[VAULT/LIST] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar senhas: {str(e)}")


# =========================================
# CREATE PASSWORD
# =========================================

@router.post("/")
def create_password(
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Cria uma nova senha."""
    print(f"[VAULT/CREATE] Criando senha para: {current_user['id']}")

    try:
        if not data.get("client") or not data.get("description") or not data.get("password"):
            raise HTTPException(
                status_code=400,
                detail="Cliente, descrição e senha são obrigatórios"
            )

        is_admin = current_user.get("is_admin") or current_user.get("role") == "ADMIN"
        group_id = data.get("group_id")

        if not is_admin and not current_user.get("group_id"):
            raise HTTPException(
                status_code=403,
                detail="Você não pertence a nenhum grupo!"
            )

        if not is_admin:
            group_id = current_user.get("group_id")

        if group_id and not is_admin:
            with engine.connect() as conn:
                group_check = conn.execute(
                    text("""
                        SELECT id FROM cpe_grupo
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

        allowed_group_id = None if is_admin else current_user.get("group_id")
        is_exclusive = bool(data.get("is_exclusive", False))
        is_public = bool(data.get("is_public", False))

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO cofre_senhas (
                    cofre_user_id, cofre_client, cofre_email, cofre_description,
                    cofre_password, cofre_link, cofre_observation, cofre_group_id,
                    cofre_is_public, cofre_is_exclusive, cofre_allowed_group_id
                ) VALUES (
                    :user_id, :client, :email, :description,
                    :password, :link, :observation, :group_id,
                    :is_public, :is_exclusive, :allowed_group_id
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
                "is_public": is_public,
                "is_exclusive": is_exclusive,
                "allowed_group_id": allowed_group_id,
            })

        print("[VAULT/CREATE] ✓ Senha criada")
        return {"success": True, "message": "Senha salva com sucesso!"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[VAULT/CREATE] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar senha: {str(e)}")


# =========================================
# GET PASSWORD
# =========================================

@router.get("/{password_id}")
def get_password(
    password_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Obtém uma senha específica."""
    print(f"[VAULT/GET] Obtendo senha: {password_id}")

    try:
        is_admin = current_user.get("is_admin") or current_user.get("role") == "ADMIN"

        with engine.connect() as conn:
            q = text("""
                SELECT
                    id,
                    cofre_user_id          AS user_id,
                    cofre_client           AS client,
                    cofre_email            AS email,
                    cofre_description      AS description,
                    cofre_password         AS password,
                    cofre_link             AS link,
                    cofre_observation      AS observation,
                    cofre_group_id         AS group_id,
                    cofre_is_public        AS is_public,
                    cofre_is_exclusive     AS is_exclusive,
                    cofre_allowed_group_id AS allowed_group_id,
                    cofre_created_at       AS created_at,
                    cofre_updated_at       AS updated_at
                FROM cofre_senhas
                WHERE id = :id
            """)
            result = conn.execute(q, {"id": password_id}).mappings().first()

            if not result:
                raise HTTPException(status_code=404, detail="Senha não encontrada")

            if not is_admin:
                if (result["user_id"] != current_user["id"]
                        and result["allowed_group_id"] != current_user.get("group_id")):
                    raise HTTPException(
                        status_code=403,
                        detail="Você não tem permissão para acessar esta senha"
                    )

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
                "is_public": bool(result["is_public"]),
                "is_exclusive": bool(result["is_exclusive"]) if result["is_exclusive"] else False,
                "allowed_group_id": result["allowed_group_id"],
                "created_at": result["created_at"].isoformat() if result["created_at"] else None,
                "updated_at": result["updated_at"].isoformat() if result["updated_at"] else None,
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[VAULT/GET] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


# =========================================
# UPDATE PASSWORD
# =========================================

@router.put("/{password_id}")
def update_password(
    password_id: int,
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Atualiza uma senha existente."""
    print(f"[VAULT/UPDATE] Atualizando senha: {password_id}")

    try:
        is_admin = current_user.get("is_admin") or current_user.get("role") == "ADMIN"

        with engine.begin() as conn:
            pwd = conn.execute(
                text("SELECT id, cofre_user_id AS user_id FROM cofre_senhas WHERE id = :id"),
                {"id": password_id}
            ).mappings().first()

            if not pwd:
                raise HTTPException(status_code=404, detail="Senha não encontrada")

            if not is_admin and pwd["user_id"] != current_user["id"]:
                raise HTTPException(
                    status_code=403,
                    detail="Você não pode editar senhas de outros usuários"
                )

            allowed_group_id = None if is_admin else current_user.get("group_id")
            group_id = data.get("group_id")
            if not is_admin:
                group_id = current_user.get("group_id")

            conn.execute(text("""
                UPDATE cofre_senhas SET
                    cofre_client           = COALESCE(:client, cofre_client),
                    cofre_email            = COALESCE(:email, cofre_email),
                    cofre_description      = COALESCE(:description, cofre_description),
                    cofre_password         = COALESCE(:password, cofre_password),
                    cofre_link             = COALESCE(:link, cofre_link),
                    cofre_observation      = COALESCE(:observation, cofre_observation),
                    cofre_group_id         = COALESCE(:group_id, cofre_group_id),
                    cofre_is_public        = COALESCE(:is_public, cofre_is_public),
                    cofre_is_exclusive     = COALESCE(:is_exclusive, cofre_is_exclusive),
                    cofre_allowed_group_id = COALESCE(:allowed_group_id, cofre_allowed_group_id),
                    cofre_updated_at       = NOW()
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

        print("[VAULT/UPDATE] ✓ Senha atualizada")
        return {"success": True, "message": "Senha atualizada com sucesso!"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[VAULT/UPDATE] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


# =========================================
# DELETE PASSWORD
# =========================================

@router.delete("/{password_id}")
def delete_password(
    password_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Deleta uma senha."""
    print(f"[VAULT/DELETE] Deletando senha: {password_id}")

    try:
        is_admin = current_user.get("is_admin") or current_user.get("role") == "ADMIN"

        with engine.begin() as conn:
            pwd = conn.execute(
                text("SELECT id, cofre_user_id AS user_id FROM cofre_senhas WHERE id = :id"),
                {"id": password_id}
            ).mappings().first()

            if not pwd:
                raise HTTPException(status_code=404, detail="Senha não encontrada")

            if not is_admin and pwd["user_id"] != current_user["id"]:
                raise HTTPException(
                    status_code=403,
                    detail="Você não pode deletar senhas de outros usuários"
                )

            result = conn.execute(
                text("DELETE FROM cofre_senhas WHERE id = :id"),
                {"id": password_id}
            )

            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Senha não encontrada")

        print("[VAULT/DELETE] ✓ Senha deletada")
        return {"success": True, "message": "Senha deletada com sucesso!"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[VAULT/DELETE] ✗ Erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


# =========================================
# GRUPOS VISIVEIS AO COFRE
# =========================================

@router.get("/groups/list")
def list_groups(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Lista grupos do sistema visíveis ao usuário para vinculação de senhas."""
    print("[VAULT/GROUPS/LIST] Listando grupos")

    try:
        is_admin = current_user.get("is_admin") or current_user.get("role") == "ADMIN"

        with engine.connect() as conn:
            if is_admin:
                q = text("""
                    SELECT id, name, created_at
                      FROM cpe_grupo
                     ORDER BY name ASC
                """)
                results = conn.execute(q).mappings().all()
            else:
                user_group_id = current_user.get("group_id")
                if not user_group_id:
                    return []
                q = text("""
                    SELECT id, name, created_at
                      FROM cpe_grupo
                     WHERE id = :group_id
                """)
                results = conn.execute(q, {"group_id": user_group_id}).mappings().all()

            groups = [
                {
                    "id": g["id"],
                    "name": g["name"],
                    "created_at": g["created_at"].isoformat() if g["created_at"] else None,
                }
                for g in results
            ]

            print(f"[VAULT/GROUPS/LIST] ✓ {len(groups)} grupos")
            return groups

    except Exception as e:
        print(f"[VAULT/GROUPS/LIST] ✗ Erro: {e}")
        return []


# =========================================
# VAULT PIN
# =========================================

@router.get("/vault-pin/status")
def vault_pin_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Verifica se o usuário tem vault PIN configurado."""
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT vault_pin_hash FROM users WHERE id = :id"),
                {"id": current_user["id"]}
            ).mappings().first()
        has_pin = bool(row and row["vault_pin_hash"])
        return {"has_pin": has_pin}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vault-pin/set")
def vault_pin_set(data: dict, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Define ou altera o vault PIN do usuário."""
    try:
        pin = (data.get("pin") or "").strip()
        if len(pin) < 4:
            raise HTTPException(status_code=400, detail="O PIN deve ter no mínimo 4 caracteres")

        pin_hash = _bcrypt.hashpw(pin.encode(), _bcrypt.gensalt()).decode()

        with engine.begin() as conn:
            conn.execute(
                text("UPDATE users SET vault_pin_hash = :hash WHERE id = :id"),
                {"hash": pin_hash, "id": current_user["id"]}
            )
        print(f"[VAULT/PIN] PIN configurado para user_id={current_user['id']}")
        return {"ok": True, "message": "PIN do cofre configurado com sucesso!"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vault-pin/verify")
def vault_pin_verify(data: dict, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Verifica o vault PIN do usuário. Retorna ok=True se correto."""
    try:
        pin = (data.get("pin") or "").strip()

        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT vault_pin_hash FROM users WHERE id = :id"),
                {"id": current_user["id"]}
            ).mappings().first()

        if not row or not row["vault_pin_hash"]:
            raise HTTPException(status_code=400, detail="PIN não configurado")

        ok = _bcrypt.checkpw(pin.encode(), row["vault_pin_hash"].encode())
        if not ok:
            raise HTTPException(status_code=403, detail="PIN incorreto")

        print(f"[VAULT/PIN] Verificação OK para user_id={current_user['id']}")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vault-pin/reset")
def vault_pin_reset(data: dict, current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    ADMIN ONLY: Reseta o vault PIN de um usuário.
    Remove o hash, forçando o usuário a cadastrar novo PIN no próximo acesso.
    """
    try:
        is_admin = current_user.get("role") == "ADMIN"
        if not is_admin:
            raise HTTPException(status_code=403, detail="Apenas administradores podem resetar PINs")

        target_user_id = data.get("user_id")
        if not target_user_id:
            raise HTTPException(status_code=400, detail="user_id obrigatório")

        with engine.begin() as conn:
            # Verifica se o usuário existe
            user_row = conn.execute(
                text("SELECT id, name FROM users WHERE id = :id"),
                {"id": target_user_id}
            ).mappings().first()

            if not user_row:
                raise HTTPException(status_code=404, detail="Usuário não encontrado")

            conn.execute(
                text("UPDATE users SET vault_pin_hash = NULL WHERE id = :id"),
                {"id": target_user_id}
            )

        print(f"[VAULT/PIN] PIN resetado por admin {current_user['id']} para user {target_user_id}")
        return {"ok": True, "message": f"PIN de '{user_row['name']}' resetado com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vault-pin/users-status")
def vault_pin_users_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    """ADMIN ONLY: Lista todos os usuários com status do vault PIN."""
    try:
        is_admin = current_user.get("role") == "ADMIN"
        if not is_admin:
            raise HTTPException(status_code=403, detail="Acesso negado")

        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT id, name, username, email,
                       CASE WHEN vault_pin_hash IS NOT NULL THEN 1 ELSE 0 END AS has_pin
                FROM users
                WHERE is_active = 1
                ORDER BY name ASC
            """)).mappings().all()

        return [{"id": r["id"], "name": r["name"], "username": r["username"],
                 "email": r["email"], "has_pin": bool(r["has_pin"])} for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================
# FUNCOES AUXILIARES
# =========================================

def get_user_name(conn, user_id: int) -> str:
    """Obtém o nome do usuário pelo ID."""
    try:
        result = conn.execute(
            text("SELECT name FROM users WHERE id = :id"),
            {"id": user_id}
        ).mappings().first()
        return result["name"] if result else "Desconhecido"
    except Exception:
        return "Desconhecido"
