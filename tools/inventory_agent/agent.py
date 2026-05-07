#!/usr/bin/env python3
"""
CPE Control — Agente de Inventário T.I.  v1.1.0
================================================
Coleta informações do dispositivo e envia para o servidor CPE Control.

Uso:
    python agent.py              → envia uma vez e sai
    python agent.py --loop       → envia a cada 5 minutos (serviço)
    python agent.py --test       → imprime dados coletados sem enviar
    python agent.py --url URL    → sobrescreve o servidor de destino

Requisitos:
    pip install -r requirements.txt   (psutil e requests)
    PowerShell já vem no Windows — nenhuma dependência adicional

NOTAS:
  - Localização por IP é imprecisa (mostra cidade do provedor/ISP, não do
    usuário). Configure LOCATION_ESTADO e LOCATION_CIDADE abaixo.
  - Dados de hardware (marca, modelo, série) usam PowerShell + WMI.
"""

import argparse
import json
import logging
import os
import platform
import socket
import subprocess
import sys
import time

# ─── CONFIGURAÇÃO (editar antes de distribuir) ────────────────────────────────
API_URL   = "http://127.0.0.1:8000/api/inventario/agent/report"
AGENT_KEY = "cpe-inv-2026"
VERSAO    = "1.1.0"
INTERVAL  = 300   # segundos entre envios no modo --loop
TIMEOUT   = 15    # timeout HTTP em segundos

# Localização física do computador.
# Preencha aqui para evitar erro de geolocalização por IP.
# Se deixar vazio, tenta detectar automaticamente via ipinfo.io
# (pode mostrar cidade errada por causa do roteamento do provedor).
LOCATION_ESTADO = ""   # Ex: "Minas Gerais"
LOCATION_CIDADE = ""   # Ex: "Belo Horizonte"
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AGENTE-CPE] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("cpe_agent.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

try:
    import psutil
except ImportError:
    log.error("psutil não instalado. Execute: pip install psutil")
    sys.exit(1)

try:
    import requests
except ImportError:
    log.error("requests não instalado. Execute: pip install requests")
    sys.exit(1)


# ─── PowerShell helper (resolve encoding do WMIC) ─────────────────────────────

def _ps(cmd: str) -> str:
    """
    Executa um comando PowerShell e retorna a saída como string.
    Usa PowerShell em vez de WMIC porque o WMIC emite UTF-16 LE,
    que o Python lê incorretamente como UTF-8 e produz lixo.
    """
    if platform.system() != "Windows":
        return ""
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-OutputFormat", "Text",
                "-Command", cmd,
            ],
            capture_output=True,
            timeout=10,
        )
        # PowerShell pode emitir UTF-8 com BOM — utf-8-sig remove o BOM
        return result.stdout.decode("utf-8-sig", errors="ignore").strip()
    except Exception as exc:
        log.debug(f"[PS] Falha ao executar '{cmd[:60]}': {exc}")
        return ""


# ─── Coleta de hardware via PowerShell/WMI ───────────────────────────────────

def get_serial_number() -> str:
    if platform.system() == "Windows":
        v = _ps("(Get-WmiObject Win32_BIOS).SerialNumber")
        return v if v and v not in ("", "None", "Default string", "To Be Filled By O.E.M.") else ""
    try:
        return subprocess.check_output(
            ["dmidecode", "-s", "system-serial-number"],
            stderr=subprocess.DEVNULL, timeout=5, encoding="utf-8",
        ).strip()
    except Exception:
        return ""


def get_manufacturer_model() -> tuple[str, str]:
    if platform.system() == "Windows":
        marca  = _ps("(Get-WmiObject Win32_ComputerSystem).Manufacturer")
        modelo = _ps("(Get-WmiObject Win32_ComputerSystem).Model")
        # Sanitiza valores genéricos que alguns fabricantes colocam
        for placeholder in ("System manufacturer", "System Product Name",
                            "To Be Filled By O.E.M.", "Default string", "None"):
            if marca  == placeholder: marca  = ""
            if modelo == placeholder: modelo = ""
        return marca, modelo
    try:
        marca  = subprocess.check_output(
            ["dmidecode", "-s", "system-manufacturer"],
            stderr=subprocess.DEVNULL, timeout=5, encoding="utf-8",
        ).strip()
        modelo = subprocess.check_output(
            ["dmidecode", "-s", "system-product-name"],
            stderr=subprocess.DEVNULL, timeout=5, encoding="utf-8",
        ).strip()
        return marca, modelo
    except Exception:
        return "", ""


def get_cpu_modelo() -> str:
    """CPU name via PowerShell (mais completo que platform.processor())."""
    if platform.system() == "Windows":
        v = _ps("(Get-WmiObject Win32_Processor).Name")
        if v:
            return v
    return platform.processor() or "Desconhecido"


# ─── Tipo do dispositivo ──────────────────────────────────────────────────────

def is_notebook() -> bool:
    try:
        return psutil.sensors_battery() is not None
    except Exception:
        return False


def get_tipo() -> str:
    ver = platform.version().lower()
    if "server" in ver or "server" in platform.release().lower():
        return "servidor"
    return "notebook" if is_notebook() else "desktop"


# ─── Hostname ─────────────────────────────────────────────────────────────────

def get_hostname() -> str:
    """
    Usa COMPUTERNAME no Windows (sempre o nome curto correto).
    socket.gethostname() pode retornar o FQDN em ambientes com domínio.
    """
    if platform.system() == "Windows":
        nome = os.environ.get("COMPUTERNAME", "").strip()
        if nome:
            return nome
    return socket.gethostname()


# ─── Arquitetura ──────────────────────────────────────────────────────────────

def get_arquitetura() -> str:
    """
    platform.machine() retorna a arquitetura do Python instalado,
    não necessariamente do hardware (Python 32-bit em Windows 64-bit
    retorna 'x86'). PROCESSOR_ARCHITECTURE reflete o hardware real.
    """
    if platform.system() == "Windows":
        arch = os.environ.get("PROCESSOR_ARCHITECTURE", "").strip()
        # Mapa de valores do Windows para rótulos legíveis
        return {"AMD64": "x86_64 (64-bit)", "x86": "x86 (32-bit)",
                "ARM64": "ARM64"}.get(arch, arch or platform.machine())
    return platform.machine()


# ─── Uptime ───────────────────────────────────────────────────────────────────

def get_uptime_dias() -> int:
    try:
        return int((time.time() - psutil.boot_time()) / 86400)
    except Exception:
        return 0


# ─── Memória ──────────────────────────────────────────────────────────────────

def get_memoria() -> dict:
    m = psutil.virtual_memory()
    return {
        "memoria_total_gb": round(m.total / 1073741824, 2),
        "memoria_uso_pct":  round(m.percent, 2),
    }


# ─── Disco ────────────────────────────────────────────────────────────────────

def get_disco() -> dict:
    discos, total_b, livre_b = [], 0, 0
    for part in psutil.disk_partitions(all=False):
        try:
            u = psutil.disk_usage(part.mountpoint)
            discos.append({
                "mountpoint": part.mountpoint,
                "fstype":     part.fstype,
                "total_gb":   round(u.total / 1073741824, 2),
                "livre_gb":   round(u.free  / 1073741824, 2),
                "livre_pct":  round(u.free / u.total * 100, 2) if u.total else 0,
            })
            total_b += u.total
            livre_b += u.free
        except (PermissionError, OSError):
            pass
    return {
        "disco_total_gb":  round(total_b / 1073741824, 2),
        "disco_livre_gb":  round(livre_b / 1073741824, 2),
        "disco_livre_pct": round(livre_b / total_b * 100, 2) if total_b else 0,
        "discos_json":     discos,
    }


# ─── CPU ──────────────────────────────────────────────────────────────────────

def get_cpu() -> dict:
    return {
        "cpu_modelo":  get_cpu_modelo(),
        "cpu_nucleos": psutil.cpu_count(logical=True),
        "cpu_uso_pct": round(psutil.cpu_percent(interval=1), 2),
    }


# ─── IP interno ───────────────────────────────────────────────────────────────

def get_ip_interno() -> str:
    """
    Método UDP: abre socket para 8.8.8.8 (não envia dados) e lê o IP
    da interface de saída padrão. Funciona sem precisar de DNS.
    Atenção: se houver VPN ativa, pode retornar o IP da VPN.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    # Fallback: resolve o próprio hostname
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return ""


# ─── Localização ──────────────────────────────────────────────────────────────

def get_geo() -> dict:
    """
    Se LOCATION_ESTADO/CIDADE estiverem configurados, usa esses valores.
    Caso contrário tenta ipinfo.io — mas atenção: o resultado reflete a
    localização do provedor (ISP), não do computador fisicamente.
    Ex: provedor de BH com POP em SP → retorna São Paulo.
    """
    if LOCATION_ESTADO or LOCATION_CIDADE:
        log.debug("[GEO] Usando localização manual configurada")
        # Ainda tenta pegar o IP externo
        ip_ext = ""
        try:
            r = requests.get("https://api.ipify.org?format=json", timeout=5)
            if r.ok:
                ip_ext = r.json().get("ip", "")
        except Exception:
            pass
        return {
            "ip_externo": ip_ext,
            "estado_br":  LOCATION_ESTADO,
            "cidade":     LOCATION_CIDADE,
        }

    try:
        r = requests.get("https://ipinfo.io/json", timeout=6)
        if r.ok:
            d = r.json()
            return {
                "ip_externo": d.get("ip", ""),
                "estado_br":  d.get("region", ""),
                "cidade":     d.get("city", ""),
            }
    except Exception:
        pass
    return {"ip_externo": "", "estado_br": "", "cidade": ""}


# ─── Usuário logado ───────────────────────────────────────────────────────────

def get_usuario() -> str:
    return (
        os.environ.get("USERNAME")
        or os.environ.get("USER")
        or ""
    )


# ─── Coleta completa ──────────────────────────────────────────────────────────

def coletar() -> dict:
    log.info("Coletando dados do dispositivo...")
    marca, modelo = get_manufacturer_model()
    geo  = get_geo()
    mem  = get_memoria()
    disk = get_disco()
    cpu  = get_cpu()

    return {
        "hostname":            get_hostname(),
        "usuario_logado":      get_usuario(),
        "ip_interno":          get_ip_interno(),
        "ip_externo":          geo["ip_externo"],
        "tipo":                get_tipo(),
        "marca":               marca,
        "modelo":              modelo,
        "numero_serie":        get_serial_number(),
        "sistema_operacional": f"{platform.system()} {platform.release()}",
        "versao_os":           platform.version(),
        "arquitetura":         get_arquitetura(),
        **mem,
        **disk,
        **cpu,
        "dias_ligado":         get_uptime_dias(),
        "estado_br":           geo["estado_br"],
        "cidade":              geo["cidade"],
        "versao_agente":       VERSAO,
    }


# ─── Envio ────────────────────────────────────────────────────────────────────

def enviar(dados: dict, url: str) -> bool:
    try:
        r = requests.post(
            url,
            json=dados,
            headers={
                "X-Agent-Key":  AGENT_KEY,
                "Content-Type": "application/json",
            },
            timeout=TIMEOUT,
        )
        if r.ok:
            log.info(f"✅ Enviado — hostname={dados['hostname']} | ação={r.json().get('action','?')}")
            return True
        log.error(f"❌ Servidor retornou {r.status_code}: {r.text[:200]}")
        return False
    except requests.exceptions.ConnectionError:
        log.error(f"❌ Sem conexão com {url}")
        return False
    except Exception as exc:
        log.error(f"❌ Erro ao enviar: {exc}")
        return False


# ─── Entry-point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="CPE Control — Agente de Inventário T.I. v" + VERSAO
    )
    parser.add_argument("--loop", action="store_true",
                        help=f"Executa em loop a cada {INTERVAL}s")
    parser.add_argument("--test", action="store_true",
                        help="Exibe dados coletados sem enviar")
    parser.add_argument("--url", default=API_URL,
                        help="URL do servidor (sobrescreve padrão)")
    args = parser.parse_args()

    log.info(f"CPE Control Agent v{VERSAO} | destino: {args.url}")

    if args.test:
        dados = coletar()
        print("\n" + "=" * 60)
        print("  DADOS COLETADOS (modo teste — nada foi enviado)")
        print("=" * 60)
        for k, v in dados.items():
            if k == "discos_json":
                print(f"  {k:25s}: {json.dumps(v, ensure_ascii=False)}")
            else:
                print(f"  {k:25s}: {v}")
        print("=" * 60 + "\n")
        return

    if args.loop:
        log.info(f"Modo loop — intervalo: {INTERVAL}s")
        while True:
            try:
                enviar(coletar(), args.url)
            except Exception as exc:
                log.error(f"Erro inesperado: {exc}")
            time.sleep(INTERVAL)
    else:
        enviar(coletar(), args.url)


if __name__ == "__main__":
    main()
