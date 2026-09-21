/* 休闲花园 · 2048 的**纯规则核心**（浏览器与 Node 都能跑）。

   必须与 Python 侧 `minigame_2048.py` 逐位一致：32 位 xorshift、90% 出 2、
   空格等概率、同一次操作里新合成的方块不再合并、只有棋盘变化才生成新块。
   规则 v2：棋盘 5×5；每次"本应合并"消耗一个随机数，<20 判**合并失败**——
   只留下一个原值方块（不翻倍），位置就是合并结果本该出现的那一格。
   对拍脚本见 `tests/test_minigame_2048_parity.py`（Node ↔ Python）。 */

export const DIRECTION_CHARS = 'lrud';
export const DIRECTIONS = { left: 0, right: 1, up: 2, down: 3 };
export const ETERNAL_VALUE = 2048;
export const BOARD_SIZE = 5;
export const CELL_COUNT = BOARD_SIZE * BOARD_SIZE;
export const RULES_VERSION = 2;
export const MERGE_FAIL_PERCENT = 20;

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

export function mergeLine(line, rngState) {
  const packed = line.filter(Boolean);
  const out = [];
  let gained = 0;
  const merges = [];
  let state = rngState >>> 0;
  for (let index = 0; index < packed.length; index += 1) {
    if (index + 1 < packed.length && packed[index] === packed[index + 1]) {
      state = rngNext(state);
      const failed = (state % 100) < MERGE_FAIL_PERCENT;
      const value = failed ? packed[index] : packed[index] * 2;
      gained += value;
      merges.push({ value, from: packed[index], failed });
      out.push(value);
      index += 1;
    } else {
      out.push(packed[index]);
    }
  }
  while (out.length < BOARD_SIZE) out.push(0);
  return { line: out, gained, merges, rngState: state >>> 0 };
}

export function lineIndices(direction) {
  const lines = [];
  if (direction === DIRECTIONS.up || direction === DIRECTIONS.down) {
    for (let col = 0; col < BOARD_SIZE; col += 1) {
      const indexes = Array.from({ length: BOARD_SIZE }, (_unused, row) => row * BOARD_SIZE + col);
      if (direction === DIRECTIONS.down) indexes.reverse();
      lines.push(indexes);
    }
    return lines;
  }
  for (let row = 0; row < BOARD_SIZE; row += 1) {
    const indexes = Array.from({ length: BOARD_SIZE }, (_unused, col) => row * BOARD_SIZE + col);
    if (direction === DIRECTIONS.right) indexes.reverse();
    lines.push(indexes);
  }
  return lines;
}

export function applyMove(cells, direction, rngState = 0) {
  const out = new Array(CELL_COUNT).fill(0);
  let gained = 0;
  let state = rngState >>> 0;
  const moves = [];   // [{from, to, merged, failed}]：给界面做"滑过去/碎裂"动画用（与棋盘结果同源）
  for (const indexes of lineIndices(direction)) {
    const packed = [];
    indexes.forEach((index, offset) => {
      const value = cells[index];
      if (value) packed.push({ value, from: index, order: offset });
    });
    let cursor = 0;
    for (let i = 0; i < packed.length; i += 1) {
      const to = indexes[cursor];
      if (i + 1 < packed.length && packed[i].value === packed[i + 1].value) {
        state = rngNext(state);
        const failed = (state % 100) < MERGE_FAIL_PERCENT;
        const value = failed ? packed[i].value : packed[i].value * 2;
        gained += value;
        out[to] = value;
        moves.push({ from: packed[i].from, to, merged: true, failed });
        moves.push({ from: packed[i + 1].from, to, merged: true, failed });
        i += 1;
      } else {
        out[to] = packed[i].value;
        moves.push({ from: packed[i].from, to, merged: false });
      }
      cursor += 1;
    }
  }
  return {
    cells: out,
    gained,
    moves,
    rngState: state >>> 0,
    changed: out.some((value, index) => value !== cells[index]),
  };
}

export function stepMove(cells, rngState, score, direction) {
  const move = applyMove(cells, direction, rngState);
  if (!move.changed) {
    return { cells, rngState, score, gained: 0, changed: false, spawn: null, moves: [] };
  }
  const spawned = spawnTile(move.cells, move.rngState);
  return {
    cells: spawned.cells,
    rngState: spawned.rngState,
    score: score + move.gained,
    gained: move.gained,
    changed: true,
    spawn: spawned.info,
    moves: move.moves,
  };
}

export function isGameOver(cells) {
  if (cells.some((value) => !value)) return false;
  for (let index = 0; index < CELL_COUNT; index += 1) {
    const value = cells[index];
    const col = index % BOARD_SIZE;
    const row = Math.floor(index / BOARD_SIZE);
    if (col < BOARD_SIZE - 1 && cells[index + 1] === value) return false;
    if (row < BOARD_SIZE - 1 && cells[index + BOARD_SIZE] === value) return false;
  }
  return true;
}

export function maxTile(cells) {
  return cells.reduce((max, value) => Math.max(max, value || 0), 0);
}

export function initialCells(seed) {
  let rngState = seed >>> 0;
  let cells = new Array(CELL_COUNT).fill(0);
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
