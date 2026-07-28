import unittest

from cards import CardInstance
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_runtime_v2 import run_v2_event


class HealLoggingTests(unittest.TestCase):
    @staticmethod
    def _prime_engine(engine):
        engine.player_names = [f"玩家{i + 1}" for i in range(len(engine.players))]
        for player in engine.players:
            player.health = 100
            player.base_max_health = 100
        return engine

    def test_v2_full_health_target_logs_failed_heal_after_card_use(self):
        engine = self._prime_engine(GameEngine2v2())
        card = CardInstance("Rose")
        engine.log_msg(f"{engine.pn(0)}使用了{card.name_cn}")

        result = run_v2_event(
            engine,
            {
                "source_player": 0,
                "target_player": 2,
                "target_player_explicit": True,
                "card": card,
                "choice": {"target_player": 2},
                "current_action": {"choice": {"target_player": 2}},
            },
            {"steps": [{"op": "heal", "target": "target", "amount": 7}]},
        )

        self.assertTrue(result.get("success"))
        self.assertEqual(engine.players[2].health, 100)
        self.assertEqual(engine.log, ["玩家1使用玫瑰，但玩家3未回复生命"])

    def test_v2_heal_still_logs_actual_recovered_health(self):
        engine = self._prime_engine(GameEngine2v2())
        engine.players[2].health = 96
        card = CardInstance("Rose")
        engine.log_msg(f"{engine.pn(0)}使用了{card.name_cn}")

        run_v2_event(
            engine,
            {
                "source_player": 0,
                "target_player": 2,
                "target_player_explicit": True,
                "card": card,
                "choice": {"target_player": 2},
                "current_action": {"choice": {"target_player": 2}},
            },
            {"steps": [{"op": "heal", "target": "target", "amount": 7}]},
        )

        self.assertEqual(engine.players[2].health, 100)
        self.assertEqual(engine.log, ["玩家1使用玫瑰，玩家3回复4H"])

    def test_atomic_heal_logs_failed_heal(self):
        engine = self._prime_engine(GameEngine())
        card = CardInstance("Rose")
        engine.log_msg(f"{engine.pn(0)}使用了{card.name_cn}")

        engine._atomic_heal(0, card, {"target": "self", "amount": 7}, "", None, {})

        self.assertEqual(engine.log, ["玩家1使用玫瑰，但玩家1未回复生命"])


if __name__ == "__main__":
    unittest.main()
