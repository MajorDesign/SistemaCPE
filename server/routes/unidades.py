"""
Router de Unidades CPE (filiais físicas)
- GET    /api/unidades            -> Lista unidades
- GET    /api/unidades/{id}       -> Obtém unidade
- POST   /api/unidades            -> Cria unidade
- PUT    /api/unidades/{id}       -> Atualiza unidade
- DELETE /api/unidades/{id}       -> Deleta unidade (se não tiver salas/usuários)
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from database import (
    get_db_or_404,
    convert_datetime_to_string,
    convert_datetime_list,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/unidades", tags=["unidades"])


# ============================================================
# SCHEMAS
# ============================================================

class UnidadeBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=120)
    sigla: Optional[str] = Field(None, max_length=20)
    cidade: Optional[str] = Field(None, max_length=120)
    uf: Optional[str] = Field(None, min_length=2, max_length=2)
    endereco: Optional[str] = Field(None, max_length=255)
    ativo: bool = True


class UnidadeCreate(UnidadeBase):
    pass


class UnidadeUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=120)
    sigla: Optional[str] = Field(None, max_length=20)
    cidade: Optional[str] = Field(None, max_length=120)
    uf: Optional[str] = Field(None, min_length=2, max_length=2)
    endereco: Optional[str] = Field(None, max_length=255)
    ativo: Optional[bool] = None


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/")
async def list_unidades(somente_ativas: bool = False):
    """Lista todas as unidades."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        if somente_ativas:
            cursor.execute(
                "SELECT id, nome, sigla, cidade, uf, endereco, ativo, created_at "
                "FROM unidades_cpe WHERE ativo = 1 ORDER BY nome"
            )
        else:
            cursor.execute(
                "SELECT id, nome, sigla, cidade, uf, endereco, ativo, created_at "
                "FROM unidades_cpe ORDER BY nome"
            )
        rows = cursor.fetchall()
        return convert_datetime_list(rows)
    except Exception as err:
        logger.error(f"[UNIDADES/LIST] ERRO: {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar unidades: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.get("/{unidade_id}")
async def get_unidade(unidade_id: int):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, nome, sigla, cidade, uf, endereco, ativo, created_at "
            "FROM unidades_cpe WHERE id = %s",
            (unidade_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Unidade não encontrada")
        return convert_datetime_to_string(row)
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[UNIDADES/GET] ERRO: {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter unidade: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_unidade(data: UnidadeCreate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM unidades_cpe WHERE nome = %s", (data.nome,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Já existe uma unidade com esse nome")

        uf = (data.uf or "").upper() or None
        cursor.execute(
            "INSERT INTO unidades_cpe (nome, sigla, cidade, uf, endereco, ativo) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (data.nome, data.sigla, data.cidade, uf, data.endereco, 1 if data.ativo else 0),
        )
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute(
            "SELECT id, nome, sigla, cidade, uf, endereco, ativo, created_at "
            "FROM unidades_cpe WHERE id = %s",
            (new_id,),
        )
        return convert_datetime_to_string(cursor.fetchone())
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[UNIDADES/CREATE] ERRO: {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar unidade: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.put("/{unidade_id}")
async def update_unidade(unidade_id: int, data: UnidadeUpdate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM unidades_cpe WHERE id = %s", (unidade_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Unidade não encontrada")

        updates = []
        params = []
        if data.nome is not None:
            cursor.execute(
                "SELECT id FROM unidades_cpe WHERE nome = %s AND id != %s",
                (data.nome, unidade_id),
            )
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Já existe outra unidade com esse nome")
            updates.append("nome = %s"); params.append(data.nome)
        if data.sigla is not None:
            updates.append("sigla = %s"); params.append(data.sigla)
        if data.cidade is not None:
            updates.append("cidade = %s"); params.append(data.cidade)
        if data.uf is not None:
            updates.append("uf = %s"); params.append(data.uf.upper() or None)
        if data.endereco is not None:
            updates.append("endereco = %s"); params.append(data.endereco)
        if data.ativo is not None:
            updates.append("ativo = %s"); params.append(1 if data.ativo else 0)

        if not updates:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

        params.append(unidade_id)
        cursor.execute(f"UPDATE unidades_cpe SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()

        cursor.execute(
            "SELECT id, nome, sigla, cidade, uf, endereco, ativo, created_at "
            "FROM unidades_cpe WHERE id = %s",
            (unidade_id,),
        )
        return convert_datetime_to_string(cursor.fetchone())
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[UNIDADES/UPDATE] ERRO: {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar unidade: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.delete("/{unidade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unidade(unidade_id: int):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS total FROM users WHERE unit_id = %s", (unidade_id,))
        if (cursor.fetchone() or {}).get("total", 0) > 0:
            raise HTTPException(
                status_code=400,
                detail="Não é possível excluir: existem usuários vinculados a esta unidade",
            )

        cursor.execute("SELECT COUNT(*) AS total FROM recepcao_salas WHERE unit_id = %s", (unidade_id,))
        if (cursor.fetchone() or {}).get("total", 0) > 0:
            raise HTTPException(
                status_code=400,
                detail="Não é possível excluir: existem salas vinculadas a esta unidade",
            )

        cursor.execute("DELETE FROM unidades_cpe WHERE id = %s", (unidade_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Unidade não encontrada")
        conn.commit()
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[UNIDADES/DELETE] ERRO: {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao deletar unidade: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
