"""
/consultachamado numero:SUP-2026-00178 -> embed com status + ultima resposta

Fluxo:
  1. GET /api/discord/link/{did}       — descobre o CPE user vinculado
  2. POST /api/discord/link/{did}/session — session token pra agir como ele
  3. GET /api/tickets/by-numero/{n}    — dados do ticket (respeita permissao)
  4. GET /api/ticket-interacoes/{id}   — historico pra pegar ultima publica
  5. Monta embed rico + botao "Abrir no navegador"
"""

import logging
from datetime import datetime
from typing import Optional
import discord
from discord import app_commands

from api_client import (
    get_link, get_session, get_ticket_by_numero, list_interacoes, ApiError,
)

logger = logging.getLogger("cpe-bot.consultar")

# Cores alinhadas com o card do desktop (TicketCardDetail.tsx STATUS_STYLE)
STATUS_META = {
    1: ("Aberto",       0xEF4444),
    2: ("Em andamento", 0xF59E0B),
    3: ("Aguardando",   0x8B5CF6),
    4: ("Resolvido",    0x10B981),
    5: ("Fechado",      0x6B7280),
}

TICKET_URL_BASE = "https://cpecontrol.cpetecnologia.com.br/SistemaCPE/web/pages/tickets.html"


def _fmt_relative(iso: str) -> str:
    """Tempo relativo curto em pt-BR ('agora', 'há 5min', 'há 2h', '05/09/2026')."""
    if not iso:
        return "?"
    try:
        then = datetime.fromisoformat(iso.replace(" ", "T"))
    except Exception:
        return iso
    diff = (datetime.now() - then).total_seconds()
    if diff < 60:
        return "agora"
    if diff < 3600:
        return f"há {int(diff // 60)}min"
    if diff < 86400:
        return f"há {int(diff // 3600)}h"
    d = int(diff // 86400)
    if d < 7:
        return f"há {d}d"
    return then.strftime("%d/%m/%Y")


def register(tree: app_commands.CommandTree, guild: discord.Object) -> None:

    @tree.command(
        name="consultachamado",
        description="Consulta status + última resposta de um chamado",
        guild=guild,
    )
    @app_commands.describe(numero="Número do chamado (ex: SUP-2026-00178)")
    async def consultachamado(inter: discord.Interaction, numero: str) -> None:
        await inter.response.defer(ephemeral=True, thinking=True)
        discord_id = str(inter.user.id)
        numero_norm = numero.strip().upper()

        # ── 1. Verifica se user esta vinculado ──
        try:
            link = await get_link(discord_id)
        except ApiError as e:
            if e.status == 404:
                await inter.followup.send(
                    "🔗 Você ainda não vinculou sua conta.\n"
                    "Use **`/vincular email:seu.email@cpetecnologia.com.br`** primeiro.",
                    ephemeral=True,
                )
                return
            await _erro_generico(inter, e, "consultar vínculo")
            return

        # ── 2. Pega session token ──
        try:
            sess = await get_session(discord_id)
        except ApiError as e:
            await _erro_generico(inter, e, "emitir sessão")
            return

        token = sess["token"]
        cpe_user_id = sess["user_id"]

        # ── 3. Busca ticket ──
        try:
            ticket = await get_ticket_by_numero(numero_norm, token, cpe_user_id)
        except ApiError as e:
            if e.status == 404:
                await inter.followup.send(
                    f"🔍 Chamado `{numero_norm}` não encontrado.",
                    ephemeral=True,
                )
                return
            if e.status == 403:
                await inter.followup.send(
                    f"🚫 Você não tem permissão pra ver `{numero_norm}`.",
                    ephemeral=True,
                )
                return
            await _erro_generico(inter, e, "buscar chamado")
            return

        # ── 4. Ultima resposta (best-effort — se falhar, mostra sem) ──
        ultima: Optional[dict] = None
        try:
            interacoes = await list_interacoes(ticket["id"], token)
            for i in reversed(interacoes):
                if i.get("tipo") != "sistema" and i.get("publico") == 1:
                    ultima = i
                    break
        except Exception as e:
            logger.warning(f"[consultar] falha lista interacoes ticket={ticket['id']}: {e}")

        # ── 5. Monta embed ──
        embed = _build_ticket_embed(ticket, ultima, link.get("name"))

        # Botao "abrir no navegador" (via UI View)
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Abrir no navegador",
            style=discord.ButtonStyle.link,
            url=f"{TICKET_URL_BASE}?open={ticket['id']}",
        ))

        await inter.followup.send(embed=embed, view=view, ephemeral=True)


def _build_ticket_embed(ticket: dict, ultima: Optional[dict], vinculado_como: Optional[str]) -> discord.Embed:
    status_label, color = STATUS_META.get(ticket.get("status_id", 0), ("?", 0x808080))
    numero_exib = ticket.get("numero") or ticket.get("id_alfanumerica") or f"#{ticket['id']}"

    embed = discord.Embed(
        title=f"{numero_exib}",
        description=f"**{ticket.get('assunto', '(sem título)')}**",
        color=color,
    )

    embed.add_field(name="Status", value=status_label, inline=True)
    embed.add_field(
        name="Responsável",
        value=ticket.get("responsavel_nome") or "*Sem responsável*",
        inline=True,
    )

    # Setor / categoria / subcategoria numa linha só
    setor_partes = []
    if ticket.get("group_name"):
        setor_partes.append(ticket["group_name"])
    if ticket.get("categoria_nome"):
        cat = ticket["categoria_nome"]
        if ticket.get("subcategoria_nome"):
            cat += f" › {ticket['subcategoria_nome']}"
        setor_partes.append(cat)
    if setor_partes:
        embed.add_field(name="Setor", value=" · ".join(setor_partes), inline=False)

    # Ultima resposta como field grande
    if ultima:
        autor = ultima.get("usuario_nome") or f"Usuário #{ultima.get('usuario_id')}"
        quando = _fmt_relative(ultima.get("created_at", ""))
        preview = (ultima.get("mensagem") or "").strip()
        if len(preview) > 800:
            preview = preview[:800] + "…"
        if not preview:
            preview = "*(mensagem vazia)*"
        embed.add_field(
            name=f"💬 Última resposta ({quando} · {autor})",
            value=preview,
            inline=False,
        )
    else:
        embed.add_field(
            name="💬 Última resposta",
            value="*Sem respostas ainda neste chamado.*",
            inline=False,
        )

    if vinculado_como:
        embed.set_footer(text=f"Vinculado como {vinculado_como}")

    return embed


async def _erro_generico(inter: discord.Interaction, e: ApiError, contexto: str) -> None:
    logger.warning(f"[consultar] {contexto} falhou status={e.status} detail={e.detail}")
    emoji = "⏱️" if e.status == 429 else "❌"
    await inter.followup.send(
        f"{emoji} Erro ao {contexto}: {e.detail}",
        ephemeral=True,
    )
