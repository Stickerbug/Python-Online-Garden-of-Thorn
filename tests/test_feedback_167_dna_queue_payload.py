"""反馈 #167：装备多个 DNA 时每回合只能变换一次。

根因：``_bio_resolve_dna_choice`` 在排队第二个 DNA 选择时只返回
``{'success': True, 'needs_choice': True}``，服务端据此再发一次
``choice_request``，内容是空的；客户端上刚弹出的真实选择窗口被这份空请求
顶掉（并可能立刻按取消回传），于是多个 DNA 每回合只完成一次变换。

这里同时守住引擎侧的返回值与服务端「用 pending_choice 拼请求」的写法。
"""

from pathlib import Path

from cards import CARD_DEFS, CardInstance
from game_engine import EquipmentInstance, GameEngine
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
BIO_PACKAGE = ROOT / "mods" / "Bio Cards Addition.gtnmod"


def _register_dna():
    mod = load_mod(str(BIO_PACKAGE))
    if mod.errors:
        raise AssertionError(mod.errors)
    cards = {}
    for card in mod.cards:
        CARD_DEFS[card.id] = card.to_card_def()
        cards[card.id] = card
    return cards


def _engine_with_dnas(count: int) -> GameEngine:
    engine = GameEngine()
    engine.phase = "action"
    engine.round_num = 2
    engine.first_player = 0
    engine.current_player = 0
    for player in engine.players:
        player.health = 100
        player.deck = []
        player.hand = []
        player.discard = []
        player.equipment = []
    player = engine.players[0]
    player.hand = [CardInstance("Basic"), CardInstance("Bone")]
    player.equipment = [EquipmentInstance(CardInstance("DNA"), 0) for _ in range(count)]
    return engine


def test_each_equipped_dna_asks_for_its_own_transform():
    previous = CARD_DEFS.get("DNA")
    try:
        _register_dna()
        engine = _engine_with_dnas(2)
        assert engine._bio_queue_dna_turn_start(0, "") is True
        prompts = 0
        while engine.pending_choice is not None and prompts < 5:
            prompts += 1
            target = engine.pending_choice["hand_cards"][0]["instance_id"]
            result = engine.resolve_choice(0, {"target_instance_id": target})
            if result.get("needs_choice"):
                assert result.get("choice_type") == "choose_card_from_hand", result
                assert result.get("hand_cards"), "第二个 DNA 的请求必须带着候选手牌"
                assert result.get("card", {}).get("def_id") == "DNA", result
            else:
                assert result.get("success"), result
        assert prompts == 2
    finally:
        if previous is None:
            CARD_DEFS.pop("DNA", None)
        else:
            CARD_DEFS["DNA"] = previous


def test_only_one_dna_still_asks_once():
    previous = CARD_DEFS.get("DNA")
    try:
        _register_dna()
        engine = _engine_with_dnas(1)
        assert engine._bio_queue_dna_turn_start(0, "") is True
        target = engine.pending_choice["hand_cards"][0]["instance_id"]
        result = engine.resolve_choice(0, {"target_instance_id": target})
        assert result.get("success") and not result.get("needs_choice"), result
        assert engine.pending_choice is None
    finally:
        if previous is None:
            CARD_DEFS.pop("DNA", None)
        else:
            CARD_DEFS["DNA"] = previous


def test_server_emits_live_pending_choice_payload():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "live_pending = getattr(engine, 'pending_choice', None)" in source
    assert (
        "live_pending if isinstance(live_pending, dict) and live_pending else result"
        in source
    )
