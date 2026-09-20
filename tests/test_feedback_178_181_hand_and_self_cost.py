"""反馈 #178（血玉米文案）与 #181（布加迪手牌上限 -2）的回归守卫。"""

import json
import zipfile
from pathlib import Path

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import EquipmentInstance, GameEngine
from mod_loader import load_mod

ROOT = Path(__file__).resolve().parents[1]
DESERT = ROOT / "mods" / "Desert Cards Addition.gtnmod"
HEL = ROOT / "mods" / "Hel Cards Addition.gtnmod"


def _register(package: Path, card_ids):
    mod = load_mod(str(package))
    assert not mod.errors, mod.errors
    cards = {card.id: card for card in mod.cards}
    for card_id in card_ids:
        if card_id in cards:
            CARD_DEFS[card_id] = cards[card_id].to_card_def()
    return cards


def _engine():
    engine = GameEngine()
    engine.phase = "action"
    engine.current_player = 0
    for player in engine.players:
        player.hand = []
        player.deck = []
        player.discard = []
        player.equipment = []
        player.health = 100
        player.max_health = 100
        player.armor = 0
    engine.players[0].elixir = 20
    return engine


# ---------------------------------------------------------------- #178 血玉米

def test_blood_corn_says_lose_health_in_every_language():
    with zipfile.ZipFile(DESERT) as package:
        data = json.loads(package.read("mod.json").decode("utf-8-sig"))
        zh = json.loads(package.read("locales/zh.json").decode("utf-8-sig"))
    card = next(card for card in data["registries"]["cards"] if card["id"] == "desert_cards_addition:blood_corn")
    assert "失去3[[icon:H]]" in card["effect_text"]
    assert "对自己造成3" not in card["effect_text"]
    assert "失去3[[icon:H]]" in zh["cards"]["desert_cards_addition:blood_corn"]["effect_text"]


def test_blood_corn_self_cost_is_health_loss_not_damage():
    _register(DESERT, ("BloodCorn",))
    engine = _engine()
    engine.players[0].armor = 5
    corn = CardInstance("BloodCorn")
    engine.players[0].hand = [corn]

    result = engine.play_card(0, corn.instance_id, {"target_player": 1})

    assert result.get("success"), result
    assert engine.players[0].health == 97
    assert engine.players[0].armor == 5  # 失去生命不吃护甲
    self_log = [line for line in engine.log if "血玉米" in str(line) and "H=" in str(line)]
    assert self_log, engine.log[-5:]
    assert "失去3H" in self_log[-1]
    assert "伤害" not in self_log[-1]


# ---------------------------------------------------------------- #181 布加迪

def test_bugatti_lowers_target_hand_limit_by_two():
    _register(HEL, ("Bugatti",))
    engine = _engine()
    bugatti = CardInstance("Bugatti")
    engine.players[0].hand = [bugatti]

    assert engine.players[1].hand_limit() == 7
    result = engine.play_card(0, bugatti.instance_id, {"target_player": 1})
    assert result.get("success"), result
    assert engine.players[1].hand_limit() == 5
    assert engine.players[0].hand_limit() == 7  # 只影响目标


def test_flag_only_hand_limit_penalty_still_counts_one():
    """旧牌只写了 hand_limit_penalty 而没有数值时，仍按 1 层惩罚（不回归成 -2）。"""
    card_id = "__test_hand_limit_penalty_only__"
    previous = CARD_DEFS.get(card_id)
    CARD_DEFS[card_id] = CardDef(
        id=card_id,
        name_en="Flag Only Penalty",
        name_cn="仅 flag 惩罚",
        cost_e=0,
        cost_m=0,
        card_type="root",
        count=1,
        quality="test",
        description="",
        effect_text="",
        flags={"hand_limit_penalty"},
    )
    try:
        engine = _engine()
        engine.players[0].equipment = [EquipmentInstance(CardInstance(card_id), 1)]
        engine._refresh_hand_limit_bonuses()
        assert engine.players[1].hand_limit() == 6
    finally:
        if previous is None:
            CARD_DEFS.pop(card_id, None)
        else:
            CARD_DEFS[card_id] = previous
