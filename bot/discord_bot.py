"""
CPE Control Bot — bot Discord com slash commands que conversam com a
CPEControlAPI pra vincular conta e consultar chamados.

Rodar manualmente (dev):
    E:\\xampp\\htdocs\\SistemaCPE\\server\\.venv\\Scripts\\python.exe discord_bot.py

Rodar em produção (NSSM): ver README.md.
"""

import os
import sys
import logging

# Precisa antes dos imports do pacote `commands`
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import discord
from discord import app_commands


# ─── Config ───────────────────────────────────────────────────────
TOKEN    = os.environ.get("DISCORD_BOT_TOKEN", "")
GUILD_ID = os.environ.get("DISCORD_GUILD_ID", "")
API_BASE = os.environ.get("CPE_API_BASE", "http://127.0.0.1:8000")

if not TOKEN:
    print("[BOT] ERRO: DISCORD_BOT_TOKEN nao configurado em .env", file=sys.stderr)
    sys.exit(1)
if not GUILD_ID or not GUILD_ID.isdigit():
    print("[BOT] ERRO: DISCORD_GUILD_ID nao configurado ou invalido", file=sys.stderr)
    sys.exit(1)
GUILD_ID = int(GUILD_ID)

# ─── Logging ──────────────────────────────────────────────────────
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(logs_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        # Segundo handler pra arquivo (rotate simples via NSSM)
    ],
)
# Reduz ruido do discord.py (voice, gateway heartbeat, etc)
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("discord.http").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)

logger = logging.getLogger("cpe-bot")


# ─── Bot ──────────────────────────────────────────────────────────
class CPEControlBot(discord.Client):
    def __init__(self):
        # Slash commands nao precisam de intents privilegiados
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Registra commands scoped ao guild da CPE (propaga instantaneamente
        # ao contrario do sync global que leva ate 1h)
        guild = discord.Object(id=GUILD_ID)
        from commands import register_all, register_background_tasks
        register_all(self.tree, guild)
        synced = await self.tree.sync(guild=guild)
        logger.info(f"[BOT] {len(synced)} slash commands sincronizados pra guild {GUILD_ID}")
        # Task loop de notificacoes push (polling backend a cada 15s)
        register_background_tasks(self)
        logger.info("[BOT] tasks de background iniciadas (notifier)")


bot = CPEControlBot()


@bot.event
async def on_ready():
    logger.info(f"[BOT] logado como {bot.user} (id={bot.user.id})")
    logger.info(f"[BOT] servindo {len(bot.guilds)} guild(s) — API: {API_BASE}")


@bot.event
async def on_error(event, *args, **kwargs):
    logger.exception(f"[BOT] erro nao tratado em evento={event}")


if __name__ == "__main__":
    try:
        bot.run(TOKEN, log_handler=None)  # nosso logging.basicConfig ja cuida
    except discord.LoginFailure:
        logger.error("[BOT] token invalido — resetar no Developer Portal e atualizar .env")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("[BOT] interrompido pelo user (Ctrl+C)")
