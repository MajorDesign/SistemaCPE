"""
Configurações centralizadas da aplicação
"""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# =========================================
# LOAD ENV
# =========================================
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# =========================================
# BANCO DE DADOS
# =========================================
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DB", "cpe_plus")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
)

# =========================================
# APLICAÇÃO
# =========================================
APP_TITLE = "CPE Control API"
APP_VERSION = "0.2"
APP_SECRET = os.getenv("APP_SECRET", "change_me")

# =========================================
# CORS
# =========================================
CORS_ORIGINS_RAW = os.getenv("CORS_ORIGINS", "http://localhost").strip()
CORS_ORIGINS: List[str] = [o.strip() for o in CORS_ORIGINS_RAW.split(",") if o.strip()]

CORS_DEFAULT_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

# =========================================
# SESSÃO
# =========================================
COOKIE_NAME = "cpe_session"
SESSION_MAX_AGE_SECONDS = 7 * 24 * 3600  # 7 dias

# =========================================
# DEV
# =========================================
DEV_API_KEY = os.getenv("DEV_API_KEY", "").strip()

# =========================================
# STARTUP LOG
# =========================================
def print_startup_config():
    """Imprime configurações ao iniciar"""
    print("\n" + "=" * 60)
    print("CPE Control API - Iniciando")
    print("=" * 60)
    print(f"Banco de dados: {MYSQL_DB}")
    print(f"Host: {MYSQL_HOST}:{MYSQL_PORT}")
    print(f"DEV_API_KEY carregada? {'SIM' if DEV_API_KEY else 'NÃO'}")
    print(f"CORS_ORIGINS: {CORS_ORIGINS if CORS_ORIGINS else CORS_DEFAULT_ORIGINS}")
    print(f"SESSION_MAX_AGE: {SESSION_MAX_AGE_SECONDS} segundos ({SESSION_MAX_AGE_SECONDS // 3600} horas)")
    print("=" * 60 + "\n")