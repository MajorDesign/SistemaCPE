// ===== INÍCIO: config.js (Configuração Global) =====

// =========================================
// Configuração Base da API
// =========================================
//
// Em produção: API na porta 8000 (cpe_plus).
// Em dev local: pode alternar entre porta 8000 (dev) e 8001 (staging)
// via seletor na tela de login. A escolha é salva em localStorage.
// =========================================

const _API_ENVS = {
  dev:     { port: 8000, label: 'Dev',     db: 'cpe_plus' },
  staging: { port: 8001, label: 'Staging', db: 'cpe_plus_staging' },
};

const _isLocalhost = typeof window !== 'undefined' &&
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

// Em produção força sempre dev (porta 8000)
const _savedEnv = _isLocalhost
  ? ((typeof localStorage !== 'undefined' && localStorage.getItem('cpe_env')) || 'dev')
  : 'dev';

const API_ENV  = _savedEnv in _API_ENVS ? _savedEnv : 'dev';
const API_PORT = _API_ENVS[API_ENV].port;

const _curHost = (typeof window !== 'undefined' && window.location && window.location.hostname)
  ? window.location.hostname
  : '127.0.0.1';

// Quando rodando atrás de domínio público (Cloudflare Tunnel),
// a API fica em api.<dominio> via HTTPS — sem porta explícita.
// Em dev/staging local, segue a regra de host+porta.
const _isPublicDomain = /^(?:www\.)?[\w-]+\.[\w]{2,}/.test(_curHost) && _curHost !== 'localhost';

const API_BASE_URL = _isPublicDomain
  ? `${window.location.protocol}//api.${_curHost.replace(/^www\./, '')}`
  : `http://${_curHost}:${API_PORT}`;

if (typeof window !== 'undefined') {
  window.API_BASE_URL = API_BASE_URL;
  window.API_ENV      = API_ENV;
  window._API_ENVS    = _API_ENVS;
}

const SESSION_COOKIE_NAME = "cpe_session";
const COOKIE_NAME = "cpe_session";

console.log(`[CONFIG] Ambiente: ${API_ENV} | API: ${API_BASE_URL}`);

// ===== FIM: config.js (Configuração Global) =====
