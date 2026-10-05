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


class ForgedCardCopyTest(unittest.TestCase):
    """#368 根因：机械轨道/弃牌复制走 _new_card(def_id)，锻造卡 titan:XXXX
    不在 STORY_CARDS → 报「未知故事卡牌」把对局卡死。"""

    def _state(self):
        return {
            'phase': 'combat', 'stage': 1,
            'player': {'health': 80, 'elixir': 5, 'magic': 5, 'deck': [],
                       'next_card_serial': 100},
            'combat': {
                'hand': [], 'draw_pile': [], 'discard_pile': [], 'exile_pile': [],
                'enemies': [{'id': 'e1', 'def_id': 'mechanical_flower',
                             'health': 456, 'max_health': 456,
                             'mechanical_track': [], 'intent': None}],
                'elixir': 5, 'magic': 5, 'shield': 0,
            },
        }

    def test_forged_card_survives_mechanical_track(self):
        state = self._state()
        events = []
        a = story_engine._new_card(state, 'chloroplast')
        b = story_engine._new_card(state, 'sunflower_card')
        state['player']['deck'] += [a, b]
        forged = story_engine._forge_story_cards(state, a, b, events, source='titan_forge')
        forged.setdefault('modifiers', {})['force_void'] = 1
        forged['generated']['effects'] = tuple(
            list(forged['generated']['effects'])
            + [{'type': 'create_discard_copy', 'amount': 1}]
        )
        state['combat']['exile_pile'].append(forged)
        story_engine._notify_exiled(state, forged, events, seed=1)
        enemy = state['combat']['enemies'][0]
        self.assertEqual(len(enemy['mechanical_track']), 1)
        card = enemy['mechanical_track'].pop(0)
        # 修复前这里抛 StoryActionError(UNKNOWN_CARD)
        story_engine._resolve_mechanical_track_card(state, enemy, card, 1, events)
        self.assertTrue(any(e['type'] == 'mechanical_track_card_created' for e in events))

    def test_copy_card_instance_generated_keeps_definition(self):
        state = self._state()
        forged = {
            'instance_id': 'sc-00055', 'def_id': 'titan:00100',
            'generated': {'name': {'zh': 'A·B', 'en': 'A·B'}, 'effects': ()},
            'modifiers': {'force_void': 1},
        }
        copied = story_engine._copy_card_instance(state, forged)
        self.assertNotEqual(copied['instance_id'], forged['instance_id'])
        self.assertEqual(copied['def_id'], 'titan:00100')
        self.assertIn('generated', copied)
        self.assertEqual(state['player']['next_card_serial'], 101)

    def test_copy_card_instance_regular_unchanged(self):
        state = self._state()
        card = {'instance_id': 'sc-00100', 'def_id': 'chloroplast', 'upgraded': True}
        copied = story_engine._copy_card_instance(state, card)
        self.assertEqual(copied['def_id'], 'chloroplast')
        self.assertTrue(copied.get('upgraded'))


if __name__ == '__main__':
    unittest.main()
