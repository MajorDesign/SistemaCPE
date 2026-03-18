console.log("[PASSWORD-VAULT.JS] Módulo carregado");

// =========================================
// ⚙️ VARIÁVEIS GLOBAIS
// =========================================

let passwords = [];
let groups = [];
let selectedPasswordId = null;
let currentGroupFilter = "";
let currentUser = null;

// =========================================
// 🔄 INIT PAGE
// =========================================

document.addEventListener("DOMContentLoaded", async () => {
  console.log("[VAULT] Inicializando página...");
  
  try {
    // ✅ Esconder loading e mostrar conteúdo
    const loadingPage = document.getElementById("loadingPage");
    const containerMain = document.querySelector(".container-main");
    
    if (loadingPage) loadingPage.style.display = "flex";
    if (containerMain) containerMain.style.display = "none";

    // ✅ Proteger página - obtém usuário autenticado
    currentUser = await initPageAuth("PASSWORD-VAULT");
    if (!currentUser) {
      console.error("[VAULT] Usuário não autenticado");
      return;
    }

    console.log("[VAULT] ✓ Usuário autenticado:", currentUser.name);

    // ✅ Carrega dados
    await loadGroups();
    await loadPasswords();

    // ✅ Setup event listeners
    setupEventListeners();

    // ✅ Mostrar conteúdo
    if (loadingPage) loadingPage.style.display = "none";
    if (containerMain) containerMain.style.display = "flex";

    console.log("[VAULT] ✓ Página inicializada com sucesso");

  } catch (err) {
    console.error("[VAULT] ✗ Erro ao inicializar:", err.message);
    showError("Erro ao inicializar página: " + err.message);
  }
});

// =========================================
// 👥 CARREGAR GRUPOS
// =========================================

async function loadGroups() {
  try {
    console.log("[VAULT/GROUPS] Carregando grupos da API...");

    const response = await apiGetPasswordGroups();
    
    console.log("[VAULT/GROUPS] Resposta recebida:", response);
    
    // ✅ A resposta pode vir de 3 formas:
    // 1. Como array direto: [{ id: 1, name: "Grupo 1" }]
    // 2. Como objeto com success e groups: { success: true, groups: [...] }
    // 3. Como objeto com data: { data: [...] }
    
    let groupsList = [];
    
    if (Array.isArray(response)) {
      groupsList = response;
    } else if (response && response.groups && Array.isArray(response.groups)) {
      groupsList = response.groups;
    } else if (response && response.data && Array.isArray(response.data)) {
      groupsList = response.data;
    } else if (response && Array.isArray(response)) {
      groupsList = response;
    }

    if (!Array.isArray(groupsList) || groupsList.length === 0) {
      console.warn("[VAULT/GROUPS] Nenhum grupo encontrado");
      groups = [];
    } else {
      groups = groupsList;
      console.log("[VAULT/GROUPS] ✓", groups.length, "grupos carregados:", groups);
    }

    // ✅ Popula o select de grupos no modal
    populateGroupSelect();

    // ✅ Renderiza pills de grupos
    renderGroupPills();

  } catch (err) {
    console.error("[VAULT/GROUPS] ✗ Erro:", err.message);
    console.error("[VAULT/GROUPS] Stack:", err.stack);
    showError("Erro ao carregar grupos: " + err.message);
    groups = [];
  }
}

// =========================================
// 📋 CARREGAR SENHAS
// =========================================

async function loadPasswords() {
  try {
    console.log("[VAULT/LOAD] Carregando senhas da API...");

    const response = await apiGetPasswords();
    
    if (!response || !Array.isArray(response)) {
      console.warn("[VAULT/LOAD] Resposta inválida da API");
      passwords = [];
      renderPasswords([]);
      updateStatistics();
      return;
    }

    passwords = response.map(pwd => ({
      id: pwd.id,
      client: pwd.client,
      email: pwd.email,
      description: pwd.description,
      password: pwd.password,
      link: pwd.link,
      observation: pwd.observation,
      group_id: pwd.group_id,
      group_name: groups.find(g => g.id === pwd.group_id)?.name || null,
      is_public: pwd.is_public,
      created_at: pwd.created_at
    }));

    console.log("[VAULT/LOAD] ✓", passwords.length, "senhas carregadas");
    renderPasswords(filterPasswords());
    updateStatistics();

  } catch (err) {
    console.error("[VAULT/LOAD] ✗ Erro:", err.message);
    showError("Erro ao carregar senhas: " + err.message);
    passwords = [];
  }
}

// =========================================
// 🎨 RENDERIZAR GROUP PILLS
// =========================================

function renderGroupPills() {
  const pillsContainer = document.getElementById("categoryPills");
  if (!pillsContainer) return;

  let html = '<div class="category-pill active" onclick="filterByGroup(\'\')">Todos <i class="bi bi-check-lg"></i></div>';

  groups.forEach(group => {
    html += `
      <div class="category-pill" onclick="filterByGroup(${group.id})">
        ${group.name}
      </div>
    `;
  });

  pillsContainer.innerHTML = html;
  console.log("[VAULT/PILLS] ✓ Pills renderizadas");
}

// =========================================
// 🔍 FILTRAR POR GRUPO
// =========================================

function filterByGroup(groupId) {
  currentGroupFilter = groupId;
  console.log("[VAULT/FILTER] Filtrando por grupo:", groupId || "Todos");

  // Atualiza pills ativas
  document.querySelectorAll(".category-pill").forEach(pill => {
    pill.classList.remove("active");
  });

  if (event && event.target) {
    event.target.closest(".category-pill")?.classList.add("active");
  }

  renderPasswords(filterPasswords());
}

// =========================================
// 🔍 FILTRAR SENHAS
// =========================================

function filterPasswords() {
  let filtered = passwords;

  // Filtro por grupo
  if (currentGroupFilter) {
    filtered = filtered.filter(p => p.group_id === parseInt(currentGroupFilter));
  }

  // Filtro por busca
  const searchTerm = document.getElementById("searchInput")?.value?.toLowerCase() || "";
  if (searchTerm) {
    filtered = filtered.filter(p =>
      p.client.toLowerCase().includes(searchTerm) ||
      p.description.toLowerCase().includes(searchTerm) ||
      (p.email && p.email.toLowerCase().includes(searchTerm))
    );
  }

  return filtered;
}

// =========================================
// 🎨 RENDERIZAR SENHAS
// =========================================

function renderPasswords(list = passwords) {
  const passwordsList = document.getElementById("passwordsList");
  if (!passwordsList) return;

  if (!list || list.length === 0) {
    passwordsList.innerHTML = `
      <div style="grid-column: 1 / -1;">
        <div class="empty-state">
          <div class="empty-state-icon"><i class="bi bi-inbox"></i></div>
          <p>Nenhuma senha encontrada</p>
          <p style="font-size: 12px; margin-top: 1rem;">Clique em "Nova Senha" para criar uma</p>
        </div>
      </div>
    `;
    return;
  }

  passwordsList.innerHTML = list.map(pwd => `
    <div class="password-card">
      <div class="password-icon">
        <i class="bi bi-shield-lock"></i>
      </div>

      <div class="password-client">${escapeHtml(pwd.client)}</div>
      <div class="password-description">${escapeHtml(pwd.description)}</div>

      <div class="password-badges">
        ${pwd.is_public ? '<span class="badge badge-public"><i class="bi bi-share2"></i> Público</span>' : ''}
        ${pwd.group_id ? `<span class="badge badge-group"><i class="bi bi-folder"></i> ${escapeHtml(pwd.group_name)}</span>` : ''}
      </div>

      <div class="password-meta">
        ${pwd.email ? `
          <div class="password-meta-item">
            <i class="bi bi-envelope"></i>
            <span>${escapeHtml(pwd.email)}</span>
          </div>
        ` : ''}
        ${pwd.link ? `
          <div class="password-meta-item">
            <i class="bi bi-link-45deg"></i>
            <a href="${escapeHtml(pwd.link)}" target="_blank" rel="noopener noreferrer">${escapeHtml(pwd.link)}</a>
          </div>
        ` : ''}
        ${pwd.observation ? `
          <div class="password-meta-item">
            <i class="bi bi-chat-left-text"></i>
            <span>${escapeHtml(pwd.observation)}</span>
          </div>
        ` : ''}
      </div>

      <div class="password-actions">
        <button class="btn-password-action" onclick="editPassword(${pwd.id})" title="Editar">
          <i class="bi bi-pencil"></i> Editar
        </button>
        <button class="btn-password-action danger" onclick="deletePasswordConfirm(${pwd.id}, '${escapeHtml(pwd.client).replace(/'/g, "\\'")}')">
          <i class="bi bi-trash"></i> Deletar
        </button>
      </div>
    </div>
  `).join("");

  console.log("[VAULT/RENDER] ✓", list.length, "senhas renderizadas");
}

// =========================================
// 📊 ATUALIZAR ESTATÍSTICAS
// =========================================

function updateStatistics() {
  const total = passwords.length;
  const publicCount = passwords.filter(p => p.is_public).length;
  const privateCount = total - publicCount;

  document.getElementById("totalPasswords").textContent = total;
  document.getElementById("totalGroups").textContent = groups.length;
  document.getElementById("publicPasswords").textContent = publicCount;
  document.getElementById("privatePasswords").textContent = privateCount;

  console.log("[VAULT/STATS] ✓ Estatísticas atualizadas");
}

// =========================================
// 💾 POPULAR SELECT DE GRUPOS
// =========================================

function populateGroupSelect() {
  const groupSelect = document.getElementById("passwordGroup");
  if (!groupSelect) return;

  groupSelect.innerHTML = '<option value="">-- Sem Grupo --</option>';

  groups.forEach(group => {
    const option = document.createElement("option");
    option.value = group.id;
    option.textContent = group.name;
    groupSelect.appendChild(option);
  });

  console.log("[VAULT/SELECT] ✓ Select de grupos populado");
}

// =========================================
// 👁️ TOGGLE PASSWORD VISIBILITY
// =========================================

function togglePasswordVisibility() {
  const field = document.getElementById("passwordValue");
  if (!field) return;

  field.type = field.type === "password" ? "text" : "password";

  const btn = event.target.closest("button");
  if (btn) {
    btn.querySelector("i").classList.toggle("bi-eye");
    btn.querySelector("i").classList.toggle("bi-eye-slash");
  }
}

// =========================================
// 🔐 GERAR SENHA ALEATÓRIA
// =========================================

function generatePassword(length = 16) {
  const uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  const lowercase = "abcdefghijklmnopqrstuvwxyz";
  const numbers = "0123456789";
  const symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?";

  const chars = lowercase + uppercase + numbers + symbols;
  let password = "";

  for (let i = 0; i < length; i++) {
    password += chars.charAt(Math.floor(Math.random() * chars.length));
  }

  return password;
}

// =========================================
// ✏️ EDITAR SENHA
// =========================================

async function editPassword(passwordId) {
  const password = passwords.find(p => p.id === passwordId);
  if (!password) {
    showError("Senha não encontrada");
    return;
  }

  console.log("[VAULT/EDIT] Editando senha:", passwordId);

  selectedPasswordId = passwordId;
  
  const modalLabel = document.getElementById("passwordModalLabel");
  if (modalLabel) {
    modalLabel.innerHTML = '<i class="bi bi-pencil-square"></i> Editar Senha';
  }

  // Preenche formulário
  const form = {
    client: document.getElementById("passwordClient"),
    email: document.getElementById("passwordEmail"),
    description: document.getElementById("passwordDescription"),
    password: document.getElementById("passwordValue"),
    link: document.getElementById("passwordLink"),
    observation: document.getElementById("passwordObservation"),
    group: document.getElementById("passwordGroup"),
    isPublic: document.getElementById("passwordIsPublic"),
    submitBtn: document.getElementById("submitBtn")
  };

  if (form.client) form.client.value = password.client;
  if (form.email) form.email.value = password.email || "";
  if (form.description) form.description.value = password.description;
  if (form.password) form.password.value = password.password;
  if (form.link) form.link.value = password.link || "";
  if (form.observation) form.observation.value = password.observation || "";
  if (form.group) form.group.value = password.group_id || "";
  if (form.isPublic) form.isPublic.checked = password.is_public;
  if (form.submitBtn) form.submitBtn.innerHTML = '<i class="bi bi-check-lg"></i> Atualizar Senha';

  // Limpar erros
  clearModalErrors();

  // Abrir modal
  const modal = new bootstrap.Modal(document.getElementById("passwordModal"));
  modal.show();
}

// =========================================
// 🗑️ DELETAR SENHA
// =========================================

async function deletePasswordConfirm(passwordId, clientName) {
  console.log("[VAULT/DELETE] Deletando senha:", passwordId);

  if (!confirm(`Tem certeza que deseja deletar a senha de "${clientName}"?\n\nEsta ação não pode ser desfeita!`)) {
    return;
  }

  try {
    await apiDeletePassword(passwordId);
    
    showSuccess(`Senha de "${clientName}" deletada com sucesso!`);
    await loadPasswords();

  } catch (err) {
    console.error("[VAULT/DELETE] ✗ Erro:", err.message);
    showError("Erro ao deletar senha: " + err.message);
  }
}

// =========================================
// 💾 SUBMISSÃO DO FORMULÁRIO
// =========================================

function setupFormSubmission() {
  const form = document.getElementById("passwordForm");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const client = document.getElementById("passwordClient")?.value?.trim();
    const email = document.getElementById("passwordEmail")?.value?.trim();
    const description = document.getElementById("passwordDescription")?.value?.trim();
    const password = document.getElementById("passwordValue")?.value;
    const link = document.getElementById("passwordLink")?.value?.trim();
    const observation = document.getElementById("passwordObservation")?.value?.trim();
    const groupId = document.getElementById("passwordGroup")?.value;
    const isPublic = document.getElementById("passwordIsPublic")?.checked;

    // ✅ Validações
    if (!client || !description || !password) {
      showModalError("Preencha os campos obrigatórios (Cliente, Descrição, Senha)!");
      return;
    }

    if (password.length < 6) {
      showModalError("Senha deve ter no mínimo 6 caracteres!");
      return;
    }

    try {
      const submitBtn = document.getElementById("submitBtn");
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processando...';

      const passwordData = {
        client,
        email: email || null,
        description,
        password,
        link: link || null,
        observation: observation || null,
        group_id: groupId ? parseInt(groupId) : null,
        is_public: isPublic
      };

      if (selectedPasswordId) {
        // ATUALIZAR
        console.log("[VAULT/SUBMIT] Atualizando senha:", selectedPasswordId);
        await apiUpdatePassword(selectedPasswordId, passwordData);
        showSuccess("Senha atualizada com sucesso!");

      } else {
        // CRIAR
        console.log("[VAULT/SUBMIT] Criando nova senha...");
        await apiCreatePassword(passwordData);
        showSuccess("Senha criada com sucesso!");
      }

      // Limpa formulário e fecha modal
      form.reset();
      const modal = bootstrap.Modal.getInstance(document.getElementById("passwordModal"));
      modal?.hide();

      // Recarrega dados
      selectedPasswordId = null;
      await loadPasswords();

    } catch (err) {
      console.error("[VAULT/SUBMIT] ✗ Erro:", err.message);
      showModalError(err.message || "Erro ao processar senha!");
    } finally {
      const submitBtn = document.getElementById("submitBtn");
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="bi bi-check-lg"></i> Salvar Senha';
    }
  });
}

// =========================================
// 🎯 SETUP EVENT LISTENERS
// =========================================

function setupEventListeners() {
  console.log("[VAULT/SETUP] Configurando event listeners...");

  // Busca
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      renderPasswords(filterPasswords());
    });
  }

  // Filtro de categoria
  const categoryFilter = document.getElementById("categoryFilter");
  if (categoryFilter) {
    categoryFilter.addEventListener("change", (e) => {
      filterByGroup(e.target.value);
    });
  }

  // Modal events
  const passwordModal = document.getElementById("passwordModal");
  if (passwordModal) {
    passwordModal.addEventListener("show.bs.modal", () => {
      if (!selectedPasswordId) {
        const label = document.getElementById("passwordModalLabel");
        if (label) label.innerHTML = '<i class="bi bi-plus-square"></i> Nova Senha';
        
        const form = document.getElementById("passwordForm");
        if (form) form.reset();
        
        const passwordField = document.getElementById("passwordValue");
        if (passwordField) passwordField.type = "password";
        
        const submitBtn = document.getElementById("submitBtn");
        if (submitBtn) submitBtn.innerHTML = '<i class="bi bi-check-lg"></i> Salvar Senha';
      }
      
      clearModalErrors();
    });

    passwordModal.addEventListener("hidden.bs.modal", () => {
      selectedPasswordId = null;
    });
  }

  // Form submission
  setupFormSubmission();

  console.log("[VAULT/SETUP] ✓ Event listeners configurados");
}

// =========================================
// 📢 MENSAGENS DE ERRO
// =========================================

function showError(message) {
  const alertBox = document.getElementById("alertBox");
  const alertMessage = document.getElementById("alertMessage");
  
  if (alertBox && alertMessage) {
    alertMessage.textContent = message;
    alertBox.classList.remove("d-none");
    
    setTimeout(() => {
      alertBox.classList.add("d-none");
    }, 5000);
  }

  console.warn("[VAULT/ERROR]", message);
}

function showSuccess(message) {
  const successBox = document.getElementById("successBox");
  const successMessage = document.getElementById("successMessage");
  
  if (successBox && successMessage) {
    successMessage.textContent = message;
    successBox.classList.remove("d-none");
    
    setTimeout(() => {
      successBox.classList.add("d-none");
    }, 5000);
  }

  console.log("[VAULT/SUCCESS]", message);
}

function showModalError(message) {
  const modalAlert = document.getElementById("modalAlertBox");
  const modalAlertMsg = document.getElementById("modalAlertMessage");
  
  if (modalAlert && modalAlertMsg) {
    modalAlertMsg.textContent = message;
    modalAlert.classList.remove("d-none");
  }

  console.warn("[VAULT/MODAL-ERROR]", message);
}

function clearModalErrors() {
  const modalAlert = document.getElementById("modalAlertBox");
  if (modalAlert) {
    modalAlert.classList.add("d-none");
  }
}

// =========================================
// 🛡️ UTILITY FUNCTIONS
// =========================================

function escapeHtml(text) {
  if (!text) return "";
  
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  };

  return text.replace(/[&<>"']/g, m => map[m]);
}

// =========================================
// 📱 INICIALIZAÇÃO DO NAVEGADOR (NAV)
// =========================================

function initializeNav() {
  const menuToggle = document.querySelector(".menu-toggle");
  const sidebar = document.querySelector(".sidebar");

  if (menuToggle && sidebar) {
    menuToggle.addEventListener("click", () => {
      sidebar.classList.toggle("active");
    });

    // Fechar sidebar ao clicar fora
    document.addEventListener("click", (e) => {
      if (!e.target.closest(".sidebar") && !e.target.closest(".menu-toggle")) {
        sidebar.classList.remove("active");
      }
    });
  }
}

// Inicializa navegação quando DOM estiver pronto
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeNav);
} else {
  initializeNav();
}

console.log("[PASSWORD-VAULT.JS] ✓ Módulo totalmente carregado");