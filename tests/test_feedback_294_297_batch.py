# -*- coding: utf-8 -*-
"""GS-296 / GS-297：模组窗口取消语义 + 电池物理伤害触发。

GS-296：护身符这类「按钮表里没有 cancel」的模组窗口，超时/断线/回合超时
统一走 button='cancel' 兜底——旧校验直接抛 V2RuntimeError，自动结束回合
随之失败并每 tick 重试（invalid v2 ui button 刷屏），玩家被永久卡死。
GS-297（设计拍板 2026-10-01）：电池改为**任意来源的物理伤害**都触发电击
（含盐反伤、众生平等自伤等），攻击牌命中路径不变；电击本身是魔法伤害，
不会互相连锁。
"""

import unittest

import app  # noqa: F401  装载模组
from game_engine import CardInstance, GameEngine
from mod_runtime_v2 import V2RuntimeError, validate_v2_ui_response


def target_choice(player_id):
    return {'target_player': player_id, 'target_player_id': player_id, 'target_id': player_id}


class V2UiCancelSemanticsTests(unittest.TestCase):
    def component(self):
        return {
            'type': 'modal',
            'controls': [
                {'id': 'cards', 'type': 'multi_card_picker',
                 'target': 'self', 'zone': 'hand', 'min_select': 2, 'max_select': 2},
            ],
            'buttons': [{'id': 'confirm', 'role': 'confirm'}],
        }

    def test_cancel_button_always_accepted(self):
        """未声明 cancel 按钮时，系统级 cancel 不再抛 invalid v2 ui button。"""
        clean = validate_v2_ui_response(None, {}, self.component(), {'button': 'cancel', 'values': {}})
        self.assertEqual('cancel', clean.get('button'))
        self.assertTrue(clean.get('cancelled'))

    def test_cancel_skips_value_validation(self):
        """取消意图不做取值校验（空选择不满足 min_select 也不该报错）。"""
        clean = validate_v2_ui_response(None, {}, self.component(), {'button': 'cancel'})
        self.assertTrue(clean.get('cancelled'))

    def test_declared_cancel_role_button_cancels(self):
        comp = self.component()
        comp['buttons'] = [{'id': 'quit', 'role': 'cancel'}]
        clean = validate_v2_ui_response(None, {}, comp, {'button': 'quit', 'values': {}})
        self.assertTrue(clean.get('cancelled'))

    def test_unknown_button_still_rejected(self):
        with self.assertRaises(V2RuntimeError):
            validate_v2_ui_response(None, {}, self.component(), {'button': 'hack', 'values': {}})

    def test_amulet_modal_system_cancel_end_to_end(self):
        engine = GameEngine()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.max_health = 100
            player.elixir = 20
            player.magic = 20
            player.hand = []
            player.deck = []
            player.discard = []
        amulet = CardInstance('Amulet')
        engine.players[0].hand = [amulet, CardInstance('Basic'), CardInstance('Rose')]
        engine.play_card(0, amulet.instance_id, target_choice(1))
        pending = getattr(engine, 'pending_v2_ui', None)
        self.assertIsNotNone(pending)
        result = engine.handle_v2_ui_response(
            0, pending['request_id'], {'button': 'cancel', 'values': {}},
        )
        self.assertTrue(result.get('success'))
        self.assertTrue(result.get('cancelled'))
        self.assertIsNone(engine.pending_v2_ui)
        remaining = [c.card_def.name_cn for c in engine.players[0].hand]
        self.assertEqual(['基本', '玫瑰'], remaining)


class BatteryPhysicalDamageTests(unittest.TestCase):
    def build_engine(self):
        engine = GameEngine()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.max_health = 100
            player.elixir = 20
            player.magic = 20
            player.hand = []
            player.deck = []
            player.discard = []
        return engine

    def equip_battery(self, engine, player_id):
        battery = CardInstance('Battery')
        engine.players[player_id].hand = [battery]
        engine.current_player = player_id
        engine.play_card(player_id, battery.instance_id, target_choice(player_id))
        if getattr(engine, 'pending_response', None):
            engine.handle_response(1 - player_id, None)
        engine.current_player = 0

    def test_salt_reflection_triggers_battery(self):
        """GS-297：攻击方持有电池，目标用盐反制——盐的物理反伤触发电池回击。"""
        engine = self.build_engine()
        self.equip_battery(engine, 0)
        salt = CardInstance('Salt')
        attack = CardInstance('Basic')
        engine.players[0].hand = [attack]
        engine.players[1].hand = [salt]
        engine.play_card(0, attack.instance_id, target_choice(1))
        if getattr(engine, 'pending_response', None):
            engine.handle_response(1, salt.instance_id)
        # 基本8D + 电池电击3（盐的物理反伤打到电池持有者触发）= 共11伤
        self.assertEqual(11, 100 - engine.players[1].health)

    def test_magic_direct_damage_does_not_trigger_battery(self):
        engine = self.build_engine()
        self.equip_battery(engine, 0)
        engine._deal_direct_damage(0, 7, '测试魔法', 1, damage_type='magic')
        self.assertEqual(93, engine.players[0].health)
        self.assertEqual(100, engine.players[1].health)

    def test_physical_direct_damage_triggers_battery(self):
        engine = self.build_engine()
        self.equip_battery(engine, 0)
        engine._deal_direct_damage(0, 7, '测试物理', 1, damage_type='physical')
        self.assertEqual(93, engine.players[0].health)
        self.assertEqual(97, engine.players[1].health)

    def test_equal_suffering_self_damage_zaps_self(self):
        """众生平等自伤（攻击路径，attacker=自己）→ 电池电自己。"""
        engine = self.build_engine()
        self.equip_battery(engine, 0)
        engine.opening_event_picks = ['12', '1']
        engine._apply_equal_suffering_turn_end(0)
        # 自伤5 + 电池电自己3
        self.assertEqual(92, engine.players[0].health)


if __name__ == '__main__':
    unittest.main()
