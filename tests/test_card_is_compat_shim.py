"""`_card_is` 兼容层：GTN-AI 训练采集仍按名字判定，线上 AI 对局会刷 AttributeError。

引擎内部早就换成数据驱动的 ``_card_has_mark`` / ``_card_has_flag``，但线上 AI 运行包
（GTN-AI ``gtn_ai/environment.py``）还在调 ``engine._card_is(card, "Fusion", "vanilla:fusion")``
与 ``engine._card_is(source, "Mimic")``，日志里表现是每局刷
``ai_training_capture_failed ... AttributeError: 'GameEngine' object has no attribute '_card_is'``。
"""

from cards import CardInstance
from game_engine import GameEngine


def test_card_is_matches_namespace_and_local_ids():
    engine = GameEngine()
    fusion = CardInstance("Fusion")
    assert engine._card_is(fusion, "Fusion", "vanilla:fusion") is True
    assert engine._card_is(fusion, "vanilla:fusion") is True
    assert engine._card_is(fusion, "FUSION") is True


def test_card_is_uses_marks_and_rejects_unrelated_cards():
    engine = GameEngine()
    mimic = CardInstance("Mimic")
    basic = CardInstance("Basic")
    assert engine._card_is(mimic, "Mimic") is True
    assert engine._card_is(basic, "Fusion", "vanilla:fusion") is False
    assert engine._card_is(None, "Fusion") is False
    assert engine._card_is(basic) is False
