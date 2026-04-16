"""
Funções auxiliares e utilitários
"""

from fastapi import HTTPException, status
from security import pwd_context

# =========================================
# PASSWORD VALIDATION
# =========================================

def ensure_bcrypt_password_ok(raw_password: str) -> None:
    """Valida comprimento da senha para bcrypt (máx 72 bytes)"""
    if len(raw_password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha muito longa. O máximo para bcrypt é 72 bytes."
        )


def hash_password(password: str) -> str:
    """Gera hash da senha"""
    ensure_bcrypt_password_ok(password)
    return pwd_context.hash(password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    """Verifica se a senha corresponde ao hash"""
    try:
        return pwd_context.verify(raw_password, password_hash)
    except Exception as e:
        print(f"[UTILS] ✗ Erro ao verificar hash: {e}")
        return False


# =========================================
# VALIDATION HELPERS
# =========================================

def validate_email_format(email: str) -> bool:
    """Valida formato básico de email"""
    return "@" in email and "." in email.split("@")[-1]


def validate_password_strength(password: str) -> bool:
    """Valida força da senha (mínimo 6 caracteres)"""
    return len(password) >= 6


# =========================================
# STRING HELPERS
# =========================================

def normalize_email(email: str) -> str:
    """Normaliza email: lowercase + strip"""
    return email.lower().strip()


def normalize_string(s: str) -> str:
    """Normaliza string: strip"""
    return s.strip() if s else ""