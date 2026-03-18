"""
Configuração do banco de dados
"""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from config import DATABASE_URL

# =========================================
# DATABASE ENGINE
# =========================================
engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)

print(f"✓ Engine SQLAlchemy criado")

def get_db_connection():
    """Retorna uma conexão com o banco"""
    return engine.connect()

def get_db_session():
    """Retorna uma sessão do banco (usar como context manager)"""
    with engine.begin() as conn:
        yield conn