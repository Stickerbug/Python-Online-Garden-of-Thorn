"""冰火两重天：10 层灼烧 + 30 层霜冻（同一名敌方玩家）。"""

from pathlib import Path

import db
from game_engine import GameEngine


ROOT = Path(__file__).resolve().parents[1]


def make_engine():
    engine = GameEngine()
    engine.phase = 'action'
    engine.current_player = 0
    for player in engine.players:
        player.health = 100
        player.max_health = 100
        player.fire = 0
        player.custom_statuses = {}
    return engine


def test_achievement_definition_and_locales():
    definition = db.ACHIEVEMENT_DEF_MAP['fire_frost_dual']
    assert definition['reward_dew'] == 800
    assert definition['metric'] == 'flag_fire_frost_dual'
    assert definition['target'] == 1
    assert definition['name_i18n']['zh'] == '冰火两重天'
    for lang in ('zh', 'en', 'fr', 'ja'):
        assert definition['name_i18n'][lang]
        assert definition['description_i18n'][lang]


def test_metric_reaches_threshold_at_10_fire_and_30_frost():
    engine = make_engine()
    engine.players[1].fire = 10
    engine.players[1].custom_statuses['arctic:frost'] = 30

    engine._note_achievement_status_peak(1)

    assert engine.players[0].achievement_max_enemy_fire_frost_dual >= 30
    assert engine.players[0].achievement_max_enemy_frost == 30


def test_metric_stays_below_threshold_when_either_side_is_short():
    engine = make_engine()
    engine.players[1].fire = 9
    engine.players[1].custom_statuses['arctic:frost'] = 100
    engine._note_achievement_status_peak(1)
    assert engine.players[0].achievement_max_enemy_fire_frost_dual < 30

    engine = make_engine()
    engine.players[1].fire = 100
    engine.players[1].custom_statuses['arctic:frost'] = 29
    engine._note_achievement_status_peak(1)
    assert engine.players[0].achievement_max_enemy_fire_frost_dual < 30


def test_flag_is_emitted_by_live_and_match_end_builders():
    source = (ROOT / 'app.py').read_text(encoding='utf-8')
    assert "user_flags.append('flag_fire_frost_dual')" in source
    assert "'flag_fire_frost_dual'," in source
