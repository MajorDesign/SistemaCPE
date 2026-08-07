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


def enviar_email_bcc(
    destinatarios: Iterable[str],
    assunto: str,
    html: str,
    texto: Optional[str] = None,
    reply_to: Optional[str] = None,
    async_send: bool = True,
    perfil: str = "default",
) -> None:
    """Envia 1 unica mensagem com lista BCC (sem expor destinatarios entre si).

    Use isto para broadcasts pro grupo: 1 conexao SMTP em vez de N, evita
    rate-limit, e cada destinatario recebe sem ver os outros emails.

    Diferencas vs enviar_email com lista:
    - enviar_email([a,b,c]) -> 1 msg com To: a, b, c (todos veem todos)
    - enviar_email_bcc([a,b,c]) -> 1 msg com To: <self>, RCPT a, b, c
                                   (cada um ve so o proprio email)
    """
    lista = [e.strip() for e in destinatarios if e and "@" in (e or "")]
    if not lista:
        logger.warning(f"[EMAIL-BCC] sem destinatários válidos para assunto='{assunto}'")
        return

    if async_send:
        t = threading.Thread(
            target=_enviar_sync_bcc,
            args=(lista, assunto, html, texto, reply_to, perfil),
            daemon=True,
        )
        t.start()
    else:
        _enviar_sync_bcc(lista, assunto, html, texto, reply_to, perfil)


def _enviar_sync_bcc(
    destinatarios: list[str],
    assunto: str,
    html: str,
    texto: Optional[str],
    reply_to: Optional[str],
    perfil: str = "default",
) -> None:
    cfg = _get_cfg(perfil)
    if not smtp_configurado(perfil):
        logger.warning(
            f"[EMAIL-BCC] SMTP ({perfil}) nao configurado — assunto='{assunto}' "
            f"destinatarios={len(destinatarios)} (defina "
            f"{'AGENDA_' if perfil == 'agenda' else ''}SMTP_HOST/USER/FROM no .env)"
        )
        return

    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"]    = formataddr((cfg["from_name"], cfg["from_addr"]))
    # To: aponta pro proprio remetente; destinatarios reais vao via RCPT TO
    msg["To"]      = formataddr((cfg["from_name"], cfg["from_addr"]))
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
                # send_message com to_addrs explicito faz BCC real (RCPT TO sem expor)
                smtp.send_message(msg, from_addr=cfg["from_addr"], to_addrs=destinatarios)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as smtp:
                smtp.ehlo()
                if cfg["use_tls"]:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                if cfg["user"] and cfg["password"]:
                    smtp.login(cfg["user"], cfg["password"])
                smtp.send_message(msg, from_addr=cfg["from_addr"], to_addrs=destinatarios)
        logger.info(
            f"[EMAIL-BCC] ✅ Enviado (1 msg, {len(destinatarios)} RCPT): "
            f"assunto='{assunto}'"
        )
    except Exception as err:
        logger.error(
            f"[EMAIL-BCC] ❌ Falha ao enviar para {len(destinatarios)} destinatarios: {err}"
        )


# =====================================================================
# Templates HTML — identidade CPE Control (#FFC107 amarelo / #1A1A1A preto)
# =====================================================================

_BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><title>{title}</title></head>
<body style="margin:0;padding:0;background:#f5f5f7;font-family:Segoe UI,Roboto,Arial,sans-serif;color:#1f2937;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;background:#fff;border-radius:12px;overflow:hidden;
                    box-shadow:0 4px 18px rgba(0,0,0,0.08);">
        <tr>
          <td style="background:linear-gradient(135deg,#FFC107 0%,#FFA500 100%);
                     padding:22px 28px;color:#1A1A1A;
                     border-bottom:4px solid #1A1A1A;">
            <div style="font-size:13px;letter-spacing:.08em;text-transform:uppercase;font-weight:700;opacity:.75;">
              {tag}
            </div>
            <div style="font-size:22px;font-weight:800;margin-top:4px;line-height:1.2;">
              {title}
            </div>
          </td>
        </tr>
        <tr><td style="padding:26px 28px;font-size:14px;line-height:1.6;color:#1f2937;">
          {body}
        </td></tr>
        <tr>
          <td style="padding:16px 28px;background:#1A1A1A;
                     border-top:3px solid #FFC107;
                     font-size:12px;color:#cbd5e1;text-align:center;">
            <div style="margin-bottom:6px;">
              <span style="color:#FFC107;font-weight:700;letter-spacing:.04em;">CPE&nbsp;CONTROL</span>
              <span style="opacity:.6;"> · Sistema de Gerenciamento Inteligente</span>
            </div>
            <div style="font-size:11px;opacity:.7;">
              E-mail automático — não responda a esta mensagem.
            </div>
            <div style="margin-top:10px;padding-top:10px;border-top:1px solid #2a2a2a;
                        font-size:11px;color:#94a3b8;">
              <i>Desenvolvido por</i> <strong style="color:#FFC107;">Jonathan Lopes</strong>
            </div>
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


def email_ticket_para_grupo(
    *, ticket_numero: str, assunto: str, descricao: str,
    grupo: str, prioridade: str, solicitante_nome: str,
    destinatario_nome: str,
) -> tuple[str, str]:
    """Email broadcast pra todos do grupo quando um chamado novo (ou devolvido /
    encaminhado) entra na fila do grupo, sem responsavel atribuido ainda."""
    subject = f"[Chamado {ticket_numero}] Novo chamado aguardando atendimento"
    body = f"""
        <p>Olá <strong>{_escape(destinatario_nome)}</strong>,</p>
        <p>Há um novo chamado <strong>aguardando atendimento</strong> na fila
        do seu grupo. Qualquer pessoa do grupo pode assumi-lo no sistema.</p>

        <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
               style="border-collapse:collapse;margin:14px 0;border:1px solid #eef0f4;border-radius:8px;">
          <tbody>
            {_info_box("Nº do chamado", ticket_numero)}
            {_info_box("Assunto", assunto)}
            {_info_box("Solicitante", solicitante_nome)}
            {_info_box("Setor", grupo)}
            {_info_box("Prioridade", prioridade)}
          </tbody>
        </table>

        <div style="margin:14px 0;padding:12px 14px;background:#f9fafb;
                    border-left:4px solid #667eea;border-radius:6px;">
          <div style="font-size:12px;color:#6b7280;margin-bottom:4px;">Descrição</div>
          <div style="white-space:pre-wrap;">{_escape(descricao)}</div>
        </div>

        <p>Após alguém do grupo assumir o chamado, apenas o responsável
        receberá as atualizações seguintes.</p>
    """
    html = _BASE_TEMPLATE.format(title="Novo chamado na fila do grupo", tag="Aguardando atendimento", body=body)
    return subject, html


def email_ticket_atribuido(
    *, ticket_numero: str, assunto: str,
    destinatario_nome: str, atribuidor_nome: str, e_proprio_solicitante: bool = False,
) -> tuple[str, str]:
    """Email pro novo responsavel (ou pro solicitante avisando quem pegou)."""
    if e_proprio_solicitante:
        subject = f"[Chamado {ticket_numero}] Seu chamado foi assumido"
        titulo = "Seu chamado foi assumido"
        msg = (
            f"<p>Seu chamado <strong>{_escape(ticket_numero)}</strong> foi "
            f"assumido por <strong>{_escape(atribuidor_nome)}</strong> e já "
            f"está em atendimento.</p>"
        )
    else:
        subject = f"[Chamado {ticket_numero}] Atribuído a você"
        titulo = "Chamado atribuído a você"
        msg = (
            f"<p>O chamado <strong>{_escape(ticket_numero)}</strong> foi "
            f"atribuído a você por <strong>{_escape(atribuidor_nome)}</strong>. "
            f"A partir de agora você é o responsável e receberá todas as "
            f"atualizações deste chamado.</p>"
        )
    body = f"""
        <p>Olá <strong>{_escape(destinatario_nome)}</strong>,</p>
        {msg}
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
               style="border-collapse:collapse;margin:14px 0;border:1px solid #eef0f4;border-radius:8px;">
          <tbody>
            {_info_box("Nº do chamado", ticket_numero)}
            {_info_box("Assunto", assunto)}
          </tbody>
        </table>
    """
    html = _BASE_TEMPLATE.format(title=titulo, tag="Atribuição", body=body)
    return subject, html


def email_ticket_status_alterado(
    *, ticket_numero: str, assunto: str,
    status_anterior: str, status_novo: str,
    autor_nome: str, destinatario_nome: str,
) -> tuple[str, str]:
    """Email quando o status do ticket muda."""
    subject = f"[Chamado {ticket_numero}] Status: {status_novo}"
    body = f"""
        <p>Olá <strong>{_escape(destinatario_nome)}</strong>,</p>
        <p>O status do chamado <strong>{_escape(ticket_numero)}</strong> foi
        atualizado por <strong>{_escape(autor_nome)}</strong>.</p>

        <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
               style="border-collapse:collapse;margin:14px 0;border:1px solid #eef0f4;border-radius:8px;">
          <tbody>
            {_info_box("Nº do chamado", ticket_numero)}
            {_info_box("Assunto", assunto)}
            {_info_box("Status anterior", status_anterior)}
            {_info_box("Status atual", status_novo)}
          </tbody>
        </table>
    """
    html = _BASE_TEMPLATE.format(title="Status do chamado atualizado", tag="Atualização", body=body)
    return subject, html


def email_ticket_encaminhado(
    *, ticket_numero: str, assunto: str,
    grupo_origem: str, grupo_destino: str, motivo: str,
    autor_nome: str, destinatario_nome: str,
    e_solicitante: bool = False,
) -> tuple[str, str]:
    """Email quando o ticket é encaminhado pra outro grupo."""
    subject = f"[Chamado {ticket_numero}] Encaminhado para {grupo_destino}"
    if e_solicitante:
        msg = (
            f"<p>Seu chamado <strong>{_escape(ticket_numero)}</strong> foi "
            f"encaminhado de <strong>{_escape(grupo_origem)}</strong> para "
            f"<strong>{_escape(grupo_destino)}</strong> por "
            f"<strong>{_escape(autor_nome)}</strong>. O novo grupo dará "
            f"continuidade no atendimento.</p>"
        )
    else:
        msg = (
            f"<p>O chamado <strong>{_escape(ticket_numero)}</strong> foi "
            f"encaminhado para o seu grupo (<strong>{_escape(grupo_destino)}</strong>) "
            f"por <strong>{_escape(autor_nome)}</strong>, vindo de "
            f"<strong>{_escape(grupo_origem)}</strong>.</p>"
        )
    motivo_html = ""
    if motivo:
        motivo_html = f"""
            <div style="margin:14px 0;padding:12px 14px;background:#f9fafb;
                        border-left:4px solid #667eea;border-radius:6px;">
              <div style="font-size:12px;color:#6b7280;margin-bottom:4px;">Motivo</div>
              <div style="white-space:pre-wrap;">{_escape(motivo)}</div>
            </div>
        """
    body = f"""
        <p>Olá <strong>{_escape(destinatario_nome)}</strong>,</p>
        {msg}
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
               style="border-collapse:collapse;margin:14px 0;border:1px solid #eef0f4;border-radius:8px;">
          <tbody>
            {_info_box("Nº do chamado", ticket_numero)}
            {_info_box("Assunto", assunto)}
            {_info_box("Origem", grupo_origem)}
            {_info_box("Destino", grupo_destino)}
          </tbody>
        </table>
        {motivo_html}
    """
    html = _BASE_TEMPLATE.format(title="Chamado encaminhado", tag="Encaminhamento", body=body)
    return subject, html


def email_ticket_devolvido(
    *, ticket_numero: str, assunto: str,
    devolvedor_nome: str, motivo: str, destinatario_nome: str,
) -> tuple[str, str]:
    """Email quando o responsavel devolve o ticket pra fila do grupo."""
    subject = f"[Chamado {ticket_numero}] Voltou para a fila do grupo"
    motivo_html = ""
    if motivo:
        motivo_html = f"""
            <div style="margin:14px 0;padding:12px 14px;background:#f9fafb;
                        border-left:4px solid #f59e0b;border-radius:6px;">
              <div style="font-size:12px;color:#6b7280;margin-bottom:4px;">Motivo da devolução</div>
              <div style="white-space:pre-wrap;">{_escape(motivo)}</div>
            </div>
        """
    body = f"""
        <p>Olá <strong>{_escape(destinatario_nome)}</strong>,</p>
        <p>O chamado <strong>{_escape(ticket_numero)}</strong> foi devolvido
        para a fila do grupo por <strong>{_escape(devolvedor_nome)}</strong>.
        Qualquer pessoa do grupo pode assumi-lo novamente.</p>

        <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
               style="border-collapse:collapse;margin:14px 0;border:1px solid #eef0f4;border-radius:8px;">
          <tbody>
            {_info_box("Nº do chamado", ticket_numero)}
            {_info_box("Assunto", assunto)}
          </tbody>
        </table>
        {motivo_html}
    """
    html = _BASE_TEMPLATE.format(title="Chamado devolvido para a fila", tag="Aguardando atendimento", body=body)
    return subject, html


def email_ticket_reaberto(
    *, ticket_numero: str, assunto: str,
    solicitante_nome: str, justificativa: str, destinatario_nome: str,
    e_solicitante: bool = False,
) -> tuple[str, str]:
    """Email quando o solicitante reabre um chamado resolvido."""
    subject = f"[Chamado {ticket_numero}] Reaberto"
    if e_solicitante:
        msg = (
            f"<p>Confirmamos que você reabriu o chamado "
            f"<strong>{_escape(ticket_numero)}</strong>. Em breve um responsável "
            f"dará continuidade no atendimento.</p>"
        )
    else:
        msg = (
            f"<p>O chamado <strong>{_escape(ticket_numero)}</strong> foi reaberto "
            f"por <strong>{_escape(solicitante_nome)}</strong>. Por favor, "
            f"dê continuidade no atendimento.</p>"
        )
    body = f"""
        <p>Olá <strong>{_escape(destinatario_nome)}</strong>,</p>
        {msg}
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
               style="border-collapse:collapse;margin:14px 0;border:1px solid #eef0f4;border-radius:8px;">
          <tbody>
            {_info_box("Nº do chamado", ticket_numero)}
            {_info_box("Assunto", assunto)}
          </tbody>
        </table>
        <div style="margin:14px 0;padding:12px 14px;background:#fef2f2;
                    border-left:4px solid #DC2626;border-radius:6px;">
          <div style="font-size:12px;color:#7f1d1d;margin-bottom:4px;font-weight:600;">
            Justificativa da reabertura
          </div>
          <div style="white-space:pre-wrap;">{_escape(justificativa)}</div>
        </div>
    """
    html = _BASE_TEMPLATE.format(title="Chamado reaberto", tag="Reabertura", body=body)
    return subject, html


def email_ticket_comentario_interno(
    *, ticket_numero: str, assunto: str,
    autor_nome: str, mensagem: str, destinatario_nome: str,
) -> tuple[str, str]:
    """Email pra equipe quando alguem posta um comentario interno.
    NUNCA enviado ao solicitante (é uma nota interna entre a equipe)."""
    subject = f"[Chamado {ticket_numero}] Novo comentário interno"
    body = f"""
        <p>Olá <strong>{_escape(destinatario_nome)}</strong>,</p>
        <p><strong>{_escape(autor_nome)}</strong> postou um <strong>comentário
        interno</strong> no chamado <strong>{_escape(ticket_numero)}</strong>:</p>

        <div style="margin:14px 0;padding:14px 16px;background:#fef3c7;
                    border-left:4px solid #d97706;border-radius:6px;">
          <div style="font-size:12px;color:#92400e;margin-bottom:6px;font-weight:600;">
            🔒 Visível apenas para a equipe
          </div>
          <div style="white-space:pre-wrap;">{_escape(mensagem)}</div>
        </div>

        <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
               style="border-collapse:collapse;margin:14px 0;border:1px solid #eef0f4;border-radius:8px;">
          <tbody>
            {_info_box("Nº do chamado", ticket_numero)}
            {_info_box("Assunto", assunto)}
          </tbody>
        </table>
    """
    html = _BASE_TEMPLATE.format(title="Novo comentário interno", tag="Nota da equipe", body=body)
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


def email_precadastro_liberado(
    nome: str | None,
    email: str,
    link_login: str,
) -> tuple[str, str]:
    """E-mail pro usuário quando o admin libera a solicitação de pré-cadastro.

    Diferente de `email_cadastro_aprovado` (esse é o passo FINAL, quando o user
    já preencheu tudo e virou usuário): aqui o email só entrou na whitelist e
    o usuário ainda precisa voltar na tela de login pra completar o cadastro.
    """
    subject = "Seu e-mail foi liberado — CPE Control"
    saudacao = f"Olá <strong>{_escape(nome)}</strong>," if nome else "Olá,"
    body = f"""
        <p>{saudacao}</p>
        <p>Boa notícia! Seu e-mail <strong>{_escape(email)}</strong> foi
        <span style="color:#16A34A;font-weight:600;">liberado pelo administrador</span>
        e agora você já pode iniciar o cadastro no <strong>CPE Control</strong>.</p>

        <div style="margin:18px 0;padding:16px 18px;background:#FFFBEB;
                    border-left:4px solid #F59E0B;border-radius:6px;font-size:13.5px;">
          <div style="font-weight:700;color:#92400E;margin-bottom:10px;font-size:14px;">
            📋 Como fazer seu primeiro acesso — passo a passo
          </div>
          <ol style="margin:0;padding-left:22px;color:#1f2937;line-height:1.75;">
            <li>Clique no botão <strong>“Ir pra tela de login”</strong> abaixo.</li>
            <li>Na tela de login, clique em <strong>«Solicitar primeiro acesso»</strong>.</li>
            <li>Informe seu e-mail (o mesmo que foi liberado: <em>{_escape(email)}</em>).</li>
            <li>Preencha nome completo, CPF, unidade e escolha uma senha.</li>
            <li>Envie a solicitação — o administrador vai revisar e aprovar seu cadastro.</li>
            <li>Quando aprovado, você recebe outro e-mail confirmando e pode entrar no sistema normalmente.</li>
          </ol>
        </div>

        <p style="text-align:center;margin:24px 0 8px;">
          <a href="{_escape(link_login)}"
             style="display:inline-block;padding:12px 28px;background:#FFC107;
                    color:#1A1A1A;font-weight:700;font-size:14px;text-decoration:none;
                    border-radius:8px;box-shadow:0 4px 12px rgba(255,193,7,.35);">
            🚀 Ir pra tela de login
          </a>
        </p>

        <p style="font-size:12px;color:#6B7280;text-align:center;margin-top:8px;">
          Se o botão não funcionar, copie e cole este link no navegador:<br>
          <span style="word-break:break-all;">{_escape(link_login)}</span>
        </p>

        <div style="margin-top:18px;padding:12px 14px;background:#F3F4F6;
                    border-radius:6px;font-size:12px;color:#6B7280;">
          <strong>💡 Dica:</strong> use o mesmo e-mail liberado — se digitar outro,
          a solicitação vai ficar bloqueada de novo e você precisará pedir liberação outra vez.
        </div>
    """
    html = _BASE_TEMPLATE.format(title="Seu e-mail foi liberado", tag="Acesso liberado", body=body)
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


# =====================================================================
# FROTAS — lembretes de devolução de veículo (scheduler)
# =====================================================================

def email_lembrete_devolver_veiculo_1h(
    *, condutor_nome: str, veiculo_modelo: str, veiculo_placa: str,
    horario_fim: str, data_fim: str, checklist_id: int,
) -> tuple[str, str]:
    """1h antes do fim da reserva. Amigável, só um lembrete."""
    subject = f"Lembrete: falta 1h pra devolver o veículo {veiculo_placa}"
    body = f"""
        <p>Olá <strong>{_escape(condutor_nome)}</strong>,</p>
        <p>Sua reserva do veículo <strong>{_escape(veiculo_modelo)}</strong>
        ({_escape(veiculo_placa)}) termina em <strong>1 hora</strong>
        ({_escape(data_fim)} às {_escape(horario_fim)}).</p>

        <div style="margin:14px 0;padding:14px 16px;background:#fffbeb;
                    border-left:4px solid #f59e0b;border-radius:6px;font-size:13px;">
          <strong>📋 Não esqueça:</strong> ao chegar, procure o
          <strong>responsável de Frotas</strong> pra fazer a
          <strong>vistoria de retorno</strong>. Sem essa vistoria o veículo
          fica bloqueado pra próxima reserva.
        </div>

        <p style="font-size:12px;color:#6B7280;">
          Checklist da viagem: <code>#{checklist_id}</code>
        </p>
    """
    html = _BASE_TEMPLATE.format(title="Reserva termina em 1 hora", tag="Lembrete", body=body)
    return subject, html


def email_devolver_veiculo_vencido(
    *, condutor_nome: str, veiculo_modelo: str, veiculo_placa: str,
    horario_fim: str, data_fim: str, checklist_id: int,
    horas_atraso: int,
) -> tuple[str, str]:
    """No horário do fim (0h atraso) OU reforço a cada 3h. Tom mais firme."""
    if horas_atraso == 0:
        subject = f"⏰ Devolução vencida: veículo {veiculo_placa}"
        titulo_email = "Sua reserva venceu agora"
        alerta_texto = (
            "Sua reserva acabou de vencer. Por favor, devolva o veículo "
            "e procure o responsável de Frotas pra vistoria de retorno."
        )
    else:
        subject = f"⚠️ Atraso de {horas_atraso}h — devolver {veiculo_placa}"
        titulo_email = f"Devolução atrasada há {horas_atraso}h"
        alerta_texto = (
            f"Sua reserva venceu há <strong>{horas_atraso} hora(s)</strong> "
            "e o veículo ainda não foi devolvido. Enquanto isso, você não "
            "consegue reservar outro veículo, e o carro fica bloqueado "
            "pra outras pessoas."
        )
    body = f"""
        <p>Olá <strong>{_escape(condutor_nome)}</strong>,</p>
        <p>{alerta_texto}</p>

        <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
               style="border-collapse:collapse;margin:14px 0;border:1px solid #eef0f4;border-radius:8px;">
          <tbody>
            {_info_box("Veículo", f"{veiculo_modelo} ({veiculo_placa})")}
            {_info_box("Reserva venceu em", f"{data_fim} às {horario_fim}")}
            {_info_box("Checklist", f"#{checklist_id}")}
          </tbody>
        </table>

        <div style="margin:14px 0;padding:14px 16px;background:#fef2f2;
                    border-left:4px solid #dc2626;border-radius:6px;font-size:13px;">
          <strong>⚠️ Ação obrigatória:</strong> devolva o veículo e chame
          o responsável de Frotas pra fazer a <strong>vistoria de retorno</strong>.
          Sem isso, o carro fica bloqueado pra qualquer nova reserva.
        </div>
    """
    tag = "Devolução vencida" if horas_atraso == 0 else "Atrasado"
    html = _BASE_TEMPLATE.format(title=titulo_email, tag=tag, body=body)
    return subject, html


def email_escalada_atraso_veiculo(
    *, destinatario_nome: str, condutor_nome: str,
    veiculo_modelo: str, veiculo_placa: str,
    data_fim: str, horario_fim: str,
    checklist_id: int, horas_atraso: int,
) -> tuple[str, str]:
    """Escalada pro RESPONSAVEL_GRUPO de Frotas após 6h de atraso.
    Objetivo: dar visibilidade pro dono do processo."""
    subject = f"🚨 Frotas: veículo {veiculo_placa} atrasado há {horas_atraso}h"
    body = f"""
        <p>Olá <strong>{_escape(destinatario_nome)}</strong>,</p>
        <p>Este é um alerta automático da equipe de Frotas.</p>
        <p>O condutor <strong>{_escape(condutor_nome)}</strong> não devolveu o
        veículo <strong>{_escape(veiculo_modelo)}</strong> ({_escape(veiculo_placa)}),
        cuja reserva venceu há <strong>{horas_atraso} hora(s)</strong>.
        Já enviamos lembretes automáticos pro condutor, mas o veículo
        continua sem devolução/vistoria.</p>

        <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
               style="border-collapse:collapse;margin:14px 0;border:1px solid #eef0f4;border-radius:8px;">
          <tbody>
            {_info_box("Veículo", f"{veiculo_modelo} ({veiculo_placa})")}
            {_info_box("Condutor", condutor_nome)}
            {_info_box("Vencimento", f"{data_fim} às {horario_fim}")}
            {_info_box("Horas de atraso", str(horas_atraso))}
            {_info_box("Checklist", f"#{checklist_id}")}
          </tbody>
        </table>

        <div style="margin:14px 0;padding:14px 16px;background:#fef2f2;
                    border-left:4px solid #dc2626;border-radius:6px;font-size:13px;">
          <strong>📞 Sugestões:</strong>
          <ul style="margin:6px 0 0;padding-left:18px;color:#7f1d1d;">
            <li>Ligar/mensagem pro condutor</li>
            <li>Se necessário, forçar vistoria pelo sistema (Frotas → botão "Forçar vistoria")</li>
            <li>Registrar o incidente pra próximas reservas</li>
          </ul>
        </div>
    """
    html = _BASE_TEMPLATE.format(
        title=f"Veículo atrasado há {horas_atraso}h",
        tag="Escalada Frotas",
        body=body,
    )
    return subject, html


# ============================================================
# Reserva cancelada por falta de aprovacao (2026-07-16)
# ============================================================

def email_reserva_expirada_condutor(
    *, condutor_nome: str, veiculo_modelo: str, veiculo_placa: str,
    destino: str, data_reserva: str, horario_inicio: str,
    resp_frotas_nome: str,
) -> tuple[str, str]:
    """Email pro CONDUTOR quando reserva foi cancelada por falta de aprovacao."""
    subject = f"Reserva não confirmada — {veiculo_placa}"
    body = f"""
        <p>Olá <strong>{_escape(condutor_nome)}</strong>,</p>
        <p>Sua reserva foi <strong>cancelada automaticamente</strong> porque
        não recebeu confirmação a tempo do responsável de Frotas
        (<strong>{_escape(resp_frotas_nome)}</strong>).</p>

        <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
               style="border-collapse:collapse;margin:14px 0;border:1px solid #eef0f4;border-radius:8px;">
          <tbody>
            {_info_box("Veículo", f"{veiculo_modelo} ({veiculo_placa})")}
            {_info_box("Destino", destino or "—")}
            {_info_box("Hora prevista de saída", f"{data_reserva} às {horario_inicio}")}
            {_info_box("Responsável que deveria aprovar", resp_frotas_nome)}
          </tbody>
        </table>

        <div style="margin:14px 0;padding:14px 16px;background:#eff6ff;
                    border-left:4px solid #3b82f6;border-radius:6px;font-size:13px;">
          <strong>O que fazer:</strong> se ainda precisa do veículo, faça uma
          <strong>nova reserva</strong> no sistema. Se possível, avise o
          responsável de Frotas antes pra ele acompanhar a aprovação.
        </div>
    """
    html = _BASE_TEMPLATE.format(
        title="Reserva não confirmada",
        tag="Reserva cancelada",
        body=body,
    )
    return subject, html


def email_reserva_expirada_responsavel(
    *, resp_frotas_nome: str, condutor_nome: str,
    veiculo_modelo: str, veiculo_placa: str,
    destino: str, data_reserva: str, horario_inicio: str,
    minutos_atraso: int,
) -> tuple[str, str]:
    """Email pro RESPONSAVEL FROTAS avisando que a reserva foi cancelada por falta de aprovacao dele."""
    subject = f"Você não aprovou a tempo — reserva de {veiculo_placa}"
    body = f"""
        <p>Olá <strong>{_escape(resp_frotas_nome)}</strong>,</p>
        <p>Uma reserva do condutor <strong>{_escape(condutor_nome)}</strong>
        foi <strong>cancelada automaticamente</strong> porque não recebeu
        aprovação até o horário de saída
        (atraso: <strong>{minutos_atraso} min</strong>).</p>

        <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
               style="border-collapse:collapse;margin:14px 0;border:1px solid #eef0f4;border-radius:8px;">
          <tbody>
            {_info_box("Condutor", condutor_nome)}
            {_info_box("Veículo", f"{veiculo_modelo} ({veiculo_placa})")}
            {_info_box("Destino", destino or "—")}
            {_info_box("Hora prevista de saída", f"{data_reserva} às {horario_inicio}")}
          </tbody>
        </table>

        <div style="margin:14px 0;padding:14px 16px;background:#fef9c3;
                    border-left:4px solid #f59e0b;border-radius:6px;font-size:13px;">
          <strong>💡 Dica:</strong> notificações de reservas pendentes ficam
          no topo do sistema. Se o condutor precisar do veículo, ele pode
          fazer uma nova reserva — mas agora depende de você aprovar a tempo.
        </div>
    """
    html = _BASE_TEMPLATE.format(
        title="Reserva expirou sem sua aprovação",
        tag="Ação perdida",
        body=body,
    )
    return subject, html
