// ============================================================
// DASHBOARD SLA — painel inteligente por role
// USER       → KPIs dos próprios chamados
// RESPONSAVEL_GRUPO / ADMIN → KPIs do grupo + tabela por membro
// ============================================================

// ── 1. TOGGLE ────────────────────────────────────────────────
function toggleDashboardSLA(button) {
  const content = button.nextElementSibling;
  const icon    = button.querySelector('.toggle-icon');

  content.classList.toggle('d-none');

  if (content.classList.contains('d-none')) {
    icon.classList.replace('bi-chevron-up', 'bi-chevron-down');
  } else {
    icon.classList.replace('bi-chevron-down', 'bi-chevron-up');
    carregarDashboardSLA();
  }
}

// ── 2. CARREGAR ───────────────────────────────────────────────
async function carregarDashboardSLA() {
  const user = (typeof getCurrentUser === 'function') ? getCurrentUser() : null;
  if (!user || !user.id) {
    _slaMsgShow('Usuário não autenticado.');
    return;
  }

  const isGestor = user.role === 'RESPONSAVEL_GRUPO' || user.role === 'ADMIN' ||
                   user.role === 'TI' || user.role === 'MANAGER';

  document.getElementById('slaDashboardTitle').textContent =
    isGestor ? 'Dashboard SLA — Grupo' : 'Meu Desempenho SLA';

  _slaSetLoading(true);

  try {
    const dados = await apiRequest('GET', `/tickets/dashboard/sla?usuario_id=${user.id}`);
    _renderDashboard(dados, isGestor);
  } catch (err) {
    _slaSetLoading(false);
    _slaMsgShow('Erro ao carregar: ' + (err?.detail || err?.message || 'tente novamente.'));
    document.getElementById('slaKpiCards').innerHTML = '';
  }
}

// ── 3. RECARREGAR ─────────────────────────────────────────────
function recarregarDashboardSLA() {
  document.getElementById('slaPeriodo').textContent     = '—';
  document.getElementById('slaKpiCards').innerHTML      = _skeletonKpis();
  document.getElementById('slaMembroSection').style.display = 'none';
  _slaMsgShow('');
  carregarDashboardSLA();
}

// ── 4. RENDERIZAR ─────────────────────────────────────────────
function _renderDashboard(dados, isGestor) {
  _slaSetLoading(false);

  const r     = dados.resumo_geral || {};
  const total = r.total_tickets || 0;

  // Período
  document.getElementById('slaPeriodo').textContent = dados.periodo || '—';

  // ── KPI Cards principais — todos os usuários veem os mesmos 6 cards ──
  const finalizados = r.finalizados  ?? 0;
  const emAndamento = r.em_andamento ?? 0;

  const cardsBase = [
    _kpiCard('primary',  'bi-ticket-perforated-fill', 'Total',            total,                            ''),
    _kpiCard('secondary','bi-hourglass-split',         'Em Andamento',     emAndamento,                      ''),
    _kpiCard('dark',     'bi-check2-all',              'Finalizados',      finalizados,                      ''),
    _kpiCard('success',  'bi-check-circle-fill',       'Dentro do Prazo',  r.sla_dentro_prazo?.qtd  ?? 0,   _pct(r.sla_dentro_prazo?.percentual)),
    _kpiCard('danger',   'bi-x-circle-fill',           'SLA Estourado',    r.sla_estourado?.qtd     ?? 0,   _pct(r.sla_estourado?.percentual)),
    _kpiCard('warning',  'bi-exclamation-circle-fill', 'Próx. de Vencer',  r.sla_proximo_vencer?.qtd ?? 0,  _pct(r.sla_proximo_vencer?.percentual)),
  ];
  document.getElementById('slaKpiCards').innerHTML = cardsBase.join('');

  // ── Bloco SLA Primeira Resposta — sempre visível quando há tickets ──
  const prNoPrazo       = r.sla_pr_no_prazo?.qtd        ?? 0;
  const prEstourado     = r.sla_pr_estourado?.qtd        ?? 0;
  const prProximoVencer = r.sla_pr_proximo_vencer?.qtd   ?? 0;
  const prAguard        = r.sla_pr_aguardando?.qtd       ?? 0;

  const prSection = document.getElementById('slaPrimeiraRespostaSection');
  if (prSection) {
    if (total > 0) {
      const prCards = [
        _kpiCard('success',  'bi-reply-fill',           '1ª Resp. no Prazo',    prNoPrazo,       _pct(r.sla_pr_no_prazo?.percentual)),
        _kpiCard('danger',   'bi-reply-fill',           '1ª Resp. Estourada',   prEstourado,     _pct(r.sla_pr_estourado?.percentual)),
        _kpiCard('warning',  'bi-exclamation-triangle', '1ª Resp. Próx. Vencer',prProximoVencer, _pct(r.sla_pr_proximo_vencer?.percentual)),
        _kpiCard('secondary','bi-hourglass-split',      '1ª Resp. Aguardando',  prAguard,        _pct(r.sla_pr_aguardando?.percentual)),
      ];
      prSection.innerHTML = `
        <div class="mt-3 pt-2 border-top">
          <div class="d-flex align-items-center mb-2">
            <span class="badge bg-success me-2"><i class="bi bi-reply-fill"></i></span>
            <span class="fw-semibold text-muted" style="font-size:.82rem;">SLA PRIMEIRA RESPOSTA</span>
          </div>
          <div class="row g-2">${prCards.join('')}</div>
        </div>`;
      prSection.style.display = '';
    } else {
      prSection.style.display = 'none';
    }
  }

  // Tabela de membros (só gestor)
  const membros = dados.por_usuario || [];
  const section = document.getElementById('slaMembroSection');

  if (isGestor && membros.length > 0) {
    section.style.display = '';
    document.getElementById('slaMembroTableBody').innerHTML =
      membros
        .sort((a, b) => b.total_tickets - a.total_tickets)
        .map(_renderMembroRow)
        .join('');
  } else {
    section.style.display = 'none';
  }

  // Aviso se sem dados
  if (total === 0) {
    _slaMsgShow('Nenhum ticket com SLA encontrado neste período.');
  } else {
    _slaMsgShow('');
  }
}

// ── 5. ROW MEMBRO ─────────────────────────────────────────────
function _renderMembroRow(u) {
  const total      = u.total_tickets   || 0;
  const andamento  = u.em_andamento    || 0;
  const finalizados= u.finalizados     || 0;
  const estourado  = u.sla_estourado?.qtd  ?? 0;
  const noPrazo    = u.sla_dentro_prazo?.qtd ?? 0;
  const prNoPrazo  = u.sla_pr_no_prazo?.qtd  ?? 0;
  const prEstourado= u.sla_pr_estourado?.qtd ?? 0;

  // Taxa de sucesso = tickets sem estouro / total  (apenas finalizados)
  const taxa = finalizados > 0
    ? Math.round(((finalizados - estourado) / finalizados) * 100)
    : (total > 0 ? Math.round(((total - estourado) / total) * 100) : 0);
  const taxaColor = taxa >= 85 ? 'success' : taxa >= 65 ? 'warning' : 'danger';

  // Inicial para avatar
  const inicial = (u.usuario_nome || '?')[0].toUpperCase();

  return `
    <tr>
      <td>
        <div class="d-flex align-items-center gap-2">
          <div class="sla-avatar sla-avatar-${_avatarColor(u.usuario_id)}">${inicial}</div>
          <div>
            <div class="fw-semibold" style="font-size:.85rem;line-height:1.2">${_esc(u.usuario_nome)}</div>
            <small class="text-muted">#${u.usuario_id}</small>
          </div>
        </div>
      </td>
      <td class="text-center">
        <span class="fw-bold">${total}</span>
      </td>
      <td class="text-center">
        <span class="badge rounded-pill bg-primary-subtle text-primary">${andamento}</span>
      </td>
      <td class="text-center">
        <span class="badge rounded-pill bg-secondary-subtle text-secondary">${finalizados}</span>
      </td>
      <td class="text-center">
        <span class="fw-semibold text-success">${noPrazo}</span>
        <small class="text-muted ms-1">${_pct(u.sla_dentro_prazo?.percentual)}</small>
      </td>
      <td class="text-center">
        ${estourado > 0
          ? `<span class="fw-semibold text-danger">${estourado}</span>
             <small class="text-muted ms-1">${_pct(u.sla_estourado?.percentual)}</small>`
          : `<span class="text-muted">—</span>`}
      </td>
      <td class="text-center">
        ${prNoPrazo > 0
          ? `<span class="fw-semibold text-success">${prNoPrazo}</span>
             <small class="text-muted ms-1">${_pct(u.sla_pr_no_prazo?.percentual)}</small>`
          : `<span class="text-muted">—</span>`}
      </td>
      <td class="text-center">
        ${prEstourado > 0
          ? `<span class="fw-semibold text-danger">${prEstourado}</span>
             <small class="text-muted ms-1">${_pct(u.sla_pr_estourado?.percentual)}</small>`
          : `<span class="text-muted">—</span>`}
      </td>
      <td class="text-center">
        ${u.atraso_medio
          ? `<span class="badge bg-danger-subtle text-danger fw-semibold">${_esc(u.atraso_medio)}</span>`
          : `<span class="text-muted">—</span>`}
      </td>
      <td>
        <div class="d-flex align-items-center gap-2">
          <div class="progress flex-grow-1" style="height:7px;border-radius:4px">
            <div class="progress-bar bg-${taxaColor}" style="width:${taxa}%;transition:width .6s ease"></div>
          </div>
          <small class="text-${taxaColor} fw-bold" style="min-width:34px;text-align:right">${taxa}%</small>
        </div>
      </td>
    </tr>`;
}

// ── 6. KPI CARD ───────────────────────────────────────────────
function _kpiCard(color, icon, label, value, sub, colClass = 'col-6 col-md-2') {
  const bg = {
    primary:   '#e8f0fe', success:   '#e6f4ea',
    danger:    '#fce8e6', warning:   '#fff8e6',
    secondary: '#f1f5f9', dark:      '#f0fdf4',
  }[color] || '#f8f9fa';

  const fg = {
    primary:   '#1a73e8', success:   '#188038',
    danger:    '#c5221f', warning:   '#c97a00',
    secondary: '#475569', dark:      '#166534',
  }[color] || '#333';

  return `
    <div class="${colClass}">
      <div class="sla-kpi-card" style="background:${bg};border-left-color:${fg}">
        <div class="sla-kpi-top">
          <i class="bi ${icon} sla-kpi-icon" style="color:${fg}"></i>
          <span class="sla-kpi-value" style="color:${fg}">${value}</span>
          ${sub ? `<span class="sla-kpi-sub">${sub}</span>` : ''}
        </div>
        <div class="sla-kpi-label">${label}</div>
      </div>
    </div>`;
}

// ── 7. SKELETON ───────────────────────────────────────────────
function _skeletonKpis() {
  return Array(6).fill(`
    <div class="col-6 col-md-2">
      <div class="sla-kpi-card sla-kpi-skeleton">
        <div class="sla-skeleton-line" style="width:70%;height:10px;margin-bottom:6px"></div>
        <div class="sla-skeleton-line" style="width:40%;height:22px;margin-bottom:4px"></div>
        <div class="sla-skeleton-line" style="width:55%;height:9px"></div>
      </div>
    </div>`).join('');
}

// ── 8. ESTADO LOADING / ERRO ──────────────────────────────────
function _slaSetLoading(on) {
  const cards = document.getElementById('slaKpiCards');
  if (on) {
    cards.innerHTML = _skeletonKpis();
    _slaMsgShow('');
  }
}

function _slaMsgShow(msg) {
  const el = document.getElementById('slaDashboardMsg');
  if (!msg) { el.style.display = 'none'; return; }
  el.style.display = '';
  el.innerHTML = `<i class="bi bi-info-circle text-secondary me-1"></i>${msg}`;
}

// ── 9. HELPERS ────────────────────────────────────────────────
function _pct(v) {
  return (v !== undefined && v !== null) ? `${v}%` : '';
}

function _esc(str) {
  return (str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function _avatarColor(id) {
  const colors = ['blue','green','purple','orange','teal','red','indigo','pink'];
  return colors[(id || 0) % colors.length];
}
