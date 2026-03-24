"""
WebSocket Router - Notificacoes em Tempo Real para Tickets
"""

from fastapi import APIRouter, WebSocket, status, Query
import logging
import json
from datetime import datetime
from typing import Dict, Set
import asyncio

# =========================================
# CONFIGURAR LOGGING
# =========================================
logger = logging.getLogger(__name__)

# =========================================
# GERENCIADOR DE CONEXOES WEBSOCKET
# =========================================

class ConnectionManager:
    """Gerencia conexoes WebSocket ativas"""
    
    def __init__(self):
        # Dict[user_id] = Set[WebSocket]
        self.active_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, user_id: int, websocket: WebSocket):
        """Conecta um novo cliente WebSocket"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        
        logger.info(f"[WS] ✅ USUARIO #{user_id} CONECTADO")
        logger.info(f"[WS]   - Total de conexoes para este usuario: {len(self.active_connections[user_id])}")
        logger.info(f"[WS]   - Usuarios conectados: {len(self.active_connections)}")
    
    def disconnect(self, user_id: int, websocket: WebSocket):
        """Desconecta um cliente WebSocket"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            
            logger.info(f"[WS] ❌ USUARIO #{user_id} DESCONECTADO")
            logger.info(f"[WS]   - Usuarios conectados: {len(self.active_connections)}")
    
    async def broadcast_to_user(self, user_id: int, message: dict):
        """Envia mensagem para todas as conexoes de um usuario"""
        if user_id in self.active_connections:
            logger.info(f"[WS] 📤 Enviando mensagem para usuario #{user_id}")
            logger.info(f"[WS]   - Tipo: {message.get('type', 'unknown')}")
            logger.info(f"[WS]   - Conexoes ativas: {len(self.active_connections[user_id])}")
            
            disconnected = set()
            
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"[WS] ⚠️ Erro ao enviar: {str(e)}")
                    disconnected.add(websocket)
            
            for ws in disconnected:
                self.active_connections[user_id].discard(ws)
    
    async def broadcast_to_all(self, message: dict):
        """Envia mensagem para todos os usuarios conectados"""
        logger.info(f"[WS] 📢 BROADCAST GLOBAL")
        logger.info(f"[WS]   - Tipo: {message.get('type', 'unknown')}")
        logger.info(f"[WS]   - Usuarios conectados: {len(self.active_connections)}")
        
        for user_id in list(self.active_connections.keys()):
            await self.broadcast_to_user(user_id, message)
    
    def get_active_users(self) -> list:
        """Retorna lista de usuarios conectados"""
        return list(self.active_connections.keys())
    
    def get_connection_count(self) -> int:
        """Retorna total de conexoes ativas"""
        total = 0
        for connections in self.active_connections.values():
            total += len(connections)
        return total


# =========================================
# INSTANCIA GLOBAL DO GERENCIADOR
# =========================================
manager = ConnectionManager()

# =========================================
# ROUTER DE WEBSOCKET
# =========================================

ws_router = APIRouter(tags=["websocket"])


@ws_router.websocket("/ws/tickets/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, token: str = Query(None)):
    """
    WebSocket para notificacoes em tempo real de tickets
    
    Query Parameters:
    - token: Token de autenticacao (obtido no login)
    
    Exemplo de URL:
    ws://localhost:8000/ws/tickets/1?token=abc123...
    """
    
    logger.info("\n" + "=" * 90)
    logger.info(f"[WS] 🔌 NOVA TENTATIVA DE CONEXAO")
    logger.info("=" * 90)
    logger.info(f"[WS]   - User ID: {user_id}")
    logger.info(f"[WS]   - IP: {websocket.client.host}:{websocket.client.port}")
    logger.info(f"[WS]   - Token: {token[:20] + '...' if token else 'NENHUM'}")
    
    # ✅ VALIDAR TOKEN
    if not token:
        logger.warning("[WS] ❌ CONEXAO REJEITADA: Token nao fornecido")
        logger.warning("[WS]    > Use: ws://localhost:8000/ws/tickets/{user_id}?token={seu_token}")
        logger.info("=" * 90 + "\n")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token nao fornecido")
        return
    
    # Aqui você pode adicionar validacao mais rigorosa do token
    # Por enquanto, apenas verificamos se o token existe
    logger.info("[WS] ✅ Token validado com sucesso")
    
    try:
        # ✅ CONECTAR
        logger.info("[WS] 🔗 Aceitando conexao...")
        await manager.connect(user_id, websocket)
        logger.info("=" * 90)
        
        # ✅ ENVIAR MENSAGEM DE BOAS-VINDAS
        welcome_message = {
            "type": "connection",
            "status": "connected",
            "user_id": user_id,
            "message": f"Conectado com sucesso! Aguardando notificacoes...",
            "timestamp": datetime.now().isoformat(),
            "active_users": manager.get_active_users(),
            "total_connections": manager.get_connection_count()
        }
        
        logger.info("[WS] 📤 Enviando mensagem de boas-vindas...")
        await websocket.send_json(welcome_message)
        logger.info("[WS] ✅ Mensagem enviada\n")
        
        # ✅ MANTER CONEXAO ATIVA E ESCUTAR MENSAGENS
        while True:
            try:
                data = await websocket.receive_text()
                
                logger.info(f"[WS] 📥 Mensagem recebida do usuario #{user_id}")
                logger.info(f"[WS]   - Conteudo: {data[:100]}...")
                
                # Processar diferentes tipos de mensagens
                try:
                    message = json.loads(data)
                    msg_type = message.get("type", "unknown")
                    
                    if msg_type == "ping":
                        # Responder ao ping com pong
                        pong_message = {
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        }
                        await websocket.send_json(pong_message)
                        logger.info("[WS] 📤 Pong enviado\n")
                    
                    elif msg_type == "status":
                        # Solicitar status das conexoes
                        status_message = {
                            "type": "status",
                            "active_users": manager.get_active_users(),
                            "total_connections": manager.get_connection_count(),
                            "timestamp": datetime.now().isoformat()
                        }
                        await websocket.send_json(status_message)
                        logger.info("[WS] 📤 Status enviado\n")
                    
                    else:
                        logger.warning(f"[WS] ⚠️ Tipo de mensagem desconhecido: {msg_type}\n")
                
                except json.JSONDecodeError:
                    logger.warning("[WS] ⚠️ Erro ao decodificar JSON\n")
            
            except Exception as e:
                logger.error(f"[WS] ❌ Erro ao receber mensagem: {str(e)}\n")
                break
    
    except Exception as err:
        logger.error(f"[WS] ❌ ERRO NA CONEXAO: {str(err)}")
        logger.error(f"[WS]    - Tipo: {type(err).__name__}")
        logger.error(f"[WS]    - Usuario: #{user_id}")
        logger.error("=" * 90 + "\n")
    
    finally:
        manager.disconnect(user_id, websocket)
        logger.info("")


# =========================================
# FUNCOES AUXILIARES PARA ENVIAR NOTIFICACOES
# =========================================

async def notify_ticket_created(user_id: int, ticket_data: dict):
    """Notifica sobre novo ticket criado"""
    message = {
        "type": "ticket_created",
        "status": "success",
        "ticket": ticket_data,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast_to_user(user_id, message)


async def notify_ticket_updated(user_id: int, ticket_id: int, ticket_data: dict):
    """Notifica sobre atualizacao de ticket"""
    message = {
        "type": "ticket_updated",
        "status": "success",
        "ticket_id": ticket_id,
        "ticket": ticket_data,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast_to_user(user_id, message)


async def notify_ticket_closed(user_id: int, ticket_id: int):
    """Notifica sobre fechamento de ticket"""
    message = {
        "type": "ticket_closed",
        "status": "success",
        "ticket_id": ticket_id,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast_to_user(user_id, message)


async def notify_comment_added(user_id: int, ticket_id: int, comment_data: dict):
    """Notifica sobre novo comentario em ticket"""
    message = {
        "type": "comment_added",
        "status": "success",
        "ticket_id": ticket_id,
        "comment": comment_data,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast_to_user(user_id, message)


async def broadcast_notification(title: str, message: str, notification_type: str = "info"):
    """Envia notificacao para todos os usuarios conectados"""
    broadcast_message = {
        "type": "notification",
        "notification_type": notification_type,
        "title": title,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast_to_all(broadcast_message)