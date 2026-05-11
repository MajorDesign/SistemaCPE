"""
Seeder de permissões — fonte da verdade do catálogo de páginas.

Roda no startup do FastAPI e popula `permission_pages` com a lista
canônica abaixo, fazendo `INSERT IGNORE` para não sobrescrever páginas
já configuradas pelo admin (apenas adiciona novas).

PARA ADICIONAR UMA PÁGINA NOVA AO SISTEMA:
    1) Adicionar uma entrada em PAGES_CATALOG abaixo
    2) Reiniciar a API
    3) A página aparece automaticamente em /permissions.html
       e o admin configura quais roles/grupos podem acessar.
"""

from __future__ import annotations

import logging
from typing import TypedDict

from database import get_db_connection

logger = logging.getLogger(__name__)


class PageDef(TypedDict, total=False):
    page_key:     str
    display_name: str
    description:  str
    category:     str   # 'admin' | 'operational' | 'config'
    icon:         str   # bootstrap-icons sem prefixo (ex: 'bi-calendar')
    url:          str
    ordem:        int
    # default_roles é aplicado SOMENTE quando a página é inserida pela
    # primeira vez. Não sobrescreve configuração do admin em re-runs.
    default_roles: list[str]


# Defaults sensatos por categoria — usados quando a página é inserida
# pela primeira vez se 'default_roles' não estiver explícito.
_DEFAULT_ROLES_POR_CATEGORIA = {
    "operational": ["USER", "RESPONSAVEL_GRUPO", "TI", "MANAGER", "ADMIN"],
    "admin":       ["ADMIN", "TI"],
    "config":      ["USER", "RESPONSAVEL_GRUPO", "TI", "MANAGER", "ADMIN"],
}


# =====================================================================
# CATÁLOGO CANÔNICO DE PÁGINAS DO SISTEMA
# =====================================================================
# Esta é a fonte da verdade. NÃO editar diretamente em SQL — sempre
# adicionar/remover aqui e reiniciar a API. Mudanças nesta lista são
# rastreadas pelo git.
# =====================================================================
PAGES_CATALOG: list[PageDef] = [
    # ───────── Operacionais (uso diário) ─────────
    {"page_key": "DASHBOARD",        "display_name": "Dashboard",
     "description": "Painel principal do sistema",
     "category": "operational", "icon": "bi-speedometer2",
     "url": "/SistemaCPE/index.html",                              "ordem": 10},

    {"page_key": "TICKETS",          "display_name": "Tickets",
     "description": "Gerenciamento de chamados e suporte",
     "category": "operational", "icon": "bi-ticket-detailed",
     "url": "/SistemaCPE/web/pages/tickets.html",                  "ordem": 20},

    {"page_key": "TASKS",            "display_name": "Tarefas",
     "description": "Gerenciamento de tarefas e projetos",
     "category": "operational", "icon": "bi-check2-square",
     "url": "/SistemaCPE/web/pages/tasks.html",                    "ordem": 30},

    {"page_key": "PROJECTS",         "display_name": "Projetos",
     "description": "Visão de projetos e portfólios",
     "category": "operational", "icon": "bi-folder",
     "url": "/SistemaCPE/web/pages/projects.html",                 "ordem": 40},

    {"page_key": "AGENDA",           "display_name": "Agenda",
     "description": "Calendário integrado com Carbonio",
     "category": "operational", "icon": "bi-calendar-event",
     "url": "/SistemaCPE/web/pages/agenda.html",                   "ordem": 50},

    {"page_key": "CHAT",             "display_name": "Chat",
     "description": "Comunicação interna entre usuários",
     "category": "operational", "icon": "bi-chat-dots",
     "url": "/SistemaCPE/web/pages/chat.html",                     "ordem": 60},

    {"page_key": "RECEPCAO",         "display_name": "Recepção",
     "description": "Reservas de salas e gestão de visitantes",
     "category": "operational", "icon": "bi-door-open",
     "url": "/SistemaCPE/web/pages/recepcao.html",                 "ordem": 70},

    {"page_key": "FLEET",            "display_name": "Frotas",
     "description": "Gestão de veículos, manutenção e reservas",
     "category": "operational", "icon": "bi-truck",
     "url": "/SistemaCPE/web/pages/fleet.html",                    "ordem": 80},

    {"page_key": "CONTRATOS",        "display_name": "Contratos",
     "description": "Gestão de contratos e documentos",
     "category": "operational", "icon": "bi-file-earmark-text",
     "url": "/SistemaCPE/web/pages/contratos.html",                "ordem": 90},

    {"page_key": "AVALIACOES",       "display_name": "Avaliações",
     "description": "Avaliações de tickets e performance",
     "category": "operational", "icon": "bi-star",
     "url": "/SistemaCPE/web/pages/avaliacoes.html",               "ordem": 100},

    {"page_key": "KNOWLEDGE_BASE",   "display_name": "Base de Conhecimento",
     "description": "Artigos, manuais e documentação",
     "category": "operational", "icon": "bi-book",
     "url": "/SistemaCPE/web/pages/knowledge-base.html",           "ordem": 110},

    {"page_key": "DOWNLOAD_AGENTS",  "display_name": "Download de Agentes",
     "description": "Baixar agentes de instalação",
     "category": "operational", "icon": "bi-download",
     "url": "/SistemaCPE/web/pages/download-agents.html",          "ordem": 120},

    # ───────── Administrativas ─────────
    {"page_key": "USERS",            "display_name": "Usuários",
     "description": "Gerenciamento de usuários do sistema",
     "category": "admin", "icon": "bi-people",
     "url": "/SistemaCPE/web/pages/users.html",                    "ordem": 200},

    {"page_key": "GROUPS",           "display_name": "Grupos",
     "description": "Gerenciamento de grupos e departamentos",
     "category": "admin", "icon": "bi-diagram-3",
     "url": "/SistemaCPE/web/pages/groups.html",                   "ordem": 210},

    {"page_key": "PERMISSIONS",      "display_name": "Permissões",
     "description": "Controle de acesso a páginas e funcionalidades",
     "category": "admin", "icon": "bi-shield-lock",
     "url": "/SistemaCPE/web/pages/permissions.html",              "ordem": 220},

    {"page_key": "INVENTORY",        "display_name": "Inventário",
     "description": "Inventário de equipamentos",
     "category": "admin", "icon": "bi-pc-display",
     "url": "/SistemaCPE/web/pages/inventory.html",                "ordem": 230},

    {"page_key": "INVENTORY_TI",     "display_name": "Inventário T.I.",
     "description": "Dispositivos monitorados por agente — notebooks, desktops, servidores",
     "category": "admin", "icon": "bi-laptop",
     "url": "/SistemaCPE/web/pages/inventory-ti.html",             "ordem": 231,
     "default_roles": ["ADMIN", "TI", "MANAGER"]},

    {"page_key": "NETWORK",          "display_name": "Monitoramento de Rede",
     "description": "Painel de status dos Mikrotik das unidades CPE (WANs, ping, lentidão)",
     "category": "admin", "icon": "bi-broadcast-pin",
     "url": "/SistemaCPE/web/pages/network.html",                  "ordem": 232,
     "default_roles": ["ADMIN", "TI"]},

    {"page_key": "PASSWORD_VAULT",   "display_name": "Cofre de Senhas",
     "description": "Cofre de senhas com acesso por grupo",
     "category": "admin", "icon": "bi-shield-lock-fill",
     "url": "/SistemaCPE/web/pages/password-vault.html",           "ordem": 240},

    {"page_key": "REPORTS",          "display_name": "Relatórios",
     "description": "Relatórios e análises do sistema",
     "category": "admin", "icon": "bi-graph-up",
     "url": "/SistemaCPE/web/pages/reports.html",                  "ordem": 250},

    {"page_key": "BILLING",          "display_name": "Faturamento",
     "description": "Faturamento e pagamentos",
     "category": "admin", "icon": "bi-credit-card",
     "url": "/SistemaCPE/web/pages/billing.html",                  "ordem": 260},

    {"page_key": "REGISTRATIONS",    "display_name": "Cadastros",
     "description": "Cadastros diversos do sistema",
     "category": "admin", "icon": "bi-person-plus",
     "url": "/SistemaCPE/web/pages/registrations.html",            "ordem": 270},

    # ───────── Configuração ─────────
    {"page_key": "SETTINGS",         "display_name": "Configurações",
     "description": "Configurações pessoais e do sistema",
     "category": "config", "icon": "bi-gear",
     "url": "/SistemaCPE/web/pages/settings.html",                 "ordem": 300},
]


def seed_pages() -> dict:
    """
    Faz INSERT IGNORE de cada página em `permission_pages`.
    Não sobrescreve páginas existentes — apenas adiciona novas
    e atualiza os campos descritivos das que já estão lá.

    Retorna: {'inseridos': N, 'atualizados': M, 'total': T}
    """
    conn = None
    cursor = None
    inseridos = 0
    atualizados = 0

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        for page in PAGES_CATALOG:
            cursor.execute(
                "SELECT page_key FROM permission_pages WHERE page_key = %s",
                (page["page_key"],),
            )
            existe = cursor.fetchone() is not None

            if existe:
                # Atualiza apenas os campos descritivos (não toca em is_active
                # que pode ter sido alterado pelo admin)
                cursor.execute("""
                    UPDATE permission_pages
                       SET display_name = %s,
                           description  = %s,
                           category     = %s,
                           icon         = %s,
                           url          = %s,
                           ordem        = %s
                     WHERE page_key = %s
                """, (
                    page["display_name"],
                    page.get("description"),
                    page.get("category", "operational"),
                    page.get("icon", "bi-file-earmark"),
                    page.get("url"),
                    page.get("ordem", 100),
                    page["page_key"],
                ))
                atualizados += 1
            else:
                cursor.execute("""
                    INSERT INTO permission_pages
                        (page_key, display_name, description, category, icon, url, ordem, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
                """, (
                    page["page_key"],
                    page["display_name"],
                    page.get("description"),
                    page.get("category", "operational"),
                    page.get("icon", "bi-file-earmark"),
                    page.get("url"),
                    page.get("ordem", 100),
                ))
                inseridos += 1

                # Página recém-criada: aplica roles default da categoria
                # (ou explícitos em default_roles). Re-runs NÃO mexem nisso.
                roles_default = page.get("default_roles") or \
                    _DEFAULT_ROLES_POR_CATEGORIA.get(
                        page.get("category", "operational"), []
                    )
                for role in roles_default:
                    cursor.execute("""
                        INSERT IGNORE INTO permission_page_role (page_key, role)
                        VALUES (%s, %s)
                    """, (page["page_key"], role))

        conn.commit()
        logger.info(f"[PERM_SEEDER] ✅ {inseridos} novas páginas, {atualizados} atualizadas")
        return {
            "inseridos": inseridos,
            "atualizados": atualizados,
            "total": len(PAGES_CATALOG),
        }

    except Exception as err:
        logger.error(f"[PERM_SEEDER] ❌ {err}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
