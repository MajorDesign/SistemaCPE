"""
Inventário T.I. — Dispositivos com agente de coleta automática.

Endpoints:
    GET  /api/inventario/dispositivos              → lista com filtros
    GET  /api/inventario/dispositivos/{id}         → detalhe completo
    GET  /api/inventario/stats                     → KPIs para o painel
    POST /api/inventario/agent/report              → agente envia relatório (upsert)
    GET  /api/inventario/agent/version             → versão atual do agente (para auto-update)
    GET  /api/inventario/agent/download            → baixa CPEAgente.py atualizado
    PATCH /api/inventario/dispositivos/{id}/apelido    → editar apelido/patrimônio
    PATCH /api/inventario/dispositivos/{id}/estoque    → mover para/de estoque
    PATCH /api/inventario/dispositivos/{id}/info       → atualizar responsável/setor/localização
    DELETE /api/inventario/dispositivos/{id}           → remover registro
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import pathlib
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, Request, UploadFile
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
    search:     Optional[str]  = Query(None),
    tipo:       Optional[str]  = Query(None),
    status:     Optional[str]  = Query(None),
    estado:     Optional[str]  = Query(None),
    em_estoque: Optional[bool] = Query(None,
        description="None=todos, False=ativos, True=apenas estoque"),
):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT id, hostname, apelido, em_estoque, em_manutencao, manutencao_atual_id,
                   nome_responsavel, setor, localizacao_cpe,
                   usuario_logado, ip_interno, ip_externo,
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
                           OR cidade LIKE %s OR estado_br LIKE %s
                           OR nome_responsavel LIKE %s OR setor LIKE %s
                           OR localizacao_cpe LIKE %s)"""
            s = f"%{search}%"
            params.extend([s] * 10)

        if tipo:
            sql += " AND tipo = %s"
            params.append(tipo)

        if estado:
            sql += " AND estado_br = %s"
            params.append(estado)

        if em_estoque is not None:
            sql += " AND em_estoque = %s"
            params.append(1 if em_estoque else 0)

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
        # Stats consideram apenas equipamentos ATIVOS (em_estoque=0 E em_manutencao=0).
        # Estoque e manutenção são contados separadamente — equipamentos
        # parados/em reparo não devem poluir KPIs operacionais (online/offline).
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
            WHERE em_estoque = 0 AND em_manutencao = 0
        """)
        stats = cursor.fetchone() or {}

        cursor.execute(
            "SELECT COUNT(*) AS n FROM inventario_dispositivos WHERE em_estoque = 1"
        )
        estoque = int((cursor.fetchone() or {}).get("n") or 0)

        # Manutenção: conta tanto pelo flag no dispositivo quanto pelas
        # manutenções em aberto (status != concluida/cancelada).
        cursor.execute("""
            SELECT COUNT(*) AS n
              FROM inventario_manutencoes
             WHERE status NOT IN ('concluida','cancelada')
        """)
        manutencao = int((cursor.fetchone() or {}).get("n") or 0)

        cursor.execute(
            "SELECT ultimo_heartbeat FROM inventario_dispositivos "
            "WHERE em_estoque = 0 AND em_manutencao = 0"
        )
        devs = cursor.fetchall()
        online  = sum(1 for d in devs if not _is_offline(d.get("ultimo_heartbeat")))
        total   = int(stats.get("total") or 0)
        offline = total - online

        return {**stats, "online": online, "offline": offline,
                "estoque": estoque, "manutencao": manutencao}
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

    # MAC é a chave estável (sobrevive a rename do host e troca de IP/rede).
    # Agentes antigos (< 1.6.0) não enviam — cai no fallback por hostname.
    mac = (payload.get("mac") or "").strip().upper() or None

    discos_raw = payload.get("discos_json")
    discos_str = json.dumps(discos_raw, ensure_ascii=False) if discos_raw else None

    fields = {
        "hostname":            hostname,
        "mac":                 mac,
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
    cursor = conn.cursor(dictionary=True)
    try:
        # ── Lookup em 3 níveis: MAC, hostname, numero_serie ──────────────
        # O 3º nível é crucial pra migração de agentes < 1.6.0 (sem MAC) para
        # 1.6.0+ (com MAC) quando o hostname mudou no caminho. Sem ele, o
        # agente novo cria registro duplicado da mesma máquina física.
        existing = None
        match_by = None
        if mac:
            cursor.execute(
                "SELECT id, hostname FROM inventario_dispositivos WHERE mac = %s",
                (mac,),
            )
            existing = cursor.fetchone()
            if existing:
                match_by = "mac"

        if not existing:
            cursor.execute(
                "SELECT id, hostname FROM inventario_dispositivos WHERE hostname = %s",
                (hostname,),
            )
            existing = cursor.fetchone()
            if existing:
                match_by = "hostname"

        # Último recurso: numero_serie único + registro existente sem MAC
        # (= cadastrado por agente antigo, agora reportando via v1.6.0+
        # com hostname diferente). Só dispara quando temos série confiável.
        numero_serie_in = (payload.get("numero_serie") or "").strip()
        if not existing and mac and numero_serie_in and len(numero_serie_in) >= 6:
            cursor.execute(
                "SELECT id, hostname FROM inventario_dispositivos "
                "WHERE numero_serie = %s AND (mac IS NULL OR mac = '') "
                "ORDER BY id LIMIT 1",
                (numero_serie_in,),
            )
            existing = cursor.fetchone()
            if existing:
                match_by = "numero_serie"
                logger.info(
                    f"[INV AGENT] migrando registro #{existing['id']} (sem MAC) — "
                    f"hostname '{existing['hostname']}' → '{hostname}' "
                    f"(mac={mac}, serie={numero_serie_in})"
                )

        if existing:
            non_host = {k: v for k, v in fields.items()}
            set_sql  = ", ".join(f"`{k}` = %s" for k in non_host)
            vals     = list(non_host.values()) + [existing["id"]]
            cursor.execute(
                f"UPDATE inventario_dispositivos SET {set_sql} WHERE id = %s",
                vals,
            )
            renamed = (match_by in ("mac", "numero_serie")
                       and existing["hostname"] != hostname)
            action = "renamed" if renamed else "updated"
            if renamed and match_by == "mac":
                logger.info(
                    f"[INV AGENT] hostname mudou via MAC: "
                    f"'{existing['hostname']}' → '{hostname}' (mac={mac})"
                )
        else:
            cols = ", ".join(f"`{k}`" for k in fields)
            phs  = ", ".join(["%s"] * len(fields))
            cursor.execute(
                f"INSERT INTO inventario_dispositivos ({cols}) VALUES ({phs})",
                list(fields.values()),
            )
            action = "created"

        conn.commit()
        logger.info(f"[INV AGENT] {action}: hostname={hostname} mac={mac or '-'} (matched by {match_by or 'new'})")
        return {"ok": True, "action": action, "hostname": hostname, "matched_by": match_by}

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


# ─── Mover para/de estoque ────────────────────────────────────────────────────

@router.patch("/dispositivos/{device_id}/estoque")
def atualizar_estoque(device_id: int, payload: dict):
    """Move o equipamento para o estoque (em_estoque=1) ou tira (=0).

    Quando vai para estoque, limpa nome_responsavel e setor — o equipamento
    está parado aguardando reutilização. Mantém localizacao_cpe (onde está
    fisicamente guardado).
    """
    em_estoque = bool(payload.get("em_estoque", True))
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if em_estoque:
            cursor.execute(
                "UPDATE inventario_dispositivos "
                "SET em_estoque = 1, nome_responsavel = NULL, setor = NULL "
                "WHERE id = %s",
                (device_id,),
            )
        else:
            cursor.execute(
                "UPDATE inventario_dispositivos SET em_estoque = 0 WHERE id = %s",
                (device_id,),
            )
        if cursor.rowcount == 0:
            raise HTTPException(404, "Dispositivo não encontrado")
        conn.commit()
        return {"ok": True, "em_estoque": em_estoque}
    finally:
        cursor.close()
        conn.close()


# ─── Atualizar responsável / setor / localização ──────────────────────────────

@router.patch("/dispositivos/{device_id}/info")
def atualizar_info(device_id: int, payload: dict):
    """Atualiza nome_responsavel, setor e localizacao_cpe.

    Aceita os 3 campos opcionais. Strings vazias viram NULL.
    """
    def _norm(v):
        v = (v or "").strip()
        return v or None

    nome  = _norm(payload.get("nome_responsavel"))
    setor = _norm(payload.get("setor"))
    local = _norm(payload.get("localizacao_cpe"))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE inventario_dispositivos "
            "SET nome_responsavel = %s, setor = %s, localizacao_cpe = %s "
            "WHERE id = %s",
            (nome, setor, local, device_id),
        )
        if cursor.rowcount == 0:
            # rowcount=0 também acontece quando nada mudou; checa se existe
            cursor.execute(
                "SELECT 1 FROM inventario_dispositivos WHERE id = %s",
                (device_id,),
            )
            if not cursor.fetchone():
                raise HTTPException(404, "Dispositivo não encontrado")
        conn.commit()
        return {
            "ok": True,
            "nome_responsavel": nome,
            "setor": setor,
            "localizacao_cpe": local,
        }
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


# =====================================================================
# CELULARES CORPORATIVOS — CRUD + termo de responsabilidade
# =====================================================================

from pydantic import BaseModel, Field
from typing import List


class CelularBase(BaseModel):
    marca: str = Field(..., min_length=1, max_length=50)
    modelo: str = Field(..., min_length=1, max_length=100)
    imei1: str = Field(..., min_length=8, max_length=20)
    imei2: Optional[str] = Field(None, max_length=20)
    numero_chip: Optional[str] = Field(None, max_length=30)
    operadora: Optional[str] = Field(None, max_length=30)
    numero_telefone: Optional[str] = Field(None, max_length=20)
    patrimonio: Optional[str] = Field(None, max_length=50)
    acessorios: Optional[str] = Field("bateria e carregador", max_length=255)
    cor: Optional[str] = Field(None, max_length=30)
    status: Optional[str] = Field("disponivel", pattern="^(em_uso|disponivel|manutencao|inativo)$")
    responsavel_id: Optional[int] = None
    data_entrega: Optional[str] = None  # YYYY-MM-DD
    observacoes: Optional[str] = None


class CelularUpdate(BaseModel):
    marca: Optional[str] = Field(None, max_length=50)
    modelo: Optional[str] = Field(None, max_length=100)
    imei1: Optional[str] = Field(None, max_length=20)
    imei2: Optional[str] = Field(None, max_length=20)
    numero_chip: Optional[str] = Field(None, max_length=30)
    operadora: Optional[str] = Field(None, max_length=30)
    numero_telefone: Optional[str] = Field(None, max_length=20)
    patrimonio: Optional[str] = Field(None, max_length=50)
    acessorios: Optional[str] = Field(None, max_length=255)
    cor: Optional[str] = Field(None, max_length=30)
    status: Optional[str] = Field(None, pattern="^(em_uso|disponivel|manutencao|inativo)$")
    responsavel_id: Optional[int] = None
    data_entrega: Optional[str] = None
    observacoes: Optional[str] = None


def _row_to_celular(row: dict) -> dict:
    """Converte linha do banco em dict serializável."""
    for k in ("criado_em", "atualizado_em", "data_entrega"):
        if row.get(k):
            row[k] = row[k].isoformat() if hasattr(row[k], "isoformat") else str(row[k])
    return row


@router.get("/celulares")
def listar_celulares(
    status: Optional[str] = Query(None),
    responsavel_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None, description="Busca em marca/modelo/IMEI/patrimônio"),
):
    """Lista todos os celulares, com filtros opcionais."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT c.*, u.name AS responsavel_nome, u.email AS responsavel_email, u.cpf AS responsavel_cpf
            FROM inventario_celulares c
            LEFT JOIN users u ON u.id = c.responsavel_id
            WHERE 1=1
        """
        params: List = []
        if status:
            sql += " AND c.status = %s"; params.append(status)
        if responsavel_id:
            sql += " AND c.responsavel_id = %s"; params.append(responsavel_id)
        if q:
            sql += " AND (c.marca LIKE %s OR c.modelo LIKE %s OR c.imei1 LIKE %s OR c.imei2 LIKE %s OR c.patrimonio LIKE %s)"
            like = f"%{q}%"
            params += [like, like, like, like, like]
        sql += " ORDER BY c.criado_em DESC"
        cur.execute(sql, params)
        return [_row_to_celular(r) for r in cur.fetchall()]
    finally:
        cur.close(); conn.close()


@router.get("/celulares/{cel_id}")
def detalhe_celular(cel_id: int):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT c.*, u.name AS responsavel_nome, u.email AS responsavel_email, u.cpf AS responsavel_cpf
            FROM inventario_celulares c
            LEFT JOIN users u ON u.id = c.responsavel_id
            WHERE c.id = %s
        """, (cel_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Celular não encontrado")
        return _row_to_celular(row)
    finally:
        cur.close(); conn.close()


@router.post("/celulares", status_code=201)
def criar_celular(payload: CelularBase):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id FROM inventario_celulares WHERE imei1 = %s", (payload.imei1,))
        if cur.fetchone():
            raise HTTPException(400, "Já existe celular com este IMEI1")
        cur.execute("""
            INSERT INTO inventario_celulares
              (marca, modelo, imei1, imei2, numero_chip, operadora, numero_telefone,
               patrimonio, acessorios, cor, status, responsavel_id, data_entrega, observacoes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            payload.marca, payload.modelo, payload.imei1, payload.imei2,
            payload.numero_chip, payload.operadora, payload.numero_telefone,
            payload.patrimonio, payload.acessorios, payload.cor,
            payload.status, payload.responsavel_id, payload.data_entrega, payload.observacoes,
        ))
        new_id = cur.lastrowid
        if payload.responsavel_id and payload.data_entrega:
            cur.execute("""
                INSERT INTO inventario_celulares_historico
                  (celular_id, responsavel_id, data_entrega, observacoes)
                VALUES (%s,%s,%s,%s)
            """, (new_id, payload.responsavel_id, payload.data_entrega, payload.observacoes))
        conn.commit()
        cur.execute("SELECT * FROM inventario_celulares WHERE id = %s", (new_id,))
        return _row_to_celular(cur.fetchone())
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"[CELULARES] erro ao criar: {e}")
        raise HTTPException(500, f"Erro ao criar celular: {e}")
    finally:
        cur.close(); conn.close()


@router.put("/celulares/{cel_id}")
def atualizar_celular(cel_id: int, payload: CelularUpdate):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM inventario_celulares WHERE id = %s", (cel_id,))
        atual = cur.fetchone()
        if not atual:
            raise HTTPException(404, "Celular não encontrado")

        fields, vals = [], []
        for k, v in payload.model_dump(exclude_none=True).items():
            fields.append(f"`{k}` = %s"); vals.append(v)
        if not fields:
            raise HTTPException(400, "Nenhum campo para atualizar")
        vals.append(cel_id)
        cur.execute(f"UPDATE inventario_celulares SET {', '.join(fields)} WHERE id = %s", vals)

        novo_resp = payload.responsavel_id
        nova_data = payload.data_entrega
        if novo_resp is not None and novo_resp != atual.get("responsavel_id"):
            cur.execute("""
                UPDATE inventario_celulares_historico
                SET data_devolucao = CURDATE()
                WHERE celular_id = %s AND data_devolucao IS NULL
            """, (cel_id,))
            if novo_resp:
                cur.execute("""
                    INSERT INTO inventario_celulares_historico
                      (celular_id, responsavel_id, data_entrega, observacoes)
                    VALUES (%s, %s, %s, %s)
                """, (cel_id, novo_resp, nova_data or str(datetime.now().date()), payload.observacoes))

        conn.commit()
        cur.execute("""
            SELECT c.*, u.name AS responsavel_nome, u.email AS responsavel_email, u.cpf AS responsavel_cpf
            FROM inventario_celulares c
            LEFT JOIN users u ON u.id = c.responsavel_id
            WHERE c.id = %s
        """, (cel_id,))
        return _row_to_celular(cur.fetchone())
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"[CELULARES] erro ao atualizar: {e}")
        raise HTTPException(500, f"Erro ao atualizar celular: {e}")
    finally:
        cur.close(); conn.close()


@router.delete("/celulares/{cel_id}", status_code=204)
def deletar_celular(cel_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM inventario_celulares_historico WHERE celular_id = %s", (cel_id,))
        cur.execute("DELETE FROM inventario_celulares WHERE id = %s", (cel_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "Celular não encontrado")
    finally:
        cur.close(); conn.close()


@router.get("/celulares/{cel_id}/termo")
def dados_termo_celular(cel_id: int):
    """Retorna dados necessários para gerar o termo de responsabilidade.
    O frontend monta o HTML e usa window.print() para gerar o PDF."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT c.*, u.name AS responsavel_nome, u.email AS responsavel_email, u.cpf AS responsavel_cpf
            FROM inventario_celulares c
            LEFT JOIN users u ON u.id = c.responsavel_id
            WHERE c.id = %s
        """, (cel_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Celular não encontrado")
        if not row.get("responsavel_id"):
            raise HTTPException(400, "Atribua um responsável antes de gerar o termo")
        if not row.get("responsavel_cpf"):
            raise HTTPException(400,
                f"O usuário {row.get('responsavel_nome')} não tem CPF cadastrado. "
                f"Edite o perfil dele antes de gerar o termo.")
        cur.execute("""
            UPDATE inventario_celulares_historico
            SET termo_gerado_em = NOW()
            WHERE celular_id = %s AND data_devolucao IS NULL
        """, (cel_id,))
        conn.commit()
        return _row_to_celular(row)
    finally:
        cur.close(); conn.close()


# ═════════════════════════════════════════════════════════════════════════════
# FORNECEDORES DE TI — assistencia tecnica, lojas de pecas, etc
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/fornecedores")
def fornecedores_listar(ativo: Optional[bool] = Query(None)):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        sql = "SELECT * FROM fornecedores_ti WHERE 1=1"
        params: list = []
        if ativo is not None:
            sql += " AND ativo = %s"
            params.append(1 if ativo else 0)
        sql += " ORDER BY nome"
        cur.execute(sql, params)
        return {"fornecedores": cur.fetchall()}
    finally:
        cur.close(); conn.close()


@router.post("/fornecedores", status_code=201)
def fornecedores_criar(payload: dict):
    nome = (payload.get("nome") or "").strip()
    if not nome:
        raise HTTPException(400, "Nome do fornecedor é obrigatório")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO fornecedores_ti
                (nome, cnpj, endereco, responsavel, telefone, ativo)
            VALUES (%s, %s, %s, %s, %s, 1)
        """, (
            nome,
            (payload.get("cnpj") or "").strip() or None,
            (payload.get("endereco") or "").strip() or None,
            (payload.get("responsavel") or "").strip() or None,
            (payload.get("telefone") or "").strip() or None,
        ))
        conn.commit()
        return {"id": cur.lastrowid, "nome": nome}
    finally:
        cur.close(); conn.close()


@router.put("/fornecedores/{forn_id}")
def fornecedores_atualizar(forn_id: int, payload: dict):
    nome = (payload.get("nome") or "").strip()
    if not nome:
        raise HTTPException(400, "Nome do fornecedor é obrigatório")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE fornecedores_ti SET
                nome = %s, cnpj = %s, endereco = %s,
                responsavel = %s, telefone = %s,
                ativo = %s
            WHERE id = %s
        """, (
            nome,
            (payload.get("cnpj") or "").strip() or None,
            (payload.get("endereco") or "").strip() or None,
            (payload.get("responsavel") or "").strip() or None,
            (payload.get("telefone") or "").strip() or None,
            1 if payload.get("ativo", True) else 0,
            forn_id,
        ))
        if cur.rowcount == 0:
            cur.execute("SELECT 1 FROM fornecedores_ti WHERE id = %s", (forn_id,))
            if not cur.fetchone():
                raise HTTPException(404, "Fornecedor não encontrado")
        conn.commit()
        return {"ok": True}
    finally:
        cur.close(); conn.close()


@router.delete("/fornecedores/{forn_id}", status_code=204)
def fornecedores_excluir(forn_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Não deleta se há manutenções vinculadas — desativa em vez disso
        cur.execute(
            "SELECT COUNT(*) FROM inventario_manutencoes WHERE fornecedor_id = %s",
            (forn_id,),
        )
        if (cur.fetchone() or [0])[0] > 0:
            cur.execute(
                "UPDATE fornecedores_ti SET ativo = 0 WHERE id = %s", (forn_id,)
            )
            conn.commit()
            return
        cur.execute("DELETE FROM fornecedores_ti WHERE id = %s", (forn_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Fornecedor não encontrado")
        conn.commit()
    finally:
        cur.close(); conn.close()


# ═════════════════════════════════════════════════════════════════════════════
# MANUTENCOES DE TI — historico + upload PDF de orcamento
# ═════════════════════════════════════════════════════════════════════════════

# Pasta de upload dos PDFs de orcamento (criada sob demanda)
_MANUT_UPLOAD_DIR = pathlib.Path(__file__).resolve().parent.parent.parent \
    / "web" / "uploads" / "manutencoes"
_MANUT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def _row_to_manutencao(r: dict) -> dict:
    """Normaliza linha do JOIN manutencoes + fornecedores + dispositivos."""
    if r.get("valor") is not None:
        r["valor"] = float(r["valor"])
    for k in ("data_envio", "data_retorno", "criado_em", "atualizado_em"):
        if r.get(k) and hasattr(r[k], "strftime"):
            r[k] = r[k].strftime("%Y-%m-%d %H:%M:%S")
    return r


@router.get("/manutencoes")
def manutencoes_listar(status: Optional[str] = Query(None)):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT m.*,
                   f.nome AS fornecedor_nome,
                   d.hostname AS dispositivo_hostname,
                   d.apelido  AS dispositivo_apelido
              FROM inventario_manutencoes m
              LEFT JOIN fornecedores_ti      f ON f.id = m.fornecedor_id
              LEFT JOIN inventario_dispositivos d ON d.id = m.dispositivo_id
             WHERE 1=1
        """
        params: list = []
        if status:
            sql += " AND m.status = %s"
            params.append(status)
        sql += " ORDER BY m.data_envio DESC, m.id DESC"
        cur.execute(sql, params)
        rows = [_row_to_manutencao(r) for r in cur.fetchall()]
        return {"manutencoes": rows, "total": len(rows)}
    finally:
        cur.close(); conn.close()


@router.get("/manutencoes/{manut_id}")
def manutencao_detalhe(manut_id: int):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT m.*,
                   f.nome AS fornecedor_nome,
                   d.hostname AS dispositivo_hostname,
                   d.apelido  AS dispositivo_apelido
              FROM inventario_manutencoes m
              LEFT JOIN fornecedores_ti      f ON f.id = m.fornecedor_id
              LEFT JOIN inventario_dispositivos d ON d.id = m.dispositivo_id
             WHERE m.id = %s
        """, (manut_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Manutenção não encontrada")
        return _row_to_manutencao(row)
    finally:
        cur.close(); conn.close()


@router.post("/manutencoes", status_code=201)
async def manutencao_criar(
    problema:            str            = Form(...),
    dispositivo_id:      Optional[int]  = Form(None),
    marca:               Optional[str]  = Form(None),
    modelo:              Optional[str]  = Form(None),
    usuario_responsavel: Optional[str]  = Form(None),
    valor:               Optional[float] = Form(None),
    fornecedor_id:       Optional[int]  = Form(None),
    status:              str            = Form("orcamento"),
    observacoes:         Optional[str]  = Form(None),
    orcamento:           Optional[UploadFile] = File(None),
):
    """Cria registro de manutenção e marca o dispositivo como em_manutencao."""
    problema = (problema or "").strip()
    if not problema:
        raise HTTPException(400, "Descrição do problema é obrigatória")

    # Se vinculado a dispositivo, copia marca/modelo dele caso não venha no form
    if dispositivo_id and (not marca or not modelo):
        conn0 = get_db_connection()
        cur0 = conn0.cursor(dictionary=True)
        try:
            cur0.execute(
                "SELECT marca, modelo FROM inventario_dispositivos WHERE id = %s",
                (dispositivo_id,),
            )
            d = cur0.fetchone()
            if d:
                marca  = marca  or d.get("marca")
                modelo = modelo or d.get("modelo")
        finally:
            cur0.close(); conn0.close()

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO inventario_manutencoes
                (dispositivo_id, marca, modelo, usuario_responsavel,
                 problema, valor, fornecedor_id, status, observacoes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            dispositivo_id, marca, modelo,
            (usuario_responsavel or "").strip() or None,
            problema, valor, fornecedor_id, status,
            (observacoes or "").strip() or None,
        ))
        new_id = cur.lastrowid

        # Salva PDF do orçamento se enviado
        if orcamento and orcamento.filename:
            ext = pathlib.Path(orcamento.filename).suffix.lower() or ".pdf"
            if ext not in (".pdf", ".jpg", ".jpeg", ".png"):
                raise HTTPException(400, "Anexo deve ser PDF ou imagem")
            content = await orcamento.read()
            if len(content) > _MANUT_MAX_BYTES:
                raise HTTPException(413, "Arquivo maior que 10 MB")
            _MANUT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            fname = f"m{new_id}_{hashlib.md5(content).hexdigest()[:8]}{ext}"
            (_MANUT_UPLOAD_DIR / fname).write_bytes(content)
            rel_path = f"/SistemaCPE/web/uploads/manutencoes/{fname}"
            cur.execute(
                "UPDATE inventario_manutencoes SET orcamento_path = %s WHERE id = %s",
                (rel_path, new_id),
            )

        # Marca dispositivo como em manutenção
        if dispositivo_id:
            cur.execute("""
                UPDATE inventario_dispositivos
                   SET em_manutencao = 1, manutencao_atual_id = %s
                 WHERE id = %s
            """, (new_id, dispositivo_id))

        conn.commit()
        return {"id": new_id, "ok": True}
    finally:
        cur.close(); conn.close()


@router.put("/manutencoes/{manut_id}")
def manutencao_atualizar(manut_id: int, payload: dict):
    """Atualiza campos textuais e status. Para trocar PDF, recriar.

    Se status mudar pra 'concluida' ou 'cancelada' e havia um dispositivo
    vinculado em em_manutencao, libera o flag e seta data_retorno.
    """
    allowed_status = {"orcamento", "aprovada", "em_andamento", "concluida", "cancelada"}
    new_status = payload.get("status")
    if new_status is not None and new_status not in allowed_status:
        raise HTTPException(400, f"Status inválido: {new_status}")

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT id, dispositivo_id, status FROM inventario_manutencoes WHERE id = %s",
            (manut_id,),
        )
        atual = cur.fetchone()
        if not atual:
            raise HTTPException(404, "Manutenção não encontrada")

        fields, params = [], []
        for k in ("marca", "modelo", "usuario_responsavel", "problema",
                  "observacoes"):
            if k in payload:
                fields.append(f"{k} = %s")
                v = payload.get(k)
                params.append((v or "").strip() or None if isinstance(v, str) else v)
        if "valor" in payload:
            fields.append("valor = %s"); params.append(payload.get("valor"))
        if "fornecedor_id" in payload:
            fields.append("fornecedor_id = %s"); params.append(payload.get("fornecedor_id"))
        if new_status:
            fields.append("status = %s"); params.append(new_status)
            if new_status in ("concluida", "cancelada"):
                fields.append("data_retorno = COALESCE(data_retorno, NOW())")
        if not fields:
            return {"ok": True, "noop": True}
        params.append(manut_id)
        cur.execute(
            f"UPDATE inventario_manutencoes SET {', '.join(fields)} WHERE id = %s",
            params,
        )

        # Se fechou a manutenção do dispositivo, libera o flag
        if new_status in ("concluida", "cancelada") and atual.get("dispositivo_id"):
            cur.execute("""
                UPDATE inventario_dispositivos
                   SET em_manutencao = 0, manutencao_atual_id = NULL
                 WHERE id = %s AND manutencao_atual_id = %s
            """, (atual["dispositivo_id"], manut_id))

        conn.commit()
        return {"ok": True}
    finally:
        cur.close(); conn.close()


@router.delete("/manutencoes/{manut_id}", status_code=204)
def manutencao_excluir(manut_id: int):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT id, dispositivo_id, orcamento_path FROM inventario_manutencoes WHERE id = %s",
            (manut_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Manutenção não encontrada")

        # Apaga PDF do disco
        if row.get("orcamento_path"):
            fname = pathlib.Path(row["orcamento_path"]).name
            try:
                (_MANUT_UPLOAD_DIR / fname).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Falha ao apagar PDF {fname}: {e}")

        cur.execute("DELETE FROM inventario_manutencoes WHERE id = %s", (manut_id,))

        # Se era a manutenção ativa do dispositivo, libera o flag
        if row.get("dispositivo_id"):
            cur.execute("""
                UPDATE inventario_dispositivos
                   SET em_manutencao = 0, manutencao_atual_id = NULL
                 WHERE id = %s AND manutencao_atual_id = %s
            """, (row["dispositivo_id"], manut_id))

        conn.commit()
    finally:
        cur.close(); conn.close()


@router.get("/manutencoes/{manut_id}/orcamento")
def manutencao_baixar_orcamento(manut_id: int):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT orcamento_path FROM inventario_manutencoes WHERE id = %s",
            (manut_id,),
        )
        row = cur.fetchone()
        if not row or not row.get("orcamento_path"):
            raise HTTPException(404, "Orçamento não encontrado")
        fname = pathlib.Path(row["orcamento_path"]).name
        path  = _MANUT_UPLOAD_DIR / fname
        if not path.exists():
            raise HTTPException(404, "Arquivo do orçamento não está no disco")
        return FileResponse(path, filename=fname)
    finally:
        cur.close(); conn.close()


# ═════════════════════════════════════════════════════════════════════════════
# CONTROLE FINANCEIRO DO ESTOQUE T.I. (inventario_itens)
# Quem usa, quanto vale, onde está, estoque baixo, perda por inativação.
# ═════════════════════════════════════════════════════════════════════════════

_ITEM_CATEGORIAS = {"hardware", "periferico", "suprimento",
                    "software", "mobiliario", "outro"}


def _row_to_item(r: dict) -> dict:
    """Converte tipos não-JSON e calcula valor_total."""
    if r.get("valor_unitario") is not None:
        r["valor_unitario"] = float(r["valor_unitario"])
    qtd = r.get("quantidade") or 0
    val = r.get("valor_unitario") or 0
    r["valor_total"] = round(qtd * val, 2)
    r["baixo_estoque"] = bool(
        r.get("estoque_minimo") and qtd < r.get("estoque_minimo")
    )
    for k in ("inativado_em", "criado_em", "atualizado_em"):
        if r.get(k) and hasattr(r[k], "strftime"):
            r[k] = r[k].strftime("%Y-%m-%d %H:%M:%S")
    return r


@router.get("/itens")
def itens_listar(
    ativo:       Optional[bool] = Query(None),
    categoria:   Optional[str]  = Query(None),
    grupo_id:    Optional[int]  = Query(None),
    unidade_cpe: Optional[str]  = Query(None),
    search:      Optional[str]  = Query(None),
):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT i.*,
                   g.name      AS grupo_nome,
                   d.hostname  AS dispositivo_hostname,
                   d.apelido   AS dispositivo_apelido,
                   u.name      AS inativado_por_nome
              FROM inventario_itens i
              LEFT JOIN cpe_grupo                g ON g.id = i.grupo_id
              LEFT JOIN inventario_dispositivos  d ON d.id = i.dispositivo_id
              LEFT JOIN users                    u ON u.id = i.inativado_por_user_id
             WHERE 1=1
        """
        params: list = []
        if ativo is not None:
            sql += " AND i.ativo = %s"
            params.append(1 if ativo else 0)
        if categoria:
            sql += " AND i.categoria = %s"
            params.append(categoria)
        if grupo_id:
            sql += " AND i.grupo_id = %s"
            params.append(grupo_id)
        if unidade_cpe:
            sql += " AND i.unidade_cpe = %s"
            params.append(unidade_cpe)
        if search:
            sql += """ AND (i.nome LIKE %s OR i.codigo LIKE %s
                            OR i.descricao LIKE %s OR i.localizacao_detalhe LIKE %s)"""
            s = f"%{search}%"
            params.extend([s, s, s, s])
        sql += " ORDER BY i.ativo DESC, i.nome"
        cur.execute(sql, params)
        rows = [_row_to_item(r) for r in cur.fetchall()]
        return {"itens": rows, "total": len(rows)}
    finally:
        cur.close(); conn.close()


@router.get("/itens/stats")
def itens_stats():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT
                COUNT(*)                                            AS total,
                SUM(ativo = 1)                                      AS ativos,
                SUM(ativo = 0)                                      AS inativos,
                ROUND(COALESCE(SUM(
                    CASE WHEN ativo=1 THEN quantidade * valor_unitario END
                ), 0), 2)                                           AS valor_ativo,
                ROUND(COALESCE(SUM(
                    CASE WHEN ativo=0 THEN quantidade * valor_unitario END
                ), 0), 2)                                           AS valor_inativo,
                SUM(ativo = 1 AND estoque_minimo > 0
                    AND quantidade < estoque_minimo)                AS baixo_estoque
            FROM inventario_itens
        """)
        s = cur.fetchone() or {}
        # MySQL devolve Decimal para SUM — converte pra float
        for k in ("valor_ativo", "valor_inativo"):
            if s.get(k) is not None:
                s[k] = float(s[k])
        return s
    finally:
        cur.close(); conn.close()


def _checar_duplicatas(cur, dispositivo_id, numero_serie, ignore_id=None):
    """Valida que nao existe outro item financeiro com mesmo dispositivo OU
    mesmo numero de serie (quando preenchido).
    Lanca HTTPException 409 com mensagem clara."""
    if dispositivo_id:
        sql = "SELECT id, nome FROM inventario_itens WHERE dispositivo_id = %s"
        params = [dispositivo_id]
        if ignore_id:
            sql += " AND id <> %s"; params.append(ignore_id)
        cur.execute(sql, params)
        row = cur.fetchone()
        if row:
            other_id, other_nome = (row["id"], row["nome"]) if isinstance(row, dict) else row
            raise HTTPException(
                409,
                f"Este equipamento já está vinculado ao item #{other_id} "
                f"({other_nome}). Edite o item existente em vez de criar outro."
            )
    if numero_serie:
        sql = "SELECT id, nome FROM inventario_itens WHERE numero_serie = %s"
        params = [numero_serie]
        if ignore_id:
            sql += " AND id <> %s"; params.append(ignore_id)
        cur.execute(sql, params)
        row = cur.fetchone()
        if row:
            other_id, other_nome = (row["id"], row["nome"]) if isinstance(row, dict) else row
            raise HTTPException(
                409,
                f"Já existe um item com este número de série: #{other_id} ({other_nome})."
            )


@router.post("/itens", status_code=201)
def itens_criar(payload: dict):
    nome = (payload.get("nome") or "").strip()
    if not nome:
        raise HTTPException(400, "Nome do item é obrigatório")
    categoria = (payload.get("categoria") or "outro").strip()
    if categoria not in _ITEM_CATEGORIAS:
        raise HTTPException(400, f"Categoria inválida: {categoria}")

    qtd = int(payload.get("quantidade") or 0)
    val = float(payload.get("valor_unitario") or 0)
    if qtd < 0 or val < 0:
        raise HTTPException(400, "Quantidade/valor não podem ser negativos")

    dispositivo_id = payload.get("dispositivo_id") or None
    numero_serie   = (payload.get("numero_serie") or "").strip() or None

    completo = 1 if payload.get("completo", True) else 0
    justif   = (payload.get("justificativa_incompleto") or "").strip() or None
    if completo == 0 and not justif:
        raise HTTPException(400, "Equipamento marcado como incompleto exige justificativa")

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        _checar_duplicatas(cur, dispositivo_id, numero_serie)
        cur.execute("""
            INSERT INTO inventario_itens
                (nome, codigo, numero_serie, categoria, descricao,
                 completo, justificativa_incompleto,
                 quantidade, valor_unitario, estoque_minimo,
                 unidade_cpe, grupo_id, localizacao_detalhe, dispositivo_id,
                 ativo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
        """, (
            nome,
            (payload.get("codigo") or "").strip() or None,
            numero_serie,
            categoria,
            (payload.get("descricao") or "").strip() or None,
            completo,
            justif if completo == 0 else None,
            qtd, val,
            int(payload.get("estoque_minimo") or 0),
            (payload.get("unidade_cpe") or "").strip() or None,
            payload.get("grupo_id") or None,
            (payload.get("localizacao_detalhe") or "").strip() or None,
            dispositivo_id,
        ))
        conn.commit()
        return {"id": cur.lastrowid, "ok": True}
    finally:
        cur.close(); conn.close()


@router.put("/itens/{item_id}")
def itens_atualizar(item_id: int, payload: dict):
    """Atualiza campos textuais e financeiros. Status muda via /inativar."""
    if "categoria" in payload and payload["categoria"] not in _ITEM_CATEGORIAS:
        raise HTTPException(400, f"Categoria inválida")

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        # Valida duplicatas (dispositivo / numero_serie) — ignorando o próprio
        dispositivo_id = payload.get("dispositivo_id") if "dispositivo_id" in payload else None
        numero_serie   = (payload.get("numero_serie") or "").strip() if "numero_serie" in payload else None
        if "dispositivo_id" in payload or "numero_serie" in payload:
            _checar_duplicatas(cur, dispositivo_id or None,
                               numero_serie or None, ignore_id=item_id)

        fields, params = [], []
        for k in ("nome", "codigo", "numero_serie", "categoria", "descricao",
                  "unidade_cpe", "localizacao_detalhe", "justificativa_incompleto"):
            if k in payload:
                v = payload.get(k)
                fields.append(f"{k} = %s")
                params.append((v or "").strip() or None if isinstance(v, str) else v)
        for k in ("quantidade", "estoque_minimo"):
            if k in payload:
                fields.append(f"{k} = %s")
                params.append(int(payload.get(k) or 0))
        if "completo" in payload:
            completo_val = 1 if payload.get("completo") else 0
            if completo_val == 0:
                justif = (payload.get("justificativa_incompleto") or "").strip()
                if not justif:
                    # Se PUT marca incompleto sem mandar justificativa, busca
                    # a já existente; se também não existe, exige no payload.
                    cur.execute(
                        "SELECT justificativa_incompleto FROM inventario_itens WHERE id = %s",
                        (item_id,)
                    )
                    row = cur.fetchone()
                    if not row or not (row.get("justificativa_incompleto") or "").strip():
                        raise HTTPException(400, "Equipamento incompleto exige justificativa")
            fields.append("completo = %s")
            params.append(completo_val)
        if "valor_unitario" in payload:
            fields.append("valor_unitario = %s")
            params.append(float(payload.get("valor_unitario") or 0))
        if "grupo_id" in payload:
            fields.append("grupo_id = %s")
            params.append(payload.get("grupo_id") or None)
        if "dispositivo_id" in payload:
            fields.append("dispositivo_id = %s")
            params.append(payload.get("dispositivo_id") or None)
        if not fields:
            return {"ok": True, "noop": True}
        params.append(item_id)
        cur.execute(
            f"UPDATE inventario_itens SET {', '.join(fields)} WHERE id = %s",
            params,
        )
        if cur.rowcount == 0:
            cur.execute("SELECT 1 FROM inventario_itens WHERE id = %s", (item_id,))
            if not cur.fetchone():
                raise HTTPException(404, "Item não encontrado")
        conn.commit()
        return {"ok": True}
    finally:
        cur.close(); conn.close()


@router.delete("/itens/{item_id}", status_code=204)
def itens_excluir(item_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM inventario_itens WHERE id = %s", (item_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Item não encontrado")
        conn.commit()
    finally:
        cur.close(); conn.close()


@router.patch("/itens/{item_id}/inativar")
def itens_inativar(item_id: int, payload: dict):
    """Marca item como inativo. Motivo obrigatório.

    Inativar não deleta — o item continua no banco para o relatório
    de "valor parado / perda" no KPI Valor Inativo.
    """
    motivo = (payload.get("motivo") or "").strip()
    if not motivo:
        raise HTTPException(400, "Motivo da inativação é obrigatório")
    user_id = payload.get("inativado_por_user_id") or None

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE inventario_itens
               SET ativo = 0,
                   motivo_inativacao = %s,
                   inativado_em = NOW(),
                   inativado_por_user_id = %s
             WHERE id = %s
        """, (motivo, user_id, item_id))
        if cur.rowcount == 0:
            cur.execute("SELECT 1 FROM inventario_itens WHERE id = %s", (item_id,))
            if not cur.fetchone():
                raise HTTPException(404, "Item não encontrado")
        conn.commit()
        return {"ok": True, "ativo": False}
    finally:
        cur.close(); conn.close()


@router.patch("/itens/{item_id}/reativar")
def itens_reativar(item_id: int):
    """Reativa item (limpa motivo de inativação)."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE inventario_itens
               SET ativo = 1,
                   motivo_inativacao = NULL,
                   inativado_em = NULL,
                   inativado_por_user_id = NULL
             WHERE id = %s
        """, (item_id,))
        if cur.rowcount == 0:
            cur.execute("SELECT 1 FROM inventario_itens WHERE id = %s", (item_id,))
            if not cur.fetchone():
                raise HTTPException(404, "Item não encontrado")
        conn.commit()
        return {"ok": True, "ativo": True}
    finally:
        cur.close(); conn.close()


@router.get("/itens/dispositivos-disponiveis")
def itens_dispositivos_disponiveis():
    """Lista dispositivos do agente que ainda NÃO estão vinculados a um item
    financeiro. Usado no modal de cadastro pra pré-popular notebook."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT d.id, d.hostname, d.apelido, d.marca, d.modelo, d.tipo,
                   d.numero_serie, d.nome_responsavel, d.localizacao_cpe
              FROM inventario_dispositivos d
              LEFT JOIN inventario_itens i ON i.dispositivo_id = d.id
             WHERE i.id IS NULL
             ORDER BY d.hostname
        """)
        return {"dispositivos": cur.fetchall()}
    finally:
        cur.close(); conn.close()
