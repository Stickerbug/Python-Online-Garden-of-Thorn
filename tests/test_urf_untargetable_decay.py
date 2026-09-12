"""反馈 #107：无限火力里“不可选中”层数必须在本人回合开始衰减。

对照依据（当前工作区文件）：

* 1v1：``game_engine.py:16525-16529``，``_run_timed_effects_for_turn`` 之后衰减
  ``untargetable``，归零时写日志；
* 2v2：``game_engine_2v2.py:1904-1908``，同一段逻辑；
* URF：``game_engine_urf.py`` 的 ``_apply_turn_start_effects`` 是整段覆写，修复前
  只有铲子分支（``game_engine_urf.py:433-436``）会碰 ``untargetable``，于是黄瓜
  （``ocean:cucumber``：``events.on_response.resolution.suppress_responder_untargetable``
  + ``after_resolution`` 的 ``player_status_layers(status=untargetable, amount=1)``）
  给出的一层不可选中会永久留在无限火力对局里。
"""

import pytest

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from game_engine_urf import GameEngineInfiniteFire


ATTACK_TEST_CARD_ID = "__test_urf_untargetable_attack__"
CUCUMBER_TEST_CARD_ID = "__test_urf_untargetable_cucumber__"


def setup_module():
    # 攻击牌：任意一张攻击本人对手的“荆棘”牌都会开响应窗口（与
    # tests/test_urf_rebound_response.py 的夹具同款）。
    CARD_DEFS[ATTACK_TEST_CARD_ID] = CardDef(
        id=ATTACK_TEST_CARD_ID,
        name_en="Untargetable Attack Test",
        name_cn="不可选中攻击测试",
        cost_e=1,
        cost_m=0,
        card_type="thorn",
        count=1,
        quality="test",
        description="",
        effect_text="",
        flags=set(),
        damage=1,
    )
    # 反制牌：字段与 ``ocean:cucumber`` 的数据声明一致（mods/Ocean Cards
    # Addition.gtnmod → mod.json 的 events.on_response）。
    CARD_DEFS[CUCUMBER_TEST_CARD_ID] = CardDef(
        id=CUCUMBER_TEST_CARD_ID,
        name_en="Cucumber Layer Test",
        name_cn="黄瓜层数测试",
        cost_e=1,
        cost_m=0,
        card_type="guard",
        count=1,
        quality="test",
        description="",
        effect_text="",
        flags={"exile"},
        response_trigger="targeted",
        v2_events={
            "on_response": {
                "steps": [],
                "resolution": {
                    "suppress_responder_untargetable": True,
                    "after_resolution": [
                        {"op": "player_status_layers", "amount": 1, "status": "untargetable"},
                    ],
                },
            },
        },
    )


def teardown_module():
    CARD_DEFS.pop(ATTACK_TEST_CARD_ID, None)
    CARD_DEFS.pop(CUCUMBER_TEST_CARD_ID, None)


def make_engine(engine_cls):
    engine = engine_cls()
    engine.phase = "action"
    engine.round_num = 1
    engine.first_player = 0
    engine.current_player = 0
    for player in engine.players:
        player.health = 100
        player.max_health = 100
        player.elixir = 100
        player.magic = 100
        player.hand = []
        player.deck = []
        player.discard = []
        player.exile = []
        player.equipment = []
    return engine


def turn_start_log(engine):
    return "\n".join(str(entry) for entry in getattr(engine, "log", []) or [])


@pytest.mark.parametrize("engine_cls", [GameEngine, GameEngine2v2, GameEngineInfiniteFire])
def test_untargetable_layer_decays_on_own_turn_start_in_every_mode(engine_cls):
    """三引擎对照：本人回合开始时一层不可选中必须衰减为 0。"""
    engine = make_engine(engine_cls)
    engine.players[0].untargetable = 1

    engine._apply_turn_start_effects(0)

    assert engine.players[0].untargetable == 0
    assert "不可选中效果结束" in turn_start_log(engine)
    # 对手不该被牵连
    assert int(getattr(engine.players[1], "untargetable", 0) or 0) == 0


@pytest.mark.parametrize("engine_cls", [GameEngine, GameEngine2v2, GameEngineInfiniteFire])
def test_untargetable_layers_decay_one_per_turn(engine_cls):
    """多层不可选中每回合只掉一层，且中途不写“结束”日志。"""
    engine = make_engine(engine_cls)
    engine.players[1].untargetable = 2

    engine._apply_turn_start_effects(1)
    assert engine.players[1].untargetable == 1
    assert "不可选中效果结束" not in turn_start_log(engine)

    engine._apply_turn_start_effects(1)
    assert engine.players[1].untargetable == 0
    assert "不可选中效果结束" in turn_start_log(engine)


def test_urf_cucumber_response_layer_expires_on_next_turn_start():
    """URF 里黄瓜响应给出的一层不可选中，在响应者下个回合开始归零（反馈 #107 主场景）。"""
    engine = make_engine(GameEngineInfiniteFire)
    attack = CardInstance(ATTACK_TEST_CARD_ID)
    cucumber = CardInstance(CUCUMBER_TEST_CARD_ID)
    engine.players[0].hand = [attack]
    engine.players[1].hand = [cucumber]

    play_result = engine.play_card(0, attack.instance_id, {"target_player": 1})
    assert play_result.get("needs_response"), play_result

    response_result = engine.handle_response(1, cucumber.instance_id)
    assert response_result.get("success"), response_result
    assert int(engine.players[1].untargetable or 0) == 1

    engine._apply_turn_start_effects(1)

    assert int(engine.players[1].untargetable or 0) == 0
    assert "不可选中效果结束" in turn_start_log(engine)


def test_urf_shovel_branch_still_clears_untargetable():
    """补齐衰减块后，铲子分支原本的清除行为保持不变。"""
    engine = make_engine(GameEngineInfiniteFire)
    player = engine.players[0]
    player.untargetable = 1
    player.shovel_active = True

    engine._apply_turn_start_effects(0)

    assert int(player.untargetable or 0) == 0
    assert not player.shovel_active
    assert "铲子效果结束" in turn_start_log(engine)
