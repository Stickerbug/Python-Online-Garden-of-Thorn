import unittest

from cards import CARD_DEFS, CardDef, CardInstance
from db import ACHIEVEMENT_DEF_MAP
from game_engine import DAMAGE_TAG_DIRECT, DAMAGE_TYPE_PHYSICAL, GameEngine, PlayerState


TEST_CARD_ID = "test:damage_output"


class DamageOutputMilestoneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_def = CARD_DEFS.get(TEST_CARD_ID)
        CARD_DEFS[TEST_CARD_ID] = CardDef(
            TEST_CARD_ID,
            "Damage Output",
            "伤害产出",
            0,
            0,
            "thorn",
            1,
            "Common",
            "",
            "",
        )

    @classmethod
    def tearDownClass(cls):
        if cls.previous_def is None:
            CARD_DEFS.pop(TEST_CARD_ID, None)
        else:
            CARD_DEFS[TEST_CARD_ID] = cls.previous_def

    @staticmethod
    def engine():
        engine = GameEngine()
        for player in engine.players:
            player.health = 100
            player.max_health = 100
            player.armor = 0
            player.custom_statuses = {}
        return engine

    def test_overkill_and_armor_absorption_both_count(self):
        engine = self.engine()
        target = engine.players[1]
        target.health = 5
        target.armor = 4

        dealt = engine.deal_attack_damage(1, 20, attacker_id=0)

        self.assertEqual(dealt, 16)
        self.assertEqual(target.health, -11)
        self.assertEqual(engine.players[0].total_damage_dealt, 16)
        self.assertEqual(engine.players[0].achievement_total_damage_output, 20)

    def test_shield_and_sponge_absorption_count(self):
        shielded = self.engine()
        shielded._set_custom_status_alias_group(
            1,
            "jungle:shield",
            ("jungle:shield", "shield"),
            7,
        )

        dealt = shielded._deal_direct_damage(
            1,
            10,
            "测试",
            0,
            damage_type=DAMAGE_TYPE_PHYSICAL,
            damage_tag=DAMAGE_TAG_DIRECT,
        )

        self.assertEqual(dealt, 3)
        self.assertEqual(shielded.players[0].achievement_total_damage_output, 10)

        sponge = self.engine()
        sponge.players[1].sponge_active = True

        dealt = sponge.deal_attack_damage(1, 20, attacker_id=0)

        self.assertEqual(dealt, 0)
        self.assertEqual(sponge.players[1].poison, 10)
        self.assertEqual(sponge.players[0].achievement_total_damage_output, 20)

    def test_power_and_damage_multiplier_apply_before_absorption(self):
        engine = self.engine()
        card = CardInstance(TEST_CARD_ID)
        card.power_value = 4
        engine.players[0].damage_multiplier = 1.5
        engine.players[1].armor = 100

        dealt = engine.deal_attack_damage(
            1,
            10,
            attacker_id=0,
            source_card=card,
        )

        self.assertEqual(dealt, 0)
        self.assertEqual(engine.players[0].achievement_total_damage_output, 21)

    def test_metric_survives_serialization_and_resets_per_match(self):
        engine = self.engine()
        engine.players[0].achievement_total_damage_output = 123

        restored = PlayerState.from_dict(engine.players[0].to_dict())
        self.assertEqual(restored.achievement_total_damage_output, 123)

        engine._reset_achievement_match_stats(0)
        self.assertEqual(engine.players[0].achievement_total_damage_output, 0)

    def test_milestone_series_uses_expected_targets(self):
        expected = {
            "damage_output_500": (500, 250),
            "damage_output_2000": (2000, 600),
            "damage_output_10000": (10000, 1500),
            "damage_output_50000": (50000, 3500),
        }
        for achievement_id, (target, reward) in expected.items():
            definition = ACHIEVEMENT_DEF_MAP[achievement_id]
            self.assertEqual(definition["metric"], "damage_output_total")
            self.assertEqual(definition["target"], target)
            self.assertEqual(definition["reward_dew"], reward)


if __name__ == "__main__":
    unittest.main()
