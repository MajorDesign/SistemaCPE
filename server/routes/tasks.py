"""
API de Tarefas Diárias (Jira-style)
- Tarefas por grupo com status personalizados
- Etapas que podem envolver múltiplos grupos
- Apenas RESPONSAVEL_GRUPO pode finalizar a tarefa
- Numeração automática: TASK-0001
"""

from fastapi import APIRouter, HTTPException, Query, status, File, UploadFile
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import logging
import sys
import os
import uuid
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_or_404

logger = logging.getLogger(__name__)

tasks_router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

ROLES_ELEVATED = ("RESPONSAVEL_GRUPO", "ADMIN", "TI", "MANAGER")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _fmt(val):
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


def _log(cursor, tarefa_id, usuario_id, acao, detalhe=None, etapa_id=None):
    cursor.execute(
        "INSERT INTO historico_TASK (tarefa_id, etapa_id, usuario_id, acao, detalhe) VALUES (%s,%s,%s,%s,%s)",
        (tarefa_id, etapa_id, usuario_id, acao, detalhe)
    )


def _enrich_tarefa(cursor, t: dict) -> dict:
    cursor.execute("SELECT name FROM cpe_grupo WHERE id = %s", (t["group_id"],))
    g = cursor.fetchone()
    t["group_name"] = g["name"] if g else None

    if t.get("responsavel_id"):
        cursor.execute("SELECT name FROM users WHERE id = %s", (t["responsavel_id"],))
        u = cursor.fetchone()
        t["responsavel_nome"] = u["name"] if u else None
    else:
        t["responsavel_nome"] = None

    if t.get("criador_id"):
        cursor.execute("SELECT name FROM users WHERE id = %s", (t["criador_id"],))
        u = cursor.fetchone()
        t["criador_nome"] = u["name"] if u else None
    else:
        t["criador_nome"] = None

    if t.get("status_id"):
        cursor.execute("SELECT nome, cor, is_final FROM status_TASK WHERE id = %s", (t["status_id"],))
        s = cursor.fetchone()
        t["status_nome"]  = s["nome"]     if s else None
        t["status_cor"]   = s["cor"]      if s else None
        t["status_final"] = s["is_final"] if s else 0
    else:
        t["status_nome"]  = None
        t["status_cor"]   = None
        t["status_final"] = 0

    cursor.execute(
        """SELECT e.id, e.titulo, e.group_id, e.status_id, e.responsavel_id,
                  e.tempo_estimado, e.prazo, e.concluida_em, e.ordem,
                  g.name AS group_name,
                  u.name AS responsavel_nome,
                  s.nome AS status_nome, s.cor AS status_cor
           FROM etapas_TASK e
           LEFT JOIN cpe_grupo g ON g.id = e.group_id
           LEFT JOIN users u ON u.id = e.responsavel_id
           LEFT JOIN status_TASK s ON s.id = e.status_id
           WHERE e.tarefa_id = %s
           ORDER BY e.ordem, e.id""",
        (t["id"],)
    )
    etapas = cursor.fetchall()
    t["etapas"] = [{
        "id": e["id"],
        "titulo": e["titulo"],
        "group_id": e["group_id"],
        "group_name": e["group_name"],
        "status_id": e["status_id"],
        "status_nome": e["status_nome"],
        "status_cor": e["status_cor"],
        "responsavel_id": e["responsavel_id"],
        "responsavel_nome": e["responsavel_nome"],
        "tempo_estimado": e["tempo_estimado"],
        "prazo": _fmt(e["prazo"]),
        "concluida_em": _fmt(e["concluida_em"]),
        "ordem": e["ordem"]
    } for e in etapas]

    total = len(t["etapas"])
    conc  = sum(1 for e in t["etapas"] if e["concluida_em"])
    t["total_etapas"]      = total
    t["etapas_concluidas"] = conc
    t["porcentagem"]       = round(conc / total * 100) if total else 0
    # Progresso combinado (etapas + subtarefas) — calculado após subtarefas serem carregadas

    # Relator
    relator_id = t.get("relator_id") or t.get("criador_id")
    if relator_id:
        cursor.execute("SELECT name FROM users WHERE id = %s", (relator_id,))
        u = cursor.fetchone()
        t["relator_nome"] = u["name"] if u else None
    else:
        t["relator_nome"] = None

    # Subtarefas
    cursor.execute(
        """SELECT s.id, s.titulo, s.concluida, s.concluida_em, s.created_at,
                  u.name AS criador_nome
           FROM subtarefas_TASK s
           LEFT JOIN users u ON u.id = s.criador_id
           WHERE s.tarefa_id = %s ORDER BY s.id""",
        (t["id"],)
    )
    t["subtarefas"] = [{"id": s["id"], "titulo": s["titulo"],
                        "concluida": s["concluida"], "concluida_em": _fmt(s["concluida_em"]),
                        "criador_nome": s["criador_nome"]} for s in cursor.fetchall()]

    # Progresso combinado: etapas concluídas + subtarefas concluídas
    total_itens  = len(t["etapas"]) + len(t["subtarefas"])
    itens_conc   = (sum(1 for e in t["etapas"] if e.get("concluida_em")) +
                    sum(1 for s in t["subtarefas"] if s.get("concluida")))
    t["total_itens"]     = total_itens
    t["itens_concluidos"]= itens_conc
    if total_itens > 0:
        t["porcentagem"] = round(itens_conc / total_itens * 100)

    # Categorias
    cursor.execute(
        """SELECT c.id, c.nome, c.cor
           FROM tarefa_categorias_TASK tc
           JOIN categorias_TASK c ON c.id = tc.categoria_id
           WHERE tc.tarefa_id = %s""",
        (t["id"],)
    )
    t["categorias"] = [{"id": c["id"], "nome": c["nome"], "cor": c["cor"]}
                       for c in cursor.fetchall()]

    # Membros da equipe
    cursor.execute(
        """SELECT u.id, u.name, u.role
           FROM tarefa_membros_TASK tm
           JOIN users u ON u.id = tm.usuario_id
           WHERE tm.tarefa_id = %s""",
        (t["id"],)
    )
    t["membros"] = [{"id": u["id"], "nome": u["name"], "role": u["role"]}
                    for u in cursor.fetchall()]

    # Encaminhamentos entre grupos
    try:
        cursor.execute(
            """SELECT e.id, e.de_grupo_id, e.para_grupo_id, e.encaminhado_por,
                      e.encaminhado_em, e.status_id_origem, e.status_id_retorno,
                      e.devolvido_em, e.devolvido_por, e.motivo_devolucao,
                      dg.name AS de_grupo_nome, pg.name AS para_grupo_nome,
                      u1.name AS encaminhado_por_nome, u2.name AS devolvido_por_nome
               FROM tarefa_encaminhamentos_TASK e
               JOIN cpe_grupo dg ON dg.id = e.de_grupo_id
               JOIN cpe_grupo pg ON pg.id = e.para_grupo_id
               LEFT JOIN users u1 ON u1.id = e.encaminhado_por
               LEFT JOIN users u2 ON u2.id = e.devolvido_por
               WHERE e.tarefa_id = %s
               ORDER BY e.encaminhado_em ASC""",
            (t["id"],)
        )
        encs = cursor.fetchall()
        t["encaminhamentos"] = [{
            "id":                   enc["id"],
            "de_grupo_id":          enc["de_grupo_id"],
            "de_grupo_nome":        enc["de_grupo_nome"],
            "para_grupo_id":        enc["para_grupo_id"],
            "para_grupo_nome":      enc["para_grupo_nome"],
            "encaminhado_por_nome": enc["encaminhado_por_nome"],
            "encaminhado_em":       _fmt(enc["encaminhado_em"]),
            "devolvido_em":         _fmt(enc["devolvido_em"]),
            "devolvido_por_nome":   enc["devolvido_por_nome"],
            "motivo_devolucao":     enc["motivo_devolucao"],
        } for enc in encs]
    except Exception:
        t["encaminhamentos"] = []

    for campo in ("prazo", "concluida_em", "created_at", "updated_at", "start_date"):
        if campo in t:
            t[campo] = _fmt(t[campo])

    return t


# ─── Models ───────────────────────────────────────────────────────────────────

class StatusCreate(BaseModel):
    group_id:   Optional[int] = None          # ADMIN tem group_id=NULL
    usuario_id: int           = Field(..., gt=0)
    espaco_id:  Optional[int] = None
    nome:       str           = Field(..., min_length=1, max_length=100)
    cor:        str           = Field(default="#6b7280", max_length=7)
    icone:      str           = Field(default="bi-circle", max_length=50)
    ordem:      int           = Field(default=0)
    is_final:   int           = Field(default=0, ge=0, le=1)


class StatusUpdate(BaseModel):
    usuario_id: int            = Field(..., gt=0)
    espaco_id:  Optional[int]  = None
    nome:       Optional[str]  = Field(None, min_length=1, max_length=100)
    cor:        Optional[str]  = Field(None, max_length=7)
    icone:      Optional[str]  = Field(None, max_length=50)
    ordem:      Optional[int]  = None
    is_final:   Optional[int]  = Field(None, ge=0, le=1)


class CategoriaCreate(BaseModel):
    usuario_id: int           = Field(..., gt=0)
    espaco_id:  Optional[int] = None
    group_id:   Optional[int] = None
    nome:       str           = Field(..., min_length=1, max_length=100)
    cor:        str           = Field(default="#6554c0", max_length=7)


class SubtarefaCreate(BaseModel):
    criador_id: int = Field(..., gt=0)
    titulo:     str = Field(..., min_length=1, max_length=500)


class SubtarefaUpdate(BaseModel):
    titulo:    Optional[str] = Field(None, min_length=1, max_length=500)
    concluida: Optional[int] = Field(None, ge=0, le=1)


class TempoUpdate(BaseModel):
    usuario_id:     int           = Field(..., gt=0)
    tempo_gasto:    Optional[str] = Field(None, max_length=50)
    tempo_restante: Optional[str] = Field(None, max_length=50)
    start_date:     Optional[str] = None


class TarefaCreate(BaseModel):
    usuario_id:     int           = Field(..., gt=0)
    espaco_id:      Optional[int] = None
    titulo:         str           = Field(..., min_length=1, max_length=255)
    descricao:      Optional[str] = None
    prioridade:     str           = Field(default="media", pattern="^(baixa|media|alta|urgente)$")
    status_id:      Optional[int] = None
    responsavel_id: Optional[int] = None
    tempo_estimado: int           = Field(default=0, ge=0)
    prazo:          Optional[str] = None


class TarefaUpdate(BaseModel):
    usuario_id:     int           = Field(..., gt=0)
    titulo:         Optional[str] = Field(None, min_length=1, max_length=255)
    descricao:      Optional[str] = None
    prioridade:     Optional[str] = Field(None, pattern="^(baixa|media|alta|urgente)$")
    status_id:      Optional[int] = None
    responsavel_id: Optional[int] = None
    tempo_estimado: Optional[int] = Field(None, ge=0)
    prazo:          Optional[str] = None
    start_date:     Optional[str] = None
    cor_card:       Optional[str] = None


class EspacoGrupoAdd(BaseModel):
    usuario_id: int = Field(..., gt=0)
    group_id:   int = Field(..., gt=0)


class SlaUpdate(BaseModel):
    usuario_id: int = Field(..., gt=0)
    slas: list   # [{status_id, sla_minutos}]


class EncaminharBody(BaseModel):
    usuario_id:    int           = Field(..., gt=0)
    para_grupo_id: int           = Field(..., gt=0)
    motivo:        Optional[str] = None


class DevolverBody(BaseModel):
    usuario_id: int           = Field(..., gt=0)
    motivo:     Optional[str] = None


class EtapaCreate(BaseModel):
    usuario_id:     int           = Field(..., gt=0)
    group_id:       int           = Field(..., gt=0)
    titulo:         str           = Field(..., min_length=1, max_length=255)
    descricao:      Optional[str] = None
    status_id:      Optional[int] = None
    responsavel_id: Optional[int] = None
    tempo_estimado: int           = Field(default=0, ge=0)
    prazo:          Optional[str] = None
    ordem:          int           = Field(default=0)


class EtapaUpdate(BaseModel):
    usuario_id:     int           = Field(..., gt=0)
    titulo:         Optional[str] = Field(None, min_length=1, max_length=255)
    descricao:      Optional[str] = None
    status_id:      Optional[int] = None
    responsavel_id: Optional[int] = None
    tempo_estimado: Optional[int] = Field(None, ge=0)
    prazo:          Optional[str] = None


class ComentarioCreate(BaseModel):
    autor_id: int           = Field(..., gt=0)
    etapa_id: Optional[int] = None
    texto:    str           = Field(..., min_length=1, max_length=60000)


# ─── STATUS ───────────────────────────────────────────────────────────────────

@tasks_router.get("/status")
def listar_status(group_id: int = Query(..., gt=0), usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        cursor.execute(
            "SELECT * FROM status_TASK WHERE group_id = %s ORDER BY ordem, id",
            (group_id,)
        )
        rows = cursor.fetchall()
        return [{"id": r["id"], "group_id": r["group_id"], "nome": r["nome"],
                 "cor": r["cor"], "icone": r["icone"], "ordem": r["ordem"],
                 "is_final": r["is_final"]} for r in rows]
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.post("/status", status_code=201)
def criar_status(body: StatusCreate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, body.usuario_id)
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Apenas gestores podem criar status.")
        # RESPONSAVEL_GRUPO só pode criar status para o próprio grupo
        if u["role"] == "RESPONSAVEL_GRUPO" and body.group_id and u["group_id"] != body.group_id:
            raise HTTPException(403, "Acesso negado a este grupo.")

        # Usar group_id do usuário como fallback se não fornecido
        effective_group_id = body.group_id or u["group_id"]

        cursor.execute(
            "INSERT INTO status_TASK (group_id, espaco_id, nome, cor, icone, ordem, is_final) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (effective_group_id, body.espaco_id, body.nome, body.cor, body.icone, body.ordem, body.is_final)
        )
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM status_TASK WHERE id = %s", (new_id,))
        r = cursor.fetchone()
        return {"id": r["id"], "group_id": r["group_id"], "espaco_id": r.get("espaco_id"),
                "nome": r["nome"], "cor": r["cor"], "icone": r["icone"],
                "ordem": r["ordem"], "is_final": r["is_final"]}
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.put("/status/{status_id}")
def atualizar_status(status_id: int, body: StatusUpdate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, body.usuario_id)
        cursor.execute("SELECT * FROM status_TASK WHERE id = %s", (status_id,))
        s = cursor.fetchone()
        if not s:
            raise HTTPException(404, "Status não encontrado.")
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Apenas gestores podem editar status.")
        if u["role"] == "RESPONSAVEL_GRUPO":
            cursor.execute(
                "SELECT 1 FROM espaco_grupos_TASK WHERE espaco_id=%s AND group_id=%s",
                (s["espaco_id"], u["group_id"])
            )
            if not cursor.fetchone():
                raise HTTPException(403, "Seu grupo não faz parte deste espaço.")

        sets, vals = [], []
        if body.nome     is not None: sets.append("nome=%s");     vals.append(body.nome)
        if body.cor      is not None: sets.append("cor=%s");      vals.append(body.cor)
        if body.icone    is not None: sets.append("icone=%s");    vals.append(body.icone)
        if body.ordem    is not None: sets.append("ordem=%s");    vals.append(body.ordem)
        if body.is_final is not None: sets.append("is_final=%s"); vals.append(body.is_final)

        if sets:
            vals.append(status_id)
            cursor.execute(f"UPDATE status_TASK SET {', '.join(sets)} WHERE id = %s", vals)
            conn.commit()

        cursor.execute("SELECT * FROM status_TASK WHERE id = %s", (status_id,))
        r = cursor.fetchone()
        return {"id": r["id"], "group_id": r["group_id"], "nome": r["nome"],
                "cor": r["cor"], "icone": r["icone"], "ordem": r["ordem"],
                "is_final": r["is_final"]}
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.delete("/status/{status_id}", status_code=204)
def deletar_status(status_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, usuario_id)
        cursor.execute("SELECT * FROM status_TASK WHERE id = %s", (status_id,))
        s = cursor.fetchone()
        if not s:
            raise HTTPException(404, "Status não encontrado.")
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Apenas gestores podem deletar status.")
        if u["role"] == "RESPONSAVEL_GRUPO" and u["group_id"] != s["group_id"]:
            raise HTTPException(403, "Acesso negado.")

        cursor.execute("SELECT COUNT(*) AS n FROM tarefas_TASK WHERE status_id = %s", (status_id,))
        n1 = cursor.fetchone()["n"]
        cursor.execute("SELECT COUNT(*) AS n FROM etapas_TASK WHERE status_id = %s", (status_id,))
        n2 = cursor.fetchone()["n"]
        if n1 + n2 > 0:
            raise HTTPException(400, "Status em uso por tarefas ou etapas.")

        cursor.execute("DELETE FROM status_TASK WHERE id = %s", (status_id,))
        conn.commit()
    finally:
        if cursor: cursor.close()
        conn.close()


# ─── ESPAÇOS ─────────────────────────────────────────────────────────────────
# IMPORTANTE: estas rotas devem estar ANTES de /{tarefa_id} para não conflitar

TEMPLATE_STATUSES = {
    'tarefa': [
        {'nome': 'A Fazer',  'cor': '#6b7280', 'icone': 'bi-circle',             'ordem': 0, 'is_final': 0},
        {'nome': 'Fazendo',  'cor': '#f59e0b', 'icone': 'bi-arrow-right-circle', 'ordem': 1, 'is_final': 0},
        {'nome': 'Feito',    'cor': '#10b981', 'icone': 'bi-check-circle',       'ordem': 2, 'is_final': 1},
    ],
    'kanban': [
        {'nome': 'Backlog',       'cor': '#6b7280', 'icone': 'bi-inbox',             'ordem': 0, 'is_final': 0},
        {'nome': 'A Fazer',       'cor': '#3b82f6', 'icone': 'bi-circle',            'ordem': 1, 'is_final': 0},
        {'nome': 'Em Andamento',  'cor': '#f59e0b', 'icone': 'bi-arrow-right-circle','ordem': 2, 'is_final': 0},
        {'nome': 'Concluído',     'cor': '#10b981', 'icone': 'bi-check-circle',      'ordem': 3, 'is_final': 1},
    ],
    'scrum': [
        {'nome': 'Backlog',      'cor': '#6b7280', 'icone': 'bi-inbox',             'ordem': 0, 'is_final': 0},
        {'nome': 'Sprint',       'cor': '#3b82f6', 'icone': 'bi-lightning-charge',  'ordem': 1, 'is_final': 0},
        {'nome': 'Em Andamento', 'cor': '#f59e0b', 'icone': 'bi-arrow-right-circle','ordem': 2, 'is_final': 0},
        {'nome': 'Revisão',      'cor': '#8b5cf6', 'icone': 'bi-eye',               'ordem': 3, 'is_final': 0},
        {'nome': 'Concluído',    'cor': '#10b981', 'icone': 'bi-check-circle',      'ordem': 4, 'is_final': 1},
    ],
    'gestao': [
        {'nome': 'Planejado',    'cor': '#6b7280', 'icone': 'bi-calendar',          'ordem': 0, 'is_final': 0},
        {'nome': 'Em Andamento', 'cor': '#3b82f6', 'icone': 'bi-arrow-right-circle','ordem': 1, 'is_final': 0},
        {'nome': 'Bloqueado',    'cor': '#ef4444', 'icone': 'bi-x-circle',          'ordem': 2, 'is_final': 0},
        {'nome': 'Concluído',    'cor': '#10b981', 'icone': 'bi-check-circle',      'ordem': 3, 'is_final': 1},
    ],
}


class EspacoCreate(BaseModel):
    usuario_id:    int           = Field(..., gt=0)
    nome:          str           = Field(..., min_length=1, max_length=255)
    chave:         str           = Field(..., min_length=1, max_length=20)
    template:      str           = Field(default='tarefa')
    template_id:   Optional[int] = Field(default=None)  # ID de template salvo no banco
    gerenciado_por:str           = Field(default='equipe')
    cor:           Optional[str] = Field(default='#6554c0', max_length=7)
    membros:       Optional[list]= Field(default=[])  # [{usuario_id, funcao}]


class EspacoMembrosAdd(BaseModel):
    usuario_id: int  = Field(..., gt=0)
    funcao:     str  = Field(default='membro')


@tasks_router.get("/espacos")
def listar_espacos(usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, usuario_id)

        # Admin/TI vê todos; outros veem os do próprio grupo + onde foram convidados e aceitaram
        if u["role"] in ("ADMIN", "TI", "MANAGER"):
            cursor.execute("SELECT e.* FROM espacos_TASK e ORDER BY e.created_at DESC")
        else:
            cursor.execute(
                """SELECT DISTINCT e.* FROM espacos_TASK e
                   WHERE e.group_id = %s
                      OR e.criador_id = %s
                      OR EXISTS(SELECT 1 FROM espaco_membros_TASK m WHERE m.espaco_id=e.id AND m.usuario_id=%s)
                      OR EXISTS(SELECT 1 FROM espaco_grupos_TASK eg WHERE eg.espaco_id=e.id AND eg.group_id=%s)
                   ORDER BY e.created_at DESC""",
                (u["group_id"], usuario_id, usuario_id, u["group_id"])
            )
        espacos = cursor.fetchall()
        result = []
        for esp in espacos:
            e = dict(esp)
            e["created_at"] = _fmt(e["created_at"])
            # contagem de membros
            cursor.execute("SELECT COUNT(*) AS n FROM espaco_membros_TASK WHERE espaco_id=%s", (e["id"],))
            e["total_membros"] = cursor.fetchone()["n"]
            # statuses
            cursor.execute(
                "SELECT id,group_id,nome,cor,icone,ordem,is_final FROM status_TASK WHERE espaco_id=%s ORDER BY ordem",
                (e["id"],)
            )
            e["statuses"] = cursor.fetchall()
            result.append(e)
        return result
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.post("/espacos", status_code=201)
def criar_espaco(body: EspacoCreate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, body.usuario_id)
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Apenas gestores podem criar espaços.")

        template = body.template if body.template in TEMPLATE_STATUSES else 'tarefa'
        chave = body.chave.upper().replace(' ', '')[:20]

        # Se template_id fornecido, buscar cor do template salvo
        template_cor = body.cor or '#6554c0'
        saved_statuses = None
        if body.template_id:
            cursor.execute("SELECT * FROM templates_espaco_TASK WHERE id=%s", (body.template_id,))
            tpl = cursor.fetchone()
            if tpl:
                template_cor = body.cor or tpl["cor"]
                cursor.execute(
                    "SELECT nome, cor, icone, ordem, is_final FROM template_statuses_TASK WHERE template_id=%s ORDER BY ordem",
                    (body.template_id,)
                )
                saved_statuses = cursor.fetchall()

        cursor.execute(
            """INSERT INTO espacos_TASK (nome, chave, template, gerenciado_por, group_id, criador_id, cor)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (body.nome, chave, template, body.gerenciado_por,
             u["group_id"], body.usuario_id, template_cor)
        )
        conn.commit()
        espaco_id = cursor.lastrowid

        # Adicionar criador como administrador
        cursor.execute(
            "INSERT IGNORE INTO espaco_membros_TASK (espaco_id, usuario_id, funcao) VALUES (%s,%s,'administrador')",
            (espaco_id, body.usuario_id)
        )

        # Adicionar grupo do criador como participante automático
        if u["group_id"]:
            cursor.execute(
                "INSERT IGNORE INTO espaco_grupos_TASK (espaco_id, group_id, adicionado_por) VALUES (%s,%s,%s)",
                (espaco_id, u["group_id"], body.usuario_id)
            )

        # Criar statuses — do template salvo ou do template padrão
        status_list = saved_statuses if saved_statuses else TEMPLATE_STATUSES[template]
        for s in status_list:
            cursor.execute(
                """INSERT INTO status_TASK (group_id, espaco_id, nome, cor, icone, ordem, is_final)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (u["group_id"], espaco_id,
                 s['nome'], s['cor'], s.get('icone', 'bi-circle'), s['ordem'], s['is_final'])
            )

        # Adicionar membros opcionais
        if body.membros:
            cursor.execute("SELECT nome FROM espacos_TASK WHERE id=%s", (espaco_id,))
            _esp = cursor.fetchone()
            _esp_nome = _esp["nome"] if _esp else body.nome
            for m in body.membros:
                uid = m.get('usuario_id')
                funcao = m.get('funcao', 'membro')
                if uid and uid != body.usuario_id:
                    cursor.execute(
                        "INSERT IGNORE INTO espaco_membros_TASK (espaco_id, usuario_id, funcao) VALUES (%s,%s,%s)",
                        (espaco_id, uid, funcao)
                    )
                    cursor.execute(
                        """INSERT INTO notificacoes (ticket_id, usuario_id, mensagem, tipo, lido, created_at)
                           VALUES (NULL, %s, %s, 'convite_task', 0, NOW())""",
                        (uid, f'Você foi adicionado ao quadro "{_esp_nome}". Acesse Tarefas para ver.')
                    )

        conn.commit()

        cursor.execute("SELECT * FROM espacos_TASK WHERE id=%s", (espaco_id,))
        e = dict(cursor.fetchone())
        e["created_at"] = _fmt(e["created_at"])
        cursor.execute(
            "SELECT id,nome,cor,icone,ordem,is_final FROM status_TASK WHERE espaco_id=%s ORDER BY ordem",
            (espaco_id,)
        )
        e["statuses"] = cursor.fetchall()
        e["total_membros"] = len(body.membros) + 1
        return e
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.get("/espacos/{espaco_id}/membros")
def listar_membros_espaco(espaco_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        cursor.execute(
            """SELECT m.id, m.usuario_id, m.funcao, m.created_at,
                      u.name, u.email, u.role
               FROM espaco_membros_TASK m
               LEFT JOIN users u ON u.id = m.usuario_id
               WHERE m.espaco_id = %s ORDER BY m.funcao, u.name""",
            (espaco_id,)
        )
        rows = cursor.fetchall()
        return [{"id": r["id"], "usuario_id": r["usuario_id"], "nome": r["name"],
                 "email": r["email"], "role": r["role"], "funcao": r["funcao"],
                 "created_at": _fmt(r["created_at"])} for r in rows]
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.post("/espacos/{espaco_id}/membros", status_code=201)
def adicionar_membro_espaco(espaco_id: int, body: EspacoMembrosAdd):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, body.usuario_id)
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Apenas gestores podem adicionar membros.")
        cursor.execute(
            "INSERT IGNORE INTO espaco_membros_TASK (espaco_id, usuario_id, funcao) VALUES (%s,%s,%s)",
            (espaco_id, body.usuario_id, body.funcao)
        )
        conn.commit()
        return {"ok": True}
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.delete("/espacos/{espaco_id}/membros/{uid}", status_code=204)
def remover_membro_espaco(espaco_id: int, uid: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, usuario_id)
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Apenas gestores podem remover membros.")
        cursor.execute(
            "DELETE FROM espaco_membros_TASK WHERE espaco_id=%s AND usuario_id=%s",
            (espaco_id, uid)
        )
        conn.commit()
    finally:
        if cursor: cursor.close()
        conn.close()


# ─── ESPAÇO: GRUPOS PARTICIPANTES ────────────────────────────────────────────

@tasks_router.delete("/espacos/{espaco_id}", status_code=204)
def excluir_espaco(espaco_id: int, usuario_id: int = Query(..., gt=0)):
    """Exclui um espaço inteiro e todos os dados relacionados."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, usuario_id)

        # Só ADMIN, TI ou RESPONSAVEL_GRUPO (do grupo criador) pode excluir
        cursor.execute("SELECT * FROM espacos_TASK WHERE id=%s", (espaco_id,))
        esp = cursor.fetchone()
        if not esp:
            raise HTTPException(404, "Espaço não encontrado.")

        if u["role"] not in ("ADMIN", "TI"):
            if u["role"] == "RESPONSAVEL_GRUPO":
                if u["group_id"] != esp["group_id"]:
                    raise HTTPException(403, "Você só pode excluir quadros do seu grupo.")
            else:
                raise HTTPException(403, "Sem permissão para excluir quadros.")

        # Buscar todas as tarefas do espaço para limpar dependências
        cursor.execute("SELECT id FROM tarefas_TASK WHERE espaco_id=%s", (espaco_id,))
        tarefa_ids = [r["id"] for r in cursor.fetchall()]

        if tarefa_ids:
            placeholders = ','.join(['%s'] * len(tarefa_ids))
            # Deletar dependências das tarefas
            for tbl in ("comentarios_TASK", "historico_TASK", "subtarefas_TASK",
                        "etapas_TASK", "tarefa_categorias_TASK", "tarefa_historico_status_TASK"):
                try:
                    cursor.execute(f"DELETE FROM {tbl} WHERE tarefa_id IN ({placeholders})", tarefa_ids)
                except Exception:
                    pass  # Tabela pode não existir

            # Deletar tarefas
            cursor.execute(f"DELETE FROM tarefas_TASK WHERE espaco_id=%s", (espaco_id,))

        # Deletar dados do espaço
        cursor.execute("DELETE FROM status_TASK WHERE espaco_id=%s", (espaco_id,))
        cursor.execute("DELETE FROM espaco_membros_TASK WHERE espaco_id=%s", (espaco_id,))
        cursor.execute("DELETE FROM espaco_grupos_TASK WHERE espaco_id=%s", (espaco_id,))
        cursor.execute("DELETE FROM espaco_grupo_sla_TASK WHERE espaco_id=%s", (espaco_id,))
        cursor.execute("DELETE FROM convites_espaco_TASK WHERE espaco_id=%s", (espaco_id,))

        # Deletar o espaço
        cursor.execute("DELETE FROM espacos_TASK WHERE id=%s", (espaco_id,))
        conn.commit()

        logging.info(f"[ESPACO] Espaço #{espaco_id} excluído por user #{usuario_id}")
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.get("/espacos/{espaco_id}/grupos")
def listar_grupos_espaco(espaco_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        cursor.execute(
            """SELECT eg.group_id, g.name AS group_name, eg.adicionado_em,
                      u.name AS adicionado_por_nome
               FROM espaco_grupos_TASK eg
               LEFT JOIN cpe_grupo g ON g.id = eg.group_id
               LEFT JOIN users u ON u.id = eg.adicionado_por
               WHERE eg.espaco_id = %s
               ORDER BY g.name""",
            (espaco_id,)
        )
        grupos = cursor.fetchall()
        result = []
        for gr in grupos:
            # Carregar SLAs deste grupo neste espaço
            cursor.execute(
                """SELECT s.id AS status_id, s.nome AS status_nome, s.cor AS status_cor,
                          COALESCE(sl.sla_minutos, 0) AS sla_minutos
                   FROM status_TASK s
                   LEFT JOIN espaco_grupo_sla_TASK sl
                     ON sl.espaco_id=%s AND sl.group_id=%s AND sl.status_id=s.id
                   WHERE s.espaco_id=%s
                   ORDER BY s.ordem""",
                (espaco_id, gr["group_id"], espaco_id)
            )
            slas = cursor.fetchall()
            result.append({
                "group_id":           gr["group_id"],
                "group_name":         gr["group_name"],
                "adicionado_em":      _fmt(gr["adicionado_em"]),
                "adicionado_por_nome":gr["adicionado_por_nome"],
                "slas":               [{"status_id": s["status_id"], "status_nome": s["status_nome"],
                                        "status_cor": s["status_cor"], "sla_minutos": s["sla_minutos"]}
                                       for s in slas],
            })
        return result
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.post("/espacos/{espaco_id}/grupos", status_code=201)
def convidar_grupo_espaco(espaco_id: int, body: EspacoGrupoAdd):
    """Envia convite para um grupo participar do espaço."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, body.usuario_id)
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Apenas gestores podem convidar grupos.")

        # Verificar se já participa
        cursor.execute(
            "SELECT 1 FROM espaco_grupos_TASK WHERE espaco_id=%s AND group_id=%s",
            (espaco_id, body.group_id)
        )
        if cursor.fetchone():
            raise HTTPException(400, "Este grupo já participa deste quadro.")

        # Verificar se já tem convite pendente
        cursor.execute(
            "SELECT id FROM convites_espaco_TASK WHERE espaco_id=%s AND group_id=%s AND status='pendente'",
            (espaco_id, body.group_id)
        )
        if cursor.fetchone():
            raise HTTPException(400, "Já existe um convite pendente para este grupo.")

        # Criar convite
        cursor.execute(
            "INSERT INTO convites_espaco_TASK (espaco_id, group_id, convidado_por) VALUES (%s,%s,%s)",
            (espaco_id, body.group_id, body.usuario_id)
        )
        convite_id = cursor.lastrowid

        # Buscar dados do espaço para a notificação
        cursor.execute("SELECT nome FROM espacos_TASK WHERE id=%s", (espaco_id,))
        esp = cursor.fetchone()
        esp_nome = esp["nome"] if esp else f"Espaço #{espaco_id}"

        # Notificar todos os membros ativos do grupo convidado
        cursor.execute(
            "SELECT id, name FROM users WHERE group_id=%s AND (is_active IS NULL OR is_active=1)",
            (body.group_id,)
        )
        membros_grupo = cursor.fetchall()
        for resp in membros_grupo:
            cursor.execute(
                """INSERT INTO notificacoes (ticket_id, usuario_id, mensagem, tipo, lido, created_at)
                   VALUES (NULL, %s, %s, %s, 0, NOW())""",
                (resp["id"],
                 f"Seu grupo foi convidado para participar do quadro \"{esp_nome}\". Acesse Tarefas para aceitar ou recusar.",
                 "convite_task")
            )

        conn.commit()
        notificados = len(membros_grupo)
        msg = f"Convite enviado com sucesso! ({notificados} membro(s) notificado(s))"
        if notificados == 0:
            msg = "Convite enviado, porém o grupo não possui membros ativos para notificar."
        return {"ok": True, "convite_id": convite_id, "message": msg}
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.get("/espacos/{espaco_id}/convites-pendentes")
def listar_convites_espaco(espaco_id: int, usuario_id: int = Query(..., gt=0)):
    """Lista convites pendentes enviados para um espaço (visão do gestor)."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, usuario_id)
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Sem permissão.")
        cursor.execute(
            """SELECT c.id, c.group_id, c.status, c.created_at,
                      g.name AS group_name,
                      u.name AS convidado_por_nome
               FROM convites_espaco_TASK c
               LEFT JOIN cpe_grupo g ON g.id = c.group_id
               LEFT JOIN users u ON u.id = c.convidado_por
               WHERE c.espaco_id = %s AND c.status = 'pendente'
               ORDER BY c.created_at DESC""",
            (espaco_id,)
        )
        rows = cursor.fetchall()
        return [{"id": r["id"], "group_id": r["group_id"], "group_name": r["group_name"],
                 "convidado_por_nome": r["convidado_por_nome"], "created_at": _fmt(r["created_at"])}
                for r in rows]
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.delete("/convites/{convite_id}")
def cancelar_convite(convite_id: int, usuario_id: int = Query(..., gt=0)):
    """Cancela (remove) um convite pendente."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, usuario_id)
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Sem permissão para cancelar convites.")
        cursor.execute(
            "SELECT id FROM convites_espaco_TASK WHERE id=%s AND status='pendente'",
            (convite_id,)
        )
        if not cursor.fetchone():
            raise HTTPException(404, "Convite não encontrado ou já respondido.")
        # DELETE em vez de UPDATE status='cancelado': o ENUM da tabela não inclui
        # 'cancelado', então um UPDATE causaria string vazia e violação de UNIQUE KEY.
        cursor.execute("DELETE FROM convites_espaco_TASK WHERE id=%s", (convite_id,))
        conn.commit()
        return {"ok": True, "message": "Convite cancelado."}
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.get("/convites")
def listar_convites(usuario_id: int = Query(..., gt=0)):
    """Lista convites pendentes para o grupo do usuário."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, usuario_id)
        gid = u["group_id"]
        if not gid:
            return []  # ADMIN sem grupo

        cursor.execute(
            """SELECT c.id, c.espaco_id, c.group_id, c.status, c.created_at,
                      e.nome AS espaco_nome, e.cor AS espaco_cor, e.chave AS espaco_chave,
                      u.name AS convidado_por_nome
               FROM convites_espaco_TASK c
               LEFT JOIN espacos_TASK e ON e.id = c.espaco_id
               LEFT JOIN users u ON u.id = c.convidado_por
               WHERE c.group_id = %s AND c.status = 'pendente'
               ORDER BY c.created_at DESC""",
            (gid,)
        )
        rows = cursor.fetchall()
        return [{
            "id": r["id"],
            "espaco_id": r["espaco_id"],
            "espaco_nome": r["espaco_nome"],
            "espaco_cor": r["espaco_cor"],
            "espaco_chave": r["espaco_chave"],
            "convidado_por_nome": r["convidado_por_nome"],
            "created_at": _fmt(r["created_at"]),
        } for r in rows]
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.put("/convites/{convite_id}/aceitar")
def aceitar_convite(convite_id: int, usuario_id: int = Query(..., gt=0)):
    """Aceita um convite — adiciona o grupo ao espaço."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, usuario_id)

        cursor.execute("SELECT * FROM convites_espaco_TASK WHERE id=%s AND status='pendente'", (convite_id,))
        convite = cursor.fetchone()
        if not convite:
            raise HTTPException(404, "Convite não encontrado ou já respondido.")

        # Verificar se o usuário pertence ao grupo convidado (ou é ADMIN)
        if u["role"] not in ("ADMIN", "TI") and u["group_id"] != convite["group_id"]:
            raise HTTPException(403, "Você não pode responder a este convite.")

        # Atualizar convite
        cursor.execute(
            "UPDATE convites_espaco_TASK SET status='aceito', respondido_em=NOW(), respondido_por=%s WHERE id=%s",
            (usuario_id, convite_id)
        )

        # Adicionar grupo ao espaço
        cursor.execute(
            "INSERT IGNORE INTO espaco_grupos_TASK (espaco_id, group_id, adicionado_por) VALUES (%s,%s,%s)",
            (convite["espaco_id"], convite["group_id"], usuario_id)
        )

        # Notificar quem convidou
        cursor.execute("SELECT nome FROM espacos_TASK WHERE id=%s", (convite["espaco_id"],))
        esp = cursor.fetchone()
        cursor.execute("SELECT name FROM cpe_grupo WHERE id=%s", (convite["group_id"],))
        grp = cursor.fetchone()
        cursor.execute(
            """INSERT INTO notificacoes (ticket_id, usuario_id, mensagem, tipo, lido, created_at)
               VALUES (NULL, %s, %s, %s, 0, NOW())""",
            (convite["convidado_por"],
             f"O grupo \"{grp['name'] if grp else '?'}\" aceitou o convite para o quadro \"{esp['nome'] if esp else '?'}\".",
             "convite_aceito_task")
        )

        conn.commit()
        return {"ok": True, "espaco_id": convite["espaco_id"], "message": "Convite aceito! O grupo agora participa do quadro."}
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.put("/convites/{convite_id}/recusar")
def recusar_convite(convite_id: int, usuario_id: int = Query(..., gt=0)):
    """Recusa um convite."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, usuario_id)

        cursor.execute("SELECT * FROM convites_espaco_TASK WHERE id=%s AND status='pendente'", (convite_id,))
        convite = cursor.fetchone()
        if not convite:
            raise HTTPException(404, "Convite não encontrado ou já respondido.")

        if u["role"] not in ("ADMIN", "TI") and u["group_id"] != convite["group_id"]:
            raise HTTPException(403, "Você não pode responder a este convite.")

        cursor.execute(
            "UPDATE convites_espaco_TASK SET status='recusado', respondido_em=NOW(), respondido_por=%s WHERE id=%s",
            (usuario_id, convite_id)
        )

        # Notificar quem convidou
        cursor.execute("SELECT nome FROM espacos_TASK WHERE id=%s", (convite["espaco_id"],))
        esp = cursor.fetchone()
        cursor.execute("SELECT name FROM cpe_grupo WHERE id=%s", (convite["group_id"],))
        grp = cursor.fetchone()
        cursor.execute(
            """INSERT INTO notificacoes (ticket_id, usuario_id, mensagem, tipo, lido, created_at)
               VALUES (NULL, %s, %s, %s, 0, NOW())""",
            (convite["convidado_por"],
             f"O grupo \"{grp['name'] if grp else '?'}\" recusou o convite para o quadro \"{esp['nome'] if esp else '?'}\".",
             "convite_recusado_task")
        )

        conn.commit()
        return {"ok": True, "message": "Convite recusado."}
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.delete("/espacos/{espaco_id}/grupos/{group_id}", status_code=204)
def remover_grupo_espaco(espaco_id: int, group_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, usuario_id)
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Apenas gestores podem remover grupos.")
        cursor.execute(
            "DELETE FROM espaco_grupos_TASK WHERE espaco_id=%s AND group_id=%s",
            (espaco_id, group_id)
        )
        cursor.execute(
            "DELETE FROM espaco_grupo_sla_TASK WHERE espaco_id=%s AND group_id=%s",
            (espaco_id, group_id)
        )
        # Limpar convite aceito
        cursor.execute(
            "DELETE FROM convites_espaco_TASK WHERE espaco_id=%s AND group_id=%s",
            (espaco_id, group_id)
        )
        conn.commit()
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.put("/espacos/{espaco_id}/grupos/{group_id}/sla")
def atualizar_sla_grupo(espaco_id: int, group_id: int, body: SlaUpdate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, body.usuario_id)
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Apenas gestores podem definir SLA.")
        # RESPONSAVEL_GRUPO só pode definir SLA do seu próprio grupo
        if u["role"] == "RESPONSAVEL_GRUPO" and u["group_id"] != group_id:
            raise HTTPException(403, "Você só pode definir SLA do seu próprio grupo.")
        for item in body.slas:
            sid = item.get("status_id")
            mins = int(item.get("sla_minutos", 0))
            if not sid:
                continue
            cursor.execute(
                """INSERT INTO espaco_grupo_sla_TASK (espaco_id, group_id, status_id, sla_minutos)
                   VALUES (%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE sla_minutos=%s""",
                (espaco_id, group_id, sid, mins, mins)
            )
        conn.commit()
        return {"ok": True}
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.get("/espacos/{espaco_id}/relatorio-grupos")
def relatorio_grupos(espaco_id: int, usuario_id: int = Query(..., gt=0)):
    """Retorna quanto tempo cada grupo ficou em cada coluna, com breakdown por usuário."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)

        # Grupos participantes
        cursor.execute(
            """SELECT eg.group_id, g.name AS group_name
               FROM espaco_grupos_TASK eg
               LEFT JOIN cpe_grupo g ON g.id=eg.group_id
               WHERE eg.espaco_id=%s ORDER BY g.name""",
            (espaco_id,)
        )
        grupos = cursor.fetchall()

        # Statuses do espaço
        cursor.execute(
            "SELECT id, nome, cor FROM status_TASK WHERE espaco_id=%s ORDER BY ordem",
            (espaco_id,)
        )
        statuses = cursor.fetchall()

        result = []
        for gr in grupos:
            gid = gr["group_id"]
            colunas = []
            for st in statuses:
                sid = st["id"]
                # Totais do grupo nesta coluna
                cursor.execute(
                    """SELECT COUNT(*) AS total_entradas,
                              SUM(TIMESTAMPDIFF(MINUTE, entrou_em, COALESCE(saiu_em, UTC_TIMESTAMP()))) AS total_minutos,
                              AVG(TIMESTAMPDIFF(MINUTE, entrou_em, COALESCE(saiu_em, UTC_TIMESTAMP()))) AS media_minutos
                       FROM tarefa_historico_status_TASK
                       WHERE status_id=%s AND responsavel_group_id=%s
                         AND tarefa_id IN (SELECT id FROM tarefas_TASK WHERE espaco_id=%s)""",
                    (sid, gid, espaco_id)
                )
                stat = cursor.fetchone()
                # SLA definido para este grupo nesta coluna
                cursor.execute(
                    "SELECT sla_minutos FROM espaco_grupo_sla_TASK WHERE espaco_id=%s AND group_id=%s AND status_id=%s",
                    (espaco_id, gid, sid)
                )
                sla_row = cursor.fetchone()
                sla_min = sla_row["sla_minutos"] if sla_row else 0
                total_min = int(stat["total_minutos"] or 0)
                media_min = round(float(stat["media_minutos"] or 0), 1)

                # Breakdown por usuário nesta coluna
                cursor.execute(
                    """SELECT h.responsavel_id, u.name AS user_name,
                              COUNT(*) AS total_entradas,
                              SUM(TIMESTAMPDIFF(MINUTE, h.entrou_em, COALESCE(h.saiu_em, UTC_TIMESTAMP()))) AS total_minutos
                       FROM tarefa_historico_status_TASK h
                       LEFT JOIN users u ON u.id = h.responsavel_id
                       WHERE h.status_id=%s AND h.responsavel_group_id=%s
                         AND h.tarefa_id IN (SELECT id FROM tarefas_TASK WHERE espaco_id=%s)
                         AND h.responsavel_id IS NOT NULL
                       GROUP BY h.responsavel_id, u.name
                       ORDER BY total_minutos DESC""",
                    (sid, gid, espaco_id)
                )
                usuarios_rows = cursor.fetchall()
                usuarios = [
                    {
                        "user_id":        r["responsavel_id"],
                        "user_name":      r["user_name"] or f"Usuário {r['responsavel_id']}",
                        "total_entradas": r["total_entradas"],
                        "total_minutos":  int(r["total_minutos"] or 0),
                    }
                    for r in usuarios_rows
                ]

                colunas.append({
                    "status_id":      sid,
                    "status_nome":    st["nome"],
                    "status_cor":     st["cor"],
                    "total_entradas": stat["total_entradas"],
                    "total_minutos":  total_min,
                    "media_minutos":  media_min,
                    "sla_minutos":    sla_min,
                    "sla_ok":         sla_min == 0 or media_min <= sla_min,
                    "usuarios":       usuarios,
                })
            result.append({
                "group_id":   gid,
                "group_name": gr["group_name"],
                "colunas":    colunas,
            })
        return result
    finally:
        if cursor: cursor.close()
        conn.close()


# ─── UPLOAD DE IMAGENS ────────────────────────────────────────────────────────

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          '..', 'web', 'assests', 'uploads', 'tasks')
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@tasks_router.post("/upload-imagem")
async def upload_imagem(file: UploadFile = File(...), usuario_id: int = Query(..., gt=0)):
    """Faz upload de uma imagem e retorna a URL pública."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)

        # Validar extensão
        ext = os.path.splitext(file.filename or '')[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"Tipo de arquivo não permitido. Use: {', '.join(ALLOWED_EXTENSIONS)}")

        # Validar tamanho
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(400, "Arquivo muito grande. Máximo 5MB.")

        # Gerar nome único
        nome_arquivo = f"{uuid.uuid4().hex}{ext}"
        caminho = os.path.join(UPLOAD_DIR, nome_arquivo)

        # Salvar
        with open(caminho, 'wb') as f:
            f.write(content)

        # URL pública
        url = f"/SistemaCPE/web/assests/uploads/tasks/{nome_arquivo}"
        return {"ok": True, "url": url, "filename": file.filename}
    finally:
        if cursor: cursor.close()
        conn.close()


# ─── TEMPLATES DE ESPAÇO (deve ficar ANTES de /{tarefa_id}) ──────────────────

@tasks_router.get("/templates")
def listar_templates(usuario_id: int = Query(..., gt=0)):
    """Lista todos os templates salvos."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        cursor.execute(
            """SELECT t.id, t.nome, t.descricao, t.cor, t.criador_id,
                      u.name AS criador_nome, t.created_at,
                      COUNT(ts.id) AS total_colunas
               FROM templates_espaco_TASK t
               LEFT JOIN users u ON u.id = t.criador_id
               LEFT JOIN template_statuses_TASK ts ON ts.template_id = t.id
               GROUP BY t.id ORDER BY t.created_at DESC"""
        )
        rows = cursor.fetchall()
        return [{"id": r["id"], "nome": r["nome"], "descricao": r["descricao"],
                 "cor": r["cor"], "criador_nome": r["criador_nome"],
                 "total_colunas": r["total_colunas"],
                 "created_at": _fmt(r["created_at"])} for r in rows]
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.post("/templates", status_code=201)
def salvar_template(body: dict):
    """Salva o espaço atual como template reutilizável."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        usuario_id = body.get("usuario_id")
        espaco_id = body.get("espaco_id")
        nome = (body.get("nome") or "").strip()
        descricao = (body.get("descricao") or "").strip() or None

        if not usuario_id or not espaco_id or not nome:
            raise HTTPException(400, "usuario_id, espaco_id e nome são obrigatórios.")

        u = _usuario(cursor, usuario_id)
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Apenas gestores podem salvar templates.")

        # Buscar dados do espaço
        cursor.execute("SELECT * FROM espacos_TASK WHERE id=%s", (espaco_id,))
        esp = cursor.fetchone()
        if not esp:
            raise HTTPException(404, "Espaço não encontrado.")

        # Criar template
        cursor.execute(
            "INSERT INTO templates_espaco_TASK (nome, descricao, cor, criador_id) VALUES (%s,%s,%s,%s)",
            (nome, descricao, esp["cor"], usuario_id)
        )
        template_id = cursor.lastrowid

        # Copiar statuses
        cursor.execute(
            "SELECT nome, cor, icone, ordem, is_final FROM status_TASK WHERE espaco_id=%s ORDER BY ordem",
            (espaco_id,)
        )
        statuses = cursor.fetchall()
        for s in statuses:
            cursor.execute(
                "INSERT INTO template_statuses_TASK (template_id, nome, cor, icone, ordem, is_final) VALUES (%s,%s,%s,%s,%s,%s)",
                (template_id, s["nome"], s["cor"], s["icone"], s["ordem"], s["is_final"])
            )

        conn.commit()
        return {"ok": True, "template_id": template_id, "message": f"Modelo \"{nome}\" salvo com {len(statuses)} colunas!"}
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.delete("/templates/{template_id}", status_code=204)
def deletar_template(template_id: int, usuario_id: int = Query(..., gt=0)):
    """Deleta um template salvo."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, usuario_id)
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Apenas gestores podem deletar templates.")
        cursor.execute("DELETE FROM templates_espaco_TASK WHERE id=%s", (template_id,))
        if cursor.rowcount == 0:
            raise HTTPException(404, "Template não encontrado.")
        conn.commit()
    finally:
        if cursor: cursor.close()
        conn.close()


# ─── CATEGORIAS (deve ficar ANTES de /{tarefa_id}) ────────────────────────────

@tasks_router.get("/categorias")
def listar_categorias(
    espaco_id:  Optional[int] = Query(None),
    usuario_id: int           = Query(..., gt=0),
):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        if espaco_id:
            cursor.execute(
                "SELECT * FROM categorias_TASK WHERE espaco_id=%s ORDER BY nome",
                (espaco_id,)
            )
        else:
            cursor.execute("SELECT * FROM categorias_TASK ORDER BY nome")
        rows = cursor.fetchall()
        return [{"id": r["id"], "nome": r["nome"], "cor": r["cor"],
                 "espaco_id": r["espaco_id"]} for r in rows]
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.post("/categorias", status_code=201)
def criar_categoria_route(body: CategoriaCreate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, body.usuario_id)
        cursor.execute(
            "INSERT INTO categorias_TASK (espaco_id, group_id, nome, cor) VALUES (%s,%s,%s,%s)",
            (body.espaco_id, body.group_id, body.nome, body.cor)
        )
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM categorias_TASK WHERE id=%s", (new_id,))
        r = cursor.fetchone()
        return {"id": r["id"], "nome": r["nome"], "cor": r["cor"], "espaco_id": r["espaco_id"]}
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.delete("/categorias/{cat_id}", status_code=204)
def deletar_categoria_route(cat_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, usuario_id)
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Apenas gestores podem deletar categorias.")
        cursor.execute("DELETE FROM tarefa_categorias_TASK WHERE categoria_id=%s", (cat_id,))
        cursor.execute("DELETE FROM categorias_TASK WHERE id=%s", (cat_id,))
        conn.commit()
    finally:
        if cursor: cursor.close()
        conn.close()


# ─── TAREFAS ──────────────────────────────────────────────────────────────────

@tasks_router.get("")
def listar_tarefas(
    usuario_id:  int           = Query(..., gt=0),
    espaco_id:   Optional[int] = Query(None),
    group_id:    Optional[int] = Query(None),
    status_id:   Optional[int] = Query(None),
    prioridade:  Optional[str] = Query(None),
    responsavel: Optional[int] = Query(None),
    search:      Optional[str] = Query(None),
    minha_fila:  bool          = Query(False),
):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, usuario_id)

        if u["role"] in ("ADMIN", "TI", "MANAGER"):
            gid_filter = group_id
        else:
            gid_filter = u["group_id"]

        where, params = ["1=1"], []

        if espaco_id is not None:
            where.append("t.espaco_id = %s")
            params.append(espaco_id)
        elif gid_filter is not None:
            where.append(
                "(t.group_id = %s OR EXISTS("
                "  SELECT 1 FROM etapas_TASK e WHERE e.tarefa_id = t.id AND e.group_id = %s"
                "))"
            )
            params += [gid_filter, gid_filter]

        if status_id:
            where.append("t.status_id = %s"); params.append(status_id)
        if prioridade:
            where.append("t.prioridade = %s"); params.append(prioridade)
        if responsavel:
            where.append("t.responsavel_id = %s"); params.append(responsavel)
        if minha_fila:
            where.append(
                "(t.responsavel_id = %s OR EXISTS("
                "  SELECT 1 FROM etapas_TASK e WHERE e.tarefa_id = t.id AND e.responsavel_id = %s"
                "))"
            )
            params += [usuario_id, usuario_id]
        if search:
            where.append("(t.titulo LIKE %s OR t.descricao LIKE %s OR t.numero LIKE %s)")
            s = f"%{search}%"; params += [s, s, s]

        sql = (
            f"SELECT t.* FROM tarefas_TASK t WHERE {' AND '.join(where)} "
            "ORDER BY FIELD(t.prioridade,'urgente','alta','media','baixa'), "
            "t.prazo IS NULL, t.prazo, t.created_at DESC LIMIT 200"
        )
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [_enrich_tarefa(cursor, dict(r)) for r in rows]
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.post("", status_code=201)
def criar_tarefa(body: TarefaCreate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, body.usuario_id)

        # Número: usa chave do espaço quando disponível (ST-1, KEY-2) ou TASK-0001
        if body.espaco_id:
            cursor.execute("SELECT chave FROM espacos_TASK WHERE id=%s", (body.espaco_id,))
            esp = cursor.fetchone()
            chave = esp["chave"] if esp else "TASK"
            cursor.execute(
                "SELECT COUNT(*) AS n FROM tarefas_TASK WHERE espaco_id=%s", (body.espaco_id,)
            )
            cnt = cursor.fetchone()["n"]
            numero = f"{chave}-{cnt + 1}"
        else:
            cursor.execute("SELECT COUNT(*) AS n FROM tarefas_TASK")
            cnt = cursor.fetchone()["n"]
            numero = f"TASK-{cnt + 1:04d}"

        prazo = None
        if body.prazo:
            try:
                prazo = datetime.fromisoformat(body.prazo.replace("Z", "+00:00"))
            except Exception:
                raise HTTPException(400, "Formato de prazo inválido.")

        cursor.execute(
            """INSERT INTO tarefas_TASK
               (numero, titulo, descricao, prioridade, status_id, espaco_id, group_id,
                criador_id, responsavel_id, relator_id, tempo_estimado, prazo)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (numero, body.titulo, body.descricao, body.prioridade,
             body.status_id, body.espaco_id, u["group_id"], body.usuario_id,
             body.responsavel_id, body.usuario_id, body.tempo_estimado, prazo)
        )
        conn.commit()
        new_id = cursor.lastrowid
        _log(cursor, new_id, body.usuario_id, "criou", f"Tarefa criada: {body.titulo}")
        # Registrar início do rastreamento de tempo no status inicial
        if body.status_id:
            cursor.execute("SELECT nome, cor FROM status_TASK WHERE id=%s", (body.status_id,))
            ns = cursor.fetchone()
            cursor.execute(
                """INSERT INTO tarefa_historico_status_TASK
                   (tarefa_id, status_id, status_nome, status_cor, responsavel_id, responsavel_group_id, entrou_em)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (new_id, body.status_id, ns["nome"] if ns else None, ns["cor"] if ns else None,
                 body.responsavel_id, u["group_id"], datetime.now(timezone.utc))
            )
        conn.commit()

        cursor.execute("SELECT * FROM tarefas_TASK WHERE id = %s", (new_id,))
        return _enrich_tarefa(cursor, dict(cursor.fetchone()))
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.get("/{tarefa_id}")
def detalhe_tarefa(tarefa_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        cursor.execute("SELECT * FROM tarefas_TASK WHERE id = %s", (tarefa_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(404, "Tarefa não encontrada.")
        return _enrich_tarefa(cursor, dict(row))
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.put("/{tarefa_id}")
def atualizar_tarefa(tarefa_id: int, body: TarefaUpdate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, body.usuario_id)
        cursor.execute("SELECT * FROM tarefas_TASK WHERE id = %s", (tarefa_id,))
        t = cursor.fetchone()
        if not t:
            raise HTTPException(404, "Tarefa não encontrada.")

        # Task livre = sem responsável. Qualquer usuário pode se auto-atribuir
        # (desde que não esteja editando outros campos ao mesmo tempo).
        task_livre = t["responsavel_id"] is None
        outros_campos_alterados = any(getattr(body, f) is not None for f in (
            "titulo","descricao","prioridade","status_id","tempo_estimado",
            "prazo","start_date","cor_card",
        ))
        so_auto_claim = (
            task_livre
            and body.responsavel_id is not None
            and body.responsavel_id == u["id"]
            and not outros_campos_alterados
        )

        if not so_auto_claim:
            if u["role"] not in ROLES_ELEVATED and u["group_id"] != t["group_id"]:
                raise HTTPException(403, "Sem permissão.")

        # Proteção contra "roubo" de task já atribuída
        if (body.responsavel_id is not None
                and body.responsavel_id != (t["responsavel_id"] or 0)
                and not task_livre):
            is_admin     = u["role"] in ("ADMIN", "TI", "MANAGER")
            is_resp_grp  = u["role"] == "RESPONSAVEL_GRUPO" and u["group_id"] == t["group_id"]
            is_current   = t["responsavel_id"] == u["id"]
            if not (is_admin or is_resp_grp or is_current):
                raise HTTPException(403, "Esta tarefa já está atribuída a outra pessoa.")

        sets, vals, changes = [], [], []
        if body.titulo         is not None: sets.append("titulo=%s");         vals.append(body.titulo);         changes.append(f"título: {body.titulo}")
        if body.descricao      is not None: sets.append("descricao=%s");      vals.append(body.descricao)
        if body.prioridade     is not None: sets.append("prioridade=%s");     vals.append(body.prioridade);     changes.append(f"prioridade: {body.prioridade}")
        if body.status_id      is not None:
            sets.append("status_id=%s"); vals.append(body.status_id)
            cursor.execute("SELECT nome FROM status_TASK WHERE id=%s", (body.status_id,))
            _st = cursor.fetchone()
            changes.append(f"status: {_st['nome'] if _st else body.status_id}")
        if body.responsavel_id is not None: sets.append("responsavel_id=%s"); vals.append(body.responsavel_id)
        if body.tempo_estimado is not None: sets.append("tempo_estimado=%s"); vals.append(body.tempo_estimado)
        if body.prazo is not None:
            try:
                prazo = datetime.fromisoformat(body.prazo.replace("Z", "+00:00")) if body.prazo else None
            except Exception:
                raise HTTPException(400, "Formato de prazo inválido.")
            sets.append("prazo=%s"); vals.append(prazo)
        if body.start_date is not None:
            try:
                sd = datetime.fromisoformat(body.start_date.replace("Z", "+00:00")) if body.start_date else None
            except Exception:
                raise HTTPException(400, "Formato de start_date inválido.")
            sets.append("start_date=%s"); vals.append(sd)
        if body.cor_card is not None:
            if u["role"] not in ROLES_ELEVATED:
                raise HTTPException(403, "Sem permissão para alterar a cor do card.")
            sets.append("cor_card=%s"); vals.append(body.cor_card if body.cor_card else None)

        if sets:
            vals.append(tarefa_id)
            cursor.execute(f"UPDATE tarefas_TASK SET {', '.join(sets)} WHERE id = %s", vals)
            _log(cursor, tarefa_id, body.usuario_id, "atualizou", "; ".join(changes) if changes else "editou")

            now = datetime.now(timezone.utc)
            # Se mudou de status, registrar histórico de tempo por coluna
            if body.status_id is not None and body.status_id != t["status_id"]:
                # Fechar registro anterior
                cursor.execute(
                    "UPDATE tarefa_historico_status_TASK SET saiu_em=%s WHERE tarefa_id=%s AND saiu_em IS NULL",
                    (now, tarefa_id)
                )
                # Buscar info do novo status
                cursor.execute("SELECT nome, cor FROM status_TASK WHERE id=%s", (body.status_id,))
                ns = cursor.fetchone()
                # Determinar responsável (novo ou atual)
                resp_id = body.responsavel_id if body.responsavel_id is not None else t["responsavel_id"]
                resp_gid = None
                if resp_id:
                    cursor.execute("SELECT group_id FROM users WHERE id=%s", (resp_id,))
                    ru = cursor.fetchone()
                    resp_gid = ru["group_id"] if ru else None
                # Abrir novo registro
                cursor.execute(
                    """INSERT INTO tarefa_historico_status_TASK
                       (tarefa_id, status_id, status_nome, status_cor, responsavel_id, responsavel_group_id, entrou_em)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (tarefa_id, body.status_id, ns["nome"] if ns else None, ns["cor"] if ns else None,
                     resp_id, resp_gid, now)
                )
            elif (body.responsavel_id is not None and body.responsavel_id != t.get("responsavel_id")):
                # Só o responsável mudou — fechar registro atual e abrir novo com novo responsável
                cursor.execute(
                    "UPDATE tarefa_historico_status_TASK SET saiu_em=%s WHERE tarefa_id=%s AND saiu_em IS NULL",
                    (now, tarefa_id)
                )
                cursor.execute("SELECT nome, cor FROM status_TASK WHERE id=%s", (t["status_id"],))
                curr_st = cursor.fetchone()
                cursor.execute("SELECT group_id FROM users WHERE id=%s", (body.responsavel_id,))
                new_ru = cursor.fetchone()
                cursor.execute(
                    """INSERT INTO tarefa_historico_status_TASK
                       (tarefa_id, status_id, status_nome, status_cor, responsavel_id, responsavel_group_id, entrou_em)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (tarefa_id, t["status_id"],
                     curr_st["nome"] if curr_st else None,
                     curr_st["cor"] if curr_st else None,
                     body.responsavel_id,
                     new_ru["group_id"] if new_ru else t["group_id"],
                     now)
                )

            conn.commit()

        cursor.execute("SELECT * FROM tarefas_TASK WHERE id = %s", (tarefa_id,))
        return _enrich_tarefa(cursor, dict(cursor.fetchone()))
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.delete("/{tarefa_id}", status_code=204)
def deletar_tarefa(tarefa_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, usuario_id)
        cursor.execute("SELECT * FROM tarefas_TASK WHERE id = %s", (tarefa_id,))
        t = cursor.fetchone()
        if not t:
            raise HTTPException(404, "Tarefa não encontrada.")
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Apenas gestores podem deletar tarefas.")
        if u["role"] == "RESPONSAVEL_GRUPO" and u["group_id"] != t["group_id"]:
            raise HTTPException(403, "Acesso negado.")

        for tbl in ("comentarios_TASK", "historico_TASK", "etapas_TASK"):
            cursor.execute(f"DELETE FROM {tbl} WHERE tarefa_id = %s", (tarefa_id,))
        cursor.execute("DELETE FROM tarefas_TASK WHERE id = %s", (tarefa_id,))
        conn.commit()
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.post("/{tarefa_id}/finalizar")
def finalizar_tarefa(tarefa_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, usuario_id)
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Apenas gestores podem finalizar tarefas.")

        cursor.execute("SELECT * FROM tarefas_TASK WHERE id = %s", (tarefa_id,))
        t = cursor.fetchone()
        if not t:
            raise HTTPException(404, "Tarefa não encontrada.")
        if u["role"] == "RESPONSAVEL_GRUPO" and u["group_id"] != t["group_id"]:
            raise HTTPException(403, "Acesso negado.")
        if t["concluida_em"]:
            raise HTTPException(400, "Tarefa já finalizada.")

        cursor.execute(
            "SELECT COUNT(*) AS n FROM etapas_TASK WHERE tarefa_id = %s AND concluida_em IS NULL",
            (tarefa_id,)
        )
        pendentes = cursor.fetchone()["n"]
        if pendentes > 0:
            raise HTTPException(400, f"Existem {pendentes} etapa(s) não concluída(s).")

        cursor.execute(
            "SELECT id FROM status_TASK WHERE espaco_id = %s AND is_final = 1 ORDER BY id LIMIT 1",
            (t["espaco_id"],)
        )
        final_status = cursor.fetchone()
        if not final_status:
            raise HTTPException(400, "Este espaço não possui uma coluna de conclusão configurada.")

        now = datetime.now(timezone.utc)
        cursor.execute(
            "UPDATE tarefas_TASK SET concluida_em=%s, concluida_por=%s, status_id=%s WHERE id=%s",
            (now, usuario_id, final_status["id"], tarefa_id)
        )
        _log(cursor, tarefa_id, usuario_id, "finalizou", "Tarefa finalizada")
        conn.commit()

        cursor.execute("SELECT * FROM tarefas_TASK WHERE id = %s", (tarefa_id,))
        return _enrich_tarefa(cursor, dict(cursor.fetchone()))
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.post("/{tarefa_id}/reabrir")
def reabrir_tarefa(tarefa_id: int, usuario_id: int = Query(..., gt=0)):
    """Reabre uma tarefa finalizada, voltando para o penúltimo status."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, usuario_id)

        cursor.execute("SELECT * FROM tarefas_TASK WHERE id = %s", (tarefa_id,))
        t = cursor.fetchone()
        if not t:
            raise HTTPException(404, "Tarefa não encontrada.")
        if not t["concluida_em"]:
            raise HTTPException(400, "Tarefa não está finalizada.")

        # Só RESPONSAVEL_GRUPO do grupo da tarefa (ou ADMIN/TI) pode reabrir
        if u["role"] == "RESPONSAVEL_GRUPO" and u["group_id"] != t["group_id"]:
            raise HTTPException(403, "Apenas o responsável do grupo desta tarefa pode reabri-la.")
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Sem permissão para reabrir tarefas.")

        # Buscar penúltimo status do histórico (o último antes do final)
        cursor.execute(
            """SELECT status_id, status_nome, status_cor, responsavel_id, responsavel_group_id
               FROM tarefa_historico_status_TASK
               WHERE tarefa_id = %s
               ORDER BY entrou_em DESC LIMIT 2""",
            (tarefa_id,)
        )
        historico = cursor.fetchall()

        # penúltimo = segundo registro (o primeiro é o status final atual)
        if len(historico) >= 2:
            penultimo = historico[1]
            novo_status_id = penultimo["status_id"]
            resp_id = penultimo["responsavel_id"]
            resp_gid = penultimo["responsavel_group_id"]
        else:
            # Se só tem 1 entrada, volta para o primeiro status do espaço
            cursor.execute(
                "SELECT id FROM status_TASK WHERE espaco_id=%s AND is_final=0 ORDER BY ordem LIMIT 1",
                (t["espaco_id"],)
            )
            first = cursor.fetchone()
            novo_status_id = first["id"] if first else t["status_id"]
            resp_id = t["responsavel_id"]
            resp_gid = t["group_id"]

        now = datetime.now(timezone.utc)

        # Limpar concluida_em e mover para o penúltimo status
        cursor.execute(
            "UPDATE tarefas_TASK SET concluida_em=NULL, concluida_por=NULL, status_id=%s WHERE id=%s",
            (novo_status_id, tarefa_id)
        )

        # Fechar o registro de histórico do status final (se aberto)
        cursor.execute(
            "UPDATE tarefa_historico_status_TASK SET saiu_em=%s WHERE tarefa_id=%s AND saiu_em IS NULL",
            (now, tarefa_id)
        )

        # Abrir novo registro de histórico para o status reaberto (continua a contagem)
        cursor.execute("SELECT nome, cor FROM status_TASK WHERE id=%s", (novo_status_id,))
        ns = cursor.fetchone()
        cursor.execute(
            """INSERT INTO tarefa_historico_status_TASK
               (tarefa_id, status_id, status_nome, status_cor, responsavel_id, responsavel_group_id, entrou_em)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (tarefa_id, novo_status_id,
             ns["nome"] if ns else "?", ns["cor"] if ns else "#6b7280",
             resp_id, resp_gid, now)
        )

        _log(cursor, tarefa_id, usuario_id, "reabriu", "Tarefa reaberta")
        conn.commit()

        cursor.execute("SELECT * FROM tarefas_TASK WHERE id = %s", (tarefa_id,))
        return _enrich_tarefa(cursor, dict(cursor.fetchone()))
    finally:
        if cursor: cursor.close()
        conn.close()


# ─── ENCAMINHAMENTO ENTRE GRUPOS ──────────────────────────────────────────────

@tasks_router.post("/{tarefa_id}/encaminhar")
def encaminhar_tarefa(tarefa_id: int, body: EncaminharBody):
    """Encaminha a tarefa para outro grupo. A tarefa deve estar em coluna final."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, body.usuario_id)

        cursor.execute("SELECT * FROM tarefas_TASK WHERE id=%s", (tarefa_id,))
        t = cursor.fetchone()
        if not t:
            raise HTTPException(404, "Tarefa não encontrada.")
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Sem permissão para encaminhar tarefas.")
        if u["role"] == "RESPONSAVEL_GRUPO" and u["group_id"] != t["group_id"]:
            raise HTTPException(403, "Seu grupo não é o dono atual da tarefa.")
        if t["group_id"] == body.para_grupo_id:
            raise HTTPException(400, "A tarefa já pertence a este grupo.")

        # Verificar se o status atual é final
        cursor.execute("SELECT is_final FROM status_TASK WHERE id=%s", (t["status_id"],))
        st = cursor.fetchone()
        if not st or not st["is_final"]:
            raise HTTPException(400, "A tarefa deve estar em uma coluna final para ser encaminhada.")

        # Primeiro status não-final do espaço (statuses são compartilhados por todos os grupos do espaço)
        cursor.execute(
            """SELECT id FROM status_TASK
               WHERE espaco_id=%s AND is_final=0
               ORDER BY ordem ASC, id ASC LIMIT 1""",
            (t["espaco_id"],)
        )
        first_st = cursor.fetchone()
        if not first_st:
            raise HTTPException(
                400,
                "Este espaço não possui colunas disponíveis para encaminhar."
            )

        now = datetime.now(timezone.utc)

        # Fechar registro atual de histórico de status
        cursor.execute(
            "UPDATE tarefa_historico_status_TASK SET saiu_em=%s WHERE tarefa_id=%s AND saiu_em IS NULL",
            (now, tarefa_id)
        )

        # Abrir novo registro de histórico para o grupo destino
        cursor.execute("SELECT nome, cor FROM status_TASK WHERE id=%s", (first_st["id"],))
        ns = cursor.fetchone()
        cursor.execute(
            """INSERT INTO tarefa_historico_status_TASK
               (tarefa_id, status_id, status_nome, status_cor, responsavel_id, responsavel_group_id, entrou_em)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (tarefa_id, first_st["id"],
             ns["nome"] if ns else None, ns["cor"] if ns else None,
             None, body.para_grupo_id, now)
        )

        # Registrar encaminhamento
        cursor.execute(
            """INSERT INTO tarefa_encaminhamentos_TASK
               (tarefa_id, de_grupo_id, para_grupo_id, encaminhado_por,
                encaminhado_em, status_id_origem, status_id_retorno)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (tarefa_id, t["group_id"], body.para_grupo_id,
             body.usuario_id, now, t["status_id"], t["status_id"])
        )

        # Transferir posse
        cursor.execute(
            "UPDATE tarefas_TASK SET group_id=%s, status_id=%s WHERE id=%s",
            (body.para_grupo_id, first_st["id"], tarefa_id)
        )

        # Notificar membros do grupo destino
        cursor.execute("SELECT titulo FROM tarefas_TASK WHERE id=%s", (tarefa_id,))
        titulo_row = cursor.fetchone()
        titulo = titulo_row["titulo"] if titulo_row else "Tarefa"
        cursor.execute(
            """INSERT INTO notificacoes (ticket_id, usuario_id, mensagem, tipo, lido, created_at)
               SELECT %s, u.id, %s, 'encaminhamento_task', 0, NOW()
               FROM users u WHERE u.group_id=%s AND (u.is_active IS NULL OR u.is_active=1)""",
            (tarefa_id,
             f'Tarefa "{titulo}" foi encaminhada para seu grupo.',
             body.para_grupo_id)
        )

        cursor.execute("SELECT name FROM cpe_grupo WHERE id=%s", (body.para_grupo_id,))
        _g = cursor.fetchone()
        _log(cursor, tarefa_id, body.usuario_id, "encaminhou",
             f"Encaminhada para {_g['name'] if _g else f'grupo {body.para_grupo_id}'}")
        conn.commit()

        cursor.execute("SELECT * FROM tarefas_TASK WHERE id=%s", (tarefa_id,))
        return _enrich_tarefa(cursor, dict(cursor.fetchone()))
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.post("/{tarefa_id}/devolver")
def devolver_tarefa(tarefa_id: int, body: DevolverBody):
    """Devolve a tarefa ao grupo que a encaminhou, reiniciando o SLA daquele grupo."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, body.usuario_id)

        cursor.execute("SELECT * FROM tarefas_TASK WHERE id=%s", (tarefa_id,))
        t = cursor.fetchone()
        if not t:
            raise HTTPException(404, "Tarefa não encontrada.")
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Sem permissão para devolver tarefas.")
        if u["role"] == "RESPONSAVEL_GRUPO" and u["group_id"] != t["group_id"]:
            raise HTTPException(403, "Seu grupo não é o dono atual da tarefa.")

        # Encaminhamento ativo mais recente
        cursor.execute(
            """SELECT * FROM tarefa_encaminhamentos_TASK
               WHERE tarefa_id=%s AND devolvido_em IS NULL
               ORDER BY encaminhado_em DESC LIMIT 1""",
            (tarefa_id,)
        )
        enc = cursor.fetchone()
        if not enc:
            raise HTTPException(400, "Esta tarefa não possui encaminhamento ativo.")

        now = datetime.now(timezone.utc)

        # Fechar registro atual de histórico de status
        cursor.execute(
            "UPDATE tarefa_historico_status_TASK SET saiu_em=%s WHERE tarefa_id=%s AND saiu_em IS NULL",
            (now, tarefa_id)
        )

        # Abrir novo registro para o grupo de origem (SLA continua do ponto onde parou)
        retorno_id = enc["status_id_retorno"] or enc["status_id_origem"]
        cursor.execute("SELECT nome, cor FROM status_TASK WHERE id=%s", (retorno_id,))
        ns = cursor.fetchone()
        cursor.execute(
            """INSERT INTO tarefa_historico_status_TASK
               (tarefa_id, status_id, status_nome, status_cor, responsavel_id, responsavel_group_id, entrou_em)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (tarefa_id, retorno_id,
             ns["nome"] if ns else None, ns["cor"] if ns else None,
             None, enc["de_grupo_id"], now)
        )

        # Registrar devolução
        cursor.execute(
            """UPDATE tarefa_encaminhamentos_TASK
               SET devolvido_em=%s, devolvido_por=%s, motivo_devolucao=%s
               WHERE id=%s""",
            (now, body.usuario_id, body.motivo, enc["id"])
        )

        # Devolver posse ao grupo de origem
        cursor.execute(
            "UPDATE tarefas_TASK SET group_id=%s, status_id=%s WHERE id=%s",
            (enc["de_grupo_id"], retorno_id, tarefa_id)
        )

        # Notificar membros do grupo de origem
        cursor.execute("SELECT titulo FROM tarefas_TASK WHERE id=%s", (tarefa_id,))
        titulo_row = cursor.fetchone()
        titulo = titulo_row["titulo"] if titulo_row else "Tarefa"
        motivo_txt = f" Motivo: {body.motivo}" if body.motivo else ""
        cursor.execute(
            """INSERT INTO notificacoes (ticket_id, usuario_id, mensagem, tipo, lido, created_at)
               SELECT %s, u.id, %s, 'encaminhamento_task', 0, NOW()
               FROM users u WHERE u.group_id=%s AND (u.is_active IS NULL OR u.is_active=1)""",
            (tarefa_id,
             f'Tarefa "{titulo}" foi devolvida para seu grupo.{motivo_txt}',
             enc["de_grupo_id"])
        )

        cursor.execute("SELECT name FROM cpe_grupo WHERE id=%s", (enc["de_grupo_id"],))
        _g2 = cursor.fetchone()
        _g2_nome = _g2["name"] if _g2 else f"grupo {enc['de_grupo_id']}"
        _log(cursor, tarefa_id, body.usuario_id, "devolveu",
             f"Devolvida para {_g2_nome}" + (f": {body.motivo}" if body.motivo else ""))
        conn.commit()

        cursor.execute("SELECT * FROM tarefas_TASK WHERE id=%s", (tarefa_id,))
        return _enrich_tarefa(cursor, dict(cursor.fetchone()))
    finally:
        if cursor: cursor.close()
        conn.close()


# ─── HISTÓRICO DE STATUS (tempo por coluna) ──────────────────────────────────

@tasks_router.get("/{tarefa_id}/historico-status")
def historico_status_tarefa(tarefa_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        cursor.execute(
            """SELECT h.id, h.status_id, h.status_nome, h.status_cor,
                      h.responsavel_id, u.name AS responsavel_nome,
                      h.responsavel_group_id, g.name AS group_name,
                      h.entrou_em, h.saiu_em,
                      TIMESTAMPDIFF(MINUTE, h.entrou_em, COALESCE(h.saiu_em, UTC_TIMESTAMP())) AS duracao_minutos
               FROM tarefa_historico_status_TASK h
               LEFT JOIN users u ON u.id = h.responsavel_id
               LEFT JOIN cpe_grupo g ON g.id = h.responsavel_group_id
               WHERE h.tarefa_id = %s
               ORDER BY h.entrou_em""",
            (tarefa_id,)
        )
        rows = cursor.fetchall()
        return [{
            "id":                 r["id"],
            "status_id":          r["status_id"],
            "status_nome":        r["status_nome"],
            "status_cor":         r["status_cor"],
            "responsavel_nome":   r["responsavel_nome"],
            "group_name":         r["group_name"],
            "responsavel_group_id": r["responsavel_group_id"],
            "entrou_em":          _fmt(r["entrou_em"]),
            "saiu_em":            _fmt(r["saiu_em"]),
            "duracao_minutos":    r["duracao_minutos"],
            "em_aberto":          r["saiu_em"] is None,
        } for r in rows]
    finally:
        if cursor: cursor.close()
        conn.close()


# ─── TEMPO POR USUÁRIO (tempo como responsável em cada status) ────────────────

@tasks_router.get("/{tarefa_id}/tempo-usuarios")
def tempo_usuarios_tarefa(tarefa_id: int, usuario_id: int = Query(..., gt=0)):
    """Retorna o tempo total que cada usuário ficou como responsável em cada status."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        # Agrupa por responsavel_id + status_id, soma duração
        cursor.execute(
            """SELECT h.responsavel_id, u.name AS user_name,
                      h.responsavel_group_id, g.name AS group_name,
                      h.status_id, h.status_nome, h.status_cor,
                      COUNT(*) AS total_passagens,
                      SUM(TIMESTAMPDIFF(MINUTE, h.entrou_em, COALESCE(h.saiu_em, UTC_TIMESTAMP()))) AS total_minutos
               FROM tarefa_historico_status_TASK h
               LEFT JOIN users u ON u.id = h.responsavel_id
               LEFT JOIN cpe_grupo g ON g.id = h.responsavel_group_id
               WHERE h.tarefa_id = %s AND h.responsavel_id IS NOT NULL
               GROUP BY h.responsavel_id, u.name, h.responsavel_group_id, g.name,
                        h.status_id, h.status_nome, h.status_cor
               ORDER BY u.name, h.status_id""",
            (tarefa_id,)
        )
        rows = cursor.fetchall()

        # Agrupa por usuário
        usuarios = {}
        for r in rows:
            uid = r["responsavel_id"]
            if uid not in usuarios:
                usuarios[uid] = {
                    "user_id":    uid,
                    "user_name":  r["user_name"] or f"Usuário {uid}",
                    "group_name": r["group_name"],
                    "statuses":   [],
                    "total_minutos_geral": 0,
                }
            mins = int(r["total_minutos"] or 0)
            usuarios[uid]["statuses"].append({
                "status_id":       r["status_id"],
                "status_nome":     r["status_nome"],
                "status_cor":      r["status_cor"],
                "total_passagens": r["total_passagens"],
                "total_minutos":   mins,
            })
            usuarios[uid]["total_minutos_geral"] += mins

        result = sorted(usuarios.values(), key=lambda x: -x["total_minutos_geral"])

        # Tempo ocioso: períodos sem responsável atribuído
        cursor.execute(
            """SELECT SUM(TIMESTAMPDIFF(MINUTE, h.entrou_em, COALESCE(h.saiu_em, UTC_TIMESTAMP()))) AS idle_minutos
               FROM tarefa_historico_status_TASK h
               WHERE h.tarefa_id = %s AND h.responsavel_id IS NULL""",
            (tarefa_id,)
        )
        idle_row = cursor.fetchone()
        idle_mins = int(idle_row["idle_minutos"] or 0) if idle_row else 0
        if idle_mins > 0:
            result.append({
                "user_id":   None,
                "user_name": "Sem responsável",
                "group_name": None,
                "statuses":   [],
                "total_minutos_geral": idle_mins,
                "is_idle": True,
            })

        return result
    finally:
        if cursor: cursor.close()
        conn.close()


# ─── ETAPAS ───────────────────────────────────────────────────────────────────

@tasks_router.post("/{tarefa_id}/etapas", status_code=201)
def criar_etapa(tarefa_id: int, body: EtapaCreate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, body.usuario_id)
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Apenas gestores podem vincular grupos.")

        cursor.execute("SELECT id FROM tarefas_TASK WHERE id = %s", (tarefa_id,))
        if not cursor.fetchone():
            raise HTTPException(404, "Tarefa não encontrada.")

        prazo = None
        if body.prazo:
            try:
                prazo = datetime.fromisoformat(body.prazo.replace("Z", "+00:00"))
            except Exception:
                raise HTTPException(400, "Formato de prazo inválido.")

        cursor.execute(
            """INSERT INTO etapas_TASK
               (tarefa_id, group_id, titulo, descricao, status_id,
                responsavel_id, tempo_estimado, prazo, ordem)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (tarefa_id, body.group_id, body.titulo, body.descricao,
             body.status_id, body.responsavel_id, body.tempo_estimado,
             prazo, body.ordem)
        )
        conn.commit()
        etapa_id = cursor.lastrowid

        cursor.execute("SELECT name FROM cpe_grupo WHERE id = %s", (body.group_id,))
        g = cursor.fetchone()
        _log(cursor, tarefa_id, body.usuario_id, "criou_etapa",
             f"Etapa '{body.titulo}' → {g['name'] if g else body.group_id}", etapa_id)
        conn.commit()

        cursor.execute("SELECT * FROM etapas_TASK WHERE id = %s", (etapa_id,))
        e = dict(cursor.fetchone())
        e["prazo"]       = _fmt(e["prazo"])
        e["concluida_em"]= _fmt(e["concluida_em"])
        e["created_at"]  = _fmt(e["created_at"])
        return e
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.put("/{tarefa_id}/etapas/{etapa_id}")
def atualizar_etapa(tarefa_id: int, etapa_id: int, body: EtapaUpdate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, body.usuario_id)
        cursor.execute(
            "SELECT * FROM etapas_TASK WHERE id = %s AND tarefa_id = %s",
            (etapa_id, tarefa_id)
        )
        e = cursor.fetchone()
        if not e:
            raise HTTPException(404, "Etapa não encontrada.")
        if u["role"] not in ROLES_ELEVATED and u["group_id"] != e["group_id"]:
            raise HTTPException(403, "Sem permissão.")

        sets, vals, changes = [], [], []
        if body.titulo         is not None: sets.append("titulo=%s");         vals.append(body.titulo)
        if body.descricao      is not None: sets.append("descricao=%s");      vals.append(body.descricao)
        if body.status_id      is not None:
            sets.append("status_id=%s"); vals.append(body.status_id)
            cursor.execute("SELECT nome FROM status_TASK WHERE id=%s", (body.status_id,))
            _st = cursor.fetchone()
            changes.append(f"status: {_st['nome'] if _st else body.status_id}")
        if body.responsavel_id is not None: sets.append("responsavel_id=%s"); vals.append(body.responsavel_id)
        if body.tempo_estimado is not None: sets.append("tempo_estimado=%s"); vals.append(body.tempo_estimado)
        if body.prazo          is not None:
            try:
                prazo = datetime.fromisoformat(body.prazo.replace("Z", "+00:00"))
            except Exception:
                raise HTTPException(400, "Formato de prazo inválido.")
            sets.append("prazo=%s"); vals.append(prazo)

        if sets:
            vals.append(etapa_id)
            cursor.execute(f"UPDATE etapas_TASK SET {', '.join(sets)} WHERE id = %s", vals)
            _log(cursor, tarefa_id, body.usuario_id, "atualizou_etapa",
                 "; ".join(changes) if changes else "editou etapa", etapa_id)
            conn.commit()

        cursor.execute("SELECT * FROM etapas_TASK WHERE id = %s", (etapa_id,))
        e = dict(cursor.fetchone())
        e["prazo"]       = _fmt(e["prazo"])
        e["concluida_em"]= _fmt(e["concluida_em"])
        e["created_at"]  = _fmt(e["created_at"])
        return e
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.post("/{tarefa_id}/etapas/{etapa_id}/concluir")
def concluir_etapa(tarefa_id: int, etapa_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, usuario_id)
        cursor.execute(
            "SELECT * FROM etapas_TASK WHERE id = %s AND tarefa_id = %s",
            (etapa_id, tarefa_id)
        )
        e = cursor.fetchone()
        if not e:
            raise HTTPException(404, "Etapa não encontrada.")
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Apenas gestores podem concluir etapas.")
        if u["role"] == "RESPONSAVEL_GRUPO" and u["group_id"] != e["group_id"]:
            raise HTTPException(403, "Acesso negado.")
        if e["concluida_em"]:
            raise HTTPException(400, "Etapa já concluída.")

        cursor.execute(
            "SELECT id FROM status_TASK WHERE group_id = %s AND is_final = 1 ORDER BY id LIMIT 1",
            (e["group_id"],)
        )
        final_status = cursor.fetchone()

        now = datetime.now(timezone.utc)
        cursor.execute(
            "UPDATE etapas_TASK SET concluida_em=%s, concluida_por=%s, status_id=%s WHERE id=%s",
            (now, usuario_id, final_status["id"] if final_status else e["status_id"], etapa_id)
        )
        _log(cursor, tarefa_id, usuario_id, "concluiu_etapa", f"Etapa '{e['titulo']}' concluída", etapa_id)
        conn.commit()

        cursor.execute("SELECT * FROM etapas_TASK WHERE id = %s", (etapa_id,))
        e = dict(cursor.fetchone())
        e["prazo"]       = _fmt(e["prazo"])
        e["concluida_em"]= _fmt(e["concluida_em"])
        return e
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.delete("/{tarefa_id}/etapas/{etapa_id}", status_code=204)
def deletar_etapa(tarefa_id: int, etapa_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, usuario_id)
        cursor.execute(
            "SELECT * FROM etapas_TASK WHERE id = %s AND tarefa_id = %s",
            (etapa_id, tarefa_id)
        )
        e = cursor.fetchone()
        if not e:
            raise HTTPException(404, "Etapa não encontrada.")
        if u["role"] not in ROLES_ELEVATED:
            raise HTTPException(403, "Apenas gestores podem deletar etapas.")
        if u["role"] == "RESPONSAVEL_GRUPO" and u["group_id"] != e["group_id"]:
            raise HTTPException(403, "Acesso negado.")

        cursor.execute("DELETE FROM etapas_TASK WHERE id = %s", (etapa_id,))
        _log(cursor, tarefa_id, usuario_id, "removeu_etapa", f"Etapa removida: {e['titulo']}")
        conn.commit()
    finally:
        if cursor: cursor.close()
        conn.close()


# ─── COMENTÁRIOS ──────────────────────────────────────────────────────────────

@tasks_router.get("/{tarefa_id}/comentarios")
def listar_comentarios(tarefa_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        cursor.execute(
            """SELECT c.*, u.name AS autor_nome
               FROM comentarios_TASK c
               LEFT JOIN users u ON u.id = c.autor_id
               WHERE c.tarefa_id = %s ORDER BY c.created_at""",
            (tarefa_id,)
        )
        rows = cursor.fetchall()
        return [{"id": r["id"], "tarefa_id": r["tarefa_id"], "etapa_id": r["etapa_id"],
                 "autor_id": r["autor_id"], "autor_nome": r["autor_nome"],
                 "texto": r["texto"], "created_at": _fmt(r["created_at"])} for r in rows]
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.post("/{tarefa_id}/comentarios", status_code=201)
def adicionar_comentario(tarefa_id: int, body: ComentarioCreate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, body.autor_id)
        cursor.execute("SELECT id FROM tarefas_TASK WHERE id = %s", (tarefa_id,))
        if not cursor.fetchone():
            raise HTTPException(404, "Tarefa não encontrada.")

        cursor.execute(
            "INSERT INTO comentarios_TASK (tarefa_id, etapa_id, autor_id, texto) VALUES (%s,%s,%s,%s)",
            (tarefa_id, body.etapa_id, body.autor_id, body.texto)
        )
        new_id = cursor.lastrowid
        _log(cursor, tarefa_id, body.autor_id, "comentou", body.texto[:80] if body.texto else None, body.etapa_id)
        conn.commit()
        cursor.execute(
            "SELECT c.*, u.name AS autor_nome FROM comentarios_TASK c "
            "LEFT JOIN users u ON u.id = c.autor_id WHERE c.id = %s",
            (new_id,)
        )
        r = cursor.fetchone()
        return {"id": r["id"], "tarefa_id": r["tarefa_id"], "etapa_id": r["etapa_id"],
                "autor_id": r["autor_id"], "autor_nome": r["autor_nome"],
                "texto": r["texto"], "created_at": _fmt(r["created_at"])}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[COMENTARIO] Erro: {e}")
        raise HTTPException(500, f"Erro ao comentar: {str(e)}")
    finally:
        if cursor: cursor.close()
        conn.close()


# ─── HISTÓRICO ────────────────────────────────────────────────────────────────

@tasks_router.get("/{tarefa_id}/historico")
def listar_historico(tarefa_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        cursor.execute(
            """SELECT h.*, u.name AS usuario_nome
               FROM historico_TASK h LEFT JOIN users u ON u.id = h.usuario_id
               WHERE h.tarefa_id = %s ORDER BY h.created_at""",
            (tarefa_id,)
        )
        rows = cursor.fetchall()
        return [{"id": r["id"], "acao": r["acao"], "detalhe": r["detalhe"],
                 "usuario_nome": r["usuario_nome"], "created_at": _fmt(r["created_at"])} for r in rows]
    finally:
        if cursor: cursor.close()
        conn.close()


# ─── AUXILIARES ───────────────────────────────────────────────────────────────

@tasks_router.get("/grupos/lista")
def listar_grupos(usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        cursor.execute("""
            SELECT g.id, g.name, COUNT(u.id) AS total_membros
            FROM cpe_grupo g
            LEFT JOIN users u ON u.group_id = g.id AND u.is_active = 1
            GROUP BY g.id, g.name
            ORDER BY g.name
        """)
        rows = cursor.fetchall()
        return [{"id": r["id"], "name": r["name"], "total_membros": r["total_membros"]} for r in rows]
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.get("/grupos/{group_id}/membros")
def membros_grupo(group_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        cursor.execute(
            "SELECT id, name, role FROM users WHERE group_id = %s AND is_active = 1 ORDER BY name",
            (group_id,)
        )
        rows = cursor.fetchall()
        return [{"id": r["id"], "name": r["name"], "role": r["role"]} for r in rows]
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.post("/{tarefa_id}/categorias/{cat_id}", status_code=201)
def associar_categoria(tarefa_id: int, cat_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        cursor.execute(
            "INSERT IGNORE INTO tarefa_categorias_TASK (tarefa_id, categoria_id) VALUES (%s,%s)",
            (tarefa_id, cat_id)
        )
        conn.commit()
        return {"ok": True}
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.delete("/{tarefa_id}/categorias/{cat_id}", status_code=204)
def remover_categoria_tarefa(tarefa_id: int, cat_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        cursor.execute(
            "DELETE FROM tarefa_categorias_TASK WHERE tarefa_id=%s AND categoria_id=%s",
            (tarefa_id, cat_id)
        )
        conn.commit()
    finally:
        if cursor: cursor.close()
        conn.close()


# ─── SUBTAREFAS ───────────────────────────────────────────────────────────────

@tasks_router.get("/{tarefa_id}/subtarefas")
def listar_subtarefas(tarefa_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        cursor.execute(
            "SELECT s.*, u.name AS criador_nome FROM subtarefas_TASK s "
            "LEFT JOIN users u ON u.id=s.criador_id WHERE s.tarefa_id=%s ORDER BY s.id",
            (tarefa_id,)
        )
        rows = cursor.fetchall()
        return [{"id": r["id"], "titulo": r["titulo"], "concluida": r["concluida"],
                 "concluida_em": _fmt(r["concluida_em"]), "criador_nome": r["criador_nome"]} for r in rows]
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.post("/{tarefa_id}/subtarefas", status_code=201)
def criar_subtarefa(tarefa_id: int, body: SubtarefaCreate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        u = _usuario(cursor, body.criador_id)
        cursor.execute("SELECT id, group_id FROM tarefas_TASK WHERE id=%s", (tarefa_id,))
        t = cursor.fetchone()
        if not t:
            raise HTTPException(404, "Tarefa não encontrada.")
        is_admin = u["role"] in ("ADMIN", "TI", "MANAGER")
        is_grupo_task = t["group_id"] and u["group_id"] == t["group_id"]
        task_sem_grupo = not t["group_id"]
        if not (is_admin or is_grupo_task or task_sem_grupo):
            raise HTTPException(403, "Você só pode criar subtarefas em tarefas do seu grupo.")
        cursor.execute(
            "INSERT INTO subtarefas_TASK (tarefa_id, titulo, criador_id) VALUES (%s,%s,%s)",
            (tarefa_id, body.titulo, body.criador_id)
        )
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM subtarefas_TASK WHERE id=%s", (new_id,))
        r = cursor.fetchone()
        return {"id": r["id"], "titulo": r["titulo"], "concluida": r["concluida"],
                "concluida_em": _fmt(r["concluida_em"])}
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.put("/{tarefa_id}/subtarefas/{sub_id}")
def atualizar_subtarefa(tarefa_id: int, sub_id: int, body: SubtarefaUpdate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, body.criador_id if hasattr(body, 'criador_id') else 0) if False else None
        cursor.execute(
            "SELECT * FROM subtarefas_TASK WHERE id=%s AND tarefa_id=%s",
            (sub_id, tarefa_id)
        )
        s = cursor.fetchone()
        if not s:
            raise HTTPException(404, "Subtarefa não encontrada.")

        sets, vals = [], []
        if body.titulo    is not None: sets.append("titulo=%s");    vals.append(body.titulo)
        if body.concluida is not None:
            sets.append("concluida=%s"); vals.append(body.concluida)
            now = datetime.now(timezone.utc) if body.concluida else None
            sets.append("concluida_em=%s"); vals.append(now)

        if sets:
            vals.append(sub_id)
            cursor.execute(f"UPDATE subtarefas_TASK SET {', '.join(sets)} WHERE id=%s", vals)
            conn.commit()

        cursor.execute("SELECT * FROM subtarefas_TASK WHERE id=%s", (sub_id,))
        r = cursor.fetchone()
        return {"id": r["id"], "titulo": r["titulo"], "concluida": r["concluida"],
                "concluida_em": _fmt(r["concluida_em"])}
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.delete("/{tarefa_id}/subtarefas/{sub_id}", status_code=204)
def deletar_subtarefa(tarefa_id: int, sub_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        cursor.execute(
            "DELETE FROM subtarefas_TASK WHERE id=%s AND tarefa_id=%s",
            (sub_id, tarefa_id)
        )
        conn.commit()
    finally:
        if cursor: cursor.close()
        conn.close()


# ─── MEMBROS DA TAREFA (TEAM) ─────────────────────────────────────────────────

@tasks_router.get("/{tarefa_id}/membros")
def listar_membros_tarefa(tarefa_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        cursor.execute(
            "SELECT u.id, u.name, u.role FROM tarefa_membros_TASK tm "
            "JOIN users u ON u.id=tm.usuario_id WHERE tm.tarefa_id=%s ORDER BY u.name",
            (tarefa_id,)
        )
        return [{"id": r["id"], "nome": r["name"], "role": r["role"]}
                for r in cursor.fetchall()]
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.post("/{tarefa_id}/membros/{uid}", status_code=201)
def adicionar_membro_tarefa(tarefa_id: int, uid: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        cursor.execute(
            "INSERT IGNORE INTO tarefa_membros_TASK (tarefa_id, usuario_id) VALUES (%s,%s)",
            (tarefa_id, uid)
        )
        conn.commit()
        return {"ok": True}
    finally:
        if cursor: cursor.close()
        conn.close()


@tasks_router.delete("/{tarefa_id}/membros/{uid}", status_code=204)
def remover_membro_tarefa(tarefa_id: int, uid: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, usuario_id)
        cursor.execute(
            "DELETE FROM tarefa_membros_TASK WHERE tarefa_id=%s AND usuario_id=%s",
            (tarefa_id, uid)
        )
        conn.commit()
    finally:
        if cursor: cursor.close()
        conn.close()


# ─── CONTROLE DE TEMPO ────────────────────────────────────────────────────────

@tasks_router.put("/{tarefa_id}/tempo")
def atualizar_tempo(tarefa_id: int, body: TempoUpdate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        _usuario(cursor, body.usuario_id)
        cursor.execute("SELECT id FROM tarefas_TASK WHERE id=%s", (tarefa_id,))
        if not cursor.fetchone():
            raise HTTPException(404, "Tarefa não encontrada.")

        sets, vals = [], []
        if body.tempo_gasto    is not None: sets.append("tempo_gasto=%s");    vals.append(body.tempo_gasto or None)
        if body.tempo_restante is not None: sets.append("tempo_restante=%s"); vals.append(body.tempo_restante or None)
        if body.start_date     is not None:
            try:
                sd = datetime.fromisoformat(body.start_date.replace("Z", "+00:00")) if body.start_date else None
            except Exception:
                raise HTTPException(400, "Formato de start_date inválido.")
            sets.append("start_date=%s"); vals.append(sd)

        if sets:
            vals.append(tarefa_id)
            cursor.execute(f"UPDATE tarefas_TASK SET {', '.join(sets)} WHERE id=%s", vals)
            _log(cursor, tarefa_id, body.usuario_id, "atualizou_tempo",
                 f"gasto={body.tempo_gasto} restante={body.tempo_restante}")
            conn.commit()

        cursor.execute("SELECT * FROM tarefas_TASK WHERE id=%s", (tarefa_id,))
        t = dict(cursor.fetchone())
        return {"tempo_gasto": t["tempo_gasto"], "tempo_restante": t["tempo_restante"],
                "start_date": _fmt(t.get("start_date"))}
    finally:
        if cursor: cursor.close()
        conn.close()
