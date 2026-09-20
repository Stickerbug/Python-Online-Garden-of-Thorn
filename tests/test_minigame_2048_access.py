# -*- coding: utf-8 -*-
"""内测权限（用户用例 5）：只有服务端真实角色 staff / admin 能进，不看客户端自报。"""

from __future__ import annotations

import unittest

import minigame_2048_service as svc


class _FakeDb:
    def __init__(self, roles):
        self.roles = roles

    def get_user_role_profile(self, identifier):
        key = str(identifier)
        role = self.roles.get(key)
        return {"role_type": role} if role else None


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.original = svc.db_module
        svc.db_module = _FakeDb({
            "1": "staff",
            "2": "admin",
            "3": "player",
            "tester1": "staff",
            "boss": "admin",
            "guest": "player",
        })

    def tearDown(self):
        svc.db_module = self.original

    def test_staff_and_admin_pass(self):
        self.assertTrue(svc.can_access_minigame(1, "tester1"))
        self.assertTrue(svc.can_access_minigame(2, "boss"))

    def test_regular_account_and_guest_are_denied(self):
        self.assertFalse(svc.can_access_minigame(3, "player"))
        self.assertFalse(svc.can_access_minigame(99, "guest"))
        self.assertFalse(svc.can_access_minigame(None, ""))

    def test_username_lookup_is_not_trusted_over_role_table(self):
        # 自称 staff 的用户名在角色表里不是 staff → 拒绝
        svc.db_module = _FakeDb({"liar": "player"})
        self.assertFalse(svc.can_access_minigame(5, "liar"))

    def test_database_error_fails_closed(self):
        class _Broken:
            def get_user_role_profile(self, identifier):
                raise RuntimeError("db down")

        svc.db_module = _Broken()
        self.assertFalse(svc.can_access_minigame(1, "tester1"))


if __name__ == "__main__":
    unittest.main()
