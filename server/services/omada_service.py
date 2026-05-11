"""
omada_service.py — cliente HTTP para o Omada Controller (TP-Link).

Read-only: descobre o omadacId, faz login, lista sites e devices.
Token é cacheado em memória (TTL 30 min) pra evitar relogar a cada request.

Compatível com Omada Controller v5/v6 (API v2/v3).
"""

from __future__ import annotations

import os
import time
import logging
import threading
from typing import Optional

import requests
import urllib3

# Controller geralmente tem certificado self-signed — desliga o warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

BASE_URL = (os.environ.get("OMADA_BASE_URL") or "").rstrip("/")
USERNAME = os.environ.get("OMADA_USER", "")
PASSWORD = os.environ.get("OMADA_PASS", "")
SITE_OVR = os.environ.get("OMADA_SITE", "").strip() or None

_TIMEOUT = 10
_TOKEN_TTL_S = 25 * 60   # 25 minutos (refresh antes do controller expirar)


class OmadaError(Exception):
    pass


# ─── Cache de sessão ─────────────────────────────────────────────────
_lock = threading.Lock()
_session_state = {
    "omadac_id":   None,    # ID do controller (descoberto em /api/info)
    "token":       None,    # Csrf-Token retornado no login
    "session":     None,    # requests.Session com cookies do controller
    "expira_em":   0.0,
    "sites":       [],      # cache leve de sites (id + name)
}


def _configurado() -> bool:
    return bool(BASE_URL and USERNAME and PASSWORD)


def _descobrir_omadac_id(session: requests.Session) -> str:
    r = session.get(f"{BASE_URL}/api/info", timeout=_TIMEOUT, verify=False)
    r.raise_for_status()
    data = r.json()
    if data.get("errorCode") != 0:
        raise OmadaError(f"/api/info: {data.get('msg')}")
    oid = data.get("result", {}).get("omadacId")
    if not oid:
        raise OmadaError("omadacId ausente em /api/info")
    return oid


def _login() -> dict:
    """Loga no controller e devolve estado de sessão pronto pra uso.
    Retorna dict com 'session', 'omadac_id', 'token'. Levanta OmadaError."""
    if not _configurado():
        raise OmadaError("OMADA_* não configurado no .env")

    session = requests.Session()
    omadac_id = _descobrir_omadac_id(session)
    url = f"{BASE_URL}/{omadac_id}/api/v2/login"
    r = session.post(url,
                     json={"username": USERNAME, "password": PASSWORD},
                     timeout=_TIMEOUT, verify=False)
    r.raise_for_status()
    data = r.json()
    if data.get("errorCode") != 0:
        raise OmadaError(f"login: {data.get('msg')}")
    token = data.get("result", {}).get("token")
    if not token:
        raise OmadaError("token ausente na resposta de login")
    return {"session": session, "omadac_id": omadac_id, "token": token}


def _sessao_valida() -> dict:
    """Garante uma sessão válida (relogar se expirou). Thread-safe."""
    with _lock:
        agora = time.monotonic()
        if (_session_state["token"]
                and _session_state["session"]
                and _session_state["expira_em"] > agora):
            return {
                "session":    _session_state["session"],
                "omadac_id":  _session_state["omadac_id"],
                "token":      _session_state["token"],
            }
        info = _login()
        _session_state.update(info)
        _session_state["expira_em"] = agora + _TOKEN_TTL_S
        _session_state["sites"] = []  # limpa cache de sites
        logger.info("[OMADA] Sessão renovada (omadacId=%s)", info["omadac_id"])
        return info


def _api_get(path: str) -> dict:
    """Helper interno: GET autenticado em /{omadacId}/api/v2/<path>."""
    info = _sessao_valida()
    url = f"{BASE_URL}/{info['omadac_id']}/api/v2/{path.lstrip('/')}"
    r = info["session"].get(url,
                            headers={"Csrf-Token": info["token"]},
                            timeout=_TIMEOUT, verify=False)
    # Se token expirou (401/sessão), força relogin uma vez
    if r.status_code in (401, 403):
        with _lock:
            _session_state["token"] = None
            _session_state["expira_em"] = 0
        info = _sessao_valida()
        url = f"{BASE_URL}/{info['omadac_id']}/api/v2/{path.lstrip('/')}"
        r = info["session"].get(url,
                                headers={"Csrf-Token": info["token"]},
                                timeout=_TIMEOUT, verify=False)
    r.raise_for_status()
    data = r.json()
    if data.get("errorCode") != 0:
        raise OmadaError(f"{path}: {data.get('msg')}")
    return data.get("result") or {}


def listar_sites() -> list[dict]:
    """Lista sites cadastrados no controller."""
    if _session_state["sites"]:
        return _session_state["sites"]
    res = _api_get("sites?currentPage=1&currentPageSize=100")
    sites = res.get("data", []) if isinstance(res, dict) else []
    _session_state["sites"] = [
        {"id": s.get("id"), "name": s.get("name")}
        for s in sites if s.get("id")
    ]
    return _session_state["sites"]


def _resolver_site_id() -> Optional[str]:
    """Resolve o site_id baseado em OMADA_SITE (nome) ou pega o primeiro."""
    sites = listar_sites()
    if not sites:
        return None
    if SITE_OVR:
        for s in sites:
            if s["name"].lower() == SITE_OVR.lower() or s["id"] == SITE_OVR:
                return s["id"]
    return sites[0]["id"]


def listar_devices(site_id: Optional[str] = None) -> list[dict]:
    """Lista dispositivos (APs/switches/gateways) de um site.

    Retorna lista normalizada com chaves estáveis para o frontend:
        id, hostname, mac, ip, modelo, tipo, status,
        firmware, uptime, clients, site_id, site_name.
    """
    sid = site_id or _resolver_site_id()
    if not sid:
        return []

    res = _api_get(f"sites/{sid}/devices")
    devices_raw = res if isinstance(res, list) else res.get("data") or []

    # Pelo controller v6: `type` é string ("ap"|"switch"|"gateway").
    # `status` é int: 0/1 = desconectado; >= 10 = conectado (variantes de
    # provisioning/upgrading/ready). Confirmado: status=15 com clientes ativos.
    TIPOS_VALIDOS = {"ap", "switch", "gateway"}

    site_name = ""
    for s in _session_state["sites"]:
        if s["id"] == sid:
            site_name = s["name"]; break

    out = []
    for d in devices_raw:
        status_raw = d.get("status")
        try:
            status_int = int(status_raw) if status_raw is not None else 0
        except (TypeError, ValueError):
            status_int = 0
        online = status_int >= 10

        tipo = (d.get("type") or "").lower().strip()
        if tipo not in TIPOS_VALIDOS:
            tipo = "outro"

        out.append({
            "id":          d.get("mac") or d.get("id"),
            "hostname":    d.get("name") or d.get("hostname") or "—",
            "mac":         d.get("mac") or "",
            "ip":          d.get("ip") or "",
            "modelo":      d.get("model") or d.get("showModel") or "",
            "tipo":        tipo,
            "status":      "online" if online else "offline",
            "firmware":    d.get("firmwareVersion") or "",
            "uptime":      d.get("uptime") or "",       # string já formatada "6day(s) 20h..."
            "uptime_s":    d.get("uptimeLong") or 0,    # em segundos
            "clients":     d.get("clientNum") or d.get("clientNumByDualBand") or 0,
            "sn":          d.get("sn") or "",
            "cpu_pct":     d.get("cpuUtil"),
            "mem_pct":     d.get("memUtil"),
            "site_id":     sid,
            "site_name":   site_name,
        })
    return out


def listar_devices_todos_sites() -> list[dict]:
    """Lista dispositivos de todos os sites visíveis pra esse usuário."""
    sites = listar_sites()
    if not sites:
        return []
    all_devs = []
    for s in sites:
        try:
            all_devs.extend(listar_devices(s["id"]))
        except Exception as exc:
            logger.warning("[OMADA] Falha listando site %s (%s): %s",
                           s.get("name"), s.get("id"), exc)
    return all_devs


# ─── Clientes ativos ─────────────────────────────────────────────────
# Mapa do `deviceCategory` do Omada → label PT-BR usado no frontend
_CAT_LABEL = {
    "Mobile":  "telemovel",
    "Office":  "escritorio",
    "Network": "rede",
    "Others":  "outros",
}


def listar_clientes(site_id: Optional[str] = None) -> list[dict]:
    """Lista clientes ATIVOS (conectados agora) de um site específico.

    Retorna lista normalizada com: id, nome, mac, ip, ssid, ap_name, ap_mac,
    categoria (telemovel|escritorio|rede|outros), os_name, vendor, signal,
    rx_rate, tx_rate, conexao (wired/wireless), site_id, site_name.
    """
    sid = site_id or _resolver_site_id()
    if not sid:
        return []

    # Pagina pra evitar limite implícito do controller
    todos: list[dict] = []
    page = 1
    while True:
        res = _api_get(
            f"sites/{sid}/clients"
            f"?currentPage={page}&currentPageSize=500&filters.active=true"
        )
        page_data = (res.get("data") if isinstance(res, dict) else res) or []
        if not page_data:
            break
        todos.extend(page_data)
        # Encerra se já pegou tudo
        total = res.get("totalRows") if isinstance(res, dict) else len(page_data)
        if len(todos) >= (total or len(todos)):
            break
        page += 1
        if page > 20:  # paranoia: max 10k clientes
            break

    site_name = ""
    for s in _session_state["sites"]:
        if s["id"] == sid:
            site_name = s["name"]; break

    out = []
    for c in todos:
        cat = _CAT_LABEL.get(c.get("deviceCategory") or "Others", "outros")
        sinal = c.get("signalLevel")
        out.append({
            "id":          c.get("mac"),
            "nome":        c.get("hostName") or c.get("name") or c.get("mac"),
            "mac":         c.get("mac") or "",
            "ip":          c.get("ip") or "",
            "ssid":        c.get("ssid") or "",
            "ap_name":     c.get("apName") or "",
            "ap_mac":      c.get("apMac") or "",
            "categoria":   cat,
            "os_name":     c.get("osName") or "",
            "vendor":      c.get("vendor") or "",
            "signal":      sinal if isinstance(sinal, (int, float)) else None,
            "rx_rate_kbps": c.get("rxRate") or 0,
            "tx_rate_kbps": c.get("txRate") or 0,
            "wireless":    bool(c.get("wireless")),
            "site_id":     sid,
            "site_name":   site_name,
        })
    return out


def listar_clientes_todos_sites() -> list[dict]:
    """Agrega clientes ativos de todos os sites."""
    sites = listar_sites()
    if not sites:
        return []
    todos = []
    for s in sites:
        try:
            todos.extend(listar_clientes(s["id"]))
        except Exception as exc:
            logger.warning("[OMADA] Clientes falharam no site %s (%s): %s",
                           s.get("name"), s.get("id"), exc)
    return todos


# ─── Topologia ───────────────────────────────────────────────────────
def topologia(site_id: Optional[str] = None) -> dict:
    """Constrói um snapshot de topologia: switches/gateways como nós-pai,
    APs como filhos, e o agregado de clientes (count) por AP.

    Estrutura:
        {
          "site_id": ..., "site_name": ...,
          "switches":  [{... infos do device ...}],
          "aps":       [{... infos do device, clients_count ...}],
          "gateways":  [{... infos do device ...}],
          "outros":    [...],
        }
    """
    sid = site_id or _resolver_site_id()
    if not sid:
        return {"site_id": None, "site_name": "", "switches": [], "aps": [], "gateways": [], "outros": []}

    devs = listar_devices(sid)

    # clientNum já vem direto do device. Mas pra reforçar, contamos
    # clientes ativos por apMac quando disponível.
    try:
        clientes = listar_clientes(sid)
        clients_per_ap: dict[str, int] = {}
        for c in clientes:
            if c.get("ap_mac"):
                clients_per_ap[c["ap_mac"]] = clients_per_ap.get(c["ap_mac"], 0) + 1
    except Exception:
        clients_per_ap = {}

    site_name = ""
    for s in _session_state["sites"]:
        if s["id"] == sid:
            site_name = s["name"]; break

    buckets = {"switches": [], "aps": [], "gateways": [], "outros": []}
    for d in devs:
        d_copy = dict(d)
        d_copy["clients_count"] = clients_per_ap.get(d.get("mac"), d.get("clients") or 0)
        key = {"ap": "aps", "switch": "switches", "gateway": "gateways"}.get(d.get("tipo"), "outros")
        buckets[key].append(d_copy)

    return {
        "site_id":   sid,
        "site_name": site_name,
        **buckets,
    }
