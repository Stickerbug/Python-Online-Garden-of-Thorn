/* 休闲花园 ·「合成大花花」页面层。

   规则核心在 `suika_core.js`（纯逻辑、可重放），这里只负责：
   贴图归一化 → canvas 渲染 → 输入（拖动/键盘）→ 本地存档 → 界面状态。
   物理用 vendor 的 matter.js（UMD，页面用 <script> 先加载，挂到 window.Matter）。 */

import {
  ARENA,
  DROP_COOLDOWN_MS,
  MAX_TIER,
  RULES_VERSION,
  SuikaGame,
  TIERS,
  seedFromText,
  tierDef,
} from './suika_core.js';

const CONFIG = (() => {
  const node = document.getElementById('sk-config');
  if (!node) return {};
  try { return JSON.parse(node.textContent || '{}') || {}; } catch (_) { return {}; }
})();

const USER_KEY = String(CONFIG.userId || '0');
const SAVE_KEY = `gtn_suika.v1.save.u${USER_KEY}`;
const BEST_KEY = `gtn_suika.v1.best.u${USER_KEY}`;
const LEGEND_KEY = 'gtn_suika.v1.prefs';

const DEFAULT_SKIN = Object.freeze({ primary: '#FFE763', shape: 'oval', kind: '' });
const PLAYER_LOOK = Object.freeze({ x: 0.707, y: -0.707 });   // 固定看向右上 45°
const LOOK_OFFSET_X = 0.38;
const LOOK_OFFSET_Y = 0.56;

/* 每档的**兜底底色**：只在"贴图没加载出来"或"第 10 档玩家球"时用到。
   有贴图的档位不再画底色圆和描边——贴图本身就是这颗球的外框。 */
const TIER_COLORS = [
  { bg: '#d9e9f5', edge: '#a7c8dc' },   // Bubble
  { bg: '#f7f0dc', edge: '#d6c6a1' },   // Ant Egg
  { bg: '#e8453f', edge: '#b8332f' },   // Ladybug
  { bg: '#b08a5c', edge: '#7e5c34' },   // Ant Hole
  { bg: '#971c25', edge: '#6e1219' },   // Dark Ladybug
  { bg: '#35b455', edge: '#1e7f3c' },   // Cactus
  { bg: '#ede12a', edge: '#b4ab1d' },   // Uranium Barrel
  { bg: '#2f6e52', edge: '#1e4b38' },   // Gambler
  { bg: '#e6e85b', edge: '#c0c23c' },   // Shiny Ladybug
  { bg: '#b4b6b8', edge: '#8a8c8e' },   // Mecha Flower
  { bg: '#ffe763', edge: '#cfbb50' },   // Player（用皮肤色覆盖）
];

const SCAN = 256;
/* 贴图墨迹占球直径的比例：1 = 图片外框正好等于物理半径画出来的圆，
   这样"看上去挨住"就是"真的碰到"（没有底色圆兜着，缩小会让手感对不上）。 */
const BOX_FILL = 1;

const canvas = document.getElementById('sk-canvas');
const ctx = canvas ? canvas.getContext('2d') : null;
const scoreEl = document.getElementById('sk-score');
const bestEl = document.getElementById('sk-best');
const statusEl = document.getElementById('sk-status');
const nextChipEl = document.getElementById('sk-next-chip');
const nextNameEl = document.getElementById('sk-next-name');
const nextHintEl = document.getElementById('sk-next-hint');
const legendEl = document.getElementById('sk-legend-grid');
const overlayEl = document.getElementById('sk-overlay');
const overlayTitleEl = document.getElementById('sk-overlay-title');
const overlayTextEl = document.getElementById('sk-overlay-text');
const overlayScoreEl = document.getElementById('sk-overlay-score');
const overlayPrimaryEl = document.getElementById('sk-overlay-primary');
const overlaySecondaryEl = document.getElementById('sk-overlay-secondary');
const newButtonEl = document.getElementById('sk-new');
const animToggle = document.getElementById('sk-anim');
const aimToggle = document.getElementById('sk-aim');

const Matter = window.Matter || null;
const art = new Array(TIERS.length).fill(null);
const pops = [];
let playerSkin = { ...DEFAULT_SKIN };
let phelrenFrame = null;
let game = null;
let aimX = ARENA.width / 2;
let dragging = false;
let animationsEnabled = true;
let aimGuideEnabled = true;
let bestScore = 0;
let lastFrameAt = 0;
let lastDropAt = 0;
let overlayMode = '';
let pendingAction = null;

/* ---------- 小工具 ---------- */

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function hexToRgb(color) {
  const match = /^#?([0-9a-f]{6})$/i.exec(String(color || '').trim());
  if (!match) return { r: 255, g: 231, b: 99 };
  const value = parseInt(match[1], 16);
  return { r: (value >> 16) & 255, g: (value >> 8) & 255, b: value & 255 };
}

function rgbToHex({ r, g, b }) {
  const channel = (v) => clamp(Math.round(v), 0, 255).toString(16).padStart(2, '0');
  return `#${channel(r)}${channel(g)}${channel(b)}`;
}

function skinBorder(color) {
  const { r, g, b } = hexToRgb(color);
  return rgbToHex({ r: r * 0.81, g: g * 0.81, b: b * 0.81 });
}

function skinLuminance(color) {
  const { r, g, b } = hexToRgb(color);
  const srgb = [r, g, b].map((v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * srgb[0] + 0.7152 * srgb[1] + 0.0722 * srgb[2];
}

function readStored(key) {
  try { return window.localStorage.getItem(key); } catch (_) { return null; }
}

function writeStored(key, value) {
  try { window.localStorage.setItem(key, value); return true; } catch (_) { return false; }
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`图片加载失败：${src}`));
    img.src = src;
  });
}

function setStatus(text, { offline = false } = {}) {
  if (!statusEl) return;
  statusEl.textContent = text;
  statusEl.classList.toggle('is-offline', !!offline);
}

/* ---------- 贴图：加载 + 墨迹归一化 ---------- */

async function prepareArt(index) {
  const def = tierDef(index);
  if (!def.art) return null;
  const img = await loadImage(def.art);
  const buffer = document.createElement('canvas');
  buffer.width = SCAN;
  buffer.height = SCAN;
  const bufferCtx = buffer.getContext('2d');
  bufferCtx.drawImage(img, 0, 0, SCAN, SCAN);
  const data = bufferCtx.getImageData(0, 0, SCAN, SCAN).data;
  let minX = SCAN;
  let minY = SCAN;
  let maxX = -1;
  let maxY = -1;
  let sumR = 0;
  let sumG = 0;
  let sumB = 0;
  let count = 0;
  for (let y = 0; y < SCAN; y += 1) {
    for (let x = 0; x < SCAN; x += 1) {
      const offset = (y * SCAN + x) * 4;
      if (data[offset + 3] < 24) continue;
      if (x < minX) minX = x;
      if (y < minY) minY = y;
      if (x > maxX) maxX = x;
      if (y > maxY) maxY = y;
      sumR += data[offset];
      sumG += data[offset + 1];
      sumB += data[offset + 2];
      count += 1;
    }
  }
  if (!count) return { img, box: { cx: 0.5, cy: 0.5, w: 1, h: 1 }, avg: '#cccccc' };
  return {
    img,
    box: {
      cx: (minX + maxX + 1) / 2 / SCAN,
      cy: (minY + maxY + 1) / 2 / SCAN,
      w: (maxX - minX + 1) / SCAN,
      h: (maxY - minY + 1) / SCAN,
    },
    avg: rgbToHex({ r: sumR / count, g: sumG / count, b: sumB / count }),
  };
}

async function loadAllArt() {
  await Promise.all(TIERS.map(async (def, index) => {
    try {
      art[index] = await prepareArt(index);
    } catch (error) {
      console.warn('[suika] 贴图加载失败', def.id, error);
      art[index] = null;
    }
  }));
}

function drawSprite(target, sprite, x, y, radius, rotation = 0, alpha = 1, shadow = false) {
  if (!sprite) return;
  const { img, box } = sprite;
  const size = radius * 2 * BOX_FILL;
  const full = size / Math.max(box.w, box.h);
  target.save();
  target.globalAlpha = alpha;
  if (shadow) {
    // 很淡的原图（例如半透明的泡泡）在浅色底上会看不清：给贴图一层柔和投影，
    // 跟故事模式敌人立绘的处理一致。它是阴影，不是外框——形状仍由贴图自己决定。
    const scale = Math.max(1, Math.min(3, window.devicePixelRatio || 1));
    target.shadowColor = 'rgba(24, 34, 28, 0.32)';
    target.shadowBlur = Math.max(3, radius * 0.22) * scale;
  }
  target.translate(x, y);
  if (rotation) target.rotate(rotation);
  // 用整张图当源（3 参数形式）：不依赖 naturalWidth —— SVG 的固有尺寸可能是 0，
  // 那样 9 参数写法会算出一个画布外的源矩形，浏览器会**静默**什么都不画。
  target.drawImage(img, -box.cx * full, -box.cy * full, full, full);
  target.restore();
}

/* ---------- 玩家档：把皮肤画成球 ---------- */

function eyePath(target, shape, cx, cy, w, h) {
  target.beginPath();
  const left = cx - w / 2;
  const top = cy - h / 2;
  if (shape === 'diamond') {
    target.moveTo(cx, cy - h / 2);
    target.lineTo(cx + w / 2, cy);
    target.lineTo(cx, cy + h / 2);
    target.lineTo(cx - w / 2, cy);
    target.closePath();
    return;
  }
  if (shape === 'hexagon') {
    target.moveTo(left + w * 0.22, top);
    target.lineTo(left + w * 0.78, top);
    target.lineTo(left + w, cy);
    target.lineTo(left + w * 0.78, top + h);
    target.lineTo(left + w * 0.22, top + h);
    target.lineTo(left, cy);
    target.closePath();
    return;
  }
  if (shape === 'rectangle') {
    const radius = Math.min(w, h) * 0.18;
    if (typeof target.roundRect === 'function') target.roundRect(left, top, w, h, radius);
    else target.rect(left, top, w, h);
    return;
  }
  target.ellipse(cx, cy, w / 2, h / 2, 0, 0, Math.PI * 2);
}

function drawPlayerBall(target, x, y, radius) {
  const color = playerSkin.primary || DEFAULT_SKIN.primary;
  const edge = skinBorder(color);
  const inverted = skinLuminance(color) < 0.22;
  const feature = inverted ? '#ffffff' : '#111111';
  const pupil = inverted ? '#111111' : '#ffffff';
  const radiusSafe = radius;

  target.save();
  target.beginPath();
  target.arc(x, y, radiusSafe, 0, Math.PI * 2);
  target.fillStyle = color;
  target.fill();
  const borderWidth = Math.max(2, radiusSafe * 0.14);
  if (borderWidth > 0) {
    target.lineWidth = borderWidth;
    target.strokeStyle = edge;
    target.stroke();
  }

  if (playerSkin.kind === 'phelren' && phelrenFrame) {
    target.save();
    target.beginPath();
    target.arc(x, y, radiusSafe - borderWidth / 2, 0, Math.PI * 2);
    target.clip();
    const size = radiusSafe * 2;
    target.drawImage(phelrenFrame, x - size / 2, y - size / 2, size, size);
    target.restore();
    target.restore();
    return;
  }

  const eyeW = radiusSafe * 2 * 0.10;
  const eyeH = radiusSafe * 2 * 0.20;
  const eyeY = y - radiusSafe + radiusSafe * 2 * 0.32 + eyeH / 2;
  const leftX = x - radiusSafe + radiusSafe * 2 * 0.33 + eyeW / 2;
  const rightX = x + radiusSafe - radiusSafe * 2 * 0.33 - eyeW / 2;
  const pupilW = eyeW * 0.84;
  const pupilH = eyeH * 0.54;
  const offsetX = PLAYER_LOOK.x * LOOK_OFFSET_X * eyeW;
  const offsetY = PLAYER_LOOK.y * LOOK_OFFSET_Y * eyeH;

  const shape = playerSkin.shape || 'oval';
  target.fillStyle = feature;
  [leftX, rightX].forEach((eyeX) => {
    eyePath(target, shape, eyeX, eyeY, eyeW, eyeH);
    target.fill();
  });
  target.fillStyle = pupil;
  [leftX, rightX].forEach((eyeX) => {
    if (shape === 'diamond' || shape === 'hexagon') {
      eyePath(target, shape, eyeX + offsetX, eyeY + offsetY, pupilW, pupilH);
      target.fill();
      return;
    }
    target.beginPath();
    target.ellipse(eyeX + offsetX, eyeY + offsetY, pupilW / 2, pupilH / 2, 0, 0, Math.PI * 2);
    target.fill();
  });

  // 嘴：与站点皮肤同一条曲线（viewBox 100×56 → M20,18 C36,32 64,32 80,18）
  const mouthW = radiusSafe * 2 * 0.38;
  const mouthH = radiusSafe * 2 * 0.20;
  const mouthX = x - mouthW / 2;
  const mouthY = y - radiusSafe + radiusSafe * 2 * 0.63;
  const px = (v) => mouthX + (v / 100) * mouthW;
  const py = (v) => mouthY + (v / 56) * mouthH;
  target.beginPath();
  target.moveTo(px(20), py(18));
  target.bezierCurveTo(px(36), py(32), px(64), py(32), px(80), py(18));
  target.lineWidth = Math.max(1.5, radiusSafe * 0.09);
  target.strokeStyle = feature;
  target.lineCap = 'round';
  target.stroke();
  target.restore();
}

function tierColors(index) {
  if (index === MAX_TIER) {
    const color = playerSkin.primary || DEFAULT_SKIN.primary;
    return { bg: color, edge: skinBorder(color) };
  }
  return TIER_COLORS[index] || TIER_COLORS[0];
}

/* ---------- 渲染 ---------- */

function resizeCanvas() {
  if (!canvas) return;
  const dpr = Math.max(1, Math.min(3, window.devicePixelRatio || 1));
  canvas.width = Math.round(ARENA.width * dpr);
  canvas.height = Math.round(ARENA.height * dpr);
  if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

/* 主题色读一次就缓存：每帧都 getComputedStyle 太浪费，明暗切换时再刷新。 */
let themeColors = null;

function refreshThemeColors() {
  const styles = getComputedStyle(document.documentElement);
  const read = (name, fallback) => (styles.getPropertyValue(name) || '').trim() || fallback;
  themeColors = {
    arena: read('--sk-arena', '#E4E9E2'),
    board: read('--sk-board', '#CCD5CF'),
    edge: read('--sk-board-edge', '#B3BFB7'),
    danger: read('--sk-danger', '#C0392B'),
    accent: read('--sk-accent', '#4B3F8F'),
    text: read('--sk-text', '#2C3E50'),
  };
}

/** 当前瞄准位置（按下一颗的半径夹进可投放范围）。 */
function currentAimX() {
  if (!game) return ARENA.width / 2;
  const def = tierDef(game.nextTier);
  return clamp(aimX, ARENA.wall + def.radius, ARENA.width - ARENA.wall - def.radius);
}

function drawArena() {
  const { width, height, wall, loseLineY, dropLineY } = ARENA;
  if (!themeColors) refreshThemeColors();
  const { arena, board, edge, danger, accent, text } = themeColors;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = board;
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = arena;
  ctx.fillRect(wall, 0, width - wall * 2, height - wall);

  // 地板与侧墙
  ctx.fillStyle = edge;
  ctx.fillRect(0, height - wall, width, wall);
  ctx.fillRect(0, 0, wall, height);
  ctx.fillRect(width - wall, 0, wall, height);

  // 顶部：半透明大分数水印（画在失败线上方的空档里）
  if (game) {
    ctx.save();
    ctx.globalAlpha = 0.12;
    ctx.fillStyle = text;
    ctx.font = 'italic bold 54px "PingFang SC", "Microsoft YaHei", system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(game.score), width / 2, loseLineY / 2 - 2);
    ctx.restore();
  }

  // 失败线 + 线上文字
  const inDanger = !!(game && game.danger);
  ctx.save();
  ctx.setLineDash([14, 12]);
  ctx.lineWidth = 4;
  ctx.strokeStyle = inDanger ? danger : 'rgba(196, 92, 74, 0.55)';
  ctx.beginPath();
  ctx.moveTo(wall, loseLineY);
  ctx.lineTo(width - wall, loseLineY);
  ctx.stroke();
  ctx.restore();
  ctx.save();
  ctx.globalAlpha = inDanger ? 0.95 : 0.7;
  ctx.fillStyle = danger;
  ctx.font = 'bold 15px "PingFang SC", "Microsoft YaHei", system-ui, sans-serif';
  ctx.textAlign = 'left';
  ctx.textBaseline = 'bottom';
  ctx.fillText('失败线', wall + 10, loseLineY - 6);
  ctx.restore();

  // 落点预测：虚线 + 落点圆圈 + 顶部那颗待投放的球
  if (aimGuideEnabled && game && !game.gameOver) {
    const def = tierDef(game.nextTier);
    const x = currentAimX();
    const land = game.predictLanding(x, game.nextTier);
    // 刚投放过的一小段时间里淡入，避免和老球的位置对不上
    const sinceDrop = performance.now() - lastDropAt;
    const alpha = lastDropAt ? Math.max(0, Math.min(1, (sinceDrop - 180) / 220)) : 1;
    if (alpha > 0.02) {
      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.setLineDash([9, 9]);
      ctx.lineWidth = 3;
      ctx.strokeStyle = accent;
      ctx.beginPath();
      ctx.moveTo(x, dropLineY + def.radius);
      ctx.lineTo(land.x, land.y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.arc(land.x, land.y, def.radius, 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();
    }
    const sprite = art[game.nextTier];
    if (game.nextTier === MAX_TIER) {
      ctx.save();
      ctx.globalAlpha = 0.9;
      drawPlayerBall(ctx, x, dropLineY + def.radius, def.radius);
      ctx.restore();
    } else if (sprite) {
      drawSprite(ctx, sprite, x, dropLineY + def.radius, def.radius, 0, 0.9, true);
    } else {
      ctx.save();
      ctx.globalAlpha = 0.9;
      ctx.beginPath();
      ctx.arc(x, dropLineY + def.radius, def.radius, 0, Math.PI * 2);
      ctx.fillStyle = tierColors(game.nextTier).bg;
      ctx.fill();
      ctx.restore();
    }
  }
}

function drawBalls() {
  if (!game) return;
  for (const record of game.balls) {
    const tier = record.tier;
    const def = tierDef(tier);
    const isPlayer = tier === MAX_TIER;
    const x = record.body.position.x;
    const y = record.body.position.y;
    // 有贴图的档位：只画贴图，贴图自己就是球的外框（不再叠一层底色圆）。
    if (isPlayer) {
      drawPlayerBall(ctx, x, y, def.radius);
    } else if (art[tier]) {
      drawSprite(ctx, art[tier], x, y, def.radius, record.body.angle || 0, 1, true);
    } else {
      const colors = tierColors(tier);
      ctx.save();
      ctx.beginPath();
      ctx.arc(x, y, def.radius, 0, Math.PI * 2);
      ctx.fillStyle = colors.bg;
      ctx.fill();
      ctx.lineWidth = Math.max(2, def.radius * 0.14);
      ctx.strokeStyle = colors.edge;
      ctx.stroke();
      ctx.fillStyle = 'rgba(0,0,0,0.45)';
      ctx.font = `700 ${Math.round(def.radius * 0.5)}px system-ui, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(def.en, x, y);
      ctx.restore();
    }
  }
}

function drawPops(now) {
  if (!animationsEnabled) return;
  for (let i = pops.length - 1; i >= 0; i -= 1) {
    const pop = pops[i];
    const age = now - pop.at;
    if (age > 320) { pops.splice(i, 1); continue; }
    const t = age / 320;
    const radius = pop.radius * (0.9 + t * 0.5);
    ctx.save();
    ctx.globalAlpha = (1 - t) * 0.75;
    ctx.lineWidth = Math.max(2, pop.radius * 0.16 * (1 - t));
    ctx.strokeStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(pop.x, pop.y, radius, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }
}

function render(now = performance.now()) {
  if (!ctx) return;
  drawArena();
  drawBalls();
  drawPops(now);
}

/* ---------- 界面状态 ---------- */

function updateScore() {
  const score = game ? game.score : 0;
  if (scoreEl) scoreEl.textContent = String(score);
  if (score > bestScore) {
    bestScore = score;
    writeStored(BEST_KEY, String(bestScore));
  }
  if (bestEl) bestEl.textContent = String(bestScore);
}

function updateNextChip() {
  if (!game) return;
  const tier = game.nextTier;
  const def = tierDef(tier);
  const colors = tierColors(tier);
  if (nextChipEl) {
    // 有贴图就直接显示贴图本身（不套底色圆/描边）；玩家档没有贴图，用皮肤色圆代替。
    nextChipEl.style.backgroundImage = def.art ? `url("${def.art}")` : 'none';
    nextChipEl.style.backgroundColor = def.art ? 'transparent' : colors.bg;
    nextChipEl.style.borderColor = def.art ? 'transparent' : colors.edge;
  }
  if (nextNameEl) nextNameEl.textContent = def.en;
  if (nextHintEl) {
    const maxTier = game.maxSpawnTier;
    nextHintEl.textContent = `当前可抽到 ${tierDef(maxTier).en}（${game.score} 分解锁）`;
  }
}

function buildLegend() {
  if (!legendEl) return;
  legendEl.textContent = '';
  TIERS.forEach((def, index) => {
    const item = document.createElement('div');
    item.className = 'sk-chain-item';
    item.dataset.tier = String(index);
    const ball = document.createElement('span');
    ball.className = 'sk-chain-ball';
    const colors = tierColors(index);
    if (def.art) {
      ball.style.backgroundColor = 'transparent';
      ball.style.borderColor = 'transparent';
      ball.style.backgroundImage = `url("${def.art}")`;
    } else {
      ball.style.backgroundColor = colors.bg;
      ball.style.borderRadius = '50%';
    }
    const name = document.createElement('span');
    name.className = 'sk-chain-name';
    name.textContent = def.en;
    const score = document.createElement('span');
    score.className = 'sk-chain-score';
    score.textContent = `${def.score} 分`;
    item.append(ball, name, score);
    legendEl.append(item);
  });
  markNextInLegend();
}

/** 合成路线里高亮"下一枚"那一档。 */
function markNextInLegend() {
  if (!legendEl || !game) return;
  const next = String(game.nextTier);
  legendEl.querySelectorAll('.sk-chain-item').forEach((item) => {
    item.classList.toggle('is-next', item.dataset.tier === next);
  });
}

function showOverlay(mode) {
  if (!overlayEl) return;
  overlayMode = mode;
  overlayEl.hidden = false;
  if (mode === 'gameover') {
    if (overlayTitleEl) overlayTitleEl.textContent = '游戏结束';
    if (overlayTextEl) overlayTextEl.textContent = '有花花在判负线上停满 1 秒了。';
    if (overlayScoreEl) overlayScoreEl.textContent = String(game ? game.score : 0);
    if (overlayPrimaryEl) overlayPrimaryEl.textContent = '再来一局';
    if (overlaySecondaryEl) overlaySecondaryEl.hidden = true;
  } else if (mode === 'confirm') {
    if (overlayTitleEl) overlayTitleEl.textContent = '重新开始？';
    if (overlayTextEl) overlayTextEl.textContent = '当前这一局的进度会被丢弃。';
    if (overlayScoreEl) overlayScoreEl.textContent = String(game ? game.score : 0);
    if (overlayPrimaryEl) overlayPrimaryEl.textContent = '重新开始';
    if (overlaySecondaryEl) {
      overlaySecondaryEl.hidden = false;
      overlaySecondaryEl.textContent = '取消';
    }
  }
}

function hideOverlay() {
  if (overlayEl) overlayEl.hidden = true;
  overlayMode = '';
}

/* ---------- 存档 ---------- */

function saveLocal({ gameOver = false } = {}) {
  if (!game) return;
  const payload = {
    v: RULES_VERSION,
    seed: game.seed,
    score: game.score,
    gameOver: gameOver || game.gameOver,
    timeMs: Math.round(game.timeMs),
    drops: game.dropLog.map((entry) => ({ t: entry.t, x: entry.x })),
    savedAt: Date.now(),
  };
  const ok = writeStored(SAVE_KEY, JSON.stringify(payload));
  if (ok) setStatus(overlayMode === 'gameover' ? '本局结束' : '已保存到本机');
  else setStatus('无法写入本机存储：进度不会保留', { offline: true });
}

function loadLocal() {
  const raw = readStored(SAVE_KEY);
  if (!raw) return null;
  try {
    const data = JSON.parse(raw);
    // 规则版本不同的旧存档直接作废（v2 改了生成规则与判负判定，重放会对不上）
    if (!data || data.v !== RULES_VERSION || !Array.isArray(data.drops) || !data.seed) return null;
    return data;
  } catch (_) {
    return null;
  }
}

function newSeed() {
  const text = `${USER_KEY}:${Date.now()}:${Math.random().toString(36).slice(2, 10)}`;
  return seedFromText(text) >>> 0;
}

function startGame({ seed = newSeed(), drops = [], uptoMs = 0, restored = false } = {}) {
  game = new SuikaGame(Matter, { seed });
  if (drops.length) {
    game.seekTo(0);
    for (const entry of drops) {
      game.seekTo(Number(entry.t) || 0);
      game.drop(Number(entry.x) || 0);
    }
    // 存档记的是"最后一次投放之后又过了多久"：重放到同一时刻，球就停在刷新前的位置。
    game.seekTo(Number(uptoMs) || 0);
    game.takeEvents();
  }
  pops.length = 0;
  aimX = ARENA.width / 2;
  hideOverlay();
  updateScore();
  updateNextChip();
  if (restored) {
    setStatus(`已恢复上一局（${drops.length} 次投放）`);
  } else {
    setStatus('新的一局，已保存到本机');
    saveLocal();
  }
}

function requestNewGame() {
  const played = game && (game.totalDrops > 0) && !game.gameOver;
  if (played) {
    pendingAction = () => { startGame(); };
    showOverlay('confirm');
    return;
  }
  startGame();
}

/* ---------- 输入 ---------- */

function canvasXFromEvent(event) {
  const rect = canvas.getBoundingClientRect();
  const ratio = ARENA.width / rect.width;
  return clamp((event.clientX - rect.left) * ratio, 0, ARENA.width);
}

function updateAim(clientX) {
  if (!game) return;
  const def = tierDef(game.nextTier);
  aimX = clamp(clientX, ARENA.wall + def.radius, ARENA.width - ARENA.wall - def.radius);
}

function dropAtAim() {
  if (!game || game.gameOver) return;
  const result = game.drop(aimX);
  if (!result.ok) {
    if (result.reason === 'cooldown') setStatus(`投放间隔 ${(DROP_COOLDOWN_MS / 1000).toFixed(1)} 秒`);
    return;
  }
  game.takeEvents();
  updateScore();
  updateNextChip();
  markNextInLegend();
  lastDropAt = performance.now();
  saveLocal();
}

function bindInput() {
  if (!canvas) return;
  canvas.addEventListener('pointerdown', (event) => {
    if (event.button != null && event.button !== 0 && event.pointerType === 'mouse') return;
    dragging = true;
    updateAim(canvasXFromEvent(event));
    try { canvas.setPointerCapture(event.pointerId); } catch (_) { /* 忽略 */ }
    event.preventDefault();
  });
  canvas.addEventListener('pointermove', (event) => {
    if (!dragging && event.pointerType !== 'mouse') return;
    updateAim(canvasXFromEvent(event));
    if (dragging) event.preventDefault();
  });
  const finish = (event) => {
    if (!dragging) return;
    dragging = false;
    updateAim(canvasXFromEvent(event));
    dropAtAim();
    event.preventDefault();
  };
  canvas.addEventListener('pointerup', finish);
  canvas.addEventListener('pointercancel', (event) => {
    dragging = false;
    event.preventDefault();
  });
  canvas.addEventListener('contextmenu', (event) => event.preventDefault());

  window.addEventListener('keydown', (event) => {
    const target = event.target;
    if (target instanceof HTMLElement
      && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))) return;
    if (!game || game.gameOver) return;
    const step = event.shiftKey ? 48 : 16;
    const key = event.key;
    if (key === 'ArrowLeft' || key === 'a' || key === 'A') { aimX = clamp(aimX - step, ARENA.wall, ARENA.width - ARENA.wall); event.preventDefault(); return; }
    if (key === 'ArrowRight' || key === 'd' || key === 'D') { aimX = clamp(aimX + step, ARENA.wall, ARENA.width - ARENA.wall); event.preventDefault(); return; }
    if (key === ' ' || key === 'Spacebar' || key === 'ArrowDown' || key === 'Enter') {
      dropAtAim();
      event.preventDefault();
    }
  });
}

/* ---------- 事件与循环 ---------- */

function handleEvents(events) {
  for (const event of events) {
    if (event.type === 'merge') {
      if (animationsEnabled) {
        pops.push({ x: event.x, y: event.y, radius: tierDef(event.nextTier).radius, at: performance.now() });
      }
      updateScore();
    } else if (event.type === 'game_over') {
      saveLocal({ gameOver: true });
      showOverlay('gameover');
    }
  }
}

function frame(now) {
  if (!lastFrameAt) lastFrameAt = now;
  const dt = Math.min(120, Math.max(0, now - lastFrameAt));
  lastFrameAt = now;
  if (game && !document.hidden) {
    handleEvents(game.advance(dt));
    updateScore();
  }
  render(now);
  requestAnimationFrame(frame);
}

/* ---------- 玩家皮肤 ---------- */

async function loadPlayerSkin() {
  try {
    const response = await fetch('/api/auth/me', { credentials: 'same-origin' });
    if (!response.ok) return;
    const data = await response.json();
    const user = data && data.user ? data.user : null;
    if (!user) return;
    const skin = user.skin || {};
    playerSkin = {
      primary: /^#[0-9a-fA-F]{6}$/.test(String(skin.primary_color || '')) ? String(skin.primary_color).toUpperCase() : DEFAULT_SKIN.primary,
      shape: ['oval', 'rectangle', 'diamond', 'hexagon'].includes(String(skin.eye_shape || '')) ? String(skin.eye_shape) : DEFAULT_SKIN.shape,
      kind: String(user.avatar_kind || '') === 'phelren' ? 'phelren' : '',
    };
    if (playerSkin.kind === 'phelren') {
      phelrenFrame = await loadImage('/static/assets/player-avatars/phelren-frame.svg').catch(() => null);
    }
  } catch (error) {
    console.warn('[suika] 读取皮肤失败，用初始皮肤', error);
  }
  TIER_COLORS[MAX_TIER] = tierColors(MAX_TIER);
  buildLegend();
  updateNextChip();
}

/* ---------- 偏好 ---------- */

function loadPrefs() {
  try {
    const data = JSON.parse(readStored(LEGEND_KEY) || '{}');
    if (typeof data.animations === 'boolean') animationsEnabled = data.animations;
    if (typeof data.aim === 'boolean') aimGuideEnabled = data.aim;
  } catch (_) { /* 用默认值 */ }
  if (animToggle) animToggle.checked = animationsEnabled;
  if (aimToggle) aimToggle.checked = aimGuideEnabled;
}

function savePrefs() {
  writeStored(LEGEND_KEY, JSON.stringify({ animations: animationsEnabled, aim: aimGuideEnabled }));
}

/* ---------- 启动 ---------- */

function bindUi() {
  if (newButtonEl) newButtonEl.addEventListener('click', () => requestNewGame());
  if (overlayPrimaryEl) {
    overlayPrimaryEl.addEventListener('click', () => {
      const action = overlayMode === 'confirm' ? pendingAction : null;
      pendingAction = null;
      hideOverlay();
      if (action) action();
      else startGame();
    });
  }
  if (overlaySecondaryEl) {
    overlaySecondaryEl.addEventListener('click', () => {
      pendingAction = null;
      if (overlayMode === 'confirm') hideOverlay();
    });
  }
  if (animToggle) {
    animToggle.addEventListener('change', () => {
      animationsEnabled = animToggle.checked;
      savePrefs();
    });
  }
  if (aimToggle) {
    aimToggle.addEventListener('change', () => {
      aimGuideEnabled = aimToggle.checked;
      savePrefs();
    });
  }
  if (canvas) {
    canvas.addEventListener('pointermove', (event) => {
      if (event.pointerType === 'mouse' && !dragging) updateAim(canvasXFromEvent(event));
    });
  }
  window.addEventListener('beforeunload', () => saveLocal());
  window.addEventListener('online', () => setStatus('网络已恢复'));
  window.addEventListener('offline', () => setStatus('离线：本机已保存', { offline: true }));
  window.addEventListener('resize', () => { resizeCanvas(); render(); });
  try {
    new MutationObserver(() => { refreshThemeColors(); render(); })
      .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  } catch (_) { /* 浏览器不支持就算了，颜色退回默认值 */ }
}

async function boot() {
  if (!canvas || !ctx) return;
  if (!Matter) {
    setStatus('物理引擎没有加载出来，刷新试试', { offline: true });
    return;
  }
  loadPrefs();
  resizeCanvas();
  refreshThemeColors();
  bestScore = Number(readStored(BEST_KEY) || '0') || 0;
  if (bestEl) bestEl.textContent = String(bestScore);
  buildLegend();
  await loadAllArt();
  const saved = loadLocal();
  if (saved && !saved.gameOver && saved.drops.length) {
    startGame({ seed: saved.seed, drops: saved.drops, uptoMs: saved.timeMs, restored: true });
  } else {
    startGame();
  }
  updateNextChip();
  bindInput();
  bindUi();
  loadPlayerSkin();
  attachPresence();
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/minigame/suika/sw.js', { scope: '/minigame/suika' })
      .catch(() => { /* 缓存不可用不影响游玩 */ });
  }
  // 浏览器探针用的只读钩子（不参与玩法）
  window.__skSnapshot = () => (game ? game.snapshot() : null);
  window.__skArt = () => art.map((item) => (item ? { avg: item.avg, w: item.box.w, h: item.box.h } : null));
  window.__skBooted = true;
  requestAnimationFrame(frame);
}

/** 在线状态 + 对局邀请：走休闲花园共用的 minigame-presence.js（服务端认注册表里的 gameKey）。 */
function attachPresence() {
  const presence = window.GtnMinigamePresence;
  if (!presence) return;
  presence.attach({
    gameKey: CONFIG.gameKey || 'suika',
    nickname: CONFIG.username || '',
    inviteBoxId: 'sk-invite',
    inviteTextId: 'sk-invite-text',
    acceptBtnId: 'sk-invite-accept',
    declineBtnId: 'sk-invite-decline',
    declineToggleId: 'sk-decline-invites',
    // 连接类信息不抢状态栏（那里在显示存档状态），只有被拒绝/出错才提示
    onStatus: (text, kind) => {
      if (kind === 'denied' || kind === 'error') setStatus(text, { offline: true });
    },
    // 接受邀请前先把这一局存好（云同步接入后这里会顺便等一次上传）
    beforeAccept: async () => { saveLocal(); },
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => { boot(); });
} else {
  boot();
}
