let tickets = [];
let filteredTickets = [];
let selectedTickets = new Set();
let currentPage = 1;
let itemsPerPage = 25;
let selectedTicketId = null;
let viewingTicketId = null;

// Sistema de detecção de duplo clique
let lastClickedRow = null;
let lastClickTime = 0;
const DOUBLE_CLICK_DELAY = 300;

// =========================================
// INICIALIZAÇÃO
// =========================================

document.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    loadTickets();
    setupEventListeners();
    console.log("[TICKETS] ✅ Sistema carregado com sucesso");
  }, 300);
});

function setupEventListeners() {
  document.getElementById("searchInput")?.addEventListener("input", applyFilters);
  document.getElementById("dateFilter")?.addEventListener("change", applyFilters);
  document.getElementById("statusFilter")?.addEventListener("change", applyFilters);
  document.getElementById("priorityFilter")?.addEventListener("change", applyFilters);
  document.getElementById("groupFilter")?.addEventListener("change", applyFilters);
  document.getElementById("ticketForm")?.addEventListener("submit", handleFormSubmit);
  document.getElementById("assignForm")?.addEventListener("submit", submitAssign);
  document.getElementById("detailReplyForm")?.addEventListener("submit", submitDetailReply);
  document.getElementById("detailInternalForm")?.addEventListener("submit", submitDetailInternal);
  document.getElementById("selectAll")?.addEventListener("change", toggleSelectAll);
}

// =========================================
// CARREGAR E RENDERIZAR TICKETS
// =========================================

function loadTickets() {
  tickets = [
    {
      id: 1234,
      title: "Problema com login na plataforma",
      userName: "João Silva",
      email: "joao.silva@empresa.com",
      group: "suporte",
      priority: "high",
      status: "open",
      assignedTo: null,
      createdAt: "2026-03-09",
      updatedAt: "2026-03-09 10:30",
      description: "Não consigo fazer login. Já tentei recuperar a senha mas não funciona.",
      comments: [
        {id: 1, author: "Sistema", type: "system", text: "Ticket criado", date: "2026-03-09 10:00"}
      ]
    },
    {
      id: 1233,
      title: "Erro ao processar pagamento",
      userName: "Maria Santos",
      email: "maria.santos@empresa.com",
      group: "vendas",
      priority: "urgent",
      status: "in-progress",
      assignedTo: "joao.silva",
      createdAt: "2026-03-09",
      updatedAt: "2026-03-09 09:15",
      description: "Gateway retornando erro 500 em todas as transações.",
      comments: [
        {id: 1, author: "Você", type: "internal", text: "Verificar logs do gateway", date: "2026-03-09 11:00"},
        {id: 2, author: "João Silva", type: "public", text: "Estamos investigando o problema", date: "2026-03-09 11:30"}
      ]
    },
    {
      id: 1232,
      title: "Dúvida sobre funcionalidade de relatórios",
      userName: "Pedro Costa",
      email: "pedro.costa@empresa.com",
      group: "administrativo",
      priority: "medium",
      status: "open",
      assignedTo: null,
      createdAt: "2026-03-07",
      updatedAt: "2026-03-07 14:20",
      description: "Como exportar relatórios em Excel?",
      comments: []
    },
    {
      id: 1231,
      title: "Solicitação de integração com Zapier",
      userName: "Ana Oliveira",
      email: "ana.oliveira@empresa.com",
      group: "desenvolvimento",
      priority: "low",
      status: "resolved",
      assignedTo: "maria.santos",
      createdAt: "2026-03-08",
      updatedAt: "2026-03-09 08:00",
      description: "Integração com Zapier para automações.",
      comments: []
    },
    {
      id: 1230,
      title: "Exportação de dados não funciona",
      userName: "Carlos Mendes",
      email: "carlos.mendes@empresa.com",
      group: "financeiro",
      priority: "high",
      status: "in-progress",
      assignedTo: "pedro.costa",
      createdAt: "2026-03-09",
      updatedAt: "2026-03-09 08:00",
      description: "Grande volume de dados gera erro.",
      comments: []
    }
  ];

  applyFilters();
  updateStatistics();
}

function applyFilters() {
  let filtered = [...tickets];
  const search = document.getElementById("searchInput")?.value?.toLowerCase() || "";
  const date = document.getElementById("dateFilter")?.value || "";
  const status = document.getElementById("statusFilter")?.value || "";
  const priority = document.getElementById("priorityFilter")?.value || "";
  const group = document.getElementById("groupFilter")?.value || "";

  if (search) {
    filtered = filtered.filter(t =>
      t.title.toLowerCase().includes(search) ||
      t.userName.toLowerCase().includes(search) ||
      t.email.toLowerCase().includes(search)
    );
  }
  if (date) filtered = filtered.filter(t => t.createdAt === date);
  if (status) filtered = filtered.filter(t => t.status === status);
  if (priority) filtered = filtered.filter(t => t.priority === priority);
  if (group) filtered = filtered.filter(t => t.group === group);

  filteredTickets = filtered;
  currentPage = 1;
  renderTable();
}

function renderTable() {
  const startIdx = (currentPage - 1) * itemsPerPage;
  const endIdx = startIdx + itemsPerPage;
  const pageTickets = filteredTickets.slice(startIdx, endIdx);
  const body = document.getElementById("ticketsBody");

  if (pageTickets.length === 0) {
    body.innerHTML = `<tr><td colspan="8" class="text-center text-muted py-4">Nenhum ticket encontrado</td></tr>`;
    updatePagination();
    return;
  }

  body.innerHTML = pageTickets.map(t => {
    const initial = t.userName.charAt(0).toUpperCase();
    const checked = selectedTickets.has(t.id) ? 'checked' : '';
    const assignedLabel = t.assignedTo ? getUserLabel(t.assignedTo) : '<span class="text-muted">-</span>';
    
    return `
      <tr class="ticket-row" data-ticket-id="${t.id}" ${selectedTickets.has(t.id) ? 'class="ticket-row table-active"' : 'class="ticket-row"'}>
        <td onclick="event.stopPropagation()">
          <input type="checkbox" class="row-checkbox" value="${t.id}" onchange="toggleRowSelect(${t.id}, this);" ${checked}>
        </td>
        <td onclick="detectDoubleClick(event, ${t.id})">
          <div class="d-flex align-items-center gap-2">
            <div class="avatar" style="background:linear-gradient(135deg, #667eea, #764ba2); color:#fff; width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:12px;">
              ${initial}
            </div>
            <span>${t.userName}</span>
          </div>
        </td>
        <td onclick="detectDoubleClick(event, ${t.id})">${t.title}</td>
        <td onclick="event.stopPropagation()">${getPriorityBadge(t.priority)}</td>
        <td onclick="event.stopPropagation()">${getStatusBadge(t.status)}</td>
        <td onclick="event.stopPropagation()">${assignedLabel}</td>
        <td onclick="event.stopPropagation()"><small>${t.createdAt}</small></td>
        <td onclick="event.stopPropagation()">
          <div class="action-buttons">
            <button class="btn btn-sm btn-info" onclick="openTicketDetail(${t.id})" title="Visualizar">
              <i class="bi bi-eye"></i>
            </button>
            <button class="btn btn-sm btn-warning" onclick="editTicketRow(${t.id})" title="Editar">
              <i class="bi bi-pencil"></i>
            </button>
            <button class="btn btn-sm btn-danger" onclick="deleteTicketRow(${t.id})" title="Deletar">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join("");

  updatePagination();
}

function updatePagination() {
  const totalPages = Math.ceil(filteredTickets.length / itemsPerPage);
  const startIdx = (currentPage - 1) * itemsPerPage + 1;
  const endIdx = Math.min(currentPage * itemsPerPage, filteredTickets.length);

  document.getElementById("totalItems").textContent = filteredTickets.length;
  document.getElementById("totalPages").textContent = totalPages || 1;
  document.getElementById("currentPage").value = currentPage;
  document.getElementById("paginationText").textContent = `${filteredTickets.length === 0 ? 0 : startIdx} a ${endIdx} de ${filteredTickets.length}`;
}

function updateStatistics() {
  document.getElementById("totalTickets").textContent = tickets.length;
  document.getElementById("openTickets").textContent = tickets.filter(t => t.status === "open").length;
  document.getElementById("inProgressTickets").textContent = tickets.filter(t => t.status === "in-progress").length;
  document.getElementById("resolvedTickets").textContent = tickets.filter(t => t.status === "resolved").length;
}

// =========================================
// DETECÇÃO DE DUPLO CLIQUE
// =========================================

function detectDoubleClick(event, ticketId) {
  const now = Date.now();
  const currentRow = ticketId;

  // Se foi no mesmo ticket e dentro do tempo permitido
  if (lastClickedRow === currentRow && now - lastClickTime < DOUBLE_CLICK_DELAY) {
    console.log("✅ Duplo clique detectado no ticket:", ticketId);
    openTicketDetail(ticketId);
    lastClickedRow = null;
    lastClickTime = 0;
  } else {
    // Primeiro clique
    lastClickedRow = currentRow;
    lastClickTime = now;
  }
}

// =========================================
// SELEÇÃO DE TICKETS
// =========================================

function toggleSelectAll(checkbox) {
  const checkboxes = document.querySelectorAll('.row-checkbox');
  checkboxes.forEach(cb => {
    cb.checked = checkbox.checked;
    selectedTickets[checkbox.checked ? 'add' : 'delete'](parseInt(cb.value));
  });
  updateRowSelection();
}

function toggleRowSelect(id, checkbox) {
  checkbox.checked ? selectedTickets.add(id) : selectedTickets.delete(id);
  updateRowSelection();
}

function updateRowSelection() {
  document.querySelectorAll('.ticket-row').forEach(row => {
    const checkbox = row.querySelector('.row-checkbox');
    if (checkbox?.checked) {
      row.classList.add('table-active');
    } else {
      row.classList.remove('table-active');
    }
  });

  // Mostrar/Esconder botão Responder
  const respondBtn = document.getElementById('respondBtn');
  if (selectedTickets.size === 1) {
    respondBtn.style.display = 'inline-block';
  } else {
    respondBtn.style.display = 'none';
  }
}

// =========================================
// AÇÕES EM LOTE
// =========================================

function editSelected() {
  if (selectedTickets.size === 0) { 
    showError("Selecione um ticket!"); 
    return; 
  }
  if (selectedTickets.size > 1) { 
    showError("Selecione apenas um!"); 
    return; 
  }
  
  const ticketId = Array.from(selectedTickets)[0];
  editTicketRow(ticketId);
}

function deleteSelected() {
  if (selectedTickets.size === 0) { 
    showError("Selecione um ticket!"); 
    return; 
  }
  
  if (confirm(`Deletar ${selectedTickets.size} ticket(s)?`)) {
    selectedTickets.forEach(id => {
      const idx = tickets.findIndex(t => t.id === id);
      if (idx !== -1) tickets.splice(idx, 1);
    });
    selectedTickets.clear();
    document.getElementById("selectAll").checked = false;
    showSuccess(`Ticket(s) deletado(s)!`);
    applyFilters();
    updateStatistics();
  }
}

function assignSelected() {
  if (selectedTickets.size === 0) { 
    showError("Selecione um ticket!"); 
    return; 
  }
  document.getElementById("assignUser").value = "";
  new bootstrap.Modal(document.getElementById("assignModal")).show();
}

function respondSelected() {
  if (selectedTickets.size !== 1) { 
    showError("Selecione um ticket!"); 
    return; 
  }
  
  const ticketId = Array.from(selectedTickets)[0];
  openTicketDetail(ticketId);
}

// =========================================
// AÇÕES NA LINHA (BOTÕES)
// =========================================

function openTicketDetail(id) {
  const t = tickets.find(x => x.id === id);
  if (!t) return;

  viewingTicketId = id;

  // Preencher header
  document.getElementById("detailTitle").textContent = t.title;
  document.getElementById("detailId").textContent = `#${t.id}`;

  // Preencher info rápida do chat
  document.getElementById("chatUserName").textContent = t.userName;
  document.getElementById("chatEmail").textContent = t.email;
  document.getElementById("chatAssigned").textContent = t.assignedTo ? getUserLabel(t.assignedTo) : "Não atribuído";
  
  const chatStatusEl = document.getElementById("chatStatus");
  chatStatusEl.innerHTML = getStatusBadge(t.status);

  // Preencher descrição
  document.getElementById("detailDescription").textContent = t.description;

  // Preencher comentários
  renderCommentsList(t.comments);

  // Preencher aba detalhes
  document.getElementById("detailUserName").textContent = t.userName;
  document.getElementById("detailEmail").textContent = t.email;
  document.getElementById("detailGroup").textContent = getGroupLabel(t.group);
  
  document.getElementById("detailPriority").innerHTML = getPriorityBadge(t.priority);
  document.getElementById("detailStatus").innerHTML = getStatusBadge(t.status);
  
  document.getElementById("detailAssignedTo").textContent = t.assignedTo ? getUserLabel(t.assignedTo) : "Não atribuído";
  document.getElementById("detailCreatedAt").textContent = t.createdAt;
  document.getElementById("detailUpdatedAt").textContent = t.updatedAt;

  // Preencher selects da aba ações
  document.getElementById("detailStatusSelect").value = t.status;
  document.getElementById("detailGroupSelect").value = t.group;
  document.getElementById("detailAssignSelect").value = t.assignedTo || "";

  // Limpar formulários de resposta
  document.getElementById("detailReplyForm").reset();
  document.getElementById("detailInternalForm").reset();

  // Abrir modal e ir para a aba de chat
  const modal = new bootstrap.Modal(document.getElementById("ticketDetailModal"));
  modal.show();

  // Focar no textarea de resposta
  setTimeout(() => {
    document.getElementById('detailReplyText').focus();
  }, 500);
}

function editTicketRow(id) {
  const t = tickets.find(x => x.id === id);
  if (!t) return;

  selectedTicketId = id;
  document.getElementById("ticketModalLabel").innerHTML = '<i class="bi bi-pencil-square"></i> Editar Ticket';
  document.getElementById("ticketTitle").value = t.title;
  document.getElementById("ticketDescription").value = t.description;
  document.getElementById("ticketClient").value = t.userName;
  document.getElementById("ticketEmail").value = t.email;
  document.getElementById("ticketGroup").value = t.group;
  document.getElementById("ticketPriority").value = t.priority;
  document.getElementById("submitBtn").textContent = 'Atualizar';
  
  new bootstrap.Modal(document.getElementById("ticketModal")).show();
}

function deleteTicketRow(id) {
  const t = tickets.find(x => x.id === id);
  if (!t) return;

  if (confirm(`Deletar "${t.title}"?`)) {
    tickets = tickets.filter(x => x.id !== id);
    showSuccess("Ticket deletado!");
    applyFilters();
    updateStatistics();
  }
}

// =========================================
// MODAL DE NOVO TICKET
// =========================================

function openNewTicketModal() {
  selectedTicketId = null;
  document.getElementById("ticketModalLabel").innerHTML = '<i class="bi bi-plus-square"></i> Novo Ticket';
  document.getElementById("ticketForm").reset();
  document.getElementById("submitBtn").textContent = 'Criar';
  new bootstrap.Modal(document.getElementById("ticketModal")).show();
}

// =========================================
// ABAS E MODO DE RESPOSTA
// =========================================

function switchTab(event, tab) {
  event.preventDefault();
  
  document.querySelectorAll('.ticket-detail-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.ticket-detail-content').forEach(c => c.classList.remove('active'));

  event.target.classList.add('active');
  document.getElementById(`tab-${tab}`).classList.add('active');
}

function switchReplyMode(event, mode) {
  event.preventDefault();
  
  document.querySelectorAll('.reply-menu-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.reply-mode').forEach(m => m.classList.remove('active'));

  event.target.classList.add('active');
  document.getElementById(`reply-${mode}`).classList.add('active');
}

// =========================================
// COMENTÁRIOS
// =========================================

function renderCommentsList(comments) {
  const container = document.getElementById("detailCommentsList");
  
  if (!comments || comments.length === 0) {
    container.innerHTML = '<p class="text-muted text-center py-4"><i class="bi bi-chat-dots"></i> Nenhum comentário ainda</p>';
    return;
  }

  container.innerHTML = comments.map(c => {
    let badgeClass = 'bg-secondary';
    let borderClass = '';

    if (c.type === 'internal') {
      badgeClass = 'bg-warning text-dark';
      borderClass = 'internal';
    } else if (c.type === 'public') {
      badgeClass = 'bg-success text-white';
      borderClass = 'public';
    }

    return `
      <div class="comment-item ${borderClass}">
        <div class="comment-header">
          <span class="comment-author">${c.author}</span>
          <span class="comment-type-badge ${badgeClass}">
            ${c.type === 'internal' ? 'INTERNO' : c.type === 'public' ? 'RESPOSTA' : 'SISTEMA'}
          </span>
          <span class="comment-date">${c.date}</span>
        </div>
        <p class="comment-text">${c.text}</p>
      </div>
    `;
  }).join("");
}

function submitDetailReply(e) {
  e.preventDefault();
  const text = document.getElementById("detailReplyText").value.trim();

  if (!text) { 
    showError("Digite uma resposta!"); 
    return; 
  }

  const t = tickets.find(x => x.id === viewingTicketId);
  if (!t) return;

  if (!t.comments) t.comments = [];

  const newComment = {
    id: Date.now(),
    author: "Você",
    type: "public",
    text: text,
    date: new Date().toLocaleString('pt-BR')
  };

  t.comments.push(newComment);
  t.updatedAt = new Date().toLocaleString('pt-BR');
  if (t.status === 'open') t.status = 'in-progress';

  showSuccess("Resposta enviada para o usuário!");
  document.getElementById("detailReplyForm").reset();
  renderCommentsList(t.comments);
  applyFilters();
  updateStatistics();
  document.getElementById('detailReplyText').focus();
}

function submitDetailInternal(e) {
  e.preventDefault();
  const text = document.getElementById("detailInternalText").value.trim();

  if (!text) { 
    showError("Digite um comentário!"); 
    return; 
  }

  const t = tickets.find(x => x.id === viewingTicketId);
  if (!t) return;

  if (!t.comments) t.comments = [];

  const newComment = {
    id: Date.now(),
    author: "Você",
    type: "internal",
    text: text,
    date: new Date().toLocaleString('pt-BR')
  };

  t.comments.push(newComment);
  t.updatedAt = new Date().toLocaleString('pt-BR');

  showSuccess("Comentário interno salvo!");
  document.getElementById("detailInternalForm").reset();
  renderCommentsList(t.comments);
  applyFilters();
}

// =========================================
// AÇÕES DO MODAL DETAIL
// =========================================

function updateTicketStatus() {
  const t = tickets.find(x => x.id === viewingTicketId);
  if (!t) return;

  const newStatus = document.getElementById("detailStatusSelect").value;
  t.status = newStatus;
  t.updatedAt = new Date().toLocaleString('pt-BR');
  
  showSuccess("Status atualizado!");
  applyFilters();
  updateStatistics();
}

function updateTicketGroup() {
  const t = tickets.find(x => x.id === viewingTicketId);
  if (!t) return;

  const newGroup = document.getElementById("detailGroupSelect").value;
  if (!newGroup) { 
    showError("Selecione um setor!"); 
    return; 
  }

  t.group = newGroup;
  t.updatedAt = new Date().toLocaleString('pt-BR');
  
  showSuccess("Ticket transferido!");
  applyFilters();
  updateStatistics();
}

function updateTicketAssign() {
  const t = tickets.find(x => x.id === viewingTicketId);
  if (!t) return;

  const newAssign = document.getElementById("detailAssignSelect").value;
  t.assignedTo = newAssign || null;
  t.updatedAt = new Date().toLocaleString('pt-BR');
  
  showSuccess("Atribuição atualizada!");
  applyFilters();
  updateStatistics();
}

function deleteViewingTicket() {
  const t = tickets.find(x => x.id === viewingTicketId);
  if (!t) return;
  
  if (confirm(`Deletar "${t.title}"?`)) {
    tickets = tickets.filter(x => x.id !== viewingTicketId);
    showSuccess("Ticket deletado!");
    bootstrap.Modal.getInstance(document.getElementById("ticketDetailModal"))?.hide();
    applyFilters();
    updateStatistics();
  }
}

// =========================================
// FORMULÁRIOS
// =========================================

function submitAssign(e) {
  e.preventDefault();
  const user = document.getElementById("assignUser").value.trim();
  if (!user) { 
    showError("Selecione um usuário!"); 
    return; 
  }

  selectedTickets.forEach(id => {
    const t = tickets.find(x => x.id === id);
    if (t) {
      t.assignedTo = user;
      t.updatedAt = new Date().toLocaleString('pt-BR');
    }
  });

  showSuccess(`${selectedTickets.size} ticket(s) atribuído(s)!`);
  bootstrap.Modal.getInstance(document.getElementById("assignModal"))?.hide();
  selectedTickets.clear();
  document.getElementById("selectAll").checked = false;
  applyFilters();
  updateStatistics();
}

function handleFormSubmit(e) {
  e.preventDefault();
  const title = document.getElementById("ticketTitle").value.trim();
  const userName = document.getElementById("ticketClient").value.trim();
  const email = document.getElementById("ticketEmail").value.trim();
  const group = document.getElementById("ticketGroup").value;
  const priority = document.getElementById("ticketPriority").value;
  const description = document.getElementById("ticketDescription").value.trim();

  if (!title || !userName || !email || !group || !priority) {
    showError("Preencha todos os campos obrigatórios!");
    return;
  }

  const today = new Date().toISOString().split('T')[0];
  const now = new Date().toLocaleString('pt-BR');

  if (selectedTicketId) {
    // EDITAR
    const t = tickets.find(x => x.id === selectedTicketId);
    if (t) {
      t.title = title;
      t.description = description;
      t.userName = userName;
      t.email = email;
      t.group = group;
      t.priority = priority;
      t.updatedAt = now;
      showSuccess("Ticket atualizado!");
    }
  } else {
    // CRIAR NOVO
    tickets.push({
      id: Math.max(...tickets.map(t => t.id), 0) + 1,
      title,
      description,
      userName,
      email,
      group,
      priority,
      status: "open",
      assignedTo: null,
      createdAt: today,
      updatedAt: now,
      comments: []
    });
    showSuccess("Ticket criado com sucesso!");
  }

  bootstrap.Modal.getInstance(document.getElementById("ticketModal"))?.hide();
  selectedTicketId = null;
  document.getElementById("ticketForm").reset();
  applyFilters();
  updateStatistics();
}

// =========================================
// FILTROS E PAGINAÇÃO
// =========================================

function toggleAdvancedFilters() {
  document.getElementById("advancedFilters").classList.toggle("d-none");
}

function clearFilters() {
  document.getElementById("searchInput").value = "";
  document.getElementById("dateFilter").value = "";
  document.getElementById("statusFilter").value = "";
  document.getElementById("priorityFilter").value = "";
  document.getElementById("groupFilter").value = "";
  applyFilters();
}

function changeItemsPerPage(value) {
  itemsPerPage = parseInt(value);
  currentPage = 1;
  renderTable();
}

function previousPage() {
  if (currentPage > 1) { 
    currentPage--; 
    renderTable(); 
  }
}

function nextPage() {
  if (currentPage < Math.ceil(filteredTickets.length / itemsPerPage)) { 
    currentPage++; 
    renderTable(); 
  }
}

function goToPage(page) {
  page = parseInt(page);
  const maxPages = Math.ceil(filteredTickets.length / itemsPerPage);
  if (page >= 1 && page <= maxPages) { 
    currentPage = page; 
    renderTable(); 
  }
}

// =========================================
// HELPERS - LABELS E BADGES
// =========================================

function getPriorityLabel(p) {
  return {
    low: "Baixa", 
    medium: "Média", 
    high: "Alta", 
    urgent: "Urgente"
  }[p] || p;
}

function getPriorityBadge(p) {
  const classes = {
    low: "bg-info",
    medium: "bg-warning",
    high: "bg-danger",
    urgent: "bg-danger"
  };
  return `<span class="badge ${classes[p] || 'bg-secondary'}">${getPriorityLabel(p)}</span>`;
}

function getStatusLabel(s) {
  return {
    open: "Aberto", 
    "in-progress": "Andamento", 
    resolved: "Resolvido", 
    closed: "Fechado"
  }[s] || s;
}

function getStatusBadge(s) {
  const classes = {
    open: "bg-warning text-dark",
    "in-progress": "bg-primary",
    resolved: "bg-success",
    closed: "bg-secondary"
  };
  return `<span class="badge ${classes[s] || 'bg-secondary'}">${getStatusLabel(s)}</span>`;
}

function getGroupLabel(g) {
  return {
    suporte: "Suporte Técnico", 
    vendas: "Vendas", 
    financeiro: "Financeiro", 
    administrativo: "Administrativo", 
    desenvolvimento: "Desenvolvimento"
  }[g] || g;
}

function getUserLabel(u) {
  const users = {
    "joao.silva": "João Silva",
    "maria.santos": "Maria Santos",
    "pedro.costa": "Pedro Costa",
    "ana.oliveira": "Ana Oliveira",
    "carlos.mendes": "Carlos Mendes",
    "me": "Você"
  };
  return users[u] || u;
}

// =========================================
// ALERTAS
// =========================================

function showError(msg) {
  const box = document.getElementById("alertBox");
  document.getElementById("alertMessage").textContent = msg;
  box.classList.remove("d-none");
  setTimeout(() => box.classList.add("d-none"), 5000);
}

function showSuccess(msg) {
  const box = document.getElementById("successBox");
  document.getElementById("successMessage").textContent = msg;
  box.classList.remove("d-none");
  setTimeout(() => box.classList.add("d-none"), 5000);
}