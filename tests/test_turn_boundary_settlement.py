import unittest

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import EquipmentInstance, GameEngine, PlayerState
from game_engine_2v2 import GameEngine2v2


class TurnBoundarySettlementTests(unittest.TestCase):
    def _prime_1v1(self):
        engine = GameEngine()
        engine.phase = 'action'
        engine.round_num = 2
        engine.first_player = 0
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.deck = []
            player.hand = []
            player.discard = []
        return engine

    def test_bandage_expires_after_next_allied_actionable_player_turn(self):
        engine = self._prime_1v1()
        player = engine.players[0]
        player.invincible = True
        player.bandage_death_pending = True
        player.bandage_trigger_boundary_id = 0

        engine._end_player_turn(0)

        self.assertFalse(engine.game_over)
        self.assertEqual(engine.current_player, 1)
        self.assertEqual(player.health, 100)

        engine._end_player_turn(1)

        self.assertFalse(engine.game_over)
        self.assertEqual(engine.current_player, 0)
        self.assertEqual(player.health, 100)
        self.assertEqual(player.bandage_death_action_player_id, 0)

        engine._end_player_turn(0)

        self.assertTrue(engine.game_over)
        self.assertEqual(engine.winner, 1)
        self.assertEqual(player.health, 0)

    def test_stunned_turn_does_not_count_as_actionable(self):
        engine = self._prime_1v1()
        player = engine.players[0]
        player.invincible = True
        player.bandage_death_pending = True
        player.bandage_trigger_boundary_id = 0
        engine.players[1].skip_turn = 1

        engine._end_player_turn(0)

        self.assertFalse(engine.game_over)
        self.assertEqual(engine.current_player, 0)
        self.assertEqual(player.health, 100)
        self.assertEqual(player.bandage_death_action_player_id, 0)

        engine._end_player_turn(0)

        self.assertTrue(engine.game_over)
        self.assertEqual(engine.winner, 1)
        self.assertEqual(engine.players[1].skip_turn, 0)
        stun_index = next(i for i, line in enumerate(engine.log) if '被眩晕，跳过本回合' in line)
        bandage_index = next(i for i, line in enumerate(engine.log) if '的绷带效果结束' in line)
        self.assertLess(stun_index, bandage_index)
        self.assertEqual(engine._turn_boundary_serial, 3)

    def test_turn_start_auto_effects_finish_before_bandage_death(self):
        engine = self._prime_1v1()
        engine.current_player = 0
        engine._ensure_turn_boundary()
        player = engine.players[0]
        player.invincible = True
        player.bandage_death_pending = True
        player.bandage_trigger_boundary_id = 0
        engine._run_ocean_auto_cards_turn_start = lambda _player_id: engine.log_msg('回合开始自动效果')

        engine._enter_player_action_phase(0)

        self.assertFalse(engine.game_over)
        self.assertEqual(player.health, 100)
        self.assertEqual(player.bandage_death_action_player_id, 0)
        self.assertFalse(any('的绷带效果结束' in line for line in engine.log))

        engine._end_player_turn(0)

        auto_index = engine.log.index('回合开始自动效果')
        bandage_index = next(i for i, line in enumerate(engine.log) if '的绷带效果结束' in line)
        self.assertLess(auto_index, bandage_index)
        self.assertTrue(engine.game_over)

    def test_bandage_triggered_during_boundary_waits_one_more_action(self):
        engine = self._prime_1v1()
        engine._ensure_turn_boundary()
        player = engine.players[0]
        player.invincible = True
        engine._mark_bandage_death_pending(0)

        engine._enter_player_action_phase(1)

        self.assertFalse(engine.game_over)
        self.assertEqual(player.health, 100)
        self.assertEqual(engine.phase, 'action')

        engine.first_player = 1
        engine.current_player = 1
        engine._end_player_turn(1)

        self.assertFalse(engine.game_over)
        self.assertEqual(engine.current_player, 0)
        self.assertEqual(player.health, 100)
        self.assertEqual(player.bandage_death_action_player_id, 0)

        engine._end_player_turn(0)

        self.assertTrue(engine.game_over)
        self.assertEqual(engine.winner, 1)
        self.assertEqual(player.health, 0)

    def test_2v2_bandage_expiry_does_not_stop_surviving_team(self):
        engine = GameEngine2v2()
        engine.phase = 'action'
        engine.round_num = 2
        engine.turn_order = [0, 2, 1, 3]
        engine.turn_index = 0
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.deck = []
            player.hand = []
            player.discard = []
        player = engine.players[0]
        player.invincible = True
        player.bandage_death_pending = True
        player.bandage_trigger_boundary_id = 0

        engine._end_player_turn(0)

        self.assertFalse(engine.game_over)
        self.assertEqual(player.health, 100)
        self.assertEqual(engine.current_player, 2)
        self.assertEqual(engine.phase, 'action')

        engine._end_player_turn(2)

        self.assertFalse(engine.game_over)
        self.assertEqual(engine.current_player, 1)
        self.assertEqual(player.health, 100)
        self.assertEqual(player.bandage_death_action_player_id, 1)

        engine._end_player_turn(1)

        self.assertFalse(engine.game_over)
        self.assertEqual(player.health, 0)
        self.assertEqual(engine.current_player, 3)
        self.assertEqual(engine.phase, 'action')

    def test_opposing_pending_bandages_expire_on_their_respective_team_turns(self):
        engine = GameEngine2v2()
        engine.phase = 'action'
        engine.current_player = 0
        engine.players[1].health = 0
        engine.players[3].health = 0
        for player_id in (0, 2):
            player = engine.players[player_id]
            player.health = 1
            player.invincible = True
            player.bandage_death_pending = True
            player.bandage_trigger_boundary_id = 0
        engine._ensure_turn_boundary()

        engine._enter_player_action_phase(0)

        self.assertFalse(engine.game_over)
        self.assertEqual(engine.players[0].health, 1)
        self.assertEqual(engine.players[0].bandage_death_action_player_id, 0)
        self.assertEqual(engine.players[2].bandage_death_action_player_id, -1)

        engine._end_player_turn(0)

        self.assertTrue(engine.game_over)
        self.assertEqual(engine.winner, 1)
        self.assertEqual(engine.winning_team, 1)
        self.assertEqual(engine.players[0].health, 0)
        self.assertEqual(engine.players[2].health, 1)

    def test_bandage_trigger_does_not_block_the_current_action_phase(self):
        engine = self._prime_1v1()
        player = engine.players[0]
        player.health = 0
        player.elixir = 10
        player.bandage_active = True

        engine._check_yggdrasil(0)

        card = CardInstance('Basic')
        player.hand = [card]
        result = engine.play_card(
            0,
            card.instance_id,
            {'target_player': 1, 'target_player_id': 1, 'target_id': 1},
        )

        self.assertTrue(result.get('success'))
        self.assertEqual(player.health, 1)
        self.assertTrue(player.bandage_death_pending)
        self.assertEqual(engine.phase, 'action')
        self.assertEqual(engine.current_player, 0)

        engine._end_player_turn(0)

        self.assertFalse(engine.game_over)
        self.assertEqual(player.health, 1)
        self.assertEqual(player.bandage_death_action_player_id, -1)

        engine._end_player_turn(1)

        self.assertFalse(engine.game_over)
        self.assertEqual(engine.current_player, 0)
        self.assertEqual(player.bandage_death_action_player_id, 0)

        engine._end_player_turn(0)

        self.assertTrue(engine.game_over)
        self.assertEqual(player.health, 0)

    def test_bandage_triggered_on_enemy_turn_allows_the_saved_player_to_act(self):
        engine = self._prime_1v1()
        engine.first_player = 1
        engine.current_player = 1
        player = engine.players[0]
        player.health = 5
        player.bandage_active = True
        card = CardInstance('Basic')
        player.hand = [card]

        engine.deal_attack_damage(0, 10, attacker_id=1)
        engine._end_player_turn(1)

        self.assertFalse(engine.game_over)
        self.assertEqual(engine.current_player, 0)
        self.assertEqual(player.health, 1)
        self.assertEqual(player.bandage_death_action_player_id, 0)

        result = engine.play_card(
            0,
            card.instance_id,
            {'target_player': 1, 'target_player_id': 1, 'target_id': 1},
        )

        self.assertTrue(result.get('success'))

    def test_bandage_action_assignment_survives_state_round_trip(self):
        player = PlayerState(0)
        player.bandage_death_pending = True
        player.bandage_death_action_player_id = 0

        restored = PlayerState.from_dict(player.to_dict())

        self.assertTrue(restored.bandage_death_pending)
        self.assertEqual(restored.bandage_death_action_player_id, 0)

    def test_2v2_actionable_teammate_death_still_expires_bandage(self):
        engine = GameEngine2v2()
        engine.phase = 'action'
        engine.turn_order = [0, 2, 1, 3]
        engine.turn_index = 2
        engine.current_player = 1
        for player in engine.players:
            player.health = 100
        pending = engine.players[0]
        pending.health = 1
        pending.invincible = True
        pending.bandage_death_pending = True
        pending.bandage_death_action_player_id = 1
        engine.players[1].health = 0

        advanced = engine._advance_dead_current_player_if_ready()

        self.assertTrue(advanced)
        self.assertTrue(engine.game_over)
        self.assertEqual(engine.winning_team, 1)
        self.assertEqual(pending.health, 0)

    def test_stunned_teammate_is_not_the_next_allied_actionable_player(self):
        engine = GameEngine2v2()
        engine.phase = 'action'
        engine.round_num = 2
        engine.turn_order = [0, 2, 1, 3]
        engine.turn_index = 0
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.deck = []
            player.hand = []
            player.discard = []
        pending = engine.players[0]
        pending.invincible = True
        pending.bandage_death_pending = True
        pending.bandage_trigger_boundary_id = 0
        engine.players[1].skip_turn = 1

        engine._end_player_turn(0)
        engine._end_player_turn(2)

        self.assertEqual(engine.current_player, 3)
        self.assertEqual(pending.health, 100)
        self.assertEqual(engine.players[1].skip_turn, 0)

        engine._end_player_turn(3)

        self.assertEqual(pending.health, 100)
        self.assertEqual(engine.current_player, 0)
        self.assertEqual(pending.bandage_death_action_player_id, 0)

        engine._end_player_turn(0)

        self.assertEqual(pending.health, 0)
        self.assertEqual(engine.current_player, 2)

    def test_turn_start_death_does_not_skip_living_player_or_soil_turn_end(self):
        soil_id = 'test:r15236_soil'
        previous = CARD_DEFS.get(soil_id)
        CARD_DEFS[soil_id] = CardDef(
            soil_id,
            'Soil',
            '土',
            0,
            0,
            'root',
            1,
            'Common',
            '',
            '',
            flags={'indestructible'},
            v2_events={
                'on_owner_turn_end': {
                    'steps': [{
                        'op': 'add_status',
                        'target': 'target',
                        'status': 'sluggish',
                        'amount': 1,
                    }],
                },
            },
        )
        try:
            engine = GameEngine2v2()
            engine.phase = 'action'
            engine.round_num = 17
            engine.turn_order = [0, 2, 1, 3]
            engine.turn_index = 2
            engine.current_player = 1
            for player in engine.players:
                player.health = 100
                player.max_health = 100
                player.deck = []
                player.hand = []
                player.discard = []
                player.exile = []
                player.equipment = []
            engine.players[0].health = 0
            engine.players[3].health = 1
            engine.players[3].fire = 1
            for owner_id in (1, 1, 3):
                equipment = EquipmentInstance(CardInstance(soil_id), owner_id)
                equipment.effect_target = 2
                engine.players[owner_id].equipment.append(equipment)

            engine._end_player_turn(1)

            self.assertEqual(engine.players[3].health, 0)
            self.assertEqual(engine.current_player, 2)
            self.assertEqual(engine.turn_index, 1)
            self.assertEqual(engine.players[2].sluggish, 0)

            engine._end_player_turn(2)

            self.assertEqual(engine.players[2].sluggish, 3)
        finally:
            if previous is None:
                CARD_DEFS.pop(soil_id, None)
            else:
                CARD_DEFS[soil_id] = previous

    def test_new_matching_timed_effect_settles_in_same_boundary(self):
        engine = self._prime_1v1()
        engine.current_player = 1
        engine._ensure_turn_boundary()
        engine._register_timed_effect(
            0,
            1,
            'target_turn_start',
            1,
            [{
                'type': 'timed_effect',
                'params': {
                    'target': 'event_target',
                    'trigger': 'target_turn_start',
                    'duration': 1,
                    'effects': [{
                        'type': 'var_add',
                        'params': {'target': 'event_target', 'name': 'boundary_probe', 'value': 1},
                    }],
                },
            }],
        )

        engine._run_timed_effects_for_turn(1)

        self.assertEqual(engine.players[1].custom_vars.get('boundary_probe'), 1)
        self.assertEqual(engine.timed_effects, [])

    def test_timed_source_runs_at_most_once_per_boundary(self):
        engine = self._prime_1v1()
        engine.current_player = 1
        engine._ensure_turn_boundary()
        engine._register_timed_effect(
            0,
            1,
            'target_turn_start',
            2,
            [{
                'type': 'var_add',
                'params': {'target': 'event_target', 'name': 'boundary_probe', 'value': 1},
            }],
        )

        engine._run_timed_effects_for_turn(1)
        engine._run_timed_effects_for_turn(1)
        self.assertEqual(engine.players[1].custom_vars.get('boundary_probe'), 1)

        engine._finish_turn_boundary()
        engine._ensure_turn_boundary()
        engine._run_timed_effects_for_turn(1)
        self.assertEqual(engine.players[1].custom_vars.get('boundary_probe'), 2)

    def test_foresight_choice_pauses_and_resumes_boundary(self):
        engine = self._prime_1v1()
        player = engine.players[0]
        player.foresight = 1
        player.hand = [CardInstance('Basic')]
        player.deck = [CardInstance('Bone')]

        engine._start_player_turn(0)

        self.assertIsNotNone(engine.pending_choice)
        self.assertTrue(engine._turn_boundary_active)
        engine.resolve_choice(0, {'selected_instance_ids': []})
        self.assertIsNone(engine.pending_choice)
        self.assertFalse(engine._turn_boundary_active)
        self.assertEqual(engine.phase, 'action')

    def test_dna_choice_pauses_and_resumes_boundary(self):
        engine = self._prime_1v1()
        player = engine.players[0]
        selected = CardInstance('Basic')
        player.hand = [selected]
        dna_equipment = EquipmentInstance(CardInstance('Basic'), 0)
        player.equipment = [dna_equipment]
        engine._bio_active_equipment_targeting = lambda *_args: [(0, dna_equipment)]
        engine._bio_dna_candidates_for_card = lambda _card: ['Basic']

        engine._start_player_turn(0)

        self.assertIsNotNone(engine.pending_choice)
        self.assertTrue(engine.pending_choice.get('bio_dna_turn_start'))
        self.assertTrue(engine._turn_boundary_active)
        engine.resolve_choice(0, {'target_instance_id': selected.instance_id})
        self.assertIsNone(engine.pending_choice)
        self.assertFalse(engine._turn_boundary_active)
        self.assertEqual(engine.phase, 'action')


if __name__ == '__main__':
    unittest.main()
