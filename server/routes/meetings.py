"""
Salas de reuniao temporarias (estilo Google Meet / Jitsi).

- Qualquer usuario logado pode criar uma sala.
- Sala tem URL publica: /SistemaCPE/web/pages/meet.html?code=XYZ
- Externos abrem o link, digitam nome, ficam em SALA DE ESPERA.
- Host aprova/rejeita guests via lista. Internos entram direto.
- WebRTC mesh igual ao chat-voice (audio/video/screen).
- Sala persistente ate host clicar "Encerrar".

WS dedicado pra meeting: /api/meetings/ws?code=XYZ&token=YYY
  - token pode ser:
    * cookie/header de sessao do CPE (user logado)
    * guest_token gerado ao requestar entrada (externo)
"""
import json
import logging
import asyncio
import secrets
from typing import Optional, Dict, Set, List
from datetime import datetime

from fastapi import (
    APIRouter, WebSocket, WebSocketDisconnect, HTTPException,
    Request, Query,
)
from pydantic import BaseModel, Field

from database import get_chat_db_or_404, get_db_or_404
from security import parse_session_token, get_user_by_id

router = APIRouter(prefix="/api/meetings", tags=["meetings"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Geracao de codes / tokens
# ---------------------------------------------------------------------
_CODE_ALPHABET = "abcdefghijkmnpqrstuvwxyz23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
_CODE_LEN = 10


def _gen_code(cur, tentativas: int = 8) -> str:
    for _ in range(tentativas):
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LEN))
        cur.execute("SELECT 1 FROM chat_meeting_rooms WHERE codigo=%s LIMIT 1", (code,))
        if not cur.fetchone():
            return code
    raise HTTPException(status_code=500, detail="Nao foi possivel gerar code unico")


def _gen_token() -> str:
    return secrets.token_urlsafe(32)


def _gen_peer_id() -> str:
    return secrets.token_urlsafe(20)[:32]


# ---------------------------------------------------------------------
# Helpers de auth
# ---------------------------------------------------------------------
def _user_from_request(request: Request) -> Optional[dict]:
    """Resolve user logado a partir do cookie/header. Retorna None se nao
    logado (NAO levanta exception — meeting permite acesso de guests)."""
    token = request.cookies.get("cpe_session") or request.headers.get("X-Auth-Token", "")
    if not token:
        return None
    uid = parse_session_token(token)
    if not uid:
        return None
    return get_user_by_id(uid)


def _exigir_user(request: Request) -> dict:
    user = _user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Sessao requerida")
    return user


def _meeting_by_code(code: str) -> Optional[dict]:
    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, codigo, nome, criado_por, criado_em, encerrada_em
            FROM chat_meeting_rooms WHERE codigo=%s
        """, (code,))
        return cur.fetchone()
    finally:
        cur.close(); conn.close()


def _user_eh_host(meeting: dict, user_id: int) -> bool:
    return meeting and meeting["criado_por"] == user_id


# ---------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------
class MeetingCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=120)


class RequestEntryBody(BaseModel):
    guest_name: Optional[str] = Field(None, max_length=80,
                                       description="Nome do externo (NULL pra users logados)")


class UpdateStateBody(BaseModel):
    mic_on: Optional[bool] = None
    cam_on: Optional[bool] = None
    share_on: Optional[bool] = None


# ---------------------------------------------------------------------
# Connection Manager (WS) — proprio do meetings, isolado do chat
# ---------------------------------------------------------------------
class MeetingConnManager:
    """Mantem mapa de meeting_id -> { peer_id: WebSocket }.
    Cada peer (interno ou externo) tem 1 WS aberta enquanto na sala."""
    def __init__(self):
        self._rooms: Dict[int, Dict[str, WebSocket]] = {}

    async def connect(self, meeting_id: int, peer_id: str, ws: WebSocket):
        # NAO faz ws.accept() — o handler ja aceitou no inicio. Double-accept
        # em Starlette dropa a conexao silenciosamente (causa loop 1006).
        self._rooms.setdefault(meeting_id, {})[peer_id] = ws
        print(f"[MEET-WS] +peer {peer_id[:8]} meeting={meeting_id} "
              f"total_na_sala={len(self._rooms[meeting_id])}", flush=True)

    def disconnect(self, meeting_id: int, peer_id: str):
        room = self._rooms.get(meeting_id)
        if room and peer_id in room:
            del room[peer_id]
            if not room:
                del self._rooms[meeting_id]
        print(f"[MEET-WS] -peer {peer_id[:8]} meeting={meeting_id}", flush=True)

    async def send_to_peer(self, meeting_id: int, peer_id: str, payload: dict):
        room = self._rooms.get(meeting_id) or {}
        ws = room.get(peer_id)
        if not ws:
            return
        try:
            await ws.send_text(json.dumps(payload, default=str))
        except Exception as e:
            logger.warning(f"[MEET-WS] send fail {peer_id[:8]}: {e}")
            self.disconnect(meeting_id, peer_id)

    async def broadcast(self, meeting_id: int, payload: dict, except_peer: Optional[str] = None):
        room = self._rooms.get(meeting_id) or {}
        msg = json.dumps(payload, default=str)
        dead: List[str] = []
        for pid, ws in list(room.items()):
            if except_peer and pid == except_peer:
                continue
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(pid)
        for pid in dead:
            self.disconnect(meeting_id, pid)


manager = MeetingConnManager()


# ---------------------------------------------------------------------
# REST: criar/listar/encerrar
# ---------------------------------------------------------------------
@router.post("/")
def criar_meeting(body: MeetingCreate, request: Request):
    user = _exigir_user(request)
    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        code = _gen_code(cur)
        cur.execute("""
            INSERT INTO chat_meeting_rooms (codigo, nome, criado_por)
            VALUES (%s, %s, %s)
        """, (code, body.nome.strip(), user["id"]))
        mid = cur.lastrowid
        conn.commit()
    finally:
        cur.close(); conn.close()
    return {
        "success": True,
        "meeting_id": mid,
        "codigo": code,
        "nome": body.nome.strip(),
        "url_path": f"/SistemaCPE/web/pages/meet.html?code={code}",
    }


@router.get("/info/{code}")
def info_meeting(code: str, request: Request):
    """Preview publico da sala — chamavel sem login. Retorna nome + host_nome
    e flag sou_host (False se nao logado ou se nao for o host)."""
    m = _meeting_by_code(code)
    if not m:
        raise HTTPException(status_code=404, detail="Sala nao encontrada")
    if m["encerrada_em"]:
        return {
            "success": True,
            "meeting": {
                "codigo": code,
                "nome": m["nome"],
                "encerrada": True,
            },
        }
    # Nome do host
    host_nome = ""
    plus = get_db_or_404()
    pcur = plus.cursor(dictionary=True)
    try:
        pcur.execute("SELECT name FROM users WHERE id=%s", (m["criado_por"],))
        u = pcur.fetchone()
        host_nome = u.get("name") if u else ""
    finally:
        pcur.close(); plus.close()
    user = _user_from_request(request)
    sou_host = bool(user and user["id"] == m["criado_por"])
    return {
        "success": True,
        "meeting": {
            "codigo": code,
            "nome": m["nome"],
            "host_nome": host_nome,
            "encerrada": False,
            "sou_host": sou_host,
            "logado": bool(user),
            "meu_nome": user.get("name") if user else None,
        },
    }


@router.delete("/{code}")
async def encerrar_meeting(code: str, request: Request):
    user = _exigir_user(request)
    m = _meeting_by_code(code)
    if not m:
        raise HTTPException(status_code=404, detail="Sala nao encontrada")
    if not _user_eh_host(m, user["id"]):
        raise HTTPException(status_code=403, detail="So o host pode encerrar")
    if m["encerrada_em"]:
        return {"success": True, "noop": True}

    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE chat_meeting_rooms SET encerrada_em=NOW() WHERE id=%s",
                    (m["id"],))
        # Limpa participantes ativos
        cur.execute("DELETE FROM chat_meeting_participants WHERE meeting_id=%s",
                    (m["id"],))
        conn.commit()
    finally:
        cur.close(); conn.close()

    # Notifica todos os peers WS pra fechar
    await manager.broadcast(m["id"], {"type": "meeting_ended"})
    return {"success": True}


@router.get("/{code}/participants")
def listar_participantes(code: str, request: Request):
    """Lista participantes (dentro + aguardando). So host."""
    user = _exigir_user(request)
    m = _meeting_by_code(code)
    if not m:
        raise HTTPException(status_code=404, detail="Sala nao encontrada")
    if not _user_eh_host(m, user["id"]):
        raise HTTPException(status_code=403, detail="So o host pode listar")
    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT peer_id, user_id, guest_name, status, mic_on, cam_on,
                   share_on, entrou_em
            FROM chat_meeting_participants WHERE meeting_id=%s
        """, (m["id"],))
        rows = cur.fetchall()
    finally:
        cur.close(); conn.close()
    # Enriquece nomes pra users logados
    uids = [r["user_id"] for r in rows if r["user_id"]]
    nomes: Dict[int, str] = {}
    if uids:
        plus = get_db_or_404()
        pcur = plus.cursor(dictionary=True)
        try:
            ph = ",".join(["%s"] * len(uids))
            pcur.execute(f"SELECT id, name FROM users WHERE id IN ({ph})", uids)
            for u in pcur.fetchall():
                nomes[u["id"]] = u["name"]
        finally:
            pcur.close(); plus.close()
    for r in rows:
        r["display_name"] = (nomes.get(r["user_id"]) if r["user_id"] else r["guest_name"]) or "?"
    return {"success": True, "participants": rows}


# ---------------------------------------------------------------------
# Request-entry: solicita entrada (interno OU externo)
# ---------------------------------------------------------------------
@router.post("/{code}/request-entry")
async def request_entry(code: str, body: RequestEntryBody, request: Request):
    """Cria entrada em chat_meeting_participants com status='aguardando'.
    Se for o host (logado), status='dentro' direto.
    Se logado nao-host, status='dentro' direto tambem (interno do sistema
    pula a sala de espera; sala de espera serve so pra externos).
    Se guest externo, retorna guest_token + status='aguardando'.

    Retorna: { peer_id, guest_token?, status, sou_host }
    """
    m = _meeting_by_code(code)
    if not m:
        raise HTTPException(status_code=404, detail="Sala nao encontrada")
    if m["encerrada_em"]:
        raise HTTPException(status_code=410, detail="Sala encerrada")

    user = _user_from_request(request)
    peer_id = _gen_peer_id()
    guest_token = None
    guest_name = None
    user_id = None
    sou_host = False

    # Regra: SO o host entra direto. Todos os outros (internos do CPE OU
    # externos) ficam aguardando aprovacao na sala de espera. O host
    # controla quem entra (consistente com a decisao "sala de espera com
    # aprovacao do host").
    if user:
        user_id = user["id"]
        sou_host = (user["id"] == m["criado_por"])
        status = "dentro" if sou_host else "aguardando"
    else:
        # Externo precisa de nome
        if not body.guest_name or not body.guest_name.strip():
            raise HTTPException(status_code=400, detail="Nome obrigatorio pra guests externos")
        guest_name = body.guest_name.strip()[:80]
        guest_token = _gen_token()
        status = "aguardando"

    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO chat_meeting_participants
              (meeting_id, peer_id, user_id, guest_name, guest_token, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (m["id"], peer_id, user_id, guest_name, guest_token, status))
        conn.commit()
    finally:
        cur.close(); conn.close()

    print(f"[MEET] request-entry code={code} peer={peer_id[:8]} "
          f"user_id={user_id} guest='{guest_name}' status={status} "
          f"sou_host={sou_host}", flush=True)

    # Se externo (aguardando), notifica HOST se estiver online via WS
    if status == "aguardando":
        await manager.broadcast(m["id"], {
            "type": "meeting_join_request",
            "peer_id": peer_id,
            "guest_name": guest_name,
        })

    return {
        "success": True,
        "peer_id": peer_id,
        "guest_token": guest_token,
        "status": status,
        "sou_host": sou_host,
        "display_name": (user["name"] if user else guest_name),
        "meeting_id": m["id"],
        "meeting_nome": m["nome"],
    }


# ---------------------------------------------------------------------
# Host aprova / rejeita guest
# ---------------------------------------------------------------------
@router.post("/{code}/approve/{peer_id}")
async def approve_guest(code: str, peer_id: str, request: Request):
    user = _exigir_user(request)
    m = _meeting_by_code(code)
    if not m:
        raise HTTPException(status_code=404, detail="Sala nao encontrada")
    if not _user_eh_host(m, user["id"]):
        raise HTTPException(status_code=403, detail="So o host pode aprovar")
    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE chat_meeting_participants
            SET status='dentro'
            WHERE meeting_id=%s AND peer_id=%s AND status='aguardando'
        """, (m["id"], peer_id))
        conn.commit()
        affected = cur.rowcount
    finally:
        cur.close(); conn.close()
    if not affected:
        raise HTTPException(status_code=404, detail="Participante nao esta aguardando")
    # Notifica o guest (esta com WS aberta no lobby)
    await manager.send_to_peer(m["id"], peer_id, {
        "type": "meeting_join_approved",
    })
    # Notifica resto da sala que tem novo participante (eles vao iniciar
    # offers; o guest faz answer)
    await manager.broadcast(m["id"], {
        "type": "meeting_participant_joined",
        "peer_id": peer_id,
    }, except_peer=peer_id)
    return {"success": True}


@router.post("/{code}/reject/{peer_id}")
async def reject_guest(code: str, peer_id: str, request: Request):
    user = _exigir_user(request)
    m = _meeting_by_code(code)
    if not m:
        raise HTTPException(status_code=404, detail="Sala nao encontrada")
    if not _user_eh_host(m, user["id"]):
        raise HTTPException(status_code=403, detail="So o host pode rejeitar")
    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE chat_meeting_participants SET status='rejeitado'
            WHERE meeting_id=%s AND peer_id=%s
        """, (m["id"], peer_id))
        conn.commit()
    finally:
        cur.close(); conn.close()
    await manager.send_to_peer(m["id"], peer_id, {
        "type": "meeting_join_rejected",
    })
    # Forca disconnect do peer
    manager.disconnect(m["id"], peer_id)
    return {"success": True}


# ---------------------------------------------------------------------
# Leave: sai da sala
# ---------------------------------------------------------------------
@router.post("/{code}/leave/{peer_id}")
async def leave_meeting(code: str, peer_id: str, request: Request):
    m = _meeting_by_code(code)
    if not m:
        return {"success": True, "noop": True}
    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM chat_meeting_participants WHERE meeting_id=%s AND peer_id=%s",
            (m["id"], peer_id))
        conn.commit()
    finally:
        cur.close(); conn.close()
    await manager.broadcast(m["id"], {
        "type": "meeting_participant_left",
        "peer_id": peer_id,
    })
    manager.disconnect(m["id"], peer_id)
    return {"success": True}


# ---------------------------------------------------------------------
# WebSocket: signaling WebRTC + eventos da sala
# Aceita 3 modos de auth (em ordem):
#   1. session_token (header X-Auth-Token ou cookie cpe_session) → user logado
#   2. guest_token query param → guest aprovado
#   3. anonimo NAO aceito
# ---------------------------------------------------------------------
@router.websocket("/ws")
async def meeting_ws(websocket: WebSocket):
    code = websocket.query_params.get("code", "").strip()
    peer_id = websocket.query_params.get("peer_id", "").strip()
    guest_token = websocket.query_params.get("guest_token", "").strip()
    session_token = (
        websocket.query_params.get("token", "")
        or websocket.headers.get("x-auth-token", "")
        or websocket.cookies.get("cpe_session", "")
    ).strip()

    print(f"[MEET-WS] connect attempt code={code} peer={peer_id[:8] if peer_id else 'NONE'} "
          f"has_session_tok={bool(session_token)} has_guest_tok={bool(guest_token)}", flush=True)
    await websocket.accept()

    if not code or not peer_id:
        await websocket.send_text(json.dumps(
            {"type": "error", "detail": "code e peer_id obrigatorios"}))
        await websocket.close(code=1008)
        return

    m = _meeting_by_code(code)
    if not m:
        await websocket.send_text(json.dumps({"type": "error", "detail": "Sala nao encontrada"}))
        await websocket.close(code=1008); return
    if m["encerrada_em"]:
        await websocket.send_text(json.dumps({"type": "meeting_ended"}))
        await websocket.close(code=1000); return

    # Resolve participante
    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT user_id, guest_name, guest_token, status
            FROM chat_meeting_participants
            WHERE meeting_id=%s AND peer_id=%s
        """, (m["id"], peer_id))
        part = cur.fetchone()
    finally:
        cur.close(); conn.close()
    if not part:
        await websocket.send_text(json.dumps(
            {"type": "error", "detail": "Peer nao registrado (request-entry primeiro)"}))
        await websocket.close(code=1008); return

    # Valida auth
    auth_ok = False
    user_id = None
    if part["user_id"]:
        # Interno — precisa de session_token valido com aquele user_id
        if session_token:
            uid = parse_session_token(session_token)
            if uid == part["user_id"]:
                auth_ok = True
                user_id = uid
    else:
        # Guest — precisa de guest_token
        if guest_token and guest_token == part["guest_token"]:
            auth_ok = True

    if not auth_ok:
        print(f"[MEET-WS] auth FAIL peer={peer_id[:8]} "
              f"part.user_id={part['user_id']} part.has_guest_token={bool(part['guest_token'])} "
              f"recv_session={bool(session_token)} recv_guest={bool(guest_token)}", flush=True)
        await websocket.send_text(json.dumps({"type": "error", "detail": "Auth invalida"}))
        await websocket.close(code=1008); return
    print(f"[MEET-WS] auth OK peer={peer_id[:8]} status={part['status']} user_id={part['user_id']}", flush=True)

    # Se eh externo e ainda esta 'aguardando', mantem WS aberta (lobby)
    # ate o host aprovar. Se rejeitado, recebe meeting_join_rejected e
    # WS fecha.
    if part["status"] == "rejeitado":
        await websocket.send_text(json.dumps({"type": "meeting_join_rejected"}))
        await websocket.close(code=1000); return

    # Conecta (status pode ser 'aguardando' ou 'dentro')
    await manager.connect(m["id"], peer_id, websocket)

    # Manda lista de participantes ativos pro recem-conectado
    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT peer_id, user_id, guest_name, mic_on, cam_on, share_on
            FROM chat_meeting_participants
            WHERE meeting_id=%s AND status='dentro' AND peer_id != %s
        """, (m["id"], peer_id))
        outros = cur.fetchall()
    finally:
        cur.close(); conn.close()
    # Enriquece com nome pra users logados
    uids = [o["user_id"] for o in outros if o["user_id"]]
    nomes: Dict[int, str] = {}
    if uids:
        plus = get_db_or_404()
        pcur = plus.cursor(dictionary=True)
        try:
            ph = ",".join(["%s"] * len(uids))
            pcur.execute(f"SELECT id, name FROM users WHERE id IN ({ph})", uids)
            for u in pcur.fetchall():
                nomes[u["id"]] = u["name"]
        finally:
            pcur.close(); plus.close()
    for o in outros:
        o["display_name"] = (nomes.get(o["user_id"]) if o["user_id"] else o["guest_name"]) or "?"

    await websocket.send_text(json.dumps({
        "type": "hello",
        "meu_peer_id": peer_id,
        "status": part["status"],
        "sou_host": bool(user_id and user_id == m["criado_por"]),
        "participantes": outros,
        "meeting_nome": m["nome"],
    }, default=str))

    # Se sou host, mando tambem lista de "aguardando" pra UI mostrar
    if user_id and user_id == m["criado_por"]:
        conn = get_chat_db_or_404()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("""
                SELECT peer_id, guest_name
                FROM chat_meeting_participants
                WHERE meeting_id=%s AND status='aguardando'
            """, (m["id"],))
            aguardando = cur.fetchall()
        finally:
            cur.close(); conn.close()
        if aguardando:
            await websocket.send_text(json.dumps({
                "type": "meeting_pending_list",
                "pending": aguardando,
            }, default=str))

    # Notifica resto da sala que entrei (se status='dentro')
    if part["status"] == "dentro":
        await manager.broadcast(m["id"], {
            "type": "meeting_participant_joined",
            "peer_id": peer_id,
            "user_id": part["user_id"],
            "guest_name": part["guest_name"],
            "display_name": (nomes.get(part["user_id"]) if part["user_id"]
                             else part["guest_name"]) or "?",
        }, except_peer=peer_id)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except Exception:
                continue
            t = data.get("type")
            if t in ("meeting_offer", "meeting_answer", "meeting_ice"):
                # Signaling 1-a-1: roteia pro to_peer_id
                to_peer = data.get("to_peer_id")
                if to_peer:
                    await manager.send_to_peer(m["id"], to_peer, {
                        **data,
                        "from_peer_id": peer_id,
                    })
            elif t == "meeting_state":
                # Atualiza mic/cam/share + broadcast pros outros
                mic = bool(data.get("mic_on"))
                cam = bool(data.get("cam_on"))
                shr = bool(data.get("share_on"))
                conn = get_chat_db_or_404()
                cur = conn.cursor()
                try:
                    cur.execute("""
                        UPDATE chat_meeting_participants
                        SET mic_on=%s, cam_on=%s, share_on=%s
                        WHERE meeting_id=%s AND peer_id=%s
                    """, (int(mic), int(cam), int(shr), m["id"], peer_id))
                    conn.commit()
                finally:
                    cur.close(); conn.close()
                await manager.broadcast(m["id"], {
                    "type": "meeting_state",
                    "peer_id": peer_id,
                    "mic_on": mic, "cam_on": cam, "share_on": shr,
                }, except_peer=peer_id)
            elif t == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            # outros types sao ignorados silenciosamente
    except WebSocketDisconnect:
        print(f"[MEET-WS] disconnect normal peer={peer_id[:8]}", flush=True)
    except Exception as e:
        import traceback
        print(f"[MEET-WS] ERRO peer={peer_id[:8]}: {e}\n{traceback.format_exc()}", flush=True)
    finally:
        manager.disconnect(m["id"], peer_id)
        # Cleanup APENAS pra peer que ja estava 'dentro'. Pending ('aguardando')
        # nao deleta — permite ao guest reabrir aba sem perder o pedido + nao
        # remove do "pending" do host. Pra abandonar de fato, frontend chama
        # POST /leave/{peer_id} explicito.
        try:
            conn = get_chat_db_or_404()
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM chat_meeting_participants "
                "WHERE meeting_id=%s AND peer_id=%s AND status='dentro'",
                (m["id"], peer_id))
            conn.commit()
            cur.close(); conn.close()
        except Exception:
            pass
        # Notifica resto APENAS se era um participante 'dentro' que saiu
        if part["status"] == "dentro":
            try:
                await manager.broadcast(m["id"], {
                    "type": "meeting_participant_left",
                    "peer_id": peer_id,
                })
            except Exception:
                pass
