"""
API de Tickets/Chamados - v3.1
Endpoints para criar, listar, atualizar e deletar tickets
Também inclui endpoints para interações (comentários/respostas)

📋 FEATURES:
  ✅ Logs detalhados para debug
  ✅ Validações robustas
  ✅ Tratamento de erros completo
  ✅ Notificações WebSocket
  ✅ Permissões granulares
  ✅ Filtros avançados
"""

from fastapi import APIRouter, HTTPException, status, Query, Depends
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import logging
import json
from app import get_db_or_404

logger = logging.getLogger(__name__)

# =========================================
# 🔧 CONFIGURAÇÕES
# =========================================

LOG_SEPARADOR = "=" * 100
VERSAO_API = "3.1"
LIMITE_PADRAO = 25
LIMITE_MAXIMO = 100

# =========================================
# 1️⃣ MODELOS PYDANTIC (Validação)
# =========================================

# --- TICKETS ---
class TicketCriar(BaseModel):
    """Modelo para criar novo ticket"""
    solicitante_id: int = Field(..., gt=0, description="ID do usuário solicitante")
    group_id: int = Field(..., gt=0, description="ID do grupo/departamento")
    categoria_id: Optional[int] = Field(None, description="ID da categoria")
    subcategoria_id: Optional[int] = Field(None, description="ID da subcategoria")
    prioridade_id: int = Field(default=2, ge=1, le=4, description="ID da prioridade (1-4)")
    assunto: str = Field(..., min_length=3, max_length=255, description="Assunto do ticket")
    descricao_inicial: str = Field(..., min_length=5, max_length=5000, description="Descrição detalhada")
    origem: str = Field(default="portal", description="Origem do ticket")
    responsavel_id: Optional[int] = Field(None, gt=0, description="ID do responsável")

    @validator('assunto')
    def assunto_nao_vazio(cls, v):
        if not v or not v.strip():
            raise ValueError('Assunto não pode estar vazio')
        return v.strip()

    @validator('descricao_inicial')
    def descricao_nao_vazia(cls, v):
        if not v or not v.strip():
            raise ValueError('Descrição não pode estar vazia')
        return v.strip()

class TicketAtualizar(BaseModel):
    """Modelo para atualizar ticket"""
    status_id: Optional[int] = Field(None, ge=1, le=4, description="ID do novo status")
    prioridade_id: Optional[int] = Field(None, ge=1, le=4, description="ID da nova prioridade")
    responsavel_id: Optional[int] = Field(None, gt=0, description="ID do novo responsável")
    group_id: Optional[int] = Field(None, gt=0, description="ID do novo grupo")
    assunto: Optional[str] = Field(None, min_length=3, max_length=255, description="Novo assunto")
    descricao_inicial: Optional[str] = Field(None, min_length=5, max_length=5000, description="Nova descrição")

class TicketResposta(BaseModel):
    """Resposta padrão de ticket"""
    id: int
    numero: str
    assunto: str
    descricao_inicial: str
    solicitante_id: int
    responsavel_id: Optional[int] = None
    group_id: int
    status_id: int
    prioridade_id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "numero": "SUP-2026-00001",
                "assunto": "Sistema não funciona",
                "descricao_inicial": "Não consigo acessar...",
                "solicitante_id": 5,
                "responsavel_id": 10,
                "group_id": 2,
                "status_id": 1,
                "prioridade_id": 3,
                "created_at": "2026-03-24T10:30:00",
                "updated_at": "2026-03-24T10:30:00"
            }
        }

# --- INTERAÇÕES ---
class InteracaoCriar(BaseModel):
    """Modelo para criar interação/comentário"""
    ticket_id: int = Field(..., gt=0, description="ID do ticket")
    usuario_id: int = Field(..., gt=0, description="ID do usuário que comenta")
    tipo: str = Field(default="resposta", description="Tipo: 'resposta', 'nota_interna', 'sistema'")
    publico: int = Field(default=1, ge=0, le=1, description="0=Interno, 1=Público")
    mensagem: str = Field(..., min_length=1, max_length=5000, description="Conteúdo da mensagem")

    @validator('tipo')
    def tipo_valido(cls, v):
        tipos_validos = ['resposta', 'nota_interna', 'sistema']
        if v not in tipos_validos:
            raise ValueError(f'Tipo inválido. Válidos: {tipos_validos}')
        return v

    @validator('mensagem')
    def mensagem_nao_vazia(cls, v):
        if not v or not v.strip():
            raise ValueError('Mensagem não pode estar vazia')
        return v.strip()

class InteracaoResposta(BaseModel):
    """Resposta de interação"""
    id: int
    ticket_id: int
    usuario_id: int
    usuario_nome: Optional[str] = None
    tipo: str
    publico: int
    mensagem: str
    created_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "ticket_id": 1,
                "usuario_id": 10,
                "usuario_nome": "João Silva",
                "tipo": "resposta",
                "publico": 1,
                "mensagem": "Problema resolvido!",
                "created_at": "2026-03-24T11:00:00"
            }
        }

# =========================================
# 2️⃣ UTILITÁRIOS E HELPERS
# =========================================

def log_inicio(endpoint: str, **kwargs):
    """Log de início de operação"""
    logger.info(f"\n{LOG_SEPARADOR}")
    logger.info(f"[TICKETS v{VERSAO_API}] 🚀 {endpoint.upper()}")
    logger.info(f"{LOG_SEPARADOR}")
    for chave, valor in kwargs.items():
        logger.info(f"  ├─ {chave}: {valor}")

def log_etapa(etapa: str, icon_status: str = "•", **kwargs):
    """Log de passo intermediário"""
    logger.info(f"  ├─ {icon_status} {etapa}")
    for chave, valor in kwargs.items():
        logger.info(f"  │  └─ {chave}: {valor}")

def log_fim(status: str, **kwargs):
    """Log de conclusão"""
    icons = {
        "sucesso": "✅",
        "erro": "❌",
        "aviso": "⚠️"
    }
    icon = icons.get(status, "•")
    logger.info(f"  └─ {icon} {status.upper()}")
    for chave, valor in kwargs.items():
        logger.info(f"     └─ {chave}: {valor}")
    logger.info(f"{LOG_SEPARADOR}\n")

def validar_ticket_existe(cursor, ticket_id: int) -> dict:
    """Valida se ticket existe e retorna seus dados"""
    cursor.execute(
        "SELECT id, numero, group_id FROM tickets WHERE id = %s",
        (ticket_id,)
    )
    ticket = cursor.fetchone()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket #{ticket_id} não encontrado"
        )
    return ticket

def validar_usuario_existe(cursor, usuario_id: int) -> dict:
    """Valida se usuário existe e retorna seus dados"""
    cursor.execute(
        "SELECT id, name, email FROM users WHERE id = %s",
        (usuario_id,)
    )
    usuario = cursor.fetchone()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuário #{usuario_id} não encontrado"
        )
    return usuario

def validar_grupo_existe(cursor, grupo_id: int) -> dict:
    """Valida se grupo existe e retorna seus dados"""
    cursor.execute(
        "SELECT id, name FROM password_groups WHERE id = %s",
        (grupo_id,)
    )
    grupo = cursor.fetchone()
    if not grupo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grupo #{grupo_id} não encontrado"
        )
    return grupo

def obter_ou_criar_status_id(cursor, nome_status: str = "Aberto") -> int:
    """Obtém ou cria status padrão"""
    cursor.execute(
        "SELECT id FROM ticket_status WHERE nome = %s LIMIT 1",
        (nome_status,)
    )
    resultado = cursor.fetchone()
    return resultado['id'] if resultado else 1

def gerar_numero_ticket(cursor, grupo_id: int) -> str:
    """Gera número único para ticket no formato PREFIX-YEAR-SEQUENTIAL"""
    
    # ✅ Obter prefixo do grupo
    cursor.execute(
        "SELECT name FROM password_groups WHERE id = %s",
        (grupo_id,)
    )
    grupo = cursor.fetchone()
    
    if not grupo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Grupo #{grupo_id} não encontrado"
        )
    
    prefixo_grupo = grupo['name'][:3].upper()
    
    # ✅ Contar tickets do ano atual para o grupo
    cursor.execute(
        """SELECT COUNT(*) as count FROM tickets 
           WHERE group_id = %s AND YEAR(created_at) = YEAR(NOW())""",
        (grupo_id,)
    )
    resultado_contagem = cursor.fetchone()
    sequencial = (resultado_contagem['count'] + 1) if resultado_contagem else 1
    
    # ✅ Montar número
    ano = datetime.now().year
    numero_ticket = f"{prefixo_grupo}-{ano}-{sequencial:05d}"
    
    return numero_ticket, grupo['name']

def converter_datetime_string(dados: dict) -> dict:
    """Converte datetime objects para strings ISO"""
    if not dados:
        return dados
    
    resultado = dict(dados)
    for chave, valor in resultado.items():
        if hasattr(valor, 'isoformat'):
            resultado[chave] = valor.isoformat()
    return resultado

def converter_datetime_lista(lista_dados: list) -> list:
    """Converte lista de dicts com datetime para strings"""
    return [converter_datetime_string(item) for item in lista_dados]

def enviar_notificacao_websocket(notificacao: dict, tipo_notificacao: str):
    """Envia notificação via WebSocket (async)"""
    try:
        from routes.websocket import manager
        import asyncio
        
        notificacao['type'] = tipo_notificacao
        notificacao['timestamp'] = datetime.now().isoformat()
        notificacao['api_version'] = VERSAO_API
        
        if tipo_notificacao == "ticket_criado":
            asyncio.create_task(
                manager.broadcast_to_user(
                    notificacao.get('solicitante_id'),
                    notificacao
                )
            )
        elif tipo_notificacao == "comentario_adicionado":
            asyncio.create_task(
                manager.broadcast_to_all(notificacao)
            )
        
        log_etapa("Notificação WebSocket", "📤", type=tipo_notificacao)
        
    except Exception as erro_ws:
        logger.warning(f"  │  └─ ⚠️ Erro WebSocket: {str(erro_ws)}")

# =========================================
# 3️⃣ ROUTERS
# =========================================

tickets_router = APIRouter(
    prefix="/api/tickets",
    tags=["tickets"],
    responses={
        400: {"description": "Dados inválidos"},
        404: {"description": "Recurso não encontrado"},
        500: {"description": "Erro interno do servidor"}
    }
)

interacoes_router = APIRouter(
    prefix="/api/ticket-interacoes",
    tags=["interações"],
    responses={
        400: {"description": "Dados inválidos"},
        404: {"description": "Recurso não encontrado"},
        500: {"description": "Erro interno do servidor"}
    }
)

# =========================================
# 4️⃣ ENDPOINTS DE TICKETS
# =========================================

@tickets_router.get(
    "/",
    response_model=List[dict],
    summary="Listar tickets",
    description="Obtém lista de todos os tickets com filtros opcionais"
)
async def obter_tickets(
    grupo_id: Optional[int] = Query(None, description="Filtrar por grupo"),
    status_id: Optional[int] = Query(None, description="Filtrar por status"),
    responsavel_id: Optional[int] = Query(None, description="Filtrar por responsável"),
    prioridade_id: Optional[int] = Query(None, description="Filtrar por prioridade"),
    pular: int = Query(0, ge=0, description="Registros a pular"),
    limite: int = Query(LIMITE_PADRAO, ge=1, le=LIMITE_MAXIMO, description="Limite de registros")
):
    """
    Obtém tickets com filtros opcionais
    
    **Parâmetros:**
    - **grupo_id**: Filtrar por grupo (opcional)
    - **status_id**: Filtrar por status 1=Aberto, 2=Andamento, 3=Resolvido, 4=Fechado (opcional)
    - **responsavel_id**: Filtrar por responsável (opcional)
    - **prioridade_id**: Filtrar por prioridade 1=Baixa, 2=Normal, 3=Alta, 4=Urgente (opcional)
    - **pular**: Quantidade de registros a pular (paginação)
    - **limite**: Quantidade de registros retornar (padrão: 25, máximo: 100)
    
    **Exemplo:**
    ```
    GET /api/tickets?status_id=1&limite=10&pular=0
    ```
    """
    
    log_inicio(
        "obter_tickets",
        grupo_id=grupo_id,
        status_id=status_id,
        responsavel_id=responsavel_id,
        prioridade_id=prioridade_id,
        pular=pular,
        limite=limite
    )
    
    conexao = get_db_or_404()
    cursor = None
    
    try:
        cursor = conexao.cursor(dictionary=True)
        
        # ✅ Construir query dinâmica com filtros
        filtros = []
        parametros = []
        
        if grupo_id:
            filtros.append("t.group_id = %s")
            parametros.append(grupo_id)
            log_etapa("Filtro grupo", "🔍", grupo_id=grupo_id)
        
        if status_id:
            filtros.append("t.status_id = %s")
            parametros.append(status_id)
            log_etapa("Filtro status", "🔍", status_id=status_id)
        
        if responsavel_id:
            filtros.append("t.responsavel_id = %s")
            parametros.append(responsavel_id)
            log_etapa("Filtro responsável", "🔍", responsavel_id=responsavel_id)
        
        if prioridade_id:
            filtros.append("t.prioridade_id = %s")
            parametros.append(prioridade_id)
            log_etapa("Filtro prioridade", "🔍", prioridade_id=prioridade_id)
        
        clausula_where = "WHERE " + " AND ".join(filtros) if filtros else ""
        
        # ✅ Query principal
        query = f"""
            SELECT 
                t.id,
                t.numero,
                t.assunto,
                t.descricao_inicial,
                t.solicitante_id,
                t.responsavel_id,
                t.group_id,
                t.categoria_id,
                t.status_id,
                t.prioridade_id,
                t.created_at,
                t.updated_at,
                u.name as solicitante_nome,
                u.email as solicitante_email,
                r.name as responsavel_nome,
                g.name as group_name
            FROM tickets t
            LEFT JOIN users u ON t.solicitante_id = u.id
            LEFT JOIN users r ON t.responsavel_id = r.id
            LEFT JOIN password_groups g ON t.group_id = g.id
            {clausula_where}
            ORDER BY t.created_at DESC
            LIMIT %s OFFSET %s
        """
        
        parametros.extend([limite, pular])
        cursor.execute(query, parametros)
        tickets = cursor.fetchall()
        tickets = converter_datetime_lista(tickets)
        
        log_fim(
            "sucesso",
            total=len(tickets),
            tamanho_pagina=limite,
            offset=pular
        )
        
        return tickets or []
        
    except Exception as erro:
        log_fim("erro", erro=str(erro))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar tickets: {str(erro)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

# =========================================

@tickets_router.get(
    "/{ticket_id}",
    response_model=dict,
    summary="Obter ticket",
    description="Obtém detalhes completos de um ticket específico"
)
async def obter_ticket(ticket_id: int = Query(..., gt=0, description="ID do ticket")):
    """Obtém um ticket específico com todos os detalhes"""
    
    log_inicio("obter_ticket_detalhe", ticket_id=ticket_id)
    
    conexao = get_db_or_404()
    cursor = None
    
    try:
        cursor = conexao.cursor(dictionary=True)
        
        # ✅ Validar existência
        log_etapa("Validando ticket", "🔍")
        verificacao_ticket = validar_ticket_existe(cursor, ticket_id)
        log_etapa("Ticket validado", "✓", numero=verificacao_ticket['numero'])
        
        # ✅ Query detalhada
        query = """
            SELECT 
                t.id,
                t.numero,
                t.assunto,
                t.descricao_inicial,
                t.solicitante_id,
                t.responsavel_id,
                t.group_id,
                t.categoria_id,
                t.subcategoria_id,
                t.status_id,
                t.prioridade_id,
                t.origem,
                t.primeira_resposta_em,
                t.resolvido_em,
                t.fechado_em,
                t.created_at,
                t.updated_at,
                u.name as solicitante_nome,
                u.email as solicitante_email,
                r.name as responsavel_nome,
                g.name as group_name
            FROM tickets t
            LEFT JOIN users u ON t.solicitante_id = u.id
            LEFT JOIN users r ON t.responsavel_id = r.id
            LEFT JOIN password_groups g ON t.group_id = g.id
            WHERE t.id = %s
        """
        
        cursor.execute(query, (ticket_id,))
        ticket = cursor.fetchone()
        ticket = converter_datetime_string(ticket)
        
        log_fim("sucesso", numero=ticket['numero'], status_id=ticket['status_id'])
        return ticket
        
    except HTTPException:
        raise
    except Exception as erro:
        log_fim("erro", erro=str(erro))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter ticket: {str(erro)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

# =========================================

@tickets_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=TicketResposta,
    summary="Criar ticket",
    description="Cria um novo ticket no sistema"
)
async def criar_ticket(ticket: TicketCriar):
    """
    Cria um novo ticket no sistema
    
    **Validações:**
    - Solicitante deve existir
    - Grupo deve existir
    - Assunto: mínimo 3 caracteres
    - Descrição: mínimo 5 caracteres
    - Prioridade: 1-4
    
    **Número do ticket** é gerado automaticamente no formato:
    **[PREFIXO_GRUPO]-[ANO]-[SEQUENCIAL]**
    
    Exemplo: **SUP-2026-00001**
    
    **Status padrão:** Aberto (ID=1)
    """
    
    log_inicio(
        "criar_ticket",
        solicitante_id=ticket.solicitante_id,
        grupo_id=ticket.group_id,
        prioridade_id=ticket.prioridade_id,
        assunto=ticket.assunto[:50]
    )
    
    conexao = get_db_or_404()
    cursor = None
    
    try:
        cursor = conexao.cursor(dictionary=True)
        
        # ✅ VALIDAÇÃO 1: Solicitante existe
        log_etapa("Validando solicitante", "🔍", usuario_id=ticket.solicitante_id)
        solicitante = validar_usuario_existe(cursor, ticket.solicitante_id)
        log_etapa("Solicitante OK", "✓", nome=solicitante['name'])
        
        # ✅ VALIDAÇÃO 2: Grupo existe
        log_etapa("Validando grupo", "🔍", grupo_id=ticket.group_id)
        grupo = validar_grupo_existe(cursor, ticket.group_id)
        log_etapa("Grupo OK", "✓", nome=grupo['name'])
        
        # ✅ VALIDAÇÃO 3: Se tem responsável, valida
        if ticket.responsavel_id:
            log_etapa("Validando responsável", "🔍", usuario_id=ticket.responsavel_id)
            responsavel = validar_usuario_existe(cursor, ticket.responsavel_id)
            log_etapa("Responsável OK", "✓", nome=responsavel['name'])
        
        # ✅ Gerar número único
        log_etapa("Gerando número", "📝")
        numero, nome_grupo = gerar_numero_ticket(cursor, ticket.group_id)
        log_etapa("Número gerado", "✓", numero=numero)
        
        # ✅ Obter status padrão
        log_etapa("Obtendo status padrão", "📝")
        status_id = obter_ou_criar_status_id(cursor, "Aberto")
        log_etapa("Status definido", "✓", status_id=status_id)
        
        # ✅ Inserir ticket
        log_etapa("Inserindo ticket no banco", "💾")
        query_insercao = """
            INSERT INTO tickets (
                numero, solicitante_id, responsavel_id, group_id, 
                categoria_id, subcategoria_id, status_id, prioridade_id,
                assunto, descricao_inicial, origem, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        
        cursor.execute(query_insercao, (
            numero,
            ticket.solicitante_id,
            ticket.responsavel_id,
            ticket.group_id,
            ticket.categoria_id,
            ticket.subcategoria_id,
            status_id,
            ticket.prioridade_id,
            ticket.assunto,
            ticket.descricao_inicial,
            ticket.origem
        ))
        
        conexao.commit()
        novo_ticket_id = cursor.lastrowid
        log_etapa("Inserido no banco", "✓", ticket_id=novo_ticket_id)
        
        # ✅ Obter ticket criado
        cursor.execute(
            """SELECT id, numero, assunto, descricao_inicial, solicitante_id, 
                      responsavel_id, group_id, status_id, prioridade_id, 
                      created_at, updated_at
               FROM tickets WHERE id = %s""",
            (novo_ticket_id,)
        )
        novo_ticket = cursor.fetchone()
        novo_ticket = converter_datetime_string(novo_ticket)
        
        log_etapa("Notificando via WebSocket", "📤")
        enviar_notificacao_websocket(
            {
                "ticket_id": novo_ticket_id,
                "numero": numero,
                "assunto": ticket.assunto,
                "solicitante_id": ticket.solicitante_id,
                "status": "sucesso"
            },
            "ticket_criado"
        )
        
        log_fim("sucesso", ticket_id=novo_ticket_id, numero=numero)
        return novo_ticket
        
    except HTTPException:
        raise
    except Exception as erro:
        log_fim("erro", erro=str(erro))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar ticket: {str(erro)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

# =========================================

@tickets_router.put(
    "/{ticket_id}",
    response_model=TicketResposta,
    summary="Atualizar ticket",
    description="Atualiza dados de um ticket existente"
)
async def atualizar_ticket(
    ticket_id: int = Query(..., gt=0, description="ID do ticket"),
    ticket: TicketAtualizar = None
):
    """
    Atualiza um ticket com novos valores
    
    **Campos que podem ser atualizados:**
    - status_id (1-4)
    - prioridade_id (1-4)
    - responsavel_id
    - group_id
    - assunto
    - descricao_inicial
    
    **Nota:** Apenas campos fornecidos serão atualizados
    """
    
    log_inicio("atualizar_ticket", ticket_id=ticket_id)
    
    conexao = get_db_or_404()
    cursor = None
    
    try:
        cursor = conexao.cursor(dictionary=True)
        
        # ✅ Validar existência
        log_etapa("Validando ticket", "🔍")
        verificacao_ticket = validar_ticket_existe(cursor, ticket_id)
        log_etapa("Ticket validado", "✓", numero=verificacao_ticket['numero'])
        
        # ✅ Construir updates dinamicamente
        atualizacoes = []
        parametros = []
        
        if ticket.status_id is not None:
            atualizacoes.append("status_id = %s")
            parametros.append(ticket.status_id)
            log_etapa("Atualizando", "✏️", campo="status_id", valor=ticket.status_id)
        
        if ticket.prioridade_id is not None:
            atualizacoes.append("prioridade_id = %s")
            parametros.append(ticket.prioridade_id)
            log_etapa("Atualizando", "✏️", campo="prioridade_id", valor=ticket.prioridade_id)
        
        if ticket.responsavel_id is not None:
            responsavel = validar_usuario_existe(cursor, ticket.responsavel_id)
            atualizacoes.append("responsavel_id = %s")
            parametros.append(ticket.responsavel_id)
            log_etapa("Atualizando", "✏️", campo="responsavel_id", valor=ticket.responsavel_id)
        
        if ticket.group_id is not None:
            grupo = validar_grupo_existe(cursor, ticket.group_id)
            atualizacoes.append("group_id = %s")
            parametros.append(ticket.group_id)
            log_etapa("Atualizando", "✏️", campo="group_id", valor=ticket.group_id)
        
        if ticket.assunto is not None:
            atualizacoes.append("assunto = %s")
            parametros.append(ticket.assunto)
            log_etapa("Atualizando", "✏️", campo="assunto", valor=ticket.assunto[:50])
        
        if ticket.descricao_inicial is not None:
            atualizacoes.append("descricao_inicial = %s")
            parametros.append(ticket.descricao_inicial)
            log_etapa("Atualizando", "✏️", campo="descricao_inicial", valor="[texto]")
        
        if not atualizacoes:
            log_fim("aviso", mensagem="Nenhum campo fornecido")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum campo fornecido para atualização"
            )
        
        # ✅ Adicionar timestamp
        atualizacoes.append("updated_at = NOW()")
        
        # ✅ Executar update
        log_etapa("Executando update", "💾")
        query_atualizacao = f"UPDATE tickets SET {', '.join(atualizacoes)} WHERE id = %s"
        parametros.append(ticket_id)
        
        cursor.execute(query_atualizacao, parametros)
        conexao.commit()
        log_etapa("Update executado", "✓")
        
        # ✅ Obter ticket atualizado
        cursor.execute(
            """SELECT id, numero, assunto, descricao_inicial, solicitante_id, 
                      responsavel_id, group_id, status_id, prioridade_id, 
                      created_at, updated_at
               FROM tickets WHERE id = %s""",
            (ticket_id,)
        )
        ticket_atualizado = cursor.fetchone()
        ticket_atualizado = converter_datetime_string(ticket_atualizado)
        
        log_fim("sucesso", numero=ticket_atualizado['numero'])
        return ticket_atualizado
        
    except HTTPException:
        raise
    except Exception as erro:
        log_fim("erro", erro=str(erro))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar ticket: {str(erro)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

# =========================================

@tickets_router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar ticket",
    description="Remove um ticket do sistema"
)
async def deletar_ticket(ticket_id: int = Query(..., gt=0, description="ID do ticket")):
    """Deleta um ticket do sistema"""
    
    log_inicio("deletar_ticket", ticket_id=ticket_id)
    
    conexao = get_db_or_404()
    cursor = None
    
    try:
        cursor = conexao.cursor(dictionary=True)
        
        # ✅ Validar existência
        log_etapa("Validando ticket", "🔍")
        verificacao_ticket = validar_ticket_existe(cursor, ticket_id)
        log_etapa("Ticket validado", "✓", numero=verificacao_ticket['numero'])
        
        # ✅ Deletar
        log_etapa("Deletando ticket", "🗑️")
        cursor.execute("DELETE FROM tickets WHERE id = %s", (ticket_id,))
        conexao.commit()
        log_etapa("Deletado do banco", "✓")
        
        log_fim("sucesso", ticket_id=ticket_id)
        
    except HTTPException:
        raise
    except Exception as erro:
        log_fim("erro", erro=str(erro))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar ticket: {str(erro)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

# =========================================
# 5️⃣ ENDPOINTS DE INTERAÇÕES (Comentários)
# =========================================

@interacoes_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=InteracaoResposta,
    summary="Criar interação",
    description="Adiciona um comentário ou resposta a um ticket"
)
async def criar_interacao(interacao: InteracaoCriar):
    """
    Cria um novo comentário/interação no ticket
    
    **Tipos de interação:**
    - `resposta` (padrão): Comentário público, solicitante vê
    - `nota_interna`: Comentário privado, apenas equipe vê
    - `sistema`: Mensagem gerada automaticamente
    
    **Visibilidade:**
    - `publico=1` (padrão): Solicitante vê
    - `publico=0`: Apenas equipe vê
    """
    
    log_inicio(
        "criar_interacao",
        ticket_id=interacao.ticket_id,
        usuario_id=interacao.usuario_id,
        tipo=interacao.tipo,
        publico=interacao.publico
    )
    
    conexao = get_db_or_404()
    cursor = None
    
    try:
        cursor = conexao.cursor(dictionary=True)
        
        # ✅ Validar ticket existe
        log_etapa("Validando ticket", "🔍")
        verificacao_ticket = validar_ticket_existe(cursor, interacao.ticket_id)
        log_etapa("Ticket OK", "✓", numero=verificacao_ticket['numero'])
        
        # ✅ Validar usuário existe
        log_etapa("Validando usuário", "🔍")
        verificacao_usuario = validar_usuario_existe(cursor, interacao.usuario_id)
        log_etapa("Usuário OK", "✓", nome=verificacao_usuario['name'])
        
        # ✅ Inserir interação
        log_etapa("Inserindo interação", "💾")
        cursor.execute("""
            INSERT INTO ticket_interacoes 
            (ticket_id, usuario_id, tipo, publico, mensagem, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (
            interacao.ticket_id,
            interacao.usuario_id,
            interacao.tipo,
            interacao.publico,
            interacao.mensagem
        ))
        
        conexao.commit()
        novo_id = cursor.lastrowid
        log_etapa("Inserida com ID", "✓", id=novo_id)
        
        # ✅ Obter interação criada
        cursor.execute("""
            SELECT ti.id, ti.ticket_id, ti.usuario_id, ti.tipo, ti.publico, 
                   ti.mensagem, ti.created_at, u.name as usuario_nome
            FROM ticket_interacoes ti
            LEFT JOIN users u ON ti.usuario_id = u.id
            WHERE ti.id = %s
        """, (novo_id,))
        
        resultado = cursor.fetchone()
        
        # ✅ Enviar notificação
        log_etapa("Notificando via WebSocket", "📤")
        enviar_notificacao_websocket(
            {
                "ticket_id": interacao.ticket_id,
                "usuario_id": interacao.usuario_id,
                "usuario_nome": verificacao_usuario['name'],
                "mensagem": interacao.mensagem[:100],
                "tipo": interacao.tipo,
                "publico": interacao.publico,
                "status": "sucesso"
            },
            "comentario_adicionado"
        )
        
        log_fim("sucesso", interacao_id=novo_id, tipo=interacao.tipo)
        
        return {
            "id": resultado['id'],
            "ticket_id": resultado['ticket_id'],
            "usuario_id": resultado['usuario_id'],
            "usuario_nome": resultado['usuario_nome'],
            "tipo": resultado['tipo'],
            "publico": resultado['publico'],
            "mensagem": resultado['mensagem'],
            "created_at": str(resultado['created_at'])
        }
        
    except HTTPException:
        raise
    except Exception as erro:
        log_fim("erro", erro=str(erro))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar interação: {str(erro)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

# =========================================

@interacoes_router.get(
    "/{ticket_id}",
    response_model=List[InteracaoResposta],
    summary="Listar interações",
    description="Obtém todos os comentários e respostas de um ticket"
)
async def obter_interacoes_ticket(ticket_id: int = Query(..., gt=0, description="ID do ticket")):
    """
    Lista todas as interações (comentários) de um ticket
    
    Retorna ordenado por data de criação (mais antigos primeiro)
    """
    
    log_inicio("obter_interacoes_ticket", ticket_id=ticket_id)
    
    conexao = get_db_or_404()
    cursor = None
    
    try:
        cursor = conexao.cursor(dictionary=True)
        
        # ✅ Validar ticket existe
        log_etapa("Validando ticket", "🔍")
        verificacao_ticket = validar_ticket_existe(cursor, ticket_id)
        log_etapa("Ticket OK", "✓", numero=verificacao_ticket['numero'])
        
        # ✅ Buscar interações
        log_etapa("Buscando interações", "🔍")
        cursor.execute("""
            SELECT ti.id, ti.ticket_id, ti.usuario_id, ti.tipo, ti.publico, 
                   ti.mensagem, ti.created_at, u.name as usuario_nome
            FROM ticket_interacoes ti
            LEFT JOIN users u ON ti.usuario_id = u.id
            WHERE ti.ticket_id = %s
            ORDER BY ti.created_at ASC
        """, (ticket_id,))
        
        interacoes = cursor.fetchall()
        
        resposta = [
            {
                "id": linha['id'],
                "ticket_id": linha['ticket_id'],
                "usuario_id": linha['usuario_id'],
                "usuario_nome": linha['usuario_nome'],
                "tipo": linha['tipo'],
                "publico": linha['publico'],
                "mensagem": linha['mensagem'],
                "created_at": str(linha['created_at'])
            }
            for linha in interacoes
        ]
        
        log_fim("sucesso", total=len(resposta))
        return resposta
        
    except HTTPException:
        raise
    except Exception as erro:
        log_fim("erro", erro=str(erro))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar interações: {str(erro)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()