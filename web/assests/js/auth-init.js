/**
 * ============================================================
 * INICIALIZAÇÃO PADRÃO DE AUTENTICAÇÃO
 * Use isso em TODAS as páginas protegidas
 * ============================================================
 */

async function initPageAuth(pageTitle = "Página") {
    console.log("\n" + "=".repeat(60));
    console.log(`[${pageTitle.toUpperCase()}/INIT] Inicializando página...`);
    console.log("=".repeat(60));
  
    try {
      // ✅ Verifica se o usuário está autenticado
      console.log(`[${pageTitle.toUpperCase()}/INIT] Verificando autenticação...`);
      const user = await getMe();
  
      console.log(`[${pageTitle.toUpperCase()}/INIT] ✓ Sessão válida, usuário:`, user.name);
  
      // ✅ Remove a tela de loading
      const loadingPage = document.getElementById("loadingPage");
      if (loadingPage) {
        loadingPage.style.display = "none";
      }
  
      // ✅ Mostra o conteúdo principal
      const containerMain = document.querySelector(".container-main");
      if (containerMain) {
        containerMain.style.display = "flex";
      }
  
      // ✅ Renderiza o menu dinâmico
      console.log(`[${pageTitle.toUpperCase()}/INIT] Renderizando navegação...`);
      await renderNavigation(user.role || "USER");
  
      console.log(`[${pageTitle.toUpperCase()}/INIT] ✓ Página carregada com sucesso`);
      console.log("=".repeat(60) + "\n");
  
      return user;
  
    } catch (err) {
      console.error(`[${pageTitle.toUpperCase()}/INIT] ✗ Erro na autenticação:`, err.message);
      console.log(`[${pageTitle.toUpperCase()}/INIT] Redirecionando para login...`);
  
      // ✅ Redireciona para login
      setTimeout(() => {
        window.location.href = "/SistemaCPE/web/login.html";
      }, 1000);
    }
  }