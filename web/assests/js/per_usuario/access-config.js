// ================================================== 
// ARQUIVO: access-config.js
// FUNÇÃO: Configuração centralizada de acesso a páginas e funcionalidades
// Data: 06/04/2026 20:15
// OBJETIVO: Um único local para gerenciar TODAS as restrições do sistema
// ==================================================

/**
 * CONFIGURAÇÃO DE ACESSO - SISTEMA CENTRALIZADO
 * 
 * Este arquivo é o LOCAL ÚNICO para gerenciar:
 * - Acesso a páginas
 * - Acesso a funcionalidades específicas
 * - Exceções e regras especiais
 * 
 * Quando precisar adicionar novas restrições:
 * 1. Abra este arquivo
 * 2. Localize a seção apropriada
 * 3. Adicione a nova regra
 * 4. Pronto! Não precisa mexer em mais nada
 */

// ================================================== 
// SECTION 1: CONFIGURAÇÃO DE ACESSO A PÁGINAS
// Data: 06/04/2026 20:15
// ==================================================

/**
 * Define quais ROLES podem acessar cada página
 * 
 * Structure:
 * {
 *   'NOME_PAGINA': {
 *     allowedRoles: ['ADMIN', 'TI', 'MANAGER'],
 *     description: 'Descrição da página',
 *     requiresApproval: false  // Se true, precisa de aprovação adicional
 *   }
 * }
 */
const PAGE_ACCESS_CONFIG = {
    // ================================================== 
    // PÁGINAS ADMINISTRATIVAS - Apenas ADMIN e TI
    // ==================================================
    'USERS': {
      allowedRoles: ['ADMIN', 'TI'],
      description: 'Gerenciamento de Usuários - Criar, editar, deletar usuários',
      requiresApproval: false
    },
    
    'GROUPS': {
      allowedRoles: ['ADMIN', 'TI', 'MANAGER'],
      description: 'Gerenciamento de Grupos/Setores',
      requiresApproval: false
    },
    
    'REGISTRATIONS': {
      allowedRoles: ['ADMIN', 'TI', 'MANAGER'],
      description: 'Cadastros Diversos',
      requiresApproval: false
    },
    
    'REPORTS': {
      allowedRoles: ['ADMIN', 'TI', 'MANAGER'],
      description: 'Relatórios e Análises',
      requiresApproval: false
    },
    
    'INVENTORY': {
      allowedRoles: ['ADMIN', 'TI'],
      description: 'Inventário de Equipamentos',
      requiresApproval: false
    },
    
    'PASSWORD_VAULT': {
      allowedRoles: ['ADMIN', 'TI'],
      description: 'Cofre de Senhas - Acesso restrito',
      requiresApproval: false
    },
    
    'SETTINGS': {
      allowedRoles: ['ADMIN'],
      description: 'Configurações do Sistema',
      requiresApproval: false
    },
    
    'BILLING': {
      allowedRoles: ['ADMIN', 'MANAGER'],
      description: 'Faturamento e Pagamentos',
      requiresApproval: false
    },
    
    // ================================================== 
    // PÁGINAS OPERACIONAIS - Todos os usuários
    // ==================================================
    'DASHBOARD': {
      allowedRoles: ['USER', 'RESPONSAVEL_GRUPO', 'ADMIN', 'TI', 'MANAGER'],
      description: 'Dashboard Principal',
      requiresApproval: false
    },
    
    'TICKETS': {
      allowedRoles: ['USER', 'RESPONSAVEL_GRUPO', 'ADMIN', 'TI', 'MANAGER'],
      description: 'Gerenciamento de Tickets',
      requiresApproval: false
    },
    
    'CHAT': {
      allowedRoles: ['USER', 'RESPONSAVEL_GRUPO', 'ADMIN', 'TI', 'MANAGER'],
      description: 'Chat e Comunicação',
      requiresApproval: false
    },
    
    'TASKS': {
      allowedRoles: ['USER', 'RESPONSAVEL_GRUPO', 'ADMIN', 'TI', 'MANAGER'],
      description: 'Tarefas e Projetos',
      requiresApproval: false
    },
    
    'PROJECTS': {
      allowedRoles: ['USER', 'RESPONSAVEL_GRUPO', 'ADMIN', 'TI', 'MANAGER'],
      description: 'Gerenciamento de Projetos',
      requiresApproval: false
    },
    
    'KNOWLEDGE_BASE': {
      allowedRoles: ['USER', 'RESPONSAVEL_GRUPO', 'ADMIN', 'TI', 'MANAGER'],
      description: 'Base de Conhecimento',
      requiresApproval: false
    },
    
    'DOWNLOAD_AGENTS': {
      allowedRoles: ['USER', 'RESPONSAVEL_GRUPO', 'ADMIN', 'TI', 'MANAGER'],
      description: 'Download de Agentes',
      requiresApproval: false
    },

    'PERMISSIONS': {
      allowedRoles: ['ADMIN'],
      description: 'Gerenciamento de Permissões de Acesso',
      requiresApproval: false
    }
  };
  
  // ================================================== 
  // SECTION 2: CONFIGURAÇÃO DE ACESSO A FUNCIONALIDADES
  // Data: 06/04/2026 20:15
  // ==================================================
  
  /**
   * Define quais ROLES podem executar cada FUNCIONALIDADE
   * 
   * Uma funcionalidade é uma ação dentro de uma página
   * Exemplo: Criar usuário, deletar usuário, editar grupo, etc.
   * 
   * Structure:
   * {
   *   'NOME_FUNCIONALIDADE': {
   *     allowedRoles: ['ADMIN', 'TI'],
   *     description: 'Descrição da funcionalidade',
   *     pageRequired: 'USERS'  // Página onde a funcionalidade está
   *   }
   * }
   */
  const FEATURE_ACCESS_CONFIG = {
    // ================================================== 
    // FUNCIONALIDADES - USUÁRIOS
    // ==================================================
    'CREATE_USER': {
      allowedRoles: ['ADMIN', 'TI'],
      description: 'Criar novo usuário',
      pageRequired: 'USERS'
    },
    
    'EDIT_USER': {
      allowedRoles: ['ADMIN', 'TI'],
      description: 'Editar dados de usuário',
      pageRequired: 'USERS'
    },
    
    'DELETE_USER': {
      allowedRoles: ['ADMIN'],
      description: 'Deletar usuário do sistema',
      pageRequired: 'USERS'
    },
    
    'CHANGE_USER_ROLE': {
      allowedRoles: ['ADMIN'],
      description: 'Alterar role/perfil de usuário',
      pageRequired: 'USERS'
    },
    
    'RESET_USER_PASSWORD': {
      allowedRoles: ['ADMIN', 'TI'],
      description: 'Resetar senha de usuário',
      pageRequired: 'USERS'
    },
    
    // ================================================== 
    // FUNCIONALIDADES - GRUPOS
    // ==================================================
    'CREATE_GROUP': {
      allowedRoles: ['ADMIN', 'TI', 'MANAGER'],
      description: 'Criar novo grupo/setor',
      pageRequired: 'GROUPS'
    },
    
    'EDIT_GROUP': {
      allowedRoles: ['ADMIN', 'TI', 'MANAGER'],
      description: 'Editar grupo/setor',
      pageRequired: 'GROUPS'
    },
    
    'DELETE_GROUP': {
      allowedRoles: ['ADMIN', 'TI'],
      description: 'Deletar grupo/setor',
      pageRequired: 'GROUPS'
    },
    
    // ================================================== 
    // FUNCIONALIDADES - TICKETS
    // ==================================================
    'CREATE_TICKET': {
      allowedRoles: ['USER', 'RESPONSAVEL_GRUPO', 'ADMIN', 'TI', 'MANAGER'],
      description: 'Criar novo ticket',
      pageRequired: 'TICKETS'
    },
    
    'EDIT_TICKET': {
      allowedRoles: ['ADMIN', 'TI', 'MANAGER', 'RESPONSAVEL_GRUPO'],
      description: 'Editar ticket',
      pageRequired: 'TICKETS'
    },
    
    'DELETE_TICKET': {
      allowedRoles: ['ADMIN', 'TI'],
      description: 'Deletar ticket',
      pageRequired: 'TICKETS'
    },
    
    'ASSIGN_TICKET': {
      allowedRoles: ['ADMIN', 'TI', 'MANAGER', 'RESPONSAVEL_GRUPO'],
      description: 'Atribuir ticket a responsável',
      pageRequired: 'TICKETS'
    },
    
    // Adicione mais funcionalidades conforme necessário
  };
  
  // ==================================================
  // SECTION 3: EXCEÇÕES E REGRAS ESPECIAIS
  // Data: 06/04/2026 20:15
  // NOTA: Lido dinamicamente do localStorage (gerenciado por permissions.html)
  // ==================================================

  // ==================================================
  // CACHE em memória (evita múltiplas requests por página)
  // ==================================================
  let _cachedPagePermissions = null;
  let _cachedUserExceptions  = {};   // chave: userId

  /**
   * Busca permissões de páginas da API (com cache em memória)
   * @returns {Promise<object>}  { PAGE_NAME: [roles] }
   */
  async function fetchPagePermissions() {
    if (_cachedPagePermissions) return _cachedPagePermissions;
    try {
      const res = await fetch('http://localhost:8000/api/permissions/pages');
      const data = await res.json();
      if (data.success) {
        _cachedPagePermissions = data.permissions;
        return _cachedPagePermissions;
      }
    } catch (e) {
      console.warn('[ACCESS-CONFIG] Não foi possível buscar permissões da API, usando defaults.', e);
    }
    return {};
  }

  /**
   * Busca exceções de um usuário da API (com cache em memória)
   * @param {number|string} userId
   * @returns {Promise<{blockPages: string[], allowPages: string[]}>}
   */
  async function fetchUserExceptions(userId) {
    if (_cachedUserExceptions[userId]) return _cachedUserExceptions[userId];
    try {
      const res = await fetch(`http://localhost:8000/api/permissions/exceptions/user/${userId}`);
      const data = await res.json();
      if (data.success) {
        _cachedUserExceptions[userId] = {
          blockPages: data.blockPages || [],
          allowPages: data.allowPages || []
        };
        return _cachedUserExceptions[userId];
      }
    } catch (e) {
      console.warn('[ACCESS-CONFIG] Não foi possível buscar exceções da API.', e);
    }
    return { blockPages: [], allowPages: [] };
  }

  /** Limpa o cache (chamar após salvar permissões no admin) */
  function clearPermissionsCache() {
    _cachedPagePermissions = null;
    _cachedUserExceptions  = {};
  }
  
  // ================================================== 
  // SECTION 4: FUNÇÕES AUXILIARES
  // Data: 06/04/2026 20:15
  // ==================================================
  
  /**
   * Obtém configuração de acesso a uma página
   */
  function getPageAccessConfig(pageName) {
    return PAGE_ACCESS_CONFIG[pageName] || null;
  }
  
  /**
   * Obtém configuração de acesso a uma funcionalidade
   */
  function getFeatureAccessConfig(featureName) {
    return FEATURE_ACCESS_CONFIG[featureName] || null;
  }
  
  /**
   * Verifica se usuário pode acessar página (async — consulta a API)
   * Ordem de prioridade:
   *  1. Exceção individual do banco (block → nega, allow → permite)
   *  2. Permissões do banco (page_permissions)
   *  3. Configuração padrão (PAGE_ACCESS_CONFIG hardcoded)
   *
   * @returns {Promise<boolean>}
   */
  async function canAccessPage(userRole, pageName, userId = null) {
    // STEP 1: Exceções individuais do banco
    if (userId) {
      const exc = await fetchUserExceptions(userId);

      if (exc.blockPages.includes(pageName)) {
        console.log(`[ACCESS-CONFIG] ❌ ${pageName} bloqueado para userId ${userId}`);
        return false;
      }

      if (exc.allowPages.includes(pageName)) {
        console.log(`[ACCESS-CONFIG] ✅ ${pageName} permitido por exceção para userId ${userId}`);
        return true;
      }
    }

    // STEP 2: Permissões do banco (page_permissions)
    const dbPermissions = await fetchPagePermissions();
    if (dbPermissions[pageName]) {
      console.log(`[ACCESS-CONFIG] 📋 Usando permissões do banco para ${pageName}`);
      return dbPermissions[pageName].includes(userRole);
    }

    // STEP 3: Config padrão local
    const config = getPageAccessConfig(pageName);
    if (!config) return false;

    return config.allowedRoles.includes(userRole);
  }

  /**
   * Verifica se usuário pode executar funcionalidade (síncrono, sem exceções individuais)
   */
  function canAccessFeature(userRole, featureName) {
    const config = getFeatureAccessConfig(featureName);
    if (!config) return false;
    return config.allowedRoles.includes(userRole);
  }
  
  // ================================================== 
  // [FIM] access-config.js
  // Data: 06/04/2026 20:15
  // ==================================================