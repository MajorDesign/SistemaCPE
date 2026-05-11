"""
mikrotik_service.py — cliente HTTP/API pro Mikrotik RouterOS.

Conecta via API (porta 8728/8729) e coleta status das WANs:
- Status (running ou não) das interfaces WAN
- Latência média + perda via ping pra alvos externos (ex: 8.8.8.8)
- CPU, RAM e uptime do Mikrotik
- Tráfego rx/tx das WANs (Mbps)

Read-only. Usa o user `cpe-monitor-geral` configurado em cada unidade.
"""

from __future__ import annotations

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

USER     = os.environ.get("MIKROTIK_USER", "cpe-monitor-geral")
PASS     = os.environ.get("MIKROTIK_PASS", "")
DEFAULT_PORT = int(os.environ.get("MIKROTIK_PORT", "8728"))
PING_TARGETS = ["1.1.1.1", "8.8.8.8"]  # alvos pra teste de latência
PING_COUNT   = 3     # 3 pings = mesmo que o terminal usa (mais estável)
PING_TIMEOUT_MS = 1000


class MikrotikError(Exception):
    pass


def _conectar(host: str, port: int = DEFAULT_PORT, timeout: int = 6):
    """Conecta no Mikrotik. Lança MikrotikError em qualquer falha."""
    try:
        # Import tardio pra não derrubar a API se a lib não estiver instalada
        import routeros_api
    except ImportError:
        raise MikrotikError("biblioteca routeros-api não instalada")

    if not PASS:
        raise MikrotikError("MIKROTIK_PASS não configurado no .env")

    try:
        conn = routeros_api.RouterOsApiPool(
            host, username=USER, password=PASS,
            port=port, plaintext_login=True,
            use_ssl=(port == 8729),
            ssl_verify=False, ssl_verify_hostname=False,
        )
        return conn
    except Exception as exc:
        raise MikrotikError(f"falha ao conectar em {host}:{port} — {exc}")


def _resource(api) -> dict:
    """Lê CPU/RAM/uptime do Mikrotik."""
    res = api.get_resource("/system/resource")
    rows = res.get()
    if not rows:
        return {}
    r = rows[0]
    try:
        cpu = int(r.get("cpu-load", 0))
    except (TypeError, ValueError):
        cpu = 0
    try:
        free_mem = int(r.get("free-memory", 0))
        total_mem = int(r.get("total-memory", 1))
        mem_pct = round(100 * (1 - free_mem / total_mem), 1) if total_mem else None
    except (TypeError, ValueError):
        mem_pct = None
    return {
        "cpu_pct":   cpu,
        "mem_pct":   mem_pct,
        "uptime":    r.get("uptime") or "",
        "board":     r.get("board-name") or "",
        "version":   r.get("version") or "",
        "free_mem_mb": round((free_mem or 0) / 1048576, 1) if 'free_mem' in dir() else None,
    }


def _truthy(v) -> bool:
    """Normaliza valores 'true'/'false'/'yes'/'no'/bool retornados pela API."""
    if isinstance(v, bool):
        return v
    return str(v or "").strip().lower() in ("true", "yes", "1")


def _interface_status(api, name: str) -> dict:
    """Retorna status básico de uma interface (running + tx/rx bytes).

    Usa `get(name=...)` (filtro nativo) ao invés de `call("print", ...)` —
    `print` retorna campos com formato dependente da versão e às vezes
    omite `running` quando false, daí o falso-positivo de "offline"."""
    res = api.get_resource("/interface")
    try:
        rows = res.get(name=name)
    except Exception as exc:
        logger.debug("get interface %s: %s", name, exc)
        rows = []
    if not rows:
        return {"running": False, "disabled": True, "rx_bps": 0, "tx_bps": 0, "comment": ""}

    r = rows[0]
    running  = _truthy(r.get("running"))
    disabled = _truthy(r.get("disabled"))

    # Stats de tráfego — `print stats=yes` é o jeito de pegar rx/tx-bits-per-second.
    # Se falhar (ex: versão antiga), só fica zero, não quebra o status.
    rx_bps = 0
    tx_bps = 0
    try:
        stats_rows = res.call("print", {"stats": "", "without-paging": ""})
        for s in stats_rows:
            if s.get("name") == name:
                rx_bps = int(s.get("rx-bits-per-second", 0) or 0)
                tx_bps = int(s.get("tx-bits-per-second", 0) or 0)
                # Se o print tem running e o get não pegou, usa daqui também
                if not running and "running" in s:
                    running = _truthy(s.get("running"))
                break
    except Exception as exc:
        logger.debug("print stats %s: %s", name, exc)

    return {
        "running":  running,
        "disabled": disabled,
        "rx_bps":   rx_bps,
        "tx_bps":   tx_bps,
        "comment":  r.get("comment") or "",
    }


def _parse_rtt(rtt_str) -> Optional[float]:
    """Converte string ou número de RTT do Mikrotik em milissegundos.
    Aceita: '5ms 240us', '1.2ms', '500us', '12.971', 12, b'5ms'."""
    if rtt_str is None:
        return None
    # Decodifica bytes se vier do API binário
    if isinstance(rtt_str, bytes):
        try: rtt_str = rtt_str.decode()
        except Exception: return None
    # Número puro (assume ms)
    if isinstance(rtt_str, (int, float)):
        return round(float(rtt_str), 2)
    s = str(rtt_str).strip().lower()
    if not s:
        return None
    import re
    # Procura tokens com unidade explícita
    total_ms = 0.0
    found_unit = False
    for m in re.finditer(r"([0-9]+(?:\.[0-9]+)?)\s*(ms|us|s)", s):
        found_unit = True
        val = float(m.group(1))
        unit = m.group(2)
        if unit == "s":   total_ms += val * 1000
        elif unit == "ms":total_ms += val
        elif unit == "us":total_ms += val / 1000
    if found_unit:
        return round(total_ms, 2) if total_ms else None
    # Sem unidade — tenta parse direto como número (assume ms)
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def _interface_ip(api, interface: str) -> Optional[str]:
    """Retorna o IP (sem máscara) da interface, ou None se não tiver."""
    try:
        rows = api.get_resource("/ip/address").get(interface=interface)
        for r in rows:
            addr = r.get("address") or ""
            ip = addr.split("/")[0].strip()
            if ip:
                return ip
    except Exception:
        pass
    return None


def _ping_attempt(api, target: str, params: dict) -> dict:
    """Faz uma tentativa de ping. Retorna sempre um dict com loss_pct."""
    try:
        results = list(api.get_resource("/").call("ping", params))
    except Exception as exc:
        return {"latency_ms": None, "loss_pct": 100.0,
                "erro": f"erro chamando /ping: {exc}", "results": []}
    if not results:
        return {"latency_ms": None, "loss_pct": 100.0,
                "erro": "sem resposta da API ping", "results": []}
    return {"latency_ms": None, "loss_pct": None, "erro": None, "results": results}


def _parse_ping_results(results: list) -> tuple:
    """Extrai (sent, received, avg_ms) de uma resposta de ping."""
    sent = 0
    received = 0
    avg_ms = None
    individual_times = []
    for r in results:
        try:
            sent     = int(r.get("sent", sent) or sent)
            received = int(r.get("received", received) or received)
        except (TypeError, ValueError):
            pass
        rtt_avg = r.get("avg-rtt")
        if rtt_avg:
            parsed = _parse_rtt(rtt_avg)
            if parsed is not None:
                avg_ms = parsed
        rtt_t = r.get("time")
        if rtt_t:
            parsed = _parse_rtt(rtt_t)
            if parsed is not None:
                individual_times.append(parsed)
    if sent == 0 and individual_times:
        sent = len(results) - 1 if len(results) > 1 else len(results)
        received = len(individual_times)
    if avg_ms is None and individual_times:
        avg_ms = round(sum(individual_times) / len(individual_times), 2)
    return sent, received, avg_ms


def _ping_via(api, target: str, interface: str) -> dict:
    """Pinga `target` saindo pela `interface` dada. Estratégia robusta:

    1ª tentativa: `src-address` = IP da interface (funciona em multi-WAN com IP público)
    2ª tentativa (se 1ª deu 100% loss): `interface=` (funciona em NAT/DHCP bridge)
    3ª tentativa (se 2ª também falhou): `src-address` + `interface` (belt + suspenders)

    Retorna sempre {latency_ms, loss_pct, erro}.
    """
    src_ip = _interface_ip(api, interface)
    base_params = {"address": target, "count": str(PING_COUNT)}

    tentativas = []
    if src_ip:
        tentativas.append({**base_params, "src-address": src_ip})
    tentativas.append({**base_params, "interface": interface})
    if src_ip:
        tentativas.append({**base_params, "src-address": src_ip, "interface": interface})

    last_err = None
    last_results = None
    for params in tentativas:
        attempt = _ping_attempt(api, target, params)
        if attempt["erro"]:
            last_err = attempt["erro"]
            continue
        sent, received, avg_ms = _parse_ping_results(attempt["results"])
        if sent > 0 and received > 0:
            # Sucesso parcial ou total
            loss_pct = round(100 * (sent - received) / sent, 1)
            return {"latency_ms": avg_ms, "loss_pct": loss_pct, "erro": None}
        last_results = attempt["results"]

    # Todas falharam — analisa o motivo pra mensagem útil
    socket_err = False
    if last_results:
        for r in last_results:
            status = (r.get("status") or "").lower()
            if "could not make socket" in status or "no route" in status:
                socket_err = True
                break

    if socket_err:
        # WAN só funciona via routing-mark (sem default route na main table).
        # Não é queda real — é configuração de mark-routing.
        return {
            "latency_ms": None,
            "loss_pct":   None,
            "erro":       "WAN com routing-mark (sem default route na main table) — link ativo mas não acessível via socket padrão",
            "via_mark":   True,
        }

    # Erro genérico
    sample = ""
    if last_results:
        try:
            r0 = last_results[0] if len(last_results) > 0 else {}
            sample = " sample=" + ", ".join(f"{k}={v}" for k, v in list(r0.items())[:6])
        except Exception:
            pass
    return {"latency_ms": None, "loss_pct": 100.0,
            "erro": (last_err or f"ping {len(last_results or [])} entries sem resposta") + sample}


def coletar_status(host: str, port: int, wans: list[dict]) -> dict:
    """Função principal — conecta na unidade e devolve snapshot completo.

    `wans` = [{"interface": "ether1", "label": "CENTURY 1GB"}, ...]

    Retorna dict com:
        ok (bool), erro (str|None), system (resource), wans (lista)
    """
    out = {"ok": False, "erro": None, "system": {}, "wans": []}
    if not PASS:
        out["erro"] = "MIKROTIK_PASS ausente no .env"
        return out

    conn = None
    try:
        conn = _conectar(host, port)
        api = conn.get_api()

        out["system"] = _resource(api)

        for w in wans:
            iface = w.get("interface") or "ether1"
            wan = {
                "label":     w.get("label") or iface,
                "interface": iface,
                "status":    "unknown",
                "latency_ms": None,
                "packet_loss": None,
                "rx_bps":    0,
                "tx_bps":    0,
            }
            try:
                # Estatísticas de tráfego (não-bloqueia status)
                try:
                    info = _interface_status(api, iface)
                    wan["rx_bps"]   = info["rx_bps"]
                    wan["tx_bps"]   = info["tx_bps"]
                    if info.get("disabled"):
                        wan["status"] = "disabled"
                        out["wans"].append(wan)
                        continue
                except Exception:
                    pass

                # Ping é o que decide se está realmente online.
                # Funciona em qualquer config: WAN com IP público, NAT, etc.
                ping = _ping_via(api, PING_TARGETS[0], iface)
                # Se falhar com o primeiro alvo (e não for por mark-routing),
                # tenta o segundo (1.1.1.1 ↔ 8.8.8.8)
                if (not ping.get("via_mark")
                        and (ping["loss_pct"] is None or ping["loss_pct"] >= 100)
                        and len(PING_TARGETS) > 1):
                    ping = _ping_via(api, PING_TARGETS[1], iface)

                wan["latency_ms"]  = ping["latency_ms"]
                wan["packet_loss"] = ping["loss_pct"]
                if ping.get("erro"):
                    wan["erro"] = ping["erro"]

                # WAN só acessível via routing-mark = link ativo mas não testável
                if ping.get("via_mark"):
                    wan["status"] = "via_mark"
                elif ping["loss_pct"] is None:
                    wan["status"] = "unknown"
                elif ping["loss_pct"] >= 100:
                    wan["status"] = "offline"
                elif ping["loss_pct"] >= 5 or (ping["latency_ms"] or 0) > 200:
                    wan["status"] = "degraded"
                else:
                    wan["status"] = "online"
            except Exception as exc:
                logger.warning("WAN %s falhou: %s", iface, exc)
                wan["status"] = "unknown"

            out["wans"].append(wan)

        out["ok"] = True
    except MikrotikError as exc:
        out["erro"] = str(exc)
    except Exception as exc:
        out["erro"] = f"erro inesperado: {exc}"
    finally:
        if conn:
            try: conn.disconnect()
            except Exception: pass
    return out


def coletar_unidades(unidades: list[dict]) -> list[dict]:
    """Coleta status de várias unidades em paralelo.
    `unidades` = lista de dicts (network_units rows)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _coletar(u):
        wans = [
            {"interface": u["wan1_interface"], "label": u["wan1_label"]},
            {"interface": u["wan2_interface"], "label": u["wan2_label"]},
        ]
        snap = coletar_status(u["host"], u.get("porta") or DEFAULT_PORT, wans)
        snap["unit_id"]  = u["id"]
        snap["nome"]     = u["nome"]
        snap["identity"] = u["identity"]
        snap["host"]     = u["host"]
        return snap

    out = []
    with ThreadPoolExecutor(max_workers=min(8, len(unidades) or 1)) as ex:
        futures = [ex.submit(_coletar, u) for u in unidades if u.get("ativo", 1)]
        for fut in as_completed(futures):
            try:
                out.append(fut.result())
            except Exception as exc:
                logger.error("Falha coletar: %s", exc)
    out.sort(key=lambda x: x.get("nome", ""))
    return out
