"""
Criptografia simétrica (Fernet/AES-128-CBC + HMAC) para guardar
tokens de terceiros (Carbonio, etc.) no banco.

Uso:
    from services.crypto_helper import encrypt_str, decrypt_str
    encrypted = encrypt_str("meu segredo")
    plain     = decrypt_str(encrypted)

A chave vem de AGENDA_SECRET_KEY (.env). Se ausente, deriva-se de
APP_SECRET via SHA256, mas a recomendação é definir explicitamente
com `Fernet.generate_key()`.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet

    raw = os.getenv("AGENDA_SECRET_KEY", "").strip()
    if raw:
        try:
            _fernet = Fernet(raw.encode())
            return _fernet
        except (ValueError, TypeError):
            logger.warning(
                "[CRYPTO] AGENDA_SECRET_KEY inválida (não é uma chave Fernet). "
                "Derivando do APP_SECRET — defina com Fernet.generate_key()."
            )

    # Fallback: deriva chave do APP_SECRET (menos seguro, mas funcional)
    secret = os.getenv("APP_SECRET", "default-change-me-now")
    digest = hashlib.sha256(secret.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    _fernet = Fernet(key)
    return _fernet


def encrypt_str(plain: str) -> str:
    """Criptografa texto e retorna em base64 url-safe."""
    if plain is None:
        return None
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_str(token: str) -> Optional[str]:
    """Descriptografa. Retorna None se o token for inválido/corrompido."""
    if not token:
        return None
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        logger.warning("[CRYPTO] token inválido (chave mudou ou dado corrompido)")
        return None
