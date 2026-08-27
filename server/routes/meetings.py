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


class ScheduleInviteeIn(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    email: str = Field(..., min_length=5, max_length=200)


class ScheduleCreate(BaseModel):
    titulo: str = Field(..., min_length=2, max_length=150)
    descricao: Optional[str] = Field(None, max_length=2000)
    start_at: str = Field(..., description="ISO 8601 local BR (ex: 2026-08-20T14:30)")
    duracao_min: int = Field(30, ge=5, le=480, description="duracao em minutos (5 a 480)")
    invitees: List[ScheduleInviteeIn] = Field(default_factory=list)


class ScheduleUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=2, max_length=150)
    descricao: Optional[str] = Field(None, max_length=2000)
    start_at: Optional[str] = None
    duracao_min: Optional[int] = Field(None, ge=5, le=480)
    invitees: Optional[List[ScheduleInviteeIn]] = None


class ScheduleCancel(BaseModel):
    motivo: Optional[str] = Field(None, max_length=300)


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

    def disconnect(self, meeting_id: int, peer_id: str, only_if_ws: Optional[WebSocket] = None):
        """Remove peer do mapa. Se `only_if_ws` for passado, so remove se a WS
        registrada for exatamente essa — evita a race em que WS1 caiu, WS2 (nova
        do reconnect) ja assumiu o slot, e o finally de WS1 iria dropar WS2."""
        room = self._rooms.get(meeting_id)
        if not room or peer_id not in room:
            print(f"[MEET-WS] -peer {peer_id[:8]} noop (nao estava no mapa)", flush=True)
            return
        if only_if_ws is not None and room[peer_id] is not only_if_ws:
            # WS ja foi substituida pela nova conexao do reconnect — nao mexer.
            print(f"[MEET-WS] -peer {peer_id[:8]} SKIP (ws antiga; ha reconnect ativo)",
                  flush=True)
            return
        del room[peer_id]
        if not room:
            del self._rooms[meeting_id]
        print(f"[MEET-WS] -peer {peer_id[:8]} meeting={meeting_id}", flush=True)

    async def send_to_peer(self, meeting_id: int, peer_id: str, payload: dict):
        room = self._rooms.get(meeting_id) or {}
        ws = room.get(peer_id)
        if not ws:
            # Log detalhado pra diagnostico (era silent fail antes)
            other_peers = list(room.keys())
            print(f"[MEET-WS] send_to_peer FAIL peer={peer_id[:8]} type={payload.get('type')} "
                  f"— peer nao esta no room. peers_no_room={len(other_peers)} "
                  f"{[p[:8] for p in other_peers]}", flush=True)
            return
        try:
            await ws.send_text(json.dumps(payload, default=str))
            print(f"[MEET-WS] send_to_peer OK peer={peer_id[:8]} type={payload.get('type')}",
                  flush=True)
        except Exception as e:
            logger.warning(f"[MEET-WS] send fail {peer_id[:8]}: {e}")
            self.disconnect(meeting_id, peer_id, only_if_ws=ws)

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
# TURN / STUN — gera ICE servers efêmeros via Cloudflare Realtime TURN
# Cache em memoria: 1 fetch real a cada ~50min (TTL 1h na CF, renova
# 10min antes do expire). Sem env config -> fallback STUN-only.
# ---------------------------------------------------------------------

import os
import time as _time

_ICE_CACHE: dict = {"ice_servers": None, "expires_at": 0.0}

_ICE_STUN_FALLBACK = [
    {"urls": ["stun:stun.l.google.com:19302"]},
    {"urls": ["stun:stun1.l.google.com:19302"]},
]


def _fetch_cloudflare_turn() -> Optional[list]:
    """Chama API do Cloudflare Realtime TURN. Retorna iceServers ou None."""
    key_id = (os.getenv("CLOUDFLARE_TURN_KEY_ID") or "").strip()
    token  = (os.getenv("CLOUDFLARE_TURN_KEY_TOKEN") or "").strip()
    if not key_id or not token:
        return None
    try:
        import requests as _requests
        r = _requests.post(
            f"https://rtc.live.cloudflare.com/v1/turn/keys/{key_id}/credentials/generate-ice-servers",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"ttl": 3600},   # 1 hora
            timeout=8,
        )
        if r.status_code != 201:
            logger.warning(f"[TURN] CF retornou HTTP {r.status_code}: {r.text[:200]}")
            return None
        data = r.json()
        ice = data.get("iceServers")
        if not isinstance(ice, list) or not ice:
            logger.warning(f"[TURN] CF response sem iceServers: {data}")
            return None
        return ice
    except Exception as e:
        logger.warning(f"[TURN] erro chamando CF: {e}")
        return None


# ---------------------------------------------------------------------
# ATA DE REUNIAO — transcript via Web Speech (client-side) + resumo
# via Gemini (Google Generative AI free tier).
#
# Em memoria, durante a gravacao: ATAS_EM_GRAVACAO[meeting_id] =
# {"ata_id": int, "falas": [{"at": isostr, "autor": str, "texto": str,
# "lang": str}]}. No /stop, serializa pro DB + dispara LLM em thread.
# ---------------------------------------------------------------------

ATAS_EM_GRAVACAO: dict = {}     # meeting_id -> {ata_id, falas}


def _gemini_gerar_ata(transcript_text: str) -> Optional[str]:
    """Chama Gemini Free Tier pra resumir o transcript em ata markdown.
    Retorna o markdown OU None se nao tiver API key OU se a chamada falhar.
    """
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        return None
    if not transcript_text or not transcript_text.strip():
        return None

    prompt = (
        "Voce eh um secretario de reunioes. Dado o transcript abaixo de uma "
        "reuniao corporativa, gere uma ATA em markdown estruturada em portugues "
        "brasileiro com as seguintes secoes (use # e ## como cabecalhos):\n\n"
        "1. Resumo executivo (2-3 frases do que foi a reuniao)\n"
        "2. Topicos discutidos (lista com bullets)\n"
        "3. Decisoes tomadas (se houver, lista)\n"
        "4. Acoes pendentes (lista com responsavel quando mencionado e prazo se mencionado)\n"
        "5. Proximos passos (se houver)\n\n"
        "Seja conciso e objetivo. Nao invente informacoes que nao estao no transcript. "
        "Se uma secao nao tem conteudo, omita-a.\n\n"
        "---TRANSCRIPT DA REUNIAO---\n"
        f"{transcript_text}\n"
        "---FIM DO TRANSCRIPT---"
    )

    try:
        import requests as _requests
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-flash-latest:generateContent?key=" + api_key
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048,
            },
        }
        r = _requests.post(url, json=body, timeout=60)
        if r.status_code != 200:
            logger.warning(f"[ATA-LLM] Gemini retornou HTTP {r.status_code}: {r.text[:300]}")
            return None
        data = r.json()
        candidates = data.get("candidates") or []
        if not candidates:
            logger.warning(f"[ATA-LLM] Gemini sem candidates: {data}")
            return None
        parts = candidates[0].get("content", {}).get("parts") or []
        if not parts:
            return None
        return (parts[0].get("text") or "").strip() or None
    except Exception as e:
        logger.warning(f"[ATA-LLM] erro chamando Gemini: {e}")
        return None


def _gerar_ata_background(ata_id: int):
    """Roda em thread separada apos /stop. Le falas serializadas do DB,
    monta texto, chama Gemini, persiste ata_gerada + status final."""
    import time as _t
    conn = None
    cur  = None
    try:
        conn = get_chat_db_or_404()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, transcript_bruto FROM chat_meeting_atas WHERE id = %s",
            (ata_id,),
        )
        row = cur.fetchone()
        if not row:
            return
        try:
            falas = json.loads(row.get("transcript_bruto") or "[]")
        except Exception:
            falas = []

        # Monta texto plano: "Fulano (HH:MM): texto"
        linhas = []
        for f in falas:
            autor = f.get("autor") or "Desconhecido"
            at    = (f.get("at") or "")[11:16]   # extrai HH:MM do iso
            txt   = (f.get("texto") or "").strip()
            if not txt: continue
            linhas.append(f"{autor} ({at}): {txt}")
        transcript_text = "\n".join(linhas)

        ata_md = _gemini_gerar_ata(transcript_text)
        if ata_md:
            cur.execute(
                "UPDATE chat_meeting_atas SET ata_gerada=%s, status='pronta', "
                "modelo_llm='gemini-flash-latest' WHERE id=%s",
                (ata_md, ata_id),
            )
        else:
            # Sem LLM disponivel OU falha — salva transcript bruto como
            # ata fallback (markdown simples) e marca 'pronta'.
            fallback = "# Transcript bruto (resumo automatico indisponivel)\n\n"
            fallback += transcript_text or "_(sem falas registradas)_"
            cur.execute(
                "UPDATE chat_meeting_atas SET ata_gerada=%s, status='pronta', "
                "modelo_llm='fallback-bruto' WHERE id=%s",
                (fallback, ata_id),
            )
        conn.commit()
        logger.info(f"[ATA] ata_id={ata_id} processada e marcada 'pronta'")
    except Exception as e:
        logger.error(f"[ATA] erro processando ata_id={ata_id}: {e}")
        try:
            if cur:
                cur.execute(
                    "UPDATE chat_meeting_atas SET status='erro', erro_msg=%s WHERE id=%s",
                    (str(e)[:500], ata_id),
                )
                conn.commit()
        except Exception:
            pass
    finally:
        if cur:  cur.close()
        if conn: conn.close()


# ---------------------------------------------------------------------
# Capacidade maxima de participantes por sala — protege qualidade do
# mesh P2P. Default 8, configuravel via .env (MAX_MEETING_PARTICIPANTS).
# Pra suportar mais precisa SFU — ver [[project_meet_capacidade_max]].
# ---------------------------------------------------------------------

def _max_participants() -> int:
    """Le do .env a cada request (permite ajuste sem restart)."""
    try:
        v = int(os.getenv("MAX_MEETING_PARTICIPANTS", "8"))
        return max(2, v)   # piso de seguranca
    except (TypeError, ValueError):
        return 8


def _count_participantes_dentro(cursor, meeting_id: int) -> int:
    cursor.execute(
        "SELECT COUNT(*) FROM chat_meeting_participants "
        "WHERE meeting_id=%s AND status='dentro'",
        (meeting_id,),
    )
    row = cursor.fetchone()
    return int(row[0]) if row else 0


# ---------------------------------------------------------------------
# Cloudflare Analytics — consumo TURN do mes corrente
# Usa GraphQL callsTurnUsageAdaptiveGroups (dimensao date, sum egress+ingress).
# Cache 15 min pra evitar rate-limit da CF. Requer CLOUDFLARE_ACCOUNT_ID +
# CLOUDFLARE_ANALYTICS_TOKEN no .env — sem essas vars, endpoint retorna
# {available: false} e o frontend esconde o bloco de consumo.
# ---------------------------------------------------------------------

_TURN_USAGE_CACHE: dict = {"data": None, "expires_at": 0.0}
_TURN_USAGE_FREE_GB = 1000  # franquia mensal (grava aqui pra facilitar tuning)


def _fetch_cloudflare_turn_usage() -> Optional[dict]:
    """Chama Cloudflare GraphQL Analytics API. Retorna dict pronto pro
    frontend, ou None se falhou/sem config."""
    acct  = (os.getenv("CLOUDFLARE_ACCOUNT_ID") or "").strip()
    token = (os.getenv("CLOUDFLARE_ANALYTICS_TOKEN") or "").strip()
    if not acct or not token:
        return None

    # Janela: dia 1 do mes atual ate hoje (UTC).
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    since = now.replace(day=1).strftime("%Y-%m-%d")
    until = now.strftime("%Y-%m-%d")
    days_month_total = (now.replace(month=now.month % 12 + 1, day=1) - timedelta(days=1)).day \
                       if now.month != 12 else 31
    day_of_month = now.day

    query = (
        "query ($tag: string!, $since: Date!, $until: Date!) { "
        "  viewer { "
        "    accounts(filter: {accountTag: $tag}) { "
        "      callsTurnUsageAdaptiveGroups("
        "        limit: 500, filter: {date_geq: $since, date_leq: $until}, "
        "        orderBy: [date_ASC]"
        "      ) { "
        "        dimensions { date } "
        "        sum { egressBytes ingressBytes } "
        "      } "
        "    } "
        "  } "
        "}"
    )
    try:
        import requests as _requests
        r = _requests.post(
            "https://api.cloudflare.com/client/v4/graphql",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            json={"query": query,
                  "variables": {"tag": acct, "since": since, "until": until}},
            timeout=10,
        )
        if r.status_code != 200:
            logger.warning(f"[TURN/USAGE] CF HTTP {r.status_code}: {r.text[:200]}")
            return None
        payload = r.json()
        if payload.get("errors"):
            logger.warning(f"[TURN/USAGE] GraphQL erro: {payload['errors']}")
            return None
        buckets = (payload.get("data", {}).get("viewer", {})
                   .get("accounts", [{}])[0]
                   .get("callsTurnUsageAdaptiveGroups", []) or [])
    except Exception as e:
        logger.warning(f"[TURN/USAGE] erro consultando CF: {e}")
        return None

    days: list = []
    total_bytes = 0
    for b in buckets:
        s = b.get("sum", {}) or {}
        egress  = int(s.get("egressBytes") or 0)
        ingress = int(s.get("ingressBytes") or 0)
        total   = egress + ingress
        total_bytes += total
        d = (b.get("dimensions") or {}).get("date")
        if d:
            days.append({"date": d, "bytes": total,
                          "egress": egress, "ingress": ingress})

    gb = total_bytes / (1024 ** 3)
    pct = round((gb / _TURN_USAGE_FREE_GB) * 100, 2) if _TURN_USAGE_FREE_GB else 0.0
    return {
        "available":     True,
        "month_start":   since,
        "month_end":     until,
        "day_of_month":  day_of_month,
        "days_in_month": days_month_total,
        "pct_month_elapsed": round((day_of_month / days_month_total) * 100, 1),
        "total_gb":      round(gb, 4),
        "total_bytes":   total_bytes,
        "free_gb":       _TURN_USAGE_FREE_GB,
        "pct_used":      pct,
        "days":          days,
        "fetched_at":    now.isoformat(),
    }


@router.get("/turn-usage")
def get_turn_usage(request: Request):
    """Retorna consumo TURN do mes corrente (so ADMIN). Cache 15 min."""
    user = _exigir_user(request)  # so autenticado
    role = (user.get("role") or "").upper()
    if role != "ADMIN":
        raise HTTPException(status_code=403,
                            detail="Apenas ADMIN pode ver consumo do TURN.")

    now = _time.time()
    if _TURN_USAGE_CACHE["data"] and now < _TURN_USAGE_CACHE["expires_at"]:
        cached = dict(_TURN_USAGE_CACHE["data"])
        cached["cached"] = True
        return cached

    data = _fetch_cloudflare_turn_usage()
    if data is None:
        # sem config, sem quebrar UI
        return {"available": False,
                "reason": "CLOUDFLARE_ACCOUNT_ID/ANALYTICS_TOKEN nao configurados"}
    _TURN_USAGE_CACHE["data"] = data
    _TURN_USAGE_CACHE["expires_at"] = now + 15 * 60  # 15 min
    data["cached"] = False
    return data


@router.get("/limits")
def meeting_limits():
    """Retorna limites configurados de reuniao pra o frontend exibir
    warnings/bloqueios claros. Sem auth: e info publica de UX."""
    max_p = _max_participants()
    # Warning suave 3 slots antes do MAX (ou na metade se MAX for pequeno).
    warn = max(2, max_p - 3)
    return {
        "max_participants": max_p,
        "warn_threshold": warn,
        "reason": (
            "Reunioes usam WebRTC mesh (todos-com-todos), que degrada em "
            "qualidade e uso de CPU/banda acima de ~5 pessoas. Acima de "
            f"{max_p} participantes, novas entradas sao bloqueadas para "
            "proteger o audio/video de quem ja esta na sala."
        ),
    }


@router.get("/turn-credentials")
async def get_turn_credentials():
    """Retorna {iceServers:[...]} pra ser usado no RTCPeerConnection do cliente.

    Comportamento:
    - Sem CLOUDFLARE_TURN_KEY_ID/TOKEN no .env -> STUN-only (fallback).
    - Com config -> credentials efemeros da Cloudflare (TTL 1h),
      renovados em background a cada ~50min (cache em memoria).
    - Falha na CF -> fallback STUN, log warning, NAO derruba a reuniao.
    """
    now = _time.time()
    if _ICE_CACHE["ice_servers"] and now < _ICE_CACHE["expires_at"]:
        return {"iceServers": _ICE_CACHE["ice_servers"], "source": "cache"}

    # Tenta CF em thread (requests eh sync) pra nao bloquear event loop
    ice = await asyncio.to_thread(_fetch_cloudflare_turn)
    if ice:
        _ICE_CACHE["ice_servers"] = ice
        _ICE_CACHE["expires_at"]  = now + (50 * 60)   # 50 min cache
        return {"iceServers": ice, "source": "cloudflare"}

    # Fallback: STUN-only (mantem comportamento atual sem TURN)
    return {"iceServers": _ICE_STUN_FALLBACK, "source": "stun-fallback"}


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


# ---------------------------------------------------------------------
# AGENDAMENTOS (schedules): reunioes marcadas pra data/hora futura,
# convidados por email. Cada agendamento cria uma sala meeting_rooms
# ja no ato — link vai estavel no email. Cancelamento manda email
# tambem. Lembretes 24h e 15min por background job (meeting_scheduler).
# ---------------------------------------------------------------------

def _parse_start_at(s: str) -> datetime:
    """Aceita 'YYYY-MM-DDTHH:MM' ou 'YYYY-MM-DD HH:MM(:SS)'. Timezone
    tratada como horario local BR (sem tz-info) — evita confusao com
    UTC no MySQL DATETIME que ja e naive."""
    s = (s or "").strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise HTTPException(status_code=400, detail=f"Data/hora invalida: {s!r} — use YYYY-MM-DDTHH:MM")


def _schedule_link(code: str) -> str:
    from config import PUBLIC_BASE_URL
    return f"{PUBLIC_BASE_URL}/SistemaCPE/web/pages/meet.html?code={code}"


def _fetch_schedule(cur, schedule_id: int) -> Optional[dict]:
    cur.execute("""
        SELECT s.*, m.codigo AS meeting_code
          FROM chat_meeting_schedules s
          LEFT JOIN chat_meeting_rooms m ON m.id = s.meeting_id
         WHERE s.id = %s
    """, (schedule_id,))
    return cur.fetchone()


def _fetch_invitees(cur, schedule_id: int) -> List[dict]:
    cur.execute("""
        SELECT id, nome, email, user_id, token, convite_enviado_em, entrou_em
          FROM chat_meeting_schedule_invitees
         WHERE schedule_id = %s
         ORDER BY id
    """, (schedule_id,))
    return cur.fetchall() or []


def _host_nome(user_id: int) -> str:
    plus = get_db_or_404()
    pcur = plus.cursor(dictionary=True)
    try:
        pcur.execute("SELECT name FROM users WHERE id=%s", (user_id,))
        u = pcur.fetchone()
        return (u or {}).get("name") or "CPE Tecnologia"
    finally:
        pcur.close(); plus.close()


def _resolve_internal_user_ids(emails: List[str]) -> Dict[str, int]:
    """Retorna map {email_lower: user_id} pros emails que existem em cpe_plus.users."""
    if not emails:
        return {}
    plus = get_db_or_404()
    pcur = plus.cursor(dictionary=True)
    try:
        placeholders = ",".join(["%s"] * len(emails))
        pcur.execute(
            f"SELECT id, email FROM users WHERE LOWER(email) IN ({placeholders})",
            [e.lower() for e in emails],
        )
        return {r["email"].lower(): r["id"] for r in pcur.fetchall() or []}
    finally:
        pcur.close(); plus.close()


def _enviar_convite(dest_email: str, dest_nome: str, host_nome: str,
                    titulo: str, descricao: Optional[str],
                    start_at: datetime, end_at: datetime, link: str) -> None:
    try:
        from services.email_service import enviar_email, email_meeting_convite
        subject, html = email_meeting_convite(
            dest_nome=dest_nome, host_nome=host_nome,
            titulo=titulo, descricao=descricao or "",
            start_at=start_at, end_at=end_at, link=link,
        )
        enviar_email(dest_email, subject, html)
    except Exception as e:
        logger.warning(f"[MEET-SCHED] falha convite {dest_email}: {e}")


def _enviar_cancelamento(dest_email: str, dest_nome: str, host_nome: str,
                          titulo: str, start_at: datetime, motivo: Optional[str]) -> None:
    try:
        from services.email_service import enviar_email, email_meeting_cancelamento
        subject, html = email_meeting_cancelamento(
            dest_nome=dest_nome, host_nome=host_nome,
            titulo=titulo, start_at=start_at, motivo=motivo or "",
        )
        enviar_email(dest_email, subject, html)
    except Exception as e:
        logger.warning(f"[MEET-SCHED] falha cancelamento {dest_email}: {e}")


@router.post("/schedules")
def criar_schedule(body: ScheduleCreate, request: Request):
    """Cria agendamento + sala. Envia convite pra cada invitee."""
    user = _exigir_user(request)
    start_at = _parse_start_at(body.start_at)
    if start_at < datetime.now():
        raise HTTPException(status_code=400, detail="Data/hora ja passou — agende pra o futuro")
    from datetime import timedelta
    end_at = start_at + timedelta(minutes=body.duracao_min)

    # Dedup convidados por email (case-insensitive)
    seen = set()
    invitees_norm = []
    for inv in body.invitees:
        key = inv.email.strip().lower()
        if not key or "@" not in key or key in seen:
            continue
        seen.add(key)
        invitees_norm.append({"nome": inv.nome.strip()[:120], "email": inv.email.strip()[:200]})

    # Resolve users internos pra linkar user_id
    internal_map = _resolve_internal_user_ids([i["email"] for i in invitees_norm])

    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        # 1) Cria sala (chat_meeting_rooms) — link estavel ate a reuniao rolar
        code = _gen_code(cur)
        cur.execute("""
            INSERT INTO chat_meeting_rooms (codigo, nome, criado_por)
            VALUES (%s, %s, %s)
        """, (code, body.titulo.strip(), user["id"]))
        meeting_id = cur.lastrowid

        # 2) Cria schedule
        cur.execute("""
            INSERT INTO chat_meeting_schedules
                (meeting_id, host_id, titulo, descricao, start_at, end_at, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'agendada')
        """, (
            meeting_id, user["id"],
            body.titulo.strip(),
            (body.descricao or "").strip() or None,
            start_at, end_at,
        ))
        schedule_id = cur.lastrowid

        # 3) Grava invitees com token
        now = datetime.now()
        for inv in invitees_norm:
            token = _gen_token()
            uid_int = internal_map.get(inv["email"].lower())
            cur.execute("""
                INSERT INTO chat_meeting_schedule_invitees
                    (schedule_id, nome, email, user_id, token, convite_enviado_em)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (schedule_id, inv["nome"], inv["email"], uid_int, token, now))

        conn.commit()
    finally:
        cur.close(); conn.close()

    # 4) Envia emails (fora do lock DB — enviar_email e async por default)
    link = _schedule_link(code)
    host = _host_nome(user["id"])
    for inv in invitees_norm:
        _enviar_convite(
            dest_email=inv["email"], dest_nome=inv["nome"],
            host_nome=host, titulo=body.titulo.strip(),
            descricao=body.descricao, start_at=start_at, end_at=end_at,
            link=link,
        )

    return {
        "success": True,
        "schedule_id": schedule_id,
        "meeting_id": meeting_id,
        "codigo": code,
        "link": link,
        "invitees_enviados": len(invitees_norm),
    }


@router.get("/schedules")
def listar_schedules(request: Request, status: Optional[str] = None):
    """Lista MINHAS reunioes agendadas. Filtro por status opcional."""
    user = _exigir_user(request)
    where = ["host_id = %s"]
    params: List = [user["id"]]
    if status and status in ("agendada", "em_andamento", "concluida", "cancelada"):
        where.append("status = %s")
        params.append(status)

    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(f"""
            SELECT s.id, s.titulo, s.descricao, s.start_at, s.end_at, s.status,
                   s.cancelamento_motivo, s.cancelado_em, s.created_at,
                   m.codigo AS meeting_code,
                   (SELECT COUNT(*) FROM chat_meeting_schedule_invitees i
                     WHERE i.schedule_id = s.id) AS total_invitees
              FROM chat_meeting_schedules s
              LEFT JOIN chat_meeting_rooms m ON m.id = s.meeting_id
             WHERE {' AND '.join(where)}
             ORDER BY s.start_at DESC
             LIMIT 200
        """, params)
        rows = cur.fetchall() or []
    finally:
        cur.close(); conn.close()

    for r in rows:
        r["link"] = _schedule_link(r["meeting_code"]) if r.get("meeting_code") else None
    return {"success": True, "schedules": rows}


@router.get("/schedules/{schedule_id}")
def obter_schedule(schedule_id: int, request: Request):
    user = _exigir_user(request)
    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        s = _fetch_schedule(cur, schedule_id)
        if not s:
            raise HTTPException(status_code=404, detail="Agendamento nao encontrado")
        if s["host_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="So o host pode ver este agendamento")
        s["link"] = _schedule_link(s["meeting_code"]) if s.get("meeting_code") else None
        s["invitees"] = _fetch_invitees(cur, schedule_id)
    finally:
        cur.close(); conn.close()
    return {"success": True, "schedule": s}


@router.patch("/schedules/{schedule_id}")
def editar_schedule(schedule_id: int, body: ScheduleUpdate, request: Request):
    """Edita agendamento. Se mudou horario ou lista de convidados, reenvia
    convite pra todos (novos e antigos)."""
    user = _exigir_user(request)
    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    reenviar = False
    novos_convidados: List[dict] = []
    try:
        s = _fetch_schedule(cur, schedule_id)
        if not s:
            raise HTTPException(status_code=404, detail="Agendamento nao encontrado")
        if s["host_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="So o host pode editar")
        if s["status"] != "agendada":
            raise HTTPException(status_code=400, detail=f"Nao e possivel editar (status: {s['status']})")

        sets = []
        params: List = []
        start_at_novo = s["start_at"]
        end_at_novo = s["end_at"]
        if body.titulo is not None:
            sets.append("titulo = %s"); params.append(body.titulo.strip())
        if body.descricao is not None:
            sets.append("descricao = %s"); params.append((body.descricao or "").strip() or None)
        if body.start_at is not None or body.duracao_min is not None:
            from datetime import timedelta
            start_at_novo = _parse_start_at(body.start_at) if body.start_at else s["start_at"]
            if start_at_novo < datetime.now():
                raise HTTPException(status_code=400, detail="Data/hora ja passou")
            dur = body.duracao_min if body.duracao_min else int(
                (s["end_at"] - s["start_at"]).total_seconds() // 60
            )
            end_at_novo = start_at_novo + timedelta(minutes=dur)
            sets.append("start_at = %s"); params.append(start_at_novo)
            sets.append("end_at = %s"); params.append(end_at_novo)
            # Zera flags de lembrete pra reenviar
            sets.append("lembrete_24h_enviado_em = NULL")
            sets.append("lembrete_15min_enviado_em = NULL")
            reenviar = True

        if sets:
            params.append(schedule_id)
            cur.execute(f"UPDATE chat_meeting_schedules SET {', '.join(sets)} WHERE id = %s", params)

        # Substituir lista de invitees se veio
        if body.invitees is not None:
            cur.execute("DELETE FROM chat_meeting_schedule_invitees WHERE schedule_id = %s", (schedule_id,))
            seen = set()
            invitees_norm = []
            for inv in body.invitees:
                key = inv.email.strip().lower()
                if not key or "@" not in key or key in seen:
                    continue
                seen.add(key)
                invitees_norm.append({"nome": inv.nome.strip()[:120], "email": inv.email.strip()[:200]})
            internal_map = _resolve_internal_user_ids([i["email"] for i in invitees_norm])
            now = datetime.now()
            for inv in invitees_norm:
                token = _gen_token()
                uid_int = internal_map.get(inv["email"].lower())
                cur.execute("""
                    INSERT INTO chat_meeting_schedule_invitees
                        (schedule_id, nome, email, user_id, token, convite_enviado_em)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (schedule_id, inv["nome"], inv["email"], uid_int, token, now))
            novos_convidados = invitees_norm
            reenviar = True

        conn.commit()

        # Reenviar convites se preciso (fora do commit)
        if reenviar:
            invitees_to_notify = novos_convidados if novos_convidados else [
                {"nome": r["nome"], "email": r["email"]}
                for r in _fetch_invitees(cur, schedule_id)
            ]
            link = _schedule_link(s["meeting_code"]) if s.get("meeting_code") else None
            host = _host_nome(user["id"])
            titulo_final = body.titulo.strip() if body.titulo is not None else s["titulo"]
            for inv in invitees_to_notify:
                _enviar_convite(
                    dest_email=inv["email"], dest_nome=inv["nome"],
                    host_nome=host, titulo=titulo_final,
                    descricao=body.descricao if body.descricao is not None else s.get("descricao"),
                    start_at=start_at_novo, end_at=end_at_novo,
                    link=link or "",
                )
    finally:
        cur.close(); conn.close()

    return {"success": True}


@router.delete("/schedules/{schedule_id}")
def cancelar_schedule(schedule_id: int, request: Request,
                      motivo: Optional[str] = Query(None, max_length=300)):
    """Cancela agendamento. Marca status='cancelada' e envia email pros invitees."""
    user = _exigir_user(request)
    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    invitees = []
    try:
        s = _fetch_schedule(cur, schedule_id)
        if not s:
            raise HTTPException(status_code=404, detail="Agendamento nao encontrado")
        if s["host_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="So o host pode cancelar")
        if s["status"] == "cancelada":
            return {"success": True, "message": "Ja estava cancelado"}

        cur.execute("""
            UPDATE chat_meeting_schedules
               SET status='cancelada',
                   cancelamento_motivo=%s,
                   cancelado_por=%s,
                   cancelado_em=NOW()
             WHERE id=%s
        """, ((motivo or "").strip() or None, user["id"], schedule_id))

        # Encerrar a sala tambem (evita links "zumbi")
        if s.get("meeting_id"):
            cur.execute(
                "UPDATE chat_meeting_rooms SET encerrada_em=NOW() WHERE id=%s AND encerrada_em IS NULL",
                (s["meeting_id"],),
            )

        invitees = _fetch_invitees(cur, schedule_id)
        conn.commit()
    finally:
        cur.close(); conn.close()

    # Emails de cancelamento
    host = _host_nome(user["id"])
    for inv in invitees:
        _enviar_cancelamento(
            dest_email=inv["email"], dest_nome=inv["nome"],
            host_nome=host, titulo=s["titulo"],
            start_at=s["start_at"], motivo=motivo,
        )
    return {"success": True, "invitees_notificados": len(invitees)}


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
        # Bloqueio de capacidade: se vai entrar direto ('dentro'), conta.
        # Pra quem fica 'aguardando' nao conta agora (so vai pesar quando
        # for aprovado — checado no /approve).
        if status == "dentro":
            max_p = _max_participants()
            atual = _count_participantes_dentro(cur, m["id"])
            if atual >= max_p:
                # 409 (Conflict) e o status certo pra "recurso lotado" —
                # nao e 403 (permissao). Front trata como mensagem clara.
                raise HTTPException(
                    status_code=409,
                    detail=f"Sala cheia: {atual} de {max_p} participantes. "
                           f"Aguarde alguem sair para entrar, ou fale com "
                           f"o organizador pra abrir uma sala nova.",
                )
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
        # Bloqueio de capacidade: nao deixa o host aprovar se ja cheio.
        max_p = _max_participants()
        atual = _count_participantes_dentro(cur, m["id"])
        if atual >= max_p:
            raise HTTPException(
                status_code=403,
                detail=f"Reunião já está no limite máximo ({atual}/{max_p}). "
                       f"Peça pra alguém sair antes de aprovar.",
            )
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
    print(f"[MEET-WS] APROVACAO peer={peer_id[:12]} sala={m['id']} — chamando send_to_peer",
          flush=True)
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
# ATA: start (host) / stop (host) / get / list_me
# ---------------------------------------------------------------------

@router.post("/{code}/ata/start")
async def ata_start(code: str, request: Request):
    user = _exigir_user(request)
    m = _meeting_by_code(code)
    if not m:
        raise HTTPException(status_code=404, detail="Sala nao encontrada")
    if not _user_eh_host(m, user["id"]):
        raise HTTPException(status_code=403, detail="So o host pode gravar a ata")

    # Ja tem ata em gravacao?
    if m["id"] in ATAS_EM_GRAVACAO:
        raise HTTPException(status_code=409, detail="Ata ja esta sendo gravada")

    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO chat_meeting_atas
               (meeting_id, meeting_code, meeting_nome, criada_por_user_id, status)
               VALUES (%s, %s, %s, %s, 'gravando')""",
            (m["id"], code, m.get("nome") or "", user["id"]),
        )
        conn.commit()
        ata_id = cur.lastrowid
    finally:
        cur.close(); conn.close()

    ATAS_EM_GRAVACAO[m["id"]] = {"ata_id": ata_id, "falas": []}
    await manager.broadcast(m["id"], {
        "type": "meeting_ata_started",
        "ata_id": ata_id,
        "by_user_id": user["id"],
        "by_user_name": user.get("name") or "",
    })
    logger.info(f"[ATA] iniciada ata_id={ata_id} meeting={m['id']} por user={user['id']}")
    return {"success": True, "ata_id": ata_id}


@router.post("/{code}/ata/stop")
async def ata_stop(code: str, request: Request):
    user = _exigir_user(request)
    m = _meeting_by_code(code)
    if not m:
        raise HTTPException(status_code=404, detail="Sala nao encontrada")
    if not _user_eh_host(m, user["id"]):
        raise HTTPException(status_code=403, detail="So o host pode encerrar a ata")

    grav = ATAS_EM_GRAVACAO.pop(m["id"], None)
    if not grav:
        raise HTTPException(status_code=409, detail="Nao ha ata sendo gravada")
    ata_id = grav["ata_id"]
    falas  = grav["falas"]

    # Persiste transcript e marca 'gerando'
    conn = get_chat_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute(
            """UPDATE chat_meeting_atas
               SET status='gerando', finalizada_em=NOW(), transcript_bruto=%s
               WHERE id=%s""",
            (json.dumps(falas, default=str), ata_id),
        )
        conn.commit()
    finally:
        cur.close(); conn.close()

    # Avisa todos
    await manager.broadcast(m["id"], {
        "type": "meeting_ata_stopped",
        "ata_id": ata_id,
        "falas_total": len(falas),
    })

    # Dispara geracao em thread (Gemini ate ~30s)
    import threading
    threading.Thread(target=_gerar_ata_background, args=(ata_id,), daemon=True).start()
    logger.info(f"[ATA] stop ata_id={ata_id} falas={len(falas)} -> 'gerando' (background)")
    return {"success": True, "ata_id": ata_id, "status": "gerando", "falas_total": len(falas)}


@router.get("/atas/me")
async def atas_minhas(request: Request):
    """Lista atas criadas pelo usuario logado (mais recentes primeiro)."""
    user = _exigir_user(request)
    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """SELECT id, meeting_code, meeting_nome, status, modelo_llm,
                      iniciada_em, finalizada_em, erro_msg
               FROM chat_meeting_atas
               WHERE criada_por_user_id = %s
               ORDER BY iniciada_em DESC
               LIMIT 100""",
            (user["id"],),
        )
        rows = cur.fetchall()
    finally:
        cur.close(); conn.close()
    return {"atas": rows}


@router.get("/atas/{ata_id}")
async def ata_get(ata_id: int, request: Request):
    """Detalhe de uma ata. Por enquanto so o criador acessa."""
    user = _exigir_user(request)
    conn = get_chat_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """SELECT * FROM chat_meeting_atas WHERE id = %s""",
            (ata_id,),
        )
        row = cur.fetchone()
    finally:
        cur.close(); conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Ata nao encontrada")
    if row["criada_por_user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Sem permissao pra ver esta ata")
    # transcript_bruto vem como JSON string; parse
    try:
        row["transcript_bruto"] = json.loads(row.get("transcript_bruto") or "[]")
    except Exception:
        row["transcript_bruto"] = []
    return row


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
            elif t == "meeting_caption":
                # Legenda (texto transcrito do mic local). Broadcast pros
                # outros peers do room — cada um traduz no proprio cliente
                # pro idioma escolhido. Sem persistencia.
                texto = (data.get("text") or "").strip()[:500]
                if not texto:
                    continue
                source_lang = (data.get("source_lang") or "pt-BR")[:10]
                from_name   = (data.get("from_name") or "")[:80]
                await manager.broadcast(m["id"], {
                    "type": "meeting_caption",
                    "peer_id": peer_id,
                    "text": texto,
                    "source_lang": source_lang,
                    "from_name": from_name,
                }, except_peer=peer_id)
                # Se ata em gravacao, acumula em memoria pra serializar no /stop
                grav = ATAS_EM_GRAVACAO.get(m["id"])
                if grav:
                    from datetime import datetime as _dt
                    grav["falas"].append({
                        "at":    _dt.utcnow().isoformat(timespec="seconds"),
                        "autor": from_name or "Participante",
                        "texto": texto,
                        "lang":  source_lang,
                        "peer_id": peer_id,
                    })
            elif t == "meeting_recording":
                # Sinaliza que o HOST comecou/parou de gravar a sala
                # localmente. Nao persistimos — e volatil por sessao.
                # Apenas o host da sala pode emitir (o proprio front barra
                # pra outros, mas conferimos aqui tambem por seguranca).
                if peer_id and part.get("user_id") and part["user_id"] == m["criado_por"]:
                    await manager.broadcast(m["id"], {
                        "type":      "meeting_recording",
                        "peer_id":   peer_id,
                        "recording": bool(data.get("recording")),
                        "by_name":   (data.get("by_name") or "")[:80],
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
        # Passa a WS especifica pra evitar dropar peer que ja reconectou
        # com uma NOVA WS (race: WS1 cai enquanto WS2 do reconnect ja assumiu).
        manager.disconnect(m["id"], peer_id, only_if_ws=websocket)
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
