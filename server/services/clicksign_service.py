"""
Clicksign — wrapper das chamadas necessárias para o fluxo "Termo de Responsabilidade".

Fluxo coberto (4 chamadas Clicksign):
  1. POST /api/v1/documents          → cria o documento (PDF em base64)
  2. POST /api/v1/signers            → cria o signatário (nome, cpf, email)
  3. POST /api/v1/lists              → vincula o signatário ao documento
  4. POST /api/v1/notifications      → dispara o e-mail para o signatário

Documentação: https://developers.clicksign.com/docs

Variáveis de ambiente esperadas (em server/.env):
  CLICKSIGN_TOKEN  — Access Token gerado no painel da Clicksign
  CLICKSIGN_ENV    — "sandbox" (default) ou "production"
"""

import os
import base64
import requests
from typing import Dict, Any


SANDBOX_HOST    = "https://sandbox.clicksign.com"
PRODUCTION_HOST = "https://app.clicksign.com"
TIMEOUT         = 30


class ClicksignError(Exception):
    """Erro retornado pela API da Clicksign (com mensagem amigável já formatada)."""


def _host() -> str:
    env = (os.getenv("CLICKSIGN_ENV") or "sandbox").lower().strip()
    return PRODUCTION_HOST if env == "production" else SANDBOX_HOST


def _token() -> str:
    tk = (os.getenv("CLICKSIGN_TOKEN") or "").strip()
    if not tk or tk == "COLE_SEU_TOKEN_AQUI":
        raise ClicksignError(
            "Token Clicksign não configurado. "
            "Edite o arquivo server/.env e preencha CLICKSIGN_TOKEN."
        )
    return tk


def _post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST genérico autenticado. Converte erros HTTP em ClicksignError com mensagem clara."""
    url = f"{_host()}{path}?access_token={_token()}"
    try:
        r = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=TIMEOUT,
        )
    except requests.exceptions.ConnectionError:
        raise ClicksignError("Sem conexão com a Clicksign. Verifique a internet do servidor.")
    except requests.exceptions.Timeout:
        raise ClicksignError("Tempo esgotado ao chamar a Clicksign (servidor lento ou fora do ar).")

    if r.status_code in (200, 201, 202, 204):
        try:
            return r.json() or {}
        except Exception:
            return {}

    # Tenta extrair mensagem de erro da Clicksign
    try:
        data = r.json()
    except Exception:
        data = {}

    detalhe = ""
    if isinstance(data, dict):
        if isinstance(data.get("errors"), list) and data["errors"]:
            detalhe = "; ".join(str(e) for e in data["errors"])
        elif data.get("message"):
            detalhe = str(data["message"])
        elif data.get("error"):
            detalhe = str(data["error"])

    if r.status_code == 401:
        raise ClicksignError("Token Clicksign inválido ou expirado. Gere um novo no painel.")
    if r.status_code == 422:
        raise ClicksignError(f"Dados inválidos para a Clicksign: {detalhe or 'verifique nome/cpf/email'}")
    if r.status_code == 429:
        raise ClicksignError("Limite de requisições da Clicksign atingido. Aguarde alguns segundos.")
    if r.status_code >= 500:
        raise ClicksignError("Clicksign está fora do ar (erro 5xx). Tente novamente em alguns minutos.")

    raise ClicksignError(f"Erro Clicksign ({r.status_code}): {detalhe or r.text[:200]}")


# =========================================
# 1) CRIAR DOCUMENTO
# =========================================
def criar_documento(pdf_bytes: bytes, filename: str) -> str:
    """Sobe o PDF para a Clicksign. Retorna o document_key."""
    if not filename.lower().endswith(".pdf"):
        filename = filename + ".pdf"

    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
    content_data_uri = f"data:application/pdf;base64,{pdf_b64}"

    payload = {
        "document": {
            "path": f"/{filename}",
            "content_base64": content_data_uri,
            "deadline_at": None,         # sem prazo limite
            "auto_close": True,          # fecha automaticamente quando todos assinarem
            "locale": "pt-BR",
        }
    }
    data = _post("/api/v1/documents", payload)
    key = (data.get("document") or {}).get("key")
    if not key:
        raise ClicksignError("Clicksign retornou OK mas não devolveu o document key.")
    return key


# =========================================
# 2) CRIAR SIGNATÁRIO
# =========================================
def criar_signatario(nome: str, email: str, cpf: str) -> str:
    """Cria o signatário. Retorna o signer_key.

    Autenticação por clique no e-mail (auths=['email']).
    """
    cpf_digits = "".join(c for c in (cpf or "") if c.isdigit())

    payload = {
        "signer": {
            "name":            nome.strip(),
            "email":           email.strip().lower(),
            "documentation":   cpf_digits,
            "has_documentation": True,
            "auths":           ["email"],
            "delivery":        "email",
            # birthday é opcional para auth por email
        }
    }
    data = _post("/api/v1/signers", payload)
    key = (data.get("signer") or {}).get("key")
    if not key:
        raise ClicksignError("Clicksign retornou OK mas não devolveu o signer key.")
    return key


# =========================================
# 3) VINCULAR SIGNATÁRIO AO DOCUMENTO
# =========================================
def vincular_signatario(document_key: str, signer_key: str) -> str:
    """Cria a 'list' que liga signer ao documento. Retorna o request_signature_key
    necessário para disparar a notificação por e-mail."""
    payload = {
        "list": {
            "document_key": document_key,
            "signer_key":   signer_key,
            "sign_as":      "party",   # signatário é parte (não testemunha)
            "message":      "Por favor, leia e assine o Termo de Responsabilidade do notebook.",
        }
    }
    data = _post("/api/v1/lists", payload)
    rsk = (data.get("list") or {}).get("request_signature_key")
    if not rsk:
        raise ClicksignError("Clicksign retornou OK mas não devolveu o request_signature_key.")
    return rsk


# =========================================
# 4) DISPARAR NOTIFICAÇÃO POR E-MAIL
# =========================================
def notificar_signatario(request_signature_key: str) -> None:
    """Dispara o e-mail da Clicksign pro signatário com o link de assinatura."""
    payload = {
        "request_signature_key": request_signature_key,
        "message": "Você recebeu um Termo de Responsabilidade da CPE Tecnologia para assinar."
    }
    _post("/api/v1/notifications", payload)


# =========================================
# FLUXO COMPLETO (alto nível)
# =========================================
def enviar_termo_para_assinatura(
    pdf_bytes: bytes,
    filename: str,
    signatario_nome: str,
    signatario_email: str,
    signatario_cpf: str,
) -> Dict[str, str]:
    """Executa as 4 etapas e devolve as chaves geradas.

    Lança ClicksignError em qualquer falha (com mensagem amigável).
    """
    document_key = criar_documento(pdf_bytes, filename)
    signer_key   = criar_signatario(signatario_nome, signatario_email, signatario_cpf)
    rsk          = vincular_signatario(document_key, signer_key)
    notificar_signatario(rsk)
    return {
        "document_key":          document_key,
        "signer_key":            signer_key,
        "request_signature_key": rsk,
    }
