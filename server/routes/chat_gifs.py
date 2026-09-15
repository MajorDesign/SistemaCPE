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
    """Converte item da API Giphy num formato compacto pro cliente."""
    imgs = item.get("images") or {}
    fh = imgs.get("fixed_height") or {}
    preview_url = fh.get("webp") or fh.get("url") or ""
    original = imgs.get("original") or {}
    original_url = original.get("url") or ""
    return {
        "id": str(item.get("id")),
        "title": item.get("title") or "",
        "provider": "giphy",
        "preview_url": preview_url,
        "original_url": original_url,
        "width": int(fh.get("width") or 0),
        "height": int(fh.get("height") or 0),
    }


# --------------------------------------------------------------
# Klipy — API key vai como PATH param na URL: /api/v1/{KEY}/gifs/...
# --------------------------------------------------------------
def _klipy_key() -> str:
    k = (os.getenv("KLIPY_API_KEY") or "").strip()
    if not k:
        raise HTTPException(status_code=503, detail="Klipy nao configurado no servidor")
    return k


def _klipy_pick_variant(file_root: dict, size_pref: list[str], fmt_pref: list[str]) -> dict:
    """Escolhe primeira variante disponivel de acordo com preferencia
    de tamanho ('sm','md','hd','xs') e formato ('webp','gif','mp4')."""
    for size in size_pref:
        node = file_root.get(size) or {}
        for fmt in fmt_pref:
            v = node.get(fmt)
            if v and v.get("url"):
                return v
    return {}


def _klipy_normalize(item: dict) -> dict:
    """Klipy response: item.file.{hd|md|sm|xs}.{gif|webp|mp4|...}.
    Preview: preferir sm/webp (leve). Original: hd/gif (compat maxima)."""
    file_root = item.get("file") or {}
    preview = _klipy_pick_variant(file_root, ["sm", "md", "xs", "hd"], ["webp", "gif"])
    original = _klipy_pick_variant(file_root, ["hd", "md", "sm"], ["gif", "webp"])
    return {
        "id": str(item.get("id") or item.get("slug") or ""),
        "title": item.get("title") or "",
        "provider": "klipy",
        "preview_url": preview.get("url", ""),
        "original_url": original.get("url", ""),
        "width": int(preview.get("width") or 0),
        "height": int(preview.get("height") or 0),
    }


def _klipy_call(path: str, params: dict) -> dict:
    """Chama Klipy e valida payload comum. Retorna a lista de items."""
    url = f"https://api.klipy.com/api/v1/{_klipy_key()}/{path.lstrip('/')}"
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Klipy HTTP {r.status_code}")
        payload = r.json()
        if not payload.get("result"):
            errs = payload.get("errors") or {}
            raise HTTPException(status_code=502, detail=f"Klipy: {errs}")
        return payload.get("data") or {}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"[klipy] falha: {e}")
        raise HTTPException(status_code=502, detail="Falha ao consultar Klipy")


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


_ALLOWED_PROVIDERS = ("giphy", "klipy")


@router.get("/trending")
def trending(
    request: Request,
    provider: str = Query("giphy"),
    limit: int = Query(24, ge=1, le=50),
    offset: int = Query(0, ge=0, le=5000),
):
    _exigir_user(request)
    if provider not in _ALLOWED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' nao suportado")

    key = f"trending:{provider}:{limit}:{offset}"
    cached = _cache_get(key)
    if cached:
        return cached

    if provider == "giphy":
        try:
            r = requests.get(
                "https://api.giphy.com/v1/gifs/trending",
                params={"api_key": _giphy_key(), "limit": limit, "offset": offset, "rating": "g"},
                timeout=10,
            )
            if r.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Giphy HTTP {r.status_code}")
            payload = r.json()
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"[gifs/trending] giphy: {e}")
            raise HTTPException(status_code=502, detail="Falha ao consultar Giphy")
        items = [_giphy_normalize(x) for x in (payload.get("data") or [])]
    else:  # klipy
        # Klipy usa 'page' + 'per_page' em vez de offset. Convertemos.
        page = (offset // limit) + 1
        data = _klipy_call("gifs/trending", {"page": page, "per_page": limit})
        items = [_klipy_normalize(x) for x in (data.get("data") or [])]

    resp = {"success": True, "gifs": items, "provider": provider}
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
    if provider not in _ALLOWED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' nao suportado")

    q_clean = q.strip()
    if not q_clean:
        raise HTTPException(status_code=400, detail="Query vazia")

    key = f"search:{provider}:{q_clean.lower()}:{limit}:{offset}"
    cached = _cache_get(key)
    if cached:
        return cached

    if provider == "giphy":
        try:
            r = requests.get(
                "https://api.giphy.com/v1/gifs/search",
                params={"api_key": _giphy_key(), "q": q_clean, "limit": limit,
                        "offset": offset, "rating": "g", "lang": "pt"},
                timeout=10,
            )
            if r.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Giphy HTTP {r.status_code}")
            payload = r.json()
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"[gifs/search] giphy: {e}")
            raise HTTPException(status_code=502, detail="Falha ao consultar Giphy")
        items = [_giphy_normalize(x) for x in (payload.get("data") or [])]
    else:  # klipy
        page = (offset // limit) + 1
        data = _klipy_call("gifs/search", {"q": q_clean, "page": page, "per_page": limit})
        items = [_klipy_normalize(x) for x in (data.get("data") or [])]

    resp = {"success": True, "gifs": items, "provider": provider}
    _cache_set(key, resp)
    return resp
