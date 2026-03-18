// -*- coding: utf-8 -*-

console.log("[NAV.JS] 🔧 Script carregando...");

/* =========================================
   FUNÇÃO DE ESCAPE HTML
   ========================================= */

function escapeHtml(text) {
  if (!text) return '';
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, char => map[char]);
}

/* =========================================
   CONFIGURAÇÃO DE MENU GLOBAL
   ========================================= */

const globalMenu = [
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
];

/* =========================================
   RENDERIZAR NAVBAR
   ========================================= */

function renderNavbar() {
  console.log("[NAV/NAVBAR] 📱 Renderizando navbar...");

  const navbarContainer = document.getElementById("navbar-container");
  
  if (!navbarContainer) {
    console.error("[NAV/NAVBAR] ❌ #navbar-container não encontrado!");
    return false;
  }

  const user = localStorage.getItem("user");
  let userData = { name: "Visitante" };
  
  if (user) {
    try {
      userData = JSON.parse(user);
    } catch (err) {
      console.warn("[NAV/NAVBAR] ⚠️ Erro ao fazer parse do usuário:", err.message);
    }
  }

  const initials = userData.name 
    ? userData.name.split(" ").map(n => n[0]).join("").toUpperCase().substring(0, 2)
    : "V";

  const userName = userData.name || "Visitante";

  navbarContainer.innerHTML = `
    <div class="navbar-top">
      <div class="navbar-left">
        <img 
          src="/SistemaCPE/web/assests/images/favicon.png" 
          alt="CPE" 
          class="navbar-favicon"
          onerror="this.style.display='none';"
        >
      </div>

      <div class="navbar-center">
        <span class="navbar-page-title" id="pageTitle">Dashboard</span>
      </div>

      <div class="navbar-right">
        <button class="navbar-icon-btn" title="Menu" onclick="toggleSidebarMobile()">
          <i class="bi bi-list"></i>
        </button>
        <button class="navbar-icon-btn" title="Notificações">
          <i class="bi bi-bell"></i>
        </button>
        <button class="navbar-icon-btn" title="Ajuda">
          <i class="bi bi-question-circle"></i>
        </button>
        <div class="navbar-user-section">
          <div class="user-avatar-navbar" title="${escapeHtml(userName)}">${initials}</div>
          <span class="navbar-user-name">${escapeHtml(userName)}</span>
          <button class="navbar-icon-btn btn-logout-navbar" onclick="handleLogout(event)" title="Sair">
            <i class="bi bi-box-arrow-right"></i>
          </button>
        </div>
      </div>
    </div>
  `;

  console.log("[NAV/NAVBAR] ✅ Navbar renderizada com sucesso");
  return true;
}

/* =========================================
   RENDERIZAR SIDEBAR
   ========================================= */

function renderSidebar() {
  console.log("[NAV/SIDEBAR] 🎯 Renderizando sidebar...");

  const sidebarContainer = document.getElementById("sidebar-container");
  
  if (!sidebarContainer) {
    console.error("[NAV/SIDEBAR] ❌ #sidebar-container não encontrado!");
    return false;
  }

  let menuHTML = `
    <div class="sidebar-wrapper">
      <div class="sidebar-logo-container"></div>
      <nav class="sidebar-nav">
        <ul class="sidebar-menu">
  `;

  globalMenu.forEach((item, index) => {
    if (item.submenu && Array.isArray(item.submenu)) {
      menuHTML += `
        <li class="menu-item has-submenu" title="${item.label}">
          <a href="#" class="menu-link" onclick="toggleSubmenu(event, this)">
            <span class="menu-icon">
              <i class="bi ${item.icon}"></i>
            </span>
            <span class="menu-label">${item.label}</span>
            <i class="bi bi-chevron-right submenu-arrow"></i>
          </a>
          <ul class="submenu">
            ${item.submenu.map(subitem => `
              <li class="submenu-item">
                <a href="${subitem.path}" class="submenu-link" onclick="updatePageTitle('${subitem.label}')">
                  <i class="bi ${subitem.icon}"></i>
                  <span>${subitem.label}</span>
                </a>
              </li>
            `).join("")}
          </ul>
        </li>
      `;
    } else {
      const isActive = window.location.pathname.includes(item.path.replace("/SistemaCPE", ""));
      const activeClass = isActive ? "active" : "";

      menuHTML += `
        <li class="menu-item ${activeClass}" title="${item.label}">
          <a href="${item.path}" class="menu-link ${activeClass}" onclick="updatePageTitle('${item.label}')">
            <span class="menu-icon">
              <i class="bi ${item.icon}"></i>
            </span>
            <span class="menu-label">${item.label}</span>
          </a>
        </li>
      `;
    }
  });

  menuHTML += `
        <li class="menu-item logout-item" title="Sair">
          <a href="#" onclick="handleLogout(event)" class="menu-link logout-link">
            <span class="menu-icon">
              <i class="bi bi-box-arrow-left"></i>
            </span>
            <span class="menu-label">Sair</span>
          </a>
        </li>
        </ul>
      </nav>
    </div>
  `;

  sidebarContainer.innerHTML = menuHTML;

  setupSidebarListeners();

  console.log("[NAV/SIDEBAR] ✅ Sidebar renderizada com sucesso");
  return true;
}

/* =========================================
   SETUP LISTENERS DO SIDEBAR
   ========================================= */

function setupSidebarListeners() {
  console.log("[NAV/SIDEBAR-LISTENERS] 🔗 Configurando listeners...");

  const sidebarWrapper = document.querySelector(".sidebar-wrapper");
  
  if (sidebarWrapper) {
    sidebarWrapper.addEventListener("mouseenter", function() {
      this.classList.add("expanded");
    });

    sidebarWrapper.addEventListener("mouseleave", function() {
      this.classList.remove("expanded");
    });
  }

  console.log("[NAV/SIDEBAR-LISTENERS] ✅ Listeners configurados");
}

/* =========================================
   ATUALIZAR TÍTULO DA PÁGINA
   ========================================= */

function updatePageTitle(title) {
  const pageTitle = document.getElementById("pageTitle");
  if (pageTitle) {
    pageTitle.textContent = title;
    console.log(`[NAV/TITLE] ✅ Título atualizado: "${title}"`);
  }
}

/* =========================================
   TOGGLE SUBMENU
   ========================================= */

function toggleSubmenu(event, element) {
  event.preventDefault();
  event.stopPropagation();

  const submenu = element.nextElementSibling;
  const arrow = element.querySelector(".submenu-arrow");

  if (!submenu || !submenu.classList.contains("submenu")) {
    console.warn("[NAV/SUBMENU] ⚠️ Submenu não encontrado");
    return;
  }

  const isHidden = submenu.style.display === "none" || submenu.offsetHeight === 0;
  submenu.style.display = isHidden ? "block" : "none";

  if (arrow) {
    arrow.style.transform = isHidden ? "rotate(90deg)" : "rotate(0deg)";
  }

  console.log(`[NAV/SUBMENU] ✅ Submenu ${isHidden ? "aberto" : "fechado"}`);
}

/* =========================================
   TOGGLE SIDEBAR MOBILE
   ========================================= */

function toggleSidebarMobile() {
  const sidebar = document.querySelector(".sidebar-wrapper");
  if (sidebar) {
    sidebar.classList.toggle("show");
    console.log("[NAV/MOBILE] ✅ Sidebar mobile toggled");
  }
}

/* =========================================
   LOGOUT
   ========================================= */

function handleLogout(event) {
  event.preventDefault();
  event.stopPropagation();

  if (!confirm("Tem certeza que deseja sair?")) {
    console.log("[NAV/LOGOUT] ⚠️ Logout cancelado");
    return;
  }

  console.log("[NAV/LOGOUT] 🚪 Processando logout...");

  try {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    localStorage.removeItem("logged_in");
    localStorage.removeItem("auth_token");
    localStorage.removeItem("current_user");
    
    console.log("[NAV/LOGOUT] ✅ Dados de sessão removidos");
    window.location.href = "/SistemaCPE/web/login.html";
    
  } catch (err) {
    console.error("[NAV/LOGOUT] ❌ Erro:", err.message);
    localStorage.clear();
    window.location.href = "/SistemaCPE/web/login.html";
  }
}

/* =========================================
   INICIALIZAR NAVEGAÇÃO
   ========================================= */

function initializeNavigation() {
  console.log("\n" + "=".repeat(80));
  console.log("[NAV/INIT] 🚀 Inicializando navegação");
  console.log("=".repeat(80));

  try {
    const navbarOk = renderNavbar();
    const sidebarOk = renderSidebar();

    if (navbarOk && sidebarOk) {
      console.log("[NAV/INIT] ✅ Navegação inicializada com sucesso!");
      console.log("[NAV/INIT] 📊 Componentes:");
      console.log("[NAV/INIT]   ✓ Navbar");
      console.log("[NAV/INIT]   ✓ Sidebar");
      console.log("[NAV/INIT]   ✓ Menu items carregados");
      console.log("=".repeat(80) + "\n");
      return true;
    } else {
      console.warn("[NAV/INIT] ⚠️ Problemas na inicialização");
      console.log("=".repeat(80) + "\n");
      return false;
    }

  } catch (err) {
    console.error("[NAV/INIT] ❌ ERRO:", err.message);
    console.error(err.stack);
    console.log("=".repeat(80) + "\n");
    return false;
  }
}

/* =========================================
   BOOT DO SCRIPT
   ========================================= */

console.log("[NAV.JS] ✅ Script carregado");

document.addEventListener("DOMContentLoaded", function() {
  console.log("[NAV.JS/BOOT] 🎬 DOMContentLoaded disparado");
  
  setTimeout(function() {
    const success = initializeNavigation();
    if (success) {
      console.log("[NAV.JS/BOOT] ✅ nav.js pronto para uso");
    } else {
      console.error("[NAV.JS/BOOT] ❌ Erro na inicialização");
    }
  }, 50);
});

// Fallback se DOMContentLoaded já passou
if (document.readyState === "complete" || document.readyState === "interactive") {
  console.log("[NAV.JS/FALLBACK] 🔄 DOM já carregado, inicializando agora");
  setTimeout(initializeNavigation, 50);
}