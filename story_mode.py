import hashlib
import random

from story_content import initial_story_player


STORY_SCHEMA_VERSION = 2
STORY_CONTENT_VERSION = 'story-alpha-3'
STORY_FLOOR_COUNT = 16

STORY_STAGES = (
    {'stage': 1, 'biomes': ('garden', 'desert', 'ocean')},
    {'stage': 2, 'biomes': ('jungle', 'arctic', 'bio')},
    {'stage': 3, 'biomes': ('factory', 'sewers', 'jurassic')},
    {'stage': 4, 'biomes': ('hel', 'void'), 'hidden': True},
)

_ROOM_WEIGHTS = (
    ('shop', 1),
    ('rest', 2),
    ('elite', 3),
    ('event', 3),
    ('combat', 6),
)


def _seed_int(seed, namespace=''):
    digest = hashlib.sha256(f'{seed}:{namespace}'.encode('utf-8')).digest()
    return int.from_bytes(digest[:16], 'big')


def _weighted_choice(rng, values):
    total = sum(weight for _, weight in values)
    pick = rng.uniform(0, total)
    cursor = 0
    for value, weight in values:
        cursor += weight
        if pick <= cursor:
            return value
    return values[-1][0]


def _floor_widths(rng):
    widths = [1]
    for floor in range(2, STORY_FLOOR_COUNT):
        previous = widths[-1]
        minimum = max(2, previous - 2)
        maximum = min(5, previous + 2, previous * 2)
        if floor == 2:
            minimum = maximum = 2
        elif floor == STORY_FLOOR_COUNT - 1:
            maximum = min(maximum, 3)
        choices = list(range(minimum, maximum + 1))
        widths.append(rng.choice(choices))
    widths.append(1)
    return widths


def _node_x(index, width):
    return round((index + 1) / (width + 1), 6)


def _random_partition(total, parts, rng, max_size=None):
    """Split total ordered items into non-empty contiguous groups."""
    sizes = [1] * parts
    for _ in range(total - parts):
        candidates = [
            index for index, size in enumerate(sizes)
            if max_size is None or size < max_size
        ]
        sizes[rng.choice(candidates)] += 1
    return sizes


def _would_cross(candidate, edges, previous_order, next_order):
    source_index = previous_order[candidate[0]]
    target_index = next_order[candidate[1]]
    return any(
        (source_index - previous_order[source_id])
        * (target_index - next_order[target_id]) < 0
        for source_id, target_id in edges
    )


def _connect_floors(rng, previous_nodes, next_nodes):
    previous_order = {node['id']: index for index, node in enumerate(previous_nodes)}
    next_order = {node['id']: index for index, node in enumerate(next_nodes)}
    outgoing = {node['id']: set() for node in previous_nodes}
    edges = set()

    # Partition each ordered floor into contiguous groups. This covers every
    # node while guaranteeing that the base routes cannot cross.
    if len(next_nodes) >= len(previous_nodes):
        group_sizes = _random_partition(
            len(next_nodes),
            len(previous_nodes),
            rng,
            max_size=2,
        )
        target_cursor = 0
        for parent, group_size in zip(previous_nodes, group_sizes):
            for target in next_nodes[target_cursor:target_cursor + group_size]:
                edge = (parent['id'], target['id'])
                edges.add(edge)
                outgoing[parent['id']].add(target['id'])
            target_cursor += group_size
    else:
        group_sizes = _random_partition(len(previous_nodes), len(next_nodes), rng)
        parent_cursor = 0
        for target, group_size in zip(next_nodes, group_sizes):
            for parent in previous_nodes[parent_cursor:parent_cursor + group_size]:
                edge = (parent['id'], target['id'])
                edges.add(edge)
                outgoing[parent['id']].add(target['id'])
            parent_cursor += group_size

    # Optional alternate routes may share a node, but may not invert the
    # left-to-right ordering of any existing connection.
    for parent in previous_nodes:
        if len(outgoing[parent['id']]) >= 2 or rng.random() >= 0.42:
            continue
        candidates = [
            target for target in next_nodes
            if target['id'] not in outgoing[parent['id']]
            and not _would_cross(
                (parent['id'], target['id']),
                edges,
                previous_order,
                next_order,
            )
        ]
        if not candidates:
            continue
        target = min(candidates, key=lambda node: (abs(node['x'] - parent['x']), rng.random()))
        edge = (parent['id'], target['id'])
        edges.add(edge)
        outgoing[parent['id']].add(target['id'])

    return [
        {'from': parent_id, 'to': target_id}
        for parent_id, target_id in sorted(
            edges,
            key=lambda edge: (previous_order[edge[0]], next_order[edge[1]]),
        )
    ]


def generate_story_map(seed, stage=1, biome='garden'):
    stage = int(stage)
    biome = str(biome or 'garden')
    rng = random.Random(_seed_int(seed, f'map:{stage}:{biome}'))
    widths = _floor_widths(rng)
    floors = []

    for floor, width in enumerate(widths, start=1):
        if floor == 1:
            room_types = ['blessing'] * width
        elif floor == 2:
            room_types = ['combat'] * width
        elif floor == 9:
            room_types = ['chest'] * width
        elif floor == 15:
            room_types = ['rest'] * width
        elif floor == 16:
            room_types = ['boss'] * width
        else:
            choices = tuple(item for item in _ROOM_WEIGHTS if floor > 6 or item[0] != 'elite')
            room_types = [_weighted_choice(rng, choices) for _ in range(width)]

        nodes = []
        for index, room_type in enumerate(room_types):
            nodes.append({
                'id': f's{stage}-f{floor:02d}-n{index}',
                'floor': floor,
                'index': index,
                'x': _node_x(index, width),
                'type': room_type,
                'status': 'locked',
            })
        floors.append({'floor': floor, 'width': width, 'nodes': nodes})

    edges = []
    for index in range(len(floors) - 1):
        edges.extend(_connect_floors(rng, floors[index]['nodes'], floors[index + 1]['nodes']))

    floors[0]['nodes'][0]['status'] = 'current'
    return {
        'stage': stage,
        'biome': biome,
        'floor_count': STORY_FLOOR_COUNT,
        'floors': floors,
        'edges': edges,
    }


def build_initial_story_state(seed):
    story_map = generate_story_map(seed, stage=1, biome='garden')
    first_node = story_map['floors'][0]['nodes'][0]
    return {
        'schema_version': STORY_SCHEMA_VERSION,
        'content_version': STORY_CONTENT_VERSION,
        'phase': 'blessing',
        'stage': 1,
        'biome': 'garden',
        'current_floor': 1,
        'current_node_id': first_node['id'],
        'available_stages': list(STORY_STAGES),
        'map': story_map,
        'player': initial_story_player(),
        'combat': None,
        'room': None,
        'reward': None,
        'rng_counter': 0,
        'normal_battles': 0,
        'completed': False,
        'last_events': [],
        'flags': {},
    }
