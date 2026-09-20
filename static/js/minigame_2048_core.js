/* 休闲花园 · 2048 的**纯规则核心**（浏览器与 Node 都能跑）。

   必须与 Python 侧 `minigame_2048.py` 逐位一致：32 位 xorshift、90% 出 2、
   空格等概率、同一次操作里新合成的方块不再合并、只有棋盘变化才生成新块。
   对拍脚本见 `.codex-tmp/round110/parity_check.mjs`（Node ↔ Python）。 */

export const DIRECTION_CHARS = 'lrud';
export const DIRECTIONS = { left: 0, right: 1, up: 2, down: 3 };
export const ETERNAL_VALUE = 2048;

export function rngNext(value) {
  let x = value >>> 0;
  if (x === 0) x = 0x9E3779B9;
  x ^= (x << 13) >>> 0; x >>>= 0;
  x ^= x >>> 17; x >>>= 0;
  x ^= (x << 5) >>> 0; x >>>= 0;
  return x >>> 0;
}

export function seedFromText(text) {
  let value = 0x811C9DC5;
  for (const char of String(text || '')) {
    value ^= char.codePointAt(0) & 0xFF;
    value = Math.imul(value, 0x01000193) >>> 0;
  }
  return value || 0x9E3779B9;
}

export function emptyCells(cells) {
  const out = [];
  cells.forEach((value, index) => { if (!value) out.push(index); });
  return out;
}

export function spawnTile(cells, rngState) {
  const empties = emptyCells(cells);
  if (!empties.length) return { cells, rngState, info: null };
  const roll = rngNext(rngState);
  const value = (roll % 100) < 90 ? 2 : 4;
  const pick = rngNext(roll);
  const index = empties[pick % empties.length];
  const next = cells.slice();
  next[index] = value;
  return { cells: next, rngState: pick, info: { index, value } };
}

export function mergeLine(line) {
  const packed = line.filter(Boolean);
  const out = [];
  let gained = 0;
  for (let index = 0; index < packed.length; index += 1) {
    if (index + 1 < packed.length && packed[index] === packed[index + 1]) {
      const merged = packed[index] * 2;
      gained += merged;
      out.push(merged);
      index += 1;
    } else {
      out.push(packed[index]);
    }
  }
  while (out.length < 4) out.push(0);
  return { line: out, gained };
}

export function lineIndices(direction) {
  const lines = [];
  if (direction === DIRECTIONS.up || direction === DIRECTIONS.down) {
    for (let col = 0; col < 4; col += 1) {
      const indexes = [0, 1, 2, 3].map((row) => row * 4 + col);
      if (direction === DIRECTIONS.down) indexes.reverse();
      lines.push(indexes);
    }
    return lines;
  }
  for (let row = 0; row < 4; row += 1) {
    const indexes = [0, 1, 2, 3].map((col) => row * 4 + col);
    if (direction === DIRECTIONS.right) indexes.reverse();
    lines.push(indexes);
  }
  return lines;
}

export function applyMove(cells, direction) {
  const out = new Array(16).fill(0);
  let gained = 0;
  for (const indexes of lineIndices(direction)) {
    const merged = mergeLine(indexes.map((index) => cells[index]));
    gained += merged.gained;
    indexes.forEach((index, offset) => { out[index] = merged.line[offset]; });
  }
  return { cells: out, gained, changed: out.some((value, index) => value !== cells[index]) };
}

export function stepMove(cells, rngState, score, direction) {
  const move = applyMove(cells, direction);
  if (!move.changed) {
    return { cells, rngState, score, gained: 0, changed: false, spawn: null };
  }
  const spawned = spawnTile(move.cells, rngState);
  return {
    cells: spawned.cells,
    rngState: spawned.rngState,
    score: score + move.gained,
    gained: move.gained,
    changed: true,
    spawn: spawned.info,
  };
}

export function isGameOver(cells) {
  if (cells.some((value) => !value)) return false;
  for (let index = 0; index < 16; index += 1) {
    const value = cells[index];
    const col = index % 4;
    const row = Math.floor(index / 4);
    if (col < 3 && cells[index + 1] === value) return false;
    if (row < 3 && cells[index + 4] === value) return false;
  }
  return true;
}

export function maxTile(cells) {
  return cells.reduce((max, value) => Math.max(max, value || 0), 0);
}

export function initialCells(seed) {
  let rngState = seed >>> 0;
  let cells = new Array(16).fill(0);
  for (let i = 0; i < 2; i += 1) {
    const spawned = spawnTile(cells, rngState);
    cells = spawned.cells;
    rngState = spawned.rngState;
  }
  return { cells, rngState };
}

/** 用操作串重放一局（与 Python 的 replay 同口径）。 */
export function replay(seed, ops) {
  let { cells, rngState } = initialCells(seed >>> 0);
  let score = 0;
  let index = 0;
  for (const char of String(ops || '')) {
    const direction = DIRECTION_CHARS.indexOf(char);
    if (direction < 0) throw new Error(`未知方向字符：${char}`);
    const result = stepMove(cells, rngState, score, direction);
    cells = result.cells;
    rngState = result.rngState;
    score = result.score;
    index += 1;
  }
  return { seed: seed >>> 0, cells, rngState, score, index, maxTile: maxTile(cells), gameOver: isGameOver(cells) };
}
