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
  constructor(config = {}) {
    this.config = {
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
      ],
      enableLogging: true,
      redirectDelay: 500,
      eventDispatchDelay: 300,
      ...config
    };

    this.user = null;
    this.isLoggedIn = false;
    this.eventDispatched = false;

    // [INICIO] Aguardar DOM estar pronto
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", () => {
        setTimeout(() => this.init(), 50);
      });
    } else {
      setTimeout(() => this.init(), 50);
    }
    // [FIM] Aguardar DOM estar pronto
  }

  // ====================================
  // INICIALIZAÇÃO
  // ====================================
  // [INICIO] init()
  init() {
    this.log("\n" + "=".repeat(80));
    this.log("[ROUTE-PROTECTION] Inicializando sistema de protecao de rotas");
    this.log("=".repeat(80));

    this.checkAuthentication();
    this.validatePageAccess();

    this.log("=".repeat(80) + "\n");
  }
  // [FIM] init()

  // ====================================
  // VERIFICAR AUTENTICAÇÃO
  // ====================================
  // [INICIO] checkAuthentication()
  checkAuthentication() {
    this.log("[ROUTE-PROTECTION] Verificando autenticacao...");

    // Tentar localStorage primeiro
    let userStr = localStorage.getItem("cpe_user");
    let token = localStorage.getItem("cpe_token");

    // Fallback para sessionStorage
    if (!userStr) userStr = sessionStorage.getItem("cpe_user");
    if (!token) token = sessionStorage.getItem("cpe_token");

    // Fallback para formato antigo (compatibilidade)
    if (!userStr) userStr = localStorage.getItem("user");
    if (!token) token = localStorage.getItem("token");

    this.isLoggedIn = userStr !== null && userStr !== undefined && token !== null && token !== undefined;

    if (this.isLoggedIn && userStr) {
      try {
        this.user = JSON.parse(userStr);
        this.log("[ROUTE-PROTECTION] Autenticacao confirmada");
        this.log("[ROUTE-PROTECTION]   Nome: " + this.user.name);
        this.log("[ROUTE-PROTECTION]   Email: " + this.user.email);
        this.log("[ROUTE-PROTECTION]   Role: " + this.user.role);
        this.log("[ROUTE-PROTECTION]   ID: " + this.user.id);
      } catch (err) {
        this.log("[ROUTE-PROTECTION] Erro ao recuperar dados: " + err.message);
        this.isLoggedIn = false;
        this.user = null;
        this.clearAllStorage();
      }
    } else {
      this.log("[ROUTE-PROTECTION] Nenhum usuario autenticado");
    }
  }
  // [FIM] checkAuthentication()

  // ====================================
  // LIMPAR TODOS OS STORAGES
  // ====================================
  // [INICIO] clearAllStorage()
  clearAllStorage() {
    this.log("[ROUTE-PROTECTION] Limpando dados de sessao...");

    // Remover dados novos
    localStorage.removeItem("cpe_user");
    localStorage.removeItem("cpe_token");
    sessionStorage.removeItem("cpe_user");
    sessionStorage.removeItem("cpe_token");

    // Remover dados antigos
    localStorage.removeItem("user_id");
    localStorage.removeItem("user");
    localStorage.removeItem("logged_in");
    localStorage.removeItem("login_time");
    localStorage.removeItem("token");

    this.log("[ROUTE-PROTECTION] Dados removidos com sucesso");
  }
  // [FIM] clearAllStorage()

  // ====================================
  // VALIDAR ACESSO À PÁGINA
  // ====================================
  // [INICIO] validatePageAccess()
  validatePageAccess() {
    const currentPage = window.location.pathname;

    this.log("[ROUTE-PROTECTION] Pagina atual: " + currentPage);

    // [INICIO] Verificar se é página protegida
    const isProtectedPage = this.config.protectedPages.some((page) =>
      currentPage.includes(page)
    );
    // [FIM] Verificar se é página protegida

    // [INICIO] Verificar se é página pública
    const isPublicPage = this.config.publicPages.some((page) =>
      currentPage.includes(page)
    );
    // [FIM] Verificar se é página pública

    this.log("[ROUTE-PROTECTION] Tipo: " + (isProtectedPage ? "PROTEGIDA" : isPublicPage ? "PUBLICA" : "DESCONHECIDA"));

    // [INICIO] CASO 1: Página protegida SEM autenticação
    if (isProtectedPage && !this.isLoggedIn) {
      this.log("[ROUTE-PROTECTION] Acesso negado! Redirecionando para login...");
      this.redirectToLogin(currentPage);
      return;
    }
    // [FIM] CASO 1

    // [INICIO] CASO 2: Página de login COM autenticação
    if (isPublicPage && this.isLoggedIn && this.user) {
      this.log("[ROUTE-PROTECTION] Ja autenticado. Redirecionando para dashboard...");
      this.redirectToDashboard();
      return;
    }
    // [FIM] CASO 2

    // [INICIO] CASO 3: Página protegida COM autenticação
    if (isProtectedPage && this.isLoggedIn && this.user) {
      this.log("[ROUTE-PROTECTION] Acesso permitido");
      this.markPageAsLoaded();
      return;
    }
    // [FIM] CASO 3

    // [INICIO] CASO 4: Página pública SEM autenticação
    if (isPublicPage && !this.isLoggedIn) {
      this.log("[ROUTE-PROTECTION] Pagina publica acessivel");
      this.markPageAsLoaded();
      return;
    }
    // [FIM] CASO 4

    // [INICIO] CASO 5: Página desconhecida
    this.log("[ROUTE-PROTECTION] Pagina desconhecida - permitindo acesso");
    this.markPageAsLoaded();
    // [FIM] CASO 5
  }
  // [FIM] validatePageAccess()

  // ====================================
  // REDIRECIONAR PARA LOGIN
  // ====================================
  // [INICIO] redirectToLogin()
  redirectToLogin(from) {
    if (from && from !== this.config.loginPageUrl) {
      sessionStorage.setItem("redirectAfterLogin", from);
      this.log("[ROUTE-PROTECTION] URL de origem salva: " + from);
    }

    this.log("[ROUTE-PROTECTION] Redirecionando em " + this.config.redirectDelay + "ms...");

    setTimeout(() => {
      window.location.href = this.config.loginPageUrl;
    }, this.config.redirectDelay);
  }
  // [FIM] redirectToLogin()

  // ====================================
  // REDIRECIONAR PARA DASHBOARD
  // ====================================
  // [INICIO] redirectToDashboard()
  redirectToDashboard() {
    this.log("[ROUTE-PROTECTION] Redirecionando em " + this.config.redirectDelay + "ms...");

    setTimeout(() => {
      window.location.href = this.config.dashboardUrl;
    }, this.config.redirectDelay);
  }
  // [FIM] redirectToDashboard()

  // ====================================
  // MARCAR PÁGINA COMO CARREGADA
  // ====================================
  // [INICIO] markPageAsLoaded()
  markPageAsLoaded() {
    // [INICIO] Remover overlay de loading
    const loadingPage = document.getElementById("loadingPage");
    if (loadingPage) {
      loadingPage.style.display = "none";
      this.log("[ROUTE-PROTECTION] Loading overlay removido");
    }
    // [FIM] Remover overlay de loading

    // [INICIO] Mostrar conteúdo
    const containerMain = document.querySelector(".container-main");
    if (containerMain) {
      containerMain.style.display = "flex";
      this.log("[ROUTE-PROTECTION] Conteudo da pagina exibido");
    }
    // [FIM] Mostrar conteúdo

    // [INICIO] Disparar evento com delay
    if (!this.eventDispatched && this.user) {
      setTimeout(() => {
        this.log("[ROUTE-PROTECTION] Disparando evento authenticationSuccess...");
        const event = new CustomEvent("authenticationSuccess", {
          detail: { user: this.user }
        });
        document.dispatchEvent(event);
        this.eventDispatched = true;
        this.log("[ROUTE-PROTECTION] Evento disparado com sucesso");
      }, this.config.eventDispatchDelay);
    }
    // [FIM] Disparar evento com delay
  }
  // [FIM] markPageAsLoaded()

  // ====================================
  // FUNÇÕES PÚBLICAS
  // ====================================

  // [INICIO] getUser()
  /**
   * Obter dados do usuario autenticado
   * @returns {Object|null} Dados do usuario ou null
   */
  getUser() {
    return this.user;
  }
  // [FIM] getUser()

  // [INICIO] isAuthenticated()
  /**
   * Verificar se usuario esta autenticado
   * @returns {Boolean} true se autenticado
   */
  isAuthenticated() {
    return this.isLoggedIn && this.user !== null;
  }
  // [FIM] isAuthenticated()

  // [INICIO] logout()
  /**
   * Fazer logout e limpar dados de sessao
   */
  logout() {
    this.log("\n[ROUTE-PROTECTION] Logout iniciado...");

    this.clearAllStorage();

    this.log("[ROUTE-PROTECTION] Redirecionando para login...");
    this.log("=".repeat(80) + "\n");

    this.user = null;
    this.isLoggedIn = false;

    setTimeout(() => {
      window.location.href = this.config.loginPageUrl;
    }, this.config.redirectDelay);
  }
  // [FIM] logout()

  // [INICIO] getUserInfo()
  /**
   * Obter informacoes do usuario formatadas
   * @returns {Object|null} Informacoes do usuario ou null
   */
  getUserInfo() {
    if (!this.isAuthenticated()) return null;

    return {
      id: this.user.id,
      name: this.user.name,
      email: this.user.email,
      username: this.user.username,
      role: this.user.role,
      groupId: this.user.group_id,
      isActive: this.user.is_active,
      createdAt: this.user.created_at
    };
  }
  // [FIM] getUserInfo()

  // [INICIO] hasRole()
  /**
   * Verificar se usuario tem uma role especifica
   * @param {String} role - Role a verificar (ex: 'ADMIN', 'USER')
   * @returns {Boolean} true se usuario tem a role
   */
  hasRole(role) {
    if (!this.isAuthenticated()) return false;
    return this.user.role === role;
  }
  // [FIM] hasRole()

  // [INICIO] hasAnyRole()
  /**
   * Verificar se usuario tem uma das roles especificadas
   * @param {Array} roles - Array de roles a verificar
   * @returns {Boolean} true se usuario tem uma das roles
   */
  hasAnyRole(roles) {
    if (!this.isAuthenticated()) return false;
    return roles.includes(this.user.role);
  }
  // [FIM] hasAnyRole()

  // [INICIO] log()
  /**
   * Registrar mensagem no console (se ativado)
   * @param {String} message - Mensagem a registrar
   */
  log(message) {
    if (this.config.enableLogging) {
      console.log(message);
    }
  }
  // [FIM] log()
}

// ====================================
// INSTÂNCIA GLOBAL
// ====================================
// [INICIO] Instância Global
const authProtection = new RouteProtection();

// Disponibilizar globalmente
window.RouteProtection = RouteProtection;
window.authProtection = authProtection;
// [FIM] Instância Global

// ====================================
// DEBUG E VALIDAÇÃO
// ====================================
// [INICIO] Log de Validacao Final
console.log("\n[ROUTE-PROTECTION] Sistema carregado com sucesso!");
console.log("[ROUTE-PROTECTION] Funcoes disponiveis:");
console.log("[ROUTE-PROTECTION]   - authProtection.getUser()");
console.log("[ROUTE-PROTECTION]   - authProtection.isAuthenticated()");
console.log("[ROUTE-PROTECTION]   - authProtection.logout()");
console.log("[ROUTE-PROTECTION]   - authProtection.getUserInfo()");
console.log("[ROUTE-PROTECTION]   - authProtection.hasRole(role)");
console.log("[ROUTE-PROTECTION]   - authProtection.hasAnyRole(roles)");
console.log("[ROUTE-PROTECTION]\n" + "=".repeat(80) + "\n");
// [FIM] Log de Validacao Final