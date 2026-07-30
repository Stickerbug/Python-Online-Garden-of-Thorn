import unittest

from cards import CardInstance
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from game_engine_urf import GameEngineInfiniteFire


ENGINE_TYPES = (GameEngine, GameEngine2v2, GameEngineInfiniteFire)


class StatusImmunityApplicationTests(unittest.TestCase):
    @staticmethod
    def grant_status_immunity(engine, player_id=0):
        engine.players[player_id].custom_statuses["status_immune"] = 1

    def test_player_property_statuses_accumulate_while_suppressed(self):
        for engine_type in ENGINE_TYPES:
            with self.subTest(engine=engine_type.__name__):
                engine = engine_type()
                player = engine.players[0]
                card = CardInstance("Basic")
                player.poison = 3
                self.grant_status_immunity(engine)

                engine._atomic_player_prop_add(
                    0,
                    card,
                    {"target": "self", "property": "poison", "amount": 2},
                    "",
                    None,
                    "play",
                )
                engine._atomic_player_prop_add(
                    0,
                    card,
                    {"target": "self", "property": "dodge", "amount": 1},
                    "",
                    None,
                    "play",
                )

                self.assertEqual(player.poison, 5)
                self.assertEqual(player.dodge, 1)
                self.assertEqual(engine._get_player_property_value(0, "poison"), 0)
                self.assertEqual(engine._get_player_property_value(0, "dodge"), 0)
                self.assertEqual(
                    engine._get_player_property_value(0, "poison", include_suppressed=True),
                    5,
                )

                player.custom_statuses.clear()
                self.assertEqual(engine._get_player_property_value(0, "poison"), 5)
                self.assertEqual(engine._get_player_property_value(0, "dodge"), 1)

    def test_boolean_status_is_stored_but_inactive_during_immunity(self):
        for engine_type in ENGINE_TYPES:
            with self.subTest(engine=engine_type.__name__):
                engine = engine_type()
                player = engine.players[0]
                card = CardInstance("Basic")
                self.grant_status_immunity(engine)

                engine._atomic_player_prop_set(
                    0,
                    card,
                    {"target": "self", "property": "untargetable", "value": 1},
                    "",
                    None,
                    "play",
                )

                self.assertTrue(player.untargetable)
                self.assertEqual(engine._get_player_property_value(0, "untargetable"), 0)
                player.custom_statuses.clear()
                self.assertEqual(engine._get_player_property_value(0, "untargetable"), 1)

    def test_triangle_layers_can_change_while_their_effect_is_suppressed(self):
        for engine_type in ENGINE_TYPES:
            with self.subTest(engine=engine_type.__name__):
                engine = engine_type()
                player = engine.players[0]
                card = CardInstance("Basic")
                player.custom_vars["三角形层数"] = 2
                player.triangle_stacks = 2
                self.grant_status_immunity(engine)

                engine._atomic_var_set(
                    0,
                    card,
                    {
                        "target": "self",
                        "name": "三角形层数",
                        "value": {
                            "op": "min",
                            "a": 4,
                            "b": {
                                "op": "add",
                                "a": {
                                    "target": "self",
                                    "name": "三角形层数",
                                    "op": "var",
                                },
                                "b": 1,
                            },
                        },
                    },
                    "",
                    None,
                    "play",
                )

                self.assertEqual(player.custom_vars["三角形层数"], 3)
                self.assertEqual(player.triangle_stacks, 3)
                self.assertEqual(
                    engine._eval_expr(
                        0,
                        {"ref": "var", "target": "self", "name": "三角形层数"},
                        card,
                    ),
                    0,
                )
                player.custom_statuses.clear()
                self.assertEqual(
                    engine._eval_expr(
                        0,
                        {"ref": "var", "target": "self", "name": "三角形层数"},
                        card,
                    ),
                    3,
                )


if __name__ == "__main__":
    unittest.main()
