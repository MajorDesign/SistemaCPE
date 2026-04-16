(() => {
    const btn = document.getElementById("btnToggleSidebar");
    const sidebar = document.querySelector(".app-sidebar");
  
    if (!btn || !sidebar) return;
  
    btn.addEventListener("click", () => {
      sidebar.classList.toggle("show");
    });
  
    // Fecha sidebar ao clicar fora (mobile)
    document.addEventListener("click", (e) => {
      const isMobile = window.matchMedia("(max-width: 767px)").matches;
      if (!isMobile) return;
  
      const clickedInsideSidebar = sidebar.contains(e.target);
      const clickedButton = btn.contains(e.target);
  
      if (!clickedInsideSidebar && !clickedButton && sidebar.classList.contains("show")){
        sidebar.classList.remove("show");
      }
    });
  })();
  