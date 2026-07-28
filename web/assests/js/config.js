// ===== INÍCIO: config.js (Configuração Global) =====
//
// Em produção: API na porta 8000 (cpe_plus).
// Em dev local: pode alternar entre porta 8000 (dev) e 8001 (staging)
// via seletor na tela de login. A escolha é salva em localStorage.
//
// IMPORTANTE: usamos `var` (não `const`/`let`) para as globais de
// compatibilidade. Se algum HTML incluir config.js duas vezes (acontece
// em algumas páginas), `var` permite re-declarar sem SyntaxError.
// E o IIFE abaixo evita recalcular tudo na segunda execução.

var API_BASE_URL;
var API_ENV;
var SESSION_COOKIE_NAME;
var COOKIE_NAME;

(function () {
  if (typeof window !== 'undefined' && window.__CPE_CONFIG_LOADED__) return;
  if (typeof window !== 'undefined') window.__CPE_CONFIG_LOADED__ = true;

  const API_ENVS = {
    dev:     { port: 8000, label: 'Dev',     db: 'cpe_plus' },
    staging: { port: 8001, label: 'Staging', db: 'cpe_plus_staging' },
  };

  const curHost = (typeof window !== 'undefined' && window.location && window.location.hostname)
    ? window.location.hostname
    : '127.0.0.1';

  const isLocalhost    = curHost === 'localhost' || curHost === '127.0.0.1';
  const isIp           = /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(curHost);
  const isPublicDomain = !isIp && !isLocalhost && /[a-z]/i.test(curHost) && curHost.includes('.');

  // Seletor Dev/Staging só vale em localhost. Fora disso, sempre dev (porta 8000).
  // Prioridade em localhost:
  //   1. ?env=staging|dev na URL (necessário pra links compartilhados entre
  //      abas anônimas que não herdam localStorage)
  //   2. localStorage.cpe_env (escolha manual do usuário no login)
  //   3. 'dev' (default)
  let urlEnv = null;
  if (isLocalhost && typeof window !== 'undefined' && window.location && window.location.search) {
    try {
      const p = new URLSearchParams(window.location.search).get('env');
      if (p && (p in API_ENVS)) urlEnv = p;
    } catch (_) { /* ignora URL malformada */ }
  }
  const savedEnv = isLocalhost
    ? (urlEnv
       || (typeof localStorage !== 'undefined' && localStorage.getItem('cpe_env'))
       || 'dev')
    : 'dev';
  // Se veio via URL, persiste pro localStorage — assim recarregar/navegar
  // pra outras páginas do sistema mantém o ambiente.
  if (urlEnv && typeof localStorage !== 'undefined') {
    try { localStorage.setItem('cpe_env', urlEnv); } catch (_) {}
  }

  const apiEnv  = (savedEnv in API_ENVS) ? savedEnv : 'dev';
  const apiPort = API_ENVS[apiEnv].port;

  // Em dominio publico: same-origin. Caddy (atras do Cloudflare Tunnel) faz /api/* -> 8000.
  // Em IP/localhost: chama API direto na porta dela.
  const apiBaseUrl = isPublicDomain
    ? ''
    : `http://${curHost}:${apiPort}`;

  // Globais (var no escopo global)
  API_BASE_URL        = apiBaseUrl;
  API_ENV             = apiEnv;
  SESSION_COOKIE_NAME = 'cpe_session';
  COOKIE_NAME         = 'cpe_session';

  // Espelho em window.* para módulos que preferem essa forma
  if (typeof window !== 'undefined') {
    window.API_BASE_URL        = API_BASE_URL;
    window.API_ENV             = API_ENV;
    window._API_ENVS           = API_ENVS;
    window.SESSION_COOKIE_NAME = SESSION_COOKIE_NAME;
    window.COOKIE_NAME         = COOKIE_NAME;
  }

  console.log(`[CONFIG] Ambiente: ${apiEnv} | API: ${apiBaseUrl || '(same-origin)'}`);
})();

// ===== FIM: config.js (Configuração Global) =====
