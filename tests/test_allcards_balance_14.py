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
    "MagicGlass": "Garden Cards Addition.gtnmod",
    "Coffee": "Vanilla Cards.gtnmod",
    "Sewage": "Vanilla Cards.gtnmod",
    "Coconut": "Desert Cards Addition.gtnmod",
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

    # --------------------------------------------------------- Sewage GB-386
    def test_sewage_logs_fallback_when_target_has_no_equipment(self):
        # GB-386：目标没装备时不弹空选择窗、不静默作废——补「没有可摧毁的装备」。
        engine = self.action_engine()
        engine.players[1].equipment = []
        sewage = CardInstance("Sewage")

        result = self.play(engine, 0, sewage, self.target_choice(1))

        self.assertTrue(result.get("success"), result)
        if getattr(engine, "pending_response", None):
            engine.resolve_forced_response()
        self.assertIsNone(engine.pending_choice)  # 没有卡在空窗口上
        self.assertTrue(
            any("没有可摧毁的装备" in line for line in engine.log),
            engine.log,
        )

    def test_sewage_still_destroys_chosen_equipment(self):
        from game_engine import EquipmentInstance

        engine = self.action_engine()
        disc = CardInstance("Disc")
        engine.players[1].equipment = [EquipmentInstance(disc, 1)]
        sewage = CardInstance("Sewage")

        result = self.play(engine, 0, sewage, self.target_choice(1))
        self.assertTrue(result.get("success"), result)
        if getattr(engine, "pending_response", None):
            engine.resolve_forced_response()
        self.assertIsNotNone(engine.pending_choice)
        resolved = engine.resolve_choice(0, {
            "target_player": 1, "target_player_id": 1, "target_id": 1,
            "target_instance_id": disc.instance_id,
        })
        self.assertTrue(resolved.get("success"), resolved)
        self.assertEqual(0, len(engine.players[1].equipment))
        self.assertTrue(any("摧毁" in line for line in engine.log), engine.log)

    # ------------------------------------------------------- Coconut GB-384
    def test_coconut_can_be_reequipped_after_trigger_destroys_itself(self):
        # GB-299/384/333：装备触发自毁不再给实例残留「打出中自毁」标记，
        # 同一实例第二次打出能正常回到装备区。
        engine = self.action_engine(GameEngine2v2)
        coconut = CardInstance("Coconut")
        engine.players[0].hand = [coconut]

        result = self.play(engine, 0, coconut, self.target_choice(0))
        self.assertTrue(result.get("success"), result)
        if getattr(engine, "pending_response", None):
            engine.resolve_forced_response()
        self.assertTrue(any(
            getattr(eq, "card_instance", None) is coconut
            for eq in engine.players[0].equipment
        ))

        # 模拟装备触发（椰子触发：摧毁本装备）。
        engine._run_v2_card_event(
            0, coconut, "on_equipment_trigger",
            {"target_player": 1, "target_player_id": 1, "target_id": 1},
        )
        self.assertEqual(0, len(engine.players[0].equipment))
        self.assertNotIn("_equipment_destroyed_this_play", coconut.__dict__)

        # 第二次打出同一实例：应重新装备，而不是进弃牌堆。
        engine.players[0].discard.remove(coconut)
        engine.players[0].hand = [coconut]
        result2 = self.play(engine, 0, coconut, self.target_choice(0))
        self.assertTrue(result2.get("success"), result2)
        if getattr(engine, "pending_response", None):
            engine.resolve_forced_response()
        if engine.pending_choice is not None:
            resolved2 = engine.resolve_choice(0, self.target_choice(0))
            self.assertTrue(resolved2.get("success"), resolved2)
        self.assertTrue(any(
            getattr(eq, "card_instance", None) is coconut
            for eq in engine.players[0].equipment
        ))

    # ------------------------------------------------------------ Magic Glass
    def test_magic_glass_is_three_damage_split_over_fission_three(self):
        # 平衡 2026-10-07：3D + 裂变3（留存基线 3，不是 1+2）。按裂变规则
        # （每次 ceil(原始×聚变/裂变)）拆成 3 段 ×1D，每段命中回自己 1M，
        # 打出后裂变回落到基线 3（回手再打仍是 3 段）。
        engine = self.action_engine()
        engine.players[0].magic = 0
        engine.players[0].max_magic = 10
        engine.players[1].health = 100
        glass = CardInstance("MagicGlass")
        self.assertEqual(3, glass.fission_base)

        result = self.play(engine, 0, glass, self.target_choice(1))

        self.assertTrue(result.get("success"), result)
        if getattr(engine, "pending_response", None):
            engine.resolve_forced_response()
        self.assertEqual(97, engine.players[1].health)  # 3 段 × ceil(3/3)=1
        self.assertEqual(3, engine.players[0].magic)  # 每段命中 +1M
        self.assertEqual(3, glass.fission_level)
        self.assertEqual(3, getattr(glass, "fission_base", 3))

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

    def test_blood_diamond_applies_one_bleed_per_petal(self):
        """平衡改动（反馈 #152/#155）：血钻石改成珊瑚式 —— 单次命中 + 永久裂变 4。

        4 个子瓣各结算 1 层流血（广域打击所以双方各 4 层），不再叠出 16 层。
        详细契约见 tests/test_blood_diamond_redesign.py。
        """
        engine = self.action_engine()
        diamond = CardInstance("Blood Diamond")

        result = self.play(engine, 0, diamond, self.target_choice(1))

        self.assertTrue(result.get("success"), result)
        self.assertEqual(4, engine.players[1].bleed)
        self.assertEqual(4, engine.players[0].bleed)
        self.assertEqual(4, diamond.fission_level)

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
    def test_ankh_rolls_back_to_own_turn_start_and_skips_defeated(self):
        # 平衡 2026-10-07：所有玩家的 H/E/M 和状态回到各自上个自己回合
        # 开始时的数值（不回到对局开始、不复活），打出者再 -2E。
        engine = self.action_engine(GameEngine2v2)
        engine.players[0].health = 80
        engine.players[0].elixir = 6
        engine.players[0].magic = 4
        engine.players[0].custom_statuses["poisoned"] = 2
        engine._save_turn_start_snapshot(0)
        engine.players[2].health = 70
        engine.players[2].custom_statuses["burning"] = 3
        engine._save_turn_start_snapshot(2)

        engine.players[0].health = 30
        engine.players[0].elixir = 1
        engine.players[0].magic = 0
        engine.players[0].custom_statuses["poisoned"] = 9
        engine.players[2].health = 10
        engine.players[2].custom_statuses = {}
        engine.players[1].health = 0
        engine.players[1].hand = [CardInstance("Basic")]
        engine.players[1].deck = [CardInstance("Bone")]
        ankh = CardInstance("Ankh")

        result = self.play(engine, 0, ankh, self.target_choice(0))
        self.assertTrue(result.get("success"), result)
        # 结算反制窗口后再断言回退结果：无人可反制时是纯等待窗，
        # 由 resolve_forced_response 到点结算（与 app 层 worker 同口径）。
        if engine.pending_response is not None:
            if engine.pending_response.get("forced_wait"):
                engine.resolve_forced_response()
            else:
                for entry in list(engine.pending_response.get("counter_cards", [])):
                    if entry.get("responder_id") is not None:
                        engine.handle_response(int(entry["responder_id"]), None)
        self.assertEqual(80, engine.players[0].health)
        self.assertEqual(4, engine.players[0].elixir)  # 回到6E后再-2E
        self.assertEqual(4, engine.players[0].magic)
        self.assertEqual(2, engine.players[0].custom_statuses.get("poisoned"))
        self.assertEqual(70, engine.players[2].health)
        self.assertEqual(3, engine.players[2].custom_statuses.get("burning"))
        # 「所有玩家」默认不含阵亡玩家：不复活、区域不动。
        self.assertEqual(0, engine.players[1].health)
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

    def test_magic_pearl_keeps_one_autoplay_copy_per_turn_after_repeated_plays(self):
        # 表格14 R170：文案是"回合开始时……自动对其打出一张"，没有
        # "本局每打出过1次就额外打出1张"的成长条款，所以重复打出也只留一个队列项。
        engine = self.action_engine()
        engine.players[1].health = 200
        first = CardInstance("Magic Pearl")
        second = CardInstance("Magic Pearl")
        engine.players[0].hand = [first, second]
        self.play(engine, 0, first, self.target_choice(1))
        self.play(engine, 0, second, self.target_choice(1))

        entries = engine.players[0].custom_vars.get("ocean_auto_cards") or []
        self.assertEqual(1, len(entries), entries)

        engine.players[1].health = 100
        engine.players[1].hand = []
        engine._run_ocean_auto_cards_turn_start(0)
        self.assertEqual(95, engine.players[1].health)

    def test_magic_pearl_text_and_queue_step_follow_workbook_14(self):
        import json
        import zipfile

        with zipfile.ZipFile(MODS / "Ocean Cards Addition.gtnmod") as package:
            pearl_spec = json.loads(package.read("mod.json").decode("utf-8"))
            pearl_locales = {
                language: json.loads(package.read(f"locales/{language}.json").decode("utf-8"))
                for language in ("zh", "en", "fr", "ja")
            }
        pearl = next(
            card for card in pearl_spec["registries"]["cards"]
            if card["id"] == "ocean:magic_pearl"
        )
        self.assertIn("若目标可选中", pearl["effect_text"])
        self.assertNotIn("每打出过", pearl["effect_text"])

        queue_step = None

        def walk(node):
            nonlocal queue_step
            if isinstance(node, dict):
                # Round 50 / 批次 AN：队列自动打出并进 auto_play 伞
                # （``auto_play(mode:"queue")``），旧名 queue_auto_play 已退役。
                if node.get("op") == "auto_play" and str(node.get("mode") or "") == "queue":
                    queue_step = node
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(pearl["events"])
        self.assertIsNotNone(queue_step)
        self.assertEqual("target", queue_step["target"])
        self.assertTrue(queue_step.get("dedupe"), queue_step)

        for language in ("zh", "en", "fr", "ja"):
            self.assertEqual(
                pearl["effect_text_i18n"][language],
                pearl_locales[language]["cards"]["ocean:magic_pearl"]["effect_text"],
            )

    def test_dizzy_text_follows_workbook_14(self):
        import json
        import zipfile

        with zipfile.ZipFile(MODS / "Desert Cards Addition.gtnmod") as package:
            dizzy_spec = json.loads(package.read("mod.json").decode("utf-8"))
            locales = {
                language: json.loads(package.read(f"locales/{language}.json").decode("utf-8"))
                for language in ("zh", "en", "fr", "ja")
            }
        dizzy = next(
            card for card in dizzy_spec["registries"]["cards"]
            if card["id"] == "desert_cards_addition:dizzy"
        )
        self.assertIn("所有牌不可取消", dizzy["effect_text"])
        self.assertNotIn("此牌", dizzy["effect_text"])
        for language in ("zh", "en", "fr", "ja"):
            self.assertEqual(
                dizzy["effect_text_i18n"][language],
                locales[language]["cards"]["desert_cards_addition:dizzy"]["effect_text"],
            )

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
