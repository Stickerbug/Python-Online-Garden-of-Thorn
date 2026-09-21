# -*- coding: utf-8 -*-
"""前后端规则一致性（用户用例 4）：Node 跑客户端核心，Python 跑服务端核心，逐位对拍。"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import unittest

import minigame_2048 as g

ROOT = pathlib.Path(__file__).resolve().parents[1]
CORE_JS = ROOT / "static" / "js" / "minigame_2048_core.js"

CASES = [
    (1, "lurd"),
    (424242, "lurdllurdu"),
    (987654321, "udlr" * 8),
    (20240920, "l" * 12 + "u" * 6 + "r" * 9),
    (77, "dlur" * 12),
    # 规则 v2：5×5 + 合并失败——这些长操作串里必然出现合并与失败分支
    (31337, "l" * 6 + "u" * 4 + "r" * 3 + "d" * 5 + "l" * 4),
    (20260921, "lllluuuurrrrdddd" * 3),
    (5, "uldr" * 20),
    (24680, "ldru" * 32),
]


def python_side(cases):
    out = []
    for seed, ops in cases:
        result = g.replay(seed, ops)
        out.append({
            "seed": seed, "ops": ops, "cells": result["cells"], "score": result["score"],
            "rng": result["rng_state"], "maxTile": result["max_tile"],
            "gameOver": result["game_over"],
        })
    return out


NODE_SCRIPT = """
import { pathToFileURL } from 'node:url';
const { replay } = await import(pathToFileURL(process.argv[1]).href);
const cases = JSON.parse(process.argv[2]);
const out = cases.map(([seed, ops]) => {
  const r = replay(seed, ops);
  return { seed, ops, cells: r.cells, score: r.score, rng: r.rngState, maxTile: r.maxTile, gameOver: r.gameOver };
});
console.log(JSON.stringify(out));
"""


class ParityTests(unittest.TestCase):
    def test_client_and_server_agree_on_every_case(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("没有 node：跳过前后端对拍（在 CI/开发机上有 node 时会跑）")
        payload = json.dumps([[seed, ops] for seed, ops in CASES])
        completed = subprocess.run(
            [node, "--input-type=module", "-e", NODE_SCRIPT, str(CORE_JS), payload],
            capture_output=True, text=True, timeout=120, check=True,
        )
        js_side = json.loads(completed.stdout.strip().splitlines()[-1])
        py_side = python_side(CASES)
        self.assertEqual(len(js_side), len(py_side))
        for expected, actual in zip(py_side, js_side):
            self.assertEqual(actual["cells"], expected["cells"], expected["ops"])
            self.assertEqual(actual["score"], expected["score"], expected["ops"])
            self.assertEqual(actual["rng"], expected["rng"], expected["ops"])
            self.assertEqual(actual["maxTile"], expected["maxTile"], expected["ops"])
            self.assertEqual(actual["gameOver"], expected["gameOver"], expected["ops"])


if __name__ == "__main__":
    unittest.main()
