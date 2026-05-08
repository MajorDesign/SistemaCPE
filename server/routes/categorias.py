"""
API de Categorias e Subcategorias
- Categorias ficam vinculadas a um grupo (cpe_grupo)
- Subcategorias ficam vinculadas a uma categoria
- Apenas ADMIN e TI podem criar/editar/deletar
- Qualquer usuário autenticado pode listar (para uso no form de ticket)
"""

from fastapi import APIRouter, HTTPException, Query, Path, status
from pydantic import BaseModel, Field
from typing import Optional
import logging

from database import get_db_or_404

logger = logging.getLogger(__name__)

ROLES_ESCRITA = {"ADMIN", "TI"}

categorias_router    = APIRouter(prefix="/api/categorias",    tags=["categorias"])
subcategorias_router = APIRouter(prefix="/api/subcategorias", tags=["subcategorias"])

# Endpoint extra para verificar permissão no frontend
@categorias_router.get("/check-permissao")
async def check_permissao_categorias(usuario_id: int):
    """
    Retorna se o usuário pode gerenciar categorias e em qual escopo.

    Resposta:
        {pode: bool, scope: 'all'|'own'|null, group_id: int|null}

    - ADMIN/TI                       → scope='all',  group_id=null  (todos os grupos)
    - RESPONSAVEL_GRUPO com group_id → scope='own',  group_id=<id>  (apenas o próprio grupo)
    - Exceção MANAGE_CATEGORIES      → scope='all',  group_id=null  (todos os grupos)
    - Demais                         → pode=False
    """
    from database import get_db_or_404
    conn   = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT role, group_id FROM users WHERE id = %s AND is_active = 1",
            (usuario_id,)
        )
        user = cursor.fetchone()
        if not user:
            return {"pode": False, "scope": None, "group_id": None}

        if user["role"] in ROLES_ESCRITA:
            return {"pode": True, "scope": "all", "group_id": None}

        if user["role"] == "RESPONSAVEL_GRUPO" and user.get("group_id"):
            return {"pode": True, "scope": "own", "group_id": user["group_id"]}

        # Exceção MANAGE_CATEGORIES = libera escrita global (mesmo comportamento legado)
        cursor.execute(
            "SELECT id FROM user_access_exceptions "
            "WHERE user_id = %s AND page_name = 'MANAGE_CATEGORIES' AND exception_type = 'allow'",
            (usuario_id,)
        )
        if cursor.fetchone():
            return {"pode": True, "scope": "all", "group_id": None}

        return {"pode": False, "scope": None, "group_id": None}
    finally:
        cursor.close()
        conn.close()


# =========================================
# MODELS
# =========================================

class CategoriaCreate(BaseModel):
    group_id:                       int           = Field(..., gt=0)
    nome:                           str           = Field(..., min_length=2, max_length=255)
    descricao:                      Optional[str] = Field(None, max_length=500)
    sla_minutos:                    Optional[int] = Field(None, ge=1, description="SLA total em minutos. None = sem SLA.")
    sla_primeira_resposta_minutos:  Optional[int] = Field(None, ge=1, description="SLA de primeira resposta em minutos. None = sem SLA de 1ª resposta.")
    usuario_id:                     int           = Field(..., gt=0)

class CategoriaUpdate(BaseModel):
    nome:                           Optional[str]  = Field(None, min_length=2, max_length=255)
    descricao:                      Optional[str]  = Field(None, max_length=500)
    sla_minutos:                    Optional[int]  = Field(None, ge=0, description="0 = remover SLA; >0 = novo valor em minutos")
    sla_primeira_resposta_minutos:  Optional[int]  = Field(None, ge=0, description="0 = remover SLA de 1ª resposta; >0 = novo valor em minutos")
    ativo:                          Optional[bool] = None
    usuario_id:                     int            = Field(..., gt=0)

class SubcategoriaCreate(BaseModel):
    categoria_id:                   int           = Field(..., gt=0)
    nome:                           str           = Field(..., min_length=2, max_length=255)
    descricao:                      Optional[str] = Field(None, max_length=500)
    sla_minutos:                    Optional[int] = Field(None, ge=1, description="SLA total em minutos. None = herda da categoria.")
    sla_primeira_resposta_minutos:  Optional[int] = Field(None, ge=1, description="SLA de primeira resposta em minutos. None = herda da categoria.")
    usuario_id:                     int           = Field(..., gt=0)

class SubcategoriaUpdate(BaseModel):
    nome:                           Optional[str]  = Field(None, min_length=2, max_length=255)
    descricao:                      Optional[str]  = Field(None, max_length=500)
    sla_minutos:                    Optional[int]  = Field(None, ge=0, description="0 = remover SLA; >0 = novo valor em minutos")
    sla_primeira_resposta_minutos:  Optional[int]  = Field(None, ge=0, description="0 = remover SLA de 1ª resposta; >0 = novo valor em minutos")
    ativo:                          Optional[bool] = None
    usuario_id:                     int            = Field(..., gt=0)


# =========================================
# HELPER
# =========================================

def _verificar_permissao(cursor, usuario_id: int, group_id: int = None):
    """
    Verifica se o usuário pode gerenciar categorias do grupo informado.

    - ADMIN/TI                          → pode em qualquer grupo
    - RESPONSAVEL_GRUPO                 → só se users.group_id == group_id
    - Exceção MANAGE_CATEGORIES         → pode em qualquer grupo
    - Demais                            → 403

    `group_id=None` significa "operação não vinculada a grupo" (uso interno
    raro) e exige um dos cargos com escopo global.
    """
    cursor.execute(
        "SELECT role, group_id FROM users WHERE id = %s AND is_active = 1",
        (usuario_id,)
    )
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    role = user["role"]
    user_group_id = user.get("group_id")

    if role in ROLES_ESCRITA:
        return  # ADMIN/TI: tudo

    if role == "RESPONSAVEL_GRUPO":
        if group_id is not None and user_group_id == group_id:
            return  # Responsável agindo no próprio grupo
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode gerenciar categorias do seu próprio grupo."
        )

    # Exceção individual MANAGE_CATEGORIES — escopo global
    cursor.execute(
        "SELECT id FROM user_access_exceptions "
        "WHERE user_id = %s AND page_name = 'MANAGE_CATEGORIES' AND exception_type = 'allow'",
        (usuario_id,)
    )
    if cursor.fetchone():
        return  # Permissão concedida via exceção individual

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Sem permissão para gerenciar categorias"
    )


def _group_id_da_categoria(cursor, categoria_id: int) -> int:
    """Retorna o group_id da categoria. Lança 404 se não existir."""
    cursor.execute("SELECT group_id FROM categorias WHERE id = %s", (categoria_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Categoria nao encontrada")
    return row["group_id"]


def _group_id_da_subcategoria(cursor, subcategoria_id: int) -> int:
    """Retorna o group_id do grupo da categoria pai da subcategoria."""
    cursor.execute(
        """SELECT c.group_id
             FROM subcategorias s
             JOIN categorias c ON c.id = s.categoria_id
            WHERE s.id = %s""",
        (subcategoria_id,)
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Subcategoria nao encontrada")
    return row["group_id"]


# =========================================
# CATEGORIAS
# =========================================

@categorias_router.get("/")
async def listar_categorias(group_id: int = Query(..., gt=0)):
    """Lista categorias ativas de um grupo com suas subcategorias."""
    conn   = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, group_id, nome, descricao, sla_minutos, sla_primeira_resposta_minutos, ativo, created_at "
            "FROM categorias WHERE group_id = %s AND ativo = 1 ORDER BY nome",
            (group_id,)
        )
        cats = cursor.fetchall()
        for cat in cats:
            cursor.execute(
                "SELECT id, categoria_id, nome, descricao, sla_minutos, sla_primeira_resposta_minutos, ativo, created_at "
                "FROM subcategorias WHERE categoria_id = %s AND ativo = 1 ORDER BY nome",
                (cat["id"],)
            )
            cat["subcategorias"] = cursor.fetchall()
        return cats
    finally:
        cursor.close()
        conn.close()


@categorias_router.post("/", status_code=status.HTTP_201_CREATED)
async def criar_categoria(payload: CategoriaCreate):
    """Cria categoria para um grupo. ADMIN/TI ou Responsável do próprio grupo."""
    conn   = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _verificar_permissao(cursor, payload.usuario_id, group_id=payload.group_id)

        cursor.execute("SELECT id FROM `cpe_grupo` WHERE id = %s", (payload.group_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Grupo #{payload.group_id} nao encontrado")

        cursor.execute(
            "INSERT INTO categorias (group_id, nome, descricao, sla_minutos, sla_primeira_resposta_minutos) "
            "VALUES (%s, %s, %s, %s, %s)",
            (payload.group_id, payload.nome.strip(), payload.descricao,
             payload.sla_minutos or None, payload.sla_primeira_resposta_minutos or None)
        )
        conn.commit()
        cat_id = cursor.lastrowid

        cursor.execute(
            "SELECT id, group_id, nome, descricao, sla_minutos, sla_primeira_resposta_minutos, ativo, created_at "
            "FROM categorias WHERE id = %s",
            (cat_id,)
        )
        nova = cursor.fetchone()
        nova["subcategorias"] = []
        logger.info(f"[CATEGORIA] Criada: '{payload.nome}' no grupo #{payload.group_id}")
        return nova

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        if "Duplicate entry" in str(e):
            raise HTTPException(status_code=400, detail=f"Ja existe uma categoria '{payload.nome}' neste grupo")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@categorias_router.put("/{categoria_id}")
async def atualizar_categoria(categoria_id: int = Path(..., gt=0), payload: CategoriaUpdate = None):
    """Atualiza uma categoria. ADMIN/TI ou Responsável do próprio grupo."""
    conn   = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        # Categoria precisa existir; pegamos seu group_id para validar permissão
        gid = _group_id_da_categoria(cursor, categoria_id)
        _verificar_permissao(cursor, payload.usuario_id, group_id=gid)

        updates, params = [], []
        if payload.nome        is not None: updates.append("nome = %s");        params.append(payload.nome.strip())
        if payload.descricao   is not None: updates.append("descricao = %s");   params.append(payload.descricao)
        if payload.ativo       is not None: updates.append("ativo = %s");       params.append(1 if payload.ativo else 0)
        if payload.sla_minutos is not None:
            sla_val = payload.sla_minutos if payload.sla_minutos > 0 else None
            updates.append("sla_minutos = %s"); params.append(sla_val)
        if payload.sla_primeira_resposta_minutos is not None:
            pr_val = payload.sla_primeira_resposta_minutos if payload.sla_primeira_resposta_minutos > 0 else None
            updates.append("sla_primeira_resposta_minutos = %s"); params.append(pr_val)

        if not updates:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

        params.append(categoria_id)
        cursor.execute(f"UPDATE categorias SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()

        cursor.execute(
            "SELECT id, group_id, nome, descricao, sla_minutos, sla_primeira_resposta_minutos, ativo "
            "FROM categorias WHERE id = %s",
            (categoria_id,)
        )
        return cursor.fetchone()

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        if "Duplicate entry" in str(e):
            raise HTTPException(status_code=400, detail="Ja existe uma categoria com esse nome neste grupo")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@categorias_router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_categoria(
    categoria_id: int = Path(..., gt=0),
    usuario_id:   int = Query(..., gt=0)
):
    """Desativa categoria e suas subcategorias (soft-delete).
    ADMIN/TI ou Responsável do próprio grupo."""
    conn   = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        gid = _group_id_da_categoria(cursor, categoria_id)
        _verificar_permissao(cursor, usuario_id, group_id=gid)

        cursor.execute("UPDATE subcategorias SET ativo = 0 WHERE categoria_id = %s", (categoria_id,))
        cursor.execute("UPDATE categorias    SET ativo = 0 WHERE id = %s",           (categoria_id,))
        conn.commit()
        logger.info(f"[CATEGORIA] Desativada: #{categoria_id}")

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# =========================================
# SUBCATEGORIAS
# =========================================

@subcategorias_router.get("/")
async def listar_subcategorias(categoria_id: int = Query(..., gt=0)):
    """Lista subcategorias ativas de uma categoria."""
    conn   = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, categoria_id, nome, descricao, sla_minutos, sla_primeira_resposta_minutos, ativo, created_at "
            "FROM subcategorias WHERE categoria_id = %s AND ativo = 1 ORDER BY nome",
            (categoria_id,)
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


@subcategorias_router.post("/", status_code=status.HTTP_201_CREATED)
async def criar_subcategoria(payload: SubcategoriaCreate):
    """Cria subcategoria. ADMIN/TI ou Responsável do grupo da categoria pai."""
    conn   = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, group_id FROM categorias WHERE id = %s AND ativo = 1",
            (payload.categoria_id,)
        )
        cat = cursor.fetchone()
        if not cat:
            raise HTTPException(status_code=404, detail="Categoria nao encontrada ou inativa")
        _verificar_permissao(cursor, payload.usuario_id, group_id=cat["group_id"])

        cursor.execute(
            "INSERT INTO subcategorias (categoria_id, nome, descricao, sla_minutos, sla_primeira_resposta_minutos) "
            "VALUES (%s, %s, %s, %s, %s)",
            (payload.categoria_id, payload.nome.strip(), payload.descricao,
             payload.sla_minutos or None, payload.sla_primeira_resposta_minutos or None)
        )
        conn.commit()
        sub_id = cursor.lastrowid

        cursor.execute(
            "SELECT id, categoria_id, nome, descricao, sla_minutos, sla_primeira_resposta_minutos, ativo, created_at "
            "FROM subcategorias WHERE id = %s",
            (sub_id,)
        )
        nova = cursor.fetchone()
        logger.info(f"[SUBCATEGORIA] Criada: '{payload.nome}' na categoria #{payload.categoria_id}")
        return nova

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        if "Duplicate entry" in str(e):
            raise HTTPException(status_code=400, detail=f"Ja existe uma subcategoria '{payload.nome}' nesta categoria")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@subcategorias_router.put("/{subcategoria_id}")
async def atualizar_subcategoria(subcategoria_id: int = Path(..., gt=0), payload: SubcategoriaUpdate = None):
    """Atualiza uma subcategoria. ADMIN/TI ou Responsável do grupo da categoria pai."""
    conn   = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        gid = _group_id_da_subcategoria(cursor, subcategoria_id)
        _verificar_permissao(cursor, payload.usuario_id, group_id=gid)

        updates, params = [], []
        if payload.nome      is not None: updates.append("nome = %s");      params.append(payload.nome.strip())
        if payload.descricao is not None: updates.append("descricao = %s"); params.append(payload.descricao)
        if payload.ativo     is not None: updates.append("ativo = %s");     params.append(1 if payload.ativo else 0)
        if payload.sla_minutos is not None:
            sla_val = payload.sla_minutos if payload.sla_minutos > 0 else None
            updates.append("sla_minutos = %s"); params.append(sla_val)
        if payload.sla_primeira_resposta_minutos is not None:
            pr_val = payload.sla_primeira_resposta_minutos if payload.sla_primeira_resposta_minutos > 0 else None
            updates.append("sla_primeira_resposta_minutos = %s"); params.append(pr_val)

        if not updates:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

        params.append(subcategoria_id)
        cursor.execute(f"UPDATE subcategorias SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()

        cursor.execute(
            "SELECT id, categoria_id, nome, descricao, sla_minutos, sla_primeira_resposta_minutos, ativo "
            "FROM subcategorias WHERE id = %s",
            (subcategoria_id,)
        )
        return cursor.fetchone()

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        if "Duplicate entry" in str(e):
            raise HTTPException(status_code=400, detail="Ja existe uma subcategoria com esse nome nesta categoria")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@subcategorias_router.delete("/{subcategoria_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_subcategoria(
    subcategoria_id: int = Path(..., gt=0),
    usuario_id:      int = Query(..., gt=0)
):
    """Desativa subcategoria (soft-delete). ADMIN/TI ou Responsável do grupo da categoria pai."""
    conn   = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        gid = _group_id_da_subcategoria(cursor, subcategoria_id)
        _verificar_permissao(cursor, usuario_id, group_id=gid)

        cursor.execute("UPDATE subcategorias SET ativo = 0 WHERE id = %s", (subcategoria_id,))
        conn.commit()
        logger.info(f"[SUBCATEGORIA] Desativada: #{subcategoria_id}")

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
