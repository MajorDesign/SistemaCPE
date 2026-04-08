"""
Serviço de SLA (Service Level Agreement)
- Inicia quando usuário assume o ticket
- Pausa quando usuário devolve OU responsável/admin pausa manualmente
- Retoma quando usuário assume novamente
- Armazena tudo em ticket_sla para relatórios futuros
"""

from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SLAService:

    @staticmethod
    def criar_sla(conn, ticket_id: int, categoria_id: int, sla_minutos: int):
        """
        Cria o registro de SLA para o ticket assim que ele é associado a uma categoria com SLA.
        Status inicial: aguardando (não começa a contar até alguém assumir).
        """
        cursor = conn.cursor(dictionary=True)
        try:
            # Evita duplicata
            cursor.execute("SELECT id FROM ticket_sla WHERE ticket_id = %s", (ticket_id,))
            if cursor.fetchone():
                return

            cursor.execute(
                """
                INSERT INTO ticket_sla (ticket_id, categoria_id, sla_minutos, status)
                VALUES (%s, %s, %s, 'aguardando')
                """,
                (ticket_id, categoria_id, sla_minutos)
            )
            logger.info(f"[SLA] Criado para ticket #{ticket_id} — {sla_minutos} min")
        finally:
            cursor.close()

    @staticmethod
    def iniciar_sla(conn, ticket_id: int) -> bool:
        """
        Marca o início da contagem (quando usuário assume o ticket).
        Se estava pausado, retoma do ponto em que parou.
        Retorna True se houve alteração.
        """
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, status, iniciado_em FROM ticket_sla WHERE ticket_id = %s",
                (ticket_id,)
            )
            sla = cursor.fetchone()
            if not sla:
                return False

            agora = datetime.now()

            if sla["status"] == "aguardando":
                cursor.execute(
                    "UPDATE ticket_sla SET status='em_andamento', iniciado_em=%s, pausado_em=NULL WHERE ticket_id=%s",
                    (agora, ticket_id)
                )
                logger.info(f"[SLA] Iniciado para ticket #{ticket_id}")

            elif sla["status"] == "pausado":
                # Retomar — pausado_em ficará NULL novamente
                cursor.execute(
                    "UPDATE ticket_sla SET status='em_andamento', pausado_em=NULL WHERE ticket_id=%s",
                    (ticket_id,)
                )
                logger.info(f"[SLA] Retomado para ticket #{ticket_id}")

            else:
                return False  # já em andamento ou concluído/estourado

            return True
        finally:
            cursor.close()

    @staticmethod
    def pausar_sla(conn, ticket_id: int) -> bool:
        """
        Pausa a contagem acumulando os minutos já decorridos.
        Chamado quando usuário devolve ou responsável/admin pausa manualmente.
        """
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, status, iniciado_em, minutos_pausados FROM ticket_sla WHERE ticket_id = %s",
                (ticket_id,)
            )
            sla = cursor.fetchone()
            if not sla or sla["status"] != "em_andamento":
                return False

            agora = datetime.now()
            # Minutos decorridos desde o início (descontando pausas anteriores já registradas)
            minutos_decorridos = max(0, int((agora - sla["iniciado_em"]).total_seconds() / 60))
            # O tempo que ficou EM ANDAMENTO neste período é: decorrido - já pausado
            # Mas minutos_pausados acumula o tempo pausado total, não o ativo
            # Guardamos pausado_em para calcular o tempo que ficou parado nesta pausa
            cursor.execute(
                "UPDATE ticket_sla SET status='pausado', pausado_em=%s WHERE ticket_id=%s",
                (agora, ticket_id)
            )
            logger.info(f"[SLA] Pausado para ticket #{ticket_id}")
            return True
        finally:
            cursor.close()

    @staticmethod
    def acumular_pausa(conn, ticket_id: int):
        """
        Quando o SLA é retomado, acumula os minutos que ficou pausado.
        Chamado automaticamente antes de iniciar_sla quando status='pausado'.
        """
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT pausado_em, minutos_pausados FROM ticket_sla WHERE ticket_id = %s AND status = 'pausado'",
                (ticket_id,)
            )
            sla = cursor.fetchone()
            if not sla or not sla["pausado_em"]:
                return

            agora = datetime.now()
            mins_pausa = max(0, int((agora - sla["pausado_em"]).total_seconds() / 60))
            novo_total  = sla["minutos_pausados"] + mins_pausa

            cursor.execute(
                "UPDATE ticket_sla SET minutos_pausados=%s WHERE ticket_id=%s",
                (novo_total, ticket_id)
            )
        finally:
            cursor.close()

    @staticmethod
    def concluir_sla(conn, ticket_id: int):
        """Marca SLA como concluído (ticket fechado/resolvido dentro do prazo)."""
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, status FROM ticket_sla WHERE ticket_id = %s",
                (ticket_id,)
            )
            sla = cursor.fetchone()
            if not sla or sla["status"] in ("concluido", "estourado"):
                return
            cursor.execute(
                "UPDATE ticket_sla SET status='concluido', concluido_em=%s WHERE ticket_id=%s",
                (datetime.now(), ticket_id)
            )
            logger.info(f"[SLA] Concluído para ticket #{ticket_id}")
        finally:
            cursor.close()

    @staticmethod
    def calcular_status_sla(sla: dict) -> dict:
        """
        Dado um dict do ticket_sla, retorna o status atual com:
        - minutos_ativos: minutos de atendimento real (descontando pausas)
        - minutos_restantes: quanto resta do SLA
        - percentual: 0-100+ de uso do SLA
        - cor: 'verde' | 'amarelo' | 'vermelho'
        - label: texto para exibição
        - estourado: bool
        """
        if not sla:
            return None

        status      = sla.get("status")
        sla_total   = sla.get("sla_minutos", 0)
        mins_pausado = sla.get("minutos_pausados", 0) or 0
        iniciado_em = sla.get("iniciado_em")

        if status == "aguardando" or not iniciado_em:
            return {
                "status": "aguardando",
                "cor": "cinza",
                "label": "Aguardando início",
                "minutos_ativos": 0,
                "minutos_restantes": sla_total,
                "percentual": 0,
                "estourado": False
            }

        agora = datetime.now()

        if status == "pausado":
            # Tempo ativo até o momento da pausa
            pausado_em = sla.get("pausado_em")
            if pausado_em:
                minutos_decorridos = max(0, int((pausado_em - iniciado_em).total_seconds() / 60))
            else:
                minutos_decorridos = max(0, int((agora - iniciado_em).total_seconds() / 60))
        elif status in ("concluido", "estourado"):
            concluido_em = sla.get("concluido_em") or sla.get("estourou_em") or agora
            minutos_decorridos = max(0, int((concluido_em - iniciado_em).total_seconds() / 60))
        else:
            # em_andamento
            minutos_decorridos = max(0, int((agora - iniciado_em).total_seconds() / 60))

        minutos_ativos    = max(0, minutos_decorridos - mins_pausado)
        minutos_restantes = sla_total - minutos_ativos
        percentual        = round((minutos_ativos / sla_total * 100), 1) if sla_total > 0 else 0
        estourado         = minutos_ativos > sla_total or status == "estourado"

        if estourado or status == "estourado":
            cor   = "vermelho"
            label = f"SLA estourado há {abs(minutos_restantes)} min"
        elif percentual >= 50:
            cor   = "amarelo"
            label = f"Restam {minutos_restantes} min"
        else:
            cor   = "verde"
            label = f"Restam {minutos_restantes} min"

        if status == "pausado":
            label = f"Pausado — {label}"
        elif status == "concluido":
            cor   = "verde"
            label = "Concluído dentro do prazo"

        return {
            "status":            status,
            "cor":               cor,
            "label":             label,
            "minutos_ativos":    minutos_ativos,
            "minutos_restantes": minutos_restantes,
            "percentual":        percentual,
            "estourado":         estourado
        }
