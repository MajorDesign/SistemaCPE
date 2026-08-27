"""
Modo Suporte (impersonate) — 2026-08-27.

Permite que um ADMIN inicie uma sessao "vendo como" outro usuario, pra
diagnostico rapido do que o usuario esta enxergando/vivenciando.

Seguranca:
- SO ADMIN pode iniciar (nem TI, nem RESPONSAVEL_GRUPO).
- Nao pode impersonar outro ADMIN (evita "roubo" horizontal).
- Nao pode impersonar a si mesmo.
- Token de impersonate expira em 60 minutos (nao renovavel; precisa
  reiniciar impersonate).
- Sessao e READ-ONLY: middleware bloqueia POST/PUT/PATCH/DELETE
  (excecao: /api/auth/logout e /api/auth/impersonate/end).
- Toda açao fica registrada em audit_logs.

Frontend:
- Ao chamar /impersonate/{target_id}, recebe {token} e substitui o token
  atual, guardando o original em localStorage['cpe_token_real'].
- Banner global em todas as paginas mostra "voce esta em modo suporte" +
  botao Sair (chama /impersonate/end e restaura o token real).
"""

from typing import Any, Dict

from database import engine
from fastapi import APIRouter, Depends, HTTPException, Request, status
from security import (
    get_current_user,
    get_user_by_id,
    make_impersonation_token,
    IMPERSONATE_TTL_SECONDS,
)
from sqlalchemy import text

router = APIRouter(prefix="/api/auth", tags=["Auth-Impersonate"])


def _log_audit(user_id: int, action: str, target_user_id: int,
                description: str, ip: str = None) -> None:
    """Grava linha em audit_logs. Silencioso se tabela nao existe."""
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO audit_logs
                  (user_id, module, action, object_type, object_id, ip_address, description)
                VALUES
                  (:uid, :mod, :act, :otype, :oid, :ip, :desc)
            """), {
                "uid":  user_id,
                "mod":  "auth",
                "act":  action,
                "otype": "user",
                "oid":  target_user_id,
                "ip":   ip,
                "desc": description[:500] if description else None,
            })
    except Exception as e:
        # Nao quebra o flow se audit_logs schema for diferente
        import logging
        logging.getLogger(__name__).warning(f"[IMPERSONATE/AUDIT] falha: {e}")


@router.post("/impersonate/{target_id}")
async def start_impersonate(target_id: int, request: Request,
                             current_user: Dict[str, Any] = Depends(get_current_user)):
    """Inicia sessao de suporte. Retorna token temporario (60min, read-only)."""
    role = (current_user.get("role") or "").upper()

    # Guard 1: so ADMIN inicia (mesmo se ja for impersonate, o real user
    # que conta pra ADMIN — get_current_user retorna dados do impersonated).
    # Aqui usamos o impersonated_by pra impedir "impersonate encadeado".
    if current_user.get("impersonated_by"):
        raise HTTPException(status_code=400,
                             detail="Voce ja esta em modo suporte. Saia primeiro.")
    if role != "ADMIN":
        raise HTTPException(status_code=403,
                             detail="Apenas ADMIN pode entrar em modo suporte.")

    # Guard 2: nao pode ser voce mesmo
    if target_id == current_user["id"]:
        raise HTTPException(status_code=400,
                             detail="Voce nao precisa impersonar voce mesmo.")

    # Guard 3: alvo existe e esta ativo
    target = get_user_by_id(target_id)
    if not target or target.get("is_active") != 1:
        raise HTTPException(status_code=404,
                             detail="Usuario nao encontrado ou inativo.")

    # Guard 4: alvo NAO pode ser ADMIN (evita "roubo horizontal")
    if (target.get("role") or "").upper() == "ADMIN":
        raise HTTPException(status_code=403,
                             detail="Nao e possivel entrar como outro ADMIN.")

    token = make_impersonation_token(current_user["id"], target_id)

    # Audit
    client_ip = request.client.host if request.client else None
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        client_ip = fwd.split(",")[0].strip()
    _log_audit(
        user_id=current_user["id"],
        action="impersonate_start",
        target_user_id=target_id,
        description=f"{current_user['name']} iniciou modo suporte como {target['name']} ({target['email']})",
        ip=client_ip,
    )

    return {
        "success":         True,
        "token":           token,
        "impersonated": {
            "id":    target["id"],
            "name":  target["name"],
            "email": target["email"],
            "role":  target["role"],
        },
        "expires_in":      IMPERSONATE_TTL_SECONDS,
        "warning":         "Modo suporte esta READ-ONLY. Qualquer POST/PUT/DELETE sera bloqueado.",
    }


@router.post("/impersonate/end")
async def end_impersonate(request: Request,
                           current_user: Dict[str, Any] = Depends(get_current_user)):
    """Encerra a sessao de suporte no lado servidor (audit).
    O frontend descarta o token e volta pro token real que guardou."""
    if not current_user.get("impersonated_by"):
        return {"success": True, "message": "Nao estava em modo suporte."}
    imp_id = current_user["impersonated_by"]
    imp_name = current_user.get("impersonated_by_name") or f"user#{imp_id}"

    client_ip = request.client.host if request.client else None
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        client_ip = fwd.split(",")[0].strip()
    _log_audit(
        user_id=imp_id,
        action="impersonate_end",
        target_user_id=current_user["id"],
        description=f"{imp_name} encerrou modo suporte (era {current_user['name']})",
        ip=client_ip,
    )
    return {"success": True, "message": "Modo suporte encerrado."}
