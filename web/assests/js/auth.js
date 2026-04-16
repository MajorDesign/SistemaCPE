console.log("=".repeat(80));
console.log("[AUTH.JS] 🔐 Carregando módulo de autenticação");
console.log("[AUTH.JS] ⚙️  Modo: SEM BLOQUEIO - Acesso Público Permitido");
console.log("=".repeat(80) + "\n");

// ============================================================
// 🔐 GERENCIAMENTO DE TOKENS
// ============================================================

/**
 * Obtém o token de qualquer storage
 * @returns {string|null} - Token ou null
 */
function getToken() {
  const token = localStorage.getItem("token") || 
                sessionStorage.getItem("token") ||
                localStorage.getItem("access_token") ||
                sessionStorage.getItem("access_token");
  
  if (token) {
    console.log("[AUTH/TOKEN] ✓ Token encontrado");
    return token;
  }
  
  console.log("[AUTH/TOKEN] ℹ️  Nenhum token encontrado - Modo público");
  return null;
}

/**
 * Salva o token em localStorage e sessionStorage
 * @param {string} token - Token a ser salvo
 * @returns {boolean} - true se salvo com sucesso
 */
function saveToken(token) {
  if (!token) {
    console.error("[AUTH/SAVE-TOKEN] ✗ Token vazio");
    return false;
  }
  
  try {
    localStorage.setItem("token", token);
    sessionStorage.setItem("token", token);
    console.log("[AUTH/SAVE-TOKEN] ✓ Token salvo com sucesso");
    return true;
  } catch (err) {
    console.error("[AUTH/SAVE-TOKEN] ✗ Erro ao salvar token:", err.message);
    return false;
  }
}

/**
 * Remove o token de todos os storages
 */
function removeToken() {
  try {
    localStorage.removeItem("token");
    localStorage.removeItem("access_token");
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("access_token");
    console.log("[AUTH/REMOVE-TOKEN] ✓ Token removido");
  } catch (err) {
    console.error("[AUTH/REMOVE-TOKEN] ✗ Erro ao remover token:", err.message);
  }
}

// ============================================================
// 👤 GERENCIAMENTO DE USUÁRIO
// ============================================================

/**
 * Obtém os dados do usuário da API
 * @returns {Object} - Objeto do usuário ou usuário público
 */
async function getMe() {
  try {
    console.log("[AUTH/GETME] 🔍 Buscando dados do usuário...");

    const token = getToken();
    
    // ✅ SE NÃO HÁ TOKEN, RETORNAR USUÁRIO PÚBLICO
    if (!token) {
      console.log("[AUTH/GETME] 🔓 Sem token - Retornando usuário público");
      
      const publicUser = {
        id: "public",
        name: "Visitante",
        email: "public@sistemacpe.local",
        role: "USER",
        is_admin: 0,
        is_manager: 0,
        is_active: 1,
        department_id: null,
        group_id: null,
        group_name: null,
        created_at: null,
        updated_at: null
      };
      
      setCurrentUser(publicUser);
      return publicUser;
    }

    console.log("[AUTH/GETME] 🔑 Token encontrado");
    console.log("[AUTH/GETME] 📡 Tentando chamar API /api/users/me...");

    const response = await fetch("http://localhost:8000/api/users/me", {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      }
    });

    console.log("[AUTH/GETME] 📊 Status da resposta:", response.status);

    // ✅ SE API FALHAR, RETORNAR USUÁRIO DO LOCALSTORAGE OU PÚBLICO
    if (!response.ok) {
      console.warn(`[AUTH/GETME] ⚠️  API retornou ${response.status} - Usando fallback`);
      
      const savedUser = getCurrentUser();
      if (savedUser && savedUser.id) {
        console.log("[AUTH/GETME] ✓ Usando usuário salvo do localStorage");
        return savedUser;
      }
      
      // Retornar usuário público
      const publicUser = {
        id: "public",
        name: "Visitante",
        email: "public@sistemacpe.local",
        role: "USER",
        is_admin: 0,
        is_manager: 0,
        is_active: 1,
        department_id: null,
        group_id: null,
        group_name: null,
        created_at: null,
        updated_at: null
      };
      
      setCurrentUser(publicUser);
      return publicUser;
    }

    const data = await response.json();
    console.log("[AUTH/GETME] 📊 Dados recebidos da API");

    // ✅ EXTRAIR USUÁRIO
    let user = null;
    
    if (data && data.user && typeof data.user === 'object') {
      user = data.user;
    } else if (data && data.data && typeof data.data === 'object') {
      user = data.data;
    } else if (data && (data.id || data.email)) {
      user = data;
    }

    if (!user || !user.id) {
      console.warn("[AUTH/GETME] ⚠️  Usuário inválido na resposta");
      return getCurrentUser() || {
        id: "public",
        name: "Visitante",
        email: "public@sistemacpe.local",
        role: "USER",
        is_admin: 0,
        is_manager: 0,
        is_active: 1
      };
    }

    // ✅ NORMALIZAR USUÁRIO
    const normalizedUser = {
      id: user.id,
      name: user.name || "Usuário",
      email: user.email || "",
      role: user.role || "USER",
      is_admin: user.is_admin === 1 || user.is_admin === true ? 1 : 0,
      department_id: user.department_id || null,
      group_id: user.group_id || null,
      group_name: user.group_name || null,
      is_manager: user.is_manager === 1 || user.is_manager === true ? 1 : 0,
      is_active: user.is_active !== undefined ? user.is_active : 1,
      created_at: user.created_at || null,
      updated_at: user.updated_at || null,
      ...user
    };

    console.log("[AUTH/GETME] ✅ Usuário carregado:", {
      id: normalizedUser.id,
      name: normalizedUser.name,
      email: normalizedUser.email,
      role: normalizedUser.role
    });

    setCurrentUser(normalizedUser);
    return normalizedUser;

  } catch (err) {
    console.warn("[AUTH/GETME] ⚠️  Erro ao chamar API:", err.message);
    console.log("[AUTH/GETME] 🔓 Continuando com modo público");
    
    // ✅ RETORNAR USUÁRIO PÚBLICO MESMO COM ERRO
    const publicUser = {
      id: "public",
      name: "Visitante",
      email: "public@sistemacpe.local",
      role: "USER",
      is_admin: 0,
      is_manager: 0,
      is_active: 1,
      department_id: null,
      group_id: null,
      group_name: null
    };
    
    setCurrentUser(publicUser);
    return publicUser;
  }
}

/**
 * Obtém o usuário armazenado localmente
 * @returns {Object|null} - Usuário ou null
 */
function getCurrentUser() {
  try {
    const userStr = localStorage.getItem("user");
    if (!userStr) {
      console.log("[AUTH/GET-CURRENT] ℹ️  Nenhum usuário armazenado");
      return null;
    }
    const user = JSON.parse(userStr);
    console.log("[AUTH/GET-CURRENT] ✓ Usuário recuperado:", user.name);
    return user;
  } catch (err) {
    console.warn("[AUTH/GET-CURRENT] ⚠️  Erro ao parsear usuário:", err.message);
    return null;
  }
}

/**
 * Armazena o usuário em localStorage e sessionStorage
 * @param {Object} user - Objeto do usuário
 */
function setCurrentUser(user) {
  try {
    if (user && user.id) {
      const userStr = JSON.stringify(user);
      localStorage.setItem("user", userStr);
      sessionStorage.setItem("user", userStr);
      console.log("[AUTH/SET-CURRENT] ✓ Usuário armazenado:", user.name);
    } else {
      localStorage.removeItem("user");
      sessionStorage.removeItem("user");
      console.log("[AUTH/SET-CURRENT] ✓ Usuário removido");
    }
  } catch (err) {
    console.error("[AUTH/SET-CURRENT] ✗ Erro:", err.message);
  }
}

/**
 * Remove o usuário de todos os storages
 */
function removeCurrentUser() {
  try {
    localStorage.removeItem("user");
    localStorage.removeItem("userRole");
    localStorage.removeItem("isAdmin");
    sessionStorage.removeItem("user");
    console.log("[AUTH/REMOVE-CURRENT] ✓ Usuário removido");
  } catch (err) {
    console.error("[AUTH/REMOVE-CURRENT] ✗ Erro:", err.message);
  }
}

// ============================================================
// 🔐 VERIFICAÇÃO DE AUTENTICAÇÃO (SEM BLOQUEIO)
// ============================================================

/**
 * Verifica se o usuário está autenticado
 * @returns {boolean} - true se tem token válido
 */
async function checkAuth() {
  try {
    console.log("[AUTH/CHECK] 🔍 Verificando autenticação...");
    
    const token = getToken();
    if (!token) {
      console.log("[AUTH/CHECK] ℹ️  Nenhum token - Modo público");
      return false;
    }

    const user = await getMe();
    const isAuth = user && user.id && user.id !== "public" ? true : false;
    
    console.log(`[AUTH/CHECK] ${isAuth ? '✓ Autenticado' : 'ℹ️  Modo público'}`);
    return isAuth;

  } catch (err) {
    console.warn("[AUTH/CHECK] ⚠️  Erro:", err.message);
    return false;
  }
}

/**
 * Verifica se o usuário é administrador
 * @param {Object} user - Usuário (opcional, usa o atual se não fornecido)
 * @returns {boolean} - true se é admin
 */
function isAdmin(user = null) {
  if (!user) {
    user = getCurrentUser();
  }
  
  if (!user) {
    return false;
  }
  
  return user.is_admin === 1 || 
         user.is_admin === true || 
         user.role === "ADMIN";
}

/**
 * Verifica se o usuário é gerente
 * @param {Object} user - Usuário (opcional, usa o atual se não fornecido)
 * @returns {boolean} - true se é gerente
 */
function isManager(user = null) {
  if (!user) {
    user = getCurrentUser();
  }
  
  if (!user) {
    return false;
  }
  
  return user.is_manager === 1 || user.is_manager === true;
}

// ============================================================
// 🔄 INICIALIZAR PÁGINA COM AUTENTICAÇÃO (SEM BLOQUEIO)
// ============================================================

/**
 * Inicializa autenticação da página - SEM BLOQUEIO
 * @param {string} pageName - Nome da página para logs
 * @returns {Object} - Dados do usuário (sempre retorna algo)
 */
async function initPageAuth(pageName = "PÁGINA") {
  console.log("\n" + "=".repeat(80));
  console.log(`[${pageName}/INIT] 🔐 INICIALIZANDO PÁGINA`);
  console.log(`[${pageName}/INIT] ⚙️  Modo: SEM BLOQUEIO - Acesso público permitido`);
  console.log("=".repeat(80));

  const loadingPage = document.getElementById("loadingPage");
  const containerMain = document.querySelector(".container-main");

  try {
    console.log(`[${pageName}/INIT] 📋 Storage atual:`);
    console.log(`[${pageName}/INIT]   localStorage.token: ${localStorage.getItem("token") ? "✓" : "✗"}`);
    console.log(`[${pageName}/INIT]   localStorage.user: ${localStorage.getItem("user") ? "✓" : "✗"}`);

    // ✅ OBTER USUÁRIO (COM OU SEM AUTENTICAÇÃO)
    console.log(`\n[${pageName}/INIT] 👤 Obtendo dados do usuário...`);
    const user = await getMe();
    
    console.log(`[${pageName}/INIT] ✓ Usuário: ${user.name} (${user.role})`);

    // ✅ REMOVER LOADING
    if (loadingPage) {
      loadingPage.style.display = "none";
      console.log(`[${pageName}/INIT] ✓ Loading removido`);
    }

    // ✅ MOSTRAR CONTEÚDO
    if (containerMain) {
      containerMain.style.display = "flex";
      console.log(`[${pageName}/INIT] ✓ Conteúdo exibido`);
    }

    // ✅ RENDERIZAR NAVEGAÇÃO
    if (typeof renderNavigation === "function") {
      try {
        await renderNavigation(user.role || "USER");
        console.log(`[${pageName}/INIT] ✓ Navegação renderizada`);
      } catch (err) {
        console.warn(`[${pageName}/INIT] ⚠️  Erro na navegação:`, err.message);
      }
    }

    // ✅ ATUALIZAR SIDEBAR
    if (typeof updateSidebarUser === "function") {
      try {
        updateSidebarUser(user);
        console.log(`[${pageName}/INIT] ✓ Sidebar atualizado`);
      } catch (err) {
        console.warn(`[${pageName}/INIT] ⚠️  Erro no sidebar:`, err.message);
      }
    }

    // ✅ ATUALIZAR NAVBAR
    if (typeof updateUserInfo === "function") {
      try {
        updateUserInfo(user);
        console.log(`[${pageName}/INIT] ✓ Navbar atualizado`);
      } catch (err) {
        console.warn(`[${pageName}/INIT] ⚠️  Erro na navbar:`, err.message);
      }
    }

    console.log(`\n[${pageName}/INIT] ✅ PÁGINA INICIALIZADA`);
    console.log(`[${pageName}/INIT] 🔓 Modo: ${user.id === 'public' ? 'PÚBLICO' : 'AUTENTICADO'}`);
    console.log("=".repeat(80) + "\n");

    return user;

  } catch (err) {
    console.warn(`\n[${pageName}/INIT] ⚠️  ERRO`);
    console.warn(`[${pageName}/INIT] 📍 ${err.message}`);

    // ✅ MESMO COM ERRO, MOSTRAR PÁGINA
    if (loadingPage) {
      loadingPage.style.display = "none";
    }

    if (containerMain) {
      containerMain.style.display = "flex";
    }

    console.log(`[${pageName}/INIT] 🔓 Continuando com modo público`);
    console.log("=".repeat(80) + "\n");

    // ✅ RETORNAR USUÁRIO PÚBLICO
    return {
      id: "public",
      name: "Visitante",
      email: "public@sistemacpe.local",
      role: "USER",
      is_admin: 0,
      is_manager: 0,
      is_active: 1
    };
  }
}

// ============================================================
// 🚪 LOGOUT
// ============================================================

/**
 * Faz logout do usuário
 */
async function logout() {
  try {
    console.log("[AUTH/LOGOUT] 🔓 Iniciando logout...");

    // ✅ TENTAR CHAMAR API DE LOGOUT (NÃO OBRIGATÓRIO)
    try {
      const token = getToken();
      if (token) {
        console.log("[AUTH/LOGOUT] 📡 Notificando servidor...");
        await fetch("http://localhost:8000/api/auth/logout", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          }
        });
        console.log("[AUTH/LOGOUT] ✓ Logout confirmado no servidor");
      }
    } catch (apiErr) {
      console.log("[AUTH/LOGOUT] ℹ️  Servidor não responde - continuando");
    }

    // ✅ LIMPAR STORAGE LOCALMENTE
    console.log("[AUTH/LOGOUT] 🗑️  Limpando storage...");
    removeToken();
    removeCurrentUser();

    console.log("[AUTH/LOGOUT] ✓ Logout bem-sucedido");
    console.log("[AUTH/LOGOUT] 🔄 Redirecionando para login...");

    window.location.href = "/SistemaCPE/web/login.html";

  } catch (err) {
    console.error("[AUTH/LOGOUT] ✗ Erro:", err.message);
    window.location.href = "/SistemaCPE/web/login.html";
  }
}

// ============================================================
// 🔄 REFRESH TOKEN
// ============================================================

/**
 * Atualiza o token
 * @returns {string|null} - Novo token ou null
 */
async function refreshToken() {
  try {
    console.log("[AUTH/REFRESH] 🔄 Atualizando token...");

    const token = getToken();
    if (!token) {
      console.log("[AUTH/REFRESH] ℹ️  Sem token para atualizar");
      return null;
    }

    const response = await fetch("http://localhost:8000/api/auth/refresh", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      }
    });

    if (!response.ok) {
      console.warn(`[AUTH/REFRESH] ⚠️  Falha ao atualizar (${response.status})`);
      return null;
    }

    const data = await response.json();
    const newToken = data.token || data.access_token;

    if (newToken) {
      saveToken(newToken);
      console.log("[AUTH/REFRESH] ✓ Token atualizado");
      return newToken;
    }

    console.warn("[AUTH/REFRESH] ⚠️  Nenhum token na resposta");
    return null;

  } catch (err) {
    console.warn("[AUTH/REFRESH] ⚠️  Erro:", err.message);
    return null;
  }
}

// ============================================================
// 🎨 UI - MOSTRAR ERROS
// ============================================================

/**
 * Mostra erro de autenticação
 * @param {string} message - Mensagem de erro
 */
function showAuthError(message) {
  try {
    // ✅ TENTAR USAR FUNÇÃO GLOBAL
    if (typeof showError === "function") {
      showError(`Erro: ${message}`);
      return;
    }

    // ✅ FALLBACK: CRIAR ALERTA
    const alertDiv = document.createElement("div");
    alertDiv.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #dc3545;
      color: white;
      padding: 20px;
      border-radius: 8px;
      max-width: 400px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      z-index: 10000;
      font-family: Arial, sans-serif;
    `;
    alertDiv.innerHTML = `
      <strong>⚠️  Aviso</strong><br>
      ${message}
    `;
    document.body.appendChild(alertDiv);

    setTimeout(() => {
      alertDiv.remove();
    }, 5000);

  } catch (err) {
    console.error("[AUTH/ERROR] ✗ Erro ao mostrar alerta:", err.message);
  }
}

// ============================================================
// ✅ INICIALIZAÇÃO
// ============================================================

console.log("[AUTH.JS] ✅ Módulo de autenticação carregado");
console.log("[AUTH.JS] 🔓 Acesso público: ATIVADO");
console.log("[AUTH.JS] ⚠️  Todos os bloqueios foram removidos\n");