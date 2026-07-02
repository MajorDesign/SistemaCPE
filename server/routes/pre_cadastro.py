"""
Router de Pré-cadastro de Usuários (auto-cadastro guiado).

Fluxo:
    1) Admin importa lista de e-mails autorizados via CSV (POST /upload-csv)
    2) Usuário entra no login, clica "Primeiro acesso", informa o e-mail
       (GET /verificar-email)
    3) Se autorizado, escolhe nome+senha+grupo (GET /grupos-publicos +
       POST /solicitar) e aguarda aprovação do admin
    4) Admin lista pendentes (GET /pendentes) e aprova/recusa
       (POST /{id}/aprovar | POST /{id}/recusar)

Endpoints públicos (usados na tela de login, sem auth):
    GET  /api/pre-cadastro/verificar-email
    GET  /api/pre-cadastro/grupos-publicos
    POST /api/pre-cadastro/solicitar

Endpoints administrativos:
    POST   /api/pre-cadastro/upload-csv
    GET    /api/pre-cadastro/pendentes
    POST   /api/pre-cadastro/{id}/aprovar
    POST   /api/pre-cadastro/{id}/recusar
    GET    /api/pre-cadastro/emails
    DELETE /api/pre-cadastro/emails/{id}
"""

from __future__ import annotations

import csv
import io
import logging
import re
from typing import Optional

import bcrypt
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, EmailStr, Field

from config import PUBLIC_BASE_URL
from database import get_db_or_404, convert_datetime_to_string, convert_datetime_list
from services.email_service import email_cadastro_aprovado, enviar_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pre-cadastro", tags=["pre-cadastro"])


# ============================================================
# SCHEMAS
# ============================================================

class SolicitarPayload(BaseModel):
    email:    EmailStr
    name:     str = Field(..., min_length=2, max_length=120)
    username: str = Field(..., min_length=3, max_length=50,
                          description="Username escolhido pelo usuário. Letras/números/./_/-")
    cpf:      str = Field(..., min_length=11, max_length=14,
                          description="CPF — 11 dígitos (com ou sem formatação)")
    password: str = Field(..., min_length=8, max_length=255)
    group_id: int = Field(..., gt=0)
    unit_id:  int = Field(..., gt=0)


class RecusarPayload(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=500)


# ============================================================
# HELPERS
# ============================================================

def gerar_username(email: str, nome: str) -> str:
    """
    Gera username a partir do email — pega a parte antes do @ e
    normaliza (minúsculas, só letras/números/ponto/underscore/hífen).
    Ex: 'Jonathan.Lopes@cpe.com.br' -> 'jonathan.lopes'
    """
    base = (email.split("@")[0] or "").strip().lower()
    base = re.sub(r"[^a-z0-9._-]", "", base)
    if not base:
        # fallback: deriva do nome
        base = re.sub(r"[^a-z0-9.]", "", nome.lower().replace(" ", "."))
    return base[:50] or "usuario"


def garantir_username_unico(cursor, username_base: str) -> str:
    """Se o username já existe na tabela users, adiciona sufixo numérico."""
    cursor.execute("SELECT id FROM users WHERE username = %s", (username_base,))
    if not cursor.fetchone():
        return username_base
    n = 2
    while True:
        candidato = f"{username_base}{n}"
        cursor.execute("SELECT id FROM users WHERE username = %s", (candidato,))
        if not cursor.fetchone():
            return candidato
        n += 1
        if n > 999:
            raise HTTPException(status_code=500, detail="Não foi possível gerar username único")


# ---------- Username escolhido pelo usuário ----------

_USERNAME_REGEX = re.compile(r"^[a-z0-9._-]{3,50}$")

def validar_username_formato(username: str) -> str:
    """Normaliza pra minúsculas, valida formato. Retorna o username limpo."""
    u = (username or "").strip().lower()
    if not _USERNAME_REGEX.match(u):
        raise HTTPException(
            status_code=400,
            detail="Username inválido. Use 3-50 caracteres: letras minúsculas, números, ponto, sublinhado ou hífen.",
        )
    return u


def username_disponivel(cursor, username: str, ignorar_email: Optional[str] = None) -> bool:
    """True se username está livre em users + pre_cadastro_pendentes (status pendente).
    `ignorar_email` exclui a própria solicitação ao reaproveitar pendência."""
    cursor.execute("SELECT id FROM users WHERE username = %s LIMIT 1", (username,))
    if cursor.fetchone(): return False
    if ignorar_email:
        cursor.execute(
            "SELECT id FROM pre_cadastro_pendentes "
            "WHERE username = %s AND status = 'pendente' AND email != %s LIMIT 1",
            (username, ignorar_email),
        )
    else:
        cursor.execute(
            "SELECT id FROM pre_cadastro_pendentes "
            "WHERE username = %s AND status = 'pendente' LIMIT 1",
            (username,),
        )
    return not cursor.fetchone()


# ---------- CPF — formatação + validação dos dígitos verificadores ----------

def limpar_cpf(cpf: str) -> str:
    """Remove tudo que não é dígito. Retorna apenas os 11 dígitos."""
    return re.sub(r"\D", "", cpf or "")


def formatar_cpf(cpf_digitos: str) -> str:
    """Formata 11 dígitos em 000.000.000-00."""
    c = cpf_digitos
    return f"{c[0:3]}.{c[3:6]}.{c[6:9]}-{c[9:11]}" if len(c) == 11 else cpf_digitos


def validar_cpf(cpf: str) -> str:
    """Valida CPF (formato + dígitos verificadores). Retorna formatado ou raise 400."""
    c = limpar_cpf(cpf)
    if len(c) != 11 or c == c[0] * 11:
        raise HTTPException(status_code=400, detail="CPF inválido — informe os 11 dígitos.")

    # Dígito 1
    soma = sum(int(c[i]) * (10 - i) for i in range(9))
    d1 = ((soma * 10) % 11) % 10
    if d1 != int(c[9]):
        raise HTTPException(status_code=400, detail="CPF inválido.")

    # Dígito 2
    soma = sum(int(c[i]) * (11 - i) for i in range(10))
    d2 = ((soma * 10) % 11) % 10
    if d2 != int(c[10]):
        raise HTTPException(status_code=400, detail="CPF inválido.")

    return formatar_cpf(c)


def _detectar_delimitador(texto: str) -> str:
    """Detecta se o CSV usa ',' ou ';' como separador (padrão pt-BR / Excel)."""
    amostra = "\n".join(texto.splitlines()[:5])
    virgulas = amostra.count(",")
    pontoVirgulas = amostra.count(";")
    return ";" if pontoVirgulas > virgulas else ","


def parsear_csv(conteudo: bytes) -> list[dict]:
    """
    Aceita CSV no formato 'email[<delim>nome]'. Detecta cabeçalho e
    delimitador (',' ou ';') automaticamente.
    Retorna lista de dicts {email, nome}.
    """
    texto = conteudo.decode("utf-8-sig", errors="replace")
    delim = _detectar_delimitador(texto)
    linhas: list[dict] = []
    primeira = True
    reader = csv.reader(io.StringIO(texto), delimiter=delim)
    for row in reader:
        if not row:
            continue
        cells = [c.strip() for c in row if c is not None]
        if not cells or not cells[0]:
            continue
        email = cells[0].strip().lower()
        nome  = cells[1].strip() if len(cells) > 1 else None

        # Pula cabeçalho — primeira linha sem @ no primeiro campo
        if primeira and "@" not in email:
            primeira = False
            continue
        primeira = False

        if "@" not in email or "." not in email.split("@", 1)[-1]:
            continue
        linhas.append({"email": email, "nome": nome or None})
    return linhas


def notificar_admins(cursor, mensagem: str) -> None:
    """Cria uma notificação para todos os usuários ADMIN."""
    cursor.execute("SELECT id FROM users WHERE role = 'ADMIN' AND is_active = 1")
    admins = cursor.fetchall()
    if not admins:
        return
    for adm in admins:
        adm_id = adm["id"] if isinstance(adm, dict) else adm[0]
        cursor.execute(
            "INSERT INTO notificacoes (ticket_id, usuario_id, mensagem, tipo, lido) "
            "VALUES (NULL, %s, %s, 'pre_cadastro_pendente', 0)",
            (adm_id, mensagem[:255]),
        )


# ============================================================
# ENDPOINTS PÚBLICOS (usados na tela de login)
# ============================================================

@router.get("/verificar-email")
async def verificar_email(email: str = Query(..., min_length=5, max_length=190)):
    """
    Verifica se um e-mail pode iniciar o pré-cadastro.

    Possíveis retornos:
        autorizado=False           -> e-mail não está na lista importada
        ja_cadastrado=True         -> e-mail já tem usuário ativo no sistema
        ja_pendente=True           -> existe solicitação pendente
        recusado=True              -> houve recusa anterior (devolve motivo)
        autorizado=True (sem flags) -> pode prosseguir
    """
    email_norm = email.strip().lower()
    logger.info(f"[PRECAD/VERIFICAR] {email_norm}")

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        # 1) Já existe usuário com esse e-mail?
        cursor.execute("SELECT id FROM users WHERE email = %s", (email_norm,))
        if cursor.fetchone():
            return {
                "autorizado": False,
                "ja_cadastrado": True,
                "mensagem": "Este e-mail já está cadastrado. Caso não lembre da senha, procure o administrador.",
            }

        # 2) Já existe solicitação pendente?
        cursor.execute(
            "SELECT id, status, motivo_recusa FROM pre_cadastro_pendentes "
            "WHERE email = %s ORDER BY id DESC LIMIT 1",
            (email_norm,),
        )
        pend = cursor.fetchone()
        if pend and pend["status"] == "pendente":
            return {
                "autorizado": False,
                "ja_pendente": True,
                "mensagem": "Você já fez sua solicitação de cadastro. Aguarde a aprovação do administrador.",
            }
        if pend and pend["status"] == "aprovado":
            return {
                "autorizado": False,
                "ja_cadastrado": True,
                "mensagem": "Sua solicitação já foi aprovada. Faça login normalmente.",
            }

        # 3) E-mail está na lista autorizada?
        cursor.execute(
            "SELECT id, nome_sugerido, status FROM pre_cadastro_emails WHERE email = %s",
            (email_norm,),
        )
        email_row = cursor.fetchone()
        if not email_row:
            return {
                "autorizado": False,
                "mensagem": "Este e-mail não está autorizado para auto-cadastro. Procure o administrador.",
            }
        if email_row["status"] == "usado":
            return {
                "autorizado": False,
                "ja_cadastrado": True,
                "mensagem": "Este e-mail já foi utilizado em um cadastro. Procure o administrador.",
            }

        resp = {
            "autorizado": True,
            "email": email_norm,
            "nome_sugerido": email_row["nome_sugerido"],
        }

        # 4) Recusa anterior — devolve motivo pra o usuário corrigir
        if pend and pend["status"] == "recusado":
            resp["recusado_anterior"] = True
            resp["motivo_recusa"] = pend["motivo_recusa"]
            resp["mensagem"] = "Seu cadastro anterior foi recusado. Veja o motivo e refaça."

        return resp

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.get("/grupos-publicos")
async def listar_grupos_publicos():
    """Lista grupos visíveis no auto-cadastro (visivel_signup=1)."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT g.id, g.name, g.description, g.department_id,
                   d.name AS department_name
              FROM cpe_grupo g
              LEFT JOIN departments d ON d.id = g.department_id
             WHERE g.visivel_signup = 1
             ORDER BY d.name, g.name
        """)
        return convert_datetime_list(cursor.fetchall())
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.get("/unidades-publicas")
async def listar_unidades_publicas():
    """Lista unidades ativas — usado no select do formulário de primeiro acesso."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, nome, sigla, cidade, uf
              FROM unidades_cpe
             WHERE ativo = 1
             ORDER BY nome
        """)
        return cursor.fetchall()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.get("/verificar-username")
async def verificar_username(username: str = Query(..., min_length=3, max_length=50)):
    """Checa em tempo real se o username escolhido está disponível.
    Retorna {disponivel: bool, motivo: str}."""
    try:
        u = validar_username_formato(username)
    except HTTPException as e:
        return {"disponivel": False, "motivo": e.detail}

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        if username_disponivel(cursor, u):
            return {"disponivel": True, "username": u}
        return {"disponivel": False, "motivo": "Username já está em uso. Escolha outro."}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.post("/solicitar", status_code=status.HTTP_201_CREATED)
async def solicitar_cadastro(payload: SolicitarPayload):
    """Cria uma solicitação de cadastro pendente de aprovação."""
    email_norm = payload.email.strip().lower()
    nome = payload.name.strip()

    # Valida e normaliza username + cpf
    username = validar_username_formato(payload.username)
    cpf_fmt  = validar_cpf(payload.cpf)

    logger.info(f"[PRECAD/SOLICITAR] {email_norm} -> grupo {payload.group_id} unidade {payload.unit_id} user '{username}'")

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        # Re-valida e-mail (pode ter mudado entre o verificar e o solicitar)
        cursor.execute("SELECT id FROM users WHERE email = %s", (email_norm,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="E-mail já cadastrado no sistema.")

        cursor.execute(
            "SELECT id, status FROM pre_cadastro_emails WHERE email = %s",
            (email_norm,),
        )
        email_row = cursor.fetchone()
        if not email_row:
            raise HTTPException(status_code=400, detail="E-mail não autorizado para auto-cadastro.")
        if email_row["status"] == "usado":
            raise HTTPException(status_code=400, detail="Este e-mail já foi utilizado em um cadastro.")

        # Bloqueia se já tem pendente pra esse mesmo e-mail
        cursor.execute(
            "SELECT id FROM pre_cadastro_pendentes WHERE email = %s AND status = 'pendente'",
            (email_norm,),
        )
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Já existe uma solicitação pendente para este e-mail.")

        # Username escolhido pelo usuário precisa estar disponível
        if not username_disponivel(cursor, username, ignorar_email=email_norm):
            raise HTTPException(status_code=400, detail="Username já está em uso. Escolha outro.")

        # CPF — bloqueia duplicidade no banco (se já tem user com esse CPF)
        cursor.execute("SELECT id FROM users WHERE cpf = %s LIMIT 1", (cpf_fmt,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Este CPF já está cadastrado no sistema.")

        # Valida grupo (e que esteja visível pra signup)
        cursor.execute(
            "SELECT id, name FROM cpe_grupo WHERE id = %s AND visivel_signup = 1",
            (payload.group_id,),
        )
        grupo = cursor.fetchone()
        if not grupo:
            raise HTTPException(status_code=400, detail="Grupo inválido ou não disponível para auto-cadastro.")

        # Valida unidade
        cursor.execute(
            "SELECT id, nome FROM unidades_cpe WHERE id = %s AND ativo = 1",
            (payload.unit_id,),
        )
        unidade = cursor.fetchone()
        if not unidade:
            raise HTTPException(status_code=400, detail="Unidade inválida.")

        password_hash = bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        # Se já existe um pendente "recusado" para este e-mail, atualiza ele em vez de criar novo
        cursor.execute(
            "SELECT id FROM pre_cadastro_pendentes WHERE email = %s AND status = 'recusado'",
            (email_norm,),
        )
        recusado = cursor.fetchone()
        if recusado:
            cursor.execute("""
                UPDATE pre_cadastro_pendentes
                   SET name = %s, cpf = %s, username = %s, password_hash = %s,
                       group_id = %s, unit_id = %s, status = 'pendente',
                       solicitado_em = CURRENT_TIMESTAMP,
                       respondido_por = NULL, respondido_em = NULL,
                       motivo_recusa = NULL
                 WHERE id = %s
            """, (nome, cpf_fmt, username, password_hash,
                  payload.group_id, payload.unit_id, recusado["id"]))
            pend_id = recusado["id"]
        else:
            cursor.execute("""
                INSERT INTO pre_cadastro_pendentes
                    (email, name, cpf, username, password_hash, group_id, unit_id, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pendente')
            """, (email_norm, nome, cpf_fmt, username, password_hash,
                  payload.group_id, payload.unit_id))
            pend_id = cursor.lastrowid

        notificar_admins(
            cursor,
            f"Novo pré-cadastro pendente: {nome} ({email_norm}) — {grupo['name']} / {unidade['nome']}",
        )

        conn.commit()
        logger.info(f"[PRECAD/SOLICITAR] ✅ id={pend_id} username={username} cpf={cpf_fmt[:6]}***")

        return {
            "ok": True,
            "id": pend_id,
            "username": username,
            "mensagem": "Solicitação enviada! Aguarde a aprovação do administrador.",
        }

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[PRECAD/SOLICITAR] ❌ {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao solicitar cadastro: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ============================================================
# ENDPOINTS ADMINISTRATIVOS
# ============================================================

@router.post("/upload-csv")
async def upload_csv(arquivo: UploadFile = File(...), importado_por: Optional[int] = Query(None)):
    """
    Importa lista de e-mails autorizados a partir de um CSV.
    Formato aceito: 'email' ou 'email,nome' (uma linha por usuário).
    Cabeçalho é detectado automaticamente.
    """
    if not arquivo.filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .csv ou .txt")

    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    linhas = parsear_csv(conteudo)
    if not linhas:
        raise HTTPException(status_code=400, detail="Nenhum e-mail válido encontrado no arquivo")

    logger.info(f"[PRECAD/CSV] {len(linhas)} linha(s) válidas em {arquivo.filename}")

    conn = get_db_or_404()
    cursor = None
    importados = 0
    duplicados = 0
    try:
        cursor = conn.cursor(dictionary=True)
        for linha in linhas:
            cursor.execute(
                "SELECT id FROM pre_cadastro_emails WHERE email = %s",
                (linha["email"],),
            )
            if cursor.fetchone():
                # já existe — atualiza nome se vier preenchido
                if linha["nome"]:
                    cursor.execute(
                        "UPDATE pre_cadastro_emails SET nome_sugerido = %s WHERE email = %s",
                        (linha["nome"], linha["email"]),
                    )
                duplicados += 1
                continue
            cursor.execute(
                "INSERT INTO pre_cadastro_emails (email, nome_sugerido, importado_por) "
                "VALUES (%s, %s, %s)",
                (linha["email"], linha["nome"], importado_por),
            )
            importados += 1
        conn.commit()
        return {
            "ok": True,
            "total_linhas": len(linhas),
            "importados": importados,
            "duplicados": duplicados,
        }
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[PRECAD/CSV] ❌ {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao importar CSV: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.get("/pendentes")
async def listar_pendentes(status_filtro: str = Query("pendente")):
    """Lista solicitações pendentes (default) ou todas."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        where = ""
        params: tuple = ()
        if status_filtro and status_filtro != "todos":
            where = "WHERE p.status = %s"
            params = (status_filtro,)
        cursor.execute(f"""
            SELECT p.id, p.email, p.name, p.cpf, p.username,
                   p.group_id, p.unit_id, p.status,
                   p.solicitado_em, p.respondido_em, p.motivo_recusa,
                   g.name AS group_name,
                   d.name AS department_name,
                   u.nome AS unit_name, u.sigla AS unit_sigla
              FROM pre_cadastro_pendentes p
              LEFT JOIN cpe_grupo g    ON g.id = p.group_id
              LEFT JOIN departments d  ON d.id = g.department_id
              LEFT JOIN unidades_cpe u ON u.id = p.unit_id
              {where}
             ORDER BY p.solicitado_em DESC
        """, params)
        return convert_datetime_list(cursor.fetchall())
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.post("/{pendente_id}/aprovar")
async def aprovar(pendente_id: int, aprovado_por: Optional[int] = Query(None)):
    """
    Cria o usuário definitivo (role=USER) com base na solicitação,
    marca o e-mail da lista como 'usado' e a solicitação como 'aprovado'.
    """
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM pre_cadastro_pendentes WHERE id = %s",
            (pendente_id,),
        )
        pend = cursor.fetchone()
        if not pend:
            raise HTTPException(status_code=404, detail="Solicitação não encontrada")
        if pend["status"] != "pendente":
            raise HTTPException(status_code=400, detail=f"Solicitação já está {pend['status']}")

        # Garante que e-mail/username não conflitam
        cursor.execute("SELECT id FROM users WHERE email = %s", (pend["email"],))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Já existe usuário com este e-mail")

        # Username escolhido pelo usuário. Se entrou em conflito enquanto estava
        # na fila (caso raro — alguém pegou esse user enquanto pendia), gera sufixo.
        username_final = garantir_username_unico(cursor, pend["username"])

        # department_id herda do grupo
        cursor.execute(
            "SELECT department_id FROM cpe_grupo WHERE id = %s",
            (pend["group_id"],),
        )
        grp = cursor.fetchone()
        department_id = grp["department_id"] if grp else None

        # Valida que CPF da pendência ainda não foi usado por outro user
        # (alguém pode ter sido cadastrado manualmente enquanto pendia)
        if pend.get("cpf"):
            cursor.execute("SELECT id FROM users WHERE cpf = %s LIMIT 1", (pend["cpf"],))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="CPF da solicitação já está cadastrado em outro usuário.")

        cursor.execute("""
            INSERT INTO users (name, email, cpf, username, password_hash, role,
                               group_id, department_id, unit_id, is_active)
            VALUES (%s, %s, %s, %s, %s, 'USER', %s, %s, %s, 1)
        """, (
            pend["name"], pend["email"], pend.get("cpf"), username_final,
            pend["password_hash"],
            pend["group_id"], department_id, pend.get("unit_id"),
        ))
        new_user_id = cursor.lastrowid

        cursor.execute("""
            UPDATE pre_cadastro_pendentes
               SET status = 'aprovado',
                   respondido_por = %s,
                   respondido_em = CURRENT_TIMESTAMP,
                   user_id = %s
             WHERE id = %s
        """, (aprovado_por, new_user_id, pendente_id))

        cursor.execute("""
            UPDATE pre_cadastro_emails
               SET status = 'usado',
                   usado_em = CURRENT_TIMESTAMP,
                   user_id = %s
             WHERE email = %s
        """, (new_user_id, pend["email"]))

        conn.commit()
        logger.info(f"[PRECAD/APROVAR] ✅ pendente {pendente_id} -> user {new_user_id}")

        # Pega nome do grupo pra incluir no email (consulta separada — não falha o aprovar se quebrar)
        grupo_nome = None
        try:
            cursor.execute("SELECT name FROM cpe_grupo WHERE id = %s", (pend["group_id"],))
            row = cursor.fetchone()
            if row: grupo_nome = row["name"]
        except Exception:
            pass

        # Envia email de boas-vindas (async — não bloqueia a resposta)
        try:
            link_login = f"{PUBLIC_BASE_URL}/SistemaCPE/web/login.html"
            assunto, html = email_cadastro_aprovado(
                nome=pend["name"],
                username=username_final,
                grupo_nome=grupo_nome,
                link_login=link_login,
            )
            enviar_email(para=pend["email"], assunto=assunto, html=html)
            logger.info(f"[PRECAD/APROVAR] 📧 email de boas-vindas disparado para {pend['email']}")
        except Exception as err:
            # Não derruba a aprovação se o email falhar — admin pode reenviar depois
            logger.error(f"[PRECAD/APROVAR] ⚠️ falha ao enviar email pra {pend['email']}: {err}")

        return {"ok": True, "user_id": new_user_id, "username": username_final}

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[PRECAD/APROVAR] ❌ {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao aprovar: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.post("/{pendente_id}/recusar")
async def recusar(pendente_id: int, payload: RecusarPayload, recusado_por: Optional[int] = Query(None)):
    """Marca a solicitação como recusada com motivo. Permite que o usuário refaça."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, status FROM pre_cadastro_pendentes WHERE id = %s",
            (pendente_id,),
        )
        pend = cursor.fetchone()
        if not pend:
            raise HTTPException(status_code=404, detail="Solicitação não encontrada")
        if pend["status"] != "pendente":
            raise HTTPException(status_code=400, detail=f"Solicitação já está {pend['status']}")

        cursor.execute("""
            UPDATE pre_cadastro_pendentes
               SET status = 'recusado',
                   motivo_recusa = %s,
                   respondido_por = %s,
                   respondido_em = CURRENT_TIMESTAMP
             WHERE id = %s
        """, (payload.motivo.strip(), recusado_por, pendente_id))
        conn.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[PRECAD/RECUSAR] ❌ {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao recusar: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.get("/emails")
async def listar_emails():
    """Lista os e-mails autorizados (para admin gerenciar a lista importada)."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, email, nome_sugerido, status, importado_em, usado_em
              FROM pre_cadastro_emails
             ORDER BY importado_em DESC
        """)
        return convert_datetime_list(cursor.fetchall())
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


class EmailAutorizadoManualIn(BaseModel):
    email: EmailStr
    nome_sugerido: Optional[str] = Field(None, max_length=120)
    importado_por: Optional[int] = None


@router.post("/emails", status_code=status.HTTP_201_CREATED)
async def adicionar_email_manual(payload: EmailAutorizadoManualIn):
    """
    Adiciona 1 e-mail à lista de autorizados manualmente (sem passar por CSV).
    Regras:
      - E-mail é normalizado (lowercase, trim).
      - 409 se já existe usuário com esse e-mail.
      - 409 se já está na lista (com detail informativo do status).
      - Insert simples caso contrário.
    """
    email_norm = payload.email.strip().lower()
    nome = (payload.nome_sugerido or "").strip() or None

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM users WHERE email = %s", (email_norm,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=409,
                detail="Este e-mail já pertence a um usuário cadastrado no sistema.",
            )

        cursor.execute(
            "SELECT id, status FROM pre_cadastro_emails WHERE email = %s",
            (email_norm,),
        )
        row = cursor.fetchone()
        if row:
            if row["status"] == "usado":
                raise HTTPException(
                    status_code=409,
                    detail="Este e-mail já foi utilizado em um cadastro.",
                )
            raise HTTPException(
                status_code=409,
                detail="Este e-mail já está na lista de autorizados (aguardando 1º acesso).",
            )

        cursor.execute(
            "INSERT INTO pre_cadastro_emails (email, nome_sugerido, importado_por) "
            "VALUES (%s, %s, %s)",
            (email_norm, nome, payload.importado_por),
        )
        conn.commit()
        new_id = cursor.lastrowid
        logger.info(f"[PRECAD/MANUAL] ✅ id={new_id} email={email_norm} nome='{nome or ''}'")
        return {
            "ok": True,
            "id": new_id,
            "email": email_norm,
            "nome_sugerido": nome,
            "status": "disponivel",
        }
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[PRECAD/MANUAL] ❌ {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao adicionar e-mail: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.delete("/emails/{email_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_email(email_id: int):
    """Remove um e-mail da lista de autorizados (só se não foi usado)."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT status FROM pre_cadastro_emails WHERE id = %s",
            (email_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="E-mail não encontrado")
        if row["status"] == "usado":
            raise HTTPException(status_code=400, detail="Não é possível remover um e-mail já utilizado em cadastro")
        cursor.execute("DELETE FROM pre_cadastro_emails WHERE id = %s", (email_id,))
        conn.commit()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
