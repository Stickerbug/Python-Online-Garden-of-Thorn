# -*- coding: utf-8 -*-
"""Apply the behavior/event side of the All Cards balance pass."""

from __future__ import annotations

import copy
import json
import os
import pathlib
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"


EVENT_PATCHES = {
    "Coffee": {
        "events": {
            "on_play": {
                "steps": [
                    {"op": "request_target", "allowed": "any"},
                    {"op": "gain_e", "target": "target", "amount": 2},
                    {"op": "card_prop_add", "card": {"ref": "current_card"}, "property": "heavy_value", "amount": 1},
                ]
            }
        }
    },
    "Heavy": {
        "events": {"on_play": {"steps": [
            {"op": "deal_damage", "target": "target", "amount": 36, "hits": 1},
            {"op": "add_status", "target": "source", "status": "stunned", "amount": 1},
        ]}}
    },
    "Shovel": {
        "events": {"on_play": {"steps": [
            {"op": "player_prop_set", "target": "self", "property": "untargetable", "value": 1},
            {"op": "force_end_turn"},
        ]}}
    },
    "Missile": {
        "events": {"on_response": {"steps": [
            {"op": "deal_damage", "target": "target", "amount": 12, "hits": 1},
            {"op": "draw_cards", "target": "self", "amount": 1},
        ]}}
    },
    "Soil": {
        "events": {"on_play": {"steps": [
            {"op": "player_prop_add", "target": "choice_target", "prop": "base_max_health", "value": 40},
            {"op": "heal", "target": "choice_target", "amount": 40},
            {"op": "give_card_to_deck", "target": "choice_target", "card_id": "Dust", "amount": 5, "position": "random"},
        ]}}
    },
    "Magic Antennae": {
        "events": {"on_play": {"steps": [
            {"op": "request_target", "allowed": "any"},
            # Round 22：旧名 garden_show_initial_deck 已删除，规范名是 reveal_card_set。
            {"op": "reveal_card_set", "target": "target"},
            {"op": "draw_cards", "target": "self", "amount": 1},
        ]}}
    },
    "Mecha Antennae": {
        "events": {"on_play": {"steps": [
            {"op": "request_target", "allowed": "any"},
            {
                "op": "request_ui",
                "save_as": "mecha_antennae_type",
                "component": {
                    "type": "modal",
                    "title_cn": "机械触角",
                    "title_en": "Mecha Antennae",
                    "controls": [{
                        "id": "card_type",
                        "type": "select",
                        "label_cn": "选择一种类型",
                        "label_en": "Choose a card type",
                        "options": [
                            {"value": "thorn", "label_cn": "攻击牌", "label_en": "Thorn"},
                            {"value": "bloom", "label_cn": "技能牌", "label_en": "Bloom"},
                            {"value": "root", "label_cn": "装备牌", "label_en": "Root"},
                            {"value": "guard", "label_cn": "反制牌", "label_en": "Guard"},
                        ],
                    }],
                    "buttons": [{"id": "confirm", "role": "confirm", "label_cn": "确定", "label_en": "Confirm"}],
                },
            },
            {
                "op": "garden_mecha_antennae",
                "target": "target",
                "card_type": {
                    "op": "get",
                    "object": {"op": "var", "name": "mecha_antennae_type"},
                    "key": "card_type",
                },
            },
            {
                "op": "request_ui",
                "save_as": "mecha_antennae_pick",
                "component": {
                    "type": "modal",
                    "title_cn": "抽牌堆顶3张",
                    "title_en": "Top 3 cards of your deck",
                    "controls": [{
                        "id": "pick",
                        "type": "card_picker",
                        "zone": "deck",
                        "target": "source",
                        "allowed_instance_ids": {"op": "deck_top_ids", "target": "source", "count": 3},
                    }],
                    "buttons": [{"id": "confirm", "role": "confirm", "label_cn": "确定", "label_en": "Confirm"}],
                },
            },
            {
                "op": "garden_mecha_antennae_resolve",
                "target": "source",
                "card_id": {
                    "op": "get",
                    "object": {"op": "var", "name": "mecha_antennae_pick"},
                    "key": "pick",
                },
            },
        ]}}
    },
    "Wind": {
        "events": {"on_play": {"steps": [
            {"op": "request_target", "allowed": "any"},
            {"type": "desert_wind_schedule", "params": {"target": "target"}},
        ]}}
    },
    "Magnet": {
        "events": {"on_play": {"steps": [
            {"op": "request_target", "allowed": "not_self"},
            {"op": "direct_damage", "target": "target", "amount": 2, "damage_type": "magic", "damage_tag": "battery"},
            {"op": "reveal_enemy_hand", "target": "target"},
            {"op": "request_card", "target": "target", "zone": "hand", "choice_type": "choose_card_from_hand", "cancellable": False},
            {"op": "move_to_hand", "card": "chosen_card", "target": "self"},
        ]}}
    },
    "Dead Leaf": {
        "events": {"on_play": {"steps": [
            {"op": "deal_damage", "target": "target", "amount": 6},
            {"op": "ocean_dead_leaf_slow_if_no_counter", "target": "target", "amount": 1},
        ]}}
    },
    "Needle": {
        "events": {"on_play": {"steps": [
            {"op": "deal_damage", "target": "target", "amount": 4},
            {"op": "status_add_named", "target": "target", "status": "ocean:unable_counter", "amount": 1},
        ]}}
    },
    "Blueberries": {
        "events": {"on_play": {"steps": [
            {"op": "deal_damage", "target": "target", "amount": 1, "hits": 4, "on_hit": [
                {"op": "arctic_apply_frost", "target": "target", "amount": 3},
            ]},
        ]}}
    },
    "Icicle": {
        "events": {"on_play": {"steps": [
            {"op": "deal_damage", "target": "target", "amount": 6, "on_hit": [
                {"op": "arctic_apply_frost", "target": "target", "amount": 3},
            ]},
            {"op": "arctic_icicle_shuffle_discard"},
        ]}}
    },
    "Clover": {
        "events": {"target_turn_start": {"steps": [
            {"type": "hel_add_luck", "params": {"target": "target", "amount": 4}},
        ]}}
    },
    "Magic Clover": {
        "events": {"on_play": {"steps": [
            {"op": "request_target", "allowed": "any"},
            {"type": "hel_magic_clover_trigger", "params": {"target": "target"}},
        ]}}
    },
    "Grass": {
        # Workbook 14 dropped the "已装备1回合时" requirement.
        "events": {
            "on_equipment_trigger": {
                "max_uses_per_turn": 1,
                "ready_turns": 0,
                "steps": [{"op": "heal", "target": "target", "amount": 6}],
            },
            "on_play": {
                "steps": [
                    {"op": "request_target", "allowed": "any"},
                    {"op": "place_as_equip", "effect_target": "choice_target"},
                ]
            },
        }
    },
    "Blood Dice": {
        "events": {"on_play": {"steps": [
            {"op": "request_target", "allowed": "any"},
            {"type": "hel_blood_dice", "params": {"target": "target", "luck": 10, "damage": 6}},
        ]}}
    },
    "Bugatti": {
        "events": {"target_turn_start_after_draw": {"steps": [
            {"type": "hel_bugatti_draw", "params": {"target": "target"}},
        ]}}
    },
    "Magic Trident": {
        "events": {"on_play": {"steps": [
            {"op": "request_target", "allowed": "not_self"},
            {"op": "ocean_charge_self_damage"},
            {"op": "deal_damage", "target": "target", "amount": 18, "hits": 1},
        ]}}
    },
    "Sugar": {
        "events": {"on_play": {"steps": [
            {"type": "bio_sugar_attack", "params": {"target": "target", "amount": 2, "hits": 6}},
        ]}}
    },
    "Blood Diamond": {
        "events": {"on_play": {"steps": [
            {"type": "bio_blood_diamond_attack", "params": {"target": "target", "amount": 3}},
        ]}}
    },
}


META_PATCHES = {
    "Coffee": {"damage": 0, "hits": 1},
    "Heavy": {"damage": 36, "hits": 1},
    "Shovel": {"damage": 0, "hits": 0},
    "Missile": {"damage": 12, "hits": 1},
    "Soil": {"damage": 0, "hits": 0},
    "Magic Antennae": {"damage": 0, "hits": 0},
    "Dead Leaf": {"damage": 6, "hits": 1},
    "Needle": {"damage": 4, "hits": 1},
    "Blueberries": {"damage": 1, "hits": 4},
    "Icicle": {"damage": 6, "hits": 1},
    "Blood Diamond": {"damage": 3, "hits": 4},
    "Sugar": {"damage": 2, "hits": 6},
    "Blood Dice": {"damage": 6, "hits": 1},
    "Magic Pearl": {"damage": 5, "hits": 1},
    "Magic Trident": {"damage": 18, "hits": 1},
    "Broccoli": {"damage": 10, "hits": 1},
    "Clay": {"damage": 5, "hits": 1},
}


def main_member(zf):
    names = {name.lower(): name for name in zf.namelist()}
    for candidate in ("mod.json", "gtnmod.json"):
        if candidate in names:
            return names[candidate]
    raise ValueError("package has no mod.json")


def read_package(path):
    with zipfile.ZipFile(path, "r") as zf:
        main = main_member(zf)
        data = json.loads(zf.read(main).decode("utf-8-sig"))
        members = {item.filename: zf.read(item.filename) for item in zf.infolist()}
    return data, members, main


def write_package(path, data, members, main):
    members = dict(members)
    members[main] = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    handle, temp_name = tempfile.mkstemp(suffix=".gtnmod", dir=str(path.parent))
    os.close(handle)
    temp_path = pathlib.Path(temp_name)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for filename, content in members.items():
                zf.writestr(filename, content)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def find_card(data, name):
    for card in data.get("registries", {}).get("cards", []) or []:
        if str(card.get("name_en") or "") == name or str(card.get("legacy_id") or "") == name:
            return card
    return None


def main():
    for path in sorted(MODS.glob("*.gtnmod")):
        data, members, main_member_name = read_package(path)
        changed = False
        for name, patch in {**EVENT_PATCHES, **META_PATCHES}.items():
            card = find_card(data, name)
            if not card:
                continue
            if name in EVENT_PATCHES:
                card["events"] = copy.deepcopy(EVENT_PATCHES[name]["events"])
                card.pop("v2_events", None)
                changed = True
            if name in META_PATCHES:
                for field, value in META_PATCHES[name].items():
                    card[field] = value
                changed = True
        if changed:
            write_package(path, data, members, main_member_name)
            print("events updated", path.name)


if __name__ == "__main__":
    main()
