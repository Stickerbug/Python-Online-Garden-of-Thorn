from pathlib import Path

from cards import CardInstance
from game_engine import GameEngine


ROOT = Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')


def test_chilli_preplay_choice_hides_sublime_cards():
    chilli_branch = GAME_JS.split(
        "} else if (defId === 'Chilli') {",
        2,
    )[-1].split(
        'return null;',
        1,
    )[0]

    assert '!cardHasSublimeFlag(c)' in chilli_branch


def test_server_rejects_sublime_card_as_discard_choice():
    engine = GameEngine()
    chilli = CardInstance('Chilli')
    yggdrasil = CardInstance('Yggdrasil')
    basic = CardInstance('Basic')
    engine.players[0].hand = [chilli, yggdrasil, basic]
    effect = {'type': 'discard_choice_then_draw', 'params': {}}

    assert not engine._choice_request_satisfied(
        effect,
        {'target_instance_id': yggdrasil.instance_id},
        chilli,
    )
    assert engine._choice_request_satisfied(
        effect,
        {'target_instance_id': basic.instance_id},
        chilli,
    )
