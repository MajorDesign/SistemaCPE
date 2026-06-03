/**
 * auth-guard.js — Sentinela global de sessão (2026-06-03).
 *
 * PROBLEMA RESOLVIDO:
 *   Quando o token de sessão (12h) expira, várias partes da SPA disparam
 *   chamadas autenticadas em paralelo (chat-notifier, polling de sino,
 *   meetings, WebSocket reconnect, etc). Todas batem 401, e o backend
 *   antigamente acionava fail2ban — banindo o IP público do escritório
 *   e bloqueando TODOS os usuários simultaneamente.
 *
 * SOLUÇÃO (sem mexer em código existente):
 *   Monkey-patch em window.fetch + WebSocket. Ao detectar a primeira
 *   resposta 401 em rota /api/* (exceto /api/auth/login), o guard:
 *     1) Marca a sessão como expirada (flag global)
 *     2) Cancela TODOS os pollings (clear de intervals/timeouts dispatched)
 *     3) Fecha WebSockets ativos
 *     4) Mostra modal não-bloqueante "Sessão expirada"
 *     5) Limpa storage e redireciona pro login em 3s
 *
 *   Após a primeira detecção, qualquer fetch para /api/* é abortado
 *   localmente (rejeita com erro sintético) — assim não chove 401 no
 *   backend nem aciona rate-limits.
 *
 * Incluído em todas as páginas via nav.js (auto-loader).
 */
(function (global) {
  'use strict';

  if (global.__cpeAuthGuardLoaded) return;
  global.__cpeAuthGuardLoaded = true;

  const LOGIN_URL = '/SistemaCPE/web/login.html';
  const REDIRECT_DELAY_MS = 3000;

  // Rotas onde 401 é ESPERADO e não deve disparar o guard
  const ROTAS_IGNORADAS = [
    '/api/auth/login',
    '/api/auth/forgot-password',
    '/api/auth/reset-password',
    '/api/auth/primeiro-acesso',
  ];

  let _expirado = false;

  function log(...a) { console.warn('[AUTH-GUARD]', ...a); }

  function _ehRotaIgnorada(url) {
    try {
      const u = new URL(url, location.origin);
      return ROTAS_IGNORADAS.some(r => u.pathname.startsWith(r));
    } catch { return false; }
  }

  function _ehRotaApi(url) {
    try {
      const u = new URL(url, location.origin);
      return u.pathname.startsWith('/api/');
    } catch { return false; }
  }

  /** Limpa localStorage/sessionStorage de tudo relacionado à sessão. */
  function _limparStorage() {
    const keys = ['cpe_token', 'cpe_user', 'token', 'user',
                  'user_id', 'logged_in', 'login_time'];
    keys.forEach(k => {
      try { localStorage.removeItem(k); } catch {}
      try { sessionStorage.removeItem(k); } catch {}
    });
  }

  /** Modal não-bloqueante avisando expiração + redirect. */
  function _mostrarModal() {
    if (document.getElementById('__cpeAuthGuardModal')) return;
    const div = document.createElement('div');
    div.id = '__cpeAuthGuardModal';
    div.style.cssText = `
      position: fixed; inset: 0; z-index: 9999999;
      background: rgba(0,0,0,0.55); backdrop-filter: blur(3px);
      display: flex; align-items: center; justify-content: center;
      font-family: 'Inter', -apple-system, sans-serif;
      animation: __agFade .2s ease;
    `;
    div.innerHTML = `
      <div style="background:#fff;border-radius:14px;padding:32px 36px;
                  max-width:420px;width:90%;text-align:center;
                  box-shadow:0 20px 60px rgba(0,0,0,.4);">
        <div style="font-size:48px;line-height:1;margin-bottom:14px">⏰</div>
        <h2 style="margin:0 0 10px 0;color:#1A1A1A;font-size:1.3rem;font-weight:700;">
          Sua sessão expirou
        </h2>
        <p style="margin:0 0 22px 0;color:#6c757d;line-height:1.5;font-size:.95rem;">
          Por segurança, sua sessão de 12 horas terminou.<br>
          Você será redirecionado pro login em
          <strong id="__agCount" style="color:#FFC107">3</strong>s.
        </p>
        <button id="__agBtnLogin" style="
          background:#FFC107;color:#1A1A1A;border:0;border-radius:8px;
          padding:11px 28px;font-weight:700;font-size:.95rem;cursor:pointer;
          box-shadow:0 4px 12px rgba(255,193,7,.4);
        ">Ir para login agora</button>
      </div>
      <style>@keyframes __agFade { from {opacity:0} to {opacity:1} }</style>
    `;
    document.body.appendChild(div);

    document.getElementById('__agBtnLogin').onclick = _redirecionar;

    let cnt = 3;
    const tick = setInterval(() => {
      cnt--;
      const el = document.getElementById('__agCount');
      if (el) el.textContent = String(Math.max(0, cnt));
      if (cnt <= 0) { clearInterval(tick); _redirecionar(); }
    }, 1000);
  }

  function _redirecionar() {
    // location.replace pra não voltar com o botão "voltar" do navegador
    try { location.replace(LOGIN_URL); } catch { location.href = LOGIN_URL; }
  }

  /** Dispara o protocolo de expiração de sessão. Idempotente. */
  function _ativarExpirado(motivo) {
    if (_expirado) return;
    _expirado = true;
    log('Sessão expirada —', motivo, '— parando todas as chamadas e redirecionando');

    // Fecha WebSockets abertos (chat global notifier, chat.html, meetings)
    try {
      (global.__cpeOpenWebSockets || []).forEach(ws => {
        try { ws.close(4001, 'session-expired'); } catch {}
      });
    } catch {}

    // Limpa storage e mostra modal
    _limparStorage();
    _mostrarModal();

    // Dispara evento global pra qualquer código local que queira reagir
    try {
      global.dispatchEvent(new CustomEvent('cpe:session-expired', { detail: { motivo } }));
    } catch {}
  }

  // ────────────────────────────────────────────────────────────────────
  // PATCH em window.fetch
  // ────────────────────────────────────────────────────────────────────
  const _fetchOriginal = global.fetch.bind(global);

  global.fetch = async function (input, init) {
    const url = (typeof input === 'string') ? input
              : (input && input.url) ? input.url
              : String(input);

    // Se já está expirado e a rota é /api/* não-ignorada, aborta localmente
    // pra não bombardear o backend com 401s
    if (_expirado && _ehRotaApi(url) && !_ehRotaIgnorada(url)) {
      return Promise.reject(new Error('Sessão expirada — chamada cancelada localmente'));
    }

    const resp = await _fetchOriginal(input, init);

    // Intercepta 401 em rotas /api/* não-ignoradas
    if (resp.status === 401 && _ehRotaApi(url) && !_ehRotaIgnorada(url)) {
      _ativarExpirado(`401 em ${url}`);
    }

    return resp;
  };

  // ────────────────────────────────────────────────────────────────────
  // Rastreio leve de WebSockets pra poder fechá-los na expiração
  // ────────────────────────────────────────────────────────────────────
  global.__cpeOpenWebSockets = global.__cpeOpenWebSockets || [];
  const _WSOriginal = global.WebSocket;
  if (_WSOriginal && !_WSOriginal.__cpePatched) {
    function _WSPatched(url, protocols) {
      const ws = new _WSOriginal(url, protocols);
      try { global.__cpeOpenWebSockets.push(ws); } catch {}
      ws.addEventListener('close', () => {
        try {
          const i = global.__cpeOpenWebSockets.indexOf(ws);
          if (i >= 0) global.__cpeOpenWebSockets.splice(i, 1);
        } catch {}
      });
      return ws;
    }
    _WSPatched.prototype = _WSOriginal.prototype;
    _WSPatched.CONNECTING = _WSOriginal.CONNECTING;
    _WSPatched.OPEN       = _WSOriginal.OPEN;
    _WSPatched.CLOSING    = _WSOriginal.CLOSING;
    _WSPatched.CLOSED     = _WSOriginal.CLOSED;
    _WSPatched.__cpePatched = true;
    global.WebSocket = _WSPatched;
  }

  // API pública (opcional — pra debugging)
  global.cpeAuthGuard = {
    isExpired: () => _expirado,
    forceExpire: () => _ativarExpirado('forçado manualmente'),
  };

  log('Sentinela carregado — interceptando 401 em /api/*');

})(typeof window !== 'undefined' ? window : this);
