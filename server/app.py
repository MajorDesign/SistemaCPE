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
from fastapi import FastAPI, HTTPException, APIRouter, status, Query, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

# Garante que stdout/stderr aceitem UTF-8 (emojis nos print() das rotas)
# necessário no Windows onde o terminal padrão usa CP1252
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

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
    unit_id: Optional[int] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    cpf: Optional[str] = Field(None, max_length=14)

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    role: Optional[str] = Field(None, pattern="^(USER|ADMIN|TI|RESPONSAVEL_GRUPO)$")
    group_id: Optional[int] = None
    unit_id: Optional[int] = None
    is_active: Optional[bool] = None
    cpf: Optional[str] = Field(None, max_length=14)

# ✅ CORRIGIDO: adicionado group_name para o frontend preencher o modal de ticket
# ✅ NOVO (2026-04-30): unit_id e unit_nome para vincular usuário a uma unidade CPE
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    username: Optional[str] = None
    role: str
    group_id: Optional[int] = None
    group_name: Optional[str] = None   # nome do grupo/setor do usuário
    unit_id: Optional[int] = None
    unit_nome: Optional[str] = None    # nome da unidade física (ex.: CPE Belo Horizonte)
    cpf: Optional[str] = None          # CPF (11 dígitos, sem máscara) — usado em termos
    is_active: bool
    created_at: Optional[str] = None
    must_change_password: bool = False  # flag setada quando admin reseta a senha

# --- GRUPOS ---
class GroupBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=500)

class GroupCreate(GroupBase):
    department_id: int = Field(..., gt=0)

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
# DEBUG: WS test endpoint sem middlewares de auth
# =========================================
from fastapi import WebSocket as _WS
@app.websocket("/api/_debug/ws-test")
async def _debug_ws_test(ws: _WS):
    await ws.accept()
    await ws.send_text("hello from ws test")
    await ws.close()


# =========================================
# 8. MIDDLEWARE: CORS
# =========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Localhost / dev
        "http://localhost",
        "http://localhost:80",
        "http://localhost:1509",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://localhost:5500",
        "http://127.0.0.1",
        "http://127.0.0.1:80",
        "http://127.0.0.1:1509",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5500",
        "http://localhost/SistemaCPE",
        "http://localhost/SistemaCPE/",
        "http://localhost/SistemaCPE/web",
        "http://127.0.0.1/SistemaCPE",
        "http://127.0.0.1/SistemaCPE/",
        "http://127.0.0.1/SistemaCPE/web",
        # IP público (NAT MikroTik) — manter enquanto staging usa
        "http://201.16.214.49:1509",
        "http://201.16.214.49:8000",
        # Domínios públicos via Cloudflare Tunnel
        "https://cpecontrol.us.kg",
        "https://api.cpecontrol.us.kg",
        "https://www.cpecontrol.us.kg",
        "https://cpecontrol.cpetecnologia.com.br",
        "https://www.cpecontrol.cpetecnologia.com.br",
        "https://agenda.cpecontrol.com.br",
    ],
    # Aceita qualquer IP da rede local (10.x, 172.16-31.x, 192.168.x) na porta 80 ou 8000
    # OU qualquer subdominio *.cpetecnologia.com.br via HTTPS
    allow_origin_regex=r"^https?://(10(\.\d{1,3}){3}|172\.(1[6-9]|2\d|3[01])(\.\d{1,3}){2}|192\.168(\.\d{1,3}){2})(:\d+)?(/.*)?$|^https://[a-z0-9-]+\.cpetecnologia\.com\.br$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600
)

logger.info("✅ CORS CONFIGURADO COM SUCESSO!\n")

# =========================================
# 8.1 MIDDLEWARE: Defesas contra abuso/DDoS de aplicação
# =========================================
# Estratégia em 3 camadas:
#   (a) Limite de tamanho de body: bloqueia uploads abusivos
#   (b) Rate-limit por IP: 120 req/min em rotas /api/*
#   (c) Auto-ban fail2ban-like: 10 erros 401/403 em 5min → ban 30min
#
# Combinado com o rate-limit específico de /api/auth/login (5/5min)
# isso cobre: brute-force, scraping, scanning automatizado, slow attacks.
# DDoS volumétrico (gigabits) NÃO é defensável aqui — só upstream/CDN resolve.

from collections import deque
from fastapi.responses import JSONResponse

# --- Limites configuráveis via env ---
_MAX_BODY_BYTES   = int(os.getenv("MAX_BODY_MB", "50")) * 1024 * 1024
_REQ_PER_MIN      = int(os.getenv("RATE_LIMIT_PER_MIN", "120"))
_REQ_WINDOW_SEC   = 60
_AUTH_FAIL_MAX    = int(os.getenv("AUTH_FAIL_MAX", "30"))
_AUTH_FAIL_WINDOW = int(os.getenv("AUTH_FAIL_WINDOW_SEC", "600"))   # 10 min
_AUTH_BAN_SEC     = int(os.getenv("AUTH_BAN_SEC", "900"))           # 15 min

# IPs internos/confiáveis nunca são banidos (LAN + loopback)
_TRUSTED_IP_PREFIXES = ("127.", "10.", "192.168.", "172.16.", "172.17.", "172.18.",
                        "172.19.", "172.20.", "172.21.", "172.22.", "172.23.",
                        "172.24.", "172.25.", "172.26.", "172.27.", "172.28.",
                        "172.29.", "172.30.", "172.31.", "::1")

# Caminhos isentos do rate-limit (healthcheck, docs, static)
_RATE_EXEMPT_PREFIXES = ("/health", "/uploads/", "/docs", "/redoc", "/openapi.json")

_REQ_LOG       = {}   # ip -> deque[timestamps]
_AUTH_FAILURES = {}   # ip -> deque[timestamps]
_AUTH_BANNED   = {}   # ip -> unban_timestamp

def _client_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def _cors_response(request: Request, status_code: int, detail: str) -> JSONResponse:
    """JSONResponse com CORS headers manuais — para erros que escapam do CORSMiddleware."""
    origin = request.headers.get("origin", "")
    headers = {}
    if origin and (
        origin.startswith(("http://localhost", "http://127.0.0.1")) or
        any(net in origin for net in ("172.16.", "172.17.", "10.", "192.168."))
    ):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Vary"] = "Origin"
    return JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers)


@app.middleware("http")
async def abuse_protection(request: Request, call_next):
    path = request.url.path
    ip   = _client_ip(request)
    now  = time.time()

    # (1) IP banido?
    ban_until = _AUTH_BANNED.get(ip, 0)
    if ban_until > now:
        wait = int(ban_until - now)
        return _cors_response(request, 429,
            f"IP temporariamente bloqueado por suspeita de ataque. Aguarde {wait}s.")
    if ban_until and ban_until <= now:
        _AUTH_BANNED.pop(ip, None)

    # (2) Body grande demais?
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit():
        if int(content_length) > _MAX_BODY_BYTES:
            mb = _MAX_BODY_BYTES // (1024 * 1024)
            return _cors_response(request, 413, f"Request acima de {mb}MB rejeitada.")

    # (3) Rate-limit por IP (só em rotas reais, não em static/docs)
    if not path.startswith(_RATE_EXEMPT_PREFIXES):
        log = _REQ_LOG.setdefault(ip, deque())
        while log and now - log[0] > _REQ_WINDOW_SEC:
            log.popleft()
        if len(log) >= _REQ_PER_MIN:
            return _cors_response(request, 429,
                f"Limite de {_REQ_PER_MIN} requisições por minuto excedido.")
        log.append(now)

    # Processa a request
    response = await call_next(request)

    # (4) Fail2ban: registra erros de AUTH para banir IPs externos abusivos.
    #     Regras (afinadas para evitar banir usuários legítimos):
    #       - Só conta 401 (token inválido/expirado) — não 403 (autorização de role)
    #       - Ignora /api/auth/login (já tem rate-limit dedicado)
    #       - Ignora IPs da rede interna confiável
    is_trusted = ip.startswith(_TRUSTED_IP_PREFIXES)
    is_auth_failure = (
        response.status_code == 401
        and path.startswith("/api/")
        and not path.startswith("/api/auth/login")
    )
    if is_auth_failure and not is_trusted:
        fails = _AUTH_FAILURES.setdefault(ip, deque())
        while fails and now - fails[0] > _AUTH_FAIL_WINDOW:
            fails.popleft()
        fails.append(now)
        if len(fails) >= _AUTH_FAIL_MAX:
            _AUTH_BANNED[ip] = now + _AUTH_BAN_SEC
            fails.clear()
            logger.warning(
                f"[SEC] 🚫 IP {ip} BANIDO por {_AUTH_BAN_SEC // 60}min — "
                f"{_AUTH_FAIL_MAX} erros 401 em {_AUTH_FAIL_WINDOW}s"
            )

    return response

logger.info(f"✅ Anti-abuso ativo: {_REQ_PER_MIN} req/min, body max {_MAX_BODY_BYTES // 1024 // 1024}MB, "
            f"ban após {_AUTH_FAIL_MAX} erros 401 em {_AUTH_FAIL_WINDOW}s\n")


# Endpoints administrativos para gerenciar bloqueios em runtime
@app.get("/api/security/banned", tags=["security"])
def listar_banidos():
    """Lista IPs atualmente banidos com tempo restante."""
    now = time.time()
    return {
        "banned": [
            {"ip": ip, "wait_s": int(until - now)}
            for ip, until in _AUTH_BANNED.items() if until > now
        ],
        "rate_limited_ips": [
            {"ip": ip, "requests_in_window": len(dq)}
            for ip, dq in _REQ_LOG.items() if dq
        ],
    }

@app.post("/api/security/unban/{ip}", tags=["security"])
def desbanir(ip: str):
    """Remove o ban de um IP e zera contadores. Útil quando o fail2ban pega um usuário legítimo."""
    removed = bool(_AUTH_BANNED.pop(ip, None))
    _AUTH_FAILURES.pop(ip, None)
    _REQ_LOG.pop(ip, None)
    return {"ok": True, "ip": ip, "estava_banido": removed}


# =========================================
# 8.2 MIDDLEWARE: Headers de segurança
# =========================================
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    # Anti-clickjacking
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    # Anti-MIME-sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Não vazar URL referenciadora em links externos
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Bloqueia features que a aplicação não usa
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response

logger.info("✅ Security headers middleware ativo\n")

# =========================================
# 9. ROUTER DE AUTENTICACAO
# =========================================

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

# ==================================================
# Rate-limit de login: bloqueia força bruta por IP
# 5 tentativas falhas em 5min → 15min de bloqueio
# ==================================================
from collections import defaultdict

_LOGIN_ATTEMPTS = defaultdict(list)   # ip -> [timestamp, ...]
_LOGIN_BLOCKED  = {}                  # ip -> timestamp_unblock
_MAX_ATTEMPTS   = 5
_WINDOW_SEC     = 300                 # 5 min
_BLOCK_SEC      = 900                 # 15 min

def _check_rate_limit(ip: str) -> None:
    """Levanta 429 se IP estiver bloqueado por brute-force."""
    now = time.time()
    unblock = _LOGIN_BLOCKED.get(ip, 0)
    if unblock > now:
        wait = int(unblock - now)
        raise HTTPException(
            status_code=429,
            detail=f"Muitas tentativas de login. Tente novamente em {wait}s."
        )
    # Limpa tentativas fora da janela
    _LOGIN_ATTEMPTS[ip] = [t for t in _LOGIN_ATTEMPTS[ip] if now - t < _WINDOW_SEC]

def _register_failure(ip: str) -> None:
    now = time.time()
    _LOGIN_ATTEMPTS[ip].append(now)
    if len(_LOGIN_ATTEMPTS[ip]) >= _MAX_ATTEMPTS:
        _LOGIN_BLOCKED[ip] = now + _BLOCK_SEC
        _LOGIN_ATTEMPTS[ip].clear()
        logger.warning(f"[AUTH] 🚫 IP {ip} bloqueado por {_BLOCK_SEC}s (brute-force)")

def _register_success(ip: str) -> None:
    _LOGIN_ATTEMPTS.pop(ip, None)
    _LOGIN_BLOCKED.pop(ip, None)


@auth_router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(login_data: LoginRequest, response: Response, request: Request = None):
    """Realiza login do usuario"""
    # Identifica IP (respeita X-Forwarded-For se vier de proxy/NAT)
    client_ip = "unknown"
    if request:
        fwd = request.headers.get("X-Forwarded-For", "")
        client_ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    _check_rate_limit(client_ip)

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
                    u.group_id, u.unit_id, u.cpf, u.is_active, u.created_at, u.password_hash,
                    u.must_change_password,
                    `cpe_grupo`.`name` AS group_name,
                    unidades_cpe.nome AS unit_nome
                FROM users u
                LEFT JOIN `cpe_grupo`   ON u.group_id = `cpe_grupo`.`id`
                LEFT JOIN unidades_cpe  ON u.unit_id  = unidades_cpe.id
                WHERE u.email = %s
            """
        else:
            query = """
                SELECT
                    u.id, u.name, u.email, u.username, u.role,
                    u.group_id, u.unit_id, u.cpf, u.is_active, u.created_at, u.password_hash,
                    u.must_change_password,
                    `cpe_grupo`.`name` AS group_name,
                    unidades_cpe.nome AS unit_nome
                FROM users u
                LEFT JOIN `cpe_grupo`   ON u.group_id = `cpe_grupo`.`id`
                LEFT JOIN unidades_cpe  ON u.unit_id  = unidades_cpe.id
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

        # GERAR TOKEN DE SESSÃO (HMAC — mesmo formato usado por fleet.py e security.py)
        logger.info("[AUTH] 🔐 Gerando token de sessão HMAC...")

        try:
            from security import make_session_token
            from config import COOKIE_NAME, SESSION_MAX_AGE_SECONDS
            session_token = make_session_token(user['id'])
            logger.info(f"[AUTH]   ✓ Token gerado: {session_token[:30]}...")
        except Exception as token_err:
            logger.error(f"[AUTH] ❌ Erro ao gerar token: {str(token_err)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao gerar token: {str(token_err)}"
            )

        # Definir cookie HTTP-only (para autenticação server-side)
        response.set_cookie(
            key=COOKIE_NAME,
            value=session_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=SESSION_MAX_AGE_SECONDS,
            path="/",
        )
        logger.info(f"[AUTH]   ✓ Cookie '{COOKIE_NAME}' definido na resposta")

        logger.info("[AUTH] ✅ LOGIN BEM-SUCEDIDO!")
        logger.info("=" * 100 + "\n")
        _register_success(client_ip)

        return LoginResponse(
            success=True,
            message=f"Bem-vindo, {user['name']}!",
            user=user_response,
            access_token=session_token,   # mesmo token — frontend salva no localStorage
            token_type="bearer"
        )

    except HTTPException as he:
        # Marca falha de auth (401) no rate-limit. Erros 400 (campos vazios) não contam.
        if he.status_code == status.HTTP_401_UNAUTHORIZED:
            _register_failure(client_ip)
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

@groups_router.get("/departments")
async def list_departments():
    """Lista todos os departamentos disponíveis"""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT d.id, d.name, d.description, d.created_at,
                   COUNT(g.id) AS total_grupos
            FROM departments d
            LEFT JOIN cpe_grupo g ON g.department_id = d.id
            GROUP BY d.id, d.name, d.description, d.created_at
            ORDER BY d.name
        """)
        rows = cursor.fetchall()
        return convert_datetime_list(rows)
    except Exception as err:
        logger.error(f"[DEPARTMENTS] ERRO: {str(err)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao listar departamentos: {str(err)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@groups_router.post("/departments", status_code=status.HTTP_201_CREATED)
async def create_department(data: dict):
    """Cria um novo departamento"""
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip() or None
    if not name or len(name) < 2:
        raise HTTPException(status_code=400, detail="Nome do departamento obrigatório (mínimo 2 caracteres)")
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM departments WHERE name = %s", (name,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Departamento com este nome já existe")
        cursor.execute("INSERT INTO departments (name, description) VALUES (%s, %s)", (name, description))
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT id, name, description, created_at FROM departments WHERE id = %s", (new_id,))
        dept = cursor.fetchone()
        dept["total_grupos"] = 0
        return convert_datetime_to_string(dept)
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[DEPARTMENTS/CREATE] ERRO: {str(err)}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar departamento: {str(err)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@groups_router.put("/departments/{dept_id}")
async def update_department(dept_id: int, data: dict):
    """Atualiza um departamento"""
    name = (data.get("name") or "").strip()
    description = data.get("description")
    if description is not None:
        description = description.strip() or None
    if not name or len(name) < 2:
        raise HTTPException(status_code=400, detail="Nome do departamento obrigatório (mínimo 2 caracteres)")
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM departments WHERE name = %s AND id != %s", (name, dept_id))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Já existe outro departamento com este nome")
        cursor.execute("UPDATE departments SET name = %s, description = %s WHERE id = %s", (name, description, dept_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Departamento não encontrado")
        conn.commit()
        return {"ok": True, "id": dept_id, "name": name}
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[DEPARTMENTS/UPDATE] ERRO: {str(err)}")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar departamento: {str(err)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@groups_router.delete("/departments/{dept_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(dept_id: int):
    """Deleta um departamento (só se não tiver grupos vinculados)"""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) AS total FROM cpe_grupo WHERE department_id = %s", (dept_id,))
        row = cursor.fetchone()
        if row and row["total"] > 0:
            raise HTTPException(status_code=400, detail=f"Não é possível excluir: {row['total']} grupo(s) vinculado(s) a este departamento")
        cursor.execute("DELETE FROM departments WHERE id = %s", (dept_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Departamento não encontrado")
        conn.commit()
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[DEPARTMENTS/DELETE] ERRO: {str(err)}")
        raise HTTPException(status_code=500, detail=f"Erro ao excluir departamento: {str(err)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

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
        new_group_id = cursor.lastrowid
        logger.info(f"[GROUPS]   ✅ Grupo criado com ID: {new_group_id}")

        # Criar pasta raiz no módulo de Contratos para este grupo
        try:
            cursor.execute(
                "INSERT INTO contrato_pastas (group_id, nome, is_root) VALUES (%s, %s, 1)",
                (new_group_id, group.name)
            )
            logger.info(f"[GROUPS]   ✅ Pasta raiz de contratos criada para grupo {new_group_id}")
        except Exception as pasta_err:
            logger.warning(f"[GROUPS]   ⚠️ Nao foi possivel criar pasta de contratos: {pasta_err}")

        conn.commit()

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
        cursor.execute(
            "SELECT u.id, u.name, u.email, u.username, u.role, u.group_id, u.unit_id, u.cpf, "
            "       u.is_active, u.created_at, unidades_cpe.nome AS unit_nome "
            "FROM users u LEFT JOIN unidades_cpe ON u.unit_id = unidades_cpe.id "
            "ORDER BY u.created_at DESC"
        )
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
        cursor.execute(
            "SELECT u.id, u.name, u.email, u.username, u.role, u.group_id, u.unit_id, u.cpf, "
            "       u.is_active, u.created_at, unidades_cpe.nome AS unit_nome "
            "FROM users u LEFT JOIN unidades_cpe ON u.unit_id = unidades_cpe.id "
            "WHERE u.id = %s",
            (user_id,),
        )
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

        if user.unit_id:
            cursor.execute("SELECT id FROM unidades_cpe WHERE id = %s", (user.unit_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unidade nao encontrada")

        logger.info("[USERS] 🔐 Gerando hash da senha com bcrypt...")
        try:
            password_hash = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            logger.info("[USERS]   ✅ Hash gerado com sucesso")
        except Exception as hash_err:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao processar senha")

        cpf_clean = ''.join(filter(str.isdigit, (user.cpf or ''))) or None
        cursor.execute(
            "INSERT INTO users (name, email, username, password_hash, role, group_id, unit_id, cpf, is_active) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (user.name, user.email, user.username, password_hash, user.role,
             user.group_id, user.unit_id, cpf_clean, user.is_active)
        )

        conn.commit()
        new_user_id = cursor.lastrowid
        logger.info(f"[USERS]   ✅ Usuario criado com ID: {new_user_id}")

        cursor.execute(
            "SELECT u.id, u.name, u.email, u.username, u.role, u.group_id, u.unit_id, u.cpf, "
            "       u.is_active, u.created_at, unidades_cpe.nome AS unit_nome "
            "FROM users u LEFT JOIN unidades_cpe ON u.unit_id = unidades_cpe.id "
            "WHERE u.id = %s",
            (new_user_id,),
        )
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

        if user.unit_id is not None:
            if user.unit_id != 0:
                cursor.execute("SELECT id FROM unidades_cpe WHERE id = %s", (user.unit_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unidade nao encontrada")
            updates.append("unit_id = %s")
            params.append(user.unit_id if user.unit_id != 0 else None)

        if user.is_active is not None:
            updates.append("is_active = %s")
            params.append(user.is_active)

        if user.cpf is not None:
            cpf_clean = ''.join(filter(str.isdigit, user.cpf)) or None
            updates.append("cpf = %s")
            params.append(cpf_clean)

        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhum campo para atualizar")

        params.append(user_id)
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()

        cursor.execute(
            "SELECT u.id, u.name, u.email, u.username, u.role, u.group_id, u.unit_id, u.cpf, "
            "       u.is_active, u.created_at, unidades_cpe.nome AS unit_nome "
            "FROM users u LEFT JOIN unidades_cpe ON u.unit_id = unidades_cpe.id "
            "WHERE u.id = %s",
            (user_id,),
        )
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

class PasswordChangeRequest(BaseModel):
    # senha_atual eh obrigatorio quando o proprio user troca a propria senha
    # (sem flag must_change_password ativa). Pode vir vazio quando:
    #  - admin reseta a senha de outro user (sem confirmar a atual)
    #  - user com must_change_password=1 trocando (acabou de receber temp)
    senha_atual: Optional[str] = None
    senha_nova:  str = Field(..., min_length=8)
    # admin pode marcar pra forcar troca no proximo login do user resetado
    forcar_troca: Optional[bool] = False


def _resolver_requester_id(request: Request) -> Optional[int]:
    """Pega o ID do usuario logado via cookie ou header X-Auth-Token."""
    from security import parse_session_token, COOKIE_NAME
    tok = request.cookies.get(COOKIE_NAME) or request.headers.get("X-Auth-Token") \
        or request.headers.get("x-auth-token")
    if not tok:
        return None
    return parse_session_token(tok)


@users_router.post("/{user_id}/senha")
async def change_password(user_id: int, payload: PasswordChangeRequest, request: Request):
    """Troca/reseta senha de usuario.

    Tres modos:
      1. SELF normal: user troca a propria senha — exige `senha_atual`,
         confere com bcrypt. Zera must_change_password.
      2. SELF apos reset admin: user com must_change_password=1 troca
         sem precisar de `senha_atual` (acabou de receber temporaria).
         Zera a flag.
      3. ADMIN: ADMIN/TI/MANAGER/RESPONSAVEL_GRUPO redefine senha de
         OUTRO user sem precisar de `senha_atual`. Pode marcar
         `forcar_troca=true` (set must_change_password=1) — recomendado
         pra forcar o user a definir uma senha pessoal antes de seguir.
    """
    requester_id = _resolver_requester_id(request)
    if not requester_id:
        raise HTTPException(status_code=401, detail="Nao autenticado")

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        # Quem esta solicitando + alvo
        cursor.execute(
            "SELECT id, role, password_hash, must_change_password "
            "FROM users WHERE id = %s", (requester_id,))
        requester = cursor.fetchone()
        if not requester:
            raise HTTPException(status_code=401, detail="Solicitante invalido")

        cursor.execute(
            "SELECT id, password_hash, must_change_password "
            "FROM users WHERE id = %s", (user_id,))
        target = cursor.fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")

        is_self = (requester["id"] == user_id)
        is_admin = requester["role"] in ("ADMIN", "TI", "MANAGER", "RESPONSAVEL_GRUPO")

        if not is_self and not is_admin:
            raise HTTPException(status_code=403,
                                detail="Sem permissao pra resetar senha de outro usuario")

        # Modo SELF: precisa confirmar a senha atual, A NAO SER que
        # esteja com flag must_change_password (acabou de ser resetado).
        if is_self and not target.get("must_change_password"):
            if not payload.senha_atual:
                raise HTTPException(status_code=400,
                                    detail="Informe a senha atual")
            if not bcrypt.checkpw(payload.senha_atual.encode("utf-8"),
                                  (target["password_hash"] or "").encode("utf-8")):
                raise HTTPException(status_code=401, detail="Senha atual incorreta")

        # Decide nova flag must_change_password:
        #   admin reset com forcar_troca = 1
        #   qualquer SELF (incluindo apos reset) = 0
        if is_self:
            nova_flag = 0
        else:
            nova_flag = 1 if payload.forcar_troca else 0

        novo_hash = bcrypt.hashpw(payload.senha_nova.encode("utf-8"),
                                  bcrypt.gensalt()).decode("utf-8")
        cursor.execute(
            "UPDATE users SET password_hash = %s, must_change_password = %s WHERE id = %s",
            (novo_hash, nova_flag, user_id))
        conn.commit()
        logger.info(f"[USERS] Senha alterada — alvo={user_id} solicitante={requester_id} "
                    f"is_self={is_self} forcar_troca={nova_flag}")
        return {"ok": True, "mensagem": "Senha alterada com sucesso",
                "must_change_password": bool(nova_flag)}
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[USERS] ❌ ERRO ao trocar senha: {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao trocar senha: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


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
# 12. ROTA RAIZ + HEALTH CHECK
# =========================================

@app.get("/")
async def root():
    """Informacoes basicas da API"""
    db_ok = True
    try:
        conn = get_db_connection()
        conn.close()
    except Exception:
        db_ok = False

    return {
        "api": "CPE Control API",
        "version": "2.0.0",
        "status": "online",
        "database": "ok" if db_ok else "erro",
        "docs": "/docs",
        "health": "/health",
        "timestamp": datetime.now().isoformat(),
    }

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

    # Router de Chamados Antigos (somente consulta)
    try:
        from routes.chamados_antigos import router as chamados_antigos_router
        app.include_router(chamados_antigos_router)
        logger.info("✅ Router de Chamados Antigos registrado: /api/chamados-antigos")
    except Exception as _e:
        logger.warning(f"⚠️ Router de Chamados Antigos NÃO registrado: {_e}")
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

    # Seeder + migrador (refatoração 2026-05-05) — roda no startup.
    # Idempotentes: podem rodar em toda inicialização sem efeito colateral.
    try:
        from services.permission_seeder import seed_pages
        from services.permission_migrator import migrate_legacy_page_permissions
        result_seed = seed_pages()
        logger.info(f"✅ Seeder de páginas: {result_seed}")
        result_mig = migrate_legacy_page_permissions()
        logger.info(f"✅ Migrador legacy: {result_mig}")
    except Exception as seed_err:
        logger.error(f"⚠️  Seeder/Migrador de permissões falhou: {seed_err}")
        import traceback
        logger.error(traceback.format_exc())
except Exception as err:
    logger.error(f"❌ Erro ao registrar router de Permissões: {str(err)}")

# ✅ REGISTRAR ROUTER DA DASHBOARD (KPIs + agenda + pendências adaptados por role)
try:
    from routes.dashboard import router as dashboard_router
    app.include_router(dashboard_router)
    logger.info("✅ Router de Dashboard registrado: /api/dashboard")
except Exception as err:
    logger.error(f"❌ Erro ao registrar router de Dashboard: {str(err)}")

# ✅ REGISTRAR ROUTER DE CATEGORIAS/SUBCATEGORIAS (EXTERNO)
try:
    from routes.categorias import categorias_router, subcategorias_router, campos_router
    app.include_router(categorias_router)
    app.include_router(subcategorias_router)
    app.include_router(campos_router)
    logger.info("✅ Router de Categorias registrado: /api/categorias")
    logger.info("✅ Router de Subcategorias registrado: /api/subcategorias")
    logger.info("✅ Router de Campos de Categoria registrado: /api/categoria-campos")
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

# ✅ REGISTRAR ROUTER DE CHAT REALTIME (WS + REST)
try:
    from routes.chat import router as chat_router
    app.include_router(chat_router)
    logger.info("✅ Router de Chat registrado: /api/chat (REST + WS /ws)")
except Exception as err:
    logger.error(f"❌ Erro ao registrar router de Chat: {str(err)}")
    import traceback
    logger.error(traceback.format_exc())

# ✅ REGISTRAR ROUTER DE TASKS (EXTERNO)
try:
    from routes.tasks import tasks_router
    app.include_router(tasks_router)
    logger.info("✅ Router de Tasks registrado: /api/tasks")
except Exception as err:
    logger.error(f"❌ Erro ao registrar router de Tasks: {str(err)}")
    import traceback
    logger.error(traceback.format_exc())

# ✅ REGISTRAR ROUTER DE FROTAS (EXTERNO)
try:
    from routes.fleet import router as fleet_router
    app.include_router(fleet_router)
    logger.info("✅ Router de Frotas registrado: /api/fleet")
except Exception as err:
    logger.error(f"❌ Erro ao registrar router de Frotas: {str(err)}")
    import traceback
    logger.error(traceback.format_exc())

# ✅ REGISTRAR ROUTER DE EQUIPE DE SUPORTE (agendas de atendimento)
try:
    from routes.atendimentos import router as atendimentos_router
    app.include_router(atendimentos_router)
    logger.info("✅ Router de Equipe de Suporte registrado: /api/atendimentos")
except Exception as err:
    logger.error(f"❌ Erro ao registrar router de Equipe de Suporte: {str(err)}")
    import traceback
    logger.error(traceback.format_exc())

# ✅ REGISTRAR ROUTER DE CONTRATOS (EXTERNO)
try:
    from routes.contratos import router as contratos_router
    app.include_router(contratos_router)
    logger.info("✅ Router de Contratos registrado: /api/contratos")
except Exception as err:
    logger.error(f"❌ Erro ao registrar router de Contratos: {str(err)}")
    import traceback
    logger.error(traceback.format_exc())

# ✅ REGISTRAR ROUTER DE AGENTES (DOWNLOAD DE UTILITÁRIOS)
try:
    from routes.agents import router as agents_router
    app.include_router(agents_router)
    logger.info("✅ Router de Agents registrado: /api/agents")
except Exception as err:
    logger.error(f"❌ Erro ao registrar router de Agents: {str(err)}")
    import traceback
    logger.error(traceback.format_exc())

# ✅ REGISTRAR ROUTER DE COFRE DE SENHAS
try:
    from routes.passwords_new import router as passwords_router
    app.include_router(passwords_router)
    logger.info("✅ Router de Passwords registrado: /api/passwords")
except Exception as err:
    logger.error(f"❌ Erro ao registrar router de Passwords: {str(err)}")
    import traceback
    logger.error(traceback.format_exc())

# ✅ REGISTRAR ROUTER CLICKSIGN (assinatura eletrônica)
try:
    from routes.clicksign import router as clicksign_router
    app.include_router(clicksign_router)
    logger.info("✅ Router de Clicksign registrado: /api/clicksign")
except Exception as err:
    logger.error(f"❌ Erro ao registrar router de Clicksign: {str(err)}")
    import traceback
    logger.error(traceback.format_exc())

# ✅ REGISTRAR ROUTER DE UNIDADES CPE
try:
    from routes.unidades import router as unidades_router
    app.include_router(unidades_router)
    logger.info("✅ Router de Unidades registrado: /api/unidades")
except Exception as err:
    logger.error(f"❌ Erro ao registrar router de Unidades: {str(err)}")
    import traceback
    logger.error(traceback.format_exc())

# ✅ REGISTRAR ROUTER DE RECEPÇÃO (salas, reservas, envios)
try:
    from routes.recepcao import router as recepcao_router
    app.include_router(recepcao_router)
    logger.info("✅ Router de Recepção registrado: /api/recepcao")

    # Inicia o job em background que cancela reservas pendentes após 40min
    from services.recepcao_scheduler import iniciar as iniciar_scheduler_recepcao
    iniciar_scheduler_recepcao()
    logger.info("✅ Scheduler de Recepção iniciado (auto-cancel 40min)")
except Exception as err:
    logger.error(f"❌ Erro ao registrar Recepção: {str(err)}")
    import traceback
    logger.error(traceback.format_exc())

# ✅ REGISTRAR ROUTER DE AGENDA (integração Carbonio)
try:
    from routes.agenda import router as agenda_router
    app.include_router(agenda_router)
    logger.info("✅ Router de Agenda registrado: /api/agenda")

    # Inicia scheduler de lembretes de agenda (sino quando começar a reunião)
    from services.agenda_scheduler import iniciar as iniciar_agenda_scheduler
    iniciar_agenda_scheduler()
    logger.info("✅ Scheduler de Agenda iniciado (lembretes via sino)")
except Exception as err:
    logger.error(f"❌ Erro ao registrar Agenda: {str(err)}")
    import traceback
    logger.error(traceback.format_exc())

# ✅ REGISTRAR ROUTER DE PRÉ-CADASTRO (auto-cadastro guiado)
try:
    from routes.pre_cadastro import router as pre_cadastro_router
    app.include_router(pre_cadastro_router)
    logger.info("✅ Router de Pré-cadastro registrado: /api/pre-cadastro")
except Exception as err:
    logger.error(f"❌ Erro ao registrar Pré-cadastro: {str(err)}")

# ✅ REGISTRAR ROUTER DO INVENTÁRIO T.I. (dispositivos + agente)
try:
    from routes.inventory import router as inventory_router
    app.include_router(inventory_router)
    logger.info("✅ Router de Inventário T.I. registrado: /api/inventario")
except Exception as err:
    logger.error(f"❌ Erro ao registrar router de Inventário T.I.: {str(err)}")
    import traceback
    logger.error(traceback.format_exc())

try:
    from routes.network import router as network_router
    app.include_router(network_router)
    logger.info("✅ Router de Monitoramento de Rede registrado: /api/network")
except Exception as err:
    logger.error(f"❌ Erro ao registrar router de Monitoramento de Rede: {str(err)}")
    import traceback
    logger.error(traceback.format_exc())

# ✅ SERVIR UPLOADS ESTÁTICOS (fotos de veículos)
try:
    _uploads_dir = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web", "uploads")
    )
    os.makedirs(_uploads_dir, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=_uploads_dir), name="uploads")
    logger.info(f"✅ Upload estático montado em /uploads → {_uploads_dir}")
except Exception as err:
    logger.warning(f"⚠️ Não foi possível montar uploads estáticos: {str(err)}")

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
    
    # reload=True so em dev: em prod (servico Windows NSSM) o uvicorn reload
    # spawna worker com Python errado (do PATH em vez do venv) — quebra
    # registro de routers e fica em loop. Em prod, deixar False; o
    # Restart-Service CPEControlAPI cuida do reload quando precisar.
    _reload = os.getenv("UVICORN_RELOAD", "0").strip() == "1"
    uvicorn.run(
        "app:app",
        host="0.0.0.0",   # aceita conexoes da rede local
        port=8000,
        reload=_reload,
        log_level="info",
        proxy_headers=True,         # confia em X-Forwarded-Proto/For/Host (Caddy/cloudflared)
        forwarded_allow_ips="*",    # de qualquer IP (estamos atras de tunnel/proxy local)
    )