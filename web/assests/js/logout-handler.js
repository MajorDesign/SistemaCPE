/**
 * 🚪 LOGOUT HANDLER - Gerencia logout em qualquer página
 */

class LogoutHandler {
    constructor(buttonSelector = "#logoutBtn") {
      this.button = document.querySelector(buttonSelector);
      if (this.button) {
        this.button.addEventListener("click", () => this.handleLogout());
      }
    }
  
    handleLogout() {
      if (!authProtection) {
        console.error("authProtection não está disponível");
        return;
      }
  
      if (confirm("Tem certeza que deseja sair?")) {
        authProtection.logout();
      }
    }
  }
  
  // Instanciar automaticamente quando houver botão
  document.addEventListener("DOMContentLoaded", () => {
    const logoutHandler = new LogoutHandler("#logoutBtn");
  });