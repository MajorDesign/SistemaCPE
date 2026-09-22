"""
Endpoints de usuarios — /api/users*

2026-09-22: consolidacao. Ate hoje, este arquivo tinha uma versao com
Depends(get_current_user) que NUNCA foi importada pelo app.py — era
codigo morto. A versao viva estava inline em app.py:1290-1691 e vencia
o registro do router pela ordem de include. Vinha causando bugs de
"esqueci de adicionar campo em dois lugares" (PUT sem cargo em
2026-09-17, GET sem avatar_url em 2026-09-21).

Este arquivo agora e a fonte da verdade. Comportamento identico ao
inline anterior — zero regressao — mas modularizado e importado pelo
app.py como qualquer outro router.
"""

from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import logging

from database import (
    get_db_or_404,
    convert_datetime_to_string,
    convert_datetime_list,
    validate_email_unique,
    validate_username_unique,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


# =========================================
# MODELOS PYDANTIC
# =========================================

class UserBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    role: str = Field(default="USER", pattern="^(USER|ADMIN|TI|RESPONSAVEL_GRUPO)$")
    group_id: Optional[int] = None
    unit_id: Optional[int] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    cpf: Optional[str] = Field(None, max_length=14)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    role: Optional[str] = Field(None, pattern="^(USER|ADMIN|TI|RESPONSAVEL_GRUPO)$")
    group_id: Optional[int] = None
    unit_id: Optional[int] = None
    is_active: Optional[bool] = None
    cpf: Optional[str] = Field(None, max_length=14)
    # 2026-09-18 migration 098: perfil de contato editavel pelo proprio user
    cargo: Optional[str] = Field(None, max_length=120)
    telefone: Optional[str] = Field(None, max_length=30)
    ramal: Optional[str] = Field(None, max_length=10)


class PasswordChangeRequest(BaseModel):
    # senha_atual eh obrigatorio quando o proprio user troca a propria senha
    # (sem flag must_change_password ativa). Pode vir vazio quando:
    #  - admin reseta a senha de outro user (sem confirmar a atual)
    #  - user com must_change_password=1 trocando (acabou de receber temp)
    senha_atual: Optional[str] = None
    senha_nova:  str = Field(..., min_length=8)
    # admin pode marcar pra forcar troca no proximo login do user resetado
    forcar_troca: Optional[bool] = False


def _resolver_requester_id(request: Request) -> Optional[int]:
    """Pega o ID do usuario logado via cookie ou header X-Auth-Token."""
    from security import parse_session_token, COOKIE_NAME
    tok = request.cookies.get(COOKIE_NAME) or request.headers.get("X-Auth-Token") \
        or request.headers.get("x-auth-token")
    if not tok:
        return None
    return parse_session_token(tok)


# =========================================
# ENDPOINTS
# =========================================

@router.get("/")
async def get_users():
    """Obtem todos os usuarios"""
    logger.info("\n[USERS] 📋 Listando todos os usuarios...")

    conn = get_db_or_404()
    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            # 2026-09-21: avatar_url pra users.html mostrar foto na lista.
            "SELECT u.id, u.name, u.email, u.username, u.role, u.group_id, u.unit_id, u.cpf, "
            "       u.is_active, u.created_at, u.avatar_url, unidades_cpe.nome AS unit_nome "
            "FROM users u LEFT JOIN unidades_cpe ON u.unit_id = unidades_cpe.id "
            "ORDER BY u.created_at DESC"
        )
        users = cursor.fetchall()
        users = convert_datetime_list(users)

        logger.info(f"[USERS] ✅ {len(users)} usuario(s) encontrado(s)\n")
        return users or []

    except Exception as err:
        logger.error(f"[USERS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao listar usuarios: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.get("/{user_id}")
async def get_user(user_id: int):
    """Obtem um usuario especifico"""
    logger.info(f"\n[USERS] 🔍 Obtendo usuario #{user_id}...")

    conn = get_db_or_404()
    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT u.id, u.name, u.email, u.username, u.role, u.group_id, u.unit_id, u.cpf, "
            "       u.is_active, u.created_at, u.avatar_url, unidades_cpe.nome AS unit_nome "
            "FROM users u LEFT JOIN unidades_cpe ON u.unit_id = unidades_cpe.id "
            "WHERE u.id = %s",
            (user_id,),
        )
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")

        user = convert_datetime_to_string(user)
        logger.info(f"[USERS] ✅ Usuario encontrado: {user['name']}\n")
        return user

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[USERS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao obter usuario: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """Cria um novo usuario"""
    logger.info("\n[USERS] ➕ CRIANDO NOVO USUARIO")
    logger.info(f"[USERS]   - Nome: {user.name}")
    logger.info(f"[USERS]   - Email: {user.email}")

    conn = get_db_or_404()
    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)

        if not validate_email_unique(cursor, user.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Email ja registrado")

        if not validate_username_unique(cursor, user.username):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Username ja registrado")

        if user.group_id:
            cursor.execute("SELECT id FROM `cpe_grupo` WHERE id = %s", (user.group_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grupo nao encontrado")

        if user.unit_id:
            cursor.execute("SELECT id FROM unidades_cpe WHERE id = %s", (user.unit_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unidade nao encontrada")

        logger.info("[USERS] 🔐 Gerando hash da senha (argon2 via passlib)...")
        try:
            # 2026-08-21: padronizado com hash_password (utils) — antes usava
            # bcrypt direto, criando duas familias de hash no banco (bcrypt
            # do cadastro, argon2 do reset). Login/verify agora usam passlib
            # e aceitam ambos, mas cadastro novo sai em argon2.
            from utils import hash_password as _hash_pwd
            password_hash = _hash_pwd(user.password)
            logger.info("[USERS]   ✅ Hash gerado com sucesso")
        except Exception:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao processar senha")

        cpf_clean = ''.join(filter(str.isdigit, (user.cpf or ''))) or None
        cursor.execute(
            "INSERT INTO users (name, email, username, password_hash, role, group_id, unit_id, cpf, is_active) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (user.name, user.email, user.username, password_hash, user.role,
             user.group_id, user.unit_id, cpf_clean, user.is_active)
        )

        conn.commit()
        new_user_id = cursor.lastrowid
        logger.info(f"[USERS]   ✅ Usuario criado com ID: {new_user_id}")

        cursor.execute(
            "SELECT u.id, u.name, u.email, u.username, u.role, u.group_id, u.unit_id, u.cpf, "
            "       u.is_active, u.created_at, unidades_cpe.nome AS unit_nome "
            "FROM users u LEFT JOIN unidades_cpe ON u.unit_id = unidades_cpe.id "
            "WHERE u.id = %s",
            (new_user_id,),
        )
        new_user = cursor.fetchone()
        new_user = convert_datetime_to_string(new_user)

        logger.info("[USERS] ✅ SUCESSO!\n")
        return new_user

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[USERS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao criar usuario: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.put("/{user_id}")
async def update_user(user_id: int, user: UserUpdate):
    """Atualiza um usuario"""
    logger.info(f"\n[USERS] ✏️ ATUALIZANDO USUARIO #{user_id}")

    conn = get_db_or_404()
    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")

        updates = []
        params = []

        if user.name is not None:
            updates.append("name = %s")
            params.append(user.name)

        if user.email is not None:
            if not validate_email_unique(cursor, user.email, exclude_user_id=user_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email ja registrado")
            updates.append("email = %s")
            params.append(user.email)

        if user.username is not None:
            if not validate_username_unique(cursor, user.username, exclude_user_id=user_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username ja registrado")
            updates.append("username = %s")
            params.append(user.username)

        if user.role is not None:
            updates.append("role = %s")
            params.append(user.role)

        if user.group_id is not None:
            cursor.execute("SELECT id FROM `cpe_grupo` WHERE id = %s", (user.group_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grupo nao encontrado")
            updates.append("group_id = %s")
            params.append(user.group_id)

        if user.unit_id is not None:
            if user.unit_id != 0:
                cursor.execute("SELECT id FROM unidades_cpe WHERE id = %s", (user.unit_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unidade nao encontrada")
            updates.append("unit_id = %s")
            params.append(user.unit_id if user.unit_id != 0 else None)

        if user.is_active is not None:
            updates.append("is_active = %s")
            params.append(user.is_active)

        if user.cpf is not None:
            cpf_clean = ''.join(filter(str.isdigit, user.cpf)) or None
            updates.append("cpf = %s")
            params.append(cpf_clean)

        # 2026-09-18: campos do perfil de contato (migration 098).
        if user.cargo is not None:
            v = (user.cargo or "").strip()
            updates.append("cargo = %s")
            params.append(v[:120] if v else None)
        if user.telefone is not None:
            v = (user.telefone or "").strip()
            updates.append("telefone = %s")
            params.append(v[:30] if v else None)
        if user.ramal is not None:
            v = (user.ramal or "").strip()
            if v and not v.isdigit():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ramal deve conter apenas números"
                )
            updates.append("ramal = %s")
            params.append(v[:10] if v else None)

        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhum campo para atualizar")

        params.append(user_id)
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()

        cursor.execute(
            "SELECT u.id, u.name, u.email, u.username, u.role, u.group_id, u.unit_id, u.cpf, "
            "       u.is_active, u.created_at, unidades_cpe.nome AS unit_nome "
            "FROM users u LEFT JOIN unidades_cpe ON u.unit_id = unidades_cpe.id "
            "WHERE u.id = %s",
            (user_id,),
        )
        updated_user = cursor.fetchone()
        updated_user = convert_datetime_to_string(updated_user)

        logger.info("[USERS] ✅ SUCESSO!\n")
        return updated_user

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[USERS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao atualizar usuario: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.post("/{user_id}/senha")
async def change_password(user_id: int, payload: PasswordChangeRequest, request: Request):
    """Troca/reseta senha de usuario.

    Tres modos:
      1. SELF normal: user troca a propria senha — exige `senha_atual`,
         confere com bcrypt. Zera must_change_password.
      2. SELF apos reset admin: user com must_change_password=1 troca
         sem precisar de `senha_atual` (acabou de receber temporaria).
         Zera a flag.
      3. ADMIN: ADMIN/TI/MANAGER/RESPONSAVEL_GRUPO redefine senha de
         OUTRO user sem precisar de `senha_atual`. Pode marcar
         `forcar_troca=true` (set must_change_password=1) — recomendado
         pra forcar o user a definir uma senha pessoal antes de seguir.
    """
    requester_id = _resolver_requester_id(request)
    if not requester_id:
        raise HTTPException(status_code=401, detail="Nao autenticado")

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        # Quem esta solicitando + alvo
        cursor.execute(
            "SELECT id, role, password_hash, must_change_password "
            "FROM users WHERE id = %s", (requester_id,))
        requester = cursor.fetchone()
        if not requester:
            raise HTTPException(status_code=401, detail="Solicitante invalido")

        cursor.execute(
            "SELECT id, password_hash, must_change_password "
            "FROM users WHERE id = %s", (user_id,))
        target = cursor.fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")

        is_self = (requester["id"] == user_id)
        is_admin = requester["role"] in ("ADMIN", "TI", "MANAGER", "RESPONSAVEL_GRUPO")

        if not is_self and not is_admin:
            raise HTTPException(status_code=403,
                                detail="Sem permissao pra resetar senha de outro usuario")

        # Modo SELF: precisa confirmar a senha atual, A NAO SER que
        # esteja com flag must_change_password (acabou de ser resetado).
        # 2026-08-21: usa verify_password (passlib argon2+bcrypt) — antes usava
        # bcrypt.checkpw direto, que travava quem tinha hash argon2 (do reset).
        from utils import verify_password as _verify_pwd, hash_password as _hash_pwd
        if is_self and not target.get("must_change_password"):
            if not payload.senha_atual:
                raise HTTPException(status_code=400,
                                    detail="Informe a senha atual")
            if not _verify_pwd(payload.senha_atual, target["password_hash"] or ""):
                raise HTTPException(status_code=401, detail="Senha atual incorreta")

        # Decide nova flag must_change_password:
        #   admin reset com forcar_troca = 1
        #   qualquer SELF (incluindo apos reset) = 0
        if is_self:
            nova_flag = 0
        else:
            nova_flag = 1 if payload.forcar_troca else 0

        # Usa hash_password (argon2 via passlib) — mesmo esquema do reset,
        # mantem consistencia. Login e mudanca de senha aceitam ambos.
        novo_hash = _hash_pwd(payload.senha_nova)
        cursor.execute(
            "UPDATE users SET password_hash = %s, must_change_password = %s WHERE id = %s",
            (novo_hash, nova_flag, user_id))
        conn.commit()
        logger.info(f"[USERS] Senha alterada — alvo={user_id} solicitante={requester_id} "
                    f"is_self={is_self} forcar_troca={nova_flag}")
        return {"ok": True, "mensagem": "Senha alterada com sucesso",
                "must_change_password": bool(nova_flag)}
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[USERS] ❌ ERRO ao trocar senha: {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao trocar senha: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int):
    """Deleta um usuario"""
    logger.info(f"\n[USERS] 🗑️ DELETANDO USUARIO #{user_id}...")

    conn = get_db_or_404()
    cursor = None

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT name FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")

        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()

        logger.info(f"[USERS] ✅ DELETADO COM SUCESSO!\n")

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[USERS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao deletar usuario: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
