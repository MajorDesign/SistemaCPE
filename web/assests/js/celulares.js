/* ============================================================
   MÓDULO DE CELULARES CORPORATIVOS
   ============================================================ */

const API_HOST = (typeof API_BASE_URL !== 'undefined'
  ? API_BASE_URL
  : `http://${window.location.hostname || '127.0.0.1'}:8000`);

const API = {
  celulares: API_HOST + '/api/inventario/celulares',
  users:     API_HOST + '/api/users',
};

let celulares = [];
let usuarios  = [];
let editandoId = null;

/* ============================================================
   HELPERS
   ============================================================ */
function $(id) { return document.getElementById(id); }
function escHtml(s) {
  return (s || '').toString().replace(/[&<>"']/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
}
function formatCPF(cpf) {
  if (!cpf) return '';
  const c = cpf.replace(/\D/g, '');
  if (c.length !== 11) return cpf;
  return `${c.slice(0,3)}.${c.slice(3,6)}.${c.slice(6,9)}-${c.slice(9,11)}`;
}

const STATUS_LBL = {
  em_uso:     'Em uso',
  disponivel: 'Disponível',
  manutencao: 'Manutenção',
  inativo:    'Inativo',
};

/* ============================================================
   AUTO-DETECTAR MARCA/MODELO via userAgent
   ============================================================ */
function detectarDispositivo() {
  const ua = navigator.userAgent;
  let marca = '', modelo = '';

  // iPhone / iPad
  if (/iPhone/i.test(ua)) {
    marca = 'Apple'; modelo = 'iPhone';
    const m = ua.match(/iPhone\s?OS\s([\d_]+)/);
    if (m) modelo = `iPhone (iOS ${m[1].replace(/_/g, '.')})`;
  }
  else if (/iPad/i.test(ua)) {
    marca = 'Apple'; modelo = 'iPad';
  }
  // Android — extrai modelo do trecho "; MODELO Build/" ou "; MODELO)"
  else if (/Android/i.test(ua)) {
    const m = ua.match(/Android[^;]*;\s*([^;)]+?)\s*(?:Build|;|\))/);
    if (m) {
      const dev = m[1].trim();
      // Tenta separar marca conhecida
      const marcas = ['Samsung','Motorola','Xiaomi','Redmi','LG','Sony','Huawei','Asus','Realme','OnePlus','Nokia','Lenovo','Positivo','Multilaser'];
      const marcaFound = marcas.find(m2 => new RegExp(m2, 'i').test(dev));
      if (marcaFound) {
        marca = marcaFound;
        modelo = dev.replace(new RegExp(marcaFound, 'i'), '').trim();
      } else {
        marca = 'Android'; modelo = dev;
      }
    } else {
      marca = 'Android';
    }
  }

  return { marca, modelo };
}

/* ============================================================
   BOOTSTRAP
   ============================================================ */
async function init() {
  await Promise.all([loadUsuarios(), loadCelulares()]);
  renderTabela();

  $('filtroBusca').addEventListener('input',  renderTabela);
  $('filtroStatus').addEventListener('change', renderTabela);

  // Fecha modal clicando fora
  $('modalCelular').addEventListener('click', e => {
    if (e.target.id === 'modalCelular') fecharModal();
  });
}
document.addEventListener('DOMContentLoaded', init);

async function loadCelulares() {
  try {
    const r = await fetch(API.celulares);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    celulares = await r.json();
  } catch (err) {
    console.error('[CEL] loadCelulares', err);
    celulares = [];
  }
}

async function loadUsuarios() {
  try {
    const r = await fetch(API.users);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const lista = await r.json();
    usuarios = (lista || []).filter(u => u.is_active);
  } catch (err) {
    console.error('[CEL] loadUsuarios', err);
    usuarios = [];
  }
}

/* ============================================================
   RENDER — KPIs + tabela
   ============================================================ */
function renderKPIs(list) {
  const total = list.length;
  const eu = list.filter(c => c.status === 'em_uso').length;
  const di = list.filter(c => c.status === 'disponivel').length;
  const mn = list.filter(c => c.status === 'manutencao').length;
  $('kpiTotal').textContent = total;
  $('kpiEmUso').textContent = eu;
  $('kpiDisp').textContent  = di;
  $('kpiMan').textContent   = mn;
}

function renderTabela() {
  const q  = ($('filtroBusca').value || '').toLowerCase().trim();
  const st = $('filtroStatus').value;

  const filtrados = celulares.filter(c => {
    if (st && c.status !== st) return false;
    if (q) {
      const hay = `${c.marca} ${c.modelo} ${c.imei1} ${c.imei2 || ''} ${c.patrimonio || ''}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  renderKPIs(celulares);

  const tb = $('celTBody');
  if (!filtrados.length) {
    tb.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:30px;color:#9ca3af;">Nenhum celular encontrado.</td></tr>';
    return;
  }

  tb.innerHTML = filtrados.map(c => `
    <tr>
      <td>
        <strong>${escHtml(c.marca)}</strong><br>
        <span style="color:#6b7280;font-size:12px;">${escHtml(c.modelo)}</span>
      </td>
      <td style="font-family:monospace;">${escHtml(c.imei1)}</td>
      <td>${escHtml(c.numero_telefone || '—')}</td>
      <td>${c.responsavel_nome ? escHtml(c.responsavel_nome) : '<span style="color:#9ca3af;">—</span>'}</td>
      <td><span class="status-pill status-${c.status}">${STATUS_LBL[c.status] || c.status}</span></td>
      <td>${escHtml(c.patrimonio || '—')}</td>
      <td style="text-align:right;">
        ${c.responsavel_id ? `<button class="cel-action primary" onclick="gerarTermo(${c.id})" title="Gerar termo de responsabilidade"><i class="bi bi-file-earmark-text"></i></button>` : ''}
        <button class="cel-action" onclick="editarCelular(${c.id})" title="Editar"><i class="bi bi-pencil"></i></button>
        <button class="cel-action danger" onclick="deletarCelular(${c.id})" title="Excluir"><i class="bi bi-trash"></i></button>
      </td>
    </tr>
  `).join('');
}

/* ============================================================
   MODAL — abertura e fechamento
   ============================================================ */
function abrirModalCadastro() {
  editandoId = null;
  $('modalTitulo').innerHTML = '<i class="bi bi-phone-fill"></i> Novo Celular';
  limparForm();
  preencherResponsaveis(null);

  // Auto-detecta marca/modelo se for um celular abrindo o cadastro
  const det = detectarDispositivo();
  if (det.marca) {
    $('fMarca').value  = det.marca;
    $('fModelo').value = det.modelo;
    $('deviceHint').style.display = 'flex';
    $('deviceHintText').textContent =
      `Dispositivo detectado pelo navegador: ${det.marca} ${det.modelo}. Confira e ajuste se necessário.`;
  } else {
    $('deviceHint').style.display = 'none';
  }

  $('modalCelular').classList.add('active');
}

function editarCelular(id) {
  const c = celulares.find(x => x.id === id);
  if (!c) return;
  editandoId = id;
  $('modalTitulo').innerHTML = '<i class="bi bi-pencil-square"></i> Editar Celular';
  $('deviceHint').style.display = 'none';

  $('fMarca').value       = c.marca || '';
  $('fModelo').value      = c.modelo || '';
  $('fImei1').value       = c.imei1 || '';
  $('fImei2').value       = c.imei2 || '';
  $('fNumero').value      = c.numero_telefone || '';
  $('fOperadora').value   = c.operadora || '';
  $('fChip').value        = c.numero_chip || '';
  $('fCor').value         = c.cor || '';
  $('fPatrimonio').value  = c.patrimonio || '';
  $('fStatus').value      = c.status || 'disponivel';
  $('fDataEntrega').value = c.data_entrega || '';
  $('fAcessorios').value  = c.acessorios || 'bateria e carregador';
  $('fObs').value         = c.observacoes || '';

  preencherResponsaveis(c.responsavel_id);
  $('modalCelular').classList.add('active');
}

function fecharModal() {
  $('modalCelular').classList.remove('active');
  editandoId = null;
}

function limparForm() {
  ['fMarca','fModelo','fImei1','fImei2','fNumero','fChip','fCor','fPatrimonio',
   'fDataEntrega','fObs'].forEach(id => $(id).value = '');
  $('fOperadora').value   = '';
  $('fStatus').value      = 'disponivel';
  $('fAcessorios').value  = 'bateria e carregador';
}

function preencherResponsaveis(selectedId) {
  const sel = $('fResponsavel');
  sel.innerHTML = '<option value="">— Sem responsável —</option>' +
    usuarios.map(u =>
      `<option value="${u.id}" ${u.id === selectedId ? 'selected' : ''}>${escHtml(u.name)}${u.cpf ? '' : ' (sem CPF)'}</option>`
    ).join('');
}

/* ============================================================
   SALVAR (POST ou PUT)
   ============================================================ */
async function salvarCelular() {
  const payload = {
    marca:           $('fMarca').value.trim(),
    modelo:          $('fModelo').value.trim(),
    imei1:           $('fImei1').value.trim(),
    imei2:           $('fImei2').value.trim() || null,
    numero_chip:     $('fChip').value.trim() || null,
    operadora:       $('fOperadora').value || null,
    numero_telefone: $('fNumero').value.trim() || null,
    patrimonio:      $('fPatrimonio').value.trim() || null,
    acessorios:      $('fAcessorios').value.trim() || 'bateria e carregador',
    cor:             $('fCor').value.trim() || null,
    status:          $('fStatus').value,
    responsavel_id:  parseInt($('fResponsavel').value) || null,
    data_entrega:    $('fDataEntrega').value || null,
    observacoes:     $('fObs').value.trim() || null,
  };

  if (!payload.marca || !payload.modelo || !payload.imei1) {
    alert('Marca, modelo e IMEI 1 são obrigatórios.');
    return;
  }

  try {
    const url    = editandoId ? `${API.celulares}/${editandoId}` : API.celulares;
    const method = editandoId ? 'PUT' : 'POST';
    const r = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${r.status}`);
    }
    fecharModal();
    await loadCelulares();
    renderTabela();
  } catch (err) {
    alert('Erro ao salvar: ' + err.message);
    console.error(err);
  }
}

/* ============================================================
   DELETAR
   ============================================================ */
async function deletarCelular(id) {
  const c = celulares.find(x => x.id === id);
  if (!c) return;
  if (!confirm(`Excluir o celular ${c.marca} ${c.modelo} (IMEI ${c.imei1})?\n\nO histórico será apagado.`)) return;
  try {
    const r = await fetch(`${API.celulares}/${id}`, { method: 'DELETE' });
    if (!r.ok && r.status !== 204) throw new Error('HTTP ' + r.status);
    await loadCelulares();
    renderTabela();
  } catch (err) {
    alert('Erro ao excluir: ' + err.message);
  }
}

/* ============================================================
   GERAR TERMO — abre nova aba com a página de impressão
   ============================================================ */
function gerarTermo(id) {
  window.open(`/SistemaCPE/web/pages/termo-celular.html?id=${id}`, '_blank');
}
