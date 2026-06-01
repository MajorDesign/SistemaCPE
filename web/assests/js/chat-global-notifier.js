/* =====================================================================
   CPE Chat — Global Notifier
   --------------------------------------------------------------------
   Roda em TODAS as paginas do sistema (exceto chat.html, que tem seu
   proprio WS) pra mostrar:
   - Toast no canto inferior direito quando recebe nova mensagem
   - Badge no icone de chat do navbar (contador de nao-lidas global)
   - Som de notificacao
   - Popup flutuante de chamada recebida com Atender / Recusar

   Reconecta automaticamente com backoff exponencial.
   ===================================================================== */
(function () {
  // Skip se estamos no chat.html — la ja tem WS proprio e UI completa
  if (location.pathname.endsWith('/chat.html')) return;

  // Skip se nao estamos numa pagina autenticada do sistema (login, etc)
  if (location.pathname.endsWith('/login.html') ||
      location.pathname.endsWith('/agendar.html')) return;

  const API_BASE = (typeof window.API_BASE_URL !== 'undefined') ? window.API_BASE_URL : '';
  const WS_BASE  = API_BASE && API_BASE.startsWith('http')
    ? API_BASE.replace(/^http/, 'ws')
    : (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host;

  let _self = null;
  let _token = '';
  let _ws = null;
  let _retryMs = 1000;
  let _unread = 0;
  let _callState = null;
  let _audioCtx = null;
  let _ringtoneInterval = null;

  function _t() {
    return localStorage.getItem('cpe_token') || sessionStorage.getItem('cpe_token') || '';
  }
  function _u() {
    try { return JSON.parse(localStorage.getItem('cpe_user') || sessionStorage.getItem('cpe_user') || '{}'); }
    catch { return {}; }
  }
  function _esc(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function _initials(name) {
    if (!name) return '?';
    const parts = name.trim().split(/\s+/);
    return ((parts[0]?.[0] || '') + (parts[parts.length-1]?.[0] || '')).toUpperCase() || '?';
  }

  /* ============ INIT ============ */
  document.addEventListener('DOMContentLoaded', () => {
    _self = _u();
    _token = _t();
    if (!_self.id || !_token) return;  // nao logado
    _injetarUI();
    _conectarWS();
    // Permissao de notif desktop — pede silenciosamente se ainda nao decidiu
    if ('Notification' in window && Notification.permission === 'default') {
      try { Notification.requestPermission().catch(() => {}); } catch {}
    }
  });

  /* ============ UI INJETADA NO BODY ============ */
  function _injetarUI() {
    if (document.getElementById('cgnStyles')) return; // ja injetado

    const css = `
      .cgn-toast-container {
        position: fixed; bottom: 18px; right: 18px;
        z-index: 9990;
        display: flex; flex-direction: column; gap: 8px;
        pointer-events: none;
      }
      .cgn-toast {
        background: #1A1A1A; color: #E5E5E5;
        border: 1px solid #353535; border-left: 3px solid #FFC107;
        border-radius: 8px;
        padding: 10px 14px;
        min-width: 260px; max-width: 360px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        display: flex; gap: 10px;
        cursor: pointer;
        pointer-events: auto;
        animation: cgnSlideIn 0.25s ease-out;
        font-family: 'Inter', system-ui, sans-serif;
      }
      .cgn-toast:hover { background: #232323; }
      .cgn-toast-avatar {
        width: 36px; height: 36px; border-radius: 50%;
        background: linear-gradient(135deg, #6366F1, #8B5CF6);
        color: #fff; display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 0.78rem; flex-shrink: 0;
      }
      .cgn-toast-body { flex: 1; min-width: 0; }
      .cgn-toast-author {
        font-weight: 600; font-size: 0.86rem; color: #fff;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      }
      .cgn-toast-msg {
        font-size: 0.8rem; color: #9CA3AF; margin-top: 2px;
        max-height: 38px; overflow: hidden;
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
      }
      @keyframes cgnSlideIn {
        from { opacity: 0; transform: translateX(20px); }
        to { opacity: 1; transform: translateX(0); }
      }
      .cgn-toast.cgn-closing {
        animation: cgnSlideOut 0.2s ease-in forwards;
      }
      @keyframes cgnSlideOut {
        to { opacity: 0; transform: translateX(20px); }
      }

      /* Popup de chamada flutuante */
      .cgn-call-overlay {
        display: none; position: fixed; inset: 0; z-index: 9995;
        background: rgba(0,0,0,0.78);
        align-items: center; justify-content: center;
        animation: cgnFade 0.15s ease-out;
      }
      .cgn-call-overlay.open { display: flex; }
      @keyframes cgnFade { from {opacity:0;} to {opacity:1;} }
      .cgn-call-box {
        background: #1A1A1A; border-radius: 16px;
        padding: 28px 36px 22px; max-width: 360px; width: 90%;
        text-align: center; border: 1px solid #353535;
        box-shadow: 0 20px 60px rgba(0,0,0,0.7);
        font-family: 'Inter', system-ui, sans-serif;
      }
      .cgn-call-status {
        font-size: 0.72rem; text-transform: uppercase;
        letter-spacing: 0.1em; color: #FFC107;
        margin-bottom: 6px; font-weight: 700;
      }
      .cgn-call-avatar {
        width: 96px; height: 96px; border-radius: 50%;
        margin: 14px auto;
        background: linear-gradient(135deg, #6366F1, #8B5CF6);
        color: #fff; font-size: 2.2rem; font-weight: 700;
        display: flex; align-items: center; justify-content: center;
        animation: cgnPulseRing 1.4s ease-out infinite;
      }
      @keyframes cgnPulseRing {
        0% { box-shadow: 0 0 0 0 rgba(255, 193, 7, 0.5); }
        70% { box-shadow: 0 0 0 20px rgba(255, 193, 7, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 193, 7, 0); }
      }
      .cgn-call-name {
        font-size: 1.2rem; font-weight: 700; color: #fff; margin-bottom: 4px;
      }
      .cgn-call-sub {
        font-size: 0.82rem; color: #9CA3AF; margin-bottom: 22px;
      }
      .cgn-call-buttons {
        display: flex; justify-content: center; gap: 24px;
      }
      .cgn-call-buttons button {
        width: 56px; height: 56px; border-radius: 50%;
        border: none; cursor: pointer; color: #fff; font-size: 1.4rem;
        display: flex; align-items: center; justify-content: center;
        transition: transform 0.1s, filter 0.1s;
      }
      .cgn-call-buttons button:hover { transform: scale(1.08); filter: brightness(1.1); }
      .cgn-btn-accept { background: #10B981; }
      .cgn-btn-reject { background: #DC2626; }
    `;
    const style = document.createElement('style');
    style.id = 'cgnStyles';
    style.textContent = css;
    document.head.appendChild(style);

    // Containers
    const toastBox = document.createElement('div');
    toastBox.className = 'cgn-toast-container';
    toastBox.id = 'cgnToastContainer';
    document.body.appendChild(toastBox);

    const callBox = document.createElement('div');
    callBox.className = 'cgn-call-overlay';
    callBox.id = 'cgnCallOverlay';
    callBox.innerHTML = `
      <div class="cgn-call-box">
        <div class="cgn-call-status">📞 CHAMADA RECEBIDA</div>
        <div class="cgn-call-avatar" id="cgnCallAvatar">?</div>
        <div class="cgn-call-name" id="cgnCallName">—</div>
        <div class="cgn-call-sub">Toque pra atender</div>
        <div class="cgn-call-buttons">
          <button class="cgn-btn-reject" onclick="window._cgnAtender(false)" title="Rejeitar">
            <i class="bi bi-telephone-x-fill"></i>
          </button>
          <button class="cgn-btn-accept" onclick="window._cgnAtender(true)" title="Atender">
            <i class="bi bi-telephone-fill"></i>
          </button>
        </div>
      </div>
    `;
    document.body.appendChild(callBox);
  }

  /* ============ WEBSOCKET ============ */
  function _conectarWS() {
    if (!_token) return;
    const url = `${WS_BASE}/api/chat/ws?token=${encodeURIComponent(_token)}`;
    try {
      _ws = new WebSocket(url);
    } catch (e) {
      console.warn('[CGN] WS init fail', e);
      return;
    }
    _ws.addEventListener('open', () => {
      console.log('[CGN] conectado');
      _retryMs = 1000;
    });
    _ws.addEventListener('message', (ev) => {
      let data; try { data = JSON.parse(ev.data); } catch { return; }
      _onWsEvent(data);
    });
    _ws.addEventListener('close', () => {
      setTimeout(_conectarWS, _retryMs);
      _retryMs = Math.min(_retryMs * 2, 30000);
    });
    _ws.addEventListener('error', () => { try { _ws.close(); } catch {} });
  }

  function _onWsEvent(data) {
    if (data.type === 'message') {
      _onMensagemNova(data);
    } else if (data.type === 'call_invite') {
      _onChamadaRecebida(data);
    } else if (data.type === 'call_cancel') {
      _fecharPopupChamada();
    } else if (data.type === 'notification_new') {
      // Notificacao persistente (sino) — forca refresh imediato
      if (typeof window.loadNotifications === 'function') {
        try { window.loadNotifications(); } catch {}
      }
    }
  }

  /* ============ MENSAGEM NOVA → toast + badge + som + notif desktop ============ */
  function _onMensagemNova(m) {
    if (m.author?.id === _self.id) return;  // nao notifica msg propria
    _unread++;
    _atualizarBadge();
    _tocarBip();
    const meMencionou = Array.isArray(m.mentions) && m.mentions.includes(_self.id);
    _mostrarToast(m, meMencionou);
    // Forca refresh do sino se houver mention (backend criou notif persistente)
    if (meMencionou && typeof window.loadNotifications === 'function') {
      try { window.loadNotifications(); } catch {}
    }
    // Notif desktop nativa quando aba esta em background (escondida)
    // Pra mention SEMPRE; pra outras msgs so se tab nao esta visivel
    _notifDesktop(m, meMencionou);
  }

  /* ============ Notification API (desktop) ============ */
  function _notifDesktop(m, meMencionou) {
    if (!('Notification' in window)) return;
    if (Notification.permission !== 'granted') return;
    // So mostra se aba nao esta focada/visivel ou se eh mention (sempre)
    if (document.hasFocus() && !document.hidden && !meMencionou) return;
    try {
      const corpo = (m.content || '').slice(0, 160) ||
        (m.attachments?.length ? '📷 enviou uma imagem' : '');
      const tit = meMencionou
        ? `🔔 ${m.author?.name || 'Alguém'} te mencionou`
        : (m.author?.name || 'Nova mensagem');
      const n = new Notification(tit, {
        body: corpo,
        icon: '/SistemaCPE/web/assests/icons/icon-192.png',
        tag: `cpe-chat-${m.channel_id || 'msg'}`,
        requireInteraction: !!meMencionou,
      });
      n.onclick = () => {
        try { window.focus(); } catch {}
        try { n.close(); } catch {}
        window.location.href = '/SistemaCPE/web/pages/chat.html';
      };
    } catch { /* ignore */ }
  }

  function _atualizarBadge() {
    const badge = document.getElementById('chatNotifyBadge');
    if (!badge) return;
    if (_unread > 0) {
      badge.textContent = _unread > 99 ? '99+' : _unread;
      badge.style.display = 'flex';
    } else {
      badge.style.display = 'none';
    }
  }

  function _mostrarToast(m, mencionado) {
    const box = document.getElementById('cgnToastContainer');
    if (!box) return;
    const toast = document.createElement('div');
    toast.className = 'cgn-toast';
    if (mencionado) {
      toast.style.borderLeftColor = '#EF4444';
      toast.style.borderLeftWidth = '4px';
    }
    const tag = mencionado
      ? '<span style="background:#EF4444;color:#fff;font-size:0.62rem;font-weight:700;'
        + 'padding:1px 6px;border-radius:8px;margin-right:6px;text-transform:uppercase">'
        + '@menção</span>'
      : '';
    toast.innerHTML = `
      <div class="cgn-toast-avatar">${_esc(_initials(m.author?.name))}</div>
      <div class="cgn-toast-body">
        <div class="cgn-toast-author">${tag}${_esc(m.author?.name || 'Usuário')}</div>
        <div class="cgn-toast-msg">${_esc((m.content || '').slice(0, 140) ||
          (m.attachments?.length ? '📷 Enviou uma imagem' : ''))}</div>
      </div>
    `;
    toast.onclick = () => {
      window.location.href = '/SistemaCPE/web/pages/chat.html';
    };
    box.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('cgn-closing');
      setTimeout(() => toast.remove(), 200);
    }, mencionado ? 8000 : 5000);
  }

  /* ============ SOM (Web Audio bip duplo) ============ */
  function _tocarBip() {
    try {
      if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const ctx = _audioCtx;
      if (ctx.state === 'suspended') ctx.resume();
      const bip = (freq, when, dur, vol) => {
        const osc = ctx.createOscillator();
        const g = ctx.createGain();
        osc.type = 'sine'; osc.frequency.value = freq;
        g.gain.setValueAtTime(0, ctx.currentTime + when);
        g.gain.linearRampToValueAtTime(vol, ctx.currentTime + when + 0.01);
        g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + when + dur);
        osc.connect(g); g.connect(ctx.destination);
        osc.start(ctx.currentTime + when);
        osc.stop(ctx.currentTime + when + dur + 0.02);
      };
      bip(880, 0, 0.12, 0.18);
      bip(1100, 0.10, 0.12, 0.18);
    } catch (e) { /* sem som */ }
  }

  /* ============ CHAMADA RECEBIDA → popup + ringtone + notif desktop ============ */
  function _onChamadaRecebida(data) {
    if (_callState) return; // ja em outra
    _callState = data;
    document.getElementById('cgnCallAvatar').textContent =
      _initials(data.from_user_name);
    document.getElementById('cgnCallName').textContent =
      data.from_user_name || 'Usuário';
    document.getElementById('cgnCallOverlay').classList.add('open');
    _tocarRingtone();
    _notifDesktopChamada(data);
  }

  /* Notif desktop nativa de chamada via Service Worker.
     Usa SW.showNotification() pra suportar actions Atender/Rejeitar
     mesmo se a aba estiver minimizada. Tag igual ao push do PWA pra
     que NAO duplique a notif caso ambas cheguem juntas. */
  async function _notifDesktopChamada(data) {
    if (!('Notification' in window)) return;
    if (Notification.permission !== 'granted') return;
    try {
      const reg = await (navigator.serviceWorker?.ready);
      if (!reg || !reg.showNotification) return;
      const from = data.from_user_id;
      await reg.showNotification(`📞 ${data.from_user_name || 'Alguém'} está te ligando`, {
        body: 'Toque pra atender',
        icon: '/SistemaCPE/web/assests/icons/icon-192.png',
        badge: '/SistemaCPE/web/assests/icons/icon-96.png',
        tag: `cpe-call-${from}`,        // mesma tag do push do backend → substitui (sem duplicar)
        requireInteraction: true,        // fica fixa ate user agir
        vibrate: [400, 200, 400, 200, 400, 200, 400],
        actions: [
          { action: 'answer', title: '📞 Atender' },
          { action: 'reject', title: '📵 Rejeitar' },
        ],
        data: {
          url: `/SistemaCPE/web/pages/chat.html?incoming_call=${from}`,
          isCall: true,
        },
        renotify: true,
      });
    } catch (e) {
      // fallback: Notification simples sem actions (algum browser sem SW)
      try {
        const from = data.from_user_id;
        const n = new Notification(`📞 ${data.from_user_name || 'Alguém'} está te ligando`, {
          body: 'Clique pra atender',
          icon: '/SistemaCPE/web/assests/icons/icon-192.png',
          tag: `cpe-call-${from}`,
          requireInteraction: true,
        });
        n.onclick = () => {
          try { window.focus(); } catch {}
          try { n.close(); } catch {}
          window.location.href = `/SistemaCPE/web/pages/chat.html?incoming_call=${from}&auto_answer=1`;
        };
      } catch {}
    }
  }

  /* Fecha notif desktop quando call_cancel ou usuario respondeu */
  async function _fecharNotifChamada(fromUserId) {
    try {
      const reg = await (navigator.serviceWorker?.ready);
      if (!reg || !reg.getNotifications) return;
      const tag = `cpe-call-${fromUserId}`;
      const notifs = await reg.getNotifications({ tag });
      notifs.forEach(n => { try { n.close(); } catch {} });
    } catch {}
  }

  function _tocarRingtone() {
    _pararRingtone();
    try {
      if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const ctx = _audioCtx;
      if (ctx.state === 'suspended') ctx.resume();
      const tocar = () => {
        const bip = (freq, when, dur) => {
          const osc = ctx.createOscillator();
          const g = ctx.createGain();
          osc.type = 'sine'; osc.frequency.value = freq;
          g.gain.setValueAtTime(0, ctx.currentTime + when);
          g.gain.linearRampToValueAtTime(0.25, ctx.currentTime + when + 0.02);
          g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + when + dur);
          osc.connect(g); g.connect(ctx.destination);
          osc.start(ctx.currentTime + when);
          osc.stop(ctx.currentTime + when + dur + 0.02);
        };
        bip(880, 0, 0.4);
        bip(880, 0.5, 0.4);
      };
      tocar();
      _ringtoneInterval = setInterval(tocar, 1800);
    } catch {}
  }

  function _pararRingtone() {
    if (_ringtoneInterval) { clearInterval(_ringtoneInterval); _ringtoneInterval = null; }
  }

  function _fecharPopupChamada() {
    const fromId = _callState?.from_user_id;
    document.getElementById('cgnCallOverlay')?.classList.remove('open');
    _pararRingtone();
    _callState = null;
    if (fromId) _fecharNotifChamada(fromId);
  }

  /* ============ ATENDER / REJEITAR ============ */
  window._cgnAtender = function (accept) {
    if (!_callState) return;
    if (accept) {
      const from = _callState.from_user_id;
      _fecharPopupChamada();
      // Redireciona pro chat com flag pra auto-atender
      window.location.href =
        `/SistemaCPE/web/pages/chat.html?incoming_call=${from}&auto_answer=1`;
    } else {
      try {
        _ws?.send(JSON.stringify({
          type: 'call_reject',
          to_user_id: _callState.from_user_id,
        }));
      } catch {}
      _fecharPopupChamada();
    }
  };

  // Esc rejeita
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && _callState) window._cgnAtender(false);
  });
})();
