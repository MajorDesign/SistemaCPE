/* =====================================================================
   CPE Chat — Voice/Video room (WebRTC mesh P2P)
   --------------------------------------------------------------------
   - Cada participante abre 1 RTCPeerConnection com cada outro peer
     (mesh full N²). Funciona ate ~5 pessoas; degrada acima disso.
   - Signaling pelo WebSocket existente: voice_offer / voice_answer /
     voice_ice (1-a-1 entre peer_ids) e voice_join / voice_leave / voice_state
     (broadcast pros membros do canal).
   - Servidor STUN: Google publico (gratis). Sem TURN — funciona na
     mesma rede ou Internet sem CGNAT pesado.
   - Suporta: voz, video, screen share. Toggle dinamico via replaceTrack.
   ===================================================================== */
(function () {
  const STUN_SERVERS = [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' },
  ];

  // Estado global do modulo
  window._voiceState = {
    canalId: null,
    myPeerId: null,
    localStream: null,
    screenStream: null,
    peers: new Map(),   // peer_id -> { user_id, name, pc, audioEl, videoEl, screenEl }
    micOn: true,
    camOn: false,
    shareOn: false,
  };

  function _rid() {
    // peer_id curto
    return Math.random().toString(36).slice(2, 12) + Date.now().toString(36);
  }

  function _wsSend(msg) {
    if (window._ws && window._ws.readyState === WebSocket.OPEN) {
      window._ws.send(JSON.stringify(msg));
    }
  }

  /* =================================================================
     Entrar / sair de canal de voz
     ================================================================= */
  window.voiceEntrar = async function (channelId) {
    const st = window._voiceState;
    if (st.canalId === channelId) return;        // ja conectado
    if (st.canalId) await window.voiceSair();    // sai do anterior primeiro

    // 1) Captura mic (sem camera — usuario liga depois se quiser)
    let local;
    try {
      local = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
        video: false,
      });
    } catch (e) {
      alert('Não foi possível acessar o microfone: ' + e.message);
      return;
    }
    st.localStream = local;
    st.canalId = channelId;
    st.myPeerId = _rid();
    st.micOn = true; st.camOn = false; st.shareOn = false;

    // 2) Informa backend que entrei + recebe lista de peers existentes
    let resp;
    try {
      resp = await window._chatApiCall('POST', `/channels/${channelId}/voice/join`,
        { peer_id: st.myPeerId });
    } catch (e) {
      alert('Erro ao entrar na sala: ' + e.message);
      _cleanup();
      return;
    }
    const existingPeers = resp.peers || [];

    // 3) Cria peer connection com cada um (eu sou o initiator)
    for (const p of existingPeers) {
      _connectToPeer(p, /* initiator */ true);
    }

    _renderVoiceRoom();
    _setHeaderLeaveBtn(true);
  };

  window.voiceSair = async function () {
    const st = window._voiceState;
    if (!st.canalId) return;
    try {
      await window._chatApiCall('POST', `/channels/${st.canalId}/voice/leave`);
    } catch {}
    _cleanup();
    _renderVoiceRoom();
    _setHeaderLeaveBtn(false);
  };

  function _cleanup() {
    const st = window._voiceState;
    for (const p of st.peers.values()) {
      try { p.pc.close(); } catch {}
    }
    st.peers.clear();
    if (st.localStream) {
      st.localStream.getTracks().forEach(t => t.stop());
    }
    if (st.screenStream) {
      st.screenStream.getTracks().forEach(t => t.stop());
    }
    st.localStream = null;
    st.screenStream = null;
    st.canalId = null;
    st.myPeerId = null;
    st.micOn = true;
    st.camOn = false;
    st.shareOn = false;
  }

  /* =================================================================
     Peer connection: cria, adiciona tracks, gerencia ICE/SDP
     ================================================================= */
  function _connectToPeer(peerInfo, initiator) {
    const st = window._voiceState;
    if (st.peers.has(peerInfo.peer_id)) return;
    const pc = new RTCPeerConnection({ iceServers: STUN_SERVERS });
    const entry = {
      user_id: peerInfo.user_id,
      name: peerInfo.name || `Usuário #${peerInfo.user_id}`,
      mic_on: !!peerInfo.mic_on, cam_on: !!peerInfo.cam_on, share_on: !!peerInfo.share_on,
      pc, peer_id: peerInfo.peer_id,
    };
    st.peers.set(peerInfo.peer_id, entry);

    // Adiciona meus tracks atuais
    if (st.localStream) {
      for (const t of st.localStream.getTracks()) {
        pc.addTrack(t, st.localStream);
      }
    }
    if (st.screenStream) {
      for (const t of st.screenStream.getTracks()) {
        pc.addTrack(t, st.screenStream);
      }
    }

    // ICE — manda candidatos pro outro lado via WS
    pc.onicecandidate = (ev) => {
      if (ev.candidate) {
        _wsSend({
          type: 'voice_ice',
          to_user_id: peerInfo.user_id,
          to_peer_id: peerInfo.peer_id,
          from_peer_id: st.myPeerId,
          candidate: ev.candidate.toJSON(),
        });
      }
    };

    // Quando peer envia midia
    pc.ontrack = (ev) => {
      _onRemoteTrack(peerInfo.peer_id, ev);
    };

    pc.onconnectionstatechange = () => {
      if (['failed', 'closed', 'disconnected'].includes(pc.connectionState)) {
        // peer caiu — limpa elementos visuais
        const e = st.peers.get(peerInfo.peer_id);
        if (e) {
          [e.audioEl, e.videoEl, e.screenEl].forEach(el => el?.remove());
        }
      }
      _renderVoiceRoom();
    };

    if (initiator) {
      // Manda offer
      pc.createOffer().then(offer => pc.setLocalDescription(offer)).then(() => {
        _wsSend({
          type: 'voice_offer',
          to_user_id: peerInfo.user_id,
          to_peer_id: peerInfo.peer_id,
          from_peer_id: st.myPeerId,
          sdp: pc.localDescription,
        });
      }).catch(err => console.error('[voice] createOffer fail', err));
    }
  }

  function _onRemoteTrack(peer_id, ev) {
    const st = window._voiceState;
    const entry = st.peers.get(peer_id);
    if (!entry) return;
    const stream = ev.streams[0];
    if (!stream) return;
    const track = ev.track;
    if (track.kind === 'audio') {
      let el = entry.audioEl;
      if (!el) {
        el = document.createElement('audio');
        el.autoplay = true;
        el.playsInline = true;
        document.body.appendChild(el);
        entry.audioEl = el;
      }
      el.srcObject = stream;
    } else if (track.kind === 'video') {
      // Pode ser camera OU tela; render dentro do card do peer
      _aplicarVideoNoCard(peer_id, stream);
    }
    _renderVoiceRoom();
  }

  /* =================================================================
     Handlers de signaling vindos do WebSocket (chamados pelo chat.html)
     ================================================================= */
  window.onVoiceSignal = function (data) {
    const st = window._voiceState;
    if (!st.canalId) return;
    if (data.type === 'voice_join') {
      // Outro user entrou. Nao crio peer pra mim mesmo.
      if (data.peer_id === st.myPeerId) return;
      // Eu NAO sou o initiator (o newcomer envia offers pros existing — ja
      // tratado em voiceEntrar). Aqui so registro pra UI. A oferta vira logo.
      return;
    }
    if (data.type === 'voice_leave') {
      const entry = [...st.peers.values()].find(p => p.user_id === data.user_id);
      if (entry) {
        try { entry.pc.close(); } catch {}
        [entry.audioEl, entry.videoEl, entry.screenEl].forEach(el => el?.remove());
        st.peers.delete(entry.peer_id);
      }
      _renderVoiceRoom();
      return;
    }
    if (data.type === 'voice_state') {
      const entry = [...st.peers.values()].find(p => p.user_id === data.user_id);
      if (entry) {
        entry.mic_on = data.mic_on; entry.cam_on = data.cam_on; entry.share_on = data.share_on;
        _renderVoiceRoom();
      }
      return;
    }
    if (data.type === 'voice_offer') {
      // Recebi uma offer — sou o callee. Cria peer connection se nao tem.
      let entry = st.peers.get(data.from_peer_id);
      if (!entry) {
        _connectToPeer({
          peer_id: data.from_peer_id,
          user_id: data.from_user_id,
          name: null,
        }, /* initiator */ false);
        entry = st.peers.get(data.from_peer_id);
      }
      entry.pc.setRemoteDescription(new RTCSessionDescription(data.sdp))
        .then(() => entry.pc.createAnswer())
        .then(answer => entry.pc.setLocalDescription(answer))
        .then(() => {
          _wsSend({
            type: 'voice_answer',
            to_user_id: data.from_user_id,
            to_peer_id: data.from_peer_id,
            from_peer_id: st.myPeerId,
            sdp: entry.pc.localDescription,
          });
        }).catch(err => console.error('[voice] answer fail', err));
      return;
    }
    if (data.type === 'voice_answer') {
      const entry = st.peers.get(data.from_peer_id);
      if (!entry) return;
      entry.pc.setRemoteDescription(new RTCSessionDescription(data.sdp))
        .catch(err => console.error('[voice] setRemoteDesc(answer) fail', err));
      return;
    }
    if (data.type === 'voice_ice') {
      const entry = st.peers.get(data.from_peer_id);
      if (!entry) return;
      entry.pc.addIceCandidate(new RTCIceCandidate(data.candidate))
        .catch(err => console.warn('[voice] addIceCandidate fail', err));
      return;
    }
  };

  /* =================================================================
     Toggles: mic, cam, screen
     ================================================================= */
  window.voiceToggleMic = function () {
    const st = window._voiceState;
    if (!st.localStream) return;
    st.micOn = !st.micOn;
    st.localStream.getAudioTracks().forEach(t => t.enabled = st.micOn);
    _wsSend({ type: 'voice_state', channel_id: st.canalId,
              mic_on: st.micOn, cam_on: st.camOn, share_on: st.shareOn });
    _renderVoiceRoom();
  };

  window.voiceToggleCam = async function () {
    const st = window._voiceState;
    if (!st.localStream) return;
    if (st.camOn) {
      // Desliga camera
      st.localStream.getVideoTracks().forEach(t => { t.stop(); st.localStream.removeTrack(t); });
      // Tira dos peer connections
      for (const p of st.peers.values()) {
        const sender = p.pc.getSenders().find(s => s.track && s.track.kind === 'video');
        if (sender) p.pc.removeTrack(sender);
      }
      st.camOn = false;
    } else {
      try {
        const camStream = await navigator.mediaDevices.getUserMedia({ video: true });
        const track = camStream.getVideoTracks()[0];
        st.localStream.addTrack(track);
        // Adiciona em todos os peers
        for (const p of st.peers.values()) {
          p.pc.addTrack(track, st.localStream);
          // Renegocia (precisa reoffer pra novo media line)
          _renegociar(p);
        }
        st.camOn = true;
      } catch (e) {
        alert('Câmera: ' + e.message);
        return;
      }
    }
    _wsSend({ type: 'voice_state', channel_id: st.canalId,
              mic_on: st.micOn, cam_on: st.camOn, share_on: st.shareOn });
    _renderVoiceRoom();
  };

  window.voiceToggleShare = async function () {
    const st = window._voiceState;
    if (!st.canalId) return;
    if (st.shareOn) {
      st.screenStream?.getTracks().forEach(t => { t.stop(); });
      // Remove dos peers
      for (const p of st.peers.values()) {
        const senders = p.pc.getSenders().filter(s => s.track && s.track.kind === 'video' &&
                                                       s.track.label?.toLowerCase().includes('screen'));
        senders.forEach(s => p.pc.removeTrack(s));
      }
      st.screenStream = null;
      st.shareOn = false;
    } else {
      try {
        const screen = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
        st.screenStream = screen;
        const track = screen.getVideoTracks()[0];
        for (const p of st.peers.values()) {
          p.pc.addTrack(track, screen);
          _renegociar(p);
        }
        // Se user fechar do navegador
        track.onended = () => { window.voiceToggleShare(); };
        st.shareOn = true;
      } catch (e) {
        if (e.name !== 'NotAllowedError') alert('Compartilhar tela: ' + e.message);
        return;
      }
    }
    _wsSend({ type: 'voice_state', channel_id: st.canalId,
              mic_on: st.micOn, cam_on: st.camOn, share_on: st.shareOn });
    _renderVoiceRoom();
  };

  async function _renegociar(peerEntry) {
    try {
      const offer = await peerEntry.pc.createOffer();
      await peerEntry.pc.setLocalDescription(offer);
      _wsSend({
        type: 'voice_offer',
        to_user_id: peerEntry.user_id,
        to_peer_id: peerEntry.peer_id,
        from_peer_id: window._voiceState.myPeerId,
        sdp: peerEntry.pc.localDescription,
      });
    } catch (e) { console.error('[voice] renegocia fail', e); }
  }

  /* =================================================================
     UI da sala
     ================================================================= */
  function _aplicarVideoNoCard(peer_id, stream) {
    const card = document.querySelector(`.voice-peer-card[data-peer="${peer_id}"]`);
    if (!card) return;
    let v = card.querySelector('video');
    if (!v) {
      v = document.createElement('video');
      v.autoplay = true; v.playsInline = true; v.muted = false;
      card.appendChild(v);
    }
    v.srcObject = stream;
  }

  function _renderVoiceRoom() {
    const st = window._voiceState;
    const box = document.getElementById('chatVoiceRoom');
    if (!box) return;
    if (!st.canalId) {
      box.style.display = 'none';
      return;
    }
    box.style.display = '';
    const peers = [...st.peers.values()];
    // Card self primeiro
    const myCard = `<div class="voice-peer-card self" data-peer="${st.myPeerId}">
      <div class="avatar-big">${_escVoice(_initialsVoice(window._self?.name))}</div>
      <div class="peer-name">Você</div>
      <div class="peer-flags">
        ${st.micOn ? '<i class="bi bi-mic-fill" style="color:#10B981"></i>' : '<i class="bi bi-mic-mute-fill" style="color:#EF4444"></i>'}
        ${st.camOn ? '<i class="bi bi-camera-video-fill" style="color:#3B82F6"></i>' : ''}
        ${st.shareOn ? '<i class="bi bi-display-fill" style="color:#A855F7"></i>' : ''}
      </div>
    </div>`;
    const peerCards = peers.map(p => `<div class="voice-peer-card" data-peer="${_escVoice(p.peer_id)}">
      <div class="avatar-big">${_escVoice(_initialsVoice(p.name))}</div>
      <div class="peer-name">${_escVoice(p.name || 'Usuário')}</div>
      <div class="peer-flags">
        ${p.mic_on ? '<i class="bi bi-mic-fill" style="color:#10B981"></i>' : '<i class="bi bi-mic-mute-fill" style="color:#EF4444"></i>'}
        ${p.cam_on ? '<i class="bi bi-camera-video-fill" style="color:#3B82F6"></i>' : ''}
        ${p.share_on ? '<i class="bi bi-display-fill" style="color:#A855F7"></i>' : ''}
      </div>
    </div>`).join('');
    box.innerHTML = `
      <div class="voice-room-header">
        <i class="bi bi-volume-up-fill"></i> Conectado · ${peers.length + 1} ${peers.length === 0 ? 'pessoa (só você)' : 'pessoas'}
      </div>
      <div class="voice-peers-grid">${myCard}${peerCards}</div>
      <div class="voice-controls">
        <button class="${st.micOn ? '' : 'off'}" onclick="voiceToggleMic()" title="${st.micOn ? 'Mutar' : 'Desmutar'}">
          <i class="bi ${st.micOn ? 'bi-mic-fill' : 'bi-mic-mute-fill'}"></i>
        </button>
        <button class="${st.camOn ? 'active' : ''}" onclick="voiceToggleCam()" title="${st.camOn ? 'Desligar câmera' : 'Ligar câmera'}">
          <i class="bi ${st.camOn ? 'bi-camera-video-fill' : 'bi-camera-video-off-fill'}"></i>
        </button>
        <button class="${st.shareOn ? 'active' : ''}" onclick="voiceToggleShare()" title="${st.shareOn ? 'Parar de compartilhar' : 'Compartilhar tela'}">
          <i class="bi bi-display-fill"></i>
        </button>
        <button class="danger" onclick="voiceSair()" title="Sair da chamada">
          <i class="bi bi-telephone-x-fill"></i>
        </button>
      </div>
    `;
    // Tenta reaplicar streams visuais
    for (const p of peers) {
      const remoteStreams = new Set();
      p.pc.getReceivers().forEach(r => {
        if (r.track && r.track.kind === 'video') {
          // Streams nao sao acessiveis diretamente do receiver em todos os browsers
        }
      });
    }
  }

  function _setHeaderLeaveBtn(connected) {
    // Toggle visual do botao "Entrar" / "Sair" no header do canal
    const btn = document.getElementById('voiceJoinLeaveBtn');
    if (!btn) return;
    if (connected) {
      btn.innerHTML = '<i class="bi bi-telephone-x-fill"></i> Sair da chamada';
      btn.classList.add('connected');
    } else {
      btn.innerHTML = '<i class="bi bi-telephone-fill"></i> Entrar na chamada';
      btn.classList.remove('connected');
    }
  }

  function _escVoice(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function _initialsVoice(name) {
    if (!name) return '?';
    const parts = name.trim().split(/\s+/);
    return ((parts[0]?.[0] || '') + (parts[parts.length-1]?.[0] || '')).toUpperCase() || '?';
  }
})();
