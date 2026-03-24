"""
CPE Control API - Aplicacao Principal
Gerenciamento de Usuarios, Grupos, Tickets e Notificacoes com Autenticacao Bcrypt
"""

# =========================================
# 1. IMPORTACOES
# =========================================
from fastapi import FastAPI, HTTPException, APIRouter, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import mysql.connector
import logging
import uvicorn
import bcrypt
import hashlib
import time
from contextlib import asynccontextmanager
from datetime import datetime

# =========================================
# 2. CONFIGURAR LOGGING
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


# Testar conexao ao iniciar
try:
    logger.info("[DB] Testando conexao com o banco de dados...")
    test_conn = get_db_connection()
    test_cursor = test_conn.cursor()
    test_cursor.execute("SELECT VERSION()")
    version = test_cursor.fetchone()
    logger.info(f"[DB] ✅ MySQL version: {version[0]}")
    test_cursor.close()
    test_conn.close()
except Exception as err:
    logger.error(f"[DB] ❌ FALHA NA CONEXAO: {str(err)}")

# =========================================
# 5. MODELOS PYDANTIC
# =========================================

# --- USUARIOS ---
class UserBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    email: EmailStr = Field(...)
    username: str = Field(..., min_length=3, max_length=100)
    role: str = Field(default="USER", pattern="^(USER|ADMIN|MANAGER|TI)$")
    group_id: Optional[int] = None
    is_active: bool = Field(True)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    role: Optional[str] = Field(None, pattern="^(USER|ADMIN|MANAGER|TI)$")
    group_id: Optional[int] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    username: Optional[str] = None
    role: str
    group_id: Optional[int] = None
    is_active: bool
    created_at: Optional[str] = None

# --- GRUPOS ---
class GroupBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=500)

class GroupCreate(GroupBase):
    pass

class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=500)

class GroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: Optional[str] = None

# --- AUTENTICACAO ---
class LoginRequest(BaseModel):
    credential: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)

class LoginResponse(BaseModel):
    success: bool
    message: str
    user: UserResponse
    access_token: str
    token_type: str = Field(default="bearer")

# --- NOTIFICACOES ---
class NotificacaoCreate(BaseModel):
    ticket_id: int = Field(...)
    usuario_id: int = Field(...)
    mensagem: str = Field(..., min_length=1)
    tipo: str = Field(default="info")
    lido: Optional[bool] = Field(False)

class NotificacaoUpdate(BaseModel):
    lido: Optional[bool] = None
    mensagem: Optional[str] = None

class NotificacaoResponse(BaseModel):
    id: int
    ticket_id: int
    usuario_id: int
    mensagem: str
    tipo: str
    lido: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

# --- HEALTH CHECK ---
class HealthCheckResponse(BaseModel):
    status: str
    api: str
    version: str
    timestamp: str
    database: Optional[str] = None

# --- TICKETS ---
class TicketCreate(BaseModel):
    assunto: str = Field(..., min_length=5)
    descricao_inicial: str = Field(..., min_length=10)
    solicitante_id: int = Field(...)
    responsavel_id: Optional[int] = None
    group_id: Optional[int] = None
    categoria_id: Optional[int] = None
    prioridade_id: int = Field(default=2)
    origem: Optional[str] = None

class TicketUpdate(BaseModel):
    assunto: Optional[str] = Field(None, min_length=5)
    descricao_inicial: Optional[str] = Field(None, min_length=10)
    responsavel_id: Optional[int] = None
    group_id: Optional[int] = None
    categoria_id: Optional[int] = None
    status_id: Optional[int] = None
    prioridade_id: Optional[int] = None

class TicketResponse(BaseModel):
    id: int
    numero: str
    assunto: str
    solicitante_id: int
    responsavel_id: Optional[int] = None
    group_id: Optional[int] = None
    status_id: int
    prioridade_id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

# --- INTERACOES DE TICKET ---
class TicketInteracaoCreate(BaseModel):
    ticket_id: int = Field(...)
    usuario_id: int = Field(...)
    mensagem: str = Field(..., min_length=1)
    tipo: str = Field(default="resposta")
    publico: int = Field(default=1)

class TicketInteracaoResponse(BaseModel):
    id: int
    ticket_id: int
    usuario_id: int
    mensagem: str
    tipo: str
    publico: int
    created_at: Optional[str] = None

# =========================================
# 6. FUNCOES UTILITARIAS
# =========================================

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

def convert_datetime_to_string(obj: dict) -> dict:
    """Converte datetime para string ISO em um dicionario"""
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
        logger.error(f"[CONVERT] Erro ao converter: {str(err)}")
        return obj

def convert_datetime_list(objects: list) -> list:
    """Converte datetime para string ISO em lista"""
    return [convert_datetime_to_string(obj) for obj in objects]

def validate_group_exists(cursor, group_id: int) -> bool:
    """Valida se um grupo existe"""
    try:
        cursor.execute("SELECT id FROM password_groups WHERE id = %s", (group_id,))
        return cursor.fetchone() is not None
    except Exception as err:
        logger.error(f"[VALIDATE] Erro ao validar grupo: {str(err)}")
        return False

def validate_email_unique(cursor, email: str, exclude_user_id: Optional[int] = None) -> bool:
    """Valida se um email e unico"""
    try:
        if exclude_user_id:
            cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", (email, exclude_user_id))
        else:
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        return cursor.fetchone() is None
    except Exception as err:
        logger.error(f"[VALIDATE] Erro ao validar email: {str(err)}")
        return False

def validate_username_unique(cursor, username: str, exclude_user_id: Optional[int] = None) -> bool:
    """Valida se um username e unico"""
    try:
        if exclude_user_id:
            cursor.execute("SELECT id FROM users WHERE username = %s AND id != %s", (username, exclude_user_id))
        else:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        return cursor.fetchone() is None
    except Exception as err:
        logger.error(f"[VALIDATE] Erro ao validar username: {str(err)}")
        return False

def gerar_numero_ticket(cursor) -> str:
    """Gera numero unico para ticket formato YYYY-XXXXX"""
    try:
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
    """Mapeia dados do ticket com informacoes relacionadas"""
    try:
        # Buscar nome do solicitante
        cursor.execute("SELECT name, email FROM users WHERE id = %s", (ticket['solicitante_id'],))
        solicitante = cursor.fetchone()
        
        # Buscar nome do responsavel
        responsavel = None
        if ticket['responsavel_id']:
            cursor.execute("SELECT name FROM users WHERE id = %s", (ticket['responsavel_id'],))
            responsavel = cursor.fetchone()
        
        # Buscar nome do grupo
        grupo = None
        if ticket['group_id']:
            cursor.execute("SELECT name FROM password_groups WHERE id = %s", (ticket['group_id'],))
            grupo = cursor.fetchone()
        
        return {
            **ticket,
            "solicitante_nome": solicitante['name'] if solicitante else "Desconhecido",
            "solicitante_email": solicitante['email'] if solicitante else "sem-email",
            "responsavel_nome": responsavel['name'] if responsavel else "Nao atribuido",
            "group_name": grupo['name'] if grupo else "Sem setor"
        }
    
    except Exception as err:
        logger.error(f"[MAPA] Erro ao mapear dados: {str(err)}")
        return ticket

# =========================================
# 7. LIFESPAN - EVENTOS DE CICLO DE VIDA
# =========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicacao"""
    # ===== STARTUP =====
    logger.info("\n" + "=" * 90)
    logger.info("✅ CPE CONTROL API v2.0.0 INICIADA COM SUCESSO")
    logger.info("=" * 90)
    logger.info("\n📋 ENDPOINTS DISPONIVEIS:")
    logger.info("   " + "-" * 80)
    logger.info("   [AUTH]")
    logger.info("   POST   /api/auth/login                      -> Login do usuario")
    logger.info("   ")
    logger.info("   [GRUPOS]")
    logger.info("   GET    /api/groups                          -> Listar grupos")
    logger.info("   GET    /api/groups/{id}                     -> Obter grupo especifico")
    logger.info("   POST   /api/groups                          -> Criar novo grupo")
    logger.info("   PUT    /api/groups/{id}                     -> Atualizar grupo")
    logger.info("   DELETE /api/groups/{id}                     -> Deletar grupo")
    logger.info("   ")
    logger.info("   [USUARIOS]")
    logger.info("   GET    /api/users                           -> Listar usuarios")
    logger.info("   GET    /api/users/{id}                      -> Obter usuario especifico")
    logger.info("   POST   /api/users                           -> Criar novo usuario")
    logger.info("   PUT    /api/users/{id}                      -> Atualizar usuario")
    logger.info("   DELETE /api/users/{id}                      -> Deletar usuario")
    logger.info("   ")
    logger.info("   [TICKETS]")
    logger.info("   GET    /api/tickets                         -> Listar tickets")
    logger.info("   GET    /api/tickets/{id}                    -> Obter ticket especifico")
    logger.info("   POST   /api/tickets                         -> Criar novo ticket")
    logger.info("   PUT    /api/tickets/{id}                    -> Atualizar ticket")
    logger.info("   DELETE /api/tickets/{id}                    -> Deletar ticket")
    logger.info("   ")
    logger.info("   [INTERACOES]")
    logger.info("   GET    /api/ticket-interacoes/{ticket_id}   -> Listar comentarios")
    logger.info("   POST   /api/ticket-interacoes               -> Criar comentario/resposta")
    logger.info("   ")
    logger.info("   [NOTIFICACOES]")
    logger.info("   GET    /api/notificacoes                    -> Listar notificacoes")
    logger.info("   POST   /api/notificacoes                    -> Criar notificacao")
    logger.info("   GET    /api/notificacoes/nao-lidas/{id}     -> Contar nao lidas")
    logger.info("   PUT    /api/notificacoes/{id}               -> Marcar como lida")
    logger.info("   DELETE /api/notificacoes/{id}               -> Deletar notificacao")
    logger.info("   ")
    logger.info("   [HEALTH]")
    logger.info("   GET    /health                              -> Verificar saude da API")
    logger.info("   " + "-" * 80)
    logger.info("\n📚 DOCUMENTACAO:")
    logger.info("   🌐 Swagger UI: http://localhost:8000/docs")
    logger.info("   🌐 ReDoc: http://localhost:8000/redoc")
    logger.info("\n🌐 SERVIDOR:")
    logger.info("   HTTP: http://localhost:8000")
    logger.info("   HTTP: http://127.0.0.1:8000")
    logger.info("\n" + "=" * 90 + "\n")
    
    yield
    
    # ===== SHUTDOWN =====
    logger.info("\n" + "=" * 90)
    logger.info("🛑 CPE CONTROL API DESLIGADA COM SUCESSO")
    logger.info("=" * 90 + "\n")

# =========================================
# 8. CRIAR APLICACAO FASTAPI
# =========================================

app = FastAPI(
    title="CPE Control API",
    version="2.0.0",
    description="Sistema de Gerenciamento de Usuarios, Grupos, Tickets e Notificacoes",
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
        "http://localhost/SistemaCPE/",
        "http://localhost/SistemaCPE/web",
        "http://127.0.0.1/SistemaCPE",
        "http://127.0.0.1/SistemaCPE/",
        "http://127.0.0.1/SistemaCPE/web",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600
)

logger.info("✅ CORS CONFIGURADO COM SUCESSO!\n")

# =========================================
# 10. ROUTER DE AUTENTICACAO
# =========================================

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

@auth_router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(login_data: LoginRequest):
    """Realiza login do usuario"""
    logger.info("\n" + "=" * 90)
    logger.info("[AUTH] 🔐 TENTATIVA DE LOGIN")
    logger.info("=" * 90)
    logger.info(f"[AUTH]   - Credencial: {login_data.credential}")

    credential = login_data.credential.strip()
    password = login_data.password.strip()

    if not credential or not password:
        logger.warning("[AUTH] ❌ Credencial ou senha vazia")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credencial e senha sao obrigatorios"
        )

    conn = None
    cursor = None

    try:
        logger.info("[AUTH] 🔌 Conectando ao banco de dados...")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        logger.info("[AUTH] ✅ Conexao estabelecida")

        is_email = "@" in credential
        logger.info(f"[AUTH]   - Tipo: {'EMAIL' if is_email else 'USERNAME'}")

        if is_email:
            query = "SELECT id, name, email, username, role, group_id, is_active, created_at, password_hash FROM users WHERE email = %s AND is_active = TRUE LIMIT 1"
        else:
            query = "SELECT id, name, email, username, role, group_id, is_active, created_at, password_hash FROM users WHERE username = %s AND is_active = TRUE LIMIT 1"

        logger.info(f"[AUTH] 🔎 Buscando usuario: {credential}")
        cursor.execute(query, (credential,))
        user = cursor.fetchone()

        if not user:
            logger.warning(f"[AUTH] ❌ Usuario nao encontrado: {credential}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email/username ou senha invalidos"
            )

        logger.info(f"[AUTH] ✅ Usuario encontrado: {user['name']}")
        logger.info("[AUTH] 🔐 Validando senha com bcrypt...")

        password_hash = user.get('password_hash')
        if not password_hash:
            logger.warning("[AUTH] ❌ Usuario nao tem senha definida")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email/username ou senha invalidos"
            )

        try:
            senha_valida = bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception as err:
            logger.error(f"[AUTH] ❌ Erro ao validar hash: {str(err)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email/username ou senha invalidos"
            )

        if not senha_valida:
            logger.warning(f"[AUTH] ❌ Senha incorreta para: {credential}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email/username ou senha invalidos"
            )

        logger.info("[AUTH] ✅ Senha validada com sucesso!")

        # Validar dados do usuario
        if not user.get('username'):
            user['username'] = user['email']
        if not user.get('name'):
            user['name'] = user['email']
        if not user.get('role'):
            user['role'] = 'USER'

        logger.info("[AUTH] 📅 Convertendo dados de datetime...")
        user = convert_datetime_to_string(user)

        if 'password_hash' in user:
            del user['password_hash']

        logger.info("[AUTH] 📦 Construindo resposta...")
        
        try:
            user_response = UserResponse(**user)
            logger.info("[AUTH] ✅ UserResponse criado com sucesso")
        except Exception as validation_err:
            logger.error(f"[AUTH] ❌ ERRO DE VALIDACAO: {str(validation_err)}")
            raise

        # GERAR TOKEN PARA WEBSOCKET
        logger.info("[AUTH] 🔐 Gerando token de autenticacao...")
        
        try:
            token_data = f"{user['id']}:{int(time.time())}"
            access_token = hashlib.sha256(token_data.encode()).hexdigest()
            logger.info(f"[AUTH]   ✓ Token gerado: {access_token[:30]}...")
        except Exception as token_err:
            logger.error(f"[AUTH] ❌ Erro ao gerar token: {str(token_err)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao gerar token: {str(token_err)}"
            )
        
        logger.info("[AUTH] ✅ LOGIN BEM-SUCEDIDO!")
        logger.info("=" * 90 + "\n")

        return LoginResponse(
            success=True,
            message=f"Bem-vindo, {user['name']}!",
            user=user_response,
            access_token=access_token,
            token_type="bearer"
        )

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[AUTH] ❌ ERRO INESPERADO: {str(err)}")
        logger.error("=" * 90 + "\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar login: {str(err)}"
        )

    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass

# =========================================
# 11. ROUTER DE GRUPOS
# =========================================

groups_router = APIRouter(prefix="/api/groups", tags=["groups"])

@groups_router.get("/")
async def get_groups():
    """Obtem todos os grupos"""
    logger.info("\n[GROUPS] 📋 Listando todos os grupos...")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, created_at FROM password_groups ORDER BY created_at DESC")
        groups = cursor.fetchall()
        groups = convert_datetime_list(groups)
        
        logger.info(f"[GROUPS] ✅ {len(groups)} grupo(s) encontrado(s)\n")
        return groups or []
        
    except Exception as err:
        logger.error(f"[GROUPS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao listar grupos: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@groups_router.get("/{group_id}")
async def get_group(group_id: int):
    """Obtem um grupo especifico"""
    logger.info(f"\n[GROUPS] 🔍 Obtendo grupo #{group_id}...")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, created_at FROM password_groups WHERE id = %s", (group_id,))
        group = cursor.fetchone()
        
        if not group:
            logger.warning(f"[GROUPS] ❌ Grupo #{group_id} nao encontrado")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo nao encontrado")
        
        group = convert_datetime_to_string(group)
        logger.info(f"[GROUPS] ✅ Grupo encontrado: {group['name']}\n")
        return group
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[GROUPS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao obter grupo: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@groups_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_group(group: GroupCreate):
    """Cria um novo grupo"""
    logger.info("\n[GROUPS] ➕ CRIANDO NOVO GRUPO")
    logger.info(f"[GROUPS]   - Nome: {group.name}")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("INSERT INTO password_groups (name) VALUES (%s)", (group.name,))
        conn.commit()
        new_group_id = cursor.lastrowid
        logger.info(f"[GROUPS]   ✅ Grupo criado com ID: {new_group_id}")
        
        cursor.execute("SELECT id, name, created_at FROM password_groups WHERE id = %s", (new_group_id,))
        new_group = cursor.fetchone()
        new_group = convert_datetime_to_string(new_group)
        
        logger.info("[GROUPS] ✅ SUCESSO!\n")
        return new_group
        
    except Exception as err:
        logger.error(f"[GROUPS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao criar grupo: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@groups_router.put("/{group_id}")
async def update_group(group_id: int, group: GroupUpdate):
    """Atualiza um grupo"""
    logger.info(f"\n[GROUPS] ✏️ ATUALIZANDO GRUPO #{group_id}")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM password_groups WHERE id = %s", (group_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo nao encontrado")
        
        updates = []
        params = []
        
        if group.name is not None:
            updates.append("name = %s")
            params.append(group.name)
        
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhum campo para atualizar")
        
        params.append(group_id)
        cursor.execute(f"UPDATE password_groups SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()
        
        cursor.execute("SELECT id, name, created_at FROM password_groups WHERE id = %s", (group_id,))
        updated_group = cursor.fetchone()
        updated_group = convert_datetime_to_string(updated_group)
        
        logger.info("[GROUPS] ✅ SUCESSO!\n")
        return updated_group
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[GROUPS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao atualizar grupo: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@groups_router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(group_id: int):
    """Deleta um grupo"""
    logger.info(f"\n[GROUPS] 🗑️ DELETANDO GRUPO #{group_id}...")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT name FROM password_groups WHERE id = %s", (group_id,))
        group = cursor.fetchone()
        
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo nao encontrado")
        
        cursor.execute("DELETE FROM password_groups WHERE id = %s", (group_id,))
        conn.commit()
        
        logger.info(f"[GROUPS] ✅ DELETADO COM SUCESSO!\n")
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[GROUPS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao deletar grupo: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# =========================================
# 12. ROUTER DE USUARIOS
# =========================================

users_router = APIRouter(prefix="/api/users", tags=["users"])

@users_router.get("/")
async def get_users():
    """Obtem todos os usuarios"""
    logger.info("\n[USERS] 📋 Listando todos os usuarios...")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, email, username, role, group_id, is_active, created_at FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        users = convert_datetime_list(users)
        
        logger.info(f"[USERS] ✅ {len(users)} usuario(s) encontrado(s)\n")
        return users or []
        
    except Exception as err:
        logger.error(f"[USERS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao listar usuarios: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@users_router.get("/{user_id}")
async def get_user(user_id: int):
    """Obtem um usuario especifico"""
    logger.info(f"\n[USERS] 🔍 Obtendo usuario #{user_id}...")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, email, username, role, group_id, is_active, created_at FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")
        
        user = convert_datetime_to_string(user)
        logger.info(f"[USERS] ✅ Usuario encontrado: {user['name']}\n")
        return user
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[USERS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao obter usuario: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@users_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """Cria um novo usuario"""
    logger.info("\n[USERS] ➕ CRIANDO NOVO USUARIO")
    logger.info(f"[USERS]   - Nome: {user.name}")
    logger.info(f"[USERS]   - Email: {user.email}")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        if not validate_email_unique(cursor, user.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Email ja registrado")
        
        if not validate_username_unique(cursor, user.username):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Username ja registrado")
        
        if user.group_id and not validate_group_exists(cursor, user.group_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Grupo nao encontrado")
        
        logger.info("[USERS] 🔐 Gerando hash da senha com bcrypt...")
        try:
            password_hash = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            logger.info("[USERS]   ✅ Hash gerado com sucesso")
        except Exception as hash_err:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao processar senha")
        
        cursor.execute(
            "INSERT INTO users (name, email, username, password_hash, role, group_id, is_active) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (user.name, user.email, user.username, password_hash, user.role, user.group_id, user.is_active)
        )
        
        conn.commit()
        new_user_id = cursor.lastrowid
        logger.info(f"[USERS]   ✅ Usuario criado com ID: {new_user_id}")
        
        cursor.execute("SELECT id, name, email, username, role, group_id, is_active, created_at FROM users WHERE id = %s", (new_user_id,))
        new_user = cursor.fetchone()
        new_user = convert_datetime_to_string(new_user)
        
        logger.info("[USERS] ✅ SUCESSO!\n")
        return new_user
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[USERS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao criar usuario: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@users_router.put("/{user_id}")
async def update_user(user_id: int, user: UserUpdate):
    """Atualiza um usuario"""
    logger.info(f"\n[USERS] ✏️ ATUALIZANDO USUARIO #{user_id}")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")
        
        updates = []
        params = []
        
        if user.name is not None:
            updates.append("name = %s")
            params.append(user.name)
        
        if user.email is not None:
            if not validate_email_unique(cursor, user.email, exclude_user_id=user_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email ja registrado")
            updates.append("email = %s")
            params.append(user.email)
        
        if user.username is not None:
            if not validate_username_unique(cursor, user.username, exclude_user_id=user_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username ja registrado")
            updates.append("username = %s")
            params.append(user.username)
        
        if user.role is not None:
            updates.append("role = %s")
            params.append(user.role)
        
        if user.group_id is not None:
            if not validate_group_exists(cursor, user.group_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grupo nao encontrado")
            updates.append("group_id = %s")
            params.append(user.group_id)
        
        if user.is_active is not None:
            updates.append("is_active = %s")
            params.append(user.is_active)
        
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhum campo para atualizar")
        
        params.append(user_id)
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()
        
        cursor.execute("SELECT id, name, email, username, role, group_id, is_active, created_at FROM users WHERE id = %s", (user_id,))
        updated_user = cursor.fetchone()
        updated_user = convert_datetime_to_string(updated_user)
        
        logger.info("[USERS] ✅ SUCESSO!\n")
        return updated_user
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[USERS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao atualizar usuario: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@users_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int):
    """Deleta um usuario"""
    logger.info(f"\n[USERS] 🗑️ DELETANDO USUARIO #{user_id}...")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT name FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")
        
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        
        logger.info(f"[USERS] ✅ DELETADO COM SUCESSO!\n")
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[USERS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao deletar usuario: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# =========================================
# 13. ROUTER DE TICKETS
# =========================================

tickets_router = APIRouter(prefix="/api/tickets", tags=["tickets"])

@tickets_router.get("/")
async def get_tickets():
    """Obtem todos os tickets"""
    logger.info("\n[TICKETS] 📋 Listando todos os tickets...")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, numero, assunto, descricao_inicial, solicitante_id, responsavel_id, group_id, categoria_id, status_id, prioridade_id, origem, created_at, updated_at FROM tickets ORDER BY created_at DESC")
        tickets = cursor.fetchall()
        
        tickets_mapeados = []
        for ticket in tickets:
            ticket_com_dados = mapa_dados_ticket(ticket, cursor)
            ticket_com_dados = convert_datetime_to_string(ticket_com_dados)
            tickets_mapeados.append(ticket_com_dados)
        
        logger.info(f"[TICKETS] ✅ {len(tickets_mapeados)} ticket(s) encontrado(s)\n")
        return tickets_mapeados
        
    except Exception as err:
        logger.error(f"[TICKETS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao listar tickets: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@tickets_router.get("/{ticket_id}")
async def get_ticket(ticket_id: int):
    """Obtem um ticket especifico"""
    logger.info(f"\n[TICKET] 🔍 Obtendo ticket #{ticket_id}...")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, numero, assunto, descricao_inicial, solicitante_id, responsavel_id, group_id, categoria_id, status_id, prioridade_id, origem, created_at, updated_at FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()
        
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket nao encontrado")
        
        ticket = mapa_dados_ticket(ticket, cursor)
        ticket = convert_datetime_to_string(ticket)
        
        logger.info(f"[TICKET] ✅ Ticket encontrado: {ticket['numero']}\n")
        return ticket
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[TICKET] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao obter ticket: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@tickets_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_ticket(ticket_data: TicketCreate):
    """Cria um novo ticket"""
    logger.info("\n[TICKETS] ➕ CRIANDO NOVO TICKET")
    logger.info(f"[TICKETS]   - Assunto: {ticket_data.assunto}")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id FROM users WHERE id = %s", (ticket_data.solicitante_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solicitante nao existe")
        
        if ticket_data.responsavel_id:
            cursor.execute("SELECT id FROM users WHERE id = %s", (ticket_data.responsavel_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Responsavel nao existe")
        
        if ticket_data.group_id:
            cursor.execute("SELECT id FROM password_groups WHERE id = %s", (ticket_data.group_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grupo nao existe")
        
        numero_ticket = gerar_numero_ticket(cursor)
        
        cursor.execute(
            "INSERT INTO tickets (numero, assunto, descricao_inicial, solicitante_id, responsavel_id, group_id, categoria_id, status_id, prioridade_id, origem, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())",
            (numero_ticket, ticket_data.assunto, ticket_data.descricao_inicial, ticket_data.solicitante_id, ticket_data.responsavel_id or None, ticket_data.group_id or None, ticket_data.categoria_id or None, 1, ticket_data.prioridade_id, ticket_data.origem or "web")
        )
        
        conn.commit()
        new_ticket_id = cursor.lastrowid
        logger.info(f"[TICKETS]   ✅ Ticket criado com ID: {new_ticket_id}")
        
        cursor.execute("SELECT id, numero, assunto, descricao_inicial, solicitante_id, responsavel_id, group_id, categoria_id, status_id, prioridade_id, origem, created_at, updated_at FROM tickets WHERE id = %s", (new_ticket_id,))
        new_ticket = cursor.fetchone()
        new_ticket = mapa_dados_ticket(new_ticket, cursor)
        new_ticket = convert_datetime_to_string(new_ticket)
        
        logger.info("[TICKETS] ✅ SUCESSO!\n")
        return new_ticket
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[TICKETS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao criar ticket: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@tickets_router.put("/{ticket_id}")
async def update_ticket(ticket_id: int, ticket_data: TicketUpdate):
    """Atualiza um ticket"""
    logger.info(f"\n[TICKETS] ✏️ ATUALIZANDO TICKET #{ticket_id}")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM tickets WHERE id = %s", (ticket_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket nao encontrado")
        
        updates = []
        params = []
        
        if ticket_data.assunto is not None:
            updates.append("assunto = %s")
            params.append(ticket_data.assunto)
        
        if ticket_data.descricao_inicial is not None:
            updates.append("descricao_inicial = %s")
            params.append(ticket_data.descricao_inicial)
        
        if ticket_data.responsavel_id is not None:
            if ticket_data.responsavel_id:
                cursor.execute("SELECT id FROM users WHERE id = %s", (ticket_data.responsavel_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Responsavel nao existe")
            updates.append("responsavel_id = %s")
            params.append(ticket_data.responsavel_id or None)
        
        if ticket_data.group_id is not None:
            if ticket_data.group_id:
                cursor.execute("SELECT id FROM password_groups WHERE id = %s", (ticket_data.group_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grupo nao existe")
            updates.append("group_id = %s")
            params.append(ticket_data.group_id or None)
        
        if ticket_data.status_id is not None:
            updates.append("status_id = %s")
            params.append(ticket_data.status_id)
        
        if ticket_data.prioridade_id is not None:
            updates.append("prioridade_id = %s")
            params.append(ticket_data.prioridade_id)
        
        if ticket_data.categoria_id is not None:
            updates.append("categoria_id = %s")
            params.append(ticket_data.categoria_id)
        
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhum campo para atualizar")
        
        updates.append("updated_at = NOW()")
        params.append(ticket_id)
        
        cursor.execute(f"UPDATE tickets SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()
        
        cursor.execute("SELECT id, numero, assunto, descricao_inicial, solicitante_id, responsavel_id, group_id, categoria_id, status_id, prioridade_id, origem, created_at, updated_at FROM tickets WHERE id = %s", (ticket_id,))
        updated_ticket = cursor.fetchone()
        updated_ticket = mapa_dados_ticket(updated_ticket, cursor)
        updated_ticket = convert_datetime_to_string(updated_ticket)
        
        logger.info("[TICKETS] ✅ SUCESSO!\n")
        return updated_ticket
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[TICKETS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao atualizar ticket: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@tickets_router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(ticket_id: int):
    """Deleta um ticket"""
    logger.info(f"\n[TICKETS] 🗑️ DELETANDO TICKET #{ticket_id}...")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT numero FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()
        
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket nao encontrado")
        
        cursor.execute("DELETE FROM ticket_interacoes WHERE ticket_id = %s", (ticket_id,))
        cursor.execute("DELETE FROM notificacoes WHERE ticket_id = %s", (ticket_id,))
        cursor.execute("DELETE FROM tickets WHERE id = %s", (ticket_id,))
        conn.commit()
        
        logger.info(f"[TICKETS] ✅ TICKET {ticket['numero']} DELETADO COM SUCESSO!\n")
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[TICKETS] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao deletar ticket: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# =========================================
# 14. ROUTER DE INTERACOES
# =========================================

interacoes_router = APIRouter(prefix="/api/ticket-interacoes", tags=["interacoes"])

@interacoes_router.get("/{ticket_id}")
async def get_ticket_interacoes(ticket_id: int):
    """Obtem todas as interacoes de um ticket"""
    logger.info(f"\n[INTERACOES] 💬 Listando comentarios do ticket #{ticket_id}...")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id FROM tickets WHERE id = %s", (ticket_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket nao encontrado")
        
        cursor.execute("SELECT id, ticket_id, usuario_id, mensagem, tipo, publico, created_at FROM ticket_interacoes WHERE ticket_id = %s ORDER BY created_at ASC", (ticket_id,))
        interacoes = cursor.fetchall()
        
        interacoes_mapeadas = []
        for interacao in interacoes:
            cursor.execute("SELECT name FROM users WHERE id = %s", (interacao['usuario_id'],))
            usuario = cursor.fetchone()
            interacao['usuario_nome'] = usuario['name'] if usuario else "Desconhecido"
            interacao = convert_datetime_to_string(interacao)
            interacoes_mapeadas.append(interacao)
        
        logger.info(f"[INTERACOES] ✅ {len(interacoes_mapeadas)} comentario(s) encontrado(s)\n")
        return interacoes_mapeadas
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[INTERACOES] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao listar interacoes: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@interacoes_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_ticket_interacao(interacao_data: TicketInteracaoCreate):
    """Cria uma nova interacao"""
    logger.info("\n[INTERACOES] ➕ CRIANDO COMENTARIO")
    logger.info(f"[INTERACOES]   - Ticket: #{interacao_data.ticket_id}")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id FROM tickets WHERE id = %s", (interacao_data.ticket_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket nao existe")
        
        cursor.execute("SELECT id FROM users WHERE id = %s", (interacao_data.usuario_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao existe")
        
        cursor.execute("INSERT INTO ticket_interacoes (ticket_id, usuario_id, mensagem, tipo, publico, created_at) VALUES (%s, %s, %s, %s, %s, NOW())", 
            (interacao_data.ticket_id, interacao_data.usuario_id, interacao_data.mensagem, interacao_data.tipo, interacao_data.publico))
        
        conn.commit()
        new_interacao_id = cursor.lastrowid
        logger.info(f"[INTERACOES]   ✅ Comentario criado com ID: {new_interacao_id}")
        
        cursor.execute("SELECT id, ticket_id, usuario_id, mensagem, tipo, publico, created_at FROM ticket_interacoes WHERE id = %s", (new_interacao_id,))
        new_interacao = cursor.fetchone()
        
        cursor.execute("SELECT name FROM users WHERE id = %s", (new_interacao['usuario_id'],))
        usuario = cursor.fetchone()
        new_interacao['usuario_nome'] = usuario['name'] if usuario else "Desconhecido"
        
        new_interacao = convert_datetime_to_string(new_interacao)
        
        logger.info("[INTERACOES] ✅ SUCESSO!\n")
        return new_interacao
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[INTERACOES] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao criar comentario: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# =========================================
# 15. ROUTER DE NOTIFICACOES
# =========================================

notificacoes_router = APIRouter(prefix="/api/notificacoes", tags=["notificacoes"])

@notificacoes_router.get("/")
async def get_notificacoes(usuario_id: int = Query(...), lido: bool = None, limite: int = 50, offset: int = 0):
    """Lista notificacoes do usuario"""
    logger.info(f"\n[NOTIFICACOES] 📬 Listando notificacoes do usuario #{usuario_id}")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id FROM users WHERE id = %s", (usuario_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")
        
        query = "SELECT id, ticket_id, usuario_id, mensagem, tipo, lido, created_at, updated_at FROM notificacoes WHERE usuario_id = %s"
        params = [usuario_id]
        
        if lido is not None:
            query += " AND lido = %s"
            params.append(lido)
        
        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limite, offset])
        
        cursor.execute(query, params)
        notificacoes = cursor.fetchall()
        notificacoes = convert_datetime_list(notificacoes)
        
        logger.info(f"[NOTIFICACOES] ✅ {len(notificacoes)} notificacao(oes) encontrada(s)\n")
        return notificacoes or []
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[NOTIFICACOES] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao listar notificacoes: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@notificacoes_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_notificacao(notificacao: NotificacaoCreate):
    """Cria uma nova notificacao"""
    logger.info("\n[NOTIFICACOES] 💌 CRIANDO NOTIFICACAO")
    logger.info(f"[NOTIFICACOES]   - Ticket: #{notificacao.ticket_id}")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id FROM tickets WHERE id = %s", (notificacao.ticket_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket nao encontrado")
        
        cursor.execute("SELECT id FROM users WHERE id = %s", (notificacao.usuario_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")
        
        cursor.execute("INSERT INTO notificacoes (ticket_id, usuario_id, mensagem, tipo, lido, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, NOW(), NOW())",
            (notificacao.ticket_id, notificacao.usuario_id, notificacao.mensagem, notificacao.tipo, notificacao.lido))
        
        conn.commit()
        new_notif_id = cursor.lastrowid
        logger.info(f"[NOTIFICACOES]   ✅ ID criado: {new_notif_id}")
        
        cursor.execute("SELECT id, ticket_id, usuario_id, mensagem, tipo, lido, created_at, updated_at FROM notificacoes WHERE id = %s", (new_notif_id,))
        new_notif = cursor.fetchone()
        new_notif = convert_datetime_to_string(new_notif)
        
        logger.info("[NOTIFICACOES] ✅ SUCESSO!\n")
        return new_notif
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[NOTIFICACOES] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao criar notificacao: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@notificacoes_router.get("/nao-lidas/{usuario_id}")
async def contar_nao_lidas(usuario_id: int):
    """Conta notificacoes nao lidas"""
    logger.info(f"\n[NOTIFICACOES] 📊 Contando nao lidas do usuario #{usuario_id}")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as total FROM notificacoes WHERE usuario_id = %s AND lido = FALSE", (usuario_id,))
        result = cursor.fetchone()
        count = result['total'] if result else 0
        
        logger.info(f"[NOTIFICACOES] ✅ {count} nao lida(s)\n")
        return {"usuario_id": usuario_id, "nao_lidas": count}
        
    except Exception as err:
        logger.error(f"[NOTIFICACOES] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao contar notificacoes: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@notificacoes_router.put("/{notificacao_id}")
async def update_notificacao(notificacao_id: int, notificacao: NotificacaoUpdate):
    """Atualiza uma notificacao"""
    logger.info(f"\n[NOTIFICACOES] 📝 Atualizando notificacao #{notificacao_id}")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM notificacoes WHERE id = %s", (notificacao_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificacao nao encontrada")
        
        updates = []
        params = []
        
        if notificacao.lido is not None:
            updates.append("lido = %s")
            params.append(notificacao.lido)
        
        if notificacao.mensagem is not None:
            updates.append("mensagem = %s")
            params.append(notificacao.mensagem)
        
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhum campo para atualizar")
        
        updates.append("updated_at = NOW()")
        params.append(notificacao_id)
        
        cursor.execute(f"UPDATE notificacoes SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()
        
        cursor.execute("SELECT id, ticket_id, usuario_id, mensagem, tipo, lido, created_at, updated_at FROM notificacoes WHERE id = %s", (notificacao_id,))
        updated_notif = cursor.fetchone()
        updated_notif = convert_datetime_to_string(updated_notif)
        
        logger.info("[NOTIFICACOES] ✅ SUCESSO!\n")
        return updated_notif
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[NOTIFICACOES] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao atualizar notificacao: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@notificacoes_router.delete("/{notificacao_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notificacao(notificacao_id: int):
    """Deleta uma notificacao"""
    logger.info(f"\n[NOTIFICACOES] 🗑️ DELETANDO NOTIFICACAO #{notificacao_id}...")
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM notificacoes WHERE id = %s", (notificacao_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificacao nao encontrada")
        
        cursor.execute("DELETE FROM notificacoes WHERE id = %s", (notificacao_id,))
        conn.commit()
        
        logger.info(f"[NOTIFICACOES] ✅ DELETADA COM SUCESSO!\n")
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[NOTIFICACOES] ❌ ERRO: {str(err)}\n")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao deletar notificacao: {str(err)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# =========================================
# 16. HEALTH CHECK
# =========================================

@app.get("/health", response_model=HealthCheckResponse)
async def health():
    """Verifica a saude da API"""
    db_status = "✅ OK"
    try:
        conn = get_db_connection()
        conn.close()
    except:
        db_status = "❌ ERRO"
    
    return {
        "status": "ok",
        "api": "CPE Control API",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "database": db_status
    }

# =========================================
# 17. REGISTRAR ROUTERS
# =========================================

app.include_router(auth_router)
app.include_router(groups_router)
app.include_router(users_router)
app.include_router(tickets_router)
app.include_router(interacoes_router)
app.include_router(notificacoes_router)

logger.info("✅ TODOS OS ROUTERS REGISTRADOS COM SUCESSO!")
logger.info("   - Router de Autenticacao: /api/auth")
logger.info("   - Router de Grupos: /api/groups")
logger.info("   - Router de Usuarios: /api/users")
logger.info("   - Router de Tickets: /api/tickets")
logger.info("   - Router de Interacoes: /api/ticket-interacoes")
logger.info("   - Router de Notificacoes: /api/notificacoes")
logger.info("")

# =========================================
# 18. MAIN - INICIALIZAR SERVIDOR
# =========================================

if __name__ == "__main__":
    logger.info("\n" + "=" * 90)
    logger.info("🚀 INICIANDO CPE CONTROL API v2.0.0")
    logger.info("=" * 90)
    logger.info("🌐 Servidor: http://localhost:8000")
    logger.info("🌐 IP Local: http://127.0.0.1:8000")
    logger.info("📚 Documentacao: http://localhost:8000/docs")
    logger.info("=" * 90 + "\n")
    
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )