"""
Serviço de Conexão com Banco de Dados
Centraliza toda a lógica de conexão MySQL para evitar circular imports
Utiliza mysql.connector (sem SQLAlchemy)
"""

from fastapi import HTTPException, status
import mysql.connector
import logging
import os
from typing import Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Engine SQLAlchemy (usado por security.py e rotas que precisam de SQLAlchemy)
_database_url = os.getenv("DATABASE_URL", "mysql+pymysql://root:@127.0.0.1:3306/cpe_plus")
engine = create_engine(_database_url, pool_pre_ping=True)

# =========================================
# CONFIGURACAO DE LOGGING
# =========================================
logger = logging.getLogger(__name__)

# =========================================
# CONFIGURACAO DO BANCO DE DADOS
# =========================================
DB_CONFIG = {
    "host":     os.getenv("MYSQL_HOST",     "localhost"),
    "user":     os.getenv("MYSQL_USER",     "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DB",       "cpe_plus"),
    "use_pure": True,    # evita segfault do C extension no mysql-connector 9.x
    "charset":  "utf8mb4",   # corrige acentuação (XAMPP retorna cp850 por padrão)
    "collation": "utf8mb4_unicode_ci",
}

logger.info("=" * 90)
logger.info("DATABASE.PY - CONFIGURACAO DE BANCO DE DADOS")
logger.info("=" * 90)
logger.info(f"Host: {DB_CONFIG['host']}")
logger.info(f"User: {DB_CONFIG['user']}")
logger.info(f"Database: {DB_CONFIG['database']}")
logger.info("=" * 90 + "\n")

# =========================================
# FUNCOES DE CONEXAO
# =========================================

def get_db_connection():
    """
    Estabelece conexao com o banco de dados MySQL
    
    Returns:
        mysql.connector.MySQLConnection: Conexao ativa com o banco
        
    Raises:
        mysql.connector.Error: Erro ao conectar ao MySQL
        Exception: Erro desconhecido
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        logger.debug("[DB] Conexao estabelecida com sucesso")
        return conn
    
    except mysql.connector.Error as err:
        if err.errno == 2003:
            logger.error("[DB] Erro 2003: Nao conseguiu conectar ao MySQL")
            logger.error(f"[DB]    > Verifique se o MySQL esta rodando em {DB_CONFIG['host']}")
        elif err.errno == 1049:
            logger.error(f"[DB] Erro 1049: Database '{DB_CONFIG['database']}' nao existe")
            logger.error("[DB]    > Crie o database ou altere o nome em DB_CONFIG")
        elif err.errno == 1045:
            logger.error("[DB] Erro 1045: Usuario ou senha invalidos")
        else:
            logger.error(f"[DB] Erro MySQL #{err.errno}: {err.msg}")
        raise
    
    except Exception as err:
        logger.error(f"[DB] Erro desconhecido ao conectar: {str(err)}")
        raise


def get_db_or_404():
    """
    Obtem conexao com o banco de dados ou lanca erro HTTP 500
    
    Usada pelos routers quando precisam de conexao com banco
    Trata erros e retorna resposta HTTP apropriada
    
    Returns:
        mysql.connector.MySQLConnection: Conexao ativa com o banco
        
    Raises:
        HTTPException: Erro 500 quando nao consegue conectar
    """
    try:
        logger.debug("[DB] Obtendo conexao via get_db_or_404()...")
        conn = get_db_connection()
        logger.debug("[DB] Conexao obtida com sucesso")
        return conn
    
    except Exception as err:
        logger.error(f"[DB] Erro ao conectar ao banco: {str(err)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao conectar ao banco de dados"
        )


def testar_conexao() -> bool:
    """
    Testa se a conexao com o banco de dados esta funcionando
    
    Executada durante a inicializacao da aplicacao
    
    Returns:
        bool: True se conexao funciona, False caso contrario
    """
    try:
        logger.info("[DB] Testando conexao com o banco de dados...")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        logger.info(f"[DB] ✅ MySQL version: {version[0]}")
        return True
    
    except Exception as err:
        logger.error(f"[DB] ❌ FALHA NA CONEXAO: {str(err)}")
        return False

# =========================================
# UTILITARIOS DE CONVERSAO
# =========================================

def convert_datetime_to_string(obj: dict) -> dict:
    """
    Converte campos datetime para string ISO em um dicionario
    
    Args:
        obj (dict): Dicionario com campos datetime
        
    Returns:
        dict: Dicionario com datetime convertidos para string
    """
    if not obj:
        return obj
    
    try:
        if 'created_at' in obj and obj['created_at']:
            if hasattr(obj['created_at'], 'isoformat'):
                obj['created_at'] = obj['created_at'].isoformat()
        
        if 'updated_at' in obj and obj['updated_at']:
            if hasattr(obj['updated_at'], 'isoformat'):
                obj['updated_at'] = obj['updated_at'].isoformat()
        
        return obj
    
    except Exception as err:
        logger.error(f"[CONVERT] Erro ao converter datetime: {str(err)}")
        return obj


def convert_datetime_list(objects: list) -> list:
    """
    Converte campos datetime para string ISO em uma lista de dicionarios
    
    Args:
        objects (list): Lista de dicionarios com campos datetime
        
    Returns:
        list: Lista com datetime convertidos para string
    """
    return [convert_datetime_to_string(obj) for obj in objects]

# =========================================
# VALIDACOES DE BANCO DE DADOS
# =========================================

def validate_group_exists(cursor, group_id: int) -> bool:
    """
    Valida se um grupo existe no banco de dados
    
    Args:
        cursor: Cursor MySQL aberto
        group_id (int): ID do grupo a validar
        
    Returns:
        bool: True se grupo existe, False caso contrario
    """
    try:
        cursor.execute("SELECT id FROM password_groups WHERE id = %s", (group_id,))
        resultado = cursor.fetchone()
        return resultado is not None
    
    except Exception as err:
        logger.error(f"[VALIDATE] Erro ao validar grupo: {str(err)}")
        return False


def validate_email_unique(cursor, email: str, exclude_user_id: Optional[int] = None) -> bool:
    """
    Valida se um email e unico no banco de dados
    
    Args:
        cursor: Cursor MySQL aberto
        email (str): Email a validar
        exclude_user_id (Optional[int]): ID de usuario para excluir da validacao (para UPDATE)
        
    Returns:
        bool: True se email e unico, False se ja existe
    """
    try:
        if exclude_user_id:
            cursor.execute(
                "SELECT id FROM users WHERE email = %s AND id != %s",
                (email, exclude_user_id)
            )
        else:
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        
        resultado = cursor.fetchone()
        return resultado is None
    
    except Exception as err:
        logger.error(f"[VALIDATE] Erro ao validar email: {str(err)}")
        return False


def validate_username_unique(cursor, username: str, exclude_user_id: Optional[int] = None) -> bool:
    """
    Valida se um username e unico no banco de dados
    
    Args:
        cursor: Cursor MySQL aberto
        username (str): Username a validar
        exclude_user_id (Optional[int]): ID de usuario para excluir da validacao (para UPDATE)
        
    Returns:
        bool: True se username e unico, False se ja existe
    """
    try:
        if exclude_user_id:
            cursor.execute(
                "SELECT id FROM users WHERE username = %s AND id != %s",
                (username, exclude_user_id)
            )
        else:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        
        resultado = cursor.fetchone()
        return resultado is None
    
    except Exception as err:
        logger.error(f"[VALIDATE] Erro ao validar username: {str(err)}")
        return False

# =========================================
# UTILITARIOS DE TICKETS
# =========================================

def gerar_numero_ticket(cursor) -> str:
    """
    Gera numero unico para ticket no formato YYYY-XXXXX
    
    Args:
        cursor: Cursor MySQL aberto
        
    Returns:
        str: Numero do ticket gerado (ex: 2026-00001)
        
    Raises:
        HTTPException: Erro 500 se nao conseguir gerar numero
    """
    try:
        from datetime import datetime
        
        ano_atual = datetime.now().year
        cursor.execute("""
            SELECT numero FROM tickets 
            WHERE numero LIKE CONCAT(%s, '-%')
            ORDER BY numero DESC LIMIT 1
        """, (str(ano_atual),))
        
        resultado = cursor.fetchone()
        
        if resultado and resultado['numero']:
            numero_atual = resultado['numero']
            sequencial = int(numero_atual.split('-')[1]) + 1
        else:
            sequencial = 1
        
        numero_ticket = f"{ano_atual}-{sequencial:05d}"
        logger.info(f"[TICKET] Numero gerado: {numero_ticket}")
        return numero_ticket
    
    except Exception as err:
        logger.error(f"[NUMERO] Erro ao gerar numero: {str(err)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar numero do ticket: {str(err)}"
        )


def mapa_dados_ticket(ticket: dict, cursor) -> dict:
    """
    Mapeia dados do ticket com informacoes relacionadas (usuario, grupo, etc)
    
    Args:
        ticket (dict): Dados basicos do ticket
        cursor: Cursor MySQL aberto
        
    Returns:
        dict: Ticket com dados relacionados mapeados
    """
    try:
        # Buscar nome do solicitante
        cursor.execute(
            "SELECT name, email FROM users WHERE id = %s",
            (ticket['solicitante_id'],)
        )
        solicitante = cursor.fetchone()
        
        # Buscar nome do responsavel
        responsavel = None
        if ticket.get('responsavel_id'):
            cursor.execute(
                "SELECT name FROM users WHERE id = %s",
                (ticket['responsavel_id'],)
            )
            responsavel = cursor.fetchone()
        
        # Buscar nome do grupo
        grupo = None
        if ticket.get('group_id'):
            cursor.execute(
                "SELECT name FROM password_groups WHERE id = %s",
                (ticket['group_id'],)
            )
            grupo = cursor.fetchone()
        
        return {
            **ticket,
            "solicitante_nome": solicitante['name'] if solicitante else "Desconhecido",
            "solicitante_email": solicitante['email'] if solicitante else "sem-email",
            "responsavel_nome": responsavel['name'] if responsavel else "Nao atribuido",
            "group_name": grupo['name'] if grupo else "Sem setor"
        }
    
    except Exception as err:
        logger.error(f"[MAPA] Erro ao mapear dados do ticket: {str(err)}")
        return ticket

# =========================================
# INICIALIZACAO
# =========================================

logger.info("✅ DATABASE.PY CARREGADO COM SUCESSO!")
logger.info("   - get_db_connection() disponivel")
logger.info("   - get_db_or_404() disponivel")
logger.info("   - Funcoes de validacao disponivel")
logger.info("   - Funcoes utilitarias disponivel\n")