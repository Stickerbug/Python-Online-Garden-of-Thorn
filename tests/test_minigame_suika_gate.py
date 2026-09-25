# -*- coding: utf-8 -*-
"""合成大花花对全员开放（2026-09-23 起开放公测；更早的「仅管理员」门槛已移除）。

匿名：页面与全部接口 401（与 2048 同口径，登录是唯一门槛）；
普通登录账号：页面、接口与休闲花园入口全部可用。
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

    def test_anonymous_page_ok_apis_rejected(self):
        """游客可直接进页面（2026-09-25）；数据接口仍要登录。"""
        self.assertEqual(self.client.get("/minigame/suika").status_code, 200)
        self.assertEqual(self.client.get("/api/minigame/suika/state").status_code, 401)
        self.assertEqual(self.client.get("/api/minigame/suika/leaderboard").status_code, 401)
        self.assertEqual(
            self.client.post("/api/minigame/suika/sync", json={"game_uid": "x"}).status_code, 401)
        self.assertEqual(
            self.client.post("/api/minigame/suika/restart", json={}).status_code, 401)

    def test_regular_account_can_enter(self):
        if not getattr(gtn, "DB_AVAILABLE", False):
            self.skipTest("当前环境没有可用数据库")
        with self.client.session_transaction() as session:
            session["user_id"] = 4342
            session["username"] = "plain_player"

        class _Roles:
            def get_user_role_profile(self, identifier):
                return {"role_type": "player"}

        svc.db_module = _Roles()
        with mock.patch.object(gtn, "user_role_type", lambda uid: "player"):
            self.assertEqual(self.client.get("/minigame/suika").status_code, 200)
            self.assertEqual(self.client.get("/api/minigame/suika/state").status_code, 200)
            self.assertEqual(
                self.client.get("/api/minigame/suika/leaderboard").status_code, 200)
            self.assertEqual(
                self.client.post("/api/minigame/suika/restart", json={}).status_code, 200)
            # 休闲花园列表里普通账号也能看到合成大花花的入口
            hub = self.client.get("/minigame")
            self.assertEqual(hub.status_code, 200)
            html = hub.get_data(as_text=True)
            self.assertIn("Craft Eternal", html)
            self.assertIn("/minigame/suika", html)


if __name__ == "__main__":
    unittest.main()
