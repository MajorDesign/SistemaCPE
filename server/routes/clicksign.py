"""
Rotas Clicksign — assinatura eletrônica.

Endpoint principal:
  POST /api/clicksign/termo-notebook
    Recebe PDF (multipart) + nome + cpf + email do colaborador.
    Cria documento + signatário + lista + dispara e-mail na Clicksign.
    Devolve as keys geradas (pra eventual auditoria/log).

O token Clicksign vive em server/.env (CLICKSIGN_TOKEN). Nunca trafega pra fora do servidor.
"""

import logging
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form

from services.clicksign_service import (
    enviar_termo_para_assinatura,
    ClicksignError,
)
from routes.contratos import _get_user  # reutiliza auth padrão do projeto

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/clicksign", tags=["Clicksign"])

MAX_PDF_BYTES = 2 * 1024 * 1024  # 2 MB (mesmo limite do upload de contratos)


@router.post("/termo-notebook")
async def termo_notebook(
    request: Request,
    nome: str       = Form(...),
    cpf: str        = Form(...),
    email: str      = Form(...),
    file: UploadFile = File(...),
):
    """Envia o Termo de Responsabilidade do colaborador para assinatura na Clicksign.

    Erros mapeados (mensagens claras pra UI mostrar ao usuário):
      - 400: arquivo vazio / inválido
      - 401: não autenticado no SistemaCPE
      - 502: Clicksign falhou (token inválido, dados inválidos, fora do ar etc.)
    """
    user = _get_user(request)  # 401 se não autenticado

    # ---- Validações básicas (antes de torrar chamada Clicksign) ----
    if not nome.strip() or len(nome.strip().split()) < 2:
        raise HTTPException(status_code=400, detail="Informe o nome completo (nome + sobrenome).")

    cpf_digits = "".join(c for c in (cpf or "") if c.isdigit())
    if len(cpf_digits) != 11:
        raise HTTPException(status_code=400, detail="CPF inválido (precisa ter 11 dígitos).")

    email = (email or "").strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="E-mail do colaborador inválido.")

    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="O arquivo precisa ser um PDF.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"PDF excede {MAX_PDF_BYTES//1024} KB (enviado: {len(pdf_bytes)//1024} KB)."
        )

    # ---- Chamada Clicksign (4 etapas encadeadas no service) ----
    primeiro = nome.strip().split()[0]
    filename = f"termo_{primeiro}_{cpf_digits[-4:]}.pdf"

    try:
        keys = enviar_termo_para_assinatura(
            pdf_bytes        = pdf_bytes,
            filename         = filename,
            signatario_nome  = nome.strip(),
            signatario_email = email,
            signatario_cpf   = cpf_digits,
        )
    except ClicksignError as e:
        # Mensagem amigável (já vem formatada do service)
        logger.warning(f"[CLICKSIGN] Falha ao enviar termo (user={user['id']}, email={email}): {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception(f"[CLICKSIGN] Erro inesperado (user={user['id']}): {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Erro inesperado ao integrar com a Clicksign: {e}"
        )

    logger.info(
        f"[CLICKSIGN] ✓ Termo enviado para assinatura "
        f"(user={user['id']}, signatario={email}, document_key={keys['document_key']})"
    )

    return {
        "success":      True,
        "message":      f"Termo enviado para {email}. O colaborador receberá o e-mail da Clicksign para assinar.",
        "document_key": keys["document_key"],
        "signer_key":   keys["signer_key"],
    }
