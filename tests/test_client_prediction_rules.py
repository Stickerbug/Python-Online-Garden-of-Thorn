import json
import pathlib
import re
import shutil
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')


def source_between(source, start, end):
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


class ClientPredictionRuleTests(unittest.TestCase):
    def test_targeted_equipment_prediction_uses_effect_target_and_runtime_state(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node is required for the client prediction behavior test')
        helpers = source_between(
            GAME_JS,
            'function predictionEquipmentRuntimeActive(',
            'function simulateNoCounterAttackHits(',
        )
        script = f'''
let gameState = {{}};
function normalizePlayerId(value) {{
    if (value == null || value === '') return null;
    const parsed = Number(value);
    return Number.isInteger(parsed) ? parsed : null;
}}
function getPredictionPlayerRefs() {{
    return [gameState.you, gameState.teammate, gameState.opponent, gameState.opponent2]
        .filter(Boolean);
}}
function getCardDef() {{ return {{}}; }}
function getEffectiveCardFlagSets(card, cardDef) {{
    return {{ effective: new Set([...(card.flags || []), ...(cardDef.flags || [])]) }};
}}
{helpers}

const plank = {{
    card_instance: {{ def_id: 'jungle:plank', instance_id: 'plank-1' }},
    effect_target: 1,
    custom_vars: {{}},
}};
gameState = {{
    you: {{ player_id: 0, equipment: [plank] }},
    opponent: {{ player_id: 1, equipment: [] }},
}};
const redirected = {{
    owner: predictionPlayerHasEquipment(gameState.you, 'Plank', 'jungle:plank'),
    target: predictionPlayerHasEquipment(gameState.opponent, 'Plank', 'jungle:plank'),
}};

delete plank.effect_target;
const legacyOwner = predictionPlayerHasEquipment(gameState.you, 'Plank', 'jungle:plank');
plank.effect_target = 1;
plank.custom_vars.sewers_sealed = 1;
const sealedTarget = predictionPlayerHasEquipment(gameState.opponent, 'Plank', 'jungle:plank');
delete plank.custom_vars.sewers_sealed;
plank.custom_vars._sewers_sealed_suspended = 1;
const suspendedTarget = predictionPlayerHasEquipment(gameState.opponent, 'Plank', 'jungle:plank');

const corruption = {{
    card_instance: {{ def_id: 'vanilla:corruption', instance_id: 'corruption-1' }},
    corruption_active: true,
    custom_vars: {{ sewers_sealed: 1 }},
}};
const dizzy = {{
    card_instance: {{ def_id: 'desert_cards_addition:dizzy', instance_id: 'dizzy-1' }},
    effect_target: 0,
    custom_vars: {{ sewers_sealed: 1 }},
}};
const cutter = {{
    card_instance: {{ def_id: 'factory:cutter', instance_id: 'cutter-1' }},
    effect_target: 0,
    custom_vars: {{ sewers_sealed: 1 }},
}};
gameState = {{
    you: {{ player_id: 0, equipment: [corruption, dizzy, cutter] }},
    opponent: {{ player_id: 1, equipment: [] }},
}};
const sealedCounts = [
    countActiveCorruptionEquipment(),
    countDizzyEquipmentForPrediction(gameState.you),
    countCutterEquipmentForPrediction(gameState.you),
];
[corruption, dizzy, cutter].forEach(eq => {{ eq.custom_vars = {{}}; }});
const activeCounts = [
    countActiveCorruptionEquipment(),
    countDizzyEquipmentForPrediction(gameState.you),
    countCutterEquipmentForPrediction(gameState.you),
];

process.stdout.write(JSON.stringify({{
    redirected,
    legacyOwner,
    sealedTarget,
    suspendedTarget,
    sealedCounts,
    activeCounts,
}}));
'''
        completed = subprocess.run(
            [node, '-e', script],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding='utf-8',
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                'redirected': {'owner': False, 'target': True},
                'legacyOwner': True,
                'sealedTarget': False,
                'suspendedTarget': False,
                'sealedCounts': [0, 0, 0],
                'activeCounts': [1, 1, 1],
            },
        )

    def test_damage_prediction_matches_public_defense_chain(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node is required for the client prediction behavior test')
        helpers = source_between(
            GAME_JS,
            'function predictionEquipmentRuntimeActive(',
            'function formatPredictionPart(',
        )
        script = f'''
let gameState = {{ mode: '1v1', players: [] }};
const definitions = new Map([
    ['test:attack', {{ id: 'test:attack', card_type: 'thorn', cost_e: 2, flags: [] }}],
    ['test:nonstack', {{ id: 'test:nonstack', flags: ['non_stackable'] }}],
]);
function normalizePlayerId(value) {{
    if (value == null || value === '') return null;
    const parsed = Number(value);
    return Number.isInteger(parsed) ? parsed : null;
}}
function getPredictionPlayerRefs() {{ return gameState.players || []; }}
function getCardDef(id) {{ return definitions.get(id) || {{ id, flags: [] }}; }}
function getEffectiveCardFlagSets(card, cardDef) {{
    return {{ effective: new Set([...(card.flags || []), ...(cardDef.flags || [])]) }};
}}
function readPlayerHealthValue(playerState, keys, fallback = 0) {{
    for (const key of keys) {{
        const value = Number(playerState && playerState[key]);
        if (Number.isFinite(value)) return value;
    }}
    return fallback;
}}
function getCardDisplayCosts(card, cardDef) {{
    return {{ totalE: Number(card.cost_e ?? cardDef.cost_e ?? 0), totalM: 0 }};
}}
function cardHasEffectiveFlagForPrediction(card, cardDef, flag) {{
    return getEffectiveCardFlagSets(card, cardDef).effective.has(flag);
}}
function cardMatchesAnyLocalId(card, cardDef, ids) {{
    const candidates = [card && card.def_id, cardDef && cardDef.id]
        .map(value => String(value || '').toLowerCase());
    return ids.some(id => candidates.includes(String(id || '').toLowerCase()));
}}
function getActualAttackDamageHits() {{ return []; }}
{helpers}

const player = (id, extra = {{}}) => ({{
    player_id: id,
    health: 100,
    max_health: 100,
    magic: 0,
    armor: 0,
    equipment: [],
    hand: [],
    custom_statuses: {{}},
    custom_vars: {{}},
    ...extra,
}});
let equipmentSerial = 0;
const equipment = (defId, ownerId, effectTarget, extra = {{}}) => ({{
    card_instance: {{ def_id: defId, instance_id: `eq-${{++equipmentSerial}}` }},
    owner: ownerId,
    effect_target: effectTarget,
    custom_vars: {{}},
    ...extra,
}});
const attackCard = cost => ({{ def_id: 'test:attack', card_type: 'thorn', cost_e: cost }});
const runAttack = (rawHits, attacker, target, card = attackCard(2)) => {{
    gameState.players = gameState.players.length ? gameState.players : [attacker, target];
    const runtime = createPredictionDamageRuntime(attacker, target);
    const hits = simulatePredictionAttackRawHits(rawHits, card, attacker, target, runtime);
    return {{ hits: Array.from(hits), runtime }};
}};

const orderAttacker = player(0, {{ weakness: 0 }});
const orderTarget = player(1);
orderAttacker.equipment.push(
    equipment('vanilla:corruption', 0, 0, {{ corruption_active: true }}),
    equipment('vanilla:corruption', 0, 0, {{ corruption_active: true }}),
    equipment('desert_cards_addition:dizzy', 0, 0),
);
gameState = {{ mode: '1v1', players: [orderAttacker, orderTarget] }};
const roundedOrder = runAttack([2], orderAttacker, orderTarget).hits;

const plankAttacker = player(0, {{ weakness: 1 }});
const plankTarget = player(1);
plankAttacker.equipment.push(equipment('jungle:plank', 0, 1));
gameState = {{ mode: '1v1', players: [plankAttacker, plankTarget] }};
const plankZero = runAttack([10], plankAttacker, plankTarget, attackCard(1)).hits;

const cottonAttacker = player(0);
const cottonTarget = player(1, {{ magic: 2 }});
cottonAttacker.equipment.push(equipment('jungle:magic_cotton', 0, 1));
gameState = {{ mode: '1v1', players: [cottonAttacker, cottonTarget] }};
const cotton = runAttack([10], cottonAttacker, cottonTarget);

const scalesAttacker = player(0);
const scalesTarget = player(1, {{ turn_damage_taken: 9 }});
scalesTarget.equipment.push(equipment('jurassic:scales', 1, 1));
gameState = {{ mode: '1v1', players: [scalesAttacker, scalesTarget] }};
const scales = runAttack([6, 6], scalesAttacker, scalesTarget).hits;

const amberAttacker = player(0);
const amberCard = {{ def_id: 'jurassic:amber', instance_id: 'amber-1', power_value: 0 }};
const amberTarget = player(1, {{
    revealed_tag_cards: [amberCard],
}});
gameState = {{ mode: '1v1', players: [amberAttacker, amberTarget] }};
const amber = runAttack([10, 10, 10], amberAttacker, amberTarget).hits;
const dedupedAmberCount = getPredictionVisibleHandCards({{
    hand: [amberCard],
    revealed_tag_cards: [{{ ...amberCard }}],
}}).length;

const relicAttacker = player(0);
const relicOtherEnemy = player(1);
const relicTarget = player(2);
const relicMate = player(3);
relicTarget.equipment.push(equipment('jungle:relic', 2, 2));
gameState = {{ mode: '2v2', players: [relicAttacker, relicOtherEnemy, relicTarget, relicMate] }};
const relic = runAttack([10], relicAttacker, relicTarget);

const rodAttacker = player(0);
const rodOtherEnemy = player(1);
const rodTarget = player(2);
const rodOwner = player(3, {{ magic: 1 }});
rodOwner.equipment.push(equipment('void:magic_copper_rod', 3, 2));
gameState = {{ mode: '2v2', players: [rodAttacker, rodOtherEnemy, rodTarget, rodOwner] }};
const rod = runAttack([7, 7], rodAttacker, rodTarget);

const maskAttacker = player(0);
const maskTarget = player(1);
maskTarget.equipment.push(equipment('bio:mask', 1, 1));
gameState = {{ mode: '1v1', players: [maskAttacker, maskTarget] }};
const directRuntime = createPredictionDamageRuntime(maskAttacker, maskTarget);
const directMask = simulatePredictionDirectDamageHit(
    directRuntime,
    0,
    ensurePredictionDamagePlayer(directRuntime, maskTarget),
    9,
    {{ damageType: 'physical', damageTag: 'direct' }},
);
const attackMask = runAttack([9], maskAttacker, maskTarget).hits;

const statusOwner = player(0);
const statusTarget = player(1);
statusOwner.equipment.push(equipment('desert_cards_addition:dizzy', 0, 0));
gameState = {{ mode: '1v1', players: [statusOwner, statusTarget] }};
const statusRuntime = createPredictionDamageRuntime(statusOwner, statusTarget);
const fractureWithDizzy = simulatePredictionDirectDamageHit(
    statusRuntime,
    0,
    ensurePredictionDamagePlayer(statusRuntime, statusOwner),
    4,
    {{ damageType: 'magic', damageTag: 'gtn:fracture' }},
);

const comboAttacker = player(0);
const comboTarget = player(1, {{ magic: 1 }});
comboTarget.equipment.push(
    equipment('jungle:magic_cotton', 1, 1),
    equipment('void:magic_copper_rod', 1, 1),
);
gameState = {{ mode: '1v1', players: [comboAttacker, comboTarget] }};
const combo = runAttack([6], comboAttacker, comboTarget);

const paidAttacker = player(0, {{ magic: 1 }});
const paidTarget = player(1);
paidAttacker.equipment.push(equipment('void:magic_copper_rod', 0, 1));
gameState = {{ mode: '1v1', players: [paidAttacker, paidTarget] }};
const paidRuntime = createPredictionDamageRuntime(paidAttacker, paidTarget, {{ paidMagic: 1 }});
const paidCost = Array.from(simulatePredictionAttackRawHits(
    [7], attackCard(2), paidAttacker, paidTarget, paidRuntime,
));

const nonStackOwner = player(0);
const nonStackTarget = player(1);
nonStackOwner.equipment.push(
    equipment('test:nonstack', 0, 0, {{ custom_vars: {{ sewers_sealed: 1, non_stack_equipped_order: 1 }} }}),
    equipment('test:nonstack', 0, 0, {{ custom_vars: {{ non_stack_equipped_order: 2 }} }}),
);
gameState = {{ mode: '1v1', players: [nonStackOwner, nonStackTarget] }};
const nonStackActive = getPredictionActiveEquipmentEntries()
    .filter(entry => predictionEquipmentMatches(entry.eq, 'test:nonstack')).length;

const resourceDelta = (runtime, playerId) => (runtime.resourceDeltas.get(playerId) || {{}}).magic || 0;
process.stdout.write(JSON.stringify({{
    roundedOrder,
    plankZero,
    cotton: {{ hits: cotton.hits, targetMagic: resourceDelta(cotton.runtime, 1) }},
    scales,
    amber,
    dedupedAmberCount,
    relic: {{
        hits: relic.hits,
        mateHits: relic.runtime.redirectedDamage.get(3),
    }},
    rod: {{ hits: rod.hits, ownerMagic: resourceDelta(rod.runtime, 3) }},
    mask: {{ direct: directMask, attack: attackMask }},
    fractureWithDizzy,
    combo: {{ hits: combo.hits, targetMagic: resourceDelta(combo.runtime, 1) }},
    paidCost,
    nonStackActive,
}}));
'''
        completed = subprocess.run(
            [node, '-e', script],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding='utf-8',
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                'roundedOrder': [8],
                'plankZero': [0],
                'cotton': {'hits': [2], 'targetMagic': -2},
                'scales': [6, 3],
                'amber': [8, 8, 10],
                'dedupedAmberCount': 1,
                'relic': {'hits': [3], 'mateHits': [6]},
                'rod': {'hits': [0, 7], 'ownerMagic': -1},
                'mask': {'direct': 0, 'attack': [9]},
                'fractureWithDizzy': 4,
                'combo': {'hits': [2], 'targetMagic': -1},
                'paidCost': [7],
                'nonStackActive': 0,
            },
        )

    def test_prediction_html_keeps_zero_damage_resource_cost_and_other_recipient(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node is required for the client prediction behavior test')
        formatters = source_between(
            GAME_JS,
            'function formatPredictionPart(',
            'function pushPositiveValue(',
        )
        renderer = source_between(
            GAME_JS,
            'function getCardPlayEffectPredictionHtml(',
            'function normalizePredictionHits(',
        )
        script = f'''
let currentLang = 'en';
const UI = {{ prediction_target: 'Target', prediction_self: 'Self' }};
function normalizePlayerId(value) {{
    if (value == null || value === '') return null;
    const parsed = Number(value);
    return Number.isInteger(parsed) ? parsed : null;
}}
function escapeHtml(value) {{
    return String(value).replace(/[&<>"']/g, ch => ({{
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }})[ch]);
}}
function formatDamageHits(values) {{
    const list = values.map(value => Math.max(0, Math.ceil(Number(value || 0))));
    return list.length === 1 ? `${{list[0]}}D` : list.map(value => `${{value}}D`).join(' + ');
}}
function lt(texts, fallback = '') {{ return texts[currentLang] || texts.en || texts.zh || fallback; }}
function getPlayerNameById() {{ return '<P4>'; }}
{formatters}
const prediction = {{
    target: createPredictionRecipient(1),
    self: createPredictionRecipient(0),
    others: [],
}};
prediction.target.damageHits.push(0);
applyPredictionDamageRuntime(prediction, {{
    redirectedDamage: new Map([[3, [6]]]),
    resourceDeltas: new Map([[0, {{ magic: -2 }}], [3, {{ magic: -1 }}]]),
    mitigations: [{{
        playerId: 1,
        kind: 'relic_transfer',
        prevented: 7,
        transferred: 6,
        toPlayerId: 3,
    }}],
}}, {{ player_id: 0 }}, {{ player_id: 1 }});
function shouldShowCardPlayEffectPrediction() {{ return true; }}
function getCardPlayEffectPredictionParts() {{ return prediction; }}
{renderer}
process.stdout.write(getCardPlayEffectPredictionHtml({{ def_id: 'test', instance_id: 'card-1' }}));
'''
        completed = subprocess.run(
            [node, '-e', script],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding='utf-8',
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        html = completed.stdout
        self.assertIn('0D', html)
        self.assertIn('-2M', html)
        self.assertIn('-1M', html)
        self.assertIn('card-prediction-part magic', html)
        self.assertIn('&lt;P4&gt;', html)
        self.assertIn('Relic→&lt;P4&gt; 6D', html)
        self.assertNotIn('<P4>', html)

    def test_prediction_runtime_reserves_the_played_cards_magic_cost(self):
        section = source_between(
            GAME_JS,
            'function getCardPlayEffectPredictionParts(',
            'function shouldShowCardPlayEffectPrediction(',
        )
        costs_index = section.index('const cardCosts = getCardDisplayCosts(')
        runtime_index = section.index(
            'createPredictionDamageRuntime(attackerState, targetState, { paidMagic: cardCosts.totalM })'
        )
        simulation_index = section.index('simulateNoCounterAttackHits(')
        self.assertLess(costs_index, runtime_index)
        self.assertLess(runtime_index, simulation_index)

    def test_direct_damage_source_tags_are_normalized_before_prediction(self):
        section = source_between(
            GAME_JS,
            'function getPredictionDirectDamageTag(',
            'function appendTargetDamagePrediction(',
        )
        for tag in ('gtn:poison', 'gtn:fire', 'gtn:fracture', 'gtn:bleed', 'gtn:battery'):
            self.assertIn(tag, section)
        self.assertIn('getPredictionDirectDamageType', section)

    def test_toxic_prediction_uses_the_damage_target(self):
        section = source_between(
            GAME_JS,
            'function getCardPlayEffectPredictionParts(',
            'function shouldShowCardPlayEffectPrediction(',
        )
        toxic_block = re.search(
            r'const targetImmune = .*?result\.target\.poison \+= toxic \* positiveHits;',
            section,
            re.DOTALL,
        )
        self.assertIsNotNone(toxic_block)
        self.assertIn('targetState.toxic', toxic_block.group(0))
        self.assertNotIn('attackerState.toxic', toxic_block.group(0))

    def test_server_response_poison_replaces_local_estimate(self):
        section = source_between(
            GAME_JS,
            'function getResponseBaseEffectPrediction(',
            'function appendResponseEffectToken(',
        )
        self.assertIn('prediction.target.poison = Math.max(', section)
        self.assertNotIn('prediction.target.poison +=', section)

    def test_only_a_real_nullifier_cancels_bloom_effect_prediction(self):
        section = source_between(
            GAME_JS,
            'function counterCardCancelsResponseCard(',
            'function getResponseCounterStatusReduction(',
        )
        self.assertIn("counterId === 'MagicBubble'", section)
        self.assertIn("counterId === 'vanilla:magicbubble'", section)
        self.assertNotIn('counterDef.response_trigger === responseDef.card_type', section)

    def test_fission_total_is_not_capped_as_one_damage_call(self):
        self.assertIn(
            'const MAX_CLIENT_DAMAGE_SEGMENTS = MAX_CLIENT_CARD_LAYER * MAX_CLIENT_DAMAGE_HITS;',
            GAME_JS,
        )
        section = source_between(
            GAME_JS,
            'function getActualAttackDamageHits(',
            'function getActualAttackDamageText(',
        )
        self.assertIn('const hitsPerFission = clampClientDamageHits(', section)
        self.assertIn('const totalHits = clampClientDamageSegments(hitsPerFission * fission);', section)

    def test_multi_hit_visuals_and_audio_share_the_float_timeline(self):
        section = source_between(
            GAME_JS,
            'function showStateDeltas(',
            'function clearScheduledGameOver(',
        )
        timeline_call = section.index('const scheduledEvents = showCombatFloatSequence(')
        effects_call = section.index('scheduleCombatEventEffects(', timeline_call)
        bar_call = section.index('animateBarEventSequence(', effects_call)
        self.assertLess(timeline_call, effects_call)
        self.assertLess(effects_call, bar_call)
        self.assertNotIn('triggerCombatImpact(', section[:timeline_call])
        helper = source_between(
            GAME_JS,
            'function scheduleCombatEventEffects(',
            'function scheduleSkinDamageMoods(',
        )
        self.assertIn('triggerCombatImpact(selector, event.impactKind, delay)', helper)
        self.assertIn('triggerCombatPulse(selector, event.pulseKind, delay)', helper)


if __name__ == '__main__':
    unittest.main()
