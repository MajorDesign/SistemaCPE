"""Registro central dos slash commands do bot."""

from commands import vincular, consultar, criar, notifier


def register_all(tree, guild):
    vincular.register(tree, guild)
    consultar.register(tree, guild)
    criar.register(tree, guild)


def register_background_tasks(bot):
    """Inicia tasks nao-interativas (notifier de DMs pendentes)."""
    notifier.register(bot)
