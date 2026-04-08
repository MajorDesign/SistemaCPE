"""
API de Tickets/Chamados - v3.4
Endpoints para criar, listar, atualizar e deletar tickets
Inclui endpoints para interações (comentários/respostas)

Alterações v3.4:
- Migração de password_groups para groups no banco de dados
- validar_grupo_existe atualizado para groups (FK correta do banco)
- gerar_numero_ticket atualizado para groups
- gerar_id_alfanumerica atualizado para groups
- Todas as queries de SELECT atualizadas para groups

Alterações v3.3:
- PUT /tickets/{id} agora exige usuario_id e valida permissão por role
- POST /tickets ignora responsavel_id se solicitante for USER
- POST /ticket-interacoes bloqueia comentário interno para usuário USER
- Notificação de atribuição agora notifica o novo responsável corretamente
 """

from fastapi import APIRouter, HTTPException, status, Query, Path
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (
    get_db_or_404,
    convert_datetime_to_string,
    convert_datetime_list,
    DB_CONFIG
)

# Fallback para services (graceful degradation)
try:
    from services.notificacao_service import NotificacaoService
except Exception:
    class NotificacaoService:
        def __init__(self, *args, **kwargs):
            pass
        def notificar_novo_ticket(self, **kwargs):
            pass
        def notificar_status_alterado(self, **kwargs):
            pass
        def notificar_atribuicao(self, **kwargs):
            pass
        def notificar_nova_resposta(self, **kwargs):
            pass
        def notificar_comentario_interno(self, **kwargs):
            pass

try:
    from services.permissao_service import PermissaoService
except Exception:
    class PermissaoService:
        def __init__(self, *args, **kwargs):
            pass
        def usuario_pode_atribuir(self, **kwargs):
            return True
        def usuario_pode_mudar_status(self, **kwargs):
            return True
        def usuario_pode_responder(self, **kwargs):
            return True
        def usuario_pode_comentar_interno(self, **kwargs):
            return True

logger = logging.getLogger(__name__)
LOG_SEPARADOR = "=" * 100
VERSAO_API = "3.3"
LIMITE_PADRAO = 25
LIMITE_MAXIMO = 100

# Roles com permissão de gerenciamento
ROLES_ADMIN = {"ADMIN", "TI", "MANAGER"}

# =========================================
# 🆔 GERAÇÃO DE ID ALFANUMÉRICA
# =========================================

# ================================================== 
# 🆔 GERAÇÃO DE ID ALFANUMÉRICA
# Data: 06/04/2026 19:45
# ==================================================

def gerar_id_alfanumerica(ticket_id: int, group_id: int, cursor) -> str:
    """
    Gera ID alfanumérica no formato: AA9999B9C0
    
    Componentes:
    - AA (2 letras): código do setor (primeiras 2 letras do nome do grupo)
    - 9999 (4 números): ID do ticket (com zeros à esquerda)
    - B (1 letra): prioridade (U=urgente, A=alta, N=normal, B=baixa)
    - 9 (1 número): ano reduzido (último dígito do ano)
    - C (1 letra): categoria (T=técnico por padrão)
    - 0 (1 número): checksum (dígito verificador)
    
    Total: 10 caracteres
    
    Args:
        ticket_id: ID numérico do ticket (do banco)
        group_id: ID do grupo/setor
        cursor: cursor do banco para consultar dados
    
    Returns:
        str: ID alfanumérica formatada (ex: "TI0127U6T5")
    """
    
    logger.info(f"    🆔 Gerando ID alfanumérica...")
    logger.info(f"       - ticket_id: {ticket_id}")
    logger.info(f"       - group_id: {group_id}")
    
    try:
        # 1️⃣ OBTER CÓDIGO DO SETOR (2 letras)
        cursor.execute("SELECT name FROM `cpe_grupo` WHERE id = %s", (group_id,))
        grupo = cursor.fetchone()
        
        if grupo and grupo.get("name"):
            setor_code = grupo["name"][:2].upper()
        else:
            setor_code = "TI"  # Fallback
        
        logger.info(f"       - setor_code: {setor_code}")
        
        # 2️⃣ ID COM 4 DÍGITOS
        sequencial = str(ticket_id).zfill(4)[-4:]  # Últimos 4 dígitos
        logger.info(f"       - sequencial: {sequencial}")
        
        # 3️⃣ PRIORIDADE (padrão = N para Normal)
        prioridade = "N"  # Normal
        logger.info(f"       - prioridade: {prioridade}")
        
        # 4️⃣ ANO REDUZIDO (último dígito do ano)
        ano_reduzido = str(datetime.now().year)[-1]
        logger.info(f"       - ano_reduzido: {ano_reduzido}")
        
        # 5️⃣ CATEGORIA (padrão = T para Técnico)
        categoria = "T"
        logger.info(f"       - categoria: {categoria}")
        
        # 6️⃣ MONTAR ID SEM VERIFICADOR
        id_sem_verificador = setor_code + sequencial + prioridade + ano_reduzido + categoria
        logger.info(f"       - id_sem_verificador: {id_sem_verificador}")
        
        # 7️⃣ CALCULAR CHECKSUM (dígito verificador)
        soma_checksum = 0
        for i, char in enumerate(id_sem_verificador):
            char_code = ord(char)
            peso = i + 1
            soma_checksum += char_code * peso
        
        dígito_verificador = soma_checksum % 10
        logger.info(f"       - soma_checksum: {soma_checksum}")
        logger.info(f"       - dígito_verificador: {dígito_verificador}")
        
        # 8️⃣ MONTAR ID FINAL
        id_alfanumerica = id_sem_verificador + str(dígito_verificador)
        logger.info(f"    ✅ ID alfanumérica gerada: {id_alfanumerica}")
        
        return id_alfanumerica
    
    except Exception as e:
        logger.error(f"    ❌ Erro ao gerar ID alfanumérica: {str(e)}")
        # Retornar uma ID genérica como fallback
        return f"TKT{str(ticket_id).zfill(6)}"

# ================================================== 
# [FIM] 🆔 GERAÇÃO DE ID ALFANUMÉRICA
# Data: 06/04/2026 19:45
# ==================================================

# =========================================
# 🔧 MODELOS PYDANTIC
# =========================================

class TicketCriar(BaseModel):
    solicitante_id: int = Field(..., gt=0)
    group_id: int = Field(..., gt=0)
    categoria_id: Optional[int] = Field(None, gt=0)
    subcategoria_id: Optional[int] = Field(None, gt=0)
    prioridade_id: int = Field(default=2, ge=1, le=4)
    assunto: str = Field(..., min_length=3, max_length=255)
    descricao_inicial: str = Field(..., min_length=5, max_length=5000)
    origem: str = Field(default="portal")
    # ✅ responsavel_id é aceito no payload mas será ignorado para usuário USER
    responsavel_id: Optional[int] = Field(None, gt=0)

    @field_validator("assunto")
    @classmethod
    def validar_assunto(cls, v):
        if not v.strip():
            raise ValueError("assunto nao pode estar vazio")
        return v.strip()

    @field_validator("descricao_inicial")
    @classmethod
    def validar_descricao(cls, v):
        if not v.strip():
            raise ValueError("descricao inicial nao pode estar vazia")
        return v.strip()

class TicketAtualizar(BaseModel):
    status_id: Optional[int] = Field(None, ge=1, le=4)
    prioridade_id: Optional[int] = Field(None, ge=1, le=4)
    responsavel_id: Optional[int] = Field(None, gt=0)
    group_id: Optional[int] = Field(None, gt=0)
    assunto: Optional[str] = Field(None, min_length=3, max_length=255)
    descricao_inicial: Optional[str] = Field(None, min_length=5, max_length=5000)

class TicketResposta(BaseModel):
    id: int
    numero: str
    assunto: str
    solicitante_id: int
    responsavel_id: Optional[int] = None
    group_id: int
    status_id: int
    prioridade_id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class InteracaoCriar(BaseModel):
    ticket_id: int = Field(..., gt=0)
    usuario_id: int = Field(..., gt=0)
    tipo: str = Field(default="resposta")
    publico: int = Field(default=1, ge=0, le=1)
    mensagem: str = Field(..., min_length=1, max_length=5000)

    @field_validator("tipo")
    @classmethod
    def validar_tipo(cls, v):
        if v not in ["resposta", "nota_interna", "sistema", "interno"]:
            raise ValueError("tipo invalido")
        return v

    @field_validator("mensagem")
    @classmethod
    def validar_mensagem(cls, v):
        if not v.strip():
            raise ValueError("mensagem nao pode estar vazia")
        return v.strip()

class InteracaoResposta(BaseModel):
    id: int
    ticket_id: int
    usuario_id: int
    usuario_nome: Optional[str] = None
    tipo: str
    publico: int
    mensagem: str
    created_at: str

# =========================================
# 🛣️ ROUTERS
# =========================================

tickets_router = APIRouter(prefix="/api/tickets", tags=["tickets"])
interacoes_router = APIRouter(prefix="/api/ticket-interacoes", tags=["interacoes"])

# =========================================
# 🪵 LOGGING HELPERS
# =========================================

def log_inicio(endpoint: str, **kwargs):
    logger.info(f"\n{LOG_SEPARADOR}")
    logger.info(f"[TICKETS v{VERSAO_API}] {endpoint}")
    logger.info(f"{LOG_SEPARADOR}")
    for k, v in kwargs.items():
        logger.info(f"  - {k}: {v}")

def log_fim(status_text: str, **kwargs):
    icon = {"sucesso": "✅", "erro": "❌", "aviso": "⚠️"}.get(status_text, "•")
    logger.info(f"  {icon} {status_text.upper()}")
    for k, v in kwargs.items():
        logger.info(f"    > {k}: {v}")
    logger.info(LOG_SEPARADOR)

# =========================================
# ✅ VALIDAÇÕES
# =========================================

# =========================================
# ✅ VALIDAÇÕES
# =========================================

def validar_ticket_existe(cursor, ticket_id: int):
    cursor.execute(
        "SELECT id, numero, group_id, solicitante_id, responsavel_id FROM tickets WHERE id = %s",
        (ticket_id,)
    )
    ticket = cursor.fetchone()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket #{ticket_id} nao encontrado"
        )
    return ticket

def validar_usuario_existe(cursor, usuario_id: int):
    cursor.execute(
        "SELECT id, role, group_id FROM users WHERE id = %s AND is_active = 1",
        (usuario_id,)
    )
    user = cursor.fetchone()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario #{usuario_id} nao encontrado"
        )
    return user

def validar_grupo_existe(cursor, group_id: int):
    # ✅ CORRIGIDO: tickets.group_id agora referencia cpe_grupo (FK do banco)
    # Data: 06/04/2026 19:45
    cursor.execute("SELECT id FROM `cpe_grupo` WHERE id = %s", (group_id,))
    group = cursor.fetchone()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grupo #{group_id} nao encontrado"
        )
    return group

def obter_role_usuario(cursor, usuario_id: int) -> str:
    """Retorna o role do usuário ou lança 404 se não existir."""
    cursor.execute(
        "SELECT role FROM users WHERE id = %s AND is_active = 1",
        (usuario_id,)
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario #{usuario_id} nao encontrado ou inativo"
        )
    return row["role"] or "USER"

def gerar_numero_ticket(cursor, group_id: int):
    # ✅ CORRIGIDO: Atualizado para usar cpe_grupo
    # Data: 06/04/2026 19:45
    cursor.execute("SELECT name FROM `cpe_grupo` WHERE id = %s", (group_id,))
    g = cursor.fetchone()
    prefixo = (g["name"][:3].upper() if g and g.get("name") else "TKT")
    cursor.execute(
        "SELECT COUNT(*) as count FROM tickets WHERE group_id = %s AND YEAR(created_at) = YEAR(NOW())",
        (group_id,)
    )
    c = cursor.fetchone()
    seq = (c["count"] + 1) if c else 1
    return f"{prefixo}-{datetime.now().year}-{seq:05d}"

# ================================================== 
# [FIM] ✅ VALIDAÇÕES
# Data: 06/04/2026 19:45
# ==================================================

# ========================================
# 🔔 FUNÇÃO AUXILIAR - criar_notificacao_no_banco()
# Data: 31/03/2026 15:00
# ========================================

def criar_notificacao_no_banco(conexao, ticket_id: int, usuario_id: int, tipo: str, mensagem: str):
    """
    Cria notificação direto no banco de dados (fallback quando serviço está indisponível)
    
    Args:
        conexao: conexão MySQL
        ticket_id: ID do ticket
        usuario_id: ID do usuário a ser notificado
        tipo: tipo da notificação (status_alterado, atribuido, nova_resposta, etc)
        mensagem: mensagem da notificação
    """
    cursor = None
    try:
        cursor = conexao.cursor(dictionary=True)
        logger.info(f"    ▶️ Criando notificação no banco para #{usuario_id}...")
        
        cursor.execute(
            """
            INSERT INTO notificacoes (ticket_id, usuario_id, tipo, mensagem, lido, created_at, updated_at)
            VALUES (%s, %s, %s, %s, 0, NOW(), NOW())
            """,
            (ticket_id, usuario_id, tipo, mensagem)
        )
        conexao.commit()
        logger.info(f"    ✓ Notificação criada para #{usuario_id} | tipo: {tipo}")
        
    except Exception as e:
        logger.warning(f"    ⚠️ Erro ao criar notificação no banco para #{usuario_id}: {str(e)}")
    finally:
        if cursor:
            cursor.close()

# ========================================
# FIM DA FUNÇÃO - 31/03/2026 15:00
# ========================================

# ========================================
# FIM DA FUNÇÃO AUXILIAR - 31/03/2026 14:42
# ========================================

# =========================================
# 📌 ENDPOINTS DE TICKETS
# =========================================

@tickets_router.get("/", response_model=List[dict])
async def obter_tickets(
    usuario_id: int = Query(..., gt=0, description="ID do usuário logado (necessário para filtrar por acesso)"),
    grupo_id: Optional[int] = Query(None, gt=0),
    status_id: Optional[int] = Query(None, gt=0),
    responsavel_id: Optional[int] = Query(None, gt=0),
    prioridade_id: Optional[int] = Query(None, gt=0),
    pular: int = Query(0, ge=0),
    limite: int = Query(LIMITE_PADRAO, ge=1, le=LIMITE_MAXIMO)
):
    # ✅ CORRIGIDO: Adicionar filtro de acesso baseado em ROLE + GROUP_ID
    # Data: 06/04/2026 19:45
    log_inicio("obter_tickets", usuario_id=usuario_id, grupo_id=grupo_id, status_id=status_id)
    conexao = get_db_or_404()
    cursor = None
    try:
        cursor = conexao.cursor(dictionary=True)
        
        # ✅ STEP 1: Obter role e group_id do usuário logado
        logger.info(f"  ▶️ Validando acesso do usuário #{usuario_id}...")
        usuario = validar_usuario_existe(cursor, usuario_id)
        role_usuario = usuario.get("role") or "USER"
        group_id_usuario = usuario.get("group_id")
        
        logger.info(f"  ✓ Usuário encontrado: role={role_usuario}, group_id={group_id_usuario}")
        
        filtros, params = [], []

        # ✅ STEP 2: Filtro de ACESSO baseado em ROLE
        if role_usuario in ROLES_ADMIN:  # ADMIN, TI, MANAGER
            logger.info(f"  ✓ Usuário é {role_usuario} — pode ver TODOS os tickets")
            # Admin vê tudo
        elif role_usuario == "RESPONSAVEL_GRUPO":
            logger.info(f"  ✓ Usuário é RESPONSAVEL_GRUPO — pode ver TODOS do seu group_id={group_id_usuario}")
            # Responsável vê apenas tickets do seu grupo
            filtros.append("t.group_id = %s")
            params.append(group_id_usuario)
        else:  # USER
            logger.info(f"  ✓ Usuário é USER — pode ver todos os tickets do seu grupo (group_id={group_id_usuario})")
            # User vê todos os tickets do seu grupo (somente leitura se não for o responsável)
            filtros.append("t.group_id = %s")
            params.append(group_id_usuario)

        # ✅ STEP 3: Aplicar filtros adicionais do frontend
        if grupo_id:
            filtros.append("t.group_id = %s")
            params.append(grupo_id)
        if status_id:
            filtros.append("t.status_id = %s")
            params.append(status_id)
        if responsavel_id:
            filtros.append("t.responsavel_id = %s")
            params.append(responsavel_id)
        if prioridade_id:
            filtros.append("t.prioridade_id = %s")
            params.append(prioridade_id)

        where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
        
        logger.info(f"  ✓ Filtros montados: {len(filtros)} condição(ões)")
        if filtros:
            logger.info(f"    > {' AND '.join(filtros)}")

        sql = f"""
            SELECT
                t.*,
                u.name  AS solicitante_nome,
                u.email AS solicitante_email,
                r.name  AS responsavel_nome,
                g.name  AS group_name,
                ts.status        AS sla_status,
                ts.sla_minutos   AS sla_minutos,
                ts.iniciado_em   AS sla_iniciado_em,
                ts.pausado_em    AS sla_pausado_em,
                ts.minutos_pausados AS sla_minutos_pausados,
                ts.estourou_em   AS sla_estourou_em,
                ts.concluido_em  AS sla_concluido_em
            FROM tickets t
            LEFT JOIN users u            ON t.solicitante_id = u.id
            LEFT JOIN users r            ON t.responsavel_id = r.id
            LEFT JOIN `cpe_grupo` g      ON t.group_id = g.id
            LEFT JOIN ticket_sla ts      ON ts.ticket_id = t.id
            {where}
            ORDER BY t.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limite, pular])

        logger.info(f"  ▶️ Executando query com {len(params)} parâmetros...")
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        # Calcular status do SLA para cada ticket e embutir no retorno
        tickets = []
        for row in rows:
            row = dict(row)
            sla_dict = None
            if row.get("sla_status"):
                sla_raw = {
                    "status":           row.get("sla_status"),
                    "sla_minutos":      row.get("sla_minutos"),
                    "iniciado_em":      row.get("sla_iniciado_em"),
                    "pausado_em":       row.get("sla_pausado_em"),
                    "minutos_pausados": row.get("sla_minutos_pausados") or 0,
                    "estourou_em":      row.get("sla_estourou_em"),
                    "concluido_em":     row.get("sla_concluido_em"),
                }
                sla_dict = {"calculo": SLAService.calcular_status_sla(sla_raw)}
                sla_dict.update({k: str(v) if hasattr(v, "isoformat") else v for k, v in sla_raw.items()})
            row["sla"] = sla_dict
            tickets.append(row)

        tickets = convert_datetime_list(tickets)
        log_fim("sucesso", total=len(tickets), filtro_acesso=role_usuario)
        return tickets or []

    except HTTPException:
        raise
    except Exception as e:
        log_fim("erro", erro=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

# ================================================== 
# [FIM] GET - OBTER TICKETS
# Data: 06/04/2026 19:45
# ==================================================
            

@tickets_router.get("/{ticket_id}", response_model=TicketResposta)
async def obter_ticket(ticket_id: int = Path(..., gt=0)):
    log_inicio("obter_ticket", ticket_id=ticket_id)
    conexao = get_db_or_404()
    cursor = None
    try:
        cursor = conexao.cursor(dictionary=True)
        validar_ticket_existe(cursor, ticket_id)

        cursor.execute(
            """
            SELECT
                t.*,
                u.name  AS solicitante_nome,
                u.email AS solicitante_email,
                r.name  AS responsavel_nome,
                g.name  AS group_name
            FROM tickets t
            LEFT JOIN users u          ON t.solicitante_id = u.id
            LEFT JOIN users r          ON t.responsavel_id = r.id
            LEFT JOIN `cpe_grupo` g ON t.group_id = g.id
            WHERE t.id = %s
            """,
            (ticket_id,)
        )
        ticket = convert_datetime_to_string(cursor.fetchone())

        log_fim("sucesso", numero=ticket.get("numero"))
        return ticket

    except HTTPException:
        raise
    except Exception as e:
        log_fim("erro", erro=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()


# =========================================
# 🕐 SLA — importar serviço
# =========================================
try:
    from services.sla_service import SLAService
except Exception:
    class SLAService:
        @staticmethod
        def iniciar_sla(*_): return False
        @staticmethod
        def pausar_sla(*_): return False
        @staticmethod
        def acumular_pausa(*_): pass
        @staticmethod
        def concluir_sla(*_): pass
        @staticmethod
        def calcular_status_sla(_): return None

# =========================================
# 🙋 ASSUMIR / DEVOLVER TICKET
# Qualquer usuário do grupo pode se auto-atribuir (assumir).
# O usuário atribuído pode devolver para a fila (devolver).
# Ambas as ações ficam registradas no histórico.
# =========================================

class AssumiPayload(BaseModel):
    usuario_id: int = Field(..., gt=0)

@tickets_router.post("/{ticket_id}/assumir")
async def assumir_ticket(ticket_id: int, payload: AssumiPayload):
    """Qualquer usuário do mesmo grupo pode se auto-atribuir ao ticket."""
    log_inicio("assumir_ticket", ticket_id=ticket_id, usuario_id=payload.usuario_id)
    conexao = get_db_or_404()
    cursor = None
    try:
        cursor = conexao.cursor(dictionary=True)

        ticket_db = validar_ticket_existe(cursor, ticket_id)
        usuario   = validar_usuario_existe(cursor, payload.usuario_id)
        role      = usuario.get("role") or "USER"
        e_admin   = role in ROLES_ADMIN

        # Ticket já está atribuído?
        if ticket_db.get("responsavel_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este ticket já possui um responsável atribuído"
            )

        # Usuário deve pertencer ao mesmo grupo do ticket (exceto admins)
        if not e_admin and usuario.get("group_id") != ticket_db.get("group_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não pertence ao grupo deste ticket"
            )

        nome_usuario = usuario.get("name") or f"Usuário #{payload.usuario_id}"

        # Atribuir ticket ao usuário + mudar status para Em Atendimento (2)
        cursor.execute(
            "UPDATE tickets SET responsavel_id = %s, status_id = 2, updated_at = NOW() WHERE id = %s",
            (payload.usuario_id, ticket_id)
        )

        # Registrar interação
        cursor.execute(
            """
            INSERT INTO ticket_interacoes
                (ticket_id, usuario_id, tipo, mensagem, publico, created_at)
            VALUES (%s, %s, 'atribuicao', %s, 1, NOW())
            """,
            (ticket_id, payload.usuario_id,
             f"🙋 {nome_usuario} assumiu o atendimento deste chamado.")
        )

        conexao.commit()

        # ── SLA: acumular pausa anterior (se estava pausado) e iniciar contagem ──
        SLAService.acumular_pausa(conexao, ticket_id)
        if SLAService.iniciar_sla(conexao, ticket_id):
            conexao.commit()
            cursor.execute(
                """INSERT INTO ticket_interacoes
                       (ticket_id, usuario_id, tipo, mensagem, publico, created_at)
                   VALUES (%s, %s, 'sla_iniciado', '⏱️ Contagem de SLA iniciada.', 1, NOW())""",
                (ticket_id, payload.usuario_id)
            )
            conexao.commit()

        # Notificar solicitante
        criar_notificacao_no_banco(
            conexao, ticket_id, ticket_db["solicitante_id"],
            "ticket_atribuido",
            f"Seu chamado foi assumido por {nome_usuario}"
        )

        logger.info(f"  ✅ Ticket #{ticket_id} assumido por {nome_usuario}")
        return {"success": True, "message": f"Chamado assumido por {nome_usuario}"}

    except HTTPException:
        raise
    except Exception as e:
        if conexao: conexao.rollback()
        logger.error(f"  ❌ Erro ao assumir ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:  cursor.close()
        if conexao: conexao.close()


class DevolverPayload(BaseModel):
    usuario_id: int = Field(..., gt=0)
    motivo: Optional[str] = Field(None, max_length=500)

@tickets_router.post("/{ticket_id}/devolver")
async def devolver_ticket(ticket_id: int, payload: DevolverPayload):
    """O usuário atribuído devolve o ticket para a fila do grupo."""
    log_inicio("devolver_ticket", ticket_id=ticket_id, usuario_id=payload.usuario_id)
    conexao = get_db_or_404()
    cursor = None
    try:
        cursor = conexao.cursor(dictionary=True)

        ticket_db = validar_ticket_existe(cursor, ticket_id)
        usuario   = validar_usuario_existe(cursor, payload.usuario_id)
        role      = usuario.get("role") or "USER"
        e_admin   = role in ROLES_ADMIN

        # Apenas o responsável atual ou admin pode devolver
        responsavel_atual = ticket_db.get("responsavel_id")
        if not e_admin and responsavel_atual != payload.usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas o responsável atual pode devolver o chamado"
            )

        if not responsavel_atual:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este chamado não possui responsável atribuído"
            )

        nome_usuario = usuario.get("name") or f"Usuário #{payload.usuario_id}"
        motivo_txt   = f" — Motivo: {payload.motivo}" if payload.motivo else ""

        # Remover responsável + voltar status para Aberto (1)
        cursor.execute(
            "UPDATE tickets SET responsavel_id = NULL, status_id = 1, updated_at = NOW() WHERE id = %s",
            (ticket_id,)
        )

        # Registrar interação
        cursor.execute(
            """
            INSERT INTO ticket_interacoes
                (ticket_id, usuario_id, tipo, mensagem, publico, created_at)
            VALUES (%s, %s, 'devolucao', %s, 1, NOW())
            """,
            (ticket_id, payload.usuario_id,
             f"↩️ {nome_usuario} devolveu o chamado para a fila{motivo_txt}.")
        )

        conexao.commit()

        # ── SLA: pausar contagem ao devolver ──
        if SLAService.pausar_sla(conexao, ticket_id):
            conexao.commit()
            cursor.execute(
                """INSERT INTO ticket_interacoes
                       (ticket_id, usuario_id, tipo, mensagem, publico, created_at)
                   VALUES (%s, %s, 'sla_pausado', %s, 1, NOW())""",
                (ticket_id, payload.usuario_id,
                 f"⏸️ SLA pausado{motivo_txt}.")
            )
            conexao.commit()

        # Notificar RESPONSAVEL_GRUPO do grupo
        cursor.execute(
            "SELECT id FROM users WHERE group_id = %s AND role = 'RESPONSAVEL_GRUPO' AND is_active = 1",
            (ticket_db["group_id"],)
        )
        for resp in cursor.fetchall():
            criar_notificacao_no_banco(
                conexao, ticket_id, resp["id"],
                "ticket_devolvido",
                f"{nome_usuario} devolveu o chamado para a fila{motivo_txt}"
            )

        logger.info(f"  ✅ Ticket #{ticket_id} devolvido por {nome_usuario}")
        return {"success": True, "message": "Chamado devolvido para a fila"}

    except HTTPException:
        raise
    except Exception as e:
        if conexao: conexao.rollback()
        logger.error(f"  ❌ Erro ao devolver ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:  cursor.close()
        if conexao: conexao.close()


# =========================================
# 🕐 SLA — STATUS E PAUSA MANUAL
# =========================================

@tickets_router.get("/{ticket_id}/sla")
async def status_sla(ticket_id: int):
    """Retorna o status atual do SLA de um ticket."""
    conexao = get_db_or_404()
    cursor  = None
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            """SELECT ts.*, c.nome AS categoria_nome
               FROM ticket_sla ts
               LEFT JOIN categorias c ON c.id = ts.categoria_id
               WHERE ts.ticket_id = %s""",
            (ticket_id,)
        )
        sla = cursor.fetchone()
        if not sla:
            return {"sla": None}

        # Converter datetimes para string
        for campo in ("iniciado_em", "pausado_em", "estourou_em", "concluido_em", "created_at", "updated_at"):
            if sla.get(campo) and hasattr(sla[campo], "isoformat"):
                sla[campo] = sla[campo].isoformat()

        sla["calculo"] = SLAService.calcular_status_sla(sla)
        return {"sla": sla}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:  cursor.close()
        if conexao: conexao.close()


class SLAPausarPayload(BaseModel):
    usuario_id: int           = Field(..., gt=0)
    motivo:     Optional[str] = Field(None, max_length=500)

@tickets_router.post("/{ticket_id}/sla/pausar")
async def pausar_sla_manual(ticket_id: int, payload: SLAPausarPayload):
    """Responsável do grupo ou admin pausa o SLA manualmente."""
    conexao = get_db_or_404()
    cursor  = None
    try:
        cursor = conexao.cursor(dictionary=True)
        usuario = validar_usuario_existe(cursor, payload.usuario_id)
        role    = usuario.get("role") or "USER"

        if role not in ROLES_ADMIN and role != "RESPONSAVEL_GRUPO":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas Responsável do Grupo ou Admin podem pausar o SLA"
            )

        validar_ticket_existe(cursor, ticket_id)
        pausou = SLAService.pausar_sla(conexao, ticket_id)
        if not pausou:
            raise HTTPException(status_code=400, detail="SLA não está em andamento ou não existe")

        conexao.commit()
        motivo_txt = f" — Motivo: {payload.motivo}" if payload.motivo else ""
        nome = usuario.get("name") or f"Usuário #{payload.usuario_id}"
        cursor.execute(
            """INSERT INTO ticket_interacoes
                   (ticket_id, usuario_id, tipo, mensagem, publico, created_at)
               VALUES (%s, %s, 'sla_pausado', %s, 1, NOW())""",
            (ticket_id, payload.usuario_id, f"⏸️ SLA pausado manualmente por {nome}{motivo_txt}.")
        )
        conexao.commit()
        return {"success": True, "message": "SLA pausado"}

    except HTTPException:
        raise
    except Exception as e:
        if conexao: conexao.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:  cursor.close()
        if conexao: conexao.close()


@tickets_router.post("/{ticket_id}/sla/retomar")
async def retomar_sla_manual(ticket_id: int, payload: SLAPausarPayload):
    """Responsável do grupo ou admin retoma o SLA pausado manualmente."""
    conexao = get_db_or_404()
    cursor  = None
    try:
        cursor = conexao.cursor(dictionary=True)
        usuario = validar_usuario_existe(cursor, payload.usuario_id)
        role    = usuario.get("role") or "USER"

        if role not in ROLES_ADMIN and role != "RESPONSAVEL_GRUPO":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas Responsável do Grupo ou Admin podem retomar o SLA"
            )

        validar_ticket_existe(cursor, ticket_id)
        SLAService.acumular_pausa(conexao, ticket_id)
        retomou = SLAService.iniciar_sla(conexao, ticket_id)
        if not retomou:
            raise HTTPException(status_code=400, detail="SLA não está pausado ou não existe")

        conexao.commit()
        nome = usuario.get("name") or f"Usuário #{payload.usuario_id}"
        cursor.execute(
            """INSERT INTO ticket_interacoes
                   (ticket_id, usuario_id, tipo, mensagem, publico, created_at)
               VALUES (%s, %s, 'sla_retomado', %s, 1, NOW())""",
            (ticket_id, payload.usuario_id, f"▶️ SLA retomado por {nome}.")
        )
        conexao.commit()
        return {"success": True, "message": "SLA retomado"}

    except HTTPException:
        raise
    except Exception as e:
        if conexao: conexao.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:  cursor.close()
        if conexao: conexao.close()


# =========================================
# 🔀 ENCAMINHAR TICKET PARA OUTRO GRUPO
# Permitido para TODOS os usuários com acesso ao ticket.
# Apenas ADMIN/GESTOR pode atribuir responsável ao encaminhar.
# =========================================

class EncaminharPayload(BaseModel):
    usuario_id: int = Field(..., gt=0)
    group_id:   int = Field(..., gt=0)
    motivo:     Optional[str] = Field(None, max_length=500)
    responsavel_id: Optional[int] = Field(None, gt=0)  # só admin pode usar

@tickets_router.post("/{ticket_id}/encaminhar")
async def encaminhar_ticket(ticket_id: int, payload: EncaminharPayload):
    log_inicio("encaminhar_ticket", ticket_id=ticket_id, usuario_id=payload.usuario_id, novo_grupo=payload.group_id)
    conexao = get_db_or_404()
    cursor = None
    try:
        cursor = conexao.cursor(dictionary=True)

        # Validações básicas
        ticket_db  = validar_ticket_existe(cursor, ticket_id)
        usuario    = validar_usuario_existe(cursor, payload.usuario_id)
        role_atual = usuario.get("role") or "USER"
        e_admin    = role_atual in ROLES_ADMIN

        validar_grupo_existe(cursor, payload.group_id)

        if payload.group_id == ticket_db["group_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O ticket já pertence a este grupo"
            )

        # Buscar nome do grupo destino para logs/notificação
        cursor.execute("SELECT name FROM `cpe_grupo` WHERE id = %s", (payload.group_id,))
        grupo_destino = cursor.fetchone()
        nome_grupo_destino = grupo_destino["name"] if grupo_destino else f"Grupo #{payload.group_id}"

        # Buscar nome do usuário que encaminhou
        cursor.execute("SELECT name FROM users WHERE id = %s", (payload.usuario_id,))
        row_user = cursor.fetchone()
        nome_usuario = row_user["name"] if row_user else f"Usuário #{payload.usuario_id}"

        # Responsável: só admin pode definir ao encaminhar
        novo_responsavel_id = None
        if e_admin and payload.responsavel_id:
            validar_usuario_existe(cursor, payload.responsavel_id)
            novo_responsavel_id = payload.responsavel_id

        # Atualizar ticket: novo grupo, limpar responsável (a menos que admin atribua)
        cursor.execute(
            "UPDATE tickets SET group_id = %s, responsavel_id = %s, updated_at = NOW() WHERE id = %s",
            (payload.group_id, novo_responsavel_id, ticket_id)
        )

        # Registrar interação de encaminhamento
        motivo_txt = f" — Motivo: {payload.motivo}" if payload.motivo else ""
        mensagem_interacao = (
            f"🔀 Ticket encaminhado para o grupo '{nome_grupo_destino}' "
            f"por {nome_usuario}{motivo_txt}"
        )
        cursor.execute(
            """
            INSERT INTO ticket_interacoes
                (ticket_id, usuario_id, tipo, mensagem, publico, created_at)
            VALUES (%s, %s, 'encaminhamento', %s, 1, NOW())
            """,
            (ticket_id, payload.usuario_id, mensagem_interacao)
        )

        conexao.commit()

        # Notificar RESPONSAVEL_GRUPO do novo grupo
        cursor.execute(
            "SELECT id FROM users WHERE group_id = %s AND role = 'RESPONSAVEL_GRUPO' AND is_active = 1",
            (payload.group_id,)
        )
        responsaveis_novo_grupo = cursor.fetchall()
        for resp in responsaveis_novo_grupo:
            criar_notificacao_no_banco(
                conexao, ticket_id, resp["id"],
                "ticket_encaminhado",
                f"Ticket encaminhado para '{nome_grupo_destino}' por {nome_usuario}: {ticket_db.get('assunto', '')}"
            )

        logger.info(f"  ✅ Ticket #{ticket_id} encaminhado para '{nome_grupo_destino}' por {nome_usuario}")
        return {
            "success": True,
            "message": f"Ticket encaminhado para '{nome_grupo_destino}' com sucesso"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"  ❌ Erro ao encaminhar ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:  cursor.close()
        if conexao: conexao.close()

# ================================================== 
# [FIM] GET - OBTER TICKET ÚNICO
# Data: 06/04/2026 19:45
# ==================================================

@tickets_router.post("/", status_code=status.HTTP_201_CREATED, response_model=TicketResposta)
async def criar_ticket(payload: TicketCriar):
    log_inicio(
        "criar_ticket",
        solicitante_id=payload.solicitante_id,
        group_id=payload.group_id
    )
    conexao = get_db_or_404()
    cursor = None
    try:
        cursor = conexao.cursor(dictionary=True)

        solicitante = validar_usuario_existe(cursor, payload.solicitante_id)
        validar_grupo_existe(cursor, payload.group_id)

        # ✅ Se o solicitante for USER, responsavel_id é ignorado.
        role_solicitante = solicitante.get("role") or "USER"
        responsavel_id_final = None

        if role_solicitante in ROLES_ADMIN:
            if payload.responsavel_id:
                validar_usuario_existe(cursor, payload.responsavel_id)
                responsavel_id_final = payload.responsavel_id
            logger.info(f"  ✓ Solicitante é {role_solicitante} — responsavel_id aceito: {responsavel_id_final}")
        else:
            logger.info(f"  ✓ Solicitante é USER — responsavel_id ignorado (atribuição é feita pelo admin)")

        numero = gerar_numero_ticket(cursor, payload.group_id)
        status_id_inicial = 1  # Aberto

        # ========================================
        # 💬 INSERIR TICKET NO BANCO
        # Data: 31/03/2026 16:00
        # ========================================
        
        logger.info(f"  ▶️ Inserindo ticket no banco...")
        cursor.execute(
            """
            INSERT INTO tickets (
                numero, solicitante_id, responsavel_id, group_id,
                categoria_id, subcategoria_id, status_id, prioridade_id,
                assunto, descricao_inicial, origem, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """,
            (
                numero,
                payload.solicitante_id,
                responsavel_id_final,
                payload.group_id,
                payload.categoria_id,
                payload.subcategoria_id,
                status_id_inicial,
                payload.prioridade_id,
                payload.assunto,
                payload.descricao_inicial,
                payload.origem
            )
        )
        conexao.commit()
        ticket_id = cursor.lastrowid
        logger.info(f"  ✓ Ticket inserido no banco com ID: {ticket_id}")

        # ── SLA: criar registro se categoria tem SLA definido ──
        if payload.categoria_id:
            cursor.execute(
                "SELECT sla_minutos FROM categorias WHERE id = %s AND ativo = 1",
                (payload.categoria_id,)
            )
            cat = cursor.fetchone()
            if cat and cat.get("sla_minutos"):
                SLAService.criar_sla(conexao, ticket_id, payload.categoria_id, cat["sla_minutos"])
                conexao.commit()
                logger.info(f"  ✓ SLA criado: {cat['sla_minutos']} min para ticket #{ticket_id}")

        # ========================================
        # 🆔 GERAR ID ALFANUMÉRICA
        # Data: 31/03/2026 16:00
        # ========================================

        logger.info(f"  ▶️ Gerando ID alfanumérica...")
        id_alfanumerica = gerar_id_alfanumerica(ticket_id, payload.group_id, cursor)
        logger.info(f"  ✅ ID alfanumérica gerada: {id_alfanumerica}")

        # ========================================
        # 💾 SALVAR ID ALFANUMÉRICA NO BANCO
        # Data: 31/03/2026 16:00
        # ========================================

        logger.info(f"  ▶️ Salvando ID alfanumérica no banco...")
        cursor.execute(
            "UPDATE tickets SET id_alfanumerica = %s WHERE id = %s",
            (id_alfanumerica, ticket_id)
        )
        conexao.commit()
        logger.info(f"  ✅ ID alfanumérica salva: {id_alfanumerica}")

        # ========================================
        # 🔔 NOTIFICAR NOVO TICKET
        # Data: 31/03/2026 16:00
        # ========================================
        
        logger.info(f"  ▶️ Enviando notificações de novo ticket...")
        # Buscar nome real do solicitante para a notificação
        cursor.execute("SELECT name FROM users WHERE id = %s", (payload.solicitante_id,))
        row_solicitante = cursor.fetchone()
        nome_solicitante = row_solicitante["name"] if row_solicitante else "Usuário"

        try:
            NotificacaoService(DB_CONFIG).notificar_novo_ticket(
                ticket_id=ticket_id,
                setor_id=payload.group_id,
                titulo_ticket=payload.assunto,
                usuario_autor_nome=nome_solicitante
            )
            logger.info(f"    ✓ Notificação enviada via serviço")
        except Exception as e:
            logger.warning(f"    ⚠️ Serviço indisponível: {str(e)}")
            # Fallback: notificar responsáveis do grupo diretamente no banco
            cursor.execute(
                "SELECT id FROM users WHERE group_id = %s AND role = 'RESPONSAVEL_GRUPO' AND is_active = 1",
                (payload.group_id,)
            )
            responsaveis = cursor.fetchall()
            for resp in responsaveis:
                criar_notificacao_no_banco(
                    conexao, ticket_id, resp["id"],
                    "ticket_criado",
                    f"Novo chamado de {nome_solicitante}: {payload.assunto}"
                )

        cursor.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,))
        ticket = convert_datetime_to_string(cursor.fetchone())

        log_fim("sucesso", ticket_id=ticket_id, numero=numero, id_alfanumerica=id_alfanumerica)
        return ticket

    except HTTPException:
        raise
    except Exception as e:
        log_fim("erro", erro=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()
            
@tickets_router.put("/{ticket_id}", response_model=TicketResposta)
async def atualizar_ticket(
    ticket_id: int = Path(..., gt=0),
    # ✅ usuario_id obrigatório para validar permissão de quem está alterando
    usuario_id: int = Query(..., gt=0, description="ID do usuário que está realizando a alteração"),
    payload: TicketAtualizar = None
):
    log_inicio("atualizar_ticket", ticket_id=ticket_id, usuario_id=usuario_id)
    conexao = get_db_or_404()
    cursor = None
    try:
        cursor = conexao.cursor(dictionary=True)

        ticket_db = validar_ticket_existe(cursor, ticket_id)

        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payload vazio"
            )

        # ✅ Buscar o role de quem está fazendo a alteração
        role_atual = obter_role_usuario(cursor, usuario_id)
        e_admin = role_atual in ROLES_ADMIN

        logger.info(f"  ├─ Usuário #{usuario_id} | Role: {role_atual} | Admin: {e_admin}")

        # ✅ Usuário USER só pode alterar tickets onde ele é o solicitante
        if not e_admin:
            if ticket_db["solicitante_id"] != usuario_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Você não tem permissão para alterar este ticket"
                )

            # Campos que USER não pode alterar
            campos_bloqueados = {}
            if payload.status_id is not None:
                campos_bloqueados["status_id"] = payload.status_id
            if payload.responsavel_id is not None:
                campos_bloqueados["responsavel_id"] = payload.responsavel_id
            if payload.group_id is not None:
                campos_bloqueados["group_id"] = payload.group_id

            if campos_bloqueados:
                logger.warning(
                    f"  ⚠️ Usuário USER tentou alterar campos restritos: {list(campos_bloqueados.keys())}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Usuários comuns não podem alterar status, responsável ou setor do ticket"
                )

        # Montar os campos a atualizar
        updates, params = [], []

        if payload.status_id is not None:
            updates.append("status_id = %s")
            params.append(payload.status_id)

        if payload.prioridade_id is not None:
            updates.append("prioridade_id = %s")
            params.append(payload.prioridade_id)

        if payload.responsavel_id is not None:
            validar_usuario_existe(cursor, payload.responsavel_id)
            updates.append("responsavel_id = %s")
            params.append(payload.responsavel_id)

        if payload.group_id is not None:
            validar_grupo_existe(cursor, payload.group_id)
            updates.append("group_id = %s")
            params.append(payload.group_id)

        if payload.assunto is not None:
            updates.append("assunto = %s")
            params.append(payload.assunto)

        if payload.descricao_inicial is not None:
            updates.append("descricao_inicial = %s")
            params.append(payload.descricao_inicial)

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum campo para atualizar"
            )

        updates.append("updated_at = NOW()")
        params.append(ticket_id)

        cursor.execute(
            f"UPDATE tickets SET {', '.join(updates)} WHERE id = %s",
            params
        )
        conexao.commit()

        # 🔔 NOTIFICAR ALTERAÇÕES
        logger.info(f"  ▶️ Enviando notificações de alteração...")
        try:
            ns = NotificacaoService(DB_CONFIG)
            if payload.status_id is not None:
                ns.notificar_status_alterado(
                    ticket_id=ticket_id,
                    usuario_autor_id=ticket_db["solicitante_id"],
                    novo_status=str(payload.status_id)
                )
                logger.info(f"    ✓ Status notificado")
            if payload.responsavel_id is not None:
                ns.notificar_atribuicao(
                    ticket_id=ticket_id,
                    setor_id=ticket_db["group_id"],
                    usuario_responsavel_nome=str(payload.responsavel_id)
                )
                logger.info(f"    ✓ Atribuição notificada")
        except Exception as e:
            logger.warning(f"    ⚠️ Serviço indisponível: {str(e)}")

            # ✅ Fallback de notificação corrigido:
            # status alterado → notifica o solicitante
            if payload.status_id is not None:
                criar_notificacao_no_banco(
                    conexao, ticket_id, ticket_db["solicitante_id"],
                    "status_alterado",
                    f"O status do seu chamado foi atualizado"
                )

            # atribuição → notifica o NOVO responsável (não o solicitante)
            if payload.responsavel_id is not None:
                criar_notificacao_no_banco(
                    conexao, ticket_id, payload.responsavel_id,
                    "atribuido",
                    f"Um chamado foi atribuído a você"
                )

        cursor.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,))
        atualizado = convert_datetime_to_string(cursor.fetchone())

        log_fim("sucesso", ticket_id=ticket_id)
        return atualizado

    except HTTPException:
        raise
    except Exception as e:
        log_fim("erro", erro=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()


@tickets_router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_ticket(
    ticket_id: int = Path(..., gt=0),
    # ✅ usuario_id para validar que só o solicitante (ou admin) pode deletar
    usuario_id: int = Query(..., gt=0, description="ID do usuário que está deletando")
):
    log_inicio("deletar_ticket", ticket_id=ticket_id, usuario_id=usuario_id)
    conexao = get_db_or_404()
    cursor = None
    try:
        cursor = conexao.cursor(dictionary=True)
        ticket_db = validar_ticket_existe(cursor, ticket_id)

        role_atual = obter_role_usuario(cursor, usuario_id)
        e_admin = role_atual in ROLES_ADMIN

        # Usuário USER só pode deletar o próprio ticket
        if not e_admin and ticket_db["solicitante_id"] != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para deletar este ticket"
            )

        cursor.execute("DELETE FROM tickets WHERE id = %s", (ticket_id,))
        conexao.commit()

        log_fim("sucesso", ticket_id=ticket_id)

    except HTTPException:
        raise
    except Exception as e:
        log_fim("erro", erro=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()
# ========================================
# GET - OBTER INTERAÇÕES DE UM TICKET
# Data: 31/03/2026 19:00
# ========================================

@interacoes_router.get("/{ticket_id}", response_model=List[InteracaoResposta])
async def obter_interacoes(ticket_id: int = Path(..., gt=0)):
    """
    Obtém todas as INTERAÇÕES (comentários) de um TICKET
    ✅ Retorna lista de interações
    ✅ Ordena por data de criação
    """
    log_inicio("obter_interacoes", ticket_id=ticket_id)
    conexao = get_db_or_404()
    cursor = None
    try:
        cursor = conexao.cursor(dictionary=True)

        logger.info(f"  ▶️ Buscando interações do ticket {ticket_id}...")
        
        # Validar se ticket existe
        cursor.execute("SELECT id FROM tickets WHERE id = %s", (ticket_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket {ticket_id} não encontrado"
            )

        # Buscar interações
        cursor.execute(
            """
            SELECT ti.id, ti.ticket_id, ti.usuario_id, ti.tipo, ti.publico,
                   ti.mensagem, ti.created_at, u.name AS usuario_nome
            FROM ticket_interacoes ti
            LEFT JOIN users u ON ti.usuario_id = u.id
            WHERE ti.ticket_id = %s
            ORDER BY ti.created_at ASC
            """,
            (ticket_id,)
        )
        
        registros = cursor.fetchall()
        logger.info(f"  ✓ {len(registros)} interação(ões) encontrada(s)")

        interacoes = [
            {
                "id": r["id"],
                "ticket_id": r["ticket_id"],
                "usuario_id": r["usuario_id"],
                "usuario_nome": r.get("usuario_nome"),
                "tipo": r["tipo"],
                "publico": r["publico"],
                "mensagem": r["mensagem"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None
            }
            for r in registros
        ]

        log_fim("sucesso", ticket_id=ticket_id, total_interacoes=len(interacoes))
        return interacoes

    except HTTPException:
        raise
    except Exception as e:
        log_fim("erro", erro=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

# ========================================
# 💬 ENDPOINT DE INTERAÇÕES - ALTERADO
# Data: 31/03/2026 14:42
# ========================================
# INÍCIO: Substituir de @interacoes_router.post("/", ...)
# até o final do except/finally

@interacoes_router.post("/", status_code=status.HTTP_201_CREATED, response_model=InteracaoResposta)
async def criar_interacao(payload: InteracaoCriar):
    """
    Cria uma INTERAÇÃO (comentário/resposta) em um TICKET EXISTENTE
    ✅ Valida permissões por role
    ✅ Mantém notificações funcionando
    ✅ Respeita comentários internos
    """
    log_inicio(
        "criar_interacao",
        ticket_id=payload.ticket_id,
        usuario_id=payload.usuario_id,
        tipo=payload.tipo,
        publico=payload.publico
    )
    conexao = get_db_or_404()
    cursor = None
    try:
        cursor = conexao.cursor(dictionary=True)

        # ✅ VALIDAÇÕES ESSENCIAIS
        ticket_db = validar_ticket_existe(cursor, payload.ticket_id)
        usuario = validar_usuario_existe(cursor, payload.usuario_id)
        role_usuario = usuario.get("role") or "USER"

        # ✅ Usuário USER não pode criar comentário interno
        e_interno = (payload.tipo in ["interno", "nota_interna"] or payload.publico == 0)
        if e_interno and role_usuario not in ROLES_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuários comuns não podem criar comentários internos"
            )

        # Normalizar tipo: "interno" → "nota_interna" para consistência no banco
        tipo_final = "nota_interna" if payload.tipo == "interno" else payload.tipo
        publico_final = 0 if tipo_final == "nota_interna" else payload.publico

        # ========================================
        # 💬 INSERIR INTERAÇÃO (CORRETO!)
        # Data: 31/03/2026 15:30
        # ========================================
        
        logger.info(f"  ▶️ Inserindo interação no banco...")
        cursor.execute(
            """
            INSERT INTO ticket_interacoes (
                ticket_id, usuario_id, tipo, publico, mensagem, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            """,
            (
                payload.ticket_id,
                payload.usuario_id,
                tipo_final,
                publico_final,
                payload.mensagem
            )
        )
        conexao.commit()
        interacao_id = cursor.lastrowid
        logger.info(f"  ✓ Interação #{interacao_id} inserida com sucesso")

        # ========================================
        # 🔔 NOTIFICAÇÕES (MANTÉM FUNCIONANDO)
        # Data: 31/03/2026 15:30
        # ========================================
        
        logger.info(f"  ▶️ Enviando notificações...")
        logger.info(f"    📋 Detalhes do ticket:")
        logger.info(f"       - ticket_id: {payload.ticket_id}")
        logger.info(f"       - solicitante_id: {ticket_db.get('solicitante_id')}")
        logger.info(f"       - responsavel_id: {ticket_db.get('responsavel_id')}")
        logger.info(f"       - usuario_id (quem respondeu): {payload.usuario_id}")
        
        usuarios_para_notificar = set()

        # 🔔 LÓGICA: Respostas públicas vs Comentários internos
        if publico_final == 1:  # ✅ RESPOSTA PÚBLICA
            logger.info(f"    📢 Tipo: RESPOSTA PÚBLICA - Notificando solicitante e responsável")
            
            # 1️⃣ Adicionar solicitante
            if ticket_db["solicitante_id"]:
                usuarios_para_notificar.add(ticket_db["solicitante_id"])
                logger.info(f"    ├─ ✅ Adicionado Solicitante: #{ticket_db['solicitante_id']}")
            
            # 2️⃣ Adicionar responsável (se houver)
            if ticket_db["responsavel_id"]:
                usuarios_para_notificar.add(ticket_db["responsavel_id"])
                logger.info(f"    ├─ ✅ Adicionado Responsável: #{ticket_db['responsavel_id']}")

        else:  # 🔐 COMENTÁRIO INTERNO
            logger.info(f"    🔐 Tipo: COMENTÁRIO INTERNO (SECRETO)")
            logger.warning(f"    ⚠️ NÃO notificando o solicitante (comentário é confidencial)")
            
            # 3️⃣ Para comentários internos, adicionar APENAS os admins do sistema
            cursor.execute("""
                SELECT DISTINCT u.id 
                FROM users u
                WHERE u.role IN ('ADMIN', 'TI', 'MANAGER')
                AND u.id != %s 
                AND u.is_active = 1
            """, (payload.usuario_id,))
            
            grupo_users = cursor.fetchall()
            for user in grupo_users:
                usuarios_para_notificar.add(user["id"])
            
            logger.info(f"    ├─ ✅ Adicionados Admins: {len(grupo_users)} usuários")

        # 4️⃣ Nunca notificar o próprio usuário que criou a interação
        usuarios_antes = len(usuarios_para_notificar)
        usuarios_para_notificar.discard(payload.usuario_id)
        usuarios_depois = len(usuarios_para_notificar)

        if usuarios_antes != usuarios_depois:
            logger.info(f"    ├─ 🚫 Removido quem respondeu: #{payload.usuario_id}")

        logger.info(f"    └─ 📊 Total a notificar: {len(usuarios_para_notificar)} usuário(s)")
        logger.info(f"       Lista final: {usuarios_para_notificar}")

        # ========================================
        # 🔔 ENVIAR NOTIFICAÇÕES COM FALLBACK
        # Data: 31/03/2026 15:30
        # ========================================

        logger.info(f"    ╔════════════════════════════════════════════════════════════╗")
        logger.info(f"    ║ 🔔 BLOCO DE CRIAÇÃO DE NOTIFICAÇÕES - INICIO                ║")
        logger.info(f"    ╚════════════════════════════════════════════════════════════╝")
        logger.info(f"    → usuarios_para_notificar: {usuarios_para_notificar}")
        logger.info(f"    → len(usuarios_para_notificar): {len(usuarios_para_notificar)}")
        
        if usuarios_para_notificar:
            logger.info(f"    ✓ Entrando no bloco IF (tem usuários para notificar)")
            
            try:
                logger.info(f"    ▶️ Tentando inicializar NotificacaoService...")
                ns = NotificacaoService(DB_CONFIG)
                logger.info(f"    ✓ NotificacaoService inicializado")
                
                if publico_final == 1:  # Resposta pública
                    tipo_notif = "nova_resposta"
                    mensagem_base = f"Nova resposta no ticket #{ticket_db.get('numero', payload.ticket_id)}: {payload.mensagem[:80]}"
                    logger.info(f"    → Tipo PÚBLICO (publico_final=1)")
                else:  # Comentário interno
                    tipo_notif = "comentario_interno"
                    mensagem_base = f"Comentário interno no ticket #{ticket_db.get('numero', payload.ticket_id)}: {payload.mensagem[:80]}"
                    logger.info(f"    → Tipo INTERNO (publico_final=0)")
                
                logger.info(f"    → tipo_notif: {tipo_notif}")
                logger.info(f"    → mensagem_base: {mensagem_base[:60]}...")
                logger.info(f"    🔄 INICIANDO LOOP sobre {len(usuarios_para_notificar)} usuário(s)...")
                
                # Notificar via serviço (se disponível)
                for idx, user_id in enumerate(usuarios_para_notificar, 1):
                    logger.info(f"    ├─ [Iteração {idx}] Processando user_id: {user_id}")
                    try:
                        logger.info(f"    │  ▶️ Chamando ns.notificar_nova_resposta()...")
                        ns.notificar_nova_resposta(
                            ticket_id=payload.ticket_id,
                            usuario_id=user_id,
                            usuario_autor_id=payload.usuario_id,
                            usuario_respondente_nome="Sistema"
                        )
                        logger.info(f"    │  ✓ Serviço notificou #{user_id} com SUCESSO")
                        
                    except Exception as e:
                        logger.warning(f"    │  ⚠️ Serviço falhou para #{user_id}: {str(e)}")
                        logger.info(f"    │  ▶️ Usando fallback: criar_notificacao_no_banco()")
                        # Fallback: criar direto no banco
                        criar_notificacao_no_banco(
                            conexao, 
                            payload.ticket_id, 
                            user_id, 
                            tipo_notif, 
                            mensagem_base
                        )
                        logger.info(f"    │  ✓ Fallback executado para #{user_id}")
                
                logger.info(f"    └─ ✓ Loop finalizado!")
                logger.info(f"    ✓ Notificações enviadas via serviço")
                
            except Exception as e:
                logger.warning(f"    ❌ ERRO na inicialização do serviço: {str(e)}")
                logger.warning(f"    ⚠️ Serviço indisponível, usando fallback completo...")
                logger.info(f"    🔄 INICIANDO FALLBACK (banco de dados)...")
                
                # Fallback: criar notificações direto no banco para todos
                for idx, user_id in enumerate(usuarios_para_notificar, 1):
                    logger.info(f"    ├─ [Fallback {idx}] user_id: {user_id}")
                    tipo_notif = "nova_resposta" if publico_final == 1 else "comentario_interno"
                    mensagem = f"Nova {'resposta' if publico_final == 1 else 'nota interna'} no ticket #{ticket_db.get('numero', payload.ticket_id)}"
                    logger.info(f"    │  ▶️ Criando notificação (tipo: {tipo_notif})")
                    criar_notificacao_multipla(
                        conexao, 
                        payload.ticket_id, 
                        user_id, 
                        tipo_notif, 
                        mensagem
                    )
                    logger.info(f"    │  ✓ Notificação criada para #{user_id}")
                
                logger.info(f"    └─ ✓ Fallback finalizado!")
                logger.info(f"    ✓ Notificações enviadas via fallback (banco)")
        else:
            logger.warning(f"    ❌ NENHUM USUÁRIO PARA NOTIFICAR!")
            logger.warning(f"    → usuarios_para_notificar está vazio ou None")

        logger.info(f"    ╔════════════════════════════════════════════════════════════╗")
        logger.info(f"    ║ 🔔 BLOCO DE CRIAÇÃO DE NOTIFICAÇÕES - FIM                  ║")
        logger.info(f"    ╚════════════════════════════════════════════════════════════╝")

        # ========================================
        # ✅ RETORNAR INTERAÇÃO
        # Data: 31/03/2026 15:30
        # ========================================

        cursor.execute(
            """
            SELECT ti.id, ti.ticket_id, ti.usuario_id, ti.tipo, ti.publico,
                   ti.mensagem, ti.created_at, u.name AS usuario_nome
            FROM ticket_interacoes ti
            LEFT JOIN users u ON ti.usuario_id = u.id
            WHERE ti.id = %s
            """,
            (interacao_id,)
        )
        registro = cursor.fetchone()

        resposta = {
            "id":           registro["id"],
            "ticket_id":    registro["ticket_id"],
            "usuario_id":   registro["usuario_id"],
            "usuario_nome": registro.get("usuario_nome"),
            "tipo":         registro["tipo"],
            "publico":      registro["publico"],
            "mensagem":     registro["mensagem"],
            "created_at":   registro["created_at"].isoformat() if registro["created_at"] else None
        }

        log_fim("sucesso", interacao_id=interacao_id, notificacoes_enviadas=len(usuarios_para_notificar))
        return resposta

    except HTTPException:
        raise
    except Exception as e:
        log_fim("erro", erro=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

# ========================================
# FIM DA FUNÇÃO - 31/03/2026 15:30
# ========================================