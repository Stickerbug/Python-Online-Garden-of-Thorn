"""反馈 #117：故事/经典装备公转环的角度必须连续，掉帧欠账也不能丢。

用真实的 ``static/js/equipment_motion.js`` 在 Node 里跑一个最小 DOM 夹具：

* 重建公转元素时必须续用上一次的角度，而不是重新按墙上时钟取相位（相位跳变看起来
  就是“已经转完一圈后又突然多转一段”）；
* 掉帧/挂起期间的时间记入欠账并逐帧补回（保留单帧上限），既不一次跳过去，也不丢弃。

没有 Node 时整组跳过。
"""

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EQUIPMENT_MOTION_JS = ROOT / "static" / "js" / "equipment_motion.js"

HARNESS_JS = textwrap.dedent(
    """
    'use strict';
    const fs = require('fs');
    const vm = require('vm');

    const source = fs.readFileSync(process.argv[2], 'utf8');
    const rafQueue = [];
    let clock = 0;
    let wallClockMs = 0;

    function makeElement(name) {
        return {
            name,
            isConnected: true,
            style: {},
            dataset: {},
            classList: { add() {}, remove() {}, toggle() {} },
            querySelectorAll: () => [],
            querySelector: () => null,
            contains: () => false,
        };
    }

    const listeners = [];
    const fakeDocument = {
        addEventListener(type, fn) { listeners.push({ type, fn }); },
        removeEventListener(type, fn) {
            const index = listeners.findIndex((entry) => entry.fn === fn);
            if (index >= 0) listeners.splice(index, 1);
        },
        dispatch(type, event) {
            listeners.filter((entry) => entry.type === type).forEach((entry) => entry.fn(event));
        },
    };

    const fakeWindow = {
        matchMedia: () => ({ matches: false }),
        performance: { now: () => clock },
        requestAnimationFrame(cb) { rafQueue.push(cb); return rafQueue.length; },
    };

    globalThis.window = fakeWindow;
    globalThis.document = fakeDocument;
    Date.now = () => wallClockMs;

    vm.runInThisContext(source, { filename: 'equipment_motion.js' });
    const motion = fakeWindow.GTNEquipmentMotion;

    function pump(ms) {
        clock += ms;
        const queue = rafQueue.splice(0, rafQueue.length);
        queue.forEach((cb) => cb(clock));
    }

    function angleOf(element) {
        const match = /rotate\\(([-\\d.]+)deg\\)/.exec(element.style.transform || '');
        return match ? parseFloat(match[1]) : null;
    }

    function degreesForMs(ms, periodMs) {
        return ms / periodMs * 360;
    }

    const options = {
        periodSec: 20,
        chipSelector: ':scope > chip',
        visualSelector: '.visual',
    };
    const result = {};

    // 1) 元素重建续用角度：先转 ~1 秒，把元素摘掉，再让墙上时钟跳到远处相位。
    {
        const pauseRoot = makeElement('story-avatar-stack');
        const first = makeElement('orbiter-1');
        const firstOptions = Object.assign({}, options, { pauseRoot });
        motion.startOrbitMotion(first, firstOptions);
        pump(0);
        for (let i = 0; i < 60; i += 1) pump(1000 / 60);
        const lastAngle = angleOf(first);

        first.isConnected = false;
        pump(1000 / 60);
        wallClockMs = 12000;
        const second = makeElement('orbiter-2');
        motion.startOrbitMotion(second, firstOptions);
        pump(0);
        result.rebuild = {
            lastAngle,
            rebuiltAngle: angleOf(second),
            wallClockPhase: 12000 / 20000 * 360,
        };
    }

    // 2) 掉帧欠账：一次 200ms 的间隔应该被完整补回（而不是丢掉 80ms），单帧不超上限。
    {
        const pauseRoot = makeElement('story-avatar-stack-2');
        const orbiter = makeElement('orbiter-3');
        motion.startOrbitMotion(orbiter, Object.assign({}, options, { pauseRoot }));
        pump(0);
        const start = angleOf(orbiter);
        let maxStep = 0;
        let previous = start;
        const sample = () => {
            const current = angleOf(orbiter);
            maxStep = Math.max(maxStep, current - previous);
            previous = current;
        };
        pump(200);
        sample();
        const afterGap = angleOf(orbiter);
        for (let i = 0; i < 10; i += 1) { pump(1000 / 60); sample(); }
        const elapsedMs = 200 + 10 * (1000 / 60);
        result.debt = {
            start,
            afterGap,
            afterCatchup: angleOf(orbiter),
            expected: degreesForMs(elapsedMs, 20000),
            maxSingleStep: maxStep,
            stepLimit: degreesForMs(120, 20000),
        };
    }

    // 3) 悬停暂停不产生欠账：指针停留期间角度不动，离开后按正常速度继续。
    {
        const pauseRoot = makeElement('classic-avatar-stack');
        pauseRoot.contains = (node) => node === pauseRoot || (node && node.owner === pauseRoot);
        const child = { owner: pauseRoot };
        const orbiter = makeElement('orbiter-4');
        motion.startOrbitMotion(orbiter, Object.assign({}, options, { pauseRoot }));
        pump(0);
        pump(1000 / 60);
        const beforeHover = angleOf(orbiter);
        fakeDocument.dispatch('pointerover', { target: child, relatedTarget: null });
        pump(1000 / 60);
        pump(500);
        const duringHover = angleOf(orbiter);
        fakeDocument.dispatch('pointerout', { target: child, relatedTarget: null });
        pump(1000 / 60);
        result.hover = {
            beforeHover,
            duringHover,
            afterResume: angleOf(orbiter),
            normalStep: degreesForMs(1000 / 60, 20000),
        };
    }

    process.stdout.write(JSON.stringify(result));
    """
)


@pytest.fixture(scope="module")
def orbit_probe(tmp_path_factory):
    node = shutil.which("node")
    if not node:
        pytest.skip("node 不可用，跳过公转环行为契约测试")
    harness = tmp_path_factory.mktemp("orbit") / "orbit_harness.js"
    harness.write_text(HARNESS_JS, encoding="utf-8")
    completed = subprocess.run(
        [node, str(harness), str(EQUIPMENT_MOTION_JS)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_orbit_rebuild_continues_from_last_angle(orbit_probe):
    rebuild = orbit_probe["rebuild"]
    assert rebuild["lastAngle"] is not None
    # 墙上时钟相位（216deg）与重建前的角度相差近 200deg，续用逻辑必须无视它。
    assert abs(rebuild["wallClockPhase"] - rebuild["lastAngle"]) > 150
    assert abs(rebuild["rebuiltAngle"] - rebuild["lastAngle"]) <= 0.5


def test_orbit_debt_is_repaid_instead_of_discarded(orbit_probe):
    debt = orbit_probe["debt"]
    advanced = debt["afterCatchup"] - debt["start"]
    assert advanced == pytest.approx(debt["expected"], abs=0.05)
    # 单帧仍然有上限：恢复时不会“一次跳过去”。
    assert debt["maxSingleStep"] <= debt["stepLimit"] + 0.01
    assert debt["afterGap"] - debt["start"] == pytest.approx(debt["stepLimit"], abs=0.01)


def test_orbit_hover_pause_does_not_accumulate_debt(orbit_probe):
    hover = orbit_probe["hover"]
    assert hover["duringHover"] == pytest.approx(hover["beforeHover"], abs=0.001)
    resumed_step = hover["afterResume"] - hover["duringHover"]
    assert 0 < resumed_step <= hover["normalStep"] * 1.2
