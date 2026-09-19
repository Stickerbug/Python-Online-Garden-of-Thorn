"""反馈 #168：暗物质打「没有手牌/牌堆」的目标时不该卡在空选择里。"""

import unittest
from pathlib import Path

from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
VOID_PACKAGE = ROOT / 'mods' / 'Void Card Addition.gtnmod'
CARD_IDS = ('DarkMatter', 'MagicDarkMatter')


class DarkMatterGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mod = load_mod(str(VOID_PACKAGE))
        if mod.errors:
            raise AssertionError(mod.errors)
        cls.card_defs = {card.id: card.to_card_def() for card in mod.cards}

    def setUp(self):
        self.previous = {cid: CARD_DEFS.get(cid) for cid in CARD_IDS}
        for cid in CARD_IDS:
            CARD_DEFS[cid] = self.card_defs[cid]

    def tearDown(self):
        for cid, old in self.previous.items():
            if old is None:
                CARD_DEFS.pop(cid, None)
            else:
                CARD_DEFS[cid] = old

    @staticmethod
    def _engine():
        engine = GameEngine()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.max_health = 100
            player.elixir = 30
            player.magic = 30
            player.hand = []
            player.deck = []
            player.discard = []
            player.exile = []
            player.equipment = []
            player.custom_statuses = {}
            player.custom_vars = {}
        return engine

    @staticmethod
    def _play(engine, card_id, target_id=1):
        card = CardInstance(card_id)
        engine.players[0].hand = [card]
        return engine.play_card(0, card.instance_id, {
            'target_player': target_id,
            'target_player_id': target_id,
            'target_id': target_id,
        })

    @staticmethod
    def _pending(engine):
        return engine.pending_choice or getattr(engine, 'pending_v2_ui', None)

    def test_dark_matter_on_empty_hand_does_not_hang(self):
        engine = self._engine()
        engine.players[1].deck = [CardInstance('Basic')]

        result = self._play(engine, 'DarkMatter')

        self.assertTrue(result.get('success'), result)
        self.assertIsNone(self._pending(engine))

    def test_dark_matter_with_hand_still_asks_for_a_card(self):
        engine = self._engine()
        engine.players[1].hand = [CardInstance('Basic')]

        result = self._play(engine, 'DarkMatter')

        self.assertTrue(result.get('success'), result)
        self.assertIsNotNone(self._pending(engine))

    def test_magic_dark_matter_still_asks_for_a_deck_card(self):
        engine = self._engine()
        engine.players[1].hand = [CardInstance('Basic')]
        engine.players[1].deck = [CardInstance('Basic')]

        result = self._play(engine, 'MagicDarkMatter')

        self.assertTrue(result.get('success'), result)
        self.assertIsNotNone(self._pending(engine))

    def test_magic_dark_matter_on_empty_deck_does_not_hang(self):
        engine = self._engine()
        engine.players[1].hand = [CardInstance('Basic')]

        result = self._play(engine, 'MagicDarkMatter')

        self.assertTrue(result.get('success'), result)
        self.assertIsNone(self._pending(engine))


if __name__ == '__main__':
    unittest.main()
