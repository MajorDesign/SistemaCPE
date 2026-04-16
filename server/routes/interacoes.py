"""
API de Interações (Comentários/Mensagens em Tickets)
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

# =========================================
# MODELOS PYDANTIC
# =========================================

class InteracaoCreate(BaseModel):
    """Modelo para criar nova interação"""
    ticket_id: int
    usuario_id: int
    tipo: str = "mensagem"  # mensagem, nota_interna, alteracao_status, atribuicao, sistema
    publico: bool = True
    mensagem: str = Field(..., min_length=1)

class InteracaoResponse(BaseModel):
    """Resposta padrão de interação"""
    id: int
    ticket_id: int
    usuario_id: int
    tipo: str
    publico: bool
    mensagem: str
    created_at: Optional[str]

# =========================================
# ROUTER
# =========================================

interacoes_router = APIRouter(prefix="/api/interacoes", tags=["interacoes"])

# [GET] Listar interações de um ticket
@interacoes_router.get(
    "/ticket/{ticket_id}",
    response_model=List[dict],
    summary="Listar interações de um ticket",
    description="Obtém todos os comentários de um ticket"
)
async def get_interacoes_ticket(ticket_id: int, mostrar_internas: bool = False):
    """Obtém interações de um ticket"""
    logger.info(f"[INTERACOES] Obtendo comentários do ticket #{ticket_id}")
    
    from app import get_db_or_404, convert_datetime_list
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Verificar se ticket existe
        cursor.execute("SELECT id FROM tickets WHERE id = %s", (ticket_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket #{ticket_id} não encontrado"
            )
        
        # Montar query com ou sem notas internas
        where = "publico = TRUE" if not mostrar_internas else "1=1"
        
        query = f"""
            SELECT 
                ti.id,
                ti.ticket_id,
                ti.usuario_id,
                ti.tipo,
                ti.publico,
                ti.mensagem,
                ti.created_at,
                u.name AS usuario_nome
            FROM ticket_interacoes ti
            JOIN users u ON ti.usuario_id = u.id
            WHERE ti.ticket_id = %s AND {where}
            ORDER BY ti.created_at ASC
        """
        
        cursor.execute(query, (ticket_id,))
        interacoes = cursor.fetchall()
        interacoes = convert_datetime_list(interacoes)
        
        logger.info(f"[INTERACOES] {len(interacoes)} comentário(s)")
        return interacoes or []
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[INTERACOES] Erro: {str(err)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar interações: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# [POST] Criar nova interação
@interacoes_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=InteracaoResponse,
    summary="Criar interação",
    description="Adiciona um comentário/mensagem a um ticket"
)
async def create_interacao(interacao: InteracaoCreate):
    """Cria uma nova interação"""
    logger.info(f"[INTERACOES] CRIANDO INTERAÇÃO NO TICKET #{interacao.ticket_id}")
    
    from app import get_db_or_404, convert_datetime_to_string
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Verificar ticket
        cursor.execute("SELECT id FROM tickets WHERE id = %s", (interacao.ticket_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket #{interacao.ticket_id} não encontrado"
            )
        
        # Verificar usuário
        cursor.execute("SELECT id FROM users WHERE id = %s", (interacao.usuario_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuário #{interacao.usuario_id} não encontrado"
            )
        
        # Inserir interação
        insert_query = """
            INSERT INTO ticket_interacoes (
                ticket_id, usuario_id, tipo, publico, mensagem
            ) VALUES (%s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (
            interacao.ticket_id,
            interacao.usuario_id,
            interacao.tipo,
            interacao.publico,
            interacao.mensagem
        ))
        
        # Atualizar ultimo_evento_em do ticket
        cursor.execute(
            "UPDATE tickets SET ultimo_evento_em = NOW() WHERE id = %s",
            (interacao.ticket_id,)
        )
        
        conn.commit()
        new_id = cursor.lastrowid
        logger.info(f"[INTERACOES] Interação criada! ID: {new_id}")
        
        # Obter interação criada
        cursor.execute(
            """SELECT id, ticket_id, usuario_id, tipo, publico, mensagem, created_at
               FROM ticket_interacoes WHERE id = %s""",
            (new_id,)
        )
        new_interacao = cursor.fetchone()
        new_interacao = convert_datetime_to_string(new_interacao)
        
        return new_interacao
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[INTERACOES] ERRO: {str(err)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar interação: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# [DELETE] Deletar interação
@interacoes_router.delete(
    "/{interacao_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar interação",
    description="Remove um comentário de um ticket"
)
async def delete_interacao(interacao_id: int):
    """Deleta uma interação"""
    logger.info(f"[INTERACOES] DELETANDO INTERAÇÃO #{interacao_id}")
    
    from app import get_db_or_404
    
    conn = get_db_or_404()
    cursor = None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id FROM ticket_interacoes WHERE id = %s", (interacao_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interação #{interacao_id} não encontrada"
            )
        
        cursor.execute("DELETE FROM ticket_interacoes WHERE id = %s", (interacao_id,))
        conn.commit()
        
        logger.info(f"[INTERACOES] Deletado com sucesso!")
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[INTERACOES] ERRO: {str(err)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar interação: {str(err)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()