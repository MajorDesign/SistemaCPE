// ============================================================
// ⚙️ CONFIGURAÇÃO INICIAL
// ============================================================

if (typeof API_BASE_URL === 'undefined') {
  // ✅ URL da API
  window.API_BASE_URL = "http://localhost:8000";
  console.warn("[CONFIG] API_BASE_URL não encontrada em config.js, usando default");
}

console.log("[CONFIG] API_BASE_URL:", API_BASE_URL);
console.log("[CONFIG] 🌐 Origem da página:", window.location.origin);
console.log("[CONFIG] 🔗 Será enviado para:", API_BASE_URL);
console.log("[CONFIG] Módulo api.js carregado com sucesso!");

// ============================================================
// 🔄 FUNÇÃO AUXILIAR - REQUISIÇÕES GENÉRICAS
// ============================================================

async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const method = options.method || "GET";

  console.log(`[API] ${method} ${endpoint}`);
  console.log(`[API] 🔗 URL completa: ${url}`);

  const defaultOptions = {
    method: method,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  };

  try {
    console.log("[API] 📤 Enviando requisição...");
    const response = await fetch(url, defaultOptions);

    console.log(`[API] ✓ Response: ${response.status} ${response.statusText}`);

    // Trata erro genérico
    if (!response.ok) {
      let errorData = {};
      try {
        errorData = await response.json();
      } catch (e) {
        console.warn("[API] Não conseguiu fazer parse do JSON de erro");
      }

      const errorMessage = 
        errorData.detail || 
        errorData.message || 
        errorData.error ||
        `Erro ${response.status}: ${response.statusText}`;
      
      console.error(`[API] ✗ ${errorMessage}`);
      throw new Error(errorMessage);
    }

    const responseData = await response.json();
    console.log(`[API] ✓ Data:`, responseData);

    return responseData;

  } catch (err) {
    console.error(`[API] ✗ Erro em apiFetch:`, err.message);
    throw err;
  }
}

// ============================================================
// 🗑️ FUNÇÃO AUXILIAR - LIMPAR TODO ARMAZENAMENTO
// ============================================================

function clearAllStorage() {
  console.log("[STORAGE] 🗑️ Limpando todo armazenamento...");
  
  const keysToRemove = [
    "token",
    "access_token",
    "user",
    "user_id",
    "username",
    "name",
    "email",
    "role",
    "userRole",
    "isAdmin",
    "logged_in",
    "login_time",
    "department_id",
    "group_id",
    "group_name",
    "is_manager"
  ];

  // localStorage
  keysToRemove.forEach(key => {
    if (localStorage.getItem(key)) {
      localStorage.removeItem(key);
      console.log(`[STORAGE] ✓ Removido localStorage.${key}`);
    }
  });

  // sessionStorage
  ["token", "access_token", "user"].forEach(key => {
    if (sessionStorage.getItem(key)) {
      sessionStorage.removeItem(key);
      console.log(`[STORAGE] ✓ Removido sessionStorage.${key}`);
    }
  });

  console.log("[STORAGE] ✅ Armazenamento limpo");
}

// ============================================================
// 💾 FUNÇÃO AUXILIAR - SALVAR DADOS DO USUÁRIO
// ============================================================

function saveUserData(user) {
  console.log("[STORAGE] 💾 Salvando dados do usuário...");
  
  try {
    // Salvar dados individuais
    localStorage.setItem("user_id", user.id.toString());
    localStorage.setItem("username", user.username);
    localStorage.setItem("name", user.name);
    localStorage.setItem("email", user.email);
    localStorage.setItem("role", user.role);
    localStorage.setItem("logged_in", "true");
    localStorage.setItem("login_time", new Date().toISOString());
    console.log("[STORAGE] ✓ Dados individuais salvos");

    // Salvar usuário completo
    localStorage.setItem("user", JSON.stringify(user));
    console.log("[STORAGE] ✓ Usuário JSON salvo");

    // Salvar dados adicionais
    if (user.role) {
      localStorage.setItem("userRole", user.role);
    }
    if (user.group_id) {
      localStorage.setItem("group_id", user.group_id.toString());
    }
    console.log("[STORAGE] ✓ Dados adicionais salvos");

  } catch (err) {
    console.error("[STORAGE] ❌ Erro ao salvar dados:", err.message);
    throw new Error("Falha ao salvar dados do usuário");
  }
}

// ============================================================
// 👤 FUNÇÕES DE USUÁRIO (SEM AUTENTICAÇÃO)
// ============================================================

/**
 * ✅ Obter usuário atual do localStorage
 */
function getCurrentUser() {
  console.log("[USER] 👤 Obtendo usuário atual do localStorage...");
  
  const userStr = localStorage.getItem("user");
  if (userStr) {
    try {
      const user = JSON.parse(userStr);
      console.log("[USER] ✓ Usuário recuperado:", user.name);
      return user;
    } catch (err) {
      console.error("[USER] ✗ Erro ao fazer parse do JSON:", err.message);
    }
  }
  
  // ✅ Fallback para campos individuais
  const simpleUser = {
    id: localStorage.getItem("user_id"),
    username: localStorage.getItem("username"),
    name: localStorage.getItem("name"),
    role: localStorage.getItem("role"),
    email: localStorage.getItem("email"),
    group_id: localStorage.getItem("group_id"),
    login_time: localStorage.getItem("login_time")
  };

  if (simpleUser.id) {
    console.log("[USER] ✓ Usuário recuperado dos dados individuais:", simpleUser.name);
    return simpleUser;
  }

  console.log("[USER] ✗ Nenhum usuário encontrado");
  return null;
}

/**
 * ✅ Verificar se há usuário logado
 */
function isUserLoaded() {
  const user = getCurrentUser();
  const isLoaded = !!user && user.id;
  console.log("[USER] 🔍 Usuário carregado:", isLoaded ? "✓ SIM" : "✗ NÃO");
  return isLoaded;
}

/**
 * ✅ Carregar usuário (simula login sem autenticação)
 */
async function loadUser(userId) {
  console.log("\n" + "=".repeat(80));
  console.log("[USER/LOAD] 👤 Carregando usuário #" + userId + "...");
  console.log("=".repeat(80));
  
  try {
    const response = await apiFetch(`/api/users/${userId}`, {
      method: "GET"
    });

    if (!response || !response.id) {
      console.error("[USER/LOAD] ✗ Dados do usuário inválidos");
      throw new Error("Usuário não encontrado");
    }

    console.log("[USER/LOAD] 👤 Usuário carregado:", {
      id: response.id,
      name: response.name,
      email: response.email,
      username: response.username,
      role: response.role
    });

    // ✅ Salvar dados
    saveUserData(response);

    console.log("[USER/LOAD] ✓ Verificação final de armazenamento:");
    console.log("[USER/LOAD]   • localStorage.user:", localStorage.getItem("user") ? "✓ EXISTE" : "✗ NÃO EXISTE");
    console.log("[USER/LOAD]   • localStorage.user_id:", localStorage.getItem("user_id") || "✗ NÃO EXISTE");
    console.log("[USER/LOAD]   • localStorage.name:", localStorage.getItem("name") || "✗ NÃO EXISTE");
    console.log("[USER/LOAD]   • localStorage.email:", localStorage.getItem("email") || "✗ NÃO EXISTE");

    console.log("[USER/LOAD] ✅ Usuário carregado com sucesso!");
    console.log("=".repeat(80) + "\n");

    return {
      success: true,
      user: response
    };

  } catch (err) {
    console.error("[USER/LOAD] ❌ ERRO AO CARREGAR USUÁRIO");
    console.error("[USER/LOAD] 📍 Mensagem:", err.message);
    console.error("=".repeat(80) + "\n");
    throw err;
  }
}

/**
 * ✅ Logout - Limpa dados do usuário
 */
async function logout() {
  console.log("\n[USER/LOGOUT] 🔓 Iniciando logout...");
  
  try {
    // ✅ LIMPAR TODO ARMAZENAMENTO
    clearAllStorage();

    console.log("[USER/LOGOUT] ✓ Logout bem-sucedido");
    console.log("[USER/LOGOUT] 🔄 Redirecionando para dashboard...\n");
    
    window.location.href = "/SistemaCPE/index.html";

  } catch (err) {
    console.error("[USER/LOGOUT] ✗ Erro:", err.message);
    console.error("[USER/LOGOUT] 🔄 Redirecionando para dashboard mesmo assim...\n");
    clearAllStorage();
    window.location.href = "/SistemaCPE/index.html";
  }
}

// ============================================================
// 📋 FUNÇÕES DO COFRE DE SENHAS
// ============================================================

async function apiGetPasswords() {
  console.log("[VAULT/API] 📋 Carregando senhas...");
  
  try {
    const response = await apiFetch("/api/passwords/", { method: "GET" });
    
    let passwords = [];
    if (Array.isArray(response)) {
      passwords = response;
    } else if (response && response.passwords && Array.isArray(response.passwords)) {
      passwords = response.passwords;
    } else if (response && response.data && Array.isArray(response.data)) {
      passwords = response.data;
    }
    
    console.log("[VAULT/API] ✓ Senhas carregadas:", passwords.length);
    return passwords;
    
  } catch (err) {
    console.error("[VAULT/API] ✗ Erro:", err.message);
    return [];
  }
}

async function apiGetPassword(id) {
  console.log(`[VAULT/API] 🔑 Carregando senha #${id}...`);
  
  try {
    const response = await apiFetch(`/api/passwords/${id}`, { method: "GET" });
    console.log("[VAULT/API] ✓ Senha carregada:", response);
    return response;
    
  } catch (err) {
    console.error("[VAULT/API] ✗ Erro:", err.message);
    throw err;
  }
}

async function apiCreatePassword(data) {
  console.log("[VAULT/API] ➕ Criando nova senha...");
  console.log("[VAULT/API] 📊 Dados:", {
    client: data.client,
    description: data.description,
    email: data.email || "N/A",
    group_id: data.group_id || "N/A"
  });
  
  try {
    const response = await apiFetch("/api/passwords/", {
      method: "POST",
      body: JSON.stringify(data)
    });
    console.log("[VAULT/API] ✓ Senha criada:", response);
    return response;
    
  } catch (err) {
    console.error("[VAULT/API] ✗ Erro:", err.message);
    throw err;
  }
}

async function apiUpdatePassword(id, data) {
  console.log(`[VAULT/API] ✏️ Atualizando senha #${id}...`);
  console.log("[VAULT/API] 📊 Dados:", {
    client: data.client,
    description: data.description,
    email: data.email || "N/A"
  });
  
  try {
    const response = await apiFetch(`/api/passwords/${id}`, {
      method: "PUT",
      body: JSON.stringify(data)
    });
    console.log("[VAULT/API] ✓ Senha atualizada:", response);
    return response;
    
  } catch (err) {
    console.error("[VAULT/API] ✗ Erro:", err.message);
    throw err;
  }
}

async function apiDeletePassword(id) {
  console.log(`[VAULT/API] 🗑️ Deletando senha #${id}...`);
  
  try {
    const response = await apiFetch(`/api/passwords/${id}`, {
      method: "DELETE"
    });
    console.log("[VAULT/API] ✓ Senha deletada:", response);
    return response;
    
  } catch (err) {
    console.error("[VAULT/API] ✗ Erro:", err.message);
    throw err;
  }
}

async function apiGetPublicPasswords() {
  console.log("[VAULT/API] 🌐 Carregando senhas públicas...");
  
  try {
    const response = await apiFetch("/api/passwords/public/all", { method: "GET" });
    
    let passwords = [];
    if (Array.isArray(response)) {
      passwords = response;
    } else if (response && response.passwords && Array.isArray(response.passwords)) {
      passwords = response.passwords;
    } else if (response && response.data && Array.isArray(response.data)) {
      passwords = response.data;
    }
    
    console.log("[VAULT/API] ✓ Senhas públicas carregadas:", passwords.length);
    return passwords;
    
  } catch (err) {
    console.error("[VAULT/API] ✗ Erro:", err.message);
    return [];
  }
}

// ============================================================
// 📁 FUNÇÕES DE GRUPOS
// ============================================================

async function apiGetPasswordGroups() {
  console.log("[VAULT/API] 📂 Carregando grupos...");
  
  try {
    const response = await apiFetch("/api/passwords/groups", { method: "GET" });
    
    let groups = [];
    if (Array.isArray(response)) {
      groups = response;
    } else if (response && response.groups && Array.isArray(response.groups)) {
      groups = response.groups;
    } else if (response && response.data && Array.isArray(response.data)) {
      groups = response.data;
    }
    
    console.log("[VAULT/API] ✓ Grupos carregados:", groups.length);
    return groups;
    
  } catch (err) {
    console.error("[VAULT/API] ✗ Erro ao carregar grupos:", err.message);
    return [];
  }
}

async function apiCreatePasswordGroup(name) {
  console.log("[VAULT/API] ➕ Criando grupo:", name);
  
  try {
    const response = await apiFetch("/api/passwords/groups", {
      method: "POST",
      body: JSON.stringify({ name: name })
    });
    console.log("[VAULT/API] ✓ Grupo criado:", response);
    return response;
    
  } catch (err) {
    console.error("[VAULT/API] ✗ Erro:", err.message);
    throw err;
  }
}

async function apiDeletePasswordGroup(id) {
  console.log(`[VAULT/API] 🗑️ Deletando grupo #${id}...`);
  
  try {
    const response = await apiFetch(`/api/passwords/groups/${id}`, {
      method: "DELETE"
    });
    console.log("[VAULT/API] ✓ Grupo deletado:", response);
    return response;
    
  } catch (err) {
    console.error("[VAULT/API] ✗ Erro:", err.message);
    throw err;
  }
}

// ============================================================
// 👥 FUNÇÕES DE USUÁRIOS
// ============================================================

async function apiGetUsers() {
  console.log("[USERS/API] 👥 Carregando usuários...");
  
  try {
    const response = await apiFetch("/api/users", { method: "GET" });
    
    let users = [];
    if (Array.isArray(response)) {
      users = response;
    } else if (response && response.users && Array.isArray(response.users)) {
      users = response.users;
    } else if (response && response.data && Array.isArray(response.data)) {
      users = response.data;
    }
    
    console.log("[USERS/API] ✓ Usuários carregados:", users.length);
    return users;
    
  } catch (err) {
    console.error("[USERS/API] ✗ Erro ao carregar usuários:", err.message);
    throw err;
  }
}

async function apiGetUser(userId) {
  console.log(`[USERS/API] 👤 Carregando usuário #${userId}...`);
  
  try {
    const response = await apiFetch(`/api/users/${userId}`, { method: "GET" });
    console.log("[USERS/API] ✓ Usuário carregado:", response);
    return response;
    
  } catch (err) {
    console.error("[USERS/API] ✗ Erro ao carregar usuário:", err.message);
    throw err;
  }
}

async function apiCreateUser(data) {
  console.log("[USERS/API] ➕ Criando novo usuário...");
  console.log("[USERS/API] 📊 Dados:", {
    name: data.name,
    email: data.email,
    username: data.username || "N/A",
    role: data.role || "USER",
    group_id: data.group_id || "N/A"
  });
  
  try {
    const response = await apiFetch("/api/users", {
      method: "POST",
      body: JSON.stringify(data)
    });
    console.log("[USERS/API] ✓ Usuário criado:", response);
    return response;
    
  } catch (err) {
    console.error("[USERS/API] ✗ Erro ao criar usuário:", err.message);
    throw err;
  }
}

async function apiUpdateUser(userId, data) {
  console.log(`[USERS/API] ✏️ Atualizando usuário #${userId}...`);
  console.log("[USERS/API] 📊 Dados:", {
    name: data.name,
    email: data.email,
    username: data.username || "N/A",
    role: data.role || "N/A",
    group_id: data.group_id || "N/A"
  });
  
  try {
    const response = await apiFetch(`/api/users/${userId}`, {
      method: "PUT",
      body: JSON.stringify(data)
    });
    console.log("[USERS/API] ✓ Usuário atualizado:", response);
    return response;
    
  } catch (err) {
    console.error("[USERS/API] ✗ Erro ao atualizar usuário:", err.message);
    throw err;
  }
}

async function apiDeleteUser(userId) {
  console.log(`[USERS/API] 🗑️ Deletando usuário #${userId}...`);
  
  try {
    const response = await apiFetch(`/api/users/${userId}`, {
      method: "DELETE"
    });
    console.log("[USERS/API] ✓ Usuário deletado:", response);
    return response;
    
  } catch (err) {
    console.error("[USERS/API] ✗ Erro ao deletar usuário:", err.message);
    throw err;
  }
}

// ============================================================
// ✅ VERIFICAÇÃO FINAL
// ============================================================

console.log("\n" + "=".repeat(80));
console.log("[CONFIG] ✅ Todas as funções de API carregadas com sucesso!");
console.log("[CONFIG] 🌐 Servidor: " + API_BASE_URL);
console.log("[CONFIG] 🚀 Modo: SEM AUTENTICAÇÃO (Acesso Público)");
console.log("[CONFIG] 📊 Funções disponíveis:");
console.log({
  // Usuário
  apiFetch: typeof apiFetch,
  getCurrentUser: typeof getCurrentUser,
  isUserLoaded: typeof isUserLoaded,
  loadUser: typeof loadUser,
  logout: typeof logout,
  clearAllStorage: typeof clearAllStorage,
  saveUserData: typeof saveUserData,
  
  // Senhas
  apiGetPasswords: typeof apiGetPasswords,
  apiGetPassword: typeof apiGetPassword,
  apiCreatePassword: typeof apiCreatePassword,
  apiUpdatePassword: typeof apiUpdatePassword,
  apiDeletePassword: typeof apiDeletePassword,
  apiGetPublicPasswords: typeof apiGetPublicPasswords,
  
  // Grupos
  apiGetPasswordGroups: typeof apiGetPasswordGroups,
  apiCreatePasswordGroup: typeof apiCreatePasswordGroup,
  apiDeletePasswordGroup: typeof apiDeletePasswordGroup,
  
  // Usuários
  apiGetUsers: typeof apiGetUsers,
  apiGetUser: typeof apiGetUser,
  apiCreateUser: typeof apiCreateUser,
  apiUpdateUser: typeof apiUpdateUser,
  apiDeleteUser: typeof apiDeleteUser
});
console.log("=".repeat(80) + "\n");

// ============================================================
// 🧪 VERIFICAÇÃO DE INTEGRIDADE
// ============================================================

console.log("[INTEGRITY] 🔍 Verificando integridade do api.js...");

// ✅ Verificar funções críticas
const criticalFunctions = [
  'apiFetch', 'getCurrentUser', 'isUserLoaded', 'loadUser', 'logout'
];

let integrityOk = true;
criticalFunctions.forEach(fnName => {
  if (typeof window[fnName] === 'function') {
    console.log(`[INTEGRITY] ✓ ${fnName}: OK`);
  } else {
    console.error(`[INTEGRITY] ✗ ${fnName}: FALTANDO`);
    integrityOk = false;
  }
});

if (integrityOk) {
  console.log("[INTEGRITY] ✅ Todas as funções críticas estão presentes!");
} else {
  console.error("[INTEGRITY] ❌ Algumas funções críticas estão faltando!");
}

console.log("[INTEGRITY] ✅ api.js pronto para usar\n");