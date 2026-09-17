"""反馈 #151（泰坦锻造丢钟爱）与 #145（女贞子按真实层数结算）。"""

import json
import unittest
import zipfile
from pathlib import Path

from game_engine import GameEngine
from mod_runtime_v2 import eval_v2_value
from story_mode import build_initial_story_state
import story_engine as se


ROOT = Path(__file__).resolve().parents[1]
DESERT_PACKAGE = ROOT / 'mods' / 'Desert Cards Addition.gtnmod'


def _attack_cards(state):
    return [
        card for card in state['player']['deck']
        if se._card_values(card).get('type') == 'thorn'
        and 'eternal' not in (se._card_values(card).get('tags') or ())
        and not card.get('generated')
    ]


class TitanForgeKeepsModifiersTests(unittest.TestCase):
    def test_forged_card_keeps_favorite_marker(self):
        """反馈 #151：钟爱牌被泰坦锻造合并后，钟爱必须留在新牌上。"""
        state = build_initial_story_state('forge-favorite')
        attacks = _attack_cards(state)
        self.assertGreaterEqual(len(attacks), 2)
        favorite_card, other = attacks[0], attacks[1]
        favorite_id = str(favorite_card['instance_id'])

        state['pending_deck_operations'] = [{
            'id': 'story-deck-operation-0001',
            'kind': 'favorite_card',
            'source': 'favorite',
            'count': 1,
            'minimum': 1,
            'maximum': 1,
            'candidate_ids': [favorite_id],
        }]
        events = []
        se._resolve_deck_operation(state, {'selected_card_ids': [favorite_id]}, 'forge-1', events)
        self.assertTrue(se._card_has_favorite(favorite_card))

        forge_ids = [favorite_id, str(other['instance_id'])]
        state['pending_deck_operations'] = [{
            'id': 'story-deck-operation-0002',
            'kind': 'titan_forge',
            'source': 'titan_forge',
            'count': 2,
            'minimum': 2,
            'maximum': 2,
            'candidate_ids': forge_ids,
        }]
        se._resolve_deck_operation(state, {'selected_card_ids': forge_ids}, 'forge-2', events)

        forged = [
            card for card in state['player']['deck']
            if card.get('generated')
        ]
        self.assertTrue(forged)
        self.assertTrue(se._card_has_favorite(forged[-1]))
        self.assertIn('favorite', (forged[-1].get('modifiers') or {}))


class RealStatusStackDamageTests(unittest.TestCase):
    def _engine_with_immune_poison(self):
        engine = GameEngine()
        engine.players[1].poison = 4
        engine.players[1].custom_statuses['status_immune'] = 1
        engine.players[1].custom_statuses['状态免疫'] = 1
        return engine

    def test_default_status_stack_still_respects_immunity(self):
        engine = self._engine_with_immune_poison()
        context = {'source_player': 0, 'target_player': 1}
        expr = {'op': 'status_stack', 'target': 'target', 'status': 'poison'}
        self.assertEqual(eval_v2_value(engine, context, expr), 0)

    def test_ignore_immunity_reads_real_stacks(self):
        engine = self._engine_with_immune_poison()
        context = {'source_player': 0, 'target_player': 1}
        expr = {
            'op': 'status_stack',
            'target': 'target',
            'status': 'poison',
            'ignore_immunity': True,
        }
        self.assertEqual(eval_v2_value(engine, context, expr), 4)

    def test_privet_berry_uses_real_stacks(self):
        """反馈 #145：女贞子「造成等同目标中毒层数的伤害」按实际层数算。"""
        with zipfile.ZipFile(DESERT_PACKAGE) as archive:
            data = json.loads(archive.read('mod.json').decode('utf-8'))
        berry = next(
            card for card in (data.get('registries') or {}).get('cards') or []
            if str(card.get('legacy_id')) == 'PrivetBerry'
        )
        blob = json.dumps(berry, ensure_ascii=False)
        self.assertIn('"ignore_immunity": true', blob)


if __name__ == '__main__':
    unittest.main()
