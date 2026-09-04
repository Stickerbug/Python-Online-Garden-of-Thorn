import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import EquipmentInstance, GameEngine, PlayerState
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]


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

    def test_pending_bandage_expires_at_owners_current_turn_end(self):
        engine = self._prime_1v1()
        player = engine.players[0]
        player.invincible = True
        player.bandage_death_pending = True
        player.bandage_trigger_boundary_id = 0
        # A stale value from the previous rule must not defer settlement.
        player.bandage_death_action_player_id = 1

        engine._end_player_turn(0)

        self.assertTrue(engine.game_over)
        self.assertEqual(engine.winner, 1)
        self.assertEqual(player.health, 0)
        self.assertTrue(any('自己回合结束时死亡' in line for line in engine.log))

    def test_stunned_own_turn_still_settles_bandage_death(self):
        engine = self._prime_1v1()
        engine.first_player = 1
        engine.current_player = 1
        player = engine.players[0]
        player.invincible = True
        player.bandage_death_pending = True
        player.bandage_trigger_boundary_id = 0
        player.skip_turn = 1

        engine._end_player_turn(1)

        self.assertTrue(engine.game_over)
        self.assertEqual(engine.winner, 1)
        self.assertEqual(player.skip_turn, 0)
        stun_index = next(i for i, line in enumerate(engine.log) if '被眩晕，跳过本回合' in line)
        bandage_index = next(i for i, line in enumerate(engine.log) if '的绷带效果结束' in line)
        self.assertLess(stun_index, bandage_index)

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

    def test_bandage_triggered_on_other_turn_waits_for_owners_turn_end(self):
        engine = self._prime_1v1()
        engine._ensure_turn_boundary()
        player = engine.players[0]
        player.invincible = True
        engine._mark_bandage_death_pending(0)

        engine._enter_player_action_phase(1)

        self.assertFalse(engine.game_over)
        self.assertEqual(player.health, 100)
        self.assertEqual(engine.phase, 'action')
        self.assertEqual(player.bandage_death_action_player_id, 0)

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

    def test_2v2_teammate_turn_does_not_expire_bandage(self):
        engine = GameEngine2v2()
        engine.phase = 'action'
        engine.round_num = 2
        engine.turn_order = [0, 2, 1, 3]
        engine.turn_index = 1
        engine.current_player = 2
        for player in engine.players:
            player.health = 100
            player.deck = []
            player.hand = []
            player.discard = []
        player = engine.players[0]
        player.invincible = True
        player.bandage_death_pending = True
        player.bandage_trigger_boundary_id = 0

        engine._end_player_turn(2)

        self.assertFalse(engine.game_over)
        self.assertEqual(player.health, 100)
        self.assertEqual(engine.current_player, 1)
        self.assertEqual(engine.phase, 'action')

        engine._end_player_turn(1)

        self.assertFalse(engine.game_over)
        self.assertEqual(engine.current_player, 3)
        self.assertEqual(player.health, 100)
        self.assertEqual(player.bandage_death_action_player_id, 0)

        engine._end_player_turn(3)

        self.assertFalse(engine.game_over)
        self.assertEqual(engine.current_player, 0)
        self.assertEqual(player.health, 100)

        engine._end_player_turn(0)

        self.assertFalse(engine.game_over)
        self.assertEqual(player.health, 0)
        self.assertEqual(engine.current_player, 2)
        self.assertEqual(engine.phase, 'action')

    def test_2v2_pending_bandages_expire_only_on_their_owners_turns(self):
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
        for player_id in (0, 2):
            player = engine.players[player_id]
            player.health = 1
            player.invincible = True
            player.bandage_death_pending = True
            player.bandage_trigger_boundary_id = 0
        engine._ensure_turn_boundary()

        engine._end_player_turn(0)

        self.assertFalse(engine.game_over)
        self.assertEqual(engine.players[0].health, 0)
        self.assertEqual(engine.players[2].health, 1)
        self.assertEqual(engine.current_player, 2)

        engine._end_player_turn(2)

        self.assertFalse(engine.game_over)
        self.assertEqual(engine.players[2].health, 0)
        self.assertEqual(engine.current_player, 1)

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

        engine._end_player_turn(0)

        self.assertTrue(engine.game_over)
        self.assertEqual(player.health, 0)

    def test_bandage_response_prediction_and_authoritative_timing(self):
        package = load_mod(str(ROOT / 'mods' / 'Vanilla Cards.gtnmod'))
        self.assertEqual([], package.errors)
        bandage_def = next(card.to_card_def() for card in package.cards if card.id == 'Bandage')
        previous = CARD_DEFS.get('Bandage')
        CARD_DEFS['Bandage'] = bandage_def
        try:
            engine = self._prime_1v1()
            attacker = CardInstance('Basic')
            bandage = CardInstance('Bandage')
            engine.players[0].hand = [attacker]
            engine.players[1].health = 5
            engine.players[1].hand = [bandage]

            result = engine.play_card(
                0,
                attacker.instance_id,
                {'target_player': 1, 'target_player_id': 1, 'target_id': 1},
            )
            self.assertTrue(result.get('needs_response'), result)

            prediction = engine.build_response_damage_prediction(1, [bandage])
            self.assertGreater(prediction['no_counter']['total'], 0)
            self.assertEqual(
                prediction['no_counter']['total'],
                prediction['counters'][str(bandage.instance_id)]['after']['total'],
            )
            self.assertFalse(engine.players[1].bandage_active)
            self.assertFalse(engine.players[1].bandage_death_pending)

            response = engine.handle_response(1, bandage.instance_id)
            self.assertTrue(response.get('success'), response)
            saved = engine.players[1]
            self.assertEqual(1, saved.health)
            self.assertTrue(saved.invincible)
            self.assertTrue(saved.bandage_death_pending)
            self.assertEqual(1, saved.bandage_death_action_player_id)

            engine._end_player_turn(0)
            self.assertFalse(engine.game_over)
            self.assertEqual(1, engine.current_player)
            engine._end_player_turn(1)
            self.assertTrue(engine.game_over)
            self.assertEqual(0, saved.health)
        finally:
            if previous is None:
                CARD_DEFS.pop('Bandage', None)
            else:
                CARD_DEFS['Bandage'] = previous

    def test_bandage_pending_replay_state_survives_round_trip_and_expires(self):
        player = PlayerState(0)
        player.health = 1
        player.invincible = True
        player.bandage_death_pending = True
        player.bandage_death_action_player_id = 0

        restored = PlayerState.from_dict(player.to_dict())

        self.assertTrue(restored.bandage_death_pending)
        self.assertEqual(restored.bandage_death_action_player_id, 0)
        engine = self._prime_1v1()
        engine.players[0] = restored
        engine._end_player_turn(0)
        self.assertTrue(engine.game_over)
        self.assertEqual(0, restored.health)

    def test_bandage_card_and_status_text_use_exact_own_turn_wording(self):
        package = ROOT / 'mods' / 'Vanilla Cards.gtnmod'
        with zipfile.ZipFile(package) as archive:
            document = json.loads(archive.read('mod.json').decode('utf-8'))
            zh_locale = json.loads(archive.read('locales/zh.json').decode('utf-8'))
        bandage = next(
            card
            for card in document['registries']['cards']
            if card.get('id') == 'vanilla:bandage'
        )
        exact_effect_text = '使自己获得绷带；绷带触发后自己回合结束时死亡  响应：被作为攻击牌目标'
        self.assertEqual(exact_effect_text, bandage['effect_text'])
        self.assertEqual(exact_effect_text, zh_locale['cards']['vanilla:bandage']['effect_text'])

        client_source = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
        description_spec = (ROOT / 'docs' / '卡牌描述规范.md').read_text(encoding='utf-8')
        self.assertIn('自己回合结束时死亡', client_source)
        self.assertIn('自己回合结束时死亡', description_spec)
        self.assertNotIn('己方下一名可行动玩家回合结束后死亡', client_source)
        self.assertNotIn('己方下一名可行动玩家回合结束后死亡', description_spec)

    def test_local_solo_bandage_uses_owner_turn_end(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node is required for the local Bandage behavior test')
        worker = (ROOT / 'static' / 'js' / 'local_solo_worker.js').read_text(encoding='utf-8')
        harness = r'''
const bandageEngine = Object.create(LocalSoloEngine.prototype);
bandageEngine.players = [new LocalPlayer(0), new LocalPlayer(1)];
bandageEngine.player_names = ['P1', 'P2'];
bandageEngine.log = [];
bandageEngine.logMsg = message => bandageEngine.log.push(String(message));
bandageEngine.checkGameOver = () => {};
bandageEngine._turn_boundary_active = false;
bandageEngine._turn_boundary_serial = 7;
bandageEngine.players[0].health = 1;
bandageEngine.players[0].invincible = true;
bandageEngine.markBandageDeathPending(0);
const assignedOwner = bandageEngine.players[0].bandage_death_action_player_id;
bandageEngine.expireBandagesAfterAction(1);
const afterOtherTurn = bandageEngine.players[0].health;
bandageEngine.expireBandagesAfterAction(0);
process.stdout.write(JSON.stringify({
    assignedOwner,
    afterOtherTurn,
    afterOwnTurn: bandageEngine.players[0].health,
    wording: bandageEngine.log.some(line => line.includes('自己回合结束时死亡')),
}));
'''
        with tempfile.TemporaryDirectory(prefix='gtn-bandage-worker-') as temp_dir:
            script_path = Path(temp_dir) / 'bandage-worker-test.js'
            script_path.write_text(
                "globalThis.postMessage = () => {};\n" + worker + "\n" + harness,
                encoding='utf-8',
            )
            completed = subprocess.run(
                [node, str(script_path)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=20,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            {
                'assignedOwner': 0,
                'afterOtherTurn': 1,
                'afterOwnTurn': 0,
                'wording': True,
            },
            json.loads(completed.stdout),
        )

    def test_2v2_pill_status_immunity_blocks_bandage_save(self):
        package = load_mod(str(ROOT / 'mods' / 'Vanilla Cards.gtnmod'))
        self.assertEqual([], package.errors)
        pill_def = next(card.to_card_def() for card in package.cards if card.id == 'Pill')
        previous = CARD_DEFS.get('Pill')
        CARD_DEFS['Pill'] = pill_def
        try:
            engine = GameEngine2v2()
            engine.phase = 'action'
            engine.current_player = 0
            for player in engine.players:
                player.health = 100
                player.deck = []
                player.hand = []
                player.discard = []
                player.exile = []
                player.equipment = []
            # 攻击者把药丸装到目标（玩家2）身上：目标获得状态免疫。
            pill = EquipmentInstance(CardInstance('Pill'), 0)
            pill.effect_target = 2
            engine.players[0].equipment.append(pill)
            engine.players[2].custom_statuses['status_immune'] = 1
            # 目标此前反制获得了绷带；致死攻击落下时，
            # 死亡结算必须先于装备清除——绷带应被免疫阻止。
            engine.players[2].bandage_active = True
            engine.players[2].health = 6
            attack = CardInstance('Bone')
            engine.players[0].hand.append(attack)

            result = engine.play_card(
                0,
                attack.instance_id,
                2,
                {'target_player': 2, 'target_player_id': 2, 'target_id': 2},
            )

            self.assertTrue(result.get('success'), result)
            saved = engine.players[2]
            # 状态免疫阻止绷带：目标死亡（引擎惯例保持负血量）。
            self.assertLessEqual(saved.health, 0)
            self.assertFalse(saved.bandage_active)
            self.assertFalse(saved.bandage_death_pending)
            # 指向已死亡玩家的装备随之移除。
            self.assertEqual([], engine.players[0].equipment)
        finally:
            if previous is None:
                CARD_DEFS.pop('Pill', None)
            else:
                CARD_DEFS['Pill'] = previous

    def test_2v2_bandage_still_saves_when_not_status_immune(self):
        engine = GameEngine2v2()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.deck = []
            player.hand = []
            player.discard = []
            player.exile = []
            player.equipment = []
        engine.players[2].bandage_active = True
        engine.players[2].health = 6
        engine.players[2].equipment.append(EquipmentInstance(CardInstance('Disc'), 2))
        attack = CardInstance('Bone')
        engine.players[0].hand.append(attack)

        result = engine.play_card(
            0,
            attack.instance_id,
            2,
            {'target_player': 2, 'target_player_id': 2, 'target_id': 2},
        )

        self.assertTrue(result.get('success'), result)
        saved = engine.players[2]
        self.assertEqual(1, saved.health)
        self.assertTrue(saved.invincible)
        self.assertTrue(saved.bandage_death_pending)
        # 被绷带救回：装备不被死亡清除。
        self.assertEqual(1, len(saved.equipment))

    def test_2v2_attack_counter_only_target_can_respond(self):
        engine = GameEngine2v2()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.deck = []
            player.hand = []
            player.discard = []
            player.exile = []
            player.equipment = []
        # 三名非行动玩家（含攻击者队友）都持有泡泡（thorn 响应牌）。
        bubbles = {}
        for responder_id in (1, 2, 3):
            bubble = CardInstance('Bubble')
            engine.players[responder_id].hand.append(bubble)
            bubbles[responder_id] = bubble
        attack = CardInstance('Bone')
        engine.players[0].hand.append(attack)

        result = engine.play_card(
            0,
            attack.instance_id,
            2,
            {'target_player': 2, 'target_player_id': 2, 'target_id': 2},
        )

        self.assertTrue(result.get('success'), result)
        self.assertTrue(result.get('needs_response'), result)
        pending = engine.pending_response
        self.assertIsNotNone(pending)
        responder_ids = {
            entry.get('responder_id')
            for entry in (pending.get('counter_cards') or [])
        }
        # 攻击牌只有被攻击者本人（玩家2）在反制范围内。
        self.assertEqual({2}, responder_ids)

        # 攻击者的队友（玩家1）无法反制。
        rejected_teammate = engine.handle_response(1, bubbles[1].instance_id)
        self.assertFalse(rejected_teammate.get('success'), rejected_teammate)
        # 未被攻击的另一个敌人（玩家3）也无法反制。
        rejected_bystander = engine.handle_response(3, bubbles[3].instance_id)
        self.assertFalse(rejected_bystander.get('success'), rejected_bystander)
        # 拒绝不影响待反制状态。
        self.assertIsNotNone(engine.pending_response)

        # 被攻击者本人可以反制。
        accepted = engine.handle_response(2, bubbles[2].instance_id)
        self.assertTrue(accepted.get('success'), accepted)

    def test_2v2_skill_counter_only_enemies_can_respond(self):
        engine = GameEngine2v2()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.health = 100
            player.deck = []
            player.hand = []
            player.discard = []
            player.exile = []
            player.equipment = []
        # 行动方队友（玩家1）与两名敌人（玩家2、3）都持有
        # 魔法邪眼（bloom 响应牌，文案为“敌方使用技能牌”）。
        nazars = {}
        for responder_id in (1, 2, 3):
            nazar = CardInstance('MagicNazar')
            engine.players[responder_id].hand.append(nazar)
            nazars[responder_id] = nazar
        skill = CardInstance('Rose')
        engine.players[0].hand.append(skill)

        result = engine.play_card(
            0,
            skill.instance_id,
            0,
            {'target_player': 0, 'target_player_id': 0, 'target_id': 0},
        )

        self.assertTrue(result.get('success'), result)
        self.assertTrue(result.get('needs_response'), result)
        pending = engine.pending_response
        self.assertIsNotNone(pending)
        responder_ids = {
            entry.get('responder_id')
            for entry in (pending.get('counter_cards') or [])
        }
        # 技能牌只有敌方（玩家2、3）在反制范围内；队友（玩家1）不在。
        self.assertEqual({2, 3}, responder_ids)

        # 攻击者的队友无法反制。
        rejected_teammate = engine.handle_response(1, nazars[1].instance_id)
        self.assertFalse(rejected_teammate.get('success'), rejected_teammate)
        self.assertIsNotNone(engine.pending_response)

        # 敌方玩家可以反制。
        accepted = engine.handle_response(3, nazars[3].instance_id)
        self.assertTrue(accepted.get('success'), accepted)

    def test_2v2_dead_teammate_turn_does_not_expire_bandage(self):
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
        self.assertFalse(engine.game_over)
        self.assertEqual(pending.health, 1)
        self.assertEqual(engine.current_player, 3)

    def test_2v2_stunned_owner_turn_still_expires_bandage(self):
        engine = GameEngine2v2()
        engine.phase = 'action'
        engine.round_num = 2
        engine.turn_order = [0, 2, 1, 3]
        engine.turn_index = 3
        engine.current_player = 3
        for player in engine.players:
            player.health = 100
            player.deck = []
            player.hand = []
            player.discard = []
        pending = engine.players[0]
        pending.invincible = True
        pending.bandage_death_pending = True
        pending.bandage_trigger_boundary_id = 0
        pending.skip_turn = 1

        engine._end_player_turn(3)

        self.assertEqual(pending.health, 0)
        self.assertEqual(engine.current_player, 2)
        self.assertEqual(pending.skip_turn, 0)
        self.assertFalse(engine.game_over)

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
