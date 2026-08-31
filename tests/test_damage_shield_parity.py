import unittest
from pathlib import Path

from cards import CARD_DEFS, CardInstance
from game_engine import EquipmentInstance, GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
MECHANIC_PACKAGES = (
    'Bio Cards DLC.gtnmod',
    'Jungle Cards Addition.gtnmod',
    'Jurassic Cards Addition.gtnmod',
    'Vanilla Cards.gtnmod',
    'Void Cards DLC.gtnmod',
)


class DamageShieldParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mods = [load_mod(str(ROOT / 'mods' / filename)) for filename in MECHANIC_PACKAGES]
        errors = [error for mod in mods for error in mod.errors]
        if errors:
            raise AssertionError(errors)
        cls.definitions = {}
        for mod in mods:
            for card in mod.cards:
                cls.definitions[card.id] = card.to_card_def()

    def setUp(self):
        self.previous_defs = {card_id: CARD_DEFS.get(card_id) for card_id in self.definitions}
        CARD_DEFS.update(self.definitions)

    def tearDown(self):
        for card_id, previous in self.previous_defs.items():
            if previous is None:
                CARD_DEFS.pop(card_id, None)
            else:
                CARD_DEFS[card_id] = previous

    @staticmethod
    def action_engine(engine_class):
        engine = engine_class()
        engine.phase = 'action'
        engine.current_player = 0
        for player in engine.players:
            player.hand = []
            player.deck = []
            player.discard = []
            player.exile = []
            player.equipment = []
            player.elixir = 50
            player.magic = 50
            player.health = 100
            player.max_health = 100
            player.armor = 0
            player.custom_statuses = {}
            player.custom_vars = {}
            player.turn_damage_taken = 0
        return engine

    @staticmethod
    def equip(engine, owner_id, target_id, def_id):
        equipment = EquipmentInstance(CardInstance(def_id), owner_id)
        equipment.effect_target = target_id
        engine.players[owner_id].equipment.append(equipment)
        return equipment

    @staticmethod
    def enemy_target(engine):
        return 2 if isinstance(engine, GameEngine2v2) else 1

    def test_magic_copper_rod_attack_and_direct_damage_match_in_both_engines(self):
        for engine_class in (GameEngine, GameEngine2v2):
            with self.subTest(engine=engine_class.__name__, kind='attack'):
                engine = self.action_engine(engine_class)
                target_id = self.enemy_target(engine)
                self.equip(engine, target_id, target_id, 'MagicCopperRod')
                engine.players[target_id].magic = 1
                engine._prediction_capture_target_id = target_id
                engine._prediction_first_attack_damage = 0

                dealt = engine.deal_attack_damage(target_id, 7, hits=2, attacker_id=0)

                self.assertEqual(dealt, 7)
                self.assertEqual(engine._prediction_first_attack_damage, 7)
                self.assertEqual(engine.players[target_id].health, 93)
                self.assertEqual(engine.players[target_id].magic, 0)

            with self.subTest(engine=engine_class.__name__, kind='direct'):
                engine = self.action_engine(engine_class)
                target_id = self.enemy_target(engine)
                owner_id = 1 if isinstance(engine, GameEngine2v2) else target_id
                self.equip(engine, owner_id, target_id, 'MagicCopperRod')
                engine.players[owner_id].magic = 1

                dealt = engine._deal_direct_damage(target_id, 7, '效果伤害', 0)

                self.assertEqual(dealt, 0)
                self.assertEqual(engine.players[target_id].health, 100)
                self.assertEqual(engine.players[owner_id].magic, 0)

    def test_masks_block_direct_but_not_attack_damage_in_both_engines(self):
        for engine_class in (GameEngine, GameEngine2v2):
            for def_id in ('Mask', 'MagicMask'):
                with self.subTest(engine=engine_class.__name__, mask=def_id):
                    engine = self.action_engine(engine_class)
                    target_id = self.enemy_target(engine)
                    self.equip(engine, 0, target_id, def_id)

                    direct = engine._deal_direct_damage(target_id, 7, '效果伤害', 0)
                    attack = engine.deal_attack_damage(target_id, 7, attacker_id=0)

                    self.assertEqual(direct, 0)
                    self.assertEqual(attack, 7)
                    self.assertEqual(engine.players[target_id].health, 93)

    def test_copper_rod_response_absorbs_in_both_engines(self):
        for engine_class in (GameEngine, GameEngine2v2):
            with self.subTest(engine=engine_class.__name__):
                engine = self.action_engine(engine_class)
                target_id = self.enemy_target(engine)
                attack = CardInstance('Basic')
                copper_rod = CardInstance('CopperRod')
                other_card = CardInstance('Basic')
                engine.players[0].hand = [attack]
                engine.players[target_id].hand = [copper_rod, other_card]
                choice = {
                    'target_player': target_id,
                    'target_player_id': target_id,
                    'target_id': target_id,
                }

                if isinstance(engine, GameEngine2v2):
                    played = engine.play_card(0, attack.instance_id, target_player_id=target_id, choice=choice)
                else:
                    played = engine.play_card(0, attack.instance_id, choice)
                self.assertTrue(played.get('needs_response'), played)
                response = engine.handle_response(target_id, copper_rod.instance_id)

                self.assertTrue(response.get('success'), response)
                self.assertEqual(engine.players[target_id].health, 100)
                self.assertGreater(other_card.charge_value, 0)

    def test_shared_universal_shields_match_in_both_engines(self):
        for engine_class in (GameEngine, GameEngine2v2):
            with self.subTest(engine=engine_class.__name__, mechanic='cotton'):
                engine = self.action_engine(engine_class)
                target_id = self.enemy_target(engine)
                self.equip(engine, 0, target_id, 'MagicCotton')
                engine.players[target_id].magic = 2

                dealt = engine.deal_attack_damage(target_id, 10, attacker_id=0)

                self.assertEqual(dealt, 2)
                self.assertEqual(engine.players[target_id].magic, 0)

            with self.subTest(engine=engine_class.__name__, mechanic='scales'):
                engine = self.action_engine(engine_class)
                target_id = self.enemy_target(engine)
                self.equip(engine, 0, target_id, 'Scales')
                engine.players[target_id].turn_damage_taken = 10

                dealt = engine.deal_attack_damage(target_id, 9, attacker_id=0)

                self.assertEqual(dealt, 4)

            with self.subTest(engine=engine_class.__name__, mechanic='amber'):
                engine = self.action_engine(engine_class)
                target_id = self.enemy_target(engine)
                amber = CardInstance('Amber')
                engine.players[target_id].hand = [amber]
                damage_parts = []
                for _ in range(3):
                    damage_parts.append(engine.deal_attack_damage(target_id, 10, attacker_id=0))

                self.assertEqual(damage_parts, [8, 8, 10])
                self.assertEqual(amber.power_value, -12)

    def test_relic_transfer_is_not_recursively_retransferred(self):
        engine = self.action_engine(GameEngine2v2)
        self.equip(engine, 2, 2, 'Relic')
        self.equip(engine, 3, 3, 'Relic')

        dealt = engine.deal_attack_damage(2, 10, attacker_id=0)

        self.assertEqual(dealt, 3)
        self.assertEqual(engine.players[2].health, 97)
        self.assertEqual(engine.players[3].health, 94)


if __name__ == '__main__':
    unittest.main()
