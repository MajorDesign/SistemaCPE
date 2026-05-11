"""
Inventário T.I. — Dispositivos com agente de coleta automática.

Endpoints:
    GET  /api/inventario/dispositivos              → lista com filtros
    GET  /api/inventario/dispositivos/{id}         → detalhe completo
    GET  /api/inventario/stats                     → KPIs para o painel
    POST /api/inventario/agent/report              → agente envia relatório (upsert)
    GET  /api/inventario/agent/version             → versão atual do agente (para auto-update)
    GET  /api/inventario/agent/download            → baixa CPEAgente.py atualizado
    PATCH /api/inventario/dispositivos/{id}/apelido → editar apelido/patrimônio
    DELETE /api/inventario/dispositivos/{id}       → remover registro
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse

from database import get_db_connection

router = APIRouter(prefix="/api/inventario", tags=["inventario"])
logger = logging.getLogger(__name__)

AGENT_KEY            = os.getenv("INVENTORY_AGENT_KEY", "")
OFFLINE_THRESHOLD_M  = 20   # minutos sem heartbeat → offline


# ─── Permissões ──────────────────────────────────────────────────────────────
def _require_admin_ti(request: Request) -> dict:
    """Valida que o usuário autenticado é ADMIN ou TI.
    Usado em endpoints com info sensível de rede (Omada)."""
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
            detail="Apenas Administrador ou T.I. podem ver dispositivos Omada."
        )
    return user


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _is_offline(ts) -> bool:
    if not ts:
        return True
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts)
        except ValueError:
            return True
    return (datetime.now() - ts).total_seconds() > OFFLINE_THRESHOLD_M * 60


def _fmt_row(row: dict) -> dict:
    row["status"] = "offline" if _is_offline(row.get("ultimo_heartbeat")) else "online"
    for k in ("ultimo_heartbeat", "criado_em", "atualizado_em"):
        if row.get(k) and hasattr(row[k], "isoformat"):
            row[k] = row[k].isoformat()
    return row


def _count_alerts(row: dict) -> int:
    """Conta alertas: disco < 15 % livre, RAM > 90 %, offline."""
    alerts = 0
    if _is_offline(row.get("ultimo_heartbeat")):
        alerts += 1
    if row.get("disco_livre_pct") is not None and float(row["disco_livre_pct"]) < 15:
        alerts += 1
    if row.get("memoria_uso_pct") is not None and float(row["memoria_uso_pct"]) > 90:
        alerts += 1
    return alerts


# ─── Listar dispositivos ───────────────────────────────────────────────────────

@router.get("/dispositivos")
def listar_dispositivos(
    search: Optional[str] = Query(None),
    tipo:   Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT id, hostname, apelido, usuario_logado, ip_interno, ip_externo,
                   tipo, marca, modelo, numero_serie, sistema_operacional, versao_os,
                   arquitetura, memoria_total_gb, memoria_uso_pct,
                   disco_total_gb, disco_livre_gb, disco_livre_pct,
                   cpu_modelo, cpu_nucleos, cpu_uso_pct,
                   dias_ligado, estado_br, cidade,
                   versao_agente, ultimo_heartbeat, criado_em
            FROM inventario_dispositivos
            WHERE 1=1
        """
        params: list = []

        if search:
            sql += """ AND (hostname LIKE %s OR usuario_logado LIKE %s
                           OR marca LIKE %s OR modelo LIKE %s OR apelido LIKE %s
                           OR cidade LIKE %s OR estado_br LIKE %s)"""
            s = f"%{search}%"
            params.extend([s, s, s, s, s, s, s])

        if tipo:
            sql += " AND tipo = %s"
            params.append(tipo)

        if estado:
            sql += " AND estado_br = %s"
            params.append(estado)

        sql += " ORDER BY ultimo_heartbeat DESC, hostname"
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        result = []
        for r in rows:
            r["alerts"] = _count_alerts(r)
            _fmt_row(r)
            if status and r["status"] != status:
                continue
            result.append(r)

        return {"dispositivos": result, "total": len(result)}
    finally:
        cursor.close()
        conn.close()


# ─── Detalhe ──────────────────────────────────────────────────────────────────

@router.get("/dispositivos/{device_id}")
def detalhe_dispositivo(device_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM inventario_dispositivos WHERE id = %s", (device_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(404, "Dispositivo não encontrado")
        row["alerts"] = _count_alerts(row)
        _fmt_row(row)
        if row.get("discos_json") and isinstance(row["discos_json"], str):
            try:
                row["discos_json"] = json.loads(row["discos_json"])
            except Exception:
                pass
        return row
    finally:
        cursor.close()
        conn.close()


# ─── Estatísticas ─────────────────────────────────────────────────────────────

@router.get("/stats")
def estatisticas():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT
                COUNT(*)                                                      AS total,
                SUM(tipo = 'notebook')                                        AS notebooks,
                SUM(tipo = 'desktop')                                         AS desktops,
                SUM(tipo = 'servidor')                                        AS servidores,
                SUM(tipo = 'terminal')                                        AS terminais,
                SUM(tipo = 'outro')                                           AS outros,
                ROUND(AVG(memoria_uso_pct), 1)                               AS media_ram_pct,
                ROUND(AVG(disco_livre_pct), 1)                               AS media_disco_livre_pct,
                SUM(disco_livre_pct IS NOT NULL AND disco_livre_pct < 15)    AS disco_critico,
                SUM(memoria_uso_pct IS NOT NULL AND memoria_uso_pct > 90)    AS ram_critica
            FROM inventario_dispositivos
        """)
        stats = cursor.fetchone() or {}

        cursor.execute("SELECT ultimo_heartbeat FROM inventario_dispositivos")
        devs = cursor.fetchall()
        online  = sum(1 for d in devs if not _is_offline(d.get("ultimo_heartbeat")))
        total   = int(stats.get("total") or 0)
        offline = total - online

        return {**stats, "online": online, "offline": offline}
    finally:
        cursor.close()
        conn.close()


# ─── Auto-update do agente ────────────────────────────────────────────────────

# A distribuição oficial é o .exe (PyInstaller --onefile --windowed) — usuários
# não precisam ter Python instalado. O .py fica como fallback para máquinas dev.
import glob

_INV_DIR        = (pathlib.Path(__file__).resolve()
                   .parent.parent.parent / "tools" / "inventory_agent")
_RELEASE_DIR    = _INV_DIR / "release"
_RELEASE_GLOB   = "CPEAgente_v*.exe"
_AGENT_PY       = _INV_DIR / "CPEAgente.py"        # fallback / leitura de versão
_VERSION_FROM_FILENAME_RE = re.compile(r"_v([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE)


def _latest_exe() -> Optional[pathlib.Path]:
    """Pega o .exe mais recente em release/. Retorna None se não houver build."""
    candidates = glob.glob(str(_RELEASE_DIR / _RELEASE_GLOB))
    if not candidates:
        return None
    return pathlib.Path(max(candidates, key=os.path.getmtime))


def _versao_do_exe(path: pathlib.Path) -> Optional[str]:
    m = _VERSION_FROM_FILENAME_RE.search(path.name)
    return m.group(1).rstrip(".") if m else None


def _versao_do_py() -> Optional[str]:
    """Lê VERSAO do CPEAgente.py — usado como fallback quando não há .exe."""
    try:
        texto = _AGENT_PY.read_text(encoding="utf-8")
        m = re.search(r'^VERSAO\s*=\s*["\']([^"\']+)["\']', texto, re.MULTILINE)
        return m.group(1) if m else None
    except Exception:
        return None


def _agent_versao() -> str:
    """Versão considerada 'oficial' pelo servidor — prioriza o filename do .exe."""
    exe = _latest_exe()
    if exe:
        v = _versao_do_exe(exe)
        if v: return v
    return _versao_do_py() or "0.0.0"


@router.get("/agent/version")
def agent_version():
    """Retorna a versão atual do agente disponível no servidor (do .exe em release/)."""
    return {
        "version":      _agent_versao(),
        "download_url": "/api/inventario/agent/download",
    }


@router.get("/agent/download")
def agent_download():
    """
    Serve o CPEAgente.exe mais recente para que os clientes possam se auto-atualizar.
    Qualquer máquina com o agente instalado consulta /agent/version; se houver
    versão maior, baixa o .exe daqui e troca o binário via helper batch.
    """
    exe = _latest_exe()
    if exe and exe.exists():
        return FileResponse(
            path=str(exe),
            media_type="application/octet-stream",
            filename=exe.name,
        )
    # Fallback: ambiente dev que ainda não buildou o .exe
    if _AGENT_PY.exists():
        return FileResponse(
            path=str(_AGENT_PY),
            media_type="text/plain; charset=utf-8",
            filename="CPEAgente.py",
        )
    raise HTTPException(404, "Agente não encontrado no servidor. Rode tools/inventory_agent/scripts/build.bat.")


# ─── Recebimento do relatório do agente ───────────────────────────────────────

@router.post("/agent/report")
def receber_relatorio(
    payload: dict,
    x_agent_key: Optional[str] = Header(None),
):
    if AGENT_KEY and x_agent_key != AGENT_KEY:
        raise HTTPException(401, "Chave de agente inválida")

    hostname = (payload.get("hostname") or "").strip()
    if not hostname:
        raise HTTPException(400, "hostname é obrigatório")

    discos_raw = payload.get("discos_json")
    discos_str = json.dumps(discos_raw, ensure_ascii=False) if discos_raw else None

    fields = {
        "hostname":            hostname,
        "usuario_logado":      payload.get("usuario_logado"),
        "ip_interno":          payload.get("ip_interno"),
        "ip_externo":          payload.get("ip_externo"),
        "tipo":                payload.get("tipo") or "notebook",
        "marca":               payload.get("marca"),
        "modelo":              payload.get("modelo"),
        "numero_serie":        payload.get("numero_serie"),
        "sistema_operacional": payload.get("sistema_operacional"),
        "versao_os":           payload.get("versao_os"),
        "arquitetura":         payload.get("arquitetura"),
        "memoria_total_gb":    payload.get("memoria_total_gb"),
        "memoria_uso_pct":     payload.get("memoria_uso_pct"),
        "disco_total_gb":      payload.get("disco_total_gb"),
        "disco_livre_gb":      payload.get("disco_livre_gb"),
        "disco_livre_pct":     payload.get("disco_livre_pct"),
        "discos_json":         discos_str,
        "cpu_modelo":          payload.get("cpu_modelo"),
        "cpu_nucleos":         payload.get("cpu_nucleos"),
        "cpu_uso_pct":         payload.get("cpu_uso_pct"),
        "dias_ligado":         payload.get("dias_ligado"),
        "estado_br":           payload.get("estado_br"),
        "cidade":              payload.get("cidade"),
        "versao_agente":       payload.get("versao_agente", "1.0.0"),
        "ultimo_heartbeat":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id FROM inventario_dispositivos WHERE hostname = %s", (hostname,)
        )
        existing = cursor.fetchone()

        if existing:
            non_host = {k: v for k, v in fields.items() if k != "hostname"}
            set_sql  = ", ".join(f"`{k}` = %s" for k in non_host)
            vals     = list(non_host.values()) + [hostname]
            cursor.execute(
                f"UPDATE inventario_dispositivos SET {set_sql} WHERE hostname = %s",
                vals,
            )
            action = "updated"
        else:
            cols = ", ".join(f"`{k}`" for k in fields)
            phs  = ", ".join(["%s"] * len(fields))
            cursor.execute(
                f"INSERT INTO inventario_dispositivos ({cols}) VALUES ({phs})",
                list(fields.values()),
            )
            action = "created"

        conn.commit()
        logger.info(f"[INV AGENT] {action}: hostname={hostname}")
        return {"ok": True, "action": action, "hostname": hostname}

    except Exception as exc:
        conn.rollback()
        logger.error(f"[INV AGENT] Erro ao salvar {hostname}: {exc}")
        raise HTTPException(500, str(exc))
    finally:
        cursor.close()
        conn.close()


# ─── Editar apelido/patrimônio ────────────────────────────────────────────────

@router.patch("/dispositivos/{device_id}/apelido")
def atualizar_apelido(device_id: int, payload: dict):
    apelido = (payload.get("apelido") or "").strip() or None
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE inventario_dispositivos SET apelido = %s WHERE id = %s",
            (apelido, device_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, "Dispositivo não encontrado")
        conn.commit()
        return {"ok": True}
    finally:
        cursor.close()
        conn.close()


# ─── Remover dispositivo ──────────────────────────────────────────────────────

@router.delete("/dispositivos/{device_id}")
def remover_dispositivo(device_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM inventario_dispositivos WHERE id = %s", (device_id,)
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, "Dispositivo não encontrado")
        conn.commit()
        return {"ok": True}
    finally:
        cursor.close()
        conn.close()


# ─── Omada Controller (TP-Link) — read-only ──────────────────────────────────
# Lista APs/switches/gateways do Omada Controller para integrar ao
# inventário. Só ADMIN/TI veem (info sensível de rede).

@router.get("/omada/devices")
def omada_devices(request: Request):
    """Lista dispositivos do Omada Controller (todos os sites visíveis)."""
    _require_admin_ti(request)
    try:
        from services.omada_service import (
            listar_devices_todos_sites, OmadaError, _configurado,
        )
    except ImportError as exc:
        raise HTTPException(500, f"omada_service indisponível: {exc}")

    if not _configurado():
        raise HTTPException(
            503,
            "Integração Omada não configurada. Defina OMADA_BASE_URL/USER/PASS no .env."
        )

    try:
        devices = listar_devices_todos_sites()
    except OmadaError as exc:
        logger.error("[OMADA] %s", exc)
        raise HTTPException(502, f"Omada: {exc}")
    except Exception as exc:
        logger.exception("[OMADA] Falha geral")
        raise HTTPException(502, f"Omada offline ou inalcançável: {exc}")

    online  = sum(1 for d in devices if d.get("status") == "online")
    offline = len(devices) - online

    return {
        "success": True,
        "devices": devices,
        "stats":   {
            "total":   len(devices),
            "online":  online,
            "offline": offline,
        },
    }


@router.get("/omada/sites")
def omada_sites(request: Request):
    """Lista os sites visíveis no controller (pra filtro no frontend)."""
    _require_admin_ti(request)
    try:
        from services.omada_service import listar_sites, OmadaError
    except ImportError as exc:
        raise HTTPException(500, f"omada_service indisponível: {exc}")
    try:
        return {"success": True, "sites": listar_sites()}
    except OmadaError as exc:
        raise HTTPException(502, f"Omada: {exc}")
    except Exception as exc:
        raise HTTPException(502, f"Omada inalcançável: {exc}")


@router.get("/omada/clients")
def omada_clients(request: Request, site_id: Optional[str] = Query(None)):
    """Lista clientes Omada ativos. `site_id` opcional filtra por um site;
    sem ele, agrega todos os sites visíveis."""
    _require_admin_ti(request)
    try:
        from services.omada_service import (
            listar_clientes, listar_clientes_todos_sites, OmadaError,
        )
    except ImportError as exc:
        raise HTTPException(500, f"omada_service indisponível: {exc}")
    try:
        clients = listar_clientes(site_id) if site_id else listar_clientes_todos_sites()
    except OmadaError as exc:
        raise HTTPException(502, f"Omada: {exc}")
    except Exception as exc:
        raise HTTPException(502, f"Omada inalcançável: {exc}")

    # Contagens por categoria pra montar os filtros no front
    cnt = {"telemovel": 0, "escritorio": 0, "rede": 0, "outros": 0}
    for c in clients:
        cat = c.get("categoria") or "outros"
        cnt[cat] = cnt.get(cat, 0) + 1
    return {"success": True, "clients": clients, "stats": {"total": len(clients), **cnt}}


@router.get("/omada/topology")
def omada_topology(request: Request, site_id: Optional[str] = Query(None)):
    """Snapshot da topologia: switches, APs, gateways e contagem de
    clientes por AP. `site_id` obrigatório se houver mais de um site
    (defina explicitamente no frontend)."""
    _require_admin_ti(request)
    try:
        from services.omada_service import topologia, OmadaError, listar_sites
    except ImportError as exc:
        raise HTTPException(500, f"omada_service indisponível: {exc}")
    try:
        if site_id:
            return {"success": True, "topology": topologia(site_id)}
        # Sem site_id: monta uma topologia por site (frontend escolhe qual mostrar)
        out = []
        for s in listar_sites():
            try:
                out.append(topologia(s["id"]))
            except Exception:
                pass
        return {"success": True, "topologies": out}
    except OmadaError as exc:
        raise HTTPException(502, f"Omada: {exc}")
    except Exception as exc:
        raise HTTPException(502, f"Omada inalcançável: {exc}")
