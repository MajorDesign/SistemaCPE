// ===== INÍCIO: config.js (Configuração Global) =====

// =========================================
// Configuração Base da API
// =========================================
//
// Detecta automaticamente o host do servidor:
// - Em desenvolvimento (localhost): API_BASE_URL = http://localhost:8000
// - Em produção (http://172.16.0.10:1509/...): API_BASE_URL = http://172.16.0.10:8000
// - Funciona em qualquer IP/domínio sem precisar alterar código.
//
// A API FastAPI roda SEMPRE na porta 8000. Se um dia mudar a porta,
// altere a constante API_PORT abaixo e faça git pull.
// =========================================

const API_PORT = 8000;

const _apiHost = (typeof window !== 'undefined' && window.location && window.location.hostname)
  ? window.location.hostname
  : '127.0.0.1';

const API_BASE_URL = `http://${_apiHost}:${API_PORT}`;

const SESSION_COOKIE_NAME = "cpe_session";
const COOKIE_NAME = "cpe_session";

console.log("[CONFIG] ✓ Configurações carregadas");
console.log("[CONFIG] API_BASE_URL:", API_BASE_URL);
console.log("[CONFIG] SESSION_COOKIE_NAME:", SESSION_COOKIE_NAME);

// ===== FIM: config.js (Configuração Global) =====
