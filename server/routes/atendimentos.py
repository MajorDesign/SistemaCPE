"""
Modulo Equipe de Suporte - Agendas de atendimento.

Parte interna (ADMIN/TI): agendas, horarios, servicos, equipamentos,
agendamentos, bloqueios e dashboard.
Parte publica (sem login): o cliente lista agendas, escolhe servico, dia
e horario, preenche os dados e cria um agendamento que entra como
'pendente' ate a equipe confirmar.
"""

from fastapi import APIRouter, HTTPException, Request
from database import get_db_or_404, convert_datetime_list
from datetime import datetime, date, timedelta, time as _time
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/atendimentos", tags=["Atendimentos"])

# Status de agendamento que ocupam o horario (nao podem sobrepor).
_STATUS_OCUPA = ("pendente", "agendado", "atendido")
_STATUS_VALIDOS = ("pendente", "agendado", "atendido", "cancelado", "nao_compareceu")
_GRUPO_COMERCIAL = "Comercial"
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

    O passo entre os inicios e a granularidade da agenda (slot_duracao_min);
    o bloco reservado tem o tamanho da duracao do servico.
    """
    js_wd = (dia.weekday() + 1) % 7          # Python Mon=0 -> JS Dom=0
    step = max(5, int(agenda.get("slot_duracao_min") or 30))
    dur = max(5, int(duracao_min or step))
    out = []
    for h in horarios:
        if int(h["dia_semana"]) != js_wd or not h.get("ativo", 1):
            continue
        ini = datetime.combine(dia, _td_to_time(h["hora_inicio"]))
        fim = datetime.combine(dia, _td_to_time(h["hora_fim"]))
        atual = ini
        while atual + timedelta(minutes=dur) <= fim:
            out.append(atual)
            atual += timedelta(minutes=step)
    return sorted(set(out))


def _eventos_periodo(cursor, agenda_id: int, ini: datetime, fim: datetime):
    """Carrega de uma vez agendamentos ativos e bloqueios da agenda no
    periodo. Usado pelas telas de disponibilidade (calcula em memoria)."""
    cursor.execute(
        "SELECT inicio, fim, servico_id, modalidade FROM atend_agendamentos "
        "WHERE agenda_id=%s AND status IN ('pendente','agendado','atendido') "
        "AND inicio < %s AND fim > %s", (agenda_id, fim, ini))
    ags = cursor.fetchall()
    cursor.execute(
        "SELECT inicio, fim FROM atend_bloqueios "
        "WHERE agenda_id=%s AND inicio < %s AND fim > %s", (agenda_id, fim, ini))
    blqs = cursor.fetchall()
    return ags, blqs


def _slot_tem_vaga(ags, blqs, servico_id, cap_p, cap_o, ini, fim, modalidade=None) -> bool:
    """True se o slot tem vaga. Se `modalidade` for informada, checa so ela;
    senao, considera vaga em qualquer modalidade. Presencial e online sao
    contados de forma independente."""
    if any(b["inicio"] < fim and b["fim"] > ini for b in blqs):
        return False

    def _conta(modal):
        return sum(1 for a in ags if a["servico_id"] == servico_id
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


def _checar_vaga(cursor, agenda_id, servico_id, modalidade, inicio, fim,
                 excluir_id=None):
    """Valida se cabe um agendamento. Retorna None se ha vaga, ou uma
    mensagem de erro. Capacidade vem do curso (cap_presencial/cap_online);
    presencial e online sao limites independentes."""
    if _eh_feriado(cursor, agenda_id, inicio.date()):
        return "Esse dia e feriado nessa agenda."
    cursor.execute(
        "SELECT id FROM atend_bloqueios WHERE agenda_id=%s AND inicio<%s AND fim>%s",
        (agenda_id, fim, inicio))
    if cursor.fetchone():
        return "Esse horario esta bloqueado nessa agenda."

    cap = 1
    por_modalidade = bool(servico_id) and modalidade in ("presencial", "online")
    if por_modalidade:
        cursor.execute(
            "SELECT cap_presencial, cap_online FROM atend_servicos WHERE id=%s",
            (servico_id,))
        s = cursor.fetchone()
        if s:
            bruto = s["cap_online"] if modalidade == "online" else s["cap_presencial"]
            cap = max(1, int(bruto or 1))

    sql = ("SELECT COUNT(*) AS n FROM atend_agendamentos WHERE agenda_id=%s "
           "AND status IN ('pendente','agendado','atendido') "
           "AND inicio<%s AND fim>%s")
    params = [agenda_id, fim, inicio]
    if por_modalidade:
        # capacidade por curso + modalidade (presencial e online independentes)
        sql += " AND servico_id=%s AND modalidade=%s"
        params += [servico_id, modalidade]
    if excluir_id:
        sql += " AND id != %s"
        params.append(excluir_id)
    cursor.execute(sql, params)
    if cursor.fetchone()["n"] >= cap:
        if por_modalidade:
            rotulo = "online" if modalidade == "online" else "presenciais"
            return f"Esse horario ja atingiu o limite de atendimentos {rotulo}."
        return "Esse horario ja esta ocupado nessa agenda."
    return None


def _dados_agendamento_completo(cursor, agendamento_id: int) -> dict | None:
    """Carrega todos os dados de um agendamento (joins com agenda, unidade,
    servico) — base para os 3 e-mails (cliente recebido/confirmado, equipe alerta)."""
    cursor.execute("""
        SELECT a.cliente_nome, a.cliente_email, a.cliente_telefone,
               a.inicio, a.modalidade, a.observacoes, a.titulo,
               s.nome AS servico_nome, s.instrutor AS servico_instrutor,
               ag.nome AS agenda_nome, ag.tipo AS agenda_tipo,
               u.nome AS unidade_nome, u.endereco AS unidade_endereco,
               u.telefone AS unidade_telefone
        FROM atend_agendamentos a
        JOIN atend_agendas ag        ON ag.id = a.agenda_id
        LEFT JOIN atend_servicos s   ON s.id  = a.servico_id
        LEFT JOIN unidades_cpe u     ON u.id  = ag.unidade_id
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
                   s.nome AS servico_nome, e.nome AS equipamento_nome,
                   v.name AS vendedor_nome
            FROM atend_agendamentos a
            JOIN atend_agendas ag        ON ag.id = a.agenda_id
            LEFT JOIN unidades_cpe u     ON u.id  = ag.unidade_id
            LEFT JOIN atend_servicos s   ON s.id  = a.servico_id
            LEFT JOIN atend_equipamentos e ON e.id = a.equipamento_id
            LEFT JOIN users v            ON v.id  = a.vendedor_id
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
                   s.nome AS servico_nome, e.nome AS equipamento_nome,
                   v.name AS vendedor_nome
            FROM atend_agendamentos a
            JOIN atend_agendas ag       ON ag.id = a.agenda_id
            LEFT JOIN unidades_cpe u    ON u.id  = ag.unidade_id
            LEFT JOIN atend_servicos s  ON s.id  = a.servico_id
            LEFT JOIN atend_equipamentos e ON e.id = a.equipamento_id
            LEFT JOIN users v           ON v.id  = a.vendedor_id
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
    user = _exigir_suporte(request)
    nome = (data.get("nome") or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Nome da agenda e obrigatorio")
    dur = int(data.get("slot_duracao_min") or 30)
    if dur < 5 or dur > 480:
        raise HTTPException(status_code=400, detail="Granularidade do slot deve ser entre 5 e 480 minutos")
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
            (data.get("cor") or "#0d9488").strip(), dur, user["id"],
        ))
        conn.commit()
        return {"success": True, "id": cursor.lastrowid}
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
        cursor.execute(
            "SELECT s.*, (SELECT COUNT(*) FROM atend_equipamentos e "
            "WHERE e.servico_id=s.id AND e.ativo=1) AS total_equipamentos "
            "FROM atend_servicos s WHERE s.agenda_id=%s ORDER BY s.ordem, s.nome",
            (agenda_id,))
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
        _agenda_ou_404(cursor, agenda_id)
        instrutor = (data.get("instrutor") or "").strip() or None
        cursor.execute("""
            INSERT INTO atend_servicos
                (agenda_id, nome, duracao_min, cap_presencial, cap_online,
                 instrutor, ativo, ordem)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (agenda_id, nome, dur, cap_p, cap_o, instrutor,
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
    cap_o = max(1, int(data.get("cap_online") or 1))
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _servico_ou_404(cursor, servico_id)
        instrutor = (data.get("instrutor") or "").strip() or None
        cursor.execute("""
            UPDATE atend_servicos SET nome=%s, duracao_min=%s, cap_presencial=%s,
                   cap_online=%s, instrutor=%s, ativo=%s, ordem=%s
             WHERE id=%s
        """, (nome, dur, cap_p, cap_o, instrutor,
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
        cursor.execute("DELETE FROM atend_servicos WHERE id=%s", (servico_id,))
        conn.commit()
        return {"success": True}
    finally:
        cursor.close()
        conn.close()


# ============================================================
# EQUIPAMENTOS
# ============================================================

@router.get("/servicos/{servico_id}/equipamentos")
def listar_equipamentos(servico_id: int, request: Request):
    _exigir_view_suporte(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _servico_ou_404(cursor, servico_id)
        cursor.execute(
            "SELECT * FROM atend_equipamentos WHERE servico_id=%s ORDER BY ordem, nome",
            (servico_id,))
        return {"success": True, "equipamentos": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@router.post("/equipamentos")
def criar_equipamento(request: Request, data: dict):
    _exigir_suporte(request)
    servico_id = data.get("servico_id")
    nome = (data.get("nome") or "").strip()
    if not servico_id or not nome:
        raise HTTPException(status_code=400, detail="servico_id e nome sao obrigatorios")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        _servico_ou_404(cursor, servico_id)
        cursor.execute("""
            INSERT INTO atend_equipamentos (servico_id, nome, ativo, ordem)
            VALUES (%s, %s, %s, %s)
        """, (servico_id, nome, 1 if data.get("ativo", 1) else 0,
              int(data.get("ordem") or 0)))
        conn.commit()
        return {"success": True, "id": cursor.lastrowid}
    finally:
        cursor.close()
        conn.close()


@router.put("/equipamentos/{equipamento_id}")
def atualizar_equipamento(equipamento_id: int, request: Request, data: dict):
    _exigir_suporte(request)
    nome = (data.get("nome") or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Nome do equipamento e obrigatorio")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM atend_equipamentos WHERE id=%s", (equipamento_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Equipamento nao encontrado")
        cursor.execute("""
            UPDATE atend_equipamentos SET nome=%s, ativo=%s, ordem=%s WHERE id=%s
        """, (nome, 1 if data.get("ativo", 1) else 0,
              int(data.get("ordem") or 0), equipamento_id))
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
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT u.id, u.name
            FROM users u
            JOIN cpe_grupo g ON g.id = u.group_id
            WHERE g.name = %s AND u.is_active = 1
            ORDER BY u.name
        """, (_GRUPO_COMERCIAL,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


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
        SELECT a.*, s.nome AS servico_nome, e.nome AS equipamento_nome,
               v.name AS vendedor_nome
        FROM atend_agendamentos a
        LEFT JOIN atend_servicos s     ON s.id = a.servico_id
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
    """INSERT compartilhado entre o agendamento interno e o publico."""
    cursor.execute("""
        INSERT INTO atend_agendamentos
            (agenda_id, servico_id, equipamento_id, titulo,
             cliente_nome, cliente_email, cliente_telefone, observacoes,
             modalidade, tipo_negocio, vendedor_id,
             inicio, fim, status, origem, created_by)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        agenda_id, dados["servico_id"], dados["equipamento_id"], dados["titulo"],
        dados["cliente_nome"], dados["cliente_email"], dados["cliente_telefone"],
        dados["observacoes"], dados["modalidade"], dados["tipo_negocio"],
        dados["vendedor_id"], dados["inicio"], dados["fim"], dados["status"],
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
        titulo = (data.get("titulo") or "").strip()
        if servico_id:
            srv = _servico_ou_404(cursor, servico_id, agenda_id)
            if not titulo:
                titulo = srv["nome"]
        if not titulo:
            raise HTTPException(status_code=400, detail="Informe o titulo ou um servico")
        status = data.get("status") if data.get("status") in _STATUS_VALIDOS else "agendado"
        modalidade = (data.get("modalidade")
                      if data.get("modalidade") in ("presencial", "online") else None)
        if status in _STATUS_OCUPA:
            erro = _checar_vaga(cursor, agenda_id, servico_id, modalidade, inicio, fim)
            if erro:
                raise HTTPException(status_code=409, detail=erro)
        novo = _gravar_agendamento(cursor, agenda_id, {
            "servico_id": servico_id,
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
        novo_modalidade = _campo("modalidade")
        if novo_modalidade not in ("presencial", "online"):
            novo_modalidade = None
        if novo_status in _STATUS_OCUPA:
            erro = _checar_vaga(cursor, atual["agenda_id"], novo_servico,
                                novo_modalidade, inicio, fim, excluir_id=agendamento_id)
            if erro:
                raise HTTPException(status_code=409, detail=erro)

        cursor.execute("""
            UPDATE atend_agendamentos
               SET titulo=%s, servico_id=%s, equipamento_id=%s,
                   cliente_nome=%s, cliente_email=%s, cliente_telefone=%s,
                   observacoes=%s, modalidade=%s, tipo_negocio=%s, vendedor_id=%s,
                   inicio=%s, fim=%s, status=%s
             WHERE id=%s
        """, (
            titulo, _campo("servico_id") or None, _campo("equipamento_id") or None,
            (_campo("cliente_nome") or None), (_campo("cliente_email") or None),
            (_campo("cliente_telefone") or None), (_campo("observacoes") or None),
            (_campo("modalidade") or None), (_campo("tipo_negocio") or None),
            (_campo("vendedor_id") or None),
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
# PARTE PUBLICA (sem login) - o cliente se agenda
# ============================================================

@router.get("/publico/agendas")
def pub_listar_agendas(tipo: str = None):
    """Agendas ativas, com seus servicos ativos (tela inicial publica).
    Filtro opcional por tipo ('fisica' ou 'online')."""
    filtro_tipo = tipo if tipo in ("fisica", "online") else None
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
            cursor.execute(
                "SELECT id, nome, duracao_min FROM atend_servicos "
                "WHERE agenda_id=%s AND ativo=1 ORDER BY ordem, nome", (a["id"],))
            a["servicos"] = cursor.fetchall()
        return {"success": True, "agendas": agendas}
    finally:
        cursor.close()
        conn.close()


@router.get("/publico/agendas/{agenda_id}")
def pub_obter_agenda(agenda_id: int):
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, nome, descricao, instrucoes, cor, tipo, slot_duracao_min "
            "FROM atend_agendas WHERE id=%s AND ativo=1", (agenda_id,))
        ag = cursor.fetchone()
        if not ag:
            raise HTTPException(status_code=404, detail="Agenda nao encontrada")
        cursor.execute(
            "SELECT id, nome, duracao_min FROM atend_servicos "
            "WHERE agenda_id=%s AND ativo=1 ORDER BY ordem, nome", (agenda_id,))
        ag["servicos"] = cursor.fetchall()
        return {"success": True, "agenda": ag}
    finally:
        cursor.close()
        conn.close()


@router.get("/publico/servicos/{servico_id}/equipamentos")
def pub_equipamentos(servico_id: int):
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, nome FROM atend_equipamentos "
            "WHERE servico_id=%s AND ativo=1 ORDER BY ordem, nome", (servico_id,))
        return {"success": True, "equipamentos": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@router.get("/publico/vendedores")
def pub_vendedores():
    return {"success": True, "vendedores": _query_vendedores()}


def _contexto_agenda_servico(cursor, agenda_id: int, servico_id: int):
    """Carrega agenda ativa + servico ativo + faixas de horario."""
    cursor.execute("SELECT * FROM atend_agendas WHERE id=%s AND ativo=1", (agenda_id,))
    agenda = cursor.fetchone()
    if not agenda:
        raise HTTPException(status_code=404, detail="Agenda nao encontrada")
    cursor.execute("SELECT * FROM atend_servicos WHERE id=%s AND ativo=1", (servico_id,))
    servico = cursor.fetchone()
    if not servico or servico["agenda_id"] != agenda_id:
        raise HTTPException(status_code=404, detail="Servico nao encontrado nessa agenda")
    cursor.execute("SELECT * FROM atend_horarios WHERE agenda_id=%s", (agenda_id,))
    horarios = cursor.fetchall()
    return agenda, servico, horarios


@router.get("/publico/agendas/{agenda_id}/dias")
def pub_dias_disponiveis(agenda_id: int, servico_id: int, modalidade: str = None):
    """Dias com pelo menos um horario livre para o servico na modalidade
    escolhida, nos proximos `_DIAS_BUSCA_PUBLICA` dias."""
    if modalidade not in ("presencial", "online"):
        modalidade = None
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        agenda, servico, horarios = _contexto_agenda_servico(cursor, agenda_id, servico_id)
        agora = datetime.now()
        hoje = agora.date()
        fim_janela = datetime.combine(hoje + timedelta(days=_DIAS_BUSCA_PUBLICA), _time())
        ags, blqs = _eventos_periodo(cursor, agenda_id,
                                     datetime.combine(hoje, _time()), fim_janela)
        feriados = _feriados_set(cursor, agenda_id, hoje,
                                 hoje + timedelta(days=_DIAS_BUSCA_PUBLICA))
        dur = servico["duracao_min"]
        cap_p, cap_o = servico["cap_presencial"], servico["cap_online"]
        dias = []
        for i in range(_DIAS_BUSCA_PUBLICA):
            d = hoje + timedelta(days=i)
            if str(d) in feriados:        # feriado trava o dia inteiro
                continue
            total = 0
            livres = 0
            for ini in _gerar_horarios(agenda, horarios, d, dur):
                if ini < agora:
                    continue
                total += 1
                if _slot_tem_vaga(ags, blqs, servico_id, cap_p, cap_o,
                                  ini, ini + timedelta(minutes=dur), modalidade):
                    livres += 1
            # devolve todo dia que tem horario de funcionamento (mesmo lotado),
            # para o calendario poder marcar o dia cheio em vermelho
            if total:
                dias.append({"data": str(d), "total": total, "livres": livres})
        return {"success": True, "dias": dias}
    finally:
        cursor.close()
        conn.close()


@router.get("/publico/agendas/{agenda_id}/horarios")
def pub_horarios_disponiveis(agenda_id: int, servico_id: int, data: str,
                             modalidade: str = None):
    """Horarios de inicio do servico numa data, com a flag de disponibilidade
    para a modalidade escolhida."""
    if modalidade not in ("presencial", "online"):
        modalidade = None
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        agenda, servico, horarios = _contexto_agenda_servico(cursor, agenda_id, servico_id)
        dia = _parse_date(data)
        if _eh_feriado(cursor, agenda_id, dia):
            return {"success": True, "duracao_min": servico["duracao_min"],
                    "horarios": [], "feriado": True}
        agora = datetime.now()
        dur = servico["duracao_min"]
        cap_p, cap_o = servico["cap_presencial"], servico["cap_online"]
        ags, blqs = _eventos_periodo(cursor, agenda_id,
                                     datetime.combine(dia, _time()),
                                     datetime.combine(dia + timedelta(days=1), _time()))
        # Devolve TODOS os horarios futuros do dia com a flag `disponivel`.
        # disponivel = ha vaga em pelo menos uma modalidade. Nenhum dado do
        # cliente que ocupou e exposto.
        slots = []
        for ini in _gerar_horarios(agenda, horarios, dia, dur):
            if ini < agora:
                continue
            fim = ini + timedelta(minutes=dur)
            slots.append({
                "inicio": ini.strftime("%Y-%m-%d %H:%M"),
                "fim": fim.strftime("%Y-%m-%d %H:%M"),
                "label": ini.strftime("%H:%M"),
                "disponivel": _slot_tem_vaga(ags, blqs, servico_id,
                                             cap_p, cap_o, ini, fim, modalidade),
            })
        return {"success": True, "duracao_min": dur, "horarios": slots}
    finally:
        cursor.close()
        conn.close()


@router.post("/publico/agendar")
def pub_agendar(data: dict):
    """Cria o agendamento feito pelo cliente. Entra como 'pendente'."""
    agenda_id = data.get("agenda_id")
    servico_id = data.get("servico_id")
    if not agenda_id or not servico_id:
        raise HTTPException(status_code=400, detail="Selecione a agenda e o servico")
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
        agenda, servico, horarios = _contexto_agenda_servico(cursor, agenda_id, servico_id)
        dur = servico["duracao_min"]
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
        # valida capacidade do curso para a modalidade escolhida
        erro = _checar_vaga(cursor, agenda_id, servico_id, modalidade, inicio, fim)
        if erro:
            raise HTTPException(status_code=409, detail=erro + " Escolha outro horario.")

        # equipamento (se informado) precisa pertencer ao servico
        equipamento_id = data.get("equipamento_id") or None
        if equipamento_id:
            cursor.execute("SELECT id FROM atend_equipamentos "
                           "WHERE id=%s AND servico_id=%s", (equipamento_id, servico_id))
            if not cursor.fetchone():
                raise HTTPException(status_code=400,
                                    detail="Equipamento invalido para esse servico")
        # vendedor (se informado) precisa ser do grupo Comercial
        vendedor_id = data.get("vendedor_id") or None
        if vendedor_id and not any(v["id"] == int(vendedor_id) for v in _query_vendedores()):
            raise HTTPException(status_code=400, detail="Vendedor invalido")

        novo = _gravar_agendamento(cursor, agenda_id, {
            "servico_id": servico_id,
            "equipamento_id": equipamento_id,
            "titulo": servico["nome"],
            "cliente_nome": nome,
            "cliente_email": email,
            "cliente_telefone": telefone,
            "observacoes": (data.get("observacoes") or "").strip() or None,
            "modalidade": data.get("modalidade") if data.get("modalidade") in
                ("presencial", "online") else None,
            "tipo_negocio": data.get("tipo_negocio") if data.get("tipo_negocio") in
                ("locacao", "venda") else None,
            "vendedor_id": vendedor_id,
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
