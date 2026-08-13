import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"
sys.path.insert(0, str(ROOT))


def update_package(filename, changes):
    path = MODS / filename
    with zipfile.ZipFile(path, "r") as source:
        members = [(info, source.read(info.filename)) for info in source.infolist()]
        main_name = next(
            info.filename for info, _ in members
            if info.filename.lower().endswith("mod.json")
        )
        data = json.loads(next(content for info, content in members if info.filename == main_name).decode("utf-8-sig"))

    cards = {
        card.get("id"): card
        for card in data.get("registries", {}).get("cards", [])
        if isinstance(card, dict)
    }
    for card_id, updater in changes.items():
        if card_id not in cards:
            raise KeyError(f"{filename}: missing {card_id}")
        updater(cards[card_id])

    encoded = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    handle, temp_name = tempfile.mkstemp(suffix=".gtnmod", dir=path.parent)
    os.close(handle)
    temp_path = Path(temp_name)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as target:
            for info, content in members:
                target.writestr(info, encoded if info.filename == main_name else content)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def set_fields(**fields):
    def updater(card):
        card.update(fields)
    return updater


def add_flags(*flags, **fields):
    def updater(card):
        values = list(card.get("flags") or [])
        for flag in flags:
            if flag not in values:
                values.append(flag)
        card["flags"] = values
        card.update(fields)
    return updater


def blood_knife(card):
    card.update(
        effect_text=(
            "对自己造成7[[icon:electric_damage]]；每造成3[[icon:electric_damage]]，"
            "回复自己1[[icon:E]]；若实际回复至少1[[icon:E]]，此牌回到手中"
        ),
    )
    card["flags"] = [
        flag for flag in (card.get("flags") or [])
        if flag != "rebound"
    ]


def main():
    update_package("Vanilla Cards.gtnmod", {
        "vanilla:leaf": set_fields(
            heal=1,
            effect_text=(
                "装备拥有者回合开始时，回复目标1[[icon:H]]；若已装备一回合，"
                "可花费1[[icon:E]]，触发：摧毁此装备，选择一个目标，对其造成8[[icon:D]]"
            ),
            events={
                "on_owner_turn_start": {"steps": [{"op": "heal", "target": "target", "amount": 1}]},
                "on_equipment_trigger": {"steps": [
                    {"op": "destroy_self_equipment"},
                    {"op": "deal_damage", "target": "event_target", "amount": 8},
                ]},
                "on_play": {"steps": [
                    {"op": "request_target", "allowed": "any"},
                    {"op": "place_as_equip", "effect_target": "target"},
                ]},
            },
        ),
        "vanilla:magicleaf": set_fields(
            trigger_cost_m=3,
            damage=8,
            effect_text=(
                "装备拥有者回合开始时，回复目标1[[icon:M]]；可花费3[[icon:M]]，"
                "触发：摧毁此装备，选择一个目标，对其造成8[[icon:D]]"
            ),
            events={
                "on_owner_turn_start": {"steps": [{"op": "gain_m", "target": "target", "amount": 1}]},
                "on_play": {"steps": [
                    {"op": "request_target", "allowed": "any"},
                    {"op": "place_as_equip", "effect_target": "target"},
                ]},
                "on_equipment_trigger": {"steps": [
                    {"op": "deal_damage", "target": "target", "amount": 8},
                    {"op": "destroy_current_equipment"},
                ]},
            },
        ),
        "vanilla:magicbattery": set_fields(cost_e=3),
        "vanilla:pill": set_fields(cost_e=4),
    })
    update_package("Garden Cards Addition.gtnmod", {
        "garden:avocado": set_fields(
            effect_text="目标受到实际物理伤害时，回复目标2[[icon:H]]",
        ),
        "garden:kale": add_flags(
            "precision",
            effect_text=(
                "对目标造成14[[icon:D]]；造成实际伤害时，若目标当前[[icon:H]]≤"
                "其[[icon:H]]上限的30%，则再对目标造成14[[icon:D]]"
            ),
        ),
    })
    update_package("Jungle Cards Addition.gtnmod", {
        "jungle:dianthus": add_flags("amplify"),
        "jungle:flower": set_fields(cost_e=4),
        "jungle:maple": add_flags("infinite_exclude"),
    })
    update_package("Ocean Cards Addition.gtnmod", {
        "ocean:sapphire": add_flags(
            "infinite_exclude",
            cost_e=1,
            effect_text=(
                "选择目标，再从自己手牌中选择1张不带有唯一或放逐的攻击牌将其放逐；"
                "回合开始时，若目标可选中且满足该牌的使用条件，自动对目标打出带有放逐的该牌"
            ),
        ),
    })
    update_package("Bio Cards Addition.gtnmod", {
        "bio:blood_knife": blood_knife,
    })

    from tools.sync_mod_locales import sync_package
    for filename in (
        "Vanilla Cards.gtnmod",
        "Garden Cards Addition.gtnmod",
        "Jungle Cards Addition.gtnmod",
        "Ocean Cards Addition.gtnmod",
        "Bio Cards Addition.gtnmod",
    ):
        sync_package(MODS / filename, translate=False)


if __name__ == "__main__":
    main()
