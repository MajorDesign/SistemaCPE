"""
Chat GIFs — proxy pra Giphy (e Klipy no futuro).

Chaves de API ficam SO no backend (nao expor no cliente). Endpoints:
- GET /api/chat/gifs/providers        → lista providers configurados
- GET /api/chat/gifs/trending?provider=giphy&limit=24&offset=0
- GET /api/chat/gifs/search?provider=giphy&q=X&limit=24&offset=0

Cache in-memory 5 min por (endpoint, provider, query, offset).
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, Query, Request

from security import parse_session_token, get_user_by_id

router = APIRouter(prefix="/api/chat/gifs", tags=["chat-gifs"])
logger = logging.getLogger(__name__)

_CACHE_TTL = 5 * 60  # 5 min
_cache: dict[str, tuple[float, dict]] = {}


def _exigir_user(request: Request) -> dict:
    token = request.cookies.get("cpe_session") or request.headers.get("X-Auth-Token", "")
    if not token:
        raise HTTPException(status_code=401, detail="Sessao requerida")
    uid = parse_session_token(token)
    if not uid:
        raise HTTPException(status_code=401, detail="Token invalido")
    u = get_user_by_id(uid)
    if not u:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado")
    return u


def _cache_get(key: str) -> Optional[dict]:
    hit = _cache.get(key)
    if not hit:
        return None
    ts, data = hit
    if time.time() - ts > _CACHE_TTL:
        _cache.pop(key, None)
        return None
    return data


def _cache_set(key: str, data: dict):
    _cache[key] = (time.time(), data)


# --------------------------------------------------------------
# Giphy
# --------------------------------------------------------------
def _giphy_key() -> str:
    k = (os.getenv("GIPHY_API_KEY") or "").strip()
    if not k:
        raise HTTPException(status_code=503, detail="Giphy nao configurado no servidor")
    return k


def _giphy_normalize(item: dict) -> dict:
    """Converte item da API Giphy num formato compacto pro cliente.
    Priorizamos WebP no preview (leve) e mp4 no original (menor que GIF)."""
    imgs = item.get("images") or {}
    fh = imgs.get("fixed_height") or {}
    preview_url = fh.get("webp") or fh.get("url") or ""
    original = imgs.get("original") or {}
    # Usamos o url do original (GIF) pra manter compatibilidade — se
    # quisermos otimizar depois, usar 'mp4' + <video>.
    original_url = original.get("url") or ""
    return {
        "id": item.get("id"),
        "title": item.get("title") or "",
        "provider": "giphy",
        "preview_url": preview_url,
        "original_url": original_url,
        "width": int(fh.get("width") or 0),
        "height": int(fh.get("height") or 0),
    }


@router.get("/providers")
def providers(request: Request):
    _exigir_user(request)
    return {
        "success": True,
        "providers": [
            {"id": "giphy", "label": "Giphy", "enabled": bool((os.getenv("GIPHY_API_KEY") or "").strip())},
            {"id": "klipy", "label": "Klipy", "enabled": bool((os.getenv("KLIPY_API_KEY") or "").strip())},
        ],
    }


@router.get("/trending")
def trending(
    request: Request,
    provider: str = Query("giphy"),
    limit: int = Query(24, ge=1, le=50),
    offset: int = Query(0, ge=0, le=5000),
):
    _exigir_user(request)
    if provider != "giphy":
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' nao suportado (por enquanto)")

    key = f"trending:giphy:{limit}:{offset}"
    cached = _cache_get(key)
    if cached:
        return cached

    try:
        r = requests.get(
            "https://api.giphy.com/v1/gifs/trending",
            params={
                "api_key": _giphy_key(),
                "limit": limit,
                "offset": offset,
                "rating": "g",  # safe-for-work
            },
            timeout=10,
        )
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Giphy HTTP {r.status_code}")
        payload = r.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"[gifs/trending] falha: {e}")
        raise HTTPException(status_code=502, detail="Falha ao consultar Giphy")

    items = [_giphy_normalize(x) for x in (payload.get("data") or [])]
    resp = {"success": True, "gifs": items, "provider": "giphy",
            "pagination": payload.get("pagination") or {}}
    _cache_set(key, resp)
    return resp


@router.get("/search")
def search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=100),
    provider: str = Query("giphy"),
    limit: int = Query(24, ge=1, le=50),
    offset: int = Query(0, ge=0, le=5000),
):
    _exigir_user(request)
    if provider != "giphy":
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' nao suportado (por enquanto)")

    q_clean = q.strip()
    if not q_clean:
        raise HTTPException(status_code=400, detail="Query vazia")

    key = f"search:giphy:{q_clean.lower()}:{limit}:{offset}"
    cached = _cache_get(key)
    if cached:
        return cached

    try:
        r = requests.get(
            "https://api.giphy.com/v1/gifs/search",
            params={
                "api_key": _giphy_key(),
                "q": q_clean,
                "limit": limit,
                "offset": offset,
                "rating": "g",
                "lang": "pt",
            },
            timeout=10,
        )
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Giphy HTTP {r.status_code}")
        payload = r.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"[gifs/search] falha: {e}")
        raise HTTPException(status_code=502, detail="Falha ao consultar Giphy")

    items = [_giphy_normalize(x) for x in (payload.get("data") or [])]
    resp = {"success": True, "gifs": items, "provider": "giphy",
            "pagination": payload.get("pagination") or {}}
    _cache_set(key, resp)
    return resp
