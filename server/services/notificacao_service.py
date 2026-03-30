"""
Serviço de Notificações - NotificacaoService
Responsabilidade ÚNICA: Inserir notificações automaticamente na tabela notificacoes

Quando é chamado:
1. Novo ticket criado → notificar setor destinatário
2. Nova resposta pública → notificar autor
3. Comentário interno → notificar setor (excluindo autor)
4. Status alterado → notificar autor
5. Ticket atribuído → notificar setor
"""

import logging
import mysql.connector
from mysql.connector import Error
from typing import Tuple

logger = logging.getLogger(__name__)


class NotificacaoService:
    """
    Serviço centralizado de notificações
    Insere registros na tabela notificacoes quando eventos acontecem
    """

    def __init__(self, db_config: dict):
        """
        Inicializa o serviço com configurações do banco de dados
        
        Args:
            db_config (dict): Dicionário com host, user, password, database
        """
        self.db_config = db_config

    def get_connection(self):
        """
        Obtém uma conexão com o banco de dados
        
        Returns:
            mysql.connector.MySQLConnection: Conexão aberta
            
        Raises:
            Error: Se falhar ao conectar
        """
        try:
            return mysql.connector.connect(**self.db_config)
        except Error as err:
            logger.error(f"[NOTIF-SERVICE] ❌ Erro de conexão: {err}")
            raise

    # =========================================
    # 1️⃣ NOTIFICAR SETOR - NOVO TICKET
    # =========================================

    def notificar_novo_ticket(
        self,
        ticket_id: int,
        setor_id: int,
        titulo_ticket: str,
        usuario_autor_nome: str
    ) -> bool:
        """
        Notifica TODOS os membros do setor sobre novo ticket criado
        
        Fluxo:
        1. Busca todos usuarios do setor (WHERE group_id = setor_id)
        2. Para cada usuario: INSERT em notificacoes
        3. Tipo: "ticket_criado"
        4. Mensagem: "Novo ticket: '{titulo}' de {usuario_nome}"
        
        Args:
            ticket_id (int): ID do ticket criado
            setor_id (int): ID do setor destinatário
            titulo_ticket (str): Título do ticket
            usuario_autor_nome (str): Nome de quem criou
            
        Returns:
            bool: True se notificações foram criadas, False se erro
        """

        conn = None
        cursor = None

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"[NOTIF-SERVICE] 📬 Notificando setor sobre NOVO TICKET")
            logger.info(f"{'='*80}")
            logger.info(f"  ├─ Ticket ID: {ticket_id}")
            logger.info(f"  ├─ Setor destino: {setor_id}")
            logger.info(f"  ├─ Título: {titulo_ticket}")
            logger.info(f"  └─ Autor: {usuario_autor_nome}")

            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)

            # ✅ PASSO 1: Buscar todos os usuários do setor
            logger.info(f"  ├─ 🔍 Buscando membros do setor...")
            cursor.execute(
                """
                SELECT id, name 
                FROM users 
                WHERE group_id = %s AND is_active = 1
                """,
                (setor_id,),
            )

            usuarios_setor = cursor.fetchall()
            logger.info(f"  ├─ ✅ {len(usuarios_setor)} membro(s) encontrado(s)")

            if not usuarios_setor:
                logger.warning(f"  └─ ⚠️ Setor sem membros ativos!")
                return False

            # ✅ PASSO 2: Criar notificação para cada membro
            mensagem = f"Novo ticket: \"{titulo_ticket}\" de {usuario_autor_nome}"
            notificacoes_criadas = 0

            for usuario in usuarios_setor:
                try:
                    logger.info(f"  ├─ 💌 Notificando: {usuario['name']}")

                    cursor.execute(
                        """
                        INSERT INTO notificacoes 
                        (ticket_id, usuario_id, mensagem, tipo, lido, created_at)
                        VALUES (%s, %s, %s, %s, 0, NOW())
                        """,
                        (ticket_id, usuario["id"], mensagem, "ticket_criado"),
                    )

                    notificacoes_criadas += 1
                    logger.info(f"  │  └─ ✅ Notificação criada")

                except Error as err:
                    logger.error(f"  │  └─ ❌ Erro ao notificar {usuario['name']}: {err}")
                    continue

            conn.commit()
            logger.info(f"  └─ ✅ {notificacoes_criadas} notificação(ões) criada(s)")
            logger.info(f"{'='*80}\n")

            return notificacoes_criadas > 0

        except Error as err:
            logger.error(f"[NOTIF-SERVICE] ❌ Erro: {err}")
            if conn:
                conn.rollback()
            return False

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # =========================================
    # 2️⃣ NOTIFICAR AUTOR - NOVA RESPOSTA
    # =========================================

    def notificar_nova_resposta(
        self,
        ticket_id: int,
        usuario_autor_id: int,
        usuario_respondente_nome: str,
    ) -> bool:
        """
        Notifica APENAS o autor sobre nova resposta pública no seu ticket
        
        Fluxo:
        1. Busca autor do ticket
        2. INSERT 1 notificação para o autor
        3. Tipo: "nova_resposta"
        4. Mensagem: "Nova resposta de {respondente} no seu ticket"
        
        Args:
            ticket_id (int): ID do ticket
            usuario_autor_id (int): ID do autor do ticket
            usuario_respondente_nome (str): Nome de quem respondeu
            
        Returns:
            bool: True se notificação foi criada, False se erro
        """

        conn = None
        cursor = None

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"[NOTIF-SERVICE] 📬 Notificando AUTOR sobre NOVA RESPOSTA")
            logger.info(f"{'='*80}")
            logger.info(f"  ├─ Ticket ID: {ticket_id}")
            logger.info(f"  ├─ Usuário autor: {usuario_autor_id}")
            logger.info(f"  └─ Respondente: {usuario_respondente_nome}")

            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)

            # ✅ PASSO 1: Validar que usuário existe
            logger.info(f"  ├─ 🔍 Validando autor...")
            cursor.execute(
                "SELECT id, name FROM users WHERE id = %s AND is_active = 1",
                (usuario_autor_id,),
            )

            usuario_autor = cursor.fetchone()

            if not usuario_autor:
                logger.warning(f"  └─ ⚠️ Usuário autor não encontrado ou inativo!")
                return False

            logger.info(f"  ├─ ✅ Autor encontrado: {usuario_autor['name']}")

            # ✅ PASSO 2: Criar notificação para o autor
            logger.info(f"  ├─ 💌 Criando notificação...")
            mensagem = f"Nova resposta de {usuario_respondente_nome} no seu ticket"

            cursor.execute(
                """
                INSERT INTO notificacoes 
                (ticket_id, usuario_id, mensagem, tipo, lido, created_at)
                VALUES (%s, %s, %s, %s, 0, NOW())
                """,
                (ticket_id, usuario_autor_id, mensagem, "nova_resposta"),
            )

            conn.commit()
            logger.info(f"  └─ ✅ Notificação criada")
            logger.info(f"{'='*80}\n")

            return True

        except Error as err:
            logger.error(f"[NOTIF-SERVICE] ❌ Erro: {err}")
            if conn:
                conn.rollback()
            return False

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # =========================================
    # 3️⃣ NOTIFICAR SETOR - COMENTÁRIO INTERNO
    # =========================================

    def notificar_comentario_interno(
        self,
        ticket_id: int,
        setor_id: int,
        usuario_comentador_nome: str,
        usuario_autor_id: int,
    ) -> bool:
        """
        Notifica APENAS membros do setor sobre comentário interno
        NÃO notifica o autor do ticket (comentário é privado)
        
        Fluxo:
        1. Busca autor do ticket (para excluir da notificação)
        2. Busca todos membros do setor EXCLUINDO o autor
        3. Para cada membro: INSERT notificação
        4. Tipo: "comentario_interno"
        5. Mensagem: "Comentário interno de {usuario_nome} no ticket"
        
        Args:
            ticket_id (int): ID do ticket
            setor_id (int): ID do setor
            usuario_comentador_nome (str): Nome de quem comentou
            usuario_autor_id (int): ID do autor (para excluir)
            
        Returns:
            bool: True se notificações foram criadas, False se erro
        """

        conn = None
        cursor = None

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"[NOTIF-SERVICE] 📬 Notificando SETOR sobre COMENTÁRIO INTERNO")
            logger.info(f"{'='*80}")
            logger.info(f"  ├─ Ticket ID: {ticket_id}")
            logger.info(f"  ├─ Setor: {setor_id}")
            logger.info(f"  ├─ Comentador: {usuario_comentador_nome}")
            logger.info(f"  └─ Excluindo autor ID: {usuario_autor_id}")

            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)

            # ✅ PASSO 1: Buscar membros do setor EXCLUINDO o autor
            logger.info(f"  ├─ 🔍 Buscando membros do setor (excluindo autor)...")
            cursor.execute(
                """
                SELECT id, name 
                FROM users 
                WHERE group_id = %s AND is_active = 1 AND id != %s
                """,
                (setor_id, usuario_autor_id),
            )

            usuarios_setor = cursor.fetchall()
            logger.info(f"  ├─ ✅ {len(usuarios_setor)} membro(s) encontrado(s)")

            if not usuarios_setor:
                logger.warning(f"  └─ ⚠️ Nenhum membro para notificar")
                return False

            # ✅ PASSO 2: Criar notificação para cada membro
            mensagem = f"Comentário interno de {usuario_comentador_nome} no ticket"
            notificacoes_criadas = 0

            for usuario in usuarios_setor:
                try:
                    logger.info(f"  ├─ 💌 Notificando: {usuario['name']}")

                    cursor.execute(
                        """
                        INSERT INTO notificacoes 
                        (ticket_id, usuario_id, mensagem, tipo, lido, created_at)
                        VALUES (%s, %s, %s, %s, 0, NOW())
                        """,
                        (ticket_id, usuario["id"], mensagem, "comentario_interno"),
                    )

                    notificacoes_criadas += 1
                    logger.info(f"  │  └─ ✅ Notificação criada")

                except Error as err:
                    logger.error(
                        f"  │  └─ ❌ Erro ao notificar {usuario['name']}: {err}"
                    )
                    continue

            conn.commit()
            logger.info(f"  └─ ✅ {notificacoes_criadas} notificação(ões) criada(s)")
            logger.info(f"{'='*80}\n")

            return notificacoes_criadas > 0

        except Error as err:
            logger.error(f"[NOTIF-SERVICE] ❌ Erro: {err}")
            if conn:
                conn.rollback()
            return False

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # =========================================
    # 4️⃣ NOTIFICAR AUTOR - STATUS ALTERADO
    # =========================================

    def notificar_status_alterado(
        self,
        ticket_id: int,
        usuario_autor_id: int,
        novo_status: str,
    ) -> bool:
        """
        Notifica APENAS o autor quando status do ticket é alterado
        
        Fluxo:
        1. Busca autor do ticket
        2. INSERT 1 notificação
        3. Tipo: "status_alterado"
        4. Mensagem: "Status alterado para {novo_status}"
        
        Args:
            ticket_id (int): ID do ticket
            usuario_autor_id (int): ID do autor
            novo_status (str): Nome do novo status
            
        Returns:
            bool: True se notificação foi criada, False se erro
        """

        conn = None
        cursor = None

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"[NOTIF-SERVICE] 📬 Notificando AUTOR sobre STATUS ALTERADO")
            logger.info(f"{'='*80}")
            logger.info(f"  ├─ Ticket ID: {ticket_id}")
            logger.info(f"  ├─ Usuário autor: {usuario_autor_id}")
            logger.info(f"  └─ Novo status: {novo_status}")

            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)

            # ✅ PASSO 1: Validar que usuário existe
            logger.info(f"  ├─ 🔍 Validando autor...")
            cursor.execute(
                "SELECT id, name FROM users WHERE id = %s AND is_active = 1",
                (usuario_autor_id,),
            )

            usuario_autor = cursor.fetchone()

            if not usuario_autor:
                logger.warning(f"  └─ ⚠️ Usuário autor não encontrado ou inativo!")
                return False

            logger.info(f"  ├─ ✅ Autor encontrado: {usuario_autor['name']}")

            # ✅ PASSO 2: Criar notificação
            logger.info(f"  ├─ 💌 Criando notificação...")
            mensagem = f"Status alterado para {novo_status}"

            cursor.execute(
                """
                INSERT INTO notificacoes 
                (ticket_id, usuario_id, mensagem, tipo, lido, created_at)
                VALUES (%s, %s, %s, %s, 0, NOW())
                """,
                (ticket_id, usuario_autor_id, mensagem, "status_alterado"),
            )

            conn.commit()
            logger.info(f"  └─ ✅ Notificação criada")
            logger.info(f"{'='*80}\n")

            return True

        except Error as err:
            logger.error(f"[NOTIF-SERVICE] ❌ Erro: {err}")
            if conn:
                conn.rollback()
            return False

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # =========================================
    # 5️⃣ NOTIFICAR SETOR - ATRIBUIÇÃO
    # =========================================

    def notificar_atribuicao(
        self,
        ticket_id: int,
        setor_id: int,
        usuario_responsavel_nome: str,
    ) -> bool:
        """
        Notifica setor quando ticket é atribuído a alguém
        
        Fluxo:
        1. Busca todos usuarios do setor
        2. Para cada usuario: INSERT notificação
        3. Tipo: "atribuido"
        4. Mensagem: "Ticket atribuído a {responsavel_nome}"
        
        Args:
            ticket_id (int): ID do ticket
            setor_id (int): ID do setor
            usuario_responsavel_nome (str): Nome do responsável
            
        Returns:
            bool: True se notificações foram criadas, False se erro
        """

        conn = None
        cursor = None

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"[NOTIF-SERVICE] 📬 Notificando SETOR sobre ATRIBUIÇÃO")
            logger.info(f"{'='*80}")
            logger.info(f"  ├─ Ticket ID: {ticket_id}")
            logger.info(f"  ├─ Setor: {setor_id}")
            logger.info(f"  └─ Responsável: {usuario_responsavel_nome}")

            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)

            # ✅ PASSO 1: Buscar todos os usuários do setor
            logger.info(f"  ├─ 🔍 Buscando membros do setor...")
            cursor.execute(
                """
                SELECT id, name 
                FROM users 
                WHERE group_id = %s AND is_active = 1
                """,
                (setor_id,),
            )

            usuarios_setor = cursor.fetchall()
            logger.info(f"  ├─ ✅ {len(usuarios_setor)} membro(s) encontrado(s)")

            if not usuarios_setor:
                logger.warning(f"  └─ ⚠️ Setor sem membros ativos!")
                return False

            # ✅ PASSO 2: Criar notificação para cada membro
            mensagem = f"Ticket atribuído a {usuario_responsavel_nome}"
            notificacoes_criadas = 0

            for usuario in usuarios_setor:
                try:
                    logger.info(f"  ├─ 💌 Notificando: {usuario['name']}")

                    cursor.execute(
                        """
                        INSERT INTO notificacoes 
                        (ticket_id, usuario_id, mensagem, tipo, lido, created_at)
                        VALUES (%s, %s, %s, %s, 0, NOW())
                        """,
                        (ticket_id, usuario["id"], mensagem, "atribuido"),
                    )

                    notificacoes_criadas += 1
                    logger.info(f"  │  └─ ✅ Notificação criada")

                except Error as err:
                    logger.error(f"  │  └─ ❌ Erro ao notificar {usuario['name']}: {err}")
                    continue

            conn.commit()
            logger.info(f"  └─ ✅ {notificacoes_criadas} notificação(ões) criada(s)")
            logger.info(f"{'='*80}\n")

            return notificacoes_criadas > 0

        except Error as err:
            logger.error(f"[NOTIF-SERVICE] ❌ Erro: {err}")
            if conn:
                conn.rollback()
            return False

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()