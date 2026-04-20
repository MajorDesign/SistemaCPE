"""
Módulo Contratos e Termos — Gestão de pastas e arquivos (PDF/DOC) por grupo.
"""

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from database import get_db_or_404, convert_datetime_list
import os
import uuid
import shutil
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contratos", tags=["Contratos"])

UPLOAD_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "web", "uploads", "contratos")
)
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB


# ============================================================
# HELPER: resolver usuário logado e grupo
# ============================================================

def _resolve_user_id(request: Request):
    from security import parse_session_token, COOKIE_NAME
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token:
        uid = parse_session_token(cookie_token)
        if uid:
            return uid
    header_token = request.headers.get("X-Auth-Token") or request.headers.get("x-auth-token")
    if header_token:
        uid = parse_session_token(header_token)
        if uid:
            return uid
    return None


def _get_user(request: Request):
    """Retorna dict com id, role, group_id do usuário autenticado."""
    uid = _resolve_user_id(request)
    if not uid:
        raise HTTPException(status_code=401, detail="Nao autenticado")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, name, role, group_id FROM users WHERE id=%s AND is_active=1",
            (uid,)
        )
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="Usuario nao encontrado")
        return user
    finally:
        cursor.close()
        conn.close()


def _user_can_access_group(user: dict, group_id: int) -> bool:
    """ADMIN/TI/MANAGER vê tudo; outros só o próprio grupo."""
    if user.get("role") in ("ADMIN", "TI", "MANAGER"):
        return True
    return user.get("group_id") == group_id


# ============================================================
# PASTAS
# ============================================================

@router.get("/pastas")
def list_pastas(request: Request):
    """Lista todas as pastas visíveis ao usuário (seu grupo + subpastas).
       ADMIN/TI/MANAGER veem todas. Retorna flat list para montar árvore no frontend."""
    user = _get_user(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        is_admin = user.get("role") in ("ADMIN", "TI", "MANAGER")
        if is_admin:
            cursor.execute("""
                SELECT p.*, g.name AS group_name,
                       (SELECT COUNT(*) FROM contratos c WHERE c.pasta_id = p.id) AS total_contratos
                FROM contrato_pastas p
                JOIN cpe_grupo g ON g.id = p.group_id
                ORDER BY g.name, p.parent_id, p.nome
            """)
        else:
            cursor.execute("""
                SELECT p.*, g.name AS group_name,
                       (SELECT COUNT(*) FROM contratos c WHERE c.pasta_id = p.id) AS total_contratos
                FROM contrato_pastas p
                JOIN cpe_grupo g ON g.id = p.group_id
                WHERE p.group_id = %s
                ORDER BY p.parent_id, p.nome
            """, (user.get("group_id"),))
        rows = cursor.fetchall()
        rows = convert_datetime_list(rows)
        return {"success": True, "pastas": rows}
    finally:
        cursor.close()
        conn.close()


@router.post("/pastas")
def create_pasta(request: Request, data: dict):
    user = _get_user(request)
    nome = (data.get("nome") or "").strip()
    parent_id = data.get("parent_id")
    if not nome:
        raise HTTPException(status_code=400, detail="Nome da pasta e obrigatorio")
    if not parent_id:
        raise HTTPException(status_code=400, detail="Selecione a pasta pai")

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        # Validar pasta pai e acesso
        cursor.execute("SELECT group_id FROM contrato_pastas WHERE id=%s", (parent_id,))
        pasta_pai = cursor.fetchone()
        if not pasta_pai:
            raise HTTPException(status_code=404, detail="Pasta pai nao encontrada")
        if not _user_can_access_group(user, pasta_pai["group_id"]):
            raise HTTPException(status_code=403, detail="Sem permissao para criar pasta neste grupo")

        cursor.execute("""
            INSERT INTO contrato_pastas (group_id, parent_id, nome, is_root, created_by)
            VALUES (%s, %s, %s, 0, %s)
        """, (pasta_pai["group_id"], parent_id, nome, user["id"]))
        conn.commit()
        return {"success": True, "id": cursor.lastrowid, "message": "Pasta criada!"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.put("/pastas/{pasta_id}/move")
def move_pasta(pasta_id: int, request: Request, data: dict):
    """Move pasta para outro parent (dentro do mesmo grupo)."""
    user = _get_user(request)
    novo_parent = data.get("parent_id")
    if not novo_parent:
        raise HTTPException(status_code=400, detail="parent_id obrigatorio")

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT group_id, is_root, parent_id FROM contrato_pastas WHERE id=%s", (pasta_id,))
        p = cursor.fetchone()
        if not p: raise HTTPException(status_code=404, detail="Pasta nao encontrada")
        if p["is_root"]: raise HTTPException(status_code=400, detail="Pasta raiz nao pode ser movida")
        if not _user_can_access_group(user, p["group_id"]):
            raise HTTPException(status_code=403, detail="Sem permissao")

        cursor.execute("SELECT group_id FROM contrato_pastas WHERE id=%s", (novo_parent,))
        pai = cursor.fetchone()
        if not pai: raise HTTPException(status_code=404, detail="Pasta destino nao encontrada")
        if pai["group_id"] != p["group_id"]:
            raise HTTPException(status_code=400, detail="Nao pode mover para outro grupo")

        # Evitar loop (mover para si mesmo ou descendente)
        cursor.execute("""
            WITH RECURSIVE subtree AS (
              SELECT id FROM contrato_pastas WHERE id = %s
              UNION ALL
              SELECT c.id FROM contrato_pastas c JOIN subtree s ON c.parent_id = s.id
            )
            SELECT id FROM subtree WHERE id = %s
        """, (pasta_id, novo_parent))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Nao pode mover pasta para dentro de si mesma")

        cursor.execute("UPDATE contrato_pastas SET parent_id=%s WHERE id=%s", (novo_parent, pasta_id))
        conn.commit()
        return {"success": True, "message": "Pasta movida!"}
    except HTTPException: raise
    except Exception as e:
        conn.rollback(); raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close(); conn.close()


@router.post("/pastas/{pasta_id}/copy")
def copy_pasta(pasta_id: int, request: Request, data: dict):
    """Duplica uma pasta (e todo o conteúdo) para outra pasta pai."""
    user = _get_user(request)
    novo_parent = data.get("parent_id")
    if not novo_parent:
        raise HTTPException(status_code=400, detail="parent_id obrigatorio")

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM contrato_pastas WHERE id=%s", (pasta_id,))
        origem = cursor.fetchone()
        if not origem: raise HTTPException(status_code=404, detail="Pasta nao encontrada")
        if origem["is_root"]: raise HTTPException(status_code=400, detail="Nao pode copiar pasta raiz")
        if not _user_can_access_group(user, origem["group_id"]):
            raise HTTPException(status_code=403, detail="Sem permissao")

        cursor.execute("SELECT group_id FROM contrato_pastas WHERE id=%s", (novo_parent,))
        pai = cursor.fetchone()
        if not pai: raise HTTPException(status_code=404, detail="Pasta destino nao encontrada")

        # Copia recursiva (mapeia old_id -> new_id)
        mapping = {}
        def _copy_recursive(src_id, dst_parent, dst_group):
            cursor.execute("SELECT * FROM contrato_pastas WHERE id=%s", (src_id,))
            src = cursor.fetchone()
            novo_nome = src["nome"] + (" (cópia)" if src_id == pasta_id else "")
            cursor.execute("""
                INSERT INTO contrato_pastas (group_id, parent_id, nome, is_root, created_by)
                VALUES (%s,%s,%s,0,%s)
            """, (dst_group, dst_parent, novo_nome, user["id"]))
            new_id = cursor.lastrowid
            mapping[src_id] = new_id

            # Copiar contratos desta pasta
            cursor.execute("SELECT * FROM contratos WHERE pasta_id=%s", (src_id,))
            for c in cursor.fetchall():
                # Duplicar arquivo físico
                old_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", c["arquivo_path"].lstrip("/")))
                new_filename = f"contr_{uuid.uuid4().hex[:12]}.{c['tipo']}"
                new_fs_path = os.path.join(UPLOAD_DIR, new_filename)
                try:
                    if os.path.exists(old_path):
                        shutil.copy2(old_path, new_fs_path)
                except Exception: pass
                new_url = f"/SistemaCPE/web/uploads/contratos/{new_filename}"
                cursor.execute("""
                    INSERT INTO contratos (pasta_id, nome, descricao, arquivo_path, tipo, tamanho_bytes, uploaded_by)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, (new_id, c["nome"], c["descricao"], new_url, c["tipo"], c["tamanho_bytes"], user["id"]))

            # Recursão em filhos
            cursor.execute("SELECT id FROM contrato_pastas WHERE parent_id=%s", (src_id,))
            for f in cursor.fetchall():
                _copy_recursive(f["id"], new_id, dst_group)

        _copy_recursive(pasta_id, novo_parent, pai["group_id"])
        conn.commit()
        return {"success": True, "message": "Pasta copiada!", "id": mapping[pasta_id]}
    except HTTPException: raise
    except Exception as e:
        conn.rollback(); raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close(); conn.close()


@router.delete("/pastas/{pasta_id}")
def delete_pasta(pasta_id: int, request: Request):
    user = _get_user(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT group_id, is_root FROM contrato_pastas WHERE id=%s", (pasta_id,))
        pasta = cursor.fetchone()
        if not pasta:
            raise HTTPException(status_code=404, detail="Pasta nao encontrada")
        if pasta["is_root"]:
            raise HTTPException(status_code=400, detail="Nao e possivel excluir a pasta raiz do grupo")
        if not _user_can_access_group(user, pasta["group_id"]):
            raise HTTPException(status_code=403, detail="Sem permissao")

        # Apagar arquivos físicos de todos os contratos nessa pasta (recursivo via CASCADE do DB)
        cursor.execute("""
            WITH RECURSIVE subtree AS (
              SELECT id FROM contrato_pastas WHERE id = %s
              UNION ALL
              SELECT p.id FROM contrato_pastas p
              JOIN subtree s ON p.parent_id = s.id
            )
            SELECT c.arquivo_path FROM contratos c
            WHERE c.pasta_id IN (SELECT id FROM subtree)
        """, (pasta_id,))
        for row in cursor.fetchall():
            try:
                fp = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", row["arquivo_path"].lstrip("/")))
                if os.path.exists(fp):
                    os.remove(fp)
            except Exception:
                pass

        cursor.execute("DELETE FROM contrato_pastas WHERE id=%s", (pasta_id,))
        conn.commit()
        return {"success": True, "message": "Pasta excluida!"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# ============================================================
# CONTRATOS
# ============================================================

@router.get("")
def list_contratos(request: Request, pasta_id: int):
    user = _get_user(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT group_id FROM contrato_pastas WHERE id=%s", (pasta_id,))
        pasta = cursor.fetchone()
        if not pasta:
            raise HTTPException(status_code=404, detail="Pasta nao encontrada")
        if not _user_can_access_group(user, pasta["group_id"]):
            raise HTTPException(status_code=403, detail="Sem permissao")

        cursor.execute("""
            SELECT c.*, u.name AS uploaded_by_nome
            FROM contratos c
            LEFT JOIN users u ON u.id = c.uploaded_by
            WHERE c.pasta_id = %s
            ORDER BY c.created_at DESC
        """, (pasta_id,))
        rows = cursor.fetchall()
        rows = convert_datetime_list(rows)
        return {"success": True, "contratos": rows}
    finally:
        cursor.close()
        conn.close()


@router.post("")
async def upload_contrato(
    request: Request,
    pasta_id: int = Form(...),
    nome: str = Form(...),
    descricao: str = Form(""),
    file: UploadFile = File(...),
):
    user = _get_user(request)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Formato invalido. Use PDF, DOC ou DOCX.")

    # Verificar acesso à pasta
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT group_id FROM contrato_pastas WHERE id=%s", (pasta_id,))
        pasta = cursor.fetchone()
        if not pasta:
            raise HTTPException(status_code=404, detail="Pasta nao encontrada")
        if not _user_can_access_group(user, pasta["group_id"]):
            raise HTTPException(status_code=403, detail="Sem permissao para enviar neste grupo")

        # Ler conteúdo e validar tamanho
        content = await file.read()
        tamanho = len(content)
        if tamanho > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"Arquivo excede {MAX_FILE_SIZE//1024}KB (enviado: {tamanho//1024}KB)")
        if tamanho == 0:
            raise HTTPException(status_code=400, detail="Arquivo vazio")

        tipo = ext.lstrip(".")
        filename = f"contr_{uuid.uuid4().hex[:12]}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(content)

        arquivo_url = f"/SistemaCPE/web/uploads/contratos/{filename}"

        cursor.execute("""
            INSERT INTO contratos (pasta_id, nome, descricao, arquivo_path, tipo, tamanho_bytes, uploaded_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (pasta_id, nome.strip(), descricao.strip() or None, arquivo_url, tipo, tamanho, user["id"]))
        conn.commit()
        return {"success": True, "id": cursor.lastrowid, "arquivo_path": arquivo_url, "message": "Contrato enviado!"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.put("/{contrato_id}/move")
def move_contrato(contrato_id: int, request: Request, data: dict):
    user = _get_user(request)
    nova_pasta = data.get("pasta_id")
    if not nova_pasta: raise HTTPException(status_code=400, detail="pasta_id obrigatorio")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT c.pasta_id, p.group_id AS origem_grupo
            FROM contratos c JOIN contrato_pastas p ON p.id = c.pasta_id
            WHERE c.id=%s
        """, (contrato_id,))
        c = cursor.fetchone()
        if not c: raise HTTPException(status_code=404, detail="Contrato nao encontrado")
        if not _user_can_access_group(user, c["origem_grupo"]):
            raise HTTPException(status_code=403, detail="Sem permissao")

        cursor.execute("SELECT group_id FROM contrato_pastas WHERE id=%s", (nova_pasta,))
        destino = cursor.fetchone()
        if not destino: raise HTTPException(status_code=404, detail="Pasta destino nao encontrada")
        if not _user_can_access_group(user, destino["group_id"]):
            raise HTTPException(status_code=403, detail="Sem permissao no destino")

        cursor.execute("UPDATE contratos SET pasta_id=%s WHERE id=%s", (nova_pasta, contrato_id))
        conn.commit()
        return {"success": True, "message": "Contrato movido!"}
    except HTTPException: raise
    except Exception as e:
        conn.rollback(); raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close(); conn.close()


@router.post("/{contrato_id}/copy")
def copy_contrato(contrato_id: int, request: Request, data: dict):
    user = _get_user(request)
    nova_pasta = data.get("pasta_id")
    if not nova_pasta: raise HTTPException(status_code=400, detail="pasta_id obrigatorio")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT c.*, p.group_id AS origem_grupo
            FROM contratos c JOIN contrato_pastas p ON p.id = c.pasta_id
            WHERE c.id=%s
        """, (contrato_id,))
        c = cursor.fetchone()
        if not c: raise HTTPException(status_code=404, detail="Contrato nao encontrado")
        if not _user_can_access_group(user, c["origem_grupo"]):
            raise HTTPException(status_code=403, detail="Sem permissao")

        cursor.execute("SELECT group_id FROM contrato_pastas WHERE id=%s", (nova_pasta,))
        destino = cursor.fetchone()
        if not destino: raise HTTPException(status_code=404, detail="Pasta destino nao encontrada")
        if not _user_can_access_group(user, destino["group_id"]):
            raise HTTPException(status_code=403, detail="Sem permissao no destino")

        # Duplicar arquivo físico
        old_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", c["arquivo_path"].lstrip("/")))
        new_filename = f"contr_{uuid.uuid4().hex[:12]}.{c['tipo']}"
        new_fs_path = os.path.join(UPLOAD_DIR, new_filename)
        try:
            if os.path.exists(old_path):
                shutil.copy2(old_path, new_fs_path)
        except Exception: pass
        new_url = f"/SistemaCPE/web/uploads/contratos/{new_filename}"

        cursor.execute("""
            INSERT INTO contratos (pasta_id, nome, descricao, arquivo_path, tipo, tamanho_bytes, uploaded_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (nova_pasta, c["nome"] + " (cópia)", c["descricao"], new_url, c["tipo"], c["tamanho_bytes"], user["id"]))
        conn.commit()
        return {"success": True, "id": cursor.lastrowid, "message": "Contrato copiado!"}
    except HTTPException: raise
    except Exception as e:
        conn.rollback(); raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close(); conn.close()


@router.delete("/{contrato_id}")
def delete_contrato(contrato_id: int, request: Request):
    user = _get_user(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT c.arquivo_path, c.uploaded_by, p.group_id
            FROM contratos c
            JOIN contrato_pastas p ON p.id = c.pasta_id
            WHERE c.id = %s
        """, (contrato_id,))
        contrato = cursor.fetchone()
        if not contrato:
            raise HTTPException(status_code=404, detail="Contrato nao encontrado")
        if not _user_can_access_group(user, contrato["group_id"]):
            raise HTTPException(status_code=403, detail="Sem permissao")

        # Remover arquivo físico
        try:
            fp = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", contrato["arquivo_path"].lstrip("/")))
            if os.path.exists(fp):
                os.remove(fp)
        except Exception:
            pass

        cursor.execute("DELETE FROM contratos WHERE id=%s", (contrato_id,))
        conn.commit()
        return {"success": True, "message": "Contrato excluido!"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
