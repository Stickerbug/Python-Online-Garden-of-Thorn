(function exposeEquipmentMotion(root) {
    'use strict';

    const FNV_OFFSET = 0x811c9dc5;
    const FNV_PRIME = 0x01000193;
    const UNIT_DIVISOR = 0x100000000;
    const orbitContexts = new Map();
    // 反馈 #117：单帧最多推进的真实时长，以及挂起/掉帧欠账的上限。
    // 欠账逐帧补回（而不是丢弃，也不是一次跳过去），恢复时不会出现“突然多转”。
    const ORBIT_MAX_STEP_MS = 120;
    const ORBIT_MAX_PENDING_MS = 240;
    let orbitFrame = 0;

    function mix32(value) {
        let hash = value >>> 0;
        hash ^= hash >>> 16;
        hash = Math.imul(hash, 0x7feb352d);
        hash ^= hash >>> 15;
        hash = Math.imul(hash, 0x846ca68b);
        hash ^= hash >>> 16;
        return hash >>> 0;
    }

    function hash32(value) {
        let hash = FNV_OFFSET;
        const text = String(value == null ? '' : value);
        for (let index = 0; index < text.length; index += 1) {
            hash ^= text.charCodeAt(index);
            hash = Math.imul(hash, FNV_PRIME);
        }
        return mix32(hash >>> 0);
    }

    function unit(seed) {
        return hash32(seed) / UNIT_DIVISOR;
    }

    function reducedMotion() {
        return Boolean(window.matchMedia
            && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    }

    function nowMilliseconds() {
        return (window.performance && typeof window.performance.now === 'function')
            ? window.performance.now()
            : Date.now();
    }

    function periodSeconds(value) {
        const parsed = Number(value);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : 20;
    }

    /**
     * 同一玩家同一张装备的稳定自转相位（秒）。
     * 返回负值，配合 CSS 负 animation-delay 使用。
     */
    function spinDelaySeconds(ownerKey, itemKey, period) {
        const periodSec = periodSeconds(period);
        const offset = unit(`${ownerKey || 'owner'}\u0001${itemKey || 'item'}`);
        return -Number((offset * periodSec).toFixed(3));
    }

    /**
     * 公转环共用的负延迟，避免同一时间创建的元素在相位上跳变。
     */
    function orbitDelaySeconds(period, nowMs = Date.now()) {
        const periodSec = periodSeconds(period);
        const elapsed = nowMs / 1000;
        return -((elapsed % periodSec) + periodSec) % periodSec;
    }

    /**
     * 读取公转元素当前实际旋转角度，返回能让“反向旋转层”立即对齐的负延迟。
     * 这样即使公转中途插入新装备（含暂停/隐藏后恢复），角标与外框也不会相对屏幕倾斜。
     */
    function counterDelaySeconds(orbitElement, period, nowMs = Date.now()) {
        const periodSec = periodSeconds(period);
        const el = orbitElement;
        if (el && typeof window !== 'undefined' && window.getComputedStyle) {
            try {
                const transform = window.getComputedStyle(el).transform;
                if (transform && transform !== 'none') {
                    const matrix = new DOMMatrixReadOnly(transform);
                    let degrees = Math.atan2(matrix.b, matrix.a) * 180 / Math.PI;
                    degrees = ((degrees % 360) + 360) % 360;
                    return -(degrees / 360 * periodSec);
                }
            } catch (_) {
                // 兜底到按当前时间的普通相位
            }
        }
        return orbitDelaySeconds(periodSec, nowMs);
    }

    function cleanupEnter(el) {
        if (!el || el._gtnMotionEnterTimer == null) return;
        window.clearTimeout(el._gtnMotionEnterTimer);
        el._gtnMotionEnterTimer = null;
        el.classList.remove('is-entering');
    }

    /**
     * 新装备先以 scale 0 被放进环中心，下一帧再把半径缩放过渡到 1。
     * 公转动画不受影响，因此会呈现一边旋转一边加速向外展开。
     */
    function beginEnter(el, options) {
        if (!el) return;
        const config = options || {};
        const scaleVar = config.scaleVar || '--equip-radius-scale';
        const fast = reducedMotion();
        const epoch = (el._gtnMotionEnterEpoch || 0) + 1;
        el._gtnMotionEnterEpoch = epoch;
        if (el.dataset.motionLeaving === '1') return;
        el.classList.add('is-entering');
        el.style.setProperty(scaleVar, '0');
        el.style.opacity = '0';
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                if (!el.isConnected) return;
                if (el._gtnMotionEnterEpoch !== epoch || el.dataset.motionLeaving === '1') return;
                el.style.setProperty(scaleVar, config.targetValue || '1');
                el.style.opacity = '';
                if (fast) {
                    el.classList.remove('is-entering');
                    return;
                }
                const cleanupMs = Math.max(Number(config.cleanupMs) || 720, 120);
                el._gtnMotionEnterTimer = window.setTimeout(() => {
                    el.classList.remove('is-entering');
                    el._gtnMotionEnterTimer = null;
                }, cleanupMs);
            });
        });
    }

    function clearLeaveTimer(el) {
        if (!el || el._gtnMotionLeaveTimer == null) return;
        window.clearTimeout(el._gtnMotionLeaveTimer);
        el._gtnMotionLeaveTimer = null;
    }

    /**
     * 移除装备：原地淡出（不再缩回环中心），由 onComplete 负责真正删除元素。
     * 如需旧版缩回中心效果，可传 retractToCenter: true。
     */
    function startLeave(el, options) {
        if (!el || el.dataset.motionLeaving === '1') return;
        const config = options || {};
        const scaleVar = config.scaleVar || '--equip-radius-scale';
        el._gtnMotionEnterEpoch = (el._gtnMotionEnterEpoch || 0) + 1;
        if (el._gtnMotionEnterTimer != null) {
            window.clearTimeout(el._gtnMotionEnterTimer);
            el._gtnMotionEnterTimer = null;
        }
        el.dataset.motionLeaving = '1';
        el.classList.add('is-leaving');
        if (config.retractToCenter) {
            el.style.setProperty(scaleVar, config.targetValue || '0');
        }
        el.style.opacity = '0';
        clearLeaveTimer(el);
        const fast = reducedMotion();
        const removeMs = Math.max(Number(config.removeMs) || 700, fast ? 20 : 120);
        el._gtnMotionLeaveTimer = window.setTimeout(() => {
            el._gtnMotionLeaveTimer = null;
            if (typeof config.onComplete === 'function') config.onComplete(el);
        }, removeMs);
    }

    function cancelLeave(el, options) {
        if (!el) return;
        const config = options || {};
        const scaleVar = config.scaleVar || '--equip-radius-scale';
        clearLeaveTimer(el);
        if (el.dataset.motionLeaving === '1') {
            el.classList.remove('is-leaving');
            delete el.dataset.motionLeaving;
            el.style.setProperty(scaleVar, config.restoreValue || '1');
            el.style.opacity = '';
        }
    }

    function findAnimation(element, name) {
        if (!element || typeof element.getAnimations !== 'function') return null;
        return (element.getAnimations() || []).find((animation) => animation.animationName === name) || null;
    }

    function normalizeOrbitAngle(value) {
        const angle = Number(value);
        if (!Number.isFinite(angle)) return null;
        return ((angle % 360) + 360) % 360;
    }

    /**
     * 反馈 #117：公转环元素被重建时，优先续用上一次画出的角度，
     * 而不是重新按墙上时钟取相位——相位跳变看起来就是“又多转了一段”。
     */
    function rememberedOrbitAngle(orbitElement, config) {
        const sources = [orbitElement, config && config.pauseRoot];
        for (const source of sources) {
            if (!source) continue;
            const angle = normalizeOrbitAngle(source._gtnOrbitAngle);
            if (angle != null) return angle;
        }
        return null;
    }

    function rememberOrbitAngle(orbitElement, config, angle) {
        const normalized = normalizeOrbitAngle(angle);
        if (normalized == null) return;
        if (orbitElement) orbitElement._gtnOrbitAngle = normalized;
        const root = config && config.pauseRoot;
        if (root) root._gtnOrbitAngle = normalized;
    }

    function orbitInitialAngle(periodSec, carriedAngle) {
        const carried = normalizeOrbitAngle(carriedAngle);
        if (carried != null) return carried;
        const elapsed = Date.now() / 1000;
        return ((elapsed % periodSec) + periodSec) % periodSec / periodSec * 360;
    }

    function orbitTick(timestamp) {
        orbitFrame = 0;
        const now = timestamp != null ? timestamp : nowMilliseconds();
        orbitContexts.forEach((context, orbitElement) => {
            if (!orbitElement.isConnected) {
                rememberOrbitAngle(orbitElement, context, context.angle);
                detachOrbitPointerHandlers(context);
                orbitContexts.delete(orbitElement);
                return;
            }
            const paused = reducedMotion() || Boolean(context.pointerInside);
            if (!paused && context.lastTime != null) {
                // 掉帧、后台挂起期间的时间记入欠账，之后逐帧补回。
                context.pendingMs = Math.min(
                    ORBIT_MAX_PENDING_MS,
                    context.pendingMs + Math.max(0, now - context.lastTime),
                );
            }
            context.lastTime = now;
            if (!paused && context.pendingMs > 0) {
                const stepMs = Math.min(ORBIT_MAX_STEP_MS, context.pendingMs);
                context.pendingMs -= stepMs;
                context.angle = (context.angle + stepMs / context.periodMs * 360) % 360;
            }
            rememberOrbitAngle(orbitElement, context, context.angle);
            orbitElement.style.transform = `rotate(${context.angle.toFixed(4)}deg)`;
            orbitElement.querySelectorAll(context.chipSelector).forEach((chip) => {
                const visual = chip.querySelector(context.visualSelector);
                if (visual) {
                    visual.style.transform = `rotate(${(-context.angle).toFixed(4)}deg)`;
                }
            });
        });
        if (orbitContexts.size) orbitFrame = window.requestAnimationFrame(orbitTick);
    }

    function detachOrbitPointerHandlers(context) {
        if (!context || !context.pointerHandlers) return;
        document.removeEventListener('pointerover', context.pointerHandlers.onPointerOver, true);
        document.removeEventListener('pointerout', context.pointerHandlers.onPointerOut, true);
        context.pointerHandlers = null;
        context.pointerInside = false;
    }

    function attachOrbitPointerHandlers(context) {
        if (!context || !context.pauseRoot || context.pointerHandlers) return;
        const root = context.pauseRoot;
        context.pointerInside = false;
        context.pointerHandlers = {
            onPointerOver: (event) => {
                if (!event.target || !root.isConnected) return;
                context.pointerInside = root.contains(event.target);
            },
            onPointerOut: (event) => {
                const nextTarget = event.relatedTarget;
                if (!nextTarget || !root.isConnected || !root.contains(nextTarget)) {
                    context.pointerInside = false;
                }
            },
        };
        document.addEventListener('pointerover', context.pointerHandlers.onPointerOver, true);
        document.addEventListener('pointerout', context.pointerHandlers.onPointerOut, true);
    }

    function ensureOrbitFrame() {
        if (!orbitFrame && orbitContexts.size) {
            orbitFrame = window.requestAnimationFrame(orbitTick);
        }
    }

    /**
     * 用同一个 JS 角度同时驱动公转环与内部反向旋转层。
     * 两者永远使用同一份角度，不会因为 CSS 动画创建时间不同而留下相位差。
     */
    function startOrbitMotion(orbitElement, options) {
        if (!orbitElement) return;
        const config = options || {};
        let context = orbitContexts.get(orbitElement);
        if (!context) {
            const periodSec = Number(config.periodSec) > 0 ? Number(config.periodSec) : 20;
            let carriedAngle = normalizeOrbitAngle(config.initialAngle);
            if (carriedAngle == null) carriedAngle = rememberedOrbitAngle(orbitElement, config);
            context = {
                angle: orbitInitialAngle(periodSec, carriedAngle),
                periodMs: periodSec * 1000,
                pendingMs: 0,
                chipSelector: config.chipSelector || ':scope > .classic-equip-chip',
                visualSelector: config.visualSelector || '.classic-equip-visual',
                pauseRoot: config.pauseRoot || null,
                pointerInside: false,
                pointerHandlers: null,
                lastTime: null,
            };
            orbitContexts.set(orbitElement, context);
        }
        if (config.pauseRoot && config.pauseRoot !== context.pauseRoot) {
            detachOrbitPointerHandlers(context);
            context.pauseRoot = config.pauseRoot;
            attachOrbitPointerHandlers(context);
        } else if (!context.pauseRoot && config.pauseRoot) {
            context.pauseRoot = config.pauseRoot;
            attachOrbitPointerHandlers(context);
        }
        if (config.chipSelector) context.chipSelector = config.chipSelector;
        if (config.visualSelector) context.visualSelector = config.visualSelector;
        orbitElement.classList.add('gtn-orbit-js');
        attachOrbitPointerHandlers(context);
        ensureOrbitFrame();
        return context;
    }

    function stopOrbitMotion(orbitElement) {
        if (!orbitElement) return;
        const context = orbitContexts.get(orbitElement);
        if (context) {
            rememberOrbitAngle(orbitElement, context, context.angle);
            detachOrbitPointerHandlers(context);
            orbitContexts.delete(orbitElement);
        }
        orbitElement.classList.remove('gtn-orbit-js');
    }

    /**
     * 把某个装备内层的反向旋转动画，对齐到公转环动画的 startTime。
     * 这样即使装备是中途插入、或浏览器重启了动画，角标/外框也不会残留相位差。
     */
    function alignCounterRotation(host, orbitElement, options = {}) {
        if (!host || !orbitElement || host._gtnCounterAlignPending) return;
        const config = options || {};
        const ringAnimationName = config.ringAnimationName || 'classicEquipmentRingOrbit';
        const counterAnimationName = config.counterAnimationName || 'classicEquipmentCounterOrbit';
        const counterSelector = config.counterSelector || '.classic-equip-visual';
        const orbitAnimation = findAnimation(orbitElement, ringAnimationName);
        if (!orbitAnimation) return;
        host._gtnCounterAlignPending = true;
        let attempts = 0;
        const tryAlign = () => {
            host._gtnCounterAlignPending = false;
            const visual = host.querySelector(counterSelector);
            const counterAnimation = visual && findAnimation(visual, counterAnimationName);
            if (!counterAnimation) {
                attempts += 1;
                if (attempts < 3) {
                    host._gtnCounterAlignPending = true;
                    requestAnimationFrame(tryAlign);
                }
                return;
            }
            const targetStart = orbitAnimation.startTime;
            if (targetStart == null || counterAnimation.startTime == null) return;
            if (Math.abs(Number(counterAnimation.startTime) - Number(targetStart)) > 0.01) {
                try {
                    counterAnimation.startTime = targetStart;
                } catch (_) {
                    // 个别环境不允许写入 CSS 动画的 startTime，忽略即可
                }
            }
        };
        requestAnimationFrame(tryAlign);
    }

    root.GTNEquipmentMotion = Object.freeze({
        hash32,
        unit,
        reducedMotion,
        spinDelaySeconds,
        orbitDelaySeconds,
        counterDelaySeconds,
        beginEnter,
        startLeave,
        cancelLeave,
        cleanupEnter,
        alignCounterRotation,
        startOrbitMotion,
        stopOrbitMotion,
    });
})(window);
