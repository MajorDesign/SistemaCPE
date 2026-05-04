"""
Cliente do Carbonio Community Edition (compatível com Zimbra SOAP API).

Endpoint usado: POST {CARBONIO_URL}/service/soap
Formato: JSON-over-SOAP (mais simples que XML, suportado nativamente
pelo Carbonio/Zimbra desde a versão 7).

Operações implementadas (FASE 1 — somente leitura):
    autenticar(email, senha)         → AuthRequest
    listar_eventos(token, ini, fim)  → SearchRequest (types=appointment)

A autenticação retorna um `authToken` válido por ~12h. Esse token é
guardado criptografado no banco (coluna `users.carbonio_token`) e
usado nos requests subsequentes via header `<context>` SOAP.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

CARBONIO_URL = os.getenv("CARBONIO_URL", "https://webmail.cpetecnologia.com.br").rstrip("/")
SOAP_ENDPOINT = f"{CARBONIO_URL}/service/soap"
HTTP_TIMEOUT  = 20  # segundos

# verify=True é o ideal. Se o servidor tiver certificado self-signed,
# sobrescreva via env CARBONIO_VERIFY_TLS=false (não recomendado para produção).
VERIFY_TLS = os.getenv("CARBONIO_VERIFY_TLS", "true").lower() != "false"


class CarbonioError(Exception):
    """Erro de negócio do Carbonio (credenciais inválidas, conta bloqueada, etc)."""


class CarbonioOfflineError(Exception):
    """O servidor Carbonio está inacessível (rede/firewall/DNS)."""


def _post_soap(payload: dict) -> dict:
    """POST JSON-over-SOAP. Retorna o body parseado ou levanta exceção."""
    try:
        r = requests.post(
            SOAP_ENDPOINT,
            json=payload,
            timeout=HTTP_TIMEOUT,
            verify=VERIFY_TLS,
            headers={"Content-Type": "application/soap+json"},
        )
    except requests.exceptions.ConnectionError as err:
        raise CarbonioOfflineError(f"Não foi possível conectar ao Carbonio: {err}")
    except requests.exceptions.Timeout:
        raise CarbonioOfflineError("Tempo esgotado conectando ao Carbonio.")

    try:
        data = r.json()
    except ValueError:
        raise CarbonioError(f"Resposta inválida do Carbonio (HTTP {r.status_code}): {r.text[:200]}")

    body = data.get("Body", {})

    # Trata SOAP Fault (erros de negócio do Carbonio)
    if "Fault" in body:
        fault = body["Fault"]
        reason = (
            fault.get("Reason", {}).get("Text")
            or fault.get("Detail", {}).get("Error", {}).get("Code")
            or "Erro desconhecido"
        )
        code = fault.get("Detail", {}).get("Error", {}).get("Code", "")
        # account.AUTH_FAILED, account.NO_SUCH_ACCOUNT, etc
        raise CarbonioError(f"{reason} ({code})" if code else reason)

    return body


def autenticar(email: str, senha: str) -> dict:
    """
    Autentica no Carbonio e retorna { token, lifetime_segundos, email }.
    Levanta CarbonioError em credenciais inválidas / CarbonioOfflineError em rede.
    """
    payload = {
        "Header": {"context": {"_jsns": "urn:zimbra"}},
        "Body": {
            "AuthRequest": {
                "_jsns":    "urn:zimbraAccount",
                "account":  {"by": "name", "_content": email},
                "password": {"_content": senha},
            }
        },
    }
    body = _post_soap(payload)
    auth = body.get("AuthResponse", {})

    # authToken vem como lista [{"_content": "..."}]
    token_list = auth.get("authToken")
    if not token_list:
        raise CarbonioError("Servidor não devolveu authToken.")
    token = (token_list[0] or {}).get("_content")
    if not token:
        raise CarbonioError("authToken vazio.")

    lifetime_ms = auth.get("lifetime", 12 * 3600 * 1000)
    return {
        "token":              token,
        "lifetime_segundos":  int(lifetime_ms // 1000),
        "email":              email,
    }


def listar_eventos(token: str, inicio_ms: int, fim_ms: int) -> list[dict]:
    """
    Lista eventos da agenda do usuário no intervalo dado (epoch ms).
    Retorna uma lista normalizada com:
      { id, titulo, local, inicio (ISO), fim (ISO), all_day, status,
        organizador_email, organizador_nome }

    Inclui automaticamente reuniões em que o usuário foi convidado
    (mesmo que organizadas por terceiros) — comportamento nativo
    do Carbonio na pasta Calendar.
    """
    payload = {
        "Header": {"context": {"_jsns": "urn:zimbra", "authToken": token}},
        "Body": {
            "SearchRequest": {
                "_jsns":              "urn:zimbraMail",
                "types":              "appointment",
                "calExpandInstStart": inicio_ms,
                "calExpandInstEnd":   fim_ms,
                "query":              "in:Calendar",
                "limit":              500,
                "offset":             0,
            }
        },
    }
    body = _post_soap(payload)
    resp = body.get("SearchResponse", {}) or {}
    appts = resp.get("appt") or []

    eventos = []
    for a in appts:
        nome   = a.get("name") or "(Sem título)"
        local  = a.get("loc") or None
        status = a.get("status") or "TENT"  # CONF, TENT, CANC
        all_day = bool(a.get("allDay", False))

        organizador = a.get("or") or {}
        org_email = organizador.get("a") or organizador.get("d")
        org_nome  = organizador.get("d") or organizador.get("a")

        # Cada appt pode ter várias instâncias (recorrência expandida)
        instancias = a.get("inst") or [{"s": a.get("s"), "dur": a.get("dur")}]
        for inst in instancias:
            ini = inst.get("s") or inst.get("ridZ")  # ms
            dur = inst.get("dur")  # ms
            if not ini:
                continue
            # Se não tem duração explícita, assume 1h
            fim = ini + (dur if dur else 3600000)
            eventos.append({
                "id":                a.get("id"),
                "uid":               a.get("uid"),
                "titulo":            nome,
                "local":             local,
                "inicio_ms":         int(ini),
                "fim_ms":            int(fim),
                "all_day":           all_day,
                "status":            _mapear_status(status),
                "organizador_email": org_email,
                "organizador_nome":  org_nome,
                "fonte":             "carbonio",
            })
    return eventos


def _mapear_status(carbonio_status: str) -> str:
    """Mapeia status do Carbonio para nomes amigáveis."""
    return {
        "CONF": "confirmado",
        "TENT": "tentativo",
        "CANC": "cancelado",
    }.get(carbonio_status, carbonio_status.lower())


def _formatar_data_zimbra(dt_iso: str) -> str:
    """Converte ISO 8601 para o formato esperado pelo Carbonio (UTC).
    Ex.: '2026-05-05T14:00:00-03:00' → '20260505T170000Z'"""
    from datetime import datetime, timezone
    dt = datetime.fromisoformat(dt_iso.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        # Sem timezone — assume timezone local do servidor
        dt = dt.astimezone()
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime("%Y%m%dT%H%M%SZ")


def _mapear_ptst(ptst: str) -> str:
    """Mapeia ParticipantStatus do Carbonio para nome amigável."""
    return {
        "AC": "aceito",
        "DE": "recusado",
        "TE": "tentativo",
        "NE": "pendente",
        "DG": "delegado",
    }.get((ptst or "").upper(), "pendente")


def obter_detalhes_evento(token: str, evento_id: str) -> dict:
    """
    Busca os detalhes completos de um evento (inclui lista de convidados
    e status de resposta de cada um).

    Retorna:
        {
          id, uid, titulo, descricao, local, all_day, status,
          inicio_ms, fim_ms,
          organizador: {email, nome},
          convidados: [{email, nome, status, role, rsvp}]
        }
    """
    payload = {
        "Header": {"context": {"_jsns": "urn:zimbra", "authToken": token}},
        "Body": {
            "GetAppointmentRequest": {
                "_jsns":  "urn:zimbraMail",
                "id":     str(evento_id),
                "includeContent": "1",
            }
        },
    }
    body = _post_soap(payload)
    resp = body.get("GetAppointmentResponse", {}) or {}
    appts = resp.get("appt") or []
    if not appts:
        raise CarbonioError("Evento não encontrado")

    a = appts[0]
    inv_list = a.get("inv") or []
    if not inv_list:
        raise CarbonioError("Evento sem detalhes (inv vazio)")
    inv = inv_list[0]
    comps = inv.get("comp") or []
    if not comps:
        raise CarbonioError("Evento sem componente")
    comp = comps[0]

    # Extrai datas (em ms desde epoch — Carbonio retorna no formato YYYYMMDDTHHMMSSZ)
    def _parse_dt(dt_obj):
        if not dt_obj: return None
        d = dt_obj[0] if isinstance(dt_obj, list) else dt_obj
        if isinstance(d, dict):
            from datetime import datetime
            v = d.get("d") or ""
            try:
                if v.endswith("Z"):
                    return int(datetime.strptime(v, "%Y%m%dT%H%M%SZ").timestamp() * 1000)
                return int(datetime.strptime(v[:15], "%Y%m%dT%H%M%S").timestamp() * 1000)
            except Exception:
                return None
        return None

    inicio_ms = _parse_dt(comp.get("s")) or 0
    fim_ms    = _parse_dt(comp.get("e")) or (inicio_ms + 3600000)

    # Convidados (attendees)
    convidados = []
    for at in (comp.get("at") or []):
        convidados.append({
            "email":  at.get("a") or "",
            "nome":   at.get("d") or at.get("a") or "",
            "status": _mapear_ptst(at.get("ptst")),
            "role":   "obrigatório" if (at.get("role") or "REQ").upper() == "REQ" else "opcional",
            "rsvp":   bool(at.get("rsvp")),
        })

    organizador_obj = comp.get("or") or {}
    organizador = {
        "email": organizador_obj.get("a") or "",
        "nome":  organizador_obj.get("d") or organizador_obj.get("a") or "",
    }

    desc_list = comp.get("desc") or []
    descricao = ""
    if desc_list and isinstance(desc_list, list):
        descricao = (desc_list[0] or {}).get("_content", "")

    return {
        "id":           a.get("id"),
        "uid":          a.get("uid"),
        "titulo":       comp.get("name") or "(Sem título)",
        "descricao":    descricao,
        "local":        comp.get("loc"),
        "all_day":      bool(comp.get("allDay")),
        "status":       _mapear_status(comp.get("status") or a.get("status") or "TENT"),
        "inicio_ms":    inicio_ms,
        "fim_ms":       fim_ms,
        "organizador":  organizador,
        "convidados":   convidados,
    }


def reenviar_convite(token: str, evento_id: str, destinatarios: list[str]) -> dict:
    """
    Reenvia o convite (com anexo iCalendar) para os destinatários informados.
    Útil quando algum convidado ainda não respondeu.

    Usa ForwardAppointmentRequest do Carbonio (aceita o ID do item de
    calendário diretamente — ao contrário de ForwardAppointmentInviteRequest
    que exige o ID da mensagem do convite original).
    """
    if not destinatarios:
        raise ValueError("Lista de destinatários vazia")

    payload = {
        "Header": {"context": {"_jsns": "urn:zimbra", "authToken": token}},
        "Body": {
            "ForwardAppointmentRequest": {
                "_jsns": "urn:zimbraMail",
                "id":    str(evento_id),
                "m": {
                    "e":  [{"a": d, "t": "t"} for d in destinatarios],
                    "su": "Lembrete — confirme sua presença",
                    "mp": [{
                        "ct": "text/plain",
                        "content": {"_content":
                            "Olá! Reenviando o convite desta reunião — por favor, "
                            "confirme sua presença respondendo a este email."},
                    }],
                },
            }
        },
    }
    _post_soap(payload)
    return {"ok": True, "destinatarios": destinatarios}


def criar_evento(
    token: str,
    organizador_email: str,
    titulo: str,
    inicio_iso: str,
    fim_iso: str,
    local: Optional[str] = None,
    descricao: Optional[str] = None,
    convidados: Optional[list[str]] = None,
    all_day: bool = False,
    pasta_calendario_id: str = "10",  # 10 = pasta padrão "Calendar"
) -> dict:
    """
    Cria um evento (compromisso) na agenda do usuário no Carbonio.
    Carbonio dispara automaticamente os convites por email para os
    endereços passados em `convidados`.

    Retorna { id, uid, ok }.
    """
    convidados = [c for c in (convidados or []) if c and "@" in c]

    inicio_z = _formatar_data_zimbra(inicio_iso)
    fim_z    = _formatar_data_zimbra(fim_iso)

    # Componente principal do convite
    comp = {
        "name":   titulo,
        "fb":     "B",         # busy
        "transp": "O",         # opaque
        "allDay": "1" if all_day else "0",
        "status": "CONF",      # confirmado pelo organizador
        "class":  "PUB",       # público
        "draft":  "0",
        "s":      [{"d": inicio_z}],
        "e":      [{"d": fim_z}],
        "or":     {"a": organizador_email, "d": organizador_email},
    }
    if local:
        comp["loc"] = local
    if descricao:
        comp["desc"] = [{"_content": descricao}]
    if convidados:
        comp["at"] = [
            {"a": c, "role": "REQ", "ptst": "NE", "rsvp": "1", "d": c}
            for c in convidados
        ]

    # Mensagem de email (envelope) — Carbonio usa para enviar o convite
    mp = [{"ct": "text/plain", "content": {"_content": descricao or titulo}}]

    body_msg = {
        "l":   pasta_calendario_id,
        "su":  titulo,
        "inv": {"comp": [comp]},
        "mp":  mp,
    }
    if convidados:
        body_msg["e"] = [
            {"a": organizador_email, "t": "f"},  # f = from
        ] + [{"a": c, "t": "t"} for c in convidados]

    payload = {
        "Header": {"context": {"_jsns": "urn:zimbra", "authToken": token}},
        "Body": {
            "CreateAppointmentRequest": {
                "_jsns": "urn:zimbraMail",
                "m":     body_msg,
            }
        },
    }
    body = _post_soap(payload)
    resp = body.get("CreateAppointmentResponse", {}) or {}

    return {
        "ok":         True,
        "id":         resp.get("apptId") or resp.get("calItemId"),
        "uid":        resp.get("uid"),
        "invId":      resp.get("invId"),
    }
