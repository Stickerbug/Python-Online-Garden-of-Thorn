import json
import zipfile
from pathlib import Path

import pytest

from cards import CARD_DEFS, CardInstance
from game_engine import GameEngine
from game_engine_2v2 import GameEngine2v2
from mod_loader import load_mod


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'mods' / 'Ocean Cards Addition.gtnmod'
LOCAL_WORKER = ROOT / 'static' / 'js' / 'local_solo_worker.js'
CARD_IDS = {'Lightning', 'MagicLightning'}


@pytest.fixture()
def ocean_cards():
    mod = load_mod(str(PACKAGE))
    assert not mod.errors
    definitions = {card.id: card.to_card_def() for card in mod.cards if card.id in CARD_IDS}
    previous = {card_id: CARD_DEFS.get(card_id) for card_id in definitions}
    CARD_DEFS.update(definitions)
    try:
        yield definitions
    finally:
        for card_id, old_definition in previous.items():
            if old_definition is None:
                CARD_DEFS.pop(card_id, None)
            else:
                CARD_DEFS[card_id] = old_definition


def _prime_engine(engine):
    engine.phase = 'action'
    engine.current_player = 0
    for player in engine.players:
        player.hand = []
        player.deck = []
        player.discard = []
        player.exile = []
        player.equipment = []
        player.health = 100
        player.max_health = 100
        player.elixir = 30
        player.magic = 30
        player.custom_statuses = {}
        player.custom_vars = {}
    return engine


def _target_choice(target_id):
    return {
        'target_player': target_id,
        'target_player_id': target_id,
        'target_id': target_id,
    }


def test_lightning_plays_and_charges_at_most_two_target_cards(ocean_cards):
    engine = _prime_engine(GameEngine())
    lightning = CardInstance('Lightning')
    lightning.charge_value = 3
    lightning.instance_flags.add('charge')
    engine.players[0].hand = [lightning]
    engine.players[1].hand = [CardInstance('Basic') for _ in range(3)]

    result = engine.play_card(0, lightning.instance_id, _target_choice(1))

    assert result.get('success'), result
    assert engine.players[0].health == 97
    assert engine.players[1].health == 87
    assert sorted(card.charge_value for card in engine.players[1].hand) == [0, 3, 3]


def test_magic_lightning_plays_in_2v2_and_charges_the_selected_players_hand(ocean_cards):
    engine = _prime_engine(GameEngine2v2())
    lightning = CardInstance('MagicLightning')
    lightning.charge_value = 4
    lightning.instance_flags.add('charge')
    engine.players[0].hand = [lightning]
    engine.players[2].hand = [CardInstance('Basic') for _ in range(3)]
    choice = _target_choice(2)

    result = engine.play_card(0, lightning.instance_id, 2, choice)

    assert result.get('success'), result
    assert engine.players[0].health == 96
    assert engine.players[2].health == 82
    assert [card.charge_value for card in engine.players[2].hand] == [3, 3, 3]
    assert engine.players[3].health == 100


def test_charged_counter_card_applies_charge_damage_once():
    engine = _prime_engine(GameEngine())
    attack = CardInstance('Basic')
    counter = CardInstance('Bubble')
    counter.charge_value = 3
    counter.instance_flags.add('charge')
    engine.players[0].hand = [attack]
    engine.players[1].hand = [counter]

    play_result = engine.play_card(0, attack.instance_id, _target_choice(1))
    assert play_result.get('needs_response'), play_result

    response_result = engine.handle_response(1, counter.instance_id)

    assert response_result.get('success'), response_result
    assert engine.players[1].health == 97


def test_charged_counter_card_applies_charge_damage_once_in_2v2():
    engine = _prime_engine(GameEngine2v2())
    attack = CardInstance('Basic')
    counter = CardInstance('Bubble')
    counter.charge_value = 4
    counter.instance_flags.add('charge')
    engine.players[0].hand = [attack]
    engine.players[2].hand = [counter]

    play_result = engine.play_card(0, attack.instance_id, 2, _target_choice(2))
    assert play_result.get('needs_response'), play_result

    response_result = engine.handle_response(2, counter.instance_id)

    assert response_result.get('success'), response_result
    assert engine.players[2].health == 96


def test_local_training_runtime_implements_every_ocean_package_atomic():
    source = LOCAL_WORKER.read_text(encoding='utf-8')
    with zipfile.ZipFile(PACKAGE) as archive:
        spec = json.loads(archive.read('mod.json'))

    custom_atomics = set()

    def visit(value):
        if isinstance(value, dict):
            operation = value.get('op') or value.get('type')
            if isinstance(operation, str) and operation.startswith('ocean_'):
                custom_atomics.add(operation)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(spec['registries']['cards'])
    missing = sorted(
        operation
        for operation in custom_atomics
        if f'effect_{operation}(' not in source
    )
    assert not missing, f'local training runtime is missing Ocean atomics: {missing}'
