/**
 * Inicializa a autenticação da página
 */
async function initPageAuth(pageName = "PÁGINA") {
  console.log("\n" + "=".repeat(60));
  console.log(`[${pageName}/INIT] Inicializando página...`);
  console.log("=".repeat(60));

  try {
    // ✅ Verifica se o usuário está autenticado
    console.log(`[${pageName}/INIT] Verificando autenticação...`);
    
    // Tenta obter os dados do usuário
    const user = await getMe();
    
    if (!user) {
      throw new Error("Usuário não autenticado");
    }

    console.log(`[${pageName}/INIT] ✓ Sessão válida, usuário:`, user.name);

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
    console.log(`[${pageName}/INIT] Renderizando navegação...`);
    
    if (typeof renderNavigation === "function") {
      await renderNavigation(user.role || "USER");
    } else {
      console.warn(`[${pageName}/INIT] renderNavigation não definida`);
    }

    console.log(`[${pageName}/INIT] ✓ Página carregada com sucesso`);
    console.log("=".repeat(60) + "\n");

    return user;

  } catch (err) {
    console.error(`[${pageName}/INIT] ✗ Erro na autenticação:`, err.message);
    console.log(`[${pageName}/INIT] Redirecionando para login em 2 segundos...`);

    // ✅ Remove o loading
    const loadingPage = document.getElementById("loadingPage");
    if (loadingPage) {
      loadingPage.style.display = "none";
    }

    // ✅ Redireciona para login
    setTimeout(() => {
      window.location.href = "/SistemaCPE/web/login.html";
    }, 2000);
    
    return null;
  }
}