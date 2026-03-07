// =========================================
// Configuração da API
// =========================================

const API_BASE_URL = "http://localhost:8000";  // ✅ SEM /api no final!

console.log("[CONFIG] API_BASE_URL:", API_BASE_URL);


// =========================================
// Função Helper - Requisições API
// =========================================

async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;  // ✅ Agora fica: http://localhost:8000/api/auth/me
  const method = options.method || "GET";

  console.log(`[API] ${method} ${endpoint}`);

  const defaultOptions = {
    method: method,
    credentials: "include", // ✅ Envia cookies (sessão)
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, defaultOptions);

    console.log(`[API] ✓ Response: ${response.status} ${response.statusText}`);

    // ✅ CORRIGIDO: Trata 401 sem jogar erro
    if (response.status === 401) {
      console.warn("[API] ✗ Não autenticado (401)");
      return null;
    }

    if (!response.ok) {
      let errorData = {};
      try {
        errorData = await response.json();
      } catch (e) {
        console.warn("[API] Não conseguiu fazer parse do JSON de erro");
      }

      const errorMessage = errorData.detail || errorData.message || `Erro ${response.status}: ${response.statusText}`;
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


// =========================================
// Funções de Autenticação
// =========================================

async function login(email, password) {
  console.log("\n[AUTH/LOGIN] Iniciando login...");
  
  try {
    const response = await apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    console.log("[AUTH/LOGIN] ✓ Login bem-sucedido");
    return response;

  } catch (err) {
    console.error("[AUTH/LOGIN] ✗ Erro:", err.message);
    throw err;
  }
}


async function logout() {
  console.log("[AUTH/LOGOUT] Iniciando logout...");
  
  try {
    await apiFetch("/api/auth/logout", { method: "POST" });
    console.log("[AUTH/LOGOUT] ✓ Logout bem-sucedido");
  } catch (err) {
    console.error("[AUTH/LOGOUT] ✗ Erro:", err.message);
  }
}


/**
 * ✅ CORRIGIDO: Trata erro 401 sem jogar exceção
 */
async function getMe() {
  console.log("[AUTH/ME] Obtendo dados do usuário...");
  
  try {
    const response = await apiFetch("/api/auth/me", { method: "GET" });
    
    // ✅ NOVO: Se response for null (401), retorna null
    if (!response) {
      console.warn("[AUTH/ME] ✗ Usuário não autenticado");
      return null;
    }
    
    console.log("[AUTH/ME] ✓ Dados obtidos:", response);
    return response;

  } catch (err) {
    console.error("[AUTH/ME] ✗ Erro:", err.message);
    return null; // ✅ Retorna null em caso de erro
  }
}


// =========================================
// Funções Utilitárias
// =========================================

/**
 * ✅ CORRIGIDO: Protege página com tratamento adequado
 */
async function protectPage() {
  console.log("\n[PROTECT] Verificando autenticação...");
  
  try {
    const user = await getMe();
    
    if (!user) {
      console.warn("[PROTECT] ✗ Usuário não autenticado");
      window.location.href = "/SistemaCPE/web/login.html";
      return null;
    }
    
    console.log("[PROTECT] ✓ Usuário autenticado:", user.name);
    return user;

  } catch (err) {
    console.error("[PROTECT] ✗ Erro na verificação:", err.message);
    window.location.href = "/SistemaCPE/web/login.html";
    return null;
  }
}

// ===== FIM: api.js =====