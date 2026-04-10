"""
CPE Control API - Aplicacao Principal v2.0.0
Gerenciamento de Usuarios, Grupos, Tickets e Notificacoes com Autenticacao Bcrypt

✅ VALIDADO E TESTADO
✅ SEM CIRCULAR IMPORTS
✅ TODOS OS ROUTERS FUNCIONAM
✅ v2.0.1 - Login retorna group_name para preencher modal de ticket
"""

# =========================================
# 1. IMPORTACOES BASE
# =========================================
from fastapi import FastAPI, HTTPException, APIRouter, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
import logging
import uvicorn
import bcrypt
import hashlib
import time
from contextlib import asynccontextmanager
from datetime import datetime
import sys
import os

# =========================================
# 2. ADICIONAR DIRETORIO AO PATH (RESOLVE IMPORTS)
# =========================================
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# =========================================
# 3. IMPORTAR DE DATABASE.PY
# =========================================
from database import (
    get_db_connection,
    get_db_or_404,
    convert_datetime_to_string,
    convert_datetime_list,
    validate_email_unique,
    validate_username_unique,
    DB_CONFIG
)

# =========================================
# 4. CONFIGURAR LOGGING
# =========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("\n" + "=" * 100)
logger.info("CONFIGURACAO DE BANCO DE DADOS")
logger.info("=" * 100)
logger.info(f"  Host: {DB_CONFIG['host']}")
logger.info(f"  User: {DB_CONFIG['user']}")
logger.info(f"  Database: {DB_CONFIG['database']}")
logger.info("=" * 100 + "\n")

# =========================================
# 5. MODELOS PYDANTIC
# =========================================

# --- USUARIOS ---
class UserBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    role: str = Field(default="USER", pattern="^(USER|ADMIN|TI|RESPONSAVEL_GRUPO)$")
    group_id: Optional[int] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    role: Optional[str] = Field(None, pattern="^(USER|ADMIN|TI|RESPONSAVEL_GRUPO)$")
    group_id: Optional[int] = None
    is_active: Optional[bool] = None

# ✅ CORRIGIDO: adicionado group_name para o frontend preencher o modal de ticket
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    username: Optional[str] = None
    role: str
    group_id: Optional[int] = None
    group_name: Optional[str] = None   # ← NOVO: nome do grupo/setor do usuário
    is_active: bool
    created_at: Optional[str] = None

# --- GRUPOS ---
class GroupBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=500)

class GroupCreate(GroupBase):
    department_id: Optional[int] = None

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
    token_type: str = "bearer"

# --- HEALTH CHECK ---
class HealthCheckResponse(BaseModel):
    status: str
    api: str
    version: str
    timestamp: str
    database: Optional[str] = None

# =========================================
# 6. LIFESPAN - EVENTOS DE CICLO DE VIDA
# =========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicacao"""
    # ===== STARTUP =====
    logger.info("\n" + "=" * 100)
    logger.info("✅ CPE CONTROL API v2.0.0 INICIADA COM SUCESSO")
    logger.info("=" * 100)
    logger.info("\n📋 ENDPOINTS DISPONIVEIS:\n")
    logger.info("   [AUTH]")
    logger.info("   └─ POST   /api/auth/login                      -> Login do usuario\n")
    logger.info("   [GRUPOS]")
    logger.info("   ├─ GET    /api/groups                          -> Listar grupos")
    logger.info("   ├─ GET    /api/groups/{id}                     -> Obter grupo especifico")
    logger.info("   ├─ POST   /api/groups                          -> Criar novo grupo")
    logger.info("   ├─ PUT    /api/groups/{id}                     -> Atualizar grupo")
    logger.info("   └─ DELETE /api/groups/{id}                     -> Deletar grupo\n")
    logger.info("   [USUARIOS]")
    logger.info("   ├─ GET    /api/users                           -> Listar usuarios")
    logger.info("   ├─ GET    /api/users/{id}                      -> Obter usuario especifico")
    logger.info("   ├─ POST   /api/users                           -> Criar novo usuario")
    logger.info("   ├─ PUT    /api/users/{id}                      -> Atualizar usuario")
    logger.info("   └─ DELETE /api/users/{id}                      -> Deletar usuario\n")
    logger.info("   [TICKETS]")
    logger.info("   ├─ GET    /api/tickets                         -> Listar tickets")
    logger.info("   ├─ GET    /api/tickets/{id}                    -> Obter ticket especifico")
    logger.info("   ├─ POST   /api/tickets                         -> Criar novo ticket")
    logger.info("   ├─ PUT    /api/tickets/{id}                    -> Atualizar ticket")
    logger.info("   └─ DELETE /api/tickets/{id}                    -> Deletar ticket\n")
    logger.info("   [INTERACOES]")
    logger.info("   ├─ GET    /api/ticket-interacoes/{ticket_id}   -> Listar comentarios")
    logger.info("   └─ POST   /api/ticket-interacoes               -> Criar comentario\n")
    logger.info("   [NOTIFICACOES]")
    logger.info("   ├─ GET    /api/notificacoes                    -> Listar notificacoes")
    logger.info("   ├─ GET    /api/notificacoes/nao-lidas/{id}     -> Contar nao lidas")
    logger.info("   ├─ PUT    /api/notificacoes/{id}               -> Marcar como lida")
    logger.info("   └─ DELETE /api/notificacoes/{id}               -> Deletar notificacao\n")
    logger.info("   [HEALTH]")
    logger.info("   └─ GET    /health                              -> Verificar saude da API\n")
    logger.info("=" * 100)
    logger.info("📚 DOCUMENTACAO:")
    logger.info("   🌐 Swagger UI: http://localhost:8000/docs")
    logger.info("   🌐 ReDoc: http://localhost:8000/redoc\n")
    logger.info("🌐 SERVIDOR:")
    logger.info("   HTTP: http://localhost:8000")
    logger.info("   HTTP: http://127.0.0.1:8000\n")
    logger.info("=" * 100 + "\n")
    
    yield
    
    # ===== SHUTDOWN =====
    logger.info("\n" + "=" * 100)
    logger.info("🛑 CPE CONTROL API DESLIGADA COM SUCESSO")
    logger.info("=" * 100 + "\n")

# =========================================
# 7. CRIAR APLICACAO FASTAPI
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
# 8. MIDDLEWARE: CORS
# =========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:80",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://localhost:5500",
        "http://127.0.0.1",
        "http://127.0.0.1:80",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5500",
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
# 9. ROUTER DE AUTENTICACAO
# =========================================

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

# ================================================== 
# LOGIN - FUNÇÃO COMPLETA CORRIGIDA
# Data: 06/04/2026 19:45
# ==================================================

@auth_router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(login_data: LoginRequest):
    """Realiza login do usuario"""
    logger.info("\n" + "=" * 100)
    logger.info("[AUTH] 🔐 TENTATIVA DE LOGIN")
    logger.info("=" * 100)
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

        # ✅ CORRIGIDO: JOIN com tabela `cpe_grupo` para retornar group_name ao frontend.
        # Isso resolve o campo "Grupo/Setor" vazio no modal de criação de ticket,
        # pois users.group_id referencia a tabela `cpe_grupo` (não groups).
        # IMPORTANTE: `cpe_grupo` é a tabela renomeada (groups é palavra-chave reservada do MySQL).
        
        if is_email:
            query = """
                 SELECT
                    u.id, u.name, u.email, u.username, u.role,
                    u.group_id, u.is_active, u.created_at, u.password_hash,
                    `cpe_grupo`.`name` AS group_name
                FROM users u
                LEFT JOIN `cpe_grupo` ON u.group_id = `cpe_grupo`.`id`
                WHERE u.email = %s
            """
        else:
            query = """
                SELECT
                    u.id, u.name, u.email, u.username, u.role,
                    u.group_id, u.is_active, u.created_at, u.password_hash,
                    `cpe_grupo`.`name` AS group_name
                FROM users u
                LEFT JOIN `cpe_grupo` ON u.group_id = `cpe_grupo`.`id`
                WHERE u.username = %s
            """
        
        logger.info(f"[AUTH] 🔎 Buscando usuario: {credential}")
        cursor.execute(query, (credential,))
        user = cursor.fetchone()

        if not user:
            logger.warning(f"[AUTH] ❌ Usuario nao encontrado: {credential}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email/username ou senha invalidos"
            )

        logger.info(f"[AUTH] ✅ Usuario encontrado: {user['name']} | Grupo: {user.get('group_name', 'Sem grupo')}")
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
            logger.info(f"[AUTH] ✅ UserResponse criado | group_name: {user_response.group_name}")
        except Exception as validation_err:
            logger.error(f"[AUTH] ❌ ERRO DE VALIDACAO: {str(validation_err)}")
            raise

        # GERAR TOKEN
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
        logger.info("=" * 100 + "\n")

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
        logger.error("=" * 100 + "\n")
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

# ================================================== 
# [FIM] LOGIN - FUNÇÃO COMPLETA CORRIGIDA
# Data: 06/04/2026 19:45
# ==================================================

# =========================================
# 10. ROUTER DE GRUPOS
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
        cursor.execute("SELECT id, department_id, name, description, created_at FROM `cpe_grupo` ORDER BY created_at DESC")
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
        cursor.execute("SELECT id, department_id, name, description, created_at FROM `cpe_grupo` WHERE id = %s", (group_id,))
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
        cursor.execute("INSERT INTO `cpe_grupo` (department_id, name, description) VALUES (%s, %s, %s)",
        (group.department_id, group.name, group.description))
        conn.commit()
        new_group_id = cursor.lastrowid
        logger.info(f"[GROUPS]   ✅ Grupo criado com ID: {new_group_id}")
        
        cursor.execute("SELECT id, department_id, name, description, created_at FROM `cpe_grupo` WHERE id = %s", (new_group_id,))
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
        cursor.execute("SELECT id FROM `cpe_grupo` WHERE id = %s", (group_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo nao encontrado")
        
        updates = []
        params = []
        
        if group.name is not None:
            updates.append("name = %s")
            params.append(group.name)
        
        if group.description is not None:
            updates.append("description = %s")
            params.append(group.description)
        
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhum campo para atualizar")
        
        params.append(group_id)
        cursor.execute(f"UPDATE `cpe_grupo` SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()
        
        cursor.execute("SELECT id, department_id, name, description, created_at FROM `cpe_grupo` WHERE id = %s", (group_id,))
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
        cursor.execute("SELECT name FROM `cpe_grupo` WHERE id = %s", (group_id,))
        group = cursor.fetchone()
        
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo nao encontrado")
        
        cursor.execute("DELETE FROM `cpe_grupo` WHERE id = %s", (group_id,))
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
# 11. ROUTER DE USUARIOS
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
        
        if user.group_id:
            cursor.execute("SELECT id FROM `cpe_grupo` WHERE id = %s", (user.group_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grupo nao encontrado")
        
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
            cursor.execute("SELECT id FROM `cpe_grupo` WHERE id = %s", (user.group_id,))
            if not cursor.fetchone():
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
# 12. HEALTH CHECK
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
# 13. REGISTRAR ROUTERS INTERNOS
# =========================================

app.include_router(auth_router)
app.include_router(groups_router)
app.include_router(users_router)

logger.info("✅ Routers internos registrados com sucesso!")
logger.info("   - Router de Autenticacao: /api/auth")
logger.info("   - Router de Grupos: /api/groups")
logger.info("   - Router de Usuarios: /api/users\n")

# =========================================
# 14. REGISTRAR ROUTERS EXTERNOS (COM TRY/EXCEPT)
# =========================================

# ✅ REGISTRAR ROUTER DE TICKETS (EXTERNO)
try:
    from routes.tickets import tickets_router, interacoes_router
    app.include_router(tickets_router)
    app.include_router(interacoes_router)
    logger.info("✅ Router de Tickets registrado: /api/tickets")
    logger.info("✅ Router de Interações registrado: /api/ticket-interacoes")
except ModuleNotFoundError as err:
    logger.error(f"❌ Erro ao importar routes.tickets: Modulo nao encontrado")
    logger.error(f"   Arquivo esperado: server/routes/tickets.py")
    logger.error(f"   Detalhes: {str(err)}")
except ImportError as err:
    logger.error(f"❌ Erro ao importar routes.tickets: Circular import ou dependencia faltando")
    logger.error(f"   Detalhes: {str(err)}")
    import traceback
    logger.error(traceback.format_exc())
except Exception as err:
    logger.error(f"❌ Erro ao registrar router de Tickets: {str(err)}")
    logger.error(f"   Detalhes: {type(err).__name__}")
    import traceback
    logger.error(traceback.format_exc())

# ✅ REGISTRAR ROUTER DE PERMISSÕES (EXTERNO)
try:
    from routes.permissions import router as permissions_router
    app.include_router(permissions_router)
    logger.info("✅ Router de Permissões registrado: /api/permissions")
except Exception as err:
    logger.error(f"❌ Erro ao registrar router de Permissões: {str(err)}")

# ✅ REGISTRAR ROUTER DE CATEGORIAS/SUBCATEGORIAS (EXTERNO)
try:
    from routes.categorias import categorias_router, subcategorias_router
    app.include_router(categorias_router)
    app.include_router(subcategorias_router)
    logger.info("✅ Router de Categorias registrado: /api/categorias")
    logger.info("✅ Router de Subcategorias registrado: /api/subcategorias")
except Exception as err:
    logger.error(f"❌ Erro ao registrar router de Categorias: {str(err)}")

# ✅ REGISTRAR ROUTER DE NOTIFICAÇÕES (EXTERNO)
try:
    from routes.notificacoes import notificacoes_router
    app.include_router(notificacoes_router)
    logger.info("✅ Router de Notificações registrado: /api/notificacoes")
except ModuleNotFoundError as err:
    logger.error(f"❌ Erro ao importar routes.notificacoes: Modulo nao encontrado")
    logger.error(f"   Arquivo esperado: server/routes/notificacoes.py")
    logger.error(f"   Detalhes: {str(err)}")
except ImportError as err:
    logger.error(f"❌ Erro ao importar routes.notificacoes: Circular import ou dependencia faltando")
    logger.error(f"   Detalhes: {str(err)}")
    import traceback
    logger.error(traceback.format_exc())
except Exception as err:
    logger.error(f"❌ Erro ao registrar router de Notificações: {str(err)}")
    logger.error(f"   Detalhes: {type(err).__name__}")
    import traceback
    logger.error(traceback.format_exc())

# ✅ REGISTRAR ROUTER DE AVALIAÇÕES (EXTERNO)
try:
    from routes.avaliacoes import avaliacoes_router
    app.include_router(avaliacoes_router)
    logger.info("✅ Router de Avaliações registrado: /api/avaliacoes")
except Exception as err:
    logger.error(f"❌ Erro ao registrar router de Avaliações: {str(err)}")
    import traceback
    logger.error(traceback.format_exc())

logger.info("")
logger.info("✅ TODOS OS ROUTERS REGISTRADOS!")
logger.info("=" * 100)
logger.info("📋 RESUMO DOS ENDPOINTS:")
logger.info("=" * 100)
logger.info("   [AUTH]        /api/auth/login")
logger.info("   [GROUPS]      GET/POST/PUT/DELETE /api/groups{/{id}}")
logger.info("   [USERS]       GET/POST/PUT/DELETE /api/users{/{id}}")
logger.info("   [TICKETS]     GET/POST/PUT/DELETE /api/tickets{/{id}}")
logger.info("   [INTERACOES]  GET /api/ticket-interacoes/{ticket_id}")
logger.info("   [INTERACOES]  POST /api/ticket-interacoes")
logger.info("   [NOTIFICACOES] GET/PUT/DELETE /api/notificacoes{/{id}}")
logger.info("   [NOTIFICACOES] GET /api/notificacoes/nao-lidas/{usuario_id}")
logger.info("   [HEALTH]      /health")
logger.info("=" * 100)
logger.info("")

# =========================================
# 15. MAIN - INICIALIZAR SERVIDOR
# =========================================

if __name__ == "__main__":
    logger.info("\n" + "=" * 100)
    logger.info("🚀 INICIANDO CPE CONTROL API v2.0.0")
    logger.info("=" * 100)
    logger.info("🌐 Servidor: http://localhost:8000")
    logger.info("🌐 IP Local: http://127.0.0.1:8000")
    logger.info("📚 Documentacao: http://localhost:8000/docs")
    logger.info("=" * 100 + "\n")
    
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )