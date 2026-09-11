"""反馈中心 #78 的回归测试（多人引擎）。

像「松果」这种"造成伤害就复制并追加打出"的牌，多张复制必须逐张结算
（复制 → 打出 → 再复制下一张）。旧实现只把复制排队、等整张牌结算完再
统一打出，复制会先全部堆进手牌撑爆手牌上限（爆牌）。
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


def _load_mod_cards(*paths):
    cards = {}
    for path in paths:
        mod = load_mod(str(path))
        if mod.errors:
            raise AssertionError(mod.errors)
        for card in mod.cards:
            cards[card.id] = card.to_card_def()
    return cards


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


def _play_card(engine, engine_class, player_id, card, target_id, extra_choice=None):
    choice = {
        "target_player": target_id,
        "target_player_id": target_id,
        "target_id": target_id,
    }
    if extra_choice:
        choice.update(extra_choice)
    if engine_class is GameEngine2v2:
        return engine.play_card(player_id, card.instance_id, target_id, choice)
    return engine.play_card(player_id, card.instance_id, choice)


class PineconeAutoPlayOrderTests(unittest.TestCase):
    """反馈 #78：追加打出的复制要逐张结算，不再先堆满手牌。"""

    @classmethod
    def setUpClass(cls):
        cls.cards = _load_mod_cards(ARCTIC_PACKAGE)

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
            if PINECONE_COPY_MODIFIER
            in (getattr(card, "setup_modifiers", set()) or set())
        ]

    @staticmethod
    def _fission_pinecone(level):
        pinecone = CardInstance("Pinecone")
        pinecone.fission_level = level
        pinecone.fission_count = level - 1
        return pinecone

    def _trace_engine(self, engine, events):
        """记录"复制"与"打出"的先后顺序，用来断言逐张结算。"""
        original_copy = engine._atomic_copy_card_instance
        original_play = engine.play_card

        def copy_spy(player_id, card, params, log, choice, context, _original=original_copy):
            result = _original(player_id, card, params, log, choice, context)
            if params.get("setup_modifiers"):
                created = engine._find_card_by_instance_id(
                    getattr(engine, "_last_created_card_instance_id", None)
                )
                events.append(("copy", getattr(created, "instance_id", None)))
            return result

        def play_spy(*args, **kwargs):
            card_instance_id = args[1] if len(args) > 1 else kwargs.get("card_instance_id")
            events.append(("play", card_instance_id))
            return original_play(*args, **kwargs)

        engine._atomic_copy_card_instance = copy_spy
        engine.play_card = play_spy

    def test_fission_copies_resolve_one_by_one_with_enough_energy(self):
        for engine_class in ENGINE_CLASSES:
            with self.subTest(engine=engine_class.__name__):
                engine = _prepare_engine(engine_class)
                events = []
                queue_depths = []
                self._trace_engine(engine, events)
                original_queue = engine._bio_queue_auto_play

                def queue_spy(player_id, card, choice, no_cost=False, source="", _original=original_queue):
                    _original(player_id, card, choice, no_cost=no_cost, source=source)
                    queue_depths.append(
                        len(engine.custom_vars.get("bio_auto_play_queue") or [])
                    )

                engine._bio_queue_auto_play = queue_spy

                pinecone = self._fission_pinecone(10)
                engine.players[0].hand = [pinecone]
                engine.players[0].elixir = 100

                result = _play_card(engine, engine_class, 0, pinecone, _enemy_id(engine_class))

                self.assertTrue(result.get("success"), result)
                player = engine.players[0]
                # 每次复制之后紧接着打出这张复制，队列同时最多留 1 张
                copy_events = [event for event in events if event[0] == "copy"]
                self.assertEqual(10, len(copy_events))
                for index, event in enumerate(events):
                    if event[0] != "copy":
                        continue
                    self.assertEqual("play", events[index + 1][0], events)
                    self.assertEqual(event[1], events[index + 1][1], events)
                self.assertLessEqual(max(queue_depths), 1, queue_depths)
                # 复制全部打出：没有一张留在手牌，也没有一张被爆牌弃掉
                self.assertEqual([], self._copy_cards(player.hand))
                self.assertEqual([], self._copy_cards(player.discard))
                self.assertEqual(10, len(self._copy_cards(player.exile)))
                self.assertFalse(engine.custom_vars.get("bio_auto_play_queue"))

    def test_reported_ten_energy_play_does_not_burn_or_duplicate_copies(self):
        for engine_class in ENGINE_CLASSES:
            with self.subTest(engine=engine_class.__name__):
                engine = _prepare_engine(engine_class)
                pinecone = self._fission_pinecone(10)
                engine.players[0].hand = [pinecone]
                engine.players[0].elixir = 10

                result = _play_card(engine, engine_class, 0, pinecone, _enemy_id(engine_class))

                self.assertTrue(result.get("success"), result)
                player = engine.players[0]
                played = self._copy_cards(player.exile)
                leftover = self._copy_cards(player.hand)
                burned = self._copy_cards(player.discard)
                # 10 次伤害 = 10 张复制；付得起的当场打出，剩下的留在手牌
                self.assertGreaterEqual(len(played), 1)
                self.assertEqual(10, len(played) + len(leftover) + len(burned))
                self.assertLessEqual(len(leftover), player.hand_limit())
                # 手牌溢出不会把同一张实例重复塞进弃牌堆
                discard_ids = [card.instance_id for card in player.discard]
                self.assertEqual(len(discard_ids), len(set(discard_ids)))



if __name__ == "__main__":
    unittest.main()
