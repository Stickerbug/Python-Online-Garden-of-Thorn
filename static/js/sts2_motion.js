/*
 * sts2_motion.js — 杀戮尖塔2风格手牌动画引擎（独立模块，零依赖）
 *
 * 参数来自 STS2动画拆解.md（60fps 实测），2026-10-01 整体提速 2 倍（原值 ÷ 2）：
 *   抽牌飞行 175ms / 错峰 100ms（批量 30ms）；出牌飞行 200ms，本体缩到 35%；
 *   弃牌飞行 210ms / 错峰 60ms；洗牌单张 350ms / 错峰 15ms，多流并行；
 *   悬停 60ms；重排 90ms。
 *
 * 视觉原则（反“AI 粒子风”）：
 *   - 拖尾不是发光圆点，而是「卡牌剪影残影」：63:88 圆角矩形、细边框、
 *     无模糊无霓虹光晕，颜色直接取自游戏卡种框色（--card-frame-color），
 *     旋转跟随飞行方向，快速缩小淡出——像实体卡甩过留下的重影。
 *   - 幽灵牌背复用游戏自身的暗色牌背（#3d3d5c + 细边框），不发明新视觉。
 *
 * 设计约束：
 *   - 纯 rAF 驱动（对齐 equipment_motion.js），单帧推进上限防后台切回跳变；
 *   - 动画只新增一次性节点（ghost/残影），不侵入现有手牌 DOM 结构；
 *   - classic / story 两套 UI 共用：只要求调用方给出「起点 rect / 终点 rect / 卡牌元素」。
 */
(function exposeSts2Motion(root) {
    'use strict';

    const MAX_STEP_MS = 120; // 单帧推进上限：切后台回来不会瞬移

    // ---------- 缓动 ----------
    const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
    const easeInCubic = (t) => t * t * t;
    const easeInOutQuad = (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
    const linear = (t) => t;

    function rafLoop(duration, onFrame, easing) {
        return new Promise((resolve) => {
            if (duration <= 0) {
                onFrame(1, 1, 0);
                resolve();
                return;
            }
            const start = performance.now();
            let lastElapsed = 0;
            function tick(now) {
                const rawElapsed = now - start;
                const step = Math.min(rawElapsed - lastElapsed, MAX_STEP_MS);
                lastElapsed = rawElapsed;
                const t = Math.min(1, rawElapsed / duration);
                onFrame(easing(t), t, step);
                if (t < 1) requestAnimationFrame(tick);
                else resolve();
            }
            requestAnimationFrame(tick);
        });
    }

    // ---------- 二次贝塞尔 ----------
    // P0 起点、P2 终点，控制点 P1 = 中点上抬 arcHeight（先扬后抑的 StS2 弧线）
    function arcControl(p0, p2, arcHeight) {
        return {
            x: (p0.x + p2.x) / 2,
            y: Math.min(p0.y, p2.y) - arcHeight,
        };
    }
    function pointOnArc(p0, p1, p2, t) {
        const u = 1 - t;
        return {
            x: u * u * p0.x + 2 * u * t * p1.x + t * t * p2.x,
            y: u * u * p0.y + 2 * u * t * p1.y + t * t * p2.y,
        };
    }

    function rectOf(thing) {
        if (!thing) return null;
        if (thing instanceof Element) return thing.getBoundingClientRect();
        if (typeof thing === 'string') {
            const el = document.querySelector(thing);
            return el ? el.getBoundingClientRect() : null;
        }
        if (typeof thing === 'object' && 'left' in thing) return thing;
        return null;
    }
    function centerOf(rect) {
        return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
    }

    // ---------- 卡框色取样 ----------
    // 优先读卡牌元素的 --card-frame-color（游戏按卡种 thorn/bloom/root 定义），
    // 取不到时回退到暗琥珀——融入画面而不是霓虹色。
    function sampleFrameColor(el) {
        try {
            if (el && el instanceof Element) {
                const value = getComputedStyle(el).getPropertyValue('--card-frame-color').trim();
                if (value) return value;
            }
        } catch (err) { /* computed style 不可用时静默回退 */ }
        return '#a08050';
    }
    // 带透明度的颜色：支持 #rrggbb / rgb() 输入；其余原样返回
    function withAlpha(color, alpha) {
        if (typeof color !== 'string') return color;
        const hex = color.trim().match(/^#([0-9a-f]{6})$/i);
        if (hex) {
            const n = parseInt(hex[1], 16);
            return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
        }
        const rgb = color.trim().match(/^rgba?\(([^)]+)\)$/i);
        if (rgb) {
            const parts = rgb[1].split(',').map((s) => s.trim());
            if (parts.length >= 3) {
                return `rgba(${parts[0]}, ${parts[1]}, ${parts[2]}, ${alpha})`;
            }
        }
        return color;
    }

    // ---------- 拖尾：卡牌剪影残影 ----------
    // 沿弧线在卡牌身后撒「小卡片剪影」：63:88 圆角矩形、细边框、无模糊，
    // 颜色 = 卡框色降透明，旋转跟随飞行方向。像实体卡甩过的重影。
    function spawnTrailSliver(x, y, w, h, color, lifeMs, angleDeg) {
        const el = document.createElement('div');
        el.className = 'sts2-trail-card';
        el.style.left = `${x - w / 2}px`;
        el.style.top = `${y - h / 2}px`;
        el.style.width = `${w}px`;
        el.style.height = `${h}px`;
        el.style.setProperty('--sts2-sliver-border', color);
        el.style.setProperty('--sts2-sliver-fill', withAlpha(color, 0.10));
        if (Number.isFinite(angleDeg)) el.style.rotate = `${angleDeg}deg`;
        el.style.setProperty('--sts2-trail-life', `${lifeMs}ms`);
        document.body.appendChild(el);
        setTimeout(() => el.remove(), lifeMs + 40);
    }

    // ---------- 幽灵卡 ----------
    // 优先级：cardEl 克隆 > backTemplate 克隆（游戏真实牌背，可含皮肤图）> 内置牌背
    function makeGhost(cardEl, rect, cardBack, backTemplate) {
        let ghost;
        if (cardEl) {
            ghost = cardEl.cloneNode(true);
        } else if (backTemplate && backTemplate instanceof Element) {
            ghost = backTemplate.cloneNode(true);
        } else {
            ghost = document.createElement('div');
            if (cardBack) {
                const back = document.createElement('div');
                back.className = 'sts2-card-back';
                ghost.appendChild(back);
            }
        }
        ghost.classList.add('sts2-ghost');
        // 以中心定位（对齐 rect 中心），避免半张偏移
        ghost.style.left = `${rect.left + rect.width / 2}px`;
        ghost.style.top = `${rect.top + rect.height / 2}px`;
        ghost.style.width = `${rect.width}px`;
        ghost.style.height = `${rect.height}px`;
        document.body.appendChild(ghost);
        return ghost;
    }

    /*
     * flyCard — 万能弧线飞行（出牌 / 弃牌 / 抽牌 / 牌堆移动共用）
     * opts:
     *   from, to          rect | Element | selector（必填）
     *   cardEl            要克隆的卡牌元素（可空）
     *   cardBack          无 cardEl 时是否画牌背（默认 true）
     *   duration          飞行毫秒（默认 400）
     *   arcHeight         弧顶抬高 px（默认 140；洗牌用 200+）
     *   scaleFrom/scaleTo 起止缩放（出牌 1 → 0.35；抽牌 0.8 → 1）
     *   rotate            飞行中附加旋转角（deg，默认 0）
     *   trailColor        残影颜色（建议 = 卡框色，sampleFrameColor 取样）
     *   trail             是否拖残影（默认 true）
     *   trailStep         撒残影间隔 ms（默认 duration/10，出牌短弃牌长）
     *   ease              'out' | 'in' | 'inout' | 'linear'
     *   z                 幽灵 z-index（默认 4200，与 card-play-flash 同层）
     */
    async function flyCard(opts) {
        const fromRect = rectOf(opts.from);
        const toRect = rectOf(opts.to);
        // 目标元素隐藏或尚未布局时（宽/高为 0）不飞——避免牌冲向 (0,0)
        if (!fromRect || !toRect || fromRect.width < 2 || fromRect.height < 2 || toRect.width < 2 || toRect.height < 2) return;
        const duration = opts.duration ?? 200;
        const arcHeight = opts.arcHeight ?? 140;
        const scaleFrom = opts.scaleFrom ?? 1;
        const scaleTo = opts.scaleTo ?? 1;
        const rotate = opts.rotate ?? 0;
        const easeName = opts.ease || 'out';
        const easing = easeName === 'in' ? easeInCubic
            : easeName === 'inout' ? easeInOutQuad
            : easeName === 'linear' ? linear
            : easeOutCubic;

        const p0 = centerOf(fromRect);
        const p2 = centerOf(toRect);
        const p1 = arcControl(p0, p2, arcHeight);
        const ghost = makeGhost(opts.cardEl, fromRect, opts.cardBack !== false, opts.backTemplate);
        ghost.style.zIndex = String(opts.z ?? 4200);

        await runArcFlight(ghost, p0, p1, p2, {
            duration,
            easing,
            scaleFrom,
            scaleTo,
            rotate,
            width: fromRect.width,
            height: fromRect.height,
            trail: opts.trail !== false,
            trailColor: opts.trailColor,
            trailStep: opts.trailStep,
            sliverScale: opts.sliverScale ?? 0.72,
        });
        ghost.remove();
    }

    /*
     * flyElement — 沿弧线飞行一个已存在（position:fixed，left/top 已摆好）的元素。
     * 不克隆、不负责移除；供 game.js 的 card-play-flash / story.js 的
     * story-card-flight 无缝替换原直线 CSS 动画。
     */
    async function flyElement(el, opts) {
        if (!el) return;
        const rect = el.getBoundingClientRect();
        const toRect = rectOf(opts.to);
        if (!rect || !toRect) return;
        const p0 = centerOf(rect);
        const p2 = centerOf(toRect);
        const p1 = arcControl(p0, p2, opts.arcHeight ?? 140);
        const easeName = opts.ease || 'out';
        const easing = easeName === 'in' ? easeInCubic
            : easeName === 'inout' ? easeInOutQuad
            : easeName === 'linear' ? linear
            : easeOutCubic;
        await runArcFlight(el, p0, p1, p2, {
            duration: opts.duration ?? 200,
            easing,
            scaleFrom: opts.scaleFrom ?? 1,
            scaleTo: opts.scaleTo ?? 1,
            rotate: opts.rotate ?? 0,
            width: rect.width,
            height: rect.height,
            trail: opts.trail !== false,
            trailColor: opts.trailColor,
            trailStep: opts.trailStep,
            sliverScale: opts.sliverScale ?? 0.72,
            baseTransform: opts.baseTransform || '',
        });
    }

    // 弧线飞行的公共主体：WAAPI 关键帧预采样驱动。
    // 位置/缩放/旋转沿贝塞尔与缓动曲线预先采样成关键帧，交给浏览器合成器线程
    // 插值执行——出牌/抽牌伴随的大批量重渲染挤占主线程时，飞行依然逐帧平滑
    // （旧版 rAF 逐帧写 transform 在主线程繁忙时会跳帧，视觉上"只有几个过程"）。
    async function runArcFlight(el, p0, p1, p2, cfg) {
        const frames = Math.max(24, Math.min(64, Math.round(cfg.duration / 16.7)));
        const easing = cfg.easing || linear;
        const keyframes = [];
        const trailSpawns = []; // { atMs, x, y, w, h, angle }
        const trailStep = cfg.trailStep ?? Math.max(16, cfg.duration / 10);
        const wantTrail = cfg.trail && cfg.trailColor;
        let prev = p0;
        let trailAccum = Infinity;
        const stepMs = cfg.duration / frames;
        for (let i = 0; i <= frames; i += 1) {
            const rawT = i / frames;
            const pos = pointOnArc(p0, p1, p2, easing(rawT));
            const scale = cfg.scaleFrom + (cfg.scaleTo - cfg.scaleFrom) * rawT;
            keyframes.push({
                transform: `${cfg.baseTransform || ''}translate(${pos.x - p0.x}px, ${pos.y - p0.y}px)`
                    + ` rotate(${cfg.rotate * rawT}deg) scale(${scale})`,
                offset: rawT,
            });
            if (wantTrail) {
                trailAccum += stepMs;
                if (trailAccum >= trailStep) {
                    trailAccum = 0;
                    const dx = pos.x - prev.x;
                    const dy = pos.y - prev.y;
                    const angle = (dx || dy) ? Math.atan2(dy, dx) * 180 / Math.PI - 90 : 0;
                    const s = cfg.sliverScale * scale;
                    trailSpawns.push({
                        atMs: Math.round(rawT * cfg.duration),
                        x: pos.x,
                        y: pos.y,
                        w: Math.max(10, cfg.width * s),
                        h: Math.max(14, cfg.height * s),
                        angle,
                    });
                    prev = pos;
                }
            }
        }
        el.style.willChange = 'transform';
        const anim = el.animate(keyframes, { duration: cfg.duration, easing: 'linear', fill: 'forwards' });
        const timers = trailSpawns.map((spawn) => setTimeout(
            () => spawnTrailSliver(spawn.x, spawn.y, spawn.w, spawn.h, cfg.trailColor, 240, spawn.angle),
            spawn.atMs,
        ));
        // 超时兜底：个别环境下动画时钟不推进（无头截图、渲染进程异常等），
        // 不能让 await 链路永久挂起（否则抽牌的真身停留在隐藏态）。
        let timedOut = false;
        const guardId = setTimeout(() => {
            timedOut = true;
            try { anim.cancel(); } catch (err) { /* 已结束则忽略 */ }
        }, cfg.duration + 400);
        try {
            await anim.finished;
        } catch (err) { /* cancel / 页面隐藏等中断：按完成处理 */ }
        clearTimeout(guardId);
        timers.forEach(clearTimeout);
        if (timedOut) {
            const last = keyframes[keyframes.length - 1];
            el.style.transform = last.transform;
        }
    }

    /*
     * drawToHand — 回合抽牌：从抽牌堆逐张错峰飞入手牌
     * slots: 每张牌的目标 rect（手牌扇里各槽位的 getBoundingClientRect）
     * onEach(index): 每张卡到达时刻回调（此刻把真实卡牌显示出来）
     */
    async function drawToHand(opts) {
        const pileRect = rectOf(opts.pileEl);
        if (!pileRect) return;
        const slots = opts.slots || [];
        const stagger = opts.stagger ?? 100;
        const duration = opts.duration ?? 175;
        const jobs = slots.map((slotRect, i) => (async () => {
            await delay(i * stagger);
            await flyCard({
                from: pileRect,
                to: slotRect,
                cardBack: true,
                backTemplate: opts.backTemplate,
                duration,
                arcHeight: 90,
                scaleFrom: 0.72,
                scaleTo: 1,
                rotate: (i % 2 === 0 ? 1 : -1) * (22 + i * 5),
                ease: 'out',
                trailColor: opts.trailColor,
                trail: opts.trail !== false,
                sliverScale: 0.55,
                z: 4190 + i,
            });
            if (opts.onEach) opts.onEach(i);
        })());
        await Promise.all(jobs);
    }

    /*
     * fanRelayout — 手牌扇 FLIP 重排
     * 用法：改动 DOM 前调 captureFan(container)，改动后调 playFan(container, opts)
     */
    function captureFan(container) {
        const map = new Map();
        container.querySelectorAll('[data-instance-id]').forEach((el) => {
            map.set(el.dataset.instanceId, el.getBoundingClientRect());
        });
        return map;
    }
    function playFan(container, before, opts) {
        if (!before || !before.size) return;
        const duration = (opts && opts.duration) ?? 90;
        const skipNew = (opts && opts.skipNew) || null;
        container.querySelectorAll('[data-instance-id]').forEach((el) => {
            const old = before.get(el.dataset.instanceId);
            const newPose = el.style.transform || 'none';
            if (!old) {
                // 新牌默认从下方淡入；若调用方另有入场动画（如抽牌飞入）则跳过
                if (skipNew && skipNew.has(el.dataset.instanceId)) return;
                el.animate(
                    [
                        { transform: `${newPose} translateY(28px)`, opacity: 0 },
                        { transform: newPose, opacity: 1 },
                    ],
                    { duration, easing: 'cubic-bezier(0.34, 1.56, 0.64, 1)' },
                );
                return;
            }
            const now = el.getBoundingClientRect();
            const dx = old.left + old.width / 2 - (now.left + now.width / 2);
            if (Math.abs(dx) < 1) return;
            // FLIP：旧位姿 → 新位姿（内联样式已是新姿态，动画期间叠加位移补偿）
            el.animate(
                [
                    { transform: `${newPose} translateX(${dx}px)` },
                    { transform: newPose },
                ],
                { duration, easing: 'cubic-bezier(0.22, 0.9, 0.35, 1.1)' },
            );
        });
    }

    /*
     * endTurnDiscard — 结束回合：手牌逐张错峰飞弃牌堆
     * cardEls: 参与弃牌的手牌元素（Retain 的不要传进来）
     */
    async function endTurnDiscard(opts) {
        const pileRect = rectOf(opts.pileEl);
        if (!pileRect) return;
        const cards = opts.cardEls || [];
        const stagger = opts.stagger ?? 60;
        const duration = opts.duration ?? 210;
        const color = opts.trailColor;
        const jobs = cards.map((el, i) => (async () => {
            const rect = el.getBoundingClientRect();
            el.style.visibility = 'hidden'; // 真身立刻藏起，幽灵接班
            await delay(i * stagger);
            await flyCard({
                from: rect,
                to: pileRect,
                cardEl: el,
                duration,
                arcHeight: Math.max(120, (rect.top - pileRect.top) * 0.5),
                scaleFrom: 1,
                scaleTo: 0.4,
                rotate: 46 + (i % 3) * 12,
                ease: 'inout',
                trailColor: typeof color === 'function' ? color(el, i) : color,
                z: 4180 + i,
            });
            if (opts.onEach) opts.onEach(i, el);
        })());
        await Promise.all(jobs);
    }

    /*
     * shuffleStream — 洗牌：弃牌堆整堆多流抛物线飞回抽牌堆
     * StS2 实测：单张 ~700ms、错峰 ~30ms、2-3 条流并行、全程 ~1.4s、不阻塞抽牌
     * 残影用低饱和苔绿（花园主题），不带霓虹感
     */
    async function shuffleStream(opts) {
        const fromRect = rectOf(opts.fromEl);
        const toRect = rectOf(opts.toEl);
        if (!fromRect || !toRect) return;
        const count = opts.count ?? 10;
        const streams = opts.streams ?? 3;
        const stagger = opts.stagger ?? 15;
        const duration = opts.duration ?? 350;
        const jobs = [];
        for (let i = 0; i < count; i += 1) {
            jobs.push((async () => {
                await delay(i * stagger);
                await flyCard({
                    from: fromRect,
                    to: toRect,
                    cardBack: true,
                    backTemplate: opts.backTemplate,
                    duration,
                    arcHeight: 190 + (i % streams) * 42,
                    scaleFrom: 0.5,
                    scaleTo: 0.42,
                    rotate: (i % 2 === 0 ? 1 : -1) * (26 + (i % 5) * 9),
                    ease: 'inout',
                    trail: i % 3 === 0, // 只给每第 3 张拖残影，密度不糊
                    trailColor: opts.trailColor || 'rgba(124, 154, 130, 0.55)',
                    sliverScale: 0.5,
                    z: 4170 + (i % 8),
                });
                if (opts.onEach) opts.onEach(i);
            })());
        }
        await Promise.all(jobs);
    }

    // ---------- 伤害数字 / 状态文字 ----------
    const NUM_FONT = 'Georgia, "Times New Roman", "Noto Serif SC", serif';
    function popText(opts) {
        const rect = rectOf(opts.target);
        if (!rect) return;
        const el = document.createElement('div');
        el.className = `sts2-pop sts2-pop-${opts.variant || 'damage'}`;
        el.textContent = String(opts.text ?? '');
        el.style.left = `${rect.left + rect.width / 2}px`;
        el.style.top = `${rect.top + rect.height * 0.28}px`;
        if (opts.color) el.style.color = opts.color;
        el.style.fontSize = `${opts.size || 44}px`;
        el.style.fontFamily = NUM_FONT;
        document.body.appendChild(el);
        setTimeout(() => el.remove(), opts.life || 900);
    }

    // ---------- 震屏 ----------
    async function shake(opts) {
        const el = opts.el || document.body;
        const intensity = opts.intensity ?? 6;
        const duration = opts.duration ?? 220;
        const freq = opts.freq ?? 34;
        await rafLoop(duration, (_e, rawT) => {
            const decay = 1 - rawT;
            const dx = Math.sin(rawT * freq * 2.1) * intensity * decay;
            const dy = Math.cos(rawT * freq * 1.7) * intensity * 0.6 * decay;
            el.style.transform = `translate(${dx}px, ${dy}px)`;
        }, linear);
        el.style.transform = '';
    }

    function delay(ms) {
        return new Promise((resolve) => setTimeout(resolve, ms));
    }

    const STS2 = {
        flyCard,
        flyElement,
        drawToHand,
        captureFan,
        playFan,
        endTurnDiscard,
        shuffleStream,
        popText,
        shake,
        sampleFrameColor,
        // 节奏常量表（2026-10-01：整体提速 2 倍，基础值 = 原拆解值 ÷ 2）
        TIMING: {
            DRAW_FLY: 175,
            DRAW_STAGGER: 100,
            DRAW_STAGGER_BATCH: 30,
            PLAY_FLY: 200,
            DISCARD_FLY: 210,
            DISCARD_STAGGER: 60,
            SHUFFLE_FLY: 350,
            SHUFFLE_STAGGER: 15,
            HOVER: 60,
            FAN_RELAYOUT: 90,
            BANNER_HOLD: 900,
        },
    };

    root.STS2 = STS2;
})(window);
