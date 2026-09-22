# -*- coding: utf-8 -*-
"""休闲花园 · 大厅联动（用户 2026-09-22 的四条需求）。

1. 小游戏注册表是唯一白名单，以后加小游戏不用改 presence / 邀请；
2. 在大厅里，正在玩小游戏的人保持"离开大厅时"的位置（观战者仍然最后）；
3. 从大厅进休闲花园，返回时回到大厅（而不是停在主页），来源走白名单、防开放重定向；
4. 大厅页脚按钮顺序：返回主页、设置、休闲花园。
"""

from __future__ import annotations

import unittest
from unittest import mock

import minigame_2048_service as svc
import minigame_registry as reg

try:
    import app as gtn
except Exception as exc:  # pragma: no cover - 缺依赖时明确跳过
    gtn = None
    IMPORT_ERROR = str(exc)
else:
    IMPORT_ERROR = ""


class RegistryTests(unittest.TestCase):
    def test_registry_whitelist(self):
        self.assertTrue(reg.is_minigame('2048'))
        self.assertTrue(reg.is_minigame('suika'))
        self.assertFalse(reg.is_minigame('minecraft'))
        self.assertFalse(reg.is_minigame(''))
        self.assertTrue(reg.invite_ready('suika'))

    def test_back_href_only_whitelisted(self):
        self.assertEqual(reg.minigame_hub_back_href('lobby'), '/?enter_lobby=1')
        self.assertEqual(reg.minigame_hub_back_href('home'), '/')
        self.assertEqual(reg.minigame_hub_back_href('https://evil.example'), '/')
        self.assertEqual(reg.minigame_hub_back_href(None), '/')

    def test_from_param_is_whitelisted(self):
        self.assertEqual(reg.normalize_from('lobby'), 'lobby')
        self.assertEqual(reg.normalize_from('HOME'), 'home')
        self.assertEqual(reg.normalize_from('//evil.example'), '')
        self.assertEqual(reg.with_from('/minigame/suika', 'lobby'), '/minigame/suika?from=lobby')
        self.assertEqual(reg.with_from('/minigame/suika', 'evil'), '/minigame/suika')


@unittest.skipIf(gtn is None, f"无法导入 app（{IMPORT_ERROR}）")
class LobbyPositionTests(unittest.TestCase):
    """小游戏里的人在大厅列表里应该留在原位。"""

    def setUp(self):
        self._players = dict(gtn.players)

    def tearDown(self):
        gtn.players.clear()
        gtn.players.update(self._players)

    @staticmethod
    def _player(nick, status, **extra):
        data = {
            'nickname': nick,
            'status': status,
            'user_id': extra.pop('user_id', 0),
            'beta_mode': False,
            'room_id': None,
        }
        data.update(extra)
        return data

    def test_minigame_player_keeps_lobby_order(self):
        gtn.players.clear()
        gtn.players['sid-a'] = self._player('Alice', 'lobby')
        gtn.players['sid-b'] = self._player('Bob', 'minigame', minigame='suika')
        gtn.players['sid-c'] = self._player('Cara', 'lobby')
        gtn.players['sid-d'] = self._player('Dave', 'spectating')
        names = [item['nickname'] for item in gtn.get_lobby_list()]
        # 名字排序：Alice / Bob / Cara，观战者 Dave 仍然最后
        self.assertEqual(names, ['Alice', 'Bob', 'Cara', 'Dave'])


@unittest.skipIf(gtn is None, f"无法导入 app（{IMPORT_ERROR}）")
class LobbyRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = gtn.app.test_client()
        self.original_db = svc.db_module

    def tearDown(self):
        svc.db_module = self.original_db
        if getattr(self, 'role_patch', None):
            self.role_patch.stop()
            self.role_patch = None

    def _login(self):
        class _Roles:
            def get_user_role_profile(self, identifier):
                return {"role_type": "player"}

        svc.db_module = _Roles()
        # 本文件测的是"链接把 from 带回去"的管线；合成大花花的入口/页面现在仅
        # 管理员可见（_minigame_suika_guard），所以把角色表指成 staff 才覆盖得到 suika。
        self.role_patch = mock.patch.object(gtn, 'user_role_type', lambda uid: 'staff')
        self.role_patch.start()
        with self.client.session_transaction() as session:
            session["user_id"] = 4242
            session["username"] = "lobby_probe"

    def test_hub_keeps_from_and_returns_to_lobby(self):
        self._login()
        body = self.client.get('/minigame?from=lobby').get_data(as_text=True)
        self.assertIn('href="/?enter_lobby=1"', body)
        self.assertIn('/minigame/suika?from=lobby', body)
        self.assertIn('/minigame/2048?from=lobby', body)

    def test_hub_ignores_bad_from(self):
        self._login()
        body = self.client.get('/minigame?from=https://evil.example').get_data(as_text=True)
        self.assertIn('href="/"', body)
        self.assertNotIn('evil.example', body)

    def test_lobby_footer_button_order(self):
        self._login()
        body = self.client.get('/').get_data(as_text=True)
        back = body.find('id="btn-lobby-back"')
        settings = body.find('id="btn-lobby-settings"')
        leisure = body.find('id="btn-lobby-leisure"')
        self.assertGreater(back, -1, '大厅缺少"返回主页"按钮')
        self.assertGreater(settings, -1, '大厅缺少"设置"按钮')
        self.assertGreater(leisure, -1, '大厅缺少"休闲花园"按钮')
        self.assertLess(back, settings)
        self.assertLess(settings, leisure, '休闲花园按钮应该在设置按钮右边')

    def test_page_links_carry_from(self):
        self._login()
        suika = self.client.get('/minigame/suika?from=lobby').get_data(as_text=True)
        self.assertIn('href="/minigame?from=lobby"', suika)
        page2048 = self.client.get('/minigame/2048?from=lobby').get_data(as_text=True)
        self.assertIn('href="/minigame?from=lobby"', page2048)


if __name__ == "__main__":
    unittest.main()
