/* =====================================================================
   Service Worker — CPE Control PWA
   Estrategia: minimo viavel. Sem cache offline ainda (sistema depende de
   API/WebSocket em tempo real — cache nao agrega). Aqui apenas gerencia
   push notifications e click em notif.
   ===================================================================== */

const SW_VERSION = 'cpe-sw-v2';

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

  // Tipos especiais por tag:
  //  - 'cpe-call-*'          : chamada de voz (botoes atender/rejeitar)
  //  - 'cpe-chatmention-*'   : @mention em canal (urgente, fica fixa)
  //  - 'cpe-chatdm-*'        : DM (semi-urgente, vibra mais forte)
  //  - 'cpe-chat-*'          : msg comum em canal (suave)
  const tag = data.tag || 'cpe-chat';
  const isCall    = tag.startsWith('cpe-call-');
  const isMention = tag.startsWith('cpe-chatmention-');
  const isDm      = tag.startsWith('cpe-chatdm-');

  const opts = {
    body: data.body || '',
    icon: '/SistemaCPE/web/assests/icons/icon-192.png',
    badge: '/SistemaCPE/web/assests/icons/icon-96.png',
    tag,
    data: { url: data.url || '/SistemaCPE/web/pages/chat.html', isCall },
    // Fixa na tela ate clique pra chamadas e mentions
    requireInteraction: isCall || isMention,
    vibrate:
      isCall    ? [400, 200, 400, 200, 400, 200, 400]
      : isMention ? [300, 150, 300, 150, 300]
      : isDm      ? [250, 120, 250]
      :           [200, 100, 200],
    silent: false,
    actions: isCall ? [
      { action: 'answer',  title: '📞 Atender' },
      { action: 'reject',  title: '📵 Rejeitar' },
    ] : (isMention || isDm) ? [
      { action: 'open',  title: '💬 Abrir chat' },
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
