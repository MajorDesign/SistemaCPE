"""Registro central dos slash commands do bot."""

from commands import vincular, consultar, criar


def register_all(tree, guild):
    vincular.register(tree, guild)
    consultar.register(tree, guild)
    criar.register(tree, guild)
