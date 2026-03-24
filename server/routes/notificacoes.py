from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import datetime
from database import get_db
from models import Notificacao, Ticket, User
from schemas import NotificacaoCreate, NotificacaoUpdate, NotificacaoResponse
import logging

logger = logging.getLogger("app")

router = APIRouter(prefix="/api/notificacoes", tags=["Notificações"])

# =========================================
# GET - LISTAR NOTIFICAÇÕES
# =========================================

@router.get("", response_model=list[NotificacaoResponse])
async def listar_notificacoes(
    usuario_id: int = Query(..., description="ID do usuário"),
    lido: bool = Query(None, description="Filtrar por status de leitura"),
    limite: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Lista notificações do usuário"""
    try:
        logger.info(f"\n{'='*90}")
        logger.info(f"[NOTIFICACOES] 📬 Listando notificações do usuário #{usuario_id}")
        logger.info(f"{'='*90}")
        
        usuario = db.query(User).filter(User.id == usuario_id).first()
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        query = db.query(Notificacao).filter(Notificacao.usuario_id == usuario_id)
        
        if lido is not None:
            query = query.filter(Notificacao.lido == lido)
        
        total = query.count()
        notificacoes = query.order_by(desc(Notificacao.created_at)).offset(offset).limit(limite).all()
        
        logger.info(f"[NOTIFICACOES] ✅ {len(notificacoes)} notificação(ões) encontrada(s)")
        logger.info(f"[NOTIFICACOES]   - Total: {total}")
        logger.info(f"{'='*90}\n")
        
        return notificacoes
        
    except Exception as e:
        logger.error(f"[NOTIFICACOES] ❌ Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =========================================
# POST - CRIAR NOTIFICAÇÃO
# =========================================

@router.post("", response_model=NotificacaoResponse, status_code=201)
async def criar_notificacao(
    notificacao_data: NotificacaoCreate,
    db: Session = Depends(get_db)
):
    """Cria uma nova notificação"""
    try:
        logger.info(f"\n{'='*90}")
        logger.info(f"[NOTIFICACOES] 💌 CRIANDO NOTIFICAÇÃO")
        logger.info(f"{'='*90}")
        logger.info(f"[NOTIFICACOES]   - Ticket: #{notificacao_data.ticket_id}")
        logger.info(f"[NOTIFICACOES]   - Usuário: #{notificacao_data.usuario_id}")
        logger.info(f"[NOTIFICACOES]   - Tipo: {notificacao_data.tipo}")
        
        ticket = db.query(Ticket).filter(Ticket.id == notificacao_data.ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket não encontrado")
        
        usuario = db.query(User).filter(User.id == notificacao_data.usuario_id).first()
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        notificacao = Notificacao(
            ticket_id=notificacao_data.ticket_id,
            usuario_id=notificacao_data.usuario_id,
            mensagem=notificacao_data.mensagem,
            tipo=notificacao_data.tipo,
            lido=notificacao_data.lido,
            created_at=datetime.now()
        )
        
        db.add(notificacao)
        db.commit()
        db.refresh(notificacao)
        
        logger.info(f"[NOTIFICACOES]   ✅ ID criado: {notificacao.id}")
        logger.info(f"[NOTIFICACOES] ✅ NOTIFICAÇÃO CRIADA COM SUCESSO!")
        logger.info(f"{'='*90}\n")
        
        return notificacao
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[NOTIFICACOES] ❌ Erro: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# =========================================
# PUT - MARCAR COMO LIDA
# =========================================

@router.put("/{notificacao_id}", response_model=NotificacaoResponse)
async def marcar_como_lida(
    notificacao_id: int,
    notificacao_update: NotificacaoUpdate,
    db: Session = Depends(get_db)
):
    """Marca notificação como lida"""
    try:
        notificacao = db.query(Notificacao).filter(Notificacao.id == notificacao_id).first()
        if not notificacao:
            raise HTTPException(status_code=404, detail="Notificação não encontrada")
        
        if notificacao_update.lido is not None:
            notificacao.lido = notificacao_update.lido
        
        notificacao.updated_at = datetime.now()
        db.commit()
        db.refresh(notificacao)
        
        logger.info(f"[NOTIFICACOES] ✅ Notificação #{notificacao_id} atualizada")
        
        return notificacao
        
    except Exception as e:
        logger.error(f"[NOTIFICACOES] ❌ Erro: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# =========================================
# DELETE - DELETAR NOTIFICAÇÃO
# =========================================

@router.delete("/{notificacao_id}", status_code=204)
async def deletar_notificacao(notificacao_id: int, db: Session = Depends(get_db)):
    """Deleta uma notificação"""
    try:
        notificacao = db.query(Notificacao).filter(Notificacao.id == notificacao_id).first()
        if not notificacao:
            raise HTTPException(status_code=404, detail="Notificação não encontrada")
        
        db.delete(notificacao)
        db.commit()
        
        logger.info(f"[NOTIFICACOES] ✅ Notificação #{notificacao_id} deletada")
        
        return None
        
    except Exception as e:
        logger.error(f"[NOTIFICACOES] ❌ Erro: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# =========================================
# GET - CONTAR NÃO LIDAS
# =========================================

@router.get("/nao-lidas/{usuario_id}")
async def contar_nao_lidas(usuario_id: int, db: Session = Depends(get_db)):
    """Conta notificações não lidas"""
    try:
        count = db.query(Notificacao).filter(
            and_(
                Notificacao.usuario_id == usuario_id,
                Notificacao.lido == False
            )
        ).count()
        
        return {"usuario_id": usuario_id, "nao_lidas": count}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))