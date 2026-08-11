import json
from pathlib import Path

from cards import CARD_DEFS, CardInstance
from formal_logic import parse_formula
from formal_logic_runtime import (
    MACRO_EQUIPMENT_ID,
    SUBSTITUTION_STATUS,
    _automatic_play_target,
    _complete_inference,
    _special_card_for_formula,
    boosted_draft_pool,
    formula_for_card,
    formal_proxy_suppresses_effect,
    on_equipment_triggered,
    on_turn_end,
    resume_formal_logic_actions,
    set_card_formula,
    start_formal_logic_actions,
)
from game_engine import GameEngine
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "mods" / "Formal Logic Reasoning.gtnmod"


class TestFormalLogicRuntime:
    @classmethod
    def setup_class(cls):
        cls.mod = load_mod(str(PACKAGE))
        assert cls.mod.errors == []
        cls.mod_defs = {card.id: card.to_card_def() for card in cls.mod.cards}

    def setup_method(self):
        self.previous_defs = {card_id: CARD_DEFS.get(card_id) for card_id in self.mod_defs}
        CARD_DEFS.update(self.mod_defs)

    def teardown_method(self):
        for card_id, previous in self.previous_defs.items():
            if previous is None:
                CARD_DEFS.pop(card_id, None)
            else:
                CARD_DEFS[card_id] = previous

    @staticmethod
    def engine():
        engine = GameEngine()
        engine.phase = "action"
        engine.current_player = 0
        for player in engine.players:
            player.hand = []
            player.deck = []
            player.discard = []
            player.exile = []
            player.equipment = []
            player.elixir = 99
            player.magic = 99
            player.health = 200
            player.max_health = 200
        return engine

    @staticmethod
    def play(engine, card, target_id=0):
        result = engine.play_card(
            0,
            card.instance_id,
            {
                "target_player_id": target_id,
                "target_player": target_id,
                "target_id": target_id,
            },
        )
        assert result.get("success"), result
        return result

    def test_package_is_valid_entertainment_mod(self):
        assert self.mod.info.category == "entertainment"
        assert self.mod.info.author == "NaN"
        assert len(self.mod.cards) == 19
        assert self.mod.warnings == []

    def test_k_axiom_completes_substitution_and_inference_cycle(self):
        engine = self.engine()
        player = engine.players[0]
        cards = [
            CardInstance("formal_logic:axiom_k"),
            CardInstance("formal_logic:variable_0"),
            CardInstance("formal_logic:variable_1"),
            CardInstance("formal_logic:variable_0"),
            CardInstance("formal_logic:variable_1"),
        ]
        for card in cards:
            player.add_to_hand(card, trigger_enter_hand=False)
        axiom, first_zero, first_one, inference_zero, inference_one = cards

        for card, target in (
            (axiom, 0),
            (first_zero, 1),
            (axiom, 0),
            (first_one, 0),
            (axiom, 0),
            (inference_zero, 1),
            (inference_one, 0),
        ):
            self.play(engine, card, target)

        assert SUBSTITUTION_STATUS not in player.custom_statuses
        assert "formal_logic:inference" not in player.custom_statuses
        assert engine._find_card_location(axiom)[1] == "discard"
        assert axiom.name_cn == "├$0>($1>$0)"
        assert sum(card.def_id == "formal_logic:variable_0" for card in player.discard) == 3
        assert any("完成推理" in message for message in engine.log)

    def test_status_immunity_preserves_pending_substitution(self):
        engine = self.engine()
        player = engine.players[0]
        axiom = CardInstance("formal_logic:axiom_k")
        ignored = CardInstance("formal_logic:variable_0")
        applied = CardInstance("formal_logic:variable_1")
        for card in (axiom, ignored, applied):
            player.add_to_hand(card, trigger_enter_hand=False)

        self.play(engine, axiom, 0)
        original = formula_for_card(axiom)
        player.custom_statuses["status_immune"] = 1
        self.play(engine, ignored, 1)
        assert player.custom_statuses.get(SUBSTITUTION_STATUS) == 1
        assert formula_for_card(axiom) == original

        player.custom_statuses.pop("status_immune")
        self.play(engine, applied, 0)
        assert SUBSTITUTION_STATUS not in player.custom_statuses
        assert formula_for_card(axiom) != original

    def test_after_inference_theorem_resets_only_when_inference_finishes(self):
        engine = self.engine()
        player = engine.players[0]
        theorem = CardInstance("formal_logic:double_negation_intro")
        substitution_value = CardInstance("formal_logic:variable_1")
        inference_value = CardInstance("formal_logic:variable_1")
        for card in (theorem, substitution_value, inference_value):
            player.add_to_hand(card, trigger_enter_hand=False)

        self.play(engine, theorem, 0)
        self.play(engine, substitution_value, 1)
        player.discard.remove(theorem)
        player.add_to_hand(theorem, trigger_enter_hand=False)
        self.play(engine, theorem, 0)

        assert player.custom_statuses.get("formal_logic:inference") == 1
        assert theorem.custom_vars.get("formal_logic_stage") == 1
        assert formula_for_card(theorem) == parse_formula("├$1>¬¬$1")

        self.play(engine, inference_value, 1)

        assert "formal_logic:inference" not in player.custom_statuses
        assert "formal_logic_stage" not in theorem.custom_vars
        assert formula_for_card(theorem) == parse_formula("├$0>¬¬$0")

    def test_special_formula_detection_keeps_double_negation_theorems_distinct(self):
        identity = _special_card_for_formula(parse_formula("├$7>$7"))
        introduction = _special_card_for_formula(parse_formula("├$7>¬¬$7"))
        elimination = _special_card_for_formula(parse_formula("├¬¬$7>$7"))
        assert identity is not None and identity.def_id == "formal_logic:identity"
        assert introduction is not None and introduction.def_id == "formal_logic:double_negation_intro"
        assert elimination is not None and elimination.def_id == "formal_logic:double_negation_elim"

    def test_automatic_play_target_respects_card_target_mode(self):
        engine = self.engine()
        self_only = CardInstance("formal_logic:macro")
        wide = CardInstance("formal_logic:generalization")
        wide.instance_flags.add("wide_strike")
        attack = CardInstance("formal_logic:variable_0")

        assert _automatic_play_target(engine, 0, self_only)[0] == 0
        assert _automatic_play_target(engine, 0, wide)[0] == -1
        assert _automatic_play_target(engine, 0, attack)[0] == 1

    def test_inference_can_play_its_conclusion_out_of_turn(self):
        engine = self.engine()
        engine.current_player = 1
        source = CardInstance("formal_logic:generated_theorem")
        engine.players[0].exile.append(source)
        payload = {
            "source_card_instance_id": source.instance_id,
            "premises": [],
            "antecedents": [],
            "conclusion": {
                "kind": "const",
                "value": "formal_logic:variable_0",
                "children": [],
            },
        }

        result = start_formal_logic_actions(engine, 0, _complete_inference(engine, 0, payload))

        assert result.get("success")
        assert any(card.def_id == "formal_logic:variable_0" for card in engine.players[0].discard)

    def test_a_card_played_during_inference_cannot_grant_new_inference(self):
        engine = self.engine()
        player = engine.players[0]
        axiom = CardInstance("formal_logic:axiom_k")
        zero = CardInstance("formal_logic:variable_0")
        one = CardInstance("formal_logic:variable_1")
        competing_axiom = CardInstance("formal_logic:axiom_k")
        for card in (axiom, zero, one, competing_axiom):
            player.add_to_hand(card, trigger_enter_hand=False)

        self.play(engine, axiom, 0)
        self.play(engine, zero, 1)
        self.play(engine, axiom, 0)
        self.play(engine, one, 0)
        self.play(engine, axiom, 0)
        assert player.custom_statuses.get("formal_logic:inference") == 1

        competing_axiom.custom_vars["formal_logic_stage"] = 2
        self.play(engine, competing_axiom, 0)
        assert "formal_logic:inference" not in player.custom_statuses

    def test_single_negation_inference_requires_no_card_play(self):
        engine = self.engine()
        player = engine.players[0]
        theorem = CardInstance("formal_logic:generated_theorem")
        set_card_formula(theorem, parse_formula("├¬[A]"))
        theorem.custom_vars["formal_logic_required_substitutions"] = 0
        player.add_to_hand(theorem, trigger_enter_hand=False)

        hand_count = len(player.hand)
        self.play(engine, theorem, 0)
        assert len(player.hand) <= hand_count
        assert "formal_logic:inference" not in player.custom_statuses
        assert any("否定结论不打出牌" in message for message in engine.log)

    def test_paused_atomic_actions_are_json_serializable_and_resume(self):
        engine = self.engine()
        player = engine.players[0]
        card = CardInstance("formal_logic:variable_0")
        player.add_to_hand(card, trigger_enter_hand=False)

        result = start_formal_logic_actions(
            engine,
            0,
            [
                {
                    "op": "choose",
                    "choice_type": "card",
                    "owner_id": 0,
                    "zone": "hand",
                    "allowed_instance_ids": [card.instance_id],
                    "save_as": "picked",
                },
                {
                    "op": "move_card",
                    "instance_id": {"var": "picked"},
                    "owner_id": 0,
                    "zone": "discard",
                },
            ],
        )
        assert result.get("needs_v2_ui")
        state = engine.pending_v2_ui["resume_state"]
        json.dumps(state, ensure_ascii=False)

        resumed = resume_formal_logic_actions(
            engine,
            state,
            {"button": "confirm", "values": {"choice": card.instance_id}},
        )
        assert resumed.get("success")
        assert card in player.discard

    def test_deduction_metatheorem_invalidates_inverse_deduction(self):
        engine = self.engine()
        inverse = CardInstance("formal_logic:inverse_deduction")
        axiom = CardInstance("formal_logic:axiom_k")
        response = CardInstance("formal_logic:deduction_metatheorem")
        engine.players[0].hand.extend([inverse, axiom])
        engine.players[1].hand.append(response)

        played = engine.play_card(0, inverse.instance_id, {})
        assert played.get("needs_v2_ui")
        pending = engine.pending_v2_ui
        selected = engine.handle_v2_ui_response(
            0,
            pending["request_id"],
            {"button": "confirm", "values": {"choice": axiom.instance_id}},
        )
        assert selected.get("needs_v2_ui")
        pending = engine.pending_v2_ui
        resolved = engine.handle_v2_ui_response(
            1,
            pending["request_id"],
            {"button": "confirm", "values": {"choice": response.instance_id}},
        )

        assert resolved.get("success")
        assert axiom in engine.players[0].hand
        assert inverse in engine.players[0].exile
        assert response in engine.players[1].discard
        assert any("逆演绎元定理被反制" in message for message in engine.log)

    def test_macro_proxy_suppresses_numeric_effect_and_accumulates_heavy(self):
        engine = self.engine()
        player = engine.players[0]
        source = CardInstance("formal_logic:variable_0")
        player.add_to_hand(source, trigger_enter_hand=False)

        result = start_formal_logic_actions(
            engine,
            0,
            [
                {
                    "op": "choose",
                    "choice_type": "card",
                    "owner_id": 0,
                    "zone": "hand",
                    "allowed_instance_ids": [source.instance_id],
                    "save_as": "selected_card",
                },
                {"op": "call", "name": "macro_create"},
            ],
        )
        assert result.get("needs_v2_ui")
        state = engine.pending_v2_ui["resume_state"]
        resume_formal_logic_actions(
            engine,
            state,
            {"button": "confirm", "values": {"choice": source.instance_id}},
        )
        engine.pending_v2_ui = None

        macro = next(eq.card_instance for eq in player.equipment if eq.card_instance.def_id == MACRO_EQUIPMENT_ID)
        assert source in player.exile
        assert any(card.def_id == source.def_id for card in player.discard)

        on_equipment_triggered(engine, 0, macro)
        proxy = next(card for card in player.hand if formal_proxy_suppresses_effect(card))
        assert "void" in proxy.flags
        health_before = engine.players[1].health
        self.play(engine, proxy, 1)
        assert engine.players[1].health == health_before
        assert macro.custom_vars.get("formal_logic_macro_heavy") == 1

        on_equipment_triggered(engine, 0, macro)
        next_proxy = next(card for card in player.hand if formal_proxy_suppresses_effect(card))
        assert next_proxy.temp_heavy_value == 1

    def test_dynamic_formula_name_survives_copy_and_serialization(self):
        card = CardInstance("formal_logic:generated_theorem")
        set_card_formula(card, parse_formula("$0├$1>$0"))
        restored = CardInstance.from_dict(json.loads(json.dumps(card.to_dict())))
        copied = card.copy()
        assert restored.name_cn == "$0├$1>$0"
        assert copied.name_cn == "$0├$1>$0"
        assert restored.custom_vars is not card.custom_vars

        set_card_formula(card, parse_formula("├[Light]"))
        assert card.name_cn == f"├[{CARD_DEFS['Light'].name_cn}]"
        assert card.name_en == f"├[{CARD_DEFS['Light'].name_en}]"

    def test_debut_permanent_cost_survives_play_and_later_debut_is_temporary(self):
        engine = self.engine()
        player = engine.players[0]
        permanent_target = CardInstance("Basic")
        player.add_to_hand(permanent_target, trigger_enter_hand=False)
        player.add_to_hand(CardInstance("formal_logic:double_negation_intro"))
        pending = engine.pending_v2_ui
        engine.handle_v2_ui_response(
            0,
            pending["request_id"],
            {"button": "confirm", "values": {"choice": permanent_target.instance_id}},
        )
        assert permanent_target.cost_e == 0

        self.play(engine, permanent_target, 1)
        assert permanent_target.cost_e == 0

        temporary_target = CardInstance("Bone")
        player.add_to_hand(temporary_target, trigger_enter_hand=False)
        player.add_to_hand(CardInstance("formal_logic:double_negation_intro"))
        pending = engine.pending_v2_ui
        engine.handle_v2_ui_response(
            0,
            pending["request_id"],
            {"button": "confirm", "values": {"choice": temporary_target.instance_id}},
        )
        assert temporary_target.cost_e == 0
        on_turn_end(engine, 0)
        assert temporary_target.cost_e == temporary_target.card_def.cost_e

    def test_repeatable_debut_effect_runs_each_time_card_enters_hand(self):
        engine = self.engine()
        player = engine.players[0]
        player.health = 50
        player.max_health = 100
        player.add_to_hand(CardInstance("formal_logic:transitivity"))
        player.add_to_hand(CardInstance("formal_logic:transitivity"))
        assert player.health == 60

    def test_great_mathematician_only_boosts_formal_cards(self):
        engine = self.engine()
        engine.opening_event_picks[0] = "formal_logic:great_mathematician"
        formal = CardInstance("formal_logic:variable_0")
        ordinary = CardInstance("Light")
        formal.draft_weight = 2.0
        ordinary.draft_weight = 2.0
        boosted = boosted_draft_pool(engine, 0, [formal, ordinary])
        assert boosted[0].draft_weight == 10.0
        assert boosted[1].draft_weight == 2.0
