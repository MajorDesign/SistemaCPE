/**
 * ✅ Verifica se está na página de login
 */
function isLoginPage() {
  const path = (location.pathname || "").toLowerCase();
  return path.endsWith("/login.html") || path.endsWith("/login");
}

/**
 * ✅ REFATORADO: Proteger páginas usando localStorage
 * Não faz mais chamada a /api/auth/me
 */
async function protectPages() {
  console.log("\n[MAIN/PROTECT] 🔒 Verificando autenticação das páginas...");

  // Se estiver na página de login, não bloqueia
  if (isLoginPage()) {
    console.log("[MAIN/PROTECT] ✓ Página de login detectada, skip proteção");
    return;
  }

  try {
    // ✅ USAR LOCALSTORAGE AO INVÉS DE /api/auth/me
    console.log("[MAIN/PROTECT] 📝 Verificando dados em localStorage...");
    
    const isLoggedIn = localStorage.getItem("logged_in") === "true";
    const token = localStorage.getItem("token");
    const userStr = localStorage.getItem("user");

    console.log("[MAIN/PROTECT] 🔍 Status:");
    console.log("[MAIN/PROTECT]   • logged_in:", isLoggedIn ? "✓" : "✗");
    console.log("[MAIN/PROTECT]   • token:", token ? "✓" : "✗");
    console.log("[MAIN/PROTECT]   • user:", userStr ? "✓" : "✗");

    // ❌ Se não está autenticado
    if (!isLoggedIn || !token) {
      console.warn("[MAIN/PROTECT] ⚠️  Usuário não autenticado!");
      console.warn("[MAIN/PROTECT] 🔄 Redirecionando para login...");
      window.location.replace("./login.html");
      return;
    }

    // ✅ RECUPERAR E EXPOR USUÁRIO
    let user = null;

    if (userStr) {
      try {
        user = JSON.parse(userStr);
        console.log("[MAIN/PROTECT] ✓ Usuário parseado de localStorage.user");
      } catch (err) {
        console.warn("[MAIN/PROTECT] ⚠️  Erro ao fazer parse, usando fallback...");
        user = {
          id: localStorage.getItem("user_id"),
          username: localStorage.getItem("username"),
          name: localStorage.getItem("name"),
          email: localStorage.getItem("email"),
          role: localStorage.getItem("role")
        };
      }
    }

    if (!user || !user.id) {
      console.error("[MAIN/PROTECT] ❌ Dados de usuário inválidos");
      window.location.replace("./login.html");
      return;
    }

    // ✅ Expor no window para usar em outras páginas
    window.__ME__ = user;
    console.log("[MAIN/PROTECT] ✓ Usuário autenticado:", user.name);
    console.log("[MAIN/PROTECT] ✓ Dados disponíveis em window.__ME__");
    console.log("[MAIN/PROTECT] ✅ Proteção concluída\n");

  } catch (err) {
    console.error("[MAIN/PROTECT] ❌ ERRO:", err.message);
    console.warn("[MAIN/PROTECT] 🔄 Redirecionando para login...\n");
    window.location.replace("./login.html");
  }
}

/**
 * ✅ Setup de Menu Mobile
 */
function setupMobileMenu() {
  console.log("[MAIN/MENU] 📱 Configurando menu mobile...");

  const menuToggle = document.querySelector('.menu-toggle');
  const sidebar = document.querySelector('.sidebar');

  if (!menuToggle || !sidebar) {
    console.warn("[MAIN/MENU] ⚠️  Elementos não encontrados");
    return;
  }

  // ✅ Toggle menu ao clicar no botão
  menuToggle.addEventListener('click', function(e) {
    e.stopPropagation();
    sidebar.classList.toggle('active');
    console.log("[MAIN/MENU] ☰ Menu toggled");
  });

  // ✅ Fechar menu ao clicar em um item
  const menuLinks = document.querySelectorAll('.menu-link');
  menuLinks.forEach(link => {
    link.addEventListener('click', function() {
      if (window.innerWidth <= 768) {
        sidebar.classList.remove('active');
        console.log("[MAIN/MENU] ✓ Menu fechado (item clicado)");
      }
    });
  });

  // ✅ Definir item ativo baseado na página atual
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  menuLinks.forEach(link => {
    const href = link.getAttribute('href');
    if (href === currentPage || (currentPage === '' && href === 'index.html')) {
      link.classList.add('active');
      console.log("[MAIN/MENU] ✓ Item ativo:", currentPage);
    }
  });

  // ✅ Fechar menu ao clicar fora
  document.addEventListener('click', function(event) {
    if (!sidebar.contains(event.target) && !menuToggle.contains(event.target)) {
      if (window.innerWidth <= 768 && sidebar.classList.contains('active')) {
        sidebar.classList.remove('active');
        console.log("[MAIN/MENU] ✓ Menu fechado (clique fora)");
      }
    }
  });

  console.log("[MAIN/MENU] ✅ Menu mobile configurado");
}

/**
 * ✅ Setup de Busca
 */
function setupSearch() {
  console.log("[MAIN/SEARCH] 🔍 Configurando busca...");

  const searchBox = document.querySelector('.search-box input');
  if (!searchBox) {
    console.warn("[MAIN/SEARCH] ⚠️  Input de busca não encontrado");
    return;
  }

  searchBox.addEventListener('input', function(e) {
    const query = e.target.value.toLowerCase();
    const menuItems = document.querySelectorAll('.menu-item');
    
    let visibleCount = 0;
    menuItems.forEach(item => {
      const text = item.textContent.toLowerCase();
      const shouldShow = text.includes(query);
      item.style.display = shouldShow ? 'block' : 'none';
      if (shouldShow) visibleCount++;
    });

    console.log(`[MAIN/SEARCH] 🔎 Query: "${query}" | Itens visíveis: ${visibleCount}`);
  });

  console.log("[MAIN/SEARCH] ✅ Busca configurada");
}

/**
 * ✅ INICIALIZAÇÃO PRINCIPAL
 */
document.addEventListener('DOMContentLoaded', () => {
  console.log("\n" + "=".repeat(80));
  console.log("[MAIN] 🎬 Inicializando main.js...");
  console.log("=".repeat(80));

  try {
    // 1️⃣ Proteger página (redireciona se não logado)
    protectPages();

    // 2️⃣ Setup de menu mobile
    setupMobileMenu();

    // 3️⃣ Setup de busca
    setupSearch();

    console.log("[MAIN] ✅ Tudo inicializado com sucesso!");
    console.log("=".repeat(80) + "\n");

  } catch (err) {
    console.error("[MAIN] ❌ ERRO NA INICIALIZAÇÃO:", err.message);
    console.error("[MAIN] Stack:", err.stack);
    console.error("=".repeat(80) + "\n");
  }
});

/**
 * ⚠️ HELPER: Obter usuário atual (compatibilidade)
 * Use window.__ME__ após protectPages()
 */
function getCurrentUserFromPage() {
  return window.__ME__ || null;
}