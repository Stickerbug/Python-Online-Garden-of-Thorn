import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import pytest

from card_i18n import CARD_I18N
from cards import CARD_DEFS, CardInstance, YGGDRASIL_HEAL
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod
from story_content import STORY_RELICS


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('engine_type,target_id', ((GameEngine, 1), (GameEngine2v2, 2)))
def test_yggdrasil_heals_living_target_for_twenty_five(engine_type, target_id):
    engine = engine_type()
    target = engine.players[target_id]
    target.health = 50

    engine._effect_yggdrasil(
        0,
        CardInstance('Yggdrasil'),
        {'target_player': target_id, 'target_player_id': target_id, 'target_id': target_id},
    )

    assert YGGDRASIL_HEAL == 25
    assert target.health == 75
    assert any('回复25H' in line for line in engine.log)


def test_yggdrasil_heal_respects_health_cap_and_heal_block():
    engine = GameEngine()
    target = engine.players[1]
    card = CardInstance('Yggdrasil')
    choice = {'target_player': 1}

    target.health = 90
    engine._effect_yggdrasil(0, card, choice)
    assert target.health == 100

    target.health = 50
    target.heal_block = 1
    engine._effect_yggdrasil(0, card, choice)
    assert target.health == 62
    assert target.heal_block == 0

    target.health = 50
    target.heal_block = 1
    target.custom_statuses['status_immune'] = 1
    engine._effect_yggdrasil(0, card, choice)
    assert target.health == 75
    assert target.heal_block == 0


def test_yggdrasil_dead_target_still_uses_the_distinct_five_health_revive():
    engine = GameEngine2v2()
    target = engine.players[2]
    target.health = 0
    target.heal_block = 2
    target.weakness = 3
    target.blind = 1
    target.deck = []

    engine._effect_yggdrasil(
        0,
        CardInstance('Yggdrasil'),
        {'target_player': 2},
    )

    assert target.health == 5
    assert target.invincible
    assert target.heal_block == 0
    assert target.weakness == 0
    assert target.blind == 0


def test_yggdrasil_definitions_and_package_share_the_twenty_five_heal():
    vanilla_mod = load_mod(str(ROOT / 'mods' / 'Vanilla Cards.gtnmod'))
    vanilla_card = next(
        card for card in vanilla_mod.cards
        if str(card.id or '').lower().endswith('yggdrasil')
    )
    assert '回复目标25[[icon:H]]' in vanilla_card.to_card_def().effect_text
    for language in ('zh', 'en', 'fr', 'ja'):
        effect = CARD_I18N['Yggdrasil']['effect'][language]
        assert '25' in effect
        assert '20' not in effect

    package_path = ROOT / 'mods' / 'Vanilla Cards.gtnmod'
    with zipfile.ZipFile(package_path) as package:
        assert package.testzip() is None
        mod_data = json.loads(package.read('mod.json').decode('utf-8'))
        card = next(
            entry for entry in mod_data['registries']['cards']
            if entry.get('id') == 'vanilla:yggdrasil'
        )
        heal_step = next(
            step for step in card['events']['on_play']['steps']
            if step.get('op') == 'heal'
        )
        assert heal_step['amount'] == 25
        assert '25[[icon:H]]' in card['effect_text']
        for locale_name in ('zh', 'en', 'fr', 'ja'):
            locale = json.loads(package.read(f'locales/{locale_name}.json').decode('utf-8'))
            effect = locale['cards']['vanilla:yggdrasil']['effect_text']
            assert '25[[icon:H]]' in effect
            assert '20[[icon:H]]' not in effect


def test_story_world_tree_leaf_remains_a_separate_full_health_relic():
    relic = STORY_RELICS['world_tree_leaf']
    assert relic['script'] == 'revive'
    assert '满H' in relic['description']['zh']
    assert '25' not in relic['description']['zh']

