/* ============================================================
   MÓDULO AGENDA — agenda.js
   Integração com Carbonio (FASE 1: login + listar)
   ============================================================ */

const $ = (id) => document.getElementById(id);

const API_HOST = (typeof API_BASE_URL !== 'undefined' ? API_BASE_URL
  : `http://${window.location.hostname || '127.0.0.1'}:8000`);

const API = {
  status:        API_HOST + '/api/agenda/status',
  login:         API_HOST + '/api/agenda/login',
  logout:        API_HOST + '/api/agenda/logout',
  eventos:       API_HOST + '/api/agenda/eventos',          // GET lista | POST cria
  detalhes:      (id) => `${API_HOST}/api/agenda/eventos/${encodeURIComponent(id)}/detalhes`,
  reenviar:      (id) => `${API_HOST}/api/agenda/eventos/${encodeURIComponent(id)}/reenviar`,
  notificacoes:  API_HOST + '/api/notificacoes',
};

let currentUser = null;
let calendar    = null;
let _eventosCache = [];   // cache da última busca

/* =============================================================
   UTILS
   ============================================================= */
function escHtml(s) {
  if (s === null || s === undefined) return '';
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

function toast(msg, tipo = 'info') {
  const wrap = $('agendaToast');
  if (!wrap) return alert(msg);
  const el = document.createElement('div');
  el.className = 'agenda-toast-item ' + tipo;
  el.innerHTML = msg;
  wrap.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; }, 4000);
  setTimeout(() => el.remove(), 4500);
}

function dtPt(d) {
  if (!d) return '—';
  const date = (d instanceof Date) ? d : new Date(d);
  if (isNaN(date)) return String(d);
  const pad = n => String(n).padStart(2, '0');
  return `${pad(date.getDate())}/${pad(date.getMonth()+1)}/${date.getFullYear()}, ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function fmtHora(d) {
  if (!d) return '';
  const date = (d instanceof Date) ? d : new Date(d);
  if (isNaN(date)) return '';
  const pad = n => String(n).padStart(2, '0');
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function diaIso(d) {
  // YYYY-MM-DD do dia local
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
}

function nomeDia(d) {
  const dias = ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira',
                'Quinta-feira', 'Sexta-feira', 'Sábado'];
  return dias[d.getDay()];
}

function showSection(sec) {
  document.querySelectorAll('.agenda-page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.agenda-nav-item').forEach(i => i.classList.remove('active'));
  $('page-' + sec).classList.add('active');
  document.querySelector(`.agenda-nav-item[data-section="${sec}"]`)?.classList.add('active');
  $('topbarTitle').textContent = sec === 'calendario' ? 'Calendário' : 'Próximos 7 dias';

  if (sec === 'proximos') renderProximos();
  if (sec === 'calendario' && calendar) calendar.render();
}

/* =============================================================
   BOOTSTRAP DO MÓDULO
   ============================================================= */
async function bootAgenda() {
  // Pega usuário logado do localStorage (mesmo padrão do nav.js)
  try {
    currentUser = JSON.parse(localStorage.getItem('cpe_user') || 'null');
  } catch (_) { currentUser = null; }

  if (!currentUser || !currentUser.id) {
    window.location.href = '/SistemaCPE/web/login.html';
    return;
  }

  $('topbarUser').textContent = currentUser.name || currentUser.email || '';

  // Mostra a aplicação ANTES de verificar status — assim o modal renderiza
  // por cima do layout, em vez de por cima da tela de loading (z-index 9999).
  $('agendaLoading').style.display = 'none';
  $('agendaApp').style.display     = 'flex';

  // Sino de notificações começa a polar imediatamente
  iniciarSino();

  // Verifica se já está conectado. Só inicializa o calendário se sim;
  // caso contrário, abre o modal de login e espera o usuário se conectar.
  const conectado = await verificarStatusCarbonio();
  if (conectado) {
    initCalendar();
  } else {
    abrirModalLogin();
  }
}

async function verificarStatusCarbonio() {
  try {
    const r = await fetch(`${API.status}?usuario_id=${currentUser.id}`);
    const data = await r.json();
    if (data.conectado) {
      $('agendaConnInfo').style.display = '';
      $('agendaConnEmail').textContent  = data.email || '';
      return true;
    }
    $('agendaConnInfo').style.display = 'none';
    return false;
  } catch (err) {
    console.error('[AGENDA/STATUS]', err);
    toast('Erro ao verificar conexão Carbonio: ' + err.message, 'error');
    return false;
  }
}

/* Limpa backdrops "fantasma" que possam ter ficado de instâncias antigas */
function limparBackdropsModal() {
  document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
  document.body.classList.remove('modal-open');
  document.body.style.overflow = '';
  document.body.style.paddingRight = '';
}

/* =============================================================
   LOGIN CARBONIO
   ============================================================= */
function abrirModalLogin() {
  // Se o modal já está aberto, não abre de novo (evita backdrop duplicado)
  const modalEl = $('loginCarbonioModal');
  if (modalEl.classList.contains('show')) return;

  $('loginErr').classList.add('d-none');
  $('loginEmail').value = currentUser.email || '';
  $('loginSenha').value = '';

  // getOrCreateInstance reutiliza a mesma instância em chamadas repetidas
  bootstrap.Modal.getOrCreateInstance(modalEl).show();
  setTimeout(() => $('loginSenha').focus(), 300);
}

function cancelarLogin() {
  bootstrap.Modal.getInstance($('loginCarbonioModal'))?.hide();
  limparBackdropsModal();
  // Volta para o sistema (não tem como usar a agenda sem token)
  window.location.href = '/SistemaCPE/index.html';
}

async function submitLoginCarbonio() {
  const erro = $('loginErr');
  erro.classList.add('d-none');

  const email = $('loginEmail').value.trim();
  const senha = $('loginSenha').value;
  if (!email || !senha) {
    erro.textContent = 'Preencha email e senha.';
    erro.classList.remove('d-none');
    return;
  }

  const btn = $('btnLoginCarbonio');
  const txt = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Conectando...';

  try {
    const r = await fetch(API.login, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        usuario_id: currentUser.id,
        email,
        senha,
      }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || 'HTTP ' + r.status);

    bootstrap.Modal.getInstance($('loginCarbonioModal'))?.hide();
    // Garantia extra: limpa qualquer backdrop fantasma
    limparBackdropsModal();

    $('agendaConnInfo').style.display = '';
    $('agendaConnEmail').textContent  = data.email;
    toast('Conectado a ' + data.email, 'success');

    if (!calendar) {
      initCalendar();
    } else {
      calendar.refetchEvents();
    }
  } catch (err) {
    erro.textContent = err.message;
    erro.classList.remove('d-none');
  } finally {
    btn.disabled = false;
    btn.innerHTML = txt;
  }
}

async function logoutCarbonio() {
  if (!confirm('Desconectar sua agenda Carbonio?')) return;
  try {
    await fetch(API.logout, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ usuario_id: currentUser.id }),
    });
    $('agendaConnInfo').style.display = 'none';
    if (calendar) {
      calendar.removeAllEvents();
      calendar.refetchEvents();
    }
    abrirModalLogin();
  } catch (err) {
    toast('Erro: ' + err.message, 'error');
  }
}

/* =============================================================
   CALENDÁRIO
   ============================================================= */
function statusToClass(status) {
  return 'evt-' + (status || 'tentativo');
}

function initCalendar() {
  const el = $('calendar');
  calendar = new FullCalendar.Calendar(el, {
    locale: 'pt-br',
    initialView: 'timeGridWeek',
    firstDay: 0,
    headerToolbar: {
      left:   'prev,next today',
      center: 'title',
      right:  'dayGridMonth,timeGridWeek,timeGridDay,listWeek',
    },
    buttonText: {
      today: 'Hoje', month: 'Mês', week: 'Semana', day: 'Dia', list: 'Agenda',
    },
    allDayText: 'Dia todo',
    moreLinkText: n => `+${n} mais`,
    noEventsText: 'Nenhum compromisso no período',
    height: 720,
    nowIndicator: true,
    slotMinTime: '07:00:00',
    slotMaxTime: '22:00:00',
    selectable: true,
    selectMirror: true,
    select(info) {
      // Clicar/arrastar num horário vazio abre o modal já preenchido
      abrirNovoEvento(info.start, info.end);
    },
    eventClick(info) {
      abrirDetalheEvento(info.event.extendedProps.evento);
    },
    events: fetchEventos,
  });
  calendar.render();
}

async function fetchEventos(fetchInfo, success, failure) {
  try {
    const params = new URLSearchParams({
      usuario_id: currentUser.id,
      inicio:     fetchInfo.startStr,
      fim:        fetchInfo.endStr,
    });
    const r = await fetch(`${API.eventos}?${params}`);
    if (r.status === 401) {
      const j = await r.json().catch(() => ({}));
      console.warn('[AGENDA/EVENTOS] 401:', j.detail);
      toast(j.detail || 'Sessão Carbonio expirou — faça login novamente.', 'warn');
      $('agendaConnInfo').style.display = 'none';
      // Devolve lista vazia e abre modal (se ainda não estiver aberto)
      success([]);
      abrirModalLogin();
      return;
    }
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.detail || 'HTTP ' + r.status);
    }
    const data = await r.json();
    _eventosCache = data.eventos || [];

    const events = _eventosCache.map(ev => ({
      id:    String(ev.id),
      title: ev.titulo,
      start: new Date(ev.inicio_ms),
      end:   new Date(ev.fim_ms),
      allDay: ev.all_day,
      classNames: [statusToClass(ev.status)],
      extendedProps: { evento: ev },
    }));
    success(events);
    renderProximos();
  } catch (err) {
    console.error('[AGENDA/EVENTOS]', err);
    toast('Erro ao buscar eventos: ' + err.message, 'error');
    failure(err);
  }
}

function recarregarEventos() {
  if (calendar) calendar.refetchEvents();
}

/* =============================================================
   LISTA "PRÓXIMOS 7 DIAS"
   ============================================================= */
function renderProximos() {
  const lista = $('listaProximos');
  if (!lista) return;

  const agora = new Date();
  const limite = new Date();
  limite.setDate(agora.getDate() + 7);

  // Filtra do cache: só eventos ativos no intervalo dos próximos 7 dias
  const proximos = _eventosCache
    .filter(ev => {
      const fim = new Date(ev.fim_ms);
      const ini = new Date(ev.inicio_ms);
      return fim >= agora && ini <= limite;
    })
    .sort((a, b) => a.inicio_ms - b.inicio_ms);

  if (!proximos.length) {
    lista.innerHTML = `
      <div class="agenda-empty">
        <i class="bi bi-calendar2-x"></i>
        <p>Nenhum compromisso nos próximos 7 dias.</p>
      </div>`;
    return;
  }

  // Agrupa por dia
  const grupos = {};
  proximos.forEach(ev => {
    const d = new Date(ev.inicio_ms);
    const chave = diaIso(d);
    if (!grupos[chave]) grupos[chave] = { data: d, items: [] };
    grupos[chave].items.push(ev);
  });

  const partes = [];
  Object.values(grupos).forEach(g => {
    const isHoje    = diaIso(g.data) === diaIso(agora);
    const titulo    = isHoje ? 'Hoje' : nomeDia(g.data);
    const dataPt    = `${String(g.data.getDate()).padStart(2,'0')}/${String(g.data.getMonth()+1).padStart(2,'0')}`;
    partes.push(`<div class="agenda-list-day">${titulo} — ${dataPt}</div>`);
    g.items.forEach(ev => {
      partes.push(`
        <div class="agenda-list-item" onclick='abrirDetalheEvento(${JSON.stringify(ev).replace(/'/g, "&#39;")})'>
          <div class="agenda-list-time">
            <div class="hora">${fmtHora(ev.inicio_ms)}</div>
            <div class="ate">até ${fmtHora(ev.fim_ms)}</div>
          </div>
          <div class="agenda-list-info">
            <div class="titulo">${escHtml(ev.titulo)}</div>
            <div class="meta">
              ${ev.local ? `<span><i class="bi bi-geo-alt"></i>${escHtml(ev.local)}</span>` : ''}
              ${ev.organizador_nome ? `<span><i class="bi bi-person"></i>${escHtml(ev.organizador_nome)}</span>` : ''}
            </div>
          </div>
          <span class="agenda-list-status ${ev.status}">${ev.status}</span>
        </div>`);
    });
  });

  lista.innerHTML = partes.join('');
}

/* =============================================================
   MODAL DE DETALHES
   ============================================================= */
async function abrirDetalheEvento(ev) {
  if (!ev) return;
  const corpo = $('eventoDetalheCorpo');

  // Renderização inicial com dados básicos + spinner para os convidados
  const renderBasico = (extra = '') => `
    <h5>${escHtml(ev.titulo)}</h5>
    <hr>
    <p><i class="bi bi-calendar"></i> <strong>Início:</strong> ${dtPt(ev.inicio_ms)}</p>
    <p><i class="bi bi-calendar-check"></i> <strong>Fim:</strong> ${dtPt(ev.fim_ms)}</p>
    ${ev.local ? `<p><i class="bi bi-geo-alt"></i> <strong>Local:</strong> ${escHtml(ev.local)}</p>` : ''}
    ${ev.organizador_nome ? `<p><i class="bi bi-person"></i> <strong>Organizador:</strong> ${escHtml(ev.organizador_nome)}${ev.organizador_email ? ' &lt;' + escHtml(ev.organizador_email) + '&gt;' : ''}</p>` : ''}
    <p>
      <span class="agenda-list-status ${ev.status}" style="font-size:11px">${ev.status}</span>
      <small class="text-muted ms-2">via Carbonio</small>
    </p>
    ${extra}`;

  corpo.innerHTML = renderBasico(`
    <hr>
    <p class="text-muted small">
      <i class="bi bi-hourglass-split"></i> Carregando convidados...
    </p>`);
  bootstrap.Modal.getOrCreateInstance($('eventoDetalhe')).show();

  // Lazy-load: busca detalhes completos (com lista de convidados e RSVPs)
  if (!ev.id) return;
  try {
    const r = await fetch(`${API.detalhes(ev.id)}?usuario_id=${currentUser.id}`);
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.detail || 'HTTP ' + r.status);
    }
    const det = await r.json();
    const convidados = det.convidados || [];

    let secaoConvidados;
    if (convidados.length === 0) {
      secaoConvidados = `<p class="text-muted small"><i class="bi bi-people"></i> Sem convidados.</p>`;
    } else {
      const pendentes = convidados
        .filter(c => c.status === 'pendente' || c.status === 'tentativo')
        .map(c => c.email);

      const linhas = convidados.map(c => `
        <div class="evt-attendee">
          <div class="info">
            <div class="nome">${escHtml(c.nome || c.email)}</div>
            <div class="email">${escHtml(c.email)} • ${escHtml(c.role)}</div>
          </div>
          <span class="badge-rsvp ${c.status}">${c.status}</span>
          ${c.status === 'pendente' || c.status === 'tentativo'
            ? `<button class="btn-reenviar" onclick="reenviarConviteUm('${ev.id}', '${escHtml(c.email)}')" title="Reenviar convite a este convidado">
                 <i class="bi bi-arrow-clockwise"></i>
               </button>` : ''}
        </div>`).join('');

      const btnReenviarTodos = pendentes.length > 0
        ? `<button class="btn-agenda btn-agenda-secondary mt-2"
                   onclick='reenviarParaTodos("${ev.id}", ${JSON.stringify(pendentes)})'>
             <i class="bi bi-send"></i> Reenviar a todos os pendentes (${pendentes.length})
           </button>`
        : '';

      secaoConvidados = `
        <h6 class="mt-3"><i class="bi bi-people-fill"></i> Convidados (${convidados.length})</h6>
        <div class="evt-attendees">${linhas}</div>
        ${btnReenviarTodos}`;
    }

    const desc = det.descricao
      ? `<hr><p style="white-space:pre-wrap;font-size:.9rem;color:#374151">${escHtml(det.descricao)}</p>`
      : '';
    corpo.innerHTML = renderBasico(desc + '<hr>' + secaoConvidados);
  } catch (err) {
    corpo.innerHTML = renderBasico(`
      <hr>
      <p class="text-danger small"><i class="bi bi-exclamation-triangle"></i> Falha ao carregar convidados: ${escHtml(err.message)}</p>`);
  }
}

async function reenviarConviteUm(eventoId, email) {
  if (!confirm(`Reenviar convite para ${email}?`)) return;
  try {
    const r = await fetch(API.reenviar(eventoId), {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        usuario_id:    currentUser.id,
        destinatarios: [email],
      }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || 'HTTP ' + r.status);
    toast(`Convite reenviado para ${email}`, 'success');
  } catch (err) {
    toast('Erro ao reenviar: ' + err.message, 'error');
  }
}

async function reenviarParaTodos(eventoId, emails) {
  if (!emails || !emails.length) return;
  if (!confirm(`Reenviar convite para ${emails.length} pessoa(s) pendente(s)?`)) return;
  try {
    const r = await fetch(API.reenviar(eventoId), {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        usuario_id:    currentUser.id,
        destinatarios: emails,
      }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || 'HTTP ' + r.status);
    toast(`Convite reenviado para ${emails.length} pessoa(s)`, 'success');
  } catch (err) {
    toast('Erro ao reenviar: ' + err.message, 'error');
  }
}

/* =============================================================
   NOVO COMPROMISSO (Fase 2 — criar evento no Carbonio)
   ============================================================= */
function _toLocalInput(d) {
  // converte Date → 'YYYY-MM-DDTHH:MM' (formato do <input type="datetime-local">)
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function _toIsoComTimezone(localStr) {
  // 'YYYY-MM-DDTHH:MM' (local) → ISO 8601 com offset
  // Ex: '2026-05-05T14:00' → '2026-05-05T14:00:00-03:00'
  if (!localStr) return null;
  const dt = new Date(localStr);
  if (isNaN(dt)) return null;
  const offMin = -dt.getTimezoneOffset();
  const sign = offMin >= 0 ? '+' : '-';
  const abs = Math.abs(offMin);
  const offH = String(Math.floor(abs / 60)).padStart(2, '0');
  const offM = String(abs % 60).padStart(2, '0');
  return localStr + `:00${sign}${offH}:${offM}`;
}

function abrirNovoEvento(inicioPrefill = null, fimPrefill = null) {
  $('novoEventoErr').classList.add('d-none');
  $('evtTitulo').value     = '';
  $('evtLocal').value      = '';
  $('evtDescricao').value  = '';
  $('evtConvidados').value = '';

  // Default: agora + 1h, com duração de 1h
  const ini = inicioPrefill instanceof Date ? inicioPrefill : new Date(Date.now() + 60 * 60 * 1000);
  // Arredonda os minutos para baixo para o múltiplo de 15
  ini.setMinutes(Math.floor(ini.getMinutes() / 15) * 15, 0, 0);
  const fim = fimPrefill instanceof Date && fimPrefill > ini
    ? fimPrefill
    : new Date(ini.getTime() + 60 * 60 * 1000);

  $('evtInicio').value = _toLocalInput(ini);
  $('evtFim').value    = _toLocalInput(fim);

  bootstrap.Modal.getOrCreateInstance($('novoEventoModal')).show();
  setTimeout(() => $('evtTitulo').focus(), 300);
}

async function submitNovoEvento() {
  const erro = $('novoEventoErr');
  erro.classList.add('d-none');

  const titulo = $('evtTitulo').value.trim();
  const ini    = $('evtInicio').value;
  const fim    = $('evtFim').value;
  const local  = $('evtLocal').value.trim();
  const desc   = $('evtDescricao').value.trim();
  const convidadosRaw = $('evtConvidados').value.trim();

  if (!titulo) {
    erro.textContent = 'Informe o título do compromisso.';
    erro.classList.remove('d-none'); return;
  }
  if (!ini || !fim) {
    erro.textContent = 'Informe início e fim.';
    erro.classList.remove('d-none'); return;
  }
  if (new Date(fim) <= new Date(ini)) {
    erro.textContent = 'O fim deve ser depois do início.';
    erro.classList.remove('d-none'); return;
  }

  // Parse de convidados — divide por vírgula/ponto-e-vírgula/espaço, valida @
  const convidados = convidadosRaw
    .split(/[,;\s]+/)
    .map(s => s.trim())
    .filter(s => s.length > 0);
  for (const c of convidados) {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(c)) {
      erro.textContent = `Email de convidado inválido: ${c}`;
      erro.classList.remove('d-none'); return;
    }
  }

  const btn = $('btnSalvarEvento');
  const txt = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Criando...';

  try {
    const r = await fetch(API.eventos, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        usuario_id: currentUser.id,
        titulo,
        inicio:     _toIsoComTimezone(ini),
        fim:        _toIsoComTimezone(fim),
        local:      local || null,
        descricao:  desc  || null,
        convidados,
        all_day:    false,
      }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || 'HTTP ' + r.status);

    bootstrap.Modal.getInstance($('novoEventoModal'))?.hide();
    limparBackdropsModal();

    const msg = convidados.length
      ? `Compromisso criado e convite enviado a ${convidados.length} pessoa(s).`
      : 'Compromisso criado na sua agenda.';
    toast(msg, 'success');

    if (calendar) calendar.refetchEvents();
  } catch (err) {
    erro.textContent = err.message;
    erro.classList.remove('d-none');
  } finally {
    btn.disabled = false;
    btn.innerHTML = txt;
  }
}

/* =============================================================
   SINO DE NOTIFICAÇÕES (lembretes da agenda + outras)
   ============================================================= */
let _notifs = [];
let _notifTimer = null;

const ICONES_NOTIF = {
  lembrete_agenda:        '🔔',
  convite_reuniao:        '📅',
  convite_aceito_reuniao: '✅',
  convite_recusado_reuniao: '❌',
  confirmar_reserva:      '📆',
  ticket_criado:          '🎫',
  nova_resposta:          '💬',
  status_alterado:        '🔄',
  atribuido:              '👤',
  info: 'ℹ️', aviso: '⚠️', erro: '❌', sucesso: '✅',
};

async function carregarNotifs() {
  if (!currentUser?.id) return;
  try {
    const r = await fetch(`${API.notificacoes}/usuario/${currentUser.id}?limite=20`);
    if (!r.ok) return;
    const data = await r.json();
    _notifs = Array.isArray(data) ? data : (data.notificacoes || []);
    renderSino();
  } catch (err) {
    console.warn('[AGENDA/SINO]', err);
  }
}

function renderSino() {
  const naoLidas = _notifs.filter(n => !n.lido).length;
  const badge = $('sinoBadge');
  if (naoLidas > 0) {
    badge.style.display = 'flex';
    badge.textContent   = naoLidas > 9 ? '9+' : String(naoLidas);
  } else {
    badge.style.display = 'none';
  }

  const lista = $('sinoLista');
  if (_notifs.length === 0) {
    lista.innerHTML = `
      <div class="sino-empty">
        <i class="bi bi-inbox" style="font-size:24px;display:block;margin-bottom:6px"></i>
        Nenhuma notificação.
      </div>`;
    return;
  }
  const ordenadas = [..._notifs].sort((a, b) =>
    new Date(b.created_at) - new Date(a.created_at));
  lista.innerHTML = ordenadas.slice(0, 15).map(n => `
    <div class="sino-item ${n.lido ? '' : 'unread'}"
         onclick="clicarNotif(${n.id}, '${escHtml(n.tipo)}')">
      <div class="icone">${ICONES_NOTIF[n.tipo] || '📬'}</div>
      <div class="conteudo">
        <div class="msg">${escHtml(n.mensagem)}</div>
        <div class="meta">${formatarTempo(n.created_at)}</div>
      </div>
    </div>`).join('');
}

function formatarTempo(dataStr) {
  try {
    const d = new Date(dataStr);
    const diff = (new Date() - d) / 60000; // min
    if (diff < 1) return 'agora mesmo';
    if (diff < 60) return Math.floor(diff) + ' min atrás';
    if (diff < 1440) return Math.floor(diff / 60) + 'h atrás';
    return Math.floor(diff / 1440) + 'd atrás';
  } catch (_) { return ''; }
}

function toggleSinoPanel(e) {
  if (e) e.stopPropagation();
  const panel = $('sinoPanel');
  panel.classList.toggle('show');
  if (panel.classList.contains('show')) {
    // Marca todas como lidas ao abrir
    marcarTodasLidas();
  }
}

async function clicarNotif(id, tipo) {
  // Marca como lida
  if (id > 0) {
    try {
      await fetch(`${API.notificacoes}/${id}?usuario_id=${currentUser.id}`, {
        method:  'PUT',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ lido: true }),
      });
    } catch (_) {}
  }
  // Lembretes de agenda já estão na agenda; outras vão pra outras telas
  if (tipo === 'lembrete_agenda' || tipo === 'confirmar_reserva') {
    $('sinoPanel').classList.remove('show');
    await carregarNotifs();
    return;
  }
  // Outros tipos podem redirecionar (recepção, tickets, etc)
  if (tipo && tipo.includes('reuniao')) {
    window.location.href = '/SistemaCPE/web/pages/recepcao.html';
  }
}

async function marcarTodasLidas() {
  const naoLidas = _notifs.filter(n => !n.lido && n.id > 0);
  if (!naoLidas.length) return;
  await Promise.all(naoLidas.map(n =>
    fetch(`${API.notificacoes}/${n.id}?usuario_id=${currentUser.id}`, {
      method:  'PUT',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ lido: true }),
    }).catch(() => {})
  ));
  await carregarNotifs();
}

async function limparNotifsLidas(e) {
  if (e) e.stopPropagation();
  try {
    const r = await fetch(
      `${API.notificacoes}/limpador/lidas?usuario_id=${currentUser.id}`,
      { method: 'DELETE' }
    );
    if (r.ok) {
      const j = await r.json();
      toast(`${j.total_deletadas || 0} notificação(ões) removida(s)`, 'success');
      await carregarNotifs();
    }
  } catch (err) {
    toast('Erro ao limpar: ' + err.message, 'error');
  }
}

function iniciarSino() {
  carregarNotifs();
  if (_notifTimer) clearInterval(_notifTimer);
  _notifTimer = setInterval(carregarNotifs, 30000);  // refresh a cada 30s

  // Fecha o painel ao clicar fora
  document.addEventListener('click', e => {
    const panel = $('sinoPanel');
    const wrap  = $('sinoWrap');
    if (panel?.classList.contains('show') &&
        !panel.contains(e.target) && !wrap.contains(e.target)) {
      panel.classList.remove('show');
    }
  });
}

/* =============================================================
   SIDEBAR TOGGLE
   ============================================================= */
function toggleSidebar() {
  const sb = $('agendaSidebar');
  const ct = $('agendaContent');
  const ic = $('sidebarToggleIcon');
  sb.classList.toggle('collapsed');
  ct.classList.toggle('sidebar-collapsed');
  if (ic) {
    const collapsed = sb.classList.contains('collapsed');
    ic.className = collapsed ? 'bi bi-layout-sidebar' : 'bi bi-layout-sidebar-reverse';
  }
}

/* Expõe globais (onclicks inline) */
window.showSection         = showSection;
window.toggleSidebar       = toggleSidebar;
window.submitLoginCarbonio = submitLoginCarbonio;
window.cancelarLogin       = cancelarLogin;
window.logoutCarbonio      = logoutCarbonio;
window.recarregarEventos   = recarregarEventos;
window.abrirDetalheEvento  = abrirDetalheEvento;
window.abrirNovoEvento     = abrirNovoEvento;
window.submitNovoEvento    = submitNovoEvento;
window.toggleSinoPanel     = toggleSinoPanel;
window.clicarNotif         = clicarNotif;
window.limparNotifsLidas   = limparNotifsLidas;
window.reenviarConviteUm   = reenviarConviteUm;
window.reenviarParaTodos   = reenviarParaTodos;

document.addEventListener('DOMContentLoaded', bootAgenda);
