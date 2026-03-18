"""
CPE Control API - Aplicação Principal
Gerenciamento de Usuários com Vinculação de Grupos
"""

from fastapi import FastAPI, HTTPException, APIRouter, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import mysql.connector
from contextlib import asynccontextmanager
from datetime import datetime
import logging

# =========================================
# CONFIGURAR LOGGING
# =========================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =========================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# =========================================

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "cpe_plus",
}

logger.info("=" * 90)
logger.info("🔧 CONFIGURAÇÃO DE BANCO DE DADOS")
logger.info("=" * 90)
logger.info(f"Host: {DB_CONFIG['host']}")
logger.info(f"User: {DB_CONFIG['user']}")
logger.info(f"Database: {DB_CONFIG['database']}")
logger.info("=" * 90 + "\n")

# =========================================
# FUNÇÕES DE BANCO DE DADOS
# =========================================

def get_db_connection():
    """✅ Estabelece conexão com o banco de dados"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        if err.errno == 2003:
            logger.error("[DB] ❌ Erro 2003: Não conseguiu conectar ao MySQL")
            logger.error(f"[DB]    → Verifique se o MySQL está rodando em {DB_CONFIG['host']}")
        elif err.errno == 1049:
            logger.error(f"[DB] ❌ Erro 1049: Database '{DB_CONFIG['database']}' não existe")
            logger.error("[DB]    → Crie o database ou altere o nome em DB_CONFIG")
        elif err.errno == 1045:
            logger.error("[DB] ❌ Erro 1045: Usuário ou senha inválidos")
        else:
            logger.error(f"[DB] ❌ Erro MySQL #{err.errno}: {err.msg}")
        raise
    except Exception as err:
        logger.error(f"[DB] ❌ Erro desconhecido ao conectar: {str(err)}")
        raise

# Testar conexão ao iniciar
try:
    logger.info("[DB] 🧪 Testando conexão com o banco de dados...")
    test_conn = get_db_connection()
    test_cursor = test_conn.cursor()
    test_cursor.execute("SELECT VERSION()")
    version = test_cursor.fetchone()
    logger.info(f"[DB] ✅ MySQL version: {version[0]}")
    test_cursor.close()
    test_conn.close()
except Exception as err:
    logger.error(f"[DB] ❌ FALHA NA CONEXÃO: {str(err)}")

# =========================================
# MODELOS PYDANTIC - USUÁRIOS
# =========================================

class UserBase(BaseModel):
    """Modelo base de usuário"""
    name: str = Field(..., min_length=3, max_length=255, description="Nome completo")
    email: EmailStr = Field(..., description="Email do usuário")
    username: str = Field(..., min_length=3, max_length=100, description="Nome de usuário")
    role: str = Field(default="USER", pattern="^(USER|ADMIN|MANAGER|TI)$", description="Papel do usuário")
    group_id: Optional[int] = Field(None, description="ID do grupo vinculado")
    is_active: bool = Field(True, description="Status do usuário")


class UserCreate(UserBase):
    """Modelo para criar usuário (sem autenticação)"""
    pass


class UserUpdate(BaseModel):
    """Modelo para atualizar usuário"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    role: Optional[str] = Field(None, pattern="^(USER|ADMIN|MANAGER|TI)$")
    group_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Modelo de resposta do usuário"""
    id: int
    name: str
    email: str
    username: str
    role: str
    group_id: Optional[int] = None
    is_active: bool
    created_at: Optional[str] = None


# =========================================
# MODELOS PYDANTIC - GRUPOS
# =========================================

class GroupBase(BaseModel):
    """Modelo base de grupo"""
    name: str = Field(..., min_length=3, max_length=255, description="Nome do grupo")
    description: Optional[str] = Field(None, max_length=500, description="Descrição do grupo")


class GroupCreate(GroupBase):
    """Modelo para criar grupo"""
    pass


class GroupUpdate(BaseModel):
    """Modelo para atualizar grupo"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=500)


class GroupResponse(BaseModel):
    """Modelo de resposta do grupo"""
    id: int
    name: str
    description: Optional[str] = None
    created_at: Optional[str] = None


# =========================================
# MODELOS PYDANTIC - HEALTH CHECK
# =========================================

class HealthCheckResponse(BaseModel):
    """Modelo para health check"""
    status: str
    api: str
    version: str
    timestamp: str
    database: Optional[str] = None


# =========================================
# FUNÇÕES UTILITÁRIAS
# =========================================

def get_db_or_404():
    """Obtém conexão ou lança erro 500"""
    try:
        return get_db_connection()
    except Exception as err:
        logger.error(f"[DB] ✗ Erro ao conectar ao banco: {str(err)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao conectar ao banco de dados"
        )


def convert_datetime_to_string(obj: dict) -> dict:
    """✅ Converte datetime para string ISO em um dicionário"""
    if obj and obj.get('created_at'):
        obj['created_at'] = obj['created_at'].isoformat()
    return obj


def convert_datetime_list(objects: list) -> list:
    """✅ Converte datetime para string ISO em lista"""
    return [convert_datetime_to_string(obj) for obj in objects]


def validate_group_exists(cursor, group_id: int) -> bool:
    """Valida se um grupo existe"""
    try:
        cursor.execute("SELECT id FROM password_groups WHERE id = %s", (group_id,))
        return cursor.fetchone() is not None
    except Exception as err:
        logger.error(f"[VALIDATE] ✗ Erro ao validar grupo: {str(err)}")
        return False


def validate_email_unique(cursor, email: str, exclude_user_id: Optional[int] = None) -> bool:
    """Valida se um email é único"""
    try:
        if exclude_user_id:
            cursor.execute(
                "SELECT id FROM users WHERE email = %s AND id != %s",
                (email, exclude_user_id)
            )
        else:
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        return cursor.fetchone() is None
    except Exception as err:
        logger.error(f"[VALIDATE] ✗ Erro ao validar email: {str(err)}")
        return False


def validate_username_unique(cursor, username: str, exclude_user_id: Optional[int] = None) -> bool:
    """Valida se um username é único"""
    try:
        if exclude_user_id:
            cursor.execute(
                "SELECT id FROM users WHERE username = %s AND id != %s",
                (username, exclude_user_id)
            )
        else:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        return cursor.fetchone() is None
    except Exception as err:
        logger.error(f"[VALIDATE] ✗ Erro ao validar username: {str(err)}")
        return False


# =========================================
# LIFESPAN - EVENTOS DE CICLO DE VIDA
# =========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    # ===== STARTUP =====
    logger.info("\n" + "=" * 90)
    logger.info("✅ CPE CONTROL API v2.0.0 INICIADA COM SUCESSO")
    logger.info("=" * 90)
    logger.info("\n📌 ENDPOINTS DISPONÍVEIS:")
    logger.info("   " + "─" * 80)
    logger.info("   📋 GET    /api/groups                → Listar grupos")
    logger.info("   📄 GET    /api/groups/{id}           → Obter grupo específico")
    logger.info("   ➕ POST   /api/groups                → Criar novo grupo")
    logger.info("   ✏️  PUT    /api/groups/{id}           → Atualizar grupo")
    logger.info("   🗑️  DELETE /api/groups/{id}           → Deletar grupo")
    logger.info("   📋 GET    /api/users                 → Listar usuários")
    logger.info("   📄 GET    /api/users/{id}            → Obter usuário específico")
    logger.info("   ➕ POST   /api/users                 → Criar novo usuário")
    logger.info("   ✏️  PUT    /api/users/{id}            → Atualizar usuário")
    logger.info("   🗑️  DELETE /api/users/{id}            → Deletar usuário")
    logger.info("   ❤️  GET    /health                   → Verificar saúde da API")
    logger.info("   " + "─" * 80)
    logger.info("\n📊 DOCUMENTAÇÃO:")
    logger.info("   • Swagger UI: http://localhost:8000/docs")
    logger.info("   • ReDoc: http://localhost:8000/redoc")
    logger.info("\n" + "=" * 90 + "\n")
    
    yield
    
    # ===== SHUTDOWN =====
    logger.info("\n" + "=" * 90)
    logger.info("🛑 CPE CONTROL API DESLIGADA COM SUCESSO")
    logger.info("=" * 90 + "\n")


# =========================================
# CRIAR APLICAÇÃO FASTAPI
# =========================================

app = FastAPI(
    title="CPE Control API",
    version="2.0.0",
    description="Sistema de Gerenciamento de Usuários com Vinculação de Grupos (Sem Autenticação)",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# =========================================
# MIDDLEWARE: CORS
# =========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:80",
        "http://localhost:8080",
        "http://localhost:5500",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:80",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:8000",
        "http://localhost/SistemaCPE",
        "http://127.0.0.1/SistemaCPE",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600
)

logger.info("✅ CORS CONFIGURADO COM SUCESSO!\n")


# =========================================
# ROUTER DE GRUPOS
# =========================================

groups_router = APIRouter(prefix="/api/groups", tags=["groups"])


@groups_router.get(
    "/",
    response_model=list,
    summary="Listar grupos",
    description="Obtém lista completa de todos os grupos cadastrados"
)
async def get_groups():
    """📋 Obtém todos os grupos"""
    logger.info("\n" + "=" * 90)
    logger.info("[GROUPS] 📋 Listando todos os grupos...")
    logger.info("=" * 90)
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                id,
                name,
                created_at
            FROM password_groups
            ORDER BY created_at DESC
        """
        
        cursor.execute(query)
        groups = cursor.fetchall()
        groups = convert_datetime_list(groups)
        
        logger.info(f"[GROUPS] ✓ {len(groups)} grupo(s) encontrado(s)")
        logger.info("=" * 90 + "\n")
        
        return groups or []
        
    except Exception as err:
        logger.error(f"[GROUPS] ✗ Erro: {str(err)}")
        logger.error("=" * 90 + "\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar grupos: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@groups_router.get(
    "/{group_id}",
    response_model=GroupResponse,
    summary="Obter grupo",
    description="Obtém informações detalhadas de um grupo específico"
)
async def get_group(group_id: int):
    """📄 Obtém um grupo específico pelo ID"""
    logger.info(f"\n[GROUPS] 📄 Obtendo grupo #{group_id}...")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                id,
                name,
                created_at
            FROM password_groups
            WHERE id = %s
        """
        
        cursor.execute(query, (group_id,))
        group = cursor.fetchone()
        
        if not group:
            logger.warning(f"[GROUPS] ✗ Grupo #{group_id} não encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo com ID {group_id} não encontrado"
            )
        
        group = convert_datetime_to_string(group)
        logger.info(f"[GROUPS] ✓ Grupo encontrado: {group['name']}\n")
        return group
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[GROUPS] ✗ Erro: {str(err)}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter grupo: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@groups_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=GroupResponse,
    summary="Criar grupo",
    description="Cria um novo grupo"
)
async def create_group(group: GroupCreate):
    """➕ Cria um novo grupo"""
    logger.info("\n" + "=" * 90)
    logger.info("[GROUPS] ➕ CRIANDO NOVO GRUPO")
    logger.info("=" * 90)
    logger.info(f"[GROUPS]   • Nome: {group.name}")
    if group.description:
        logger.info(f"[GROUPS]   • Descrição: {group.description}")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        insert_query = """
            INSERT INTO password_groups (name)
            VALUES (%s)
        """
        
        cursor.execute(insert_query, (group.name,))
        
        conn.commit()
        new_group_id = cursor.lastrowid
        logger.info(f"[GROUPS] ✓ Grupo criado com ID: {new_group_id}")
        
        cursor.execute(
            """SELECT id, name, created_at 
               FROM password_groups WHERE id = %s""",
            (new_group_id,)
        )
        new_group = cursor.fetchone()
        new_group = convert_datetime_to_string(new_group)
        
        logger.info("[GROUPS] ✓ SUCESSO!")
        logger.info("=" * 90 + "\n")
        
        return new_group
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[GROUPS] ✗ ERRO: {str(err)}")
        logger.error("=" * 90 + "\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar grupo: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@groups_router.put(
    "/{group_id}",
    response_model=GroupResponse,
    summary="Atualizar grupo",
    description="Atualiza dados de um grupo"
)
async def update_group(group_id: int, group: GroupUpdate):
    """✏️ Atualiza um grupo"""
    logger.info("\n" + "=" * 90)
    logger.info(f"[GROUPS] ✏️ ATUALIZANDO GRUPO #{group_id}")
    logger.info("=" * 90)
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id FROM password_groups WHERE id = %s", (group_id,))
        if not cursor.fetchone():
            logger.warning(f"[GROUPS] ✗ Grupo #{group_id} não encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo com ID {group_id} não encontrado"
            )
        
        updates = []
        params = []
        
        if group.name is not None:
            updates.append("name = %s")
            params.append(group.name)
            logger.info(f"[GROUPS]   • Nome: {group.name}")
        
        if group.description is not None:
            updates.append("user_group_id = %s")
            params.append(group.description)
            logger.info(f"[GROUPS]   • Descrição: {group.description}")
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum campo fornecido para atualizar"
            )
        
        update_query = f"""
            UPDATE password_groups
            SET {', '.join(updates)}
            WHERE id = %s
        """
        
        params.append(group_id)
        cursor.execute(update_query, params)
        conn.commit()
        
        logger.info(f"[GROUPS] ✓ SUCESSO!")
        
        cursor.execute(
            """SELECT id, name, created_at 
               FROM password_groups WHERE id = %s""",
            (group_id,)
        )
        updated_group = cursor.fetchone()
        updated_group = convert_datetime_to_string(updated_group)
        
        logger.info("=" * 90 + "\n")
        
        return updated_group
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[GROUPS] ✗ ERRO: {str(err)}")
        logger.error("=" * 90 + "\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar grupo: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@groups_router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar grupo",
    description="Remove um grupo do sistema"
)
async def delete_group(group_id: int):
    """🗑️ Deleta um grupo do sistema"""
    logger.info(f"\n[GROUPS] 🗑️ DELETANDO GRUPO #{group_id}...")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT name FROM password_groups WHERE id = %s", (group_id,))
        group = cursor.fetchone()
        
        if not group:
            logger.warning(f"[GROUPS] ✗ Grupo #{group_id} não encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo com ID {group_id} não encontrado"
            )
        
        logger.info(f"[GROUPS] ✓ Deletando: {group['name']}")
        
        cursor.execute("DELETE FROM password_groups WHERE id = %s", (group_id,))
        conn.commit()
        
        logger.info(f"[GROUPS] ✓ DELETADO COM SUCESSO!\n")
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[GROUPS] ✗ ERRO: {str(err)}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar grupo: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# =========================================
# ROUTER DE USUÁRIOS
# =========================================

users_router = APIRouter(prefix="/api/users", tags=["users"])


@users_router.get(
    "/",
    response_model=list,
    summary="Listar usuários",
    description="Obtém lista completa de todos os usuários cadastrados"
)
async def get_users():
    """📋 Obtém todos os usuários"""
    logger.info("\n" + "=" * 90)
    logger.info("[USERS] 📋 Listando todos os usuários...")
    logger.info("=" * 90)
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                id,
                name,
                email,
                username,
                role,
                group_id,
                is_active,
                created_at
            FROM users
            ORDER BY created_at DESC
        """
        
        cursor.execute(query)
        users = cursor.fetchall()
        users = convert_datetime_list(users)
        
        logger.info(f"[USERS] ✓ {len(users)} usuário(s) encontrado(s)")
        logger.info("=" * 90 + "\n")
        
        return users or []
        
    except Exception as err:
        logger.error(f"[USERS] ✗ Erro: {str(err)}")
        logger.error("=" * 90 + "\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar usuários: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@users_router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Obter usuário",
    description="Obtém informações detalhadas de um usuário específico"
)
async def get_user(user_id: int):
    """📄 Obtém um usuário específico pelo ID"""
    logger.info(f"\n[USERS] 📄 Obtendo usuário #{user_id}...")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                id,
                name,
                email,
                username,
                role,
                group_id,
                is_active,
                created_at
            FROM users
            WHERE id = %s
        """
        
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
        
        if not user:
            logger.warning(f"[USERS] ✗ Usuário #{user_id} não encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuário com ID {user_id} não encontrado"
            )
        
        user = convert_datetime_to_string(user)
        logger.info(f"[USERS] ✓ Usuário encontrado: {user['name']}\n")
        return user
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[USERS] ✗ Erro: {str(err)}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter usuário: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@users_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    summary="Criar usuário",
    description="Cria um novo usuário com vinculação a um grupo (sem senha)"
)
async def create_user(user: UserCreate):
    """➕ Cria um novo usuário"""
    logger.info("\n" + "=" * 90)
    logger.info("[USERS] ➕ CRIANDO NOVO USUÁRIO")
    logger.info("=" * 90)
    logger.info(f"[USERS]   • Nome: {user.name}")
    logger.info(f"[USERS]   • Email: {user.email}")
    logger.info(f"[USERS]   • Username: {user.username}")
    logger.info(f"[USERS]   • Role: {user.role}")
    if user.group_id:
        logger.info(f"[USERS]   • Grupo: {user.group_id}")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        if not validate_email_unique(cursor, user.email):
            logger.warning(f"[USERS] ✗ Email já registrado: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{user.email}' já está registrado"
            )
        
        if not validate_username_unique(cursor, user.username):
            logger.warning(f"[USERS] ✗ Username já registrado: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{user.username}' já está registrado"
            )
        
        if user.group_id:
            if not validate_group_exists(cursor, user.group_id):
                logger.warning(f"[USERS] ✗ Grupo #{user.group_id} não encontrado")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Grupo com ID {user.group_id} não encontrado"
                )
        
        insert_query = """
            INSERT INTO users (name, email, username, role, group_id, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (
            user.name,
            user.email,
            user.username,
            user.role,
            user.group_id,
            user.is_active
        ))
        
        conn.commit()
        new_user_id = cursor.lastrowid
        logger.info(f"[USERS] ✓ Usuário criado com ID: {new_user_id}")
        
        cursor.execute(
            """SELECT id, name, email, username, role, group_id, is_active, created_at 
               FROM users WHERE id = %s""",
            (new_user_id,)
        )
        new_user = cursor.fetchone()
        new_user = convert_datetime_to_string(new_user)
        
        logger.info("[USERS] ✓ SUCESSO!")
        logger.info("=" * 90 + "\n")
        
        return new_user
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[USERS] ✗ ERRO: {str(err)}")
        logger.error("=" * 90 + "\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar usuário: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@users_router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Atualizar usuário",
    description="Atualiza dados de um usuário"
)
async def update_user(user_id: int, user: UserUpdate):
    """✏️ Atualiza um usuário"""
    logger.info("\n" + "=" * 90)
    logger.info(f"[USERS] ✏️ ATUALIZANDO USUÁRIO #{user_id}")
    logger.info("=" * 90)
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            logger.warning(f"[USERS] ✗ Usuário #{user_id} não encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuário com ID {user_id} não encontrado"
            )
        
        updates = []
        params = []
        
        if user.name is not None:
            updates.append("name = %s")
            params.append(user.name)
            logger.info(f"[USERS]   • Nome: {user.name}")
        
        if user.email is not None:
            if not validate_email_unique(cursor, user.email, exclude_user_id=user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email '{user.email}' já está registrado"
                )
            updates.append("email = %s")
            params.append(user.email)
            logger.info(f"[USERS]   • Email: {user.email}")
        
        if user.username is not None:
            if not validate_username_unique(cursor, user.username, exclude_user_id=user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Username '{user.username}' já está registrado"
                )
            updates.append("username = %s")
            params.append(user.username)
            logger.info(f"[USERS]   • Username: {user.username}")
        
        if user.role is not None:
            updates.append("role = %s")
            params.append(user.role)
            logger.info(f"[USERS]   • Role: {user.role}")
        
        if user.group_id is not None:
            if not validate_group_exists(cursor, user.group_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Grupo com ID {user.group_id} não encontrado"
                )
            updates.append("group_id = %s")
            params.append(user.group_id)
            logger.info(f"[USERS]   • Grupo: {user.group_id}")
        
        if user.is_active is not None:
            updates.append("is_active = %s")
            params.append(user.is_active)
            logger.info(f"[USERS]   • Status: {'Ativo' if user.is_active else 'Inativo'}")
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum campo fornecido para atualizar"
            )
        
        update_query = f"""
            UPDATE users
            SET {', '.join(updates)}
            WHERE id = %s
        """
        
        params.append(user_id)
        cursor.execute(update_query, params)
        conn.commit()
        
        logger.info(f"[USERS] ✓ SUCESSO!")
        
        cursor.execute(
            """SELECT id, name, email, username, role, group_id, is_active, created_at 
               FROM users WHERE id = %s""",
            (user_id,)
        )
        updated_user = cursor.fetchone()
        updated_user = convert_datetime_to_string(updated_user)
        
        logger.info("=" * 90 + "\n")
        
        return updated_user
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[USERS] ✗ ERRO: {str(err)}")
        logger.error("=" * 90 + "\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar usuário: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@users_router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar usuário",
    description="Remove um usuário do sistema"
)
async def delete_user(user_id: int):
    """🗑️ Deleta um usuário do sistema"""
    logger.info(f"\n[USERS] 🗑️ DELETANDO USUÁRIO #{user_id}...")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT name, email FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            logger.warning(f"[USERS] ✗ Usuário #{user_id} não encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuário com ID {user_id} não encontrado"
            )
        
        logger.info(f"[USERS] ✓ Deletando: {user['name']}")
        
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        
        logger.info(f"[USERS] ✓ DELETADO COM SUCESSO!\n")
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[USERS] ✗ ERRO: {str(err)}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar usuário: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# =========================================
# ❤️ HEALTH CHECK
# =========================================

@app.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health Check",
    description="Verifica se a API está funcionando"
)
async def health():
    """❤️ Verifica a saúde da API"""
    db_status = "✓ OK"
    try:
        conn = get_db_connection()
        conn.close()
    except:
        db_status = "✗ ERRO"
    
    return {
        "status": "ok",
        "api": "CPE Control API",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "database": db_status
    }


# =========================================
# REGISTRAR ROUTERS
# =========================================

app.include_router(groups_router)
app.include_router(users_router)

logger.info("✅ Routers registrados com sucesso!")
logger.info("   • Router de Grupos: /api/groups")
logger.info("   • Router de Usuários: /api/users\n")

# =========================================
# MAIN - INICIALIZAR SERVIDOR
# =========================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("\n" + "=" * 90)
    logger.info("🚀 INICIANDO CPE CONTROL API v2.0.0")
    logger.info("=" * 90)
    logger.info("🌐 Servidor: http://localhost:8000")
    logger.info("🔧 IP Local: http://127.0.0.1:8000")
    logger.info("📚 Documentação: http://localhost:8000/docs")
    logger.info("⚠️  SEM AUTENTICAÇÃO - Acesso público total!")
    logger.info("=" * 90 + "\n")
    
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )