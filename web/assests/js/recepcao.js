/* ============================================================
   MÓDULO DE RECEPÇÃO — recepcao.js
   CPE Tecnologia
   ============================================================ */

console.log("[RECEP] iniciando...");

const API_HOST = (typeof API_BASE_URL !== 'undefined'
  ? API_BASE_URL
  : `http://${window.location.hostname || '127.0.0.1'}:8000`);

const API = {
  base:        API_HOST + '/api',
  unidades:    API_HOST + '/api/unidades',
  salas:       API_HOST + '/api/recepcao/salas',
  reservas:    API_HOST + '/api/recepcao/reservas',
  envios:      API_HOST + '/api/recepcao/envios',
  eventos:     API_HOST + '/api/recepcao/eventos',
  users:       API_HOST + '/api/users',
  convites:    API_HOST + '/api/recepcao/convites',
  escritorios: API_HOST + '/api/recepcao/escritorios',
};

let currentUser  = null;
let unidades     = [];
let escritorios  = [];     // todos os escritórios cadastrados
let salas        = [];
let envios       = [];
let usuariosAtivos = [];   // para multi-select de convidados
let calendar     = null;
let editandoSala     = null;
let editandoEnvio    = null;

// Helpers para trabalhar com escritórios por unidade
function escritoriosDaUnidade(unitId) {
  if (!unitId) return [];
  return escritorios.filter(e => e.ativo && String(e.unit_id) === String(unitId));
}
function unidadeTemEscritorios(unitId) {
  return escritoriosDaUnidade(unitId).length > 0;
}

const ROLES_GERENCIAM_SALA = new Set(['ADMIN', 'TI', 'MANAGER', 'RESPONSAVEL_GRUPO']);

/* ============================================================
   HELPERS
   ============================================================ */
function $(id)         { return document.getElementById(id); }
function escHtml(s)    { return (s || '').replace(/[&<>"']/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c])); }

function podeGerenciarSala() {
  return currentUser && ROLES_GERENCIAM_SALA.has(currentUser.role);
}

function toast(msg, tipo = 'info') {
  const wrap = $('recepToast');
  if (!wrap) return alert(msg);
  const el = document.createElement('div');
  el.className = 'recep-toast-item ' + tipo;
  el.innerHTML = msg;
  wrap.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; }, 4000);
  setTimeout(() => el.remove(), 4500);
}

function dtIso(v) {
  // converte "2026-04-30T14:00" -> "2026-04-30T14:00:00"
  if (!v) return null;
  return v.length === 16 ? v + ':00' : v;
}

function dtPt(v) {
  if (!v) return '—';
  const d = new Date(v);
  if (isNaN(d.getTime())) return v;
  return d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}

function brl(n) {
  const v = parseFloat(n) || 0;
  return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

/* ============================================================
   AUTH / BOOTSTRAP
   ============================================================ */
function loadCurrentUser() {
  const raw = localStorage.getItem('cpe_user');
  if (!raw) {
    window.location.href = '/SistemaCPE/web/login.html';
    return null;
  }
  try { return JSON.parse(raw); }
  catch { window.location.href = '/SistemaCPE/web/login.html'; return null; }
}

// Renomeada de "bootstrap" para "bootRecepcao" — o nome anterior conflitava
// com o objeto global `bootstrap` do framework Bootstrap (bootstrap.Modal etc).
async function bootRecepcao() {
  currentUser = loadCurrentUser();
  if (!currentUser) return;

  $('topbarUser').textContent = currentUser.name || '';

  try {
    await loadUnidades();
    await loadEscritorios();
    await loadSalas();
    await loadUsuarios();
    initCalendar();
  } catch (err) {
    console.error('[RECEP] bootRecepcao erro:', err);
    toast('Erro ao carregar dados iniciais: ' + err.message, 'error');
  }

  $('recepLoading').style.display = 'none';
  $('recepApp').style.display     = 'flex';

  if (!podeGerenciarSala()) {
    const btn = $('btnNovaSala');
    if (btn) btn.style.display = 'none';
  }

  // deeplink: ?reserva_id=NN abre o modal de detalhes da reserva
  const params = new URLSearchParams(window.location.search);
  const reservaIdParam = parseInt(params.get('reserva_id'));
  if (reservaIdParam) {
    setTimeout(() => abrirReservaPorId(reservaIdParam), 200);
  }
}

async function loadEscritorios() {
  try {
    const r = await fetch(API.escritorios);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    escritorios = await r.json();
  } catch (err) {
    console.error('[RECEP/ESCRITORIOS]', err);
    escritorios = [];
  }
}

async function loadUsuarios() {
  try {
    const r = await fetch(API.users);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const lista = await r.json();
    usuariosAtivos = (lista || [])
      .filter(u => u.is_active)
      .map(u => ({
        id: u.id,
        nome: u.name || u.username || ('User #' + u.id),
        email: u.email || '',
        username: u.username || '',
      }))
      .sort((a, b) => a.nome.localeCompare(b.nome));
  } catch (err) {
    console.error('[RECEP/USERS]', err);
    usuariosAtivos = [];
  }
}

function filtrarConvidados() {
  const q = ($('resvConvidadosBusca').value || '').toLowerCase().trim();
  const sel = $('resvConvidados');
  // preserva já selecionados
  const selecionados = new Set(Array.from(sel.selectedOptions).map(o => o.value));
  const filtrados = !q ? usuariosAtivos
    : usuariosAtivos.filter(u =>
        u.nome.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q) ||
        u.username.toLowerCase().includes(q));

  sel.innerHTML = filtrados
    .filter(u => u.id !== currentUser.id)        // não convida a si mesmo
    .map(u => {
      const sel_attr = selecionados.has(String(u.id)) ? ' selected' : '';
      const sub = u.email ? ` — ${escHtml(u.email)}` : '';
      return `<option value="${u.id}"${sel_attr}>${escHtml(u.nome)}${sub}</option>`;
    }).join('');
}

document.addEventListener('DOMContentLoaded', bootRecepcao);

/* ============================================================
   NAVEGAÇÃO ENTRE SEÇÕES
   ============================================================ */
function showSection(sec) {
  document.querySelectorAll('.recep-page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.recep-nav-item').forEach(n => n.classList.remove('active'));
  $('page-' + sec).classList.add('active');
  document.querySelector(`.recep-nav-item[data-section="${sec}"]`)?.classList.add('active');

  const titles = {
    calendario: 'Calendário de Reservas',
    salas:      'Salas de Reunião',
    envios:     'Envios de Mercadoria',
  };
  $('topbarTitle').textContent = titles[sec] || '';

  if (sec === 'envios')   loadEnvios();
  if (sec === 'salas')    renderSalas();
  if (sec === 'calendario' && calendar) calendar.refetchEvents();
}

/* ============================================================
   UNIDADES
   ============================================================ */
async function loadUnidades() {
  const r = await fetch(API.unidades + '/?somente_ativas=true');
  if (!r.ok) {
    let detail = '';
    try { detail = (await r.json()).detail || ''; } catch {}
    throw new Error(`HTTP ${r.status} em /api/unidades — ${detail || 'sem detalhe'}`);
  }
  unidades = await r.json();

  const opts = '<option value="">— Selecione —</option>' +
    unidades.map(u =>
      `<option value="${u.id}">${escHtml(u.nome)}${u.sigla ? ' (' + escHtml(u.sigla) + ')' : ''}</option>`
    ).join('');
  const todasOpts = '<option value="">Todas as unidades</option>' +
    unidades.map(u =>
      `<option value="${u.id}">${escHtml(u.nome)}${u.sigla ? ' (' + escHtml(u.sigla) + ')' : ''}</option>`
    ).join('');

  $('resvUnit').innerHTML       = todasOpts;
  $('salaUnit').innerHTML       = opts;
  $('filterUnitCal').innerHTML  = todasOpts;
  $('filterUnitSala').innerHTML = todasOpts;
}

/* ============================================================
   SALAS
   ============================================================ */
async function loadSalas() {
  const unitFilter = $('filterUnitSala')?.value || '';
  const escFilter  = $('filterEscritorioSala')?.value || '';
  const params = new URLSearchParams();
  if (unitFilter) params.set('unit_id', unitFilter);
  if (escFilter)  params.set('escritorio_id', escFilter);
  const url = API.salas + (params.toString() ? '?' + params.toString() : '');
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    salas = await r.json();
    renderSalas();
    populateResvSala();
  } catch (err) {
    console.error('[RECEP/SALAS]', err);
    toast('Erro ao carregar salas: ' + err.message, 'error');
  }
}

function renderSalas() {
  const grid = $('salasGrid');
  if (!grid) return;

  const list = salas;
  if (!list || !list.length) {
    grid.innerHTML = `
      <div class="recep-card" style="grid-column:1/-1;text-align:center;color:#6b7280;">
        <i class="bi bi-door-closed" style="font-size:32px"></i>
        <p style="margin-top:8px">Nenhuma sala cadastrada para os filtros atuais.</p>
        ${podeGerenciarSala() ? '<p style="font-size:13px;color:#9ca3af">Clique em "Nova Sala" para criar a primeira.</p>' : ''}
      </div>`;
    return;
  }

  grid.innerHTML = list.map(s => `
    <div class="recep-room-card">
      <div class="room-color-bar" style="background:${escHtml(s.cor || '#3b82f6')}"></div>
      <span class="room-status-badge ${s.ativa ? 'ativa' : 'inativa'}">
        ${s.ativa ? 'Ativa' : 'Inativa'}
      </span>
      <div class="room-title">
        <i class="bi bi-${s.tipo === 'auditorio' ? 'easel' : 'door-open'}"></i>
        ${escHtml(s.nome)}
      </div>
      <div class="room-meta">
        <span><i class="bi bi-geo-alt"></i> ${escHtml(s.unit_sigla || s.unit_nome || 'Unidade #' + s.unit_id)}</span>
        ${s.escritorio_nome ? `<span><i class="bi bi-building"></i> ${escHtml(s.escritorio_nome)}</span>` : ''}
        ${s.capacidade ? `<span><i class="bi bi-people"></i> ${s.capacidade} pessoas</span>` : ''}
        <span><i class="bi bi-tag"></i> ${s.tipo === 'auditorio' ? 'Auditório' : 'Sala'}</span>
      </div>
      ${s.descricao ? `<div style="font-size:13px;color:#4b5563;margin-bottom:14px">${escHtml(s.descricao)}</div>` : ''}
      <div class="room-actions">
        <button class="btn-recep btn-recep-secondary" onclick="agendarPara(${s.id})">
          <i class="bi bi-calendar-plus"></i> Agendar
        </button>
        ${podeGerenciarSala() ? `
          <button class="btn-recep btn-recep-secondary" onclick="openSalaModal(${s.id})">
            <i class="bi bi-pencil"></i>
          </button>
          <button class="btn-recep btn-recep-secondary" onclick="deletarSala(${s.id}, '${escHtml(s.nome).replace(/'/g, "\\'")}')" style="color:#ef4444">
            <i class="bi bi-trash"></i>
          </button>` : ''}
      </div>
    </div>
  `).join('');
}

function populateResvSala() {
  // popula o select de sala da modal de Nova Reserva conforme unidade selecionada
  onResvUnitChange();
}

function onResvUnitChange() {
  const unitId = $('resvUnit').value;
  const escWrap = $('resvEscritorioWrap');
  const escSel  = $('resvEscritorio');

  // Mostra select de escritório só se a unidade tiver subdivisão
  if (unitId && unidadeTemEscritorios(unitId)) {
    escSel.innerHTML = '<option value="">— Selecione o escritório —</option>' +
      escritoriosDaUnidade(unitId)
        .map(e => `<option value="${e.id}">${escHtml(e.nome)}</option>`).join('');
    escWrap.style.display = '';
  } else {
    escWrap.style.display = 'none';
    escSel.value = '';
  }

  onResvEscritorioChange();
}

function onResvEscritorioChange() {
  const unitId = $('resvUnit').value;
  const escId  = $('resvEscritorio').value;
  const exigeEscritorio = unitId && unidadeTemEscritorios(unitId);

  // Filtra salas pelo escritório quando aplicável
  const filtradas = salas.filter(s => {
    if (!s.ativa) return false;
    if (unitId && String(s.unit_id) !== String(unitId)) return false;
    if (exigeEscritorio) {
      if (!escId) return false;
      // Sala sem escritorio_id = "comum" à unidade (aparece em qualquer escritório).
      // Sala com escritorio_id = só aparece no escritório específico.
      if (s.escritorio_id && String(s.escritorio_id) !== String(escId)) return false;
    }
    return true;
  });

  const placeholder = exigeEscritorio && !escId
    ? '<option value="">— Selecione o escritório primeiro —</option>'
    : '<option value="">— Selecione a sala —</option>';
  $('resvSala').innerHTML = placeholder + filtradas.map(s => {
    const sufixo = s.escritorio_nome ? ` · ${escHtml(s.escritorio_nome)}` : '';
    return `<option value="${s.id}">${escHtml(s.nome)} — ${escHtml(s.unit_sigla || s.unit_nome || '')}${sufixo}</option>`;
  }).join('');
}

function onSalaUnitChange() {
  const unitId = $('salaUnit').value;
  const wrap = $('salaEscritorioWrap');
  const sel  = $('salaEscritorio');
  if (unitId && unidadeTemEscritorios(unitId)) {
    const cur = sel.value;
    sel.innerHTML = '<option value="">— Sem escritório —</option>' +
      escritoriosDaUnidade(unitId)
        .map(e => `<option value="${e.id}">${escHtml(e.nome)}</option>`).join('');
    if (cur) sel.value = cur;
    wrap.style.display = '';
  } else {
    wrap.style.display = 'none';
    sel.value = '';
  }
}

function onFilterSalaUnitChange() {
  const unitId = $('filterUnitSala').value;
  const wrap = $('filterEscritorioSala');
  if (unitId && unidadeTemEscritorios(unitId)) {
    wrap.innerHTML = '<option value="">Todos os escritórios</option>' +
      escritoriosDaUnidade(unitId)
        .map(e => `<option value="${e.id}">${escHtml(e.nome)}</option>`).join('');
    wrap.style.display = '';
  } else {
    wrap.value = '';
    wrap.style.display = 'none';
  }
  loadSalas();
}

function openSalaModal(salaId = null) {
  if (!podeGerenciarSala()) {
    toast('Apenas Administrador ou Responsável de Grupo podem cadastrar salas.', 'error');
    return;
  }

  editandoSala = salaId;
  $('salaErr').classList.add('d-none');

  if (salaId) {
    const s = salas.find(x => x.id === salaId);
    if (!s) return;
    $('salaModalTitle').textContent = 'Editar Sala';
    $('salaUnit').value       = s.unit_id;
    $('salaNome').value        = s.nome || '';
    $('salaTipo').value        = s.tipo || 'sala';
    $('salaCapacidade').value  = s.capacidade || '';
    $('salaCor').value         = s.cor || '#3b82f6';
    $('salaDescricao').value   = s.descricao || '';
    $('salaAtiva').checked     = !!s.ativa;
    onSalaUnitChange();   // popula escritórios
    $('salaEscritorio').value = s.escritorio_id || '';
  } else {
    $('salaModalTitle').textContent = 'Nova Sala';
    $('salaUnit').value       = currentUser.unit_id || '';
    $('salaNome').value        = '';
    $('salaTipo').value        = 'sala';
    $('salaCapacidade').value  = '';
    $('salaCor').value         = '#3b82f6';
    $('salaDescricao').value   = '';
    $('salaAtiva').checked     = true;
    onSalaUnitChange();
  }

  new bootstrap.Modal($('salaModal')).show();
}

async function submitSala() {
  const erro = $('salaErr');
  erro.classList.add('d-none');

  const unit_id        = parseInt($('salaUnit').value) || 0;
  const escritorio_id  = parseInt($('salaEscritorio').value) || null;
  const nome           = $('salaNome').value.trim();
  const tipo           = $('salaTipo').value;
  const capacidade     = parseInt($('salaCapacidade').value) || null;
  const cor            = $('salaCor').value;
  const descricao      = $('salaDescricao').value.trim();
  const ativa          = $('salaAtiva').checked;

  if (!unit_id) {
    erro.textContent = 'Selecione a unidade';
    erro.classList.remove('d-none'); return;
  }
  if (!nome || nome.length < 2) {
    erro.textContent = 'Nome obrigatório';
    erro.classList.remove('d-none'); return;
  }
  if (unidadeTemEscritorios(unit_id) && !escritorio_id) {
    erro.textContent = 'Esta unidade tem escritórios. Selecione qual escritório esta sala pertence.';
    erro.classList.remove('d-none'); return;
  }

  const payload = {
    unit_id,
    escritorio_id,
    nome, tipo, capacidade, cor, descricao: descricao || null, ativa,
  };
  let url    = API.salas;
  let method = 'POST';

  if (editandoSala) {
    url    = API.salas + '/' + editandoSala;
    method = 'PUT';
    payload.atualizado_por = currentUser.id;
    // sentinela 0 = limpar escritório
    payload.escritorio_id = escritorio_id || 0;
  } else {
    payload.criado_por = currentUser.id;
  }

  try {
    const r = await fetch(url, {
      method, headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.detail || 'HTTP ' + r.status);
    }
    bootstrap.Modal.getInstance($('salaModal')).hide();
    toast(editandoSala ? 'Sala atualizada' : 'Sala criada', 'success');
    await loadSalas();
    if (calendar) calendar.refetchEvents();
  } catch (err) {
    erro.textContent = err.message;
    erro.classList.remove('d-none');
  }
}

async function deletarSala(salaId, nome) {
  if (!confirm(`Excluir a sala "${nome}"? Todas as reservas associadas também serão removidas.`)) return;
  try {
    const r = await fetch(`${API.salas}/${salaId}?usuario_id=${currentUser.id}`, { method: 'DELETE' });
    if (!r.ok && r.status !== 204) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.detail || 'HTTP ' + r.status);
    }
    toast('Sala removida', 'success');
    await loadSalas();
    if (calendar) calendar.refetchEvents();
  } catch (err) {
    toast('Erro ao excluir: ' + err.message, 'error');
  }
}

function agendarPara(salaId) {
  showSection('calendario');
  setTimeout(() => {
    const s = salas.find(x => x.id === salaId);
    openReservaModal();
    if (s) {
      $('resvUnit').value = s.unit_id;
      onResvUnitChange();
      $('resvSala').value = String(salaId);
    }
  }, 50);
}

/* ============================================================
   CALENDARIO + RESERVAS
   ============================================================ */
function statusToColor(status) {
  switch (status) {
    case 'pendente':   return '#f59e0b';
    case 'confirmada': return '#3b82f6';
    case 'concluida':  return '#9ca3af';
    case 'cancelada':
    case 'expirada':   return '#ef4444';
    default:           return '#6b7280';
  }
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
    // Tradução manual — garante PT-BR mesmo se o pacote de locale não carregar
    buttonText: {
      today:   'Hoje',
      month:   'Mês',
      week:    'Semana',
      day:     'Dia',
      list:    'Agenda',
      prev:    'Anterior',
      next:    'Próximo',
    },
    allDayText: 'Dia todo',
    moreLinkText: n => `+${n} mais`,
    noEventsText: 'Nenhuma reserva no período',
    weekText: 'Sem',
    height: 720,
    nowIndicator: true,
    slotMinTime: '07:00:00',
    slotMaxTime: '22:00:00',
    allDaySlot: false,
    selectable: true,
    selectMirror: true,
    select(info) {
      openReservaModal();
      const i = new Date(info.start);
      const f = new Date(info.end);
      $('resvInicio').value = toDtLocalInput(i);
      $('resvFim').value    = toDtLocalInput(f);
    },
    eventClick(info) {
      openReservaDetalhe(info.event.extendedProps.reserva);
    },
    events: fetchEventos,
  });
  calendar.render();
}

function toDtLocalInput(d) {
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

async function fetchEventos(fetchInfo, success, failure) {
  try {
    const params = new URLSearchParams();
    params.set('inicio', fetchInfo.startStr);
    params.set('fim',    fetchInfo.endStr);
    const unitId = $('filterUnitCal').value;
    const salaId = $('filterSalaCal').value;
    if (unitId) params.set('unit_id', unitId);
    if (salaId) params.set('sala_id', salaId);

    const r = await fetch(`${API.reservas}?${params}`);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const lista = await r.json();

    const events = lista.map(rv => ({
      id: String(rv.id),
      title: `${rv.titulo} — ${rv.sala_nome}`,
      start: rv.inicio,
      end:   rv.fim,
      backgroundColor: statusToColor(rv.status),
      borderColor: statusToColor(rv.status),
      textColor: '#fff',
      classNames: ['recep-event-' + rv.status],
      extendedProps: { reserva: rv },
    }));
    success(events);
  } catch (err) {
    console.error('[RECEP/EVENTOS]', err);
    failure(err);
  }
}

function onFilterCalendar() {
  const unitId = $('filterUnitCal').value;
  const escWrap = $('filterEscritorioCal');

  // mostra/esconde filtro de escritório
  if (unitId && unidadeTemEscritorios(unitId)) {
    const cur = escWrap.value;
    escWrap.innerHTML = '<option value="">Todos os escritórios</option>' +
      escritoriosDaUnidade(unitId)
        .map(e => `<option value="${e.id}">${escHtml(e.nome)}</option>`).join('');
    if (cur) escWrap.value = cur;
    escWrap.style.display = '';
  } else {
    escWrap.value = '';
    escWrap.style.display = 'none';
  }
  const escId = escWrap.value;

  const filtradas = salas.filter(s => {
    if (unitId && String(s.unit_id) !== String(unitId)) return false;
    // Sala sem escritorio_id = "comum" à unidade (aparece em qualquer escritório)
    if (escId && s.escritorio_id && String(s.escritorio_id) !== String(escId)) return false;
    return true;
  });
  const cur = $('filterSalaCal').value;
  $('filterSalaCal').innerHTML = '<option value="">Todas as salas</option>' +
    filtradas.map(s => `<option value="${s.id}">${escHtml(s.nome)}</option>`).join('');
  if (cur) $('filterSalaCal').value = cur;

  if (calendar) calendar.refetchEvents();
}

function openReservaModal() {
  $('reservaErr').classList.add('d-none');
  $('reservaModalTitle').textContent = 'Nova Reserva';
  $('resvUnit').value       = currentUser.unit_id || '';
  $('resvEscritorio').value = '';
  onResvUnitChange();              // mostra/esconde escritório e filtra salas
  $('resvTitulo').value    = '';
  $('resvDescricao').value = '';
  $('resvConvidadosBusca').value = '';
  filtrarConvidados();             // popula select de convidados
  // preenche com "agora" arredondado pra próxima meia hora
  const now = new Date();
  now.setMinutes(Math.ceil(now.getMinutes() / 30) * 30, 0, 0);
  const fim = new Date(now.getTime() + 60 * 60 * 1000);
  $('resvInicio').value = toDtLocalInput(now);
  $('resvFim').value    = toDtLocalInput(fim);

  new bootstrap.Modal($('reservaModal')).show();
}

async function submitReserva() {
  const erro = $('reservaErr');
  erro.classList.add('d-none');

  const unitId    = $('resvUnit').value;
  const escId     = $('resvEscritorio').value;
  const sala_id   = parseInt($('resvSala').value) || 0;
  const titulo    = $('resvTitulo').value.trim();
  const inicio    = dtIso($('resvInicio').value);
  const fim       = dtIso($('resvFim').value);
  const descricao = $('resvDescricao').value.trim() || null;

  if (unitId && unidadeTemEscritorios(unitId) && !escId) {
    erro.textContent = 'Selecione o escritório (obrigatório nesta unidade)';
    erro.classList.remove('d-none'); return;
  }
  if (!sala_id) {
    erro.textContent = 'Selecione a sala';
    erro.classList.remove('d-none'); return;
  }
  if (!titulo || titulo.length < 2) {
    erro.textContent = 'Informe o título da reunião';
    erro.classList.remove('d-none'); return;
  }
  if (!inicio || !fim) {
    erro.textContent = 'Informe início e fim';
    erro.classList.remove('d-none'); return;
  }
  if (new Date(fim) <= new Date(inicio)) {
    erro.textContent = 'Fim deve ser maior que o início';
    erro.classList.remove('d-none'); return;
  }

  const convidados_ids = Array.from($('resvConvidados').selectedOptions)
    .map(o => parseInt(o.value)).filter(Boolean);

  const payload = {
    sala_id,
    usuario_id: currentUser.id,
    titulo,
    descricao,
    inicio,
    fim,
    convidados_ids,
  };

  try {
    const btn = $('btnSubmitReserva');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Enviando...';

    const r = await fetch(API.reservas, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.detail || 'HTTP ' + r.status);
    }
    const reserva = await r.json();

    bootstrap.Modal.getInstance($('reservaModal')).hide();
    const sufConv = convidados_ids.length
      ? ` ${convidados_ids.length} convidado(s) notificado(s).`
      : '';
    toast(
      `Reserva criada! Confirme em até 40 min.${sufConv} ` +
      `<a href="#" onclick="abrirReservaPorId(${reserva.id});return false;">confirmar agora</a>`,
      'success',
    );
    if (calendar) calendar.refetchEvents();
  } catch (err) {
    erro.textContent = err.message;
    erro.classList.remove('d-none');
  } finally {
    const btn = $('btnSubmitReserva');
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-check-lg"></i> Criar Reserva';
  }
}

async function abrirReservaPorId(id) {
  // Busca em janela ampla (-180 / +180 dias) pra não depender da view atual
  try {
    const inicio = new Date(Date.now() - 180 * 86400000).toISOString();
    const fim    = new Date(Date.now() + 180 * 86400000).toISOString();
    const url = `${API.reservas}?inicio=${encodeURIComponent(inicio)}&fim=${encodeURIComponent(fim)}`;
    const r = await fetch(url);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const list = await r.json();
    const reserva = list.find(x => x.id === id);
    if (reserva) {
      showSection('calendario');
      openReservaDetalhe(reserva);
    } else {
      toast('Reserva não encontrada (#' + id + ').', 'warn');
    }
  } catch (err) {
    toast('Erro ao buscar reserva: ' + err.message, 'error');
  }
}

async function openReservaDetalhe(rv) {
  if (!rv) return;
  const dono       = rv.usuario_id === currentUser.id;
  const podeAdmin  = ['ADMIN', 'TI', 'MANAGER'].includes(currentUser.role);
  const statusLabel = {
    pendente:   'Pendente — aguardando confirmação',
    confirmada: 'Confirmada — sala em uso',
    concluida:  'Concluída',
    cancelada:  'Cancelada',
    expirada:   'Expirada — confirmação não recebida até o início',
  }[rv.status] || rv.status;

  // Mensagem de prazo: agora baseada no horário de início (não no created_at).
  // Mostra contagem regressiva até o início e avisa quando entrou na janela
  // dos 40 min finais.
  let prazoMsg = '';
  if (rv.status === 'pendente') {
    const minAteInicio = (new Date(rv.inicio) - new Date()) / 60000;
    if (minAteInicio <= 0) {
      prazoMsg = `<div class="alert alert-danger" style="font-size:.85rem;margin-top:10px">
        <i class="bi bi-x-octagon"></i> A reunião já passou do horário de início — esta reserva será expirada em breve.
      </div>`;
    } else if (minAteInicio <= 40) {
      prazoMsg = `<div class="alert alert-danger" style="font-size:.85rem;margin-top:10px">
        <i class="bi bi-bell-fill"></i> <strong>Confirme agora!</strong>
        Faltam <strong>${Math.ceil(minAteInicio)} min</strong> para o início — sem confirmação, a sala será liberada.
      </div>`;
    } else {
      const horas = Math.floor(minAteInicio / 60);
      const mins  = Math.ceil(minAteInicio % 60);
      const tempo = horas > 0 ? `${horas}h ${mins}min` : `${mins}min`;
      prazoMsg = `<div class="alert alert-info" style="font-size:.85rem;margin-top:10px">
        <i class="bi bi-clock"></i> Reunião começa em <strong>${tempo}</strong>.
        Você receberá uma notificação no sino 40 min antes para confirmar.
      </div>`;
    }
  }

  // busca lista de convidados
  let convidados = [];
  try {
    const r = await fetch(`${API.reservas}/${rv.id}/convidados`);
    if (r.ok) convidados = await r.json();
  } catch (_) {}

  const meuConvite = convidados.find(c => c.usuario_id === currentUser.id);

  const statusBadge = (s) => {
    const cores = {
      pendente: 'background:#fde68a;color:#92400e',
      aceito:   'background:#bbf7d0;color:#065f46',
      recusado: 'background:#fecaca;color:#991b1b',
    };
    const lbls = { pendente: 'Pendente', aceito: 'Aceito', recusado: 'Recusou' };
    return `<span style="${cores[s] || ''};padding:2px 8px;border-radius:10px;font-size:.72rem;font-weight:600">${lbls[s] || s}</span>`;
  };

  const convidadosHtml = convidados.length === 0
    ? '<p style="color:#9ca3af;font-size:.85rem;margin:0">Nenhum convidado nesta reunião.</p>'
    : `<ul class="list-group list-group-flush" style="max-height:180px;overflow-y:auto">
        ${convidados.map(c => `
          <li class="list-group-item d-flex justify-content-between align-items-center" style="padding:6px 0;border:none">
            <span style="font-size:.9rem">
              <i class="bi bi-person-fill"></i> ${escHtml(c.usuario_nome)}
              ${c.usuario_id === currentUser.id ? '<span style="color:#3b82f6;font-size:.75rem">(você)</span>' : ''}
            </span>
            ${statusBadge(c.status)}
          </li>
        `).join('')}
       </ul>`;

  $('resvDetCorpo').innerHTML = `
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
      <span class="badge" style="background:${statusToColor(rv.status)};color:#fff;padding:6px 10px;font-size:.85rem">
        ${escHtml(statusLabel)}
      </span>
    </div>
    <h5>${escHtml(rv.titulo)}</h5>
    ${rv.descricao ? `<p style="color:#6b7280">${escHtml(rv.descricao)}</p>` : ''}
    <hr>
    <p><i class="bi bi-door-open"></i> <strong>Sala:</strong> ${escHtml(rv.sala_nome)}</p>
    ${rv.escritorio_nome ? `<p><i class="bi bi-building"></i> <strong>Escritório:</strong> ${escHtml(rv.escritorio_nome)}</p>` : ''}
    <p><i class="bi bi-person"></i> <strong>Solicitante:</strong> ${escHtml(rv.usuario_nome)}</p>
    <p><i class="bi bi-calendar"></i> <strong>Início:</strong> ${dtPt(rv.inicio)}</p>
    <p><i class="bi bi-calendar-check"></i> <strong>Fim:</strong> ${dtPt(rv.fim)}</p>
    ${rv.confirmada_em ? `<p><i class="bi bi-check2-circle"></i> <strong>Confirmada em:</strong> ${dtPt(rv.confirmada_em)}</p>` : ''}
    ${rv.cancelada_em ? `<p><i class="bi bi-x-circle"></i> <strong>Encerrada em:</strong> ${dtPt(rv.cancelada_em)} ${rv.motivo_cancel ? '— ' + escHtml(rv.motivo_cancel) : ''}</p>` : ''}
    ${prazoMsg}
    <hr>
    <h6 style="margin-bottom:8px"><i class="bi bi-people-fill"></i> Convidados (${convidados.length})</h6>
    ${convidadosHtml}
  `;

  const acts = $('resvDetActions');
  acts.innerHTML = '';

  // Botões aceitar/recusar — apenas para convidado com status pendente
  if (meuConvite && meuConvite.status === 'pendente' && !['cancelada','expirada','concluida'].includes(rv.status)) {
    const btnAceitar = document.createElement('button');
    btnAceitar.className = 'btn btn-success';
    btnAceitar.innerHTML = '<i class="bi bi-check-lg"></i> Aceitar Convite';
    btnAceitar.onclick = () => responderConvite(meuConvite.id, true, rv.id);
    acts.appendChild(btnAceitar);

    const btnRecusar = document.createElement('button');
    btnRecusar.className = 'btn btn-outline-danger';
    btnRecusar.innerHTML = '<i class="bi bi-x-lg"></i> Recusar';
    btnRecusar.onclick = () => responderConvite(meuConvite.id, false, rv.id);
    acts.appendChild(btnRecusar);
  }

  if (rv.status === 'pendente' && (dono || podeAdmin)) {
    const btn = document.createElement('button');
    btn.className = 'btn btn-success';
    btn.innerHTML = '<i class="bi bi-check-lg"></i> Confirmar Reserva';
    btn.onclick = () => confirmarReserva(rv.id);
    acts.appendChild(btn);
  }
  if (['pendente', 'confirmada'].includes(rv.status) && (dono || podeAdmin)) {
    const btnCanc = document.createElement('button');
    btnCanc.className = 'btn btn-outline-danger';
    btnCanc.innerHTML = '<i class="bi bi-x-lg"></i> Cancelar';
    btnCanc.onclick = () => cancelarReserva(rv.id);
    acts.appendChild(btnCanc);
  }
  const btnFechar = document.createElement('button');
  btnFechar.className = 'btn btn-secondary';
  btnFechar.textContent = 'Fechar';
  btnFechar.setAttribute('data-bs-dismiss', 'modal');
  acts.appendChild(btnFechar);

  new bootstrap.Modal($('reservaDetalhe')).show();
}

async function responderConvite(conviteId, aceitar, reservaId) {
  try {
    const r = await fetch(`${API.convites}/${conviteId}/responder`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ usuario_id: currentUser.id, aceitar }),
    });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.detail || 'HTTP ' + r.status);
    }
    toast(aceitar ? 'Convite aceito.' : 'Convite recusado.', aceitar ? 'success' : 'warn');
    bootstrap.Modal.getInstance($('reservaDetalhe'))?.hide();
    if (calendar) calendar.refetchEvents();
  } catch (err) {
    toast('Erro: ' + err.message, 'error');
  }
}

async function confirmarReserva(id) {
  try {
    const r = await fetch(`${API.reservas}/${id}/confirmar?usuario_id=${currentUser.id}`, { method: 'POST' });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.detail || 'HTTP ' + r.status);
    }
    toast('Reserva confirmada — a sala está marcada como em uso.', 'success');
    bootstrap.Modal.getInstance($('reservaDetalhe'))?.hide();
    if (calendar) calendar.refetchEvents();
  } catch (err) {
    toast('Erro: ' + err.message, 'error');
  }
}

async function cancelarReserva(id) {
  const motivo = prompt('Motivo do cancelamento (opcional):') || null;
  try {
    const r = await fetch(`${API.reservas}/${id}/cancelar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ usuario_id: currentUser.id, motivo }),
    });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.detail || 'HTTP ' + r.status);
    }
    toast('Reserva cancelada', 'warn');
    bootstrap.Modal.getInstance($('reservaDetalhe'))?.hide();
    if (calendar) calendar.refetchEvents();
  } catch (err) {
    toast('Erro: ' + err.message, 'error');
  }
}

/* ============================================================
   ENVIOS
   ============================================================ */
async function loadEnvios() {
  try {
    const r = await fetch(API.envios);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    envios = await r.json();
    renderEnvios();
  } catch (err) {
    toast('Erro ao carregar envios: ' + err.message, 'error');
  }
}

function renderEnvios() {
  const tbody = $('enviosTbody');
  if (!tbody) return;

  const search = ($('envioSearch')?.value || '').toLowerCase();
  let lista = envios;
  if (search) {
    lista = envios.filter(e =>
      (e.destino || '').toLowerCase().includes(search) ||
      (e.destinatario || '').toLowerCase().includes(search) ||
      (e.codigo_correios || '').toLowerCase().includes(search)
    );
  }

  if (!lista.length) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;color:#6b7280;padding:24px">
      <i class="bi bi-inbox"></i> Nenhum envio cadastrado.<br>
      <small>Clique em <strong>"Novo Envio"</strong> para registrar uma mercadoria.
      Após salvar com o código de rastreio, o botão <strong>Rastrear</strong> aparece nesta tabela.</small>
    </td></tr>`;
    return;
  }

  tbody.innerHTML = lista.map(e => {
    const codigoCell = e.codigo_correios
      ? `<a href="#" onclick="abrirRastreio(${e.id});return false" title="Rastrear via API">
           <code>${escHtml(e.codigo_correios)}</code> <i class="bi bi-geo-alt" style="font-size:.7rem"></i>
         </a>`
      : '<span style="color:#9ca3af">—</span>';
    return `
    <tr>
      <td>#${e.id}</td>
      <td>${escHtml(e.remetente_nome || '—')}</td>
      <td>${escHtml(e.destino)}</td>
      <td>${escHtml(e.destinatario)}</td>
      <td>${brl(e.valor_mercadoria)}</td>
      <td>${codigoCell}</td>
      <td>${e.status_correios
            ? `<span class="badge-status" style="background:#dbeafe;color:#1e40af">${escHtml(e.status_correios)}</span>`
            : '<span style="color:#9ca3af;font-size:.85rem">Não rastreado</span>'}</td>
      <td style="font-size:.85rem;color:#6b7280">${e.ultima_atualizacao ? dtPt(e.ultima_atualizacao) : '—'}</td>
      <td style="white-space:nowrap;text-align:center">
        ${e.codigo_correios ? `
          <button class="btn btn-sm btn-outline-primary" onclick="abrirRastreio(${e.id})" title="Rastrear via API">
            <i class="bi bi-geo-alt"></i> Rastrear
          </button>
          <button class="btn btn-sm btn-outline-secondary" onclick="atualizarStatusManual(${e.id})" title="Atualizar status manualmente">
            <i class="bi bi-pencil-square"></i>
          </button>` : `
          <button class="btn btn-sm btn-outline-secondary" disabled title="Cadastre o código dos Correios para habilitar">
            <i class="bi bi-geo-alt"></i> Sem código
          </button>`}
        <button class="btn btn-sm btn-outline-secondary" onclick="openEnvioModal(${e.id})" title="Editar envio">
          <i class="bi bi-pencil"></i>
        </button>
        <button class="btn btn-sm btn-outline-danger" onclick="deletarEnvio(${e.id})" title="Excluir">
          <i class="bi bi-trash"></i>
        </button>
      </td>
    </tr>`;
  }).join('');
}

/* ========================================================
   RASTREIO via API seurastreio.com.br
   ========================================================
   Mantido como FALLBACK abaixo (comentado): abrir o site dos
   Correios numa janela popup, caso a API falhe.
   ======================================================== */

let _rastApiEnvioAtual = null;

function abrirRastreio(codigoOuEnvioId) {
  // Aceita ID do envio (numérico) ou código de rastreio (string)
  let envio = null;
  if (typeof codigoOuEnvioId === 'number') {
    envio = envios.find(e => e.id === codigoOuEnvioId);
  } else {
    envio = envios.find(e => e.codigo_correios === codigoOuEnvioId);
  }
  if (!envio || !envio.codigo_correios) {
    toast('Envio sem código de rastreio.', 'warn');
    return;
  }
  _rastApiEnvioAtual = envio.id;
  $('rastApiCodigo').textContent = envio.codigo_correios;
  $('rastApiLinkDetalhes').style.display = 'none';
  $('rastApiCorpo').innerHTML = `
    <div class="text-center" style="padding:32px">
      <div class="recep-spinner" style="margin:0 auto 12px"></div>
      <p class="text-muted">Consultando API...</p>
    </div>`;
  new bootstrap.Modal($('rastreioApiModal')).show();
  carregarRastreioApi(envio.id);
}

async function rastrearEnvioRecarregar() {
  if (_rastApiEnvioAtual) await carregarRastreioApi(_rastApiEnvioAtual);
}

async function carregarRastreioApi(envioId) {
  const corpo = $('rastApiCorpo');
  try {
    const r = await fetch(`${API.envios}/${envioId}/rastrear`);
    const data = await r.json();

    if (!r.ok) {
      throw new Error(data.detail || 'HTTP ' + r.status);
    }

    if (!data.ok) {
      corpo.innerHTML = `
        <div class="alert alert-warning">
          <i class="bi bi-exclamation-triangle"></i>
          <strong>Não foi possível consultar a API.</strong><br>
          ${escHtml(data.erro || 'Erro desconhecido')}
        </div>
        <p class="text-muted small">
          Você pode usar o rastreio manual (botão de lápis na tabela) ou abrir o site dos
          Correios em nova aba clicando
          <a href="https://rastreamento.correios.com.br/app/index.php?objetos=${encodeURIComponent($('rastApiCodigo').textContent)}"
             target="_blank" rel="noopener">aqui</a>.
        </p>`;
      return;
    }

    if (data.linkDetalhes) {
      const link = $('rastApiLinkDetalhes');
      link.href = data.linkDetalhes;
      link.style.display = '';
    }

    // Banner de cache + controle do botão "Atualizar"
    const btnAtualizar = $('rastApiBtnRecarregar');
    let bannerCache = '';
    if (data.cached) {
      const ult     = data.ultima_consulta_api ? dtPt(data.ultima_consulta_api) : '—';
      const proxima = data.proxima_consulta_em ? dtPt(data.proxima_consulta_em) : '—';
      bannerCache = `
        <div class="alert alert-secondary py-2 mb-3" style="font-size:.82rem">
          <i class="bi bi-clock-history"></i>
          <strong>Dados em cache.</strong>
          Última consulta: ${escHtml(ult)}.
          Próxima atualização disponível em <strong>${escHtml(proxima)}</strong>
          (cache de ${data.cache_horas || 4}h por envio para economizar consultas da API).
        </div>`;
      btnAtualizar.disabled = true;
      btnAtualizar.title    = `Liberada em ${proxima}`;
      btnAtualizar.classList.add('disabled');
    } else {
      btnAtualizar.disabled = false;
      btnAtualizar.title    = 'Forçar nova consulta na API';
      btnAtualizar.classList.remove('disabled');
    }

    const eventos = data.eventos || [];
    const previsao = data.previsaoEntrega
      ? `<div class="alert alert-info py-2 mb-3" style="font-size:.85rem">
           <i class="bi bi-calendar-event"></i>
           <strong>Previsão de entrega:</strong> ${dtPt(data.previsaoEntrega)}
         </div>` : '';

    const eventoMaisRecente = data.descricao
      ? `<div class="rast-card-status">
           <div class="rast-status-icon"><i class="bi bi-geo-alt-fill"></i></div>
           <div>
             <div class="rast-status-titulo">${escHtml(data.descricao)}</div>
             ${data.local ? `<div class="rast-status-local">${escHtml(data.local)}</div>` : ''}
             ${data.data  ? `<div class="rast-status-data">${dtPt(data.data)}</div>` : ''}
           </div>
         </div>` : '';

    let timeline = '';
    if (eventos.length > 1) {
      timeline = `
        <h6 class="mt-4 mb-3"><i class="bi bi-clock-history"></i> Histórico</h6>
        <div class="status-timeline">
          ${eventos.map(ev => `
            <div class="status-event">
              <div class="status-event-icon em_transito">
                <i class="bi bi-geo-alt"></i>
              </div>
              <div class="status-event-body">
                <p class="status-event-title">${escHtml(ev.descricao || '—')}</p>
                ${ev.local ? `<p class="status-event-local">${escHtml(ev.local)}</p>` : ''}
                ${ev.data  ? `<div class="status-event-data">${dtPt(ev.data)}</div>` : ''}
              </div>
            </div>`).join('')}
        </div>`;
    } else if (eventos.length === 1 && data.message) {
      timeline = `<p class="text-muted small mt-3"><i class="bi bi-info-circle"></i> ${escHtml(data.message)}</p>`;
    }

    if (!eventoMaisRecente && !timeline) {
      corpo.innerHTML = bannerCache + `
        <div class="status-empty">
          <i class="bi bi-inbox" style="font-size:32px;display:block;margin-bottom:8px"></i>
          ${escHtml(data.message || 'Sem eventos registrados ainda.')}
        </div>`;
      return;
    }

    corpo.innerHTML = bannerCache + previsao + eventoMaisRecente + timeline;

    // Atualiza status na tabela em segundo plano
    await loadEnvios();

  } catch (err) {
    corpo.innerHTML = `
      <div class="alert alert-danger">
        <i class="bi bi-x-circle"></i> Erro: ${escHtml(err.message)}
      </div>`;
  }
}

/* ============================================================
   FALLBACK — popup com site dos Correios
   ============================================================
   Caso a API seurastreio.com.br fique indisponível, descomentar
   a função abaixo e usá-la em substituição a `abrirRastreio()`.

   function abrirRastreio_PopupCorreios(codigo) {
     const codigoLimpo = String(codigo || '').trim().toUpperCase();
     if (!codigoLimpo) return;
     const url = `https://rastreamento.correios.com.br/app/index.php?objetos=${encodeURIComponent(codigoLimpo)}`;
     const w = 1100, h = 750;
     const left = Math.max(0, (window.screen.width  - w) / 2);
     const top  = Math.max(0, (window.screen.height - h) / 2);
     const features = `width=${w},height=${h},left=${left},top=${top},`
                    + 'resizable=yes,scrollbars=yes,toolbar=no,menubar=no,location=no,status=no';
     const popup = window.open(url, 'rastreioCorreios', features);
     if (!popup || popup.closed) {
       toast('Permita popups deste site no navegador para abrir o rastreamento.', 'warn');
       window.open(url, '_blank', 'noopener');
       return;
     }
     popup.focus();
   }
*/

/* ========================================================
   STATUS MANUAL — modal com timeline (estilo Correios)
   ======================================================== */
const TIPOS_EVENTO = {
  etiqueta_emitida:    { icone: 'bi-upc-scan',          label: 'Etiqueta emitida' },
  postado:             { icone: 'bi-mailbox',           label: 'Postado nos Correios' },
  em_transito:         { icone: 'bi-truck',             label: 'Em trânsito' },
  saiu_entrega:        { icone: 'bi-truck-flatbed',     label: 'Saiu para entrega' },
  entregue:            { icone: 'bi-box-seam-fill',     label: 'Entregue' },
  aguardando_retirada: { icone: 'bi-shop',              label: 'Aguardando retirada' },
  tentativa_entrega:   { icone: 'bi-clock-history',     label: 'Tentativa de entrega' },
  devolvido:           { icone: 'bi-arrow-counterclockwise', label: 'Devolvido' },
  extraviado:          { icone: 'bi-exclamation-triangle', label: 'Extraviado' },
  outros:              { icone: 'bi-info-circle',       label: 'Outro' },
};

let _statusEnvioId = null;
let _statusEventos = [];

async function atualizarStatusManual(envioId) {
  const e = envios.find(x => x.id === envioId);
  if (!e) return;
  _statusEnvioId = envioId;
  $('statusEnvioRef').textContent =
    `— #${envioId} • ${e.destinatario || ''} ${e.codigo_correios ? '• ' + e.codigo_correios : ''}`;
  $('statusForm').style.display = 'none';
  $('statusFormErr').classList.add('d-none');
  await carregarEventos();
  new bootstrap.Modal($('statusModal')).show();
}

async function carregarEventos() {
  const tl = $('statusTimeline');
  tl.innerHTML = '<div class="status-empty"><i class="bi bi-hourglass-split"></i> Carregando...</div>';
  try {
    const r = await fetch(`${API.envios}/${_statusEnvioId}/eventos`);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    _statusEventos = await r.json();
    renderTimeline();
  } catch (err) {
    tl.innerHTML = `<div class="status-empty text-danger">Erro: ${escHtml(err.message)}</div>`;
  }
}

function renderTimeline() {
  const tl = $('statusTimeline');
  if (!_statusEventos.length) {
    tl.innerHTML = `
      <div class="status-empty">
        <i class="bi bi-clock-history" style="font-size:32px;display:block;margin-bottom:8px"></i>
        Nenhum evento registrado ainda.<br>
        <small>Clique em "Adicionar evento" para registrar um status.</small>
      </div>`;
    return;
  }
  tl.innerHTML = _statusEventos.map(ev => {
    const t = TIPOS_EVENTO[ev.tipo] || TIPOS_EVENTO.outros;
    return `
      <div class="status-event">
        <div class="status-event-icon ${ev.tipo}">
          <i class="bi ${t.icone}"></i>
        </div>
        <div class="status-event-body">
          <p class="status-event-title">${escHtml(ev.descricao)}</p>
          ${ev.local ? `<p class="status-event-local">${escHtml(ev.local)}</p>` : ''}
          <div class="status-event-data">${dtPt(ev.data_evento)}</div>
        </div>
        <div class="status-event-actions">
          <button onclick="abrirFormEvento(${ev.id})" title="Editar"><i class="bi bi-pencil"></i></button>
          <button class="danger" onclick="excluirEvento(${ev.id})" title="Excluir"><i class="bi bi-trash"></i></button>
        </div>
      </div>`;
  }).join('');
}

function abrirFormEvento(eventoId = null) {
  $('statusForm').style.display = '';
  $('statusFormErr').classList.add('d-none');
  $('btnAdicionarEvento').disabled = true;

  if (eventoId) {
    const ev = _statusEventos.find(x => x.id === eventoId);
    if (!ev) return;
    $('statusFormTitle').innerHTML = '<i class="bi bi-pencil"></i> Editar evento';
    $('statusFormId').value        = ev.id;
    $('statusFormTipo').value      = ev.tipo;
    $('statusFormDescricao').value = ev.descricao || '';
    $('statusFormLocal').value     = ev.local || '';
    $('statusFormData').value      = (ev.data_evento || '').replace(' ', 'T').slice(0, 16);
  } else {
    $('statusFormTitle').innerHTML = '<i class="bi bi-plus-circle"></i> Novo evento';
    $('statusFormId').value        = '';
    $('statusFormTipo').value      = 'em_transito';
    $('statusFormDescricao').value = '';
    $('statusFormLocal').value     = '';
    const agora = new Date();
    agora.setMinutes(agora.getMinutes() - agora.getTimezoneOffset());
    $('statusFormData').value      = agora.toISOString().slice(0, 16);
  }
}

function cancelarFormEvento() {
  $('statusForm').style.display = 'none';
  $('btnAdicionarEvento').disabled = false;
}

async function salvarEvento() {
  const id        = $('statusFormId').value;
  const tipo      = $('statusFormTipo').value;
  const descricao = $('statusFormDescricao').value.trim();
  const local     = $('statusFormLocal').value.trim();
  const dataEv    = $('statusFormData').value;
  const errBox    = $('statusFormErr');

  if (!descricao || descricao.length < 2) {
    errBox.textContent = 'Informe a descrição do evento.';
    errBox.classList.remove('d-none');
    return;
  }
  if (!dataEv) {
    errBox.textContent = 'Informe a data e hora do evento.';
    errBox.classList.remove('d-none');
    return;
  }
  errBox.classList.add('d-none');

  const payload = { tipo, descricao, local: local || null, data_evento: dataEv };
  try {
    const url    = id ? `${API.base}/recepcao/eventos/${id}` : `${API.envios}/${_statusEnvioId}/eventos`;
    const method = id ? 'PUT' : 'POST';
    const r = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.detail || 'HTTP ' + r.status);
    }
    toast(id ? 'Evento atualizado.' : 'Evento adicionado.', 'success');
    cancelarFormEvento();
    await carregarEventos();
    await loadEnvios();
  } catch (err) {
    errBox.textContent = err.message;
    errBox.classList.remove('d-none');
  }
}

async function excluirEvento(eventoId) {
  if (!confirm('Excluir este evento da timeline?')) return;
  try {
    const r = await fetch(`${API.base}/recepcao/eventos/${eventoId}`, { method: 'DELETE' });
    if (!r.ok && r.status !== 204) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.detail || 'HTTP ' + r.status);
    }
    toast('Evento excluído.', 'success');
    await carregarEventos();
    await loadEnvios();
  } catch (err) {
    toast('Erro: ' + err.message, 'error');
  }
}

function openEnvioModal(envioId = null) {
  editandoEnvio = envioId;
  $('envioErr').classList.add('d-none');

  if (envioId) {
    const e = envios.find(x => x.id === envioId);
    if (!e) return;
    $('envioModalTitle').textContent = 'Editar Envio';
    $('envioRemetente').value         = e.remetente_nome || currentUser.name;
    $('envioDestino').value           = e.destino || '';
    $('envioDestinatario').value      = e.destinatario || '';
    $('envioValor').value             = e.valor_mercadoria || 0;
    $('envioCodigo').value            = e.codigo_correios || '';
    $('envioObs').value               = e.observacoes || '';
  } else {
    $('envioModalTitle').textContent = 'Novo Envio';
    $('envioRemetente').value         = currentUser.name;
    $('envioDestino').value           = '';
    $('envioDestinatario').value      = '';
    $('envioValor').value             = 0;
    $('envioCodigo').value            = '';
    $('envioObs').value               = '';
  }

  new bootstrap.Modal($('envioModal')).show();
}

async function submitEnvio() {
  const erro = $('envioErr');
  erro.classList.add('d-none');

  const destino      = $('envioDestino').value.trim();
  const destinatario = $('envioDestinatario').value.trim();
  const valor        = parseFloat($('envioValor').value) || 0;
  const codigoRaw    = $('envioCodigo').value.trim().toUpperCase();
  const observacoes  = $('envioObs').value.trim() || null;

  if (!destino || destino.length < 2) {
    erro.textContent = 'Informe o destino';
    erro.classList.remove('d-none'); return;
  }
  if (!destinatario || destinatario.length < 2) {
    erro.textContent = 'Informe o destinatário';
    erro.classList.remove('d-none'); return;
  }
  if (codigoRaw && !/^[A-Z]{2}\d{9}[A-Z]{2}$/.test(codigoRaw)) {
    erro.textContent = 'Código dos Correios inválido (formato AA123456789BR)';
    erro.classList.remove('d-none'); return;
  }

  const payload = {
    destino, destinatario,
    valor_mercadoria: valor,
    codigo_correios: codigoRaw || null,
    observacoes,
  };
  let url    = API.envios;
  let method = 'POST';

  if (editandoEnvio) {
    url    = API.envios + '/' + editandoEnvio;
    method = 'PUT';
  } else {
    payload.remetente_id = currentUser.id;
  }

  try {
    const r = await fetch(url, {
      method, headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.detail || 'HTTP ' + r.status);
    }
    bootstrap.Modal.getInstance($('envioModal')).hide();
    toast(editandoEnvio ? 'Envio atualizado' : 'Envio cadastrado', 'success');
    await loadEnvios();
  } catch (err) {
    erro.textContent = err.message;
    erro.classList.remove('d-none');
  }
}

async function deletarEnvio(id) {
  if (!confirm('Excluir este envio?')) return;
  try {
    const r = await fetch(`${API.envios}/${id}`, { method: 'DELETE' });
    if (!r.ok && r.status !== 204) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.detail || 'HTTP ' + r.status);
    }
    toast('Envio removido', 'success');
    await loadEnvios();
  } catch (err) {
    toast('Erro: ' + err.message, 'error');
  }
}


/* expõe funções para os onclicks inline */
window.showSection         = showSection;
window.toggleSidebar       = function() {
  const sb = document.getElementById('recepSidebar');
  const ct = document.getElementById('recepContent');
  const ic = document.getElementById('sidebarToggleIcon');
  sb.classList.toggle('collapsed');
  ct.classList.toggle('sidebar-collapsed');
  if (ic) {
    const collapsed = sb.classList.contains('collapsed');
    ic.className = collapsed ? 'bi bi-layout-sidebar' : 'bi bi-layout-sidebar-reverse';
  }
};
window.openReservaModal    = openReservaModal;
window.submitReserva       = submitReserva;
window.confirmarReserva    = confirmarReserva;
window.cancelarReserva     = cancelarReserva;
window.openSalaModal       = openSalaModal;
window.submitSala          = submitSala;
window.deletarSala         = deletarSala;
window.agendarPara         = agendarPara;
window.openEnvioModal      = openEnvioModal;
window.submitEnvio         = submitEnvio;
window.deletarEnvio        = deletarEnvio;
window.abrirRastreio       = abrirRastreio;
window.rastrearEnvioRecarregar = rastrearEnvioRecarregar;
window.atualizarStatusManual = atualizarStatusManual;
window.abrirFormEvento     = abrirFormEvento;
window.cancelarFormEvento  = cancelarFormEvento;
window.salvarEvento        = salvarEvento;
window.excluirEvento       = excluirEvento;
window.onResvUnitChange         = onResvUnitChange;
window.onResvEscritorioChange   = onResvEscritorioChange;
window.onSalaUnitChange         = onSalaUnitChange;
window.onFilterCalendar         = onFilterCalendar;
window.onFilterSalaUnitChange   = onFilterSalaUnitChange;
window.loadSalas           = loadSalas;
window.renderEnvios        = renderEnvios;
window.abrirReservaPorId   = abrirReservaPorId;
window.responderConvite    = responderConvite;
window.filtrarConvidados   = filtrarConvidados;
