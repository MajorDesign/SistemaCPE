// Componentes reutilizáveis

const sidebarHTML = `
<div class="sidebar">
  <div class="sidebar-header">
    <div class="sidebar-logo">M</div>
    <div class="sidebar-title">MILVUS</div>
  </div>
  
  <div class="search-box">
    <input type="text" placeholder="Buscar">
  </div>
  
  <ul class="sidebar-menu">
    <li class="menu-item">
      <a href="index.html" class="menu-link">
        <span class="menu-icon">📊</span>
        <span>Dashboards</span>
      </a>
    </li>
    <li class="menu-item">
      <a href="pages/tickets.html" class="menu-link">
        <span class="menu-icon">🎫</span>
        <span>Tickets</span>
      </a>
    </li>
    <li class="menu-item">
      <a href="pages/chat.html" class="menu-link">
        <span class="menu-icon">💬</span>
        <span>Chat</span>
        <span class="menu-badge">BETA</span>
      </a>
    </li>
    <li class="menu-item">
      <a href="pages/tasks.html" class="menu-link">
        <span class="menu-icon">✓</span>
        <span>Tarefas</span>
      </a>
    </li>
    <li class="menu-item">
      <a href="pages/projects.html" class="menu-link">
        <span class="menu-icon">📁</span>
        <span>Projetos</span>
        <span class="menu-badge">BETA</span>
      </a>
    </li>
    <li class="menu-item">
      <a href="pages/inventory.html" class="menu-link">
        <span class="menu-icon">📦</span>
        <span>Inventário</span>
      </a>
    </li>
    <li class="menu-item">
      <a href="pages/reports.html" class="menu-link">
        <span class="menu-icon">📈</span>
        <span>Relatórios</span>
      </a>
    </li>
    <li class="menu-item">
      <a href="pages/billing.html" class="menu-link">
        <span class="menu-icon">💰</span>
        <span>Faturamento</span>
      </a>
    </li>
    <li class="menu-item">
      <a href="pages/knowledge-base.html" class="menu-link">
        <span class="menu-icon">📚</span>
        <span>Base de conhecimento</span>
      </a>
    </li>
    <li class="menu-item">
      <a href="pages/registrations.html" class="menu-link">
        <span class="menu-icon">👥</span>
        <span>Cadastros</span>
      </a>
    </li>
    <li class="menu-item">
      <a href="pages/settings.html" class="menu-link">
        <span class="menu-icon">⚙️</span>
        <span>Configurações</span>
      </a>
    </li>
    <li class="menu-item">
      <a href="pages/download-agents.html" class="menu-link">
        <span class="menu-icon">⬇️</span>
        <span>Download de Agentes</span>
      </a>
    </li>
  </ul>
</div>
`;

// Função para inserir sidebar em todas as páginas
function insertSidebar() {
  const container = document.querySelector('.container-main');
  if (container && !container.querySelector('.sidebar')) {
    const sidebarDiv = document.createElement('div');
    sidebarDiv.innerHTML = sidebarHTML;
    container.insertBefore(sidebarDiv.firstElementChild, container.firstChild);
  }
}

// Função para criar header
function createHeader(title) {
  return `
    <div class="top-bar">
      <button class="menu-toggle">☰</button>
      <h1>${title}</h1>
    </div>
  `;
}

// Executar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', insertSidebar);
