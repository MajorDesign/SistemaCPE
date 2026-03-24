/**
 * CPE Control - Sistema de Gestão de Tickets
 * Cliente JavaScript para gerenciamento de tickets
 * API: http://127.0.0.1:8000/api
 */

// =========================================
// 1. VARIÁVEIS GLOBAIS
// =========================================

let tickets = [];
let filteredTickets = [];
let selectedTickets = new Set();
let users = [];
let currentPage = 1;
let itemsPerPage = 25;
let selectedTicketId = null;
let viewingTicketId = null;
let isLoadingTickets = false;
let isLoadingUsers = false;

const API_BASE = 'http://127.0.0.1:8000/api';
const API_TIMEOUT = 10000;

// =========================================
// 2. INICIALIZAÇÃO
// =========================================

document.addEventListener("DOMContentLoaded", async () => {
  console.log("[TICKETS] ⏳ Iniciando sistema de tickets...");
  
  try {
    const token = localStorage.getItem('cpe_token');
    const userStr = localStorage.getItem('cpe_user');
    
    console.log('[TICKETS] Token encontrado:', !!token);
    console.log('[TICKETS] User encontrado:', !!userStr);
    
    if (!token || !userStr) {
      console.error('[TICKETS] ❌ Dados de autenticação não encontrados!');
      showError('❌ Por favor, faça login novamente.');
      setTimeout(() => {
        window.location.href = '/SistemaCPE/web/login.html';
      }, 2000);
      return;
    }

    console.log('[TICKETS] ✅ Autenticação OK');

    setupEventListeners();
    await loadUsers();
    await loadTickets();
    
    console.log("[TICKETS] ✅ Sistema carregado com sucesso!");
    
  } catch (erro) {
    console.error('[TICKETS] ❌ Erro na inicialização:', erro);
    showError(`❌ Erro ao inicializar: ${erro.message}`);
  }
});

function setupEventListeners() {
  console.log("[TICKETS] 🔌 Configurando event listeners...");
  
  const elementos = {
    'searchInput': 'input',
    'statusFilter': 'change',
    'priorityFilter': 'change',
    'ticketForm': 'submit',
    'assignForm': 'submit',
    'detailReplyForm': 'submit',
    'detailInternalForm': 'submit',
    'selectAll': 'change'
  };

  const handlers = {
    'searchInput': applyFilters,
    'statusFilter': applyFilters,
    'priorityFilter': applyFilters,
    'ticketForm': handleFormSubmit,
    'assignForm': submitAssign,
    'detailReplyForm': submitDetailReply,
    'detailInternalForm': submitDetailInternal,
    'selectAll': (e) => toggleSelectAll(e.target)
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
// 3. REQUISIÇÕES À API
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
      method: method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    };

    if (body) {
      options.body = JSON.stringify(body);
    }

    console.log(`[API] 📤 ${method} ${endpoint}`);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);
    options.signal = controller.signal;
    
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
// 4. CARREGAR USUÁRIOS
// =========================================

async function loadUsers() {
  if (isLoadingUsers) return;
  isLoadingUsers = true;
  console.log("[USUARIOS] 📥 Carregando usuários da API...");
  
  try {
    // ✅ CORRIGIDO: de '/usuarios' para '/users'
    const data = await apiRequest('GET', '/users'); 
    
    if (!data || !Array.isArray(data)) {
      console.warn('[USUARIOS] ⚠️ Resposta inválida da API');
      users = [];
    } else {
      users = data.map(u => ({
        id: u.id,
        name: u.name || u.nome || 'Sem nome', // Corrigido para usar 'name' primeiro
        email: u.email || 'sem-email'
      }));
      console.log(`[USUARIOS] ✅ ${users.length} usuário(s) carregado(s)`);
    }
    
    populateUserDropdowns();
    debugUserDropdowns();
    
  } catch (error) {
    console.error('[USUARIOS] ❌ Erro ao carregar:', error);
    users = [];
  } finally {
    isLoadingUsers = false;
  }
}

function debugUserDropdowns() {
  console.log("\n========== DEBUG DROPDOWNS ==========");
  console.log(`[DEBUG] users.length:`, users.length);
  ["assignUser", "detailAssignSelect"].forEach(id => {
    const el = document.getElementById(id);
    console.log(`\n[DEBUG] Dropdown #${id}:`, el ? `Encontrado (${el.options.length} opções)` : 'NÃO ENCONTRADO');
  });
  console.log("====================================\n");
}

function populateUserDropdowns() {
  console.log("[USUARIOS] 🔍 Populando dropdowns...");
  
  const dropdownConfigs = [
    { id: "assignUser", placeholder: "Selecione um usuário..." },
    { id: "detailAssignSelect", placeholder: "Não atribuído" }
  ];

  const optionsHTML = users.map(u => `<option value="${u.id}">${u.name}</option>`).join("");

  dropdownConfigs.forEach(config => {
    const element = document.getElementById(config.id);
    if (element) {
      const placeholderHTML = `<option value="">${config.placeholder}</option>`;
      element.innerHTML = placeholderHTML + optionsHTML;
      console.log(`[USUARIOS] ✅ Dropdown #${config.id} preenchido com ${users.length} usuários.`);
    } else {
      console.error(`[USUARIOS] ❌ Elemento #${config.id} NÃO ENCONTRADO no DOM!`);
    }
  });
}

// =========================================
// 5. CARREGAR TICKETS
// =========================================

async function loadTickets() {
  if (isLoadingTickets) return;
  isLoadingTickets = true;
  console.log("[TICKETS] 📥 Carregando tickets...");
  
  try {
    const data = await apiRequest('GET', '/tickets');
    
    if (!data || !Array.isArray(data)) {
      console.warn('[TICKETS] ⚠️ Resposta inválida');
      tickets = [];
    } else {
      tickets = data.map(t => ({
        id: t.id,
        numero: t.numero || `#${t.id}`,
        title: t.assunto || 'Sem título',
        // ✅ CORRIGIDO: para usar os campos que a API realmente envia
        userName: t.solicitante_nome || "Desconhecido",
        email: t.solicitante_email || "sem-email",
        groupName: t.group_name || "Sem setor",
        priority: mapPriorityFromApi(t.prioridade_id),
        status: mapStatusFromApi(t.status_id),
        assignedTo: t.responsavel_id,
        assignedName: t.responsavel_nome || "Não atribuído",
        createdAt: formatDate(t.created_at),
        createdAtFull: t.created_at,
        updatedAt: formatDate(t.updated_at),
        updatedAtFull: t.updated_at,
        description: t.descricao_inicial || 'Sem descrição'
      }));
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
// 6. MAPEAR DADOS DA API
// =========================================

function mapPriorityFromApi(id) { return { 1: 'low', 2: 'medium', 3: 'high', 4: 'urgent' }[id] || 'medium'; }
function mapPriorityToApi(p) { return { 'low': 1, 'medium': 2, 'high': 3, 'urgent': 4 }[p] || 2; }
function mapStatusFromApi(id) { return { 1: 'open', 2: 'in-progress', 3: 'resolved', 4: 'closed' }[id] || 'open'; }
function mapStatusToApi(s) { return { 'open': 1, 'in-progress': 2, 'resolved': 3, 'closed': 4 }[s] || 1; }
function formatDate(d) { return d ? new Date(d).toLocaleDateString('pt-BR') : 'N/A'; }
function formatDateTime(d) { return d ? new Date(d).toLocaleString('pt-BR') : 'N/A'; }

// =========================================
// 7. FILTROS
// =========================================

function applyFilters() {
  const search = document.getElementById("searchInput")?.value?.toLowerCase().trim() || "";
  const status = document.getElementById("statusFilter")?.value || "";
  const priority = document.getElementById("priorityFilter")?.value || "";

  filteredTickets = tickets.filter(t => 
    (!status || t.status === status) &&
    (!priority || t.priority === priority) &&
    (!search || t.title.toLowerCase().includes(search) || t.userName.toLowerCase().includes(search) || t.numero.toLowerCase().includes(search))
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
// 8. RENDERIZAR TABELA E PAGINAÇÃO
// =========================================

function renderTable() {
  const body = document.getElementById("ticketsBody");
  if (!body) return;

  const pageTickets = filteredTickets.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  if (pageTickets.length === 0) {
    body.innerHTML = `<tr><td colspan="8" class="text-center text-muted py-4"><i class="bi bi-inbox"></i> Nenhum ticket encontrado</td></tr>`;
  } else {
    body.innerHTML = pageTickets.map(t => {
      const initial = t.userName.charAt(0).toUpperCase() || "?";
      const checked = selectedTickets.has(t.id) ? 'checked' : '';
      return `
        <tr class="ticket-row ${checked ? 'table-active' : ''}" data-ticket-id="${t.id}">
          <td onclick="event.stopPropagation()"><input type="checkbox" class="row-checkbox" value="${t.id}" onchange="toggleRowSelect(${t.id}, this);" ${checked}></td>
          <td onclick="openTicketDetail(${t.id})"><div class="d-flex align-items-center gap-2"><div class="avatar">${initial}</div><span>${t.userName}</span></div></td>
          <td onclick="openTicketDetail(${t.id})">${t.title}</td>
          <td>${getPriorityBadge(t.priority)}</td>
          <td>${getStatusBadge(t.status)}</td>
          <td><small>${t.assignedName !== "Não atribuído" ? t.assignedName : '-'}</small></td>
          <td><small>${t.createdAt}</small></td>
          <td>
            <button class="btn btn-sm btn-info" onclick="openTicketDetail(${t.id})" title="Visualizar"><i class="bi bi-eye"></i></button>
            <button class="btn btn-sm btn-danger" onclick="deleteTicketRow(${t.id})" title="Deletar"><i class="bi bi-trash"></i></button>
          </td>
        </tr>`;
    }).join("");
  }
  updatePagination();
}

function updatePagination() {
  const total = filteredTickets.length;
  const totalPages = Math.ceil(total / itemsPerPage) || 1;
  const start = total === 0 ? 0 : (currentPage - 1) * itemsPerPage + 1;
  const end = Math.min(currentPage * itemsPerPage, total);

  document.getElementById("totalItems").textContent = total;
  document.getElementById("totalPages").textContent = totalPages;
  document.getElementById("paginationText").textContent = `${start} a ${end} de ${total}`;
  document.getElementById("currentPage").value = currentPage;
}

function updateStatistics() {
  document.getElementById("totalTickets").textContent = tickets.length;
  document.getElementById("openTickets").textContent = tickets.filter(t => t.status === "open").length;
  document.getElementById("inProgressTickets").textContent = tickets.filter(t => t.status === "in-progress").length;
  document.getElementById("resolvedTickets").textContent = tickets.filter(t => t.status === "resolved").length;
}

// =========================================
// 9. SELEÇÃO
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
// 10. AÇÕES EM LOTE
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

  const userName = users.find(u => u.id == userId)?.name || "Desconhecido";
  console.log(`[ASSIGN] 👤 Atribuindo ${selectedTickets.size} ticket(s) para: ${userName}...`);
  
  let successes = 0;
  for (const ticketId of selectedTickets) {
    const result = await apiRequest('PUT', `/tickets/${ticketId}`, { responsavel_id: parseInt(userId) });
    if (result) successes++;
  }

  showSuccess(`✅ ${successes} ticket(s) atribuído(s) para ${userName}.`);
  bootstrap.Modal.getInstance(document.getElementById("assignModal"))?.hide();
  selectedTickets.clear();
  document.getElementById("selectAll").checked = false;
  await loadTickets();
}

// =========================================
// 11. AÇÕES NA LINHA E MODAL DE DETALHE
// =========================================

async function openTicketDetail(id) {
  const t = tickets.find(x => x.id === id);
  if (!t) {
    showError(`❌ Ticket #${id} não encontrado`);
    return;
  }

  viewingTicketId = id;
  console.log(`[DETAIL] 📖 Abrindo ticket #${id}...`, t);

  // Preencher todos os campos do modal
  document.getElementById("detailTitle").textContent = t.title;
  document.getElementById("detailId").textContent = t.numero;
  document.getElementById("detailDescription").textContent = t.description;
  document.getElementById("detailUserName").textContent = t.userName;
  document.getElementById("detailEmail").textContent = t.email;
  document.getElementById("detailStatusQuick").innerHTML = getStatusBadge(t.status);
  document.getElementById("detailAssignedName").textContent = t.assignedName;
  document.getElementById("detailUserNameDetail").textContent = t.userName;
  document.getElementById("detailEmailDetail").textContent = t.email;
  document.getElementById("detailGroup").textContent = t.groupName;
  document.getElementById("detailPriority").innerHTML = getPriorityBadge(t.priority);
  document.getElementById("detailStatus").innerHTML = getStatusBadge(t.status);
  document.getElementById("detailAssignedTo").textContent = t.assignedName;
  document.getElementById("detailCreatedAt").textContent = formatDateTime(t.createdAtFull);
  document.getElementById("detailUpdatedAt").textContent = formatDateTime(t.updatedAtFull);
  document.getElementById("detailStatusSelect").value = t.status;
  document.getElementById("detailAssignSelect").value = t.assignedTo || "";
  
  console.log('[DETAIL] ✅ Todos os campos do modal preenchidos.');

  await loadTicketComments(id);
  new bootstrap.Modal(document.getElementById("ticketDetailModal")).show();
}

function editTicketRow(id) {
  const t = tickets.find(x => x.id === id);
  if (!t) return;

  selectedTicketId = id;
  document.getElementById("ticketModalLabel").innerHTML = `<i class="bi bi-pencil-square"></i> Editar Ticket #${t.numero}`;
  document.getElementById("ticketTitle").value = t.title;
  document.getElementById("ticketDescription").value = t.description;
  document.getElementById("ticketPriority").value = t.priority;
  
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
  console.log(`[TICKETS] 🗑️ Deletando #${id}...`);
  const result = await apiRequest('DELETE', `/tickets/${id}`);
  if (result) {
    console.log(`[TICKETS] ✅ #${id} deletado`);
    return true;
  }
  showError(`❌ Erro ao deletar ticket #${id}`);
  return false;
}

// =========================================
// 12. NOVO/EDITAR TICKET
// =========================================

function openNewTicketModal() {
  selectedTicketId = null;
  document.getElementById("ticketForm").reset();
  document.getElementById("ticketModalLabel").innerHTML = `<i class="bi bi-plus-square"></i> Novo Ticket`;
  
  const user = JSON.parse(localStorage.getItem('cpe_user') || '{}');
  document.getElementById("ticketClient").value = user.name || user.usuario_nome || '';
  document.getElementById("ticketEmail").value = user.email || user.usuario_email || '';
  document.getElementById("ticketGroupName").value = user.group_name || user.grupo_nome || '';
  document.getElementById("ticketGroup").value = user.group_id || user.grupo_id || '';
  
  new bootstrap.Modal(document.getElementById("ticketModal")).show();
}

async function handleFormSubmit(e) {
  e.preventDefault();
  
  const title = document.getElementById("ticketTitle").value.trim();
  const description = document.getElementById("ticketDescription").value.trim();
  if (title.length < 3 || description.length < 5) {
    showError("❌ Assunto (mín 3) e Descrição (mín 5) são obrigatórios!");
    return;
  }

  const user = JSON.parse(localStorage.getItem('cpe_user') || '{}');
  const payload = {
    assunto: title,
    descricao_inicial: description,
    prioridade_id: mapPriorityToApi(document.getElementById("ticketPriority").value),
    group_id: user.group_id || user.grupo_id,
    solicitante_id: user.id || user.usuario_id,
    origem: 'web'
  };

  let result;
  if (selectedTicketId) {
    console.log(`[TICKET] ✏️ Editando #${selectedTicketId}...`);
    result = await apiRequest('PUT', `/tickets/${selectedTicketId}`, payload);
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
// 13. COMENTÁRIOS
// =========================================

async function loadTicketComments(ticketId) {
  console.log(`[COMENTARIOS] 📥 Carregando para ticket #${ticketId}...`);
  const data = await apiRequest('GET', `/ticket-interacoes/${ticketId}`);
  const container = document.getElementById("detailCommentsList");
  if (!container) return;

  if (!data || data.length === 0) {
    container.innerHTML = '<p class="text-muted text-center py-4">Nenhum comentário</p>';
    return;
  }

  container.innerHTML = data.map(c => `
    <div class="comment-item p-3 mb-2 rounded bg-light">
      <div class="d-flex justify-content-between align-items-center mb-2">
        <span class="fw-bold">${c.usuario_nome || 'Desconhecido'}</span>
        <div>
          <span class="badge ${c.publico ? 'bg-success' : 'bg-warning text-dark'} me-2">${c.publico ? 'RESPOSTA' : 'INTERNO'}</span>
          <span class="text-muted small">${formatDateTime(c.created_at)}</span>
        </div>
      </div>
      <p class="mb-0">${c.mensagem || '[Sem conteúdo]'}</p>
    </div>
  `).join("");
}

async function submitComment(form, isPublic) {
  const textEl = form.querySelector('textarea');
  const text = textEl?.value?.trim();
  if (!text || text.length < 3) { 
    showError("❌ Mensagem muito curta!"); 
    return; 
  }

  const user = JSON.parse(localStorage.getItem('cpe_user') || '{}');
  const payload = {
    ticket_id: viewingTicketId,
    usuario_id: user.id || user.usuario_id,
    mensagem: text,
    tipo: isPublic ? 'resposta' : 'interno',
    publico: isPublic ? 1 : 0
  };

  const result = await apiRequest('POST', '/ticket-interacoes', payload);
  if (result) {
    showSuccess(`✅ ${isPublic ? 'Resposta enviada' : 'Comentário salvo'}!`);
    form.reset();
    await loadTicketComments(viewingTicketId);
  }
}

function submitDetailReply(e) { e.preventDefault(); submitComment(e.target, true); }
function submitDetailInternal(e) { e.preventDefault(); submitComment(e.target, false); }

// =========================================
// 14. PAGINAÇÃO
// =========================================

function changeItemsPerPage(value) { itemsPerPage = parseInt(value); currentPage = 1; renderTable(); }
function previousPage() { if (currentPage > 1) { currentPage--; renderTable(); } }
function nextPage() { if (currentPage < Math.ceil(filteredTickets.length / itemsPerPage)) { currentPage++; renderTable(); } }
function goToPage(pageNum) {
  const num = parseInt(pageNum);
  const totalPages = Math.ceil(filteredTickets.length / itemsPerPage) || 1;
  if (num >= 1 && num <= totalPages) {
    currentPage = num;
    renderTable();
  }
}

// =========================================
// 15. BADGES
// =========================================

function getPriorityBadge(p) {
  const map = { 'low': "Baixa", 'medium': "Média", 'high': "Alta", 'urgent': "Urgente" };
  const classes = { 'low': "bg-info", 'medium': "bg-warning", 'high': "bg-danger", 'urgent': "bg-danger" };
  return `<span class="badge ${classes[p]}">${map[p] || p}</span>`;
}

function getStatusBadge(s) {
  const map = { 'open': "Aberto", 'in-progress': "Andamento", 'resolved': "Resolvido", 'closed': "Fechado" };
  const classes = { 'open': "bg-warning text-dark", 'in-progress': "bg-primary", 'resolved': "bg-success", 'closed': "bg-secondary" };
  return `<span class="badge ${classes[s]}">${map[s] || s}</span>`;
}

// =========================================
// 16. FUNÇÕES DE ABAS (DETAIL MODAL)
// =========================================

function switchTab(event, tab) {
  event.preventDefault();
  document.querySelectorAll('.ticket-detail-tab, .ticket-detail-content').forEach(el => el.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById(`tab-${tab}`)?.classList.add('active');
}

function switchReplyMode(event, mode) {
  event.preventDefault();
  document.querySelectorAll('.reply-menu-tab, .reply-mode').forEach(el => el.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById(`reply-${mode}`)?.classList.add('active');
}

async function resolveTicket() {
  console.log(`[ACTION] 🏁 Finalizando ticket #${viewingTicketId}...`);
  
  const newStatus = 'resolved';
  const result = await apiRequest('PUT', `/tickets/${viewingTicketId}`, { status_id: mapStatusToApi(newStatus) });
  
  if (result) {
    showSuccess("✅ Ticket finalizado com sucesso!");
    
    await loadTickets(); 

    const updatedTicket = tickets.find(t => t.id === viewingTicketId);
    if (updatedTicket) {
      // Atualiza a UI do modal sem reabri-lo
      document.getElementById("detailStatusQuick").innerHTML = getStatusBadge(updatedTicket.status);
      document.getElementById("detailStatus").innerHTML = getStatusBadge(updatedTicket.status);
      document.getElementById("detailStatusSelect").value = updatedTicket.status;
      console.log(`[DETAIL] ✅ UI do modal atualizada para o status: ${updatedTicket.status}`);
    }
  } else {
    showError("❌ Erro ao tentar finalizar o ticket.");
  }
}

async function updateTicketStatus() {
  const newStatus = document.getElementById("detailStatusSelect")?.value;
  if (!newStatus) { 
    showError("❌ Selecione um status"); 
    return; 
  }
  
  const result = await apiRequest('PUT', `/tickets/${viewingTicketId}`, { status_id: mapStatusToApi(newStatus) });
  
  if (result) {
    showSuccess("✅ Status atualizado com sucesso!");
    
    // 1. Atualiza a lista de tickets em segundo plano
    await loadTickets(); 

    // 2. Encontra o ticket atualizado na nova lista
    const updatedTicket = tickets.find(t => t.id === viewingTicketId);
    if (updatedTicket) {
      // 3. Atualiza apenas os campos de status visíveis no modal
      document.getElementById("detailStatusQuick").innerHTML = getStatusBadge(updatedTicket.status);
      document.getElementById("detailStatus").innerHTML = getStatusBadge(updatedTicket.status);
      console.log(`[DETAIL] ✅ UI do modal atualizada para o status: ${updatedTicket.status}`);
    }
  } else {
    // Se falhar, reverta o dropdown para o valor original
    const originalTicket = tickets.find(t => t.id === viewingTicketId);
    if(originalTicket) {
        document.getElementById("detailStatusSelect").value = originalTicket.status;
    }
  }
}

async function updateTicketAssign() {
  const userId = document.getElementById("detailAssignSelect")?.value;
  // Não precisa de validação aqui, pois selecionar "Não atribuído" (valor vazio) é uma ação válida.
  
  const result = await apiRequest('PUT', `/tickets/${viewingTicketId}`, { 
    // Envia null se o valor for vazio, ou o número do ID.
    responsavel_id: userId ? parseInt(userId) : null 
  });

  if (result) {
    showSuccess("✅ Atribuição atualizada com sucesso!");
    
    // 1. Atualiza a lista de tickets em segundo plano (para a tabela principal)
    await loadTickets(); 

    // 2. Encontra o ticket atualizado na nova lista
    const updatedTicket = tickets.find(t => t.id === viewingTicketId);
    if (updatedTicket) {
      // 3. Atualiza apenas os campos visíveis no modal, sem reabri-lo
      document.getElementById("detailAssignedName").textContent = updatedTicket.assignedName;
      document.getElementById("detailAssignedTo").textContent = updatedTicket.assignedName;
      console.log(`[DETAIL] ✅ UI do modal atualizada para o responsável: ${updatedTicket.assignedName}`);
    }
  } else {
    // Se falhar, reverta o dropdown para o valor original
    const originalTicket = tickets.find(t => t.id === viewingTicketId);
    if(originalTicket) {
        document.getElementById("detailAssignSelect").value = originalTicket.assignedTo || "";
    }
  }
}

// =========================================
// 17. ALERTAS
// =========================================

function showAlert(id, msg) {
  const box = document.getElementById(id);
  const messageEl = box?.querySelector('span');
  if (box && messageEl) {
    messageEl.innerHTML = msg;
    box.classList.remove("d-none");
    setTimeout(() => box.classList.add("d-none"), 5000);
  }
}

function showError(msg) {
  showAlert("alertBox", msg);
  console.error(`[ALERTA] ${msg}`);
}

function showSuccess(msg) {
  showAlert("successBox", msg);
  console.log(`[ALERTA] ${msg}`);
}

console.log("[TICKETS] 🎉 Script carregado completamente!");