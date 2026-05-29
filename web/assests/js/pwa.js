/* =====================================================================
   CPE Chat — PWA helper
   - Registra service worker
   - Captura 'beforeinstallprompt' pra botao "Instalar app"
   - Pede permissao e subscribe Web Push (passa VAPID public key do backend)
   - Envia subscription pro backend pra entrega quando offline
   ===================================================================== */

(function () {
  const API_BASE = (typeof window.API_BASE_URL !== 'undefined')
    ? window.API_BASE_URL
    : 'http://127.0.0.1:8000';

  function _token() {
    return localStorage.getItem('cpe_token') || sessionStorage.getItem('cpe_token') || '';
  }

  // ----- Service worker -----
  async function registerSW() {
    if (!('serviceWorker' in navigator)) return null;
    try {
      const reg = await navigator.serviceWorker.register('/SistemaCPE/web/sw.js', {
        scope: '/SistemaCPE/'
      });
      return reg;
    } catch (e) {
      console.warn('[pwa] SW register falhou', e);
      return null;
    }
  }

  // ----- Botao "Instalar app" (beforeinstallprompt) -----
  let _installPrompt = null;
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    _installPrompt = e;
    // Notifica a UI que pode mostrar botao
    window.dispatchEvent(new CustomEvent('pwa:installable'));
  });
  window.pwaInstall = async function () {
    if (!_installPrompt) {
      alert('Pra instalar, abra o menu do navegador → "Instalar app" / "Adicionar à tela inicial".');
      return false;
    }
    _installPrompt.prompt();
    const ch = await _installPrompt.userChoice.catch(() => ({ outcome: 'dismissed' }));
    _installPrompt = null;
    return ch.outcome === 'accepted';
  };
  window.pwaCanInstall = () => !!_installPrompt;

  // ----- Web Push -----
  function urlBase64ToUint8Array(b64) {
    const padding = '='.repeat((4 - b64.length % 4) % 4);
    const base64 = (b64 + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw = atob(base64);
    return Uint8Array.from(raw, c => c.charCodeAt(0));
  }

  async function getVapidPublicKey() {
    try {
      const r = await fetch(`${API_BASE}/api/chat/push/vapid-public-key`, {
        credentials: 'include',
        headers: { 'X-Auth-Token': _token() },
      });
      if (!r.ok) return null;
      const d = await r.json();
      return d.key || null;
    } catch { return null; }
  }

  window.pwaPushSubscribe = async function () {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      alert('Seu navegador não suporta push notifications.');
      return false;
    }
    if (!('Notification' in window)) return false;
    if (Notification.permission === 'denied') {
      alert('Você bloqueou notificações. Habilite no cadeado da barra de endereço.');
      return false;
    }
    if (Notification.permission === 'default') {
      const p = await Notification.requestPermission();
      if (p !== 'granted') return false;
    }
    const reg = await navigator.serviceWorker.ready;
    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      const vapid = await getVapidPublicKey();
      if (!vapid) { alert('Push notifications não estão configuradas no servidor.'); return false; }
      try {
        sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(vapid),
        });
      } catch (e) {
        console.warn('[pwa] subscribe falhou', e);
        alert('Não foi possível ativar notificações: ' + e.message);
        return false;
      }
    }
    // Envia pro backend (idempotente — UPSERT)
    try {
      await fetch(`${API_BASE}/api/chat/push/subscribe`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-Auth-Token': _token() },
        body: JSON.stringify(sub.toJSON()),
      });
      return true;
    } catch (e) {
      console.warn('[pwa] enviar sub falhou', e);
      return false;
    }
  };

  window.pwaPushUnsubscribe = async function () {
    if (!('serviceWorker' in navigator)) return;
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.getSubscription();
    if (!sub) return;
    try {
      await fetch(`${API_BASE}/api/chat/push/unsubscribe`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-Auth-Token': _token() },
        body: JSON.stringify({ endpoint: sub.endpoint }),
      });
    } catch {}
    await sub.unsubscribe().catch(() => {});
  };

  window.pwaIsSubscribed = async function () {
    if (!('serviceWorker' in navigator)) return false;
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.getSubscription();
    return !!sub;
  };

  // Auto-registra SW no boot
  registerSW();
})();
