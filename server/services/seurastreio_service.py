"""
Serviço de rastreamento via seurastreio.com.br

Endpoint público:
    GET https://seurastreio.com.br/api/public/rastreio/{codigo}
    Header: Authorization: Bearer <SEURASTREIO_API_KEY>

Plano gratuito: 10 requisições/minuto por IP, retorna apenas o evento
mais recente (`eventoMaisRecente`). Plano pago retorna `historico`
(todos os eventos, mais recente primeiro) e `previsaoEntrega`.

Retorno padronizado:
    ok=True:  { ok, codigo, status, descricao, data, local, detalhe,
                eventos[], previsaoEntrega, linkDetalhes }
    ok=False: { ok, erro, offline (bool) }
"""

from __future__ import annotations

import logging
import os
import re
from typing import Optional

import requests

logger = logging.getLogger(__name__)

API_KEY  = os.getenv("SEURASTREIO_API_KEY", "")
BASE_URL = "https://seurastreio.com.br/api/public/rastreio"
HTTP_TIMEOUT = 12  # segundos

# Códigos aceitos: Correios (AA123456789BR) ou Total Express (TXAQ187563341tx)
_CODIGO_CORREIOS = re.compile(r"^[A-Z]{2}\d{9}[A-Z]{2}$", re.I)
_CODIGO_TX       = re.compile(r"^TX[A-Z0-9]+$", re.I)


def validar_codigo(codigo: str) -> bool:
    """Aceita formatos Correios ou Total Express."""
    if not codigo:
        return False
    c = codigo.strip()
    return bool(_CODIGO_CORREIOS.match(c) or _CODIGO_TX.match(c))


def _e_erro_de_rede(err: Exception) -> bool:
    if isinstance(err, requests.exceptions.ConnectionError):
        msg = str(err).lower()
        return any(s in msg for s in (
            "getaddrinfo failed", "name or service not known",
            "nameresolutionerror", "max retries exceeded",
            "connection refused", "no route to host", "timed out",
        ))
    if isinstance(err, requests.exceptions.Timeout):
        return True
    return False


def _normalizar_evento(ev: dict) -> dict:
    """Normaliza um evento para o formato usado pelo frontend."""
    return {
        "codigo":    ev.get("codigo")    or "",
        "descricao": ev.get("descricao") or "",
        "detalhe":   ev.get("detalhe")   or "",
        "data":      ev.get("data")      or "",
        "local":     ev.get("local")     or "",
    }


def rastrear(codigo: str) -> dict:
    """Consulta o status do objeto via seurastreio.com.br."""
    if not codigo:
        return {"ok": False, "erro": "Código vazio"}

    codigo = codigo.strip().upper()
    if not validar_codigo(codigo):
        return {
            "ok": False,
            "erro": "Formato inválido (Correios: AA123456789BR ou Total Express: TX...).",
        }

    if not API_KEY:
        return {
            "ok": False,
            "erro": "Chave SEURASTREIO_API_KEY não configurada no .env do servidor.",
        }

    headers = {"Authorization": f"Bearer {API_KEY}"}
    url = f"{BASE_URL}/{codigo}"

    try:
        r = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)

        if r.status_code == 401:
            try:
                body = r.json()
            except ValueError:
                body = {}
            return {
                "ok": False, "offline": False,
                "erro": body.get("message") or "Chave de API inválida ou expirada.",
            }
        if r.status_code == 429:
            return {
                "ok": False, "offline": False,
                "erro": "Limite de consultas atingido (10/min). Tente novamente em instantes.",
            }
        if r.status_code == 404:
            return {
                "ok": True, "codigo": codigo,
                "status": "not_found",
                "descricao": "Objeto não encontrado",
                "data": None, "local": None, "detalhe": None,
                "eventos": [], "linkDetalhes": None, "previsaoEntrega": None,
            }
        if r.status_code != 200:
            return {
                "ok": False, "offline": False,
                "erro": f"Erro HTTP {r.status_code}: {r.text[:120]}",
            }

        try:
            data = r.json()
        except ValueError:
            return {"ok": False, "offline": False, "erro": "Resposta inválida da API."}

        if not data.get("success"):
            return {
                "ok": False, "offline": False,
                "erro": data.get("message") or "API retornou status sem sucesso.",
            }

        evento = data.get("eventoMaisRecente") or {}
        historico = data.get("historico") or []  # plano pago

        eventos_norm = [_normalizar_evento(ev) for ev in historico]
        if not eventos_norm and evento:
            eventos_norm = [_normalizar_evento(evento)]

        return {
            "ok": True,
            "codigo":    data.get("codigo") or codigo,
            "status":    data.get("status") or "found",
            "descricao": evento.get("descricao") or "",
            "data":      evento.get("data") or None,
            "local":     evento.get("local") or None,
            "detalhe":   evento.get("detalhe") or None,
            "eventos":   eventos_norm,
            "previsaoEntrega": data.get("previsaoEntrega") or None,
            "linkDetalhes":    data.get("linkDetalhesCompletos") or None,
            "message":         data.get("message") or "",
        }

    except requests.RequestException as err:
        offline = _e_erro_de_rede(err)
        logger.warning(f"[SEURASTREIO] {'OFFLINE' if offline else 'erro'}: {err}")
        if offline:
            return {
                "ok": False, "offline": True,
                "erro": ("O servidor não conseguiu acessar a API de rastreio. "
                         "Verifique conexão/firewall."),
            }
        return {"ok": False, "offline": False, "erro": f"Falha: {err}"}
    except Exception as err:
        logger.error(f"[SEURASTREIO] erro inesperado: {err}")
        return {"ok": False, "offline": False, "erro": f"Erro inesperado: {err}"}
