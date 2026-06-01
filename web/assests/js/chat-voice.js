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

    // 1) Tenta capturar mic. Se o user escolheu dispositivo especifico em
    //    Configuracoes -> Voz e video, usa ele; senao 'audio: true' simples
    //    deixa o browser escolher o PADRAO do sistema.
    let local = null;
    let micDisponivel = true;
    const savedMicId = localStorage.getItem('cpe_chat_micId') || '';
    const audioConstraints = savedMicId
      ? { deviceId: { exact: savedMicId } }
      : true;
    try {
      local = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints, video: false });
    } catch (e) {
      micDisponivel = false;
      const nome = e.name || '';
      let msg;
      if (nome === 'NotFoundError' || nome === 'OverconstrainedError') {
        msg = 'Nenhum microfone encontrado neste dispositivo.';
      } else if (nome === 'NotAllowedError' || nome === 'PermissionDeniedError') {
        msg = 'Você bloqueou o acesso ao microfone. Libere nas configurações do navegador (cadeado da barra de endereço).';
      } else if (nome === 'NotReadableError') {
        msg = 'Microfone ocupado por outro aplicativo. Feche Zoom, Meet, Teams etc.';
      } else {
        msg = (e.message || 'Erro desconhecido') + ' (' + nome + ')';
      }
      const ok = confirm(`${msg}\n\nDeseja entrar mesmo assim como "só escuta"? Você vai conseguir ouvir os outros, mas não vai poder falar.`);
      if (!ok) return;
      // Cria stream vazio só pra ter o objeto (sem tracks de audio)
      local = new MediaStream();
    }
    st.localStream = local;
    st.canalId = channelId;
    st.myPeerId = _rid();
    st.micOn = micDisponivel;
    st.camOn = false;
    st.shareOn = false;

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
    console.log('[VOICE] entrei na sala', { channelId, myPeerId: st.myPeerId,
      existingPeers, micDisponivel });

    // 3) Cria peer connection com cada um (eu sou o initiator)
    for (const p of existingPeers) {
      console.log('[VOICE] criando peer connection (initiator) com', p);
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
      // Aplica speaker selecionado em Configuracoes (se browser suportar setSinkId)
      const speakerId = localStorage.getItem('cpe_chat_speakerId') || '';
      if (speakerId && typeof el.setSinkId === 'function') {
        el.setSinkId(speakerId).catch(() => {});
      }
    } else if (track.kind === 'video') {
      // Pode ser camera OU tela. Cada stream remoto vira um <video> no card.
      if (!entry.remoteStreams) entry.remoteStreams = new Map();
      entry.remoteStreams.set(stream.id, stream);
      // Quando o sender remove o track, removemos da UI
      track.onended = () => {
        entry.remoteStreams?.delete(stream.id);
        _renderVoiceRoom();
      };
      stream.onremovetrack = () => {
        if (stream.getVideoTracks().length === 0) {
          entry.remoteStreams?.delete(stream.id);
          _renderVoiceRoom();
        }
      };
    }
    _renderVoiceRoom();
  }

  /* =================================================================
     Handlers de signaling vindos do WebSocket (chamados pelo chat.html)
     ================================================================= */
  window.onVoiceSignal = function (data) {
    const st = window._voiceState;
    console.log('[VOICE] WS event:', data.type, data);
    if (!st.canalId) {
      console.warn('[VOICE] ignorando — nao estou em sala');
      return;
    }
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
      // Desliga camera — para o track e remove dos peers
      const camTracks = st.localStream.getVideoTracks().filter(t => !_ehTrackDeTela(t));
      camTracks.forEach(t => { t.stop(); st.localStream.removeTrack(t); });
      for (const p of st.peers.values()) {
        const sender = p.pc.getSenders().find(s => s.track && s.track.kind === 'video'
                                                    && !_ehTrackDeTela(s.track));
        if (sender) { try { p.pc.removeTrack(sender); } catch {} }
        _renegociar(p);
      }
      st.camOn = false;
    } else {
      const savedCamId = localStorage.getItem('cpe_chat_camId') || '';
      const videoConstraints = savedCamId
        ? { deviceId: { exact: savedCamId } }
        : true;
      let camStream;
      try {
        camStream = await navigator.mediaDevices.getUserMedia({ video: videoConstraints, audio: false });
      } catch (e) {
        const nome = e.name || '';
        let msg;
        if (nome === 'NotFoundError' || nome === 'OverconstrainedError') {
          msg = 'Nenhuma câmera encontrada. Conecte uma webcam.';
        } else if (nome === 'NotAllowedError' || nome === 'PermissionDeniedError') {
          msg = 'Acesso à câmera bloqueado. Libere nas permissões do site (cadeado da barra de endereço).';
        } else if (nome === 'NotReadableError') {
          msg = 'Câmera ocupada por outro aplicativo. Feche Zoom/Meet/Teams/OBS.';
        } else {
          msg = (e.message || 'Erro desconhecido') + ' (' + nome + ')';
        }
        alert('📷 Câmera: ' + msg);
        console.error('[voice] getUserMedia(video) fail', e);
        return;
      }
      const track = camStream.getVideoTracks()[0];
      st.localStream.addTrack(track);
      for (const p of st.peers.values()) {
        p.pc.addTrack(track, st.localStream);
        _renegociar(p);
      }
      // Se outro app tomar a camera (driver fail/desconexao USB)
      track.onended = () => {
        console.warn('[voice] track de camera terminou inesperadamente');
        if (st.camOn) window.voiceToggleCam();
      };
      st.camOn = true;
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
      // Remove track de tela dos peers (identificada por _ehTrackDeTela ou
      // pelo stream id ser o do screenStream antigo)
      for (const p of st.peers.values()) {
        const senders = p.pc.getSenders().filter(s => s.track && s.track.kind === 'video'
                                                       && _ehTrackDeTela(s.track));
        senders.forEach(s => { try { p.pc.removeTrack(s); } catch {} });
        _renegociar(p);
      }
      st.screenStream = null;
      st.shareOn = false;
    } else {
      // getDisplayMedia requer secure context (HTTPS) OU localhost
      if (!window.isSecureContext) {
        alert('🖥️ Compartilhar tela requer HTTPS ou localhost.\n' +
              'Acesso atual: ' + location.origin);
        return;
      }
      if (!navigator.mediaDevices?.getDisplayMedia) {
        alert('🖥️ Seu navegador não suporta compartilhar tela. Use Chrome/Edge/Firefox atualizados.');
        return;
      }
      let screen;
      try {
        screen = await navigator.mediaDevices.getDisplayMedia({
          video: { cursor: 'always' },
          audio: false,
        });
      } catch (e) {
        if (e.name === 'NotAllowedError') {
          // Usuario cancelou o seletor — silencioso
          console.log('[voice] usuario cancelou seletor de tela');
        } else {
          alert('🖥️ Compartilhar tela: ' + (e.message || e.name));
          console.error('[voice] getDisplayMedia fail', e);
        }
        return;
      }
      st.screenStream = screen;
      const track = screen.getVideoTracks()[0];
      for (const p of st.peers.values()) {
        p.pc.addTrack(track, screen);
        _renegociar(p);
      }
      // Se user clicar "Parar de compartilhar" no botao do browser
      track.onended = () => {
        console.log('[voice] tela parou de compartilhar (botao do browser)');
        if (st.shareOn) window.voiceToggleShare();
      };
      st.shareOn = true;
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

  // Cria ou reaproveita um <video> dentro do card. Diferencia por data-key
  // (1 video por stream — assim camera + screen share coexistem).
  function _ensureVideo(card, key, stream, muted) {
    if (!card || !stream) return null;
    let v = card.querySelector(`video[data-vkey="${key}"]`);
    if (!v) {
      v = document.createElement('video');
      v.autoplay = true; v.playsInline = true;
      v.muted = !!muted;
      v.dataset.vkey = key;
      card.appendChild(v);
    }
    if (v.srcObject !== stream) v.srcObject = stream;
    return v;
  }

  // Heuristica pra distinguir track da camera vs screen share
  // (label da screen costuma conter "screen" / "display" / "window" / "tab")
  function _ehTrackDeTela(track) {
    return /screen|display|window|tab|monitor/i.test(track.label || '');
  }

  // Aplica os videos LOCAIS (camera + screen share) dentro do card "Voce".
  // Sempre `muted` pra nao gerar feedback de audio.
  function _aplicarVideosLocais() {
    const st = window._voiceState;
    const card = document.querySelector('.voice-peer-card.self');
    if (!card) return;
    // Camera local
    if (st.camOn && st.localStream) {
      const camTrack = st.localStream.getVideoTracks().find(t => !_ehTrackDeTela(t));
      if (camTrack) {
        const camStream = new MediaStream([camTrack]);
        _ensureVideo(card, 'local-cam', camStream, true);
      }
    } else {
      card.querySelector('video[data-vkey="local-cam"]')?.remove();
    }
    // Screen share local
    if (st.shareOn && st.screenStream && st.screenStream.getVideoTracks().length) {
      _ensureVideo(card, 'local-screen', st.screenStream, true);
    } else {
      card.querySelector('video[data-vkey="local-screen"]')?.remove();
    }
    _ajustarLayoutVideosNoCard(card);
  }

  // Aplica videos REMOTOS de cada peer (camera + screen) usando os streams
  // armazenados em peer.remoteStreams.
  function _aplicarVideosRemotos() {
    const st = window._voiceState;
    for (const peer of st.peers.values()) {
      const card = document.querySelector(
        `.voice-peer-card[data-peer="${CSS.escape(peer.peer_id)}"]`);
      if (!card) continue;
      const streamsExistentes = peer.remoteStreams || new Map();
      // Remove videos cujo stream ja nao existe mais
      card.querySelectorAll('video[data-vkey^="remote-"]').forEach(v => {
        const key = v.dataset.vkey.replace('remote-', '');
        if (!streamsExistentes.has(key)) v.remove();
      });
      // Aplica/atualiza
      streamsExistentes.forEach((stream, id) => {
        _ensureVideo(card, `remote-${id}`, stream, false);
      });
      _ajustarLayoutVideosNoCard(card);
    }
  }

  // Se ha 2 videos no card, divide em 2 colunas; senao 1 ocupa tudo.
  function _ajustarLayoutVideosNoCard(card) {
    const videos = card.querySelectorAll('video');
    videos.forEach((v, i) => {
      if (videos.length === 1) {
        v.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;object-fit:cover;border-radius:10px;background:#000;z-index:1';
      } else {
        // Dois: lado a lado, cada um 50%
        const left = i === 0 ? '0' : '50%';
        v.style.cssText = `position:absolute;top:0;left:${left};width:50%;height:100%;object-fit:cover;background:#000;z-index:1`;
      }
    });
    // Quando ha video, esconde o avatar grande
    const av = card.querySelector('.avatar-big');
    if (av) av.style.display = videos.length ? 'none' : '';
    // Nome/flags ficam acima do video com sombra pra contraste
    const nameEl = card.querySelector('.peer-name');
    const flagsEl = card.querySelector('.peer-flags');
    if (videos.length) {
      [nameEl, flagsEl].forEach(el => {
        if (el) {
          el.style.position = 'relative';
          el.style.zIndex = '2';
          el.style.textShadow = '0 1px 3px rgba(0,0,0,0.9)';
        }
      });
    }
  }

  function _aplicarVideosTodos() {
    _aplicarVideosLocais();
    _aplicarVideosRemotos();
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
    // CRITICAL: re-renderizar o innerHTML destroi qualquer <video> previamente
    // inserido. Reaplica TODOS os streams (self e remotos) logo apos.
    _aplicarVideosTodos();
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
