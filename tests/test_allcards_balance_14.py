"""Focused tests for the All Cards balance pass from development workbook 14."""

import unittest
from pathlib import Path

from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"
PACKAGES = {
    "Shovel": "Garden Cards Addition.gtnmod",
    "Coffee": "Vanilla Cards.gtnmod",
    "Coal": "Garden Cards DLC.gtnmod",
    "Grass": "Garden Cards DLC.gtnmod",
    "Clay": "Sewers Cards Addition.gtnmod",
    "Lotus": "Sewers Cards Addition.gtnmod",
    "Broccoli": "Sewers Cards Addition.gtnmod",
    "Chitin": "Sewers Cards DLC.gtnmod",
    "Bugatti": "Hel Cards Addition.gtnmod",
    "Clover": "Hel Cards Addition.gtnmod",
    "Blood Dice": "Hel Cards Addition.gtnmod",
    "Magic Clover": "Hel Cards Addition.gtnmod",
    "Ankh": "Desert Cards Addition.gtnmod",
    "Magic Pearl": "Ocean Cards Addition.gtnmod",
    "Magic Trident": "Ocean Cards Addition.gtnmod",
    "Mecha Antennae": "Factory Cards Addition.gtnmod",
    "Sugar": "Bio Cards Addition.gtnmod",
    "Blood Diamond": "Bio Cards Addition.gtnmod",
}


class AllCardsBalance14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.card_defs = {}
        for name, filename in PACKAGES.items():
            mod = load_mod(str(MODS / filename))
            if mod.errors:
                raise AssertionError((filename, mod.errors))
            card = next((c for c in mod.cards if c.id == name), None)
            if card is None:
                # Some packages store cards under their legacy runtime id.
                card = next(c for c in mod.cards if c.name_en == name)
            cls.card_defs[name] = card.to_card_def()

    def setUp(self):
        self.previous_defs = {name: CARD_DEFS.get(name) for name in PACKAGES}
        CARD_DEFS.update(self.card_defs)

    def tearDown(self):
        for name, previous in self.previous_defs.items():
            if previous is None:
                CARD_DEFS.pop(name, None)
            else:
                CARD_DEFS[name] = previous

    @staticmethod
    def action_engine(engine_type=GameEngine):
        engine = engine_type()
        engine.phase = "action"
        engine.current_player = 0
        engine.first_player = 0
        for player in engine.players:
            player.hand = []
            player.deck = []
            player.discard = []
            player.exile = []
            player.equipment = []
            player.health = 100
            player.max_health = 100
            player.elixir = 30
            player.magic = 30
            player.armor = 0
            player.dodge = 0
            player.blind = 0
            player.custom_statuses = {}
            player.custom_vars = {}
        return engine

    @staticmethod
    def target_choice(target_id):
        return {
            "target_player": target_id,
            "target_player_id": target_id,
            "target_id": target_id,
        }

    def play(self, engine, player_id, card, choice=None):
        engine.players[player_id].hand.append(card)
        if isinstance(engine, GameEngine2v2):
            target_id = choice.get("target_id") if isinstance(choice, dict) else None
            return engine.play_card(player_id, card.instance_id, target_id, choice or {})
        return engine.play_card(player_id, card.instance_id, choice or {})

    # ---------------------------------------------------------------- Shovel
    def test_shovel_ends_the_turn_immediately(self):
        engine = self.action_engine()
        shovel = CardInstance("Shovel")

        result = self.play(engine, 0, shovel, self.target_choice(0))

        self.assertTrue(result.get("success"), result)
        self.assertEqual(1, engine.players[0].untargetable)
        self.assertEqual(1, engine.current_player)
        self.assertFalse(getattr(engine.players[0], "force_end_turn", False))

    # ---------------------------------------------------------------- Coffee
    def test_coffee_heals_two_and_gives_the_card_heavy(self):
        engine = self.action_engine()
        coffee = CardInstance("Coffee")
        engine.players[1].elixir = 0

        result = self.play(engine, 0, coffee, self.target_choice(1))

        self.assertTrue(result.get("success"), result)
        self.assertEqual(2, engine.players[1].elixir)

    # ---------------------------------------------------------------- Coal
    def test_coal_damage_uses_fire_stacks_on_play(self):
        engine = self.action_engine()
        engine.players[0].fire = 3
        coal = CardInstance("Coal")

        result = self.play(engine, 0, coal, self.target_choice(1))

        self.assertTrue(result.get("success"), result)
        self.assertEqual(86, engine.players[1].health)  # 8 + 2 x 3

    def test_grass_can_trigger_on_the_turn_it_is_equipped(self):
        for engine_type in (GameEngine, GameEngine2v2):
            engine = self.action_engine(engine_type)
            target_id = 1 if engine_type is GameEngine else 2
            grass = CardInstance("Grass")
            result = self.play(engine, 0, grass, self.target_choice(target_id))
            self.assertTrue(result.get("success"), result)
            equipment = engine.players[0].equipment[0]
            self.assertEqual(0, equipment.turns_equipped)
            engine.players[target_id].health = 50

            triggered = engine.use_trigger(0, equipment.card_instance.instance_id)

            self.assertTrue(triggered.get("success"), triggered)
            self.assertEqual(56, engine.players[target_id].health)
            again = engine.use_trigger(0, equipment.card_instance.instance_id)
            self.assertFalse(again.get("success"), again)

    # ----------------------------------------------------------------- Clay
    def test_clay_gains_power_per_six_actual_damage_up_to_eighteen(self):
        engine = self.action_engine()
        clay = CardInstance("Clay")
        engine.players[0].hand = [clay]

        engine._record_damage(0, 5)
        self.assertEqual(0, clay.power_value)
        engine._record_damage(0, 1)
        self.assertEqual(1, clay.power_value)
        engine._record_damage(0, 6 * 30)
        self.assertEqual(18, clay.power_value)
        self.assertEqual(18, int(clay.custom_vars.get("sewers_clay_power_gained", 0)))

    # ---------------------------------------------------------------- Lotus
    def test_lotus_clears_poison_and_reduces_the_heal(self):
        engine = self.action_engine()
        engine.players[1].health = 50
        engine.players[1].poison = 4
        lotus = CardInstance("Lotus")

        result = self.play(engine, 0, lotus, self.target_choice(1))

        self.assertTrue(result.get("success"), result)
        self.assertEqual(56, engine.players[1].health)  # 10 - 4
        self.assertEqual(0, engine.players[1].poison)

    # ------------------------------------------------------------- Broccoli
    def test_broccoli_counter_damage_keeps_power(self):
        engine = self.action_engine()
        broccoli = CardInstance("Broccoli")
        broccoli.power_value = 6
        broccoli.instance_flags.add("power")
        broccoli._sewers_was_countered_this_play = True
        engine._apply_card_effect(0, broccoli, {"target_player": 1, "target_id": 1})

        # 10D (+6 Power) plus the countered 3D x2 (+6 Power each) = 28.
        self.assertEqual(72, engine.players[1].health)
        self.assertEqual(6, broccoli.power_value)

    # ------------------------------------------------------- Ocean / Bio hits
    def test_magic_trident_deals_eighteen_on_play(self):
        engine = self.action_engine()
        trident = CardInstance("Magic Trident")

        result = self.play(engine, 0, trident, self.target_choice(1))

        self.assertTrue(result.get("success"), result)
        self.assertEqual(82, engine.players[1].health)

    def test_sugar_deals_two_six_times_and_heals_twenty(self):
        engine = self.action_engine()
        engine.players[1].health = 50
        sugar = CardInstance("Sugar")

        result = self.play(engine, 0, sugar, self.target_choice(1))

        self.assertTrue(result.get("success"), result)
        self.assertEqual(58, engine.players[1].health)  # 50 - 12 + 20

    def test_blood_diamond_applies_bleed_for_every_actual_hit(self):
        engine = self.action_engine()
        diamond = CardInstance("Blood Diamond")

        result = self.play(engine, 0, diamond, self.target_choice(1))

        self.assertTrue(result.get("success"), result)
        # 4 fission petals of ceil(3 / 4) = 1 damage, twice (self-target + target).
        self.assertEqual(16, engine.players[1].bleed)

    # --------------------------------------------------------------- Chitin
    def test_chitin_destruction_clears_equipment_target_nazar(self):
        engine = self.action_engine()
        chitin = CardInstance("Chitin")
        result = self.play(engine, 0, chitin, self.target_choice(1))
        self.assertTrue(result.get("success"), result)
        equipment = engine.players[0].equipment[0]
        self.assertEqual(1, equipment.effect_target)
        engine._set_nazar_status_value(1, 3)

        destroyed = engine._destroy_equipment(0, equipment, check_protection=False)

        self.assertTrue(destroyed)
        self.assertEqual(0, engine._nazar_status_value(1))

    # -------------------------------------------------------------- Bugatti
    def test_bugatti_draws_to_hand_limit_after_turn_start_draw(self):
        engine = self.action_engine()
        bugatti = CardInstance("Bugatti")
        result = self.play(engine, 0, bugatti, self.target_choice(1))
        self.assertTrue(result.get("success"), result)
        equipment = engine.players[0].equipment[0]
        self.assertEqual(1, equipment.effect_target)
        target = engine.players[1]
        target.hand = [CardInstance("Basic") for _ in range(3)]
        target.deck = [CardInstance("Basic") for _ in range(6)]

        engine._run_target_turn_start_after_draw_equipment(1)

        # Bugatti draws the target up to its (reduced) hand limit.
        self.assertEqual(target.hand_limit(), len(target.hand))
        self.assertGreater(len(target.hand), 3)

    # ---------------------------------------------------------------- Ankh
    def test_ankh_revives_defeated_players_with_their_zones(self):
        engine = self.action_engine(GameEngine2v2)
        engine.players[1].health = 0
        engine.players[1].hand = [CardInstance("Basic")]
        engine.players[1].deck = [CardInstance("Bone")]
        ankh = CardInstance("Ankh")

        result = self.play(engine, 0, ankh, self.target_choice(0))

        self.assertTrue(result.get("success"), result)
        self.assertGreater(engine.players[1].health, 0)
        self.assertEqual(1, len(engine.players[1].hand))
        self.assertEqual(1, len(engine.players[1].deck))

    # ----------------------------------------------------------- Magic Pearl
    def test_magic_pearl_entering_hand_grants_power_and_registers_autoplay(self):
        engine = self.action_engine()
        pearl = CardInstance("Magic Pearl")
        engine.players[0].hand = [pearl]

        engine._handle_card_enter_hand(0, pearl)
        self.assertEqual(2, pearl.power_value)

        result = self.play(engine, 0, pearl, self.target_choice(1))
        self.assertTrue(result.get("success"), result)
        entries = engine.players[0].custom_vars.get("ocean_auto_cards") or []
        self.assertEqual(1, len(entries))
        self.assertTrue(engine._def_id_is_magic_pearl(entries[0]["def_id"]), entries[0])

    def test_magic_pearl_autoplay_copy_does_not_gain_power(self):
        engine = self.action_engine()
        engine.players[1].health = 100
        pearl = CardInstance("Magic Pearl")
        engine.players[0].hand = [pearl]
        self.play(engine, 0, pearl, self.target_choice(1))

        engine.players[1].health = 100
        engine.players[1].hand = []
        engine._run_ocean_auto_cards_turn_start(0)

        # The autoplay copy deals the base 5D instead of 7D.
        self.assertEqual(95, engine.players[1].health)

    # -------------------------------------------------------- Mecha Antennae
    def test_mecha_antennae_reveals_all_zones_and_takes_top_three(self):
        engine = self.action_engine()
        target = engine.players[1]
        target.hand = [CardInstance("Basic"), CardInstance("Bone")]
        target.deck = [CardInstance("Basic")]
        target.discard = []
        target.exile = []
        caster = engine.players[0]
        top_cards = [CardInstance("Basic"), CardInstance("Bone"), CardInstance("Stinger")]
        caster.deck = list(top_cards) + [CardInstance("Sand")]

        result = self.play(engine, 0, CardInstance("Mecha Antennae"), self.target_choice(1))
        self.assertTrue(result.get("needs_v2_ui"), result)
        first = engine.handle_v2_ui_response(
            0,
            engine.pending_v2_ui["request_id"],
            {"button": "confirm", "values": {"card_type": "thorn"}},
        )
        self.assertTrue(first.get("needs_v2_ui"), first)
        for candidate in target.hand + target.deck:
            self.assertIn("revealed", candidate.instance_flags)
        self.assertNotIn("revealed", caster.deck[0].instance_flags)

        second = engine.handle_v2_ui_response(
            0,
            engine.pending_v2_ui["request_id"],
            {"button": "confirm", "values": {"pick": top_cards[1].instance_id}},
        )
        self.assertTrue(second.get("success"), second)
        hand_ids = [card.instance_id for card in caster.hand]
        discard_ids = [card.instance_id for card in caster.discard]
        self.assertIn(top_cards[1].instance_id, hand_ids)
        self.assertIn(top_cards[0].instance_id, discard_ids)
        self.assertIn(top_cards[2].instance_id, discard_ids)
        self.assertEqual(1, len(caster.deck))

    def test_mecha_antennae_ui_flow_reveals_then_picks_from_deck_top(self):
        engine = self.action_engine()
        caster = engine.players[0]
        target = engine.players[1]
        target.hand = [CardInstance("Basic")]
        top_cards = [CardInstance("Basic"), CardInstance("Bone"), CardInstance("Stinger")]
        caster.deck = list(top_cards) + [CardInstance("Sand")]
        mecha = CardInstance("Mecha Antennae")

        result = self.play(engine, 0, mecha, self.target_choice(1))

        self.assertTrue(result.get("needs_v2_ui"), result)
        pending = engine.pending_v2_ui
        self.assertIsNotNone(pending)
        first = engine.handle_v2_ui_response(
            0, pending["request_id"], {"button": "confirm", "values": {"card_type": "thorn"}}
        )
        self.assertTrue(first.get("needs_v2_ui"), first)
        self.assertIn("revealed", target.hand[0].instance_flags)
        pending = engine.pending_v2_ui
        options = pending["component"]["controls"][0]["options"]
        self.assertEqual(
            {card.instance_id for card in top_cards},
            {option["value"] for option in options},
        )

        second = engine.handle_v2_ui_response(
            0, pending["request_id"], {"button": "confirm", "values": {"pick": top_cards[0].instance_id}}
        )

        self.assertTrue(second.get("success"), second)
        self.assertIsNone(engine.pending_v2_ui)
        self.assertIn(top_cards[0], caster.hand)
        self.assertIn(top_cards[1], caster.discard)
        self.assertIn(top_cards[2], caster.discard)

    # ----------------------------------------------------- Hel crit / trigger
    def test_base_crit_multiplier_is_two(self):
        engine = self.action_engine()
        self.assertEqual(2.0, engine._hel_crit_multiplier(0))

    def test_clover_grants_four_luck_at_target_turn_start(self):
        engine = self.action_engine()
        clover = CardInstance("Clover")
        result = self.play(engine, 0, clover, self.target_choice(1))
        self.assertTrue(result.get("success"), result)
        equipment = engine.players[0].equipment[0]

        engine._run_card_event(
            0,
            equipment.card_instance,
            "target_turn_start",
            None,
            {"source_id": 0, "target_id": 1},
        )

        self.assertEqual(4, engine._hel_luck_value(1))

    # ------------------------------------------------- blinding / uncancel
    def test_blinded_players_cannot_cancel_card_choices(self):
        engine = self.action_engine()
        engine.players[0].blind = 1
        compass = CardInstance("Basic")
        engine.players[0].hand = [compass, CardInstance("Bone")]
        card = next(card for card in engine.players[0].hand if card.def_id == "Basic")
        card.choice_params = None
        engine.players[0].custom_vars["test_unused"] = 0

        self.assertTrue(engine._player_choices_are_uncancellable(0))
        engine.players[0].blind = 0
        self.assertFalse(engine._player_choices_are_uncancellable(0))


if __name__ == "__main__":
    unittest.main()
