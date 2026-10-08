(() => {
  'use strict';
  const NAMES = `Bulbasaur|Ivysaur|Venusaur|Charmander|Charmeleon|Charizard|Squirtle|Wartortle|Blastoise|Caterpie|Metapod|Butterfree|Weedle|Kakuna|Beedrill|Pidgey|Pidgeotto|Pidgeot|Rattata|Raticate|Spearow|Fearow|Ekans|Arbok|Pikachu|Raichu|Sandshrew|Sandslash|Nidoran♀|Nidorina|Nidoqueen|Nidoran♂|Nidorino|Nidoking|Clefairy|Clefable|Vulpix|Ninetales|Jigglypuff|Wigglytuff|Zubat|Golbat|Oddish|Gloom|Vileplume|Paras|Parasect|Venonat|Venomoth|Diglett|Dugtrio|Meowth|Persian|Psyduck|Golduck|Mankey|Primeape|Growlithe|Arcanine|Poliwag|Poliwhirl|Poliwrath|Abra|Kadabra|Alakazam|Machop|Machoke|Machamp|Bellsprout|Weepinbell|Victreebel|Tentacool|Tentacruel|Geodude|Graveler|Golem|Ponyta|Rapidash|Slowpoke|Slowbro|Magnemite|Magneton|Farfetch'd|Doduo|Dodrio|Seel|Dewgong|Grimer|Muk|Shellder|Cloyster|Gastly|Haunter|Gengar|Onix|Drowzee|Hypno|Krabby|Kingler|Voltorb|Electrode|Exeggcute|Exeggutor|Cubone|Marowak|Hitmonlee|Hitmonchan|Lickitung|Koffing|Weezing|Rhyhorn|Rhydon|Chansey|Tangela|Kangaskhan|Horsea|Seadra|Goldeen|Seaking|Staryu|Starmie|Mr. Mime|Scyther|Jynx|Electabuzz|Magmar|Pinsir|Tauros|Magikarp|Gyarados|Lapras|Ditto|Eevee|Vaporeon|Jolteon|Flareon|Porygon|Omanyte|Omastar|Kabuto|Kabutops|Aerodactyl|Snorlax|Articuno|Zapdos|Moltres|Dratini|Dragonair|Dragonite|Mewtwo|Mew`.split('|');
  if (NAMES.length !== 151) throw new Error('Pokédex names list does not contain 151 species.');
  const $ = id => document.getElementById(id);
  const refs = {
    head: $('head-select'), body: $('body-select'), edition: $('edition'), palette: $('palette'),
    size: $('head-size'), splice: $('splice'), smart: $('auto-seam'), canvas: $('fusion-canvas'),
    headPreview: $('head-preview'), bodyPreview: $('body-preview'), loader: $('loader'),
    error: $('error-msg'), status: $('status-text'), name: $('fusion-name'), details: $('fusion-details'),
    recent: $('recent-grid'), download: $('download-btn')
  };
  const STORAGE_KEY = 'pokesplice.gen1.history.v1';
  const cache = new Map();
  let currentRender = 0;
  let timer = 0;
  let history = [];
  let isReady = false;
  const numeric = (v, fallback, lo, hi) => Number.isFinite(Number(v)) ? Math.max(lo, Math.min(hi, Number(v))) : fallback;
  const pad = n => String(n).padStart(3, '0');
  function urlFor(id, edition, fallback = false) {
    const folder = `sprites/pokemon/versions/generation-i/${edition}/${id}.png`;
    return fallback ? `https://raw.githubusercontent.com/PokeAPI/sprites/master/${folder}`
      : `https://cdn.jsdelivr.net/gh/PokeAPI/sprites@master/${folder}`;
  }
  function loadSprite(id, edition) {
    const key = `${edition}:${id}`;
    if (cache.has(key)) return cache.get(key);
    const promise = new Promise((resolve, reject) => {
      const image = new Image();
      image.crossOrigin = 'anonymous';
      let source = 0;
      image.onload = () => resolve(image);
      image.onerror = () => {
        if (!source++) image.src = urlFor(id, edition, true);
        else reject(new Error(`Could not load #${pad(id)} (${NAMES[id - 1]}). Check your connection or try a different sprite edition.`));
      };
      image.src = urlFor(id, edition);
    });
    cache.set(key, promise);
    promise.catch(() => { if (cache.get(key) === promise) cache.delete(key); });
    return promise;
  }
  function values() {
    return {
      head: Number(refs.head.value), body: Number(refs.body.value),
      edition: refs.edition.value, palette: refs.palette.value,
      headSize: Number(refs.size.value), splice: Number(refs.splice.value), smart: refs.smart.checked
    };
  }
  function nameFor(a, b) {
    const head = NAMES[a - 1].replace(/[^a-zA-Z]/g, '');
    const body = NAMES[b - 1].replace(/[^a-zA-Z]/g, '');
    if (a === b) return head;
    const splitHead = Math.max(2, Math.min(head.length - 1, Math.ceil(head.length * .53)));
    const splitBody = Math.max(1, Math.min(body.length - 1, Math.floor(body.length * .49)));
    const prefix = head.slice(0, splitHead);
    const suffix = body.slice(splitBody).toLowerCase();
    return (prefix + suffix).replace(/([a-z])\1{2,}/gi, '$1$1');
  }
  function updateChrome(v) {
    $('head-id').textContent = `#${pad(v.head)}`;
    $('body-id').textContent = `#${pad(v.body)}`;
    $('result-number').textContent = `NO. ${pad(v.head)} × ${pad(v.body)}`;
    refs.name.textContent = nameFor(v.head, v.body);
    refs.details.textContent = `${NAMES[v.head - 1]} head · ${NAMES[v.body - 1]} body`;
    $('head-size-value').textContent = `${v.headSize}%`;
    $('splice-value').textContent = `${v.splice}%`;
    for (const [preview, id] of [[refs.headPreview, v.head], [refs.bodyPreview, v.body]]) {
      preview.dataset.fallback = '0';
      preview.onerror = () => {
        if (preview.dataset.fallback !== '1') {
          preview.dataset.fallback = '1';
          preview.src = urlFor(id, v.edition, true);
        }
      };
      preview.src = urlFor(id, v.edition);
    }
    refs.headPreview.alt = `${NAMES[v.head - 1]} original Generation I sprite`;
    refs.bodyPreview.alt = `${NAMES[v.body - 1]} original Generation I sprite`;
  }
  function setStatus(message, error = false) {
    refs.status.textContent = message;
    refs.status.style.color = error ? '#ff9d91' : '';
  }
  function saveHistory(v) {
    const key = JSON.stringify(v);
    const png = refs.canvas.toDataURL('image/png');
    history = [{ ...v, key, png }, ...history.filter(item => item.key !== key)].slice(0, 12);
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(history)); }
    catch (_) { /* Private browsing / storage quota; current session still works. */ }
    renderHistory();
  }
  function renderHistory() {
    refs.recent.replaceChildren();
    if (!history.length) {
      const div = document.createElement('div');
      div.className = 'recent-empty';
      div.textContent = 'Your experiments will appear here.';
      refs.recent.appendChild(div);
      return;
    }
    for (const item of history) {
      if (!(item.head >= 1 && item.head <= 151 && item.body >= 1 && item.body <= 151) || typeof item.png !== 'string') continue;
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'recent-item';
      button.title = `Restore ${NAMES[item.head - 1]} + ${NAMES[item.body - 1]}`;
      const frame = document.createElement('div');
      frame.className = 'recent-thumb';
      const image = document.createElement('img');
      image.src = item.png;
      image.alt = '';
      frame.appendChild(image);
      const title = document.createElement('span');
      title.textContent = nameFor(item.head, item.body);
      button.append(frame, title);
      button.addEventListener('click', () => { applyValues(item); scheduleRender(); window.scrollTo({top:0,behavior:'smooth'}); });
      refs.recent.appendChild(button);
    }
  }
  function applyValues(v) {
    refs.head.value = String(numeric(v.head, 25, 1, 151));
    refs.body.value = String(numeric(v.body, 1, 1, 151));
    if (['red-blue', 'yellow', 'red-green-japan'].includes(v.edition)) refs.edition.value = v.edition;
    if (['original', 'gameboy', 'blue', 'red', 'sepia'].includes(v.palette)) refs.palette.value = v.palette;
    refs.size.value = String(numeric(v.headSize, 100, 65, 150));
    refs.splice.value = String(numeric(v.splice, 46, 30, 64));
    refs.smart.checked = v.smart !== false && v.smart !== 'false' && v.smart !== '0';
  }
  function scheduleRender() {
    clearTimeout(timer);
    const v = values();
    updateChrome(v);
    const token = ++currentRender;
    refs.download.disabled = true;
    refs.loader.hidden = false;
    refs.error.hidden = true;
    setStatus('Splicing specimens…');
    timer = setTimeout(() => draw(v, token), 55);
  }
  async function draw(v, token) {
    try {
      const [head, body] = await Promise.all([loadSprite(v.head, v.edition), loadSprite(v.body, v.edition)]);
      if (token !== currentRender) return;
      window.FusionEngine.fuse(head, body, refs.canvas, v);
      if (token !== currentRender) return;
      isReady = true;
      refs.download.disabled = false;
      refs.loader.hidden = true;
      setStatus('✓ Fusion complete · generated locally in your browser');
      refs.error.hidden = true;
      updateUrl(v);
      saveHistory(v);
    } catch (error) {
      if (token !== currentRender) return;
      isReady = false;
      refs.loader.hidden = true;
      refs.download.disabled = true;
      refs.error.hidden = false;
      refs.error.textContent = `Sprite loading failed: ${error.message}`;
      setStatus('Unable to complete fusion', true);
    }
  }
  function updateUrl(v) {
    if (window.location.protocol === 'file:') return;
    const params = new URLSearchParams();
    params.set('head', String(v.head)); params.set('body', String(v.body));
    if (v.edition !== 'red-blue') params.set('edition', v.edition);
    if (v.palette !== 'original') params.set('palette', v.palette);
    if (v.headSize !== 100) params.set('size', String(v.headSize));
    if (v.splice !== 46) params.set('splice', String(v.splice));
    if (!v.smart) params.set('smart', '0');
    const url = `${location.pathname}?${params.toString()}${location.hash}`;
    try { historyApiReplace(url); } catch (_) { /* Embedded browsers can restrict URL changes. */ }
  }
  function historyApiReplace(url) { window.history.replaceState(null, '', url); }
  function exportPNG() {
    if (!isReady || refs.download.disabled) return;
    const big = document.createElement('canvas');
    big.width = 768; big.height = 768;
    const ctx = big.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(refs.canvas, 0, 0, 768, 768);
    const link = document.createElement('a');
    const v = values();
    link.href = big.toDataURL('image/png');
    link.download = `pokesplice-${pad(v.head)}-${pad(v.body)}.png`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setStatus('✓ Exported transparent 768 × 768 PNG');
  }
  function randomizedPair() {
    const a = Math.floor(Math.random() * 151) + 1;
    let b = Math.floor(Math.random() * 151) + 1;
    if (b === a) b = (b % 151) + 1;
    refs.head.value = String(a);
    refs.body.value = String(b);
    scheduleRender();
  }
  function populateNames() {
    for (let i = 0; i < NAMES.length; i++) {
      for (const select of [refs.head, refs.body]) {
        const option = new Option(`#${pad(i + 1)} ${NAMES[i]}`, String(i + 1));
        select.appendChild(option);
      }
    }
  }
  function restoreFromUrl() {
    const query = new URLSearchParams(location.search);
    applyValues({
      head:query.get('head') ?? 25,body:query.get('body') ?? 1,
      edition:query.get('edition') ?? 'red-blue',palette:query.get('palette') ?? 'original',
      headSize:query.get('size') ?? 100,splice:query.get('splice') ?? 46,
      smart:query.get('smart') !== '0'
    });
  }
  async function copyShareLink() {
    if (location.protocol === 'file:') {
      setStatus('Host the folder online to get shareable fusion links.', true);
      return;
    }
    try {
      await navigator.clipboard.writeText(location.href);
      setStatus('✓ Fusion link copied to clipboard');
    } catch (_) {
      const temp = document.createElement('textarea');
      temp.value = location.href; document.body.appendChild(temp); temp.select();
      const ok = document.execCommand('copy'); temp.remove();
      setStatus(ok ? '✓ Fusion link copied' : 'Copy the URL from your address bar', !ok);
    }
  }
  function initialize() {
    populateNames();
    try {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      if (Array.isArray(stored)) history = stored.slice(0, 12);
    } catch (_) { history = []; }
    renderHistory();
    restoreFromUrl();
    for (const element of [refs.head, refs.body, refs.edition, refs.palette, refs.size, refs.splice, refs.smart]) {
      element.addEventListener('input', scheduleRender);
      if (element.tagName === 'SELECT') element.addEventListener('change', scheduleRender);
    }
    $('swap-btn').addEventListener('click', () => {
      const a = refs.head.value; refs.head.value = refs.body.value; refs.body.value = a;
      scheduleRender();
    });
    $('random-btn').addEventListener('click', randomizedPair);
    $('reset-btn').addEventListener('click', () => {
      refs.size.value = '100'; refs.splice.value = '46'; refs.smart.checked = true;
      scheduleRender();
    });
    $('clear-history').addEventListener('click', () => {
      history = [];
      try { localStorage.removeItem(STORAGE_KEY); } catch (_) {}
      renderHistory();
      setStatus('Recent fusion history cleared');
    });
    $('share-btn').addEventListener('click', copyShareLink);
    refs.download.addEventListener('click', exportPNG);
    window.addEventListener('popstate', () => {restoreFromUrl();scheduleRender();});
    scheduleRender();
  }
  initialize();
})();