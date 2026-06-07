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
const LATE_ROUND_FIRE_START = 20;
const CARD_FLAG_ALIASES = {
    'tag_troll_cards:exile': 'exile',
    'troll_cards:exile': 'exile',
    'tag_troll_cards_exile': 'exile',
    'troll_cards_exile': 'exile',
};

class ModLoopBreak extends Error {}
class ModLoopContinue extends Error {}

const TUTORIAL_DECKS = [
    [
        'Basic', 'Rose', 'Leaf', 'Coffee', 'Fission',
        'Triangle', 'Bubble', 'Fusion', 'Basic', 'Basic',
        'Bone', 'Battery', 'Stinger', 'Leaf', 'Bubble',
    ],
    [
        'Basic', 'Rose', 'Coffee', 'Battery', 'Rose',
        'Basic', 'Bone', 'Leaf', 'Bubble', 'Basic',
        'Stinger', 'Battery', 'Bubble', 'Triangle', 'Fire',
    ],
];

const EVENT_EFFECT_TYPES = new Set([
    'on_owner_turn_start',
    'on_enemy_turn_start',
    'on_any_turn_start',
    'on_damage_taken',
    'on_equipment_trigger',
    'on_equipment_destroy',
    'on_hand_owner_turn_start',
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
    enemy_turn_start: ['onEnemyTurnStart', 'enemy_turn_start', 'on_enemy_turn_start'],
    any_turn_start: ['onAnyTurnStart', 'any_turn_start', 'on_any_turn_start'],
    damage_taken: ['onDamageTaken', 'damage_taken', 'on_damage_taken'],
    equipment_trigger: ['onEquipmentTrigger', 'equipment_trigger', 'on_equipment_trigger'],
    equipment_destroy: ['onEquipmentDestroy', 'equipment_destroy', 'on_equipment_destroy', 'onDestroy'],
    hand_owner_turn_start: ['onHandOwnerTurnStart', 'hand_owner_turn_start', 'on_hand_owner_turn_start'],
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
    enemy_turn_start: ['on_enemy_turn_start'],
    any_turn_start: ['on_any_turn_start'],
    damage_taken: ['on_damage_taken'],
    equipment_trigger: ['on_equipment_trigger'],
    equipment_destroy: ['on_equipment_destroy', 'on_before_destroyed'],
    hand_owner_turn_start: ['on_hand_owner_turn_start'],
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
    return CARD_FLAG_ALIASES[text.toLowerCase()] || text;
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
        if (String(value.type || value.op || '') === 'destroy_self_equipment') return true;
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
        if (this.def_id === 'Tomato') {
            this.bonus_damage = Math.min(18, Math.max(0, this.bonus_damage));
            this.held_turns = Math.min(6, Math.max(0, this.held_turns));
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
        return Math.max(0, base - this.mimic_discount);
    }

    get cost_m() {
        return this.cost_m_override != null ? this.cost_m_override : toInt(this.def().cost_m, 0);
    }

    get flags() {
        const flags = new Set(normalizeCardFlags(this.def().flags || []));
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
            bonus_damage: this.def_id === 'Tomato' ? Math.min(18, Math.max(0, this.bonus_damage)) : this.bonus_damage,
            return_to_hand_turns: this.return_to_hand_turns,
            held_turns: this.def_id === 'Tomato' ? Math.min(6, Math.max(0, this.held_turns)) : this.held_turns,
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
        this.skip_turn = false;
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
        this.extra_hand_limit_bonus = 0;
        this.negate_next_skill = false;
        this.is_first_player = false;
        this.hand = [];
        this.deck = [];
        this.discard = [];
        this.exile = [];
        this.equipment = [];
        this.cards_played_this_turn = {};
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

    addToHand(card) {
        if (card && card.def_id === 'Tomato') {
            card.bonus_damage = 0;
            card.held_turns = 0;
        }
        this.hand.push(card);
        if (typeof this.onEnterHand === 'function') {
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
        this.health = Math.min(this.health + amount, this.base_max_health);
    }

    gainElixir(amount) {
        this.elixir = Math.min(this.elixir + amount, this.max_elixir);
    }

    gainMagic(amount) {
        this.magic = Math.min(this.magic + amount, this.max_magic);
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
        };
        if (includePrivate) {
            data.hand = this.hand.map(card => card.toDict());
            data.deck = this.deck.map(card => card.toDict());
            data.discard = this.discard.map(card => card.toDict());
            data.exile = this.exile.map(card => card.toDict());
            data.cards_played_this_turn = { ...this.cards_played_this_turn };
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
        this._antenna_reveal = [null, null];
        this._last_damage_value = [0, 0];
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
            const handSize = i === this.first_player ? FIRST_PLAYER_HAND_SIZE : INITIAL_HAND_SIZE;
            if (i === this.first_player && this.opening_event_picks[i] === 7) {
                this.players[i].elixir += 3;
            }
            this.players[i].drawCards(handSize);
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
                'coffee_first_use', 'invincible', 'skip_turn', 'damage_multiplier', 'bandage_active',
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
        clone._antenna_reveal = cloneJson(this._antenna_reveal) || [null, null];
        clone._last_damage_value = [...this._last_damage_value];
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
        if (!card || !this.hasCardEvent(card.def(), 'enter_hand')) return;
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
        ps.custom_vars = { '咖啡首次使用': 1, '三角形层数': 0, '魔法电池本回合回魔': 0 };
        deckEntries.forEach(entry => {
            const defId = typeof entry === 'string' ? entry : entry && entry.def_id;
            if (defId && cardDef(defId)) ps.deck.push(new LocalCard(entry));
        });
    }

    pn(playerId) {
        return this.player_names[playerId] || `玩家${playerId + 1}`;
    }

    logMsg(message) {
        let text = String(message || '').trim();
        if (!text) return;
        text = this.normalizeDamageLogText(text);
        if (this.mergeBubbleLog(text)) return;
        if (this.mergeChineseUseEquipment(text)) return;
        if (this.mergeChineseUseDestination(text)) return;
        if (this.mergeSimpleUseDetail(text)) return;
        if (this.mergeSimpleUseDamageLog(text)) return;
        if (this.mergeLegacyUseDamageLog(text)) return;
        if (this.mergeDamageTakenLog(text)) return;
        this.log.push(text);
    }

    normalizeDamageLogText(text) {
        const parsed = this.parseDamageTakenLog(text);
        if (!parsed) return text;
        return `${parsed.prefix}${parsed.target}受到${this.formatDamageParts(parsed.parts)}（H=${parsed.startHp}→${parsed.endHp}）`;
    }

    parseDamageTakenLog(text) {
        const raw = String(text || '');
        let match = raw.match(/^(.+)受到(\d+(?:\+\d+)*)点伤害（H=([^）]+)）$/);
        let before;
        let parts;
        let hpText;
        if (match) {
            before = match[1];
            parts = match[2].split('+').map(part => toInt(part, 0));
            hpText = match[3];
        } else {
            match = raw.match(/^(.+)受到(\d+)D(?:×(\d+))?（H=([^）]+)）$/);
            if (match) {
                before = match[1];
                parts = Array(Math.max(1, toInt(match[3] || 1, 1))).fill(toInt(match[2], 0));
                hpText = match[4];
            } else {
                match = raw.match(/^(.+)受到\((\d+(?:\+\d+)*)\)D（H=([^）]+)）$/);
                if (!match) return null;
                before = match[1];
                parts = match[2].split('+').map(part => toInt(part, 0));
                hpText = match[3];
            }
        }
        const cut = before.lastIndexOf('，');
        const prefix = cut >= 0 ? before.slice(0, cut + 1) : '';
        const target = cut >= 0 ? before.slice(cut + 1) : before;
        let startHp = '';
        let endHp = hpText;
        const arrow = hpText.indexOf('→');
        if (arrow >= 0) {
            startHp = hpText.slice(0, arrow);
            endHp = hpText.slice(arrow + 1);
        } else {
            const hp = Number.parseInt(hpText, 10);
            const total = parts.reduce((sum, part) => sum + toInt(part, 0), 0);
            if (Number.isFinite(hp)) startHp = String(hp + total);
        }
        return { prefix, target, parts, startHp, endHp };
    }

    formatDamageParts(parts) {
        const values = (parts || []).map(part => toInt(part, 0));
        if (!values.length) return '0D';
        if (values.length === 1) return `${values[0]}D`;
        if (values.every(value => value === values[0])) return `${values[0]}D×${values.length}`;
        return `(${values.join('+')})D`;
    }

    mergeDamageTakenLog(text) {
        if (!this.log.length) return false;
        const current = this.parseDamageTakenLog(text);
        const previous = this.parseDamageTakenLog(this.log[this.log.length - 1]);
        if (!current || !previous || current.target !== previous.target || !previous.startHp) {
            return false;
        }
        this.log[this.log.length - 1] = `${previous.prefix}${previous.target}受到${this.formatDamageParts([...previous.parts, ...current.parts])}（H=${previous.startHp}→${current.endHp}）`;
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
        return false;
    }

    mergeSimpleUseDamageLog(text) {
        if (!this.log.length || !this.parseDamageTakenLog(text)) return false;
        const match = String(this.log[this.log.length - 1]).match(/^(.+)使用了(.+)$/);
        if (!match) return false;
        this.log[this.log.length - 1] = `${match[1]}使用${match[2]}，${text}`;
        return true;
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
            if (!this.parseDamageTakenLog(text)) return false;
            detail = text;
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
        if (this._antenna_reveal[forPlayer]) {
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
            antenna_reveal: this._antenna_reveal[forPlayer],
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
            ps.gainMagic(5);
            (sub.conversions || []).slice(0, 3).forEach(conv => {
                const sourceDef = conv.source_def_id;
                const magicDef = conv.magic_def_id;
                const idx = ps.deck.findIndex(card => card.def_id === sourceDef);
                if (idx >= 0 && cardDef(magicDef)) {
                    ps.deck[idx] = new LocalCard(magicDef);
                    this.logMsg(`${this.pn(playerId)}【魔力转化】：${cardName(sourceDef)}变为${cardName(magicDef)}`);
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
                    ps.deck[idx] = light;
                    converted += 1;
                }
            });
            this.logMsg(`${this.pn(playerId)}【光之洗礼】：${converted}张牌变为Light(萌芽+共生)`);
        } else if (eventId === 4) {
            opp.fire += 2;
            this.logMsg(`${this.pn(playerId)}【烈焰预兆】：敌方+2灼烧`);
        } else if (eventId === 5) {
            this.logMsg(`${this.pn(playerId)}【命运抽签】：前二回合抽牌至手牌满`);
        } else if (eventId === 6) {
            this.logMsg(`${this.pn(playerId)}【能量涌动】：前三回合额外回复2E`);
        } else if (eventId === 7) {
            this.logMsg(`${this.pn(playerId)}【先手压制】：先手回复3E并抽4张牌`);
        } else if (eventId === 8) {
            ps.max_health -= 20;
            ps.base_max_health -= 20;
            ps.health -= 20;
            const targetDef = sub.yggdrasil_convert_def_id;
            let idx = targetDef ? ps.deck.findIndex(card => card.def_id === targetDef) : -1;
            if (idx < 0) idx = ps.deck.findIndex(card => card.def_id !== 'Yggdrasil');
            if (idx >= 0 && cardDef('Yggdrasil')) {
                const oldDef = ps.deck[idx].def_id;
                ps.deck[idx] = new LocalCard('Yggdrasil');
                this.logMsg(`${this.pn(playerId)}【绝境求生】：最大生命值-20，${cardName(oldDef)}变为Yggdrasil`);
            }
        }
    }

    startDrawPhase() {
        this.phase = 'draw';
        this.players.forEach(ps => {
            ps.cards_played_this_turn = {};
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
        if (ps.skip_turn) {
            ps.skip_turn = false;
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

    applyTurnStartEffects(playerId) {
        const ps = this.players[playerId];
        const oppId = 1 - playerId;
        const opp = this.players[oppId];
        this._antenna_reveal[playerId] = null;
        this.runZoneOwnerTurnStartEvents(playerId);
        this.runTimedEffectsForTurn(playerId);
        this.players.forEach(owner => {
            owner.equipment.forEach(eq => { eq.uses_this_turn = 0; });
        });
        if (ps.shovel_active) {
            ps.shovel_active = false;
            ps.untargetable = false;
            this.logMsg(`${this.pn(playerId)}的铲子效果结束`);
        }
        if (this.round_num > 1) {
            const drawCount = Math.max(0, DRAW_PER_TURN - ps.enemy_draw_reduction);
            ps.drawCards(drawCount);
            this.logMsg(`${this.pn(playerId)}抽${drawCount}张牌`);
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
        if (ps.poison > 0) {
            this.dealDirectDamage(playerId, ps.poison, '中毒');
            if (this.game_over || ps.health <= 0) return;
            ps.poison = Math.floor(ps.poison / 2);
        }
        if (ps.fire > 0) {
            this.dealDirectDamage(playerId, ps.fire, '灼烧');
            if (this.game_over || ps.health <= 0) return;
        }
        if (this.round_num > 1) {
            let recovery = ELIXIR_RECOVERY;
            [...opp.equipment].forEach(eq => {
                const aura = (eq.card_def.effects || []).find(e => e && e.type === 'aura_enemy_elixir_recovery');
                if (aura) recovery += this.evalInt(oppId, (aura.params || {}).amount, eq.card_instance, 0);
                else if (eq.def_id === 'Pincer') recovery -= 1;
            });
            recovery = Math.max(0, recovery - ps.enemy_e_reduction);
            ps.gainElixir(recovery);
            this.logMsg(`${this.pn(playerId)}回复${recovery}E`);
        }
        if (this.opening_event_picks[playerId] === 5 && this.round_num <= 2) {
            const drawNeeded = ps.handSpace();
            if (drawNeeded > 0) {
                ps.drawCards(drawNeeded);
                this.logMsg(`${this.pn(playerId)}抽${drawNeeded}张至手牌满`);
            }
        }
        if (this.opening_event_picks[playerId] === 6 && this.round_num <= 3) {
            ps.gainElixir(2);
            this.logMsg(`${this.pn(playerId)}额外+2E`);
        }
        [...ps.equipment].forEach(eq => {
            eq.turns_equipped += 1;
            if (this.hasCardEvent(eq.card_def, 'owner_turn_start')) {
                this.runCardEvent(playerId, eq.card_instance, 'owner_turn_start', null, {
                    event: 'owner_turn_start',
                    source_id: playerId,
                    target_id: playerId,
                });
            }
        });
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

    getChoiceRequest(card) {
        for (const effect of this.walkChoiceEffects(playEffectsFor(card))) {
            const type = effect.type || '';
            if (['request_target', 'request_card', 'request_confirm'].includes(type)) return effect;
            if (['discard_choice_then_draw', 'destroy_equipment_choice_or_first', 'choose_from_deck', 'choose_from_discard', 'steal_enemy_card'].includes(type)) {
                return effect;
            }
        }
        return null;
    }

    getChoiceType(card) {
        const effect = this.getChoiceRequest(card);
        const params = (effect && effect.params) || {};
        if (params.choice_type) return params.choice_type;
        if (!effect) return '';
        if (effect.type === 'request_target') return 'choose_target';
        if (effect.type === 'request_confirm') return 'confirm';
        if (effect.type === 'request_card') {
            const zone = params.zone || 'hand';
            if (zone === 'equipment') return 'choose_equipment';
            if (zone === 'deck') return 'choose_from_deck';
            if (zone === 'discard') return 'choose_from_discard';
            if (zone === 'exile') return 'choose_from_exile';
            return params.multi ? 'choose_cards_from_hand' : 'choose_card_from_hand';
        }
        if (effect.type === 'choose_from_deck') return 'choose_from_deck';
        if (effect.type === 'choose_from_discard') return 'choose_from_discard';
        if (effect.type === 'steal_enemy_card') return 'choose_from_enemy_hand';
        if (effect.type === 'destroy_equipment_choice_or_first') return 'choose_equipment';
        return '';
    }

    cardNeedsChoice(card) {
        return !!this.getChoiceRequest(card);
    }

    resolveTarget(playerId, target) {
        const context = this._active_effect_context || {};
        if (typeof target === 'number') return target;
        if (target && typeof target === 'object' && target.ref === 'card_owner') {
            const card = this.resolveCardRef(playerId, target.card, null);
            const loc = this.findCardLocation(card);
            return loc ? loc.ownerId : playerId;
        }
        if (!target || target === 'self' || target === 'friendly') return playerId;
        if (target === 'enemy') return 1 - playerId;
        if (target === 'both') return -1;
        if (target === 'random') return Math.random() < 0.5 ? playerId : 1 - playerId;
        if (['choice_target', 'selected_target', 'chosen_target'].includes(target)) {
            const choice = this._active_choice || {};
            return toInt(choice.target_player ?? choice.target_player_id ?? choice.target_id, playerId);
        }
        if (['event_source', 'source', 'last_actor', 'damage_source'].includes(target)) return toInt(context.source_id, playerId);
        if (['event_target', 'target'].includes(target)) return toInt(context.target_id, 1 - playerId);
        return playerId;
    }

    resolveTargets(playerId, target) {
        if (target === 'both' || target === 'all') return [0, 1];
        const tid = this.resolveTarget(playerId, target);
        return tid === -1 ? [0, 1] : [tid].filter(id => id >= 0 && id < this.players.length);
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

    removeCardFromCurrentZone(card) {
        const loc = this.findCardLocation(card);
        if (!loc) return null;
        const ps = this.players[loc.ownerId];
        if (loc.zone === 'equipment') ps.equipment.splice(loc.index, 1);
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
            '邪眼': ps.nazar_active ? ps.nazar_big_hits : 0,
            Nazar: ps.nazar_active ? ps.nazar_big_hits : 0,
        };
        return toInt(map[key], 0);
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
        const op = expr.op || expr.type || '';
        if (op === 'const') return expr.value ?? fallbackValue;
        if (op === 'var') {
            const store = this.varStoreForTarget(playerId, expr.target || 'self');
            return this.scalarValue(store[String(expr.name || 'var')], 0);
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
            if (prop === 'cost_e') return toInt(card.cost_e, 0);
            if (prop === 'cost_m') return toInt(card.cost_m, 0);
            if (prop === 'tag_count' || prop === 'tags_count') return card.flags.size;
            return toInt(card[prop], fallbackValue);
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
        if (op === 'add' || op === '+') return this.evalExpr(playerId, expr.a, currentCard, 0) + this.evalExpr(playerId, expr.b, currentCard, 0);
        if (op === 'sub' || op === '-') return this.evalExpr(playerId, expr.a, currentCard, 0) - this.evalExpr(playerId, expr.b, currentCard, 0);
        if (op === 'mul' || op === '*') return this.evalExpr(playerId, expr.a, currentCard, 0) * this.evalExpr(playerId, expr.b, currentCard, 0);
        if (op === 'div' || op === '/') {
            const b = this.evalExpr(playerId, expr.b, currentCard, 0);
            return b === 0 ? 0 : this.evalExpr(playerId, expr.a, currentCard, 0) / b;
        }
        if (op === 'floor') return Math.floor(this.evalExpr(playerId, expr.value ?? expr.a, currentCard, 0));
        if (op === 'ceil') return Math.ceil(this.evalExpr(playerId, expr.value ?? expr.a, currentCard, 0));
        if (op === 'min') return Math.min(this.evalExpr(playerId, expr.a, currentCard, 0), this.evalExpr(playerId, expr.b, currentCard, 0));
        if (op === 'max') return Math.max(this.evalExpr(playerId, expr.a, currentCard, 0), this.evalExpr(playerId, expr.b, currentCard, 0));
        if (op === 'last_damage') {
            const tid = this.resolveTarget(playerId, expr.target || 'enemy');
            return toInt(this._last_damage_value[tid], 0);
        }
        if (op === 'selected_cards_count') {
            const choice = this._active_choice || {};
            if (Array.isArray(choice.target_instance_ids)) return choice.target_instance_ids.length;
            return choice.target_instance_id != null || choice.target_def_id != null ? 1 : 0;
        }
        if (op === 'selected_card_index') return toInt((this._active_effect_context || {}).selected_card_index, 0);
        if (ref === 'var') {
            const store = this.varStoreForTarget(playerId, expr.target || 'self');
            return this.scalarValue(store[String(expr.name || 'var')], 0);
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
        return toInt(ps[prop], 0);
    }

    setPlayerPropertyValue(targetId, property, value) {
        const ps = this.players[targetId];
        if (!ps) return;
        let prop = String(property || 'health');
        if (prop === 'energy') prop = 'elixir';
        if (prop === 'max_energy') prop = 'max_elixir';
        const next = Math.max(0, toInt(value, 0));
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

    mimicSpecialCostForCard(target) {
        if (!target) return 0;
        const fusionExtra = Math.max(0, toInt(target.fusion_level, 1) - 1);
        const fissionExtra = Math.max(0, toInt(target.fission_level, 1) - 1);
        const tomatoLayer = target.def_id === 'Tomato' ? Math.min(6, Math.max(0, toInt(target.held_turns, 0))) : 0;
        return Math.ceil((fusionExtra + fissionExtra + tomatoLayer) / 2);
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
            event_card_type: eventCard ? eventCard.card_type : '',
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
            if (eventName === 'equipment_trigger' && cardEventRequiresSelfDestroy(def, eventName)) {
                const eq = this.findEquipmentForCard(ownerId, card);
                if (eq && !this.destroyEquipment(ownerId, eq)) return true;
            }
            this.runEffectList(ownerId, card, effects, choice, { event: eventName, ...extraContext });
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
        const hits = Math.max(1, this.evalInt(playerId, params.hits ?? 1, card, 1));
        this._incoming_damage_hint[targetId] = amount;
        const dealt = this.dealAttackDamage(targetId, amount, hits, !!params.is_precision, playerId);
        this._last_damage_value[targetId] = dealt;
        if (log) this.logMsg(log);
    }

    effect_direct_damage(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
        const amount = this.evalInt(playerId, params.amount ?? 1, card, 1);
        const sourceText = String(params.source_text || params.source_name || params.label || params.source || (card ? cardName(card.def_id) : '\u6548\u679c'));
        this.dealDirectDamage(targetId, amount, sourceText, playerId);
    }

    effect_lifesteal_damage(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
        const amount = this.modifiedAttackDamage(this.evalInt(playerId, params.amount ?? 8, card, 8), card);
        const dealt = this.dealAttackDamage(targetId, amount, 1, !!params.is_precision, playerId);
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
        this.players[targetId].drawCards(amount);
        this.logMsg(`${this.pn(targetId)}抽${amount}张牌`);
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
        const amount = this.evalInt(playerId, params.amount ?? 1, card, 1);
        this.players[targetId].poison += amount;
        this.logMsg(`${this.pn(targetId)}+${amount}层中毒`);
    }

    effect_apply_burn(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
        const amount = this.evalInt(playerId, params.amount ?? 1, card, 1);
        this.players[targetId].fire += amount;
        this.logMsg(`${this.pn(targetId)}+${amount}层灼烧`);
    }

    effect_apply_toxic(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
        const amount = this.evalInt(playerId, params.amount ?? 1, card, 1);
        this.players[targetId].toxic += amount;
        this.logMsg(`${this.pn(targetId)}+${amount}层淬毒`);
    }

    effect_apply_vulnerable(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
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
        }
        return next;
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
        target[prop] = this.clampCardProperty(target, prop, current + this.evalInt(playerId, params.amount ?? params.value ?? 0, card, 0));
        if (prop === 'fusion_level') target.fusion_multiplier = target.fusion_level;
        if (prop === 'fission_level') target.fission_count = Math.max(0, target.fission_level - 1);
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
        if (eq) eq[String(params.property || 'turns_equipped')] = this.evalInt(playerId, params.value ?? 0, card, 0);
    }

    effect_equipment_prop_add(playerId, card, params) {
        const eq = this.resolveEquipmentRef(playerId, params.equipment || { ref: 'current_equipment' }, card);
        if (eq) {
            const prop = String(params.property || 'turns_equipped');
            eq[prop] = toInt(eq[prop], 0) + this.evalInt(playerId, params.amount ?? params.value ?? 0, card, 0);
        }
    }

    effect_copy_card(playerId, card, params, log) {
        const target = this.resolveCardRef(playerId, params.card || { ref: 'selected_card' }, card);
        if (!target) return;
        if (!this.players[playerId].canAddToHand()) return;
        if (card && card.def_id === 'Mimic' && !this.payMimicSpecialCost(playerId, target, card)) return;
        const copy = target.copy();
        copy.instance_id = randintId();
        this.players[playerId].addToHand(copy);
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
        target.addToHand(newCard);
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
        this.discardCard(target, newCard);
        this._last_created_card_instance_id = newCard.instance_id;
        this._active_effect_context.last_created_card_instance_id = newCard.instance_id;
        if (log && newCard.def_id !== ERROR_CARD_ID) this.logMsg(log);
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
        if (!target || !targetPlayer || !targetPlayer.canAddToHand()) return;
        const loc = this.removeCardFromCurrentZone(target);
        if (loc) targetPlayer.addToHand(target);
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
        if (loc) this.players[loc.ownerId].exile.push(target);
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
        this.resolveTargets(playerId, params.target || 'enemy').forEach(tid => {
            [...this.players[tid].equipment].forEach(eq => {
                if (!eq.card_instance.flags.has('indestructible') && this.destroyEquipment(tid, eq)) {
                    this.logDestroyedEquipment(playerId, tid, eq, log);
                }
            });
        });
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
        this.players[targetId].skip_turn = true;
    }

    effect_reveal_enemy_hand(playerId, card, params, log) {
        const targetId = this.resolveTarget(playerId, params.target || 'enemy');
        this._antenna_reveal[playerId] = this.players[targetId].hand.map(c => c.toDict());
        this.logMsg(log || `${this.pn(playerId)}查看了${this.pn(targetId)}的手牌`);
    }

    effect_choose_from_discard(playerId, card, params, log, choice) {
        const targetDef = choice && choice.target_def_id;
        if (!targetDef) return;
        const ps = this.players[playerId];
        const idx = ps.discard.findIndex(c => c.def_id === targetDef);
        if (idx >= 0 && ps.canAddToHand()) {
            const found = ps.discard.splice(idx, 1)[0];
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
        if (status === 'poison') this.players[targetId].poison = 0;
        else if (status === 'fire') this.players[targetId].fire = 0;
        else if (status) this.players[targetId][status] = 0;
    }

    effect_status_add_named(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const status = String(params.status || params.name || '');
        const amount = this.evalInt(playerId, params.amount ?? 1, card, 1);
        if (status) this.players[targetId][status] = toInt(this.players[targetId][status], 0) + amount;
    }

    effect_status_set_named(playerId, card, params) {
        const targetId = this.resolveTarget(playerId, params.target || 'self');
        const status = String(params.status || params.name || '');
        const amount = this.evalInt(playerId, params.amount ?? params.value ?? 0, card, 0);
        if (status) this.players[targetId][status] = amount;
    }

    effect_add_status(playerId, card, params, log, choice) {
        this.effect_status_add_named(playerId, card, { ...params, status: params.status || params.id || params.name }, log, choice);
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
        this.players[targetId].invincible = this.evalInt(playerId, params.value ?? params.amount ?? 1, card, 1) > 0;
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
    effect_request_target() {}
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
        return 0;
    }

    modifiedAttackDamage(base, card) {
        let bonus = Math.max(0, toInt(card && card.bonus_damage, 0));
        if (card && card.def_id === 'Tomato') bonus = Math.min(18, bonus);
        let amount = toInt(base, 0) + bonus;
        const fusion = Math.max(1, toInt(card && card.fusion_level, 1));
        const fission = Math.max(1, toInt(card && card.fission_level, 1));
        return Math.ceil((amount * fusion) / fission);
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
        this.players.forEach(ps => {
            if (ps.health > 0) {
                ps.fire += 1;
                applied += 1;
            }
        });
        if (applied > 0) this.logMsg(`第${this.round_num}回合开始，所有存活玩家+1灼烧`);
    }

    dealDirectDamage(playerId, amount, source = '', sourceId = null) {
        const ps = this.players[playerId];
        if (!ps || ps.invincible) {
            if (ps) this.logMsg(`${this.pn(playerId)}无敌，免疫${source}伤害`);
            return 0;
        }
        let actual = this.applyCorruptionMultiplier(amount);
        ps.health -= actual;
        this.recordDamage(playerId, actual, sourceId);
        this.logMsg(`${this.pn(playerId)}受到${actual}点${source}伤害（H=${ps.health}）`);
        this.checkYggdrasil(playerId);
        this.checkGameOver();
        return actual;
    }

    dealAttackDamage(targetId, amount, hits = 1, isPrecision = false, attackerId = 1 - targetId) {
        const ps = this.players[targetId];
        if (!ps || ps.untargetable) {
            if (ps) this.logMsg(`${this.pn(targetId)}无法被攻击选中`);
            return 0;
        }
        let total = 0;
        for (let h = 0; h < hits; h++) {
            let precisionDodged = false;
            if (ps.dodge > 0) {
                ps.dodge -= 1;
                if (!isPrecision) {
                    this.logMsg(`${this.pn(targetId)}闪避了攻击`);
                    continue;
                }
                precisionDodged = true;
                this.logMsg(`${this.pn(targetId)}的闪避被精准消耗`);
            }
            if (ps.invincible) {
                this.logMsg(`${this.pn(targetId)}无敌，免疫伤害`);
                continue;
            }
            let dmg = Math.max(0, toInt(amount, 0));
            if (this.halve_next_attack) dmg = Math.ceil(dmg / 2);
            else if (precisionDodged) dmg = Math.ceil(dmg / 2);
            dmg = this.applyCorruptionMultiplier(dmg);
            if (ps.nazar_active) {
                const original = dmg;
                dmg = Math.max(1, dmg - 9);
                if (original >= 10) {
                    ps.nazar_big_hits += 1;
                    if (ps.nazar_big_hits >= 2) {
                        ps.nazar_active = false;
                        ps.nazar_big_hits = 0;
                    }
                }
            }
            dmg = Math.max(0, dmg - ps.armor);
            if (ps.sponge_active && dmg > 0) {
                ps.poison += Math.floor(dmg / 2);
                dmg = 0;
            }
            ps.health -= dmg;
            total += dmg;
            this.recordDamage(targetId, dmg, attackerId);
            this.logMsg(`${this.pn(targetId)}受到${dmg}点伤害（H=${ps.health}）`);
            if (dmg > 0 && ps.toxic > 0) ps.poison += ps.toxic;
            this._game_over_defer_depth += 1;
            try {
                this.checkYggdrasil(targetId);
                if (dmg > 0) {
                    [...ps.equipment].forEach(eq => {
                        if (this.hasCardEvent(eq.card_def, 'damage_taken')) {
                            this.runCardEvent(targetId, eq.card_instance, 'damage_taken', null, {
                                event: 'damage_taken',
                                source_id: attackerId,
                                target_id: targetId,
                                damage: dmg,
                            });
                        } else if (eq.def_id === 'Battery') {
                            this.dealDirectDamage(attackerId, 3, '电池', targetId);
                            this.logMsg(`${this.pn(targetId)}的电池效果：对${this.pn(attackerId)}造成3D`);
                        } else if (eq.def_id === 'MagicBattery' && ps.magic_battery_m_this_turn < 3) {
                            ps.gainMagic(1);
                            ps.magic_battery_m_this_turn += 1;
                            ps.custom_vars['魔法电池本回合回魔'] = ps.magic_battery_m_this_turn;
                            this.logMsg(`${this.pn(targetId)}的魔法电池效果：+1M`);
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

    checkYggdrasil(playerId) {
        const ps = this.players[playerId];
        if (!ps || ps.health > 0) return;
        if (ps.bandage_active) {
            ps.health = 1;
            ps.invincible = true;
            ps.bandage_active = false;
            ps.bandage_death_pending = true;
            this.logMsg(`${this.pn(playerId)}的绷带发动！无敌直到下个友方回合结束，然后死亡`);
            return;
        }
        const idx = ps.hand.findIndex(card => card.def_id === 'Yggdrasil');
        if (idx >= 0) {
            const card = ps.hand.splice(idx, 1)[0];
            ps.exile.push(card);
            ps.health = 5;
            ps.invincible = true;
            ['poison', 'fire', 'vulnerable', 'toxic', 'triangle_stacks', 'dodge', 'armor', 'equipment_protection'].forEach(prop => { ps[prop] = 0; });
            ps.nazar_active = false;
            ps.nazar_big_hits = 0;
            ps.negate_next_skill = false;
            ps.skip_turn = false;
            ps.damage_multiplier = 1.0;
            ps.custom_vars['三角形层数'] = 0;
            this.logMsg(`${this.pn(playerId)}的世界树之叶发动！清除己方所有效果，生命值设为5，本回合无敌！`);
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
        if (card.def_id === 'Tomato') {
            card.bonus_damage = 0;
            card.held_turns = 0;
        }
    }

    discardCard(ps, card) {
        if (card.card_type === 'thorn') this.resetOneShotAttackAttrs(card);
        card.mimic_discount = 0;
        ps.discard.push(card);
    }

    destroyEquipment(ownerId, eq) {
        const ps = this.players[ownerId];
        if (!eq || !ps.equipment.includes(eq)) return false;
        if (ps.equipment_protection > 0) {
            ps.equipment_protection -= 1;
            this.logMsg(`${this.pn(ownerId)}的装备保护抵消了摧毁！`);
            return false;
        }
        if (this.hasCardEvent(eq.card_def, 'equipment_destroy')) {
            this.runCardEvent(ownerId, eq.card_instance, 'equipment_destroy', null, {
                event: 'equipment_destroy',
                source_id: ownerId,
                target_id: ownerId,
            });
        }
        if (eq.def_id === 'Disc') {
            const effectTarget = toInt(eq.effect_target ?? eq.owner ?? ownerId, ownerId);
            const targetState = this.players[effectTarget] || ps;
            targetState.armor = Math.max(0, targetState.armor - 2);
        }
        ps.equipment.splice(ps.equipment.indexOf(eq), 1);
        if (eq.card_instance.flags.has('exile')) ps.exile.push(eq.card_instance);
        else this.discardCard(ps, eq.card_instance);
        this.dispatchCardEvent('equipment_destroyed', ownerId, eq.card_instance, ownerId, eq, ownerId);
        return true;
    }

    getExtraEForCard(playerId, card) {
        if (card.flags.has('symbiosis')) return 0;
        return toInt(this.players[playerId].cards_played_this_turn[card.def_id], 0);
    }

    canPlayCard(playerId, card) {
        const ps = this.players[playerId];
        const def = card.def();
        if (def.card_type === 'guard' && !hasScriptEntry(def, 'play') && !(def.effects || []).length) {
            return [false, '反制牌只能通过响应机制使用'];
        }
        if (this.phase !== 'action' || this.current_player !== playerId) return [false, '不是你的回合'];
        if (ps.attack_blocked > 0 && def.card_type === 'thorn') return [false, '本回合无法使用攻击牌'];
        if (ps.attack_only > 0 && def.card_type !== 'thorn') return [false, '本回合只能使用攻击牌'];
        if (ps.shovel_active) return [false, '链子效果中，无法使用卡牌'];
        const totalE = card.cost_e + this.getExtraEForCard(playerId, card);
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
        if (opp.hand.some(c => c.def().response_trigger === 'any')) return true;
        if (opp.hand.some(c => c.def().response_trigger === trigger)) return true;
        if (this.wouldDestroyEquipment(card) && opp.hand.some(c => c.def().response_trigger === 'equipment_destroy')) return true;
        if (this.wouldHeal(card) && opp.hand.some(c => c.def().response_trigger === 'heal')) return true;
        return false;
    }

    checkPrecisionResponseNeeded(playerId, card) {
        if (!card.flags.has('precision')) return false;
        return this.players[1 - playerId].hand.some(c => c.def().response_trigger === 'thorn');
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
        const [canPlay, reason] = this.canPlayCard(playerId, card);
        if (!canPlay) return { success: false, error: reason };
        const totalE = card.cost_e + this.getExtraEForCard(playerId, card);
        this.spendResource(playerId, 'elixir', totalE, card);
        this.spendResource(playerId, 'magic', card.cost_m, card);
        ps.cards_played_this_turn[card.def_id] = toInt(ps.cards_played_this_turn[card.def_id], 0) + 1;
        const removed = ps.removeHandCard(instanceId);
        if (!removed) return { success: false, error: '移出手牌失败' };
        if (this.checkResponseNeeded(playerId, card) || this.checkPrecisionResponseNeeded(playerId, card)) {
            this.pending_response = {
                card: card.toDict(),
                player_id: playerId,
                original_choice: choice,
                is_precision: card.flags.has('precision'),
            };
            return { success: true, needs_response: true, card: card.toDict() };
        }
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
            if (card.flags.has('exile')) ps.exile.push(card);
            else this.discardCard(ps, card);
            this.dispatchCardEvent('card_used', playerId, card, playerId, null, null, choice);
            return result;
        }
        this.negated_card = false;
        if (this.cardNeedsChoice(card) && choice == null) {
            const choiceRequest = this.getChoiceRequest(card);
            const choiceParams = (choiceRequest && choiceRequest.params) || {};
            const choiceType = this.getChoiceType(card);
            const targetId = choiceRequest && choiceRequest.type === 'request_card'
                ? this.resolveTarget(playerId, choiceParams.target || 'self')
                : null;
            this.pending_choice = {
                card: card.toDict(),
                player_id: playerId,
                choice_type: choiceType,
                choice_params: choiceParams,
            };
            if (targetId != null) this.pending_choice.target_player_id = targetId;
            ps.hand.unshift(card);
            ps.elixir += card.cost_e + Math.max(0, toInt(ps.cards_played_this_turn[card.def_id], 1) - 1);
            ps.magic += card.cost_m;
            ps.cards_played_this_turn[card.def_id] = Math.max(0, toInt(ps.cards_played_this_turn[card.def_id], 1) - 1);
            return {
                success: true,
                needs_choice: true,
                choice_type: choiceType,
                choice_params: choiceParams,
                target_player_id: targetId,
                card: card.toDict(),
            };
        }
        if (card.def_id === 'Mimic' && choice && choice.target_instance_id != null) {
            const target = ps.findHandCard(choice.target_instance_id);
            if (target && !this.canPayMimicSpecialCost(playerId, target)) {
                ps.hand.unshift(card);
                ps.elixir += card.cost_e + Math.max(0, toInt(ps.cards_played_this_turn[card.def_id], 1) - 1);
                ps.magic += card.cost_m;
                ps.cards_played_this_turn[card.def_id] = Math.max(0, toInt(ps.cards_played_this_turn[card.def_id], 1) - 1);
                return { success: false, error: '能量不足' };
            }
        }
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
        const equipOwnerId = card._placed_as_equipment_owner != null ? card._placed_as_equipment_owner : playerId;
        const scriptControlsPlay = getScriptEffects(card.def(), 'play').length > 0;
        if ((card.card_type === 'root' && !scriptControlsPlay) || card._placed_as_equipment) {
            if (!this.findEquipmentForCard(equipOwnerId, card)) {
                const eq = new LocalEquipment(card, equipOwnerId);
                this.players[equipOwnerId].equipment.push(eq);
                this.logMsg(`${this.pn(equipOwnerId)}装备了${cardName(card.def_id)}`);
            }
        } else if (card.flags.has('exile')) {
            const loc = this.findCardLocation(card);
            if (!loc) ps.exile.push(card);
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
        const effects = playEffectsFor(card);
        if (effects.length) {
            this.runEffectList(playerId, card, effects, choice, {
                event: 'play',
                source_id: playerId,
                target_id: this.resolveTarget(playerId, choice && choice.target_player_id != null ? choice.target_player_id : 'enemy'),
            });
            return;
        }
        this.logMsg(`${this.pn(playerId)}使用了${cardName(card.def_id)}`);
    }

    executeCardEffectHalfDamage(playerId, card, choice = null) {
        this.halve_next_attack = true;
        this.logMsg(`${this.pn(playerId)}的精准牌被闪避反制，伤害减半！`);
        const result = this.executeCardEffect(playerId, card, choice);
        this.halve_next_attack = false;
        return result;
    }

    resolveChoice(playerId, choice) {
        if (!this.pending_choice) return { success: false, error: '没有待选择操作' };
        const pending = this.pending_choice;
        this.pending_choice = null;
        const card = new LocalCard(pending.card);
        const ps = this.players[playerId];
        if (choice == null) {
            if (!ps.findHandCard(card.instance_id)) ps.hand.unshift(card);
            return { success: false, error: '选择已取消' };
        }
        const dupCount = toInt(ps.cards_played_this_turn[card.def_id], 0);
        this.spendResource(playerId, 'elixir', card.cost_e + dupCount, card);
        this.spendResource(playerId, 'magic', card.cost_m, card);
        ps.cards_played_this_turn[card.def_id] = dupCount + 1;
        const handCard = ps.findHandCard(card.instance_id);
        if (handCard) ps.removeHandCard(card.instance_id);
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
            if (!counter || counter.cost_e > responder.elixir || counter.cost_m > responder.magic) {
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
            this.spendResource(responderId, 'elixir', counter.cost_e, counter);
            this.spendResource(responderId, 'magic', counter.cost_m, counter);
            const removed = responder.removeHandCard(instanceId);
            this.logMsg(`${this.pn(responderId)}使用${cardName(removed.def_id)}进行反制！`);
            const dodgeBeforeCounter = toInt(responder.dodge, 0);
            this.executeCounterEffect(responderId, removed, card, playerId);
            if (removed.def_id === 'Bubble') {
                const result = pending.is_precision
                    ? this.executeCardEffectHalfDamage(playerId, card, choice)
                    : this.executeCardEffect(playerId, card, choice);
                responder.dodge = Math.min(toInt(responder.dodge, 0), dodgeBeforeCounter);
                return result;
            }
            if (removed.def_id === 'MagicBubble') this.negated_card = true;
            return this.executeCardEffect(playerId, card, choice);
        }
        return this.executeCardEffect(playerId, card, choice);
    }

    executeCounterEffect(responderId, counterCard, originalCard, originalPlayerId) {
        const effects = getScriptEffects(counterCard.def(), 'response');
        if (effects.length) {
            this.runEffectList(responderId, counterCard, effects, null, {
                event: 'response',
                source_id: responderId,
                target_id: originalPlayerId,
            });
        } else if (counterCard.def_id === 'Bubble') {
            this.players[responderId].dodge += 1;
        } else if (counterCard.def_id === 'Nazar') {
            this.players[responderId].nazar_active = true;
            this.players[responderId].nazar_big_hits = 0;
        } else if (counterCard.def_id === 'MagicNazar') {
            this.players[responderId].equipment_protection += 1;
        } else if (counterCard.def_id === 'MagicBubble') {
            this.players[responderId].negate_next_skill = true;
        }
        if (counterCard.flags.has('exile')) this.players[responderId].exile.push(counterCard);
        else this.discardCard(this.players[responderId], counterCard);
        this.dispatchCardEvent('card_used', responderId, counterCard, originalPlayerId == null ? responderId : originalPlayerId);
    }

    useTrigger(playerId, equipmentInstanceId) {
        if (this.current_player !== playerId) return { success: false, error: '不是你的回合' };
        const ps = this.players[playerId];
        const eq = ps.findEquipment(equipmentInstanceId);
        if (!eq) return { success: false, error: '装备不存在' };
        const triggerCost = toInt(eq.card_def.trigger_cost_e, -1);
        if (triggerCost < 0 && !this.hasCardEvent(eq.card_def, 'equipment_trigger')) return { success: false, error: '该装备没有触发效果' };
        if (eq.turns_equipped < 1) return { success: false, error: '装备需要装备一回合后才能触发' };
        if (triggerCost > ps.elixir) return { success: false, error: '能量不足' };
        const maxUses = this.equipmentTriggerMaxUses(eq);
        if (maxUses > 0 && toInt(eq.uses_this_turn, 0) >= maxUses) return { success: false, error: `该装备本回合最多触发${maxUses}次` };
        if (cardEventRequiresSelfDestroy(eq.card_def, 'equipment_trigger') && toInt(ps.equipment_protection, 0) > 0) {
            return { success: false, error: '装备保护会抵消摧毁，无法触发' };
        }
        if (triggerCost > 0) this.spendResource(playerId, 'elixir', triggerCost, eq.card_instance);
        eq.uses_this_turn = toInt(eq.uses_this_turn, 0) + 1;
        if (this.hasCardEvent(eq.card_def, 'equipment_trigger')) {
            this.runCardEvent(playerId, eq.card_instance, 'equipment_trigger', null, {
                event: 'equipment_trigger',
                source_id: playerId,
                target_id: 1 - playerId,
            });
            this.dispatchCardEvent('equipment_triggered', playerId, eq.card_instance, 1 - playerId, eq, playerId);
        } else if (eq.def_id === 'Leaf') {
            if (this.destroyEquipment(playerId, eq)) this.dealAttackDamage(1 - playerId, 8, 1, false, playerId);
        } else if (eq.def_id === 'Mark') {
            if (this.destroyEquipment(playerId, eq)) this.players[1 - playerId].skip_turn = true;
        } else if (eq.def_id === 'Mine') {
            if (this.destroyEquipment(playerId, eq)) this.dealAttackDamage(1 - playerId, 20, 1, false, playerId);
        }
        if (!this.hasCardEvent(eq.card_def, 'equipment_trigger')) {
            this.dispatchCardEvent('equipment_triggered', playerId, eq.card_instance, 1 - playerId, eq, playerId);
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
        if (ps.bandage_death_pending) {
            ps.health = 0;
            ps.bandage_death_pending = false;
            ps.invincible = false;
            this.logMsg(`${this.pn(playerId)}的绷带效果结束，死亡！`);
            this.checkGameOver();
            if (this.game_over) return;
        }
        if (ps.bandage_active && ps.invincible) {
            ps.bandage_active = false;
            ps.bandage_death_pending = true;
        }
        [...ps.hand].forEach(card => {
            if (card.flags.has('void')) {
                ps.hand.splice(ps.hand.indexOf(card), 1);
                ps.exile.push(card);
                this.logMsg(`${this.pn(playerId)}的${cardName(card.def_id)}因虚无被放逐`);
            }
        });
        if (ps.attack_blocked > 0) ps.attack_blocked -= 1;
        if (ps.attack_only > 0) ps.attack_only -= 1;
        this.saveLastTurnDamageSnapshot(playerId);
        if (playerId === this.first_player) this.startPlayerTurn(1 - this.first_player);
        else this.endRound();
    }

    endRound() {
        this.players.forEach((ps, pid) => {
            if (ps.invincible && !ps.bandage_active && !ps.bandage_death_pending) {
                ps.invincible = false;
                this.logMsg(`${this.pn(pid)}的无敌效果结束`);
            }
        });
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
        const safe = new Set(['Basic', 'Bone', 'Fire', 'Rose', 'Coffee', 'Battery']);
        const order = ['thorn', 'bloom', 'root'];
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
            const result = engine.playCard(pidx, message.payload && message.payload.card_instance_id, message.payload && message.payload.choice);
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
            if (!result.success && result.error) emit('server_error', { message: result.error });
            engine.sendState(engine.tutorial ? 0 : null);
            return;
        }
        if (message.type === 'solo_use_trigger') {
            const result = engine.useTrigger(engine.current_player, message.payload && message.payload.equipment_instance_id);
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
