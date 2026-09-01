"""Account-level discovery extraction for the story-mode compendium."""

from copy import deepcopy
import re

from story_content import (
    STORY_BLESSINGS,
    STORY_CARDS,
    STORY_ENEMIES,
    STORY_ENCHANTMENT_BOOKS,
    STORY_RELICS,
    STORY_STATUSES,
    STORY_TAGS,
    STORY_TRAITS,
)


_RESOURCE_PATTERN = re.compile(r"\[\[icon:([DHEM])\]\]|(?<![A-Za-z])([DHEM])(?![A-Za-z])")
_CARD_COLLECTION_KEYS = (
    'deck', 'hand', 'draw_pile', 'discard_pile', 'exile_pile', 'equipment',
)


def _localized_values(value):
    if isinstance(value, dict):
        return tuple(str(item or '') for item in value.values())
    return (str(value or ''),)


def _walk_values(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key), item
            yield from _walk_values(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_values(item)


def _effective_card_definition(card_id, upgraded=False):
    definition = STORY_CARDS.get(str(card_id or ''))
    if not definition:
        return None
    values = deepcopy(definition)
    if upgraded and isinstance(definition.get('upgrade'), dict):
        values.update(deepcopy(definition['upgrade']))
    return values


def _status_is_visible(value):
    try:
        return float(value or 0) != 0
    except (TypeError, ValueError):
        return bool(value)


def collect_story_discoveries(state):
    """Return normalized discoveries that are currently visible in ``state``.

    The extractor deliberately ignores the generated route map. Future rooms may
    already exist in the server state, but they have not been shown to the player.
    """
    state = state if isinstance(state, dict) else {}
    found = set()

    def add(content_type, content_id, variant='base'):
        content_type = str(content_type or '').strip().lower()
        content_id = str(content_id or '').strip()
        variant = str(variant or 'base').strip().lower()
        if content_type and content_id:
            found.add((content_type, content_id, variant))

    def add_term(kind, term_id):
        term_id = str(term_id or '').strip()
        catalog = {
            'tag': STORY_TAGS,
            'status': STORY_STATUSES,
            'trait': STORY_TRAITS,
            'resource': {'D': None, 'H': None, 'E': None, 'M': None},
        }.get(kind)
        if catalog is not None and term_id in catalog:
            add('term', f'{kind}:{term_id}')

    def add_definition_terms(definition):
        if not isinstance(definition, dict):
            return
        for tag_id in definition.get('tags') or ():
            add_term('tag', tag_id)
        text_values = []
        for field in ('description', 'flavor', 'name'):
            text_values.extend(_localized_values(definition.get(field)))
        if definition.get('cost_e') is not None:
            add_term('resource', 'E')
        if definition.get('cost_m') is not None:
            add_term('resource', 'M')
        for text in text_values:
            for match in _RESOURCE_PATTERN.finditer(text):
                add_term('resource', match.group(1) or match.group(2))
        for key, value in _walk_values(definition.get('effects') or ()):
            if isinstance(value, str):
                if value in STORY_STATUSES:
                    add_term('status', value)
                if value in STORY_TAGS and key in ('tag', 'tags'):
                    add_term('tag', value)
            if key == 'type' and value in {
                'damage', 'damage_per_status', 'damage_from_shield',
                'damage_per_elixir', 'self_damage',
            }:
                add_term('resource', 'D')
            elif key == 'type' and value in {
                'heal', 'self_heal', 'allies_heal', 'heal_to_full',
            }:
                add_term('resource', 'H')
            elif key == 'type' and value in {'elixir', 'turn_elixir'}:
                add_term('resource', 'E')
            elif key == 'type' and value in {'magic', 'turn_magic'}:
                add_term('resource', 'M')

    def add_card(card_or_id, upgraded=None):
        if isinstance(card_or_id, dict):
            card_id = card_or_id.get('def_id') or card_or_id.get('card_id')
            is_upgraded = bool(card_or_id.get('upgraded'))
        else:
            card_id = card_or_id
            is_upgraded = bool(upgraded)
        card_id = str(card_id or '')
        definition = _effective_card_definition(card_id, is_upgraded)
        if not definition:
            return
        add('card', card_id, 'upgraded' if is_upgraded else 'base')
        add_definition_terms(definition)

    def add_relic(relic_id):
        relic_id = str(relic_id or '')
        definition = STORY_RELICS.get(relic_id)
        if not definition:
            return
        add('relic', relic_id)
        add_definition_terms(definition)

    def add_blessing(blessing_id):
        blessing_id = str(blessing_id or '')
        definition = STORY_BLESSINGS.get(blessing_id)
        if not definition:
            return
        add('blessing', blessing_id)
        add_definition_terms(definition)

    def add_enchantment_book(book_or_id):
        book_id = (
            book_or_id.get('book_id')
            if isinstance(book_or_id, dict)
            else book_or_id
        )
        book_id = str(book_id or '')
        definition = STORY_ENCHANTMENT_BOOKS.get(book_id)
        if not definition:
            return
        add('enchantment_book', book_id)
        add_definition_terms(definition)

    def add_enemy(enemy):
        if not isinstance(enemy, dict):
            return
        enemy_id = str(enemy.get('def_id') or '')
        definition = STORY_ENEMIES.get(enemy_id)
        if not definition:
            return
        add('enemy', enemy_id)
        intent = enemy.get('intent') if isinstance(enemy.get('intent'), dict) else {}
        move_index = intent.get('move_index')
        if not isinstance(move_index, int) and intent.get('name') is not None:
            move_index = next(
                (
                    index
                    for index, move in enumerate(definition.get('moves') or ())
                    if move.get('name') == intent.get('name')
                ),
                None,
            )
        if not isinstance(move_index, int):
            move_index = enemy.get('move_index')
        if isinstance(move_index, int) and 0 <= move_index < len(definition.get('moves') or ()):
            add('enemy', enemy_id, f'intent:{move_index}')
            add_definition_terms(definition['moves'][move_index])
        for trait_id in definition.get('traits') or ():
            add_term('trait', trait_id)
        for status_id in STORY_STATUSES:
            if _status_is_visible(enemy.get(status_id)):
                add_term('status', status_id)

    player = state.get('player') if isinstance(state.get('player'), dict) else {}
    for card in player.get('deck') or ():
        add_card(card)
    for relic_id in player.get('relics') or ():
        add_relic(relic_id)
    for blessing_id in player.get('blessings') or ():
        add_blessing(blessing_id)
    if player.get('blessing'):
        add_blessing(player.get('blessing'))
    for book in player.get('enchantment_books') or ():
        add_enchantment_book(book)

    combat = state.get('combat') if isinstance(state.get('combat'), dict) else {}
    for key in _CARD_COLLECTION_KEYS:
        for card in combat.get(key) or ():
            add_card(card)
    for enemy in combat.get('enemies') or ():
        add_enemy(enemy)
    for status_id in STORY_STATUSES:
        if _status_is_visible(combat.get(status_id)):
            add_term('status', status_id)

    reward = state.get('reward') if isinstance(state.get('reward'), dict) else {}
    for card in reward.get('cards') or ():
        add_card(card)
    for relic_id in reward.get('relics') or ():
        add_relic(relic_id)
    add_relic(reward.get('relic'))
    add_relic(reward.get('selected_relic_id'))
    add_enchantment_book(reward.get('enchantment_book'))
    add_enchantment_book(reward.get('selected_enchantment_book_id'))
    selected_card_id = reward.get('selected_card_id')
    if selected_card_id:
        selected = next(
            (
                card for card in reward.get('cards') or ()
                if isinstance(card, dict) and card.get('card_id') == selected_card_id
            ),
            selected_card_id,
        )
        add_card(selected)

    room = state.get('room') if isinstance(state.get('room'), dict) else {}
    for card in room.get('cards') or ():
        add_card(card)
    for relic in room.get('relics') or ():
        add_relic(relic.get('relic_id') if isinstance(relic, dict) else relic)
    add_relic(room.get('relic'))
    for book in room.get('enchantment_books') or ():
        add_enchantment_book(
            book.get('book_id') if isinstance(book, dict) else book
        )

    # Current event results may reveal generated content without adding it to
    # the deck. Restrict this recursive scan to the active room and last events.
    for visible in (room, state.get('last_events') or ()):
        for key, value in _walk_values(visible):
            if key in ('card_id', 'def_id', 'from_def_id', 'to_def_id'):
                add_card(value)
            elif key in ('relic', 'relic_id', 'selected_relic_id'):
                add_relic(value)
            elif key in ('blessing', 'blessing_id'):
                add_blessing(value)
            elif key in ('status', 'status_id'):
                add_term('status', value)
            elif key in ('trait', 'trait_id'):
                add_term('trait', value)
            elif key in (
                'book_id', 'enchantment_book',
                'selected_enchantment_book_id',
            ):
                add_enchantment_book(value)

    for blessing_id in state.get('blessing_options') or ():
        add_blessing(blessing_id)

    return [
        {'content_type': kind, 'content_id': content_id, 'variant': variant}
        for kind, content_id, variant in sorted(found)
    ]
