"""反馈中心 #75 的回归测试（多人引擎）。

磁铁跨玩家偷取唯一牌时，若自己已有同名唯一牌，按既有唯一牌规则处理：
保留偷来的牌，并向牌组加入 1 张虚空；自己没持有同名唯一牌时正常获得。
"""

import unittest
from pathlib import Path

from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
DESERT_PACKAGE = ROOT / "mods" / "Desert Cards Addition.gtnmod"
VANILLA_PACKAGE = ROOT / "mods" / "Vanilla Cards.gtnmod"
VOID_PACKAGE = ROOT / "mods" / "Void Card Addition.gtnmod"

UNIQUE_ID = "Bandage"
NORMAL_ID = "Basic"
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


class MagnetUniqueStealTests(unittest.TestCase):
    """反馈 #75：磁铁偷唯一牌的唯一牌惩罚。"""

    @classmethod
    def setUpClass(cls):
        cls.cards = _load_mod_cards(DESERT_PACKAGE, VANILLA_PACKAGE, VOID_PACKAGE)

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
    def _steal(engine, engine_class, stolen_id, own_duplicate):
        magnet = CardInstance("Magnet")
        engine.players[0].hand = [CardInstance(stolen_id)] if own_duplicate else []
        engine.players[0].hand.append(magnet)
        stolen = CardInstance(stolen_id)
        enemy_id = _enemy_id(engine_class)
        engine.players[enemy_id].hand = [stolen]

        result = _play_card(engine, engine_class, 0, magnet, enemy_id)
        if not result.get("success"):
            return result, stolen, enemy_id
        if result.get("needs_choice"):
            engine.resolve_choice(0, {"target_instance_id": stolen.instance_id})
        return result, stolen, enemy_id

    def test_stealing_a_unique_card_you_already_own_adds_one_void(self):
        for engine_class in ENGINE_CLASSES:
            with self.subTest(engine=engine_class.__name__):
                engine = _prepare_engine(engine_class)
                result, stolen, enemy_id = self._steal(
                    engine, engine_class, UNIQUE_ID, own_duplicate=True
                )

                self.assertTrue(result.get("success"), result)
                player = engine.players[0]
                void_id = engine._void_resolve_card_def_id("void:void")
                self.assertIsNotNone(void_id)
                # 偷来的牌保留在自己手上（和强制复制唯一牌一样），另外加 1 张虚空
                self.assertEqual(2, sum(card.def_id == UNIQUE_ID for card in player.hand))
                self.assertEqual([void_id], [card.def_id for card in player.deck])
                self.assertNotIn(stolen, engine.players[enemy_id].hand)

    def test_stealing_a_unique_card_you_do_not_own_has_no_penalty(self):
        for engine_class in ENGINE_CLASSES:
            with self.subTest(engine=engine_class.__name__):
                engine = _prepare_engine(engine_class)
                result, stolen, enemy_id = self._steal(
                    engine, engine_class, UNIQUE_ID, own_duplicate=False
                )

                self.assertTrue(result.get("success"), result)
                player = engine.players[0]
                self.assertEqual([stolen], [card for card in player.hand if card.def_id == UNIQUE_ID])
                self.assertEqual([], player.deck)

    def test_stealing_a_duplicate_of_a_normal_card_has_no_penalty(self):
        for engine_class in ENGINE_CLASSES:
            with self.subTest(engine=engine_class.__name__):
                engine = _prepare_engine(engine_class)
                result, stolen, enemy_id = self._steal(
                    engine, engine_class, NORMAL_ID, own_duplicate=True
                )

                self.assertTrue(result.get("success"), result)
                player = engine.players[0]
                self.assertEqual(2, sum(card.def_id == NORMAL_ID for card in player.hand))
                self.assertEqual([], player.deck)

    def test_same_player_move_to_hand_is_not_penalized(self):
        engine = _prepare_engine(GameEngine)
        unique_owned = CardInstance(UNIQUE_ID)
        unique_extra = CardInstance(UNIQUE_ID)
        engine.players[0].discard = [unique_owned]
        engine.players[0].hand = [unique_extra]

        # Round 50 / 批次 AN：``move_to_hand`` 已并进 ``move_card(zone:"hand")``。
        engine._run_effect_list(
            0, None,
            [{"op": "move_card", "zone": "hand", "card": unique_owned, "target": "self"}],
            None, {},
        )

        self.assertIn(unique_owned, engine.players[0].hand)
        self.assertEqual([], engine.players[0].deck)



if __name__ == "__main__":
    unittest.main()
