# -*- coding: utf-8 -*-
"""合成大花花的门禁（用户 2026-09-22 拍板）：仅管理员（admin / staff）可进。

普通登录账号：页面与全部接口 403，休闲花园列表里也看不到入口；
管理员（staff）：与原来一样可以进。身份只认服务端角色表，客户端自报无效。
"""

from __future__ import annotations

import unittest
from unittest import mock

import minigame_2048_service as svc

try:
    import app as gtn
except Exception as exc:  # pragma: no cover - 缺依赖时明确跳过
    gtn = None
    IMPORT_ERROR = str(exc)
else:
    IMPORT_ERROR = ""


@unittest.skipIf(gtn is None, f"无法导入 app（{IMPORT_ERROR}）")
class SuikaGateTests(unittest.TestCase):
    def setUp(self):
        self.client = gtn.app.test_client()
        self.original_db = svc.db_module

    def tearDown(self):
        svc.db_module = self.original_db

    def test_anonymous_is_rejected(self):
        self.assertEqual(self.client.get("/minigame/suika").status_code, 401)
        self.assertEqual(self.client.get("/api/minigame/suika/state").status_code, 401)
        self.assertEqual(self.client.get("/api/minigame/suika/leaderboard").status_code, 401)
        self.assertEqual(
            self.client.post("/api/minigame/suika/sync", json={"game_uid": "x"}).status_code, 401)
        self.assertEqual(
            self.client.post("/api/minigame/suika/restart", json={}).status_code, 401)

    def test_regular_account_is_blocked(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 4342
            session["username"] = "plain_player"

        class _Roles:
            def get_user_role_profile(self, identifier):
                return {"role_type": "player"}

        svc.db_module = _Roles()
        with mock.patch.object(gtn, "user_role_type", lambda uid: "none"):
            self.assertEqual(self.client.get("/minigame/suika").status_code, 403)
            self.assertEqual(self.client.get("/api/minigame/suika/state").status_code, 403)
            self.assertEqual(
                self.client.get("/api/minigame/suika/leaderboard").status_code, 403)
            self.assertEqual(
                self.client.post("/api/minigame/suika/restart", json={}).status_code, 403)
            self.assertEqual(
                self.client.post("/api/minigame/suika/sync",
                                 json={"game_uid": "x", "drops": []}).status_code, 403)
            # 休闲花园本身照常能进，但列表里没有合成大花花的入口
            hub = self.client.get("/minigame")
            self.assertEqual(hub.status_code, 200)
            html = hub.get_data(as_text=True)
            self.assertIn("Craft Eternal", html)
            self.assertNotIn("/minigame/suika", html)

    def test_staff_account_is_allowed(self):
        if not getattr(gtn, "DB_AVAILABLE", False):
            self.skipTest("当前环境没有可用数据库")
        with self.client.session_transaction() as session:
            session["user_id"] = 4343
            session["username"] = "probe_staff2"

        class _Roles:
            def get_user_role_profile(self, identifier):
                return {"role_type": "staff"}

        svc.db_module = _Roles()
        with mock.patch.object(gtn, "user_role_type", lambda uid: "staff"):
            self.assertEqual(self.client.get("/minigame/suika").status_code, 200)
            hub = self.client.get("/minigame")
            self.assertEqual(hub.status_code, 200)
            self.assertIn("/minigame/suika", hub.get_data(as_text=True))
            self.assertEqual(self.client.get("/api/minigame/suika/state").status_code, 200)


if __name__ == "__main__":
    unittest.main()
