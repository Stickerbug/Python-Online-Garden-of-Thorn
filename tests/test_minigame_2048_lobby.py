# -*- coding: utf-8 -*-
"""休闲花园 2048 与大厅/邀请的接口（用户第九节的一部分）。

覆盖：大厅显示「小游戏中」、默认可被邀请、拒绝对局邀请在**服务端邀请处理处**生效、
正式对局状态优先（小游戏标签页不许把对局中的人改回可邀请）。
"""

from __future__ import annotations

import unittest
from unittest import mock as unittest_mock

import minigame_2048_service as svc

try:
    import app as gtn
except Exception as exc:  # pragma: no cover
    gtn = None
    IMPORT_ERROR = str(exc)
else:
    IMPORT_ERROR = ""


@unittest.skipIf(gtn is None, f"无法导入 app（{IMPORT_ERROR}）")
class LobbyPresenceTests(unittest.TestCase):
    def setUp(self):
        self._players = dict(gtn.players)
        gtn.players.clear()
        self._original_db = svc.db_module

    def tearDown(self):
        gtn.players.clear()
        gtn.players.update(self._players)
        svc.db_module = self._original_db

    def _player(self, **overrides):
        player = {
            'nickname': 'mini_player',
            'status': 'minigame',
            'minigame': '2048',
            'room_id': None,
            'spectating_room': None,
            'user_id': 4242,
            'is_registered_user': True,
            'mode': '1v1',
            'beta_mode': False,
        }
        player.update(overrides)
        gtn.players['sid-mini'] = player
        return player

    def test_zh_status_label(self):
        self.assertEqual(gtn.zh_status('minigame'), '小游戏中')

    def test_lobby_list_contains_minigame_player_with_marker(self):
        self._player()
        rows = [row for row in gtn.get_lobby_list(None) if row['sid'] == 'sid-mini']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['status'], 'minigame')
        self.assertEqual(rows[0]['minigame'], '2048')

    def test_minigame_player_is_invitable_by_default(self):
        self._player()
        self.assertTrue(gtn.player_is_lobby_match_available('sid-mini'))

    def test_player_in_a_match_is_not_available(self):
        self._player(status='in_game', room_id=7)
        self.assertFalse(gtn.player_is_lobby_match_available('sid-mini'))

    def test_decline_preference_is_read_for_minigame_players_only(self):
        player = self._player()
        with unittest_mock.patch.object(
                svc, 'prefs_decline_invites', staticmethod(lambda conn, user_id: True)):
            self.assertTrue(gtn.minigame_2048_player_declines_invites(player))
            # 回到大厅后不再受小游戏偏好约束
            player['status'] = 'lobby'
            self.assertFalse(gtn.minigame_2048_player_declines_invites(player))

    def test_db_failure_falls_back_to_allow(self):
        player = self._player()
        def _boom(conn, user_id):
            raise RuntimeError('db down')

        with unittest_mock.patch.object(svc, 'prefs_decline_invites', staticmethod(_boom)):
            self.assertFalse(gtn.minigame_2048_player_declines_invites(player))

    def test_presence_event_refuses_non_staff(self):
        client = gtn.app.test_client()
        with client.session_transaction() as session:
            session['user_id'] = 4242
            session['username'] = 'regular'
        self._player()

        class _Roles:
            @staticmethod
            def get_user_role_profile(identifier):
                return {'role_type': 'player'}

        svc.db_module = _Roles()
        with client.session_transaction() as session:
            session['username'] = 'regular'
        # 直接调 socket 处理器需要 request 上下文，这里改测判定函数本身
        self.assertFalse(svc.can_access_minigame(4242, 'regular'))


if __name__ == "__main__":
    unittest.main()
