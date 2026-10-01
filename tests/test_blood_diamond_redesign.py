"""反馈：血钻石改成珊瑚式——单次命中 + 永久裂变，不再 4 次命中叠 16 层流血。"""

import unittest
from pathlib import Path

from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine, reset_card_after_play
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'mods' / 'Bio Cards Addition.gtnmod'
OCEAN_PACKAGE = ROOT / 'mods' / 'Ocean Cards Addition.gtnmod'


class BloodDiamondRedesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_mod(str(PACKAGE))
        cls.ocean = load_mod(str(OCEAN_PACKAGE))
        if cls.mod.errors or cls.ocean.errors:
            raise AssertionError(cls.mod.errors + cls.ocean.errors)
        cls.card_defs = {card.id: card.to_card_def() for card in [*cls.mod.cards, *cls.ocean.cards]}

    def setUp(self):
        self.previous = {cid: CARD_DEFS.get(cid) for cid in ('BloodDiamond', 'Coral')}
        for cid in self.previous:
            CARD_DEFS[cid] = self.card_defs[cid]

    def tearDown(self):
        for cid, old in self.previous.items():
            if old is None:
                CARD_DEFS.pop(cid, None)
            else:
                CARD_DEFS[cid] = old

    def _play_fully(self, card_id):
        engine = GameEngine()
        engine.players[1].health = 999
        card = CardInstance(card_id)
        engine.players[0].hand = [card]
        engine._active_choice = {'target_player': 1}
        before = engine.players[1].health
        for hit in range(int(card.fission_level)):
            card.fission_hit = hit
            engine._apply_card_effect(0, card, engine._active_choice)
        card.fission_hit = 0
        return engine, card, before - engine.players[1].health

    def test_card_data_matches_the_coral_style_redesign(self):
        card_def = self.card_defs['BloodDiamond']
        self.assertEqual(card_def.hits, 1)
        self.assertEqual(card_def.fission_level, 4)
        self.assertIn('unfading_fission', card_def.flags)
        # 双加数体系（2026-10-01）：「打出后不减少裂变层数」句由「不灭：裂变」标签芯片承担
        self.assertNotIn('不减少裂变层数', card_def.effect_text)
        self.assertNotIn('×4', card_def.effect_text)

    def test_playing_it_deals_one_hit_per_petal_and_keeps_bleed_small(self):
        engine, card, damage = self._play_fully('BloodDiamond')
        self.assertEqual(card.fission_level, 4)
        self.assertEqual(damage, 12)
        self.assertEqual(getattr(engine.players[1], 'bleed', 0), 4)

    def test_fission_survives_playing_like_coral(self):
        diamond = CardInstance('BloodDiamond')
        reset_card_after_play(diamond)
        self.assertEqual(diamond.fission_level, 4)
        coral = CardInstance('Coral')
        reset_card_after_play(coral)
        self.assertEqual(coral.fission_level, 4)

    def test_plain_thorn_card_still_loses_its_gained_layers(self):
        # 双加数体系（设计 2026-10-01）：无「不灭：裂变」的普通裂变卡打出后
        # 回落到卡面基线（获得的增量 M 清零），而不再重置为 1。
        plain = CardInstance('Coral')
        plain.instance_flags.clear()
        CARD_DEFS['Coral'] = type(self.card_defs['Coral'])(
            **{**self.card_defs['Coral'].__dict__, 'flags': set()}
        )
        plain.fission_base = 4
        plain.fission_level = 7
        reset_card_after_play(plain)
        self.assertEqual(plain.fission_level, 4)


if __name__ == '__main__':
    unittest.main()
