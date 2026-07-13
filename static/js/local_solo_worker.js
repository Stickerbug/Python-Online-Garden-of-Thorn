/* Local single-player runtime for solo training and tutorial.
 * This worker intentionally mirrors the server event shape so the existing UI
 * can render local games without branching through the whole frontend.
 */

const HAND_LIMIT = 7;
const DRAW_PER_TURN = 3;
const ELIXIR_RECOVERY = 5;
const BASE_MAX_HEALTH = 100;
const BASE_MAX_ELIXIR = 10;
const BASE_MAX_MAGIC = 10;
const INITIAL_HEALTH = 100;
const INITIAL_ELIXIR = 5;
const INITIAL_MAGIC = 0;
const INITIAL_HAND_SIZE = 5;
const FIRST_PLAYER_HAND_SIZE = 4;
const DECK_SIZE = 15;
const ERROR_CARD_ID = 'Error';
const MOD_RUNTIME_ERROR_MESSAGE = '模组执行出现了一个意外错误。请联系管理员。';
const CORRUPTION_DAMAGE_MULTIPLIER = 1.5;
const LATE_ROUND_FIRE_START = 10;
const CARD_FLAG_ALIASES = {
    'tag_troll_cards:exile': 'exile',
    'troll_cards:exile': 'exile',
    'tag_troll_cards_exile': 'exile',
    'troll_cards_exile': 'exile',
    'tag_thorn_cards_supplement_1:sticky': 'sticky',
    'thorn_cards_supplement_1:sticky': 'sticky',
    'tag_thorn_cards_supplement_1_sticky': 'sticky',
    'thorn_cards_supplement_1_sticky': 'sticky',
    'temp_magic_heavy': 'temp_magic_heavy',
    'tag_temp_magic_heavy': 'temp_magic_heavy',
    'void:temp_magic_heavy': 'temp_magic_heavy',
    'tag_void:temp_magic_heavy': 'temp_magic_heavy',
    'tag_void_temp_magic_heavy': 'temp_magic_heavy',
    '暂时魔力沉重': 'temp_magic_heavy',
    'floating': 'floating',
    'tag_floating': 'floating',
    'void:floating': 'floating',
    'tag_void:floating': 'floating',
    'tag_void_floating': 'floating',
    '漂浮': 'floating',
};
const VANILLA_FLAGS = new Set([
    'precision', 'exile', 'non_stackable', 'indestructible', 'sprout', 'symbiosis',
    'attract', 'void', 'self_only', 'uncancellable', 'infinite_exclude', 'rebound',
    'copy', 'unique', 'swift', 'stealth', 'revealed', 'temp_magic_heavy', 'floating',
    'sublime',
]);

class ModLoopBreak extends Error {}
class ModLoopContinue extends Error {}

const TUTORIAL_DECKS = [
    [
        'Basic', 'Rose', 'Leaf', 'Bone', 'Bubble',
        'Fission', 'Triangle', 'Sewage', 'Fusion', 'Basic',
        'Basic', 'Fire', 'Yggdrasil', 'Yucca', 'MagicBubble',
    ],
    [
        'Basic', 'Battery', 'Leaf', 'Basic', 'Bone',
        'Stinger', 'Fire', 'Disc', 'Bubble', 'Mine',
        'Basic', 'Bone', 'Mark', 'Sewage', 'MagicBubble',
    ],
];

const EVENT_EFFECT_TYPES = new Set([
    'on_owner_turn_start',
    'on_target_turn_start',
    'on_owner_turn_end',
    'on_enemy_turn_start',
    'on_any_turn_start',
    'on_damage_taken',
    'on_equipment_trigger',
    'on_equipment_destroy',
    'on_hand_owner_turn_start',
    'on_hand_owner_turn_end',
    'on_enter_hand',
    'on_discard_owner_turn_start',
    'on_deck_owner_turn_start',
    'on_card_used',
    'on_equipment_triggered',
    'on_equipment_destroyed',
    'on_resource_spent',
    'on_player_stat_changed',
    'on_fatal_set_health_exile',
    'aura_enemy_elixir_recovery',
]);

const SCRIPT_ENTRY_ALIASES = {
    play: ['onPlay', 'play', 'on_play'],
    response: ['onResponse', 'response', 'on_response'],
    owner_turn_start: ['onOwnerTurnStart', 'owner_turn_start', 'on_owner_turn_start'],
    target_turn_start: ['onTargetTurnStart', 'target_turn_start', 'on_target_turn_start'],
    owner_turn_end: ['onOwnerTurnEnd', 'owner_turn_end', 'on_owner_turn_end'],
    enemy_turn_start: ['onEnemyTurnStart', 'enemy_turn_start', 'on_enemy_turn_start'],
    any_turn_start: ['onAnyTurnStart', 'any_turn_start', 'on_any_turn_start'],
    damage_taken: ['onDamageTaken', 'damage_taken', 'on_damage_taken'],
    equipment_trigger: ['onEquipmentTrigger', 'equipment_trigger', 'on_equipment_trigger'],
    equipment_destroy: ['onEquipmentDestroy', 'equipment_destroy', 'on_equipment_destroy', 'onDestroy'],
    hand_owner_turn_start: ['onHandOwnerTurnStart', 'hand_owner_turn_start', 'on_hand_owner_turn_start'],
    hand_owner_turn_end: ['onHandOwnerTurnEnd', 'hand_owner_turn_end', 'on_hand_owner_turn_end'],
    enter_hand: ['onEnterHand', 'enter_hand', 'on_enter_hand'],
    discard_owner_turn_start: ['onDiscardOwnerTurnStart', 'discard_owner_turn_start', 'on_discard_owner_turn_start'],
    deck_owner_turn_start: ['onDeckOwnerTurnStart', 'deck_owner_turn_start', 'on_deck_owner_turn_start'],
    card_used: ['onCardUsed', 'card_used', 'on_card_used'],
    equipment_triggered: ['onEquipmentTriggered', 'equipment_triggered', 'on_equipment_triggered'],
    equipment_destroyed: ['onEquipmentDestroyed', 'equipment_destroyed', 'on_equipment_destroyed'],
    resource_spent: ['onResourceSpent', 'resource_spent', 'on_resource_spent'],
    player_stat_changed: ['onPlayerStatChanged', 'player_stat_changed', 'on_player_stat_changed'],
};

const V2_EVENT_ALIASES = {
    play: ['on_play'],
    response: ['on_response'],
    owner_turn_start: ['on_owner_turn_start', 'on_turn_start', 'on_turn_start_while_equipped'],
    target_turn_start: ['on_target_turn_start'],
    owner_turn_end: ['on_owner_turn_end', 'on_turn_end_while_equipped'],
    enemy_turn_start: ['on_enemy_turn_start'],
    any_turn_start: ['on_any_turn_start'],
    damage_taken: ['on_damage_taken'],
    equipment_trigger: ['on_equipment_trigger'],
    equipment_destroy: ['on_equipment_destroy', 'on_before_destroyed'],
    hand_owner_turn_start: ['on_hand_owner_turn_start'],
    hand_owner_turn_end: ['on_hand_owner_turn_end'],
    enter_hand: ['on_enter_hand'],
    discard_owner_turn_start: ['on_discard_owner_turn_start', 'on_discard'],
    deck_owner_turn_start: ['on_deck_owner_turn_start'],
    card_used: ['on_card_used', 'after_play_card'],
    equipment_triggered: ['on_equipment_triggered'],
    equipment_destroyed: ['on_equipment_destroyed'],
    resource_spent: ['on_resource_spent'],
    player_stat_changed: ['on_player_stat_changed'],
};

const TRACKED_PLAYER_STATS = [
    'health', 'max_health', 'elixir', 'max_elixir', 'magic', 'max_magic',
    'armor', 'dodge', 'poison', 'fire', 'vulnerable', 'toxic',
    'equipment_protection', 'hand_limit',
];

let cardDefs = {};
let openingEventMagicPool = [];
let engine = null;
let nextInstanceId = 900000;

function emit(type, data = {}) {
    postMessage({ type, data });
}

function fallback(reason) {
    emit('fallback_required', { reason: String(reason || 'local runtime unsupported') });
}

function randintId() {
    nextInstanceId += 1;
    return nextInstanceId;
}

function deepClone(value) {
    return value == null ? value : JSON.parse(JSON.stringify(value));
}

function shuffle(list) {
    for (let i = list.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [list[i], list[j]] = [list[j], list[i]];
    }
}

function toInt(value, fallbackValue = 0) {
    const n = Number(value);
    if (!Number.isFinite(n)) return fallbackValue;
    return Math.trunc(n);
}

function escapeRegExp(value) {
    return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function normalizeCardFlag(flag) {
    const text = String(flag == null ? '' : flag).trim();
    if (!text) return '';
    const lower = text.toLowerCase();
    if (CARD_FLAG_ALIASES[lower]) return CARD_FLAG_ALIASES[lower];
    if (lower.startsWith('tag_')) {
        const local = lower.slice(4).split(':').pop().split('_').pop();
        if (VANILLA_FLAGS.has(local)) return local;
    }
    if (lower.includes(':')) {
        const local = lower.split(':').pop();
        if (VANILLA_FLAGS.has(local)) return local;
    }
    if (VANILLA_FLAGS.has(lower)) return lower;
    return text;
}

function normalizeCardFlags(flags) {
    if (!flags) return [];
    if (flags instanceof Set) return Array.from(flags).map(normalizeCardFlag).filter(Boolean);
    if (Array.isArray(flags)) return flags.map(normalizeCardFlag).filter(Boolean);
    if (typeof flags === 'string') return flags.split(/[,\s]+/).map(normalizeCardFlag).filter(Boolean);
    if (typeof flags === 'object') return Object.entries(flags)
        .filter(([_, enabled]) => !!enabled)
        .map(([flag]) => normalizeCardFlag(flag))
        .filter(Boolean);
    return [];
}

function cardDef(defId) {
    return cardDefs[defId] || null;
}

function cardName(defId) {
    const def = cardDef(defId);
    return def ? (def.name_cn || def.name_en || def.id) : defId;
}

function cardIsSublime(card) {
    if (!card) return false;
    const flags = card.flags instanceof Set ? card.flags : new Set(normalizeCardFlags(card.flags || []));
    return flags.has('sublime') || flags.has('vanilla:sublime') || flags.has('tag_sublime') || flags.has('exalted');
}

function cardSelectableByAction(card) {
    return !!card && !cardIsSublime(card);
}

function parseJsonish(value) {
    if (typeof value !== 'string') return value;
    const text = value.trim();
    if (!text || !'{["'.includes(text[0])) return value;
    try { return parseJsonish(JSON.parse(text)); } catch (_) { return value; }
}

function scriptEffectsFrom(script) {
    if (Array.isArray(script)) return script;
    if (script && Array.isArray(script.effects)) return script.effects;
    return [];
}

function v2EventsFrom(def) {
    if (!def || typeof def !== 'object') return {};
    if (def.v2_events && typeof def.v2_events === 'object') return def.v2_events;
    const resourceEvents = def.v2_resource && def.v2_resource.events;
    return resourceEvents && typeof resourceEvents === 'object' ? resourceEvents : {};
}

function v2EventNames(entry) {
    const raw = String(entry || '');
    const names = [...(V2_EVENT_ALIASES[raw] || [])];
    if (raw) names.push(raw.startsWith('on_') ? raw : `on_${raw}`);
    return [...new Set(names)];
}

function v2EventSteps(def, entry) {
    const events = v2EventsFrom(def);
    for (const name of v2EventNames(entry)) {
        const eventDef = events[name];
        if (Array.isArray(eventDef)) return eventDef;
        if (eventDef && Array.isArray(eventDef.steps)) return eventDef.steps;
        if (eventDef && Array.isArray(eventDef.effects)) return eventDef.effects;
    }
    return [];
}

function v2StepParams(step) {
    const params = step && typeof step.params === 'object' && !Array.isArray(step.params)
        ? { ...step.params }
        : {};
    Object.entries(step || {}).forEach(([key, value]) => {
        if (!['op', 'type', 'params', 'then', 'else', 'body', 'steps', 'condition'].includes(key)) {
            params[key] = value;
        }
    });
    return params;
}

function v2StepsToEffects(steps) {
    if (!Array.isArray(steps)) return [];
    return steps.map(v2StepToEffect).filter(Boolean);
}

function v2StepToEffect(step) {
    if (!step || typeof step !== 'object') return null;
    const op = step.op || step.type || '';
    const params = v2StepParams(step);
    if (op === 'if') {
        return {
            type: 'if',
            params: {
                condition: step.condition || params.condition,
                then: v2StepsToEffects(step.then || params.then || []),
                else: v2StepsToEffects(step.else || params.else || []),
            },
        };
    }
    if (op === 'repeat') {
        return {
            type: 'repeat',
            params: {
                times: params.times ?? params.count,
                body: v2StepsToEffects(step.body || step.steps || params.body || params.steps || []),
            },
        };
    }
    if (op === 'repeat_until') {
        return {
            type: 'repeat_until',
            params: {
                condition: step.condition || params.condition,
                body: v2StepsToEffects(step.body || step.steps || params.body || params.steps || []),
            },
        };
    }
    if (op === 'for_each_selected_card') {
        return {
            type: 'for_each_selected_card',
            params: {
                ...params,
                body: v2StepsToEffects(step.body || step.steps || params.body || params.steps || []),
            },
        };
    }
    if (op === 'draw_cards') return { type: 'draw', params };
    if (op === 'add_status') return { type: 'status_add_named', params: { ...params, status: params.status || params.id || params.name } };
    if (op === 'remove_status') return { type: 'status_remove_named', params: { ...params, status: params.status || params.id || params.name } };
    if (op === 'set_status') return { type: 'status_set_named', params: { ...params, status: params.status || params.id || params.name } };
    if (op === 'move_card') {
        const zone = String(params.to || params.zone || 'discard');
        const map = { hand: 'move_to_hand', deck: 'move_to_deck', discard: 'move_to_discard', exile: 'move_to_exile' };
        return { type: map[zone] || 'move_to_discard', params };
    }
    if (op === 'create_card') {
        const zone = String(params.to || params.zone || 'hand');
        const map = { hand: 'give_card_to_hand', deck: 'give_card_to_deck', discard: 'give_card_to_discard' };
        return { type: map[zone] || 'give_card_to_hand', params: { ...params, card: params.card || params.card_id || params.id } };
    }
    if (op === 'destroy_equipment') return { type: 'destroy_equipment_choice_or_first', params };
    if (op === 'log') return { type: 'log', params };
    return { type: op, params };
}

function getScriptEffects(def, entry) {
    const scripts = (def && def.scripts) || {};
    const aliases = SCRIPT_ENTRY_ALIASES[entry] || [entry];
    for (const key of aliases) {
        if (Object.prototype.hasOwnProperty.call(scripts, key)) {
            return scriptEffectsFrom(scripts[key]);
        }
    }
    const v2Steps = v2EventSteps(def, entry);
    if (v2Steps.length) return v2StepsToEffects(v2Steps);
    return [];
}

function hasScriptEntry(def, entry) {
    return getScriptEffects(def, entry).length > 0;
}

function cardEventRequiresSelfDestroy(def, entry) {
    const walk = value => {
        if (Array.isArray(value)) return value.some(walk);
        if (!value || typeof value !== 'object') return false;
        if (['destroy_self_equipment', 'destroy_current_equipment'].includes(String(value.type || value.op || ''))) return true;
        const params = value.params && typeof value.params === 'object' ? value.params : {};
        return ['steps', 'effects', 'body', 'then', 'else', 'on_cancel'].some(key => walk(value[key]) || walk(params[key]));
    };
    return walk(getScriptEffects(def, entry));
}

function playEffectsFor(card) {
    const def = card.def();
    const scriptEffects = getScriptEffects(def, 'play');
    return scriptEffects.length ? scriptEffects : ((def && def.effects) || []);
}

class LocalCard {
    constructor(entry) {
        const source = typeof entry === 'string' ? { def_id: entry } : (entry || {});
        this.def_id = source.def_id || source.id || '';
        if (this.def_id && !cardDef(this.def_id) && cardDef(ERROR_CARD_ID)) this.def_id = ERROR_CARD_ID;
        if (!this.def_id && cardDef(ERROR_CARD_ID)) this.def_id = ERROR_CARD_ID;
        this.instance_id = source.instance_id || randintId();
        this.cost_e_override = source.cost_e_override ?? null;
        this.cost_m_override = source.cost_m_override ?? null;
        this.fission_count = toInt(source.fission_count, 0);
        this.fusion_multiplier = Number(source.fusion_multiplier ?? 1) || 1;
        this.fission_level = Math.max(1, toInt(source.fission_level ?? (this.fission_count + 1), 1));
        this.fusion_level = Math.max(1, toInt(source.fusion_level ?? this.fusion_multiplier, 1));
        this.mimic_discount = toInt(source.mimic_discount, 0);
        this.fission_hit = toInt(source.fission_hit, 0);
        this.instance_flags = new Set(normalizeCardFlags(source.instance_flags || []));
        this.disabled_flags = new Set(normalizeCardFlags(source.disabled_flags || []));
        this.bonus_damage = toInt(source.bonus_damage, 0);
        this.return_to_hand_turns = toInt(source.return_to_hand_turns, 0);
        this.held_turns = toInt(source.held_turns, 0);
        this.swift_value = Math.max(0, toInt(source.swift_value, 0));
        this.magic_swift_value = Math.max(0, toInt(source.magic_swift_value, 0));
        this.power_value = Math.max(0, toInt(source.power_value, 0));
        this.temp_swift_value = Math.max(0, toInt(source.temp_swift_value, 0));
        this.temp_heavy_value = Math.max(0, toInt(source.temp_heavy_value, 0));
        this.temp_magic_heavy_value = Math.max(0, toInt(source.temp_magic_heavy_value, 0));
        this.extra_hits = Math.max(0, toInt(source.extra_hits, 0));
        this.setup_modifiers = new Set(source.setup_modifiers || []);
        if (this.def_id === 'Tomato') {
            this.power_value = Math.min(18, Math.max(0, this.power_value));
        }
        this.durability = toInt(source.durability, 0);
        this._placed_as_equipment = false;
        this._placed_as_equipment_owner = null;
    }

    def() {
        return cardDef(this.def_id) || {};
    }

    get card_type() {
        return this.def().card_type || '';
    }

    get cost_e() {
        const base = this.cost_e_override != null ? this.cost_e_override : toInt(this.def().cost_e, 0);
        return Math.max(0, base + this.temp_heavy_value - this.mimic_discount - this.swift_value - this.temp_swift_value);
    }

    get cost_m() {
        const base = this.cost_m_override != null ? this.cost_m_override : toInt(this.def().cost_m, 0);
        return Math.max(0, base + Math.max(0, toInt(this.temp_magic_heavy_value, 0)) - Math.max(0, toInt(this.magic_swift_value, 0)));
    }

    get flags() {
        const def = this.def();
        const flags = new Set(normalizeCardFlags([...(def.flags || []), ...(def.tags || [])]));
        this.instance_flags.forEach(flag => flags.add(flag));
        this.disabled_flags.forEach(flag => flags.delete(flag));
        return flags;
    }

    copy() {
        return new LocalCard(this.toDict());
    }

    toDict() {
        return {
            def_id: this.def_id,
            instance_id: this.instance_id,
            cost_e_override: this.cost_e_override,
            cost_m_override: this.cost_m_override,
            fission_count: this.fission_count,
            fusion_multiplier: this.fusion_multiplier,
            fission_level: this.fission_level,
            fusion_level: this.fusion_level,
            mimic_discount: this.mimic_discount,
            instance_flags: Array.from(this.instance_flags),
            disabled_flags: Array.from(this.disabled_flags),
            bonus_damage: this.bonus_damage,
            return_to_hand_turns: this.return_to_hand_turns,
            held_turns: this.held_turns,
            swift_value: this.swift_value,
            magic_swift_value: this.magic_swift_value,
            power_value: this.power_value,
            temp_swift_value: this.temp_swift_value,
            temp_heavy_value: this.temp_heavy_value,
            temp_magic_heavy_value: this.temp_magic_heavy_value,
            extra_hits: this.extra_hits,
            setup_modifiers: Array.from(this.setup_modifiers),
            durability: this.durability,
        };
    }
}

class LocalEquipment {
    constructor(card, owner) {
        this.card_instance = card;
        this.owner = owner;
        this.effect_target = owner;
        this.turns_equipped = 0;
        this.uses_this_turn = 0;
        this.corruption_active = false;
        this.armor = 0;
        this.custom_vars = {};
    }

    get def_id() {
        return this.card_instance.def_id;
    }

    get card_def() {
        return this.card_instance.def();
    }

    toDict() {
        return {
            card_instance: this.card_instance.toDict(),
            owner: this.owner,
            effect_target: this.effect_target,
            turns_equipped: this.turns_equipped,
            uses_this_turn: this.uses_this_turn,
            corruption_active: this.corruption_active,
            armor: this.armor,
            custom_vars: { ...(this.custom_vars || {}) },
        };
    }
}

class LocalPlayer {
    constructor(playerId) {
        this.player_id = playerId;
        this.health = INITIAL_HEALTH;
        this.max_health = BASE_MAX_HEALTH;
        this.base_max_health = BASE_MAX_HEALTH;
        this.elixir = INITIAL_ELIXIR;
        this.max_elixir = BASE_MAX_ELIXIR;
        this.magic = INITIAL_MAGIC;
        this.max_magic = BASE_MAX_MAGIC;
        this.armor = 0;
        this.poison = 0;
        this.fire = 0;
        this.vulnerable = 0;
        this.toxic = 0;
        this.triangle_stacks = 0;
        this.dodge = 0;
        this.nazar_active = false;
        this.nazar_big_hits = 0;
        this.equipment_protection = 0;
        this.magic_battery_m_this_turn = 0;
        this.coffee_first_use = true;
        this.invincible = false;
        this.invincible_until_player = null;
        this.invincible_granted_round = -1;
        this.invincible_granted_turn_marker = -1;
        this.skip_turn = 0;
        this.damage_multiplier = 1.0;
        this.bandage_active = false;
        this.bandage_death_pending = false;
        this.attack_blocked = 0;
        this.untargetable = false;
        this.sponge_active = false;
        this.shovel_active = false;
        this.attack_only = 0;
        this.enemy_draw_reduction = 0;
        this.enemy_e_reduction = 0;
        this.sluggish = 0;
        this.foresight = 0;
        this.blind = 0;
        this.heal_block = 0;
        this.extra_hand_limit_bonus = 0;
        this.negate_next_skill = false;
        this.is_first_player = false;
        this.hand = [];
        this.deck = [];
        this.discard = [];
        this.exile = [];
        this.equipment = [];
        this.cards_played_this_turn = {};
        this.cards_played_this_turn_instance_ids = [];
        this.turn_damage_taken = 0;
        this.turn_damage_dealt = 0;
        this.last_turn_damage_taken = 0;
        this.last_turn_damage_dealt = 0;
        this.total_damage_taken = 0;
        this.total_damage_dealt = 0;
        this.custom_vars = {
            '咖啡首次使用': 1,
            '三角形层数': 0,
            '魔法电池本回合回魔': 0,
        };
        this.onEnterHand = null;
    }

    findHandCard(instanceId) {
        return this.hand.find(card => card.instance_id === Number(instanceId)) || null;
    }

    removeHandCard(instanceId) {
        const idx = this.hand.findIndex(card => card.instance_id === Number(instanceId));
        return idx >= 0 ? this.hand.splice(idx, 1)[0] : null;
    }

    findEquipment(instanceId) {
        return this.equipment.find(eq => eq.card_instance.instance_id === Number(instanceId)) || null;
    }

    handLimit() {
        const ownGoldenLeaf = this.equipment.filter(eq =>
            eq && eq.def_id === 'GoldenLeaf' && (eq.effect_target ?? this.player_id) === this.player_id
        ).length;
        return HAND_LIMIT + ownGoldenLeaf + Math.max(0, Number(this.extra_hand_limit_bonus || 0));
    }

    ruleHandSize() {
        return this.hand.filter(card => card.def_id !== ERROR_CARD_ID).length;
    }

    canAddToHand() {
        return this.ruleHandSize() < this.handLimit();
    }

    handSpace() {
        return Math.max(0, this.handLimit() - this.ruleHandSize());
    }

    addToHand(card, options = {}) {
        this.hand.push(card);
        if (options.triggerEnterHand !== false && typeof this.onEnterHand === 'function') {
            this.onEnterHand(this.player_id, card);
        }
    }

    drawCards(count) {
        const drawn = [];
        const sproutQueue = [];
        for (let i = 0; i < count; i++) {
            if (!this.deck.length) {
                if (!this.discard.length) break;
                this.deck = this.discard.splice(0);
                shuffle(this.deck);
            }
            const card = this.deck.shift();
            if (!card) break;
            if (card.def_id === ERROR_CARD_ID) {
                this.addToHand(card);
                drawn.push(card);
                continue;
            }
            if (!this.canAddToHand()) {
                const flags = card.flags;
                const nonAttract = this.hand.filter(c => !c.flags.has('attract'));
                if (flags.has('attract') && nonAttract.length) {
                    const discardCard = nonAttract[0];
                    this.hand.splice(this.hand.indexOf(discardCard), 1);
                    this.discard.push(discardCard);
                    this.addToHand(card);
                    drawn.push(card);
                } else {
                    this.discard.push(card);
                }
            } else {
                this.addToHand(card);
                drawn.push(card);
            }
            if (card.flags.has('sprout') && this.hand.includes(card)) {
                sproutQueue.push(card);
            }
        }
        while (sproutQueue.length) {
            sproutQueue.shift();
            if (!this.deck.length) {
                if (!this.discard.length) break;
                this.deck = this.discard.splice(0);
                shuffle(this.deck);
            }
            const extra = this.deck.shift();
            if (!extra) break;
            if (extra.def_id === ERROR_CARD_ID) {
                this.addToHand(extra);
                drawn.push(extra);
                continue;
            }
            if (this.canAddToHand()) {
                this.addToHand(extra);
                drawn.push(extra);
                if (extra.flags.has('sprout')) sproutQueue.push(extra);
            } else {
                this.discard.push(extra);
            }
        }
        return drawn;
    }

    heal(amount) {
        if (amount > 0 && toInt(this.heal_block, 0) > 0) {
            const custom = this.custom_statuses || {};
            const immune = ['status_immune', 'immune', '状态免疫'].some(key => toInt(custom[key], 0) > 0);
            if (!immune) {
                const reduction = Math.min(1, 0.5 * toInt(this.heal_block, 0));
                amount = Math.max(0, Math.floor(amount * (1 - reduction)));
            }
            this.heal_block = Math.max(0, toInt(this.heal_block, 0) - 1);
        }
        this.health = Math.min(this.health + amount, this.base_max_health);
    }

    gainElixir(amount) {
        this.elixir = Math.min(this.elixir + amount, this.max_elixir);
    }

    gainMagic(amount) {
        this.magic = Math.min(this.magic + amount, this.max_magic);
    }

    customStatusesDict() {
        const keys = [
            'jungle:fragile', 'fragile',
            'jungle:shield', 'shield',
            'jungle:turn_heal_turns', 'turn_heal_turns',
            'jungle:turn_heal_power', 'turn_heal_power',
            'jungle:turn_magic_turns', 'turn_magic_turns',
            'jungle:turn_magic_power', 'turn_magic_power',
            'jungle:root_status', 'jungle:root', 'root_status',
            'jungle:toxic_poison', 'toxic_poison',
        ];
        const result = {};
        keys.forEach(key => {
            const value = toInt(this[key], 0);
            if (value > 0) result[key] = value;
        });
        return result;
    }

    toDict(includePrivate = true) {
        const data = {
            player_id: this.player_id,
            health: this.health,
            max_health: this.max_health,
            base_max_health: this.base_max_health,
            elixir: this.elixir,
            max_elixir: this.max_elixir,
            magic: this.magic,
            max_magic: this.max_magic,
            armor: this.armor,
            poison: this.poison,
            fire: this.fire,
            vulnerable: this.vulnerable,
            toxic: this.toxic,
            triangle_stacks: this.triangle_stacks,
            dodge: this.dodge,
            nazar_active: this.nazar_active,
            nazar_big_hits: this.nazar_big_hits,
            equipment_protection: this.equipment_protection,
            invincible: this.invincible,
            invincible_until_player: this.invincible_until_player,
            invincible_granted_round: this.invincible_granted_round,
            invincible_granted_turn_marker: this.invincible_granted_turn_marker,
            skip_turn: this.skip_turn,
            damage_multiplier: this.damage_multiplier,
            bandage_active: this.bandage_active,
            bandage_death_pending: this.bandage_death_pending,
            attack_blocked: this.attack_blocked,
            untargetable: this.untargetable,
            sponge_active: this.sponge_active,
            shovel_active: this.shovel_active,
            attack_only: this.attack_only,
            enemy_draw_reduction: this.enemy_draw_reduction,
            enemy_e_reduction: this.enemy_e_reduction,
            sluggish: this.sluggish,
            foresight: this.foresight,
            blind: this.blind,
            extra_hand_limit_bonus: this.extra_hand_limit_bonus,
            negate_next_skill: this.negate_next_skill,
            is_first_player: this.is_first_player,
            coffee_first_use: this.coffee_first_use,
            equipment: this.equipment.map(eq => eq.toDict()),
            deck_count: this.deck.length,
            discard_count: this.discard.length,
            exile_count: this.exile.length,
            hand_count: this.hand.length,
            hand_limit: this.handLimit(),
            turn_damage_taken: this.turn_damage_taken,
            turn_damage_dealt: this.turn_damage_dealt,
            last_turn_damage_taken: this.last_turn_damage_taken,
            last_turn_damage_dealt: this.last_turn_damage_dealt,
            total_damage_taken: this.total_damage_taken,
            total_damage_dealt: this.total_damage_dealt,
            custom_statuses: this.customStatusesDict(),
        };
        if (includePrivate) {
            data.hand = this.hand.map(card => card.toDict());
            data.deck = this.deck.map(card => card.toDict());
            data.discard = this.discard.map(card => card.toDict());
            data.exile = this.exile.map(card => card.toDict());
            data.cards_played_this_turn = { ...this.cards_played_this_turn };
            data.cards_played_this_turn_instance_ids = [...(this.cards_played_this_turn_instance_ids || [])];
            data.custom_vars = { ...this.custom_vars };
        }
        return data;
    }
}

class LocalSoloEngine {
    constructor(payload, options = {}) {
        this.players = [new LocalPlayer(0), new LocalPlayer(1)];
        this.bindPlayerCallbacks();
        this.player_names = options.playerNames || payload.playerNames || ['Player A', 'Player B'];
        this.phase = 'playing';
        this.first_player = [payload.event0, payload.event1].filter(id => id === 7).length === 1
            ? (payload.event0 === 7 ? 0 : 1)
            : 0;
        this.current_player = this.first_player;
        this.round_num = 1;
        this.game_over = false;
        this.winner = null;
        this.log = [];
        this.pending_response = null;
        this.pending_choice = null;
        this.opening_event_picks = [payload.event0 ?? null, payload.event1 ?? null];
        this.opening_event_sub_choices = [payload.sub0 || null, payload.sub1 || null];
        this._antennae_reveal = [null, null];
        this._last_damage_value = [0, 0];
        this._last_positive_damage_hits = [0, 0];
        this._incoming_damage_hint = [0, 0];
        this._game_over_defer_depth = 0;
        this.halve_next_attack = false;
        this.negated_card = false;
        this._last_created_card_instance_id = null;
        this._active_choice = null;
        this._active_effect_context = {};
        this.timed_effects = [];
        this.tutorial = !!options.tutorial;
        this.match_key = `local:${Date.now()}:${Math.random().toString(36).slice(2)}`;

        this.resetPlayer(0, payload.deck0 || [], this.first_player === 0);
        this.resetPlayer(1, payload.deck1 || [], this.first_player === 1);
        for (let i = 0; i < 2; i++) {
            if (this.opening_event_picks[i] != null) this.applyOpeningEvent(i);
        }
        for (let i = 0; i < 2; i++) {
            let handSize = i === this.first_player ? FIRST_PLAYER_HAND_SIZE : INITIAL_HAND_SIZE;
            if (i === this.first_player && this.opening_event_picks[i] === 7) {
                this.players[i].elixir = Math.max(this.players[i].elixir, 7);
                handSize = 5;
            }
            if (this.opening_event_picks[i] === 5) {
                handSize = Math.max(0, handSize - 1);
            }
            this.players[i].drawCards(handSize);
            this.enforceUniqueCardsForPlayer(i);
        }
        this.logMsg(`${options.startLabel || '单人训练场开始'}！${this.pn(this.first_player)}先手。`);
        this.logMsg(`=== 第${this.round_num}回合 ===`);
        this.startPlayerTurn(this.first_player);
    }

    bindPlayerCallbacks() {
        this.players.forEach(player => {
            player.onEnterHand = (playerId, card) => this.handleCardEnterHand(playerId, card);
        });
    }

    cloneForPrediction() {
        const clone = Object.create(LocalSoloEngine.prototype);
        const cloneJson = value => {
            try {
                return typeof structuredClone === 'function'
                    ? structuredClone(value)
                    : JSON.parse(JSON.stringify(value));
            } catch (_) {
                return null;
            }
        };
        clone.players = this.players.map(source => {
            const player = new LocalPlayer(source.player_id);
            const data = source.toDict(true);
            [
                'health', 'max_health', 'base_max_health', 'elixir', 'max_elixir', 'magic', 'max_magic',
                'armor', 'poison', 'fire', 'vulnerable', 'toxic', 'triangle_stacks', 'dodge',
                'nazar_active', 'nazar_big_hits', 'equipment_protection', 'magic_battery_m_this_turn',
                'coffee_first_use', 'invincible', 'invincible_until_player', 'invincible_granted_round',
                'invincible_granted_turn_marker', 'skip_turn', 'damage_multiplier', 'bandage_active',
                'bandage_death_pending', 'attack_blocked', 'untargetable', 'sponge_active',
                'shovel_active', 'attack_only', 'enemy_draw_reduction', 'enemy_e_reduction',
                'extra_hand_limit_bonus', 'negate_next_skill', 'is_first_player',
                'turn_damage_taken', 'turn_damage_dealt', 'last_turn_damage_taken', 'last_turn_damage_dealt',
                'total_damage_taken', 'total_damage_dealt',
            ].forEach(key => { player[key] = data[key] ?? source[key]; });
            player.hand = (data.hand || []).map(card => new LocalCard(card));
            player.deck = (data.deck || []).map(card => new LocalCard(card));
            player.discard = (data.discard || []).map(card => new LocalCard(card));
            player.exile = (data.exile || []).map(card => new LocalCard(card));
            player.equipment = (source.equipment || []).map(eq => {
                const copy = new LocalEquipment(new LocalCard(eq.card_instance.toDict()), eq.owner);
                copy.effect_target = eq.effect_target;
                copy.turns_equipped = eq.turns_equipped;
                copy.uses_this_turn = eq.uses_this_turn;
                copy.corruption_active = !!eq.corruption_active;
                return copy;
            });
            player.cards_played_this_turn = { ...(source.cards_played_this_turn || {}) };
            player.cards_played_this_turn_instance_ids = [...(source.cards_played_this_turn_instance_ids || [])];
            player.custom_vars = { ...(source.custom_vars || {}) };
            return player;
        });
        clone.player_names = [...this.player_names];
        clone.phase = this.phase;
        clone.first_player = this.first_player;
        clone.current_player = this.current_player;
        clone.round_num = this.round_num;
        clone.game_over = this.game_over;
        clone.winner = this.winner;
        clone.log = [...this.log];
        clone.pending_response = cloneJson(this.pending_response);
        clone.pending_choice = cloneJson(this.pending_choice);
        clone.opening_event_picks = [...this.opening_event_picks];
        clone.opening_event_sub_choices = cloneJson(this.opening_event_sub_choices) || [null, null];
        clone._antennae_reveal = cloneJson(this._antennae_reveal) || [null, null];
        clone._last_damage_value = [...this._last_damage_value];
        clone._last_positive_damage_hits = [...(this._last_positive_damage_hits || [0, 0])];
        clone._incoming_damage_hint = [...this._incoming_damage_hint];
        clone._game_over_defer_depth = this._game_over_defer_depth;
        clone.halve_next_attack = this.halve_next_attack;
        clone.negated_card = this.negated_card;
        clone._last_created_card_instance_id = this._last_created_card_instance_id;
        clone._active_choice = cloneJson(this._active_choice);
        clone._active_effect_context = cloneJson(this._active_effect_context) || {};
        clone.timed_effects = cloneJson(this.timed_effects) || [];
        clone.tutorial = this.tutorial;
        clone.match_key = this.match_key;
        clone.bindPlayerCallbacks();
        return clone;
    }

    responsePredictionTargetId(responderId) {
        const pending = this.pending_response || {};
        let targetId = toInt(pending.target_player_id, responderId);
        if (targetId < 0 || targetId >= this.players.length) targetId = responderId;
        if (targetId < 0 || targetId >= this.players.length) targetId = 0;
        return targetId;
    }

    predictionDamagePartsFromLog(logStart, targetId) {
        const targetName = this.pn(targetId);
        const parts = [];
        this.log.slice(logStart).forEach(line => {
            const parsed = this.parseDamageTakenLog(line);
            if (parsed && parsed.target === targetName) {
                parsed.parts.forEach(part => {
                    const value = toInt(part, 0);
                    if (value > 0) parts.push(value);
                });
            }
        });
        return parts;
    }

    simulatePendingResponseDamage(responderId, instanceId = null) {
        if (!this.pending_response) return { total: 0, parts: [], display: '' };
        const targetId = this.responsePredictionTargetId(responderId);
        try {
            const sim = this.cloneForPrediction();
            const simTargetId = sim.responsePredictionTargetId(responderId);
            const beforeHealth = toInt(sim.players[simTargetId].health, 0);
            const logStart = sim.log.length;
            sim.handleResponse(responderId, instanceId);
            let parts = sim.predictionDamagePartsFromLog(logStart, simTargetId);
            let total = parts.reduce((sum, part) => sum + toInt(part, 0), 0);
            if (total <= 0) {
                const afterHealth = toInt(sim.players[simTargetId].health, beforeHealth);
                total = Math.max(0, beforeHealth - afterHealth);
                parts = total > 0 ? [total] : [];
            }
            return {
                target_player_id: targetId,
                total,
                parts,
                display: parts.length ? this.formatDamageParts(parts) : (total === 0 ? '0D' : `${total}D`),
            };
        } catch (_) {
            return { target_player_id: targetId, total: 0, parts: [], display: '' };
        }
    }

    buildResponseDamagePrediction(responderId, counterCards = []) {
        const noCounter = this.simulatePendingResponseDamage(responderId, null);
        const baseTotal = toInt(noCounter.total, 0);
        const counters = {};
        counterCards.forEach(card => {
            const instanceId = toInt(card && card.instance_id, 0);
            if (!instanceId) return;
            const after = this.simulatePendingResponseDamage(responderId, instanceId);
            const reduction = Math.max(0, baseTotal - toInt(after.total, 0));
            counters[String(instanceId)] = {
                after,
                reduction,
                reduction_display: reduction > 0 ? `-${this.formatDamageParts([reduction])}` : '',
            };
        });
        return { no_counter: noCounter, counters };
    }

    handleCardEnterHand(playerId, card) {
        if (!card || card.def_id === ERROR_CARD_ID) return;
        const player = this.players[playerId];
        const copyCount = Math.max(0, toInt(card.def().copy_count, 0));
        if (player && copyCount > 0 && card.flags.has('copy')) {
            let added = 0;
            for (let i = 0; i < copyCount; i++) {
                if (!player.canAddToHand()) break;
                const copyCard = new LocalCard(card.def_id);
                copyCard.instance_flags.add('exile');
                copyCard.disabled_flags.add('copy');
                this.applySetupModifiersToCard(playerId, copyCard);
                player.addToHand(copyCard, { triggerEnterHand: false });
                added += 1;
            }
            if (added > 0) {
                this.logMsg(`${this.pn(playerId)}的${cardName(card.def_id)}因副本效果加入${added}张放逐复制`);
            }
        }
        if (!this.hasCardEvent(card.def(), 'enter_hand')) return;
        this.runCardEvent(playerId, card, 'enter_hand', null, {
            source_id: playerId,
            target_id: playerId,
            zone: 'hand',
        });
    }

    resetPlayer(playerId, deckEntries, isFirst) {
        const ps = this.players[playerId];
        ps.health = INITIAL_HEALTH;
        ps.max_health = BASE_MAX_HEALTH;
        ps.base_max_health = BASE_MAX_HEALTH;
        ps.elixir = INITIAL_ELIXIR;
        ps.magic = INITIAL_MAGIC;
        ps.is_first_player = isFirst;
        ps.hand = [];
        ps.deck = [];
        ps.discard = [];
        ps.exile = [];
        ps.equipment = [];
        ps.cards_played_this_turn = {};
        ps.cards_played_this_turn_instance_ids = [];
        ps.custom_vars = { '咖啡首次使用': 1, '三角形层数': 0, '魔法电池本回合回魔': 0 };
        deckEntries.forEach(entry => {
            const defId = typeof entry === 'string' ? entry : entry && entry.def_id;
            if (defId && cardDef(defId)) ps.deck.push(new LocalCard(entry));
        });
        this.enforceUniqueCardsForPlayer(playerId);
    }

    enforceUniqueCardsForPlayer(playerId, preferredCard = null) {
        const ps = this.players[playerId];
        if (!ps) return;
        const groups = new Map();
        [ps.hand, ps.deck, ps.discard].forEach(zone => {
            zone.slice().forEach(card => {
                if (!card || !card.flags || !card.flags.has('unique')) return;
                if (!groups.has(card.def_id)) groups.set(card.def_id, []);
                groups.get(card.def_id).push({ zone, card });
            });
        });
        groups.forEach(entries => {
            if (entries.length <= 1) return;
            let keep = null;
            if (preferredCard) {
                keep = entries.find(entry => entry.card === preferredCard || entry.card.instance_id === preferredCard.instance_id);
            }
            if (!keep) keep = entries[Math.floor(Math.random() * entries.length)];
            entries.forEach(entry => {
                if (entry === keep || entry.card.instance_id === keep.card.instance_id) return;
                const idx = entry.zone.indexOf(entry.card);
                if (idx >= 0) entry.zone.splice(idx, 1);
                this.putCardInExile(playerId, entry.card);
                this.logMsg(`${this.pn(playerId)}的唯一牌${cardName(entry.card.def_id)}多余副本被放逐`);
            });
        });
    }

    pn(playerId) {
        return this.player_names[playerId] || `玩家${playerId + 1}`;
    }

    logMsg(message) {
        let text = String(message || '').trim();
        if (!text) return;
        text = this.normalizeDamageLogText(text);
        if (this.mergeRepeatedUseBeforeDamage(text)) return;
        if (this.mergeBubbleLog(text)) return;
        if (this.mergeChineseUseEquipment(text)) return;
        if (this.mergeChineseUseDestination(text)) return;
        if (this.mergeSimpleUseDetail(text)) return;
        if (this.mergeSimpleUseDamageLog(text)) return;
        if (this.mergeLegacyUseDamageLog(text)) return;
        if (this.mergeDamageTakenLog(text)) return;
        if (this.moveUseLogBeforeResponseDetail(text)) return;
        this.log.push(text);
    }

    isResponseDetailLog(text) {
        return /^.+使用泡泡(?:进行反制！?|，.*)$/.test(text)
            || /^.+精准牌被闪避反制.*$/.test(text)
            || text === '精准牌被闪避反制，伤害减半！';
    }

    moveUseLogBeforeResponseDetail(text) {
        if (!/^.+使用了.+$/.test(text) || !this.log.length) return false;
        let insertAt = this.log.length;
        while (insertAt > 0 && this.isResponseDetailLog(this.log[insertAt - 1])) {
            insertAt -= 1;
        }
        if (insertAt === this.log.length) return false;
        this.log.splice(insertAt, 0, text);
        return true;
    }

    normalizeDamageLogText(text) {
        const parsed = this.parseDamageTakenLog(text);
        if (!parsed) return text;
        return `${parsed.prefix}${parsed.target}受到${this.formatDamageUnits(parsed.units)}（H=${parsed.hpChain.join('→')}）`;
    }

    parseDamageTakenLog(text) {
        const raw = String(text || '');
        let match = raw.match(/^(.+)受到(\d+(?:\+\d+)*)点伤害[（(]H=([^）)]+)[）)]$/);
        let before;
        let parts;
        let hpText;
        if (match) {
            before = match[1];
            parts = match[2].split('+').map(part => toInt(part, 0));
            return this.buildDamageParseResult(before, match[3], [{ expr: this.formatDamageParts(parts), parts }]);
        } else {
            match = raw.match(/^(.+)受到(\d+)D(?:×(\d+))?(?:×(\d+))?[（(]H=([^）)]+)[）)]$/);
            if (match) {
                before = match[1];
                const innerTimes = Math.max(1, toInt(match[3] || 1, 1));
                const outerTimes = Math.max(1, toInt(match[4] || 1, 1));
                parts = Array(innerTimes).fill(toInt(match[2], 0));
                const expr = `${match[2]}D${innerTimes > 1 ? `×${innerTimes}` : ''}`;
                return this.buildDamageParseResult(before, match[5], Array.from({ length: outerTimes }, () => ({ expr, parts: parts.slice() })));
            } else {
                match = raw.match(/^(.+)受到[（(](\d+(?:\+\d+)*)[）)]D[（(]H=([^）)]+)[）)]$/);
                if (!match) return null;
                before = match[1];
                parts = match[2].split('+').map(part => toInt(part, 0));
                return this.buildDamageParseResult(before, match[3], [{ expr: this.formatDamageParts(parts), parts }]);
            }
        }
    }

    buildDamageParseResult(before, hpText, units) {
        const cut = before.lastIndexOf('，');
        const prefix = cut >= 0 ? before.slice(0, cut + 1) : '';
        const target = cut >= 0 ? before.slice(cut + 1) : before;
        let hpChain = String(hpText || '').split('→').filter(Boolean);
        let startHp = '';
        let endHp = hpChain.length ? hpChain[hpChain.length - 1] : String(hpText || '');
        if (hpChain.length >= 2) {
            startHp = hpChain[0];
        } else {
            const hp = Number.parseInt(endHp, 10);
            const total = (units || []).reduce((sum, unit) => sum + (unit.parts || []).reduce((s, p) => s + toInt(p, 0), 0), 0);
            if (Number.isFinite(hp)) startHp = String(hp + total);
            hpChain = startHp ? [startHp, endHp] : (endHp ? [endHp] : []);
        }
        return {
            prefix,
            target,
            parts: (units || []).flatMap(unit => unit.parts || []),
            units,
            startHp,
            endHp,
            hpChain,
        };
    }

    formatDamageParts(parts) {
        const values = (parts || []).map(part => toInt(part, 0));
        if (!values.length) return '0D';
        if (values.length === 1) return `${values[0]}D`;
        if (values.every(value => value === values[0])) return `${values[0]}D×${values.length}`;
        return `(${values.join('+')})D`;
    }

    formatDamageUnits(units) {
        const clean = (units || []).map(unit => ({
            expr: String(unit.expr || this.formatDamageParts(unit.parts || [])),
            parts: (unit.parts || []).map(part => toInt(part, 0)),
        }));
        if (!clean.length) return '0D';
        const exprs = clean.map(unit => unit.expr);
        if (exprs.every(expr => expr === exprs[0])) {
            return exprs.length === 1 ? exprs[0] : `${exprs[0]}×${exprs.length}`;
        }
        return this.formatDamageParts(clean.flatMap(unit => unit.parts));
    }

    parsePlainUseCountLog(text) {
        const match = String(text || '').match(/^(.+)使用了?([^，]+?)(?: ×(\d+))?$/);
        if (!match) return null;
        return { actor: match[1], card: match[2], count: toInt(match[3] || 1, 1) };
    }

    mergeRepeatedUseBeforeDamage(text) {
        const current = this.parsePlainUseCountLog(text);
        if (!current) return false;
        if (this.log.length >= 1) {
            const lastUse = this.parsePlainUseCountLog(this.log[this.log.length - 1]);
            if (lastUse && lastUse.actor === current.actor && lastUse.card === current.card) {
                this.log[this.log.length - 1] = `${current.actor}使用了${current.card} ×${lastUse.count + current.count}`;
                return true;
            }
        }
        if (this.log.length < 2 || !this.parseDamageTakenLog(this.log[this.log.length - 1])) {
            if (this.log.length >= 1 && this.parseDamageTakenLog(this.log[this.log.length - 1])) {
                this.log.splice(this.log.length - 1, 0, `${current.actor}使用了${current.card}`);
                return true;
            }
            return false;
        }
        const previousUse = this.parsePlainUseCountLog(this.log[this.log.length - 2]);
        if (!previousUse || previousUse.actor !== current.actor || previousUse.card !== current.card) return false;
        this.log[this.log.length - 2] = `${current.actor}使用了${current.card} ×${previousUse.count + current.count}`;
        return true;
    }

    mergeDamageTakenLog(text) {
        if (!this.log.length) return false;
        const current = this.parseDamageTakenLog(text);
        const previous = this.parseDamageTakenLog(this.log[this.log.length - 1]);
        if (!current || !previous || current.target !== previous.target || !previous.startHp) {
            return false;
        }
        let hpChain = previous.hpChain || [previous.startHp, previous.endHp];
        const currentChain = current.hpChain || [current.startHp, current.endHp];
        if (hpChain.length && currentChain.length && hpChain[hpChain.length - 1] === currentChain[0]) {
            hpChain = hpChain.concat(currentChain.slice(1));
        } else {
            hpChain = hpChain.concat([current.endHp]);
        }
        this.log[this.log.length - 1] = `${previous.prefix}${previous.target}受到${this.formatDamageUnits([...(previous.units || [{ expr: this.formatDamageParts(previous.parts), parts: previous.parts }]), ...(current.units || [{ expr: this.formatDamageParts(current.parts), parts: current.parts }])])}（H=${hpChain.join('→')}）`;
        return true;
    }

    mergeBubbleLog(text) {
        if (!this.log.length) return false;
        const last = String(this.log[this.log.length - 1] || '');
        let match = text.match(/^(.+)闪避了攻击！?$/);
        if (match && new RegExp(`^${escapeRegExp(match[1])}使用泡泡进行反制！?$`).test(last)) {
            this.log[this.log.length - 1] = `${match[1]}使用泡泡，闪避了攻击`;
            return true;
        }
        if (text === '精准牌被闪避反制，伤害减半！') {
            match = last.match(/^(.+)使用泡泡进行反制！?$/);
            if (match) {
                this.log[this.log.length - 1] = `${match[1]}使用泡泡，精准攻击伤害减半`;
                return true;
            }
        }
        match = text.match(/^(.+)的精准牌被闪避反制，伤害减半！?$/);
        if (match) {
            const bubble = last.match(/^(.+)使用泡泡进行反制！?$/);
            if (bubble) {
                this.log[this.log.length - 1] = `${bubble[1]}使用泡泡，${match[1]}的精准攻击伤害减半`;
                return true;
            }
        }
        return false;
    }

    mergeSimpleUseDamageLog(text) {
        return false;
    }

    parseChineseUseLog(text) {
        const match = String(text || '').match(/^(.+)使用(?!并)(?:了)?([^，！!:：]+)(?:，(.+))?$/);
        if (!match) return null;
        return {
            actor: match[1],
            card: match[2],
            detail: match[3] || '',
        };
    }

    mergeChineseUseEquipment(text) {
        if (!this.log.length) return false;
        const match = String(text || '').match(/^(.+)装备了(.+)$/);
        if (!match) return false;
        const owner = match[1];
        const cardNameText = match[2];
        const used = this.parseChineseUseLog(this.log[this.log.length - 1]);
        if (!used || used.card !== cardNameText) return false;
        const detail = used.detail ? `，${used.detail}` : '';
        this.log[this.log.length - 1] = used.actor === owner
            ? `${used.actor}使用并装备了${cardNameText}${detail}`
            : `${used.actor}使用并给${owner}装备了${cardNameText}${detail}`;
        return true;
    }

    mergeChineseUseDestination(text) {
        if (!this.log.length) return false;
        const used = this.parseChineseUseLog(this.log[this.log.length - 1]);
        if (!used) return false;
        const actor = escapeRegExp(used.actor);
        const cardNameText = escapeRegExp(used.card);
        let destination = '';
        if (new RegExp(`^(?:${actor}的)?${cardNameText}被放逐$`).test(text)) {
            destination = `${used.card}被放逐`;
        } else if (new RegExp(`^(?:${actor}的)?${cardNameText}移入弃牌堆$`).test(text)) {
            destination = `${used.card}移入弃牌堆`;
        } else if (new RegExp(`^${actor}的${cardNameText}被魔法泡泡反制，失效！?$`).test(text)) {
            destination = `${used.card}被魔法泡泡反制，失效`;
        }
        if (!destination) return false;
        this.log[this.log.length - 1] = `${this.log[this.log.length - 1]}，${destination}`;
        return true;
    }

    mergeSimpleUseDetail(text) {
        if (!this.log.length) return false;
        const match = String(this.log[this.log.length - 1]).match(/^(.+)使用了(.+)$/);
        if (!match) return false;
        const actor = match[1];
        const cardNameText = match[2];
        let detail = '';
        if (String(text).startsWith(actor)) detail = String(text).slice(actor.length);
        const allowedStarts = ['对', '回复', '获得', '抽', '+', '血量', '无法', '仅可', '消耗', '每回合', '丢弃', '查看', '摧毁', '从'];
        if (!allowedStarts.some(prefix => detail.startsWith(prefix))) {
            if (this.parseDamageTakenLog(text)) return false;
            return false;
        }
        this.log[this.log.length - 1] = `${actor}使用${cardNameText}，${detail}`;
        return true;
    }

    mergeLegacyUseDamageLog(text) {
        if (!this.log.length || !this.parseDamageTakenLog(text)) return false;
        const match = String(this.log[this.log.length - 1]).match(/^(.+)使用(.+)！(?:对.+)?造成.+伤害$/);
        if (!match) return false;
        this.log[this.log.length - 1] = `${match[1]}使用${match[2]}，${text}`;
        return true;
    }

    publicState(perspective = null) {
        const forPlayer = perspective == null
            ? (this.tutorial ? 0 : (this.game_over ? 0 : this.current_player))
            : perspective;
        const opponent = 1 - forPlayer;
        const oppData = this.players[opponent].toDict(false);
        oppData.hand_count = this.players[opponent].hand.filter(card => card.def_id !== ERROR_CARD_ID).length;
        oppData.deck_count = this.players[opponent].deck.filter(card => card.def_id !== ERROR_CARD_ID).length;
        oppData.discard_count = this.players[opponent].discard.filter(card => card.def_id !== ERROR_CARD_ID).length;
        oppData.exile_count = this.players[opponent].exile.filter(card => card.def_id !== ERROR_CARD_ID).length;
        if (this.pending_choice && this.pending_choice.player_id === forPlayer) {
            const choiceType = this.pending_choice.choice_type || '';
            const targetId = this.pending_choice.target_player_id;
            const params = this.pending_choice.choice_params || {};
            if (choiceType === 'choose_from_enemy_hand') {
                oppData.hand = this.players[opponent].hand.filter(card => card.def_id !== ERROR_CARD_ID).map(card => card.toDict());
            }
            if (targetId === opponent) {
                if (choiceType === 'choose_card_from_hand' || params.zone === 'hand') {
                    oppData.hand = this.players[opponent].hand.filter(card => card.def_id !== ERROR_CARD_ID).map(card => card.toDict());
                }
                if (choiceType === 'choose_from_deck' || params.zone === 'deck') {
                    oppData.deck = this.players[opponent].deck.filter(card => card.def_id !== ERROR_CARD_ID).map(card => card.toDict());
                }
                if (choiceType === 'choose_from_discard' || params.zone === 'discard') {
                    oppData.discard = this.players[opponent].discard.filter(card => card.def_id !== ERROR_CARD_ID).map(card => card.toDict());
                }
                if (choiceType === 'choose_equipment' || params.zone === 'equipment') {
                    oppData.equipment = this.players[opponent].equipment.map(eq => eq.toDict());
                }
            }
        }
        if (this._antennae_reveal[forPlayer]) {
            oppData.revealed_hand = this.players[opponent].hand.filter(card => card.def_id !== ERROR_CARD_ID).map(card => card.toDict());
            oppData.hand = this.players[opponent].hand.filter(card => card.def_id !== ERROR_CARD_ID).map(card => card.toDict());
        }
        const state = {
            phase: this.phase,
            current_player: this.current_player,
            round_num: this.round_num,
            game_over: this.game_over,
            winner: this.winner,
            you: this.players[forPlayer].toDict(true),
            opponent: oppData,
            log: this.log.slice(),
            log_start: 0,
            log_total: this.log.length,
            match_key: this.match_key,
            pending_response: this.pending_response,
            pending_choice: this.pending_choice,
            opening_event_picks: this.opening_event_picks,
            antennae_reveal: this._antennae_reveal[forPlayer],
            your_id: forPlayer,
            your_name: this.tutorial ? '你' : (forPlayer === 0 ? 'Player A' : 'Player B'),
            opponent_name: this.tutorial ? '练习对手' : (forPlayer === 0 ? 'Player B' : 'Player A'),
            enemy_ids: [opponent],
            opponent_names: [this.tutorial ? this.pn(opponent) : (forPlayer === 0 ? 'Player B' : 'Player A')],
            solo: true,
        };
        if (this.tutorial) state.tutorial = true;
        return state;
    }

    sendState(perspective = null) {
        emit('solo_state', this.publicState(perspective));
    }

    applyOpeningEvent(playerId) {
        const eventId = this.opening_event_picks[playerId];
        const sub = this.opening_event_sub_choices[playerId] || {};
        const ps = this.players[playerId];
        const opp = this.players[1 - playerId];
        if (eventId === 1) {
            ps.max_health += 20;
            ps.base_max_health += 20;
            ps.health += 20;
            this.logMsg(`${this.pn(playerId)}【生命强化】：最大生命值+20`);
        } else if (eventId === 2) {
            (sub.conversions || []).slice(0, 3).forEach(conv => {
                const sourceDef = conv.source_def_id;
                const idx = ps.deck.findIndex(card => card.def_id === sourceDef);
                if (idx >= 0 && cardDef('ManaOrb')) {
                    const mana = new LocalCard('ManaOrb');
                    mana.instance_flags.add('sprout');
                    mana.instance_flags.add('symbiosis');
                    this.applySetupModifiersToCard(playerId, mana);
                    ps.deck[idx] = mana;
                    this.logMsg(`${this.pn(playerId)}【魔力转化】：${cardName(sourceDef)}变为[[card:ManaOrb|flag=sprout|flag=symbiosis]]`);
                }
            });
        } else if (eventId === 3) {
            let converted = 0;
            (sub.convert_def_ids || []).slice(0, 5).forEach(sourceDef => {
                const idx = ps.deck.findIndex(card => card.def_id === sourceDef);
                if (idx >= 0 && cardDef('Light')) {
                    const light = new LocalCard('Light');
                    light.instance_flags.add('sprout');
                    light.instance_flags.add('symbiosis');
                    this.applySetupModifiersToCard(playerId, light);
                    ps.deck[idx] = light;
                    converted += 1;
                }
            });
            this.logMsg(`${this.pn(playerId)}【光之洗礼】：${converted}张牌变为[[card:Light|flag=sprout|flag=symbiosis]]`);
        } else if (eventId === 4) {
            if (!this.statusApplicationBlocked(1 - playerId, 'fire')) {
                opp.fire += 3;
                this.logMsg(`${this.pn(playerId)}【烈焰预兆】：敌方+3灼烧`);
            }
        } else if (eventId === 5) {
            const picked = (sub.add_def_ids || sub.def_ids || []).slice(0, 1);
            let added = 0;
            picked.forEach(defId => {
                if (this.cardAllowedForFatedDraw(defId)) {
                    ps.deck.push(this.applySetupModifiersToCard(playerId, new LocalCard(defId)));
                    added += 1;
                }
            });
            if (added > 0) shuffleInPlace(ps.deck);
            this.logMsg(`${this.pn(playerId)}【命运抽签】：少抽1张牌，${added}张牌洗入牌库`);
        } else if (eventId === 6) {
            this.logMsg(`${this.pn(playerId)}【能量涌动】：每回合多回复1E`);
        } else if (eventId === 7) {
            this.logMsg(`${this.pn(playerId)}【先手压制】：先手回复7E并抽5张牌`);
        } else if (eventId === 8) {
            ps.max_health -= 20;
            ps.base_max_health -= 20;
            ps.health -= 20;
            const targetDef = sub.yggdrasil_convert_def_id;
            let idx = targetDef ? ps.deck.findIndex(card => card.def_id === targetDef) : -1;
            if (idx < 0) idx = ps.deck.findIndex(card => card.def_id !== 'Yggdrasil');
            if (idx >= 0 && cardDef('Yggdrasil')) {
                const oldDef = ps.deck[idx].def_id;
                ps.deck[idx] = this.applySetupModifiersToCard(playerId, new LocalCard('Yggdrasil'));
                this.logMsg(`${this.pn(playerId)}【绝境求生】：最大生命值-20，${cardName(oldDef)}变为Yggdrasil`);
            }
        } else if (eventId === 9) {
            let changed = 0;
            ps.deck.forEach(card => {
                const before = Math.max(0, toInt(card.extra_hits, 0));
                this.applySetupModifiersToCard(playerId, card);
                if (Math.max(0, toInt(card.extra_hits, 0)) > before) {
                    changed += 1;
                }
            });
            let added = 0;
            if (cardDef('Dust')) {
                for (let i = 0; i < 5; i += 1) {
                    const dust = new LocalCard('Dust');
                    dust.instance_flags.add('exile');
                    this.applySetupModifiersToCard(playerId, dust);
                    ps.deck.push(dust);
                    added += 1;
                }
                shuffleInPlace(ps.deck);
            }
            this.logMsg(`${this.pn(playerId)}【多重瓣】：${changed}张多子瓣牌子瓣+1，${added}张[[card:Dust|flag=exile]]洗入牌库`);
        } else if (eventId === 10) {
            ps.custom_vars.setup_magic_acceleration = 1;
            ps.custom_vars.setup_magic_acceleration_play_count = 0;
            this.logMsg(`${this.pn(playerId)}【魔力加速】：每打出2张牌回复1M`);
        }
    }

    cardAllowedForFatedDraw(defId) {
        const def = cardDef(defId);
        if (!def || defId === ERROR_CARD_ID) return false;
        return toInt(def.count, 0) > 0;
    }

    startDrawPhase() {
        this.phase = 'draw';
        this.players.forEach(ps => {
            ps.cards_played_this_turn = {};
            ps.cards_played_this_turn_instance_ids = [];
            ps.magic_battery_m_this_turn = 0;
            ps.custom_vars['魔法电池本回合回魔'] = 0;
        });
        this.logMsg(`=== 第${this.round_num}回合 ===`);
        this.applyLateRoundFirePressure();
        if (this.game_over) return;
        this.startPlayerTurn(this.first_player);
    }

    startPlayerTurn(playerId) {
        this.current_player = playerId;
        this.resetTurnDamageCounters();
        this.applyTurnStartEffects(playerId);
        if (this.game_over) return;
        const ps = this.players[playerId];
        if (ps.custom_vars && ps.custom_vars.ocean_skip_action_after_start) {
            ps.custom_vars.ocean_skip_action_after_start = false;
            this.logMsg(`${this.pn(playerId)}被魔法珊瑚影响，跳过本回合行动`);
            this.endPlayerTurn(playerId);
            return;
        }
        if (ps.skip_turn > 0 && this.isStatusImmune(playerId)) {
            ps.skip_turn = Math.max(0, toInt(ps.skip_turn, 0) - 1);
        } else if (ps.skip_turn > 0) {
            ps.skip_turn -= 1;
            this.logMsg(`${this.pn(playerId)}被眩晕，跳过本回合！`);
            this.endPlayerTurn(playerId);
            return;
        }
        if (ps.health <= 0) {
            this.checkYggdrasil(playerId);
            if (ps.health <= 0) {
                this.checkGameOver();
                return;
            }
        }
        this.phase = 'action';
    }

    runZoneOwnerTurnStartEvents(playerId) {
        const ps = this.players[playerId];
        [
            ['hand', 'hand_owner_turn_start'],
            ['discard', 'discard_owner_turn_start'],
            ['deck', 'deck_owner_turn_start'],
        ].forEach(([zoneName, eventName]) => {
            [...ps[zoneName]].forEach(card => {
                if (ps[zoneName].includes(card) && this.hasCardEvent(card.def(), eventName)) {
                    this.runCardEvent(playerId, card, eventName, null, {
                        event: eventName,
                        source_id: playerId,
                        target_id: playerId,
                        zone: zoneName,
                    });
                }
            });
        });
    }

    runHandOwnerTurnEndEvents(playerId) {
        const ps = this.players[playerId];
        [...ps.hand].forEach(card => {
            if (ps.hand.includes(card) && this.hasCardEvent(card.def(), 'hand_owner_turn_end')) {
                this.runCardEvent(playerId, card, 'hand_owner_turn_end', null, {
                    event: 'hand_owner_turn_end',
                    source_id: playerId,
                    target_id: playerId,
                    zone: 'hand',
                });
            }
        });
    }

    applyTurnStartEffects(playerId) {
        const ps = this.players[playerId];
        const oppId = 1 - playerId;
        const opp = this.players[oppId];
        this._antennae_reveal[playerId] = null;
        this.runZoneOwnerTurnStartEvents(playerId);
        this.runOceanAutoCardsTurnStart(playerId);
        this.runTimedEffectsForTurn(playerId);
        this.applyJungleTurnStartStatuses(playerId);
        const oceanSkipTurns = Math.max(0, toInt((ps.custom_vars || {}).ocean_action_skip_turns, 0));
        const skipDrawRecovery = oceanSkipTurns > 0;
        if (skipDrawRecovery) {
            ps.custom_vars.ocean_action_skip_turns = oceanSkipTurns - 1;
            ps.custom_vars.ocean_skip_action_after_start = true;
        }
        this.players.forEach(owner => {
            owner.equipment.forEach(eq => { eq.uses_this_turn = 0; });
        });
        if (ps.shovel_active) {
            ps.shovel_active = false;
            ps.untargetable = false;
            this.logMsg(`${this.pn(playerId)}的不可选中效果结束`);
        }
        this.clearTurnStartActionStatuses(playerId);
        const earlyEquipment = this.runOwnerTurnStartActionStatusEquipment(playerId);
        if (this.round_num > 1 && !skipDrawRecovery) {
            const drawCount = Math.max(0, DRAW_PER_TURN - ps.enemy_draw_reduction - ps.sluggish);
            const drawn = ps.drawCards(drawCount);
            this.logMsg(`${this.pn(playerId)}抽${drawn.length}张牌`);
            this.applyElectricWebDrawDamage(playerId, drawn.length);
            if (ps.sluggish > 0) this.logMsg(`${this.pn(playerId)}的迟缓减少${Math.min(ps.sluggish, DRAW_PER_TURN)}张抽牌`);
            this.clearSluggishAfterDraw(playerId);
        }
        this.players.forEach((owner, ownerId) => {
            [...owner.equipment].forEach(eq => {
                if (this.hasCardEvent(eq.card_def, 'any_turn_start')) {
                    this.runCardEvent(ownerId, eq.card_instance, 'any_turn_start', null, {
                        event: 'any_turn_start',
                        source_id: ownerId,
                        target_id: playerId,
                    });
                }
            });
        });
        [...opp.equipment].forEach(eq => {
            if (this.hasCardEvent(eq.card_def, 'enemy_turn_start')) {
                this.runCardEvent(oppId, eq.card_instance, 'enemy_turn_start', null, {
                    event: 'enemy_turn_start',
                    source_id: oppId,
                    target_id: playerId,
                });
            } else if (eq.def_id === 'Corruption' && !eq.corruption_active) {
                eq.corruption_active = true;
                this.logMsg(`${this.pn(oppId)}的腐化效果激活`);
            }
        });
        this.players.forEach((owner, ownerId) => {
            [...owner.equipment].forEach(eq => {
                const effectTarget = Number(eq.effect_target ?? ownerId);
                if (effectTarget !== playerId || !this.hasCardEvent(eq.card_def, 'target_turn_start')) return;
                this.runCardEvent(ownerId, eq.card_instance, 'target_turn_start', null, {
                    event: 'target_turn_start',
                    source_id: ownerId,
                    target_id: playerId,
                });
            });
        });
        this._deferTurnStartDeathChecks = true;
        if (ps.poison > 0) {
            this.dealDirectDamage(playerId, ps.poison, '中毒');
            ps.poison = Math.floor(ps.poison / 2);
            this.applyToxicPoisonAfterPoisonSettlement(playerId);
        }
        if (ps.fire > 0) {
            this.dealDirectDamage(playerId, ps.fire, '灼烧');
        }
        if (this.round_num > 1 && !skipDrawRecovery) {
            let recovery = ELIXIR_RECOVERY;
            [...opp.equipment].forEach(eq => {
                const aura = (eq.card_def.effects || []).find(e => e && e.type === 'aura_enemy_elixir_recovery');
                if (aura) recovery += this.evalInt(oppId, (aura.params || {}).amount, eq.card_instance, 0);
                else if (eq.def_id === 'Pincer') recovery -= 1;
            });
            recovery = Math.max(0, recovery - ps.enemy_e_reduction);
            if (this.opening_event_picks[playerId] === 6) {
                recovery += 1;
            }
            ps.gainElixir(recovery);
            this.logMsg(`${this.pn(playerId)}回复${recovery}E`);
        }
        [...ps.equipment].forEach(eq => {
            const key = eq.card_instance && eq.card_instance.instance_id;
            if (earlyEquipment.has(key)) return;
            eq.turns_equipped += 1;
            if (this.hasCardEvent(eq.card_def, 'owner_turn_start')) {
                this.runCardEvent(playerId, eq.card_instance, 'owner_turn_start', null, {
                    event: 'owner_turn_start',
                    source_id: playerId,
                    target_id: eq.effect_target ?? playerId,
                });
            }
        });
        if (!this.game_over) this.applyJungleTurnStartRegen(playerId);
        this._deferTurnStartDeathChecks = false;
        if (ps.health <= 0) {
            this.checkYggdrasil(playerId);
            this.checkGameOver();
        }
    }

    applyToxicPoisonAfterPoisonSettlement(playerId) {
        const ps = this.players[playerId];
        if (!ps) return;
        const custom = ps.custom_statuses || {};
        const immune = toInt(custom.status_immune, 0) > 0
            || toInt(custom.immune, 0) > 0
            || toInt(custom['状态免疫'], 0) > 0;
        if (immune) return;
        const amount = toInt(ps['jungle:toxic_poison'], 0)
            + toInt(ps.toxic_poison, 0)
            + toInt(ps['剧毒'], 0);
        if (amount <= 0) return;
        ps.poison += amount;
        this.logMsg(`${this.pn(playerId)}的剧毒施加${amount}层中毒`);
    }

    effectTreeContainsActionStatus(value, depth = 0) {
        if (depth > 30 || value == null) return false;
        const actionStatuses = new Set([
            'sluggish', '迟缓', 'foresight', '预知', 'blind', '失明',
            'stunned', 'dizzy', 'skip_turn', '眩晕', 'attack_blocked', '禁攻',
            'attack_only', '仅攻击', 'magic_blocked', '魔力封锁',
        ]);
        if (Array.isArray(value)) return value.some(v => this.effectTreeContainsActionStatus(v, depth + 1));
        if (typeof value === 'object') {
            const op = String(value.op || value.type || '');
            const status = String(value.status || value.name || value.id || '');
            if (op === 'electric_web_arm') return true;
            if (['add_status', 'status_add_named', 'set_status', 'set_status_named'].includes(op) && actionStatuses.has(status)) return true;
            return Object.values(value).some(v => this.effectTreeContainsActionStatus(v, depth + 1));
        }
        return false;
    }

    ownerTurnStartEquipmentActionStatuses(eq) {
        const def = eq && eq.card_def;
        if (!def) return false;
        if (this.effectTreeContainsActionStatus((def.events || {}).on_owner_turn_start)) return true;
        return ((def.effects || [])).some(effect => effect && effect.type === 'on_owner_turn_start' && this.effectTreeContainsActionStatus(effect));
    }

    runOwnerTurnStartActionStatusEquipment(playerId) {
        const handled = new Set();
        this.players.forEach((owner, ownerId) => {
            owner.equipment.slice().forEach(eq => {
                if ((eq.effect_target ?? ownerId) !== playerId) return;
                if (!this.ownerTurnStartEquipmentActionStatuses(eq)) return;
                const key = eq.card_instance && eq.card_instance.instance_id;
                if (handled.has(key)) return;
                handled.add(key);
                eq.turns_equipped += 1;
                if (this.hasCardEvent(eq.card_def, 'owner_turn_start')) {
                    this.runCardEvent(ownerId, eq.card_instance, 'owner_turn_start', null, {
                        event: 'owner_turn_start',
                        source_id: ownerId,
                        target_id: playerId,
                    });
                }
            });
        });
        return handled;
    }

    clearTurnStartActionStatuses(playerId) {
        const ps = this.players[playerId];
        const cleared = [];
        [['foresight', '预知'], ['blind', '失明']].forEach(([attr, label]) => {
            if (toInt(ps[attr], 0) <= 0) return;
            if (attr === 'blind' && ps.hand.length && !this.isStatusImmune(playerId)) {
                shuffle(ps.hand);
                this.logMsg(`${this.pn(playerId)}因失明打乱手牌`);
            }
            ps[attr] = 0;
            cleared.push(label);
        });
        if (cleared.length) this.logMsg(`${this.pn(playerId)}的${cleared.join('、')}效果清除`);
    }

    clearSluggishAfterDraw(playerId) {
        const ps = this.players[playerId];
        if (!ps || toInt(ps.sluggish, 0) <= 0) return;
        ps.sluggish = 0;
        this.logMsg(`${this.pn(playerId)}的迟缓效果清除`);
    }

    hasCardEvent(def, eventName) {
        if (hasScriptEntry(def, eventName)) return true;
        const eventType = `on_${eventName}`;
        return ((def && def.effects) || []).some(effect => effect && effect.type === eventType);
    }

    walkChoiceEffects(effects, out = []) {
        (effects || []).forEach(effect => {
            if (!effect || typeof effect !== 'object') return;
            if (EVENT_EFFECT_TYPES.has(effect.type)) return;
            out.push(effect);
            const params = effect.params || {};
            ['then', 'else', 'body', 'effects', 'a', 'b'].forEach(key => {
                if (Array.isArray(params[key])) this.walkChoiceEffects(params[key], out);
            });
        });
        return out;
    }

    choiceTargetFromChoice(choice, fallback = -1) {
        if (!choice || typeof choice !== 'object') return fallback;
        return toInt(choice.target_player ?? choice.target_player_id ?? choice.target_id, fallback);
    }

    choiceTypeForEffect(effect) {
        const params = (effect && effect.params) || {};
        const type = (effect && effect.type) || '';
        if (params.choice_type) return params.choice_type;
        if (type === 'request_target') return 'choose_target';
        if (type === 'request_confirm') return 'confirm';
        if (type === 'request_card') {
            const zone = params.zone || 'hand';
            if (zone === 'equipment') return 'choose_equipment';
            if (zone === 'deck') return 'choose_from_deck';
            if (zone === 'discard') return 'choose_from_discard';
            if (zone === 'exile') return 'choose_from_exile';
            return params.multi ? 'choose_cards_from_hand' : 'choose_card_from_hand';
        }
        if (type === 'choose_from_deck') return 'choose_from_deck';
        if (type === 'choose_from_discard') return 'choose_from_discard';
        if (type === 'steal_enemy_card') return 'choose_from_enemy_hand';
        if (type === 'discard_choice_then_draw') return 'choose_card_to_discard';
        if (type === 'destroy_equipment_choice_or_first') return 'choose_equipment';
        return '';
    }

    choiceRequestSatisfied(effect, choice) {
        if (!effect) return true;
        if (!choice || typeof choice !== 'object') return false;
        const params = effect.params || {};
        const type = effect.type || '';
        const choiceType = this.choiceTypeForEffect(effect);
        if (choice.cancelled && params.continue_on_cancel) return true;
        if (type === 'request_target' || choiceType === 'choose_target') {
            return this.choiceTargetFromChoice(choice) >= 0;
        }
        if (type === 'request_confirm' || choiceType === 'confirm') {
            return choice.confirmed != null || choice.accepted != null;
        }
        if (choiceType === 'choose_cards_from_hand') {
            if (!Array.isArray(choice.target_instance_ids)) return false;
            const minCount = Math.max(0, toInt(params.min_count ?? params.min ?? 1, 1));
            return choice.target_instance_ids.length >= minCount;
        }
        if (choiceType === 'choose_same_attacks_from_hand') {
            return Array.isArray(choice.target_instance_ids) && choice.target_instance_ids.length > 0;
        }
        if (choiceType === 'choose_ocean_sapphire') {
            return this.choiceTargetFromChoice(choice) >= 0 && choice.target_instance_id != null;
        }
        if ([
            'choose_attack_from_hand', 'choose_card_from_hand', 'choose_card_to_discard',
            'choose_from_deck', 'choose_from_discard', 'choose_from_exile',
            'choose_equipment', 'choose_enemy_equipment', 'choose_from_enemy_hand',
        ].includes(choiceType)) {
            return choice.target_instance_id != null || choice.target_def_id != null;
        }
        return !!choice;
    }

    getChoiceRequest(card, choice = null) {
        if (card && this.cardIs(card, 'Spikeball', 'ocean:spikeball')) {
            const loc = this.findCardLocation(card);
            const ownerId = loc ? loc.ownerId : -1;
            const ps = ownerId >= 0 ? this.players[ownerId] : null;
            if (ps && ps.hand.includes(card) && ps.hand.length < 4) return null;
        }
        for (const effect of this.walkChoiceEffects(playEffectsFor(card))) {
            const type = effect.type || '';
            const isChoice = ['request_target', 'request_card', 'request_confirm', 'discard_choice_then_draw', 'destroy_equipment_choice_or_first', 'choose_from_deck', 'choose_from_discard', 'steal_enemy_card'].includes(type);
            if (!isChoice) continue;
            if (this.choiceRequestSatisfied(effect, choice)) continue;
            if (['request_target', 'request_card', 'request_confirm'].includes(type)) return effect;
            if (['discard_choice_then_draw', 'destroy_equipment_choice_or_first', 'choose_from_deck', 'choose_from_discard', 'steal_enemy_card'].includes(type)) {
                return effect;
            }
        }
        return null;
    }

    getChoiceType(card) {
        if (card && card.flags && card.flags.has('wide_strike')) return '';
        const effect = this.getChoiceRequest(card);
        if (!effect) return '';
        return this.choiceTypeForEffect(effect);
    }

    cardNeedsChoice(card) {
        if (card && card.flags && card.flags.has('wide_strike')) return false;
        return !!this.getChoiceRequest(card);
    }

    choiceSatisfiesRequest(card, choice) {
        return !this.getChoiceRequest(card, choice);
    }

    queueCardChoice(playerId, card, choice = null, alreadyPaid = false) {
        const choiceRequest = this.getChoiceRequest(card, choice);
        if (!choiceRequest) return null;
        const choiceParams = (choiceRequest && choiceRequest.params) || {};
        const choiceType = this.choiceTypeForEffect(choiceRequest);
        const oldChoice = this._active_choice;
        if (choice && typeof choice === 'object') this._active_choice = choice;
        let targetId = null;
        try {
            targetId = choiceRequest && choiceRequest.type === 'request_card'
                ? this.resolveTarget(playerId, choiceParams.target || 'self')
                : null;
        } finally {
            this._active_choice = oldChoice;
        }
        this.pending_choice = {
            card: card.toDict(),
            player_id: playerId,
            choice_type: choiceType,
            choice_params: choiceParams,
            original_choice: choice && typeof choice === 'object' ? { ...choice } : null,
            already_paid: !!alreadyPaid,
        };
        if (targetId != null) {
            this.pending_choice.target_player_id = targetId;
            if (['choose_from_enemy_hand', 'choose_card_from_hand'].includes(choiceType) && this.players[targetId]) {
                this.pending_choice.hand_cards = this.players[targetId].hand.map(c => c.toDict());
            }
        }
        const keepPaidChoice = choiceType === 'choose_ocean_sapphire' || choiceType === 'magic_salt_reflect';
        if (alreadyPaid && !keepPaidChoice) {
            const ps = this.players[playerId];
            this.undoMagicAccelerationAfterPendingChoice(playerId, card);
            if (!ps.findHandCard(card.instance_id)) ps.hand.unshift(card);
            ps.elixir += this.paidEForRefund(playerId, card);
            ps.magic += card.cost_m;
            ps.cards_played_this_turn[card.def_id] = Math.max(0, toInt(ps.cards_played_this_turn[card.def_id], 1) - 1);
        }
        const result = {
            success: true,
            needs_choice: true,
            choice_type: choiceType,
            choice_params: choiceParams,
            target_player_id: targetId,
            card: card.toDict(),
        };
        if (targetId != null && ['choose_from_enemy_hand', 'choose_card_from_hand'].includes(choiceType) && this.players[targetId]) {
            result.hand_cards = this.players[targetId].hand.map(c => c.toDict());
        }
        return result;
    }

    defaultAutoChoiceForPending(pending) {
        if (!pending) return null;
        const playerId = toInt(pending.player_id, 0);
        const type = String(pending.choice_type || '');
        const targetId = pending.target_player_id != null ? toInt(pending.target_player_id, 1 - playerId) : (1 - playerId);
        const choice = targetId >= 0 ? { target_player: targetId, target_player_id: targetId, target_id: targetId } : {};
        const card = pending.card ? LocalCard.fromDict(pending.card) : null;
        if (type === 'choose_target') return choice;
        if (type === 'confirm') return { ...choice, confirmed: true, accepted: true };
        if (type === 'choose_cards_from_hand' || type === 'choose_same_attacks_from_hand') {
            const maxCount = Math.max(1, toInt((pending.choice_params || {}).max_count || (pending.choice_params || {}).count || 1, 1));
            const currentId = card ? card.instance_id : -1;
            const cards = this.players[playerId].hand.filter(c => c.instance_id !== currentId && !c.flags.has('exalted') && (type !== 'choose_same_attacks_from_hand' || c.card_type === 'thorn'));
            return { ...choice, target_instance_ids: cards.slice(0, maxCount).map(c => c.instance_id) };
        }
        const zoneMap = {
            choose_attack_from_hand: 'hand',
            choose_card_from_hand: 'hand',
            choose_card_to_discard: 'hand',
            choose_from_enemy_hand: 'hand',
            choose_from_deck: 'deck',
            choose_from_discard: 'discard',
            choose_from_exile: 'exile',
        };
        if (zoneMap[type]) {
            const ownerId = ['choose_from_enemy_hand', 'choose_card_from_hand', 'choose_from_deck', 'choose_from_discard', 'choose_from_exile'].includes(type) ? targetId : playerId;
            const zone = (this.players[ownerId] && this.players[ownerId][zoneMap[type]]) || [];
            let selected = zone.find(c => c && !c.flags.has('exalted') && (!card || c.instance_id !== card.instance_id));
            if (type === 'choose_attack_from_hand') selected = zone.find(c => c && c.card_type === 'thorn' && !c.flags.has('exalted') && (!card || c.instance_id !== card.instance_id));
            return selected ? { ...choice, target_instance_id: selected.instance_id } : null;
        }
        if (type === 'choose_ocean_sapphire') {
            const selected = this.players[playerId].hand.find(c => c.card_type === 'thorn' && !c.flags.has('exalted') && (!card || c.instance_id !== card.instance_id));
            return selected ? { ...choice, target_instance_id: selected.instance_id } : null;
        }
        if (type === 'choose_equipment' || type === 'choose_enemy_equipment') {
            const ownerId = type === 'choose_enemy_equipment' ? targetId : playerId;
            const eq = this.players[ownerId] && this.players[ownerId].equipment[0];
            return eq && eq.card_instance ? { ...choice, target_instance_id: eq.card_instance.instance_id } : null;
        }
        return choice;
    }

    checkCardResponseAfterChoice(playerId, card, choice) {
        const needsResponse = this.checkResponseNeeded(playerId, card) || this.checkPrecisionResponseNeeded(playerId, card);
        if (!needsResponse) return null;
        const targetId = this.choiceTargetFromChoice(choice, 1 - playerId);
        this.pending_response = {
            card: card.toDict(),
            player_id: playerId,
            target_player_id: targetId,
            original_choice: choice,
            is_precision: card.flags.has('precision'),
        };
        return { success: true, needs_response: true, card: card.toDict() };
    }

    resolveTarget(playerId, target) {
        const context = this._active_effect_context || {};
        const canTarget = (id, allowSelf = true) => {
            id = toInt(id, -1);
            if (id < 0 || id >= this.players.length) return false;
            if (id === playerId) return !!allowSelf;
            const ps = this.players[id];
            return !!ps && toInt(ps.health, 0) > 0 && !ps.untargetable;
        };
        if (typeof target === 'number') return target;
        if (target && typeof target === 'object' && target.ref === 'card_owner') {
            const card = this.resolveCardRef(playerId, target.card, null);
            const loc = this.findCardLocation(card);
            return loc ? loc.ownerId : playerId;
        }
        if (!target || target === 'self' || target === 'friendly') return playerId;
        if (target === 'enemy') {
            const enemyId = 1 - playerId;
            return canTarget(enemyId, false) ? enemyId : -1;
        }
        if (target === 'both') return -1;
        if (target === 'random') return Math.random() < 0.5 ? playerId : 1 - playerId;
        if (['choice_target', 'selected_target', 'chosen_target'].includes(target)) {
            const choice = this._active_choice || {};
            const tid = toInt(choice.target_player ?? choice.target_player_id ?? choice.target_id, -1);
            return canTarget(tid, true) ? tid : -1;
        }
        if (['event_source', 'source', 'last_actor', 'damage_source'].includes(target)) return toInt(context.source_id, playerId);
        if (target === 'target') {
            const choice = this._active_choice || {};
            if (choice.target_player != null || choice.target_player_id != null || choice.target_id != null) {
                const tid = toInt(choice.target_player ?? choice.target_player_id ?? choice.target_id, -1);
                return canTarget(tid, true) ? tid : -1;
            }
            const tid = toInt(context.target_id, -1);
            return canTarget(tid, true) ? tid : -1;
        }
        if (target === 'event_target') {
            const tid = toInt(context.target_id, -1);
            return canTarget(tid, true) ? tid : -1;
        }
        return playerId;
    }

    resolveTargets(playerId, target) {
        if (target === 'both' || target === 'all') return [0, 1];
        const tid = this.resolveTarget(playerId, target);
        return tid === -1 ? [] : [tid].filter(id => id >= 0 && id < this.players.length);
    }

    wideStrikeTargetIds(playerId, card) {
        const allowSelf = !!(card && card.flags && card.flags.has('self_target'));
        return this.players
            .map((ps, targetId) => ({ ps, targetId }))
            .filter(({ ps, targetId }) => {
                if (!ps || toInt(ps.health, 0) <= 0) return false;
                if (targetId === playerId) return allowSelf;
                return !ps.untargetable || this.isStatusImmune(targetId);
            })
            .map(({ targetId }) => targetId);
    }

    findCardByInstanceId(instanceId) {
        const id = Number(instanceId);
        if (!Number.isFinite(id)) return null;
        for (const ps of this.players) {
            for (const zone of ['hand', 'deck', 'discard', 'exile']) {
                const found = ps[zone].find(card => card.instance_id === id);
                if (found) return found;
            }
            const eq = ps.equipment.find(item => item.card_instance.instance_id === id);
            if (eq) return eq.card_instance;
        }
        return null;
    }

    findCardLocation(card) {
        if (!card) return null;
        for (const [ownerId, ps] of this.players.entries()) {
            for (const zone of ['hand', 'deck', 'discard', 'exile']) {
                const idx = ps[zone].indexOf(card);
                if (idx >= 0) return { ownerId, zone, index: idx, card };
            }
            const eqIndex = ps.equipment.findIndex(eq => eq.card_instance === card || eq.card_instance.instance_id === card.instance_id);
            if (eqIndex >= 0) return { ownerId, zone: 'equipment', index: eqIndex, card };
        }
        return null;
    }

    resolveCardRef(playerId, ref, currentCard = null) {
        if (ref instanceof LocalCard) return ref;
        if (ref == null) return currentCard;
        if (typeof ref === 'string') {
            if (['current_card', 'this', 'this_card'].includes(ref)) return currentCard;
            if (['selected_card', 'choice_card', 'chosen_card'].includes(ref)) {
                return this.resolveCardRef(playerId, { ref: 'selected_card' }, currentCard);
            }
            if (['last_created_card', 'created_card', 'last_copied_card'].includes(ref)) {
                return this.resolveCardRef(playerId, { ref: 'last_created_card' }, currentCard);
            }
            return null;
        }
        if (typeof ref !== 'object') return null;
        if (ref.op === 'last_created_card') ref = { ref: 'last_created_card' };
        if (ref.op === 'selected_card_at') ref = { ref: 'selected_card_at', index: ref.index };
        if (ref.op === 'selected_card') ref = { ref: 'selected_card' };
        if (ref.op === 'current_card') ref = { ref: 'current_card' };
        if (['current_card', 'this_card'].includes(ref.ref)) return currentCard;
        if (['event_card', 'used_card', 'trigger_card', 'destroyed_card'].includes(ref.ref)) {
            return this.findCardByInstanceId((this._active_effect_context || {}).event_card_instance_id);
        }
        if (['last_created_card', 'created_card', 'last_copied_card'].includes(ref.ref)) {
            return this.findCardByInstanceId(this._active_effect_context.last_created_card_instance_id || this._last_created_card_instance_id);
        }
        if (ref.ref === 'card_instance') return this.findCardByInstanceId(ref.instance_id);
        if (ref.ref === 'var') {
            let raw = this.varStoreForTarget(playerId, ref.target || 'self')[String(ref.name || 'var')];
            if (Array.isArray(raw)) raw = raw.length ? raw[0] : null;
            return this.resolveCardRef(playerId, raw, currentCard);
        }
        if (ref.ref === 'list_item') return this.resolveCardRef(playerId, this.listItemRaw(playerId, ref, currentCard), currentCard);
        if (['selected_card', 'choice_card', 'chosen_card'].includes(ref.ref)) {
            const choice = this._active_choice || {};
            const id = choice.target_instance_id ?? (Array.isArray(choice.target_instance_ids) ? choice.target_instance_ids[0] : null);
            if (id != null) return this.findCardByInstanceId(id);
            if (choice.target_def_id) {
                const targetId = this.resolveTarget(playerId, choice.target_player_id ?? 'self');
                const ps = this.players[targetId] || this.players[playerId];
                return [...ps.hand, ...ps.deck, ...ps.discard, ...ps.exile].find(card => card.def_id === choice.target_def_id) || null;
            }
            return null;
        }
        if (ref.ref === 'selected_card_at') {
            const ids = (this._active_choice && this._active_choice.target_instance_ids) || [];
            const idx = this.evalInt(playerId, ref.index, currentCard, 1) - 1;
            return idx >= 0 && idx < ids.length ? this.findCardByInstanceId(ids[idx]) : null;
        }
        if (ref.ref === 'zone_card') {
            const tid = this.resolveTarget(playerId, ref.target || 'self');
            const ps = this.players[tid];
            if (!ps) return null;
            const zoneName = String(ref.zone || 'hand');
            const zone = zoneName === 'equipment' ? ps.equipment.map(eq => eq.card_instance) : (ps[zoneName] || []);
            const idx = this.evalInt(playerId, ref.index, currentCard, 1) - 1;
            return idx >= 0 && idx < zone.length ? zone[idx] : null;
        }
        return null;
    }

    resolveCardIdRef(playerId, ref, currentCard = null) {
        if (typeof ref === 'string') return ref;
        if (ref && typeof ref === 'object' && ref.ref === 'card_by_id') return String(ref.id || '');
        if (ref && typeof ref === 'object' && ['var', 'list_item'].includes(ref.ref)) {
            let raw = ref.ref === 'var'
                ? this.varStoreForTarget(playerId, ref.target || 'self')[String(ref.name || 'var')]
                : this.listItemRaw(playerId, ref, currentCard);
            if (Array.isArray(raw)) raw = raw.length ? raw[0] : '';
            if (typeof raw === 'string') return raw;
            const rawCard = this.resolveCardRef(playerId, raw, currentCard);
            return rawCard ? rawCard.def_id : '';
        }
        const card = this.resolveCardRef(playerId, ref, currentCard);
        return card ? card.def_id : '';
    }

    cardDefinitionForRef(playerId, ref, currentCard = null) {
        const cardId = this.resolveCardIdRef(playerId, ref, currentCard);
        return cardId ? cardDef(cardId) : null;
    }

    cardDefPropertyValue(playerId, ref, property, currentCard = null) {
        const def = this.cardDefinitionForRef(playerId, ref, currentCard);
        if (!def) return 0;
        const prop = String(property || 'cost_e');
        if (prop === 'flags' || prop === 'tags') return [...new Set(def.flags || [])].map(String).sort();
        if (['cost_e', 'cost_m', 'count', 'trigger_cost_e'].includes(prop)) return toInt(def[prop], 0);
        if (['effect_text', 'description', 'card_type', 'quality', 'name_cn', 'name_en', 'trigger_effect_text', 'id'].includes(prop)) {
            return String(def[prop] || '');
        }
        return def[prop] ?? 0;
    }

    cardDefTags(playerId, ref, currentCard = null) {
        const def = this.cardDefinitionForRef(playerId, ref, currentCard);
        if (!def) return [];
        return [...new Set(def.flags || [])].map(String).sort();
    }

    cleanupEquipmentDerivedEffects(ownerId, eq) {
        const ps = this.players[ownerId];
        if (!ps || !eq) return;
        const effectTarget = Math.max(0, Math.min(this.players.length - 1, toInt(eq.effect_target ?? eq.owner ?? ownerId, ownerId)));
        const targetState = this.players[effectTarget] || ps;
        if (this.cardIs(eq.card_instance || eq, 'Disc', 'vanilla:disc')) {
            targetState.armor = Math.max(0, toInt(targetState.armor, 0) - 2);
        }
        if (this.cardIs(eq.card_instance || eq, 'ElectricWeb', 'factory:electricweb')) {
            this.cleanupElectricWebDrawDamage(eq);
        }
        if (
            this.cardIs(eq.card_instance || eq, 'Sponge', 'ocean:sponge', 'troll_cards:sponge', 'vanilla:sponge')
            && !this.hasOtherSpongeTargeting(effectTarget, eq)
        ) {
            targetState.sponge_active = false;
        }
        if (this.cardIs(eq.card_instance || eq, 'Pill', 'vanilla:pill', 'troll_cards:pill')) {
            targetState.custom_statuses = targetState.custom_statuses || {};
            delete targetState.custom_statuses.status_immune;
            delete targetState.custom_statuses.immune;
            delete targetState.custom_statuses['状态免疫'];
            targetState.status_immune = 0;
            targetState.immune = 0;
            targetState['状态免疫'] = 0;
        }
        const rootLayers = toInt((eq.custom_vars || {}).jungle_root_layers, 0);
        if (rootLayers > 0) {
            const current = this.customStatusValue(effectTarget, 'jungle:root_status', 'jungle:root', 'root_status');
            this.setCustomStatusAliasGroup(effectTarget, 'jungle:root_status', ['jungle:root_status', 'jungle:root', 'root_status'], Math.max(0, current - rootLayers));
            eq.custom_vars.jungle_root_layers = 0;
        }
    }

    cleanupElectricWebDrawDamage(eq) {
        if (!eq) return;
        eq.custom_vars = eq.custom_vars || {};
        const targetId = toInt(eq.custom_vars.electric_web_armed_target, -1);
        const amount = toInt(eq.custom_vars.electric_web_armed_amount, 0);
        if (amount > 0 && this.players[targetId]) {
            const current = toInt(this.players[targetId].custom_vars.electric_web_draw_damage, 0);
            this.players[targetId].custom_vars.electric_web_draw_damage = Math.max(0, current - amount);
        }
        eq.custom_vars.electric_web_armed_target = -1;
        eq.custom_vars.electric_web_armed_amount = 0;
    }

    clearElectricWebDrawRecordsForTarget(targetId) {
        if (!this.players[targetId]) return;
        this.players.forEach(ps => {
            (ps.equipment || []).forEach(eq => {
                if (!eq || !this.cardIs(eq.card_instance || eq, 'ElectricWeb', 'factory:electricweb')) return;
                eq.custom_vars = eq.custom_vars || {};
                if (toInt(eq.custom_vars.electric_web_armed_target, -1) === targetId) {
                    eq.custom_vars.electric_web_armed_target = -1;
                    eq.custom_vars.electric_web_armed_amount = 0;
                }
            });
        });
    }

    hasOtherSpongeTargeting(targetId, excludeEq = null) {
        return this.players.some((ownerState, ownerId) => (ownerState.equipment || []).some(candidate => {
            if (!candidate || candidate === excludeEq) return false;
            if (!this.cardIs(candidate.card_instance || candidate, 'Sponge', 'ocean:sponge', 'troll_cards:sponge', 'vanilla:sponge')) return false;
            const effectTarget = Math.max(0, Math.min(this.players.length - 1, toInt(candidate.effect_target ?? candidate.owner ?? ownerId, ownerId)));
            return effectTarget === targetId;
        }));
    }

    removeCardFromCurrentZone(card) {
        const loc = this.findCardLocation(card);
        if (!loc) return null;
        const ps = this.players[loc.ownerId];
        if (loc.zone === 'equipment') {
            this.cleanupEquipmentDerivedEffects(loc.ownerId, ps.equipment[loc.index]);
            ps.equipment.splice(loc.index, 1);
        }
        else ps[loc.zone].splice(loc.index, 1);
        return loc;
    }

    varStoreForTarget(playerId, target) {
        if (target === 'global') {
            this.custom_vars = this.custom_vars || {};
            return this.custom_vars;
        }
        if (target === 'team') {
            return (this.players[playerId] || this.players[0]).custom_vars;
        }
        const tid = this.resolveTarget(playerId, target || 'self');
        return (this.players[tid] || this.players[playerId]).custom_vars;
    }

    scalarValue(value, fallbackValue = 0) {
        if (Array.isArray(value)) return value.length ? this.scalarValue(value[0], fallbackValue) : fallbackValue;
        if (value && typeof value === 'object') {
            if (value.ref === 'card_instance') {
                const card = this.findCardByInstanceId(value.instance_id);
                return card ? card.def_id : fallbackValue;
            }
            return fallbackValue;
        }
        return value == null ? fallbackValue : value;
    }

    serializableListItem(item) {
        if (item instanceof LocalCard) return { ref: 'card_instance', instance_id: item.instance_id };
        if (Array.isArray(item)) return item.map(v => this.serializableListItem(v));
        if (item && typeof item === 'object') {
            return Object.fromEntries(Object.entries(item).map(([k, v]) => [k, this.serializableListItem(v)]));
        }
        return item;
    }

    zoneList(playerId, target, zoneName) {
        const tid = this.resolveTarget(playerId, target || 'self');
        const ps = this.players[tid];
        if (!ps) return [];
        const zone = zoneName === 'equipment' ? ps.equipment.map(eq => eq.card_instance) : (ps[zoneName] || []);
        return zone.filter(Boolean).map(card => ({ ref: 'card_instance', instance_id: card.instance_id }));
    }

    evalList(playerId, expr, currentCard = null) {
        expr = parseJsonish(expr);
        if (Array.isArray(expr)) return expr.map(v => this.serializableListItem(v));
        if (expr == null) return [];
        if (typeof expr !== 'object') return [expr];
        const ref = expr.ref;
        if (ref === 'list' || ref === 'list_create') return (expr.items || []).map(item => this.serializableListItem(this.evalRawItem(playerId, item, currentCard)));
        if (ref === 'list_var') {
            const raw = this.varStoreForTarget(playerId, expr.target || 'self')[String(expr.name || 'var')];
            return Array.isArray(raw) ? [...raw] : (raw == null ? [] : [raw]);
        }
        if (ref === 'var') {
            const raw = this.varStoreForTarget(playerId, expr.target || 'self')[String(expr.name || 'var')];
            return Array.isArray(raw) ? [...raw] : (raw == null ? [] : [raw]);
        }
        if (ref === 'zone_list') return this.zoneList(playerId, expr.target || 'self', String(expr.zone || 'hand'));
        if (ref === 'card_def_tags') return this.cardDefTags(playerId, expr.card || '', currentCard);
        if (ref === 'list_item') {
            const item = this.listItemRaw(playerId, expr, currentCard);
            return item == null ? [] : [item];
        }
        return [this.evalExpr(playerId, expr, currentCard, 0)];
    }

    listItemRaw(playerId, expr, currentCard = null) {
        const values = this.evalList(playerId, expr && expr.list, currentCard);
        const idx = this.evalInt(playerId, expr && expr.index, currentCard, 1) - 1;
        return idx >= 0 && idx < values.length ? values[idx] : null;
    }

    evalRawItem(playerId, expr, currentCard = null) {
        expr = parseJsonish(expr);
        if (typeof expr === 'string') {
            const asNumber = Number(expr);
            return Number.isFinite(asNumber) ? asNumber : expr;
        }
        if (typeof expr === 'number' || typeof expr === 'boolean' || expr == null) return expr;
        if (expr && typeof expr === 'object') {
            const ref = expr.ref;
            if (ref === 'list_item') return this.listItemRaw(playerId, expr, currentCard);
            if (['card_instance', 'zone_card', 'selected_card', 'selected_card_at', 'current_card', 'this_card', 'event_card', 'used_card', 'trigger_card', 'destroyed_card', 'last_created_card', 'created_card', 'last_copied_card'].includes(ref)) {
                const card = this.resolveCardRef(playerId, expr, currentCard);
                return card ? this.serializableListItem(card) : expr;
            }
            if (ref === 'var') {
                const raw = this.varStoreForTarget(playerId, expr.target || 'self')[String(expr.name || 'var')];
                return Array.isArray(raw) ? (raw.length ? raw[0] : null) : raw;
            }
        }
        return this.evalExpr(playerId, expr, currentCard, 0);
    }

    evalVarAssignmentValue(playerId, expr, currentCard = null) {
        expr = parseJsonish(expr);
        if (Array.isArray(expr)) return expr.length ? this.serializableListItem(expr[0]) : 0;
        if (expr && typeof expr === 'object' && ['list', 'list_create', 'list_var', 'zone_list', 'card_def_tags'].includes(expr.ref)) {
            const values = this.evalList(playerId, expr, currentCard);
            return values.length ? this.serializableListItem(values[0]) : 0;
        }
        return this.serializableListItem(this.evalRawItem(playerId, expr, currentCard));
    }

    sameListItem(a, b) {
        a = this.serializableListItem(a);
        b = this.serializableListItem(b);
        if (a && typeof a === 'object' && a.ref === 'card_instance' && typeof b === 'string') {
            const card = this.findCardByInstanceId(a.instance_id);
            return !!card && card.def_id === b;
        }
        if (b && typeof b === 'object' && b.ref === 'card_instance' && typeof a === 'string') {
            const card = this.findCardByInstanceId(b.instance_id);
            return !!card && card.def_id === a;
        }
        return JSON.stringify(a) === JSON.stringify(b);
    }

    statusCount(targetId, status) {
        if (targetId < 0) return this.players.reduce((sum, _, idx) => sum + this.statusCount(idx, status), 0);
        const ps = this.players[targetId];
        if (!ps) return 0;
        const key = String(status || '');
        if (this.isStatusImmune(targetId) && !['status_immune', 'immune', '状态免疫'].includes(key)) return 0;
        const map = {
            poison: ps.poison,
            '中毒': ps.poison,
            burn: ps.fire,
            fire: ps.fire,
            '灼烧': ps.fire,
            vulnus: ps.vulnerable,
            vulnerable: ps.vulnerable,
            '易伤': ps.vulnerable,
            toxic: ps.toxic,
            '淬毒': ps.toxic,
            dodge: ps.dodge,
            '闪避': ps.dodge,
            equip_protection: ps.equipment_protection,
            equipment_protection: ps.equipment_protection,
            '装备摧毁保护': ps.equipment_protection,
            invincible: ps.invincible ? 1 : 0,
            '无敌': ps.invincible ? 1 : 0,
            untargetable: ps.untargetable ? 1 : 0,
            '不可选中': ps.untargetable ? 1 : 0,
            '邪眼': this.nazarStatusValue(playerId),
            Nazar: this.nazarStatusValue(playerId),
            nazar: this.nazarStatusValue(playerId),
        };
        if (Object.prototype.hasOwnProperty.call(map, key)) return toInt(map[key], 0);
        return toInt(ps[key], 0);
    }

    customStatusValue(playerId, ...keys) {
        const ps = this.players[playerId];
        if (!ps) return 0;
        const values = keys.map(key => toInt(ps[String(key || '')], 0));
        return Math.max(0, ...values);
    }

    setCustomStatusAliasGroup(playerId, primaryKey, keys, value) {
        const ps = this.players[playerId];
        if (!ps) return;
        const amount = Math.max(0, toInt(value, 0));
        const allKeys = Array.from(new Set([primaryKey, ...(keys || [])].filter(Boolean).map(String)));
        allKeys.forEach(key => { ps[key] = 0; });
        if (amount > 0) ps[String(primaryKey)] = amount;
    }

    mergeTurnRegenStatus(playerId, kind, turns, power) {
        const isMagic = String(kind || '') === 'magic';
        const turnsKey = isMagic ? 'jungle:turn_magic_turns' : 'jungle:turn_heal_turns';
        const powerKey = isMagic ? 'jungle:turn_magic_power' : 'jungle:turn_heal_power';
        const turnAliases = isMagic ? ['jungle:turn_magic_turns', 'turn_magic_turns'] : ['jungle:turn_heal_turns', 'turn_heal_turns'];
        const powerAliases = isMagic ? ['jungle:turn_magic_power', 'turn_magic_power'] : ['jungle:turn_heal_power', 'turn_heal_power'];
        const mergedTurns = this.customStatusValue(playerId, ...turnAliases) + Math.max(0, toInt(turns, 0));
        const mergedPower = Math.max(this.customStatusValue(playerId, ...powerAliases), Math.max(0, toInt(power, 0)));
        this.setCustomStatusAliasGroup(playerId, turnsKey, turnAliases, mergedTurns);
        this.setCustomStatusAliasGroup(playerId, powerKey, powerAliases, mergedPower);
        return [mergedTurns, mergedPower];
    }

    applyJungleTurnStartStatuses(playerId) {
        const ps = this.players[playerId];
        if (!ps) return;
        ps.custom_vars.electric_web_draw_damage = 0;
        this.clearElectricWebDrawRecordsForTarget(playerId);
        ps['jungle:fragile'] = 0;
        ps.fragile = 0;
        const shield = this.customStatusValue(playerId, 'jungle:shield', 'shield');
        if (shield > 0) this.setCustomStatusAliasGroup(playerId, 'jungle:shield', ['jungle:shield', 'shield'], Math.floor(shield / 2));
    }

    applyJungleTurnStartRegen(playerId) {
        const ps = this.players[playerId];
        if (!ps) return;
        const healTurns = this.customStatusValue(playerId, 'jungle:turn_heal_turns', 'turn_heal_turns');
        const healPower = this.customStatusValue(playerId, 'jungle:turn_heal_power', 'turn_heal_power');
        if (healTurns > 0 && healPower > 0) {
            if (!this.isStatusImmune(playerId)) {
                ps.heal(healPower);
                this.logMsg(`${this.pn(playerId)}的回合回复：+${healPower}H`);
            }
            this.setCustomStatusAliasGroup(playerId, 'jungle:turn_heal_turns', ['jungle:turn_heal_turns', 'turn_heal_turns'], healTurns - 1);
            if (healTurns - 1 <= 0) this.setCustomStatusAliasGroup(playerId, 'jungle:turn_heal_power', ['jungle:turn_heal_power', 'turn_heal_power'], 0);
        }
        const magicTurns = this.customStatusValue(playerId, 'jungle:turn_magic_turns', 'turn_magic_turns');
        const magicPower = this.customStatusValue(playerId, 'jungle:turn_magic_power', 'turn_magic_power');
        if (magicTurns > 0 && magicPower > 0) {
            if (!this.isStatusImmune(playerId)) {
                ps.gainMagic(magicPower);
                this.logMsg(`${this.pn(playerId)}的魔力回合回复：+${magicPower}M`);
            }
            this.setCustomStatusAliasGroup(playerId, 'jungle:turn_magic_turns', ['jungle:turn_magic_turns', 'turn_magic_turns'], magicTurns - 1);
            if (magicTurns - 1 <= 0) this.setCustomStatusAliasGroup(playerId, 'jungle:turn_magic_power', ['jungle:turn_magic_power', 'turn_magic_power'], 0);
        }
    }

    zoneSize(targetId, zoneName) {
        if (targetId < 0) return this.players.reduce((sum, _, idx) => sum + this.zoneSize(idx, zoneName), 0);
        const ps = this.players[targetId];
        if (!ps) return 0;
        const zone = String(zoneName || 'hand');
        if (zone === 'equipment') return ps.equipment.length;
        return (ps[zone] || []).length;
    }

    resetTurnDamageCounters() {
        this.players.forEach(ps => {
            ps.turn_damage_taken = 0;
            ps.turn_damage_dealt = 0;
        });
    }

    saveLastTurnDamageSnapshot(playerId) {
        const ps = this.players[playerId];
        if (!ps) return;
        ps.last_turn_damage_taken = toInt(ps.turn_damage_taken, 0);
        ps.last_turn_damage_dealt = toInt(ps.turn_damage_dealt, 0);
    }

    recordDamage(targetId, amount, sourceId = null) {
        const value = Math.max(0, toInt(amount, 0));
        if (value <= 0) return;
        const target = this.players[targetId];
        if (target) {
            target.turn_damage_taken += value;
            target.total_damage_taken += value;
        }
        const source = this.players[sourceId];
        if (source) {
            source.turn_damage_dealt += value;
            source.total_damage_dealt += value;
        }
    }

    evalExpr(playerId, expr, currentCard = null, fallbackValue = 0) {
        expr = parseJsonish(expr);
        if (expr == null) return fallbackValue;
        if (typeof expr === 'number') return expr;
        if (typeof expr === 'boolean') return expr ? 1 : 0;
        if (typeof expr === 'string') {
            const asNumber = Number(expr);
            return Number.isFinite(asNumber) ? asNumber : fallbackValue;
        }
        if (typeof expr !== 'object') return fallbackValue;
        const ref = expr.ref;
        const op = expr.op || expr.ref || expr.type || '';
        if (op === 'const') return expr.value ?? fallbackValue;
        if (op === 'var') {
            const context = this._active_effect_context || {};
            const key = String(expr.name || expr.id || 'var');
            if (Object.prototype.hasOwnProperty.call(context, key)) return context[key];
            const store = this.varStoreForTarget(playerId, expr.target || 'self');
            return this.scalarValue(store[key], 0);
        }
        if (op === 'player_stat') {
            const tid = this.resolveTarget(playerId, expr.target || 'self');
            if (tid < 0) {
                return this.players.reduce((sum, _, idx) => sum + this.playerPropertyValue(idx, expr.stat || expr.property || 'health'), 0);
            }
            return this.playerPropertyValue(tid, expr.stat || expr.property || 'health');
        }
        if (op === 'card_prop') {
            const card = this.resolveCardRef(playerId, expr.card || { ref: 'current_card' }, currentCard);
            if (!card) return fallbackValue;
            const prop = String(expr.property || expr.prop || 'cost_e');
            if (prop === 'base_hits' || prop === 'base_petals' || prop === 'base_petal_count') {
                return Math.max(1, toInt((card.def && card.def().hits) || 1, 1));
            }
            if (prop === 'total_hits' || prop === 'petals' || prop === 'petal_count' || prop === '子瓣') {
                return this.cardTotalHits(card, Math.max(1, toInt((card.def && card.def().hits) || 1, 1)));
            }
            if (prop === 'cost_e') return toInt(card.cost_e, 0);
            if (prop === 'cost_m') return toInt(card.cost_m, 0);
            if (prop === 'paid_e') return toInt(card._paid_e_this_play ?? card.cost_e, 0);
            if (prop === 'paid_m') return toInt(card._paid_m_this_play ?? card.cost_m, 0);
            if (prop === 'tag_count' || prop === 'tags_count') return card.flags.size;
            return toInt(card[prop], fallbackValue);
        }
        if (op === 'equipment_prop' || op === 'equipment_property') {
            const eq = this.resolveEquipmentRef(playerId, expr.equipment || { ref: 'current_equipment' }, currentCard);
            return this.equipmentProperty(eq, expr.property || expr.prop || 'turns_equipped');
        }
        if (op === 'current_damage' || op === 'damage_amount') {
            const context = this._active_effect_context || {};
            return toInt(context.damage ?? context.amount, 0);
        }
        if (op === 'status_stack') {
            const tid = this.resolveTarget(playerId, expr.target || 'self');
            return this.statusCount(tid, expr.status || expr.name || expr.id || '');
        }
        if (op === 'count') {
            if (expr.zone) return this.zoneSize(this.resolveTarget(playerId, expr.target || 'self'), expr.zone);
            if (expr.list) return this.evalList(playerId, expr.list, currentCard).length;
            return fallbackValue;
        }
        if (op === 'add' || op === '+') {
            const values = Array.isArray(expr.values) ? expr.values : [expr.a, expr.b];
            return values.reduce((sum, value) => sum + this.evalExpr(playerId, value, currentCard, 0), 0);
        }
        if (op === 'sub' || op === '-') {
            const values = Array.isArray(expr.values) ? expr.values : [expr.a, expr.b];
            if (!values.length) return 0;
            return values.slice(1).reduce((out, value) => out - this.evalExpr(playerId, value, currentCard, 0), this.evalExpr(playerId, values[0], currentCard, 0));
        }
        if (op === 'mul' || op === '*') {
            const values = Array.isArray(expr.values) ? expr.values : [expr.a, expr.b];
            return values.reduce((out, value) => out * this.evalExpr(playerId, value, currentCard, 0), 1);
        }
        if (op === 'div' || op === '/') {
            const values = Array.isArray(expr.values) ? expr.values : [expr.a, expr.b];
            if (values.length < 2) return 0;
            const b = this.evalExpr(playerId, values[1], currentCard, 0);
            return b === 0 ? 0 : this.evalExpr(playerId, values[0], currentCard, 0) / b;
        }
        if (op === 'floor') return Math.floor(this.evalExpr(playerId, expr.value ?? expr.a, currentCard, 0));
        if (op === 'ceil') return Math.ceil(this.evalExpr(playerId, expr.value ?? expr.a, currentCard, 0));
        if (op === 'min') {
            const values = Array.isArray(expr.values) ? expr.values : [expr.a, expr.b];
            return values.length ? Math.min(...values.map(value => this.evalExpr(playerId, value, currentCard, 0))) : 0;
        }
        if (op === 'max') {
            const values = Array.isArray(expr.values) ? expr.values : [expr.a, expr.b];
            return values.length ? Math.max(...values.map(value => this.evalExpr(playerId, value, currentCard, 0))) : 0;
        }
        if (op === 'last_damage') {
            const tid = this.resolveTarget(playerId, expr.target || 'enemy');
            return toInt(this._last_damage_value[tid], 0);
        }
        if (op === 'last_positive_hits' || op === 'positive_hits') {
            const tid = this.resolveTarget(playerId, expr.target || 'enemy');
            return toInt((this._last_positive_damage_hits || [])[tid], 0);
        }
        if (op === 'selected_cards_count') {
            const choice = this._active_choice || {};
            if (Array.isArray(choice.target_instance_ids)) return choice.target_instance_ids.length;
            return choice.target_instance_id != null || choice.target_def_id != null ? 1 : 0;
        }
        if (op === 'selected_card_index') return toInt((this._active_effect_context || {}).selected_card_index, 0);
        if (ref === 'var') {
            const context = this._active_effect_context || {};
            const key = String(expr.name || expr.id || 'var');
            if (Object.prototype.hasOwnProperty.call(context, key)) return context[key];
            const store = this.varStoreForTarget(playerId, expr.target || 'self');
            return this.scalarValue(store[key], 0);
        }
        if (ref === 'source_player' || op === 'source_player') {
            return playerId;
        }
        if (ref === 'timer_remaining') {
            return toInt((this._active_effect_context || {}).timer_remaining, 0);
        }
        if (ref === 'loop_index') {
            const context = this._active_effect_context || {};
            return toInt(context.loop_index ?? context.list_index ?? context.equipment_index ?? context.repeat_index, 0);
        }
        if (ref === 'damage_source') {
            return toInt((this._active_effect_context || {}).source_id, playerId);
        }
        if (ref === 'damage_amount') {
            const context = this._active_effect_context || {};
            return toInt(context.damage ?? context.amount, 0);
        }
        if (ref === 'list_var' || ref === 'list' || ref === 'zone_list') return this.scalarValue(this.evalList(playerId, expr, currentCard), 0);
        if (ref === 'list_length') return this.evalList(playerId, expr.list || [], currentCard).length;
        if (ref === 'list_item') return this.scalarValue(this.listItemRaw(playerId, expr, currentCard), 0);
        if (ref === 'player_property' || ref === 'target_attribute') {
            const tid = this.resolveTarget(playerId, expr.target || 'self');
            if (tid < 0) {
                return this.players.reduce((sum, _, idx) => sum + this.evalExpr(idx, { ...expr, target: idx }, currentCard, 0), 0);
            }
            const prop = String(expr.property || expr.attribute || expr.attr || 'health');
            return this.playerPropertyValue(tid, prop);
        }
        if (ref === 'math_op') {
            const a = this.evalExpr(playerId, expr.a, currentCard, 0);
            const b = this.evalExpr(playerId, expr.b, currentCard, 0);
            if (expr.op === '+') return a + b;
            if (expr.op === '-') return a - b;
            if (expr.op === '*') return a * b;
            if (expr.op === '/') return b === 0 ? 0 : Math.trunc(a / b);
            if (expr.op === '%') return b === 0 ? 0 : a % b;
            return 0;
        }
        if (ref === 'min_max') {
            const a = this.evalExpr(playerId, expr.a, currentCard, 0);
            const b = this.evalExpr(playerId, expr.b, currentCard, 0);
            return expr.mode === 'max' ? Math.max(a, b) : Math.min(a, b);
        }
        if (ref === 'card_property') {
            const card = this.resolveCardRef(playerId, expr.card || { ref: 'current_card' }, currentCard);
            if (!card) return 0;
            const prop = String(expr.property || 'fusion_level');
            if (prop === 'cost_e') return toInt(card.cost_e, 0);
            if (prop === 'cost_m') return toInt(card.cost_m, 0);
            if (prop === 'cost_e_override') return card.cost_e_override != null ? toInt(card.cost_e_override, 0) : toInt(card.def().cost_e, 0);
            if (prop === 'cost_m_override') return card.cost_m_override != null ? toInt(card.cost_m_override, 0) : toInt(card.def().cost_m, 0);
            return toInt(card[prop], 0);
        }
        if (ref === 'card_tag_count') {
            const card = this.resolveCardRef(playerId, expr.card || { ref: 'current_card' }, currentCard);
            return card ? card.flags.size : 0;
        }
        if (ref === 'card_def_property') {
            return this.cardDefPropertyValue(playerId, expr.card || '', expr.property || 'cost_e', currentCard);
        }
        if (ref === 'card_def_tags') {
            return this.cardDefTags(playerId, expr.card || '', currentCard);
        }
        if (ref === 'equipment_property') {
            const eq = this.resolveEquipmentRef(playerId, expr.equipment || { ref: 'current_equipment' }, currentCard);
            return this.equipmentProperty(eq, expr.property || 'turns_equipped');
        }
        if (ref === 'status_count') {
            const tid = this.resolveTarget(playerId, expr.target || 'self');
            return this.statusCount(tid, expr.status || '');
        }
        if (ref === 'zone_count') {
            const tid = this.resolveTarget(playerId, expr.target || 'self');
            return this.zoneSize(tid, expr.zone || 'hand');
        }
        if (['turn_damage_taken', 'turn_damage_dealt', 'last_turn_damage_taken', 'last_turn_damage_dealt', 'total_damage_taken', 'total_damage_dealt'].includes(ref)) {
            const tid = this.resolveTarget(playerId, expr.target || 'self');
            const ps = this.players[tid] || this.players[playerId];
            return toInt(ps[ref], 0);
        }
        if (ref === 'last_damage') {
            const tid = this.resolveTarget(playerId, expr.target || 'enemy');
            return toInt(this._last_damage_value[tid], 0);
        }
        if (ref === 'last_positive_hits' || ref === 'positive_hits') {
            const tid = this.resolveTarget(playerId, expr.target || 'enemy');
            return toInt((this._last_positive_damage_hits || [])[tid], 0);
        }
        if (ref === 'incoming_damage') {
            const tid = this.resolveTarget(playerId, expr.target || 'self');
            return toInt(this._incoming_damage_hint[tid], 0);
        }
        if (ref === 'selected_cards_count') {
            const choice = this._active_choice || {};
            if (Array.isArray(choice.target_instance_ids)) return choice.target_instance_ids.length;
            return choice.target_instance_id != null || choice.target_def_id != null ? 1 : 0;
        }
        if (ref === 'selected_card_index') return toInt((this._active_effect_context || {}).selected_card_index, 0);
        if (ref === 'equipment_count_named') {
            const tid = this.resolveTarget(playerId, expr.target || 'self');
            const ids = tid === -1 ? this.players.map((_, idx) => idx) : [tid];
            const idSet = new Set(ids);
            let total = 0;
            this.players.forEach((ps, ownerId) => {
                ps.equipment.forEach(eq => {
                    const effectTarget = toInt(eq.effect_target ?? eq.owner ?? ownerId, ownerId);
                    if (eq.def_id === expr.card_id && idSet.has(effectTarget)) total += 1;
                });
            });
            return total;
        }
        if (ref === 'hand_limit') {
            const tid = this.resolveTarget(playerId, expr.target || 'self');
            const ps = this.players[tid] || this.players[playerId];
            return ps.handLimit();
        }
        if (ref === 'hand_size' || ref === 'deck_remaining' || ref === 'discard_size' || ref === 'exile_size') {
            const tid = this.resolveTarget(playerId, expr.target || 'self');
            const ps = this.players[tid] || this.players[playerId];
            const zone = ref === 'deck_remaining' ? 'deck' : ref.replace('_size', '');
            return (ps[zone] || []).length;
        }
        if (ref === 'play_count') {
            return toInt(this.players[playerId].cards_played_this_turn[expr.card_id || (currentCard && currentCard.def_id)], 0);
        }
        if (ref === 'equip_turns') {
            const eq = this.findEquipmentForCard(playerId, currentCard);
            return eq ? eq.turns_equipped : 0;
        }
        if (ref === 'durability') return currentCard ? toInt(currentCard.durability, 0) : 0;
        return fallbackValue;
    }

    evalInt(playerId, expr, currentCard = null, fallbackValue = 0) {
        return toInt(this.scalarValue(this.evalExpr(playerId, expr, currentCard, fallbackValue), fallbackValue), fallbackValue);
    }

    evalCondition(playerId, cond, currentCard = null) {
        cond = parseJsonish(cond);
        if (!cond) return false;
        if (typeof cond === 'boolean') return cond;
        if (typeof cond === 'string') return cond === 'true' || cond === 'True';
        const op = cond.op || cond.type || '';
        if (op === 'compare') {
            const a = this.evalExpr(playerId, cond.a, currentCard, 0);
            const b = this.evalExpr(playerId, cond.b, currentCard, 0);
            const operator = cond.operator || '==';
            if (operator === '>') return a > b;
            if (operator === '>=') return a >= b;
            if (operator === '<') return a < b;
            if (operator === '<=') return a <= b;
            if (operator === '!=' || operator === '!==') return a !== b;
            return a === b;
        }
        if (op === 'var_compare') {
            const store = this.varStoreForTarget(playerId, cond.target || 'self');
            return this.evalCondition(playerId, {
                op: 'compare',
                a: toInt(this.scalarValue(store[String(cond.name || 'var')], 0), 0),
                operator: cond.operator || '==',
                b: cond.value ?? cond.b ?? 0,
            }, currentCard);
        }
        if (op === 'list_contains') {
            const values = this.evalList(playerId, cond.list || [], currentCard);
            const item = this.serializableListItem(this.evalRawItem(playerId, cond.item ?? 0, currentCard));
            return values.some(value => this.sameListItem(value, item));
        }
        if (op === 'and') {
            const conditions = cond.conditions || [cond.a, cond.b];
            return conditions.every(c => this.evalCondition(playerId, c, currentCard));
        }
        if (op === 'or') {
            const conditions = cond.conditions || [cond.a, cond.b];
            return conditions.some(c => this.evalCondition(playerId, c, currentCard));
        }
        if (op === 'not') return !this.evalCondition(playerId, cond.condition ?? cond.value, currentCard);
        if (op === 'has_status_named' || op === 'has_status') {
            const tid = this.resolveTarget(playerId, cond.target || 'self');
            const status = cond.status || cond.name;
            return this.statusCount(tid, status) > 0;
        }
        if (op === 'has_tag') {
            const targetCard = this.resolveCardRef(playerId, cond.card || { ref: 'current_card' }, currentCard);
            if (!targetCard) return false;
            const tag = normalizeCardFlag(cond.tag || '');
            return targetCard.flags.has(tag);
        }
        if (op === 'damage_source_relation') {
            const context = this._active_effect_context || {};
            const sourceId = toInt(context.source_id, playerId);
            const targetId = toInt(context.target_id, playerId);
            const relation = String(cond.relation || 'any');
            if (relation === 'any') return sourceId >= 0 && sourceId < this.players.length;
            if (relation === 'self') return sourceId === targetId;
            const sameSide = sourceId === targetId;
            if (relation === 'friendly' || relation === 'ally') return sameSide && sourceId !== targetId;
            if (relation === 'same_side') return sameSide;
            if (relation === 'enemy') return sourceId !== targetId;
            return false;
        }
        if (op === 'event_card_type') {
            const expected = String(cond.card_type || 'any');
            const actual = String((this._active_effect_context || {}).event_card_type || '');
            return expected === 'any' || expected === actual;
        }
        if (op === 'hand_full') {
            const tid = this.resolveTarget(playerId, cond.target || 'self');
            return !(this.players[tid] || this.players[playerId]).canAddToHand();
        }
        if (op === 'zone_contains') {
            const tid = this.resolveTarget(playerId, cond.target || 'self');
            const ps = this.players[tid] || this.players[playerId];
            const zone = ps[cond.zone || 'hand'] || [];
            return zone.some(card => card.def_id === cond.card_id);
        }
        return !!this.evalExpr(playerId, cond, currentCard, 0);
    }

    eventRelationMatches(listenerOwner, actorId, relation) {
        relation = String(relation || 'any');
        if (['any', 'all', 'both'].includes(relation)) return actorId >= 0 && actorId < this.players.length;
        if (['self', 'owner'].includes(relation)) return actorId === listenerOwner;
        if (['teammate', 'ally'].includes(relation)) return false;
        if (['friendly', 'same_side'].includes(relation)) return actorId === listenerOwner;
        if (relation === 'enemy') return actorId !== listenerOwner && actorId >= 0 && actorId < this.players.length;
        return false;
    }

    eventWrapperMatches(ownerId, eventName, params = {}, context = {}) {
        let actorId = toInt(context.source_id, ownerId);
        if (eventName === 'equipment_destroyed') actorId = toInt(context.target_id, actorId);
        if (eventName === 'player_stat_changed') actorId = toInt(context.target_id, actorId);
        if (!this.eventRelationMatches(ownerId, actorId, params.relation || 'any')) return false;
        if (eventName === 'card_used') {
            const expected = String(params.card_type || 'any');
            const actual = String(context.event_card_type || '');
            if (expected !== 'any' && expected !== actual) return false;
        }
        if (eventName === 'resource_spent') {
            const expectedResource = String(params.resource || 'elixir');
            const actualResource = String(context.resource || '');
            if (expectedResource !== actualResource) return false;
            const threshold = Math.max(1, this.evalInt(ownerId, params.amount ?? 1, null, 1));
            if (toInt(context.amount, 0) < threshold) return false;
        }
        if (eventName === 'player_stat_changed') {
            const expectedProp = String(params.property || 'health');
            const actualProp = String(context.property || '');
            if (expectedProp !== actualProp) return false;
            const expectedDirection = String(params.direction || 'change');
            const actualDirection = String(context.direction || 'change');
            if (expectedDirection !== 'change' && expectedDirection !== actualDirection) return false;
        }
        return true;
    }

    playerPropertyValue(targetId, property) {
        const prop = String(property || 'health');
        if (targetId < 0) {
            return this.players.reduce((sum, _, idx) => sum + this.playerPropertyValue(idx, prop), 0);
        }
        const ps = this.players[targetId];
        if (!ps) return 0;
        if (prop === 'health') return toInt(ps.health, 0);
        if (prop === 'max_health') return toInt(ps.max_health, 0);
        if (prop === 'elixir' || prop === 'energy') return toInt(ps.elixir, 0);
        if (prop === 'max_elixir' || prop === 'max_energy') return toInt(ps.max_elixir, 0);
        if (prop === 'magic') return toInt(ps.magic, 0);
        if (prop === 'max_magic') return toInt(ps.max_magic, 0);
        if (prop === 'hand_limit') return ps.handLimit();
        if (prop === 'hand_size') return ps.hand.length;
        if (prop === 'deck_remaining' || prop === 'deck_count') return ps.deck.length;
        if (prop === 'discard_size' || prop === 'discard_count') return ps.discard.length;
        if (prop === 'exile_size' || prop === 'exile_count') return ps.exile.length;
        if (prop === 'equip_count' || prop === 'equipment_count') return ps.equipment.length;
        const statusProps = new Set([
            'dodge', 'poison', 'fire', 'vulnerable', 'toxic', 'equipment_protection',
            'attack_blocked', 'attack_only', 'enemy_draw_reduction', 'enemy_e_reduction',
            'nazar_big_hits', 'sluggish', 'overload', 'foresight', 'fracture', 'stagnation',
            'blind', 'heal_block', 'weakness', 'bleed', 'skip_turn',
            'invincible', 'untargetable', 'bandage_active', 'sponge_active', 'shovel_active',
            'negate_next_skill', 'nazar_active',
        ]);
        if (this.isStatusImmune(targetId) && statusProps.has(prop)) return 0;
        return toInt(ps[prop], 0);
    }

    setPlayerPropertyValue(targetId, property, value) {
        const ps = this.players[targetId];
        if (!ps) return;
        let prop = String(property || 'health');
        if (prop === 'energy') prop = 'elixir';
        if (prop === 'max_energy') prop = 'max_elixir';
        const next = Math.max(0, toInt(value, 0));
        const statusProps = new Set([
            'poison', 'fire', 'vulnerable', 'toxic', 'equipment_protection',
            'attack_blocked', 'attack_only', 'enemy_draw_reduction', 'enemy_e_reduction',
            'nazar_big_hits', 'sluggish', 'overload', 'foresight', 'fracture', 'stagnation',
            'blind', 'heal_block', 'weakness', 'bleed', 'skip_turn',
            'invincible', 'untargetable', 'bandage_active', 'sponge_active', 'shovel_active',
            'negate_next_skill', 'nazar_active',
        ]);
        if (next > 0 && this.isStatusImmune(targetId) && statusProps.has(prop)) return;
        if (prop === 'hand_limit') {
            const golden = ps.equipment.filter(eq => eq.def_id === 'GoldenLeaf' && (eq.effect_target ?? targetId) === targetId).length;
            ps.extra_hand_limit_bonus = Math.max(0, next - HAND_LIMIT - golden);
            return;
        }
        if (prop === 'hand_limit_bonus') {
            ps.extra_hand_limit_bonus = next;
            return;
        }
        ps[prop] = next;
        if (prop === 'max_health') {
            ps.base_max_health = next;
            ps.health = Math.min(ps.health, ps.max_health);
        } else if (prop === 'max_elixir') {
            ps.elixir = Math.min(ps.elixir, ps.max_elixir);
        } else if (prop === 'max_magic') {
            ps.magic = Math.min(ps.magic, ps.max_magic);
        }
    }

    snapshotPlayerStats() {
        return this.players.map((_, playerId) => {
            const stats = {};
            TRACKED_PLAYER_STATS.forEach(prop => { stats[prop] = this.playerPropertyValue(playerId, prop); });
            return stats;
        });
    }

    dispatchPlayerStatChanges(before, sourceId, sourceCard = null) {
        if (!Array.isArray(before)) return;
        const depth = toInt(this._stat_change_event_depth, 0);
        if (depth >= 4) return;
        this._stat_change_event_depth = depth + 1;
        try {
            before.slice(0, this.players.length).forEach((stats, playerId) => {
                Object.entries(stats || {}).forEach(([property, oldValue]) => {
                    const newValue = this.playerPropertyValue(playerId, property);
                    if (newValue === oldValue) return;
                    this.dispatchCardEvent('player_stat_changed', sourceId, sourceCard, playerId, null, null, null, {
                        property,
                        old_value: oldValue,
                        new_value: newValue,
                        delta: newValue - oldValue,
                        direction: newValue > oldValue ? 'increase' : 'decrease',
                    });
                });
            });
        } finally {
            this._stat_change_event_depth = depth;
        }
    }

    resourceEventRepeatCount(ownerId, params = {}, context = {}) {
        const amount = toInt(context.amount, 0);
        const threshold = Math.max(1, this.evalInt(ownerId, params.amount ?? 1, null, 1));
        return Math.max(1, Math.floor(amount / threshold));
    }

    spendResource(playerId, resource, amount, sourceCard = null) {
        const ps = this.players[playerId];
        if (!ps) return 0;
        const attr = resource === 'magic' ? 'magic' : 'elixir';
        const requested = Math.max(0, toInt(amount, 0));
        if (requested <= 0) return 0;
        const before = this.snapshotPlayerStats();
        const actual = Math.min(requested, toInt(ps[attr], 0));
        ps[attr] = Math.max(0, toInt(ps[attr], 0) - requested);
        if (actual > 0) {
            this.dispatchCardEvent('resource_spent', playerId, sourceCard, playerId, null, null, null, {
                resource: attr,
                amount: actual,
            });
        }
        this.dispatchPlayerStatChanges(before, playerId, sourceCard);
        return actual;
    }

    paidEForRefund(playerId, card) {
        if (!card) return 0;
        if (card._paid_e_this_play != null) return Math.max(0, toInt(card._paid_e_this_play, 0));
        return Math.max(0, toInt(card.cost_e, 0) + this.getExtraEForCard(playerId, card));
    }

    mimicSpecialCostForCard(target) {
        if (!target) return 0;
        const fusionExtra = Math.max(0, toInt(target.fusion_level, 1) - 1);
        const fissionExtra = Math.max(0, toInt(target.fission_level, 1) - 1);
        const layered = ['swift_value', 'magic_swift_value', 'power_value', 'bonus_damage', 'temp_swift_value', 'temp_heavy_value', 'temp_magic_heavy_value']
            .reduce((sum, key) => sum + Math.max(0, toInt(target[key], 0)), 0);
        return Math.ceil((fusionExtra + fissionExtra + layered) / 2);
    }

    canPayMimicSpecialCost(playerId, target) {
        const ps = this.players[playerId];
        if (!ps) return false;
        return toInt(ps.elixir, 0) >= this.mimicSpecialCostForCard(target);
    }

    payMimicSpecialCost(playerId, target, sourceCard = null) {
        const cost = this.mimicSpecialCostForCard(target);
        if (cost <= 0) return true;
        if (!this.canPayMimicSpecialCost(playerId, target)) return false;
        this.spendResource(playerId, 'elixir', cost, sourceCard);
        return true;
    }

    equipmentTriggerMaxUses(eq) {
        if (!eq || !eq.card_def) return 0;
        for (const effect of eq.card_def.effects || []) {
            if (!effect || effect.type !== 'on_equipment_trigger') continue;
            const params = effect.params || {};
            return Math.max(0, toInt(params.max_uses_per_turn ?? params.max_uses ?? 0, 0));
        }
        return 0;
    }

    iterEventListenerCards() {
        const out = [];
        const seen = new Set();
        this.players.forEach((ps, ownerId) => {
            ps.equipment.slice().forEach(eq => {
                const card = eq && eq.card_instance;
                if (!card || seen.has(card.instance_id)) return;
                seen.add(card.instance_id);
                out.push({ ownerId, card, equipment: eq });
            });
            ps.hand.slice().forEach(card => {
                if (!card || seen.has(card.instance_id)) return;
                seen.add(card.instance_id);
                out.push({ ownerId, card, equipment: null });
            });
        });
        return out;
    }

    dispatchCardEvent(eventName, sourceId, eventCard = null, targetId = null, equipment = null, equipmentOwnerId = null, choice = null, extraContext = null) {
        const eventCardId = eventCard && eventCard.instance_id;
        const context = {
            source_id: sourceId,
            target_id: targetId == null ? sourceId : targetId,
            event_card_instance_id: eventCardId,
            event_card_def_id: eventCard ? eventCard.def_id : '',
            event_card_type: eventCard ? eventCard.card_type : '',
            event_card_cost_e: eventCard ? toInt(eventCard._paid_e_this_play ?? eventCard.cost_e, 0) : 0,
            event_card_cost_m: eventCard ? toInt(eventCard._paid_m_this_play ?? eventCard.cost_m, 0) : 0,
        };
        if (equipment) {
            context.selected_equipment_instance_id = equipment.card_instance && equipment.card_instance.instance_id;
            context.selected_equipment_owner_id = equipmentOwnerId == null ? sourceId : equipmentOwnerId;
        }
        if (extraContext && typeof extraContext === 'object') Object.assign(context, extraContext);
        this.iterEventListenerCards().forEach(({ ownerId, card }) => {
            if (card.instance_id === eventCardId) return;
            if (!this.hasCardEvent(card.def(), eventName)) return;
            this.runCardEvent(ownerId, card, eventName, choice, context);
        });
    }

    runCardEvent(ownerId, card, eventName, choice = null, extraContext = {}) {
        const def = card.def();
        const effects = getScriptEffects(def, eventName);
        if (effects.length) {
            this.runEffectList(ownerId, card, effects, choice, { event: eventName, ...extraContext, listener_owner_id: ownerId });
            return true;
        }
        const eventType = `on_${eventName}`;
        let ran = false;
        ((def && def.effects) || []).forEach(effect => {
            if (!effect || effect.type !== eventType) return;
            const params = effect.params || {};
            if (!this.eventWrapperMatches(ownerId, eventName, params, extraContext)) return;
            const repeatCount = eventName === 'resource_spent' ? this.resourceEventRepeatCount(ownerId, params, extraContext) : 1;
            for (let repeatIndex = 0; repeatIndex < repeatCount; repeatIndex++) {
                this.runEffectList(ownerId, card, params.effects || [], choice, {
                    event: eventName,
                    repeat_index: repeatIndex + 1,
                    ...extraContext,
                    listener_owner_id: ownerId,
                });
            }
            ran = true;
        });
        return ran;
    }

    runEffectList(playerId, card, effects, choice = null, context = {}) {
        const prevChoice = this._active_choice;
        const prevContext = this._active_effect_context;
        this._active_choice = choice || {};
        this._active_effect_context = { ...(prevContext || {}), ...(context || {}) };
        try {
            for (const effect of (effects || [])) {
                const type = effect && typeof effect === 'object' ? String(effect.type || '') : String(effect || '');
                const params = effect && typeof effect === 'object' ? (effect.params || {}) : {};
                if (choice && choice.cancelled && ['request_target', 'request_card', 'request_confirm'].includes(type) && !params.continue_on_cancel) {
                    break;
                }
                this.runOneEffect(playerId, card, effect, choice);
            }
        } finally {
            this._active_choice = prevChoice;
            this._active_effect_context = prevContext;
        }
    }

    timerTriggerMatches(entry, currentPlayer) {
        const trigger = String(entry.trigger || 'target_turn_start');
        const ownerId = toInt(entry.owner_id, currentPlayer);
        const targetId = toInt(entry.target_id, ownerId);
        if (trigger === 'target_turn_start' || trigger === 'turn_start') return currentPlayer === targetId;
        if (trigger === 'owner_turn_start') return currentPlayer === ownerId;
        if (trigger === 'friendly_turn_start') return currentPlayer === ownerId;
        if (trigger === 'enemy_turn_start') return currentPlayer !== ownerId;
        if (trigger === 'any_turn_start') return true;
        return false;
    }

    timerTargets(playerId, target) {
        if (target === 'global' || target === 'team') return [playerId];
        const ids = this.resolveTargets(playerId, target || 'self').filter(id => id >= 0 && id < this.players.length);
        return ids.length ? ids : [playerId];
    }

    registerTimedEffect(ownerId, targetId, trigger, duration, effects, card = null) {
        duration = Math.max(1, Math.min(toInt(duration, 1), 999));
        if (!Array.isArray(effects) || !effects.length) return;
        this.timed_effects = Array.isArray(this.timed_effects) ? this.timed_effects : [];
        const entry = {
            owner_id: ownerId,
            target_id: targetId,
            trigger: trigger || 'target_turn_start',
            remaining: duration,
            effects: deepClone(effects),
        };
        if (card && card.instance_id != null) entry.card_instance_id = card.instance_id;
        this.timed_effects.push(entry);
        if (this.timed_effects.length > 200) {
            this.timed_effects = this.timed_effects.slice(-200);
        }
    }

    runTimedEffectsForTurn(currentPlayer) {
        if (!Array.isArray(this.timed_effects) || !this.timed_effects.length) return;
        const kept = [];
        [...this.timed_effects].forEach(entry => {
            if (!entry || typeof entry !== 'object') return;
            if (!this.timerTriggerMatches(entry, currentPlayer)) {
                kept.push(entry);
                return;
            }
            const ownerId = toInt(entry.owner_id, currentPlayer);
            const targetId = toInt(entry.target_id, ownerId);
            const remaining = toInt(entry.remaining, 0);
            const timerCard = entry.card_instance_id != null ? this.findCardByInstanceId(entry.card_instance_id) : null;
            this.runEffectList(ownerId, timerCard, entry.effects || [], null, {
                event: 'timed_effect',
                source_id: ownerId,
                target_id: targetId,
                timer_current_player: currentPlayer,
                timer_remaining: remaining,
            });
            entry.remaining = remaining - 1;
            if (entry.remaining > 0) kept.push(entry);
        });
        this.timed_effects = kept;
    }

    runOneEffect(playerId, card, effect, choice) {
        if (!effect || typeof effect !== 'object') return;
        const type = effect.type || '';
        if (EVENT_EFFECT_TYPES.has(type)) return;
        const params = effect.params || {};
        const log = effect.log || '';
        const aliases = {
            damage: 'deal_damage',
            add_armor: 'gain_armor',
            poison: 'apply_poison',
            burn: 'apply_burn',
            toxic: 'apply_toxic',
            vulnus: 'apply_vulnerable',
        };
        const name = aliases[type] || type;
        const handler = this[`effect_${name}`];
        const statWrapperSkip = new Set([
            'if', 'if_else', 'repeat', 'repeat_until', 'for_each', 'for_each_selected_card',
            'for_each_list', 'timed_effect', 'countdown_var', 'cost_e', 'cost_m',
        ]);
        try {
            const beforeStats = this.snapshotPlayerStats();
            if (typeof handler === 'function') handler.call(this, playerId, card, params, log, choice);
            else if (log) this.logMsg(log);
            else throw new Error(`Unknown effect: ${type}`);
            if (!statWrapperSkip.has(name)) this.dispatchPlayerStatChanges(beforeStats, playerId, card);
        } catch (err) {
            if (err instanceof ModLoopBreak || err instanceof ModLoopContinue) throw err;
            this.logMsg(MOD_RUNTIME_ERROR_MESSAGE);
            console.error('[mod-runtime-error]', type, err);
        }
    }

    effect_if(playerId, card, params, log, choice) {
        const branch = this.evalCondition(playerId, params.condition, card) ? params.then : params.else;
        this.runEffectList(playerId, card, branch || [], choice, this._active_effect_context);
    }

    effect_if_else(playerId, card, params, log, choice) {
        this.effect_if(playerId, card, params, log, choice);
    }

    effect_repeat(playerId, card, params, log, choice) {
        const times = Math.max(0, this.evalInt(playerId, params.times || params.count, card, 1));
        for (let i = 0; i < times; i++) {
            try {
                this.runEffectList(playerId, card, params.body || params.effects || [], choice, {
                    ...this._active_effect_context,
                    repeat_index: i + 1,
                });
            } catch (err) {
                if (err instanceof ModLoopContinue) continue;
                if (err instanceof ModLoopBreak) break;
                throw err;
            }
        }
    }

    effect_repeat_until(playerId, card, params, log, choice) {
        const body = params.body || params.effects || [];
        let loops = 0;
        while (loops < 64 && !this.evalCondition(playerId, params.condition, card)) {
            try {
                this.runEffectList(playerId, card, body, choice, {
                    ...this._active_effect_context,
                    repeat_index: loops + 1,
                });
            } catch (err) {
                if (err instanceof ModLoopContinue) {
                    loops += 1;
                    continue;
                }
                if (err instanceof ModLoopBreak) break;
                throw err;
            }
            loops += 1;
        }
    }

    effect_for_each(playerId, card, params, log, choice) {
        const targets = this.resolveTargets(playerId, params.targets || 'friendly');
        for (const [idx, targetId] of targets.entries()) {
            try {
                this.runEffectList(targetId, card, params.body || [], choice, {
                    ...this._active_effect_context,
                    loop_player_id: targetId,
                    loop_index: idx + 1,
                });
            } catch (err) {
                if (err instanceof ModLoopContinue) continue;
                if (err instanceof ModLoopBreak) break;
                throw err;
            }
        }
    }

    effect_for_each_selected_card(playerId, card, params, log, choice) {
        const ids = Array.isArray((choice || {}).target_instance_ids)
            ? choice.target_instance_ids
            : ((choice || {}).target_instance_id != null ? [choice.target_instance_id] : []);
        for (const [idx, id] of ids.entries()) {
            try {
                this.runEffectList(playerId, card, params.body || [], { ...(choice || {}), target_instance_id: id }, {
                    ...this._active_effect_context,
                    selected_card_index: idx + 1,
                });
            } catch (err) {
                if (err instanceof ModLoopContinue) continue;
                if (err instanceof ModLoopBreak) break;
                throw err;
            }
        }
    }

    effect_for_each_list(playerId, card, params, log, choice) {
        const name = String(params.name || 'item');
        const store = this.varStoreForTarget(playerId, params.target || 'self');
        const hadOld = Object.prototype.hasOwnProperty.call(store, name);
        const oldValue = store[name];
        try {
            const values = this.evalList(playerId, params.list || [], card);
            for (const [idx, item] of values.entries()) {
                store[name] = this.serializableListItem(item);
                try {
                    this.runEffectList(playerId, card, params.body || [], choice, {
                        ...this._active_effect_context,
                        list_index: idx + 1,
                    });
                } catch (err) {
                    if (err instanceof ModLoopContinue) continue;
                    if (err instanceof ModLoopBreak) break;
                    throw err;
                }
            }
        } finally {
            if (hadOld) store[name] = oldValue;
            else delete store[name];
        }
    }

    equipmentMatchesLoopFilter(playerId, eq, params, card) {
        const filter = String(params.filter || 'all');
        if (filter === 'all' || filter === 'any') return true;
        if (filter === 'destroyable') return !eq.card_instance.flags.has('indestructible');
        if (filter === 'indestructible') return eq.card_instance.flags.has('indestructible');
        if (filter === 'named' || filter === 'card_id') {
            const expected = params.card ? this.resolveCardIdRef(playerId, params.card, card) : String(params.card_id || '');
            return !!expected && eq.def_id === expected;
        }
        if (filter === 'current_target' || filter === 'effect_target') {
            const targetId = this.resolveTarget(playerId, params.effect_target ?? params.target ?? 'self');
            return toInt(eq.effect_target ?? eq.owner, -1) === targetId;
        }
        return true;
    }

    effect_for_each_equipment(playerId, card, params, log, choice) {
        const items = [];
        this.resolveTargets(playerId, params.target || 'self').forEach(targetId => {
            const ps = this.players[targetId];
            if (!ps) return;
            ps.equipment.forEach(eq => {
                if (this.equipmentMatchesLoopFilter(playerId, eq, params, card)) items.push({ ownerId: targetId, eq });
            });
        });
        for (const [idx, item] of items.entries()) {
            try {
                this.runEffectList(playerId, card, params.body || [], choice, {
                    ...this._active_effect_context,
                    selected_equipment_instance_id: item.eq.card_instance.instance_id,
                    selected_equipment_owner_id: item.ownerId,
                    equipment_index: idx + 1,
                });
            } catch (err) {
                if (err instanceof ModLoopContinue) continue;
                if (err instanceof ModLoopBreak) break;
                throw err;
            }
        }
    }

    effect_break() {
        throw new ModLoopBreak();
    }

    effect_continue() {
        throw new ModLoopContinue();
    }

    effect_timed_effect(playerId, card, params) {
        const duration = this.evalInt(playerId, params.duration ?? params.turns ?? 1, card, 1);
        const effects = params.effects || params.body || [];
        this.timerTargets(playerId, params.target || 'self').forEach(targetId => {
            this.registerTimedEffect(playerId, targetId, params.trigger || 'target_turn_start', duration, effects, card);
        });
    }

    effect_countdown_var(playerId, card, params, log, choice) {
        const target = params.target || 'self';
        const name = String(params.name || 'timer');
        const duration = this.evalInt(playerId, params.duration ?? params.turns ?? 1, card, 1);
        this.effect_var_set(playerId, card, { target, name, value: duration }, log, choice);
        this.timerTargets(playerId, target).forEach(targetId => {
            const effectTarget = (target === 'global' || target === 'team') ? target : targetId;
            const effects = [{ type: 'var_sub', params: { target: effectTarget, name, value: 1 } }];
            this.registerTimedEffect(playerId, targetId, params.trigger || 'target_turn_start', duration, effects);
        });
    }

    effect_deal_damage(playerId, card, params, log = '') {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
        const amount = this.modifiedAttackDamage(this.evalInt(playerId, params.amount ?? 6, card, 6), card);
        const baseHits = this.evalInt(playerId, params.hits ?? 1, card, 1);
        const inheritExtraHits = params.inherit_extra_hits !== false && params.use_card_extra_hits !== false;
        const hits = inheritExtraHits ? this.cardTotalHits(card, baseHits) : Math.max(1, baseHits);
        this._incoming_damage_hint[targetId] = amount;
        const isPrecision = !!(params.is_precision || params.precision) || (card && card.flags && card.flags.has('precision'));
        const dealt = this.dealAttackDamage(targetId, amount, hits, isPrecision, playerId, card);
        this._last_damage_value[targetId] = dealt;
        const positiveHits = toInt((this._last_positive_damage_hits || [])[targetId], 0);
        const onHit = Array.isArray(params.on_hit) ? params.on_hit : [];
        if (dealt > 0 && positiveHits > 0 && onHit.length) {
            for (let i = 0; i < positiveHits; i += 1) {
                this.runEffectList(playerId, card, onHit, this._active_choice || {}, {
                    ...(this._active_effect_context || {}),
                    target_id: targetId,
                    last_damage: dealt,
                    hit_index: i + 1,
                });
            }
        }
        if (log) this.logMsg(log);
    }

    effect_ocean_magic_coral_tick(playerId, card, params, log) {
        const times = Math.max(1, this.evalInt(playerId, params.times ?? 1, card, 1));
        this.players.forEach(ps => {
            ps.custom_vars = ps.custom_vars || {};
            ps.custom_vars.ocean_action_skip_turns = Math.max(0, toInt(ps.custom_vars.ocean_action_skip_turns, 0)) + times;
        });
        if (log) this.logMsg(log);
    }

    oceanSelectableTargets(playerId, { allowSelf = false, enemiesOnly = false } = {}) {
        return this.players
            .map((ps, tid) => ({ ps, tid }))
            .filter(({ ps, tid }) => {
                if (!ps || toInt(ps.health, 0) <= 0 || ps.untargetable) return false;
                if (tid === playerId) return !!allowSelf;
                if (enemiesOnly) return tid !== playerId;
                return true;
            })
            .map(({ tid }) => tid);
    }

    effect_ocean_for_each_selectable_target(playerId, card, params, log, choice) {
        const body = Array.isArray(params.body) ? params.body : (Array.isArray(params.steps) ? params.steps : []);
        if (!body.length) return;
        const targets = this.wideStrikeTargetIds(playerId, card);
        targets.forEach(targetId => {
            if (this.game_over) return;
            const childChoice = { target_player_id: targetId, target_player: targetId, target_id: targetId };
            const childContext = {
                ...(this._active_effect_context || {}),
                target_id: targetId,
                target_player: targetId,
                choice: childChoice,
            };
            delete childContext.wide_strike_targets;
            delete childContext.target_players;
            this.runEffectList(playerId, card, body, childChoice, childContext);
        });
        if (log) this.logMsg(log);
    }

    effect_ocean_charge_self_damage(playerId, card, params, log) {
        const amount = Math.max(0, toInt(card && card.charge_value, 0));
        if (amount > 0) {
            this.dealDirectDamage(playerId, amount, '电荷', playerId, { damage_type: 'magic', damage_tag: 'battery' });
        }
        if (log) this.logMsg(log);
    }

    voidChoiceTarget(playerId, params = {}) {
        const targetId = this.resolveTarget(playerId, params.target || 'target');
        if (targetId >= 0 && targetId < this.players.length) return targetId;
        return this.resolveTarget(playerId, 'enemy');
    }

    voidDealAttackDamage(playerId, card, amount, params = {}) {
        const targetId = this.voidChoiceTarget(playerId, params);
        if (targetId < 0 || targetId >= this.players.length) return 0;
        const finalAmount = this.modifiedAttackDamage(Math.max(0, toInt(amount, 0)), card);
        const isPrecision = !!(params.is_precision || params.precision) || !!(card && card.flags && card.flags.has('precision'));
        this._incoming_damage_hint[targetId] = finalAmount;
        const dealt = this.dealAttackDamage(targetId, finalAmount, 1, isPrecision, playerId, card);
        this._last_damage_value[targetId] = dealt;
        return dealt;
    }

    voidPlayedCountBeforeCurrent(playerId) {
        const played = (this.players[playerId] && this.players[playerId].cards_played_this_turn) || {};
        return Math.max(0, Object.values(played).reduce((sum, value) => sum + toInt(value, 0), 0) - 1);
    }

    effect_void_turn_count_damage(playerId, card, params, log = '') {
        const base = this.evalInt(playerId, params.base ?? 6, card, 6);
        const per = this.evalInt(playerId, params.per ?? 4, card, 4);
        this.voidDealAttackDamage(playerId, card, Math.max(0, base + per * this.voidPlayedCountBeforeCurrent(playerId)), params);
        if (log) this.logMsg(log);
    }

    effect_void_magic_relativity_damage_end(playerId, card, params, log = '') {
        const base = this.evalInt(playerId, params.base ?? 28, card, 28);
        const per = this.evalInt(playerId, params.per ?? -5, card, -5);
        this.voidDealAttackDamage(playerId, card, Math.max(0, base + per * this.voidPlayedCountBeforeCurrent(playerId)), params);
        if (log) this.logMsg(log);
        this.endTurn(playerId);
    }

    effect_void_scythe_damage(playerId, card, params, log = '') {
        const base = this.evalInt(playerId, params.base ?? 40, card, 40);
        const per = this.evalInt(playerId, params.per_hand ?? 5, card, 5);
        const remaining = Math.max(0, ((this.players[playerId] || {}).hand || []).length);
        this.voidDealAttackDamage(playerId, card, Math.max(0, base - per * remaining), params);
        if (log) this.logMsg(log);
    }

    effect_void_magic_wing_damage(playerId, card, params, log = '') {
        const limit = Math.max(0, this.evalInt(playerId, params.extra_limit ?? 4, card, 4));
        const spend = Math.min(limit, Math.max(0, toInt((this.players[playerId] || {}).magic, 0)));
        if (spend > 0) this.spendResource(playerId, 'magic', spend, card);
        const base = this.evalInt(playerId, params.base ?? 4, card, 4);
        const per = this.evalInt(playerId, params.per ?? 4, card, 4);
        this.voidDealAttackDamage(playerId, card, base + spend * per, params);
        if (log) this.logMsg(log);
    }

    effect_void_antimatter_damage(playerId, card, params, log = '') {
        const ps = this.players[playerId];
        const lastDef = String((ps && (ps.custom_vars.void_current_previous_def_id || ps.custom_vars.void_last_played_def_id)) || '');
        if (lastDef === 'Antimatter' || lastDef === 'void:antimatter') {
            card.instance_flags.add('exile');
        }
        const amount = this.evalInt(playerId, params.amount ?? 10, card, 10);
        this.voidDealAttackDamage(playerId, card, amount, params);
        if (log) this.logMsg(log);
    }

    effect_void_damage_all_except_self(playerId, card, params, log = '') {
        const amount = this.evalInt(playerId, params.amount ?? 25, card, 25);
        this.players.forEach((ps, targetId) => {
            if (targetId === playerId || !ps || toInt(ps.health, 0) <= 0 || ps.untargetable) return;
            const finalAmount = this.modifiedAttackDamage(amount, card);
            this._incoming_damage_hint[targetId] = finalAmount;
            this.dealAttackDamage(targetId, finalAmount, 1, card && card.flags && card.flags.has('precision'), playerId, card);
        });
        if (log) this.logMsg(log);
    }

    voidResolveCardId(playerId, value, fallback = ERROR_CARD_ID, card = null) {
        const raw = this.resolveCardIdRef(playerId, value || fallback, card) || String(value || fallback || '');
        if (cardDef(raw)) return raw;
        const lowered = raw.toLowerCase();
        const fromNamespace = lowered.includes(':')
            ? lowered.split(':').pop().split(/[_\-\s]+/).filter(Boolean).map(part => part.charAt(0).toUpperCase() + part.slice(1)).join('')
            : '';
        return Object.keys(cardDefs).find(id => {
            const def = cardDef(id) || {};
            return id.toLowerCase() === lowered
                || String(def.legacy_id || '').toLowerCase() === lowered
                || (fromNamespace && id.toLowerCase() === fromNamespace.toLowerCase());
        }) || fallback;
    }

    voidZoneList(targetId, zoneName) {
        const ps = this.players[targetId];
        if (!ps) return [];
        if (zoneName === 'equipment') return ps.equipment.map(eq => eq.card_instance).filter(Boolean);
        return (ps[zoneName] || []).filter(Boolean);
    }

    voidSelectedZoneCard(targetId, zoneName, choice = null) {
        const zone = this.voidZoneList(targetId, zoneName);
        const selectedId = choice && choice.target_instance_id != null ? toInt(choice.target_instance_id, -1) : -1;
        if (selectedId >= 0) {
            const found = zone.find(card => card.instance_id === selectedId);
            if (found && !found.flags.has('exalted')) return found;
        }
        const selectedDef = choice && choice.target_def_id ? String(choice.target_def_id) : '';
        if (selectedDef) {
            const found = zone.find(card => card.def_id === selectedDef && cardSelectableByAction(card));
            if (found) return found;
        }
        return zone.find(card => cardSelectableByAction(card)) || null;
    }

    effect_void_add_void_to_hand(playerId, card, params, log = '') {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const target = this.players[targetId];
        if (!target || !target.canAddToHand()) return;
        const defId = this.voidResolveCardId(playerId, params.card || 'Void', 'Void', card);
        const newCard = new LocalCard(defId);
        target.addToHand(newCard);
        this._last_created_card_instance_id = newCard.instance_id;
        this._active_effect_context.last_created_card_instance_id = newCard.instance_id;
        if (log) this.logMsg(log);
    }

    effect_void_add_card_to_deck(playerId, card, params, log = '') {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const target = this.players[targetId];
        if (!target) return;
        const defId = this.voidResolveCardId(playerId, params.card || params.card_id || params.def_id || 'Void', 'Void', card);
        const newCard = new LocalCard(defId);
        this.applySetupModifiersToCard(targetId, newCard);
        if (params.position === 'random') target.deck.splice(Math.floor(Math.random() * (target.deck.length + 1)), 0, newCard);
        else if (params.position === 'bottom') target.deck.push(newCard);
        else target.deck.unshift(newCard);
        this._last_created_card_instance_id = newCard.instance_id;
        this._active_effect_context.last_created_card_instance_id = newCard.instance_id;
        if (log) this.logMsg(log);
    }

    effect_void_exile_target_hand(playerId, card, params, log = '') {
        const targetId = this.resolveTarget(playerId, params.target || 'target');
        const ps = this.players[targetId];
        if (!ps) return;
        const exiled = ps.hand.filter(handCard => !handCard.flags.has('exalted'));
        ps.hand = ps.hand.filter(handCard => handCard.flags.has('exalted'));
        exiled.forEach(handCard => this.putCardInExile(targetId, handCard));
        if (exiled.length > 0) {
            const keys = ['jungle:fragile', 'fragile'];
            const current = this.customStatusValue(targetId, ...keys);
            this.setCustomStatusAliasGroup(targetId, 'jungle:fragile', keys, current + exiled.length);
            this.logMsg(log || `${this.pn(targetId)}被放逐${exiled.length}张手牌并获得${exiled.length}层易损`);
            return;
        }
        if (log) this.logMsg(log);
    }

    effect_void_move_selected_card(playerId, card, params, log = '') {
        const targetId = this.resolveTarget(playerId, params.target || 'target');
        const fromZone = String(params.from_zone || params.zone || 'discard');
        const toZone = String(params.to_zone || 'deck_top');
        const selected = this.voidSelectedZoneCard(targetId, fromZone, this._active_choice || {});
        if (!selected) return;
        const loc = this.removeCardFromCurrentZone(selected);
        if (!loc) return;
        const ps = this.players[targetId] || this.players[loc.ownerId];
        if (!ps) return;
        if (toZone === 'hand') ps.addToHand(selected);
        else if (toZone === 'discard') this.discardCard(ps, selected);
        else if (toZone === 'exile') this.putCardInExile(targetId, selected);
        else if (toZone === 'deck_bottom') ps.deck.push(selected);
        else if (toZone === 'deck_random') ps.deck.splice(Math.floor(Math.random() * (ps.deck.length + 1)), 0, selected);
        else ps.deck.unshift(selected);
        if (log) this.logMsg(log);
    }

    effect_void_give_selected_hand_flag(playerId, card, params, log = '') {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const selected = this.voidSelectedZoneCard(targetId, 'hand', this._active_choice || {});
        const flag = normalizeCardFlag(params.flag || 'floating');
        if (selected && flag) selected.instance_flags.add(flag);
        if (log) this.logMsg(log);
    }

    effect_void_copy_response_card(playerId, card, params, log = '') {
        const original = this.resolveCardRef(playerId, { ref: 'event_card' }, card) || (this._active_effect_context || {}).original_card;
        if (!original || !this.players[playerId].canAddToHand()) return;
        const copy = original.copy ? original.copy() : new LocalCard(original.def_id);
        copy.instance_flags.add('exile');
        this.players[playerId].addToHand(copy);
        this._last_created_card_instance_id = copy.instance_id;
        this._active_effect_context.last_created_card_instance_id = copy.instance_id;
        if (log) this.logMsg(log);
    }

    effect_void_add_temp_heavy_to_hand(playerId, card, params, log = '') {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const amount = Math.max(0, this.evalInt(playerId, params.amount ?? 1, card, 1));
        const kind = String(params.kind || 'e');
        (this.players[targetId]?.hand || []).forEach(handCard => {
            if (kind === 'm') {
                handCard.temp_magic_heavy_value = toInt(handCard.temp_magic_heavy_value, 0) + amount;
                handCard.instance_flags.add('temp_magic_heavy');
            } else {
                handCard.temp_heavy_value = toInt(handCard.temp_heavy_value, 0) + amount;
                handCard.instance_flags.add('temp_heavy');
            }
        });
        if (log) this.logMsg(log);
    }

    effect_void_quantum_randomize(playerId, card, params, log = '') {
        const maxCost = Math.max(0, this.evalInt(playerId, params.max_cost ?? 3, card, 3));
        (this.players[playerId]?.hand || []).forEach(handCard => {
            if (toInt(handCard.def().cost_e, 0) <= maxCost) handCard.cost_e_override = Math.floor(Math.random() * (maxCost + 1));
        });
        if (log) this.logMsg(log);
    }

    effect_void_toggle_void_hand(playerId, card, params, log = '') {
        const targetId = this.resolveTarget(playerId, params.target || 'target');
        (this.players[targetId]?.hand || []).forEach(handCard => {
            if (handCard.flags.has('void')) {
                handCard.instance_flags.delete('void');
                handCard.disabled_flags.add('void');
            } else {
                handCard.instance_flags.add('void');
                handCard.disabled_flags.delete('void');
            }
        });
        if (log) this.logMsg(log);
    }

    effect_void_set_void_all_cards(playerId, card, params, log = '') {
        const targetId = this.resolveTarget(playerId, params.target || 'target');
        const enabled = params.enabled !== false;
        const ps = this.players[targetId];
        if (!ps) return;
        ['hand', 'deck', 'discard'].forEach(zone => {
            ps[zone].forEach(zoneCard => {
                if (enabled) {
                    zoneCard.instance_flags.add('void');
                    zoneCard.disabled_flags.delete('void');
                } else {
                    zoneCard.instance_flags.delete('void');
                    zoneCard.disabled_flags.add('void');
                }
            });
        });
        if (log) this.logMsg(log);
    }

    voidWeightedCardId(cardType, exclude = new Set()) {
        const pool = [];
        Object.entries(cardDefs).forEach(([id, def]) => {
            if (!def || def.card_type !== cardType || exclude.has(id)) return;
            const weight = Math.max(0, toInt(def.count, 0));
            for (let i = 0; i < weight; i += 1) pool.push(id);
        });
        if (!pool.length) return '';
        return pool[Math.floor(Math.random() * pool.length)];
    }

    effect_void_transform_own_cards(playerId, card, params, log = '') {
        const ps = this.players[playerId];
        if (!ps) return;
        ['hand', 'deck', 'discard'].forEach(zoneName => {
            ps[zoneName].forEach((oldCard, idx) => {
                const newId = this.voidWeightedCardId(oldCard.card_type, new Set([oldCard.def_id]));
                if (!newId) return;
                const newCard = new LocalCard(newId);
                this.applySetupModifiersToCard(playerId, newCard);
                ps[zoneName][idx] = newCard;
            });
        });
        ps.equipment.forEach(eq => {
            const oldCard = eq.card_instance;
            const newId = this.voidWeightedCardId('root', new Set([oldCard.def_id]));
            if (!newId) return;
            const armor = eq.armor;
            const target = eq.effect_target;
            eq.card_instance = new LocalCard(newId);
            this.applySetupModifiersToCard(playerId, eq.card_instance);
            eq.armor = armor;
            eq.effect_target = eq.card_instance.flags.has('self_only') ? playerId : target;
        });
        if (log) this.logMsg(log);
    }

    effect_void_satan_swap(playerId, card, params, log = '') {
        const targetId = this.resolveTarget(playerId, params.target || 'target');
        if (targetId < 0 || targetId >= this.players.length || targetId === playerId) return;
        const a = this.players[playerId];
        const b = this.players[targetId];
        const ah = a.health, ae = a.elixir, am = a.magic;
        a.health = Math.min(b.health, a.max_health);
        a.elixir = Math.min(b.elixir, a.max_elixir);
        a.magic = Math.min(b.magic, a.max_magic);
        b.health = Math.min(ah, b.max_health);
        b.elixir = Math.min(ae, b.max_elixir);
        b.magic = Math.min(am, b.max_magic);
        this.logMsg(log || `${this.pn(playerId)}与${this.pn(targetId)}交换了H/E/M`);
    }

    effect_void_exile_selected_card(playerId, card, params, log = '') {
        const targetId = this.resolveTarget(playerId, params.target || 'target');
        const zone = String(params.zone || 'hand');
        const selected = this.voidSelectedZoneCard(targetId, zone, this._active_choice || {});
        if (!selected) return;
        const loc = this.removeCardFromCurrentZone(selected);
        if (loc) this.putCardInExile(loc.ownerId, selected);
        const addDef = params.add_def_id || params.add_card || '';
        if (addDef) {
            const newId = this.voidResolveCardId(playerId, addDef, ERROR_CARD_ID, card);
            const newCard = new LocalCard(newId);
            this.applySetupModifiersToCard(targetId, newCard);
            if (zone === 'deck') this.players[targetId].deck.splice(Math.floor(Math.random() * (this.players[targetId].deck.length + 1)), 0, newCard);
            else this.players[targetId].addToHand(newCard);
        }
        if (log) this.logMsg(log);
    }

    effect_void_magic_corruption(playerId, card, params, log = '') {
        const targetId = this.resolveTarget(playerId, params.target || 'target');
        const ps = this.players[targetId];
        if (!ps) return;
        const newId = this.voidResolveCardId(playerId, 'Corruption', 'Corruption', card);
        const newCard = new LocalCard(newId);
        const eq = new LocalEquipment(newCard, targetId);
        eq.effect_target = targetId;
        eq.corruption_active = true;
        ps.equipment.push(eq);
        if (log) this.logMsg(log);
    }

    effect_void_kitty_auto_play(playerId, card, params, log = '') {
        const owner = this.players[playerId];
        if (!owner || toInt(owner.skip_turn, 0) > 0 || toInt(owner.forced_skip_turn, 0) > 0) return;
        const candidates = this.players.map((ps, id) => ({ ps, id })).filter(({ ps, id }) => id !== playerId && ps && toInt(ps.health, 0) > 0);
        if (!candidates.length) return;
        const actorId = candidates[Math.floor(Math.random() * candidates.length)].id;
        const actor = this.players[actorId];
        const topCard = (actor.deck || []).find(deckCard => !deckCard.flags.has('exalted'));
        if (!topCard) return;
        let targetId = -1;
        if (topCard.card_type === 'thorn' || (!topCard.flags.has('self_only') && (this.cardNeedsChoice(topCard) || topCard.card_type !== 'guard'))) {
            targetId = 1 - actorId;
            if (!this.players[targetId] || toInt(this.players[targetId].health, 0) <= 0 || this.players[targetId].untargetable) return;
        }
        const idx = actor.deck.indexOf(topCard);
        if (idx < 0) return;
        actor.deck.splice(idx, 1);
        actor.addToHand(topCard, { triggerEnterHand: false });
        const autoChoice = targetId >= 0 ? { target_player: targetId, target_player_id: targetId, target_id: targetId } : {};
        this.logMsg(log || `小猫使${this.pn(actorId)}自动打出${cardName(topCard.def_id)}`);
        const prevAutoActor = this.allowOutOfTurnAutoPlayFor;
        const prevAutoChoice = this._auto_resolve_choices_for;
        const prevAutoNoCost = this._auto_play_no_cost_for;
        this.allowOutOfTurnAutoPlayFor = actorId;
        this._auto_resolve_choices_for = actorId;
        this._auto_play_no_cost_for = actorId;
        try {
            this.playCard(actorId, topCard.instance_id, autoChoice);
        } finally {
            this.allowOutOfTurnAutoPlayFor = prevAutoActor;
            this._auto_resolve_choices_for = prevAutoChoice;
            this._auto_play_no_cost_for = prevAutoNoCost;
        }
    }

    effect_void_soap_wide_strike(playerId, card, params, log = '') {
        const targetId = this.resolveTarget(playerId, params.target || 'target');
        const ps = this.players[targetId];
        if (!ps) return;
        ['hand', 'deck', 'discard'].forEach(zone => {
            ps[zone].forEach(zoneCard => {
                if (zoneCard.card_type === 'thorn') zoneCard.instance_flags.add('wide_strike');
            });
        });
        if (log) this.logMsg(log);
    }

    effect_void_puppeteer(playerId, card, params, log = '') {
        const targetId = this.resolveTarget(playerId, params.target || 'target');
        const ps = this.players[targetId];
        if (!ps) return;
        ps.honey_control_turns = Math.max(1, toInt(ps.honey_control_turns, 0) + 1);
        ps.custom_vars.void_puppeteer_damage_multiplier = Math.max(Number(ps.custom_vars.void_puppeteer_damage_multiplier || 1), 1.5);
        ps.custom_vars.honey_lowest_enemy = true;
        if (log) this.logMsg(log);
    }

    effect_ocean_spikeball_damage(playerId, card, params, log) {
        const ps = this.players[playerId];
        const handCount = ps ? ps.hand.length : 0;
        const boosted = handCount < 4;
        if (boosted) {
            card.instance_flags.add('precision');
            card.instance_flags.add('wide_strike');
            card.instance_flags.add('ocean_spikeball_boosted');
        } else {
            card.instance_flags.delete('wide_strike');
            card.instance_flags.delete('ocean_spikeball_boosted');
        }
        const amount = this.modifiedAttackDamage(this.evalInt(playerId, boosted ? (params.boosted_amount ?? 20) : (params.amount ?? 6), card, boosted ? 20 : 6), card);
        const targets = boosted
            ? this.resolveTargets(playerId, 'both').filter(tid => tid >= 0 && tid < this.players.length && toInt(this.players[tid].health, 0) > 0 && !this.players[tid].untargetable)
            : [this.resolveTarget(playerId, params.target || 'target')].filter(tid => tid >= 0 && tid < this.players.length);
        targets.forEach(targetId => {
            this._incoming_damage_hint[targetId] = amount;
            this.dealAttackDamage(targetId, amount, 1, true, playerId, card);
        });
        if (log) this.logMsg(log);
    }

    effect_direct_damage(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
        const amount = this.evalInt(playerId, params.amount ?? 1, card, 1);
        const sourceText = String(params.source_text || params.source_name || params.label || params.source || (card ? cardName(card.def_id) : '\u6548\u679c'));
        this.dealDirectDamage(targetId, amount, sourceText, playerId, {
            damage_type: params.damage_type || null,
            damage_tag: params.damage_tag || null,
        });
    }

    effect_counter_pending_attack_damage(playerId, card, params, log = '') {
        const context = this._active_effect_context || {};
        let incoming = 0;
        const parts = context.incoming_damage_parts;
        if (Array.isArray(parts) && parts.length) incoming = toInt(parts[0], 0);
        if (incoming <= 0) incoming = toInt(context.first_damage ?? context.damage_amount ?? context.incoming_damage, 0);
        const ratio = Number(params.ratio ?? params.multiplier ?? 0.5) || 0;
        const amount = Math.max(0, Math.ceil(incoming * ratio));
        if (amount <= 0) return;
        const sourceText = String(params.source || params.source_text || (card ? cardName(card.def_id) : '\u53cd\u51fb'));
        const targetRef = params.target || 'target';
        const targets = (targetRef === 'all_enemies' || targetRef === 'enemies')
            ? [1 - playerId].filter(id => id >= 0 && id < this.players.length)
            : this.resolveTargets(playerId, targetRef);
        targets.forEach(targetId => {
            if (targetId < 0 || targetId >= this.players.length) return;
            if (String(params.mode || params.damage_mode || 'attack').toLowerCase() === 'direct') {
                this.dealDirectDamage(targetId, amount, sourceText, playerId, {
                    damage_type: params.damage_type || null,
                    damage_tag: params.damage_tag || null,
                });
            } else {
                this.dealAttackDamage(targetId, amount, 1, false, playerId, card);
            }
        });
        if (log) this.logMsg(log);
    }

    effect_lifesteal_damage(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
        const amount = this.modifiedAttackDamage(this.evalInt(playerId, params.amount ?? 8, card, 8), card);
        const isPrecision = !!params.is_precision || (card && card.flags && card.flags.has('precision'));
        const dealt = this.dealAttackDamage(targetId, amount, 1, isPrecision, playerId, card);
        this._last_damage_value[targetId] = dealt;
        if (dealt > 0) this.players[playerId].heal(this.evalInt(playerId, params.heal ?? 4, card, 4));
    }

    effect_heal(playerId, card, params) {
        this.resolveTargets(playerId, params.target || 'self').forEach(tid => {
            const amount = this.evalInt(playerId, params.amount ?? 0, card, 0);
            this.players[tid].heal(amount);
            this.logMsg(`${this.pn(tid)}回复${amount}H`);
        });
    }

    effect_draw(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const amount = this.evalInt(playerId, params.amount ?? 1, card, 1);
        const drawn = this.players[targetId].drawCards(amount);
        this.logMsg(`${this.pn(targetId)}抽${drawn.length}张牌`);
        this.applyElectricWebDrawDamage(targetId, drawn.length);
    }

    effect_draw_to_hand_limit(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const ps = this.players[targetId];
        if (!ps) return;
        const limit = Math.max(0, typeof ps.handLimit === 'function' ? ps.handLimit() : toInt(ps.hand_limit, 7));
        const amount = Math.max(0, limit - ps.hand.length);
        if (amount <= 0) {
            this.logMsg(`${this.pn(targetId)}没有抽牌`);
            return;
        }
        const drawn = ps.drawCards(amount);
        this.logMsg(`${this.pn(targetId)}抽${drawn.length}张牌`);
        this.applyElectricWebDrawDamage(targetId, drawn.length);
    }

    effect_gain_e(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const amount = this.evalInt(playerId, params.amount ?? 1, card, 1);
        this.players[targetId].gainElixir(amount);
        this.logMsg(`${this.pn(targetId)}获得${amount}E`);
    }

    effect_gain_m(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const amount = this.evalInt(playerId, params.amount ?? 1, card, 1);
        this.players[targetId].gainMagic(amount);
        this.logMsg(`${this.pn(targetId)}获得${amount}M`);
    }

    effect_magic_salt_reflect(playerId, card, params) {
        const context = this._active_effect_context || {};
        const ownerId = toInt(context.selected_equipment_owner_id ?? playerId, playerId);
        const attackerId = toInt(context.source_id, -1);
        const owner = this.players[ownerId];
        if (!owner || attackerId < 0 || attackerId >= this.players.length) return;
        if (this.pending_choice || this.pending_response) return;
        const costM = Math.max(0, this.evalInt(ownerId, params.cost_m ?? 1, card, 1));
        if (costM > 0 && owner.magic < costM) return;
        const damage = Math.max(0, toInt(context.damage, 0));
        if (damage <= 0) return;
        const ratio = Number(params.ratio ?? 0.5);
        const reflected = Math.max(0, Math.ceil(damage * ratio));
        if (reflected <= 0) return;
        this.pending_choice = {
            card: card.toDict(),
            player_id: ownerId,
            choice_type: 'magic_salt_reflect',
            choice_params: {
                owner_id: ownerId,
                attacker_id: attackerId,
                target_id: toInt(context.target_id, ownerId),
                damage,
                reflect: reflected,
                ratio,
                cost_m: costM,
                cancellable: true,
                title: '魔法盐',
                message: `是否支付${costM}M，对${this.pn(attackerId)}反弹${reflected}D？`,
                ok_text: '支付并反伤',
                cancel_text: '不触发',
            },
            already_paid: true,
            message: `是否支付${costM}M，对${this.pn(attackerId)}反弹${reflected}D？`,
        };
    }

    effect_gain_armor(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const amount = this.evalInt(playerId, params.amount ?? 1, card, 1);
        this.players[targetId].armor += amount;
        this.logMsg(`${this.pn(targetId)}获得${amount}护甲`);
    }

    effect_gain_dodge(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const amount = this.evalInt(playerId, params.amount ?? 1, card, 1);
        this.players[targetId].dodge += amount;
        this.logMsg(`${this.pn(targetId)}获得${amount}层闪避`);
    }

    effect_apply_poison(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
        if (this.statusApplicationBlocked(targetId, 'poison')) return;
        const amount = this.evalInt(playerId, params.amount ?? 1, card, 1);
        this.players[targetId].poison += amount;
        this.logMsg(`${this.pn(targetId)}+${amount}层中毒`);
    }

    effect_apply_burn(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
        if (this.statusApplicationBlocked(targetId, 'fire')) return;
        const amount = this.evalInt(playerId, params.amount ?? 1, card, 1);
        this.players[targetId].fire += amount;
        this.logMsg(`${this.pn(targetId)}+${amount}层灼烧`);
    }

    effect_apply_toxic(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
        if (this.statusApplicationBlocked(targetId, 'toxic')) return;
        const amount = this.evalInt(playerId, params.amount ?? 1, card, 1);
        this.players[targetId].toxic += amount;
        this.logMsg(`${this.pn(targetId)}+${amount}层淬毒`);
    }

    effect_apply_vulnerable(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
        if (this.statusApplicationBlocked(targetId, 'vulnerable')) return;
        const amount = this.evalInt(playerId, params.amount ?? 1, card, 1);
        this.players[targetId].vulnerable += amount;
    }

    effect_var_set(playerId, card, params) {
        const store = this.varStoreForTarget(playerId, params.target || 'self');
        const name = String(params.name || 'var');
        store[name] = this.evalVarAssignmentValue(playerId, params.value ?? 0, card);
        const tid = this.resolveTarget(playerId, params.target || 'self');
        if (name === '三角形层数') this.players[tid].triangle_stacks = store[name];
        if (name === '咖啡首次使用') this.players[tid].coffee_first_use = store[name] > 0;
        if (name === '魔法电池本回合回魔') this.players[tid].magic_battery_m_this_turn = store[name];
    }

    effect_var_add(playerId, card, params) {
        const store = this.varStoreForTarget(playerId, params.target || 'self');
        const name = String(params.name || 'var');
        store[name] = toInt(this.scalarValue(store[name], 0), 0) + this.evalInt(playerId, params.value ?? params.amount ?? 0, card, 0);
        if (name === '三角形层数') this.players[this.resolveTarget(playerId, params.target || 'self')].triangle_stacks = store[name];
    }

    effect_var_sub(playerId, card, params) {
        const store = this.varStoreForTarget(playerId, params.target || 'self');
        const name = String(params.name || 'var');
        store[name] = toInt(this.scalarValue(store[name], 0), 0) - this.evalInt(playerId, params.value ?? params.amount ?? 0, card, 0);
    }

    effect_var_mul(playerId, card, params) {
        const store = this.varStoreForTarget(playerId, params.target || 'self');
        const name = String(params.name || 'var');
        store[name] = toInt(this.scalarValue(store[name], 0), 0) * this.evalInt(playerId, params.value ?? params.amount ?? 1, card, 1);
    }

    effect_var_div(playerId, card, params) {
        const store = this.varStoreForTarget(playerId, params.target || 'self');
        const name = String(params.name || 'var');
        const div = this.evalInt(playerId, params.value ?? params.amount ?? 1, card, 1);
        const current = toInt(this.scalarValue(store[name], 0), 0);
        store[name] = div === 0 ? current : Math.trunc(current / div);
    }

    effect_list_set(playerId, card, params) {
        const targets = ['global', 'team'].includes(params.target) ? [params.target] : this.resolveTargets(playerId, params.target || 'self');
        targets.forEach(tid => {
            this.varStoreForTarget(playerId, tid)[String(params.name || 'list')] = this.evalList(playerId, params.list || [], card).map(v => this.serializableListItem(v));
        });
    }

    effect_list_append(playerId, card, params) {
        const targets = ['global', 'team'].includes(params.target) ? [params.target] : this.resolveTargets(playerId, params.target || 'self');
        targets.forEach(tid => {
            const store = this.varStoreForTarget(playerId, tid);
            const name = String(params.name || 'list');
            const current = Array.isArray(store[name]) ? store[name] : (store[name] == null ? [] : [store[name]]);
            current.push(this.serializableListItem(this.evalRawItem(playerId, params.item ?? 0, card)));
            store[name] = current;
        });
    }

    effect_list_insert(playerId, card, params) {
        const targets = ['global', 'team'].includes(params.target) ? [params.target] : this.resolveTargets(playerId, params.target || 'self');
        targets.forEach(tid => {
            const store = this.varStoreForTarget(playerId, tid);
            const name = String(params.name || 'list');
            const current = Array.isArray(store[name]) ? store[name] : (store[name] == null ? [] : [store[name]]);
            const idx = Math.max(0, Math.min(current.length, this.evalInt(playerId, params.index ?? 1, card, 1) - 1));
            current.splice(idx, 0, this.serializableListItem(this.evalRawItem(playerId, params.item ?? 0, card)));
            store[name] = current;
        });
    }

    effect_list_delete(playerId, card, params) {
        const targets = ['global', 'team'].includes(params.target) ? [params.target] : this.resolveTargets(playerId, params.target || 'self');
        targets.forEach(tid => {
            const store = this.varStoreForTarget(playerId, tid);
            const name = String(params.name || 'list');
            const current = Array.isArray(store[name]) ? store[name] : (store[name] == null ? [] : [store[name]]);
            const idx = this.evalInt(playerId, params.index ?? 1, card, 1) - 1;
            if (idx >= 0 && idx < current.length) current.splice(idx, 1);
            store[name] = current;
        });
    }

    effect_list_clear(playerId, card, params) {
        const targets = ['global', 'team'].includes(params.target) ? [params.target] : this.resolveTargets(playerId, params.target || 'self');
        targets.forEach(tid => {
            this.varStoreForTarget(playerId, tid)[String(params.name || 'list')] = [];
        });
    }

    effect_player_prop_set(playerId, card, params) {
        this.resolveTargets(playerId, params.target || 'self').forEach(tid => {
            const prop = String(params.property || 'health');
            const value = this.evalInt(playerId, params.value ?? 0, card, 0);
            this.setPlayerPropertyValue(tid, prop, value);
        });
    }

    effect_player_prop_add(playerId, card, params) {
        this.resolveTargets(playerId, params.target || 'self').forEach(tid => {
            const prop = String(params.property || 'health');
            const amount = this.evalInt(playerId, params.amount ?? params.value ?? 0, card, 0);
            this.setPlayerPropertyValue(tid, prop, this.playerPropertyValue(tid, prop) + amount);
        });
    }

    effect_add_equipment_armor(playerId, card, params, log) {
        const amount = this.evalInt(playerId, params.amount ?? 1, card, 1);
        this.resolveTargets(playerId, params.target || 'self').forEach(tid => {
            const ps = this.players[tid];
            if (!ps) return;
            let changed = 0;
            ps.equipment.forEach(eq => {
                if (eq.card_instance && eq.card_instance.flags && eq.card_instance.flags.has('indestructible')) return;
                eq.armor = Math.max(0, toInt(eq.armor, 0)) + amount;
                changed += 1;
            });
            if (changed > 0 && log) this.logMsg(log);
        });
    }

    effect_destroy_current_equipment(playerId, card, params, log) {
        const instanceId = card && card.instance_id;
        if (instanceId == null) return;
        for (let ownerId = 0; ownerId < this.players.length; ownerId += 1) {
            const eq = this.players[ownerId].equipment.find(item => item.card_instance && item.card_instance.instance_id === instanceId);
            if (eq) {
                const destroyed = this.destroyEquipment(ownerId, eq);
                if (destroyed && log) this.logMsg(log);
                return;
            }
        }
    }

    effect_give_magic_orb_to_hand(playerId, card, params, log) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const ps = this.players[targetId];
        if (!ps || !ps.canAddToHand()) return;
        const newCard = new LocalCard('ManaOrb');
        ['symbiosis', 'exile', 'void'].forEach(flag => newCard.instance_flags.add(flag));
        this.applySetupModifiersToCard(targetId, newCard);
        ps.addToHand(newCard);
        this._last_created_card_instance_id = newCard.instance_id;
        if (this._active_effect_context) {
            this._active_effect_context.last_created_card_instance_id = newCard.instance_id;
        }
        if (log) this.logMsg(log);
    }

    effect_cost_e(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const amount = this.evalInt(playerId, params.amount ?? params.value ?? 0, card, 0);
        this.spendResource(targetId, 'elixir', amount, card);
    }

    effect_cost_m(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const amount = this.evalInt(playerId, params.amount ?? params.value ?? 0, card, 0);
        this.spendResource(targetId, 'magic', amount, card);
    }

    effect_reduce_next_cost(playerId, card, params, log) {
        this.modifyHandCardCost(playerId, card, params, log, -1);
    }

    effect_increase_next_cost(playerId, card, params, log) {
        this.modifyHandCardCost(playerId, card, params, log, 1);
    }

    modifyHandCardCost(playerId, card, params, log, direction) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const target = this.players[targetId];
        if (!target) return;
        const amount = Math.abs(this.evalInt(playerId, params.amount ?? params.value ?? 1, card, 1));
        if (amount <= 0) return;
        const cardType = String(params.card_type || '').trim();
        let changed = 0;
        target.hand.forEach(handCard => {
            if (cardType && handCard.card_type !== cardType) return;
            if (direction < 0) {
                handCard.temp_swift_value = Math.max(0, toInt(handCard.temp_swift_value, 0)) + amount;
                handCard.instance_flags.add('temp_swift');
            } else {
                handCard.temp_heavy_value = Math.max(0, toInt(handCard.temp_heavy_value, 0)) + amount;
                handCard.instance_flags.add('temp_heavy');
            }
            changed += 1;
        });
        if (changed > 0 && log) this.logMsg(log);
    }

    clampCardProperty(target, prop, value) {
        let next = toInt(value, 0);
        if (prop === 'fusion_level' || prop === 'fission_level') {
            next = Math.max(1, next);
        } else {
            next = Math.max(0, next);
        }
        if (target && target.def_id === 'Tomato') {
            if (prop === 'held_turns') next = Math.min(6, next);
            if (prop === 'bonus_damage') next = Math.min(18, next);
            if (prop === 'power_value') next = Math.min(18, next);
        }
        return next;
    }

    syncCardSpecialPropertyFlag(target, prop, disableWhenZero = false) {
        if (!target) return;
        const mapping = {
            swift_value: 'swift',
            magic_swift_value: 'magic_swift',
            power_value: 'power',
            temp_swift_value: 'temp_swift',
            temp_heavy_value: 'temp_heavy',
            temp_magic_heavy_value: 'temp_magic_heavy',
        };
        const flag = mapping[prop];
        if (!flag) return;
        const value = Math.max(0, toInt(target[prop], 0));
        if (value > 0) {
            target.instance_flags.add(flag);
            target.disabled_flags.delete(flag);
        } else {
            target.instance_flags.delete(flag);
            if (disableWhenZero) target.disabled_flags.add(flag);
        }
    }

    effect_card_prop_set(playerId, card, params) {
        const target = this.resolveCardRef(playerId, params.card || { ref: 'current_card' }, card);
        if (!target) return;
        let prop = String(params.property || 'fusion_level');
        if (prop === 'cost_e') prop = 'cost_e_override';
        if (prop === 'cost_m') prop = 'cost_m_override';
        target[prop] = this.clampCardProperty(target, prop, this.evalInt(playerId, params.value ?? 0, card, 0));
        if (prop === 'fusion_level') target.fusion_multiplier = target.fusion_level;
        if (prop === 'fission_level') target.fission_count = Math.max(0, target.fission_level - 1);
        this.syncCardSpecialPropertyFlag(target, prop, true);
    }

    effect_card_prop_add(playerId, card, params) {
        const target = this.resolveCardRef(playerId, params.card || { ref: 'current_card' }, card);
        if (!target) return;
        let prop = String(params.property || 'fusion_level');
        if (prop === 'cost_e') prop = 'cost_e_override';
        if (prop === 'cost_m') prop = 'cost_m_override';
        const current = prop === 'cost_e_override'
            ? (target.cost_e_override != null ? target.cost_e_override : toInt(target.def().cost_e, 0))
            : prop === 'cost_m_override'
                ? (target.cost_m_override != null ? target.cost_m_override : toInt(target.def().cost_m, 0))
                : toInt(target[prop], 0);
        let amount = this.evalInt(playerId, params.amount ?? params.value ?? 0, card, 0);
        if (
            prop === 'fission_level'
            && card && card.def_id === 'Fission'
            && card.setup_modifiers instanceof Set
            && card.setup_modifiers.has('multi_petal')
            && toInt(amount, 0) === 1
        ) {
            amount = 2;
        }
        target[prop] = this.clampCardProperty(target, prop, current + amount);
        if (prop === 'fusion_level') target.fusion_multiplier = target.fusion_level;
        if (prop === 'fission_level') target.fission_count = Math.max(0, target.fission_level - 1);
        this.syncCardSpecialPropertyFlag(target, prop, false);
    }

    effect_card_prop_mul(playerId, card, params) {
        const target = this.resolveCardRef(playerId, params.card || { ref: 'current_card' }, card);
        if (!target) return;
        let prop = String(params.property || 'fusion_level');
        if (prop === 'cost_e') prop = 'cost_e_override';
        if (prop === 'cost_m') prop = 'cost_m_override';
        const multiplier = this.evalInt(playerId, params.multiplier ?? params.amount ?? 1, card, 1);
        const current = prop === 'cost_e_override'
            ? (target.cost_e_override != null ? target.cost_e_override : toInt(target.def().cost_e, 0))
            : prop === 'cost_m_override'
                ? (target.cost_m_override != null ? target.cost_m_override : toInt(target.def().cost_m, 0))
                : toInt(target[prop], 0);
        target[prop] = this.clampCardProperty(target, prop, current * multiplier);
        if (prop === 'fusion_level') target.fusion_multiplier = target.fusion_level;
        if (prop === 'fission_level') target.fission_count = Math.max(0, target.fission_level - 1);
        this.syncCardSpecialPropertyFlag(target, prop, false);
    }

    effect_card_damage_multiply(playerId, card, params) {
        const target = this.resolveCardRef(playerId, params.card || { ref: 'current_card' }, card);
        if (!target) return;
        const multiplier = this.evalInt(playerId, params.multiplier ?? 2, card, 2);
        target.fusion_level = Math.max(1, toInt(target.fusion_level, 1)) * multiplier;
        target.fusion_multiplier = target.fusion_level;
    }

    effect_clear_tags(playerId, card, params) {
        const target = this.resolveCardRef(playerId, params.card || { ref: 'current_card' }, card);
        if (!target) return;
        target.flags.forEach(flag => target.disabled_flags.add(flag));
        target.instance_flags.clear();
    }

    effect_equipment_prop_set(playerId, card, params) {
        const eq = this.resolveEquipmentRef(playerId, params.equipment || { ref: 'current_equipment' }, card);
        if (!eq) return;
        const prop = String(params.property || 'turns_equipped');
        const value = this.evalInt(playerId, params.value ?? 0, card, 0);
        if (prop === 'turns_equipped' || prop === 'equip_turns' || prop === 'equipped_turns') eq.turns_equipped = Math.max(0, value);
        else if (prop === 'effect_target' || prop === 'target_player') eq.effect_target = value;
        else if (prop === 'corruption_active' || prop === 'is_corruption_active') eq.corruption_active = !!value;
        else {
            eq.custom_vars = eq.custom_vars || {};
            eq.custom_vars[prop] = value;
        }
    }

    effect_equipment_prop_add(playerId, card, params) {
        const eq = this.resolveEquipmentRef(playerId, params.equipment || { ref: 'current_equipment' }, card);
        if (eq) {
            const prop = String(params.property || 'turns_equipped');
            const value = this.equipmentProperty(eq, prop) + this.evalInt(playerId, params.amount ?? params.value ?? 0, card, 0);
            if (prop === 'turns_equipped' || prop === 'equip_turns' || prop === 'equipped_turns') eq.turns_equipped = Math.max(0, value);
            else if (prop === 'effect_target' || prop === 'target_player') eq.effect_target = value;
            else if (prop === 'corruption_active' || prop === 'is_corruption_active') eq.corruption_active = !!value;
            else {
                eq.custom_vars = eq.custom_vars || {};
                eq.custom_vars[prop] = value;
            }
        }
    }

    effect_copy_card(playerId, card, params, log) {
        const target = this.resolveCardRef(playerId, params.card || { ref: 'selected_card' }, card);
        if (!target) return;
        if (!this.players[playerId].canAddToHand()) return;
        if (card && card.def_id === 'Mimic' && !this.payMimicSpecialCost(playerId, target, card)) return;
        const copy = target.copy();
        copy.instance_id = randintId();
        if (card && card.def_id === 'Mimic') {
            const halfLayer = value => Math.max(1, Math.ceil(Math.max(1, toInt(value, 1)) / 2));
            copy.fusion_level = halfLayer(target.fusion_level);
            copy.fusion_multiplier = copy.fusion_level;
            copy.fission_level = halfLayer(target.fission_level);
            copy.fission_count = Math.max(0, copy.fission_level - 1);
            ['swift_value', 'magic_swift_value', 'power_value', 'bonus_damage', 'temp_swift_value', 'temp_heavy_value', 'temp_magic_heavy_value'].forEach(key => {
                copy[key] = Math.ceil(Math.max(0, toInt(target[key], 0)) / 2);
            });
            if (copy.swift_value > 0) copy.instance_flags.add('swift');
            if (copy.magic_swift_value > 0) copy.instance_flags.add('magic_swift');
            if (copy.power_value > 0) copy.instance_flags.add('power');
            if (copy.temp_swift_value > 0) copy.instance_flags.add('temp_swift');
            if (copy.temp_heavy_value > 0) copy.instance_flags.add('temp_heavy');
            if (copy.temp_magic_heavy_value > 0) copy.instance_flags.add('temp_magic_heavy');
        } else {
            this.applySetupModifiersToCard(playerId, copy);
        }
        this.players[playerId].addToHand(copy);
        this.enforceUniqueCardsForPlayer(playerId, copy);
        this._last_created_card_instance_id = copy.instance_id;
        this._active_effect_context.last_created_card_instance_id = copy.instance_id;
        if (log) this.logMsg(log);
    }

    effect_give_card_to_hand(playerId, card, params, log) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const target = this.players[targetId] || this.players[playerId];
        const cardId = this.resolveCardIdRef(playerId, params.card || '', card);
        const def = cardDef(cardId) || cardDef(ERROR_CARD_ID);
        if (!def) return;
        if ((def.id || cardId) !== ERROR_CARD_ID && !target.canAddToHand()) return;
        const newCard = new LocalCard(def.id || cardId);
        this.applySetupModifiersToCard(targetId, newCard);
        target.addToHand(newCard);
        this.enforceUniqueCardsForPlayer(targetId, newCard);
        this._last_created_card_instance_id = newCard.instance_id;
        this._active_effect_context.last_created_card_instance_id = newCard.instance_id;
        if (log && newCard.def_id !== ERROR_CARD_ID) this.logMsg(log);
    }

    effect_give_card_to_deck(playerId, card, params, log) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const target = this.players[targetId] || this.players[playerId];
        const cardId = this.resolveCardIdRef(playerId, params.card || '', card);
        const def = cardDef(cardId) || cardDef(ERROR_CARD_ID);
        if (!def) return;
        const newCard = new LocalCard(def.id || cardId);
        this.applySetupModifiersToCard(targetId, newCard);
        const position = params.position || 'top';
        if (position === 'bottom') target.deck.push(newCard);
        else if (position === 'random') target.deck.splice(Math.floor(Math.random() * (target.deck.length + 1)), 0, newCard);
        else target.deck.unshift(newCard);
        this._last_created_card_instance_id = newCard.instance_id;
        this._active_effect_context.last_created_card_instance_id = newCard.instance_id;
        if (log && newCard.def_id !== ERROR_CARD_ID) this.logMsg(log);
    }

    effect_give_card_to_discard(playerId, card, params, log) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const target = this.players[targetId] || this.players[playerId];
        const cardId = this.resolveCardIdRef(playerId, params.card || '', card);
        const def = cardDef(cardId) || cardDef(ERROR_CARD_ID);
        if (!def) return;
        const newCard = new LocalCard(def.id || cardId);
        this.applySetupModifiersToCard(targetId, newCard);
        this.discardCard(target, newCard);
        this._last_created_card_instance_id = newCard.instance_id;
        this._active_effect_context.last_created_card_instance_id = newCard.instance_id;
        if (log && newCard.def_id !== ERROR_CARD_ID) this.logMsg(log);
    }

    effect_create_copies_to_deck_top(playerId, card, params, log) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const target = this.players[targetId] || this.players[playerId];
        if (!target) return;
        const cardId = this.resolveCardIdRef(playerId, params.def_id || params.card || params.card_id || params.id || card?.def_id || ERROR_CARD_ID, card);
        const def = cardDef(cardId) || cardDef(ERROR_CARD_ID);
        if (!def) return;
        const count = Math.max(0, this.evalInt(playerId, params.count ?? 1, card, 1));
        const flags = normalizeCardFlags(params.flags || []);
        const swift = Math.max(0, this.evalInt(playerId, params.swift_value ?? 0, card, 0));
        const magicSwift = Math.max(0, this.evalInt(playerId, params.magic_swift_value ?? 0, card, 0));
        const power = Math.max(0, this.evalInt(playerId, params.power_value ?? 0, card, 0));
        const extraHits = Math.max(0, this.evalInt(playerId, params.extra_hits ?? 0, card, 0));
        for (let i = 0; i < count; i++) {
            const newCard = new LocalCard(def.id || cardId);
            flags.forEach(flag => newCard.instance_flags.add(flag));
            if (swift > 0) {
                newCard.swift_value = swift;
                newCard.instance_flags.add('swift');
            }
            if (magicSwift > 0) {
                newCard.magic_swift_value = magicSwift;
                newCard.instance_flags.add('magic_swift');
            }
            if (power > 0) {
                newCard.power_value = power;
                newCard.instance_flags.add('power');
            }
            if (extraHits > 0) {
                newCard.extra_hits = extraHits;
                newCard.setup_modifiers.add('explicit_extra_hits');
            }
            this.applySetupModifiersToCard(targetId, newCard);
            target.deck.unshift(newCard);
            this._last_created_card_instance_id = newCard.instance_id;
            this._active_effect_context.last_created_card_instance_id = newCard.instance_id;
        }
        if (log) this.logMsg(log);
    }

    effect_move_to_discard(playerId, card, params) {
        const target = this.resolveCardRef(playerId, params.card || { ref: 'selected_card' }, card);
        const loc = this.removeCardFromCurrentZone(target);
        if (loc) this.discardCard(this.players[loc.ownerId], target);
    }

    effect_move_to_hand(playerId, card, params) {
        const target = this.resolveCardRef(playerId, params.card || { ref: 'selected_card' }, card);
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const targetPlayer = this.players[targetId];
        const isMagnet = String(card && card.def_id || '').toLowerCase().endsWith('magnet');
        if (!target || !targetPlayer || !targetPlayer.canAddToHand()) {
            if (isMagnet) this._antennae_reveal[playerId] = null;
            return;
        }
        const loc = this.removeCardFromCurrentZone(target);
        if (loc) {
            targetPlayer.addToHand(target);
            if (isMagnet) {
                this.logMsg(`${this.pn(playerId)}用磁铁从${this.pn(loc.ownerId)}手牌中获得了${cardName(target.def_id)}`);
                this._antennae_reveal[playerId] = null;
            }
        }
    }

    effect_move_to_deck(playerId, card, params) {
        const target = this.resolveCardRef(playerId, params.card || { ref: 'current_card' }, card);
        const loc = this.removeCardFromCurrentZone(target);
        const targetId = this.resolveTarget(playerId, params.target || (loc ? loc.ownerId : 'self'));
        if (!target || !this.players[targetId]) return;
        if (params.position === 'bottom') this.players[targetId].deck.push(target);
        else this.players[targetId].deck.unshift(target);
    }

    effect_move_to_exile(playerId, card, params) {
        const target = this.resolveCardRef(playerId, params.card || { ref: 'selected_card' }, card);
        const loc = this.removeCardFromCurrentZone(target);
        if (loc) this.putCardInExile(loc.ownerId, target);
    }

    effect_assembler_effect(playerId, card, params, log, choice) {
        const targetId = this.resolveTarget(playerId, params.target || 'choice_target');
        const targetPlayer = this.players[targetId] || this.players[playerId];
        const selectedId = choice && choice.target_instance_id;
        if (selectedId != null) {
            const targetCard = this.players[playerId].findHandCard(selectedId);
            if (targetCard) {
                this.players[playerId].hand = this.players[playerId].hand.filter(c => c.instance_id !== targetCard.instance_id);
                this.putCardInExile(playerId, targetCard);
                this.logMsg(`${this.pn(playerId)}放逐了${cardName(targetCard.def_id)}`);
            }
            const roll = Math.floor(Math.random() * 3);
            if (roll === 0) {
                const created = new LocalCard('Laser');
                created.swift_value = 2;
                created.flags.add('swift');
                this.applySetupModifiersToCard(targetId, created);
                targetPlayer.addToHand(created);
                this.logMsg(`${this.pn(playerId)}的重构机：${this.pn(targetId)}获得激光器`);
            } else if (roll === 1) {
                const created = new LocalCard('Sawblade');
                created.swift_value = 2;
                created.flags.add('swift');
                this.applySetupModifiersToCard(targetId, created);
                targetPlayer.addToHand(created);
                this.logMsg(`${this.pn(playerId)}的重构机：${this.pn(targetId)}获得锯片`);
            } else {
                targetPlayer.fragment_stacks = toInt(targetPlayer.fragment_stacks, 0) + 2;
                targetPlayer.addToHand(this.applySetupModifiersToCard(targetId, new LocalCard('Fragment')));
                this.logMsg(`${this.pn(playerId)}的重构机：${this.pn(targetId)}获得2层碎片和1张碎片`);
            }
            return;
        }
        const handCards = this.players[playerId].hand
            .filter(c => c.instance_id !== card.instance_id)
            .map(c => c.toDict());
        if (!handCards.length) return;
        this.pending_choice = {
            player_id: playerId,
            choice_type: 'choose_card_from_hand',
            card: card.toDict(),
            hand_cards: handCards,
            message: '重构机：选择一张手牌放逐',
            target_player_id: targetId,
            original_choice: { target_player_id: targetId },
        };
    }

    logDestroyedEquipment(actorId, ownerId, eq, customLog) {
        if (!eq) return;
        const eqName = cardName(eq.def_id || (eq.card_instance && eq.card_instance.def_id));
        this.logMsg(customLog || `${this.pn(actorId)}摧毁了${this.pn(ownerId)}的${eqName}`);
    }

    effect_remove_specific_card(playerId, card, params, log) {
        const target = this.resolveCardRef(playerId, params.card || { ref: 'selected_card' }, card);
        const loc = this.findCardLocation(target);
        if (!loc) return;
        if (loc.zone === 'equipment') {
            const eq = this.players[loc.ownerId].equipment[loc.index];
            if (this.destroyEquipment(loc.ownerId, eq)) this.logDestroyedEquipment(playerId, loc.ownerId, eq, log);
            else if (log) this.logMsg(log);
        } else {
            this.removeCardFromCurrentZone(target);
            if (log) this.logMsg(log);
        }
    }

    effect_destroy_all_destroyable_equipment(playerId, card, params, log) {
        let destroyedCount = 0;
        this.resolveTargets(playerId, params.target || 'enemy').forEach(tid => {
            [...this.players[tid].equipment].forEach(eq => {
                if (!eq.card_instance.flags.has('indestructible') && this.destroyEquipment(tid, eq)) {
                    destroyedCount += 1;
                    this.logDestroyedEquipment(playerId, tid, eq, log);
                }
            });
        });
        if (this._active_effect_context) {
            this._active_effect_context.last_destroyed_equipment_count = destroyedCount;
        }
    }

    effect_destroy_random_equip(playerId, card, params, log) {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
        const list = this.players[targetId].equipment.filter(eq => !eq.card_instance.flags.has('indestructible'));
        if (list.length) {
            const eq = list[Math.floor(Math.random() * list.length)];
            if (this.destroyEquipment(targetId, eq)) this.logDestroyedEquipment(playerId, targetId, eq, log);
        }
    }

    effect_destroy_all_equip(playerId, card, params, log) {
        this.effect_destroy_all_destroyable_equipment(playerId, card, params, log);
    }

    effect_destroy_equipment_choice_or_first(playerId, card, params, log) {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
        let eq = null;
        const choiceCard = this.resolveCardRef(playerId, params.card || { ref: 'selected_card' }, card);
        if (choiceCard) eq = this.players[targetId].equipment.find(item => item.card_instance === choiceCard || item.card_instance.instance_id === choiceCard.instance_id);
        if (!eq) eq = this.players[targetId].equipment.find(item => !item.card_instance.flags.has('indestructible'));
        if (eq && this.destroyEquipment(targetId, eq)) this.logDestroyedEquipment(playerId, targetId, eq, log);
    }

    effect_destroy_self_equipment(playerId, card) {
        const eq = this.findEquipmentForCard(playerId, card);
        if (eq) this.destroyEquipment(playerId, eq);
    }

    effect_place_as_equip(playerId, card, params) {
        const targetCard = this.resolveCardRef(playerId, params.card || { ref: 'current_card' }, card);
        if (!targetCard) return;
        const ownerId = this.resolveTarget(playerId, params.owner || params.equip_owner || 'self');
        this.removeCardFromCurrentZone(targetCard);
        if (!this.findEquipmentForCard(ownerId, targetCard)) {
            const eq = new LocalEquipment(targetCard, ownerId);
            if (params.effect_target != null) {
                eq.effect_target = this.resolveTarget(playerId, params.effect_target);
            } else {
                const selectedTarget = this.resolveTarget(playerId, 'choice_target');
                if (selectedTarget >= 0 && selectedTarget < this.players.length) eq.effect_target = selectedTarget;
            }
            this.players[ownerId].equipment.push(eq);
            this.logMsg(`${this.pn(ownerId)}装备了${cardName(targetCard.def_id)}`);
        }
        if (targetCard === card) {
            card._placed_as_equipment = true;
            card._placed_as_equipment_owner = ownerId;
        }
    }

    effect_add_equipment_to_zone(playerId, card, params, log) {
        const cardId = this.resolveCardIdRef(playerId, params.card || 'Leaf', card);
        const def = cardDef(cardId);
        let ownerIds = this.resolveTargets(playerId, params.target || params.owner || 'self');
        if (!ownerIds.length) ownerIds = [playerId];
        if (!def) {
            const errorDef = cardDef(ERROR_CARD_ID);
            if (!errorDef) return;
            ownerIds.forEach(ownerId => {
                const owner = this.players[ownerId];
                if (!owner) return;
                const newCard = new LocalCard(ERROR_CARD_ID);
                owner.addToHand(newCard);
                this._last_created_card_instance_id = newCard.instance_id;
                this._active_effect_context.last_created_card_instance_id = newCard.instance_id;
            });
            return;
        }
        ownerIds.forEach(ownerId => {
            const owner = this.players[ownerId];
            if (!owner) return;
            const newCard = new LocalCard(def.id || cardId);
            this.applySetupModifiersToCard(ownerId, newCard);
            newCard.durability = toInt(def.durability, 0) > 0 ? toInt(def.durability, 0) : 3;
            const eq = new LocalEquipment(newCard, ownerId);
            if (params.effect_target != null) {
                const effectTarget = this.resolveTarget(playerId, params.effect_target);
                if (effectTarget >= 0 && effectTarget < this.players.length) eq.effect_target = effectTarget;
            } else {
                eq.effect_target = ownerId;
            }
            owner.equipment.push(eq);
            this._last_created_card_instance_id = newCard.instance_id;
            this._active_effect_context.last_created_card_instance_id = newCard.instance_id;
            this.logMsg(log || `${this.pn(ownerId)}获得装备${cardName(newCard.def_id)}`);
        });
    }

    effect_skip_turn(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
        if (this.statusApplicationBlocked(targetId, 'skip_turn')) return;
        const amount = toInt(params.amount, 1);
        this.players[targetId].skip_turn += amount;
    }

    effect_reveal_enemy_hand(playerId, card, params, log) {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
        this._antennae_reveal[playerId] = this.players[targetId].hand.map(c => c.toDict());
        this.logMsg(log || `${this.pn(playerId)}查看了${this.pn(targetId)}的手牌`);
    }

    effect_choose_from_discard(playerId, card, params, log, choice) {
        const targetDef = choice && choice.target_def_id;
        if (!targetDef) return;
        const ps = this.players[playerId];
        const idx = ps.discard.findIndex(c => c.def_id === targetDef);
        if (idx >= 0 && ps.canAddToHand()) {
            const found = ps.discard.splice(idx, 1)[0];
            found.instance_flags.add('symbiosis');
            ps.addToHand(found);
            if (log) this.logMsg(log);
        }
    }

    effect_choose_from_deck(playerId, card, params, log, choice) {
        const ps = this.players[playerId];
        let idx = -1;
        if (choice && choice.target_instance_id != null) idx = ps.deck.findIndex(c => c.instance_id === choice.target_instance_id);
        if (idx < 0 && choice && choice.target_def_id) idx = ps.deck.findIndex(c => c.def_id === choice.target_def_id);
        if (idx >= 0 && ps.canAddToHand()) {
            const found = ps.deck.splice(idx, 1)[0];
            ps.addToHand(found);
            if (log) this.logMsg(log);
        }
    }

    effect_steal_enemy_card(playerId, card, params, log, choice) {
        const sourceId = this.resolveTarget(playerId, params.target || 'enemy');
        const source = this.players[sourceId];
        const target = this.players[playerId];
        let stolen = null;
        if (choice && choice.target_instance_id != null) {
            const idx = source.hand.findIndex(c => c.instance_id === choice.target_instance_id);
            if (idx >= 0) stolen = source.hand.splice(idx, 1)[0];
        }
        if (!stolen && source.hand.length) stolen = source.hand.splice(0, 1)[0];
        if (stolen && target.canAddToHand()) {
            target.addToHand(stolen);
            this.logMsg(log || `${this.pn(playerId)}从${this.pn(sourceId)}手牌中获得1张牌`);
        }
    }

    effect_triangle_damage(playerId, card, params) {
        const base = this.evalInt(playerId, params.base ?? 6, card, 6);
        const perStack = this.evalInt(playerId, params.per_stack ?? 3, card, 3);
        const stackName = String(params.stack_name || '三角形层数');
        const stack = toInt(this.players[playerId].custom_vars[stackName] ?? this.players[playerId].triangle_stacks, 0);
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
        const amount = this.modifiedAttackDamage(base + perStack * stack, card);
        const dealt = this.dealAttackDamage(targetId, amount, 1, !!params.is_precision, playerId);
        this._last_damage_value[targetId] = dealt;
        if (dealt > 0) {
            const next = Math.min(4, stack + 1);
            this.players[playerId].custom_vars[stackName] = next;
            this.players[playerId].triangle_stacks = next;
        }
    }

    effect_status_remove_named(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const status = String(params.status || params.name || '');
        if (['status_immune', 'immune', '状态免疫'].includes(status)) {
            if (this.players[targetId]) {
                this.players[targetId].custom_statuses = this.players[targetId].custom_statuses || {};
                delete this.players[targetId].custom_statuses.status_immune;
                delete this.players[targetId].custom_statuses.immune;
                delete this.players[targetId].custom_statuses['状态免疫'];
            }
            return;
        }
        if (status === 'poison') this.players[targetId].poison = 0;
        else if (status === 'fire') this.players[targetId].fire = 0;
        else if (status) this.players[targetId][status] = 0;
    }

    effect_status_add_named(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const status = String(params.status || params.name || '');
        const amount = this.evalInt(playerId, params.amount ?? 1, card, 1);
        if (!status) return;
        if (this.statusApplicationBlocked(targetId, status)) return;
        if (['status_immune', 'immune', '状态免疫'].includes(status)) {
            this.players[targetId].custom_statuses = this.players[targetId].custom_statuses || {};
            delete this.players[targetId].custom_statuses.immune;
            delete this.players[targetId].custom_statuses['状态免疫'];
            if (amount > 0) this.players[targetId].custom_statuses.status_immune = 1;
            return;
        }
        if (['nazar', '邪眼', 'Nazar'].includes(status)) {
            this.setNazarStatusValue(targetId, this.nazarStatusValue(targetId) + amount);
            return;
        }
        const aliases = { burn: 'fire', vulnus: 'vulnerable', stunned: 'skip_turn', dizzy: 'skip_turn', '眩晕': 'skip_turn', '禁攻': 'attack_blocked' };
        const prop = aliases[status] || status;
        this.players[targetId][prop] = toInt(this.players[targetId][prop], 0) + amount;
    }

    effect_status_set_named(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const status = String(params.status || params.name || '');
        const amount = this.evalInt(playerId, params.amount ?? params.value ?? 0, card, 0);
        if (['status_immune', 'immune', '状态免疫'].includes(status)) {
            this.players[targetId].custom_statuses = this.players[targetId].custom_statuses || {};
            delete this.players[targetId].custom_statuses.immune;
            delete this.players[targetId].custom_statuses['状态免疫'];
            if (amount > 0) this.players[targetId].custom_statuses.status_immune = 1;
            else delete this.players[targetId].custom_statuses.status_immune;
            return;
        }
        if (['nazar', '邪眼', 'Nazar'].includes(status)) {
            this.setNazarStatusValue(targetId, amount);
            return;
        }
        if (status) this.players[targetId][status] = amount;
    }

    effect_apply_turn_regen(playerId, card, params, log, choice) {
        const targetId = this.resolveTarget(playerId, params.target || 'self', choice);
        const kind = String(params.kind || 'heal');
        if (this.statusApplicationBlocked(targetId, kind === 'magic' ? 'turn_magic_turns' : 'turn_heal_turns')) return;
        const turns = this.evalInt(playerId, params.turns ?? params.amount ?? 1, card, 1, choice);
        const power = this.evalInt(playerId, params.power ?? params.level ?? 1, card, 1, choice);
        const [mergedTurns, mergedPower] = this.mergeTurnRegenStatus(targetId, kind, turns, power);
        if (kind === 'magic') {
            this.players[targetId].gainMagic(power);
            const remainingTurns = Math.max(0, mergedTurns - 1);
            this.setCustomStatusAliasGroup(targetId, 'jungle:turn_magic_turns', ['jungle:turn_magic_turns', 'turn_magic_turns'], remainingTurns);
            if (remainingTurns <= 0) this.setCustomStatusAliasGroup(targetId, 'jungle:turn_magic_power', ['jungle:turn_magic_power', 'turn_magic_power'], 0);
            this.logMsg(log || `${this.pn(targetId)}获得魔力回合回复：${remainingTurns};${mergedPower}，+${power}M`);
        } else {
            this.players[targetId].heal(power);
            const remainingTurns = Math.max(0, mergedTurns - 1);
            this.setCustomStatusAliasGroup(targetId, 'jungle:turn_heal_turns', ['jungle:turn_heal_turns', 'turn_heal_turns'], remainingTurns);
            if (remainingTurns <= 0) this.setCustomStatusAliasGroup(targetId, 'jungle:turn_heal_power', ['jungle:turn_heal_power', 'turn_heal_power'], 0);
            this.logMsg(log || `${this.pn(targetId)}获得回合回复：${remainingTurns};${mergedPower}，+${power}H`);
        }
    }

    effect_apply_jungle_status(playerId, card, params, log, choice) {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy', choice);
        if (!this.players[targetId]) return;
        const status = String(params.status || 'jungle:shield');
        if (this.statusApplicationBlocked(targetId, status)) return;
        const amount = Math.max(0, this.evalInt(playerId, params.amount ?? 1, card, 1, choice));
        const current = this.customStatusValue(targetId, status);
        this.setCustomStatusAliasGroup(targetId, status, [status], current + amount);
        const label = String(params.label || status.split(':').pop() || status);
        if (log !== false) this.logMsg(log || `${this.pn(targetId)}获得${amount}层${label}`);
    }

    effect_jungle_root_gain(playerId, card, params, log, choice) {
        const targetId = this.resolveTarget(playerId, params.target || 'self', choice);
        if (!this.players[targetId]) return;
        const amount = Math.max(0, this.evalInt(playerId, params.amount ?? 2, card, 2, choice));
        const current = this.customStatusValue(targetId, 'jungle:root_status', 'jungle:root', 'root_status');
        this.setCustomStatusAliasGroup(targetId, 'jungle:root_status', ['jungle:root_status', 'jungle:root', 'root_status'], current + amount);
        const { eq } = this.findEquipmentByCardInstanceId(card && card.instance_id);
        if (eq) {
            eq.custom_vars = eq.custom_vars || {};
            eq.custom_vars.jungle_root_layers = toInt(eq.custom_vars.jungle_root_layers, 0) + amount;
        }
        this.logMsg(log || `${this.pn(targetId)}获得${amount}层树根`);
    }

    effect_jungle_root_remove_owned(playerId, card, params, log, choice) {
        const targetId = this.resolveTarget(playerId, params.target || 'self', choice);
        if (!this.players[targetId]) return;
        const { eq } = this.findEquipmentByCardInstanceId(card && card.instance_id);
        const amount = eq ? toInt((eq.custom_vars || {}).jungle_root_layers, 0) : 0;
        if (amount > 0) {
            const current = this.customStatusValue(targetId, 'jungle:root_status', 'jungle:root', 'root_status');
            this.setCustomStatusAliasGroup(targetId, 'jungle:root_status', ['jungle:root_status', 'jungle:root', 'root_status'], Math.max(0, current - amount));
            eq.custom_vars.jungle_root_layers = 0;
        }
    }

    effect_electric_web_arm(playerId, card, params, log, choice) {
        const targetId = this.resolveTarget(playerId, params.target || 'target', choice);
        const amount = Math.max(0, this.evalInt(playerId, params.amount ?? 2, card, 2, choice));
        if (!this.players[targetId]) return;
        this.players[targetId].custom_vars.electric_web_draw_damage = (
            toInt(this.players[targetId].custom_vars.electric_web_draw_damage, 0) + amount
        );
        const eq = this.findEquipmentForCard(playerId, card);
        if (eq) {
            eq.custom_vars = eq.custom_vars || {};
            eq.custom_vars.electric_web_armed_target = targetId;
            eq.custom_vars.electric_web_armed_amount = (
                toInt(eq.custom_vars.electric_web_armed_amount, 0) + amount
            );
        }
    }

    effect_add_status(playerId, card, params, log, choice) {
        this.effect_status_add_named(playerId, card, { ...params, status: params.status || params.id || params.name }, log, choice);
    }

    effect_cogwheel_mark(playerId, card, params, log, choice) {
        const targetId = this.resolveTarget(playerId, params.target || 'choice_target');
        const ps = this.players[targetId];
        if (!ps) return;
        ps.cogwheel_active = true;
        ps.cogwheel_exclude_instance_id = card ? toInt(card.instance_id, -1) : -1;
        this.returnCogwheelCardsNow(targetId);
        if (log) this.logMsg(log);
    }

    effect_ocean_sapphire_mark(playerId, card, params, log, choice) {
        const targetId = this.resolveTarget(playerId, params.target || 'target');
        if (targetId < 0 || targetId >= this.players.length) return;
        const ps = this.players[playerId];
        const iid = choice && choice.target_instance_id != null ? toInt(choice.target_instance_id, -1) : -1;
        const chosen = iid >= 0 ? ps.findHandCard(iid) : null;
        if (!chosen || chosen.card_type !== 'thorn') return;
        const idx = ps.hand.indexOf(chosen);
        if (idx < 0) return;
        ps.hand.splice(idx, 1);
        chosen.instance_flags.add('exile');
        this.putCardInExile(playerId, chosen);
        const entries = Array.isArray(ps.custom_vars.ocean_auto_cards) ? ps.custom_vars.ocean_auto_cards : [];
        entries.push({
            def_id: chosen.def_id,
            target_id: targetId,
            swift_value: toInt(chosen.swift_value, 0),
            magic_swift_value: toInt(chosen.magic_swift_value, 0),
            exile: true,
            no_auto: true,
        });
        ps.custom_vars.ocean_auto_cards = entries;
        this.logMsg(log || `${this.pn(playerId)}的蓝宝石放逐1张攻击牌`);
    }

    runOceanAutoCardsTurnStart(playerId) {
        const ps = this.players[playerId];
        const entries = ps && Array.isArray(ps.custom_vars.ocean_auto_cards) ? ps.custom_vars.ocean_auto_cards : [];
        if (!entries.length) return;
        entries.forEach(entry => {
            if (this.game_over || this.phase !== 'action') return;
            const targetId = toInt(entry && entry.target_id, -1);
            const target = this.players[targetId];
            if (!target || targetId === playerId || toInt(target.health, 0) <= 0 || target.untargetable) return;
            const defId = String(entry.def_id || '');
            if (!defId || !cardDef(defId)) return;
            const tempCard = new LocalCard(defId);
            tempCard.instance_flags.add('exile');
            tempCard.instance_flags.add('ocean_no_auto');
            tempCard.disabled_flags.add('rebound');
            const swift = Math.max(0, toInt(entry.swift_value, 0));
            const magicSwift = Math.max(0, toInt(entry.magic_swift_value, 0));
            if (swift > 0) {
                tempCard.swift_value = swift;
                tempCard.instance_flags.add('swift');
            }
            if (magicSwift > 0) {
                tempCard.magic_swift_value = magicSwift;
                tempCard.instance_flags.add('magic_swift');
            }
            if (tempCard.cost_e > ps.elixir || tempCard.cost_m > ps.magic) return;
            ps.addToHand(tempCard, { triggerEnterHand: false });
            const previousAutoActor = this.allowOutOfTurnAutoPlayFor;
            this.allowOutOfTurnAutoPlayFor = playerId;
            let result = null;
            try {
                result = this.playCard(playerId, tempCard.instance_id, {
                    target_player: targetId,
                    target_player_id: targetId,
                    target_id: targetId,
                });
            } finally {
                this.allowOutOfTurnAutoPlayFor = previousAutoActor;
            }
            const idx = ps.hand.indexOf(tempCard);
            if (idx >= 0 && !(result && (result.needs_choice || result.needs_v2_ui))) ps.hand.splice(idx, 1);
            if (result && (result.needs_response || result.needs_choice || result.needs_v2_ui)) return;
        });
    }

    effect_remove_status(playerId, card, params, log, choice) {
        this.effect_status_remove_named(playerId, card, { ...params, status: params.status || params.id || params.name }, log, choice);
    }

    effect_set_status(playerId, card, params, log, choice) {
        this.effect_status_set_named(playerId, card, { ...params, status: params.status || params.id || params.name }, log, choice);
    }

    effect_draw_cards(playerId, card, params, log, choice) {
        this.effect_draw(playerId, card, params, log, choice);
    }

    effect_add_tag(playerId, card, params, log) {
        this.effect_tag_add_named(playerId, card, params, log);
    }

    effect_remove_tag(playerId, card, params, log) {
        this.effect_tag_remove_named(playerId, card, params, log);
    }

    effect_tag_add_named(playerId, card, params, log) {
        const target = this.resolveCardRef(playerId, params.card || { ref: 'current_card' }, card);
        const tag = normalizeCardFlag(params.tag || '');
        if (!target || !tag) return;
        target.instance_flags.add(tag);
        if (log) this.logMsg(log);
    }

    effect_third_eye_precision_or_hidden(playerId, card, params, log) {
        const target = this.resolveCardRef(playerId, params.card || { ref: 'selected_card' }, card);
        if (!target) return;
        if (target.flags.has('precision') || target.instance_flags.has('precision')) {
            target.instance_flags.add('stealth');
            if (log) this.logMsg(log);
            return;
        }
        target.instance_flags.add('precision');
        if (log) this.logMsg(log);
    }

    effect_grant_temp_swift_highest_e(playerId, card, params, log) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const ps = this.players[targetId];
        if (!ps || !ps.hand.length) return;
        const amount = Math.max(0, this.evalInt(playerId, params.amount ?? 3, card, 3));
        const candidates = ps.hand
            .filter(c => c !== card)
            .sort((a, b) => {
                const ea = Math.max(0, toInt(a.cost_e, 0) + this.getExtraEForCard(targetId, a));
                const eb = Math.max(0, toInt(b.cost_e, 0) + this.getExtraEForCard(targetId, b));
                return eb - ea || String(cardName(a.def_id)).localeCompare(String(cardName(b.def_id)));
            });
        const target = candidates[0];
        if (!target || amount <= 0) return;
        target.temp_swift_value = Math.max(0, toInt(target.temp_swift_value, 0)) + amount;
        target.instance_flags.add('temp_swift');
        if (log) this.logMsg(log);
    }

    effect_delayed_blind_next_turn(playerId, card, params, log) {
        const targetId = this.resolveTarget(playerId, params.target || 'target');
        const amount = Math.max(1, this.evalInt(playerId, params.amount ?? 1, card, 1));
        this.registerTimedEffect(playerId, targetId, 'target_turn_start', 1, [
            { type: 'add_status', params: { target: 'target', status: 'blind', amount } },
        ], card);
        if (log) this.logMsg(log);
    }

    effect_delayed_reveal_hand_next_turn(playerId, card, params, log) {
        const targetId = this.resolveTarget(playerId, params.target || 'target');
        this.registerTimedEffect(playerId, targetId, 'target_turn_start', 1, [
            { type: 'reveal_hand', params: { target: 'target', viewer: playerId } },
        ], card);
        if (log) this.logMsg(log);
    }

    effect_reveal_hand(playerId, card, params, log) {
        const targetId = this.resolveTarget(playerId, params.target || 'target');
        const viewerId = params.viewer != null ? toInt(params.viewer, playerId) : playerId;
        if (!this.players[targetId] || !this.players[viewerId]) return;
        this._antennae_reveal[viewerId] = this.players[targetId].hand.map(c => c.toDict());
        if (log) this.logMsg(log);
    }

    effect_tag_remove_named(playerId, card, params, log) {
        const target = this.resolveCardRef(playerId, params.card || { ref: 'current_card' }, card);
        const tag = normalizeCardFlag(params.tag || '');
        if (!target || !tag) return;
        target.instance_flags.delete(tag);
        if (log) this.logMsg(log);
    }

    effect_clear_status(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const ps = this.players[targetId];
        ['poison', 'fire', 'vulnerable', 'toxic', 'dodge'].forEach(prop => { ps[prop] = 0; });
    }

    effect_set_health(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        this.setPlayerPropertyValue(targetId, 'health', this.evalInt(playerId, params.value ?? params.amount ?? 0, card, 0));
    }

    effect_invincible(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        if (this.evalInt(playerId, params.value ?? params.amount ?? 1, card, 1) > 0) {
            if (this.statusApplicationBlocked(targetId, 'invincible')) return;
            this.setInvincibleUntilNextOwnTurnEnd(targetId);
        } else {
            this.clearInvincibleState(targetId);
        }
    }

    effect_mod_e_regen(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
        this.players[targetId].enemy_e_reduction = Math.max(0, toInt(this.players[targetId].enemy_e_reduction, 0) - this.evalInt(playerId, params.amount ?? 0, card, 0));
    }

    effect_mod_m_regen() {}

    effect_mod_draw(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        this.players[targetId].enemy_draw_reduction = Math.max(0, toInt(this.players[targetId].enemy_draw_reduction, 0) - this.evalInt(playerId, params.amount ?? 0, card, 0));
    }

    effect_equip_protection(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        this.players[targetId].equipment_protection += this.evalInt(playerId, params.amount ?? 1, card, 1);
    }

    effect_response_declare() {}

    effect_trigger_manual() {}

    effect_log(playerId, card, params, log) {
        const message = log || params.message || params.text || '';
        if (message) this.logMsg(String(message));
    }

    effect_nullify_current_card() {
        this.negated_card = true;
    }

    effect_request_card() {}
    effect_request_target(playerId, card, params) {
        const targetId = this.choiceTargetFromChoice(this._active_choice, -1);
        if (targetId >= 0 && targetId < this.players.length) {
            this._active_choice.target_player = targetId;
            this._active_choice.target_player_id = targetId;
            this._active_choice.target_id = targetId;
            this._active_effect_context.target_id = targetId;
        }
    }
    effect_request_confirm() {}
    effect_aura_enemy_elixir_recovery() {}

    findEquipmentForCard(ownerId, card) {
        if (!card || !this.players[ownerId]) return null;
        return this.players[ownerId].equipment.find(eq => eq.card_instance === card || eq.card_instance.instance_id === card.instance_id) || null;
    }

    findEquipmentByCardInstanceId(instanceId) {
        const iid = Number(instanceId);
        if (!Number.isFinite(iid)) return { ownerId: -1, eq: null };
        for (const [ownerId, ps] of this.players.entries()) {
            const eq = ps.equipment.find(item => item.card_instance && item.card_instance.instance_id === iid);
            if (eq) return { ownerId, eq };
        }
        return { ownerId: -1, eq: null };
    }

    consumeJungleRootLayerFromEquipment(targetId) {
        for (const [ownerId, ps] of this.players.entries()) {
            for (const eq of ps.equipment || []) {
                const defId = String((eq.card_instance && eq.card_instance.def_id) || eq.def_id || '');
                eq.custom_vars = eq.custom_vars || {};
                const layers = toInt(eq.custom_vars.jungle_root_layers, 0);
                if (layers <= 0 && !['Root', 'jungle:root'].includes(defId)) continue;
                const effectTarget = toInt(eq.effect_target ?? eq.owner ?? ownerId, ownerId);
                if (effectTarget !== targetId) continue;
                if (layers <= 0) continue;
                eq.custom_vars.jungle_root_layers = layers - 1;
                return;
            }
        }
    }

    resolveEquipmentRef(playerId, ref, currentCard = null) {
        ref = parseJsonish(ref);
        if (ref instanceof LocalEquipment) return ref;
        if (ref == null) ref = { ref: 'current_equipment' };
        if (typeof ref === 'string') ref = { ref };
        if (!ref || typeof ref !== 'object') return null;
        if (['event_equipment', 'trigger_equipment', 'destroyed_equipment'].includes(ref.ref)) {
            return this.findEquipmentByCardInstanceId((this._active_effect_context || {}).selected_equipment_instance_id).eq;
        }
        if (['current_equipment', 'this_equipment'].includes(ref.ref)) {
            return this.findEquipmentForCard(playerId, currentCard)
                || this.findEquipmentByCardInstanceId(currentCard && currentCard.instance_id).eq;
        }
        if (['selected_equipment', 'choice_equipment'].includes(ref.ref)) {
            const contextId = (this._active_effect_context || {}).selected_equipment_instance_id;
            const choice = this._active_choice || {};
            const id = contextId ?? choice.target_instance_id ?? (Array.isArray(choice.target_instance_ids) ? choice.target_instance_ids[0] : null);
            return this.findEquipmentByCardInstanceId(id).eq;
        }
        if (ref.ref === 'card_equipment') {
            const targetCard = this.resolveCardRef(playerId, ref.card, currentCard);
            return this.findEquipmentByCardInstanceId(targetCard && targetCard.instance_id).eq;
        }
        return null;
    }

    equipmentProperty(eq, property) {
        if (!eq) return 0;
        const prop = String(property || 'turns_equipped');
        if (prop === 'turns_equipped' || prop === 'equip_turns' || prop === 'equipped_turns') return toInt(eq.turns_equipped, 0);
        if (prop === 'effect_target' || prop === 'target_player') return toInt(eq.effect_target ?? eq.owner, 0);
        if (prop === 'corruption_active' || prop === 'is_corruption_active') return eq.corruption_active ? 1 : 0;
        if (prop === 'owner') return toInt(eq.owner, 0);
        return toInt((eq.custom_vars || {})[prop], 0);
    }

    modifiedAttackDamage(base, card) {
        let bonus = Math.max(0, toInt(card && card.bonus_damage, 0));
        if (card && card.def_id === 'Tomato') bonus = Math.min(18, bonus);
        let amount = toInt(base, 0) + bonus;
        const fusion = Math.max(1, toInt(card && card.fusion_level, 1));
        const fission = Math.max(1, toInt(card && card.fission_level, 1));
        return Math.ceil((amount * fusion) / fission);
    }

    cardTotalHits(card, baseHits = 1) {
        return Math.max(1, toInt(baseHits, 1) + Math.max(0, toInt(card && card.extra_hits, 0)));
    }

    cardBasePetalCount(card) {
        const fallback = { Sand: 4, Wing: 2, Light: 2 };
        let best = Math.max(1, toInt((card && card.def && card.def().hits) || 1, 1), toInt(fallback[card && card.def_id] || 1, 1));
        playEffectsFor(card).forEach(effect => {
            const type = effect && String(effect.type || '');
            if (type !== 'deal_damage' && type !== 'damage') return;
            const params = effect.params || {};
            const hits = toInt(params.hits, 1);
            if (Number.isFinite(hits)) best = Math.max(best, hits);
        });
        return best;
    }

    applySetupModifiersToCard(playerId, card) {
        if (!card || !this.players[playerId]) return card;
        const eventId = toInt(this.opening_event_picks[playerId], -1);
        if (eventId === 9 && (card.def_id === 'Fission' || this.cardBasePetalCount(card) >= 2)) {
            card.setup_modifiers = card.setup_modifiers instanceof Set
                ? card.setup_modifiers
                : new Set(card.setup_modifiers || []);
            if (!card.setup_modifiers.has('multi_petal')) {
                if (card.def_id === 'Fission') {
                    card.instance_flags.add('multi_petal_fission');
                } else {
                    card.extra_hits = Math.max(0, toInt(card.extra_hits, 0)) + 1;
                }
                card.setup_modifiers.add('multi_petal');
            }
        }
        return card;
    }

    applyMagicAccelerationAfterPlay(playerId, card = null) {
        const ps = this.players[playerId];
        if (toInt(ps.custom_vars.setup_magic_acceleration, 0) <= 0) return;
        const previousCount = Math.abs(toInt(ps.custom_vars.setup_magic_acceleration_play_count, 0)) % 2;
        let nextCount = previousCount + 1;
        let gained = 0;
        if (nextCount >= 2) {
            nextCount = 0;
            const beforeMagic = ps.magic;
            ps.gainMagic(1);
            gained = Math.max(0, ps.magic - beforeMagic);
            if (gained > 0) this.logMsg(`${this.pn(playerId)}【魔力加速】：+1M`);
        }
        ps.custom_vars.setup_magic_acceleration_play_count = nextCount;
        ps.custom_vars.setup_magic_acceleration_last_before = previousCount;
        ps.custom_vars.setup_magic_acceleration_last_gain = gained;
        ps.custom_vars.setup_magic_acceleration_last_instance_id = toInt(card && card.instance_id, 0);
    }

    undoMagicAccelerationAfterPendingChoice(playerId, card = null) {
        const ps = this.players[playerId];
        if (toInt(ps.custom_vars.setup_magic_acceleration, 0) <= 0) return;
        const cardInstanceId = toInt(card && card.instance_id, 0);
        if (toInt(ps.custom_vars.setup_magic_acceleration_last_instance_id, -1) !== cardInstanceId) return;
        ps.custom_vars.setup_magic_acceleration_play_count = Math.abs(
            toInt(ps.custom_vars.setup_magic_acceleration_last_before, 0)
        ) % 2;
        const gained = Math.max(0, toInt(ps.custom_vars.setup_magic_acceleration_last_gain, 0));
        delete ps.custom_vars.setup_magic_acceleration_last_before;
        delete ps.custom_vars.setup_magic_acceleration_last_gain;
        delete ps.custom_vars.setup_magic_acceleration_last_instance_id;
        if (gained <= 0) return;
        const msg = `${this.pn(playerId)}【魔力加速】：+1M`;
        for (let index = this.log.length - 1; index >= 0; index -= 1) {
            if (this.log[index] !== msg) continue;
            this.log.splice(index, 1);
            break;
        }
        ps.magic = Math.max(0, ps.magic - gained);
    }

    getCorruptionCount() {
        let count = 0;
        this.players.forEach(ps => {
            ps.equipment.forEach(eq => {
                if (eq.def_id === 'Corruption' && eq.corruption_active) count += 1;
            });
        });
        return count;
    }

    getCorruptionMultiplier() {
        return CORRUPTION_DAMAGE_MULTIPLIER ** Math.max(0, this.getCorruptionCount());
    }

    applyCorruptionMultiplier(amount) {
        const multiplier = this.getCorruptionMultiplier();
        const base = Math.max(0, toInt(amount, 0));
        return multiplier > 1 ? Math.ceil(base * multiplier) : base;
    }

    applyLateRoundFirePressure() {
        if (this.round_num < LATE_ROUND_FIRE_START) return;
        let applied = 0;
        this.players.forEach((ps, playerId) => {
            if (ps.health > 0 && !this.statusApplicationBlocked(playerId, 'fire')) {
                ps.fire += 1;
                applied += 1;
            }
        });
        if (applied > 0) this.logMsg(`第${this.round_num}回合开始，所有存活玩家+1灼烧`);
    }

    hasEquipment(playerId, defId) {
        if (!this.players[playerId]) return false;
        const target = String(defId || '').toLowerCase();
        return this.players.some((ps, ownerId) => (ps.equipment || []).some(eq => {
            const effectTarget = toInt(eq.effect_target ?? ownerId, ownerId);
            if (effectTarget !== playerId) return false;
            const id = String(eq.def_id || '').toLowerCase();
            return id === target || id.endsWith(`:${target}`);
        }));
    }

    cardIs(card, ...ids) {
        if (!card) return false;
        const wanted = new Set((ids || []).filter(Boolean).map(v => String(v).toLowerCase()));
        const def = typeof card.def === 'function' ? card.def() : (card.card_def || card);
        const candidates = [
            card.def_id,
            card.id,
            def && def.id,
            def && def.legacy_id,
            def && def.runtime_id,
            def && def.v2_resource && def.v2_resource.legacy_id,
            def && def.v2_resource && def.v2_resource.id,
            def && def.v2_resource && def.v2_resource.runtime_id,
        ].filter(Boolean).map(v => String(v).toLowerCase());
        return candidates.some(v => wanted.has(v));
    }

    damageDealtEquipmentFlatBonus(sourceId) {
        const sid = toInt(sourceId, -1);
        if (sid < 0 || sid >= this.players.length) return 0;
        let bonus = 0;
        this.players.forEach((owner, ownerId) => {
            owner.equipment.forEach(eq => {
                const id = String(eq.def_id || '').toLowerCase();
                const effectTarget = toInt(eq.effect_target ?? eq.owner ?? ownerId, ownerId);
                if (effectTarget !== sid) return;
                if (id === 'cutter' || id.endsWith(':cutter')) bonus += 2;
            });
        });
        return bonus;
    }

    applyUniversalDamageShields(targetId, damage, sourceId = null, source = '') {
        let actual = Math.max(0, toInt(damage, 0));
        const ps = this.players[targetId];
        if (!ps || actual <= 0) return actual;
        const shield = this.customStatusValue(targetId, 'jungle:shield', 'shield');
        if (shield > 0 && !this.isStatusImmune(targetId)) {
            const blocked = Math.min(shield, actual);
            actual -= blocked;
            this.setCustomStatusAliasGroup(targetId, 'jungle:shield', ['jungle:shield', 'shield'], shield - blocked);
            this.logMsg(`${this.pn(targetId)}的护盾抵扣${blocked}点伤害`);
        }
        if (actual > 0 && this.hasEquipment(targetId, 'MagicCotton')) {
            const spent = Math.min(Math.max(0, toInt(ps.magic, 0)), Math.ceil(actual / 4));
            if (spent > 0) {
                const blocked = Math.min(actual, spent * 4);
                ps.magic -= spent;
                actual -= blocked;
                this.logMsg(`${this.pn(targetId)}的魔法棉花消耗${spent}M抵扣${blocked}点伤害`);
            }
        }
        return actual;
    }

    applyElectricWebDrawDamage(playerId, drawnCount) {
        const ps = this.players[playerId];
        if (!ps) return;
        const perCard = toInt(ps.custom_vars.electric_web_draw_damage, 0);
        const count = Math.max(0, toInt(drawnCount, 0));
        if (perCard <= 0 || count <= 0) return;
        const total = perCard * count;
        this.dealDirectDamage(playerId, total, '电网', playerId, {
            damage_type: 'magic',
            damage_tag: 'factory:electric_web',
        });
        this.logMsg(`${this.pn(playerId)}的电网效果：抽${count}张牌，受到${total}电伤`);
    }

    iterEquipmentTargetingPlayer(playerId) {
        const out = [];
        this.players.forEach((ownerState, ownerId) => {
            (ownerState.equipment || []).forEach(eq => {
                const effectTarget = toInt(eq && (eq.effect_target ?? eq.owner), ownerId);
                if (effectTarget === playerId) out.push({ ownerId, eq });
            });
        });
        return out;
    }

    dealDirectDamage(playerId, amount, source = '', sourceId = null, damageMeta = null) {
        const ps = this.players[playerId];
        if (!ps || (ps.invincible && !this.isStatusImmune(playerId))) {
            if (ps) this.logMsg(`${this.pn(playerId)}无敌，免疫${source}伤害`);
            return 0;
        }
        let actual = this.applyCorruptionMultiplier(amount);
        actual = this.applyUniversalDamageShields(playerId, actual, sourceId, source);
        ps.health -= actual;
        this.recordDamage(playerId, actual, sourceId);
        this.logMsg(`${this.pn(playerId)}受到${actual}点${source}伤害（H=${ps.health}）`);
        if (!this._deferTurnStartDeathChecks) {
            this.checkYggdrasil(playerId);
            this.checkGameOver();
        }
        return actual;
    }

    dealAttackDamage(targetId, amount, hits = 1, isPrecision = false, attackerId = 1 - targetId, sourceCard = null) {
        const ps = this.players[targetId];
        const immune = this.isStatusImmune(targetId);
        if (!ps || (ps.untargetable && !immune)) {
            if (ps) this.logMsg(`${this.pn(targetId)}无法被攻击选中`);
            return 0;
        }
        let total = 0;
        if (!Array.isArray(this._last_positive_damage_hits) || this._last_positive_damage_hits.length !== this.players.length) {
            this._last_positive_damage_hits = Array(this.players.length).fill(0);
        }
        this._last_positive_damage_hits[targetId] = 0;
        for (let h = 0; h < hits; h++) {
            let precisionDodged = false;
            let plankBlocksAttack = false;
            if (ps.dodge > 0 && !immune) {
                ps.dodge -= 1;
                if (!isPrecision) {
                    this.logMsg(`${this.pn(targetId)}闪避了攻击`);
                    continue;
                }
                precisionDodged = true;
                if (!this.suppressPrecisionDodgeLog) {
                    this.logMsg(`${this.pn(targetId)}的闪避被精准消耗`);
                }
            }
            if (ps.invincible && !immune) {
                this.logMsg(`${this.pn(targetId)}无敌，免疫伤害`);
                continue;
            }
            if (sourceCard && this.hasEquipment(targetId, 'Plank')) {
                try {
                    if (toInt(sourceCard.cost_e, 0) <= 1) {
                        plankBlocksAttack = true;
                    }
                } catch (e) {}
            }
            let power = 0;
            if (sourceCard) {
                power = Math.max(0, toInt(sourceCard.power_value, 0));
            }
            let dmg = Math.max(0, toInt(amount, 0)) + Math.ceil(power / Math.max(1, toInt(hits, 1)));
            if (this.halve_next_attack) dmg = Math.ceil(dmg / 2);
            else if (precisionDodged) dmg = Math.ceil(dmg / 2);
            dmg = this.applyCorruptionMultiplier(dmg);
            dmg += this.damageDealtEquipmentFlatBonus(attackerId);
            if (plankBlocksAttack) dmg = 0;
            let nazarStacks = immune ? 0 : this.nazarStatusValue(targetId);
            if (dmg > 0 && nazarStacks > 0) {
                const original = dmg;
                dmg = Math.max(1, dmg - 9);
                if (original >= 10) {
                    this.setNazarStatusValue(targetId, nazarStacks - 1);
                }
            }
            const rootArmor = immune ? 0 : this.customStatusValue(targetId, 'jungle:root', 'jungle:root_status', 'root_status');
            const fragile = immune ? 0 : this.customStatusValue(targetId, 'jungle:fragile', 'fragile');
            dmg = Math.max(0, dmg - ps.armor - rootArmor + fragile);
            if (ps.sponge_active && dmg > 0 && !immune) {
                const converted = Math.min(10, Math.floor(dmg / 2));
                ps.poison += converted;
                dmg = 0;
            }
            dmg = this.applyUniversalDamageShields(targetId, dmg, attackerId, '攻击');
            ps.health -= dmg;
            total += dmg;
            if (dmg > 0) this._last_positive_damage_hits[targetId] += 1;
            this.recordDamage(targetId, dmg, attackerId);
            this.logMsg(`${this.pn(targetId)}受到${dmg}点伤害（H=${ps.health}）`);
            if (dmg > 0) {
                const rootLayers = this.customStatusValue(targetId, 'jungle:root', 'jungle:root_status', 'root_status');
                if (rootLayers > 0) {
                    this.setCustomStatusAliasGroup(targetId, 'jungle:root_status', ['jungle:root_status', 'jungle:root', 'root_status'], rootLayers - 1);
                    this.consumeJungleRootLayerFromEquipment(targetId);
                }
            }
            if (dmg > 0 && ps.toxic > 0 && !immune) ps.poison += ps.toxic;
            this._game_over_defer_depth += 1;
            try {
                this.checkYggdrasil(targetId);
                if (dmg > 0) {
                    this.iterEquipmentTargetingPlayer(targetId).forEach(({ ownerId, eq }) => {
                        if (this.cardIs(eq.card_instance || eq, 'Battery', 'vanilla:battery')) {
                            const dealt = this.dealDirectDamage(attackerId, 3, '电池电击', targetId, {
                                damage_type: 'magic',
                                damage_tag: 'gtn:battery',
                            });
                            if (dealt > 0) {
                                this.logMsg(`${this.pn(targetId)}的电池效果：对${this.pn(attackerId)}造成3电伤`);
                            } else {
                                this.logMsg(`${this.pn(targetId)}的电池触发，但${this.pn(attackerId)}未受到电伤`);
                            }
                        } else if (this.cardIs(eq.card_instance || eq, 'MagicBattery', 'vanilla:magicbattery')) {
                            const ownerState = this.players[ownerId];
                            if (ownerState && ownerState.magic_battery_m_this_turn < 3) {
                                ownerState.gainMagic(1);
                                ownerState.magic_battery_m_this_turn += 1;
                                ownerState.custom_vars['魔法电池本回合回魔'] = ownerState.magic_battery_m_this_turn;
                                this.logMsg(`${this.pn(ownerId)}的魔法电池效果：+1M`);
                            }
                        } else if (this.hasCardEvent(eq.card_def, 'damage_taken')) {
                            this.runCardEvent(targetId, eq.card_instance, 'damage_taken', null, {
                                event: 'damage_taken',
                                source_id: attackerId,
                                target_id: targetId,
                                damage: dmg,
                                selected_equipment_instance_id: eq.card_instance && eq.card_instance.instance_id,
                                selected_equipment_owner_id: ownerId,
                            });
                        }
                    });
                }
            } finally {
                this._game_over_defer_depth -= 1;
            }
            if (ps.health <= 0 || this.players[attackerId].health <= 0) {
                this.checkGameOver();
                break;
            }
        }
        return total;
    }

    currentTurnMarker() {
        return toInt(this.current_player, -1);
    }

    setInvincibleUntilNextOwnTurnEnd(playerId) {
        const ps = this.players[playerId];
        if (!ps) return;
        if (this.isStatusImmune(playerId)) return;
        ps.invincible = true;
        ps.invincible_until_player = playerId;
        ps.invincible_granted_round = toInt(this.round_num, 0);
        ps.invincible_granted_turn_marker = this.currentTurnMarker();
    }

    clearInvincibleState(playerId) {
        const ps = this.players[playerId];
        if (!ps) return;
        ps.invincible = false;
        ps.invincible_until_player = null;
        ps.invincible_granted_round = -1;
        ps.invincible_granted_turn_marker = -1;
    }

    shouldExpireInvincibleOnTurnEnd(playerId) {
        const ps = this.players[playerId];
        if (!ps || !ps.invincible) return false;
        if (ps.invincible_until_player != null && ps.invincible_until_player !== playerId) return false;
        return !(toInt(ps.invincible_granted_round, -1) === toInt(this.round_num, 0)
            && toInt(ps.invincible_granted_turn_marker, -1) === this.currentTurnMarker());
    }

    clearYggdrasilEffects(playerId) {
        const ps = this.players[playerId];
        if (!ps) return;
        ['poison', 'fire', 'vulnerable', 'toxic', 'triangle_stacks', 'dodge', 'armor', 'equipment_protection'].forEach(prop => { ps[prop] = 0; });
        ps.nazar_active = false;
        ps.nazar_big_hits = 0;
        ps.negate_next_skill = false;
        ps.skip_turn = false;
        ps.damage_multiplier = 1.0;
        ps.bandage_active = false;
        ps.bandage_death_pending = false;
        this.clearInvincibleState(playerId);
        ps.custom_statuses = {};
        ps.custom_vars['三角形层数'] = 0;
    }

    triggerYggdrasilEffect(targetId, card = null, sourcePlayerId = null, options = {}) {
        const ps = this.players[targetId];
        if (!ps) return false;
        const wasDead = ps.health <= 0;
        ps.health = 5;
        this.clearYggdrasilEffects(targetId);
        this.setInvincibleUntilNextOwnTurnEnd(targetId);
        const drawn = ps.drawCards(3);
        if (card) {
            if (options.exileFromHand) {
                const idx = ps.hand.findIndex(c => c.instance_id === card.instance_id);
                if (idx >= 0) ps.hand.splice(idx, 1);
                this.putCardInExile(targetId, card);
            } else if (options.exilePlayedCard) {
                card.instance_flags.add('exile');
            }
        }
        const actorText = sourcePlayerId != null && sourcePlayerId !== targetId
            ? `${this.pn(sourcePlayerId)}的世界树之叶使`
            : `${this.pn(targetId)}的世界树之叶`;
        const reviveText = wasDead ? '复活，' : '';
        this.logMsg(`${actorText}${this.pn(targetId)}${reviveText}生命值设为5，抽${drawn.length}张牌，清除所有效果，无敌直到下一个自己回合结束！`);
        return true;
    }

    effectYggdrasil(playerId, card, choice = null) {
        let targetId = this.choiceTargetFromChoice(choice, playerId);
        if (!this.players[targetId]) targetId = playerId;
        if (this.players[targetId].health <= 0) {
            this.triggerYggdrasilEffect(targetId, card, playerId, { exilePlayedCard: true });
        } else {
            this.players[targetId].heal(20);
            this.logMsg(`${this.pn(playerId)}使用世界树之叶！${this.pn(targetId)}回复20H`);
        }
    }

    checkYggdrasil(playerId) {
        const ps = this.players[playerId];
        if (!ps || ps.health > 0) return;
        if (ps.bandage_active && !this.isStatusImmune(playerId)) {
            ps.health = 1;
            this.setInvincibleUntilNextOwnTurnEnd(playerId);
            ps.bandage_active = false;
            ps.bandage_death_pending = true;
            this.logMsg(`${this.pn(playerId)}的绷带发动！无敌直到下一个自己回合结束，然后死亡`);
            return;
        }
        const idx = ps.hand.findIndex(card => card.def_id === 'Yggdrasil');
        if (idx >= 0) {
            this.triggerYggdrasilEffect(playerId, ps.hand[idx], null, { exileFromHand: true });
        }
    }

    checkGameOver() {
        if (this._game_over_defer_depth > 0) return;
        if (this.players[0].health <= 0 && this.players[1].health <= 0) {
            this.game_over = true;
            this.winner = -1;
            this.phase = 'game_over';
            this.logMsg('双方生命值同时归零！平局！');
            return;
        }
        for (let i = 0; i < 2; i++) {
            if (this.players[i].health <= 0) {
                this.game_over = true;
                this.winner = 1 - i;
                this.phase = 'game_over';
                this.logMsg(`${this.pn(i)}生命值归零！${this.pn(this.winner)}获胜！`);
                return;
            }
        }
    }

    resetOneShotAttackAttrs(card) {
        card.fission_level = 1;
        card.fusion_level = 1;
        card.fission_count = 0;
        card.fusion_multiplier = 1.0;
        card.fission_hit = 0;
    }

    resetCardAfterPlay(card) {
        const preserveFission = card && (card.flags.has('preserve_fission') || card.instance_flags.has('preserve_fission'));
        const preservedFissionLevel = preserveFission ? Math.max(1, toInt(card.fission_level, 1)) : 1;
        if (card.card_type === 'thorn') this.resetOneShotAttackAttrs(card);
        if (preserveFission) {
            card.fission_level = preservedFissionLevel;
            card.fission_count = Math.max(0, preservedFissionLevel - 1);
            card.fission_hit = 0;
        }
        card.cost_e_override = null;
        card.cost_m_override = null;
        card.mimic_discount = 0;
        card.power_value = 0;
        card.temp_swift_value = 0;
        card.temp_heavy_value = 0;
        card.temp_magic_heavy_value = 0;
        card.instance_flags.delete('power');
        card.instance_flags.delete('temp_swift');
        card.instance_flags.delete('temp_heavy');
    }

    resetCardForDiscard(card) {
    }

    discardCard(ps, card) {
        ps.discard.push(card);
    }

    isVoidAntimatter(card) {
        if (!card) return false;
        const id = String(card.def_id || '');
        const def = card.def && card.def();
        const legacy = String((def && def.legacy_id) || '');
        return id === 'Antimatter' || id === 'void:antimatter' || legacy === 'Antimatter';
    }

    putCardInExile(ownerId, card, trigger = true) {
        const ps = this.players[ownerId];
        if (!ps || !card) return;
        const alreadyExiled = ps.exile.includes(card);
        if (!alreadyExiled) ps.exile.push(card);
        if (trigger && !alreadyExiled && this.isVoidAntimatter(card)) {
            this.effect_void_damage_all_except_self(ownerId, card, { amount: 10 });
        }
    }

    destroyEquipment(ownerId, eq) {
        const ps = this.players[ownerId];
        if (!eq || !ps.equipment.includes(eq)) return false;
        if (eq.card_instance && eq.card_instance.flags && eq.card_instance.flags.has('indestructible')) return false;
        if (toInt(eq.armor, 0) > 0) {
            eq.armor = Math.max(0, toInt(eq.armor, 0) - 1);
            this.logMsg(`${this.pn(ownerId)}的${cardName(eq.def_id)}装备护甲抵消了摧毁（剩余${eq.armor}）`);
            return false;
        }
        if (ps.equipment_protection > 0) {
            ps.equipment_protection -= 1;
            this.logMsg(`${this.pn(ownerId)}的装备保护抵消了摧毁！`);
            return false;
        }
        const effectTarget = Math.max(0, Math.min(this.players.length - 1, toInt(eq.effect_target ?? eq.owner ?? ownerId, ownerId)));
        if (this.hasCardEvent(eq.card_def, 'equipment_destroy')) {
            this.runCardEvent(ownerId, eq.card_instance, 'equipment_destroy', null, {
                event: 'equipment_destroy',
                source_id: ownerId,
                target_id: effectTarget,
                equipment_owner_id: ownerId,
            });
        }
        this.cleanupEquipmentDerivedEffects(ownerId, eq);
        ps.equipment.splice(ps.equipment.indexOf(eq), 1);
        if (eq.card_instance.flags.has('exile')) this.putCardInExile(ownerId, eq.card_instance);
        else this.discardCard(ps, eq.card_instance);
        this.dispatchCardEvent('equipment_destroyed', ownerId, eq.card_instance, effectTarget, eq, ownerId);
        return true;
    }

    getExtraEForCard(playerId, card) {
        let extra = card.flags.has('symbiosis') ? 0 : this.cardsPlayedThisTurnCount(this.players[playerId], card);
        if (this.cardIs(card, 'Bamboo', 'jungle:bamboo')) {
            const otherBamboo = this.players[playerId].hand.filter(c => c !== card && this.cardIs(c, 'Bamboo', 'jungle:bamboo')).length;
            extra -= otherBamboo;
        }
        return extra;
    }

    cardLocalIds(card) {
        const ids = new Set();
        if (!card) return [];
        const push = value => {
            if (value !== undefined && value !== null && String(value)) ids.add(String(value));
        };
        push(card.def_id);
        const def = typeof card.def === 'function' ? card.def() : null;
        push(def && def.id);
        push(def && def.legacy_id);
        const resource = def && def.v2_resource;
        if (resource && typeof resource === 'object') {
            push(resource.id);
            push(resource.legacy_id);
            push(resource.runtime_id);
        }
        return Array.from(ids);
    }

    cardsPlayedThisTurnCount(ps, card) {
        const played = (ps && ps.cards_played_this_turn) || {};
        const ids = this.cardLocalIds(card);
        if (!ids.length && card && card.def_id) ids.push(String(card.def_id));
        return ids.reduce((sum, id) => sum + toInt(played[id], 0), 0);
    }

    customStatusValue(playerId, ...names) {
        const ps = this.players[playerId];
        const statuses = (ps && ps.custom_statuses) || {};
        if (!ps) return 0;
        return names.reduce((maxValue, name) => {
            const key = String(name || '');
            return Math.max(maxValue, Math.max(0, toInt(statuses[key], 0)), Math.max(0, toInt(ps[key], 0)));
        }, 0);
    }

    nazarStatusValue(playerId) {
        const ps = this.players[playerId];
        if (!ps) return 0;
        let value = this.customStatusValue(playerId, 'nazar', '邪眼', 'Nazar');
        if (ps.nazar_active) value += Math.max(0, 2 - Math.max(0, toInt(ps.nazar_big_hits, 0)));
        return Math.max(0, value);
    }

    setNazarStatusValue(playerId, value) {
        const ps = this.players[playerId];
        if (!ps) return;
        ps.nazar_active = false;
        ps.nazar_big_hits = 0;
        ps.custom_statuses = ps.custom_statuses || {};
        delete ps.custom_statuses['邪眼'];
        delete ps.custom_statuses.Nazar;
        const amount = Math.max(0, toInt(value, 0));
        if (amount > 0) ps.custom_statuses.nazar = amount;
        else delete ps.custom_statuses.nazar;
    }

    isStatusImmune(playerId) {
        const ps = this.players[playerId];
        if (!ps) return false;
        const custom = ps.custom_statuses || {};
        return ['status_immune', 'immune', '状态免疫'].some(key => toInt(custom[key], 0) > 0 || toInt(ps[key], 0) > 0);
    }

    statusApplicationBlocked(playerId, status) {
        if (!this.players[playerId]) return true;
        return false;
    }

    actionLimitStatusValue(playerId, attr, ...aliases) {
        const ps = this.players[playerId];
        if (!ps) return 0;
        if (this.isStatusImmune(playerId)) return 0;
        return Math.max(Math.max(0, toInt(ps[attr], 0)), this.customStatusValue(playerId, ...aliases));
    }

    decayActionLimitStatus(playerId, attr, ...aliases) {
        const ps = this.players[playerId];
        if (!ps) return;
        if (toInt(ps[attr], 0) > 0) ps[attr] = Math.max(0, toInt(ps[attr], 0) - 1);
        ps.custom_statuses = ps.custom_statuses || {};
        aliases.forEach(name => {
            const value = toInt(ps.custom_statuses[name], 0);
            if (value > 1) ps.custom_statuses[name] = value - 1;
            else if (value > 0) delete ps.custom_statuses[name];
        });
    }

    canPlayCard(playerId, card) {
        const ps = this.players[playerId];
        const def = card.def();
        if (def.card_type === 'guard' && !hasScriptEntry(def, 'play') && !(def.effects || []).length) {
            return [false, '反制牌只能通过响应机制使用'];
        }
        if (this.phase !== 'action' || (this.current_player !== playerId && this.allowOutOfTurnAutoPlayFor !== playerId)) return [false, '不是你的回合'];
        if (this.actionLimitStatusValue(playerId, 'attack_blocked', 'attack_blocked', '禁攻') > 0 && def.card_type === 'thorn') return [false, '本回合无法使用攻击牌'];
        if (this.actionLimitStatusValue(playerId, 'attack_only', 'attack_only', '仅攻击') > 0 && def.card_type !== 'thorn') return [false, '本回合只能使用攻击牌'];
        if (ps.shovel_active) return [false, '链子效果中，无法使用卡牌'];
        const totalE = Math.max(0, card.cost_e + this.getExtraEForCard(playerId, card));
        if (totalE > ps.elixir) return [false, `能量不足（需要${totalE}E，当前${ps.elixir}E）`];
        if (card.cost_m > ps.magic) return [false, `魔力不足（需要${card.cost_m}M，当前${ps.magic}M）`];
        return [true, ''];
    }

    wouldDestroyEquipment(card) {
        if (['Sewage', 'MagicSewage'].includes(card.def_id)) return true;
        return playEffectsFor(card).some(effect => {
            const type = effect && effect.type;
            return ['remove_specific_card', 'destroy_equipment_choice_or_first', 'destroy_random_equip', 'destroy_all_equip', 'destroy_all_destroyable_equipment'].includes(type);
        });
    }

    wouldHeal(card) {
        const def = card.def();
        if (toInt(def.heal, 0) > 0 || toInt(card.heal, 0) > 0) return true;
        return playEffectsFor(card).some(effect => {
            if (!effect || typeof effect !== 'object') return false;
            const type = String(effect.type || '');
            const params = effect.params || {};
            if (type === 'heal' || type === 'drain_damage') return true;
            if (type === 'player_prop_add' && String(params.property || '') === 'health') return true;
            return false;
        });
    }

    checkResponseNeeded(playerId, card) {
        if (card.flags.has('precision')) return false;
        const opp = this.players[1 - playerId];
        const trigger = card.card_type;
        if (opp.hand.some(c => this.canPayCounterCard(1 - playerId, c) && c.def().response_trigger === 'any')) return true;
        if (opp.hand.some(c => this.canPayCounterCard(1 - playerId, c) && c.def().response_trigger === trigger)) return true;
        if (this.wouldDestroyEquipment(card) && opp.hand.some(c => this.canPayCounterCard(1 - playerId, c) && c.def().response_trigger === 'equipment_destroy')) return true;
        if (this.wouldHeal(card) && opp.hand.some(c => this.canPayCounterCard(1 - playerId, c) && c.def().response_trigger === 'heal')) return true;
        return false;
    }

    checkPrecisionResponseNeeded(playerId, card) {
        if (!card.flags.has('precision')) return false;
        return this.players[1 - playerId].hand.some(c => this.canPayCounterCard(1 - playerId, c) && c.def().response_trigger === 'thorn');
    }

    canPayCounterCard(playerId, card) {
        const ps = this.players[playerId];
        return !!ps && !!card && card.cost_e <= ps.elixir && card.cost_m <= ps.magic;
    }

    getCounterCards(playerId, playedCard) {
        const def = playedCard.def();
        const triggerTypes = ['any'];
        if (def.card_type) triggerTypes.push(def.card_type);
        if (this.wouldDestroyEquipment(playedCard)) triggerTypes.push('equipment_destroy');
        if (this.wouldHeal(playedCard)) triggerTypes.push('heal');
        return this.players[playerId].hand.filter(card => triggerTypes.includes(card.def().response_trigger));
    }

    playCard(playerId, instanceId, choice = null) {
        const ps = this.players[playerId];
        const card = ps.findHandCard(instanceId);
        if (!card) return { success: false, error: '卡牌不在手中' };
        if (card.def_id === ERROR_CARD_ID) {
            ps.removeHandCard(instanceId);
            return { success: true, card: card.toDict(), ignored: true };
        }
        if (this.pending_response) return { success: false, error: '等待对手反制响应' };
        if (card.def().card_type === 'thorn') {
            if (card.flags && card.flags.has('wide_strike')) {
                if (!this.wideStrikeTargetIds(playerId, card).length) {
                    return { success: false, error: '没有可选中的玩家' };
                }
            } else {
                const targetId = this.resolveTarget(playerId, choice && choice.target_player_id != null ? choice.target_player_id : 'enemy');
                const allowsSelf = card.flags && card.flags.has('self_target');
                if (targetId < 0 || targetId >= this.players.length || (targetId === playerId && !allowsSelf)) {
                    return { success: false, error: '没有可选中的玩家' };
                }
            }
        }
        if (this._auto_resolve_choices_for === playerId && this.cardNeedsChoice(card) && !this.choiceSatisfiesRequest(card, choice)) {
            const choiceRequest = this.getChoiceRequest(card, choice);
            const choiceParams = (choiceRequest && choiceRequest.params) || {};
            const choiceType = this.choiceTypeForEffect(choiceRequest);
            let choiceTargetId = null;
            if (choiceRequest && choiceRequest.type === 'request_card') {
                choiceTargetId = this.resolveTarget(playerId, choiceParams.target || 'self');
            }
            const pendingPreview = {
                card: card.toDict(),
                player_id: playerId,
                choice_type: choiceType,
                choice_params: choiceParams,
                target_player_id: choiceTargetId != null ? choiceTargetId : (choice && (choice.target_player_id ?? choice.target_player ?? choice.target_id)),
            };
            const generated = this.defaultAutoChoiceForPending(pendingPreview);
            if (generated) choice = { ...(choice || {}), ...generated };
        }
        const [canPlay, reason] = this.canPlayCard(playerId, card);
        const autoNoCost = this._auto_play_no_cost_for === playerId;
        if (!canPlay && !(autoNoCost && (String(reason).includes('能量不足') || String(reason).includes('魔力不足')))) return { success: false, error: reason };
        if (this.cardNeedsChoice(card) && !this.choiceSatisfiesRequest(card, choice)) {
            const queued = this.queueCardChoice(playerId, card, choice, false);
            if (queued) return queued;
        }
        const totalE = autoNoCost ? 0 : Math.max(0, card.cost_e + this.getExtraEForCard(playerId, card));
        const totalM = autoNoCost ? 0 : card.cost_m;
        card._paid_e_this_play = totalE;
        card._paid_m_this_play = totalM;
        this.spendResource(playerId, 'elixir', totalE, card);
        this.spendResource(playerId, 'magic', totalM, card);
        ps.cards_played_this_turn[card.def_id] = toInt(ps.cards_played_this_turn[card.def_id], 0) + 1;
        const removed = ps.removeHandCard(instanceId);
        if (!removed) return { success: false, error: '移出手牌失败' };
        ps.cards_played_this_turn_instance_ids.push(toInt(card.instance_id, instanceId));
        this.applyMagicAccelerationAfterPlay(playerId, card);
        const responseResult = this.checkCardResponseAfterChoice(playerId, card, choice);
        if (responseResult) return responseResult;
        return this.executeCardEffect(playerId, card, choice);
    }

    logCardPlay(playerId, card) {
        this.logMsg(`${this.pn(playerId)}使用了${cardName(card.def_id)}`);
    }

    executeCardEffect(playerId, card, choice = null) {
        const ps = this.players[playerId];
        const result = { success: true, card: card.toDict() };
        if (card.card_type === 'thorn' && (card.fission_level > 1 || card.fusion_level > 1)) {
            this.logMsg(`[特效] ${cardName(card.def_id)} 聚变=${card.fusion_level} 裂变=${card.fission_level}`);
        }
        if (this.negated_card && card.card_type === 'bloom') {
            this.negated_card = false;
            this.logCardPlay(playerId, card);
            this.logMsg(`${this.pn(playerId)}的${cardName(card.def_id)}被魔法泡泡反制，失效！`);
            this.resetCardAfterPlay(card);
            if (card.flags.has('exile')) this.putCardInExile(playerId, card);
            else this.discardCard(ps, card);
            this.dispatchCardEvent('card_used', playerId, card, playerId, null, null, choice);
            result.countered = true;
            result.negated = true;
            return result;
        }
        this.negated_card = false;
        if (card.card_type === 'bloom') {
            const opponentId = 1 - playerId;
            const opponent = this.players[opponentId];
            const stacks = opponent ? toInt(opponent.custom_statuses.magic_nazar, 0) : 0;
            const paidE = card._paid_e_this_play != null ? toInt(card._paid_e_this_play, 0) : Math.max(0, toInt(card.cost_e, 0));
            if (opponent && stacks > 0 && paidE <= 1) {
                this.logCardPlay(playerId, card);
                opponent.custom_statuses.magic_nazar = stacks - 1;
                if (opponent.custom_statuses.magic_nazar <= 0) delete opponent.custom_statuses.magic_nazar;
                this.logMsg(`${this.pn(opponentId)}的魔法邪眼使${this.pn(playerId)}的${cardName(card.def_id)}失效`);
                this.resetCardAfterPlay(card);
                if (card.flags.has('exile')) this.putCardInExile(playerId, card);
                else this.discardCard(ps, card);
                this.dispatchCardEvent('card_used', playerId, card, playerId, null, null, choice);
                return result;
            }
        }
        if (this.cardNeedsChoice(card) && !this.choiceSatisfiesRequest(card, choice)) {
            const queued = this.queueCardChoice(playerId, card, choice, true);
            if (queued) return queued;
        }
        if (card.def_id === 'Mimic' && choice && choice.target_instance_id != null) {
            const target = ps.findHandCard(choice.target_instance_id);
            if (target && !this.canPayMimicSpecialCost(playerId, target)) {
                ps.hand.unshift(card);
                ps.elixir += this.paidEForRefund(playerId, card);
                ps.magic += card.cost_m;
                ps.cards_played_this_turn[card.def_id] = Math.max(0, toInt(ps.cards_played_this_turn[card.def_id], 1) - 1);
                return { success: false, error: '能量不足' };
            }
        }
        const playLogMarker = this.log.length;
        if (playEffectsFor(card).length) {
            this.logCardPlay(playerId, card);
        }
        if (card.card_type === 'thorn') {
            const fission = Math.max(1, toInt(card.fission_level, 1));
            for (let i = 0; i < fission; i++) {
                if (this.game_over) break;
                card.fission_hit = i;
                this.applyCardEffect(playerId, card, choice);
            }
            card.fission_hit = 0;
        } else {
            this.applyCardEffect(playerId, card, choice);
        }
        if (this.pending_choice) {
            if (this._auto_resolve_choices_for === playerId) {
                const autoChoice = this.defaultAutoChoiceForPending(this.pending_choice);
                if (autoChoice) {
                    const autoResult = this.resolveChoice(playerId, autoChoice);
                    if (!this.pending_choice) return autoResult || { success: true };
                }
            }
            if (this.pending_choice.choice_type !== 'magic_salt_reflect') {
                const keepPaidChoice = this.pending_choice.choice_type === 'choose_ocean_sapphire';
                if (keepPaidChoice) {
                    this.pending_choice.play_log_marker = playLogMarker;
                } else {
                    this.undoMagicAccelerationAfterPendingChoice(playerId, card);
                    const expected = `${this.pn(playerId)}使用了${cardName(card.def_id)}`;
                    if (this.log[playLogMarker] === expected) this.log.splice(playLogMarker, 1);
                    if (!ps.findHandCard(card.instance_id)) {
                        ps.hand.unshift(card);
                        ps.elixir += this.paidEForRefund(playerId, card);
                        ps.magic += card.cost_m;
                        ps.cards_played_this_turn[card.def_id] = Math.max(0, toInt(ps.cards_played_this_turn[card.def_id], 1) - 1);
                    }
                }
                return {
                    success: true,
                    needs_choice: true,
                    choice_type: this.pending_choice.choice_type || '',
                    choice_params: this.pending_choice.choice_params || {},
                    target_player_id: this.pending_choice.target_player_id,
                    card: card.toDict(),
                    hand_cards: this.pending_choice.hand_cards || [],
                    deck_cards: this.pending_choice.deck_cards || [],
                    discard_cards: this.pending_choice.discard_cards || [],
                    message: this.pending_choice.message || '',
                };
            }
        }
        const equipOwnerId = card._placed_as_equipment_owner != null ? card._placed_as_equipment_owner : playerId;
        const playScripts = (card.def() && card.def().scripts) || {};
        const scriptControlsPlay = (SCRIPT_ENTRY_ALIASES.play || ['play']).some(key =>
            Object.prototype.hasOwnProperty.call(playScripts, key)
            && scriptEffectsFrom(playScripts[key]).length > 0
        );
        this.resetCardAfterPlay(card);
        if ((card.card_type === 'root' && !scriptControlsPlay) || card._placed_as_equipment) {
            if (!this.findEquipmentForCard(equipOwnerId, card)) {
                const eq = new LocalEquipment(card, equipOwnerId);
                this.players[equipOwnerId].equipment.push(eq);
                this.logMsg(`${this.pn(equipOwnerId)}装备了${cardName(card.def_id)}`);
            }
        } else if (card.flags.has('rebound')) {
            ps.addToHand(card);
            this.logMsg(`${this.pn(playerId)}的${cardName(card.def_id)}因回转回到手中`);
        } else if (card.flags.has('exile')) {
            const loc = this.findCardLocation(card);
            if (!loc) this.putCardInExile(playerId, card);
            this.logMsg(`${this.pn(playerId)}的${cardName(card.def_id)}被放逐`);
        } else {
            const loc = this.findCardLocation(card);
            if (!loc) this.discardCard(ps, card);
        }
        const targetId = choice && (choice.target_player ?? choice.target_player_id ?? choice.target_id);
        this.dispatchCardEvent('card_used', playerId, card, targetId == null ? playerId : toInt(targetId, playerId), null, null, choice);
        this.checkGameOver();
        return result;
    }

    applyCardEffect(playerId, card, choice = null) {
        if (card && card.def_id === 'Yggdrasil') {
            this.effectYggdrasil(playerId, card, choice);
            return;
        }
        const effects = playEffectsFor(card);
        if (effects.length) {
            const handlesWideStrikeInternally = effects.some(effect => [
                'ocean_for_each_selectable_target',
                'ocean_spikeball_damage',
            ].includes(String(effect && effect.type || '')));
            if (card.flags.has('wide_strike') && !handlesWideStrikeInternally) {
                this.wideStrikeTargetIds(playerId, card).forEach(targetId => {
                    const targetChoice = {
                        ...(choice || {}),
                        target_player_id: targetId,
                        target_player: targetId,
                        target_id: targetId,
                    };
                    this.runEffectList(playerId, card, effects, targetChoice, {
                        event: 'play',
                        source_id: playerId,
                        target_id: targetId,
                        target_player: targetId,
                    });
                });
            } else {
                this.runEffectList(playerId, card, effects, choice, {
                    event: 'play',
                    source_id: playerId,
                    target_id: this.resolveTarget(playerId, choice && choice.target_player_id != null ? choice.target_player_id : 'enemy'),
                });
            }
            return;
        }
        if (card.card_type === 'thorn' && toInt(card.damage, 0) > 0) {
            const amount = this.modifiedAttackDamage(toInt(card.damage, 0), card);
            const hits = Math.max(1, toInt(card.hits, 1));
            const targets = card.flags.has('wide_strike')
                ? this.wideStrikeTargetIds(playerId, card)
                : [this.resolveTarget(playerId, choice && choice.target_player_id != null ? choice.target_player_id : 'enemy')];
            targets.forEach(targetId => {
                this.dealAttackDamage(targetId, amount, hits, card.flags.has('precision'), playerId, card);
            });
            return;
        }
        this.logMsg(`${this.pn(playerId)}使用了${cardName(card.def_id)}`);
    }

    executeCardEffectHalfDamage(playerId, card, choice = null) {
        this.halve_next_attack = true;
        this.suppressPrecisionDodgeLog = true;
        this.logMsg(`${this.pn(playerId)}的精准牌被闪避反制，伤害减半！`);
        let result;
        try {
            result = this.executeCardEffect(playerId, card, choice);
        } finally {
            this.halve_next_attack = false;
            this.suppressPrecisionDodgeLog = false;
        }
        return result;
    }

    resolveChoice(playerId, choice) {
        if (!this.pending_choice) return { success: false, error: '没有待选择操作' };
        const pending = this.pending_choice;
        this.pending_choice = null;
        if (pending.original_choice && typeof pending.original_choice === 'object') {
            choice = choice && typeof choice === 'object'
                ? { ...pending.original_choice, ...choice }
                : { ...pending.original_choice };
        }
        const card = new LocalCard(pending.card);
        const ps = this.players[playerId];
        const choiceCancelled = choice == null || (typeof choice === 'object' && (choice.cancelled || choice.cancel));
        if (pending.choice_type === 'magic_salt_reflect') {
            if (choiceCancelled || !(choice && (choice.confirmed || choice.accepted))) {
                return { success: true, cancelled: true };
            }
            const params = pending.choice_params || {};
            const ownerId = toInt(params.owner_id, playerId);
            const attackerId = toInt(params.attacker_id, -1);
            const damage = Math.max(0, toInt(params.damage, 0));
            if (!this.players[ownerId] || !this.players[attackerId] || damage <= 0) {
                return { success: false, error: '魔法盐反伤失败' };
            }
            const costM = Math.max(0, toInt(params.cost_m, 1));
            const owner = this.players[ownerId];
            if (owner.magic < costM) {
                this.logMsg(`${this.pn(ownerId)}的魔法盐魔力不足`);
                return { success: true, not_enough_magic: true };
            }
            if (costM > 0) this.spendResource(ownerId, 'magic', costM, card);
            const reflected = Math.max(0, Math.ceil(damage * Number(params.ratio ?? 0.5)));
            if (reflected <= 0) return { success: true };
            const dealt = this.dealDirectDamage(attackerId, reflected, '魔法盐反伤', ownerId, {
                damage_type: 'physical',
                damage_tag: 'gtn:magic_salt',
            });
            if (dealt > 0) this.logMsg(`${this.pn(ownerId)}消耗${costM}M，魔法盐对${this.pn(attackerId)}反弹${dealt}D`);
            return { success: true, reflected: dealt };
        }
        if (choiceCancelled) {
            if ((pending.choice_params || {}).cancellable === false) {
                this.pending_choice = pending;
                return { success: false, error: '此选择不能取消' };
            }
            if (pending.already_paid) {
                this.undoMagicAccelerationAfterPendingChoice(playerId, card);
                const marker = Number.isInteger(pending.play_log_marker) ? pending.play_log_marker : -1;
                const expected = `${this.pn(playerId)}使用了${cardName(card.def_id)}`;
                if (marker >= 0 && this.log[marker] === expected) this.log.splice(marker, 1);
                if (!ps.findHandCard(card.instance_id)) ps.hand.unshift(card);
                ps.elixir += this.paidEForRefund(playerId, card);
                ps.magic += card.cost_m;
                ps.cards_played_this_turn[card.def_id] = Math.max(0, toInt(ps.cards_played_this_turn[card.def_id], 1) - 1);
            } else if (!ps.findHandCard(card.instance_id)) {
                ps.hand.unshift(card);
            }
            return { success: false, cancelled: true, error: '选择已取消' };
        }
        if (!pending.already_paid) {
            const handCard = ps.findHandCard(card.instance_id);
            const costCard = handCard || card;
            const dupCount = toInt(ps.cards_played_this_turn[card.def_id], 0);
            card._paid_e_this_play = Math.max(0, costCard.cost_e + this.getExtraEForCard(playerId, costCard));
            card._paid_m_this_play = card.cost_m;
            this.spendResource(playerId, 'elixir', card._paid_e_this_play, card);
            this.spendResource(playerId, 'magic', card.cost_m, card);
            ps.cards_played_this_turn[card.def_id] = dupCount + 1;
            if (handCard) ps.removeHandCard(card.instance_id);
            this.applyMagicAccelerationAfterPlay(playerId, card);
        }
        if (this.cardNeedsChoice(card) && !this.choiceSatisfiesRequest(card, choice)) {
            return this.executeCardEffect(playerId, card, choice);
        }
        const responseResult = this.checkCardResponseAfterChoice(playerId, card, choice);
        if (responseResult) return responseResult;
        return this.executeCardEffect(playerId, card, choice);
    }

    handleResponse(responderId, instanceId) {
        if (!this.pending_response) return { success: false, error: '没有待响应的操作' };
        const pending = this.pending_response;
        this.pending_response = null;
        const playerId = pending.player_id;
        const card = new LocalCard(pending.card);
        const choice = pending.original_choice;
        if (instanceId != null) {
            const responder = this.players[responderId];
            const counter = responder.findHandCard(instanceId);
            const counterCostE = counter ? Math.max(0, toInt(counter.cost_e, 0)) : 0;
            const counterCostM = counter ? Math.max(0, toInt(counter.cost_m, 0)) : 0;
            if (!counter || counterCostE > responder.elixir || counterCostM > responder.magic) {
                return this.executeCardEffect(playerId, card, choice);
            }
            const trigger = counter.def().response_trigger;
            const playedType = card.card_type;
            const valid = trigger === 'any'
                || trigger === playedType
                || (this.wouldDestroyEquipment(card) && trigger === 'equipment_destroy')
                || (this.wouldHeal(card) && trigger === 'heal')
                || (pending.is_precision && trigger === 'thorn');
            if (!valid) return this.executeCardEffect(playerId, card, choice);
            this.spendResource(responderId, 'elixir', counterCostE, counter);
            this.spendResource(responderId, 'magic', counterCostM, counter);
            const removed = responder.removeHandCard(instanceId);
            this.logMsg(`${this.pn(responderId)}使用${cardName(removed.def_id)}进行反制！`);
            const dodgeBeforeCounter = toInt(responder.dodge, 0);
            const pendingDamagePrediction = this.simulatePendingResponseDamage(responderId, null);
            this.executeCounterEffect(responderId, removed, card, playerId, pendingDamagePrediction);
            if (removed.def_id === 'Bubble') {
                const result = pending.is_precision
                    ? this.executeCardEffectHalfDamage(playerId, card, choice)
                    : this.executeCardEffect(playerId, card, choice);
                if (!this.isStatusImmune(responderId)) {
                    responder.dodge = Math.min(toInt(responder.dodge, 0), dodgeBeforeCounter);
                }
                return result;
            }
            if (removed.def_id === 'MagicBubble') this.negated_card = true;
            return this.executeCardEffect(playerId, card, choice);
        }
        return this.executeCardEffect(playerId, card, choice);
    }

    executeCounterEffect(responderId, counterCard, originalCard, originalPlayerId, pendingDamagePrediction = null) {
        const effects = getScriptEffects(counterCard.def(), 'response');
        if (this.hasCardEvent(counterCard.def(), 'response')) {
            this.runCardEvent(responderId, counterCard, 'response', {
                target_player: originalPlayerId,
                target_player_id: originalPlayerId,
                target_id: originalPlayerId,
            }, {
                event: 'response',
                source_id: responderId,
                target_id: originalPlayerId,
                original_card_instance_id: originalCard && originalCard.instance_id,
                original_card_def_id: originalCard && originalCard.def_id,
                incoming_damage: toInt(pendingDamagePrediction && pendingDamagePrediction.total, 0),
                first_damage: toInt((pendingDamagePrediction && pendingDamagePrediction.parts && pendingDamagePrediction.parts[0]) || 0, 0),
                damage_amount: toInt(pendingDamagePrediction && pendingDamagePrediction.total, 0),
                incoming_damage_parts: (pendingDamagePrediction && Array.isArray(pendingDamagePrediction.parts)) ? [...pendingDamagePrediction.parts] : [],
            });
        } else if (effects.length) {
            this.runEffectList(responderId, counterCard, effects, null, {
                event: 'response',
                source_id: responderId,
                target_id: originalPlayerId,
                incoming_damage: toInt(pendingDamagePrediction && pendingDamagePrediction.total, 0),
                first_damage: toInt((pendingDamagePrediction && pendingDamagePrediction.parts && pendingDamagePrediction.parts[0]) || 0, 0),
                damage_amount: toInt(pendingDamagePrediction && pendingDamagePrediction.total, 0),
                incoming_damage_parts: (pendingDamagePrediction && Array.isArray(pendingDamagePrediction.parts)) ? [...pendingDamagePrediction.parts] : [],
            });
        } else if (counterCard.def_id === 'Bubble') {
            if (!this.statusApplicationBlocked(responderId, 'dodge')) {
                this.players[responderId].dodge += 1;
            }
        } else if (counterCard.def_id === 'Nazar') {
            if (!this.statusApplicationBlocked(responderId, 'nazar')) {
                this.setNazarStatusValue(responderId, this.nazarStatusValue(responderId) + 2);
            }
        } else if (counterCard.def_id === 'MagicNazar') {
            if (!this.statusApplicationBlocked(responderId, 'magic_nazar')) {
                this.players[responderId].custom_statuses.magic_nazar = toInt(this.players[responderId].custom_statuses.magic_nazar, 0) + 2;
            }
        } else if (counterCard.def_id === 'MagicBubble') {
            if (!this.statusApplicationBlocked(responderId, 'negate_next_skill')) {
                this.players[responderId].negate_next_skill = true;
            }
        }
        this.resetCardAfterPlay(counterCard);
        if (counterCard.flags.has('exile')) this.putCardInExile(responderId, counterCard);
        else this.discardCard(this.players[responderId], counterCard);
        this.dispatchCardEvent('card_used', responderId, counterCard, originalPlayerId == null ? responderId : originalPlayerId);
    }

    useTrigger(playerId, equipmentInstanceId, targetPlayerId = null) {
        if (this.current_player !== playerId) return { success: false, error: '不是你的回合' };
        const ps = this.players[playerId];
        const eq = ps.findEquipment(equipmentInstanceId);
        if (!eq) return { success: false, error: '装备不存在' };
        const triggerCost = toInt(eq.card_def.trigger_cost_e, -1);
        const triggerCostM = Math.max(0, toInt(eq.card_def.trigger_cost_m ?? eq.card_def.v2_resource?.trigger_cost_m, 0));
        if (triggerCost < 0 && !this.hasCardEvent(eq.card_def, 'equipment_trigger')) return { success: false, error: '该装备没有触发效果' };
        if (eq.turns_equipped < 1) return { success: false, error: '装备需要装备一回合后才能触发' };
        if (triggerCost > ps.elixir) return { success: false, error: '能量不足' };
        if (triggerCostM > ps.magic) return { success: false, error: '魔力不足' };
        const maxUses = this.equipmentTriggerMaxUses(eq);
        if (maxUses > 0 && toInt(eq.uses_this_turn, 0) >= maxUses) return { success: false, error: `该装备本回合最多触发${maxUses}次` };
        if (cardEventRequiresSelfDestroy(eq.card_def, 'equipment_trigger') && toInt(ps.equipment_protection, 0) > 0) {
            return { success: false, error: '装备保护会抵消摧毁，无法触发' };
        }
        if (triggerCost > 0) this.spendResource(playerId, 'elixir', triggerCost, eq.card_instance);
        if (triggerCostM > 0) this.spendResource(playerId, 'magic', triggerCostM, eq.card_instance);
        eq.uses_this_turn = toInt(eq.uses_this_turn, 0) + 1;
        const targetId = Number.isInteger(Number(targetPlayerId)) ? toInt(targetPlayerId, 1 - playerId) : 1 - playerId;
        if (this.hasCardEvent(eq.card_def, 'equipment_trigger')) {
            this.runCardEvent(playerId, eq.card_instance, 'equipment_trigger', {
                target_player: targetId,
                target_player_id: targetId,
                target_id: targetId,
            }, {
                event: 'equipment_trigger',
                source_id: playerId,
                target_id: targetId,
                selected_equipment_instance_id: eq.card_instance && eq.card_instance.instance_id,
                selected_equipment_owner_id: playerId,
            });
            this.dispatchCardEvent('equipment_triggered', playerId, eq.card_instance, targetId, eq, playerId);
        } else if (eq.def_id === 'Leaf') {
            if (this.destroyEquipment(playerId, eq)) this.dealAttackDamage(1 - playerId, 8, 1, false, playerId);
        } else if (eq.def_id === 'Mark') {
            if (this.destroyEquipment(playerId, eq) && !this.statusApplicationBlocked(1 - playerId, 'skip_turn')) {
                this.players[1 - playerId].skip_turn = true;
            }
        } else if (eq.def_id === 'Mine') {
            if (this.destroyEquipment(playerId, eq)) this.dealAttackDamage(1 - playerId, 20, 1, false, playerId);
        }
        if (!this.hasCardEvent(eq.card_def, 'equipment_trigger')) {
            this.dispatchCardEvent('equipment_triggered', playerId, eq.card_instance, targetId, eq, playerId);
        }
        this.checkGameOver();
        return { success: true };
    }

    endTurn(playerId) {
        if (this.current_player !== playerId) return { success: false, error: '不是你的回合' };
        if (this.pending_response) return { success: false, error: '等待对手反制响应' };
        this.endPlayerTurn(playerId);
        return { success: true };
    }

    endPlayerTurn(playerId) {
        const ps = this.players[playerId];
        this.runHandOwnerTurnEndEvents(playerId);
        if (this.game_over) return;
        this.runOwnerTurnEndEquipment(playerId);
        if (this.game_over) return;
        this.decayEquipmentArmorEndTurn(playerId);
        if (ps.bandage_death_pending && this.shouldExpireInvincibleOnTurnEnd(playerId)) {
            ps.health = 0;
            ps.bandage_death_pending = false;
            this.clearInvincibleState(playerId);
            this.logMsg(`${this.pn(playerId)}的绷带效果结束，死亡！`);
            this.checkGameOver();
            if (this.game_over) return;
        }
        if (ps.bandage_active && ps.invincible) {
            ps.bandage_active = false;
            ps.bandage_death_pending = true;
        }
        this.returnCogwheelCardsNow(playerId);
        [...ps.hand].forEach(card => {
            if (card.flags.has('void')) {
                ps.hand.splice(ps.hand.indexOf(card), 1);
                const alreadyExiled = ps.exile.includes(card);
                this.putCardInExile(playerId, card, false);
                this.logMsg(`${this.pn(playerId)}的${cardName(card.def_id)}因虚无被放逐`);
                if (!alreadyExiled && this.isVoidAntimatter(card)) {
                    this.effect_void_damage_all_except_self(playerId, card, { amount: 10 });
                }
            }
        });
        this.decayActionLimitStatus(playerId, 'attack_blocked', 'attack_blocked', '禁攻');
        this.decayActionLimitStatus(playerId, 'attack_only', 'attack_only', '仅攻击');
        if (ps.invincible && !ps.bandage_active && !ps.bandage_death_pending && this.shouldExpireInvincibleOnTurnEnd(playerId)) {
            this.clearInvincibleState(playerId);
            this.logMsg(`${this.pn(playerId)}的无敌效果结束`);
        }
        this.saveLastTurnDamageSnapshot(playerId);
        if (playerId === this.first_player) this.startPlayerTurn(1 - this.first_player);
        else this.endRound();
    }

    runOwnerTurnEndEquipment(playerId) {
        const ps = this.players[playerId];
        if (!ps) return;
        [...ps.equipment].forEach(eq => {
            if (!this.hasCardEvent(eq.card_def, 'owner_turn_end')) return;
            const targetId = Number.isInteger(Number(eq.effect_target)) ? toInt(eq.effect_target, playerId) : playerId;
            this.runCardEvent(playerId, eq.card_instance, 'owner_turn_end', null, {
                event: 'owner_turn_end',
                source_id: playerId,
                target_id: targetId,
                selected_equipment_instance_id: eq.card_instance && eq.card_instance.instance_id,
                selected_equipment_owner_id: playerId,
            });
        });
    }

    decayEquipmentArmorEndTurn(playerId) {
        const ps = this.players[playerId];
        if (!ps) return;
        [...ps.equipment].forEach(eq => {
            const armor = toInt(eq.armor, 0);
            if (armor > 0) eq.armor = Math.max(0, armor - 1);
        });
    }

    returnCogwheelCardsNow(playerId) {
        const ps = this.players[playerId];
        if (!ps.cogwheel_active) return;
        const excludeId = toInt(ps.cogwheel_exclude_instance_id, -1);
        let excludeDefId = '';
        [ps.hand || [], ps.discard || [], ps.exile || []].some(zone => {
            const found = zone.find(c => toInt(c && c.instance_id, -1) === excludeId);
            if (found) {
                excludeDefId = String(found.def_id || '');
                return true;
            }
            return false;
        });
        const returned = [];
        [...(ps.cards_played_this_turn_instance_ids || [])].forEach(instanceId => {
            const iid = toInt(instanceId, -1);
            if (iid === excludeId) return;
            let found = null;
            let zone = null;
            for (const cards of [ps.deck || [], ps.discard || []]) {
                const idx = cards.findIndex(c => c.instance_id === iid);
                if (idx >= 0) {
                    found = cards[idx];
                    zone = cards;
                    break;
                }
            }
            if (!found || !cardSelectableByAction(found) || !ps.canAddToHand()) return;
            if (['factory:cogwheel', 'Cogwheel'].includes(String(found.def_id || ''))) return;
            if (excludeDefId && String(found.def_id || '') === excludeDefId) return;
            zone.splice(zone.indexOf(found), 1);
            found.mimic_discount = 0;
            found.instance_flags.add('symbiosis');
            ps.addToHand(found);
            returned.push(found);
        });
        ps.cogwheel_active = false;
        ps.cogwheel_exclude_instance_id = -1;
        if (returned.length) this.logMsg(`${this.pn(playerId)}的齿轮效果：${returned.length}张牌回到手中并获得共生`);
    }

    endRound() {
        this.round_num += 1;
        if (!this.game_over) this.startDrawPhase();
    }

    setNextDraw(defIds) {
        const ps = this.players[this.current_player];
        const picked = [];
        (defIds || []).forEach(defId => {
            const idx = ps.deck.findIndex(card => card.def_id === defId);
            if (idx >= 0) picked.push(ps.deck.splice(idx, 1)[0]);
        });
        if (!picked.length) return { success: false, error: '设置失败：牌堆中没有这些牌' };
        [...picked].reverse().forEach(card => ps.deck.unshift(card));
        this.logMsg(`训练场：${this.pn(this.current_player)} 设置下次抽牌：${picked.map(card => cardName(card.def_id)).join('、')}`);
        return { success: true };
    }

    pickTutorialBotCard() {
        if (this.current_player !== 1 || this.phase !== 'action' || this.game_over) return null;
        const ps = this.players[1];
        if (Object.values(ps.cards_played_this_turn).reduce((a, b) => a + b, 0) >= 1) return null;
        const safe = new Set(['Basic', 'Bone', 'Stinger', 'Battery']);
        const order = ['thorn', 'root'];
        for (const type of order) {
            for (const card of ps.hand) {
                if (!safe.has(card.def_id) || card.card_type !== type) continue;
                if (card.card_type === 'root' && ps.equipment.length >= 4) continue;
                if (this.canPlayCard(1, card)[0]) return card;
            }
        }
        return null;
    }
}

function startLocalGame(message) {
    cardDefs = message.cardDefs || {};
    if (!cardDefs[ERROR_CARD_ID]) {
        cardDefs[ERROR_CARD_ID] = {
            id: ERROR_CARD_ID,
            name_en: 'Error',
            name_cn: '错误',
            cost_e: 0,
            cost_m: 0,
            card_type: 'bloom',
            flags: ['infinite_exclude'],
            effect_text: '这是一个错误，请联系服务器管理员',
            description: '哎呀，你怎么会看到这张牌？',
        };
    }
    openingEventMagicPool = message.openingEventMagicPool || [];
    const payload = message.payload || {};
    const tutorial = message.type === 'tutorial_start';
    const deck0 = tutorial ? TUTORIAL_DECKS[0] : (payload.deck0 || []);
    const deck1 = tutorial ? TUTORIAL_DECKS[1] : (payload.deck1 || []);
    if (!tutorial && (deck0.length !== DECK_SIZE || deck1.length !== DECK_SIZE)) {
        emit('server_error', { message: '训练场牌组必须各为15张' });
        return;
    }
    engine = new LocalSoloEngine(
        { ...payload, deck0, deck1 },
        {
            tutorial,
            playerNames: tutorial ? ['你', '练习对手'] : payload.playerNames,
            startLabel: tutorial ? '新手教程开始' : '单人训练场开始',
        },
    );
    emit('game_phase', { phase: 'playing', solo: true, tutorial });
    engine.sendState(tutorial ? 0 : null);
}

onmessage = event => {
    const message = event.data || {};
    try {
        if (message.type === 'solo_start' || message.type === 'tutorial_start') {
            startLocalGame(message);
            return;
        }
        if (!engine) {
            emit('server_error', { message: '训练场尚未开始' });
            return;
        }
        if (message.type === 'solo_pause') {
            engine = null;
            emit('solo_paused', {});
            return;
        }
        if (message.type === 'solo_play_card') {
            const pidx = engine.current_player;
            const payload = message.payload || {};
            const targetPlayerId = toInt(payload.target_player_id, -1);
            let choice = payload.choice;
            if (targetPlayerId >= 0) {
                choice = { ...(choice && typeof choice === 'object' ? choice : {}) };
                if (choice.target_player == null) choice.target_player = targetPlayerId;
                if (choice.target_player_id == null) choice.target_player_id = targetPlayerId;
                if (choice.target_id == null) choice.target_id = targetPlayerId;
            }
            const result = engine.playCard(pidx, payload.card_instance_id, choice);
            if (result.needs_response) {
                if (engine.tutorial && pidx === 0) {
                    engine.handleResponse(1, null);
                    engine.sendState(0);
                    return;
                }
                engine.sendState(engine.tutorial ? 0 : 1 - pidx);
                const responder = 1 - pidx;
                const counterCards = engine.getCounterCards(responder, new LocalCard(result.card));
                emit('response_request', {
                    card: result.card,
                    player_id: pidx,
                    target_player_id: responder,
                    counter_cards: counterCards.map(card => card.toDict()),
                    damage_prediction: engine.buildResponseDamagePrediction(responder, counterCards),
                });
                return;
            }
            if (result.needs_choice) {
                engine.sendState();
                emit('choice_request', {
                    choice_type: result.choice_type,
                    card: result.card,
                    choice_params: result.choice_params || {},
                    target_player_id: result.target_player_id,
                });
                return;
            }
            if (!result.success) {
                emit('server_error', { message: result.error || 'Operation failed' });
                return;
            }
            engine.sendState(engine.tutorial ? 0 : null);
            return;
        }
        if (message.type === 'solo_response') {
            const responder = engine.pending_response ? 1 - engine.pending_response.player_id : engine.current_player;
            const cardInstanceId = engine.tutorial && responder !== 0 ? null : (message.payload && message.payload.card_instance_id);
            engine.handleResponse(responder, cardInstanceId);
            engine.sendState(engine.tutorial ? 0 : null);
            return;
        }
        if (message.type === 'solo_resolve_choice') {
            const pidx = engine.pending_choice ? engine.pending_choice.player_id : engine.current_player;
            const result = engine.resolveChoice(pidx, message.payload && message.payload.choice);
            if (result.needs_response) {
                if (engine.tutorial && pidx === 0) {
                    engine.handleResponse(1, null);
                    engine.sendState(0);
                    return;
                }
                engine.sendState(engine.tutorial ? 0 : 1 - pidx);
                const responder = 1 - pidx;
                const counterCards = engine.getCounterCards(responder, new LocalCard(result.card));
                emit('response_request', {
                    card: result.card,
                    player_id: pidx,
                    target_player_id: engine.pending_response ? engine.pending_response.target_player_id : responder,
                    counter_cards: counterCards.map(card => card.toDict()),
                    damage_prediction: engine.buildResponseDamagePrediction(responder, counterCards),
                });
                return;
            }
            if (!result.success && result.error) emit('server_error', { message: result.error });
            engine.sendState(engine.tutorial ? 0 : null);
            return;
        }
        if (message.type === 'solo_use_trigger') {
            const payload = message.payload || {};
            const result = engine.useTrigger(engine.current_player, payload.equipment_instance_id, payload.target_player_id);
            if (!result.success) emit('server_error', { message: result.error || 'Operation failed' });
            engine.sendState(engine.tutorial ? 0 : null);
            return;
        }
        if (message.type === 'solo_end_turn') {
            const result = engine.endTurn(engine.current_player);
            if (!result.success) emit('server_error', { message: result.error || 'Operation failed' });
            engine.sendState(engine.tutorial ? 0 : null);
            return;
        }
        if (message.type === 'solo_set_next_draw') {
            const result = engine.setNextDraw((message.payload && message.payload.def_ids) || []);
            if (!result.success) emit('server_error', { message: result.error || 'Operation failed' });
            engine.sendState(engine.tutorial ? 0 : null);
            return;
        }
        if (message.type === 'tutorial_bot_action') {
            if (!engine.tutorial) return;
            if (engine.current_player !== 1 || engine.pending_response || engine.pending_choice || engine.game_over) {
                engine.sendState(0);
                return;
            }
            const card = engine.pickTutorialBotCard();
            if (card) {
                const result = engine.playCard(1, card.instance_id);
                if (result.needs_response) {
                    engine.sendState(0);
                    const counterCards = engine.getCounterCards(0, new LocalCard(result.card));
                    emit('response_request', {
                        card: result.card,
                        player_id: 1,
                        target_player_id: 0,
                        counter_cards: counterCards.map(c => c.toDict()),
                        damage_prediction: engine.buildResponseDamagePrediction(0, counterCards),
                    });
                    return;
                }
                if (result.needs_choice) engine.endTurn(1);
                engine.sendState(0);
            } else {
                engine.endTurn(1);
                engine.sendState(0);
            }
            return;
        }
        fallback(`local action not implemented: ${message.type}`);
    } catch (err) {
        fallback(err && err.stack ? err.stack : err);
    }
};
