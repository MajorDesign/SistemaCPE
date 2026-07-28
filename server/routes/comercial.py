"""
Router do modulo Comercial (Fase 1 — base).

Endpoints:
  Vendedores + Slots
    GET  /api/comercial/vendedores
    GET  /api/comercial/slots
    GET  /api/comercial/slots/{vendedor_id}
    PUT  /api/comercial/slots/{vendedor_id}  (max 3)

  Clientes
    GET  /api/comercial/clientes
    GET  /api/comercial/clientes/buscar?email=X
    POST /api/comercial/clientes            (upsert por email)
    GET  /api/comercial/clientes/{id}
    GET  /api/comercial/clientes/{id}/reunioes  (historico)

  Reunioes
    GET  /api/comercial/reunioes
    POST /api/comercial/reunioes
    GET  /api/comercial/reunioes/{id}
    PUT  /api/comercial/reunioes/{id}
    POST /api/comercial/reunioes/{id}/cancelar
    POST /api/comercial/reunioes/{id}/classificar

Permissao:
  Todos os endpoints exigem que o user seja ADMIN/TI/MANAGER
  OU pertenca ao grupo cujo nome (LOWER) e 'comercial'.
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from typing import Optional, List
from datetime import date, time

from fastapi import APIRouter, HTTPException, Request, Query, status, UploadFile, File, Form
from pydantic import BaseModel, EmailStr, Field, validator

from database import get_db_or_404, get_chat_db_or_404, convert_datetime_list, convert_datetime_to_string
from security import get_user_by_id
from routes.fleet import _get_user_id  # reusa helper de extracao de user id
from routes.meetings import _gen_code   # reusa gerador de codigo de meeting
from config import PUBLIC_BASE_URL

# Pasta de upload do material de apoio comercial
_UPLOAD_DIR_COMERCIAL = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "..", "web", "uploads", "comercial")
)
os.makedirs(_UPLOAD_DIR_COMERCIAL, exist_ok=True)

# Extensoes aceitas — apresentacoes, docs, imagens, videos leves
_MATERIAL_EXTS = {
    ".pdf", ".ppt", ".pptx", ".doc", ".docx", ".xls", ".xlsx",
    ".jpg", ".jpeg", ".png", ".webp", ".gif",
    ".mp4", ".webm", ".mov",
    ".txt", ".csv",
}
_MATERIAL_MAX_BYTES = 100 * 1024 * 1024  # 100 MB — apresentacoes com video costumam ser grandes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/comercial", tags=["comercial"])


# ============================================================
# HELPERS DE PERMISSAO
# ============================================================

def _user_dict(request: Request) -> dict:
    """Retorna dict do user autenticado com id, role, group_id."""
    uid = _get_user_id(request)
    user = get_user_by_id(uid)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado")
    return user


def _grupo_comercial_id(cursor) -> Optional[int]:
    """Resolve id do grupo Comercial em runtime (sem hard-code)."""
    cursor.execute("SELECT id FROM cpe_grupo WHERE LOWER(name) = 'comercial' LIMIT 1")
    row = cursor.fetchone()
    return row["id"] if row else None


def _pode_acessar_comercial(user: dict, cursor) -> bool:
    """True se user tem acesso ao modulo Comercial."""
    if (user.get("role") or "").upper() in ("ADMIN", "TI", "MANAGER"):
        return True
    grupo_id = _grupo_comercial_id(cursor)
    return grupo_id is not None and user.get("group_id") == grupo_id


def _require_comercial(request: Request, cursor):
    """Lanca 403 se user nao tem acesso. Retorna dict do user."""
    user = _user_dict(request)
    if not _pode_acessar_comercial(user, cursor):
        raise HTTPException(status_code=403, detail="Acesso restrito ao grupo Comercial")
    return user


def _base_url_do_request(request: Request) -> Optional[str]:
    """Extrai base URL (scheme://host[:port]) do request pra montar links
    absolutos no MESMO ambiente que criou o recurso.

    Ordem: header Origin > header Referer > None (caller usa fallback).
    Retorna sem barra final. Deixa None se nenhum header confiavel veio."""
    origin = (request.headers.get("origin") or "").strip()
    if origin:
        return origin.rstrip("/")
    referer = (request.headers.get("referer") or "").strip()
    if referer:
        try:
            from urllib.parse import urlparse
            p = urlparse(referer)
            if p.scheme and p.netloc:
                return f"{p.scheme}://{p.netloc}"
        except Exception:
            pass
    return None


def _pode_gerenciar_vendedores(user: dict, cursor) -> bool:
    """True se user pode configurar horarios de OUTROS vendedores.
    Vale pra: ADMIN/TI/MANAGER (globais) ou RESPONSAVEL_GRUPO do grupo Comercial."""
    role = (user.get("role") or "").upper()
    if role in ("ADMIN", "TI", "MANAGER"):
        return True
    if role == "RESPONSAVEL_GRUPO":
        grupo_id = _grupo_comercial_id(cursor)
        return grupo_id is not None and user.get("group_id") == grupo_id
    return False


# ============================================================
# SCHEMAS PYDANTIC
# ============================================================

class SlotIn(BaseModel):
    hora:  str  = Field(..., description="HH:MM ou HH:MM:SS")
    ordem: int  = Field(..., ge=1, le=3)
    ativo: bool = True

    @validator("hora")
    def _valida_hora(cls, v):
        v = v.strip()
        # aceita "09:00" ou "09:00:00"
        parts = v.split(":")
        if len(parts) < 2 or len(parts) > 3:
            raise ValueError("Hora invalida — use HH:MM")
        try:
            h, m = int(parts[0]), int(parts[1])
            s = int(parts[2]) if len(parts) == 3 else 0
        except ValueError:
            raise ValueError("Hora com caracteres invalidos")
        if not (0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59):
            raise ValueError("Hora fora do intervalo valido")
        return f"{h:02d}:{m:02d}:{s:02d}"


class SlotsIn(BaseModel):
    slots: List[SlotIn] = Field(..., min_items=0, max_items=3)


class ClienteIn(BaseModel):
    nome:              str            = Field(..., min_length=2, max_length=200)
    empresa:           Optional[str]  = Field(None, max_length=200)
    email:             Optional[EmailStr] = None
    telefone:          Optional[str]  = Field(None, max_length=30)
    produto_interesse: Optional[str]  = None


class ReuniaoIn(BaseModel):
    vendedor_id: int
    cliente_id:  int
    data:        date
    hora:        str
    slot_id:     Optional[int] = None
    meeting_url: Optional[str] = None
    meeting_id:  Optional[int] = None


class ClassificacaoIn(BaseModel):
    classificacao: str = Field(..., pattern="^(quente|morno|frio)$")
    comentario:    Optional[str] = None


# ============================================================
# VENDEDORES + SLOTS
# ============================================================

@router.get("/vendedores")
def listar_vendedores(request: Request):
    """Lista de vendedores. Regra de visibilidade:
      - ADMIN/TI/MANAGER e RESPONSAVEL_GRUPO Comercial: veem TODOS.
      - Vendedor USER comum: ve so a si mesmo (nao pode espiar agenda
        dos colegas).
    Retorna `can_manage` pra o frontend decidir mostrar botões de
    edicao globais."""
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        user = _require_comercial(request, cursor)
        can_manage = _pode_gerenciar_vendedores(user, cursor)
        grupo_id = _grupo_comercial_id(cursor)
        if grupo_id is None:
            return {"vendedores": [], "can_manage": can_manage, "me_id": user["id"]}
        if can_manage:
            cursor.execute("""
                SELECT u.id, u.name, u.email, u.role,
                       (SELECT COUNT(*) FROM comercial_vendedor_slots s
                         WHERE s.vendedor_id = u.id AND s.ativo = 1) AS slots_count
                  FROM users u
                 WHERE u.group_id = %s AND u.is_active = 1
                 ORDER BY u.name
            """, (grupo_id,))
        else:
            # USER comum ve so a si mesmo
            cursor.execute("""
                SELECT u.id, u.name, u.email, u.role,
                       (SELECT COUNT(*) FROM comercial_vendedor_slots s
                         WHERE s.vendedor_id = u.id AND s.ativo = 1) AS slots_count
                  FROM users u
                 WHERE u.id = %s AND u.is_active = 1
            """, (user["id"],))
        return {
            "vendedores": cursor.fetchall(),
            "can_manage": can_manage,
            "me_id":      user["id"],
        }
    finally:
        cursor.close(); conn.close()


@router.get("/slots")
def slots_do_user_atual(request: Request):
    """Slots do proprio user autenticado."""
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        user = _require_comercial(request, cursor)
        cursor.execute("""
            SELECT id, vendedor_id, hora, ordem, ativo
              FROM comercial_vendedor_slots
             WHERE vendedor_id = %s
             ORDER BY ordem
        """, (user["id"],))
        rows = cursor.fetchall()
        # hora vem como timedelta — normaliza pra string HH:MM
        for r in rows:
            r["hora"] = _time_to_str(r["hora"])
        return {"vendedor_id": user["id"], "slots": rows}
    finally:
        cursor.close(); conn.close()


@router.get("/slots/{vendedor_id}")
def slots_de_vendedor(vendedor_id: int, request: Request):
    """Slots de qualquer vendedor (visualizacao)."""
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _require_comercial(request, cursor)
        cursor.execute("""
            SELECT id, vendedor_id, hora, ordem, ativo
              FROM comercial_vendedor_slots
             WHERE vendedor_id = %s
             ORDER BY ordem
        """, (vendedor_id,))
        rows = cursor.fetchall()
        for r in rows:
            r["hora"] = _time_to_str(r["hora"])
        return {"vendedor_id": vendedor_id, "slots": rows}
    finally:
        cursor.close(); conn.close()


@router.put("/slots/{vendedor_id}")
def salvar_slots(vendedor_id: int, body: SlotsIn, request: Request):
    """Substitui os slots do vendedor. Podem alterar:
      - o proprio vendedor (self)
      - ADMIN/TI/MANAGER (roles globais)
      - RESPONSAVEL_GRUPO do grupo Comercial (gerencia sua equipe)
    """
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        user = _require_comercial(request, cursor)
        if user["id"] != vendedor_id and not _pode_gerenciar_vendedores(user, cursor):
            raise HTTPException(status_code=403,
                                detail="Sem permissao pra alterar horarios de outro vendedor")

        # Garante que ordem 1..3 aparece no maximo 1x (Pydantic max_items=3 mas
        # nao impede duplicar ordem=1 tres vezes)
        ordens = [s.ordem for s in body.slots]
        if len(ordens) != len(set(ordens)):
            raise HTTPException(status_code=400, detail="Cada ordem (1,2,3) deve aparecer no maximo 1 vez")

        # Substituicao completa: delete + insert dentro de txn
        cursor.execute("DELETE FROM comercial_vendedor_slots WHERE vendedor_id=%s", (vendedor_id,))
        for s in body.slots:
            cursor.execute("""
                INSERT INTO comercial_vendedor_slots (vendedor_id, hora, ordem, ativo)
                VALUES (%s, %s, %s, %s)
            """, (vendedor_id, s.hora, s.ordem, 1 if s.ativo else 0))
        conn.commit()

        return {"ok": True, "count": len(body.slots)}
    except HTTPException:
        conn.rollback(); raise
    except Exception as err:
        conn.rollback()
        logger.error(f"[COMERCIAL/SLOTS] erro: {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar slots: {err}")
    finally:
        cursor.close(); conn.close()


# ============================================================
# CLIENTES
# ============================================================

@router.get("/clientes")
def listar_clientes(request: Request, q: Optional[str] = Query(None, description="Busca em nome/empresa/email")):
    """Lista clientes (com filtro opcional por texto)."""
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _require_comercial(request, cursor)
        if q:
            like = f"%{q}%"
            cursor.execute("""
                SELECT id, nome, empresa, email, telefone, produto_interesse, created_at
                  FROM comercial_clientes
                 WHERE nome LIKE %s OR empresa LIKE %s OR email LIKE %s
                 ORDER BY created_at DESC
                 LIMIT 100
            """, (like, like, like))
        else:
            cursor.execute("""
                SELECT id, nome, empresa, email, telefone, produto_interesse, created_at
                  FROM comercial_clientes
                 ORDER BY created_at DESC
                 LIMIT 200
            """)
        return {"clientes": convert_datetime_list(cursor.fetchall())}
    finally:
        cursor.close(); conn.close()


@router.get("/clientes/buscar")
def buscar_cliente_por_email(request: Request, email: str = Query(..., min_length=3)):
    """Busca cliente EXATO por email (case-insensitive). Retorna None se nao achar."""
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _require_comercial(request, cursor)
        cursor.execute("""
            SELECT id, nome, empresa, email, telefone, produto_interesse, created_at
              FROM comercial_clientes
             WHERE LOWER(email) = LOWER(%s)
             LIMIT 1
        """, (email.strip(),))
        row = cursor.fetchone()
        if row:
            row = convert_datetime_to_string(row)
        return {"cliente": row}
    finally:
        cursor.close(); conn.close()


@router.post("/clientes", status_code=201)
def criar_ou_reusar_cliente(body: ClienteIn, request: Request):
    """Se email ja existe -> retorna o existente (reuso). Senao cria novo."""
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        user = _require_comercial(request, cursor)

        email_norm = (body.email or "").strip().lower() or None
        if email_norm:
            cursor.execute("SELECT id FROM comercial_clientes WHERE LOWER(email)=%s LIMIT 1", (email_norm,))
            existing = cursor.fetchone()
            if existing:
                # Retorna o existente sem alterar (evita sobrescrever dados)
                cursor.execute("""
                    SELECT id, nome, empresa, email, telefone, produto_interesse, created_at
                      FROM comercial_clientes WHERE id=%s
                """, (existing["id"],))
                return {"reused": True, "cliente": convert_datetime_to_string(cursor.fetchone())}

        cursor.execute("""
            INSERT INTO comercial_clientes
                (nome, empresa, email, telefone, produto_interesse, criado_por)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (body.nome.strip(), (body.empresa or "").strip() or None,
              email_norm, (body.telefone or "").strip() or None,
              (body.produto_interesse or "").strip() or None, user["id"]))
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("""
            SELECT id, nome, empresa, email, telefone, produto_interesse, created_at
              FROM comercial_clientes WHERE id=%s
        """, (new_id,))
        return {"reused": False, "cliente": convert_datetime_to_string(cursor.fetchone())}
    except HTTPException:
        conn.rollback(); raise
    except Exception as err:
        conn.rollback()
        logger.error(f"[COMERCIAL/CLIENTES] erro: {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar cliente: {err}")
    finally:
        cursor.close(); conn.close()


@router.get("/clientes/{cliente_id}")
def detalhes_cliente(cliente_id: int, request: Request):
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _require_comercial(request, cursor)
        cursor.execute("""
            SELECT id, nome, empresa, email, telefone, produto_interesse, created_at, updated_at
              FROM comercial_clientes WHERE id=%s
        """, (cliente_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Cliente nao encontrado")
        return {"cliente": convert_datetime_to_string(row)}
    finally:
        cursor.close(); conn.close()


@router.get("/clientes/{cliente_id}/reunioes")
def historico_reunioes_cliente(cliente_id: int, request: Request):
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _require_comercial(request, cursor)
        cursor.execute("""
            SELECT r.id, r.data, r.hora, r.status, r.classificacao, r.comentario,
                   r.meeting_url, r.agendado_em,
                   v.name AS vendedor_nome
              FROM comercial_reunioes r
              JOIN users v ON v.id = r.vendedor_id
             WHERE r.cliente_id = %s
             ORDER BY r.data DESC, r.hora DESC
        """, (cliente_id,))
        rows = cursor.fetchall()
        for r in rows:
            r["hora"] = _time_to_str(r["hora"])
            if r.get("data"):
                r["data"] = str(r["data"])
        return {"reunioes": convert_datetime_list(rows)}
    finally:
        cursor.close(); conn.close()


# ============================================================
# REUNIOES
# ============================================================

@router.get("/reunioes")
def listar_reunioes(
    request: Request,
    vendedor_id: Optional[int] = None,
    data_inicio: Optional[date] = None,
    data_fim:    Optional[date] = None,
    status_filtro: Optional[str] = Query(None, alias="status"),
):
    """Lista reunioes com filtros opcionais.

    Visibilidade:
      - ADMIN/TI/MANAGER e RESPONSAVEL_GRUPO Comercial: veem TODAS.
      - Vendedor USER comum: ve so as reunioes onde ele eh o vendedor
        que vai atender OU as que ele mesmo marcou. Nao consegue
        espiar a agenda de outros vendedores nem via query param."""
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        user = _require_comercial(request, cursor)
        can_manage = _pode_gerenciar_vendedores(user, cursor)
        where = ["1=1"]
        params: list = []
        if not can_manage:
            # Cerca por identidade: proprio vendedor OU proprio agendador.
            # Ignora vendedor_id do request pra evitar bypass.
            where.append("(r.vendedor_id = %s OR r.agendado_por = %s)")
            params.extend([user["id"], user["id"]])
        elif vendedor_id:
            where.append("r.vendedor_id = %s"); params.append(vendedor_id)
        if data_inicio:
            where.append("r.data >= %s"); params.append(data_inicio)
        if data_fim:
            where.append("r.data <= %s"); params.append(data_fim)
        if status_filtro:
            where.append("r.status = %s"); params.append(status_filtro)

        cursor.execute(f"""
            SELECT r.id, r.data, r.hora, r.status,
                   r.classificacao, r.comentario, r.meeting_url,
                   r.vendedor_id, v.name AS vendedor_nome,
                   r.cliente_id, c.nome AS cliente_nome, c.empresa AS cliente_empresa,
                   r.agendado_por, ap.name AS agendado_por_nome,
                   r.agendado_em, r.classificado_em
              FROM comercial_reunioes r
              JOIN users v            ON v.id  = r.vendedor_id
              JOIN comercial_clientes c ON c.id = r.cliente_id
         LEFT JOIN users ap           ON ap.id = r.agendado_por
             WHERE {' AND '.join(where)}
             ORDER BY r.data DESC, r.hora
             LIMIT 500
        """, tuple(params))
        rows = cursor.fetchall()
        for r in rows:
            r["hora"] = _time_to_str(r["hora"])
            if r.get("data"): r["data"] = str(r["data"])
        return {"reunioes": convert_datetime_list(rows)}
    finally:
        cursor.close(); conn.close()


@router.post("/reunioes", status_code=201)
def criar_reuniao(body: ReuniaoIn, request: Request):
    """Cria reuniao + gera meeting publico automaticamente.
    Valida que o slot esta disponivel.

    Autorizacao pra vendedor_id:
      - ADMIN/TI/MANAGER e RESPONSAVEL_GRUPO Comercial: qualquer vendedor.
      - Vendedor USER comum: so pode marcar reuniao com ele mesmo
        como vendedor (nao pode marcar em nome de colega)."""
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    chat_conn = None
    chat_cur = None
    try:
        user = _require_comercial(request, cursor)

        # Bloqueio: USER comum so marca pra si mesmo
        if not _pode_gerenciar_vendedores(user, cursor) and body.vendedor_id != user["id"]:
            raise HTTPException(
                status_code=403,
                detail="Voce so pode marcar reunioes com voce mesmo como vendedor",
            )

        # Confere cliente + vendedor existentes
        cursor.execute("""
            SELECT id, name FROM users
             WHERE id=%s AND is_active=1
        """, (body.vendedor_id,))
        vendedor = cursor.fetchone()
        if not vendedor:
            raise HTTPException(status_code=400, detail="Vendedor nao encontrado ou inativo")
        cursor.execute("""
            SELECT id, nome, empresa FROM comercial_clientes WHERE id=%s
        """, (body.cliente_id,))
        cliente = cursor.fetchone()
        if not cliente:
            raise HTTPException(status_code=400, detail="Cliente nao encontrado")

        # Slot ja ocupado nesta data+hora pro vendedor?
        cursor.execute("""
            SELECT id FROM comercial_reunioes
             WHERE vendedor_id=%s AND data=%s AND hora=%s
               AND status IN ('agendada','realizada')
             LIMIT 1
        """, (body.vendedor_id, body.data, body.hora))
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="Slot ja ocupado — escolha outro horario")

        # Gera meeting publico automaticamente (a menos que o caller ja tenha passado)
        meeting_url = body.meeting_url
        meeting_id  = body.meeting_id
        if not meeting_url:
            try:
                chat_conn = get_chat_db_or_404()
                chat_cur  = chat_conn.cursor(dictionary=True)
                code = _gen_code(chat_cur)
                empresa_str = f" ({cliente.get('empresa')})" if cliente.get('empresa') else ""
                nome_meeting = f"Reuniao {vendedor['name']} x {cliente['nome']}{empresa_str}".strip()[:150]
                chat_cur.execute("""
                    INSERT INTO chat_meeting_rooms (codigo, nome, criado_por)
                    VALUES (%s, %s, %s)
                """, (code, nome_meeting, user["id"]))
                meeting_id = chat_cur.lastrowid
                chat_conn.commit()
                # URL publica: prefere o host de origem do request (Origin/Referer)
                # pra o link cair no mesmo ambiente onde a sala foi criada
                # (evita reuniao criada em staging apontar pra prod, onde a
                # sala nao existe). Fallback pro PUBLIC_BASE_URL de config.
                base = _base_url_do_request(request) or (PUBLIC_BASE_URL or "").rstrip("/")
                meeting_url = f"{base}/SistemaCPE/web/pages/meet.html?code={code}"
                logger.info(f"[COMERCIAL/MEETING] code={code} url={meeting_url} vendedor={vendedor['name']}")
            except Exception as err:
                logger.warning(f"[COMERCIAL/MEETING] falhou gerar meeting: {err} — segue sem link")
                meeting_url = None
                meeting_id = None

        cursor.execute("""
            INSERT INTO comercial_reunioes
              (vendedor_id, cliente_id, data, hora, slot_id, meeting_url, meeting_id, agendado_por)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (body.vendedor_id, body.cliente_id, body.data, body.hora,
              body.slot_id, meeting_url, meeting_id, user["id"]))
        conn.commit()
        new_id = cursor.lastrowid
        logger.info(f"[COMERCIAL/REUNIAO] criada id={new_id} vendedor={body.vendedor_id} cliente={body.cliente_id}")
        return {
            "ok": True, "id": new_id,
            "meeting_url": meeting_url,
            "meeting_id":  meeting_id,
        }
    except HTTPException:
        conn.rollback()
        try:
            if chat_conn: chat_conn.rollback()
        except Exception: pass
        raise
    except Exception as err:
        conn.rollback()
        try:
            if chat_conn: chat_conn.rollback()
        except Exception: pass
        logger.error(f"[COMERCIAL/REUNIAO] erro: {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar reuniao: {err}")
    finally:
        cursor.close(); conn.close()
        try:
            if chat_cur: chat_cur.close()
            if chat_conn: chat_conn.close()
        except Exception: pass


@router.get("/reunioes/{reuniao_id}")
def detalhes_reuniao(reuniao_id: int, request: Request):
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _require_comercial(request, cursor)
        cursor.execute("""
            SELECT r.*, v.name AS vendedor_nome, c.nome AS cliente_nome,
                   c.empresa AS cliente_empresa, c.email AS cliente_email,
                   c.telefone AS cliente_telefone, c.produto_interesse,
                   ap.name AS agendado_por_nome
              FROM comercial_reunioes r
              JOIN users v            ON v.id  = r.vendedor_id
              JOIN comercial_clientes c ON c.id = r.cliente_id
         LEFT JOIN users ap           ON ap.id = r.agendado_por
             WHERE r.id = %s
        """, (reuniao_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Reuniao nao encontrada")
        row["hora"] = _time_to_str(row["hora"])
        if row.get("data"): row["data"] = str(row["data"])
        return {"reuniao": convert_datetime_to_string(row)}
    finally:
        cursor.close(); conn.close()


@router.post("/reunioes/{reuniao_id}/cancelar")
def cancelar_reuniao(reuniao_id: int, request: Request):
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _require_comercial(request, cursor)
        cursor.execute("UPDATE comercial_reunioes SET status='cancelada' WHERE id=%s", (reuniao_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Reuniao nao encontrada")
        conn.commit()
        return {"ok": True}
    except HTTPException:
        conn.rollback(); raise
    except Exception as err:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        cursor.close(); conn.close()


@router.post("/reunioes/{reuniao_id}/classificar")
def classificar_reuniao(reuniao_id: int, body: ClassificacaoIn, request: Request):
    """Pos-reuniao: vendedor classifica quente/morno/frio + comentario."""
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _require_comercial(request, cursor)
        cursor.execute("SELECT vendedor_id, status FROM comercial_reunioes WHERE id=%s", (reuniao_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Reuniao nao encontrada")

        cursor.execute("""
            UPDATE comercial_reunioes
               SET classificacao=%s, comentario=%s,
                   classificado_em=NOW(),
                   status = CASE WHEN status='agendada' THEN 'realizada' ELSE status END
             WHERE id=%s
        """, (body.classificacao, body.comentario, reuniao_id))
        conn.commit()
        return {"ok": True}
    except HTTPException:
        conn.rollback(); raise
    except Exception as err:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        cursor.close(); conn.close()


# ============================================================
# MATERIAL DE APOIO
# ============================================================

@router.get("/material-apoio")
def listar_material(request: Request, incluir_inativo: bool = False):
    """Lista arquivos de apoio. Por default so os ativos."""
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _require_comercial(request, cursor)
        where = "" if incluir_inativo else "WHERE ativo = 1"
        cursor.execute(f"""
            SELECT m.id, m.titulo, m.descricao, m.arquivo_path,
                   m.arquivo_nome_original, m.mime_type, m.tamanho_bytes,
                   m.categoria, m.ordem, m.ativo,
                   m.uploaded_by, u.name AS uploaded_por_nome,
                   m.created_at
              FROM comercial_material_apoio m
              LEFT JOIN users u ON u.id = m.uploaded_by
              {where}
              ORDER BY m.ordem, m.created_at DESC
        """)
        return {"materiais": convert_datetime_list(cursor.fetchall())}
    finally:
        cursor.close(); conn.close()


@router.post("/material-apoio", status_code=201)
async def upload_material(
    request: Request,
    file:      UploadFile = File(...),
    titulo:    str        = Form(...),
    descricao: Optional[str] = Form(None),
    categoria: Optional[str] = Form(None),
    ordem:     Optional[int] = Form(0),
):
    """Upload de arquivo + metadata. Salva em web/uploads/comercial/<uuid>.<ext>."""
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        user = _require_comercial(request, cursor)

        titulo = (titulo or "").strip()
        if not titulo:
            raise HTTPException(status_code=400, detail="Titulo e obrigatorio")

        original_name = (file.filename or "").strip()
        ext = os.path.splitext(original_name)[1].lower()
        if ext not in _MATERIAL_EXTS:
            raise HTTPException(
                status_code=400,
                detail=f"Formato nao suportado: {ext}. Aceitos: {', '.join(sorted(_MATERIAL_EXTS))}"
            )

        # Nome fisico unico
        safe_name = f"cm_{uuid.uuid4().hex[:12]}{ext}"
        filepath  = os.path.join(_UPLOAD_DIR_COMERCIAL, safe_name)

        # Escreve em stream, tracking do tamanho pra bloquear se ultrapassar limite
        total = 0
        with open(filepath, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB por vez
                if not chunk:
                    break
                total += len(chunk)
                if total > _MATERIAL_MAX_BYTES:
                    f.close()
                    try: os.remove(filepath)
                    except Exception: pass
                    raise HTTPException(
                        status_code=413,
                        detail=f"Arquivo excede o limite de {_MATERIAL_MAX_BYTES // (1024*1024)} MB"
                    )
                f.write(chunk)

        rel_url = f"/SistemaCPE/web/uploads/comercial/{safe_name}"

        cursor.execute("""
            INSERT INTO comercial_material_apoio
              (titulo, descricao, arquivo_path, arquivo_nome_original,
               mime_type, tamanho_bytes, categoria, ordem, uploaded_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            titulo, (descricao or "").strip() or None, rel_url,
            original_name or None, file.content_type or None,
            total, (categoria or "").strip() or None, ordem or 0, user["id"],
        ))
        conn.commit()
        new_id = cursor.lastrowid
        logger.info(f"[COMERCIAL/MATERIAL] upload id={new_id} titulo='{titulo}' size={total}")
        return {"ok": True, "id": new_id, "arquivo_path": rel_url, "tamanho_bytes": total}
    except HTTPException:
        conn.rollback(); raise
    except Exception as err:
        conn.rollback()
        logger.error(f"[COMERCIAL/MATERIAL] erro upload: {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao subir arquivo: {err}")
    finally:
        cursor.close(); conn.close()


class MaterialUpdateIn(BaseModel):
    titulo:    Optional[str] = None
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    ordem:     Optional[int] = None
    ativo:     Optional[bool] = None


@router.put("/material-apoio/{material_id}")
def atualizar_material(material_id: int, body: MaterialUpdateIn, request: Request):
    """Edita metadata (nao substitui o arquivo — pra trocar arquivo, delete + upload novo)."""
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _require_comercial(request, cursor)
        cursor.execute("SELECT id FROM comercial_material_apoio WHERE id=%s", (material_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Material nao encontrado")

        sets, params = [], []
        for f in ("titulo", "descricao", "categoria", "ordem"):
            v = getattr(body, f)
            if v is not None:
                sets.append(f"{f}=%s"); params.append(v)
        if body.ativo is not None:
            sets.append("ativo=%s"); params.append(1 if body.ativo else 0)
        if not sets:
            return {"ok": True, "changed": 0}

        params.append(material_id)
        cursor.execute(f"UPDATE comercial_material_apoio SET {', '.join(sets)} WHERE id=%s", params)
        conn.commit()
        return {"ok": True, "changed": cursor.rowcount}
    except HTTPException:
        conn.rollback(); raise
    except Exception as err:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        cursor.close(); conn.close()


@router.delete("/material-apoio/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_material(material_id: int, request: Request):
    """Hard delete: apaga do banco E do disco."""
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _require_comercial(request, cursor)
        cursor.execute(
            "SELECT arquivo_path FROM comercial_material_apoio WHERE id=%s",
            (material_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Material nao encontrado")

        cursor.execute("DELETE FROM comercial_material_apoio WHERE id=%s", (material_id,))
        conn.commit()

        # Apaga arquivo do disco (silencioso se falhar — DB e a fonte da verdade)
        try:
            path = row["arquivo_path"] or ""
            if path.startswith("/SistemaCPE/web/uploads/comercial/"):
                fname = os.path.basename(path)
                fs_path = os.path.join(_UPLOAD_DIR_COMERCIAL, fname)
                if os.path.exists(fs_path):
                    os.remove(fs_path)
        except Exception as err:
            logger.warning(f"[COMERCIAL/MATERIAL] apagar arquivo falhou: {err}")
    except HTTPException:
        conn.rollback(); raise
    except Exception as err:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        cursor.close(); conn.close()


# ============================================================
# HELPERS INTERNOS
# ============================================================

def _time_to_str(v) -> Optional[str]:
    """Normaliza time/timedelta/str do MySQL pra 'HH:MM'."""
    if v is None: return None
    from datetime import timedelta, time as _time
    if isinstance(v, timedelta):
        t = int(v.total_seconds())
        return f"{t//3600:02d}:{(t%3600)//60:02d}"
    if isinstance(v, _time):
        return v.strftime("%H:%M")
    s = str(v).strip()
    if not s: return None
    parts = s.split(":")
    if len(parts) < 2: return s
    return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
