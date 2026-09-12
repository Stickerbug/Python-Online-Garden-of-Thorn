"""反馈 #100：PvP 里放逐优先于回转；两边补术语描述。"""

from pathlib import Path

from cards import CARD_DEFS, CardDef, CardInstance
from game_engine import GameEngine


ROOT = Path(__file__).resolve().parents[1]
BOTH_ID = '__test_rebound_exile_both__'
REBOUND_ID = '__test_rebound_only__'


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
    CARD_DEFS[BOTH_ID] = _make_def(BOTH_ID, {'rebound', 'exile'})
    CARD_DEFS[REBOUND_ID] = _make_def(REBOUND_ID, {'rebound'})


def teardown_module():
    CARD_DEFS.pop(BOTH_ID, None)
    CARD_DEFS.pop(REBOUND_ID, None)


def make_engine():
    engine = GameEngine()
    engine.phase = 'action'
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


def test_card_with_rebound_and_exile_is_exiled():
    engine = make_engine()
    card = CardInstance(BOTH_ID)
    engine.players[0].hand = [card]

    result = engine.play_card(0, card.instance_id, {})

    assert result.get('success'), result
    assert engine.players[0].find_hand_card(card.instance_id) is None
    assert any(item.instance_id == card.instance_id for item in engine.players[0].exile)


def test_rebound_only_card_still_returns_to_hand():
    engine = make_engine()
    card = CardInstance(REBOUND_ID)
    engine.players[0].hand = [card]

    result = engine.play_card(0, card.instance_id, {})

    assert result.get('success'), result
    assert engine.players[0].find_hand_card(card.instance_id) is not None
    assert all(item.instance_id != card.instance_id for item in engine.players[0].exile)


def test_rebound_description_mentions_exile_priority_in_both_modes():
    game_js = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
    story_content = (ROOT / 'story_content.py').read_text(encoding='utf-8')
    for source in (game_js, story_content):
        assert '若同时带有放逐，则放逐优先。' in source
        assert 'Exile takes priority' in source
        assert 'l’Exil est prioritaire' in source
        assert '放逐が優先されます' in source
