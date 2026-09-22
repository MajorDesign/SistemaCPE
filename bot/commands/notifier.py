"""
Task loop que polla /api/discord/notifications/pending a cada 15s e envia
DM pros users vinculados quando responsavel responde/atribui/finaliza um
chamado deles.

Diferente dos outros commands, este modulo nao registra slash commands —
so agenda uma tasks.loop no bot. discord_bot.py chama register(bot) no
setup_hook.

Handler de erro: se DM falhar (Forbidden = user bloqueou bot, DMs desligados
pra membros do servidor), marca a notificacao como delivered com error setado
pra o backend NAO retentar (evita ficar spammando o log).
"""

import logging
from typing import Optional
import discord
from discord.ext import tasks

from api_client import (
    list_pending_notifications, mark_notifications_delivered, ApiError,
)

logger = logging.getLogger("cpe-bot.notifier")

POLL_INTERVAL_SECONDS = 15
BATCH_LIMIT           = 50
TICKET_URL_BASE = "https://cpecontrol.cpetecnologia.com.br/SistemaCPE/web/pages/tickets.html"

# Alinhado com tickets.js:1263 e TicketCardDetail.tsx STATUS_STYLE (cores)
STATUS_LABELS = {
    1: "Aberto",
    2: "Em andamento",
    3: "Aguardando",
    4: "Resolvido",
    5: "Fechado",
}

# (emoji, cor, titulo) por event_type
EVENT_META = {
    "resposta":         ("💬", 0x3B82F6, "Nova resposta no seu chamado"),
    "atribuido":        ("👤", 0xF59E0B, "Chamado atribuído"),
    "status_changed":   ("🔄", 0x8B5CF6, "Status do chamado mudou"),
    "ticket_resolvido": ("✅", 0x10B981, "Chamado resolvido — avalie!"),
}


def register(bot: discord.Client) -> None:
    """Inicia o task loop. Chamado do setup_hook do bot."""
    _push_notifier.start(bot)


@tasks.loop(seconds=POLL_INTERVAL_SECONDS)
async def _push_notifier(bot: discord.Client) -> None:
    try:
        pending = await list_pending_notifications(limit=BATCH_LIMIT)
    except ApiError as e:
        logger.warning(f"[notifier] pending falhou: {e}")
        return
    except Exception as e:
        logger.warning(f"[notifier] erro inesperado no fetch: {e}")
        return

    if not pending:
        return

    logger.info(f"[notifier] processando {len(pending)} notificacao(oes)")
    delivered_ids: list = []
    # Agrupa por mensagem de erro pra chamar mark-delivered uma vez por erro
    failed_by_error: dict = {}

    for notif in pending:
        did = str(notif.get("discord_id") or "")
        if not did:
            failed_by_error.setdefault("MISSING_DISCORD_ID", []).append(notif["id"])
            continue
        try:
            user = await bot.fetch_user(int(did))
        except discord.NotFound:
            failed_by_error.setdefault("DISCORD_USER_NOT_FOUND", []).append(notif["id"])
            continue
        except Exception as e:
            failed_by_error.setdefault(f"FETCH_USER: {str(e)[:80]}", []).append(notif["id"])
            continue

        try:
            embed, view = _build_notification(notif)
            await user.send(embed=embed, view=view)
            delivered_ids.append(notif["id"])
        except discord.Forbidden:
            # User bloqueou bot ou desabilitou DMs pra membros do servidor
            failed_by_error.setdefault("DM_FORBIDDEN", []).append(notif["id"])
            logger.info(f"[notifier] DM forbidden did={did} (user bloqueou/DMs off)")
        except Exception as e:
            failed_by_error.setdefault(f"SEND: {str(e)[:80]}", []).append(notif["id"])
            logger.warning(f"[notifier] falha DM did={did}: {e}")

    # Marca sucessos
    if delivered_ids:
        try:
            await mark_notifications_delivered(delivered_ids)
            logger.info(f"[notifier] {len(delivered_ids)} DMs entregues")
        except Exception as e:
            logger.warning(f"[notifier] mark-delivered(sucesso) falhou: {e}")

    # Marca falhas por grupo de erro
    for err, ids in failed_by_error.items():
        try:
            await mark_notifications_delivered(ids, error=err)
            logger.info(f"[notifier] {len(ids)} marcadas com erro='{err}'")
        except Exception as e:
            logger.warning(f"[notifier] mark-delivered(erro) falhou: {e}")


@_push_notifier.before_loop
async def _before_loop():
    logger.info(f"[notifier] task loop iniciando — poll a cada {POLL_INTERVAL_SECONDS}s")


def _build_notification(notif: dict) -> tuple:
    """(embed, view) baseado no event_type + payload."""
    et = notif.get("event_type") or "?"
    emoji, color, titulo = EVENT_META.get(et, ("📢", 0x808080, "Atualização"))
    payload = notif.get("payload") or {}

    numero  = notif.get("numero") or notif.get("id_alfanumerica") or f"#{notif.get('ticket_id')}"
    assunto = notif.get("assunto") or "(sem título)"

    embed = discord.Embed(
        title=f"{emoji} {titulo}",
        description=f"**{numero}** · {assunto}",
        color=color,
    )

    if et == "resposta":
        autor = payload.get("autor_nome") or "Alguém"
        msg = (payload.get("mensagem") or "").strip()
        if len(msg) > 500:
            msg = msg[:500] + "…"
        embed.add_field(
            name=f"{autor} respondeu:",
            value=msg or "*(mensagem vazia)*",
            inline=False,
        )
    elif et == "atribuido":
        resp = payload.get("responsavel_nome") or f"Usuário #{payload.get('responsavel_id')}"
        embed.add_field(name="Responsável agora", value=resp, inline=True)
    elif et == "status_changed":
        novo = STATUS_LABELS.get(payload.get("status_id_novo"), "?")
        embed.add_field(name="Novo status", value=novo, inline=True)
    elif et == "ticket_resolvido":
        finalizador = payload.get("finalizador_nome") or "Suporte"
        embed.add_field(name="Finalizado por", value=finalizador, inline=True)
        solucao = (payload.get("solucao") or "").strip()
        if solucao:
            if len(solucao) > 500:
                solucao = solucao[:500] + "…"
            embed.add_field(name="Solução aplicada", value=solucao, inline=False)
        embed.add_field(
            name="⭐ Sua avaliação",
            value="Abra no navegador pra avaliar o atendimento — feche o ciclo!",
            inline=False,
        )

    embed.set_footer(text="CPE Control · abra no navegador pra ver detalhes")

    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        label="Abrir no navegador",
        style=discord.ButtonStyle.link,
        url=f"{TICKET_URL_BASE}?ticket_id={notif.get('ticket_id')}",
    ))
    return embed, view
