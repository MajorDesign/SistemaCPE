// =========================================
// 0. GERAÇÃO DE ID ALFANUMÉRICA
// =========================================

/**
 * Gera ID alfanumérica única no formato: AA9999B9C0
 * 
 * Formato:
 * - AA (2 letras): código do setor (ex: TI, RH, FN, CM)
 * - 9999 (4 números): número sequencial do ticket (incremental, 0001-9999)
 * - B (1 letra): tipo/prioridade (U=urgente, N=normal, A=alta, B=baixa)
 * - 9 (1 número): ano reduzido (ex: 6 para 2026)
 * - C (1 letra): categoria ou código interno (T=técnico, A=administrativo, etc)
 * - 0 (1 número): dígito verificador (checksum)
 * 
 * Total: exatamente 10 caracteres
 * 
 * @param {string} setor - Código do setor com 2 letras (ex: "TI", "RH", "FN")
 * @param {string} prioridade - 1 letra indicando prioridade (ex: "U", "N", "A", "B")
 * @param {string} categoria - 1 letra indicando categoria (ex: "T", "A", "V")
 * @param {number} sequencial - Número sequencial do ticket (1-9999, será preenchido com zeros)
 * @returns {string} ID formatada com exatamente 10 caracteres (ex: "TI0001U6T3")
 * @throws {Error} Se os parâmetros forem inválidos
 * 
 * @example
 * const id = gerarIdTicket("TI", "U", "T", 127);
 * // Retorna: "TI0127U6T5" (onde 6 é o ano atual reduzido, 5 é o dígito verificador)
 */
function gerarIdTicket(setor, prioridade, categoria, sequencial) {
  // ========================================
  // 1️⃣ VALIDAÇÕES DE ENTRADA
  // ========================================
  
  // Validar setor: deve ter exatamente 2 letras
  if (!setor || typeof setor !== 'string' || setor.length !== 2) {
    throw new Error('❌ Setor deve ter exatamente 2 letras (ex: "TI", "RH")');
  }
  
  const setorUpper = setor.toUpperCase();
  if (!/^[A-Z]{2}$/.test(setorUpper)) {
    throw new Error('❌ Setor deve conter apenas letras maiúsculas (ex: "TI", "RH")');
  }
  
  // Validar prioridade: deve ter exatamente 1 letra
  if (!prioridade || typeof prioridade !== 'string' || prioridade.length !== 1) {
    throw new Error('❌ Prioridade deve ter exatamente 1 letra (ex: "U", "N", "A", "B")');
  }
  
  const prioridadeUpper = prioridade.toUpperCase();
  if (!/^[A-Z]$/.test(prioridadeUpper)) {
    throw new Error('❌ Prioridade deve ser uma única letra maiúscula');
  }
  
  // Validar categoria: deve ter exatamente 1 letra
  if (!categoria || typeof categoria !== 'string' || categoria.length !== 1) {
    throw new Error('❌ Categoria deve ter exatamente 1 letra (ex: "T", "A", "V")');
  }
  
  const categoriaUpper = categoria.toUpperCase();
  if (!/^[A-Z]$/.test(categoriaUpper)) {
    throw new Error('❌ Categoria deve ser uma única letra maiúscula');
  }
  
  // Validar sequencial: deve ser número entre 1 e 9999
  const seqNum = parseInt(sequencial);
  if (isNaN(seqNum) || seqNum < 1 || seqNum > 9999) {
    throw new Error('❌ Sequencial deve ser um número entre 1 e 9999');
  }
  
  // ========================================
  // 2️⃣ GERAR COMPONENTES DA ID
  // ========================================
  
  // Setor: AA (2 letras maiúsculas)
  const parteSetor = setorUpper; // ex: "TI"
  
  // Sequencial: 9999 (4 dígitos, preenchido com zeros à esquerda)
  const parteSequencial = String(seqNum).padStart(4, '0'); // ex: "0127"
  
  // Prioridade: B (1 letra maiúscula)
  const partePrioridade = prioridadeUpper; // ex: "U"
  
  // Ano reduzido: 9 (último dígito do ano atual)
  const anoAtual = new Date().getFullYear(); // ex: 2026
  const parteAno = String(anoAtual).slice(-1); // ex: "6" (de 2026)
  
  // Categoria: C (1 letra maiúscula)
  const parteCategoria = categoriaUpper; // ex: "T"
  
  // ========================================
  // 3️⃣ CALCULAR DÍGITO VERIFICADOR (CHECKSUM)
  // ========================================
  
  /**
   * Calcula dígito verificador usando soma ponderada dos valores ASCII
   * Método simples e eficaz para evitar duplicatas
   */
  const idSemVerificador = parteSetor + parteSequencial + partePrioridade + parteAno + parteCategoria;
  
  // Calcular soma ponderada dos valores ASCII
  let somaChecksum = 0;
  for (let i = 0; i < idSemVerificador.length; i++) {
    const charCode = idSemVerificador.charCodeAt(i); // Código ASCII do caractere
    const peso = (i + 1); // Peso: 1 para posição 0, 2 para posição 1, etc
    somaChecksum += charCode * peso;
  }
  
  // Dígito verificador: último dígito da soma (0-9)
  const digitoVerificador = somaChecksum % 10;
  
  // ========================================
  // 4️⃣ MONTAR ID FINAL
  // ========================================
  
  const idFinal = idSemVerificador + digitoVerificador;
  
  // Garantir que tem exatamente 10 caracteres
  if (idFinal.length !== 10) {
    throw new Error(`❌ Erro ao gerar ID: tamanho incorreto (${idFinal.length} chars ao invés de 10)`);
  }
  
  // ========================================
  // 5️⃣ LOGGING E RETORNO
  // ========================================
  
  console.log(`[ID_GERADOR] ✅ ID gerada com sucesso`);
  console.log(`  - Setor:        ${parteSetor}`);
  console.log(`  - Sequencial:   ${parteSequencial}`);
  console.log(`  - Prioridade:   ${partePrioridade}`);
  console.log(`  - Ano:          ${parteAno}`);
  console.log(`  - Categoria:    ${parteCategoria}`);
  console.log(`  - Verificador:  ${digitoVerificador}`);
  console.log(`  - ID FINAL:     ${idFinal}`);
  
  return idFinal;
}

/**
 * Valida uma ID já gerada verificando seu dígito verificador
 * Útil para garantir integridade da ID
 * 
 * @param {string} id - ID a ser validada (10 caracteres)
 * @returns {boolean} true se a ID é válida, false caso contrário
 * 
 * @example
 * validarIdTicket("TI0127U6T5"); // true ou false
 */
function validarIdTicket(id) {
  // Validar tamanho
  if (!id || typeof id !== 'string' || id.length !== 10) {
    console.warn(`[ID_VALIDADOR] ⚠️ ID inválida: tamanho incorreto`);
    return false;
  }
  
  // Extrair componentes
  const idSemVerificador = id.substring(0, 9);
  const verificadorOriginal = parseInt(id.charAt(9));
  
  // Recalcular dígito verificador
  let somaChecksum = 0;
  for (let i = 0; i < idSemVerificador.length; i++) {
    const charCode = idSemVerificador.charCodeAt(i);
    const peso = (i + 1);
    somaChecksum += charCode * peso;
  }
  
  const verificadorCalculado = somaChecksum % 10;
  
  // Comparar
  const valido = verificadorOriginal === verificadorCalculado;
  
  if (valido) {
    console.log(`[ID_VALIDADOR] ✅ ID válida: ${id}`);
  } else {
    console.warn(`[ID_VALIDADOR] ❌ ID inválida: checksum não corresponde`);
  }
  
  return valido;
}

/**
 * Extrai e exibe informações de uma ID gerada
 * 
 * @param {string} id - ID a ser decomposta (10 caracteres)
 * @returns {object} Objeto com os componentes da ID
 * 
 * @example
 * const info = decompurIdTicket("TI0127U6T5");
 * // Retorna: { setor: "TI", sequencial: "0127", prioridade: "U", ano: "6", categoria: "T", verificador: "5" }
 */
function decompurIdTicket(id) {
  if (!id || id.length !== 10) {
    throw new Error('❌ ID deve ter exatamente 10 caracteres');
  }
  
  return {
    setor:        id.substring(0, 2),      // AA
    sequencial:   id.substring(2, 6),      // 9999
    prioridade:   id.substring(6, 7),      // B
    ano:          id.substring(7, 8),      // 9
    categoria:    id.substring(8, 9),      // C
    verificador:  id.substring(9, 10),     // 0
    completa:     id                       // AA9999B9C0
  };
}

/**
 * CPE Control - Sistema de Gestão de Tickets
 * Cliente JavaScript para gerenciamento de tickets
 * API: http://127.0.0.1:8000/api
 *
 * v2.1 - Alterações:
 * - Controle de permissão por role (USER / ADMIN / TI / MANAGER)
 * - usuario_id adicionado em todas as chamadas PUT e DELETE (obrigatório no backend)
 * - usuario_id adicionado no GET de interações (filtra comentários internos)
 * - Suporte a ?ticket_id= na URL (redireciona da notificação)
 * - Botões e abas ocultados por perfil
 */

// =========================================
// 1. VARIÁVEIS GLOBAIS
// =========================================

let tickets         = [];
let filteredTickets = [];
let selectedTickets = new Set();
let users           = [];
let groups          = [];
let currentPage     = 1;
let itemsPerPage    = 25;
let selectedTicketId = null;
let viewingTicketId  = null;
let isLoadingTickets = false;
let isLoadingUsers   = false;

// Vista atual: 'todos' | 'meus' | 'para_mim'
let currentVista = 'todos';

// Buffers de anexos pendentes (antes do envio)
//   pendingAttachments.create   → imagens para o novo ticket
//   pendingAttachments.reply    → imagens para a resposta pública
//   pendingAttachments.internal → imagens para o comentário interno
const pendingAttachments = { create: [], reply: [], internal: [] };
// 2026-08-19: aumentado 250 KB -> 10 MB e aceita agora DOC/DOCX/XLS/XLSX/PDF
// alem de imagens. Persistido em ticket_attachments (LONGBLOB) e vinculado
// a interacao_id — todos aparecem no historico do chamado.
const ATTACH_MAX_BYTES   = 10 * 1024 * 1024;  // 10 MB por arquivo
const ATTACH_MIMES_OK    = [
  // imagens
  'image/jpeg', 'image/png', 'image/webp', 'image/gif',
  // documentos
  'application/pdf',
  'application/msword',                                                       // .doc
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  // .docx
  'application/vnd.ms-excel',                                                 // .xls
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',        // .xlsx
];

const API_BASE    = (typeof API_BASE_URL !== 'undefined' ? API_BASE_URL : `http://${window.location.hostname || '127.0.0.1'}:8000`) + '/api';
const API_TIMEOUT = 10000;

// Roles com permissão de gerenciamento — espelha o backend (tickets.py)
const ROLES_ADMIN = new Set(['ADMIN', 'TI', 'MANAGER']);

// =========================================
// 2. HELPERS DE USUÁRIO LOGADO
// =========================================

/** Retorna o objeto do usuário logado a partir do localStorage. */
function getCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem('cpe_user') || '{}');
  } catch {
    return {};
  }
}

/** Retorna true se o usuário logado tem perfil de administrador. */
function isAdmin() {
  const user = getCurrentUser();
  return ROLES_ADMIN.has(user.role);
}

/** Retorna true se o usuário é Responsável de Grupo. */
function isResponsavelGrupo() {
  return getCurrentUser().role === 'RESPONSAVEL_GRUPO';
}

/** Retorna true se o usuário pode gerenciar tickets (admin ou responsável do grupo). */
function isGestor() {
  return isAdmin() || isResponsavelGrupo();
}

/** Retorna o ID do usuário logado (número). */
function getCurrentUserId() {
  const user = getCurrentUser();
  return user.id || user.usuario_id || null;
}

// =========================================
// 3. INICIALIZAÇÃO
// =========================================

document.addEventListener("DOMContentLoaded", async () => {
  console.log("[TICKETS] ⏳ Iniciando sistema de tickets...");

  try {
    const token   = localStorage.getItem('cpe_token');
    const userStr = localStorage.getItem('cpe_user');

    console.log('[TICKETS] Token encontrado:', !!token);
    console.log('[TICKETS] User encontrado:',  !!userStr);

    if (!token || !userStr) {
      console.error('[TICKETS] ❌ Dados de autenticação não encontrados!');
      showError('❌ Por favor, faça login novamente.');
      setTimeout(() => { window.location.href = '/SistemaCPE/web/login.html'; }, 2000);
      return;
    }

    console.log('[TICKETS] ✅ Autenticação OK');
    console.log('[TICKETS] 👤 Role:', getCurrentUser().role);

    // Aplica visibilidade de elementos antes de carregar dados
    applyRolePermissions();

    setupEventListeners();
    await loadUsers();
    await loadGroups();
    await loadTickets();

    // Carrega categorias e aplica preferencia salva de filtros (se houver)
    _carregarCategoriasFiltro().catch(() => {});

    // ✅ Abre ticket automaticamente se vier de notificação (?ticket_id=X)
    checkUrlTicketId();

    // ✅ Verifica avaliações pendentes e exibe popup se necessário
    setTimeout(verificarAvaliacoesPendentes, 1500);

    console.log("[TICKETS] ✅ Sistema carregado com sucesso!");

  } catch (erro) {
    console.error('[TICKETS] ❌ Erro na inicialização:', erro);
    showError(`❌ Erro ao inicializar: ${erro.message}`);
  }
});

// =========================================
// 4. PERMISSÕES POR ROLE
// =========================================

/**
 * Oculta ou exibe elementos da interface de acordo com o role do usuário.
 * Chamado uma vez na inicialização.
 */
function applyRolePermissions() {
  const gestor = isGestor(); // ADMIN, TI, MANAGER ou RESPONSAVEL_GRUPO
  const role   = getCurrentUser().role || 'USER';
  console.log(`[PERMISSAO] 🔐 Role: ${role} | Gestor: ${gestor}`);

  // Botão "Alterar" — gestores (admin + responsável do grupo)
  const btnAlterar = document.getElementById('btnAlterar');
  if (btnAlterar) btnAlterar.style.display = gestor ? '' : 'none';

  // Botão "Atribuir" — gestores (admin + responsável do grupo)
  const btnAtribuir = document.getElementById('btnAtribuir');
  if (btnAtribuir) btnAtribuir.style.display = gestor ? '' : 'none';

  // Botao "Permissoes" — so ADMIN e RESPONSAVEL_GRUPO
  // (TI/MANAGER veem tudo por padrao e nao precisam configurar restricao
  // por membro; UI so faz sentido pra quem gerencia o proprio time)
  const btnPerm = document.getElementById('btnPermissoesCat');
  if (btnPerm) {
    const podePerm = (role === 'ADMIN' || role === 'RESPONSAVEL_GRUPO');
    btnPerm.style.display = podePerm ? '' : 'none';
  }

  console.log(`[PERMISSAO] ✅ Elementos ajustados para role: ${role}`);
}

/* ================================================================
   PERMISSOES POR CATEGORIA — configuracao do responsavel do grupo
   Ver /api/tickets/permissoes/*
   ================================================================ */
let _permGroupId = null;
let _permMembroSelId = null;
let _permCatSelecionadas = new Set(); // "cat:ID" ou "sub:ID"

async function abrirModalPermissoes() {
  const cu = getCurrentUser() || {};
  const role = cu.role || 'USER';
  // ADMIN edita qualquer grupo — por ora, permite escolher SO o grupo do
  // proprio user autenticado (admin manda group_id via nav). Simplificado:
  // ambos usam users.group_id como alvo. Admin sem group_id ve alerta.
  _permGroupId = cu.group_id || null;
  if (!_permGroupId) {
    alert('Você não tem um grupo definido — impossível configurar permissões.\n' +
          'Se você é admin, atribua-se a um grupo em Usuários.');
    return;
  }
  _permMembroSelId = null;
  _permCatSelecionadas.clear();
  document.getElementById('permCatErro').classList.add('d-none');
  document.getElementById('permCatBtnSalvar').classList.add('d-none');
  document.getElementById('permCatBtnZerar').classList.add('d-none');
  document.getElementById('permCatCabecalho').innerHTML =
    '<div class="text-muted small">Selecione um membro à esquerda pra configurar.</div>';
  document.getElementById('permCatArvore').innerHTML = '';

  const modal = new bootstrap.Modal(document.getElementById('permCatModal'));
  modal.show();
  await _permCarregarMembros();
}

async function _permCarregarMembros() {
  const list = document.getElementById('permMembrosList');
  list.innerHTML = '<div class="text-center py-3 text-muted small"><i class="bi bi-hourglass-split"></i> Carregando...</div>';
  try {
    const r = await fetch(`${API_BASE_URL}/api/tickets/permissoes/grupo/${_permGroupId}/membros`, {
      credentials: 'include',
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const j = await r.json();
    const membros = (j.membros || []).filter(m => (m.role || 'USER').toUpperCase() === 'USER');
    if (!membros.length) {
      list.innerHTML = '<div class="text-muted small py-3 text-center">Nenhum membro USER no grupo.</div>';
      return;
    }
    list.innerHTML = membros.map(m => {
      const badge = m.ve_tudo
        ? '<span class="perm-badge" style="background:#d1fae5;color:#065f46">vê tudo</span>'
        : `<span class="perm-badge" style="background:#fef3c7;color:#78350f">${m.restricoes_count} restrição(ões)</span>`;
      return `<div class="perm-membro" data-uid="${m.id}" onclick="permCatSelecionarMembro(${m.id})">
        <span class="perm-nome">${_escHtmlP(m.name)}</span>
        <div class="small text-muted">${_escHtmlP(m.email)}</div>
        <div class="mt-1">${badge}</div>
      </div>`;
    }).join('');
  } catch (e) {
    list.innerHTML = `<div class="text-danger small py-3">Erro: ${_escHtmlP(e.message)}</div>`;
  }
}

async function permCatSelecionarMembro(userId) {
  _permMembroSelId = userId;
  document.querySelectorAll('#permMembrosList .perm-membro').forEach(el => {
    el.classList.toggle('active', Number(el.dataset.uid) === userId);
  });

  const arv = document.getElementById('permCatArvore');
  arv.innerHTML = '<div class="text-center py-3 text-muted small"><i class="bi bi-hourglass-split"></i> Carregando...</div>';
  try {
    const r = await fetch(`${API_BASE_URL}/api/tickets/permissoes/user/${userId}`, { credentials:'include' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const j = await r.json();

    _permCatSelecionadas.clear();
    (j.restricoes || []).forEach(rc => {
      if (rc.subcategoria_id) _permCatSelecionadas.add('sub:' + rc.subcategoria_id);
      else _permCatSelecionadas.add('cat:' + rc.categoria_id);
    });

    document.getElementById('permCatCabecalho').innerHTML =
      `<div style="font-weight:600">${_escHtmlP(j.membro.name)}</div>
       <div class="small text-muted">${_escHtmlP(j.membro.email)}</div>`;

    const cats = j.categorias_disponiveis || [];
    if (!cats.length) {
      arv.innerHTML = '<div class="text-muted small py-3 text-center">Este grupo não tem categorias cadastradas.</div>';
    } else {
      arv.innerHTML = cats.map(c => {
        const catKey = 'cat:' + c.categoria_id;
        const catChecked = _permCatSelecionadas.has(catKey);
        const subsHtml = (c.subcategorias || []).map(sc => {
          const subKey = 'sub:' + sc.subcategoria_id;
          const subChecked = _permCatSelecionadas.has(subKey);
          return `<label class="perm-sub-item">
            <input type="checkbox" data-key="${subKey}" data-parent-cat="${c.categoria_id}"
                   onchange="permCatToggle(this)" ${subChecked ? 'checked' : ''}>
            ${_escHtmlP(sc.subcategoria_nome)}
          </label>`;
        }).join('');
        return `<div class="perm-cat-block">
          <div class="perm-cat-title">
            <input type="checkbox" data-key="${catKey}" data-cat-id="${c.categoria_id}"
                   onchange="permCatToggle(this)" ${catChecked ? 'checked' : ''}>
            <i class="bi bi-folder"></i> ${_escHtmlP(c.categoria_nome)}
            <span class="text-muted small" style="font-weight:400">
              — marcar aqui libera a categoria inteira
            </span>
          </div>
          ${subsHtml ? `<div class="perm-sub-list">${subsHtml}</div>` : ''}
        </div>`;
      }).join('');
    }

    document.getElementById('permCatBtnSalvar').classList.remove('d-none');
    document.getElementById('permCatBtnZerar').classList.toggle('d-none', _permCatSelecionadas.size === 0);
  } catch (e) {
    arv.innerHTML = `<div class="text-danger small py-3">Erro: ${_escHtmlP(e.message)}</div>`;
  }
}

function permCatToggle(el) {
  const k = el.dataset.key;
  if (el.checked) {
    _permCatSelecionadas.add(k);
    // Se marcou uma categoria inteira, desmarca as subs dela (redundante)
    if (k.startsWith('cat:')) {
      const catId = el.dataset.catId;
      document.querySelectorAll(`#permCatArvore input[data-parent-cat="${catId}"]`).forEach(sub => {
        const sk = sub.dataset.key;
        _permCatSelecionadas.delete(sk);
        sub.checked = false;
      });
    }
  } else {
    _permCatSelecionadas.delete(k);
  }
  document.getElementById('permCatBtnZerar').classList.toggle('d-none', _permCatSelecionadas.size === 0);
}

async function permCatSalvar() {
  if (!_permMembroSelId) return;
  const items = [];
  _permCatSelecionadas.forEach(k => {
    const [tipo, idStr] = k.split(':');
    const id = Number(idStr);
    if (tipo === 'cat') items.push({ categoria_id: id });
    else if (tipo === 'sub') {
      // Precisa achar a categoria pai (procura no DOM)
      const el = document.querySelector(`#permCatArvore input[data-key="${k}"]`);
      const catId = Number(el?.dataset?.parentCat);
      if (catId) items.push({ categoria_id: catId, subcategoria_id: id });
    }
  });
  const btn = document.getElementById('permCatBtnSalvar');
  const orig = btn.innerHTML;
  btn.disabled = true; btn.innerHTML = '<i class="bi bi-arrow-repeat" style="animation:spin 1s linear infinite"></i> Salvando...';
  try {
    const r = await fetch(`${API_BASE_URL}/api/tickets/permissoes/user/${_permMembroSelId}`, {
      method:'PUT', credentials:'include',
      headers: { 'Content-Type':'application/json' },
      body: JSON.stringify({ categorias: items }),
    });
    const j = await r.json();
    if (!r.ok || !j.success) throw new Error(j.detail || 'Falha ao salvar');
    document.getElementById('permCatErro').classList.add('d-none');
    // Recarrega lista de membros pra atualizar o badge
    await _permCarregarMembros();
    document.querySelectorAll('#permMembrosList .perm-membro').forEach(el => {
      if (Number(el.dataset.uid) === _permMembroSelId) el.classList.add('active');
    });
    if (typeof showSuccess === 'function') showSuccess(`Salvo! ${j.restricoes_ativas} restrição(ões) ativa(s).`);
  } catch (e) {
    const err = document.getElementById('permCatErro');
    err.textContent = e.message;
    err.classList.remove('d-none');
  } finally {
    btn.disabled = false; btn.innerHTML = orig;
  }
}

async function permCatZerar() {
  if (!_permMembroSelId) return;
  if (!confirm('Remover todas as restrições deste membro (ele volta a ver tudo do grupo)?')) return;
  try {
    const r = await fetch(`${API_BASE_URL}/api/tickets/permissoes/user/${_permMembroSelId}`, {
      method:'DELETE', credentials:'include',
    });
    const j = await r.json();
    if (!r.ok || !j.success) throw new Error(j.detail || 'Falha');
    _permCatSelecionadas.clear();
    await permCatSelecionarMembro(_permMembroSelId);
    await _permCarregarMembros();
    document.querySelectorAll('#permMembrosList .perm-membro').forEach(el => {
      if (Number(el.dataset.uid) === _permMembroSelId) el.classList.add('active');
    });
  } catch (e) {
    const err = document.getElementById('permCatErro');
    err.textContent = e.message;
    err.classList.remove('d-none');
  }
}

function _escHtmlP(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}

/**
 * Aplica permissões dentro do modal de detalhe do ticket.
 * Chamado toda vez que o modal é aberto, pois depende do ticket visualizado.
 */
function applyDetailPermissions(ticket) {
  const admin                 = isAdmin();
  const userId                = getCurrentUserId();
  const isSolicitante         = ticket.solicitante_id === userId;
  const isResponsavelDoTicket = ticket.assignedTo === userId;
  const semResponsavel        = !ticket.assignedTo;
  const ticketResolvido       = ticket.status_id === 4;
  const ticketFechado         = ticket.status_id === 5;
  const ticketEncerrado       = ticketResolvido || ticketFechado;
  const reopen_count          = ticket.reopen_count || 0;

  // ── Aba "Ações": visível para solicitante, responsável do ticket ou admin ──
  const podeAcessarAcoes = admin || isSolicitante || isResponsavelDoTicket;
  const tabActions = document.querySelector('[onclick="switchTab(event, \'actions\')"]');
  if (tabActions) tabActions.style.display = podeAcessarAcoes ? '' : 'none';

  // ── Seção "Finalizar": APENAS o responsável do ticket, enquanto não encerrado ──
  const sectionFinalizar = document.getElementById('sectionFinalizarChamado');
  if (sectionFinalizar)
    sectionFinalizar.style.display = (isResponsavelDoTicket && !ticketEncerrado) ? '' : 'none';

  // ── Seção "Reabrir": solicitante OU admin, quando resolvido, até 3 vezes ──
  const sectionReabrir = document.getElementById('sectionReabrirChamado');
  if (sectionReabrir) {
    if ((isSolicitante || admin) && ticketResolvido) {
      sectionReabrir.style.display = '';
      const esgotado = document.getElementById('reabrirEsgotado');
      const btnReabrir = document.getElementById('btnReopenChamado');
      if (reopen_count >= 3) {
        if (esgotado)  esgotado.style.display  = '';
        if (btnReabrir) btnReabrir.style.display = 'none';
      } else {
        if (esgotado)  esgotado.style.display  = 'none';
        if (btnReabrir) btnReabrir.style.display = '';
      }
    } else {
      sectionReabrir.style.display = 'none';
    }
  }

  // ── Seção "Alterar Status": APENAS o responsável do ticket, enquanto não encerrado ──
  const sectionStatus = document.getElementById('sectionAlterarStatus');
  if (sectionStatus)
    sectionStatus.style.display = (isResponsavelDoTicket && !ticketEncerrado) ? '' : 'none';

  // ── Seção "Atribuir Responsável": apenas admins ──
  const sectionAtribuir = document.getElementById('sectionAtribuirResponsavel');
  if (sectionAtribuir) sectionAtribuir.style.display = admin ? '' : 'none';

  // ── Aba "Comentário Interno": apenas admin ──
  const tabInternal = document.querySelector('[onclick="switchReplyMode(event, \'internal\')"]');
  if (tabInternal) tabInternal.style.display = admin ? '' : 'none';

  // ── Formulário de resposta: oculto se encerrado ou sem permissão ──
  const podeInteragir = !ticketEncerrado && (admin || isSolicitante || isResponsavelDoTicket);
  const replyForm = document.getElementById('detailReplyForm');
  if (replyForm) {
    replyForm.style.display = podeInteragir ? '' : 'none';
    document.getElementById('readonlyNotice')?.remove();
    if (!podeInteragir) {
      const notice = document.createElement('p');
      notice.id = 'readonlyNotice';
      notice.className = 'text-muted text-center py-2 small';
      notice.innerHTML = ticketEncerrado
        ? '<i class="bi bi-lock"></i> Chamado encerrado — somente visualização.'
        : '<i class="bi bi-eye"></i> Você pode visualizar este chamado mas não pode interagir.';
      replyForm.parentNode.insertBefore(notice, replyForm);
    }
  }

  // ── Ticket encerrado: aplicar overlay cinza ──
  const modalBody = document.querySelector('#ticketDetailModal .modal-body');
  if (modalBody) {
    if (ticketEncerrado) modalBody.classList.add('ticket-encerrado');
    else                 modalBody.classList.remove('ticket-encerrado');
  }

  // ── Botão "Deletar": apenas RESPONSAVEL_GRUPO ──
  const btnDeletar = document.getElementById('btnDeletarTicket');
  if (btnDeletar) btnDeletar.style.display = isResponsavelGrupo() ? '' : 'none';

  // ── Botão "Assumir": sem responsável + mesmo grupo + não encerrado ──
  const btnAssumir = document.getElementById('btnAssumirTicket');
  if (btnAssumir) {
    const user = getCurrentUser();
    const mesmoGrupo = admin || (user.group_id && user.group_id === ticket.group_id);
    btnAssumir.classList.toggle('d-none', !(semResponsavel && mesmoGrupo && !ticketEncerrado));
  }

  // ── Botão "Desistir": apenas o responsável atual, não encerrado ──
  const btnDevolver = document.getElementById('btnDevolverTicket');
  if (btnDevolver)
    btnDevolver.classList.toggle('d-none', !(isResponsavelDoTicket && !ticketEncerrado));

  // ── Botão "Encaminhar":
  //    - Sem responsável: solicitante OU membros do grupo podem encaminhar
  //    - Com responsável (atendimento iniciado): APENAS o responsável
  //    - Nunca quando encerrado
  const btnEncaminhar = document.getElementById('btnEncaminharTicket');
  if (btnEncaminhar) {
    const user = getCurrentUser();
    const mesmoGrupo = admin || (user.group_id && user.group_id === ticket.group_id);
    const podeEncaminhar = !ticketEncerrado && (
      semResponsavel
        ? (isSolicitante || mesmoGrupo)
        : (isResponsavelDoTicket || admin)
    );
    btnEncaminhar.classList.toggle('d-none', !podeEncaminhar);
  }

  console.log(`[PERMISSAO] ✅ Modal | solicitante:${isSolicitante} | responsavelTicket:${isResponsavelDoTicket} | encerrado:${ticketEncerrado}`);
}

// =========================================
// 5. SUPORTE A ?ticket_id= NA URL
// =========================================

/**
 * Verifica se a URL contém ?ticket_id=X.
 * Se sim, abre o modal desse ticket automaticamente.
 * Isso é chamado pelo nav.js ao clicar em uma notificação.
 */
function checkUrlTicketId() {
  const params   = new URLSearchParams(window.location.search);
  const ticketId = parseInt(params.get('ticket_id'));

  if (!ticketId) return;

  console.log(`[URL] 🔔 ticket_id encontrado na URL: #${ticketId}`);

  const ticket = tickets.find(t => t.id === ticketId);
  if (ticket) {
    openTicketDetail(ticketId);
  } else {
    console.warn(`[URL] ⚠️ Ticket #${ticketId} não encontrado na lista carregada`);
    showError(`⚠️ Ticket #${ticketId} não encontrado ou sem permissão de acesso.`);
  }

  // Remove o parâmetro da URL sem recarregar a página
  const url = new URL(window.location);
  url.searchParams.delete('ticket_id');
  window.history.replaceState({}, '', url);
}

// =========================================
// 6. EVENT LISTENERS
// =========================================

function setupEventListeners() {
  console.log("[TICKETS] 🔌 Configurando event listeners...");

  const elementos = {
    'searchInput':      'input',
    'statusFilter':     'change',
    'priorityFilter':   'change',
    'ticketForm':       'submit',
    'assignForm':       'submit',
    'detailReplyForm':  'submit',
    'detailInternalForm': 'submit',
    'selectAll':        'change'
  };

  const handlers = {
    'searchInput':        applyFilters,
    'statusFilter':       applyFilters,
    'priorityFilter':     applyFilters,
    'ticketForm':         handleFormSubmit,
    'assignForm':         submitAssign,
    'detailReplyForm':    submitDetailReply,
    'detailInternalForm': submitDetailInternal,
    'selectAll':          (e) => toggleSelectAll(e.target)
  };

  for (const [elementId, event] of Object.entries(elementos)) {
    const element = document.getElementById(elementId);
    if (element) {
      element.addEventListener(event, handlers[elementId]);
      console.log(`  ✓ ${elementId}`);
    } else {
      console.warn(`  ⚠️ Elemento #${elementId} não encontrado`);
    }
  }
}

// =========================================
// 7. REQUISIÇÕES À API
// =========================================

async function apiRequest(method, endpoint, body = null) {
  try {
    const token = localStorage.getItem('cpe_token');

    if (!token) {
      console.error('[API] ❌ Token não encontrado!');
      showError('❌ Sessão expirada. Faça login novamente.');
      setTimeout(() => { window.location.href = '/SistemaCPE/web/login.html'; }, 2000);
      return null;
    }

    const options = {
      method,
      headers: {
        'Content-Type':  'application/json',
        'Authorization': `Bearer ${token}`
      }
    };

    if (body) options.body = JSON.stringify(body);

    console.log(`[API] 📤 ${method} ${endpoint}`);

    const controller = new AbortController();
    const timeoutId  = setTimeout(() => controller.abort(), API_TIMEOUT);
    options.signal   = controller.signal;

    const response = await fetch(`${API_BASE}${endpoint}`, options);
    clearTimeout(timeoutId);

    if ([401, 403].includes(response.status)) {
      console.error('[API] ❌ Não autorizado (401/403)');
      localStorage.clear();
      showError('❌ Sessão expirada. Faça login novamente.');
      setTimeout(() => { window.location.href = '/SistemaCPE/web/login.html'; }, 2000);
      return null;
    }

    if (response.status === 204) {
      console.log(`[API] ✅ ${method} ${endpoint} (No Content)`);
      return { success: true };
    }

    const responseData = await response.json();

    if (!response.ok) {
      const errorDetail = responseData.detail || `Erro ${response.status}`;
      throw new Error(errorDetail);
    }

    console.log(`[API] ✅ ${method} ${endpoint}`);
    return responseData;

  } catch (error) {
    if (error.name === 'AbortError') {
      console.error(`[API] ⏱️ Timeout: ${endpoint}`);
      showError('⏱️ Requisição expirou. Tente novamente.');
    } else {
      console.error(`[API] ❌ Erro: ${error.message}`);
      showError(`❌ Erro na API: ${error.message}`);
    }
    return null;
  }
}

// =========================================
// 8. CARREGAR USUÁRIOS
// =========================================

async function loadUsers() {
  if (isLoadingUsers) return;
  isLoadingUsers = true;
  console.log("[USUARIOS] 📥 Carregando usuários da API...");

  try {
    const data = await apiRequest('GET', '/users');

    if (!data || !Array.isArray(data)) {
      console.warn('[USUARIOS] ⚠️ Resposta inválida da API');
      users = [];
    } else {
      users = data.map(u => ({
        id:    u.id,
        name:  u.name  || u.nome  || 'Sem nome',
        email: u.email || 'sem-email',
        role:  u.role  || 'USER'
      }));
      console.log(`[USUARIOS] ✅ ${users.length} usuário(s) carregado(s)`);
    }

    populateUserDropdowns();

  } catch (error) {
    console.error('[USUARIOS] ❌ Erro ao carregar:', error);
    users = [];
  } finally {
    isLoadingUsers = false;
  }
}

function populateUserDropdowns() {
  console.log("[USUARIOS] 🔍 Populando dropdowns...");

  const dropdownConfigs = [
    { id: "assignUser",        placeholder: "Selecione um usuário..." },
    { id: "detailAssignSelect", placeholder: "Não atribuído" }
  ];

  const optionsHTML = users.map(u =>
    `<option value="${u.id}">${u.name}</option>`
  ).join("");

  dropdownConfigs.forEach(config => {
    const element = document.getElementById(config.id);
    if (element) {
      element.innerHTML = `<option value="">${config.placeholder}</option>` + optionsHTML;
      console.log(`[USUARIOS] ✅ Dropdown #${config.id} preenchido com ${users.length} usuários.`);
    } else {
      console.warn(`[USUARIOS] ⚠️ Dropdown #${config.id} não encontrado no DOM.`);
    }
  });
}

// =========================================
// 8B. CARREGAR GRUPOS
// =========================================

async function loadGroups() {
  console.log("[GRUPOS] 📥 Carregando grupos da API...");
  try {
    // scope=all porque o dropdown 'Setor de destino' do modal Novo
    // Ticket e o modal 'Encaminhar' precisam mostrar TODOS os grupos —
    // qualquer user abre chamado pra qualquer setor. Sem esse param
    // o backend filtra por role e USER so ve o proprio grupo (fix
    // 2026-08-14 documentado em GOTCHAS/REGRAS_NEGOCIO).
    const data = await apiRequest('GET', '/groups?scope=all');
    if (!data || !Array.isArray(data)) {
      console.warn('[GRUPOS] ⚠️ Resposta inválida');
      groups = [];
    } else {
      groups = data.map(g => ({ id: g.id, name: g.name }));
      console.log(`[GRUPOS] ✅ ${groups.length} grupo(s) carregado(s)`);
    }
  } catch (error) {
    console.error('[GRUPOS] ❌ Erro ao carregar:', error);
    groups = [];
  }
}

function populateGroupDropdown() {
  const select = document.getElementById('ticketGroupName');
  if (!select) return;

  const user = getCurrentUser();
  const userGroupId = user.group_id || user.grupo_id || null;

  select.innerHTML = '<option value="">Selecione o grupo...</option>' +
    groups.map(g =>
      `<option value="${g.id}" ${g.id == userGroupId ? 'selected' : ''}>${g.name}</option>`
    ).join('');

  console.log(`[GRUPOS] ✅ Select populado com ${groups.length} grupos (padrão: ${userGroupId})`);

  // Ao mudar o grupo, carregar categorias desse grupo
  select.addEventListener('change', async () => {
    const gid = parseInt(select.value);
    resetCategoriaSubcategoria();
    if (!gid) return;
    await carregarCategoriasTicket(gid);
  });

  // Se já tem grupo pré-selecionado, carregar categorias imediatamente
  if (userGroupId) {
    carregarCategoriasTicket(userGroupId);
  }
}

/** Carrega categorias do grupo selecionado e popula o select de categoria.
 *  Se o grupo tem categorias cadastradas, exibe e marca 'required'.
 *  Se nao tem, oculta e remove 'required' (evita travar o submit do form).
 */
async function carregarCategoriasTicket(groupId) {
  const catDiv    = document.getElementById('ticketCategoriaDiv');
  const catSelect = document.getElementById('ticketCategoria');
  if (!catDiv || !catSelect) return;

  try {
    const res = await fetch(`${API_BASE}/categorias?group_id=${groupId}`);
    if (!res.ok) return;
    const cats = await res.json();

    if (!cats.length) {
      catDiv.classList.add('d-none');
      catSelect.required = false;
      return;
    }

    catSelect.innerHTML = '<option value="">Selecione uma categoria...</option>' +
      cats.map(c => `<option value="${c.id}" data-subs='${JSON.stringify(c.subcategorias || [])}'>${c.nome}</option>`).join('');

    catDiv.classList.remove('d-none');
    catSelect.required = true;

    // Ao mudar categoria, popular subcategorias + recarregar campos custom
    catSelect.onchange = () => {
      const opt  = catSelect.options[catSelect.selectedIndex];
      const subs = opt ? JSON.parse(opt.dataset.subs || '[]') : [];
      preencherSubcategorias(subs);
      carregarCamposTicket();
    };

  } catch (e) {
    console.warn('[TICKET] Erro ao carregar categorias:', e);
  }
}

/** Mostra/limpa a mensagem de erro no rodapé do modal de novo ticket */
function setTicketModalErro(msg) {
  const box = document.getElementById('ticketModalErro');
  const txt = document.getElementById('ticketModalErroMsg');
  if (!box || !txt) return;
  if (msg) { txt.textContent = msg; box.style.display = ''; }
  else { box.style.display = 'none'; }
}

/** Busca os campos personalizados da categoria+subcategoria e renderiza no form */
async function carregarCamposTicket() {
  const wrap = document.getElementById('ticketCamposCustomWrap');
  const cont = document.getElementById('ticketCamposCustom');
  if (!wrap || !cont) return;

  const catId = document.getElementById('ticketCategoria')?.value || '';
  const subId = document.getElementById('ticketSubcategoria')?.value || '';

  if (!catId && !subId) {
    wrap.classList.add('d-none');
    cont.innerHTML = '';
    return;
  }

  try {
    const qs = [];
    if (catId) qs.push('categoria_id=' + catId);
    if (subId) qs.push('subcategoria_id=' + subId);
    const res = await fetch(`${API_BASE}/categoria-campos/do-ticket?` + qs.join('&'));
    if (!res.ok) { wrap.classList.add('d-none'); return; }
    const campos = (await res.json()).campos || [];

    if (!campos.length) {
      wrap.classList.add('d-none');
      cont.innerHTML = '';
      return;
    }

    const tipoInput = { texto: 'text', numero: 'number', data: 'date' };
    cont.innerHTML = campos.map(c => {
      const req = c.obrigatorio ? ' <span class="text-danger">*</span>' : '';
      return `
        <div class="col-md-6">
          <label class="form-label mb-1" style="font-size:.8rem;">${escapeHtml(c.label)}${req}</label>
          <input type="${tipoInput[c.tipo] || 'text'}"
                 class="form-control form-control-sm ticket-campo-custom"
                 data-campo-id="${c.id}"
                 data-obrigatorio="${c.obrigatorio ? 1 : 0}"
                 data-label="${escapeHtml(c.label)}"
                 oninput="this.classList.remove('is-invalid'); setTicketModalErro('');">
          <div class="invalid-feedback" style="font-size:.75rem;">
            <i class="bi bi-exclamation-circle"></i> Campo obrigatório
          </div>
        </div>`;
    }).join('');
    wrap.classList.remove('d-none');
  } catch (e) {
    console.warn('[TICKET] Erro ao carregar campos personalizados:', e);
    wrap.classList.add('d-none');
  }
}

/** Preenche o select de subcategorias com base na categoria escolhida.
 *  Se a categoria tem subcategorias, exibe e marca 'required'. Senao oculta.
 */
function preencherSubcategorias(subs) {
  const subDiv    = document.getElementById('ticketSubcategoriaDiv');
  const subSelect = document.getElementById('ticketSubcategoria');
  if (!subDiv || !subSelect) return;

  subSelect.innerHTML = '<option value="">Selecione uma subcategoria...</option>';

  if (!subs.length) {
    subDiv.classList.add('d-none');
    subSelect.required = false;
    return;
  }

  subs.forEach(s => {
    const opt = document.createElement('option');
    opt.value       = s.id;
    opt.textContent = s.nome;
    subSelect.appendChild(opt);
  });
  subDiv.classList.remove('d-none');
  subSelect.required = true;

  // Ao trocar a subcategoria, recarrega os campos personalizados
  subSelect.onchange = () => carregarCamposTicket();
}

/** Limpa categoria e subcategoria ao mudar de grupo */
function resetCategoriaSubcategoria() {
  const catDiv  = document.getElementById('ticketCategoriaDiv');
  const subDiv  = document.getElementById('ticketSubcategoriaDiv');
  const catSel  = document.getElementById('ticketCategoria');
  const subSel  = document.getElementById('ticketSubcategoria');
  if (catDiv)  catDiv.classList.add('d-none');
  if (subDiv)  subDiv.classList.add('d-none');
  if (catSel)  { catSel.innerHTML = '<option value="">Selecione uma categoria...</option>'; catSel.required = false; }
  if (subSel)  { subSel.innerHTML = '<option value="">Selecione uma subcategoria...</option>'; subSel.required = false; }
  // Esconde os campos personalizados ao trocar de grupo
  const camposWrap = document.getElementById('ticketCamposCustomWrap');
  const camposCont = document.getElementById('ticketCamposCustom');
  if (camposWrap) camposWrap.classList.add('d-none');
  if (camposCont) camposCont.innerHTML = '';
}

// =========================================
// 9. CARREGAR TICKETS
// =========================================

async function loadTickets() {
  if (isLoadingTickets) return;
  isLoadingTickets = true;
  console.log("[TICKETS] 📥 Carregando tickets...");

  try {
    // ✅ CORRIGIDO: Adicionar usuario_id obrigatório na requisição
    const userId = getCurrentUserId();
    if (!userId) {
      console.error('[TICKETS] ❌ usuario_id não encontrado!');
      showError('❌ Erro: usuário não identificado. Faça login novamente.');
      return;
    }

    console.log(`[TICKETS] 📤 Enviando usuario_id=${userId} para backend...`);
    const data = await apiRequest('GET', `/tickets?usuario_id=${userId}`);

    if (!data || !Array.isArray(data)) {
      console.warn('[TICKETS] ⚠️ Resposta inválida');
      tickets = [];
    } else {
      tickets = data.map(t => ({
        id:              t.id,
        numero:          t.numero || `#${t.id}`,
        id_alfanumerica: t.id_alfanumerica || null,
        title:           t.assunto || 'Sem título',
        userName:        t.solicitante_nome  || "Desconhecido",
        email:           t.solicitante_email || "sem-email",
        groupName:       t.group_name        || "Sem setor",
        group_id:        t.group_id          || null,
        priority:        mapPriorityFromApi(t.prioridade_id),
        status:          mapStatusFromApi(t.status_id),
        status_id:       t.status_id,
        assignedTo:      t.responsavel_id,
        assignedName:    t.responsavel_nome || "Não atribuído",
        solicitante_id:  t.solicitante_id,
        categoria_id:    t.categoria_id    || null,
        subcategoria_id: t.subcategoria_id || null,
        reopen_count:    t.reopen_count || 0,
        createdAt:       formatDate(t.created_at),
        createdAtFull:   t.created_at,
        updatedAt:       formatDate(t.updated_at),
        updatedAtFull:   t.updated_at,
        description:     t.descricao_inicial || 'Sem descrição',
        sla:             t.sla || null
      }));

      // O backend já filtra corretamente por role:
      // - ADMIN/TI/MANAGER → todos os tickets
      // - RESPONSAVEL_GRUPO → tickets do seu grupo
      // - USER → tickets que criou ou foram atribuídos a ele
      console.log(`[TICKETS] ✅ ${tickets.length} ticket(s) carregado(s)`);
    }

    applyFilters();
    updateStatistics();

  } catch (error) {
    console.error('[TICKETS] ❌ Erro ao carregar:', error);
    tickets = [];
  } finally {
    isLoadingTickets = false;
    renderTable();
  }
}

// =========================================
// 10. MAPEAR DADOS DA API
// =========================================

/**
 * Retorna true se o ticket foi criado há menos de 2h e ainda está aberto (sem responsável atribuído).
 */
function isNewTicket(ticket) {
  if (ticket.status !== 'open') return false;
  if (ticket.assignedTo) return false;
  const created = new Date(ticket.createdAtFull);
  return (Date.now() - created.getTime()) < 2 * 60 * 60 * 1000; // 2 horas
}

function mapPriorityFromApi(id) { return { 1: 'low', 2: 'medium', 3: 'high', 4: 'urgent' }[id] || 'medium'; }
function mapPriorityToApi(p)    { return { 'low': 1, 'medium': 2, 'high': 3, 'urgent': 4 }[p] || 2; }
function mapStatusFromApi(id)   { return { 1: 'open', 2: 'in-progress', 3: 'waiting', 4: 'resolved', 5: 'closed' }[id] || 'open'; }
function mapStatusToApi(s)      { return { 'open': 1, 'in-progress': 2, 'waiting': 3, 'resolved': 4, 'closed': 5 }[s] || 1; }
function formatDate(d)          { return d ? new Date(d).toLocaleDateString('pt-BR') : 'N/A'; }
function formatDateTime(d)      { return d ? new Date(d).toLocaleString('pt-BR')     : 'N/A'; }


/**
 * Mapeia prioridade de texto para código de 1 letra para ID alfanumérica
 * @param {string} priority - Prioridade (low, medium, high, urgent)
 * @returns {string} Código de 1 letra (B=baixa, N=normal, A=alta, U=urgente)
 */
function mapaPriorityToCode(priority) {
  const map = {
    'low':    'B',      // Baixa
    'medium': 'N',      // Normal
    'high':   'A',      // Alta
    'urgent': 'U'       // Urgente
  };
  return map[priority] || 'N';
}
// =========================================
// 11. FILTROS
// =========================================

function applyFilters() {
  const search    = document.getElementById("searchInput")?.value?.toLowerCase().trim() || "";
  const status    = document.getElementById("statusFilter")?.value || "";
  const priority  = document.getElementById("priorityFilter")?.value || "";
  const grupoId   = document.getElementById("grupoFilter")?.value        || "";
  const respId    = document.getElementById("responsavelFilter")?.value  || "";
  const catId     = document.getElementById("categoriaFilter")?.value    || "";
  const subId     = document.getElementById("subcategoriaFilter")?.value || "";

  const userId = getCurrentUserId();
  const matchVista = (t) => {
    if (currentVista === 'meus')     return t.solicitante_id === userId;
    if (currentVista === 'para_mim') return t.assignedTo === userId;
    return true; // 'todos'
  };

  filteredTickets = tickets.filter(t =>
    matchVista(t) &&
    (!status   || t.status   === status)   &&
    (!priority || t.priority === priority) &&
    (!grupoId  || String(t.group_id)        === grupoId) &&
    (!respId   || String(t.assignedTo || '') === respId) &&
    (!catId    || String(t.categoria_id)    === catId) &&
    (!subId    || String(t.subcategoria_id) === subId) &&
    (!search   || t.title.toLowerCase().includes(search) ||
                  t.userName.toLowerCase().includes(search) ||
                  t.numero.toLowerCase().includes(search))
  );

  updateVistaCounts();
  currentPage = 1;
  renderTable();

  // Depois de renderizar, decide se abre banner "salvar como padrão"
  atualizarBannerFiltroPref();
}

function clearFilters() {
  ['searchInput', 'statusFilter', 'priorityFilter', 'grupoFilter',
   'responsavelFilter', 'categoriaFilter', 'subcategoriaFilter'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  const catSel = document.getElementById('categoriaFilter');
  const subSel = document.getElementById('subcategoriaFilter');
  if (catSel) { catSel.innerHTML = '<option value="">Categoria</option>'; catSel.disabled = true; }
  if (subSel) { subSel.innerHTML = '<option value="">Subcategoria</option>'; subSel.disabled = true; }
  // Responsavel volta a listar todos os users
  _popularResponsavelFiltro(null);
  applyFilters();
  showSuccess("✅ Filtros limpos");
}

function toggleAdvancedFilters() {
  const el = document.getElementById("advancedFilters");
  el?.classList.toggle('d-none');
  // Carrega Grupo/Responsavel lazy — so quando o painel abre a primeira vez
  if (el && !el.classList.contains('d-none')) {
    _carregarFiltrosCascata();
  }
}

/* ================================================================
   FILTRO POR CATEGORIA / SUBCATEGORIA + PREFERENCIA SALVA
   ================================================================ */

// Cache das categorias do grupo do user (com subs embutidas)
let _categoriasFiltroCache = null;
// True enquanto o banner "salvar como padrao" fica aberto pra combinacao atual
let _bannerFiltroSuprimido = new Set(); // combinacoes ja descartadas

// Caches de Grupo e Users (compartilhados; carregados 1x)
let _gruposFiltroCache = null;
let _usersFiltroCache  = null;

/**
 * Popula Grupo (todos, via /groups?scope=all) e Responsavel (todos
 * users ativos, via /users/) — inicial. Cada mudanca no Grupo dispara
 * onGrupoFilterChange() que refiltra as categorias e o responsavel.
 * Aplica pref salva no final.
 */
async function _carregarFiltrosCascata() {
  if (_gruposFiltroCache && _usersFiltroCache) {
    _aplicarFiltrosPrefSeExiste();
    return;
  }
  try {
    const [grupos, users] = await Promise.all([
      fetch(`${API_BASE}/groups?scope=all`, { credentials: 'include' }).then(r => r.ok ? r.json() : []),
      fetch(`${API_BASE}/users/`,             { credentials: 'include' }).then(r => r.ok ? r.json() : []),
    ]);
    _gruposFiltroCache = Array.isArray(grupos) ? grupos : (grupos?.groups || []);
    const arrUsers = Array.isArray(users) ? users : (users?.users || []);
    _usersFiltroCache = arrUsers
      .filter(u => u.is_active !== 0)
      .map(u => ({ id: u.id, name: u.name, group_id: u.group_id }));

    const gSel = document.getElementById('grupoFilter');
    if (gSel) {
      gSel.innerHTML = '<option value="">Grupo</option>' +
        _gruposFiltroCache.map(g => `<option value="${g.id}">${_escHtmlP(g.name)}</option>`).join('');
    }
    _popularResponsavelFiltro(null);
  } catch (e) {
    console.warn('[TICKETS/FILTRO] erro ao carregar grupos/users:', e);
  }
  // Aplica pref salva (grupo/status/priority/cat/sub/responsavel)
  _aplicarFiltrosPrefSeExiste();
}

function _popularResponsavelFiltro(grupoId) {
  const sel = document.getElementById('responsavelFilter');
  if (!sel || !_usersFiltroCache) return;
  const atual = sel.value;
  let lista = _usersFiltroCache;
  if (grupoId) lista = lista.filter(u => String(u.group_id || '') === String(grupoId));
  lista = [...lista].sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  sel.innerHTML = '<option value="">Responsável</option>' +
    lista.map(u => `<option value="${u.id}">${_escHtmlP(u.name)}</option>`).join('');
  if (atual && lista.some(u => String(u.id) === atual)) sel.value = atual;
}

async function onGrupoFilterChange() {
  const gid    = document.getElementById('grupoFilter')?.value || '';
  const catSel = document.getElementById('categoriaFilter');
  const subSel = document.getElementById('subcategoriaFilter');

  if (catSel) { catSel.innerHTML = '<option value="">Categoria</option>';    catSel.disabled = !gid; }
  if (subSel) { subSel.innerHTML = '<option value="">Subcategoria</option>'; subSel.disabled = true; }
  _popularResponsavelFiltro(gid || null);

  if (gid) {
    try {
      const r = await fetch(`${API_BASE}/categorias?group_id=${gid}`, { credentials:'include' });
      if (r.ok) {
        const cats = await r.json();
        _categoriasFiltroCache = cats || [];
        catSel.innerHTML = '<option value="">Categoria</option>' +
          _categoriasFiltroCache.map(c =>
            `<option value="${c.id}" data-subs='${JSON.stringify(c.subcategorias || [])}'>${_escHtmlP(c.nome)}</option>`
          ).join('');
      }
    } catch (e) { console.warn('[TICKETS/FILTRO] erro cats:', e); }
  }
  applyFilters();
}

/**
 * @deprecated Mantido apenas pro caso de alguem chamar externamente.
 * A logica migrou pra _carregarFiltrosCascata + onGrupoFilterChange.
 */
async function _carregarCategoriasFiltro() {
  return _carregarFiltrosCascata();
}

function onCategoriaFilterChange() {
  const catSel = document.getElementById('categoriaFilter');
  const subSel = document.getElementById('subcategoriaFilter');
  if (!catSel || !subSel) return;

  const opt  = catSel.options[catSel.selectedIndex];
  const subs = (opt && opt.dataset.subs) ? JSON.parse(opt.dataset.subs || '[]') : [];
  subSel.innerHTML = '<option value="">Subcategoria</option>' +
    subs.map(s => `<option value="${s.id}">${_escHtmlP(s.nome)}</option>`).join('');
  subSel.disabled = !catSel.value || subs.length === 0;
  applyFilters();
}

// Estado atual dos filtros como objeto simples
function _filtrosAtuaisSnapshot() {
  return {
    status:          document.getElementById("statusFilter")?.value        || "",
    priority:        document.getElementById("priorityFilter")?.value      || "",
    grupo_id:        document.getElementById("grupoFilter")?.value         || "",
    responsavel_id:  document.getElementById("responsavelFilter")?.value   || "",
    categoria_id:    document.getElementById("categoriaFilter")?.value     || "",
    subcategoria_id: document.getElementById("subcategoriaFilter")?.value  || "",
  };
}

function _filtroVazio(f) {
  return !f.status && !f.priority && !f.grupo_id && !f.responsavel_id
         && !f.categoria_id && !f.subcategoria_id;
}

function _filtroIguais(a, b) {
  return a.status === b.status && a.priority === b.priority &&
         a.grupo_id === b.grupo_id && a.responsavel_id === b.responsavel_id &&
         a.categoria_id === b.categoria_id && a.subcategoria_id === b.subcategoria_id;
}

function _prefKey() {
  const uid = getCurrentUserId() || 'anon';
  return `tickets_filter_prefs_v1_${uid}`;
}

function _lerPref() {
  try { return JSON.parse(localStorage.getItem(_prefKey()) || 'null'); }
  catch { return null; }
}

function _salvarPref(f) {
  try { localStorage.setItem(_prefKey(), JSON.stringify(f)); }
  catch (_) {}
}

function _limparPref() {
  try { localStorage.removeItem(_prefKey()); } catch (_) {}
}

/**
 * Decide se mostra o banner "salvar como padrao" (aparece quando o
 * usuario aplicou filtros diferentes do que ja esta salvo e ainda nao
 * descartou essa combinacao nesta sessao).
 */
function atualizarBannerFiltroPref() {
  const banner = document.getElementById('filterPrefBanner');
  const ativo  = document.getElementById('filterPrefAtiva');
  if (!banner || !ativo) return;

  const atual = _filtrosAtuaisSnapshot();
  const pref  = _lerPref();

  // Indicador de pref ativa (mostrado se ha pref salva)
  ativo.classList.toggle('d-none', !pref);

  // Banner: mostra so quando ha filtro nao-vazio, nao bate com pref, e
  // essa combinacao ainda nao foi descartada nesta sessao.
  const chave = JSON.stringify(atual);
  const jaDescartou = _bannerFiltroSuprimido.has(chave);
  const igualPref   = pref && _filtroIguais(atual, pref);
  const mostrar     = !_filtroVazio(atual) && !igualPref && !jaDescartou;
  banner.classList.toggle('d-none', !mostrar);
}

function salvarFiltrosPref() {
  const f = _filtrosAtuaisSnapshot();
  _salvarPref(f);
  document.getElementById('filterPrefBanner')?.classList.add('d-none');
  showSuccess('✅ Filtro salvo como padrão. Vai aplicar automaticamente na próxima vez.');
  atualizarBannerFiltroPref();
}

function descartarBannerFiltroPref() {
  const chave = JSON.stringify(_filtrosAtuaisSnapshot());
  _bannerFiltroSuprimido.add(chave);
  document.getElementById('filterPrefBanner')?.classList.add('d-none');
}

function apagarFiltrosPref() {
  if (!confirm('Remover a preferência salva? Os filtros ficarão em branco no próximo acesso.')) return;
  _limparPref();
  clearFilters();
  showSuccess('Preferência removida.');
}

async function _aplicarFiltrosPrefSeExiste() {
  const pref = _lerPref();
  if (!pref) return;

  const set = (id, val) => { const el = document.getElementById(id); if (el && val != null) el.value = String(val); };

  set('statusFilter',    pref.status || '');
  set('priorityFilter',  pref.priority || '');
  set('grupoFilter',     pref.grupo_id || '');

  // Se pref tem grupo, dispara cascade pra popular categorias + filtrar responsavel
  if (pref.grupo_id) {
    await onGrupoFilterChange();
    // onGrupoFilterChange ja chamou applyFilters — vamos aplicar valores
    // dos filhos e re-aplicar
  }

  set('categoriaFilter',   pref.categoria_id || '');
  set('responsavelFilter', pref.responsavel_id || '');

  // Popular subcategorias antes de aplicar valor da sub
  const catSel = document.getElementById('categoriaFilter');
  const subSel = document.getElementById('subcategoriaFilter');
  if (catSel && subSel && pref.categoria_id) {
    const opt = catSel.options[catSel.selectedIndex];
    const subs = (opt && opt.dataset.subs) ? JSON.parse(opt.dataset.subs || '[]') : [];
    subSel.innerHTML = '<option value="">Subcategoria</option>' +
      subs.map(s => `<option value="${s.id}">${_escHtmlP(s.nome)}</option>`).join('');
    subSel.disabled = !catSel.value || subs.length === 0;
    if (pref.subcategoria_id) subSel.value = String(pref.subcategoria_id);
  }

  // Se ha algum filtro, abre o painel pra o user ver o que ta aplicado
  if (!_filtroVazio(pref)) {
    document.getElementById('advancedFilters')?.classList.remove('d-none');
  }
  applyFilters();
}

// =========================================
// 12. RENDERIZAR TABELA E PAGINAÇÃO
// =========================================

function renderTable() {
  const body = document.getElementById("ticketsBody");
  if (!body) return;

  const pageTickets = filteredTickets.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  if (pageTickets.length === 0) {
    body.innerHTML = `
      <tr>
        <td colspan="8" class="text-center text-muted py-4">
          <i class="bi bi-inbox"></i> Nenhum ticket encontrado
        </td>
      </tr>`;
    updatePagination();
    return;
  }

  const userId = getCurrentUserId();
  const admin  = isAdmin();
  const gestor = isGestor();

  body.innerHTML = pageTickets.map(t => {
    const initial = t.userName.charAt(0).toUpperCase() || "?";
    const checked = selectedTickets.has(t.id) ? 'checked' : '';

    // ✅ Botão deletar na linha: apenas RESPONSAVEL_GRUPO pode deletar
    const podeDeletar = isResponsavelGrupo();
    const btnDeletar  = podeDeletar
      ? `<button class="btn btn-sm btn-danger" onclick="deleteTicketRow(${t.id})" title="Deletar"><i class="bi bi-trash"></i></button>`
      : '';

    return `
      <tr class="ticket-row ${checked ? 'table-active' : ''}" data-ticket-id="${t.id}">
        <td onclick="event.stopPropagation()">
          <input type="checkbox" class="row-checkbox" value="${t.id}"
                 onchange="toggleRowSelect(${t.id}, this);" ${checked}>
        </td>
        <td onclick="openTicketDetail(${t.id})">
          <strong class="text-primary">${t.id_alfanumerica || '#' + t.id}</strong>
          ${isNewTicket(t) ? '<span class="badge bg-danger ms-1" style="font-size:0.65rem;vertical-align:middle;">NOVO</span>' : ''}
        </td>
        <td onclick="openTicketDetail(${t.id})">
          <div class="d-flex align-items-center gap-2">
            <div class="avatar">${initial}</div>
            <span>${t.userName}</span>
          </div>
        </td>
        <td onclick="openTicketDetail(${t.id})">${t.title}</td>
        <td>${getPriorityBadge(t.priority)}</td>
        <td>${getStatusBadge(t.status)}</td>
        <td><small>${t.assignedName !== "Não atribuído" ? t.assignedName : '-'}</small></td>
        <td>${getSLABadge(t.sla)}</td>
        <td><small>${t.createdAt}</small></td>
        <td>
          <button class="btn btn-sm btn-info" onclick="openTicketDetail(${t.id})" title="Visualizar">
            <i class="bi bi-eye"></i>
          </button>
          ${btnDeletar}
        </td>
      </tr>`;
  }).join("");

  updatePagination();
}

function updatePagination() {
  const total      = filteredTickets.length;
  const totalPages = Math.ceil(total / itemsPerPage) || 1;
  const start      = total === 0 ? 0 : (currentPage - 1) * itemsPerPage + 1;
  const end        = Math.min(currentPage * itemsPerPage, total);

  document.getElementById("totalItems").textContent    = total;
  document.getElementById("totalPages").textContent    = totalPages;
  document.getElementById("paginationText").textContent = `${start} a ${end} de ${total}`;
  document.getElementById("currentPage").value         = currentPage;
}

function updateStatistics() {
  document.getElementById("totalTickets").textContent      = tickets.length;
  document.getElementById("openTickets").textContent       = tickets.filter(t => t.status === "open").length;
  document.getElementById("inProgressTickets").textContent = tickets.filter(t => t.status === "in-progress").length;
  document.getElementById("resolvedTickets").textContent   = tickets.filter(t => t.status === "resolved").length;
}

// =========================================
// 13. SELEÇÃO
// =========================================

function toggleSelectAll(checkbox) {
  document.querySelectorAll('.row-checkbox').forEach(cb => {
    cb.checked = checkbox.checked;
    selectedTickets[checkbox.checked ? 'add' : 'delete'](parseInt(cb.value));
  });
  updateRowSelection();
}

function toggleRowSelect(id, checkbox) {
  selectedTickets[checkbox.checked ? 'add' : 'delete'](id);
  updateRowSelection();
}

function updateRowSelection() {
  document.querySelectorAll('.ticket-row').forEach(row => {
    const cb = row.querySelector('.row-checkbox');
    row.classList.toggle('table-active', cb?.checked);
  });
}

// =========================================
// 14. AÇÕES EM LOTE
// =========================================

function editSelected() {
  if (selectedTickets.size !== 1) {
    showError("❌ Selecione apenas um ticket para editar!");
    return;
  }
  editTicketRow(Array.from(selectedTickets)[0]);
}

async function deleteSelected() {
  if (selectedTickets.size === 0) {
    showError("❌ Selecione pelo menos um ticket!");
    return;
  }
  if (!confirm(`⚠️ Tem certeza que deseja deletar ${selectedTickets.size} ticket(s)?`)) return;

  let successes = 0;
  for (const id of selectedTickets) {
    if (await deleteTicketFromAPI(id)) successes++;
  }

  selectedTickets.clear();
  document.getElementById("selectAll").checked = false;
  showSuccess(`✅ ${successes} ticket(s) deletado(s) com sucesso.`);
  await loadTickets();
}

function assignSelected() {
  if (selectedTickets.size === 0) {
    showError("❌ Selecione pelo menos um ticket!");
    return;
  }
  if (users.length === 0) {
    showError("❌ Lista de usuários não carregada. Tente novamente.");
    loadUsers();
    return;
  }

  document.getElementById("assignCountText").textContent = selectedTickets.size;
  document.getElementById("assignUser").value = "";
  new bootstrap.Modal(document.getElementById("assignModal")).show();
}

async function submitAssign(e) {
  e.preventDefault();
  const userId = document.getElementById("assignUser")?.value;
  if (!userId) {
    showError("❌ Selecione um usuário!");
    return;
  }

  const currentUserId = getCurrentUserId();
  const userName = users.find(u => u.id == userId)?.name || "Desconhecido";
  console.log(`[ASSIGN] 👤 Atribuindo ${selectedTickets.size} ticket(s) para: ${userName}...`);

  let successes = 0;
  for (const ticketId of selectedTickets) {
    // ✅ usuario_id obrigatório no PUT (validação de permissão no backend)
    const result = await apiRequest(
      'PUT',
      `/tickets/${ticketId}?usuario_id=${currentUserId}`,
      { responsavel_id: parseInt(userId) }
    );
    if (result) successes++;
  }

  showSuccess(`✅ ${successes} ticket(s) atribuído(s) para ${userName}.`);
  bootstrap.Modal.getInstance(document.getElementById("assignModal"))?.hide();
  selectedTickets.clear();
  document.getElementById("selectAll").checked = false;
  await loadTickets();
}

// =========================================
// 15. MODAL DE DETALHE DO TICKET
// =========================================

/** Busca o detalhe do ticket e preenche:
 *   - categoria / subcategoria (a partir do JOIN do backend)
 *   - campos personalizados preenchidos (campos_personalizados[])
 */
async function carregarCamposDetalhe(id) {
  const row  = document.getElementById('detailCamposCustomRow');
  const cont = document.getElementById('detailCamposCustom');
  const elCat = document.getElementById('detailCategoria');
  const elSub = document.getElementById('detailSubcategoria');
  if (elCat) elCat.textContent = '—';
  if (elSub) elSub.textContent = '—';
  if (row)  row.style.display = 'none';
  if (cont) cont.innerHTML = '';
  try {
    const res = await fetch(`${API_BASE}/tickets/${id}`);
    if (!res.ok) return;
    const data = await res.json();

    // Categoria / Subcategoria (novos)
    if (elCat) elCat.textContent = data.categoria_nome    || '—';
    if (elSub) elSub.textContent = data.subcategoria_nome || '—';

    // Campos personalizados
    const campos = data.campos_personalizados || [];
    if (!campos.length || !cont || !row) return;
    cont.innerHTML = campos.map(c => {
      let val = c.valor || '—';
      if (c.tipo === 'data' && c.valor) {
        const p = String(c.valor).slice(0, 10).split('-');
        if (p.length === 3) val = `${p[2]}/${p[1]}/${p[0]}`;
      }
      return `<div style="font-size:.85rem;margin-top:2px;">
        <strong>${escapeHtml(c.label)}:</strong> ${escapeHtml(val)}</div>`;
    }).join('');
    row.style.display = '';
  } catch (e) { /* silencia */ }
}

async function openTicketDetail(id) {
  const t = tickets.find(x => x.id === id);
  if (!t) {
    showError(`❌ Ticket #${id} não encontrado`);
    return;
  }

  // Se um chamado ANTIGO está aberto, fecha-o e move para split (à direita)
  const antigoEl = document.getElementById('chamadoAntigoModal');
  const antigoAberto = _viewingAntigoId && antigoEl?.classList.contains('show');
  const antigoParaSplit = antigoAberto ? _viewingAntigoId : null;
  if (antigoAberto) {
    // Fecha o modal antigo manualmente (sem deixar backdrop preso)
    antigoEl.classList.remove('show');
    antigoEl.style.display = 'none';
    antigoEl.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('modal-open');
    document.body.style.overflow     = '';
    document.body.style.paddingRight = '';
    document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
    const inst = bootstrap.Modal.getInstance(antigoEl);
    if (inst) { try { inst.dispose(); } catch(e){} }
    _viewingAntigoId = null;
  }

  viewingTicketId = id;
  console.log(`[DETAIL] 📖 Abrindo ticket #${id}...`);

  // Preencher campos do modal
  document.getElementById("detailTitle").textContent          = t.title;
  document.getElementById("detailId").textContent             = t.numero;
  document.getElementById("detailDescription").textContent    = t.description;
  document.getElementById("detailUserName").textContent       = t.userName;
  document.getElementById("detailEmail").textContent          = t.email;
  document.getElementById("detailStatusQuick").innerHTML      = getStatusBadge(t.status);
  document.getElementById("detailAssignedName").textContent   = t.assignedName;
  document.getElementById("detailUserNameDetail").textContent = t.userName;
  document.getElementById("detailEmailDetail").textContent    = t.email;
  document.getElementById("detailGroup").textContent          = t.groupName;
  document.getElementById("detailPriority").innerHTML         = getPriorityBadge(t.priority);
  document.getElementById("detailStatus").innerHTML           = getStatusBadge(t.status);
  document.getElementById("detailAssignedTo").textContent     = t.assignedName;
  document.getElementById("detailCreatedAt").textContent      = formatDateTime(t.createdAtFull);
  document.getElementById("detailUpdatedAt").textContent      = formatDateTime(t.updatedAtFull);
  document.getElementById("detailStatusSelect").value         = t.status;
  document.getElementById("detailAssignSelect").value         = t.assignedTo || "";

  // ✅ Campos personalizados preenchidos (busca no detalhe da API)
  carregarCamposDetalhe(id);

  // ✅ Aplica permissões de acordo com o role e se é o solicitante
  applyDetailPermissions(t);

  // ✅ Renderiza painel de SLA
  renderSLANoModal(t);

  // ✅ Passa usuario_id para filtrar comentários internos no backend
  await loadTicketComments(id);

  // Limpa estado fantasma deixado por um minimize anterior
  const _ticketModalEl = document.getElementById("ticketDetailModal");
  if (_ticketModalEl) {
    _ticketModalEl.style.display = '';
    _ticketModalEl.removeAttribute('aria-hidden');
  }
  new bootstrap.Modal(_ticketModalEl).show();

  // Se havia um chamado antigo aberto, ativa SPLIT com ele à direita
  if (antigoParaSplit) {
    setTimeout(async () => {
      _splitAntigoId = antigoParaSplit;
      _splitTicketId = null;
      await _renderSplitPanelAntigo(antigoParaSplit);
      document.body.classList.add('ticket-split-mode');
    }, 200);
  }
}

function editTicketRow(id) {
  const t = tickets.find(x => x.id === id);
  if (!t) return;

  selectedTicketId = id;
  document.getElementById("ticketModalLabel").innerHTML =
    `<i class="bi bi-pencil-square"></i> Editar Ticket #${t.numero}`;
  document.getElementById("ticketTitle").value       = t.title;
  document.getElementById("ticketDescription").value = t.description;
  document.getElementById("ticketPriority").value    = t.priority;

  new bootstrap.Modal(document.getElementById("ticketModal")).show();
}

async function deleteTicketRow(id) {
  const t = tickets.find(x => x.id === id);
  if (!t || !confirm(`⚠️ Deletar "${t.title}"?`)) return;

  if (await deleteTicketFromAPI(id)) {
    showSuccess("✅ Ticket deletado!");
    await loadTickets();
  }
}

async function deleteViewingTicket() {
  if (!viewingTicketId) return;
  await deleteTicketRow(viewingTicketId);
  bootstrap.Modal.getInstance(document.getElementById("ticketDetailModal"))?.hide();
}

async function deleteTicketFromAPI(id) {
  const userId = getCurrentUserId();
  console.log(`[TICKETS] 🗑️ Deletando #${id}...`);

  // ✅ usuario_id obrigatório no DELETE (validação de permissão no backend)
  const result = await apiRequest('DELETE', `/tickets/${id}?usuario_id=${userId}`);
  if (result) {
    console.log(`[TICKETS] ✅ #${id} deletado`);
    return true;
  }
  showError(`❌ Erro ao deletar ticket #${id}`);
  return false;
}

// =========================================
// 16. NOVO / EDITAR TICKET
// =========================================

function openNewTicketModal() {
  selectedTicketId = null;
  document.getElementById("ticketForm").reset();
  document.getElementById("ticketModalLabel").innerHTML =
    `<i class="bi bi-plus-square"></i> Novo Ticket`;
  setTicketModalErro('');  // limpa erro de uma abertura anterior

  // ✅ Preenche automaticamente com dados do usuário logado
  const user = getCurrentUser();
  document.getElementById("ticketClient").value = user.name  || user.usuario_nome  || '';
  document.getElementById("ticketEmail").value  = user.email || user.usuario_email || '';

  // ✅ Limpa categoria e subcategoria do form anterior
  resetCategoriaSubcategoria();
  _clearPendingSlot('create');

  // ✅ Popula o select de grupos e pré-seleciona o grupo do usuário
  populateGroupDropdown();

  new bootstrap.Modal(document.getElementById("ticketModal")).show();
}

async function handleFormSubmit(e) {
  e.preventDefault();

  const title       = document.getElementById("ticketTitle").value.trim();
  const description = document.getElementById("ticketDescription").value.trim();

  if (title.length < 3 || description.length < 5) {
    showError("❌ Assunto (mín 3) e Descrição (mín 5) são obrigatórios!");
    return;
  }

  const user    = getCurrentUser();
  const userId  = getCurrentUserId();

  // ✨ NÃO GERAR ID AQUI - DEIXAR PARA O BACKEND
  // O backend vai gerar a ID alfanumérica baseada no ID real do banco

  // ✅ Grupo escolhido pelo usuário no select (pode ser qualquer grupo)
  const selectedGroupId = parseInt(document.getElementById("ticketGroupName").value);
  if (!selectedGroupId) {
    showError("❌ Selecione o grupo de destino do chamado!");
    return;
  }

  const categoriaId    = parseInt(document.getElementById("ticketCategoria")?.value)    || null;
  const subcategoriaId = parseInt(document.getElementById("ticketSubcategoria")?.value) || null;

  // Coleta valores dos campos personalizados + valida os obrigatórios.
  // Campos faltantes ficam destacados em vermelho (Bootstrap is-invalid),
  // a mensagem aparece no rodapé do PRÓPRIO modal e a tela rola até o 1º.
  setTicketModalErro('');  // limpa erro anterior

  const camposValores = [];
  const camposInputs  = document.querySelectorAll('.ticket-campo-custom');
  let primeiroFaltante = null;
  for (const inp of camposInputs) {
    inp.classList.remove('is-invalid');
    const valor = (inp.value || '').trim();
    if (inp.dataset.obrigatorio === '1' && !valor) {
      inp.classList.add('is-invalid');
      if (!primeiroFaltante) primeiroFaltante = inp;
    } else if (valor) {
      camposValores.push({ campo_id: parseInt(inp.dataset.campoId), valor });
    }
  }
  if (primeiroFaltante) {
    setTicketModalErro('Preencha os campos obrigatórios destacados em vermelho.');
    primeiroFaltante.scrollIntoView({ block: 'center', behavior: 'smooth' });
    primeiroFaltante.focus();
    return;
  }

  const payload = {
    assunto:           title,
    descricao_inicial: description,
    prioridade_id:     mapPriorityToApi(document.getElementById("ticketPriority").value),
    group_id:          selectedGroupId,
    solicitante_id:    user.id || user.usuario_id,
    origem:            'web',
    categoria_id:      categoriaId,
    subcategoria_id:   subcategoriaId,
    campos_valores:    camposValores
  };

  let result;
  if (selectedTicketId) {
    console.log(`[TICKET] ✏️ Editando #${selectedTicketId}...`);
    result = await apiRequest(
      'PUT',
      `/tickets/${selectedTicketId}?usuario_id=${userId}`,
      payload
    );
  } else {
    console.log("[TICKET] ➕ Criando novo ticket...");
    result = await apiRequest('POST', '/tickets', payload);
  }

  if (result) {
    // Faz upload das imagens pendentes (somente na criação)
    const novoTicketId = (!selectedTicketId && result && result.id) ? result.id : null;
    if (novoTicketId) {
      await _uploadPendingAttachments('create', novoTicketId, null);
    }
    showSuccess(`✅ Ticket ${selectedTicketId ? 'atualizado' : 'criado'} com sucesso!`);
    bootstrap.Modal.getInstance(document.getElementById("ticketModal"))?.hide();
    selectedTicketId = null;
    await loadTickets();
  } else {
    showError(`❌ Erro ao ${selectedTicketId ? 'atualizar' : 'criar'} o ticket.`);
  }
}

// =========================================
// 17. COMENTÁRIOS / INTERAÇÕES
// =========================================

async function loadTicketComments(ticketId) {
  console.log(`[COMENTARIOS] 📥 Carregando para ticket #${ticketId}...`);

  const userId = getCurrentUserId();
  const admin = isAdmin();  // ✅ Verificar se é admin

  // Carrega comentários e anexos em paralelo.
  // Para anexos usamos fetch direto (sem showError) — assim, se a tabela
  // ainda não existir ou houver falha de rede, a UI segue funcionando.
  const fetchAttachments = async () => {
    try {
      const res = await fetch(`${API_BASE}/tickets/${ticketId}/attachments`);
      if (!res.ok) return [];
      return await res.json();
    } catch {
      return [];
    }
  };
  const [data, attachments] = await Promise.all([
    apiRequest('GET', `/ticket-interacoes/${ticketId}?usuario_id=${userId}`),
    fetchAttachments(),
  ]);

  // Agrupa anexos por interacao_id (null = anexo da descrição inicial)
  const anexosPorInteracao = {};
  const anexosDescricao = [];
  (attachments || []).forEach(a => {
    if (a.interacao_id) {
      (anexosPorInteracao[a.interacao_id] ||= []).push(a);
    } else {
      anexosDescricao.push(a);
    }
  });

  // Anexos da descrição inicial aparecem logo abaixo da descrição
  const descAttachBox = document.getElementById('detailDescriptionAttachments');
  if (descAttachBox) {
    descAttachBox.innerHTML = anexosDescricao.length ? _renderAttachGallery(anexosDescricao) : '';
  }

  const container = document.getElementById("detailCommentsList");
  if (!container) return;

  if (!data || data.length === 0) {
    container.innerHTML =
      '<p class="text-muted text-center py-4">Nenhum comentário ainda</p>';
    return;
  }

  // ✅ FILTRAR: USER só vê comentários públicos (publico=1)
  // ✅ ADMIN vê tudo (público e interno)
  const comentariosFiltrados = admin ? data : data.filter(c => c.publico === 1);

  if (comentariosFiltrados.length === 0) {
    container.innerHTML =
      '<p class="text-muted text-center py-4">Nenhum comentário disponível</p>';
    return;
  }

  container.innerHTML = comentariosFiltrados.map(c => {
    const anexos = anexosPorInteracao[c.id] || [];
    return `
    <div class="comment-item p-3 mb-2 rounded bg-light">
      <div class="d-flex justify-content-between align-items-center mb-2">
        <span class="fw-bold">${c.usuario_nome || 'Desconhecido'}</span>
        <div>
          <span class="badge ${c.publico ? 'bg-success' : 'bg-warning text-dark'} me-2">
            ${c.publico ? 'RESPOSTA' : 'INTERNO'}
          </span>
          <span class="text-muted small">${formatDateTime(c.created_at)}</span>
        </div>
      </div>
      <p class="mb-0">${c.mensagem || '[Sem conteúdo]'}</p>
      ${anexos.length ? _renderAttachGallery(anexos) : ''}
    </div>`;
  }).join("");
}

/** HTML de galeria de thumbs para anexos já gravados no histórico.
 *  - Imagens: thumbnail clicável que abre viewer
 *  - Docs/PDF: card com ícone + nome, click abre em nova aba pra download/visualização
 */
function _renderAttachGallery(anexos) {
  if (!anexos || !anexos.length) return '';
  const base = API_BASE; // já inclui /api
  return `
    <div class="comment-attachments">
      ${anexos.map(a => {
        const url = `${base}/tickets/attachments/${a.id}`;
        const safeName = (a.filename || 'arquivo').replace(/"/g, '&quot;').replace(/'/g, "\\'");
        const sizeKB = ((a.size_bytes || 0) / 1024).toFixed(0);
        const isImg = (a.mime_type || '').startsWith('image/');
        if (isImg) {
          return `
            <a href="${url}" onclick="event.preventDefault(); openImageViewer('${url}', '${safeName}');"
               title="${safeName} (${sizeKB} KB)">
              <img src="${url}" alt="${safeName}">
            </a>`;
        }
        // Documento (PDF/Word/Excel/etc): card baixavel (classe CSS
        // attach-doc-link em tickets.css, sobrescreve o 80x80 padrao)
        const icon = _iconForMime(a.mime_type);
        const color = _colorForMime(a.mime_type);
        return `
          <a href="${url}" target="_blank" rel="noopener" class="attach-doc-link"
             title="Abrir/baixar ${safeName} (${sizeKB} KB)">
            <i class="bi ${icon}" style="font-size:20px;color:${color};flex-shrink:0"></i>
            <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${safeName}</span>
            <span style="color:#6B7280;font-size:11px;flex-shrink:0">${sizeKB} KB</span>
          </a>`;
      }).join('')}
    </div>
  `;
}

/** Abre o modal flutuante exibindo a imagem em tamanho ampliado. */
function openImageViewer(url, filename) {
  const img    = document.getElementById('imageViewerImg');
  const label  = document.getElementById('imageViewerFilename');
  const openA  = document.getElementById('imageViewerOpen');
  if (img)   img.src = url;
  if (label) label.textContent = filename || 'imagem';
  if (openA) openA.href = url;
  new bootstrap.Modal(document.getElementById('imageViewerModal')).show();
}

async function submitComment(form, isPublic) {
  const textEl = form.querySelector('textarea');
  const text   = textEl?.value?.trim();

  if (!text || text.length < 3) {
    showError("❌ Mensagem muito curta!");
    return;
  }

  const user    = getCurrentUser();
  const payload = {
    ticket_id:  viewingTicketId,
    usuario_id: user.id || user.usuario_id,
    mensagem:   text,
    tipo:       isPublic ? 'resposta' : 'interno',
    publico:    isPublic ? 1 : 0
  };

  const result = await apiRequest('POST', '/ticket-interacoes', payload);
  if (result) {
    // Upload de anexos vinculados a esta interação
    const slot = isPublic ? 'reply' : 'internal';
    const interacaoId = result && result.id ? result.id : null;
    if (interacaoId) {
      await _uploadPendingAttachments(slot, viewingTicketId, interacaoId);
    }
    showSuccess(`✅ ${isPublic ? 'Resposta enviada' : 'Comentário salvo'}!`);
    form.reset();
    _clearPendingSlot(slot);
    await loadTicketComments(viewingTicketId);
  }
}

function submitDetailReply(e)    { e.preventDefault(); submitComment(e.target, true);  }
function submitDetailInternal(e) { e.preventDefault(); submitComment(e.target, false); }

// =========================================
// 18. PAGINAÇÃO
// =========================================

function changeItemsPerPage(value) {
  itemsPerPage = parseInt(value);
  currentPage  = 1;
  renderTable();
}

function previousPage() {
  if (currentPage > 1) { currentPage--; renderTable(); }
}

function nextPage() {
  if (currentPage < Math.ceil(filteredTickets.length / itemsPerPage)) {
    currentPage++;
    renderTable();
  }
}

function goToPage(pageNum) {
  const num        = parseInt(pageNum);
  const totalPages = Math.ceil(filteredTickets.length / itemsPerPage) || 1;
  if (num >= 1 && num <= totalPages) {
    currentPage = num;
    renderTable();
  }
}

// =========================================
// 19. BADGES
// =========================================

function getPriorityBadge(p) {
  const map     = { 'low': "Baixa", 'medium': "Média", 'high': "Alta", 'urgent': "Urgente" };
  const classes = { 'low': "bg-info", 'medium': "bg-warning", 'high': "bg-danger", 'urgent': "bg-danger" };
  return `<span class="badge ${classes[p] || 'bg-secondary'}">${map[p] || p}</span>`;
}

function getStatusBadge(s) {
  const map     = { 'open': "Aberto", 'in-progress': "Andamento", 'resolved': "Resolvido", 'closed': "Fechado" };
  const classes = { 'open': "bg-warning text-dark", 'in-progress': "bg-primary", 'resolved': "bg-success", 'closed': "bg-secondary" };
  return `<span class="badge ${classes[s] || 'bg-secondary'}">${map[s] || s}</span>`;
}

function getSLABadge(sla) {
  if (!sla || !sla.calculo) return '<span class="text-muted small">—</span>';
  const c = sla.calculo;
  const colorMap = { verde: '#198754', amarelo: '#ffc107', vermelho: '#dc3545', cinza: '#6c757d' };
  const textMap  = { verde: '#fff',    amarelo: '#000',    vermelho: '#fff',    cinza: '#fff'    };
  const bg   = colorMap[c.cor] || '#6c757d';
  const text = textMap[c.cor]  || '#fff';
  const icon = c.cor === 'vermelho' ? 'bi-alarm-fill'
             : c.cor === 'amarelo'  ? 'bi-clock-history'
             : c.cor === 'cinza'    ? 'bi-pause-circle'
             : 'bi-check-circle';
  return `<span class="badge" style="background:${bg};color:${text};white-space:nowrap;" title="${c.label}">
    <i class="bi ${icon}"></i> ${c.label}
  </span>`;
}

// =========================================
// 20. ABAS DO MODAL DE DETALHE
// =========================================

function switchTab(event, tab) {
  event.preventDefault();
  document.querySelectorAll('.ticket-detail-tab, .ticket-detail-content')
    .forEach(el => el.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById(`tab-${tab}`)?.classList.add('active');
}

function switchReplyMode(event, mode) {
  event.preventDefault();
  document.querySelectorAll('.reply-menu-tab, .reply-mode')
    .forEach(el => el.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById(`reply-${mode}`)?.classList.add('active');
}

/** Mostra/oculta o histórico de comentários do modal de detalhe. */
function toggleCommentsSection() {
  const section = document.querySelector('#ticketDetailModal .comments-section');
  if (!section) return;
  section.classList.toggle('is-collapsed');
}

// =========================================
// DOCK DE TICKETS MINIMIZADOS + SPLIT VIEW
// =========================================

/** Tickets minimizados em memória — { [id]: {id, numero, title, status} } */
const _minimizedTickets = {};
/** Chamados antigos minimizados — { [trackid]: {trackid, assunto, status} } */
const _minimizedAntigos = {};
let   _splitTicketId    = null;   // ID do ticket NORMAL no painel da direita
let   _splitAntigoId    = null;   // trackid do CHAMADO ANTIGO no painel da direita
let   _viewingAntigoId  = null;   // trackid do chamado antigo atualmente aberto no modal

/** Limite de chips no dock — evita poluir a barra do rodapé. */
const DOCK_MAX = 6;
function _dockCount() {
  return Object.keys(_minimizedTickets).length + Object.keys(_minimizedAntigos).length;
}
function _dockHasRoom(idAlvo) {
  // Permite minimizar se já existe (caso de regravar) OU se há espaço
  if (_minimizedTickets[idAlvo] != null || _minimizedAntigos[idAlvo] != null) return true;
  if (_dockCount() < DOCK_MAX) return true;
  showError(`⚠️ Limite de ${DOCK_MAX} chamados minimizados atingido. Feche um chip do dock antes de minimizar outro.`);
  return false;
}

/** Minimiza o modal de detalhe atual e cria um chip no dock. */
function minimizeTicketModal() {
  const id = viewingTicketId;
  if (!id) return;
  const t = tickets.find(x => x.id === id);
  if (!t) return;
  if (!_dockHasRoom(id)) return;

  _minimizedTickets[id] = { id, numero: t.numero, title: t.title, status: t.status };
  _renderTicketDock();

  // Esconde manualmente — Modal.hide() do Bootstrap deixa o backdrop preso
  // quando o modal foi aberto com data-bs-backdrop="static".
  const modalEl = document.getElementById('ticketDetailModal');
  if (modalEl) {
    modalEl.classList.remove('show');
    modalEl.style.display = 'none';
    modalEl.setAttribute('aria-hidden', 'true');
  }
  document.body.classList.remove('modal-open');
  document.body.style.overflow      = '';
  document.body.style.paddingRight  = '';
  document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());

  // Descarta a instância Bootstrap — `openTicketDetail` cria uma nova ao restaurar.
  const inst = bootstrap.Modal.getInstance(modalEl);
  if (inst) { try { inst.dispose(); } catch (e) { /* ignore */ } }
}

/** Re-renderiza o dock combinando tickets normais e chamados antigos. */
function _renderTicketDock() {
  const dock = document.getElementById('ticketDock');
  if (!dock) return;
  const tickets   = Object.values(_minimizedTickets);
  const antigos   = Object.values(_minimizedAntigos);
  if (!tickets.length && !antigos.length) { dock.innerHTML = ''; return; }

  const chipTicket = (t) => `
    <div class="ticket-dock-item" onclick="handleDockClick(${t.id})"
         title="Clique para abrir (ou abrir lado a lado, se já houver outro)">
      <i class="bi bi-ticket-detailed"></i>
      <span class="dock-title">${t.numero} — ${(t.title || '').replace(/</g,'&lt;')}</span>
      <button class="dock-close" title="Descartar"
              onclick="event.stopPropagation(); closeFromDock(${t.id})">
        <i class="bi bi-x-lg"></i>
      </button>
    </div>`;
  const chipAntigo = (a) => {
    const tid = a.trackid.replace(/'/g, "\\'");
    return `
    <div class="ticket-dock-item ticket-dock-item--antigo"
         onclick="handleDockClickAntigo('${tid}')"
         title="Chamado antigo — clique para abrir ou dividir tela com um ticket">
      <i class="bi bi-archive"></i>
      <span class="dock-title">${a.trackid} — ${(a.assunto || '').replace(/</g,'&lt;')}</span>
      <button class="dock-close" title="Descartar"
              onclick="event.stopPropagation(); closeAntigoFromDock('${tid}')">
        <i class="bi bi-x-lg"></i>
      </button>
    </div>`;
  };

  dock.innerHTML =
    tickets.map(chipTicket).join('') +
    antigos.map(chipAntigo).join('');
}

/**
 * Clique no chip de TICKET NORMAL:
 *  - Modal aberto com outro ticket → split
 *  - Caso contrário → restaura
 */
function handleDockClick(id) {
  const modalEl = document.getElementById('ticketDetailModal');
  const modalVisible = modalEl?.classList.contains('show');
  if (modalVisible && viewingTicketId && viewingTicketId !== id) {
    openInSplit(id);
  } else {
    restoreFromDock(id);
  }
}

/**
 * Clique no chip de CHAMADO ANTIGO:
 *  - Modal de ticket NORMAL aberto → abre o antigo em SPLIT (à direita)
 *  - Caso contrário → restaura no modal de chamado antigo
 */
function handleDockClickAntigo(trackid) {
  const modalEl = document.getElementById('ticketDetailModal');
  const modalVisible = modalEl?.classList.contains('show');
  if (modalVisible && viewingTicketId) {
    openAntigoInSplit(trackid);
  } else {
    restoreAntigoFromDock(trackid);
  }
}

/** Restaura um ticket do dock (volta a abrir o modal). */
function restoreFromDock(id) {
  delete _minimizedTickets[id];
  _renderTicketDock();
  openTicketDetail(id);
}

/** Remove o chip do dock sem reabrir. */
function closeFromDock(id) {
  delete _minimizedTickets[id];
  _renderTicketDock();
}

/** Ativa split view: mantém o modal atual à esquerda, mostra outro ticket à direita. */
async function openInSplit(id) {
  const modalEl = document.getElementById('ticketDetailModal');
  const modalVisible = modalEl?.classList.contains('show');

  // Sem outro ticket aberto no modal → split não faz sentido, só restaura
  if (!modalVisible || !viewingTicketId || id === viewingTicketId) {
    restoreFromDock(id);
    return;
  }

  delete _minimizedTickets[id];
  _renderTicketDock();
  _splitTicketId = id;
  await _renderSplitPanel(id);
  document.body.classList.add('ticket-split-mode');
  console.log(`[SPLIT] Ativo: esquerda=#${viewingTicketId} | direita=#${id}`);
}

// Cleanup defensivo global de modais Bootstrap:
// - Limpa split se fechou o ticketDetailModal
// - Remove .modal-backdrop preso quando ja nao ha nenhum modal aberto
//   (bug conhecido do Bootstrap 5 com data-bs-backdrop="static": as
//    vezes o backdrop permanece no DOM apos o hide, deixando a pagina
//    escura e travada). Ver bug reportado 2026-08-14.
document.addEventListener('DOMContentLoaded', () => {
  document.addEventListener('hidden.bs.modal', (ev) => {
    // Split: so ativa quando o modal principal fecha
    if (ev.target?.id === 'ticketDetailModal') {
      if (document.body.classList.contains('ticket-split-mode')) {
        document.body.classList.remove('ticket-split-mode');
        _splitTicketId = null;
      }
      viewingTicketId = null;
    }
    // Cleanup de backdrop residual (independente de qual modal fechou)
    setTimeout(() => {
      if (!document.querySelector('.modal.show')) {
        document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
        document.body.classList.remove('modal-open');
        document.body.style.overflow      = '';
        document.body.style.paddingRight  = '';
      }
    }, 50);
  }, true);
});

/** Renderiza o conteúdo do painel direito (somente leitura). */
async function _renderSplitPanel(id) {
  const t = tickets.find(x => x.id === id);
  if (!t) return;

  // Garante visual de TICKET NOVO (amarelo + ícone de ticket)
  const sidePanel = document.getElementById('ticketDetailModal2');
  if (sidePanel) sidePanel.classList.remove('is-antigo');
  const icon = document.getElementById('iconDetailHeader2');
  if (icon) icon.className = 'bi bi-ticket-detailed';

  document.getElementById('detailTitle2').textContent      = t.title;
  document.getElementById('detailId2').textContent         = ' · ' + t.numero;
  document.getElementById('detail2UserName').textContent   = t.userName;
  document.getElementById('detail2Status').innerHTML       = getStatusBadge(t.status);
  document.getElementById('detail2AssignedName').textContent = t.assignedName;
  document.getElementById('detail2Description').textContent = t.description;

  // Comentários
  try {
    const userId = getCurrentUserId();
    const data = await apiRequest('GET', `/ticket-interacoes/${id}?usuario_id=${userId}`);
    const admin = isAdmin();
    const list = (data || []).filter(c => admin || c.publico === 1);
    const box  = document.getElementById('detail2CommentsList');
    if (!list.length) {
      box.innerHTML = '<p class="text-muted text-center py-3">Sem comentários</p>';
    } else {
      box.innerHTML = list.map(c => `
        <div class="comment-item p-2 mb-2 rounded bg-light">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <strong>${c.usuario_nome || '—'}</strong>
            <small class="text-muted">${formatDateTime(c.created_at)}</small>
          </div>
          <div style="white-space:pre-wrap;">${(c.mensagem||'').replace(/</g,'&lt;')}</div>
        </div>
      `).join('');
    }
  } catch (e) { console.warn('[SPLIT] erro:', e); }
}

/** Fecha o split view (volta o modal principal ao tamanho normal). */
function closeSplitView() {
  document.body.classList.remove('ticket-split-mode');
  _splitTicketId = null;
  _splitAntigoId = null;
}

/** Minimiza o painel direito do split (ticket OU chamado antigo) para o dock. */
function minimizeSplitPanel() {
  if (_splitTicketId) {
    if (!_dockHasRoom(_splitTicketId)) return;
    const t = tickets.find(x => x.id === _splitTicketId);
    if (t) {
      _minimizedTickets[t.id] = { id: t.id, numero: t.numero, title: t.title, status: t.status };
    }
  } else if (_splitAntigoId) {
    if (!_dockHasRoom(_splitAntigoId)) return;
    const titulo = document.getElementById('detailTitle2')?.textContent || _splitAntigoId;
    _minimizedAntigos[_splitAntigoId] = { trackid: _splitAntigoId, assunto: titulo };
  }
  _splitTicketId = null;
  _splitAntigoId = null;
  document.body.classList.remove('ticket-split-mode');
  _renderTicketDock();
}

/** Troca os 2 itens entre esquerda e direita do split (qualquer combinação). */
async function swapSplitTickets() {
  // Caso A — esquerda TICKET, direita TICKET
  if (viewingTicketId && _splitTicketId) {
    const left  = viewingTicketId;
    const right = _splitTicketId;
    await openTicketDetail(right);
    _splitTicketId = left;
    await _renderSplitPanel(left);
    return;
  }
  // Caso B — esquerda TICKET, direita ANTIGO  → swap inverte (esquerda vira antigo)
  if (viewingTicketId && _splitAntigoId) {
    const oldTicket = viewingTicketId;
    const oldAntigo = _splitAntigoId;
    // Fecha modal de ticket, abre modal de antigo (que vira esquerda) e coloca ticket à direita
    closeSplitView();
    bootstrap.Modal.getInstance(document.getElementById('ticketDetailModal'))?.hide();
    await abrirChamadoAntigo(oldAntigo);
    // Agora simulamos: modal antigo aberto → adiciona ticket no painel direito
    _splitTicketId = oldTicket;
    _splitAntigoId = null;
    await _renderSplitPanel(oldTicket);
    document.body.classList.add('ticket-split-mode');
    return;
  }
  // Caso C — esquerda ANTIGO, direita ANTIGO
  if (_viewingAntigoId && _splitAntigoId) {
    const oldLeft  = _viewingAntigoId;
    const oldRight = _splitAntigoId;
    // Repopula o modal principal de antigo com oldRight
    const r = await fetch(`${API_BASE}/chamados-antigos/${encodeURIComponent(oldRight)}`);
    if (r.ok) {
      const c = await r.json();
      const setText = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v || '—'; };
      const fmt = (d) => d ? new Date(d).toLocaleString('pt-BR') : '—';
      setText('antigoTitulo',         c.assunto);
      setText('antigoTrackid',        ' · ' + c.trackid);
      setText('antigoSolicitante',    c.solicitante);
      setText('antigoEmail',          c.email);
      setText('antigoStatus',         c.nome_status);
      setText('antigoCategoria',      c.categoria);
      setText('antigoAtribuido',      c.atribuido_a);
      setText('antigoAberto',         fmt(c.aberto_em));
      setText('antigoPrimeiraResp',   fmt(c.primeira_resp));
      setText('antigoFechado',        fmt(c.fechado_em));
      setText('antigoMensagem',       c.mensagem);
      setText('antigoRespondidoPor',  c.respondido_por);
      setText('antigoDhResposta',     fmt(c.dh_resposta));
      setText('antigoResposta',       c.resposta);
      _viewingAntigoId = oldRight;
    }
    _splitAntigoId = oldLeft;
    await _renderSplitPanelAntigo(oldLeft);
    return;
  }
  // Caso D — esquerda ANTIGO, direita TICKET (raro mas válido)
  if (_viewingAntigoId && _splitTicketId) {
    const oldAntigo = _viewingAntigoId;
    const oldTicket = _splitTicketId;
    closeSplitView();
    bootstrap.Modal.getInstance(document.getElementById('chamadoAntigoModal'))?.hide();
    await openTicketDetail(oldTicket);
    _splitAntigoId = oldAntigo;
    _splitTicketId = null;
    await _renderSplitPanelAntigo(oldAntigo);
    document.body.classList.add('ticket-split-mode');
    return;
  }
}

/** Expande / recolhe o modal de detalhe do ticket (modal-xl ↔ tela cheia). */
function toggleDetailFullscreen() {
  const dialog = document.getElementById('ticketDetailDialog');
  const icon   = document.getElementById('iconDetailFullscreen');
  const modalEl = document.getElementById('ticketDetailModal');
  if (!dialog) return;
  const expandido = dialog.classList.toggle('modal-fullscreen');

  // Em fullscreen, limpa dimensões custom de resize e tira o padding-right
  // que o Bootstrap injeta inline para compensar a scrollbar do body.
  const content = dialog.querySelector('.modal-content');
  if (expandido) {
    if (content) {
      content.dataset._savedW = content.style.width  || '';
      content.dataset._savedH = content.style.height || '';
      content.style.width = ''; content.style.height = '';
    }
    dialog.dataset._savedW    = dialog.style.width      || '';
    dialog.dataset._savedML   = dialog.style.marginLeft || '';
    dialog.dataset._savedMT   = dialog.style.marginTop  || '';
    dialog.style.width = ''; dialog.style.marginLeft = ''; dialog.style.marginTop = '';
    if (modalEl) modalEl.style.paddingRight = '0';
    dialog.classList.remove('modal-xl', 'modal-dialog-centered');
    if (icon) icon.className = 'bi bi-arrows-angle-contract';
  } else {
    if (content) {
      content.style.width  = content.dataset._savedW || '';
      content.style.height = content.dataset._savedH || '';
    }
    dialog.style.width      = dialog.dataset._savedW  || '';
    dialog.style.marginLeft = dialog.dataset._savedML || '';
    dialog.style.marginTop  = dialog.dataset._savedMT || '';
    if (modalEl) modalEl.style.paddingRight = '';
    dialog.classList.add('modal-xl', 'modal-dialog-centered');
    if (icon) icon.className = 'bi bi-arrows-fullscreen';
  }
}

/**
 * Anexa 8 handles invisíveis nas bordas/cantos do .modal-dialog para
 * permitir redimensionar arrastando — comportamento de janela Windows.
 * Idempotente.
 */
function _attachDetailResizeHandles() {
  const dialog = document.getElementById('ticketDetailDialog');
  if (!dialog) return;
  if (dialog.dataset.resizeReady === '1') return;
  dialog.dataset.resizeReady = '1';

  // .modal-dialog tem pointer-events:none por padrão; precisa de position:relative
  // para os handles (absolute) ficarem posicionados em relação a ele.
  dialog.style.position = 'relative';

  const dirs = ['n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw'];
  dirs.forEach(dir => {
    const h = document.createElement('div');
    h.className = `resize-handle rh-${dir}`;
    h.dataset.dir = dir;
    h.addEventListener('mousedown',  e => _startResize(e, dialog, dir));
    h.addEventListener('touchstart', e => _startResize(e.touches[0], dialog, dir, e), {passive:false});
    dialog.appendChild(h);
  });
}

function _startResize(evt, dialog, dir, originalEvent) {
  if (originalEvent && originalEvent.preventDefault) originalEvent.preventDefault();
  if (evt.preventDefault) evt.preventDefault?.();

  // Em modo fullscreen ou split, não permitir resize
  if (dialog.classList.contains('modal-fullscreen')) return;
  if (document.body.classList.contains('ticket-split-mode')) return;

  const content = dialog.querySelector('.modal-content');
  const rect = content.getBoundingClientRect();
  const startX = evt.clientX;
  const startY = evt.clientY;
  const startW = rect.width;
  const startH = rect.height;

  const MIN_W = 480;
  const MIN_H = 320;
  const MAX_W = window.innerWidth  - 24;
  const MAX_H = window.innerHeight - 24;

  // Trava as dimensões atuais
  dialog.style.width  = startW + 'px';
  dialog.style.maxWidth  = 'none';
  content.style.width  = '100%';
  content.style.height = startH + 'px';
  content.style.maxHeight = 'none';

  const startMarginL = parseFloat(getComputedStyle(dialog).marginLeft) || 0;
  const startMarginT = parseFloat(getComputedStyle(dialog).marginTop)  || 0;

  const onMove = (e) => {
    const ev = e.touches ? e.touches[0] : e;
    const dx = ev.clientX - startX;
    const dy = ev.clientY - startY;
    let newW = startW, newH = startH, newML = startMarginL, newMT = startMarginT;

    if (dir.includes('e')) newW = Math.min(MAX_W, Math.max(MIN_W, startW + dx));
    if (dir.includes('w')) {
      newW  = Math.min(MAX_W, Math.max(MIN_W, startW - dx));
      newML = startMarginL + (startW - newW);
    }
    if (dir.includes('s')) newH = Math.min(MAX_H, Math.max(MIN_H, startH + dy));
    if (dir.includes('n')) {
      newH  = Math.min(MAX_H, Math.max(MIN_H, startH - dy));
      newMT = startMarginT + (startH - newH);
    }
    dialog.style.width      = newW + 'px';
    content.style.height    = newH + 'px';
    dialog.style.marginLeft = newML + 'px';
    dialog.style.marginTop  = newMT + 'px';
  };

  const onUp = () => {
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup',   onUp);
    document.removeEventListener('touchmove', onMove);
    document.removeEventListener('touchend',  onUp);
    document.body.style.userSelect = '';
  };

  document.body.style.userSelect = 'none';
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup',   onUp);
  document.addEventListener('touchmove', onMove, {passive:false});
  document.addEventListener('touchend',  onUp);
}

// Anexa os handles assim que o modal de detalhe abre.
document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('ticketDetailModal');
  if (!modal) return;
  modal.addEventListener('shown.bs.modal', _attachDetailResizeHandles);
});

// =========================================
// 21. AÇÕES DO MODAL DE DETALHE
// =========================================

// Mantido como alias para compatibilidade de chamadas antigas
async function resolveTicket() { await finalizarTicket(); }

/** Abre o modal de finalização para o atendente preencher a solução. */
function finalizarTicket() {
  if (!viewingTicketId) return;
  const ta  = document.getElementById('finalizarSolucao');
  const err = document.getElementById('finalizarError');
  if (ta)  ta.value = '';
  if (err) err.classList.add('d-none');
  new bootstrap.Modal(document.getElementById('finalizarModal')).show();
}

/** Envia POST /finalizar com a solução preenchida no modal. */
async function submitFinalizarTicket() {
  if (!viewingTicketId) return;
  const userId  = getCurrentUserId();
  const solucao = document.getElementById('finalizarSolucao')?.value?.trim() || '';
  const errorEl = document.getElementById('finalizarError');

  if (solucao.length < 5) {
    if (errorEl) {
      errorEl.textContent = 'Descreva a solução com pelo menos 5 caracteres.';
      errorEl.classList.remove('d-none');
    }
    return;
  }

  try {
    const token = localStorage.getItem('cpe_token') || '';
    const res = await fetch(`${API_BASE}/tickets/${viewingTicketId}/finalizar`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body:    JSON.stringify({ usuario_id: userId, solucao })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      if (errorEl) {
        errorEl.textContent = err.detail || 'Erro ao finalizar o chamado.';
        errorEl.classList.remove('d-none');
      }
      return;
    }

    bootstrap.Modal.getInstance(document.getElementById('finalizarModal'))?.hide();
    bootstrap.Modal.getInstance(document.getElementById('ticketDetailModal'))?.hide();
    showSuccess('✅ Chamado finalizado! O solicitante foi notificado por e-mail.');
    await loadTickets();

  } catch (e) {
    console.error('[FINALIZAR] Erro:', e);
    if (errorEl) {
      errorEl.textContent = 'Erro de conexão ao finalizar o chamado.';
      errorEl.classList.remove('d-none');
    }
  }
}

// ── Reabrir chamado ──────────────────────────────
function reabrirChamado() {
  if (!viewingTicketId) return;
  document.getElementById('reabrirJustificativa').value = '';
  document.getElementById('reabrirError').classList.add('d-none');
  new bootstrap.Modal(document.getElementById('reabrirModal')).show();
}

async function submitReabrir() {
  if (!viewingTicketId) return;
  const userId   = getCurrentUserId();
  const justText = document.getElementById('reabrirJustificativa').value.trim();
  const errorEl  = document.getElementById('reabrirError');

  if (justText.length < 5) {
    errorEl.textContent = 'Informe uma justificativa com pelo menos 5 caracteres.';
    errorEl.classList.remove('d-none');
    return;
  }

  try {
    const token = localStorage.getItem('cpe_token') || '';
    const res = await fetch(`${API_BASE}/tickets/${viewingTicketId}/reabrir`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body:    JSON.stringify({ usuario_id: userId, justificativa: justText })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      errorEl.textContent = err.detail || 'Erro ao reabrir o chamado.';
      errorEl.classList.remove('d-none');
      return;
    }

    bootstrap.Modal.getInstance(document.getElementById('reabrirModal'))?.hide();
    bootstrap.Modal.getInstance(document.getElementById('ticketDetailModal'))?.hide();
    showSuccess('🔄 Chamado reaberto com sucesso!');
    await loadTickets();

  } catch (e) {
    console.error('[REABRIR] Erro:', e);
    errorEl.textContent = 'Erro de conexão ao reabrir o chamado.';
    errorEl.classList.remove('d-none');
  }
}

async function updateTicketStatus() {
  const newStatus = document.getElementById("detailStatusSelect")?.value;
  if (!newStatus) { showError("❌ Selecione um status"); return; }

  const userId = getCurrentUserId();

  // ✅ usuario_id obrigatório no PUT
  const result = await apiRequest(
    'PUT',
    `/tickets/${viewingTicketId}?usuario_id=${userId}`,
    { status_id: mapStatusToApi(newStatus) }
  );

  if (result) {
    showSuccess("✅ Status atualizado com sucesso!");
    await loadTickets();

    const updatedTicket = tickets.find(t => t.id === viewingTicketId);
    if (updatedTicket) {
      document.getElementById("detailStatusQuick").innerHTML = getStatusBadge(updatedTicket.status);
      document.getElementById("detailStatus").innerHTML      = getStatusBadge(updatedTicket.status);
    }
  } else {
    const originalTicket = tickets.find(t => t.id === viewingTicketId);
    if (originalTicket) {
      document.getElementById("detailStatusSelect").value = originalTicket.status;
    }
  }
}

async function updateTicketAssign() {
  const responsavelId = document.getElementById("detailAssignSelect")?.value;
  const userId        = getCurrentUserId();

  // ✅ usuario_id obrigatório no PUT
  // responsavel_id null quando vazio é tratado corretamente pelo Pydantic (Optional)
  const result = await apiRequest(
    'PUT',
    `/tickets/${viewingTicketId}?usuario_id=${userId}`,
    { responsavel_id: responsavelId ? parseInt(responsavelId) : null }
  );

  if (result) {
    showSuccess("✅ Atribuição atualizada com sucesso!");
    await loadTickets();

    const updatedTicket = tickets.find(t => t.id === viewingTicketId);
    if (updatedTicket) {
      document.getElementById("detailAssignedName").textContent = updatedTicket.assignedName;
      document.getElementById("detailAssignedTo").textContent   = updatedTicket.assignedName;
    }
  } else {
    const originalTicket = tickets.find(t => t.id === viewingTicketId);
    if (originalTicket) {
      document.getElementById("detailAssignSelect").value = originalTicket.assignedTo || "";
    }
  }
}

// =========================================
// 22. ASSUMIR / DEVOLVER TICKET
// =========================================

async function assumirTicket() {
  if (!viewingTicketId) return;
  const userId = getCurrentUserId();

  try {
    const token = localStorage.getItem('cpe_token') || '';
    const res = await fetch(`${API_BASE}/tickets/${viewingTicketId}/assumir`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ usuario_id: userId })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showError(err.detail || 'Erro ao assumir o chamado.');
      return;
    }

    showSuccess('Chamado assumido! Você agora é o responsável.');
    bootstrap.Modal.getInstance(document.getElementById('ticketDetailModal'))?.hide();
    await loadTickets();

  } catch (e) {
    console.error('[ASSUMIR] Erro:', e);
    showError('Erro de conexão ao assumir o chamado.');
  }
}

function devolverTicket() {
  if (!viewingTicketId) return;
  document.getElementById('devolverMotivo').value = '';
  new bootstrap.Modal(document.getElementById('devolverModal')).show();
}

async function submitDevolver() {
  if (!viewingTicketId) return;
  const userId = getCurrentUserId();
  const motivo = document.getElementById('devolverMotivo').value.trim();

  try {
    const token = localStorage.getItem('cpe_token') || '';
    const res = await fetch(`${API_BASE}/tickets/${viewingTicketId}/devolver`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ usuario_id: userId, motivo: motivo || null })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showError(err.detail || 'Erro ao devolver o chamado.');
      return;
    }

    bootstrap.Modal.getInstance(document.getElementById('devolverModal'))?.hide();
    bootstrap.Modal.getInstance(document.getElementById('ticketDetailModal'))?.hide();
    showSuccess('Chamado devolvido para a fila do setor.');
    await loadTickets();

  } catch (e) {
    console.error('[DEVOLVER] Erro:', e);
    showError('Erro de conexão ao devolver o chamado.');
  }
}

// =========================================
// 24. ENCAMINHAR TICKET
// =========================================

/**
 * Abre o modal de encaminhamento, populando o select de grupos
 * (excluindo o grupo atual do ticket) e, se admin, o select de responsáveis.
 */
async function openForwardModal() {
  if (!viewingTicketId) return;

  const ticket = tickets.find(t => t.id === viewingTicketId);
  if (!ticket) return;

  // Limpar estado anterior
  const groupSelect  = document.getElementById('forwardGroupSelect');
  const respSelect   = document.getElementById('forwardResponsavelSelect');
  const respDiv      = document.getElementById('forwardResponsavelDiv');
  const motivoEl     = document.getElementById('forwardMotivo');
  const errorEl      = document.getElementById('forwardError');

  groupSelect.innerHTML  = '<option value="">Selecione o grupo...</option>';
  respSelect.innerHTML   = '<option value="">Sem atribuição</option>';
  motivoEl.value         = '';
  errorEl.classList.add('d-none');

  // Carregar grupos se ainda não carregados
  if (!groups || groups.length === 0) {
    await loadGroups();
  }

  // Popular grupos — excluir o grupo atual do ticket
  const currentGroupId = ticket.group_id;
  groups.forEach(g => {
    if (g.id === currentGroupId) return; // pula grupo atual
    const opt = document.createElement('option');
    opt.value       = g.id;
    opt.textContent = g.name;
    groupSelect.appendChild(opt);
  });

  // Mostrar responsável apenas para admins
  if (isAdmin()) {
    respDiv.classList.remove('d-none');

    // Quando o grupo de destino mudar, carregar usuários daquele grupo
    groupSelect.onchange = async () => {
      respSelect.innerHTML = '<option value="">Sem atribuição</option>';
      const gid = parseInt(groupSelect.value);
      if (!gid) return;

      try {
        const userId = getCurrentUserId();
        const token  = localStorage.getItem('cpe_token') || '';
        const res    = await fetch(`${API_BASE}/users?usuario_id=${userId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) return;
        const data = await res.json();
        const list = Array.isArray(data) ? data : (data.users || []);

        list
          .filter(u => u.group_id === gid)
          .forEach(u => {
            const opt = document.createElement('option');
            opt.value       = u.id;
            opt.textContent = u.name;
            respSelect.appendChild(opt);
          });
      } catch (e) {
        console.error('[ENCAMINHAR] Erro ao carregar usuários do grupo:', e);
      }
    };
  } else {
    respDiv.classList.add('d-none');
    groupSelect.onchange = null;
  }

  // Abrir modal
  const modal = new bootstrap.Modal(document.getElementById('forwardModal'));
  modal.show();
}

/**
 * Envia o pedido de encaminhamento para o backend.
 */
async function submitForward() {
  const groupSelect = document.getElementById('forwardGroupSelect');
  const respSelect  = document.getElementById('forwardResponsavelSelect');
  const motivoEl    = document.getElementById('forwardMotivo');
  const errorEl     = document.getElementById('forwardError');

  const groupId = parseInt(groupSelect.value);
  if (!groupId) {
    errorEl.textContent = 'Selecione o grupo de destino.';
    errorEl.classList.remove('d-none');
    return;
  }

  const userId       = getCurrentUserId();
  const motivo       = motivoEl.value.trim();
  const responsavelId = isAdmin() && respSelect.value ? parseInt(respSelect.value) : null;

  const payload = {
    usuario_id:     userId,
    group_id:       groupId,
    motivo:         motivo || null,
    responsavel_id: responsavelId
  };

  try {
    const token = localStorage.getItem('cpe_token') || '';
    const res   = await fetch(`${API_BASE}/tickets/${viewingTicketId}/encaminhar`, {
      method:  'POST',
      headers: {
        'Content-Type':  'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      errorEl.textContent = err.detail || 'Erro ao encaminhar o chamado.';
      errorEl.classList.remove('d-none');
      return;
    }

    // Fechar modal e recarregar
    bootstrap.Modal.getInstance(document.getElementById('forwardModal'))?.hide();
    bootstrap.Modal.getInstance(document.getElementById('ticketDetailModal'))?.hide();
    showSuccess('Chamado encaminhado com sucesso!');
    await loadTickets();

  } catch (e) {
    console.error('[ENCAMINHAR] Erro:', e);
    errorEl.textContent = 'Erro de conexão. Tente novamente.';
    errorEl.classList.remove('d-none');
  }
}

// =========================================
// 25. SLA — MODAL DE DETALHE
// =========================================

/** Atualiza o painel de SLA no modal de detalhe */
function renderSLANoModal(ticket) {
  const sla   = ticket.sla;
  const row   = document.getElementById('detailSLARow');
  const badge = document.getElementById('detailSLABadge');
  const bar   = document.getElementById('detailSLABarFill');
  const label = document.getElementById('detailSLALabel');
  const ctrl  = document.getElementById('detailSLAControls');
  const btnP  = document.getElementById('btnSLAPausar');
  const btnR  = document.getElementById('btnSLARetomar');

  if (!sla || !sla.calculo) {
    if (row) row.style.display = 'none';
    return;
  }

  row.style.display = '';
  const c = sla.calculo;
  const colorMap = { verde: '#198754', amarelo: '#ffc107', vermelho: '#dc3545', cinza: '#6c757d' };

  badge.innerHTML = getSLABadge(sla);
  bar.style.background  = colorMap[c.cor] || '#6c757d';
  bar.style.width       = Math.min(c.percentual, 100) + '%';
  label.textContent     = c.label;

  // Controles de pausa — apenas para gestores (RESPONSAVEL_GRUPO ou admin)
  if (isGestor() && c.status !== 'concluido' && c.status !== 'estourado' && c.status !== 'aguardando') {
    ctrl.style.removeProperty('display');
    if (c.status === 'pausado') {
      btnP.classList.add('d-none');
      btnR.classList.remove('d-none');
    } else {
      btnP.classList.remove('d-none');
      btnR.classList.add('d-none');
    }
  } else {
    ctrl.style.setProperty('display', 'none', 'important');
  }
}

async function pausarSLAManual() {
  if (!viewingTicketId) return;
  const userId = getCurrentUserId();
  const motivo = prompt('Motivo da pausa (opcional):') || null;
  try {
    const token = localStorage.getItem('cpe_token') || '';
    const res   = await fetch(`${API_BASE}/tickets/${viewingTicketId}/sla/pausar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body:   JSON.stringify({ usuario_id: userId, motivo })
    });
    if (!res.ok) { const e = await res.json().catch(() => ({})); showError(e.detail || 'Erro ao pausar SLA.'); return; }
    showSuccess('SLA pausado.');
    await loadTickets();
    const t = tickets.find(x => x.id === viewingTicketId);
    if (t) renderSLANoModal(t);
  } catch (e) { showError('Erro de conexão.'); }
}

async function retomarSLAManual() {
  if (!viewingTicketId) return;
  const userId = getCurrentUserId();
  try {
    const token = localStorage.getItem('cpe_token') || '';
    const res   = await fetch(`${API_BASE}/tickets/${viewingTicketId}/sla/retomar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body:   JSON.stringify({ usuario_id: userId })
    });
    if (!res.ok) { const e = await res.json().catch(() => ({})); showError(e.detail || 'Erro ao retomar SLA.'); return; }
    showSuccess('SLA retomado.');
    await loadTickets();
    const t = tickets.find(x => x.id === viewingTicketId);
    if (t) renderSLANoModal(t);
  } catch (e) { showError('Erro de conexão.'); }
}

// =========================================
// 26. ALERTAS
// =========================================

function showAlert(id, msg) {
  const box       = document.getElementById(id);
  const messageEl = box?.querySelector('span');
  if (box && messageEl) {
    messageEl.innerHTML = msg;
    box.classList.remove("d-none");
    setTimeout(() => box.classList.add("d-none"), 5000);
  }
}

function showError(msg)   { showAlert("alertBox",    msg); console.error(`[ALERTA] ${msg}`); }
function showSuccess(msg) { showAlert("successBox",  msg); console.log(`[ALERTA] ${msg}`);   }

console.log("[TICKETS] 🎉 Script carregado completamente!");

// =========================================
// 27. SISTEMA DE AVALIAÇÃO DE CHAMADOS
// =========================================

let _avaliacaoPendente = null; // ticket atual sendo avaliado

/**
 * Verifica se há avaliações pendentes para o usuário logado.
 * Exibe popup para as que ainda não foram mostradas 2x.
 */
async function verificarAvaliacoesPendentes() {
  const userId = getCurrentUserId();
  if (!userId) return;

  try {
    const pendentes = await apiRequest('GET', `/avaliacoes/pendentes?usuario_id=${userId}`);
    if (!pendentes || pendentes.length === 0) return;

    // Mostra o primeiro da fila
    _abrirPopupAvaliacao(pendentes[0]);
  } catch (err) {
    console.warn('[AVAL] Erro ao verificar pendentes:', err);
  }
}

function _abrirPopupAvaliacao(aval) {
  _avaliacaoPendente = aval;

  // Preenche modal
  document.getElementById('avalModalNumero').textContent  = aval.numero || `#${aval.ticket_id}`;
  document.getElementById('avalModalAssunto').textContent = aval.assunto || '—';
  document.getElementById('avalModalResp').textContent    = aval.responsavel_nome || '—';
  document.getElementById('avalStarInput').value          = '';
  document.getElementById('avalComentario').value         = '';
  document.getElementById('avalComentarioWrap').classList.add('d-none');
  document.getElementById('avalComentarioObrig').classList.add('d-none');
  document.getElementById('avalErro').textContent         = '';
  document.getElementById('avalBtnEnviar').disabled       = true;
  _renderAvalStars(0);

  // Registra que o popup foi exibido
  apiRequest('POST', `/avaliacoes/popup-visto/${aval.ticket_id}?usuario_id=${getCurrentUserId()}`)
    .catch(() => {});

  const modal = new bootstrap.Modal(document.getElementById('avaliacaoModal'), { backdrop: 'static', keyboard: false });
  modal.show();
}

function _renderAvalStars(selected) {
  const container = document.getElementById('avalStarsContainer');
  let html = '';
  for (let i = 1; i <= 10; i++) {
    const filled = i <= selected;
    html += `<i class="bi bi-star${filled ? '-fill' : ''} aval-star"
               style="font-size:1.6rem;cursor:pointer;color:${filled ? '#f59e0b' : '#d1d5db'};transition:color .1s;"
               data-val="${i}"
               onmouseover="_hoverStars(${i})"
               onmouseout="_renderAvalStars(parseInt(document.getElementById('avalStarInput').value)||0)"
               onclick="_selecionarEstrela(${i})"></i>`;
  }
  container.innerHTML = html;
}

function _hoverStars(n) {
  const container = document.getElementById('avalStarsContainer');
  container.querySelectorAll('.aval-star').forEach((el, idx) => {
    const filled = idx + 1 <= n;
    el.className  = `bi bi-star${filled ? '-fill' : ''} aval-star`;
    el.style.color = filled ? '#f59e0b' : '#d1d5db';
  });
}

function _selecionarEstrela(n) {
  document.getElementById('avalStarInput').value = n;
  _renderAvalStars(n);

  // Comentário obrigatório se < 4
  const wrap  = document.getElementById('avalComentarioWrap');
  const obrig = document.getElementById('avalComentarioObrig');
  if (n < 4) {
    wrap.classList.remove('d-none');
    obrig.classList.remove('d-none');
  } else {
    wrap.classList.remove('d-none');
    obrig.classList.add('d-none');
  }

  document.getElementById('avalBtnEnviar').disabled = false;
}

async function submitAvaliacao() {
  if (!_avaliacaoPendente) return;
  const estrelas   = parseInt(document.getElementById('avalStarInput').value);
  const comentario = document.getElementById('avalComentario').value.trim();
  const erroEl     = document.getElementById('avalErro');

  if (!estrelas) { erroEl.textContent = 'Selecione uma nota antes de enviar.'; return; }
  if (estrelas < 4 && !comentario) {
    erroEl.textContent = 'Comentário obrigatório para notas abaixo de 4 estrelas.';
    document.getElementById('avalComentario').focus();
    return;
  }

  const btn = document.getElementById('avalBtnEnviar');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Enviando...';
  erroEl.textContent = '';

  try {
    await apiRequest('POST', `/avaliacoes/${_avaliacaoPendente.ticket_id}`, {
      usuario_id: getCurrentUserId(),
      estrelas,
      comentario: comentario || null
    });

    bootstrap.Modal.getInstance(document.getElementById('avaliacaoModal'))?.hide();
    showSuccess('✅ Avaliação enviada! Obrigado pelo seu feedback.');
    _avaliacaoPendente = null;
  } catch (err) {
    erroEl.textContent = err?.detail || 'Erro ao enviar avaliação. Tente novamente.';
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-send me-1"></i>Enviar Avaliação';
  }
}

function pularAvaliacao() {
  bootstrap.Modal.getInstance(document.getElementById('avaliacaoModal'))?.hide();
  _avaliacaoPendente = null;
}

// =========================================
// VISTA DE TICKETS (abas: Todos / Meus / Para mim)
// =========================================

/** Troca a aba ativa e re-renderiza a lista (ou abre o painel de antigos). */
function setTicketsVista(vista) {
  if (!['todos', 'meus', 'para_mim', 'antigos'].includes(vista)) vista = 'todos';
  currentVista = vista;
  document.querySelectorAll('.tickets-view-tabs .nav-link').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.vista === vista);
  });

  // Toggle entre painel normal de tickets e painel de chamados antigos
  const painelAntigos = document.getElementById('painelChamadosAntigos');
  // Pega APENAS os elementos da tabela normal — não os de dentro do painel de antigos
  const tabelaNormal     = document.getElementById('ticketsBody')?.closest('.table-responsive');
  const paginacaoNormal  = document.querySelector('.content > .pagination-bar')
                        || (tabelaNormal && tabelaNormal.nextElementSibling?.classList?.contains('pagination-bar')
                              ? tabelaNormal.nextElementSibling : null);
  const elementosNormais = [
    document.querySelector('.advanced-filters'),
    document.querySelector('.stats-bar'),
    document.querySelector('.dashboard-sla-container'),
    tabelaNormal,
    paginacaoNormal,
  ].filter(Boolean);

  if (vista === 'antigos') {
    elementosNormais.forEach(el => el.classList.add('d-none'));
    if (painelAntigos) painelAntigos.classList.remove('d-none');
    carregarCategoriasAntigas();
    carregarStatusAntigos();
    carregarTotalChamadosAntigos();
    buscarChamadosAntigos(1);
  } else {
    elementosNormais.forEach(el => el.classList.remove('d-none'));
    if (painelAntigos) painelAntigos.classList.add('d-none');
    applyFilters();
  }
}

// =========================================
// CHAMADOS ANTIGOS (somente consulta)
// =========================================

let _antigosPagina = 1;
let _antigosTotalPags = 1;

async function carregarTotalChamadosAntigos() {
  try {
    const r = await fetch(`${API_BASE}/chamados-antigos/stats`);
    if (!r.ok) return;
    const j = await r.json();
    const el = document.getElementById('vistaCountAntigos');
    if (el) el.textContent = j.total ?? 0;
    // Exibe data/hora da última importação no alerta
    const imp = document.getElementById('antigosUltimoImport');
    if (imp) {
      if (j.ultimo_import) {
        const d = new Date(j.ultimo_import);
        imp.innerHTML = `<i class="bi bi-clock-history"></i> Importado em <strong>${d.toLocaleString('pt-BR')}</strong>`;
      } else {
        imp.textContent = '';
      }
    }
  } catch (e) { /* ignore */ }
}

/** Popula o select de categorias com os valores distintos da base. Cacheado por sessão. */
let _antigosCategoriasCarregadas = false;
async function carregarCategoriasAntigas() {
  if (_antigosCategoriasCarregadas) return;
  try {
    const r = await fetch(`${API_BASE}/chamados-antigos/categorias`);
    if (!r.ok) return;
    const cats = await r.json();
    const sel = document.getElementById('antigosCategoria');
    if (!sel) return;
    const valorAtual = sel.value;
    sel.innerHTML = '<option value="">Todas categorias</option>' +
      cats.map(c => {
        const nome = (c.categoria || '').replace(/</g,'&lt;');
        return `<option value="${nome}">${nome} (${c.total})</option>`;
      }).join('');
    sel.value = valorAtual;
    _antigosCategoriasCarregadas = true;
  } catch (e) { console.warn('[ANTIGOS] erro categorias:', e); }
}

/** Popula o select de status com os valores reais da base (cacheado).
 *  Legado usa Novo/Respondido/Em Progresso/etc — hardcode antigo
 *  (Aberto/Em andamento/Fechado) nao batia e sempre retornava 0. */
let _antigosStatusCarregados = false;
async function carregarStatusAntigos() {
  if (_antigosStatusCarregados) return;
  try {
    const r = await fetch(`${API_BASE}/chamados-antigos/status`);
    if (!r.ok) return;
    const arr = await r.json();
    const sel = document.getElementById('antigosStatus');
    if (!sel) return;
    const valorAtual = sel.value;
    sel.innerHTML = '<option value="">Todos status</option>' +
      arr.map(s => {
        const nome = (s.nome_status || '').replace(/</g,'&lt;');
        return `<option value="${nome}">${nome} (${s.total})</option>`;
      }).join('');
    sel.value = valorAtual;
    _antigosStatusCarregados = true;
  } catch (e) { console.warn('[ANTIGOS] erro status:', e); }
}

async function buscarChamadosAntigos(pagina = 1) {
  _antigosPagina = pagina;
  const q        = document.getElementById('antigosSearch')?.value?.trim() || '';
  const status   = document.getElementById('antigosStatus')?.value || '';
  const categoria = document.getElementById('antigosCategoria')?.value || '';
  const dataIni  = document.getElementById('antigosDataIni')?.value || '';
  const dataFim  = document.getElementById('antigosDataFim')?.value || '';

  const params = new URLSearchParams({ pagina, por_pagina: 25 });
  if (q)         params.set('q', q);
  if (status)    params.set('status', status);
  if (categoria) params.set('categoria', categoria);
  if (dataIni)   params.set('data_ini', dataIni);
  if (dataFim)   params.set('data_fim', dataFim);

  const tbody = document.getElementById('antigosBody');
  if (tbody) tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-3"><i class="bi bi-hourglass-split"></i> Carregando...</td></tr>';

  try {
    const r = await fetch(`${API_BASE}/chamados-antigos?${params}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const j = await r.json();
    _renderChamadosAntigosTabela(j);
  } catch (e) {
    console.error('[ANTIGOS] erro:', e);
    if (tbody) tbody.innerHTML = '<tr><td colspan="8" class="text-center text-danger py-3">Erro ao consultar chamados antigos. Verifique se a tabela foi populada.</td></tr>';
  }
}

function _renderChamadosAntigosTabela(data) {
  const tbody = document.getElementById('antigosBody');
  if (!tbody) return;
  _antigosTotalPags = data.total_paginas || 1;

  document.getElementById('antigosPagAtual').textContent  = data.pagina;
  document.getElementById('antigosTotalPags').textContent = _antigosTotalPags;
  document.getElementById('antigosResumo').textContent =
    `${data.total} chamado(s) — mostrando ${data.itens.length}`;

  if (!data.itens.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">Nenhum chamado encontrado.</td></tr>';
    return;
  }

  tbody.innerHTML = data.itens.map(c => {
    const aberto = c.aberto_em  ? new Date(c.aberto_em).toLocaleDateString('pt-BR') : '—';
    const fech   = c.fechado_em ? new Date(c.fechado_em).toLocaleDateString('pt-BR') : '—';
    const status = c.nome_status || '—';
    return `
      <tr style="cursor:pointer;" onclick="abrirChamadoAntigo('${c.trackid}')">
        <td><code class="text-primary">${c.trackid}</code></td>
        <td>${(c.assunto || '').replace(/</g,'&lt;')}</td>
        <td>${(c.solicitante || '').replace(/</g,'&lt;')}</td>
        <td><span class="badge bg-secondary">${(c.categoria || '—').replace(/</g,'&lt;')}</span></td>
        <td>${_renderStatusAntigo(status)}</td>
        <td>${(c.atribuido_a || '—').replace(/</g,'&lt;')}</td>
        <td class="small">${aberto}</td>
        <td class="small">${fech}</td>
      </tr>`;
  }).join('');
}

function _renderStatusAntigo(s) {
  const map = {
    'Resolvido':    'bg-success',
    'Fechado':      'bg-secondary',
    'Em andamento': 'bg-info text-dark',
    'Aberto':       'bg-warning text-dark',
  };
  return `<span class="badge ${map[s] || 'bg-light text-dark'}">${s}</span>`;
}

function antigosPagAnt() {
  if (_antigosPagina > 1) buscarChamadosAntigos(_antigosPagina - 1);
}
function antigosPagProx() {
  if (_antigosPagina < _antigosTotalPags) buscarChamadosAntigos(_antigosPagina + 1);
}

async function abrirChamadoAntigo(trackid) {
  try {
    // Caso 1: TICKET NORMAL já aberto → split (antigo à direita)
    const ticketEl = document.getElementById('ticketDetailModal');
    if (ticketEl?.classList.contains('show') && viewingTicketId) {
      _splitAntigoId = trackid;
      _splitTicketId = null;
      await _renderSplitPanelAntigo(trackid);
      document.body.classList.add('ticket-split-mode');
      return;
    }

    // Caso 2: OUTRO CHAMADO ANTIGO já aberto → split entre 2 antigos
    //   - O antigo atual fica à esquerda (modal principal `chamadoAntigoModal`)
    //   - O novo trackid vai para o painel direito `#ticketDetailModal2` (read-only)
    const modalEl = document.getElementById('chamadoAntigoModal');
    const antigoAberto = modalEl?.classList.contains('show') && _viewingAntigoId;
    if (antigoAberto && _viewingAntigoId !== trackid) {
      _splitAntigoId = trackid;
      _splitTicketId = null;
      await _renderSplitPanelAntigo(trackid);
      document.body.classList.add('ticket-split-mode');
      return;
    }

    // Caso 3: nenhum modal aberto (ou clicou no mesmo antigo já aberto) → abre normal
    const r = await fetch(`${API_BASE}/chamados-antigos/${encodeURIComponent(trackid)}`);
    if (!r.ok) { showError('Chamado não encontrado'); return; }
    const c = await r.json();

    const jaVisivel = modalEl?.classList.contains('show');
    _viewingAntigoId = trackid;

    const setText = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v || '—'; };
    const fmt = (d) => d ? new Date(d).toLocaleString('pt-BR') : '—';

    setText('antigoTitulo',         c.assunto);
    setText('antigoTrackid',        ' · ' + c.trackid);
    setText('antigoSolicitante',    c.solicitante);
    setText('antigoEmail',          c.email);
    setText('antigoStatus',         c.nome_status);
    setText('antigoCategoria',      c.categoria);
    setText('antigoAtribuido',      c.atribuido_a);
    setText('antigoAberto',         fmt(c.aberto_em));
    setText('antigoPrimeiraResp',   fmt(c.primeira_resp));
    setText('antigoFechado',        fmt(c.fechado_em));
    setText('antigoMensagem',       c.mensagem);
    setText('antigoRespondidoPor',  c.respondido_por);
    setText('antigoDhResposta',     fmt(c.dh_resposta));
    setText('antigoResposta',       c.resposta);

    if (jaVisivel) {
      // Modal já aberto — só atualizamos os dados, sem reabrir
      return;
    }
    // Limpa estado fantasma deixado por um minimize anterior
    if (modalEl) {
      modalEl.style.display = '';
      modalEl.removeAttribute('aria-hidden');
    }
    new bootstrap.Modal(modalEl).show();
  } catch (e) {
    console.error('[ANTIGOS] detalhe:', e);
    showError('Erro ao carregar chamado.');
  }
}

// Carrega a contagem inicial quando a página inicializar
document.addEventListener('DOMContentLoaded', () => { carregarTotalChamadosAntigos(); });

// =========================================
// CHAMADO ANTIGO — minimizar, fullscreen, split
// =========================================

/** Minimiza o modal de chamado antigo e cria um chip no dock. */
function minimizeChamadoAntigoModal() {
  const trackid = _viewingAntigoId;
  if (!trackid) return;
  if (!_dockHasRoom(trackid)) return;
  const tituloEl = document.getElementById('antigoTitulo');
  const titulo   = tituloEl?.textContent || trackid;

  _minimizedAntigos[trackid] = { trackid, assunto: titulo };
  _renderTicketDock();

  // Fecha manualmente (mesmo padrão do ticket normal)
  const modalEl = document.getElementById('chamadoAntigoModal');
  if (modalEl) {
    modalEl.classList.remove('show');
    modalEl.style.display = 'none';
    modalEl.setAttribute('aria-hidden', 'true');
  }
  document.body.classList.remove('modal-open');
  document.body.style.overflow     = '';
  document.body.style.paddingRight = '';
  document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
  const inst = bootstrap.Modal.getInstance(modalEl);
  if (inst) { try { inst.dispose(); } catch(e){} }
}

/** Alterna fullscreen do modal de chamado antigo. */
function toggleChamadoAntigoFullscreen() {
  const dialog = document.getElementById('chamadoAntigoDialog');
  const icon   = document.getElementById('iconChamadoAntigoFullscreen');
  const modalEl = document.getElementById('chamadoAntigoModal');
  if (!dialog) return;
  const expandido = dialog.classList.toggle('modal-fullscreen');
  if (expandido) {
    dialog.classList.remove('modal-lg', 'modal-dialog-centered');
    if (icon) icon.className = 'bi bi-arrows-angle-contract';
    if (modalEl) modalEl.style.paddingRight = '0';
  } else {
    dialog.classList.add('modal-lg', 'modal-dialog-centered');
    if (icon) icon.className = 'bi bi-arrows-fullscreen';
    if (modalEl) modalEl.style.paddingRight = '';
  }
}

/** Restaura um chamado antigo do dock. */
function restoreAntigoFromDock(trackid) {
  delete _minimizedAntigos[trackid];
  _renderTicketDock();
  abrirChamadoAntigo(trackid);
}

/** Descarta um chamado antigo do dock sem reabrir. */
function closeAntigoFromDock(trackid) {
  delete _minimizedAntigos[trackid];
  _renderTicketDock();
}

/** Ativa split com chamado antigo à direita (modal de ticket normal precisa estar aberto). */
async function openAntigoInSplit(trackid) {
  const modalEl = document.getElementById('ticketDetailModal');
  const modalVisible = modalEl?.classList.contains('show');
  if (!modalVisible || !viewingTicketId) {
    restoreAntigoFromDock(trackid);
    return;
  }
  delete _minimizedAntigos[trackid];
  _renderTicketDock();
  _splitAntigoId = trackid;
  _splitTicketId = null;
  await _renderSplitPanelAntigo(trackid);
  document.body.classList.add('ticket-split-mode');
}

/** Popula o painel direito com dados de um chamado antigo (somente leitura). */
async function _renderSplitPanelAntigo(trackid) {
  try {
    const r = await fetch(`${API_BASE}/chamados-antigos/${encodeURIComponent(trackid)}`);
    if (!r.ok) return;
    const c = await r.json();
    const fmt = (d) => d ? new Date(d).toLocaleString('pt-BR') : '—';

    // Aplica variante CINZA (chamado antigo) + ícone de arquivo
    const sidePanel = document.getElementById('ticketDetailModal2');
    if (sidePanel) sidePanel.classList.add('is-antigo');
    const icon = document.getElementById('iconDetailHeader2');
    if (icon) icon.className = 'bi bi-archive';

    document.getElementById('detailTitle2').textContent       = c.assunto || '';
    document.getElementById('detailId2').textContent          = ' · ' + c.trackid;
    document.getElementById('detail2UserName').textContent    = c.solicitante || '';
    document.getElementById('detail2Status').innerHTML        =
      `<span class="badge bg-light text-dark">${c.nome_status || '—'}</span>`;
    document.getElementById('detail2AssignedName').textContent = c.atribuido_a || '—';
    document.getElementById('detail2Description').textContent  = c.mensagem || '';

    const box = document.getElementById('detail2CommentsList');
    if (c.resposta) {
      box.innerHTML = `
        <div class="comment-item p-2 mb-2 rounded bg-light">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <strong>${(c.respondido_por||'—').replace(/</g,'&lt;')}</strong>
            <small class="text-muted">${fmt(c.dh_resposta)}</small>
          </div>
          <div style="white-space:pre-wrap;">${(c.resposta||'').replace(/</g,'&lt;')}</div>
        </div>`;
    } else {
      box.innerHTML = '<p class="text-muted text-center py-3">Sem resposta registrada</p>';
    }
  } catch (e) { console.warn('[SPLIT-ANTIGO] erro:', e); }
}

// Limpa _viewingAntigoId quando o modal antigo for fechado
document.addEventListener('DOMContentLoaded', () => {
  const m = document.getElementById('chamadoAntigoModal');
  if (m) m.addEventListener('hidden.bs.modal', () => { _viewingAntigoId = null; });
});

/** Atualiza os contadores das abas a partir da lista carregada. */
function updateVistaCounts() {
  const userId = getCurrentUserId();
  const total    = tickets.length;
  const meus     = tickets.filter(t => t.solicitante_id === userId).length;
  const paraMim  = tickets.filter(t => t.assignedTo === userId).length;

  const setCount = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };
  setCount('vistaCountTodos',  total);
  setCount('vistaCountMeus',   meus);
  setCount('vistaCountParaMim', paraMim);

  // USER nunca recebe atribuição → esconde a aba "Para mim"
  const item = document.getElementById('vistaParaMimItem');
  if (item) {
    const podeReceber = isGestor() || paraMim > 0;
    item.style.display = podeReceber ? '' : 'none';
  }
}

// =========================================
// ANEXOS DE IMAGEM (≤250 KB)
// =========================================

function _humanSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function _validateAttachFile(file) {
  if (!ATTACH_MIMES_OK.includes(file.type)) {
    return `"${file.name}": tipo não permitido (${file.type || 'desconhecido'}). Use JPG, PNG, PDF, Word ou Excel.`;
  }
  if (file.size > ATTACH_MAX_BYTES) {
    return `"${file.name}" tem ${_humanSize(file.size)} (limite 10 MB).`;
  }
  return null;
}

// 2026-08-19: helper — retorna ícone Bootstrap p/ tipos não-imagem
function _iconForMime(mime) {
  if (!mime) return 'bi-file-earmark';
  if (mime === 'application/pdf') return 'bi-file-earmark-pdf-fill';
  if (mime.includes('word') || mime.includes('wordprocessing')) return 'bi-file-earmark-word-fill';
  if (mime.includes('excel') || mime.includes('spreadsheet')) return 'bi-file-earmark-excel-fill';
  return 'bi-file-earmark';
}
function _colorForMime(mime) {
  if (mime === 'application/pdf') return '#DC2626';
  if (mime.includes('word') || mime.includes('wordprocessing')) return '#2563EB';
  if (mime.includes('excel') || mime.includes('spreadsheet')) return '#16A34A';
  return '#6B7280';
}

function _renderAttachPreview(slot, container) {
  if (!container) return;
  const files = pendingAttachments[slot];
  if (!files.length) {
    container.innerHTML = '';
    return;
  }
  container.innerHTML = files.map((f, idx) => {
    const safeName = (f.name || 'arquivo').replace(/"/g, '&quot;').replace(/'/g, "\\'");
    const isImg = (f.type || '').startsWith('image/');
    if (isImg) {
      return `
        <div class="attach-thumb"
             onclick="openImageViewer('${f._previewUrl}', '${safeName}')">
          <img src="${f._previewUrl}" alt="${f.name}">
          <button type="button" class="attach-remove" title="Remover"
            onclick="event.stopPropagation(); removePendingAttach('${slot}', ${idx})">×</button>
          <span class="attach-size">${_humanSize(f.size)}</span>
        </div>`;
    }
    // Não-imagem: card com ícone + nome + tamanho
    const icon = _iconForMime(f.type);
    const color = _colorForMime(f.type);
    return `
      <div class="attach-thumb attach-doc" style="display:flex;flex-direction:column;align-items:center;justify-content:center;background:#F9FAFB;border:1px solid #E5E7EB;border-radius:6px;padding:10px 8px;min-width:110px;position:relative">
        <i class="bi ${icon}" style="font-size:32px;color:${color}"></i>
        <span style="font-size:11px;font-weight:600;color:#374151;margin-top:4px;max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${safeName}">${safeName}</span>
        <button type="button" class="attach-remove" title="Remover"
          onclick="event.stopPropagation(); removePendingAttach('${slot}', ${idx})">×</button>
        <span class="attach-size">${_humanSize(f.size)}</span>
      </div>`;
  }).join('');
}

function removePendingAttach(slot, idx) {
  const arr = pendingAttachments[slot] || [];
  const f = arr[idx];
  if (f && f._previewUrl) URL.revokeObjectURL(f._previewUrl);
  arr.splice(idx, 1);
  const containerId = slot === 'create' ? 'ticketAttachPreview'
                    : slot === 'reply'  ? 'replyAttachPreview'
                    : 'internalAttachPreview';
  _renderAttachPreview(slot, document.getElementById(containerId));
}

function _addPendingFiles(slot, fileList, previewContainerId) {
  const errors = [];
  for (const f of fileList) {
    const err = _validateAttachFile(f);
    if (err) { errors.push(err); continue; }
    f._previewUrl = URL.createObjectURL(f);
    pendingAttachments[slot].push(f);
  }
  _renderAttachPreview(slot, document.getElementById(previewContainerId));
  if (errors.length) showError(errors.join('\n'));
}

/** Handler do input de anexos no modal Novo Ticket. */
function onTicketAttachChange(e) {
  _addPendingFiles('create', e.target.files, 'ticketAttachPreview');
  e.target.value = ''; // permite re-selecionar mesmo arquivo
}

/** Handler dos inputs de anexos nos forms de resposta/comentário. */
function onReplyAttachChange(e, slot) {
  const previewId = slot === 'reply' ? 'replyAttachPreview' : 'internalAttachPreview';
  _addPendingFiles(slot, e.target.files, previewId);
  e.target.value = '';
}

/** Limpa um slot e revoga as URLs de preview. */
function _clearPendingSlot(slot) {
  (pendingAttachments[slot] || []).forEach(f => {
    if (f._previewUrl) URL.revokeObjectURL(f._previewUrl);
  });
  pendingAttachments[slot] = [];
  const containerId = slot === 'create' ? 'ticketAttachPreview'
                    : slot === 'reply'  ? 'replyAttachPreview'
                    : 'internalAttachPreview';
  const el = document.getElementById(containerId);
  if (el) el.innerHTML = '';
}

/**
 * Envia os arquivos pendentes para o backend após criar o ticket/interação.
 * Em caso de erro num arquivo, segue tentando os outros.
 */
async function _uploadPendingAttachments(slot, ticketId, interacaoId = null) {
  const files = pendingAttachments[slot] || [];
  if (!files.length) return [];

  const userId = getCurrentUserId();
  const enviados = [];
  for (const f of files) {
    const form = new FormData();
    form.append('usuario_id', userId);
    if (interacaoId) form.append('interacao_id', interacaoId);
    form.append('file', f, f.name);
    try {
      const token = localStorage.getItem('cpe_token') || '';
      const res = await fetch(`${API_BASE}/tickets/${ticketId}/attachments`, {
        method: 'POST',
        headers: token ? { 'X-Auth-Token': token } : {},
        body: form,
      });
      if (!res.ok) {
        const txt = await res.text();
        console.warn(`[ATTACH] Falha ao enviar "${f.name}": ${res.status} ${txt}`);
        showError(`Falha ao enviar "${f.name}"`);
        continue;
      }
      enviados.push(await res.json());
    } catch (err) {
      console.error('[ATTACH] erro:', err);
    }
  }
  _clearPendingSlot(slot);
  return enviados;
}