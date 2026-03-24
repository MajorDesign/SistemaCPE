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
   * Valida se o usuário tem acesso à página atual
   * @private
   */
  validatePageAccess() {
    const currentPage = window.location.pathname;

    this.log("[ROUTE-PROTECTION] 📄 Página atual: " + currentPage);

    const isProtectedPage = this._isProtectedPage(currentPage);
    const isPublicPage = this._isPublicPage(currentPage);

    this.log(
      "[ROUTE-PROTECTION] 🏷️ Tipo: " +
        (isProtectedPage ? "PROTEGIDA" : isPublicPage ? "PÚBLICA" : "DESCONHECIDA")
    );

    // Página protegida SEM autenticação
    if (isProtectedPage && !this.isLoggedIn) {
      this.log("[ROUTE-PROTECTION] ❌ Acesso negado! Redirecionando para login...");
      this.redirectToLogin(currentPage);
      return;
    }

    // Página de login COM autenticação
    if (isPublicPage && this.isLoggedIn && this.user) {
      this.log("[ROUTE-PROTECTION] 📋 Já autenticado. Redirecionando para dashboard...");
      this.redirectToDashboard();
      return;
    }

    // Página protegida COM autenticação
    if (isProtectedPage && this.isLoggedIn && this.user) {
      this.log("[ROUTE-PROTECTION] ✅ Acesso permitido");
      this.markPageAsLoaded();
      return;
    }

    // Página pública SEM autenticação
    if (isPublicPage && !this.isLoggedIn) {
      this.log("[ROUTE-PROTECTION] ✅ Página pública acessível");
      this.markPageAsLoaded();
      return;
    }

    // Página desconhecida
    this.log("[ROUTE-PROTECTION] ⚠️ Página desconhecida - permitindo acesso");
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

// ====================================
// INSTÂNCIA GLOBAL
// ====================================

const authProtection = new RouteProtection();

// Disponibilizar globalmente
window.RouteProtection = RouteProtection;
window.authProtection = authProtection;

// ====================================
// LOG FINAL
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
console.log("[ROUTE-PROTECTION]\n" + "=".repeat(80) + "\n");