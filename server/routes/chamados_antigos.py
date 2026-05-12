"""
API de Chamados Antigos — somente consulta.

Endpoints:
  GET /api/chamados-antigos          → lista paginada com filtros
  GET /api/chamados-antigos/{trackid} → detalhe de 1 chamado
  GET /api/chamados-antigos/stats     → estatísticas (total)

Os dados vêm da tabela `chamados_antigos` populada via:
    python tools/import_chamados_antigos.py

Todos os endpoints aceitam usuario_id na query string apenas para log de auditoria.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Path
from database import get_db_or_404

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chamados-antigos", tags=["chamados-antigos"])


@router.get("/stats")
def stats(usuario_id: Optional[int] = Query(None, gt=0)):
    """Retorna {total, ultimo_import} da base. Tudo zero/None se a tabela não existir."""
    conn = get_db_or_404()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT COUNT(*) AS total, MAX(created_at) AS ultimo_import "
            "FROM chamados_antigos"
        )
        row = cur.fetchone() or {}
        ultimo = row.get("ultimo_import")
        return {
            "total":         int(row.get("total") or 0),
            "ultimo_import": ultimo.isoformat() if ultimo else None,
        }
    except Exception as e:
        msg = str(e).lower()
        if "doesn't exist" in msg or "chamados_antigos" in msg:
            return {"total": 0, "ultimo_import": None}
        # Coluna created_at não existe — fallback só com total
        if "created_at" in msg:
            try:
                cur.execute("SELECT COUNT(*) AS total FROM chamados_antigos")
                r2 = cur.fetchone() or {}
                return {"total": int(r2.get("total") or 0), "ultimo_import": None}
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()


@router.get("/categorias")
def listar_categorias():
    """Retorna categorias distintas da base — para popular o filtro no front."""
    conn = get_db_or_404()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT categoria, COUNT(*) AS total
              FROM chamados_antigos
             WHERE categoria IS NOT NULL AND categoria <> ''
             GROUP BY categoria
             ORDER BY categoria ASC
            """
        )
        return cur.fetchall() or []
    except Exception as e:
        msg = str(e).lower()
        if "doesn't exist" in msg or "chamados_antigos" in msg:
            return []
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()


@router.get("")
@router.get("/")
def listar(
    usuario_id: Optional[int] = Query(None, gt=0),
    q:        Optional[str]   = Query(None, description="Busca em assunto, solicitante, email, mensagem"),
    status:   Optional[str]   = Query(None, description="Filtra por Nome_status"),
    categoria: Optional[str]  = Query(None, description="Filtra por categoria exata"),
    data_ini: Optional[str]   = Query(None, description="YYYY-MM-DD"),
    data_fim: Optional[str]   = Query(None, description="YYYY-MM-DD"),
    pagina:   int = Query(1, ge=1),
    por_pagina: int = Query(25, ge=1, le=100),
):
    """Lista chamados antigos com filtros e paginação."""
    conn = get_db_or_404()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)

        filtros: list[str] = []
        params:  list = []

        if q and q.strip():
            termo = f"%{q.strip()}%"
            filtros.append(
                "(trackid LIKE %s OR assunto LIKE %s OR solicitante LIKE %s "
                " OR email LIKE %s OR mensagem LIKE %s OR resposta LIKE %s "
                " OR atribuido_a LIKE %s OR respondido_por LIKE %s)"
            )
            params.extend([termo] * 8)

        if status and status.strip():
            filtros.append("nome_status = %s")
            params.append(status.strip())

        if categoria and categoria.strip():
            filtros.append("categoria = %s")
            params.append(categoria.strip())

        if data_ini:
            filtros.append("DATE(aberto_em) >= %s")
            params.append(data_ini)
        if data_fim:
            filtros.append("DATE(aberto_em) <= %s")
            params.append(data_fim)

        where = ("WHERE " + " AND ".join(filtros)) if filtros else ""

        # Total para paginação
        cur.execute(f"SELECT COUNT(*) AS c FROM chamados_antigos {where}", params)
        total = int((cur.fetchone() or {}).get("c") or 0)

        offset = (pagina - 1) * por_pagina
        cur.execute(
            f"""
            SELECT trackid, nome_status, email, solicitante, categoria, prioridade,
                   assunto, aberto_em, fechado_em, atribuido_a
              FROM chamados_antigos
              {where}
             ORDER BY aberto_em DESC
             LIMIT %s OFFSET %s
            """,
            params + [por_pagina, offset]
        )
        rows = cur.fetchall()
        for r in rows:
            if r.get("aberto_em"):  r["aberto_em"]  = r["aberto_em"].isoformat()
            if r.get("fechado_em"): r["fechado_em"] = r["fechado_em"].isoformat()

        return {
            "total":       total,
            "pagina":      pagina,
            "por_pagina":  por_pagina,
            "total_paginas": max(1, (total + por_pagina - 1) // por_pagina),
            "itens":       rows,
        }

    except Exception as e:
        msg = str(e).lower()
        if "doesn't exist" in msg or "chamados_antigos" in msg:
            logger.warning("[CHAMADOS_ANTIGOS] tabela ainda não existe — rode a migration 033 e o import")
            return {"total": 0, "pagina": 1, "por_pagina": por_pagina,
                    "total_paginas": 1, "itens": []}
        logger.error(f"[CHAMADOS_ANTIGOS] erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()


@router.get("/{trackid}")
def detalhe(trackid: str = Path(...)):
    """Retorna todos os campos de um chamado antigo."""
    conn = get_db_or_404()
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT * FROM chamados_antigos WHERE trackid = %s LIMIT 1""",
            (trackid,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Chamado {trackid} não encontrado")
        for k in ("aberto_em", "primeira_resp", "fechado_em", "dh_resposta"):
            if row.get(k): row[k] = row[k].isoformat()
        return row
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e).lower()
        if "doesn't exist" in msg or "chamados_antigos" in msg:
            raise HTTPException(status_code=404, detail="Base de chamados antigos não inicializada")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()
