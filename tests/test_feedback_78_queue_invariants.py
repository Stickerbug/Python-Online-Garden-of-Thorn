"""反馈 #78 的独立不变量检查（补 tests/test_feedback_78_75_engine.py 未覆盖的角度）。

该文件只断言"队列不残留 / 不迟到结算"这类不变量，不重复断言实现细节：
1. 报错场景（空手、10E、裂变10 松果）打完后，``bio_auto_play_queue`` 必须清空；
2. 之后任何一次普通结算（``_after_response_result``）都不应把剩余复制"迟到"打出；
3. 复制实例不能同时出现在两个区域，手牌不得超过上限。
"""

import unittest
from pathlib import Path

from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
ARCTIC_PACKAGE = ROOT / "mods" / "Arctic Cards Addition.gtnmod"
PINECONE_COPY_MODIFIER = "arctic_pinecone_copy"
ENGINE_CLASSES = (GameEngine, GameEngine2v2)


def _load_cards(path):
    mod = load_mod(str(path))
    if mod.errors:
        raise AssertionError(mod.errors)
    return {card.id: card.to_card_def() for card in mod.cards}


def _prepare_engine(engine_class):
    engine = engine_class()
    engine.phase = "action"
    engine.current_player = 0
    for player in engine.players:
        player.hand = []
        player.deck = []
        player.discard = []
        player.exile = []
        player.equipment = []
        player.elixir = 50
        player.magic = 50
        player.health = 100
        player.max_health = 100
        player.armor = 0
        player.custom_statuses = {}
        player.custom_vars = {}
    return engine


def _enemy_id(engine_class):
    return 2 if engine_class is GameEngine2v2 else 1


def _fission_pinecone(level):
    pinecone = CardInstance("Pinecone")
    pinecone.fission_level = level
    pinecone.fission_count = level - 1
    return pinecone


def _play(engine, engine_class, card, target_id):
    choice = {
        "target_player": target_id,
        "target_player_id": target_id,
        "target_id": target_id,
    }
    if engine_class is GameEngine2v2:
        return engine.play_card(0, card.instance_id, target_id, choice)
    return engine.play_card(0, card.instance_id, choice)


class QueueInvariantTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cards = _load_cards(ARCTIC_PACKAGE)

    def setUp(self):
        self.previous_defs = {card_id: CARD_DEFS.get(card_id) for card_id in self.cards}
        CARD_DEFS.update(self.cards)

    def tearDown(self):
        for card_id, previous in self.previous_defs.items():
            if previous is None:
                CARD_DEFS.pop(card_id, None)
            else:
                CARD_DEFS[card_id] = previous

    @staticmethod
    def _copy_cards(cards):
        return [
            card
            for card in cards
            if PINECONE_COPY_MODIFIER in (getattr(card, "setup_modifiers", set()) or set())
        ]

    def _zones(self, player):
        return {
            "hand": list(player.hand),
            "deck": list(player.deck),
            "discard": list(player.discard),
            "exile": list(player.exile),
        }

    def test_ten_energy_repro_leaves_no_queue_residue(self):
        for engine_class in ENGINE_CLASSES:
            with self.subTest(engine=engine_class.__name__):
                engine = _prepare_engine(engine_class)
                pinecone = _fission_pinecone(10)
                engine.players[0].hand = [pinecone]
                engine.players[0].elixir = 10

                result = _play(engine, engine_class, pinecone, _enemy_id(engine_class))
                self.assertTrue(result.get("success"), result)

                player = engine.players[0]
                queue = engine.custom_vars.get("bio_auto_play_queue")
                self.assertFalse(queue, f"队列应清空，实际残留 {queue!r}")

                zones = self._zones(player)
                copies = {
                    name: self._copy_cards(cards) for name, cards in zones.items()
                }
                total = sum(len(items) for items in copies.values())
                self.assertEqual(10, total, copies)

                seen = {}
                for name, items in copies.items():
                    for card in items:
                        self.assertNotIn(
                            card.instance_id,
                            seen,
                            f"实例 {card.instance_id} 同时出现在 {seen.get(card.instance_id)} 与 {name}",
                        )
                        seen[card.instance_id] = name

                self.assertLessEqual(len(player.hand), player.hand_limit())

    def test_later_resolution_does_not_replay_leftover_copies(self):
        for engine_class in ENGINE_CLASSES:
            with self.subTest(engine=engine_class.__name__):
                engine = _prepare_engine(engine_class)
                pinecone = _fission_pinecone(10)
                engine.players[0].hand = [pinecone]
                engine.players[0].elixir = 10

                result = _play(engine, engine_class, pinecone, _enemy_id(engine_class))
                self.assertTrue(result.get("success"), result)

                player = engine.players[0]
                exile_before = len(self._copy_cards(player.exile))
                hand_before = [card.instance_id for card in player.hand]

                # 普通结算钩子不应把"上一张牌留下的复制"迟到打出。
                engine._after_response_result(0, {"success": True})

                self.assertEqual(
                    exile_before,
                    len(self._copy_cards(player.exile)),
                    "残留复制在后续结算中被迟到打出",
                )
                self.assertEqual(
                    hand_before,
                    [card.instance_id for card in player.hand],
                    "后续结算改动了手牌",
                )


if __name__ == "__main__":
    unittest.main()
