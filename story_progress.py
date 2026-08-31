"""Server-authoritative character and difficulty unlock rules for Story mode."""

from __future__ import annotations


STORY_CHARACTER_CHAIN = (
    'common_flower',
    'mage',
    'orbiter',
    'summoner',
    'occultist',
)
STORY_DIFFICULTIES = ('easy', 'normal', 'hard', 'lunatic')
STORY_JOURNEY_MODES = ('standard', 'boss_rush')


def normalize_story_character_id(value):
    character_id = str(value or '').strip().lower()
    if character_id not in STORY_CHARACTER_CHAIN:
        raise ValueError('UNKNOWN_STORY_CHARACTER')
    return character_id


def normalize_story_difficulty(value):
    difficulty = str(value or '').strip().lower()
    if difficulty not in STORY_DIFFICULTIES:
        raise ValueError('UNKNOWN_STORY_DIFFICULTY')
    return difficulty


def normalize_story_journey_mode(value):
    mode = str(value or 'standard').strip().lower()
    if mode not in STORY_JOURNEY_MODES:
        raise ValueError('UNKNOWN_STORY_JOURNEY_MODE')
    return mode


def build_story_progress_payload(rows=()):
    """Project persisted clear counters into the public unlock contract."""

    clears = {
        character_id: {
            difficulty: {'standard': 0, 'boss_rush': 0}
            for difficulty in STORY_DIFFICULTIES
        }
        for character_id in STORY_CHARACTER_CHAIN
    }
    for row in rows or ():
        try:
            character_id = normalize_story_character_id(row.get('character_id'))
            difficulty = normalize_story_difficulty(row.get('difficulty'))
        except (AttributeError, ValueError):
            continue
        clears[character_id][difficulty] = {
            'standard': max(0, int(row.get('standard_clears') or 0)),
            'boss_rush': max(0, int(row.get('boss_rush_clears') or 0)),
        }

    characters = {}
    for index, character_id in enumerate(STORY_CHARACTER_CHAIN):
        prerequisite = STORY_CHARACTER_CHAIN[index - 1] if index else None
        unlocked = prerequisite is None or any(
            clears[prerequisite][difficulty]['standard'] > 0
            for difficulty in STORY_DIFFICULTIES
        )
        normal_complete = clears[character_id]['normal']['standard'] > 0
        hard_complete = clears[character_id]['hard']['standard'] > 0
        characters[character_id] = {
            'unlocked': bool(unlocked),
            'unlock_character_id': prerequisite,
            'completed_any_difficulty': any(
                clears[character_id][difficulty]['standard'] > 0
                for difficulty in STORY_DIFFICULTIES
            ),
            'difficulties': {
                'easy': True,
                'normal': True,
                'hard': bool(normal_complete),
                'lunatic': bool(hard_complete),
            },
            'modes': {
                'standard': True,
                'boss_rush': bool(hard_complete),
            },
            'clears': clears[character_id],
        }
    return {
        'schema_version': 1,
        'characters': characters,
    }


def story_character_is_unlocked(progress, character_id):
    try:
        character_id = normalize_story_character_id(character_id)
    except ValueError:
        return False
    return bool(
        ((progress or {}).get('characters') or {})
        .get(character_id, {})
        .get('unlocked')
    )


def story_journey_is_unlocked(progress, character_id, difficulty, journey_mode):
    try:
        character_id = normalize_story_character_id(character_id)
        difficulty = normalize_story_difficulty(difficulty)
        journey_mode = normalize_story_journey_mode(journey_mode)
    except ValueError:
        return False
    character = ((progress or {}).get('characters') or {}).get(character_id) or {}
    return bool(
        character.get('unlocked')
        and (character.get('difficulties') or {}).get(difficulty)
        and (character.get('modes') or {}).get(journey_mode)
    )


def story_coop_unlock_intersection(progress_by_user, character_id):
    """Return difficulties/modes shared by every party member."""

    progress_values = list((progress_by_user or {}).values())
    if not progress_values:
        return {'difficulties': [], 'modes': []}
    try:
        character_id = normalize_story_character_id(character_id)
    except ValueError:
        return {'difficulties': [], 'modes': []}
    difficulties = [
        difficulty
        for difficulty in STORY_DIFFICULTIES
        if all(
            story_journey_is_unlocked(progress, character_id, difficulty, 'standard')
            for progress in progress_values
        )
    ]
    modes = [
        mode
        for mode in STORY_JOURNEY_MODES
        if all(
            story_journey_is_unlocked(progress, character_id, 'normal', mode)
            for progress in progress_values
        )
    ]
    return {'difficulties': difficulties, 'modes': modes}
