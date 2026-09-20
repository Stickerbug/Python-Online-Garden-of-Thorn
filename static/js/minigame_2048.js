/* 休闲花园 · 2048 客户端。

   规则与随机数必须和 Python 侧（minigame_2048.py）**逐位一致**：
   32 位 xorshift、90% 出 2、空格等概率、同一次操作里新合成的方块不再合并。
   本地先跑，网络只负责同步 / 排行榜；任何移动、合并、生成都不等待服务器。

   存档按账号隔离（`gtn_mg2048_v1_u<id>`）；未确认的操作排队，重连后按
   `from_index` 续传，服务端重放验证。401/403 视为真实拒绝，不用缓存绕过。 */

import {
  DIRECTION_CHARS, DIRECTIONS, ETERNAL_VALUE, initialCells, isGameOver, maxTile,
  seedFromText, stepMove,
} from './minigame_2048_core.js';

const CONFIG = JSON.parse(document.getElementById('mg-config').textContent || '{}');
const PALETTE = JSON.parse(document.getElementById('mg-palette').textContent || '[]');
const RULES_VERSION = 1;
const SAVE_VERSION = 1;
const MAX_PENDING_OPS = 20000;
const SYNC_DEBOUNCE_MS = 400;
const RETRY_BASE_MS = 1500;
const RETRY_MAX_MS = 30000;
const KEY_DIRECTIONS = {
  ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'up', ArrowDown: 'down',
  a: 'left', d: 'right', w: 'up', s: 'down',
};
const STORAGE_PREFIX = 'gtn_mg2048_v1_';
const accountKey = `${STORAGE_PREFIX}u${CONFIG.userId || 'self'}`;

const el = (id) => document.getElementById(id);
const boardEl = el('mg-board');
const scoreEl = el('mg-score');
const bestEl = el('mg-best');
const verifiedEl = el('mg-verified');
const syncEl = el('mg-sync');
const overlayEl = el('mg-overlay');

let state = null;          // { seed, rngState, cells, score, ops, acked, gameUid, best, ... }
let syncTimer = null;
let retryDelay = RETRY_BASE_MS;
let syncing = false;
let identityRejected = false;
let showNumbers = false;
let animations = true;

/* ---------------- 规则（与 Python 侧同构） ---------------- */

const PALETTE_BY_VALUE = new Map(PALETTE.map((item) => [Number(item.value), item]));

function paletteFor(value) {
  return PALETTE_BY_VALUE.get(Number(value)) || null;
}

/* 原版 / AK IOI 的"方块光晕"细节：从 128 起，每一档光晕更亮，
   2048 是原版那圈金色光，再往上维持最亮；同时有一圈 1px 内侧高光（rim light）。
   数值取自两边 CSS 共用的那组透明度阶梯（0.2381 → 0.55556）。 */
const GLOW_LADDER = [
  [128, 0.2381], [256, 0.31746], [512, 0.39683], [1024, 0.47619], [2048, 0.55556],
];
const ETERNAL_GLOW_RGB = '243, 215, 116';   // 原版 .tile-2048 的金色

function hexToRgb(hex) {
  const text = String(hex || '').trim().replace('#', '');
  if (text.length !== 6) return null;
  const value = Number.parseInt(text, 16);
  if (Number.isNaN(value)) return null;
  return `${(value >> 16) & 255}, ${(value >> 8) & 255}, ${value & 255}`;
}

function glowFor(value, borderHex) {
  const tier = Number(value) || 0;
  let alpha = 0;
  for (const [threshold, step] of GLOW_LADDER) {
    if (tier >= threshold) alpha = step;
  }
  if (!alpha) return null;
  const rgb = tier >= 2048 ? ETERNAL_GLOW_RGB : (hexToRgb(borderHex) || null);
  if (!rgb) return null;
  return {
    outer: `rgba(${rgb}, ${alpha})`,
    inset: `rgba(255, 255, 255, ${(alpha * 0.6).toFixed(4)})`,
  };
}

/* ---------------- 本地存档 ---------------- */

function storage() {
  try {
    const probe = '__mg_probe__';
    window.localStorage.setItem(probe, '1');
    window.localStorage.removeItem(probe);
    return window.localStorage;
  } catch (_) {
    return null;
  }
}

const store = storage();
let storageWarned = false;

function saveLocal() {
  if (!store) {
    if (!storageWarned) {
      storageWarned = true;
      setSyncText('无法可靠保存（浏览器存储不可用），本次游玩仍可继续');
    }
    return;
  }
  try {
    store.setItem(accountKey, JSON.stringify({
      saveVersion: SAVE_VERSION,
      rulesVersion: RULES_VERSION,
      gameUid: state.gameUid,
      seed: state.seed,
      rngState: state.rngState,
      cells: state.cells,
      score: state.score,
      ops: state.ops.join(''),
      acked: state.acked,
      best: state.best,
      reachedShown: state.reachedShown,
      continued: state.continued,
      source: state.source,
      localNew: state.localNew === true,
      declined: state.declined,
    }));
  } catch (exc) {
    if (!storageWarned) {
      storageWarned = true;
      setSyncText('无法可靠保存（存储配额不足），本次游玩仍可继续');
    }
  }
}

function loadLocal() {
  if (!store) return null;
  try {
    const raw = store.getItem(accountKey);
    if (!raw) return null;
    const data = JSON.parse(raw);
    if (!data || data.saveVersion !== SAVE_VERSION) return null;
    return data;
  } catch (_) {
    return null;
  }
}

/* ---------------- 渲染 ---------------- */

function setSyncText(text, kind = '') {
  syncEl.textContent = text;
  syncEl.dataset.state = kind;
}

function tileLabel(value) {
  const item = paletteFor(value);
  return item ? item.name : '';
}

/* 方块外观（底色 / 边框 / 字色 / 光晕）与内容，棋盘格子和合并幽灵块共用。 */
function applyTileSkin(tile, value) {
  const item = paletteFor(value);
  tile.style.setProperty('--mg-tile-bg', item ? item.bg : '#9aa5a0');
  tile.style.setProperty('--mg-tile-border', item ? item.border : '#7d8783');
  tile.style.setProperty('--mg-tile-fg', item ? item.fg : '#15201B');
  const glow = glowFor(value, item ? item.border : '');
  if (glow) {
    tile.style.setProperty('--mg-glow', glow.outer);
    tile.style.setProperty('--mg-glow-inset', glow.inset);
  }
  const name = tileLabel(value);
  // 名称越长字号越小：CSS 用 --mg-chars 算 cqw/cqh 比例（见 minigame_2048.css）
  tile.style.setProperty('--mg-chars', String((name || String(value)).length));
}

function tileFaceHtml(value) {
  const name = tileLabel(value);
  if (!name) {
    return `<span class="mg-tile-face"><span class="mg-tile-name">${value}</span></span>`;
  }
  return `<span class="mg-tile-face">`
    + `<span class="mg-tile-name">${name}</span>`
    + (showNumbers ? `<span class="mg-tile-value">${value}</span>` : '')
    + '</span>';
}

function renderBoard(animate) {
  boardEl.innerHTML = '';
  const pending = state.ops.length - state.acked;
  // 这一步里"被合并掉"的格子（用来播放合并弹一下，和原版一致）
  const mergedIndexes = new Set(
    (animate && Array.isArray(state.lastMoves) ? state.lastMoves : [])
      .filter((move) => move && move.merged)
      .map((move) => move.to),
  );
  /* 原版 html_actuator.addTile 的做法：合并时把"被合并掉的两块"也渲染出来，
     让它们各自从原位滑到目标格，合并后的新块再在它们上面 pop。
     这里用"幽灵块"实现：绝对定位在目标格，先摆回源格位置再过渡过去，动画完就移除。 */
  const mergeSources = new Map();
  if (animate && Array.isArray(state.lastMoves)) {
    state.lastMoves.forEach((move) => {
      if (!move || !move.merged) return;
      if (!mergeSources.has(move.to)) mergeSources.set(move.to, []);
      mergeSources.get(move.to).push(move.from);
    });
  }
  const ghostTargets = new Map();   // to → [ghost 元素]
  state.cells.forEach((value, index) => {
    const tile = document.createElement('div');
    tile.className = 'mg-cell' + (value ? ' filled' : '');
    if (value) {
      applyTileSkin(tile, value);
      tile.innerHTML = tileFaceHtml(value);
      tile.classList.add('mg-tile');
      if (value >= 2048) tile.classList.add('mg-tile-eternal');
      if (animate && state.lastSpawn === index) tile.classList.add('mg-tile-new');
      if (animate && mergedIndexes.has(index)) tile.classList.add('mg-tile-merged');
    }
    boardEl.appendChild(tile);
  });
  // 生成合并幽灵块：源值取自"上一步的棋盘"，让它们滑进目标格
  if (mergeSources.size && Array.isArray(state.lastPrev)) {
    mergeSources.forEach((sources, target) => {
      const cell = boardEl.children[target];
      if (!cell) return;
      const created = [];
      sources.forEach((from) => {
        const value = Number(state.lastPrev[from] || 0);
        if (!value) return;
        const ghost = document.createElement('div');
        ghost.className = 'mg-cell filled mg-ghost';
        applyTileSkin(ghost, value);
        ghost.innerHTML = tileFaceHtml(value);
        ghost.dataset.from = String(from);
        ghost.dataset.to = String(target);
        boardEl.insertBefore(ghost, cell);
        created.push(ghost);
      });
      if (created.length) ghostTargets.set(target, created);
    });
  }
  // 原版那种"方块滑过去"：按上一步的移动映射把方块先摆回旧位置，再过渡回原位。
  if (animate && Array.isArray(state.lastMoves) && state.lastMoves.length) {
    slideTiles(state.lastMoves, ghostTargets);
  }
  scoreEl.textContent = String(state.score);
  bestEl.textContent = String(state.best);
  // 同步算好字号（在下一帧绘制之前），新方块一出现就是最终大小；缓存命中时几乎零成本。
  fitTileNames();
  updateSyncLabel();
}

/* 同步状态那行小字：棋盘重绘和"只更新同步信息"两条路共用。
   （从服务器回来的同步结果不需要重绘棋盘——重绘会打断正在播放的出现/合并动画。） */
function updateSyncLabel() {
  const pending = state.ops.length - state.acked;
  if (pending > 0) {
    setSyncText(`待同步 ${pending} 步${navigator.onLine ? '' : '（离线，本地已保存）'}`,
      navigator.onLine ? 'pending' : 'offline');
  } else if (state.acked === state.ops.length) {
    setSyncText(state.lastSyncLabel || '已同步', 'ok');
  }
}

let tileFitFrame = null;
/* 字号缓存：key = 文字 + 格子尺寸。同一文字在同样大的格子里直接套用上次算好的字号，
   这样新方块**在首次绘制前**就已经是最终字号，不会出现"先小后大"的跳变。 */
const tileFitCache = new Map();

function fitTileNames({ force = false } = {}) {
  // 连"合并幽灵块"一起算：它们和最终方块用同一套字号，滑进去时文字不会突然变化
  const cells = boardEl.querySelectorAll('.mg-cell.filled');
  cells.forEach((cell) => {
    const name = cell.querySelector('.mg-tile-name');
    if (!name) return;
    const text = String(name.textContent || '');
    const key = `${text}|${cell.clientWidth}|${cell.clientHeight}`;
    const cached = tileFitCache.get(key);
    if (cached && !force) {
      name.style.fontSize = `${cached}px`;
      return;
    }
    const availW = Math.max(18, cell.clientWidth - 10);
    const availH = Math.max(14, cell.clientHeight - 10);
    const fits = (size) => {
      name.style.fontSize = `${size}px`;
      const rect = name.getBoundingClientRect();
      return rect.width <= availW + 0.5 && rect.height <= availH + 0.5;
    };
    // 二分找出"能放下"的最大字号：短名更大、长名自动变小，且尽量占满格子。
    const MAX_SIZE = 40;
    const MIN_SIZE = 9;
    let low = MIN_SIZE;
    let high = MAX_SIZE;
    if (fits(high)) {
      name.style.fontSize = `${high}px`;
      tileFitCache.set(key, high);
      return;
    }
    while (high - low > 0.5) {
      const mid = (low + high) / 2;
      if (fits(mid)) low = mid;
      else high = mid;
    }
    const size = Math.floor(low * 10) / 10;
    name.style.fontSize = `${size}px`;
    tileFitCache.set(key, size);
  });
}

function scheduleTileFit() {
  if (tileFitFrame) window.cancelAnimationFrame(tileFitFrame);
  tileFitFrame = window.requestAnimationFrame(() => {
    tileFitFrame = null;
    fitTileNames({ force: true });
  });
}

/* 方块滑动（对应原版 `.tile` 的 `transition: 100ms ease-in-out`）：
   先把方块按"旧格子 → 新格子"的位移摆回旧位置，下一动画帧再放回原位，
   让 CSS 过渡把它滑过去；不改变最终布局，也不影响无动画模式。 */
function slideTiles(moves, ghostTargets = new Map()) {
  const cells = boardEl.querySelectorAll('.mg-cell:not(.mg-ghost)');
  if (cells.length !== 16) return;
  const first = cells[0].getBoundingClientRect();
  const stepX = cells[1].getBoundingClientRect().left - first.left;
  const stepY = cells[4].getBoundingClientRect().top - first.top;
  const shifted = [];
  const mergeTargets = new Set(ghostTargets.keys());
  moves.forEach((move) => {
    if (!move || move.from === move.to) return;
    // 合并格不滑动：原版里滑进去的是"被合并掉的两块"（下面按幽灵块处理），新块只在原位 pop
    if (mergeTargets.has(move.to)) return;
    const target = cells[move.to];
    if (!target) return;
    const fromCol = move.from % 4;
    const fromRow = Math.floor(move.from / 4);
    const toCol = move.to % 4;
    const toRow = Math.floor(move.to / 4);
    target.style.transition = 'none';
    target.style.transform = `translate(${(fromCol - toCol) * stepX}px, ${(fromRow - toRow) * stepY}px)`;
    shifted.push(target);
  });
  // 合并幽灵块：先摆到源格，再滑到目标格，动画结束后移除
  const ghosts = [];
  ghostTargets.forEach((list, target) => {
    const cell = cells[target];
    if (!cell) return;
    const baseLeft = cell.offsetLeft;
    const baseTop = cell.offsetTop;
    const width = cell.offsetWidth;
    const height = cell.offsetHeight;
    list.forEach((ghost) => {
      const from = Number(ghost.dataset.from || 0);
      const fromCol = from % 4;
      const fromRow = Math.floor(from / 4);
      const toCol = target % 4;
      const toRow = Math.floor(target / 4);
      ghost.style.left = `${baseLeft}px`;
      ghost.style.top = `${baseTop}px`;
      ghost.style.width = `${width}px`;
      ghost.style.height = `${height}px`;
      ghost.style.transition = 'none';
      ghost.style.transform = `translate(${(fromCol - toCol) * stepX}px, ${(fromRow - toRow) * stepY}px)`;
      ghosts.push(ghost);
    });
  });
  const movingGhosts = ghosts.slice();
  if (!shifted.length && !movingGhosts.length) return;
  void boardEl.offsetHeight;   // 强制重排，让上面的初始位移先生效
  window.requestAnimationFrame(() => {
    shifted.forEach((el) => {
      el.style.transition = 'transform 100ms ease-in-out';
      el.style.transform = 'translate(0, 0)';
    });
    movingGhosts.forEach((el) => {
      el.style.transition = 'transform 100ms ease-in-out';
      el.style.transform = 'translate(0, 0)';
    });
    window.setTimeout(() => {
      shifted.forEach((el) => {
        el.style.transition = '';
        el.style.transform = '';
      });
      movingGhosts.forEach((el) => el.remove());
    }, 150);
  });
}

// 便于自动化检查（也方便以后调试）：手动触发一次"字号自适应"
window.__mgFit = () => fitTileNames({ force: true });

function buildLegend() {
  const host = el('mg-legend-grid');
  if (!host) return;
  // 排版参考 AK IOI 的 oi-2048：左边一块"方块"，右边写名称（这里是稀有度名）。
  host.innerHTML = PALETTE.map((item) => `
    <span class="mg-legend-item" style="--mg-tile-bg:${item.bg};--mg-tile-fg:${item.fg}">
      <span class="mg-legend-swatch">${item.value}</span>
      <span class="mg-legend-name">${item.name}</span>
    </span>`).join('');
}

function showOverlay({ title, text, primary, secondary }) {
  el('mg-overlay-title').textContent = title;
  el('mg-overlay-text').textContent = text || '';
  const primaryBtn = el('mg-overlay-primary');
  const secondaryBtn = el('mg-overlay-secondary');
  primaryBtn.textContent = primary.label;
  primaryBtn.onclick = primary.run;
  if (secondary) {
    secondaryBtn.hidden = false;
    secondaryBtn.textContent = secondary.label;
    secondaryBtn.onclick = secondary.run;
  } else {
    secondaryBtn.hidden = true;
    secondaryBtn.onclick = null;
  }
  overlayEl.hidden = false;
}

function hideOverlay() {
  overlayEl.hidden = true;
}

/* ---------------- 同步 ---------------- */

function scheduleSync(delay = SYNC_DEBOUNCE_MS) {
  if (identityRejected) return;
  if (syncTimer) return;
  syncTimer = window.setTimeout(() => {
    syncTimer = null;
    void syncNow();
  }, delay);
}

async function syncNow() {
  if (syncing || identityRejected) return;
  const pendingOps = state.ops.slice(state.acked);
  if (!pendingOps.length) return;
  syncing = true;
  const fromIndex = state.acked;
  const payload = {
    game_uid: state.gameUid,
    from_index: fromIndex,
    ops: pendingOps.join(''),
    claimed_score: state.score,
    claimed_cells: state.cells,
    source: state.source,
    reached_2048: maxTile(state.cells) >= 2048,
    continued: state.continued,
    // 离线自开的局：把种子一起交上去，服务端从起点重放验证（记录离线来源）。
    new_game: state.localNew === true,
    seed: state.localNew === true ? state.seed : undefined,
  };
  try {
    const response = await fetch('/api/minigame/2048/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(payload),
    });
    if (response.status === 401 || response.status === 403) {
      identityRejected = true;
      const body = await response.json().catch(() => ({}));
      setSyncText(body.error || '身份或权限失效，已停止同步（本地进度仍在）', 'denied');
      return;
    }
    if (response.status === 409) {
      const body = await response.json().catch(() => ({}));
      await handleConflict(body);
      return;
    }
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      setSyncText(body.error || '同步被拒绝，本地进度已保留', 'error');
      retryDelay = Math.min(retryDelay * 2, RETRY_MAX_MS);
      scheduleSync(retryDelay);
      return;
    }
    const body = await response.json();
    state.acked = Number(body.op_index || fromIndex + pendingOps.length);
    state.localNew = false;
    state.lastSyncLabel = body.record
      ? `已同步 · 已验证 ${body.record.score} 分`
      : '已同步（本次没有新增计分）';
    if (body.verified) verifiedEl.textContent = String(body.verified.score);
    retryDelay = RETRY_BASE_MS;
    saveLocal();
    // 不要重绘棋盘：会打断正在播放的出现/合并/滑动动画。只更新同步状态那行字。
    updateSyncLabel();
    if (state.ops.length > state.acked) scheduleSync();
  } catch (_) {
    setSyncText('离线，本地已保存', 'offline');
    retryDelay = Math.min(retryDelay * 2, RETRY_MAX_MS);
    scheduleSync(retryDelay);
  } finally {
    syncing = false;
  }
}

async function handleConflict(body) {
  // 服务器已接受的分支保持权威：本地分支留备份，不换局 ID 继续计入成绩。
  try {
    store && store.setItem(`${accountKey}_conflict`, JSON.stringify({
      at: new Date().toISOString(),
      seed: state.seed, ops: state.ops.join(''), score: state.score,
    }));
  } catch (_) { /* 备份失败也不阻断 */ }
  const serverState = body.state;
  setSyncText('与服务器进度分叉：已用服务器分支继续，本地分支已备份', 'conflict');
  if (serverState && serverState.game) {
    adoptServerState(serverState);
  }
}

function adoptServerState(serverState) {
  const game = serverState.game;
  const board = serverState.board || {};
  state.gameUid = game.game_uid;
  state.localNew = false;
  state.seed = Number(game.seed);
  state.ops = String(game.ops || '').split('');
  state.acked = Number(serverState.verified?.op_index || 0);
  state.cells = (board.cells || []).slice();
  state.score = Number(board.score || 0);
  state.rngState = Number(board.rng_state || 0);
  saveLocal();
  renderBoard(false);
}

/* ---------------- 操作 ---------------- */

function move(direction) {
  if (!state || identityRejected) return;
  if (!overlayEl.hidden) return;
  const previousCells = state.cells.slice();   // 合并幽灵块要用"合并前的数值"
  const result = stepMove(state.cells, state.rngState, state.score, direction);
  if (!result.changed) return;                       // 无效操作：不加分、不生成、不入队
  state.cells = result.cells;
  state.rngState = result.rngState;
  state.score = result.score;
  state.ops.push(DIRECTION_CHARS[direction]);
  if (state.ops.length - state.acked > MAX_PENDING_OPS) state.acked = state.ops.length - MAX_PENDING_OPS;
  state.best = Math.max(state.best || 0, state.score);
  state.lastSpawn = result.spawn ? result.spawn.index : null;
  state.lastMoves = Array.isArray(result.moves) ? result.moves : [];
  state.lastPrev = previousCells;
  if (result.gained > 0) {
    // 官方 2048 的 "+N" 反馈：飘在分数格上，不占布局。
    const box = scoreEl.parentElement;
    if (box) {
      // 原版 updateScore 会先清空分数格，所以任何时刻只挂一个 "+N"
      box.querySelectorAll('.mg-score-float').forEach((node) => node.remove());
      const float = document.createElement('span');
      float.className = 'mg-score-float';
      float.textContent = `+${result.gained}`;
      box.appendChild(float);
      window.setTimeout(() => float.remove(), 750);
    }
  }
  saveLocal();
  renderBoard(animations);
  scheduleSync();
  if (maxTile(state.cells) >= 2048 && !state.reachedShown) {
    state.reachedShown = true;
    state.continued = true;
    saveLocal();
    showOverlay({
      title: '达成 Eternal（2048）！',
      text: '可以继续合成 Fabled、Divine 等更高级方块，也可以开新局。',
      primary: { label: '继续游戏', run: () => { hideOverlay(); } },
      secondary: { label: '重新开始', run: () => { hideOverlay(); void restartGame(); } },
    });
  } else if (isGameOver(state.cells)) {
    showOverlay({
      title: '游戏结束',
      text: `本局 ${state.score} 分。成绩已自动同步，不需要手动提交。`,
      primary: { label: '再来一局', run: () => { hideOverlay(); void restartGame(); } },
      secondary: { label: '看看棋盘', run: () => hideOverlay() },
    });
  }
}

async function restartGame() {
  if (!window.confirm('确定重新开始？当前这局会关闭（已获得的成绩与待同步操作都会保留）。')) return;
  try {
    const response = await fetch('/api/minigame/2048/restart', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ source: state.source }),
    });
    if (response.status === 401 || response.status === 403) {
      identityRejected = true;
      setSyncText('身份或权限失效，无法开始新局（本地进度仍在）', 'denied');
      return;
    }
    if (response.ok) {
      const body = await response.json();
      adoptServerState(body);
      hideOverlay();
      return;
    }
  } catch (_) { /* 离线：本地开新局 */ }
  startLocalGame();
  hideOverlay();
}

function startLocalGame(seed) {
  const value = seed || seedFromText(`${CONFIG.username}:${Date.now()}:${Math.random()}`);
  const initial = initialCells(value >>> 0);
  state = {
    ...state,
    gameUid: `local-${value.toString(16)}`,
    seed: value >>> 0,
    rngState: initial.rngState,
    cells: initial.cells,
    score: 0,
    ops: [],
    acked: 0,
    reachedShown: false,
    continued: false,
    source: navigator.onLine ? 'online' : 'offline',
    localNew: true,
    lastSyncLabel: '本地新局：联网后自动验证',
  };
  saveLocal();
  renderBoard(false);
  scheduleSync();
}

/* ---------------- 输入 ---------------- */

function isEditable(target) {
  if (!target) return false;
  const tag = String(target.tagName || '').toLowerCase();
  return tag === 'input' || tag === 'textarea' || tag === 'select' || target.isContentEditable;
}

document.addEventListener('keydown', (event) => {
  if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) return;
  if (isEditable(event.target)) return;               // 聊天/设置输入框里不触发移动
  const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
  if (key === 'r') {
    void restartGame();
    return;
  }
  const direction = KEY_DIRECTIONS[key];
  if (direction === undefined) return;
  event.preventDefault();
  move(DIRECTIONS[direction]);
});

let touchStart = null;
boardEl.addEventListener('touchstart', (event) => {
  if (event.touches.length !== 1) return;
  const touch = event.touches[0];
  touchStart = { x: touch.clientX, y: touch.clientY, handled: false };
}, { passive: true });
boardEl.addEventListener('touchmove', (event) => {
  if (!touchStart || event.touches.length !== 1) return;
  const touch = event.touches[0];
  const dx = touch.clientX - touchStart.x;
  const dy = touch.clientY - touchStart.y;
  if (Math.abs(dx) < 24 && Math.abs(dy) < 24) return;
  if (touchStart.handled) { event.preventDefault(); return; }   // 一次手势只移动一次
  touchStart.handled = true;
  event.preventDefault();
  move(Math.abs(dx) > Math.abs(dy)
    ? (dx > 0 ? DIRECTIONS.right : DIRECTIONS.left)
    : (dy > 0 ? DIRECTIONS.down : DIRECTIONS.up));
}, { passive: false });
boardEl.addEventListener('touchend', () => { touchStart = null; }, { passive: true });

/* ---------------- 排行榜 / 偏好 ---------------- */

/* ---------------- 大厅在线状态 + 对局邀请 ----------------
   小游戏页只"标状态"：服务端据此在大厅显示「小游戏中 · 2048」，
   正式对局 / 观战 / 重连中的状态优先，后台标签页改不动它们。
   断线（关页、断网）走正常清理，不会伪造在线。 */

let socket = null;

function connectPresence() {
  if (typeof io !== 'function') return;
  socket = io({ transports: ['websocket', 'polling'], withCredentials: true });
  socket.on('connect', () => {
    socket.emit('minigame_presence', { game: '2048' });
    setSyncText('在线：正在校验本机进度…');
    scheduleSync(200);
  });
  socket.on('minigame_status', () => { /* 状态已生效 */ });
  socket.on('server_error', (payload) => {
    const reason = payload && payload.reason;
    if (reason === 'minigame_denied' || reason === 'minigame_login_required') {
      identityRejected = true;
      setSyncText((payload && payload.message) || '身份或权限失效（本地进度仍在）', 'denied');
      return;
    }
    if (reason === 'minigame_lower_priority') {
      setSyncText('你正在对局 / 观战中：小游戏状态未生效', 'denied');
    }
  });
  socket.on('invite_received', (payload) => {
    // 邀请只做提示，不自动离开棋盘；接受前先保存本地进度并尝试同步。
    showInvitePrompt(payload || {});
  });
  socket.on('invite_cancelled', () => hideInvitePrompt());
}

function showInvitePrompt(payload) {
  const box = el('mg-invite');
  const text = el('mg-invite-text');
  if (!box || !text) return;
  text.textContent = `${payload.from || '对方'} 邀请你对局${payload.mode ? `（${payload.mode}）` : ''}`;
  box.hidden = false;
}

function hideInvitePrompt() {
  const box = el('mg-invite');
  if (box) box.hidden = true;
}

async function acceptInvite() {
  hideInvitePrompt();
  saveLocal();
  try {
    // 不无限阻塞：给同步最多 3 秒，没传完也继续（队列随后自动续传）。
    await Promise.race([syncNow(), new Promise((resolve) => window.setTimeout(resolve, 3000))]);
  } catch (_) { /* 同步失败也继续 */ }
  if (socket) {
    socket.emit('minigame_leave', { game: '2048' });
    socket.emit('accept_invite', {});
  }
  setSyncText('正在进入对局…（进度已保存，未传完的操作会继续同步）');
  window.setTimeout(() => { window.location.href = '/'; }, 600);
}

function declineInvite() {
  hideInvitePrompt();
  if (socket) socket.emit('decline_invite', {});
}

async function openLeaderboard(windowMode = '14d') {
  const modal = el('mg-rank-modal');
  const body = el('mg-rank-body');
  modal.hidden = false;
  body.textContent = '正在读取…';
  try {
    const response = await fetch(`/api/minigame/2048/leaderboard?window=${windowMode}&limit=100`,
      { credentials: 'same-origin' });
    if (response.status === 401 || response.status === 403) {
      body.textContent = '身份或权限失效，无法查看排行榜。';
      return;
    }
    const data = await response.json();
    const entries = data.leaderboard?.entries || [];
    if (!entries.length) {
      body.innerHTML = '<p class="mg-hint">还没有已验证成绩。</p>';
      return;
    }
    body.innerHTML = `
      <table class="mg-rank-table">
        <thead><tr><th>名次</th><th>账号</th><th>总分</th><th>最高方块</th><th>验证时间</th></tr></thead>
        <tbody>${entries.map((item) => `
          <tr${data.me && item.user_id === data.me.user_id ? ' class="me"' : ''}>
            <td class="mg-rank-no">${item.rank}</td>
            <td>${escapeHtml(item.username || '')}</td>
            <td>${item.score}</td>
            <td>${item.max_rarity ? `${escapeHtml(item.max_rarity)}（${item.max_tile}）` : item.max_tile}</td>
            <td>${escapeHtml(String(item.verified_at || '').replace('T', ' ').replace('Z', ''))}</td>
          </tr>`).join('')}</tbody>
      </table>
      ${data.me ? `<p class="mg-hint">你：第 ${data.me.rank} 名 · ${data.me.score} 分</p>`
        : '<p class="mg-hint">你在当前榜单还没有已验证成绩。</p>'}
      ${(data.periods || []).length ? `<p class="mg-hint">奖期：${data.periods.map((p) =>
        `${escapeHtml(p.period_key)} ${p.status === 'paid' ? `已发 ${p.pool}` : '未发（' + escapeHtml(p.reason || '') + '）'}`).join('；')}</p>` : ''}`;
  } catch (_) {
    body.textContent = '离线，暂时读不到排行榜（棋盘不受影响）。';
  }
}

function escapeHtml(text) {
  return String(text == null ? '' : text).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[char]));
}

async function loadPrefs() {
  try {
    const response = await fetch('/api/minigame/2048/prefs', { credentials: 'same-origin' });
    if (!response.ok) return;
    const data = await response.json();
    el('mg-decline-invites').checked = !!data.prefs?.decline_invites;
    if (data.prefs?.show_numbers) {
      showNumbers = true;
      el('mg-show-numbers').checked = true;
    }
  } catch (_) { /* 离线：用本地开关 */ }
}

async function savePrefs() {
  try {
    await fetch('/api/minigame/2048/prefs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        decline_invites: el('mg-decline-invites').checked,
        show_numbers: el('mg-show-numbers').checked,
      }),
    });
  } catch (_) { /* 离线时偏好等下次再同步 */ }
}

/* ---------------- 启动 ---------------- */

async function boot() {
  buildLegend();
  const local = loadLocal();
  if (local) {
    state = {
      gameUid: local.gameUid,
      seed: local.seed,
      rngState: local.rngState,
      cells: local.cells,
      score: local.score,
      ops: String(local.ops || '').split(''),
      acked: Number(local.acked || 0),
      best: Number(local.best || local.score || 0),
      reachedShown: !!local.reachedShown,
      continued: !!local.continued,
      source: local.source || 'online',
      localNew: local.localNew === true,
      declined: !!local.declined,
      lastSyncLabel: '已从本机续局（联网后校验）',
    };
    renderBoard(false);
  }
  try {
    const response = await fetch('/api/minigame/2048/state', { credentials: 'same-origin' });
    if (response.status === 401 || response.status === 403) {
      identityRejected = true;
      setSyncText('身份或权限失效：请重新登录后再进入（本地进度仍在）', 'denied');
      if (!state) startLocalGame();
      return;
    }
    const data = await response.json();
    if (!state || !state.gameUid) {
      adoptServerState(data);
      state.best = Math.max(state.best || 0, state.score);
      saveLocal();
    } else {
      verifiedEl.textContent = String(data.verified?.score || 0);
      state.best = Math.max(state.best || 0, state.score);
      setSyncText('在线：正在校验本机进度…');
      scheduleSync(200);
    }
  } catch (_) {
    setSyncText('离线，本地已保存', 'offline');
    if (!state) startLocalGame();
  }
  await loadPrefs();
  renderBoard(false);
  boardEl.focus();
  window.addEventListener('online', () => { retryDelay = RETRY_BASE_MS; scheduleSync(200); });
  window.addEventListener('offline', () => setSyncText('离线，本地已保存', 'offline'));
  window.addEventListener('resize', () => scheduleTileFit());
  window.addEventListener('orientationchange', () => scheduleTileFit());
  document.addEventListener('visibilitychange', () => { if (!document.hidden) scheduleSync(200); });
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/minigame/2048/sw.js', { scope: '/minigame/2048' })
      .catch(() => { /* 缓存不可用不影响游玩 */ });
  }
  connectPresence();
  void syncNow();
}

el('mg-new').addEventListener('click', () => { void restartGame(); });
el('mg-invite-accept').addEventListener('click', () => { void acceptInvite(); });
el('mg-invite-decline').addEventListener('click', () => { declineInvite(); });
el('mg-rank').addEventListener('click', () => { void openLeaderboard('14d'); });
el('mg-show-numbers').addEventListener('change', (event) => {
  showNumbers = event.target.checked;
  renderBoard(false);
  scheduleTileFit();
  void savePrefs();
});
el('mg-decline-invites').addEventListener('change', () => { void savePrefs(); });
el('mg-animations').addEventListener('change', (event) => {
  animations = event.target.checked;
  document.documentElement.classList.toggle('mg-no-anim', !animations);
});
el('mg-rank-modal').addEventListener('click', (event) => {
  if (event.target.closest('[data-mg-close]')) el('mg-rank-modal').hidden = true;
  const tab = event.target.closest('[data-mg-window]');
  if (tab) {
    document.querySelectorAll('[data-mg-window]').forEach((btn) => {
      btn.classList.toggle('active', btn === tab);
    });
    void openLeaderboard(tab.dataset.mgWindow);
  }
});
if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  animations = false;
  document.documentElement.classList.add('mg-no-anim');
  el('mg-animations').checked = false;
}
void boot();
