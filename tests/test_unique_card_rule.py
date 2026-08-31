import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from cards import (
    CARD_DEFS,
    CardDef,
    CardInstance,
    create_random_weighted_deck_def_ids,
)
from game_engine import EquipmentInstance, GameEngine
from game_engine_2v2 import GameEngine2v2
from formal_logic_runtime import start_formal_logic_actions
from mod_runtime_v2 import run_v2_event


ROOT = Path(__file__).resolve().parents[1]
UNIQUE_ID = 'test:unique-rule-card'
VOID_ID = 'test:unique-rule-void'
NORMAL_ID = 'test:unique-rule-normal'


def make_def(def_id, *, flags=(), legacy_id='', count=4):
    card_def = CardDef(
        def_id,
        def_id,
        def_id,
        1,
        0,
        'bloom',
        count,
        'Common',
        '',
        '',
        flags=set(flags),
    )
    card_def.legacy_id = legacy_id
    card_def.v2_resource = {
        'id': 'void:void' if def_id == VOID_ID else def_id,
        'legacy_id': legacy_id,
    }
    return card_def


class UniqueCardRuleTests(unittest.TestCase):
    def setUp(self):
        self.test_defs = {
            UNIQUE_ID: make_def(UNIQUE_ID, flags={'unique'}),
            VOID_ID: make_def(
                VOID_ID,
                flags={'self_only', 'infinite_exclude'},
                legacy_id='Void',
                count=0,
            ),
            NORMAL_ID: make_def(NORMAL_ID),
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
    def prepare_engine(engine_class=GameEngine):
        engine = engine_class()
        for player in engine.players:
            player.hand = []
            player.deck = []
            player.discard = []
            player.exile = []
            player.equipment = []
            player.elixir = 50
            player.magic = 50
        return engine

    def test_bandage_package_marks_the_card_unique(self):
        package = ROOT / 'mods' / 'Vanilla Cards.gtnmod'
        with zipfile.ZipFile(package) as archive:
            document = json.loads(archive.read('mod.json').decode('utf-8'))
        bandage = next(
            card
            for card in document['registries']['cards']
            if card.get('id') == 'vanilla:bandage'
        )
        self.assertIn('exile', bandage['flags'])
        self.assertIn('unique', bandage['flags'])

    def test_owned_unique_card_is_removed_from_later_draft_options(self):
        for engine_class in (GameEngine, GameEngine2v2):
            with self.subTest(engine=engine_class.__name__):
                engine = self.prepare_engine(engine_class)
                engine.phase = 'draft'
                engine.player_draft_started[0] = True
                engine.draft_pool = [CardInstance(UNIQUE_ID), CardInstance(NORMAL_ID)]
                engine.draft_picks[0] = [UNIQUE_ID]
                engine.draft_type_order = ['bloom', 'bloom']

                engine._generate_draft_options_for_player(0)

                self.assertNotIn(
                    UNIQUE_ID,
                    {card.def_id for card in engine.draft_options[0]},
                )

    def test_stale_or_forged_duplicate_unique_draft_pick_is_rejected(self):
        for engine_class in (GameEngine, GameEngine2v2):
            with self.subTest(engine=engine_class.__name__):
                engine = self.prepare_engine(engine_class)
                engine.phase = 'draft'
                engine.player_draft_started[0] = True
                engine.draft_picks[0] = [UNIQUE_ID]
                engine.draft_options[0] = [CardInstance(UNIQUE_ID)]
                engine.draft_type_order = ['bloom', 'bloom']

                result = engine.draft_pick(0, UNIQUE_ID)

                if isinstance(result, dict):
                    self.assertFalse(result.get('success'), result)
                else:
                    self.assertFalse(result)
                self.assertEqual([UNIQUE_ID], engine.draft_picks[0])

    def test_mimic_keeps_unique_copy_and_adds_void_without_exiling_either(self):
        for engine_class in (GameEngine, GameEngine2v2):
            with self.subTest(engine=engine_class.__name__):
                engine = self.prepare_engine(engine_class)
                player = engine.players[0]
                target = CardInstance(UNIQUE_ID)
                mimic = CardInstance('Mimic')
                player.hand = [target]

                engine._effect_mimic(
                    0,
                    mimic,
                    {'target_instance_id': target.instance_id},
                )

                self.assertEqual(
                    2,
                    sum(card.def_id == UNIQUE_ID for card in player.hand),
                )
                expected_void_id = engine._void_resolve_card_def_id('void:void')
                self.assertEqual([expected_void_id], [card.def_id for card in player.deck])
                self.assertFalse(any(card.def_id == UNIQUE_ID for card in player.exile))

    def test_forced_copy_detects_unique_card_in_every_owned_zone(self):
        for zone_name in ('hand', 'deck', 'discard', 'exile', 'equipment'):
            with self.subTest(zone=zone_name):
                engine = self.prepare_engine()
                player = engine.players[0]
                original = CardInstance(UNIQUE_ID)
                if zone_name == 'equipment':
                    player.equipment = [EquipmentInstance(original, 0)]
                else:
                    getattr(player, zone_name).append(original)
                copied = original.copy()

                engine._add_forced_copy_to_hand(0, copied)

                self.assertIn(copied, player.hand)
                expected_void_id = engine._void_resolve_card_def_id('void:void')
                self.assertEqual(
                    [expected_void_id],
                    [card.def_id for card in player.deck if card.def_id == expected_void_id],
                )
                self.assertNotIn(original, player.exile if zone_name != 'exile' else [])

    def test_normal_duplicate_generation_is_rejected_without_void_or_exile(self):
        engine = self.prepare_engine()
        player = engine.players[0]
        original = CardInstance(UNIQUE_ID)
        generated = CardInstance(UNIQUE_ID)
        player.discard.append(original)
        player.hand.append(generated)

        accepted = engine._enforce_unique_cards_for_player(0, preferred_card=generated)

        self.assertFalse(accepted)
        self.assertNotIn(generated, player.hand)
        self.assertIn(original, player.discard)
        self.assertEqual([], player.exile)
        self.assertFalse(any(card.def_id == VOID_ID for card in player.deck))

    def test_normal_hand_generation_rejects_duplicate_before_enter_hand_event(self):
        engine = self.prepare_engine()
        player = engine.players[0]
        player.discard.append(CardInstance(UNIQUE_ID))
        entered = []
        player._enter_hand_callback = lambda player_id, card: entered.append((player_id, card.def_id))

        engine._atomic_give_card_to_hand(
            0,
            None,
            {'target': 'self', 'card': UNIQUE_ID},
            '',
            None,
            {},
        )

        self.assertEqual([], entered)
        self.assertFalse(any(card.def_id == UNIQUE_ID for card in player.hand))
        self.assertEqual(1, sum(card.def_id == UNIQUE_ID for card in player.discard))

    def test_v2_move_preserves_forced_duplicates_but_create_rejects_a_new_one(self):
        engine = self.prepare_engine()
        player = engine.players[0]
        original = CardInstance(UNIQUE_ID)
        forced_copy = original.copy()
        player.discard.append(original)
        player.hand.append(forced_copy)
        context = {'source_player': 0, 'card': forced_copy}

        moved = run_v2_event(
            engine,
            context,
            {'steps': [{'op': 'move_card', 'card': 'current_card', 'owner': 'source', 'to': 'deck'}]},
        )

        self.assertTrue(moved.get('success'), moved)
        self.assertIn(original, player.discard)
        self.assertIn(forced_copy, player.deck)
        self.assertEqual(2, sum(card.def_id == UNIQUE_ID for card in [*player.deck, *player.discard]))

        entered = []
        player._enter_hand_callback = lambda player_id, card: entered.append((player_id, card.def_id))
        created = run_v2_event(
            engine,
            context,
            {'steps': [{'op': 'create_card', 'card_id': UNIQUE_ID, 'target': 'source', 'to': 'hand'}]},
        )

        self.assertTrue(created.get('success'), created)
        self.assertEqual([], entered)
        self.assertFalse(any(card.def_id == UNIQUE_ID for card in player.hand))
        self.assertEqual(2, sum(card.def_id == UNIQUE_ID for card in [*player.deck, *player.discard]))

    def test_formal_logic_forced_snapshot_copy_uses_unique_penalty(self):
        engine = self.prepare_engine()
        player = engine.players[0]
        original = CardInstance(UNIQUE_ID)
        player.exile.append(original)

        result = start_formal_logic_actions(
            engine,
            0,
            [{
                'op': 'create_card',
                'snapshot': original.to_dict(),
                'owner_id': 0,
                'zone': 'discard',
                'trigger_hand': False,
                'forced_copy': True,
                'save_as': 'formal_copy',
            }],
        )

        self.assertTrue(result.get('success'), result)
        self.assertEqual(1, sum(card.def_id == UNIQUE_ID for card in player.exile))
        self.assertEqual(1, sum(card.def_id == UNIQUE_ID for card in player.discard))
        expected_void_id = engine._void_resolve_card_def_id('void:void')
        self.assertEqual([expected_void_id], [card.def_id for card in player.deck])

    def test_create_copies_to_deck_keeps_each_unique_copy_and_penalizes_each_extra(self):
        engine = self.prepare_engine()
        player = engine.players[0]
        player.equipment.append(EquipmentInstance(CardInstance(UNIQUE_ID), 0))

        engine._atomic_create_copies_to_deck_top(
            0,
            None,
            {'target': 'self', 'def_id': UNIQUE_ID, 'count': 2},
            '',
            None,
            {},
        )

        expected_void_id = engine._void_resolve_card_def_id('void:void')
        self.assertEqual(2, sum(card.def_id == UNIQUE_ID for card in player.deck))
        self.assertEqual(2, sum(card.def_id == expected_void_id for card in player.deck))

    def test_legacy_or_forced_duplicates_are_not_removed_by_global_enforcement(self):
        engine = self.prepare_engine()
        player = engine.players[0]
        first = CardInstance(UNIQUE_ID)
        second = first.copy()
        player.hand.append(first)
        player.discard.append(second)

        engine._enforce_unique_cards_for_all()

        self.assertIn(first, player.hand)
        self.assertIn(second, player.discard)
        self.assertEqual([], player.exile)

    def test_random_deck_generation_never_repeats_a_unique_card(self):
        for _ in range(30):
            picked = create_random_weighted_deck_def_ids(
                count=15,
                allowed_def_ids={UNIQUE_ID, NORMAL_ID},
            )
            self.assertLessEqual(picked.count(UNIQUE_ID), 1)

    def test_local_worker_keeps_forced_unique_copy_and_adds_void(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node is required for the local worker behavior test')
        worker = (ROOT / 'static' / 'js' / 'local_solo_worker.js').read_text(encoding='utf-8')
        self.assertIn('effect_arctic_snowflake_copy(', worker)
        self.assertIn('effect_arctic_icicle_shuffle_discard(', worker)
        harness = r'''
cardDefs = {
    Unique: {id: 'Unique', name_cn: '唯一测试牌', name_en: 'Unique', card_type: 'bloom', flags: ['unique']},
    Snowflake: {id: 'Snowflake', name_cn: '雪花', name_en: 'Snowflake', card_type: 'thorn', flags: ['unique']},
    Icicle: {id: 'Icicle', name_cn: '冰锥', name_en: 'Icicle', card_type: 'thorn', flags: ['unique']},
    Void: {id: 'Void', name_cn: '虚空', name_en: 'Void', card_type: 'bloom', flags: ['infinite_exclude']},
    Error: {id: 'Error', name_cn: '错误', name_en: 'Error', card_type: 'bloom', flags: ['infinite_exclude']},
};
const localEngine = Object.create(LocalSoloEngine.prototype);
localEngine.players = [new LocalPlayer(0), new LocalPlayer(1)];
localEngine.player_names = ['P1', 'P2'];
localEngine.log = [];
localEngine._active_effect_context = {};
localEngine.logMsg = message => localEngine.log.push(String(message));
localEngine.voidResolveCardId = () => 'Void';
localEngine.applySetupModifiersToCard = (playerId, card) => card;
const original = new LocalCard('Unique');
localEngine.players[0].equipment.push(new LocalEquipment(original, 0));
const copied = original.copy();
copied.instance_id = 999999;
localEngine.addForcedCopyToHand(0, copied);
localEngine.enforceUniqueCardsForPlayer(0);
const generated = new LocalCard('Unique');
const snowflake = new LocalCard('Snowflake');
localEngine.effect_arctic_snowflake_copy(0, snowflake, {}, '');
const icicle = new LocalCard('Icicle');
localEngine.effect_arctic_icicle_shuffle_discard(0, icicle, {}, '');
localEngine.effect_create_copies_to_deck_top(0, null, {def_id: 'Unique', count: 2}, '');
process.stdout.write(JSON.stringify({
    hand: localEngine.players[0].hand.map(card => card.def_id),
    uniqueDeckCount: localEngine.players[0].deck.filter(card => card.def_id === 'Unique').length,
    voidDeckCount: localEngine.players[0].deck.filter(card => card.def_id === 'Void').length,
    discard: localEngine.players[0].discard.map(card => card.def_id),
    equipment: localEngine.players[0].equipment.map(eq => eq.card_instance.def_id),
    canNormallyAcquire: localEngine.canNormallyAcquireCard(0, generated),
    legacyCleanupPreserved: localEngine.players[0].hand.includes(copied),
}));
'''
        with tempfile.TemporaryDirectory(prefix='gtn-unique-worker-') as temp_dir:
            script_path = Path(temp_dir) / 'unique-worker-test.js'
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
                'hand': ['Unique', 'Snowflake'],
                'uniqueDeckCount': 2,
                'voidDeckCount': 5,
                'discard': ['Icicle'],
                'equipment': ['Unique'],
                'canNormallyAcquire': False,
                'legacyCleanupPreserved': True,
            },
            json.loads(completed.stdout),
        )


if __name__ == '__main__':
    unittest.main()
