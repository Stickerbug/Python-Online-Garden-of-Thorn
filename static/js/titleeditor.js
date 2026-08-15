(() => {
  'use strict';

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const clone = value => JSON.parse(JSON.stringify(value));
  const app = $('#title-editor-app');
  if (!app) return;

  const COLOR_TOKENS = {
    thorn: '#C0392B', bloom: '#1ABC9C', root: '#8D6E63', guard: '#2980B9',
    curse: '#7650A8', infect: '#4F9B57', health: '#3FAE62', elixir: '#65B96F',
    energy: '#E2B530', magic: '#3478D4', damage: '#D74646', electric: '#E2B530',
    poison: '#8A4FA7', fire: '#E15A36', armor: '#5B84A7', precision: '#D4AC0D',
    banish: '#6E7781', indestructible: '#D4AC0D', critical: '#D4AC0D',
    primary: '#7EEF6D', common: '#7EEF6D', unusual: '#FFE65D', rare: '#4D52E3',
    epic: '#861FDE', legendary: '#DE1F1F', mythic: '#1FDBDE', ultra: '#FF2B75',
    super: '#2BFFA3', omega: '#F329D9', eternal: '#EEEEEE', unique: '#555555',
    milestone: '#5AA469', hidden: '#7257A8', admin: '#D34C4C', neutral: '#718078',
    spectator: '#8A9690',
  };
  const RAINBOW = ['#FF3B30', '#FF9500', '#FFCC00', '#34C759', '#00B7C7', '#3478F6', '#7857D8', '#FF2D96'];
  const SEGMENT_ID_PATTERN = /^[a-zA-Z0-9_.:-]{1,40}$/;
  const TITLE_ID_PATTERN = /^[a-zA-Z0-9_.:-]{1,64}$/;

  const state = {
    csrf: '',
    permissions: { canEdit: false, canPublish: false, canRollback: false },
    actor: null,
    liveCatalog: { schema_version: 1, titles: [] },
    catalog: { schema_version: 1, titles: [] },
    baseRevisionId: null,
    currentRevision: null,
    history: [],
    selectedId: '',
    selectedColor: null,
    previewTheme: 'light',
    serverDiff: null,
    hasServerDraft: false,
    staleDraft: false,
    savedFingerprint: '',
    undo: [],
    redo: [],
    lastHistoryKey: '',
    lastHistoryAt: 0,
    saveTimer: null,
    saveRequest: 0,
    saving: false,
    confirmAction: null,
    createMode: 'create',
    toastTimer: null,
    loading: true,
  };

  const refs = {
    alert: $('#te-alert'),
    revision: $('#te-revision'),
    integrity: $('#te-integrity'),
    saveState: $('#te-save-state'),
    undo: $('#te-undo'),
    redo: $('#te-redo'),
    publish: $('#te-publish'),
    discard: $('#te-discard'),
    titleList: $('#te-title-list'),
    titleCount: $('#te-title-count'),
    search: $('#te-search'),
    filter: $('#te-filter-status'),
    empty: $('#te-empty'),
    editor: $('#te-editor'),
    editingName: $('#te-editing-name'),
    editingId: $('#te-editing-id'),
    active: $('#te-active'),
    sourceType: $('#te-source-type'),
    sourceRef: $('#te-source-ref'),
    priceFree: $('#te-price-free'),
    pricePaid: $('#te-price-paid'),
    shopWeight: $('#te-shop-weight'),
    purchasable: $('#te-purchasable'),
    segments: $('#te-segments'),
    markup: $('#te-markup'),
    markupError: $('#te-markup-error'),
    preview: $('#te-preview'),
    previewTitle: $('#te-preview-title'),
    diff: $('#te-diff-summary'),
    colorControls: $('#te-color-controls'),
    colorTarget: $('#te-color-target'),
    colorPicker: $('#te-color-picker'),
    colorValue: $('#te-color-value'),
    colorToken: $('#te-color-token'),
    red: $('#te-r'), green: $('#te-g'), blue: $('#te-b'),
    hue: $('#te-h'), saturation: $('#te-s'), value: $('#te-v'),
    alpha: $('#te-alpha'), alphaValue: $('#te-alpha-value'),
    helpDialog: $('#te-help-dialog'),
    historyDialog: $('#te-history-dialog'),
    historyList: $('#te-history-list'),
    confirmDialog: $('#te-confirm-dialog'),
    confirmKicker: $('#te-confirm-kicker'),
    confirmTitle: $('#te-confirm-title'),
    confirmBody: $('#te-confirm-body'),
    confirmMessageWrap: $('#te-confirm-message-wrap'),
    confirmMessage: $('#te-confirm-message'),
    confirmPhraseWrap: $('#te-confirm-phrase-wrap'),
    confirmPhraseLabel: $('#te-confirm-phrase-label'),
    confirmPhrase: $('#te-confirm-phrase'),
    confirmSubmit: $('#te-confirm-submit'),
    createDialog: $('#te-create-dialog'),
    createTitle: $('#te-create-title'),
    newId: $('#te-new-id'),
    newName: $('#te-new-name'),
    createError: $('#te-create-error'),
    toast: $('#te-toast'),
  };

  function fingerprint(value) {
    return JSON.stringify(value);
  }

  function make(tag, className = '', text = '') {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== '') node.textContent = text;
    return node;
  }

  function showToast(message, isError = false) {
    window.clearTimeout(state.toastTimer);
    refs.toast.textContent = String(message || '');
    refs.toast.classList.toggle('is-error', Boolean(isError));
    refs.toast.classList.remove('hidden');
    state.toastTimer = window.setTimeout(() => refs.toast.classList.add('hidden'), 3200);
  }

  function setAlert(message = '', kind = '') {
    refs.alert.textContent = message;
    refs.alert.classList.toggle('hidden', !message);
    refs.alert.dataset.kind = kind;
  }

  function setSaveState(message, isError = false) {
    refs.saveState.textContent = message || '';
    refs.saveState.classList.toggle('is-error', Boolean(isError));
  }

  async function api(url, options = {}) {
    const headers = new Headers(options.headers || {});
    if (options.body != null && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
    if (state.csrf && options.method && options.method !== 'GET') headers.set('X-Title-Editor-CSRF', state.csrf);
    const response = await fetch(url, { credentials: 'same-origin', ...options, headers });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.success === false) {
      const error = new Error(payload.error || `请求失败（${response.status}）`);
      error.status = response.status;
      throw error;
    }
    return payload;
  }

  function selectedTitle() {
    return state.catalog.titles.find(item => item.id === state.selectedId) || null;
  }

  function titleColorCss(value) {
    const key = String(value || '').trim();
    return COLOR_TOKENS[key.toLowerCase()] || (/^#[0-9a-f]{6}(?:[0-9a-f]{2})?$/i.test(key) ? key : COLOR_TOKENS.neutral);
  }

  function normalizeAngle(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return 90;
    return Math.round((((number % 360) + 360) % 360) * 1000) / 1000;
  }

  function clamp(value, minimum, maximum) {
    return Math.min(maximum, Math.max(minimum, Number(value) || 0));
  }

  function colorToRgba(value) {
    let color = titleColorCss(value);
    if (!/^#[0-9a-f]{6}(?:[0-9a-f]{2})?$/i.test(color)) color = '#718078';
    return {
      r: parseInt(color.slice(1, 3), 16),
      g: parseInt(color.slice(3, 5), 16),
      b: parseInt(color.slice(5, 7), 16),
      a: color.length === 9 ? parseInt(color.slice(7, 9), 16) / 255 : 1,
    };
  }

  function rgbaToHex({ r, g, b, a = 1 }, includeAlpha = a < 0.999) {
    const byte = number => Math.round(clamp(number, 0, 255)).toString(16).padStart(2, '0').toUpperCase();
    const base = `#${byte(r)}${byte(g)}${byte(b)}`;
    return includeAlpha ? `${base}${byte(clamp(a, 0, 1) * 255)}` : base;
  }

  function rgbToHsv({ r, g, b }) {
    const red = r / 255;
    const green = g / 255;
    const blue = b / 255;
    const max = Math.max(red, green, blue);
    const min = Math.min(red, green, blue);
    const delta = max - min;
    let hue = 0;
    if (delta) {
      if (max === red) hue = 60 * (((green - blue) / delta) % 6);
      else if (max === green) hue = 60 * ((blue - red) / delta + 2);
      else hue = 60 * ((red - green) / delta + 4);
    }
    return { h: Math.round((hue + 360) % 360), s: Math.round((max ? delta / max : 0) * 100), v: Math.round(max * 100) };
  }

  function hsvToRgb(h, s, v) {
    const hue = ((Number(h) % 360) + 360) % 360;
    const saturation = clamp(s, 0, 100) / 100;
    const value = clamp(v, 0, 100) / 100;
    const chroma = value * saturation;
    const x = chroma * (1 - Math.abs((hue / 60) % 2 - 1));
    const m = value - chroma;
    let channels = [0, 0, 0];
    if (hue < 60) channels = [chroma, x, 0];
    else if (hue < 120) channels = [x, chroma, 0];
    else if (hue < 180) channels = [0, chroma, x];
    else if (hue < 240) channels = [0, x, chroma];
    else if (hue < 300) channels = [x, 0, chroma];
    else channels = [chroma, 0, x];
    return { r: Math.round((channels[0] + m) * 255), g: Math.round((channels[1] + m) * 255), b: Math.round((channels[2] + m) * 255) };
  }

  function normalizeColorInput(raw) {
    const text = String(raw || '').trim();
    const token = text.toLowerCase();
    if (COLOR_TOKENS[token]) return token;
    const shortHex = text.match(/^#([0-9a-f]{3})([0-9a-f])?$/i);
    if (shortHex) {
      const rgb = shortHex[1].split('').map(ch => ch + ch).join('');
      const alpha = shortHex[2] ? shortHex[2] + shortHex[2] : '';
      return `#${rgb}${alpha}`.toUpperCase();
    }
    const fullHex = text.match(/^#([0-9a-f]{6})([0-9a-f]{2})?$/i);
    if (fullHex) return `#${fullHex[1]}${fullHex[2] || ''}`.toUpperCase();
    const rgb = text.match(/^rgba?\s*\(\s*(\d{1,3})\s*[,;/]\s*(\d{1,3})\s*[,;/]\s*(\d{1,3})(?:\s*[,;/]\s*([\d.]+)%?)?\s*\)$/i);
    if (rgb) {
      const channels = rgb.slice(1, 4).map(Number);
      if (channels.some(value => value < 0 || value > 255)) return '';
      let alpha = 1;
      if (rgb[4] != null) alpha = text.includes(`${rgb[4]}%`) || Number(rgb[4]) > 1 ? Number(rgb[4]) / 100 : Number(rgb[4]);
      if (alpha < 0 || alpha > 1) return '';
      return rgbaToHex({ r: channels[0], g: channels[1], b: channels[2], a: alpha });
    }
    const hsv = text.match(/^hsva?\s*\(\s*([\d.+-]+)\s*[,;/]\s*([\d.]+)%?\s*[,;/]\s*([\d.]+)%?(?:\s*[,;/]\s*([\d.]+)%?)?\s*\)$/i);
    if (hsv) {
      const rgbValue = hsvToRgb(Number(hsv[1]), Number(hsv[2]), Number(hsv[3]));
      let alpha = 1;
      if (hsv[4] != null) alpha = text.includes(`${hsv[4]}%`) || Number(hsv[4]) > 1 ? Number(hsv[4]) / 100 : Number(hsv[4]);
      if (alpha < 0 || alpha > 1) return '';
      return rgbaToHex({ ...rgbValue, a: alpha });
    }
    return '';
  }

  function normalizePaint(paint) {
    if (!paint || typeof paint !== 'object') return { kind: 'solid', color: 'neutral' };
    const kind = String(paint.kind || 'solid').toLowerCase();
    if (kind === 'solid') return { kind, color: normalizeColorInput(paint.color) || 'neutral' };
    if (kind === 'gradient' || kind === 'rainbow') {
      const fallback = kind === 'rainbow' ? RAINBOW : ['#FF3344', '#3478F6'];
      const colors = (Array.isArray(paint.colors) ? paint.colors : fallback)
        .map(color => normalizeColorInput(color) || 'neutral').slice(0, 12);
      return { kind, angle: normalizeAngle(paint.angle), colors: colors.length >= 2 ? colors : fallback.slice() };
    }
    if (kind === 'theme') {
      return {
        kind,
        light: { kind: 'solid', color: normalizeColorInput(paint.light?.color) || '#FFFFFF' },
        dark: { kind: 'solid', color: normalizeColorInput(paint.dark?.color) || '#000000' },
      };
    }
    return { kind: 'solid', color: 'neutral' };
  }

  function paintFallbackColor(paint) {
    const normalized = normalizePaint(paint);
    if (normalized.kind === 'solid') return normalized.color;
    if (normalized.kind === 'theme') return normalized.light.color;
    return normalized.colors[0] || 'neutral';
  }

  function styleToMarkup(style) {
    return (style?.segments || []).map(segment => {
      const paint = normalizePaint(segment.paint);
      let tag = `color:${paint.color}`;
      if (paint.kind === 'gradient') tag = `gradient:${paint.angle}deg,${paint.colors.join('>')}`;
      if (paint.kind === 'rainbow') tag = `rainbow:${paint.angle}`;
      if (paint.kind === 'theme') tag = `theme:light=${paint.light.color};dark=${paint.dark.color}`;
      const id = String(segment.id || '').trim();
      return `{${tag}${id ? `|id=${id}` : ''}}${String(segment.text || '')}{/}`;
    }).join('');
  }

  function syncTitle(title) {
    if (!title) return;
    if (!title.style || !Array.isArray(title.style.segments)) title.style = { version: 1, segments: [] };
    title.style.version = 1;
    title.style.segments.forEach(segment => { segment.paint = normalizePaint(segment.paint); });
    title.name = title.style.segments.map(segment => String(segment.text || '')).join('');
    title.style_markup = styleToMarkup(title.style);
    title.color = paintFallbackColor(title.style.segments[0]?.paint);
  }

  function validateCatalog() {
    if (!Array.isArray(state.catalog.titles) || !state.catalog.titles.length) return '称号目录不能为空';
    const ids = new Set();
    for (const title of state.catalog.titles) {
      if (!TITLE_ID_PATTERN.test(String(title.id || ''))) return `称号 ID 无效：${title.id || '（空）'}`;
      if (ids.has(title.id)) return `称号 ID 重复：${title.id}`;
      ids.add(title.id);
      syncTitle(title);
      if (!title.name || title.name.length > 64) return `${title.id} 的名称应为 1 至 64 个字符`;
      if (!title.style.segments.length || title.style.segments.length > 24) return `${title.id} 的样式段数量无效`;
      const segmentIds = new Set();
      for (const segment of title.style.segments) {
        if (!segment.text) return `${title.id} 存在空白样式段`;
        if (/[{}]/.test(segment.text)) return `${title.id} 的文字不能包含 { 或 }`;
        if (!SEGMENT_ID_PATTERN.test(String(segment.id || ''))) return `${title.id} 的样式段 ID 无效`;
        if (segmentIds.has(segment.id)) return `${title.id} 的样式段 ID 重复：${segment.id}`;
        segmentIds.add(segment.id);
      }
    }
    return '';
  }

  function currentFingerprint() {
    state.catalog.titles.forEach(syncTitle);
    return fingerprint(state.catalog);
  }

  function isDirty() {
    return currentFingerprint() !== state.savedFingerprint;
  }

  function updateCommandState() {
    refs.undo.disabled = !state.undo.length;
    refs.redo.disabled = !state.redo.length;
    refs.discard.disabled = !state.hasServerDraft && fingerprint(state.catalog) === fingerprint(state.liveCatalog);
    refs.publish.hidden = !state.permissions.canPublish;
    refs.publish.disabled = !state.permissions.canPublish || state.staleDraft || (!state.hasServerDraft && !isDirty());
  }

  function scheduleSave() {
    window.clearTimeout(state.saveTimer);
    setSaveState('尚未保存');
    state.saveTimer = window.setTimeout(() => saveDraft(), 900);
  }

  function mutate(key, callback, render = 'summary') {
    const before = clone(state.catalog);
    const beforeFingerprint = fingerprint(before);
    callback();
    const title = selectedTitle();
    if (title) syncTitle(title);
    const afterFingerprint = fingerprint(state.catalog);
    if (beforeFingerprint === afterFingerprint) return;

    const now = Date.now();
    if (!(state.lastHistoryKey === key && now - state.lastHistoryAt < 750)) {
      state.undo.push(before);
      if (state.undo.length > 100) state.undo.shift();
    }
    state.lastHistoryKey = key;
    state.lastHistoryAt = now;
    state.redo = [];
    state.serverDiff = null;
    if (render === 'all') renderAll();
    else if (render === 'segments') {
      renderSegments();
      renderPreview();
      renderTitleList();
      renderDiff();
    } else {
      renderSelectedHeader();
      renderPreview();
      renderTitleList();
      renderDiff();
      refreshColorSwatches();
      refs.markup.value = title?.style_markup || '';
    }
    updateCommandState();
    scheduleSave();
  }

  function restoreCatalog(snapshot) {
    state.catalog = clone(snapshot);
    if (!state.catalog.titles.some(item => item.id === state.selectedId)) {
      state.selectedId = state.catalog.titles[0]?.id || '';
    }
    state.selectedColor = null;
    state.serverDiff = null;
    state.lastHistoryKey = '';
    renderAll();
    scheduleSave();
  }

  function undo() {
    if (!state.undo.length) return;
    window.clearTimeout(state.saveTimer);
    state.redo.push(clone(state.catalog));
    restoreCatalog(state.undo.pop());
  }

  function redo() {
    if (!state.redo.length) return;
    window.clearTimeout(state.saveTimer);
    state.undo.push(clone(state.catalog));
    restoreCatalog(state.redo.pop());
  }

  function paintPresentation(paint) {
    const normalized = normalizePaint(paint);
    if (normalized.kind === 'gradient' || normalized.kind === 'rainbow') {
      return { className: 'title-paint-gradient', properties: { '--title-paint-gradient': `linear-gradient(${normalized.angle}deg,${normalized.colors.map(titleColorCss).join(',')})` } };
    }
    if (normalized.kind === 'theme') {
      return { className: 'title-paint-theme', properties: { '--title-paint-light': titleColorCss(normalized.light.color), '--title-paint-dark': titleColorCss(normalized.dark.color) } };
    }
    return { className: 'title-paint-solid', properties: { color: titleColorCss(normalized.color) } };
  }

  function applyPaint(node, paint) {
    const presentation = paintPresentation(paint);
    node.classList.add(presentation.className, 'title-style-segment');
    Object.entries(presentation.properties).forEach(([name, value]) => node.style.setProperty(name, value));
  }

  function appendStyledTitle(parent, title, bracketed = true) {
    const segments = title?.style?.segments || [];
    if (bracketed) parent.append(document.createTextNode('['));
    segments.forEach(segment => {
      const span = make('span');
      span.textContent = String(segment.text || '');
      applyPaint(span, segment.paint);
      parent.append(span);
    });
    if (bracketed) parent.append(document.createTextNode('] '));
  }

  function renderPreview() {
    refs.preview.dataset.theme = state.previewTheme;
    refs.previewTitle.replaceChildren();
    const title = selectedTitle();
    if (title) appendStyledTitle(refs.previewTitle, title, true);
  }

  function renderTitleList() {
    const query = String(refs.search.value || '').trim().toLowerCase();
    const filter = refs.filter.value || 'all';
    const filtered = state.catalog.titles.filter(title => {
      if (query && !`${title.name} ${title.id}`.toLowerCase().includes(query)) return false;
      if (filter === 'active' && !title.active) return false;
      if (filter === 'inactive' && title.active) return false;
      if (filter === 'purchasable' && !(title.active && title.purchasable && Number(title.shop_weight) > 0)) return false;
      return true;
    });
    refs.titleCount.textContent = `${filtered.length}/${state.catalog.titles.length}`;
    refs.titleList.replaceChildren();
    const fragment = document.createDocumentFragment();
    filtered.forEach(title => {
      const row = make('button', 'te-title-row');
      row.type = 'button';
      row.dataset.titleId = title.id;
      row.classList.toggle('active', title.id === state.selectedId);
      row.classList.toggle('is-inactive', !title.active);
      const main = make('span', 'te-title-row-main');
      main.append(make('span', 'te-title-row-name', title.name || '未命名'));
      main.append(make('span', 'te-title-row-id', title.id));
      row.append(main);
      const badgeText = !title.active ? '下架' : title.purchasable && Number(title.shop_weight) > 0 ? '商店' : title.source_type || '称号';
      row.append(make('span', 'te-title-row-badge', badgeText));
      fragment.append(row);
    });
    if (!filtered.length) fragment.append(make('div', 'te-empty-list', '没有符合条件的称号'));
    refs.titleList.append(fragment);
  }

  function renderSelectedHeader() {
    const title = selectedTitle();
    refs.empty.classList.toggle('hidden', Boolean(title));
    refs.editor.classList.toggle('hidden', !title);
    if (!title) return;
    refs.editingName.textContent = title.name || '未命名';
    refs.editingId.textContent = title.id;
  }

  function fillEditorFields() {
    const title = selectedTitle();
    renderSelectedHeader();
    if (!title) return;
    refs.active.checked = Boolean(title.active);
    refs.sourceType.value = title.source_type || '';
    refs.sourceRef.value = title.source_ref || '';
    refs.priceFree.value = title.price_free == null ? '' : title.price_free;
    refs.pricePaid.value = title.price_paid == null ? '' : title.price_paid;
    refs.shopWeight.value = title.shop_weight == null ? 0 : title.shop_weight;
    refs.purchasable.checked = Boolean(title.purchasable);
    refs.markup.value = title.style_markup || styleToMarkup(title.style);
    refs.markupError.textContent = '';
  }

  function labelWithInput(labelText, input) {
    const label = make('label');
    label.append(make('span', '', labelText), input);
    return label;
  }

  function colorPathValue(segment, path) {
    return path.split('.').reduce((value, key) => value?.[/^\d+$/.test(key) ? Number(key) : key], segment.paint);
  }

  function setColorPathValue(segment, path, value) {
    const keys = path.split('.');
    let target = segment.paint;
    keys.slice(0, -1).forEach(key => { target = target[/^\d+$/.test(key) ? Number(key) : key]; });
    target[/^\d+$/.test(keys.at(-1)) ? Number(keys.at(-1)) : keys.at(-1)] = value;
  }

  function colorButton(index, path, labelText) {
    const title = selectedTitle();
    const segment = title.style.segments[index];
    const value = colorPathValue(segment, path);
    const button = make('button', 'te-color-chip');
    button.type = 'button';
    button.dataset.segmentIndex = String(index);
    button.dataset.colorPath = path;
    if (state.selectedColor?.segmentId === segment.id && state.selectedColor?.path === path) button.classList.add('active');
    const swatch = make('span', 'te-color-swatch');
    swatch.style.background = titleColorCss(value);
    button.append(swatch, make('span', '', `${labelText}: ${value}`));
    return button;
  }

  function renderPaintOptions(container, segment, index) {
    const paint = normalizePaint(segment.paint);
    segment.paint = paint;
    if (paint.kind === 'solid') {
      container.append(colorButton(index, 'color', '颜色'));
      return;
    }
    if (paint.kind === 'gradient') {
      const controls = make('div', 'te-gradient-controls');
      const angle = make('input', 'te-angle-input');
      angle.type = 'number';
      angle.value = String(paint.angle);
      angle.dataset.segmentIndex = String(index);
      controls.append(labelWithInput('角度', angle));
      paint.colors.forEach((color, colorIndex) => {
        controls.append(colorButton(index, `colors.${colorIndex}`, `色 ${colorIndex + 1}`));
        if (paint.colors.length > 2) {
          const remove = make('button', 'te-mini-remove', '×');
          remove.type = 'button';
          remove.title = `删除颜色 ${colorIndex + 1}`;
          remove.dataset.action = 'remove-stop';
          remove.dataset.segmentIndex = String(index);
          remove.dataset.stopIndex = String(colorIndex);
          controls.append(remove);
        }
      });
      if (paint.colors.length < 12) {
        const add = make('button', '', '添加颜色');
        add.type = 'button';
        add.dataset.action = 'add-stop';
        add.dataset.segmentIndex = String(index);
        controls.append(add);
      }
      container.append(controls);
      return;
    }
    if (paint.kind === 'rainbow') {
      const controls = make('div', 'te-gradient-controls');
      const angle = make('input', 'te-angle-input');
      angle.type = 'number';
      angle.value = String(paint.angle);
      angle.dataset.segmentIndex = String(index);
      controls.append(labelWithInput('彩虹角度', angle), make('span', 'te-paint-note', '彩虹色由游戏统一生成'));
      container.append(controls);
      return;
    }
    container.append(colorButton(index, 'light.color', '浅色主题'), colorButton(index, 'dark.color', '深色主题'));
  }

  function renderSegments() {
    refs.segments.replaceChildren();
    const title = selectedTitle();
    if (!title) return;
    title.style.segments.forEach((segment, index) => {
      const row = make('div', 'te-segment');
      row.dataset.segmentIndex = String(index);
      if (state.selectedColor?.segmentId === segment.id) row.classList.add('is-selected');
      const top = make('div', 'te-segment-top');
      const textInput = make('input', 'te-segment-text');
      textInput.value = segment.text || '';
      textInput.maxLength = 64;
      textInput.dataset.segmentIndex = String(index);
      const idInput = make('input', 'te-segment-id');
      idInput.value = segment.id || '';
      idInput.maxLength = 40;
      idInput.dataset.segmentIndex = String(index);
      const kind = make('select', 'te-paint-kind');
      kind.dataset.segmentIndex = String(index);
      [['solid', '纯色'], ['gradient', '渐变'], ['rainbow', '彩虹'], ['theme', '明暗主题色']].forEach(([value, label]) => {
        const option = make('option', '', label);
        option.value = value;
        option.selected = normalizePaint(segment.paint).kind === value;
        kind.append(option);
      });
      const remove = make('button', 'te-segment-remove', '×');
      remove.type = 'button';
      remove.title = '删除样式段';
      remove.dataset.action = 'remove-segment';
      remove.dataset.segmentIndex = String(index);
      remove.disabled = title.style.segments.length <= 1;
      top.append(labelWithInput('文字', textInput), labelWithInput('稳定段 ID', idInput), labelWithInput('样式', kind), remove);
      const options = make('div', 'te-paint-options');
      renderPaintOptions(options, segment, index);
      row.append(top, options);
      refs.segments.append(row);
    });
    syncColorControls();
  }

  function colorSelection() {
    const title = selectedTitle();
    if (!title || !state.selectedColor) return null;
    const index = title.style.segments.findIndex(item => item.id === state.selectedColor.segmentId);
    if (index < 0) return null;
    const segment = title.style.segments[index];
    const value = colorPathValue(segment, state.selectedColor.path);
    return { title, segment, index, value };
  }

  function syncColorControls() {
    const selection = colorSelection();
    refs.colorControls.classList.toggle('is-disabled', !selection);
    if (!selection) {
      refs.colorTarget.textContent = '请选择一个颜色';
      return;
    }
    const { segment, value } = selection;
    refs.colorTarget.textContent = `${segment.text || segment.id} · ${state.selectedColor.path}`;
    refs.colorValue.value = value;
    refs.colorToken.value = COLOR_TOKENS[String(value).toLowerCase()] ? String(value).toLowerCase() : '';
    const rgba = colorToRgba(value);
    const hsv = rgbToHsv(rgba);
    refs.colorPicker.value = rgbaToHex(rgba, false);
    refs.red.value = String(rgba.r);
    refs.green.value = String(rgba.g);
    refs.blue.value = String(rgba.b);
    refs.hue.value = String(hsv.h);
    refs.saturation.value = String(hsv.s);
    refs.value.value = String(hsv.v);
    refs.alpha.value = String(Math.round(rgba.a * 100));
    refs.alphaValue.value = `${Math.round(rgba.a * 100)}%`;
  }

  function refreshColorSwatches() {
    const title = selectedTitle();
    if (!title) return;
    $$('[data-color-path]', refs.segments).forEach(button => {
      const index = Number(button.dataset.segmentIndex);
      const segment = title.style.segments[index];
      if (!segment) return;
      const value = colorPathValue(segment, button.dataset.colorPath);
      const swatch = $('.te-color-swatch', button);
      const label = swatch?.nextElementSibling;
      if (swatch) swatch.style.background = titleColorCss(value);
      if (label) label.textContent = `${label.textContent.split(':')[0]}: ${value}`;
      button.classList.toggle('active', state.selectedColor?.segmentId === segment.id && state.selectedColor?.path === button.dataset.colorPath);
    });
    $$('.te-segment', refs.segments).forEach((row, index) => {
      row.classList.toggle('is-selected', title.style.segments[index]?.id === state.selectedColor?.segmentId);
    });
  }

  function setSelectedColor(value, key = 'color') {
    const normalized = normalizeColorInput(value);
    const selection = colorSelection();
    if (!selection || !normalized) {
      if (!normalized) showToast('无法识别该颜色值', true);
      syncColorControls();
      return;
    }
    mutate(`${key}:${selection.segment.id}:${state.selectedColor.path}`, () => {
      setColorPathValue(selection.segment, state.selectedColor.path, normalized);
    });
    syncColorControls();
  }

  function computeLocalDiff() {
    const live = new Map(state.liveCatalog.titles.map(item => [item.id, item]));
    const changes = [];
    state.catalog.titles.forEach(item => {
      const before = live.get(item.id);
      if (!before) changes.push({ id: item.id, name: item.name, added: true, deactivated: false });
      else if (fingerprint(before) !== fingerprint(item)) changes.push({ id: item.id, name: item.name, added: false, deactivated: Boolean(before.active && !item.active) });
    });
    return {
      changed_count: changes.length,
      added_count: changes.filter(item => item.added).length,
      deactivated_count: changes.filter(item => item.deactivated).length,
      affected_user_count: null,
      equipped_user_count: null,
      name_style_reset_count: null,
      changes,
    };
  }

  function renderDiff() {
    const diff = state.serverDiff || computeLocalDiff();
    refs.diff.replaceChildren();
    if (!diff.changed_count) {
      refs.diff.textContent = '暂无修改';
      return;
    }
    const grid = make('div', 'te-diff-grid');
    const metrics = [
      ['修改称号', diff.changed_count],
      ['新增', diff.added_count || 0],
      ['下架', diff.deactivated_count || 0],
      ['影响玩家', diff.affected_user_count == null ? '保存后计算' : diff.affected_user_count],
      ['佩戴中玩家', diff.equipped_user_count == null ? '保存后计算' : diff.equipped_user_count],
      ['昵称颜色重置', diff.name_style_reset_count == null ? '保存后计算' : diff.name_style_reset_count],
    ];
    metrics.forEach(([label, value]) => {
      const cell = make('div');
      cell.append(make('strong', '', String(value)), document.createTextNode(label));
      grid.append(cell);
    });
    refs.diff.append(grid);
  }

  function renderRevision() {
    const revision = state.currentRevision;
    refs.revision.textContent = revision ? `线上修订 #${revision.revision_id} · ${revision.sha256.slice(0, 10)}` : '尚无线上修订';
    refs.integrity.classList.toggle('is-ok', state.integrityOk === true);
    refs.integrity.classList.toggle('is-bad', state.integrityOk === false);
    refs.integrity.title = state.integrityOk ? '线上目录与修订快照一致' : '线上目录与修订快照不一致';
  }

  function renderAll() {
    renderRevision();
    renderTitleList();
    fillEditorFields();
    renderSegments();
    renderPreview();
    renderDiff();
    updateCommandState();
  }

  function formatTime(value) {
    if (!value) return '时间未知';
    const normalized = /(?:Z|[+-]\d\d:\d\d)$/.test(value) ? value : `${value}Z`;
    const date = new Date(normalized);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'medium', hour12: false }).format(date);
  }

  async function loadWorkspace({ preserveSelection = false } = {}) {
    state.loading = true;
    setSaveState('正在载入');
    try {
      const payload = await api('/api/title-editor/workspace');
      const workspace = payload.workspace || {};
      state.csrf = payload.csrf_token || '';
      state.permissions = {
        canEdit: Boolean(payload.permissions?.can_edit),
        canPublish: Boolean(payload.permissions?.can_publish),
        canRollback: Boolean(payload.permissions?.can_rollback),
      };
      state.actor = payload.actor || null;
      state.currentRevision = workspace.current_revision || null;
      state.integrityOk = Boolean(workspace.integrity_ok);
      state.liveCatalog = clone(workspace.catalog || { schema_version: 1, titles: [] });
      state.hasServerDraft = Boolean(workspace.draft);
      state.staleDraft = Boolean(workspace.draft?.stale);
      state.catalog = clone(workspace.draft?.catalog || workspace.catalog || { schema_version: 1, titles: [] });
      state.baseRevisionId = workspace.draft?.base_revision_id || workspace.current_revision?.revision_id || null;
      state.serverDiff = workspace.draft?.diff || null;
      state.history = workspace.history || [];
      state.savedFingerprint = currentFingerprint();
      state.undo = [];
      state.redo = [];
      state.selectedColor = null;
      if (!preserveSelection || !state.catalog.titles.some(item => item.id === state.selectedId)) {
        state.selectedId = state.catalog.titles[0]?.id || '';
      }
      populateColorTokens(payload.color_tokens || []);
      if (!workspace.integrity_ok) setAlert('安全检查发现线上称号目录与当前修订快照不一致。请勿发布，并先检查数据库。', 'error');
      else if (state.staleDraft) setAlert('此草稿基于旧修订。可以查看或另存修改，但发布前必须放弃草稿并从线上版本重新开始。', 'warning');
      else setAlert('');
      setSaveState(state.hasServerDraft ? `草稿已保存${workspace.draft?.updated_at ? ` · ${formatTime(workspace.draft.updated_at)}` : ''}` : '线上版本');
      renderAll();
    } catch (error) {
      setAlert(error.message || '称号目录加载失败', 'error');
      setSaveState('载入失败', true);
      showToast(error.message || '载入失败', true);
    } finally {
      state.loading = false;
    }
  }

  function populateColorTokens(tokens) {
    refs.colorToken.replaceChildren();
    const custom = make('option', '', '自定义颜色');
    custom.value = '';
    refs.colorToken.append(custom);
    (tokens.length ? tokens : Object.keys(COLOR_TOKENS)).forEach(token => {
      const option = make('option', '', token);
      option.value = token;
      refs.colorToken.append(option);
    });
  }

  async function saveDraft({ quiet = false } = {}) {
    window.clearTimeout(state.saveTimer);
    if (state.saving) {
      scheduleSave();
      return false;
    }
    const error = validateCatalog();
    if (error) {
      setSaveState('草稿未保存', true);
      if (!quiet) showToast(error, true);
      return false;
    }
    const requestFingerprint = currentFingerprint();
    if (requestFingerprint === state.savedFingerprint && state.hasServerDraft) return true;
    if (requestFingerprint === fingerprint(state.liveCatalog) && !state.hasServerDraft) {
      state.savedFingerprint = requestFingerprint;
      setSaveState('线上版本');
      return true;
    }
    state.saving = true;
    const requestId = ++state.saveRequest;
    setSaveState('正在保存');
    try {
      const payload = await api('/api/title-editor/draft', {
        method: 'POST',
        body: JSON.stringify({ base_revision_id: state.baseRevisionId, catalog: clone(state.catalog) }),
      });
      if (requestId !== state.saveRequest) return false;
      state.hasServerDraft = true;
      state.staleDraft = Boolean(payload.draft?.stale);
      state.serverDiff = payload.draft?.diff || null;
      state.savedFingerprint = requestFingerprint;
      setSaveState(state.staleDraft ? '草稿已保存 · 基础版本已过期' : '草稿已保存', state.staleDraft);
      renderDiff();
      updateCommandState();
      if (currentFingerprint() !== requestFingerprint) scheduleSave();
      return true;
    } catch (saveError) {
      setSaveState('草稿保存失败', true);
      if (!quiet) showToast(saveError.message, true);
      return false;
    } finally {
      state.saving = false;
    }
  }

  function openConfirm(options) {
    state.confirmAction = options.onConfirm;
    refs.confirmKicker.textContent = options.kicker || '';
    refs.confirmTitle.textContent = options.title || '请确认';
    refs.confirmBody.textContent = options.body || '';
    refs.confirmMessageWrap.classList.toggle('hidden', options.message === false);
    refs.confirmMessage.value = options.defaultMessage || '';
    refs.confirmPhraseWrap.classList.toggle('hidden', !options.phrase);
    refs.confirmPhraseLabel.textContent = options.phrase ? `输入 ${options.phrase} 以确认` : '';
    refs.confirmPhrase.value = '';
    refs.confirmSubmit.textContent = options.submitLabel || '确认';
    refs.confirmSubmit.dataset.phrase = options.phrase || '';
    refs.confirmDialog.showModal();
    window.setTimeout(() => (options.phrase ? refs.confirmPhrase : refs.confirmSubmit).focus(), 0);
  }

  async function beginPublish() {
    if (!state.permissions.canPublish) return;
    if (!(await saveDraft())) return;
    if (state.staleDraft) {
      showToast('草稿基础版本已过期，不能发布', true);
      return;
    }
    const diff = state.serverDiff || computeLocalDiff();
    if (!diff.changed_count) {
      showToast('没有可发布的修改', true);
      return;
    }
    const body = [
      `将发布 ${diff.changed_count} 个称号的修改，其中新增 ${diff.added_count || 0} 个、下架 ${diff.deactivated_count || 0} 个。`,
      `影响玩家：${diff.affected_user_count ?? '未知'}；当前佩戴：${diff.equipped_user_count ?? '未知'}。`,
      `可能重置昵称颜色选择：${diff.name_style_reset_count ?? '未知'} 人。`,
      '发布会立即改变线上目录，并自动生成不可变修订与压缩备份。',
    ].join('\n');
    openConfirm({
      kicker: 'Publish revision',
      title: '发布称号目录',
      body,
      phrase: 'publish',
      submitLabel: '发布',
      onConfirm: async message => {
        const payload = await api('/api/title-editor/publish', {
          method: 'POST',
          body: JSON.stringify({ confirm: 'publish', message }),
        });
        refs.confirmDialog.close();
        const errors = payload.result?.backup_errors || [];
        showToast(errors.length ? `发布成功，但有 ${errors.length} 个备份写入失败` : `已发布修订 #${payload.result?.revision_id}` , Boolean(errors.length));
        await loadWorkspace({ preserveSelection: true });
      },
    });
  }

  function renderHistory() {
    refs.historyList.replaceChildren();
    if (!state.history.length) {
      refs.historyList.append(make('div', 'te-empty-list', '暂无修订记录'));
      return;
    }
    state.history.forEach(revision => {
      const row = make('div', 'te-history-item');
      const content = make('div');
      const current = revision.revision_id === state.currentRevision?.revision_id;
      content.append(make('strong', '', `#${revision.revision_id} · ${revision.kind || 'publish'}${current ? ' · 当前' : ''}`));
      content.append(make('div', 'te-history-meta', `${formatTime(revision.created_at)} · ${revision.actor_username || 'system'} · ${revision.sha256.slice(0, 12)}`));
      content.append(make('div', 'te-history-message', revision.message || '无修订说明'));
      row.append(content);
      if (state.permissions.canRollback && !current) {
        const button = make('button', '', '回退到此版本');
        button.type = 'button';
        button.dataset.rollbackRevision = String(revision.revision_id);
        row.append(button);
      }
      refs.historyList.append(row);
    });
  }

  function beginRollback(revisionId) {
    const revision = state.history.find(item => item.revision_id === Number(revisionId));
    if (!revision || !state.permissions.canRollback) return;
    openConfirm({
      kicker: 'Create rollback revision',
      title: `回退到修订 #${revision.revision_id}`,
      body: `系统会以修订 #${revision.revision_id} 的快照创建一个新的线上修订，而不会删除任何历史记录。当前草稿将被放弃；旧版本中不存在的新称号会被安全地下架。`,
      phrase: 'rollback',
      defaultMessage: `Rollback to revision ${revision.revision_id}`,
      submitLabel: '执行回退',
      onConfirm: async message => {
        const payload = await api('/api/title-editor/rollback', {
          method: 'POST',
          body: JSON.stringify({ confirm: 'rollback', revision_id: revision.revision_id, message }),
        });
        refs.confirmDialog.close();
        showToast(`已创建回退修订 #${payload.result?.revision_id}`);
        await loadWorkspace({ preserveSelection: true });
      },
    });
  }

  function openCreate(mode) {
    state.createMode = mode;
    const source = selectedTitle();
    refs.createTitle.textContent = mode === 'duplicate' ? '复制称号' : '新建称号';
    refs.newId.value = mode === 'duplicate' && source ? `${source.id}-copy` : 'shop:';
    refs.newName.value = mode === 'duplicate' && source ? source.name : '';
    refs.createError.textContent = '';
    refs.createDialog.showModal();
    refs.newId.focus();
    refs.newId.select();
  }

  function createTitle() {
    const id = String(refs.newId.value || '').trim();
    const name = String(refs.newName.value || '').trim();
    if (!TITLE_ID_PATTERN.test(id)) {
      refs.createError.textContent = 'ID 仅可包含字母、数字及 . _ : -';
      return;
    }
    if (state.catalog.titles.some(item => item.id === id)) {
      refs.createError.textContent = '该 ID 已存在';
      return;
    }
    if (!name || name.length > 64 || /[{}]/.test(name)) {
      refs.createError.textContent = '名称应为 1 至 64 个字符，且不能包含花括号';
      return;
    }
    const source = state.createMode === 'duplicate' ? selectedTitle() : null;
    mutate(`create:${id}`, () => {
      let title;
      if (source) {
        title = clone(source);
        title.id = id;
        if (title.name !== name) {
          const paint = clone(title.style?.segments?.[0]?.paint || { kind: 'solid', color: 'neutral' });
          title.style = { version: 1, segments: [{ id: 'main', text: name, paint }] };
        }
        title.source_type = 'admin';
        title.source_ref = `duplicate:${source.id}`.slice(0, 96);
        title.purchasable = false;
        title.shop_weight = 0;
      } else {
        title = {
          id, name, color: 'neutral', source_type: 'admin', source_ref: '',
          price_free: null, price_paid: null, purchasable: false, active: true, shop_weight: 0,
          style: { version: 1, segments: [{ id: 'main', text: name, paint: { kind: 'solid', color: 'neutral' } }] },
        };
      }
      syncTitle(title);
      state.catalog.titles.push(title);
      state.catalog.titles.sort((a, b) => a.id.localeCompare(b.id));
      state.selectedId = id;
      state.selectedColor = null;
    }, 'all');
    refs.createDialog.close();
  }

  async function parseMarkup() {
    const title = selectedTitle();
    if (!title) return;
    refs.markupError.textContent = '';
    try {
      const payload = await api('/api/title-editor/preview', {
        method: 'POST',
        body: JSON.stringify({ style_markup: refs.markup.value, fallback_color: title.color || 'neutral' }),
      });
      mutate(`markup:${title.id}`, () => {
        title.style = clone(payload.style);
        title.name = payload.name;
        title.color = payload.color;
        title.style_markup = refs.markup.value.trim();
        state.selectedColor = null;
      }, 'all');
      showToast('语法已解析并应用');
    } catch (error) {
      refs.markupError.textContent = error.message;
    }
  }

  function bindStaticFields() {
    const bindings = [
      [refs.active, 'active', input => input.checked, 'change'],
      [refs.sourceType, 'source_type', input => input.value.trim(), 'input'],
      [refs.sourceRef, 'source_ref', input => input.value.trim(), 'input'],
      [refs.priceFree, 'price_free', input => input.value === '' ? null : Number(input.value), 'input'],
      [refs.pricePaid, 'price_paid', input => input.value === '' ? null : Number(input.value), 'input'],
      [refs.shopWeight, 'shop_weight', input => input.value === '' ? 0 : Number(input.value), 'input'],
      [refs.purchasable, 'purchasable', input => input.checked, 'change'],
    ];
    bindings.forEach(([input, field, getter, event]) => {
      input.addEventListener(event, () => {
        const title = selectedTitle();
        if (!title) return;
        mutate(`field:${title.id}:${field}`, () => { title[field] = getter(input); });
      });
    });
  }

  function bindEvents() {
    bindStaticFields();
    refs.search.addEventListener('input', renderTitleList);
    refs.filter.addEventListener('change', renderTitleList);
    refs.titleList.addEventListener('click', event => {
      const row = event.target.closest('[data-title-id]');
      if (!row) return;
      state.selectedId = row.dataset.titleId;
      state.selectedColor = null;
      renderAll();
    });
    refs.segments.addEventListener('input', event => {
      const title = selectedTitle();
      const index = Number(event.target.dataset.segmentIndex);
      const segment = title?.style?.segments?.[index];
      if (!segment) return;
      if (event.target.matches('.te-segment-text')) {
        mutate(`segment-text:${title.id}:${index}`, () => { segment.text = event.target.value; });
      } else if (event.target.matches('.te-segment-id')) {
        const oldId = segment.id;
        mutate(`segment-id:${title.id}:${index}`, () => {
          segment.id = event.target.value.trim();
          if (state.selectedColor?.segmentId === oldId) state.selectedColor.segmentId = segment.id;
        });
      } else if (event.target.matches('.te-angle-input')) {
        mutate(`angle:${title.id}:${index}`, () => { segment.paint.angle = normalizeAngle(event.target.value); });
      }
    });
    refs.segments.addEventListener('change', event => {
      if (!event.target.matches('.te-paint-kind')) return;
      const title = selectedTitle();
      const index = Number(event.target.dataset.segmentIndex);
      const segment = title?.style?.segments?.[index];
      if (!segment) return;
      const kind = event.target.value;
      mutate(`paint-kind:${title.id}:${index}`, () => {
        const current = paintFallbackColor(segment.paint);
        if (kind === 'solid') segment.paint = { kind, color: current };
        if (kind === 'gradient') segment.paint = { kind, angle: 90, colors: [current, '#3478F6'] };
        if (kind === 'rainbow') segment.paint = { kind, angle: 90, colors: RAINBOW.slice() };
        if (kind === 'theme') segment.paint = { kind, light: { kind: 'solid', color: current }, dark: { kind: 'solid', color: '#000000' } };
        state.selectedColor = null;
      }, 'segments');
    });
    refs.segments.addEventListener('click', event => {
      const color = event.target.closest('[data-color-path]');
      if (color) {
        const title = selectedTitle();
        const segment = title?.style?.segments?.[Number(color.dataset.segmentIndex)];
        if (!segment) return;
        state.selectedColor = { segmentId: segment.id, path: color.dataset.colorPath };
        refreshColorSwatches();
        syncColorControls();
        return;
      }
      const action = event.target.closest('[data-action]');
      if (!action) return;
      const title = selectedTitle();
      const index = Number(action.dataset.segmentIndex);
      const segment = title?.style?.segments?.[index];
      if (!segment) return;
      if (action.dataset.action === 'remove-segment' && title.style.segments.length > 1) {
        mutate(`remove-segment:${title.id}:${index}`, () => {
          title.style.segments.splice(index, 1);
          state.selectedColor = null;
        }, 'segments');
      }
      if (action.dataset.action === 'add-stop' && segment.paint.colors.length < 12) {
        mutate(`add-stop:${title.id}:${index}`, () => {
          segment.paint.colors.push(segment.paint.colors.at(-1) || '#3478F6');
        }, 'segments');
      }
      if (action.dataset.action === 'remove-stop' && segment.paint.colors.length > 2) {
        mutate(`remove-stop:${title.id}:${index}`, () => {
          segment.paint.colors.splice(Number(action.dataset.stopIndex), 1);
          state.selectedColor = null;
        }, 'segments');
      }
    });
    $('#te-add-segment').addEventListener('click', () => {
      const title = selectedTitle();
      if (!title || title.style.segments.length >= 24) return;
      mutate(`add-segment:${title.id}`, () => {
        let counter = title.style.segments.length + 1;
        let id = `part-${counter}`;
        const used = new Set(title.style.segments.map(item => item.id));
        while (used.has(id)) id = `part-${++counter}`;
        title.style.segments.push({ id, text: '新段', paint: { kind: 'solid', color: 'neutral' } });
      }, 'segments');
    });

    refs.colorPicker.addEventListener('input', () => {
      const current = colorToRgba(colorSelection()?.value);
      const next = `${refs.colorPicker.value}${current.a < 0.999 ? Math.round(current.a * 255).toString(16).padStart(2, '0') : ''}`;
      setSelectedColor(next, 'picker');
    });
    refs.colorValue.addEventListener('change', () => setSelectedColor(refs.colorValue.value, 'value'));
    refs.colorToken.addEventListener('change', () => {
      if (refs.colorToken.value) setSelectedColor(refs.colorToken.value, 'token');
    });
    [refs.red, refs.green, refs.blue].forEach(input => input.addEventListener('change', () => {
      const current = colorToRgba(colorSelection()?.value);
      setSelectedColor(rgbaToHex({ r: refs.red.value, g: refs.green.value, b: refs.blue.value, a: current.a }), 'rgb');
    }));
    [refs.hue, refs.saturation, refs.value].forEach(input => input.addEventListener('change', () => {
      const current = colorToRgba(colorSelection()?.value);
      setSelectedColor(rgbaToHex({ ...hsvToRgb(refs.hue.value, refs.saturation.value, refs.value.value), a: current.a }), 'hsv');
    }));
    refs.alpha.addEventListener('input', () => {
      refs.alphaValue.value = `${refs.alpha.value}%`;
      const current = colorToRgba(colorSelection()?.value);
      setSelectedColor(rgbaToHex({ ...current, a: Number(refs.alpha.value) / 100 }), 'alpha');
    });

    $('#te-theme-light').addEventListener('click', event => {
      state.previewTheme = 'light';
      event.currentTarget.classList.add('active');
      $('#te-theme-dark').classList.remove('active');
      renderPreview();
    });
    $('#te-theme-dark').addEventListener('click', event => {
      state.previewTheme = 'dark';
      event.currentTarget.classList.add('active');
      $('#te-theme-light').classList.remove('active');
      renderPreview();
    });
    refs.undo.addEventListener('click', undo);
    refs.redo.addEventListener('click', redo);
    $('#te-help').addEventListener('click', () => refs.helpDialog.showModal());
    $('#te-history').addEventListener('click', () => {
      renderHistory();
      refs.historyDialog.showModal();
    });
    $('#te-create').addEventListener('click', () => openCreate('create'));
    $('#te-duplicate').addEventListener('click', () => openCreate('duplicate'));
    $('#te-create-submit').addEventListener('click', createTitle);
    $('#te-parse-markup').addEventListener('click', parseMarkup);
    refs.publish.addEventListener('click', beginPublish);
    refs.discard.addEventListener('click', () => {
      openConfirm({
        kicker: 'Discard draft', title: '放弃当前草稿', message: false,
        body: '服务器草稿和本页尚未保存的修改都会被移除，编辑器将重新载入当前线上修订。此操作不会改变线上目录或历史修订。',
        submitLabel: '放弃草稿',
        onConfirm: async () => {
          await api('/api/title-editor/draft', { method: 'DELETE' });
          refs.confirmDialog.close();
          showToast('草稿已放弃');
          await loadWorkspace();
        },
      });
    });
    refs.historyList.addEventListener('click', event => {
      const button = event.target.closest('[data-rollback-revision]');
      if (button) beginRollback(button.dataset.rollbackRevision);
    });
    refs.confirmSubmit.addEventListener('click', async () => {
      const phrase = refs.confirmSubmit.dataset.phrase || '';
      if (phrase && refs.confirmPhrase.value.trim().toLowerCase() !== phrase.toLowerCase()) {
        showToast(`请输入 ${phrase} 以确认`, true);
        refs.confirmPhrase.focus();
        return;
      }
      if (!state.confirmAction) return;
      refs.confirmSubmit.disabled = true;
      try {
        await state.confirmAction(refs.confirmMessage.value.trim());
      } catch (error) {
        showToast(error.message || '操作失败', true);
      } finally {
        refs.confirmSubmit.disabled = false;
      }
    });
    $$('.te-dialog-close').forEach(button => button.addEventListener('click', () => button.closest('dialog')?.close()));
    refs.createDialog.addEventListener('keydown', event => {
      if (event.key === 'Enter' && event.target.tagName !== 'TEXTAREA') {
        event.preventDefault();
        createTitle();
      }
    });
    document.addEventListener('keydown', event => {
      const command = event.ctrlKey || event.metaKey;
      if (command && event.key.toLowerCase() === 's') {
        event.preventDefault();
        saveDraft();
      } else if (command && !event.shiftKey && event.key.toLowerCase() === 'z') {
        event.preventDefault();
        undo();
      } else if ((command && event.key.toLowerCase() === 'y') || (command && event.shiftKey && event.key.toLowerCase() === 'z')) {
        event.preventDefault();
        redo();
      }
    });
    window.addEventListener('beforeunload', event => {
      if (!isDirty()) return;
      event.preventDefault();
      event.returnValue = '';
    });
  }

  bindEvents();
  loadWorkspace();
})();
