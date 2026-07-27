from pathlib import Path

from cards import CardInstance
from game_engine import GameEngine


ROOT = Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
LOCAL_SOLO_WORKER_JS = (
    ROOT / 'static' / 'js' / 'local_solo_worker.js'
).read_text(encoding='utf-8')


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


def test_local_solo_choice_validation_uses_shared_sublime_rule():
    assert 'return !selectedCard || !cardSelectableByAction(selectedCard);' in (
        LOCAL_SOLO_WORKER_JS
    )
    assert "c.flags.has('exalted')" not in LOCAL_SOLO_WORKER_JS.split(
        'defaultAutoChoiceForPending(pending) {',
        1,
    )[1].split(
        'checkCardResponseAfterChoice(',
        1,
    )[0]
