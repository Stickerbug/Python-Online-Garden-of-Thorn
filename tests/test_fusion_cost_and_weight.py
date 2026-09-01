import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from cards import (
    CARD_DEFS,
    CardInstance,
    MAX_CARD_LAYER,
    build_draft_pool,
    fusion_adjusted_cost,
    fusion_cost_surcharge,
    same_type_draw_probabilities,
)
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "mods" / "Vanilla Cards.gtnmod"
GAME_JS = (ROOT / "static" / "js" / "game.js").read_text(encoding="utf-8")
LOCAL_WORKER_JS = (ROOT / "static" / "js" / "local_solo_worker.js").read_text(encoding="utf-8")
CARD_STYLE_GUIDE = (ROOT / "docs" / "卡牌描述规范.md").read_text(encoding="utf-8")


def _node_binary(test_case):
    node = shutil.which("node")
    if not node:
        test_case.skipTest("node is required for JavaScript parity tests")
    return node


def _run_node(test_case, source):
    node = _node_binary(test_case)
    with tempfile.TemporaryDirectory(prefix="gtn-fusion-cost-") as temp_dir:
        script = Path(temp_dir) / "fusion-cost-test.js"
        script.write_text(source, encoding="utf-8")
        completed = subprocess.run(
            [node, str(script)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
    test_case.assertEqual(completed.returncode, 0, completed.stderr)
    return json.loads(completed.stdout)


class FusionCostAndWeightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mod = load_mod(str(PACKAGE))
        if mod.errors:
            raise AssertionError(mod.errors)
        cls.package_cards = {card.id: card for card in mod.cards}

    def test_integer_cost_formula_keeps_default_and_floors_each_extra_layer(self):
        self.assertEqual(fusion_adjusted_cost(3, 1), 3)
        self.assertEqual(fusion_adjusted_cost(3, 2), 4)
        self.assertEqual(fusion_adjusted_cost(3, 3), 6)
        self.assertEqual(fusion_adjusted_cost(1, 2), 1)
        self.assertEqual(fusion_adjusted_cost(0, 64), 0)
        self.assertEqual(fusion_adjusted_cost(3, 10_000), 3 * (MAX_CARD_LAYER + 1) // 2)
        self.assertEqual(fusion_adjusted_cost(-3, 2), 0)
        self.assertEqual(fusion_adjusted_cost("invalid", "invalid"), 0)
        self.assertEqual(fusion_cost_surcharge(3, 2), 1)
        self.assertEqual(fusion_cost_surcharge(3, 3), 3)

    def test_card_cost_calculates_fusion_from_original_cost_before_other_modifiers(self):
        card = CardInstance("MagicBone")
        card.fusion_level = 2
        card.cost_e_override = 4
        card.cost_m_override = 7
        card.temp_heavy_value = 2
        card.mimic_discount = 1
        card.swift_value = 2
        card.temp_swift_value = 1
        card.temp_magic_heavy_value = 1
        card.magic_swift_value = 2

        # Magic Bone's original costs are 0E/4M. Fusion adds 0E/2M first;
        # overrides, Heavy, Swift and Temporary Swift are applied afterward.
        self.assertEqual(card.cost_e, 2)
        self.assertEqual(card.cost_m, 8)

        card.custom_vars.update({
            "formal_logic_permanent_cost_e": 9,
            "formal_logic_permanent_cost_m": 9,
            "formal_logic_temporary_cost_e": 6,
            "formal_logic_temporary_cost_m": 5,
        })
        self.assertEqual(card.cost_e, 4)
        self.assertEqual(card.cost_m, 6)

        card.temp_swift_value = 0
        self.assertEqual(card.cost_e, 5)
        card.temp_swift_value = 1
        self.assertEqual(card.cost_e, 4)

    def test_server_1v1_and_2v2_require_and_pay_the_increased_cost(self):
        for engine_type, target_id in ((GameEngine, 1), (GameEngine2v2, 2)):
            with self.subTest(engine=engine_type.__name__):
                engine = engine_type()
                engine.phase = "action"
                engine.current_player = 0
                for player in engine.players:
                    player.hand = []
                    player.deck = []
                    player.discard = []
                    player.exile = []
                    player.equipment = []
                    player.elixir = 2
                    player.magic = 10
                card = CardInstance("Bone")
                card.fusion_level = 2
                engine.players[0].hand = [card]
                choice = {
                    "target_player": target_id,
                    "target_player_id": target_id,
                    "target_id": target_id,
                }

                allowed, reason = engine.can_play_card(0, card)
                self.assertFalse(allowed)
                self.assertIn("需要3E", reason)

                engine.players[0].elixir = 3
                if engine_type is GameEngine2v2:
                    result = engine.play_card(0, card.instance_id, target_id, choice)
                else:
                    result = engine.play_card(0, card.instance_id, choice)
                self.assertTrue(result.get("success"), result)
                self.assertEqual(engine.players[0].elixir, 0)

    def test_fission_and_fusion_weights_are_doubled_in_builtin_and_package(self):
        self.assertEqual(CARD_DEFS["Fission"].count, 4)
        self.assertEqual(CARD_DEFS["Fusion"].count, 4)
        self.assertEqual(self.package_cards["Fission"].count, 4)
        self.assertEqual(self.package_cards["Fusion"].count, 4)

        probabilities = same_type_draw_probabilities({"Fission", "Fusion", "Rose"})
        self.assertAlmostEqual(probabilities["Fission"], 2 / 9)
        self.assertAlmostEqual(probabilities["Fusion"], 2 / 9)
        self.assertAlmostEqual(probabilities["Rose"], 5 / 9)
        pool_weights = {
            card.def_id: card.draft_weight
            for card in build_draft_pool({"Fission", "Fusion", "Rose"})
        }
        self.assertEqual(pool_weights, {"Fission": 4.0, "Fusion": 4.0, "Rose": 10.0})

    def test_package_and_term_copy_explain_the_new_cost_rule(self):
        fusion = self.package_cards["Fusion"]
        self.assertIn("原始花费", fusion.effect_text)
        self.assertIn("增加50%", fusion.effect_text)
        self.assertIn("向下取整", fusion.effect_text)
        for language in ("zh", "en", "fr", "ja"):
            localized = fusion.effect_text_i18n.get(language, "")
            self.assertTrue(localized, language)
        self.assertIn("其他花费修改在此后结算", GAME_JS)
        self.assertIn("其他花费修改在此后结算", CARD_STYLE_GUIDE)

    def test_multiplayer_cost_display_matches_server_and_does_not_scale_player_penalties(self):
        helpers = GAME_JS.split("function clampClientCardLayer", 1)[1].split(
            "function clampClientExtraHits", 1
        )[0]
        display = "function clampClientCardLayer" + helpers
        costs = GAME_JS.split("function getCardDisplayCosts", 1)[1].split(
            "function isOwnBlindActive", 1
        )[0]
        costs = "function getCardDisplayCosts" + costs
        harness = r'''
const MAX_CLIENT_CARD_LAYER = 64;
function normalizeFlagList(values) { return Array.isArray(values) ? values : []; }
function normalizePlayerId(value) { const n = Number(value); return Number.isFinite(n) ? n : null; }
function getCardLocalIds(card) { return [String(card.def_id || card.id || '')]; }
function cardMatchesAnyLocalId() { return false; }
function getCardDef() { return {}; }
function isStatusImmune() { return false; }
const gameState = { phase: 'action', game_over: false, current_player: 0 };
const cardDef = { id: 'Cost', cost_e: 3, cost_m: 5, swift_value: 1, magic_swift_value: 1, flags: [] };
const owner = { player_id: 0, cards_played_this_turn: { Cost: 2 }, hand: [], custom_statuses: {} };
const ordinary = getCardDisplayCosts({
    def_id: 'Cost', fusion_level: 2, mimic_discount: 1,
    temp_swift_value: 1, temp_heavy_value: 1, temp_magic_heavy_value: 1,
    instance_flags: [], disabled_flags: [],
}, cardDef, owner);
const formal = getCardDisplayCosts({
    def_id: 'Cost', fusion_level: 2, instance_flags: [], disabled_flags: [],
    cost_e_override: 9, cost_m_override: 9,
    custom_vars: {
        formal_logic_permanent_cost_e: 8,
        formal_logic_permanent_cost_m: 8,
        formal_logic_temporary_cost_e: 4,
        formal_logic_temporary_cost_m: 3,
    },
}, { id: 'Cost', cost_e: 1, cost_m: 1, flags: [] }, { player_id: 0, cards_played_this_turn: {}, hand: [] });
process.stdout.write(JSON.stringify({ ordinary, formal }));
'''
        result = _run_node(self, f"{display}\n{costs}\n{harness}")
        self.assertEqual(result["ordinary"]["totalE"], 4)
        self.assertEqual(result["ordinary"]["totalM"], 7)
        self.assertEqual(result["formal"]["totalE"], 4)
        self.assertEqual(result["formal"]["totalM"], 3)

    def test_local_worker_uses_the_same_fusion_cost_formula(self):
        harness = r'''
cardDefs = {
    Cost: { id: 'Cost', name_cn: '费用牌', card_type: 'thorn', cost_e: 3, cost_m: 5, flags: [] },
    Error: { id: 'Error', name_cn: '错误', card_type: 'bloom', cost_e: 0, cost_m: 0, flags: [] },
};
const card = new LocalCard({
    def_id: 'Cost', fusion_level: 2, mimic_discount: 1,
    temp_heavy_value: 1, temp_magic_heavy_value: 1,
    swift_value: 1, temp_swift_value: 1, magic_swift_value: 1,
});
const formal = new LocalCard({
    def_id: 'Cost', fusion_level: 2, cost_e_override: 9, cost_m_override: 9,
    custom_vars: {
        formal_logic_permanent_cost_e: 8,
        formal_logic_permanent_cost_m: 8,
        formal_logic_temporary_cost_e: 4,
        formal_logic_temporary_cost_m: 3,
    },
});
const capped = new LocalCard({ def_id: 'Cost', fusion_level: 10000 });
process.stdout.write(JSON.stringify({
    ordinary: [card.cost_e, card.cost_m],
    formal: [formal.cost_e, formal.cost_m],
    cappedLevel: capped.fusion_level,
}));
'''
        result = _run_node(
            self,
            "globalThis.postMessage = () => {};\n" + LOCAL_WORKER_JS + "\n" + harness,
        )
        self.assertEqual(result["ordinary"], [2, 7])
        self.assertEqual(result["formal"], [5, 5])
        self.assertEqual(result["cappedLevel"], MAX_CARD_LAYER)


if __name__ == "__main__":
    unittest.main()
