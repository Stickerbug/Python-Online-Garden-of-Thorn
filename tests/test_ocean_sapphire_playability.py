import unittest

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2


def make_card_def(def_id, card_type, *, legacy_id='', flags=None):
    card_def = CardDef(
        def_id,
        def_id,
        def_id,
        2 if card_type == 'bloom' else 0,
        0,
        card_type,
        1,
        'Common',
        '',
        '',
        flags=set(flags or []),
    )
    card_def.legacy_id = legacy_id
    if legacy_id:
        card_def.v2_resource = {'legacy_id': legacy_id}
    return card_def


class OceanSapphirePlayabilityTests(unittest.TestCase):
    def setUp(self):
        self.test_defs = {
            'test:ocean_sapphire': make_card_def(
                'test:ocean_sapphire',
                'bloom',
                legacy_id='Sapphire',
                flags={'exile'},
            ),
            'test:sapphire_attack': make_card_def('test:sapphire_attack', 'thorn'),
            'test:sapphire_unique_attack': make_card_def(
                'test:sapphire_unique_attack',
                'thorn',
                flags={'unique'},
            ),
            'test:sapphire_exile_attack': make_card_def(
                'test:sapphire_exile_attack',
                'thorn',
                flags={'exile'},
            ),
        }
        self.test_defs['test:ocean_sapphire'].v2_events = {
            'on_play': {
                'steps': [
                    {
                        'op': 'request_card',
                        'params': {
                            'choice_type': 'choose_ocean_sapphire',
                            'cancellable': True,
                        },
                    },
                    {
                        'op': 'ocean_sapphire_mark',
                        'target': 'target',
                    },
                ],
            },
        }
        self.previous_defs = {key: CARD_DEFS.get(key) for key in self.test_defs}
        CARD_DEFS.update(self.test_defs)

    def tearDown(self):
        for key, previous in self.previous_defs.items():
            if previous is None:
                CARD_DEFS.pop(key, None)
            else:
                CARD_DEFS[key] = previous

    @staticmethod
    def prepare_engine(engine):
        engine.phase = 'action'
        engine.current_player = 0
        player = engine.players[0]
        player.hand.clear()
        player.elixir = 10
        player.magic = 10
        return player

    def test_sapphire_is_rejected_before_payment_without_attack_card(self):
        for engine in (GameEngine(), GameEngine2v2()):
            with self.subTest(engine=type(engine).__name__):
                player = self.prepare_engine(engine)
                sapphire = CardInstance('test:ocean_sapphire')
                player.hand.append(sapphire)

                can_play, reason = engine.can_play_card(0, sapphire)
                result = (
                    engine.play_card(0, sapphire.instance_id)
                    if isinstance(engine, GameEngine) and not isinstance(engine, GameEngine2v2)
                    else engine.play_card(0, sapphire.instance_id, -1)
                )

                self.assertFalse(can_play)
                self.assertIn('没有可选择的攻击牌', reason)
                self.assertFalse(result['success'])
                self.assertIn('没有可选择的攻击牌', result['error'])
                self.assertEqual(player.elixir, 10)
                self.assertEqual(player.hand, [sapphire])
                self.assertIsNone(engine.pending_choice)

    def test_sapphire_ignores_unique_and_exile_attack_cards(self):
        for blocked_def_id in ('test:sapphire_unique_attack', 'test:sapphire_exile_attack'):
            with self.subTest(blocked_def_id=blocked_def_id):
                engine = GameEngine()
                player = self.prepare_engine(engine)
                sapphire = CardInstance('test:ocean_sapphire')
                player.hand.extend([sapphire, CardInstance(blocked_def_id)])

                can_play, reason = engine.can_play_card(0, sapphire)

                self.assertFalse(can_play)
                self.assertIn('没有可选择的攻击牌', reason)

    def test_sapphire_is_playable_with_an_eligible_attack_card(self):
        for engine in (GameEngine(), GameEngine2v2()):
            with self.subTest(engine=type(engine).__name__):
                player = self.prepare_engine(engine)
                sapphire = CardInstance('test:ocean_sapphire')
                attack = CardInstance('test:sapphire_attack')
                player.hand.extend([sapphire, attack])

                can_play, reason = engine.can_play_card(0, sapphire)

                self.assertTrue(can_play)
                self.assertEqual(reason, '')
                self.assertEqual(
                    engine._ocean_sapphire_selectable_attacks(0, sapphire),
                    [attack],
                )

    def test_valid_sapphire_choice_resumes_once_and_exiles_selected_attack(self):
        engine = GameEngine()
        player = self.prepare_engine(engine)
        sapphire = CardInstance('test:ocean_sapphire')
        attack = CardInstance('test:sapphire_attack')
        player.hand.extend([sapphire, attack])

        play_result = engine.play_card(0, sapphire.instance_id)

        self.assertTrue(play_result['success'])
        self.assertTrue(play_result['needs_choice'])
        self.assertEqual(play_result['choice_type'], 'choose_ocean_sapphire')
        self.assertIsNotNone(engine.pending_choice)
        self.assertIsNone(player.find_hand_card(sapphire.instance_id))

        choice_result = engine.resolve_choice(0, {
            'target_player': 1,
            'target_player_id': 1,
            'target_id': 1,
            'target_instance_id': attack.instance_id,
        })

        self.assertTrue(choice_result['success'])
        self.assertIsNone(engine.pending_choice)
        self.assertIsNone(player.find_hand_card(attack.instance_id))
        self.assertIn(attack.instance_id, [card.instance_id for card in player.exile])
        entries = player.custom_vars.get('ocean_auto_cards', [])
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['target_id'], 1)


if __name__ == '__main__':
    unittest.main()
