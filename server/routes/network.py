"""
Monitoramento de Rede — endpoints para gerenciar unidades Mikrotik
e consultar status em tempo real.

CRUD de unidades é restrito a ADMIN/TI (informação sensível de rede).
Endpoint de status pode ser visto por ADMIN/TI também.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from database import get_db_or_404

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/network", tags=["network"])


# ─── Permissão ───────────────────────────────────────────────
def _require_admin_ti(request: Request) -> dict:
    """ADMIN/TI apenas — info sensível de infra."""
    from security import parse_session_token, COOKIE_NAME, get_user_by_id
    token = (request.cookies.get(COOKIE_NAME)
             or request.headers.get("X-Auth-Token")
             or request.headers.get("x-auth-token"))
    uid = parse_session_token(token) if token else None
    user = get_user_by_id(uid) if uid else None
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")
    if user.get("role") not in ("ADMIN", "TI"):
        raise HTTPException(
            status_code=403,
            detail="Apenas Administrador ou T.I. podem acessar monitoramento de rede."
        )
    return user


# ─── CRUD: Unidades ──────────────────────────────────────────
@router.get("/units")
def list_units(request: Request, ativo: Optional[int] = Query(None)):
    """Lista as unidades cadastradas. `ativo=1` filtra só ativas."""
    _require_admin_ti(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = "SELECT * FROM network_units"
        params: list = []
        if ativo is not None:
            sql += " WHERE ativo = %s"
            params.append(ativo)
        sql += " ORDER BY nome"
        cursor.execute(sql, params)
        return {"success": True, "units": cursor.fetchall()}
    finally:
        cursor.close(); conn.close()


@router.post("/units")
def create_unit(request: Request, data: dict):
    """Cadastra uma nova unidade (Mikrotik)."""
    _require_admin_ti(request)
    nome     = (data.get("nome") or "").strip()
    identity = (data.get("identity") or "").strip()
    host     = (data.get("host") or "").strip()
    if not nome or not identity or not host:
        raise HTTPException(400, "Campos obrigatórios: nome, identity, host.")

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO network_units
                (nome, identity, host, porta,
                 wan1_interface, wan1_label, wan2_interface, wan2_label,
                 modelo, observacoes, ativo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            nome, identity, host,
            int(data.get("porta") or 8728),
            data.get("wan1_interface") or "ether1",
            data.get("wan1_label")     or "WAN 1",
            data.get("wan2_interface") or "ether2",
            data.get("wan2_label")     or "WAN 2",
            data.get("modelo") or None,
            data.get("observacoes") or None,
            1 if data.get("ativo", True) else 0,
        ))
        new_id = cursor.lastrowid
        conn.commit()
        cursor.execute("SELECT * FROM network_units WHERE id=%s", (new_id,))
        return {"success": True, "unit": cursor.fetchone()}
    except Exception as e:
        conn.rollback()
        if "Duplicate" in str(e):
            raise HTTPException(400, f"Já existe uma unidade com identity '{identity}'")
        raise HTTPException(500, str(e))
    finally:
        cursor.close(); conn.close()


@router.put("/units/{unit_id}")
def update_unit(unit_id: int, request: Request, data: dict):
    _require_admin_ti(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM network_units WHERE id=%s", (unit_id,))
        if not cursor.fetchone():
            raise HTTPException(404, "Unidade não encontrada")

        fields = []
        params: list = []
        for col in ("nome", "identity", "host", "porta",
                    "wan1_interface", "wan1_label",
                    "wan2_interface", "wan2_label",
                    "modelo", "observacoes"):
            if col in data:
                fields.append(f"{col} = %s")
                params.append(data[col])
        if "ativo" in data:
            fields.append("ativo = %s")
            params.append(1 if data["ativo"] else 0)
        if not fields:
            raise HTTPException(400, "Nada para atualizar.")
        params.append(unit_id)
        cursor.execute(f"UPDATE network_units SET {', '.join(fields)} WHERE id=%s", params)
        conn.commit()
        cursor.execute("SELECT * FROM network_units WHERE id=%s", (unit_id,))
        return {"success": True, "unit": cursor.fetchone()}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        if "Duplicate" in str(e):
            raise HTTPException(400, "Já existe outra unidade com essa identity.")
        raise HTTPException(500, str(e))
    finally:
        cursor.close(); conn.close()


@router.delete("/units/{unit_id}")
def delete_unit(unit_id: int, request: Request):
    _require_admin_ti(request)
    conn = get_db_or_404()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM network_units WHERE id=%s", (unit_id,))
        if cursor.rowcount == 0:
            raise HTTPException(404, "Unidade não encontrada")
        conn.commit()
        return {"success": True}
    finally:
        cursor.close(); conn.close()


# ─── Status em tempo real (coleta ao vivo) ───────────────────
@router.get("/status")
def live_status(request: Request, unit_id: Optional[int] = Query(None)):
    """Coleta status ao vivo de todas as unidades ativas (ou de uma só).
    Resposta é cacheada por 30s no front pra não esmagar os Mikrotiks."""
    _require_admin_ti(request)

    try:
        from services.mikrotik_service import coletar_unidades
    except ImportError as exc:
        raise HTTPException(500, f"mikrotik_service indisponível: {exc}")

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = "SELECT * FROM network_units WHERE ativo=1"
        params: list = []
        if unit_id:
            sql += " AND id=%s"
            params.append(unit_id)
        sql += " ORDER BY nome"
        cursor.execute(sql, params)
        unidades = cursor.fetchall()
    finally:
        cursor.close(); conn.close()

    snapshots = coletar_unidades(unidades)

    # Resumo geral
    total = len(snapshots)
    com_falha = sum(1 for s in snapshots if not s.get("ok"))
    wan_offline = 0
    wan_degraded = 0
    for s in snapshots:
        for w in s.get("wans", []):
            if w["status"] == "offline":
                wan_offline += 1
            elif w["status"] == "degraded":
                wan_degraded += 1

    return {
        "success":   True,
        "snapshots": snapshots,
        "summary":   {
            "total":         total,
            "com_falha":     com_falha,
            "wan_offline":   wan_offline,
            "wan_degraded":  wan_degraded,
        },
    }


# ─── Histórico recente ───────────────────────────────────────
@router.get("/history")
def historico(request: Request,
              unit_id: Optional[int] = Query(None),
              horas:   int           = Query(24, ge=1, le=720)):
    """Histórico de status_log das últimas N horas (default 24h)."""
    _require_admin_ti(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT l.*, u.nome AS unit_nome
              FROM network_status_log l
              JOIN network_units u ON u.id = l.unit_id
             WHERE l.coletado_em >= NOW() - INTERVAL %s HOUR
        """
        params = [horas]
        if unit_id:
            sql += " AND l.unit_id = %s"
            params.append(unit_id)
        sql += " ORDER BY l.coletado_em DESC LIMIT 5000"
        cursor.execute(sql, params)
        return {"success": True, "log": cursor.fetchall()}
    finally:
        cursor.close(); conn.close()


@router.get("/events")
def eventos(request: Request,
            ativos:  bool = Query(False),
            horas:   int  = Query(72, ge=1, le=720)):
    """Eventos de queda/degradação. `ativos=true` mostra só os em andamento."""
    _require_admin_ti(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT e.*, u.nome AS unit_nome
              FROM network_events e
              JOIN network_units u ON u.id = e.unit_id
             WHERE 1=1
        """
        params: list = []
        if ativos:
            sql += " AND e.encerrado_em IS NULL"
        else:
            sql += " AND e.iniciado_em >= NOW() - INTERVAL %s HOUR"
            params.append(horas)
        sql += " ORDER BY e.iniciado_em DESC LIMIT 500"
        cursor.execute(sql, params)
        return {"success": True, "events": cursor.fetchall()}
    finally:
        cursor.close(); conn.close()
