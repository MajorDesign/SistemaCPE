(() => {
  const form = document.getElementById("loginForm");
  const credentialInput = document.getElementById("credential");
  const passwordInput = document.getElementById("password");
  const errorBox = document.getElementById("loginError");
  const errorMessage = document.getElementById("errorMessage");
  const submitBtn = document.getElementById("submitBtn");

  // ====================================
  // VALIDAR ELEMENTOS DO DOM
  // ====================================
  if (!form || !credentialInput || !passwordInput || !errorBox || !errorMessage || !submitBtn) {
    console.error("[LOGIN] ERRO: Elementos do formulario nao encontrados!");
    console.error("[LOGIN]   - loginForm:", form ? "OK" : "FALTANDO");
    console.error("[LOGIN]   - credentialInput:", credentialInput ? "OK" : "FALTANDO");
    console.error("[LOGIN]   - passwordInput:", passwordInput ? "OK" : "FALTANDO");
    console.error("[LOGIN]   - errorBox:", errorBox ? "OK" : "FALTANDO");
    console.error("[LOGIN]   - errorMessage:", errorMessage ? "OK" : "FALTANDO");
    console.error("[LOGIN]   - submitBtn:", submitBtn ? "OK" : "FALTANDO");
    return;
  }

  console.log("[LOGIN] ✓ Elementos do formulario carregados com sucesso");

  // ====================================
  // LIMPAR ERROS AO DIGITAR - CREDENTIAL
  // ====================================
  credentialInput.addEventListener("input", () => {
    errorBox.classList.remove("show");
    errorMessage.textContent = "";
  });

  // ====================================
  // LIMPAR ERROS AO DIGITAR - PASSWORD
  // ====================================
  passwordInput.addEventListener("input", () => {
    errorBox.classList.remove("show");
    errorMessage.textContent = "";
  });

  // ====================================
  // SUBMIT DO FORMULARIO
  // ====================================
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    console.log("\n" + "=".repeat(80));
    console.log("[LOGIN] 🔐 INICIANDO PROCESSO DE LOGIN");
    console.log("=".repeat(80));

    // [INICIO] Obter valores do formulario
    const credential = credentialInput.value.trim();
    const password = passwordInput.value.trim();

    console.log("[LOGIN] Dados do formulario:");
    console.log(`[LOGIN]   - credential: "${credential}"`);
    console.log(`[LOGIN]   - password: "${'*'.repeat(password.length)}"`);
    // [FIM] Obter valores do formulario

    // [INICIO] Validar credential
    if (!credential) {
      showError("Por favor, preencha o campo de email ou usuario");
      return;
    }

    if (credential.length < 3) {
      showError("Email ou usuario deve ter no minimo 3 caracteres");
      return;
    }
    // [FIM] Validar credential

    // [INICIO] Validar password
    if (!password) {
      showError("Por favor, preencha o campo de senha");
      return;
    }

    if (password.length < 6) {
      showError("A senha deve ter no minimo 6 caracteres");
      return;
    }
    // [FIM] Validar password

    // [INICIO] Desabilitar botao
    submitBtn.disabled = true;
    const spinner = submitBtn.querySelector(".button-spinner");
    const text = submitBtn.querySelector(".button-text");
    if (spinner) spinner.style.display = "inline-block";
    if (text) text.textContent = "Autenticando...";
    // [FIM] Desabilitar botao

    try {
      console.log("[LOGIN] ✓ Validacoes basicas concluidas");
      console.log(`[LOGIN] 📝 Credencial fornecida: ${credential}`);
      console.log(`[LOGIN] 📝 Senha fornecida: ${'*'.repeat(password.length)}`);
      console.log("[LOGIN] 🔍 Validando credenciais no banco de dados...");

      // [INICIO] Construir payload
      const payload = {
        credential: credential,
        password: password
      };

      console.log("[LOGIN] Payload construido:");
      console.log("[LOGIN]   - credential:", payload.credential);
      console.log("[LOGIN]   - password:", '*'.repeat(payload.password.length));
      // [FIM] Construir payload

      // [INICIO] Fazer requisicao para API
      console.log("[LOGIN] 📡 Enviando requisicao para API...");
      console.log("[LOGIN]   - URL: http://127.0.0.1:8000/api/auth/login");
      console.log("[LOGIN]   - Method: POST");

      const response = await fetch("http://127.0.0.1:8000/api/auth/login", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify(payload)
      });

      console.log(`[LOGIN] 📊 Status da resposta: ${response.status}`);
      console.log(`[LOGIN] 📊 Status text: ${response.statusText}`);

      const data = await response.json();

      console.log("[LOGIN] ✓ Resposta recebida da API");
      // [FIM] Fazer requisicao para API

      // [INICIO] Processar resposta
      if (!response.ok) {
        console.error("[LOGIN] ❌ ERRO na resposta da API!");
        console.error(`[LOGIN]   - Status: ${response.status}`);
        console.error(`[LOGIN]   - Status text: ${response.statusText}`);

        if (Array.isArray(data.detail)) {
          console.error("[LOGIN]   - Erros de validacao:");
          data.detail.forEach((err, index) => {
            console.error(`[LOGIN]      [${index}] Campo: ${err.loc ? err.loc.join(' > ') : 'N/A'}`);
            console.error(`[LOGIN]           Mensagem: ${err.msg}`);
            console.error(`[LOGIN]           Tipo: ${err.type}`);
          });
          throw new Error("Erro de validacao nos dados enviados");
        } else if (data.detail) {
          console.error(`[LOGIN]   - Mensagem: ${data.detail}`);
          throw new Error(data.detail);
        } else {
          console.error("[LOGIN]   - Resposta:", JSON.stringify(data));
          throw new Error("Falha ao autenticar. Verifique suas credenciais.");
        }
      }
      // [FIM] Processar resposta

      // [INICIO] Login bem-sucedido
      console.log("[LOGIN] ✅ LOGIN BEM-SUCEDIDO!");
      console.log(`[LOGIN]   - Nome: ${data.user.name}`);
      console.log(`[LOGIN]   - Email: ${data.user.email}`);
      console.log(`[LOGIN]   - Username: ${data.user.username}`);
      console.log(`[LOGIN]   - ID: ${data.user.id}`);
      console.log(`[LOGIN]   - Role: ${data.user.role}`);
      console.log(`[LOGIN]   - Ativo: ${data.user.is_active}`);

      // [INICIO] Salvar dados no localStorage - CHAVES CORRETAS!
      console.log("[LOGIN] 💾 Salvando dados no localStorage...");
      
      // ✅ CHAVE CORRIGIDA: "cpe_user" (não "user")
      localStorage.setItem("cpe_user", JSON.stringify(data.user));
      console.log("[LOGIN]   ✓ cpe_user salvo");
      
      // ✅ CHAVE CORRIGIDA: "cpe_token" (não "user_id")
      localStorage.setItem("cpe_token", data.user.id);
      console.log("[LOGIN]   ✓ cpe_token salvo");
      
      // ✅ SALVAR TAMBÉM EM sessionStorage
      sessionStorage.setItem("cpe_user", JSON.stringify(data.user));
      console.log("[LOGIN]   ✓ cpe_user (sessionStorage) salvo");
      
      sessionStorage.setItem("cpe_token", data.user.id);
      console.log("[LOGIN]   ✓ cpe_token (sessionStorage) salvo");

      console.log("[LOGIN] ✓ Todos os dados salvos com sucesso!");
      console.log("[LOGIN] 🔄 Redirecionando para dashboard...");
      console.log("=".repeat(80) + "\n");

      // [INICIO] Redirecionar
      const redirectUrl = sessionStorage.getItem("redirectAfterLogin") || "/SistemaCPE/index.html";
      sessionStorage.removeItem("redirectAfterLogin");

      console.log(`[LOGIN] 🎯 URL de redirecionamento: ${redirectUrl}`);

      setTimeout(() => {
        window.location.href = redirectUrl;
      }, 500);
      // [FIM] Redirecionar

    } catch (err) {
      console.error("[LOGIN] ❌ ERRO NA REQUISICAO!");
      console.error(`[LOGIN]   - Tipo: ${err.name}`);
      console.error(`[LOGIN]   - Mensagem: ${err.message}`);
      console.error(`[LOGIN]   - Stack: ${err.stack}`);
      console.error("=".repeat(80) + "\n");

      showError(err.message);

      // [INICIO] Restaurar botao
      submitBtn.disabled = false;
      if (spinner) spinner.style.display = "none";
      if (text) text.textContent = "Entrar no Sistema";
      // [FIM] Restaurar botao

    }
  });

  // ====================================
  // FUNCAO: MOSTRAR ERRO
  // ====================================
  // [INICIO] showError()
  function showError(message) {
    console.warn(`[LOGIN] ⚠️  ${message}`);
    
    if (errorMessage) {
      errorMessage.textContent = message;
    }
    
    if (errorBox) {
      errorBox.classList.add("show");
    }
  }
  // [FIM] showError()

})();