"""
Routes package
"""

# Import rotas para registro em app.py
from . import auth
from . import users
from . import groups
from . import passwords_new
from . import audit

__all__ = ["auth", "users", "groups", "passwords_new", "audit"]