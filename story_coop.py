"""Pure cooperative-story state contracts.

This module is intentionally additive.  The live single-player story engine
continues to persist schema v9 until the cooperative engine can consume every
v10 phase.  Cooperative routes may build v10 states here without changing or
silently upgrading an existing solo run.
"""

from copy import deepcopy
from types import MappingProxyType

from story_mode import build_initial_story_state


COOP_STORY_SCHEMA_VERSION = 10
LEGACY_SOLO_STORY_SCHEMA_VERSION = 9
COOP_STORY_MIN_PLAYERS = 2
COOP_STORY_MAX_PLAYERS = 4
COOP_STORY_MVP_MAX_PLAYERS = 2

COOP_STORY_PUBLIC_MEMBER_FIELDS = frozenset({
    'seat',
    'user_id',
    'username',
    'display_name',
    'membership_status',
    'party_role',
})

COOP_STORY_DEFAULT_RULES = MappingProxyType({
    'turn_model': 'shared_hero_phase',
    'action_ordering': 'server_serialized',
    'route_vote_policy': 'seeded_random',
    'event_vote_policy': 'unanimous_then_seeded_random',
    'reward_scope': 'per_player',
    'gold_scope': 'per_player',
    'hand_visibility': 'party',
    'allow_mid_combat_join': False,
    'disconnect_policy': 'auto_ready_after_grace',
    'post_combat_revive_ratio': 0.20,
})


class CoopStoryStateError(ValueError):
    """A stable validation failure suitable for API error mapping."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = str(code)
        self.message = str(message)


def coop_story_default_rules():
    """Return an independent JSON-serializable copy of the v10 rule contract."""

    return dict(COOP_STORY_DEFAULT_RULES)


def _positive_int(value, *, code, label):
    if isinstance(value, bool):
        raise CoopStoryStateError(code, f'{label}必须是正整数')
    if isinstance(value, int):
        normalized = value
    elif isinstance(value, str) and value.strip().isdecimal():
        normalized = int(value.strip())
    else:
        raise CoopStoryStateError(code, f'{label}必须是正整数')
    if normalized <= 0:
        raise CoopStoryStateError(code, f'{label}必须是正整数')
    return normalized


def _public_member(member, seat):
    if not isinstance(member, dict):
        raise CoopStoryStateError('INVALID_MEMBER', '队伍成员格式无效')
    user_id = _positive_int(
        member.get('user_id'),
        code='INVALID_MEMBER_USER_ID',
        label='成员账号编号',
    )
    username = str(member.get('username') or '').strip()
    if not username or len(username) > 64:
        raise CoopStoryStateError('INVALID_MEMBER_USERNAME', '成员账号名称无效')
    display_name = str(member.get('display_name') or username).strip()
    if not display_name or len(display_name) > 64:
        raise CoopStoryStateError('INVALID_MEMBER_DISPLAY_NAME', '成员显示名称无效')
    return {
        'seat': int(seat),
        'user_id': user_id,
        'username': username,
        'display_name': display_name,
        'membership_status': 'active',
        'party_role': 'leader' if int(seat) == 0 else 'member',
    }


def _normalize_members(members, *, minimum, maximum):
    if not isinstance(members, (list, tuple)):
        raise CoopStoryStateError('INVALID_MEMBERS', '队伍成员列表无效')
    if len(members) < minimum or len(members) > maximum:
        raise CoopStoryStateError(
            'INVALID_MEMBER_COUNT',
            f'队伍人数必须在 {minimum} 到 {maximum} 人之间',
        )
    normalized = [_public_member(member, seat) for seat, member in enumerate(members)]
    user_ids = [member['user_id'] for member in normalized]
    if len(set(user_ids)) != len(user_ids):
        raise CoopStoryStateError('DUPLICATE_MEMBER', '同一账号不能占用多个队伍席位')
    return normalized


def _coordination_state():
    return {
        'action_sequence': 0,
        'action_receipts': {},
        'combat_ready_seats': [],
        'combat_ready_round': None,
        'map_vote': None,
        'room_decision': None,
    }


def _party_state(members, *, mode, max_players):
    return {
        'mode': str(mode),
        'leader_seat': 0,
        'max_players': int(max_players),
        'members': deepcopy(members),
        'rules': coop_story_default_rules(),
    }


def _convert_base_state(base_state, members, *, mode, max_players):
    state = deepcopy(base_state)
    player = state.pop('player', None)
    if not isinstance(player, dict):
        raise CoopStoryStateError('INVALID_LEGACY_PLAYER', '故事玩家状态无效')
    legacy_reward = state.pop('reward', None)
    state['schema_version'] = COOP_STORY_SCHEMA_VERSION
    state['mode'] = str(mode)
    state['party'] = _party_state(members, mode=mode, max_players=max_players)
    state['players'] = {
        str(member['seat']): deepcopy(player)
        for member in members
    }
    state['coordination'] = _coordination_state()
    state['shared_reward'] = None
    state['rewards_by_player'] = (
        {'0': deepcopy(legacy_reward)}
        if legacy_reward is not None and len(members) == 1
        else None
    )
    return state


def build_initial_coop_story_state(seed, members, max_players=COOP_STORY_MVP_MAX_PLAYERS):
    """Build a deterministic v10 cooperative run without touching live v9 data."""

    if isinstance(max_players, bool) or not isinstance(max_players, int):
        raise CoopStoryStateError('INVALID_MAX_PLAYERS', '队伍人数上限必须是正整数')
    if not COOP_STORY_MIN_PLAYERS <= max_players <= COOP_STORY_MAX_PLAYERS:
        raise CoopStoryStateError(
            'INVALID_MAX_PLAYERS',
            f'队伍人数上限必须在 {COOP_STORY_MIN_PLAYERS} 到 {COOP_STORY_MAX_PLAYERS} 人之间',
        )
    normalized_members = _normalize_members(
        members,
        minimum=COOP_STORY_MIN_PLAYERS,
        maximum=max_players,
    )
    base_state = build_initial_story_state(str(seed))
    return _convert_base_state(
        base_state,
        normalized_members,
        mode='coop',
        max_players=max_players,
    )


def upgrade_v9_solo_story_state(state, member):
    """Safely wrap a non-combat v9 solo state as a one-seat v10 party.

    In-combat migration is deliberately rejected because v9 keeps one mixed
    combat object, while v10 requires private combat zones for every seat.
    """

    if not isinstance(state, dict):
        raise CoopStoryStateError('INVALID_STORY_STATE', '故事状态无效')
    try:
        schema_version = int(state.get('schema_version') or 0)
    except (TypeError, ValueError) as exc:
        raise CoopStoryStateError('UNSUPPORTED_SCHEMA_VERSION', '只支持迁移故事 schema v9') from exc
    if schema_version != LEGACY_SOLO_STORY_SCHEMA_VERSION:
        raise CoopStoryStateError('UNSUPPORTED_SCHEMA_VERSION', '只支持迁移故事 schema v9')
    if state.get('combat') is not None:
        raise CoopStoryStateError(
            'COMBAT_MIGRATION_UNSUPPORTED',
            '战斗中的单人旅程不能迁移到多人状态',
        )
    normalized_members = _normalize_members([member], minimum=1, maximum=1)
    return _convert_base_state(
        state,
        normalized_members,
        mode='solo',
        max_players=1,
    )


def validate_story_state_v10(state, *, expected_mode=None):
    """Validate structural invariants shared by persistence and transport."""

    if not isinstance(state, dict):
        raise CoopStoryStateError('INVALID_STORY_STATE', '故事状态无效')
    schema_version = state.get('schema_version')
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version != COOP_STORY_SCHEMA_VERSION
    ):
        raise CoopStoryStateError('INVALID_SCHEMA_VERSION', '故事状态不是 schema v10')
    if 'player' in state:
        raise CoopStoryStateError('LEGACY_PLAYER_PRESENT', 'schema v10 不能包含单数 player 字段')
    mode = str(state.get('mode') or '')
    if mode not in {'solo', 'coop'}:
        raise CoopStoryStateError('INVALID_STORY_MODE', '故事状态模式无效')
    if expected_mode is not None and mode != str(expected_mode):
        raise CoopStoryStateError('STORY_MODE_MISMATCH', '故事状态模式不匹配')
    party = state.get('party')
    players = state.get('players')
    coordination = state.get('coordination')
    if not isinstance(party, dict) or not isinstance(players, dict):
        raise CoopStoryStateError('INVALID_PARTY_STATE', '队伍或玩家状态无效')
    if not isinstance(coordination, dict):
        raise CoopStoryStateError('INVALID_COORDINATION_STATE', '队伍协作状态无效')
    action_sequence = coordination.get('action_sequence', 0)
    if (
        isinstance(action_sequence, bool)
        or not isinstance(action_sequence, int)
        or action_sequence < 0
    ):
        raise CoopStoryStateError('INVALID_ACTION_SEQUENCE', '协作动作序号无效')
    if not isinstance(coordination.get('action_receipts', {}), dict):
        raise CoopStoryStateError('INVALID_ACTION_RECEIPTS', '协作动作回执无效')
    combat_ready_seats = coordination.get('combat_ready_seats', [])
    if not isinstance(combat_ready_seats, list):
        raise CoopStoryStateError('INVALID_COMBAT_READY_STATE', '战斗准备席位无效')
    members = party.get('members')
    if not isinstance(members, list):
        raise CoopStoryStateError('INVALID_MEMBERS', '队伍成员列表无效')
    if any(not isinstance(member, dict) for member in members):
        raise CoopStoryStateError('INVALID_MEMBERS', '队伍成员列表无效')
    if any(set(member) != COOP_STORY_PUBLIC_MEMBER_FIELDS for member in members):
        raise CoopStoryStateError('INVALID_MEMBER_FIELDS', '队伍成员只能包含公开字段')
    if any(
        isinstance(member.get('seat'), bool)
        or not isinstance(member.get('seat'), int)
        or isinstance(member.get('user_id'), bool)
        or not isinstance(member.get('user_id'), int)
        for member in members
    ):
        raise CoopStoryStateError('INVALID_SEAT_LAYOUT', '队伍席位或成员账号编号无效')
    leader_seat = party.get('leader_seat')
    if isinstance(leader_seat, bool) or not isinstance(leader_seat, int):
        raise CoopStoryStateError('INVALID_LEADER_SEAT', '队长席位无效')
    max_players = party.get('max_players')
    if isinstance(max_players, bool) or not isinstance(max_players, int):
        raise CoopStoryStateError('INVALID_MEMBER_COUNT', '队伍人数上限无效')
    seats = [member['seat'] for member in members]
    user_ids = [member['user_id'] for member in members]
    expected_seats = list(range(len(members)))
    if seats != expected_seats or set(players) != {str(seat) for seat in expected_seats}:
        raise CoopStoryStateError('INVALID_SEAT_LAYOUT', '队伍席位与玩家状态不一致')
    if any(user_id <= 0 for user_id in user_ids) or len(set(user_ids)) != len(user_ids):
        raise CoopStoryStateError('DUPLICATE_MEMBER', '队伍成员账号编号无效或重复')
    for member in members:
        username = member['username']
        display_name = member['display_name']
        if (
            not isinstance(username, str)
            or username != username.strip()
            or not username
            or len(username) > 64
        ):
            raise CoopStoryStateError('INVALID_MEMBER_USERNAME', '成员账号名称无效')
        if (
            not isinstance(display_name, str)
            or display_name != display_name.strip()
            or not display_name
            or len(display_name) > 64
        ):
            raise CoopStoryStateError('INVALID_MEMBER_DISPLAY_NAME', '成员显示名称无效')
        if member['membership_status'] != 'active':
            raise CoopStoryStateError('INVALID_MEMBERSHIP_STATUS', '运行中的队伍成员必须是激活状态')
    if any(not isinstance(players[str(seat)], dict) for seat in expected_seats):
        raise CoopStoryStateError('INVALID_PLAYER_STATE', '玩家状态无效')
    if (
        any(isinstance(seat, bool) or not isinstance(seat, int) for seat in combat_ready_seats)
        or combat_ready_seats != sorted(set(combat_ready_seats))
        or any(seat not in expected_seats for seat in combat_ready_seats)
    ):
        raise CoopStoryStateError('INVALID_COMBAT_READY_STATE', '战斗准备席位无效')
    combat_ready_round = coordination.get('combat_ready_round')
    if combat_ready_round is not None and (
        isinstance(combat_ready_round, bool)
        or not isinstance(combat_ready_round, int)
        or combat_ready_round <= 0
    ):
        raise CoopStoryStateError('INVALID_COMBAT_READY_STATE', '战斗准备回合无效')
    if leader_seat not in expected_seats:
        raise CoopStoryStateError('INVALID_LEADER_SEAT', '队长席位无效')
    for member in members:
        expected_role = 'leader' if member['seat'] == leader_seat else 'member'
        if member['party_role'] != expected_role:
            raise CoopStoryStateError('INVALID_PARTY_ROLE', '队伍成员角色与队长席位不一致')
    if str(party.get('mode') or '') != mode:
        raise CoopStoryStateError('STORY_MODE_MISMATCH', '队伍模式与故事状态模式不匹配')
    if mode == 'solo' and (len(members) != 1 or max_players != 1):
        raise CoopStoryStateError('INVALID_MEMBER_COUNT', '单人 v10 状态必须只有一个成员')
    if mode == 'coop':
        if not COOP_STORY_MIN_PLAYERS <= len(members) <= max_players <= COOP_STORY_MAX_PLAYERS:
            raise CoopStoryStateError('INVALID_MEMBER_COUNT', '多人 v10 状态的队伍人数无效')
    return True


def story_seat_for_user(state, user_id):
    """Resolve a server-authenticated account to its stable party seat."""

    validate_story_state_v10(state)
    target = _positive_int(user_id, code='INVALID_MEMBER_USER_ID', label='成员账号编号')
    for member in state['party']['members']:
        if int(member['user_id']) == target:
            return int(member['seat'])
    return None
