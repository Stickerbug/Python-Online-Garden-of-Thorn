# -*- coding: utf-8 -*-
"""9.24 修正：自己装在自己身上的螫针（effect_target=自己）也能在自己回E时施加超载。"""

import unittest

import app  # noqa: F401  装载模组：Pincer 的声明式事件（on_elixir_recovery）依赖 CARD_DEFS
import game_engine as ge


def _make_engine():
    engine = ge.GameEngine()
    engine.players = [ge.PlayerState(i) for i in range(2)]
    engine.round_num = 2
    return engine


class PincerSelfOverloadTests(unittest.TestCase):
    @staticmethod
    def _place_pincer(engine, owner_id, effect_target):
        card = ge.CardInstance('Pincer')
        card.effect_target = effect_target
        card.turns_equipped = 0
        card.uses_this_turn = 0
        engine.players[owner_id].equipment.append(card)
        return card

    def _place_self_pincer(self, engine, player_id):
        return self._place_pincer(engine, player_id, player_id)

    @staticmethod
    def _run_turn_start_capturing_logs(engine, player_id):
        logs = []
        original = engine.log_msg

        def capture(message, *args, **kwargs):
            logs.append(str(message))

        engine.log_msg = capture
        try:
            engine._apply_turn_start_effects(player_id)
        finally:
            engine.log_msg = original
        return logs

    def test_self_equipped_pincer_overloads_self_on_recovery(self):
        # 超载在回E时施加、同回合开始立即扣E并清层——用日志判定是否施加过。
        engine = _make_engine()
        self._place_self_pincer(engine, 0)
        alice = engine.players[0]
        alice.overload = 0
        alice.elixir = 0
        logs = self._run_turn_start_capturing_logs(engine, 0)
        self.assertTrue(any('超载' in line for line in logs), '自装螫针应在自己回合回E时对自己施加超载')

    def test_enemy_equipped_pincer_still_overloads_target(self):
        engine = _make_engine()
        self._place_pincer(engine, 1, 0)
        alice = engine.players[0]
        alice.overload = 0
        alice.elixir = 0
        logs = self._run_turn_start_capturing_logs(engine, 0)
        self.assertTrue(any('超载' in line for line in logs), '敌方装在Alice身上的螫针仍应施加超载')

    def test_pincer_on_third_party_not_overload_self(self):
        engine = _make_engine()
        self._place_pincer(engine, 0, 1)
        alice = engine.players[0]
        alice.overload = 0
        alice.elixir = 0
        logs = self._run_turn_start_capturing_logs(engine, 0)
        self.assertFalse(any('超载' in line for line in logs), 'effect_target 指向他人的螫针不应施加给自己')


if __name__ == '__main__':
    unittest.main()
