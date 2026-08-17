"""
API de Avaliações de Tickets
- Solicitante avalia o atendimento após o chamado ser finalizado (status 4)
- Escala de 1 a 10 estrelas (cada = 10%)
- Comentário obrigatório se estrelas < 4
- Prazo de 7 dias após finalização; popup mostrado no máximo 2x
- Leitura: RESPONSAVEL_GRUPO (só do seu grupo) e ADMIN
"""

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, timedelta
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_or_404

logger = logging.getLogger(__name__)

avaliacoes_router = APIRouter(prefix="/api/avaliacoes", tags=["Avaliações"])

ROLES_ADMIN = ("ADMIN", "TI", "MANAGER")


# ─── Modelos ──────────────────────────────────────────────────────────────────

class AvaliacaoSubmit(BaseModel):
    usuario_id: int = Field(..., gt=0)
    estrelas:   int = Field(..., ge=1, le=10)
    comentario: Optional[str] = Field(None, max_length=2000)

    @field_validator("comentario")
    @classmethod
    def comentario_obrigatorio_abaixo_4(cls, v, info):
        estrelas = info.data.get("estrelas")
        if estrelas is not None and estrelas < 4:
            if not v or not v.strip():
                raise ValueError("Comentário obrigatório para avaliações abaixo de 4 estrelas.")
        return v


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _fmt_dt(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


def _usuario(cursor, uid):
    cursor.execute("SELECT id, name, role, group_id FROM users WHERE id = %s", (uid,))
    u = cursor.fetchone()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return u


# ─── POST /api/avaliacoes/popup-visto/{ticket_id} ─────────────────────────────
@avaliacoes_router.post("/popup-visto/{ticket_id}", status_code=200)
async def registrar_popup_visto(ticket_id: int, usuario_id: int = Query(..., gt=0)):
    """Incrementa popup_count (máx 2). Chamado pelo frontend ao exibir o popup."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, popup_count, avaliado_em FROM ticket_avaliacoes WHERE ticket_id = %s AND solicitante_id = %s",
            (ticket_id, usuario_id)
        )
        row = cursor.fetchone()
        if not row:
            return {"ok": False, "detail": "Avaliação não encontrada."}
        if row["avaliado_em"]:
            return {"ok": False, "detail": "Já avaliado."}
        novo = min((row["popup_count"] or 0) + 1, 2)
        cursor.execute(
            "UPDATE ticket_avaliacoes SET popup_count = %s WHERE ticket_id = %s",
            (novo, ticket_id)
        )
        conn.commit()
        return {"ok": True, "popup_count": novo}
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# ─── GET /api/avaliacoes/pendentes ────────────────────────────────────────────
@avaliacoes_router.get("/pendentes")
async def avaliacoes_pendentes(usuario_id: int = Query(..., gt=0)):
    """
    Retorna avaliações pendentes do solicitante:
    - Não avaliado
    - Não expirado
    - popup_count < 2
    """
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                a.ticket_id, a.popup_count, a.expira_em,
                t.numero, t.assunto,
                u.name AS responsavel_nome
            FROM ticket_avaliacoes a
            JOIN tickets t ON t.id = a.ticket_id
            LEFT JOIN users u ON u.id = a.responsavel_id
            WHERE a.solicitante_id = %s
              AND a.avaliado_em IS NULL
              AND a.expira_em > NOW()
              AND a.popup_count < 2
            ORDER BY a.created_at DESC
            """,
            (usuario_id,)
        )
        rows = cursor.fetchall()
        for r in rows:
            r["expira_em"] = _fmt_dt(r["expira_em"])
        return rows
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# ─── POST /api/avaliacoes/{ticket_id} ─────────────────────────────────────────
@avaliacoes_router.post("/{ticket_id}", status_code=201)
async def submeter_avaliacao(ticket_id: int, payload: AvaliacaoSubmit):
    """Solicitante submete sua avaliação (única, definitiva)."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, solicitante_id, avaliado_em, expira_em
            FROM ticket_avaliacoes
            WHERE ticket_id = %s
            """,
            (ticket_id,)
        )
        aval = cursor.fetchone()
        if not aval:
            raise HTTPException(status_code=404, detail="Ticket sem avaliação pendente.")

        if aval["avaliado_em"]:
            raise HTTPException(status_code=409, detail="Este chamado já foi avaliado.")

        if aval["solicitante_id"] != payload.usuario_id:
            raise HTTPException(status_code=403, detail="Apenas o solicitante pode avaliar este chamado.")

        if aval["expira_em"] and aval["expira_em"] < datetime.now():
            raise HTTPException(status_code=410, detail="Prazo de avaliação expirado.")

        cursor.execute(
            """
            UPDATE ticket_avaliacoes
            SET estrelas     = %s,
                comentario   = %s,
                avaliado_em  = NOW()
            WHERE ticket_id  = %s
            """,
            (payload.estrelas, payload.comentario, ticket_id)
        )
        conn.commit()
        logger.info(f"[AVALIACAO] Ticket #{ticket_id} avaliado com {payload.estrelas} estrelas")
        return {"ok": True, "message": "Avaliação registrada com sucesso."}
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# ─── GET /api/avaliacoes ──────────────────────────────────────────────────────
@avaliacoes_router.get("")
async def listar_avaliacoes(
    usuario_id:  int           = Query(..., gt=0),
    grupo_id:    Optional[int] = Query(None),
    data_inicio: Optional[str] = Query(None),
    data_fim:    Optional[str] = Query(None),
    estrelas_min:Optional[int] = Query(None, ge=1, le=10),
    estrelas_max:Optional[int] = Query(None, ge=1, le=10),
    apenas_avaliados: bool     = Query(False),
    responsavel_id: Optional[int] = Query(None, gt=0),
    categoria_id:    Optional[int] = Query(None, gt=0),
    subcategoria_id: Optional[int] = Query(None, gt=0),
    pagina:      int           = Query(1, ge=1),
    por_pagina:  int           = Query(50, ge=1, le=200),
):
    """
    Lista avaliações — acesso: RESPONSAVEL_GRUPO (só grupo) ou ADMIN (todos).
    """
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        usuario = _usuario(cursor, usuario_id)
        role    = usuario.get("role") or "USER"
        e_admin = role in ROLES_ADMIN

        if not e_admin and role != "RESPONSAVEL_GRUPO":
            raise HTTPException(status_code=403, detail="Acesso negado.")

        filtros = []
        params  = []

        # RESPONSAVEL_GRUPO: só vê o próprio grupo
        if not e_admin:
            filtros.append("a.group_id = %s")
            params.append(usuario.get("group_id"))
        elif grupo_id:
            filtros.append("a.group_id = %s")
            params.append(grupo_id)

        if data_inicio:
            filtros.append("a.created_at >= %s")
            params.append(data_inicio + " 00:00:00")
        if data_fim:
            filtros.append("a.created_at <= %s")
            params.append(data_fim + " 23:59:59")
        if estrelas_min is not None:
            filtros.append("a.estrelas >= %s")
            params.append(estrelas_min)
        if estrelas_max is not None:
            filtros.append("a.estrelas <= %s")
            params.append(estrelas_max)
        if apenas_avaliados:
            filtros.append("a.avaliado_em IS NOT NULL")
        if responsavel_id:
            filtros.append("a.responsavel_id = %s")
            params.append(responsavel_id)
        if categoria_id:
            filtros.append("t.categoria_id = %s")
            params.append(categoria_id)
        if subcategoria_id:
            filtros.append("t.subcategoria_id = %s")
            params.append(subcategoria_id)

        where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
        offset = (pagina - 1) * por_pagina

        sql = f"""
            SELECT
                a.id, a.ticket_id, a.estrelas, a.comentario,
                a.popup_count, a.avaliado_em, a.expira_em, a.created_at,
                t.numero, t.assunto,
                us.name  AS solicitante_nome,
                ur.name  AS responsavel_nome,
                g.name   AS grupo_nome
            FROM ticket_avaliacoes a
            JOIN tickets t        ON t.id = a.ticket_id
            JOIN users us         ON us.id = a.solicitante_id
            LEFT JOIN users ur    ON ur.id = a.responsavel_id
            LEFT JOIN cpe_grupo g ON g.id  = a.group_id
            {where}
            ORDER BY a.created_at DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(sql, params + [por_pagina, offset])
        rows = cursor.fetchall()

        # total
        cursor.execute(f"SELECT COUNT(*) AS total FROM ticket_avaliacoes a JOIN tickets t ON t.id = a.ticket_id {where}", params)
        total = cursor.fetchone()["total"]

        for r in rows:
            r["avaliado_em"] = _fmt_dt(r["avaliado_em"])
            r["expira_em"]   = _fmt_dt(r["expira_em"])
            r["created_at"]  = _fmt_dt(r["created_at"])

        return {
            "total": total,
            "pagina": pagina,
            "por_pagina": por_pagina,
            "avaliacoes": rows
        }
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# ─── GET /api/avaliacoes/resumo ───────────────────────────────────────────────
@avaliacoes_router.get("/resumo")
async def resumo_avaliacoes(
    usuario_id: int           = Query(..., gt=0),
    grupo_id:   Optional[int] = Query(None),
):
    """KPIs: média, total, distribuição por estrela — para reports.html."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        usuario = _usuario(cursor, usuario_id)
        role    = usuario.get("role") or "USER"
        e_admin = role in ROLES_ADMIN

        if not e_admin and role != "RESPONSAVEL_GRUPO":
            raise HTTPException(status_code=403, detail="Acesso negado.")

        filtros = ["a.avaliado_em IS NOT NULL"]
        params  = []

        if not e_admin:
            filtros.append("a.group_id = %s")
            params.append(usuario.get("group_id"))
        elif grupo_id:
            filtros.append("a.group_id = %s")
            params.append(grupo_id)

        where = "WHERE " + " AND ".join(filtros)

        cursor.execute(f"""
            SELECT
                COUNT(*)             AS total_avaliados,
                ROUND(AVG(estrelas), 2) AS media,
                SUM(estrelas >= 8)   AS positivas,
                SUM(estrelas BETWEEN 4 AND 7) AS neutras,
                SUM(estrelas < 4)    AS negativas
            FROM ticket_avaliacoes a
            {where}
        """, params)
        kpis = cursor.fetchone()

        # Total de tickets com avaliação criada (avaliados + pendentes + expirados)
        cursor.execute(f"""
            SELECT COUNT(*) AS total_criadas,
                   SUM(avaliado_em IS NULL AND expira_em > NOW()) AS pendentes,
                   SUM(avaliado_em IS NULL AND expira_em <= NOW()) AS expiradas
            FROM ticket_avaliacoes a
            {where.replace('a.avaliado_em IS NOT NULL AND', '').replace('AND a.avaliado_em IS NOT NULL', '').replace('WHERE a.avaliado_em IS NOT NULL', 'WHERE 1=1')}
        """, params)
        totais = cursor.fetchone()

        # Distribuição por estrela
        cursor.execute(f"""
            SELECT estrelas, COUNT(*) AS qtd
            FROM ticket_avaliacoes a
            {where}
            GROUP BY estrelas
            ORDER BY estrelas
        """, params)
        distribuicao = {str(r["estrelas"]): r["qtd"] for r in cursor.fetchall()}

        return {
            "media":           float(kpis["media"] or 0),
            "total_avaliados": kpis["total_avaliados"] or 0,
            "positivas":       int(kpis["positivas"] or 0),
            "neutras":         int(kpis["neutras"] or 0),
            "negativas":       int(kpis["negativas"] or 0),
            "pendentes":       int(totais["pendentes"] or 0),
            "expiradas":       int(totais["expiradas"] or 0),
            "distribuicao":    distribuicao,
        }
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# ─── GET /api/avaliacoes/por-responsavel ─────────────────────────────────────
@avaliacoes_router.get("/por-responsavel")
async def avaliacoes_por_responsavel(
    usuario_id: int           = Query(..., gt=0),
    grupo_id:   Optional[int] = Query(None),
    data_inicio:Optional[str] = Query(None),
    data_fim:   Optional[str] = Query(None),
):
    """
    Estatísticas de avaliação agrupadas por responsável.
    Acesso: RESPONSAVEL_GRUPO (só grupo) ou ADMIN.
    """
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        usuario = _usuario(cursor, usuario_id)
        role    = usuario.get("role") or "USER"
        e_admin = role in ROLES_ADMIN

        if not e_admin and role != "RESPONSAVEL_GRUPO":
            raise HTTPException(status_code=403, detail="Acesso negado.")

        filtros = ["a.avaliado_em IS NOT NULL", "a.responsavel_id IS NOT NULL"]
        params  = []

        if not e_admin:
            filtros.append("a.group_id = %s")
            params.append(usuario.get("group_id"))
        elif grupo_id:
            filtros.append("a.group_id = %s")
            params.append(grupo_id)

        if data_inicio:
            filtros.append("a.avaliado_em >= %s")
            params.append(data_inicio + " 00:00:00")
        if data_fim:
            filtros.append("a.avaliado_em <= %s")
            params.append(data_fim + " 23:59:59")

        where = "WHERE " + " AND ".join(filtros)

        cursor.execute(f"""
            SELECT
                a.responsavel_id,
                u.name                           AS responsavel_nome,
                COUNT(*)                         AS total_avaliados,
                ROUND(AVG(a.estrelas), 2)        AS media,
                SUM(a.estrelas >= 8)             AS positivas,
                SUM(a.estrelas BETWEEN 4 AND 7)  AS neutras,
                SUM(a.estrelas < 4)              AS negativas,
                MIN(a.estrelas)                  AS menor_nota,
                MAX(a.estrelas)                  AS maior_nota
            FROM ticket_avaliacoes a
            JOIN users u ON u.id = a.responsavel_id
            {where}
            GROUP BY a.responsavel_id, u.name
            ORDER BY media DESC, total_avaliados DESC
        """, params)
        membros = cursor.fetchall()

        for m in membros:
            m["media"]      = float(m["media"] or 0)
            m["positivas"]  = int(m["positivas"] or 0)
            m["neutras"]    = int(m["neutras"] or 0)
            m["negativas"]  = int(m["negativas"] or 0)
            m["menor_nota"] = int(m["menor_nota"] or 0)
            m["maior_nota"] = int(m["maior_nota"] or 0)

        return {"membros": membros}
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()
