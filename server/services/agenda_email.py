"""
Notificacao por email da Agenda v2.

Gera .ics em conformidade com RFC 5545 (METHOD:REQUEST / CANCEL) e envia
como anexo junto ao HTML do convite. Cliente do usuario externo (Outlook/
Gmail/Apple Calendar) consegue importar 1-clique.

Nao mexe no email_service.py existente — reutiliza SMTP config do .env.
"""
from __future__ import annotations

import io
import logging
import smtplib
import ssl
import threading
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Optional

from services.email_service import _get_cfg, smtp_configurado, _make_ssl_context

logger = logging.getLogger(__name__)


PUBLIC_BASE_URL_DEFAULT = "https://cpecontrol.cpetecnologia.com.br"


# ---------------------------------------------------------------------
# ICS builder (RFC 5545 minimalista)
# ---------------------------------------------------------------------
def _dt_ics(d) -> str:
    """DATETIME BR naive -> string YYYYMMDDTHHMMSS (float time, sem TZ).
    Manter horario local BR e nao anexar tzinfo — clientes tratam como
    'local do usuario' que abre. Para preserva TZ certo, ver TZID depois."""
    if isinstance(d, str):
        d = datetime.fromisoformat(d.replace(" ", "T").replace("Z", ""))
    return d.strftime("%Y%m%dT%H%M%S")


def _escape_ics(s: Optional[str]) -> str:
    if s is None:
        return ""
    # RFC 5545 §3.3.11
    return (s
            .replace("\\", "\\\\")
            .replace(";", "\\;")
            .replace(",", "\\,")
            .replace("\n", "\\n")
            .replace("\r", ""))


def gerar_ics(
    *,
    uid: str,
    titulo: str,
    descricao: Optional[str],
    local: Optional[str],
    inicio,
    fim,
    organizador_email: str,
    organizador_nome: Optional[str],
    participante_email: Optional[str],
    method: str = "REQUEST",   # REQUEST | CANCEL | PUBLISH
    seq: int = 0,
    url: Optional[str] = None,
) -> bytes:
    """Retorna .ics como bytes (utf-8). Um unico VEVENT."""
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//CPE Control//Agenda v2//PT-BR",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        f"METHOD:{method}",
        "BEGIN:VEVENT",
        f"UID:{_escape_ics(uid)}",
        f"DTSTAMP:{now}",
        f"SEQUENCE:{seq}",
        f"DTSTART;TZID=America/Sao_Paulo:{_dt_ics(inicio)}",
        f"DTEND;TZID=America/Sao_Paulo:{_dt_ics(fim)}",
        f"SUMMARY:{_escape_ics(titulo)}",
    ]
    if descricao:
        lines.append(f"DESCRIPTION:{_escape_ics(descricao)}")
    if local:
        lines.append(f"LOCATION:{_escape_ics(local)}")
    if url:
        lines.append(f"URL:{_escape_ics(url)}")
    lines.append(
        f"ORGANIZER;CN={_escape_ics(organizador_nome or '')}:mailto:{organizador_email}"
    )
    if participante_email:
        lines.append(
            f"ATTENDEE;CN={_escape_ics(participante_email)};ROLE=REQ-PARTICIPANT;"
            f"PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:{participante_email}"
        )
    status_map = {"REQUEST": "CONFIRMED", "CANCEL": "CANCELLED", "PUBLISH": "CONFIRMED"}
    lines.append(f"STATUS:{status_map.get(method, 'CONFIRMED')}")
    lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")


# ---------------------------------------------------------------------
# Email compose + send
# ---------------------------------------------------------------------
def _rsvp_url(base_url: str, token: str) -> str:
    return f"{base_url.rstrip('/')}/SistemaCPE/web/rsvp/index.html?token={token}"


def _html_convite(*, titulo: str, host_nome: str, inicio_txt: str, local: Optional[str],
                  descricao: Optional[str], rsvp_url_full: Optional[str],
                  is_cancel: bool = False, motivo: Optional[str] = None) -> str:
    if is_cancel:
        cabec = f"❌ <strong>Reunião cancelada:</strong> {titulo}"
        cta = ""
    else:
        cabec = f"📅 Convite: <strong>{titulo}</strong>"
        cta = ""
        if rsvp_url_full:
            cta = f"""
              <div style="margin:20px 0;">
                <a href="{rsvp_url_full}&amp;resposta=aceito"
                   style="display:inline-block;padding:10px 16px;background:#16a34a;color:#fff;
                          text-decoration:none;border-radius:6px;font-weight:600;margin-right:6px">
                  ✓ Aceitar
                </a>
                <a href="{rsvp_url_full}&amp;resposta=talvez"
                   style="display:inline-block;padding:10px 16px;background:#d97706;color:#fff;
                          text-decoration:none;border-radius:6px;font-weight:600;margin-right:6px">
                  ? Talvez
                </a>
                <a href="{rsvp_url_full}&amp;resposta=recusado"
                   style="display:inline-block;padding:10px 16px;background:#dc2626;color:#fff;
                          text-decoration:none;border-radius:6px;font-weight:600">
                  ✗ Recusar
                </a>
              </div>
              <p style="font-size:12px;color:#666">
                Ou <a href="{rsvp_url_full}">clique aqui</a> pra responder no navegador.
              </p>
            """

    motivo_html = ""
    if motivo:
        motivo_html = (f"<p><strong>Motivo:</strong> "
                       f"{motivo}</p>")

    local_html = f"<p><strong>Local:</strong> {local}</p>" if local else ""
    desc_html = f"<div style='background:#f5f5f5;padding:10px;border-radius:6px'>{descricao}</div>" if descricao else ""

    return f"""<!doctype html>
<html><body style="font-family:Segoe UI,Arial,sans-serif;color:#111;line-height:1.5">
  <div style="max-width:600px;margin:20px auto;padding:20px;
              border:1px solid #e5e7eb;border-radius:10px;background:#fff">
    <div style="font-size:18px;font-weight:600;margin-bottom:8px">{cabec}</div>
    <p>Organizador: <strong>{host_nome}</strong></p>
    <p><strong>Quando:</strong> {inicio_txt}</p>
    {local_html}
    {desc_html}
    {motivo_html}
    {cta}
    <hr style="border:none;border-top:1px solid #eee;margin:20px 0">
    <p style="font-size:11px;color:#888">
      Este evento veio da agenda do CPE Control. Um arquivo .ics vai anexo —
      abra pra adicionar ao seu calendário (Outlook, Gmail, Apple Calendar).
    </p>
  </div>
</body></html>"""


def enviar_convite_agenda(
    *,
    dest_email: str,
    dest_nome: Optional[str],
    titulo: str,
    host_nome: str,
    host_email: str,
    inicio,
    fim,
    local: Optional[str],
    descricao: Optional[str],
    ics_uid: str,
    rsvp_token: Optional[str] = None,      # so pra externo
    base_url: str = PUBLIC_BASE_URL_DEFAULT,
    method: str = "REQUEST",
    seq: int = 0,
    motivo: Optional[str] = None,          # so em CANCEL
    async_send: bool = True,
) -> None:
    """Envia email de convite/cancelamento/atualizacao com .ics anexo."""
    from services.email_service import _get_cfg
    cfg = _get_cfg("default")
    if not smtp_configurado("default"):
        logger.warning(f"[AGENDA-EMAIL] SMTP nao configurado — pulando envio para {dest_email}")
        return

    is_cancel = method == "CANCEL"
    inicio_txt = _formatar_dt_br(inicio) + (
        f" — {_formatar_dt_br(fim)}" if not is_cancel else ""
    )
    rsvp_url_full = _rsvp_url(base_url, rsvp_token) if rsvp_token and not is_cancel else None
    html = _html_convite(
        titulo=titulo, host_nome=host_nome, inicio_txt=inicio_txt, local=local,
        descricao=descricao, rsvp_url_full=rsvp_url_full,
        is_cancel=is_cancel, motivo=motivo,
    )
    assunto = (
        f"❌ Reunião cancelada: {titulo}"
        if is_cancel
        else f"📅 Convite: {titulo} — {inicio_txt}"
    )

    ics_bytes = gerar_ics(
        uid=ics_uid, titulo=titulo, descricao=descricao, local=local,
        inicio=inicio, fim=fim,
        organizador_email=host_email, organizador_nome=host_nome,
        participante_email=dest_email,
        method=method, seq=seq,
        url=rsvp_url_full,
    )

    def _do_send():
        msg = EmailMessage()
        msg["Subject"] = assunto
        msg["From"]    = formataddr((cfg["from_name"], cfg["from_addr"]))
        msg["To"]      = dest_email
        msg["Message-ID"] = make_msgid(domain=cfg["from_addr"].split("@", 1)[-1] or "cpe")

        msg.set_content(f"Convite para: {titulo}\nQuando: {inicio_txt}\n")
        msg.add_alternative(html, subtype="html")

        # anexo .ics — 2 formas garantem que os clientes reconheçam:
        # 1) parte 'text/calendar; method=X' (in-line, pra Gmail/Outlook Web)
        # 2) parte 'application/ics; name=invite.ics' (attachment, fallback)
        msg.add_attachment(
            ics_bytes,
            maintype="text",
            subtype="calendar",
            filename="invite.ics",
            params={"method": method, "charset": "utf-8", "name": "invite.ics"},
        )

        try:
            if cfg["use_ssl"]:
                with smtplib.SMTP_SSL(cfg["host"], cfg["port"],
                                      context=_make_ssl_context(), timeout=30) as smtp:
                    smtp.login(cfg["user"], cfg["password"])
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as smtp:
                    smtp.ehlo()
                    if cfg["use_tls"]:
                        smtp.starttls(context=_make_ssl_context())
                        smtp.ehlo()
                    if cfg["user"] and cfg["password"]:
                        smtp.login(cfg["user"], cfg["password"])
                    smtp.send_message(msg)
            logger.info(f"[AGENDA-EMAIL] ✅ {method} enviado → {dest_email}")
        except Exception as e:
            logger.error(f"[AGENDA-EMAIL] ❌ Falha {method} para {dest_email}: {e}")

    if async_send:
        threading.Thread(target=_do_send, daemon=True).start()
    else:
        _do_send()


def _formatar_dt_br(d) -> str:
    if isinstance(d, str):
        d = datetime.fromisoformat(d.replace(" ", "T").replace("Z", ""))
    return d.strftime("%d/%m/%Y %H:%M")
