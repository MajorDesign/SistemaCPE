"""
/vincular email:...        -> pede codigo pra CPEControlAPI, backend envia email
/vincular-confirmar 123456 -> confirma o codigo e cria o vinculo Discord<->CPE
/desvincular               -> remove o vinculo do proprio Discord id

Respostas sao ephemeral (so o user ve).
"""

import logging
import discord
from discord import app_commands

from api_client import link_challenge, link_verify, unlink, ApiError

logger = logging.getLogger("cpe-bot.vincular")


def register(tree: app_commands.CommandTree, guild: discord.Object) -> None:

    @tree.command(
        name="vincular",
        description="Vincula sua conta Discord ao CPE Control (envia código por email)",
        guild=guild,
    )
    @app_commands.describe(email="Seu email do CPE Control (@cpetecnologia.com.br)")
    async def vincular(inter: discord.Interaction, email: str) -> None:
        await inter.response.defer(ephemeral=True, thinking=True)
        discord_id = str(inter.user.id)

        try:
            await link_challenge(discord_id, email.strip())
        except ApiError as e:
            if e.status == 429:
                await inter.followup.send(
                    f"⏱️ {e.detail}",
                    ephemeral=True,
                )
                return
            logger.warning(f"[vincular] falha challenge did={discord_id}: {e}")
            await inter.followup.send(
                f"❌ Não consegui enviar o código. Detalhe: {e.detail}",
                ephemeral=True,
            )
            return
        except Exception as e:
            logger.error(f"[vincular] erro inesperado: {e}")
            await inter.followup.send(
                "❌ Erro ao contactar o CPE Control. Tente novamente em instantes.",
                ephemeral=True,
            )
            return

        # Resposta padrao (anti-enumeracao — nao confirma se email existe)
        await inter.followup.send(
            f"✉️ Se o email `{email}` estiver cadastrado no CPE Control, "
            f"você receberá um código de 6 dígitos em instantes.\n\n"
            f"Confirme com **`/vincular-confirmar codigo:XXXXXX`** — "
            f"o código expira em 15 minutos.",
            ephemeral=True,
        )

    @tree.command(
        name="vincular-confirmar",
        description="Confirma o código de 6 dígitos recebido por email",
        guild=guild,
    )
    @app_commands.describe(codigo="Código de 6 dígitos que chegou no seu email")
    async def vincular_confirmar(inter: discord.Interaction, codigo: str) -> None:
        await inter.response.defer(ephemeral=True, thinking=True)
        discord_id = str(inter.user.id)
        code_clean = codigo.strip().replace(" ", "")

        # Validacao local antes de gastar request pra o backend
        if not (code_clean.isdigit() and len(code_clean) == 6):
            await inter.followup.send(
                "❌ O código precisa ter exatamente 6 dígitos numéricos.",
                ephemeral=True,
            )
            return

        try:
            r = await link_verify(discord_id, code_clean)
        except ApiError as e:
            logger.info(f"[vincular-confirmar] falha did={discord_id} status={e.status}")
            emoji = "⏱️" if e.status == 429 else "❌"
            await inter.followup.send(f"{emoji} {e.detail}", ephemeral=True)
            return
        except Exception as e:
            logger.error(f"[vincular-confirmar] erro inesperado: {e}")
            await inter.followup.send(
                "❌ Erro ao contactar o CPE Control. Tente novamente em instantes.",
                ephemeral=True,
            )
            return

        user = r.get("user", {})
        logger.info(f"[vincular-confirmar] OK did={discord_id} user_id={user.get('id')}")
        await inter.followup.send(
            f"✅ Conta vinculada! Você está autenticado como **{user.get('name', '?')}** "
            f"(`{user.get('email', '?')}`).\n\n"
            f"Já pode usar **`/consultachamado numero:SUP-2026-00178`**.",
            ephemeral=True,
        )

    @tree.command(
        name="desvincular",
        description="Remove o vínculo da sua conta Discord com o CPE Control",
        guild=guild,
    )
    async def desvincular(inter: discord.Interaction) -> None:
        # Segurança: discord_id vem SEMPRE do proprio inter.user, jamais
        # de input do usuario. Discord ja autentica quem esta chamando.
        await inter.response.defer(ephemeral=True, thinking=True)
        discord_id = str(inter.user.id)

        try:
            r = await unlink(discord_id)
        except ApiError as e:
            logger.warning(f"[desvincular] falha did={discord_id}: {e}")
            await inter.followup.send(
                f"❌ Não consegui desvincular. Detalhe: {e.detail}",
                ephemeral=True,
            )
            return
        except Exception as e:
            logger.error(f"[desvincular] erro inesperado: {e}")
            await inter.followup.send(
                "❌ Erro ao contactar o CPE Control. Tente novamente em instantes.",
                ephemeral=True,
            )
            return

        if r.get("unlinked"):
            email = r.get("was_linked_to") or "?"
            logger.info(f"[desvincular] OK did={discord_id} era_vinculado_a={email}")
            await inter.followup.send(
                f"✅ Vínculo removido. Sua conta Discord não está mais ligada a "
                f"**{email}** no CPE Control.\n\n"
                f"Para vincular novamente, use **`/vincular email:seu.email@cpetecnologia.com.br`**.",
                ephemeral=True,
            )
        else:
            await inter.followup.send(
                "ℹ️ Sua conta Discord não estava vinculada a nenhum usuário CPE. "
                "Nada foi alterado.",
                ephemeral=True,
            )
