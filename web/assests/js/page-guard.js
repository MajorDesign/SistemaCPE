/**
 * page-guard.js — Guard único de página (refatoração 2026-05-05).
 *
 * Substitui em um arquivo só:
 *   - route-protection.js (autenticação)
 *   - access-config.js + page-access-control.js + role-permissions.js (autorização)
 *
 * USO:
 *   <script src="/SistemaCPE/web/assests/js/config.js"></script>
 *   <script src="/SistemaCPE/web/assests/js/page-guard.js"></script>
 *   <script>pageGuard('AGENDA');</script>
 *
 * O guard:
 *   1) Verifica que existe token + dados do usuário no storage
 *      Se não, redireciona pra login.
 *   2) Chama GET /api/permissions/check?page=X&user_id=Y (lógica canônica
 *      no backend: ADMIN sempre passa → exceções vencem → role OU grupo libera)
 *   3) Se permitido: dispara `authenticationSuccess` (compat com código
 *      existente) e libera a página.
 *   4) Se negado: mostra mensagem e redireciona pro dashboard.
 *
 * API EXPORTADA (window.pageGuard):
 *   pageGuard(pageKey)        - inicia o guard pra uma página
 *   pageGuard.getUser()       - retorna o usuário logado (ou null)
 *   pageGuard.authHeaders()   - { 'Content-Type', 'Authorization': Bearer ... }
 *   pageGuard.logout()        - limpa storage e vai pro login
 */

// ════════════════════════════════════════════════════════════════════
// AUTH-GUARD INLINE — sentinela global de sessão (2026-06-03).
//
// Está INLINE dentro do page-guard.js (em vez de arquivo separado) para
// garantir que o monkey-patch de window.fetch e WebSocket aconteça ANTES
// do primeiro fetch — qualquer assincronia (script src + load) abriria
// uma janela de corrida onde 401 vazaria pro backend.
//
// Detalhes: web/assests/js/auth-guard.js (fonte canônica, mesma lógica).
// ════════════════════════════════════════════════════════════════════
(function (global) {
  if (global.__cpeAuthGuardLoaded) return;
  global.__cpeAuthGuardLoaded = true;

  const LOGIN_URL = '/SistemaCPE/web/login.html';
  const ROTAS_IGNORADAS = [
    '/api/auth/login', '/api/auth/forgot-password',
    '/api/auth/reset-password', '/api/auth/primeiro-acesso',
  ];
  let _expirado = false;

  function _ehRotaIgnorada(url) {
    try { return ROTAS_IGNORADAS.some(r => new URL(url, location.origin).pathname.startsWith(r)); }
    catch { return false; }
  }
  function _ehRotaApi(url) {
    try { return new URL(url, location.origin).pathname.startsWith('/api/'); }
    catch { return false; }
  }
  function _limparStorage() {
    ['cpe_token','cpe_user','token','user','user_id','logged_in','login_time']
      .forEach(k => { try{localStorage.removeItem(k);}catch{} try{sessionStorage.removeItem(k);}catch{} });
  }
  function _mostrarModal() {
    if (document.getElementById('__cpeAuthGuardModal')) return;
    const div = document.createElement('div');
    div.id = '__cpeAuthGuardModal';
    div.style.cssText = 'position:fixed;inset:0;z-index:9999999;background:rgba(0,0,0,.55);backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center;font-family:Inter,-apple-system,sans-serif';
    div.innerHTML = `
      <div style="background:#fff;border-radius:14px;padding:32px 36px;max-width:420px;width:90%;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.4)">
        <div style="font-size:48px;line-height:1;margin-bottom:14px">⏰</div>
        <h2 style="margin:0 0 10px;color:#1A1A1A;font-size:1.3rem;font-weight:700">Sua sessão expirou</h2>
        <p style="margin:0 0 22px;color:#6c757d;line-height:1.5;font-size:.95rem">
          Por segurança, sua sessão de 12 horas terminou.<br>
          Você será redirecionado pro login em <strong id="__agCount" style="color:#FFC107">3</strong>s.
        </p>
        <button id="__agBtnLogin" style="background:#FFC107;color:#1A1A1A;border:0;border-radius:8px;padding:11px 28px;font-weight:700;font-size:.95rem;cursor:pointer;box-shadow:0 4px 12px rgba(255,193,7,.4)">Ir para login agora</button>
      </div>`;
    document.body.appendChild(div);
    const ir = () => { try{location.replace(LOGIN_URL);}catch{location.href=LOGIN_URL;} };
    document.getElementById('__agBtnLogin').onclick = ir;
    let c = 3;
    const t = setInterval(() => {
      c--; const e = document.getElementById('__agCount'); if (e) e.textContent = String(Math.max(0,c));
      if (c<=0) { clearInterval(t); ir(); }
    }, 1000);
  }
  function _ativarExpirado(motivo) {
    if (_expirado) return;
    _expirado = true;
    console.warn('[AUTH-GUARD] Sessão expirada —', motivo);
    try { (global.__cpeOpenWebSockets||[]).forEach(ws => { try{ws.close(4001,'session-expired');}catch{} }); } catch {}
    _limparStorage();
    if (document.body) _mostrarModal();
    else document.addEventListener('DOMContentLoaded', _mostrarModal, { once: true });
    try { global.dispatchEvent(new CustomEvent('cpe:session-expired', { detail: { motivo } })); } catch {}
  }

  // Helper interno pra ler o token com fallback de chaves legadas.
  function _readTokenLocal() {
    try {
      return localStorage.getItem('cpe_token')
          || sessionStorage.getItem('cpe_token')
          || localStorage.getItem('token')
          || sessionStorage.getItem('token')
          || '';
    } catch (_) { return ''; }
  }

  // Patch window.fetch
  // 2026-08-24: agora tambem INJETA auth (X-Auth-Token + Authorization Bearer)
  // + credentials:'include' em toda chamada pra /api/*. Antes, paginas antigas
  // que faziam fetch direto sem enviar token davam 401 em ambientes onde front
  // e API sao origens diferentes (staging local: front porta 80, API porta 8001)
  // — o cookie de sessao nao viaja entre origens. Agora funciona em qualquer
  // ambiente sem precisar tocar em cada pagina.
  const _fOriginal = global.fetch.bind(global);
  global.fetch = async function (input, init) {
    const url = (typeof input === 'string') ? input : (input && input.url) ? input.url : String(input);
    if (_expirado && _ehRotaApi(url) && !_ehRotaIgnorada(url)) {
      return Promise.reject(new Error('Sessão expirada — chamada cancelada'));
    }
    // Injeta auth em rotas da API que ainda nao tem
    if (_ehRotaApi(url) && !_ehRotaIgnorada(url)) {
      const tk = _readTokenLocal();
      init = init || {};
      if (!('credentials' in init)) init.credentials = 'include';
      const h = new Headers(init.headers || {});
      if (tk && !h.has('X-Auth-Token')) h.set('X-Auth-Token', tk);
      if (tk && !h.has('Authorization'))  h.set('Authorization', 'Bearer ' + tk);
      init.headers = h;
    }
    const resp = await _fOriginal(input, init);
    if (resp.status === 401 && _ehRotaApi(url) && !_ehRotaIgnorada(url)) {
      _ativarExpirado(`401 em ${url}`);
    }
    return resp;
  };

  // Rastreio leve de WebSockets pra fechar na expiração
  global.__cpeOpenWebSockets = global.__cpeOpenWebSockets || [];
  const _WS = global.WebSocket;
  if (_WS && !_WS.__cpePatched) {
    function _WSp(url, protocols) {
      const ws = new _WS(url, protocols);
      try { global.__cpeOpenWebSockets.push(ws); } catch {}
      ws.addEventListener('close', () => {
        try { const i = global.__cpeOpenWebSockets.indexOf(ws); if (i>=0) global.__cpeOpenWebSockets.splice(i,1); } catch {}
      });
      return ws;
    }
    _WSp.prototype = _WS.prototype;
    _WSp.CONNECTING = _WS.CONNECTING; _WSp.OPEN = _WS.OPEN;
    _WSp.CLOSING = _WS.CLOSING; _WSp.CLOSED = _WS.CLOSED;
    _WSp.__cpePatched = true;
    global.WebSocket = _WSp;
  }

  global.cpeAuthGuard = {
    isExpired: () => _expirado,
    forceExpire: () => _ativarExpirado('forçado manualmente'),
  };
  console.log('[AUTH-GUARD] Sentinela ativo — 401 em /api/* dispara redirect pra login');
})(typeof window !== 'undefined' ? window : this);

(function (global) {
  'use strict';

  // ────────────────────────────────────────────────────────────────────
  // CONFIG
  // ────────────────────────────────────────────────────────────────────
  const CFG = {
    loginUrl:     '/SistemaCPE/web/login.html',
    dashboardUrl: '/SistemaCPE/index.html',
    apiBaseFallback: () => `http://${location.hostname || '127.0.0.1'}:8000`,
    storageKeys: {
      // Chaves novas (preferenciais)
      user:  'cpe_user',
      token: 'cpe_token',
      // Chaves legadas (compatibilidade durante a migração)
      userLegacy:  'user',
      tokenLegacy: 'token',
    },
    log: true,
  };

  function log(...args) { if (CFG.log) console.log('[PAGE-GUARD]', ...args); }
  function err(...args) { console.error('[PAGE-GUARD]', ...args); }

  // ────────────────────────────────────────────────────────────────────
  // STORAGE — busca em localStorage E sessionStorage, novo E legado
  // ────────────────────────────────────────────────────────────────────
  function readStorage(key) {
    return localStorage.getItem(key) || sessionStorage.getItem(key);
  }

  function getToken() {
    return readStorage(CFG.storageKeys.token)
        || readStorage(CFG.storageKeys.tokenLegacy)
        || '';
  }

  function getUser() {
    const raw = readStorage(CFG.storageKeys.user) || readStorage(CFG.storageKeys.userLegacy);
    if (!raw) return null;
    try {
      const u = JSON.parse(raw);
      if (u && u.id && u.email && u.role) return u;
    } catch (_) { /* corrupto */ }
    return null;
  }

  function clearStorage() {
    Object.values(CFG.storageKeys).forEach(k => {
      localStorage.removeItem(k);
      sessionStorage.removeItem(k);
    });
    localStorage.removeItem('user_id');
    localStorage.removeItem('logged_in');
    localStorage.removeItem('login_time');
  }

  function getApiBase() {
    return (typeof global.API_BASE_URL !== 'undefined')
      ? global.API_BASE_URL
      : CFG.apiBaseFallback();
  }

  function authHeaders() {
    const t = getToken();
    return t
      ? { 'Content-Type': 'application/json', 'Authorization': `Bearer ${t}` }
      : { 'Content-Type': 'application/json' };
  }

  // ────────────────────────────────────────────────────────────────────
  // UI — overlay de loading e mensagem de bloqueio
  // ────────────────────────────────────────────────────────────────────
  function ensureOverlay() {
    if (document.getElementById('__pgGuardOverlay')) return;
    const div = document.createElement('div');
    div.id = '__pgGuardOverlay';
    div.style.cssText = `
      position: fixed; inset: 0;
      background: rgba(255,255,255,.96);
      backdrop-filter: blur(2px);
      z-index: 999999;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      font-family: 'Inter', -apple-system, sans-serif;
    `;
    div.innerHTML = `
      <div style="width:48px;height:48px;border:4px solid #FFC107;border-top-color:transparent;border-radius:50%;animation:__pgSpin .9s linear infinite;"></div>
      <div id="__pgGuardMsg" style="margin-top:18px;color:#374151;font-size:14px;font-weight:500;">Validando acesso...</div>
      <style>@keyframes __pgSpin { to { transform: rotate(360deg); } }</style>
    `;
    document.documentElement.appendChild(div);
  }

  function setOverlayMessage(text, isError) {
    const msg = document.getElementById('__pgGuardMsg');
    if (msg) {
      msg.textContent = text;
      msg.style.color = isError ? '#DC2626' : '#374151';
    }
  }

  function removeOverlay() {
    const o = document.getElementById('__pgGuardOverlay');
    if (o) o.remove();
  }

  function redirectToLogin(reason) {
    log('Redirecionando para login:', reason || '(sem motivo)');
    sessionStorage.setItem('redirectAfterLogin', location.pathname + location.search);
    location.replace(CFG.loginUrl);
  }

  function redirectToDashboard(reason) {
    log('Redirecionando para dashboard:', reason || '(sem motivo)');
    setOverlayMessage(reason || 'Acesso negado', true);
    setTimeout(() => location.replace(CFG.dashboardUrl), 1800);
  }

  // ────────────────────────────────────────────────────────────────────
  // EVENTO de compat — algumas páginas escutam `authenticationSuccess`
  // ────────────────────────────────────────────────────────────────────
  let dispatched = false;
  function dispatchAuthSuccess(user) {
    if (dispatched) return;
    dispatched = true;
    document.dispatchEvent(new CustomEvent('authenticationSuccess', { detail: { user } }));
    log('Evento authenticationSuccess despachado');
  }

  // ────────────────────────────────────────────────────────────────────
  // GUARD PRINCIPAL
  // ────────────────────────────────────────────────────────────────────
  async function pageGuard(pageKey) {
    if (!pageKey) {
      err('pageGuard: page key obrigatória, ex: pageGuard("AGENDA")');
      return;
    }

    ensureOverlay();

    // 1) Autenticação
    const user  = getUser();
    const token = getToken();
    if (!user || !token) {
      redirectToLogin('Sem token ou usuário');
      return;
    }

    log(`Verificando acesso de ${user.name} (${user.role}) à página ${pageKey}`);

    // 2) Autorização via API canônica
    try {
      const url = `${getApiBase()}/api/permissions/check?page=${encodeURIComponent(pageKey)}&user_id=${user.id}`;
      const resp = await fetch(url, { headers: authHeaders() });

      if (!resp.ok) {
        // API com problema — fallback conservador: assume permitido p/ não travar
        // o sistema todo se a API estiver lenta/indisponível. Logamos pra investigar.
        err('API de permissões falhou (HTTP ' + resp.status + ') — liberando por fallback.');
        liberar(user);
        return;
      }

      const data = await resp.json();
      if (data && data.allowed) {
        log('✅ Permitido —', data.reason);
        liberar(user);
      } else {
        log('❌ Negado —', data && data.reason);
        redirectToDashboard(`Acesso negado: ${(data && data.reason) || 'sem permissão'}`);
      }

    } catch (e) {
      err('Erro de rede ao validar permissão:', e);
      // Mesmo fallback: libera com warning. Garante que usuário consegue
      // operar mesmo se o serviço de permissões estiver fora do ar.
      liberar(user);
    }
  }

  function liberar(user) {
    removeOverlay();
    dispatchAuthSuccess(user);
  }

  // ────────────────────────────────────────────────────────────────────
  // API PÚBLICA
  // ────────────────────────────────────────────────────────────────────
  pageGuard.getUser      = getUser;
  pageGuard.getToken     = getToken;
  pageGuard.authHeaders  = authHeaders;
  pageGuard.logout = function () {
    clearStorage();
    location.replace(CFG.loginUrl);
  };

  global.pageGuard = pageGuard;

})(typeof window !== 'undefined' ? window : this);
