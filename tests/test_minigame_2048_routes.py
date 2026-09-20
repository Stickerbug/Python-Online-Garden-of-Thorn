# -*- coding: utf-8 -*-
"""2048 路由级权限（用户用例 5）：直达 URL / 接口 / 伪造身份都进不去。"""

from __future__ import annotations

import unittest

import minigame_2048_service as svc

try:
    import app as gtn
except Exception as exc:  # pragma: no cover - 缺依赖时明确跳过
    gtn = None
    IMPORT_ERROR = str(exc)
else:
    IMPORT_ERROR = ""


@unittest.skipIf(gtn is None, f"无法导入 app（{IMPORT_ERROR}）")
class RouteAccessTests(unittest.TestCase):
    def setUp(self):
        self.client = gtn.app.test_client()
        self.original_db = svc.db_module

    def tearDown(self):
        svc.db_module = self.original_db

    def test_anonymous_is_rejected(self):
        self.assertEqual(self.client.get("/minigame/2048").status_code, 401)
        self.assertEqual(self.client.get("/api/minigame/2048/state").status_code, 401)
        self.assertEqual(self.client.get("/api/minigame/2048/leaderboard").status_code, 401)
        post = self.client.post("/api/minigame/2048/sync", json={"ops": "lurd"})
        self.assertEqual(post.status_code, 401)

    def test_regular_account_is_forbidden_even_with_direct_url(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 4242
            session["username"] = "regular_player"

        class _Roles:
            def get_user_role_profile(self, identifier):
                return {"role_type": "player"}

        svc.db_module = _Roles()
        for path in ("/minigame/2048", "/api/minigame/2048/state",
                     "/api/minigame/2048/leaderboard", "/api/minigame/2048/prefs"):
            self.assertEqual(self.client.get(path).status_code, 403, path)
        self.assertEqual(
            self.client.post("/api/minigame/2048/restart", json={}).status_code, 403)
        denied = self.client.get("/api/minigame/2048/state").get_json()
        self.assertIn("内测", denied.get("error", ""))

    def test_staff_can_use_the_api(self):
        if not getattr(gtn, "DB_AVAILABLE", False):
            self.skipTest("当前环境没有可用数据库")
        with self.client.session_transaction() as session:
            session["user_id"] = 4243
            session["username"] = "probe_staff"

        class _Roles:
            def get_user_role_profile(self, identifier):
                return {"role_type": "staff"}

        svc.db_module = _Roles()
        self.assertEqual(self.client.get("/minigame/2048").status_code, 200)
        state = self.client.get("/api/minigame/2048/state")
        self.assertEqual(state.status_code, 200)
        payload = state.get_json()
        self.assertEqual(len(payload["rules"]["rarity_table"]), 17)
        sync = self.client.post("/api/minigame/2048/sync",
                                json={"game_uid": payload["game"]["game_uid"],
                                      "from_index": 0, "ops": "lurd"})
        self.assertEqual(sync.status_code, 200)
        self.assertEqual(sync.get_json()["status"], "ok")

    def test_lobby_entry_button_only_renders_for_staff(self):
        """大厅里的「休闲花园 · 2048」入口只给通过内测门槛的账号渲染。"""

        class _Roles:
            @staticmethod
            def get_user_role_profile(identifier):
                return {"role_type": "staff" if str(identifier) == "entry_staff" else "player"}

        svc.db_module = _Roles()
        with self.client.session_transaction() as session:
            session["user_id"] = 9001
            session["username"] = "entry_player"
        html = self.client.get("/").data.decode("utf-8", "replace")
        self.assertNotIn("btn-minigame-2048", html)
        with self.client.session_transaction() as session:
            session["user_id"] = 9002
            session["username"] = "entry_staff"
        html = self.client.get("/").data.decode("utf-8", "replace")
        self.assertIn("btn-minigame-2048", html)


if __name__ == "__main__":
    unittest.main()
