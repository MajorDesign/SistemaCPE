"""
email_service.py — envio de e-mails transacionais via SMTP do Carbonio.

Configuração via .env:
    SMTP_HOST       → host do servidor SMTP   (ex: mail.cpetecnologia.com.br)
    SMTP_PORT       → porta (ex: 587 para STARTTLS, 465 para SSL puro)
    SMTP_USER       → conta autenticada para envio
    SMTP_PASSWORD   → senha da conta
    SMTP_FROM       → endereço que aparece em "De:" (default = SMTP_USER)
    SMTP_FROM_NAME  → nome amigável do remetente (default = "CPE Control")
    SMTP_USE_TLS    → "1" para STARTTLS (default), "0" para desabilitar
    SMTP_USE_SSL    → "1" para SSL puro (porta 465). Default = "0".

Envio sempre acontece em uma thread separada — a requisição HTTP não bloqueia
esperando o SMTP responder. Falhas são logadas mas NÃO derrubam o endpoint.
"""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
import threading
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

# Carrega .env só pra garantir (em caso de import isolado)
try:
    from config import APP_VERSION  # noqa: F401  — força load_dotenv
except Exception:
    pass


def _get_cfg(perfil: str = "default") -> dict:
    """Lê o config SMTP do ambiente a cada envio (permite hot reload sem restart).

    perfil:
        - "default": SMTP geral (tickets, etc) — vars SMTP_*
        - "agenda":  SMTP do modulo de agendamento — vars AGENDA_SMTP_*
                     com fallback para as SMTP_* gerais quando nao definidas
                     (mantem o sistema funcional sem precisar duplicar config)
    """
    if perfil == "agenda":
        # tenta as AGENDA_SMTP_* primeiro; cai pra SMTP_* se nao tiver
        host = os.getenv("AGENDA_SMTP_HOST", "").strip() or os.getenv("SMTP_HOST", "").strip()
        port = int(os.getenv("AGENDA_SMTP_PORT", "") or os.getenv("SMTP_PORT", "587") or "587")
        user = os.getenv("AGENDA_SMTP_USER", "").strip() or os.getenv("SMTP_USER", "").strip()
        pwd  = os.getenv("AGENDA_SMTP_PASSWORD", "") or os.getenv("SMTP_PASSWORD", "")
        from_addr = (os.getenv("AGENDA_SMTP_FROM") or os.getenv("AGENDA_SMTP_USER")
                     or os.getenv("SMTP_FROM") or os.getenv("SMTP_USER") or "").strip()
        from_name = (os.getenv("AGENDA_SMTP_FROM_NAME")
                     or "CPE Tecnologia - Agendamento").strip()
        use_tls = (os.getenv("AGENDA_SMTP_USE_TLS") or os.getenv("SMTP_USE_TLS", "1")).strip() == "1"
        use_ssl = (os.getenv("AGENDA_SMTP_USE_SSL") or os.getenv("SMTP_USE_SSL", "0")).strip() == "1"
        return {"host": host, "port": port, "user": user, "password": pwd,
                "from_addr": from_addr, "from_name": from_name,
                "use_tls": use_tls, "use_ssl": use_ssl}

    return {
        "host":      os.getenv("SMTP_HOST", "").strip(),
        "port":      int(os.getenv("SMTP_PORT", "587") or "587"),
        "user":      os.getenv("SMTP_USER", "").strip(),
        "password":  os.getenv("SMTP_PASSWORD", ""),
        "from_addr": (os.getenv("SMTP_FROM") or os.getenv("SMTP_USER") or "").strip(),
        "from_name": os.getenv("SMTP_FROM_NAME", "CPE Control").strip(),
        "use_tls":   os.getenv("SMTP_USE_TLS", "1").strip() == "1",
        "use_ssl":   os.getenv("SMTP_USE_SSL", "0").strip() == "1",
    }


def smtp_configurado(perfil: str = "default") -> bool:
    cfg = _get_cfg(perfil)
    return bool(cfg["host"] and cfg["user"] and cfg["from_addr"])


def _enviar_sync(
    para: list[str],
    assunto: str,
    html: str,
    texto: Optional[str],
    reply_to: Optional[str],
    perfil: str = "default",
) -> None:
    cfg = _get_cfg(perfil)
    if not smtp_configurado(perfil):
        logger.warning(
            f"[EMAIL] SMTP ({perfil}) nao configurado — assunto='{assunto}' destinatarios={para} "
            f"(defina {'AGENDA_' if perfil == 'agenda' else ''}SMTP_HOST/USER/FROM no .env)"
        )
        return

    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"]    = formataddr((cfg["from_name"], cfg["from_addr"]))
    msg["To"]      = ", ".join(para)
    msg["Message-ID"] = make_msgid(domain=cfg["from_addr"].split("@", 1)[-1] or "cpe")
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.set_content(texto or _html_to_text(html))
    msg.add_alternative(html, subtype="html")

    try:
        if cfg["use_ssl"]:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=ctx, timeout=30) as smtp:
                smtp.login(cfg["user"], cfg["password"])
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as smtp:
                smtp.ehlo()
                if cfg["use_tls"]:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                if cfg["user"] and cfg["password"]:
                    smtp.login(cfg["user"], cfg["password"])
                smtp.send_message(msg)
        logger.info(f"[EMAIL] ✅ Enviado: assunto='{assunto}' → {para}")
    except Exception as err:
        logger.error(f"[EMAIL] ❌ Falha ao enviar para {para}: {err}")


def enviar_email(
    para: str | Iterable[str],
    assunto: str,
    html: str,
    texto: Optional[str] = None,
    reply_to: Optional[str] = None,
    async_send: bool = True,
    perfil: str = "default",
) -> None:
    """Dispara um e-mail. Por padrão envia em background (não bloqueia o request).

    `para` pode ser uma string ou lista de strings. E-mails inválidos/vazios são
    descartados silenciosamente. `perfil` escolhe o conjunto de variáveis SMTP
    do .env: "default" usa SMTP_*, "agenda" usa AGENDA_SMTP_* (com fallback).
    """
    destinatarios = [e.strip() for e in ([para] if isinstance(para, str) else list(para))
                     if e and "@" in (e or "")]
    if not destinatarios:
        logger.warning(f"[EMAIL] sem destinatários válidos para assunto='{assunto}'")
        return

    if async_send:
        t = threading.Thread(
            target=_enviar_sync,
            args=(destinatarios, assunto, html, texto, reply_to, perfil),
            daemon=True,
        )
        t.start()
    else:
        _enviar_sync(destinatarios, assunto, html, texto, reply_to, perfil)


# =====================================================================
# Templates HTML — visual leve, cores do sistema (#667eea / #764ba2)
# =====================================================================

_BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><title>{title}</title></head>
<body style="margin:0;padding:0;background:#f5f5f7;font-family:Segoe UI,Roboto,Arial,sans-serif;color:#1f2937;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;background:#fff;border-radius:12px;overflow:hidden;
                    box-shadow:0 4px 14px rgba(0,0,0,0.06);">
        <tr>
          <td style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
                     padding:20px 28px;color:#fff;">
            <div style="font-size:13px;letter-spacing:.06em;text-transform:uppercase;opacity:.85;">
              {tag}
            </div>
            <div style="font-size:20px;font-weight:600;margin-top:4px;">
              {title}
            </div>
          </td>
        </tr>
        <tr><td style="padding:24px 28px;font-size:14px;line-height:1.55;">
          {body}
        </td></tr>
        <tr>
          <td style="padding:14px 28px;background:#f9fafb;border-top:1px solid #eef0f4;
                     font-size:12px;color:#6b7280;">
            <div>CPE Control · Sistema de Chamados</div>
            <div style="margin-top:2px;">Você está recebendo este e-mail porque está envolvido neste chamado.</div>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def _html_to_text(html: str) -> str:
    """Versão texto-puro grosseira (apenas pra fallback de clients que não renderizam HTML)."""
    import re
    txt = re.sub(r"<\s*br\s*/?\s*>", "\n", html, flags=re.I)
    txt = re.sub(r"</\s*p\s*>", "\n\n", txt, flags=re.I)
    txt = re.sub(r"<[^>]+>", "", txt)
    return re.sub(r"\n{3,}", "\n\n", txt).strip()


def _escape(s: str | None) -> str:
    if not s:
        return ""
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&#39;"))


def _info_box(label: str, valor: str) -> str:
    return (
        f'<tr><td style="padding:6px 0;color:#6b7280;width:120px;">{_escape(label)}</td>'
        f'<td style="padding:6px 0;font-weight:600;">{_escape(valor)}</td></tr>'
    )


# ---------------------------------------------------------------------
# Mensagens prontas
# ---------------------------------------------------------------------

def email_ticket_criado(
    *, para: str, ticket_numero: str, assunto: str,
    descricao: str, grupo: str, prioridade: str, solicitante_nome: str
) -> tuple[str, str]:
    """Retorna (subject, html) para o e-mail de ticket criado."""
    subject = f"[Chamado {ticket_numero}] Recebemos sua solicitação"
    body = f"""
        <p>Olá <strong>{_escape(solicitante_nome)}</strong>,</p>
        <p>Recebemos sua solicitação e ela já está registrada em nosso sistema.
        Acompanhe abaixo os detalhes:</p>

        <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
               style="border-collapse:collapse;margin:14px 0;border:1px solid #eef0f4;border-radius:8px;">
          <tbody>
            {_info_box("Nº do chamado", ticket_numero)}
            {_info_box("Assunto", assunto)}
            {_info_box("Setor", grupo)}
            {_info_box("Prioridade", prioridade)}
          </tbody>
        </table>

        <div style="margin:14px 0;padding:12px 14px;background:#f9fafb;
                    border-left:4px solid #667eea;border-radius:6px;">
          <div style="font-size:12px;color:#6b7280;margin-bottom:4px;">Descrição</div>
          <div style="white-space:pre-wrap;">{_escape(descricao)}</div>
        </div>

        <p>Em breve um responsável atenderá seu chamado. Você pode acompanhar
        o andamento no sistema.</p>
    """
    html = _BASE_TEMPLATE.format(title="Seu chamado foi registrado", tag="Novo Chamado", body=body)
    return subject, html


def email_resposta_publica(
    *, ticket_numero: str, assunto: str,
    autor_nome: str, mensagem: str, destinatario_nome: str
) -> tuple[str, str]:
    """E-mail para o solicitante (ou responsável) quando há nova resposta pública."""
    subject = f"[Chamado {ticket_numero}] Nova resposta: {assunto}"
    body = f"""
        <p>Olá <strong>{_escape(destinatario_nome)}</strong>,</p>
        <p>O chamado <strong>{_escape(ticket_numero)}</strong> recebeu uma nova resposta de
           <strong>{_escape(autor_nome)}</strong>:</p>

        <div style="margin:14px 0;padding:14px 16px;background:#f9fafb;
                    border-left:4px solid #667eea;border-radius:6px;">
          <div style="font-size:12px;color:#6b7280;margin-bottom:6px;">
            {_escape(autor_nome)} escreveu:
          </div>
          <div style="white-space:pre-wrap;">{_escape(mensagem)}</div>
        </div>

        <p>Acesse o sistema para visualizar o histórico completo do chamado e responder.</p>
    """
    html = _BASE_TEMPLATE.format(title="Nova resposta no chamado", tag="Atualização", body=body)
    return subject, html


# =====================================================================
# AGENDAMENTO — recebido (pendente) e confirmado
# =====================================================================

# Template proprio do agendamento — cores CPE Control (preto #1A1A1A + amarelo #FFC107).
# Logo "CPE" desenhada como pill amarelo+preto via HTML/CSS inline pra ser robusto
# em todos clientes de email (Gmail/Outlook bloqueiam filter:invert em imagens).
_AGENDA_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><title>{title}</title></head>
<body style="margin:0;padding:0;background:#F4F6F9;font-family:'Segoe UI',Roboto,Arial,sans-serif;color:#1A1A1A;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;background:#FFFFFF;border-radius:14px;overflow:hidden;
                    box-shadow:0 6px 20px rgba(0,0,0,0.08);">
        <!-- Header preto com logo CPE amarela -->
        <tr>
          <td style="background:#1A1A1A;padding:24px 28px;color:#FFFFFF;">
            <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
              <tr>
                <td valign="middle" style="width:64px;">
                  <div style="display:inline-block;background:#FFC107;color:#1A1A1A;
                              font-weight:900;font-size:18px;padding:10px 14px;
                              border-radius:8px;letter-spacing:1px;
                              font-family:Arial,sans-serif;line-height:1;">CPE</div>
                </td>
                <td valign="middle" style="padding-left:14px;">
                  <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;
                              color:#FFC107;font-weight:700;">
                    {tag}
                  </div>
                  <div style="font-size:22px;font-weight:700;margin-top:4px;color:#FFFFFF;
                              font-family:'Segoe UI',sans-serif;">
                    {title}
                  </div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr><td style="padding:26px 28px;font-size:14px;line-height:1.55;color:#1A1A1A;">
          {body}
        </td></tr>
        <!-- Footer com fundo claro + acentos amarelos -->
        <tr>
          <td style="padding:18px 28px;background:#FAFAFA;border-top:1px solid #E5E7EB;
                     font-size:12px;color:#6B7280;text-align:center;">
            <div style="margin-bottom:8px;color:#1A1A1A;">
              <strong>Por favor, nao responda este e-mail.</strong>
            </div>
            <div>
              Em caso de duvidas, escreva para
              <a href="mailto:aline.milagres@cpetecnologia.com.br"
                 style="color:#1A1A1A;background:#FFF3C2;padding:2px 8px;border-radius:4px;
                        text-decoration:none;font-weight:700;">
                aline.milagres@cpetecnologia.com.br
              </a>
            </div>
            <div style="margin-top:12px;color:#9CA3AF;font-size:11px;">
              <span style="color:#1A1A1A;font-weight:700;">CPE Tecnologia</span>
              &middot; Suporte Tecnico
            </div>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def _fmt_data_br(dt) -> str:
    """Formata datetime → 'dd/mm/aaaa, dia da semana, HH:MM'."""
    if dt is None:
        return ""
    dias = ["segunda-feira", "terca-feira", "quarta-feira", "quinta-feira",
            "sexta-feira", "sabado", "domingo"]
    return f"{dt.strftime('%d/%m/%Y')} ({dias[dt.weekday()]}) as {dt.strftime('%H:%M')}"


def _agenda_info_row(label: str, valor: str) -> str:
    if not valor:
        return ""
    return (
        f'<tr>'
        f'<td style="padding:8px 0;color:#6b7280;width:140px;vertical-align:top;">{_escape(label)}</td>'
        f'<td style="padding:8px 0;font-weight:600;color:#0f172a;">{_escape(valor)}</td>'
        f'</tr>'
    )


def email_agendamento_recebido(
    *, cliente_nome: str, servico_nome: str, unidade_nome: str,
    inicio, modalidade: str, instrutor: Optional[str] = None,
) -> tuple[str, str]:
    """E-mail quando o cliente acabou de preencher o formulario publico.
    Status inicial = 'pendente'. Avisa que a equipe vai confirmar."""
    subject = f"Recebemos seu agendamento - {servico_nome}"
    modal_label = "Online (videochamada)" if modalidade == "online" else "Presencial"

    body = f"""
        <p>Ola <strong>{_escape(cliente_nome)}</strong>,</p>
        <p>Recebemos sua solicitacao de agendamento! Em breve nossa equipe de
        suporte vai analisar a disponibilidade e <strong>confirmar</strong> ou
        entrar em contato caso precise reagendar.</p>

        <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
               style="border-collapse:collapse;margin:18px 0;padding:14px 16px;
                      background:#FFF8E1;border-left:4px solid #FFC107;border-radius:8px;">
          <tbody>
            {_agenda_info_row("Curso/Servico", servico_nome)}
            {_agenda_info_row("Instrutor", instrutor or "")}
            {_agenda_info_row("Local", unidade_nome)}
            {_agenda_info_row("Modalidade", modal_label)}
            {_agenda_info_row("Data e horario", _fmt_data_br(inicio))}
          </tbody>
        </table>

        <div style="margin:18px 0;padding:12px 14px;background:#1A1A1A;
                    border-left:4px solid #FFC107;border-radius:6px;font-size:13px;
                    color:#FFFFFF;">
          <strong style="color:#FFC107;">Status:</strong> Aguardando confirmacao da equipe.
          Voce recebera um novo e-mail assim que o agendamento for confirmado.
        </div>

        <p style="color:#6b7280;font-size:13px;">
          Obrigado por escolher a CPE Tecnologia!
        </p>
    """
    html = _AGENDA_TEMPLATE.format(
        title="Recebemos seu agendamento",
        tag="Agendamento Pendente",
        body=body,
    )
    return subject, html


def email_agendamento_confirmado(
    *, cliente_nome: str, servico_nome: str, unidade_nome: str,
    unidade_endereco: Optional[str], unidade_telefone: Optional[str],
    inicio, modalidade: str, instrutor: Optional[str] = None,
) -> tuple[str, str]:
    """E-mail enviado quando a equipe confirma (status muda de pendente -> agendado).
    Mostra todos os detalhes pro cliente."""
    subject = f"Agendamento confirmado - {servico_nome}"

    if modalidade == "online":
        local_txt = "Online via videochamada"
        local_extra = ("O link da videochamada sera enviado proximo ao horario do "
                       "atendimento.")
    else:
        local_txt = unidade_nome
        partes = []
        if unidade_endereco:
            partes.append(unidade_endereco)
        local_extra = " &middot; ".join(partes) if partes else ""

    body = f"""
        <p>Ola <strong>{_escape(cliente_nome)}</strong>,</p>
        <p>Boa noticia! Seu agendamento foi <strong style="color:#15803d;">confirmado</strong>
        pela nossa equipe de suporte. Anote os detalhes abaixo:</p>

        <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
               style="border-collapse:collapse;margin:18px 0;padding:16px 18px;
                      background:#ecfdf5;border-left:4px solid #10b981;border-radius:8px;">
          <tbody>
            {_agenda_info_row("Curso/Servico", servico_nome)}
            {_agenda_info_row("Instrutor", instrutor or "")}
            {_agenda_info_row("Modalidade",
                              "Online (videochamada)" if modalidade == "online" else "Presencial")}
            {_agenda_info_row("Local", local_txt)}
            {_agenda_info_row("Endereco", local_extra) if (modalidade != "online" and local_extra) else ""}
            {_agenda_info_row("Data e horario", _fmt_data_br(inicio))}
            {_agenda_info_row("Telefone da unidade", unidade_telefone or "")}
          </tbody>
        </table>

        {f'''<div style="margin:16px 0;padding:12px 14px;background:#eff6ff;
                    border-left:4px solid #3b82f6;border-radius:6px;font-size:13px;color:#1e3a8a;">
          <strong>Atendimento online:</strong> {local_extra}
        </div>''' if (modalidade == "online" and local_extra) else ''}

        <p style="margin-top:18px;">
          <strong>Importante:</strong> Caso nao possa comparecer, avise nossa equipe
          o quanto antes para liberarmos o horario para outro cliente.
        </p>

        <p style="color:#6b7280;font-size:13px;margin-top:18px;">
          Te esperamos! Equipe CPE Tecnologia.
        </p>
    """
    html = _AGENDA_TEMPLATE.format(
        title="Agendamento confirmado!",
        tag="Confirmado",
        body=body,
    )
    return subject, html


def email_equipe_novo_agendamento(
    *, cliente_nome: str, cliente_email: str, cliente_telefone: str,
    servico_nome: str, agenda_nome: str, unidade_nome: Optional[str],
    inicio, modalidade: str, observacoes: Optional[str] = None,
    instrutor: Optional[str] = None,
) -> tuple[str, str]:
    """Alerta interno enviado para a equipe (suporte.agenda.cpe@) quando
    surge um novo agendamento PENDENTE no formulario publico. Tom de
    alerta — apoio pra equipe nao perder o pendente."""
    subject = f"[NOVO] Agendamento pendente: {cliente_nome} - {servico_nome}"
    local = unidade_nome or agenda_nome
    modal_label = "Online" if modalidade == "online" else "Presencial"

    obs_block = (
        f'''<div style="margin:14px 0;padding:12px 14px;background:#f9fafb;
                       border-left:4px solid #6b7280;border-radius:6px;">
              <div style="font-size:12px;color:#6b7280;margin-bottom:4px;font-weight:600;">
                Observacao do cliente
              </div>
              <div style="white-space:pre-wrap;">{_escape(observacoes)}</div>
            </div>'''
        if observacoes else ""
    )

    body = f"""
        <p>Novo agendamento criado pelo formulario publico — <strong>aguardando
        confirmacao</strong>:</p>

        <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
               style="border-collapse:collapse;margin:18px 0;padding:14px 16px;
                      background:#fffbeb;border-left:4px solid #f59e0b;border-radius:8px;">
          <tbody>
            {_agenda_info_row("Cliente", cliente_nome)}
            {_agenda_info_row("E-mail", cliente_email)}
            {_agenda_info_row("Telefone", cliente_telefone)}
            {_agenda_info_row("Curso/Servico", servico_nome)}
            {_agenda_info_row("Instrutor", instrutor or "")}
            {_agenda_info_row("Local", local)}
            {_agenda_info_row("Modalidade", modal_label)}
            {_agenda_info_row("Data e horario", _fmt_data_br(inicio))}
          </tbody>
        </table>

        {obs_block}

        <p style="margin-top:18px;font-size:13px;color:#6b7280;">
          Acesse <strong>Equipe de Suporte &rarr; Dashboard &rarr; Aguardando
          confirmacao</strong> para aprovar ou recusar.
        </p>
    """
    html = _AGENDA_TEMPLATE.format(
        title="Novo agendamento pendente",
        tag="Acao necessaria",
        body=body,
    )
    return subject, html


def email_ticket_finalizado(
    *, ticket_numero: str, assunto: str, solicitante_nome: str,
    finalizador_nome: str, solucao: str
) -> tuple[str, str]:
    """E-mail final com motivo/solução."""
    subject = f"[Chamado {ticket_numero}] Finalizado — {assunto}"
    body = f"""
        <p>Olá <strong>{_escape(solicitante_nome)}</strong>,</p>
        <p>Seu chamado <strong>{_escape(ticket_numero)}</strong> foi finalizado por
           <strong>{_escape(finalizador_nome)}</strong>.</p>

        <div style="margin:14px 0;padding:14px 16px;background:#ecfdf5;
                    border-left:4px solid #10b981;border-radius:6px;">
          <div style="font-size:12px;color:#065f46;margin-bottom:6px;font-weight:600;">
            ✅ Solução aplicada
          </div>
          <div style="white-space:pre-wrap;">{_escape(solucao) or 'Sem detalhes adicionais.'}</div>
        </div>

        <p>Se o problema retornar ou se você não estiver satisfeito com a solução,
        é possível reabrir o chamado no sistema.</p>
    """
    html = _BASE_TEMPLATE.format(title="Chamado finalizado", tag="Resolvido", body=body)
    return subject, html


# =====================================================================
# Templates: Cadastro aprovado + Reset de senha
# =====================================================================
def email_cadastro_aprovado(
    nome: str,
    username: str,
    grupo_nome: str | None,
    link_login: str,
) -> tuple[str, str]:
    """E-mail para o usuário quando o admin aprova o pré-cadastro.

    NÃO contém a senha (já foi definida pelo próprio usuário no primeiro
    acesso e está armazenada como hash). Apenas confirma o username e
    aponta o link de login.
    """
    subject = "Seu cadastro foi aprovado — CPE Control"
    grupo_info = (
        _info_box("Seu grupo", grupo_nome) if grupo_nome else ""
    )
    body = f"""
        <p>Olá <strong>{_escape(nome)}</strong>,</p>
        <p>Boa notícia! Seu cadastro no <strong>CPE Control</strong> foi
        <span style="color:#16A34A;font-weight:600;">aprovado pelo administrador</span>
        e você já pode entrar no sistema.</p>

        {_info_box("Seu nome de usuário (login)", username)}
        {grupo_info}

        <div style="margin:18px 0 6px;padding:14px 16px;background:#fffbeb;
                    border-left:4px solid #F59E0B;border-radius:6px;font-size:13px;">
          <strong>🔐 Sua senha</strong> é a mesma que você cadastrou no formulário de
          primeiro acesso. Por segurança, ela não é enviada por e-mail.<br>
          Esqueceu? Use o link <em>“Esqueci minha senha”</em> na tela de login.
        </div>

        <p style="text-align:center;margin:24px 0 8px;">
          <a href="{_escape(link_login)}"
             style="display:inline-block;padding:12px 28px;background:#FFC107;
                    color:#1A1A1A;font-weight:700;font-size:14px;text-decoration:none;
                    border-radius:8px;box-shadow:0 4px 12px rgba(255,193,7,.35);">
            🚀 Acessar o sistema
          </a>
        </p>

        <p style="font-size:12px;color:#6B7280;text-align:center;margin-top:8px;">
          Se o botão não funcionar, copie e cole este link no navegador:<br>
          <span style="word-break:break-all;">{_escape(link_login)}</span>
        </p>
    """
    html = _BASE_TEMPLATE.format(title="Cadastro aprovado", tag="Bem-vindo(a)", body=body)
    return subject, html


def email_reset_senha(
    nome: str,
    link_reset: str,
    ip_origem: str,
    minutos_validade: int = 60,
) -> tuple[str, str]:
    """E-mail com link pra redefinir a senha. Token válido por 1h (default).

    Inclui IP que solicitou (audit) — se não foi o próprio usuário, ele
    sabe que alguém tentou comprometer a conta.
    """
    subject = "Redefinir senha — CPE Control"
    body = f"""
        <p>Olá <strong>{_escape(nome)}</strong>,</p>
        <p>Recebemos uma solicitação para <strong>redefinir a senha</strong>
        da sua conta no <strong>CPE Control</strong>.</p>

        <p style="text-align:center;margin:24px 0 8px;">
          <a href="{_escape(link_reset)}"
             style="display:inline-block;padding:12px 28px;background:#FFC107;
                    color:#1A1A1A;font-weight:700;font-size:14px;text-decoration:none;
                    border-radius:8px;box-shadow:0 4px 12px rgba(255,193,7,.35);">
            🔑 Redefinir minha senha
          </a>
        </p>

        <p style="font-size:12px;color:#6B7280;text-align:center;margin-top:8px;">
          Se o botão não funcionar, copie e cole este link no navegador:<br>
          <span style="word-break:break-all;">{_escape(link_reset)}</span>
        </p>

        <div style="margin:20px 0 6px;padding:14px 16px;background:#fef2f2;
                    border-left:4px solid #DC2626;border-radius:6px;font-size:13px;">
          <strong>⚠️ Atenção:</strong>
          <ul style="margin:6px 0 0;padding-left:18px;color:#7f1d1d;">
            <li>O link expira em <strong>{minutos_validade} minutos</strong>.</li>
            <li>Ele só pode ser usado <strong>uma única vez</strong>.</li>
            <li>Solicitado a partir do IP: <code>{_escape(ip_origem)}</code></li>
          </ul>
        </div>

        <p style="margin-top:18px;font-size:13px;color:#374151;">
          <strong>Você NÃO solicitou esta troca?</strong> Pode ignorar este e-mail —
          sua senha atual continua válida. Se isto acontecer com frequência, avise o time
          de TI para investigar.
        </p>
    """
    html = _BASE_TEMPLATE.format(title="Redefinir senha", tag="Segurança", body=body)
    return subject, html
