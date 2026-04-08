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

const API_BASE    = 'http://127.0.0.1:8000/api';
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

    // ✅ Abre ticket automaticamente se vier de notificação (?ticket_id=X)
    checkUrlTicketId();

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

  console.log(`[PERMISSAO] ✅ Elementos ajustados para role: ${role}`);
}

/**
 * Aplica permissões dentro do modal de detalhe do ticket.
 * Chamado toda vez que o modal é aberto, pois depende do ticket visualizado.
 */
function applyDetailPermissions(ticket) {
  const admin           = isAdmin();
  const responsavel     = isResponsavelGrupo();
  const gestor          = isGestor();
  const userId          = getCurrentUserId();
  const isSolicitante   = ticket.solicitante_id === userId;
  const isResponsavelDoTicket = ticket.assignedTo === userId;
  // USER pode interagir (responder) apenas se for o responsável atribuído ao ticket
  const podeInteragir   = gestor || isSolicitante || isResponsavelDoTicket;

  // Aba "Ações" — apenas gestores
  const tabActions = document.querySelector('[onclick="switchTab(event, \'actions\')"]');
  if (tabActions) tabActions.style.display = gestor ? '' : 'none';

  // Aba "Comentário Interno" — apenas admin completo
  const tabInternal = document.querySelector('[onclick="switchReplyMode(event, \'internal\')"]');
  if (tabInternal) tabInternal.style.display = admin ? '' : 'none';

  // Formulário de resposta pública — visível só para quem pode interagir
  const replyForm = document.getElementById('detailReplyForm');
  if (replyForm) {
    replyForm.style.display = podeInteragir ? '' : 'none';
    if (!podeInteragir) {
      // Exibe aviso de somente leitura
      const existing = document.getElementById('readonlyNotice');
      if (!existing) {
        const notice = document.createElement('p');
        notice.id = 'readonlyNotice';
        notice.className = 'text-muted text-center py-2';
        notice.innerHTML = '<i class="bi bi-eye"></i> Você pode visualizar este chamado mas não pode interagir. Aguarde ser atribuído.';
        replyForm.parentNode.insertBefore(notice, replyForm);
      }
    } else {
      document.getElementById('readonlyNotice')?.remove();
    }
  }

  // Botão "Deletar":
  // - Gestores: sempre
  // - USER: apenas o próprio ticket (solicitante)
  const btnDeletar = document.getElementById('btnDeletarTicket');
  if (btnDeletar) {
    btnDeletar.style.display = (gestor || isSolicitante) ? '' : 'none';
  }

  // Botão "Assumir": visível quando o ticket NÃO tem responsável e o usuário é do mesmo grupo
  const btnAssumir = document.getElementById('btnAssumirTicket');
  if (btnAssumir) {
    const user = getCurrentUser();
    const semResponsavel = !ticket.assignedTo || ticket.assignedTo === null;
    const mesmoGrupo = admin || (user.group_id && user.group_id === ticket.group_id);
    const ticketAberto = ticket.status !== 'Fechado' && ticket.status !== 'Cancelado';
    const podeAssumir = semResponsavel && mesmoGrupo && ticketAberto;
    btnAssumir.classList.toggle('d-none', !podeAssumir);
  }

  // Botão "Desistir": visível apenas para quem é o responsável atual
  const btnDevolver = document.getElementById('btnDevolverTicket');
  if (btnDevolver) {
    const ticketAberto = ticket.status !== 'Fechado' && ticket.status !== 'Cancelado';
    const podeDevolver = isResponsavelDoTicket && ticketAberto;
    btnDevolver.classList.toggle('d-none', !podeDevolver);
  }

  console.log(`[PERMISSAO] ✅ Modal | gestor:${gestor} | solicitante:${isSolicitante} | responsavelTicket:${isResponsavelDoTicket} | podeInteragir:${podeInteragir}`);
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
    const data = await apiRequest('GET', '/groups');
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

/** Carrega categorias do grupo selecionado e popula o select de categoria */
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
      return;
    }

    catSelect.innerHTML = '<option value="">Selecione uma categoria...</option>' +
      cats.map(c => `<option value="${c.id}" data-subs='${JSON.stringify(c.subcategorias || [])}'>${c.nome}</option>`).join('');

    catDiv.classList.remove('d-none');

    // Ao mudar categoria, popular subcategorias
    catSelect.onchange = () => {
      const opt  = catSelect.options[catSelect.selectedIndex];
      const subs = opt ? JSON.parse(opt.dataset.subs || '[]') : [];
      preencherSubcategorias(subs);
    };

  } catch (e) {
    console.warn('[TICKET] Erro ao carregar categorias:', e);
  }
}

/** Preenche o select de subcategorias com base na categoria escolhida */
function preencherSubcategorias(subs) {
  const subDiv    = document.getElementById('ticketSubcategoriaDiv');
  const subSelect = document.getElementById('ticketSubcategoria');
  if (!subDiv || !subSelect) return;

  subSelect.innerHTML = '<option value="">Selecione uma subcategoria...</option>';

  if (!subs.length) {
    subDiv.classList.add('d-none');
    return;
  }

  subs.forEach(s => {
    const opt = document.createElement('option');
    opt.value       = s.id;
    opt.textContent = s.nome;
    subSelect.appendChild(opt);
  });
  subDiv.classList.remove('d-none');
}

/** Limpa categoria e subcategoria ao mudar de grupo */
function resetCategoriaSubcategoria() {
  const catDiv  = document.getElementById('ticketCategoriaDiv');
  const subDiv  = document.getElementById('ticketSubcategoriaDiv');
  const catSel  = document.getElementById('ticketCategoria');
  const subSel  = document.getElementById('ticketSubcategoria');
  if (catDiv)  catDiv.classList.add('d-none');
  if (subDiv)  subDiv.classList.add('d-none');
  if (catSel)  catSel.innerHTML = '<option value="">Selecione uma categoria...</option>';
  if (subSel)  subSel.innerHTML = '<option value="">Selecione uma subcategoria...</option>';
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
        assignedTo:      t.responsavel_id,
        assignedName:    t.responsavel_nome || "Não atribuído",
        solicitante_id:  t.solicitante_id,
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
function mapStatusFromApi(id)   { return { 1: 'open', 2: 'in-progress', 3: 'resolved', 4: 'closed' }[id] || 'open'; }
function mapStatusToApi(s)      { return { 'open': 1, 'in-progress': 2, 'resolved': 3, 'closed': 4 }[s] || 1; }
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
  const search   = document.getElementById("searchInput")?.value?.toLowerCase().trim() || "";
  const status   = document.getElementById("statusFilter")?.value || "";
  const priority = document.getElementById("priorityFilter")?.value || "";

  filteredTickets = tickets.filter(t =>
    (!status   || t.status   === status)   &&
    (!priority || t.priority === priority) &&
    (!search   || t.title.toLowerCase().includes(search) ||
                  t.userName.toLowerCase().includes(search) ||
                  t.numero.toLowerCase().includes(search))
  );

  currentPage = 1;
  renderTable();
}

function clearFilters() {
  ['searchInput', 'statusFilter', 'priorityFilter'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  applyFilters();
  showSuccess("✅ Filtros limpos");
}

function toggleAdvancedFilters() {
  document.getElementById("advancedFilters")?.classList.toggle('d-none');
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

    // ✅ Botão deletar na linha: gestor (admin/responsável) vê sempre; USER só vê o próprio ticket
    const podeDeletar = gestor || t.solicitante_id === userId;
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

async function openTicketDetail(id) {
  const t = tickets.find(x => x.id === id);
  if (!t) {
    showError(`❌ Ticket #${id} não encontrado`);
    return;
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

  // ✅ Aplica permissões de acordo com o role e se é o solicitante
  applyDetailPermissions(t);

  // ✅ Renderiza painel de SLA
  renderSLANoModal(t);

  // ✅ Passa usuario_id para filtrar comentários internos no backend
  await loadTicketComments(id);

  new bootstrap.Modal(document.getElementById("ticketDetailModal")).show();
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

  // ✅ Preenche automaticamente com dados do usuário logado
  const user = getCurrentUser();
  document.getElementById("ticketClient").value = user.name  || user.usuario_nome  || '';
  document.getElementById("ticketEmail").value  = user.email || user.usuario_email || '';

  // ✅ Limpa categoria e subcategoria do form anterior
  resetCategoriaSubcategoria();

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

  const payload = {
    assunto:           title,
    descricao_inicial: description,
    prioridade_id:     mapPriorityToApi(document.getElementById("ticketPriority").value),
    group_id:          selectedGroupId,
    solicitante_id:    user.id || user.usuario_id,
    origem:            'web',
    categoria_id:      categoriaId,
    subcategoria_id:   subcategoriaId
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

  const data = await apiRequest(
    'GET',
    `/ticket-interacoes/${ticketId}?usuario_id=${userId}`
  );

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

  container.innerHTML = comentariosFiltrados.map(c => `
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
    </div>
  `).join("");
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
    showSuccess(`✅ ${isPublic ? 'Resposta enviada' : 'Comentário salvo'}!`);
    form.reset();
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

// =========================================
// 21. AÇÕES DO MODAL DE DETALHE
// =========================================

async function resolveTicket() {
  console.log(`[ACTION] 🏁 Finalizando ticket #${viewingTicketId}...`);

  const userId = getCurrentUserId();

  // ✅ usuario_id obrigatório no PUT
  const result = await apiRequest(
    'PUT',
    `/tickets/${viewingTicketId}?usuario_id=${userId}`,
    { status_id: mapStatusToApi('resolved') }
  );

  if (result) {
    showSuccess("✅ Ticket finalizado com sucesso!");
    await loadTickets();

    const updatedTicket = tickets.find(t => t.id === viewingTicketId);
    if (updatedTicket) {
      document.getElementById("detailStatusQuick").innerHTML = getStatusBadge(updatedTicket.status);
      document.getElementById("detailStatus").innerHTML      = getStatusBadge(updatedTicket.status);
      document.getElementById("detailStatusSelect").value   = updatedTicket.status;
    }
  } else {
    showError("❌ Erro ao tentar finalizar o ticket.");
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