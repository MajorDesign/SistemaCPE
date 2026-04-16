// ==================================================
// ARQUIVO: page-access-control.js
// FUNÇÃO: Validação de acesso a páginas (async — usa API)
// Data: 07/04/2026
// NOTA: Usa access-config.js
// ==================================================

/**
 * Valida se o usuário pode acessar a página.
 * Esconde a página imediatamente para evitar flash de conteúdo,
 * faz a verificação assíncrona na API e então:
 *   - redireciona se negado
 *   - exibe a página se permitido
 *
 * @param {string} pageName - ex: "USERS", "CHAT"
 */
async function checkPageAccess(pageName) {
  // Esconde a página imediatamente (evita flash de conteúdo)
  document.documentElement.style.visibility = 'hidden';

  console.log(`[PAGE-ACCESS] 🔐 Verificando acesso: ${pageName}`);

  // STEP 1: Usuário logado?
  const userStr = localStorage.getItem('cpe_user');
  if (!userStr) {
    console.error(`[PAGE-ACCESS/${pageName}] ❌ Nenhum usuário logado`);
    alert('❌ Você deve fazer login para acessar esta página!');
    window.location.href = '/SistemaCPE/web/login.html';
    return null;
  }

  // STEP 2: Parse
  let userData;
  try {
    userData = JSON.parse(userStr);
  } catch (err) {
    console.error(`[PAGE-ACCESS/${pageName}] ❌ Sessão inválida`);
    localStorage.removeItem('cpe_user');
    localStorage.removeItem('cpe_token');
    alert('❌ Sessão inválida. Faça login novamente.');
    window.location.href = '/SistemaCPE/web/login.html';
    return null;
  }

  const userRole = userData.role || 'USER';
  const userId   = userData.id;

  console.log(`[PAGE-ACCESS/${pageName}] 👤 ${userData.name} (${userRole})`);

  // STEP 3: Verificar acesso (consulta API)
  try {
    const allowed = await canAccessPage(userRole, pageName, userId);

    if (!allowed) {
      console.error(`[PAGE-ACCESS/${pageName}] ❌ ACESSO NEGADO`);
      alert(
        `❌ ACESSO NEGADO!\n\n` +
        `Sua função (${getRoleLabel(userRole)}) não tem permissão para esta página.\n\n` +
        `Você será redirecionado...`
      );
      window.location.href = '/SistemaCPE/index.html';
      return null;
    }

    // Acesso permitido — exibe a página
    console.log(`[PAGE-ACCESS/${pageName}] ✅ ACESSO PERMITIDO`);
    document.documentElement.style.visibility = 'visible';
    return userData;

  } catch (err) {
    // Falha na API — aplica regra local como fallback
    console.warn(`[PAGE-ACCESS/${pageName}] ⚠️ Falha na API, usando config local:`, err.message);

    const config = getPageAccessConfig(pageName);
    const localAllowed = config ? config.allowedRoles.includes(userRole) : false;

    if (!localAllowed) {
      alert(`❌ ACESSO NEGADO!\n\nSua função (${getRoleLabel(userRole)}) não tem permissão para esta página.`);
      window.location.href = '/SistemaCPE/index.html';
      return null;
    }

    document.documentElement.style.visibility = 'visible';
    return userData;
  }
}

/**
 * Verifica se usuário pode executar uma funcionalidade (síncrono)
 */
function canUserAccessFeature(featureName, userRole) {
  const allowed = canAccessFeature(userRole, featureName);
  if (!allowed) {
    const config = getFeatureAccessConfig(featureName);
    if (config) {
      console.warn(`[FEATURE-ACCESS] ⚠️ ${featureName} permitido apenas para: ${config.allowedRoles.join(', ')}`);
    }
  }
  return allowed;
}

/**
 * Retorna label legível do role
 */
function getRoleLabel(role) {
  const labels = {
    'USER':             '👤 Usuário Comum',
    'RESPONSAVEL_GRUPO':'👨‍💼 Responsável do Grupo',
    'ADMIN':            '🔐 Administrador',
    'TI':               '🔧 TI',
    'MANAGER':          '📊 Gerente'
  };
  return labels[role] || role;
}

// ==================================================
// [FIM] page-access-control.js
// ==================================================
