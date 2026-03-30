"""
Serviço de Permissões - PermissaoService
Responsabilidade ÚNICA: Validar se usuário pode fazer determinada ação

Validações:
1. usuario_pode_atribuir() → Usuário pode atribuir ticket?
2. usuario_pode_mudar_status() → Usuário pode mudar status?
3. usuario_pode_responder() → Usuário pode responder (público)?
4. usuario_pode_comentar_interno() → Usuário pode comentar internamente?
"""

import logging
import mysql.connector
from mysql.connector import Error

logger = logging.getLogger(__name__)


class PermissaoService:
    """
    Serviço centralizado de permissões
    Valida se usuário pode executar ações em tickets
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
            logger.error(f"[PERM-SERVICE] ❌ Erro de conexão: {err}")
            raise

    # =========================================
    # 1️⃣ PODE ATRIBUIR?
    # =========================================

    def usuario_pode_atribuir(self, usuario_id: int, ticket_id: int) -> bool:
        """
        Valida se usuário pode ATRIBUIR um ticket
        
        Lógica de validação:
        1. Busca autor do ticket
        2. Se usuario_id == solicitante_id → ❌ É autor, não pode atribuir
        3. Busca group_id do usuário
        4. Busca group_id do ticket
        5. Se group_id diferentes → ❌ Não é do setor
        6. Se tudo OK → ✅ PODE atribuir
        
        Args:
            usuario_id (int): ID do usuário tentando fazer ação
            ticket_id (int): ID do ticket que quer atribuir
            
        Returns:
            bool: True=pode atribuir, False=não pode
        """

        conn = None
        cursor = None

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"[PERM-SERVICE] 🔐 Validando permissão: ATRIBUIR")
            logger.info(f"{'='*80}")
            logger.info(f"  ├─ Usuário ID: {usuario_id}")
            logger.info(f"  ├─ Ticket ID: {ticket_id}")

            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)

            # ✅ PASSO 1: Buscar dados do ticket
            logger.info(f"  ├─ 🔍 Buscando dados do ticket...")
            cursor.execute(
                "SELECT solicitante_id, group_id FROM tickets WHERE id = %s",
                (ticket_id,),
            )

            ticket = cursor.fetchone()

            if not ticket:
                logger.warning(f"  ├─ ⚠️ Ticket não encontrado")
                logger.info(f"{'='*80}\n")
                return False

            solicitante_id = ticket["solicitante_id"]
            ticket_group_id = ticket["group_id"]

            logger.info(f"  ├─ ✅ Ticket encontrado")
            logger.info(f"  ├─ ✅ Autor do ticket: {solicitante_id}")
            logger.info(f"  ├─ ✅ Setor destino: {ticket_group_id}")

            # ✅ PASSO 2: Validar se é autor
            logger.info(f"  ├─ 🔍 Verificando: é autor?")

            if usuario_id == solicitante_id:
                logger.warning(f"  ├─ ❌ SIM - Usuário é AUTOR, não pode atribuir")
                logger.info(f"{'='*80}\n")
                return False

            logger.info(f"  ├─ ✅ NÃO - Usuário não é autor")

            # ✅ PASSO 3: Buscar group_id do usuário
            logger.info(f"  ├─ 🔍 Buscando grupo do usuário...")
            cursor.execute(
                "SELECT group_id, name FROM users WHERE id = %s AND is_active = 1",
                (usuario_id,),
            )

            usuario = cursor.fetchone()

            if not usuario:
                logger.warning(f"  ├─ ⚠️ Usuário não encontrado ou inativo")
                logger.info(f"{'='*80}\n")
                return False

            usuario_group_id = usuario["group_id"]
            usuario_nome = usuario["name"]

            logger.info(f"  ├─ ✅ Usuário encontrado: {usuario_nome}")
            logger.info(f"  ├─ ✅ Grupo do usuário: {usuario_group_id}")

            # ✅ PASSO 4: Validar se é do setor
            logger.info(f"  ├─ 🔍 Verificando: pertence ao setor?")

            if usuario_group_id != ticket_group_id:
                logger.warning(
                    f"  ├─ ❌ NÃO - Usuário não pertence ao setor do ticket"
                )
                logger.info(f"{'='*80}\n")
                return False

            logger.info(f"  ├─ ✅ SIM - Usuário pertence ao setor")
            logger.info(f"  └─ ✅ PERMISSÃO CONCEDIDA - Pode atribuir")
            logger.info(f"{'='*80}\n")

            return True

        except Error as err:
            logger.error(f"[PERM-SERVICE] ❌ Erro ao validar: {err}")
            logger.info(f"{'='*80}\n")
            return False

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # =========================================
    # 2️⃣ PODE MUDAR STATUS?
    # =========================================

    def usuario_pode_mudar_status(self, usuario_id: int, ticket_id: int) -> bool:
        """
        Valida se usuário pode MUDAR STATUS de um ticket
        
        Lógica de validação:
        1. Busca autor do ticket
        2. Se usuario_id == solicitante_id → ❌ É autor, não pode mudar status
        3. Busca group_id do usuário
        4. Busca group_id do ticket
        5. Se group_id diferentes → ❌ Não é do setor
        6. Se tudo OK → ✅ PODE mudar status
        
        Args:
            usuario_id (int): ID do usuário tentando fazer ação
            ticket_id (int): ID do ticket que quer mudar status
            
        Returns:
            bool: True=pode mudar status, False=não pode
        """

        conn = None
        cursor = None

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"[PERM-SERVICE] 🔐 Validando permissão: MUDAR STATUS")
            logger.info(f"{'='*80}")
            logger.info(f"  ├─ Usuário ID: {usuario_id}")
            logger.info(f"  ├─ Ticket ID: {ticket_id}")

            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)

            # ✅ PASSO 1: Buscar dados do ticket
            logger.info(f"  ├─ 🔍 Buscando dados do ticket...")
            cursor.execute(
                "SELECT solicitante_id, group_id FROM tickets WHERE id = %s",
                (ticket_id,),
            )

            ticket = cursor.fetchone()

            if not ticket:
                logger.warning(f"  ├─ ⚠️ Ticket não encontrado")
                logger.info(f"{'='*80}\n")
                return False

            solicitante_id = ticket["solicitante_id"]
            ticket_group_id = ticket["group_id"]

            logger.info(f"  ├─ ✅ Ticket encontrado")
            logger.info(f"  ├─ ✅ Autor do ticket: {solicitante_id}")
            logger.info(f"  ├─ ✅ Setor destino: {ticket_group_id}")

            # ✅ PASSO 2: Validar se é autor
            logger.info(f"  ├─ 🔍 Verificando: é autor?")

            if usuario_id == solicitante_id:
                logger.warning(f"  ├─ ❌ SIM - Usuário é AUTOR, não pode mudar status")
                logger.info(f"{'='*80}\n")
                return False

            logger.info(f"  ├─ ✅ NÃO - Usuário não é autor")

            # ✅ PASSO 3: Buscar group_id do usuário
            logger.info(f"  ├─ 🔍 Buscando grupo do usuário...")
            cursor.execute(
                "SELECT group_id, name FROM users WHERE id = %s AND is_active = 1",
                (usuario_id,),
            )

            usuario = cursor.fetchone()

            if not usuario:
                logger.warning(f"  ├─ ⚠️ Usuário não encontrado ou inativo")
                logger.info(f"{'='*80}\n")
                return False

            usuario_group_id = usuario["group_id"]
            usuario_nome = usuario["name"]

            logger.info(f"  ├─ ✅ Usuário encontrado: {usuario_nome}")
            logger.info(f"  ├─ ✅ Grupo do usuário: {usuario_group_id}")

            # ✅ PASSO 4: Validar se é do setor
            logger.info(f"  ├─ 🔍 Verificando: pertence ao setor?")

            if usuario_group_id != ticket_group_id:
                logger.warning(
                    f"  ├─ ❌ NÃO - Usuário não pertence ao setor do ticket"
                )
                logger.info(f"{'='*80}\n")
                return False

            logger.info(f"  ├─ ✅ SIM - Usuário pertence ao setor")
            logger.info(f"  └─ ✅ PERMISSÃO CONCEDIDA - Pode mudar status")
            logger.info(f"{'='*80}\n")

            return True

        except Error as err:
            logger.error(f"[PERM-SERVICE] ❌ Erro ao validar: {err}")
            logger.info(f"{'='*80}\n")
            return False

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # =========================================
    # 3️⃣ PODE RESPONDER (PÚBLICO)?
    # =========================================

    def usuario_pode_responder(self, usuario_id: int, ticket_id: int) -> bool:
        """
        Valida se usuário pode RESPONDER (criar interação pública)
        
        Lógica de validação:
        1. Busca autor do ticket
        2. Se usuario_id == solicitante_id → ✅ É autor, PODE responder
        3. Busca group_id do usuário
        4. Busca group_id do ticket
        5. Se group_id == → ✅ É do setor, PODE responder
        6. Se nenhum dos dois → ❌ Não pode
        
        Args:
            usuario_id (int): ID do usuário tentando fazer ação
            ticket_id (int): ID do ticket que quer responder
            
        Returns:
            bool: True=pode responder, False=não pode
        """

        conn = None
        cursor = None

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"[PERM-SERVICE] 🔐 Validando permissão: RESPONDER")
            logger.info(f"{'='*80}")
            logger.info(f"  ├─ Usuário ID: {usuario_id}")
            logger.info(f"  ├─ Ticket ID: {ticket_id}")

            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)

            # ✅ PASSO 1: Buscar dados do ticket
            logger.info(f"  ├─ 🔍 Buscando dados do ticket...")
            cursor.execute(
                "SELECT solicitante_id, group_id FROM tickets WHERE id = %s",
                (ticket_id,),
            )

            ticket = cursor.fetchone()

            if not ticket:
                logger.warning(f"  ├─ ⚠️ Ticket não encontrado")
                logger.info(f"{'='*80}\n")
                return False

            solicitante_id = ticket["solicitante_id"]
            ticket_group_id = ticket["group_id"]

            logger.info(f"  ├─ ✅ Ticket encontrado")
            logger.info(f"  ├─ ✅ Autor do ticket: {solicitante_id}")
            logger.info(f"  ├─ ✅ Setor destino: {ticket_group_id}")

            # ✅ PASSO 2: Validar se é autor
            logger.info(f"  ├─ 🔍 Verificando: é autor?")

            if usuario_id == solicitante_id:
                logger.info(f"  ├─ ✅ SIM - Usuário é AUTOR, pode responder")
                logger.info(f"  └─ ✅ PERMISSÃO CONCEDIDA - Pode responder")
                logger.info(f"{'='*80}\n")
                return True

            logger.info(f"  ├─ ✅ NÃO - Usuário não é autor")

            # ✅ PASSO 3: Buscar group_id do usuário
            logger.info(f"  ├─ 🔍 Buscando grupo do usuário...")
            cursor.execute(
                "SELECT group_id, name FROM users WHERE id = %s AND is_active = 1",
                (usuario_id,),
            )

            usuario = cursor.fetchone()

            if not usuario:
                logger.warning(f"  ├─ ⚠️ Usuário não encontrado ou inativo")
                logger.info(f"{'='*80}\n")
                return False

            usuario_group_id = usuario["group_id"]
            usuario_nome = usuario["name"]

            logger.info(f"  ├─ ✅ Usuário encontrado: {usuario_nome}")
            logger.info(f"  ├─ ✅ Grupo do usuário: {usuario_group_id}")

            # ✅ PASSO 4: Validar se é do setor
            logger.info(f"  ├─ 🔍 Verificando: pertence ao setor?")

            if usuario_group_id == ticket_group_id:
                logger.info(f"  ├─ ✅ SIM - Usuário pertence ao setor, pode responder")
                logger.info(f"  └─ ✅ PERMISSÃO CONCEDIDA - Pode responder")
                logger.info(f"{'='*80}\n")
                return True

            logger.warning(f"  ├─ ❌ NÃO - Usuário não pertence ao setor")
            logger.warning(f"  └─ ❌ PERMISSÃO NEGADA - Não pode responder")
            logger.info(f"{'='*80}\n")

            return False

        except Error as err:
            logger.error(f"[PERM-SERVICE] ❌ Erro ao validar: {err}")
            logger.info(f"{'='*80}\n")
            return False

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # =========================================
    # 4️⃣ PODE COMENTAR INTERNAMENTE?
    # =========================================

    def usuario_pode_comentar_interno(self, usuario_id: int, ticket_id: int) -> bool:
        """
        Valida se usuário pode COMENTAR INTERNAMENTE
        
        Lógica de validação:
        1. Busca autor do ticket
        2. Se usuario_id == solicitante_id → ❌ É autor, não pode comentar interno
        3. Busca group_id do usuário
        4. Busca group_id do ticket
        5. Se group_id diferentes → ❌ Não é do setor
        6. Se tudo OK → ✅ PODE comentar internamente
        
        Args:
            usuario_id (int): ID do usuário tentando fazer ação
            ticket_id (int): ID do ticket que quer comentar
            
        Returns:
            bool: True=pode comentar internamente, False=não pode
        """

        conn = None
        cursor = None

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"[PERM-SERVICE] 🔐 Validando permissão: COMENTAR INTERNAMENTE")
            logger.info(f"{'='*80}")
            logger.info(f"  ├─ Usuário ID: {usuario_id}")
            logger.info(f"  ├─ Ticket ID: {ticket_id}")

            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)

            # ✅ PASSO 1: Buscar dados do ticket
            logger.info(f"  ├─ 🔍 Buscando dados do ticket...")
            cursor.execute(
                "SELECT solicitante_id, group_id FROM tickets WHERE id = %s",
                (ticket_id,),
            )

            ticket = cursor.fetchone()

            if not ticket:
                logger.warning(f"  ├─ ⚠️ Ticket não encontrado")
                logger.info(f"{'='*80}\n")
                return False

            solicitante_id = ticket["solicitante_id"]
            ticket_group_id = ticket["group_id"]

            logger.info(f"  ├─ ✅ Ticket encontrado")
            logger.info(f"  ├─ ✅ Autor do ticket: {solicitante_id}")
            logger.info(f"  ├─ ✅ Setor destino: {ticket_group_id}")

            # ✅ PASSO 2: Validar se é autor
            logger.info(f"  ├─ 🔍 Verificando: é autor?")

            if usuario_id == solicitante_id:
                logger.warning(
                    f"  ├─ ❌ SIM - Usuário é AUTOR, não pode comentar internamente"
                )
                logger.info(f"{'='*80}\n")
                return False

            logger.info(f"  ├─ ✅ NÃO - Usuário não é autor")

            # ✅ PASSO 3: Buscar group_id do usuário
            logger.info(f"  ├─ 🔍 Buscando grupo do usuário...")
            cursor.execute(
                "SELECT group_id, name FROM users WHERE id = %s AND is_active = 1",
                (usuario_id,),
            )

            usuario = cursor.fetchone()

            if not usuario:
                logger.warning(f"  ├─ ⚠️ Usuário não encontrado ou inativo")
                logger.info(f"{'='*80}\n")
                return False

            usuario_group_id = usuario["group_id"]
            usuario_nome = usuario["name"]

            logger.info(f"  ├─ ✅ Usuário encontrado: {usuario_nome}")
            logger.info(f"  ├─ ✅ Grupo do usuário: {usuario_group_id}")

            # ✅ PASSO 4: Validar se é do setor
            logger.info(f"  ├─ 🔍 Verificando: pertence ao setor?")

            if usuario_group_id != ticket_group_id:
                logger.warning(
                    f"  ├─ ❌ NÃO - Usuário não pertence ao setor do ticket"
                )
                logger.info(f"{'='*80}\n")
                return False

            logger.info(f"  ├─ ✅ SIM - Usuário pertence ao setor")
            logger.info(f"  └─ ✅ PERMISSÃO CONCEDIDA - Pode comentar internamente")
            logger.info(f"{'='*80}\n")

            return True

        except Error as err:
            logger.error(f"[PERM-SERVICE] ❌ Erro ao validar: {err}")
            logger.info(f"{'='*80}\n")
            return False

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()