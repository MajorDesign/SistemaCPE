/* =====================================================================
   Service Worker — CPE Control PWA
   Estrategia: minimo viavel. Sem cache offline ainda (sistema depende de
   API/WebSocket em tempo real — cache nao agrega). Aqui apenas gerencia
   push notifications e click em notif.
   ===================================================================== */

const SW_VERSION = 'cpe-sw-v1';

self.addEventListener('install', (ev) => {
  // ativa imediatamente sem esperar refresh
  self.skipWaiting();
});

self.addEventListener('activate', (ev) => {
  ev.waitUntil(self.clients.claim());
});

/* ----- Push notifications ----- */
self.addEventListener('push', (ev) => {
  if (!ev.data) return;
  let data = {};
  try { data = ev.data.json(); } catch { data = { title: 'CPE', body: ev.data.text() }; }
  const title = data.title || 'CPE Chat';

  // Chamada recebida (tag começa com 'cpe-call-') tem tratamento especial:
  // requireInteraction fixa a notif na tela ate user agir, vibracao mais
  // forte, e 2 botoes (Atender / Rejeitar) que abrem o sistema na acao certa.
  const isCall = (data.tag || '').startsWith('cpe-call-');
  const opts = {
    body: data.body || '',
    icon: '/SistemaCPE/web/assests/icons/icon-192.png',
    badge: '/SistemaCPE/web/assests/icons/icon-96.png',
    tag: data.tag || 'cpe-chat',
    data: { url: data.url || '/SistemaCPE/web/pages/chat.html', isCall },
    requireInteraction: isCall,
    vibrate: isCall ? [400, 200, 400, 200, 400, 200, 400] : [200, 100, 200],
    silent: false,
    actions: isCall ? [
      { action: 'answer',  title: '📞 Atender' },
      { action: 'reject',  title: '📵 Rejeitar' },
    ] : [],
  };
  ev.waitUntil(self.registration.showNotification(title, opts));
});

self.addEventListener('notificationclick', (ev) => {
  ev.notification.close();
  const dataUrl = ev.notification.data?.url || '/SistemaCPE/web/pages/chat.html';
  const isCall  = !!ev.notification.data?.isCall;
  const action  = ev.action;   // 'answer' | 'reject' | '' (click no corpo)

  // Decide URL final conforme acao
  let url = dataUrl;
  if (isCall) {
    // dataUrl ja vem com ?incoming_call=USER_ID. Adiciona auto_answer ou auto_reject
    if (action === 'answer') url += (url.includes('?') ? '&' : '?') + 'auto_answer=1';
    if (action === 'reject') url += (url.includes('?') ? '&' : '?') + 'auto_reject=1';
  }

  ev.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const c of all) {
      if (c.url.includes('/SistemaCPE/')) {
        await c.focus();
        // Se a janela ja esta no chat.html, posta mensagem pra ele agir sem reload
        if (c.url.includes('/chat.html')) {
          try {
            c.postMessage({ type: 'incoming_call_action', action: action || 'open', url });
            return;
          } catch {}
        }
        if (c.url !== url && 'navigate' in c) {
          try { await c.navigate(url); } catch {}
        }
        return;
      }
    }
    if (self.clients.openWindow) await self.clients.openWindow(url);
  })());
});
