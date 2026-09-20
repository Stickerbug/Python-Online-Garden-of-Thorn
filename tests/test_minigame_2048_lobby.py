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

@unittest.skipIf(gtn is None, f"无法导入 app（{IMPORT_ERROR}）")
class SameAccountInviteTests(unittest.TestCase):
    """同账号多标签页（2048 页）替大厅接受/拒绝邀请（用户第九节）。"""

    def setUp(self):
        self._players = dict(gtn.players)
        self._invites = dict(gtn.invites)
        gtn.players.clear()
        gtn.invites.clear()

    def tearDown(self):
        gtn.players.clear()
        gtn.players.update(self._players)
        gtn.invites.clear()
        gtn.invites.update(self._invites)

    def _scene(self):
        gtn.players['lobby-a'] = {'nickname': 'alice', 'user_id': 11, 'status': 'lobby'}
        gtn.players['lobby-b'] = {'nickname': 'bob', 'user_id': 22, 'status': 'lobby'}
        gtn.players['mini-b'] = {'nickname': 'bob', 'user_id': 22, 'status': 'minigame',
                                 'minigame': '2048'}
        gtn.invites['lobby-a'] = 'lobby-b'

    def test_same_sid_still_works(self):
        self._scene()
        self.assertEqual(gtn.resolve_invite_target_for('lobby-b', 'lobby-a'), 'lobby-b')

    def test_sibling_tab_of_same_account_can_accept(self):
        self._scene()
        self.assertEqual(gtn.resolve_invite_target_for('mini-b', 'lobby-a'), 'mini-b')
        self.assertEqual(gtn.invites['lobby-a'], 'mini-b')   # 邀请改绑到当前会话

    def test_other_account_cannot_accept(self):
        self._scene()
        gtn.players['lobby-c'] = {'nickname': 'carol', 'user_id': 33, 'status': 'lobby'}
        self.assertIsNone(gtn.resolve_invite_target_for('lobby-c', 'lobby-a'))
        self.assertEqual(gtn.invites['lobby-a'], 'lobby-b')

    def test_guests_compare_by_nickname(self):
        gtn.players['g1'] = {'nickname': 'GuestOne', 'status': 'lobby'}
        gtn.players['g2'] = {'nickname': 'guestone', 'status': 'minigame'}
        gtn.invites['host'] = 'g1'
        self.assertEqual(gtn.resolve_invite_target_for('g2', 'host'), 'g2')

    def test_missing_invite_returns_none(self):
        self._scene()
        self.assertIsNone(gtn.resolve_invite_target_for('mini-b', 'nobody'))

if __name__ == "__main__":
    unittest.main()
