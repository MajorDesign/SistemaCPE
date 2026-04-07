// ================================================== 
// ARQUIVO: role-permissions.js
// FUNCAO: Mapear permissões de ROLE para PÁGINAS
// Data: 01/04/2026 17:30
// ==================================================

/**
 * MATRIZ DE PERMISSÕES
 * 
 * Define quais páginas cada ROLE pode acessar
 * Formato: { pagina: [roles_permitidos] }
 */

const ROLE_PERMISSIONS = {
    // ================================================== 
    // PÁGINAS ADMINISTRATIVAS - Apenas ADMIN
    // ==================================================
    'USERS': {
      allowedRoles: ['ADMIN'],
      description: 'Gerenciamento de Usuários',
      adminOnly: true
    },
    'GROUPS': {
      allowedRoles: ['ADMIN'],
      description: 'Gerenciamento de Grupos/Setores',
      adminOnly: true
    },
    'REGISTRATIONS': {
      allowedRoles: ['ADMIN'],
      description: 'Cadastros Diversos',
      adminOnly: true
    },
    'SETTINGS': {
      allowedRoles: ['ADMIN'],
      description: 'Configurações do Sistema',
      adminOnly: true
    },
    
    // ================================================== 
    // PÁGINAS SEMI-ADMINISTRATIVAS - ADMIN + TI
    // ==================================================
    'INVENTORY': {
      allowedRoles: ['ADMIN', 'TI'],
      description: 'Inventário de Equipamentos',
      adminOnly: false
    },
    'PASSWORD_VAULT': {
      allowedRoles: ['ADMIN', 'TI'],
      description: 'Cofre de Senhas',
      adminOnly: false
    },
    'REPORTS': {
      allowedRoles: ['ADMIN', 'TI'],
      description: 'Relatórios',
      adminOnly: false
    },
    'BILLING': {
      allowedRoles: ['ADMIN', 'TI'],
      description: 'Faturamento',
      adminOnly: false
    },
    
    // ================================================== 
    // PÁGINAS GERENCIAIS - ADMIN + MANAGER
    // ==================================================
    'DASHBOARD': {
      allowedRoles: ['USER', 'RESPONSAVEL_GRUPO', 'ADMIN', 'TI', 'MANAGER'],
      description: 'Dashboard Principal',
      adminOnly: false
    },
    
    // ================================================== 
    // PÁGINAS OPERACIONAIS - TODOS OS USUÁRIOS
    // ==================================================
    'TICKETS': {
      allowedRoles: ['USER', 'RESPONSAVEL_GRUPO', 'ADMIN', 'TI', 'MANAGER'],
      description: 'Gerenciamento de Tickets',
      adminOnly: false
    },
    'CHAT': {
      allowedRoles: ['USER', 'RESPONSAVEL_GRUPO', 'ADMIN', 'TI', 'MANAGER'],
      description: 'Chat',
      adminOnly: false
    },
    'TASKS': {
      allowedRoles: ['USER', 'RESPONSAVEL_GRUPO', 'ADMIN', 'TI', 'MANAGER'],
      description: 'Tarefas',
      adminOnly: false
    },
    'PROJECTS': {
      allowedRoles: ['USER', 'RESPONSAVEL_GRUPO', 'ADMIN', 'TI', 'MANAGER'],
      description: 'Projetos',
      adminOnly: false
    },
    'KNOWLEDGE_BASE': {
      allowedRoles: ['USER', 'RESPONSAVEL_GRUPO', 'ADMIN', 'TI', 'MANAGER'],
      description: 'Base de Conhecimento',
      adminOnly: false
    },
    'DOWNLOAD_AGENTS': {
      allowedRoles: ['USER', 'RESPONSAVEL_GRUPO', 'ADMIN', 'TI', 'MANAGER'],
      description: 'Download de Agentes',
      adminOnly: false
    }
  };
  
  /**
   * FUNCAO: canUserAccessPage()
   * 
   * Verifica se um usuário pode acessar uma página específica
   * 
   * @param {string} role - Role do usuário
   * @param {string} pageName - Nome da página (ex: 'USERS', 'GROUPS')
   * @returns {boolean} - true se pode acessar, false caso contrário
   */
  function canUserAccessPage(role, pageName) {
    const pagePerms = ROLE_PERMISSIONS[pageName];
    
    if (!pagePerms) {
      console.warn(`[ROLE-PERMS] Página '${pageName}' não encontrada na matriz de permissões`);
      return false;
    }
    
    return pagePerms.allowedRoles.includes(role);
  }
  
  /**
   * FUNCAO: getUserAccessiblePages()
   * 
   * Retorna lista de TODAS as páginas que um usuário pode acessar
   * 
   * @param {string} role - Role do usuário
   * @returns {array} - Array com nomes das páginas acessíveis
   */
  function getUserAccessiblePages(role) {
    return Object.entries(ROLE_PERMISSIONS)
      .filter(([pageName, perms]) => perms.allowedRoles.includes(role))
      .map(([pageName, perms]) => ({
        pageName,
        description: perms.description,
        adminOnly: perms.adminOnly
      }));
  }
  
  /**
   * FUNCAO: getRoleDescription()
   * 
   * Retorna descrição legível do role
   * 
   * @param {string} role - Role do usuário
   * @returns {string} - Descrição formatada
   */
  function getRoleDescription(role) {
    const roleDescriptions = {
      'USER': '👤 Usuário Comum - Acesso limitado a tickets e tarefas pessoais',
      'RESPONSAVEL_GRUPO': '👨‍💼 Responsável do Grupo - Gerencia tickets e usuários do grupo',
      'ADMIN': '🔐 Administrador - Acesso total ao sistema',
      'TI': '🔧 TI - Acesso a inventário, senhas e relatórios técnicos',
      'MANAGER': '📊 Gerente - Acesso a relatórios e gerenciamento de projetos'
    };
    
    return roleDescriptions[role] || role;
  }
  
  /**
   * FUNCAO: displayUserAccessiblePages()
   * 
   * Exibe em uma div qual usuário tem acesso a quais páginas
   * Usado na aba de permissões de usuários
   * 
   * @param {string} role - Role do usuário
   * @param {string} containerId - ID do elemento HTML onde exibir
   */
  function displayUserAccessiblePages(role, containerId = 'userAccessPages') {
    const container = document.getElementById(containerId);
    if (!container) {
      console.warn(`[ROLE-PERMS] Elemento #${containerId} não encontrado`);
      return;
    }
    
    const pages = getUserAccessiblePages(role);
    
    let html = `
      <div class="access-pages-container">
        <h6 style="margin-bottom: 1rem; color: #333;">
          <i class="bi bi-shield-check"></i> Páginas Acessíveis para <strong>${getRoleLabel(role)}</strong>
        </h6>
        
        <div class="pages-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem;">
    `;
    
    if (pages.length === 0) {
      html += `
        <div style="grid-column: 1/-1; text-align: center; color: #999; padding: 2rem;">
          <i class="bi bi-exclamation-circle" style="font-size: 2rem;"></i>
          <p>Nenhuma página acessível</p>
        </div>
      `;
    } else {
      pages.forEach(page => {
        const badge = page.adminOnly 
          ? '<span class="badge bg-danger" style="margin-left: 0.5rem;">Apenas Admin</span>'
          : '';
        
        html += `
          <div class="page-card" style="
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 1rem;
            transition: all 0.3s ease;
          ">
            <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
              <i class="bi bi-file-earmark-text" style="font-size: 1.5rem; margin-right: 0.5rem; color: #667eea;"></i>
              <strong>${page.pageName}</strong>
              ${badge}
            </div>
            <p style="margin: 0; color: #666; font-size: 0.9rem;">
              ${page.description}
            </p>
          </div>
        `;
      });
    }
    
    html += `
        </div>
      </div>
    `;
    
    container.innerHTML = html;
  }
  
  // ================================================== 
  // [FIM] role-permissions.js
  // Data: 01/04/2026 17:30
  // ==================================================