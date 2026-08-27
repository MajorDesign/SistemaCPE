// -*- coding: utf-8 -*-

console.log("[NAV.JS] 🔧 Script carregando...");

/* =========================================
   BANNER GLOBAL — MODO SUPORTE (impersonate)
   Adicionado 2026-08-27. Aparece em TODAS as paginas se localStorage
   cpe_impersonate_active == '1'. Botao "Sair" restaura o token real.
   ========================================= */
(function _impersonateBanner() {
  try {
    if (localStorage.getItem('cpe_impersonate_active') !== '1') return;
    const targetName = localStorage.getItem('cpe_impersonate_target_name') || 'usuário';
    const realUserStr = localStorage.getItem('cpe_user_real');
    let realName = 'você';
    try { realName = (JSON.parse(realUserStr || '{}')).name || realName; } catch (_) {}

    const html = `
      <div id="cpe-impersonate-banner"
           style="position:fixed;top:0;left:0;right:0;z-index:99999;
                  background:linear-gradient(90deg,#B91C1C 0%,#DC2626 100%);
                  color:#fff;padding:8px 14px;font-family:'DM Sans',system-ui,sans-serif;
                  font-size:13px;font-weight:600;display:flex;align-items:center;
                  gap:12px;box-shadow:0 2px 8px rgba(0,0,0,.25);letter-spacing:.01em">
        <i class="bi bi-eye-fill" style="font-size:16px"></i>
        <span style="flex:1">
          MODO SUPORTE — Você está vendo o sistema como
          <strong>${escapeHtml(targetName)}</strong>
          <span style="opacity:.8;font-weight:400"> (a sessão é READ-ONLY; qualquer edição é bloqueada)</span>
        </span>
        <button type="button" onclick="window.sairModoSuporte()"
                style="background:#fff;color:#B91C1C;border:none;border-radius:6px;
                       padding:5px 12px;font-weight:700;cursor:pointer;font-size:12px">
          <i class="bi bi-box-arrow-right"></i> Sair do modo suporte
        </button>
      </div>
      <style>body { padding-top: 40px !important; }</style>
    `;
    const wrap = document.createElement('div');
    wrap.innerHTML = html;
    document.body.appendChild(wrap.firstElementChild);
    document.body.appendChild(wrap.lastElementChild); // style tag
  } catch (e) {
    console.warn('[NAV/IMPERSONATE] falha no banner:', e);
  }
})();

window.sairModoSuporte = async function () {
  try {
    const base = (typeof API_BASE_URL !== 'undefined') ? API_BASE_URL : '';
    const tok  = localStorage.getItem('token') || localStorage.getItem('cpe_token') || '';
    // Best-effort: avisa o servidor pra logar o end (permitido pela allowlist)
    try {
      await fetch(base + '/api/auth/impersonate/end', {
        method: 'POST',
        headers: { 'X-Auth-Token': tok }
      });
    } catch (_) {}
    // Restaura token e user reais
    const realTok  = localStorage.getItem('cpe_token_real');
    const realUser = localStorage.getItem('cpe_user_real');
    if (realTok)  { localStorage.setItem('token', realTok); localStorage.setItem('cpe_token', realTok); }
    if (realUser) { localStorage.setItem('user', realUser); localStorage.setItem('cpe_user', realUser); }
    // Limpa flags de impersonate
    localStorage.removeItem('cpe_impersonate_active');
    localStorage.removeItem('cpe_impersonate_target_name');
    localStorage.removeItem('cpe_token_real');
    localStorage.removeItem('cpe_user_real');
    // Recarrega pra tudo voltar ao normal
    window.location.href = '/SistemaCPE/index.html';
  } catch (e) {
    alert('Erro ao sair: ' + e.message + '\nRecarregue a pagina manualmente.');
  }
};


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

// ================================================== 
// CONFIGURAÇÃO DE MENU GLOBAL COM FILTRO POR ROLE
// Data: 01/04/2026
// ==================================================

const globalMenu = [
  { path: "/SistemaCPE/index.html", label: "Dashboard", icon: "bi-speedometer2", requiredRoles: ["USER", "RESPONSAVEL_GRUPO", "ADMIN", "TI", "MANAGER"] },
  { path: "/SistemaCPE/web/pages/tickets.html",    label: "Tickets",    icon: "bi-ticket",     requiredRoles: ["USER", "RESPONSAVEL_GRUPO", "ADMIN", "TI", "MANAGER"] },
  { path: "/SistemaCPE/web/pages/users.html", label: "Usuários", icon: "bi-people", requiredRoles: ["ADMIN", "TI", "MANAGER"] },
  { path: "/SistemaCPE/web/pages/groups.html", label: "Gerenciar Grupos", icon: "bi-diagram-3", requiredRoles: ["ADMIN", "TI", "MANAGER"] },
  { path: "/SistemaCPE/web/pages/chat.html", label: "Chat", icon: "bi-chat-dots", requiredRoles: ["USER", "RESPONSAVEL_GRUPO", "ADMIN", "TI", "MANAGER"] },
  { path: "/SistemaCPE/web/pages/tasks.html", label: "Tarefas", icon: "bi-check-lg", requiredRoles: ["USER", "RESPONSAVEL_GRUPO", "ADMIN", "TI", "MANAGER"] },
  {
    label: "Inventário",
    icon: "bi-box",
    requiredRoles: ["ADMIN", "TI", "MANAGER"],
    submenu: [
      { path: "/SistemaCPE/web/pages/inventory.html",    label: "Financeiro TI",        icon: '<span class="icon-pcdollar"><i class="bi bi-pc-display"></i><i class="bi bi-currency-dollar icon-pcdollar-badge"></i></span>', requiredRoles: ["ADMIN", "TI", "MANAGER"] },
      { path: "/SistemaCPE/web/pages/inventory-ti.html", label: "Inventário T.I.",       icon: "bi-laptop",         requiredRoles: ["ADMIN", "TI", "MANAGER"] },
      { path: "/SistemaCPE/web/pages/celulares.html",    label: "Celulares Corporativos", icon: "bi-phone",         requiredRoles: ["ADMIN", "TI", "MANAGER"] },
      { path: "/SistemaCPE/web/pages/network.html",      label: "Monitoramento de Rede", icon: "bi-broadcast-pin",  requiredRoles: ["ADMIN", "TI"] }
    ]
  },
  { path: "/SistemaCPE/web/pages/password-vault.html", label: "Cofre de Senhas", icon: "bi-shield-lock", requiredRoles: ["USER", "RESPONSAVEL_GRUPO", "ADMIN", "TI", "MANAGER"] },
  // 2026-08-25: MANAGER removido do acesso ao menu de Relatórios.
  // Regra em docs/REGRAS_NEGOCIO.md#relatorios-e-avaliacoes.
  { path: "/SistemaCPE/web/pages/reports.html", label: "Relatórios", icon: "bi-graph-up", requiredRoles: ["RESPONSAVEL_GRUPO", "ADMIN", "TI"] },
  { path: "/SistemaCPE/web/pages/base_conhecimento.html", label: "Base de conhecimento", icon: "bi-book", requiredRoles: ["USER", "RESPONSAVEL_GRUPO", "ADMIN", "TI", "MANAGER"] },
  { path: "/SistemaCPE/web/pages/contratos.html", label: "Contratos e Termos", icon: "bi-file-earmark-text", requiredRoles: ["USER", "RESPONSAVEL_GRUPO", "ADMIN", "TI", "MANAGER"] },
  { path: "/SistemaCPE/web/pages/settings.html", label: "Configurações", icon: "bi-gear", requiredRoles: ["ADMIN", "TI", "MANAGER"] },
  { path: "/SistemaCPE/web/pages/download-agents.html", label: "Download de Agentes", icon: "bi-download", requiredRoles: ["USER", "RESPONSAVEL_GRUPO", "ADMIN", "TI", "MANAGER"] },
  // ==================================================
  // ✨ MENU: Módulo de Frotas
  // Data: 15/04/2026
  // ==================================================
  {
    path: "/SistemaCPE/web/pages/fleet.html",
    label: "Frotas",
    icon: "bi-truck",
    requiredRoles: ["ADMIN", "TI", "MANAGER", "RESPONSAVEL_GRUPO"],
    external: true
  },
  // ==================================================
  // ✨ MENU: Módulo Equipe de Suporte (agendas de atendimento)
  // Data: 22/05/2026
  // ==================================================
  {
    path: "/SistemaCPE/web/pages/equipe-suporte.html",
    label: "Equipe de Suporte",
    icon: "bi-headset",
    requiredRoles: ["ADMIN", "TI"],
    external: true
  },
  // ==================================================
  // ✨ MENU: Módulo Comercial (agenda vendedores + reuniões + material apoio)
  // Data: 2026-07-23
  // Filtro real vem do backend (grupo Comercial + ADMIN/TI/MANAGER).
  // requiredRoles aqui é só fallback se a API /me/menu cair.
  // ==================================================
  {
    path: "/SistemaCPE/web/pages/comercial.html",
    label: "Comercial",
    icon: "bi-briefcase-fill",
    requiredRoles: ["ADMIN", "TI", "MANAGER"],
    external: true
  },
  // ==================================================
  // ✨ MENU: Módulo de Recepção
  // Data: 30/04/2026
  // Aberto a todos os perfis — qualquer usuário pode agendar sala
  // e cadastrar envios; só ADMIN/RESPONSAVEL_GRUPO cria sala.
  // ==================================================
  {
    path: "/SistemaCPE/web/pages/recepcao.html",
    label: "Recepção",
    icon: "bi-building-check",
    requiredRoles: ["USER", "RESPONSAVEL_GRUPO", "ADMIN", "TI", "MANAGER"],
    external: true
  },
  // ==================================================
  // ✨ MENU: Módulo Agenda (integração Carbonio)
  // Data: 04/05/2026
  // Cada usuário conecta sua própria conta Carbonio (webmail).
  // ==================================================
  {
    path: "/SistemaCPE/web/pages/agenda.html",
    label: "Agenda",
    icon: "bi-calendar2-event",
    requiredRoles: ["USER", "RESPONSAVEL_GRUPO", "ADMIN", "TI", "MANAGER"],
    external: true
  },
  // ==================================================
  // ✨ MENU: Permissões do Sistema
  // Data: 06/04/2026 21:30
  // ==================================================
  { path: "/SistemaCPE/web/pages/permissions.html", label: "Permissões", icon: "bi-shield-lock", requiredRoles: ["ADMIN"] }
];
// ==================================================
// getFilteredMenu — REFATORADO 2026-05-05
//
// Agora usa /api/permissions/me/menu (lógica canônica do backend que
// considera role + grupo + exceções), em vez de fazer o filtro
// localmente baseado só em requiredRoles.
//
// Mantém o `globalMenu` hardcoded como fonte de label/icon/submenu —
// porque essas informações de UI (ordem, ícones, agrupamento em
// submenu) ainda não estão no banco. O backend só decide QUAIS pages
// o user pode ver; o front decide COMO mostrar.
// ==================================================
// Mapeamentos especiais: nem todo arquivo .html tem o mesmo nome do
// page_key cadastrado em permission_pages. Quando precisar de um
// nome diferente, registra aqui.
const _PAGE_KEY_OVERRIDES = {
  '/SistemaCPE/index.html': 'DASHBOARD',
  '/SistemaCPE/':           'DASHBOARD',
};

function pageKeyFromPath(path) {
  if (!path) return '';
  if (_PAGE_KEY_OVERRIDES[path]) return _PAGE_KEY_OVERRIDES[path];
  return path.split('/').pop().replace('.html', '').replace(/-/g, '_').toUpperCase();
}

async function getFilteredMenu(userRole, userId) {
  console.log("[NAV/MENU] 🔍 Filtrando menu pelo backend canônico (role + grupo + exceções)");

  // Sem user_id válido: trata como sem permissão (retorna vazio)
  if (!userId) {
    console.warn("[NAV/MENU] ⚠️ userId não informado — menu vazio");
    return [];
  }

  // 1) Pergunta ao backend quais page_keys o user pode acessar
  const apiBase = (typeof API_BASE_URL !== 'undefined')
    ? API_BASE_URL
    : `http://${location.hostname || '127.0.0.1'}:8000`;

  let allowedKeys = null;
  try {
    const r = await fetch(`${apiBase}/api/permissions/me/menu?user_id=${userId}`);
    if (r.ok) {
      const data = await r.json();
      allowedKeys = new Set((data.pages || []).map(p => p.page_key));
      console.log(`[NAV/MENU] ✅ Backend retornou ${allowedKeys.size} páginas permitidas`);
    } else {
      console.warn(`[NAV/MENU] ⚠️ /me/menu falhou (HTTP ${r.status}); usando fallback por role`);
    }
  } catch (e) {
    console.warn('[NAV/MENU] ⚠️ Erro ao chamar /me/menu:', e.message, '- fallback por role');
  }

  // Fallback: se o backend caiu, usa requiredRoles do globalMenu (comportamento antigo)
  // — assim o sistema continua navegável mesmo se a API estiver fora do ar.
  function passaFallback(item) {
    return !item.requiredRoles || item.requiredRoles.includes(userRole);
  }
  function passa(item) {
    if (allowedKeys === null) return passaFallback(item);
    if (!item.path) return true;  // wrapper de submenu: avalia pelos filhos
    return allowedKeys.has(pageKeyFromPath(item.path));
  }

  // 2) Filtra globalMenu mantendo a estrutura (label, icon, submenu)
  return globalMenu
    .map(item => {
      // Item com submenu: filtra subitens primeiro
      if (item.submenu && Array.isArray(item.submenu)) {
        const subFiltered = item.submenu.filter(passa);
        if (subFiltered.length === 0) return null;     // esconde wrapper se zero filhos
        return { ...item, submenu: subFiltered };
      }
      return passa(item) ? item : null;
    })
    .filter(Boolean);
}

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

  // ✅ CORRIGIDO: chave unificada para "cpe_user" (igual ao tickets.js)
  const userStr = localStorage.getItem("cpe_user");
  let userData = { name: "Visitante" };
  
  if (userStr) {
    try {
      userData = JSON.parse(userStr);
    } catch (err) {
      console.warn("[NAV/NAVBAR] ⚠️ Erro ao fazer parse do usuário:", err.message);
    }
  }

  const initials = userData.name
    ? userData.name.split(" ").map(n => n[0]).join("").toUpperCase().substring(0, 2)
    : "V";

  const userName = userData.name || "Visitante";

  // Avatar: se o user tem foto salva (avatar_url), renderiza <img>;
  // senão, mostra as iniciais. Cache-buster `?t=...` evita ver foto antiga.
  const avatarHtml = userData.avatar_url
    ? `<img src="${escapeHtml(userData.avatar_url)}${userData.avatar_url.includes('?') ? '' : '?t=' + Date.now()}" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:inherit;">`
    : escapeHtml(initials);

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
        <!-- ICONE CHAT (novas mensagens/chamadas — script global cuida do badge) -->
        <button class="navbar-icon-btn chat-notify-btn"
                id="chatNotifyBtn"
                title="Chat — abrir"
                onclick="window.location.href='/SistemaCPE/web/pages/chat.html'"
                style="position:relative">
          <i class="bi bi-chat-dots-fill"></i>
          <span id="chatNotifyBadge"
                style="display:none;position:absolute;top:2px;right:2px;
                       background:#EF4444;color:#fff;font-size:0.6rem;font-weight:700;
                       min-width:16px;height:16px;border-radius:8px;padding:0 4px;
                       display:none;align-items:center;justify-content:center"></span>
        </button>

        <!-- SINO DE NOTIFICAÇÕES (tickets) -->
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
          <div class="user-avatar-navbar" title="${escapeHtml(userName)}" style="overflow:hidden">${avatarHtml}</div>
          <span class="navbar-user-name">${escapeHtml(userName)}</span>
          <button class="navbar-icon-btn btn-logout-navbar" onclick="handleLogout(event)" title="Sair">
            <i class="bi bi-box-arrow-right"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- PAINEL DE NOTIFICAÇÕES (BALÃO) -->
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
        <button class="btn-limpar-notificacoes" 
                onclick="limparNotificacoesLidas(event)"
                title="Deletar todas as notificações já lidas">
          <i class="bi bi-trash"></i>
          Limpar lidas
        </button>
        
        <a href="/SistemaCPE/web/pages/tickets.html" 
           onclick="closeNotificationPanel(event)"
           class="link-todos-tickets">
          Ver todos os tickets →
        </a>
      </div>
  `;

  
  console.log("[NAV/NAVBAR] ✅ Navbar renderizada com sucesso");
  return true;
}

/* =========================================
   RENDERIZAR SIDEBAR
   ========================================= */

   async function renderSidebar() {
    console.log("[NAV/SIDEBAR] 🎯 Renderizando sidebar...");

    const sidebarContainer = document.getElementById("sidebar-container");

    if (!sidebarContainer) {
      console.error("[NAV/SIDEBAR] ❌ #sidebar-container não encontrado!");
      return false;
    }

    // ✅ CORRIGIDO: Obter role do usuário
    const userStr = localStorage.getItem("cpe_user");
    let userRole = "USER";
    let userId = null;

    if (userStr) {
      try {
        const userData = JSON.parse(userStr);
        userRole = userData.role || "USER";
        userId = userData.id || null;
        console.log("[NAV/SIDEBAR] 👤 Role do usuário: " + userRole);
      } catch (err) {
        console.warn("[NAV/SIDEBAR] ⚠️ Erro ao obter role:", err.message);
      }
    }

    // ==================================================
// RENDERIZAR SIDEBAR COM FILTRO POR ROLE + EXCEÇÕES
// Data: 01/04/2026 16:45
// ==================================================

    // ✅ Filtrar menu por role e exceções individuais
    const menuFiltered = await getFilteredMenu(userRole, userId);
    console.log("[NAV/SIDEBAR] ✅ Menu filtrado: " + menuFiltered.length + " itens visíveis");
  
    let menuHTML = `
      <div class="sidebar-wrapper">
        <div class="sidebar-logo-container"></div>
        <nav class="sidebar-nav">
          <ul class="sidebar-menu">
    `;

  // ✅ CORRIGIDO: Usar menuFiltered (não globalMenu) para respeitar permissões por role
  // Data: 01/04/2026 16:45
  // Renderiza o icone: se vier HTML cru (icones compostos tipo PC+$), usa
  // direto; senao gera <i class="bi XXX"></i> a partir do nome.
  const _renderMenuIcon = (icon) => {
    if (typeof icon === 'string' && icon.trim().startsWith('<')) return icon;
    return `<i class="bi ${icon}"></i>`;
  };
  menuFiltered.forEach((item, index) => {
    if (item.submenu && Array.isArray(item.submenu)) {
      menuHTML += `
        <li class="menu-item has-submenu" title="${item.label}">
          <a href="#" class="menu-link" onclick="toggleSubmenu(event, this)">
            <span class="menu-icon">
              ${_renderMenuIcon(item.icon)}
            </span>
            <span class="menu-label">${item.label}</span>
            <i class="bi bi-chevron-right submenu-arrow"></i>
          </a>
          <ul class="submenu">
            ${item.submenu.map(subitem => `
              <li class="submenu-item">
                <a href="${subitem.path}" class="submenu-link" onclick="updatePageTitle('${subitem.label}')">
                  ${_renderMenuIcon(subitem.icon)}
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
              ${_renderMenuIcon(item.icon)}
            </span>
            <span class="menu-label">${item.label}</span>
          </a>
        </li>
      `;
    }
  });
  // ================================================== 
  // [FIM] RENDERIZAR SIDEBAR COM FILTRO POR ROLE
  // Data: 01/04/2026 16:45
  // ==================================================

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
   CONECTA o botão #menuToggle (presente nas top-bars das páginas)
   à lógica de abrir/fechar a sidebar.
   - Em mobile (≤768px): abre/fecha como overlay (.show)
   - Em desktop:        alterna o modo colapsado (.collapsed)
   ========================================= */
function setupGlobalMenuToggle() {
  const btn = document.getElementById("menuToggle");
  if (!btn) return;
  if (btn.dataset.bound === "1") return;  // evita bind duplicado
  btn.dataset.bound = "1";

  btn.addEventListener("click", () => {
    const isMobile = window.matchMedia("(max-width: 768px)").matches;
    if (isMobile) {
      toggleSidebarMobile();
    } else {
      const sb = document.querySelector(".sidebar-wrapper");
      if (sb) sb.classList.toggle("collapsed");
    }
  });

  console.log("[NAV/TOGGLE] ✓ Botão #menuToggle conectado");
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
    // ✅ CORRIGIDO: removendo as chaves corretas usadas pelo sistema
    // tickets.js salva como "cpe_token" e "cpe_user"
    localStorage.removeItem("cpe_token");
    localStorage.removeItem("cpe_user");
    // Mantendo remoção das chaves antigas por compatibilidade
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
   SISTEMA DE NOTIFICAÇÕES
   ========================================= */

// --- Variáveis globais ---
let notificationsData = [];
let currentUserId = null;
let notificationCheckInterval = null;
const NOTIFICATIONS_API = (typeof API_BASE_URL !== 'undefined' ? API_BASE_URL : `http://${window.location.hostname || '127.0.0.1'}:8000`) + "/api/notificacoes";

// Inicializar notificações
function initNotifications() {
  try {
    console.log("[NAV/NOTIFICATIONS] ⚙️ Inicializando notificações...");
    
    // ✅ CORRIGIDO: chave unificada para "cpe_user" (igual ao tickets.js e app.py)
    const userStr = localStorage.getItem("cpe_user");
    if (!userStr) {
      console.warn("[NAV/NOTIFICATIONS] ⚠️ Usuário não autenticado (cpe_user não encontrado)");
      return;
    }
    
    const user = JSON.parse(userStr);
    currentUserId = user.id;
    
    if (!currentUserId) {
      console.warn("[NAV/NOTIFICATIONS] ⚠️ ID do usuário não encontrado no cpe_user");
      return;
    }
    
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

// Carregar notificações da API
async function loadNotifications() {
  try {
    if (!currentUserId) return;
    
    console.log("[NAV/NOTIFICATIONS] 📡 Carregando notificações...");
    
    const response = await fetch(`${NOTIFICATIONS_API}/usuario/${currentUserId}?limite=20`);
    
    if (response.status === 404) {
      console.warn("[NAV/NOTIFICATIONS] ⚠️ Endpoint não encontrado, usando localStorage");
      loadNotificationsFromStorage();
      return;
    }
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();

    // A API retorna { total, registros, limite, offset, notificacoes: [...] }
    const notifications = Array.isArray(data) ? data : (data.notificacoes || []);
    
    console.log("[NAV/NOTIFICATIONS] ✅ " + notifications.length + " notificação(ões)");
    
    // Armazenar no localStorage como fallback
    localStorage.setItem("notifications_" + currentUserId, JSON.stringify(notifications));
    
    notificationsData = notifications;

    // Merge convites de tarefas pendentes como notificações sintéticas
    await _mergeConvitesTask();

    updateNotificationUI();

  } catch (error) {
    console.error("[NAV/NOTIFICATIONS] ❌ Erro:", error);
    loadNotificationsFromStorage();
  }
}

// Busca convites pendentes e injeta no sino, garantindo que sempre apareçam
async function _mergeConvitesTask() {
  try {
    if (!currentUserId) return;
    const _api = (typeof API_BASE_URL !== 'undefined' ? API_BASE_URL : `http://${window.location.hostname || '127.0.0.1'}:8000`);
    const res = await fetch(`${_api}/api/tasks/convites?usuario_id=${currentUserId}`);
    if (!res.ok) return;
    const convites = await res.json();
    if (!Array.isArray(convites) || !convites.length) return;

    // Transforma convites em entradas de notificação (id negativo = sintético)
    const sinteticos = convites.map(c => ({
      id: -c.id,
      ticket_id: null,
      usuario_id: currentUserId,
      mensagem: `Convite para o quadro "${c.espaco_nome}" — convidado por ${c.convidado_por_nome || 'um gestor'}.`,
      tipo: 'convite_task',
      lido: false,
      created_at: c.created_at
    }));

    // Remove notificações convite_task do banco para evitar duplicatas
    const semConvitesDb = notificationsData.filter(n => n.tipo !== 'convite_task');
    notificationsData = [...sinteticos, ...semConvitesDb];
    console.log(`[NAV/NOTIFICATIONS] 📩 ${sinteticos.length} convite(s) de tarefa injetado(s) no sino`);
  } catch (_) {}
}

// Carregar do localStorage (fallback)
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

// Atualizar UI
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

// Atualizar badge do sino
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

// ========================================
// 🗑️ LIMPAR NOTIFICAÇÕES LIDAS - NOVO
// Data: 31/03/2026 15:10
// ========================================
// INÍCIO: Adicionar antes de closeNotificationPanel()

async function limparNotificacoesLidas(event) {
  if (event) {
    event.stopPropagation();
  }
  
  if (!currentUserId) {
    console.warn("[NAV/NOTIFICATIONS] ⚠️ Usuário não autenticado");
    return;
  }

  console.log("[NAV/NOTIFICATIONS] 🗑️ Iniciando limpeza de notificações lidas...");

  try {
    const response = await fetch(
      `${NOTIFICATIONS_API}/limpador/lidas?usuario_id=${currentUserId}`,
      {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json"
        }
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const resultado = await response.json();
    console.log("[NAV/NOTIFICATIONS] ✅ Limpeza concluída:", resultado);

    // Recarregar notificações
    await loadNotifications();

    // Feedback visual ao usuário
    if (resultado.total_deletadas > 0) {
      const mensagem = `${resultado.total_deletadas} notificação(ões) removida(s)`;
      console.log(`[NAV/NOTIFICATIONS] 📢 ${mensagem}`);
      alert(`✅ ${mensagem}`);
    } else {
      console.log("[NAV/NOTIFICATIONS] ℹ️ Nenhuma notificação lida para remover");
      alert("ℹ️ Nenhuma notificação lida para remover");
    }

  } catch (error) {
    console.error("[NAV/NOTIFICATIONS] ❌ Erro ao limpar:", error.message);
    alert("❌ Erro ao limpar notificações");
  }
}

// ========================================
// FIM DA FUNÇÃO - 31/03/2026 15:10
// ========================================

// Renderizar lista de notificações
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
           onclick="handleNotificationClick(${notif.id}, ${notif.ticket_id}, '${notif.tipo}')"
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

// Toggle painel de notificações
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

// Fechar painel de notificações
function closeNotificationPanel(event) {
  if (event) {
    event.stopPropagation();
  }
  
  const panel = document.getElementById("notificationPanel");
  if (panel) {
    panel.classList.remove("show");
  }
}

// Clique em notificação: marca como lida e redireciona para o ticket
async function handleNotificationClick(notificationId, ticketId, tipo) {
  console.log("[NAV/NOTIFICATIONS] 🔗 Clique #" + notificationId + " | Ticket #" + ticketId + " | Tipo: " + tipo);

  try {
    // Marcar como lida
    await markNotificationAsRead(notificationId);

    // Fechar painel
    closeNotificationPanel();

    // Redirecionar baseado no tipo
    // OBS: para tipos de Recepção, o campo `ticket_id` da tabela notificacoes
    // está sendo reaproveitado para guardar o id da reserva.
    const tiposReuniao = new Set([
      'convite_reuniao',
      'convite_aceito_reuniao',
      'convite_recusado_reuniao',
    ]);

    if (tipo && tipo.includes('convite') && tipo.includes('task')) {
      // Convites de quadro → ir para Tarefas
      window.location.href = '/SistemaCPE/web/pages/tasks.html';
    } else if (tipo === 'lembrete_agenda') {
      // Lembrete de compromisso → abre a Agenda
      window.location.href = '/SistemaCPE/web/pages/agenda.html';
    } else if (tipo === 'pre_cadastro_pendente') {
      // Solicitação de cadastro → abre Usuários focando na seção de pendentes
      window.location.href = '/SistemaCPE/web/pages/users.html?focus=pendentes';
    } else if (tiposReuniao.has(tipo) && ticketId) {
      // Convite/resposta de reunião → ir para Recepção e abrir a reserva
      window.location.href = `/SistemaCPE/web/pages/recepcao.html?reserva_id=${ticketId}`;
    } else if (ticketId) {
      // Notificação de ticket → ir para ticket
      window.location.href = `/SistemaCPE/web/pages/tickets.html?ticket_id=${ticketId}`;
    }

  } catch (error) {
    console.error("[NAV/NOTIFICATIONS] ❌ Erro:", error);
  }
}

// Marcar uma notificação como lida
async function markNotificationAsRead(notificationId) {
  try {
    if (!currentUserId || notificationId < 0) return; // ignora sintéticas (convites)

    // ✅ CORRIGIDO: adicionado ?usuario_id= obrigatório exigido pelo notificacoes.py
    // Sem esse parâmetro a API retornava erro 422 (Unprocessable Entity)
    const response = await fetch(
      `${NOTIFICATIONS_API}/${notificationId}?usuario_id=${currentUserId}`,
      {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ lido: true })
      }
    );
    
    if (response.ok) {
      console.log("[NAV/NOTIFICATIONS] ✅ Notificação #" + notificationId + " marcada como lida");
      await loadNotifications();
    } else {
      console.warn("[NAV/NOTIFICATIONS] ⚠️ Falha ao marcar lida: HTTP " + response.status);
    }
  } catch (error) {
    console.error("[NAV/NOTIFICATIONS] ❌ Erro ao marcar lida:", error);
  }
}

// Marcar todas como lidas
async function markAllAsRead() {
  try {
    if (!currentUserId) return;

    const unreadNotifs = notificationsData.filter(n => !n.lido && n.id > 0); // ignora sintéticas

    if (unreadNotifs.length === 0) return;
    
    console.log("[NAV/NOTIFICATIONS] 📋 Marcando " + unreadNotifs.length + " como lida(s)...");
    
    for (const notif of unreadNotifs) {
      // ✅ CORRIGIDO: adicionado ?usuario_id= em todas as chamadas PUT
      await fetch(
        `${NOTIFICATIONS_API}/${notif.id}?usuario_id=${currentUserId}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ lido: true })
        }
      );
    }
    
    await loadNotifications();
  } catch (error) {
    console.error("[NAV/NOTIFICATIONS] ❌ Erro:", error);
  }
}

/* =========================================
   FUNÇÕES AUXILIARES DE NOTIFICAÇÕES
   ========================================= */

// ✅ CORRIGIDO: tipos alinhados com os valores reais gravados no banco
// (notificacoes.py valida: "info","aviso","erro","sucesso","ticket_criado",
//  "nova_resposta","status_alterado","atribuido","comentario_interno")
function getNotificationIcon(tipo) {
  const icons = {
    "ticket_criado":            "🎫",
    "nova_resposta":            "💬",
    "status_alterado":          "🔄",
    "atribuido":                "👤",
    "comentario_interno":       "🔒",
    "avaliacao_pendente":       "⭐",
    "convite_task":             "📩",
    "convite_aceito_task":      "✅",
    "convite_recusado_task":    "❌",
    "convite_reuniao":          "📅",
    "convite_aceito_reuniao":   "✅",
    "convite_recusado_reuniao": "❌",
    "lembrete_agenda":          "🔔",
    "info":                     "ℹ️",
    "aviso":                    "⚠️",
    "erro":                     "❌",
    "sucesso":                  "✅"
  };
  return icons[tipo] || "📬";
}

function getTipoLabel(tipo) {
  const labels = {
    "ticket_criado":            "Ticket Criado",
    "nova_resposta":            "Nova Resposta",
    "status_alterado":          "Status Alterado",
    "atribuido":                "Ticket Atribuído",
    "comentario_interno":       "Comentário Interno",
    "avaliacao_pendente":       "Avaliação Pendente",
    "convite_task":             "Convite de Quadro",
    "convite_aceito_task":      "Convite Aceito",
    "convite_recusado_task":    "Convite Recusado",
    "convite_reuniao":          "Convite de Reunião",
    "convite_aceito_reuniao":   "Reunião Confirmada",
    "convite_recusado_reuniao": "Reunião Recusada",
    "lembrete_agenda":          "Lembrete da Agenda",
    "info":                     "Informação",
    "aviso":                    "Aviso",
    "erro":                     "Erro",
    "sucesso":                  "Sucesso"
  };
  return labels[tipo] || "Notificação";
}

function getTipoBadgeText(tipo) {
  const texts = {
    "ticket_criado":            "Criado",
    "nova_resposta":            "Resposta",
    "status_alterado":          "Status",
    "atribuido":                "Atribuído",
    "comentario_interno":       "Interno",
    "avaliacao_pendente":       "Avaliação",
    "convite_task":             "Convite",
    "convite_aceito_task":      "Aceito",
    "convite_recusado_task":    "Recusado",
    "convite_reuniao":          "Reunião",
    "convite_aceito_reuniao":   "Aceito",
    "convite_recusado_reuniao": "Recusado",
    "lembrete_agenda":          "Agenda",
    "info":                     "Info",
    "aviso":                    "Aviso",
    "erro":                     "Erro",
    "sucesso":                  "Sucesso"
  };
  return texts[tipo] || tipo;
}

function formatNotificationDate(dateString) {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000)    return "Agora";
    if (diff < 3600000)  return Math.floor(diff / 60000) + "m atrás";
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

async function initializeNavigation() {
  console.log("\n" + "=".repeat(80));
  console.log("[NAV/INIT] 🚀 Inicializando navegação");
  console.log("=".repeat(80));

  try {
    const navbarOk = renderNavbar();
    const sidebarOk = await renderSidebar();

    if (navbarOk && sidebarOk) {
      console.log("[NAV/INIT] ✅ Navegação inicializada com sucesso!");
      console.log("[NAV/INIT] 📊 Componentes:");
      console.log("[NAV/INIT]   ✓ Navbar");
      console.log("[NAV/INIT]   ✓ Sidebar");
      console.log("[NAV/INIT]   ✓ Menu items carregados");
      console.log("[NAV/INIT]   ✓ Sistema de notificações pronto");

      // Conecta o botão #menuToggle (top-bar das páginas) à sidebar
      setupGlobalMenuToggle();

      // Inicializar notificações
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

// =========================================
// CHAT GLOBAL NOTIFIER — carrega script global de chat em todas as paginas
// que usam navbar (sino + toast + popup chamada). O proprio script se
// auto-desativa em chat.html (la tem WS proprio).
// =========================================
(function loadChatGlobalNotifier() {
  if (document.querySelector('script[data-cgn]')) return;
  const s = document.createElement('script');
  s.src = '/SistemaCPE/web/assests/js/chat-global-notifier.js';
  s.setAttribute('data-cgn', '1');
  s.defer = true;
  document.head.appendChild(s);
})();