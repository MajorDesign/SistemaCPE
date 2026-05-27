/* =====================================================================
   Agendamento publico — agendar.js
   Pagina aberta: cliente lista agendas, escolhe servico/dia/horario e
   preenche os dados. O agendamento entra como "pendente".
   ===================================================================== */

const API_HOST = (typeof API_BASE_URL !== 'undefined') ? API_BASE_URL : 'http://127.0.0.1:8000';
const API = API_HOST + '/api/atendimentos/publico';
const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
const MESES_FULL = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
const DIAS_SEM = ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado'];
const DOW = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

let agendasPub = [];      // todas as agendas ativas (fisicas + online)
let agendaSel = null;     // agenda escolhida no form
let modalidadeSel = null; // 'presencial' | 'online' — escolhida na tela 0
let vendedores = [];
let calMesRef = new Date();   // mês exibido no calendário
let diasInfo = {};            // mapa data -> {total, livres}
let diaSelecionado = null;    // data 'YYYY-MM-DD' escolhida

/* ---- util ---- */
function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g,
    c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[c]));
}
function el(id) { return document.getElementById(id); }
function setErro(msg) {
  const box = el('formErro');
  if (msg) { box.textContent = msg; box.style.display = 'block'; box.scrollIntoView({ block: 'center' }); }
  else { box.style.display = 'none'; }
}
async function get(path) {
  const r = await fetch(API + path);
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    throw new Error(e.detail || ('Erro ' + r.status));
  }
  return r.json();
}

/* ============ CARREGAMENTO ============ */
async function carregarAgendas() {
  try {
    const d = await get('/agendas');
    agendasPub = d.agendas || [];
  } catch (e) {
    agendasPub = [];
  }
}

/* ============ ESCOLHA DA MODALIDADE (tela 0) ============ */
function _mostrarApenas(viewId) {
  ['viewModalidade', 'viewLanding', 'viewForm'].forEach(v => {
    const el2 = el(v); if (el2) el2.style.display = (v === viewId) ? 'block' : 'none';
  });
  window.scrollTo(0, 0);
}

function voltarModalidade() {
  modalidadeSel = null;
  _mostrarApenas('viewModalidade');
}

async function escolherModalidade(m) {
  modalidadeSel = m;
  // garante que as agendas estao carregadas (caso o usuario abra direto via deep-link)
  if (!agendasPub.length) await carregarAgendas();

  if (m === 'online') {
    const onlines = agendasPub.filter(a => a.tipo === 'online');
    if (!onlines.length) {
      alert('No momento nao ha agenda de atendimento online disponivel. '
          + 'Por favor escolha presencial ou tente novamente mais tarde.');
      voltarModalidade();
      return;
    }
    // cai direto no form com a primeira agenda online
    abrirForm(onlines[0].id);
    return;
  }

  // presencial: mostra os cards das unidades fisicas
  _mostrarApenas('viewLanding');
  renderCards();
}

function renderCards() {
  const busca = (el('buscaAgenda').value || '').toLowerCase();
  // so unidades fisicas aparecem na landing (online tem fluxo proprio)
  const lista = agendasPub.filter(a => a.tipo !== 'online').filter(a => {
    if (!busca) return true;
    const naServico = (a.servicos || []).some(s => s.nome.toLowerCase().includes(busca));
    return a.nome.toLowerCase().includes(busca) || naServico;
  });
  const box = el('cardsAgendas');
  if (!lista.length) {
    box.innerHTML = '<div class="ag-loading">Nenhuma unidade encontrada.</div>';
    return;
  }
  box.innerHTML = lista.map(a => {
    const total = (a.servicos || []).length;
    const btnSrv = total
      ? `<button type="button" class="ag-card-srv-btn"
            onclick="abrirModalServicos(${a.id})">
          <i class="bi bi-list-check"></i>
          <span>Ver ${total} serviço${total === 1 ? '' : 's'} disponíve${total === 1 ? 'l' : 'is'}</span>
          <i class="bi bi-chevron-right ag-card-srv-chev"></i>
         </button>`
      : `<div class="ag-card-srv-empty">
          <i class="bi bi-info-circle"></i> Nenhum serviço cadastrado
         </div>`;
    return `<div class="ag-card">
      <div class="ag-card-nome">${esc(a.nome)}</div>
      ${a.descricao ? `<div class="ag-card-desc">${esc(a.descricao)}</div>` : ''}
      ${btnSrv}
      <button class="ag-btn ag-btn-block" onclick="abrirForm(${a.id})">
        <i class="bi bi-calendar-check"></i> Agendar</button>
    </div>`;
  }).join('');
}

/* ============ MODAL: servicos da unidade ============ */
function abrirModalServicos(agendaId) {
  const a = agendasPub.find(x => x.id === agendaId);
  if (!a) return;
  el('modalServicosTitulo').textContent = a.nome;
  const lista = el('modalServicosLista');
  const srv = a.servicos || [];
  if (!srv.length) {
    lista.innerHTML = '<li class="ag-modal-srv-empty">Nenhum serviço cadastrado.</li>';
  } else {
    lista.innerHTML = srv.map(s => `
      <li>
        <i class="bi bi-check-circle-fill"></i>
        <div>
          <div class="ag-modal-srv-nome">${esc(s.nome)}</div>
          <div class="ag-modal-srv-dur">${s.duracao_min} min</div>
        </div>
      </li>`).join('');
  }
  // botao do rodape leva pro form da agenda
  const btn = el('modalServicosAgendar');
  btn.onclick = () => { fecharModalServicos(); abrirForm(agendaId); };
  el('modalServicos').classList.add('show');
  document.body.style.overflow = 'hidden';
}

function fecharModalServicos(ev) {
  if (ev && ev.target && ev.target.id !== 'modalServicos') return;
  el('modalServicos').classList.remove('show');
  document.body.style.overflow = '';
}

/* ============ FORM ============ */
function abrirForm(agendaId) {
  _mostrarApenas('viewForm');
  el('passo1').style.display = 'block';
  el('passo2').style.display = 'none';
  el('passoOk').style.display = 'none';
  marcarStep(1);
  setErro('');

  // Filtra as opcoes do select de agendas pela modalidade escolhida.
  // Se nao houver modalidade (deep link ?agenda=ID), mostra todas.
  const opcoes = agendasPub.filter(a => {
    if (!modalidadeSel) return true;
    return modalidadeSel === 'online' ? a.tipo === 'online' : a.tipo !== 'online';
  });
  el('fAgenda').innerHTML = opcoes.map(a =>
    `<option value="${a.id}">${esc(a.nome)}</option>`).join('');
  el('fAgenda').value = agendaId;

  // Se ja temos modalidade, pre-marca o radio e bloqueia a troca
  // (cliente nao pode pular do online pro presencial sem voltar).
  const radios = document.querySelectorAll('input[name="modalidade"]');
  radios.forEach(r => {
    r.checked = (modalidadeSel && r.value === modalidadeSel);
    r.disabled = !!modalidadeSel;
  });

  onAgendaChange();
  // onAgendaChange limpa os radios — repoe a modalidade se aplicavel
  if (modalidadeSel) {
    radios.forEach(r => { r.checked = r.value === modalidadeSel; });
    if (typeof onModalidadeChange === 'function') onModalidadeChange();
  }
}

function voltarLanding() {
  // Online voltou direto pro form, sem passar pela landing.
  // Entao "voltar" do online deve ir pra escolha de modalidade.
  if (modalidadeSel === 'online') {
    voltarModalidade();
  } else {
    _mostrarApenas('viewLanding');
  }
}

function marcarStep(n) {
  el('step1').classList.toggle('active', n >= 1);
  el('step2').classList.toggle('active', n >= 2);
}

function onAgendaChange() {
  const id = parseInt(el('fAgenda').value);
  agendaSel = agendasPub.find(a => a.id === id) || null;
  // instruções
  if (agendaSel && agendaSel.instrucoes) {
    el('txtInstrucoes').textContent = agendaSel.instrucoes;
    el('boxInstrucoes').style.display = 'block';
  } else {
    el('boxInstrucoes').style.display = 'none';
  }
  // serviços da agenda
  const fs = el('fServico');
  fs.innerHTML = '<option value="">--- Escolha um serviço ---</option>' +
    (agendaSel ? agendaSel.servicos.map(s =>
      `<option value="${s.id}">${esc(s.nome)}</option>`).join('') : '');
  document.querySelectorAll('input[name="modalidade"]').forEach(r => { r.checked = false; });
  resetCalendario();
}

function pad2(n) { return String(n).padStart(2, '0'); }
function ymd(d) { return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate()); }
function rotuloDia(dataStr) {
  const d = new Date(dataStr + 'T00:00:00');
  return `${DIAS_SEM[d.getDay()]}, ${d.getDate()} de ${MESES[d.getMonth()]}`;
}

function resetCalendario() {
  diasInfo = {};
  diaSelecionado = null;
  el('fHorario').value = '';
  el('agCalGrid').innerHTML = '<div class="ag-help" style="grid-column:1/-1">Escolha um serviço primeiro.</div>';
  el('agCalMes').textContent = '—';
  el('agSlots').innerHTML = '';
}

function onServicoChange() { carregarDias(); }
function onModalidadeChange() { carregarDias(); }

// O calendário só carrega depois que serviço E modalidade foram escolhidos —
// a disponibilidade dos dias depende da modalidade.
async function carregarDias() {
  resetCalendario();
  const servicoId = el('fServico').value;
  const modalidade = radioVal('modalidade');
  if (!servicoId || !agendaSel) return;
  if (!modalidade) {
    el('agCalGrid').innerHTML = '<div class="ag-help" style="grid-column:1/-1">' +
      'Escolha presencial ou online para ver os dias disponíveis.</div>';
    return;
  }
  el('agCalGrid').innerHTML = '<div class="ag-help" style="grid-column:1/-1">Carregando dias...</div>';
  try {
    const d = await get(
      `/agendas/${agendaSel.id}/dias?servico_id=${servicoId}&modalidade=${modalidade}`);
    diasInfo = {};
    (d.dias || []).forEach(x => { diasInfo[x.data] = x; });
    const primeiroLivre = (d.dias || []).find(x => x.livres > 0);
    calMesRef = primeiroLivre ? new Date(primeiroLivre.data + 'T00:00:00') : new Date();
    calMesRef.setDate(1);
    renderCalendario();
  } catch (e) {
    el('agCalGrid').innerHTML =
      '<div class="ag-help" style="grid-column:1/-1">Erro ao carregar dias.</div>';
  }
}

function calMudarMes(delta) {
  calMesRef = new Date(calMesRef.getFullYear(), calMesRef.getMonth() + delta, 1);
  renderCalendario();
}

function renderCalendario() {
  const ano = calMesRef.getFullYear(), mes = calMesRef.getMonth();
  el('agCalMes').textContent = MESES_FULL[mes] + ' ' + ano;
  const ini = new Date(ano, mes, 1);
  ini.setDate(ini.getDate() - ini.getDay());   // recua até domingo
  let html = DOW.map(d => `<div class="ag-cal-dow">${d}</div>`).join('');
  const cur = new Date(ini);
  for (let i = 0; i < 42; i++) {
    const ds = ymd(cur);
    const foraMes = cur.getMonth() !== mes;
    const info = diasInfo[ds];
    let cls = 'ag-cal-day', extra = '', click = '';
    if (foraMes) {
      cls += ' fora';
    } else if (info && info.livres > 0) {
      cls += ' livre'; click = `onclick="selecionarDia('${ds}')"`;
      extra = `<small>${info.livres} livre(s)</small>`;
    } else if (info) {
      cls += ' cheio'; extra = '<small>sem vaga</small>';
    } else {
      cls += ' indisp';
    }
    if (ds === diaSelecionado) cls += ' sel';
    html += `<div class="${cls}" ${click}>${cur.getDate()}${extra}</div>`;
    cur.setDate(cur.getDate() + 1);
  }
  el('agCalGrid').innerHTML = html;
}

async function selecionarDia(dataStr) {
  diaSelecionado = dataStr;
  el('fHorario').value = '';
  renderCalendario();
  el('agSlots').innerHTML = '<div class="ag-help">Carregando horários...</div>';
  try {
    const d = await get(`/agendas/${agendaSel.id}/horarios?servico_id=${el('fServico').value}` +
      `&data=${dataStr}&modalidade=${radioVal('modalidade')}`);
    renderSlots(d.horarios || []);
  } catch (e) {
    el('agSlots').innerHTML = '<div class="ag-help">Erro ao carregar horários.</div>';
  }
}

function renderSlots(slots) {
  if (!slots.length) {
    el('agSlots').innerHTML = '<div class="ag-help">Nenhum horário neste dia.</div>';
    return;
  }
  const grade = slots.map(s => s.disponivel
    ? `<button type="button" class="ag-slot livre" data-inicio="${s.inicio}"
         onclick="escolherSlot(this)">${s.label}</button>`
    : `<button type="button" class="ag-slot cheio" disabled
         title="Horário já preenchido">${s.label} • Ocupado</button>`
  ).join('');
  el('agSlots').innerHTML =
    `<div class="ag-slots-titulo">Horários de ${rotuloDia(diaSelecionado)}</div>
     <div class="ag-slots-grid">${grade}</div>`;
}

function escolherSlot(btn) {
  document.querySelectorAll('.ag-slot.sel').forEach(b => b.classList.remove('sel'));
  btn.classList.add('sel');
  el('fHorario').value = btn.dataset.inicio;
}

/* ---- navegação entre passos ---- */
async function irPasso(n) {
  setErro('');
  if (n === 2) {
    if (!el('fServico').value) return setErro('Escolha um serviço.');
    if (!radioVal('modalidade')) return setErro('Escolha se o treinamento é presencial ou online.');
    if (!el('fHorario').value) return setErro('Escolha um dia e um horário no calendário.');
    await prepararPasso2();
    el('passo1').style.display = 'none';
    el('passo2').style.display = 'block';
    marcarStep(2);
  } else {
    el('passo2').style.display = 'none';
    el('passo1').style.display = 'block';
    marcarStep(1);
  }
  window.scrollTo(0, 0);
}

async function prepararPasso2() {
  // equipamentos do serviço escolhido
  const servicoId = el('fServico').value;
  const cx = el('listaEquipamentos');
  cx.innerHTML = '<div class="ag-help">Carregando...</div>';
  try {
    const d = await get(`/servicos/${servicoId}/equipamentos`);
    const eqs = d.equipamentos || [];
    if (!eqs.length) {
      el('boxEquipamentos').style.display = 'none';
    } else {
      el('boxEquipamentos').style.display = 'block';
      cx.innerHTML = eqs.map(e =>
        `<label class="ag-radio"><input type="radio" name="equipamento" value="${e.id}"> ${esc(e.nome)}</label>`
      ).join('');
    }
  } catch (e) {
    cx.innerHTML = '<div class="ag-help">Erro ao carregar equipamentos.</div>';
  }
  // vendedores (uma vez)
  if (!vendedores.length) {
    try {
      const d = await get('/vendedores');
      vendedores = d.vendedores || [];
    } catch (e) { vendedores = []; }
  }
  const lv = el('listaVendedores');
  lv.innerHTML = vendedores.length
    ? vendedores.map(v =>
        `<label class="ag-radio"><input type="radio" name="vendedor" value="${v.id}"> ${esc(v.name)}</label>`).join('')
    : '<div class="ag-help">Nenhum vendedor cadastrado no grupo Comercial.</div>';
}

function radioVal(nome) {
  const r = document.querySelector(`input[name="${nome}"]:checked`);
  return r ? r.value : '';
}

async function enviarAgendamento() {
  setErro('');
  const nome = el('fNome').value.trim();
  const email = el('fEmail').value.trim();
  const telefone = el('fTelefone').value.trim();
  if (!nome) return setErro('Informe seu nome completo.');
  if (!email || !email.includes('@')) return setErro('Informe um e-mail válido.');
  if (!telefone) return setErro('Informe seu telefone.');

  const temEquip = el('boxEquipamentos').style.display !== 'none';
  const equipamento = radioVal('equipamento');
  if (temEquip && !equipamento) return setErro('Selecione o equipamento.');
  const modalidade = radioVal('modalidade');
  if (!modalidade) return setErro('Informe se o treinamento é presencial ou online.');
  const tipo = radioVal('tipo');
  if (!tipo) return setErro('Informe se é locação ou venda.');
  const vendedor = radioVal('vendedor');
  if (vendedores.length && !vendedor) return setErro('Selecione o vendedor que te atende.');

  const payload = {
    agenda_id: agendaSel.id,
    servico_id: parseInt(el('fServico').value),
    inicio: el('fHorario').value,
    cliente_nome: nome,
    cliente_email: email,
    cliente_telefone: telefone,
    observacoes: el('fMensagem').value.trim(),
    equipamento_id: equipamento || null,
    modalidade: modalidade,
    tipo_negocio: tipo,
    vendedor_id: vendedor || null,
  };

  const btn = el('btnEnviar');
  btn.disabled = true;
  try {
    const r = await fetch(API + '/agendar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      setErro(d.detail || 'Não foi possível concluir o agendamento.');
      btn.disabled = false;
      return;
    }
    el('passo2').style.display = 'none';
    el('passoOk').style.display = 'block';
    el('okMsg').textContent = d.mensagem || 'Aguarde a confirmação da equipe.';
    window.scrollTo(0, 0);
  } catch (e) {
    setErro('Erro de conexão. Tente novamente.');
    btn.disabled = false;
  }
}

// Fluxo da pagina publica:
//   - Tela 0 (default): escolha presencial / online
//   - Deep link ?modalidade=presencial : pula tela 0, mostra unidades
//   - Deep link ?modalidade=online     : pula tela 0, abre form da agenda online
//   - Deep link ?agenda=ID             : compatibilidade — abre form daquela agenda
async function bootstrap() {
  await carregarAgendas();

  const params = new URLSearchParams(window.location.search);
  const modal = params.get('modalidade');
  const idStr = params.get('agenda');

  if (idStr) {
    const id = parseInt(idStr, 10);
    const alvo = agendasPub.find(a => a.id === id);
    if (alvo) {
      // adota a modalidade implicita da propria agenda
      modalidadeSel = alvo.tipo === 'online' ? 'online' : 'presencial';
      abrirForm(id);
      return;
    }
    setErro('Agenda nao encontrada ou desativada. Escolha uma da lista.');
    _mostrarApenas('viewModalidade');
    return;
  }

  if (modal === 'presencial' || modal === 'online') {
    escolherModalidade(modal);
    return;
  }

  // padrao: tela inicial de escolha
  _mostrarApenas('viewModalidade');
}

document.addEventListener('DOMContentLoaded', bootstrap);

// ESC fecha o modal de servicos
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && el('modalServicos') && el('modalServicos').classList.contains('show')) {
    fecharModalServicos();
  }
});
