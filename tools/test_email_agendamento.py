"""
test_email_agendamento.py — dispara os 2 e-mails de agendamento para validar
visual + entrega real via SMTP do Carbonio (perfil 'agenda').

Uso:
    python tools/test_email_agendamento.py <email_destino>
    python tools/test_email_agendamento.py vidajlopes@gmail.com

Executa de forma SÍNCRONA (sem thread) pra mostrar erro/sucesso na hora.
"""
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Mostra logs do email_service (info de envio, warnings, etc) no terminal
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))

# Carrega .env do server/
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / "server" / ".env")
except ImportError:
    print("AVISO: python-dotenv nao instalado — confiando nas vars do shell")

from services.email_service import (  # noqa: E402
    enviar_email,
    email_agendamento_recebido,
    email_agendamento_confirmado,
    email_equipe_novo_agendamento,
    smtp_configurado,
)


def main():
    destino = sys.argv[1] if len(sys.argv) > 1 else "vidajlopes@gmail.com"
    print(f"\n>>> Destino: {destino}")
    print(f">>> SMTP 'agenda' configurado: {smtp_configurado('agenda')}")
    print(f">>> AGENDA_SMTP_HOST: {os.getenv('AGENDA_SMTP_HOST')}")
    print(f">>> AGENDA_SMTP_USER: {os.getenv('AGENDA_SMTP_USER')}")
    print(f">>> AGENDA_SMTP_FROM: {os.getenv('AGENDA_SMTP_FROM')}\n")

    inicio_teste = datetime(2026, 6, 1, 14, 30)
    equipe = (os.getenv("EQUIPE_AGENDA_EMAILS")
              or os.getenv("AGENDA_SMTP_USER", "")).strip()

    # 1) E-mail "RECEBIDO" (pendente) — cliente
    print(">>> [1/3] Enviando e-mail 'recebido' para o cliente...")
    subject, html = email_agendamento_recebido(
        cliente_nome="Jonathan Lopes",
        servico_nome="Treinamento GNSS",
        unidade_nome="CPE Tecnologia BH",
        inicio=inicio_teste,
        modalidade="presencial",
        instrutor="Eng. João Silva",
    )
    enviar_email(
        para=destino,
        assunto="[TESTE 1/3] " + subject,
        html=html,
        perfil="agenda",
        async_send=False,
    )

    # 2) E-mail "CONFIRMADO" — cliente
    print("\n>>> [2/3] Enviando e-mail 'confirmado' para o cliente...")
    subject, html = email_agendamento_confirmado(
        cliente_nome="Jonathan Lopes",
        servico_nome="Treinamento GNSS",
        unidade_nome="CPE Tecnologia BH",
        unidade_endereco="Av. dos Andradas, 3000 - Centro - Belo Horizonte/MG",
        unidade_telefone="(31) 99999-9999",
        inicio=inicio_teste,
        modalidade="presencial",
        instrutor="Eng. João Silva",
    )
    enviar_email(
        para=destino,
        assunto="[TESTE 2/3] " + subject,
        html=html,
        perfil="agenda",
        async_send=False,
    )

    # 3) E-mail "ALERTA EQUIPE" — interno (suporte.agenda.cpe@)
    print(f"\n>>> [3/3] Enviando alerta interno para a equipe ({equipe})...")
    subject, html = email_equipe_novo_agendamento(
        cliente_nome="Jonathan Lopes",
        cliente_email="vidajlopes@gmail.com",
        cliente_telefone="(31) 99999-9999",
        servico_nome="Treinamento GNSS",
        agenda_nome="CPETecnologia BH",
        unidade_nome="CPE Tecnologia BH",
        inicio=inicio_teste,
        modalidade="presencial",
        observacoes="Cliente solicitou ajuda com configuração inicial do GNSS i80.",
        instrutor="Eng. João Silva",
    )
    enviar_email(
        para=equipe,
        assunto="[TESTE 3/3] " + subject,
        html=html,
        perfil="agenda",
        async_send=False,
    )

    print(f"\n>>> FIM.")
    print(f"   2 e-mails (cliente)  -> {destino}")
    print(f"   1 alerta (equipe)    -> {equipe}")
    print(f"   Veja a inbox e a pasta SPAM em ambos.")


if __name__ == "__main__":
    main()
