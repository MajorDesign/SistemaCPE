// ===== INÍCIO: password-vault.js (Gerenciador de Cofre de Senhas) =====

// =========================================
// Classe: PasswordVault
// =========================================

class PasswordVault {
    constructor() {
      this.currentUser = null;
      this.currentDepartment = null;
      this.passwords = [];
      this.devices = [];
      this.groups = [];
    }
  
    /**
     * Inicializa o cofre de senhas
     */
    async init() {
      try {
        console.log("[VAULT] Inicializando cofre de senhas...");
  
        // Obtém dados do usuário
        this.currentUser = await getMe();
  
        console.log("[VAULT] ✓ Usuário:", this.currentUser.name);
  
        // Carrega dados do departamento
        await this.loadDepartmentData();
  
        // Carrega senhas do departamento
        await this.loadPasswords();
  
        // Carrega grupos
        await this.loadGroups();
  
        console.log("[VAULT] ✓ Cofre de senhas inicializado");
  
        return true;
  
      } catch (err) {
        console.error("[VAULT] ✗ Erro ao inicializar:", err.message);
        throw err;
      }
    }
  
    /**
     * Carrega dados do departamento do usuário
     */
    async loadDepartmentData() {
      try {
        console.log("[VAULT] Carregando dados do departamento...");
  
        const response = await apiFetch("/api/users/me/department", {
          method: "GET",
        });
  
        this.currentDepartment = response;
  
        console.log("[VAULT] ✓ Departamento:", this.currentDepartment.name);
  
      } catch (err) {
        console.error("[VAULT] ✗ Erro ao carregar departamento:", err.message);
        throw err;
      }
    }
  
    /**
     * Carrega senhas do departamento
     */
    async loadPasswords() {
      try {
        console.log("[VAULT] Carregando senhas...");
  
        const response = await apiFetch(
          `/api/passwords?department_id=${this.currentDepartment.id}`,
          { method: "GET" }
        );
  
        this.passwords = response.data || [];
  
        console.log("[VAULT] ✓ Senhas carregadas:", this.passwords.length);
  
        return this.passwords;
  
      } catch (err) {
        console.error("[VAULT] ✗ Erro ao carregar senhas:", err.message);
        throw err;
      }
    }
  
    /**
     * Carrega grupos de permissão
     */
    async loadGroups() {
      try {
        console.log("[VAULT] Carregando grupos...");
  
        const response = await apiFetch("/api/groups", { method: "GET" });
  
        this.groups = response.data || [];
  
        console.log("[VAULT] ✓ Grupos carregados:", this.groups.length);
  
        return this.groups;
  
      } catch (err) {
        console.error("[VAULT] ✗ Erro ao carregar grupos:", err.message);
        throw err;
      }
    }
  
    /**
     * Gera uma senha aleatória
     */
    generatePassword(length = 16, options = {}) {
      const uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
      const lowercase = "abcdefghijklmnopqrstuvwxyz";
      const numbers = "0123456789";
      const symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?";
  
      let chars = lowercase + uppercase + numbers;
  
      if (options.symbols) chars += symbols;
      if (options.excludeAmbiguous) {
        chars = chars.replace(/[il1Lo0O]/g, "");
      }
  
      let password = "";
      for (let i = 0; i < length; i++) {
        password += chars.charAt(Math.floor(Math.random() * chars.length));
      }
  
      return password;
    }
  
    /**
     * Cria uma nova senha
     */
    async createPassword(data) {
      try {
        console.log("[VAULT] Criando nova senha...");
  
        const response = await apiFetch("/api/passwords", {
          method: "POST",
          body: JSON.stringify({
            ...data,
            department_id: this.currentDepartment.id,
            created_by: this.currentUser.id,
          }),
        });
  
        console.log("[VAULT] ✓ Senha criada com ID:", response.id);
  
        // Recarrega senhas
        await this.loadPasswords();
  
        return response;
  
      } catch (err) {
        console.error("[VAULT] ✗ Erro ao criar senha:", err.message);
        throw err;
      }
    }
  
    /**
     * Atualiza uma senha existente
     */
    async updatePassword(id, data) {
      try {
        console.log("[VAULT] Atualizando senha ID:", id);
  
        const response = await apiFetch(`/api/passwords/${id}`, {
          method: "PUT",
          body: JSON.stringify(data),
        });
  
        console.log("[VAULT] ✓ Senha atualizada");
  
        // Recarrega senhas
        await this.loadPasswords();
  
        return response;
  
      } catch (err) {
        console.error("[VAULT] ✗ Erro ao atualizar senha:", err.message);
        throw err;
      }
    }
  
    /**
     * Deleta uma senha
     */
    async deletePassword(id) {
      try {
        console.log("[VAULT] Deletando senha ID:", id);
  
        await apiFetch(`/api/passwords/${id}`, {
          method: "DELETE",
        });
  
        console.log("[VAULT] ✓ Senha deletada");
  
        // Recarrega senhas
        await this.loadPasswords();
  
      } catch (err) {
        console.error("[VAULT] ✗ Erro ao deletar senha:", err.message);
        throw err;
      }
    }
  
    /**
     * Registra acesso a uma senha (auditoria)
     */
    async logAccess(passwordId, action = "VIEW") {
      try {
        console.log(`[VAULT] Registrando ${action} da senha:`, passwordId);
  
        await apiFetch("/api/audit-logs", {
          method: "POST",
          body: JSON.stringify({
            module: "PASSWORD_VAULT",
            action: action,
            object_id: passwordId,
            object_type: "PASSWORD",
            user_id: this.currentUser.id,
            department_id: this.currentDepartment.id,
            ip_address: await this.getUserIP(),
          }),
        });
  
        console.log("[VAULT] ✓ Acesso registrado");
  
      } catch (err) {
        console.warn("[VAULT] Não foi possível registrar acesso:", err.message);
      }
    }
  
    /**
     * Obtém IP do usuário
     */
    async getUserIP() {
      try {
        const response = await fetch("https://api.ipify.org?format=json");
        const data = await response.json();
        return data.ip;
      } catch (err) {
        return "0.0.0.0";
      }
    }
  
    /**
     * Verifica se o usuário pode visualizar uma senha
     */
    canViewPassword(password) {
      // Se é público, todos podem ver
      if (password.is_public) return true;
  
      // Se é do usuário, pode ver
      if (password.created_by === this.currentUser.id) return true;
  
      // Se está compartilhado com o grupo do usuário, pode ver
      if (password.shared_with && password.shared_with.includes(this.currentUser.group_id)) {
        return true;
      }
  
      return false;
    }
  
    /**
     * Filtra senhas visíveis para o usuário
     */
    getVisiblePasswords() {
      return this.passwords.filter(pwd => this.canViewPassword(pwd));
    }
  }
  
  // Instância global
  const vault = new PasswordVault();
  
  // ===== FIM: password-vault.js (Gerenciador de Cofre de Senhas) =====