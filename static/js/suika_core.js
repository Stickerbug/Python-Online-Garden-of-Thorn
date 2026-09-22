/* 休闲花园 ·「合成大花花」（Suika 类）的**纯规则核心**：只依赖传入的 matter.js，
   不碰 DOM，浏览器与 Node 跑同一份代码。

   规则（用户 2026-09-22 拍板，见 docs/合成大花花-移植方案.md 第五节）：
   - 11 档链条 Bubble → Ant Egg → Ladybug → Ant Hole → Dark Ladybug → Cactus →
     Uranium Barrel → Gambler → Shiny Ladybug → Mecha Flower → Player，半径/分值照经典 Suika；
   - 同档两球相撞即合成下一档，**按合成出的新档位给分**；最高档（Player）相撞两颗直接消失，
     也按 Player 的分值给分；
   - 判负：有球停在判负线上方**满 1 秒**才结束；**刚投放的那颗不算**（下次投放后才纳入判定）；
   - 随机只从最小的 5 档等概率取，用 32 位 xorshift（与 2048 同一套写法），
     于是「种子 + 投放序列」可以完全重放——服务端以后可以拿它复核分数。

   物理照搬 moonfloof/suika-game（公有领域）的手感参数：
   friction 0.006 / frictionStatic 0.006 / frictionAir 0 / restitution 0.1，
   固定步长 1000/60ms 推进，保证同样输入得到同样结果。 */

export const RULES_VERSION = 2;
export const FIXED_STEP_MS = 1000 / 60;

/** 场地：640×960 逻辑分辨率；左右墙与地板各占 64，底部再留 48 给状态栏（页面上画在画布外）。 */
export const ARENA = Object.freeze({
  width: 640,
  height: 960,
  wall: 64,
  loseLineY: 84,
  dropLineY: 32,
  bottomBar: 48,
});

export const PHYSICS = Object.freeze({
  friction: 0.006,
  frictionStatic: 0.006,
  frictionAir: 0,
  restitution: 0.1,
  density: 0.001,
});

export const DROP_COOLDOWN_MS = 500;
export const LOSE_HOLD_MS = 1000;
export const RANDOM_TIER_POOL = 5;

/* 规则 v2（对着 47.99.48.177 那套调过手感）：
   - 判负要求"真的停住"：竖直速度低于 LOSE_MAX_SPEED 才计入线上停留时间；
   - 生成档位随分数开放：低分只出最小几档，越到后面越容易见到大档；
   - 按"最大可生成档位的分值"加权（最小的球权重最大），并禁止连着出同一档、
     禁止最近 SPAWN_HISTORY 颗里同一档出现太多次。 */
export const LOSE_MAX_SPEED = 0.5;
export const SPAWN_HISTORY = 10;
export const SPAWN_MAX_SAME_RUN = 2;     // 连续 2 次相同就不再出这一档
export const SPAWN_MAX_SAME_TOTAL = 3;   // 最近 10 颗里出现 3 次就不再出
export const SPAWN_RARE_WINDOW = 8;      // 当前最高档在最近 8 颗里出现过就不再出
export const SPAWN_GATE_SCORES = Object.freeze([300, 1800]);
export const SPAWN_GATE_TIERS = Object.freeze([3, 4, 5]);

/** 11 档：半径/分值是经典 Suika 曲线；贴图见 docs/合成大花花-美术清单.md。 */
export const TIERS = Object.freeze([
  { id: 'bubble', zh: '泡泡', en: 'Bubble', radius: 24, score: 1, art: '/static/assets/story-enemies/bubble.svg' },
  { id: 'ant_egg', zh: '蚂蚁卵', en: 'Ant Egg', radius: 32, score: 3, art: '/static/assets/story-enemies/ant-egg.svg' },
  { id: 'ladybug', zh: '瓢虫', en: 'Ladybug', radius: 40, score: 6, art: '/static/assets/story-enemies/ladybug.svg' },
  { id: 'ant_hole', zh: '蚁穴', en: 'Ant Hole', radius: 56, score: 10, art: '/static/assets/story-enemies/ant-hole.svg' },
  { id: 'dark_ladybug', zh: '深色瓢虫', en: 'Dark Ladybug', radius: 64, score: 15, art: '/static/assets/story-enemies/dark-ladybug.svg' },
  { id: 'cactus', zh: '仙人掌', en: 'Cactus', radius: 72, score: 21, art: '/static/assets/story-enemies/cactus.svg' },
  { id: 'uranium_barrel', zh: '铀桶', en: 'Uranium Barrel', radius: 84, score: 28, art: '/static/assets/story-enemies/uranium-barrel.svg' },
  { id: 'gambler', zh: '赌徒', en: 'Gambler', radius: 96, score: 36, art: '/static/assets/story-enemies/gambler.svg' },
  { id: 'shiny_ladybug', zh: '闪亮瓢虫', en: 'Shiny Ladybug', radius: 128, score: 45, art: '/static/assets/story-enemies/shiny-ladybug.svg' },
  { id: 'mecha_flower', zh: '机械花', en: 'Mecha Flower', radius: 160, score: 55, art: '/static/assets/story-enemies/mechanical-flower.svg' },
  // 第 10 档不给贴图：运行时用当前玩家的皮肤画（游客＝初始皮肤）。
  { id: 'player', zh: '玩家', en: 'Player', radius: 192, score: 66, art: null },
]);

export const MAX_TIER = TIERS.length - 1;

export function tierDef(tier) {
  const index = Math.max(0, Math.min(MAX_TIER, Number(tier) | 0));
  return TIERS[index];
}

/** 与 2048 同一套 32 位 xorshift，方便两端对拍。 */
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

/** 当前分数下最高能生成到第几档（低分只出小球，后面才可能出现大档）。 */
export function maxSpawnTierFor(score) {
  const value = Number(score) || 0;
  if (value > SPAWN_GATE_SCORES[1]) return SPAWN_GATE_TIERS[2];
  if (value > SPAWN_GATE_SCORES[0]) return SPAWN_GATE_TIERS[1];
  return SPAWN_GATE_TIERS[0];
}

function clamp(value, min, max) {
  if (!Number.isFinite(value)) return (min + max) / 2;
  return Math.max(min, Math.min(max, value));
}

function ballOptions(Matter, tier) {
  const def = tierDef(tier);
  return {
    friction: PHYSICS.friction,
    frictionStatic: PHYSICS.frictionStatic,
    frictionAir: PHYSICS.frictionAir,
    restitution: PHYSICS.restitution,
    density: PHYSICS.density,
    label: `suika:tier${def.radius}`,
  };
}

export class SuikaGame {
  constructor(Matter, options = {}) {
    if (!Matter || !Matter.Engine || !Matter.Bodies) throw new Error('suika_core: 需要 matter.js');
    this.Matter = Matter;
    this.seed = (Number(options.seed) >>> 0) || 1;
    this.rngState = this.seed >>> 0;
    this.score = 0;
    this.timeMs = 0;
    this.pendingMs = 0;
    this.dropCooldownMs = 0;
    this.totalDrops = 0;
    this.maxTierSeen = 0;   // 本局合成出现过的最高档（投放的球不算，合成出来的才算）
    this.nextBallId = 1;
    this.gameOver = false;
    this.balls = [];
    this.dropLog = [];
    this.spawnHistory = [];
    this.events = [];
    this.mergeQueue = [];

    this.engine = Matter.Engine.create({ enableSleeping: false });
    this.engine.gravity.x = 0;
    this.engine.gravity.y = 1;
    this.world = this.engine.world;
    this.buildArena();

    this.queue = [];
    this.queue.push(this.rollTier());
    this.queue.push(this.rollTier());

    this.onCollisionStart = (event) => {
      for (const pair of event.pairs) {
        const dataA = pair.bodyA && pair.bodyA.suika;
        const dataB = pair.bodyB && pair.bodyB.suika;
        if (!dataA || !dataB) continue;
        if (dataA.removed || dataB.removed) continue;
        if (dataA.tier !== dataB.tier) continue;
        dataA.removed = true;
        dataB.removed = true;
        this.mergeQueue.push([pair.bodyA, pair.bodyB]);
      }
    };
    Matter.Events.on(this.engine, 'collisionStart', this.onCollisionStart);
  }

  buildArena() {
    const { Matter } = this;
    const { width, height, wall } = ARENA;
    const options = {
      isStatic: true,
      friction: PHYSICS.friction,
      frictionStatic: PHYSICS.frictionStatic,
      restitution: PHYSICS.restitution,
      label: 'suika:wall',
    };
    const bodies = [
      Matter.Bodies.rectangle(wall / 2, height / 2, wall, height * 2, options),
      Matter.Bodies.rectangle(width - wall / 2, height / 2, wall, height * 2, options),
      Matter.Bodies.rectangle(width / 2, height - wall / 2, width * 2, wall, options),
    ];
    this.walls = bodies;
    Matter.Composite.add(this.world, bodies);
  }

  /** 均匀取 [0,1) 的随机数（推进种子状态）。 */
  roll01() {
    this.rngState = rngNext(this.rngState);
    return (this.rngState >>> 8) / 0x1000000;
  }

  get maxSpawnTier() {
    return Math.min(MAX_TIER, maxSpawnTierFor(this.score));
  }

  /** 某个档位最近连着出了几次。 */
  runLength(tier) {
    let run = 0;
    for (let i = this.spawnHistory.length - 1; i >= 0; i -= 1) {
      if (this.spawnHistory[i] !== tier) break;
      run += 1;
    }
    return run;
  }

  /** 这一档现在能不能出（防连出 / 防短时间内重复 / 大档最近出现过）。 */
  canSpawn(tier, maxTier) {
    if (this.runLength(tier) >= SPAWN_MAX_SAME_RUN) return false;
    const total = this.spawnHistory.filter((value) => value === tier).length;
    if (total >= SPAWN_MAX_SAME_TOTAL) return false;
    if (tier === maxTier) {
      const recent = this.spawnHistory.slice(-SPAWN_RARE_WINDOW);
      if (recent.includes(tier)) return false;
    }
    return true;
  }

  /** 取下一颗要投放的档位：按分值加权（越小越常见），并过一遍防连出规则。 */
  rollTier() {
    const maxTier = this.maxSpawnTier;
    const candidates = [];
    for (let tier = 0; tier <= maxTier; tier += 1) {
      candidates.push({ tier, weight: tierDef(maxTier - tier).score });
    }
    const allowed = candidates.filter((entry) => this.canSpawn(entry.tier, maxTier));
    const pool = allowed.length
      ? allowed
      : candidates.slice().sort((a, b) => this.runLength(b.tier) - this.runLength(a.tier));
    const total = pool.reduce((sum, entry) => sum + entry.weight, 0);
    let roll = this.roll01() * total;
    let picked = pool[pool.length - 1].tier;
    for (const entry of pool) {
      roll -= entry.weight;
      if (roll <= 0) { picked = entry.tier; break; }
    }
    this.spawnHistory.push(picked);
    if (this.spawnHistory.length > SPAWN_HISTORY) this.spawnHistory.shift();
    return picked;
  }

  /** 落点预测：这颗球如果现在投放，会停在哪个圆心高度（只看第一个相交的圆，不考虑弹跳/滚动）。 */
  predictLanding(x, tier = this.nextTier) {
    const radius = tierDef(tier).radius;
    const floor = ARENA.height - ARENA.wall - radius;
    let best = floor;
    let found = false;
    for (const record of this.balls) {
      const otherRadius = tierDef(record.tier).radius;
      const dx = Math.abs(x - record.body.position.x);
      if (dx > radius + otherRadius) continue;
      const y = record.body.position.y - Math.sqrt((radius + otherRadius) ** 2 - dx * dx);
      if (!found || y < best) { best = y; found = true; }
    }
    if (found && best < radius) best = radius;
    return { x, y: best, landedOnBall: found };
  }

  get nextTier() {
    return this.queue.length ? this.queue[0] : 0;
  }

  /** 往世界里放一颗球（投放与合成都走这里）。
   *  ``isStatic`` 只给测试/调试用：让球悬在原地验证判负线规则。 */
  spawnBall(tier, x, y, options = {}) {
    const { Matter } = this;
    const def = tierDef(tier);
    const body = Matter.Bodies.circle(x, y, def.radius, {
      ...ballOptions(Matter, tier),
      isStatic: !!options.isStatic,
    });
    const ballId = this.nextBallId;
    this.nextBallId += 1;
    body.suika = { ballId, tier, overMs: 0, droppedAtMs: this.timeMs };
    if (options.velocity) Matter.Body.setVelocity(body, options.velocity);
    Matter.Composite.add(this.world, body);
    this.balls.push({ id: ballId, tier, body, overMs: 0, droppedAtMs: this.timeMs });
    return { ballId, body };
  }

  /** 投放一颗。x 会被夹进可投放范围；冷却中 / 已结束会拒绝。 */
  drop(x) {
    if (this.gameOver) return { ok: false, reason: 'game_over' };
    if (this.dropCooldownMs > 0) return { ok: false, reason: 'cooldown' };
    const tier = this.queue.shift();
    this.queue.push(this.rollTier());
    const def = tierDef(tier);
    const px = clamp(Number(x), ARENA.wall + def.radius, ARENA.width - ARENA.wall - def.radius);
    const { ballId } = this.spawnBall(tier, px, ARENA.dropLineY);
    this.dropCooldownMs = DROP_COOLDOWN_MS;
    this.totalDrops += 1;
    this.dropLog.push({ t: this.timeMs, x: Math.round(px * 1000) / 1000, tier });
    this.events.push({ type: 'drop', ballId, tier, x: px, y: ARENA.dropLineY });
    return { ok: true, ballId, tier, x: px };
  }

  /** 推进一个固定步长。 */
  step() {
    if (this.gameOver) return;
    const { Matter } = this;
    Matter.Engine.update(this.engine, FIXED_STEP_MS);
    this.timeMs += FIXED_STEP_MS;
    if (this.dropCooldownMs > 0) this.dropCooldownMs = Math.max(0, this.dropCooldownMs - FIXED_STEP_MS);
    this.resolveMerges();
    this.checkLoseLine();
  }

  /** 推进真实时间（毫秒），内部仍是固定步长。 */
  advance(ms) {
    const amount = Math.max(0, Number(ms) || 0);
    this.pendingMs += amount;
    while (this.pendingMs >= FIXED_STEP_MS && !this.gameOver) {
      this.pendingMs -= FIXED_STEP_MS;
      this.step();
    }
    return this.takeEvents();
  }

  /** 一直推进到 >= 目标时刻（重放投放序列用）。 */
  seekTo(targetMs) {
    const target = Math.max(0, Number(targetMs) || 0);
    while (!this.gameOver && this.timeMs + FIXED_STEP_MS <= target) this.step();
    return this.takeEvents();
  }

  takeEvents() {
    const out = this.events;
    this.events = [];
    return out;
  }

  resolveMerges() {
    const { Matter } = this;
    while (this.mergeQueue.length) {
      const [bodyA, bodyB] = this.mergeQueue.shift();
      const dataA = bodyA.suika;
      const dataB = bodyB.suika;
      if (!dataA || !dataB) continue;
      const tier = dataA.tier;
      const x = (bodyA.position.x + bodyB.position.x) / 2;
      const y = (bodyA.position.y + bodyB.position.y) / 2;
      const vx = (bodyA.velocity.x + bodyB.velocity.x) / 2;
      const vy = (bodyA.velocity.y + bodyB.velocity.y) / 2;
      this.removeBall(dataA.ballId);
      this.removeBall(dataB.ballId);
      const nextTier = Math.min(MAX_TIER, tier + 1);
      const gained = tierDef(nextTier).score;
      this.score += gained;
      if (nextTier > this.maxTierSeen) this.maxTierSeen = nextTier;
      if (tier < MAX_TIER) {
        const { ballId } = this.spawnBall(nextTier, x, y, { velocity: { x: vx, y: vy } });
        this.events.push({ type: 'merge', tier, nextTier, gained, x, y, ballId, spawned: true });
      } else {
        // 最高档相撞：两颗都消失，不生成新球，但照常按最高档给分。
        this.events.push({ type: 'merge', tier, nextTier: MAX_TIER, gained, x, y, spawned: false });
      }
    }
  }

  removeBall(ballId) {
    const { Matter } = this;
    const index = this.balls.findIndex((ball) => ball.id === ballId);
    if (index < 0) return;
    const [record] = this.balls.splice(index, 1);
    if (record.body) Matter.Composite.remove(this.world, record.body);
  }

  /** 判负线：除了刚投放的那颗，有球停在线上一整秒就结束。 */
  checkLoseLine() {
    if (!this.balls.length) return;
    const newestId = this.balls[this.balls.length - 1].id;
    let danger = false;
    for (const record of this.balls) {
      if (record.id === newestId) { record.overMs = 0; continue; }
      const def = tierDef(record.tier);
      const top = record.body.position.y - def.radius;
      // 规则 v2：要"真的停住"才算（竖直速度很小），避免球在线上弹一下就被判负
      const slow = Math.abs(record.body.velocity.y) < LOSE_MAX_SPEED;
      if (top < ARENA.loseLineY && slow) {
        record.overMs += FIXED_STEP_MS;
        danger = true;
        if (record.overMs >= LOSE_HOLD_MS) {
          this.gameOver = true;
          this.events.push({ type: 'game_over', ballId: record.id, tier: record.tier, overMs: record.overMs });
          return;
        }
      } else {
        record.overMs = 0;
      }
    }
    this.danger = danger;
  }

  /** 最高处那颗球（判负线参考）——给界面画警告线用。 */
  highestBall() {
    let best = null;
    for (const record of this.balls) {
      const def = tierDef(record.tier);
      const top = record.body.position.y - def.radius;
      if (!best || top < best.top) best = { top, tier: record.tier, id: record.id };
    }
    return best;
  }

  snapshot() {
    return {
      rulesVersion: RULES_VERSION,
      seed: this.seed,
      rngState: this.rngState,
      score: this.score,
      timeMs: Math.round(this.timeMs),
      gameOver: this.gameOver,
      danger: !!this.danger,
      maxSpawnTier: this.maxSpawnTier,
      maxTierSeen: this.maxTierSeen,
      queue: this.queue.slice(),
      totalDrops: this.totalDrops,
      dropLog: this.dropLog.map((entry) => ({ ...entry })),
      balls: this.balls.map((record) => ({
        id: record.id,
        tier: record.tier,
        radius: tierDef(record.tier).radius,
        x: Math.round(record.body.position.x * 1000) / 1000,
        y: Math.round(record.body.position.y * 1000) / 1000,
        angle: Math.round(record.body.angle * 10000) / 10000,
      })),
    };
  }

  /** 存档/同步用：只要种子 + 投放序列就能完整重放一局。 */
  serialize() {
    return {
      v: RULES_VERSION,
      seed: this.seed,
      score: this.score,
      gameOver: this.gameOver,
      drops: this.dropLog.map((entry) => ({ t: Math.round(entry.t * 1000) / 1000, x: entry.x })),
    };
  }
}

/** 用「种子 + 投放序列」重放一局，返回终局快照（前端/服务端同口径）。 */
export function replay(Matter, seed, drops) {
  const game = new SuikaGame(Matter, { seed });
  for (const entry of drops || []) {
    const t = Math.max(0, Number(entry && entry.t) || 0);
    game.seekTo(t);
    const result = game.drop(Number(entry && entry.x) || 0);
    if (!result.ok && result.reason === 'cooldown') {
      // 投放间隔不足 500ms 的记录是非法操作；重放时直接跳过，由服务端规则判定拒绝。
      game.dropLog.pop();
    }
  }
  return game;
}

/** 让球堆静下来（测试用）：返回是否已静止。 */
export function settle(Matter, game, maxMs = 8000, threshold = 0.12) {
  let elapsed = 0;
  while (elapsed < maxMs) {
    game.advance(FIXED_STEP_MS);
    elapsed += FIXED_STEP_MS;
    if (game.gameOver) return true;
    const moving = game.balls.some((record) => Math.hypot(record.body.velocity.x, record.body.velocity.y) > threshold);
    if (!moving && game.balls.length) return true;
  }
  return false;
}
