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

// Permissoes do user logado no modulo — preenchidas no init via /meu-nivel.
// admin = CRUD estrutura (agendas, cursos, equipamentos, horarios, feriados)
// op    = criar/cancelar agendamento (Suporte comum)
// view  = somente leitura (Comercial)
let _nivel     = 'none';
let _canView   = false;
let _canOp     = false;
let _canAdmin  = false;

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
let treinosPreselect = null; // agenda a pré-selecionar ao abrir a seção Treinamentos
let dronesPreselect = null;  // agenda a pré-selecionar ao abrir a seção Drones

/* ============ PERMISSOES ============ */
async function carregarPermissoes() {
  const r = await apiFetch('/meu-nivel');
  if (r.success) {
    _nivel    = r.nivel || 'none';
    _canView  = _nivel !== 'none';
    _canOp    = _nivel === 'op' || _nivel === 'admin';
    _canAdmin = _nivel === 'admin';
  }
  aplicarPermissoes();
}

/* Mostra/esconde controles do admin conforme nivel. Chamado depois de
   cada render que injeta HTML novo (modais, tabelas, cards). */
function aplicarPermissoes() {
  // Esconde tudo marcado com [data-need-admin] se nao for admin
  document.querySelectorAll('[data-need-admin]').forEach(el => {
    el.style.display = _canAdmin ? '' : 'none';
  });
  // Esconde tudo marcado com [data-need-op] se nao puder operacao
  document.querySelectorAll('[data-need-op]').forEach(el => {
    el.style.display = _canOp ? '' : 'none';
  });
}

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
  cursos: 'Cursos', treinamentos: 'Treinamentos', drones: 'Drones',
  equipamentos: 'Equipamentos', clientes: 'Clientes', feriados: 'Feriados',
};
function showSection(name) {
  document.querySelectorAll('.sup-page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  document.querySelectorAll('.sup-nav-item').forEach(n =>
    n.classList.toggle('active', n.dataset.section === name));
  document.getElementById('topbarTitle').textContent = TITULOS_SECAO[name] || '';
  document.getElementById('supSidebar').classList.remove('show');
  if (name === 'dashboard') loadDashboard();
  else if (name === 'treinamentos') initSecaoTreinamentos();
  else if (name === 'drones') initSecaoDrones();
  else if (name === 'clientes') initSecaoClientes();
  else if (name === 'agendas') initSecaoAgendas();
  else if (name === 'calendario') initSecaoCalendario();
  else if (name === 'cursos') initSecaoCursos();
  else if (name === 'equipamentos') initSecaoEquipamentos();
  else if (name === 'feriados') initSecaoFeriados();
  // Anima itens visiveis na pagina nova com stagger (cards, agendas, stats).
  // Respeita prefers-reduced-motion via CSS @media.
  supAnimateInPage(name);
}

/* ============ MOVIMENTO ============
   Stagger fade-up nos cards/agendas/stats ao trocar de secao. Cuida pra
   só animar UMA VEZ por entrada e dentro do contêiner correto. */
function supAnimateInPage(name) {
  const page = document.getElementById('page-' + name);
  if (!page) return;
  // Pequeno delay pra dar tempo da pagina renderizar (algumas usam fetchs async)
  requestAnimationFrame(() => {
    const seletores = [
      '.sup-stat-card',
      '.sup-agenda-card',
      '.sup-card',
      '.sup-table tbody tr',
    ];
    const alvos = page.querySelectorAll(seletores.join(','));
    alvos.forEach((el, i) => {
      el.classList.remove('sup-enter');                 // reset
      void el.offsetWidth;                              // reflow pra reiniciar
      el.style.animationDelay = (Math.min(i, 18) * 28) + 'ms';
      el.classList.add('sup-enter');
    });
  });
}

/* Aplica pulso amarelo num elemento recem-criado (1.2s e remove sozinho). */
function supPulse(el) {
  if (!el) return;
  el.classList.add('sup-pulse');
  setTimeout(() => el.classList.remove('sup-pulse'), 1300);
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
  // Carrega ociosidade dos 2 grupos (so visivel pra _canAdmin via data-need-admin no HTML)
  carregarOciosidade('Drone');
  carregarOciosidade('Suporte');
}

/* ============ OCIOSIDADE DA EQUIPE (dashboard, admin-only) ============
   Mostra matriz instrutor x dia colorida pra responsavel do grupo enxergar
   quem esta livre nos proximos 7 dias.
   Backend: GET /api/atendimentos/instrutores-ociosidade?dias=7&grupo=Drone|Suporte
   Cada grupo vira um card separado.
   Permissao backend: admin do modulo (mesma whitelist da dashboard inteira). */
async function carregarOciosidade(grupo) {
  // Detecta se ALGUM card data-need-admin esta visivel; se nao, não chama
  // o endpoint (evita 403 no console pra view-only).
  const anyAdminCard = document.querySelector('[data-need-admin]');
  if (!anyAdminCard || anyAdminCard.style.display === 'none') return;

  const sufixo = grupo === 'Drone' ? 'Drone' : 'Suporte';
  const tbody = document.getElementById('tbodyOciosidade' + sufixo);
  if (!tbody) return;

  const r = await apiFetch('/instrutores-ociosidade?dias=7&grupo=' + encodeURIComponent(grupo));
  if (!r || !r.success) {
    tbody.innerHTML = '<tr><td class="sup-empty">Falha ao carregar ociosidade.</td></tr>';
    return;
  }
  renderOciosidade(grupo, r.dias || [], r.instrutores || []);
}

function renderOciosidade(grupo, dias, instrutores) {
  const sufixo = grupo === 'Drone' ? 'Drone' : 'Suporte';
  const thead = document.getElementById('thOciosidade' + sufixo);
  const tbody = document.getElementById('tbodyOciosidade' + sufixo);
  if (!thead || !tbody) return;

  // Helper: data ISO -> "Seg 17/06" (pt-BR curto)
  const DOW = ['Dom','Seg','Ter','Qua','Qui','Sex','Sab'];
  const fmtCab = (iso) => {
    const d = new Date(iso + 'T12:00:00');  // meio-dia evita TZ rolling
    return DOW[d.getDay()] + ' ' + String(d.getDate()).padStart(2,'0') + '/' + String(d.getMonth()+1).padStart(2,'0');
  };

  // Reconstroi cabecalho (primeira coluna varia por grupo)
  const colNome = grupo === 'Drone' ? 'Piloto' : 'Instrutor';
  thead.innerHTML = `<th style="min-width:220px">${colNome}</th>`
    + dias.map(d => `<th style="text-align:center;font-size:11px;font-weight:600">${fmtCab(d)}</th>`).join('');

  if (!instrutores.length) {
    tbody.innerHTML = `<tr><td colspan="${dias.length + 1}" class="sup-empty">`
      + `Nenhum usuario cadastrado no grupo ${grupo}.</td></tr>`;
    return;
  }

  // Helper: cor de fundo pela carga
  const corCelula = (qtd) => {
    if (qtd === 0) return { bg:'#dcfce7', fg:'#166534', txt:'Livre' };       // verde
    if (qtd === 1) return { bg:'#fef9c3', fg:'#854d0e', txt:'1 ag.' };       // amarelo
    if (qtd === 2) return { bg:'#fed7aa', fg:'#9a3412', txt:'2 ag.' };       // laranja
    return { bg:'#fee2e2', fg:'#991b1b', txt:qtd + ' ag.' };                 // vermelho
  };

  // Helper: iniciais pra fallback do avatar
  const iniciais = (nome) => {
    if (!nome) return '?';
    return nome.trim().split(/\s+/).slice(0,2).map(s => s[0]).join('').toUpperCase();
  };

  tbody.innerHTML = instrutores.map(ins => {
    const av = ins.avatar_url
      ? `<img src="${esc(ins.avatar_url)}" alt="" style="width:32px;height:32px;border-radius:50%;object-fit:cover;flex-shrink:0">`
      : `<div style="width:32px;height:32px;border-radius:50%;background:#1a1a1a;color:#ffc107;display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;flex-shrink:0">${esc(iniciais(ins.nome))}</div>`;

    const celulas = ins.celulas.map(c => {
      const cor = corCelula(c.qtd);
      const tip = c.detalhes
        ? ` title="${esc(c.detalhes).replace(/\|/g, '\n')}"`
        : ' title="Sem agendamentos"';
      return `<td style="text-align:center;padding:6px;background:${cor.bg};color:${cor.fg};font-weight:600;font-size:12px"${tip}>${cor.txt}</td>`;
    }).join('');

    return `<tr>
      <td style="vertical-align:middle">
        <div style="display:flex;align-items:center;gap:10px">
          ${av}
          <div>
            <div style="font-weight:600;color:#1f2937">${esc(ins.nome)}</div>
            <div style="font-size:11px;color:#6b7280">${ins.total} agendamento(s) na semana</div>
          </div>
        </div>
      </td>
      ${celulas}
    </tr>`;
  }).join('');
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
        <button class="btn-sup btn-sup-ghost btn-sup-sm" onclick="configHorariosDe(${a.id})" data-need-admin>
          <i class="bi bi-gear"></i> Horários</button>
        <button class="btn-sup btn-sup-ghost btn-sup-sm" onclick="irParaCursos(${a.id})">
          <i class="bi bi-mortarboard"></i> Cursos</button>
        <button class="btn-sup btn-sup-ghost btn-sup-sm" onclick="irParaTreinamentos(${a.id})">
          <i class="bi bi-easel"></i> Treinamentos</button>
        <button class="btn-sup btn-sup-ghost btn-sup-sm" onclick="irParaDrones(${a.id})">
          <i class="bi bi-airplane-engines-fill"></i> Drones</button>
        <button class="btn-sup btn-sup-ghost btn-sup-sm" onclick="abrirModalAgenda(${a.id})" data-need-admin>
          <i class="bi bi-pencil"></i> Editar</button>
        <button class="btn-sup btn-sup-${a.ativo ? 'danger' : 'primary'} btn-sup-sm"
          onclick="toggleAgenda(${a.id})" data-need-admin>
          <i class="bi bi-power"></i> ${a.ativo ? 'Desativar' : 'Ativar'}</button>
      </div>
    </div>`;
  }).join('');
  aplicarPermissoes();
}

/* ============ LINK PUBLICO ============ */
// Detecta o ambiente atual:
//   - local (localhost / 127.0.0.1 / IP da rede) -> link aponta pro host atual
//     (modo dev — voce testa a UX completa sem publicar nada)
//   - dominio publico (cpecontrol.cpetecnologia.com.br) -> link de producao
// Em qualquer caso usa `window.location.origin` — sempre bate o ambiente em uso.
const PUBLIC_AGENDAR_PATH = '/SistemaCPE/web/pages/agendar.html';

function _isAmbienteLocal() {
  const h = window.location.hostname;
  return h === 'localhost' || h === '127.0.0.1' || /^\d{1,3}(\.\d{1,3}){3}$/.test(h);
}

function _urlAgendarPublico() {
  return window.location.origin + PUBLIC_AGENDAR_PATH;
}

async function copiarLinkPublico() {
  const url = _urlAgendarPublico();
  const tag = _isAmbienteLocal() ? '[DEV] ' : '';
  try {
    await navigator.clipboard.writeText(url);
    toast(tag + 'Link copiado: ' + url, 'success');
  } catch (e) {
    // fallback se o clipboard API falhar (HTTP, browser antigo)
    const tmp = document.createElement('textarea');
    tmp.value = url; document.body.appendChild(tmp);
    tmp.select(); document.execCommand('copy'); tmp.remove();
    toast(tag + 'Link copiado: ' + url, 'success');
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

function irParaTreinamentos(id) {
  treinosPreselect = id;
  showSection('treinamentos');
}

function irParaDrones(id) {
  dronesPreselect = id;
  showSection('drones');
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
      <td><button class="btn-sup btn-sup-ghost btn-sup-sm" onclick="abrirModalAgenda(${a.id})" data-need-admin>
        <i class="bi bi-pencil"></i></button></td>
    </tr>`;
  }).join('');
  aplicarPermissoes();
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
  // Excluir agenda: so admin pode (DELETE destrutivo).
  document.getElementById('btnExcluirAgenda').style.display =
    (a && _canAdmin) ? 'inline-flex' : 'none';
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

/* Carrega TODAS as ofertas da agenda em arrays separados (cursos, treinamentos
   e drones). Usado pelo modal de novo/editar atendimento (calendário interno). */
let treinosAgenda = [];
let dronesAgenda  = [];
async function carregarServicosAgenda() {
  if (!agendaAtual) { servicosAgenda = []; treinosAgenda = []; dronesAgenda = []; return; }
  const aid = agendaAtual.id;
  const [rs, rt, rd] = await Promise.all([
    apiFetch('/agendas/' + aid + '/servicos'),
    apiFetch('/agendas/' + aid + '/treinamentos'),
    apiFetch('/agendas/' + aid + '/drones'),
  ]);
  servicosAgenda = rs && rs.success ? (rs.servicos || [])      : [];
  treinosAgenda  = rt && rt.success ? (rt.treinamentos || [])  : [];
  dronesAgenda   = rd && rd.success ? (rd.drones || [])        : [];
}

/* Decodifica o value do select 'agtServico' (formato 'tipo:ID') em
   { tipo, id, item } ou null. Compat: se vier só um número, assume curso. */
function _parseAgtOferta(val) {
  if (!val) return null;
  let tipo, id;
  if (String(val).includes(':')) {
    const parts = String(val).split(':');
    tipo = parts[0];
    id = parseInt(parts[1], 10);
  } else {
    tipo = 'servico';
    id = parseInt(val, 10);
  }
  const arr = tipo === 'servico'      ? servicosAgenda
            : tipo === 'treinamento'  ? treinosAgenda
            : tipo === 'drone'        ? dronesAgenda
            : [];
  const item = arr.find(x => x.id == id) || null;
  return item ? { tipo, id, item } : null;
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
  // Sem permissao de operacao (Comercial / sem grupo) nem abre o modal.
  if (!_canOp) {
    toast('Voce nao tem permissao para criar agendamentos.', 'error');
    return;
  }
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
  let html = '<option value="">— Sem serviço —</option>';
  if (servicosAgenda.length) {
    html += '<optgroup label="Cursos">';
    html += servicosAgenda.map(s =>
      `<option value="servico:${s.id}">${esc(s.nome)} (${s.duracao_min}min)</option>`).join('');
    html += '</optgroup>';
  }
  if (treinosAgenda.length) {
    html += '<optgroup label="Treinamentos">';
    html += treinosAgenda.map(t =>
      `<option value="treinamento:${t.id}">${esc(t.nome)} (${t.duracao_min}min)</option>`).join('');
    html += '</optgroup>';
  }
  if (dronesAgenda.length) {
    html += '<optgroup label="Drones">';
    html += dronesAgenda.map(d =>
      `<option value="drone:${d.id}">${esc(d.nome)} (${d.duracao_min}min)</option>`).join('');
    html += '</optgroup>';
  }
  document.getElementById('agtServico').innerHTML = html;
}
function _preencherSelectVendedores() {
  document.getElementById('agtVendedor').innerHTML =
    '<option value="">—</option>' +
    vendedoresList.map(v => `<option value="${v.id}">${esc(v.name)}</option>`).join('');
}
async function _carregarEquipSelect(valOuId, selecionado) {
  const sel = document.getElementById('agtEquipamento');
  sel.innerHTML = '<option value="">—</option>';
  if (!valOuId) return;
  // Aceita 'tipo:id' (formato novo) ou só id (compat — assume servico)
  let path;
  if (String(valOuId).includes(':')) {
    const o = _parseAgtOferta(valOuId);
    if (!o) return;
    path = o.tipo === 'drone'        ? '/drones/' + o.id + '/equipamentos'
         : o.tipo === 'treinamento'  ? '/treinamentos/' + o.id + '/equipamentos'
         :                              '/servicos/' + o.id + '/equipamentos';
  } else {
    path = '/servicos/' + valOuId + '/equipamentos';
  }
  const r = await apiFetch(path);
  if (r.success) {
    sel.innerHTML = '<option value="">—</option>' +
      (r.equipamentos || []).filter(e => e.ativo)
        .map(e => `<option value="${e.id}">${esc(e.nome)}</option>`).join('');
  }
  if (selecionado) sel.value = selecionado;
}

async function onAgtServicoChange() {
  const val = document.getElementById('agtServico').value;
  await _carregarEquipSelect(val);
  // Instrutor/piloto: dropdown sempre visivel mas a LISTA muda conforme tipo
  //   - drone        -> grupo Drone (pilotos)
  //   - treinamento  -> grupo Suporte
  //   - servico/curso-> grupo Suporte
  //   - nenhuma sel. -> grupo Suporte (default, troca quando o user escolher)
  const o = _parseAgtOferta(val);
  const label = document.getElementById('agtPilotoLabel');
  const suffix = document.getElementById('agtPilotoLabelSuffix');
  if (o && o.tipo === 'drone') {
    await _popularSelectInstrutores('agtPiloto', 'Drone');
    label.textContent = 'Piloto / Operador do drone *';
    suffix.textContent = '(obrigatorio — grupo Drone)';
  } else {
    await _popularSelectInstrutores('agtPiloto', 'Suporte');
    label.textContent = 'Instrutor';
    suffix.textContent = '(opcional — grupo Suporte — usado na dashboard de ociosidade)';
  }
  if (!o) return;
  const s = o.item;
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
  // Reconstrói o value 'tipo:id' a partir do agendamento existente
  let valOferta = '';
  if (a) {
    if (a.servico_id)        valOferta = 'servico:' + a.servico_id;
    else if (a.treinamento_id) valOferta = 'treinamento:' + a.treinamento_id;
    else if (a.drone_id)     valOferta = 'drone:' + a.drone_id;
  }
  document.getElementById('agtId').value = a ? a.id : '';
  document.getElementById('agtServico').value = valOferta;
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

  // Instrutor/piloto: dropdown sempre visivel. Lista correta vem de
  // onAgtServicoChange (que ja decide grupo Drone vs Suporte pelo tipo).
  // Chamamos manualmente porque setar .value em script nao dispara change.
  await onAgtServicoChange();
  // Pre-preenche o instrutor selecionado, se houver
  if (a && a.piloto_id) {
    document.getElementById('agtPiloto').value = String(a.piloto_id);
  }

  // Excluir agendamento (DELETE) e admin-only; cancelar (status='cancelado') e op.
  document.getElementById('btnExcluirAg').style.display =
    (a && _canAdmin) ? 'inline-flex' : 'none';
  await _carregarEquipSelect(valOferta,
                             a && a.equipamento_id ? a.equipamento_id : '');
  abrirModal('modalAgendamento');
}

async function salvarAgendamento() {
  const id = document.getElementById('agtId').value;
  const o = _parseAgtOferta(document.getElementById('agtServico').value);
  const payload = {
    agenda_id: agendaAtual.id,
    servico_id:     (o && o.tipo === 'servico')     ? o.id : null,
    treinamento_id: (o && o.tipo === 'treinamento') ? o.id : null,
    drone_id:       (o && o.tipo === 'drone')       ? o.id : null,
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
    piloto_id:   document.getElementById('agtPiloto').value || null,
    status: document.getElementById('agtStatus').value,
    observacoes: document.getElementById('agtObs').value.trim(),
  };
  if (!payload.titulo) { setErro('erroAg', 'Informe o título ou escolha um serviço.'); return; }
  if (!payload.inicio || !payload.fim) { setErro('erroAg', 'Informe início e fim.'); return; }
  // Drone exige piloto
  if (payload.drone_id && !payload.piloto_id) {
    setErro('erroAg', 'Selecione o piloto que vai operar o drone neste atendimento.');
    return;
  }
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
function _opcoesAgendas(selId, filtro) {
  // filtro: opcional, ex: a => a.tipo !== 'online'
  const sel = document.getElementById(selId);
  const prev = sel.value;
  const lista = filtro ? agendas.filter(filtro) : agendas;
  sel.innerHTML = lista.length
    ? lista.map(a => `<option value="${a.id}">${esc(a.nome)}</option>`).join('')
    : '<option value="">Nenhuma agenda disponível</option>';
  if (prev && lista.some(a => String(a.id) === String(prev))) sel.value = prev;
}

async function initSecaoCursos() {
  if (!agendas.length) await loadAgendas();
  // Curso é apenas presencial — não listar agendas online no select
  _opcoesAgendas('cursoAgendaSel', a => (a.tipo || 'fisica') !== 'online');
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
        title="Editar" data-need-admin><i class="bi bi-pencil"></i></button>
      <button class="btn-sup btn-sup-secondary btn-sup-sm" onclick="abrirModalDuplicar('curso', ${s.id}, ${JSON.stringify(s.nome).replace(/"/g, '&quot;')})"
        title="Duplicar para outras unidades" data-need-admin><i class="bi bi-files"></i></button>
      <button class="btn-sup btn-sup-danger btn-sup-sm" onclick="excluirCurso(${s.id})"
        title="Excluir" data-need-admin><i class="bi bi-trash"></i></button>
    </td></tr>`).join('');
  aplicarPermissoes();
}

function _agendaAtualCursos() {
  const id = parseInt(document.getElementById('cursoAgendaSel').value);
  return agendas.find(a => a.id === id) || null;
}

/* Curso é APENAS presencial — esconde o campo "Capacidade online" SEMPRE
   e força cap_online=0. Frontend espelha a regra do backend. */
function _adaptarModalCursoPorTipo() {
  const onlineWrap = document.getElementById('cursoCapOnlineWrap');
  const grid = document.getElementById('cursoCapWrap');
  if (!onlineWrap || !grid) return;
  onlineWrap.style.display = 'none';
  grid.style.gridTemplateColumns = '1fr';
  const onlineInput = document.getElementById('cursoCapOnline');
  if (onlineInput) onlineInput.value = 0;
}

/* Carrega vendedores no select. Pre-seleciona id se passado. */
async function _popularSelectVendedor(selId, vendedor_id) {
  if (!vendedoresList.length) {
    const v = await apiFetch('/vendedores');
    vendedoresList = v.success ? (v.vendedores || []) : [];
  }
  const sel = document.getElementById(selId);
  if (!sel) return;
  sel.innerHTML = '<option value="">— Sem vendedor padrão —</option>' +
    vendedoresList.map(v => `<option value="${v.id}">${esc(v.name)}</option>`).join('');
  if (vendedor_id) sel.value = vendedor_id;
}

function onCursoVendedorChange() {
  // Se selecionar vendedor cadastrado, limpa o campo manual
  if (document.getElementById('cursoVendedorSel').value) {
    document.getElementById('cursoVendedorNome').value = '';
  }
}
function toggleCursoVendedorManual() {
  const wrap = document.getElementById('cursoVendedorManualWrap');
  wrap.style.display = wrap.style.display === 'none' ? '' : 'none';
}

async function novoCurso() {
  setErro('erroCurso', '');
  document.getElementById('modalCursoTitulo').textContent = 'Novo curso';
  document.getElementById('cursoId').value = '';
  document.getElementById('cursoNome').value = '';
  document.getElementById('cursoDescricao').value = '';
  document.getElementById('cursoDuracao').value = 60;
  document.getElementById('cursoCapPresencial').value = 1;
  document.getElementById('cursoCapOnline').value = 1;
  document.getElementById('cursoInstrutor').value = '';
  document.getElementById('cursoVendedorNome').value = '';
  document.getElementById('cursoVendedorManualWrap').style.display = 'none';
  document.getElementById('cursoAtivo').checked = true;
  document.getElementById('cursoMidiaWrap').style.display = 'none';
  document.getElementById('cursoEquipsWrap').style.display = 'none';
  await _popularSelectVendedor('cursoVendedorSel');
  _adaptarModalCursoPorTipo();
  abrirModal('modalCurso');
}

async function editarCurso(id) {
  const s = cursosSecao.find(x => x.id === id);
  if (!s) return;
  setErro('erroCurso', '');
  document.getElementById('modalCursoTitulo').textContent = 'Editar curso';
  document.getElementById('cursoId').value = s.id;
  document.getElementById('cursoNome').value = s.nome;
  document.getElementById('cursoDescricao').value = s.descricao || '';
  document.getElementById('cursoDuracao').value = s.duracao_min;
  document.getElementById('cursoCapPresencial').value = s.cap_presencial || 1;
  document.getElementById('cursoCapOnline').value = s.cap_online || 1;
  document.getElementById('cursoInstrutor').value = s.instrutor || '';
  document.getElementById('cursoVendedorNome').value = s.vendedor_nome || '';
  document.getElementById('cursoVendedorManualWrap').style.display = s.vendedor_nome ? '' : 'none';
  document.getElementById('cursoAtivo').checked = !!s.ativo;
  await _popularSelectVendedor('cursoVendedorSel', s.vendedor_id);
  // Mídia + Equipamentos + Banner + Módulos só ao editar (precisam de id existente)
  document.getElementById('cursoMidiaWrap').style.display = '';
  document.getElementById('cursoEquipsWrap').style.display = '';
  document.getElementById('cursoEquipNovoWrap').style.display = 'none';
  document.getElementById('cursoBannerWrap').style.display = '';
  document.getElementById('cursoModulosWrap').style.display = '';
  carregarMidia('servico', s.id, 'curso');
  carregarEquipsVinculados('servico', s.id, 'curso');
  carregarBanner('servico', s.id, 'curso', s.banner_url);
  carregarModulos('servico', s.id, 'curso');
  _adaptarModalCursoPorTipo();
  abrirModal('modalCurso');
}

async function salvarCurso() {
  const id = document.getElementById('cursoId').value;
  const payload = {
    agenda_id: document.getElementById('cursoAgendaSel').value,
    nome: document.getElementById('cursoNome').value.trim(),
    descricao: document.getElementById('cursoDescricao').value.trim(),
    duracao_min: parseInt(document.getElementById('cursoDuracao').value) || 60,
    cap_presencial: parseInt(document.getElementById('cursoCapPresencial').value) || 1,
    cap_online: parseInt(document.getElementById('cursoCapOnline').value) || 1,
    instrutor: document.getElementById('cursoInstrutor').value.trim(),
    vendedor_id: document.getElementById('cursoVendedorSel').value || null,
    vendedor_nome: document.getElementById('cursoVendedorNome').value.trim(),
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

/* ============ SEÇÃO EQUIPAMENTOS — catalogo global ============ */
let equipsSecao = [];          // todos os equipamentos do sistema
let equipVincAtuais = [];      // vinculos do equipamento sendo editado
let _opcoesItensCache = {};    // cache servico/treinamento pra select de vinculo

async function initSecaoEquipamentos() {
  if (!agendas.length) await loadAgendas();
  await carregarEquipamentos();
}

async function carregarEquipamentos() {
  const tbody = document.getElementById('tbodyEquipamentos');
  const r = await apiFetch('/equipamentos');
  equipsSecao = r.success ? (r.equipamentos || []) : [];
  if (!equipsSecao.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="sup-empty">' +
      'Nenhum equipamento cadastrado. Clique em "Novo equipamento".</td></tr>';
    return;
  }
  tbody.innerHTML = equipsSecao.map(e => {
    // Vinculos: chips compactos sentence-case com icone que discrimina o tipo.
    const vincs = (e.vinculos || []).map(v => {
      const tipoIcon = v.entidade === 'treinamento' ? 'bi-easel'
                     : v.entidade === 'drone'       ? 'bi-airplane-engines-fill'
                     :                                'bi-mortarboard';
      const tipoLabel = v.entidade === 'treinamento' ? 'Treinamento'
                      : v.entidade === 'drone'       ? 'Drone'
                      :                                'Curso';
      const nome = v.nome || '?';
      const titleAttr = (tipoLabel + ': ' + nome).replace(/"/g, '&quot;');
      return '<span class="sup-equip-vinc-chip tipo-' + esc(v.entidade) +
             '" title="' + titleAttr + '">' +
             '<i class="bi ' + tipoIcon + '"></i>' +
             '<span>' + esc(nome) + '</span></span>';
    }).join('');
    const vincsCell = vincs
      ? '<div class="sup-equip-vincs">' + vincs + '</div>'
      : '<span class="sup-help">Sem vínculo</span>';

    // Descricao: truncada em 2 linhas, tooltip nativo com texto completo.
    const descFull = e.descricao
      ? esc(String(e.descricao).replace(/\s+/g, ' ').trim())
      : '';
    const descCell = descFull
      ? '<div class="sup-equip-desc-cell" title="' + descFull + '">' + descFull + '</div>'
      : '<span class="sup-help">—</span>';

    const thumb = e.foto_principal
      ? `<img src="${esc(e.foto_principal)}" alt="" class="sup-equip-thumb"
              onclick="event.stopPropagation(); abrirLightbox('${esc(e.foto_principal)}')"
              title="Clique pra ampliar">`
      : '<span class="sup-equip-thumb sup-equip-thumb-empty"><i class="bi bi-pc-display"></i></span>';
    return `<tr>
      <td>
        <div style="display:flex;align-items:center;gap:10px">
          ${thumb}
          <strong>${esc(e.nome)}</strong>
        </div>
      </td>
      <td>${descCell}</td>
      <td>${vincsCell}</td>
      <td>${e.ativo ? '<span class="sup-pill ok">Ativo</span>'
                    : '<span class="sup-pill off">Inativo</span>'}</td>
      <td style="white-space:nowrap">
        <button class="btn-sup btn-sup-ghost btn-sup-sm" onclick="editarEquipamento(${e.id})"
                title="Editar / vincular" data-need-admin><i class="bi bi-pencil"></i></button>
      </td>
    </tr>`;
  }).join('');
  aplicarPermissoes();
}

/* Popula select de itens (curso ou treinamento) para o bloco de vinculo,
   com cache. Cada opcao mostra "Agenda - Item". */
async function _carregarOpcoesItens(entidade) {
  if (_opcoesItensCache[entidade]) return _opcoesItensCache[entidade];
  const itens = [];
  const pathPorEntidade = {
    'servico':     a => '/agendas/' + a.id + '/servicos',
    'treinamento': a => '/agendas/' + a.id + '/treinamentos',
    'drone':       a => '/agendas/' + a.id + '/drones',
  };
  const chavePorEntidade = { 'servico': 'servicos', 'treinamento': 'treinamentos', 'drone': 'drones' };
  for (const a of agendas.filter(x => x.ativo)) {
    const r = await apiFetch(pathPorEntidade[entidade](a));
    const lista = r.success ? (r[chavePorEntidade[entidade]] || []) : [];
    lista.forEach(it => itens.push({
      id: it.id, nome: it.nome, agenda_id: a.id, agenda_nome: a.nome,
    }));
  }
  _opcoesItensCache[entidade] = itens;
  return itens;
}

async function onEquipVincTipoChange() {
  const tipo = document.getElementById('equipVincTipo').value;
  const sel = document.getElementById('equipVincItemSel');
  sel.innerHTML = '<option value="">Carregando...</option>';
  const itens = await _carregarOpcoesItens(tipo);
  // exclui os ja vinculados (mesma entidade + entidade_id)
  const jaVinc = new Set(
    equipVincAtuais.filter(v => v.entidade === tipo).map(v => v.entidade_id));
  const livres = itens.filter(i => !jaVinc.has(i.id));
  sel.innerHTML = '<option value="">— Escolha um item —</option>' +
    livres.map(i => `<option value="${i.id}">${esc(i.agenda_nome)} → ${esc(i.nome)}</option>`).join('');
}

function _renderVincList() {
  const box = document.getElementById('equipVincLista');
  if (!equipVincAtuais.length) {
    box.innerHTML = '<div class="sup-help" style="padding:12px;background:#fafafa;border-radius:6px">' +
      'Nenhum vínculo. Use o seletor acima pra adicionar.</div>';
    return;
  }
  box.innerHTML = equipVincAtuais.map((v, idx) => {
    const tipoIcon  = v.entidade === 'treinamento' ? 'bi-easel'
                    : v.entidade === 'drone'       ? 'bi-airplane-engines-fill'
                    : 'bi-mortarboard';
    const tipoLabel = v.entidade === 'treinamento' ? 'Treinamento'
                    : v.entidade === 'drone'       ? 'Drone'
                    : 'Curso';
    return `<div class="sup-midia-video-item">
      <i class="bi ${tipoIcon}"></i>
      <span style="flex:1">
        <strong>${esc(v.nome || ('#' + v.entidade_id))}</strong>
        <span class="sup-help" style="margin-left:6px">(${tipoLabel})</span>
      </span>
      <button type="button" title="Remover" onclick="removerVincLocal(${idx})">
        <i class="bi bi-x-lg"></i>
      </button>
    </div>`;
  }).join('');
}

async function addVinculoEquip() {
  const tipo = document.getElementById('equipVincTipo').value;
  const sel = document.getElementById('equipVincItemSel');
  const itemId = parseInt(sel.value);
  if (!itemId) { toast('Escolha um item.', 'error'); return; }
  const itens = await _carregarOpcoesItens(tipo);
  const item = itens.find(i => i.id === itemId);
  if (!item) return;
  equipVincAtuais.push({
    entidade: tipo, entidade_id: itemId, nome: item.nome,
  });
  _renderVincList();
  // remove do select
  onEquipVincTipoChange();
}

function removerVincLocal(idx) {
  equipVincAtuais.splice(idx, 1);
  _renderVincList();
  onEquipVincTipoChange();
}

async function novoEquipamento() {
  setErro('erroEquip', '');
  document.getElementById('modalEquipTitulo').textContent = 'Novo equipamento';
  document.getElementById('equipId').value = '';
  document.getElementById('equipNome').value = '';
  document.getElementById('equipDescricao').value = '';
  document.getElementById('equipAtivo').checked = true;
  document.getElementById('btnExcluirEquip').style.display = 'none';
  document.getElementById('equipFotosWrap').style.display = 'none';
  equipVincAtuais = [];
  _opcoesItensCache = {};
  _renderVincList();
  document.getElementById('equipVincTipo').value = 'servico';
  await onEquipVincTipoChange();
  abrirModal('modalEquip');
}

async function editarEquipamento(id) {
  const e = equipsSecao.find(x => x.id === id);
  if (!e) return;
  setErro('erroEquip', '');
  document.getElementById('modalEquipTitulo').textContent = 'Editar equipamento';
  document.getElementById('equipId').value = e.id;
  document.getElementById('equipNome').value = e.nome;
  document.getElementById('equipDescricao').value = e.descricao || '';
  document.getElementById('equipAtivo').checked = !!e.ativo;
  document.getElementById('btnExcluirEquip').style.display = _canAdmin ? 'inline-flex' : 'none';
  document.getElementById('equipFotosWrap').style.display = '';
  carregarFotosEquip(e.id);
  equipVincAtuais = (e.vinculos || []).map(v => ({
    entidade: v.entidade, entidade_id: v.entidade_id, nome: v.nome,
  }));
  _opcoesItensCache = {};
  _renderVincList();
  document.getElementById('equipVincTipo').value = 'servico';
  await onEquipVincTipoChange();
  abrirModal('modalEquip');
}

async function salvarEquipamento() {
  const id = document.getElementById('equipId').value;
  const payload = {
    nome: document.getElementById('equipNome').value.trim(),
    descricao: document.getElementById('equipDescricao').value.trim(),
    ativo: document.getElementById('equipAtivo').checked,
    vinculos: equipVincAtuais.map(v => ({
      entidade: v.entidade, entidade_id: v.entidade_id,
    })),
  };
  if (!payload.nome) { setErro('erroEquip', 'Informe o nome.'); return; }
  const r = id
    ? await apiFetch('/equipamentos/' + id, { method: 'PUT', body: JSON.stringify(payload) })
    : await apiFetch('/equipamentos', { method: 'POST', body: JSON.stringify(payload) });
  if (!r.success) { setErro('erroEquip', r.detail || 'Erro ao salvar.'); return; }
  fecharModal('modalEquip');
  toast('Equipamento salvo.', 'success');
  await carregarEquipamentos();
}

async function excluirEquipDoModal() {
  const id = document.getElementById('equipId').value;
  if (!id) return;
  if (!confirm('Excluir este equipamento? Os vínculos com cursos/treinamentos serão removidos.')) return;
  const r = await apiFetch('/equipamentos/' + id, { method: 'DELETE' });
  if (!r.success) { setErro('erroEquip', r.detail || 'Erro ao excluir.'); return; }
  fecharModal('modalEquip');
  toast('Equipamento excluído.', 'success');
  await carregarEquipamentos();
}

// Compat: chamada antiga `excluirEquipamento(id)` (caso ainda apareça em algum render)
async function excluirEquipamento(id) {
  if (!confirm('Excluir este equipamento?')) return;
  const r = await apiFetch('/equipamentos/' + id, { method: 'DELETE' });
  if (!r.success) { toast(r.detail || 'Erro ao excluir.', 'error'); return; }
  toast('Equipamento excluído.', 'success');
  await carregarEquipamentos();
}

/* ============ MIDIA (fotos + videos) — generico ============ */
// `kind` e 'curso' ou 'treino' — define o prefixo dos ids dos elementos
async function carregarMidia(entidade, entidadeId, kind) {
  const r = await apiFetch(`/midia/${entidade}/${entidadeId}`);
  const fotos = r.success ? (r.fotos || []) : [];
  const videos = r.success ? (r.videos || []) : [];
  _renderFotos(kind, entidade, entidadeId, fotos);
  _renderVideos(kind, entidade, entidadeId, videos);
}

function _renderFotos(kind, entidade, entidadeId, fotos) {
  const box = document.getElementById(kind + 'FotosLista');
  if (!box) return;
  if (!fotos.length) {
    box.innerHTML = '<div class="sup-midia-empty">Nenhuma foto enviada ainda.</div>';
    return;
  }
  box.innerHTML = fotos.map(f => `
    <div class="sup-midia-foto">
      <img src="${esc(f.arquivo)}" alt="">
      <button type="button" title="Excluir"
              onclick="excluirFoto(${f.id}, '${entidade}', ${entidadeId}, '${kind}')">
        <i class="bi bi-x"></i>
      </button>
    </div>`).join('');
}

function _renderVideos(kind, entidade, entidadeId, videos) {
  const box = document.getElementById(kind + 'VideosLista');
  if (!box) return;
  if (!videos.length) {
    box.innerHTML = '<div class="sup-midia-empty">Nenhum vídeo cadastrado ainda.</div>';
    return;
  }
  box.innerHTML = videos.map(v => `
    <div class="sup-midia-video-item">
      <i class="bi bi-camera-video"></i>
      <a href="${esc(v.url)}" target="_blank" rel="noopener">
        ${esc(v.titulo || v.url)}
      </a>
      <button type="button" title="Excluir"
              onclick="excluirVideo(${v.id}, '${entidade}', ${entidadeId}, '${kind}')">
        <i class="bi bi-trash"></i>
      </button>
    </div>`).join('');
}

/* ============ EQUIPAMENTOS dentro do modal de curso/treinamento ============ */
// Lista equipamentos vinculados + select pra vincular outro + criar inline.
// `kind` = 'curso' | 'treino'  (prefixo dos ids dos elementos)
// `entidade` = 'servico' | 'treinamento'

async function carregarEquipsVinculados(entidade, entidadeId, kind) {
  const path = entidade === 'servico'
    ? '/servicos/' + entidadeId + '/equipamentos'
    : '/treinamentos/' + entidadeId + '/equipamentos';
  const r = await apiFetch(path);
  const vincs = r.success ? (r.equipamentos || []) : [];
  _renderEquipsVinculados(kind, entidade, entidadeId, vincs);
  await _atualizarSelectEquipsLivres(kind, entidade, entidadeId, vincs);
}

// Resumo curto da descricao (max ~160 chars). Quebra em fronteira de palavra
// e adiciona reticencias quando truncado. Tooltip mostra a descricao completa.
function _resumirDescricao(txt, max) {
  if (!txt) return '';
  const s = String(txt).replace(/\s+/g, ' ').trim();
  const limite = max || 160;
  if (s.length <= limite) return s;
  const corte = s.lastIndexOf(' ', limite);
  return s.slice(0, corte > 60 ? corte : limite) + '…';
}

function _renderEquipsVinculados(kind, entidade, entidadeId, equips) {
  const box = document.getElementById(kind + 'EquipsLista');
  if (!box) return;
  if (!equips.length) {
    box.innerHTML = '<div class="sup-help" style="padding:10px;background:#fafafa;border-radius:6px">' +
      'Nenhum equipamento vinculado ainda.</div>';
    return;
  }
  box.innerHTML = equips.map(e => {
    const resumo = _resumirDescricao(e.descricao, 160);
    const descFull = e.descricao ? esc(String(e.descricao).replace(/\s+/g,' ').trim()) : '';
    const thumb = e.foto_capa
      ? `<img src="${esc(e.foto_capa)}" alt="" class="sup-equip-thumb"
              onclick="abrirLightbox('${esc(e.foto_capa)}')"
              title="Clique para ampliar">`
      : `<div class="sup-equip-thumb sup-equip-thumb-placeholder"><i class="bi bi-pc-display"></i></div>`;
    return `
    <div class="sup-equip-item">
      ${thumb}
      <div style="flex:1;min-width:0">
        <div style="font-weight:600">${esc(e.nome)}</div>
        ${resumo ? `<div class="sup-help sup-equip-desc" title="${descFull}">${esc(resumo)}</div>` : ''}
      </div>
      <button type="button" title="Desvincular"
              onclick="desvincularEquip(${e.id}, '${entidade}', ${entidadeId}, '${kind}')">
        <i class="bi bi-x-lg"></i>
      </button>
    </div>`;
  }).join('');
}

// Popula o select com TODOS os equipamentos ativos. Os ja vinculados
// aparecem desabilitados (em cinza) com a marca "(ja vinculado)".
async function _atualizarSelectEquipsLivres(kind, entidade, entidadeId, jaVinculados) {
  const sel = document.getElementById(kind + 'EquipSel');
  if (!sel) return;
  const r = await apiFetch('/equipamentos');
  const todos = r.success ? (r.equipamentos || []) : [];
  const idsVinc = new Set(jaVinculados.map(e => e.id));
  const ativos = todos.filter(e => e.ativo);
  sel.innerHTML = '<option value="">— Vincular equipamento existente —</option>' +
    ativos.map(e => {
      const vinc = idsVinc.has(e.id);
      return `<option value="${e.id}"${vinc ? ' disabled' : ''}>` +
             `${esc(e.nome)}${vinc ? ' (já vinculado)' : ''}` +
             `</option>`;
    }).join('');
}

async function _vincularEquip(entidade, entidadeId, kind) {
  const sel = document.getElementById(kind + 'EquipSel');
  const equipId = parseInt(sel.value);
  if (!equipId) { toast('Escolha um equipamento.', 'error'); return; }
  const r = await apiFetch('/equipamentos/' + equipId + '/vinculos', {
    method: 'POST', body: JSON.stringify({ entidade, entidade_id: entidadeId }),
  });
  if (!r.success) { toast(r.detail || 'Erro ao vincular.', 'error'); return; }
  toast('Equipamento vinculado.', 'success');
  carregarEquipsVinculados(entidade, entidadeId, kind);
}

async function _criarEquipInline(entidade, entidadeId, kind) {
  const nome = document.getElementById(kind + 'EquipNovoNome').value.trim();
  const desc = document.getElementById(kind + 'EquipNovoDesc').value.trim();
  if (!nome) { toast('Informe o nome do equipamento.', 'error'); return; }
  const r = await apiFetch('/equipamentos', {
    method: 'POST',
    body: JSON.stringify({
      nome, descricao: desc, ativo: true,
      vinculos: [{ entidade, entidade_id: entidadeId }],
    }),
  });
  if (!r.success) { toast(r.detail || 'Erro ao criar.', 'error'); return; }
  // limpa campos e re-recolhe
  document.getElementById(kind + 'EquipNovoNome').value = '';
  document.getElementById(kind + 'EquipNovoDesc').value = '';
  document.getElementById(kind + 'EquipNovoWrap').style.display = 'none';
  toast('Equipamento criado e vinculado.', 'success');
  carregarEquipsVinculados(entidade, entidadeId, kind);
}

async function desvincularEquip(equipId, entidade, entidadeId, kind) {
  if (!confirm('Desvincular este equipamento? (o equipamento continua no catálogo)')) return;
  const params = new URLSearchParams({ entidade, entidade_id: entidadeId });
  const r = await apiFetch('/equipamentos/' + equipId + '/vinculos?' + params, { method: 'DELETE' });
  if (!r.success) { toast(r.detail || 'Erro ao desvincular.', 'error'); return; }
  toast('Desvinculado.', 'success');
  carregarEquipsVinculados(entidade, entidadeId, kind);
}

// Wrappers por kind
function vincularEquipCurso()  { const id = document.getElementById('cursoId').value;   return _vincularEquip('servico',     id, 'curso'); }
function vincularEquipTreino() { const id = document.getElementById('treinoId').value;  return _vincularEquip('treinamento', id, 'treino'); }
function vincularEquipDrone()  { const id = document.getElementById('droneId').value;   return _vincularEquip('drone',       id, 'drone'); }
function criarEquipInlineCurso()  { const id = document.getElementById('cursoId').value;   return _criarEquipInline('servico',     id, 'curso'); }
function criarEquipInlineTreino() { const id = document.getElementById('treinoId').value;  return _criarEquipInline('treinamento', id, 'treino'); }
function criarEquipInlineDrone()  { const id = document.getElementById('droneId').value;   return _criarEquipInline('drone',       id, 'drone'); }
function toggleCriarEquipInlineCurso()  { const w = document.getElementById('cursoEquipNovoWrap');  w.style.display = w.style.display === 'none' ? '' : 'none'; }
function toggleCriarEquipInlineTreino() { const w = document.getElementById('treinoEquipNovoWrap'); w.style.display = w.style.display === 'none' ? '' : 'none'; }
function toggleCriarEquipInlineDrone()  { const w = document.getElementById('droneEquipNovoWrap');  w.style.display = w.style.display === 'none' ? '' : 'none'; }

async function uploadFotosCurso(ev)  { return _uploadFotos(ev, 'servico',     'curso'); }
async function uploadFotosTreino(ev) { return _uploadFotos(ev, 'treinamento', 'treino'); }
async function uploadFotosDrone(ev)  { return _uploadFotos(ev, 'drone',       'drone'); }
async function _uploadFotos(ev, entidade, kind) {
  const files = [...(ev.target.files || [])];
  if (!files.length) return;
  // kind = prefixo do id do form: 'curso' | 'treino' | 'drone'
  const entId = document.getElementById(kind + 'Id').value;
  if (!entId) { toast('Salve primeiro.', 'error'); return; }
  toast(`Enviando ${files.length} foto(s)...`, 'info');
  for (const f of files) {
    const fd = new FormData();
    fd.append('file', f);
    try {
      const res = await fetch(API + `/midia/${entidade}/${entId}/fotos`, {
        method: 'POST', credentials: 'include',
        headers: { 'X-Auth-Token': _token() },
        body: fd,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast(`Falha em ${f.name}: ${err.detail || res.statusText}`, 'error');
      }
    } catch (e) {
      toast(`Erro: ${e.message}`, 'error');
    }
  }
  ev.target.value = '';
  carregarMidia(entidade, entId, kind);
}

async function addVideoCurso()  { return _addVideo('servico',     'curso'); }
async function addVideoTreino() { return _addVideo('treinamento', 'treino'); }
async function addVideoDrone()  { return _addVideo('drone',       'drone'); }
async function _addVideo(entidade, kind) {
  // kind = prefixo dos ids no form: 'curso' | 'treino' | 'drone'
  const entId = document.getElementById(kind + 'Id').value;
  if (!entId) { toast('Salve primeiro.', 'error'); return; }
  const url = document.getElementById(kind + 'VideoUrl').value.trim();
  const titulo = document.getElementById(kind + 'VideoTitulo').value.trim();
  if (!url) { toast('Informe a URL do vídeo.', 'error'); return; }
  const r = await apiFetch(`/midia/${entidade}/${entId}/videos`, {
    method: 'POST', body: JSON.stringify({ url, titulo }),
  });
  if (!r.success) { toast(r.detail || 'Erro ao adicionar.', 'error'); return; }
  document.getElementById(kind + 'VideoUrl').value = '';
  document.getElementById(kind + 'VideoTitulo').value = '';
  carregarMidia(entidade, entId, kind);
}

async function excluirFoto(id, entidade, entidadeId, kind) {
  if (!confirm('Excluir esta foto?')) return;
  const r = await apiFetch(`/midia/fotos/${id}`, { method: 'DELETE' });
  if (!r.success) { toast(r.detail || 'Erro.', 'error'); return; }
  carregarMidia(entidade, entidadeId, kind);
}
async function excluirVideo(id, entidade, entidadeId, kind) {
  if (!confirm('Excluir este vídeo?')) return;
  const r = await apiFetch(`/midia/videos/${id}`, { method: 'DELETE' });
  if (!r.success) { toast(r.detail || 'Erro.', 'error'); return; }
  carregarMidia(entidade, entidadeId, kind);
}

/* ============ FOTOS DO EQUIPAMENTO (so fotos — sem videos) ============ */
async function carregarFotosEquip(equipId) {
  const r = await apiFetch(`/midia/equipamento/${equipId}`);
  const fotos = r.success ? (r.fotos || []) : [];
  _renderFotosEquip(equipId, fotos);
}

function _renderFotosEquip(equipId, fotos) {
  const box = document.getElementById('equipFotosLista');
  if (!box) return;
  if (!fotos.length) {
    box.innerHTML = '<div class="sup-midia-empty">' +
      'Nenhuma foto. Clique em "Enviar fotos" pra adicionar.</div>';
    return;
  }
  box.innerHTML = fotos.map(f => `
    <div class="sup-equip-fotos-item" onclick="abrirLightbox('${esc(f.arquivo)}')"
         title="Clique pra ampliar">
      <img src="${esc(f.arquivo)}" alt="">
      <button type="button" title="Excluir"
              onclick="event.stopPropagation(); excluirFotoEquip(${f.id}, ${equipId})">
        <i class="bi bi-x"></i>
      </button>
    </div>`).join('');
}

async function uploadFotosEquip(ev) {
  const files = [...(ev.target.files || [])];
  if (!files.length) return;
  const equipId = document.getElementById('equipId').value;
  if (!equipId) { toast('Salve primeiro.', 'error'); return; }
  toast(`Enviando ${files.length} foto(s)...`, 'info');
  let okCount = 0, errCount = 0;
  for (const f of files) {
    const fd = new FormData();
    fd.append('file', f);
    try {
      const res = await fetch(API + `/midia/equipamento/${equipId}/fotos`, {
        method: 'POST', credentials: 'include',
        headers: { 'X-Auth-Token': _token() },
        body: fd,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        console.error('[EQUIP-FOTO] HTTP', res.status, err);
        toast(`Falha (${res.status}) em ${f.name}: ${err.detail || res.statusText}`, 'error');
        errCount++;
      } else {
        okCount++;
      }
    } catch (e) {
      console.error('[EQUIP-FOTO] exceção', e);
      toast(`Erro: ${e.message}`, 'error');
      errCount++;
    }
  }
  ev.target.value = '';
  if (okCount) toast(`${okCount} foto(s) enviada(s).`, 'success');
  await carregarFotosEquip(equipId);
  // Atualiza tabela do catalogo pra refletir nova miniatura
  await carregarEquipamentos();
}

async function excluirFotoEquip(fotoId, equipId) {
  if (!confirm('Excluir esta foto?')) return;
  const r = await apiFetch(`/midia/fotos/${fotoId}`, { method: 'DELETE' });
  if (!r.success) { toast(r.detail || 'Erro.', 'error'); return; }
  carregarFotosEquip(equipId);
  carregarEquipamentos();
}

/* ============ LIGHTBOX (clique-pra-ampliar) ============ */
function abrirLightbox(url) {
  const lb = document.getElementById('supLightbox');
  if (!lb) return;
  lb.querySelector('img').src = url;
  lb.classList.add('open');
}
function fecharLightbox() {
  const lb = document.getElementById('supLightbox');
  if (lb) lb.classList.remove('open');
}
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') fecharLightbox();
});

/* ============ SEÇÃO TREINAMENTOS ============ */
let treinosSecao = [];

async function initSecaoTreinamentos() {
  if (!agendas.length) await loadAgendas();
  _opcoesAgendas('treinoAgendaSel');
  if (treinosPreselect) {
    document.getElementById('treinoAgendaSel').value = treinosPreselect;
    treinosPreselect = null;
  }
  await carregarTreinamentos();
}

async function carregarTreinamentos() {
  const agId = document.getElementById('treinoAgendaSel').value;
  const tbody = document.getElementById('tbodyTreinamentos');
  if (!agId) {
    tbody.innerHTML = '<tr><td colspan="7" class="sup-empty">Cadastre uma agenda primeiro.</td></tr>';
    treinosSecao = [];
    return;
  }
  const r = await apiFetch('/agendas/' + agId + '/treinamentos');
  treinosSecao = r.success ? (r.treinamentos || []) : [];
  if (!treinosSecao.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="sup-empty">Nenhum treinamento nesta agenda. Clique em "Novo treinamento".</td></tr>';
    return;
  }
  tbody.innerHTML = treinosSecao.map(t => {
    const vendedor = t.vendedor_nome
      || (t.vendedor_id ? (vendedoresList.find(v => v.id == t.vendedor_id) || {}).name : '');
    return `<tr>
      <td><strong>${esc(t.nome)}</strong>
        ${t.descricao ? '<br><span class="sup-help">' + esc(t.descricao.slice(0,80)) + (t.descricao.length>80?'…':'') + '</span>' : ''}</td>
      <td>${t.instrutor ? '<i class="bi bi-person-badge"></i> ' + esc(t.instrutor) : '<span class="sup-help">—</span>'}</td>
      <td>${vendedor ? esc(vendedor) : '<span class="sup-help">—</span>'}</td>
      <td>${t.duracao_min} min</td>
      <td>
        <span title="Fotos"><i class="bi bi-image"></i> ${t.total_fotos || 0}</span>
        &middot;
        <span title="Vídeos"><i class="bi bi-camera-video"></i> ${t.total_videos || 0}</span>
      </td>
      <td>${t.ativo ? '<span class="sup-pill ok">Ativo</span>'
                    : '<span class="sup-pill off">Inativo</span>'}</td>
      <td style="white-space:nowrap">
        <button class="btn-sup btn-sup-ghost btn-sup-sm" onclick="editarTreinamento(${t.id})"
                title="Editar" data-need-admin><i class="bi bi-pencil"></i></button>
        <button class="btn-sup btn-sup-secondary btn-sup-sm" onclick="abrirModalDuplicar('treinamento', ${t.id}, ${JSON.stringify(t.nome).replace(/"/g, '&quot;')})"
                title="Duplicar para outras unidades" data-need-admin><i class="bi bi-files"></i></button>
        <button class="btn-sup btn-sup-danger btn-sup-sm" onclick="excluirTreinamentoDireto(${t.id}, ${JSON.stringify(t.nome).replace(/"/g, '&quot;')})"
                title="Excluir" data-need-admin><i class="bi bi-trash"></i></button>
      </td>
    </tr>`;
  }).join('');
  aplicarPermissoes();
}

function _agendaAtualTreinos() {
  const id = parseInt(document.getElementById('treinoAgendaSel').value);
  return agendas.find(a => a.id === id) || null;
}
function _adaptarModalTreinoPorTipo() {
  const ag = _agendaAtualTreinos();
  const presWrap = document.getElementById('treinoCapPresencialWrap');
  const grid = document.getElementById('treinoCapWrap');
  if (!presWrap || !grid) return;
  if (ag && ag.tipo === 'online') {
    presWrap.style.display = 'none';
    grid.style.gridTemplateColumns = '1fr';
    document.getElementById('treinoCapPresencial').value = 1;
  } else {
    presWrap.style.display = '';
    grid.style.gridTemplateColumns = '';
  }
}
function onTreinoVendedorChange() {
  if (document.getElementById('treinoVendedorSel').value) {
    document.getElementById('treinoVendedorNome').value = '';
  }
}
function toggleTreinoVendedorManual() {
  const wrap = document.getElementById('treinoVendedorManualWrap');
  wrap.style.display = wrap.style.display === 'none' ? '' : 'none';
}

async function novoTreinamento() {
  setErro('erroTreino', '');
  document.getElementById('modalTreinoTitulo').textContent = 'Novo treinamento';
  document.getElementById('treinoId').value = '';
  document.getElementById('treinoNome').value = '';
  document.getElementById('treinoDescricao').value = '';
  document.getElementById('treinoDuracao').value = 120;
  document.getElementById('treinoCapPresencial').value = 1;
  document.getElementById('treinoCapOnline').value = 1;
  document.getElementById('treinoInstrutor').value = '';
  document.getElementById('treinoVendedorNome').value = '';
  document.getElementById('treinoVendedorManualWrap').style.display = 'none';
  document.getElementById('treinoAtivo').checked = true;
  document.getElementById('treinoMidiaWrap').style.display = 'none';
  document.getElementById('treinoEquipsWrap').style.display = 'none';
  document.getElementById('btnExcluirTreino').style.display = 'none';
  await _popularSelectVendedor('treinoVendedorSel');
  _adaptarModalTreinoPorTipo();
  abrirModal('modalTreinamento');
}

async function editarTreinamento(id) {
  const t = treinosSecao.find(x => x.id === id);
  if (!t) return;
  setErro('erroTreino', '');
  document.getElementById('modalTreinoTitulo').textContent = 'Editar treinamento';
  document.getElementById('treinoId').value = t.id;
  document.getElementById('treinoNome').value = t.nome;
  document.getElementById('treinoDescricao').value = t.descricao || '';
  document.getElementById('treinoDuracao').value = t.duracao_min;
  document.getElementById('treinoCapPresencial').value = t.cap_presencial || 1;
  document.getElementById('treinoCapOnline').value = t.cap_online || 1;
  document.getElementById('treinoInstrutor').value = t.instrutor || '';
  document.getElementById('treinoVendedorNome').value = t.vendedor_nome || '';
  document.getElementById('treinoVendedorManualWrap').style.display = t.vendedor_nome ? '' : 'none';
  document.getElementById('treinoAtivo').checked = !!t.ativo;
  document.getElementById('btnExcluirTreino').style.display = _canAdmin ? 'inline-flex' : 'none';
  await _popularSelectVendedor('treinoVendedorSel', t.vendedor_id);
  document.getElementById('treinoMidiaWrap').style.display = '';
  document.getElementById('treinoEquipsWrap').style.display = '';
  document.getElementById('treinoEquipNovoWrap').style.display = 'none';
  document.getElementById('treinoBannerWrap').style.display = '';
  document.getElementById('treinoModulosWrap').style.display = '';
  carregarMidia('treinamento', t.id, 'treino');
  carregarEquipsVinculados('treinamento', t.id, 'treino');
  carregarBanner('treinamento', t.id, 'treino', t.banner_url);
  carregarModulos('treinamento', t.id, 'treino');
  _adaptarModalTreinoPorTipo();
  abrirModal('modalTreinamento');
}

async function salvarTreinamento() {
  const id = document.getElementById('treinoId').value;
  const payload = {
    agenda_id: document.getElementById('treinoAgendaSel').value,
    nome: document.getElementById('treinoNome').value.trim(),
    descricao: document.getElementById('treinoDescricao').value.trim(),
    duracao_min: parseInt(document.getElementById('treinoDuracao').value) || 120,
    cap_presencial: parseInt(document.getElementById('treinoCapPresencial').value) || 1,
    cap_online: parseInt(document.getElementById('treinoCapOnline').value) || 1,
    instrutor: document.getElementById('treinoInstrutor').value.trim(),
    vendedor_id: document.getElementById('treinoVendedorSel').value || null,
    vendedor_nome: document.getElementById('treinoVendedorNome').value.trim(),
    ativo: document.getElementById('treinoAtivo').checked,
  };
  if (!payload.nome) { setErro('erroTreino', 'Informe o nome.'); return; }
  const r = id
    ? await apiFetch('/treinamentos/' + id, { method: 'PUT', body: JSON.stringify(payload) })
    : await apiFetch('/treinamentos', { method: 'POST', body: JSON.stringify(payload) });
  if (!r.success) { setErro('erroTreino', r.detail || 'Erro ao salvar.'); return; }
  fecharModal('modalTreinamento');
  toast('Treinamento salvo.', 'success');
  await carregarTreinamentos();
}

async function excluirTreinamento() {
  const id = document.getElementById('treinoId').value;
  if (!id || !confirm('Excluir este treinamento? Fotos e vídeos vinculados serão removidos.')) return;
  const r = await apiFetch('/treinamentos/' + id, { method: 'DELETE' });
  if (!r.success) { setErro('erroTreino', r.detail || 'Erro ao excluir.'); return; }
  fecharModal('modalTreinamento');
  toast('Treinamento excluído.', 'success');
  await carregarTreinamentos();
}

/* ============================================================
   DRONES — espelho de treinamentos (sem colisão com curso/treino)
   ============================================================ */
let dronesSecao = [];

async function initSecaoDrones() {
  if (!agendas.length) await loadAgendas();
  // Drone é apenas presencial — não listar agendas online no select
  _opcoesAgendas('droneAgendaSel', a => (a.tipo || 'fisica') !== 'online');
  if (dronesPreselect) {
    document.getElementById('droneAgendaSel').value = dronesPreselect;
    dronesPreselect = null;
  }
  await carregarDrones();
}

async function carregarDrones() {
  const agId = document.getElementById('droneAgendaSel').value;
  const tbody = document.getElementById('tbodyDrones');
  if (!agId) {
    tbody.innerHTML = '<tr><td colspan="7" class="sup-empty">Cadastre uma agenda primeiro.</td></tr>';
    dronesSecao = [];
    return;
  }
  const r = await apiFetch('/agendas/' + agId + '/drones');
  dronesSecao = r.success ? (r.drones || []) : [];
  if (!dronesSecao.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="sup-empty">Nenhum drone nesta agenda. Clique em "Novo drone".</td></tr>';
    return;
  }
  tbody.innerHTML = dronesSecao.map(d => {
    const vendedor = d.vendedor_nome
      || (d.vendedor_id ? (vendedoresList.find(v => v.id == d.vendedor_id) || {}).name : '');
    return `<tr>
      <td><strong>${esc(d.nome)}</strong>
        ${d.descricao ? '<br><span class="sup-help">' + esc(d.descricao.slice(0,80)) + (d.descricao.length>80?'…':'') + '</span>' : ''}</td>
      <td>${d.instrutor ? '<i class="bi bi-person-badge"></i> ' + esc(d.instrutor) : '<span class="sup-help">—</span>'}</td>
      <td>${vendedor ? esc(vendedor) : '<span class="sup-help">—</span>'}</td>
      <td>${d.duracao_min} min</td>
      <td>
        <span title="Fotos"><i class="bi bi-image"></i> ${d.total_fotos || 0}</span>
        &middot;
        <span title="Vídeos"><i class="bi bi-camera-video"></i> ${d.total_videos || 0}</span>
      </td>
      <td>${d.ativo ? '<span class="sup-pill ok">Ativo</span>'
                    : '<span class="sup-pill off">Inativo</span>'}</td>
      <td style="white-space:nowrap">
        <button class="btn-sup btn-sup-ghost btn-sup-sm" onclick="editarDrone(${d.id})"
                title="Editar" data-need-admin><i class="bi bi-pencil"></i></button>
        <button class="btn-sup btn-sup-secondary btn-sup-sm" onclick="abrirModalDuplicar('drone', ${d.id}, ${JSON.stringify(d.nome).replace(/"/g, '&quot;')})"
                title="Duplicar para outras unidades" data-need-admin><i class="bi bi-files"></i></button>
        <button class="btn-sup btn-sup-danger btn-sup-sm" onclick="excluirDroneDireto(${d.id}, ${JSON.stringify(d.nome).replace(/"/g, '&quot;')})"
                title="Excluir" data-need-admin><i class="bi bi-trash"></i></button>
      </td>
    </tr>`;
  }).join('');
  aplicarPermissoes();
}

function _agendaAtualDrones() {
  const id = parseInt(document.getElementById('droneAgendaSel').value);
  return agendas.find(a => a.id === id) || null;
}
/* Drone é APENAS presencial — esconde "Capacidade online" SEMPRE
   e força cap_online=0. Frontend espelha a regra do backend. */
function _adaptarModalDronePorTipo() {
  const onlineWrap = document.getElementById('droneCapOnlineWrap');
  const grid = document.getElementById('droneCapWrap');
  if (!onlineWrap || !grid) return;
  onlineWrap.style.display = 'none';
  grid.style.gridTemplateColumns = '1fr';
  const onlineInput = document.getElementById('droneCapOnline');
  if (onlineInput) onlineInput.value = 0;
}
function onDroneVendedorChange() {
  if (document.getElementById('droneVendedorSel').value) {
    document.getElementById('droneVendedorNome').value = '';
  }
}
function toggleDroneVendedorManual() {
  const wrap = document.getElementById('droneVendedorManualWrap');
  wrap.style.display = wrap.style.display === 'none' ? '' : 'none';
}
function onDroneInstrutorChange() {
  // Se o usuário escolheu um piloto do select, limpa o campo manual
  if (document.getElementById('droneInstrutorSel').value) {
    const m = document.getElementById('droneInstrutor');
    if (m) m.value = '';
  }
}
function toggleDroneInstrutorManual() {
  const wrap = document.getElementById('droneInstrutorManualWrap');
  wrap.style.display = wrap.style.display === 'none' ? '' : 'none';
}

/* Caches globais de instrutores por grupo. Carregam na 1a vez que precisam. */
let pilotosList = [];           // grupo Drone (pilotos)
let instrutoresSuporteList = []; // grupo Suporte (instrutores de treinamento/curso)

/* Compat: cadastro de drone continua usando _popularSelectPilotos
   (lista APENAS pilotos do grupo Drone, comportamento original). */
async function _popularSelectPilotos(selId, piloto_id) {
  if (!pilotosList.length) {
    const r = await apiFetch('/pilotos');
    pilotosList = r.success ? (r.pilotos || []) : [];
  }
  const sel = document.getElementById(selId);
  if (!sel) return;
  sel.innerHTML = '<option value="">— Sem piloto padrão —</option>' +
    pilotosList.map(p => `<option value="${p.id}">${esc(p.name)}</option>`).join('');
  if (piloto_id) sel.value = String(piloto_id);
}

/* Generalizada (2026-06-17): popula select com instrutores do grupo escolhido.
   Aceita 'Drone' (pilotos) ou 'Suporte' (instrutores de treinamento).
   Mantem valor pre-selecionado (preserva escolha do user quando troca tipo). */
async function _popularSelectInstrutores(selId, grupo) {
  const sel = document.getElementById(selId);
  if (!sel) return;
  // Preserva selecao anterior antes de re-renderizar (UX: trocar tipo nao
  // perde o instrutor escolhido se ele estiver na lista do novo grupo).
  const selecionadoAntes = sel.value;

  let lista;
  if (grupo === 'Drone') {
    if (!pilotosList.length) {
      const r = await apiFetch('/pilotos');
      pilotosList = r.success ? (r.pilotos || []) : [];
    }
    lista = pilotosList;
  } else {
    // Default: 'Suporte' (qualquer outro valor cai aqui)
    if (!instrutoresSuporteList.length) {
      const r = await apiFetch('/instrutores-suporte');
      instrutoresSuporteList = r.success ? (r.instrutores || []) : [];
    }
    lista = instrutoresSuporteList;
  }

  const labelVazio = grupo === 'Drone' ? '— Sem piloto —' : '— Sem instrutor —';
  sel.innerHTML = `<option value="">${labelVazio}</option>` +
    lista.map(p => `<option value="${p.id}">${esc(p.name)}</option>`).join('');

  // Restaura selecao se o id ainda existe no novo grupo
  if (selecionadoAntes && lista.some(p => String(p.id) === selecionadoAntes)) {
    sel.value = selecionadoAntes;
  }
}

async function novoDrone() {
  setErro('erroDrone', '');
  document.getElementById('modalDroneTitulo').textContent = 'Novo drone';
  document.getElementById('droneId').value = '';
  document.getElementById('droneNome').value = '';
  document.getElementById('droneDescricao').value = '';
  document.getElementById('droneDuracao').value = 60;
  document.getElementById('droneCapPresencial').value = 1;
  document.getElementById('droneCapOnline').value = 1;
  document.getElementById('droneInstrutor').value = '';
  document.getElementById('droneInstrutorManualWrap').style.display = 'none';
  document.getElementById('droneVendedorNome').value = '';
  document.getElementById('droneVendedorManualWrap').style.display = 'none';
  document.getElementById('droneAtivo').checked = true;
  document.getElementById('droneMidiaWrap').style.display = 'none';
  document.getElementById('droneEquipsWrap').style.display = 'none';
  document.getElementById('btnExcluirDrone').style.display = 'none';
  await Promise.all([
    _popularSelectVendedor('droneVendedorSel'),
    _popularSelectPilotos('droneInstrutorSel'),
  ]);
  _adaptarModalDronePorTipo();
  abrirModal('modalDrone');
}

async function editarDrone(id) {
  const d = dronesSecao.find(x => x.id === id);
  if (!d) return;
  setErro('erroDrone', '');
  document.getElementById('modalDroneTitulo').textContent = 'Editar drone';
  document.getElementById('droneId').value = d.id;
  document.getElementById('droneNome').value = d.nome;
  document.getElementById('droneDescricao').value = d.descricao || '';
  document.getElementById('droneDuracao').value = d.duracao_min;
  document.getElementById('droneCapPresencial').value = d.cap_presencial || 1;
  document.getElementById('droneCapOnline').value = d.cap_online || 1;
  document.getElementById('droneVendedorNome').value = d.vendedor_nome || '';
  document.getElementById('droneVendedorManualWrap').style.display = d.vendedor_nome ? '' : 'none';
  document.getElementById('droneAtivo').checked = !!d.ativo;
  document.getElementById('btnExcluirDrone').style.display = _canAdmin ? 'inline-flex' : 'none';
  await Promise.all([
    _popularSelectVendedor('droneVendedorSel', d.vendedor_id),
    _popularSelectPilotos('droneInstrutorSel'),
  ]);
  // Instrutor: tenta casar com a lista de pilotos pelo nome. Se achar, seleciona o id;
  // senão, mostra como "manual" (texto livre).
  const sel = document.getElementById('droneInstrutorSel');
  const inputManual = document.getElementById('droneInstrutor');
  const manualWrap = document.getElementById('droneInstrutorManualWrap');
  const matchPiloto = d.instrutor
    ? pilotosList.find(p => p.name === d.instrutor)
    : null;
  if (matchPiloto) {
    sel.value = String(matchPiloto.id);
    inputManual.value = '';
    manualWrap.style.display = 'none';
  } else if (d.instrutor) {
    sel.value = '';
    inputManual.value = d.instrutor;
    manualWrap.style.display = '';
  } else {
    sel.value = '';
    inputManual.value = '';
    manualWrap.style.display = 'none';
  }
  document.getElementById('droneMidiaWrap').style.display = '';
  document.getElementById('droneEquipsWrap').style.display = '';
  document.getElementById('droneEquipNovoWrap').style.display = 'none';
  document.getElementById('droneBannerWrap').style.display = '';
  document.getElementById('droneModulosWrap').style.display = '';
  carregarMidia('drone', d.id, 'drone');
  carregarEquipsVinculados('drone', d.id, 'drone');
  carregarBanner('drone', d.id, 'drone', d.banner_url);
  carregarModulos('drone', d.id, 'drone');
  _adaptarModalDronePorTipo();
  abrirModal('modalDrone');
}

async function salvarDrone() {
  const id = document.getElementById('droneId').value;
  // Piloto: prioridade pra select (grupo Drone). Se vazio, usa o texto livre.
  const pilotoId = document.getElementById('droneInstrutorSel').value;
  const pilotoSel = pilotoId ? pilotosList.find(p => String(p.id) === pilotoId) : null;
  const pilotoNome = pilotoSel
    ? pilotoSel.name
    : document.getElementById('droneInstrutor').value.trim();
  const payload = {
    agenda_id: document.getElementById('droneAgendaSel').value,
    nome: document.getElementById('droneNome').value.trim(),
    descricao: document.getElementById('droneDescricao').value.trim(),
    duracao_min: parseInt(document.getElementById('droneDuracao').value) || 60,
    cap_presencial: parseInt(document.getElementById('droneCapPresencial').value) || 1,
    cap_online: parseInt(document.getElementById('droneCapOnline').value) || 1,
    instrutor: pilotoNome,
    vendedor_id: document.getElementById('droneVendedorSel').value || null,
    vendedor_nome: document.getElementById('droneVendedorNome').value.trim(),
    ativo: document.getElementById('droneAtivo').checked,
  };
  if (!payload.nome) { setErro('erroDrone', 'Informe o nome.'); return; }
  const r = id
    ? await apiFetch('/drones/' + id, { method: 'PUT', body: JSON.stringify(payload) })
    : await apiFetch('/drones', { method: 'POST', body: JSON.stringify(payload) });
  if (!r.success) { setErro('erroDrone', r.detail || 'Erro ao salvar.'); return; }
  fecharModal('modalDrone');
  toast('Drone salvo.', 'success');
  await carregarDrones();
}

async function excluirDrone() {
  const id = document.getElementById('droneId').value;
  if (!id || !confirm('Excluir este drone? Fotos e vídeos vinculados serão removidos.')) return;
  const r = await apiFetch('/drones/' + id, { method: 'DELETE' });
  if (!r.success) { setErro('erroDrone', r.detail || 'Erro ao excluir.'); return; }
  fecharModal('modalDrone');
  toast('Drone excluído.', 'success');
  await carregarDrones();
}

async function excluirDroneDireto(id, nome) {
  if (!confirm(`Excluir o drone "${nome}"?\n\nEsta ação remove:\n- O drone\n- Fotos e vídeos vinculados\n- Vínculos com equipamentos\n\nAgendamentos passados ficam preservados (sem referência).`)) return;
  try {
    const r = await apiFetch('/drones/' + id, { method: 'DELETE' });
    if (!r.success) {
      toast('Erro: ' + (r.detail || 'falha'), 'error');
      return;
    }
    toast('Drone excluído', 'success');
    carregarDrones();
  } catch (e) {
    alert('Erro de rede: ' + (e.message || e));
  }
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
        <button class="btn-sup btn-sup-ghost btn-sup-sm" title="Ver treinamentos"
          onclick="fecharModal('modalListaAgendas'); irParaTreinamentos(${a.id})">
          <i class="bi bi-easel"></i></button>
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
        <button class="btn-sup btn-sup-primary btn-sup-sm" onclick="confirmarPendente(${p.id})" data-need-op>
          <i class="bi bi-check-lg"></i> Confirmar</button>
        <button class="btn-sup btn-sup-danger btn-sup-sm" onclick="recusarPendente(${p.id})" data-need-op>
          <i class="bi bi-x-lg"></i> Recusar</button>
      </td></tr>`;
  }).join('');
  aplicarPermissoes();
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

/* ============ SEÇÃO CLIENTES ============ */
let clientesSecao = [];

async function initSecaoClientes() {
  document.getElementById('buscaCliente').value = '';
  const tbody = document.getElementById('tbodyClientes');
  tbody.innerHTML = '<tr><td colspan="6" class="sup-empty">Carregando...</td></tr>';
  const r = await apiFetch('/clientes');
  clientesSecao = r.success ? (r.clientes || []) : [];
  renderClientes();
}

function renderClientes() {
  const busca = (document.getElementById('buscaCliente').value || '').toLowerCase().trim();
  const lista = clientesSecao.filter(c => {
    if (!busca) return true;
    return (c.nome || '').toLowerCase().includes(busca)
        || (c.email || '').toLowerCase().includes(busca)
        || (c.empresa || '').toLowerCase().includes(busca)
        || (c.telefone || '').toLowerCase().includes(busca);
  });
  const tbody = document.getElementById('tbodyClientes');
  if (!lista.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="sup-empty">' +
      (clientesSecao.length ? 'Nenhum cliente encontrado.' : 'Ainda não há clientes na base. Eles aparecem após o primeiro agendamento público.') +
      '</td></tr>';
    return;
  }
  tbody.innerHTML = lista.map(c => {
    const empresaFuncao = [c.empresa, c.funcao].filter(Boolean).map(esc).join('<br><span class="sup-help">');
    const ult = c.ultimo_contato ? fmtDataBR(c.ultimo_contato) : '—';
    const totA = c.total_atendidos || 0;
    const totC = c.total_cancelados || 0;
    return `<tr>
      <td><strong>${esc(c.nome || '—')}</strong></td>
      <td>${empresaFuncao ? empresaFuncao + (c.funcao ? '</span>' : '') : '<span class="sup-help">—</span>'}</td>
      <td>${esc(c.email)}${c.telefone
        ? '<br><span class="sup-help">' + esc(c.telefone) + '</span>' : ''}</td>
      <td>
        <strong>${c.total_agendamentos}</strong> total
        <span class="sup-help">(${totA} atendidos, ${totC} cancelados)</span>
      </td>
      <td>${ult}</td>
      <td style="white-space:nowrap">
        <button class="btn-sup btn-sup-ghost btn-sup-sm" title="Ver histórico"
                onclick="verHistoricoCliente('${esc(c.email)}', '${esc(c.nome || '')}')">
          <i class="bi bi-eye"></i> Histórico
        </button>
        <button class="btn-sup btn-sup-ghost btn-sup-sm" title="Editar"
                data-need-admin
                onclick="editarCliente('${esc(c.email)}')">
          <i class="bi bi-pencil"></i>
        </button>
      </td>
    </tr>`;
  }).join('');
  aplicarPermissoes();
}

/* ====== Editar cliente (admin do modulo) ====== */
function editarCliente(email) {
  const c = clientesSecao.find(x => x.email === email);
  if (!c) return;
  setErro('erroEditarCliente', '');
  document.getElementById('edClienteEmail').value         = c.email;
  document.getElementById('edClienteEmailDisplay').value  = c.email;
  document.getElementById('edClienteNome').value          = c.nome || '';
  document.getElementById('edClienteTelefone').value      = c.telefone || '';
  document.getElementById('edClienteEmpresa').value       = c.empresa || '';
  document.getElementById('edClienteFuncao').value        = c.funcao || '';
  abrirModal('modalEditarCliente');
}

async function salvarEdicaoCliente() {
  const payload = {
    email:    document.getElementById('edClienteEmail').value,
    nome:     document.getElementById('edClienteNome').value.trim(),
    telefone: document.getElementById('edClienteTelefone').value.trim(),
    empresa:  document.getElementById('edClienteEmpresa').value.trim(),
    funcao:   document.getElementById('edClienteFuncao').value.trim(),
  };
  if (!payload.nome) { setErro('erroEditarCliente', 'Informe o nome.'); return; }
  const r = await apiFetch('/clientes', { method: 'PUT', body: JSON.stringify(payload) });
  if (!r.success) { setErro('erroEditarCliente', r.detail || 'Erro ao salvar.'); return; }
  fecharModal('modalEditarCliente');
  toast(`Cliente atualizado (${r.atualizados} agendamento(s) afetados).`, 'success');
  await initSecaoClientes();
}

/* ====== Exportar CSV (client-side, do que está filtrado) ====== */
function exportarClientesCSV() {
  const busca = (document.getElementById('buscaCliente').value || '').toLowerCase().trim();
  const lista = clientesSecao.filter(c => {
    if (!busca) return true;
    return (c.nome || '').toLowerCase().includes(busca)
        || (c.email || '').toLowerCase().includes(busca)
        || (c.empresa || '').toLowerCase().includes(busca)
        || (c.telefone || '').toLowerCase().includes(busca);
  });
  if (!lista.length) { toast('Nenhum cliente para exportar.', 'error'); return; }

  const cols = ['Nome', 'Email', 'Telefone', 'Empresa', 'Funcao',
                'Total agendamentos', 'Atendidos', 'Cancelados',
                'Primeiro contato', 'Ultimo contato'];
  const cell = v => {
    const s = String(v == null ? '' : v).replace(/"/g, '""');
    return /[",\n;]/.test(s) ? `"${s}"` : s;
  };
  const rows = lista.map(c => [
    c.nome, c.email, c.telefone, c.empresa, c.funcao,
    c.total_agendamentos, c.total_atendidos, c.total_cancelados,
    c.primeiro_contato ? fmtDataBR(c.primeiro_contato) : '',
    c.ultimo_contato   ? fmtDataBR(c.ultimo_contato)   : '',
  ].map(cell).join(';'));
  // BOM UTF-8 pra Excel abrir com acentos corretos
  const csv = '﻿' + cols.join(';') + '\n' + rows.join('\n');

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const stamp = new Date().toISOString().slice(0, 10);
  a.href = url;
  a.download = `clientes-cpe-${stamp}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  toast(`Exportado: ${lista.length} cliente(s).`, 'success');
}

async function verHistoricoCliente(email, nome) {
  document.getElementById('modalClienteTitulo').textContent = nome || email;
  document.getElementById('tbodyHistorico').innerHTML =
    '<tr><td colspan="6" class="sup-empty">Carregando...</td></tr>';
  // Header com dados do cliente
  const c = clientesSecao.find(x => x.email === email) || {};
  document.getElementById('modalClienteHeader').innerHTML = `
    <div><strong>E-mail</strong><br>${esc(c.email)}</div>
    <div><strong>Telefone</strong><br>${esc(c.telefone || '—')}</div>
    <div><strong>Empresa</strong><br>${esc(c.empresa || '—')}</div>
    <div><strong>Função</strong><br>${esc(c.funcao || '—')}</div>
  `;
  abrirModal('modalCliente');

  const r = await apiFetch('/clientes/historico?email=' + encodeURIComponent(email));
  const hist = r.success ? (r.historico || []) : [];
  const tbody = document.getElementById('tbodyHistorico');
  if (!hist.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="sup-empty">Sem agendamentos.</td></tr>';
    return;
  }
  tbody.innerHTML = hist.map(h => {
    const dt = parseDT(h.inicio);
    const data = `${fmtDataBR(h.inicio)}<br><span class="sup-help">${hm(dt)}</span>`;
    const tipoTag = h.tipo_oferta === 'treinamento'
      ? '<span class="sup-pill pendente">Treinamento</span>'
      : '<span class="sup-pill agendado">Curso</span>';
    const modal = h.modalidade === 'online'
      ? '<i class="bi bi-camera-video"></i> Online'
      : h.modalidade === 'presencial'
        ? '<i class="bi bi-buildings"></i> Presencial' : '—';
    return `<tr>
      <td>${data}</td>
      <td>${tipoTag}<br><strong>${esc(h.oferta_nome || h.titulo || '—')}</strong></td>
      <td>${esc(h.instrutor || '—')}</td>
      <td>${esc(h.unidade_nome || h.agenda_nome || '—')}</td>
      <td>${modal}</td>
      <td><span class="sup-pill ${h.status}">${rotuloStatus(h.status)}</span></td>
    </tr>`;
  }).join('');
}

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
        onclick="excluirFeriado(${f.id}, ${nacional})" data-need-admin><i class="bi bi-trash"></i></button></td>
    </tr>`;
  }).join('');
  aplicarPermissoes();
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
  await carregarPermissoes();    // descobre o nivel do user antes de renderizar
  await carregarUnidades();
  await loadDashboard();
  // sino: primeira carga + poll a cada 30s
  carregarNotificacoes();
  if (_notifTimer) clearInterval(_notifTimer);
  _notifTimer = setInterval(carregarNotificacoes, 30000);
  document.getElementById('supLoading').style.display = 'none';
});


/* ============================================================
   DUPLICAR (cursos e treinamentos) para outras unidades
   ============================================================ */
let _dupCtx = null;  // {tipo:'curso'|'treinamento', id, origemAgendaId}

function abrirModalDuplicar(tipo, id, nome) {
  const listaPorTipo = {
    'curso':        cursosSecao,
    'treinamento':  treinosSecao,
    'drone':        dronesSecao,
  };
  const lista = listaPorTipo[tipo] || [];
  const item = lista.find(x => x.id == id);
  const agendaOrigemId = item ? item.agenda_id : null;
  _dupCtx = { tipo, id, agendaOrigemId };

  document.getElementById('dupId').value = id;
  document.getElementById('dupTipo').value = tipo;
  document.getElementById('dupOrigem').textContent = (nome || '—') + ' (id ' + id + ')';
  const titulosPorTipo = {
    'curso':       'Duplicar curso para outras unidades',
    'treinamento': 'Duplicar treinamento para outras unidades',
    'drone':       'Duplicar drone para outras unidades',
  };
  document.getElementById('modalDupTitulo').textContent =
    titulosPorTipo[tipo] || 'Duplicar para outras unidades';
  document.getElementById('erroDup').innerHTML = '';

  // Lista de agendas (todas EXCETO a de origem)
  const cont = document.getElementById('dupAgendasList');
  const destinos = (agendas || []).filter(a => a.id !== agendaOrigemId);
  if (!destinos.length) {
    cont.innerHTML = '<div class="sup-empty">Não há outras unidades disponíveis para duplicação.</div>';
  } else {
    cont.innerHTML = destinos.map(a => `
      <label style="display:flex;align-items:center;gap:10px;padding:8px 10px;
                    border-radius:6px;cursor:pointer;transition:background .1s"
             onmouseover="this.style.background='#fffbe8'"
             onmouseout="this.style.background='transparent'">
        <input type="checkbox" class="dup-agenda-cb" value="${a.id}">
        <span style="flex:1">
          <strong>${esc(a.nome)}</strong>
          ${a.tipo === 'online' ? ' <span class="sup-pill" style="background:#dbeafe;color:#1e40af;font-size:.7rem">ONLINE</span>' : ''}
        </span>
        ${a.ativo ? '' : '<span class="sup-pill off">Inativa</span>'}
      </label>
    `).join('');
  }

  document.getElementById('modalDuplicar').classList.add('show');
}

function dupMarcarTodas(marcar) {
  document.querySelectorAll('#dupAgendasList .dup-agenda-cb').forEach(cb => {
    cb.checked = !!marcar;
  });
}

async function confirmarDuplicar() {
  if (!_dupCtx) return;
  const cbs = document.querySelectorAll('#dupAgendasList .dup-agenda-cb:checked');
  const agenda_ids = Array.from(cbs).map(cb => parseInt(cb.value, 10)).filter(Boolean);

  if (!agenda_ids.length) {
    document.getElementById('erroDup').innerHTML =
      '<div class="sup-modal-erro-msg">Selecione pelo menos uma unidade destino.</div>';
    return;
  }

  const endpointPorTipo = {
    'curso':       '/servicos/' + _dupCtx.id + '/duplicar',
    'treinamento': '/treinamentos/' + _dupCtx.id + '/duplicar',
    'drone':       '/drones/' + _dupCtx.id + '/duplicar',
  };
  const endpoint = endpointPorTipo[_dupCtx.tipo];

  try {
    const r = await apiFetch(endpoint, {
      method: 'POST',
      body: JSON.stringify({ agenda_ids }),
    });
    if (!r.success) {
      document.getElementById('erroDup').innerHTML =
        '<div class="sup-modal-erro-msg">Erro: ' + esc(r.detail || 'falha desconhecida') + '</div>';
      return;
    }
    fecharModal('modalDuplicar');
    const msg = `Duplicado em ${r.duplicados} unidade(s)` +
      (r.equipamentos_replicados ? ` — ${r.equipamentos_replicados} equipamento(s) vinculado(s)` : '') +
      (r.ignorados && r.ignorados.length ? ` (${r.ignorados.length} ignoradas)` : '');
    if (typeof toast === 'function') toast(msg, 'success');
    else alert(msg);
    // Recarrega a lista da agenda atual
    if (_dupCtx.tipo === 'curso')           carregarCursos();
    else if (_dupCtx.tipo === 'treinamento') carregarTreinamentos();
    else if (_dupCtx.tipo === 'drone')      carregarDrones();
  } catch (e) {
    document.getElementById('erroDup').innerHTML =
      '<div class="sup-modal-erro-msg">Erro de rede: ' + esc(e.message || e) + '</div>';
  }
}

/* ============================================================
   EXCLUIR DIRETO (treinamento — versão sem modal de edição aberta)
   curso já tem excluirCurso() chamada direta na linha.
   ============================================================ */
async function excluirTreinamentoDireto(id, nome) {
  if (!confirm(`Excluir o treinamento "${nome}"?\n\nEsta ação remove:\n- O treinamento\n- Fotos e vídeos vinculados\n- Vínculos com equipamentos\n\nAgendamentos passados ficam preservados (sem referência).`)) return;
  try {
    const r = await apiFetch('/treinamentos/' + id, { method: 'DELETE' });
    if (!r.success) {
      if (typeof toast === 'function') toast('Erro: ' + (r.detail || 'falha'), 'error');
      else alert('Erro ao excluir: ' + (r.detail || 'falha desconhecida'));
      return;
    }
    if (typeof toast === 'function') toast('Treinamento excluído', 'success');
    carregarTreinamentos();
  } catch (e) {
    alert('Erro de rede: ' + (e.message || e));
  }
}


/* ============================================================
   BANNER por entidade (curso / treinamento / drone)
   Upload separado da galeria. POST/DELETE /midia/{entidade}/{id}/banner
   ============================================================ */
function carregarBanner(entidade, entidadeId, kind, urlInicial) {
  const preview = document.getElementById(kind + 'BannerPreview');
  const btnDel  = document.getElementById(kind + 'BannerExcluirBtn');
  if (!preview) return;
  if (urlInicial) {
    preview.innerHTML = '<img src="' + esc(urlInicial) + '" alt="Banner">';
    if (btnDel) btnDel.style.display = '';
  } else {
    preview.innerHTML = '<div class="sup-banner-preview-vazio">'
      + '<i class="bi bi-image"></i>Nenhum banner enviado ainda.</div>';
    if (btnDel) btnDel.style.display = 'none';
  }
}

async function _uploadBanner(ev, entidade, entidadeId, kind) {
  const file = (ev.target.files || [])[0];
  if (!file) return;
  if (!entidadeId) { toast('Salve primeiro antes de enviar o banner.', 'error'); return; }
  const fd = new FormData();
  fd.append('file', file);
  try {
    const res = await fetch(API + '/midia/' + entidade + '/' + entidadeId + '/banner', {
      method: 'POST', credentials: 'include',
      headers: { 'X-Auth-Token': _token() },
      body: fd,
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      toast(data.detail || ('Erro ' + res.status), 'error');
      return;
    }
    toast('Banner enviado!', 'success');
    carregarBanner(entidade, entidadeId, kind, data.banner_url);
  } catch (e) {
    toast('Falha no upload: ' + (e.message || e), 'error');
  }
  ev.target.value = '';
}

async function _excluirBanner(entidade, entidadeId, kind) {
  if (!confirm('Remover o banner atual?')) return;
  const r = await apiFetch('/midia/' + entidade + '/' + entidadeId + '/banner', { method: 'DELETE' });
  if (!r.success) { toast(r.detail || 'Erro ao remover.', 'error'); return; }
  toast('Banner removido.', 'success');
  carregarBanner(entidade, entidadeId, kind, null);
}

function uploadBannerCurso(ev)  { return _uploadBanner(ev, 'servico',     document.getElementById('cursoId').value, 'curso'); }
function uploadBannerTreino(ev) { return _uploadBanner(ev, 'treinamento', document.getElementById('treinoId').value, 'treino'); }
function uploadBannerDrone(ev)  { return _uploadBanner(ev, 'drone',       document.getElementById('droneId').value, 'drone'); }
function excluirBannerCurso()   { return _excluirBanner('servico',     document.getElementById('cursoId').value, 'curso'); }
function excluirBannerTreino()  { return _excluirBanner('treinamento', document.getElementById('treinoId').value, 'treino'); }
function excluirBannerDrone()   { return _excluirBanner('drone',       document.getElementById('droneId').value, 'drone'); }


/* ============================================================
   MÓDULOS — aulas/tópicos dentro de cursos/treinamentos/drones
   GET/POST /{entidade}/{id}/modulos, PUT/DELETE /modulos/{id}
   ============================================================ */
async function carregarModulos(entidade, entidadeId, kind) {
  if (!entidadeId) return;
  const r = await apiFetch('/' + entidade + '/' + entidadeId + '/modulos');
  const mods = r.success ? (r.modulos || []) : [];
  // Guarda em cache no DOM pra abrir editor sem buscar de novo
  const box = document.getElementById(kind + 'ModulosLista');
  if (box) box._modulos = mods;
  _renderModulos(kind, entidade, entidadeId, mods);
}

function _renderModulos(kind, entidade, entidadeId, modulos) {
  const box = document.getElementById(kind + 'ModulosLista');
  if (!box) return;
  if (!modulos.length) {
    box.innerHTML = '<div class="sup-help" style="padding:10px;background:#fafafa;border-radius:6px">' +
      'Nenhum módulo cadastrado ainda. Clique em "Adicionar módulo".</div>';
    return;
  }
  box.innerHTML = modulos.map((m, idx) => {
    const dur  = m.duracao_min ? '<span><i class="bi bi-clock"></i> ' + m.duracao_min + ' min</span>' : '';
    const tops = (m.topicos && m.topicos.length)
      ? '<span><i class="bi bi-card-checklist"></i> ' + m.topicos.length + ' tópico' + (m.topicos.length === 1 ? '' : 's') + '</span>'
      : '';
    return '<div class="sup-modulo-item" data-modulo-id="' + m.id + '" '
      + 'onclick="_abrirEditorModuloPorId(\'' + entidade + '\',\'' + entidadeId + '\',\'' + kind + '\',' + m.id + ')">'
      + '<div class="sup-modulo-num">' + String(idx + 1).padStart(2, '0') + '</div>'
      + '<div class="sup-modulo-body">'
      +   '<div class="sup-modulo-titulo">' + esc(m.titulo) + '</div>'
      +   '<div class="sup-modulo-meta">' + dur + tops + '</div>'
      + '</div>'
      + '<div class="sup-modulo-actions">'
      +   '<button type="button" title="Editar"><i class="bi bi-pencil"></i></button>'
      + '</div></div>';
  }).join('');
}

// Resolve o módulo do cache do DOM e abre o editor (evita problema de
// serializar JSON dentro de onclick).
function _abrirEditorModuloPorId(entidade, entidadeId, kind, moduloId) {
  const box = document.getElementById(kind + 'ModulosLista');
  const mods = (box && box._modulos) || [];
  const m = mods.find(x => x.id === moduloId);
  abrirModuloEditor(entidade, entidadeId, kind, m || null);
}

function abrirModuloEditor(entidade, entidadeId, kind, modulo) {
  if (!entidadeId) {
    toast('Salve primeiro o curso/treinamento/drone antes de adicionar módulos.', 'error');
    return;
  }
  document.getElementById('moduloEntidade').value   = entidade;
  document.getElementById('moduloEntidadeId').value = entidadeId;
  document.getElementById('moduloKind').value       = kind;
  document.getElementById('moduloId').value         = modulo && modulo.id ? modulo.id : '';
  document.getElementById('moduloTitulo').value     = (modulo && modulo.titulo) || '';
  document.getElementById('moduloDescricao').value  = (modulo && modulo.descricao) || '';
  document.getElementById('moduloDuracao').value    = (modulo && modulo.duracao_min) || '';
  document.getElementById('moduloTopicos').value    = (modulo && modulo.topicos ? modulo.topicos.join('\n') : '');
  document.getElementById('modModuloTitulo').textContent = modulo ? 'Editar módulo' : 'Novo módulo';
  document.getElementById('moduloExcluirBtn').style.display = modulo ? '' : 'none';
  document.getElementById('erroModulo').textContent = '';
  abrirModal('modalModulo');
}

async function salvarModulo() {
  const id          = document.getElementById('moduloId').value;
  const entidade    = document.getElementById('moduloEntidade').value;
  const entidadeId  = document.getElementById('moduloEntidadeId').value;
  const kind        = document.getElementById('moduloKind').value;
  const titulo      = document.getElementById('moduloTitulo').value.trim();
  const descricao   = document.getElementById('moduloDescricao').value.trim();
  const duracao_min = document.getElementById('moduloDuracao').value;
  const topicosRaw  = document.getElementById('moduloTopicos').value;
  const topicos = topicosRaw.split('\n').map(s => s.trim()).filter(Boolean);

  if (!titulo) {
    document.getElementById('erroModulo').textContent = 'Título é obrigatório.';
    return;
  }
  const payload = {
    titulo,
    descricao: descricao || null,
    duracao_min: duracao_min ? parseInt(duracao_min) : null,
    topicos,
  };

  let r;
  if (id) {
    r = await apiFetch('/modulos/' + id, { method: 'PUT', body: JSON.stringify(payload) });
  } else {
    r = await apiFetch('/' + entidade + '/' + entidadeId + '/modulos', {
      method: 'POST', body: JSON.stringify(payload),
    });
  }
  if (!r.success) {
    document.getElementById('erroModulo').textContent = r.detail || 'Erro ao salvar.';
    return;
  }
  toast(id ? 'Módulo atualizado.' : 'Módulo criado.', 'success');
  fecharModal('modalModulo');
  carregarModulos(entidade, entidadeId, kind);
}

async function excluirModuloAtual() {
  const id = document.getElementById('moduloId').value;
  if (!id) return;
  const entidade   = document.getElementById('moduloEntidade').value;
  const entidadeId = document.getElementById('moduloEntidadeId').value;
  const kind       = document.getElementById('moduloKind').value;
  if (!confirm('Excluir este módulo?')) return;
  const r = await apiFetch('/modulos/' + id, { method: 'DELETE' });
  if (!r.success) { toast(r.detail || 'Erro.', 'error'); return; }
  toast('Módulo excluído.', 'success');
  fecharModal('modalModulo');
  carregarModulos(entidade, entidadeId, kind);
}
