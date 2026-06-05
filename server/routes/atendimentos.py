"""
Modulo Equipe de Suporte - Agendas de atendimento.

Parte interna (ADMIN/TI): agendas, horarios, servicos, equipamentos,
agendamentos, bloqueios e dashboard.
Parte publica (sem login): o cliente lista agendas, escolhe servico, dia
e horario, preenche os dados e cria um agendamento que entra como
'pendente' ate a equipe confirmar.
"""

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from database import get_db_or_404, convert_datetime_list
from datetime import datetime, date, timedelta, time as _time
import logging
import os
import shutil
import uuid as _uuid
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/atendimentos", tags=["Atendimentos"])

# Status de agendamento que ocupam o horario (nao podem sobrepor).
_STATUS_OCUPA = ("pendente", "agendado", "atendido")
_STATUS_VALIDOS = ("pendente", "agendado", "atendido", "cancelado", "nao_compareceu")
_GRUPO_COMERCIAL = "Comercial"
_GRUPO_PILOTOS = "Drone"  # operadores/pilotos cadastrados aqui aparecem no agendamento de drone
_DIAS_BUSCA_PUBLICA = 60   # janela de dias oferecida ao cliente


# ============================================================
# AUTENTICACAO / AUTORIZACAO (parte interna)
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


def _get_user(request: Request) -> dict:
    from security import get_user_by_id
    uid = _resolve_user_id(request)
    if not uid:
        raise HTTPException(status_code=401, detail="Nao autenticado")
    user = get_user_by_id(uid)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado")
    return user


def _grupo_do_user(user: dict) -> str:
    """Retorna o nome do grupo do user (vazio se nao tem)."""
    gid = user.get("group_id")
    if not gid:
        return ""
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT name FROM cpe_grupo WHERE id=%s", (gid,))
        row = cursor.fetchone()
        return (row["name"] if row else "") or ""
    finally:
        cursor.close()
        conn.close()


# Niveis de acesso ao modulo:
#   admin  -> CRUD de estrutura (agendas, cursos, equipamentos, horarios,
#             feriados, bloqueios). ADMIN, TI, RESPONSAVEL_GRUPO do Suporte,
#             grupo "Suporte ti".
#   op     -> operacao do dia-a-dia (criar/cancelar agendamento via PUT status).
#             admin + usuario comum do grupo "Suporte".
#   view   -> somente leitura (Comercial + qualquer um dos acima).

_GRUPOS_ADMIN_FIXOS = ("Suporte ti",)
_GRUPOS_RESP_ADMIN  = ("Suporte",)   # responsavel_grupo desses grupos = admin
_GRUPOS_OP          = ("Suporte",)   # usuarios comuns desses grupos = op
_GRUPOS_VIEW_ONLY   = ("Comercial",)


def _calc_nivel_suporte(user: dict) -> str:
    """Retorna 'admin' | 'op' | 'view' | 'none'."""
    role = user.get("role")
    if role == "ADMIN" or role == "TI":
        return "admin"
    grupo = _grupo_do_user(user)
    if grupo in _GRUPOS_ADMIN_FIXOS:
        return "admin"
    if role == "RESPONSAVEL_GRUPO" and grupo in _GRUPOS_RESP_ADMIN:
        return "admin"
    if grupo in _GRUPOS_OP:
        return "op"
    if grupo in _GRUPOS_VIEW_ONLY:
        return "view"
    return "none"


def _403(nivel_exigido: str):
    msgs = {
        "admin": "Apenas Administrador, T.I. ou Responsavel do Suporte podem alterar a estrutura do modulo.",
        "op":    "Voce nao tem permissao para criar ou alterar agendamentos.",
        "view":  "Voce nao tem permissao para acessar o modulo de Equipe de Suporte.",
    }
    raise HTTPException(status_code=403, detail=msgs.get(nivel_exigido, "Acesso negado."))


def _exigir_view_suporte(request: Request) -> dict:
    """Leitura — qualquer perfil autorizado (admin, op ou view)."""
    user = _get_user(request)
    if _calc_nivel_suporte(user) == "none":
        _403("view")
    return user


def _exigir_op_suporte(request: Request) -> dict:
    """Operacao — admin ou usuario do Suporte. Comercial bloqueado."""
    user = _get_user(request)
    if _calc_nivel_suporte(user) not in ("admin", "op"):
        _403("op")
    return user


def _exigir_admin_suporte(request: Request) -> dict:
    """Estrutura — apenas ADMIN, TI, Responsavel do Suporte ou grupo Suporte ti."""
    user = _get_user(request)
    if _calc_nivel_suporte(user) != "admin":
        _403("admin")
    return user


# Alias retro-compat: mantem chamadas existentes (vao ser trocadas abaixo).
_exigir_suporte = _exigir_admin_suporte


# ============================================================
# HELPERS
# ============================================================

def _parse_dt(valor, campo: str) -> datetime:
    if not valor:
        raise HTTPException(status_code=400, detail=f"Campo '{campo}' e obrigatorio")
    txt = str(valor).strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(txt, fmt)
        except ValueError:
            continue
    raise HTTPException(status_code=400, detail=f"Data invalida em '{campo}': {valor}")


def _parse_date(valor, campo: str = "data") -> date:
    if not valor:
        raise HTTPException(status_code=400, detail=f"Campo '{campo}' e obrigatorio")
    try:
        return datetime.strptime(str(valor).strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Data invalida em '{campo}': {valor}")


def _td_to_time(valor) -> _time:
    """Normaliza valor de coluna TIME (timedelta ou str) para datetime.time."""
    if isinstance(valor, _time):
        return valor
    if isinstance(valor, timedelta):
        total = int(valor.total_seconds())
        return _time(hour=(total // 3600) % 24, minute=(total % 3600) // 60)
    h, m = str(valor).split(":")[:2]
    return _time(hour=int(h), minute=int(m))


def _gerar_horarios(agenda: dict, horarios: list, dia: date, duracao_min: int) -> list:
    """Gera os horarios de inicio possiveis para um atendimento de
    `duracao_min` minutos numa data, conforme as faixas de funcionamento.

    Passo da grade = duracao do curso. Isso evita "buracos" e horarios
    quebrados — cada inicio comeca exatamente onde o anterior terminaria.
    Ex: curso 60min em faixa 08:00-12:00 gera 08:00, 09:00, 10:00, 11:00.

    O campo `slot_duracao_min` da agenda continua no banco por
    retrocompatibilidade mas nao influencia mais o passo da grade.
    """
    js_wd = (dia.weekday() + 1) % 7          # Python Mon=0 -> JS Dom=0
    dur = max(5, int(duracao_min or 30))
    out = []
    for h in horarios:
        if int(h["dia_semana"]) != js_wd or not h.get("ativo", 1):
            continue
        ini = datetime.combine(dia, _td_to_time(h["hora_inicio"]))
        fim = datetime.combine(dia, _td_to_time(h["hora_fim"]))
        atual = ini
        while atual + timedelta(minutes=dur) <= fim:
            out.append(atual)
            atual += timedelta(minutes=dur)
    return sorted(set(out))


def _eventos_periodo(cursor, agenda_id: int, ini: datetime, fim: datetime):
    """Carrega de uma vez agendamentos ativos e bloqueios da agenda no
    periodo. Usado pelas telas de disponibilidade (calcula em memoria)."""
    cursor.execute(
        "SELECT inicio, fim, servico_id, treinamento_id, modalidade "
        "FROM atend_agendamentos "
        "WHERE agenda_id=%s AND status IN ('pendente','agendado','atendido') "
        "AND inicio < %s AND fim > %s", (agenda_id, fim, ini))
    ags = cursor.fetchall()
    cursor.execute(
        "SELECT inicio, fim FROM atend_bloqueios "
        "WHERE agenda_id=%s AND inicio < %s AND fim > %s", (agenda_id, fim, ini))
    blqs = cursor.fetchall()
    return ags, blqs


def _slot_tem_vaga(ags, blqs, oferta_id, cap_p, cap_o, ini, fim,
                   modalidade=None, entidade="servico") -> bool:
    """True se o slot tem vaga. Se `modalidade` for informada, checa so ela;
    senao, considera vaga em qualquer modalidade. Presencial e online sao
    contados de forma independente.

    `entidade` = 'servico' | 'treinamento' — define qual campo do agendamento
    deve bater com oferta_id.

    REGRA DE COLISÃO (2026-06-03): curso e treinamento compartilham o mesmo
    recurso (sala/instrutor). Se for slot de curso, qualquer treinamento no
    horário bloqueia. E vice-versa. Modalidade não conta aqui — recurso comum.
    DRONE usa recurso próprio (drone físico): NÃO entra nessa regra de colisão.
    REGRA CURSO E DRONE: ambos são apenas presenciais. Slot online sempre False.
    """
    if modalidade == "online" and entidade in ("servico", "drone"):
        return False
    if any(b["inicio"] < fim and b["fim"] > ini for b in blqs):
        return False

    # Colisão curso<->treinamento (mesmo recurso). Drone fica de fora.
    if entidade == "servico":
        if any(a.get("treinamento_id") is not None
               and a["inicio"] < fim and a["fim"] > ini for a in ags):
            return False
    elif entidade == "treinamento":
        if any(a.get("servico_id") is not None
               and a["inicio"] < fim and a["fim"] > ini for a in ags):
            return False
    # entidade == "drone": sem checagem de colisão entre entidades

    if entidade == "servico":         chave = "servico_id"
    elif entidade == "treinamento":   chave = "treinamento_id"
    else:                              chave = "drone_id"

    def _conta(modal):
        return sum(1 for a in ags if a.get(chave) == oferta_id
                   and a["modalidade"] == modal
                   and a["inicio"] < fim and a["fim"] > ini)

    cp = max(1, int(cap_p or 1))
    co = max(1, int(cap_o or 1))
    if modalidade == "presencial":
        return _conta("presencial") < cp
    if modalidade == "online":
        return _conta("online") < co
    return _conta("presencial") < cp or _conta("online") < co


def _eh_feriado(cursor, agenda_id, dia) -> bool:
    """True se a data e feriado para a agenda (nacional ou especifico dela)."""
    cursor.execute(
        "SELECT id FROM atend_feriados WHERE data=%s "
        "AND (agenda_id IS NULL OR agenda_id=%s) LIMIT 1", (dia, agenda_id))
    return cursor.fetchone() is not None


def _feriados_set(cursor, agenda_id, dini, dfim) -> set:
    """Conjunto de strings 'YYYY-MM-DD' que sao feriado para a agenda no periodo."""
    cursor.execute(
        "SELECT data FROM atend_feriados WHERE data BETWEEN %s AND %s "
        "AND (agenda_id IS NULL OR agenda_id=%s)", (dini, dfim, agenda_id))
    return {str(r["data"]) for r in cursor.fetchall()}


def _resolver_oferta(cursor, agenda_id, servico_id=None, treinamento_id=None, drone_id=None):
    """Retorna metadados da 'oferta' (curso, treinamento ou drone) ou None se
    nenhum dos IDs foi informado.

    Prioridade quando mais de um for passado: servico > treinamento > drone.
    Levanta 404 se o ID nao existe ou nao pertence a agenda.
    """
    if servico_id:
        cursor.execute(
            "SELECT id, nome, duracao_min, cap_presencial, cap_online "
            "FROM atend_servicos WHERE id=%s", (servico_id,))
        s = cursor.fetchone()
        if not s or (agenda_id is not None and not _pertence_agenda(cursor, "atend_servicos", servico_id, agenda_id)):
            raise HTTPException(status_code=404, detail="Curso nao encontrado nessa agenda")
        return {"entidade": "servico", "id": s["id"], "nome": s["nome"],
                "duracao_min": s["duracao_min"],
                "cap_presencial": s["cap_presencial"], "cap_online": s["cap_online"]}
    if treinamento_id:
        cursor.execute(
            "SELECT id, nome, duracao_min, cap_presencial, cap_online "
            "FROM atend_treinamentos WHERE id=%s", (treinamento_id,))
        t = cursor.fetchone()
        if not t or (agenda_id is not None and not _pertence_agenda(cursor, "atend_treinamentos", treinamento_id, agenda_id)):
            raise HTTPException(status_code=404, detail="Treinamento nao encontrado nessa agenda")
        return {"entidade": "treinamento", "id": t["id"], "nome": t["nome"],
                "duracao_min": t["duracao_min"],
                "cap_presencial": t["cap_presencial"], "cap_online": t["cap_online"]}
    if drone_id:
        cursor.execute(
            "SELECT id, nome, duracao_min, cap_presencial, cap_online "
            "FROM atend_drones WHERE id=%s", (drone_id,))
        d = cursor.fetchone()
        if not d or (agenda_id is not None and not _pertence_agenda(cursor, "atend_drones", drone_id, agenda_id)):
            raise HTTPException(status_code=404, detail="Drone nao encontrado nessa agenda")
        return {"entidade": "drone", "id": d["id"], "nome": d["nome"],
                "duracao_min": d["duracao_min"],
                "cap_presencial": d["cap_presencial"], "cap_online": d["cap_online"]}
    return None


def _pertence_agenda(cursor, tabela: str, id_: int, agenda_id: int) -> bool:
    cursor.execute(f"SELECT 1 FROM {tabela} WHERE id=%s AND agenda_id=%s", (id_, agenda_id))
    return cursor.fetchone() is not None


def _checar_vaga(cursor, agenda_id, servico_id, modalidade, inicio, fim,
                 excluir_id=None, treinamento_id=None, drone_id=None):
    """Valida se cabe um agendamento. Retorna None se ha vaga, ou uma
    mensagem de erro. Capacidade vem da oferta (curso, treinamento ou drone);
    presencial e online sao limites independentes.

    Drone NAO entra na regra de colisao curso<->treinamento (recurso proprio).
    """
    if _eh_feriado(cursor, agenda_id, inicio.date()):
        return "Esse dia e feriado nessa agenda."
    cursor.execute(
        "SELECT id FROM atend_bloqueios WHERE agenda_id=%s AND inicio<%s AND fim>%s",
        (agenda_id, fim, inicio))
    if cursor.fetchone():
        return "Esse horario esta bloqueado nessa agenda."

    # Regra: curso e drone são APENAS presenciais. Bloqueia online.
    if servico_id and modalidade == "online":
        return "Curso é apenas presencial — escolha a modalidade presencial."
    if drone_id and modalidade == "online":
        return "Drone é apenas presencial — escolha a modalidade presencial."

    cap = 1
    cap_por_oferta = (servico_id or treinamento_id or drone_id) and modalidade in ("presencial", "online")
    if cap_por_oferta:
        if servico_id:    tabela, oferta_id = "atend_servicos", servico_id
        elif treinamento_id: tabela, oferta_id = "atend_treinamentos", treinamento_id
        else:             tabela, oferta_id = "atend_drones", drone_id
        cursor.execute(
            f"SELECT cap_presencial, cap_online FROM {tabela} WHERE id=%s",
            (oferta_id,))
        s = cursor.fetchone()
        if s:
            bruto = s["cap_online"] if modalidade == "online" else s["cap_presencial"]
            cap = max(1, int(bruto or 1))

    # REGRA DE COLISÃO CURSO ↔ TREINAMENTO (adicionada 2026-06-03):
    # Curso e treinamento compartilham o mesmo recurso físico (sala/instrutor).
    # Se estamos agendando um CURSO e existe TREINAMENTO ocupando o horário
    # naquela agenda, bloqueia. E vice-versa. Não distingue modalidade aqui —
    # se há treinamento marcado no slot, o curso entra em conflito mesmo se
    # for modalidade diferente (recurso comum).
    if servico_id:
        cursor.execute(
            "SELECT id FROM atend_agendamentos WHERE agenda_id=%s "
            "AND status IN ('pendente','agendado','atendido') "
            "AND treinamento_id IS NOT NULL "
            "AND inicio<%s AND fim>%s "
            + ("AND id != %s LIMIT 1" if excluir_id else "LIMIT 1"),
            ([agenda_id, fim, inicio, excluir_id] if excluir_id else [agenda_id, fim, inicio]),
        )
        if cursor.fetchone():
            return ("Esse horário já tem um treinamento marcado nessa agenda. "
                    "Curso e treinamento não podem coexistir no mesmo horário.")
    elif treinamento_id:
        cursor.execute(
            "SELECT id FROM atend_agendamentos WHERE agenda_id=%s "
            "AND status IN ('pendente','agendado','atendido') "
            "AND servico_id IS NOT NULL "
            "AND inicio<%s AND fim>%s "
            + ("AND id != %s LIMIT 1" if excluir_id else "LIMIT 1"),
            ([agenda_id, fim, inicio, excluir_id] if excluir_id else [agenda_id, fim, inicio]),
        )
        if cursor.fetchone():
            return ("Esse horário já tem um curso marcado nessa agenda. "
                    "Curso e treinamento não podem coexistir no mesmo horário.")

    sql = ("SELECT COUNT(*) AS n FROM atend_agendamentos WHERE agenda_id=%s "
           "AND status IN ('pendente','agendado','atendido') "
           "AND inicio<%s AND fim>%s")
    params = [agenda_id, fim, inicio]
    if cap_por_oferta:
        # capacidade por oferta + modalidade (presencial e online independentes)
        if servico_id:
            sql += " AND servico_id=%s AND modalidade=%s"
            params += [servico_id, modalidade]
        elif treinamento_id:
            sql += " AND treinamento_id=%s AND modalidade=%s"
            params += [treinamento_id, modalidade]
        else:
            sql += " AND drone_id=%s AND modalidade=%s"
            params += [drone_id, modalidade]
    if excluir_id:
        sql += " AND id != %s"
        params.append(excluir_id)
    cursor.execute(sql, params)
    if cursor.fetchone()["n"] >= cap:
        if cap_por_oferta:
            rotulo = "online" if modalidade == "online" else "presenciais"
            return f"Esse horario ja atingiu o limite de atendimentos {rotulo}."
        return "Esse horario ja esta ocupado nessa agenda."
    return None


def _dados_agendamento_completo(cursor, agendamento_id: int) -> dict | None:
    """Carrega todos os dados de um agendamento (joins com agenda, unidade,
    servico OU treinamento) — base para os 3 e-mails (cliente recebido/
    confirmado, equipe alerta)."""
    cursor.execute("""
        SELECT a.cliente_nome, a.cliente_email, a.cliente_telefone,
               a.inicio, a.modalidade, a.observacoes, a.titulo,
               COALESCE(s.nome,      t.nome)      AS servico_nome,
               COALESCE(s.instrutor, t.instrutor) AS servico_instrutor,
               ag.nome AS agenda_nome, ag.tipo AS agenda_tipo,
               u.nome AS unidade_nome, u.endereco AS unidade_endereco,
               u.telefone AS unidade_telefone
        FROM atend_agendamentos a
        JOIN atend_agendas ag          ON ag.id = a.agenda_id
        LEFT JOIN atend_servicos s     ON s.id  = a.servico_id
        LEFT JOIN atend_treinamentos t ON t.id  = a.treinamento_id
        LEFT JOIN unidades_cpe u       ON u.id  = ag.unidade_id
        WHERE a.id = %s
    """, (agendamento_id,))
    return cursor.fetchone()


def _resolver_nome_local(row: dict) -> str:
    """Decide o que mostrar como 'local' no e-mail (unidade fisica ou agenda online)."""
    modalidade = row.get("modalidade") or "presencial"
    if row.get("agenda_tipo") == "online" or not row.get("unidade_nome"):
        return ("CPE Tecnologia - Atendimento online"
                if modalidade == "online"
                else row.get("agenda_nome", "CPE Tecnologia"))
    return row["unidade_nome"]


def _dispatch_email_agendamento(cursor, agendamento_id: int, evento: str) -> None:
    """Dispara o e-mail apropriado para o CLIENTE.

    evento:
        - "recebido":   cliente acabou de criar (status=pendente)
        - "confirmado": equipe acabou de confirmar (status: pendente -> agendado)

    Falhas no envio nunca propagam — agendamento ja foi gravado no banco;
    a thread do email_service loga warning se SMTP nao estiver configurado.
    """
    try:
        row = _dados_agendamento_completo(cursor, agendamento_id)
        if not row or not row.get("cliente_email"):
            return

        cliente_nome = row.get("cliente_nome") or "Cliente"
        servico_nome = row.get("servico_nome") or row.get("agenda_nome") or "Atendimento"
        modalidade = row.get("modalidade") or "presencial"
        unidade_nome = _resolver_nome_local(row)
        instrutor = row.get("servico_instrutor")

        from services.email_service import (
            enviar_email,
            email_agendamento_recebido,
            email_agendamento_confirmado,
        )

        if evento == "recebido":
            subject, html = email_agendamento_recebido(
                cliente_nome=cliente_nome,
                servico_nome=servico_nome,
                unidade_nome=unidade_nome,
                inicio=row["inicio"],
                modalidade=modalidade,
                instrutor=instrutor,
            )
        elif evento == "confirmado":
            subject, html = email_agendamento_confirmado(
                cliente_nome=cliente_nome,
                servico_nome=servico_nome,
                unidade_nome=unidade_nome,
                unidade_endereco=row.get("unidade_endereco"),
                unidade_telefone=row.get("unidade_telefone"),
                inicio=row["inicio"],
                modalidade=modalidade,
                instrutor=instrutor,
            )
        else:
            return

        enviar_email(
            para=row["cliente_email"],
            assunto=subject,
            html=html,
            perfil="agenda",   # usa AGENDA_SMTP_* do .env
        )
    except Exception as err:
        logger.warning(f"[ATENDIMENTOS] Falha ao montar e-mail '{evento}' "
                       f"agendamento_id={agendamento_id}: {err}")


def _dispatch_email_equipe_novo(cursor, agendamento_id: int) -> None:
    """Alerta interno pra equipe quando surge um agendamento pendente.

    Destinatarios:
      EQUIPE_AGENDA_EMAILS (vars de ambiente, separados por virgula) OU,
      como fallback, o proprio AGENDA_SMTP_USER (auto-envio).
    """
    try:
        row = _dados_agendamento_completo(cursor, agendamento_id)
        if not row:
            return

        import os
        destinos_raw = (os.getenv("EQUIPE_AGENDA_EMAILS")
                        or os.getenv("AGENDA_SMTP_USER", "")).strip()
        destinos = [e.strip() for e in destinos_raw.split(",") if e.strip() and "@" in e]
        if not destinos:
            logger.info("[ATENDIMENTOS] Nenhum destinatario interno configurado "
                        "(EQUIPE_AGENDA_EMAILS / AGENDA_SMTP_USER vazios).")
            return

        from services.email_service import enviar_email, email_equipe_novo_agendamento

        subject, html = email_equipe_novo_agendamento(
            cliente_nome=row.get("cliente_nome") or "Cliente",
            cliente_email=row.get("cliente_email") or "—",
            cliente_telefone=row.get("cliente_telefone") or "—",
            servico_nome=row.get("servico_nome") or row.get("titulo") or "Atendimento",
            agenda_nome=row.get("agenda_nome") or "Agenda",
            unidade_nome=row.get("unidade_nome"),
            inicio=row["inicio"],
            modalidade=row.get("modalidade") or "presencial",
            observacoes=row.get("observacoes"),
            instrutor=row.get("servico_instrutor"),
        )
        enviar_email(
            para=destinos,
            assunto=subject,
            html=html,
            perfil="agenda",
        )
    except Exception as err:
        logger.warning(f"[ATENDIMENTOS] Falha ao montar alerta interno "
                       f"agendamento_id={agendamento_id}: {err}")


def _agenda_ou_404(cursor, agenda_id: int) -> dict:
    cursor.execute("SELECT * FROM atend_agendas WHERE id=%s", (agenda_id,))
    ag = cursor.fetchone()
    if not ag:
        raise HTTPException(status_code=404, detail="Agenda nao encontrada")
    return ag


def _servico_ou_404(cursor, servico_id: int, agenda_id: int = None) -> dict:
    cursor.execute("SELECT * FROM atend_servicos WHERE id=%s", (servico_id,))
    s = cursor.fetchone()
    if not s or (agenda_id is not None and s["agenda_id"] != agenda_id):
        raise HTTPException(status_code=404, detail="Servico nao encontrado")
    return s


# ============================================================
# NIVEL DE ACESSO (pra UI esconder/mostrar acoes)
# ============================================================

@router.get("/meu-nivel")
def meu_nivel(request: Request):
    """Retorna o nivel de acesso do user logado no modulo:
        admin -> CRUD de estrutura (agendas, cursos, etc)
        op    -> criar/cancelar agendamento (Suporte comum)
        view  -> somente leitura (Comercial)
        none  -> sem acesso

    Frontend usa isso pra esconder botoes que o user nao pode usar.
    Backend tambem valida em cada endpoint — esta resposta e so UX."""
    user = _get_user(request)
    return {"success": True, "nivel": _calc_nivel_suporte(user),
            "grupo": _grupo_do_user(user), "role": user.get("role")}


# ============================================================
# DASHBOARD
# ============================================================

@router.get("/dashboard")
def dashboard(request: Request):
    _exigir_view_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        hoje = date.today()
        amanha = hoje + timedelta(days=1)

        cursor.execute(
            "SELECT COUNT(*) AS n FROM atend_agendamentos "
            "WHERE DATE(inicio)=%s AND status IN ('pendente','agendado','atendido')", (hoje,))
        ag_hoje = cursor.fetchone()["n"]
        cursor.execute(
            "SELECT COUNT(*) AS n FROM atend_agendamentos "
            "WHERE DATE(inicio)=%s AND status IN ('pendente','agendado','atendido')", (amanha,))
        ag_amanha = cursor.fetchone()["n"]
        cursor.execute("SELECT COUNT(*) AS n FROM atend_agendas WHERE ativo=1")
        total_agendas = cursor.fetchone()["n"]
        cursor.execute("SELECT COUNT(*) AS n FROM atend_agendamentos WHERE status='pendente'")
        pendentes = cursor.fetchone()["n"]

        cursor.execute("""
            SELECT DATE_FORMAT(inicio,'%Y-%m') AS mes,
                   COUNT(*) AS total,
                   SUM(status='atendido') AS atendidos
            FROM atend_agendamentos
            WHERE inicio >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
            GROUP BY DATE_FORMAT(inicio,'%Y-%m')
            ORDER BY mes
        """)
        series = cursor.fetchall()

        return {
            "success": True,
            "agendamentos_hoje": ag_hoje,
            "agendamentos_amanha": ag_amanha,
            "total_agendas": total_agendas,
            "pendentes": pendentes,
            "series_mensal": series,
        }
    finally:
        cursor.close()
        conn.close()


@router.get("/agendamentos-do-dia")
def agendamentos_do_dia(request: Request, data: str):
    """Lista todos os agendamentos ativos (pendente/agendado/atendido) de
    uma data, com joins de agenda, unidade, servico, vendedor e equipamento.
    Usado pelos cards 'Hoje' / 'Amanha' do dashboard."""
    _exigir_view_suporte(request)
    dia = _parse_date(data, "data")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT a.id, a.titulo, a.cliente_nome, a.cliente_email, a.cliente_telefone,
                   a.inicio, a.fim, a.modalidade, a.tipo_negocio, a.observacoes,
                   a.status, a.origem,
                   ag.nome AS agenda_nome, ag.cor AS agenda_cor,
                   u.nome AS unidade_nome,
                   COALESCE(s.nome, t.nome) AS servico_nome,
                   CASE WHEN a.treinamento_id IS NOT NULL THEN 'treinamento' ELSE 'curso' END AS tipo_oferta,
                   e.nome AS equipamento_nome,
                   COALESCE(v.name, a.vendedor_nome) AS vendedor_nome
            FROM atend_agendamentos a
            JOIN atend_agendas ag          ON ag.id = a.agenda_id
            LEFT JOIN unidades_cpe u       ON u.id  = ag.unidade_id
            LEFT JOIN atend_servicos s     ON s.id  = a.servico_id
            LEFT JOIN atend_treinamentos t ON t.id  = a.treinamento_id
            LEFT JOIN atend_equipamentos e ON e.id  = a.equipamento_id
            LEFT JOIN users v              ON v.id  = a.vendedor_id
            WHERE DATE(a.inicio) = %s
              AND a.status IN ('pendente','agendado','atendido')
            ORDER BY a.inicio
        """, (dia,))
        return {"success": True,
                "data": str(dia),
                "agendamentos": convert_datetime_list(cursor.fetchall())}
    finally:
        cursor.close()
        conn.close()


@router.get("/clientes")
def listar_clientes(request: Request):
    """Base de clientes derivada dos agendamentos publicos.
    Dedup por e-mail. Pra cada cliente, retorna os dados MAIS RECENTES
    (caso ele tenha atualizado entre agendamentos) + contadores."""
    _exigir_view_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1) Pega o UltimO agendamento de cada email (id maior == mais recente)
        cursor.execute("""
            SELECT a.cliente_email AS email,
                   a.cliente_nome AS nome,
                   a.cliente_telefone AS telefone,
                   a.cliente_empresa AS empresa,
                   a.cliente_funcao AS funcao
            FROM atend_agendamentos a
            WHERE a.cliente_email IS NOT NULL AND TRIM(a.cliente_email) != ''
              AND a.id = (
                SELECT MAX(a2.id) FROM atend_agendamentos a2
                WHERE a2.cliente_email = a.cliente_email
              )
        """)
        dados = {r["email"].lower(): r for r in cursor.fetchall()}

        # 2) Contadores e datas por email
        cursor.execute("""
            SELECT LOWER(cliente_email) AS email,
                   COUNT(*) AS total_agendamentos,
                   SUM(status='atendido')  AS total_atendidos,
                   SUM(status='cancelado') AS total_cancelados,
                   MIN(created_at) AS primeiro_contato,
                   MAX(created_at) AS ultimo_contato
            FROM atend_agendamentos
            WHERE cliente_email IS NOT NULL AND TRIM(cliente_email) != ''
            GROUP BY LOWER(cliente_email)
        """)
        for r in cursor.fetchall():
            d = dados.get(r["email"])
            if d:
                d.update({k: r[k] for k in
                         ("total_agendamentos", "total_atendidos",
                          "total_cancelados", "primeiro_contato", "ultimo_contato")})

        clientes = sorted(dados.values(),
                          key=lambda c: c.get("ultimo_contato") or datetime.min,
                          reverse=True)
        return {"success": True, "clientes": convert_datetime_list(clientes)}
    finally:
        cursor.close()
        conn.close()


@router.put("/clientes")
def atualizar_cliente(request: Request, data: dict):
    """Atualiza os dados de um cliente em TODOS os agendamentos com o mesmo
    e-mail (a base de clientes e derivada da tabela atend_agendamentos, entao
    pra propagar a edicao precisa atualizar a fonte).

    Apenas admin do modulo (ADMIN, TI, RESPONSAVEL_GRUPO do Suporte ou
    grupo 'Suporte ti') pode editar — Comercial e Suporte comum so visualizam.

    E-mail nao e editavel (e a chave de identificacao da base).
    """
    _exigir_admin_suporte(request)
    email = (data.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="E-mail obrigatorio")

    nome     = (data.get("nome")     or "").strip() or None
    telefone = (data.get("telefone") or "").strip() or None
    empresa  = (data.get("empresa")  or "").strip() or None
    funcao   = (data.get("funcao")   or "").strip() or None
    if not nome:
        raise HTTPException(status_code=400, detail="Nome obrigatorio")

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            UPDATE atend_agendamentos
               SET cliente_nome=%s, cliente_telefone=%s,
                   cliente_empresa=%s, cliente_funcao=%s
             WHERE LOWER(cliente_email)=%s
        """, (nome, telefone, empresa, funcao, email))
        conn.commit()
        return {"success": True, "atualizados": cursor.rowcount}
    finally:
        cursor.close()
        conn.close()


@router.get("/clientes/historico")
def historico_cliente(request: Request, email: str):
    """Historico completo de agendamentos de um cliente (por email).
    Mostra curso/treinamento, instrutor, data, modalidade, unidade, status."""
    _exigir_view_suporte(request)
    email = (email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="E-mail obrigatorio")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT a.id, a.inicio, a.fim, a.modalidade, a.tipo_negocio, a.status,
                   a.titulo, a.observacoes, a.created_at,
                   COALESCE(s.nome, t.nome) AS oferta_nome,
                   COALESCE(s.instrutor, t.instrutor) AS instrutor,
                   CASE WHEN a.treinamento_id IS NOT NULL THEN 'treinamento' ELSE 'curso' END AS tipo_oferta,
                   ag.nome AS agenda_nome,
                   u.nome AS unidade_nome,
                   e.nome AS equipamento_nome,
                   COALESCE(v.name, a.vendedor_nome) AS vendedor_nome
            FROM atend_agendamentos a
            JOIN atend_agendas ag          ON ag.id = a.agenda_id
            LEFT JOIN atend_servicos s     ON s.id  = a.servico_id
            LEFT JOIN atend_treinamentos t ON t.id  = a.treinamento_id
            LEFT JOIN unidades_cpe u       ON u.id  = ag.unidade_id
            LEFT JOIN atend_equipamentos e ON e.id  = a.equipamento_id
            LEFT JOIN users v              ON v.id  = a.vendedor_id
            WHERE LOWER(a.cliente_email) = %s
            ORDER BY a.inicio DESC
        """, (email,))
        return {"success": True, "email": email,
                "historico": convert_datetime_list(cursor.fetchall())}
    finally:
        cursor.close()
        conn.close()


@router.get("/pendentes")
def listar_pendentes(request: Request):
    """Todos os agendamentos aguardando confirmacao, de todas as agendas."""
    _exigir_view_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT a.id, a.titulo, a.cliente_nome, a.cliente_email, a.cliente_telefone,
                   a.inicio, a.fim, a.modalidade, a.tipo_negocio, a.observacoes, a.origem,
                   ag.nome AS agenda_nome, u.nome AS unidade_nome,
                   COALESCE(s.nome, t.nome) AS servico_nome,
                   CASE WHEN a.treinamento_id IS NOT NULL THEN 'treinamento' ELSE 'curso' END AS tipo_oferta,
                   e.nome AS equipamento_nome,
                   COALESCE(v.name, a.vendedor_nome) AS vendedor_nome
            FROM atend_agendamentos a
            JOIN atend_agendas ag          ON ag.id = a.agenda_id
            LEFT JOIN unidades_cpe u       ON u.id  = ag.unidade_id
            LEFT JOIN atend_servicos s     ON s.id  = a.servico_id
            LEFT JOIN atend_treinamentos t ON t.id  = a.treinamento_id
            LEFT JOIN atend_equipamentos e ON e.id  = a.equipamento_id
            LEFT JOIN users v              ON v.id  = a.vendedor_id
            WHERE a.status = 'pendente'
            ORDER BY a.inicio
        """)
        return {"success": True, "pendentes": convert_datetime_list(cursor.fetchall())}
    finally:
        cursor.close()
        conn.close()


# ============================================================
# AGENDAS
# ============================================================

@router.get("/agendas")
def listar_agendas(request: Request, incluir_inativas: int = 0):
    _exigir_view_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        where = "" if incluir_inativas else "WHERE a.ativo = 1"
        cursor.execute(f"""
            SELECT a.*, u.nome AS unidade_nome, u.sigla AS unidade_sigla
            FROM atend_agendas a
            LEFT JOIN unidades_cpe u ON u.id = a.unidade_id
            {where}
            ORDER BY a.nome
        """)
        agendas = cursor.fetchall()
        cursor.execute("SELECT * FROM atend_horarios WHERE ativo=1")
        horarios_all = cursor.fetchall()

        hoje = date.today()
        amanha = hoje + timedelta(days=1)
        fim7 = hoje + timedelta(days=7)

        for a in agendas:
            aid = a["id"]
            cursor.execute(
                "SELECT COUNT(*) AS n FROM atend_agendamentos WHERE agenda_id=%s "
                "AND DATE(inicio)=%s AND status IN ('pendente','agendado','atendido')",
                (aid, hoje))
            a["agendamentos_hoje"] = cursor.fetchone()["n"]
            cursor.execute(
                "SELECT COUNT(*) AS n FROM atend_agendamentos WHERE agenda_id=%s "
                "AND DATE(inicio)=%s AND status IN ('pendente','agendado','atendido')",
                (aid, amanha))
            a["agendamentos_amanha"] = cursor.fetchone()["n"]
            cursor.execute(
                "SELECT COUNT(*) AS n FROM atend_agendamentos WHERE agenda_id=%s "
                "AND DATE(inicio) BETWEEN %s AND %s "
                "AND status IN ('pendente','agendado','atendido')", (aid, hoje, fim7))
            ocupados7 = cursor.fetchone()["n"]
            a["agendamentos_prox7"] = ocupados7

            hr = [h for h in horarios_all if h["agenda_id"] == aid]
            capacidade = 0
            for d in range(7):
                capacidade += len(_gerar_horarios(a, hr, hoje + timedelta(days=d),
                                                   a["slot_duracao_min"]))
            a["taxa_ocupacao"] = (None if capacidade == 0
                                  else round(ocupados7 / capacidade * 100, 1))
            a["capacidade_prox7"] = capacidade

        return {"success": True, "agendas": convert_datetime_list(agendas)}
    finally:
        cursor.close()
        conn.close()


@router.get("/agendas/{agenda_id}")
def obter_agenda(agenda_id: int, request: Request):
    _exigir_view_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT a.*, u.nome AS unidade_nome, u.sigla AS unidade_sigla
            FROM atend_agendas a
            LEFT JOIN unidades_cpe u ON u.id = a.unidade_id
            WHERE a.id = %s
        """, (agenda_id,))
        ag = cursor.fetchone()
        if not ag:
            raise HTTPException(status_code=404, detail="Agenda nao encontrada")
        return {"success": True, "agenda": convert_datetime_list([ag])[0]}
    finally:
        cursor.close()
        conn.close()


@router.post("/agendas")
def criar_agenda(request: Request, data: dict):
    """Cria uma nova agenda + pre-popula horarios de funcionamento padrao
    (Seg-Sex 08:00-12:00 + 13:00-18:00 — almoco "bloqueado" naturalmente).
    O admin pode personalizar depois em 'Configurar horarios'."""
    user = _exigir_suporte(request)
    nome = (data.get("nome") or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Nome da agenda e obrigatorio")
    # slot_duracao_min e legado — mantido no banco pra retrocompat, mas nao
    # afeta mais a grade (passo agora vem da duracao do curso). Default 30.
    slot_legado = int(data.get("slot_duracao_min") or 30)
    tipo = data.get("tipo") if data.get("tipo") in ("fisica", "online") else "fisica"
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM atend_agendas WHERE nome=%s", (nome,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Ja existe uma agenda com esse nome")
        cursor.execute("""
            INSERT INTO atend_agendas
                (nome, unidade_id, tipo, descricao, instrucoes, cor, slot_duracao_min, ativo, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 1, %s)
        """, (
            nome, data.get("unidade_id") or None, tipo,
            (data.get("descricao") or "").strip() or None,
            (data.get("instrucoes") or "").strip() or None,
            (data.get("cor") or "#0d9488").strip(), slot_legado, user["id"],
        ))
        nova_id = cursor.lastrowid

        # Horarios padrao CPE: Seg-Sex, manha 09:00-13:00 + tarde 14:00-18:00
        # Almoco 13:00-14:00 fica naturalmente fora.
        # Sabado/Domingo ficam vazios — admin pode adicionar em "Configurar horarios".
        faixas_padrao = []
        for dia_semana in (1, 2, 3, 4, 5):       # JS: 0=dom, 1=seg ... 5=sex, 6=sab
            faixas_padrao.append((nova_id, dia_semana, "09:00", "13:00"))
            faixas_padrao.append((nova_id, dia_semana, "14:00", "18:00"))
        cursor.executemany(
            "INSERT INTO atend_horarios (agenda_id, dia_semana, hora_inicio, hora_fim) "
            "VALUES (%s, %s, %s, %s)", faixas_padrao)

        conn.commit()
        return {"success": True, "id": nova_id}
    finally:
        cursor.close()
        conn.close()


@router.put("/agendas/{agenda_id}")
def atualizar_agenda(agenda_id: int, request: Request, data: dict):
    _exigir_suporte(request)
    nome = (data.get("nome") or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Nome da agenda e obrigatorio")
    dur = int(data.get("slot_duracao_min") or 30)
    if dur < 5 or dur > 480:
        raise HTTPException(status_code=400, detail="Granularidade do slot deve ser entre 5 e 480 minutos")
    tipo = data.get("tipo") if data.get("tipo") in ("fisica", "online") else None
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        atual = _agenda_ou_404(cursor, agenda_id)
        cursor.execute("SELECT id FROM atend_agendas WHERE nome=%s AND id!=%s", (nome, agenda_id))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Ja existe uma agenda com esse nome")
        cursor.execute("""
            UPDATE atend_agendas
               SET nome=%s, unidade_id=%s, tipo=%s, descricao=%s, instrucoes=%s, cor=%s,
                   slot_duracao_min=%s, ativo=%s
             WHERE id=%s
        """, (
            nome, data.get("unidade_id") or None, tipo or atual["tipo"],
            (data.get("descricao") or "").strip() or None,
            (data.get("instrucoes") or "").strip() or None,
            (data.get("cor") or "#0d9488").strip(), dur,
            1 if data.get("ativo", 1) else 0, agenda_id,
        ))
        conn.commit()
        return {"success": True}
    finally:
        cursor.close()
        conn.close()


@router.delete("/agendas/{agenda_id}")
def excluir_agenda(agenda_id: int, request: Request):
    _exigir_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _agenda_ou_404(cursor, agenda_id)
        cursor.execute("DELETE FROM atend_agendas WHERE id=%s", (agenda_id,))
        conn.commit()
        return {"success": True}
    finally:
        cursor.close()
        conn.close()


# ============================================================
# SERVICOS
# ============================================================

@router.get("/agendas/{agenda_id}/servicos")
def listar_servicos(agenda_id: int, request: Request):
    _exigir_view_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _agenda_ou_404(cursor, agenda_id)
        # Conta equipamentos vinculados via tabela polimorfica atend_equipamento_vinculos
        # (substituiu o antigo atend_equipamentos.servico_id que foi dropado na migration 050)
        cursor.execute("""
            SELECT s.*,
                   (SELECT COUNT(*) FROM atend_equipamento_vinculos v
                    JOIN atend_equipamentos e ON e.id = v.equipamento_id
                    WHERE v.entidade='servico' AND v.entidade_id=s.id AND e.ativo=1
                   ) AS total_equipamentos
            FROM atend_servicos s
            WHERE s.agenda_id=%s
            ORDER BY s.ordem, s.nome
        """, (agenda_id,))
        return {"success": True, "servicos": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@router.post("/servicos")
def criar_servico(request: Request, data: dict):
    _exigir_suporte(request)
    agenda_id = data.get("agenda_id")
    nome = (data.get("nome") or "").strip()
    if not agenda_id or not nome:
        raise HTTPException(status_code=400, detail="agenda_id e nome sao obrigatorios")
    dur = int(data.get("duracao_min") or 60)
    if dur < 5 or dur > 1440:
        raise HTTPException(status_code=400, detail="Duracao deve ser entre 5 e 1440 minutos")
    cap_p = max(1, int(data.get("cap_presencial") or 1))
    cap_o = max(1, int(data.get("cap_online") or 1))
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        agenda = _agenda_ou_404(cursor, agenda_id)
        # Regra: curso é APENAS presencial. Não pode ser cadastrado em agenda online.
        if (agenda.get("tipo") or "").lower() == "online":
            raise HTTPException(status_code=400,
                detail="Curso é apenas presencial — escolha uma agenda física.")
        instrutor = (data.get("instrutor") or "").strip() or None
        descricao = (data.get("descricao") or "").strip() or None
        vendedor_id = data.get("vendedor_id") or None
        vendedor_nome = (data.get("vendedor_nome") or "").strip() or None
        # cap_online sempre 0 para curso (UI também esconde o campo)
        cursor.execute("""
            INSERT INTO atend_servicos
                (agenda_id, nome, descricao, duracao_min, cap_presencial, cap_online,
                 instrutor, vendedor_id, vendedor_nome, ativo, ordem)
            VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s)
        """, (agenda_id, nome, descricao, dur, cap_p, instrutor,
              vendedor_id, vendedor_nome,
              1 if data.get("ativo", 1) else 0,
              int(data.get("ordem") or 0)))
        conn.commit()
        return {"success": True, "id": cursor.lastrowid}
    finally:
        cursor.close()
        conn.close()


@router.put("/servicos/{servico_id}")
def atualizar_servico(servico_id: int, request: Request, data: dict):
    _exigir_suporte(request)
    nome = (data.get("nome") or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Nome do servico e obrigatorio")
    dur = int(data.get("duracao_min") or 60)
    if dur < 5 or dur > 1440:
        raise HTTPException(status_code=400, detail="Duracao deve ser entre 5 e 1440 minutos")
    cap_p = max(1, int(data.get("cap_presencial") or 1))
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        servico = _servico_ou_404(cursor, servico_id)
        # Curso é apenas presencial — não pode pertencer a agenda online (proteção dupla)
        cursor.execute("SELECT tipo FROM atend_agendas WHERE id=%s", (servico["agenda_id"],))
        ag = cursor.fetchone()
        if ag and (ag.get("tipo") or "").lower() == "online":
            raise HTTPException(status_code=400,
                detail="Curso é apenas presencial — esta agenda é online.")
        instrutor = (data.get("instrutor") or "").strip() or None
        descricao = (data.get("descricao") or "").strip() or None
        vendedor_id = data.get("vendedor_id") or None
        vendedor_nome = (data.get("vendedor_nome") or "").strip() or None
        # cap_online sempre 0 (curso só presencial)
        cursor.execute("""
            UPDATE atend_servicos
               SET nome=%s, descricao=%s, duracao_min=%s, cap_presencial=%s,
                   cap_online=0, instrutor=%s, vendedor_id=%s, vendedor_nome=%s,
                   ativo=%s, ordem=%s
             WHERE id=%s
        """, (nome, descricao, dur, cap_p, instrutor,
              vendedor_id, vendedor_nome,
              1 if data.get("ativo", 1) else 0,
              int(data.get("ordem") or 0), servico_id))
        conn.commit()
        return {"success": True}
    finally:
        cursor.close()
        conn.close()


@router.delete("/servicos/{servico_id}")
def excluir_servico(servico_id: int, request: Request):
    _exigir_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _servico_ou_404(cursor, servico_id)
        # Limpa midia (polimorfica, sem FK)
        cursor.execute(
            "DELETE FROM atend_midia_fotos WHERE entidade='servico' AND entidade_id=%s",
            (servico_id,))
        cursor.execute(
            "DELETE FROM atend_midia_videos WHERE entidade='servico' AND entidade_id=%s",
            (servico_id,))
        # Limpa vinculos m:n com equipamentos
        cursor.execute(
            "DELETE FROM atend_equipamento_vinculos WHERE entidade='servico' AND entidade_id=%s",
            (servico_id,))
        cursor.execute("DELETE FROM atend_servicos WHERE id=%s", (servico_id,))
        conn.commit()
        return {"success": True}
    finally:
        cursor.close()
        conn.close()


@router.post("/servicos/{servico_id}/duplicar")
def duplicar_servico(servico_id: int, request: Request, data: dict):
    """Duplica um curso em N agendas (unidades). Copia: dados base + vínculos
    com equipamentos. NÃO copia mídia (fotos/vídeos) — cada unidade costuma
    ter prints próprios; o usuário adiciona depois se quiser.

    Body: {"agenda_ids": [id1, id2, ...]} — agendas destino.
    Bloqueia tentativa de duplicar pra mesma agenda do original.
    """
    _exigir_admin_suporte(request)
    agenda_ids = data.get("agenda_ids") or []
    if not isinstance(agenda_ids, list) or not agenda_ids:
        raise HTTPException(status_code=400, detail="Informe ao menos uma agenda destino.")

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        original = _servico_ou_404(cursor, servico_id)

        # Filtra: só agendas existentes e diferentes da original
        cursor.execute(
            "SELECT id, nome FROM atend_agendas WHERE id IN ("
            + ",".join(["%s"] * len(agenda_ids)) + ")",
            tuple(agenda_ids),
        )
        agendas_existentes = {a["id"]: a["nome"] for a in cursor.fetchall()}

        # Pega vínculos do original com equipamentos (m:n)
        cursor.execute(
            "SELECT equipamento_id FROM atend_equipamento_vinculos "
            "WHERE entidade='servico' AND entidade_id=%s",
            (servico_id,),
        )
        equip_ids = [r["equipamento_id"] for r in cursor.fetchall()]

        criados = []
        ignorados = []
        for aid in agenda_ids:
            if aid not in agendas_existentes:
                ignorados.append({"agenda_id": aid, "motivo": "agenda inexistente"})
                continue
            if aid == original["agenda_id"]:
                ignorados.append({"agenda_id": aid, "motivo": "mesma agenda do original"})
                continue

            cursor.execute("""
                INSERT INTO atend_servicos
                    (agenda_id, nome, descricao, duracao_min, cap_presencial, cap_online,
                     instrutor, vendedor_id, vendedor_nome, ativo, ordem)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                aid, original["nome"], original.get("descricao"),
                original.get("duracao_min", 60),
                original.get("cap_presencial", 1), original.get("cap_online", 1),
                original.get("instrutor"),
                original.get("vendedor_id"), original.get("vendedor_nome"),
                int(original.get("ativo") or 1), int(original.get("ordem") or 0),
            ))
            novo_id = cursor.lastrowid

            # Replica vínculos com equipamentos (são globais — podem ser reusados)
            for eq_id in equip_ids:
                cursor.execute(
                    "INSERT IGNORE INTO atend_equipamento_vinculos "
                    "(equipamento_id, entidade, entidade_id) VALUES (%s, 'servico', %s)",
                    (eq_id, novo_id),
                )

            criados.append({
                "id": novo_id, "agenda_id": aid, "agenda_nome": agendas_existentes[aid],
            })

        conn.commit()
        return {
            "success": True,
            "duplicados": len(criados),
            "criados": criados,
            "ignorados": ignorados,
            "equipamentos_replicados": len(equip_ids),
        }
    finally:
        cursor.close()
        conn.close()


# ============================================================
# EQUIPAMENTOS — catalogo global com vinculos m:n
# ============================================================
# Equipamento agora e cadastrado UMA vez e pode ser vinculado a
# multiplos cursos e/ou treinamentos atraves de atend_equipamento_vinculos.

def _equipamento_com_vinculos(cursor, eqs: list) -> list:
    """Anexa lista de vinculos (cursos + treinamentos) em cada equipamento."""
    if not eqs:
        return eqs
    ids = [e["id"] for e in eqs]
    placeholders = ",".join(["%s"] * len(ids))
    cursor.execute(f"""
        SELECT v.equipamento_id, v.entidade, v.entidade_id,
               CASE WHEN v.entidade='servico'
                    THEN (SELECT nome FROM atend_servicos     WHERE id=v.entidade_id)
                    ELSE (SELECT nome FROM atend_treinamentos WHERE id=v.entidade_id) END AS nome,
               CASE WHEN v.entidade='servico'
                    THEN (SELECT agenda_id FROM atend_servicos     WHERE id=v.entidade_id)
                    ELSE (SELECT agenda_id FROM atend_treinamentos WHERE id=v.entidade_id) END AS agenda_id
        FROM atend_equipamento_vinculos v
        WHERE v.equipamento_id IN ({placeholders})
    """, ids)
    vinculos_por_eq = {}
    for v in cursor.fetchall():
        vinculos_por_eq.setdefault(v["equipamento_id"], []).append({
            "entidade": v["entidade"], "entidade_id": v["entidade_id"],
            "nome": v["nome"], "agenda_id": v["agenda_id"],
        })

    # Foto principal (primeira por ordem, em empate menor id) — miniatura na tabela
    cursor.execute(f"""
        SELECT entidade_id, arquivo
        FROM atend_midia_fotos
        WHERE entidade='equipamento' AND entidade_id IN ({placeholders})
        ORDER BY entidade_id, ordem, id
    """, ids)
    foto_por_eq = {}
    for r in cursor.fetchall():
        eid = r["entidade_id"]
        if eid not in foto_por_eq:
            foto_por_eq[eid] = r["arquivo"]

    for e in eqs:
        e["vinculos"] = vinculos_por_eq.get(e["id"], [])
        e["foto_principal"] = foto_por_eq.get(e["id"])
    return eqs


@router.get("/equipamentos")
def listar_todos_equipamentos(request: Request):
    """Catalogo global de equipamentos (com vinculos m:n)."""
    _exigir_view_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM atend_equipamentos ORDER BY ordem, nome")
        return {"success": True, "equipamentos": _equipamento_com_vinculos(cursor, cursor.fetchall())}
    finally:
        cursor.close()
        conn.close()


@router.get("/servicos/{servico_id}/equipamentos")
def listar_equipamentos(servico_id: int, request: Request):
    """Equipamentos vinculados a um curso."""
    _exigir_view_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _servico_ou_404(cursor, servico_id)
        cursor.execute("""
            SELECT e.* FROM atend_equipamentos e
            JOIN atend_equipamento_vinculos v ON v.equipamento_id = e.id
            WHERE v.entidade='servico' AND v.entidade_id=%s
            ORDER BY e.ordem, e.nome
        """, (servico_id,))
        return {"success": True, "equipamentos": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@router.get("/treinamentos/{treinamento_id}/equipamentos")
def listar_equipamentos_treino(treinamento_id: int, request: Request):
    """Equipamentos vinculados a um treinamento."""
    _exigir_view_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _treinamento_ou_404(cursor, treinamento_id)
        cursor.execute("""
            SELECT e.* FROM atend_equipamentos e
            JOIN atend_equipamento_vinculos v ON v.equipamento_id = e.id
            WHERE v.entidade='treinamento' AND v.entidade_id=%s
            ORDER BY e.ordem, e.nome
        """, (treinamento_id,))
        return {"success": True, "equipamentos": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@router.post("/equipamentos")
def criar_equipamento(request: Request, data: dict):
    _exigir_admin_suporte(request)
    nome = (data.get("nome") or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Nome e obrigatorio")
    descricao = (data.get("descricao") or "").strip() or None
    # Opcional: lista de vinculos iniciais  [{"entidade":"servico|treinamento","entidade_id":N}]
    vinculos = data.get("vinculos") or []
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO atend_equipamentos (nome, descricao, ativo, ordem)
            VALUES (%s, %s, %s, %s)
        """, (nome, descricao, 1 if data.get("ativo", 1) else 0,
              int(data.get("ordem") or 0)))
        novo = cursor.lastrowid
        for v in vinculos:
            ent = v.get("entidade")
            ent_id = v.get("entidade_id")
            if ent in ("servico", "treinamento") and ent_id:
                cursor.execute("""
                    INSERT IGNORE INTO atend_equipamento_vinculos
                        (equipamento_id, entidade, entidade_id) VALUES (%s, %s, %s)
                """, (novo, ent, int(ent_id)))
        conn.commit()
        return {"success": True, "id": novo}
    finally:
        cursor.close()
        conn.close()


@router.put("/equipamentos/{equipamento_id}")
def atualizar_equipamento(equipamento_id: int, request: Request, data: dict):
    _exigir_admin_suporte(request)
    nome = (data.get("nome") or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Nome do equipamento e obrigatorio")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM atend_equipamentos WHERE id=%s", (equipamento_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Equipamento nao encontrado")
        descricao = (data.get("descricao") or "").strip() or None
        cursor.execute("""
            UPDATE atend_equipamentos SET nome=%s, descricao=%s, ativo=%s, ordem=%s
             WHERE id=%s
        """, (nome, descricao, 1 if data.get("ativo", 1) else 0,
              int(data.get("ordem") or 0), equipamento_id))

        # Se o cliente mandar vinculos no payload, substitui o conjunto inteiro
        if "vinculos" in data:
            cursor.execute(
                "DELETE FROM atend_equipamento_vinculos WHERE equipamento_id=%s",
                (equipamento_id,))
            for v in (data.get("vinculos") or []):
                ent = v.get("entidade")
                ent_id = v.get("entidade_id")
                if ent in ("servico", "treinamento") and ent_id:
                    cursor.execute("""
                        INSERT IGNORE INTO atend_equipamento_vinculos
                            (equipamento_id, entidade, entidade_id) VALUES (%s, %s, %s)
                    """, (equipamento_id, ent, int(ent_id)))
        conn.commit()
        return {"success": True}
    finally:
        cursor.close()
        conn.close()


# ---- Helpers individuais de vinculo (atalho para adicionar/remover sem PUT inteiro) ----

@router.post("/equipamentos/{equipamento_id}/vinculos")
def add_vinculo_equipamento(equipamento_id: int, request: Request, data: dict):
    _exigir_admin_suporte(request)
    ent = data.get("entidade")
    ent_id = data.get("entidade_id")
    if ent not in ("servico", "treinamento") or not ent_id:
        raise HTTPException(status_code=400, detail="entidade e entidade_id sao obrigatorios")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT IGNORE INTO atend_equipamento_vinculos (equipamento_id, entidade, entidade_id) "
            "VALUES (%s, %s, %s)", (equipamento_id, ent, int(ent_id)))
        conn.commit()
        return {"success": True}
    finally:
        cursor.close()
        conn.close()


@router.delete("/equipamentos/{equipamento_id}/vinculos")
def remover_vinculo_equipamento(equipamento_id: int, request: Request,
                                 entidade: str, entidade_id: int):
    _exigir_admin_suporte(request)
    if entidade not in ("servico", "treinamento"):
        raise HTTPException(status_code=400, detail="entidade invalida")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "DELETE FROM atend_equipamento_vinculos "
            "WHERE equipamento_id=%s AND entidade=%s AND entidade_id=%s",
            (equipamento_id, entidade, entidade_id))
        conn.commit()
        return {"success": True}
    finally:
        cursor.close()
        conn.close()


@router.delete("/equipamentos/{equipamento_id}")
def excluir_equipamento(equipamento_id: int, request: Request):
    _exigir_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM atend_equipamentos WHERE id=%s", (equipamento_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Equipamento nao encontrado")
        cursor.execute("DELETE FROM atend_equipamentos WHERE id=%s", (equipamento_id,))
        conn.commit()
        return {"success": True}
    finally:
        cursor.close()
        conn.close()


# ============================================================
# VENDEDORES (usuarios do grupo Comercial)
# ============================================================

@router.get("/vendedores")
def listar_vendedores(request: Request):
    _exigir_view_suporte(request)
    return {"success": True, "vendedores": _query_vendedores()}


def _query_vendedores() -> list:
    return _query_usuarios_grupo(_GRUPO_COMERCIAL)


def _query_usuarios_grupo(nome_grupo: str) -> list:
    """Retorna usuários ativos de um grupo (id, name). Usado por
    /vendedores (grupo Comercial) e /pilotos (grupo Drone)."""
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT u.id, u.name
            FROM users u
            JOIN cpe_grupo g ON g.id = u.group_id
            WHERE g.name = %s AND u.is_active = 1
            ORDER BY u.name
        """, (nome_grupo,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


@router.get("/pilotos")
def listar_pilotos(request: Request):
    """Usuários ativos do grupo 'Drone' — pilotos/operadores disponíveis
    para vincular a um drone (no cadastro) ou a um agendamento de drone."""
    _exigir_view_suporte(request)
    return {"success": True, "pilotos": _query_usuarios_grupo(_GRUPO_PILOTOS)}


# ============================================================
# FERIADOS
# ============================================================

@router.get("/feriados")
def listar_feriados(request: Request, agenda_id: int = None):
    """Feriados nacionais + (se agenda_id informado) os especificos da agenda,
    do ano corrente em diante."""
    _exigir_view_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        if agenda_id:
            cursor.execute("""
                SELECT f.*, a.nome AS agenda_nome
                FROM atend_feriados f
                LEFT JOIN atend_agendas a ON a.id = f.agenda_id
                WHERE (f.agenda_id IS NULL OR f.agenda_id = %s)
                  AND f.data >= MAKEDATE(YEAR(CURDATE()), 1)
                ORDER BY f.data
            """, (agenda_id,))
        else:
            cursor.execute("""
                SELECT f.*, NULL AS agenda_nome FROM atend_feriados f
                WHERE f.agenda_id IS NULL
                  AND f.data >= MAKEDATE(YEAR(CURDATE()), 1)
                ORDER BY f.data
            """)
        return {"success": True, "feriados": convert_datetime_list(cursor.fetchall())}
    finally:
        cursor.close()
        conn.close()


@router.post("/feriados")
def criar_feriado(request: Request, data: dict):
    user = _exigir_suporte(request)
    dia = _parse_date(data.get("data"))
    nome = (data.get("nome") or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Informe o nome do feriado")
    agenda_id = data.get("agenda_id") or None
    tipo = data.get("tipo")
    if tipo not in ("nacional", "estadual", "municipal", "outro"):
        tipo = "nacional" if not agenda_id else "estadual"
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        if agenda_id:
            _agenda_ou_404(cursor, agenda_id)
            cursor.execute(
                "SELECT id FROM atend_feriados WHERE data=%s AND agenda_id=%s",
                (dia, agenda_id))
        else:
            cursor.execute(
                "SELECT id FROM atend_feriados WHERE data=%s AND agenda_id IS NULL",
                (dia,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Ja existe um feriado nessa data")
        cursor.execute(
            "INSERT INTO atend_feriados (data, nome, agenda_id, tipo, created_by) "
            "VALUES (%s, %s, %s, %s, %s)", (dia, nome, agenda_id, tipo, user["id"]))
        conn.commit()
        return {"success": True, "id": cursor.lastrowid}
    finally:
        cursor.close()
        conn.close()


@router.delete("/feriados/{feriado_id}")
def excluir_feriado(feriado_id: int, request: Request):
    _exigir_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM atend_feriados WHERE id=%s", (feriado_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Feriado nao encontrado")
        cursor.execute("DELETE FROM atend_feriados WHERE id=%s", (feriado_id,))
        conn.commit()
        return {"success": True}
    finally:
        cursor.close()
        conn.close()


# ============================================================
# HORARIOS DE FUNCIONAMENTO
# ============================================================

@router.get("/agendas/{agenda_id}/horarios")
def listar_horarios(agenda_id: int, request: Request):
    _exigir_view_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _agenda_ou_404(cursor, agenda_id)
        cursor.execute(
            "SELECT id, dia_semana, hora_inicio, hora_fim, ativo "
            "FROM atend_horarios WHERE agenda_id=%s ORDER BY dia_semana, hora_inicio",
            (agenda_id,))
        rows = cursor.fetchall()
        for r in rows:
            r["hora_inicio"] = str(_td_to_time(r["hora_inicio"]))[:5]
            r["hora_fim"] = str(_td_to_time(r["hora_fim"]))[:5]
        return {"success": True, "horarios": rows}
    finally:
        cursor.close()
        conn.close()


@router.put("/agendas/{agenda_id}/horarios")
def salvar_horarios(agenda_id: int, request: Request, data: dict):
    _exigir_suporte(request)
    faixas = data.get("horarios")
    if not isinstance(faixas, list):
        raise HTTPException(status_code=400, detail="Lista de horarios invalida")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _agenda_ou_404(cursor, agenda_id)
        limpas = []
        for f in faixas:
            try:
                dia = int(f.get("dia_semana"))
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail="dia_semana invalido")
            if dia < 0 or dia > 6:
                raise HTTPException(status_code=400, detail="dia_semana deve ser entre 0 e 6")
            hi = str(f.get("hora_inicio") or "").strip()[:5]
            hf = str(f.get("hora_fim") or "").strip()[:5]
            if not hi or not hf:
                raise HTTPException(status_code=400, detail="Hora de inicio e fim sao obrigatorias")
            if hf <= hi:
                raise HTTPException(
                    status_code=400,
                    detail=f"A hora de fim ({hf}) deve ser maior que a de inicio ({hi})")
            limpas.append((agenda_id, dia, hi, hf))
        cursor.execute("DELETE FROM atend_horarios WHERE agenda_id=%s", (agenda_id,))
        if limpas:
            cursor.executemany(
                "INSERT INTO atend_horarios (agenda_id, dia_semana, hora_inicio, hora_fim) "
                "VALUES (%s, %s, %s, %s)", limpas)
        conn.commit()
        return {"success": True, "total": len(limpas)}
    finally:
        cursor.close()
        conn.close()


# ============================================================
# AGENDAMENTOS (interno)
# ============================================================

def _row_agendamentos(cursor, agenda_id: int, dt_ini: date, dt_fim: date):
    cursor.execute("""
        SELECT a.*,
               COALESCE(s.nome, t.nome) AS servico_nome,
               CASE WHEN a.treinamento_id IS NOT NULL THEN 'treinamento' ELSE 'curso' END AS tipo_oferta,
               e.nome AS equipamento_nome,
               v.name AS vendedor_nome
        FROM atend_agendamentos a
        LEFT JOIN atend_servicos s     ON s.id = a.servico_id
        LEFT JOIN atend_treinamentos t ON t.id = a.treinamento_id
        LEFT JOIN atend_equipamentos e ON e.id = a.equipamento_id
        LEFT JOIN users v              ON v.id = a.vendedor_id
        WHERE a.agenda_id=%s AND a.inicio < %s AND a.fim >= %s
        ORDER BY a.inicio
    """, (agenda_id, datetime.combine(dt_fim + timedelta(days=1), _time()),
          datetime.combine(dt_ini, _time())))
    return convert_datetime_list(cursor.fetchall())


@router.get("/agendas/{agenda_id}/agendamentos")
def listar_agendamentos(agenda_id: int, request: Request, inicio: str, fim: str):
    _exigir_view_suporte(request)
    dt_ini = _parse_date(inicio, "inicio")
    dt_fim = _parse_date(fim, "fim")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _agenda_ou_404(cursor, agenda_id)
        ags = _row_agendamentos(cursor, agenda_id, dt_ini, dt_fim)
        cursor.execute("""
            SELECT * FROM atend_bloqueios
            WHERE agenda_id=%s AND inicio < %s AND fim >= %s ORDER BY inicio
        """, (agenda_id, datetime.combine(dt_fim + timedelta(days=1), _time()),
              datetime.combine(dt_ini, _time())))
        bloqueios = convert_datetime_list(cursor.fetchall())
        cursor.execute("""
            SELECT id, data, nome, tipo, agenda_id
            FROM atend_feriados
            WHERE data BETWEEN %s AND %s
              AND (agenda_id IS NULL OR agenda_id = %s)
            ORDER BY data
        """, (dt_ini, dt_fim, agenda_id))
        feriados = convert_datetime_list(cursor.fetchall())
        return {"success": True, "agendamentos": ags,
                "bloqueios": bloqueios, "feriados": feriados}
    finally:
        cursor.close()
        conn.close()


def _gravar_agendamento(cursor, agenda_id, dados, origem, created_by):
    """INSERT compartilhado entre o agendamento interno e o publico.
    dados pode ter servico_id OU treinamento_id (mutuamente exclusivos).
    Vendedor: aceita vendedor_id (cadastrado) E/OU vendedor_nome (texto
    livre, quando o cliente nao achou o vendedor na lista).
    Cliente: alem de nome/email/telefone aceita empresa e funcao (opcionais
    — formam a base de clientes derivada)."""
    cursor.execute("""
        INSERT INTO atend_agendamentos
            (agenda_id, servico_id, treinamento_id, drone_id, equipamento_id, titulo,
             cliente_nome, cliente_email, cliente_telefone,
             cliente_empresa, cliente_funcao,
             observacoes, modalidade, tipo_negocio, vendedor_id, vendedor_nome,
             piloto_id,
             inicio, fim, status, origem, created_by)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        agenda_id, dados.get("servico_id"), dados.get("treinamento_id"),
        dados.get("drone_id"),
        dados["equipamento_id"], dados["titulo"],
        dados["cliente_nome"], dados["cliente_email"], dados["cliente_telefone"],
        dados.get("cliente_empresa"), dados.get("cliente_funcao"),
        dados["observacoes"], dados["modalidade"], dados["tipo_negocio"],
        dados["vendedor_id"], dados.get("vendedor_nome"),
        dados.get("piloto_id"),
        dados["inicio"], dados["fim"], dados["status"],
        origem, created_by,
    ))
    return cursor.lastrowid


@router.post("/agendamentos")
def criar_agendamento(request: Request, data: dict):
    """Agendamento criado pela equipe (parte interna)."""
    user = _exigir_op_suporte(request)
    agenda_id = data.get("agenda_id")
    if not agenda_id:
        raise HTTPException(status_code=400, detail="agenda_id e obrigatorio")
    inicio = _parse_dt(data.get("inicio"), "inicio")
    fim = _parse_dt(data.get("fim"), "fim")
    if fim <= inicio:
        raise HTTPException(status_code=400, detail="O fim deve ser posterior ao inicio")

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _agenda_ou_404(cursor, agenda_id)
        servico_id = data.get("servico_id") or None
        treinamento_id = data.get("treinamento_id") or None
        drone_id = data.get("drone_id") or None
        titulo = (data.get("titulo") or "").strip()
        if servico_id:
            srv = _servico_ou_404(cursor, servico_id, agenda_id)
            if not titulo:
                titulo = srv["nome"]
        elif treinamento_id:
            trn = _treinamento_ou_404(cursor, treinamento_id, agenda_id)
            if not titulo:
                titulo = trn["nome"]
        elif drone_id:
            drn = _drone_ou_404(cursor, drone_id, agenda_id)
            if not titulo:
                titulo = drn["nome"]
        if not titulo:
            raise HTTPException(status_code=400, detail="Informe o titulo, curso, treinamento ou drone")
        status = data.get("status") if data.get("status") in _STATUS_VALIDOS else "agendado"
        modalidade = (data.get("modalidade")
                      if data.get("modalidade") in ("presencial", "online") else None)
        if status in _STATUS_OCUPA:
            erro = _checar_vaga(cursor, agenda_id, servico_id, modalidade, inicio, fim,
                                treinamento_id=treinamento_id, drone_id=drone_id)
            if erro:
                raise HTTPException(status_code=409, detail=erro)
        # Piloto: aceita user_id do grupo Drone. Só faz sentido quando a oferta é drone.
        piloto_id = data.get("piloto_id") or None
        if piloto_id and not drone_id:
            piloto_id = None  # silencia em vez de erro — UX limpo
        novo = _gravar_agendamento(cursor, agenda_id, {
            "servico_id": servico_id,
            "treinamento_id": treinamento_id,
            "drone_id": drone_id,
            "equipamento_id": data.get("equipamento_id") or None,
            "titulo": titulo,
            "cliente_nome": (data.get("cliente_nome") or "").strip() or None,
            "cliente_email": (data.get("cliente_email") or "").strip() or None,
            "cliente_telefone": (data.get("cliente_telefone") or "").strip() or None,
            "observacoes": (data.get("observacoes") or "").strip() or None,
            "modalidade": modalidade,
            "tipo_negocio": data.get("tipo_negocio") if data.get("tipo_negocio") in
                ("locacao", "venda") else None,
            "vendedor_id": data.get("vendedor_id") or None,
            "piloto_id": piloto_id,
            "inicio": inicio, "fim": fim, "status": status,
        }, origem="interno", created_by=user["id"])
        conn.commit()
        return {"success": True, "id": novo}
    finally:
        cursor.close()
        conn.close()


@router.put("/agendamentos/{agendamento_id}")
def atualizar_agendamento(agendamento_id: int, request: Request, data: dict):
    _exigir_op_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM atend_agendamentos WHERE id=%s", (agendamento_id,))
        atual = cursor.fetchone()
        if not atual:
            raise HTTPException(status_code=404, detail="Agendamento nao encontrado")

        titulo = (data.get("titulo") or atual["titulo"] or "").strip()
        if not titulo:
            raise HTTPException(status_code=400, detail="O titulo e obrigatorio")
        inicio = _parse_dt(data["inicio"], "inicio") if data.get("inicio") else atual["inicio"]
        fim = _parse_dt(data["fim"], "fim") if data.get("fim") else atual["fim"]
        if fim <= inicio:
            raise HTTPException(status_code=400, detail="O fim deve ser posterior ao inicio")
        novo_status = data.get("status") or atual["status"]
        if novo_status not in _STATUS_VALIDOS:
            raise HTTPException(status_code=400, detail="Status invalido")

        def _campo(chave):
            return (data.get(chave) if chave in data else atual[chave])

        novo_servico = _campo("servico_id") or None
        novo_treinamento = _campo("treinamento_id") or None
        novo_drone = _campo("drone_id") or None
        novo_modalidade = _campo("modalidade")
        if novo_modalidade not in ("presencial", "online"):
            novo_modalidade = None
        if novo_status in _STATUS_OCUPA:
            erro = _checar_vaga(cursor, atual["agenda_id"], novo_servico,
                                novo_modalidade, inicio, fim,
                                excluir_id=agendamento_id,
                                treinamento_id=novo_treinamento,
                                drone_id=novo_drone)
            if erro:
                raise HTTPException(status_code=409, detail=erro)

        # Piloto só faz sentido em agendamento de drone
        novo_piloto = _campo("piloto_id") or None
        if novo_piloto and not novo_drone:
            novo_piloto = None

        cursor.execute("""
            UPDATE atend_agendamentos
               SET titulo=%s, servico_id=%s, treinamento_id=%s, drone_id=%s,
                   equipamento_id=%s,
                   cliente_nome=%s, cliente_email=%s, cliente_telefone=%s,
                   observacoes=%s, modalidade=%s, tipo_negocio=%s, vendedor_id=%s,
                   piloto_id=%s,
                   inicio=%s, fim=%s, status=%s
             WHERE id=%s
        """, (
            titulo, novo_servico, novo_treinamento, novo_drone,
            _campo("equipamento_id") or None,
            (_campo("cliente_nome") or None), (_campo("cliente_email") or None),
            (_campo("cliente_telefone") or None), (_campo("observacoes") or None),
            (_campo("modalidade") or None), (_campo("tipo_negocio") or None),
            (_campo("vendedor_id") or None),
            novo_piloto,
            inicio, fim, novo_status, agendamento_id,
        ))
        conn.commit()
        # E-mail de confirmacao quando o status passa para "agendado"
        # (vindo de "pendente" — a fila tipica de aprovacao da equipe).
        if atual["status"] != "agendado" and novo_status == "agendado":
            _dispatch_email_agendamento(cursor, agendamento_id, "confirmado")
        return {"success": True}
    finally:
        cursor.close()
        conn.close()


@router.delete("/agendamentos/{agendamento_id}")
def excluir_agendamento(agendamento_id: int, request: Request):
    _exigir_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM atend_agendamentos WHERE id=%s", (agendamento_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Agendamento nao encontrado")
        cursor.execute("DELETE FROM atend_agendamentos WHERE id=%s", (agendamento_id,))
        conn.commit()
        return {"success": True}
    finally:
        cursor.close()
        conn.close()


# ============================================================
# BLOQUEIOS
# ============================================================

@router.post("/bloqueios")
def criar_bloqueio(request: Request, data: dict):
    user = _exigir_suporte(request)
    agenda_id = data.get("agenda_id")
    if not agenda_id:
        raise HTTPException(status_code=400, detail="agenda_id e obrigatorio")
    inicio = _parse_dt(data.get("inicio"), "inicio")
    fim = _parse_dt(data.get("fim"), "fim")
    if fim <= inicio:
        raise HTTPException(status_code=400, detail="O fim deve ser posterior ao inicio")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _agenda_ou_404(cursor, agenda_id)
        cursor.execute("""
            INSERT INTO atend_bloqueios (agenda_id, inicio, fim, motivo, created_by)
            VALUES (%s, %s, %s, %s, %s)
        """, (agenda_id, inicio, fim,
              (data.get("motivo") or "").strip() or None, user["id"]))
        conn.commit()
        return {"success": True, "id": cursor.lastrowid}
    finally:
        cursor.close()
        conn.close()


@router.delete("/bloqueios/{bloqueio_id}")
def excluir_bloqueio(bloqueio_id: int, request: Request):
    _exigir_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM atend_bloqueios WHERE id=%s", (bloqueio_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Bloqueio nao encontrado")
        cursor.execute("DELETE FROM atend_bloqueios WHERE id=%s", (bloqueio_id,))
        conn.commit()
        return {"success": True}
    finally:
        cursor.close()
        conn.close()


# ============================================================
# TREINAMENTOS (CRUD interno) - espelho de servicos
# ============================================================

def _treinamento_ou_404(cursor, treinamento_id: int, agenda_id: int = None) -> dict:
    cursor.execute("SELECT * FROM atend_treinamentos WHERE id=%s", (treinamento_id,))
    t = cursor.fetchone()
    if not t or (agenda_id is not None and t["agenda_id"] != agenda_id):
        raise HTTPException(status_code=404, detail="Treinamento nao encontrado")
    return t


@router.get("/agendas/{agenda_id}/treinamentos")
def listar_treinamentos(agenda_id: int, request: Request):
    _exigir_view_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _agenda_ou_404(cursor, agenda_id)
        cursor.execute("""
            SELECT t.*,
                   (SELECT COUNT(*) FROM atend_midia_fotos f
                    WHERE f.entidade='treinamento' AND f.entidade_id=t.id) AS total_fotos,
                   (SELECT COUNT(*) FROM atend_midia_videos v
                    WHERE v.entidade='treinamento' AND v.entidade_id=t.id) AS total_videos
            FROM atend_treinamentos t
            WHERE t.agenda_id=%s ORDER BY t.ordem, t.nome
        """, (agenda_id,))
        return {"success": True, "treinamentos": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@router.post("/treinamentos")
def criar_treinamento(request: Request, data: dict):
    _exigir_admin_suporte(request)
    agenda_id = data.get("agenda_id")
    nome = (data.get("nome") or "").strip()
    if not agenda_id or not nome:
        raise HTTPException(status_code=400, detail="agenda_id e nome sao obrigatorios")
    dur = int(data.get("duracao_min") or 60)
    if dur < 5 or dur > 1440:
        raise HTTPException(status_code=400, detail="Duracao deve ser entre 5 e 1440 minutos")
    cap_p = max(1, int(data.get("cap_presencial") or 1))
    cap_o = max(1, int(data.get("cap_online") or 1))
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _agenda_ou_404(cursor, agenda_id)
        cursor.execute("""
            INSERT INTO atend_treinamentos
                (agenda_id, nome, descricao, duracao_min, cap_presencial, cap_online,
                 instrutor, vendedor_id, vendedor_nome, ativo, ordem)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            agenda_id, nome,
            (data.get("descricao") or "").strip() or None,
            dur, cap_p, cap_o,
            (data.get("instrutor") or "").strip() or None,
            data.get("vendedor_id") or None,
            (data.get("vendedor_nome") or "").strip() or None,
            1 if data.get("ativo", 1) else 0,
            int(data.get("ordem") or 0),
        ))
        conn.commit()
        return {"success": True, "id": cursor.lastrowid}
    finally:
        cursor.close()
        conn.close()


@router.put("/treinamentos/{treinamento_id}")
def atualizar_treinamento(treinamento_id: int, request: Request, data: dict):
    _exigir_admin_suporte(request)
    nome = (data.get("nome") or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Nome do treinamento e obrigatorio")
    dur = int(data.get("duracao_min") or 60)
    if dur < 5 or dur > 1440:
        raise HTTPException(status_code=400, detail="Duracao deve ser entre 5 e 1440 minutos")
    cap_p = max(1, int(data.get("cap_presencial") or 1))
    cap_o = max(1, int(data.get("cap_online") or 1))
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _treinamento_ou_404(cursor, treinamento_id)
        cursor.execute("""
            UPDATE atend_treinamentos
               SET nome=%s, descricao=%s, duracao_min=%s, cap_presencial=%s,
                   cap_online=%s, instrutor=%s, vendedor_id=%s, vendedor_nome=%s,
                   ativo=%s, ordem=%s
             WHERE id=%s
        """, (
            nome,
            (data.get("descricao") or "").strip() or None,
            dur, cap_p, cap_o,
            (data.get("instrutor") or "").strip() or None,
            data.get("vendedor_id") or None,
            (data.get("vendedor_nome") or "").strip() or None,
            1 if data.get("ativo", 1) else 0,
            int(data.get("ordem") or 0), treinamento_id,
        ))
        conn.commit()
        return {"success": True}
    finally:
        cursor.close()
        conn.close()


@router.delete("/treinamentos/{treinamento_id}")
def excluir_treinamento(treinamento_id: int, request: Request):
    _exigir_admin_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _treinamento_ou_404(cursor, treinamento_id)
        # Limpa fotos/videos associadas (polimorfico, sem FK)
        cursor.execute(
            "DELETE FROM atend_midia_fotos WHERE entidade='treinamento' AND entidade_id=%s",
            (treinamento_id,))
        cursor.execute(
            "DELETE FROM atend_midia_videos WHERE entidade='treinamento' AND entidade_id=%s",
            (treinamento_id,))
        # Limpa vinculos m:n com equipamentos
        cursor.execute(
            "DELETE FROM atend_equipamento_vinculos WHERE entidade='treinamento' AND entidade_id=%s",
            (treinamento_id,))
        cursor.execute("DELETE FROM atend_treinamentos WHERE id=%s", (treinamento_id,))
        conn.commit()
        return {"success": True}
    finally:
        cursor.close()
        conn.close()


@router.post("/treinamentos/{treinamento_id}/duplicar")
def duplicar_treinamento(treinamento_id: int, request: Request, data: dict):
    """Duplica um treinamento em N agendas. Mesma lógica de /servicos/duplicar."""
    _exigir_admin_suporte(request)
    agenda_ids = data.get("agenda_ids") or []
    if not isinstance(agenda_ids, list) or not agenda_ids:
        raise HTTPException(status_code=400, detail="Informe ao menos uma agenda destino.")

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        original = _treinamento_ou_404(cursor, treinamento_id)

        cursor.execute(
            "SELECT id, nome FROM atend_agendas WHERE id IN ("
            + ",".join(["%s"] * len(agenda_ids)) + ")",
            tuple(agenda_ids),
        )
        agendas_existentes = {a["id"]: a["nome"] for a in cursor.fetchall()}

        cursor.execute(
            "SELECT equipamento_id FROM atend_equipamento_vinculos "
            "WHERE entidade='treinamento' AND entidade_id=%s",
            (treinamento_id,),
        )
        equip_ids = [r["equipamento_id"] for r in cursor.fetchall()]

        criados = []
        ignorados = []
        for aid in agenda_ids:
            if aid not in agendas_existentes:
                ignorados.append({"agenda_id": aid, "motivo": "agenda inexistente"})
                continue
            if aid == original["agenda_id"]:
                ignorados.append({"agenda_id": aid, "motivo": "mesma agenda do original"})
                continue

            cursor.execute("""
                INSERT INTO atend_treinamentos
                    (agenda_id, nome, descricao, duracao_min, cap_presencial, cap_online,
                     instrutor, vendedor_id, vendedor_nome, ativo, ordem)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                aid, original["nome"], original.get("descricao"),
                original.get("duracao_min", 60),
                original.get("cap_presencial", 1), original.get("cap_online", 1),
                original.get("instrutor"),
                original.get("vendedor_id"), original.get("vendedor_nome"),
                int(original.get("ativo") or 1), int(original.get("ordem") or 0),
            ))
            novo_id = cursor.lastrowid

            for eq_id in equip_ids:
                cursor.execute(
                    "INSERT IGNORE INTO atend_equipamento_vinculos "
                    "(equipamento_id, entidade, entidade_id) VALUES (%s, 'treinamento', %s)",
                    (eq_id, novo_id),
                )

            criados.append({
                "id": novo_id, "agenda_id": aid, "agenda_nome": agendas_existentes[aid],
            })

        conn.commit()
        return {
            "success": True,
            "duplicados": len(criados),
            "criados": criados,
            "ignorados": ignorados,
            "equipamentos_replicados": len(equip_ids),
        }
    finally:
        cursor.close()
        conn.close()


# ============================================================
# DRONES — espelho de treinamentos, mas SEM colisão com curso/treinamento.
# (Drone usa recurso próprio — pode coexistir no mesmo horário/agenda.)
# Os endpoints públicos retornam drones SEM precisar de token (igual treinos).
# ============================================================

def _drone_ou_404(cursor, drone_id: int, agenda_id: int = None) -> dict:
    cursor.execute("SELECT * FROM atend_drones WHERE id=%s", (drone_id,))
    d = cursor.fetchone()
    if not d:
        raise HTTPException(status_code=404, detail="Drone nao encontrado")
    if agenda_id is not None and d["agenda_id"] != agenda_id:
        raise HTTPException(status_code=400, detail="Drone nao pertence a agenda informada")
    return d


@router.get("/agendas/{agenda_id}/drones")
def listar_drones(agenda_id: int, request: Request):
    _exigir_view_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _agenda_ou_404(cursor, agenda_id)
        cursor.execute("""
            SELECT d.*,
              (SELECT COUNT(*) FROM atend_midia_fotos WHERE entidade='drone' AND entidade_id=d.id) AS total_fotos,
              (SELECT COUNT(*) FROM atend_midia_videos WHERE entidade='drone' AND entidade_id=d.id) AS total_videos,
              (SELECT COUNT(*) FROM atend_equipamento_vinculos WHERE entidade='drone' AND entidade_id=d.id) AS total_equipamentos
            FROM atend_drones d
            WHERE d.agenda_id=%s ORDER BY d.ordem, d.nome
        """, (agenda_id,))
        return {"success": True, "drones": cursor.fetchall()}
    finally:
        cursor.close(); conn.close()


@router.post("/drones")
def criar_drone(request: Request, data: dict):
    _exigir_admin_suporte(request)
    agenda_id = data.get("agenda_id")
    nome = (data.get("nome") or "").strip()
    if not agenda_id or not nome:
        raise HTTPException(status_code=400, detail="Agenda e nome sao obrigatorios")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        agenda = _agenda_ou_404(cursor, agenda_id)
        # Regra: drone é APENAS presencial (recurso físico). Não pode ser
        # cadastrado em agenda online.
        if (agenda.get("tipo") or "").lower() == "online":
            raise HTTPException(status_code=400,
                detail="Drone é apenas presencial — escolha uma agenda física.")
        # cap_online sempre 0 para drone (UI também esconde o campo)
        cursor.execute("""
            INSERT INTO atend_drones
                (agenda_id, nome, descricao, duracao_min, cap_presencial, cap_online,
                 instrutor, vendedor_id, vendedor_nome, ativo, ordem)
            VALUES (%s,%s,%s,%s,%s,0,%s,%s,%s,%s,%s)
        """, (
            agenda_id, nome, (data.get("descricao") or "").strip() or None,
            int(data.get("duracao_min") or 60),
            int(data.get("cap_presencial") or 1),
            (data.get("instrutor") or "").strip() or None,
            data.get("vendedor_id") or None,
            (data.get("vendedor_nome") or "").strip() or None,
            1 if data.get("ativo", 1) else 0,
            int(data.get("ordem") or 0),
        ))
        new_id = cursor.lastrowid
        conn.commit()
        return {"success": True, "id": new_id}
    finally:
        cursor.close(); conn.close()


@router.put("/drones/{drone_id}")
def atualizar_drone(drone_id: int, request: Request, data: dict):
    _exigir_admin_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        drone = _drone_ou_404(cursor, drone_id)
        nome = (data.get("nome") or "").strip()
        if not nome:
            raise HTTPException(status_code=400, detail="Nome obrigatorio")
        # Drone é apenas presencial — proteção dupla contra agenda online.
        cursor.execute("SELECT tipo FROM atend_agendas WHERE id=%s", (drone["agenda_id"],))
        ag = cursor.fetchone()
        if ag and (ag.get("tipo") or "").lower() == "online":
            raise HTTPException(status_code=400,
                detail="Drone é apenas presencial — esta agenda é online.")
        # cap_online sempre 0 (drone só presencial)
        cursor.execute("""
            UPDATE atend_drones SET
              nome=%s, descricao=%s, duracao_min=%s,
              cap_presencial=%s, cap_online=0,
              instrutor=%s, vendedor_id=%s, vendedor_nome=%s,
              ativo=%s, ordem=%s
            WHERE id=%s
        """, (
            nome, (data.get("descricao") or "").strip() or None,
            int(data.get("duracao_min") or 60),
            int(data.get("cap_presencial") or 1),
            (data.get("instrutor") or "").strip() or None,
            data.get("vendedor_id") or None,
            (data.get("vendedor_nome") or "").strip() or None,
            1 if data.get("ativo", 1) else 0,
            int(data.get("ordem") or 0), drone_id,
        ))
        conn.commit()
        return {"success": True}
    finally:
        cursor.close(); conn.close()


@router.delete("/drones/{drone_id}")
def excluir_drone(drone_id: int, request: Request):
    _exigir_admin_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _drone_ou_404(cursor, drone_id)
        cursor.execute("DELETE FROM atend_midia_fotos WHERE entidade='drone' AND entidade_id=%s", (drone_id,))
        cursor.execute("DELETE FROM atend_midia_videos WHERE entidade='drone' AND entidade_id=%s", (drone_id,))
        cursor.execute("DELETE FROM atend_equipamento_vinculos WHERE entidade='drone' AND entidade_id=%s", (drone_id,))
        cursor.execute("DELETE FROM atend_drones WHERE id=%s", (drone_id,))
        conn.commit()
        return {"success": True}
    finally:
        cursor.close(); conn.close()


@router.post("/drones/{drone_id}/duplicar")
def duplicar_drone(drone_id: int, request: Request, data: dict):
    """Duplica drone em N agendas. Mesma lógica de duplicar treinamento."""
    _exigir_admin_suporte(request)
    agenda_ids = data.get("agenda_ids") or []
    if not isinstance(agenda_ids, list) or not agenda_ids:
        raise HTTPException(status_code=400, detail="Informe ao menos uma agenda destino.")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        original = _drone_ou_404(cursor, drone_id)
        cursor.execute("SELECT id, nome FROM atend_agendas WHERE id IN ("
                       + ",".join(["%s"] * len(agenda_ids)) + ")", tuple(agenda_ids))
        agendas_existentes = {a["id"]: a["nome"] for a in cursor.fetchall()}
        cursor.execute(
            "SELECT equipamento_id FROM atend_equipamento_vinculos "
            "WHERE entidade='drone' AND entidade_id=%s", (drone_id,))
        equip_ids = [r["equipamento_id"] for r in cursor.fetchall()]

        criados, ignorados = [], []
        for aid in agenda_ids:
            if aid not in agendas_existentes:
                ignorados.append({"agenda_id": aid, "motivo": "agenda inexistente"})
                continue
            if aid == original["agenda_id"]:
                ignorados.append({"agenda_id": aid, "motivo": "mesma agenda do original"})
                continue
            cursor.execute("""
                INSERT INTO atend_drones
                    (agenda_id, nome, descricao, duracao_min, cap_presencial, cap_online,
                     instrutor, vendedor_id, vendedor_nome, ativo, ordem)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                aid, original["nome"], original.get("descricao"),
                original.get("duracao_min", 60),
                original.get("cap_presencial", 1), original.get("cap_online", 1),
                original.get("instrutor"),
                original.get("vendedor_id"), original.get("vendedor_nome"),
                int(original.get("ativo") or 1), int(original.get("ordem") or 0),
            ))
            novo_id = cursor.lastrowid
            for eq_id in equip_ids:
                cursor.execute(
                    "INSERT IGNORE INTO atend_equipamento_vinculos "
                    "(equipamento_id, entidade, entidade_id) VALUES (%s, 'drone', %s)",
                    (eq_id, novo_id))
            criados.append({"id": novo_id, "agenda_id": aid,
                            "agenda_nome": agendas_existentes[aid]})
        conn.commit()
        return {
            "success": True, "duplicados": len(criados),
            "criados": criados, "ignorados": ignorados,
            "equipamentos_replicados": len(equip_ids),
        }
    finally:
        cursor.close(); conn.close()


@router.get("/drones/{drone_id}/equipamentos")
def listar_equipamentos_drone(drone_id: int, request: Request):
    _exigir_view_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT e.id, e.nome, e.descricao
            FROM atend_equipamentos e
            JOIN atend_equipamento_vinculos v ON v.equipamento_id=e.id
            WHERE v.entidade='drone' AND v.entidade_id=%s AND e.ativo=1
            ORDER BY e.ordem, e.nome
        """, (drone_id,))
        return {"success": True, "equipamentos": cursor.fetchall()}
    finally:
        cursor.close(); conn.close()


# ============================================================
# MIDIA (fotos e videos) - polimorfica (servico, treinamento, drone)
# ============================================================

_MIDIA_ENTIDADES = ("servico", "treinamento", "equipamento", "drone")
_UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "web" / "uploads" / "atendimentos"
_UPLOAD_URL_BASE = "/SistemaCPE/web/uploads/atendimentos"
_FOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_MAX_FOTO_MB = 8


_TABELA_POR_ENTIDADE = {
    "servico":      "atend_servicos",
    "treinamento":  "atend_treinamentos",
    "equipamento":  "atend_equipamentos",
}


def _validar_entidade(entidade: str, entidade_id: int, cursor):
    """Garante que a entidade existe (servico, treinamento ou equipamento)."""
    if entidade not in _MIDIA_ENTIDADES:
        raise HTTPException(status_code=400,
                            detail=f"Entidade invalida (use uma de: {', '.join(_MIDIA_ENTIDADES)})")
    tabela = _TABELA_POR_ENTIDADE[entidade]
    cursor.execute(f"SELECT id FROM {tabela} WHERE id=%s", (entidade_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail=f"{entidade.capitalize()} nao encontrado")


@router.get("/midia/{entidade}/{entidade_id}")
def listar_midia(entidade: str, entidade_id: int, request: Request):
    """Lista fotos + videos de um servico/treinamento."""
    _exigir_view_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _validar_entidade(entidade, entidade_id, cursor)
        cursor.execute(
            "SELECT id, arquivo, ordem FROM atend_midia_fotos "
            "WHERE entidade=%s AND entidade_id=%s ORDER BY ordem, id",
            (entidade, entidade_id))
        fotos = cursor.fetchall()
        cursor.execute(
            "SELECT id, url, titulo, ordem FROM atend_midia_videos "
            "WHERE entidade=%s AND entidade_id=%s ORDER BY ordem, id",
            (entidade, entidade_id))
        videos = cursor.fetchall()
        return {"success": True, "fotos": fotos, "videos": videos}
    finally:
        cursor.close()
        conn.close()


@router.post("/midia/{entidade}/{entidade_id}/fotos")
async def upload_foto(entidade: str, entidade_id: int, request: Request,
                      file: UploadFile = File(...)):
    """Upload de uma foto. Aceita um arquivo por chamada (o frontend
    chama N vezes pra upload multiplo). Salva em web/uploads/atendimentos."""
    _exigir_admin_suporte(request)
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _FOTO_EXTS:
        raise HTTPException(status_code=400,
                            detail=f"Extensao nao permitida ({ext}). Use: {', '.join(_FOTO_EXTS)}")

    _UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f"{entidade}_{entidade_id}_{_uuid.uuid4().hex[:12]}{ext}"
    destino = _UPLOAD_ROOT / filename

    # Salva no disco em stream (sem limite de tamanho — desabilitado pra teste)
    with open(destino, "wb") as out:
        while True:
            chunk = await file.read(64 * 1024)
            if not chunk:
                break
            out.write(chunk)

    arquivo_url = f"{_UPLOAD_URL_BASE}/{filename}"
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _validar_entidade(entidade, entidade_id, cursor)
        cursor.execute("""
            INSERT INTO atend_midia_fotos (entidade, entidade_id, arquivo, ordem)
            VALUES (%s, %s, %s,
                    COALESCE((SELECT MAX(ordem)+1 FROM atend_midia_fotos f
                              WHERE f.entidade=%s AND f.entidade_id=%s), 0))
        """, (entidade, entidade_id, arquivo_url, entidade, entidade_id))
        conn.commit()
        return {"success": True, "id": cursor.lastrowid, "arquivo": arquivo_url}
    finally:
        cursor.close()
        conn.close()


@router.delete("/midia/fotos/{foto_id}")
def excluir_foto(foto_id: int, request: Request):
    _exigir_admin_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT arquivo FROM atend_midia_fotos WHERE id=%s", (foto_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Foto nao encontrada")
        # Apaga o arquivo do disco (best-effort)
        rel = (row["arquivo"] or "").replace(_UPLOAD_URL_BASE, "").lstrip("/")
        if rel:
            try:
                (_UPLOAD_ROOT / rel).unlink(missing_ok=True)
            except Exception as err:
                logger.warning(f"[MIDIA] falha ao remover {rel}: {err}")
        cursor.execute("DELETE FROM atend_midia_fotos WHERE id=%s", (foto_id,))
        conn.commit()
        return {"success": True}
    finally:
        cursor.close()
        conn.close()


@router.post("/midia/{entidade}/{entidade_id}/videos")
def adicionar_video(entidade: str, entidade_id: int, request: Request, data: dict):
    _exigir_admin_suporte(request)
    url = (data.get("url") or "").strip()
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=400, detail="URL invalida (precisa comecar com http:// ou https://)")
    titulo = (data.get("titulo") or "").strip() or None
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _validar_entidade(entidade, entidade_id, cursor)
        cursor.execute("""
            INSERT INTO atend_midia_videos (entidade, entidade_id, url, titulo, ordem)
            VALUES (%s, %s, %s, %s,
                    COALESCE((SELECT MAX(ordem)+1 FROM atend_midia_videos v
                              WHERE v.entidade=%s AND v.entidade_id=%s), 0))
        """, (entidade, entidade_id, url, titulo, entidade, entidade_id))
        conn.commit()
        return {"success": True, "id": cursor.lastrowid}
    finally:
        cursor.close()
        conn.close()


@router.delete("/midia/videos/{video_id}")
def excluir_video(video_id: int, request: Request):
    _exigir_admin_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM atend_midia_videos WHERE id=%s", (video_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Video nao encontrado")
        cursor.execute("DELETE FROM atend_midia_videos WHERE id=%s", (video_id,))
        conn.commit()
        return {"success": True}
    finally:
        cursor.close()
        conn.close()


# ============================================================
# PARTE PUBLICA (sem login) - o cliente se agenda
# ============================================================

def _request_eh_funcionario_cpe(request: Request) -> bool:
    """True se a request vem com token de sessão CPE válido — significa que
    é funcionário logado (não cliente público). Cursos são privados e só
    visíveis para funcionários; treinamentos são públicos pra qualquer um.

    Defesa em profundidade: o frontend já esconde cursos pra anônimos,
    mas o backend AQUI é o gatekeeper real. Sem este filtro, basta forjar
    a UI no DevTools pra ver cursos privados."""
    return _resolve_user_id(request) is not None


@router.get("/publico/agendas")
def pub_listar_agendas(request: Request, tipo: str = None):
    """Agendas ativas, com suas ofertas (tela inicial publica).
    - Treinamentos: sempre incluídos (público).
    - Cursos: incluídos APENAS se request vem com token de funcionário CPE.

    Filtro opcional por tipo ('fisica' ou 'online')."""
    filtro_tipo = tipo if tipo in ("fisica", "online") else None
    ehFunc = _request_eh_funcionario_cpe(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        if filtro_tipo:
            cursor.execute("""
                SELECT id, nome, descricao, instrucoes, cor, tipo
                FROM atend_agendas
                WHERE ativo=1 AND tipo=%s
                ORDER BY nome
            """, (filtro_tipo,))
        else:
            cursor.execute("""
                SELECT id, nome, descricao, instrucoes, cor, tipo
                FROM atend_agendas WHERE ativo=1 ORDER BY nome
            """)
        agendas = cursor.fetchall()
        for a in agendas:
            # Cursos e Drones: privados — só funcionário CPE autenticado vê.
            # Treinamentos: sempre públicos (qualquer cliente).
            a["servicos"] = _pub_listar_ofertas(cursor, a["id"], "servico") if ehFunc else []
            a["treinamentos"] = _pub_listar_ofertas(cursor, a["id"], "treinamento")
            a["drones"] = _pub_listar_ofertas(cursor, a["id"], "drone") if ehFunc else []
        return {"success": True, "agendas": agendas}
    finally:
        cursor.close()
        conn.close()


def _pub_listar_ofertas(cursor, agenda_id: int, entidade: str) -> list:
    """Retorna ofertas (servico/treinamento/drone) da agenda com galeria
    de fotos/videos inclusa. Usado pelos endpoints publicos."""
    if entidade == "servico":         tabela = "atend_servicos"
    elif entidade == "treinamento":   tabela = "atend_treinamentos"
    elif entidade == "drone":         tabela = "atend_drones"
    else: raise ValueError("entidade invalida: " + str(entidade))
    cursor.execute(f"""
        SELECT id, nome, descricao, duracao_min, instrutor,
               COALESCE(vendedor_nome,
                        (SELECT name FROM users WHERE id = vendedor_id)) AS vendedor
        FROM {tabela}
        WHERE agenda_id=%s AND ativo=1 ORDER BY ordem, nome
    """, (agenda_id,))
    itens = cursor.fetchall()
    for it in itens:
        cursor.execute(
            "SELECT id, arquivo FROM atend_midia_fotos "
            "WHERE entidade=%s AND entidade_id=%s ORDER BY ordem, id",
            (entidade, it["id"]))
        it["fotos"] = cursor.fetchall()
        cursor.execute(
            "SELECT id, url, titulo FROM atend_midia_videos "
            "WHERE entidade=%s AND entidade_id=%s ORDER BY ordem, id",
            (entidade, it["id"]))
        it["videos"] = cursor.fetchall()
    return itens


@router.get("/publico/agendas/{agenda_id}")
def pub_obter_agenda(agenda_id: int, request: Request):
    """Detalhe de agenda pública. Cursos só pra funcionário CPE logado."""
    ehFunc = _request_eh_funcionario_cpe(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, nome, descricao, instrucoes, cor, tipo, slot_duracao_min "
            "FROM atend_agendas WHERE id=%s AND ativo=1", (agenda_id,))
        ag = cursor.fetchone()
        if not ag:
            raise HTTPException(status_code=404, detail="Agenda nao encontrada")
        ag["servicos"] = _pub_listar_ofertas(cursor, agenda_id, "servico") if ehFunc else []
        ag["treinamentos"] = _pub_listar_ofertas(cursor, agenda_id, "treinamento")
        ag["drones"] = _pub_listar_ofertas(cursor, agenda_id, "drone") if ehFunc else []
        return {"success": True, "agenda": ag}
    finally:
        cursor.close()
        conn.close()


@router.get("/publico/servicos/{servico_id}/equipamentos")
def pub_equipamentos(servico_id: int):
    """Equipamentos vinculados a um servico (curso). Vinculo m:n."""
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT e.id, e.nome, e.descricao
            FROM atend_equipamentos e
            JOIN atend_equipamento_vinculos v ON v.equipamento_id = e.id
            WHERE v.entidade='servico' AND v.entidade_id=%s AND e.ativo=1
            ORDER BY e.ordem, e.nome
        """, (servico_id,))
        return {"success": True, "equipamentos": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@router.get("/publico/treinamentos/{treinamento_id}/equipamentos")
def pub_equipamentos_treino(treinamento_id: int):
    """Equipamentos vinculados a um treinamento."""
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT e.id, e.nome, e.descricao
            FROM atend_equipamentos e
            JOIN atend_equipamento_vinculos v ON v.equipamento_id = e.id
            WHERE v.entidade='treinamento' AND v.entidade_id=%s AND e.ativo=1
            ORDER BY e.ordem, e.nome
        """, (treinamento_id,))
        return {"success": True, "equipamentos": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@router.get("/publico/drones/{drone_id}/equipamentos")
def pub_equipamentos_drone(drone_id: int):
    """Equipamentos vinculados a um drone."""
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT e.id, e.nome, e.descricao
            FROM atend_equipamentos e
            JOIN atend_equipamento_vinculos v ON v.equipamento_id = e.id
            WHERE v.entidade='drone' AND v.entidade_id=%s AND e.ativo=1
            ORDER BY e.ordem, e.nome
        """, (drone_id,))
        return {"success": True, "equipamentos": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@router.get("/publico/vendedores")
def pub_vendedores():
    return {"success": True, "vendedores": _query_vendedores()}


def _contexto_agenda_oferta(cursor, agenda_id: int,
                            servico_id: int = None,
                            treinamento_id: int = None,
                            drone_id: int = None):
    """Carrega agenda ativa + oferta ativa (curso, treinamento ou drone) +
    faixas de horario. A oferta retornada tem chaves uniformes: id, nome,
    agenda_id, duracao_min, cap_presencial, cap_online + `entidade`."""
    cursor.execute("SELECT * FROM atend_agendas WHERE id=%s AND ativo=1", (agenda_id,))
    agenda = cursor.fetchone()
    if not agenda:
        raise HTTPException(status_code=404, detail="Agenda nao encontrada")
    oferta = None
    if servico_id:
        cursor.execute("SELECT * FROM atend_servicos WHERE id=%s AND ativo=1", (servico_id,))
        s = cursor.fetchone()
        if not s or s["agenda_id"] != agenda_id:
            raise HTTPException(status_code=404, detail="Curso nao encontrado nessa agenda")
        oferta = dict(s); oferta["entidade"] = "servico"
    elif treinamento_id:
        cursor.execute("SELECT * FROM atend_treinamentos WHERE id=%s AND ativo=1", (treinamento_id,))
        t = cursor.fetchone()
        if not t or t["agenda_id"] != agenda_id:
            raise HTTPException(status_code=404, detail="Treinamento nao encontrado nessa agenda")
        oferta = dict(t); oferta["entidade"] = "treinamento"
    elif drone_id:
        cursor.execute("SELECT * FROM atend_drones WHERE id=%s AND ativo=1", (drone_id,))
        d = cursor.fetchone()
        if not d or d["agenda_id"] != agenda_id:
            raise HTTPException(status_code=404, detail="Drone nao encontrado nessa agenda")
        oferta = dict(d); oferta["entidade"] = "drone"
    else:
        raise HTTPException(status_code=400,
                            detail="Informe servico_id, treinamento_id ou drone_id")
    cursor.execute("SELECT * FROM atend_horarios WHERE agenda_id=%s", (agenda_id,))
    horarios = cursor.fetchall()
    return agenda, oferta, horarios


@router.get("/publico/agendas/{agenda_id}/dias")
def pub_dias_disponiveis(agenda_id: int, servico_id: int = None,
                         treinamento_id: int = None, drone_id: int = None,
                         modalidade: str = None):
    """Dias com pelo menos um horario livre para a oferta (curso, treinamento
    ou drone) na modalidade escolhida. Passe APENAS UM dos IDs."""
    if modalidade not in ("presencial", "online"):
        modalidade = None
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        agenda, oferta, horarios = _contexto_agenda_oferta(
            cursor, agenda_id, servico_id, treinamento_id, drone_id)
        agora = datetime.now()
        hoje = agora.date()
        fim_janela = datetime.combine(hoje + timedelta(days=_DIAS_BUSCA_PUBLICA), _time())
        ags, blqs = _eventos_periodo(cursor, agenda_id,
                                     datetime.combine(hoje, _time()), fim_janela)
        feriados = _feriados_set(cursor, agenda_id, hoje,
                                 hoje + timedelta(days=_DIAS_BUSCA_PUBLICA))
        dur = oferta["duracao_min"]
        cap_p, cap_o = oferta["cap_presencial"], oferta["cap_online"]
        dias = []
        for i in range(_DIAS_BUSCA_PUBLICA):
            d = hoje + timedelta(days=i)
            if str(d) in feriados:
                continue
            total = 0
            livres = 0
            for ini in _gerar_horarios(agenda, horarios, d, dur):
                if ini < agora:
                    continue
                total += 1
                if _slot_tem_vaga(ags, blqs, oferta["id"], cap_p, cap_o,
                                  ini, ini + timedelta(minutes=dur),
                                  modalidade, entidade=oferta["entidade"]):
                    livres += 1
            if total:
                dias.append({"data": str(d), "total": total, "livres": livres})
        return {"success": True, "dias": dias}
    finally:
        cursor.close()
        conn.close()


@router.get("/publico/agendas/{agenda_id}/horarios")
def pub_horarios_disponiveis(agenda_id: int, data: str,
                             servico_id: int = None, treinamento_id: int = None,
                             drone_id: int = None, modalidade: str = None):
    """Horarios de inicio da oferta numa data, com a flag de disponibilidade."""
    if modalidade not in ("presencial", "online"):
        modalidade = None
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        agenda, oferta, horarios = _contexto_agenda_oferta(
            cursor, agenda_id, servico_id, treinamento_id, drone_id)
        dia = _parse_date(data)
        if _eh_feriado(cursor, agenda_id, dia):
            return {"success": True, "duracao_min": oferta["duracao_min"],
                    "horarios": [], "feriado": True}
        agora = datetime.now()
        dur = oferta["duracao_min"]
        cap_p, cap_o = oferta["cap_presencial"], oferta["cap_online"]
        ags, blqs = _eventos_periodo(cursor, agenda_id,
                                     datetime.combine(dia, _time()),
                                     datetime.combine(dia + timedelta(days=1), _time()))
        slots = []
        for ini in _gerar_horarios(agenda, horarios, dia, dur):
            if ini < agora:
                continue
            fim = ini + timedelta(minutes=dur)
            slots.append({
                "inicio": ini.strftime("%Y-%m-%d %H:%M"),
                "fim": fim.strftime("%Y-%m-%d %H:%M"),
                "label": ini.strftime("%H:%M"),
                "disponivel": _slot_tem_vaga(ags, blqs, oferta["id"],
                                             cap_p, cap_o, ini, fim,
                                             modalidade, entidade=oferta["entidade"]),
            })
        return {"success": True, "duracao_min": dur, "horarios": slots}
    finally:
        cursor.close()
        conn.close()


@router.post("/publico/agendar")
def pub_agendar(data: dict, request: Request):
    """Cria o agendamento feito pelo cliente. Entra como 'pendente'.

    - Cursos (servico_id): privados, só funcionário CPE autenticado pode marcar.
    - Treinamentos e Drones: livres pra qualquer cliente."""
    agenda_id = data.get("agenda_id")
    servico_id = data.get("servico_id") or None
    treinamento_id = data.get("treinamento_id") or None
    drone_id = data.get("drone_id") or None
    if not agenda_id or (not servico_id and not treinamento_id and not drone_id):
        raise HTTPException(status_code=400,
                            detail="Selecione a agenda e o curso, treinamento ou drone")

    # Guarda: curso e drone só pra funcionário CPE logado (privados).
    if (servico_id or drone_id) and not _request_eh_funcionario_cpe(request):
        item = "curso" if servico_id else "drone"
        raise HTTPException(
            status_code=403,
            detail=f"Agendamento de {item} é restrito a funcionários CPE autenticados.",
        )
    nome = (data.get("cliente_nome") or "").strip()
    email = (data.get("cliente_email") or "").strip()
    telefone = (data.get("cliente_telefone") or "").strip()
    if not nome or not email or not telefone:
        raise HTTPException(status_code=400, detail="Nome, e-mail e telefone sao obrigatorios")
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="E-mail invalido")
    inicio = _parse_dt(data.get("inicio"), "inicio")

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        agenda, oferta, horarios = _contexto_agenda_oferta(
            cursor, agenda_id, servico_id, treinamento_id, drone_id)
        dur = oferta["duracao_min"]
        fim = inicio + timedelta(minutes=dur)

        # o inicio precisa ser um horario valido gerado pela config
        if inicio not in _gerar_horarios(agenda, horarios, inicio.date(), dur):
            raise HTTPException(status_code=400,
                                detail="Horario fora do funcionamento da agenda")
        if inicio < datetime.now():
            raise HTTPException(status_code=400, detail="Esse horario ja passou")

        modalidade = data.get("modalidade")
        if modalidade not in ("presencial", "online"):
            raise HTTPException(status_code=400,
                                detail="Informe se o atendimento sera presencial ou online")
        # valida capacidade da oferta para a modalidade escolhida
        erro = _checar_vaga(cursor, agenda_id, servico_id, modalidade, inicio, fim,
                            treinamento_id=treinamento_id, drone_id=drone_id)
        if erro:
            raise HTTPException(status_code=409, detail=erro + " Escolha outro horario.")

        # equipamento (se informado) precisa estar vinculado a essa oferta
        equipamento_id = data.get("equipamento_id") or None
        if equipamento_id:
            cursor.execute(
                "SELECT 1 FROM atend_equipamento_vinculos "
                "WHERE equipamento_id=%s AND entidade=%s AND entidade_id=%s",
                (equipamento_id, oferta["entidade"], oferta["id"]))
            if not cursor.fetchone():
                raise HTTPException(status_code=400,
                                    detail="Equipamento nao vinculado a essa oferta")
        # vendedor: cliente pode escolher um cadastrado (vendedor_id) OU
        # informar o nome livre (vendedor_nome) quando nao achou na lista.
        vendedor_id = data.get("vendedor_id") or None
        vendedor_nome_livre = (data.get("vendedor_nome") or "").strip() or None
        if vendedor_id:
            if not any(v["id"] == int(vendedor_id) for v in _query_vendedores()):
                raise HTTPException(status_code=400, detail="Vendedor invalido")
            vendedor_nome_livre = None  # tem cadastro: ignora nome livre

        # Piloto: só faz sentido em agendamento de drone (oferta=drone).
        piloto_id_pub = data.get("piloto_id") or None
        if piloto_id_pub and not drone_id:
            piloto_id_pub = None
        novo = _gravar_agendamento(cursor, agenda_id, {
            "servico_id": servico_id,
            "treinamento_id": treinamento_id,
            "drone_id": drone_id,
            "equipamento_id": equipamento_id,
            "titulo": oferta["nome"],
            "cliente_nome": nome,
            "cliente_email": email,
            "cliente_telefone": telefone,
            "cliente_empresa": (data.get("cliente_empresa") or "").strip() or None,
            "cliente_funcao": (data.get("cliente_funcao") or "").strip() or None,
            "observacoes": (data.get("observacoes") or "").strip() or None,
            "modalidade": data.get("modalidade") if data.get("modalidade") in
                ("presencial", "online") else None,
            "tipo_negocio": data.get("tipo_negocio") if data.get("tipo_negocio") in
                ("locacao", "venda") else None,
            "vendedor_id": vendedor_id,
            "vendedor_nome": vendedor_nome_livre,
            "piloto_id": piloto_id_pub,
            "inicio": inicio, "fim": fim, "status": "pendente",
        }, origem="publico", created_by=None)
        conn.commit()
        # 1) E-mail de "recebido, aguardando confirmacao" para o cliente
        # 2) Alerta interno pra equipe (suporte.agenda.cpe@) — fica sabendo do pendente
        # Ambos sao async no email_service — nunca bloqueiam nem derrubam o endpoint.
        _dispatch_email_agendamento(cursor, novo, "recebido")
        _dispatch_email_equipe_novo(cursor, novo)
        return {"success": True, "id": novo,
                "mensagem": "Agendamento registrado! Aguarde a confirmacao da equipe."}
    finally:
        cursor.close()
        conn.close()
