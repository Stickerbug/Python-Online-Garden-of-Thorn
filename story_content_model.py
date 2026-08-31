"""Normalized, source-backed catalog for solo and cooperative story content.

The gameplay dictionaries in :mod:`story_content` remain the only value table.
This module adds stable content keys and audit provenance without copying card,
enemy or relic numbers.  Runtime consumers receive deep copies so an inspector
cannot mutate the authoritative catalog through the registry.
"""

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
import re

from story_content import (
    STORY_BIOMES,
    STORY_BLESSINGS,
    STORY_CARDS,
    STORY_CARD_TYPES,
    STORY_CHARACTERS,
    STORY_DIFFICULTIES,
    STORY_ENCOUNTERS,
    STORY_ENEMIES,
    STORY_EVENTS,
    STORY_RELICS,
    STORY_RULES,
    STORY_STATUSES,
    STORY_TAGS,
    STORY_TRAITS,
)
from story_character_content import (
    STORY_CHARACTER_CARD_DESIGNS,
    STORY_CHARACTER_RELIC_DESIGNS,
    STORY_CHARACTER_TERMS,
)


STORY_CONTENT_MODEL_VERSION = 1
STORY_WORKBOOK_FILE = 'Garden of Thorn 卡牌数据8.xlsx'
STORY_WORKBOOK_SHA256 = (
    '2c3f1a54d695dd6b1c3bf7fa9df22f5150029f1988caf4804444213e4cfd9546'
)
STORY_WORKBOOK_SOURCE_VERSION = f'xlsx-sha256:{STORY_WORKBOOK_SHA256}'

STORY_CONTENT_KINDS = frozenset({
    'rule',
    'character',
    'character_card',
    'character_relic',
    'term',
    'biome',
    'difficulty',
    'card_type',
    'tag',
    'status',
    'trait',
    'blessing',
    'card',
    'relic',
    'enemy',
    'encounter',
    'event',
})
_CONTENT_ID_RE = re.compile(r'[a-z0-9][a-z0-9_.:-]{0,127}')
_CELL_RANGE_RE = re.compile(
    r"(?:'[^']+'|[^!]+)![A-Z]+[1-9][0-9]*(?::[A-Z]+[1-9][0-9]*)?"
)


class StoryContentModelError(ValueError):
    """A normalized content record or its provenance is invalid."""


@dataclass(frozen=True)
class StoryContentSource:
    source_type: str
    source_version: str
    workbook_file: str = ''
    sheet: str = ''
    cell_range: str = ''
    code_symbol: str = ''
    note: str = ''

    def __post_init__(self):
        if self.source_type not in {'workbook', 'code'}:
            raise StoryContentModelError('内容来源类型必须是 workbook 或 code')
        if not str(self.source_version or '').strip():
            raise StoryContentModelError('内容来源必须包含版本')
        if self.source_type == 'workbook':
            if self.workbook_file != STORY_WORKBOOK_FILE:
                raise StoryContentModelError('工作簿来源文件不符合当前冻结版本')
            qualified = f"'{self.sheet}'!{self.cell_range}"
            if not self.sheet or not self.cell_range or not _CELL_RANGE_RE.fullmatch(qualified):
                raise StoryContentModelError('工作簿来源必须包含合法工作表与单元格范围')
            if self.code_symbol:
                raise StoryContentModelError('工作簿来源不能伪装成代码来源')
        elif not self.code_symbol or self.workbook_file or self.sheet or self.cell_range:
            raise StoryContentModelError('代码来源必须只包含可定位的代码符号')

    def manifest(self):
        payload = {
            'source_type': self.source_type,
            'source_version': self.source_version,
        }
        if self.source_type == 'workbook':
            payload.update({
                'workbook_file': self.workbook_file,
                'sheet': self.sheet,
                'cell_range': self.cell_range,
            })
        else:
            payload['code_symbol'] = self.code_symbol
        if self.note:
            payload['note'] = self.note
        return payload


@dataclass(frozen=True)
class StoryContentRecord:
    kind: str
    content_id: str
    sources: tuple
    _definition: dict = field(repr=False, compare=False)

    def __post_init__(self):
        if self.kind not in STORY_CONTENT_KINDS:
            raise StoryContentModelError(f'未知故事内容类型 {self.kind}')
        if not _CONTENT_ID_RE.fullmatch(str(self.content_id or '')):
            raise StoryContentModelError(f'故事内容 ID 无效 {self.content_id!r}')
        if not self.sources or any(
            not isinstance(source, StoryContentSource) for source in self.sources
        ):
            raise StoryContentModelError('故事内容必须包含至少一个规范来源')
        if not isinstance(self._definition, dict):
            raise StoryContentModelError('故事内容定义必须是对象')
        object.__setattr__(self, '_definition', deepcopy(self._definition))

    @property
    def key(self):
        return f'{self.kind}:{self.content_id}'

    def definition(self):
        return deepcopy(self._definition)

    def manifest(self):
        return {
            'key': self.key,
            'kind': self.kind,
            'content_id': self.content_id,
            'definition': self.definition(),
            'sources': [source.manifest() for source in self.sources],
        }


class StoryContentRegistry:
    def __init__(self, records):
        by_key = {}
        for record in records:
            if not isinstance(record, StoryContentRecord):
                raise StoryContentModelError('注册表只能包含规范故事内容记录')
            if record.key in by_key:
                raise StoryContentModelError(f'故事内容键重复 {record.key}')
            by_key[record.key] = record
        self._records = by_key
        manifest_json = json.dumps(
            self.manifest(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(',', ':'),
        )
        self.fingerprint = hashlib.sha256(manifest_json.encode('utf-8')).hexdigest()

    def record(self, kind, content_id):
        key = f'{kind}:{content_id}'
        record = self._records.get(key)
        if record is None:
            raise StoryContentModelError(f'不存在故事内容 {key}')
        return record

    def definition(self, kind, content_id):
        return self.record(kind, content_id).definition()

    def catalog(self, kind):
        if kind not in STORY_CONTENT_KINDS:
            raise StoryContentModelError(f'未知故事内容类型 {kind}')
        return {
            record.content_id: record.definition()
            for record in self._records.values()
            if record.kind == kind
        }

    def keys(self, kind=None):
        return tuple(sorted(
            key for key, record in self._records.items()
            if kind is None or record.kind == kind
        ))

    def manifest(self):
        return {
            'model_version': STORY_CONTENT_MODEL_VERSION,
            'records': {
                key: self._records[key].manifest()
                for key in sorted(self._records)
            },
        }


def _workbook_source(sheet, cell_range, note=''):
    return StoryContentSource(
        source_type='workbook',
        source_version=STORY_WORKBOOK_SOURCE_VERSION,
        workbook_file=STORY_WORKBOOK_FILE,
        sheet=sheet,
        cell_range=cell_range,
        note=note,
    )


def _code_source(code_symbol, note=''):
    return StoryContentSource(
        source_type='code',
        source_version='python-source:2026-08-31',
        code_symbol=code_symbol,
        note=note,
    )


_CARD_ROWS = {
    'basic': 3, 'rose': 4, 'amulet': 5, 'enchanted_amulet': 6,
    'bone': 7, 'coffee': 8, 'bur': 9, 'torch': 10, 'antibody': 11,
    'rock': 12, 'triangle': 13, 'sand': 14, 'shell': 15,
    'lightning': 16, 'magic_torch': 17, 'sponge': 18, 'mimic': 19,
    'light': 20, 'missile': 21, 'antler': 22, 'stinger': 23,
    'fries': 24, 'heavy': 25, 'disc': 26, 'salt': 27,
    'magic_shell': 28, 'pearl': 29, 'crystal_leaf': 30,
    'magic_crystal_leaf': 31, 'magic_pearl': 32, 'magic_acid': 33,
    'azalea': 34, 'fusion': 35, 'chromosome': 36, 'dna': 37,
    'moon_rock': 38, 'ice': 39, 'soul_splitter': 40, 'cutter': 41,
    'powder': 42, 'rna': 43, 'nuke': 44, 'rmb': 45, 'magic_bur': 46,
    'fission': 47, 'cotton': 48, 'startled': 49, 'fatigued': 50,
    'slimed': 51, 'injury': 52, 'unrelenting': 53, 'fragment': 54,
    'rice': 55, 'glass': 56, 'dust': 57, 'leaf': 58, 'acid': 59,
    'pyrite': 60, 'feather': 61, 'magic_feather': 62, 'bubble': 63,
    'magic_bubble': 64, 'mark': 65, 'dandelion_seed': 67,
    'yin_yang': 68, 'sewage': 69, 'sand_dust': 70, 'confused': 71,
    'static_electricity': 72, 'corruption': 73, 'mjolnir': 77,
    'chilly': 78, 'jelly': 79, 'nitro': 80, 'cogwheel': 81,
    'chloroplast': 82, 'beeswax': 83, 'bamboo': 84, 'corn': 85,
    'maple': 86, 'assembler': 87, 'redemption_money': 88,
    'antennae': 89, 'sunflower_card': 90, 'wind': 91, 'ankh': 92,
    'trident': 93, 'magic_trident': 94, 'magic_yin_yang': 95,
    'magic_assembler': 96, 'magic_chilly': 97, 'mushroom': 98,
    'puppeteer': 99, 'seed': 100, 'factory_waste': 101,
    'mage_basic': 103, 'mage_fries': 108, 'mage_coffee': 109,
    'mage_bone': 115, 'mage_palm_leaf': 122,
    'mage_bubble_bomb': 126, 'mage_rock': 131,
    'mage_missile': 139, 'mage_rose': 142,
}
_CARD_ROWS.update({
    content_id: index + 103
    for index, content_id in enumerate(STORY_CHARACTER_CARD_DESIGNS)
})

_RELIC_ROWS = {
    'energetic': 3, 'ruthless': 14, 'firm_defense': 15,
    'fearless_pain': 16, 'circulation': 17, 'prepared': 18,
    'cooldown': 19, 'accumulate': 20, 'opening_lightning': 21,
    'solid_barrier': 22, 'sharpen': 23, 'blade': 24, 'steady': 25,
    'rich': 26, 'diligent': 27, 'greedy': 28, 'body_reinforcement': 29,
    'indomitable': 30, 'support': 31, 'bargaining': 32,
    'world_tree_leaf': 33, 'dandelion_blessing': 34,
    'coward_defense': 35, 'return_to_origin': 36, 'last_stand': 37,
    'quantized': 38, 'dizzy_relic': 39, 'uranium': 40, 'strive': 41,
    'gluttony': 42, 'frugal': 43, 'avoid_elite': 44,
    'grab_every_card': 45, 'cognitive_bias': 46, 'pollen_relic': 47,
    'web_relic': 48, 'first_strike': 49, 'fast_learning': 50,
    'peaceful_mind': 51, 'phoenix': 52, 'sword_strategy': 53,
    'perfection': 54, 'frenzy_relic': 55, 'easy_miracle': 69,
    'easy_peace': 70, 'easy_study': 71, 'easy_tiger': 72,
    'easy_godhood': 74, 'consolation': 75, 'magic_source': 4,
}

_ENEMY_ROWS = {
    'soldier_ant': 2, 'young_ant': 3, 'worker_ant': 4, 'bee': 5,
    'wasp': 6, 'ladybug': 7, 'garden_rock': 8, 'dandelion': 9,
    'centipede': 10, 'spider': 11, 'sunflower': 12, 'avocado': 13,
    'spider_yoba': 14, 'digger': 15, 'ant_queen': 16, 'hive': 17,
    'cicada': 18, 'sandstorm': 19, 'palm_tree': 20, 'cactus': 21,
    'sandstone': 22, 'bandage_beetle': 23, 'scorpion': 24,
    'tumbleweed': 25, 'rain_frog': 26, 'nazar_beetle': 27,
    'fossil': 28, 'shiny_ladybug': 29, 'worm': 30,
    'desert_centipede': 31, 'ocean_bubble': 32, 'crab': 33,
    'lily_pad': 34, 'waterspout': 35, 'urchin': 36, 'turtle': 37,
    'electric_eel': 38, 'leech': 39, 'shark': 40, 'ocean_shell': 41,
    'ocean_pearl': 42, 'starfish': 43, 'jellyfish': 44, 'squid': 45,
    'shipwreck': 46, 'wreckage': 47, 'termite_soldier': 49,
    'termite_worker': 50, 'termite_overmind': 51, 'leafbug': 52,
    'dark_ladybug': 53, 'jungle_firefly': 54, 'jungle_wasp': 55,
    'jungle_fly': 56, 'jungle_mushroom': 57, 'pumpkin': 58,
    'snail': 59, 'bush': 60, 'spider_cave': 61, 'stickbug': 62,
    'stick': 63, 'termite_mound': 64, 'evil_centipede': 65,
    'magic_firefly': 66, 'mechanical_flower': 67,
    'mechanical_spider': 68, 'mechanical_crab': 69,
    'uranium_barrel': 70, 'reconstructor_enemy': 71,
    'mechanical_wasp': 72, 'mechanical_missile': 73, 'smoke': 74,
    'brick_pile': 75, 'mechanical_rat': 76, 'broken_machine': 77,
    'chimney': 78, 'generator': 79,
}

_ENCOUNTER_ROWS = {
    ('garden', 'simple'): (8, 9, 10),
    ('garden', 'hard'): (11, 12, 13, 14, 15, 16, 17, 18),
    ('garden', 'elite'): (2, 3, 4),
    ('garden', 'boss'): (5, 6, 7),
    ('desert', 'simple'): (25, 26, 27),
    ('desert', 'hard'): (28, 29, 30, 31, 32, 33, 34),
    ('desert', 'elite'): (22, 23, 24),
    ('desert', 'boss'): (19, 20, 21),
    ('ocean', 'simple'): (41, 42, 43),
    ('ocean', 'hard'): (44, 45, 46, 47, 48, 49, 50),
    ('ocean', 'elite'): (38, 39, 40),
    ('ocean', 'boss'): (35, 36, 37),
    ('jungle', 'simple'): (52, 53, 54),
    ('jungle', 'hard'): (55, 56, 57, 58, 59, 60, 61, 62, 63),
    ('jungle', 'elite'): (64, 65, 66),
    ('jungle', 'boss'): (67, 68, 69),
    ('factory', 'simple'): (70, 71, 80, 82, 83),
    ('factory', 'hard'): (72, 73, 81, 84, 85),
    ('factory', 'elite'): (74, 78, 79),
    ('factory', 'boss'): (75, 76, 77),
}


def _encounter_members(spec):
    return [
        deepcopy(member) if isinstance(member, dict) else {'def_id': str(member)}
        for member in spec
    ]


def _source_for(kind, content_id, *, row=None):
    if kind == 'character':
        return (_workbook_source('角色设计（先不做）', f'A{row}:B{row}'),)
    if kind == 'character_card':
        return (_workbook_source('爬塔卡牌设计', f'B{row}:K{row}'),)
    if kind == 'character_relic':
        return (_workbook_source('爬塔天赋设计', f'A{row}:D{row}'),)
    if kind == 'term':
        return (_workbook_source('爬塔卡牌设计', f'B{row}:F{row}'),)
    if kind == 'blessing':
        return (_workbook_source('爬塔赐福设计', f'A{row}:B{row}'),)
    if kind == 'card':
        if content_id in STORY_CHARACTER_CARD_DESIGNS:
            return (_workbook_source('爬塔卡牌设计', f'B{row}:K{row}'),)
        return (_workbook_source('爬塔卡牌设计', f'A{row}:K{row}'),)
    if kind == 'relic':
        return (_workbook_source('爬塔天赋设计', f'A{row}:D{row}'),)
    if kind == 'enemy':
        return (_workbook_source('爬塔怪物设计', f'A{row}:P{row}'),)
    if kind == 'encounter':
        return (_workbook_source('战斗列表', f'A{row}:D{row}'),)
    if kind == 'card_type':
        return (_workbook_source('爬塔卡牌设计', 'E3:E158'),)
    if kind == 'tag':
        return (
            _workbook_source('爬塔卡牌设计', 'G3:G158'),
            _workbook_source('标签', 'A1:B14'),
        )
    if kind == 'status':
        return (
            _workbook_source('爬塔卡牌设计', 'N3:O158'),
            _workbook_source('效果', 'A2:B23'),
        )
    if kind == 'trait':
        return (
            _workbook_source('爬塔卡牌设计', 'L3:M158'),
            _workbook_source('爬塔怪物设计', 'E2:O80'),
        )
    if kind == 'biome':
        return (_workbook_source('爬塔玩法设计', 'A1:D5'),)
    if kind == 'difficulty':
        return (_workbook_source('爬塔玩法设计', 'A17:D25'),)
    if kind == 'rule':
        return (_workbook_source('爬塔玩法设计', 'A6:D44'),)
    if kind == 'event':
        return (_code_source(
            f'story_content.STORY_EVENTS[{content_id!r}]',
            '代码新增共享事件；工作簿中没有对应单元格。',
        ),)
    raise StoryContentModelError(f'没有来源路由 {kind}:{content_id}')


def build_story_content_registry(
        *, rules=None, characters=None, biomes=None, difficulties=None,
        card_types=None,
        tags=None, statuses=None, traits=None, blessings=None, cards=None,
        relics=None, enemies=None, encounters=None, events=None,
        character_cards=None, character_relics=None, terms=None):
    catalogs = {
        'rule': {'global': deepcopy(STORY_RULES if rules is None else rules)},
        'character': deepcopy(
            STORY_CHARACTERS if characters is None else characters
        ),
        'character_card': deepcopy(
            STORY_CHARACTER_CARD_DESIGNS
            if character_cards is None else character_cards
        ),
        'character_relic': deepcopy(
            STORY_CHARACTER_RELIC_DESIGNS
            if character_relics is None else character_relics
        ),
        'term': deepcopy(STORY_CHARACTER_TERMS if terms is None else terms),
        'biome': deepcopy(STORY_BIOMES if biomes is None else biomes),
        'difficulty': deepcopy(
            STORY_DIFFICULTIES if difficulties is None else difficulties
        ),
        'card_type': deepcopy(STORY_CARD_TYPES if card_types is None else card_types),
        'tag': deepcopy(STORY_TAGS if tags is None else tags),
        'status': deepcopy(STORY_STATUSES if statuses is None else statuses),
        'trait': deepcopy(STORY_TRAITS if traits is None else traits),
        'blessing': deepcopy(STORY_BLESSINGS if blessings is None else blessings),
        'card': deepcopy(STORY_CARDS if cards is None else cards),
        'relic': deepcopy(STORY_RELICS if relics is None else relics),
        'enemy': deepcopy(STORY_ENEMIES if enemies is None else enemies),
        'event': deepcopy(STORY_EVENTS if events is None else events),
    }
    encounter_catalog = deepcopy(STORY_ENCOUNTERS if encounters is None else encounters)
    records = []

    precise_rows = {
        'card': _CARD_ROWS,
        'relic': _RELIC_ROWS,
        'enemy': _ENEMY_ROWS,
    }
    for kind, catalog in catalogs.items():
        for index, (content_id, definition) in enumerate(catalog.items(), 1):
            row = None
            if kind == 'character':
                row = index
            elif kind == 'character_card':
                row = index + 102
            elif kind == 'character_relic':
                row = index + 3
            elif kind == 'term':
                row = 157 + index
            elif kind == 'blessing':
                row = index + 1
            elif kind in precise_rows:
                row = precise_rows[kind].get(content_id)
                if row is None:
                    raise StoryContentModelError(
                        f'新增 {kind}:{content_id} 必须先登记工作簿或代码来源'
                    )
            records.append(StoryContentRecord(
                kind=kind,
                content_id=content_id,
                sources=_source_for(kind, content_id, row=row),
                _definition=definition,
            ))

    for biome, tiers in encounter_catalog.items():
        for tier, specs in tiers.items():
            rows = _ENCOUNTER_ROWS.get((biome, tier))
            if rows is None or len(rows) != len(specs):
                raise StoryContentModelError(
                    f'战斗组合 {biome}:{tier} 与工作簿来源行不一致'
                )
            for index, (spec, row) in enumerate(zip(specs, rows), 1):
                content_id = f'{biome}:{tier}:{index:03d}'
                records.append(StoryContentRecord(
                    kind='encounter',
                    content_id=content_id,
                    sources=_source_for('encounter', content_id, row=row),
                    _definition={
                        'biome': biome,
                        'tier': tier,
                        'members': _encounter_members(spec),
                    },
                ))
    return StoryContentRegistry(records)


STORY_CONTENT_REGISTRY = build_story_content_registry()
STORY_CONTENT_FINGERPRINT = STORY_CONTENT_REGISTRY.fingerprint


def validate_story_content_model():
    """Fail closed when a canonical catalog entry lacks normalized provenance."""

    expected = {
        'rule': 1,
        'character': len(STORY_CHARACTERS),
        'character_card': len(STORY_CHARACTER_CARD_DESIGNS),
        'character_relic': len(STORY_CHARACTER_RELIC_DESIGNS),
        'term': len(STORY_CHARACTER_TERMS),
        'biome': len(STORY_BIOMES),
        'difficulty': len(STORY_DIFFICULTIES),
        'card_type': len(STORY_CARD_TYPES),
        'tag': len(STORY_TAGS),
        'status': len(STORY_STATUSES),
        'trait': len(STORY_TRAITS),
        'blessing': len(STORY_BLESSINGS),
        'card': len(STORY_CARDS),
        'relic': len(STORY_RELICS),
        'enemy': len(STORY_ENEMIES),
        'encounter': sum(
            len(specs)
            for tiers in STORY_ENCOUNTERS.values()
            for specs in tiers.values()
        ),
        'event': len(STORY_EVENTS),
    }
    for kind, count in expected.items():
        actual = len(STORY_CONTENT_REGISTRY.keys(kind))
        if actual != count:
            raise StoryContentModelError(
                f'故事内容模型 {kind} 数量错误：{actual} != {count}'
            )
    return True
