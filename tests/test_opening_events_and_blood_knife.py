import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from cards import CARD_DEFS, CardDef, CardInstance
from card_i18n import CARD_I18N, OPENING_EVENT_I18N
from game_engine import GameEngine, PlayerState
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod


def make_card_def(def_id, card_type, *, flags=None, response_trigger='', cost_e=0, cost_m=0):
    return CardDef(
        def_id,
        def_id,
        def_id,
        cost_e,
        cost_m,
        card_type,
        1,
        'Common',
        '',
        '',
        flags=set(flags or []),
        response_trigger=response_trigger,
    )


class OpeningEventsAndBloodKnifeTests(unittest.TestCase):
    def setUp(self):
        self.test_ids = {
            'test:light_attack',
            'test:light_skill',
            'test:blood_knife',
            'test:order_a',
            'test:order_b',
            'test:order_hidden',
            'test:self_attack',
            'test:thorn_counter',
            'test:magic_cost',
            'test:copy_petal',
            'test:hit_petal',
            'test:fission_petal',
        }
        self.previous_defs = {key: CARD_DEFS.get(key) for key in self.test_ids}
        CARD_DEFS['test:light_attack'] = make_card_def('test:light_attack', 'thorn')
        CARD_DEFS['test:light_skill'] = make_card_def('test:light_skill', 'bloom')
        CARD_DEFS['test:blood_knife'] = make_card_def('test:blood_knife', 'bloom')
        CARD_DEFS['test:order_a'] = make_card_def('test:order_a', 'bloom')
        CARD_DEFS['test:order_b'] = make_card_def('test:order_b', 'bloom')
        CARD_DEFS['test:order_hidden'] = make_card_def(
            'test:order_hidden',
            'bloom',
            flags={'sublime'},
        )
        CARD_DEFS['test:self_attack'] = make_card_def(
            'test:self_attack',
            'thorn',
            flags={'self_target'},
        )
        CARD_DEFS['test:thorn_counter'] = make_card_def(
            'test:thorn_counter',
            'guard',
            response_trigger='thorn',
        )
        CARD_DEFS['test:magic_cost'] = make_card_def(
            'test:magic_cost',
            'bloom',
            cost_m=1,
        )
        CARD_DEFS['test:copy_petal'] = make_card_def(
            'test:copy_petal',
            'thorn',
            flags={'copy'},
        )
        CARD_DEFS['test:copy_petal'].copy_count = 1
        CARD_DEFS['test:hit_petal'] = make_card_def('test:hit_petal', 'thorn')
        CARD_DEFS['test:hit_petal'].hits = 3
        CARD_DEFS['test:fission_petal'] = make_card_def('test:fission_petal', 'thorn')
        CARD_DEFS['test:fission_petal'].fission_level = 4

    def tearDown(self):
        for key, old_value in self.previous_defs.items():
            if old_value is None:
                CARD_DEFS.pop(key, None)
            else:
                CARD_DEFS[key] = old_value

    def test_light_baptism_only_converts_attack_cards(self):
        engine = GameEngine()
        engine.players[0].deck = [
            CardInstance('test:light_attack'),
            CardInstance('test:light_skill'),
            CardInstance('Light'),
        ]
        engine.opening_event_picks[0] = 3
        engine.opening_event_sub_choices[0] = {
            'convert_def_ids': ['test:light_attack', 'test:light_skill', 'Light'],
        }

        engine._apply_opening_event(0)

        self.assertEqual(
            [card.def_id for card in engine.players[0].deck],
            ['Light', 'test:light_skill', 'Light'],
        )
        converted_lights = [
            card for card in engine.players[0].deck
            if card.def_id == 'Light'
        ]
        self.assertEqual(len(converted_lights), 2)
        self.assertTrue(all({'sprout', 'symbiosis'} <= card.flags for card in converted_lights))
        self.assertIn('最多5张攻击牌', engine.OPENING_EVENTS[3]['desc'])

    def test_light_baptism_frontends_only_offer_attack_cards(self):
        root = Path(__file__).resolve().parents[1]
        game_js = (root / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')

        self.assertGreaterEqual(
            game_js.count("return def && def.card_type === 'thorn';"),
            2,
        )

    def test_multi_petal_adds_three_dust_cards(self):
        engine = GameEngine()
        engine.opening_event_picks[0] = 9
        engine.players[0].deck = []

        engine._apply_opening_event(0)

        dust_cards = [card for card in engine.players[0].deck if card.def_id == 'Dust']
        self.assertEqual(len(dust_cards), 3)
        self.assertTrue(all('exile' in card.flags for card in dust_cards))

    def test_multi_petal_expands_copy_hit_and_fission_petals_once(self):
        engine = GameEngine()
        engine.opening_event_picks[0] = 9

        copy_petal = CardInstance('test:copy_petal')
        engine._apply_setup_modifiers_to_card(0, copy_petal)
        self.assertIn('multi_petal', copy_petal.setup_modifiers)
        self.assertEqual(copy_petal.extra_hits, 0)
        engine.players[0].hand = [copy_petal]
        engine._handle_card_enter_hand(0, copy_petal)
        self.assertEqual(len(engine.players[0].hand), 3)

        hit_petal = CardInstance('test:hit_petal')
        engine._apply_setup_modifiers_to_card(0, hit_petal)
        self.assertEqual(hit_petal.extra_hits, 1)

        fission_petal = CardInstance('test:fission_petal')
        engine._apply_setup_modifiers_to_card(0, fission_petal)
        self.assertEqual(fission_petal.fission_level, 5)

    def test_magic_acceleration_accepts_string_event_id(self):
        engine = GameEngine()
        engine.opening_event_picks[0] = '10'

        engine._apply_opening_event(0)

        self.assertEqual(engine.opening_event_picks[0], 10)
        self.assertEqual(engine.players[0].custom_vars.get('setup_magic_acceleration'), 1)

    def test_mimic_copying_symbiosis_mimic_marks_everlasting_mana_pool(self):
        engine = GameEngine()
        engine.opening_event_picks[0] = '10'
        engine._apply_opening_event(0)
        source = CardInstance('Mimic')
        target = CardInstance('Mimic')
        target.instance_flags.add('symbiosis')
        engine.players[0].hand = [target]

        engine._effect_mimic(0, source, {'target_instance_id': target.instance_id})

        self.assertEqual(
            engine.players[0].custom_vars.get('achievement_creative_mode_mana_pool'),
            1,
        )

    def test_mana_pool_requires_symbiosis_on_the_copied_mimic(self):
        engine = GameEngine()
        engine.opening_event_picks[0] = 10
        engine._apply_opening_event(0)
        source = CardInstance('Mimic')
        target = CardInstance('Mimic')
        engine.players[0].hand = [target]

        engine._effect_mimic(0, source, {'target_instance_id': target.instance_id})

        self.assertIsNone(
            engine.players[0].custom_vars.get('achievement_creative_mode_mana_pool')
        )

    def test_floral_arrangement_reorders_the_full_visible_deck(self):
        engine = GameEngine()
        engine.players[0].deck = [
            CardInstance('test:order_a'),
            CardInstance('test:order_hidden'),
            CardInstance('test:order_b'),
            CardInstance('test:order_a'),
        ]
        engine.opening_event_picks[0] = 11
        engine.opening_event_sub_choices[0] = {
            'deck_order_def_ids': [
                'test:order_b',
                'test:order_a',
                'test:order_a',
            ],
        }

        engine._apply_opening_event(0)

        self.assertEqual(
            [card.def_id for card in engine.players[0].deck],
            [
                'test:order_b',
                'test:order_hidden',
                'test:order_a',
                'test:order_a',
            ],
        )

    def test_flame_omen_applies_three_fire_and_stacks_through_status_immunity(self):
        engine = GameEngine()
        engine.opening_event_picks[0] = 4
        engine.players[1].fire = 2
        engine.players[1].custom_statuses['status_immune'] = 1

        engine._apply_opening_event(0)

        self.assertEqual(engine.players[1].fire, 5)
        restored = PlayerState.from_dict(engine.players[1].to_dict())
        self.assertEqual(restored.fire, 5)
        self.assertEqual(GameEngine.OPENING_EVENTS[4]['desc'], '开局对随机1名敌方玩家施加3层灼烧')
        for language in ('zh', 'en', 'fr', 'ja'):
            description = OPENING_EVENT_I18N[4]['desc'][language]
            self.assertIn('3', description, language)
            self.assertIn('1', description, language)
            self.assertNotIn('4', description, language)

    def test_flame_omen_applies_to_one_random_2v2_enemy_and_not_the_ally(self):
        engine = GameEngine2v2()
        engine.opening_event_picks[0] = 4
        engine.players[1].fire = 7
        engine.players[2].fire = 1
        engine.players[3].fire = 2
        engine.players[3].custom_statuses['status_immune'] = 1

        engine._apply_opening_event(0)

        fire = [player.fire for player in engine.players]
        self.assertEqual(fire[:2], [0, 7])
        self.assertEqual(sorted((fire[2] - 1, fire[3] - 2)), [0, 3])
        self.assertTrue(any('随机敌方+3灼烧' in line for line in engine.log))

    def test_energy_surge_banks_turn_end_elixir_without_backlash(self):
        engine = GameEngine()
        engine.opening_event_picks[0] = '6'
        player = engine.players[0]
        player.elixir = 5
        player.health = 100

        engine._apply_energy_surge_turn_end(0)

        self.assertEqual(player.health, 100)
        self.assertEqual(
            player.custom_vars.get(GameEngine.ENERGY_SURGE_PENDING_KEY), 2
        )
        self.assertFalse(any('反噬' in line for line in engine.log))
        self.assertTrue(any('剩余5E，下回合额外回复2E' in line for line in engine.log))

    def test_energy_surge_banks_by_actual_turn_end_elixir(self):
        engine = GameEngine()
        engine.opening_event_picks[0] = 6
        engine.first_player = 0
        engine.current_player = 0
        engine.phase = 'action'
        player = engine.players[0]
        player.health = 100
        player.elixir = 3
        engine._start_player_turn = lambda _player_id: None

        engine._end_player_turn(0)

        self.assertEqual(player.health, 100)
        self.assertEqual(
            player.custom_vars.get(GameEngine.ENERGY_SURGE_PENDING_KEY), 1
        )

    def test_energy_surge_grants_banked_elixir_at_next_turn_start(self):
        engine = GameEngine()
        engine.round_num = 2
        engine.opening_event_picks[0] = 6
        player = engine.players[0]
        player.elixir = 5
        engine._apply_energy_surge_turn_end(0)

        # 对手回合里用反制牌把 E 花光，不会改变已经记好的账。
        player.elixir = 0
        engine._apply_turn_start_effects(0)

        self.assertEqual(player.elixir, 7)
        self.assertEqual(
            player.custom_vars.get(GameEngine.ENERGY_SURGE_PENDING_KEY), 0
        )

    def test_energy_surge_recovery_still_respects_the_elixir_cap(self):
        engine = GameEngine()
        engine.round_num = 2
        engine.opening_event_picks[0] = 6
        player = engine.players[0]
        player.max_elixir = 10
        player.elixir = 10
        engine._apply_energy_surge_turn_end(0)

        player.elixir = 3
        engine._apply_turn_start_effects(0)

        self.assertEqual(player.elixir, player.max_elixir)
        self.assertEqual(player.elixir, 10)

    def test_energy_surge_matches_two_vs_two_banking(self):
        engine = GameEngine2v2()
        engine.round_num = 2
        engine.opening_event_picks[0] = 6
        player = engine.players[0]
        player.elixir = 4
        player.health = 100

        engine._apply_energy_surge_turn_end(0)

        self.assertEqual([p.health for p in engine.players], [100, 100, 100, 100])
        self.assertEqual(
            player.custom_vars.get(GameEngine.ENERGY_SURGE_PENDING_KEY), 2
        )

        player.elixir = 0
        engine._apply_turn_start_effects_2v2(0)
        self.assertEqual(player.elixir, 7)

    def test_energy_surge_text_matches_the_authoritative_rule(self):
        expected = '回合结束时每剩余2[[icon:E]]，下回合开始多回复1[[icon:E]]'
        self.assertEqual(GameEngine.OPENING_EVENTS[6]['desc'], expected)
        self.assertEqual(OPENING_EVENT_I18N[6]['desc']['zh'], expected)
        for language in ('zh', 'en', 'fr', 'ja'):
            description = OPENING_EVENT_I18N[6]['desc'][language]
            self.assertIn('2', description, language)
            self.assertIn('1', description, language)
            self.assertIn('[[icon:E]]', description, language)
            self.assertNotIn('[[icon:D]]', description, language)

    def test_floral_arrangement_exposes_own_deck_order_only_to_the_owner(self):
        engine = GameEngine()
        engine.opening_event_picks[0] = 11
        engine.players[0].deck = [
            CardInstance('test:order_a'),
            CardInstance('test:order_b'),
        ]
        engine.players[1].deck = [CardInstance('test:order_b')]

        own_state = engine.get_public_state(0)
        other_state = engine.get_public_state(1)

        self.assertTrue(own_state['you'].get('deck_order_visible'))
        self.assertEqual(
            [card['def_id'] for card in own_state['you']['deck']],
            ['test:order_a', 'test:order_b'],
        )
        self.assertNotIn('deck_order_visible', other_state['you'])
        self.assertNotIn('deck_order_visible', own_state['opponent'])
        self.assertNotIn('deck_order_visible', other_state['opponent'])

    def test_floral_arrangement_visibility_follows_live_deck_order(self):
        engine = GameEngine()
        engine.opening_event_picks[0] = 11
        engine.players[0].deck = [
            CardInstance('test:order_a'),
            CardInstance('test:order_b'),
        ]
        engine.get_public_state(0)

        engine.players[0].deck.reverse()
        state = engine.get_public_state(0)

        self.assertEqual(
            [card['def_id'] for card in state['you']['deck']],
            ['test:order_b', 'test:order_a'],
        )

    def test_floral_arrangement_exposes_own_deck_order_in_two_vs_two(self):
        engine = GameEngine2v2()
        engine.opening_event_picks[0] = 11
        engine.players[0].deck = [CardInstance('test:order_a')]

        own_state = engine.get_public_state(0)
        mate_state = engine.get_public_state(1)

        self.assertTrue(own_state['you'].get('deck_order_visible'))
        self.assertNotIn('deck_order_visible', mate_state['you'])

    def test_floral_arrangement_text_mentions_persistent_visibility(self):
        expected = '调整自己抽牌堆的顺序；本局始终可见抽牌堆顺序'
        self.assertEqual(GameEngine.OPENING_EVENTS[11]['desc'], expected)
        self.assertEqual(OPENING_EVENT_I18N[11]['desc']['zh'], expected)
        # “该顺序”会被误读为开局调整好的那一次顺序；描述必须指向抽牌堆本身。
        self.assertNotIn('该顺序', expected)
        self.assertIn('抽牌堆顺序', expected)
        self.assertIn('always', OPENING_EVENT_I18N[11]['desc']['en'])
        for language in ('zh', 'en', 'fr', 'ja'):
            self.assertTrue(
                OPENING_EVENT_I18N[11]['desc'][language].strip(), language
            )

    def test_floral_arrangement_frontend_uses_the_lightweight_flag(self):
        game_js = (
            Path(__file__).resolve().parents[1] / 'static' / 'js' / 'game.js'
        ).read_text(encoding='utf-8')
        self.assertIn('deck_order_visible', game_js)
        self.assertIn('ownDeckOrderVisible', game_js)

    def test_equal_suffering_hits_other_players_at_turn_end(self):
        engine = GameEngine()
        engine.opening_event_picks[0] = 12
        engine.players[0].health = 100
        engine.players[1].health = 100

        engine._apply_equal_suffering_turn_end(0)

        self.assertEqual(engine.players[0].health, 95)
        self.assertEqual(engine.players[1].health, 92)

    def test_equal_suffering_finishes_all_damage_before_draw_check(self):
        engine = GameEngine()
        engine.opening_event_picks[0] = 12
        engine.players[0].health = 5
        engine.players[1].health = 8

        engine._apply_equal_suffering_turn_end(0)

        self.assertEqual([player.health for player in engine.players], [0, 0])
        self.assertTrue(engine.game_over)
        self.assertEqual(engine.winner, -1)

    def test_equal_suffering_and_leaf_fallback_text_matches_current_rules(self):
        expected = '自己回合结束时，对自己造成5[[icon:D]]，并对每名其他可选中玩家造成8[[icon:D]]'
        self.assertEqual(GameEngine.OPENING_EVENTS[12]['desc'], expected)
        self.assertEqual(OPENING_EVENT_I18N[12]['desc']['zh'], expected)
        leaf_text = CARD_DEFS['Leaf'].effect_text.replace('[[icon:H]]', 'H')
        magic_leaf_text = CARD_DEFS['MagicLeaf'].effect_text.replace('[[icon:M]]', 'M').replace('[[icon:D]]', 'D')
        self.assertIn('装备拥有者回合开始时，回复目标1H', leaf_text)
        self.assertIn('可花费3M', magic_leaf_text)
        self.assertIn('对其造成8D', magic_leaf_text)
        self.assertIn('装备拥有者回合开始时，回复目标1H', CARD_I18N['Leaf']['effect']['zh'])
        self.assertIn('可花费3M', CARD_I18N['MagicLeaf']['effect']['zh'])

        vanilla_path = Path(__file__).resolve().parents[1] / 'mods' / 'Vanilla Cards.gtnmod'
        with zipfile.ZipFile(vanilla_path) as archive:
            english = json.loads(archive.read('locales/en.json'))['cards']
            french = json.loads(archive.read('locales/fr.json'))['cards']
            japanese = json.loads(archive.read('locales/ja.json'))['cards']
        for localized in (english, french, japanese):
            self.assertNotIn('12[[icon:D]]', localized['vanilla:magicleaf']['effect_text'])
            self.assertIn('8[[icon:D]]', localized['vanilla:magicleaf']['effect_text'])
        self.assertIn("equipment owner's turn", english['vanilla:leaf']['effect_text'])
        self.assertIn("propriétaire de l'équipement", french['vanilla:leaf']['effect_text'])
        self.assertIn('装備の所有者', japanese['vanilla:leaf']['effect_text'])

    def test_equal_suffering_uses_team_damage_in_two_vs_two(self):
        engine = GameEngine2v2()
        engine.opening_event_picks[0] = 12
        for player in engine.players:
            player.health = 100

        engine._apply_equal_suffering_turn_end(0)

        self.assertEqual([player.health for player in engine.players], [95, 92, 92, 92])

    def test_blood_knife_recovers_for_actual_damage_dealt(self):
        # The mechanic now lives in the package data, so drive it through the
        # real play path instead of calling the retired engine atom.
        package = Path(__file__).resolve().parents[1] / 'mods' / 'Bio Cards Addition.gtnmod'
        mod = load_mod(str(package))
        previous = CARD_DEFS.get('BloodKnife')
        CARD_DEFS['BloodKnife'] = next(
            item for item in mod.cards if item.id == 'BloodKnife'
        ).to_card_def()
        try:
            engine = GameEngine()
            engine.phase = 'action'
            engine.current_player = 0
            player = engine.players[0]
            player.hand = []
            player.deck = []
            player.discard = []
            player.health = 100
            player.max_health = 100
            player.elixir = 0
            card = CardInstance('BloodKnife')
            player.hand.append(card)

            result = engine.play_card(0, card.instance_id, {})

            self.assertTrue(result.get('success'), result)
            self.assertEqual(player.health, 93)
            self.assertEqual(player.elixir, 2)
            self.assertIn(card, player.hand)
        finally:
            if previous is None:
                CARD_DEFS.pop('BloodKnife', None)
            else:
                CARD_DEFS['BloodKnife'] = previous

    def test_blood_knife_mod_data_matches_new_rules(self):
        archive = Path(__file__).resolve().parents[1] / 'mods' / 'Bio Cards Addition.gtnmod'
        with zipfile.ZipFile(archive) as package:
            mod_data = json.loads(package.read('mod.json').decode('utf-8'))
        card = next(
            item for item in mod_data['registries']['cards']
            if item.get('id') == 'bio:blood_knife'
        )

        self.assertEqual(card['cost_e'], 0)
        self.assertEqual(card['card_type'], 'bloom')
        # 数据标记约定（engine_runtime_support.py 顶部说明，重构第 5 轮起）：
        # 每张卡在 flags 里声明 mark:<card id>，通用 helper 用 _card_has_mark 查它。
        # 它是运行时挂钩用的内部标记，不算卡面标签，所以断言时先把它摘掉。
        flags = set(card['flags'])
        self.assertEqual({flag for flag in flags if not flag.startswith('mark:')},
                         {'self_only', 'symbiosis'})
        self.assertIn('mark:bio:blood_knife', flags)
        self.assertEqual(
            card['effect_text'],
            '对自己造成7[[icon:electric_damage]]；每造成3[[icon:electric_damage]]，回复自己1[[icon:E]]；若实际回复至少1[[icon:E]]，此牌回到手中',
        )

    def test_blood_sugar_does_not_have_self_target(self):
        # Workbook 14 moved Blood Sugar (and RNA/Magic RNA) into the Bio DLC package.
        archive = Path(__file__).resolve().parents[1] / 'mods' / 'Bio Cards DLC.gtnmod'
        with zipfile.ZipFile(archive) as package:
            mod_data = json.loads(package.read('mod.json').decode('utf-8'))
        card = next(
            item for item in mod_data['registries']['cards']
            if item.get('id') == 'bio:blood_sugar'
        )

        self.assertNotIn('self_target', card.get('flags', []))

    def test_self_targeted_attack_does_not_offer_opponent_response(self):
        engine = GameEngine()
        card = CardInstance('test:self_attack')
        engine.players[1].hand = [CardInstance('test:thorn_counter')]

        result = engine._check_card_response_after_choice(
            0,
            card,
            {'target_player': 0, 'target_player_id': 0, 'target_id': 0},
        )

        self.assertIsNone(result)
        self.assertIsNone(engine.pending_response)

    def test_enemy_targeted_attack_still_offers_response(self):
        engine = GameEngine()
        card = CardInstance('test:self_attack')
        engine.players[1].hand = [CardInstance('test:thorn_counter')]

        result = engine._check_card_response_after_choice(
            0,
            card,
            {'target_player': 1, 'target_player_id': 1, 'target_id': 1},
        )

        self.assertTrue(result and result.get('needs_response'))
        self.assertIsNotNone(engine.pending_response)

    def test_two_vs_two_self_targeted_attack_offers_no_response(self):
        engine = GameEngine2v2()
        card = CardInstance('test:self_attack')
        engine.players[2].hand = [CardInstance('test:thorn_counter')]
        engine.players[3].hand = [CardInstance('test:thorn_counter')]

        result = engine._check_card_response_after_choice(
            0,
            card,
            {'target_player': 0, 'target_player_id': 0, 'target_id': 0},
        )

        self.assertIsNone(result)
        self.assertIsNone(engine.pending_response)

    def test_foresight_does_not_disable_magic_block(self):
        for engine_type in (GameEngine, GameEngine2v2):
            for status_key in ('magic_blocked', 'troll_cards:magic_blocked'):
                with self.subTest(engine=engine_type.__name__, status=status_key):
                    engine = engine_type()
                    player = engine.players[0]
                    player.hand = [CardInstance('test:magic_cost')]
                    player.deck = [CardInstance('test:light_skill') for _ in range(8)]
                    player.magic = 10
                    player.foresight = 1
                    player.custom_statuses[status_key] = 1
                    engine.round_num = 2
                    engine.phase = 'draw'

                    engine._start_player_turn(0)
                    self.assertEqual(engine.pending_choice.get('choice_type'), 'foresight_replace')
                    engine.resolve_choice(0, {'selected_instance_ids': []})

                    playable, reason = engine.can_play_card(0, player.hand[0])
                    self.assertFalse(playable)
                    self.assertIn('魔力消耗', reason)
                    self.assertEqual(player.custom_statuses.get(status_key), 1)

    def test_charge_decays_at_turn_end(self):
        engine = GameEngine()
        card = CardInstance('test:light_skill')
        card.charge_value = 2
        card.instance_flags.add('charge')
        engine.players[0].hand = [card]

        engine._decay_ocean_card_charge_turn_end(0)
        self.assertEqual(card.charge_value, 1)
        self.assertIn('charge', card.instance_flags)

        engine._decay_ocean_card_charge_turn_end(0)
        self.assertEqual(card.charge_value, 0)
        self.assertNotIn('charge', card.instance_flags)


if __name__ == '__main__':
    unittest.main()
