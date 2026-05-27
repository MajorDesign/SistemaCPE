/* =====================================================================
   Equipe de Suporte — agendas de atendimento
   SPA: dashboard, lista de agendas, calendário e configuração de horários.
   ===================================================================== */

const API_HOST = (typeof API_BASE_URL !== 'undefined') ? API_BASE_URL : 'http://127.0.0.1:8000';
const API = API_HOST + '/api/atendimentos';

const DIAS = ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'];
const DIAS_ABREV = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb'];
const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
const HORA_INI = 6, HORA_FIM = 21, ROW_H = 48;   // grade do calendário

/* estado */
let agendas = [];
let agendaAtual = null;
let calView = 'semana';
let calRef = new Date();              // âncora do período exibido
let calAgendamentos = [];
let calBloqueios = [];
let calFeriados = [];                 // feriados do período exibido
let chartAg = null, chartAt = null;
let servicosAgenda = [];     // serviços da agenda aberta (modal de agendamento)
let vendedoresList = [];     // usuários do grupo Comercial
let cursosSecao = [];        // cursos exibidos na seção Cursos
let cursosPreselect = null;  // agenda a pré-selecionar ao abrir a seção Cursos

/* ============ AUTH / API ============ */
function _token() {
  return localStorage.getItem('cpe_token') || sessionStorage.getItem('cpe_token') || '';
}
async function apiFetch(path, options = {}) {
  try {
    const res = await fetch(API + path, {
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-Auth-Token': _token(),
        ...(options.headers || {}),
      },
      ...options,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      return { success: false, detail: err.detail || 'Erro na requisição' };
    }
    return await res.json();
  } catch (e) {
    console.error('[SUP API]', e);
    return { success: false, detail: 'Erro de conexão com o servidor' };
  }
}

/* ============ TOAST ============ */
function toast(msg, tipo = 'info') {
  const box = document.getElementById('supToast');
  const el = document.createElement('div');
  el.className = 'sup-toast-item ' + tipo;
  el.textContent = msg;
  box.appendChild(el);
  setTimeout(() => el.remove(), 3600);
}

/* ============ HELPERS DE DATA ============ */
function pad(n) { return String(n).padStart(2, '0'); }
function ymd(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
function hm(d) { return pad(d.getHours()) + ':' + pad(d.getMinutes()); }
function ymdhm(d) { return ymd(d) + 'T' + hm(d); }
function parseDT(s) { return s ? new Date(String(s).replace(' ', 'T')) : null; }
function mesmoDia(a, b) { return ymd(a) === ymd(b); }
function inicioSemana(d) {
  const r = new Date(d); r.setHours(0, 0, 0, 0);
  r.setDate(r.getDate() - r.getDay());          // domingo
  return r;
}

/* ============ MODAIS ============ */
function abrirModal(id) { document.getElementById(id).classList.add('show'); }
function fecharModal(id) { document.getElementById(id).classList.remove('show'); }
function setErro(id, msg) {
  const el = document.getElementById(id);
  if (msg) { el.textContent = msg; el.style.display = 'block'; }
  else { el.style.display = 'none'; }
}

/* ============ NAVEGAÇÃO ============ */
const TITULOS_SECAO = {
  dashboard: 'Dashboard', agendas: 'Agendas', calendario: 'Calendário',
  cursos: 'Cursos', equipamentos: 'Equipamentos', feriados: 'Feriados',
};
function showSection(name) {
  document.querySelectorAll('.sup-page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  document.querySelectorAll('.sup-nav-item').forEach(n =>
    n.classList.toggle('active', n.dataset.section === name));
  document.getElementById('topbarTitle').textContent = TITULOS_SECAO[name] || '';
  document.getElementById('supSidebar').classList.remove('show');
  if (name === 'dashboard') loadDashboard();
  else if (name === 'agendas') initSecaoAgendas();
  else if (name === 'calendario') initSecaoCalendario();
  else if (name === 'cursos') initSecaoCursos();
  else if (name === 'equipamentos') initSecaoEquipamentos();
  else if (name === 'feriados') initSecaoFeriados();
}

/* ============ DASHBOARD ============ */
async function loadDashboard() {
  const d = await apiFetch('/dashboard');
  if (!d.success) { toast(d.detail || 'Falha ao carregar dashboard', 'error'); return; }
  document.getElementById('stHoje').textContent = d.agendamentos_hoje;
  document.getElementById('stAmanha').textContent = d.agendamentos_amanha;
  document.getElementById('stAgendas').textContent = d.total_agendas;
  document.getElementById('stPendentes').textContent = d.pendentes || 0;
  renderCharts(d.series_mensal || []);
  await loadAgendas();
}

function ultimos12Meses() {
  const arr = [], hoje = new Date();
  for (let i = 11; i >= 0; i--) {
    const d = new Date(hoje.getFullYear(), hoje.getMonth() - i, 1);
    arr.push({ key: d.getFullYear() + '-' + pad(d.getMonth() + 1),
               label: MESES[d.getMonth()] + '/' + String(d.getFullYear()).slice(2) });
  }
  return arr;
}

function renderCharts(series) {
  const meses = ultimos12Meses();
  const mapa = {};
  series.forEach(s => { mapa[s.mes] = s; });
  const labels = meses.map(m => m.label);
  const totais = meses.map(m => mapa[m.key] ? Number(mapa[m.key].total) : 0);
  const atend = meses.map(m => mapa[m.key] ? Number(mapa[m.key].atendidos || 0) : 0);

  if (chartAg) chartAg.destroy();
  chartAg = new Chart(document.getElementById('chartAgendamentos'), {
    type: 'line',
    data: { labels, datasets: [{
      label: 'Agendamentos', data: totais, fill: true,
      borderColor: '#0d9488', backgroundColor: 'rgba(13,148,136,.15)', tension: .35,
    }] },
    options: { responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
  });

  if (chartAt) chartAt.destroy();
  chartAt = new Chart(document.getElementById('chartAtendidos'), {
    type: 'bar',
    data: { labels, datasets: [{
      label: 'Atendidos', data: atend, backgroundColor: '#22c55e',
    }] },
    options: { responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
  });
}

async function loadAgendas() {
  const d = await apiFetch('/agendas?incluir_inativas=1');
  agendas = d.success ? (d.agendas || []) : [];
  renderAgendasTabela();
  renderAgendasCards();
}

/* ============ SEÇÃO AGENDAS (config por unidade) ============ */
async function initSecaoAgendas() {
  if (!agendas.length) await loadAgendas();
  else renderAgendasCards();
}

function renderAgendasCards() {
  const grid = document.getElementById('gridAgendas');
  if (!grid) return;
  if (!agendas.length) {
    grid.innerHTML = '<div class="sup-empty">Nenhuma agenda cadastrada. Clique em "Nova agenda".</div>';
    return;
  }
  grid.innerHTML = agendas.map(a => {
    const status = a.ativo ? '<span class="sup-pill ok">Ativa</span>'
                           : '<span class="sup-pill off">Inativa</span>';
    const temHorarios = (a.capacidade_prox7 || 0) > 0;
    return `<div class="sup-agenda-card" style="border-left-color:${a.cor || '#0d9488'}">
      <div style="display:flex;justify-content:space-between;gap:8px;align-items:start">
        <h3>${esc(a.nome)}</h3>${status}
      </div>
      <div class="sup-ag-meta">
        <span><i class="bi bi-geo-alt"></i> ${a.unidade_nome ? esc(a.unidade_nome) : 'Sem unidade vinculada'}</span>
        <span><i class="bi bi-clock"></i> ${temHorarios ? 'Horários configurados'
                                                        : 'Sem horários configurados'}</span>
        <span><i class="bi bi-calendar-check"></i> ${a.agendamentos_prox7} agendamento(s) nos próximos 7 dias</span>
      </div>
      <div class="sup-ag-acoes">
        <button class="btn-sup btn-sup-primary btn-sup-sm" onclick="abrirAgenda(${a.id})">
          <i class="bi bi-calendar3"></i> Calendário</button>
        <button class="btn-sup btn-sup-ghost btn-sup-sm" onclick="configHorariosDe(${a.id})">
          <i class="bi bi-gear"></i> Horários</button>
        <button class="btn-sup btn-sup-ghost btn-sup-sm" onclick="irParaCursos(${a.id})">
          <i class="bi bi-mortarboard"></i> Cursos</button>
        <button class="btn-sup btn-sup-ghost btn-sup-sm" onclick="abrirModalAgenda(${a.id})">
          <i class="bi bi-pencil"></i> Editar</button>
        <button class="btn-sup btn-sup-${a.ativo ? 'danger' : 'primary'} btn-sup-sm"
          onclick="toggleAgenda(${a.id})">
          <i class="bi bi-power"></i> ${a.ativo ? 'Desativar' : 'Ativar'}</button>
      </div>
    </div>`;
  }).join('');
}

/* ============ LINK PUBLICO ============ */
// Link sempre aponta pro dominio publico — eh o que o cliente vai usar,
// independentemente de onde o admin esteja acessando (local, IP, dominio).
const PUBLIC_AGENDAR_URL =
  'https://cpecontrol.cpetecnologia.com.br/SistemaCPE/web/pages/agendar.html';

function _urlAgendarPublico() {
  return PUBLIC_AGENDAR_URL;
}

async function copiarLinkPublico() {
  const url = _urlAgendarPublico();
  try {
    await navigator.clipboard.writeText(url);
    toast('Link copiado: ' + url, 'success');
  } catch (e) {
    // fallback se o clipboard API falhar (HTTP, browser antigo)
    const tmp = document.createElement('textarea');
    tmp.value = url; document.body.appendChild(tmp);
    tmp.select(); document.execCommand('copy'); tmp.remove();
    toast('Link copiado: ' + url, 'success');
  }
}

function abrirLinkPublico() {
  window.open(_urlAgendarPublico(), '_blank', 'noopener');
}

function configHorariosDe(id) {
  agendaAtual = agendas.find(a => a.id === id) || null;
  if (agendaAtual) abrirConfigHorarios();
}

function irParaCursos(id) {
  cursosPreselect = id;
  showSection('cursos');
}

async function toggleAgenda(id) {
  const a = agendas.find(x => x.id === id);
  if (!a) return;
  if (!confirm(a.ativo
      ? 'Desativar esta agenda? Ela deixa de aparecer na página pública de agendamento.'
      : 'Reativar esta agenda?')) return;
  const r = await apiFetch('/agendas/' + id, { method: 'PUT', body: JSON.stringify({
    nome: a.nome, unidade_id: a.unidade_id, descricao: a.descricao,
    instrucoes: a.instrucoes, cor: a.cor, slot_duracao_min: a.slot_duracao_min,
    ativo: !a.ativo,
  }) });
  if (!r.success) { toast(r.detail || 'Erro ao atualizar.', 'error'); return; }
  toast(a.ativo ? 'Agenda desativada.' : 'Agenda ativada.', 'success');
  await loadAgendas();
}

function renderAgendasTabela() {
  const busca = (document.getElementById('buscaAgenda').value || '').toLowerCase();
  const tbody = document.getElementById('tbodyAgendas');
  const lista = agendas.filter(a => a.nome.toLowerCase().includes(busca));
  if (!lista.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="sup-empty">' +
      (agendas.length ? 'Nenhuma agenda encontrada.' : 'Nenhuma agenda cadastrada. Clique em "Nova agenda".') +
      '</td></tr>';
    return;
  }
  tbody.innerHTML = lista.map(a => {
    let ocup;
    if (a.taxa_ocupacao === null || a.taxa_ocupacao === undefined)
      ocup = '<span style="color:#9ca3af">Sem horários</span>';
    else ocup = a.taxa_ocupacao + '%';
    const status = a.ativo
      ? '<span class="sup-pill ok">Ativa</span>'
      : '<span class="sup-pill off">Inativa</span>';
    return `<tr>
      <td><span class="sup-link" onclick="abrirAgenda(${a.id})">${esc(a.nome)}</span></td>
      <td>${a.unidade_nome ? esc(a.unidade_nome) : '—'}</td>
      <td>${a.agendamentos_hoje}</td>
      <td>${a.agendamentos_amanha}</td>
      <td>${a.agendamentos_prox7}</td>
      <td>${ocup}</td>
      <td>${status}</td>
      <td><button class="btn-sup btn-sup-ghost btn-sup-sm" onclick="abrirModalAgenda(${a.id})">
        <i class="bi bi-pencil"></i></button></td>
    </tr>`;
  }).join('');
}

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g,
    c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[c]));
}

/* ============ AGENDA — CRUD ============ */
async function carregarUnidades() {
  try {
    const r = await fetch(API_HOST + '/api/unidades/?somente_ativas=true');
    if (!r.ok) return;
    const us = await r.json();
    const sel = document.getElementById('agUnidade');
    sel.innerHTML = '<option value="">— Nenhuma —</option>' +
      us.map(u => `<option value="${u.id}">${esc(u.nome)}</option>`).join('');
  } catch (e) { console.warn('[SUP] unidades:', e.message); }
}

function abrirModalAgenda(id) {
  setErro('erroAgenda', '');
  const a = id ? agendas.find(x => x.id === id) : null;
  document.getElementById('modalAgendaTitulo').textContent = a ? 'Editar agenda' : 'Nova agenda';
  document.getElementById('agendaId').value = a ? a.id : '';
  document.getElementById('agNome').value = a ? a.nome : '';
  document.getElementById('agTipo').value = a && a.tipo ? a.tipo : 'fisica';
  document.getElementById('agUnidade').value = a && a.unidade_id ? a.unidade_id : '';
  document.getElementById('agDuracao').value = a ? a.slot_duracao_min : 30;
  onAgTipoChange();
  document.getElementById('agCor').value = a ? (a.cor || '#0d9488') : '#0d9488';
  document.getElementById('agAtivo').value = a ? (a.ativo ? '1' : '0') : '1';
  document.getElementById('agDescricao').value = a && a.descricao ? a.descricao : '';
  document.getElementById('agInstrucoes').value = a && a.instrucoes ? a.instrucoes : '';
  document.getElementById('btnExcluirAgenda').style.display = a ? 'inline-flex' : 'none';
  abrirModal('modalAgenda');
}

function onAgTipoChange() {
  const tipo = document.getElementById('agTipo').value;
  const sel = document.getElementById('agUnidade');
  if (tipo === 'online') {
    sel.value = '';
    sel.disabled = true;
  } else {
    sel.disabled = false;
  }
}

async function salvarAgenda() {
  const id = document.getElementById('agendaId').value;
  const tipo = document.getElementById('agTipo').value;
  const payload = {
    nome: document.getElementById('agNome').value.trim(),
    tipo: tipo === 'online' ? 'online' : 'fisica',
    // agenda online nao se vincula a unidade fisica
    unidade_id: tipo === 'online' ? null : (document.getElementById('agUnidade').value || null),
    slot_duracao_min: parseInt(document.getElementById('agDuracao').value) || 30,
    cor: document.getElementById('agCor').value,
    ativo: document.getElementById('agAtivo').value === '1',
    descricao: document.getElementById('agDescricao').value.trim(),
    instrucoes: document.getElementById('agInstrucoes').value.trim(),
  };
  if (!payload.nome) { setErro('erroAgenda', 'Informe o nome da agenda.'); return; }
  const r = id
    ? await apiFetch('/agendas/' + id, { method: 'PUT', body: JSON.stringify(payload) })
    : await apiFetch('/agendas', { method: 'POST', body: JSON.stringify(payload) });
  if (!r.success) { setErro('erroAgenda', r.detail || 'Erro ao salvar.'); return; }
  fecharModal('modalAgenda');
  toast(id ? 'Agenda atualizada.' : 'Agenda criada.', 'success');
  await loadAgendas();
}

async function excluirAgenda() {
  const id = document.getElementById('agendaId').value;
  if (!id) return;
  if (!confirm('Excluir esta agenda? Todos os horários e atendimentos dela serão removidos.')) return;
  const r = await apiFetch('/agendas/' + id, { method: 'DELETE' });
  if (!r.success) { setErro('erroAgenda', r.detail || 'Erro ao excluir.'); return; }
  fecharModal('modalAgenda');
  toast('Agenda excluída.', 'success');
  await loadAgendas();
}

/* ============ ABRIR CALENDÁRIO DE UMA AGENDA ============ */
function abrirAgenda(id) {
  // define a agenda e entra no Calendário — initSecaoCalendario faz o resto
  agendaAtual = agendas.find(a => a.id === id) || null;
  showSection('calendario');
}

async function initSecaoCalendario() {
  if (!agendas.length) await loadAgendas();
  const sel = document.getElementById('calAgendaSel');
  if (!agendas.length) {
    sel.innerHTML = '<option value="">Nenhuma agenda</option>';
    document.getElementById('calContainer').innerHTML =
      '<div class="sup-card sup-empty">Crie uma agenda no Dashboard primeiro.</div>';
    document.getElementById('calPeriodo').textContent = '—';
    agendaAtual = null;
    return;
  }
  sel.innerHTML = agendas.map(a => `<option value="${a.id}">${esc(a.nome)}</option>`).join('');
  if (!agendaAtual || !agendas.some(a => a.id === agendaAtual.id)) agendaAtual = agendas[0];
  sel.value = agendaAtual.id;
  await _selecionarAgendaCalendario();
}

async function onCalAgendaChange() {
  const id = parseInt(document.getElementById('calAgendaSel').value);
  agendaAtual = agendas.find(a => a.id === id) || null;
  await _selecionarAgendaCalendario();
}

async function _selecionarAgendaCalendario() {
  if (!agendaAtual) return;
  calRef = new Date();
  await carregarServicosAgenda();
  if (!vendedoresList.length) {
    const v = await apiFetch('/vendedores');
    vendedoresList = v.success ? (v.vendedores || []) : [];
  }
  carregarCalendario();
}

async function carregarServicosAgenda() {
  if (!agendaAtual) { servicosAgenda = []; return; }
  const r = await apiFetch('/agendas/' + agendaAtual.id + '/servicos');
  servicosAgenda = r.success ? (r.servicos || []) : [];
}

/* ============ CALENDÁRIO ============ */
function mudarView(v) {
  calView = v;
  document.querySelectorAll('.sup-cal-views button').forEach(b =>
    b.classList.toggle('active', b.dataset.view === v));
  carregarCalendario();
}
function navPeriodo(dir) {
  if (calView === 'semana') calRef.setDate(calRef.getDate() + dir * 7);
  else if (calView === 'mes') calRef.setMonth(calRef.getMonth() + dir);
  else calRef.setDate(calRef.getDate() + dir);
  calRef = new Date(calRef);
  carregarCalendario();
}
function hojePeriodo() { calRef = new Date(); carregarCalendario(); }

function rangePeriodo() {
  if (calView === 'mes') {
    const ini = new Date(calRef.getFullYear(), calRef.getMonth(), 1);
    const fim = new Date(calRef.getFullYear(), calRef.getMonth() + 1, 0);
    return { ini, fim };
  }
  if (calView === 'semana') {
    const ini = inicioSemana(calRef);
    const fim = new Date(ini); fim.setDate(fim.getDate() + 6);
    return { ini, fim };
  }
  return { ini: new Date(calRef), fim: new Date(calRef) };  // dia / lista
}

async function carregarCalendario() {
  if (!agendaAtual) return;
  const { ini, fim } = rangePeriodo();
  const r = await apiFetch(
    `/agendas/${agendaAtual.id}/agendamentos?inicio=${ymd(ini)}&fim=${ymd(fim)}`);
  calAgendamentos = r.success ? (r.agendamentos || []) : [];
  calBloqueios = r.success ? (r.bloqueios || []) : [];
  calFeriados = r.success ? (r.feriados || []) : [];
  if (!r.success) toast(r.detail || 'Falha ao carregar atendimentos', 'error');
  renderCalendario();
}

/* Retorna o feriado que cai no dia `d` (Date) ou null. */
function feriadoDoDia(d) {
  const k = ymd(d);
  return calFeriados.find(f => String(f.data).slice(0, 10) === k) || null;
}

function renderCalendario() {
  const { ini, fim } = rangePeriodo();
  const cont = document.getElementById('calContainer');
  const per = document.getElementById('calPeriodo');
  if (calView === 'semana') {
    per.textContent = `${ini.getDate()} – ${fim.getDate()} de ${MESES[fim.getMonth()]}. ${fim.getFullYear()}`;
    cont.innerHTML = gridSemana(ini);
  } else if (calView === 'dia') {
    per.textContent = `${DIAS[calRef.getDay()]}, ${calRef.getDate()} de ${MESES[calRef.getMonth()]}.`;
    cont.innerHTML = gridSemana(calRef, true);
  } else if (calView === 'mes') {
    per.textContent = `${MESES[calRef.getMonth()]} de ${calRef.getFullYear()}`;
    cont.innerHTML = gridMes();
  } else {
    per.textContent = `${DIAS[calRef.getDay()]}, ${calRef.getDate()} de ${MESES[calRef.getMonth()]}.`;
    cont.innerHTML = listaDia();
  }
}

/* eventos que tocam um dia */
function eventosDoDia(d) {
  return calAgendamentos.filter(a => {
    const i = parseDT(a.inicio);
    return i && mesmoDia(i, d);
  }).sort((a, b) => parseDT(a.inicio) - parseDT(b.inicio));
}

/* posição vertical de um horário na grade */
function topoPx(dt) {
  let h = dt.getHours() + dt.getMinutes() / 60;
  if (h < HORA_INI) h = HORA_INI;
  if (h > HORA_FIM) h = HORA_FIM;
  return (h - HORA_INI) * ROW_H;
}

function gridSemana(refDate, soUmDia = false) {
  const dias = [];
  if (soUmDia) {
    dias.push(new Date(refDate));
  } else {
    const ini = inicioSemana(refDate);
    for (let i = 0; i < 7; i++) {
      const d = new Date(ini); d.setDate(d.getDate() + i); dias.push(d);
    }
  }
  const hoje = new Date();
  const cols = `56px repeat(${dias.length}, 1fr)`;

  let head = '<div class="sup-week-corner"></div>';
  dias.forEach(d => {
    const t = mesmoDia(d, hoje) ? ' today' : '';
    const fer = feriadoDoDia(d);
    const f = fer ? ' feriado' : '';
    const tip = fer ? ` title="Feriado: ${esc(fer.nome)}"` : '';
    head += `<div class="sup-week-head${t}${f}"${tip}>${DIAS_ABREV[d.getDay()]}. ${d.getDate()}` +
      (fer ? ' <i class="bi bi-calendar-x"></i>' : '') + '</div>';
  });

  let horas = '<div class="sup-week-hours">';
  for (let h = HORA_INI; h < HORA_FIM; h++) horas += `<div class="sup-hour-label">${pad(h)}:00</div>`;
  horas += '</div>';

  let colunas = '';
  dias.forEach(d => {
    const t = mesmoDia(d, hoje) ? ' today' : '';
    const fer = feriadoDoDia(d);
    let cells = '';
    for (let h = HORA_INI; h < HORA_FIM; h++) cells += '<div class="sup-hour-cell"></div>';

    // bloqueios do dia
    let blocos = '';
    calBloqueios.forEach(b => {
      const bi = parseDT(b.inicio), bf = parseDT(b.fim);
      if (!bi || !mesmoDia(bi, d)) return;
      const top = topoPx(bi), alt = Math.max(16, topoPx(bf) - top);
      blocos += `<div class="sup-event-block" style="top:${top}px;height:${alt}px"
        title="Bloqueado: ${esc(b.motivo || '')}"></div>`;
    });

    // agendamentos do dia
    let eventos = '';
    eventosDoDia(d).forEach(a => {
      const ai = parseDT(a.inicio), af = parseDT(a.fim);
      const top = topoPx(ai), alt = Math.max(22, topoPx(af) - top);
      const cor = (agendaAtual && agendaAtual.cor) || '#0d9488';
      eventos += `<div class="sup-event ${a.status}" style="top:${top}px;height:${alt}px;background:${cor}"
        onclick="abrirModalAgendamento(${a.id})">
        <strong>${hm(ai)}</strong> ${esc(a.titulo)}${a.cliente_nome ? ' — ' + esc(a.cliente_nome) : ''}
      </div>`;
    });

    // overlay de feriado — cobre a coluna inteira
    let overlay = '';
    if (fer) {
      const rot = fer.agenda_id ? (_capitaliza(fer.tipo) || 'Local') : 'Nacional';
      overlay = `<div class="sup-feriado-overlay" title="Feriado (${esc(rot)}): ${esc(fer.nome)}">
        <i class="bi bi-calendar-x"></i>
        <strong>Feriado</strong>
        <span>${esc(fer.nome)}</span>
      </div>`;
    }

    const cls = `sup-day-col${t}${fer ? ' feriado' : ''}`;
    const dblclick = fer ? '' : ` ondblclick="novoAgendamentoEm('${ymd(d)}')"`;
    colunas += `<div class="${cls}"${dblclick}>
      ${cells}${blocos}${eventos}${overlay}</div>`;
  });

  return `<div class="sup-week" style="grid-template-columns:${cols}">
    ${head}${horas}${colunas}</div>
    <p class="sup-help" style="margin-top:8px">Dois cliques numa coluna para incluir um atendimento.</p>`;
}

function gridMes() {
  const ano = calRef.getFullYear(), mes = calRef.getMonth();
  const primeiro = new Date(ano, mes, 1);
  const ini = inicioSemana(primeiro);
  const hoje = new Date();
  let html = '<div class="sup-week" style="grid-template-columns:repeat(7,1fr)">';
  DIAS_ABREV.forEach(d => { html += `<div class="sup-week-head">${d}</div>`; });
  let cursor = new Date(ini);
  for (let s = 0; s < 6; s++) {
    for (let i = 0; i < 7; i++) {
      const evs = eventosDoDia(cursor);
      const foraMes = cursor.getMonth() !== mes;
      const isHoje = mesmoDia(cursor, hoje);
      const fer = feriadoDoDia(cursor);
      const cor = (agendaAtual && agendaAtual.cor) || '#0d9488';
      let chips = evs.slice(0, 3).map(a =>
        `<div class="sup-event ${a.status}" style="position:static;margin:2px 0;background:${cor}"
          onclick="abrirModalAgendamento(${a.id})">${hm(parseDT(a.inicio))} ${esc(a.titulo)}</div>`).join('');
      if (evs.length > 3) chips += `<div class="sup-help">+${evs.length - 3} mais</div>`;
      const ferTag = fer
        ? `<div class="sup-feriado-tag" title="Feriado: ${esc(fer.nome)}">
            <i class="bi bi-calendar-x"></i> ${esc(fer.nome)}</div>`
        : '';
      const cls = `sup-day-col${isHoje ? ' today' : ''}${fer ? ' feriado' : ''}`;
      const dblclick = fer ? '' : ` ondblclick="novoAgendamentoEm('${ymd(cursor)}')"`;
      html += `<div class="${cls}"
        style="min-height:104px;padding:4px;${foraMes ? 'opacity:.45' : ''}"${dblclick}>
        <div style="font-weight:600;font-size:.8rem">${cursor.getDate()}</div>${ferTag}${chips}</div>`;
      cursor = new Date(cursor); cursor.setDate(cursor.getDate() + 1);
    }
  }
  html += '</div>';
  return html;
}

function listaDia() {
  const evs = eventosDoDia(calRef);
  if (!evs.length)
    return '<div class="sup-card sup-empty">Nenhum atendimento neste dia.</div>';
  return evs.map(a => {
    const ai = parseDT(a.inicio), af = parseDT(a.fim);
    return `<div class="sup-list-item" onclick="abrirModalAgendamento(${a.id})">
      <span class="sup-list-time">${hm(ai)} – ${hm(af)}</span>
      <div style="flex:1">
        <div style="font-weight:600">${esc(a.titulo)}</div>
        <div class="sup-help">${a.cliente_nome ? esc(a.cliente_nome) : 'Sem cliente'}</div>
      </div>
      <span class="sup-pill ${a.status}">${rotuloStatus(a.status)}</span>
    </div>`;
  }).join('');
}

function rotuloStatus(s) {
  return { pendente: 'Pendente', agendado: 'Agendado', atendido: 'Atendido',
           cancelado: 'Cancelado', nao_compareceu: 'Não compareceu' }[s] || s;
}

/* ============ AGENDAMENTO — CRUD ============ */
async function novoAgendamentoEm(dataStr) {
  // bloqueia tentativa de criar atendimento em feriado (defesa de UX,
  // o backend tambem rejeita via _checar_vaga em atendimentos.py)
  const dia = new Date(dataStr + 'T00:00');
  const fer = feriadoDoDia(dia);
  if (fer) {
    toast(`Esse dia e feriado (${fer.nome}). A agenda fica trancada.`, 'error');
    return;
  }
  await abrirModalAgendamento();
  const dur = (agendaAtual && agendaAtual.slot_duracao_min) || 30;
  document.getElementById('agtInicio').value = dataStr + 'T09:00';
  const fim = new Date(dataStr + 'T09:00');
  fim.setMinutes(fim.getMinutes() + dur);
  document.getElementById('agtFim').value = ymdhm(fim);
}

function _preencherSelectServicos() {
  document.getElementById('agtServico').innerHTML =
    '<option value="">— Sem serviço —</option>' +
    servicosAgenda.map(s => `<option value="${s.id}">${esc(s.nome)} (${s.duracao_min}min)</option>`).join('');
}
function _preencherSelectVendedores() {
  document.getElementById('agtVendedor').innerHTML =
    '<option value="">—</option>' +
    vendedoresList.map(v => `<option value="${v.id}">${esc(v.name)}</option>`).join('');
}
async function _carregarEquipSelect(servicoId, selecionado) {
  const sel = document.getElementById('agtEquipamento');
  sel.innerHTML = '<option value="">—</option>';
  if (!servicoId) return;
  const r = await apiFetch('/servicos/' + servicoId + '/equipamentos');
  if (r.success) {
    sel.innerHTML = '<option value="">—</option>' +
      (r.equipamentos || []).filter(e => e.ativo)
        .map(e => `<option value="${e.id}">${esc(e.nome)}</option>`).join('');
  }
  if (selecionado) sel.value = selecionado;
}

async function onAgtServicoChange() {
  const sid = document.getElementById('agtServico').value;
  await _carregarEquipSelect(sid);
  if (!sid) return;
  const s = servicosAgenda.find(x => x.id == sid);
  if (!s) return;
  const tit = document.getElementById('agtTitulo');
  if (!tit.value.trim()) tit.value = s.nome;
  const ini = document.getElementById('agtInicio').value;
  if (ini) {
    const f = new Date(ini);
    f.setMinutes(f.getMinutes() + s.duracao_min);
    document.getElementById('agtFim').value = ymdhm(f);
  }
}

async function abrirModalAgendamento(id) {
  if (!agendaAtual) { toast('Abra uma agenda primeiro.', 'error'); return; }
  setErro('erroAg', '');
  const a = id ? calAgendamentos.find(x => x.id === id) : null;
  document.getElementById('modalAgTitulo').textContent = a ? 'Editar atendimento' : 'Novo atendimento';
  _preencherSelectServicos();
  _preencherSelectVendedores();
  document.getElementById('agtId').value = a ? a.id : '';
  document.getElementById('agtServico').value = a && a.servico_id ? a.servico_id : '';
  document.getElementById('agtTitulo').value = a ? a.titulo : '';
  document.getElementById('agtCliente').value = a && a.cliente_nome ? a.cliente_nome : '';
  document.getElementById('agtEmail').value = a && a.cliente_email ? a.cliente_email : '';
  document.getElementById('agtTelefone').value = a && a.cliente_telefone ? a.cliente_telefone : '';
  document.getElementById('agtInicio').value = a ? ymdhm(parseDT(a.inicio)) : '';
  document.getElementById('agtFim').value = a ? ymdhm(parseDT(a.fim)) : '';
  document.getElementById('agtModalidade').value = a && a.modalidade ? a.modalidade : '';
  document.getElementById('agtTipo').value = a && a.tipo_negocio ? a.tipo_negocio : '';
  document.getElementById('agtVendedor').value = a && a.vendedor_id ? a.vendedor_id : '';
  document.getElementById('agtStatus').value = a ? a.status : 'agendado';
  document.getElementById('agtObs').value = a && a.observacoes ? a.observacoes : '';
  document.getElementById('btnExcluirAg').style.display = a ? 'inline-flex' : 'none';
  await _carregarEquipSelect(a && a.servico_id ? a.servico_id : '',
                             a && a.equipamento_id ? a.equipamento_id : '');
  abrirModal('modalAgendamento');
}

async function salvarAgendamento() {
  const id = document.getElementById('agtId').value;
  const payload = {
    agenda_id: agendaAtual.id,
    servico_id: document.getElementById('agtServico').value || null,
    equipamento_id: document.getElementById('agtEquipamento').value || null,
    titulo: document.getElementById('agtTitulo').value.trim(),
    cliente_nome: document.getElementById('agtCliente').value.trim(),
    cliente_email: document.getElementById('agtEmail').value.trim(),
    cliente_telefone: document.getElementById('agtTelefone').value.trim(),
    inicio: document.getElementById('agtInicio').value,
    fim: document.getElementById('agtFim').value,
    modalidade: document.getElementById('agtModalidade').value || null,
    tipo_negocio: document.getElementById('agtTipo').value || null,
    vendedor_id: document.getElementById('agtVendedor').value || null,
    status: document.getElementById('agtStatus').value,
    observacoes: document.getElementById('agtObs').value.trim(),
  };
  if (!payload.titulo) { setErro('erroAg', 'Informe o título ou escolha um serviço.'); return; }
  if (!payload.inicio || !payload.fim) { setErro('erroAg', 'Informe início e fim.'); return; }
  const r = id
    ? await apiFetch('/agendamentos/' + id, { method: 'PUT', body: JSON.stringify(payload) })
    : await apiFetch('/agendamentos', { method: 'POST', body: JSON.stringify(payload) });
  if (!r.success) { setErro('erroAg', r.detail || 'Erro ao salvar.'); return; }
  fecharModal('modalAgendamento');
  toast(id ? 'Atendimento atualizado.' : 'Atendimento criado.', 'success');
  carregarCalendario();
}

async function excluirAgendamento() {
  const id = document.getElementById('agtId').value;
  if (!id || !confirm('Excluir este atendimento?')) return;
  const r = await apiFetch('/agendamentos/' + id, { method: 'DELETE' });
  if (!r.success) { setErro('erroAg', r.detail || 'Erro ao excluir.'); return; }
  fecharModal('modalAgendamento');
  toast('Atendimento excluído.', 'success');
  carregarCalendario();
}

/* ============ BLOQUEIO ============ */
function abrirModalBloqueio() {
  if (!agendaAtual) { toast('Abra uma agenda primeiro.', 'error'); return; }
  setErro('erroBloq', '');
  document.getElementById('bloqInicio').value = '';
  document.getElementById('bloqFim').value = '';
  document.getElementById('bloqMotivo').value = '';
  abrirModal('modalBloqueio');
}
async function salvarBloqueio() {
  const payload = {
    agenda_id: agendaAtual.id,
    inicio: document.getElementById('bloqInicio').value,
    fim: document.getElementById('bloqFim').value,
    motivo: document.getElementById('bloqMotivo').value.trim(),
  };
  if (!payload.inicio || !payload.fim) { setErro('erroBloq', 'Informe início e fim.'); return; }
  const r = await apiFetch('/bloqueios', { method: 'POST', body: JSON.stringify(payload) });
  if (!r.success) { setErro('erroBloq', r.detail || 'Erro ao bloquear.'); return; }
  fecharModal('modalBloqueio');
  toast('Horário bloqueado.', 'success');
  carregarCalendario();
}

/* ============ CONFIGURAR HORÁRIOS ============ */
async function abrirConfigHorarios() {
  if (!agendaAtual) { toast('Abra uma agenda primeiro.', 'error'); return; }
  setErro('erroConfig', '');
  document.getElementById('cfgDur').textContent = agendaAtual.slot_duracao_min;
  document.getElementById('tbodyConfig').innerHTML =
    '<tr><td colspan="5" class="sup-empty">Carregando...</td></tr>';
  abrirModal('modalConfig');
  const r = await apiFetch('/agendas/' + agendaAtual.id + '/horarios');
  const horarios = r.success ? (r.horarios || []) : [];
  document.getElementById('tbodyConfig').innerHTML = '';
  if (!horarios.length) { addLinhaHorario(); }
  else horarios.forEach(h => addLinhaHorario(h.dia_semana, h.hora_inicio, h.hora_fim));
}

function addLinhaHorario(dia = 1, ini = '09:00', fim = '18:00') {
  const tbody = document.getElementById('tbodyConfig');
  const tr = document.createElement('tr');
  const opcoes = DIAS.map((nome, i) =>
    `<option value="${i}" ${i === Number(dia) ? 'selected' : ''}>${nome}</option>`).join('');
  tr.innerHTML = `
    <td><select class="sup-select sup-cfg-dia">${opcoes}</select></td>
    <td><input type="time" class="sup-cfg-ini" value="${ini}" oninput="atualizarGerados(this)"></td>
    <td><input type="time" class="sup-cfg-fim" value="${fim}" oninput="atualizarGerados(this)"></td>
    <td class="sup-cfg-gerados sup-help"></td>
    <td><button class="btn-sup btn-sup-danger btn-sup-sm" onclick="this.closest('tr').remove()">
      <i class="bi bi-trash"></i></button></td>`;
  tbody.appendChild(tr);
  atualizarGerados(tr.querySelector('.sup-cfg-ini'));
}

function atualizarGerados(input) {
  const tr = input.closest('tr');
  const ini = tr.querySelector('.sup-cfg-ini').value;
  const fim = tr.querySelector('.sup-cfg-fim').value;
  const cel = tr.querySelector('.sup-cfg-gerados');
  const dur = (agendaAtual && agendaAtual.slot_duracao_min) || 30;
  if (!ini || !fim || fim <= ini) { cel.textContent = '—'; return; }
  const mins = (new Date('2000-01-01T' + fim) - new Date('2000-01-01T' + ini)) / 60000;
  cel.textContent = Math.floor(mins / dur) + ' horário(s)';
}

function copiarHorarios(modo) {
  const linhas = [...document.querySelectorAll('#tbodyConfig tr')];
  const segunda = linhas.filter(tr => Number(tr.querySelector('.sup-cfg-dia').value) === 1);
  if (!segunda.length) { setErro('erroConfig', 'Configure a Segunda-feira primeiro.'); return; }
  setErro('erroConfig', '');
  const destinos = modo === 'util' ? [2, 3, 4, 5] : [0, 2, 3, 4, 5, 6];
  destinos.forEach(dia => {
    segunda.forEach(tr => {
      addLinhaHorario(dia,
        tr.querySelector('.sup-cfg-ini').value,
        tr.querySelector('.sup-cfg-fim').value);
    });
  });
  toast('Horários da Segunda copiados.', 'success');
}

async function salvarConfigHorarios() {
  const linhas = [...document.querySelectorAll('#tbodyConfig tr')];
  const horarios = [];
  for (const tr of linhas) {
    const dia = Number(tr.querySelector('.sup-cfg-dia').value);
    const ini = tr.querySelector('.sup-cfg-ini').value;
    const fim = tr.querySelector('.sup-cfg-fim').value;
    if (!ini || !fim) { setErro('erroConfig', 'Preencha início e fim de todas as linhas.'); return; }
    if (fim <= ini) { setErro('erroConfig', `Fim deve ser maior que início (${ini}–${fim}).`); return; }
    horarios.push({ dia_semana: dia, hora_inicio: ini, hora_fim: fim });
  }
  const r = await apiFetch('/agendas/' + agendaAtual.id + '/horarios',
    { method: 'PUT', body: JSON.stringify({ horarios }) });
  if (!r.success) { setErro('erroConfig', r.detail || 'Erro ao salvar.'); return; }
  fecharModal('modalConfig');
  toast('Configuração de horários salva.', 'success');
  carregarCalendario();
}

/* ============ SEÇÃO CURSOS ============ */
function _opcoesAgendas(selId) {
  const sel = document.getElementById(selId);
  const prev = sel.value;
  sel.innerHTML = agendas.length
    ? agendas.map(a => `<option value="${a.id}">${esc(a.nome)}</option>`).join('')
    : '<option value="">Nenhuma agenda cadastrada</option>';
  if (prev) sel.value = prev;
}

async function initSecaoCursos() {
  if (!agendas.length) await loadAgendas();
  _opcoesAgendas('cursoAgendaSel');
  if (cursosPreselect) {
    document.getElementById('cursoAgendaSel').value = cursosPreselect;
    cursosPreselect = null;
  }
  await carregarCursos();
}

async function carregarCursos() {
  const agId = document.getElementById('cursoAgendaSel').value;
  const tbody = document.getElementById('tbodyCursos');
  const btn = document.getElementById('btnNovoCurso');
  if (!agId) {
    tbody.innerHTML = '<tr><td colspan="6" class="sup-empty">Cadastre uma agenda primeiro (no Dashboard).</td></tr>';
    btn.disabled = true;
    cursosSecao = [];
    return;
  }
  btn.disabled = false;
  const r = await apiFetch('/agendas/' + agId + '/servicos');
  cursosSecao = r.success ? (r.servicos || []) : [];
  if (!cursosSecao.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="sup-empty">Nenhum curso nesta agenda. Clique em "Novo curso".</td></tr>';
    return;
  }
  tbody.innerHTML = cursosSecao.map(s => `<tr>
    <td>${esc(s.nome)}</td>
    <td>${s.instrutor
      ? '<i class="bi bi-person-badge"></i> ' + esc(s.instrutor)
      : '<span class="sup-help">—</span>'}</td>
    <td>${s.duracao_min} min</td>
    <td>presencial ${s.cap_presencial || 1} · online ${s.cap_online || 1}</td>
    <td>${s.total_equipamentos || 0}</td>
    <td>${s.ativo ? '<span class="sup-pill ok">Ativo</span>'
                  : '<span class="sup-pill off">Inativo</span>'}</td>
    <td style="white-space:nowrap">
      <button class="btn-sup btn-sup-ghost btn-sup-sm" onclick="editarCurso(${s.id})"
        title="Editar"><i class="bi bi-pencil"></i></button>
      <button class="btn-sup btn-sup-danger btn-sup-sm" onclick="excluirCurso(${s.id})"
        title="Excluir"><i class="bi bi-trash"></i></button>
    </td></tr>`).join('');
}

function _agendaAtualCursos() {
  const id = parseInt(document.getElementById('cursoAgendaSel').value);
  return agendas.find(a => a.id === id) || null;
}

/* Em agenda online, capacidade presencial nao faz sentido — esconde o
   campo e deixa o de online ocupando a linha toda. */
function _adaptarModalCursoPorTipo() {
  const ag = _agendaAtualCursos();
  const presWrap = document.getElementById('cursoCapPresencialWrap');
  const onlineWrap = document.getElementById('cursoCapOnlineWrap');
  const grid = document.getElementById('cursoCapWrap');
  if (!presWrap || !onlineWrap || !grid) return;
  if (ag && ag.tipo === 'online') {
    presWrap.style.display = 'none';
    grid.style.gridTemplateColumns = '1fr';
    document.getElementById('cursoCapPresencial').value = 1; // valor sentinela
  } else {
    presWrap.style.display = '';
    grid.style.gridTemplateColumns = '';
  }
}

function novoCurso() {
  setErro('erroCurso', '');
  document.getElementById('modalCursoTitulo').textContent = 'Novo curso';
  document.getElementById('cursoId').value = '';
  document.getElementById('cursoNome').value = '';
  document.getElementById('cursoDuracao').value = 60;
  document.getElementById('cursoCapPresencial').value = 1;
  document.getElementById('cursoCapOnline').value = 1;
  document.getElementById('cursoInstrutor').value = '';
  document.getElementById('cursoAtivo').checked = true;
  _adaptarModalCursoPorTipo();
  abrirModal('modalCurso');
}
function editarCurso(id) {
  const s = cursosSecao.find(x => x.id === id);
  if (!s) return;
  setErro('erroCurso', '');
  document.getElementById('modalCursoTitulo').textContent = 'Editar curso';
  document.getElementById('cursoId').value = s.id;
  document.getElementById('cursoNome').value = s.nome;
  document.getElementById('cursoDuracao').value = s.duracao_min;
  document.getElementById('cursoCapPresencial').value = s.cap_presencial || 1;
  document.getElementById('cursoCapOnline').value = s.cap_online || 1;
  document.getElementById('cursoInstrutor').value = s.instrutor || '';
  document.getElementById('cursoAtivo').checked = !!s.ativo;
  _adaptarModalCursoPorTipo();
  abrirModal('modalCurso');
}
async function salvarCurso() {
  const id = document.getElementById('cursoId').value;
  const payload = {
    agenda_id: document.getElementById('cursoAgendaSel').value,
    nome: document.getElementById('cursoNome').value.trim(),
    duracao_min: parseInt(document.getElementById('cursoDuracao').value) || 60,
    cap_presencial: parseInt(document.getElementById('cursoCapPresencial').value) || 1,
    cap_online: parseInt(document.getElementById('cursoCapOnline').value) || 1,
    instrutor: document.getElementById('cursoInstrutor').value.trim(),
    ativo: document.getElementById('cursoAtivo').checked,
  };
  if (!payload.nome) { setErro('erroCurso', 'Informe o nome do curso.'); return; }
  const r = id
    ? await apiFetch('/servicos/' + id, { method: 'PUT', body: JSON.stringify(payload) })
    : await apiFetch('/servicos', { method: 'POST', body: JSON.stringify(payload) });
  if (!r.success) { setErro('erroCurso', r.detail || 'Erro ao salvar.'); return; }
  fecharModal('modalCurso');
  toast('Curso salvo.', 'success');
  await carregarCursos();
}
async function excluirCurso(id) {
  if (!confirm('Excluir este curso? Os equipamentos vinculados a ele também serão removidos.')) return;
  const r = await apiFetch('/servicos/' + id, { method: 'DELETE' });
  if (!r.success) { toast(r.detail || 'Erro ao excluir.', 'error'); return; }
  toast('Curso excluído.', 'success');
  await carregarCursos();
}

/* ============ SEÇÃO EQUIPAMENTOS ============ */
async function initSecaoEquipamentos() {
  if (!agendas.length) await loadAgendas();
  _opcoesAgendas('equipAgendaSel');
  await carregarCursosDoEquip();
}

async function carregarCursosDoEquip() {
  const agId = document.getElementById('equipAgendaSel').value;
  const sel = document.getElementById('equipCursoSel');
  if (!agId) {
    sel.innerHTML = '<option value="">— Escolha um curso —</option>';
    carregarEquipamentos();
    return;
  }
  const r = await apiFetch('/agendas/' + agId + '/servicos');
  const cursos = r.success ? (r.servicos || []) : [];
  sel.innerHTML = '<option value="">— Escolha um curso —</option>' +
    cursos.map(c => `<option value="${c.id}">${esc(c.nome)}</option>`).join('');
  carregarEquipamentos();
}

async function carregarEquipamentos() {
  const cursoId = document.getElementById('equipCursoSel').value;
  const tbody = document.getElementById('tbodyEquipamentos');
  const btn = document.getElementById('btnAddEquip');
  if (!cursoId) {
    tbody.innerHTML = '<tr><td colspan="3" class="sup-empty">Selecione um curso.</td></tr>';
    btn.disabled = true;
    return;
  }
  btn.disabled = false;
  const r = await apiFetch('/servicos/' + cursoId + '/equipamentos');
  const eqs = r.success ? (r.equipamentos || []) : [];
  if (!eqs.length) {
    tbody.innerHTML = '<tr><td colspan="3" class="sup-empty">Nenhum equipamento neste curso.</td></tr>';
    return;
  }
  tbody.innerHTML = eqs.map(e => `<tr>
    <td>${esc(e.nome)}</td>
    <td>${e.ativo ? '<span class="sup-pill ok">Ativo</span>'
                  : '<span class="sup-pill off">Inativo</span>'}</td>
    <td><button class="btn-sup btn-sup-danger btn-sup-sm" onclick="excluirEquipamento(${e.id})">
      <i class="bi bi-trash"></i></button></td>
  </tr>`).join('');
}

async function addEquipamento() {
  const cursoId = document.getElementById('equipCursoSel').value;
  if (!cursoId) { toast('Escolha um curso primeiro.', 'error'); return; }
  const inp = document.getElementById('equipNovoNome');
  const nome = inp.value.trim();
  if (!nome) { toast('Informe o nome do equipamento.', 'error'); return; }
  const r = await apiFetch('/equipamentos', {
    method: 'POST', body: JSON.stringify({ servico_id: cursoId, nome }),
  });
  if (!r.success) { toast(r.detail || 'Erro ao adicionar.', 'error'); return; }
  inp.value = '';
  toast('Equipamento adicionado.', 'success');
  await carregarEquipamentos();
}
async function excluirEquipamento(id) {
  if (!confirm('Excluir este equipamento?')) return;
  const r = await apiFetch('/equipamentos/' + id, { method: 'DELETE' });
  if (!r.success) { toast(r.detail || 'Erro ao excluir.', 'error'); return; }
  toast('Equipamento excluído.', 'success');
  await carregarEquipamentos();
}

/* ============ MODAL: agendamentos do dia (Hoje / Amanha) ============ */
async function abrirAgendamentosDia(quando) {
  const d = new Date();
  if (quando === 'amanha') d.setDate(d.getDate() + 1);
  const dataStr = ymd(d);
  const titulo = quando === 'amanha' ? 'Agendamentos para Amanhã' : 'Agendamentos para Hoje';
  document.getElementById('modalDiaTitulo').textContent =
    `${titulo} — ${fmtDataBR(dataStr)}`;
  document.getElementById('tbodyDia').innerHTML =
    '<tr><td colspan="7" class="sup-empty">Carregando...</td></tr>';
  abrirModal('modalDia');

  const r = await apiFetch('/agendamentos-do-dia?data=' + dataStr);
  const ags = r.success ? (r.agendamentos || []) : [];
  const tbody = document.getElementById('tbodyDia');
  if (!ags.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="sup-empty">
      Nenhum agendamento ${quando === 'amanha' ? 'para amanhã' : 'para hoje'}.
    </td></tr>`;
    return;
  }
  tbody.innerHTML = ags.map(a => {
    const ai = parseDT(a.inicio), af = parseDT(a.fim);
    const modal = a.modalidade === 'online' ? '<i class="bi bi-camera-video"></i> Online'
                : a.modalidade === 'presencial' ? '<i class="bi bi-buildings"></i> Presencial'
                : '—';
    return `<tr>
      <td><strong>${hm(ai)}</strong>
        <br><span class="sup-help">até ${hm(af)}</span></td>
      <td>${esc(a.cliente_nome || '—')}${a.cliente_telefone
        ? '<br><span class="sup-help">' + esc(a.cliente_telefone) + '</span>' : ''}</td>
      <td>${esc(a.servico_nome || a.titulo || '—')}</td>
      <td><strong>${esc(a.agenda_nome)}</strong>${a.unidade_nome
        ? '<br><span class="sup-help">' + esc(a.unidade_nome) + '</span>' : ''}</td>
      <td>${esc(a.vendedor_nome || '—')}</td>
      <td>${modal}</td>
      <td><span class="sup-pill ${a.status}">${rotuloStatus(a.status)}</span></td>
    </tr>`;
  }).join('');
}

/* ============ MODAL: lista de agendas (detalhada) ============ */
async function abrirListaAgendas() {
  abrirModal('modalListaAgendas');
  const tbody = document.getElementById('tbodyListaAgendas');
  if (!agendas.length) await loadAgendas();
  if (!agendas.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="sup-empty">Nenhuma agenda cadastrada.</td></tr>';
    return;
  }
  // busca a contagem de cursos de cada agenda em paralelo
  const ativas = agendas.filter(a => a.ativo);
  const cursosPorAgenda = await Promise.all(ativas.map(async a => {
    const r = await apiFetch('/agendas/' + a.id + '/servicos');
    return { id: a.id, cursos: r.success ? (r.servicos || []) : [] };
  }));
  const mapaCursos = {};
  cursosPorAgenda.forEach(x => { mapaCursos[x.id] = x.cursos; });

  tbody.innerHTML = ativas.map(a => {
    const cursos = mapaCursos[a.id] || [];
    const tipo = a.tipo === 'online'
      ? '<span class="sup-pill agendado"><i class="bi bi-camera-video"></i> Online</span>'
      : '<span class="sup-pill ok"><i class="bi bi-buildings"></i> Presencial</span>';
    let listaCursos;
    if (!cursos.length) {
      listaCursos = '<span class="sup-help">Nenhum curso cadastrado</span>';
    } else {
      listaCursos = cursos.slice(0, 4).map(c =>
        `<div style="font-size:.82rem">• ${esc(c.nome)}
          <span class="sup-help">(${c.duracao_min}min)</span></div>`).join('');
      if (cursos.length > 4) {
        listaCursos += `<div class="sup-help">+ ${cursos.length - 4} mais</div>`;
      }
    }
    return `<tr>
      <td><strong>${esc(a.nome)}</strong></td>
      <td>${a.unidade_nome ? esc(a.unidade_nome) : '<span class="sup-help">—</span>'}</td>
      <td>${tipo}</td>
      <td>${listaCursos}</td>
      <td>${a.agendamentos_hoje} / ${a.agendamentos_amanha}</td>
      <td>${a.ativo
        ? '<span class="sup-pill ok">Ativa</span>'
        : '<span class="sup-pill off">Inativa</span>'}</td>
      <td style="white-space:nowrap">
        <button class="btn-sup btn-sup-ghost btn-sup-sm" title="Abrir calendário"
          onclick="fecharModal('modalListaAgendas'); abrirAgenda(${a.id})">
          <i class="bi bi-calendar3"></i></button>
        <button class="btn-sup btn-sup-ghost btn-sup-sm" title="Ver cursos"
          onclick="fecharModal('modalListaAgendas'); irParaCursos(${a.id})">
          <i class="bi bi-mortarboard"></i></button>
      </td>
    </tr>`;
  }).join('');
}

/* ============ PENDENTES (aguardando confirmação) ============ */
async function abrirPendentes() {
  abrirModal('modalPendentes');
  document.getElementById('tbodyPendentes').innerHTML =
    '<tr><td colspan="6" class="sup-empty">Carregando...</td></tr>';
  await renderPendentes();
}

async function renderPendentes() {
  const r = await apiFetch('/pendentes');
  const ps = r.success ? (r.pendentes || []) : [];
  const tbody = document.getElementById('tbodyPendentes');
  if (!ps.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="sup-empty">' +
      'Nenhum agendamento aguardando confirmação.</td></tr>';
    return;
  }
  tbody.innerHTML = ps.map(p => {
    const ini = parseDT(p.inicio), fim = parseDT(p.fim);
    const modal = p.modalidade === 'online' ? 'Online'
                : p.modalidade === 'presencial' ? 'Presencial' : '—';
    return `<tr>
      <td><strong>${esc(p.agenda_nome)}</strong>${p.unidade_nome
        ? '<br><span class="sup-help">' + esc(p.unidade_nome) + '</span>' : ''}</td>
      <td><strong>${fmtDataBR(p.inicio)}</strong>
        <br><span class="sup-help">${hm(ini)} – ${hm(fim)}</span></td>
      <td>${esc(p.cliente_nome || '—')}${p.cliente_telefone
        ? '<br><span class="sup-help">' + esc(p.cliente_telefone) + '</span>' : ''}</td>
      <td>${esc(p.servico_nome || p.titulo || '—')}</td>
      <td>${modal}</td>
      <td style="white-space:nowrap">
        <button class="btn-sup btn-sup-primary btn-sup-sm" onclick="confirmarPendente(${p.id})">
          <i class="bi bi-check-lg"></i> Confirmar</button>
        <button class="btn-sup btn-sup-danger btn-sup-sm" onclick="recusarPendente(${p.id})">
          <i class="bi bi-x-lg"></i> Recusar</button>
      </td></tr>`;
  }).join('');
}

async function confirmarPendente(id) {
  const r = await apiFetch('/agendamentos/' + id,
    { method: 'PUT', body: JSON.stringify({ status: 'agendado' }) });
  if (!r.success) { toast(r.detail || 'Erro ao confirmar.', 'error'); return; }
  toast('Agendamento confirmado.', 'success');
  await renderPendentes();
  loadDashboard();
}

async function recusarPendente(id) {
  if (!confirm('Recusar este agendamento? Ele será cancelado.')) return;
  const r = await apiFetch('/agendamentos/' + id,
    { method: 'PUT', body: JSON.stringify({ status: 'cancelado' }) });
  if (!r.success) { toast(r.detail || 'Erro ao recusar.', 'error'); return; }
  toast('Agendamento recusado.', 'success');
  await renderPendentes();
  loadDashboard();
}

/* ============ SEÇÃO FERIADOS ============ */
function fmtDataBR(iso) {
  if (!iso) return '—';
  const p = String(iso).slice(0, 10).split('-');
  return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : iso;
}
function _capitaliza(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }

async function initSecaoFeriados() {
  if (!agendas.length) await loadAgendas();
  _opcoesAgendas('feriadoAgendaSel');
  await carregarFeriados();
}

async function carregarFeriados() {
  const agId = document.getElementById('feriadoAgendaSel').value;
  const tbody = document.getElementById('tbodyFeriados');
  const r = await apiFetch('/feriados' + (agId ? '?agenda_id=' + agId : ''));
  const feriados = r.success ? (r.feriados || []) : [];
  if (!feriados.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="sup-empty">Nenhum feriado cadastrado.</td></tr>';
    return;
  }
  tbody.innerHTML = feriados.map(f => {
    const nacional = !f.agenda_id;
    const abr = nacional
      ? '<span class="sup-pill agendado">Nacional</span>'
      : `<span class="sup-pill pendente">${esc(_capitaliza(f.tipo))}</span>`;
    return `<tr>
      <td>${fmtDataBR(f.data)}</td>
      <td>${esc(f.nome)}</td>
      <td>${abr}</td>
      <td><button class="btn-sup btn-sup-danger btn-sup-sm"
        onclick="excluirFeriado(${f.id}, ${nacional})"><i class="bi bi-trash"></i></button></td>
    </tr>`;
  }).join('');
}

function abrirModalFeriado() {
  setErro('erroFeriado', '');
  document.getElementById('feriadoData').value = '';
  document.getElementById('feriadoNome').value = '';
  // monta o "Aplica a": Nacional + uma opção por unidade
  const sel = document.getElementById('feriadoAplicaA');
  sel.innerHTML = '<option value="">🌐 Nacional — todas as unidades</option>' +
    agendas.map(a => `<option value="${a.id}">${esc(a.nome)}</option>`).join('');
  // pré-seleciona a unidade que está aberta na lista
  const atual = document.getElementById('feriadoAgendaSel').value;
  if (atual) sel.value = atual;
  abrirModal('modalFeriado');
}

async function salvarFeriado() {
  const aplicaA = document.getElementById('feriadoAplicaA').value;  // '' = nacional
  const payload = {
    data: document.getElementById('feriadoData').value,
    nome: document.getElementById('feriadoNome').value.trim(),
    agenda_id: aplicaA || null,
  };
  if (!payload.data) { setErro('erroFeriado', 'Informe a data.'); return; }
  if (!payload.nome) { setErro('erroFeriado', 'Informe o nome do feriado.'); return; }
  const r = await apiFetch('/feriados', { method: 'POST', body: JSON.stringify(payload) });
  if (!r.success) { setErro('erroFeriado', r.detail || 'Erro ao salvar.'); return; }
  fecharModal('modalFeriado');
  toast('Feriado adicionado.', 'success');
  await carregarFeriados();
}

async function excluirFeriado(id, nacional) {
  const msg = nacional
    ? 'Excluir este feriado NACIONAL? Ele será removido de TODAS as unidades.'
    : 'Excluir este feriado desta unidade?';
  if (!confirm(msg)) return;
  const r = await apiFetch('/feriados/' + id, { method: 'DELETE' });
  if (!r.success) { toast(r.detail || 'Erro ao excluir.', 'error'); return; }
  toast('Feriado removido.', 'success');
  await carregarFeriados();
}

/* ============ SINO DE NOTIFICACOES ============ */
let _notifList = [];
let _notifTimer = null;

async function carregarNotificacoes() {
  // Usa o /pendentes — eh a unica coisa realmente acionavel agora.
  // Quando surgirem outros eventos relevantes (ex: agendamento cancelado pelo
  // cliente), basta concatenar mais fontes aqui antes do renderNotificacoes().
  try {
    const r = await apiFetch('/pendentes');
    _notifList = r.success ? (r.pendentes || []) : [];
  } catch (e) {
    _notifList = [];
  }
  renderNotificacoes();
}

function renderNotificacoes() {
  const badge = document.getElementById('supNotifBadge');
  const count = document.getElementById('supNotifCount');
  const list  = document.getElementById('supNotifList');
  const wrap  = document.getElementById('supNotifWrap');
  if (!badge || !list) return;

  const n = _notifList.length;
  if (n > 0) {
    badge.textContent = n > 99 ? '99+' : String(n);
    badge.classList.add('show');
    count.textContent = `${n} pendente${n > 1 ? 's' : ''}`;
    wrap.classList.add('has-unread');
  } else {
    badge.classList.remove('show');
    count.textContent = '';
    wrap.classList.remove('has-unread');
  }

  if (!n) {
    list.innerHTML = `<div class="sup-notif-empty">
      <i class="bi bi-check-circle"></i>
      Nenhum agendamento pendente.
    </div>`;
    return;
  }

  list.innerHTML = _notifList.map(p => {
    const ini = parseDT(p.inicio);
    const unidade = p.unidade_nome ? ' · ' + esc(p.unidade_nome) : '';
    return `<div class="sup-notif-item" onclick="abrirPendentesDoSino()">
      <div class="sup-notif-item-icon"><i class="bi bi-hourglass-split"></i></div>
      <div class="sup-notif-item-body">
        <div class="sup-notif-item-title">Aguardando confirmação</div>
        <div class="sup-notif-item-msg">
          ${esc(p.cliente_nome || '—')} — ${esc(p.servico_nome || p.titulo || 'atendimento')}
        </div>
        <div class="sup-notif-item-time">
          ${fmtDataBR(p.inicio)} às ${hm(ini)} · ${esc(p.agenda_nome)}${unidade}
        </div>
      </div>
    </div>`;
  }).join('');
}

function toggleNotifPanel() {
  const panel = document.getElementById('supNotifPanel');
  if (!panel) return;
  panel.classList.toggle('show');
  // recarrega ao abrir pra mostrar dados frescos
  if (panel.classList.contains('show')) carregarNotificacoes();
}

function abrirPendentesDoSino() {
  document.getElementById('supNotifPanel').classList.remove('show');
  abrirPendentes();
}

// Fechar painel quando clicar fora
document.addEventListener('click', e => {
  const panel = document.getElementById('supNotifPanel');
  const wrap  = document.getElementById('supNotifWrap');
  if (panel && panel.classList.contains('show') &&
      !panel.contains(e.target) && !wrap.contains(e.target)) {
    panel.classList.remove('show');
  }
});

/* ============ INIT ============ */
document.addEventListener('DOMContentLoaded', async () => {
  try {
    const u = JSON.parse(localStorage.getItem('cpe_user') || '{}');
    document.getElementById('topbarUser').textContent = u.name || '';
  } catch (e) { /* ignore */ }
  await carregarUnidades();
  await loadDashboard();
  // sino: primeira carga + poll a cada 30s
  carregarNotificacoes();
  if (_notifTimer) clearInterval(_notifTimer);
  _notifTimer = setInterval(carregarNotificacoes, 30000);
  document.getElementById('supLoading').style.display = 'none';
});
