"""
CPE Control API - Aplicacao Principal
Gerenciamento de Usuarios com Vinculacao de Grupos e Autenticacao com Bcrypt
"""

# =========================================
# 1. IMPORTS
# =========================================
from fastapi import FastAPI, HTTPException, APIRouter, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import mysql.connector
import logging
import uvicorn
import bcrypt
from contextlib import asynccontextmanager
from datetime import datetime

# =========================================
# 2. CONFIGURAR LOGGING (PRIMEIRO!)
# =========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =========================================
# 3. CONFIGURACAO DO BANCO DE DADOS
# =========================================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "cpe_plus",
}

logger.info("=" * 90)
logger.info("CONFIGURACAO DE BANCO DE DADOS")
logger.info("=" * 90)
logger.info(f"Host: {DB_CONFIG['host']}")
logger.info(f"User: {DB_CONFIG['user']}")
logger.info(f"Database: {DB_CONFIG['database']}")
logger.info("=" * 90 + "\n")

# =========================================
# 4. FUNCOES DE BANCO DE DADOS
# =========================================

# [INICIO] get_db_connection()
def get_db_connection():
    """Estabelece conexao com o banco de dados"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
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
# [FIM] get_db_connection()

# Testar conexao ao iniciar
try:
    logger.info("[DB] Testando conexao com o banco de dados...")
    test_conn = get_db_connection()
    test_cursor = test_conn.cursor()
    test_cursor.execute("SELECT VERSION()")
    version = test_cursor.fetchone()
    logger.info(f"[DB] MySQL version: {version[0]}")
    test_cursor.close()
    test_conn.close()
except Exception as err:
    logger.error(f"[DB] FALHA NA CONEXAO: {str(err)}")

# =========================================
# 5. MODELOS PYDANTIC
# =========================================

# --- USUARIOS ---
class UserBase(BaseModel):
    """Modelo base de usuario"""
    name: str = Field(..., min_length=3, max_length=255, description="Nome completo")
    email: EmailStr = Field(..., description="Email do usuario")
    username: str = Field(..., min_length=3, max_length=100, description="Nome de usuario")
    role: str = Field(default="USER", pattern="^(USER|ADMIN|MANAGER|TI)$", description="Papel do usuario")
    group_id: Optional[int] = Field(None, description="ID do grupo vinculado")
    is_active: bool = Field(True, description="Status do usuario")

class UserCreate(UserBase):
    """Modelo para criar usuario"""
    password: str = Field(..., min_length=8, description="Senha do usuario (min 8 caracteres)")

class UserUpdate(BaseModel):
    """Modelo para atualizar usuario"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    role: Optional[str] = Field(None, pattern="^(USER|ADMIN|MANAGER|TI)$")
    group_id: Optional[int] = None
    is_active: Optional[bool] = None

# [INICIO] class UserResponse
class UserResponse(BaseModel):
    """Modelo de resposta do usuario"""
    id: int
    name: str
    email: str
    username: Optional[str] = None
    role: str
    group_id: Optional[int] = None
    is_active: bool
    created_at: Optional[str] = None
# [FIM] class UserResponse

# --- GRUPOS ---
class GroupBase(BaseModel):
    """Modelo base de grupo"""
    name: str = Field(..., min_length=3, max_length=255, description="Nome do grupo")
    description: Optional[str] = Field(None, max_length=500, description="Descricao do grupo")

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

# --- AUTENTICACAO ---
# [INICIO] class LoginRequest
class LoginRequest(BaseModel):
    """Modelo para requisicao de login"""
    credential: str = Field(..., min_length=3, description="Email ou username")
    password: str = Field(..., min_length=6, description="Senha do usuario")
# [FIM] class LoginRequest

class LoginResponse(BaseModel):
    """Modelo para resposta de login"""
    success: bool
    message: str
    user: UserResponse

# --- HEALTH CHECK ---
class HealthCheckResponse(BaseModel):
    """Modelo para health check"""
    status: str
    api: str
    version: str
    timestamp: str
    database: Optional[str] = None

# =========================================
# 6. FUNCOES UTILITARIAS
# =========================================

# [INICIO] get_db_or_404()
def get_db_or_404():
    """Obtem conexao ou lanca erro 500"""
    try:
        return get_db_connection()
    except Exception as err:
        logger.error(f"[DB] Erro ao conectar ao banco: {str(err)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao conectar ao banco de dados"
        )
# [FIM] get_db_or_404()

# [INICIO] convert_datetime_to_string()
def convert_datetime_to_string(obj: dict) -> dict:
    """Converte datetime para string ISO em um dicionario"""
    if not obj:
        return obj
    
    try:
        if 'created_at' in obj and obj['created_at']:
            if hasattr(obj['created_at'], 'isoformat'):
                obj['created_at'] = obj['created_at'].isoformat()
        return obj
    except Exception as err:
        logger.error(f"[CONVERT] Erro ao converter: {str(err)}")
        return obj
# [FIM] convert_datetime_to_string()

# [INICIO] convert_datetime_list()
def convert_datetime_list(objects: list) -> list:
    """Converte datetime para string ISO em lista"""
    return [convert_datetime_to_string(obj) for obj in objects]
# [FIM] convert_datetime_list()

# [INICIO] validate_group_exists()
def validate_group_exists(cursor, group_id: int) -> bool:
    """Valida se um grupo existe"""
    try:
        cursor.execute("SELECT id FROM password_groups WHERE id = %s", (group_id,))
        return cursor.fetchone() is not None
    except Exception as err:
        logger.error(f"[VALIDATE] Erro ao validar grupo: {str(err)}")
        return False
# [FIM] validate_group_exists()

# [INICIO] validate_email_unique()
def validate_email_unique(cursor, email: str, exclude_user_id: Optional[int] = None) -> bool:
    """Valida se um email e unico"""
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
        logger.error(f"[VALIDATE] Erro ao validar email: {str(err)}")
        return False
# [FIM] validate_email_unique()

# [INICIO] validate_username_unique()
def validate_username_unique(cursor, username: str, exclude_user_id: Optional[int] = None) -> bool:
    """Valida se um username e unico"""
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
        logger.error(f"[VALIDATE] Erro ao validar username: {str(err)}")
        return False
# [FIM] validate_username_unique()

# =========================================
# 7. LIFESPAN - EVENTOS DE CICLO DE VIDA
# =========================================

# [INICIO] lifespan()
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicacao"""
    # ===== STARTUP =====
    logger.info("\n" + "=" * 90)
    logger.info("CPE CONTROL API v2.0.0 INICIADA COM SUCESSO")
    logger.info("=" * 90)
    logger.info("\nENDPOINTS DISPONIVEIS:")
    logger.info("   " + "-" * 80)
    logger.info("   POST   /api/auth/login                   -> Login do usuario")
    logger.info("   GET    /api/groups                       -> Listar grupos")
    logger.info("   GET    /api/groups/{id}                  -> Obter grupo especifico")
    logger.info("   POST   /api/groups                       -> Criar novo grupo")
    logger.info("   PUT    /api/groups/{id}                  -> Atualizar grupo")
    logger.info("   DELETE /api/groups/{id}                  -> Deletar grupo")
    logger.info("   GET    /api/users                        -> Listar usuarios")
    logger.info("   GET    /api/users/{id}                   -> Obter usuario especifico")
    logger.info("   POST   /api/users                        -> Criar novo usuario")
    logger.info("   PUT    /api/users/{id}                   -> Atualizar usuario")
    logger.info("   DELETE /api/users/{id}                   -> Deletar usuario")
    logger.info("   GET    /health                           -> Verificar saude da API")
    logger.info("   " + "-" * 80)
    logger.info("\nDOCUMENTACAO:")
    logger.info("   - Swagger UI: http://localhost:8000/docs")
    logger.info("   - ReDoc: http://localhost:8000/redoc")
    logger.info("\n" + "=" * 90 + "\n")
    
    yield
    
    # ===== SHUTDOWN =====
    logger.info("\n" + "=" * 90)
    logger.info("CPE CONTROL API DESLIGADA COM SUCESSO")
    logger.info("=" * 90 + "\n")
# [FIM] lifespan()

# =========================================
# 8. CRIAR APLICACAO FASTAPI
# =========================================

app = FastAPI(
    title="CPE Control API",
    version="2.0.0",
    description="Sistema de Gerenciamento de Usuarios com Vinculacao de Grupos",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# =========================================
# 9. MIDDLEWARE: CORS
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

logger.info("CORS CONFIGURADO COM SUCESSO!\n")

# =========================================
# 10. ROUTER DE AUTENTICACAO
# =========================================

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

# [INICIO] POST /api/auth/login
@auth_router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login do Usuario",
    description="Autentica um usuario usando email ou username e senha"
)
async def login(login_data: LoginRequest):
    """Realiza login do usuario com validacao de senha usando bcrypt"""
    logger.info("\n" + "=" * 90)
    logger.info("[AUTH] TENTATIVA DE LOGIN")
    logger.info("=" * 90)
    logger.info(f"[AUTH]   - Credencial: {login_data.credential}")
    logger.info("=" * 90)

    credential = login_data.credential.strip()
    password = login_data.password.strip()

    if not credential:
        logger.warning("[AUTH] Credencial vazia")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credencial invalida"
        )

    if not password:
        logger.warning("[AUTH] Senha vazia")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha invalida"
        )

    conn = None
    cursor = None

    try:
        logger.info("[AUTH] Conectando ao banco de dados...")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        logger.info("[AUTH] Conexao estabelecida")

        logger.info("[AUTH] Identificando tipo de credencial...")
        is_email = "@" in credential

        if is_email:
            logger.info("[AUTH]   - Tipo: EMAIL")
            query = """
                SELECT id, name, email, username, role, group_id, is_active, created_at, password_hash
                FROM users
                WHERE email = %s AND is_active = TRUE
                LIMIT 1
            """
        else:
            logger.info("[AUTH]   - Tipo: USERNAME")
            query = """
                SELECT id, name, email, username, role, group_id, is_active, created_at, password_hash
                FROM users
                WHERE username = %s AND is_active = TRUE
                LIMIT 1
            """

        logger.info(f"[AUTH] Executando query para: {credential}")
        cursor.execute(query, (credential,))
        user = cursor.fetchone()

        if not user:
            logger.warning(f"[AUTH] Usuario nao encontrado: {credential}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email/username ou senha invalidos"
            )

        logger.info(f"[AUTH] Usuario encontrado!")
        logger.info(f"[AUTH]   - ID: {user['id']}")
        logger.info(f"[AUTH]   - Nome: {user['name']}")
        logger.info(f"[AUTH]   - Email: {user['email']}")
        logger.info(f"[AUTH]   - Username: {user['username'] or 'N/A'}")
        logger.info(f"[AUTH]   - Role: {user['role']}")
        logger.info(f"[AUTH]   - Grupo: {user['group_id'] or 'Nao vinculado'}")
        logger.info(f"[AUTH]   - Status: {'Ativo' if user['is_active'] else 'Inativo'}")

        logger.info("[AUTH] Validando senha com bcrypt...")
        password_hash = user.get('password_hash')

        if not password_hash:
            logger.warning("[AUTH] Usuario nao tem senha definida")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email/username ou senha invalidos"
            )

        try:
            senha_valida = bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception as err:
            logger.error(f"[AUTH] Erro ao validar hash: {str(err)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email/username ou senha invalidos"
            )

        if not senha_valida:
            logger.warning(f"[AUTH] Senha incorreta para: {credential}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email/username ou senha invalidos"
            )

        logger.info("[AUTH] Senha validada com sucesso!")

        logger.info("[AUTH] Validando dados do usuario...")
        
        if not user.get('username'):
            logger.warning(f"[AUTH] Username e NULL, usando email como fallback")
            user['username'] = user['email']
        
        if not user.get('name'):
            logger.warning(f"[AUTH] Name e NULL, usando email como fallback")
            user['name'] = user['email']
        
        if not user.get('role'):
            logger.warning(f"[AUTH] Role e NULL, usando 'USER' como padrao")
            user['role'] = 'USER'

        logger.info("[AUTH] Validacao concluida")

        logger.info("[AUTH] Convertendo dados de datetime...")
        user = convert_datetime_to_string(user)
        logger.info(f"[AUTH]   - created_at: {user.get('created_at', 'N/A')}")

        if 'password_hash' in user:
            del user['password_hash']

        logger.info("[AUTH] Construindo resposta...")
        
        try:
            user_response = UserResponse(**user)
            logger.info("[AUTH] UserResponse criado com sucesso")
        except Exception as validation_err:
            logger.error(f"[AUTH] ERRO DE VALIDACAO: {str(validation_err)}")
            logger.error(f"[AUTH]    - Dados do usuario: {user}")
            raise
        
        logger.info("[AUTH] LOGIN BEM-SUCEDIDO!")
        logger.info("=" * 90 + "\n")

        return LoginResponse(
            success=True,
            message=f"Bem-vindo, {user['name']}!",
            user=user_response
        )

    except HTTPException as http_err:
        logger.error(f"[AUTH] HTTP Error: {http_err.detail}")
        logger.error("=" * 90 + "\n")
        raise

    except Exception as err:
        logger.error(f"[AUTH] ERRO INESPERADO!")
        logger.error(f"[AUTH]    - Tipo: {type(err).__name__}")
        logger.error(f"[AUTH]    - Mensagem: {str(err)}")
        logger.error("[AUTH]    - Stack trace:")
        import traceback
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                logger.error(f"[AUTH]      {line}")
        logger.error("=" * 90 + "\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar login: {str(err)}"
        )

    finally:
        if cursor:
            try:
                cursor.close()
                logger.debug("[AUTH] Cursor fechado")
            except Exception as err:
                logger.warning(f"[AUTH] Erro ao fechar cursor: {str(err)}")
        
        if conn:
            try:
                conn.close()
                logger.debug("[AUTH] Conexao fechada")
            except Exception as err:
                logger.warning(f"[AUTH] Erro ao fechar conexao: {str(err)}")
# [FIM] POST /api/auth/login

# =========================================
# 11. ROUTER DE GRUPOS
# =========================================

groups_router = APIRouter(prefix="/api/groups", tags=["groups"])

# [INICIO] GET /api/groups
@groups_router.get(
    "/",
    response_model=list,
    summary="Listar grupos",
    description="Obtem lista completa de todos os grupos cadastrados"
)
async def get_groups():
    """Obtem todos os grupos"""
    logger.info("\n" + "=" * 90)
    logger.info("[GROUPS] Listando todos os grupos...")
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
        
        logger.info(f"[GROUPS] {len(groups)} grupo(s) encontrado(s)")
        logger.info("=" * 90 + "\n")
        
        return groups or []
        
    except Exception as err:
        logger.error(f"[GROUPS] Erro: {str(err)}")
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
# [FIM] GET /api/groups

# [INICIO] GET /api/groups/{group_id}
@groups_router.get(
    "/{group_id}",
    response_model=GroupResponse,
    summary="Obter grupo",
    description="Obtem informacoes detalhadas de um grupo especifico"
)
async def get_group(group_id: int):
    """Obtem um grupo especifico pelo ID"""
    logger.info(f"\n[GROUPS] Obtendo grupo #{group_id}...")
    
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
            logger.warning(f"[GROUPS] Grupo #{group_id} nao encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo com ID {group_id} nao encontrado"
            )
        
        group = convert_datetime_to_string(group)
        logger.info(f"[GROUPS] Grupo encontrado: {group['name']}\n")
        return group
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[GROUPS] Erro: {str(err)}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter grupo: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
# [FIM] GET /api/groups/{group_id}

# [INICIO] POST /api/groups
@groups_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=GroupResponse,
    summary="Criar grupo",
    description="Cria um novo grupo"
)
async def create_group(group: GroupCreate):
    """Cria um novo grupo"""
    logger.info("\n" + "=" * 90)
    logger.info("[GROUPS] CRIANDO NOVO GRUPO")
    logger.info("=" * 90)
    logger.info(f"[GROUPS]   - Nome: {group.name}")
    
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
        logger.info(f"[GROUPS] Grupo criado com ID: {new_group_id}")
        
        cursor.execute(
            """SELECT id, name, created_at 
               FROM password_groups WHERE id = %s""",
            (new_group_id,)
        )
        new_group = cursor.fetchone()
        new_group = convert_datetime_to_string(new_group)
        
        logger.info("[GROUPS] SUCESSO!")
        logger.info("=" * 90 + "\n")
        
        return new_group
        
    except Exception as err:
        logger.error(f"[GROUPS] ERRO: {str(err)}")
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
# [FIM] POST /api/groups

# [INICIO] PUT /api/groups/{group_id}
@groups_router.put(
    "/{group_id}",
    response_model=GroupResponse,
    summary="Atualizar grupo",
    description="Atualiza dados de um grupo"
)
async def update_group(group_id: int, group: GroupUpdate):
    """Atualiza um grupo"""
    logger.info("\n" + "=" * 90)
    logger.info(f"[GROUPS] ATUALIZANDO GRUPO #{group_id}")
    logger.info("=" * 90)
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id FROM password_groups WHERE id = %s", (group_id,))
        if not cursor.fetchone():
            logger.warning(f"[GROUPS] Grupo #{group_id} nao encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo com ID {group_id} nao encontrado"
            )
        
        updates = []
        params = []
        
        if group.name is not None:
            updates.append("name = %s")
            params.append(group.name)
            logger.info(f"[GROUPS]   - Nome: {group.name}")
        
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
        
        logger.info(f"[GROUPS] SUCESSO!")
        
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
        logger.error(f"[GROUPS] ERRO: {str(err)}")
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
# [FIM] PUT /api/groups/{group_id}

# [INICIO] DELETE /api/groups/{group_id}
@groups_router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar grupo",
    description="Remove um grupo do sistema"
)
async def delete_group(group_id: int):
    """Deleta um grupo do sistema"""
    logger.info(f"\n[GROUPS] DELETANDO GRUPO #{group_id}...")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT name FROM password_groups WHERE id = %s", (group_id,))
        group = cursor.fetchone()
        
        if not group:
            logger.warning(f"[GROUPS] Grupo #{group_id} nao encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo com ID {group_id} nao encontrado"
            )
        
        logger.info(f"[GROUPS] Deletando: {group['name']}")
        
        cursor.execute("DELETE FROM password_groups WHERE id = %s", (group_id,))
        conn.commit()
        
        logger.info(f"[GROUPS] DELETADO COM SUCESSO!\n")
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[GROUPS] ERRO: {str(err)}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar grupo: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
# [FIM] DELETE /api/groups/{group_id}

# =========================================
# 12. ROUTER DE USUARIOS
# =========================================

users_router = APIRouter(prefix="/api/users", tags=["users"])

# [INICIO] GET /api/users
@users_router.get(
    "/",
    response_model=list,
    summary="Listar usuarios",
    description="Obtem lista completa de todos os usuarios cadastrados"
)
async def get_users():
    """Obtem todos os usuarios"""
    logger.info("\n" + "=" * 90)
    logger.info("[USERS] Listando todos os usuarios...")
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
        
        logger.info(f"[USERS] {len(users)} usuario(s) encontrado(s)")
        logger.info("=" * 90 + "\n")
        
        return users or []
        
    except Exception as err:
        logger.error(f"[USERS] Erro: {str(err)}")
        logger.error("=" * 90 + "\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar usuarios: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
# [FIM] GET /api/users

# [INICIO] GET /api/users/{user_id}
@users_router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Obter usuario",
    description="Obtem informacoes detalhadas de um usuario especifico"
)
async def get_user(user_id: int):
    """Obtem um usuario especifico pelo ID"""
    logger.info(f"\n[USERS] Obtendo usuario #{user_id}...")
    
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
            logger.warning(f"[USERS] Usuario #{user_id} nao encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario com ID {user_id} nao encontrado"
            )
        
        user = convert_datetime_to_string(user)
        logger.info(f"[USERS] Usuario encontrado: {user['name']}\n")
        return user
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[USERS] Erro: {str(err)}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter usuario: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
# [FIM] GET /api/users/{user_id}

# [INICIO] POST /api/users
@users_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    summary="Criar usuario",
    description="Cria um novo usuario com vinculacao a um grupo"
)
async def create_user(user: UserCreate):
    """Cria um novo usuario"""
    logger.info("\n" + "=" * 90)
    logger.info("[USERS] CRIANDO NOVO USUARIO")
    logger.info("=" * 90)
    logger.info(f"[USERS]   - Nome: {user.name}")
    logger.info(f"[USERS]   - Email: {user.email}")
    logger.info(f"[USERS]   - Username: {user.username}")
    logger.info(f"[USERS]   - Senha: {'*' * len(user.password)}")
    logger.info(f"[USERS]   - Role: {user.role}")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        if not validate_email_unique(cursor, user.email):
            logger.warning(f"[USERS] Email ja registrado: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{user.email}' ja esta registrado"
            )
        
        if not validate_username_unique(cursor, user.username):
            logger.warning(f"[USERS] Username ja registrado: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{user.username}' ja esta registrado"
            )
        
        if user.group_id:
            if not validate_group_exists(cursor, user.group_id):
                logger.warning(f"[USERS] Grupo #{user.group_id} nao encontrado")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Grupo com ID {user.group_id} nao encontrado"
                )
        
        logger.info("[USERS] Gerando hash da senha com bcrypt...")
        try:
            password_hash = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            logger.info("[USERS]   - Hash gerado com sucesso")
        except Exception as hash_err:
            logger.error(f"[USERS] Erro ao gerar hash: {str(hash_err)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao processar senha: {str(hash_err)}"
            )
        
        insert_query = """
            INSERT INTO users (name, email, username, password_hash, role, group_id, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (
            user.name,
            user.email,
            user.username,
            password_hash,
            user.role,
            user.group_id,
            user.is_active
        ))
        
        conn.commit()
        new_user_id = cursor.lastrowid
        logger.info(f"[USERS] Usuario criado com ID: {new_user_id}")
        
        cursor.execute(
            """SELECT id, name, email, username, role, group_id, is_active, created_at 
               FROM users WHERE id = %s""",
            (new_user_id,)
        )
        new_user = cursor.fetchone()
        new_user = convert_datetime_to_string(new_user)
        
        logger.info("[USERS] SUCESSO!")
        logger.info("=" * 90 + "\n")
        
        return new_user
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[USERS] ERRO: {str(err)}")
        logger.error("=" * 90 + "\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar usuario: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
# [FIM] POST /api/users

# [INICIO] PUT /api/users/{user_id}
@users_router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Atualizar usuario",
    description="Atualiza dados de um usuario"
)
async def update_user(user_id: int, user: UserUpdate):
    """Atualiza um usuario"""
    logger.info("\n" + "=" * 90)
    logger.info(f"[USERS] ATUALIZANDO USUARIO #{user_id}")
    logger.info("=" * 90)
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            logger.warning(f"[USERS] Usuario #{user_id} nao encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario com ID {user_id} nao encontrado"
            )
        
        updates = []
        params = []
        
        if user.name is not None:
            updates.append("name = %s")
            params.append(user.name)
            logger.info(f"[USERS]   - Nome: {user.name}")
        
        if user.email is not None:
            if not validate_email_unique(cursor, user.email, exclude_user_id=user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email '{user.email}' ja esta registrado"
                )
            updates.append("email = %s")
            params.append(user.email)
            logger.info(f"[USERS]   - Email: {user.email}")
        
        if user.username is not None:
            if not validate_username_unique(cursor, user.username, exclude_user_id=user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Username '{user.username}' ja esta registrado"
                )
            updates.append("username = %s")
            params.append(user.username)
            logger.info(f"[USERS]   - Username: {user.username}")
        
        if user.role is not None:
            updates.append("role = %s")
            params.append(user.role)
            logger.info(f"[USERS]   - Role: {user.role}")
        
        if user.group_id is not None:
            if not validate_group_exists(cursor, user.group_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Grupo com ID {user.group_id} nao encontrado"
                )
            updates.append("group_id = %s")
            params.append(user.group_id)
            logger.info(f"[USERS]   - Grupo: {user.group_id}")
        
        if user.is_active is not None:
            updates.append("is_active = %s")
            params.append(user.is_active)
            logger.info(f"[USERS]   - Status: {'Ativo' if user.is_active else 'Inativo'}")
        
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
        
        logger.info(f"[USERS] SUCESSO!")
        
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
        logger.error(f"[USERS] ERRO: {str(err)}")
        logger.error("=" * 90 + "\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar usuario: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
# [FIM] PUT /api/users/{user_id}

# [INICIO] DELETE /api/users/{user_id}
@users_router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar usuario",
    description="Remove um usuario do sistema"
)
async def delete_user(user_id: int):
    """Deleta um usuario do sistema"""
    logger.info(f"\n[USERS] DELETANDO USUARIO #{user_id}...")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT name, email FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            logger.warning(f"[USERS] Usuario #{user_id} nao encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario com ID {user_id} nao encontrado"
            )
        
        logger.info(f"[USERS] Deletando: {user['name']}")
        
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        
        logger.info(f"[USERS] DELETADO COM SUCESSO!\n")
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[USERS] ERRO: {str(err)}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar usuario: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
# [FIM] DELETE /api/users/{user_id}

# =========================================
# 13. HEALTH CHECK
# =========================================

# [INICIO] GET /health
@app.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health Check",
    description="Verifica se a API esta funcionando"
)
async def health():
    """Verifica a saude da API"""
    db_status = "OK"
    try:
        conn = get_db_connection()
        conn.close()
    except:
        db_status = "ERRO"
    
    return {
        "status": "ok",
        "api": "CPE Control API",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "database": db_status
    }
# [FIM] GET /health

# =========================================
# 14. REGISTRAR ROUTERS
# =========================================

app.include_router(auth_router)
app.include_router(groups_router)
app.include_router(users_router)

logger.info("Routers registrados com sucesso!")
logger.info("   - Router de Autenticacao: /api/auth")
logger.info("   - Router de Grupos: /api/groups")
logger.info("   - Router de Usuarios: /api/users\n")

# =========================================
# 15. MAIN - INICIALIZAR SERVIDOR
# =========================================

if __name__ == "__main__":
    logger.info("\n" + "=" * 90)
    logger.info("INICIANDO CPE CONTROL API v2.0.0")
    logger.info("=" * 90)
    logger.info("Servidor: http://localhost:8000")
    logger.info("IP Local: http://127.0.0.1:8000")
    logger.info("Documentacao: http://localhost:8000/docs")
    logger.info("=" * 90 + "\n")
    
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )