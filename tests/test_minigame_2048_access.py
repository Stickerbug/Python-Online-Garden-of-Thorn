# -*- coding: utf-8 -*-
"""休闲花园（小游戏）的进入门槛：**全部登录账号都能进**，未登录一律拒绝。

身份只认服务端会话（user_id / username），不看客户端自报。
"""

from __future__ import annotations

import unittest

import minigame_2048_service as svc


class _FakeDb:
    """站在数据库模块的位置上即可；门槛已不再查角色表。"""

    def get_user_role_profile(self, identifier):
        raise AssertionError("不应再查角色表")


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.original = svc.db_module
        svc.db_module = _FakeDb()

    def tearDown(self):
        svc.db_module = self.original

    def test_any_logged_in_account_passes(self):
        self.assertTrue(svc.can_access_minigame(1, "tester1"))
        self.assertTrue(svc.can_access_minigame(2, "boss"))
        self.assertTrue(svc.can_access_minigame(3, "player"))
        self.assertTrue(svc.can_access_minigame(99, "guest"))
        # 只有 user_id（用户名缺失）会话也算登录过
        self.assertTrue(svc.can_access_minigame(7, ""))
        self.assertTrue(svc.can_access_minigame(None, "old_session"))

    def test_anonymous_is_denied(self):
        self.assertFalse(svc.can_access_minigame(None, ""))
        self.assertFalse(svc.can_access_minigame(0, ""))
        self.assertFalse(svc.can_access_minigame(None, None))

    def test_database_unavailable_fails_closed(self):
        svc.db_module = None
        self.assertFalse(svc.can_access_minigame(1, "tester1"))


if __name__ == "__main__":
    unittest.main()
