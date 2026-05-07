"""
Módulo de Agentes — Lista e serve downloads dos utilitários instalaveis
(ex: TermoNotebookCPE) disponíveis em tools/.

Convenção: cada agente tem uma pasta `release/` onde os builds ficam no
formato `<Nome>_v<versao>.exe`. O backend sempre pega o **mais recente**
(por mtime) e extrai a versão do nome do arquivo — fonte única da verdade.
"""

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from database import get_db_or_404
import os
import re
import glob
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["Agents"])

TOOLS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "tools")
)

# Pasta de contratos onde os termos assinados são depositados.
# Usa SEMPRE a pasta do grupo da T.I. independente do grupo do usuário.
# O grupo é resolvido em runtime pelo NOME — a T.I. do sistema é "Suporte ti"
# (ou similar). Se renomearem o grupo, só atualize TERMOS_GROUP_NAME.
TERMOS_GROUP_NAME     = "Suporte ti"
TERMOS_FOLDER_NAME    = "Termos Notebooks 2026"
CONTRATOS_UPLOAD_DIR  = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "web", "uploads", "contratos")
)
os.makedirs(CONTRATOS_UPLOAD_DIR, exist_ok=True)


# Catálogo de agentes. Cada entrada aponta para a pasta `release/` e o padrão
# de nome do arquivo versionado (glob). Para adicionar um novo agente,
# basta acrescentar aqui.
AGENTS = {
    "termo-notebook": {
        "id":          "termo-notebook",
        "name":        "Termo de Responsabilidade - Notebook",
        "description": "Aplicativo para preenchimento e impressão do termo de responsabilidade de notebook CPE.",
        "icon":        "bi-laptop",
        "systems":     ["Windows 10", "Windows 11"],
        "release_dir": os.path.join(TOOLS_DIR, "termo_notebook", "release"),
        "exe_glob":    "TermoNotebookCPE_v*.exe",
        # Fallback se `release/` ainda não tiver arquivos (primeira execução,
        # pré-migração). Caminhos legacy dos builds antigos.
        "legacy_exe":  [
            os.path.join(TOOLS_DIR, "termo_notebook", "dist", "TermoNotebookCPE.exe"),
            os.path.join(TOOLS_DIR, "termo_notebook", "dist", "TermoNotebookCPE_onefile.exe"),
        ],
        "source_file": os.path.join(TOOLS_DIR, "termo_notebook", "termo_notebook.py"),
    },
}

# Agente de inventário T.I. — arquivo único, sem pasta release/
_INV_AGENT_PY   = os.path.join(TOOLS_DIR, "inventory_agent", "CPEAgente.py")
_INV_VERSION_RE = re.compile(r'^VERSAO\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


def _inv_agent_versao() -> str | None:
    try:
        text = open(_INV_AGENT_PY, encoding="utf-8").read()
        m = _INV_VERSION_RE.search(text)
        return m.group(1) if m else None
    except Exception:
        return None


def _inventario_agent_info() -> dict:
    """Constrói entrada do agente de inventário dinamicamente (versão lida do fonte)."""
    py_info = _file_info(_INV_AGENT_PY)

    files = {
        "src": {
            "label":      "Agente Python (CPEAgente.py)",
            "filename":   "CPEAgente.py",
            "available":  py_info is not None,
            "size_bytes": py_info["size_bytes"] if py_info else 0,
            "modified":   py_info["modified"]    if py_info else None,
        },
    }

    return {
        "id":           "cpe-inventario",
        "name":         "Agente de Inventário T.I.",
        "description":  "Arquivo único auto-suficiente. Execute uma vez — instala dependências, registra no startup do Windows e envia dados a cada 5 minutos. Auto-atualiza-se via servidor.",
        "icon":         "bi-cpu",
        "systems":      ["Windows 10", "Windows 11", "Windows Server 2019+"],
        "version":      _inv_agent_versao(),
        "files":        files,
        "last_updated": py_info["modified"] if py_info else None,
    }


_VERSION_RE = re.compile(r"_v([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE)

def _extract_version(filename: str) -> str | None:
    """Extrai '1.0.3' de 'TermoNotebookCPE_v1.0.3.exe'."""
    m = _VERSION_RE.search(os.path.basename(filename))
    if not m:
        return None
    # Remove ponto/zero sobrando no final (se houver)
    return m.group(1).rstrip(".")


def _find_latest_release(agent: dict) -> tuple[str | None, str | None]:
    """Retorna (path, versao) do .exe mais recente em release/,
    ou (legacy_path, None) se release/ estiver vazio mas existir build antigo."""
    pattern = os.path.join(agent["release_dir"], agent["exe_glob"])
    candidates = glob.glob(pattern)
    if candidates:
        latest = max(candidates, key=os.path.getmtime)
        return latest, _extract_version(latest)
    for legacy in agent.get("legacy_exe") or []:
        if os.path.exists(legacy):
            return legacy, None
    return None, None


def _file_info(path: str | None) -> dict | None:
    if not path or not os.path.exists(path):
        return None
    st = os.stat(path)
    return {
        "size_bytes": st.st_size,
        "modified":   datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
    }


@router.get("")
def list_agents():
    """Lista agentes com a versão e metadados do build mais recente."""
    result = []
    for agent in AGENTS.values():
        exe_path, version = _find_latest_release(agent)
        exe_info = _file_info(exe_path)
        src_info = _file_info(agent.get("source_file"))

        files_meta = {
            "exe": {
                "label":      "Executável Windows (.exe)",
                "filename":   os.path.basename(exe_path) if exe_path else "TermoNotebookCPE.exe",
                "available":  exe_info is not None,
                "size_bytes": exe_info["size_bytes"] if exe_info else 0,
                "modified":   exe_info["modified"]    if exe_info else None,
            },
            "src": {
                "label":      "Código-fonte (.py)",
                "filename":   "termo_notebook.py",
                "available":  src_info is not None,
                "size_bytes": src_info["size_bytes"] if src_info else 0,
                "modified":   src_info["modified"]    if src_info else None,
            },
        }

        mais_recente = None
        for m in files_meta.values():
            if m["modified"] and (not mais_recente or m["modified"] > mais_recente):
                mais_recente = m["modified"]

        result.append({
            "id":           agent["id"],
            "name":         agent["name"],
            "description":  agent["description"],
            "icon":         agent["icon"],
            "systems":      agent["systems"],
            "version":      version,
            "files":        files_meta,
            "last_updated": mais_recente,
        })

    # Agente de inventário T.I. (estrutura diferente: .py + .bat, sem release/)
    result.append(_inventario_agent_info())

    return {"success": True, "agents": result}


@router.get("/{agent_id}/download")
def download_agent(agent_id: str, request: Request, format: str = "exe"):
    """Serve o arquivo do agente no formato solicitado (exe|src|bat|py)."""

    # Agente de inventário T.I. — arquivo único CPEAgente.py
    if agent_id == "cpe-inventario":
        if not os.path.exists(_INV_AGENT_PY):
            raise HTTPException(status_code=404, detail="CPEAgente.py não encontrado no servidor.")
        logger.info(f"[AGENTS] Download cpe-inventario -> CPEAgente.py")
        return FileResponse(_INV_AGENT_PY, filename="CPEAgente.py",
                            media_type="application/octet-stream")

    agent = AGENTS.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agente nao encontrado")

    if format == "exe":
        path, _ = _find_latest_release(agent)
        if not path or not os.path.exists(path):
            raise HTTPException(
                status_code=404,
                detail="Executável ainda não foi gerado. Rode scripts/build.bat."
            )
        filename = os.path.basename(path)
    elif format == "src":
        path = agent.get("source_file")
        if not path or not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Código-fonte não encontrado.")
        filename = "termo_notebook.py"
    else:
        raise HTTPException(status_code=400, detail=f"Formato invalido: {format}")

    logger.info(f"[AGENTS] Download {agent_id}/{format} -> {os.path.basename(path)}")
    return FileResponse(path, filename=filename, media_type="application/octet-stream")


# ============================================================
# SUBMISSÃO DE TERMO (qualquer usuário autenticado → pasta T.I.)
# ============================================================

def _resolve_authenticated_user(request: Request) -> dict:
    """Resolve o usuário autenticado por cookie de sessão ou header X-Auth-Token."""
    from security import parse_session_token, COOKIE_NAME, get_user_by_id
    token = request.cookies.get(COOKIE_NAME) or request.headers.get("X-Auth-Token") or request.headers.get("x-auth-token")
    uid = parse_session_token(token) if token else None
    if not uid:
        raise HTTPException(status_code=401, detail="Não autenticado")
    user = get_user_by_id(uid)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return user


def _ensure_termos_folder(cursor) -> int:
    """Garante que exista a pasta 'Termos Notebooks 2026' dentro do grupo T.I.
    Resolve o grupo pelo NOME (TERMOS_GROUP_NAME). Retorna o id da subpasta."""
    # 1) Resolve o group_id pelo nome (case-insensitive)
    cursor.execute(
        "SELECT id FROM cpe_grupo WHERE LOWER(name) = LOWER(%s) LIMIT 1",
        (TERMOS_GROUP_NAME,)
    )
    grp = cursor.fetchone()
    if not grp:
        raise HTTPException(
            status_code=500,
            detail=f"Grupo '{TERMOS_GROUP_NAME}' não encontrado. "
                   f"Crie esse grupo (cpe_grupo) ou ajuste TERMOS_GROUP_NAME em agents.py."
        )
    group_id = grp["id"] if isinstance(grp, dict) else grp[0]

    # 2) Pasta raiz do grupo
    cursor.execute(
        "SELECT id FROM contrato_pastas WHERE group_id=%s AND is_root=1 LIMIT 1",
        (group_id,)
    )
    raiz = cursor.fetchone()
    if not raiz:
        # Cria raiz se não existir (primeiro termo enviado)
        cursor.execute("""
            INSERT INTO contrato_pastas (group_id, parent_id, nome, is_root, created_by)
            VALUES (%s, NULL, %s, 1, NULL)
        """, (group_id, TERMOS_GROUP_NAME))
        raiz_id = cursor.lastrowid
    else:
        raiz_id = raiz["id"] if isinstance(raiz, dict) else raiz[0]

    # 3) Subpasta "Termos Notebooks 2026"
    cursor.execute(
        "SELECT id FROM contrato_pastas WHERE group_id=%s AND parent_id=%s AND nome=%s LIMIT 1",
        (group_id, raiz_id, TERMOS_FOLDER_NAME)
    )
    sub = cursor.fetchone()
    if sub:
        return sub["id"] if isinstance(sub, dict) else sub[0]

    cursor.execute("""
        INSERT INTO contrato_pastas (group_id, parent_id, nome, is_root, created_by)
        VALUES (%s, %s, %s, 0, NULL)
    """, (group_id, raiz_id, TERMOS_FOLDER_NAME))
    return cursor.lastrowid


@router.post("/termo-notebook/submit")
async def submit_termo_notebook(
    request: Request,
    nome: str = Form(...),
    descricao: str = Form(""),
    file: UploadFile = File(...),
):
    """Qualquer usuário autenticado pode enviar o termo.
    O PDF é depositado sempre na pasta 'Termos Notebooks 2026' do grupo T.I."""
    user = _resolve_authenticated_user(request)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos.")

    content = await file.read()
    tamanho = len(content)
    if tamanho == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    if tamanho > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"PDF excede 2 MB (enviado: {tamanho // 1024} KB)."
        )

    filename = f"termo_{uuid.uuid4().hex[:12]}.pdf"
    filepath = os.path.join(CONTRATOS_UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    arquivo_url = f"/SistemaCPE/web/uploads/contratos/{filename}"

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        pasta_id = _ensure_termos_folder(cursor)
        cursor.execute("""
            INSERT INTO contratos (pasta_id, nome, descricao, arquivo_path, tipo, tamanho_bytes, uploaded_by)
            VALUES (%s, %s, %s, %s, 'pdf', %s, %s)
        """, (pasta_id, nome.strip(), (descricao or "").strip() or None, arquivo_url, tamanho, user["id"]))
        conn.commit()
        logger.info(f"[AGENTS] Termo recebido de userId={user['id']} ({user.get('name')}): {filename}")
        return {
            "success":    True,
            "id":         cursor.lastrowid,
            "pasta":      TERMOS_FOLDER_NAME,
            "arquivo":    arquivo_url,
            "message":    f"Termo enviado para '{TERMOS_FOLDER_NAME}' (grupo T.I.).",
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"[AGENTS] Erro ao salvar termo: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
