(() => {
'use strict';

const $ce = (id) => document.getElementById(id);

const TYPE_META = {
  thorn: { label: 'Thorn', color: '#c0392b' },
  bloom: { label: 'Bloom', color: '#ff8fb3' },
  guard: { label: 'Guard', color: '#4d4d4d' },
  root: { label: 'Root', color: '#5b8f48' },
};

const FLAG_NAMES = {
  precision: '精准',
  exile: '放逐',
  sprout: '萌芽',
  symbiosis: '共生',
  rebound: '回转',
  copy: '副本',
  unique: '唯一',
  swift: '迅捷',
  magic_swift: '魔力迅捷',
  power: '威力',
  self_only: '不选择目标',
  indestructible: '不可摧毁',
  uncancellable: '不可取消',
  sublime: '崇高',
  team_limited: '队伍限定',
  team_unique: '队伍独一',
  infinite_exclude: '无限火力移除',
};

let allCards = [];
let filteredCards = [];
let selectedCardId = '';
let busy = false;
let sheetPreviewActive = false;
const assetDataUrlCache = new Map();

function escapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function setStatus(text, isError = false) {
  const line = $ce('status-line');
  if (!line) return;
  line.textContent = text || '';
  line.style.color = isError ? '#c0392b' : '#6f7787';
}

async function fetchJson(url, options = {}) {
  const resp = await fetch(url, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const text = await resp.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (err) {
    throw new Error(text.slice(0, 240) || '响应不是 JSON');
  }
  if (!resp.ok || data.success === false) {
    throw new Error(data.error || `请求失败 ${resp.status}`);
  }
  return data;
}

function cardName(card) {
  return card.name_cn || card.name_en || card.id || '';
}

function cardEnglish(card) {
  return card.name_en && card.name_en !== cardName(card) ? card.name_en : '';
}

function cardModName(card) {
  return card.source_mod_name_cn || card.source_mod_name_en || card.source_mod_name || card.source_mod_filename || 'Unknown Mod';
}

function typeColor(card) {
  return (TYPE_META[String(card.card_type || '').toLowerCase()] || TYPE_META.thorn).color;
}

function safeFilename(value) {
  return String(value || 'card')
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/\s+/g, '_')
    .slice(0, 140);
}

function flagLabel(flag) {
    const raw = String(flag || '').replace(/^tag_/, '').replace(/^flag_/, '');
    return FLAG_NAMES[raw] || raw;
}

function isExportableCard(card) {
  const id = String(card?.id || '').toLowerCase();
  return id && !['error', 'gtn:error', 'system:error'].includes(id);
}

function renderCard(card, options = {}) {
  const width = Math.max(240, Number($ce('card-width')?.value || 744));
  const showArt = options.showArt ?? $ce('show-art')?.checked;
  const showEnglish = options.showEnglish ?? $ce('show-english')?.checked;
  const lang = localStorage.getItem('gtn_lang') || 'zh';
  document.documentElement.lang = lang === 'zh-CN' ? 'zh' : lang;
  const renderer = window.GTN_CARD_RENDERER;
  if (!renderer || typeof renderer.createCardElement !== 'function') {
    const fallback = document.createElement('div');
    fallback.textContent = cardName(card);
    return fallback;
  }
  renderer.setOptions?.({
    showEnglish,
    showImages: showArt,
    lang,
  });
  const el = renderer.createCardElement({
    def_id: card.id,
    instance_flags: [],
    disabled_flags: [],
    fusion_level: 1,
    fission_level: 1,
  }, { small: false, disableIntro: true });
  el.style.setProperty('--card-w', `${width}px`);
  return el;
}

function updatePreview() {
  sheetPreviewActive = false;
  const wrap = $ce('card-preview-wrap');
  if (!wrap) return;
  wrap.innerHTML = '';
  const card = allCards.find(c => c.id === selectedCardId) || filteredCards[0];
  if (!card) {
    wrap.textContent = '没有卡牌';
    return;
  }
  selectedCardId = card.id;
  wrap.appendChild(renderCard(card));
  const maxPreviewWidth = Math.max(260, window.innerWidth - 720);
  const width = Math.max(240, Number($ce('card-width')?.value || 744));
  const previewScale = Math.min(1, maxPreviewWidth / width, (window.innerHeight - 88) / Math.round(width * 1.403225806));
  const manualScale = Math.max(0.25, Math.min(2, Number($ce('preview-scale')?.value || 100) / 100));
  document.documentElement.style.setProperty('--scale', String(Math.max(0.12, previewScale * manualScale)));
}

function passesFilter(card) {
  const q = String($ce('search-input')?.value || '').trim().toLowerCase();
  const mod = String($ce('mod-filter')?.value || '');
  if (mod && cardModName(card) !== mod) return false;
  if (!q) return true;
  return [
    card.id,
    card.name_cn,
    card.name_en,
    card.effect_text,
    card.description,
    cardModName(card),
  ].some(value => String(value || '').toLowerCase().includes(q));
}

function renderList() {
  const list = $ce('card-list');
  if (!list) return;
  filteredCards = allCards.filter(isExportableCard).filter(passesFilter);
  $ce('list-count').textContent = `${filteredCards.length} 张`;
  if (!filteredCards.some(c => c.id === selectedCardId)) selectedCardId = filteredCards[0]?.id || '';
  list.innerHTML = '';
  filteredCards.forEach(card => {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = `card-row ${card.id === selectedCardId ? 'is-selected' : ''}`;
    row.innerHTML = `
      <span class="card-row-type" style="--type-color:${typeColor(card)}"></span>
      <span class="card-row-name">
        <strong>${escapeHtml(cardName(card))}</strong>
        <span>${escapeHtml(cardEnglish(card) || card.id)} · ${escapeHtml(cardModName(card))}</span>
      </span>
      <span class="card-row-cost">${Number(card.cost_e || 0)}E/${Number(card.cost_m || 0)}M</span>
    `;
    row.addEventListener('click', () => {
      selectedCardId = card.id;
      renderList();
      updatePreview();
    });
    list.appendChild(row);
  });
  updatePreview();
}

function populateMods() {
  const select = $ce('mod-filter');
  if (!select) return;
  const mods = Array.from(new Set(allCards.map(cardModName))).sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'));
  select.innerHTML = `<option value="">全部模组</option>${mods.map(mod => `<option value="${escapeHtml(mod)}">${escapeHtml(mod)}</option>`).join('')}`;
}

async function loadCards() {
  setStatus('加载卡牌中...');
  const data = await fetchJson('/api/card-exporter/cards');
  allCards = (Array.isArray(data.cards) ? data.cards : []).filter(isExportableCard);
  window.GTN_CARD_RENDERER?.setCardDefs?.(Object.fromEntries(allCards.map(card => [card.id, card])));
  populateMods();
  renderList();
  setStatus(`已加载 ${allCards.length} 张卡。`);
}

function collectCssText() {
  let css = '';
  for (const sheet of Array.from(document.styleSheets)) {
    try {
      for (const rule of Array.from(sheet.cssRules || [])) css += `${rule.cssText}\n`;
    } catch (err) {
      // Ignore cross-origin stylesheets; this page only needs its own CSS.
    }
  }
  return css;
}

function sanitizeCssForSvg(css) {
  return String(css || '')
    .replace(/@charset[^;]+;/gi, '')
    .replace(/@import[^;]+;/gi, '')
    .replace(/font-display\s*:\s*optional\s*;/gi, 'font-display: block;')
    .replace(/\/\*# sourceMappingURL=[\s\S]*?\*\//g, '')
    .replace(/<\/style/gi, '<\\/style');
}

function absolutizeUrl(value) {
  if (!value || value.startsWith('data:') || value.startsWith('blob:')) return value;
  try {
    return new URL(value, window.location.origin).href;
  } catch (err) {
    return value;
  }
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

async function fetchAsDataUrl(value) {
  const absolute = absolutizeUrl(value);
  if (!absolute || absolute.startsWith('data:')) return absolute;
  if (assetDataUrlCache.has(absolute)) return assetDataUrlCache.get(absolute);
  const promise = fetch(absolute, { credentials: 'same-origin' })
    .then(resp => {
      if (!resp.ok) throw new Error(`asset ${resp.status}`);
      return resp.blob();
    })
    .then(blobToDataUrl)
    .catch(() => absolute);
  assetDataUrlCache.set(absolute, promise);
  return promise;
}

async function inlineFontUrls(css) {
  const source = String(css || '');
  const matches = Array.from(source.matchAll(/url\((['"]?)([^'")]+)\1\)/g));
  if (!matches.length) return source;
  const replacements = new Map();
  for (const match of matches) {
    const raw = match[2];
    const lower = raw.toLowerCase();
    if (
      raw.startsWith('data:')
      || (!lower.includes('/fonts/') && !lower.endsWith('.woff2') && !lower.endsWith('.woff') && !lower.endsWith('.ttf') && !lower.endsWith('.otf'))
    ) {
      continue;
    }
    replacements.set(raw, await fetchAsDataUrl(raw));
  }
  if (!replacements.size) return source;
  return source.replace(/url\((['"]?)([^'")]+)\1\)/g, (full, _quote, raw) => {
    const replacement = replacements.get(raw);
    return replacement ? `url("${replacement}")` : full;
  });
}

async function absolutizeCloneAssets(root) {
  for (const img of Array.from(root.querySelectorAll('img'))) {
    const src = img.getAttribute('src');
    if (src) img.setAttribute('src', await fetchAsDataUrl(src));
  }
  for (const node of Array.from(root.querySelectorAll('[style]'))) {
    const style = node.getAttribute('style') || '';
    let rewritten = style;
    const matches = Array.from(style.matchAll(/url\((['"]?)([^'")]+)\1\)/g));
    for (const match of matches) {
      const dataUrl = await fetchAsDataUrl(match[2]);
      rewritten = rewritten.replace(match[0], `url("${dataUrl}")`);
    }
    node.setAttribute('style', rewritten);
  }
}

async function waitForImages(root, timeoutMs = 5000) {
  const images = Array.from(root.querySelectorAll('img'));
  if (!images.length) return;
  await Promise.race([
    Promise.all(images.map(img => {
      if (img.complete) return Promise.resolve();
      return new Promise(resolve => {
        img.onload = resolve;
        img.onerror = resolve;
      });
    })),
    new Promise(resolve => setTimeout(resolve, timeoutMs)),
  ]);
}

async function waitForFonts() {
  if (document.fonts && document.fonts.ready) {
    await Promise.race([
      document.fonts.ready.catch(() => {}),
      new Promise(resolve => setTimeout(resolve, 1500)),
    ]);
  }
}

async function loadMainFontLikeGame() {
  if (!('FontFace' in window) || !document.fonts) return;
  try {
    const font = new FontFace('Kreadon', "url('/fonts/Kreadon-Regular.subset.woff2?v=2') format('woff2')", {
      weight: '400',
      style: 'normal',
    });
    const loaded = await font.load();
    document.fonts.add(loaded);
    document.documentElement.classList.add('fonts-loaded-main');
  } catch (err) {
    // Match the main game boot path: keep the fallback font chain if loading fails.
  }
}

async function nodeToPng(node, filename, pixelRatio = 3) {
  await waitForFonts();
  await waitForImages(node);
  const rect = node.getBoundingClientRect();
  const width = Math.ceil(rect.width);
  const height = Math.ceil(rect.height);
  if (!width || !height) throw new Error('导出区域为空');
  const clone = node.cloneNode(true);
  clone.setAttribute('xmlns', 'http://www.w3.org/1999/xhtml');
  clone.style.margin = '0';
  clone.style.transform = 'none';
  await absolutizeCloneAssets(clone);
  const css = await inlineFontUrls(sanitizeCssForSvg(collectCssText()));
  const wrapper = document.createElement('html');
  wrapper.setAttribute('xmlns', 'http://www.w3.org/1999/xhtml');
  wrapper.setAttribute('lang', document.documentElement.getAttribute('lang') || 'zh');
  const theme = document.documentElement.getAttribute('data-theme');
  const uiStyle = document.documentElement.getAttribute('data-ui-style');
  if (theme) wrapper.setAttribute('data-theme', theme);
  if (uiStyle) wrapper.setAttribute('data-ui-style', uiStyle);
  wrapper.className = document.documentElement.className || '';
  const head = document.createElement('head');
  const style = document.createElement('style');
  style.textContent = css;
  head.appendChild(style);
  const body = document.createElement('body');
  body.style.margin = '0';
  body.appendChild(clone);
  wrapper.appendChild(head);
  wrapper.appendChild(body);
  const html = new XMLSerializer().serializeToString(wrapper);
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
      <foreignObject width="100%" height="100%">${html}</foreignObject>
    </svg>
  `;
  const url = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  try {
    const img = await new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error('图片渲染失败'));
      image.src = url;
    });
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(width * pixelRatio));
    canvas.height = Math.max(1, Math.round(height * pixelRatio));
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingQuality = 'high';
    ctx.scale(pixelRatio, pixelRatio);
    ctx.drawImage(img, 0, 0);
    const png = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
    if (!png) throw new Error('PNG 生成失败');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(png);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 3000);
  } finally {}
}

async function exportCard(card) {
  const host = document.createElement('div');
  host.style.position = 'fixed';
  host.style.left = '-100000px';
  host.style.top = '0';
  host.style.width = 'max-content';
  host.appendChild(renderCard(card));
  document.body.appendChild(host);
  await waitForImages(host);
  const ratio = Math.max(1, Number($ce('pixel-ratio')?.value || 3));
  const countPart = $ce('show-count')?.checked ? `_x${Number(card.count || 0)}` : '';
  const filename = `${safeFilename(cardModName(card))}_${safeFilename(card.name_en || card.id)}_${safeFilename(card.name_cn || '')}${countPart}.png`;
  try {
    await nodeToPng(host.firstElementChild, filename, ratio);
  } finally {
    host.remove();
  }
}

async function exportCurrent() {
  const card = allCards.find(c => c.id === selectedCardId);
  if (!card || busy) return;
  busy = true;
  setButtonsDisabled(true);
  try {
    setStatus(`导出 ${cardName(card)}...`);
    await exportCard(card);
    setStatus(`已导出 ${cardName(card)}。`);
  } catch (err) {
    setStatus(err.message || String(err), true);
  } finally {
    busy = false;
    setButtonsDisabled(false);
  }
}

async function exportFiltered() {
  if (busy || !filteredCards.length) return;
  busy = true;
  setButtonsDisabled(true);
  try {
    const cards = filteredCards.slice();
    for (let i = 0; i < cards.length; i += 1) {
      if (!busy) break;
      const card = cards[i];
      setStatus(`导出 ${i + 1}/${cards.length}: ${cardName(card)}`);
      await exportCard(card);
      await new Promise(resolve => setTimeout(resolve, 180));
    }
    setStatus(`已导出 ${cards.length} 张。浏览器可能会询问是否允许多文件下载。`);
  } catch (err) {
    setStatus(err.message || String(err), true);
  } finally {
    busy = false;
    setButtonsDisabled(false);
  }
}

function setButtonsDisabled(disabled) {
  ['export-current-btn', 'export-filtered-btn', 'preview-sheet-btn', 'export-sheet-btn', 'reload-btn'].forEach(id => {
    const btn = $ce(id);
    if (btn) btn.disabled = disabled;
  });
}

function buildSheetNode(cards = filteredCards) {
  const columns = Math.max(1, Math.min(8, Number($ce('sheet-columns')?.value || 3)));
  const gap = Math.max(0, Math.min(80, Number($ce('sheet-gap')?.value || 12)));
  const width = Math.max(180, Number($ce('sheet-card-width')?.value || 360));
  const sheet = document.createElement('div');
  sheet.className = 'export-sheet';
  sheet.style.gridTemplateColumns = `repeat(${columns}, max-content)`;
  sheet.style.gap = `${gap}px`;
  const oldWidth = $ce('card-width')?.value;
  if ($ce('card-width')) $ce('card-width').value = String(width);
  cards.forEach(card => sheet.appendChild(renderCard(card)));
  if ($ce('card-width')) $ce('card-width').value = oldWidth;
  return sheet;
}

function previewSheet() {
  const wrap = $ce('card-preview-wrap');
  if (!wrap || !filteredCards.length) return;
  sheetPreviewActive = true;
  wrap.innerHTML = '';
  wrap.appendChild(buildSheetNode());
  const manualScale = Math.max(0.25, Math.min(2, Number($ce('preview-scale')?.value || 100) / 100));
  document.documentElement.style.setProperty('--scale', String(manualScale));
  setStatus(`正在预览拼版：${filteredCards.length} 张。`);
}

async function exportSheet() {
  if (busy || !filteredCards.length) return;
  busy = true;
  setButtonsDisabled(true);
  const host = document.createElement('div');
  host.className = 'sheet-export-host';
  host.appendChild(buildSheetNode(filteredCards.slice()));
  document.body.appendChild(host);
  try {
    setStatus(`导出拼版 ${filteredCards.length} 张...`);
    const ratio = Math.max(1, Number($ce('pixel-ratio')?.value || 3));
    const mod = String($ce('mod-filter')?.value || '全部模组');
    await nodeToPng(host.firstElementChild, `${safeFilename(mod)}_cards_sheet_x${filteredCards.length}.png`, ratio);
    setStatus(`已导出拼版 ${filteredCards.length} 张。`);
  } catch (err) {
    setStatus(err.message || String(err), true);
  } finally {
    host.remove();
    busy = false;
    setButtonsDisabled(false);
  }
}

async function login(event) {
  event.preventDefault();
  const input = $ce('exporter-key');
  const error = $ce('login-error');
  error.textContent = '';
  try {
    await fetchJson('/api/card-exporter/login', {
      method: 'POST',
      body: JSON.stringify({ key: input.value }),
    });
    showExporter();
    await loadCards();
  } catch (err) {
    error.textContent = err.message || '密码错误';
  }
}

async function logout() {
  await fetchJson('/api/card-exporter/logout', { method: 'POST', body: '{}' }).catch(() => {});
  $ce('exporter-panel').classList.add('hidden');
  $ce('login-panel').classList.remove('hidden');
}

function showExporter() {
  $ce('login-panel').classList.add('hidden');
  $ce('exporter-panel').classList.remove('hidden');
}

function bindEvents() {
  $ce('login-form')?.addEventListener('submit', login);
  $ce('logout-btn')?.addEventListener('click', logout);
  $ce('reload-btn')?.addEventListener('click', () => loadCards().catch(err => setStatus(err.message, true)));
  $ce('export-current-btn')?.addEventListener('click', exportCurrent);
  $ce('export-filtered-btn')?.addEventListener('click', exportFiltered);
  $ce('preview-sheet-btn')?.addEventListener('click', previewSheet);
  $ce('export-sheet-btn')?.addEventListener('click', exportSheet);
  ['search-input', 'mod-filter'].forEach(id => $ce(id)?.addEventListener('input', () => {
    sheetPreviewActive = false;
    renderList();
  }));
  ['card-width', 'pixel-ratio', 'preview-scale', 'show-art', 'show-english'].forEach(id => $ce(id)?.addEventListener('input', () => {
    if (sheetPreviewActive) previewSheet();
    else updatePreview();
  }));
  ['sheet-columns', 'sheet-gap', 'sheet-card-width'].forEach(id => $ce(id)?.addEventListener('input', () => {
    if (sheetPreviewActive) previewSheet();
  }));
  window.addEventListener('resize', updatePreview);
}

async function init() {
  await loadMainFontLikeGame();
  bindEvents();
  try {
    const me = await fetchJson('/api/card-exporter/me');
    if (me.authenticated) {
      showExporter();
      await loadCards();
    } else {
      $ce('login-panel').classList.remove('hidden');
    }
  } catch (err) {
    $ce('login-panel').classList.remove('hidden');
  }
}

init();

})();
