from copy import deepcopy
import json

import pytest

from story_content import (
    STORY_BLESSINGS,
    STORY_CARDS,
    STORY_ENCOUNTERS,
    STORY_ENEMIES,
    STORY_EVENTS,
    STORY_RELICS,
    STORY_REWARD_CARD_IDS,
    STORY_SHOP_CARD_IDS,
)
from story_coop_content import (
    COOP_CONTENT_FINGERPRINT,
    COOP_CHEST_RELIC_IDS,
    COOP_OPENING_BLESSING_IDS,
    COOP_REWARD_CARD_IDS,
    COOP_SHOP_RELIC_IDS,
    COOP_SHOP_CARD_IDS,
    COOP_STORY_CONTENT,
    COOP_SUPPORTED_CARD_IDS,
    COOP_SUPPORTED_ENEMY_IDS,
    COOP_SUPPORTED_RELIC_IDS,
    CoopStoryContentError,
    compile_coop_story_content,
)
from story_coop_live import (
    COOP_FULL_JOURNEY_FINGERPRINT,
    COOP_STORY_CONTENT_VERSION,
    _card_values,
)
from story_content_model import (
    STORY_CONTENT_REGISTRY,
    build_story_content_registry,
)


def _compile(
    cards=None,
    reward_ids=None,
    shop_ids=None,
    blessings=None,
    enemies=None,
    encounters=None,
    relics=None,
    events=None,
):
    kwargs = dict(
        cards=deepcopy(STORY_CARDS if cards is None else cards),
        blessings=deepcopy(STORY_BLESSINGS if blessings is None else blessings),
        enemies=deepcopy(STORY_ENEMIES if enemies is None else enemies),
        encounters=deepcopy(STORY_ENCOUNTERS if encounters is None else encounters),
        relics=deepcopy(STORY_RELICS if relics is None else relics),
        events=deepcopy(STORY_EVENTS if events is None else events),
    )
    if reward_ids is not None:
        kwargs['reward_card_ids'] = tuple(reward_ids)
    if shop_ids is not None:
        kwargs['shop_card_ids'] = tuple(shop_ids)
    return compile_coop_story_content(**kwargs)


def _json_shape(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def test_current_catalog_compiles_to_expected_safe_pools():
    assert COOP_REWARD_CARD_IDS == (
        'bone', 'torch', 'sand', 'lightning', 'stinger', 'fries',
        'magic_shell', 'leaf', 'feather', 'mjolnir',
        'mage_fries', 'mage_coffee', 'mage_bone', 'mage_palm_leaf',
        'mage_rose', 'mage_lightning', 'plasma',
    )
    assert COOP_SHOP_CARD_IDS == (
        'bone', 'coffee', 'torch', 'sand', 'lightning', 'stinger',
        'fries', 'magic_shell', 'dust', 'leaf', 'feather', 'bubble',
        'mjolnir',
        'mage_fries', 'mage_coffee', 'mage_bone', 'mage_palm_leaf',
        'mage_rose', 'mage_lightning', 'plasma',
    )
    assert COOP_SUPPORTED_CARD_IDS == frozenset({
        'basic', 'rose', 'amulet', 'mage_basic',
        *COOP_REWARD_CARD_IDS, *COOP_SHOP_CARD_IDS,
    })
    assert COOP_OPENING_BLESSING_IDS == (
        'max_health', 'rare_card', 'gold', 'wealth_and_basics'
    )
    assert COOP_SUPPORTED_ENEMY_IDS == frozenset({'soldier_ant', 'young_ant', 'wasp'})
    assert COOP_SUPPORTED_RELIC_IDS == frozenset({
        'energetic', 'magic_source', 'rich', 'diligent', 'greedy',
        'body_reinforcement', 'bargaining',
    })
    assert COOP_CHEST_RELIC_IDS == (
        'rich', 'diligent', 'greedy', 'body_reinforcement', 'bargaining',
    )
    assert COOP_SHOP_RELIC_IDS == (
        'diligent', 'greedy', 'body_reinforcement', 'bargaining',
    )
    assert COOP_STORY_CONTENT.encounter_ids('garden', 'simple') == ('garden:simple:001',)
    assert COOP_STORY_CONTENT.encounter_ids('garden', 'hard') == ()
    assert COOP_STORY_CONTENT.event_ids('garden') == ('coop_garden_crossroads',)
    assert len(COOP_CONTENT_FINGERPRINT) == 64
    int(COOP_CONTENT_FINGERPRINT, 16)
    assert len(COOP_FULL_JOURNEY_FINGERPRINT) == 64
    int(COOP_FULL_JOURNEY_FINGERPRINT, 16)
    assert COOP_STORY_CONTENT_VERSION.endswith(COOP_FULL_JOURNEY_FINGERPRINT[:12])
    assert (
        COOP_STORY_CONTENT.manifest()['content_model_fingerprint']
        == STORY_CONTENT_REGISTRY.fingerprint
    )


def test_coop_capability_manifest_uses_three_states_and_fails_closed():
    assert COOP_STORY_CONTENT.capability('card', 'basic') == {
        'state': 'supported'
    }
    assert COOP_STORY_CONTENT.capability('card', 'light')['state'] == 'deferred'
    assert COOP_STORY_CONTENT.capability('character', 'common_flower') == {
        'state': 'supported'
    }
    assert COOP_STORY_CONTENT.capability('character', 'mage')['state'] == 'supported'
    assert COOP_STORY_CONTENT.capability(
        'character_card', 'mage_basic'
    )['state'] == 'supported'
    assert COOP_STORY_CONTENT.capability(
        'character_relic', 'magic_source'
    )['state'] == 'supported'
    assert COOP_STORY_CONTENT.capability(
        'term', 'electric_damage'
    )['state'] == 'supported'
    assert COOP_STORY_CONTENT.character_definition('mage')[
        'unavailable_message'
    ]['zh'] == '这名角色还没准备好呢\n请期待开发组更新'

    cards = deepcopy(STORY_CARDS)
    cards['bone']['coop'] = False
    rejected = compile_coop_story_content(
        content_registry=build_story_content_registry(cards=cards)
    )
    assert rejected.capability('card', 'bone')['state'] == 'rejected'
    assert '排除' in rejected.capability('card', 'bone')['reason']

    with pytest.raises(CoopStoryContentError, match='未知协作内容能力'):
        COOP_STORY_CONTENT.capability('card', 'future_unknown')


def test_compiled_shop_only_card_is_executable_by_live_reducer():
    def_id, values = _card_values({
        'instance_id': 'compiled-dust-0001',
        'def_id': 'dust',
        'upgraded': False,
        'upgrade_level': 0,
    })

    assert def_id == 'dust'
    assert [effect['type'] for effect in values['effects']] == ['damage', 'shield']


def test_shared_draw_elixir_and_exile_semantics_compile_from_canonical_catalog():
    torch = COOP_STORY_CONTENT.card_definition('torch')
    coffee = COOP_STORY_CONTENT.card_definition('coffee')
    bubble = COOP_STORY_CONTENT.card_definition('bubble')

    assert [effect['type'] for effect in torch['effects']] == [
        'damage', 'active_discard', 'draw',
    ]
    assert coffee['effects'] == [{'amount': 3, 'type': 'elixir'}]
    assert coffee['tags'] == ['exile']
    assert bubble['effects'] == [{'amount': 3, 'type': 'draw'}]
    assert bubble['tags'] == ['exile']


def test_supported_coop_values_are_exact_projections_of_the_shared_registry():
    manifest = COOP_STORY_CONTENT.manifest()
    for kind, plural in (
        ('character', 'characters'),
        ('card', 'cards'),
        ('blessing', 'blessings'),
        ('enemy', 'enemies'),
        ('encounter', 'encounters'),
        ('event', 'events'),
        ('relic', 'relics'),
    ):
        for content_id, projected in manifest[plural].items():
            source = _json_shape(
                STORY_CONTENT_REGISTRY.definition(kind, content_id)
            )
            for field, value in projected.items():
                assert source[field] == value, f'{kind}:{content_id}.{field}'


def test_compatible_story_edits_flow_into_manifest_and_fingerprint():
    cards = deepcopy(STORY_CARDS)
    cards['bone']['cost_e'] = 2
    cards['bone']['effects'][0]['amount'] = 8
    cards['bone']['description']['zh'] = '协作自动同步说明'

    compiled = _compile(cards=cards)
    bone = compiled.card_definition('bone')

    assert bone['cost_e'] == 2
    assert bone['effects'][0]['amount'] == 8
    assert bone['description']['zh'] == '协作自动同步说明'
    assert compiled.fingerprint != COOP_CONTENT_FINGERPRINT


def test_default_coop_compiler_reads_the_normalized_shared_registry():
    cards = deepcopy(STORY_CARDS)
    cards['bone']['cost_e'] = 2
    cards['bone']['effects'][0]['amount'] = 11
    changed_registry = build_story_content_registry(cards=cards)

    compiled = compile_coop_story_content(content_registry=changed_registry)

    assert compiled.card_definition('bone')['cost_e'] == 2
    assert compiled.card_definition('bone')['effects'][0]['amount'] == 11
    assert compiled.fingerprint != COOP_CONTENT_FINGERPRINT
    canonical_bone = STORY_CONTENT_REGISTRY.definition('card', 'bone')
    live_bone = COOP_STORY_CONTENT.card_definition('bone')
    assert live_bone['cost_e'] == canonical_bone['cost_e']
    assert live_bone['name'] == canonical_bone['name']
    assert live_bone['description'] == canonical_bone['description']


def test_new_compatible_story_card_automatically_joins_shared_pools():
    cards = deepcopy(STORY_CARDS)
    cards['coop_probe'] = deepcopy(cards['bone'])
    cards['coop_probe']['name'] = {'zh': '协作探针', 'en': 'Coop Probe'}
    reward_ids = (*COOP_REWARD_CARD_IDS, 'coop_probe')
    shop_ids = (*STORY_SHOP_CARD_IDS, 'coop_probe')

    compiled = _compile(cards=cards, reward_ids=reward_ids, shop_ids=shop_ids)

    assert 'coop_probe' in compiled.supported_card_ids
    assert 'coop_probe' in compiled.reward_card_ids
    assert 'coop_probe' in compiled.shop_card_ids
    assert compiled.card_definition('coop_probe')['name']['zh'] == '协作探针'


def test_unsupported_story_semantics_fail_closed_without_affecting_manifest():
    cards = deepcopy(STORY_CARDS)
    cards['coop_probe'] = deepcopy(cards['bone'])
    cards['coop_probe']['effects'][0]['power_scale'] = 4
    reward_ids = (*COOP_REWARD_CARD_IDS, 'coop_probe')

    compiled = _compile(cards=cards, reward_ids=reward_ids)

    assert 'coop_probe' not in compiled.supported_card_ids
    assert 'coop_probe' not in compiled.reward_card_ids
    assert compiled.fingerprint == COOP_CONTENT_FINGERPRINT


def test_declared_or_required_content_cannot_silently_become_incompatible():
    cards = deepcopy(STORY_CARDS)
    cards['bone']['coop'] = {'enabled': True}
    cards['bone']['script'] = 'solo_only_script'
    with pytest.raises(CoopStoryContentError, match='声明启用的协作卡牌 bone 不兼容'):
        _compile(cards=cards)

    starters = deepcopy(STORY_CARDS)
    starters['basic']['effects'] = (
        {'type': 'status', 'amount': 1, 'status': 'vulnerable'},
    )
    with pytest.raises(CoopStoryContentError, match='必需协作卡牌 basic 不兼容'):
        _compile(cards=starters)


def test_blessing_edits_and_new_supported_scripts_propagate_automatically():
    blessings = deepcopy(STORY_BLESSINGS)
    blessings['gold']['amount'] = 175
    blessings['coop_probe'] = {
        'name': {'zh': '额外金币', 'en': 'Extra Gold'},
        'description': {'zh': '获得25G', 'en': 'Gain 25 G'},
        'script': 'gain_gold',
        'amount': 25,
        'order': 9,
    }

    compiled = _compile(blessings=blessings)

    assert compiled.opening_blessing_ids[-1] == 'coop_probe'
    assert compiled.blessing_definition('gold')['amount'] == 175
    assert compiled.fingerprint != COOP_CONTENT_FINGERPRINT


def test_compatible_enemy_and_encounter_edits_flow_into_shared_manifest():
    enemies = deepcopy(STORY_ENEMIES)
    encounters = deepcopy(STORY_ENCOUNTERS)
    enemies['coop_enemy_probe'] = deepcopy(enemies['soldier_ant'])
    enemies['coop_enemy_probe']['name'] = {'zh': '协作敌人探针', 'en': 'Coop Enemy Probe'}
    enemies['coop_enemy_probe']['max_health'] = 61
    encounters['garden']['simple'] = (
        *encounters['garden']['simple'],
        ('coop_enemy_probe',),
    )

    compiled = _compile(enemies=enemies, encounters=encounters)
    probe = compiled.enemy_definition('coop_enemy_probe')
    new_encounter_id = compiled.encounter_ids('garden', 'simple')[-1]

    assert probe['max_health'] == 61
    assert probe['name']['zh'] == '协作敌人探针'
    assert compiled.encounter_definition(new_encounter_id)['members'] == [
        {'def_id': 'coop_enemy_probe'},
    ]


def test_shared_event_edits_and_compatible_additions_flow_into_manifest():
    events = deepcopy(STORY_EVENTS)
    events['coop_garden_crossroads']['title']['zh'] = '共享事件新标题'
    events['coop_garden_crossroads']['options'][0]['effects'][0]['amount'] = 21
    events['coop_event_probe'] = deepcopy(events['coop_garden_crossroads'])
    events['coop_event_probe']['title'] = {'zh': '共享事件探针', 'en': 'Shared Event Probe'}

    compiled = _compile(events=events)

    assert compiled.event_ids('garden') == (
        'coop_garden_crossroads', 'coop_event_probe',
    )
    definition = compiled.event_definition('coop_garden_crossroads')
    assert definition['title']['zh'] == '共享事件新标题'
    assert definition['options'][0]['effects'][0]['amount'] == 21
    assert compiled.fingerprint != COOP_CONTENT_FINGERPRINT


def test_declared_shared_event_cannot_silently_gain_unsupported_semantics():
    events = deepcopy(STORY_EVENTS)
    events['coop_garden_crossroads']['options'][0]['effects'] = (
        {'type': 'gain_relic', 'amount': 1},
    )

    with pytest.raises(CoopStoryContentError, match='兼容共享事件'):
        _compile(events=events)


def test_compatible_relic_edits_and_additions_flow_into_shared_pools():
    relics = deepcopy(STORY_RELICS)
    relics['greedy']['amount'] = 175
    relics['coop_relic_probe'] = deepcopy(relics['diligent'])
    relics['coop_relic_probe']['name'] = {'zh': '协作遗物探针', 'en': 'Coop Relic Probe'}

    compiled = _compile(relics=relics)

    assert compiled.relic_definition('greedy')['amount'] == 175
    assert 'coop_relic_probe' in compiled.supported_relic_ids
    assert 'coop_relic_probe' in compiled.chest_relic_ids
    assert 'coop_relic_probe' in compiled.shop_relic_ids
    assert compiled.fingerprint != COOP_CONTENT_FINGERPRINT


def test_unsupported_relic_scripts_fail_closed_and_required_relics_cannot_drift():
    relics = deepcopy(STORY_RELICS)
    relics['coop_relic_probe'] = deepcopy(relics['diligent'])
    relics['coop_relic_probe']['script'] = 'solo_only_relic_script'

    compiled = _compile(relics=relics)
    assert 'coop_relic_probe' not in compiled.supported_relic_ids
    assert compiled.fingerprint == COOP_CONTENT_FINGERPRINT

    relics['energetic']['script'] = 'solo_only_relic_script'
    with pytest.raises(CoopStoryContentError, match='必需协作遗物 energetic 不兼容'):
        _compile(relics=relics)


def test_unsupported_enemy_semantics_and_mixed_encounters_fail_closed():
    enemies = deepcopy(STORY_ENEMIES)
    encounters = deepcopy(STORY_ENCOUNTERS)
    enemies['coop_enemy_probe'] = deepcopy(enemies['soldier_ant'])
    enemies['coop_enemy_probe']['moves'][0]['effects'] = (
        {'type': 'summon', 'enemy_id': 'young_ant'},
    )
    encounters['garden']['simple'] = (
        *encounters['garden']['simple'],
        ('soldier_ant', 'coop_enemy_probe'),
    )

    compiled = _compile(enemies=enemies, encounters=encounters)

    assert 'coop_enemy_probe' not in compiled.supported_enemy_ids
    assert all(
        all(member['def_id'] != 'coop_enemy_probe' for member in encounter['members'])
        for encounter in compiled.manifest()['encounters'].values()
    )


def test_manifest_callers_cannot_mutate_compiled_content():
    manifest = COOP_STORY_CONTENT.manifest()
    manifest['cards']['bone']['cost_e'] = 99
    manifest['reward_card_ids'].clear()

    assert COOP_STORY_CONTENT.card_definition('bone')['cost_e'] == STORY_CARDS['bone']['cost_e']
    assert COOP_STORY_CONTENT.reward_card_ids == COOP_REWARD_CARD_IDS
