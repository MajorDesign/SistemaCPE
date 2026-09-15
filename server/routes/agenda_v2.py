"""
Agenda corporativa v2 — desktop CPE Control.

Roda em /api/agenda/v2/* pra nao conflitar com /api/agenda/* legado
(que serve integracao Carbonio).

Sprint 1: CRUD de calendarios e eventos (sem participantes/anexos/
compartilhamento — vem em sprints seguintes).

Padrao de auth: cookie 'cpe_session' ou header 'X-Auth-Token', igual
ao resto do sistema. Datas em DATETIME naive BR (America/Sao_Paulo).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, date, time as _time
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Query, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, validator

from database import get_db_or_404
from security import parse_session_token, get_user_by_id
from services.agenda_email import enviar_convite_agenda

router = APIRouter(prefix="/api/agenda/v2", tags=["agenda-v2"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------
def _exigir_user(request: Request) -> dict:
    token = request.cookies.get("cpe_session") or request.headers.get("X-Auth-Token", "")
    if not token:
        raise HTTPException(status_code=401, detail="Sessao requerida")
    uid = parse_session_token(token)
    if not uid:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado")
    user = get_user_by_id(uid)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado")
    return user


# ---------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------
def _parse_dt(s: str) -> datetime:
    """Aceita 'YYYY-MM-DD HH:MM[:SS]' ou 'YYYY-MM-DDTHH:MM[:SS]'.
    Sem timezone — assume horario BR local."""
    s = (s or "").strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise HTTPException(status_code=400, detail=f"Data/hora invalida: {s!r} — use YYYY-MM-DDTHH:MM")


def _group_ids_do_user(cur, user_id: int) -> List[int]:
    """Retorna TODOS os group_ids do user (primario + user_groups).
    Usado pra listar calendarios de grupos que ele participa."""
    ids: set[int] = set()
    try:
        cur.execute("SELECT group_id FROM user_groups WHERE user_id=%s", (user_id,))
        for r in cur.fetchall() or []:
            gid = r.get("group_id") if isinstance(r, dict) else r[0]
            if gid:
                ids.add(gid)
    except Exception:
        pass  # tabela user_groups pode nao existir em ambientes antigos
    try:
        cur.execute("SELECT group_id FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        if row:
            gid = row.get("group_id") if isinstance(row, dict) else row[0]
            if gid:
                ids.add(gid)
    except Exception:
        pass
    return sorted(ids)


import threading as _threading
_default_cal_locks: dict[int, _threading.Lock] = {}
_default_cal_locks_guard = _threading.Lock()


def _ensure_default_calendario_pessoal(cur, user_id: int) -> int:
    """Cria (idempotente) o calendario pessoal default do user; retorna id.

    Usa lock por-user pra evitar race (multiplos requests concorrentes na
    primeira carga do renderer podiam disparar N INSERTs em paralelo — cada
    um vendo 'nao existe' no SELECT antes do commit do outro)."""
    with _default_cal_locks_guard:
        lk = _default_cal_locks.setdefault(int(user_id), _threading.Lock())
    with lk:
        cur.execute("""
            SELECT id FROM ag_calendarios
            WHERE tipo_dono='user' AND dono_user_id=%s AND is_default=1 AND deleted_at IS NULL
            LIMIT 1
        """, (user_id,))
        row = cur.fetchone()
        if row:
            return row["id"] if isinstance(row, dict) else row[0]
        cur.execute("""
            INSERT INTO ag_calendarios
              (nome, cor, tipo_dono, dono_user_id, is_default, criado_por)
            VALUES (%s, %s, 'user', %s, 1, %s)
        """, ("Meu calendario", "#1f6feb", user_id, user_id))
        return cur.lastrowid


# ---------------------------------------------------------------------
# Models Pydantic
# ---------------------------------------------------------------------
class CalendarioCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    cor: str = Field("#1f6feb", pattern=r"^#[0-9a-fA-F]{6}$")
    tipo_dono: str = Field("user", pattern="^(user|group)$")
    dono_group_id: Optional[int] = None
    descricao: Optional[str] = None


class CalendarioUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=120)
    cor: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    descricao: Optional[str] = None


class EventoCreate(BaseModel):
    calendario_id: int
    titulo: str = Field(..., min_length=1, max_length=200)
    descricao_html: Optional[str] = None
    local: Optional[str] = Field(None, max_length=200)
    link_online: Optional[str] = Field(None, max_length=500)
    meeting_code: Optional[str] = Field(None, max_length=32)
    dia_inteiro: bool = False
    inicio: str
    fim: str
    cor: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    visibilidade: str = Field("privada", pattern="^(publica|privada)$")
    disponibilidade: str = Field("ocupado", pattern="^(livre|ocupado|provisorio|fora_escritorio)$")


class EventoUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=200)
    descricao_html: Optional[str] = None
    local: Optional[str] = Field(None, max_length=200)
    link_online: Optional[str] = Field(None, max_length=500)
    meeting_code: Optional[str] = Field(None, max_length=32)
    dia_inteiro: Optional[bool] = None
    inicio: Optional[str] = None
    fim: Optional[str] = None
    cor: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    visibilidade: Optional[str] = Field(None, pattern="^(publica|privada)$")
    disponibilidade: Optional[str] = Field(None, pattern="^(livre|ocupado|provisorio|fora_escritorio)$")
    status_op: Optional[str] = Field(None, pattern="^(agendado|confirmado|em_andamento|concluido|cancelado)$")


class CancelarBody(BaseModel):
    motivo: Optional[str] = Field(None, max_length=500)


class ParticipanteAdd(BaseModel):
    # exatamente um dos dois:
    user_id: Optional[int] = None
    email: Optional[str] = Field(None, max_length=200)
    nome: Optional[str] = Field(None, max_length=120)
    papel: str = Field("obrigatorio", pattern="^(obrigatorio|opcional)$")


class ParticipantesAddBody(BaseModel):
    participantes: List[ParticipanteAdd]


class RsvpBody(BaseModel):
    status: str = Field(..., pattern="^(aceito|recusado|talvez|sem_resposta)$")


class ShareCalendarioBody(BaseModel):
    destino_tipo: str = Field(..., pattern="^(user|group)$")
    destino_id: int
    permissao: str = Field("ler", pattern="^(disponibilidade|ler|editar)$")


class ShareEventoBody(BaseModel):
    destino_tipo: str = Field(..., pattern="^(user|group)$")
    destino_id: int


# ---------------------------------------------------------------------
# CALENDARIOS
# ---------------------------------------------------------------------
@router.get("/calendarios")
def listar_calendarios(request: Request):
    """Retorna calendarios que o user tem acesso:
      - Seus pessoais
      - De grupos que participa
      - Compartilhados com ele (sprint 4 adiciona)
    """
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        # garante calendario pessoal default
        _ensure_default_calendario_pessoal(cur, uid)
        conn.commit()

        gids = _group_ids_do_user(cur, uid)

        # pessoais
        cur.execute("""
            SELECT id, nome, cor, tipo_dono, dono_user_id, dono_group_id,
                   is_default, descricao, criado_em, criado_por
            FROM ag_calendarios
            WHERE deleted_at IS NULL AND tipo_dono='user' AND dono_user_id=%s
            ORDER BY is_default DESC, nome ASC
        """, (uid,))
        pessoais = cur.fetchall()
        for c in pessoais:
            c["minha_permissao"] = "admin"  # dono direto

        # de grupos
        de_grupos = []
        if gids:
            marcadores = ",".join(["%s"] * len(gids))
            cur.execute(f"""
                SELECT c.id, c.nome, c.cor, c.tipo_dono, c.dono_user_id, c.dono_group_id,
                       c.is_default, c.descricao, c.criado_em, c.criado_por,
                       g.name AS grupo_nome
                FROM ag_calendarios c
                LEFT JOIN cpe_grupo g ON g.id = c.dono_group_id
                WHERE c.deleted_at IS NULL AND c.tipo_dono='group'
                  AND c.dono_group_id IN ({marcadores})
                ORDER BY g.name ASC, c.nome ASC
            """, tuple(gids))
            de_grupos = cur.fetchall()
            for c in de_grupos:
                c["minha_permissao"] = "admin"  # membro do grupo dono

        # compartilhados comigo: shares diretos + shares pra grupos que participo
        compartilhados_ids: set[int] = set()
        cur.execute("""
            SELECT DISTINCT calendario_id
            FROM ag_calendario_compartilhamentos
            WHERE destino_tipo='user' AND destino_user_id=%s AND revogado_em IS NULL
        """, (uid,))
        for r in cur.fetchall(): compartilhados_ids.add(r["calendario_id"])
        if gids:
            marc = ",".join(["%s"] * len(gids))
            cur.execute(f"""
                SELECT DISTINCT calendario_id
                FROM ag_calendario_compartilhamentos
                WHERE destino_tipo='group' AND destino_group_id IN ({marc}) AND revogado_em IS NULL
            """, tuple(gids))
            for r in cur.fetchall(): compartilhados_ids.add(r["calendario_id"])

        # remove ids que ja aparecem em pessoais/de_grupos (evita duplicar)
        ja = {c["id"] for c in pessoais} | {c["id"] for c in de_grupos}
        compartilhados_ids -= ja

        compartilhados = []
        if compartilhados_ids:
            marc = ",".join(["%s"] * len(compartilhados_ids))
            cur.execute(f"""
                SELECT c.id, c.nome, c.cor, c.tipo_dono, c.dono_user_id, c.dono_group_id,
                       c.is_default, c.descricao, c.criado_em, c.criado_por,
                       u.name AS dono_user_nome, g.name AS dono_group_nome
                FROM ag_calendarios c
                LEFT JOIN users u ON u.id = c.dono_user_id
                LEFT JOIN cpe_grupo g ON g.id = c.dono_group_id
                WHERE c.id IN ({marc}) AND c.deleted_at IS NULL
                ORDER BY c.nome ASC
            """, tuple(compartilhados_ids))
            compartilhados = cur.fetchall()
            # calcula a permissao efetiva do user em cada calendario compartilhado
            for c in compartilhados:
                c["minha_permissao"] = _cal_share_permissao(cur, uid, c["id"]) or "ler"

        return {"success": True, "pessoais": pessoais,
                "de_grupos": de_grupos, "compartilhados": compartilhados}
    finally:
        cur.close(); conn.close()


@router.post("/calendarios")
def criar_calendario(body: CalendarioCreate, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])

    if body.tipo_dono == "group":
        if not body.dono_group_id:
            raise HTTPException(status_code=400, detail="dono_group_id obrigatorio para tipo_dono='group'")
        # user precisa ser membro do grupo
        conn = get_db_or_404()
        cur = conn.cursor(dictionary=True)
        try:
            gids = _group_ids_do_user(cur, uid)
            if body.dono_group_id not in gids:
                raise HTTPException(status_code=403, detail="Voce nao e membro deste grupo")
            cur.execute("""
                INSERT INTO ag_calendarios
                  (nome, cor, tipo_dono, dono_group_id, descricao, criado_por)
                VALUES (%s, %s, 'group', %s, %s, %s)
            """, (body.nome, body.cor, body.dono_group_id, body.descricao, uid))
            new_id = cur.lastrowid
            conn.commit()
            return {"success": True, "id": new_id}
        finally:
            cur.close(); conn.close()

    # tipo_dono='user' — cria calendario adicional do proprio user
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            INSERT INTO ag_calendarios
              (nome, cor, tipo_dono, dono_user_id, descricao, criado_por)
            VALUES (%s, %s, 'user', %s, %s, %s)
        """, (body.nome, body.cor, uid, body.descricao, uid))
        new_id = cur.lastrowid
        conn.commit()
        return {"success": True, "id": new_id}
    finally:
        cur.close(); conn.close()


@router.patch("/calendarios/{cal_id}")
def editar_calendario(cal_id: int, body: CalendarioUpdate, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, tipo_dono, dono_user_id, dono_group_id, criado_por
            FROM ag_calendarios WHERE id=%s AND deleted_at IS NULL
        """, (cal_id,))
        cal = cur.fetchone()
        if not cal:
            raise HTTPException(status_code=404, detail="Calendario nao encontrado")
        # permissao: dono direto OU membro do grupo dono
        if cal["tipo_dono"] == "user":
            if int(cal["dono_user_id"]) != uid:
                raise HTTPException(status_code=403, detail="Sem permissao")
        else:
            gids = _group_ids_do_user(cur, uid)
            if cal["dono_group_id"] not in gids:
                raise HTTPException(status_code=403, detail="Sem permissao")

        sets, params = [], []
        if body.nome is not None:
            sets.append("nome=%s"); params.append(body.nome)
        if body.cor is not None:
            sets.append("cor=%s"); params.append(body.cor)
        if body.descricao is not None:
            sets.append("descricao=%s"); params.append(body.descricao)
        if not sets:
            return {"success": True, "noop": True}
        params.append(cal_id)
        cur.execute(f"UPDATE ag_calendarios SET {', '.join(sets)} WHERE id=%s", tuple(params))
        conn.commit()
        return {"success": True}
    finally:
        cur.close(); conn.close()


@router.delete("/calendarios/{cal_id}")
def deletar_calendario(cal_id: int, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, tipo_dono, dono_user_id, dono_group_id, is_default
            FROM ag_calendarios WHERE id=%s AND deleted_at IS NULL
        """, (cal_id,))
        cal = cur.fetchone()
        if not cal:
            raise HTTPException(status_code=404, detail="Calendario nao encontrado")
        if cal["is_default"]:
            raise HTTPException(status_code=400, detail="Calendario default nao pode ser deletado")
        if cal["tipo_dono"] == "user":
            if int(cal["dono_user_id"]) != uid:
                raise HTTPException(status_code=403, detail="Sem permissao")
        else:
            gids = _group_ids_do_user(cur, uid)
            if cal["dono_group_id"] not in gids:
                raise HTTPException(status_code=403, detail="Sem permissao")
        cur.execute("UPDATE ag_calendarios SET deleted_at=NOW() WHERE id=%s", (cal_id,))
        conn.commit()
        return {"success": True}
    finally:
        cur.close(); conn.close()


# ---------------------------------------------------------------------
# EVENTOS
# ---------------------------------------------------------------------
def _cal_share_permissao(cur, user_id: int, cal_id: int) -> Optional[str]:
    """Se ha share ativo do calendario X pro user (direto ou via grupo),
    retorna a permissao mais alta ('editar' > 'ler' > 'disponibilidade').
    None se sem share."""
    gids = _group_ids_do_user(cur, user_id)
    parts = ["destino_tipo='user' AND destino_user_id=%s"]
    params: list = [user_id]
    if gids:
        marc = ",".join(["%s"] * len(gids))
        parts.append(f"(destino_tipo='group' AND destino_group_id IN ({marc}))")
        params.extend(gids)
    cur.execute(
        f"SELECT permissao FROM ag_calendario_compartilhamentos "
        f"WHERE calendario_id=%s AND revogado_em IS NULL AND ({' OR '.join(parts)})",
        tuple([cal_id] + params),
    )
    perms = [r["permissao"] for r in cur.fetchall() or []]
    if "editar" in perms:
        return "editar"
    if "ler" in perms:
        return "ler"
    if "disponibilidade" in perms:
        return "disponibilidade"
    return None


def _user_pode_ver_calendario(cur, user_id: int, cal_id: int) -> bool:
    cur.execute("""
        SELECT tipo_dono, dono_user_id, dono_group_id
        FROM ag_calendarios WHERE id=%s AND deleted_at IS NULL
    """, (cal_id,))
    cal = cur.fetchone()
    if not cal:
        return False
    if cal["tipo_dono"] == "user":
        if int(cal["dono_user_id"]) == int(user_id):
            return True
    else:
        gids = _group_ids_do_user(cur, user_id)
        if cal["dono_group_id"] in gids:
            return True
    # via compartilhamento
    return _cal_share_permissao(cur, user_id, cal_id) is not None


def _user_pode_editar_calendario(cur, user_id: int, cal_id: int) -> bool:
    """Editar exige: dono direto OU membro do grupo dono OU share com permissao='editar'."""
    cur.execute("""
        SELECT tipo_dono, dono_user_id, dono_group_id
        FROM ag_calendarios WHERE id=%s AND deleted_at IS NULL
    """, (cal_id,))
    cal = cur.fetchone()
    if not cal:
        return False
    if cal["tipo_dono"] == "user":
        if int(cal["dono_user_id"]) == int(user_id):
            return True
    else:
        gids = _group_ids_do_user(cur, user_id)
        if cal["dono_group_id"] in gids:
            return True
    return _cal_share_permissao(cur, user_id, cal_id) == "editar"


def _evento_share_ativo(cur, user_id: int, evento_id: int) -> bool:
    """Ha share ad-hoc do evento pro user (direto ou via grupo)?"""
    gids = _group_ids_do_user(cur, user_id)
    parts = ["destino_tipo='user' AND destino_user_id=%s"]
    params: list = [user_id]
    if gids:
        marc = ",".join(["%s"] * len(gids))
        parts.append(f"(destino_tipo='group' AND destino_group_id IN ({marc}))")
        params.extend(gids)
    cur.execute(
        f"SELECT 1 FROM ag_evento_compartilhamentos "
        f"WHERE evento_id=%s AND ({' OR '.join(parts)}) LIMIT 1",
        tuple([evento_id] + params),
    )
    return cur.fetchone() is not None


def _user_e_participante(cur, user_id: int, evento_id: int) -> bool:
    """True se o user esta em ag_participantes do evento (como interno)."""
    cur.execute(
        "SELECT 1 FROM ag_participantes WHERE evento_id=%s AND user_id=%s LIMIT 1",
        (evento_id, user_id),
    )
    return cur.fetchone() is not None


def _pode_ver_evento(cur, user_id: int, evento: dict) -> bool:
    """Regra unificada de visibilidade do evento (Sprint 4):
      - organizador OU criador
      - participante (via ag_participantes)
      - vê o calendário (dono pessoal, membro do grupo dono, ou share)
      - recebeu compartilhamento ad-hoc do evento
    Nao aplica mascara de privacidade — quem chama decide."""
    if int(evento["organizador_id"]) == int(user_id):
        return True
    if int(evento.get("criado_por") or 0) == int(user_id):
        return True
    if _user_e_participante(cur, user_id, evento["id"]):
        return True
    if _evento_share_ativo(cur, user_id, evento["id"]):
        return True
    return _user_pode_ver_calendario(cur, user_id, evento["calendario_id"])


def _pode_editar_evento(cur, user_id: int, evento: dict) -> bool:
    """Editar/cancelar/deletar: organizador OU quem pode editar o calendario."""
    if int(evento["organizador_id"]) == int(user_id):
        return True
    return _user_pode_editar_calendario(cur, user_id, evento["calendario_id"])


@router.get("/eventos")
def listar_eventos(
    request: Request,
    inicio: str = Query(..., description="YYYY-MM-DD"),
    fim: str = Query(..., description="YYYY-MM-DD"),
    calendarios: Optional[str] = Query(None, description="IDs separados por virgula"),
):
    """Lista eventos no intervalo. Se `calendarios` nao vier, usa TODOS
    os calendarios visiveis pro user (pessoais + grupos)."""
    user = _exigir_user(request)
    uid = int(user["id"])

    dt_ini = _parse_dt(inicio)
    dt_fim = _parse_dt(fim)
    if dt_fim < dt_ini:
        raise HTTPException(status_code=400, detail="fim antes de inicio")

    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        # calendarios do user (mesma regra do endpoint listar_calendarios)
        _ensure_default_calendario_pessoal(cur, uid)
        conn.commit()
        gids = _group_ids_do_user(cur, uid)

        if calendarios is not None:
            # Frontend passou o parametro (mesmo que vazio) — respeita
            # filtro explicito. Vazio = zero eventos (nao "todos").
            try:
                filtro_ids = [int(x) for x in calendarios.split(",") if x.strip()]
            except ValueError:
                raise HTTPException(status_code=400, detail="Parametro calendarios invalido")
            # limita ao que o user pode ver
            filtro_ids = [c for c in filtro_ids if _user_pode_ver_calendario(cur, uid, c)]
            if not filtro_ids:
                return {"success": True, "eventos": []}
        else:
            # todos visiveis: pessoais + grupos + compartilhados diretos + shares p/ grupos
            visiveis: set[int] = set()
            # pessoais
            cur.execute("""
                SELECT id FROM ag_calendarios
                WHERE deleted_at IS NULL AND tipo_dono='user' AND dono_user_id=%s
            """, (uid,))
            for r in cur.fetchall(): visiveis.add(r["id"])
            # de grupos
            if gids:
                marc_g = ",".join(["%s"] * len(gids))
                cur.execute(f"""
                    SELECT id FROM ag_calendarios
                    WHERE deleted_at IS NULL AND tipo_dono='group'
                      AND dono_group_id IN ({marc_g})
                """, tuple(gids))
                for r in cur.fetchall(): visiveis.add(r["id"])
            # shares diretos
            cur.execute("""
                SELECT DISTINCT calendario_id FROM ag_calendario_compartilhamentos
                WHERE destino_tipo='user' AND destino_user_id=%s AND revogado_em IS NULL
            """, (uid,))
            for r in cur.fetchall(): visiveis.add(r["calendario_id"])
            # shares pra grupos
            if gids:
                marc_g = ",".join(["%s"] * len(gids))
                cur.execute(f"""
                    SELECT DISTINCT calendario_id FROM ag_calendario_compartilhamentos
                    WHERE destino_tipo='group' AND destino_group_id IN ({marc_g})
                      AND revogado_em IS NULL
                """, tuple(gids))
                for r in cur.fetchall(): visiveis.add(r["calendario_id"])
            filtro_ids = sorted(visiveis)
            if not filtro_ids:
                return {"success": True, "eventos": []}

        marcadores = ",".join(["%s"] * len(filtro_ids))
        cur.execute(f"""
            SELECT e.id, e.calendario_id, e.titulo, e.descricao_html, e.local,
                   e.link_online, e.meeting_code, e.dia_inteiro,
                   e.inicio, e.fim, e.cor, e.visibilidade, e.disponibilidade,
                   e.status_op, e.organizador_id,
                   e.criado_em, e.criado_por, e.alterado_em, e.alterado_por,
                   c.cor AS calendario_cor, c.nome AS calendario_nome
            FROM ag_eventos e
            JOIN ag_calendarios c ON c.id = e.calendario_id
            WHERE e.deleted_at IS NULL
              AND e.calendario_id IN ({marcadores})
              AND e.fim >= %s AND e.inicio <= %s
            ORDER BY e.inicio ASC, e.id ASC
        """, tuple(filtro_ids + [dt_ini, dt_fim]))
        eventos = cur.fetchall()

        # Mascarar eventos privados que o user nao pode ver por completo
        # (nao e organizador nem participante). Continua mostrando bloqueio.
        for ev in eventos:
            if ev["visibilidade"] == "privada":
                if int(ev["organizador_id"]) != uid and not _user_e_participante(cur, uid, ev["id"]):
                    ev["titulo"] = "Ocupado"
                    ev["descricao_html"] = None
                    ev["local"] = None
                    ev["link_online"] = None
        return {"success": True, "eventos": eventos}
    finally:
        cur.close(); conn.close()


@router.get("/eventos/{ev_id}")
def obter_evento(ev_id: int, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT e.*, c.nome AS calendario_nome, c.cor AS calendario_cor
            FROM ag_eventos e
            JOIN ag_calendarios c ON c.id = e.calendario_id
            WHERE e.id=%s AND e.deleted_at IS NULL
        """, (ev_id,))
        ev = cur.fetchone()
        if not ev:
            raise HTTPException(status_code=404, detail="Evento nao encontrado")
        if not _pode_ver_evento(cur, uid, ev):
            raise HTTPException(status_code=403, detail="Sem permissao pra ver esse evento")
        # mascara privacidade se nao for organizador nem participante
        eh_participante = _user_e_participante(cur, uid, ev["id"])
        if ev["visibilidade"] == "privada" and int(ev["organizador_id"]) != uid and not eh_participante:
            ev["titulo"] = "Ocupado"
            ev["descricao_html"] = None
            ev["local"] = None
            ev["link_online"] = None
        # inclui participantes (respeitando privacidade)
        cur.execute("""
            SELECT p.id, p.user_id, p.email_externo, p.nome_externo,
                   p.papel, p.rsvp, p.respondido_em, p.convite_enviado_em,
                   u.name AS user_name, u.email AS user_email, u.avatar_url AS user_avatar
            FROM ag_participantes p
            LEFT JOIN users u ON u.id = p.user_id
            WHERE p.evento_id=%s
            ORDER BY p.papel='organizador' DESC, p.criado_em ASC
        """, (ev["id"],))
        participantes = cur.fetchall()
        # nao expor rsvp_token pra ninguem via GET
        return {"success": True, "evento": ev, "participantes": participantes}
    finally:
        cur.close(); conn.close()


@router.post("/eventos")
def criar_evento(body: EventoCreate, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    dt_ini = _parse_dt(body.inicio)
    dt_fim = _parse_dt(body.fim)
    if dt_fim < dt_ini:
        raise HTTPException(status_code=400, detail="fim antes de inicio")

    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        if not _user_pode_editar_calendario(cur, uid, body.calendario_id):
            raise HTTPException(status_code=403, detail="Sem permissao pra criar evento neste calendario")
        cur.execute("""
            INSERT INTO ag_eventos
              (calendario_id, titulo, descricao_html, local, link_online, meeting_code,
               dia_inteiro, inicio, fim, cor, visibilidade, disponibilidade,
               status_op, organizador_id, criado_por)
            VALUES (%s,%s,%s,%s,%s,%s, %s,%s,%s, %s,%s,%s, 'agendado', %s, %s)
        """, (body.calendario_id, body.titulo, body.descricao_html, body.local,
              body.link_online, body.meeting_code,
              1 if body.dia_inteiro else 0, dt_ini, dt_fim,
              body.cor, body.visibilidade, body.disponibilidade,
              uid, uid))
        new_id = cur.lastrowid
        cur.execute("""
            INSERT INTO ag_audit (evento_id, actor_id, action)
            VALUES (%s, %s, 'created')
        """, (new_id, uid))
        conn.commit()
        return {"success": True, "id": new_id}
    finally:
        cur.close(); conn.close()


@router.patch("/eventos/{ev_id}")
def editar_evento(ev_id: int, body: EventoUpdate, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, calendario_id, organizador_id, inicio, fim
            FROM ag_eventos WHERE id=%s AND deleted_at IS NULL
        """, (ev_id,))
        ev = cur.fetchone()
        if not ev:
            raise HTTPException(status_code=404, detail="Evento nao encontrado")
        if not _pode_editar_evento(cur, uid, ev):
            raise HTTPException(status_code=403, detail="Sem permissao pra editar este evento")

        sets, params = [], []
        for field in ("titulo", "descricao_html", "local", "link_online", "meeting_code",
                      "cor", "visibilidade", "disponibilidade", "status_op"):
            v = getattr(body, field)
            if v is not None:
                sets.append(f"{field}=%s"); params.append(v)
        if body.dia_inteiro is not None:
            sets.append("dia_inteiro=%s"); params.append(1 if body.dia_inteiro else 0)

        novo_ini = _parse_dt(body.inicio) if body.inicio else None
        novo_fim = _parse_dt(body.fim) if body.fim else None
        if novo_ini is not None:
            sets.append("inicio=%s"); params.append(novo_ini)
        if novo_fim is not None:
            sets.append("fim=%s"); params.append(novo_fim)

        ini_final = novo_ini or ev["inicio"]
        fim_final = novo_fim or ev["fim"]
        if fim_final < ini_final:
            raise HTTPException(status_code=400, detail="fim antes de inicio")

        if not sets:
            return {"success": True, "noop": True}

        sets.append("alterado_em=NOW()"); sets.append("alterado_por=%s")
        params.append(uid)
        params.append(ev_id)
        cur.execute(f"UPDATE ag_eventos SET {', '.join(sets)} WHERE id=%s", tuple(params))
        cur.execute("""
            INSERT INTO ag_audit (evento_id, actor_id, action)
            VALUES (%s, %s, 'updated')
        """, (ev_id, uid))
        conn.commit()
        return {"success": True}
    finally:
        cur.close(); conn.close()


@router.post("/eventos/{ev_id}/cancelar")
def cancelar_evento(ev_id: int, body: CancelarBody, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT e.id, e.organizador_id, e.calendario_id, e.status_op,
                   e.titulo, e.inicio, e.fim, e.local, e.descricao_html,
                   o.name AS org_nome, o.email AS org_email
            FROM ag_eventos e
            LEFT JOIN users o ON o.id = e.organizador_id
            WHERE e.id=%s AND e.deleted_at IS NULL
        """, (ev_id,))
        ev = cur.fetchone()
        if not ev:
            raise HTTPException(status_code=404, detail="Evento nao encontrado")
        if not _pode_editar_evento(cur, uid, ev):
            raise HTTPException(status_code=403, detail="Sem permissao")
        if ev["status_op"] == "cancelado":
            return {"success": True, "noop": True}
        cur.execute("""
            UPDATE ag_eventos
            SET status_op='cancelado', cancelado_em=NOW(), cancelado_por=%s, cancel_motivo=%s,
                alterado_em=NOW(), alterado_por=%s
            WHERE id=%s
        """, (uid, body.motivo, uid, ev_id))
        cur.execute("""
            INSERT INTO ag_audit (evento_id, actor_id, action, metadata_json)
            VALUES (%s, %s, 'cancelled', JSON_OBJECT('motivo', %s))
        """, (ev_id, uid, body.motivo))
        # dispara email de CANCEL pra todos participantes
        cur.execute("""
            SELECT p.user_id, p.email_externo, p.nome_externo, p.rsvp_token,
                   u.email AS user_email, u.name AS user_name
            FROM ag_participantes p
            LEFT JOIN users u ON u.id = p.user_id
            WHERE p.evento_id=%s AND p.papel != 'organizador'
        """, (ev_id,))
        participantes_cancel = cur.fetchall()
        conn.commit()
        base_url = (os.getenv("PUBLIC_BASE_URL") or "https://cpecontrol.cpetecnologia.com.br").rstrip("/")
        ics_uid = f"agenda-v2-evt-{ev_id}@cpecontrol"
        for p in participantes_cancel:
            email = p.get("user_email") or p.get("email_externo")
            nome = p.get("user_name") or p.get("nome_externo")
            if not email:
                continue
            try:
                enviar_convite_agenda(
                    dest_email=email, dest_nome=nome,
                    titulo=ev["titulo"], host_nome=ev["org_nome"] or "CPE",
                    host_email=ev["org_email"] or "no-reply@cpetecnologia.com.br",
                    inicio=ev["inicio"], fim=ev["fim"],
                    local=ev["local"], descricao=ev.get("descricao_html"),
                    ics_uid=ics_uid, rsvp_token=None,
                    base_url=base_url, method="CANCEL", seq=1,
                    motivo=body.motivo,
                )
            except Exception as e:
                logger.warning(f"[agenda] falha email cancel: {e}")
        return {"success": True}
    finally:
        cur.close(); conn.close()


@router.delete("/eventos/{ev_id}")
def deletar_evento(ev_id: int, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, organizador_id, calendario_id
            FROM ag_eventos WHERE id=%s AND deleted_at IS NULL
        """, (ev_id,))
        ev = cur.fetchone()
        if not ev:
            raise HTTPException(status_code=404, detail="Evento nao encontrado")
        if not _pode_editar_evento(cur, uid, ev):
            raise HTTPException(status_code=403, detail="Sem permissao")
        cur.execute("UPDATE ag_eventos SET deleted_at=NOW() WHERE id=%s", (ev_id,))
        cur.execute("""
            INSERT INTO ag_audit (evento_id, actor_id, action)
            VALUES (%s, %s, 'deleted')
        """, (ev_id, uid))
        conn.commit()
        return {"success": True}
    finally:
        cur.close(); conn.close()


@router.post("/eventos/{ev_id}/duplicar")
def duplicar_evento(ev_id: int, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT * FROM ag_eventos WHERE id=%s AND deleted_at IS NULL
        """, (ev_id,))
        src = cur.fetchone()
        if not src:
            raise HTTPException(status_code=404, detail="Evento nao encontrado")
        if not _user_pode_editar_calendario(cur, uid, src["calendario_id"]) and int(src["organizador_id"]) != uid:
            raise HTTPException(status_code=403, detail="Sem permissao")
        cur.execute("""
            INSERT INTO ag_eventos
              (calendario_id, titulo, descricao_html, local, link_online, meeting_code,
               dia_inteiro, inicio, fim, cor, visibilidade, disponibilidade,
               status_op, organizador_id, criado_por)
            VALUES (%s,%s,%s,%s,%s,%s, %s,%s,%s, %s,%s,%s, 'agendado', %s, %s)
        """, (src["calendario_id"], f"{src['titulo']} (copia)", src["descricao_html"],
              src["local"], src["link_online"], src["meeting_code"],
              src["dia_inteiro"], src["inicio"], src["fim"],
              src["cor"], src["visibilidade"], src["disponibilidade"], uid, uid))
        new_id = cur.lastrowid
        cur.execute("""
            INSERT INTO ag_audit (evento_id, actor_id, action, metadata_json)
            VALUES (%s, %s, 'created', JSON_OBJECT('duplicado_de', %s))
        """, (new_id, uid, ev_id))
        conn.commit()
        return {"success": True, "id": new_id}
    finally:
        cur.close(); conn.close()


# ---------------------------------------------------------------------
# PARTICIPANTES (Sprint 3)
# ---------------------------------------------------------------------
import secrets as _secrets


def _rsvp_token() -> str:
    # 48 chars pra bater com CHAR(48) da tabela
    return _secrets.token_urlsafe(36)[:48]


@router.get("/eventos/{ev_id}/participantes")
def listar_participantes(ev_id: int, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, calendario_id, organizador_id, criado_por
            FROM ag_eventos WHERE id=%s AND deleted_at IS NULL
        """, (ev_id,))
        ev = cur.fetchone()
        if not ev:
            raise HTTPException(status_code=404, detail="Evento nao encontrado")
        if not _pode_ver_evento(cur, uid, ev):
            raise HTTPException(status_code=403, detail="Sem permissao")
        cur.execute("""
            SELECT p.id, p.user_id, p.email_externo, p.nome_externo,
                   p.papel, p.rsvp, p.respondido_em, p.convite_enviado_em, p.criado_em,
                   u.name AS user_name, u.email AS user_email, u.avatar_url AS user_avatar
            FROM ag_participantes p
            LEFT JOIN users u ON u.id = p.user_id
            WHERE p.evento_id=%s
            ORDER BY p.papel='organizador' DESC, p.criado_em ASC
        """, (ev_id,))
        return {"success": True, "participantes": cur.fetchall()}
    finally:
        cur.close(); conn.close()


@router.post("/eventos/{ev_id}/participantes")
def adicionar_participantes(ev_id: int, body: ParticipantesAddBody, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT e.id, e.calendario_id, e.organizador_id, e.titulo, e.local,
                   e.descricao_html, e.inicio, e.fim,
                   o.name AS org_nome, o.email AS org_email
            FROM ag_eventos e
            LEFT JOIN users o ON o.id = e.organizador_id
            WHERE e.id=%s AND e.deleted_at IS NULL
        """, (ev_id,))
        ev = cur.fetchone()
        if not ev:
            raise HTTPException(status_code=404, detail="Evento nao encontrado")
        # Sprint 3: so organizador ou quem edita calendario pode gerenciar participantes
        if not _pode_editar_evento(cur, uid, ev):
            raise HTTPException(status_code=403, detail="Sem permissao pra convidar")

        base_url = (os.getenv("PUBLIC_BASE_URL") or "https://cpecontrol.cpetecnologia.com.br").rstrip("/")
        ics_uid = f"agenda-v2-evt-{ev_id}@cpecontrol"

        adicionados: List[dict] = []
        for p in body.participantes:
            if p.user_id:
                # interno
                # user existe?
                cur.execute("SELECT id, name FROM users WHERE id=%s AND is_active=1", (p.user_id,))
                u = cur.fetchone()
                if not u:
                    continue
                # ja existe convite?
                cur.execute(
                    "SELECT id FROM ag_participantes WHERE evento_id=%s AND user_id=%s",
                    (ev_id, p.user_id),
                )
                if cur.fetchone():
                    continue
                cur.execute("""
                    INSERT INTO ag_participantes (evento_id, user_id, papel, convite_enviado_em)
                    VALUES (%s, %s, %s, NOW())
                """, (ev_id, p.user_id, p.papel))
                new_pid = cur.lastrowid
                adicionados.append({"id": new_pid, "user_id": p.user_id, "nome": u["name"]})
                cur.execute("""
                    INSERT INTO ag_audit (evento_id, actor_id, action, metadata_json)
                    VALUES (%s, %s, 'participant_added', JSON_OBJECT('user_id', %s))
                """, (ev_id, uid, p.user_id))
                # busca email do user pra convite
                cur.execute("SELECT email FROM users WHERE id=%s", (p.user_id,))
                em_row = cur.fetchone()
                if em_row and em_row.get("email"):
                    try:
                        enviar_convite_agenda(
                            dest_email=em_row["email"], dest_nome=u["name"],
                            titulo=ev["titulo"], host_nome=ev["org_nome"] or "CPE",
                            host_email=ev["org_email"] or "no-reply@cpetecnologia.com.br",
                            inicio=ev["inicio"], fim=ev["fim"],
                            local=ev["local"], descricao=ev.get("descricao_html"),
                            ics_uid=ics_uid, rsvp_token=None,  # interno usa botao no app
                            base_url=base_url, method="REQUEST",
                        )
                    except Exception as e:
                        logger.warning(f"[agenda] falha email convite interno: {e}")
            elif p.email:
                # externo
                email = (p.email or "").strip().lower()
                if "@" not in email:
                    continue
                cur.execute(
                    "SELECT id FROM ag_participantes WHERE evento_id=%s AND email_externo=%s",
                    (ev_id, email),
                )
                if cur.fetchone():
                    continue
                # rsvp_token unico (retenta em caso improvavel de colisao)
                for _ in range(5):
                    tok = _rsvp_token()
                    cur.execute("SELECT 1 FROM ag_participantes WHERE rsvp_token=%s LIMIT 1", (tok,))
                    if not cur.fetchone():
                        break
                else:
                    raise HTTPException(status_code=500, detail="Nao conseguiu gerar rsvp_token unico")
                cur.execute("""
                    INSERT INTO ag_participantes
                      (evento_id, email_externo, nome_externo, papel, rsvp_token, convite_enviado_em)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """, (ev_id, email, p.nome or None, p.papel, tok))
                new_pid = cur.lastrowid
                adicionados.append({
                    "id": new_pid, "email_externo": email, "nome_externo": p.nome, "rsvp_token": tok,
                })
                cur.execute("""
                    INSERT INTO ag_audit (evento_id, actor_id, action, metadata_json)
                    VALUES (%s, %s, 'participant_added', JSON_OBJECT('email', %s))
                """, (ev_id, uid, email))
                try:
                    enviar_convite_agenda(
                        dest_email=email, dest_nome=p.nome,
                        titulo=ev["titulo"], host_nome=ev["org_nome"] or "CPE",
                        host_email=ev["org_email"] or "no-reply@cpetecnologia.com.br",
                        inicio=ev["inicio"], fim=ev["fim"],
                        local=ev["local"], descricao=ev.get("descricao_html"),
                        ics_uid=ics_uid, rsvp_token=tok,
                        base_url=base_url, method="REQUEST",
                    )
                except Exception as e:
                    logger.warning(f"[agenda] falha email convite externo: {e}")
        conn.commit()
        return {"success": True, "adicionados": adicionados}
    finally:
        cur.close(); conn.close()


@router.delete("/eventos/{ev_id}/participantes/{pid}")
def remover_participante(ev_id: int, pid: int, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT e.id, e.calendario_id, e.organizador_id, p.papel, p.user_id, p.email_externo
            FROM ag_eventos e
            JOIN ag_participantes p ON p.evento_id = e.id
            WHERE e.id=%s AND p.id=%s AND e.deleted_at IS NULL
        """, (ev_id, pid))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Participante nao encontrado")
        if row["papel"] == "organizador":
            raise HTTPException(status_code=400, detail="Organizador nao pode ser removido")
        if not _pode_editar_evento(cur, uid, {
            "id": ev_id, "calendario_id": row["calendario_id"], "organizador_id": row["organizador_id"],
        }):
            raise HTTPException(status_code=403, detail="Sem permissao")
        cur.execute("DELETE FROM ag_participantes WHERE id=%s", (pid,))
        cur.execute("""
            INSERT INTO ag_audit (evento_id, actor_id, action, metadata_json)
            VALUES (%s, %s, 'participant_removed',
                    JSON_OBJECT('user_id', %s, 'email', %s))
        """, (ev_id, uid, row["user_id"], row["email_externo"]))
        conn.commit()
        return {"success": True}
    finally:
        cur.close(); conn.close()


# ---------------------------------------------------------------------
# COMPARTILHAMENTO (Sprint 4)
# ---------------------------------------------------------------------
def _valida_destino(cur, tipo: str, dest_id: int) -> bool:
    if tipo == "user":
        cur.execute("SELECT 1 FROM users WHERE id=%s AND is_active=1 LIMIT 1", (dest_id,))
    else:
        cur.execute("SELECT 1 FROM cpe_grupo WHERE id=%s LIMIT 1", (dest_id,))
    return cur.fetchone() is not None


@router.post("/calendarios/{cal_id}/compartilhar")
def compartilhar_calendario(cal_id: int, body: ShareCalendarioBody, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        # so quem edita o calendario pode compartilhar
        if not _user_pode_editar_calendario(cur, uid, cal_id):
            raise HTTPException(status_code=403, detail="Sem permissao")
        if not _valida_destino(cur, body.destino_tipo, body.destino_id):
            raise HTTPException(status_code=400, detail="Destino invalido")
        # ja existe share ativo com esse destino? atualiza permissao
        col = "destino_user_id" if body.destino_tipo == "user" else "destino_group_id"
        cur.execute(f"""
            SELECT id, permissao FROM ag_calendario_compartilhamentos
            WHERE calendario_id=%s AND destino_tipo=%s AND {col}=%s AND revogado_em IS NULL
            LIMIT 1
        """, (cal_id, body.destino_tipo, body.destino_id))
        exist = cur.fetchone()
        if exist:
            if exist["permissao"] != body.permissao:
                cur.execute("UPDATE ag_calendario_compartilhamentos SET permissao=%s WHERE id=%s",
                            (body.permissao, exist["id"]))
                conn.commit()
                return {"success": True, "id": exist["id"], "atualizado": True}
            return {"success": True, "id": exist["id"], "noop": True}
        cols = "destino_user_id" if body.destino_tipo == "user" else "destino_group_id"
        cur.execute(f"""
            INSERT INTO ag_calendario_compartilhamentos
              (calendario_id, destino_tipo, {cols}, permissao, concedido_por)
            VALUES (%s, %s, %s, %s, %s)
        """, (cal_id, body.destino_tipo, body.destino_id, body.permissao, uid))
        conn.commit()
        return {"success": True, "id": cur.lastrowid}
    finally:
        cur.close(); conn.close()


@router.get("/calendarios/{cal_id}/compartilhamentos")
def listar_shares_cal(cal_id: int, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        if not _user_pode_editar_calendario(cur, uid, cal_id):
            raise HTTPException(status_code=403, detail="Sem permissao")
        cur.execute("""
            SELECT s.id, s.destino_tipo, s.destino_user_id, s.destino_group_id, s.permissao,
                   s.concedido_em, s.concedido_por,
                   u.name AS user_name, u.email AS user_email,
                   g.name AS grupo_nome
            FROM ag_calendario_compartilhamentos s
            LEFT JOIN users u ON u.id = s.destino_user_id
            LEFT JOIN cpe_grupo g ON g.id = s.destino_group_id
            WHERE s.calendario_id=%s AND s.revogado_em IS NULL
            ORDER BY s.concedido_em DESC
        """, (cal_id,))
        return {"success": True, "shares": cur.fetchall()}
    finally:
        cur.close(); conn.close()


@router.delete("/calendarios/{cal_id}/compartilhamentos/{sid}")
def revogar_share_cal(cal_id: int, sid: int, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        if not _user_pode_editar_calendario(cur, uid, cal_id):
            raise HTTPException(status_code=403, detail="Sem permissao")
        cur.execute("""
            UPDATE ag_calendario_compartilhamentos
            SET revogado_em=NOW()
            WHERE id=%s AND calendario_id=%s AND revogado_em IS NULL
        """, (sid, cal_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Compartilhamento nao encontrado")
        conn.commit()
        return {"success": True}
    finally:
        cur.close(); conn.close()


@router.post("/eventos/{ev_id}/compartilhar")
def compartilhar_evento(ev_id: int, body: ShareEventoBody, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, calendario_id, organizador_id FROM ag_eventos WHERE id=%s AND deleted_at IS NULL", (ev_id,))
        ev = cur.fetchone()
        if not ev:
            raise HTTPException(status_code=404, detail="Evento nao encontrado")
        if not _pode_editar_evento(cur, uid, ev):
            raise HTTPException(status_code=403, detail="Sem permissao")
        if not _valida_destino(cur, body.destino_tipo, body.destino_id):
            raise HTTPException(status_code=400, detail="Destino invalido")
        col = "destino_user_id" if body.destino_tipo == "user" else "destino_group_id"
        cur.execute(f"""
            SELECT id FROM ag_evento_compartilhamentos
            WHERE evento_id=%s AND destino_tipo=%s AND {col}=%s LIMIT 1
        """, (ev_id, body.destino_tipo, body.destino_id))
        if cur.fetchone():
            return {"success": True, "noop": True}
        cur.execute(f"""
            INSERT INTO ag_evento_compartilhamentos
              (evento_id, destino_tipo, {col}, concedido_por)
            VALUES (%s, %s, %s, %s)
        """, (ev_id, body.destino_tipo, body.destino_id, uid))
        cur.execute("""
            INSERT INTO ag_audit (evento_id, actor_id, action, metadata_json)
            VALUES (%s, %s, 'shared',
              JSON_OBJECT('destino_tipo', %s, 'destino_id', %s))
        """, (ev_id, uid, body.destino_tipo, body.destino_id))
        conn.commit()
        return {"success": True, "id": cur.lastrowid}
    finally:
        cur.close(); conn.close()


@router.delete("/eventos/{ev_id}/compartilhamentos/{sid}")
def revogar_share_ev(ev_id: int, sid: int, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, calendario_id, organizador_id FROM ag_eventos WHERE id=%s AND deleted_at IS NULL", (ev_id,))
        ev = cur.fetchone()
        if not ev:
            raise HTTPException(status_code=404, detail="Evento nao encontrado")
        if not _pode_editar_evento(cur, uid, ev):
            raise HTTPException(status_code=403, detail="Sem permissao")
        cur.execute("""
            DELETE FROM ag_evento_compartilhamentos
            WHERE id=%s AND evento_id=%s
        """, (sid, ev_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Compartilhamento nao encontrado")
        conn.commit()
        return {"success": True}
    finally:
        cur.close(); conn.close()


# ---------------------------------------------------------------------
# CONFLITOS
# ---------------------------------------------------------------------
@router.get("/conflitos")
def detectar_conflitos(
    request: Request,
    inicio: str = Query(..., description="YYYY-MM-DDTHH:MM"),
    fim: str = Query(..., description="YYYY-MM-DDTHH:MM"),
    user_ids: Optional[str] = Query(None, description="user_ids separados por virgula. Default = user logado"),
    excluir_evento: Optional[int] = Query(None, description="Ignora este evento_id (uso em edicao)"),
):
    """Retorna, por user pedido, os eventos que colidem com [inicio, fim).
    Considera apenas eventos onde o user e organizador OU participante,
    e cujo status_op != 'cancelado' e disponibilidade != 'livre'."""
    user = _exigir_user(request)
    uid = int(user["id"])
    dt_ini = _parse_dt(inicio)
    dt_fim = _parse_dt(fim)
    if dt_fim <= dt_ini:
        raise HTTPException(status_code=400, detail="fim precisa ser depois de inicio")
    uids: List[int] = []
    if user_ids:
        try:
            uids = [int(x) for x in user_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="user_ids invalidos")
    if not uids:
        uids = [uid]
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        marc = ",".join(["%s"] * len(uids))
        # eventos onde o user aparece (organizador OU participante) e sobrepoem [ini,fim)
        sql = f"""
            SELECT DISTINCT e.id, e.titulo, e.inicio, e.fim, e.status_op, e.disponibilidade,
                   e.organizador_id, o.name AS organizador_nome,
                   (
                     SELECT GROUP_CONCAT(DISTINCT COALESCE(p.user_id, 0))
                     FROM ag_participantes p
                     WHERE p.evento_id = e.id AND p.user_id IN ({marc})
                   ) AS user_ids_participantes
            FROM ag_eventos e
            LEFT JOIN users o ON o.id = e.organizador_id
            LEFT JOIN ag_participantes pp ON pp.evento_id = e.id
            WHERE e.deleted_at IS NULL
              AND e.status_op <> 'cancelado'
              AND e.disponibilidade <> 'livre'
              AND e.fim > %s AND e.inicio < %s
              AND (e.organizador_id IN ({marc}) OR pp.user_id IN ({marc}))
              {("AND e.id <> %s" if excluir_evento else "")}
            ORDER BY e.inicio ASC
        """
        params = list(uids) + [dt_ini, dt_fim] + list(uids) + list(uids)
        if excluir_evento:
            params.append(excluir_evento)
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        # mapa user_id -> conflitos
        by_user: dict = {u: [] for u in uids}
        for r in rows:
            ids_str = (r.pop("user_ids_participantes") or "") or ""
            ids_env = set()
            for tok in ids_str.split(","):
                tok = tok.strip()
                if tok and tok.isdigit():
                    ids_env.add(int(tok))
            for u in uids:
                if int(r["organizador_id"]) == u or u in ids_env:
                    by_user[u].append({
                        "evento_id": r["id"], "titulo": r["titulo"],
                        "inicio": r["inicio"], "fim": r["fim"],
                        "status_op": r["status_op"], "disponibilidade": r["disponibilidade"],
                        "organizador_id": r["organizador_id"], "organizador_nome": r["organizador_nome"],
                    })
        return {"success": True, "conflitos": by_user}
    finally:
        cur.close(); conn.close()


# ---------------------------------------------------------------------
# ANEXOS (Sprint 6)
# ---------------------------------------------------------------------
_AG_ANEXOS_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "web", "uploads", "agenda",
)
_ANEXO_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_ANEXO_MIMES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/csv": ".csv",
    "text/plain": ".txt",
}


def _safe_ext(mime: str, filename: str) -> str:
    """Retorna extensao whitelisted. Preferencia MIME > filename ext."""
    if mime in _ANEXO_MIMES:
        return _ANEXO_MIMES[mime]
    ext = os.path.splitext(filename or "")[1].lower()
    if ext in _ANEXO_MIMES.values():
        return ext
    return ""  # nao permitido


@router.post("/eventos/{ev_id}/anexos")
async def upload_anexo(ev_id: int, request: Request, file: UploadFile = File(...)):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, calendario_id, organizador_id FROM ag_eventos WHERE id=%s AND deleted_at IS NULL", (ev_id,))
        ev = cur.fetchone()
        if not ev:
            raise HTTPException(status_code=404, detail="Evento nao encontrado")
        # participante ou editor pode upload
        if not (_pode_editar_evento(cur, uid, ev) or _user_e_participante(cur, uid, ev_id)):
            raise HTTPException(status_code=403, detail="Sem permissao")

        ext = _safe_ext(file.content_type or "", file.filename or "")
        if not ext:
            raise HTTPException(status_code=400,
                                detail="Tipo nao permitido. Aceitos: PDF/DOCX/XLSX/CSV/TXT/imagens.")
        content = await file.read()
        if len(content) > _ANEXO_MAX_BYTES:
            raise HTTPException(status_code=400, detail="Arquivo maior que 10MB")
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Arquivo vazio")

        yyyy_mm = datetime.now().strftime("%Y-%m")
        subdir = os.path.join(_AG_ANEXOS_ROOT, yyyy_mm)
        os.makedirs(subdir, exist_ok=True)
        import secrets as _s
        stored_name = f"{_s.token_urlsafe(16)}{ext}"
        full_path = os.path.join(subdir, stored_name)
        with open(full_path, "wb") as f:
            f.write(content)
        # storage_path relativo (nao expor abs path)
        rel_path = os.path.join("agenda", yyyy_mm, stored_name).replace("\\", "/")

        cur.execute("""
            INSERT INTO ag_anexos
              (evento_id, filename, storage_path, mime, size_bytes, uploaded_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (ev_id, file.filename[:255], rel_path, file.content_type or "application/octet-stream",
              len(content), uid))
        new_id = cur.lastrowid
        cur.execute("""
            INSERT INTO ag_audit (evento_id, actor_id, action, metadata_json)
            VALUES (%s, %s, 'attachment_added',
              JSON_OBJECT('anexo_id', %s, 'filename', %s, 'size', %s))
        """, (ev_id, uid, new_id, file.filename, len(content)))
        conn.commit()
        return {
            "success": True, "id": new_id,
            "filename": file.filename, "size_bytes": len(content),
            "mime": file.content_type,
        }
    finally:
        cur.close(); conn.close()


@router.get("/eventos/{ev_id}/anexos")
def listar_anexos(ev_id: int, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, calendario_id, organizador_id FROM ag_eventos WHERE id=%s AND deleted_at IS NULL", (ev_id,))
        ev = cur.fetchone()
        if not ev:
            raise HTTPException(status_code=404, detail="Evento nao encontrado")
        if not _pode_ver_evento(cur, uid, ev):
            raise HTTPException(status_code=403, detail="Sem permissao")
        cur.execute("""
            SELECT a.id, a.filename, a.mime, a.size_bytes, a.uploaded_em,
                   a.uploaded_by, u.name AS uploaded_by_nome
            FROM ag_anexos a
            LEFT JOIN users u ON u.id = a.uploaded_by
            WHERE a.evento_id=%s AND a.deleted_at IS NULL
            ORDER BY a.uploaded_em ASC
        """, (ev_id,))
        return {"success": True, "anexos": cur.fetchall()}
    finally:
        cur.close(); conn.close()


@router.get("/eventos/{ev_id}/anexos/{aid}")
def download_anexo(ev_id: int, aid: int, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT a.filename, a.storage_path, a.mime, e.id AS eid,
                   e.calendario_id, e.organizador_id
            FROM ag_anexos a
            JOIN ag_eventos e ON e.id = a.evento_id
            WHERE a.id=%s AND a.evento_id=%s AND a.deleted_at IS NULL AND e.deleted_at IS NULL
        """, (aid, ev_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Anexo nao encontrado")
        ev = {"id": row["eid"], "calendario_id": row["calendario_id"], "organizador_id": row["organizador_id"]}
        if not _pode_ver_evento(cur, uid, ev):
            raise HTTPException(status_code=403, detail="Sem permissao")
        # normaliza path — nao deixa navegar pra fora do _AG_ANEXOS_ROOT
        base = os.path.dirname(_AG_ANEXOS_ROOT)  # web/uploads
        full = os.path.normpath(os.path.join(base, row["storage_path"]))
        if not full.startswith(os.path.normpath(_AG_ANEXOS_ROOT)):
            raise HTTPException(status_code=400, detail="Path invalido")
        if not os.path.exists(full):
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado no disco")
        return FileResponse(full, media_type=row["mime"], filename=row["filename"])
    finally:
        cur.close(); conn.close()


@router.delete("/eventos/{ev_id}/anexos/{aid}")
def deletar_anexo(ev_id: int, aid: int, request: Request):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT a.filename, a.uploaded_by, e.id AS eid,
                   e.calendario_id, e.organizador_id
            FROM ag_anexos a
            JOIN ag_eventos e ON e.id = a.evento_id
            WHERE a.id=%s AND a.evento_id=%s AND a.deleted_at IS NULL
        """, (aid, ev_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Anexo nao encontrado")
        ev = {"id": row["eid"], "calendario_id": row["calendario_id"], "organizador_id": row["organizador_id"]}
        # remove: uploader ou editor do evento
        if int(row["uploaded_by"]) != uid and not _pode_editar_evento(cur, uid, ev):
            raise HTTPException(status_code=403, detail="Sem permissao")
        cur.execute("UPDATE ag_anexos SET deleted_at=NOW() WHERE id=%s", (aid,))
        cur.execute("""
            INSERT INTO ag_audit (evento_id, actor_id, action, metadata_json)
            VALUES (%s, %s, 'attachment_removed', JSON_OBJECT('anexo_id', %s, 'filename', %s))
        """, (ev_id, uid, aid, row["filename"]))
        conn.commit()
        return {"success": True}
    finally:
        cur.close(); conn.close()


# ---------------------------------------------------------------------
# AUDIT
# ---------------------------------------------------------------------
@router.get("/eventos/{ev_id}/audit")
def listar_audit(ev_id: int, request: Request, limit: int = Query(50, ge=1, le=200)):
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, calendario_id, organizador_id FROM ag_eventos WHERE id=%s AND deleted_at IS NULL", (ev_id,))
        ev = cur.fetchone()
        if not ev:
            raise HTTPException(status_code=404, detail="Evento nao encontrado")
        if not _pode_editar_evento(cur, uid, ev):
            raise HTTPException(status_code=403, detail="Auditoria so pra editores")
        cur.execute("""
            SELECT a.id, a.action, a.metadata_json, a.criado_em,
                   a.actor_id, u.name AS actor_nome
            FROM ag_audit a
            LEFT JOIN users u ON u.id = a.actor_id
            WHERE a.evento_id=%s
            ORDER BY a.criado_em DESC, a.id DESC
            LIMIT %s
        """, (ev_id, limit))
        return {"success": True, "audit": cur.fetchall()}
    finally:
        cur.close(); conn.close()


# ---------------------------------------------------------------------
# RSVP PUBLICO EXTERNO (sem auth, so token)
# ---------------------------------------------------------------------
@router.get("/rsvp/{token}")
def rsvp_publico_get(token: str):
    """Info minima do evento pra montar o portal RSVP externo."""
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT p.id AS pid, p.rsvp, p.respondido_em, p.nome_externo, p.email_externo,
                   e.id AS evento_id, e.titulo, e.local, e.inicio, e.fim,
                   e.status_op, e.link_online,
                   o.name AS organizador_nome
            FROM ag_participantes p
            JOIN ag_eventos e ON e.id = p.evento_id
            LEFT JOIN users o ON o.id = e.organizador_id
            WHERE p.rsvp_token=%s AND e.deleted_at IS NULL
            LIMIT 1
        """, (token,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Token invalido ou expirado")
        return {
            "success": True,
            "evento": {
                "id": row["evento_id"], "titulo": row["titulo"], "local": row["local"],
                "inicio": row["inicio"], "fim": row["fim"], "status_op": row["status_op"],
                "link_online": row["link_online"],
                "organizador_nome": row["organizador_nome"],
            },
            "participante": {
                "nome": row["nome_externo"], "email": row["email_externo"],
                "rsvp": row["rsvp"], "respondido_em": row["respondido_em"],
            },
        }
    finally:
        cur.close(); conn.close()


class RsvpPublicoBody(BaseModel):
    status: str = Field(..., pattern="^(aceito|recusado|talvez)$")


@router.post("/rsvp/{token}")
def rsvp_publico_post(token: str, body: RsvpPublicoBody):
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT p.id, p.evento_id, p.rsvp, p.email_externo,
                   e.deleted_at, e.status_op, e.organizador_id
            FROM ag_participantes p
            JOIN ag_eventos e ON e.id = p.evento_id
            WHERE p.rsvp_token=%s LIMIT 1
        """, (token,))
        row = cur.fetchone()
        if not row or row["deleted_at"]:
            raise HTTPException(status_code=404, detail="Token invalido")
        if row["status_op"] == "cancelado":
            raise HTTPException(status_code=400, detail="Evento foi cancelado")
        old = row["rsvp"]
        cur.execute("""
            UPDATE ag_participantes SET rsvp=%s, respondido_em=NOW() WHERE id=%s
        """, (body.status, row["id"]))
        # audit: usa organizador como actor (FK) + marca externo no metadata
        cur.execute("""
            INSERT INTO ag_audit (evento_id, actor_id, action, metadata_json)
            VALUES (%s, %s, 'rsvp_changed',
              JSON_OBJECT('externo', TRUE, 'email', %s,
                          'de', %s, 'para', %s, 'participante_id', %s))
        """, (row["evento_id"], row["organizador_id"],
              row["email_externo"], old, body.status, row["id"]))
        conn.commit()
        return {"success": True, "rsvp": body.status}
    finally:
        cur.close(); conn.close()


# ---------------------------------------------------------------------
# RSVP INTERNO (Sprint 3 mantido)
# ---------------------------------------------------------------------
@router.post("/eventos/{ev_id}/rsvp")
def rsvp_interno(ev_id: int, body: RsvpBody, request: Request):
    """Participante INTERNO responde. Externo usa /rsvp/{token} publico (Sprint 5)."""
    user = _exigir_user(request)
    uid = int(user["id"])
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, rsvp FROM ag_participantes
            WHERE evento_id=%s AND user_id=%s LIMIT 1
        """, (ev_id, uid))
        p = cur.fetchone()
        if not p:
            raise HTTPException(status_code=404, detail="Voce nao e participante deste evento")
        old = p["rsvp"]
        cur.execute("""
            UPDATE ag_participantes SET rsvp=%s, respondido_em=NOW()
            WHERE id=%s
        """, (body.status, p["id"]))
        cur.execute("""
            INSERT INTO ag_audit (evento_id, actor_id, action, metadata_json)
            VALUES (%s, %s, 'rsvp_changed', JSON_OBJECT('de', %s, 'para', %s))
        """, (ev_id, uid, old, body.status))
        conn.commit()
        return {"success": True, "rsvp": body.status}
    finally:
        cur.close(); conn.close()
