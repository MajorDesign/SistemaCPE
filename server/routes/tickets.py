"""
API de Tickets/Chamados - v3.3
Endpoints para criar, listar, atualizar e deletar tickets
Inclui endpoints para interações (comentários/respostas)

Alterações v3.3:
- PUT /tickets/{id} agora exige usuario_id e valida permissão por role
- POST /tickets ignora responsavel_id se solicitante for USER
- POST /ticket-interacoes bloqueia comentário interno para usuário USER
- Notificação de atribuição agora notifica o novo responsável corretamente
- validar_grupo_existe confirmado para password_groups (FK correta do banco)
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
        "SELECT id, role FROM users WHERE id = %s AND is_active = 1",
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
    # ✅ CONFIRMADO: tickets.group_id referencia password_groups (FK do banco)
    cursor.execute("SELECT id FROM password_groups WHERE id = %s", (group_id,))
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
    cursor.execute("SELECT name FROM password_groups WHERE id = %s", (group_id,))
    g = cursor.fetchone()
    prefixo = (g["name"][:3].upper() if g and g.get("name") else "TKT")
    cursor.execute(
        "SELECT COUNT(*) as count FROM tickets WHERE group_id = %s AND YEAR(created_at) = YEAR(NOW())",
        (group_id,)
    )
    c = cursor.fetchone()
    seq = (c["count"] + 1) if c else 1
    return f"{prefixo}-{datetime.now().year}-{seq:05d}"

# ========================================
# 🔔 FUNÇÃO AUXILIAR - NOVA
# Data: 31/03/2026 14:42
# CRIAR NOTIFICAÇÃO MÚLTIPLA (FALLBACK)
# ========================================
# INÍCIO: Adicionar após função criar_notificacao_no_banco()

def criar_notificacao_multipla(conexao, ticket_id: int, usuario_id: int, tipo: str, mensagem: str):
    """Cria notificação direto no banco para múltiplos usuários (fallback)"""
    cursor = None
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            """
            INSERT INTO notificacoes (ticket_id, usuario_id, tipo, mensagem, lido, created_at, updated_at)
            VALUES (%s, %s, %s, %s, 0, NOW(), NOW())
            """,
            (ticket_id, usuario_id, tipo, mensagem)
        )
        conexao.commit()
        logger.info(f"      ✓ Notificação criada para #{usuario_id} (fallback) | tipo: {tipo}")
    except Exception as e:
        logger.warning(f"      ⚠️ Erro ao criar notificação fallback para #{usuario_id}: {str(e)}")
    finally:
        if cursor:
            cursor.close()

# ========================================
# FIM DA FUNÇÃO AUXILIAR - 31/03/2026 14:42
# ========================================

# =========================================
# 📌 ENDPOINTS DE TICKETS
# =========================================

@tickets_router.get("/", response_model=List[dict])
async def obter_tickets(
    grupo_id: Optional[int] = Query(None, gt=0),
    status_id: Optional[int] = Query(None, gt=0),
    responsavel_id: Optional[int] = Query(None, gt=0),
    prioridade_id: Optional[int] = Query(None, gt=0),
    pular: int = Query(0, ge=0),
    limite: int = Query(LIMITE_PADRAO, ge=1, le=LIMITE_MAXIMO)
):
    log_inicio("obter_tickets", grupo_id=grupo_id, status_id=status_id)
    conexao = get_db_or_404()
    cursor = None
    try:
        cursor = conexao.cursor(dictionary=True)
        filtros, params = [], []

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

        sql = f"""
            SELECT
                t.*,
                u.name  AS solicitante_nome,
                u.email AS solicitante_email,
                r.name  AS responsavel_nome,
                g.name  AS group_name
            FROM tickets t
            LEFT JOIN users u          ON t.solicitante_id = u.id
            LEFT JOIN users r          ON t.responsavel_id = r.id
            LEFT JOIN password_groups g ON t.group_id = g.id
            {where}
            ORDER BY t.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limite, pular])
        cursor.execute(sql, params)
        tickets = convert_datetime_list(cursor.fetchall())

        log_fim("sucesso", total=len(tickets))
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
            LEFT JOIN password_groups g ON t.group_id = g.id
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
        # Somente ADMIN/TI/MANAGER podem abrir ticket já com responsável definido.
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

        # 🔔 NOTIFICAR NOVO TICKET
        logger.info(f"  ▶️ Enviando notificações de novo ticket...")
        try:
            NotificacaoService(DB_CONFIG).notificar_novo_ticket(
                ticket_id=ticket_id,
                setor_id=payload.group_id,
                titulo_ticket=payload.assunto,
                usuario_autor_nome="Sistema"
            )
            logger.info(f"    ✓ Notificação enviada via serviço")
        except Exception as e:
            logger.warning(f"    ⚠️ Serviço indisponível: {str(e)}")
            # Notifica o próprio solicitante que o ticket foi criado
            criar_notificacao_no_banco(
                conexao, ticket_id, payload.solicitante_id,
                "ticket_criado",
                f"Seu chamado foi aberto com sucesso: {payload.assunto}"
            )

        cursor.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,))
        ticket = convert_datetime_to_string(cursor.fetchone())

        log_fim("sucesso", ticket_id=ticket_id, numero=numero)
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
# 💬 ENDPOINT DE INTERAÇÕES - ALTERADO
# Data: 31/03/2026 14:42
# ========================================
# INÍCIO: Substituir de @interacoes_router.post("/", ...)
# até o final do except/finally

@interacoes_router.post("/", status_code=status.HTTP_201_CREATED, response_model=InteracaoResposta)
async def criar_interacao(payload: InteracaoCriar):
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

        cursor.execute(
            """
            INSERT INTO ticket_interacoes (ticket_id, usuario_id, tipo, publico, mensagem, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
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
        # ========================================
        # 🔔 NOTIFICAR TODOS OS ENVOLVIDOS - DEBUGADO
        # Data: 31/03/2026 15:25
        # ========================================
        logger.info(f"  ▶️ Enviando notificações para todos os envolvidos...")
        logger.info(f"    📋 Detalhes do ticket:")
        logger.info(f"       - ticket_id: {payload.ticket_id}")
        logger.info(f"       - solicitante_id: {ticket_db.get('solicitante_id')}")
        logger.info(f"       - responsavel_id: {ticket_db.get('responsavel_id')}")
        logger.info(f"       - usuario_id (quem respondeu): {payload.usuario_id}")
        logger.info(f"       - publico_final: {publico_final}")
        
        # Obter lista de usuários que devem receber notificação
        usuarios_para_notificar = set()
                # Obter lista de usuários que devem receber notificação
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
                
        else:  # ❌ COMENTÁRIO INTERNO (SECRETO)
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
            
            logger.info(f"    ├─ ✅ Adicionados Admins do Sistema: {len(grupo_users)} usuários")
        
        # 4️⃣ Nunca notificar o próprio usuário que está respondendo
        usuarios_antes = len(usuarios_para_notificar)
        usuarios_para_notificar.discard(payload.usuario_id)
        usuarios_depois = len(usuarios_para_notificar)
        
        if usuarios_antes != usuarios_depois:
            logger.info(f"    ├─ 🚫 Removido quem respondeu: #{payload.usuario_id} (era {usuarios_antes}, agora {usuarios_depois})")
        
        logger.info(f"    └─ 📊 Total a notificar: {len(usuarios_para_notificar)} usuário(s)")
        logger.info(f"       Lista final: {usuarios_para_notificar}")
        
        if usuarios_antes != usuarios_depois:
            logger.info(f"    ├─ 🚫 Removido quem respondeu: #{payload.usuario_id} (era {usuarios_antes}, agora {usuarios_depois})")
        
        logger.info(f"    └─ 📊 Total a notificar: {len(usuarios_para_notificar)} usuário(s)")
        logger.info(f"       Lista final: {usuarios_para_notificar}")
        
                # 🔔 CRIAR NOTIFICAÇÃO PARA CADA USUÁRIO
        logger.info(f"    ╔════════════════════════════════════════════════════════════╗")
        logger.info(f"    ║ 🔔 BLOCO DE CRIAÇÃO DE NOTIFICAÇÕES - INICIO                ║")
        logger.info(f"    ╚════════════════════════════════════════════════════════════╝")
        logger.info(f"    → usuarios_para_notificar: {usuarios_para_notificar}")
        logger.info(f"    → bool(usuarios_para_notificar): {bool(usuarios_para_notificar)}")
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
                        logger.info(f"    │  ▶️ Usando fallback: criar_notificacao_multipla()")
                        # Fallback: criar direto no banco
                        criar_notificacao_multipla(
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
        # FIM NOTIFICAÇÕES - 31/03/2026 15:25
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
# FIM DA FUNÇÃO - 31/03/2026 14:42
# ========================================


@interacoes_router.get("/{ticket_id}", response_model=List[InteracaoResposta])
async def obter_interacoes_ticket(
    ticket_id: int = Path(..., gt=0),
    # ✅ usuario_id para filtrar: USER só vê respostas públicas (publico=1)
    usuario_id: Optional[int] = Query(None, gt=0, description="ID do usuário solicitante (filtra comentários internos)")
):
    log_inicio("obter_interacoes_ticket", ticket_id=ticket_id, usuario_id=usuario_id)
    conexao = get_db_or_404()
    cursor = None
    try:
        cursor = conexao.cursor(dictionary=True)
        validar_ticket_existe(cursor, ticket_id)

        # Verificar se é admin para decidir se mostra comentários internos
        mostrar_internos = True
        if usuario_id:
            role_usuario = obter_role_usuario(cursor, usuario_id)
            if role_usuario not in ROLES_ADMIN:
                mostrar_internos = False
                logger.info(f"  ✓ Usuário USER #{usuario_id} — ocultando comentários internos")

        filtro_publico = "" if mostrar_internos else "AND ti.publico = 1"

        cursor.execute(
            f"""
            SELECT ti.id, ti.ticket_id, ti.usuario_id, ti.tipo, ti.publico,
                   ti.mensagem, ti.created_at, u.name AS usuario_nome
            FROM ticket_interacoes ti
            LEFT JOIN users u ON ti.usuario_id = u.id
            WHERE ti.ticket_id = %s {filtro_publico}
            ORDER BY ti.created_at ASC
            """,
            (ticket_id,)
        )
        rows = cursor.fetchall()

        interacoes = [
            {
                "id":           r["id"],
                "ticket_id":    r["ticket_id"],
                "usuario_id":   r["usuario_id"],
                "usuario_nome": r.get("usuario_nome"),
                "tipo":         r["tipo"],
                "publico":      r["publico"],
                "mensagem":     r["mensagem"],
                "created_at":   r["created_at"].isoformat() if r["created_at"] else None
            }
            for r in rows
        ]

        log_fim("sucesso", total=len(interacoes))
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