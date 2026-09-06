from pathlib import Path

import pytest

from cards import CARD_DEFS, CardInstance
from game_engine import EquipmentInstance, GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def modded_runtime():
    filenames = (
        'Vanilla Cards.gtnmod',
        'Jungle Cards Addition.gtnmod',
        'Factory Cards Addition.gtnmod',
    )
    mods = []
    for filename in filenames:
        mod = load_mod(str(ROOT / 'mods' / filename))
        assert not mod.errors, (filename, mod.errors)
        mods.append(mod)
    runtime_cards = {}
    for mod in mods:
        for card in mod.cards:
            runtime_cards[card.id] = card
    previous = dict(CARD_DEFS)
    for card_id, card in runtime_cards.items():
        CARD_DEFS[card_id] = card.to_card_def()
    yield runtime_cards
    CARD_DEFS.clear()
    CARD_DEFS.update(previous)


def _fresh_engine(engine_class):
    engine = engine_class()
    engine.phase = 'action'
    engine.current_player = 0
    for player in engine.players:
        player.hand = []
        player.deck = []
        player.discard = []
        player.exile = []
        player.equipment = []
        player.elixir = 50
        player.magic = 50
        player.health = 100
        player.max_health = 100
        player.armor = 0
        player.custom_statuses = {}
        player.custom_vars = {}
        player.status_immunity = 0
    return engine


@pytest.mark.parametrize(
    'engine_class,target_id',
    ((GameEngine, 1), (GameEngine2v2, 2)),
)
def test_pvp_yin_yang_draws_trigger_electric_web(
    modded_runtime,
    engine_class,
    target_id,
):
    engine = _fresh_engine(engine_class)
    web = EquipmentInstance(CardInstance('ElectricWeb'), 0)
    web.effect_target = target_id
    engine.players[0].equipment.append(web)
    engine.players[target_id].custom_vars['electric_web_draw_damage'] = 2

    yin = CardInstance('YinYang')
    engine.players[0].hand = [yin]
    engine.players[target_id].deck = [CardInstance('Basic') for _ in range(3)]
    engine.players[target_id].hand = [CardInstance('Rose'), CardInstance('Bone')]
    choice = {
        'target_player': target_id,
        'target_player_id': target_id,
        'target_id': target_id,
    }
    engine._active_choice = choice
    health_before = engine.players[target_id].health

    engine._atomic_yin_yang_effect(
        0,
        yin,
        {'target': 'target'},
        '',
        choice,
        {'target_id': target_id},
    )

    target = engine.players[target_id]
    assert target.health < health_before
    assert any('电网' in line for line in engine.log)
    assert len(target.deck) < 3


def test_electric_web_arms_immediately_when_equipped_before_yin_yang(
    modded_runtime,
):
    engine = _fresh_engine(GameEngine)
    engine.players[0].hand = [
        CardInstance('ElectricWeb'),
        CardInstance('YinYang'),
    ]
    engine.players[1].deck = [CardInstance('Basic') for _ in range(3)]
    engine.players[1].hand = [CardInstance('Rose'), CardInstance('Bone')]
    target_choice = {
        'target_player': 1,
        'target_player_id': 1,
        'target_id': 1,
    }

    result = engine.play_card(
        0,
        engine.players[0].hand[0].instance_id,
        target_choice,
    )
    assert result.get('success'), result
    assert engine.players[1].custom_vars['electric_web_draw_damage'] == 2

    health_before = engine.players[1].health
    yin = engine.players[0].hand[0]
    result = engine.play_card(0, yin.instance_id, target_choice)
    assert result.get('success'), result
    assert engine.players[1].health < health_before
    assert any('电网' in line for line in engine.log)
