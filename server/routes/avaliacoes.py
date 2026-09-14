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
# 2026-08-25: Relatórios de tickets/avaliações — MANAGER e USER NÃO veem.
# Visão executiva restrita a ADMIN/TI + RESPONSAVEL_GRUPO (só do próprio grupo).
# Regra global documentada em docs/REGRAS_NEGOCIO.md.
ROLES_REPORTS = ("ADMIN", "TI")


# ─── Modelos ──────────────────────────────────────────────────────────────────

class AvaliacaoSubmit(BaseModel):
    usuario_id: int = Field(..., gt=0)
    estrelas:   int = Field(..., ge=1, le=10)
    # 2026-08-24: comentario obrigatorio SEMPRE (era so <4/10). Sem
    # justificativa nao dava pra analisar por que a nota era baixa/alta.
    comentario: str = Field(..., min_length=1, max_length=2000)

    @field_validator("comentario")
    @classmethod
    def comentario_nao_vazio(cls, v, info):
        if not v or not v.strip():
            raise ValueError("Comentário obrigatório em toda avaliação.")
        return v.strip()


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


def _resp_group_ids(cursor, uid: int) -> list:
    """
    Multi-grupo (Fase 2): retorna lista de group_ids em que o user e
    RESPONSAVEL_GRUPO. Fallback pra users.group_id se user_groups vazio.
    """
    cursor.execute(
        "SELECT group_id FROM user_groups "
        "WHERE user_id = %s AND role_in_grp = 'RESPONSAVEL_GRUPO'",
        (uid,),
    )
    rows = cursor.fetchall() or []
    if rows:
        return [r["group_id"] for r in rows]
    # fallback
    cursor.execute("SELECT role, group_id FROM users WHERE id = %s", (uid,))
    u = cursor.fetchone()
    if u and u.get("role") == "RESPONSAVEL_GRUPO" and u.get("group_id"):
        return [u["group_id"]]
    return []


def _filtro_busca_avaliacoes(q: Optional[str]):
    """Filtro por texto (numero do ticket, id alfanumerico, assunto, solicitante).
    Retorna (join_extra, where_frag, params). join_extra vazio se filtro nao ativo.
    Se ativo, garante JOIN em tickets/users pra os campos usados.
    Aceita '#', espacos e case insensitive."""
    if not q or not q.strip():
        return ("", [], [])
    termo = f"%{q.strip().lstrip('#').strip()}%"
    join_extra = (
        " LEFT JOIN tickets t_q ON t_q.id = a.ticket_id"
        " LEFT JOIN users us_q  ON us_q.id = a.solicitante_id"
    )
    frag = (
        "(t_q.numero LIKE %s OR t_q.id_alfanumerica LIKE %s "
        " OR t_q.assunto LIKE %s OR us_q.name LIKE %s OR us_q.email LIKE %s)"
    )
    return (join_extra, [frag], [termo] * 5)


def _aplica_filtro_grupo_avaliacoes(cursor, usuario, grupo_id_query):
    """
    Constroi (fragmento_where, params) para o filtro por grupo em avaliacoes.

    - ADMIN/TI     -> filtra por grupo_id_query se informado, senao nao filtra
    - RESPONSAVEL  -> filtra por seus resp_group_ids. Se grupo_id_query dado
                      E ele responde por esse grupo, filtra so por ele;
                      se dado e ele NAO responde, 403.
    - Nenhum       -> 403

    Retorna (fragmentos: list, params: list). Chamador injeta em WHERE.
    """
    role = (usuario.get("role") or "USER").upper()
    if role in ROLES_REPORTS:
        if grupo_id_query:
            return (["a.group_id = %s"], [grupo_id_query])
        return ([], [])

    resp_gids = _resp_group_ids(cursor, usuario["id"])
    if not resp_gids:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    if grupo_id_query:
        if grupo_id_query not in resp_gids:
            raise HTTPException(status_code=403,
                                detail="Voce nao responde por este grupo.")
        return (["a.group_id = %s"], [grupo_id_query])

    ph = ",".join(["%s"] * len(resp_gids))
    return ([f"a.group_id IN ({ph})"], list(resp_gids))


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
    - Não expirado (dentro do prazo de 7 dias)

    2026-08-25: removido o filtro `popup_count < 2` daqui. Antes, quando
    o popup automatico ja tinha sido exibido 2 vezes, o ticket sumia da
    lista — e o botao "Avaliar" manual da tabela/modal (fluxo novo) nao
    achava a pendente e mostrava "prazo expirou" mesmo dentro do prazo.
    A regra do popup automatico continua valendo, mas agora aplicada no
    FRONT (verificarAvaliacoesPendentes filtra por p.popup_count<2 antes
    de abrir o popup). O campo popup_count continua no response.
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
    q:           Optional[str] = Query(None, description="Busca por numero, ID alfa, assunto, solicitante ou email"),
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
        # Multi-grupo (Fase 2): filtra por group_ids em que ele e RESPONSAVEL
        # (ou por qualquer grupo se ADMIN/TI). MANAGER continua fora do escopo
        # de relatorios (REGRA em docs/REGRAS_NEGOCIO.md).
        _f_g, _p_g = _aplica_filtro_grupo_avaliacoes(cursor, usuario, grupo_id)
        filtros = list(_f_g)
        params  = list(_p_g)

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

        # 2026-09-03: filtro busca livre por ticket/solicitante.
        # Aceita numero (FAT-2026-00231), id alfanumerico (FA0231N6T7),
        # assunto, nome do solicitante ou email. Ignora '#' e case.
        if q and q.strip():
            termo = f"%{q.strip().lstrip('#').strip()}%"
            filtros.append(
                "(t.numero LIKE %s OR t.id_alfanumerica LIKE %s "
                " OR t.assunto LIKE %s OR us.name LIKE %s OR us.email LIKE %s)"
            )
            params.extend([termo] * 5)

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

        # total — precisa dos MESMOS JOINs do query principal quando ha filtro
        # que referencia us/ur/g (2026-09-03: filtro q referencia us.name/email).
        cursor.execute(
            f"""SELECT COUNT(*) AS total
                  FROM ticket_avaliacoes a
                  JOIN tickets t     ON t.id  = a.ticket_id
                  JOIN users us      ON us.id = a.solicitante_id
             LEFT JOIN users ur      ON ur.id = a.responsavel_id
             LEFT JOIN cpe_grupo g   ON g.id  = a.group_id
                  {where}""",
            params,
        )
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
    q:          Optional[str] = Query(None),
):
    """KPIs: média, total, distribuição por estrela — para reports.html.
    2026-09-03: aceita q pra alinhar KPIs com filtro de busca da tabela."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        usuario = _usuario(cursor, usuario_id)
        _f_g, _p_g = _aplica_filtro_grupo_avaliacoes(cursor, usuario, grupo_id)
        filtros = ["a.avaliado_em IS NOT NULL"] + list(_f_g)
        params  = list(_p_g)

        # Busca livre (numero/id/assunto/solicitante/email) exige JOINs extras
        join_q, filtro_q, params_q = _filtro_busca_avaliacoes(q)
        filtros.extend(filtro_q)
        params.extend(params_q)

        where = "WHERE " + " AND ".join(filtros)

        cursor.execute(f"""
            SELECT
                COUNT(*)             AS total_avaliados,
                ROUND(AVG(estrelas), 2) AS media,
                SUM(estrelas >= 8)   AS positivas,
                SUM(estrelas BETWEEN 4 AND 7) AS neutras,
                SUM(estrelas < 4)    AS negativas
            FROM ticket_avaliacoes a
            {join_q}
            {where}
        """, params)
        kpis = cursor.fetchone()

        # Total de tickets com avaliação criada (avaliados + pendentes + expirados)
        cursor.execute(f"""
            SELECT COUNT(*) AS total_criadas,
                   SUM(avaliado_em IS NULL AND expira_em > NOW()) AS pendentes,
                   SUM(avaliado_em IS NULL AND expira_em <= NOW()) AS expiradas
            FROM ticket_avaliacoes a
            {join_q}
            {where.replace('a.avaliado_em IS NOT NULL AND', '').replace('AND a.avaliado_em IS NOT NULL', '').replace('WHERE a.avaliado_em IS NOT NULL', 'WHERE 1=1')}
        """, params)
        totais = cursor.fetchone()

        # Distribuição por estrela
        cursor.execute(f"""
            SELECT estrelas, COUNT(*) AS qtd
            FROM ticket_avaliacoes a
            {join_q}
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


# ─── GET /api/avaliacoes/resumo-por-grupo ────────────────────────────────────
@avaliacoes_router.get("/resumo-por-grupo")
async def resumo_avaliacoes_por_grupo(
    usuario_id: int           = Query(..., gt=0),
    grupo_id:   Optional[int] = Query(None),
    q:          Optional[str] = Query(None),
):
    """Retorna KPIs de avaliacoes AGRUPADOS por grupo.
    Regra (2026-09-03, docs/REGRAS_NEGOCIO.md):
    - ADMIN/TI: se filtro grupo_id ativo, 1 entry desse grupo; senao 1 entry
      consolidada (comportamento historico da "Excelencia do Grupo").
    - RESPONSAVEL_GRUPO: 1 entry por CADA grupo onde ele responde. Se filtro
      grupo_id ativo, so o desse grupo (e valida que ele responde por ele).
    - Resposta: { grupos: [{group_id, group_name, media, total_avaliados,
      positivas, neutras, negativas, pendentes, expiradas, distribuicao}] }.
    """
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        usuario = _usuario(cursor, usuario_id)
        role = (usuario.get("role") or "USER").upper()

        # Determina quais grupos o request tem escopo.
        if role in ROLES_REPORTS:
            # ADMIN/TI: se filtro veio, restringe; senao consolida em 1 entry.
            escopo_gids = [grupo_id] if grupo_id else None  # None = consolidado
        else:
            # RESPONSAVEL_GRUPO: seus grupos (multi-grupo aware)
            resp_gids = _resp_group_ids(cursor, usuario["id"])
            if not resp_gids:
                raise HTTPException(status_code=403, detail="Acesso negado.")
            if grupo_id:
                if grupo_id not in resp_gids:
                    raise HTTPException(status_code=403,
                                        detail="Voce nao responde por este grupo.")
                escopo_gids = [grupo_id]
            else:
                escopo_gids = list(resp_gids)  # todos os grupos dele — 1 entry por grupo

        # Helper interno pra rodar as 3 queries pra um grupo (ou consolidado se gid=None)
        def _kpis_para(gid):
            filtros = ["a.avaliado_em IS NOT NULL"]
            params  = []
            if gid is not None:
                filtros.append("a.group_id = %s")
                params.append(gid)
            join_q, filtro_q, params_q = _filtro_busca_avaliacoes(q)
            filtros.extend(filtro_q)
            params.extend(params_q)
            where = "WHERE " + " AND ".join(filtros)

            cursor.execute(f"""
                SELECT COUNT(*) AS total_avaliados,
                       ROUND(AVG(estrelas), 2) AS media,
                       SUM(estrelas >= 8) AS positivas,
                       SUM(estrelas BETWEEN 4 AND 7) AS neutras,
                       SUM(estrelas < 4) AS negativas
                  FROM ticket_avaliacoes a
                  {join_q}
                  {where}
            """, params)
            k = cursor.fetchone()

            # Pendentes/expiradas — sem filtro avaliado_em (nao avaliadas ainda)
            filtros_pend = []
            params_pend  = []
            if gid is not None:
                filtros_pend.append("a.group_id = %s")
                params_pend.append(gid)
            join_qp, filtro_qp, params_qp = _filtro_busca_avaliacoes(q)
            filtros_pend.extend(filtro_qp)
            params_pend.extend(params_qp)
            where_pend = ("WHERE " + " AND ".join(filtros_pend)) if filtros_pend else ""
            cursor.execute(f"""
                SELECT SUM(avaliado_em IS NULL AND expira_em > NOW()) AS pendentes,
                       SUM(avaliado_em IS NULL AND expira_em <= NOW()) AS expiradas
                  FROM ticket_avaliacoes a
                  {join_qp}
                  {where_pend}
            """, params_pend)
            tp = cursor.fetchone() or {}

            cursor.execute(f"""
                SELECT estrelas, COUNT(*) AS qtd
                  FROM ticket_avaliacoes a
                  {join_q}
                  {where}
                 GROUP BY estrelas
                 ORDER BY estrelas
            """, params)
            dist = {str(r["estrelas"]): r["qtd"] for r in cursor.fetchall()}

            return {
                "media":           float(k["media"] or 0),
                "total_avaliados": int(k["total_avaliados"] or 0),
                "positivas":       int(k["positivas"] or 0),
                "neutras":         int(k["neutras"] or 0),
                "negativas":       int(k["negativas"] or 0),
                "pendentes":       int(tp.get("pendentes") or 0),
                "expiradas":       int(tp.get("expiradas") or 0),
                "distribuicao":    dist,
            }

        grupos_out = []
        if escopo_gids is None:
            # ADMIN sem filtro → 1 entry consolidada (sem group_id/name)
            item = _kpis_para(None)
            item["group_id"]   = None
            item["group_name"] = None
            grupos_out.append(item)
        else:
            for gid in escopo_gids:
                cursor.execute("SELECT id, name FROM cpe_grupo WHERE id = %s", (gid,))
                g = cursor.fetchone() or {}
                item = _kpis_para(gid)
                item["group_id"]   = gid
                item["group_name"] = g.get("name") or f"Grupo #{gid}"
                grupos_out.append(item)

        # Ordena por media desc pra destacar melhores no topo
        grupos_out.sort(key=lambda x: x["media"], reverse=True)
        return {"grupos": grupos_out}
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
    q:          Optional[str] = Query(None),
):
    """
    Estatísticas de avaliação agrupadas por responsável.
    Acesso: RESPONSAVEL_GRUPO (só grupo) ou ADMIN.
    2026-09-03: aceita q pra alinhar KPIs individuais com filtro da tabela.
    """
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        usuario = _usuario(cursor, usuario_id)
        _f_g, _p_g = _aplica_filtro_grupo_avaliacoes(cursor, usuario, grupo_id)
        filtros = ["a.avaliado_em IS NOT NULL",
                   "a.responsavel_id IS NOT NULL"] + list(_f_g)
        params  = list(_p_g)

        if data_inicio:
            filtros.append("a.avaliado_em >= %s")
            params.append(data_inicio + " 00:00:00")
        if data_fim:
            filtros.append("a.avaliado_em <= %s")
            params.append(data_fim + " 23:59:59")

        join_q, filtro_q, params_q = _filtro_busca_avaliacoes(q)
        filtros.extend(filtro_q)
        params.extend(params_q)

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
            {join_q}
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
