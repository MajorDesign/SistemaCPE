// ===== INÍCIO: users.js (Gerenciamento de Usuários) =====

// =========================================
// Formulário de Adicionar Usuário
// =========================================

document.addEventListener("DOMContentLoaded", function() {
    console.log("[USERS/JS] Inicializando módulo de usuários");
  
    const addUserForm = document.getElementById("addUserForm");
    const submitBtn = document.getElementById("submitBtn");
    const modalAlertBox = document.getElementById("modalAlertBox");
    const modalAlertMessage = document.getElementById("modalAlertMessage");
  
    const inputName = document.getElementById("inputName");
    const inputEmail = document.getElementById("inputEmail");
    const inputUsername = document.getElementById("inputUsername");
    const inputPassword = document.getElementById("inputPassword");
    const inputPasswordConfirm = document.getElementById("inputPasswordConfirm");
    const inputRole = document.getElementById("inputRole");
  
    const togglePassword = document.getElementById("togglePassword");
    const togglePasswordConfirm = document.getElementById("togglePasswordConfirm");
  
    // ===== Toggle de Senhas =====
    togglePassword?.addEventListener("click", () => {
      const type = inputPassword.type === "password" ? "text" : "password";
      inputPassword.type = type;
      togglePassword.innerHTML = type === "password" 
        ? '<i class="bi bi-eye"></i>' 
        : '<i class="bi bi-eye-slash"></i>';
    });
  
    togglePasswordConfirm?.addEventListener("click", () => {
      const type = inputPasswordConfirm.type === "password" ? "text" : "password";
      inputPasswordConfirm.type = type;
      togglePasswordConfirm.innerHTML = type === "password" 
        ? '<i class="bi bi-eye"></i>' 
        : '<i class="bi bi-eye-slash"></i>';
    });
  
    // ===== Formatar Username =====
    inputUsername?.addEventListener("input", (e) => {
      // Remove caracteres especiais, mantém apenas letras, números e underscore
      let value = e.target.value
        .toLowerCase()
        .replace(/[^a-z0-9_]/g, "");
      e.target.value = value;
    });
  
    // ===== Submissão do Formulário =====
    addUserForm?.addEventListener("submit", async (e) => {
      e.preventDefault();
  
      console.log("[USERS/FORM] Validando formulário...");
  
      // Limpa mensagens de erro anteriores
      modalAlertBox.classList.add("d-none");
  
      // Validação básica
      if (!inputName.value?.trim()) {
        showModalError("Por favor, preencha o nome completo");
        inputName.classList.add("is-invalid");
        return;
      }
  
      if (!inputEmail.value?.trim()) {
        showModalError("Por favor, preencha o e-mail");
        inputEmail.classList.add("is-invalid");
        return;
      }
  
      if (!inputUsername.value?.trim()) {
        showModalError("Por favor, preencha o username");
        inputUsername.classList.add("is-invalid");
        return;
      }
  
      if (!inputPassword.value) {
        showModalError("Por favor, preencha a senha");
        inputPassword.classList.add("is-invalid");
        return;
      }
  
      if (inputPassword.value.length < 8) {
        showModalError("A senha deve ter no mínimo 8 caracteres");
        inputPassword.classList.add("is-invalid");
        return;
      }
  
      if (inputPassword.value !== inputPasswordConfirm.value) {
        showModalError("As senhas não conferem");
        inputPasswordConfirm.classList.add("is-invalid");
        return;
      }
  
      if (!inputRole.value) {
        showModalError("Por favor, selecione um tipo de permissão");
        inputRole.classList.add("is-invalid");
        return;
      }
  
      console.log("[USERS/FORM] ✓ Formulário válido");
  
      // Desabilita o botão
      submitBtn.disabled = true;
      submitBtn.innerHTML = `
        <span class="spinner-border spinner-border-sm loading-spinner"></span>
        Criando usuário...
      `;
  
      try {
        console.log("[USERS/FORM] Enviando dados para criar usuário...");
  
        // Faz a requisição para criar o usuário
        const response = await apiFetch("/api/users", {
          method: "POST",
          body: JSON.stringify({
            name: inputName.value.trim(),
            email: inputEmail.value.trim(),
            username: inputUsername.value.trim(),
            password: inputPassword.value,
            role: inputRole.value,
          }),
        });
  
        console.log("[USERS/FORM] ✓ Usuário criado com sucesso");
  
        // Mostra mensagem de sucesso
        const successMsg = `Usuário "${inputName.value}" criado com sucesso!`;
        document.getElementById("successMessage").textContent = successMsg;
        document.getElementById("successBox").classList.remove("d-none");
  
        // Limpa o formulário
        addUserForm.reset();
        document.querySelectorAll(".form-control, .form-select").forEach(el => {
          el.classList.remove("is-invalid");
        });
  
        // Fecha o modal
        const modal = bootstrap.Modal.getInstance(document.getElementById("userModal"));
        modal?.hide();
  
        // Aguarda um pouco e recarrega a página
        setTimeout(() => {
          location.reload();
        }, 1500);
  
      } catch (err) {
        console.error("[USERS/FORM] ✗ Erro:", err.message);
  
        // Verifica se é erro de email duplicado
        if (err.message.includes("409") || err.message.includes("já cadastrado")) {
          showModalError("Este e-mail já está cadastrado no sistema");
          inputEmail.classList.add("is-invalid");
        } else if (err.message.includes("username")) {
          showModalError("Este username já está em uso");
          inputUsername.classList.add("is-invalid");
        } else {
          showModalError("Erro ao criar usuário: " + err.message);
        }
  
        // Reabilita o botão
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="bi bi-check-lg"></i> Criar Usuário';
      }
    });
  
    /**
     * Mostra mensagem de erro no modal
     */
    function showModalError(message) {
      modalAlertMessage.textContent = message;
      modalAlertBox.classList.remove("d-none");
      window.scrollTo(0, 0);
    }
  
    console.log("[USERS/JS] ✓ Módulo de usuários inicializado");
  });
  
  // ===== FIM: users.js (Gerenciamento de Usuários) =====