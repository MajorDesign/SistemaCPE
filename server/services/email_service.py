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


def _get_cfg() -> dict:
    """Lê o config SMTP do ambiente a cada envio (permite hot reload sem restart)."""
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


def smtp_configurado() -> bool:
    cfg = _get_cfg()
    return bool(cfg["host"] and cfg["user"] and cfg["from_addr"])


def _enviar_sync(
    para: list[str],
    assunto: str,
    html: str,
    texto: Optional[str],
    reply_to: Optional[str],
) -> None:
    cfg = _get_cfg()
    if not smtp_configurado():
        logger.warning(
            f"[EMAIL] SMTP não configurado — assunto='{assunto}' destinatários={para} "
            f"(defina SMTP_HOST/SMTP_USER/SMTP_FROM no .env)"
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
) -> None:
    """Dispara um e-mail. Por padrão envia em background (não bloqueia o request).

    `para` pode ser uma string ou lista de strings. E-mails inválidos/vazios são
    descartados silenciosamente.
    """
    destinatarios = [e.strip() for e in ([para] if isinstance(para, str) else list(para))
                     if e and "@" in (e or "")]
    if not destinatarios:
        logger.warning(f"[EMAIL] sem destinatários válidos para assunto='{assunto}'")
        return

    if async_send:
        t = threading.Thread(
            target=_enviar_sync,
            args=(destinatarios, assunto, html, texto, reply_to),
            daemon=True,
        )
        t.start()
    else:
        _enviar_sync(destinatarios, assunto, html, texto, reply_to)


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
