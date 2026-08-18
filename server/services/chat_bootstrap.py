"""
chat_bootstrap.py — helpers idempotentes de sincronizacao entre cpe_plus
(users, grupos) e cpe_chat (server 'CPE TECNOLOGIA', canais por grupo,
membros).

Usado por:
  1. Script tools/sync_chat_grupos.py (execucao one-shot retroativa)
  2. Hooks em routes/users.py (create/update) e routes/groups.py + app.py
     (create) pra manter em sincronia daqui pra frente sem intervencao.

Regras:
  * Server unico "CPE TECNOLOGIA" — id vem de env CPE_CHAT_SERVER_ID
    ou fallback 1.
  * Todos os users ativos entram no server como member (owner/admin
    definidos previamente pelo admin, nao sobrescrevemos).
  * Cada cpe_grupo tem 1 canal chat_channels tipo='grupo_sistema'
    com grupo_id apontando pra ele (garantido por UNIQUE KEY do schema).
  * Users com users.group_id=X entram no canal do grupo X.
  * Match fuzzy de categoria (normaliza lower + strip acentos) — se o
    nome do grupo bate com nome de categoria existente, o canal entra
    ali; senao fica solto no topo do server.
  * Idempotente: rodar N vezes tem mesmo efeito de rodar 1 vez.

Todos os helpers sao SILENCIOSOS em caso de falha (log warning + continua).
Falha aqui NUNCA deve derrubar create_user / create_group.
"""
import logging
import os
import unicodedata
from typing import Optional

from database import get_chat_db_or_404, get_db_or_404

logger = logging.getLogger(__name__)

CPE_CHAT_SERVER_ID = int(os.getenv("CPE_CHAT_SERVER_ID", "1"))


def _norm(s: str) -> str:
    """Normaliza pra match fuzzy: lower + sem acento + sem espaco/ponto/hifen."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c for c in s.lower() if c.isalnum())


def _slug(nome: str) -> str:
    """Nome do canal: lower + acento removido + espaco/ponto -> hifen."""
    if not nome:
        return "canal"
    s = unicodedata.normalize("NFD", nome)
    s = "".join(c for c in s if not unicodedata.combining(c))
    out = []
    prev_h = False
    for ch in s.lower():
        if ch.isalnum():
            out.append(ch)
            prev_h = False
        elif not prev_h:
            out.append("-")
            prev_h = True
    slug = "".join(out).strip("-") or "canal"
    return slug[:100]


def _categoria_match(chat_cur, server_id: int, nome_grupo: str) -> Optional[int]:
    """Procura categoria com nome que bate (normalizado) com nome_grupo.
    Retorna id da categoria ou None se nao achou."""
    alvo = _norm(nome_grupo)
    if not alvo:
        return None
    chat_cur.execute(
        "SELECT id, nome FROM chat_categories WHERE server_id=%s",
        (server_id,),
    )
    for row in chat_cur.fetchall() or []:
        if _norm(row["nome"]) == alvo:
            return row["id"]
    # Segundo passe: match parcial (ex: "suporte ti" bate com categoria "T.I")
    for row in chat_cur.fetchall() or []:
        n = _norm(row["nome"])
        if n and (n in alvo or alvo in n):
            return row["id"]
    return None


def garantir_server_membro(user_id: int, role: str = "member") -> bool:
    """Adiciona user ao server CPE TECNOLOGIA se ainda nao for membro.
    Retorna True se inseriu, False se ja era membro (ou erro)."""
    try:
        conn = get_chat_db_or_404()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT IGNORE INTO chat_server_members (server_id, user_id, role) "
                "VALUES (%s, %s, %s)",
                (CPE_CHAT_SERVER_ID, user_id, role),
            )
            inserido = cur.rowcount > 0
            conn.commit()
            return inserido
        finally:
            cur.close(); conn.close()
    except Exception as e:
        logger.warning(f"[CHAT-BOOT] garantir_server_membro user={user_id}: {e}")
        return False


def garantir_canal_do_grupo(group_id: int, nome_grupo: str,
                             criador_user_id: Optional[int] = None) -> Optional[int]:
    """Garante que existe 1 canal chat_channels tipo='grupo_sistema' pra
    esse grupo. Retorna channel_id. Idempotente via UNIQUE(grupo_id)."""
    try:
        conn = get_chat_db_or_404()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT id FROM chat_channels WHERE grupo_id=%s LIMIT 1",
                (group_id,),
            )
            row = cur.fetchone()
            if row:
                return row["id"]

            # Match de categoria existente (por nome fuzzy)
            categoria_id = _categoria_match(cur, CPE_CHAT_SERVER_ID, nome_grupo)

            # Nome + slug
            nome_canal = _slug(nome_grupo)
            desc = f"Canal do grupo {nome_grupo}"

            cur.execute(
                """INSERT INTO chat_channels
                     (tipo, nome, descricao, grupo_id, server_id,
                      categoria_id, criado_por)
                   VALUES ('grupo_sistema', %s, %s, %s, %s, %s, %s)""",
                (nome_canal, desc, group_id, CPE_CHAT_SERVER_ID,
                 categoria_id, criador_user_id),
            )
            cid = cur.lastrowid
            conn.commit()
            logger.info(
                f"[CHAT-BOOT] canal criado: grupo_id={group_id} nome='{nome_canal}' "
                f"categoria={categoria_id} channel_id={cid}"
            )
            return cid
        finally:
            cur.close(); conn.close()
    except Exception as e:
        logger.warning(f"[CHAT-BOOT] garantir_canal_do_grupo grupo={group_id}: {e}")
        return None


def garantir_membro_canal(channel_id: int, user_id: int,
                           role: str = "member") -> bool:
    """Adiciona user ao canal se ainda nao for membro. Idempotente."""
    try:
        conn = get_chat_db_or_404()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT IGNORE INTO chat_channel_members "
                "(channel_id, user_id, role) VALUES (%s, %s, %s)",
                (channel_id, user_id, role),
            )
            inserido = cur.rowcount > 0
            conn.commit()
            return inserido
        finally:
            cur.close(); conn.close()
    except Exception as e:
        logger.warning(f"[CHAT-BOOT] garantir_membro_canal ch={channel_id} u={user_id}: {e}")
        return False


def remover_membro_canal(channel_id: int, user_id: int) -> bool:
    """Remove user do canal. Usado quando o user migra pra outro grupo."""
    try:
        conn = get_chat_db_or_404()
        cur = conn.cursor()
        try:
            cur.execute(
                "DELETE FROM chat_channel_members WHERE channel_id=%s AND user_id=%s",
                (channel_id, user_id),
            )
            conn.commit()
            return True
        finally:
            cur.close(); conn.close()
    except Exception as e:
        logger.warning(f"[CHAT-BOOT] remover_membro_canal ch={channel_id} u={user_id}: {e}")
        return False


def sync_user(user_id: int, group_id: Optional[int]) -> None:
    """Sincroniza um user com o chat:
    - Garante membro do server CPE
    - Se tem group_id, garante membro do canal daquele grupo
    - Se estava em outro canal grupo_sistema, remove (migracao)

    Silencioso — chamado dentro de hooks de create/update de user,
    NUNCA deve derrubar a operacao principal.
    """
    try:
        garantir_server_membro(user_id)

        # Se sem grupo, so remove associacoes antigas (migracao de grupo pra
        # "sem grupo")
        if not group_id:
            _limpar_canais_grupo_do_user(user_id)
            return

        # Busca nome do grupo em cpe_plus
        plus = get_db_or_404()
        p = plus.cursor(dictionary=True)
        try:
            p.execute("SELECT id, name FROM cpe_grupo WHERE id=%s", (group_id,))
            g = p.fetchone()
        finally:
            p.close(); plus.close()
        if not g:
            return

        cid = garantir_canal_do_grupo(group_id, g["name"])
        if not cid:
            return

        # Remove de OUTROS canais grupo_sistema (user migrou de grupo)
        _limpar_canais_grupo_do_user(user_id, exceto_channel_id=cid)
        garantir_membro_canal(cid, user_id)
    except Exception as e:
        logger.warning(f"[CHAT-BOOT] sync_user user={user_id}: {e}")


def _limpar_canais_grupo_do_user(user_id: int, exceto_channel_id: Optional[int] = None) -> None:
    """Remove user de todos os canais tipo='grupo_sistema' exceto o
    channel_id passado (usado ao migrar de grupo)."""
    try:
        conn = get_chat_db_or_404()
        cur = conn.cursor()
        try:
            if exceto_channel_id:
                cur.execute(
                    """DELETE cm FROM chat_channel_members cm
                        JOIN chat_channels c ON c.id = cm.channel_id
                       WHERE cm.user_id = %s
                         AND c.tipo = 'grupo_sistema'
                         AND cm.channel_id != %s""",
                    (user_id, exceto_channel_id),
                )
            else:
                cur.execute(
                    """DELETE cm FROM chat_channel_members cm
                        JOIN chat_channels c ON c.id = cm.channel_id
                       WHERE cm.user_id = %s
                         AND c.tipo = 'grupo_sistema'""",
                    (user_id,),
                )
            conn.commit()
        finally:
            cur.close(); conn.close()
    except Exception as e:
        logger.warning(f"[CHAT-BOOT] _limpar_canais_grupo_do_user u={user_id}: {e}")


def sync_grupo(group_id: int, nome_grupo: str,
                criador_user_id: Optional[int] = None) -> Optional[int]:
    """Chamado quando um novo grupo e criado — cria canal correspondente."""
    return garantir_canal_do_grupo(group_id, nome_grupo, criador_user_id)
