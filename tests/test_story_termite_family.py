"""Termite family data checks against development workbook 14 (爬塔怪物设计 R49-R51, R64).

The mound's psionic rules live in ``tests/test_story_jungle_factory.py``; this file
guards the pieces that are easy to drop when the mound/minion data is edited:
the three "Resolve" (决意) moves must grant one round of Invincible first, and the
minion cycles/health must stay on the workbook values.
"""

from story_content import STORY_ENEMIES


def _move(definition, index):
    return definition['moves'][index]


def _effect_types(move):
    return [effect.get('type') for effect in move.get('effects') or ()]


def test_resolve_moves_start_with_a_round_of_invincibility():
    for enemy_id, damage in (
        ('termite_soldier', 20),
        ('termite_worker', 16),
        ('termite_overmind', 23),
    ):
        resolve = _move(STORY_ENEMIES[enemy_id], -1)
        assert resolve['name']['zh'] == '决意'
        effects = list(resolve.get('effects') or ())
        # 无敌先结算，然后才是伤害与自毁（表格：这回合无敌XX D 击杀自己）。
        assert effects[0]['type'] == 'gain_status'
        assert effects[0]['status'] == 'invincible'
        assert effects[0]['amount'] == 1
        # 必须立即生效：delay 到回合结束的话，决意已经自毁、无敌等于没加。
        assert effects[0].get('immediate') is True
        assert effects[1]['type'] == 'damage'
        assert effects[1]['amount'] == damage
        assert effects[-1]['type'] == 'self_kill'


def test_termite_cycles_and_health_match_the_workbook():
    assert STORY_ENEMIES['termite_soldier']['move_order'] == (0, 1, 2)
    assert STORY_ENEMIES['termite_overmind']['move_order'] == (0, 1)
    # 白工蚁没有显式 move_order：走 move_index % 2，单挑时改用第 3 招（狂暴）。
    assert 'move_order' not in STORY_ENEMIES['termite_worker']
    assert STORY_ENEMIES['termite_worker']['script'] == 'termite_worker'
    # 白蚁丘 1-2 循环（固守 / 号令）。
    assert STORY_ENEMIES['termite_mound']['move_order'] == (0, 1)
    assert [move['name']['zh'] for move in STORY_ENEMIES['termite_mound']['moves']] == ['固守', '号令']
    assert STORY_ENEMIES['termite_mound']['max_health'] == 291
    assert STORY_ENEMIES['termite_mound']['lunatic_max_health'] == 308
    for enemy_id in ('termite_soldier', 'termite_worker', 'termite_overmind'):
        assert 'psionic_connection' in STORY_ENEMIES[enemy_id]['traits']
