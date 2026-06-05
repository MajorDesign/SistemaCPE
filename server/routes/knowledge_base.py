"""
Base de Conhecimento (KB) — artigos por SETOR.

Permissoes:
- USER comum: ve artigos publicados do PROPRIO setor (users.group_id).
- RESPONSAVEL_GRUPO: ve + cria + edita + deleta artigos do proprio setor.
- ADMIN/TI/MANAGER: ve + gerencia artigos de QUALQUER setor.

Conteudo em markdown (renderizado no frontend via marked.js).
"""
import logging
import os
import uuid as _uuid
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Request, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from database import get_db_or_404
from security import parse_session_token, get_user_by_id

router = APIRouter(prefix="/api/kb", tags=["knowledge-base"])
logger = logging.getLogger(__name__)

# Uploads de imagens dos artigos: web/uploads/kb/<aaaa-mm>/<uuid>.<ext>
_UPLOAD_KB_ROOT    = Path(__file__).resolve().parents[2] / "web" / "uploads" / "kb"
_UPLOAD_KB_URL_BASE = "/SistemaCPE/web/uploads/kb"
_KB_IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
_MAX_KB_IMG_MB = 10

_CATEGORIAS = ("procedimento", "tutorial", "troubleshooting",
               "faq", "politica", "onboarding", "outros")
_CRITICIDADES = ("baixa", "media", "alta", "critica")
_ROLES_GERENCIA = ("ADMIN", "TI", "MANAGER")
_ROLES_CRIAR    = ("RESPONSAVEL_GRUPO", "ADMIN", "TI", "MANAGER")


# ----------------------------- Helpers -----------------------------
def _user_from_request(request: Request) -> dict:
    token = request.cookies.get("cpe_session") or request.headers.get("X-Auth-Token", "")
    if not token:
        raise HTTPException(status_code=401, detail="Sem token de sessao")
    uid = parse_session_token(token)
    if not uid:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado")
    user = get_user_by_id(uid)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado")
    return user


def _eh_admin_global(user: dict) -> bool:
    return user.get("role") in _ROLES_GERENCIA


def _pode_gerenciar_grupo(user: dict, group_id: int) -> bool:
    if _eh_admin_global(user):
        return True
    # RESPONSAVEL_GRUPO ou USER do mesmo grupo? So o RESPONSAVEL pode gerenciar.
    return (user.get("role") == "RESPONSAVEL_GRUPO" and user.get("group_id") == group_id)


def _pode_ver_grupo(user: dict, group_id: int) -> bool:
    if _eh_admin_global(user):
        return True
    return user.get("group_id") == group_id


# ----------------------------- Models -----------------------------
class ArticleCreate(BaseModel):
    group_id: int = Field(..., gt=0)
    titulo: str = Field(..., min_length=3, max_length=255)
    resumo: Optional[str] = Field(None, max_length=500)
    conteudo: str = Field(..., min_length=10)
    categoria: str = Field("outros")
    subcategoria: Optional[str] = Field(None, max_length=80)
    criticidade: str = Field("media")
    capa_icon: Optional[str] = Field("bi-book", max_length=40)
    capa_cor: Optional[str] = Field("#FFC107", max_length=7)
    tags: Optional[str] = Field(None, max_length=255)
    publicado: bool = True


class ArticleEdit(BaseModel):
    titulo: Optional[str] = Field(None, min_length=3, max_length=255)
    resumo: Optional[str] = Field(None, max_length=500)
    conteudo: Optional[str] = Field(None, min_length=10)
    categoria: Optional[str] = None
    subcategoria: Optional[str] = Field(None, max_length=80)
    criticidade: Optional[str] = None
    capa_icon: Optional[str] = Field(None, max_length=40)
    capa_cor: Optional[str] = Field(None, max_length=7)
    tags: Optional[str] = Field(None, max_length=255)
    publicado: Optional[bool] = None
    group_id: Optional[int] = Field(None, gt=0)


class HelpfulBody(BaseModel):
    helpful: bool


# ----------------------------- Endpoints -----------------------------
@router.get("/groups")
def listar_grupos_disponiveis(request: Request):
    """Lista grupos que o user pode VER/ESCOLHER pra filtrar.
    Admin global: todos. USER/RESPONSAVEL: so o proprio."""
    user = _user_from_request(request)
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        if _eh_admin_global(user):
            cur.execute("""
                SELECT g.id, g.name, d.name AS department_name
                FROM cpe_grupo g
                LEFT JOIN departments d ON d.id = g.department_id
                ORDER BY g.name
            """)
        else:
            if not user.get("group_id"):
                return {"success": True, "groups": []}
            cur.execute("""
                SELECT g.id, g.name, d.name AS department_name
                FROM cpe_grupo g
                LEFT JOIN departments d ON d.id = g.department_id
                WHERE g.id = %s
            """, (user["group_id"],))
        return {"success": True, "groups": cur.fetchall()}
    finally:
        cur.close(); conn.close()


@router.get("/articles")
def listar_artigos(request: Request,
                    group_id: Optional[int] = Query(None),
                    categoria: Optional[str] = Query(None),
                    q: Optional[str] = Query(None),
                    only_my_drafts: bool = Query(False)):
    """Lista artigos do setor (filtrado por grupo + categoria + busca)."""
    user = _user_from_request(request)
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        sql = ["""
            SELECT a.id, a.group_id, g.name AS group_name,
                   a.titulo, a.resumo, a.categoria, a.subcategoria,
                   a.criticidade, a.capa_icon, a.capa_cor, a.tags,
                   a.autor_id, u.name AS autor_nome,
                   a.publicado, a.views, a.helpful, a.unhelpful,
                   a.criado_em, a.atualizado_em
            FROM kb_articles a
            LEFT JOIN cpe_grupo g ON g.id = a.group_id
            LEFT JOIN users u     ON u.id = a.autor_id
            WHERE 1=1
        """]
        params: list = []
        # Escopo: admin global ve tudo; senao so o proprio grupo.
        if not _eh_admin_global(user):
            sql.append("AND a.group_id = %s")
            params.append(user.get("group_id") or 0)
        elif group_id:
            sql.append("AND a.group_id = %s")
            params.append(group_id)
        # Rascunhos so do autor (a menos que admin)
        if only_my_drafts:
            sql.append("AND a.publicado = 0 AND a.autor_id = %s")
            params.append(user["id"])
        else:
            # USER comum so ve publicados (autor pode ver os proprios rascunhos)
            if not _eh_admin_global(user):
                sql.append("AND (a.publicado = 1 OR a.autor_id = %s)")
                params.append(user["id"])
        if categoria and categoria in _CATEGORIAS:
            sql.append("AND a.categoria = %s")
            params.append(categoria)
        if q:
            sql.append("AND (a.titulo LIKE %s OR a.resumo LIKE %s OR a.tags LIKE %s)")
            like = f"%{q.strip()}%"
            params.extend([like, like, like])
        sql.append("ORDER BY a.atualizado_em DESC LIMIT 200")
        cur.execute(" ".join(sql), tuple(params))
        return {"success": True, "articles": cur.fetchall()}
    finally:
        cur.close(); conn.close()


@router.get("/stats")
def stats(request: Request, group_id: Optional[int] = Query(None)):
    """Estatisticas leves: total, por categoria, views totais, etc."""
    user = _user_from_request(request)
    target_gid = group_id if (group_id and _eh_admin_global(user)) else user.get("group_id")
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        where = "" if (_eh_admin_global(user) and not group_id) else "WHERE group_id = %s"
        args = () if (_eh_admin_global(user) and not group_id) else (target_gid or 0,)
        cur.execute(f"""
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(publicado=1),0)    AS publicados,
                COALESCE(SUM(publicado=0),0)    AS rascunhos,
                COALESCE(SUM(views),0)          AS total_views,
                COALESCE(SUM(helpful),0)        AS total_helpful,
                COALESCE(SUM(unhelpful),0)      AS total_unhelpful
            FROM kb_articles {where}
        """, args)
        agg = cur.fetchone()
        cur.execute(f"""
            SELECT categoria, COUNT(*) AS n
            FROM kb_articles {where}
            GROUP BY categoria ORDER BY n DESC
        """, args)
        por_cat = cur.fetchall()
        return {"success": True, "stats": agg, "por_categoria": por_cat}
    finally:
        cur.close(); conn.close()


@router.get("/articles/{article_id}")
def detalhar_artigo(article_id: int, request: Request):
    user = _user_from_request(request)
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT a.*, g.name AS group_name, u.name AS autor_nome
            FROM kb_articles a
            LEFT JOIN cpe_grupo g ON g.id = a.group_id
            LEFT JOIN users u     ON u.id = a.autor_id
            WHERE a.id = %s
        """, (article_id,))
        art = cur.fetchone()
        if not art:
            raise HTTPException(status_code=404, detail="Artigo nao encontrado")
        if not _pode_ver_grupo(user, art["group_id"]):
            raise HTTPException(status_code=403, detail="Sem permissao pra ver este artigo")
        if not art["publicado"] and art["autor_id"] != user["id"] and not _eh_admin_global(user):
            raise HTTPException(status_code=403, detail="Rascunho — sem permissao")
        # Incrementa views (so se nao for o autor)
        if art["autor_id"] != user["id"]:
            cur.execute("UPDATE kb_articles SET views = views + 1 WHERE id = %s", (article_id,))
            conn.commit()
            art["views"] = (art["views"] or 0) + 1
        return {"success": True, "article": art}
    finally:
        cur.close(); conn.close()


@router.post("/articles")
def criar_artigo(body: ArticleCreate, request: Request):
    user = _user_from_request(request)
    if user.get("role") not in _ROLES_CRIAR:
        raise HTTPException(status_code=403, detail="So Responsavel de Grupo, Admin, TI ou Manager podem criar artigos")
    if not _pode_gerenciar_grupo(user, body.group_id):
        raise HTTPException(status_code=403, detail="Sem permissao pra criar no setor selecionado")
    if body.categoria not in _CATEGORIAS:
        raise HTTPException(status_code=400, detail=f"Categoria invalida (use uma de: {', '.join(_CATEGORIAS)})")
    if body.criticidade not in _CRITICIDADES:
        raise HTTPException(status_code=400, detail=f"Criticidade invalida (use: {', '.join(_CRITICIDADES)})")
    # Resumo auto se vazio
    resumo = (body.resumo or "").strip()
    if not resumo:
        # Pega primeiros 200 chars do conteudo sem hashtags/asterisks
        clean = " ".join(body.conteudo.replace("#", "").replace("*", "").split())
        resumo = clean[:200]
    conn = get_db_or_404()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO kb_articles
                (group_id, titulo, resumo, conteudo, categoria, subcategoria,
                 criticidade, capa_icon, capa_cor, tags, autor_id, publicado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (body.group_id, body.titulo.strip(), resumo, body.conteudo,
              body.categoria, (body.subcategoria or "").strip() or None,
              body.criticidade, body.capa_icon or "bi-book",
              body.capa_cor or "#FFC107", body.tags,
              user["id"], int(body.publicado)))
        new_id = cur.lastrowid
        conn.commit()
    finally:
        cur.close(); conn.close()
    return {"success": True, "id": new_id}


@router.put("/articles/{article_id}")
def editar_artigo(article_id: int, body: ArticleEdit, request: Request):
    user = _user_from_request(request)
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT group_id, autor_id FROM kb_articles WHERE id=%s", (article_id,))
        art = cur.fetchone()
        if not art:
            raise HTTPException(status_code=404, detail="Artigo nao encontrado")
        # Autor OU admin OU responsavel do grupo
        ok = (art["autor_id"] == user["id"]
              or _eh_admin_global(user)
              or _pode_gerenciar_grupo(user, art["group_id"]))
        if not ok:
            raise HTTPException(status_code=403, detail="Sem permissao pra editar")
        sets, params = [], []
        if body.titulo is not None:    sets.append("titulo=%s");    params.append(body.titulo.strip())
        if body.resumo is not None:    sets.append("resumo=%s");    params.append(body.resumo)
        if body.conteudo is not None:  sets.append("conteudo=%s");  params.append(body.conteudo)
        if body.categoria is not None:
            if body.categoria not in _CATEGORIAS:
                raise HTTPException(status_code=400, detail="Categoria invalida")
            sets.append("categoria=%s"); params.append(body.categoria)
        if body.subcategoria is not None:
            sets.append("subcategoria=%s"); params.append(body.subcategoria.strip() or None)
        if body.criticidade is not None:
            if body.criticidade not in _CRITICIDADES:
                raise HTTPException(status_code=400, detail="Criticidade invalida")
            sets.append("criticidade=%s"); params.append(body.criticidade)
        if body.capa_icon is not None: sets.append("capa_icon=%s"); params.append(body.capa_icon)
        if body.capa_cor is not None:  sets.append("capa_cor=%s");  params.append(body.capa_cor)
        if body.tags is not None:      sets.append("tags=%s");      params.append(body.tags)
        if body.publicado is not None: sets.append("publicado=%s"); params.append(int(body.publicado))
        if body.group_id is not None:
            # So admin global pode mover entre grupos
            if not _eh_admin_global(user):
                raise HTTPException(status_code=403, detail="So admin pode mover artigo entre setores")
            sets.append("group_id=%s"); params.append(body.group_id)
        if not sets:
            return {"success": True, "noop": True}
        params.append(article_id)
        cur.execute(f"UPDATE kb_articles SET {', '.join(sets)} WHERE id=%s", params)
        conn.commit()
    finally:
        cur.close(); conn.close()
    return {"success": True}


@router.delete("/articles/{article_id}")
def excluir_artigo(article_id: int, request: Request):
    user = _user_from_request(request)
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT group_id, autor_id FROM kb_articles WHERE id=%s", (article_id,))
        art = cur.fetchone()
        if not art:
            raise HTTPException(status_code=404, detail="Artigo nao encontrado")
        ok = (art["autor_id"] == user["id"]
              or _eh_admin_global(user)
              or _pode_gerenciar_grupo(user, art["group_id"]))
        if not ok:
            raise HTTPException(status_code=403, detail="Sem permissao pra excluir")
        cur.execute("DELETE FROM kb_articles WHERE id=%s", (article_id,))
        conn.commit()
    finally:
        cur.close(); conn.close()
    return {"success": True}


@router.post("/articles/{article_id}/helpful")
def marcar_helpful(article_id: int, body: HelpfulBody, request: Request):
    user = _user_from_request(request)
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT group_id FROM kb_articles WHERE id=%s", (article_id,))
        art = cur.fetchone()
        if not art:
            raise HTTPException(status_code=404, detail="Artigo nao encontrado")
        if not _pode_ver_grupo(user, art["group_id"]):
            raise HTTPException(status_code=403, detail="Sem permissao")
        col = "helpful" if body.helpful else "unhelpful"
        cur.execute(f"UPDATE kb_articles SET {col} = {col} + 1 WHERE id=%s", (article_id,))
        conn.commit()
    finally:
        cur.close(); conn.close()
    return {"success": True}


# =====================================================================
# Upload de imagem: POST /api/kb/upload-image (multipart)
# Usado pelo editor para anexar imagens nos artigos (capa ou inline).
# Retorna a URL publica pra ser inserida como ![alt](url) no markdown.
# =====================================================================
@router.post("/upload-image")
async def upload_imagem(request: Request, file: UploadFile = File(...)):
    user = _user_from_request(request)
    if user.get("role") not in _ROLES_CRIAR:
        raise HTTPException(status_code=403,
                            detail="So quem cria artigos pode subir imagens (Responsavel, Admin, TI, Manager)")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _KB_IMG_EXTS:
        raise HTTPException(status_code=400,
                            detail=f"Extensao nao permitida ({ext}). Use: {', '.join(sorted(_KB_IMG_EXTS))}")

    # Organiza por mes pra nao deixar pasta gigante: web/uploads/kb/2026-06/<uuid>.png
    from datetime import datetime
    sub = datetime.now().strftime("%Y-%m")
    pasta = _UPLOAD_KB_ROOT / sub
    pasta.mkdir(parents=True, exist_ok=True)

    filename = f"u{user['id']}_{_uuid.uuid4().hex[:14]}{ext}"
    destino = pasta / filename
    size = 0
    limit = _MAX_KB_IMG_MB * 1024 * 1024
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
                                    detail=f"Imagem maior que {_MAX_KB_IMG_MB} MB")
            out.write(chunk)

    url = f"{_UPLOAD_KB_URL_BASE}/{sub}/{filename}"
    return {
        "success": True,
        "url": url,
        "nome_original": file.filename,
        "tamanho": size,
    }
