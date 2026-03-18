// =========================================
// Verificação de Autenticação para Páginas Protegidas
// =========================================

(async () => {
    console.log("\n[AUTH-CHECK] Iniciando verificação de autenticação...");
  
    const maxRetries = 3;
    let retryCount = 0;
    let sessionValid = false;
  
    while (retryCount < maxRetries && !sessionValid) {
      try {
        console.log(`[AUTH-CHECK] Tentativa ${retryCount + 1} de ${maxRetries}...`);
  
        // Timeout de 5 segundos
        const user = await Promise.race([
          getMe(),
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error("Timeout na verificação de sessão")), 5000)
          )
        ]);
  
        console.log("[AUTH-CHECK] ✓ Sessão válida:", user.name);
        sessionValid = true;
  
        // Remove loading se existir
        const loadingPage = document.getElementById("loadingPage");
        if (loadingPage) {
          loadingPage.style.display = "none";
        }
  
        // Mostra conteúdo
        const mainContent = document.querySelector(".container-main") || document.querySelector("main") || document.body;
        if (mainContent) {
          mainContent.style.display = mainContent.style.display === "none" ? "block" : mainContent.style.display || "block";
        }
  
      } catch (err) {
        console.warn(`[AUTH-CHECK] ✗ Tentativa ${retryCount + 1} falhou:`, err.message);
        retryCount++;
  
        if (retryCount >= maxRetries) {
          console.error("[AUTH-CHECK] ✗ Falha na autenticação após todas as tentativas");
          console.log("[AUTH-CHECK] Redirecionando para login...");
  
          // Redireciona com delay
          setTimeout(() => {
            window.location.href = "/SistemaCPE/web/login.html";
          }, 1500);
        } else {
          // Aguarda antes de tentar novamente
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }
    }
  })();