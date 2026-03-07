// ===== INÍCIO: nav.js (Navegação e Controle de Acesso) =====

// =========================================
// Configuração de Permissões por Role
// =========================================

const rolePermissions = {
  ADMIN: [
    { path: "/SistemaCPE/index.html", label: "Dashboard", icon: "bi-speedometer2" },
    { path: "/SistemaCPE/web/pages/tickets.html", label: "Tickets", icon: "bi-ticket" },
    { path: "/SistemaCPE/web/pages/users.html", label: "Usuários", icon: "bi-people" },
    { path: "/SistemaCPE/web/pages/groups.html", label: "Gerenciar Grupos", icon: "bi-diagram-3" },
    { path: "/SistemaCPE/web/pages/chat.html", label: "Chat", icon: "bi-chat-dots" },
    { path: "/SistemaCPE/web/pages/tasks.html", label: "Tarefas", icon: "bi-check-lg" },
    { path: "/SistemaCPE/web/pages/projects.html", label: "Projetos", icon: "bi-folder" },
    {
      label: "Inventário",
      icon: "bi-box",
      submenu: [
        { path: "/SistemaCPE/web/pages/inventory.html", label: "Equipamentos", icon: "bi-pc-display" },
        { path: "/SistemaCPE/web/pages/password-vault.html", label: "Cofre de Senhas", icon: "bi-shield-lock" },
      ]
    },
    { path: "/SistemaCPE/web/pages/reports.html", label: "Relatórios", icon: "bi-graph-up" },
    { path: "/SistemaCPE/web/pages/billing.html", label: "Faturamento", icon: "bi-credit-card" },
    { path: "/SistemaCPE/web/pages/knowledge-base.html", label: "Base de conhecimento", icon: "bi-book" },
    { path: "/SistemaCPE/web/pages/registrations.html", label: "Cadastros", icon: "bi-person-plus" },
    { path: "/SistemaCPE/web/pages/settings.html", label: "Configurações", icon: "bi-gear" },
    { path: "/SistemaCPE/web/pages/download-agents.html", label: "Download de Agentes", icon: "bi-download" },
  ],
  MANAGER: [
    { path: "/SistemaCPE/index.html", label: "Dashboard", icon: "bi-speedometer2" },
    { path: "/SistemaCPE/web/pages/tickets.html", label: "Tickets", icon: "bi-ticket" },
    { path: "/SistemaCPE/web/pages/chat.html", label: "Chat", icon: "bi-chat-dots" },
    { path: "/SistemaCPE/web/pages/tasks.html", label: "Tarefas", icon: "bi-check-lg" },
    { path: "/SistemaCPE/web/pages/projects.html", label: "Projetos", icon: "bi-folder" },
    {
      label: "Inventário",
      icon: "bi-box",
      submenu: [
        { path: "/SistemaCPE/web/pages/inventory.html", label: "Equipamentos", icon: "bi-pc-display" },
        { path: "/SistemaCPE/web/pages/password-vault.html", label: "Cofre de Senhas", icon: "bi-shield-lock" },
      ]
    },
    { path: "/SistemaCPE/web/pages/reports.html", label: "Relatórios", icon: "bi-graph-up" },
    { path: "/SistemaCPE/web/pages/knowledge-base.html", label: "Base de conhecimento", icon: "bi-book" },
  ],
  USER: [
    { path: "/SistemaCPE/index.html", label: "Dashboard", icon: "bi-speedometer2" },
    { path: "/SistemaCPE/web/pages/tickets.html", label: "Tickets", icon: "bi-ticket" },
    { path: "/SistemaCPE/web/pages/chat.html", label: "Chat", icon: "bi-chat-dots" },
    { path: "/SistemaCPE/web/pages/tasks.html", label: "Tarefas", icon: "bi-check-lg" },
    {
      label: "Inventário",
      icon: "bi-box",
      submenu: [
        { path: "/SistemaCPE/web/pages/password-vault.html", label: "Cofre de Senhas", icon: "bi-shield-lock" },
      ]
    },
    { path: "/SistemaCPE/web/pages/knowledge-base.html", label: "Base de conhecimento", icon: "bi-book" },
  ],
};

// =========================================
// Função: Renderizar Menu Dinamicamente
// =========================================

async function renderNavigation() {
  try {
    console.log("[NAV] Renderizando navegação...");

    const user = await getMe();

    console.log("[NAV] ✓ Usuário:", user.name, "| Role:", user.role);

    const permissions = rolePermissions[user.role] || [];

    console.log("[NAV] Permissões disponíveis:", permissions.length);

    const sidebarMenu = document.querySelector(".sidebar-menu");

    if (!sidebarMenu) {
      console.warn("[NAV] Elemento .sidebar-menu não encontrado");
      return;
    }

    sidebarMenu.innerHTML = "";

    // Renderiza items do menu
    permissions.forEach((item, index) => {
      const li = document.createElement("li");
      li.className = "menu-item";

      if (item.submenu) {
        // ✅ Item com submenu
        li.innerHTML = `
          <a href="#" class="menu-link" onclick="toggleSubmenu(event, this)">
            <span class="menu-icon">
              <i class="bi ${item.icon}"></i>
            </span>
            <span>${item.label}</span>
            <i class="bi bi-chevron-down submenu-arrow" style="margin-left: auto;"></i>
          </a>
          <ul class="submenu" style="display: none;">
            ${item.submenu.map(subitem => `
              <li class="submenu-item">
                <a href="${subitem.path}" class="submenu-link">
                  <i class="bi ${subitem.icon}"></i>
                  <span>${subitem.label}</span>
                </a>
              </li>
            `).join("")}
          </ul>
        `;
      } else {
        // Item simples
        const isActive = window.location.pathname.includes(item.path.replace("/SistemaCPE", ""));
        const activeClass = isActive ? "active" : "";

        li.innerHTML = `
          <a href="${item.path}" class="menu-link ${activeClass}">
            <span class="menu-icon">
              <i class="bi ${item.icon}"></i>
            </span>
            <span>${item.label}</span>
          </a>
        `;
      }

      sidebarMenu.appendChild(li);
      console.log(`[NAV] ✓ Menu item ${index + 1}: ${item.label}`);
    });

    // Logout button
    const logoutLi = document.createElement("li");
    logoutLi.className = "menu-item logout-item";
    logoutLi.innerHTML = `
      <a href="#" onclick="handleLogout(event)" class="menu-link logout-link">
        <i class="bi bi-box-arrow-left"></i>
        <span>Sair</span>
      </a>
    `;

    sidebarMenu.appendChild(logoutLi);

    console.log("[NAV] ✓ Navegação renderizada com sucesso");

  } catch (err) {
    console.error("[NAV] ✗ Erro ao renderizar navegação:", err.message);
  }
}

// =========================================
// Função: Toggle Submenu
// =========================================

function toggleSubmenu(event, element) {
  event.preventDefault();
  const submenu = element.nextElementSibling;
  const arrow = element.querySelector(".submenu-arrow");

  if (submenu && submenu.classList.contains("submenu")) {
    const isHidden = submenu.style.display === "none";
    submenu.style.display = isHidden ? "block" : "none";
    arrow.style.transform = isHidden ? "rotate(180deg)" : "rotate(0deg)";
  }
}

// =========================================
// Função: Handler de Logout
// =========================================

async function handleLogout(event) {
  event.preventDefault();
  event.stopPropagation();

  if (confirm("Tem certeza que deseja sair?")) {
    console.log("[NAV/LOGOUT] Executando logout...");
    try {
      await logout();
    } catch (err) {
      console.error("[NAV/LOGOUT] Erro:", err.message);
      window.location.href = "/SistemaCPE/web/login.html";
    }
  }
}

// =========================================
// Função: Verificar Permissão de Página
// =========================================

function hasAccessToPage(userRole, pagePath) {
  const permissions = rolePermissions[userRole] || [];
  
  for (let item of permissions) {
    if (item.path === pagePath) return true;
    if (item.submenu) {
      if (item.submenu.some(sub => sub.path === pagePath)) return true;
    }
  }
  
  return false;
}

// =========================================
// Função: Proteger Página
// =========================================

async function protectPage() {
  try {
    console.log("[PAGE/PROTECT] Verificando acesso à página...");

    const user = await getMe();
    const currentPath = window.location.pathname;

    console.log("[PAGE/PROTECT] Usuário:", user.name, "| Role:", user.role);
    console.log("[PAGE/PROTECT] Página atual:", currentPath);

    const hasAccess = hasAccessToPage(user.role, currentPath);

    if (!hasAccess) {
      console.warn("[PAGE/PROTECT] ✗ Acesso negado");
      alert("Você não tem permissão para acessar esta página.");
      window.location.href = "/SistemaCPE/index.html";
      return false;
    }

    console.log("[PAGE/PROTECT] ✓ Acesso permitido");

    await renderNavigation();

    return user;

  } catch (err) {
    console.error("[PAGE/PROTECT] ✗ Erro:", err.message);
    window.location.href = "/SistemaCPE/web/login.html";
    return false;
  }
}

// ===== FIM: nav.js (Navegação e Controle de Acesso) =====