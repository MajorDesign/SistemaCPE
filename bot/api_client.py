"""
Cliente HTTP async que o bot Discord usa pra falar com a CPEControlAPI.

Todas as chamadas mandam o header X-Discord-Bot-Key (autentica que quem
esta chamando e o proprio bot). Chamadas que agem em nome de um user
adicionam X-Auth-Token com um session token curto emitido pelo endpoint
/api/discord/link/{id}/session.
"""

import os
import json as _json
import logging
from typing import Optional
from urllib.parse import quote

import aiohttp

logger = logging.getLogger("cpe-bot.api")

API_BASE = os.environ.get("CPE_API_BASE", "http://127.0.0.1:8000").rstrip("/")
BOT_KEY  = os.environ.get("DISCORD_BOT_API_KEY", "")

if not BOT_KEY:
    logger.error("[API] DISCORD_BOT_API_KEY nao configurada — todas as chamadas vao falhar 401")


class ApiError(Exception):
    """Erro estruturado do backend (extrai `detail` do JSON de erro FastAPI)."""
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(f"HTTP {status}: {detail}")


async def _request(method: str, path: str, *, headers: Optional[dict] = None,
                    json: Optional[dict] = None) -> dict:
    url = f"{API_BASE}{path}"
    h = {"X-Discord-Bot-Key": BOT_KEY}
    if headers:
        h.update(headers)
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as sess:
        async with sess.request(method, url, headers=h, json=json) as r:
            text = await r.text()
            if r.status >= 400:
                # Tenta extrair "detail" do JSON de erro do FastAPI
                try:
                    detail = _json.loads(text).get("detail", text[:200])
                except Exception:
                    detail = text[:200]
                if isinstance(detail, list):
                    # Pydantic validation errors vem como lista
                    detail = "; ".join(str(d) for d in detail)
                raise ApiError(r.status, str(detail))
            return _json.loads(text) if text else {}


# ---------- Discord link endpoints ---------------------------------

async def link_challenge(discord_id: str, email: str) -> dict:
    return await _request("POST", "/api/discord/link/challenge",
                          json={"discord_id": discord_id, "email": email})


async def link_verify(discord_id: str, code: str) -> dict:
    return await _request("POST", "/api/discord/link/verify",
                          json={"discord_id": discord_id, "code": code})


async def get_link(discord_id: str) -> dict:
    return await _request("GET", f"/api/discord/link/{discord_id}")


async def get_session(discord_id: str) -> dict:
    return await _request("POST", f"/api/discord/link/{discord_id}/session")


# ---------- CPE Control API (em nome do user vinculado) ------------

async def get_ticket_by_numero(numero: str, token: str, usuario_id: int) -> dict:
    return await _request(
        "GET",
        f"/api/tickets/by-numero/{quote(numero, safe='')}?usuario_id={usuario_id}",
        headers={"X-Auth-Token": token},
    )


async def list_interacoes(ticket_id: int, token: str) -> list:
    r = await _request(
        "GET",
        f"/api/ticket-interacoes/{ticket_id}",
        headers={"X-Auth-Token": token},
    )
    # Endpoint retorna lista pura
    return r if isinstance(r, list) else r.get("items", [])
