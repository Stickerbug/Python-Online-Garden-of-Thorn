/* 休闲花园 ·「合成大花花」页面层。

   规则核心在 `suika_core.js`（纯逻辑、可重放），这里只负责：
   贴图归一化 → canvas 渲染 → 输入（拖动/键盘）→ 本地存档 → 界面状态。
   物理用 vendor 的 matter.js（UMD，页面用 <script> 先加载，挂到 window.Matter）。 */

import {
  ARENA,
  DROP_COOLDOWN_MS,
  MAX_TIER,
  RULES_VERSION,
  SPAWN_GATE_SCORES,
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
/* 玩家档的视线：与游戏 skinLookCssVars 同一套系数（look × 常量 = 瞳孔自身尺寸的偏移比例）。
   游戏里 look 是动态的（看向目标），这里固定看向右上 45°，让球像在望向棋盘。 */
const PLAYER_LOOK = Object.freeze({ x: 0.707, y: -0.707 });
const SKIN_LOOK_OFFSET = Object.freeze({ x: 0.38, y: 0.56 });

/* 玩家球的脸部几何，全部以"直径占比"表示——与游戏 .skin-avatar 的 CSS 逐项对齐
   （border 7.5cqi、眼睛 10%×20% @ top32%/inset33%、瞳孔 84%×54%、嘴 top63% 38%×20%
   stroke 5.6/100）。菱形眼在游戏里更大（12%×22% @ 31%/32%），菱形/六边形的瞳孔是
   62%×62%。drawPlayerBall（canvas）与 playerBallSvg（DOM 预览）共用这份表。 */
const SKIN_FEATURES = Object.freeze({
  eye: Object.freeze({ w: 0.10, h: 0.20, top: 0.32, inset: 0.33 }),
  pupil: Object.freeze({ w: 0.84, h: 0.54 }),
  diamondEye: Object.freeze({ w: 0.12, h: 0.22, top: 0.31, inset: 0.32 }),
  smallPupil: Object.freeze({ w: 0.62, h: 0.62 }),
  mouth: Object.freeze({ w: 0.38, h: 0.20, top: 0.63, stroke: 0.056 }),
  border: 0.075,
});

function skinFeatureGeometry(shape) {
  if (shape === 'diamond') {
    return { eye: SKIN_FEATURES.diamondEye, pupil: SKIN_FEATURES.smallPupil };
  }
  if (shape === 'hexagon') {
    return { eye: SKIN_FEATURES.eye, pupil: SKIN_FEATURES.smallPupil };
  }
  return { eye: SKIN_FEATURES.eye, pupil: SKIN_FEATURES.pupil };
}

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
/* 柔和投影直接烘焙进缓存贴图：运行时逐球设 shadowBlur 是每帧一次的软件模糊，
   低端机上正是卡顿主因（反馈：性能较差的设备会比较卡）。烘焙时按 SCAN 比例取
   blur ≈ 0.22×半径（与原先 drawSprite 里的取法一致），缩放绘制时阴影随图等比。 */
const SHADOW_BAKE_MARGIN = Math.ceil(SCAN * 0.16);

const canvas = document.getElementById('sk-canvas');
const ctx = canvas ? canvas.getContext('2d') : null;
const scoreEl = document.getElementById('sk-score');
const bestEl = document.getElementById('sk-best');
const statusEl = document.getElementById('sk-status');
const verifiedEl = document.getElementById('sk-verified');
const rankBodyEl = document.getElementById('sk-rank-body');
const rankNoteEl = document.getElementById('sk-rank-note');
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

/* 云同步状态：每颗球落定/每次分数增加都上传（失败进重试，离线不阻塞游玩）。 */
const syncState = {
  gameUid: '',
  acked: 0,          // 服务端已确认的投放数
  verified: 0,       // 已验证入榜的最高分
  timer: null,
  inflight: false,
  lastError: '',
};

/* 进行中的云端重开。syncNow 要先等它落地：否则第一次同步会从 /state 领到
   「分数更高的旧局」，新一局立刻被判「分数回退」，到下次投放前都进不了榜。 */
let cloudRestartPromise = null;

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

/* 撤回通知里的昵称要转义后再进 innerHTML（与 2048 页、共用聊天渲染同口径）。 */
function escapeHtml(text) {
  return String(text == null ? '' : text)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
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
  const ink = { cx: (minX + maxX + 1) / 2 / SCAN, cy: (minY + maxY + 1) / 2 / SCAN, w: (maxX - minX + 1) / SCAN, h: (maxY - minY + 1) / SCAN };
  /* 带投影的缓存贴图：墨迹居中放进"SCAN + 2×margin"的画布，阴影一次性画好。
     box 相对整张烘焙图重算，drawSprite 缩放时墨迹仍精确落在物理半径上。 */
  const size = SCAN + SHADOW_BAKE_MARGIN * 2;
  const baked = document.createElement('canvas');
  baked.width = size;
  baked.height = size;
  const bakedCtx = baked.getContext('2d');
  bakedCtx.shadowColor = 'rgba(24, 34, 28, 0.32)';
  bakedCtx.shadowBlur = Math.max(3, SCAN * 0.11);
  bakedCtx.drawImage(img, SHADOW_BAKE_MARGIN, SHADOW_BAKE_MARGIN, SCAN, SCAN);
  return {
    img: baked,
    box: {
      cx: (SHADOW_BAKE_MARGIN + ink.cx * SCAN) / size,
      cy: (SHADOW_BAKE_MARGIN + ink.cy * SCAN) / size,
      w: (ink.w * SCAN) / size,
      h: (ink.h * SCAN) / size,
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

function drawSprite(target, sprite, x, y, radius, rotation = 0, alpha = 1) {
  if (!sprite) return;
  const { img, box } = sprite;
  const size = radius * 2 * BOX_FILL;
  const full = size / Math.max(box.w, box.h);
  target.save();
  target.globalAlpha = alpha;
  target.translate(x, y);
  if (rotation) target.rotate(rotation);
  // 用整张图当源（3 参数形式）：不依赖 naturalWidth —— SVG 的固有尺寸可能是 0，
  // 那样 9 参数写法会算出一个画布外的源矩形，浏览器会**静默**什么都不画。
  // 柔和投影已在 prepareArt 里烘焙进缓存图（原先逐帧 shadowBlur 是低端设备卡顿主因）。
  target.drawImage(img, -box.cx * full, -box.cy * full, full, full);
  target.restore();
}

/* ---------- 玩家档：把皮肤画成球 ---------- */

function eyePath(target, shape, cx, cy, w, h) {
  target.beginPath();
  const left = cx - w / 2;
  const top = cy - h / 2;
  if (shape === 'diamond') {
    target.moveTo(cx, top);
    target.lineTo(cx + w / 2, cy);
    target.lineTo(cx, cy + h / 2);
    target.lineTo(left, cy);
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
    /* 游戏里矩形眼是 2px 圆角、瞳孔 1px 圆角：按球径折算，小圆角而不是直角 */
    const radius = Math.min(w, h) * 0.16;
    if (typeof target.roundRect === 'function') target.roundRect(left, top, w, h, radius);
    else target.rect(left, top, w, h);
    return;
  }
  target.ellipse(cx, cy, w / 2, h / 2, 0, 0, Math.PI * 2);
}

/* 脸（眼睛+瞳孔+嘴），以球心 (x,y)、半径 radius 画。canvas 与 SVG 预览共用同一几何表。 */
function drawSkinFace(target, x, y, radius, feature, pupilColor) {
  const shape = playerSkin.shape || 'oval';
  const { eye, pupil } = skinFeatureGeometry(shape);
  const eyeW = radius * 2 * eye.w;
  const eyeH = radius * 2 * eye.h;
  const eyeY = y - radius + radius * 2 * eye.top + eyeH / 2;
  const leftX = x - radius + radius * 2 * eye.inset + eyeW / 2;
  const rightX = x + radius - radius * 2 * eye.inset - eyeW / 2;

  const offsetX = PLAYER_LOOK.x * SKIN_LOOK_OFFSET.x * pupil.w;
  const offsetY = PLAYER_LOOK.y * SKIN_LOOK_OFFSET.y * pupil.h;
  const pupilW = eyeW * pupil.w;
  const pupilH = eyeH * pupil.h;
  const roundPupil = shape !== 'diamond' && shape !== 'hexagon';

  target.fillStyle = feature;
  [leftX, rightX].forEach((eyeX) => {
    eyePath(target, shape, eyeX, eyeY, eyeW, eyeH);
    target.fill();
  });
  target.fillStyle = pupilColor;
  [leftX, rightX].forEach((eyeX) => {
    if (!roundPupil) {
      eyePath(target, shape, eyeX + offsetX, eyeY + offsetY, pupilW, pupilH);
      target.fill();
      return;
    }
    target.save();
    if (shape === 'rectangle') {
      const r = Math.min(pupilW, pupilH) * 0.16;
      target.beginPath();
      if (typeof target.roundRect === 'function') target.roundRect(eyeX + offsetX - pupilW / 2, eyeY + offsetY - pupilH / 2, pupilW, pupilH, r);
      else target.rect(eyeX + offsetX - pupilW / 2, eyeY + offsetY - pupilH / 2, pupilW, pupilH);
      target.fill();
      target.restore();
      return;
    }
    target.beginPath();
    target.ellipse(eyeX + offsetX, eyeY + offsetY, pupilW / 2, pupilH / 2, 0, 0, Math.PI * 2);
    target.fill();
    target.restore();
  });

  /* 嘴：与游戏 .skin-mouth 同位（top 63%、宽 38%、高 20%），同一条曲线
     （viewBox 100×56 → M20,18 C36,32 64,32 80,18），线宽按直径折算（stroke 5.6/100）。 */
  const mouthW = radius * 2 * SKIN_FEATURES.mouth.w;
  const mouthH = radius * 2 * SKIN_FEATURES.mouth.h;
  const mouthX = x - mouthW / 2;
  const mouthY = y - radius + radius * 2 * SKIN_FEATURES.mouth.top;
  const px = (v) => mouthX + (v / 100) * mouthW;
  const py = (v) => mouthY + (v / 56) * mouthH;
  target.beginPath();
  target.moveTo(px(20), py(18));
  target.bezierCurveTo(px(36), py(32), px(64), py(32), px(80), py(18));
  target.lineWidth = Math.max(1.2, radius * 2 * SKIN_FEATURES.mouth.stroke);
  target.strokeStyle = feature;
  target.lineCap = 'round';
  target.lineJoin = 'round';
  target.stroke();
}

function drawPlayerBall(target, x, y, radius) {
  const color = playerSkin.primary || DEFAULT_SKIN.primary;
  const edge = skinBorder(color);
  const inverted = skinLuminance(color) < 0.22;
  const feature = inverted ? '#ffffff' : '#111111';
  const pupil = inverted ? '#111111' : '#ffffff';
  const diameter = radius * 2;

  target.save();
  target.beginPath();
  target.arc(x, y, radius, 0, Math.PI * 2);
  target.fillStyle = color;
  target.fill();
  /* 边框与游戏 .skin-avatar 的 7.5cqi 一致（从半径向内画，不改变物理外沿） */
  const borderWidth = diameter * SKIN_FEATURES.border;
  if (borderWidth > 0) {
    target.lineWidth = borderWidth;
    target.strokeStyle = edge;
    target.stroke();
  }
  /* 内侧高光/阴影：对应游戏 inset box-shadow（顶部白 18%、底部黑 8%）。 */
  const highlight = target.createLinearGradient(x, y - radius, x, y + radius);
  highlight.addColorStop(0, 'rgba(255, 255, 255, 0.18)');
  highlight.addColorStop(0.5, 'rgba(255, 255, 255, 0)');
  highlight.addColorStop(1, 'rgba(0, 0, 0, 0.08)');
  target.fillStyle = highlight;
  target.beginPath();
  target.arc(x, y, radius - (borderWidth > 0 ? borderWidth / 2 : 0), 0, Math.PI * 2);
  target.fill();

  if (playerSkin.kind === 'phelren' && phelrenFrame) {
    target.save();
    target.beginPath();
    target.arc(x, y, radius - borderWidth / 2, 0, Math.PI * 2);
    target.clip();
    const size = radius * 2;
    target.drawImage(phelrenFrame, x - size / 2, y - size / 2, size, size);
    target.restore();
    target.restore();
    return;
  }

  drawSkinFace(target, x, y, radius, feature, pupil);
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

  // 顶部：半透明大分数水印（画在失败线上方的空档里）。
  // 中文没有真斜体，合成斜体字形会发虚——用站内字体常规字重 + 更淡的透明度。
  if (game) {
    ctx.save();
    ctx.globalAlpha = 0.10;
    ctx.fillStyle = text;
    ctx.font = '400 54px Kreadon, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif';
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
      drawSprite(ctx, sprite, x, dropLineY + def.radius, def.radius, 0, 0.9);
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
      drawSprite(ctx, art[tier], x, y, def.radius, record.body.angle || 0, 1);
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

let lastShownScore = null;
let lastShownBest = null;

function updateScore() {
  const score = game ? game.score : 0;
  /* 每帧调用但只在变化时写 DOM / 标脏（画布大分数水印也要跟着重画） */
  if (score !== lastShownScore) {
    lastShownScore = score;
    if (scoreEl) scoreEl.textContent = String(score);
    markRenderDirty();
  }
  if (score > bestScore) {
    bestScore = score;
    writeStored(BEST_KEY, String(bestScore));
  }
  if (bestEl && bestScore !== lastShownBest) {
    lastShownBest = bestScore;
    bestEl.textContent = String(bestScore);
  }
}

function updateNextChip() {
  if (!game) return;
  const tier = game.nextTier;
  const def = tierDef(tier);
  if (nextChipEl) {
    if (def.art) {
      // 有贴图就直接显示贴图本身（不套底色圆/描边）
      nextChipEl.style.backgroundImage = `url("${def.art}")`;
      nextChipEl.style.backgroundColor = 'transparent';
      nextChipEl.style.borderColor = 'transparent';
      nextChipEl.classList.remove('sk-player-preview');
      nextChipEl.innerHTML = '';
    } else if (tier === MAX_TIER) {
      // 玩家档：换成与游戏一致的带脸小预览（之前只剩一个底色圆）
      nextChipEl.style.backgroundImage = 'none';
      nextChipEl.style.backgroundColor = 'transparent';
      nextChipEl.style.borderColor = 'transparent';
      if (!nextChipEl.querySelector('.skin-avatar')) {
        nextChipEl.classList.add('sk-player-preview');
        nextChipEl.innerHTML = playerBallPreviewEl().innerHTML;
        updatePlayerPreviews();
      }
    } else {
      nextChipEl.classList.remove('sk-player-preview');
      nextChipEl.innerHTML = '';
      const colors = tierColors(tier);
      nextChipEl.style.backgroundImage = 'none';
      nextChipEl.style.backgroundColor = colors.bg;
      nextChipEl.style.borderColor = colors.edge;
    }
  }
  if (nextNameEl) nextNameEl.textContent = def.en;
  if (nextHintEl) {
    // 显示"下一档什么时候解锁"，不是当前分数（当前分只是已经越过的门槛）。
    const maxTier = game.maxSpawnTier;
    const gateIndex = SPAWN_GATE_SCORES.findIndex((score) => score > game.score);
    nextHintEl.textContent = gateIndex >= 0
      ? `当前最大可出 ${tierDef(maxTier).en} · ${SPAWN_GATE_SCORES[gateIndex]} 分后解锁更大档位`
      : `当前最大可出 ${tierDef(maxTier).en} · 已全部解锁`;
  }
}

/** 玩家档的 DOM 预览：一个小 `.skin-avatar`（与游戏同一套 CSS 类渲染）。
    合成路线/「下一枚」共用；皮肤加载完成后由 updatePlayerPreviews() 刷新。 */
function playerBallPreviewEl() {
  const span = document.createElement('span');
  span.className = 'sk-chain-ball sk-player-preview';
  span.innerHTML = '<div class="skin-avatar skin-eye-shape-oval">'
    + '<div class="skin-eye skin-eye-left"><span class="skin-pupil"></span></div>'
    + '<div class="skin-eye skin-eye-right"><span class="skin-pupil"></span></div>'
    + '<svg class="skin-mouth" viewBox="0 0 100 56" aria-hidden="true" focusable="false">'
    + '<path class="skin-mouth-line" d="M 20 18 C 36 32 64 32 80 18"></path>'
    + '</svg></div>';
  return span;
}

/** 把页面上的玩家档预览（合成路线 + 下一枚）同步成当前皮肤。 */
function updatePlayerPreviews() {
  const color = playerSkin.primary || DEFAULT_SKIN.primary;
  const shape = ['oval', 'rectangle', 'diamond', 'hexagon'].includes(String(playerSkin.shape || '')) ? playerSkin.shape : 'oval';
  const border = skinBorder(color);
  document.querySelectorAll('.sk-player-preview .skin-avatar').forEach((avatar) => {
    avatar.className = `skin-avatar skin-eye-shape-${shape}`;
    avatar.style.setProperty('--skin-main', color);
    avatar.style.setProperty('--skin-border', border);
    avatar.style.setProperty('--skin-feature', skinLuminance(color) < 0.22 ? '#ffffff' : '#111111');
    avatar.style.setProperty('--skin-pupil', skinLuminance(color) < 0.22 ? '#111111' : '#ffffff');
  });
}

function buildLegend() {
  if (!legendEl) return;
  legendEl.textContent = '';
  TIERS.forEach((def, index) => {
    const item = document.createElement('div');
    item.className = 'sk-chain-item';
    item.dataset.tier = String(index);
    let ball;
    if (def.art) {
      ball = document.createElement('span');
      ball.className = 'sk-chain-ball';
      ball.style.backgroundColor = 'transparent';
      ball.style.borderColor = 'transparent';
      ball.style.backgroundImage = `url("${def.art}")`;
    } else if (index === MAX_TIER) {
      ball = playerBallPreviewEl();   // 玩家档：带脸预览，不再是一个裸底色圆
    } else {
      ball = document.createElement('span');
      ball.className = 'sk-chain-ball';
      ball.style.backgroundColor = tierColors(index).bg;
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
  updatePlayerPreviews();
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
    gameUid: syncState.gameUid,
    acked: syncState.acked,
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
  lastAimRenderX = null;
  markRenderDirty();
  hideOverlay();
  updateScore();
  updateNextChip();
  if (restored) {
    setStatus(`已恢复上一局（${drops.length} 次投放）`);
  } else {
    setStatus('新的一局，已保存到本机');
    saveLocal();
    // 云端也跟着开新局（页面里的「新游戏 / 再来一局」都走这里）：否则新局的同步
    // 会拿 0 分去对老局的云端分数，被判「分数回退」，这一局直到刷新页面都进不了榜。
    void restartCloudGame().then(() => { scheduleSync(400); });
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
  scheduleSync();
}

/* ---------------- 云同步 + 榜单 ---------------- */

function setVerifiedText() {
  if (!verifiedEl) return;
  verifiedEl.textContent = `上榜最佳 ${syncState.verified}`;
}

function scheduleSync(delay = 1200) {
  if (syncState.timer) window.clearTimeout(syncState.timer);
  syncState.timer = window.setTimeout(() => { void syncNow(); }, delay);
}

/** 本地是全新一局（没有本地存档）时，云端也开一局新的：否则会和上一局的云端存档对不上，
   服务端会把上报判成"分数回退"，表现就是"未通过验证"。 */
async function restartCloudGame() {
  if (!game) return;
  const run = (async () => {
    try {
      const response = await fetch('/api/minigame/suika/restart', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ seed: game.seed }),
      });
      if (!response.ok) return;
      const data = await response.json();
      const remote = data && data.game;
      if (remote && remote.game_uid) {
        syncState.gameUid = String(remote.game_uid);
        syncState.acked = 0;
      }
    } catch (_) { /* 离线：下次同步时会走 state 分支 */ }
  })();
  cloudRestartPromise = run;
  try {
    await run;
  } finally {
    if (cloudRestartPromise === run) cloudRestartPromise = null;
  }
}

/** 把"新增投放 + 新总分"立刻上传；服务端落库后再启发式校验能否入榜。 */
async function syncNow() {
  if (syncState.timer) { window.clearTimeout(syncState.timer); syncState.timer = null; }
  if (!game || syncState.inflight) return;
  if (cloudRestartPromise) {
    try { await cloudRestartPromise; } catch (_) { /* 上面已兜住 */ }
  }
  if (!syncState.gameUid) {
    // 还没拿到云端局 ID：先开一局（服务端会返回 seed，与本地一致时才接管）
    try {
      const response = await fetch('/api/minigame/suika/state', { credentials: 'same-origin' });
      if (!response.ok) { syncState.lastError = 'state'; return; }
      const data = await response.json();
      const remote = data && data.game;
      if (remote && remote.game_uid) {
        syncState.gameUid = String(remote.game_uid);
        if (Number(remote.score) > syncState.verified) syncState.verified = Number(remote.score);
        setVerifiedText();
      }
    } catch (_) { syncState.lastError = 'offline'; return; }
  }
  const drops = game.dropLog.slice(syncState.acked).map((entry) => ({ t: entry.t, x: entry.x }));
  if (!drops.length && game.score === syncState.verified) return;
  syncState.inflight = true;
  try {
    const response = await fetch('/api/minigame/suika/sync', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        game_uid: syncState.gameUid,
        from_index: syncState.acked,
        drops,
        claimed_score: game.score,
        claimed_max_tier: Math.max(0, Math.min(MAX_TIER, Number(game.maxTierSeen) || 0)),
        source: navigator.onLine === false ? 'offline' : 'online',
      }),
    });
    if (!response.ok) throw new Error(`http ${response.status}`);
    const data = await response.json();
    const remote = data && data.game;
    if (remote) {
      // 服务端永远是权威：stale_game / gap 时采纳它返回的当前局与下标，
      // 否则本地会拿着旧局标识无限同步失败（在别处重开/多设备时会出现）。
      if (remote.game_uid) syncState.gameUid = String(remote.game_uid);
      syncState.acked = Math.max(0, Number(remote.drop_index) || 0);
      if (Number(remote.score) > syncState.verified) syncState.verified = Number(remote.score);
      setVerifiedText();
      saveLocal();
    }
    if (data && data.verified === false) {
      setStatus('本批成绩未通过校验，未计入排行榜（进度已保留）', { offline: true });
    } else if (data && data.verified) {
      setStatus('成绩已上榜');
      scheduleLeaderboardRefresh();
    }
  } catch (_) {
    syncState.lastError = 'sync';
    setStatus('网络不可用：进度已存在本机，稍后自动重试', { offline: true });
    scheduleSync(8000);
  } finally {
    syncState.inflight = false;
  }
}

let rankWindowMode = '14d';

/* 榜单刷新节流：有新成绩时最多 15 秒刷一次，避免连续合成时每次加分都打一发
   /leaderboard。切窗口/进页面/切页签仍然立即刷新（与 2048 页同一套）。 */
let leaderboardRefreshTimer = null;

function scheduleLeaderboardRefresh(delay = 15000) {
  if (leaderboardRefreshTimer) return;
  leaderboardRefreshTimer = window.setTimeout(() => {
    leaderboardRefreshTimer = null;
    void refreshLeaderboard();
  }, delay);
}

async function refreshLeaderboard() {
  if (!rankBodyEl) return;
  try {
    const response = await fetch(`/api/minigame/suika/leaderboard?window=${encodeURIComponent(rankWindowMode)}&limit=50`,
      { credentials: 'same-origin' });
    if (!response.ok) throw new Error(`http ${response.status}`);
    const data = await response.json();
    const rows = (data && data.table && data.table.entries) || [];
    const me = data && data.me;
    if (!rows.length) {
      rankBodyEl.textContent = '还没有已验证的成绩。';
    } else {
      rankBodyEl.textContent = '';
      const meId = me ? String(me.user_id) : '';
      rows.forEach((row) => {
        const item = document.createElement('div');
        item.className = 'sk-rank-row' + (meId && String(row.user_id) === meId ? ' is-me' : '');
        const no = document.createElement('span');
        no.className = 'sk-rank-no';
        no.textContent = `${row.rank}.`;
        const name = document.createElement('span');
        name.className = 'sk-rank-name';
        name.textContent = String(row.username || '?');
        const sub = document.createElement('span');
        sub.className = 'sk-rank-sub';
        sub.textContent = tierDef(Math.max(0, Math.min(MAX_TIER, Number(row.max_tile) || 0))).en;
        const score = document.createElement('span');
        score.className = 'sk-rank-score';
        score.textContent = String(row.score);
        item.append(no, name, sub, score);
        // 离线申报的成绩照常上榜（物理游戏没法逐位重放），但给个标记让来源可见
        if (String(row.source || '') === 'offline') {
          const tag = document.createElement('span');
          tag.className = 'sk-rank-offline';
          tag.textContent = '离线';
          tag.title = '这条成绩是断网时打的，恢复网络后补报';
          item.append(tag);
        }
        rankBodyEl.append(item);
      });
      if (me && !rows.some((row) => String(row.user_id) === meId)) {
        const item = document.createElement('div');
        item.className = 'sk-rank-row is-me';
        item.textContent = `我的名次 ${me.rank} · ${me.score} 分`;
        rankBodyEl.append(item);
      }
    }
    if (rankNoteEl) {
      const pool = Number(data && data.champion_pool) || 300;
      const need = Number(data && data.champion_min_accounts) || 3;
      rankNoteEl.textContent = `每周一按最近 14 天成绩发一次冠军奖，奖池 ${pool} 荆露。`;
      rankNoteEl.title = `每周一 00:00（UTC+8）结算；至少 ${need} 个有效账号才发放。`;
    }
  } catch (_) {
    rankBodyEl.textContent = '读取榜单失败（可能是离线）。';
  }
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
    // BUTTON 也要排除：点过「新游戏」后焦点留在按钮上，空格会同时投放 + 再点一次按钮
    if (target instanceof HTMLElement
        && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(target.tagName))) return;
    if (overlayMode) return;   // 「重新开始？」等弹窗开着时不接受棋盘键盘
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

/* ---------- 脏标记渲染：静止时整帧跳过重画（低端设备的占用大头） ----------
   需要重画：有球在动 / 合成波纹未完 / 投放后引导线淡入窗口 / 瞄准位置变了 /
   外部要求（resize、主题、字体加载完成）。canvas 不重画就保留上一帧。
   探针可读 window.__skRenderStats 观察绘制/跳过比例。 */
let renderDirty = true;
let lastAimRenderX = null;
const renderStats = { frames: 0, draws: 0 };

function markRenderDirty() {
  renderDirty = true;
}

function sceneNeedsRedraw(now) {
  if (renderDirty) return true;
  if (pops.length) return true;
  if (game && game.gameOver) return false;   // 终局棋盘静止（结算弹窗是 DOM）
  if (lastDropAt && now - lastDropAt < 700) return true;   // 引导线淡入/落定窗口
  const aimXNow = currentAimX();
  if (lastAimRenderX === null || Math.abs(aimXNow - lastAimRenderX) > 0.5) {
    lastAimRenderX = aimXNow;
    return true;
  }
  if (game) {
    for (const record of game.balls) {
      const v = record.body.velocity;
      if (Math.abs(v.x) + Math.abs(v.y) > 0.08) return true;
    }
  }
  return false;
}

function frame(now) {
  if (!lastFrameAt) lastFrameAt = now;
  const dt = Math.min(120, Math.max(0, now - lastFrameAt));
  lastFrameAt = now;
  if (game && !document.hidden) {
    handleEvents(game.advance(dt));
    updateScore();
  }
  renderStats.frames += 1;
  if (sceneNeedsRedraw(now)) {
    renderDirty = false;
    renderStats.draws += 1;
    render(now);
  }
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
  updatePlayerPreviews();
  markRenderDirty();   // 皮肤就绪后棋盘上的玩家球（若在场）要换新顔
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
      markRenderDirty();
    });
  }
  if (aimToggle) {
    aimToggle.addEventListener('change', () => {
      aimGuideEnabled = aimToggle.checked;
      savePrefs();
      markRenderDirty();   // 静止时辅助线的出现/消失也要立即重画
    });
  }
  if (canvas) {
    canvas.addEventListener('pointermove', (event) => {
      if (event.pointerType === 'mouse' && !dragging) updateAim(canvasXFromEvent(event));
    });
  }
  window.addEventListener('beforeunload', () => saveLocal());
  window.addEventListener('online', () => { setStatus('网络已恢复'); scheduleSync(300); });
  window.addEventListener('offline', () => setStatus('离线：本机已保存', { offline: true }));
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) return;
    void syncNow();
    void refreshLeaderboard();
  });
  document.querySelectorAll('[data-sk-window]').forEach((button) => {
    button.addEventListener('click', () => {
      rankWindowMode = button.dataset.skWindow === 'all' ? 'all' : '14d';
      document.querySelectorAll('[data-sk-window]').forEach((other) => {
        const active = other === button;
        other.setAttribute('aria-pressed', active ? 'true' : 'false');
        other.classList.toggle('secondary', !active);
      });
      void refreshLeaderboard();
    });
  });
  window.addEventListener('resize', () => { resizeCanvas(); markRenderDirty(); });
  try {
    new MutationObserver(() => { refreshThemeColors(); markRenderDirty(); })
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
    syncState.gameUid = String(saved.gameUid || '');
    syncState.acked = Math.max(0, Number(saved.acked) || 0);
    startGame({ seed: saved.seed, drops: saved.drops, uptoMs: saved.timeMs, restored: true });
  } else {
    startGame();
  }
  updateNextChip();
  setVerifiedText();
  void refreshLeaderboard();
  scheduleSync(400);
  bindInput();
  bindUi();
  loadPlayerSkin();
  attachPresence();
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/minigame/suika/sw.js', { scope: '/minigame/suika' })
      .catch(() => { /* 缓存不可用不影响游玩 */ });
  }
  // Kreadon 是 font-display:swap：加载完成后画布文字（分数水印/失败线）要重画一次
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => { markRenderDirty(); }).catch(() => {});
  }
  // 浏览器探针用的只读钩子（不参与玩法）
  window.__skSnapshot = () => (game ? game.snapshot() : null);
  window.__skArt = () => art.map((item) => (item ? { avg: item.avg, w: item.box.w, h: item.box.h } : null));
  window.__skRenderStats = renderStats;
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
    // 大厅聊天：和多人游戏 / 2048 是同一条，用共用渲染模块
    onSocket: (socket) => { attachChat(socket); },
  });
}

/** 大厅聊天（共用 minigame-chat.js；渲染规则与多人游戏大厅一致）。 */
function attachChat(socket) {
  const factory = window.GtnMinigameChat;
  if (!factory || !socket) return;
  const chat = factory.attach({
    socket,
    gameKey: CONFIG.gameKey || 'suika',
    userId: CONFIG.userId,
    username: CONFIG.username,
    chatRole: CONFIG.chatRole || 'player',
    toggleId: 'sk-chat-toggle',
    panelId: 'sk-chat',
    closeId: 'sk-chat-close',
    logId: 'sk-chat-log',
    formId: 'sk-chat-form',
    inputId: 'sk-chat-input',
    unreadId: 'sk-chat-unread',
    emptyHtml: '<p class="sk-hint">还没有人说话。</p>',
  });
  window.__skChat = chat;   // 浏览器探针用
  socket.on('lobby_chat_history', (payload) => {
    try {
      chat.render(payload && payload.items);
    } catch (error) {
      window.__skChatError = String((error && error.stack) || error);
    }
  });
  socket.on('chat', (payload) => {
    try {
      chat.append(payload);
    } catch (error) {
      window.__skChatError = String((error && error.stack) || error);
    }
    const panel = document.getElementById('sk-chat');
    if (panel && panel.hidden) chat.markUnread(payload);
  });
  socket.on('chat_recall', (payload) => {
    const ids = ((payload || {}).message_ids || []).map((value) => Number(value) || 0).filter(Boolean);
    const log = document.getElementById('sk-chat-log');
    if (!log) return;
    ids.forEach((id) => {
      const row = log.querySelector(`.chat-msg[data-chat-message-id="${id}"]`);
      if (row) row.remove();
    });
    const actor = escapeHtml(String((payload || {}).actor_name || '管理员'));
    const target = escapeHtml(String((payload || {}).target_name || ''));
    const text = (payload || {}).self_recall
      ? `${actor} 撤回了一条消息`
      : `${actor} 撤回了 ${target || '某个玩家'} 的一条消息`;
    log.insertAdjacentHTML('beforeend', `<div class="chat-msg chat-recall-entry">${text}</div>`);
    log.scrollTop = log.scrollHeight;
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => { boot(); });
} else {
  boot();
}
