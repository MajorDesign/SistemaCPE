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
  const opts = {
    body: data.body || '',
    icon: '/SistemaCPE/web/assests/icons/icon-192.png',
    badge: '/SistemaCPE/web/assests/icons/icon-96.png',
    tag: data.tag || 'cpe-chat',
    data: data.url ? { url: data.url } : {},
    requireInteraction: false,
  };
  ev.waitUntil(self.registration.showNotification(title, opts));
});

self.addEventListener('notificationclick', (ev) => {
  ev.notification.close();
  const url = ev.notification.data?.url || '/SistemaCPE/web/pages/chat.html';
  ev.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    // Procura uma janela ja aberta do sistema e foca/navega
    for (const c of all) {
      if (c.url.includes('/SistemaCPE/')) {
        await c.focus();
        if (c.url !== url && 'navigate' in c) {
          try { await c.navigate(url); } catch {}
        }
        return;
      }
    }
    // Senao, abre nova
    if (self.clients.openWindow) await self.clients.openWindow(url);
  })());
});
