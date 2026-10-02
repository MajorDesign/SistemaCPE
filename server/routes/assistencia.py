"""Modulo Assistencia Tecnica — Certificados.

2026-10-01: endpoints para upload de certificados de calibracao (.xlsx)
com geracao de QR-code publico que baixa o PDF convertido.

Permissao de admin/escrita: ADMIN ou grupo 'assistencia' (id=3). Delegada
pro frontend via pageGuard('ASSISTENCIA_TECNICA') + validacao server-side
em cada endpoint autenticado.

Endpoints autenticados (prefix /api/assistencia):
    POST   /certificados             criar (multipart: numero_serie + arquivo)
    GET    /certificados             listar
    GET    /certificados/{id}        detalhar
    PUT    /certificados/{id}        editar (serie e/ou arquivo)
    DELETE /certificados/{id}        soft-delete
    GET    /certificados/{id}/qr.png PNG do QR pra imprimir

Endpoint publico (sem autenticacao, prefix /cert):
    GET    /cert/{token}             streaming do PDF (rate-limited)

Seguranca:
- qr_token: 64 chars hex (secrets.token_hex(32)) — 2^256 combos, imune
  a brute-force / enumeracao sequencial.
- Arquivos salvos fora da webroot em server/uploads/assistencia_certificados/.
- Nome em disco e randomico (nunca o original) — anti path-traversal.
- Rate-limit publico: 20 downloads/minuto por IP (in-memory sliding window).
- Content-Disposition: attachment forca download, nao renderiza inline.
- 404 generico pra tokens invalidos / soft-deleted (anti-enumeracao temporal).
- Upload: so .xlsx validado por extensao + magic bytes (PK\\x03\\x04 — ZIP).
- Max 10 MB por arquivo.
"""
from __future__ import annotations

import io
import os
import re
import secrets
import time
import threading
import logging
import mimetypes
import datetime as _dt
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from database import get_db_connection
from security import get_current_user

logger = logging.getLogger(__name__)

# =========================================================================
# Config
# =========================================================================
_UPLOAD_ROOT = Path(os.environ.get(
    "ASSIST_CERT_DIR",
    str(Path(__file__).resolve().parent.parent / "uploads" / "assistencia_certificados"),
))
_UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

# Magic bytes:
#   .xlsx (Office Open XML / zip)   = 'PK\x03\x04'
#   .xls  (Compound Document / OLE2) = '\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
XLSX_MAGIC = b"PK\x03\x04"
XLS_MAGIC  = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"

XLSX_MIMES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "application/vnd.ms-excel",                                            # xls / genérico
    "application/octet-stream",                                            # alguns clientes
}
EXCEL_EXTENSIONS = (".xlsx", ".xls")

# PDF (anexo anual global)
PDF_MAGIC = b"%PDF-"
MAX_ANEXO_BYTES = 10 * 1024 * 1024  # 10 MB

# Diretorio onde o anexo global vive (um arquivo apenas, sobrescrito).
_ANEXO_GLOBAL_DIR = _UPLOAD_ROOT / "anexo_global"
_ANEXO_GLOBAL_DIR.mkdir(parents=True, exist_ok=True)

_SERIE_REGEX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _\-./]{0,98}[A-Za-z0-9]$")

# =========================================================================
# Rate limit do endpoint publico — in-memory sliding window por IP.
# 20 downloads/minuto. Reset no restart do processo. Suficiente pra
# anti-scraping, nao e defesa definitiva (atras do tunnel/caddy ha outras).
# =========================================================================
_RATE_LIMIT_WINDOW = 60     # segundos
_RATE_LIMIT_MAX    = 20
_rate_hits: dict[str, list[float]] = {}
_rate_lock = threading.Lock()


def _rate_check(ip: str) -> bool:
    now = time.time()
    with _rate_lock:
        hits = _rate_hits.get(ip, [])
        hits = [t for t in hits if now - t < _RATE_LIMIT_WINDOW]
        if len(hits) >= _RATE_LIMIT_MAX:
            _rate_hits[ip] = hits
            return False
        hits.append(now)
        _rate_hits[ip] = hits
    return True


# =========================================================================
# Helpers
# =========================================================================
def _client_ip(req: Request) -> str:
    fwd = req.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return req.client.host if req.client else "unknown"


def _assert_can_manage(current_user: dict) -> None:
    """Garante que o user pode gerenciar certificados: ADMIN OU grupo
    assistencia (id=3) OU user_groups inclui 3."""
    role = (current_user.get("role") or "").upper()
    if role == "ADMIN":
        return
    if current_user.get("group_id") == 3:
        return
    gids = current_user.get("group_ids") or []
    if 3 in gids:
        return
    raise HTTPException(
        status_code=403,
        detail="Apenas ADMIN ou usuarios do grupo Assistencia podem gerenciar certificados.",
    )


def _assert_can_manage_anexo(current_user: dict) -> None:
    """Permissao mais restrita (so pra upload do anexo anual):
    ADMIN OU (RESPONSAVEL_GRUPO E pertence ao grupo assistencia=3).

    Qualquer um do grupo Assistencia consegue CRIAR certificado, mas so
    um RESPONSAVEL_GRUPO (ou ADMIN) troca o anexo que vai pra todos.
    """
    role = (current_user.get("role") or "").upper()
    if role == "ADMIN":
        return
    if role == "RESPONSAVEL_GRUPO":
        gids = current_user.get("group_ids") or []
        if current_user.get("group_id") == 3 or 3 in gids:
            return
    raise HTTPException(
        status_code=403,
        detail="Apenas ADMIN ou RESPONSAVEL_GRUPO do grupo Assistencia pode atualizar o anexo anual.",
    )


async def _read_pdf_upload(file: UploadFile) -> bytes:
    """Le upload PDF do anexo anual. Valida extensao + magic bytes + tamanho."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    if len(data) > MAX_ANEXO_BYTES:
        raise HTTPException(status_code=413, detail=f"Anexo maior que {MAX_ANEXO_BYTES // 1024 // 1024} MB.")
    nome = (file.filename or "").lower()
    if not nome.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="So aceitamos PDF (.pdf).")
    if not data.startswith(PDF_MAGIC):
        raise HTTPException(status_code=400, detail="Arquivo .pdf invalido (magic bytes incorretos).")
    return data


def _fetch_anexo_global() -> Optional[dict]:
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """SELECT a.*, u.name AS atualizado_por_nome
                 FROM assistencia_anexo_global a
                 LEFT JOIN users u ON u.id = a.atualizado_por
                WHERE a.id = 1 LIMIT 1"""
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def _format_anexo(r: dict | None) -> dict | None:
    if not r:
        return None
    return {
        "arquivo_nome":        r.get("arquivo_nome"),
        "arquivo_size":        r.get("arquivo_size"),
        "atualizado_em":       r["atualizado_em"].isoformat() if r.get("atualizado_em") else None,
        "atualizado_por":      r.get("atualizado_por"),
        "atualizado_por_nome": r.get("atualizado_por_nome"),
    }


def _validate_serie(serie: str) -> str:
    s = (serie or "").strip()
    if not s or not _SERIE_REGEX.fullmatch(s):
        raise HTTPException(
            status_code=400,
            detail="numero_serie invalido. Use 2-100 chars alfanumericos, pode ter _ - . / espaco (nao no inicio/fim).",
        )
    return s


async def _read_upload(file: UploadFile) -> tuple[bytes, str]:
    """Le o upload. Retorna (bytes, extensao_detectada).

    Aceita .xlsx (zip-based) e .xls (OLE compound document). Valida por:
      1) extensao do filename (.xlsx ou .xls)
      2) magic bytes (defesa contra arquivo renomeado)
      3) tamanho max

    Returns:
        (data_bytes, ".xlsx" ou ".xls")
    """
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Arquivo maior que {MAX_UPLOAD_BYTES // 1024 // 1024} MB.")

    nome = (file.filename or "").lower()
    if nome.endswith(".xlsx"):
        if not data.startswith(XLSX_MAGIC):
            raise HTTPException(status_code=400, detail="Arquivo .xlsx invalido (magic bytes incorretos).")
        return data, ".xlsx"
    if nome.endswith(".xls"):
        if not data.startswith(XLS_MAGIC):
            raise HTTPException(status_code=400, detail="Arquivo .xls invalido (magic bytes incorretos).")
        return data, ".xls"
    raise HTTPException(status_code=400, detail="So aceitamos arquivos Excel (.xlsx ou .xls).")


def _random_disk_name(suffix: str = ".xlsx") -> str:
    return secrets.token_hex(16) + suffix


def _convert_to_pdf(xlsx_path: str, pdf_path: str) -> None:
    """Converte via services/xlsx_to_pdf exportando SO a aba 'Folha de Rosto'.

    Certificados tem 2 abas (Folha de Rosto + Medicao); a aba de medicao e
    uso interno e nao deve ir no QR publico. Se a aba 'Folha de Rosto' nao
    existir, o service faz fallback pro workbook inteiro + log warning.
    """
    from services.xlsx_to_pdf import convert
    convert(xlsx_path, pdf_path, sheet_name="Folha de Rosto")


def _extrair_data_calibracao(xlsx_path: str, ext: str):
    """Le a data da calibracao do arquivo. Nunca levanta — devolve None em erro."""
    from services.cert_data_parser import extract_data_calibracao
    return extract_data_calibracao(xlsx_path, ext)


# =========================================================================
# Routers
# =========================================================================
router = APIRouter(prefix="/api/assistencia", tags=["Assistencia Tecnica"])
public_router = APIRouter(tags=["Assistencia Tecnica Publico"])


# -------------------------------------------------------------------------
# POST /api/assistencia/certificados
# -------------------------------------------------------------------------
@router.post("/certificados", status_code=201)
async def criar_certificado(
    numero_serie: str = Form(...),
    arquivo: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Cria uma nova versao de certificado pra uma serie.

    Semantica (versionamento):
      - Serie nova: cria v1 (qr_token novo, impresso_em=null).
      - Serie ja existe (versao ativa):
          * nova data_calibracao > atual  -> cria v(N+1), MARCA a atual como substituida
                                             e gera qr_token NOVO (QR antigo passa a 410).
          * nova data == atual            -> 409 duplicata.
          * nova data < atual             -> 409 'arquivo mais antigo que a versao vigente'.
          * data_cal=None (parse falhou)  -> aceita como nova versao (nao da pra comparar).
    """
    _assert_can_manage(current_user)
    anexo = _fetch_anexo_global()
    if not anexo or not anexo.get("arquivo_path") or not os.path.exists(anexo["arquivo_path"]):
        raise HTTPException(
            status_code=400,
            detail="Nenhum anexo anual cadastrado. Peca ao responsavel do grupo pra fazer upload antes de criar certificados.",
        )
    serie = _validate_serie(numero_serie)
    data, ext = await _read_upload(arquivo)

    token = secrets.token_hex(32)
    disk_name_src = _random_disk_name(ext)
    disk_name_pdf = disk_name_src[: -len(ext)] + ".pdf"
    xlsx_abs = (_UPLOAD_ROOT / disk_name_src).resolve()
    pdf_abs  = (_UPLOAD_ROOT / disk_name_pdf).resolve()

    try:
        xlsx_abs.write_bytes(data)
        _convert_to_pdf(str(xlsx_abs), str(pdf_abs))
    except Exception as e:
        for p in (xlsx_abs, pdf_abs):
            try: p.unlink(missing_ok=True)
            except Exception: pass
        logger.error(f"[ASSIST/CERT] falha ao salvar/converter: {e}")
        raise HTTPException(status_code=500, detail=f"Falha ao processar arquivo: {e}")

    data_cal = _extrair_data_calibracao(str(xlsx_abs), ext)

    # Busca versao ativa atual dessa serie (se existir)
    atual = _buscar_versao_ativa(serie)
    nova_versao = 1
    substitui_id = None

    if atual:
        nova_versao = int(atual.get("versao") or 1) + 1
        substitui_id = atual["id"]
        atual_data = atual.get("data_calibracao")
        if data_cal and atual_data:
            if data_cal == atual_data:
                for p in (xlsx_abs, pdf_abs):
                    try: p.unlink(missing_ok=True)
                    except Exception: pass
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Este arquivo tem a mesma data de calibracao ({data_cal.isoformat()}) "
                        f"da versao vigente (v{atual['versao']}, cert #{atual['id']}). "
                        f"Nada a atualizar."
                    ),
                )
            if data_cal < atual_data:
                for p in (xlsx_abs, pdf_abs):
                    try: p.unlink(missing_ok=True)
                    except Exception: pass
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"O arquivo tem data de calibracao MAIS ANTIGA ({data_cal.isoformat()}) "
                        f"que a versao vigente ({atual_data.isoformat()}, v{atual['versao']}). "
                        f"Verifique se nao e o arquivo errado."
                    ),
                )

    # Transacao: insere nova versao + marca anterior como substituida
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """INSERT INTO assistencia_certificados
               (numero_serie, data_calibracao, versao,
                arquivo_xlsx_nome, arquivo_xlsx_path, arquivo_pdf_path,
                arquivo_size, arquivo_mime, qr_token, criado_por)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (serie, data_cal, nova_versao,
             arquivo.filename or disk_name_src, str(xlsx_abs), str(pdf_abs),
             len(data), arquivo.content_type or "application/octet-stream",
             token, current_user["id"]),
        )
        new_id = cur.lastrowid
        if substitui_id:
            cur.execute(
                """UPDATE assistencia_certificados
                      SET substituido_em = NOW(), substituido_por = %s
                    WHERE id = %s""",
                (new_id, substitui_id),
            )
        conn.commit()
        logger.info(
            f"[ASSIST/CERT] cert id={new_id} serie='{serie}' v{nova_versao} "
            f"token={token[:8]}... substitui={substitui_id} user={current_user['id']}"
        )

        cur.execute(
            """SELECT c.*, u1.name AS criado_por_nome, u2.name AS atualizado_por_nome
                 FROM assistencia_certificados c
                 LEFT JOIN users u1 ON u1.id = c.criado_por
                 LEFT JOIN users u2 ON u2.id = c.atualizado_por
                WHERE c.id = %s""",
            (new_id,),
        )
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    return _format_row(row)


def _buscar_versao_ativa(serie: str) -> Optional[dict]:
    """Versao vigente de uma serie (substituido_em IS NULL, deletado_em IS NULL)."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """SELECT * FROM assistencia_certificados
                WHERE numero_serie = %s
                  AND substituido_em IS NULL
                  AND deletado_em IS NULL
                ORDER BY versao DESC
                LIMIT 1""",
            (serie,),
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


# -------------------------------------------------------------------------
# GET /api/assistencia/certificados
# -------------------------------------------------------------------------
@router.get("/certificados")
async def listar_certificados(
    q: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Lista somente VERSOES ATIVAS (vigentes) de cada serie.
    Historico (versoes substituidas) fica em /certificados/by-serie/{serie}/historico.
    """
    _assert_can_manage(current_user)
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        where = ["c.deletado_em IS NULL", "c.substituido_em IS NULL"]
        params: list = []
        if q:
            where.append("c.numero_serie LIKE %s")
            params.append(f"%{q.strip()}%")
        sql = (
            "SELECT c.*, u1.name AS criado_por_nome, u2.name AS atualizado_por_nome "
            " FROM assistencia_certificados c "
            " LEFT JOIN users u1 ON u1.id = c.criado_por "
            " LEFT JOIN users u2 ON u2.id = c.atualizado_por "
            " WHERE " + " AND ".join(where) +
            " ORDER BY c.criado_em DESC"
        )
        cur.execute(sql, params)
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()
    return [_format_row(r) for r in rows]


# -------------------------------------------------------------------------
# GET /api/assistencia/certificados/by-serie/{serie}/historico
# -------------------------------------------------------------------------
@router.get("/certificados/by-serie/{serie}/historico")
async def historico_serie(serie: str, current_user: dict = Depends(get_current_user)):
    """Todas as versoes (ativa + substituidas) nao deletadas de uma serie."""
    _assert_can_manage(current_user)
    s = _validate_serie(serie)
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """SELECT c.*, u1.name AS criado_por_nome, u2.name AS atualizado_por_nome
                 FROM assistencia_certificados c
                 LEFT JOIN users u1 ON u1.id = c.criado_por
                 LEFT JOIN users u2 ON u2.id = c.atualizado_por
                WHERE c.numero_serie = %s
                  AND c.deletado_em IS NULL
                ORDER BY c.versao DESC, c.criado_em DESC""",
            (s,),
        )
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()
    return {
        "numero_serie": s,
        "total": len(rows),
        "versoes": [_format_row(r) for r in rows],
    }


# -------------------------------------------------------------------------
# POST /api/assistencia/certificados/{id}/mark-printed
# -------------------------------------------------------------------------
@router.post("/certificados/{cert_id}/mark-printed")
async def marcar_qr_impresso(cert_id: int, current_user: dict = Depends(get_current_user)):
    """Registra que o QR deste certificado foi impresso (badge NOVO some)."""
    _assert_can_manage(current_user)
    row = _fetch_cert(cert_id)
    if not row:
        raise HTTPException(status_code=404, detail="Certificado nao encontrado.")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE assistencia_certificados SET impresso_em = NOW() WHERE id = %s AND impresso_em IS NULL",
            (cert_id,),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()
    logger.info(f"[ASSIST/CERT] cert id={cert_id} marcado como impresso por user={current_user['id']}")
    return _format_row(_fetch_cert(cert_id))


# -------------------------------------------------------------------------
# GET /api/assistencia/certificados/{id}
# -------------------------------------------------------------------------
@router.get("/certificados/{cert_id}")
async def obter_certificado(cert_id: int, current_user: dict = Depends(get_current_user)):
    _assert_can_manage(current_user)
    row = _fetch_cert(cert_id)
    if not row:
        raise HTTPException(status_code=404, detail="Certificado nao encontrado.")
    return _format_row(row)


# PUT /certificados/{id} removido: fluxo unico agora e versionamento via POST.
# Pra "atualizar", suba o novo arquivo como novo certificado — o sistema
# detecta a serie existente e cria a nova versao (que gera QR novo e marca
# a anterior como substituida).


# -------------------------------------------------------------------------
# DELETE /api/assistencia/certificados/{id}  (soft delete)
# -------------------------------------------------------------------------
@router.delete("/certificados/{cert_id}", status_code=204)
async def deletar_certificado(cert_id: int, current_user: dict = Depends(get_current_user)):
    _assert_can_manage(current_user)
    row = _fetch_cert(cert_id)
    if not row:
        raise HTTPException(status_code=404, detail="Certificado nao encontrado.")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE assistencia_certificados SET deletado_em = NOW() WHERE id = %s",
            (cert_id,),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()
    logger.info(f"[ASSIST/CERT] cert id={cert_id} soft-deleted por user={current_user['id']}")
    return Response(status_code=204)


# -------------------------------------------------------------------------
# GET /api/assistencia/certificados/{id}/qr.png
# -------------------------------------------------------------------------
@router.get("/certificados/{cert_id}/qr.png")
async def gerar_qr(cert_id: int, request: Request, current_user: dict = Depends(get_current_user)):
    _assert_can_manage(current_user)
    row = _fetch_cert(cert_id)
    if not row:
        raise HTTPException(status_code=404, detail="Certificado nao encontrado.")

    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if not base:
        # Fallback pra URL atual (dev)
        base = f"{request.url.scheme}://{request.url.hostname}"
        if request.url.port and request.url.port not in (80, 443):
            base += f":{request.url.port}"

    url = f"{base}/cert/{row['qr_token']}"

    import qrcode
    img = qrcode.make(url, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    headers = {"Content-Disposition": f'inline; filename="qr-{row["numero_serie"]}.png"'}
    return StreamingResponse(buf, media_type="image/png", headers=headers)


# -------------------------------------------------------------------------
# GET /api/assistencia/relatorio?desde&ate
#     - snapshot do estado atual (vigentes OK vs vencidos)
#     - metricas no periodo: novas series, renovacoes, "salvamentos" de vencidos
#     - breakdown por usuario (quem renovou quanto)
#     - breakdown por mes (timeline)
# Util pra medir "pos-implantacao: quantas calibracoes conseguimos vender?"
# -------------------------------------------------------------------------
_JANELA_VENCIDO_DIAS = 182  # ~6 meses — mesmo criterio usado em /vencimentos


@router.get("/relatorio")
async def gerar_relatorio(
    desde: Optional[str] = None,
    ate: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    _assert_can_manage(current_user)
    hoje = _dt.date.today()

    # Default: ultimos 90 dias
    try:
        d_desde = _dt.date.fromisoformat(desde) if desde else (hoje - _dt.timedelta(days=90))
    except ValueError:
        raise HTTPException(status_code=400, detail="Parametro 'desde' invalido (use YYYY-MM-DD).")
    try:
        d_ate = _dt.date.fromisoformat(ate) if ate else hoje
    except ValueError:
        raise HTTPException(status_code=400, detail="Parametro 'ate' invalido (use YYYY-MM-DD).")
    if d_desde > d_ate:
        raise HTTPException(status_code=400, detail="'desde' deve ser <= 'ate'.")

    limite_vencido = hoje - _dt.timedelta(days=_JANELA_VENCIDO_DIAS)

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        # ----- Snapshot HOJE (so versoes ativas) -----
        cur.execute(
            """SELECT COUNT(*) AS n
                 FROM assistencia_certificados
                WHERE deletado_em IS NULL AND substituido_em IS NULL""",
        )
        total_series_ativas = cur.fetchone()["n"]

        cur.execute(
            """SELECT COUNT(*) AS n
                 FROM assistencia_certificados
                WHERE deletado_em IS NULL AND substituido_em IS NULL
                  AND data_calibracao IS NOT NULL
                  AND data_calibracao <= %s""",
            (limite_vencido,),
        )
        vigentes_vencidos = cur.fetchone()["n"]

        cur.execute(
            """SELECT COUNT(*) AS n
                 FROM assistencia_certificados
                WHERE deletado_em IS NULL AND substituido_em IS NULL
                  AND (data_calibracao IS NULL OR data_calibracao > %s)""",
            (limite_vencido,),
        )
        vigentes_ok = cur.fetchone()["n"]

        # ----- Movimentos no periodo [d_desde, d_ate] -----
        # c_novo = cert criado no periodo. c_antigo = o que ele substituiu (se existiu).
        # Convertemos 'ate' pra fim do dia pra incluir todo o dia (ate 23:59:59).
        ate_inclusivo = _dt.datetime.combine(d_ate, _dt.time(23, 59, 59))
        desde_inicio   = _dt.datetime.combine(d_desde, _dt.time.min)

        cur.execute(
            """SELECT
                 c_novo.id, c_novo.criado_em, c_novo.criado_por, c_novo.versao,
                 c_novo.numero_serie, c_novo.data_calibracao AS novo_data_cal,
                 u.name AS usuario_nome,
                 c_antigo.id AS antigo_id,
                 c_antigo.data_calibracao AS antigo_data_cal
                 FROM assistencia_certificados c_novo
            LEFT JOIN users u ON u.id = c_novo.criado_por
            LEFT JOIN assistencia_certificados c_antigo
                   ON c_antigo.substituido_por = c_novo.id
                WHERE c_novo.deletado_em IS NULL
                  AND c_novo.criado_em BETWEEN %s AND %s
                ORDER BY c_novo.criado_em DESC""",
            (desde_inicio, ate_inclusivo),
        )
        movs = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    # Agrega
    novas_series = 0
    renovacoes = 0
    renovacoes_de_vencidos = 0
    por_usuario: dict[int, dict] = {}
    por_mes: dict[str, dict] = {}
    detalhes = []

    for m in movs:
        is_renovacao = m.get("antigo_id") is not None
        salvou_vencido = False
        if is_renovacao and m.get("antigo_data_cal") and m.get("criado_em"):
            # cert antigo estava vencido quando o novo foi criado?
            idade_antigo = (m["criado_em"].date() - m["antigo_data_cal"]).days
            salvou_vencido = idade_antigo >= _JANELA_VENCIDO_DIAS

        if is_renovacao:
            renovacoes += 1
            if salvou_vencido:
                renovacoes_de_vencidos += 1
        else:
            novas_series += 1

        uid = m.get("criado_por") or 0
        bucket = por_usuario.setdefault(uid, {
            "usuario_id": uid,
            "usuario_nome": m.get("usuario_nome") or "(desconhecido)",
            "renovacoes": 0,
            "renovacoes_de_vencidos": 0,
            "novas_series": 0,
            "total": 0,
        })
        bucket["total"] += 1
        if is_renovacao:
            bucket["renovacoes"] += 1
            if salvou_vencido:
                bucket["renovacoes_de_vencidos"] += 1
        else:
            bucket["novas_series"] += 1

        mes_key = m["criado_em"].strftime("%Y-%m")
        mb = por_mes.setdefault(mes_key, {
            "mes": mes_key,
            "renovacoes": 0,
            "renovacoes_de_vencidos": 0,
            "novas_series": 0,
            "total": 0,
        })
        mb["total"] += 1
        if is_renovacao:
            mb["renovacoes"] += 1
            if salvou_vencido:
                mb["renovacoes_de_vencidos"] += 1
        else:
            mb["novas_series"] += 1

        detalhes.append({
            "id":              m["id"],
            "numero_serie":    m["numero_serie"],
            "versao":          m.get("versao") or 1,
            "criado_em":       m["criado_em"].isoformat() if m.get("criado_em") else None,
            "criado_por":      m.get("criado_por"),
            "usuario_nome":    m.get("usuario_nome"),
            "data_calibracao": m["novo_data_cal"].isoformat() if m.get("novo_data_cal") else None,
            "renovacao":       is_renovacao,
            "salvou_vencido":  salvou_vencido,
        })

    por_usuario_lista = sorted(por_usuario.values(), key=lambda x: x["total"], reverse=True)
    por_mes_lista = sorted(por_mes.values(), key=lambda x: x["mes"])

    return {
        "hoje": hoje.isoformat(),
        "periodo": {"desde": d_desde.isoformat(), "ate": d_ate.isoformat()},
        "janela_vencido_dias": _JANELA_VENCIDO_DIAS,
        "snapshot": {
            "total_series_ativas": total_series_ativas,
            "vigentes_ok": vigentes_ok,
            "vigentes_vencidos": vigentes_vencidos,
        },
        "no_periodo": {
            "total_criados": len(movs),
            "novas_series": novas_series,
            "renovacoes": renovacoes,
            "renovacoes_de_vencidos": renovacoes_de_vencidos,
        },
        "por_usuario": por_usuario_lista,
        "por_mes": por_mes_lista,
        "detalhes": detalhes,
    }


# -------------------------------------------------------------------------
# GET /api/assistencia/vencimentos  —  certificados vencidos (>=6 meses)
# -------------------------------------------------------------------------
@router.get("/vencimentos")
async def listar_vencimentos(current_user: dict = Depends(get_current_user)):
    """Lista certificados cuja data_calibracao >= 6 meses atras.

    Util pro vendedor da equipe de Assistencia: cada item e um candidato
    a contato comercial (nova calibracao).
    """
    _assert_can_manage(current_user)
    hoje = _dt.date.today()
    limite = hoje - _dt.timedelta(days=182)  # 6 meses

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """SELECT c.*, u1.name AS criado_por_nome, u2.name AS atualizado_por_nome
                 FROM assistencia_certificados c
                 LEFT JOIN users u1 ON u1.id = c.criado_por
                 LEFT JOIN users u2 ON u2.id = c.atualizado_por
                WHERE c.deletado_em IS NULL
                  AND c.data_calibracao IS NOT NULL
                  AND c.data_calibracao <= %s
                ORDER BY c.data_calibracao ASC""",
            (limite,),
        )
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    return {
        "hoje":    hoje.isoformat(),
        "limite":  limite.isoformat(),
        "total":   len(rows),
        "itens":   [_format_row(r) for r in rows],
    }


# -------------------------------------------------------------------------
# POST /api/assistencia/certificados/parse-preview
#     Le o xlsx (sem salvar) e devolve numero_serie extraido do nome do
#     arquivo + data_calibracao lida do conteudo + flag se ja existe um
#     cert ativo com (serie, data) iguais (anti-duplicata na UI).
# -------------------------------------------------------------------------
@router.post("/certificados/parse-preview")
async def preview_cert_file(
    arquivo: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    _assert_can_manage(current_user)
    data, ext = await _read_upload(arquivo)

    # Grava num arquivo temporario (parser precisa de path real; usa openpyxl
    # em read_only + xlrd que nao aceitam bytes direto).
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tf:
        tf.write(data)
        tmp_path = tf.name
    try:
        data_cal = _extrair_data_calibracao(tmp_path, ext)
    finally:
        try: os.unlink(tmp_path)
        except Exception: pass

    # Extrai serie do nome do arquivo (padrao XXXX_YYY_SERIE.ext)
    nome = (arquivo.filename or "")
    serie_arquivo = _extrair_serie_do_nome(nome)

    # Compara com versao ativa dessa serie (se existir) pra decidir status.
    #   status 'nova_serie'      -> nao existe serie no banco (vai criar v1)
    #   status 'nova_versao'     -> existe mas data_cal nova > atual (vai criar v+1)
    #   status 'duplicata'       -> mesma data da atual (bloqueado 409)
    #   status 'mais_antiga'     -> data mais antiga que a atual (bloqueado 409)
    #   status 'sem_data_nova'   -> parse novo falhou; aceita sem comparar
    #   status 'sem_serie'       -> nao conseguiu extrair serie do nome
    status = "sem_serie"
    atual = None
    versao_prevista = 1
    pode_salvar = False
    mensagem = ""

    if serie_arquivo:
        a = _buscar_versao_ativa(serie_arquivo)
        if a:
            atual = {
                "id": a["id"],
                "versao": a.get("versao") or 1,
                "numero_serie": a["numero_serie"],
                "data_calibracao": a["data_calibracao"].isoformat() if a.get("data_calibracao") else None,
                "criado_em": a["criado_em"].isoformat() if a.get("criado_em") else None,
                "arquivo_xlsx_nome": a.get("arquivo_xlsx_nome"),
            }
        if not a:
            status = "nova_serie"; pode_salvar = True; versao_prevista = 1
            mensagem = f"Nova serie '{serie_arquivo}' — sera criada como v1."
        elif not data_cal:
            status = "sem_data_nova"; pode_salvar = True
            versao_prevista = int(a.get("versao") or 1) + 1
            mensagem = (
                f"Nao foi possivel ler a data de calibracao no arquivo. "
                f"Vai criar v{versao_prevista} assumindo que e um certificado mais recente."
            )
        elif not a.get("data_calibracao"):
            status = "nova_versao"; pode_salvar = True
            versao_prevista = int(a.get("versao") or 1) + 1
            mensagem = f"Versao atual (v{a['versao']}) nao tinha data lida — sera substituida por v{versao_prevista}."
        elif data_cal > a["data_calibracao"]:
            status = "nova_versao"; pode_salvar = True
            versao_prevista = int(a.get("versao") or 1) + 1
            mensagem = (
                f"Substitui a versao atual v{a['versao']} "
                f"(de {a['data_calibracao'].isoformat()}). Gera QR novo."
            )
        elif data_cal == a["data_calibracao"]:
            status = "duplicata"; pode_salvar = False
            mensagem = (
                f"Ja existe cert v{a['versao']} com a mesma data de calibracao. "
                f"Verifique se este arquivo nao e o mesmo."
            )
        else:  # data_cal < a["data_calibracao"]
            status = "mais_antiga"; pode_salvar = False
            mensagem = (
                f"O arquivo tem data MAIS ANTIGA ({data_cal.isoformat()}) que a versao vigente "
                f"({a['data_calibracao'].isoformat()}, v{a['versao']}). Provavelmente arquivo errado."
            )

    return {
        "numero_serie_do_nome": serie_arquivo or None,
        "data_calibracao": data_cal.isoformat() if data_cal else None,
        "arquivo_nome": nome,
        "tamanho_bytes": len(data),
        "status": status,
        "pode_salvar": pode_salvar,
        "mensagem": mensagem,
        "versao_prevista": versao_prevista,
        "versao_atual": atual,
    }


def _extrair_serie_do_nome(nome_arquivo: str) -> Optional[str]:
    """Mesma logica do helper JS. Padrao XXXX_YYY_SERIE.{xlsx,xls}
    pega ultimo segmento apos '_'."""
    if not nome_arquivo:
        return None
    stem = re.sub(r"\.(xlsx|xls)$", "", nome_arquivo, flags=re.IGNORECASE)
    partes = [p.strip() for p in stem.split("_") if p.strip()]
    if not partes:
        return None
    candidato = partes[-1]
    if _SERIE_REGEX.fullmatch(candidato):
        return candidato
    return None


# -------------------------------------------------------------------------
# Anexo anual global (singleton)
# -------------------------------------------------------------------------
@router.get("/anexo-global")
async def obter_anexo_global(current_user: dict = Depends(get_current_user)):
    _assert_can_manage(current_user)
    return _format_anexo(_fetch_anexo_global())


@router.post("/anexo-global")
async def upload_anexo_global(
    arquivo: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    # Permissao mais restrita: so RESPONSAVEL_GRUPO (ou ADMIN).
    _assert_can_manage_anexo(current_user)
    data = await _read_pdf_upload(arquivo)

    # Nome em disco randomico — antigo e sobrescrito no DB mas o path novo
    # permite rollback caso o INSERT/UPDATE falhe.
    disk_name = secrets.token_hex(16) + ".pdf"
    new_abs = (_ANEXO_GLOBAL_DIR / disk_name).resolve()
    try:
        new_abs.write_bytes(data)
    except Exception as e:
        try: new_abs.unlink(missing_ok=True)
        except Exception: pass
        logger.error(f"[ASSIST/ANEXO] falha ao salvar: {e}")
        raise HTTPException(status_code=500, detail=f"Falha ao salvar anexo: {e}")

    atual = _fetch_anexo_global()
    old_path = atual["arquivo_path"] if atual else None

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        # UPSERT: id=1 e singleton
        cur.execute(
            """INSERT INTO assistencia_anexo_global
                   (id, arquivo_nome, arquivo_path, arquivo_size, atualizado_por)
                 VALUES (1, %s, %s, %s, %s)
                 ON DUPLICATE KEY UPDATE
                   arquivo_nome = VALUES(arquivo_nome),
                   arquivo_path = VALUES(arquivo_path),
                   arquivo_size = VALUES(arquivo_size),
                   atualizado_por = VALUES(atualizado_por)""",
            (arquivo.filename or disk_name, str(new_abs), len(data), current_user["id"]),
        )
        conn.commit()
    except Exception as e:
        # Rollback do arquivo em disco
        try: new_abs.unlink(missing_ok=True)
        except Exception: pass
        logger.error(f"[ASSIST/ANEXO] falha ao gravar no DB: {e}")
        raise HTTPException(status_code=500, detail=f"Falha ao gravar anexo: {e}")
    finally:
        cur.close()
        conn.close()

    # Remove o arquivo antigo do disco (depois do commit, best-effort)
    if old_path and old_path != str(new_abs):
        try: Path(old_path).unlink(missing_ok=True)
        except Exception as e: logger.warning(f"[ASSIST/ANEXO] nao removeu antigo {old_path}: {e}")

    logger.info(f"[ASSIST/ANEXO] anexo global atualizado por user={current_user['id']} size={len(data)}")
    return _format_anexo(_fetch_anexo_global())


@router.get("/anexo-global/preview")
async def preview_anexo_global(current_user: dict = Depends(get_current_user)):
    """Serve o PDF do anexo atual pra preview (autenticado, inline)."""
    _assert_can_manage(current_user)
    a = _fetch_anexo_global()
    if not a or not a.get("arquivo_path") or not os.path.exists(a["arquivo_path"]):
        raise HTTPException(status_code=404, detail="Nenhum anexo cadastrado.")
    headers = {"Content-Disposition": f'inline; filename="{a.get("arquivo_nome","anexo.pdf")}"'}
    return FileResponse(path=a["arquivo_path"], media_type="application/pdf", headers=headers)


def _merge_pdfs(certificado_path: str, anexo_path: str) -> bytes:
    """Merge: certificado primeiro, anexo depois."""
    from pypdf import PdfWriter, PdfReader
    writer = PdfWriter()
    for p in (certificado_path, anexo_path):
        reader = PdfReader(p)
        for page in reader.pages:
            writer.add_page(page)
    buf = io.BytesIO()
    writer.write(buf)
    writer.close()
    buf.seek(0)
    return buf.getvalue()


# -------------------------------------------------------------------------
# GET /cert/{token}  — PUBLICO (sem autenticacao). Baixa o PDF.
# -------------------------------------------------------------------------
@public_router.get("/cert/{token}")
async def download_publico(token: str, request: Request):
    # Rate limit anti-scraping
    ip = _client_ip(request)
    if not _rate_check(ip):
        logger.warning(f"[ASSIST/CERT/PUB] rate-limit ip={ip} token={token[:8]}...")
        raise HTTPException(status_code=429, detail="Muitos downloads deste IP. Aguarde 1 minuto.")

    # Valida formato do token (64 chars hex). Rejeita cedo com 404 generico.
    if not token or len(token) != 64 or not re.fullmatch(r"[0-9a-f]{64}", token):
        raise HTTPException(status_code=404, detail="Certificado nao encontrado.")

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """SELECT id, numero_serie, arquivo_pdf_path, substituido_em, versao
                 FROM assistencia_certificados
                WHERE qr_token = %s AND deletado_em IS NULL
                LIMIT 1""",
            (token,),
        )
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not row:
        logger.info(f"[ASSIST/CERT/PUB] token invalido ip={ip} token={token[:8]}...")
        raise HTTPException(status_code=404, detail="Certificado nao encontrado.")

    # Token existe mas foi substituido por uma versao mais nova.
    # Retornamos 410 Gone pra sinalizar ao cliente que o QR esta obsoleto
    # e orientar o contato com a assistencia (que vai fornecer o novo QR).
    if row.get("substituido_em"):
        logger.info(f"[ASSIST/CERT/PUB] token substituido ip={ip} cert_id={row['id']} serie={row['numero_serie']}")
        raise HTTPException(
            status_code=410,
            detail=(
                "Este QR-code foi substituido por uma versao mais recente. "
                "Procure a assistencia tecnica para obter o novo QR."
            ),
        )

    pdf_path = row.get("arquivo_pdf_path")
    if not pdf_path or not os.path.exists(pdf_path):
        logger.error(f"[ASSIST/CERT/PUB] arquivo nao existe em disco cert_id={row['id']} path={pdf_path}")
        raise HTTPException(status_code=404, detail="Certificado nao encontrado.")

    anexo = _fetch_anexo_global()
    anexo_path = (anexo or {}).get("arquivo_path")
    nome_download = f"Certificado-{row['numero_serie']}.pdf"

    # Se houver anexo valido em disco, faz merge (cert + anexo).
    if anexo_path and os.path.exists(anexo_path):
        try:
            merged = _merge_pdfs(pdf_path, anexo_path)
            logger.info(f"[ASSIST/CERT/PUB] download ok (merged) cert_id={row['id']} serie={row['numero_serie']} ip={ip}")
            return Response(
                content=merged,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{nome_download}"'},
            )
        except Exception as e:
            logger.error(f"[ASSIST/CERT/PUB] falha no merge cert_id={row['id']}: {e} — fallback sem anexo")
            # fallback: entrega so o cert (nao quebra download pro cliente final)

    logger.info(f"[ASSIST/CERT/PUB] download ok (sem anexo) cert_id={row['id']} serie={row['numero_serie']} ip={ip}")
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=nome_download,
    )


# =========================================================================
# helpers DB
# =========================================================================
def _fetch_cert(cert_id: int) -> Optional[dict]:
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """SELECT c.*, u1.name AS criado_por_nome, u2.name AS atualizado_por_nome
                 FROM assistencia_certificados c
                 LEFT JOIN users u1 ON u1.id = c.criado_por
                 LEFT JOIN users u2 ON u2.id = c.atualizado_por
                WHERE c.id = %s AND c.deletado_em IS NULL
                LIMIT 1""",
            (cert_id,),
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def _format_row(r: dict | None) -> dict | None:
    if not r:
        return None
    # Nao exponho os paths absolutos no disco pra client. Expondo so metadados.
    data_cal = r.get("data_calibracao")
    hoje = _dt.date.today()
    dias_desde = None
    vencido = None
    if isinstance(data_cal, _dt.date):
        dias_desde = (hoje - data_cal).days
        vencido = dias_desde >= 182  # ~6 meses

    sub_em = r.get("substituido_em")
    imp_em = r.get("impresso_em")
    ativo = (r.get("deletado_em") is None) and (sub_em is None)

    return {
        "id":                 r["id"],
        "numero_serie":       r["numero_serie"],
        "versao":             r.get("versao") or 1,
        "data_calibracao":    data_cal.isoformat() if isinstance(data_cal, _dt.date) else None,
        "dias_desde_calibracao": dias_desde,
        "vencido":            vencido,
        "ativo":              ativo,
        "substituido_em":     sub_em.isoformat() if sub_em else None,
        "substituido_por":    r.get("substituido_por"),
        "impresso_em":        imp_em.isoformat() if imp_em else None,
        "qr_novo":            ativo and imp_em is None,
        "arquivo_xlsx_nome":  r.get("arquivo_xlsx_nome"),
        "arquivo_size":       r.get("arquivo_size"),
        "qr_token":           r["qr_token"],
        "qr_url_publica":     f"/cert/{r['qr_token']}",
        "criado_em":          r["criado_em"].isoformat() if r.get("criado_em") else None,
        "criado_por":         r.get("criado_por"),
        "criado_por_nome":    r.get("criado_por_nome"),
        "atualizado_em":      r["atualizado_em"].isoformat() if r.get("atualizado_em") else None,
        "atualizado_por":     r.get("atualizado_por"),
        "atualizado_por_nome": r.get("atualizado_por_nome"),
    }
