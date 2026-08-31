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
    target.deck = []

    engine._effect_yggdrasil(
        0,
        CardInstance('Yggdrasil'),
        {'target_player': 2},
    )

    assert target.health == 5
    assert target.invincible


def test_yggdrasil_definitions_and_package_share_the_twenty_five_heal():
    assert '回复目标25[[icon:H]]' in CARD_DEFS['Yggdrasil'].effect_text
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


def test_local_worker_yggdrasil_heals_twenty_five():
    node = shutil.which('node')
    if not node:
        pytest.skip('node is required for the local Yggdrasil behavior test')
    worker = (ROOT / 'static' / 'js' / 'local_solo_worker.js').read_text(encoding='utf-8')
    harness = r'''
const yggdrasilEngine = Object.create(LocalSoloEngine.prototype);
yggdrasilEngine.players = [new LocalPlayer(0), new LocalPlayer(1)];
yggdrasilEngine.player_names = ['P1', 'P2'];
yggdrasilEngine.log = [];
yggdrasilEngine.logMsg = message => yggdrasilEngine.log.push(String(message));
yggdrasilEngine.players[1].health = 50;
yggdrasilEngine.effectYggdrasil(0, { def_id: 'Yggdrasil' }, { target_player: 1 });
process.stdout.write(JSON.stringify({
    heal: YGGDRASIL_HEAL,
    health: yggdrasilEngine.players[1].health,
    log: yggdrasilEngine.log,
}));
'''
    with tempfile.TemporaryDirectory(prefix='gtn-yggdrasil-worker-') as temp_dir:
        script_path = Path(temp_dir) / 'yggdrasil-test.js'
        script_path.write_text(
            "globalThis.postMessage = () => {};\n" + worker + "\n" + harness,
            encoding='utf-8',
        )
        completed = subprocess.run(
            [node, str(script_path)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=20,
        )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result['heal'] == 25
    assert result['health'] == 75
    assert any('回复25H' in line for line in result['log'])
