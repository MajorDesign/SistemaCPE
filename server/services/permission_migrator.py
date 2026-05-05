"""
Migrador one-shot dos dados antigos de `page_permissions` (formato CSV
em `allowed_roles`) para a estrutura relacional nova
(`permission_page_role`).

Roda no startup do FastAPI **uma vez**: usa uma flag em
`permission_pages.description` ou um marker simples para detectar se
já rodou. Se a tabela velha não existir mais (ambiente novo, fase 4),
não faz nada.

Não apaga nada da tabela velha — ela é renomeada para
`_legacy_page_permissions` apenas na FASE 4 da refatoração.
"""

from __future__ import annotations

import logging
from database import get_db_connection

logger = logging.getLogger(__name__)


def _tabela_existe(cursor, nome: str) -> bool:
    cursor.execute("""
        SELECT 1 FROM information_schema.TABLES
         WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
    """, (nome,))
    return cursor.fetchone() is not None


def migrate_legacy_page_permissions() -> dict:
    """
    Para cada linha em `page_permissions` (legado), faz split do CSV
    `allowed_roles` e insere uma linha por role em
    `permission_page_role` — desde que a página exista no catálogo.

    Idempotente: usa INSERT IGNORE.
    Retorna: {'paginas_processadas': N, 'roles_migrados': M, 'puladas': P}
    """
    conn = None
    cursor = None
    paginas = 0
    roles_migrados = 0
    puladas = 0

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1) Tabela legacy ainda existe?
        if not _tabela_existe(cursor, "page_permissions"):
            logger.info("[PERM_MIGRATOR] page_permissions não existe — nada a migrar")
            return {"paginas_processadas": 0, "roles_migrados": 0, "puladas": 0}

        # 2) Lê todas as regras antigas
        cursor.execute("SELECT page_name, allowed_roles FROM page_permissions")
        legados = cursor.fetchall()

        # 3) Roles válidos no enum atual
        roles_validos = {"USER", "RESPONSAVEL_GRUPO", "TI", "MANAGER", "ADMIN"}

        for row in legados:
            page_key = (row.get("page_name") or "").strip().upper()
            csv      = row.get("allowed_roles") or ""
            if not page_key:
                continue

            # 4) Página existe no catálogo novo?
            cursor.execute(
                "SELECT 1 FROM permission_pages WHERE page_key = %s",
                (page_key,),
            )
            if not cursor.fetchone():
                logger.info(f"[PERM_MIGRATOR] ↩️ '{page_key}' não está no catálogo — pulado")
                puladas += 1
                continue

            paginas += 1

            # 5) Insere cada role do CSV
            for role in [r.strip().upper() for r in csv.split(",") if r.strip()]:
                if role not in roles_validos:
                    continue
                cursor.execute("""
                    INSERT IGNORE INTO permission_page_role (page_key, role)
                    VALUES (%s, %s)
                """, (page_key, role))
                if cursor.rowcount > 0:
                    roles_migrados += 1

        conn.commit()
        logger.info(
            f"[PERM_MIGRATOR] ✅ páginas processadas={paginas}, "
            f"roles migrados={roles_migrados}, puladas={puladas}"
        )
        return {
            "paginas_processadas": paginas,
            "roles_migrados": roles_migrados,
            "puladas": puladas,
        }

    except Exception as err:
        logger.error(f"[PERM_MIGRATOR] ❌ {err}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
