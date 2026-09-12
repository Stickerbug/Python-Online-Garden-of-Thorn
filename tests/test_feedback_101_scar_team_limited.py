"""反馈 #101：疤痕的随机池在 1v1/URF 排除队伍限定牌，2v2 保留。"""

import random

from cards import CARD_DEFS, CardDef
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2


LIMITED_ID = '__test_scar_team_limited__'
NORMAL_ID = '__test_scar_team_normal__'


def _make_def(def_id, flags):
    return CardDef(
        id=def_id,
        name_en=def_id,
        name_cn=def_id,
        cost_e=0,
        cost_m=0,
        card_type='bloom',
        count=1,
        quality='test',
        description='',
        effect_text='',
        flags=set(flags),
    )


def setup_module():
    CARD_DEFS[LIMITED_ID] = _make_def(LIMITED_ID, {'team_limited'})
    CARD_DEFS[NORMAL_ID] = _make_def(NORMAL_ID, set())


def teardown_module():
    CARD_DEFS.pop(LIMITED_ID, None)
    CARD_DEFS.pop(NORMAL_ID, None)


def _capture_pool(monkeypatch, engine):
    captured = []
    monkeypatch.setattr(random, 'choice', lambda seq: captured.append(list(seq)) or seq[0])
    engine._void_weighted_card_id(None, exclude=set())
    return captured[0]


def test_one_v_one_scar_pool_excludes_team_limited(monkeypatch):
    pool = _capture_pool(monkeypatch, GameEngine())
    assert NORMAL_ID in pool
    assert LIMITED_ID not in pool
    for def_id in pool:
        assert 'team_limited' not in set(CARD_DEFS[def_id].flags or set())


def test_two_v_two_scar_pool_keeps_team_limited(monkeypatch):
    pool = _capture_pool(monkeypatch, GameEngine2v2())
    assert LIMITED_ID in pool
