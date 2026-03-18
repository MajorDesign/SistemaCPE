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
        ],
        enableLogging: true,
        redirectDelay: 500,
        ...config
      };
  
      this.user = null;
      this.isLoggedIn = false;
      this.eventDispatched = false;
  
      // ✅ CORRIGIDO: Aguardar DOM estar pronto com delay
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => {
          setTimeout(() => this.init(), 50);
        });
      } else {
        setTimeout(() => this.init(), 50);
      }
    }
  
    // ====================================
    // INICIALIZAÇÃO
    // ====================================
    // [INICIO] init()
    init() {
      this.log("\n" + "=".repeat(80));
      this.log("[ROUTE-PROTECTION] 🔐 Sistema de proteção de rotas inicializado");
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
      this.log("[ROUTE-PROTECTION] 🔍 Verificando autenticação...");
  
      const userStr = localStorage.getItem("cpe_user");
      const token = localStorage.getItem("cpe_token");
  
      const userStrSession = sessionStorage.getItem("cpe_user");
      const tokenSession = sessionStorage.getItem("cpe_token");
  
      const finalUserStr = userStr || userStrSession;
      const finalToken = token || tokenSession;
  
      this.isLoggedIn = finalUserStr !== null && finalToken !== null;
  
      if (this.isLoggedIn && finalUserStr) {
        try {
          this.user = JSON.parse(finalUserStr);
          this.log(`[ROUTE-PROTECTION] ✅ Usuário autenticado: ${this.user.name}`);
          this.log(`[ROUTE-PROTECTION]   • Email: ${this.user.email}`);
          this.log(`[ROUTE-PROTECTION]   • Role: ${this.user.role}`);
          this.log(`[ROUTE-PROTECTION]   • ID: ${this.user.id}`);
        } catch (err) {
          this.log(
            `[ROUTE-PROTECTION] ⚠️  Erro ao recuperar dados: ${err.message}`
          );
          this.isLoggedIn = false;
          this.user = null;
          localStorage.removeItem("cpe_user");
          localStorage.removeItem("cpe_token");
          sessionStorage.removeItem("cpe_user");
          sessionStorage.removeItem("cpe_token");
        }
      } else {
        this.log("[ROUTE-PROTECTION] ⚠️  Nenhum usuário autenticado");
      }
    }
    // [FIM] checkAuthentication()
  
    // ====================================
    // VALIDAR ACESSO À PÁGINA
    // ====================================
    // [INICIO] validatePageAccess()
    validatePageAccess() {
      const currentPage = window.location.pathname;
  
      this.log(`[ROUTE-PROTECTION] 📍 Página atual: ${currentPage}`);
  
      const isProtectedPage = this.config.protectedPages.some((page) =>
        currentPage.includes(page)
      );
      const isPublicPage = this.config.publicPages.some((page) =>
        currentPage.includes(page)
      );
  
      this.log(`[ROUTE-PROTECTION] 🔒 Página protegida: ${isProtectedPage}`);
      this.log(`[ROUTE-PROTECTION] 🔓 Página pública: ${isPublicPage}`);
  
      // ✅ CASO 1: Página protegida SEM autenticação
      if (isProtectedPage && !this.isLoggedIn) {
        this.log(
          `[ROUTE-PROTECTION] ❌ Acesso negado! Redirecionando para login...`
        );
        this.redirectToLogin(currentPage);
        return;
      }
  
      // ✅ CASO 2: Página de login COM autenticação
      if (isPublicPage && this.isLoggedIn && this.user) {
        this.log(
          `[ROUTE-PROTECTION] ℹ️  Já autenticado. Redirecionando para dashboard...`
        );
        this.redirectToDashboard();
        return;
      }
  
      // ✅ CASO 3: Página protegida COM autenticação
      if (isProtectedPage && this.isLoggedIn && this.user) {
        this.log(`[ROUTE-PROTECTION] ✅ Acesso permitido!`);
        this.markPageAsLoaded();
        return;
      }
  
      // ✅ CASO 4: Página pública SEM autenticação
      if (isPublicPage && !this.isLoggedIn) {
        this.log(`[ROUTE-PROTECTION] ✅ Página pública acessível`);
        this.markPageAsLoaded();
        return;
      }
    }
    // [FIM] validatePageAccess()
  
    // ====================================
    // REDIRECIONAR PARA LOGIN
    // ====================================
    // [INICIO] redirectToLogin()
    redirectToLogin(from) {
      if (from && from !== this.config.loginPageUrl) {
        sessionStorage.setItem("redirectAfterLogin", from);
        this.log(`[ROUTE-PROTECTION] 💾 URL de origem salva: ${from}`);
      }
  
      this.log(
        `[ROUTE-PROTECTION] ⏳ Redirecionando em ${this.config.redirectDelay}ms...`
      );
  
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
      this.log(
        `[ROUTE-PROTECTION] ⏳ Redirecionando em ${this.config.redirectDelay}ms...`
      );
  
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
      // Remover overlay de loading
      const loadingPage = document.getElementById("loadingPage");
      if (loadingPage) {
        loadingPage.style.display = "none";
        this.log(`[ROUTE-PROTECTION] ✓ Loading overlay removido`);
      }
  
      // Mostrar conteúdo
      const containerMain = document.querySelector(".container-main");
      if (containerMain) {
        containerMain.style.display = "flex";
        this.log(`[ROUTE-PROTECTION] ✓ Conteúdo da página exibido`);
      }
  
      // Disparar evento com delay para garantir que listeners estão prontos
      if (!this.eventDispatched && this.user) {
        setTimeout(() => {
          this.log(
            `[ROUTE-PROTECTION] 📢 Disparando evento authenticationSuccess...`
          );
          const event = new CustomEvent("authenticationSuccess", {
            detail: { user: this.user },
          });
          document.dispatchEvent(event);
          this.eventDispatched = true;
          this.log(`[ROUTE-PROTECTION] ✓ Evento disparado com sucesso`);
        }, 100);
      }
    }
    // [FIM] markPageAsLoaded()
  
    // ====================================
    // FUNÇÕES PÚBLICAS
    // ====================================
  
    // [INICIO] getUser()
    /**
     * Obter dados do usuário autenticado
     * @returns {Object|null} Dados do usuário ou null
     */
    getUser() {
      return this.user;
    }
    // [FIM] getUser()
  
    // [INICIO] isAuthenticated()
    /**
     * Verificar se usuário está autenticado
     * @returns {Boolean} true se autenticado
     */
    isAuthenticated() {
      return this.isLoggedIn && this.user !== null;
    }
    // [FIM] isAuthenticated()
  
    // [INICIO] logout()
    /**
     * Fazer logout e limpar dados de sessão
     */
    logout() {
      this.log("\n[ROUTE-PROTECTION] 🚪 Logout iniciado...");
  
      // Remover dados novos
      localStorage.removeItem("cpe_user");
      localStorage.removeItem("cpe_token");
      sessionStorage.removeItem("cpe_user");
      sessionStorage.removeItem("cpe_token");
  
      // Remover dados antigos (compatibilidade)
      localStorage.removeItem("user_id");
      localStorage.removeItem("user");
      localStorage.removeItem("logged_in");
      localStorage.removeItem("login_time");
      localStorage.removeItem("token");
  
      this.log("[ROUTE-PROTECTION] 💾 Dados de sessão removidos");
      this.log("[ROUTE-PROTECTION] ⏳ Redirecionando para login...");
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
     * Obter informações do usuário formatadas
     * @returns {Object|null} Informações do usuário ou null
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
        createdAt: this.user.created_at,
      };
    }
    // [FIM] getUserInfo()
  
    // [INICIO] hasRole()
    /**
     * Verificar se usuário tem uma role específica
     * @param {String} role - Role a verificar (ex: 'ADMIN', 'USER')
     * @returns {Boolean} true se usuário tem a role
     */
    hasRole(role) {
      if (!this.isAuthenticated()) return false;
      return this.user.role === role;
    }
    // [FIM] hasRole()
  
    // [INICIO] hasAnyRole()
    /**
     * Verificar se usuário tem uma das roles especificadas
     * @param {Array} roles - Array de roles a verificar
     * @returns {Boolean} true se usuário tem uma das roles
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