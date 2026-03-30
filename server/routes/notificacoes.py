"""
API de Notificações - v1.1 (CORRIGIDA)
Endpoints para listar, editar e deletar notificações
"""

from fastapi import APIRouter, HTTPException, Query, Path, status
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

logger = logging.getLogger(__name__)

LOG_SEPARADOR = "=" * 100
VERSAO_API = "1.1"
LIMITE_PADRAO = 50
LIMITE_MAXIMO = 100

# =========================================
# 🔧 MODELOS PYDANTIC v2 CORRIGIDOS
# Data: 31/03/2026 15:00
# =========================================
# INÍCIO: Modelos de Notificações

class NotificacaoCriar(BaseModel):
    ticket_id: int = Field(..., gt=0, description="ID do ticket")
    usuario_id: int = Field(..., gt=0, description="ID do usuário")
    mensagem: str = Field(..., min_length=1, max_length=500, description="Mensagem da notificação")
    tipo: str = Field(default="info", description="Tipo: info/aviso/erro/sucesso")
    lido: bool = Field(default=False, description="Status de leitura")

    @field_validator("tipo")
    @classmethod
    def validar_tipo(cls, v):
        tipos_validos = [
            "info", 
            "aviso", 
            "erro", 
            "sucesso", 
            "ticket_criado", 
            "nova_resposta", 
            "status_alterado", 
            "atribuido", 
            "comentario_interno"
        ]
        if v not in tipos_validos:
            raise ValueError(f"Tipo inválido. Válidos: {tipos_validos}")
        return v

    @field_validator("mensagem")
    @classmethod
    def validar_mensagem(cls, v):
        if not v or not v.strip():
            raise ValueError("Mensagem não pode estar vazia")
        return v.strip()

class NotificacaoAtualizar(BaseModel):
    lido: Optional[bool] = None
    mensagem: Optional[str] = Field(None, min_length=1, max_length=500)

class NotificacaoResposta(BaseModel):
    id: int
    ticket_id: int
    usuario_id: int
    mensagem: str
    tipo: str
    lido: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class NotificacoesListaResposta(BaseModel):
    total: int
    registros: int
    limite: int
    offset: int
    notificacoes: List[NotificacaoResposta]

class NaoLidasResposta(BaseModel):
    usuario_id: int
    nao_lidas: int

# =========================================
# 🛣️ ROUTER
# Data: 31/03/2026 15:00
# =========================================

notificacoes_router = APIRouter(
    prefix="/api/notificacoes",
    tags=["notificacoes"],
    responses={
        400: {"description": "Dados inválidos"},
        404: {"description": "Recurso não encontrado"},
        500: {"description": "Erro interno do servidor"}
    }
)

# =========================================
# FIM DOS MODELOS - 31/03/2026 15:00
# =========================================

# =========================================
# 🪵 LOGGING HELPERS
# =========================================

def log_inicio(endpoint: str, **kwargs):
    logger.info(f"\n{LOG_SEPARADOR}")
    logger.info(f"[NOTIF-ROUTE v{VERSAO_API}] 🚀 {endpoint}")
    logger.info(f"{LOG_SEPARADOR}")
    for k, v in kwargs.items():
        logger.info(f"  ├─ {k}: {v}")

def log_fim(status_text: str, **kwargs):
    icon = {"sucesso": "✅", "erro": "❌", "aviso": "⚠️"}.get(status_text, "•")
    logger.info(f"  └─ {icon} {status_text.upper()}")
    for k, v in kwargs.items():
        logger.info(f"     └─ {k}: {v}")
    logger.info(f"{LOG_SEPARADOR}\n")

# =========================================
# ✅ VALIDAÇÕES
# =========================================

def validar_usuario_existe(cursor, usuario_id: int) -> dict:
    cursor.execute(
        "SELECT id, name, email FROM users WHERE id = %s AND is_active = 1",
        (usuario_id,)
    )
    usuario = cursor.fetchone()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuário #{usuario_id} não encontrado"
        )
    return usuario

def validar_notificacao_existe(cursor, notificacao_id: int) -> dict:
    cursor.execute(
        "SELECT id, usuario_id, ticket_id FROM notificacoes WHERE id = %s",
        (notificacao_id,)
    )
    notificacao = cursor.fetchone()
    if not notificacao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notificação #{notificacao_id} não encontrada"
        )
    return notificacao

def validar_ticket_existe(cursor, ticket_id: int) -> dict:
    cursor.execute(
        "SELECT id, numero FROM tickets WHERE id = %s",
        (ticket_id,)
    )
    ticket = cursor.fetchone()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket #{ticket_id} não encontrado"
        )
    return ticket

# =========================================
# 📌 ENDPOINTS
# =========================================

@notificacoes_router.get(
    "/usuario/{usuario_id}",
    response_model=List[NotificacaoResposta],
    summary="Listar notificações do usuário",
    description="Retorna todas as notificações de um usuário específico"
)
async def listar_notificacoes_por_usuario(
    usuario_id: int = Path(..., gt=0),
    limite: int = Query(LIMITE_PADRAO, ge=1, le=LIMITE_MAXIMO),
    offset: int = Query(0, ge=0)
):
    log_inicio("listar_notificacoes_por_usuario", usuario_id=usuario_id, limite=limite, offset=offset)
    conexao = get_db_or_404()
    cursor = None

    try:
        cursor = conexao.cursor(dictionary=True)
        validar_usuario_existe(cursor, usuario_id)

        cursor.execute(
            """
            SELECT id, ticket_id, usuario_id, mensagem, tipo, lido, created_at, updated_at
            FROM notificacoes
            WHERE usuario_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (usuario_id, limite, offset)
        )
        notificacoes = convert_datetime_list(cursor.fetchall())
        
        for notif in notificacoes:
            notif['lido'] = bool(notif.get('lido', 0))

        log_fim("sucesso", registros=len(notificacoes))
        return notificacoes

    except HTTPException:
        raise
    except Exception as erro:
        log_fim("erro", erro=str(erro))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao listar notificações do usuário: {str(erro)}")
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

@notificacoes_router.get(
    "/nao-lidas/{usuario_id}",
    response_model=NaoLidasResposta,
    summary="Contar notificações não lidas",
    description="Obtém quantidade de notificações não lidas"
)
async def contar_nao_lidas(
    usuario_id: int = Path(..., gt=0)
):
    log_inicio("contar_nao_lidas", usuario_id=usuario_id)
    conexao = get_db_or_404()
    cursor = None

    try:
        cursor = conexao.cursor(dictionary=True)
        validar_usuario_existe(cursor, usuario_id)

        cursor.execute(
            "SELECT COUNT(*) as total FROM notificacoes WHERE usuario_id = %s AND lido = 0",
            (usuario_id,)
        )
        resultado = cursor.fetchone()
        total_nao_lidas = resultado["total"] if resultado else 0

        log_fim("sucesso", nao_lidas=total_nao_lidas)
        return NaoLidasResposta(usuario_id=usuario_id, nao_lidas=total_nao_lidas)

    except HTTPException:
        raise
    except Exception as erro:
        log_fim("erro", erro=str(erro))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao contar notificações: {str(erro)}")
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

@notificacoes_router.get(
    "/",
    response_model=NotificacoesListaResposta,
    summary="Listar notificações",
    description="Obtém notificações do usuário com filtros opcionais"
)
async def listar_notificacoes(
    usuario_id: int = Query(..., gt=0),
    lido: Optional[bool] = Query(None),
    tipo: Optional[str] = Query(None),
    limite: int = Query(LIMITE_PADRAO, ge=1, le=LIMITE_MAXIMO),
    offset: int = Query(0, ge=0)
):
    log_inicio("listar_notificacoes", usuario_id=usuario_id, lido=lido, tipo=tipo, limite=limite, offset=offset)
    conexao = get_db_or_404()
    cursor = None

    try:
        cursor = conexao.cursor(dictionary=True)
        usuario = validar_usuario_existe(cursor, usuario_id)

        filtros = ["usuario_id = %s"]
        params = [usuario_id]

        if lido is not None:
            filtros.append("lido = %s")
            params.append(1 if lido else 0)

        if tipo is not None:
            tipos_validos = ["info", "aviso", "erro", "sucesso", "ticket_criado", "nova_resposta", "status_alterado", "atribuido", "comentario_interno"]
            if tipo not in tipos_validos:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Tipo inválido. Válidos: {tipos_validos}")
            filtros.append("tipo = %s")
            params.append(tipo)

        where = " AND ".join(filtros)

        cursor.execute(f"SELECT COUNT(*) as total FROM notificacoes WHERE {where}", params)
        total = cursor.fetchone()["total"]

        cursor.execute(
            f"""
            SELECT id, ticket_id, usuario_id, mensagem, tipo, lido, created_at, updated_at
            FROM notificacoes
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            params + [limite, offset]
        )
        notificacoes = convert_datetime_list(cursor.fetchall())
        
        for notif in notificacoes:
            notif['lido'] = bool(notif.get('lido', 0))

        log_fim("sucesso", total=total, registros=len(notificacoes))
        return NotificacoesListaResposta(
            total=total,
            registros=len(notificacoes),
            limite=limite,
            offset=offset,
            notificacoes=notificacoes
        )

    except HTTPException:
        raise
    except Exception as erro:
        log_fim("erro", erro=str(erro))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao listar notificações: {str(erro)}")
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

@notificacoes_router.put(
    "/{notificacao_id}",
    response_model=NotificacaoResposta,
    summary="Atualizar notificação",
    description="Marca notificação como lida/não lida ou atualiza mensagem"
)
async def atualizar_notificacao(
    notificacao_id: int = Path(..., gt=0),
    usuario_id: int = Query(..., gt=0),
    notificacao: NotificacaoAtualizar = None
):
    log_inicio("atualizar_notificacao", notificacao_id=notificacao_id, usuario_id=usuario_id)
    conexao = get_db_or_404()
    cursor = None

    try:
        cursor = conexao.cursor(dictionary=True)
        notif_dados = validar_notificacao_existe(cursor, notificacao_id)
        if notif_dados["usuario_id"] != usuario_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não pode editar essa notificação")

        atualizacoes = []
        params = []

        if notificacao is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload vazio")

        if notificacao.lido is not None:
            atualizacoes.append("lido = %s")
            params.append(1 if notificacao.lido else 0)

        if notificacao.mensagem is not None:
            atualizacoes.append("mensagem = %s")
            params.append(notificacao.mensagem)

        if not atualizacoes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhum campo para atualizar")

        atualizacoes.append("updated_at = NOW()")
        params.append(notificacao_id)

        cursor.execute(f"UPDATE notificacoes SET {', '.join(atualizacoes)} WHERE id = %s", params)
        conexao.commit()

        cursor.execute("SELECT id, ticket_id, usuario_id, mensagem, tipo, lido, created_at, updated_at FROM notificacoes WHERE id = %s", (notificacao_id,))
        notif_atualizada = convert_datetime_to_string(cursor.fetchone())
        notif_atualizada['lido'] = bool(notif_atualizada.get('lido', 0))

        log_fim("sucesso", notificacao_id=notificacao_id)
        return NotificacaoResposta(**notif_atualizada)

    except HTTPException:
        raise
    except Exception as erro:
        log_fim("erro", erro=str(erro))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao atualizar notificação: {str(erro)}")
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

# ========================================
# 🗑️ DELETAR NOTIFICAÇÕES LIDAS
# Data: 31/03/2026 15:05
# ========================================
# INÍCIO: Adicionar novo endpoint

@notificacoes_router.delete(
    "/limpador/lidas",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    summary="Limpar notificações lidas",
    description="Remove todas as notificações já lidas do usuário"
)
async def limpar_notificacoes_lidas(
    usuario_id: int = Query(..., gt=0, description="ID do usuário")
):
    log_inicio("limpar_notificacoes_lidas", usuario_id=usuario_id)
    conexao = get_db_or_404()
    cursor = None

    try:
        cursor = conexao.cursor(dictionary=True)

        # Validar que usuário existe
        validar_usuario_existe(cursor, usuario_id)

        # Contar quantas serão deletadas
        cursor.execute(
            "SELECT COUNT(*) as total FROM notificacoes WHERE usuario_id = %s AND lido = 1",
            (usuario_id,)
        )
        resultado = cursor.fetchone()
        total_deletadas = resultado["total"] if resultado else 0

        logger.info(f"  ▶️ Deletando {total_deletadas} notificação(ões) lida(s)...")

        # Deletar todas as notificações lidas
        cursor.execute(
            "DELETE FROM notificacoes WHERE usuario_id = %s AND lido = 1",
            (usuario_id,)
        )
        conexao.commit()

        logger.info(f"  ✅ {total_deletadas} notificação(ões) deletada(s) com sucesso")

        resposta = {
            "sucesso": True,
            "mensagem": f"{total_deletadas} notificação(ões) lida(s) removida(s)",
            "total_deletadas": total_deletadas,
            "usuario_id": usuario_id
        }

        log_fim("sucesso", total_deletadas=total_deletadas)
        return resposta

    except HTTPException:
        raise
    except Exception as e:
        log_fim("erro", erro=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao limpar notificações: {str(e)}"
        )
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

# ========================================
# FIM DO ENDPOINT - 31/03/2026 15:05
# ========================================