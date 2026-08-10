/* =====================================================================
   Agendamento publico — agendar.js
   Pagina aberta: cliente lista agendas, escolhe servico/dia/horario e
   preenche os dados. O agendamento entra como "pendente".
   ===================================================================== */

const API_HOST = (typeof API_BASE_URL !== 'undefined') ? API_BASE_URL : 'http://127.0.0.1:8000';
const API = API_HOST + '/api/atendimentos/publico';
const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
const MESES_FULL = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
const DIAS_SEM = ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado'];
const DOW = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

let agendasPub = [];      // todas as agendas ativas (fisicas + online)
let agendaSel = null;     // agenda escolhida no form
let modalidadeSel = null; // 'presencial' | 'online' — escolhida na tela 0
let vendedores = [];
let calMesRef = new Date();   // mês exibido no calendário
let diasInfo = {};            // mapa data -> {total, livres}
let diaSelecionado = null;    // data 'YYYY-MM-DD' escolhida

/* ---- util ---- */
function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g,
    c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[c]));
}
function el(id) { return document.getElementById(id); }
function setErro(msg) {
  const box = el('formErro');
  if (msg) { box.textContent = msg; box.style.display = 'block'; box.scrollIntoView({ block: 'center' }); }
  else { box.style.display = 'none'; }
}
/* Token de funcionário CPE — manda em todas as chamadas. Quando ausente,
   o backend retorna só treinamentos (cursos ficam ocultos). */
function _cpeAuthToken() {
  return localStorage.getItem('cpe_token') || sessionStorage.getItem('cpe_token')
      || localStorage.getItem('token')     || sessionStorage.getItem('token')
      || '';
}

async function get(path) {
  const headers = {};
  const tok = _cpeAuthToken();
  if (tok) headers['X-Auth-Token'] = tok;
  const r = await fetch(API + path, { headers });
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    throw new Error(e.detail || ('Erro ' + r.status));
  }
  return r.json();
}

/* ============ CARREGAMENTO ============ */
async function carregarAgendas() {
  try {
    const d = await get('/agendas');
    agendasPub = d.agendas || [];
  } catch (e) {
    agendasPub = [];
  }
}

/* ============ ESCOLHA DA MODALIDADE (tela 0) ============ */
function _mostrarApenas(viewId) {
  ['viewModalidade', 'viewLanding', 'viewForm'].forEach(v => {
    const el2 = el(v); if (el2) el2.style.display = (v === viewId) ? 'block' : 'none';
  });
  window.scrollTo(0, 0);
}

function voltarModalidade() {
  modalidadeSel = null;
  _mostrarApenas('viewModalidade');
}

async function escolherModalidade(m) {
  modalidadeSel = m;
  // garante que as agendas estao carregadas (caso o usuario abra direto via deep-link)
  if (!agendasPub.length) await carregarAgendas();

  // 2026-08-05: unificado. Mesmas agendas (unidades) aparecem em AMBAS
  // modalidades. Cliente escolhe presencial ou online — internamente ocupa
  // o mesmo slot da mesma agenda. Landing lista todas as unidades que
  // oferecem a modalidade escolhida.
  const disponiveis = _agendasPelaModalidade(m);
  if (!disponiveis.length) {
    alert('No momento nao ha unidade oferecendo atendimento ' + m + '. '
        + 'Por favor tente a outra modalidade ou volte mais tarde.');
    voltarModalidade();
    return;
  }
  _mostrarApenas('viewLanding');
  renderCards();
}

/* Retorna as agendas que oferecem a modalidade. Cai back-compat pro campo
   `tipo` quando `oferece_*` não vem do backend (banco antigo sem migration 084). */
function _agendasPelaModalidade(m) {
  if (!m) return agendasPub;
  return agendasPub.filter(a => {
    if (m === 'online') {
      return a.oferece_online != null ? !!a.oferece_online : (a.tipo === 'online');
    }
    return a.oferece_presencial != null ? !!a.oferece_presencial : (a.tipo !== 'online');
  });
}

/* Detecta se o visitante é funcionário CPE logado (token salvo no storage).
   - Funcionário CPE: vê cursos + treinamentos (cursos são privados).
   - Visitante anônimo: vê só treinamentos (link público padrão).
   Esta validação acontece DUAS vezes:
   1) Aqui no frontend: UX (esconde elementos de curso)
   2) No backend: segurança real (mesmo se hackearem o front, o backend
      filtra cursos quando a request não vem com token válido) */
function _ehFuncionarioCPE() {
  const t = localStorage.getItem('cpe_token') || sessionStorage.getItem('cpe_token')
         || localStorage.getItem('token')     || sessionStorage.getItem('token');
  const u = localStorage.getItem('cpe_user')  || sessionStorage.getItem('cpe_user')
         || localStorage.getItem('user')      || sessionStorage.getItem('user');
  return !!(t && u);
}

function renderCards() {
  const busca = (el('buscaAgenda').value || '').toLowerCase();
  const ehFunc = _ehFuncionarioCPE();
  // Ofertas visíveis:
  //   - treinamentos: SEMPRE públicos (qualquer cliente)
  //   - cursos + drones: SÓ se funcionário CPE logado (privados)
  const _ofertasDe = a => {
    const trn = a.treinamentos || [];
    if (!ehFunc) return trn;
    return trn.concat(a.servicos || []).concat(a.drones || []);
  };
  const _labelOferta = (n) => n === 1 ? '1 atendimento disponível'
                                      : n + ' atendimentos disponíveis';
  const lista = _agendasPelaModalidade(modalidadeSel)
    // esconde agendas SEM ofertas visíveis para o visitante atual.
    // Anônimo não vê agenda só de drones; funcionário CPE vê tudo.
    .filter(a => _ofertasDe(a).length > 0)
    .filter(a => {
      if (!busca) return true;
      // Busca em multiplos campos: nome da unidade, descricao da unidade,
      // e em cada oferta (nome + descricao). Cobre termos que o usuario
      // ve no card, na topbar (geomensura/drones/gnss) e no detalhe.
      const hayUnidade =
        (a.nome || '').toLowerCase().includes(busca) ||
        (a.descricao || '').toLowerCase().includes(busca);
      const hayOferta = _ofertasDe(a).some(s =>
        (s.nome || '').toLowerCase().includes(busca) ||
        (s.descricao || '').toLowerCase().includes(busca));
      return hayUnidade || hayOferta;
    });
  const box = el('cardsAgendas');
  if (!lista.length) {
    box.innerHTML = '<div class="ag-loading">Nenhuma unidade encontrada.</div>';
    return;
  }
  box.innerHTML = lista.map((a, idx) => {
    const ofertas = _ofertasDe(a);
    const total = ofertas.length;
    const stn = `STN · UN-${String(idx + 1).padStart(2, '0')}`;
    if (total === 0) {
      // Sem ofertas: card nao clicavel, atalho de "agendar nesta unidade" como CTA
      return `<div class="ag-card ag-card-vazia">
        <div class="ag-card-stn">${stn}</div>
        <div class="ag-card-nome">${esc(a.nome)}</div>
        ${a.descricao ? `<div class="ag-card-desc">${esc(a.descricao)}</div>` : ''}
        <div class="ag-card-srv-empty">
          <i class="bi bi-info-circle"></i> Sem atendimentos cadastrados
        </div>
        <button class="ag-btn ag-btn-block" style="margin-top:14px"
                onclick="abrirForm(${a.id})">
          <i class="bi bi-calendar-check"></i> Agendar nesta unidade</button>
      </div>`;
    }
    // Com ofertas: card INTEIRO eh clicavel -> abre modal de atendimentos.
    // Banner amarelo no rodape mostra o numero como afirmacao de valor.
    // Atalho discreto "Agendar direto" para quem ja sabe o que quer
    // (chama stopPropagation pra nao abrir o modal).
    const labelExplora = total === 1 ? 'atendimento disponível' : 'atendimentos disponíveis';
    return `<div class="ag-card" role="button" tabindex="0"
                 onclick="abrirModalServicos(${a.id})"
                 onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();abrirModalServicos(${a.id});}">
      <div class="ag-card-stn">${stn}</div>
      <div class="ag-card-nome">${esc(a.nome)}</div>
      ${a.descricao ? `<div class="ag-card-desc">${esc(a.descricao)}</div>` : ''}
      <button type="button" class="ag-card-direto"
              onclick="event.stopPropagation(); abrirForm(${a.id})">
        Já sabe o que quer? Agendar direto <i class="bi bi-arrow-up-right"></i>
      </button>
      <div class="ag-card-srv-banner">
        <span class="ag-card-srv-count">${total}</span>
        <span class="ag-card-srv-label">${labelExplora}</span>
        <i class="bi bi-arrow-right ag-card-srv-chev"></i>
      </div>
    </div>`;
  }).join('');
}

/* ============ MODAL: ofertas da unidade ============ */
/* Treinamentos: sempre visíveis (públicos).
   Cursos e Drones: SÓ visíveis para funcionários CPE logados (privados). */
function abrirModalServicos(agendaId) {
  const a = agendasPub.find(x => x.id === agendaId);
  if (!a) return;
  el('modalServicosTitulo').textContent = a.nome;
  const lista = el('modalServicosLista');
  const ehFunc = _ehFuncionarioCPE();
  const srv = ehFunc ? (a.servicos || []) : [];   // cursos só p/ funcionário
  const trn = a.treinamentos || [];
  const drn = ehFunc ? (a.drones || [])   : [];   // drones só p/ funcionário

  const tagPrivado = '<span style="font-size:.75rem;color:#FFC107;background:#1A1A1A;padding:2px 8px;border-radius:10px;margin-left:6px;font-weight:600">PRIVADO · CPE</span>';

  const blocos = [];
  if (trn.length) {
    blocos.push('<div class="ag-modal-secao-titulo"><i class="bi bi-easel"></i> Treinamentos</div>');
    blocos.push(trn.map(t => _renderOferta(t, 'treinamento')).join(''));
  }
  if (drn.length) {
    blocos.push(`<div class="ag-modal-secao-titulo"><i class="bi bi-airplane-engines-fill"></i> Drones ${tagPrivado}</div>`);
    blocos.push(drn.map(d => _renderOferta(d, 'drone')).join(''));
  }
  if (srv.length) {
    blocos.push(`<div class="ag-modal-secao-titulo"><i class="bi bi-mortarboard"></i> Cursos ${tagPrivado}</div>`);
    blocos.push(srv.map(s => _renderOferta(s, 'curso')).join(''));
  }
  lista.innerHTML = blocos.length
    ? blocos.join('')
    : '<li class="ag-modal-srv-empty">Nenhum atendimento disponível nesta unidade.</li>';

  const btn = el('modalServicosAgendar');
  btn.onclick = () => { fecharModalServicos(); abrirForm(agendaId); };
  el('modalServicos').classList.add('show');
  document.body.style.overflow = 'hidden';
}

/* Card COMPACTO usado na lista do modal "Ver servicos disponiveis":
   apenas nome + duracao + snippet curto da descricao + indicador de fotos/videos.
   Clicar abre o modal de detalhes com tudo. */
function _renderOferta(item, kind) {
  const fotos = item.fotos || [];
  const videos = item.videos || [];
  const snippet = item.descricao
    ? esc(item.descricao.slice(0, 110)) + (item.descricao.length > 110 ? '…' : '')
    : '';
  // primeira foto vira capa (clicavel pra detalhes)
  const capa = fotos.length
    ? `<img class="ag-oferta-capa" src="${esc(fotos[0].arquivo)}" alt="">`
    : `<div class="ag-oferta-capa ag-oferta-capa-vazia"><i class="bi bi-image"></i></div>`;
  const badgeMidia = (fotos.length > 1 || videos.length > 0)
    ? `<div class="ag-oferta-badges">
        ${fotos.length > 1 ? `<span><i class="bi bi-images"></i> ${fotos.length}</span>` : ''}
        ${videos.length    ? `<span><i class="bi bi-camera-video"></i> ${videos.length}</span>` : ''}
      </div>`
    : '';
  const tag = kind === 'treinamento' ? '<span class="ag-oferta-tag">Treinamento</span>'
            : kind === 'drone'       ? '<span class="ag-oferta-tag" style="background:#0d9488;color:#fff">Drone</span>'
            : '';
  return `<div class="ag-oferta-card-compact" onclick="abrirDetalheOferta(${item.id}, '${kind}')">
    ${capa}
    ${badgeMidia}
    <div class="ag-oferta-content">
      <div class="ag-oferta-nome">${esc(item.nome)}
        ${tag}</div>
      <div class="ag-oferta-meta-row">
        <span class="ag-oferta-meta"><i class="bi bi-clock"></i> ${item.duracao_min} min</span>
        ${item.instrutor ? `<span class="ag-oferta-meta"><i class="bi bi-person-badge"></i> ${esc(item.instrutor)}</span>` : ''}
      </div>
      ${snippet ? `<div class="ag-oferta-snippet">${snippet}</div>` : ''}
      <div class="ag-oferta-cta-row">
        <span class="ag-oferta-cta">Ver detalhes <i class="bi bi-arrow-right"></i></span>
      </div>
    </div>
  </div>`;
}

/* Abre modal de detalhes (drill-down) com TUDO da oferta. */
function abrirDetalheOferta(itemId, kind) {
  // localiza item na agenda atualmente aberta no modal de servicos
  const tituloAgenda = el('modalServicosTitulo').textContent;
  const ag = agendasPub.find(a => a.nome === tituloAgenda);
  if (!ag) return;
  const lista = kind === 'treinamento' ? (ag.treinamentos || [])
              : kind === 'drone'       ? (ag.drones || [])
              :                          (ag.servicos || []);
  const item = lista.find(x => x.id === itemId);
  if (!item) return;

  // header
  el('detalheEyebrow').textContent = kind === 'treinamento' ? 'Treinamento'
                                   : kind === 'drone'       ? 'Drone'
                                   :                          'Curso';
  el('detalheTitulo').textContent = item.nome;

  // body — Hero (banner ou primeira foto) + carrossel + módulos + descrição
  const fotos = item.fotos || [];
  const videos = item.videos || [];
  const modulos = item.modulos || [];
  const iconKind = kind === 'treinamento' ? 'bi-mortarboard-fill'
                 : kind === 'drone'       ? 'bi-airplane-engines-fill'
                 :                          'bi-pc-display';

  // HERO: prioridade ao banner_url (campo dedicado); fallback pra 1a foto da galeria.
  const heroSrc = item.banner_url || (fotos[0] && fotos[0].arquivo) || null;
  const heroBlock = heroSrc
    ? `<div class="ag-detalhe-hero-wrap ${item.banner_url ? 'has-banner' : ''}">
         <img class="ag-detalhe-hero" src="${esc(heroSrc)}" alt=""
              onclick="abrirFotoLightbox('${esc(heroSrc)}')">
       </div>`
    : `<div class="ag-detalhe-hero-wrap">
         <div class="ag-detalhe-hero-placeholder"><i class="bi ${iconKind}"></i></div>
       </div>`;

  // CARROSSEL: todas as fotos da galeria (incluindo a usada como hero se NÃO houver banner_url separado).
  // Quando há banner_url dedicado, carrossel mostra TODAS as fotos da galeria.
  // Quando não há, o carrossel mostra a partir da SEGUNDA foto (a primeira virou hero).
  const fotosCarrossel = item.banner_url ? fotos : fotos.slice(1);
  const carrosselSec = fotosCarrossel.length > 0
    ? `<div class="ag-detalhe-secao">
        <div class="ag-detalhe-secao-titulo"><i class="bi bi-images"></i> Galeria</div>
        <div class="ag-carrossel" data-total="${fotosCarrossel.length}">
          <div class="ag-carrossel-track">
            ${fotosCarrossel.map((f, i) => `
              <div class="ag-carrossel-slide" data-idx="${i}">
                <img src="${esc(f.arquivo)}" alt="" onclick="abrirFotoLightbox('${esc(f.arquivo)}')">
              </div>
            `).join('')}
          </div>
          ${fotosCarrossel.length > 1 ? `
            <button type="button" class="ag-carrossel-nav prev" aria-label="Anterior"
                    onclick="carrosselNav(-1)"><i class="bi bi-chevron-left"></i></button>
            <button type="button" class="ag-carrossel-nav next" aria-label="Próximo"
                    onclick="carrosselNav(1)"><i class="bi bi-chevron-right"></i></button>
            <div class="ag-carrossel-dots">
              ${fotosCarrossel.map((_, i) => `
                <button type="button" class="ag-carrossel-dot ${i === 0 ? 'active' : ''}"
                        data-idx="${i}" onclick="carrosselGoto(${i})"
                        aria-label="Foto ${i + 1}"></button>
              `).join('')}
            </div>
          ` : ''}
        </div>
      </div>`
    : '';

  // MÓDULOS: lista numerada, expansível.
  const modulosSec = modulos.length
    ? `<div class="ag-detalhe-secao">
        <div class="ag-detalhe-secao-titulo">
          <i class="bi bi-list-ol"></i> Conteúdo programático
          <span class="ag-detalhe-secao-aside">${modulos.length} módulo${modulos.length === 1 ? '' : 's'}</span>
        </div>
        <div class="ag-modulos">${modulos.map((m, i) => {
          const dur = m.duracao_min ? `<span class="ag-modulo-dur"><i class="bi bi-clock"></i> ${m.duracao_min} min</span>` : '';
          const topicos = (m.topicos && m.topicos.length)
            ? `<ul class="ag-modulo-topicos">${m.topicos.map(t => `<li><i class="bi bi-check2"></i>${esc(t)}</li>`).join('')}</ul>`
            : '';
          const desc = m.descricao ? `<div class="ag-modulo-desc">${esc(m.descricao)}</div>` : '';
          return `<div class="ag-modulo">
            <div class="ag-modulo-head">
              <div class="ag-modulo-num">${String(i + 1).padStart(2, '0')}</div>
              <div class="ag-modulo-info">
                <div class="ag-modulo-titulo">${esc(m.titulo)}</div>
                ${dur}
              </div>
            </div>
            ${(desc || topicos) ? `<div class="ag-modulo-body">${desc}${topicos}</div>` : ''}
          </div>`;
        }).join('')}</div>
      </div>`
    : '';

  const videosSec = videos.length
    ? `<div class="ag-detalhe-secao">
        <div class="ag-detalhe-secao-titulo"><i class="bi bi-camera-video"></i> Vídeos</div>
        <div class="ag-detalhe-videos">${videos.map(v =>
          `<a href="#" onclick="abrirVideoPopup('${esc(v.url)}', '${esc(v.titulo || '')}'); return false;">
            <i class="bi bi-play-circle-fill"></i>
            <span>${esc(v.titulo || 'Ver vídeo')}</span>
          </a>`
        ).join('')}</div>
      </div>`
    : '';
  const descSec = item.descricao
    ? `<div class="ag-detalhe-secao">
        <div class="ag-detalhe-secao-titulo"><i class="bi bi-file-text"></i> Sobre</div>
        <div class="ag-detalhe-desc">${esc(item.descricao)}</div>
      </div>`
    : '';

  el('detalheBody').innerHTML = `
    ${heroBlock}
    <div class="ag-detalhe-content">
      <div class="ag-detalhe-meta">
        <span class="ag-oferta-meta"><i class="bi bi-clock"></i> ${item.duracao_min} min</span>
        ${item.instrutor ? `<span class="ag-oferta-meta"><i class="bi bi-person-badge"></i> ${esc(item.instrutor)}</span>` : ''}
        ${item.vendedor  ? `<span class="ag-oferta-meta"><i class="bi bi-person-vcard"></i> ${esc(item.vendedor)}</span>` : ''}
      </div>
      ${descSec}
      ${modulosSec}
      ${carrosselSec}
      ${videosSec}
    </div>
  `;
  // Inicializa carrossel (auto-play + estado interno)
  _inicializarCarrossel();

  // botao "Agendar este" — fecha tudo e abre o form com a oferta pre-selecionada
  const labelKind = kind === 'treinamento' ? 'treinamento'
                  : kind === 'drone'       ? 'drone'
                  :                          'curso';
  el('detalheBtnAgendar').innerHTML =
    `<i class="bi bi-calendar-check"></i> Agendar este ${labelKind}`;
  el('detalheBtnAgendar').onclick = () => {
    fecharDetalhe();
    fecharModalServicos();
    abrirForm(ag.id, { entidade: kind, id: itemId });
  };

  el('modalDetalhe').classList.add('show');
}

/* ===== Carrossel de fotos do detalhe =====
   Setas + dots + auto-play (5s, pausa quando o usuário interage). */
let _carEl = null;
let _carIdx = 0;
let _carTotal = 0;
let _carTimer = null;

function _inicializarCarrossel() {
  if (_carTimer) { clearInterval(_carTimer); _carTimer = null; }
  _carEl = document.querySelector('#detalheBody .ag-carrossel');
  if (!_carEl) { _carIdx = 0; _carTotal = 0; return; }
  _carTotal = parseInt(_carEl.dataset.total || '0', 10);
  _carIdx = 0;
  _aplicarCarrossel();
  if (_carTotal > 1) {
    _carTimer = setInterval(() => carrosselNav(1, /*auto*/true), 5000);
    // Pausa auto-play quando o usuário interage
    _carEl.addEventListener('mouseenter', _pausarCarrossel);
    _carEl.addEventListener('mouseleave', _retomarCarrossel);
  }
}
function _pausarCarrossel() {
  if (_carTimer) { clearInterval(_carTimer); _carTimer = null; }
}
function _retomarCarrossel() {
  if (!_carTimer && _carTotal > 1) {
    _carTimer = setInterval(() => carrosselNav(1, true), 5000);
  }
}
function _aplicarCarrossel() {
  if (!_carEl) return;
  const track = _carEl.querySelector('.ag-carrossel-track');
  if (track) track.style.transform = `translateX(-${_carIdx * 100}%)`;
  _carEl.querySelectorAll('.ag-carrossel-dot').forEach((d, i) => {
    d.classList.toggle('active', i === _carIdx);
  });
}
function carrosselNav(delta, auto) {
  if (!_carEl || _carTotal < 2) return;
  if (!auto) _pausarCarrossel();  // interação manual reseta auto-play
  _carIdx = (_carIdx + delta + _carTotal) % _carTotal;
  _aplicarCarrossel();
  if (!auto) _retomarCarrossel();
}
function carrosselGoto(idx) {
  if (!_carEl || idx < 0 || idx >= _carTotal) return;
  _pausarCarrossel();
  _carIdx = idx;
  _aplicarCarrossel();
  _retomarCarrossel();
}

function fecharDetalhe(ev) {
  if (ev && ev.target && ev.target.id !== 'modalDetalhe') return;
  el('modalDetalhe').classList.remove('show');
  if (_carTimer) { clearInterval(_carTimer); _carTimer = null; }
}

function abrirFotoLightbox(src) {
  // Lightbox simples: overlay com a foto em tamanho grande
  let lb = document.getElementById('agLightbox');
  if (!lb) {
    lb = document.createElement('div');
    lb.id = 'agLightbox';
    lb.className = 'ag-lightbox';
    lb.onclick = () => lb.classList.remove('show');
    document.body.appendChild(lb);
  }
  lb.innerHTML = `<img src="${esc(src)}" alt=""><button class="ag-lightbox-close">&times;</button>`;
  lb.classList.add('show');
}

/* ====== POPUP DE VIDEO (mesmo padrao de lightbox, com player embed) ======
   Suporta YouTube, Vimeo e arquivos diretos (mp4/webm). Pra qualquer outro
   host, mostra fallback com link "Abrir em nova aba" — alguns sites bloqueiam
   iframe por X-Frame-Options. */
function abrirVideoPopup(url, titulo) {
  let pop = document.getElementById('agVideoPopup');
  if (!pop) {
    pop = document.createElement('div');
    pop.id = 'agVideoPopup';
    pop.className = 'ag-video-popup';
    pop.onclick = (e) => { if (e.target === pop) fecharVideoPopup(); };
    document.body.appendChild(pop);
  }
  pop.innerHTML = _renderVideoPopupHtml(url, titulo);
  pop.classList.add('show');
  document.body.style.overflow = 'hidden';
}

function fecharVideoPopup() {
  const pop = document.getElementById('agVideoPopup');
  if (!pop || !pop.classList.contains('show')) return;
  pop.classList.remove('show');
  // Limpa o conteudo pra parar o video (iframe/video tag continuam tocando senao)
  pop.innerHTML = '';
  document.body.style.overflow = '';
}

function _renderVideoPopupHtml(url, titulo) {
  const embed = _toEmbedUrl(url);
  let player;
  if (embed.type === 'iframe') {
    player = `<iframe src="${esc(embed.src)}" frameborder="0"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
      allowfullscreen></iframe>`;
  } else if (embed.type === 'video') {
    player = `<video src="${esc(embed.src)}" controls autoplay playsinline></video>`;
  } else {
    player = `<div class="ag-video-popup-fallback">
      <i class="bi bi-info-circle"></i>
      <p>Esse vídeo não pode ser exibido dentro da página.</p>
      <a href="${esc(url)}" target="_blank" rel="noopener" class="ag-btn ag-btn-primary">
        <i class="bi bi-box-arrow-up-right"></i> Abrir em nova aba
      </a>
    </div>`;
  }
  return `
    <div class="ag-video-popup-box" onclick="event.stopPropagation()">
      <div class="ag-video-popup-header">
        <span class="ag-video-popup-title">
          <i class="bi bi-camera-video"></i> ${esc(titulo || 'Vídeo')}
        </span>
        <button type="button" class="ag-video-popup-close"
                onclick="fecharVideoPopup()" title="Fechar (Esc)">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>
      <div class="ag-video-popup-player">${player}</div>
    </div>`;
}

function _toEmbedUrl(url) {
  try {
    const u = new URL(url, location.origin);
    const host = u.hostname.replace(/^www\./, '');
    // YouTube
    if (host === 'youtube.com' || host === 'm.youtube.com') {
      if (u.pathname === '/watch') {
        const v = u.searchParams.get('v');
        if (v) return { type: 'iframe', src: `https://www.youtube.com/embed/${v}?autoplay=1&rel=0` };
      }
      if (u.pathname.startsWith('/embed/')) return { type: 'iframe', src: url };
      if (u.pathname.startsWith('/shorts/')) {
        const id = u.pathname.split('/')[2];
        if (id) return { type: 'iframe', src: `https://www.youtube.com/embed/${id}?autoplay=1&rel=0` };
      }
    }
    if (host === 'youtu.be') {
      const id = u.pathname.replace(/^\//, '').split('/')[0];
      if (id) return { type: 'iframe', src: `https://www.youtube.com/embed/${id}?autoplay=1&rel=0` };
    }
    // Vimeo
    if (host === 'vimeo.com') {
      const id = u.pathname.replace(/^\//, '').split('/')[0];
      if (/^\d+$/.test(id)) return { type: 'iframe', src: `https://player.vimeo.com/video/${id}?autoplay=1` };
    }
    if (host === 'player.vimeo.com') return { type: 'iframe', src: url };
    // Arquivo direto
    if (/\.(mp4|webm|ogg|ogv|mov)(\?.*)?$/i.test(u.pathname)) {
      return { type: 'video', src: url };
    }
  } catch (_e) { /* URL invalida cai no fallback */ }
  return { type: 'unknown', src: url };
}

function fecharModalServicos(ev) {
  if (ev && ev.target && ev.target.id !== 'modalServicos') return;
  el('modalServicos').classList.remove('show');
  document.body.style.overflow = '';
}

/* ============ FORM ============ */
// preselect (opcional): { entidade: 'servico'|'treinamento', id: number }
// — se passado, o select de serviço ja vem pre-selecionado e dispara o load.
function abrirForm(agendaId, preselect) {
  _mostrarApenas('viewForm');
  el('passo1').style.display = 'block';
  el('passo2').style.display = 'none';
  el('passoOk').style.display = 'none';
  marcarStep(1);
  setErro('');

  // Filtra as opcoes do select de agendas pela modalidade escolhida.
  // Se nao houver modalidade (deep link ?agenda=ID), mostra todas.
  const opcoes = _agendasPelaModalidade(modalidadeSel);
  el('fAgenda').innerHTML = opcoes.map(a =>
    `<option value="${a.id}">${esc(a.nome)}</option>`).join('');
  el('fAgenda').value = agendaId;

  // 2026-08-05: modelo unificado — cliente pode trocar de modalidade dentro
  // do form (antes bloqueava porque online tinha fluxo separado). Só
  // pre-marca a que ele escolheu na landing.
  const radios = document.querySelectorAll('input[name="modalidade"]');
  radios.forEach(r => {
    r.checked = (modalidadeSel && r.value === modalidadeSel);
    r.disabled = false;
  });

  onAgendaChange();
  // onAgendaChange limpa os radios — repoe a modalidade se aplicavel
  if (modalidadeSel) {
    radios.forEach(r => { r.checked = r.value === modalidadeSel; });
    if (typeof onModalidadeChange === 'function') onModalidadeChange();
  }
  // Se veio com preselect (clique em "Agendar este X" no modal de detalhes),
  // ja seleciona o serviço/treinamento e dispara carga de dias.
  if (preselect && preselect.entidade && preselect.id) {
    const val = preselect.entidade + ':' + preselect.id;
    const sel = el('fServico');
    if ([...sel.options].some(o => o.value === val)) {
      sel.value = val;
      onServicoChange();
    }
  }
}

function voltarLanding() {
  // 2026-08-05: online e presencial usam a mesma landing.
  // Voltar do form vai pra landing sempre.
  _mostrarApenas('viewLanding');
}

function marcarStep(n) {
  el('step1').classList.toggle('active', n >= 1);
  el('step2').classList.toggle('active', n >= 2);
}

function onAgendaChange() {
  const id = parseInt(el('fAgenda').value);
  agendaSel = agendasPub.find(a => a.id === id) || null;
  // instruções
  if (agendaSel && agendaSel.instrucoes) {
    el('txtInstrucoes').textContent = agendaSel.instrucoes;
    el('boxInstrucoes').style.display = 'block';
  } else {
    el('boxInstrucoes').style.display = 'none';
  }
  // Treinamentos: sempre visíveis. Cursos e Drones: só para funcionários CPE.
  const fs = el('fServico');
  const ehFunc = _ehFuncionarioCPE();
  const cursos  = ehFunc ? ((agendaSel && agendaSel.servicos) || []) : [];
  const treinos = (agendaSel && agendaSel.treinamentos) || [];
  const drones  = ehFunc ? ((agendaSel && agendaSel.drones) || []) : [];
  let html = '<option value="">--- Escolha um atendimento ---</option>';
  if (treinos.length) {
    html += '<optgroup label="Treinamentos">';
    html += treinos.map(t =>
      `<option value="treinamento:${t.id}">${esc(t.nome)}</option>`).join('');
    html += '</optgroup>';
  }
  if (cursos.length) {
    html += '<optgroup label="Cursos (CPE)">';
    html += cursos.map(s =>
      `<option value="servico:${s.id}">${esc(s.nome)}</option>`).join('');
    html += '</optgroup>';
  }
  if (drones.length) {
    html += '<optgroup label="Drones (CPE)">';
    html += drones.map(d =>
      `<option value="drone:${d.id}">${esc(d.nome)}</option>`).join('');
    html += '</optgroup>';
  }
  fs.innerHTML = html;
  document.querySelectorAll('input[name="modalidade"]').forEach(r => { r.checked = false; });
  resetCalendario();
}

/* Decodifica o value do select 'fServico' (formato 'tipo:ID') em
   { servico_id, treinamento_id, drone_id } pronto pra query string. */
function _ofertaSelecionada() {
  const v = (el('fServico').value || '').split(':');
  if (v.length !== 2) return null;
  const [tipo, idStr] = v;
  const id = parseInt(idStr);
  if (!id) return null;
  if (tipo === 'treinamento') return { treinamento_id: id };
  if (tipo === 'drone')       return { drone_id: id };
  return { servico_id: id };
}

function pad2(n) { return String(n).padStart(2, '0'); }
function ymd(d) { return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate()); }
function rotuloDia(dataStr) {
  const d = new Date(dataStr + 'T00:00:00');
  return `${DIAS_SEM[d.getDay()]}, ${d.getDate()} de ${MESES[d.getMonth()]}`;
}

function resetCalendario() {
  diasInfo = {};
  diaSelecionado = null;
  el('fHorario').value = '';
  el('agCalGrid').innerHTML = '<div class="ag-help" style="grid-column:1/-1">Escolha um serviço primeiro.</div>';
  el('agCalMes').textContent = '—';
  el('agSlots').innerHTML = '';
}

function onServicoChange() { _ajustarModalidadesPorOferta(); carregarDias(); }
function onModalidadeChange() { carregarDias(); }

/* Curso e Drone são APENAS presenciais — quando o cliente seleciona um deles,
   esconde a opção "Online" e marca "Presencial" automaticamente.
   Treinamento mantém as duas opções. */
function _ajustarModalidadesPorOferta() {
  const oferta = _ofertaSelecionada();
  const radioPres = document.querySelector('input[name="modalidade"][value="presencial"]');
  const radioOnl  = document.querySelector('input[name="modalidade"][value="online"]');
  if (!radioPres || !radioOnl) return;
  const labelOnl = radioOnl.closest('label');

  const soPresencial = oferta && (oferta.servico_id || oferta.drone_id);
  if (soPresencial) {
    if (labelOnl) labelOnl.style.display = 'none';
    radioOnl.checked = false;
    radioPres.checked = true;
  } else {
    // Treinamento: ambas
    if (labelOnl) labelOnl.style.display = '';
  }
}

// O calendário só carrega depois que serviço E modalidade foram escolhidos —
// a disponibilidade dos dias depende da modalidade.
async function carregarDias() {
  resetCalendario();
  const oferta = _ofertaSelecionada();
  const modalidade = radioVal('modalidade');
  if (!oferta || !agendaSel) return;
  if (!modalidade) {
    el('agCalGrid').innerHTML = '<div class="ag-help" style="grid-column:1/-1">' +
      'Escolha presencial ou online para ver os dias disponíveis.</div>';
    return;
  }
  el('agCalGrid').innerHTML = '<div class="ag-help" style="grid-column:1/-1">Carregando dias...</div>';
  const params = new URLSearchParams({ ...oferta, modalidade });
  try {
    const d = await get(`/agendas/${agendaSel.id}/dias?${params}`);
    diasInfo = {};
    (d.dias || []).forEach(x => { diasInfo[x.data] = x; });
    const primeiroLivre = (d.dias || []).find(x => x.livres > 0);
    calMesRef = primeiroLivre ? new Date(primeiroLivre.data + 'T00:00:00') : new Date();
    calMesRef.setDate(1);
    renderCalendario();
  } catch (e) {
    el('agCalGrid').innerHTML =
      '<div class="ag-help" style="grid-column:1/-1">Erro ao carregar dias.</div>';
  }
}

function calMudarMes(delta) {
  calMesRef = new Date(calMesRef.getFullYear(), calMesRef.getMonth() + delta, 1);
  renderCalendario();
}

function renderCalendario() {
  const ano = calMesRef.getFullYear(), mes = calMesRef.getMonth();
  el('agCalMes').textContent = MESES_FULL[mes] + ' ' + ano;
  const ini = new Date(ano, mes, 1);
  ini.setDate(ini.getDate() - ini.getDay());   // recua até domingo
  let html = DOW.map(d => `<div class="ag-cal-dow">${d}</div>`).join('');
  const cur = new Date(ini);
  for (let i = 0; i < 42; i++) {
    const ds = ymd(cur);
    const foraMes = cur.getMonth() !== mes;
    const info = diasInfo[ds];
    let cls = 'ag-cal-day', extra = '', click = '';
    if (foraMes) {
      cls += ' fora';
    } else if (info && info.livres > 0) {
      cls += ' livre'; click = `onclick="selecionarDia('${ds}')"`;
      extra = `<small>${info.livres} livre(s)</small>`;
    } else if (info) {
      cls += ' cheio'; extra = '<small>sem vaga</small>';
    } else {
      cls += ' indisp';
    }
    if (ds === diaSelecionado) cls += ' sel';
    html += `<div class="${cls}" ${click}>${cur.getDate()}${extra}</div>`;
    cur.setDate(cur.getDate() + 1);
  }
  el('agCalGrid').innerHTML = html;
}

async function selecionarDia(dataStr) {
  diaSelecionado = dataStr;
  el('fHorario').value = '';
  renderCalendario();
  el('agSlots').innerHTML = '<div class="ag-help">Carregando horários...</div>';
  const oferta = _ofertaSelecionada();
  if (!oferta) return;
  const params = new URLSearchParams({
    ...oferta, data: dataStr, modalidade: radioVal('modalidade'),
  });
  try {
    const d = await get(`/agendas/${agendaSel.id}/horarios?${params}`);
    renderSlots(d.horarios || []);
  } catch (e) {
    el('agSlots').innerHTML = '<div class="ag-help">Erro ao carregar horários.</div>';
  }
}

function renderSlots(slots) {
  if (!slots.length) {
    el('agSlots').innerHTML = '<div class="ag-help">Nenhum horário neste dia.</div>';
    return;
  }
  const grade = slots.map(s => s.disponivel
    ? `<button type="button" class="ag-slot livre" data-inicio="${s.inicio}"
         onclick="escolherSlot(this)">${s.label}</button>`
    : `<button type="button" class="ag-slot cheio" disabled
         title="Horário já preenchido">${s.label} • Ocupado</button>`
  ).join('');
  el('agSlots').innerHTML =
    `<div class="ag-slots-titulo">Horários de ${rotuloDia(diaSelecionado)}</div>
     <div class="ag-slots-grid">${grade}</div>`;
}

function escolherSlot(btn) {
  document.querySelectorAll('.ag-slot.sel').forEach(b => b.classList.remove('sel'));
  btn.classList.add('sel');
  el('fHorario').value = btn.dataset.inicio;
}

/* ---- navegação entre passos ---- */
async function irPasso(n) {
  setErro('');
  if (n === 2) {
    if (!el('fServico').value) return setErro('Escolha um serviço.');
    if (!radioVal('modalidade')) return setErro('Escolha se o treinamento é presencial ou online.');
    if (!el('fHorario').value) return setErro('Escolha um dia e um horário no calendário.');
    await prepararPasso2();
    el('passo1').style.display = 'none';
    el('passo2').style.display = 'block';
    marcarStep(2);
  } else {
    el('passo2').style.display = 'none';
    el('passo1').style.display = 'block';
    marcarStep(1);
  }
  window.scrollTo(0, 0);
}

async function prepararPasso2() {
  // equipamentos da oferta escolhida (curso ou treinamento)
  const oferta = _ofertaSelecionada();
  const cx = el('listaEquipamentos');
  cx.innerHTML = '<div class="ag-help">Carregando...</div>';
  if (!oferta) { el('boxEquipamentos').style.display = 'none'; return; }
  const path = oferta.servico_id      ? `/servicos/${oferta.servico_id}/equipamentos`
             : oferta.treinamento_id  ? `/treinamentos/${oferta.treinamento_id}/equipamentos`
             :                          `/drones/${oferta.drone_id}/equipamentos`;
  try {
    const d = await get(path);
    const eqs = d.equipamentos || [];
    if (!eqs.length) {
      el('boxEquipamentos').style.display = 'none';
    } else {
      el('boxEquipamentos').style.display = 'block';
      cx.innerHTML = eqs.map(e =>
        `<label class="ag-radio"><input type="radio" name="equipamento" value="${e.id}"> ${esc(e.nome)}</label>`
      ).join('');
    }
  } catch (e) {
    cx.innerHTML = '<div class="ag-help">Erro ao carregar equipamentos.</div>';
  }
  // vendedores (uma vez)
  if (!vendedores.length) {
    try {
      const d = await get('/vendedores');
      vendedores = d.vendedores || [];
    } catch (e) { vendedores = []; }
  }
  const lv = el('listaVendedores');
  el('boxVendedorLivre').style.display = 'none';
  el('fVendedorLivre').value = '';

  if (vendedores.length) {
    // Lista de cadastrados + opcao "Outro" no final
    lv.innerHTML = vendedores.map(v =>
        `<label class="ag-radio"><input type="radio" name="vendedor" value="${v.id}"
           onchange="onVendedorChange()"> ${esc(v.name)}</label>`).join('') +
      `<label class="ag-radio"><input type="radio" name="vendedor" value="outro"
         onchange="onVendedorChange()"> <em>Outro / não está na lista</em></label>`;
  } else {
    // Lista vazia — vai direto pro input livre
    lv.innerHTML = '<div class="ag-help" style="margin-bottom:6px">' +
      'Nenhum vendedor cadastrado. Informe o nome:</div>';
    el('boxVendedorLivre').style.display = 'block';
  }
}

function onVendedorChange() {
  const v = radioVal('vendedor');
  const box = el('boxVendedorLivre');
  box.style.display = (v === 'outro') ? 'block' : 'none';
  if (v === 'outro') el('fVendedorLivre').focus();
  else el('fVendedorLivre').value = '';
}

function radioVal(nome) {
  const r = document.querySelector(`input[name="${nome}"]:checked`);
  return r ? r.value : '';
}

async function enviarAgendamento() {
  setErro('');
  const nome = el('fNome').value.trim();
  const email = el('fEmail').value.trim();
  const telefone = el('fTelefone').value.trim();
  if (!nome) return setErro('Informe seu nome completo.');
  if (!email || !email.includes('@')) return setErro('Informe um e-mail válido.');
  if (!telefone) return setErro('Informe seu telefone.');

  const temEquip = el('boxEquipamentos').style.display !== 'none';
  const equipamento = radioVal('equipamento');
  if (temEquip && !equipamento) return setErro('Selecione o equipamento.');
  const modalidade = radioVal('modalidade');
  if (!modalidade) return setErro('Informe se o treinamento é presencial ou online.');
  const tipo = radioVal('tipo');
  if (!tipo) return setErro('Informe se é locação ou venda.');
  // Vendedor: cadastrado (id), "outro" (nome livre obrigatorio),
  // ou input direto se nao tem nenhum cadastrado (lista vazia)
  const vendedorVal = radioVal('vendedor');
  let vendedor_id = null;
  let vendedor_nome = '';
  if (vendedores.length) {
    if (!vendedorVal) return setErro('Selecione o vendedor que te atende.');
    if (vendedorVal === 'outro') {
      vendedor_nome = el('fVendedorLivre').value.trim();
      if (!vendedor_nome) return setErro('Digite o nome do vendedor.');
    } else {
      vendedor_id = parseInt(vendedorVal);
    }
  } else {
    vendedor_nome = el('fVendedorLivre').value.trim();
    if (!vendedor_nome) return setErro('Informe o nome do vendedor.');
  }

  const oferta = _ofertaSelecionada();
  if (!oferta) return setErro('Escolha um curso ou treinamento.');
  const payload = {
    agenda_id: agendaSel.id,
    ...oferta,                    // servico_id OU treinamento_id
    inicio: el('fHorario').value,
    cliente_nome: nome,
    cliente_email: email,
    cliente_telefone: telefone,
    cliente_empresa: el('fEmpresa').value.trim(),
    cliente_funcao: el('fFuncao').value.trim(),
    observacoes: el('fMensagem').value.trim(),
    equipamento_id: equipamento || null,
    modalidade: modalidade,
    tipo_negocio: tipo,
    vendedor_id: vendedor_id,
    vendedor_nome: vendedor_nome,
  };

  const btn = el('btnEnviar');
  btn.disabled = true;
  try {
    const _h = { 'Content-Type': 'application/json' };
    const _tok = _cpeAuthToken();
    if (_tok) _h['X-Auth-Token'] = _tok;
    const r = await fetch(API + '/agendar', {
      method: 'POST',
      headers: _h,
      body: JSON.stringify(payload),
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      setErro(d.detail || 'Não foi possível concluir o agendamento.');
      btn.disabled = false;
      return;
    }
    el('passo2').style.display = 'none';
    el('passoOk').style.display = 'block';
    el('okMsg').textContent = d.mensagem || 'Aguarde a confirmação da equipe.';
    window.scrollTo(0, 0);
  } catch (e) {
    setErro('Erro de conexão. Tente novamente.');
    btn.disabled = false;
  }
}

// Fluxo da pagina publica:
//   - Tela 0 (default): escolha presencial / online
//   - Deep link ?modalidade=presencial : pula tela 0, mostra unidades
//   - Deep link ?modalidade=online     : pula tela 0, abre form da agenda online
//   - Deep link ?agenda=ID             : compatibilidade — abre form daquela agenda
async function bootstrap() {
  // Badge "Logado como funcionário CPE" — ativa se houver token salvo
  if (_ehFuncionarioCPE()) {
    const badge = document.getElementById('cpeFuncBadge');
    if (badge) badge.style.display = 'block';
  }

  await carregarAgendas();

  const params = new URLSearchParams(window.location.search);
  const modal = params.get('modalidade');
  const agParam = params.get('agenda');

  // ?agenda=<id> (compat) OU ?agenda=<slug> (2026-08-05, link direto do instrutor)
  if (agParam) {
    let alvo = null;
    if (/^\d+$/.test(agParam)) {
      alvo = agendasPub.find(a => a.id === parseInt(agParam, 10));
    } else {
      // Slug: primeiro tenta na lista já carregada, senão resolve via endpoint
      alvo = agendasPub.find(a => a.slug === agParam);
      if (!alvo) {
        try {
          const r = await fetch(`${API_BASE_URL}/api/atendimentos/publico/agendas/slug/${encodeURIComponent(agParam)}`);
          if (r.ok) {
            const d = await r.json();
            alvo = d.agenda;
            // Injeta na lista pra views subsequentes acharem
            if (alvo && !agendasPub.find(a => a.id === alvo.id)) agendasPub.push(alvo);
          }
        } catch (_) { /* segue pra erro genérico abaixo */ }
      }
    }
    if (alvo) {
      // Agenda unificada (2026-08-05): oferece as duas modalidades por padrão.
      // Se o instrutor desligou uma, respeita — senão mostra tela de escolha.
      const pres = alvo.oferece_presencial != null ? !!alvo.oferece_presencial : true;
      const onl  = alvo.oferece_online     != null ? !!alvo.oferece_online     : (alvo.tipo === 'online');
      if (pres && onl) {
        // Cliente escolhe modalidade — se veio junto na URL, aplica direto
        if (modal === 'presencial' || modal === 'online') {
          modalidadeSel = modal;
        } else {
          modalidadeSel = 'presencial';
        }
      } else {
        modalidadeSel = pres ? 'presencial' : 'online';
      }
      abrirForm(alvo.id);
      return;
    }
    setErro('Agenda nao encontrada ou desativada. Escolha uma da lista.');
    _mostrarApenas('viewModalidade');
    return;
  }

  if (modal === 'presencial' || modal === 'online') {
    escolherModalidade(modal);
    return;
  }

  // padrao: tela inicial de escolha
  _mostrarApenas('viewModalidade');
}

document.addEventListener('DOMContentLoaded', bootstrap);

// ESC fecha modais (popup de video > detalhes > lista de servicos)
document.addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  const vp = document.getElementById('agVideoPopup');
  if (vp && vp.classList.contains('show')) { fecharVideoPopup(); return; }
  const detalhe = el('modalDetalhe');
  if (detalhe && detalhe.classList.contains('show')) { fecharDetalhe(); return; }
  const srv = el('modalServicos');
  if (srv && srv.classList.contains('show')) { fecharModalServicos(); }
});
