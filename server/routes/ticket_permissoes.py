"""
Permissoes de categoria por membro do grupo.

Responsavel do grupo (RESPONSAVEL_GRUPO) pode configurar quais
categorias/subcategorias cada membro (USER) do grupo dele consegue
ver na lista de tickets. Ver migration 089.

Endpoints (prefix /api/tickets/permissoes):
  GET    /grupo/{group_id}/membros   -> lista membros do grupo + resumo
                                          (quantas categorias restritas)
  GET    /user/{user_id}             -> detalhes das restricoes do membro
  PUT    /user/{user_id}             -> substitui as restricoes do membro
                                          {categorias: [{categoria_id,
                                                          subcategoria_id?}]}
  DELETE /user/{user_id}             -> zera todas as restricoes (volta
                                          a ver tudo do grupo)

Regra de acesso: SO ADMIN ou RESPONSAVEL_GRUPO do MESMO grupo do user
alvo pode ver/editar as permissoes. Ninguem mais.
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Depends, Path
from pydantic import BaseModel, Field

from database import get_db_or_404
from security import get_current_user

router = APIRouter(prefix="/api/tickets/permissoes", tags=["tickets-permissoes"])
logger = logging.getLogger(__name__)


# ============================================================
# Models
# ============================================================
class CategoriaRestricao(BaseModel):
    categoria_id: int = Field(..., gt=0)
    subcategoria_id: Optional[int] = Field(None, gt=0)


class RestricoesUpdate(BaseModel):
    categorias: List[CategoriaRestricao] = Field(default_factory=list)


# ============================================================
# Helpers de autorizacao
# ============================================================
def _role(u: dict) -> str:
    return (u.get("role") or "").upper()


def _pode_gerenciar_perms(cu: dict, group_id_alvo: int) -> bool:
    """ADMIN gerencia qualquer grupo. RESPONSAVEL_GRUPO gerencia so o
    proprio."""
    if _role(cu) == "ADMIN":
        return True
    if _role(cu) == "RESPONSAVEL_GRUPO":
        return cu.get("group_id") == group_id_alvo
    return False


def _fetch_membro(cursor, user_id: int) -> Optional[dict]:
    cursor.execute("""
        SELECT u.id, u.name, u.email, u.role, u.group_id, g.name AS group_name
          FROM users u
          LEFT JOIN cpe_grupo g ON g.id = u.group_id
         WHERE u.id = %s AND u.is_active = 1
    """, (user_id,))
    return cursor.fetchone()


# ============================================================
# Endpoints
# ============================================================
@router.get("/grupo/{group_id}/membros")
async def listar_membros_do_grupo(
    group_id: int = Path(..., gt=0),
    current_user: dict = Depends(get_current_user),
):
    """Lista todos os membros do grupo + quantas categorias restritas
    cada um tem. Se um membro tem 0 restricoes, ve tudo do grupo."""
    if not _pode_gerenciar_perms(current_user, group_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                             detail="Sem permissao pra gerenciar permissoes deste grupo.")

    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT u.id, u.name, u.email, u.role,
                   COALESCE(mc.n, 0) AS restricoes_count,
                   COALESCE(mc.cats, 0) AS categorias_liberadas,
                   COALESCE(mc.subs, 0) AS subcategorias_liberadas
              FROM users u
              LEFT JOIN (
                    SELECT user_id,
                           COUNT(*) AS n,
                           SUM(CASE WHEN subcategoria_id IS NULL THEN 1 ELSE 0 END) AS cats,
                           SUM(CASE WHEN subcategoria_id IS NOT NULL THEN 1 ELSE 0 END) AS subs
                      FROM ticket_membro_categorias
                     WHERE group_id = %s
                     GROUP BY user_id
                   ) mc ON mc.user_id = u.id
             WHERE u.group_id = %s
               AND u.is_active = 1
             ORDER BY u.name
        """, (group_id, group_id))
        rows = cur.fetchall() or []
    finally:
        cur.close(); conn.close()

    for r in rows:
        r["ve_tudo"] = (r["restricoes_count"] == 0)
    return {"success": True, "membros": rows}


@router.get("/user/{user_id}")
async def obter_restricoes(
    user_id: int = Path(..., gt=0),
    current_user: dict = Depends(get_current_user),
):
    """Detalhes das restricoes de um membro (com nomes de categoria/subcategoria)."""
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        membro = _fetch_membro(cur, user_id)
        if not membro:
            raise HTTPException(status_code=404, detail="Membro nao encontrado")
        if not _pode_gerenciar_perms(current_user, membro["group_id"]):
            raise HTTPException(status_code=403,
                                 detail="Sem permissao pra ver as restricoes deste membro.")

        cur.execute("""
            SELECT mc.id, mc.categoria_id, mc.subcategoria_id,
                   c.nome AS categoria_nome,
                   sc.nome AS subcategoria_nome
              FROM ticket_membro_categorias mc
              LEFT JOIN categorias    c  ON c.id  = mc.categoria_id
              LEFT JOIN subcategorias sc ON sc.id = mc.subcategoria_id
             WHERE mc.user_id = %s
             ORDER BY c.nome, sc.nome
        """, (user_id,))
        restricoes = cur.fetchall() or []

        # Todas as categorias/subcategorias do grupo — pra popular UI
        cur.execute("""
            SELECT c.id AS categoria_id, c.nome AS categoria_nome,
                   sc.id AS subcategoria_id, sc.nome AS subcategoria_nome
              FROM categorias c
              LEFT JOIN subcategorias sc
                     ON sc.categoria_id = c.id AND sc.ativo = 1
             WHERE c.group_id = %s AND c.ativo = 1
             ORDER BY c.nome, sc.nome
        """, (membro["group_id"],))
        arv = cur.fetchall() or []

        # Empilha em [{categoria_id, categoria_nome, subcategorias: [...]}, ...]
        cats_map = {}
        for row in arv:
            cid = row["categoria_id"]
            if cid not in cats_map:
                cats_map[cid] = {
                    "categoria_id": cid,
                    "categoria_nome": row["categoria_nome"],
                    "subcategorias": [],
                }
            if row.get("subcategoria_id"):
                cats_map[cid]["subcategorias"].append({
                    "subcategoria_id": row["subcategoria_id"],
                    "subcategoria_nome": row["subcategoria_nome"],
                })
        categorias_disponiveis = list(cats_map.values())
    finally:
        cur.close(); conn.close()

    return {
        "success": True,
        "membro": {
            "id": membro["id"], "name": membro["name"], "email": membro["email"],
            "role": membro["role"], "group_id": membro["group_id"],
            "group_name": membro["group_name"],
        },
        "restricoes": restricoes,
        "categorias_disponiveis": categorias_disponiveis,
    }


@router.put("/user/{user_id}")
async def salvar_restricoes(
    user_id: int,
    body: RestricoesUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Substitui TODAS as restricoes do membro pela lista enviada.
    Lista vazia = zera restricoes (volta ao default 've tudo')."""
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        membro = _fetch_membro(cur, user_id)
        if not membro:
            raise HTTPException(status_code=404, detail="Membro nao encontrado")
        if not _pode_gerenciar_perms(current_user, membro["group_id"]):
            raise HTTPException(status_code=403,
                                 detail="Sem permissao pra editar as restricoes deste membro.")
        # Nao permitir restringir ADMIN / RESPONSAVEL_GRUPO / TI / MANAGER —
        # essas roles enxergam tudo por design; restringi-los seria confuso.
        if (membro.get("role") or "USER").upper() != "USER":
            raise HTTPException(
                status_code=400,
                detail=(f"Nao e possivel restringir um {membro.get('role')} "
                        "— restricoes valem so pra USER."),
            )

        gid = membro["group_id"]

        # Zera tudo e reinsere (mais simples que diff)
        cur.execute("DELETE FROM ticket_membro_categorias WHERE user_id = %s", (user_id,))

        # Dedup e valida cada categoria/subcategoria pertencer ao grupo alvo
        seen = set()
        inserted = 0
        for item in body.categorias:
            key = (item.categoria_id, item.subcategoria_id or 0)
            if key in seen:
                continue
            seen.add(key)

            # Confere categoria pertence ao grupo
            cur.execute("SELECT group_id FROM categorias WHERE id = %s AND ativo = 1",
                        (item.categoria_id,))
            crow = cur.fetchone()
            if not crow or crow["group_id"] != gid:
                continue  # ignora silenciosamente categorias fora do grupo

            # Se subcategoria, confere que pertence a categoria dada
            if item.subcategoria_id:
                cur.execute(
                    "SELECT categoria_id FROM subcategorias WHERE id = %s AND ativo = 1",
                    (item.subcategoria_id,),
                )
                srow = cur.fetchone()
                if not srow or srow["categoria_id"] != item.categoria_id:
                    continue

            cur.execute("""
                INSERT INTO ticket_membro_categorias
                    (user_id, group_id, categoria_id, subcategoria_id, created_by)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, gid, item.categoria_id, item.subcategoria_id, current_user["id"]))
            inserted += 1

        conn.commit()
        logger.info(
            f"[TICKET-PERMS] user_id={user_id} agora tem {inserted} restricao(oes) "
            f"(configurado por {current_user['id']})"
        )
    finally:
        cur.close(); conn.close()

    return {"success": True, "restricoes_ativas": inserted}


@router.delete("/user/{user_id}")
async def zerar_restricoes(
    user_id: int = Path(..., gt=0),
    current_user: dict = Depends(get_current_user),
):
    """Remove todas as restricoes do membro (volta a ver tudo do grupo)."""
    conn = get_db_or_404()
    cur = conn.cursor(dictionary=True)
    try:
        membro = _fetch_membro(cur, user_id)
        if not membro:
            raise HTTPException(status_code=404, detail="Membro nao encontrado")
        if not _pode_gerenciar_perms(current_user, membro["group_id"]):
            raise HTTPException(status_code=403, detail="Sem permissao.")

        cur.execute("DELETE FROM ticket_membro_categorias WHERE user_id = %s", (user_id,))
        n = cur.rowcount or 0
        conn.commit()
    finally:
        cur.close(); conn.close()
    return {"success": True, "removidas": n}


def conceder_acesso_auto(cursor, user_id: int, categoria_id: Optional[int],
                          subcategoria_id: Optional[int], granted_by: int) -> bool:
    """Concede acesso a uma (sub)categoria pra um user sem sobrescrever
    o que ele ja tinha. Usado quando o gestor atribui um ticket pra um
    membro restrito: garante que ele passa a ver aquele ticket (e todos
    dessa (sub)categoria dali pra frente).

    - Se user nao tem NENHUMA restricao (ve tudo), nao faz nada.
    - Se categoria_id do ticket eh NULL, nao faz nada.
    - Se ja existe row exata, nao faz nada.
    - Se ha row 'categoria inteira' pra essa categoria, nao precisa
      criar a subcategoria (subset ja coberto).

    Retorna True se INSERT rolou (log util no chamador).
    """
    if not categoria_id or not user_id:
        return False

    # user com 0 restricoes? nao mexer
    cursor.execute("SELECT COUNT(*) AS n FROM ticket_membro_categorias WHERE user_id=%s",
                   (user_id,))
    if not ((cursor.fetchone() or {}).get("n") or 0):
        return False

    # busca group do user (redundante mas necessario pra insert)
    cursor.execute("SELECT group_id FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone() or {}
    gid = row.get("group_id")
    if not gid:
        return False

    # ja tem cobertura?
    cursor.execute("""
        SELECT id, subcategoria_id FROM ticket_membro_categorias
         WHERE user_id = %s AND categoria_id = %s
    """, (user_id, categoria_id))
    existentes = cursor.fetchall() or []
    for r in existentes:
        if r["subcategoria_id"] is None:
            return False  # ja ve categoria inteira
        if subcategoria_id and r["subcategoria_id"] == subcategoria_id:
            return False  # ja ve essa subcategoria especifica

    # Insere row (categoria + subcategoria opcional)
    try:
        cursor.execute("""
            INSERT INTO ticket_membro_categorias
                (user_id, group_id, categoria_id, subcategoria_id, created_by)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, gid, categoria_id, subcategoria_id, granted_by))
        logger.info(f"[TICKET-PERMS] auto-grant user={user_id} cat={categoria_id} sub={subcategoria_id} por {granted_by}")
        return True
    except Exception as e:
        logger.warning(f"[TICKET-PERMS] auto-grant falhou user={user_id}: {e}")
        return False
