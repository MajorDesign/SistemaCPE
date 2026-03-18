document.addEventListener("DOMContentLoaded", () => {
    fetch("./components/header.html")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Erro ao carregar o header.html");
        }
        return response.text();
      })
      .then((html) => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, "text/html");
        const headContent = doc.head.innerHTML;
  
        document.head.innerHTML += headContent;
      })
      .catch((error) => {
        console.error("Erro ao carregar o cabeçalho:", error);
      });
  });