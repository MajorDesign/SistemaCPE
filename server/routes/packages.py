"""
Distribuicao de pacotes assinados (multi-arquivo com verificacao SHA256).

Diferente do /api/agents (1 exe auto-instalavel por agente), aqui um
"pacote" e uma colecao de arquivos versionados (ex: VPN OpenVPN = .ovpn
+ .crt). Cliente Windows (.bat) baixa o manifesto, confere os hashes e
aplica localmente.

Endpoints cliente (protegidos por X-Package-Token):
  GET  /api/packages/{slug}/manifest         -> JSON com files + sha256
  GET  /api/packages/{slug}/files/{filename} -> binario do arquivo
  POST /api/packages/{slug}/log              -> recebe log de execucao

Endpoints admin (autenticados via X-Auth-Token do sistema):
  GET  /api/packages                         -> lista pacotes (admin)
  GET  /api/packages/{slug}                  -> detalhes + versoes
  POST /api/packages/{slug}/versions         -> upload multi-file (nova versao)
  GET  /api/packages/{slug}/logs             -> lista execucoes recentes

Armazenamento fisico: E:\\CPE\\packages\\<slug>\\<version>\\<arquivos>
Fora do web/uploads pra evitar bypass do token via download direto.
"""

from __future__ import annotations

import os
import json
import shutil
import hashlib
import logging
import secrets
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from fastapi import (
    APIRouter, HTTPException, status, Header, Path as FPath, Query,
    UploadFile, File, Form, Request,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel

from database import get_db_or_404

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/packages", tags=["packages"])

# =========================================
# CONFIG
# =========================================

# Base de storage FORA do web root — evita bypass do token via download direto.
# Configurable via .env pra facilitar deploy em outros hosts (default E:\CPE\packages).
PACKAGES_ROOT = os.environ.get("PACKAGES_ROOT", r"E:\CPE\packages")

# Limite por arquivo enviado (100 MB — cobre .ovpn/.crt/.exe leves)
MAX_FILE_MB = 100
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024

# Log recebido do cliente — limite generoso mas nao infinito
MAX_LOG_TEXT_BYTES = 2 * 1024 * 1024

# =========================================
# AUTH HELPERS
# =========================================

def _require_package_token(x_package_token: Optional[str]) -> None:
    """Valida a chave compartilhada usada pelos clientes .bat. Sem ela ou
    errada -> 401. Sem config no servidor -> 503 (fail-closed)."""
    expected = os.environ.get("PACKAGE_DOWNLOAD_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Downloads de pacote nao configurados no servidor")
    if not x_package_token:
        raise HTTPException(status_code=401, detail="Header X-Package-Token ausente")
    if not secrets.compare_digest(x_package_token, expected):
        logger.warning("[PKG] token invalido rejeitado")
        raise HTTPException(status_code=401, detail="Token invalido")


def _require_admin_user(request: Request) -> dict:
    """Resolve sessao via X-Auth-Token/cookie e exige role ADMIN/TI."""
    from security import parse_session_token, COOKIE_NAME, get_user_by_id
    token = (
        request.cookies.get(COOKIE_NAME)
        or request.headers.get("X-Auth-Token")
        or request.headers.get("x-auth-token")
    )
    uid = parse_session_token(token) if token else None
    if not uid:
        raise HTTPException(status_code=401, detail="Nao autenticado")
    user = get_user_by_id(uid)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado")
    role = (user.get("role") or "").upper()
    if role not in ("ADMIN", "TI"):
        raise HTTPException(status_code=403, detail="Apenas ADMIN/TI podem publicar pacotes")
    return user


# =========================================
# HELPERS DE ARQUIVO
# =========================================

_SAFE_FILENAME_RE = None  # lazy import re

# Nomes reservados do Windows — sem ext ou com qualquer ext, viram device
# I/O e travam/corrompem o processo. Blacklist explicita.
_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}

def _safe_filename(name: str) -> str:
    """Evita path traversal. Aceita a-z A-Z 0-9 . _ - espaco.
    Rejeita separadores de path e outros caracteres perigosos."""
    import re
    global _SAFE_FILENAME_RE
    if _SAFE_FILENAME_RE is None:
        _SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9._\- ]+$")
    if not name or "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status_code=400, detail=f"Nome de arquivo invalido: {name!r}")
    # `.` ou `..` sozinhos passariam pelo regex acima (não têm .. como substring
    # no primeiro caso; segundo é pego, mas defense-in-depth):
    if name in (".", ".."):
        raise HTTPException(status_code=400, detail=f"Nome reservado: {name!r}")
    if not _SAFE_FILENAME_RE.match(name):
        raise HTTPException(status_code=400, detail=f"Nome de arquivo com caracteres invalidos: {name!r}")
    if len(name) > 255:
        raise HTTPException(status_code=400, detail="Nome de arquivo muito longo")
    # Windows device names (CON, PRN, NUL, COM1..9, LPT1..9) — com ou sem ext.
    base = name.split(".", 1)[0].upper()
    if base in _WINDOWS_RESERVED:
        raise HTTPException(status_code=400, detail=f"Nome reservado do Windows: {name!r}")
    return name


def _assert_inside_root(dest: Path, root: str) -> None:
    """Defesa em profundidade: garante que `dest.resolve()` fica dentro
    de PACKAGES_ROOT.resolve(). Se _safe_filename passar algo esquisito
    (unicode NFKC, symlink no futuro), este check aborta antes do write."""
    try:
        dest_r = dest.resolve()
        root_r = Path(root).resolve()
        dest_r.relative_to(root_r)  # levanta ValueError se fora
    except ValueError:
        raise HTTPException(status_code=400, detail="Path fora do storage")


def _safe_slug(slug: str) -> str:
    import re
    if not re.match(r"^[a-z0-9-]{2,64}$", slug):
        raise HTTPException(status_code=400, detail=f"slug invalido: {slug!r}")
    return slug


def _safe_version(version: str) -> str:
    import re
    if not re.match(r"^[A-Za-z0-9._-]{1,50}$", version):
        raise HTTPException(status_code=400, detail=f"version invalida: {version!r}")
    return version


def _sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _package_dir(slug: str, version: str) -> Path:
    return Path(PACKAGES_ROOT) / slug / version


def _client_ip(request: Request) -> str:
    """Client IP com X-Forwarded-For confiado APENAS quando o socket
    peer for loopback — evita spoofing por qualquer chamador direto.
    A CPEControlAPI recebe trafego externo via Cloudflare Tunnel ->
    Caddy 8081 -> API 8000 (localhost), entao XFF real vem so via
    loopback. Qualquer chamada de outro IP e considerada nao-confiavel."""
    peer = request.client.host if request.client else ""
    if peer in ("127.0.0.1", "::1", "localhost"):
        fwd = request.headers.get("X-Forwarded-For", "")
        if fwd:
            return fwd.split(",")[0].strip()[:45]
    return peer or "unknown"


# =========================================
# ENDPOINTS CLIENTE (X-Package-Token)
# =========================================

@router.get("/{slug}/manifest")
async def get_manifest(
    slug: str = FPath(..., pattern=r"^[a-z0-9-]{2,64}$"),
    x_package_token: Optional[str] = Header(None),
):
    """Manifesto da versao ATUAL do pacote. Cliente usa pra saber o que
    baixar e conferir integridade via SHA256."""
    _require_package_token(x_package_token)
    slug = _safe_slug(slug)

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT p.id, p.slug, p.name, p.current_version_id, "
            "       v.version, v.notes, v.manifest_json, v.created_at "
            "  FROM packages p "
            "  LEFT JOIN package_versions v ON v.id = p.current_version_id "
            " WHERE p.slug = %s LIMIT 1",
            (slug,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Pacote nao encontrado")
        if not row.get("current_version_id"):
            raise HTTPException(status_code=404, detail="Pacote sem versao publicada ainda")

        try:
            manifest = json.loads(row["manifest_json"])
        except Exception:
            raise HTTPException(status_code=500, detail="Manifesto armazenado invalido")
        return manifest
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@router.get("/{slug}/files/{filename}")
async def download_package_file(
    slug: str = FPath(..., pattern=r"^[a-z0-9-]{2,64}$"),
    filename: str = FPath(...),
    x_package_token: Optional[str] = Header(None),
):
    """Serve UM arquivo da versao atual. Cliente ja sabe o nome pelo
    manifesto e confere o SHA256 do que baixou."""
    _require_package_token(x_package_token)
    slug     = _safe_slug(slug)
    filename = _safe_filename(filename)

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT f.disk_path "
            "  FROM packages p "
            "  JOIN package_versions v ON v.id = p.current_version_id "
            "  JOIN package_files f ON f.version_id = v.id "
            " WHERE p.slug = %s AND f.filename = %s LIMIT 1",
            (slug, filename),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado nesta versao")
        path = row["disk_path"]
        if not os.path.exists(path):
            logger.error(f"[PKG] arquivo faltando no disco: {path}")
            raise HTTPException(status_code=500, detail="Arquivo removido do storage — republish necessario")
        return FileResponse(
            path,
            filename=filename,
            media_type="application/octet-stream",
        )
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@router.post("/{slug}/log")
async def submit_execution_log(
    request: Request,
    slug: str = FPath(..., pattern=r"^[a-z0-9-]{2,64}$"),
    version: Optional[str] = Form(None),
    computer: Optional[str] = Form(None),
    user_login: Optional[str] = Form(None),
    success: bool = Form(False),
    log_file: Optional[UploadFile] = File(None),
    log_text: Optional[str] = Form(None),
    x_package_token: Optional[str] = Header(None),
):
    """Cliente .bat envia o log de execucao (arquivo ou texto plano).
    Aceita ambos os formatos pra facilitar a implementacao no bat."""
    _require_package_token(x_package_token)
    slug = _safe_slug(slug)

    # 2026-09-23 (review agente CRITICAL): rejeita body enorme ANTES de
    # ler qualquer coisa. FastAPI/Starlette carregava o UploadFile inteiro
    # em memoria/spool ate o `.read()` — 10GB de body derrubava o worker.
    try:
        content_length = int(request.headers.get("content-length") or 0)
    except ValueError:
        content_length = 0
    if content_length > MAX_LOG_TEXT_BYTES * 2:  # 2x pra margem de multipart overhead
        raise HTTPException(status_code=413, detail=f"Log excede {MAX_LOG_TEXT_BYTES // 1024} KB")

    # Extrai o texto do log — de arquivo (streaming em chunks) ou form field
    body_text = (log_text or "")[:MAX_LOG_TEXT_BYTES]
    if log_file:
        try:
            buf = bytearray()
            while True:
                chunk = await log_file.read(64 * 1024)
                if not chunk:
                    break
                buf.extend(chunk)
                if len(buf) > MAX_LOG_TEXT_BYTES:
                    # Trunca em vez de rejeitar — log parcial ainda e util pra debug
                    buf = buf[:MAX_LOG_TEXT_BYTES]
                    logger.warning(f"[PKG-LOG] log truncado (>{MAX_LOG_TEXT_BYTES} bytes)")
                    break
            body_text = bytes(buf).decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"[PKG-LOG] falha lendo log_file: {e}")

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO package_execution_logs "
            "(package_slug, version, computer, user_login, success, log_text, client_ip) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                slug,
                (version or "")[:50] or None,
                (computer or "")[:120] or None,
                (user_login or "")[:120] or None,
                1 if success else 0,
                body_text or None,
                _client_ip(request)[:45],
            ),
        )
        conn.commit()
        logger.info(
            f"[PKG-LOG] {slug} <- computer={computer or '?'} success={success}"
        )
        return {"ok": True, "id": cursor.lastrowid}
    except Exception as err:
        logger.error(f"[PKG-LOG] falha ao gravar: {err}")
        raise HTTPException(status_code=500, detail="Erro ao registrar log")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# =========================================
# ENDPOINTS ADMIN (X-Auth-Token)
# =========================================

@router.get("")
async def list_packages(request: Request):
    """Lista pacotes cadastrados. Apenas ADMIN/TI."""
    _require_admin_user(request)
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT p.id, p.slug, p.name, p.description, p.updated_at, "
            "       v.version AS current_version, v.created_at AS version_at "
            "  FROM packages p "
            "  LEFT JOIN package_versions v ON v.id = p.current_version_id "
            " ORDER BY p.name"
        )
        rows = cursor.fetchall()
        for r in rows:
            for f in ("updated_at", "version_at"):
                if r.get(f):
                    r[f] = r[f].isoformat()
        return {"packages": rows}
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@router.get("/{slug}")
async def get_package_detail(
    request: Request,
    slug: str = FPath(..., pattern=r"^[a-z0-9-]{2,64}$"),
):
    """Detalhes + historico de versoes + arquivos da versao atual."""
    _require_admin_user(request)
    slug = _safe_slug(slug)
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, slug, name, description, current_version_id, updated_at "
            "  FROM packages WHERE slug = %s LIMIT 1",
            (slug,),
        )
        pkg = cursor.fetchone()
        if not pkg:
            raise HTTPException(status_code=404, detail="Pacote nao encontrado")
        if pkg.get("updated_at"):
            pkg["updated_at"] = pkg["updated_at"].isoformat()

        # Versoes (mais recente primeiro)
        cursor.execute(
            "SELECT v.id, v.version, v.notes, v.created_at, u.name AS created_by_name "
            "  FROM package_versions v "
            "  LEFT JOIN users u ON u.id = v.created_by "
            " WHERE v.package_id = %s "
            " ORDER BY v.created_at DESC LIMIT 20",
            (pkg["id"],),
        )
        versions = cursor.fetchall()
        for v in versions:
            if v.get("created_at"):
                v["created_at"] = v["created_at"].isoformat()
            v["is_current"] = (v["id"] == pkg.get("current_version_id"))

        # Arquivos da versao atual
        files = []
        if pkg.get("current_version_id"):
            cursor.execute(
                "SELECT filename, sha256, size_bytes, position "
                "  FROM package_files "
                " WHERE version_id = %s "
                " ORDER BY position, filename",
                (pkg["current_version_id"],),
            )
            files = cursor.fetchall()

        return {"package": pkg, "versions": versions, "current_files": files}
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@router.post("/{slug}/versions")
async def publish_version(
    request: Request,
    slug: str = FPath(..., pattern=r"^[a-z0-9-]{2,64}$"),
    version: str = Form(...),
    notes: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
):
    """Publica nova versao do pacote (multi-upload).
    Server calcula SHA256, salva os arquivos em disco fora do web root,
    monta o manifesto e marca como current_version."""
    admin = _require_admin_user(request)
    slug    = _safe_slug(slug)
    version = _safe_version(version)

    if not files:
        raise HTTPException(status_code=400, detail="Envie pelo menos 1 arquivo")

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        # Pacote existe?
        cursor.execute("SELECT id FROM packages WHERE slug = %s LIMIT 1", (slug,))
        pkg = cursor.fetchone()
        if not pkg:
            raise HTTPException(status_code=404, detail=f"Pacote '{slug}' nao existe. Cadastre primeiro.")
        package_id = pkg["id"]

        # Versao nao pode conflitar (unique slug+version)
        cursor.execute(
            "SELECT id FROM package_versions WHERE package_id = %s AND version = %s LIMIT 1",
            (package_id, version),
        )
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail=f"Versao {version} ja existe pra este pacote")

        # 2026-09-23 (review agente ALTO): reject early se o request inteiro
        # excede a soma aceitavel — evita escrever muito no disco antes do 413.
        # Estimativa conservadora: 10 arquivos * MAX_FILE_BYTES + margem.
        try:
            content_length = int(request.headers.get("content-length") or 0)
        except ValueError:
            content_length = 0
        max_total = (MAX_FILE_BYTES * 10) + (5 * 1024 * 1024)  # 5MB overhead multipart
        if content_length > max_total:
            raise HTTPException(status_code=413,
                detail=f"Upload total excede {max_total // (1024*1024)} MB")

        # Cria diretorio fisico
        pkg_dir = _package_dir(slug, version)
        pkg_dir.mkdir(parents=True, exist_ok=True)

        # Salva arquivos e coleta metadata
        files_meta = []
        try:
            for pos, up in enumerate(files):
                fname = _safe_filename(up.filename or "")
                dest = pkg_dir / fname
                # 2026-09-23 (review agente CRITICAL): defesa em profundidade
                # contra path traversal — mesmo com _safe_filename, garante que
                # o path resolvido fica dentro do PACKAGES_ROOT.
                _assert_inside_root(dest, PACKAGES_ROOT)

                total = 0
                sha = hashlib.sha256()
                with open(dest, "wb") as out:
                    while True:
                        chunk = await up.read(64 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > MAX_FILE_BYTES:
                            # Apaga o arquivo parcial antes do rollback do dir
                            out.close()
                            try: os.remove(dest)
                            except Exception: pass
                            raise HTTPException(status_code=413,
                                detail=f"Arquivo {fname!r} excede {MAX_FILE_MB} MB")
                        sha.update(chunk)
                        out.write(chunk)
                files_meta.append({
                    "filename": fname,
                    "sha256":   sha.hexdigest(),
                    "size":     total,
                    "position": pos,
                    "disk_path": str(dest),
                })
        except HTTPException:
            # Rollback: apaga o dir da versao
            try: shutil.rmtree(pkg_dir, ignore_errors=True)
            except Exception: pass
            raise

        # Monta manifest_json que o cliente recebera
        manifest = {
            "package":     slug,
            "version":     version,
            "notes":       notes or "",
            "created_at":  datetime.now().isoformat(timespec="seconds"),
            "files": [
                {
                    "name":   f["filename"],
                    "url":    f"/api/packages/{slug}/files/{f['filename']}",
                    "sha256": f["sha256"],
                    "size":   f["size"],
                }
                for f in files_meta
            ],
        }

        # Insere version + files, marca como current
        cursor.execute(
            "INSERT INTO package_versions "
            "(package_id, version, notes, manifest_json, created_by) "
            "VALUES (%s, %s, %s, %s, %s)",
            (package_id, version, notes, json.dumps(manifest, ensure_ascii=False), admin["id"]),
        )
        version_id = cursor.lastrowid

        for f in files_meta:
            cursor.execute(
                "INSERT INTO package_files "
                "(version_id, filename, sha256, size_bytes, disk_path, position) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (version_id, f["filename"], f["sha256"], f["size"], f["disk_path"], f["position"]),
            )

        cursor.execute(
            "UPDATE packages SET current_version_id = %s WHERE id = %s",
            (version_id, package_id),
        )
        conn.commit()

        logger.info(
            f"[PKG] nova versao publicada: {slug} v{version} "
            f"({len(files_meta)} arquivos, por {admin.get('name')})"
        )
        return {
            "ok": True,
            "version_id": version_id,
            "manifest": manifest,
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as err:
        conn.rollback()
        logger.error(f"[PKG] erro publicando versao: {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao publicar: {err}")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@router.get("/{slug}/logs")
async def list_execution_logs(
    request: Request,
    slug: str = FPath(..., pattern=r"^[a-z0-9-]{2,64}$"),
    limit: int = Query(50, ge=1, le=200),
    success: Optional[bool] = Query(None),
):
    """Lista logs de execucao mais recentes deste pacote (admin)."""
    _require_admin_user(request)
    slug = _safe_slug(slug)

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        where = ["package_slug = %s"]
        params: list = [slug]
        if success is not None:
            where.append("success = %s")
            params.append(1 if success else 0)
        where_sql = " AND ".join(where)

        cursor.execute(
            f"SELECT id, version, computer, user_login, success, "
            f"       LEFT(log_text, 500) AS log_preview, "
            f"       client_ip, created_at "
            f"  FROM package_execution_logs "
            f" WHERE {where_sql} "
            f" ORDER BY created_at DESC LIMIT %s",
            [*params, limit],
        )
        rows = cursor.fetchall()
        for r in rows:
            if r.get("created_at"):
                r["created_at"] = r["created_at"].isoformat()
            r["success"] = bool(r.get("success"))
        return {"logs": rows}
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


@router.get("/{slug}/logs/{log_id}")
async def get_execution_log(
    request: Request,
    slug: str = FPath(..., pattern=r"^[a-z0-9-]{2,64}$"),
    log_id: int = FPath(..., gt=0),
):
    """Retorna log completo de uma execucao (com log_text integral)."""
    _require_admin_user(request)
    slug = _safe_slug(slug)

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM package_execution_logs "
            " WHERE id = %s AND package_slug = %s LIMIT 1",
            (log_id, slug),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Log nao encontrado")
        if row.get("created_at"):
            row["created_at"] = row["created_at"].isoformat()
        row["success"] = bool(row.get("success"))
        return row
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()
