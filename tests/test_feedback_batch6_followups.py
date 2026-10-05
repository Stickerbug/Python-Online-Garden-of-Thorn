# -*- coding: utf-8 -*-
"""批次6跟进：#363 战斗内不写卡组变化日志；#368 锻造卡数据丢失兜底。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import story_engine  # noqa: E402


class DeckLogCombatScopeTest(unittest.TestCase):
    def _state(self):
        return {'phase': 'reward', 'player': {'deck': [], 'deck_log': []}}

    def test_reward_gain_logged(self):
        state = self._state()
        events = [{'type': 'card_gained', 'card_id': 'stinger', 'upgraded': False, 'source': 'reward'}]
        story_engine._extract_deck_log(state, events, combat_scoped=False)
        self.assertEqual(len(state['player']['deck_log']), 1)

    def test_combat_events_not_logged(self):
        state = self._state()
        events = [
            {'type': 'card_gained', 'card_id': 'magic_orb', 'upgraded': False, 'source': 'combat'},
            {'type': 'card_exiled', 'card_instance_id': 1, 'def_id': 'magic_orb'},
        ]
        story_engine._extract_deck_log(state, events, combat_scoped=True)
        self.assertEqual(state['player']['deck_log'], [])

    def test_default_behavior_unchanged(self):
        state = self._state()
        events = [{'type': 'card_gained', 'card_id': 'stinger', 'upgraded': False, 'source': 'reward'}]
        story_engine._extract_deck_log(state, events)
        self.assertEqual(len(state['player']['deck_log']), 1)


class TitanFallbackCardDefTest(unittest.TestCase):
    def test_titan_without_generated_returns_placeholder(self):
        card = {'def_id': 'titan:00042', 'instance_id': 'sc-00042'}
        definition = story_engine._card_def(card)
        self.assertEqual(definition['name']['zh'], '残缺的锻造卡')
        self.assertEqual(definition['effects'], ())

    def test_titan_with_generated_uses_generated(self):
        card = {'def_id': 'titan:00042', 'generated': {'name': {'zh': '结合卡', 'en': 'Combo'}, 'effects': ()}}
        definition = story_engine._card_def(card)
        self.assertEqual(definition['name']['zh'], '结合卡')

    def test_unknown_real_card_still_fails(self):
        from story_engine import StoryActionError
        with self.assertRaises(StoryActionError):
            story_engine._card_def({'def_id': 'no_such_card', 'instance_id': 'x'})


if __name__ == '__main__':
    unittest.main()
