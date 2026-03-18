(() => {
    const form = document.getElementById("loginForm");
    const errorBox = document.getElementById("loginError");
    const btnToggle = document.getElementById("togglePwd");
    const pwd = document.getElementById("password");
  
    btnToggle?.addEventListener("click", () => {
      pwd.type = pwd.type === "password" ? "text" : "password";
      btnToggle.querySelector("i").className = pwd.type === "password" ? "bi bi-eye" : "bi bi-eye-slash";
    });
  
    form?.addEventListener("submit", async (e) => {
      e.preventDefault();
      errorBox.classList.add("d-none");
      errorBox.textContent = "";
  
      const email = document.getElementById("email").value.trim();
      const password = document.getElementById("password").value;
  
      try {
        const resp = await fetch("http://127.0.0.1:8000/api/auth/login", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password })
        });
  
        const data = await resp.json().catch(() => ({}));
  
        if (!resp.ok) {
          errorBox.textContent = data?.detail || "Falha no login.";
          errorBox.classList.remove("d-none");
          return;
        }
  
        // Redireciona para dashboard
        window.location.href = "/SistemaCPE/web/login.html";
      } catch (err) {
        errorBox.textContent = "Não foi possível conectar ao servidor.";
        errorBox.classList.remove("d-none");
      }
    });
  })();
  
  document.getElementById("loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    try {
        await apiFetch("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({ email, password })
        });

        window.location.href = "/SistemaCPE/web/login.html";
    } catch (err) {
        alert("Login inválido");
    }
});