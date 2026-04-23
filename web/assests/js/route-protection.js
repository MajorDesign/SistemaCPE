/**
 * 🔐 ROUTE PROTECTION - Sistema Centralizado de Autenticação
 * 
 * Este arquivo gerencia:
 * - Proteção de rotas (páginas públicas vs protegidas)
 * - Verificação de autenticação
 * - Redirecionamentos automáticos
 * - Evento de autenticação para outras páginas
 * 
 * Uso: Adicionar no <head> como primeiro script
 * <script src="/SistemaCPE/web/assests/js/route-protection.js"></script>
 */

class RouteProtection {
  // ====================================
  // CONFIGURAÇÃO PADRÃO
  // ====================================
  static DEFAULT_CONFIG = {
    loginPageUrl: "/SistemaCPE/web/login.html",
    dashboardUrl: "/SistemaCPE/index.html",
    publicPages: [
      "/SistemaCPE/web/login.html",
      "/SistemaCPE/login.html",
    ],
    protectedPages: [
      "/SistemaCPE/index.html",
      "/SistemaCPE/web/index.html",
      "/SistemaCPE/web/dashboard.html",
      "/SistemaCPE/dashboard.html",
      "/SistemaCPE/web/pages/users.html",
      "/SistemaCPE/web/pages/groups.html",
      "/SistemaCPE/web/pages/tickets.html",
      "/SistemaCPE/web/pages/categories.html",
      "/SistemaCPE/web/pages/settings.html",
    ],
    enableLogging: true,
    redirectDelay: 500,
    eventDispatchDelay: 300,
  };

  // ====================================
  // CHAVES DE ARMAZENAMENTO
  // ====================================
  static STORAGE_KEYS = {
    USER_CURRENT: "cpe_user",
    TOKEN_CURRENT: "cpe_token",
    USER_LEGACY: "user",
    TOKEN_LEGACY: "token",
    USER_ID: "user_id",
    LOGGED_IN: "logged_in",
    LOGIN_TIME: "login_time",
    REDIRECT_AFTER_LOGIN: "redirectAfterLogin",
  };

  // ====================================
  // CONSTRUTOR
  // ====================================
  constructor(config = {}) {
    this.config = { ...RouteProtection.DEFAULT_CONFIG, ...config };
    this.user = null;
    this.isLoggedIn = false;
    this.eventDispatched = false;

    this._initializeWhenReady();
  }

  // ====================================
  // INICIALIZAÇÃO
  // ====================================

  /**
   * Aguarda DOM estar pronto e inicializa
   * @private
   */
  _initializeWhenReady() {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", () => {
        setTimeout(() => this.init(), 50);
      });
    } else {
      setTimeout(() => this.init(), 50);
    }
  }

  /**
   * Inicializa o sistema de proteção de rotas
   */
  init() {
    this.log("\n" + "=".repeat(80));
    this.log("[ROUTE-PROTECTION] 🔐 Inicializando sistema de proteção de rotas");
    this.log("=".repeat(80));

    try {
      this.checkAuthentication();
      this.validatePageAccess();
      this.log("[ROUTE-PROTECTION] ✅ Sistema inicializado com sucesso");
    } catch (error) {
      this.log("[ROUTE-PROTECTION] ❌ Erro durante inicialização: " + error.message);
      this.clearAllStorage();
    }

    this.log("=".repeat(80) + "\n");
  }

  // ====================================
  // AUTENTICAÇÃO
  // ====================================

  /**
   * Verifica autenticação do usuário
   * Tenta múltiplas fontes de armazenamento
   * @private
   */
  checkAuthentication() {
    this.log("[ROUTE-PROTECTION] 🔍 Verificando autenticação...");

    // Tentar armazenamento em ordem de preferência
    const userStr = this._getUserFromStorage();
    const token = this._getTokenFromStorage();

    this.isLoggedIn = userStr !== null && token !== null;

    if (this.isLoggedIn && userStr) {
      try {
        this.user = JSON.parse(userStr);

        if (!this._validateUserObject(this.user)) {
          throw new Error("Dados do usuário inválidos");
        }

        this.log("[ROUTE-PROTECTION] ✅ Autenticação confirmada");
        this._logUserInfo();
      } catch (error) {
        this.log("[ROUTE-PROTECTION] ❌ Erro ao recuperar dados: " + error.message);
        this.isLoggedIn = false;
        this.user = null;
        this.clearAllStorage();
      }
    } else {
      this.log("[ROUTE-PROTECTION] ⚠️ Nenhum usuário autenticado");
    }
  }

  /**
   * Obtém dados do usuário do armazenamento
   * @private
   * @returns {string|null}
   */
  _getUserFromStorage() {
    // Tentar localStorage novo
    let userData = localStorage.getItem(RouteProtection.STORAGE_KEYS.USER_CURRENT);
    if (userData) return userData;

    // Tentar sessionStorage novo
    userData = sessionStorage.getItem(RouteProtection.STORAGE_KEYS.USER_CURRENT);
    if (userData) return userData;

    // Tentar localStorage legado
    userData = localStorage.getItem(RouteProtection.STORAGE_KEYS.USER_LEGACY);
    if (userData) return userData;

    // Tentar sessionStorage legado
    userData = sessionStorage.getItem(RouteProtection.STORAGE_KEYS.USER_LEGACY);
    return userData || null;
  }

  /**
   * Obtém token do armazenamento
   * @private
   * @returns {string|null}
   */
  _getTokenFromStorage() {
    // Tentar localStorage novo
    let token = localStorage.getItem(RouteProtection.STORAGE_KEYS.TOKEN_CURRENT);
    if (token) return token;

    // Tentar sessionStorage novo
    token = sessionStorage.getItem(RouteProtection.STORAGE_KEYS.TOKEN_CURRENT);
    if (token) return token;

    // Tentar localStorage legado
    token = localStorage.getItem(RouteProtection.STORAGE_KEYS.TOKEN_LEGACY);
    if (token) return token;

    // Tentar sessionStorage legado
    token = sessionStorage.getItem(RouteProtection.STORAGE_KEYS.TOKEN_LEGACY);
    return token || null;
  }

  /**
   * Valida se o objeto do usuário tem propriedades obrigatórias
   * @private
   * @param {Object} user
   * @returns {boolean}
   */
  _validateUserObject(user) {
    if (!user || typeof user !== "object") return false;
    return user.id && user.name && user.email && user.role;
  }

  /**
   * Loga informações do usuário
   * @private
   */
  _logUserInfo() {
    this.log("[ROUTE-PROTECTION]   ID: " + this.user.id);
    this.log("[ROUTE-PROTECTION]   Nome: " + this.user.name);
    this.log("[ROUTE-PROTECTION]   Email: " + this.user.email);
    this.log("[ROUTE-PROTECTION]   Role: " + this.user.role);
  }

  // ====================================
  // LIMPEZA DE ARMAZENAMENTO
  // ====================================

  /**
   * Remove todos os dados de autenticação do armazenamento
   */
  clearAllStorage() {
    this.log("[ROUTE-PROTECTION] 🧹 Limpando dados de sessão...");

    // Remover dados novos
    localStorage.removeItem(RouteProtection.STORAGE_KEYS.USER_CURRENT);
    localStorage.removeItem(RouteProtection.STORAGE_KEYS.TOKEN_CURRENT);
    sessionStorage.removeItem(RouteProtection.STORAGE_KEYS.USER_CURRENT);
    sessionStorage.removeItem(RouteProtection.STORAGE_KEYS.TOKEN_CURRENT);

    // Remover dados legados
    localStorage.removeItem(RouteProtection.STORAGE_KEYS.USER_LEGACY);
    localStorage.removeItem(RouteProtection.STORAGE_KEYS.TOKEN_LEGACY);
    localStorage.removeItem(RouteProtection.STORAGE_KEYS.USER_ID);
    localStorage.removeItem(RouteProtection.STORAGE_KEYS.LOGGED_IN);
    localStorage.removeItem(RouteProtection.STORAGE_KEYS.LOGIN_TIME);

    // Limpar sessionStorage também
    sessionStorage.removeItem(RouteProtection.STORAGE_KEYS.USER_LEGACY);
    sessionStorage.removeItem(RouteProtection.STORAGE_KEYS.TOKEN_LEGACY);

    this.log("[ROUTE-PROTECTION] ✅ Dados removidos com sucesso");
  }

  // ====================================
  // VALIDAÇÃO DE ACESSO
  // ====================================

  /**
   * Valida se o usuário tem acesso à página atual.
   * REGRA: toda página que NÃO está em publicPages é protegida por padrão.
   * Sem token/usuário -> redireciona para login.
   * @private
   */
  validatePageAccess() {
    const currentPage = window.location.pathname;
    const isPublicPage = this._isPublicPage(currentPage);

    this.log("[ROUTE-PROTECTION] 📄 Página atual: " + currentPage);
    this.log("[ROUTE-PROTECTION] 🏷️ Tipo: " + (isPublicPage ? "PÚBLICA" : "PROTEGIDA"));

    // Página pública (ex: login)
    if (isPublicPage) {
      if (this.isLoggedIn && this.user) {
        this.log("[ROUTE-PROTECTION] 📋 Já autenticado. Redirecionando para dashboard...");
        this.redirectToDashboard();
        return;
      }
      this.log("[ROUTE-PROTECTION] ✅ Página pública acessível");
      this.markPageAsLoaded();
      return;
    }

    // Página protegida (todo o resto)
    if (!this.isLoggedIn || !this.user) {
      this.log("[ROUTE-PROTECTION] ❌ Sem autenticação. Redirecionando para login...");
      this.redirectToLogin(currentPage);
      return;
    }

    this.log("[ROUTE-PROTECTION] ✅ Acesso permitido");
    this.markPageAsLoaded();
  }

  /**
   * Verifica se a página é protegida
   * @private
   * @param {string} page
   * @returns {boolean}
   */
  _isProtectedPage(page) {
    return this.config.protectedPages.some((protectedPage) =>
      page.includes(protectedPage)
    );
  }

  /**
   * Verifica se a página é pública
   * @private
   * @param {string} page
   * @returns {boolean}
   */
  _isPublicPage(page) {
    return this.config.publicPages.some((publicPage) =>
      page.includes(publicPage)
    );
  }

  // ====================================
  // REDIRECIONAMENTOS
  // ====================================

  /**
   * Redireciona para página de login
   * @param {string} [from] - Página de origem
   */
  redirectToLogin(from) {
    if (from && !from.includes(this.config.loginPageUrl)) {
      sessionStorage.setItem(RouteProtection.STORAGE_KEYS.REDIRECT_AFTER_LOGIN, from);
      this.log("[ROUTE-PROTECTION] 🔗 URL de origem salva: " + from);
    }

    this.log(
      "[ROUTE-PROTECTION] 🔄 Redirecionando em " + this.config.redirectDelay + "ms..."
    );

    setTimeout(() => {
      window.location.href = this.config.loginPageUrl;
    }, this.config.redirectDelay);
  }

  /**
   * Redireciona para dashboard
   */
  redirectToDashboard() {
    this.log(
      "[ROUTE-PROTECTION] 🔄 Redirecionando em " + this.config.redirectDelay + "ms..."
    );

    setTimeout(() => {
      window.location.href = this.config.dashboardUrl;
    }, this.config.redirectDelay);
  }

  // ====================================
  // RENDERIZAÇÃO E EVENTOS
  // ====================================

  /**
   * Marca a página como carregada e dispara eventos
   */
  markPageAsLoaded() {
    this._hideLoadingOverlay();
    this._showPageContent();
    this._dispatchAuthenticationEvent();
  }

  /**
   * Remove overlay de carregamento
   * @private
   */
  _hideLoadingOverlay() {
    const loadingPage = document.getElementById("loadingPage");
    if (loadingPage) {
      loadingPage.style.display = "none";
      this.log("[ROUTE-PROTECTION] ⏳ Loading overlay removido");
    }
  }

  /**
   * Exibe conteúdo da página
   * @private
   */
  _showPageContent() {
    const containerMain = document.querySelector(".container-main");
    if (containerMain) {
      containerMain.style.display = "flex";
      this.log("[ROUTE-PROTECTION] 👁️ Conteúdo da página exibido");
    }
  }

  /**
   * Dispara evento de autenticação bem-sucedida
   * @private
   */
  _dispatchAuthenticationEvent() {
    if (this.eventDispatched || !this.user) return;

    setTimeout(() => {
      try {
        this.log("[ROUTE-PROTECTION] 📢 Disparando evento authenticationSuccess...");

        const event = new CustomEvent("authenticationSuccess", {
          detail: { user: this.user, userInfo: this.getUserInfo() }
        });

        document.dispatchEvent(event);
        this.eventDispatched = true;

        this.log("[ROUTE-PROTECTION] ✅ Evento disparado com sucesso");
      } catch (error) {
        this.log("[ROUTE-PROTECTION] ❌ Erro ao disparar evento: " + error.message);
      }
    }, this.config.eventDispatchDelay);
  }

  // ====================================
  // MÉTODOS PÚBLICOS - INFORMAÇÕES
  // ====================================

  /**
   * Obtém dados brutos do usuário autenticado
   * @returns {Object|null} Dados do usuário ou null
   */
  getUser() {
    return this.user;
  }

  /**
   * Verifica se usuário está autenticado
   * @returns {boolean} true se autenticado
   */
  isAuthenticated() {
    return this.isLoggedIn && this.user !== null;
  }

  /**
   * Obtém informações formatadas do usuário
   * @returns {Object|null} Informações do usuário ou null
   */
  getUserInfo() {
    if (!this.isAuthenticated()) return null;

    return {
      id: this.user.id,
      name: this.user.name || "Usuário",
      email: this.user.email || "sem-email@example.com",
      username: this.user.username || this.user.name || "user",
      role: (this.user.role || "USER").toUpperCase(),
      groupId: this.user.group_id || null,
      isActive: this.user.is_active !== false,
      createdAt: this.user.created_at || null,
    };
  }

  // ====================================
  // MÉTODOS PÚBLICOS - PERMISSÕES
  // ====================================

  /**
   * Verifica se usuário tem uma role específica
   * @param {string} role - Role a verificar (ex: 'ADMIN', 'USER')
   * @returns {boolean} true se usuário tem a role
   */
  hasRole(role) {
    if (!this.isAuthenticated()) return false;
    return (this.user.role || "").toUpperCase() === role.toUpperCase();
  }

  /**
   * Verifica se usuário tem uma das roles especificadas
   * @param {Array<string>} roles - Array de roles a verificar
   * @returns {boolean} true se usuário tem uma das roles
   */
  hasAnyRole(roles) {
    if (!this.isAuthenticated()) return false;

    const userRole = (this.user.role || "").toUpperCase();
    return roles.some((role) => userRole === role.toUpperCase());
  }

  /**
   * Verifica se usuário é administrador
   * @returns {boolean}
   */
  isAdmin() {
    return this.hasRole("ADMIN");
  }

  /**
   * Verifica se usuário é suporte
   * @returns {boolean}
   */
  isSupport() {
    return this.hasRole("SUPPORT");
  }

  /**
   * Verifica se usuário é usuário comum
   * @returns {boolean}
   */
  isUser() {
    return this.hasRole("USER");
  }

  // ====================================
  // MÉTODOS PÚBLICOS - AÇÕES
  // ====================================

  /**
   * Faz logout e limpa dados de sessão
   */
  logout() {
    this.log("\n[ROUTE-PROTECTION] 🚪 Logout iniciado...");

    this.clearAllStorage();

    this.user = null;
    this.isLoggedIn = false;
    this.eventDispatched = false;

    this.log("[ROUTE-PROTECTION] 🔄 Redirecionando para login...");
    this.log("=".repeat(80) + "\n");

    setTimeout(() => {
      window.location.href = this.config.loginPageUrl;
    }, this.config.redirectDelay);
  }

  /**
   * Obtém URL de redirecionamento após login
   * @returns {string|null}
   */
  getRedirectAfterLogin() {
    const redirectUrl = sessionStorage.getItem(
      RouteProtection.STORAGE_KEYS.REDIRECT_AFTER_LOGIN
    );
    return redirectUrl || null;
  }

  /**
   * Limpa URL de redirecionamento após login
   */
  clearRedirectAfterLogin() {
    sessionStorage.removeItem(RouteProtection.STORAGE_KEYS.REDIRECT_AFTER_LOGIN);
  }

  // ====================================
  // UTILITÁRIOS
  // ====================================

  /**
   * Registra mensagem no console (se ativado)
   * @param {string} message - Mensagem a registrar
   */
  log(message) {
    if (this.config.enableLogging) {
      console.log(message);
    }
  }

  /**
   * Obtém configuração atual
   * @returns {Object}
   */
  getConfig() {
    return { ...this.config };
  }

  /**
   * Atualiza configuração
   * @param {Object} newConfig
   */
  updateConfig(newConfig) {
    this.config = { ...this.config, ...newConfig };
    this.log("[ROUTE-PROTECTION] ⚙️ Configuração atualizada");
  }
}

// ================================================== 
// FUNÇÃO AUXILIAR: checkPageAccess()
// Data: 02/04/2026 19:45
// ==================================================

/**
 * FUNCAO: checkPageAccess()
 * 
 * Valida se o usuário autenticado tem permissão para acessar a página
 * 
 * @param {string} pageName - Nome da página (ex: "USERS", "GROUPS")
 * @param {array} allowedRoles - Roles permitidos (ex: ["ADMIN", "TI", "MANAGER"])
 * @returns {object|null} - Dados do usuário se permitido, null caso contrário
 */
function checkPageAccess(pageName, allowedRoles) {
  console.log(`[PAGE-ACCESS/${pageName}] 🔐 Validando acesso para página: ${pageName}`);
  console.log(`[PAGE-ACCESS/${pageName}] ✅ Roles permitidos: ${allowedRoles.join(", ")}`);
  
  // ================================================== 
  // STEP 1: Verificar se authProtection foi carregado
  // Data: 02/04/2026 19:45
  // ==================================================
  
  if (typeof authProtection === 'undefined') {
    console.error(`[PAGE-ACCESS/${pageName}] ❌ ERRO: authProtection não foi carregado!`);
    alert("❌ Erro ao carregar sistema de proteção. Por favor, recarregue a página.");
    window.location.href = "/SistemaCPE/web/login.html";
    return null;
  }
  
  // ================================================== 
  // STEP 2: Verificar se usuário está autenticado
  // Data: 02/04/2026 19:45
  // ==================================================
  
  if (!authProtection.isAuthenticated()) {
    console.error(`[PAGE-ACCESS/${pageName}] ❌ ACESSO NEGADO: Nenhum usuário logado`);
    
    alert("❌ Você deve fazer login para acessar esta página!");
    
    setTimeout(() => {
      window.location.href = "/SistemaCPE/web/login.html";
    }, 1500);
    
    return null;
  }
  
  // ================================================== 
  // STEP 3: Obter dados do usuário
  // Data: 02/04/2026 19:45
  // ==================================================
  
  const userData = authProtection.getUser();
  const userRole = userData.role || "USER";
  
  console.log(`[PAGE-ACCESS/${pageName}] 👤 Usuário autenticado:`);
  console.log(`   └─ ID: ${userData.id}`);
  console.log(`   └─ Nome: ${userData.name}`);
  console.log(`   └─ Email: ${userData.email}`);
  console.log(`   └─ Role: ${userRole}`);
  
  // ==================================================
  // STEP 4A: Verificar exceções individuais do usuário
  // ==================================================

  const exceptions = JSON.parse(localStorage.getItem('ACCESS_EXCEPTIONS') || '{}');
  const userKey = `userId_${userData.id}`;
  const userExceptions = exceptions[userKey];

  if (userExceptions) {
    // Página explicitamente BLOQUEADA para este usuário
    if (userExceptions.blockPages && userExceptions.blockPages.includes(pageName)) {
      console.error(`[PAGE-ACCESS/${pageName}] ❌ ACESSO BLOQUEADO por exceção individual!`);
      console.error(`   └─ Usuário ID: ${userData.id} está na lista de bloqueio para ${pageName}`);

      alert(
        `❌ ACESSO BLOQUEADO!\n\n` +
        `Seu acesso a esta página foi bloqueado pelo administrador.\n\n` +
        `Você será redirecionado em 3 segundos...`
      );

      setTimeout(() => {
        window.location.href = "/SistemaCPE/index.html";
      }, 3000);

      return null;
    }

    // Página explicitamente PERMITIDA para este usuário (override de role)
    if (userExceptions.allowPages && userExceptions.allowPages.includes(pageName)) {
      console.log(`[PAGE-ACCESS/${pageName}] ✅ ACESSO PERMITIDO por exceção individual!`);
      console.log(`   └─ Usuário ID: ${userData.id} está na lista de permissão para ${pageName}`);
      return userData;
    }
  }

  // ==================================================
  // STEP 4B: Carregar permissões salvas pelo admin (PAGE_PERMISSIONS)
  // ==================================================

  const savedPermissions = JSON.parse(localStorage.getItem('PAGE_PERMISSIONS') || '{}');
  if (savedPermissions[pageName]) {
    allowedRoles = savedPermissions[pageName];
    console.log(`[PAGE-ACCESS/${pageName}] 📋 Permissões carregadas do admin: ${allowedRoles.join(", ")}`);
  }

  // ==================================================
  // STEP 4: Validar permissão de role
  // Data: 02/04/2026 19:45
  // ==================================================

  if (!allowedRoles.includes(userRole)) {
    console.error(`[PAGE-ACCESS/${pageName}] ❌ ACESSO NEGADO!`);
    console.error(`   └─ Role atual: '${userRole}'`);
    console.error(`   └─ Roles permitidos: ${allowedRoles.join(", ")}`);

    const roleLabel = getRoleLabel(userRole);
    const permittedLabel = allowedRoles.map(r => getRoleLabel(r)).join(", ");

    alert(
      `❌ ACESSO NEGADO!\n\n` +
      `Sua função (${roleLabel}) não tem permissão para acessar esta página.\n\n` +
      `Apenas ${permittedLabel} podem acessar.\n\n` +
      `Você será redirecionado em 3 segundos...`
    );

    setTimeout(() => {
      window.location.href = "/SistemaCPE/index.html";
    }, 3000);

    return null;
  }

  // ==================================================
  // STEP 5: Acesso PERMITIDO!
  // Data: 02/04/2026 19:45
  // ==================================================
  
  console.log(`[PAGE-ACCESS/${pageName}] ✅ ACESSO PERMITIDO!`);
  console.log(`   └─ Usuário: ${userData.name} (${userRole})`);
  console.log(`   └─ Página: ${pageName}`);
  
  return userData;
}

// ================================================== 
// FUNÇÃO AUXILIAR: getRoleLabel()
// Data: 02/04/2026 19:45
// ==================================================

/**
 * Retorna label legível do role
 * 
 * @param {string} role - Role do usuário
 * @returns {string} - Label formatado
 */
function getRoleLabel(role) {
  const roleLabels = {
    'USER': '👤 Usuário Comum',
    'RESPONSAVEL_GRUPO': '👨‍💼 Responsável do Grupo',
    'ADMIN': '🔐 Administrador Sistema',
    'TI': '🔧 TI',
    'MANAGER': '📊 Gerente'
  };
  
  return roleLabels[role] || role;
}

// ================================================== 
// [FIM] FUNÇÕES AUXILIARES
// Data: 02/04/2026 19:45
// ==================================================

// ================================================== 
// INSTÂNCIA GLOBAL
// Data: 02/04/2026 19:50
// ==================================================

const authProtection = new RouteProtection();  // ✅ CRIAR PRIMEIRO

window.RouteProtection = RouteProtection;
window.authProtection = authProtection;
// ====================================
// LOG FINAL
// Data: 02/04/2026 19:45
// ====================================

console.log("\n[ROUTE-PROTECTION] 🎉 Sistema carregado com sucesso!");
console.log("[ROUTE-PROTECTION] 📚 Métodos disponíveis:");
console.log("[ROUTE-PROTECTION]   ✓ authProtection.getUser()");
console.log("[ROUTE-PROTECTION]   ✓ authProtection.isAuthenticated()");
console.log("[ROUTE-PROTECTION]   ✓ authProtection.getUserInfo()");
console.log("[ROUTE-PROTECTION]   ✓ authProtection.hasRole(role)");
console.log("[ROUTE-PROTECTION]   ✓ authProtection.hasAnyRole(roles)");
console.log("[ROUTE-PROTECTION]   ✓ authProtection.isAdmin()");
console.log("[ROUTE-PROTECTION]   ✓ authProtection.isSupport()");
console.log("[ROUTE-PROTECTION]   ✓ authProtection.isUser()");
console.log("[ROUTE-PROTECTION]   ✓ authProtection.logout()");
console.log("[ROUTE-PROTECTION]   ✓ authProtection.getRedirectAfterLogin()");
console.log("[ROUTE-PROTECTION]   ✓ authProtection.getConfig()");
console.log("[ROUTE-PROTECTION]   ✓ authProtection.updateConfig(obj)");
console.log("[ROUTE-PROTECTION]   ✓ checkPageAccess(pageName, allowedRoles)");
console.log("[ROUTE-PROTECTION]   ✓ getRoleLabel(role)");
console.log("[ROUTE-PROTECTION]\n" + "=".repeat(80) + "\n");