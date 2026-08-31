from copy import deepcopy

import pytest

from story_content import (
    STORY_BLESSINGS,
    STORY_CARDS,
    STORY_CHARACTERS,
    STORY_CHARACTER_NOT_READY_MESSAGE,
    STORY_ENCOUNTERS,
    STORY_ENEMIES,
    STORY_RELICS,
)
from story_content_model import (
    STORY_CONTENT_FINGERPRINT,
    STORY_CONTENT_REGISTRY,
    STORY_WORKBOOK_FILE,
    STORY_WORKBOOK_SHA256,
    StoryContentModelError,
    StoryContentRecord,
    StoryContentSource,
    build_story_content_registry,
    validate_story_content_model,
)
from story_character_content import (
    STORY_CHARACTER_CARD_DESIGNS,
    STORY_CHARACTER_RELIC_DESIGNS,
    STORY_CHARACTER_TERMS,
)


def test_normalized_registry_covers_every_authoritative_catalog_entry():
    assert validate_story_content_model() is True
    assert len(STORY_CONTENT_REGISTRY.catalog('character')) == 5
    assert len(STORY_CHARACTERS) == 5
    assert len(STORY_CONTENT_REGISTRY.catalog('character_card')) == 55
    assert len(STORY_CHARACTER_CARD_DESIGNS) == 55
    assert len(STORY_CONTENT_REGISTRY.catalog('character_relic')) == 1
    assert len(STORY_CHARACTER_RELIC_DESIGNS) == 1
    assert len(STORY_CONTENT_REGISTRY.catalog('term')) == 1
    assert len(STORY_CHARACTER_TERMS) == 1
    assert len(STORY_CONTENT_REGISTRY.catalog('card')) == len(STORY_CARDS)
    assert len(STORY_CARDS) == 150
    assert len(STORY_CONTENT_REGISTRY.catalog('relic')) == len(STORY_RELICS) == 50
    assert len(STORY_CONTENT_REGISTRY.catalog('enemy')) == len(STORY_ENEMIES) == 77
    assert len(STORY_CONTENT_REGISTRY.catalog('encounter')) == sum(
        len(specs)
        for tiers in STORY_ENCOUNTERS.values()
        for specs in tiers.values()
    ) == 83
    assert len(STORY_CONTENT_FINGERPRINT) == 64
    int(STORY_CONTENT_FINGERPRINT, 16)


def test_workbook_sources_use_the_frozen_file_hash_and_precise_rows():
    assert STORY_WORKBOOK_FILE == 'Garden of Thorn 卡牌数据8.xlsx'
    assert STORY_WORKBOOK_SHA256 == (
        '2c3f1a54d695dd6b1c3bf7fa9df22f5150029f1988caf4804444213e4cfd9546'
    )
    expected = {
        ('card', 'basic'): ('爬塔卡牌设计', 'A3:K3'),
        ('character', 'common_flower'): ('角色设计（先不做）', 'A1:B1'),
        ('character', 'occultist'): ('角色设计（先不做）', 'A5:B5'),
        ('card', 'magic_pearl'): ('爬塔卡牌设计', 'A32:K32'),
        ('card', 'dust'): ('爬塔卡牌设计', 'A57:K57'),
        ('relic', 'world_tree_leaf'): ('爬塔天赋设计', 'A33:D33'),
        ('enemy', 'wasp'): ('爬塔怪物设计', 'A6:P6'),
        ('enemy', 'mechanical_rat'): ('爬塔怪物设计', 'A76:P76'),
        ('encounter', 'factory:simple:003'): ('战斗列表', 'A80:D80'),
        ('encounter', 'garden:elite:001'): ('战斗列表', 'A2:D2'),
    }
    for key, (sheet, cell_range) in expected.items():
        source = STORY_CONTENT_REGISTRY.record(*key).sources[0]
        assert source.source_type == 'workbook'
        assert source.workbook_file == STORY_WORKBOOK_FILE
        assert source.sheet == sheet
        assert source.cell_range == cell_range
        assert source.source_version.endswith(STORY_WORKBOOK_SHA256)


def test_all_five_sheet_characters_are_registered_with_unavailable_fallbacks():
    assert tuple(STORY_CHARACTERS) == (
        'common_flower',
        'orbiter',
        'summoner',
        'mage',
        'occultist',
    )
    for character_id in ('common_flower', 'mage'):
        character = STORY_CONTENT_REGISTRY.definition('character', character_id)
        assert character['implementation_status'] == 'playable'
    for character_id in ('orbiter', 'summoner', 'occultist'):
        character = STORY_CONTENT_REGISTRY.definition('character', character_id)
        assert character['implementation_status'] == 'planned'
        assert character['unavailable_message'] == STORY_CHARACTER_NOT_READY_MESSAGE
        assert character['unavailable_message']['zh'] == (
            '这名角色还没准备好呢\n请期待开发组更新'
        )


def test_all_mage_rows_and_electric_damage_term_keep_precise_workbook_sources():
    for row, content_id in enumerate(STORY_CHARACTER_CARD_DESIGNS, 103):
        source = STORY_CONTENT_REGISTRY.record(
            'character_card', content_id
        ).sources[0]
        assert source.cell_range == f'B{row}:K{row}'
        definition = STORY_CHARACTER_CARD_DESIGNS[content_id]
        assert definition['character_id'] == 'mage'
        assert definition['implementation_status'] == 'authored'
        assert definition['card_type'] in {'thorn', 'bloom', 'root'}
        assert definition['rarity'] in {'starter', 'common', 'rare', 'ultra'}

    first = STORY_CONTENT_REGISTRY.record('character_card', 'mage_basic')
    assert first.sources[0].sheet == '爬塔卡牌设计'
    assert first.sources[0].cell_range == 'B103:K103'
    assert first.definition()['name']['zh'] == '魔法基本'
    promoted = STORY_CONTENT_REGISTRY.record('card', 'mage_basic')
    assert promoted.sources[0].sheet == '爬塔卡牌设计'
    assert promoted.sources[0].cell_range == 'B103:K103'
    assert promoted.definition()['effects'] == ({'type': 'damage', 'amount': 13},)

    battery = STORY_CONTENT_REGISTRY.record(
        'character_card', 'mage_battery_delayed'
    )
    capacitor = STORY_CONTENT_REGISTRY.record(
        'character_card', 'mage_capacitor'
    )
    assert battery.definition()['name']['zh'] == '魔法电池'
    assert capacitor.definition()['name']['zh'] == '魔法电容器'
    assert battery.sources[0].cell_range == 'B133:K133'
    assert capacitor.sources[0].cell_range == 'B152:K152'
    assert STORY_CONTENT_REGISTRY.definition(
        'character_card', 'mage_beeswax'
    )['name']['zh'] == '魔法蜂蜡'
    assert STORY_CONTENT_REGISTRY.definition(
        'character_card', 'mage_orange'
    )['base_text'] == '造成5D'

    final_card = STORY_CONTENT_REGISTRY.record(
        'character_card', 'mage_electronic_missile'
    )
    assert final_card.sources[0].cell_range == 'B157:K157'
    electric = STORY_CONTENT_REGISTRY.record('term', 'electric_damage')
    assert electric.sources[0].cell_range == 'B158:F158'
    assert electric.definition()['name']['zh'] == '电击伤害'
    magic_source = STORY_CONTENT_REGISTRY.record(
        'character_relic', 'magic_source'
    )
    assert magic_source.sources[0].cell_range == 'A4:D4'
    assert magic_source.definition()['name']['zh'] == '魔力源泉'
    executable_magic_source = STORY_CONTENT_REGISTRY.record('relic', 'magic_source')
    assert executable_magic_source.sources[0].cell_range == 'A4:D4'
    assert executable_magic_source.definition()['script'] == 'turn_magic'


def test_code_added_event_never_claims_a_fake_workbook_cell():
    source = STORY_CONTENT_REGISTRY.record(
        'event', 'coop_garden_crossroads'
    ).sources[0]
    assert source.source_type == 'code'
    assert source.code_symbol == "story_content.STORY_EVENTS['coop_garden_crossroads']"
    assert source.workbook_file == source.sheet == source.cell_range == ''


def test_registry_definitions_are_copies_and_fingerprint_tracks_content_changes():
    definition = STORY_CONTENT_REGISTRY.definition('card', 'bone')
    definition['cost_e'] = 999
    assert STORY_CONTENT_REGISTRY.definition('card', 'bone')['cost_e'] == 1
    assert STORY_CARDS['bone']['cost_e'] == 1

    cards = deepcopy(STORY_CARDS)
    cards['bone']['cost_e'] = 2
    changed = build_story_content_registry(cards=cards)
    assert changed.definition('card', 'bone')['cost_e'] == 2
    assert changed.fingerprint != STORY_CONTENT_FINGERPRINT


def test_new_unmapped_workbook_content_fails_closed_until_source_is_registered():
    cards = deepcopy(STORY_CARDS)
    cards['unmapped_probe'] = deepcopy(cards['bone'])
    with pytest.raises(StoryContentModelError, match='必须先登记工作簿或代码来源'):
        build_story_content_registry(cards=cards)


def test_source_and_record_shapes_reject_unknown_or_ambiguous_provenance():
    with pytest.raises(StoryContentModelError, match='来源类型'):
        StoryContentSource(source_type='unknown', source_version='v1')
    with pytest.raises(StoryContentModelError, match='工作表'):
        StoryContentSource(
            source_type='workbook',
            source_version='v1',
            workbook_file=STORY_WORKBOOK_FILE,
            sheet='爬塔卡牌设计',
            cell_range='not-a-cell',
        )
    with pytest.raises(StoryContentModelError, match='未知故事内容类型'):
        StoryContentRecord(
            kind='unknown',
            content_id='probe',
            sources=(STORY_CONTENT_REGISTRY.record('card', 'basic').sources[0],),
            _definition={},
        )


def test_blessing_and_encounter_ids_are_stable_and_auditable():
    for index, blessing_id in enumerate(STORY_BLESSINGS, 2):
        source = STORY_CONTENT_REGISTRY.record('blessing', blessing_id).sources[0]
        assert source.cell_range == f'A{index}:B{index}'

    factory = [
        STORY_CONTENT_REGISTRY.definition('encounter', key.split(':', 1)[1])
        for key in STORY_CONTENT_REGISTRY.keys('encounter')
        if key.startswith('encounter:factory:simple:')
    ]
    assert [item['members'] for item in factory] == [
        [{'def_id': member} for member in spec]
        for spec in STORY_ENCOUNTERS['factory']['simple']
    ]
