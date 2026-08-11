"""
Router da Dashboard — endpoint único `GET /api/dashboard/me?user_id=X`
que devolve KPIs, agenda do dia, pendências e atalhos adaptados ao
role do usuário (USER / RESPONSAVEL_GRUPO / ADMIN / TI).

Filosofia: o frontend faz UMA chamada e recebe tudo pronto pra
renderizar. Sem ifs de role no front.

Estrutura da resposta:
{
  "user":      {id, name, role, group_id, group_name},
  "saudacao":  "Bom dia, ...",
  "kpis":      [{label, value, subtitle, icon, color, link}, ...],   ← 4 cards
  "agenda":    [{hora, fim, titulo, local}, ...],                    ← compromissos do dia
  "pendencias":[{tipo, label, urgencia, url, icon}, ...],            ← caixa de pendências
  "atalhos":   [{label, url, icon}, ...]                             ← botões rápidos
}
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from database import get_db_or_404

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ---------------------------------------------------------------------
# HELPERS GENÉRICOS
# ---------------------------------------------------------------------
def _saudacao_hora() -> str:
    h = datetime.now().hour
    if h < 12:
        return "Bom dia"
    if h < 18:
        return "Boa tarde"
    return "Boa noite"


def _kpi(label: str, value, subtitle: str = "", icon: str = "bi-info-circle",
         color: str = "default", link: str = "") -> dict:
    return {
        "label":    label,
        "value":    value,
        "subtitle": subtitle,
        "icon":     icon,
        "color":    color,    # 'default' | 'success' | 'warning' | 'danger' | 'info'
        "link":     link,
    }


def _pend(tipo: str, label: str, urgencia: str = "media",
          url: str = "", icon: str = "bi-exclamation-circle") -> dict:
    return {
        "tipo": tipo, "label": label,
        "urgencia": urgencia,    # 'baixa' | 'media' | 'alta'
        "url": url, "icon": icon,
    }


def _existe_tabela(cursor, nome: str) -> bool:
    cursor.execute("""
        SELECT 1 FROM information_schema.TABLES
         WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
    """, (nome,))
    return cursor.fetchone() is not None


# IDs de status na tabela ticket_status:
#   1=Aberto  2=Em Andamento  3=Aguardando  4=Resolvido  5=Fechado
TICKET_STATUS_FECHADOS = (4, 5)

# ID do grupo Frotas (cpe_grupo) — controla se o usuário vê os widgets de frota
GROUP_ID_FROTAS = 13


# ---------------------------------------------------------------------
# COLETAS COMUNS
# ---------------------------------------------------------------------
def _agenda_do_dia(cursor, user_id: int, group_id: Optional[int]) -> list[dict]:
    """
    Compromissos de hoje agregados de várias fontes:

    1. Reservas de sala onde o usuário é dono (`recepcao_reservas`)
    2. Reservas de sala onde o usuário foi convidado (`recepcao_convidados`)
    3. Reservas de veículo do usuário/condutor (`fleet_reservations`)
    4. Eventos da agenda Carbonio (best-effort: tenta pegar ao vivo se o
       usuário tiver token; falha silenciosa se não tiver)

    Retorna até 8 itens ordenados por horário.
    """
    eventos: list[dict] = []
    seen_keys: set[str] = set()  # evita duplicar mesma reserva (dono + convidado)

    def _push(hora: str, fim: str, titulo: str, local: str, fonte: str, key: str = ""):
        if key and key in seen_keys:
            return
        if key:
            seen_keys.add(key)
        eventos.append({
            "hora":   hora or "",
            "fim":    fim  or "",
            "titulo": titulo or "Compromisso",
            "local":  local  or "—",
            "fonte":  fonte,
        })

    # 1) Reservas de sala — dono
    if _existe_tabela(cursor, "recepcao_reservas"):
        cursor.execute("""
            SELECT r.id, r.titulo, r.inicio, r.fim, s.nome AS sala_nome
              FROM recepcao_reservas r
              JOIN recepcao_salas s ON s.id = r.sala_id
             WHERE r.usuario_id = %s
               AND DATE(r.inicio) = CURDATE()
               AND r.status IN ('confirmada','pendente')
             ORDER BY r.inicio
        """, (user_id,))
        for r in cursor.fetchall():
            _push(
                hora=r["inicio"].strftime("%H:%M") if r.get("inicio") else "",
                fim=r["fim"].strftime("%H:%M")    if r.get("fim")    else "",
                titulo=r["titulo"] or "Reserva",
                local=f"Sala {r['sala_nome']}",
                fonte="recepcao",
                key=f"reserva:{r['id']}",
            )

    # 2) Reservas de sala — convidado
    if _existe_tabela(cursor, "recepcao_convidados"):
        cursor.execute("""
            SELECT r.id, r.titulo, r.inicio, r.fim, s.nome AS sala_nome,
                   o.name AS organizador_nome
              FROM recepcao_convidados c
              JOIN recepcao_reservas r ON r.id = c.reserva_id
              JOIN recepcao_salas    s ON s.id = r.sala_id
              LEFT JOIN users o ON o.id = r.usuario_id
             WHERE c.usuario_id = %s
               AND DATE(r.inicio) = CURDATE()
               AND r.status IN ('confirmada','pendente')
             ORDER BY r.inicio
        """, (user_id,))
        for r in cursor.fetchall():
            org = r.get("organizador_nome") or ""
            _push(
                hora=r["inicio"].strftime("%H:%M") if r.get("inicio") else "",
                fim=r["fim"].strftime("%H:%M")    if r.get("fim")    else "",
                titulo=(r["titulo"] or "Reunião") + (f" — {org}" if org else ""),
                local=f"Sala {r['sala_nome']}",
                fonte="recepcao_convite",
                key=f"reserva:{r['id']}",
            )

    # 3) Reservas de veículo (frota)
    if _existe_tabela(cursor, "fleet_reservations"):
        cursor.execute("""
            SELECT fr.id, fr.destino, fr.horario_inicio, fr.horario_fim,
                   v.placa, v.modelo
              FROM fleet_reservations fr
              JOIN fleet_vehicles v ON v.id = fr.vehicle_id
             WHERE fr.solicitante_id = %s
               AND fr.data_reserva = CURDATE()
               AND fr.status IN ('aprovado','pendente')
             ORDER BY fr.horario_inicio
        """, (user_id,))
        for r in cursor.fetchall():
            hora = r["horario_inicio"].strftime("%H:%M") if hasattr(r.get("horario_inicio"), "strftime") else (str(r.get("horario_inicio") or "")[:5] or "")
            fim  = r["horario_fim"].strftime("%H:%M")    if hasattr(r.get("horario_fim"),   "strftime") else (str(r.get("horario_fim")   or "")[:5] or "")
            _push(
                hora=hora,
                fim=fim,
                titulo=f"Viagem: {r.get('destino') or '—'}",
                local=f"{r.get('placa') or ''} {r.get('modelo') or ''}".strip() or "Veículo",
                fonte="frota",
                key=f"frota:{r['id']}",
            )

    # 4) Eventos do Carbonio (live, best-effort)
    try:
        eventos_carbonio = _carbonio_eventos_hoje(cursor, user_id)
        for ev in eventos_carbonio:
            _push(
                hora=ev.get("hora", ""),
                fim=ev.get("fim", ""),
                titulo=ev.get("titulo", "Compromisso"),
                local=ev.get("local", "—"),
                fonte="carbonio",
                key=f"carb:{ev.get('id') or ev.get('titulo')}",
            )
    except Exception as exc:
        # Sem token, network falhou, etc. — silencioso (não quebra dashboard)
        logger.debug(f"[DASHBOARD] Carbonio agenda indisponível p/ user {user_id}: {exc}")

    # Ordena por hora
    eventos.sort(key=lambda e: e.get("hora") or "23:59")
    return eventos[:8]


def _carbonio_eventos_hoje(cursor, user_id: int) -> list[dict]:
    """Busca eventos do Carbonio para HOJE. Retorna lista vazia se o usuário
    não tem token, token expirou, ou Carbonio offline. Nunca propaga erro."""
    cursor.execute(
        "SELECT carbonio_token, carbonio_token_exp FROM users WHERE id = %s",
        (user_id,)
    )
    row = cursor.fetchone()
    if not row or not row.get("carbonio_token"):
        return []
    if row.get("carbonio_token_exp") and row["carbonio_token_exp"] < datetime.now():
        return []

    try:
        from services.crypto_helper import decrypt_str  # type: ignore
        from services.carbonio_service import listar_eventos  # type: ignore
    except ImportError:
        return []

    try:
        token = decrypt_str(row["carbonio_token"])
        if not token:
            return []
        ini = datetime.combine(datetime.now().date(), time.min)
        fim = datetime.combine(datetime.now().date(), time.max)
        ini_ms = int(ini.timestamp() * 1000)
        fim_ms = int(fim.timestamp() * 1000)
        eventos = listar_eventos(token, ini_ms, fim_ms)
    except Exception:
        return []

    out = []
    for ev in eventos:
        try:
            ini_dt = datetime.fromtimestamp(ev["inicio_ms"] / 1000)
            fim_dt = datetime.fromtimestamp(ev["fim_ms"]    / 1000)
        except (KeyError, TypeError, ValueError):
            continue
        out.append({
            "id":     ev.get("id"),
            "hora":   "Dia todo" if ev.get("all_day") else ini_dt.strftime("%H:%M"),
            "fim":    "" if ev.get("all_day") else fim_dt.strftime("%H:%M"),
            "titulo": ev.get("titulo") or "Compromisso",
            "local":  ev.get("local") or "—",
        })
    return out


# ---------------------------------------------------------------------
# WIDGETS ESPECIAIS (todos roles ou específicos)
# ---------------------------------------------------------------------
def _proxima_reserva_sala(cursor, user_id: int) -> Optional[dict]:
    """Próxima reserva de sala do usuário (a partir de agora)."""
    if not _existe_tabela(cursor, "recepcao_reservas"):
        return None
    cursor.execute("""
        SELECT r.id, r.titulo, r.inicio, r.fim, r.status,
               s.nome AS sala_nome
          FROM recepcao_reservas r
          JOIN recepcao_salas s ON s.id = r.sala_id
         WHERE r.usuario_id = %s
           AND r.inicio >= NOW()
           AND r.status IN ('confirmada','pendente')
         ORDER BY r.inicio ASC
         LIMIT 1
    """, (user_id,))
    r = cursor.fetchone()
    if not r:
        return None
    inicio = r.get("inicio")
    fim    = r.get("fim")
    return {
        "id":       r["id"],
        "titulo":   r["titulo"] or "Reserva",
        "sala":     r["sala_nome"],
        "data":     inicio.strftime("%d/%m/%Y") if inicio else "",
        "hora":     inicio.strftime("%H:%M")    if inicio else "",
        "fim":      fim.strftime("%H:%M")       if fim    else "",
        "status":   r["status"],
        "url":      "/SistemaCPE/web/pages/recepcao.html",
    }


def _avaliacoes_grupo(cursor, group_id: int) -> Optional[dict]:
    """
    Resumo das avaliações de tickets do grupo: média, distribuição
    (positiva/neutra/negativa), total. Mostrado pro RESPONSAVEL_GRUPO.
    """
    if not _existe_tabela(cursor, "ticket_avaliacoes"):
        return None
    cursor.execute("""
        SELECT
            AVG(estrelas)                                                AS media,
            COUNT(*)                                                     AS total,
            SUM(CASE WHEN estrelas >= 8                THEN 1 ELSE 0 END) AS positivas,
            SUM(CASE WHEN estrelas BETWEEN 4 AND 7     THEN 1 ELSE 0 END) AS neutras,
            SUM(CASE WHEN estrelas BETWEEN 1 AND 3     THEN 1 ELSE 0 END) AS negativas
          FROM ticket_avaliacoes
         WHERE group_id = %s
           AND avaliado_em IS NOT NULL
    """, (group_id,))
    r = cursor.fetchone() or {}
    total = int(r.get("total") or 0)
    if total == 0:
        return {
            "media": 0, "total": 0,
            "positivas": 0, "neutras": 0, "negativas": 0,
            "vazio": True,
            "url": "/SistemaCPE/web/pages/avaliacoes.html",
        }

    media = float(r.get("media") or 0)
    return {
        "media":     round(media, 1),
        "media_pct": round(media / 10 * 100),
        "total":     total,
        "positivas": int(r.get("positivas") or 0),
        "neutras":   int(r.get("neutras")   or 0),
        "negativas": int(r.get("negativas") or 0),
        "vazio":     False,
        "url":       "/SistemaCPE/web/pages/avaliacoes.html",
    }


def _widgets_frota(cursor) -> dict:
    """
    Widgets específicos pro responsável do grupo Frotas:
      - checklists aguardando vistoria
      - reservas de veículo de hoje
      - próxima manutenção agendada
    """
    out = {
        "checklists_aguardando": 0,
        "reservas_hoje":         0,
        "proxima_manutencao":    None,
    }

    if _existe_tabela(cursor, "fleet_checklists"):
        cursor.execute("""
            SELECT COUNT(*) AS total FROM fleet_checklists
             WHERE status IN ('aguardando_vistoria','aguardando_aprovacao')
        """)
        out["checklists_aguardando"] = int((cursor.fetchone() or {}).get("total") or 0)

    if _existe_tabela(cursor, "fleet_reservations"):
        cursor.execute("""
            SELECT COUNT(*) AS total FROM fleet_reservations
             WHERE data_reserva = CURDATE()
               AND status IN ('aprovado','pendente')
        """)
        out["reservas_hoje"] = int((cursor.fetchone() or {}).get("total") or 0)

    if _existe_tabela(cursor, "fleet_maintenance"):
        cursor.execute("""
            SELECT v.placa, v.modelo, m.tipo, m.data_entrada,
                   DATEDIFF(m.data_entrada, CURDATE()) AS dias
              FROM fleet_maintenance m
              JOIN fleet_vehicles v ON v.id = m.vehicle_id
             WHERE m.status = 'agendado'
               AND m.data_entrada IS NOT NULL
               AND m.data_entrada >= CURDATE()
             ORDER BY m.data_entrada ASC
             LIMIT 1
        """)
        m = cursor.fetchone()
        if m:
            dias = int(m.get("dias") or 0)
            out["proxima_manutencao"] = {
                "placa":  m["placa"],
                "modelo": m["modelo"],
                "tipo":   m["tipo"],
                "data":   m["data_entrada"].strftime("%d/%m/%Y") if m.get("data_entrada") else "",
                "dias":   dias,
                "label":  ("hoje" if dias == 0 else
                           "amanhã" if dias == 1 else
                           f"em {dias} dias"),
            }

    return out


# ---------------------------------------------------------------------
# KPIs e PENDÊNCIAS por ROLE
# ---------------------------------------------------------------------
def _kpis_user(cursor, user_id: int) -> list[dict]:
    """Operacional — focado nas coisas do próprio usuário."""
    out = []

    # 1) Minhas tarefas pendentes (não concluídas)
    if _existe_tabela(cursor, "tarefas_task"):
        cursor.execute("""
            SELECT COUNT(*) AS total
              FROM tarefas_task
             WHERE responsavel_id = %s
               AND concluida_em IS NULL
        """, (user_id,))
        n = (cursor.fetchone() or {}).get("total", 0)
        out.append(_kpi("Minhas tarefas pendentes", n,
                        "tarefas em aberto", "bi-check2-square",
                        "warning" if n > 5 else "default",
                        "/SistemaCPE/web/pages/tasks.html"))

    # 2) Tickets atribuídos a mim (responsavel_id) — abertos
    cursor.execute("""
        SELECT COUNT(*) AS total FROM tickets
         WHERE responsavel_id = %s
           AND status_id NOT IN (4, 5)
    """, (user_id,))
    n = (cursor.fetchone() or {}).get("total", 0)
    out.append(_kpi("Tickets atribuídos a mim", n,
                    "abertos", "bi-ticket-detailed",
                    "danger" if n > 0 else "success",
                    "/SistemaCPE/web/pages/tickets.html"))

    # 3) Próxima reserva minha (sala) — futura ou de hoje em diante
    if _existe_tabela(cursor, "recepcao_reservas"):
        cursor.execute("""
            SELECT COUNT(*) AS total FROM recepcao_reservas
             WHERE usuario_id = %s
               AND DATE(inicio) >= CURDATE()
               AND status IN ('confirmada','pendente')
        """, (user_id,))
        n = (cursor.fetchone() or {}).get("total", 0)
        out.append(_kpi("Reservas de sala", n,
                        "próximas", "bi-calendar-event", "info",
                        "/SistemaCPE/web/pages/recepcao.html"))
    else:
        out.append(_kpi("Reservas de sala", 0, "próximas", "bi-calendar-event"))

    # 4) Notificações não lidas
    cursor.execute("""
        SELECT COUNT(*) AS total FROM notificacoes
         WHERE usuario_id = %s AND lido = 0
    """, (user_id,))
    n = (cursor.fetchone() or {}).get("total", 0)
    out.append(_kpi("Notificações", n,
                    "não lidas", "bi-bell-fill",
                    "warning" if n > 0 else "default"))

    return out


def _pendencias_user(cursor, user_id: int) -> list[dict]:
    out = []

    # Reservas pra confirmar — começam nos próximos 40 min
    if _existe_tabela(cursor, "recepcao_reservas"):
        cursor.execute("""
            SELECT r.id, r.titulo, r.inicio, s.nome AS sala_nome
              FROM recepcao_reservas r
              JOIN recepcao_salas s ON s.id = r.sala_id
             WHERE r.usuario_id = %s
               AND r.status = 'pendente'
               AND r.inicio BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 40 MINUTE)
             ORDER BY r.inicio
        """, (user_id,))
        for r in cursor.fetchall():
            hora = r["inicio"].strftime("%H:%M") if r.get("inicio") else "?"
            out.append(_pend(
                "reserva_confirmar",
                f"Confirmar reserva da {r['sala_nome']} às {hora}",
                "alta",
                "/SistemaCPE/web/pages/recepcao.html",
                "bi-bell-fill",
            ))

    # Tickets aguardando minha resposta (status Aberto=1 ou Em Andamento=2)
    cursor.execute("""
        SELECT t.id, t.assunto FROM tickets t
         WHERE t.responsavel_id = %s
           AND t.status_id IN (1, 2)
         ORDER BY t.updated_at DESC LIMIT 5
    """, (user_id,))
    for t in cursor.fetchall():
        out.append(_pend(
            "ticket",
            f"Responder ticket #{t['id']}: {t['assunto'][:50]}",
            "media",
            f"/SistemaCPE/web/pages/tickets.html?id={t['id']}",
            "bi-ticket-detailed",
        ))

    return out[:6]


def _kpis_resp_grupo(cursor, user_id: int, group_id: Optional[int]) -> list[dict]:
    """Gerencial — focado no grupo que o usuário coordena."""
    out = []

    # 1) Tickets do meu grupo abertos
    if group_id:
        cursor.execute("""
            SELECT COUNT(*) AS total FROM tickets
             WHERE group_id = %s
               AND status_id NOT IN (4, 5)
        """, (group_id,))
        n = (cursor.fetchone() or {}).get("total", 0)
    else:
        n = 0
    out.append(_kpi("Tickets do meu grupo", n,
                    "abertos", "bi-ticket-detailed",
                    "warning" if n > 5 else "default",
                    "/SistemaCPE/web/pages/tickets.html"))

    # 2) Membros do grupo ativos
    if group_id:
        cursor.execute("""
            SELECT COUNT(*) AS total FROM users
             WHERE group_id = %s AND is_active = 1
        """, (group_id,))
        n = (cursor.fetchone() or {}).get("total", 0)
    else:
        n = 0
    out.append(_kpi("Membros do meu grupo", n,
                    "ativos", "bi-people-fill", "info",
                    "/SistemaCPE/web/pages/users.html"))

    # 3) Tarefas atrasadas do grupo (prazo passou e não foi concluída)
    if _existe_tabela(cursor, "tarefas_task") and group_id:
        cursor.execute("""
            SELECT COUNT(*) AS total
              FROM tarefas_task
             WHERE group_id = %s
               AND concluida_em IS NULL
               AND prazo IS NOT NULL
               AND prazo < NOW()
        """, (group_id,))
        n = (cursor.fetchone() or {}).get("total", 0)
    else:
        n = 0
    out.append(_kpi("Tarefas atrasadas", n,
                    "do meu grupo", "bi-clock-history",
                    "danger" if n > 0 else "success",
                    "/SistemaCPE/web/pages/tasks.html"))

    # 4) Pré-cadastros pendentes (responsáveis também ajudam a aprovar)
    if _existe_tabela(cursor, "pre_cadastro_pendentes"):
        cursor.execute("""
            SELECT COUNT(*) AS total FROM pre_cadastro_pendentes
             WHERE status = 'pendente'
        """)
        n = (cursor.fetchone() or {}).get("total", 0)
    else:
        n = 0
    out.append(_kpi("Pré-cadastros pendentes", n,
                    "aguardando aprovação", "bi-person-plus-fill",
                    "warning" if n > 0 else "default",
                    "/SistemaCPE/web/pages/users.html"))

    return out


def _pendencias_resp_grupo(cursor, user_id: int, group_id: Optional[int]) -> list[dict]:
    out = []

    if not group_id:
        return out

    # Tickets do grupo sem responsável (status Aberto=1 ou Em Andamento=2)
    cursor.execute("""
        SELECT id, assunto FROM tickets
         WHERE group_id = %s
           AND responsavel_id IS NULL
           AND status_id IN (1, 2)
         ORDER BY created_at ASC LIMIT 5
    """, (group_id,))
    for t in cursor.fetchall():
        out.append(_pend(
            "ticket_sem_dono",
            f"Atribuir ticket #{t['id']}: {t['assunto'][:50]}",
            "alta",
            f"/SistemaCPE/web/pages/tickets.html?id={t['id']}",
            "bi-person-add",
        ))

    # Pré-cadastros aguardando aprovação
    if _existe_tabela(cursor, "pre_cadastro_pendentes"):
        cursor.execute("""
            SELECT id, name, email FROM pre_cadastro_pendentes
             WHERE status = 'pendente'
             ORDER BY solicitado_em DESC LIMIT 3
        """)
        for p in cursor.fetchall():
            out.append(_pend(
                "pre_cadastro",
                f"Aprovar cadastro de {p['name']} ({p['email']})",
                "media",
                "/SistemaCPE/web/pages/users.html",
                "bi-person-plus-fill",
            ))

    # Se for grupo Frotas (id=13): checklists aguardando vistoria
    if group_id == 13 and _existe_tabela(cursor, "fleet_checklists"):
        cursor.execute("""
            SELECT c.id, v.placa
              FROM fleet_checklists c
              JOIN fleet_vehicles  v ON v.id = c.vehicle_id
             WHERE c.status = 'aguardando_vistoria'
             ORDER BY c.id ASC LIMIT 5
        """)
        for c in cursor.fetchall():
            out.append(_pend(
                "checklist_vistoria",
                f"Vistoriar checklist do veículo {c['placa']}",
                "alta",
                "/SistemaCPE/web/pages/fleet.html",
                "bi-clipboard-check",
            ))

    return out[:8]


def _kpis_admin(cursor) -> list[dict]:
    """Visão executiva."""
    out = []

    # 1) Usuários online AGORA (WebSocket do chat ativo)
    # Import local pra evitar circular no boot do FastAPI.
    try:
        from routes.chat import manager as _chat_manager
        online = len(_chat_manager.online_users())
        total_ativos = 0
        cursor.execute("SELECT COUNT(*) AS total FROM users WHERE is_active = 1")
        total_ativos = (cursor.fetchone() or {}).get("total", 0)
        out.append(_kpi(
            "Online agora", online,
            f"de {total_ativos} ativos", "bi-broadcast-pin",
            "success" if online > 0 else "default",
            "/SistemaCPE/web/pages/users.html",
        ))
    except Exception as e:
        logger.warning(f"[DASHBOARD] Nao foi possivel contar online: {e}")
        cursor.execute("SELECT COUNT(*) AS total FROM users WHERE is_active = 1")
        n = (cursor.fetchone() or {}).get("total", 0)
        out.append(_kpi("Usuários ativos", n, "no sistema", "bi-people-fill",
                        "info", "/SistemaCPE/web/pages/users.html"))

    # 2) Tickets abertos no sistema
    cursor.execute("""
        SELECT COUNT(*) AS total FROM tickets
         WHERE status_id NOT IN (4, 5)
    """)
    n = (cursor.fetchone() or {}).get("total", 0)
    out.append(_kpi("Tickets abertos", n, "no sistema", "bi-ticket-detailed",
                    "warning" if n > 10 else "default",
                    "/SistemaCPE/web/pages/tickets.html"))

    # 3) Pré-cadastros pendentes
    if _existe_tabela(cursor, "pre_cadastro_pendentes"):
        cursor.execute("""
            SELECT COUNT(*) AS total FROM pre_cadastro_pendentes
             WHERE status = 'pendente'
        """)
        n = (cursor.fetchone() or {}).get("total", 0)
    else:
        n = 0
    out.append(_kpi("Pré-cadastros", n, "aguardando aprovação", "bi-person-plus-fill",
                    "warning" if n > 0 else "default",
                    "/SistemaCPE/web/pages/users.html"))

    # 4) Veículos da frota em uso
    if _existe_tabela(cursor, "fleet_vehicles"):
        cursor.execute("""
            SELECT
                SUM(CASE WHEN status='em_viagem' THEN 1 ELSE 0 END) AS em_uso,
                SUM(CASE WHEN status NOT IN ('inativo','manutencao') THEN 1 ELSE 0 END) AS disponiveis_total
            FROM fleet_vehicles
        """)
        r = cursor.fetchone() or {}
        em_uso = r.get("em_uso") or 0
        total  = r.get("disponiveis_total") or 0
        out.append(_kpi("Frota em uso", em_uso,
                        f"de {total} ativos", "bi-truck", "info",
                        "/SistemaCPE/web/pages/fleet.html"))
    else:
        out.append(_kpi("Frota em uso", 0, "sem dados", "bi-truck"))

    return out


def _pendencias_admin(cursor) -> list[dict]:
    out = []

    # Pré-cadastros aguardando aprovação
    if _existe_tabela(cursor, "pre_cadastro_pendentes"):
        cursor.execute("""
            SELECT id, name, email FROM pre_cadastro_pendentes
             WHERE status = 'pendente'
             ORDER BY solicitado_em DESC LIMIT 5
        """)
        for p in cursor.fetchall():
            out.append(_pend(
                "pre_cadastro",
                f"Aprovar cadastro de {p['name']} ({p['email']})",
                "media",
                "/SistemaCPE/web/pages/users.html",
                "bi-person-plus-fill",
            ))

    # Tickets críticos sem responsável (aberto há mais de 24h)
    cursor.execute("""
        SELECT id, assunto FROM tickets
         WHERE responsavel_id IS NULL
           AND status_id IN (1, 2)
           AND created_at < NOW() - INTERVAL 1 DAY
         ORDER BY created_at ASC LIMIT 5
    """)
    for t in cursor.fetchall():
        out.append(_pend(
            "ticket_sem_dono",
            f"Atribuir ticket #{t['id']}: {t['assunto'][:50]} (>24h)",
            "alta",
            f"/SistemaCPE/web/pages/tickets.html?id={t['id']}",
            "bi-exclamation-triangle-fill",
        ))

    # Veículos em manutenção há mais de 7 dias (status_data > 7d)
    if _existe_tabela(cursor, "fleet_vehicles"):
        cursor.execute("""
            SELECT placa, modelo, avaria_em FROM fleet_vehicles
             WHERE status = 'manutencao'
               AND avaria_em < NOW() - INTERVAL 7 DAY
             ORDER BY avaria_em ASC LIMIT 3
        """)
        for v in cursor.fetchall():
            out.append(_pend(
                "veiculo_manutencao_longa",
                f"Veículo {v['placa']} em manutenção há mais de 7 dias",
                "media",
                "/SistemaCPE/web/pages/fleet.html",
                "bi-wrench-adjustable",
            ))

    return out[:8]


def _kpis_ti(cursor) -> list[dict]:
    """TI — operacional + admin (foco em chamados e infraestrutura)."""
    out = []

    # 1) Usuários online AGORA (WS do chat ativo)
    try:
        from routes.chat import manager as _chat_manager
        online = len(_chat_manager.online_users())
        cursor.execute("SELECT COUNT(*) AS total FROM users WHERE is_active = 1")
        total_ativos = (cursor.fetchone() or {}).get("total", 0)
        out.append(_kpi(
            "Online agora", online,
            f"de {total_ativos} ativos", "bi-broadcast-pin",
            "success" if online > 0 else "default",
            "/SistemaCPE/web/pages/users.html",
        ))
    except Exception as e:
        logger.warning(f"[DASHBOARD] Nao foi possivel contar online: {e}")

    # 2) Tickets críticos (prioridade Alta/Urgente)
    cursor.execute("""
        SELECT COUNT(*) AS total FROM tickets t
         JOIN ticket_prioridades p ON p.id = t.prioridade_id
         WHERE p.nome IN ('Alta','Urgente','Crítica','Critica')
           AND t.status_id NOT IN (4, 5)
    """)
    n = (cursor.fetchone() or {}).get("total", 0)
    out.append(_kpi("Tickets críticos", n, "urgentes/altos",
                    "bi-exclamation-triangle-fill",
                    "danger" if n > 0 else "success",
                    "/SistemaCPE/web/pages/tickets.html"))

    # 2) Veículos em manutenção
    if _existe_tabela(cursor, "fleet_vehicles"):
        cursor.execute("""
            SELECT COUNT(*) AS total FROM fleet_vehicles
             WHERE status = 'manutencao'
        """)
        n = (cursor.fetchone() or {}).get("total", 0)
    else:
        n = 0
    out.append(_kpi("Veículos em manutenção", n, "atualmente",
                    "bi-wrench-adjustable",
                    "warning" if n > 0 else "default",
                    "/SistemaCPE/web/pages/fleet.html"))

    # 3) Pré-cadastros pendentes
    if _existe_tabela(cursor, "pre_cadastro_pendentes"):
        cursor.execute("""
            SELECT COUNT(*) AS total FROM pre_cadastro_pendentes
             WHERE status = 'pendente'
        """)
        n = (cursor.fetchone() or {}).get("total", 0)
    else:
        n = 0
    out.append(_kpi("Pré-cadastros", n, "aguardando aprovação",
                    "bi-person-plus-fill",
                    "warning" if n > 0 else "default",
                    "/SistemaCPE/web/pages/users.html"))

    # 4) Tickets criados hoje
    cursor.execute("""
        SELECT COUNT(*) AS total FROM tickets
         WHERE DATE(created_at) = CURDATE()
    """)
    n = (cursor.fetchone() or {}).get("total", 0)
    out.append(_kpi("Tickets de hoje", n, "criados hoje", "bi-calendar-plus",
                    "info"))

    return out


# ---------------------------------------------------------------------
# ATALHOS RÁPIDOS (varia por role)
# ---------------------------------------------------------------------
_ATALHOS_BASE = [
    {"label": "Novo ticket",  "url": "/SistemaCPE/web/pages/tickets.html",  "icon": "bi-ticket-detailed"},
    {"label": "Nova tarefa",  "url": "/SistemaCPE/web/pages/tasks.html",    "icon": "bi-check2-square"},
    {"label": "Reservar sala","url": "/SistemaCPE/web/pages/recepcao.html", "icon": "bi-calendar-plus"},
]

_ATALHOS_ADMIN = _ATALHOS_BASE + [
    {"label": "Usuários",   "url": "/SistemaCPE/web/pages/users.html",       "icon": "bi-people"},
    {"label": "Permissões", "url": "/SistemaCPE/web/pages/permissions.html", "icon": "bi-shield-lock"},
]


# ---------------------------------------------------------------------
# USERS ONLINE — endpoint leve pra polling (KPI + lista nome+grupo)
# ---------------------------------------------------------------------
@router.get("/online")
def dashboard_online():
    """Retorna users online AGORA (WS do chat ativo).
    Uso: KPI da dashboard admin + polling opcional.
    Sem auth pra facilitar polling do frontend — apenas retorna id/nome/grupo
    (dados nao-sensíveis; qualquer user logado ja ve os colegas no chat).
    """
    try:
        from routes.chat import manager as _chat_manager
        ids = _chat_manager.online_users()
    except Exception:
        ids = []

    if not ids:
        return {"success": True, "total": 0, "users": []}

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        placeholders = ",".join(["%s"] * len(ids))
        cursor.execute(f"""
            SELECT u.id, u.name, u.role, g.name AS group_name
              FROM users u
              LEFT JOIN cpe_grupo g ON g.id = u.group_id
             WHERE u.id IN ({placeholders}) AND u.is_active = 1
             ORDER BY u.name
        """, tuple(ids))
        users = cursor.fetchall()
        return {"success": True, "total": len(users), "users": users}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ---------------------------------------------------------------------
# ENDPOINT PRINCIPAL
# ---------------------------------------------------------------------
@router.get("/me")
async def dashboard_me(user_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        # 1) Identifica o usuário
        cursor.execute("""
            SELECT u.id, u.name, u.email, u.role, u.group_id, g.name AS group_name
              FROM users u
              LEFT JOIN cpe_grupo g ON g.id = u.group_id
             WHERE u.id = %s AND u.is_active = 1
        """, (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado ou inativo")

        role = user.get("role") or "USER"
        gid  = user.get("group_id")

        # 2) Monta KPIs por role
        if role == "ADMIN":
            kpis     = _kpis_admin(cursor)
            pendings = _pendencias_admin(cursor)
            atalhos  = _ATALHOS_ADMIN
        elif role == "TI":
            kpis     = _kpis_ti(cursor)
            pendings = _pendencias_admin(cursor)   # mesmo conjunto admin
            atalhos  = _ATALHOS_ADMIN
        elif role == "RESPONSAVEL_GRUPO":
            kpis     = _kpis_resp_grupo(cursor, user_id, gid)
            pendings = _pendencias_resp_grupo(cursor, user_id, gid)
            atalhos  = _ATALHOS_BASE
        else:                                       # USER ou MANAGER
            kpis     = _kpis_user(cursor, user_id)
            pendings = _pendencias_user(cursor, user_id)
            atalhos  = _ATALHOS_BASE

        # 3) Agenda do dia (todos)
        agenda = _agenda_do_dia(cursor, user_id, gid)

        # 4) Próxima reserva de sala (todos)
        proxima_reserva = _proxima_reserva_sala(cursor, user_id)

        # 5) Avaliações do grupo (RESPONSAVEL_GRUPO apenas)
        avaliacoes = None
        if role == "RESPONSAVEL_GRUPO" and gid:
            avaliacoes = _avaliacoes_grupo(cursor, gid)

        # 6) Widgets de frota (RESPONSAVEL_GRUPO do grupo Frotas apenas)
        frota_widgets = None
        if role == "RESPONSAVEL_GRUPO" and gid == GROUP_ID_FROTAS:
            frota_widgets = _widgets_frota(cursor)

        return {
            "user": {
                "id":          user["id"],
                "name":        user["name"],
                "role":        role,
                "group_id":    gid,
                "group_name":  user.get("group_name"),
            },
            "saudacao":        f"{_saudacao_hora()}, {user['name'].split(' ')[0]}",
            "role_label":      _ROLE_LABEL.get(role, role),
            "kpis":            kpis,
            "agenda":          agenda,
            "proxima_reserva": proxima_reserva,
            "avaliacoes":      avaliacoes,
            "frota":           frota_widgets,
            "pendencias":      pendings,
            "atalhos":         atalhos,
        }
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[DASHBOARD/ME] {err}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao montar dashboard: {err}")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


_ROLE_LABEL = {
    "ADMIN":             "Administrador",
    "TI":                "TI",
    "RESPONSAVEL_GRUPO": "Responsável de Grupo",
    "MANAGER":           "Gerente",
    "USER":              "Usuário",
}
