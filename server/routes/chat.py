"""
Chat Realtime — Discord-like
============================
Modulo de chat com DMs + canais por grupo do sistema.

Arquitetura:
- Database `cpe_chat` separado (mesma instancia MariaDB).
- Transporte: WebSocket (FastAPI native) pra realtime; REST pra historico.
- Auth: session token HMAC ja existente (via query param `?token=` no WS).
- ConnectionManager mantem `Set[WebSocket]` por user_id pra broadcast.

NAO inclui ainda: reacoes, threads, mentions, file upload, voice, edicao
de mensagem, presence beyond online/offline. Estes entram em fases
seguintes apos validar a fundacao.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query, Request, status, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, Dict, Set, List, Any
import json
import logging
import asyncio
import os
import re
import uuid as _uuid
from pathlib import Path
from datetime import datetime, timedelta

# Web Push (graceful — se pywebpush nao instalado, push fica off)
try:
    from pywebpush import webpush, WebPushException
    _PYWEBPUSH_OK = True
except Exception:
    _PYWEBPUSH_OK = False

_VAPID_PUBLIC  = os.getenv("VAPID_PUBLIC_KEY", "").strip()
_VAPID_PRIVATE = os.getenv("VAPID_PRIVATE_KEY", "").replace("\\n", "\n").strip()
_VAPID_CONTACT = os.getenv("VAPID_CONTACT_EMAIL", "mailto:admin@example.com").strip()
_PUSH_ENABLED  = _PYWEBPUSH_OK and bool(_VAPID_PUBLIC) and bool(_VAPID_PRIVATE)

# Token de @mention armazenado no content: `<@123>` => user id 123
_MENTION_RE = re.compile(r"<@(\d+)>")

from database import get_chat_db_or_404, get_db_or_404
from security import parse_session_token, get_user_by_id

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)


# =====================================================================
# Connection Manager — proprio do chat (nao acopla com WS de tickets)
# =====================================================================
class ChatConnectionManager:
    def __init__(self):
        # user_id -> set de WebSockets (user pode estar em multiplas abas/devices)
        self._conns: Dict[int, Set[WebSocket]] = {}

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self._conns.setdefault(user_id, set()).add(ws)
        logger.warning(f"[CHAT-WS] +user {user_id} (conexoes_do_user={len(self._conns[user_id])} "
                       f"total_users_online={len(self._conns)})")
        self._set_presence(user_id, "online")

    def disconnect(self, user_id: int, ws: WebSocket):
        if user_id in self._conns:
            self._conns[user_id].discard(ws)
            if not self._conns[user_id]:
                del self._conns[user_id]
                self._set_presence(user_id, "offline")
                self._cleanup_voice_sessions(user_id)
        logger.warning(f"[CHAT-WS] -user {user_id} total_online={len(self._conns)}")

    async def send_to_users(self, user_ids: List[int], payload: dict):
        """Broadcast pra todos os WSs de uma lista de users."""
        msg = json.dumps(payload, default=str)
        dead: List = []
        for uid in user_ids:
            for ws in list(self._conns.get(uid, ())):
                try:
                    await ws.send_text(msg)
                except Exception as e:
                    logger.warning(f"[CHAT-WS] dead ws user={uid}: {e}")
                    dead.append((uid, ws))
        for uid, ws in dead:
            self.disconnect(uid, ws)

    def online_users(self) -> List[int]:
        return list(self._conns.keys())

    @staticmethod
    def _set_presence(user_id: int, status_: str):
        """Atualiza chat_presence (best-effort, nao bloqueia se falhar)."""
        try:
            conn = get_chat_db_or_404()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO chat_presence (user_id, status, ultima_atividade)
                VALUES (%s, %s, NOW())
                ON DUPLICATE KEY UPDATE status=VALUES(status), ultima_atividade=NOW()
            """, (user_id, status_))
            conn.commit()
            cur.close(); conn.close()
        except Exception as e:
            logger.warning(f"[CHAT-WS] presence update failed: {e}")

    @staticmethod
    def _cleanup_voice_sessions(user_id: int):
        """Quando user perde TODAS as conexoes WS, tira ele das salas de voz
        (sem isso, peers ficariam tentando conectar com fantasma)."""
        try:
            conn = get_chat_db_or_404()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT channel_id FROM chat_voice_sessions WHERE user_id=%s",
                (user_id,))
            channels = [r["channel_id"] for r in cur.fetchall()]
            if channels:
                cur.execute(
                    "DELETE FROM chat_voice_sessions WHERE user_id=%s", (user_id,))
                conn.commit()
            cur.close(); conn.close()
            if channels:
                asyncio.create_task(_broadcast_voice_leaves(user_id, channels))
        except Exception as e:
            logger.warning(f"[CHAT-WS] cleanup voice fail user={user_id}: {e}")


async def _broadcast_voice_leaves(user_id: int, channel_ids: List[int]):
    for ch_id in channel_ids:
        membros = _listar_membros_canal(ch_id)
        await manager.send_to_users(membros, {
            "type": "voice_leave",
            "channel_id": ch_id,
            "user_id": user_id,
        })


manager = ChatConnectionManager()


# =====================================================================
# Estado em memoria de chamadas 1-a-1 pendentes (nao respondidas ainda)
# Estrutura: target_user_id -> {from_user_id, from_name, channel_id, ts}
#
# Por que em memoria: chamadas duram <1min e o estado e consultado MUITO.
# Quando o user reconecta no WS, re-enviamos o invite pra ele (caso tenha
# perdido). Quando ele clica numa push notif, validamos se a call ainda
# esta valida (TTL 35s).
# =====================================================================
_PENDING_CALLS: Dict[int, dict] = {}
_CALL_TTL_SECONDS = 35


def _registrar_chamada(target: int, from_uid: int, from_name: str, channel_id: int):
    _PENDING_CALLS[target] = {
        "from_user_id": from_uid,
        "from_user_name": from_name,
        "channel_id": channel_id,
        "ts": datetime.utcnow().timestamp(),
    }


def _cancelar_chamada(target: int, from_uid: Optional[int] = None) -> bool:
    """Remove call pendente. Se from_uid passado, so cancela se for desse caller."""
    c = _PENDING_CALLS.get(target)
    if not c:
        return False
    if from_uid is not None and c["from_user_id"] != from_uid:
        return False
    _PENDING_CALLS.pop(target, None)
    return True


def _chamada_pendente(target: int) -> Optional[dict]:
    c = _PENDING_CALLS.get(target)
    if not c:
        return None
    if datetime.utcnow().timestamp() - c["ts"] > _CALL_TTL_SECONDS:
        _PENDING_CALLS.pop(target, None)
        return None
    return c



# =====================================================================
# Upload de imagens (anexos)
# =====================================================================
_UPLOAD_CHAT_ROOT     = Path(__file__).resolve().parents[2] / "web" / "uploads" / "chat"
_UPLOAD_CHAT_URL_BASE = "/SistemaCPE/web/uploads/chat"
_CHAT_IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_MAX_CHAT_IMG_MB = 25
_CLEANUP_DIAS = 90


# =====================================================================
# Pydantic models
# =====================================================================
class MensagemNova(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    reply_to_id: Optional[int] = None


# =====================================================================
# Helpers
# =====================================================================
def _user_from_request(request: Request) -> dict:
    """Resolve o user atual a partir do cookie/header (REST)."""
    token = request.cookies.get("cpe_session") or request.headers.get("X-Auth-Token", "")
    if not token:
        raise HTTPException(status_code=401, detail="Sem token de sessao")
    user_id = parse_session_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado")
    return user


def _listar_membros_canal(channel_id: int) -> List[int]:
    """IDs dos users membros de um canal."""
    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute("SELECT user_id FROM chat_channel_members WHERE channel_id=%s", (channel_id,))
        return [r[0] for r in cur.fetchall()]
    finally:
        cur.close(); conn.close()


def _usuario_pertence_ao_canal(user_id: int, channel_id: int) -> bool:
    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT 1 FROM chat_channel_members WHERE channel_id=%s AND user_id=%s LIMIT 1",
            (channel_id, user_id))
        return cur.fetchone() is not None
    finally:
        cur.close(); conn.close()


def _enriquecer_users(user_ids: List[int]) -> Dict[int, dict]:
    """Pega dados de cpe_plus.users em uma query (nome, email, group)."""
    if not user_ids:
        return {}
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        placeholders = ",".join(["%s"] * len(user_ids))
        cur.execute(
            f"SELECT id, name, email, role, group_id FROM users WHERE id IN ({placeholders})",
            user_ids)
        return {r["id"]: r for r in cur.fetchall()}
    finally:
        cur.close(); conn.close()


# =====================================================================
# REST: canais
# =====================================================================
@router.get("/channels")
def listar_canais(request: Request):
    """Retorna os canais que o user atual eh membro (DMs + grupo_sistema + canal).
    Inclui `unread_count` por canal (mensagens depois do ultima_msg_lida_id,
    excluindo as proprias do user)."""
    user = _user_from_request(request)
    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT c.id, c.tipo, c.nome, c.descricao, c.grupo_id, c.criado_em,
                   m.ultima_msg_lida_id,
                   (SELECT COUNT(*) FROM chat_messages msg
                      WHERE msg.channel_id = c.id
                        AND msg.deletado_em IS NULL
                        AND msg.user_id != %s
                        AND msg.id > COALESCE(m.ultima_msg_lida_id, 0)
                   ) AS unread_count
            FROM chat_channels c
            INNER JOIN chat_channel_members m ON m.channel_id = c.id
            WHERE m.user_id = %s AND c.arquivado_em IS NULL
            ORDER BY c.tipo, c.nome
        """, (user["id"], user["id"]))
        canais = cur.fetchall()

        # Pra DMs, deriva o "nome" do outro membro (pra UI mostrar)
        dm_ids = [c["id"] for c in canais if c["tipo"] == "dm"]
        outros_por_canal: Dict[int, int] = {}
        if dm_ids:
            placeholders = ",".join(["%s"] * len(dm_ids))
            cur.execute(
                f"SELECT channel_id, user_id FROM chat_channel_members "
                f"WHERE channel_id IN ({placeholders}) AND user_id != %s",
                [*dm_ids, user["id"]])
            for r in cur.fetchall():
                outros_por_canal[r["channel_id"]] = r["user_id"]
        users_map = _enriquecer_users(list(outros_por_canal.values()))
        for c in canais:
            if c["tipo"] == "dm":
                other_uid = outros_por_canal.get(c["id"])
                u = users_map.get(other_uid, {})
                c["dm_with"] = {
                    "id": other_uid, "name": u.get("name"), "email": u.get("email")
                }
                c["nome"] = u.get("name") or f"Usuario #{other_uid}"
        return {"success": True, "channels": canais}
    finally:
        cur.close(); conn.close()


@router.post("/channels/dm/{other_user_id}")
def abrir_ou_criar_dm(other_user_id: int, request: Request):
    """Retorna a DM existente entre o user atual e other_user_id, ou cria."""
    user = _user_from_request(request)
    if user["id"] == other_user_id:
        raise HTTPException(status_code=400, detail="Nao da pra abrir DM consigo mesmo")

    # Confirma que o outro user existe
    if not get_user_by_id(other_user_id):
        raise HTTPException(status_code=404, detail="Usuario destino nao encontrado")

    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        # Procura DM existente com EXATAMENTE esses 2 membros
        cur.execute("""
            SELECT c.id
            FROM chat_channels c
            INNER JOIN chat_channel_members m1 ON m1.channel_id = c.id AND m1.user_id = %s
            INNER JOIN chat_channel_members m2 ON m2.channel_id = c.id AND m2.user_id = %s
            WHERE c.tipo = 'dm'
            LIMIT 1
        """, (user["id"], other_user_id))
        row = cur.fetchone()
        if row:
            return {"success": True, "channel_id": row["id"], "created": False}

        # Cria
        cur.execute("""
            INSERT INTO chat_channels (tipo, criado_por) VALUES ('dm', %s)
        """, (user["id"],))
        channel_id = cur.lastrowid
        cur.executemany("""
            INSERT INTO chat_channel_members (channel_id, user_id, role) VALUES (%s, %s, %s)
        """, [(channel_id, user["id"], "owner"),
              (channel_id, other_user_id, "member")])
        conn.commit()
        return {"success": True, "channel_id": channel_id, "created": True}
    finally:
        cur.close(); conn.close()


@router.get("/channels/{channel_id}/messages")
def listar_mensagens(channel_id: int, request: Request,
                     before_id: Optional[int] = Query(None),
                     limit: int = Query(50, le=200)):
    """Historico de mensagens (paginado, mais novas primeiro)."""
    user = _user_from_request(request)
    if not _usuario_pertence_ao_canal(user["id"], channel_id):
        raise HTTPException(status_code=403, detail="Voce nao e membro deste canal")

    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        if before_id:
            cur.execute("""
                SELECT id, channel_id, user_id, content, reply_to_id, criado_em, editado_em
                FROM chat_messages
                WHERE channel_id=%s AND deletado_em IS NULL AND id < %s
                ORDER BY id DESC LIMIT %s
            """, (channel_id, before_id, limit))
        else:
            cur.execute("""
                SELECT id, channel_id, user_id, content, reply_to_id, criado_em, editado_em
                FROM chat_messages
                WHERE channel_id=%s AND deletado_em IS NULL
                ORDER BY id DESC LIMIT %s
            """, (channel_id, limit))
        msgs = cur.fetchall()
        msgs.reverse()  # cliente espera ordem cronologica ascendente

        users_map = _enriquecer_users(list({m["user_id"] for m in msgs}))
        for m in msgs:
            u = users_map.get(m["user_id"], {})
            m["author"] = {"id": m["user_id"], "name": u.get("name"), "email": u.get("email")}

        # Anexa attachments + reactions + mentions + reply_to (1 query cada)
        if msgs:
            msg_ids = [m["id"] for m in msgs]
            placeholders = ",".join(["%s"] * len(msg_ids))

            # Attachments
            cur.execute(f"""
                SELECT id, message_id, tipo, arquivo, nome_original, mime, tamanho
                FROM chat_attachments WHERE message_id IN ({placeholders}) ORDER BY id
            """, msg_ids)
            atts_por_msg: Dict[int, List[dict]] = {}
            for a in cur.fetchall():
                atts_por_msg.setdefault(a["message_id"], []).append(a)

            # Reactions agrupadas por (msg, emoji) com lista de user_ids
            cur.execute(f"""
                SELECT message_id, emoji, user_id
                FROM chat_message_reactions WHERE message_id IN ({placeholders})
                ORDER BY criado_em
            """, msg_ids)
            react_raw: Dict[int, Dict[str, List[int]]] = {}
            for r in cur.fetchall():
                react_raw.setdefault(r["message_id"], {}).setdefault(r["emoji"], []).append(r["user_id"])

            # Mentions
            cur.execute(f"""
                SELECT message_id, user_id FROM chat_mentions
                WHERE message_id IN ({placeholders})
            """, msg_ids)
            mentions_por_msg: Dict[int, List[int]] = {}
            for r in cur.fetchall():
                mentions_por_msg.setdefault(r["message_id"], []).append(r["user_id"])

            # Reply_to: pega preview das msgs originais referenciadas
            reply_ids = [m["reply_to_id"] for m in msgs if m.get("reply_to_id")]
            reply_map: Dict[int, dict] = {}
            if reply_ids:
                p2 = ",".join(["%s"] * len(reply_ids))
                cur.execute(f"""
                    SELECT id, user_id, content, deletado_em
                    FROM chat_messages WHERE id IN ({p2})
                """, reply_ids)
                rmsgs = cur.fetchall()
                rusers = _enriquecer_users(list({r["user_id"] for r in rmsgs}))
                for r in rmsgs:
                    u = rusers.get(r["user_id"], {})
                    reply_map[r["id"]] = {
                        "id": r["id"],
                        "author_name": u.get("name"),
                        "content_preview": ("(mensagem apagada)" if r["deletado_em"]
                                            else (r["content"] or "")[:160]),
                    }

            for m in msgs:
                m["attachments"] = atts_por_msg.get(m["id"], [])
                m["mentions"] = mentions_por_msg.get(m["id"], [])
                reacs = react_raw.get(m["id"], {})
                m["reactions"] = [
                    {"emoji": e, "count": len(uids), "users": uids,
                     "self_reacted": user["id"] in uids}
                    for e, uids in reacs.items()
                ]
                if m.get("reply_to_id"):
                    m["reply_to"] = reply_map.get(m["reply_to_id"])
        return {"success": True, "messages": msgs, "has_more": len(msgs) == limit}
    finally:
        cur.close(); conn.close()


@router.post("/channels/{channel_id}/messages")
async def enviar_mensagem(channel_id: int, body: MensagemNova, request: Request):
    """REST pra enviar msg (alternativa ao WebSocket — util pra clientes
    sem WS). Tambem faz broadcast pra subscribers via manager."""
    user = _user_from_request(request)
    if not _usuario_pertence_ao_canal(user["id"], channel_id):
        raise HTTPException(status_code=403, detail="Voce nao e membro deste canal")

    msg_payload = await _persistir_e_broadcastar(
        channel_id=channel_id,
        user_id=user["id"],
        user_name=user.get("name"),
        content=body.content,
        reply_to_id=body.reply_to_id,
    )
    return {"success": True, "message": msg_payload}


# =====================================================================
# Mark-read: atualiza ultima_msg_lida_id do user no canal
# =====================================================================
@router.post("/channels/{channel_id}/read")
def marcar_canal_lido(channel_id: int, request: Request):
    """Marca o canal como lido pelo user atual (ate a ultima msg existente)."""
    user = _user_from_request(request)
    if not _usuario_pertence_ao_canal(user["id"], channel_id):
        raise HTTPException(status_code=403, detail="Voce nao e membro deste canal")
    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE chat_channel_members m
            SET m.ultima_msg_lida_id = COALESCE((
                SELECT MAX(id) FROM chat_messages
                WHERE channel_id = m.channel_id
            ), m.ultima_msg_lida_id)
            WHERE m.channel_id = %s AND m.user_id = %s
        """, (channel_id, user["id"]))
        conn.commit()
        return {"success": True}
    finally:
        cur.close(); conn.close()


# =====================================================================
# Edit / Delete de mensagem
# =====================================================================
class MensagemEdit(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


def _msg_e_canal_ou_404(message_id: int) -> dict:
    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, channel_id, user_id, content, deletado_em
            FROM chat_messages WHERE id=%s
        """, (message_id,))
        m = cur.fetchone()
        if not m:
            raise HTTPException(status_code=404, detail="Mensagem nao encontrada")
        return m
    finally:
        cur.close(); conn.close()


@router.patch("/messages/{message_id}")
async def editar_mensagem(message_id: int, body: MensagemEdit, request: Request):
    user = _user_from_request(request)
    m = _msg_e_canal_ou_404(message_id)
    if m["deletado_em"]:
        raise HTTPException(status_code=400, detail="Mensagem ja foi apagada")
    if m["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="So o autor pode editar")

    novo_conteudo = body.content.strip()
    if not novo_conteudo:
        raise HTTPException(status_code=400, detail="Conteudo nao pode ser vazio")
    if novo_conteudo == m["content"]:
        return {"success": True, "noop": True}

    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE chat_messages SET content=%s, editado_em=NOW() WHERE id=%s
        """, (novo_conteudo, message_id))
        conn.commit()
    finally:
        cur.close(); conn.close()

    payload = {
        "type": "message_edited",
        "channel_id": m["channel_id"],
        "id": message_id,
        "content": novo_conteudo,
        "editado_em": datetime.utcnow().isoformat(),
    }
    membros = _listar_membros_canal(m["channel_id"])
    await manager.send_to_users(membros, payload)
    return {"success": True, "message": payload}


@router.delete("/messages/{message_id}")
async def deletar_mensagem(message_id: int, request: Request):
    """Soft delete. Autor pode sempre; ADMIN/TI/MANAGER podem qualquer msg."""
    user = _user_from_request(request)
    m = _msg_e_canal_ou_404(message_id)
    if m["deletado_em"]:
        return {"success": True, "noop": True}
    is_admin = user.get("role") in ("ADMIN", "TI", "MANAGER")
    if m["user_id"] != user["id"] and not is_admin:
        raise HTTPException(status_code=403, detail="Sem permissao pra apagar")

    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE chat_messages SET deletado_em=NOW() WHERE id=%s", (message_id,))
        conn.commit()
    finally:
        cur.close(); conn.close()

    payload = {
        "type": "message_deleted",
        "channel_id": m["channel_id"],
        "id": message_id,
    }
    membros = _listar_membros_canal(m["channel_id"])
    await manager.send_to_users(membros, payload)
    return {"success": True}


# =====================================================================
# Canais customizados — criados pelo Responsavel de Grupo (e ADMIN/TI/MANAGER)
# Cross-grupo/cross-setor por design. Owner gerencia; admin pode adicionar
# membros; member so conversa.
# =====================================================================
_ROLES_CRIAR_CANAL = ("RESPONSAVEL_GRUPO", "ADMIN", "TI", "MANAGER")


class CanalCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    member_ids: List[int] = Field(default_factory=list)
    tipo: str = Field("canal", pattern=r"^(canal|voz)$",
                      description="canal de texto ou voz")


class CanalEdit(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)


class AddMembersBody(BaseModel):
    user_ids: List[int]


def _role_no_canal(channel_id: int, user_id: int) -> Optional[str]:
    """Retorna 'owner'/'admin'/'member' OU None se nao for membro."""
    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute("SELECT role FROM chat_channel_members WHERE channel_id=%s AND user_id=%s",
                    (channel_id, user_id))
        r = cur.fetchone()
        return r[0] if r else None
    finally:
        cur.close(); conn.close()


def _canal_existe_e_tipo(channel_id: int) -> tuple[bool, Optional[str]]:
    """Returns (exists, tipo). tipo in {dm, grupo_sistema, canal} ou None."""
    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute("SELECT tipo FROM chat_channels WHERE id=%s AND arquivado_em IS NULL",
                    (channel_id,))
        r = cur.fetchone()
        return (r is not None, r[0] if r else None)
    finally:
        cur.close(); conn.close()


@router.post("/channels")
async def criar_canal(body: CanalCreate, request: Request):
    """Cria um canal customizado (tipo='canal'). Criador vira owner."""
    user = _user_from_request(request)
    if user.get("role") not in _ROLES_CRIAR_CANAL:
        raise HTTPException(status_code=403,
                            detail="So Responsavel de Grupo, Manager, TI ou Admin podem criar canal")

    nome = body.nome.strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Nome obrigatorio")

    # Filtra member_ids — so users que existem e estao ativos
    member_ids = list({int(x) for x in body.member_ids if x and int(x) != user["id"]})
    validos: List[int] = []
    if member_ids:
        plus = get_db_or_404()
        pcur = plus.cursor(dictionary=True)
        try:
            placeholders = ",".join(["%s"] * len(member_ids))
            pcur.execute(
                f"SELECT id FROM users WHERE id IN ({placeholders}) AND is_active=1",
                member_ids)
            validos = [r["id"] for r in pcur.fetchall()]
        finally:
            pcur.close(); plus.close()

    chat = get_chat_db_or_404()
    ccur = chat.cursor()
    try:
        ccur.execute("""
            INSERT INTO chat_channels (tipo, nome, descricao, criado_por)
            VALUES (%s, %s, %s, %s)
        """, (body.tipo, nome, body.descricao, user["id"]))
        channel_id = ccur.lastrowid

        # Owner + members
        rows = [(channel_id, user["id"], "owner")]
        rows += [(channel_id, uid, "member") for uid in validos]
        ccur.executemany("""
            INSERT INTO chat_channel_members (channel_id, user_id, role)
            VALUES (%s, %s, %s)
        """, rows)
        chat.commit()
    finally:
        ccur.close(); chat.close()

    # Notifica todos os novos membros via WS pra atualizar lista de canais
    await manager.send_to_users([user["id"]] + validos, {
        "type": "channel_created",
        "channel_id": channel_id,
        "nome": nome,
    })

    return {"success": True, "channel_id": channel_id, "members_added": len(validos)}


@router.patch("/channels/{channel_id}")
async def editar_canal(channel_id: int, body: CanalEdit, request: Request):
    """Edita nome/descricao. So canais tipo='canal'. Owner/admin do canal ou
    ADMIN/TI/MANAGER do sistema."""
    user = _user_from_request(request)
    existe, tipo = _canal_existe_e_tipo(channel_id)
    if not existe:
        raise HTTPException(status_code=404, detail="Canal nao encontrado")
    if tipo != "canal":
        raise HTTPException(status_code=400,
                            detail="Apenas canais customizados podem ser editados")

    role = _role_no_canal(channel_id, user["id"])
    is_sys_admin = user.get("role") in ("ADMIN", "TI", "MANAGER")
    if role not in ("owner", "admin") and not is_sys_admin:
        raise HTTPException(status_code=403, detail="Sem permissao pra editar este canal")

    sets, params = [], []
    if body.nome is not None:
        nome = body.nome.strip()
        if not nome:
            raise HTTPException(status_code=400, detail="Nome nao pode ser vazio")
        sets.append("nome=%s"); params.append(nome)
    if body.descricao is not None:
        sets.append("descricao=%s"); params.append(body.descricao)
    if not sets:
        return {"success": True, "noop": True}
    params.append(channel_id)

    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute(f"UPDATE chat_channels SET {', '.join(sets)} WHERE id=%s", params)
        conn.commit()
    finally:
        cur.close(); conn.close()

    membros = _listar_membros_canal(channel_id)
    await manager.send_to_users(membros, {
        "type": "channel_updated",
        "channel_id": channel_id,
        "nome": body.nome, "descricao": body.descricao,
    })
    return {"success": True}


@router.delete("/channels/{channel_id}")
async def arquivar_canal(channel_id: int, request: Request):
    """Arquiva (soft delete). So owner ou ADMIN do sistema. Nao funciona em DM/grupo_sistema."""
    user = _user_from_request(request)
    existe, tipo = _canal_existe_e_tipo(channel_id)
    if not existe:
        raise HTTPException(status_code=404, detail="Canal nao encontrado")
    if tipo != "canal":
        raise HTTPException(status_code=400,
                            detail="Apenas canais customizados podem ser arquivados")

    role = _role_no_canal(channel_id, user["id"])
    is_sys_admin = user.get("role") in ("ADMIN", "TI", "MANAGER")
    if role != "owner" and not is_sys_admin:
        raise HTTPException(status_code=403, detail="So o dono do canal pode arquivar")

    membros = _listar_membros_canal(channel_id)
    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE chat_channels SET arquivado_em=NOW() WHERE id=%s", (channel_id,))
        conn.commit()
    finally:
        cur.close(); conn.close()

    await manager.send_to_users(membros, {
        "type": "channel_archived",
        "channel_id": channel_id,
    })
    return {"success": True}


@router.get("/channels/{channel_id}/members")
def listar_membros_enriquecido(channel_id: int, request: Request):
    """Lista membros com dados de cpe_plus.users + status online."""
    user = _user_from_request(request)
    if not _usuario_pertence_ao_canal(user["id"], channel_id):
        raise HTTPException(status_code=403, detail="Voce nao e membro deste canal")

    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT user_id, role, entrou_em
            FROM chat_channel_members WHERE channel_id=%s ORDER BY role, entrou_em
        """, (channel_id,))
        rows = cur.fetchall()
    finally:
        cur.close(); conn.close()

    users_map = _enriquecer_users([r["user_id"] for r in rows])
    online = set(manager.online_users())
    result = []
    for r in rows:
        u = users_map.get(r["user_id"], {})
        result.append({
            "user_id": r["user_id"],
            "name": u.get("name"),
            "email": u.get("email"),
            "role_no_canal": r["role"],
            "online": r["user_id"] in online,
            "entrou_em": r["entrou_em"],
        })
    return {"success": True, "members": result}


@router.post("/channels/{channel_id}/members")
async def adicionar_membros(channel_id: int, body: AddMembersBody, request: Request):
    """Adiciona membros. So owner/admin do canal ou ADMIN sistema."""
    user = _user_from_request(request)
    existe, tipo = _canal_existe_e_tipo(channel_id)
    if not existe:
        raise HTTPException(status_code=404, detail="Canal nao encontrado")
    if tipo == "dm":
        raise HTTPException(status_code=400, detail="DM nao aceita novos membros")
    if tipo == "grupo_sistema":
        raise HTTPException(status_code=400,
                            detail="Membros de canais de grupo do sistema sao sincronizados automaticamente")

    role = _role_no_canal(channel_id, user["id"])
    is_sys_admin = user.get("role") in ("ADMIN", "TI", "MANAGER")
    if role not in ("owner", "admin") and not is_sys_admin:
        raise HTTPException(status_code=403, detail="Sem permissao pra adicionar membros")

    ids = list({int(x) for x in body.user_ids if x})
    if not ids:
        return {"success": True, "added": 0}

    # Valida que sao usuarios ativos reais
    plus = get_db_or_404()
    pcur = plus.cursor(dictionary=True)
    try:
        placeholders = ",".join(["%s"] * len(ids))
        pcur.execute(
            f"SELECT id FROM users WHERE id IN ({placeholders}) AND is_active=1", ids)
        validos = [r["id"] for r in pcur.fetchall()]
    finally:
        pcur.close(); plus.close()
    if not validos:
        return {"success": True, "added": 0}

    chat = get_chat_db_or_404()
    cur = chat.cursor()
    try:
        rows = [(channel_id, uid, "member") for uid in validos]
        cur.executemany("""
            INSERT IGNORE INTO chat_channel_members (channel_id, user_id, role)
            VALUES (%s, %s, %s)
        """, rows)
        added = cur.rowcount
        chat.commit()
    finally:
        cur.close(); chat.close()

    # Notifica os adicionados pra recarregarem canais
    await manager.send_to_users(validos, {
        "type": "added_to_channel",
        "channel_id": channel_id,
    })
    # E notifica membros atuais que a lista mudou
    todos = _listar_membros_canal(channel_id)
    await manager.send_to_users(todos, {
        "type": "channel_members_changed",
        "channel_id": channel_id,
    })

    return {"success": True, "added": added}


@router.delete("/channels/{channel_id}/members/{user_id}")
async def remover_membro(channel_id: int, user_id: int, request: Request):
    """Remove membro. user pode remover a si mesmo (sair); owner/admin
    do canal e ADMIN sistema podem remover qualquer. Owner nao pode ser
    removido (precisa transferir owner ou arquivar canal)."""
    actor = _user_from_request(request)
    existe, tipo = _canal_existe_e_tipo(channel_id)
    if not existe:
        raise HTTPException(status_code=404, detail="Canal nao encontrado")
    if tipo == "dm":
        raise HTTPException(status_code=400, detail="DM nao tem gerencia de membros")
    if tipo == "grupo_sistema":
        raise HTTPException(status_code=400,
                            detail="Membros de canais de grupo do sistema sao sincronizados automaticamente")

    target_role = _role_no_canal(channel_id, user_id)
    if not target_role:
        raise HTTPException(status_code=404, detail="Usuario nao e membro desse canal")
    if target_role == "owner":
        raise HTTPException(status_code=400,
                            detail="O dono nao pode ser removido. Transfira a posse ou arquive o canal")

    is_self = (actor["id"] == user_id)
    actor_role = _role_no_canal(channel_id, actor["id"])
    is_sys_admin = actor.get("role") in ("ADMIN", "TI", "MANAGER")
    if not is_self and actor_role not in ("owner", "admin") and not is_sys_admin:
        raise HTTPException(status_code=403, detail="Sem permissao pra remover este membro")

    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM chat_channel_members WHERE channel_id=%s AND user_id=%s",
                    (channel_id, user_id))
        conn.commit()
    finally:
        cur.close(); conn.close()

    # Notifica o user removido
    await manager.send_to_users([user_id], {
        "type": "removed_from_channel",
        "channel_id": channel_id,
    })
    # E os membros restantes que houve mudanca
    restantes = _listar_membros_canal(channel_id)
    if restantes:
        await manager.send_to_users(restantes, {
            "type": "channel_members_changed",
            "channel_id": channel_id,
        })
    return {"success": True}


@router.get("/users-disponiveis")
def listar_users_disponiveis(request: Request, q: Optional[str] = Query(None)):
    """Lista users ativos do sistema (id, name, email). Opcionalmente filtra
    por substring em name/email. Usado pelo seletor de membros."""
    _user_from_request(request)  # garante auth
    plus = get_db_or_404()
    cur = plus.cursor(dictionary=True)
    try:
        if q:
            like = f"%{q.strip().lower()}%"
            cur.execute("""
                SELECT id, name, email, role, group_id
                FROM users
                WHERE is_active=1
                  AND (LOWER(name) LIKE %s OR LOWER(email) LIKE %s)
                ORDER BY name LIMIT 50
            """, (like, like))
        else:
            cur.execute("""
                SELECT id, name, email, role, group_id
                FROM users WHERE is_active=1
                ORDER BY name LIMIT 200
            """)
        return {"success": True, "users": cur.fetchall()}
    finally:
        cur.close(); plus.close()


# =====================================================================
# Fase 3: Web Push notifications (PWA)
# Frontend chama /vapid-public-key, faz subscribe no browser, POST aqui.
# Quando uma msg eh enviada, enviamos push pros membros que NAO estao
# conectados no WS (i.e. quem nao recebeu via WebSocket).
# =====================================================================
class PushSubscriptionBody(BaseModel):
    endpoint: str
    keys: Dict[str, str] = Field(default_factory=dict)


class PushUnsubscribeBody(BaseModel):
    endpoint: str


@router.get("/push/vapid-public-key")
def vapid_public_key(request: Request):
    _user_from_request(request)
    if not _PUSH_ENABLED:
        raise HTTPException(status_code=503, detail="Push notifications nao configurado no servidor")
    return {"key": _VAPID_PUBLIC}


@router.post("/push/subscribe")
def push_subscribe(body: PushSubscriptionBody, request: Request):
    """Salva subscription do usuario logado (UPSERT por endpoint)."""
    user = _user_from_request(request)
    if not _PUSH_ENABLED:
        raise HTTPException(status_code=503, detail="Push nao habilitado")
    p256dh = body.keys.get("p256dh", "")
    auth = body.keys.get("auth", "")
    if not body.endpoint or not p256dh or not auth:
        raise HTTPException(status_code=400, detail="Subscription incompleta")

    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO chat_push_subscriptions (user_id, endpoint, p256dh, auth)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE user_id=VALUES(user_id),
                                    p256dh=VALUES(p256dh),
                                    auth=VALUES(auth),
                                    ultimo_uso=NOW()
        """, (user["id"], body.endpoint, p256dh, auth))
        conn.commit()
        return {"success": True}
    finally:
        cur.close(); conn.close()


@router.post("/push/unsubscribe")
def push_unsubscribe(body: PushUnsubscribeBody, request: Request):
    _user_from_request(request)
    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM chat_push_subscriptions WHERE endpoint=%s", (body.endpoint,))
        conn.commit()
        return {"success": True}
    finally:
        cur.close(); conn.close()


def _enviar_push_async(user_ids: List[int], titulo: str, corpo: str, url: str, tag: str):
    """Best-effort: envia push pra TODOS os endpoints dos user_ids.
    Roda sincrono (pywebpush nao tem versao async), entao chame de
    asyncio.to_thread / executor pra nao bloquear o event loop."""
    if not _PUSH_ENABLED or not user_ids:
        return
    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        placeholders = ",".join(["%s"] * len(user_ids))
        cur.execute(
            f"SELECT id, endpoint, p256dh, auth FROM chat_push_subscriptions WHERE user_id IN ({placeholders})",
            user_ids)
        subs = cur.fetchall()
    finally:
        cur.close(); conn.close()

    payload = json.dumps({"title": titulo, "body": corpo, "url": url, "tag": tag})
    dead_ids: List[int] = []
    for s in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": s["endpoint"],
                    "keys": {"p256dh": s["p256dh"], "auth": s["auth"]},
                },
                data=payload,
                vapid_private_key=_VAPID_PRIVATE,
                vapid_claims={"sub": _VAPID_CONTACT},
                ttl=60,
            )
        except WebPushException as e:
            # 410 Gone / 404 — subscription expirou, remove
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            if status_code in (404, 410):
                dead_ids.append(s["id"])
            else:
                logger.warning(f"[PUSH] erro {status_code}: {e}")
        except Exception as e:
            logger.warning(f"[PUSH] excecao: {e}")

    if dead_ids:
        conn = get_chat_db_or_404()
        cur = conn.cursor()
        try:
            placeholders = ",".join(["%s"] * len(dead_ids))
            cur.execute(f"DELETE FROM chat_push_subscriptions WHERE id IN ({placeholders})", dead_ids)
            conn.commit()
        finally:
            cur.close(); conn.close()


# =====================================================================
# Fase 4: Canais de voz (WebRTC mesh P2P)
# - Quem "entra" abre uma sessao em chat_voice_sessions
# - Lista de peers e propagada via WS (voice_join / voice_leave)
# - Signaling (offer/answer/ice) tambem via WS, roteado 1-a-1 por peer_id
# =====================================================================
class VoiceJoinBody(BaseModel):
    peer_id: str = Field(..., min_length=4, max_length=40)


@router.post("/channels/{channel_id}/voice/join")
async def voice_join(channel_id: int, body: VoiceJoinBody, request: Request):
    """Marca user como ativo na sala. Retorna outros peers + suas configs."""
    user = _user_from_request(request)
    if not _usuario_pertence_ao_canal(user["id"], channel_id):
        raise HTTPException(status_code=403, detail="Voce nao e membro deste canal")

    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            INSERT INTO chat_voice_sessions (channel_id, user_id, peer_id)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE peer_id=VALUES(peer_id), entrou_em=NOW(),
                                    mic_on=1, cam_on=0, share_on=0
        """, (channel_id, user["id"], body.peer_id))
        conn.commit()
        # Lista outros peers
        cur.execute("""
            SELECT user_id, peer_id, mic_on, cam_on, share_on
            FROM chat_voice_sessions
            WHERE channel_id=%s AND user_id != %s
        """, (channel_id, user["id"]))
        peers = cur.fetchall()
    finally:
        cur.close(); conn.close()

    # Enriquece com nomes
    users_map = _enriquecer_users([p["user_id"] for p in peers])
    for p in peers:
        u = users_map.get(p["user_id"], {})
        p["name"] = u.get("name") or f"Usuario #{p['user_id']}"

    # Notifica todos os membros do canal (inclusive os ja na sala) que ele entrou
    membros = _listar_membros_canal(channel_id)
    await manager.send_to_users(membros, {
        "type": "voice_join",
        "channel_id": channel_id,
        "user_id": user["id"],
        "user_name": user.get("name"),
        "peer_id": body.peer_id,
    })
    return {"success": True, "peers": peers}


@router.post("/channels/{channel_id}/voice/leave")
async def voice_leave(channel_id: int, request: Request):
    user = _user_from_request(request)
    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM chat_voice_sessions WHERE channel_id=%s AND user_id=%s",
                    (channel_id, user["id"]))
        conn.commit()
    finally:
        cur.close(); conn.close()
    membros = _listar_membros_canal(channel_id)
    await manager.send_to_users(membros, {
        "type": "voice_leave",
        "channel_id": channel_id,
        "user_id": user["id"],
    })
    return {"success": True}


@router.get("/channels/{channel_id}/voice/peers")
def voice_peers(channel_id: int, request: Request):
    """Quem esta AGORA na sala."""
    user = _user_from_request(request)
    if not _usuario_pertence_ao_canal(user["id"], channel_id):
        raise HTTPException(status_code=403, detail="Voce nao e membro deste canal")
    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT user_id, peer_id, mic_on, cam_on, share_on, entrou_em
            FROM chat_voice_sessions WHERE channel_id=%s
            ORDER BY entrou_em
        """, (channel_id,))
        peers = cur.fetchall()
    finally:
        cur.close(); conn.close()
    users_map = _enriquecer_users([p["user_id"] for p in peers])
    for p in peers:
        u = users_map.get(p["user_id"], {})
        p["name"] = u.get("name") or f"Usuario #{p['user_id']}"
    return {"success": True, "peers": peers}


# =====================================================================
# DEBUG: quem esta conectado no WS agora (uso temporario pra diagnose)
# =====================================================================
@router.get("/_debug/online")
def debug_online(request: Request):
    user = _user_from_request(request)
    return {
        "success": True,
        "me": user["id"],
        "online_user_ids": manager.online_users(),
        "total_online": len(manager.online_users()),
        "pending_calls": list(_PENDING_CALLS.keys()),
    }


# =====================================================================
# Sync canais por grupo do sistema (idempotente)
# =====================================================================
@router.post("/admin/sync-grupos")
def sync_canais_grupos(request: Request):
    """Cria 1 canal automatico por grupo em cpe_plus.cpe_grupo e adiciona
    todos os users daquele grupo como membros. Idempotente (chama N vezes
    sem duplicar). Restrito a ADMIN/TI/MANAGER."""
    user = _user_from_request(request)
    if user.get("role") not in ("ADMIN", "TI", "MANAGER"):
        raise HTTPException(status_code=403, detail="Restrito a administradores")

    plus = get_db_or_404()
    chat = get_chat_db_or_404()
    pcur = plus.cursor(dictionary=True)
    ccur = chat.cursor()
    try:
        pcur.execute("SELECT id, name, description FROM cpe_grupo ORDER BY id")
        grupos = pcur.fetchall()
        criados, ja_existiam = 0, 0
        for g in grupos:
            # 1) cria/encontra canal do grupo
            ccur.execute("SELECT id FROM chat_channels WHERE grupo_id=%s", (g["id"],))
            row = ccur.fetchone()
            if row:
                channel_id = row[0]
                ja_existiam += 1
            else:
                ccur.execute("""
                    INSERT INTO chat_channels (tipo, nome, descricao, grupo_id)
                    VALUES ('grupo_sistema', %s, %s, %s)
                """, (g["name"], g.get("description"), g["id"]))
                channel_id = ccur.lastrowid
                criados += 1

            # 2) sincroniza membros: users com group_id = g.id
            pcur.execute(
                "SELECT id FROM users WHERE group_id=%s AND is_active=1", (g["id"],))
            user_ids = [r["id"] for r in pcur.fetchall()]
            if user_ids:
                values = [(channel_id, uid, "member") for uid in user_ids]
                ccur.executemany("""
                    INSERT IGNORE INTO chat_channel_members (channel_id, user_id, role)
                    VALUES (%s, %s, %s)
                """, values)
        chat.commit()
        return {"success": True, "grupos": len(grupos), "canais_criados": criados,
                "canais_ja_existiam": ja_existiam}
    finally:
        pcur.close(); plus.close()
        ccur.close(); chat.close()


# =====================================================================
# Helper: persistir mensagem + broadcast pros membros online
# =====================================================================
async def _persistir_e_broadcastar(channel_id: int, user_id: int, user_name: str,
                                   content: str, reply_to_id: Optional[int],
                                   attachments: Optional[List[dict]] = None):
    """attachments: lista de dicts {tipo, arquivo, nome_original, mime, tamanho}.
    Parses @mentions do content (<@user_id>) e cria registros em chat_mentions."""
    # Mentions: parse + filtra so quem realmente eh membro do canal
    mention_ids = list({int(uid) for uid in _MENTION_RE.findall(content or "")})
    membros = _listar_membros_canal(channel_id)
    membros_set = set(membros)
    mention_ids = [uid for uid in mention_ids if uid in membros_set]

    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            INSERT INTO chat_messages (channel_id, user_id, content, reply_to_id)
            VALUES (%s, %s, %s, %s)
        """, (channel_id, user_id, content, reply_to_id))
        msg_id = cur.lastrowid

        # Anexos
        atts_out: List[dict] = []
        if attachments:
            for a in attachments:
                cur.execute("""
                    INSERT INTO chat_attachments (message_id, tipo, arquivo, nome_original, mime, tamanho)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (msg_id, a.get("tipo", "image"), a["arquivo"],
                      a.get("nome_original"), a.get("mime"), a.get("tamanho")))
                atts_out.append({"id": cur.lastrowid, "message_id": msg_id, **a})

        # Mentions
        if mention_ids:
            cur.executemany(
                "INSERT IGNORE INTO chat_mentions (message_id, user_id) VALUES (%s, %s)",
                [(msg_id, uid) for uid in mention_ids])

        # Reply preview (busca o autor + trecho original)
        reply_to = None
        if reply_to_id:
            cur.execute("""
                SELECT m.id, m.user_id, m.content, m.deletado_em
                FROM chat_messages m WHERE m.id = %s
            """, (reply_to_id,))
            r = cur.fetchone()
            if r:
                u = _enriquecer_users([r["user_id"]]).get(r["user_id"], {})
                reply_to = {
                    "id": r["id"],
                    "author_name": u.get("name"),
                    "content_preview": ("(mensagem apagada)" if r["deletado_em"]
                                        else (r["content"] or "")[:160]),
                }
        conn.commit()
    finally:
        cur.close(); conn.close()

    payload = {
        "type": "message",
        "channel_id": channel_id,
        "id": msg_id,
        "content": content,
        "reply_to_id": reply_to_id,
        "reply_to": reply_to,
        "criado_em": datetime.utcnow().isoformat(),
        "author": {"id": user_id, "name": user_name},
        "attachments": atts_out,
        "mentions": mention_ids,
        "reactions": [],
    }
    await manager.send_to_users(membros, payload)

    # Push notification pros membros OFFLINE (nao conectados ao WS) —
    # quem esta online ja recebeu via WS + tem Notification API in-tab.
    if _PUSH_ENABLED:
        online = set(manager.online_users())
        offline_targets = [uid for uid in membros if uid != user_id and uid not in online]
        if offline_targets:
            # Busca nome do canal pra titulo amigavel
            cnome = "Mensagem"
            try:
                conn2 = get_chat_db_or_404()
                cur2 = conn2.cursor(dictionary=True)
                cur2.execute("SELECT tipo, nome FROM chat_channels WHERE id=%s", (channel_id,))
                ch = cur2.fetchone()
                cur2.close(); conn2.close()
                if ch:
                    if ch["tipo"] == "dm":
                        titulo = user_name or "Mensagem"
                    else:
                        titulo = f"{user_name or 'Alguem'} em #{ch['nome'] or 'canal'}"
                    cnome = titulo
            except Exception:
                cnome = user_name or "Mensagem"
            preview = (content or "")[:140] or ("📷 Enviou uma imagem" if atts_out else "")
            url = f"/SistemaCPE/web/pages/chat.html"
            tag = f"cpe-chat-{channel_id}"
            # Roda em executor pra nao bloquear event loop
            asyncio.create_task(asyncio.to_thread(
                _enviar_push_async, offline_targets, cnome, preview, url, tag))
    return payload


# =====================================================================
# Upload de imagem: POST /channels/{id}/upload (multipart)
# =====================================================================
@router.post("/channels/{channel_id}/upload")
async def upload_imagem(channel_id: int, request: Request,
                        file: UploadFile = File(...),
                        caption: Optional[str] = ""):
    """Faz upload de uma imagem, cria msg no canal com a imagem como anexo
    (caption opcional vai como content da msg)."""
    user = _user_from_request(request)
    if not _usuario_pertence_ao_canal(user["id"], channel_id):
        raise HTTPException(status_code=403, detail="Voce nao e membro deste canal")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _CHAT_IMG_EXTS:
        raise HTTPException(status_code=400,
                            detail=f"Extensao nao permitida ({ext}). Use: {', '.join(sorted(_CHAT_IMG_EXTS))}")

    _UPLOAD_CHAT_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f"ch{channel_id}_{_uuid.uuid4().hex[:14]}{ext}"
    destino = _UPLOAD_CHAT_ROOT / filename
    size = 0
    limit = _MAX_CHAT_IMG_MB * 1024 * 1024
    with open(destino, "wb") as out:
        while True:
            chunk = await file.read(64 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                out.close()
                destino.unlink(missing_ok=True)
                raise HTTPException(status_code=413,
                                    detail=f"Imagem maior que {_MAX_CHAT_IMG_MB} MB")
            out.write(chunk)

    arquivo_url = f"{_UPLOAD_CHAT_URL_BASE}/{filename}"
    attachment = {
        "tipo": "image",
        "arquivo": arquivo_url,
        "nome_original": file.filename,
        "mime": file.content_type or "image/*",
        "tamanho": size,
    }
    msg_payload = await _persistir_e_broadcastar(
        channel_id=channel_id, user_id=user["id"],
        user_name=user.get("name"), content=(caption or ""),
        reply_to_id=None, attachments=[attachment],
    )
    return {"success": True, "message": msg_payload}


# =====================================================================
# 2D: Pin de mensagem + busca de mensagens
# =====================================================================
@router.post("/messages/{message_id}/pin")
async def toggle_pin(message_id: int, request: Request):
    """Toggle pin. Qualquer membro do canal pode (escolha simples). Se
    quiser restringir depois, basta checar role no canal."""
    user = _user_from_request(request)
    m = _msg_e_canal_ou_404(message_id)
    if m["deletado_em"]:
        raise HTTPException(status_code=400, detail="Mensagem apagada nao pode ser fixada")
    if not _usuario_pertence_ao_canal(user["id"], m["channel_id"]):
        raise HTTPException(status_code=403, detail="Voce nao e membro do canal")

    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT pinned_at FROM chat_messages WHERE id=%s", (message_id,))
        atual = cur.fetchone()
        ja_fixada = atual and atual["pinned_at"] is not None
        if ja_fixada:
            cur.execute("UPDATE chat_messages SET pinned_at=NULL WHERE id=%s", (message_id,))
            pinned = False
        else:
            cur.execute("UPDATE chat_messages SET pinned_at=NOW() WHERE id=%s", (message_id,))
            pinned = True
        conn.commit()
    finally:
        cur.close(); conn.close()

    payload = {
        "type": "pin_changed",
        "channel_id": m["channel_id"],
        "message_id": message_id,
        "pinned": pinned,
    }
    membros = _listar_membros_canal(m["channel_id"])
    await manager.send_to_users(membros, payload)
    return {"success": True, "pinned": pinned}


@router.get("/channels/{channel_id}/pinned")
def listar_pinadas(channel_id: int, request: Request):
    """Retorna todas as msgs fixadas do canal (mais recentes primeiro)."""
    user = _user_from_request(request)
    if not _usuario_pertence_ao_canal(user["id"], channel_id):
        raise HTTPException(status_code=403, detail="Voce nao e membro do canal")
    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, user_id, content, criado_em, pinned_at, editado_em
            FROM chat_messages
            WHERE channel_id=%s AND pinned_at IS NOT NULL AND deletado_em IS NULL
            ORDER BY pinned_at DESC LIMIT 50
        """, (channel_id,))
        msgs = cur.fetchall()
        users_map = _enriquecer_users(list({m["user_id"] for m in msgs}))
        for m in msgs:
            u = users_map.get(m["user_id"], {})
            m["author"] = {"id": m["user_id"], "name": u.get("name"), "email": u.get("email")}
        return {"success": True, "messages": msgs}
    finally:
        cur.close(); conn.close()


@router.get("/channels/{channel_id}/search")
def buscar_mensagens(channel_id: int, request: Request,
                     q: str = Query(..., min_length=2, max_length=200)):
    """Busca msgs por texto (fulltext + fallback LIKE pra termos curtos).
    Retorna ate 50 resultados mais recentes."""
    user = _user_from_request(request)
    if not _usuario_pertence_ao_canal(user["id"], channel_id):
        raise HTTPException(status_code=403, detail="Voce nao e membro do canal")
    termo = q.strip()
    if not termo:
        return {"success": True, "messages": []}
    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        # FULLTEXT IN BOOLEAN MODE — termos curtos ainda podem nao casar
        # (default min ft_word_len = 4). Fallback pra LIKE se vier vazio.
        cur.execute("""
            SELECT id, user_id, content, criado_em, pinned_at, editado_em
            FROM chat_messages
            WHERE channel_id=%s AND deletado_em IS NULL
              AND MATCH(content) AGAINST (%s IN BOOLEAN MODE)
            ORDER BY criado_em DESC LIMIT 50
        """, (channel_id, termo + "*"))
        msgs = cur.fetchall()
        if not msgs:
            # Fallback LIKE pra termos curtos
            cur.execute("""
                SELECT id, user_id, content, criado_em, pinned_at, editado_em
                FROM chat_messages
                WHERE channel_id=%s AND deletado_em IS NULL
                  AND content LIKE %s
                ORDER BY criado_em DESC LIMIT 50
            """, (channel_id, f"%{termo}%"))
            msgs = cur.fetchall()
        users_map = _enriquecer_users(list({m["user_id"] for m in msgs}))
        for m in msgs:
            u = users_map.get(m["user_id"], {})
            m["author"] = {"id": m["user_id"], "name": u.get("name"), "email": u.get("email")}
        return {"success": True, "messages": msgs, "query": termo}
    finally:
        cur.close(); conn.close()


# =====================================================================
# Reactions: toggle emoji em uma mensagem
# =====================================================================
class ReacaoBody(BaseModel):
    emoji: str = Field(..., min_length=1, max_length=16)


@router.post("/messages/{message_id}/reactions")
async def toggle_reacao(message_id: int, body: ReacaoBody, request: Request):
    """Toggle: se o user ja reagiu com esse emoji, remove; senao, adiciona.
    Faz broadcast via WS pros membros do canal."""
    user = _user_from_request(request)
    m = _msg_e_canal_ou_404(message_id)
    if m["deletado_em"]:
        raise HTTPException(status_code=400, detail="Mensagem apagada nao aceita reacoes")
    if not _usuario_pertence_ao_canal(user["id"], m["channel_id"]):
        raise HTTPException(status_code=403, detail="Voce nao e membro do canal")

    emoji = body.emoji.strip()
    if not emoji:
        raise HTTPException(status_code=400, detail="Emoji vazio")

    conn = get_chat_db_or_404()
    cur = conn.cursor()
    added: bool
    try:
        cur.execute("""
            SELECT 1 FROM chat_message_reactions
            WHERE message_id=%s AND user_id=%s AND emoji=%s
        """, (message_id, user["id"], emoji))
        ja_tinha = cur.fetchone() is not None

        if ja_tinha:
            cur.execute("""
                DELETE FROM chat_message_reactions
                WHERE message_id=%s AND user_id=%s AND emoji=%s
            """, (message_id, user["id"], emoji))
            added = False
        else:
            cur.execute("""
                INSERT INTO chat_message_reactions (message_id, user_id, emoji)
                VALUES (%s, %s, %s)
            """, (message_id, user["id"], emoji))
            added = True
        conn.commit()
    finally:
        cur.close(); conn.close()

    payload = {
        "type": "reaction",
        "channel_id": m["channel_id"],
        "message_id": message_id,
        "emoji": emoji,
        "user_id": user["id"],
        "added": added,
    }
    membros = _listar_membros_canal(m["channel_id"])
    await manager.send_to_users(membros, payload)
    return {"success": True, "added": added}


# =====================================================================
# Cleanup: apaga imagens com criado_em < hoje - 90d (admin only)
# =====================================================================
@router.post("/admin/cleanup-imagens")
def cleanup_imagens_antigas(request: Request, dias: int = Query(_CLEANUP_DIAS, ge=7, le=3650)):
    """Remove imagens (disco + DB) anteriores a `dias` dias. Padrao 90.
    Restrito a ADMIN/TI/MANAGER."""
    user = _user_from_request(request)
    if user.get("role") not in ("ADMIN", "TI", "MANAGER"):
        raise HTTPException(status_code=403, detail="Restrito a administradores")

    limite = datetime.utcnow() - timedelta(days=dias)
    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    apagadas_disco = 0
    apagadas_db = 0
    try:
        cur.execute("""
            SELECT id, arquivo FROM chat_attachments WHERE criado_em < %s
        """, (limite,))
        rows = cur.fetchall()
        for r in rows:
            rel = (r["arquivo"] or "").replace(_UPLOAD_CHAT_URL_BASE, "").lstrip("/")
            if rel:
                try:
                    (_UPLOAD_CHAT_ROOT / rel).unlink(missing_ok=True)
                    apagadas_disco += 1
                except Exception as e:
                    logger.warning(f"[CLEANUP] falha removendo {rel}: {e}")
        if rows:
            ids = [r["id"] for r in rows]
            placeholders = ",".join(["%s"] * len(ids))
            cur.execute(f"DELETE FROM chat_attachments WHERE id IN ({placeholders})", ids)
            apagadas_db = cur.rowcount
            conn.commit()
    finally:
        cur.close(); conn.close()
    return {"success": True, "apagadas_disco": apagadas_disco, "apagadas_db": apagadas_db,
            "limite": limite.isoformat(), "dias": dias}


# =====================================================================
# WebSocket: /api/chat/ws?token=...
# =====================================================================
@router.websocket("/ws")
async def chat_ws(websocket: WebSocket):
    # CRITICO: sempre fazer accept() PRIMEIRO. Chamar close() antes do
    # accept faz o Starlette mandar HTTP 403 no handshake (cliente ve
    # WS rejeitado, nao consegue ler reason). Bug em prod ate 2026-05-29.
    try:
        await websocket.accept()
    except Exception as e:
        logger.error(f"[CHAT-WS] accept fail: {type(e).__name__}: {e}")
        return

    token = websocket.query_params.get("token", "")
    user_id, user = None, None
    try:
        user_id = parse_session_token(token) if token else None
        user = get_user_by_id(user_id) if user_id else None
    except Exception as e:
        logger.error(f"[CHAT-WS] auth check fail: {type(e).__name__}: {e}")

    if not user:
        try:
            await websocket.send_text(json.dumps(
                {"type": "error", "detail": "Token ausente ou invalido"}))
            await websocket.close(code=4401, reason="Auth invalida")
        except Exception:
            pass
        return

    # Registra no manager (sem chamar manager.connect porque ele faz accept)
    manager._conns.setdefault(user_id, set()).add(websocket)
    logger.warning(f"[CHAT-WS] +user {user_id} (conexoes={len(manager._conns[user_id])} "
                   f"total_users={len(manager._conns)})")
    # Presence em executor pra nao bloquear event loop com query MySQL sincrona
    try:
        await asyncio.to_thread(manager._set_presence, user_id, "online")
    except Exception as e:
        logger.warning(f"[CHAT-WS] presence fail (nao critico): {e}")
    try:
        # Envia hello inicial
        await websocket.send_text(json.dumps({
            "type": "hello",
            "user_id": user_id,
            "online_users": manager.online_users(),
        }))

        # Replay de chamada pendente — se algum invite foi mandado pra mim
        # enquanto eu nao estava conectado (e ainda esta no TTL), reenvia
        # agora. Resolve o caso "fechou aba, abriu de novo durante a call".
        pending = _chamada_pendente(user_id)
        if pending:
            await websocket.send_text(json.dumps({
                "type": "call_invite",
                "from_user_id": pending["from_user_id"],
                "from_user_name": pending["from_user_name"],
                "channel_id": pending["channel_id"],
                "replay": True,
            }))

        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "detail": "JSON invalido"}))
                continue

            msg_type = data.get("type")
            if msg_type == "send":
                channel_id = data.get("channel_id")
                content = (data.get("content") or "").strip()
                if not channel_id or not content:
                    await websocket.send_text(json.dumps(
                        {"type": "error", "detail": "channel_id e content obrigatorios"}))
                    continue
                if not _usuario_pertence_ao_canal(user_id, channel_id):
                    await websocket.send_text(json.dumps(
                        {"type": "error", "detail": "Voce nao e membro deste canal"}))
                    continue
                reply_id = data.get("reply_to_id")
                try:
                    reply_id = int(reply_id) if reply_id else None
                except (TypeError, ValueError):
                    reply_id = None
                await _persistir_e_broadcastar(
                    channel_id=channel_id, user_id=user_id,
                    user_name=user.get("name"), content=content,
                    reply_to_id=reply_id,
                )
            elif msg_type in ("call_invite", "call_accept", "call_reject",
                              "call_cancel", "call_ringing"):
                target = data.get("to_user_id")
                if not target:
                    continue
                target = int(target)
                if not get_user_by_id(target):
                    await websocket.send_text(json.dumps(
                        {"type": "error", "detail": "Usuario destinatario nao encontrado"}))
                    continue

                payload = {
                    **data,
                    "from_user_id": user_id,
                    "from_user_name": user.get("name"),
                }

                # LOG explicito (warning pra aparecer em prod stderr)
                online_agora = manager.online_users()
                logger.warning(f"[CALL] {msg_type} from={user_id}({user.get('name')}) "
                               f"to={target} online_count={len(online_agora)} "
                               f"target_online={target in online_agora}")

                # Estado em memoria das pending calls + push notification
                if msg_type == "call_invite":
                    ch_id = data.get("channel_id")
                    _registrar_chamada(target, user_id, user.get("name") or "", int(ch_id) if ch_id else 0)
                    # Dispara push notification (cobre caso "destinatario sem chat.html aberto")
                    if _PUSH_ENABLED:
                        titulo = f"📞 {user.get('name') or 'Alguém'} está te ligando"
                        corpo = "Toque pra atender"
                        url = f"/SistemaCPE/web/pages/chat.html?incoming_call={user_id}"
                        tag = f"cpe-call-{user_id}"
                        asyncio.create_task(asyncio.to_thread(
                            _enviar_push_async, [target], titulo, corpo, url, tag))
                elif msg_type in ("call_cancel",):
                    _cancelar_chamada(target, user_id)
                elif msg_type in ("call_accept", "call_reject"):
                    # No accept/reject, quem cancela e o destinatario respondendo
                    # ao caller (que esta em data.to_user_id). O originador do
                    # invite original tinha target=me. Cleanup correto:
                    _cancelar_chamada(user_id)  # eu (callee) respondi, limpa

                await manager.send_to_users([target], payload)
            elif msg_type in ("voice_offer", "voice_answer", "voice_ice"):
                # Signaling 1-a-1 entre peers. Frontend manda {to_user_id, ...}
                target_uid = data.get("to_user_id")
                if not target_uid:
                    continue
                await manager.send_to_users([int(target_uid)], {
                    **data,
                    "from_user_id": user_id,
                })
            elif msg_type == "voice_state":
                # Toggle mic/cam/share — propaga pra todos os membros do canal
                ch_id = data.get("channel_id")
                if not ch_id:
                    continue
                mic   = 1 if data.get("mic_on") else 0
                cam   = 1 if data.get("cam_on") else 0
                share = 1 if data.get("share_on") else 0
                try:
                    conn = get_chat_db_or_404()
                    cur  = conn.cursor()
                    cur.execute("""
                        UPDATE chat_voice_sessions
                        SET mic_on=%s, cam_on=%s, share_on=%s
                        WHERE channel_id=%s AND user_id=%s
                    """, (mic, cam, share, ch_id, user_id))
                    conn.commit()
                    cur.close(); conn.close()
                except Exception as e:
                    logger.warning(f"[VOICE] update state fail: {e}")
                membros = _listar_membros_canal(ch_id)
                await manager.send_to_users(membros, {
                    "type": "voice_state",
                    "channel_id": ch_id,
                    "user_id": user_id,
                    "mic_on": bool(mic), "cam_on": bool(cam), "share_on": bool(share),
                })
            elif msg_type == "typing":
                # Broadcast pros OUTROS membros (exclui o proprio)
                channel_id = data.get("channel_id")
                if not channel_id or not _usuario_pertence_ao_canal(user_id, channel_id):
                    continue
                membros = [u for u in _listar_membros_canal(channel_id) if u != user_id]
                if membros:
                    await manager.send_to_users(membros, {
                        "type": "typing",
                        "channel_id": channel_id,
                        "user_id": user_id,
                        "user_name": user.get("name"),
                    })
            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            else:
                await websocket.send_text(json.dumps(
                    {"type": "error", "detail": f"tipo desconhecido: {msg_type}"}))
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
    except Exception as e:
        logger.exception(f"[CHAT-WS] erro user={user_id}: {e}")
        manager.disconnect(user_id, websocket)
