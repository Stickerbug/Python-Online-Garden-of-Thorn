# -*- coding: utf-8 -*-
"""合成大花花：纯规则核心（static/js/suika_core.js）的行为测试。

物理游戏没法在 Python 里逐位重放，所以这一层用 Node 跑真实物理核心，
断言的是**规则本身**：合成链与计分、投放冷却、判负线 1 秒规则、
随机只取最小 5 档、以及“种子 + 投放序列”重放的确定性。
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import unittest

import minigame_2048_service as svc

try:
    import app as gtn
except Exception as exc:  # pragma: no cover - 缺依赖时明确跳过
    gtn = None
    IMPORT_ERROR = str(exc)
else:
    IMPORT_ERROR = ""

ROOT = pathlib.Path(__file__).resolve().parents[1]
CORE_JS = ROOT / "static" / "js" / "suika_core.js"
MATTER_JS = ROOT / "static" / "vendor" / "matter.min.js"

NODE_SCRIPT = """
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
const require = createRequire(import.meta.url);
const Matter = require(process.argv[1]);
const core = await import(pathToFileURL(process.argv[2]).href);
const payload = JSON.parse(process.argv[3]);
const out = {};

// 1) 合成与计分：两颗最小档相撞 -> 第 2 档（Ant Egg），得分 = 3；冷却期内的投放被拒绝
{
  const game = new core.SuikaGame(Matter, { seed: payload.mergeSeed });
  game.queue = [0, 0, 0];
  const first = game.drop(320);
  const blocked = game.drop(320);
  core.settle(Matter, game, 6000);
  game.advance(700);
  const second = game.drop(320);
  core.settle(Matter, game, 6000);
  game.advance(400);
  const snapshot = game.snapshot();
  out.merge = {
    firstOk: first.ok,
    blockedReason: blocked.reason,
    secondOk: second.ok,
    score: snapshot.score,
    tiers: snapshot.balls.map((ball) => ball.tier),
    drops: snapshot.totalDrops,
  };
}

// 2) 确定性：同一「种子 + 投放序列」两次重放必须完全一致
{
  const a = core.replay(Matter, payload.seed, payload.drops).snapshot();
  const b = core.replay(Matter, payload.seed, payload.drops).snapshot();
  const c = core.replay(Matter, payload.seed + 1, payload.drops).snapshot();
  out.deterministic = {
    same: JSON.stringify(a) === JSON.stringify(b),
    differentSeedDiffers: JSON.stringify(a) !== JSON.stringify(c),
    score: a.score,
    balls: a.balls.length,
    top: a.balls.length ? Math.max(...a.balls.map((ball) => ball.tier)) : -1,
  };
}

// 3) 判负线：球停在线上一整秒才结束；还在动的球不算
{
  const game = new core.SuikaGame(Matter, { seed: 7 });
  game.spawnBall(4, 320, 120, { isStatic: true });
  game.spawnBall(0, 140, 700);
  game.advance(900);
  const beforeOneSecond = game.gameOver;
  game.advance(300);
  out.loseLine = { beforeOneSecond, afterOneSecond: game.gameOver, ms: Math.round(game.timeMs) };

  const moving = new core.SuikaGame(Matter, { seed: 8 });
  const fast = moving.spawnBall(4, 320, 120, { velocity: { x: 0, y: 6 } });
  moving.spawnBall(0, 140, 700);
  for (let i = 0; i < 6; i += 1) moving.advance(1000 / 60);
  out.loseMoving = {
    speed: Math.round(Math.abs(fast.body.velocity.y) * 1000) / 1000,
    overMs: moving.balls.length ? moving.balls[0].overMs : -1,
    gameOver: moving.gameOver,
  };
}

// 4) 生成规则 v2：随分数开放、按分值加权、防连出 / 防短时间重复
{
  const game = new core.SuikaGame(Matter, { seed: core.seedFromText('suika') });
  const tiers = [];
  for (let i = 0; i < 400; i += 1) tiers.push(game.rollTier());
  const counts = {};
  tiers.forEach((tier) => { counts[tier] = (counts[tier] || 0) + 1; });
  const lowCounts = [0, 1, 2, 3].map((tier) => counts[tier] || 0);

  const rich = new core.SuikaGame(Matter, { seed: 4242 });
  rich.score = 5000;
  const richTiers = [];
  for (let i = 0; i < 400; i += 1) richTiers.push(rich.rollTier());
  const rareAt = richTiers.map((tier, index) => (tier === 5 ? index : -1)).filter((index) => index >= 0);
  let spacingViolations = 0;
  for (let i = 1; i < rareAt.length; i += 1) {
    if (rareAt[i] - rareAt[i - 1] < core.SPAWN_RARE_WINDOW) spacingViolations += 1;
  }

  out.pool = {
    gates: [core.maxSpawnTierFor(0), core.maxSpawnTierFor(301), core.maxSpawnTierFor(1801)],
    lowTiers: [...new Set(tiers)].sort((a, b) => a - b),
    lowCounts,
    rarestTier: lowCounts.indexOf(Math.min(...lowCounts)),
    smallShare: Math.round(((lowCounts[0] + lowCounts[1]) / tiers.length) * 100) / 100,
    richHas4: richTiers.includes(4),
    richHas5: richTiers.includes(5),
    spacingViolations,
  };
}

// 5) 落点预测：往已经有的球上丢，预测高度应该在它上面
{
  const game = new core.SuikaGame(Matter, { seed: 99 });
  game.queue = [3, 0, 0];
  game.drop(320);
  core.settle(Matter, game, 6000);
  game.advance(400);
  const ball = game.balls[0];
  const predicted = game.predictLanding(320, 0);
  out.landing = {
    existed: !!ball,
    predictedY: Math.round(predicted.y),
    ballY: ball ? Math.round(ball.body.position.y) : -1,
    ballTop: ball ? Math.round(ball.body.position.y - core.TIERS[ball.tier].radius) : -1,
    landedOnBall: predicted.landedOnBall,
  };
}

// 6) 存档：serialize 出来的投放序列能重放出同样的分数与结束状态
{
  const game = core.replay(Matter, payload.seed, payload.drops);
  const saved = game.serialize();
  const again = core.replay(Matter, saved.seed, saved.drops);
  out.save = {
    version: saved.v,
    drops: saved.drops.length,
    scoreSame: saved.score === again.score,
    overSame: saved.gameOver === again.gameOver,
    ballsSame: game.snapshot().balls.length === again.snapshot().balls.length,
  };
}

console.log(JSON.stringify(out));
"""


class SuikaCoreTests(unittest.TestCase):
    def run_node(self, payload):
        node = shutil.which("node")
        if not node:
            self.skipTest("没有 node：跳过合成大花花核心测试")
        completed = subprocess.run(
            [node, "--input-type=module", "-e", NODE_SCRIPT,
             str(MATTER_JS), str(CORE_JS), json.dumps(payload)],
            capture_output=True, text=True, timeout=180, check=True,
        )
        return json.loads(completed.stdout.strip().splitlines()[-1])

    def test_core_rules(self):
        result = self.run_node({
            "mergeSeed": 12345,
            "seed": 987654321,
            "drops": [
                {"t": 0, "x": 300},
                {"t": 900, "x": 280},
                {"t": 1800, "x": 340},
                {"t": 2900, "x": 250},
                {"t": 4000, "x": 320},
                {"t": 5200, "x": 300},
            ],
        })

        merge = result["merge"]
        self.assertTrue(merge["firstOk"])
        self.assertEqual(merge["blockedReason"], "cooldown")
        self.assertTrue(merge["secondOk"])
        self.assertEqual(merge["tiers"], [1], "两颗最小档应该合成第 1 档（Ant Egg）")
        self.assertEqual(merge["score"], 3, "按合成出的新档位给分：Ant Egg = 3")
        self.assertEqual(merge["drops"], 2)

        deterministic = result["deterministic"]
        self.assertTrue(deterministic["same"], "同一份种子与投放序列必须完全一致")
        self.assertTrue(deterministic["differentSeedDiffers"], "换种子应当得到不同结果")
        self.assertGreaterEqual(deterministic["top"], 0)

        lose = result["loseLine"]
        self.assertFalse(lose["beforeOneSecond"], "线上一整秒之前不该判负")
        self.assertTrue(lose["afterOneSecond"], "停在判负线上满 1 秒必须结束")

        moving = result["loseMoving"]
        self.assertGreaterEqual(moving["speed"], 0.5, "这颗球应该还在动")
        self.assertEqual(moving["overMs"], 0, "还在动的球不该计入线上停留时间")
        self.assertFalse(moving["gameOver"])

        pool = result["pool"]
        self.assertEqual(pool["gates"], [3, 4, 5], "生成档位应该随分数开放")
        self.assertLessEqual(max(pool["lowTiers"]), 3, "低分时不应该出第 4 档以上")
        self.assertEqual(pool["lowTiers"], [0, 1, 2, 3], "低分时四档都要能出")
        self.assertEqual(pool["rarestTier"], 3, "低分时最大的可生成档位应该最少出现")
        self.assertGreaterEqual(pool["smallShare"], 0.5, "最小的两档应该占一半以上")
        self.assertTrue(pool["richHas4"] and pool["richHas5"], "高分时应该能出第 4、5 档")
        self.assertLessEqual(pool["spacingViolations"], 1, "大档不该在最近 8 颗里重复出现")

        landing = result["landing"]
        self.assertTrue(landing["existed"])
        self.assertTrue(landing["landedOnBall"], "正对着球丢应该预测为落在球上")
        self.assertLessEqual(
            landing["predictedY"], landing["ballTop"],
            "预测落点应该在下面那颗球的顶部之上",
        )

        save = result["save"]
        self.assertEqual(save["version"], 2)
        self.assertEqual(save["drops"], 6)
        self.assertTrue(save["scoreSame"])
        self.assertTrue(save["overSame"])
        self.assertTrue(save["ballsSame"])


@unittest.skipIf(gtn is None, f"无法导入 app（{IMPORT_ERROR}）")
class SuikaRouteTests(unittest.TestCase):
    """页面与 2048 同一套登录判定：未登录 401，登录后能拿到页面外壳。"""

    def setUp(self):
        self.client = gtn.app.test_client()
        self.original_db = svc.db_module

    def tearDown(self):
        svc.db_module = self.original_db

    def test_anonymous_is_rejected(self):
        self.assertEqual(self.client.get("/minigame/suika").status_code, 401)

    def test_logged_in_account_gets_the_shell(self):
        class _Roles:
            def get_user_role_profile(self, identifier):
                return {"role_type": "player"}

        svc.db_module = _Roles()
        with self.client.session_transaction() as session:
            session["user_id"] = 4242
            session["username"] = "suika_probe"
        response = self.client.get("/minigame/suika")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        for needle in ("sk-canvas", "sk-legend-grid", "matter.min.js", "minigame_suika.js",
                       "sk-config", "合成大花花"):
            self.assertIn(needle, body, f"页面缺少 {needle}")


if __name__ == "__main__":
    unittest.main()
