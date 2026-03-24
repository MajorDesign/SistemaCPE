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
          src="" 
          alt="CPE" 
          class="navbar-favicon"
          onerror="this.style.display='none';"
        >
      </div>

      <div class="navbar-right">
        <button class="navbar-icon-btn" title="Menu" onclick="toggleSidebarMobile()">
          <i class="bi bi-list"></i>
        </button>
        
        <!-- ✅ SINO DE NOTIFICAÇÕES -->
        <button class="navbar-icon-btn notification-bell-btn" 
                id="notificationBellBtn"
                title="Notificações"
                onclick="toggleNotificationPanel(event)">
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

    <!-- ✅ PAINEL DE NOTIFICAÇÕES (BALÃO) -->
    <div class="notification-panel" id="notificationPanel">
      <div class="notification-panel-header">
        <h5>
          <i class="bi bi-bell-fill"></i> Notificações
        </h5>
        <button class="close-btn" onclick="closeNotificationPanel(event)">
          <i class="bi bi-x"></i>
        </button>
      </div>
      
      <div class="notification-list" id="notificationList">
        <div class="notification-empty">
          <i class="bi bi-inbox"></i>
          <p>Nenhuma notificação</p>
        </div>
      </div>
      
      <div class="notification-panel-footer">
        <a href="/SistemaCPE/web/pages/tickets.html" onclick="closeNotificationPanel(event)">
          Ver todos os tickets →
        </a>
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
   ✅ SISTEMA DE NOTIFICAÇÕES
   ========================================= */

// --- Variáveis globais ---
let notificationsData = [];
let currentUserId = null;
let notificationCheckInterval = null;
const NOTIFICATIONS_API = "http://localhost:8000/api/notificacoes";

// ✅ Inicializar notificações
function initNotifications() {
  try {
    console.log("[NAV/NOTIFICATIONS] ⚙️ Inicializando notificações...");
    
    const userData = localStorage.getItem("user");
    if (!userData) {
      console.warn("[NAV/NOTIFICATIONS] ⚠️ Usuário não autenticado");
      return;
    }
    
    const user = JSON.parse(userData);
    currentUserId = user.id;
    
    console.log("[NAV/NOTIFICATIONS] 👤 Usuário: #" + currentUserId);
    
    // Carregar notificações iniciais
    loadNotifications();
    
    // Atualizar notificações a cada 15 segundos
    if (notificationCheckInterval) {
      clearInterval(notificationCheckInterval);
    }
    
    notificationCheckInterval = setInterval(loadNotifications, 15000);
    console.log("[NAV/NOTIFICATIONS] ✅ Sistema pronto (atualiza a cada 15s)");
    
    // Fechar painel ao clicar fora
    document.addEventListener("click", (e) => {
      const panel = document.getElementById("notificationPanel");
      const btn = document.getElementById("notificationBellBtn");
      
      if (panel && btn && !panel.contains(e.target) && !btn.contains(e.target)) {
        closeNotificationPanel(e);
      }
    });
    
  } catch (error) {
    console.error("[NAV/NOTIFICATIONS] ❌ Erro na inicialização:", error);
  }
}

// ✅ Carregar notificações da API
async function loadNotifications() {
  try {
    if (!currentUserId) return;
    
    console.log("[NAV/NOTIFICATIONS] 📡 Carregando notificações...");
    
    const response = await fetch(`${NOTIFICATIONS_API}?usuario_id=${currentUserId}&limite=20`);
    
    if (response.status === 404) {
      console.warn("[NAV/NOTIFICATIONS] ⚠️ Endpoint não encontrado, usando localStorage");
      loadNotificationsFromStorage();
      return;
    }
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const notifications = await response.json();
    console.log("[NAV/NOTIFICATIONS] ✅ " + notifications.length + " notificação(ões)");
    
    // Armazenar no localStorage
    localStorage.setItem("notifications_" + currentUserId, JSON.stringify(notifications));
    
    notificationsData = notifications;
    updateNotificationUI();
    
  } catch (error) {
    console.error("[NAV/NOTIFICATIONS] ❌ Erro:", error);
    loadNotificationsFromStorage();
  }
}

// ✅ Carregar do localStorage (fallback)
function loadNotificationsFromStorage() {
  try {
    const stored = localStorage.getItem("notifications_" + currentUserId);
    
    if (stored) {
      notificationsData = JSON.parse(stored);
      console.log("[NAV/NOTIFICATIONS] 💾 Usando dados do localStorage");
      updateNotificationUI();
    }
  } catch (error) {
    console.error("[NAV/NOTIFICATIONS] ❌ Erro ao carregar storage:", error);
  }
}

// ✅ Atualizar UI
function updateNotificationUI() {
  console.log("[NAV/NOTIFICATIONS-UI] 🎨 Atualizando interface...");
  
  // Contar não lidas
  const unreadCount = notificationsData.filter(n => !n.lido).length;
  console.log("[NAV/NOTIFICATIONS-UI]   - Não lidas: " + unreadCount);
  
  // Atualizar badge
  updateNotificationBadge(unreadCount);
  
  // Atualizar lista
  renderNotificationList();
}

// ✅ Atualizar badge do sino
function updateNotificationBadge(count) {
  const bellBtn = document.getElementById("notificationBellBtn");
  if (!bellBtn) return;
  
  // Remover badge antigo
  const oldBadge = bellBtn.querySelector(".notification-badge");
  if (oldBadge) oldBadge.remove();
  
  // Adicionar novo badge se houver notificações não lidas
  if (count > 0) {
    const badge = document.createElement("span");
    badge.className = "notification-badge pulse";
    badge.textContent = count > 9 ? "9+" : count;
    bellBtn.appendChild(badge);
    
    console.log("[NAV/NOTIFICATIONS-UI] 📍 Badge: " + count);
  }
}

// ✅ Renderizar lista de notificações
function renderNotificationList() {
  const listContainer = document.getElementById("notificationList");
  if (!listContainer) return;
  
  // Ordenar por mais recentes primeiro
  const sorted = [...notificationsData].sort((a, b) => {
    return new Date(b.created_at) - new Date(a.created_at);
  });
  
  // Limitar a 10 notificações
  const displayed = sorted.slice(0, 10);
  
  if (displayed.length === 0) {
    listContainer.innerHTML = `
      <div class="notification-empty">
        <i class="bi bi-inbox"></i>
        <p>Nenhuma notificação</p>
      </div>
    `;
    return;
  }
  
  listContainer.innerHTML = displayed.map(notif => {
    const icon = getNotificationIcon(notif.tipo);
    const date = formatNotificationDate(notif.created_at);
    const unreadClass = notif.lido ? "" : "unread";
    
    return `
      <div class="notification-item ${unreadClass}" 
           onclick="handleNotificationClick(${notif.id}, ${notif.ticket_id})"
           data-notification-id="${notif.id}">
        
        <div class="notification-icon ${notif.tipo}">
          ${icon}
        </div>
        
        <div class="notification-content">
          <p class="notification-title">
            ${getTipoLabel(notif.tipo)}
            <span class="notification-badge-type ${notif.tipo}">
              ${getTipoBadgeText(notif.tipo)}
            </span>
          </p>
          <p class="notification-message">
            ${escapeHtml(notif.mensagem)}
          </p>
          <p class="notification-meta">
            ${date}
          </p>
        </div>
      </div>
    `;
  }).join("");
  
  console.log("[NAV/NOTIFICATIONS-UI] ✅ Lista com " + displayed.length + " itens");
}

// ✅ Toggle painel de notificações
function toggleNotificationPanel(event) {
  if (event) {
    event.stopPropagation();
  }
  
  const panel = document.getElementById("notificationPanel");
  if (!panel) return;
  
  panel.classList.toggle("show");
  
  if (panel.classList.contains("show")) {
    console.log("[NAV/NOTIFICATIONS] 👁️ Painel aberto");
    markAllAsRead();
  } else {
    console.log("[NAV/NOTIFICATIONS] 👁️ Painel fechado");
  }
}

// ✅ Fechar painel de notificações
function closeNotificationPanel(event) {
  if (event) {
    event.stopPropagation();
  }
  
  const panel = document.getElementById("notificationPanel");
  if (panel) {
    panel.classList.remove("show");
  }
}

// ✅ Clique em notificação
async function handleNotificationClick(notificationId, ticketId) {
  console.log("[NAV/NOTIFICATIONS] 🔗 Clique #" + notificationId);
  
  try {
    // Marcar como lida
    await markNotificationAsRead(notificationId);
    
    // Fechar painel
    closeNotificationPanel();
    
    // Navegar para o ticket
    window.location.href = `/SistemaCPE/web/pages/tickets.html?ticket_id=${ticketId}`;
    
  } catch (error) {
    console.error("[NAV/NOTIFICATIONS] ❌ Erro:", error);
  }
}

// ✅ Marcar como lida
async function markNotificationAsRead(notificationId) {
  try {
    const response = await fetch(`${NOTIFICATIONS_API}/${notificationId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ lido: true })
    });
    
    if (response.ok) {
      console.log("[NAV/NOTIFICATIONS] ✅ Notificação #" + notificationId + " lida");
      await loadNotifications();
    }
  } catch (error) {
    console.error("[NAV/NOTIFICATIONS] ❌ Erro ao marcar lida:", error);
  }
}

// ✅ Marcar todas como lidas
async function markAllAsRead() {
  try {
    const unreadNotifs = notificationsData.filter(n => !n.lido);
    
    if (unreadNotifs.length === 0) return;
    
    console.log("[NAV/NOTIFICATIONS] 📋 Marcando " + unreadNotifs.length + " como lida(s)...");
    
    for (const notif of unreadNotifs) {
      await fetch(`${NOTIFICATIONS_API}/${notif.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ lido: true })
      });
    }
    
    await loadNotifications();
  } catch (error) {
    console.error("[NAV/NOTIFICATIONS] ❌ Erro:", error);
  }
}

// ✅ Funções auxiliares de notificações
function getNotificationIcon(tipo) {
  const icons = {
    "atribuido": "👤",
    "respondido": "💬",
    "transferido": "↔️",
    "finalizado": "✅",
    "alterado": "🔄"
  };
  return icons[tipo] || "📬";
}

function getTipoLabel(tipo) {
  const labels = {
    "atribuido": "Ticket Atribuído",
    "respondido": "Nova Resposta",
    "transferido": "Ticket Transferido",
    "finalizado": "Ticket Finalizado",
    "alterado": "Ticket Alterado"
  };
  return labels[tipo] || "Notificação";
}

function getTipoBadgeText(tipo) {
  const texts = {
    "atribuido": "Atribuído",
    "respondido": "Resposta",
    "transferido": "Transferência",
    "finalizado": "Finalizado",
    "alterado": "Alteração"
  };
  return texts[tipo] || tipo;
}

function formatNotificationDate(dateString) {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return "Agora";
    if (diff < 3600000) return Math.floor(diff / 60000) + "m atrás";
    if (diff < 86400000) return Math.floor(diff / 3600000) + "h atrás";
    
    const days = Math.floor(diff / 86400000);
    return days === 1 ? "Ontem" : days + "d atrás";
  } catch (error) {
    return "Data inválida";
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
      console.log("[NAV/INIT]   ✓ Sistema de notificações pronto");
      
      // ✅ Inicializar notificações
      initNotifications();
      
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