import random
import math
import json
import base64
import re
import copy
from typing import Any, List, Dict, Optional, Tuple, Set
from cards import (
    CardDef, CardInstance, CARD_DEFS, DRAFT_RATIO, DRAFT_REROLLS,
    HAND_LIMIT, DRAW_PER_TURN, ELIXIR_RECOVERY, BASE_MAX_HEALTH,
    BASE_MAX_ELIXIR, BASE_MAX_MAGIC, INITIAL_HEALTH, INITIAL_ELIXIR,
    INITIAL_MAGIC, FIRST_PLAYER_ELIXIR, SECOND_PLAYER_HEALTH,
    DECK_SIZE, INITIAL_HAND_SIZE, FIRST_PLAYER_HAND_SIZE, build_draft_pool, generate_draft_options,
    create_deck_from_draft, ERROR_CARD_ID, normalize_card_flag, normalize_card_flags,
    clamp_card_layer, clamp_card_extra_hits, clamp_damage_hits, _new_instance_id,
)
from runtime_errors import MOD_RUNTIME_ERROR_MESSAGE, record_mod_runtime_error
from mod_runtime_v2 import run_v2_event, run_v2_steps, validate_v2_ui_response
from damage_types import (
    DAMAGE_TAG_BATTERY, DAMAGE_TAG_DIRECT, DAMAGE_TAG_FIRE, DAMAGE_TAG_PHYSICAL, DAMAGE_TAG_POISON,
    DAMAGE_TYPE_MAGIC, DAMAGE_TYPE_PHYSICAL, damage_type_tag, infer_damage_type,
    status_damage_tag,
)

CORRUPTION_DAMAGE_MULTIPLIER = 1.5
LATE_ROUND_FIRE_START = 10


class ModLoopBreak(Exception):
    pass


class ModLoopContinue(Exception):
    pass


class EquipmentInstance:
    def __init__(self, card_instance: CardInstance, owner: int):
        self.card_instance = card_instance
        self.owner = owner
        self.effect_target: int = owner
        self.turns_equipped: int = 0
        self.uses_this_turn: int = 0
        self.corruption_active: bool = False
        self.armor: int = 0
        self.custom_vars: Dict[str, int] = {}

    @property
    def def_id(self) -> str:
        return self.card_instance.def_id

    @property
    def card_def(self) -> CardDef:
        return self.card_instance.card_def

    def to_dict(self) -> dict:
        return {
            'card_instance': self.card_instance.to_dict(),
            'owner': self.owner,
            'effect_target': self.effect_target,
            'turns_equipped': self.turns_equipped,
            'uses_this_turn': self.uses_this_turn,
            'corruption_active': self.corruption_active,
            'armor': self.armor,
            'custom_vars': dict(self.custom_vars),
        }

    @staticmethod
    def from_dict(d: dict) -> 'EquipmentInstance':
        ei = EquipmentInstance(
            CardInstance.from_dict(d['card_instance']),
            d['owner']
        )
        ei.turns_equipped = d.get('turns_equipped', 0)
        ei.uses_this_turn = d.get('uses_this_turn', 0)
        ei.effect_target = d.get('effect_target', ei.owner)
        ei.corruption_active = d.get('corruption_active', False)
        ei.armor = max(0, int(d.get('armor', 0) or 0))
        ei.custom_vars = dict(d.get('custom_vars', {}) or {})
        return ei


def reset_card_after_play(card: CardInstance):
    preserve_fission = 'preserve_fission' in normalize_card_flags(getattr(card, 'instance_flags', set()) or set()) or 'preserve_fission' in normalize_card_flags(getattr(card.card_def, 'flags', set()) or set())
    preserved_fission_level = clamp_card_layer(getattr(card, 'fission_level', 1)) if preserve_fission else 1
    card.cost_e_override = None
    card.cost_m_override = None
    card.mimic_discount = 0
    card.power_value = 0
    card.temp_swift_value = 0
    card.temp_heavy_value = 0
    card.temp_magic_heavy_value = 0
    card.hand_blind_turns = 0
    card.instance_flags.discard('power')
    card.instance_flags.discard('temp_swift')
    card.instance_flags.discard('temp_heavy')
    card.instance_flags.discard('temp_magic_heavy')
    card.instance_flags.discard('ocean_spikeball_boosted')
    card.instance_flags.discard('wide_strike')
    if card.card_type == 'thorn':
        card.fission_level = preserved_fission_level if preserve_fission else 1
        card.fusion_level = 1
        card.fission_count = max(0, card.fission_level - 1)
        card.fusion_multiplier = 1.0
        card.fission_hit = 0
        if card.def_id == 'Tomato':
            card.bonus_damage = 0
            card.held_turns = 0
    if getattr(card, '_mimic_copy', False):
        try:
            delattr(card, '_mimic_copy')
        except Exception:
            pass


def reset_card_for_discard(card: CardInstance):
    return


def fresh_card_copy_from_dict(data: dict, fallback_def_id: str = '') -> CardInstance:
    """Recreate a card snapshot as a new physical card instance."""
    if isinstance(data, dict):
        snapshot = dict(data)
        snapshot['instance_id'] = _new_instance_id()
        return CardInstance.from_dict(snapshot)
    return CardInstance(fallback_def_id or ERROR_CARD_ID)


class PlayerState:
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.health: int = INITIAL_HEALTH
        self.max_health: int = BASE_MAX_HEALTH
        self.base_max_health: int = BASE_MAX_HEALTH
        self.elixir: int = INITIAL_ELIXIR
        self.max_elixir: int = BASE_MAX_ELIXIR
        self.magic: int = INITIAL_MAGIC
        self.max_magic: int = BASE_MAX_MAGIC
        self.armor: int = 0
        self.poison: int = 0
        self.fire: int = 0
        self.toxic: int = 0
        self.triangle_stacks: int = 0
        self.dodge: int = 0
        self.nazar_active: bool = False
        self.nazar_big_hits: int = 0
        self.equipment_protection: int = 0
        self.magic_battery_m_this_turn: int = 0
        self.coffee_first_use: bool = True
        self.invincible: bool = False
        self.invincible_until_player: Optional[int] = None
        self.invincible_granted_round: int = -1
        self.invincible_granted_turn_marker: int = -1
        self.skip_turn: int = 0
        self.forced_skip_turn: int = 0
        self.damage_multiplier: float = 1.0
        self.bandage_active: bool = False
        self.bandage_death_pending: bool = False
        self.attack_blocked: int = 0
        self.untargetable: int = 0
        self.sponge_active: bool = False
        self.shovel_active: bool = False
        self.sluggish: int = 0
        self.enemy_draw_reduction: int = 0
        self.enemy_e_reduction: int = 0
        self.overload: int = 0
        self.foresight: int = 0
        self.fracture: int = 0
        self.stagnation: int = 0
        self.blind: int = 0
        self.heal_block: int = 0
        self.weakness: int = 0
        self.bleed: int = 0
        self.fragment_stacks: int = 0
        self.m_gained_this_turn: bool = False
        self.m_gained_last_turn: bool = False
        self.cogwheel_pending_return: list = []
        self.attack_only: int = 0
        self.honey_control_turns: int = 0
        self.hand: List[CardInstance] = []
        self.deck: List[CardInstance] = []
        self.discard: List[CardInstance] = []
        self.exile: List[CardInstance] = []
        self.equipment: List[EquipmentInstance] = []
        self.extra_hand_limit_bonus: int = 0
        self.external_zero_e_ignore_hand_limit: bool = False
        self.cards_played_this_turn: Dict[str, int] = {}
        self.cards_played_this_turn_instance_ids: List[int] = []
        self.turn_damage_taken: int = 0
        self.turn_damage_dealt: int = 0
        self.last_turn_damage_taken: int = 0
        self.last_turn_damage_dealt: int = 0
        self.total_damage_taken: int = 0
        self.total_damage_dealt: int = 0
        self.achievement_min_health: int = self.health
        self.achievement_invincible_triggered: bool = False
        self.achievement_played_thorn: bool = False
        self.achievement_yggdrasil_revived: bool = False
        self.achievement_total_healed: int = 0
        self.achievement_max_single_damage_dealt: int = 0
        self.achievement_max_cards_played_turn: int = 0
        self.achievement_turn_elixir_gained: int = 0
        self.achievement_max_turn_elixir_gained: int = 0
        self.achievement_same_instance_play_counts: Dict[int, int] = {}
        self.achievement_max_same_instance_plays: int = 0
        self.achievement_last_played_def_id: str = ''
        self.achievement_last_played_def_count: int = 0
        self.achievement_max_same_name_streak: int = 0
        self.achievement_max_enemy_poison: int = 0
        self.achievement_max_enemy_fire: int = 0
        self.achievement_max_enemy_poison_fire_min: int = 0
        self.achievement_max_enemy_status_types: int = 0
        self.achievement_attack_blocked_received: int = 0
        self.achievement_last_attack_blocked_value: int = int(self.attack_blocked)
        self.achievement_max_enemy_attack_blocked: int = 0
        self.achievement_untargetable_received: int = 0
        self.achievement_last_untargetable_value: int = int(self.untargetable)
        self.achievement_max_untargetable: int = int(self.untargetable)
        self.achievement_team_double_resources: bool = False
        self.achievement_min_enemy_card_total: int = 999999
        self.achievement_counter_successes: int = 0
        self.achievement_equipment_destroyed: int = 0
        self.achievement_max_equipment_count: int = 0
        self.achievement_max_armor: int = self.armor
        self.achievement_total_card_plays: int = 0
        self.achievement_death_round = None
        self.achievement_self_caused_death: bool = False
        self.turn_start_snapshot: Dict[str, int] = {
            'health': self.health,
            'elixir': self.elixir,
            'magic': self.magic,
        }
        self.match_start_snapshot: Dict[str, int] = {
            'health': self.health,
            'elixir': self.elixir,
            'magic': self.magic,
        }
        self.custom_vars: Dict[str, int] = {
            '\u5496\u5561\u9996\u6b21\u4f7f\u7528': 1,
            '\u4e09\u89d2\u5f62\u5c42\u6570': 0,
            '\u9b54\u6cd5\u7535\u6c60\u672c\u56de\u5408\u56de\u9b54': 0,
        }
        self.custom_statuses: Dict[str, int] = {}
        self.negate_next_skill: bool = False
        self.is_first_player: bool = False
        self._enter_hand_callback = None
        self._draw_callback = None

    def to_dict(self, include_private: bool = True) -> dict:
        d = {
            'player_id': self.player_id,
            'health': self.health,
            'max_health': self.max_health,
            'base_max_health': self.base_max_health,
            'elixir': self.elixir,
            'max_elixir': self.max_elixir,
            'magic': self.magic,
            'max_magic': self.max_magic,
            'armor': self.armor,
            'poison': self.poison,
            'fire': self.fire,
            'toxic': self.toxic,
            'triangle_stacks': self.triangle_stacks,
            'dodge': self.dodge,
            'nazar_active': self.nazar_active,
            'nazar_big_hits': self.nazar_big_hits,
            'equipment_protection': self.equipment_protection,
            'invincible': self.invincible,
            'invincible_until_player': self.invincible_until_player,
            'invincible_granted_round': self.invincible_granted_round,
            'invincible_granted_turn_marker': self.invincible_granted_turn_marker,
            'skip_turn': self.skip_turn,
            'forced_skip_turn': self.forced_skip_turn,
            'damage_multiplier': self.damage_multiplier,
            'bandage_active': self.bandage_active,
            'bandage_death_pending': self.bandage_death_pending,
            'attack_blocked': self.attack_blocked,
            'untargetable': self.untargetable,
            'sponge_active': self.sponge_active,
            'shovel_active': self.shovel_active,
            'sluggish': self.sluggish,
            'enemy_draw_reduction': self.enemy_draw_reduction,
            'enemy_e_reduction': self.enemy_e_reduction,
            'overload': self.overload,
            'foresight': self.foresight,
            'fracture': self.fracture,
            'stagnation': self.stagnation,
            'blind': self.blind,
            'heal_block': self.heal_block,
            'weakness': self.weakness,
            'bleed': self.bleed,
            'fragment_stacks': self.fragment_stacks,
            'm_gained_last_turn': self.m_gained_last_turn,
            'attack_only': self.attack_only,
            'honey_control_turns': self.honey_control_turns,
            'extra_hand_limit_bonus': self.extra_hand_limit_bonus,
            'negate_next_skill': self.negate_next_skill,
            'is_first_player': self.is_first_player,
            'coffee_first_use': self.coffee_first_use,
            'equipment': [e.to_dict() for e in self.equipment],
            'deck_count': len(self.deck),
            'discard_count': len(self.discard),
            'exile_count': len(self.exile),
            'hand_count': len(self.hand),
            'hand_limit': self.hand_limit(),
            'turn_damage_taken': self.turn_damage_taken,
            'turn_damage_dealt': self.turn_damage_dealt,
            'last_turn_damage_taken': self.last_turn_damage_taken,
            'last_turn_damage_dealt': self.last_turn_damage_dealt,
            'total_damage_taken': self.total_damage_taken,
            'total_damage_dealt': self.total_damage_dealt,
            'achievement_min_health': self.achievement_min_health,
            'achievement_invincible_triggered': self.achievement_invincible_triggered,
            'achievement_played_thorn': self.achievement_played_thorn,
            'achievement_yggdrasil_revived': self.achievement_yggdrasil_revived,
            'achievement_total_healed': self.achievement_total_healed,
            'achievement_max_single_damage_dealt': self.achievement_max_single_damage_dealt,
            'achievement_max_cards_played_turn': self.achievement_max_cards_played_turn,
            'achievement_turn_elixir_gained': self.achievement_turn_elixir_gained,
            'achievement_max_turn_elixir_gained': self.achievement_max_turn_elixir_gained,
            'achievement_same_instance_play_counts': dict(self.achievement_same_instance_play_counts),
            'achievement_max_same_instance_plays': self.achievement_max_same_instance_plays,
            'achievement_last_played_def_id': self.achievement_last_played_def_id,
            'achievement_last_played_def_count': self.achievement_last_played_def_count,
            'achievement_max_same_name_streak': self.achievement_max_same_name_streak,
            'achievement_max_enemy_poison': self.achievement_max_enemy_poison,
            'achievement_max_enemy_fire': self.achievement_max_enemy_fire,
            'achievement_max_enemy_poison_fire_min': self.achievement_max_enemy_poison_fire_min,
            'achievement_max_enemy_status_types': self.achievement_max_enemy_status_types,
            'achievement_attack_blocked_received': self.achievement_attack_blocked_received,
            'achievement_last_attack_blocked_value': self.achievement_last_attack_blocked_value,
            'achievement_max_enemy_attack_blocked': self.achievement_max_enemy_attack_blocked,
            'achievement_untargetable_received': self.achievement_untargetable_received,
            'achievement_last_untargetable_value': self.achievement_last_untargetable_value,
            'achievement_max_untargetable': self.achievement_max_untargetable,
            'achievement_team_double_resources': self.achievement_team_double_resources,
            'achievement_min_enemy_card_total': self.achievement_min_enemy_card_total,
            'achievement_counter_successes': self.achievement_counter_successes,
            'achievement_equipment_destroyed': self.achievement_equipment_destroyed,
            'achievement_max_equipment_count': self.achievement_max_equipment_count,
            'achievement_max_armor': self.achievement_max_armor,
            'achievement_total_card_plays': self.achievement_total_card_plays,
            'achievement_death_round': self.achievement_death_round,
            'achievement_self_caused_death': self.achievement_self_caused_death,
            'turn_start_snapshot': dict(self.turn_start_snapshot),
            'match_start_snapshot': dict(self.match_start_snapshot),
            'custom_statuses': dict(self.custom_statuses),
        }
        if include_private:
            d['hand'] = [c.to_dict() for c in self.hand]
            d['deck'] = [c.to_dict() for c in self.deck]
            d['discard'] = [c.to_dict() for c in self.discard]
            d['exile'] = [c.to_dict() for c in self.exile]
            d['cards_played_this_turn'] = dict(self.cards_played_this_turn)
            d['cards_played_this_turn_instance_ids'] = list(self.cards_played_this_turn_instance_ids)
            d['custom_vars'] = dict(self.custom_vars)
        return d

    @staticmethod
    def from_dict(d: dict) -> 'PlayerState':
        ps = PlayerState(d['player_id'])
        ps.health = d['health']
        ps.max_health = d['max_health']
        ps.base_max_health = d['base_max_health']
        ps.elixir = d['elixir']
        ps.max_elixir = d['max_elixir']
        ps.magic = d['magic']
        ps.max_magic = d['max_magic']
        ps.armor = d['armor']
        ps.poison = d['poison']
        ps.fire = d['fire']
        ps.toxic = d.get('toxic', 0)
        ps.triangle_stacks = d.get('triangle_stacks', 0)
        ps.dodge = d.get('dodge', 0)
        ps.nazar_active = d.get('nazar_active', False)
        ps.nazar_big_hits = d.get('nazar_big_hits', 0)
        ps.equipment_protection = d.get('equipment_protection', 0)
        ps.invincible = d.get('invincible', False)
        ps.invincible_until_player = d.get('invincible_until_player', None)
        ps.invincible_granted_round = int(d.get('invincible_granted_round', -1) if d.get('invincible_granted_round', -1) is not None else -1)
        ps.invincible_granted_turn_marker = int(d.get('invincible_granted_turn_marker', -1) if d.get('invincible_granted_turn_marker', -1) is not None else -1)
        ps.skip_turn = int(d.get('skip_turn', 0))
        ps.forced_skip_turn = int(d.get('forced_skip_turn', 0))
        ps.damage_multiplier = d.get('damage_multiplier', 1.0)
        ps.bandage_active = d.get('bandage_active', False)
        ps.bandage_death_pending = d.get('bandage_death_pending', False)
        ps.attack_blocked = d.get('attack_blocked', 0)
        raw_untargetable = d.get('untargetable', 0)
        if isinstance(raw_untargetable, bool):
            ps.untargetable = 1 if raw_untargetable else 0
        else:
            try:
                ps.untargetable = max(0, int(raw_untargetable or 0))
            except (TypeError, ValueError):
                ps.untargetable = 0
        ps.sponge_active = d.get('sponge_active', False)
        ps.shovel_active = d.get('shovel_active', False)
        ps.sluggish = d.get('sluggish', 0)
        ps.enemy_draw_reduction = int(d.get('enemy_draw_reduction', 0) or 0)
        ps.enemy_e_reduction = int(d.get('enemy_e_reduction', 0) or 0)
        ps.overload = d.get('overload', 0)
        ps.foresight = d.get('foresight', 0)
        ps.fracture = d.get('fracture', 0)
        ps.stagnation = d.get('stagnation', 0)
        ps.blind = d.get('blind', 0)
        ps.heal_block = d.get('heal_block', 0)
        ps.weakness = d.get('weakness', 0)
        ps.bleed = d.get('bleed', 0)
        ps.fragment_stacks = d.get('fragment_stacks', 0)
        ps.m_gained_last_turn = d.get('m_gained_last_turn', False)
        ps.attack_only = d.get('attack_only', 0)
        ps.honey_control_turns = int(d.get('honey_control_turns', 0) or 0)
        ps.extra_hand_limit_bonus = d.get('extra_hand_limit_bonus', 0)
        ps.negate_next_skill = d.get('negate_next_skill', False)
        ps.is_first_player = d.get('is_first_player', False)
        ps.coffee_first_use = d.get('coffee_first_use', True)
        if 'hand' in d:
            ps.hand = [CardInstance.from_dict(c) for c in d['hand']]
        if 'deck' in d:
            ps.deck = [CardInstance.from_dict(c) for c in d['deck']]
        if 'discard' in d:
            ps.discard = [CardInstance.from_dict(c) for c in d['discard']]
        if 'exile' in d:
            ps.exile = [CardInstance.from_dict(c) for c in d['exile']]
        if 'equipment' in d:
            ps.equipment = [EquipmentInstance.from_dict(e) for e in d['equipment']]
        if 'cards_played_this_turn' in d:
            ps.cards_played_this_turn = d['cards_played_this_turn']
        if 'cards_played_this_turn_instance_ids' in d:
            ps.cards_played_this_turn_instance_ids = list(d.get('cards_played_this_turn_instance_ids') or [])
        ps.turn_damage_taken = int(d.get('turn_damage_taken', 0))
        ps.turn_damage_dealt = int(d.get('turn_damage_dealt', 0))
        ps.last_turn_damage_taken = int(d.get('last_turn_damage_taken', 0))
        ps.last_turn_damage_dealt = int(d.get('last_turn_damage_dealt', 0))
        ps.total_damage_taken = int(d.get('total_damage_taken', 0))
        ps.total_damage_dealt = int(d.get('total_damage_dealt', 0))
        ps.achievement_min_health = int(d.get('achievement_min_health', ps.health))
        ps.achievement_invincible_triggered = bool(d.get('achievement_invincible_triggered', False))
        ps.achievement_played_thorn = bool(d.get('achievement_played_thorn', False))
        ps.achievement_yggdrasil_revived = bool(d.get('achievement_yggdrasil_revived', False))
        ps.achievement_total_healed = int(d.get('achievement_total_healed', 0) or 0)
        ps.achievement_max_single_damage_dealt = int(d.get('achievement_max_single_damage_dealt', 0) or 0)
        ps.achievement_max_cards_played_turn = int(d.get('achievement_max_cards_played_turn', 0) or 0)
        ps.achievement_turn_elixir_gained = int(d.get('achievement_turn_elixir_gained', 0) or 0)
        ps.achievement_max_turn_elixir_gained = int(d.get('achievement_max_turn_elixir_gained', 0) or 0)
        ps.achievement_same_instance_play_counts = {
            int(k): int(v)
            for k, v in (d.get('achievement_same_instance_play_counts') or {}).items()
            if str(k).lstrip('-').isdigit()
        }
        ps.achievement_max_same_instance_plays = int(d.get('achievement_max_same_instance_plays', 0) or 0)
        ps.achievement_last_played_def_id = str(d.get('achievement_last_played_def_id', '') or '')
        ps.achievement_last_played_def_count = int(d.get('achievement_last_played_def_count', 0) or 0)
        ps.achievement_max_same_name_streak = int(d.get('achievement_max_same_name_streak', 0) or 0)
        ps.achievement_max_enemy_poison = int(d.get('achievement_max_enemy_poison', 0) or 0)
        ps.achievement_max_enemy_fire = int(d.get('achievement_max_enemy_fire', 0) or 0)
        ps.achievement_max_enemy_poison_fire_min = int(d.get('achievement_max_enemy_poison_fire_min', 0) or 0)
        ps.achievement_max_enemy_status_types = int(d.get('achievement_max_enemy_status_types', 0) or 0)
        ps.achievement_attack_blocked_received = int(d.get('achievement_attack_blocked_received', 0) or 0)
        ps.achievement_last_attack_blocked_value = int(d.get('achievement_last_attack_blocked_value', getattr(ps, 'attack_blocked', 0)) or 0)
        ps.achievement_max_enemy_attack_blocked = int(d.get('achievement_max_enemy_attack_blocked', 0) or 0)
        ps.achievement_untargetable_received = int(d.get('achievement_untargetable_received', 0) or 0)
        ps.achievement_last_untargetable_value = int(d.get('achievement_last_untargetable_value', getattr(ps, 'untargetable', 0)) or 0)
        ps.achievement_max_untargetable = int(d.get('achievement_max_untargetable', getattr(ps, 'untargetable', 0)) or 0)
        ps.achievement_team_double_resources = bool(d.get('achievement_team_double_resources', False))
        ps.achievement_min_enemy_card_total = int(d.get('achievement_min_enemy_card_total', 999999) or 999999)
        ps.achievement_counter_successes = int(d.get('achievement_counter_successes', 0) or 0)
        ps.achievement_equipment_destroyed = int(d.get('achievement_equipment_destroyed', 0) or 0)
        ps.achievement_max_equipment_count = int(d.get('achievement_max_equipment_count', 0) or 0)
        ps.achievement_max_armor = int(d.get('achievement_max_armor', getattr(ps, 'armor', 0)) or 0)
        ps.achievement_total_card_plays = int(d.get('achievement_total_card_plays', 0) or 0)
        death_round = d.get('achievement_death_round', None)
        ps.achievement_death_round = None if death_round is None else int(death_round)
        ps.achievement_self_caused_death = bool(d.get('achievement_self_caused_death', False))
        ps.turn_start_snapshot = dict(d.get('turn_start_snapshot') or {
            'health': ps.health,
            'elixir': ps.elixir,
            'magic': ps.magic,
        })
        ps.match_start_snapshot = dict(d.get('match_start_snapshot') or {
            'health': ps.health,
            'elixir': ps.elixir,
            'magic': ps.magic,
        })
        if 'custom_vars' in d:
            ps.custom_vars = d.get('custom_vars', {})
        if 'custom_statuses' in d:
            ps.custom_statuses = d.get('custom_statuses', {})
        ps.custom_vars.setdefault('\u5496\u5561\u9996\u6b21\u4f7f\u7528', 1 if ps.coffee_first_use else 0)
        ps.custom_vars.setdefault('\u4e09\u89d2\u5f62\u5c42\u6570', int(ps.triangle_stacks))
        ps.custom_vars.setdefault('\u9b54\u6cd5\u7535\u6c60\u672c\u56de\u5408\u56de\u9b54', int(ps.magic_battery_m_this_turn))
        return ps

    def find_hand_card(self, instance_id: int) -> Optional[CardInstance]:
        for c in self.hand:
            if c.instance_id == instance_id:
                return c
        return None

    def remove_hand_card(self, instance_id: int) -> Optional[CardInstance]:
        for i, c in enumerate(self.hand):
            if c.instance_id == instance_id:
                return self.hand.pop(i)
        return None

    def find_equipment(self, instance_id: int) -> Optional[EquipmentInstance]:
        for e in self.equipment:
            if e.card_instance.instance_id == instance_id:
                return e
        return None

    def remove_equipment(self, instance_id: int) -> Optional[EquipmentInstance]:
        for i, e in enumerate(self.equipment):
            if e.card_instance.instance_id == instance_id:
                return self.equipment.pop(i)
        return None

    def hand_limit(self) -> int:
        own_golden_leaf = sum(
            1
            for e in self.equipment
            if e.def_id == 'GoldenLeaf' and getattr(e, 'effect_target', self.player_id) == self.player_id
        )
        air_penalty = sum(
            1
            for c in getattr(self, 'hand', []) or []
            if getattr(c, 'def_id', '') in ('void:air', 'Air')
        )
        return max(0, HAND_LIMIT + own_golden_leaf + max(0, int(getattr(self, 'extra_hand_limit_bonus', 0))) - air_penalty)

    def zero_e_cards_ignore_hand_limit(self) -> bool:
        return bool(getattr(self, 'external_zero_e_ignore_hand_limit', False)) or any(
            e.def_id in ('MagicGoldenLeaf', 'vanilla:magicgoldenleaf')
            and getattr(e, 'effect_target', self.player_id) == self.player_id
            for e in self.equipment
        )

    def rule_hand_size(self) -> int:
        ignore_zero_e = self.zero_e_cards_ignore_hand_limit()
        total = 0
        for c in self.hand:
            if c.def_id == ERROR_CARD_ID:
                continue
            if ignore_zero_e and int(getattr(c, 'cost_e', 0) or 0) == 0:
                continue
            total += 1
        return total

    def can_add_to_hand(self) -> bool:
        return self.rule_hand_size() < self.hand_limit()

    def hand_space(self) -> int:
        return max(0, self.hand_limit() - self.rule_hand_size())

    def add_to_hand(self, card: CardInstance, trigger_enter_hand: bool = True):
        self.hand.append(card)
        callback = getattr(self, '_enter_hand_callback', None)
        if trigger_enter_hand and callback:
            callback(self.player_id, card)
        while self.rule_hand_size() > self.hand_limit() and self.hand:
            attract_new = 'attract' in getattr(card, 'flags', set())
            non_attract = [c for c in self.hand if c is not card and 'attract' not in getattr(c, 'flags', set())]
            if attract_new and non_attract:
                overflow_card = non_attract[0]
            else:
                overflow_card = card if card in self.hand else self.hand[0]
            if overflow_card in self.hand:
                self.hand.remove(overflow_card)
                reset_card_for_discard(overflow_card)
                self.discard.append(overflow_card)
            else:
                break

    def draw_cards(self, count: int) -> List[CardInstance]:
        drawn = []
        sprout_queue = []
        for _ in range(count):
            if not self.deck:
                if not self.discard:
                    break
                self.deck = self.discard[:]
                self.discard = []
                random.shuffle(self.deck)
            card = self.deck.pop(0)
            if card.def_id == ERROR_CARD_ID:
                self.add_to_hand(card)
                drawn.append(card)
                continue
            if not self.can_add_to_hand():
                attract_cards = [c for c in self.hand if 'attract' in c.flags]
                non_attract_cards = [c for c in self.hand if 'attract' not in c.flags]
                if 'attract' in card.flags and non_attract_cards:
                    discard_card = non_attract_cards[0]
                    self.hand.remove(discard_card)
                    reset_card_for_discard(discard_card)
                    self.discard.append(discard_card)
                    self.add_to_hand(card)
                    drawn.append(card)
                else:
                    reset_card_for_discard(card)
                    self.discard.append(card)
            else:
                self.add_to_hand(card)
                drawn.append(card)
            if 'sprout' in card.flags and card in self.hand:
                sprout_queue.append(card)
        while sprout_queue:
            trigger = sprout_queue.pop(0)
            if not self.deck:
                if not self.discard:
                    break
                self.deck = self.discard[:]
                self.discard = []
                random.shuffle(self.deck)
            if self.deck:
                extra = self.deck.pop(0)
                if extra.def_id == ERROR_CARD_ID:
                    self.add_to_hand(extra)
                    drawn.append(extra)
                    continue
                if self.can_add_to_hand():
                    self.add_to_hand(extra)
                    drawn.append(extra)
                    if 'sprout' in extra.flags:
                        sprout_queue.append(extra)
                else:
                    reset_card_for_discard(extra)
                    self.discard.append(extra)
        # Electric Web callback: damage per card drawn
        draw_cb = getattr(self, '_draw_callback', None)
        if draw_cb and drawn:
            for c in drawn:
                draw_cb(self.player_id, c)
        return drawn

    def heal(self, amount: int):
        before = self.health
        if amount > 0 and self.heal_block > 0:
            if not self._is_status_immune_internal():
                reduction = min(1.0, 0.5 * self.heal_block)
                amount = max(0, int(amount * (1.0 - reduction)))
            self.heal_block = max(0, self.heal_block - 1)
        self.health = min(self.health + amount, self.base_max_health)
        try:
            self.achievement_total_healed += max(0, int(self.health) - int(before))
        except Exception:
            pass

    def _is_status_immune_internal(self) -> bool:
        custom = getattr(self, 'custom_statuses', {}) or {}
        return any(int(custom.get(key, 0) or 0) > 0 for key in ('status_immune', 'immune', '状态免疫'))

    def gain_elixir(self, amount: int):
        before = self.elixir
        self.elixir = min(self.elixir + amount, self.max_elixir)
        try:
            gained = max(0, int(self.elixir) - int(before))
            self.achievement_turn_elixir_gained += gained
            self.achievement_max_turn_elixir_gained = max(
                int(getattr(self, 'achievement_max_turn_elixir_gained', 0) or 0),
                int(getattr(self, 'achievement_turn_elixir_gained', 0) or 0),
            )
        except Exception:
            pass

    def gain_magic(self, amount: int):
        self.magic = min(self.magic + amount, self.max_magic)
        if amount > 0:
            self.m_gained_this_turn = True


class GameEngine:
    OPENING_EVENTS = {
        1: {'id': 1, 'name': '生命强化', 'desc': '最大生命值+20', 'position': 1},
        2: {'id': 2, 'name': '魔力转化', 'desc': '将最多3张牌转化为[[card:ManaOrb|flag=sprout|flag=symbiosis]]', 'position': 2},
        3: {'id': 3, 'name': '光之洗礼', 'desc': '将最多五张牌转化为Light：[[card:Light|flag=sprout|flag=symbiosis]]', 'position': 2},
        8: {'id': 8, 'name': '绝境求生', 'desc': '最大生命值-20，将一张牌变化为世界树之叶', 'position': 2},
        4: {'id': 4, 'name': '烈焰预兆', 'desc': '开局对所有敌方玩家施加3层灼烧', 'position': 3},
        5: {'id': 5, 'name': '命运抽签', 'desc': '少抽1张牌，然后从总抽牌库选择1张牌洗入牌库', 'position': 3},
        6: {'id': 6, 'name': '能量涌动', 'desc': '每回合多回复1[[icon:E]]', 'position': 3},
        7: {'id': 7, 'name': '先手压制', 'desc': '必定先手，先手回复7E并抽5张牌', 'position': 3},
        9: {'id': 9, 'name': '多重瓣', 'desc': '多子瓣牌子瓣+1，将5张[[card:Dust|flag=exile]]随机洗入抽牌堆', 'position': 1},
        10: {'id': 10, 'name': '魔力加速', 'desc': '最大生命值-10，打出一张不消耗M的牌回复1M', 'position': 1},
    }
    OPENING_EVENT_ORDER = {
        1: 10, 2: 20, 3: 30, 8: 40,
        9: 45, 10: 48, 4: 50, 5: 60, 6: 70, 7: 80,
    }
    OPENING_EVENT_COLORS = {
        1: '#3FA66B',
        2: '#5B5FC7',
        3: '#D7B84F',
        4: '#D96B3A',
        5: '#8B6FD8',
        6: '#3A8F68',
        7: '#C45151',
        8: '#5A8FCF',
        9: '#B86AA2',
        10: '#4E8FCF',
    }
    MAGIC_CARD_POOL = ['MagicBone', 'MagicStinger', 'MagicSewage', 'MagicNazar', 'MagicBubble']

    _EFFECT_ALIASES = {
        'damage': 'deal_damage',
        'damage_multi': 'deal_damage_multi',
        'poison': 'apply_poison',
        'burn': 'apply_burn',
        'toxic': 'apply_toxic',
        'add_armor': 'gain_armor',
        'remove_armor': 'remove_armor',
        'set_armor': 'set_armor',
        'dodge_this': 'dodge_this',
        'dodge_permanent': 'gain_dodge',
        'clear_buffs': 'clear_buffs',
        'clear_debuffs': 'clear_debuffs',
        'clear_all_effects': 'clear_all_effects',
        'clear_status': 'clear_status',
        'cost_e': 'cost_e',
        'cost_m': 'cost_m',
        'mod_e_regen': 'mod_e_regen',
        'mod_m_regen': 'mod_m_regen',
        'mod_draw': 'mod_draw',
        'discard': 'discard',
        'choose_from_exile': 'choose_from_exile',
        'reveal_hand': 'reveal_enemy_hand',
        'reveal_deck_top': 'reveal_deck_top',
        'steal_card': 'steal_enemy_card',
        'copy_card': 'copy_card',
        'random_discard_from_hand': 'random_discard_from_hand',
        'put_card_to_deck': 'put_card_to_deck',
        'shuffle_discard_into_deck': 'shuffle_discard_into_deck',
        'give_card_to_hand': 'give_card_to_hand',
        'give_card_to_deck': 'give_card_to_deck',
        'give_card_to_discard': 'give_card_to_discard',
        'remove_specific_card': 'remove_specific_card',
        'destroy_random_equip': 'destroy_random_equip',
        'destroy_all_equip': 'destroy_all_equip',
        'destroy_all_field_equip': 'destroy_all_field_equip',
        'equip_protection': 'counter_equip_protect',
        'remove_equip_protection': 'remove_equip_protection',
        'place_as_equip': 'place_as_equip',
        'block_action': 'block_own_actions',
        'block_card_type': 'block_card_type',
        'force_card_type': 'force_card_type',
        'nullify_current_card': 'nullify_current_card',
        'invincible': 'set_invincible',
        'untargetable': 'set_untargetable',
        'skip_turn': 'skip_turn',
        'extra_turn': 'extra_turn',
        'force_end_turn': 'force_end_turn',
        'mark_self_damage_source': 'mark_self_damage_source',
        'fission': 'fission',
        'multiply_next_damage': 'multiply_next_damage',
        'reduce_next_cost': 'reduce_next_cost',
        'increase_next_cost': 'increase_next_cost',
        'fusion': 'fusion',
        'add_tag': 'add_tag',
        'remove_tag': 'remove_tag',
        'transform_card': 'transform_card',
        'gain_durability': 'gain_durability',
        'lose_durability': 'lose_durability',
        'set_durability': 'set_durability',
        'player_prop_set': 'player_prop_set',
        'player_property_set': 'player_prop_set',
        'player_prop_add': 'player_prop_add',
        'player_property_add': 'player_prop_add',
        'record_play_count': 'record_play_count',
        'record_equip_turns': 'record_equip_turns',
        'reset_counter': 'reset_counter',
        'create_counter': 'create_counter',
        'exile_this': 'exile_this',
        'move_to_discard': 'move_to_discard',
        'move_to_deck': 'move_to_deck',
        'global_damage_mult': 'global_damage_mult',
        'global_heal_mult': 'global_heal_mult',
        'global_cost_mult': 'global_cost_mult',
        'swap_health': 'swap_health',
        'swap_hands': 'swap_hands',
        'broadcast_event': 'broadcast_event',
        'modify_damage': 'modify_damage',
        'add_status': 'status_add_named',
        'remove_status': 'status_remove_named',
        'set_status': 'set_status_named',
    }


    def _current_turn_marker(self) -> int:
        try:
            turn_index = getattr(self, 'turn_index', None)
            if turn_index is not None:
                return int(turn_index)
            return int(getattr(self, 'current_player', -1))
        except Exception:
            return -1

    def _set_invincible_until_next_own_turn_end(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        if self._is_status_immune(player_id):
            return
        ps = self.players[player_id]
        ps.invincible = True
        ps.achievement_invincible_triggered = True
        ps.invincible_until_player = player_id
        ps.invincible_granted_round = int(getattr(self, 'round_num', 0) or 0)
        ps.invincible_granted_turn_marker = self._current_turn_marker()

    def _note_achievement_health(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        try:
            current = int(getattr(ps, 'health', 0) or 0)
            previous = int(getattr(ps, 'achievement_min_health', current))
            ps.achievement_min_health = min(previous, current)
        except Exception:
            pass

    def _note_achievement_death(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        self._note_achievement_health(player_id)
        try:
            if int(getattr(ps, 'health', 0) or 0) <= 0 and getattr(ps, 'achievement_death_round', None) is None:
                ps.achievement_death_round = int(getattr(self, 'round_num', 0) or 0)
        except Exception:
            pass

    def _note_achievement_play(self, player_id: int, card: Optional[CardInstance]):
        if card is None or not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        try:
            turn_count = sum(int(v or 0) for v in (getattr(ps, 'cards_played_this_turn', {}) or {}).values())
            ps.achievement_max_cards_played_turn = max(int(getattr(ps, 'achievement_max_cards_played_turn', 0) or 0), turn_count)
        except Exception:
            pass
        try:
            def_id = str(getattr(card, 'def_id', '') or '')
            is_light = def_id.lower().endswith(':light') or def_id.lower() == 'light'
            if def_id and not is_light and def_id == str(getattr(ps, 'achievement_last_played_def_id', '') or ''):
                ps.achievement_last_played_def_count = int(getattr(ps, 'achievement_last_played_def_count', 0) or 0) + 1
            else:
                ps.achievement_last_played_def_id = def_id
                ps.achievement_last_played_def_count = 0 if is_light or not def_id else 1
            ps.achievement_max_same_name_streak = max(
                int(getattr(ps, 'achievement_max_same_name_streak', 0) or 0),
                int(getattr(ps, 'achievement_last_played_def_count', 0) or 0),
            )
        except Exception:
            pass

    def achievement_total_card_plays(self, player_id: int) -> int:
        if not (0 <= player_id < len(self.players)):
            return 0
        try:
            return max(0, int(getattr(self.players[player_id], 'achievement_total_card_plays', 0) or 0))
        except Exception:
            return 0

    def _note_achievement_card_discarded(self, player_id: int, card: Optional[CardInstance]):
        if card is None or not (0 <= player_id < len(self.players)):
            return
        try:
            instance_id = int(getattr(card, 'instance_id', 0) or 0)
            if not instance_id:
                return
            ps = self.players[player_id]
            counts = getattr(ps, 'achievement_same_instance_play_counts', None)
            if not isinstance(counts, dict):
                counts = {}
                ps.achievement_same_instance_play_counts = counts
            counts[instance_id] = int(counts.get(instance_id, 0) or 0) + 1
            ps.achievement_max_same_instance_plays = max(
                int(getattr(ps, 'achievement_max_same_instance_plays', 0) or 0),
                counts[instance_id],
            )
        except Exception:
            pass

    def _achievement_is_enemy(self, source_id: int, target_id: int) -> bool:
        if source_id == target_id:
            return False
        try:
            if hasattr(self, 'get_enemies'):
                return target_id in self.get_enemies(source_id)
        except Exception:
            pass
        return len(getattr(self, 'players', []) or []) == 2

    def _achievement_visible_card_total(self, player_id: int) -> int:
        if not (0 <= player_id < len(self.players)):
            return 0
        ps = self.players[player_id]
        try:
            return int(len(ps.hand) + len(ps.deck) + len(ps.discard))
        except Exception:
            return 0

    def _note_achievement_enemy_card_total(self, target_id: int):
        if not (0 <= target_id < len(self.players)):
            return
        total = self._achievement_visible_card_total(target_id)
        for source_id, source in enumerate(self.players):
            if self._achievement_is_enemy(source_id, target_id):
                try:
                    current = int(getattr(source, 'achievement_min_enemy_card_total', 999999) or 999999)
                    source.achievement_min_enemy_card_total = min(current, total)
                except Exception:
                    pass

    def _note_achievement_equipment_count(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        try:
            ps = self.players[player_id]
            ps.achievement_max_equipment_count = max(
                int(getattr(ps, 'achievement_max_equipment_count', 0) or 0),
                len(getattr(ps, 'equipment', []) or []),
            )
        except Exception:
            pass

    def _note_achievement_equipment_destroyed(self, source_id: Optional[int]):
        if source_id is None or not (0 <= source_id < len(self.players)):
            return
        try:
            ps = self.players[source_id]
            ps.achievement_equipment_destroyed = int(getattr(ps, 'achievement_equipment_destroyed', 0) or 0) + 1
        except Exception:
            pass

    def _note_achievement_counter_success(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        try:
            ps = self.players[player_id]
            ps.achievement_counter_successes = int(getattr(ps, 'achievement_counter_successes', 0) or 0) + 1
        except Exception:
            pass

    def _note_achievement_status_peak(self, target_id: int):
        if not (0 <= target_id < len(self.players)):
            return
        target = self.players[target_id]
        self._note_achievement_enemy_card_total(target_id)
        try:
            root_armor = self._custom_status_value(target_id, 'jungle:root', 'jungle:root_status', 'root_status')
        except Exception:
            root_armor = 0
        try:
            total_armor = max(0, int(getattr(target, 'armor', 0) or 0) + int(root_armor or 0))
            target.achievement_max_armor = max(
                int(getattr(target, 'achievement_max_armor', 0) or 0),
                total_armor,
            )
        except Exception:
            pass
        try:
            current_attack_blocked = max(0, int(getattr(target, 'attack_blocked', 0) or 0))
            last_attack_blocked = max(0, int(getattr(target, 'achievement_last_attack_blocked_value', current_attack_blocked) or 0))
            if current_attack_blocked > last_attack_blocked:
                target.achievement_attack_blocked_received = (
                    int(getattr(target, 'achievement_attack_blocked_received', 0) or 0)
                    + current_attack_blocked - last_attack_blocked
                )
            target.achievement_last_attack_blocked_value = current_attack_blocked
        except Exception:
            pass
        try:
            current_untargetable = max(0, int(getattr(target, 'untargetable', 0) or 0))
            last_untargetable = max(0, int(getattr(target, 'achievement_last_untargetable_value', current_untargetable) or 0))
            if current_untargetable > last_untargetable:
                target.achievement_untargetable_received = (
                    int(getattr(target, 'achievement_untargetable_received', 0) or 0)
                    + current_untargetable - last_untargetable
                )
            target.achievement_last_untargetable_value = current_untargetable
            target.achievement_max_untargetable = max(
                int(getattr(target, 'achievement_max_untargetable', 0) or 0),
                int(getattr(target, 'achievement_untargetable_received', 0) or 0),
                current_untargetable,
            )
        except Exception:
            pass
        try:
            status_types = 0
            builtin_values = [
                getattr(target, 'poison', 0), getattr(target, 'fire', 0), getattr(target, 'dodge', 0),
                getattr(target, 'armor', 0), getattr(target, 'triangle_stacks', 0), getattr(target, 'toxic', 0),
                getattr(target, 'overload', 0), getattr(target, 'foresight', 0), getattr(target, 'fracture', 0),
                getattr(target, 'stagnation', 0), getattr(target, 'blind', 0), getattr(target, 'heal_block', 0),
                getattr(target, 'weakness', 0), getattr(target, 'bleed', 0), getattr(target, 'attack_blocked', 0),
                getattr(target, 'attack_only', 0), getattr(target, 'honey_control_turns', 0),
            ]
            status_types += sum(1 for value in builtin_values if int(value or 0) > 0)
            custom = getattr(target, 'custom_statuses', {}) or {}
            status_types += sum(1 for value in custom.values() if int(value or 0) > 0)
        except Exception:
            status_types = 0
        for source_id, source in enumerate(self.players):
            if source_id == target_id:
                continue
            try:
                if hasattr(self, 'get_enemies'):
                    is_enemy = target_id in self.get_enemies(source_id)
                else:
                    is_enemy = len(self.players) == 2
                if is_enemy:
                    source.achievement_max_enemy_poison = max(
                        int(getattr(source, 'achievement_max_enemy_poison', 0) or 0),
                        int(getattr(target, 'poison', 0) or 0),
                    )
                    source.achievement_max_enemy_fire = max(
                        int(getattr(source, 'achievement_max_enemy_fire', 0) or 0),
                        int(getattr(target, 'fire', 0) or 0),
                    )
                    source.achievement_max_enemy_poison_fire_min = max(
                        int(getattr(source, 'achievement_max_enemy_poison_fire_min', 0) or 0),
                        min(int(getattr(target, 'poison', 0) or 0), int(getattr(target, 'fire', 0) or 0)),
                    )
                    source.achievement_max_enemy_status_types = max(
                        int(getattr(source, 'achievement_max_enemy_status_types', 0) or 0),
                        int(status_types or 0),
                    )
                    source.achievement_max_enemy_attack_blocked = max(
                        int(getattr(source, 'achievement_max_enemy_attack_blocked', 0) or 0),
                        int(getattr(target, 'achievement_attack_blocked_received', 0) or 0),
                    )
            except Exception:
                pass

    def _reset_achievement_match_stats(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        ps.achievement_min_health = ps.health
        ps.achievement_invincible_triggered = False
        ps.achievement_played_thorn = False
        ps.achievement_yggdrasil_revived = False
        ps.achievement_total_healed = 0
        ps.achievement_max_single_damage_dealt = 0
        ps.achievement_max_cards_played_turn = 0
        ps.achievement_turn_elixir_gained = 0
        ps.achievement_max_turn_elixir_gained = 0
        ps.achievement_same_instance_play_counts = {}
        ps.achievement_max_same_instance_plays = 0
        ps.achievement_last_played_def_id = ''
        ps.achievement_last_played_def_count = 0
        ps.achievement_max_same_name_streak = 0
        ps.achievement_max_enemy_poison = 0
        ps.achievement_max_enemy_fire = 0
        ps.achievement_max_enemy_poison_fire_min = 0
        ps.achievement_max_enemy_status_types = 0
        ps.achievement_attack_blocked_received = 0
        ps.achievement_last_attack_blocked_value = max(0, int(getattr(ps, 'attack_blocked', 0) or 0))
        ps.achievement_max_enemy_attack_blocked = 0
        ps.achievement_untargetable_received = 0
        ps.achievement_last_untargetable_value = max(0, int(getattr(ps, 'untargetable', 0) or 0))
        ps.achievement_max_untargetable = max(0, int(getattr(ps, 'untargetable', 0) or 0))
        ps.achievement_team_double_resources = False
        ps.achievement_min_enemy_card_total = 999999
        ps.achievement_counter_successes = 0
        ps.achievement_equipment_destroyed = 0
        ps.achievement_max_equipment_count = len(getattr(ps, 'equipment', []) or [])
        try:
            root_armor = self._custom_status_value(player_id, 'jungle:root', 'jungle:root_status', 'root_status')
        except Exception:
            root_armor = 0
        ps.achievement_max_armor = max(0, int(getattr(ps, 'armor', 0) or 0) + int(root_armor or 0))
        ps.achievement_total_card_plays = 0
        ps.achievement_death_round = None
        ps.achievement_self_caused_death = False

    def _reset_achievement_turn_stats(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        self.players[player_id].achievement_turn_elixir_gained = 0

    def _clear_invincible_state(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        ps.invincible = False
        ps.invincible_until_player = None
        ps.invincible_granted_round = -1
        ps.invincible_granted_turn_marker = -1

    def _should_expire_invincible_on_turn_end(self, player_id: int) -> bool:
        if not (0 <= player_id < len(self.players)):
            return False
        ps = self.players[player_id]
        if not ps.invincible:
            return False
        until_player = getattr(ps, 'invincible_until_player', None)
        if until_player is not None and until_player != player_id:
            return False
        grant_round_value = getattr(ps, 'invincible_granted_round', -1)
        grant_marker_value = getattr(ps, 'invincible_granted_turn_marker', -1)
        grant_round = int(grant_round_value if grant_round_value is not None else -1)
        grant_marker = int(grant_marker_value if grant_marker_value is not None else -1)
        current_round = int(getattr(self, 'round_num', 0) or 0)
        current_marker = self._current_turn_marker()
        return not (grant_round == current_round and grant_marker == current_marker)


    def _find_equipment_for_card(self, owner_id: int, card: Optional[CardInstance]):
        if card is None or owner_id < 0 or owner_id >= len(self.players):
            return None
        instance_id = getattr(card, 'instance_id', None)
        for eq in self.players[owner_id].equipment:
            if getattr(eq.card_instance, 'instance_id', None) == instance_id:
                return eq
        return None

    def _find_equipment_by_card_instance_id(self, instance_id):
        try:
            iid = int(instance_id)
        except Exception:
            return None, None
        for owner_id, ps in enumerate(self.players):
            for eq in ps.equipment:
                if getattr(eq.card_instance, 'instance_id', None) == iid:
                    return owner_id, eq
        return None, None

    def _resolve_equipment_ref(self, player_id, equipment_ref, current_card=None):
        if isinstance(equipment_ref, EquipmentInstance):
            return equipment_ref
        if equipment_ref is None:
            equipment_ref = {'ref': 'current_equipment'}
        if isinstance(equipment_ref, str):
            equipment_ref = {'ref': equipment_ref}
        if not isinstance(equipment_ref, dict):
            return None
        ref = equipment_ref.get('ref')
        if ref in ('event_equipment', 'trigger_equipment', 'destroyed_equipment'):
            context = getattr(self, '_active_effect_context', {}) or {}
            instance_id = context.get('selected_equipment_instance_id') if isinstance(context, dict) else None
            _, eq = self._find_equipment_by_card_instance_id(instance_id)
            return eq
        if ref in ('current_equipment', 'this_equipment'):
            eq = self._find_equipment_for_card(player_id, current_card)
            if eq is not None:
                return eq
            _, eq = self._find_equipment_by_card_instance_id(getattr(current_card, 'instance_id', None))
            return eq
        if ref in ('selected_equipment', 'choice_equipment'):
            context = getattr(self, '_active_effect_context', {}) or {}
            instance_id = context.get('selected_equipment_instance_id') if isinstance(context, dict) else None
            choice = getattr(self, '_active_choice', None) or {}
            if instance_id is None and isinstance(choice, dict):
                instance_id = choice.get('target_instance_id')
            if instance_id is None and isinstance(choice, dict) and isinstance(choice.get('target_instance_ids'), list) and choice.get('target_instance_ids'):
                instance_id = choice.get('target_instance_ids')[0]
            _, eq = self._find_equipment_by_card_instance_id(instance_id)
            return eq
        if ref == 'card_equipment':
            target_card = self._resolve_card_ref(player_id, equipment_ref.get('card'), current_card)
            _, eq = self._find_equipment_by_card_instance_id(getattr(target_card, 'instance_id', None))
            return eq
        return None

    def _get_equipment_property_value(self, eq, prop):
        if eq is None:
            return 0
        prop = str(prop or 'turns_equipped')
        if prop in ('turns_equipped', 'equip_turns', 'equipped_turns'):
            return int(getattr(eq, 'turns_equipped', 0))
        if prop in ('effect_target', 'target_player'):
            return int(getattr(eq, 'effect_target', getattr(eq, 'owner', 0)))
        if prop in ('corruption_active', 'is_corruption_active'):
            return 1 if bool(getattr(eq, 'corruption_active', False)) else 0
        if prop == 'owner':
            return int(getattr(eq, 'owner', 0))
        return int(getattr(eq, 'custom_vars', {}).get(prop, 0) or 0)

    def _get_status_count(self, target_id, status):
        if target_id < 0:
            return sum(self._get_status_count(pid, status) for pid in range(len(self.players)))
        if not (0 <= target_id < len(self.players)):
            return 0
        ps = self.players[target_id]
        status = str(status or '').strip()
        if status in ('status_immune', 'immune', '状态免疫'):
            return 1 if self._is_status_immune(target_id) else 0
        if self._is_status_immune(target_id) and status not in ('status_immune', 'immune', '状态免疫'):
            return 0
        counts = {
            'poison': ps.poison,
            '中毒': ps.poison,
            'burn': ps.fire,
            'fire': ps.fire,
            '灼烧': ps.fire,
            'toxic': ps.toxic,
            '淬毒': ps.toxic,
            'dodge': ps.dodge,
            '闪避': ps.dodge,
            'equip_protection': ps.equipment_protection,
            'equipment_protection': ps.equipment_protection,
            '装备摧毁保护': ps.equipment_protection,
            '装备保护': ps.equipment_protection,
            'invincible': 1 if ps.invincible else 0,
            '无敌': 1 if ps.invincible else 0,
            'untargetable': int(getattr(ps, 'untargetable', 0) or 0),
            '不可选中': int(getattr(ps, 'untargetable', 0) or 0),
            '邪眼': self._nazar_status_value(target_id),
            'Nazar': self._nazar_status_value(target_id),
            'nazar': self._nazar_status_value(target_id),
            'sluggish': ps.sluggish,
            '迟缓': ps.sluggish,
            'overload': ps.overload,
            '超载': ps.overload,
            'foresight': ps.foresight,
            '预知': ps.foresight,
            'fracture': ps.fracture,
            '破损': ps.fracture,
            'stagnation': ps.stagnation,
            '滞留': ps.stagnation,
            'blind': ps.blind,
            '失明': ps.blind,
            'heal_block': ps.heal_block,
            '禁疗': ps.heal_block,
            'weakness': ps.weakness,
            '虚弱': ps.weakness,
            'bleed': ps.bleed,
            '流血': ps.bleed,
            'fragment': ps.fragment_stacks,
            'fragment_stacks': ps.fragment_stacks,
            '碎片': ps.fragment_stacks,
            'stunned': ps.skip_turn,
            'dizzy': ps.skip_turn,
            'skip_turn': ps.skip_turn,
            '眩晕': ps.skip_turn,
        }
        if status in counts:
            return int(counts.get(status, 0))
        return int(getattr(ps, 'custom_statuses', {}).get(status, 0) or 0)

    def _status_application_blocked(self, target_id: int, status: str) -> bool:
        if not (0 <= target_id < len(self.players)):
            return True
        # 状态免疫只让状态暂时不起作用，不阻止状态被施加、叠层或按自身规则衰减。
        return False

    def _custom_status_definition(self, status):
        status = str(status or '').strip()
        if not status:
            return None
        v2_status = (getattr(self, 'v2_status_defs', {}) or {}).get(status)
        if isinstance(v2_status, dict):
            return v2_status
        try:
            from mod_loader import load_all_mods
            for mod in load_all_mods():
                for item in getattr(mod, 'custom_statuses', []) or []:
                    if not isinstance(item, dict):
                        continue
                    if status in (str(item.get('id', '')).strip(), str(item.get('name', '')).strip(),
                                  str(item.get('name_cn', '')).strip(), str(item.get('name_en', '')).strip()):
                        return item
        except Exception:
            return None
        return None

    def _status_keep_when_zero(self, status):
        definition = self._custom_status_definition(status)
        if not isinstance(definition, dict):
            return False
        return bool(definition.get('keep_when_zero') or definition.get('keep_at_zero') or definition.get('persist_at_zero'))

    def _normalize_status_value(self, ps, status):
        status = str(status or '').strip()
        if status in ('poison', '中毒'):
            ps.poison = max(0, int(ps.poison))
        elif status in ('burn', 'fire', '灼烧'):
            ps.fire = max(0, int(ps.fire))
        elif status in ('toxic', '淬毒'):
            ps.toxic = max(0, int(ps.toxic))
        elif status in ('dodge', '闪避'):
            ps.dodge = max(0, int(ps.dodge))
        elif status in ('equip_protection', 'equipment_protection', '装备摧毁保护', '装备保护'):
            ps.equipment_protection = max(0, int(ps.equipment_protection))
        elif status in ('邪眼', 'Nazar', 'nazar'):
            value = 0
            custom = getattr(ps, 'custom_statuses', {}) or {}
            for key in ('nazar', '邪眼', 'Nazar'):
                try:
                    value += int(custom.get(key, 0) or 0)
                except Exception:
                    pass
            if getattr(ps, 'nazar_active', False):
                value += max(0, 2 - int(getattr(ps, 'nazar_big_hits', 0) or 0))
            ps.nazar_active = False
            ps.nazar_big_hits = 0
            for key in ('邪眼', 'Nazar'):
                custom.pop(key, None)
            if value > 0:
                custom['nazar'] = value
            else:
                custom.pop('nazar', None)
            ps.custom_statuses = custom
        elif status in ('sluggish', '迟缓'):
            ps.sluggish = max(0, int(ps.sluggish))
        elif status in ('overload', '超载'):
            ps.overload = max(0, int(ps.overload))
        elif status in ('foresight', '预知'):
            ps.foresight = max(0, int(ps.foresight))
        elif status in ('fracture', '破损'):
            ps.fracture = max(0, int(ps.fracture))
        elif status in ('stagnation', '滞留'):
            ps.stagnation = max(0, int(ps.stagnation))
        elif status in ('blind', '失明'):
            ps.blind = max(0, int(ps.blind))
        elif status in ('heal_block', '禁疗'):
            ps.heal_block = max(0, int(ps.heal_block))
        elif status in ('weakness', '虚弱'):
            ps.weakness = max(0, int(ps.weakness))
        elif status in ('bleed', '流血'):
            ps.bleed = max(0, int(ps.bleed))
        elif status in ('fragment', 'fragment_stacks', '碎片'):
            ps.fragment_stacks = max(0, int(ps.fragment_stacks))
        elif status in ('status_immune', 'immune', '状态免疫'):
            ps.custom_statuses = getattr(ps, 'custom_statuses', {})
            value = 1 if any(int(ps.custom_statuses.get(key, 0) or 0) > 0 for key in ('status_immune', 'immune', '状态免疫')) else 0
            for key in ('status_immune', 'immune', '状态免疫'):
                ps.custom_statuses.pop(key, None)
            if value > 0:
                ps.custom_statuses['status_immune'] = 1
        elif status:
            ps.custom_statuses = getattr(ps, 'custom_statuses', {})
            value = int(ps.custom_statuses.get(status, 0) or 0)
            if value <= 0 and not self._status_keep_when_zero(status):
                ps.custom_statuses.pop(status, None)
            else:
                ps.custom_statuses[status] = max(0, value)

    def _zone_size(self, target_id, zone):
        if target_id < 0:
            return sum(self._zone_size(pid, zone) for pid in range(len(self.players)))
        if not (0 <= target_id < len(self.players)):
            return 0
        ps = self.players[target_id]
        zone = str(zone or 'hand')
        if zone == 'equipment':
            return len(ps.equipment)
        if zone == 'deck':
            return len(ps.deck)
        if zone == 'discard':
            return len(ps.discard)
        if zone == 'exile':
            return len(ps.exile)
        return len(ps.hand)

    def _reset_turn_damage_counters(self):
        for ps in self.players:
            ps.turn_damage_taken = 0
            ps.turn_damage_dealt = 0

    def _save_last_turn_damage_snapshot(self, player_id: int):
        if 0 <= player_id < len(self.players):
            ps = self.players[player_id]
            ps.last_turn_damage_taken = int(getattr(ps, 'turn_damage_taken', 0) or 0)
            ps.last_turn_damage_dealt = int(getattr(ps, 'turn_damage_dealt', 0) or 0)

    def _save_turn_start_snapshot(self, player_id: int):
        if 0 <= player_id < len(self.players):
            ps = self.players[player_id]
            ps.turn_start_snapshot = {
                'health': int(getattr(ps, 'health', 0) or 0),
                'elixir': int(getattr(ps, 'elixir', 0) or 0),
                'magic': int(getattr(ps, 'magic', 0) or 0),
            }

    def _save_match_start_snapshot(self, player_id: int):
        if 0 <= player_id < len(self.players):
            ps = self.players[player_id]
            ps.match_start_snapshot = {
                'health': int(getattr(ps, 'health', 0) or 0),
                'elixir': int(getattr(ps, 'elixir', 0) or 0),
                'magic': int(getattr(ps, 'magic', 0) or 0),
            }

    def _save_all_match_start_snapshots(self):
        for pid in range(len(self.players)):
            self._save_match_start_snapshot(pid)

    def _restore_turn_start_snapshot(self, player_id: int, extra_elixir_loss: int = 0):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        snap = dict(getattr(ps, 'turn_start_snapshot', {}) or {})
        if not snap:
            snap = {'health': ps.health, 'elixir': ps.elixir, 'magic': ps.magic}
        ps.health = max(0, min(int(snap.get('health', ps.health)), int(ps.max_health)))
        ps.elixir = max(0, min(int(snap.get('elixir', ps.elixir)) - max(0, int(extra_elixir_loss or 0)), int(ps.max_elixir)))
        ps.magic = max(0, min(int(snap.get('magic', ps.magic)), int(ps.max_magic)))

    def _restore_match_start_snapshot(self, player_id: int, extra_elixir_loss: int = 0):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        snap = dict(getattr(ps, 'match_start_snapshot', {}) or {})
        if not snap:
            snap = {'health': ps.health, 'elixir': ps.elixir, 'magic': ps.magic}
        ps.health = max(0, min(int(snap.get('health', ps.health)), int(ps.max_health)))
        ps.elixir = max(0, min(int(snap.get('elixir', ps.elixir)) - max(0, int(extra_elixir_loss or 0)), int(ps.max_elixir)))
        ps.magic = max(0, min(int(snap.get('magic', ps.magic)), int(ps.max_magic)))

    def _apply_yucca_turn_start_heal(self, player_id: int, label: str = '丝兰') -> int:
        if not (0 <= player_id < len(self.players)):
            return 0
        ps = self.players[player_id]
        before = ps.health
        ps.heal(3)
        base_healed = max(0, ps.health - before)
        bonus_healed = 0
        if int(getattr(ps, 'last_turn_damage_dealt', 0) or 0) < 10:
            bonus_before = ps.health
            ps.heal(7)
            bonus_healed = max(0, ps.health - bonus_before)
        healed = base_healed + bonus_healed
        if healed <= 0:
            return 0
        if bonus_healed:
            self.log_msg(f"{label}效果：{self.pn(player_id)}+{base_healed}H，低伤害回合额外+{bonus_healed}H")
        else:
            self.log_msg(f"{label}效果：{self.pn(player_id)}+{base_healed}H")
        return healed

    def _sewers_card_requires_player_target(self, card: Optional[CardInstance]) -> bool:
        if card is None:
            return False
        flags = self._effective_card_flags(card)
        if 'wide_strike' in flags or getattr(card, 'card_type', '') == 'guard':
            return False
        if self._card_is_self_only(card):
            return False
        return bool(
            getattr(card, 'card_type', '') == 'thorn'
            or self._v2_play_requires_choice_target(card)
            or self._root_play_requires_owner_target(card)
        )

    def _sewers_light_bulb_candidates(self) -> List[int]:
        candidates = []
        for target_id, target in enumerate(self.players):
            if not int((getattr(target, 'custom_vars', {}) or {}).get('sewers_light_bulb_active', 0) or 0):
                continue
            if int(getattr(target, 'health', 0) or 0) <= 0:
                continue
            if bool(getattr(target, 'untargetable', 0)) and not self._is_status_immune(target_id):
                continue
            candidates.append(target_id)
        return candidates

    def _sewers_forced_target_for_player(self, player_id: int) -> Optional[int]:
        if not (0 <= player_id < len(self.players)):
            return None
        candidates = self._sewers_light_bulb_candidates()
        ps = self.players[player_id]
        signature = ','.join(str(pid) for pid in sorted(candidates))
        if not candidates:
            ps.custom_vars.pop('sewers_forced_target_id', None)
            ps.custom_vars.pop('sewers_forced_target_signature', None)
            return None
        stored_signature = str(ps.custom_vars.get('sewers_forced_target_signature', '') or '')
        try:
            stored_target = int(ps.custom_vars.get('sewers_forced_target_id', -1))
        except (TypeError, ValueError):
            stored_target = -1
        if stored_signature != signature or stored_target not in candidates:
            stored_target = random.choice(candidates)
            ps.custom_vars['sewers_forced_target_signature'] = signature
            ps.custom_vars['sewers_forced_target_id'] = stored_target
        return stored_target

    def _sewers_forced_target_for_card(self, player_id: int, card: Optional[CardInstance]) -> Optional[int]:
        if not self._sewers_card_requires_player_target(card):
            return None
        return self._sewers_forced_target_for_player(player_id)

    def _sewers_clear_light_bulb_at_turn_start(self, player_id: int) -> None:
        if not (0 <= player_id < len(self.players)):
            return
        self.players[player_id].custom_vars.pop('sewers_light_bulb_active', None)

    def _sewers_apply_forced_target_choice(self, player_id: int, card: Optional[CardInstance], choice):
        target_id = self._sewers_forced_target_for_card(player_id, card)
        if target_id is None:
            return choice, None
        updated = dict(choice or {})
        updated['target_player'] = target_id
        updated['target_player_id'] = target_id
        updated['target_id'] = target_id
        return updated, target_id

    def _sewers_selected_player_targets(self, player_id: int, card: Optional[CardInstance], choice) -> List[int]:
        flags = self._effective_card_flags(card)
        if 'wide_strike' in flags:
            return list(self._wide_strike_target_ids(player_id, card))
        if not self._sewers_card_requires_player_target(card):
            return []
        target_id = self._choice_target_from_choice(choice, -1)
        if target_id < 0 and getattr(card, 'card_type', '') == 'thorn' and len(self.players) == 2:
            target_id = 1 - player_id
        return [target_id] if 0 <= target_id < len(self.players) else []

    def _sewers_trigger_vampire_fangs(self, player_id: int, card: Optional[CardInstance], choice) -> None:
        for selected_id in self._sewers_selected_player_targets(player_id, card, choice):
            owner = self.players[selected_id]
            for eq in list(getattr(owner, 'equipment', []) or []):
                if not self._card_is(eq.card_instance, 'VampireFang', 'sewers:vampire_fang'):
                    continue
                target_id = self._equipment_effect_target_id(eq, selected_id)
                if not (0 <= target_id < len(self.players)):
                    continue
                target = self.players[target_id]
                before = int(getattr(target, 'health', 0) or 0)
                target.heal(3)
                healed = max(0, int(getattr(target, 'health', 0) or 0) - before)
                if healed > 0:
                    self.log_msg(f"{self.pn(selected_id)}的吸血鬼尖牙使{self.pn(target_id)}回复{healed}H")

    def _sewers_grow_clay_power(self, target_id: int, amount: int) -> None:
        if amount < 8 or not (0 <= target_id < len(self.players)):
            return
        for hand_card in list(getattr(self.players[target_id], 'hand', []) or []):
            if self._card_is(hand_card, 'Clay', 'sewers:clay'):
                hand_card.power_value = max(0, int(getattr(hand_card, 'power_value', 0) or 0) + 3)

    def _sewers_is_confusion_card(self, card: Optional[CardInstance]) -> bool:
        if card is None:
            return False
        flags = {str(flag or '').lower() for flag in self._effective_card_flags(card)}
        return bool(flags.intersection({'confusion', 'sewers:confusion', 'tag_confusion', 'tag_sewers:confusion'}))

    def _sewers_confusion_disguise(self, responder_id: int, played_card) -> Optional[dict]:
        try:
            actual = played_card if isinstance(played_card, CardInstance) else CardInstance.from_dict(played_card)
        except Exception:
            return None
        if not self._sewers_is_confusion_card(actual):
            return None
        actual_damage = max(0, int(getattr(actual.card_def, 'damage', 0) or 0))
        actual_hits = max(1, int(getattr(actual.card_def, 'hits', 1) or 1))
        target_total = actual_damage * actual_hits
        allowed_ids = getattr(self, 'allowed_card_ids', None)
        candidates = []
        best_distance = None
        for def_id, card_def in CARD_DEFS.items():
            if def_id in (actual.def_id, ERROR_CARD_ID):
                continue
            if allowed_ids is not None and def_id not in allowed_ids:
                continue
            weight = max(0, int(getattr(card_def, 'count', 0) or 0))
            damage = max(0, int(getattr(card_def, 'damage', 0) or 0))
            hits = max(1, int(getattr(card_def, 'hits', 1) or 1))
            if getattr(card_def, 'card_type', '') != 'thorn' or weight <= 0 or damage <= 0:
                continue
            distance = abs(damage * hits - target_total)
            if best_distance is None or distance < best_distance:
                best_distance = distance
                candidates = [(def_id, weight)]
            elif distance == best_distance:
                candidates.append((def_id, weight))
        if not candidates:
            return None
        seed = f"sewers-confusion:{actual.instance_id}:{responder_id}:{self.round_num}:{','.join(d for d, _ in candidates)}"
        rng = random.Random(seed)
        total_weight = sum(weight for _, weight in candidates)
        pick = rng.uniform(0, total_weight)
        chosen_id = candidates[-1][0]
        running = 0.0
        for def_id, weight in candidates:
            running += weight
            if pick <= running:
                chosen_id = def_id
                break
        fake = CardInstance(chosen_id).to_dict()
        fake['instance_id'] = actual.instance_id
        fake['sewers_confusion_disguise'] = True
        return fake

    def _public_pending_response(self, for_player: int):
        pending = getattr(self, 'pending_response', None)
        if not isinstance(pending, dict):
            return pending
        try:
            source_id = int(pending.get('player_id', -1))
        except (TypeError, ValueError):
            source_id = -1
        is_responder = for_player != source_id
        counter_entries = pending.get('counter_cards') or []
        if counter_entries:
            responder_ids = set()
            for entry in counter_entries:
                if not isinstance(entry, dict):
                    continue
                try:
                    responder_ids.add(int(entry.get('responder_id', -1)))
                except (TypeError, ValueError):
                    continue
            is_responder = for_player in responder_ids
        if not is_responder:
            return pending
        disguised = self._sewers_confusion_disguise(for_player, pending.get('card') or {})
        if not disguised:
            return pending
        public = copy.deepcopy(pending)
        public['card'] = disguised
        return public

    def build_sewers_confusion_damage_prediction(self, responder_id: int, played_card, counter_cards=None):
        disguised = self._sewers_confusion_disguise(responder_id, played_card)
        if not disguised:
            return self.build_response_damage_prediction(responder_id, counter_cards or [])
        sim = copy.deepcopy(self)
        if isinstance(getattr(sim, 'pending_response', None), dict):
            sim.pending_response = copy.deepcopy(sim.pending_response)
            sim.pending_response['card'] = disguised
            try:
                fake_card = CardInstance.from_dict(disguised)
                sim.pending_response['is_precision'] = 'precision' in sim._effective_card_flags(fake_card)
            except Exception:
                pass
        return sim.build_response_damage_prediction(responder_id, counter_cards or [])

    def _record_damage(self, target_id, amount, source_id=None):
        try:
            amount = int(amount)
        except Exception:
            amount = 0
        if amount <= 0:
            return
        self._sewers_grow_clay_power(target_id, amount)
        if 0 <= target_id < len(self.players):
            target = self.players[target_id]
            target.turn_damage_taken += amount
            target.total_damage_taken += amount
            if source_id == target_id and int(getattr(target, 'health', 0) or 0) <= 0:
                target.achievement_self_caused_death = True
        if isinstance(source_id, int) and 0 <= source_id < len(self.players):
            source = self.players[source_id]
            source.turn_damage_dealt += amount
            source.total_damage_dealt += amount
            source.achievement_max_single_damage_dealt = max(
                int(getattr(source, 'achievement_max_single_damage_dealt', 0) or 0),
                int(amount),
            )
        self._trigger_v2_damage_status_events(target_id, source_id, amount)

    def _get_v2_status_def(self, status_id: str) -> Optional[dict]:
        defs = getattr(self, 'v2_status_defs', {}) or {}
        status = defs.get(str(status_id or ''))
        return status if isinstance(status, dict) else None

    def _get_v2_status_event(self, status_id: str, event_name: str):
        status = self._get_v2_status_def(status_id)
        events = status.get('events') if isinstance(status, dict) else None
        if not isinstance(events, dict):
            return None
        return events.get(event_name)

    def _run_v2_status_event(self, player_id: int, status_id: str, event_name: str, extra: Optional[dict] = None):
        if not (0 <= player_id < len(self.players)):
            return None
        event_def = self._get_v2_status_event(status_id, event_name)
        if not event_def:
            return None
        context = {
            'source_player': player_id,
            'target_player': player_id,
            'card': None,
            'room': getattr(self, 'room', None),
            'loadout': getattr(self, 'v2_loadout', None),
            'vars': {
                'status_id': status_id,
                'status_stack': self._get_status_count(player_id, status_id),
            },
            'last_damage': (extra or {}).get('amount', 0),
            'current_event': event_name,
            'current_action': extra or {},
        }
        result = run_v2_event(self, context, event_def)
        if isinstance(result, dict) and result.get('needs_v2_ui'):
            self._store_v2_ui_pause(result.get('v2_ui_pause') or {})
        return result

    def _trigger_v2_status_events_for_player(self, player_id: int, event_name: str, extra: Optional[dict] = None):
        if not (0 <= player_id < len(self.players)):
            return
        statuses = list((getattr(self.players[player_id], 'custom_statuses', {}) or {}).items())
        for status_id, value in statuses:
            try:
                if int(value or 0) <= 0:
                    continue
            except Exception:
                continue
            self._run_v2_status_event(player_id, str(status_id), event_name, extra)
            if getattr(self, 'game_over', False) or getattr(self, 'pending_v2_ui', None):
                break

    def _trigger_v2_damage_status_events(self, target_id, source_id, amount):
        try:
            amount = int(amount)
        except Exception:
            amount = 0
        if amount <= 0:
            return
        extra = {'amount': amount, 'source_player': source_id, 'target_player': target_id}
        if isinstance(target_id, int) and 0 <= target_id < len(self.players):
            self._trigger_v2_status_events_for_player(target_id, 'on_damage_taken', extra)
        if isinstance(source_id, int) and 0 <= source_id < len(self.players):
            self._trigger_v2_status_events_for_player(source_id, 'on_damage_dealt', extra)

    def _v2_hooks_for(self, hook_name: str) -> List[dict]:
        hooks = [hook for hook in (getattr(self, 'v2_event_hooks', []) or []) if isinstance(hook, dict) and hook.get('hook') == hook_name]
        return sorted(hooks, key=lambda hook: (
            int(hook.get('priority', 0) if isinstance(hook.get('priority', 0), int) else 0),
            str(hook.get('_mod_id', '')),
        ))

    def _v2_hook_filter_matches(self, hook: dict, context: dict) -> bool:
        flt = hook.get('filter')
        if not isinstance(flt, dict) or not flt:
            return True
        action = context.get('current_action') if isinstance(context.get('current_action'), dict) else {}
        card = context.get('card')
        for key, expected in flt.items():
            if key == 'damage_tag':
                expected_tag = str(expected)
                damage_tags = action.get('damage_tags')
                if not isinstance(damage_tags, list):
                    damage_tags = [action.get('damage_tag')]
                if expected_tag not in [str(tag) for tag in damage_tags if tag is not None]:
                    return False
            elif key in ('damage_kind', 'kind'):
                if str(action.get('damage_kind') or '') != str(expected):
                    return False
            elif key == 'card_type':
                if not card or str(getattr(card, 'card_type', '')) != str(expected):
                    return False
            elif key in ('card_tag', 'tag'):
                if str(expected) not in self._effective_card_flags(card):
                    return False
            elif key == 'card_id':
                if not card or str(getattr(card, 'def_id', '')) != str(expected):
                    return False
            elif key in ('source', 'source_player'):
                if str(context.get('source_player')) != str(expected):
                    return False
            elif key in ('target', 'target_player'):
                if str(context.get('target_player')) != str(expected):
                    return False
        return True

    def _v2_card_hook_context(self, hook_name: str, player_id: int, card: CardInstance,
                              choice: Optional[dict] = None) -> dict:
        target_id = -1
        target_explicit = False
        if isinstance(choice, dict):
            for key in ('target_player', 'target_player_id', 'target_id'):
                if key in choice:
                    try:
                        target_id = int(choice.get(key))
                        target_explicit = True
                        break
                    except Exception:
                        target_id = -1
        if not (0 <= target_id < len(self.players)):
            target_id = 1 - player_id if len(self.players) == 2 else -1
        if not (0 <= target_id < len(self.players)):
            target_id = -1
        return {
            'source_player': player_id,
            'target_player': target_id,
            'target_player_explicit': target_explicit,
            'card': card,
            'room': getattr(self, 'room', None),
            'loadout': getattr(self, 'v2_loadout', None),
            'vars': {
                'card_id': getattr(card, 'def_id', ''),
                'card_type': getattr(card, 'card_type', ''),
                'choice': choice or {},
            },
            'last_damage': 0,
            'current_event': hook_name,
            'current_action': {
                'card_id': getattr(card, 'def_id', ''),
                'card_type': getattr(card, 'card_type', ''),
                'choice': choice or {},
            },
        }

    def _run_v2_play_hook(self, hook_name: str, player_id: int, card: CardInstance,
                          choice: Optional[dict] = None):
        if not getattr(self, 'v2_event_hooks', None):
            return None
        context = self._v2_card_hook_context(hook_name, player_id, card, choice)
        return self._run_v2_event_hooks(hook_name, context, None)

    def _defer_v2_before_play_until_choice(self, card: CardInstance, choice: Optional[dict] = None) -> bool:
        try:
            return bool(self._card_needs_choice(card) and not self._choice_satisfies_request(card, choice))
        except Exception:
            return False

    def _v2_active_damage_card(self):
        card = getattr(self, '_active_v2_card', None)
        if isinstance(card, CardInstance):
            return card
        context = getattr(self, '_active_effect_context', None)
        if isinstance(context, dict):
            for key in ('event_card', 'used_card', 'trigger_card', 'card'):
                value = context.get(key)
                if isinstance(value, CardInstance):
                    return value
        return None

    def _v2_damage_tags(self, damage_kind: str, damage_tag: str, source: str = '',
                        damage_type: str = DAMAGE_TYPE_PHYSICAL) -> List[str]:
        tags = []
        type_tag = damage_type_tag(damage_type)
        for value in (type_tag, damage_tag, damage_kind):
            text = str(value or '').strip()
            if text and text not in tags:
                tags.append(text)
        source_text = str(source or '')
        source_map = {
            'fire': 'gtn:fire',
            'burn': 'gtn:fire',
            'poison': 'gtn:poison',
            'battery': 'gtn:battery',
        }
        if '灼' in source_text:
            source_map['source'] = 'gtn:fire'
        elif '毒' in source_text:
            source_map['source'] = 'gtn:poison'
        elif '电池' in source_text or '電池' in source_text:
            source_map['source'] = 'gtn:battery'
        for tag in source_map.values():
            if tag not in tags:
                tags.append(tag)
        return tags

    def _v2_damage_context(self, target_id: int, amount: int, source_id=None, *,
                           damage_kind: str = 'attack', damage_tag: str = 'gtn:physical',
                           source: str = '', is_battery: bool = False, is_precision: bool = False,
                           card: Optional[CardInstance] = None, damage_type: Optional[str] = None) -> dict:
        if card is None:
            card = self._v2_active_damage_card()
        source_player = source_id if isinstance(source_id, int) and 0 <= source_id < len(self.players) else target_id
        resolved_damage_type = infer_damage_type(source, damage_kind, damage_tag, damage_type)
        tags = self._v2_damage_tags(damage_kind, damage_tag, source, resolved_damage_type)
        primary_tag = str(damage_tag or '').strip() or (tags[0] if tags else '')
        return {
            'source_player': source_player,
            'target_player': target_id,
            'card': card,
            'room': getattr(self, 'room', None),
            'loadout': getattr(self, 'v2_loadout', None),
            'vars': {
                'amount': amount,
                'original_amount': amount,
                'damage_kind': damage_kind,
                'damage_type': resolved_damage_type,
                'damage_tag': primary_tag,
                'damage_tags': tags,
                'source': source,
                'is_battery': bool(is_battery),
                'is_precision': bool(is_precision),
            },
            'last_damage': 0,
            'current_event': 'damage',
            'current_action': {
                'amount': amount,
                'original_amount': amount,
                'damage_kind': damage_kind,
                'damage_type': resolved_damage_type,
                'damage_tag': primary_tag,
                'damage_tags': tags,
                'source': source,
                'is_battery': bool(is_battery),
                'is_precision': bool(is_precision),
            },
        }

    def _coerce_v2_damage_value(self, value, fallback: int) -> int:
        try:
            return max(0, int(math.floor(float(value))))
        except Exception:
            try:
                return max(0, int(fallback))
            except Exception:
                return 0

    def _run_v2_damage_modifiers(self, context: dict, amount: int) -> int:
        action = context.get('current_action', {}) if isinstance(context, dict) else {}
        vars_dict = context.get('vars', {}) if isinstance(context, dict) else {}
        damage_type = action.get('damage_type') or vars_dict.get('damage_type')
        if infer_damage_type(damage_type=damage_type) == DAMAGE_TYPE_MAGIC:
            return max(0, int(amount or 0))
        if not getattr(self, 'v2_event_hooks', None):
            return max(0, int(amount or 0))
        context.setdefault('vars', {})
        context.setdefault('current_action', {})
        for hook_name in ('before_damage', 'modify_damage'):
            context['current_event'] = hook_name
            context['vars']['amount'] = amount
            context['vars']['event_value'] = amount
            context['current_action']['amount'] = amount
            value = self._run_v2_event_hooks(hook_name, context, amount)
            amount = self._coerce_v2_damage_value(value, amount)
            if getattr(self, 'pending_v2_ui', None):
                break
        return max(0, int(amount or 0))

    def _run_v2_after_damage_hooks(self, context: dict, dealt: int) -> None:
        if not getattr(self, 'v2_event_hooks', None):
            return
        context.setdefault('vars', {})
        context.setdefault('current_action', {})
        context['last_damage'] = dealt
        context['vars']['dealt'] = dealt
        context['vars']['actual_damage'] = dealt
        context['vars']['event_value'] = dealt
        context['current_action']['dealt'] = dealt
        context['current_action']['actual_damage'] = dealt
        context['current_event'] = 'after_damage'
        self._run_v2_event_hooks('after_damage', context, dealt)

    def _run_v2_event_hooks(self, hook_name: str, context: Optional[dict] = None, event_value=None):
        hooks = self._v2_hooks_for(hook_name)
        if not hooks:
            return event_value
        ctx = dict(context or {})
        ctx.setdefault('source_player', 0)
        ctx.setdefault('target_player', None)
        ctx.setdefault('card', None)
        ctx.setdefault('room', getattr(self, 'room', None))
        ctx.setdefault('loadout', getattr(self, 'v2_loadout', None))
        ctx.setdefault('vars', {})
        ctx.setdefault('last_damage', 0)
        ctx.setdefault('current_event', hook_name)
        ctx.setdefault('current_action', {})
        if event_value is not None:
            ctx['event_value'] = event_value
            ctx.setdefault('vars', {})['event_value'] = event_value
        for hook in hooks:
            if not self._v2_hook_filter_matches(hook, ctx):
                continue
            steps = hook.get('steps', [])
            if not isinstance(steps, list):
                continue
            ctx['current_hook'] = hook
            result = run_v2_event(self, ctx, {'steps': steps})
            if isinstance(result, dict) and result.get('needs_v2_ui'):
                self._log_mod_runtime_error(
                    'v2_event_hook',
                    RuntimeError('event_hooks cannot request UI; use card/status/opening_event events instead'),
                    ctx.get('source_player'),
                    ctx.get('card'),
                )
                break
            if getattr(self, 'game_over', False):
                break
        return ctx.get('event_value', event_value)

    def _draw_cards_with_v2_hooks(self, player_id: int, count: int, reason: str = ''):
        if not (0 <= player_id < len(self.players)):
            return []
        context = {
            'source_player': player_id,
            'target_player': player_id,
            'vars': {'count': count, 'reason': reason},
            'current_action': {'count': count, 'reason': reason},
        }
        next_count = self._run_v2_event_hooks('before_draw', context, count)
        try:
            next_count = max(0, int(next_count))
        except Exception:
            next_count = max(0, int(count or 0))
        if getattr(self, 'pending_v2_ui', None):
            return []
        drawn = self.players[player_id].draw_cards(next_count)
        context['vars']['drawn'] = len(drawn)
        context['current_action']['drawn'] = len(drawn)
        self._run_v2_event_hooks('after_draw', context, len(drawn))
        return drawn

    def _set_equipment_property_value(self, player_id, current_card, params, value):
        eq = self._resolve_equipment_ref(player_id, params.get('equipment', {'ref': 'current_equipment'}), current_card)
        if eq is None:
            return None
        prop = str(params.get('property', 'turns_equipped'))
        if prop in ('turns_equipped', 'equip_turns', 'equipped_turns'):
            eq.turns_equipped = max(0, int(value))
        elif prop in ('effect_target', 'target_player'):
            target_id = int(value)
            if 0 <= target_id < len(self.players):
                eq.effect_target = target_id
        elif prop in ('corruption_active', 'is_corruption_active'):
            eq.corruption_active = bool(int(value))
        else:
            eq.custom_vars = getattr(eq, 'custom_vars', {}) or {}
            eq.custom_vars[prop] = int(value)
        return eq

    def _get_player_property_value(self, target_id, prop):
        if target_id < 0:
            return sum(self._get_player_property_value(pid, prop) for pid in range(len(self.players)))
        if not (0 <= target_id < len(self.players)):
            return 0
        ps = self.players[target_id]
        prop = str(prop or '')
        if prop == 'health':
            return int(ps.health)
        if prop == 'max_health':
            return int(ps.max_health)
        if prop in ('elixir', 'energy'):
            return int(ps.elixir)
        if prop in ('max_elixir', 'max_energy'):
            return int(ps.max_elixir)
        if prop == 'magic':
            return int(ps.magic)
        if prop == 'max_magic':
            return int(ps.max_magic)
        if prop == 'armor':
            return int(ps.armor)
        if prop in ('poison', 'fire', 'toxic', 'equipment_protection',
                    'attack_blocked', 'attack_only',
                    'nazar_big_hits', 'sluggish', 'overload', 'foresight', 'fracture',
                    'stagnation', 'blind', 'heal_block', 'weakness', 'bleed'):
            if self._is_status_immune(target_id):
                return 0
            return int(getattr(ps, prop, 0))
        if prop == 'dodge':
            if self._is_status_immune(target_id):
                return 0
            return int(getattr(ps, prop, 0))
        if prop in ('invincible', 'untargetable', 'bandage_active', 'sponge_active', 'shovel_active',
                    'negate_next_skill', 'nazar_active'):
            if self._is_status_immune(target_id):
                return 0
            return 1 if bool(getattr(ps, prop, False)) else 0
        if prop == 'skip_turn':
            if self._is_status_immune(target_id):
                return 0
            return int(getattr(ps, 'skip_turn', 0))
        if prop == 'base_max_health':
            return int(getattr(ps, 'base_max_health', 0))
        if prop == 'hand_size':
            return len(ps.hand)
        if prop == 'hand_limit':
            return ps.hand_limit()
        if prop in ('extra_hand_limit_bonus', 'hand_limit_bonus'):
            return int(getattr(ps, 'extra_hand_limit_bonus', 0))
        if prop == 'deck_remaining':
            return len(ps.deck)
        if prop == 'deck_count':
            return len(ps.deck)
        if prop == 'discard_size':
            return len(ps.discard)
        if prop == 'discard_count':
            return len(ps.discard)
        if prop == 'exile_size':
            return len(ps.exile)
        if prop == 'exile_count':
            return len(ps.exile)
        if prop == 'equip_count':
            return len(ps.equipment)
        if prop == 'equipment_count':
            return len(ps.equipment)
        if prop in ('turn_damage_taken', 'turn_damage_dealt', 'last_turn_damage_taken',
                    'last_turn_damage_dealt', 'total_damage_taken', 'total_damage_dealt'):
            return int(getattr(ps, prop, 0))
        return 0

    def _set_player_property_value(self, target_id, prop, value):
        if not (0 <= target_id < len(self.players)):
            return None
        ps = self.players[target_id]
        prop = str(prop or '')
        value = int(value)
        if prop == 'energy':
            prop = 'elixir'
        non_negative = {
            'health', 'max_health', 'elixir', 'energy', 'max_elixir', 'max_energy', 'magic', 'max_magic', 'armor', 'dodge',
            'poison', 'fire', 'toxic', 'equipment_protection',
            'attack_blocked', 'attack_only',
            'nazar_big_hits', 'extra_hand_limit_bonus', 'hand_limit_bonus',
            'sluggish', 'overload', 'foresight', 'fracture', 'stagnation', 'blind', 'heal_block', 'weakness', 'bleed',
            'skip_turn', 'base_max_health',
        }
        bool_props = {
            'invincible', 'untargetable', 'bandage_active', 'sponge_active', 'shovel_active',
            'negate_next_skill', 'nazar_active',
        }
        status_numeric_props = {
            'poison', 'fire', 'toxic', 'equipment_protection',
            'attack_blocked', 'attack_only',
            'nazar_big_hits', 'sluggish', 'overload', 'foresight', 'fracture', 'stagnation',
            'blind', 'heal_block', 'weakness', 'bleed', 'skip_turn',
        }
        if value > 0 and self._is_status_immune(target_id) and (prop in status_numeric_props or prop in bool_props):
            return None
        if prop in non_negative:
            if prop == 'hand_limit_bonus':
                prop = 'extra_hand_limit_bonus'
            if prop == 'max_energy':
                prop = 'max_elixir'
            setattr(ps, prop, max(0, value))
            if prop == 'max_health':
                ps.base_max_health = ps.max_health
                ps.health = min(ps.health, ps.max_health)
            elif prop == 'base_max_health':
                ps.max_health = ps.base_max_health
                ps.health = min(ps.health, ps.max_health)
            elif prop == 'max_elixir':
                ps.elixir = min(ps.elixir, ps.max_elixir)
            elif prop == 'max_magic':
                ps.magic = min(ps.magic, ps.max_magic)
        elif prop == 'hand_limit':
            golden = sum(
                1
                for e in ps.equipment
                if e.def_id == 'GoldenLeaf' and getattr(e, 'effect_target', target_id) == target_id
            )
            ps.extra_hand_limit_bonus = max(0, value - HAND_LIMIT - golden)
        elif prop in bool_props:
            setattr(ps, prop, bool(value))
        else:
            return None
        return ps

    def _match_card_selector(self, player_id, cards, selector, card=None):
        if not isinstance(selector, dict):
            return list(cards)
        st = selector.get('selector')
        if st == 'by_id':
            cid = selector.get('id')
            return [c for c in cards if c.def_id == cid]
        if st == 'by_type':
            ctype = selector.get('card_type')
            return [c for c in cards if c.card_type == ctype]
        if st == 'by_tag':
            tag = selector.get('tag')
            out = []
            for c in cards:
                inst_flags = getattr(c, 'instance_flags', set())
                base_flags = set(getattr(c.card_def, 'flags', set()) or [])
                if tag in inst_flags or tag in base_flags:
                    out.append(c)
            return out
        if st == 'all':
            return list(cards)
        if st == 'random':
            pool = list(cards)
            if not pool:
                return []
            n = max(1, int(self._eval_expr(player_id, selector.get('count', 1), card)))
            random.shuffle(pool)
            return pool[:min(n, len(pool))]
        return list(cards)

    def __init__(self):
        self.players = [PlayerState(0), PlayerState(1)]
        self.current_player: int = 0
        self.first_player: int = 0
        self.round_num: int = 0
        self.phase: str = 'waiting'
        self.log: List[str] = []
        self.draft_pool: List[CardInstance] = []
        self.allowed_card_ids: Optional[Set[str]] = None
        self.draft_options: List[List[CardInstance]] = [[], []]
        self.draft_picks: List[List[str]] = [[], []]
        self.draft_rerolls: List[int] = [DRAFT_REROLLS, DRAFT_REROLLS]
        self.draft_round: int = 0
        self.draft_type_order: List[str] = []
        self.pending_response: Optional[dict] = None
        self.pending_choice: Optional[dict] = None
        self._pending_foresight: Optional[dict] = None
        self.pending_v2_ui: Optional[dict] = None
        self.v2_ui_components: Dict[str, dict] = {}
        self.v2_loadout = None
        self.v2_tag_defs: Dict[str, dict] = {}
        self.v2_status_defs: Dict[str, dict] = {}
        self.v2_opening_event_defs: Dict[str, dict] = {}
        self.v2_event_hooks: List[dict] = []
        self.halve_next_attack: bool = False
        self.game_over: bool = False
        self.winner: int = -1
        self._game_over_defer_depth: int = 0
        self.negated_card: bool = False
        self._yggdrasil_check: bool = True
        self._antennae_reveal: List[Optional[list]] = [None, None]

        self.opening_event_options: List[List[dict]] = [[], []]
        self.opening_event_picks: List[Optional[int]] = [None, None]
        self.opening_event_sub_choices: List[Optional[dict]] = [None, None]
        self.opening_event_magic_options: List[List[List[str]]] = [[[], [], []], [[], [], []]]
        # Per-player ready state: True when draft done AND sub-choice done (if any)
        self.player_ready: List[bool] = [False, False]
        self.player_draft_started: List[bool] = [False, False]
        self.player_names: List[str] = ['玩家1', '玩家2']
        self.debug_selector_log: bool = False
        self._last_damage_value: List[int] = [0, 0]
        self._last_positive_damage_hits: List[int] = [0, 0]
        self._incoming_damage_hint: List[int] = [0, 0]
        self.custom_vars: Dict[str, int] = {}
        self.team_custom_vars: Dict[str, Dict[str, int]] = {}
        self._last_created_card_instance_id: Optional[int] = None
        self.timed_effects: List[dict] = []
        self._init_mod_variables()
        self._bind_player_callbacks()

    def pn(self, pid: int) -> str:
        return self.player_names[pid] if 0 <= pid < len(self.player_names) else f'玩家{pid+1}'

    def log_msg(self, msg: str):
        text = self._normalize_log_text(str(msg))
        if not text:
            return
        if self._merge_log_text(text):
            return
        if self._move_use_log_before_response_detail(text):
            return
        self.log.append(text)
        if self._is_log_compaction_boundary(text):
            self._mark_log_visible()
            return
        self._compact_recent_repeated_action_block()

    def _is_log_compaction_boundary(self, text: str) -> bool:
        if not text:
            return False
        return bool(
            re.fullmatch(r'=+\s*第\d+回合\s*=+', text)
            or '游戏开始' in text
            or '配装' in text and ('选择' in text or '公开' in text)
            or '开始选牌' in text
            or '抽牌阶段' in text
            or '事件选择' in text
            or '获胜' in text
            or '平局' in text
        )

    def _clear_hand_reveal_for_player(self, player_id: int):
        if hasattr(self, '_antennae_reveal') and 0 <= player_id < len(self._antennae_reveal):
            self._antennae_reveal[player_id] = None
        reveal_targets = getattr(self, '_antennae_reveal_targets', None)
        if reveal_targets is not None and 0 <= player_id < len(reveal_targets):
            reveal_targets[player_id] = None

    def _mark_log_visible(self):
        self._log_compaction_floor = len(self.log)

    def _can_merge_last_log(self) -> bool:
        return bool(self.log) and len(self.log) > int(getattr(self, '_log_compaction_floor', 0) or 0)

    def _is_response_detail_log(self, text: str) -> bool:
        clean = self._strip_card_log_markers(text)
        return bool(
            re.fullmatch(r'.+使用泡泡(?:进行反制！?|，.*)', clean)
            or re.fullmatch(r'.+精准牌被闪避反制.*', clean)
            or clean == '精准牌被闪避反制，伤害减半！'
        )

    def _move_use_log_before_response_detail(self, text: str) -> bool:
        if not re.fullmatch(r'.+使用了.+', text) or not self._can_merge_last_log():
            return False
        floor = int(getattr(self, '_log_compaction_floor', 0) or 0)
        insert_at = len(self.log)
        while insert_at > floor and self._is_response_detail_log(self.log[insert_at - 1]):
            insert_at -= 1
        if insert_at == len(self.log):
            return False
        self.log.insert(insert_at, text)
        return True

    def _normalize_log_text(self, text: str) -> str:
        text = text.strip()
        if not text:
            return ''
        text = self._normalize_damage_log_text(text)
        m = re.fullmatch(r'(.+)触发(.+)！(.+)', text)
        if m:
            return f'{m.group(1)}触发{m.group(2)}，{m.group(3)}'
        m = re.fullmatch(r'(.+)的([^：]+)效果：\+(\d+)([HME])', text)
        if m:
            return f'{m.group(2)}：{m.group(1)} +{m.group(3)}{m.group(4)}'
        m = re.fullmatch(r'(.+)效果：(.+)\+(\d+)([HME])', text)
        if m:
            return f'{m.group(1)}：{m.group(2)} +{m.group(3)}{m.group(4)}'
        m = re.fullmatch(r'(.+)的([^：]+)效果：多抽(\d+)张牌', text)
        if m:
            return f'{m.group(2)}：{m.group(1)} 多抽{m.group(3)}张'
        m = re.fullmatch(r'(.+)效果：(.+)多抽(\d+)张牌', text)
        if m:
            return f'{m.group(1)}：{m.group(2)} 多抽{m.group(3)}张'
        return text

    def _merge_log_text(self, text: str) -> bool:
        if not self._can_merge_last_log():
            return False
        last = self.log[-1]
        last_clean = self._strip_card_log_markers(last)

        if self._merge_repeated_use_before_damage(text):
            return True
        if self._merge_post_use_detail(text, last):
            return True

        m = re.fullmatch(r'(.+)的电池效果：对(.+)造成(\d+)(?:D|电伤|点电击魔法伤害)', text)
        if m:
            owner, target, damage = m.group(1), m.group(2), int(m.group(3))
            taken = re.fullmatch(rf'{re.escape(target)}受到(\d+)点电池(?:电击)?伤害（H=(.+)）', last)
            if taken:
                self.log[-1] = f'{owner}的电池反伤{target}：{damage}电伤（H={taken.group(2)}）'
                return True

        m = re.fullmatch(r'(.+)闪避了攻击！?', text)
        if m:
            responder = m.group(1)
            if re.fullmatch(rf'{re.escape(responder)}使用泡泡进行反制！?', last_clean):
                self.log[-1] = f'{responder}使用泡泡，闪避了攻击'
                return True

        if text == '精准牌被闪避反制，伤害减半！':
            m = re.fullmatch(r'(.+)使用泡泡进行反制！?', last_clean)
            if m:
                self.log[-1] = f'{m.group(1)}使用泡泡，精准攻击伤害减半'
                return True
        m = re.fullmatch(r'(.+)的精准牌被闪避反制，伤害减半！?', text)
        if m:
            bubble = re.fullmatch(r'(.+)使用泡泡进行反制！?', last_clean)
            if bubble:
                self.log[-1] = f'{bubble.group(1)}使用泡泡，{m.group(1)}的精准攻击伤害减半'
                return True

        m = re.fullmatch(r'(.+)装备了(.+)', text)
        if m:
            owner, card_name = m.group(1), m.group(2)
            simple_use = re.fullmatch(r'(.+)使用了(.+)', last)
            if simple_use and self._clean_log_card_name(simple_use.group(2)) == card_name:
                actor = simple_use.group(1)
                self.log[-1] = (
                    f'{actor}使用并装备了{card_name}'
                    if actor == owner
                    else f'{actor}使用并给{owner}装备了{card_name}'
                )
                return True
            combined_use = re.fullmatch(rf'(.+)使用{re.escape(card_name)}，(.+)', last)
            if combined_use:
                actor, detail = combined_use.group(1), combined_use.group(2)
                self.log[-1] = (
                    f'{actor}使用并装备了{card_name}，{detail}'
                    if actor == owner
                    else f'{actor}使用并给{owner}装备了{card_name}，{detail}'
                )
                return True
            combined_equipped = re.fullmatch(rf'(.+)使用并装备了{re.escape(card_name)}，(.+)', last)
            if combined_equipped and combined_equipped.group(1) == owner:
                detail = combined_equipped.group(2)
                self.log[-1] = f'{owner}使用并装备了{card_name}，{detail}'
                return True
            marker = f'使用{card_name}，'
            if last.startswith(f'{owner}{marker}'):
                detail = last[len(owner + marker):]
                self.log[-1] = f'{owner}使用并装备了{card_name}，{detail}'
                return True

        if self._merge_chinese_use_equipment(text, last):
            return True
        if self._merge_chinese_use_destination(text, last):
            return True
        if self._merge_simple_use_detail(text, last):
            return True
        if self._merge_legacy_use_damage_log(text, last):
            return True
        if self._merge_damage_taken_log(text, last):
            return True
        return self._merge_counted_log(text, last)

    def _parse_plain_use_count_log(self, text: str):
        m = re.fullmatch(r'(.+)使用了?([^，]+?)(?:\s*×(\d+))?', text)
        if not m:
            return None
        return {
            'actor': m.group(1),
            'card': self._clean_log_card_name(m.group(2)),
            'card_raw': m.group(2),
            'count': int(m.group(3) or 1),
        }

    def _format_plain_use_count_log(self, actor: str, card: str, count: int) -> str:
        return f'{actor}使用了{card}' + (f'×{count}' if int(count or 1) > 1 else '')

    def _strip_card_log_markers(self, text: str) -> str:
        return re.sub(r'\u2063CARD:[A-Za-z0-9_-]+\u2063', '', str(text or ''))

    def _clean_log_card_name(self, text: str) -> str:
        return self._strip_card_log_markers(text).strip()

    def _parse_post_use_detail_count_log(self, text: str):
        patterns = [
            r'(.+)的唯一牌(.+?)多余副本被放逐(?: ×(\d+))?',
            r'(.+)的(.+?)(因回转回到手中|因虚无被放逐|被放逐|移入弃牌堆)(?: ×(\d+))?',
            r'(.+?)(被放逐|移入弃牌堆)(?: ×(\d+))?',
            r'(.+)放逐了(.+?)(?: ×(\d+))?',
        ]
        m = re.fullmatch(patterns[0], text)
        if m:
            return {
                'actor': m.group(1),
                'card': m.group(2),
                'action': '唯一牌多余副本被放逐',
                'count': int(m.group(3) or 1),
            }
        m = re.fullmatch(patterns[1], text)
        if m:
            return {
                'actor': m.group(1),
                'card': m.group(2),
                'action': m.group(3),
                'count': int(m.group(4) or 1),
            }
        m = re.fullmatch(patterns[2], text)
        if m:
            return {
                'actor': '',
                'card': m.group(1),
                'action': m.group(2),
                'count': int(m.group(3) or 1),
            }
        m = re.fullmatch(patterns[3], text)
        if m:
            return {
                'actor': m.group(1),
                'card': m.group(2),
                'action': '放逐了',
                'count': int(m.group(3) or 1),
            }
        return None

    def _format_post_use_detail_count_log(self, detail) -> str:
        actor = detail.get('actor') or ''
        card = detail.get('card') or ''
        action = detail.get('action') or ''
        count = int(detail.get('count') or 1)
        if action == '唯一牌多余副本被放逐':
            text = f'{actor}的唯一牌{card}多余副本被放逐'
            return text + (f' ×{count}' if count > 1 else '')
        if action == '放逐了':
            text = f'{actor}放逐了{card}'
            return text + (f' ×{count}' if count > 1 else '')
        prefix = f'{actor}的' if actor else ''
        return f'{prefix}{card}{action}' + (f' ×{count}' if count > 1 else '')

    def _merge_post_use_detail(self, text: str, last: str) -> bool:
        current = self._parse_post_use_detail_count_log(text)
        previous = self._parse_post_use_detail_count_log(last)
        if not current or not previous:
            return False
        same_actor = (not current['actor'] or not previous['actor'] or current['actor'] == previous['actor'])
        if not same_actor or current['card'] != previous['card'] or current['action'] != previous['action']:
            return False
        previous['actor'] = previous['actor'] or current['actor']
        previous['count'] += current['count']
        self.log[-1] = self._format_post_use_detail_count_log(previous)
        return True

    def _find_previous_use_index_before_trailing_details(self, actor: str, card: str):
        idx = len(self.log) - 1
        while idx >= 0:
            detail = self._parse_post_use_detail_count_log(self.log[idx])
            if detail and detail['card'] == card and (not detail['actor'] or detail['actor'] == actor):
                idx -= 1
                continue
            if self._parse_damage_taken_log(self.log[idx]):
                idx -= 1
                continue
            break
        if idx < 0:
            return None
        previous_use = self._parse_plain_use_count_log(self.log[idx])
        if previous_use and previous_use['actor'] == actor and previous_use['card'] == card:
            return idx
        return None

    def _merge_repeated_use_before_damage(self, text: str) -> bool:
        current = self._parse_plain_use_count_log(text)
        if not current:
            return False
        if len(self.log) >= 1:
            last_use = self._parse_plain_use_count_log(self.log[-1])
            if last_use and last_use['actor'] == current['actor'] and last_use['card'] == current['card']:
                count = last_use['count'] + current['count']
                self.log[-1] = f"{current['actor']}使用了{last_use.get('card_raw') or current.get('card_raw') or current['card']}×{count}"
                return True
        return False

    def _normalize_damage_log_text(self, text: str) -> str:
        parsed = self._parse_damage_taken_log(text)
        if not parsed:
            return text
        return (
            f"{parsed['prefix']}{parsed['target']}受到"
            f"{self._format_damage_units(parsed['units'])}"
            f"（H={'→'.join(parsed['hp_chain'])}）"
        )

    def _parse_damage_taken_log(self, text: str):
        m = re.fullmatch(r'(.+)受到(\d+(?:\+\d+)*)点伤害[（(]H=([^）)]+)[）)]', text)
        if m:
            before, raw_damage, hp_text = m.group(1), m.group(2), m.group(3)
            parts = [int(p) for p in raw_damage.split('+')]
            unit_expr = self._format_damage_parts(parts)
        else:
            m = re.fullmatch(r'(.+)受到(\d+)D(?:×(\d+))?(?:×(\d+))?[（(]H=([^）)]+)[）)]', text)
            if m:
                before = m.group(1)
                raw_damage = m.group(2)
                inner_times = max(1, int(m.group(3) or 1))
                outer_times = max(1, int(m.group(4) or 1))
                hp_text = m.group(5)
                parts = [int(raw_damage)] * inner_times
                unit_expr = f'{raw_damage}D' + (f'×{inner_times}' if inner_times > 1 else '')
                if outer_times > 1:
                    return self._build_damage_parse_result(before, hp_text, [
                        {'expr': unit_expr, 'parts': parts[:]} for _ in range(outer_times)
                    ])
            else:
                m = re.fullmatch(r'(.+)受到[（(](\d+(?:\+\d+)*)[）)]D[（(]H=([^）)]+)[）)]', text)
                if not m:
                    return None
                before, raw_damage, hp_text = m.group(1), m.group(2), m.group(3)
                parts = [int(p) for p in raw_damage.split('+')]
                unit_expr = self._format_damage_parts(parts)
        return self._build_damage_parse_result(before, hp_text, [{'expr': unit_expr, 'parts': parts}])

    def _build_damage_parse_result(self, before: str, hp_text: str, units):
        comma_idx = before.rfind('，')
        prefix = before[:comma_idx + 1] if comma_idx >= 0 else ''
        target = before[comma_idx + 1:] if comma_idx >= 0 else before
        hp_chain = [part for part in hp_text.split('→') if part != '']
        if len(hp_chain) >= 2:
            start_hp, end_hp = hp_chain[0], hp_chain[-1]
        else:
            end_hp = hp_text
            try:
                total = sum(sum(int(p) for p in unit.get('parts', [])) for unit in units)
                start_hp = str(int(end_hp) + total)
                hp_chain = [start_hp, end_hp]
            except Exception:
                start_hp = ''
                hp_chain = [end_hp] if end_hp else []
        return {
            'prefix': prefix,
            'target': target,
            'parts': [p for unit in units for p in unit.get('parts', [])],
            'units': units,
            'start_hp': start_hp,
            'end_hp': end_hp,
            'hp_chain': hp_chain,
        }

    def _format_damage_parts(self, parts) -> str:
        values = [int(p) for p in (parts or [])]
        if not values:
            return '0D'
        if len(values) == 1:
            return f'{values[0]}D'
        if all(v == values[0] for v in values):
            return f'{values[0]}D×{len(values)}'
        return f"({'+'.join(str(v) for v in values)})D"

    def _format_damage_units(self, units) -> str:
        clean_units = [
            {
                'expr': str(unit.get('expr') or self._format_damage_parts(unit.get('parts', []))),
                'parts': [int(p) for p in unit.get('parts', [])],
            }
            for unit in (units or [])
        ]
        if not clean_units:
            return '0D'
        expressions = [unit['expr'] for unit in clean_units]
        if len(set(expressions)) == 1:
            expr = expressions[0]
            return expr if len(expressions) == 1 else f'{expr}×{len(expressions)}'
        flat_parts = [p for unit in clean_units for p in unit['parts']]
        return self._format_damage_parts(flat_parts)

    def _parse_chinese_use_log(self, text: str):
        m = re.fullmatch(r'(.+)使用(?!并)(?:了)?([^，！!:：]+)(?:，(.+))?', text)
        if not m:
            return None
        return {
            'actor': m.group(1),
            'card': self._clean_log_card_name(m.group(2)),
            'card_raw': m.group(2),
            'detail': m.group(3) or '',
        }

    def _merge_chinese_use_equipment(self, text: str, last: str) -> bool:
        m = re.fullmatch(r'(.+)装备了(.+)', text)
        if not m:
            return False
        owner, card_name = m.group(1), m.group(2)
        used = self._parse_chinese_use_log(last)
        if not used or used['card'] != card_name:
            return False
        actor = used['actor']
        card_raw = used.get('card_raw') or card_name
        detail = f'，{used["detail"]}' if used['detail'] else ''
        if actor == owner:
            self.log[-1] = f'{actor}使用并装备了{card_raw}{detail}'
        else:
            self.log[-1] = f'{actor}使用并给{owner}装备了{card_raw}{detail}'
        return True

    def _merge_chinese_use_destination(self, text: str, last: str) -> bool:
        used = self._parse_chinese_use_log(last)
        if not used:
            return False
        actor = used['actor']
        card_name = used['card']
        escaped_actor = re.escape(actor)
        escaped_card = re.escape(card_name)
        destination = None
        if re.fullmatch(rf'{escaped_actor}的{escaped_card}被放逐', text) or re.fullmatch(rf'{escaped_card}被放逐', text):
            destination = f'{card_name}被放逐'
        elif re.fullmatch(rf'{escaped_actor}的{escaped_card}移入弃牌堆', text) or re.fullmatch(rf'{escaped_card}移入弃牌堆', text):
            destination = f'{card_name}移入弃牌堆'
        elif re.fullmatch(rf'{escaped_actor}的{escaped_card}被魔法泡泡反制，失效！?', text):
            destination = f'{card_name}被魔法泡泡反制，失效'
        if not destination:
            return False
        self.log[-1] = f'{last}，{destination}'
        return True

    def _merge_damage_taken_log(self, text: str, last: str) -> bool:
        current = self._parse_damage_taken_log(text)
        previous = self._parse_damage_taken_log(last)
        if current and not previous and self._parse_post_use_detail_count_log(last) and len(self.log) >= 2:
            previous = self._parse_damage_taken_log(self.log[-2])
            if previous and self._merge_damage_taken_log_at_index(-2, previous, current):
                return True
        if not current or not previous:
            return False
        return self._merge_damage_taken_log_at_index(-1, previous, current)

    def _merge_damage_taken_log_at_index(self, index: int, previous: dict, current: dict) -> bool:
        if current['target'] != previous['target']:
            return False
        start_hp = previous['start_hp']
        if not start_hp:
            return False
        hp_chain = previous.get('hp_chain') or [previous['start_hp'], previous['end_hp']]
        current_chain = current.get('hp_chain') or [current['start_hp'], current['end_hp']]
        if hp_chain and current_chain and hp_chain[-1] == current_chain[0]:
            hp_chain = hp_chain + current_chain[1:]
        else:
            hp_chain = hp_chain + [current['end_hp']]
        units = (previous.get('units') or [{'expr': self._format_damage_parts(previous['parts']), 'parts': previous['parts']}]) + (
            current.get('units') or [{'expr': self._format_damage_parts(current['parts']), 'parts': current['parts']}]
        )
        self.log[index] = (
            f"{previous['prefix']}{previous['target']}受到"
            f"{self._format_damage_units(units)}"
            f"（H={'→'.join(hp_chain)}）"
        )
        return True

    def _merge_legacy_use_damage_log(self, text: str, last: str) -> bool:
        if not self._parse_damage_taken_log(text):
            return False
        m = re.fullmatch(r'(.+)使用(.+)！(?:对.+)?造成.+伤害', last)
        if not m:
            return False
        self.log[-1] = f'{m.group(1)}使用{m.group(2)}，{text}'
        return True

    def _merge_simple_use_detail(self, text: str, last: str) -> bool:
        m = re.fullmatch(r'(.+)使用了(.+)', last)
        if not m:
            return False
        actor, card_name = m.group(1), m.group(2)
        detail = ''
        if text.startswith(actor):
            detail = text[len(actor):]
        allowed_starts = (
            '对', '回复', '获得', '抽', '+', '聚变', '裂变', '血量',
            '无法', '仅可', '消耗', '每回合', '丢弃', '窥探',
            '查看', '摧毁', '从',
        )
        if not detail.startswith(allowed_starts):
            if self._parse_damage_taken_log(text):
                return False
            result_patterns = (
                r'.+回复\d+[HE]',
                r'.+获得\d+(E|M|护甲|闪避)',
                r'.+\+\d+(中毒|灼烧|淬毒|易伤)',
                r'.+抽\d+张牌',
                r'.+消耗\d+[EM]',
                r'.+每回合.+[+-]\d+',
            )
            if not any(re.fullmatch(pattern, text) for pattern in result_patterns):
                return False
            detail = text
        self.log[-1] = f'{actor}使用{card_name}，{detail}'
        return True

    def _merge_counted_log(self, text: str, last: str) -> bool:
        counted_patterns = [
            (r'^(.+)抽(\d+)张牌$', lambda g, total: f'{g[0]}抽{total}张牌'),
            (r'^(.+)抽(\d+)张至手牌满$', lambda g, total: f'{g[0]}抽{total}张至手牌满'),
            (r'^(.+)补充(\d+)张(.+)牌$', lambda g, total: f'{g[0]}补充{total}张{g[2]}牌'),
            (r'^(.+)获得(\d+)(E|M|护甲|闪避)$', lambda g, total: f'{g[0]}获得{total}{g[2]}'),
            (r'^(.+)回复(\d+)(E|H)$', lambda g, total: f'{g[0]}回复{total}{g[2]}'),
            (r'^(.+)\+(\d+)(中毒|灼烧|淬毒|易伤)$', lambda g, total: f'{g[0]}+{total}{g[2]}'),
        ]
        for pattern, formatter in counted_patterns:
            current = re.fullmatch(pattern, text)
            previous = re.fullmatch(pattern, last)
            if not current or not previous:
                continue
            current_groups = current.groups()
            previous_groups = previous.groups()
            if current_groups[0] != previous_groups[0] or current_groups[2:] != previous_groups[2:]:
                continue
            total = int(previous_groups[1]) + int(current_groups[1])
            self.log[-1] = formatter(current_groups, total)
            return True
        return False

    def _parse_use_for_action_block(self, text: str):
        m = re.fullmatch(r'(.+)使用了([^，]+?)(?:\s*×(\d+))?', text)
        if not m:
            return None
        return {'actor': m.group(1), 'card': self._clean_log_card_name(m.group(2)), 'count': int(m.group(3) or 1)}

    def _parse_gain_for_action_block(self, text: str):
        m = re.fullmatch(r'(.+)获得(\d+)(E|M|护甲|闪避)(?: ×(\d+))?', text)
        if not m:
            return None
        return {
            'target': m.group(1),
            'amount': int(m.group(2)),
            'kind': m.group(3),
            'count': int(m.group(4) or 1),
        }

    def _format_use_action_block(self, uses) -> str:
        actor = uses[0]['actor']
        parts = []
        for use in uses:
            card = use['card']
            count = int(use.get('count') or 1)
            parts.append(f'{card}×{count}' if count > 1 else card)
        return f"{actor}使用了{'、'.join(parts)}"

    def _format_gain_action_block(self, gain) -> str:
        count = int(gain.get('count') or 1)
        text = f"{gain['target']}获得{gain['amount']}{gain.get('resource') or gain.get('kind')}"
        return text + (f' ×{count}' if count > 1 else '')

    def _parse_repeatable_effect_log(self, text: str):
        if not text:
            return None
        if self._parse_use_for_action_block(text) or self._parse_damage_taken_log(text):
            return None
        if self._parse_post_use_detail_count_log(text):
            return None
        m = re.fullmatch(r'(.+?)(?:\s*×(\d+))?', text)
        if not m:
            return None
        base = m.group(1).strip()
        if not base:
            return None
        if re.fullmatch(r'.+使用了?.+', base):
            return None
        return {'base': base, 'count': int(m.group(2) or 1)}

    def _format_repeatable_effect_log(self, effect) -> str:
        count = int(effect.get('count') or 1)
        text = str(effect.get('base') or '')
        return text + (f' ×{count}' if count > 1 else '')

    def _parse_log_block_item(self, text: str):
        use = self._parse_use_for_action_block(text)
        if use:
            return {'kind': 'use', **use}
        damage = self._parse_damage_taken_log(text)
        if damage:
            return {'kind': 'damage', **damage}
        gain = self._parse_gain_for_action_block(text)
        if gain:
            return {
                'kind': 'gain',
                'target': gain.get('target'),
                'amount': gain.get('amount'),
                'resource': gain.get('kind'),
                'count': gain.get('count', 1),
            }
        post = self._parse_post_use_detail_count_log(text)
        if post:
            return {'kind': 'post', **post}
        repeat = self._parse_repeatable_effect_log(text)
        if repeat:
            return {'kind': 'repeat', **repeat}
        return None

    def _are_log_block_items_compatible(self, previous: dict, current: dict) -> bool:
        if not previous or not current or previous.get('kind') != current.get('kind'):
            return False
        kind = previous.get('kind')
        if kind == 'use':
            return previous.get('actor') == current.get('actor') and previous.get('card') == current.get('card')
        if kind == 'damage':
            return previous.get('prefix') == current.get('prefix') and previous.get('target') == current.get('target')
        if kind == 'gain':
            return (
                previous.get('target') == current.get('target')
                and previous.get('amount') == current.get('amount')
                and previous.get('resource') == current.get('resource')
            )
        if kind == 'post':
            same_actor = (
                not previous.get('actor')
                or not current.get('actor')
                or previous.get('actor') == current.get('actor')
            )
            return same_actor and previous.get('card') == current.get('card') and previous.get('action') == current.get('action')
        if kind == 'repeat':
            return previous.get('base') == current.get('base')
        return False

    def _merge_log_block_items(self, previous: dict, current: dict) -> dict:
        kind = previous.get('kind')
        merged = dict(previous)
        if kind in ('use', 'gain', 'post', 'repeat'):
            merged['count'] = int(previous.get('count') or 1) + int(current.get('count') or 1)
            if kind == 'post' and not merged.get('actor'):
                merged['actor'] = current.get('actor') or ''
            return merged
        if kind == 'damage':
            hp_chain = list(previous.get('hp_chain') or [previous.get('start_hp'), previous.get('end_hp')])
            hp_chain = [part for part in hp_chain if part not in (None, '')]
            current_chain = list(current.get('hp_chain') or [current.get('start_hp'), current.get('end_hp')])
            current_chain = [part for part in current_chain if part not in (None, '')]
            if not hp_chain:
                hp_chain = current_chain
            elif current_chain:
                hp_chain.extend(current_chain[1:] if hp_chain[-1] == current_chain[0] else current_chain)
            units = (previous.get('units') or [{'expr': self._format_damage_parts(previous.get('parts', [])), 'parts': previous.get('parts', [])}])
            units += (current.get('units') or [{'expr': self._format_damage_parts(current.get('parts', [])), 'parts': current.get('parts', [])}])
            merged['units'] = units
            merged['parts'] = [p for unit in units for p in unit.get('parts', [])]
            merged['hp_chain'] = hp_chain
            if hp_chain:
                merged['start_hp'] = hp_chain[0]
                merged['end_hp'] = hp_chain[-1]
            return merged
        return merged

    def _format_log_block_item(self, item: dict) -> str:
        kind = item.get('kind')
        if kind == 'use':
            return self._format_plain_use_count_log(item.get('actor') or '', item.get('card') or '', int(item.get('count') or 1))
        if kind == 'damage':
            return (
                f"{item.get('prefix') or ''}{item.get('target') or ''}受到"
                f"{self._format_damage_units(item.get('units') or [])}"
                f"（H={'→'.join(item.get('hp_chain') or [])}）"
            )
        if kind == 'gain':
            return self._format_gain_action_block(item)
        if kind == 'post':
            return self._format_post_use_detail_count_log(item)
        if kind == 'repeat':
            return self._format_repeatable_effect_log(item)
        return ''

    def _compact_recent_repeated_generic_block(self) -> bool:
        if len(self.log) < 4:
            return False
        floor = int(getattr(self, '_log_compaction_floor', 0) or 0)
        end = len(self.log)
        use_indices = [
            idx for idx in range(floor, end)
            if self._parse_use_for_action_block(self.log[idx])
        ]
        if len(use_indices) < 2:
            return False
        last_start = use_indices[-1]
        prev_start = use_indices[-2]
        block_len = end - last_start
        if block_len < 2 or prev_start + block_len != last_start:
            return False
        prev_items = [self._parse_log_block_item(self.log[idx]) for idx in range(prev_start, last_start)]
        curr_items = [self._parse_log_block_item(self.log[idx]) for idx in range(last_start, end)]
        if any(item is None for item in prev_items + curr_items):
            return False
        for prev_item, curr_item in zip(prev_items, curr_items):
            if not self._are_log_block_items_compatible(prev_item, curr_item):
                return False
        merged_items = [
            self._merge_log_block_items(prev_item, curr_item)
            for prev_item, curr_item in zip(prev_items, curr_items)
        ]
        formatted = [self._format_log_block_item(item) for item in merged_items]
        if not all(formatted):
            return False
        self.log[prev_start:end] = formatted
        return True

    def _compact_recent_repeated_use_effect_block(self) -> bool:
        """Compact repeated two-line blocks: use card + identical non-damage effect line."""
        if len(self.log) < 4:
            return False
        floor = int(getattr(self, '_log_compaction_floor', 0) or 0)
        end = len(self.log)
        pairs = []
        idx = end - 2
        while idx >= floor and len(pairs) < 12:
            use = self._parse_use_for_action_block(self.log[idx])
            effect = self._parse_repeatable_effect_log(self.log[idx + 1]) if idx + 1 < end else None
            if not use or not effect:
                break
            pairs.append((idx, use, effect))
            idx -= 2
        if len(pairs) < 2:
            return False
        pairs.reverse()
        actor = pairs[0][1]['actor']
        card = pairs[0][1]['card']
        effect_base = pairs[0][2]['base']
        compatible = []
        for pair in pairs:
            _, use, effect = pair
            if use['actor'] != actor or use['card'] != card or effect['base'] != effect_base:
                break
            compatible.append(pair)
        if len(compatible) < 2:
            return False
        start = compatible[0][0]
        if compatible[-1][0] + 2 != end:
            return False
        total_use = sum(int(use.get('count') or 1) for _, use, _ in compatible)
        total_effect = sum(int(effect.get('count') or 1) for _, _, effect in compatible)
        self.log[start:end] = [
            f'{actor}使用了{card}' + (f' ×{total_use}' if total_use > 1 else ''),
            self._format_repeatable_effect_log({'base': effect_base, 'count': total_effect}),
        ]
        return True

    def _compact_recent_repeated_effect_pair_block(self) -> bool:
        """Compact repeated effect pairs after one card use.

        Magic Coral, for example, emits damage + identical skip-turn text for
        each petal.  There is only one use line, so the normal repeated-use
        compactor cannot see it.  This keeps the timeline intact while merging
        the repeated tail into: damage×N / effect ×N.
        """
        if len(self.log) < 4:
            return False
        floor = int(getattr(self, '_log_compaction_floor', 0) or 0)
        end = len(self.log)
        if end - 4 < floor:
            return False
        prev_first = self._parse_log_block_item(self.log[end - 4])
        prev_second = self._parse_log_block_item(self.log[end - 3])
        curr_first = self._parse_log_block_item(self.log[end - 2])
        curr_second = self._parse_log_block_item(self.log[end - 1])
        if not all([prev_first, prev_second, curr_first, curr_second]):
            return False
        if prev_first.get('kind') == 'use' or curr_first.get('kind') == 'use':
            return False
        if not self._are_log_block_items_compatible(prev_first, curr_first):
            return False
        if not self._are_log_block_items_compatible(prev_second, curr_second):
            return False
        merged_first = self._merge_log_block_items(prev_first, curr_first)
        merged_second = self._merge_log_block_items(prev_second, curr_second)
        formatted = [
            self._format_log_block_item(merged_first),
            self._format_log_block_item(merged_second),
        ]
        if not all(formatted):
            return False
        self.log[end - 4:end] = formatted
        return True

    def _compact_recent_repeated_action_block(self):
        """Compact repeated card-use blocks even when identical side-effect lines sit between them.

        Example:
          A使用了骨头 / B受到12D / B获得1M repeated
        becomes:
          A使用了骨头×2 / B受到12D×2 / B获得1M ×2
        """
        if self._compact_recent_repeated_generic_block():
            return
        if self._compact_recent_repeated_use_effect_block():
            return
        if self._compact_recent_repeated_effect_pair_block():
            return
        if len(self.log) < 6:
            return
        floor = int(getattr(self, '_log_compaction_floor', 0) or 0)
        end = len(self.log)
        triples = []
        idx = end - 3
        while idx >= floor and len(triples) < 8:
            use = self._parse_use_for_action_block(self.log[idx])
            damage = self._parse_damage_taken_log(self.log[idx + 1]) if idx + 1 < end else None
            gain = self._parse_gain_for_action_block(self.log[idx + 2]) if idx + 2 < end else None
            if not use or not damage or not gain:
                break
            triples.append((idx, use, damage, gain))
            idx -= 3
        if len(triples) < 2:
            return
        triples.reverse()
        actor = triples[0][1]['actor']
        damage_target = triples[0][2]['target']
        damage_prefix = triples[0][2]['prefix']
        gain_target = triples[0][3]['target']
        gain_amount = triples[0][3]['amount']
        gain_kind = triples[0][3]['kind']
        compatible = []
        for triple in triples:
            _, use, damage, gain = triple
            if use['actor'] != actor:
                break
            if damage['target'] != damage_target or damage['prefix'] != damage_prefix:
                break
            if gain['target'] != gain_target or gain['amount'] != gain_amount or gain['kind'] != gain_kind:
                break
            hp_chain = damage.get('hp_chain') or []
            if compatible:
                prev_hp = compatible[-1][2].get('hp_chain') or []
                if prev_hp and hp_chain and prev_hp[-1] != hp_chain[0]:
                    break
            compatible.append(triple)
        if len(compatible) < 2:
            return
        start = compatible[0][0]
        if compatible[-1][0] + 3 != end:
            return
        uses = []
        for _, use, _, _ in compatible:
            if uses and uses[-1]['card'] == use['card']:
                uses[-1]['count'] += int(use.get('count') or 1)
            else:
                uses.append(dict(use))
        units = []
        hp_chain = []
        for _, _, damage, _ in compatible:
            units.extend(damage.get('units') or [{'expr': self._format_damage_parts(damage['parts']), 'parts': damage['parts']}])
            chain = damage.get('hp_chain') or [damage.get('start_hp'), damage.get('end_hp')]
            chain = [part for part in chain if part not in (None, '')]
            if not hp_chain:
                hp_chain = chain
            elif chain:
                hp_chain.extend(chain[1:] if hp_chain[-1] == chain[0] else chain)
        merged_gain = dict(compatible[0][3])
        merged_gain['count'] = sum(int(gain.get('count') or 1) for _, _, _, gain in compatible)
        damage_line = (
            f"{damage_prefix}{damage_target}受到"
            f"{self._format_damage_units(units)}"
            f"（H={'→'.join(hp_chain)}）"
        )
        self.log[start:end] = [
            self._format_use_action_block(uses),
            damage_line,
            self._format_gain_action_block(merged_gain),
        ]

    def _bind_player_callbacks(self):
        for ps in getattr(self, 'players', []):
            ps._enter_hand_callback = self._handle_card_enter_hand
            ps._draw_callback = self._handle_draw_callback

    def _refresh_hand_limit_bonuses(self):
        for ps in getattr(self, 'players', []):
            ps.extra_hand_limit_bonus = 0
            ps.external_zero_e_ignore_hand_limit = False
        for owner_id, owner_state in enumerate(getattr(self, 'players', []) or []):
            for eq in getattr(owner_state, 'equipment', []) or []:
                try:
                    target_id = int(getattr(eq, 'effect_target', owner_id))
                except Exception:
                    target_id = owner_id
                if target_id != owner_id and 0 <= target_id < len(self.players):
                    if self._equipment_is(eq, 'GoldenLeaf', 'vanilla:goldenleaf'):
                        self.players[target_id].extra_hand_limit_bonus += 1
                    if self._equipment_is(eq, 'MagicGoldenLeaf', 'vanilla:magicgoldenleaf'):
                        self.players[target_id].external_zero_e_ignore_hand_limit = True
                if 0 <= target_id < len(self.players) and self._equipment_is(eq, 'hel:bugatti', 'Bugatti'):
                    self.players[target_id].extra_hand_limit_bonus -= 1

    def _player_zero_e_cards_ignore_hand_limit(self, player_id: int) -> bool:
        if not (0 <= player_id < len(getattr(self, 'players', []))):
            return False
        for owner_id, owner_state in enumerate(getattr(self, 'players', []) or []):
            for eq in getattr(owner_state, 'equipment', []) or []:
                try:
                    target_id = int(getattr(eq, 'effect_target', owner_id))
                except Exception:
                    target_id = owner_id
                if target_id == player_id and self._equipment_is(eq, 'MagicGoldenLeaf', 'vanilla:magicgoldenleaf'):
                    return True
        return False

    def _handle_card_enter_hand(self, player_id: int, card: CardInstance):
        if not (0 <= player_id < len(getattr(self, 'players', []))):
            return
        if not card or card.def_id == ERROR_CARD_ID:
            return
        ps = self.players[player_id]
        if self._apply_unable_counter_to_entering_card(player_id, card):
            return
        # Copy: create exile copies when entering hand
        copy_count = getattr(card.card_def, 'copy_count', 0)
        if copy_count > 0 and 'copy' in card.flags:
            added = 0
            for _ in range(copy_count):
                if not ps.can_add_to_hand():
                    break
                copy_card = CardInstance(def_id=card.def_id)
                copy_card.instance_flags.add('exile')
                # Remove copy tag from copies to prevent infinite loop
                copy_card.disabled_flags.add('copy')
                self._apply_setup_modifiers_to_card(player_id, copy_card)
                ps.add_to_hand(copy_card, trigger_enter_hand=False)
                added += 1
            if added > 0:
                self.log_msg(f"{self.pn(player_id)}的{card.name_cn}因副本效果加入{added}张放逐复制")
        swift_before = int(getattr(card, 'swift_value', 0) or 0)
        if self._has_card_event(card.card_def, 'enter_hand'):
            self._run_card_event(player_id, card, 'enter_hand', None, {
                'source_id': player_id,
                'target_id': player_id,
                'zone': 'hand',
            })
        if self._card_is(card, 'BloodCorn', 'desert_cards_addition:blood_corn'):
            swift_after = int(getattr(card, 'swift_value', 0) or 0)
            if swift_after <= swift_before:
                self._add_card_swift_stack(card, 1)
        if self._card_is(card, 'Spikeball', 'ocean:spikeball'):
            try:
                hand_count = len(getattr(ps, 'hand', []) or [])
            except Exception:
                hand_count = 0
            if hand_count < 4:
                card.instance_flags.add('wide_strike')
                card.instance_flags.add('precision')
                card.instance_flags.add('ocean_spikeball_boosted')
            else:
                if 'ocean_spikeball_boosted' in getattr(card, 'instance_flags', set()):
                    card.instance_flags.discard('precision')
                card.instance_flags.discard('wide_strike')
                card.instance_flags.discard('ocean_spikeball_boosted')

    def _add_card_swift_stack(self, card: CardInstance, amount: int = 1):
        if not card or amount == 0:
            return
        current = int(getattr(card, 'swift_value', 0) or 0)
        value = max(0, min(18, current + int(amount)))
        setattr(card, 'swift_value', value)
        if value > 0:
            card.instance_flags.add('swift')
            card.disabled_flags.discard('swift')
        else:
            card.instance_flags.discard('swift')
            card.disabled_flags.add('swift')

    def _handle_draw_callback(self, player_id: int, card: CardInstance):
        """Called when a player draws a card. Triggers v2 after_draw event hooks."""
        if not (0 <= player_id < len(getattr(self, 'players', []))):
            return
        self._run_v2_event_hooks('after_draw', {
            'source_player': player_id,
            'target_player': player_id,
            'vars': {'player_id': player_id, 'drawn_card': card.def_id if card else ''},
        })
        self._apply_electric_web_draw_damage(player_id, 1)

    def _coerce_mod_var_initial(self, value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _team_var_keys(self) -> List[str]:
        if hasattr(self, 'teams'):
            return [str(i) for i in range(len(getattr(self, 'teams', [])))]
        return [str(i) for i in range(len(getattr(self, 'players', [])))]

    def _init_mod_variables(self):
        try:
            from mod_loader import get_active_mod_variables
            variables = get_active_mod_variables()
        except Exception:
            variables = []
        if not hasattr(self, 'custom_vars'):
            self.custom_vars = {}
        if not hasattr(self, 'team_custom_vars'):
            self.team_custom_vars = {}
        for variable in variables:
            name = str(variable.get('name') or variable.get('id') or '').strip()
            if not name:
                continue
            scope = variable.get('scope', 'player')
            initial = self._coerce_mod_var_initial(variable.get('initial', 0))
            if scope == 'global':
                self.custom_vars.setdefault(name, initial)
            elif scope == 'team':
                for key in self._team_var_keys():
                    self.team_custom_vars.setdefault(key, {}).setdefault(name, initial)
            else:
                for player in self.players:
                    player.custom_vars.setdefault(name, initial)

    def _visible_card_dicts(self, cards, viewer_id: int, owner_id: int, *, choice_list: bool = False):
        return [
            c.to_dict() for c in cards
            if (owner_id == viewer_id and not (choice_list and self._card_is_sublime(c))) or (
                owner_id != viewer_id
                and
                c.def_id != ERROR_CARD_ID
                and not self._card_is_sublime(c)
            )
        ]

    def _card_is_sublime(self, card: Optional[CardInstance]) -> bool:
        if card is None:
            return False
        try:
            flags = normalize_card_flags(getattr(card, 'flags', set()) or set())
        except Exception:
            flags = normalize_card_flags(getattr(getattr(card, 'card_def', None), 'flags', set()) or set())
        return bool(flags.intersection({'sublime', 'vanilla:sublime', 'tag_sublime', 'tag_vanilla:sublime'}))

    def _card_selectable_by_action(self, card: Optional[CardInstance]) -> bool:
        """Cards with Sublime can be played, but cannot be selected by other effects."""
        return card is not None and not self._card_is_sublime(card)

    def _card_visible_to_player(self, card: Optional[CardInstance], viewer_id: int, owner_id: Optional[int] = None) -> bool:
        if card is None:
            return False
        if owner_id is None:
            owner_id, _, _ = self._find_card_location(card)
        return owner_id == viewer_id or not self._card_is_sublime(card)

    def _redact_error_cards_from_payload(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            return payload
        for zone in ('hand', 'deck', 'discard', 'exile'):
            cards = payload.get(zone)
            if isinstance(cards, list):
                payload[zone] = [
                    c for c in cards
                    if not (isinstance(c, dict) and c.get('def_id') == ERROR_CARD_ID)
                ]
                payload[f'{zone}_count'] = len(payload[zone])
        return payload

    def get_public_state(self, for_player: int) -> dict:
        self._refresh_equipment_derived_player_flags()
        self._refresh_hand_limit_bonuses()
        opponent = 1 - for_player
        opp_data = self.players[opponent].to_dict(include_private=False)
        opp_data['hand_count'] = len([c for c in self.players[opponent].hand if c.def_id != ERROR_CARD_ID])
        opp_data['deck_count'] = len([c for c in self.players[opponent].deck if c.def_id != ERROR_CARD_ID])
        opp_data['discard_count'] = len([c for c in self.players[opponent].discard if c.def_id != ERROR_CARD_ID])
        opp_data['exile_count'] = len([c for c in self.players[opponent].exile if c.def_id != ERROR_CARD_ID])
        if self.pending_choice and self.pending_choice.get('player_id') == for_player:
            ct = self.pending_choice.get('choice_type', '')
            if ct in ('choose_from_enemy_hand',):
                opp_data['hand'] = self._visible_card_dicts(self.players[opponent].hand, for_player, opponent, choice_list=True)
            target_id = self.pending_choice.get('target_player_id')
            params = self.pending_choice.get('choice_params', {}) or {}
            if target_id == opponent and ct in ('choose_card_from_hand', 'choose_from_deck', 'choose_from_discard', 'choose_from_exile', 'choose_equipment'):
                zone = params.get('zone', '')
                if ct == 'choose_card_from_hand' or zone == 'hand':
                    opp_data['hand'] = self._visible_card_dicts(self.players[opponent].hand, for_player, opponent, choice_list=True)
                if ct == 'choose_from_deck' or zone == 'deck':
                    opp_data['deck'] = self._visible_card_dicts(self.players[opponent].deck, for_player, opponent, choice_list=True)
                if ct == 'choose_from_discard' or zone == 'discard':
                    opp_data['discard'] = self._visible_card_dicts(self.players[opponent].discard, for_player, opponent, choice_list=True)
                if ct == 'choose_from_exile' or zone == 'exile':
                    opp_data['exile'] = self._visible_card_dicts(self.players[opponent].exile, for_player, opponent, choice_list=True)
        if self._antennae_reveal[for_player]:
            opp_data['revealed_hand'] = self._visible_card_dicts(self.players[opponent].hand, for_player, opponent)
        # Revealed tag cards: opponent hand cards with revealed tag visible
        if hasattr(self, '_revealed_tag_cards') and self._revealed_tag_cards.get(for_player):
            opp_data['revealed_tag_cards'] = self._revealed_tag_cards[for_player]
        # Auto-detect revealed tag on opponent hand cards
        opp_revealed = [
            c.to_dict()
            for c in self.players[opponent].hand
            if 'revealed' in c.flags and c.def_id != ERROR_CARD_ID and not self._card_is_sublime(c)
        ]
        if opp_revealed:
            opp_data['revealed_tag_cards'] = opp_revealed
        log_start = 0
        self._mark_log_visible()
        # Goggles: the viewer may inspect ordered deck/discard for the chosen target.
        goggles_targets = self._goggles_view_targets_for(for_player)
        if opponent in goggles_targets:
            opp_data['deck_ordered'] = [c.to_dict() for c in self.players[opponent].deck]
            opp_data['discard_ordered'] = [c.to_dict() for c in self.players[opponent].discard]
        you_data = self.players[for_player].to_dict(include_private=True)
        if for_player in goggles_targets:
            you_data['deck_ordered'] = [c.to_dict() for c in self.players[for_player].deck]
            you_data['discard_ordered'] = [c.to_dict() for c in self.players[for_player].discard]
        return {
            'phase': self.phase,
            'current_player': self.current_player,
            'round_num': self.round_num,
            'game_over': self.game_over,
            'winner': self.winner,
            'you': you_data,
            'opponent': opp_data,
            'log': list(self.log),
            'log_start': log_start,
            'log_total': len(self.log),
            'pending_response': self._public_pending_response(for_player),
            'pending_choice': self.pending_choice,
            'pending_v2_ui': self._public_v2_ui(for_player),
            'opening_event_picks': self.opening_event_picks,
            'antennae_reveal': self._antennae_reveal[for_player],
            'forced_target_player_id': self._sewers_forced_target_for_player(for_player),
        }

    def start_event_select_first(self):
        """Start event_select phase before draft. Called after matching."""
        self.phase = 'event_select'
        self.draft_rerolls = [DRAFT_REROLLS, DRAFT_REROLLS]
        self.player_ready = [False, False]
        self.player_draft_started = [False, False]
        self._generate_opening_events()

    def start_draft_for_player(self, player_id: int):
        """Initialize draft for a specific player after they select their event.
        Called independently per player - no need to wait for opponent."""
        # Initialize draft pool and type order on first call
        if not self.draft_pool:
            self.draft_pool = build_draft_pool(self.allowed_card_ids)
            self.draft_pool = [
                c for c in self.draft_pool
                if 'team_limited' not in normalize_card_flags(getattr(c.card_def, 'flags', set()) or set())
            ]
            self.draft_type_order = []
            for card_type, count in DRAFT_RATIO.items():
                self.draft_type_order.extend([card_type] * count)
            random.shuffle(self.draft_type_order)
        # Ensure draft_picks is initialized
        if not self.draft_picks[player_id]:
            self.draft_picks[player_id] = []
        self.player_draft_started[player_id] = True
        # Generate draft options for this player
        self._generate_draft_options_for_player(player_id)
        # Update global phase
        self.phase = 'draft'

    def _generate_draft_options_for_player(self, player_id: int):
        if len(self.draft_picks[player_id]) >= self.draft_target_count(player_id):
            return
        card_type = self.draft_type_order[len(self.draft_picks[player_id])]
        self.draft_options[player_id] = generate_draft_options(self.draft_pool, card_type, 3)

    def _generate_draft_options(self):
        self._generate_draft_options_for_player(0)
        self._generate_draft_options_for_player(1)

    def draft_pick(self, player_id: int, def_id: str) -> bool:
        if len(self.draft_picks[player_id]) >= self.draft_target_count(player_id):
            return False
        if not self.draft_options[player_id]:
            self._generate_draft_options_for_player(player_id)
        options = self.draft_options[player_id]
        found = None
        for opt in options:
            if opt.def_id == def_id:
                found = opt
                break
        if found is None:
            return False
        self.draft_picks[player_id].append(def_id)
        self._generate_draft_options_for_player(player_id)
        return True

    def draft_reroll(self, player_id: int) -> bool:
        if self.draft_rerolls[player_id] <= 0:
            return False
        if len(self.draft_picks[player_id]) >= self.draft_target_count(player_id):
            return False
        old_ids = [c.def_id for c in self.draft_options[player_id]]
        self.draft_rerolls[player_id] -= 1
        card_type = self.draft_type_order[len(self.draft_picks[player_id])]
        options = generate_draft_options(self.draft_pool, card_type, 3, exclude_def_ids=old_ids)
        self.draft_options[player_id] = options
        return True

    def _v2_opening_event_option(self, resource: dict) -> Optional[dict]:
        if not isinstance(resource, dict):
            return None
        event_id = str(resource.get('id') or '').strip()
        if not event_id:
            return None
        name_cn = str(resource.get('name_cn') or resource.get('name') or event_id)
        name_en = str(resource.get('name_en') or resource.get('name') or name_cn)
        desc_cn = str(resource.get('description_cn') or resource.get('description') or resource.get('desc_cn') or resource.get('desc') or '')
        desc_en = str(resource.get('description_en') or resource.get('desc_en') or desc_cn)
        try:
            position = int(resource.get('position', 2))
        except Exception:
            position = 2
        try:
            weight = max(0.0, float(resource.get('weight', 1)))
        except Exception:
            weight = 1.0
        return {
            'id': event_id,
            'name': name_cn,
            'name_cn': name_cn,
            'name_en': name_en,
            'name_i18n': {'zh': name_cn, 'en': name_en},
            'desc': desc_cn,
            'description': desc_cn,
            'desc_cn': desc_cn,
            'desc_en': desc_en,
            'desc_i18n': {'zh': desc_cn, 'en': desc_en},
            'position': position,
            'weight': weight,
            'v2': True,
        }

    def _opening_events_for_position(self, position: int) -> List[dict]:
        events = [dict(e) for e in self.OPENING_EVENTS.values() if e.get('position') == position]
        for resource in (getattr(self, 'v2_opening_event_defs', {}) or {}).values():
            option = self._v2_opening_event_option(resource)
            if option and option.get('position') == position:
                events.append(option)
        return events

    def _all_opening_events(self) -> List[dict]:
        events = [dict(e) for e in self.OPENING_EVENTS.values()]
        for resource in (getattr(self, 'v2_opening_event_defs', {}) or {}).values():
            option = self._v2_opening_event_option(resource)
            if option:
                events.append(option)
        return events

    def _opening_event_sort_key(self, event: dict):
        event_id = event.get('id') if isinstance(event, dict) else ''
        try:
            order_key = self.OPENING_EVENT_ORDER.get(int(event_id), 500)
        except Exception:
            order_key = 500
        return (order_key, str(event_id))

    def _event_color(self, event_id) -> str:
        try:
            return self.OPENING_EVENT_COLORS.get(int(event_id), '#6B7280')
        except Exception:
            return '#6B7280'

    def _choose_opening_event(self, events: List[dict]):
        events = [event for event in events if event]
        if not events:
            return None
        weights = []
        for event in events:
            try:
                weights.append(max(0.0, float(event.get('weight', 1))))
            except Exception:
                weights.append(1.0)
        if any(weight > 0 for weight in weights):
            return random.choices(events, weights=weights, k=1)[0]
        return random.choice(events)

    def _generate_opening_events(self):
        pool = self._all_opening_events()
        for i in range(2):
            options = []
            available = list(pool)
            for _ in range(min(3, len(available))):
                picked = self._choose_opening_event(available)
                if not picked:
                    break
                options.append(picked)
                picked_id = str(picked.get('id'))
                available = [ev for ev in available if str(ev.get('id')) != picked_id]
            options.sort(key=self._opening_event_sort_key)
            for ev in options:
                ev['color'] = self._event_color(ev.get('id'))
            self.opening_event_options[i] = options
            self.opening_event_magic_options[i] = [[] for _ in self.opening_event_options[i]]

    def _card_allowed(self, def_id: str) -> bool:
        return self.allowed_card_ids is None or def_id in self.allowed_card_ids

    def _opening_event_ids_equal(self, left, right) -> bool:
        return str(left) == str(right)

    def select_opening_event(self, player_id: int, event_id: int) -> bool:
        if self.opening_event_picks[player_id] is not None:
            return False
        for event in self.opening_event_options[player_id]:
            if event and self._opening_event_ids_equal(event.get('id'), event_id):
                self.opening_event_picks[player_id] = event.get('id')
                return True
        return False

    def reroll_opening_event(self, player_id: int) -> bool:
        """Reroll opening event options, guaranteeing at least 1 different option.
        Uses draft_rerolls (shared with draft phase)."""
        if self.opening_event_picks[player_id] is not None:
            return False
        if self.draft_rerolls[player_id] <= 0:
            return False
        old_ids = set()
        for event in self.opening_event_options[player_id]:
            if event:
                old_ids.add(str(event.get('id')))
        # Generate new options, retrying until at least 1 is different
        max_attempts = 20
        for _ in range(max_attempts):
            available = self._all_opening_events()
            new_options = []
            for _ in range(min(3, len(available))):
                picked = self._choose_opening_event(available)
                if not picked:
                    break
                new_options.append(picked)
                picked_id = str(picked.get('id'))
                available = [ev for ev in available if str(ev.get('id')) != picked_id]
            new_options.sort(key=self._opening_event_sort_key)
            for ev in new_options:
                ev['color'] = self._event_color(ev.get('id'))
            new_ids = set()
            for event in new_options:
                if event:
                    new_ids.add(str(event.get('id')))
            if new_ids != old_ids:
                self.opening_event_options[player_id] = new_options
                self.opening_event_magic_options[player_id] = [[] for _ in new_options]
                self.draft_rerolls[player_id] -= 1
                return True
        # Fallback: just regenerate even if all same (shouldn't happen with enough events)
        self.opening_event_options[player_id] = new_options
        self.opening_event_magic_options[player_id] = [[] for _ in new_options]
        self.draft_rerolls[player_id] -= 1
        return True

    def both_events_selected(self) -> bool:
        return self.opening_event_picks[0] is not None and self.opening_event_picks[1] is not None

    def get_player_status(self, player_id: int) -> str:
        """Get per-player status: 'event_select', 'drafting', 'sub_choice', or 'ready'."""
        if self.player_ready[player_id]:
            return 'ready'
        if self.opening_event_picks[player_id] is None:
            return 'event_select'
        if not self.player_draft_started[player_id]:
            return 'event_reveal'
        if len(self.draft_picks[player_id]) < self.draft_target_count(player_id):
            return 'drafting'
        if self.needs_sub_choice(player_id):
            return 'sub_choice'
        # Draft done, no sub-choice needed
        self.player_ready[player_id] = True
        return 'ready'

    def draft_target_count(self, player_id: int) -> int:
        """Number of cards this player needs to draft before setup sub-choices."""
        try:
            event_id = self.opening_event_picks[player_id]
        except Exception:
            event_id = None
        if str(event_id) == '5':
            return max(0, DECK_SIZE - 1)
        return DECK_SIZE

    def needs_sub_choice(self, player_id: int) -> bool:
        """Check if the player's opening event needs a sub-choice after draft."""
        event_id = self.opening_event_picks[player_id]
        if event_id is None:
            return False
        sub = self.opening_event_sub_choices[player_id]
        # Events 2 (magic conversion), 3 (light conversion), 5 (fated draw), 8 (yggdrasil) need sub-choices
        if str(event_id) in ('2', '3', '5', '8') and not sub:
            return True
        # Check v2 events that need sub-choices
        resource = (getattr(self, 'v2_opening_event_defs', {}) or {}).get(str(event_id))
        if isinstance(resource, dict):
            events = resource.get('events', {})
            if isinstance(events, dict) and events.get('on_apply'):
                # Check if the v2 event has choose operations
                on_apply = events.get('on_apply', [])
                if isinstance(on_apply, list):
                    for step in on_apply:
                        if isinstance(step, dict) and step.get('type') in ('choose_from_deck', 'choose_card_from_hand', 'choose_from_discard'):
                            return True
        return False

    def start_game(self):
        self.phase = 'playing'
        force_first = []
        for i in range(2):
            if self.opening_event_picks[i] == 7:
                force_first.append(i)
        if len(force_first) == 1:
            self.first_player = force_first[0]
        else:
            self.first_player = random.randint(0, 1)
        self.current_player = self.first_player
        for i in range(2):
            ps = self.players[i]
            ps.is_first_player = (i == self.first_player)
            ps.deck = create_deck_from_draft(self.draft_picks[i], self.allowed_card_ids)
            ps.health = INITIAL_HEALTH
            ps.max_health = BASE_MAX_HEALTH
            ps.base_max_health = BASE_MAX_HEALTH
            ps.elixir = INITIAL_ELIXIR
            ps.magic = INITIAL_MAGIC
            self._reset_achievement_match_stats(i)
        for pid in range(len(self.players)):
            self._enforce_unique_cards_for_player(pid)
        for i in range(2):
            ps = self.players[i]
            if i != self.first_player:
                ps.health = SECOND_PLAYER_HEALTH
                ps.max_health = SECOND_PLAYER_HEALTH
                ps.base_max_health = SECOND_PLAYER_HEALTH
                self._reset_achievement_match_stats(i)
        # Built-in setup effects are applied before the opening draw. This lets
        # deck conversions such as Light trigger normal draw-time rules.
        self._apply_builtin_opening_events_before_initial_draw()
        for i in range(2):
            ps = self.players[i]
            if i == self.first_player:
                ps.elixir = FIRST_PLAYER_ELIXIR
                hand_size = FIRST_PLAYER_HAND_SIZE
                if self.opening_event_picks[i] == 7 and len(force_first) == 1:
                    hand_size = 5
                    ps.elixir = 7
                if self.opening_event_picks[i] == 5:
                    hand_size = max(0, hand_size - 1)
                ps.draw_cards(hand_size)
            else:
                hand_size = INITIAL_HAND_SIZE
                if self.opening_event_picks[i] == 5:
                    hand_size = max(0, hand_size - 1)
                ps.draw_cards(hand_size)
        # Keep v2/custom opening events deferred for now because some may
        # intentionally operate on the opening hand.
        self._apply_deferred_opening_events_after_initial_draw()
        self._save_all_match_start_snapshots()
        self.round_num = 1
        self.log_msg(f"游戏开始！{self.pn(self.first_player)}先手。")
        self.log_msg(f"=== 第{self.round_num}回合 ===")
        self._apply_late_round_fire_pressure()
        self._start_player_turn(self.first_player)

    def _opening_event_enemy_targets(self, player_id: int):
        target_id = 1 - player_id
        return [target_id] if 0 <= target_id < len(self.players) else []

    def _replace_first_card_in_setup_zones(self, player_id: int, source_def_id: str, replacement: CardInstance) -> bool:
        """Replace one matching setup card after initial draw.

        Setup choices are made from the drafted deck list, but initial hands are
        drawn before setup effects are applied. Search both hand and deck so a
        chosen card still converts when it was drawn into the opening hand.
        """
        ps = self.players[player_id]
        for zone_name in ('hand', 'deck'):
            zone = getattr(ps, zone_name, None)
            if not isinstance(zone, list):
                continue
            for idx, card in enumerate(zone):
                if getattr(card, 'def_id', None) == source_def_id:
                    zone[idx] = replacement
                    return True
        return False

    def _replace_first_non_yggdrasil_setup_card(self, player_id: int) -> bool:
        ps = self.players[player_id]
        for zone_name in ('hand', 'deck'):
            zone = getattr(ps, zone_name, None)
            if not isinstance(zone, list):
                continue
            for idx in range(len(zone) - 1, -1, -1):
                if getattr(zone[idx], 'def_id', None) != 'Yggdrasil':
                    zone[idx] = self._apply_setup_modifiers_to_card(player_id, CardInstance(def_id='Yggdrasil'))
                    return True
        return False

    def _card_allowed_for_fated_draw(self, def_id: str) -> bool:
        card_def = CARD_DEFS.get(def_id)
        if not card_def:
            return False
        if def_id == ERROR_CARD_ID:
            return False
        if self.allowed_card_ids is not None and def_id not in self.allowed_card_ids:
            return False
        return int(getattr(card_def, 'count', 0) or 0) > 0

    def fated_draw_pool_defs(self) -> List[str]:
        return sorted(
            [def_id for def_id in CARD_DEFS if self._card_allowed_for_fated_draw(def_id)],
            key=lambda did: (
                {'thorn': 0, 'bloom': 1, 'guard': 2, 'root': 3}.get(CARD_DEFS[did].card_type, 9),
                str(CARD_DEFS[did].name_en or did).lower(),
            )
        )

    def _card_total_hits(self, card: CardInstance, base_hits: Optional[int] = None) -> int:
        base = int(base_hits if base_hits is not None else getattr(card.card_def, 'hits', 1) or 1)
        return clamp_damage_hits(base + clamp_card_extra_hits(getattr(card, 'extra_hits', 0)))

    def _clamp_card_layers(self, card: Optional[CardInstance]) -> Optional[CardInstance]:
        if card is None:
            return None
        card.fission_level = clamp_card_layer(getattr(card, 'fission_level', 1))
        card.fusion_level = clamp_card_layer(getattr(card, 'fusion_level', 1))
        card.fission_count = max(0, card.fission_level - 1)
        card.fusion_multiplier = float(card.fusion_level)
        card.extra_hits = clamp_card_extra_hits(getattr(card, 'extra_hits', 0))
        return card

    def _card_base_petal_count(self, card: CardInstance) -> int:
        if getattr(card, 'def_id', '') == 'Fission':
            return 2
        vanilla_fallback = {'Sand': 4, 'Wing': 2, 'Light': 2}
        best = max(
            1,
            int(getattr(card.card_def, 'hits', 1) or 1),
            int(vanilla_fallback.get(getattr(card, 'def_id', ''), 1)),
        )
        try:
            for effect in self._play_effects_for_card(card):
                if not isinstance(effect, dict):
                    continue
                effect_type = str(effect.get('type') or '')
                if self._EFFECT_ALIASES.get(effect_type, effect_type) != 'deal_damage':
                    continue
                params = effect.get('params') if isinstance(effect.get('params'), dict) else {}
                hits = params.get('hits', 1)
                if isinstance(hits, (int, float)) or (isinstance(hits, str) and hits.isdigit()):
                    best = max(best, int(hits))
        except Exception:
            pass
        return best

    def _apply_setup_modifiers_to_card(self, player_id: int, card: Optional[CardInstance]) -> Optional[CardInstance]:
        if card is None or not (0 <= player_id < len(self.players)):
            return card
        try:
            event_id = int(self.opening_event_picks[player_id])
        except Exception:
            event_id = self.opening_event_picks[player_id]
        if event_id == 9 and self._card_base_petal_count(card) >= 2:
            modifiers = getattr(card, 'setup_modifiers', None)
            if not isinstance(modifiers, set):
                modifiers = set(modifiers or [])
                card.setup_modifiers = modifiers
            if 'multi_petal' not in modifiers:
                if getattr(card, 'def_id', '') == 'Fission':
                    card.instance_flags.add('multi_petal_fission')
                else:
                    card.extra_hits = clamp_card_extra_hits(max(0, int(getattr(card, 'extra_hits', 0) or 0)) + 1)
                modifiers.add('multi_petal')
        return card

    def _apply_multi_petal_to_player_deck(self, player_id: int):
        ps = self.players[player_id]
        changed = 0
        for card in ps.deck:
            before = max(0, int(getattr(card, 'extra_hits', 0) or 0))
            self._apply_setup_modifiers_to_card(player_id, card)
            if max(0, int(getattr(card, 'extra_hits', 0) or 0)) > before:
                changed += 1
        added = 0
        if self._card_allowed('Dust'):
            for _ in range(5):
                dust = CardInstance(def_id='Dust')
                dust.instance_flags.add('exile')
                self._apply_setup_modifiers_to_card(player_id, dust)
                ps.deck.append(dust)
                added += 1
            random.shuffle(ps.deck)
        self.log_msg(f"{self.pn(player_id)}【多重瓣】：{changed}张多子瓣牌子瓣+1，{added}张[[card:Dust|flag=exile]]洗入牌库")

    def _apply_magic_acceleration_after_play(self, player_id: int, card: Optional[CardInstance] = None):
        ps = self.players[player_id]
        if int(getattr(ps, 'custom_vars', {}).get('setup_magic_acceleration', 0) or 0) <= 0:
            return
        if card is not None and int(getattr(card, 'cost_m', 0) or 0) > 0:
            return
        before = ps.magic
        ps.gain_magic(1)
        if ps.magic != before:
            self.log_msg(f"{self.pn(player_id)}【魔力加速】：+1M")

    def _is_builtin_opening_event(self, event_id) -> bool:
        return isinstance(event_id, int) or (isinstance(event_id, str) and event_id.isdigit())

    def _apply_builtin_opening_events_before_initial_draw(self):
        for i in range(len(self.players)):
            if self._is_builtin_opening_event(self.opening_event_picks[i]):
                self._apply_opening_event(i)

    def _apply_deferred_opening_events_after_initial_draw(self):
        for i in range(len(self.players)):
            if not self._is_builtin_opening_event(self.opening_event_picks[i]):
                self._apply_opening_event(i)

    def preview_setup_cards(self, player_id: int) -> List[dict]:
        if not (0 <= player_id < len(self.players)):
            return []
        cards = []
        for def_id in self.draft_picks[player_id]:
            if self.allowed_card_ids is not None and def_id not in self.allowed_card_ids:
                continue
            cards.append(CardInstance(def_id=def_id))

        def replace_first(source_def_id: str, replacement: CardInstance) -> bool:
            for idx, card in enumerate(cards):
                if getattr(card, 'def_id', None) == source_def_id:
                    cards[idx] = replacement
                    return True
            return False

        def replace_first_non_yggdrasil() -> bool:
            for idx in range(len(cards) - 1, -1, -1):
                if getattr(cards[idx], 'def_id', None) != 'Yggdrasil':
                    cards[idx] = self._apply_setup_modifiers_to_card(player_id, CardInstance(def_id='Yggdrasil'))
                    return True
            return False

        event_id = self.opening_event_picks[player_id]
        sub = self.opening_event_sub_choices[player_id]
        if not self._is_builtin_opening_event(event_id):
            return [c.to_dict() for c in cards]
        try:
            event_id = int(event_id)
        except Exception:
            return [c.to_dict() for c in cards]
        if event_id == 2 and sub and 'conversions' in sub:
            for conv in sub.get('conversions') or []:
                source_def = conv.get('source_def_id')
                if source_def and 'ManaOrb' in CARD_DEFS:
                    mana_card = CardInstance(def_id='ManaOrb')
                    mana_card.instance_flags = {'sprout', 'symbiosis'}
                    self._apply_setup_modifiers_to_card(player_id, mana_card)
                    replace_first(source_def, mana_card)
        elif event_id == 3 and self._card_allowed('Light') and sub and 'convert_def_ids' in sub:
            converted = 0
            for target_def in list(sub.get('convert_def_ids') or []):
                if converted >= 5:
                    break
                light_card = CardInstance(def_id='Light')
                light_card.instance_flags = {'sprout', 'symbiosis'}
                self._apply_setup_modifiers_to_card(player_id, light_card)
                if replace_first(target_def, light_card):
                    converted += 1
        elif event_id == 8:
            if not self._card_allowed('Yggdrasil'):
                return [c.to_dict() for c in cards]
            target_def = sub.get('yggdrasil_convert_def_id') if isinstance(sub, dict) else None
            if target_def:
                if not replace_first(target_def, self._apply_setup_modifiers_to_card(player_id, CardInstance(def_id='Yggdrasil'))):
                    replace_first_non_yggdrasil()
            else:
                replace_first_non_yggdrasil()
        elif event_id == 5 and isinstance(sub, dict):
            for def_id in list(sub.get('add_def_ids') or sub.get('def_ids') or [])[:1]:
                if self._card_allowed_for_fated_draw(str(def_id)):
                    cards.append(self._apply_setup_modifiers_to_card(player_id, CardInstance(def_id=str(def_id))))
        elif event_id == 9:
            for card in cards:
                self._apply_setup_modifiers_to_card(player_id, card)
        return [c.to_dict() for c in cards]

    def _apply_opening_event(self, player_id: int):
        ps = self.players[player_id]
        event_id = self.opening_event_picks[player_id]
        sub = self.opening_event_sub_choices[player_id]
        if self._apply_v2_opening_event(player_id, event_id):
            return
        if event_id == 1:
            ps.max_health += 20
            ps.base_max_health += 20
            ps.health += 20
            self.log_msg(f"{self.pn(player_id)}【生命强化】：最大生命值+20")
        elif event_id == 2:
            if sub and 'conversions' in sub:
                conversions = sub['conversions']
                converted = 0
                for conv in conversions:
                    source_def = conv.get('source_def_id')
                    if source_def and 'ManaOrb' in CARD_DEFS:
                        mana_card = CardInstance(def_id='ManaOrb')
                        mana_card.instance_flags = {'sprout', 'symbiosis'}
                        self._apply_setup_modifiers_to_card(player_id, mana_card)
                        if self._replace_first_card_in_setup_zones(player_id, source_def, mana_card):
                            converted += 1
                if converted:
                    self.log_msg(f"{self.pn(player_id)}【魔力转化】：将最多3张牌转化为[[card:ManaOrb|flag=sprout|flag=symbiosis]]")
        elif event_id == 3:
            converted = 0
            if self._card_allowed('Light') and sub and 'convert_def_ids' in sub:
                target_def_ids = list(sub['convert_def_ids'])
                converted = 0
                for target_def in target_def_ids:
                    if converted >= 5:
                        break
                    light_card = CardInstance(def_id='Light')
                    light_card.instance_flags = {'sprout', 'symbiosis'}
                    self._apply_setup_modifiers_to_card(player_id, light_card)
                    if self._replace_first_card_in_setup_zones(player_id, target_def, light_card):
                        converted += 1
                self.log_msg(f"{self.pn(player_id)}【光之洗礼】：{converted}张牌变为[[card:Light|flag=sprout|flag=symbiosis]]")
        elif event_id == 4:
            target_ids = self._opening_event_enemy_targets(player_id)
            for target_id in target_ids:
                if self._status_application_blocked(target_id, 'fire'):
                    continue
                self.players[target_id].fire += 3
            target_label = "敌方全体" if len(target_ids) > 1 else "敌方"
            self.log_msg(f"{self.pn(player_id)}【烈焰预兆】：{target_label}+3灼烧")
        elif event_id == 5:
            picked = []
            if isinstance(sub, dict):
                picked = list(sub.get('add_def_ids') or sub.get('def_ids') or [])
            added = 0
            for def_id in picked[:1]:
                if self._card_allowed_for_fated_draw(str(def_id)):
                    ps.deck.append(self._apply_setup_modifiers_to_card(player_id, CardInstance(def_id=str(def_id))))
                    added += 1
            if added:
                random.shuffle(ps.deck)
            self.log_msg(f"{self.pn(player_id)}【命运抽签】：少抽1张牌，{added}张牌洗入牌库")
        elif event_id == 6:
            self.log_msg(f"{self.pn(player_id)}【能量涌动】：每回合多回复1E")
        elif event_id == 7:
            self.log_msg(f"{self.pn(player_id)}【先手压制】：先手回复7E并抽5张牌")
        elif event_id == 8:
            ps.max_health -= 20
            ps.base_max_health -= 20
            ps.health -= 20
            self._note_achievement_health(player_id)
            if not self._card_allowed('Yggdrasil'):
                return
            if sub and 'yggdrasil_convert_def_id' in sub:
                target_def = sub['yggdrasil_convert_def_id']
                yggdrasil_card = self._apply_setup_modifiers_to_card(player_id, CardInstance(def_id='Yggdrasil'))
                if self._replace_first_card_in_setup_zones(player_id, target_def, yggdrasil_card):
                    target_name = CARD_DEFS.get(target_def, CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn
                    self.log_msg(f"{self.pn(player_id)}【绝境求生】：最大生命值-20，{target_name}变为Yggdrasil")
                elif self._replace_first_non_yggdrasil_setup_card(player_id):
                    self.log_msg(f"{self.pn(player_id)}【绝境求生】：最大生命值-20，一张牌变为Yggdrasil")
            else:
                if self._replace_first_non_yggdrasil_setup_card(player_id):
                    self.log_msg(f"{self.pn(player_id)}【绝境求生】：最大生命值-20，一张牌变为Yggdrasil")
        elif event_id == 9:
            self._apply_multi_petal_to_player_deck(player_id)
        elif event_id == 10:
            ps.max_health -= 10
            ps.base_max_health -= 10
            ps.health = min(ps.health, ps.max_health)
            self._note_achievement_health(player_id)
            ps.custom_vars['setup_magic_acceleration'] = 1
            self.log_msg(f"{self.pn(player_id)}【魔力加速】：最大生命值-10，打出不消耗M的牌后回复1M")

    def _apply_v2_opening_event(self, player_id: int, event_id) -> bool:
        if event_id is None:
            return False
        resource = (getattr(self, 'v2_opening_event_defs', {}) or {}).get(str(event_id))
        if not isinstance(resource, dict):
            return False
        events = resource.get('events') if isinstance(resource.get('events'), dict) else {}
        event_def = events.get('on_apply') if isinstance(events, dict) else None
        if not event_def:
            return True
        context = {
            'source_player': player_id,
            'target_player': player_id,
            'card': None,
            'room': getattr(self, 'room', None),
            'loadout': getattr(self, 'v2_loadout', None),
            'vars': {'opening_event_id': str(event_id)},
            'last_damage': 0,
            'current_event': 'opening_event.on_apply',
            'current_action': {'opening_event': str(event_id)},
        }
        result = run_v2_event(self, context, event_def)
        if isinstance(result, dict) and result.get('needs_v2_ui'):
            self._store_v2_ui_pause(result.get('v2_ui_pause') or {})
        return True

    def _start_draw_phase(self):
        self.phase = 'draw'
        for i in range(2):
            ps = self.players[i]
            ps.cards_played_this_turn = {}
            ps.cards_played_this_turn_instance_ids = []
            ps.magic_battery_m_this_turn = 0
            ps.custom_vars['\u9b54\u6cd5\u7535\u6c60\u672c\u56de\u5408\u56de\u9b54'] = 0
        self.log_msg(f"=== 第{self.round_num}回合 ===")
        self._apply_late_round_fire_pressure()
        if self.game_over:
            return
        self._start_player_turn(self.first_player)

    def _start_player_turn(self, player_id: int):
        self._reset_achievement_turn_stats(player_id)
        self.current_player = player_id
        ps = self.players[player_id]
        opp = self.players[1 - player_id]
        self._apply_turn_start_effects(player_id)
        if self.game_over:
            return
        if self.pending_choice is not None or getattr(self, 'pending_v2_ui', None):
            return
        if getattr(self, '_skip_current_turn_after_start', False):
            self._skip_current_turn_after_start = False
            self.log_msg(f"{self.pn(player_id)}被魔法珊瑚影响，跳过本回合行动")
            self._end_player_turn(player_id)
            return
        if ps.forced_skip_turn > 0:
            ps.forced_skip_turn -= 1
            self.log_msg(f"{self.pn(player_id)}被跳过本回合")
            self._end_player_turn(player_id)
            return
        if ps.skip_turn > 0 and self._is_status_immune(player_id):
            ps.skip_turn = max(0, int(ps.skip_turn) - 1)
        elif ps.skip_turn > 0:
            ps.skip_turn -= 1
            self.log_msg(f"{self.pn(player_id)}被眩晕，跳过本回合！")
            self._end_player_turn(player_id)
            return
        if ps.health <= 0:
            self._check_yggdrasil(player_id)
            if ps.health <= 0:
                self._check_game_over()
                return
        self._enter_player_action_phase(player_id)

    def _enter_player_action_phase(self, player_id: int):
        self.phase = 'action'
        self._run_ocean_auto_cards_turn_start(player_id)
        self._continue_honey_control_if_needed(player_id)

    def _first_auto_attack_target(self, player_id: int) -> int:
        if hasattr(self, 'get_enemies'):
            enemies = [eid for eid in self.get_enemies(player_id) if 0 <= eid < len(self.players) and self.players[eid].health > 0]
            if enemies:
                return min(enemies, key=lambda eid: (self.players[eid].health, eid))
        target = 1 - player_id
        return target if 0 <= target < len(self.players) and self.players[target].health > 0 else -1

    def _card_payable_now(self, player_id: int, card: CardInstance) -> bool:
        ps = self.players[player_id]
        extra_e = self._get_extra_e_for_card(player_id, card)
        return max(0, card.cost_e + extra_e) <= ps.elixir and card.cost_m <= ps.magic

    def _continue_honey_control_if_needed(self, player_id: int):
        if self.game_over or self.phase != 'action' or self.current_player != player_id:
            return
        if self.pending_response is not None or self.pending_choice is not None or getattr(self, 'pending_v2_ui', None):
            return
        ps = self.players[player_id]
        if int(getattr(ps, 'honey_control_turns', 0) or 0) <= 0:
            return
        if getattr(self, '_honey_control_running', False):
            return
        self._honey_control_running = True
        try:
            while (
                not self.game_over
                and self.phase == 'action'
                and self.current_player == player_id
                and self.pending_response is None
                and self.pending_choice is None
                and not getattr(self, 'pending_v2_ui', None)
                and int(getattr(ps, 'honey_control_turns', 0) or 0) > 0
            ):
                target_id = self._first_auto_attack_target(player_id)
                if target_id < 0:
                    break
                next_card = None
                for hand_card in list(ps.hand):
                    if hand_card.card_type == 'thorn' and self._card_payable_now(player_id, hand_card):
                        next_card = hand_card
                        break
                if next_card is None:
                    break
                self.log_msg(f"自动控制：{self.pn(player_id)}自动打出{next_card.name_cn}")
                auto_choice = {'target_player_id': target_id, 'target_player': target_id, 'target_id': target_id}
                if len(getattr(self, 'players', []) or []) > 2:
                    result = self.play_card(player_id, next_card.instance_id, target_player_id=target_id, choice=auto_choice)
                else:
                    result = self.play_card(player_id, next_card.instance_id, auto_choice)
                if not result.get('success'):
                    break
                if result.get('needs_response') or self.pending_response is not None or self.pending_choice is not None or getattr(self, 'pending_v2_ui', None):
                    return
            ps.honey_control_turns = 0
            try:
                ps.custom_vars.pop('void_puppeteer_damage_multiplier', None)
            except Exception:
                pass
            if not self.game_over and self.phase == 'action' and self.current_player == player_id:
                self.log_msg(f"自动控制结束：{self.pn(player_id)}自动结束回合")
                self._end_player_turn(player_id)
        finally:
            self._honey_control_running = False


    def _apply_jungle_turn_start_statuses(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        ps.custom_vars['electric_web_draw_damage'] = 0
        self._clear_electric_web_draw_records_for_target(player_id)
        self._set_custom_status_value(player_id, 'jungle:fragile', 0)
        self._set_custom_status_value(player_id, 'fragile', 0)
        immune = self._is_status_immune(player_id)
        shield_keys = ('jungle:shield', 'shield')
        shield = self._custom_status_value(player_id, *shield_keys)
        if shield > 0:
            self._set_custom_status_alias_group(player_id, 'jungle:shield', shield_keys, shield // 2)

    def _apply_jungle_turn_start_regen(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        immune = self._is_status_immune(player_id)
        heal_turn_keys = ('jungle:turn_heal_turns', 'turn_heal_turns')
        heal_power_keys = ('jungle:turn_heal_power', 'turn_heal_power')
        heal_turns = self._custom_status_value(player_id, *heal_turn_keys)
        heal_power = self._custom_status_value(player_id, *heal_power_keys)
        if heal_turns > 0 and heal_power > 0:
            if not immune:
                ps.heal(heal_power)
                self.log_msg(f"{self.pn(player_id)}的回合回复：+{heal_power}H")
            self._set_custom_status_alias_group(player_id, 'jungle:turn_heal_turns', heal_turn_keys, heal_turns - 1)
            if heal_turns - 1 <= 0:
                self._set_custom_status_alias_group(player_id, 'jungle:turn_heal_power', heal_power_keys, 0)
        magic_turn_keys = ('jungle:turn_magic_turns', 'turn_magic_turns')
        magic_power_keys = ('jungle:turn_magic_power', 'turn_magic_power')
        magic_turns = self._custom_status_value(player_id, *magic_turn_keys)
        magic_power = self._custom_status_value(player_id, *magic_power_keys)
        if magic_turns > 0 and magic_power > 0:
            if not immune:
                ps.gain_magic(magic_power)
                self.log_msg(f"{self.pn(player_id)}的魔力回合回复：+{magic_power}M")
            self._set_custom_status_alias_group(player_id, 'jungle:turn_magic_turns', magic_turn_keys, magic_turns - 1)
            if magic_turns - 1 <= 0:
                self._set_custom_status_alias_group(player_id, 'jungle:turn_magic_power', magic_power_keys, 0)

    def _apply_electric_web_draw_damage(self, player_id: int, drawn_count: int):
        if not (0 <= player_id < len(self.players)):
            return
        per_card = int(self.players[player_id].custom_vars.get('electric_web_draw_damage', 0) or 0)
        count = max(0, int(drawn_count or 0))
        if per_card <= 0 or count <= 0:
            return
        total = per_card * count
        self._deal_direct_damage(player_id, total, '电网', damage_type=DAMAGE_TYPE_MAGIC, damage_tag='factory:electric_web')

    def _atomic_electric_web_arm(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        if not (0 <= target_id < len(self.players)):
            return
        amount = self._eval_int(player_id, params.get('amount', 2), card, 2)
        amount = max(0, amount)
        self.players[target_id].custom_vars['electric_web_draw_damage'] = (
            int(self.players[target_id].custom_vars.get('electric_web_draw_damage', 0) or 0)
            + amount
        )
        eq = self._find_equipment_for_card(player_id, card)
        if eq is not None:
            eq.custom_vars['electric_web_armed_target'] = target_id
            eq.custom_vars['electric_web_armed_amount'] = (
                int(eq.custom_vars.get('electric_web_armed_amount', 0) or 0) + amount
            )

    def _cleanup_electric_web_draw_damage(self, eq: EquipmentInstance) -> None:
        if eq is None:
            return
        try:
            target_id = int((getattr(eq, 'custom_vars', {}) or {}).get('electric_web_armed_target', -1))
            amount = int((getattr(eq, 'custom_vars', {}) or {}).get('electric_web_armed_amount', 0) or 0)
        except Exception:
            target_id = -1
            amount = 0
        if amount > 0 and 0 <= target_id < len(self.players):
            current = int(self.players[target_id].custom_vars.get('electric_web_draw_damage', 0) or 0)
            self.players[target_id].custom_vars['electric_web_draw_damage'] = max(0, current - amount)
        if hasattr(eq, 'custom_vars'):
            eq.custom_vars['electric_web_armed_target'] = -1
            eq.custom_vars['electric_web_armed_amount'] = 0

    def _clear_electric_web_draw_records_for_target(self, target_id: int) -> None:
        if not (0 <= target_id < len(self.players)):
            return
        for ps in self.players:
            for eq in getattr(ps, 'equipment', []) or []:
                if not self._equipment_is(eq, 'ElectricWeb', 'factory:electricweb'):
                    continue
                try:
                    armed_target = int((getattr(eq, 'custom_vars', {}) or {}).get('electric_web_armed_target', -1))
                except Exception:
                    armed_target = -1
                if armed_target == target_id:
                    eq.custom_vars['electric_web_armed_target'] = -1
                    eq.custom_vars['electric_web_armed_amount'] = 0

    def _deal_direct_damage(self, player_id: int, amount: int, source: str = '', source_id: int = None,
                            damage_type: Optional[str] = None, damage_tag: Optional[str] = None):
        if not isinstance(player_id, int):
            try:
                player_id = int(player_id)
            except Exception:
                return 0
        if not (0 <= player_id < len(self.players)):
            return 0
        ps = self.players[player_id]
        if ps.invincible and not self._is_status_immune(player_id):
            self.log_msg(f"{self.pn(player_id)}无敌，免疫{source}伤害！")
            return 0
        actual = amount
        resolved_damage_type = infer_damage_type(source, 'direct', damage_tag or '', damage_type)
        resolved_damage_tag = damage_tag or (status_damage_tag(source) if resolved_damage_type == DAMAGE_TYPE_MAGIC else DAMAGE_TAG_DIRECT)
        if str(resolved_damage_tag).strip() in (DAMAGE_TAG_POISON, DAMAGE_TAG_FIRE, 'poison', '中毒', 'fire', 'burn', '灼烧') and self._is_status_immune(player_id):
            return 0
        actual = self._apply_corruption_multiplier_to_damage(actual)
        actual = self._apply_damage_dealt_equipment_multiplier(
            actual,
            source_id,
            include_flat_bonus=(resolved_damage_type == DAMAGE_TYPE_PHYSICAL and resolved_damage_tag == DAMAGE_TAG_PHYSICAL),
        )
        damage_context = self._v2_damage_context(
            player_id,
            actual,
            source_id,
            damage_kind='direct',
            damage_tag=resolved_damage_tag,
            source=source,
            damage_type=resolved_damage_type,
        )
        actual = self._run_v2_damage_modifiers(damage_context, actual)
        if getattr(self, 'pending_v2_ui', None):
            return 0
        if actual <= 0:
            return 0
        actual = self._apply_universal_damage_shields(player_id, actual, source_id, source, resolved_damage_type)
        if actual <= 0:
            return 0
        old_health = ps.health
        ps.health -= actual
        self._note_achievement_health(player_id)
        self._record_damage(player_id, actual, source_id)
        self.log_msg(f"{self.pn(player_id)}受到{actual}点{source}伤害（H={old_health}→{ps.health}）")
        self._run_v2_after_damage_hooks(damage_context, actual)
        if not getattr(self, '_defer_turn_start_death_checks', False):
            self._check_yggdrasil(player_id)
            self._check_game_over()
        return actual

    def _custom_status_value(self, player_id: int, *names: str) -> int:
        if not (0 <= player_id < len(self.players)):
            return 0
        statuses = getattr(self.players[player_id], 'custom_statuses', {}) or {}
        total = 0
        for name in names:
            try:
                total += int(statuses.get(name, 0) or 0)
            except Exception:
                pass
        return total

    def _nazar_status_value(self, player_id: int) -> int:
        if not (0 <= player_id < len(self.players)):
            return 0
        ps = self.players[player_id]
        value = self._custom_status_value(player_id, 'nazar', '邪眼', 'Nazar')
        if getattr(ps, 'nazar_active', False):
            # Backward compatibility for old rooms/replays: nazar_big_hits used
            # to count consumed big hits out of two.
            value += max(0, 2 - int(getattr(ps, 'nazar_big_hits', 0) or 0))
        return max(0, int(value or 0))

    def _set_nazar_status_value(self, player_id: int, value: int):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        ps.nazar_active = False
        ps.nazar_big_hits = 0
        for key in ('邪眼', 'Nazar'):
            self._set_custom_status_value(player_id, key, 0)
        self._set_custom_status_value(player_id, 'nazar', max(0, int(value or 0)))

    def _add_nazar_status_value(self, player_id: int, amount: int):
        self._set_nazar_status_value(player_id, self._nazar_status_value(player_id) + int(amount or 0))

    def _set_custom_status_value(self, player_id: int, name: str, value: int):
        if not (0 <= player_id < len(self.players)):
            return
        statuses = getattr(self.players[player_id], 'custom_statuses', {}) or {}
        value = int(value or 0)
        if value <= 0:
            statuses.pop(name, None)
        else:
            statuses[name] = value
        self.players[player_id].custom_statuses = statuses
        self._note_achievement_status_peak(player_id)

    def _add_custom_status_value(self, player_id: int, name: str, amount: int):
        self._set_custom_status_value(player_id, name, self._custom_status_value(player_id, name) + int(amount or 0))

    def _set_custom_status_alias_group(self, player_id: int, primary: str, aliases: tuple, value: int):
        for name in aliases:
            if name != primary:
                self._set_custom_status_value(player_id, name, 0)
        self._set_custom_status_value(player_id, primary, value)

    def _hel_luck_keys(self) -> tuple:
        return ('hel:luck', 'luck', '幸运')

    def _hel_blazing_fire_keys(self) -> tuple:
        return ('hel:blazing_fire', 'blazing_fire', '烈火')

    def _hel_luck_value(self, player_id: int) -> int:
        if self._is_status_immune(player_id):
            return 0
        return self._custom_status_value(player_id, *self._hel_luck_keys())

    def _hel_set_luck_value(self, player_id: int, value: int):
        self._set_custom_status_alias_group(player_id, 'hel:luck', self._hel_luck_keys(), max(0, int(value or 0)))

    def _hel_add_luck_value(self, player_id: int, amount: int):
        self._hel_set_luck_value(player_id, self._custom_status_value(player_id, *self._hel_luck_keys()) + int(amount or 0))

    def _hel_crit_multiplier(self, player_id: int) -> float:
        if not self._valid_player_id(player_id):
            return 1.5
        vars_dict = getattr(self.players[player_id], 'custom_vars', {}) or {}
        try:
            perm = float(vars_dict.get('hel_crit_multiplier_bonus', 0) or 0)
        except Exception:
            perm = 0.0
        try:
            turn = float(vars_dict.get('hel_crit_multiplier_turn_bonus', 0) or 0)
        except Exception:
            turn = 0.0
        equipment = 0.0
        try:
            equipment = 0.5 * sum(
                1
                for _, eq in self._iter_equipment_targeting_player(player_id)
                if self._equipment_is(eq, 'Clover', 'hel:clover')
            )
        except Exception:
            equipment = 0.0
        return max(0.0, 1.5 + perm + equipment + turn)

    def _hel_sync_crit_multiplier_display(self, player_id: int):
        if not self._valid_player_id(player_id):
            return
        value = self._hel_crit_multiplier(player_id)
        vars_dict = getattr(self.players[player_id], 'custom_vars', {}) or {}
        if abs(value - 1.5) > 0.001:
            vars_dict['hel_crit_multiplier'] = round(value, 2)
        else:
            vars_dict.pop('hel_crit_multiplier', None)
        self.players[player_id].custom_vars = vars_dict

    def _hel_apply_lucky_crit_to_damage(self, attacker_id: int, dmg: int, source_card: Optional[CardInstance]) -> tuple:
        if dmg <= 0 or not self._valid_player_id(attacker_id):
            return max(0, int(dmg or 0)), False
        if source_card is None:
            return max(0, int(dmg or 0)), False
        flags = self._effective_card_flags(source_card)
        force = bool(getattr(source_card, '_hel_force_crit', False))
        no_luck = bool(getattr(source_card, '_hel_no_luck_crit', False))
        luck = self._hel_luck_value(attacker_id)
        crit = force or (not no_luck and luck >= dmg)
        if not crit:
            return max(0, int(dmg or 0)), False
        if not force:
            self._hel_set_luck_value(attacker_id, luck - dmg)
        multiplier = self._hel_crit_multiplier(attacker_id)
        crit_damage = int(math.ceil(max(0, dmg) * multiplier))
        if 'hel:dice' in (getattr(source_card, 'def_id', ''), getattr(source_card, 'runtime_id', '')) or getattr(source_card, 'def_id', '') == 'Dice':
            crit_damage += 3
        if getattr(source_card, '_hel_card_suit', '') == 'diamond':
            crit_damage += 6
        if 'hel:domino' in (getattr(source_card, 'def_id', ''), getattr(source_card, 'runtime_id', '')) or getattr(source_card, 'def_id', '') == 'Domino':
            crit_damage = int(math.ceil(crit_damage * 2))
            source_card.instance_flags.add('precision')
        try:
            self._hel_current_crit_hits = int(getattr(self, '_hel_current_crit_hits', 0) or 0) + 1
            self._hel_last_hit_was_crit = True
        except Exception:
            pass
        return crit_damage, True

    def _hel_apply_blazing_fire_turn_start(self, player_id: int):
        stacks = self._custom_status_value(player_id, *self._hel_blazing_fire_keys())
        if stacks <= 0 or self._is_status_immune(player_id):
            return
        self.players[player_id].fire += stacks
        self._normalize_status_value(self.players[player_id], 'fire')
        self._note_achievement_status_peak(player_id)
        self.log_msg(f"{self.pn(player_id)}的烈火施加{stacks}层灼烧")

    def _unable_counter_keys(self) -> tuple:
        return ('ocean:unable_counter', 'unable_counter', '无法反制')

    def _is_counter_card(self, card: Optional[CardInstance]) -> bool:
        if card is None:
            return False
        return getattr(card, 'card_type', '') == 'guard' or bool(getattr(card.card_def, 'response_trigger', '') or '')

    def _unable_counter_value(self, player_id: int) -> int:
        if self._is_status_immune(player_id):
            return 0
        return self._custom_status_value(player_id, *self._unable_counter_keys())

    def _set_unable_counter_value(self, player_id: int, value: int):
        self._set_custom_status_alias_group(player_id, 'ocean:unable_counter', self._unable_counter_keys(), max(0, int(value or 0)))

    def _apply_unable_counter_to_entering_card(self, player_id: int, card: CardInstance) -> bool:
        stacks = self._unable_counter_value(player_id)
        if stacks <= 0 or not self._is_counter_card(card):
            return False
        ps = self.players[player_id]
        if card not in ps.hand:
            return False
        ps.hand.remove(card)
        self._discard_card(ps, card)
        self._set_unable_counter_value(player_id, stacks - 1)
        self.log_msg(f"{self.pn(player_id)}因无法反制将{card.name_cn}置入弃牌堆")
        return True

    def _apply_unable_counter_to_current_hand(self, player_id: int):
        stacks = self._unable_counter_value(player_id)
        if stacks <= 0:
            return
        ps = self.players[player_id]
        discarded = 0
        for card in list(ps.hand):
            if stacks <= 0:
                break
            if not self._is_counter_card(card):
                continue
            ps.hand.remove(card)
            self._discard_card(ps, card)
            discarded += 1
            stacks -= 1
        if discarded:
            self._set_unable_counter_value(player_id, stacks)
            self.log_msg(f"{self.pn(player_id)}因无法反制将{discarded}张反制牌置入弃牌堆")

    def _action_limit_status_value(self, player_id: int, attr: str, *aliases: str) -> int:
        if not (0 <= player_id < len(self.players)) or self._is_status_immune(player_id):
            return 0
        ps = self.players[player_id]
        return max(int(getattr(ps, attr, 0) or 0), self._custom_status_value(player_id, *aliases))

    def _decay_action_limit_status(self, player_id: int, attr: str, *aliases: str):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        value = int(getattr(ps, attr, 0) or 0)
        if value > 0:
            setattr(ps, attr, max(0, value - 1))
        for name in aliases:
            current = self._custom_status_value(player_id, name)
            if current > 0:
                self._set_custom_status_value(player_id, name, current - 1)

    def _merge_turn_regen_status(self, player_id: int, kind: str, turns: int, power: int):
        if not (0 <= player_id < len(self.players)):
            return (0, 0)
        turns = max(0, int(turns or 0))
        power = max(0, int(power or 0))
        if kind == 'magic':
            turns_key = 'jungle:turn_magic_turns'
            power_key = 'jungle:turn_magic_power'
        else:
            turns_key = 'jungle:turn_heal_turns'
            power_key = 'jungle:turn_heal_power'
        merged_turns = self._custom_status_value(player_id, turns_key) + turns
        merged_power = max(self._custom_status_value(player_id, power_key), power)
        self._set_custom_status_value(player_id, turns_key, merged_turns)
        self._set_custom_status_value(player_id, power_key, merged_power)
        return (merged_turns, merged_power)

    def _apply_universal_damage_shields(self, target_id: int, damage: int, source_id: Optional[int], source: str, damage_type: str) -> int:
        if damage <= 0 or not (0 <= target_id < len(self.players)):
            return max(0, int(damage or 0))
        ps = self.players[target_id]
        if source != '遗物转移' and self._has_equipment(target_id, 'Relic') and hasattr(self, 'get_teammate'):
            try:
                mate_id = self.get_teammate(target_id)
            except Exception:
                mate_id = -1
            if 0 <= mate_id < len(self.players) and self.players[mate_id].health > 0:
                transfer = int(math.floor(damage * 2 / 3))
                kept = int(math.floor(damage / 3))
                if transfer > 0:
                    self.log_msg(f"{self.pn(target_id)}的遗物将{transfer}点伤害转给{self.pn(mate_id)}")
                    self._deal_direct_damage(mate_id, transfer, source or '遗物转移', target_id, damage_type=damage_type, damage_tag=DAMAGE_TAG_DIRECT)
                damage = max(0, kept)
        shield_keys = ('jungle:shield', 'shield')
        shield = self._custom_status_value(target_id, *shield_keys)
        if shield > 0 and not self._is_status_immune(target_id):
            blocked = min(shield, damage)
            damage -= blocked
            self._set_custom_status_alias_group(target_id, 'jungle:shield', shield_keys, shield - blocked)
            self.log_msg(f"{self.pn(target_id)}的护盾抵扣{blocked}点伤害")
        if damage > 0 and self._has_equipment(target_id, 'MagicCotton'):
            magic = max(0, int(getattr(ps, 'magic', 0) or 0))
            if magic > 0:
                spent = min(magic, int(math.ceil(damage / 4)))
                blocked = min(damage, spent * 4)
                ps.magic -= spent
                damage -= blocked
                self.log_msg(f"{self.pn(target_id)}的魔法棉花消耗{spent}M抵扣{blocked}点伤害")
        return max(0, int(damage))

    def _has_equipment(self, player_id: int, *def_ids: str) -> bool:
        if not (0 <= player_id < len(self.players)):
            return False
        for owner_id, owner_state in enumerate(self.players):
            for eq in getattr(owner_state, 'equipment', []) or []:
                try:
                    effect_target = int(getattr(eq, 'effect_target', owner_id))
                except Exception:
                    effect_target = owner_id
                if effect_target != player_id:
                    continue
                if self._card_is(getattr(eq, 'card_instance', None), *def_ids) or self._card_is(getattr(eq, 'card_def', None), *def_ids):
                    return True
        return False


    def _get_corruption_count(self) -> int:
        count = 0
        for ps in self.players:
            for eq in ps.equipment:
                if eq.def_id == 'Corruption' and eq.corruption_active:
                    count += 1
        return count

    def _get_corruption_multiplier(self) -> float:
        return CORRUPTION_DAMAGE_MULTIPLIER ** max(0, self._get_corruption_count())

    def _format_damage_multiplier(self, value: float) -> str:
        text = f"{float(value):.4f}".rstrip('0').rstrip('.')
        return text or '1'

    def _apply_corruption_multiplier_to_damage(self, amount, log: bool = True) -> int:
        multiplier = self._get_corruption_multiplier()
        if multiplier <= 1:
            return int(amount)
        result = int(math.ceil(float(amount) * multiplier))
        if log:
            self.log_msg(f"腐化效果：伤害x{self._format_damage_multiplier(multiplier)}")
        return result

    def _damage_dealt_equipment_multiplier(self, source_id: Optional[int]) -> float:
        try:
            source_id = int(source_id)
        except Exception:
            return 1.0
        if not (0 <= source_id < len(self.players)):
            return 1.0
        count = 0
        for owner_state in self.players:
            for eq in getattr(owner_state, 'equipment', []):
                eq_id = str(getattr(eq, 'def_id', '') or '').lower()
                effect_target = int(getattr(eq, 'effect_target', getattr(eq, 'owner', source_id)))
                if effect_target != source_id:
                    continue
                if eq_id == 'dizzy' or eq_id.endswith(':dizzy'):
                    count += 1
        return (1.0 + 0.5 * count) if count > 0 else 1.0

    def _damage_dealt_equipment_flat_bonus(self, source_id: Optional[int]) -> int:
        try:
            source_id = int(source_id)
        except Exception:
            return 0
        if not (0 <= source_id < len(self.players)):
            return 0
        bonus = 0
        for owner_state in self.players:
            for eq in getattr(owner_state, 'equipment', []):
                eq_id = str(getattr(eq, 'def_id', '') or '').lower()
                effect_target = int(getattr(eq, 'effect_target', getattr(eq, 'owner', source_id)))
                if effect_target != source_id:
                    continue
                if eq_id == 'cutter' or eq_id.endswith(':cutter'):
                    bonus += 2
        return bonus

    def _apply_damage_dealt_equipment_multiplier(self, amount: int, source_id: Optional[int], include_flat_bonus: bool = True) -> int:
        multiplier = self._damage_dealt_equipment_multiplier(source_id)
        amount = max(0, int(amount or 0))
        if multiplier > 1:
            amount = max(0, int(math.ceil(float(amount or 0) * multiplier)))
        if include_flat_bonus:
            amount += self._damage_dealt_equipment_flat_bonus(source_id)
        return amount

    def _apply_late_round_fire_pressure(self):
        if self.round_num < LATE_ROUND_FIRE_START:
            return
        applied = 0
        for ps in self.players:
            player_id = getattr(ps, 'player_id', -1)
            if ps.health > 0 and not self._status_application_blocked(player_id, 'fire'):
                ps.fire += 1
                applied += 1
        if applied:
            self.log_msg(f"第{self.round_num}回合开始，所有存活玩家+1灼烧")

    def _clear_yggdrasil_effects(self, player_id: int):
        ps = self.players[player_id]
        ps.poison = 0
        ps.fire = 0
        ps.toxic = 0
        ps.triangle_stacks = 0
        ps.dodge = 0
        ps.nazar_active = False
        ps.nazar_big_hits = 0
        ps.armor = 0
        ps.equipment_protection = 0
        ps.negate_next_skill = False
        ps.skip_turn = 0
        ps.damage_multiplier = 1.0
        ps.bandage_active = False
        ps.bandage_death_pending = False
        self._clear_invincible_state(player_id)
        try:
            ps.custom_statuses.clear()
        except Exception:
            pass
        try:
            ps.custom_vars['三角形层数'] = 0
        except Exception:
            pass

    def _trigger_yggdrasil_effect(self, target_id: int, card: Optional[CardInstance] = None,
                                  source_player_id: Optional[int] = None,
                                  exile_from_hand: bool = False,
                                  exile_played_card: bool = False) -> bool:
        if not (0 <= target_id < len(self.players)):
            return False
        ps = self.players[target_id]
        was_dead = ps.health <= 0
        actor_id = source_player_id if source_player_id is not None else target_id
        if was_dead and 0 <= actor_id < len(self.players):
            self.players[actor_id].achievement_yggdrasil_revived = True
        ps.health = 5
        self._note_achievement_health(target_id)
        self._clear_yggdrasil_effects(target_id)
        self._set_invincible_until_next_own_turn_end(target_id)
        drawn = self._draw_cards_with_v2_hooks(target_id, 3, 'yggdrasil')
        if card is not None:
            if exile_from_hand and card in ps.hand:
                ps.hand.remove(card)
                self._put_card_in_exile(ps.player_id, card)
            elif exile_played_card:
                card.instance_flags.add('exile')
        actor_text = ''
        if source_player_id is not None and source_player_id != target_id:
            actor_text = f"{self.pn(source_player_id)}的世界树之叶使"
        else:
            actor_text = f"{self.pn(target_id)}的世界树之叶"
        revive_text = '复活，' if was_dead else ''
        self.log_msg(f"{actor_text}{self.pn(target_id)}{revive_text}生命值设为5，抽{len(drawn)}张牌，清除所有效果，无敌直到下一个自己回合结束！")
        return True

    def _check_yggdrasil(self, player_id: int):
        ps = self.players[player_id]
        if ps.health <= 0 and self._yggdrasil_check:
            if ps.bandage_active and not self._is_status_immune(player_id):
                ps.health = 1
                self._note_achievement_health(player_id)
                self._set_invincible_until_next_own_turn_end(player_id)
                ps.bandage_active = False
                ps.bandage_death_pending = True
                self.log_msg(f"{self.pn(player_id)}的绷带发动！无敌直到下一个自己回合结束，然后死亡")
                self._check_game_over()
                return
            for card in ps.hand[:]:
                if card.def_id == 'Yggdrasil':
                    self._trigger_yggdrasil_effect(player_id, card, exile_from_hand=True)
                    self._check_game_over()
                    return
                if card.card_def and card.card_def.effects:
                    for effect in card.card_def.effects:
                        eff_type = effect if isinstance(effect, str) else effect.get('type', '')
                        if eff_type == 'on_fatal_set_health_exile':
                            params = effect.get('params', {}) if isinstance(effect, dict) else {}
                            log = effect.get('log', '') if isinstance(effect, dict) else ''
                            health_amount = params.get('health', 5)
                            self._trigger_yggdrasil_effect(player_id, card, exile_from_hand=True)
                            ps.health = health_amount
                            self._note_achievement_health(player_id)
                            self.log_msg(log or f"{self.pn(player_id)}的{card.name_cn}发动！清除己方所有效果，生命值设为{health_amount}，无敌直到下一个自己回合结束！")
                            self._check_game_over()
                            return

    def _check_game_over(self):
        if self._game_over_defer_depth > 0:
            return
        for i in range(2):
            if self.players[i].health <= 0:
                self._check_yggdrasil(i)
        if self.players[0].health <= 0 and self.players[1].health <= 0:
            self.game_over = True
            self.winner = -1
            self.phase = 'game_over'
            self.log_msg("双方生命值同时归零！平局！")
            return
        if self.game_over:
            return
        for i in range(2):
            if self.players[i].health <= 0:
                self.game_over = True
                self.winner = 1 - i
                self.phase = 'game_over'
                self.log_msg(f"{self.pn(i)}生命值归零！{self.pn(self.winner)}获胜！")
                return

    def surrender(self, player_id: int):
        if self.game_over:
            return {'success': False, 'error': '游戏已结束'}
        self.game_over = True
        self.winner = 1 - player_id
        self.phase = 'game_over'
        self.log_msg(f"{self.pn(player_id)}投降，{self.pn(self.winner)}获胜！")
        return {'success': True}

    def can_play_card(self, player_id: int, card: CardInstance) -> Tuple[bool, str]:
        ps = self.players[player_id]
        card_def = card.card_def
        if card_def.card_type == 'guard' and not self._has_script_entry(card_def, 'play') and not card_def.effects and not self._card_has_v2_event(card_def, 'on_play'):
            return False, "反制牌只能通过响应机制使用"
        auto_play_actor = getattr(self, '_allow_out_of_turn_auto_play_for', None)
        if self.phase != 'action' or (self.current_player != player_id and auto_play_actor != player_id):
            return False, "不是你的回合"
        immune = self._is_status_immune(player_id)
        if self._action_limit_status_value(player_id, 'attack_blocked', 'attack_blocked', '禁攻') > 0 and card_def.card_type == 'thorn' and not immune:
            return False, "本回合无法使用攻击牌"
        if self._action_limit_status_value(player_id, 'attack_only', 'attack_only', '仅攻击') > 0 and card_def.card_type != 'thorn' and not immune:
            return False, "本回合只能使用攻击牌"
        if self._action_limit_status_value(player_id, 'magic_blocked', 'magic_blocked', '魔力封锁') > 0 and card.cost_m > 0 and not immune:
            return False, "本回合无法使用带有魔力消耗的卡牌"
        if ps.shovel_active:
            return False, "链子效果中，无法使用卡牌"
        extra_e = self._get_extra_e_for_card(player_id, card)
        total_e = max(0, card.cost_e + extra_e)
        if total_e > ps.elixir:
            return False, f"能量不足（需要{total_e}E，当前{ps.elixir}E）"
        if card.cost_m > ps.magic:
            return False, f"魔力不足（需要{card.cost_m}M，当前{ps.magic}M）"
        return True, ""

    def _get_extra_e_for_card(self, player_id: int, card: CardInstance) -> int:
        ps = self.players[player_id]
        dup_count = self._cards_played_this_turn_count(ps, card)
        extra = 0 if 'symbiosis' in card.flags else dup_count
        if self._card_is(card, 'Bamboo', 'jungle:bamboo'):
            try:
                other_bamboo = sum(1 for c in ps.hand if c is not card and self._card_is(c, 'Bamboo', 'jungle:bamboo'))
            except Exception:
                other_bamboo = 0
            extra -= other_bamboo
        return extra

    def _card_local_id_values(self, card_or_def) -> Set[str]:
        values: Set[str] = set()
        if card_or_def is None:
            return values
        for value in (
            getattr(card_or_def, 'def_id', ''),
            getattr(card_or_def, 'id', ''),
            getattr(card_or_def, 'legacy_id', ''),
        ):
            if value:
                values.add(str(value))
        card_def = getattr(card_or_def, 'card_def', None)
        if card_def is not None and card_def is not card_or_def:
            values.update(self._card_local_id_values(card_def))
        resource = getattr(card_def or card_or_def, 'v2_resource', {}) or {}
        if isinstance(resource, dict):
            for key in ('id', 'legacy_id', 'runtime_id'):
                value = resource.get(key)
                if value:
                    values.add(str(value))
        return values

    def _cards_played_this_turn_count(self, ps: PlayerState, card: CardInstance) -> int:
        played = getattr(ps, 'cards_played_this_turn', {}) or {}
        ids = self._card_local_id_values(card)
        if not ids:
            ids = {str(getattr(card, 'def_id', '') or '')}
        total = 0
        for key in ids:
            try:
                total += int(played.get(key, 0) or 0)
            except Exception:
                continue
        return total

    def _card_is(self, card_or_def, *ids: str) -> bool:
        wanted = {str(item) for item in ids if item}
        if not wanted or card_or_def is None:
            return False
        def_id = str(getattr(card_or_def, 'def_id', getattr(card_or_def, 'id', '')) or '')
        if def_id in wanted:
            return True
        card_def = getattr(card_or_def, 'card_def', card_or_def)
        if str(getattr(card_def, 'id', '') or '') in wanted:
            return True
        resource = getattr(card_def, 'v2_resource', {}) or {}
        for key in ('legacy_id', 'id', 'runtime_id'):
            if str(resource.get(key, '') or '') in wanted:
                return True
        return False

    def _equipment_is(self, eq, *ids: str) -> bool:
        if eq is None:
            return False
        wanted = {str(item) for item in ids if item}
        wanted_lower = {item.lower() for item in wanted}
        values = [
            getattr(eq, 'def_id', ''),
            getattr(getattr(eq, 'card_instance', None), 'def_id', ''),
            getattr(getattr(eq, 'card_def', None), 'id', ''),
            getattr(getattr(eq, 'card_def', None), 'legacy_id', ''),
        ]
        resource = getattr(getattr(eq, 'card_def', None), 'v2_resource', {}) or {}
        values.extend([resource.get('id', ''), resource.get('legacy_id', ''), resource.get('runtime_id', '')])
        for value in values:
            text = str(value or '')
            if text in wanted or text.lower() in wanted_lower:
                return True
            tail = text.split(':')[-1]
            if tail in wanted or tail.lower() in wanted_lower:
                return True
        return self._card_is(getattr(eq, 'card_instance', None), *ids) or self._card_is(getattr(eq, 'card_def', None), *ids)

    def _mimic_special_cost_for_card(self, target: Optional[CardInstance]) -> int:
        if target is None:
            return 0
        try:
            fusion_extra = max(0, int(getattr(target, 'fusion_level', 1) or 1) - 1)
        except Exception:
            fusion_extra = 0
        try:
            fission_extra = max(0, int(getattr(target, 'fission_level', 1) or 1) - 1)
        except Exception:
            fission_extra = 0
        layered_extra = 0
        for attr in ('swift_value', 'magic_swift_value', 'power_value', 'bonus_damage', 'temp_swift_value', 'temp_heavy_value', 'temp_magic_heavy_value'):
            try:
                layered_extra += max(0, int(getattr(target, attr, 0) or 0))
            except Exception:
                pass
        return int(math.ceil((fusion_extra + fission_extra + layered_extra) / 2))

    def _can_pay_mimic_special_cost(self, player_id: int, target: Optional[CardInstance]) -> bool:
        if not (0 <= player_id < len(self.players)):
            return False
        cost = self._mimic_special_cost_for_card(target)
        return int(getattr(self.players[player_id], 'elixir', 0)) >= cost

    def _pay_mimic_special_cost(self, player_id: int, target: Optional[CardInstance], source_card: Optional[CardInstance] = None) -> bool:
        cost = self._mimic_special_cost_for_card(target)
        if cost <= 0:
            return True
        if not self._can_pay_mimic_special_cost(player_id, target):
            return False
        self._spend_resource(player_id, 'elixir', cost, source_card)
        return True

    def _make_mimic_copy_card(self, target: CardInstance) -> CardInstance:
        copy_card = target.copy()
        copy_card._mimic_copy = True

        def half_layer(value):
            try:
                layer = max(1, int(value or 1))
            except Exception:
                layer = 1
            return max(1, int(math.ceil(layer / 2)))

        copy_card.fusion_level = clamp_card_layer(half_layer(getattr(target, 'fusion_level', 1)))
        copy_card.fusion_multiplier = float(copy_card.fusion_level)
        copy_card.fission_level = clamp_card_layer(half_layer(getattr(target, 'fission_level', 1)))
        copy_card.fission_count = max(0, copy_card.fission_level - 1)
        for attr in ('swift_value', 'magic_swift_value', 'power_value', 'bonus_damage', 'temp_swift_value', 'temp_heavy_value', 'temp_magic_heavy_value'):
            try:
                setattr(copy_card, attr, int(math.ceil(max(0, int(getattr(target, attr, 0) or 0)) / 2)))
            except Exception:
                setattr(copy_card, attr, 0)
        if getattr(copy_card, 'swift_value', 0) > 0:
            copy_card.instance_flags.add('swift')
        if getattr(copy_card, 'magic_swift_value', 0) > 0:
            copy_card.instance_flags.add('magic_swift')
        if getattr(copy_card, 'power_value', 0) > 0:
            copy_card.instance_flags.add('power')
        if getattr(copy_card, 'temp_swift_value', 0) > 0:
            copy_card.instance_flags.add('temp_swift')
        if getattr(copy_card, 'temp_heavy_value', 0) > 0:
            copy_card.instance_flags.add('temp_heavy')
        if getattr(copy_card, 'temp_magic_heavy_value', 0) > 0:
            copy_card.instance_flags.add('temp_magic_heavy')
        return copy_card

    def _enforce_unique_cards_for_player(self, player_id: int, preferred_card: Optional[CardInstance] = None):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        zones = (ps.hand, ps.deck, ps.discard)
        grouped = {}
        for zone in zones:
            for card in list(zone):
                if 'unique' in self._effective_card_flags(card):
                    grouped.setdefault(card.def_id, []).append((zone, card))
        for def_id, entries in grouped.items():
            if len(entries) <= 1:
                continue
            preferred_entry = None
            if preferred_card is not None:
                for entry in entries:
                    if entry[1] is preferred_card or entry[1].instance_id == preferred_card.instance_id:
                        preferred_entry = entry
                        break
            keep_zone, keep_card = preferred_entry or random.choice(entries)
            for zone, card in entries:
                if card is keep_card or card.instance_id == keep_card.instance_id:
                    continue
                if card in zone:
                    zone.remove(card)
                self._put_card_in_exile(ps.player_id, card)
                self.log_msg(f"{self.pn(player_id)}的唯一牌{card.name_cn}多余副本被放逐")

    def _enforce_unique_cards_for_all(self):
        for pid in range(len(self.players)):
            self._enforce_unique_cards_for_player(pid)

    def _refund_pending_choice_cost(self, player_id: int, card: CardInstance):
        ps = self.players[player_id]
        played_count = ps.cards_played_this_turn.get(card.def_id, 1)
        paid_e = max(0, int(getattr(card, '_paid_e_this_play', 0) or 0))
        ps.elixir += paid_e
        ps.magic += card.cost_m
        remaining_count = max(0, played_count - 1)
        if remaining_count > 0:
            ps.cards_played_this_turn[card.def_id] = remaining_count
        else:
            ps.cards_played_this_turn.pop(card.def_id, None)
        instance_id = int(getattr(card, 'instance_id', 0) or 0)
        if instance_id:
            played_ids = getattr(ps, 'cards_played_this_turn_instance_ids', None)
            if isinstance(played_ids, list):
                for idx in range(len(played_ids) - 1, -1, -1):
                    if int(played_ids[idx] or 0) == instance_id:
                        del played_ids[idx]
                        break

    def _undo_magic_acceleration_after_pending_choice(self, player_id: int, card: Optional[CardInstance] = None):
        ps = self.players[player_id]
        if int(getattr(ps, 'custom_vars', {}).get('setup_magic_acceleration', 0) or 0) <= 0:
            return
        if card is not None and int(getattr(card, 'cost_m', 0) or 0) > 0:
            return
        msg = f"{self.pn(player_id)}【魔力加速】：+1M"
        for idx in range(len(self.log) - 1, -1, -1):
            if self.log[idx] == msg:
                del self.log[idx]
                if ps.magic > 0:
                    ps.magic -= 1
                return

    def _remove_pending_choice_play_log(self, player_id: int, card: CardInstance, play_log_marker: Optional[int] = None):
        if play_log_marker is None:
            return
        expected_play_log = f"{self.pn(player_id)}使用了{card.name_cn}"
        if 0 <= play_log_marker < len(self.log) and str(self.log[play_log_marker]).startswith(expected_play_log):
            del self.log[play_log_marker]

    def _undo_pending_choice_play_side_effects(
        self,
        player_id: int,
        card: CardInstance,
        play_log_marker: Optional[int] = None,
        restore_to_hand: bool = True,
    ):
        ps = self.players[player_id]
        self._remove_pending_choice_play_log(player_id, card, play_log_marker)
        self._undo_magic_acceleration_after_pending_choice(player_id, card)
        if restore_to_hand and ps.find_hand_card(card.instance_id) is None:
            ps.hand.insert(0, card)
        self._refund_pending_choice_cost(player_id, card)

    def _choice_target_from_choice(self, choice: Optional[dict], default: int = -1) -> int:
        if not isinstance(choice, dict):
            return default
        for key in ('target_player', 'target_player_id', 'target_id'):
            if key in choice:
                try:
                    return int(choice.get(key))
                except Exception:
                    return default
        return default

    def _target_can_be_selected(self, player_id: int, target_id: int, allow_self: bool = True,
                                alive_required: bool = True) -> bool:
        if not (0 <= target_id < len(self.players)):
            return False
        if target_id == player_id:
            return bool(allow_self)
        target = self.players[target_id]
        untargetable_active = bool(getattr(target, 'untargetable', False)) and not self._is_status_immune(target_id)
        return (target.health > 0 or not alive_required) and not untargetable_active

    def _choice_request_satisfied(self, effect: Optional[dict], choice: Optional[dict], card: Optional[CardInstance] = None) -> bool:
        if not isinstance(effect, dict):
            return True
        effect_type = self._effect_type(effect)
        params = self._effect_params(effect)
        choice_type = self._choice_type_for_effect(effect, card)
        if choice_type in ('choose_card_from_hand', 'choose_cards_from_hand', 'choose_card_to_discard'):
            current_iid = getattr(card, 'instance_id', None)
            owner_id, _, _ = self._find_card_location(card)
            owner = self.players[owner_id] if owner_id is not None and 0 <= owner_id < len(self.players) else None
            eligible = [
                hand_card for hand_card in getattr(owner, 'hand', [])
                if getattr(hand_card, 'instance_id', None) != current_iid
            ]
            if not eligible and params.get('continue_on_cancel'):
                return True
        if not isinstance(choice, dict):
            return False
        if choice.get('cancelled') and params.get('continue_on_cancel'):
            return True
        if effect_type == 'request_target' or choice_type == 'choose_target':
            return self._choice_target_from_choice(choice) >= 0
        if effect_type == 'request_confirm' or choice_type == 'confirm':
            return any(key in choice for key in ('confirmed', 'accepted'))
        current_iid = getattr(card, 'instance_id', None)
        if current_iid is not None:
            if choice.get('target_instance_id') == current_iid:
                return False
            ids = choice.get('target_instance_ids')
            if isinstance(ids, list) and current_iid in ids:
                return False
        if choice_type == 'choose_same_attacks_from_hand':
            ids = choice.get('target_instance_ids')
            return isinstance(ids, list) and bool(ids)
        if choice_type == 'choose_cards_from_hand':
            ids = choice.get('target_instance_ids')
            if isinstance(ids, list) and bool(ids):
                return True
            min_count = self._eval_int(0, params.get('min_count', 1), card, 1) if params else 1
            max_count = self._eval_int(0, params.get('max_count', min_count), card, min_count) if params else 1
            if min_count <= 0 and isinstance(ids, list):
                return True
            if min_count <= 1 and max_count <= 1 and choice.get('target_instance_id') is not None:
                return True
            return False
        if choice_type == 'choose_ocean_sapphire':
            return self._choice_target_from_choice(choice) >= 0 and choice.get('target_instance_id') is not None
        if choice_type in ('choose_card_from_discard',):
            return choice.get('target_def_id') is not None or choice.get('target_instance_id') is not None
        if choice_type in (
            'choose_attack_from_hand', 'choose_card_from_hand', 'choose_card_to_discard',
            'choose_from_deck', 'choose_from_discard', 'choose_from_exile',
            'choose_equipment', 'choose_enemy_equipment', 'choose_from_enemy_hand',
        ):
            return choice.get('target_instance_id') is not None or choice.get('target_def_id') is not None
        return bool(choice)

    def _choice_type_for_effect(self, effect: Optional[dict], card: Optional[CardInstance] = None) -> str:
        if not isinstance(effect, dict):
            return ''
        effect_type = self._effect_type(effect)
        params = self._effect_params(effect)
        if params.get('choice_type'):
            return str(params.get('choice_type'))
        if effect_type == 'request_target':
            return 'choose_target'
        if effect_type == 'request_card':
            if params.get('multi') or params.get('choice_type') == 'choose_cards_from_hand':
                return 'choose_cards_from_hand'
            zone = str(params.get('zone') or '').strip()
            if zone == 'deck':
                return 'choose_from_deck'
            if zone == 'discard':
                return 'choose_from_discard'
            if zone == 'exile':
                return 'choose_from_exile'
            if zone == 'equipment':
                return 'choose_equipment'
            return 'choose_card_from_hand'
        if effect_type == 'request_confirm':
            return 'confirm'
        if effect_type == 'discard_choice_then_draw':
            return 'choose_card_to_discard'
        if effect_type == 'destroy_equipment_choice_or_first':
            return 'choose_enemy_equipment'
        if effect_type == 'choose_from_deck':
            return 'choose_from_deck'
        if effect_type == 'choose_from_discard':
            return 'choose_from_discard'
        if effect_type == 'steal_enemy_card':
            return 'choose_from_enemy_hand'
        return ''

    def _choice_target_id_for_request(self, player_id: int, effect: Optional[dict]) -> Optional[int]:
        if not isinstance(effect, dict):
            return None
        request_type = self._effect_type(effect)
        params = self._effect_params(effect)
        selected_target = self._selected_choice_target(-1)
        if request_type == 'steal_enemy_card' and selected_target >= 0:
            return selected_target
        target_defaults = {
            'request_card': 'self',
            'choose_from_deck': 'self',
            'choose_from_discard': 'self',
            'destroy_equipment_choice_or_first': 'enemy',
            'steal_enemy_card': 'enemy',
        }
        if request_type not in target_defaults:
            return None
        return self._resolve_target(player_id, params.get('target', target_defaults[request_type]))

    def _default_auto_target_choice(self, player_id: int, allow_self: bool = True) -> int:
        enemy_id = self._first_auto_attack_target(player_id)
        if enemy_id >= 0:
            return enemy_id
        candidates = []
        for tid in range(len(self.players)):
            if self._target_can_be_selected(player_id, tid, allow_self=allow_self):
                candidates.append(tid)
        return candidates[0] if candidates else -1

    def _first_selectable_card_from_zone(self, player_id: int, target_id: int, zone_name: str, card: Optional[CardInstance] = None) -> Optional[CardInstance]:
        if not self._valid_player_id(target_id):
            return None
        ps = self.players[target_id]
        if zone_name == 'deck':
            zone = ps.deck
        elif zone_name == 'discard':
            zone = ps.discard
        elif zone_name == 'exile':
            zone = ps.exile
        else:
            zone = ps.hand
        current_iid = getattr(card, 'instance_id', None)
        for candidate in list(zone):
            if getattr(candidate, 'instance_id', None) == current_iid:
                continue
            if self._card_selectable_by_action(candidate):
                return candidate
        return None

    def _default_choice_for_pending(self, pending: Optional[dict]) -> Optional[dict]:
        if not isinstance(pending, dict):
            return None
        player_id = int(pending.get('player_id', 0) or 0)
        choice_type = str(pending.get('choice_type', '') or '')
        params = pending.get('choice_params') if isinstance(pending.get('choice_params'), dict) else {}
        card_data = pending.get('card')
        card = CardInstance.from_dict(card_data) if isinstance(card_data, dict) else None
        target_id = pending.get('target_player_id')
        if target_id is None:
            target_id = self._default_auto_target_choice(player_id, allow_self=True)
        try:
            target_id = int(target_id)
        except Exception:
            target_id = -1
        choice: dict = {}
        if target_id >= 0:
            choice.update({'target_player_id': target_id, 'target_player': target_id, 'target_id': target_id})
        if choice_type in ('choose_target',):
            chosen_target = self._default_auto_target_choice(player_id, allow_self=True)
            return {'target_player_id': chosen_target, 'target_player': chosen_target, 'target_id': chosen_target} if chosen_target >= 0 else None
        if choice_type in ('confirm',):
            return {'confirmed': True, 'accepted': True, **choice}
        if choice_type == 'hel_card_suit':
            return {'hel_suit': random.choice(['heart', 'diamond', 'spade', 'club']), **choice}
        if choice_type == 'choose_ocean_sapphire':
            chosen_target = self._default_auto_target_choice(player_id, allow_self=False)
            selected = self._first_selectable_card_from_zone(player_id, player_id, 'hand', card)
            selected = selected if selected and getattr(selected, 'card_type', '') == 'thorn' else None
            return {'target_player_id': chosen_target, 'target_player': chosen_target, 'target_id': chosen_target, 'target_instance_id': getattr(selected, 'instance_id', None)} if chosen_target >= 0 and selected else None
        if choice_type in ('choose_cards_from_hand', 'choose_same_attacks_from_hand'):
            owner_id = player_id
            current_iid = getattr(card, 'instance_id', None)
            max_count = max(1, self._eval_int(player_id, params.get('max_count', params.get('count', 1)), card, 1))
            if choice_type == 'choose_same_attacks_from_hand':
                cards = [c for c in self.players[owner_id].hand if getattr(c, 'instance_id', None) != current_iid and getattr(c, 'card_type', '') == 'thorn' and self._card_selectable_by_action(c)]
            else:
                cards = [c for c in self.players[owner_id].hand if getattr(c, 'instance_id', None) != current_iid and self._card_selectable_by_action(c)]
            ids = [getattr(c, 'instance_id', None) for c in cards[:max_count] if getattr(c, 'instance_id', None) is not None]
            return {'target_instance_ids': ids, **choice}
        zone_for_choice = {
            'choose_attack_from_hand': 'hand',
            'choose_card_from_hand': 'hand',
            'choose_card_to_discard': 'hand',
            'choose_from_enemy_hand': 'hand',
            'choose_from_deck': 'deck',
            'choose_from_discard': 'discard',
            'choose_from_exile': 'exile',
        }.get(choice_type)
        if zone_for_choice:
            owner_id = target_id if choice_type in ('choose_from_enemy_hand', 'choose_card_from_hand', 'choose_from_deck', 'choose_from_discard', 'choose_from_exile') and target_id >= 0 else player_id
            selected = self._first_selectable_card_from_zone(player_id, owner_id, zone_for_choice, card)
            if choice_type == 'choose_attack_from_hand' and selected and getattr(selected, 'card_type', '') != 'thorn':
                selected = next((c for c in self.players[owner_id].hand if getattr(c, 'card_type', '') == 'thorn' and self._card_selectable_by_action(c)), None)
            return {'target_instance_id': getattr(selected, 'instance_id', None), **choice} if selected else None
        if choice_type in ('choose_equipment', 'choose_enemy_equipment'):
            owner_id = target_id if choice_type == 'choose_enemy_equipment' and target_id >= 0 else player_id
            if not self._valid_player_id(owner_id):
                return None
            eq = next((eq for eq in self.players[owner_id].equipment if getattr(eq, 'card_instance', None) is not None), None)
            return {'target_instance_id': getattr(getattr(eq, 'card_instance', None), 'instance_id', None), **choice} if eq else None
        return choice or None

    def _queue_card_choice(self, player_id: int, card: CardInstance, choice: Optional[dict] = None,
                           already_paid: bool = False) -> Optional[dict]:
        choice_request = self._get_choice_request(card, choice)
        if choice_request is None:
            return None
        choice_params = self._effect_params(choice_request)
        choice_type = self._choice_type_for_effect(choice_request, card)
        if choice_type == 'choose_target' and isinstance(choice_params, dict):
            allowed = str(choice_params.get('allowed', '') or '').strip().lower()
            if allowed and not any(key in choice_params for key in ('target', 'targets', 'candidates')):
                if allowed in ('any', 'all', 'both'):
                    choice_params = {**choice_params, 'target': 'all', 'include_self': True}
                elif allowed in ('self', 'owner'):
                    choice_params = {**choice_params, 'target': 'self', 'include_self': True}
                elif allowed in ('friendly', 'ally', 'allies'):
                    choice_params = {**choice_params, 'target': 'friendly', 'include_self': True}
                elif allowed in ('enemy', 'enemies', 'opponent', 'opponents'):
                    choice_params = {**choice_params, 'target': 'enemy', 'include_self': False}
        if choice_type == 'choose_target' and not choice_params and (
            self._v2_play_requires_choice_target(card) or self._root_play_requires_owner_target(card)
        ):
            choice_params = {'target': 'all', 'include_self': True, 'alive_only': True}
        prev_choice = getattr(self, '_active_choice', None)
        if isinstance(choice, dict):
            self._active_choice = choice
        try:
            choice_target_id = self._choice_target_id_for_request(player_id, choice_request)
        finally:
            self._active_choice = prev_choice
        self.pending_choice = {
            'card': card.to_dict(),
            'player_id': player_id,
            'choice_type': choice_type,
            'choice_params': choice_params,
            'original_choice': dict(choice) if isinstance(choice, dict) else None,
            'already_paid': bool(already_paid),
        }
        if choice_target_id is not None:
            self.pending_choice['target_player_id'] = choice_target_id
            if choice_type in ('choose_from_enemy_hand', 'choose_card_from_hand') and 0 <= choice_target_id < len(self.players):
                self.pending_choice['hand_cards'] = self._visible_card_dicts(
                    self.players[choice_target_id].hand,
                    player_id,
                    choice_target_id,
                    choice_list=True,
                )
        keep_paid_choice = choice_type in ('choose_ocean_sapphire', 'magic_salt_reflect')
        if already_paid and not keep_paid_choice:
            self._undo_pending_choice_play_side_effects(player_id, card)
        result = {
            'success': True,
            'needs_choice': True,
            'choice_type': choice_type,
            'choice_params': choice_params,
            'target_player_id': choice_target_id,
            'card': card.to_dict(),
        }
        if choice_type in ('choose_from_enemy_hand', 'choose_card_from_hand') and choice_target_id is not None and 0 <= choice_target_id < len(self.players):
            result['hand_cards'] = self._visible_card_dicts(
                self.players[choice_target_id].hand,
                player_id,
                choice_target_id,
                choice_list=True,
            )
        return result

    def _check_card_response_after_choice(self, player_id: int, card: CardInstance, choice: Optional[dict]) -> Optional[dict]:
        prev_choice = getattr(self, '_active_choice', None)
        prev_preview = getattr(self, '_pending_response_preview', None)
        if isinstance(choice, dict):
            self._active_choice = choice
        response_target_id = self._choice_target_from_choice(choice, 1 - player_id)
        if not (0 <= response_target_id < len(self.players)):
            response_target_id = 1 - player_id
        self._pending_response_preview = {
            'card': card.to_dict(),
            'player_id': player_id,
            'target_player_id': response_target_id,
            'original_choice': choice,
            'is_precision': 'precision' in card.flags,
        }
        try:
            needs_response = self._check_response_needed(player_id, card)
            if not needs_response:
                needs_response = self._check_precision_response_needed(player_id, card)
        finally:
            self._active_choice = prev_choice
            self._pending_response_preview = prev_preview
        if not needs_response:
            return None
        self.pending_response = {
            'card': card.to_dict(),
            'player_id': player_id,
            'target_player_id': response_target_id,
            'original_choice': choice,
            'is_precision': 'precision' in card.flags,
        }
        return {'success': True, 'needs_response': True, 'card': card.to_dict()}

    def play_card(self, player_id: int, card_instance_id: int, choice: Optional[dict] = None) -> dict:
        ps = self.players[player_id]
        card = ps.find_hand_card(card_instance_id)
        if card is None:
            return {'success': False, 'error': '卡牌不在手中'}
        if card.def_id == ERROR_CARD_ID:
            ps.remove_hand_card(card_instance_id)
            return {'success': True, 'card': card.to_dict(), 'ignored': True}
        if self.pending_response is not None:
            return {'success': False, 'error': '等待对手反制响应'}
        if getattr(self, 'pending_v2_ui', None) is not None:
            return {'success': False, 'error': 'Waiting for mod UI response'}
        choice, forced_target_id = self._sewers_apply_forced_target_choice(player_id, card, choice)
        auto_choice_mode = getattr(self, '_auto_resolve_choices_for', None) == player_id
        auto_no_cost = getattr(self, '_auto_play_no_cost_for', None) == player_id
        if auto_choice_mode and self._card_needs_choice(card) and not self._choice_satisfies_request(card, choice):
            choice_request = self._get_choice_request(card, choice)
            choice_params = self._effect_params(choice_request)
            choice_target_id = self._choice_target_id_for_request(player_id, choice_request)
            preview_pending = {
                'card': card.to_dict(),
                'player_id': player_id,
                'choice_type': self._choice_type_for_effect(choice_request, card),
                'choice_params': choice_params,
                'target_player_id': choice_target_id,
                'original_choice': dict(choice) if isinstance(choice, dict) else None,
            }
            generated_choice = self._default_choice_for_pending(preview_pending)
            if isinstance(generated_choice, dict):
                choice = {**(choice or {}), **generated_choice}
        card_flags = self._effective_card_flags(card)
        if card.card_type == 'thorn' and 'wide_strike' not in card_flags:
            target_id = self._choice_target_from_choice(choice, 1 - player_id)
            if not self._target_can_be_selected(
                player_id,
                target_id,
                allow_self=('self_target' in card_flags or forced_target_id == target_id),
            ):
                return {'success': False, 'error': '没有可选中的玩家'}
        elif 'wide_strike' not in card_flags and (self._v2_play_requires_choice_target(card) or self._root_play_requires_owner_target(card)):
            target_id = self._choice_target_from_choice(choice, -1)
            allow_dead_target = self._card_is(card, 'Yggdrasil', 'vanilla:yggdrasil')
            if target_id >= 0 and not self._target_can_be_selected(
                player_id,
                target_id,
                allow_self=True,
                alive_required=not allow_dead_target,
            ):
                return {'success': False, 'error': '没有可选中的玩家'}
        can_play, reason = self.can_play_card(player_id, card)
        if not can_play:
            if not (auto_no_cost and ('能量不足' in reason or '魔力不足' in reason)):
                return {'success': False, 'error': reason}
        if self._card_needs_choice(card) and not self._choice_satisfies_request(card, choice):
            queued = self._queue_card_choice(player_id, card, choice, already_paid=False)
            if queued:
                return queued
        if not self._defer_v2_before_play_until_choice(card, choice):
            self._run_v2_play_hook('before_play_card', player_id, card, choice)
            if getattr(self, 'pending_v2_ui', None) is not None:
                return {'success': True, 'needs_v2_ui': True, 'card': card.to_dict()}
        extra_e = self._get_extra_e_for_card(player_id, card)
        total_e = 0 if auto_no_cost else max(0, card.cost_e + extra_e)
        total_m = 0 if auto_no_cost else int(card.cost_m)
        card._paid_e_this_play = int(total_e)
        card._paid_m_this_play = int(total_m)
        ps.custom_vars['void_current_previous_def_id'] = str(ps.custom_vars.get('void_last_played_def_id', '') or '')
        self._spend_resource(player_id, 'elixir', total_e, card)
        self._spend_resource(player_id, 'magic', total_m, card)
        ps.cards_played_this_turn[card.def_id] = ps.cards_played_this_turn.get(card.def_id, 0) + 1
        if getattr(card, 'card_type', '') == 'thorn':
            ps.achievement_played_thorn = True
        self._note_achievement_play(player_id, card)
        card_removed = ps.remove_hand_card(card_instance_id)
        if card_removed is None:
            return {'success': False, 'error': '移出手牌失败'}
        ps.cards_played_this_turn_instance_ids.append(int(getattr(card, 'instance_id', card_instance_id) or card_instance_id))
        self._apply_magic_acceleration_after_play(player_id, card)
        self._atomic_ocean_charge_self_damage(player_id, card, {}, '', choice, {'target_id': player_id})
        self._sewers_trigger_vampire_fangs(player_id, card, choice)
        response_result = self._check_card_response_after_choice(player_id, card, choice)
        if response_result:
            return response_result
        result = self._execute_card_effect(player_id, card, choice)
        ps.custom_vars['void_last_played_def_id'] = getattr(card, 'def_id', '')
        ps.custom_vars.pop('void_current_previous_def_id', None)
        self._enforce_unique_cards_for_all()
        return result

    def _check_response_needed(self, player_id: int, card: CardInstance) -> bool:
        flags = self._effective_card_flags(card)
        if 'precision' in flags:
            return False
        if self._card_blocks_response(card):
            return False
        target_id = self._choice_target_from_choice(getattr(self, '_active_choice', None), 1 - player_id)
        opp = self.players[1 - player_id]
        if target_id == 1 - player_id:
            for c in opp.hand:
                if (
                    self._can_pay_counter_card(1 - player_id, c)
                    and c.card_def.response_trigger == 'targeted'
                    and self._counter_card_can_counter_pending(1 - player_id, c)
                ):
                    return True
        if any(
            self._can_pay_counter_card(1 - player_id, c)
            and c.card_def.response_trigger == 'any'
            and self._counter_card_can_counter_pending(1 - player_id, c)
            for c in opp.hand
        ):
            return True
        if card.card_type == 'thorn':
            for c in opp.hand:
                if self._can_pay_counter_card(1 - player_id, c) and c.card_def.response_trigger == 'thorn' and self._counter_card_can_counter_pending(1 - player_id, c):
                    return True
        if card.card_type == 'bloom':
            for c in opp.hand:
                if self._can_pay_counter_card(1 - player_id, c) and c.card_def.response_trigger == 'bloom' and self._counter_card_can_counter_pending(1 - player_id, c):
                    return True
        if card.card_type == 'root':
            for c in opp.hand:
                if self._can_pay_counter_card(1 - player_id, c) and c.card_def.response_trigger == 'root' and self._counter_card_can_counter_pending(1 - player_id, c):
                    return True
        if card.card_type == 'guard':
            for c in opp.hand:
                if self._can_pay_counter_card(1 - player_id, c) and c.card_def.response_trigger == 'guard' and self._counter_card_can_counter_pending(1 - player_id, c):
                    return True
        if self._would_destroy_equipment(card):
            for c in opp.hand:
                if self._can_pay_counter_card(1 - player_id, c) and c.card_def.response_trigger == 'equipment_destroy' and self._counter_card_can_counter_pending(1 - player_id, c):
                    return True
        if self._would_heal(card):
            for c in opp.hand:
                if self._can_pay_counter_card(1 - player_id, c) and c.card_def.response_trigger == 'heal' and self._counter_card_can_counter_pending(1 - player_id, c):
                    return True
        return False

    def _check_precision_response_needed(self, player_id: int, card: CardInstance) -> bool:
        flags = self._effective_card_flags(card)
        if 'precision' not in flags:
            return False
        if self._card_blocks_response(card):
            return False
        target_id = self._choice_target_from_choice(getattr(self, '_active_choice', None), 1 - player_id)
        if target_id != 1 - player_id:
            return False
        opp = self.players[1 - player_id]
        for c in opp.hand:
            if self._can_pay_counter_card(1 - player_id, c) and c.card_def.response_trigger == 'thorn':
                return True
        return False

    def _can_pay_counter_card(self, player_id: int, card: CardInstance) -> bool:
        if not (0 <= player_id < len(self.players)) or card is None:
            return False
        ps = self.players[player_id]
        return int(getattr(card, 'cost_e', 0) or 0) <= int(ps.elixir or 0) and int(getattr(card, 'cost_m', 0) or 0) <= int(ps.magic or 0)

    def _is_magic_antimatter_card(self, card: Optional[CardInstance]) -> bool:
        return self._card_is(card, 'MagicAntimatter', 'void:magic_antimatter') or getattr(card, 'def_id', '') == 'MagicAntimatter'

    def _pending_response_would_be_lethal_for(self, player_id: int) -> bool:
        pending = self.pending_response or getattr(self, '_pending_response_preview', None)
        if pending is None or not (0 <= player_id < len(self.players)):
            return False
        if int(getattr(self.players[player_id], 'health', 0) or 0) <= 0:
            return False
        try:
            sim = copy.deepcopy(self)
            if sim.pending_response is None:
                preview = getattr(sim, '_pending_response_preview', None)
                if preview is not None:
                    sim.pending_response = preview
            if sim.pending_response is None or not (0 <= player_id < len(sim.players)):
                return False
            before = int(getattr(sim.players[player_id], 'health', 0) or 0)
            if before <= 0:
                return False
            sim.handle_response(player_id, None)
            after = int(getattr(sim.players[player_id], 'health', before) or 0)
            return after <= 0
        except Exception:
            return False

    def _counter_card_can_counter_pending(self, player_id: int, counter_card: CardInstance) -> bool:
        if self._is_magic_antimatter_card(counter_card):
            pending = self.pending_response or getattr(self, '_pending_response_preview', None) or {}
            try:
                source_id = int(pending.get('player_id', -1))
            except Exception:
                source_id = -1
            return source_id != player_id and self._pending_response_would_be_lethal_for(player_id)
        return True

    def _would_destroy_equipment(self, card: CardInstance) -> bool:
        return card.def_id in ('Sewage', 'MagicSewage')

    def _would_heal(self, card: CardInstance) -> bool:
        if card is None:
            return False
        if getattr(card.card_def, 'heal', 0):
            return True
        for effect in list(self._play_effects_for_card(card) or []) + list(self._v2_play_steps_for_card(card) or []):
            if not isinstance(effect, dict):
                continue
            effect_type = self._effect_type(effect)
            if effect_type in ('heal', 'lifesteal_damage'):
                return True
        return False

    def handle_response(self, responder_id: int, card_instance_id: Optional[int]) -> dict:
        if self.pending_response is None:
            return {'success': False, 'error': '没有待响应的操作'}
        pending = self.pending_response
        pending_damage_prediction = self._simulate_pending_response_damage(responder_id, None) if card_instance_id is not None else {'total': 0, 'parts': []}
        self.pending_response = None
        player_id = pending['player_id']
        card = CardInstance.from_dict(pending['card'])
        choice = pending.get('original_choice')
        if card_instance_id is not None:
            responder = self.players[responder_id]
            counter_card = responder.find_hand_card(card_instance_id)
            if counter_card is None:
                return self._after_response_result(player_id, self._execute_card_effect(player_id, card, choice))
            counter_cost_e = int(getattr(counter_card, 'cost_e', 0) or 0)
            counter_cost_m = int(getattr(counter_card, 'cost_m', 0) or 0)
            if counter_cost_e > responder.elixir or counter_cost_m > responder.magic:
                return self._after_response_result(player_id, self._execute_card_effect(player_id, card, choice))
            can_respond = False
            played_card_def = card.card_def
            if not self._counter_card_can_counter_pending(responder_id, counter_card):
                can_respond = False
            elif played_card_def.card_type == 'thorn' and counter_card.card_def.response_trigger == 'thorn':
                can_respond = True
            elif played_card_def.card_type == 'bloom' and counter_card.card_def.response_trigger == 'bloom':
                can_respond = True
            elif played_card_def.card_type == 'root' and counter_card.card_def.response_trigger == 'root':
                can_respond = True
            elif counter_card.card_def.response_trigger == 'targeted' and responder_id == pending.get('target_player_id'):
                can_respond = True
            elif counter_card.card_def.response_trigger == 'any':
                can_respond = True
            elif self._would_heal(card) and counter_card.card_def.response_trigger == 'heal':
                can_respond = True
            elif self._would_destroy_equipment(card) and counter_card.card_def.response_trigger == 'equipment_destroy':
                can_respond = True
            if not can_respond:
                return self._after_response_result(player_id, self._execute_card_effect(player_id, card, choice))
            self._spend_resource(responder_id, 'elixir', counter_cost_e, counter_card)
            self._spend_resource(responder_id, 'magic', counter_cost_m, counter_card)
            counter_removed = responder.remove_hand_card(card_instance_id)
            if counter_removed is None:
                return self._after_response_result(player_id, self._execute_card_effect(player_id, card, choice))
            self.log_msg(f"{self.pn(responder_id)}使用{counter_removed.name_cn}{self._card_log_marker(counter_removed)}进行反制！")
            self._note_achievement_counter_success(responder_id)
            dodge_before_counter = int(getattr(responder, 'dodge', 0) or 0)
            self._game_over_defer_depth += 1
            try:
                self._execute_counter_effect(responder_id, counter_removed, card, player_id, pending_damage_prediction)
                is_precision = pending.get('is_precision', False)
                if self._card_is(counter_removed, 'Bubble', 'vanilla:bubble'):
                    if self._is_status_immune(responder_id):
                        return self._after_response_result(player_id, self._execute_card_effect(player_id, card, choice))
                    if is_precision:
                        self._execute_card_effect_half_damage(player_id, card, choice)
                        if not self._is_status_immune(responder_id):
                            responder.dodge = min(int(getattr(responder, 'dodge', 0) or 0), dodge_before_counter)
                        return self._after_response_result(player_id, {'success': True, 'countered': True, 'precision_halved': True, 'card': card.to_dict()})
                    self._execute_card_effect(player_id, card, choice)
                    if not self._is_status_immune(responder_id):
                        responder.dodge = min(int(getattr(responder, 'dodge', 0) or 0), dodge_before_counter)
                    return self._after_response_result(player_id, {'success': True, 'countered': True, 'card': card.to_dict()})
                if self._card_is(counter_removed, 'MagicBubble', 'vanilla:magicbubble'):
                    self.negated_card = True
                if self._card_is(counter_removed, 'Cucumber', 'ocean:cucumber'):
                    old_untargetable = max(0, int(getattr(responder, 'untargetable', 0) or 0))
                    responder.untargetable = 0
                    try:
                        result = self._execute_card_effect(player_id, card, choice)
                    finally:
                        responder.untargetable = old_untargetable
                    self._apply_cucumber_counter_after_response(responder_id)
                else:
                    result = self._execute_card_effect(player_id, card, choice)
                return self._after_response_result(player_id, result)
            finally:
                self._game_over_defer_depth -= 1
                self._check_game_over()
        return self._after_response_result(player_id, self._execute_card_effect(player_id, card, choice))

    def _after_response_result(self, player_id: int, result: dict) -> dict:
        self._enforce_unique_cards_for_all()
        if (
            not self.game_over
            and self.phase == 'action'
            and self.current_player == player_id
            and self.pending_response is None
            and self.pending_choice is None
            and not getattr(self, 'pending_v2_ui', None)
        ):
            self._continue_honey_control_if_needed(player_id)
        return result

    def _response_prediction_target_id(self, responder_id: int) -> int:
        pending = self.pending_response or {}
        target_id = pending.get('target_player_id')
        try:
            target_id = int(target_id)
        except Exception:
            target_id = responder_id
        if not (0 <= target_id < len(self.players)):
            target_id = responder_id
        if not (0 <= target_id < len(self.players)):
            target_id = 0
        return target_id

    def _prediction_damage_parts_from_log(self, log_start: int, target_id: int) -> List[int]:
        target_name = self.pn(target_id)
        parts: List[int] = []
        for line in list(self.log[log_start:]):
            parsed = self._parse_damage_taken_log(line)
            if parsed and parsed.get('target') == target_name:
                parts.extend(int(v) for v in parsed.get('parts', []) if int(v) > 0)
        return parts

    def _simulate_pending_response_damage(self, responder_id: int, card_instance_id: Optional[int] = None) -> dict:
        if self.pending_response is None:
            return {'total': 0, 'parts': [], 'display': ''}
        target_id = self._response_prediction_target_id(responder_id)
        try:
            sim = copy.deepcopy(self)
            sim_target_id = sim._response_prediction_target_id(responder_id)
            before_health = int(getattr(sim.players[sim_target_id], 'health', 0))
            before_poison = int(getattr(sim.players[sim_target_id], 'poison', 0))
            sim._prediction_capture_target_id = sim_target_id
            sim._prediction_first_attack_damage = 0
            log_start = len(sim.log)
            sim.handle_response(responder_id, card_instance_id)
            parts = sim._prediction_damage_parts_from_log(log_start, sim_target_id)
            total = sum(parts)
            first_hit = int(getattr(sim, '_prediction_first_attack_damage', 0) or 0)
            if total <= 0:
                after_health = int(getattr(sim.players[sim_target_id], 'health', before_health))
                total = max(0, before_health - after_health)
                parts = [total] if total > 0 else []
                if first_hit <= 0:
                    first_hit = total
            after_poison = int(getattr(sim.players[sim_target_id], 'poison', before_poison))
            return {
                'target_player_id': target_id,
                'total': int(total),
                'parts': parts,
                'first_hit': int(first_hit),
                'poison': max(0, after_poison - before_poison),
                'display': self._format_damage_parts(parts) if parts else ('0D' if total == 0 else f'{total}D'),
            }
        except Exception:
            return {'target_player_id': target_id, 'total': 0, 'parts': [], 'display': ''}

    def build_response_damage_prediction(self, responder_id: int, counter_cards=None) -> dict:
        baseline = self._simulate_pending_response_damage(responder_id, None)
        base_total = int(baseline.get('total') or 0)
        predictions = {}
        for entry in counter_cards or []:
            if isinstance(entry, CardInstance):
                instance_id = entry.instance_id
            elif isinstance(entry, dict):
                instance_id = entry.get('instance_id')
            else:
                instance_id = None
            try:
                instance_id = int(instance_id)
            except Exception:
                continue
            after = self._simulate_pending_response_damage(responder_id, instance_id)
            after_total = int(after.get('total') or 0)
            reduction = max(0, base_total - after_total)
            predictions[str(instance_id)] = {
                'after': after,
                'reduction': reduction,
                'reduction_display': f'-{self._format_damage_parts([reduction])}' if reduction > 0 else '',
            }
        return {
            'no_counter': baseline,
            'counters': predictions,
        }

    def _execute_counter_effect(self, responder_id: int, counter_card: CardInstance, original_card: CardInstance,
                                original_player_id: Optional[int] = None, pending_damage_prediction: Optional[dict] = None):
        ps = self.players[responder_id]
        opp = self.players[1 - responder_id]
        response_target_id = original_player_id if original_player_id is not None else 1 - responder_id
        delay_cucumber_effect = self._card_is(counter_card, 'Cucumber', 'ocean:cucumber')
        if delay_cucumber_effect:
            pass
        elif self._card_has_v2_event(counter_card.card_def, 'on_response'):
            self._run_v2_card_event(
                responder_id,
                counter_card,
                'on_response',
                {'target_player': response_target_id},
                {
                    'event': 'response',
                    'source_id': responder_id,
                    'target_id': response_target_id,
                    'response_target_id': response_target_id,
                    'defender_id': responder_id,
                    'target_player_explicit': True,
                    'original_card_instance_id': getattr(original_card, 'instance_id', None),
                    'original_card_def_id': getattr(original_card, 'def_id', ''),
                    'original_card': original_card,
                    'incoming_damage': int((pending_damage_prediction or {}).get('total') or 0),
                    'first_damage': int((pending_damage_prediction or {}).get('first_hit') or ((pending_damage_prediction or {}).get('parts') or [0])[0] or 0),
                    'first_hit_damage': int((pending_damage_prediction or {}).get('first_hit') or ((pending_damage_prediction or {}).get('parts') or [0])[0] or 0),
                    'damage_amount': int((pending_damage_prediction or {}).get('total') or 0),
                    'incoming_damage_parts': list((pending_damage_prediction or {}).get('parts') or []),
                },
            )
        elif self._has_script_entry(counter_card.card_def, 'response'):
            self._run_effect_list(
                responder_id,
                counter_card,
                self._get_script_effects(counter_card.card_def, 'response'),
                None,
                {'event': 'response', 'source_id': responder_id, 'target_id': response_target_id},
            )
        elif self._card_is(counter_card, 'Bubble', 'vanilla:bubble'):
            if not self._status_application_blocked(responder_id, 'dodge'):
                ps.dodge += 1
                self.log_msg(f"{self.pn(responder_id)}获得1层闪避")
        elif self._card_is(counter_card, 'Nazar', 'vanilla:nazar'):
            if not self._status_application_blocked(responder_id, 'nazar'):
                self._add_nazar_status_value(responder_id, 2)
                self.log_msg(f"{self.pn(responder_id)}获得2层邪眼")
        elif self._card_is(counter_card, 'MagicNazar', 'vanilla:magicnazar'):
            if not self._status_application_blocked(responder_id, 'magic_nazar'):
                magic_nazar_stacks = int(ps.custom_statuses.get('magic_nazar', 0) or 0) + 2
                ps.custom_statuses['magic_nazar'] = magic_nazar_stacks
                self.log_msg(f"{self.pn(responder_id)}获得2层魔法邪眼（共{magic_nazar_stacks}层）")
        elif self._card_is(counter_card, 'MagicBubble', 'vanilla:magicbubble'):
            if not self._status_application_blocked(responder_id, 'negate_next_skill'):
                ps.negate_next_skill = True
                self.log_msg(f"{self.pn(responder_id)}的魔法泡泡：敌方下次技能牌失效")
        elif counter_card.card_def.effects:
            counter_effects = [e for e in counter_card.card_def.effects
                               if (isinstance(e, dict) and e.get('type', '').startswith('counter_'))
                               or (isinstance(e, str) and e.startswith('counter_'))]
            for effect in counter_effects:
                if isinstance(effect, str):
                    eff_type = effect
                    params = {}
                    log = ''
                else:
                    eff_type = effect.get('type', '')
                    params = effect.get('params', {})
                    log = effect.get('log', '')
                handler = getattr(self, f'_atomic_{eff_type}', None)
                if handler:
                    handler(responder_id, counter_card, params, log, None, 'counter')
        if self._card_is(counter_card, 'Nitro', 'ocean:nitro'):
            original_card.instance_flags.add('exile')
            original_card.instance_flags.add('ocean_nitro_negated')
            self.log_msg(f"{self.pn(responder_id)}的氮气使所响应的牌失效并进入放逐区")
        reset_card_after_play(counter_card)
        if 'exile' in counter_card.flags:
            self._put_card_in_exile(responder_id, counter_card)
        else:
            self._discard_card(ps, counter_card)
        self._note_achievement_play(responder_id, counter_card)
        self._dispatch_card_event('card_used', responder_id, counter_card,
                                  target_id=response_target_id)

    def _apply_cucumber_counter_after_response(self, responder_id: int):
        if not (0 <= responder_id < len(self.players)):
            return
        if self._status_application_blocked(responder_id, 'untargetable'):
            return
        self.players[responder_id].untargetable = max(0, int(getattr(self.players[responder_id], 'untargetable', 0) or 0)) + 1
        self._note_achievement_status_peak(responder_id)
        self.log_msg(f"{self.pn(responder_id)}获得1层无法选中")

    def _reset_one_shot_attack_attrs(self, card: CardInstance):
        reset_card_after_play(card)

    def _discard_card(self, ps, card: CardInstance):
        reset_card_for_discard(card)
        ps.discard.append(card)
        self._note_achievement_card_discarded(ps.player_id, card)
        try:
            self._note_achievement_enemy_card_total(ps.player_id)
        except Exception:
            pass

    def _is_void_antimatter(self, card: Optional[CardInstance]) -> bool:
        return self._card_is(card, 'Antimatter', 'void:antimatter')

    def _put_card_in_exile(self, owner_id: int, card: Optional[CardInstance], trigger: bool = True):
        if card is None or not self._valid_player_id(owner_id):
            return
        ps = self.players[owner_id]
        already_exiled = card in ps.exile
        if not already_exiled:
            ps.exile.append(card)
        if trigger and not already_exiled:
            self._handle_card_exiled(owner_id, card)

    def _handle_card_exiled(self, owner_id: int, card: CardInstance):
        if self._is_void_antimatter(card):
            self._atomic_void_damage_all_except_self(
                owner_id,
                card,
                {'amount': 10},
                '',
                None,
                {'event': 'card_exiled', 'source_id': owner_id, 'target_id': owner_id},
            )

    def _record_ocean_active_discard(self, player_id: int, amount: int = 1):
        if not self._valid_player_id(player_id):
            return
        try:
            current = int(self.players[player_id].custom_vars.get('ocean_active_discards', 0) or 0)
            self.players[player_id].custom_vars['ocean_active_discards'] = max(0, current + int(amount))
        except Exception:
            pass
        for hand_card in list(getattr(self.players[player_id], 'hand', []) or []):
            if self._card_is(hand_card, 'MagicTrident', 'ocean:magic_trident'):
                hand_card.power_value = max(0, int(getattr(hand_card, 'power_value', 0) or 0) + 5 * int(amount))
                hand_card.instance_flags.add('power')
            elif self._card_is(hand_card, 'MagicPearl', 'ocean:magic_pearl'):
                hand_card.power_value = max(0, int(getattr(hand_card, 'power_value', 0) or 0) + 2 * int(amount))
                hand_card.instance_flags.add('power')


    def _execute_card_effect_half_damage(self, player_id: int, card: CardInstance, choice: Optional[dict] = None) -> dict:
        self.log_msg(f"{self.pn(player_id)}的精准牌被闪避反制，伤害减半！")
        self.halve_next_attack = True
        self._suppress_next_precision_dodge_log = True
        try:
            result = self._execute_card_effect(player_id, card, choice)
        finally:
            self.halve_next_attack = False
            self._suppress_next_precision_dodge_log = False
        return result

    def _magic_nazar_counter_player_ids(self, player_id: int, card: Optional[CardInstance] = None,
                                        choice: Optional[dict] = None) -> List[int]:
        return [1 - player_id] if len(self.players) == 2 else []

    def _get_card_base_damage(self, card: CardInstance) -> int:
        dmg_map = {
            'Basic': 8, 'Bone': 12, 'Stinger': 20, 'Sand': 3,
            'Wing': 8, 'Light': 2, 'Fang': 8, 'Triangle': 6,
            'MagicBone': 15, 'MagicStinger': 30,
        }
        base = dmg_map.get(card.def_id, 0)
        return self._modified_attack_damage(base, card)



    def resolve_choice(self, player_id: int, choice: dict) -> dict:
        if self.pending_choice is None:
            return {'success': False, 'error': '没有待选择操作'}
        pending = self.pending_choice
        choice_type = pending.get('choice_type', '')
        # Handle foresight_replace choice
        if choice_type == 'foresight_replace':
            self.pending_choice = None
            ps = self.players[player_id]
            foresight_info = getattr(self, '_pending_foresight', None) or {}
            draw_budget = max(0, int(foresight_info.get('draw_count', 0) or 0))
            select_limit = max(0, int(foresight_info.get('select_limit', 0) or 0))
            resume_handler = str(foresight_info.get('resume_handler') or '').strip()
            selected_ids = (choice or {}).get('selected_instance_ids', [])
            selected_set = set(selected_ids[:select_limit])
            discarded = 0
            for card in list(ps.hand):
                if card.instance_id not in selected_set:
                    continue
                ps.hand.remove(card)
                self._discard_card(ps, card)
                discarded += 1
                self._record_ocean_active_discard(player_id, 1)
                if discarded >= select_limit:
                    break
            replacement_drawn = 0
            if discarded > 0:
                replacement_drawn = len(self._draw_cards_with_v2_hooks(player_id, discarded, 'foresight_replace'))
                self.log_msg(f"{self.pn(player_id)}因预知弃{discarded}张并抽{replacement_drawn}张牌")
            ps.foresight = 0
            self._pending_foresight = None
            if resume_handler:
                handler = getattr(self, f'_resume_{resume_handler}', None)
                if callable(handler):
                    handler(player_id, {'foresight_discarded': discarded, 'foresight_drawn': replacement_drawn, 'draw_count': draw_budget})
            self._enforce_unique_cards_for_all()
            return {'success': True, 'foresight_discarded': discarded, 'foresight_drawn': replacement_drawn}
        # Handle reorder_deck choice (e.g. Magic Goggles)
        if choice_type == 'reorder_deck':
            self.pending_choice = None
            choice_cancelled = choice is None or (
                isinstance(choice, dict) and (bool(choice.get('cancelled')) or bool(choice.get('cancel')))
            )
            if choice_cancelled:
                if (pending.get('choice_params') or {}).get('cancellable') is False:
                    self.pending_choice = pending
                    return {'success': False, 'error': '此选择不能取消'}
                card_data = pending.get('card')
                card = CardInstance.from_dict(card_data) if isinstance(card_data, dict) else None
                if card:
                    ps = self.players[player_id]
                    if ps.find_hand_card(card.instance_id) is None:
                        ps.hand.insert(0, card)
                return {'success': False, 'cancelled': True, 'error': '选择已取消'}
            target_id = pending.get('target_player_id', 1 - player_id)
            target_ps = self.players[target_id]
            new_order = (choice or {}).get('new_order', [])
            if new_order:
                id_to_card = {c.instance_id: c for c in target_ps.deck}
                new_deck = []
                for iid in new_order:
                    if iid in id_to_card:
                        new_deck.append(id_to_card.pop(iid))
                for c in id_to_card.values():
                    new_deck.append(c)
                target_ps.deck = new_deck
                self.log_msg(f"{self.pn(player_id)}重排了对手的牌堆")
            # Now properly consume the card (re-spend cost, remove from hand, discard)
            card_data = pending.get('card')
            if card_data:
                card = CardInstance.from_dict(card_data) if isinstance(card_data, dict) else None
                if card:
                    ps = self.players[player_id]
                    # Re-spend the cost that was refunded during pending
                    dup_count = ps.cards_played_this_turn.get(card.def_id, 0)
                    extra_e = self._get_extra_e_for_card(player_id, card)
                    total_e = max(0, card.cost_e + extra_e)
                    self._spend_resource(player_id, 'elixir', total_e, card)
                    self._spend_resource(player_id, 'magic', card.cost_m, card)
                    ps.cards_played_this_turn[card.def_id] = dup_count + 1
                    if getattr(card, 'card_type', '') == 'thorn':
                        ps.achievement_played_thorn = True
                    # Remove from hand
                    hand_card = ps.find_hand_card(card.instance_id)
                    if hand_card:
                        ps.remove_hand_card(card.instance_id)
                    # Discard the card (bloom cards go to discard)
                    if 'exile' in card.flags:
                        self._put_card_in_exile(ps.player_id, card)
                    else:
                        self._discard_card(ps, card)
                    self._log_card_play(player_id, card)
                    self._dispatch_card_event('card_used', player_id, card, target_id=player_id, choice=choice)
                    self._run_v2_play_hook('after_play_card', player_id, card, choice)
            self._enforce_unique_cards_for_all()
            return {'success': True, 'reordered': True}
        self.pending_choice = None
        card = CardInstance.from_dict(pending['card'])
        ps = self.players[player_id]
        choice_cancelled = choice is None or (
            isinstance(choice, dict) and (bool(choice.get('cancelled')) or bool(choice.get('cancel')))
        )
        if choice_type == 'magic_salt_reflect':
            self.pending_choice = None
            if choice_cancelled or not (isinstance(choice, dict) and (choice.get('confirmed') or choice.get('accepted'))):
                return {'success': True, 'cancelled': True}
            params = pending.get('choice_params') or {}
            try:
                owner_id = int(params.get('owner_id', player_id))
                attacker_id = int(params.get('attacker_id', -1))
                target_id = int(params.get('target_id', owner_id))
                damage = int(params.get('damage', 0) or 0)
            except Exception:
                return {'success': False, 'error': '魔法盐反伤失败'}
            if not self._valid_player_id(owner_id) or not self._valid_player_id(attacker_id) or damage <= 0:
                return {'success': False, 'error': '魔法盐反伤失败'}
            cost_m = max(0, int(params.get('cost_m', 1) or 0))
            owner = self.players[owner_id]
            if owner.magic < cost_m:
                self.log_msg(f"{self.pn(owner_id)}的魔法盐魔力不足")
                return {'success': True, 'not_enough_magic': True}
            if cost_m > 0:
                owner.magic -= cost_m
            ratio = float(params.get('ratio', 0.5) or 0.5)
            reflect = int(math.ceil(damage * ratio))
            if reflect <= 0:
                return {'success': True}
            dealt = self._deal_direct_damage(
                attacker_id,
                reflect,
                '魔法盐反伤',
                target_id,
                damage_type=DAMAGE_TYPE_PHYSICAL,
                damage_tag=DAMAGE_TAG_PHYSICAL,
            )
            if dealt > 0:
                self.log_msg(f"{self.pn(owner_id)}消耗{cost_m}M，魔法盐对{self.pn(attacker_id)}反弹{dealt}D")
            self._enforce_unique_cards_for_all()
            return {'success': True, 'reflected': dealt}
        if choice_cancelled:
            if (pending.get('choice_params') or {}).get('cancellable') is False:
                self.pending_choice = pending
                return {'success': False, 'error': '此选择不能取消'}
            if pending.get('already_paid'):
                self._undo_pending_choice_play_side_effects(
                    player_id,
                    card,
                    play_log_marker=pending.get('play_log_marker'),
                )
            elif ps.find_hand_card(card.instance_id) is None:
                ps.hand.insert(0, card)
            return {'success': False, 'cancelled': True, 'error': '选择已取消'}
        if isinstance(choice, dict):
            original_choice = pending.get('original_choice') if isinstance(pending.get('original_choice'), dict) else {}
            for key in ('target_player', 'target_player_id', 'target_id'):
                if key not in choice and key in original_choice:
                    choice[key] = original_choice[key]
            if 'target_player_id' not in choice and pending.get('target_player_id') is not None:
                choice['target_player_id'] = pending.get('target_player_id')
        choice, _ = self._sewers_apply_forced_target_choice(player_id, card, choice)
        self._run_v2_play_hook('before_play_card', player_id, card, choice)
        if getattr(self, 'pending_v2_ui', None) is not None:
            return {'success': True, 'needs_v2_ui': True, 'card': card.to_dict()}
        if not pending.get('already_paid'):
            dup_count = ps.cards_played_this_turn.get(card.def_id, 0)
            extra_e = self._get_extra_e_for_card(player_id, card)
            total_e = max(0, card.cost_e + extra_e)
            card._paid_e_this_play = int(total_e)
            card._paid_m_this_play = int(card.cost_m)
            self._spend_resource(player_id, 'elixir', total_e, card)
            self._spend_resource(player_id, 'magic', card.cost_m, card)
            ps.cards_played_this_turn[card.def_id] = dup_count + 1
            if getattr(card, 'card_type', '') == 'thorn':
                ps.achievement_played_thorn = True
            hand_card = ps.find_hand_card(card.instance_id)
            if hand_card:
                ps.remove_hand_card(card.instance_id)
            ps.cards_played_this_turn_instance_ids.append(int(getattr(card, 'instance_id', 0) or 0))
            self._apply_magic_acceleration_after_play(player_id, card)
            self._atomic_ocean_charge_self_damage(player_id, card, {}, '', choice, {'target_id': player_id})
            self._sewers_trigger_vampire_fangs(player_id, card, choice)
        if self._card_needs_choice(card) and not self._choice_satisfies_request(card, choice):
            result = self._execute_card_effect(player_id, card, choice)
            self._enforce_unique_cards_for_all()
            return result
        response_result = self._check_card_response_after_choice(player_id, card, choice)
        if response_result:
            return response_result
        result = self._execute_card_effect(player_id, card, choice)
        self._enforce_unique_cards_for_all()
        return result


    PASSIVE_EFFECT_TYPES = {'on_fatal_set_health_exile', 'on_fatal_invincible_then_die'}


    def _atomic_log(self, player_id, card, params, log, choice, context):
        msg = log or params.get('msg', '')
        if msg:
            self.log_msg(msg.format(p=player_id + 1, name=card.name_cn))












    def _atomic_reveal_enemy_hand(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if not self._valid_player_id(target_id):
            return
        opp = self.players[target_id]
        self._antennae_reveal[player_id] = [c.to_dict() for c in opp.hand]
        self.log_msg(log or f"{self.pn(player_id)}查看了{self.pn(target_id)}的手牌")

    def _atomic_steal_enemy_card(self, player_id, card, params, log, choice, context):
        ps = self.players[player_id]
        target_id = self._choice_target_from_choice(choice, -1) if isinstance(choice, dict) else -1
        if target_id < 0 and isinstance(context, dict):
            try:
                target_id = int(context.get('target_id', -1))
            except Exception:
                target_id = -1
        if target_id < 0:
            target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if not (0 <= target_id < len(self.players)):
            self.log_msg(log or f"{self.pn(player_id)}夺取失败")
            self._clear_hand_reveal_for_player(player_id)
            return
        opp = self.players[target_id]
        if choice and 'target_instance_id' in choice:
            target = opp.find_hand_card(choice['target_instance_id'])
            if not self._card_visible_to_player(target, player_id, target_id) or not self._card_selectable_by_action(target):
                target = None
            if target and ps.can_add_to_hand():
                opp.hand.remove(target)
                ps.add_to_hand(target)
                self.log_msg(log or f"{self.pn(player_id)}从{self.pn(target_id)}手牌中获得1张牌")
            else:
                self.log_msg(log or f"{self.pn(player_id)}夺取失败")
        else:
            self.log_msg(log or f"{self.pn(player_id)}未选择要夺取的牌")

        self._clear_hand_reveal_for_player(player_id)

    def _atomic_choose_from_deck(self, player_id, card, params, log, choice, context):
        ps = self.players[player_id]
        selector = params.get('selector')
        if isinstance(selector, dict):
            matched = [c for c in self._match_card_selector(player_id, ps.deck, selector, card) if self._card_selectable_by_action(c)]
            if self.debug_selector_log:
                self.log_msg(f"选择器命中(牌堆)：{len(matched)}")
        if choice and 'target_instance_id' in choice:
            target = next((c for c in ps.deck if c.instance_id == choice['target_instance_id']), None)
            if target is None and isinstance(selector, dict):
                matched = [c for c in self._match_card_selector(player_id, ps.deck, selector, card) if self._card_selectable_by_action(c)]
                target = matched[0] if matched else None
            if target and not self._card_selectable_by_action(target):
                target = None
            if target and ps.can_add_to_hand():
                ps.deck.remove(target)
                ps.add_to_hand(target)
                if log:
                    self.log_msg(log)
            else:
                self.log_msg(log or f"{self.pn(player_id)}从牌堆取牌失败")
        elif choice and 'target_def_id' in choice:
            sel = {'selector': 'by_id', 'id': choice['target_def_id']}
            matched = [c for c in self._match_card_selector(player_id, ps.deck, sel, card) if self._card_selectable_by_action(c)]
            target = matched[0] if matched else None
            if target and self._card_selectable_by_action(target) and ps.can_add_to_hand():
                ps.deck.remove(target)
                ps.add_to_hand(target)
                if log:
                    self.log_msg(log)
            else:
                self.log_msg(log or f"{self.pn(player_id)}从牌堆取牌失败")
        else:
            self.log_msg(log or f"{self.pn(player_id)}未选择牌")

    def _atomic_choose_from_discard(self, player_id, card, params, log, choice, context):
        ps = self.players[player_id]
        selector = params.get('selector')
        if isinstance(selector, dict):
            matched = [c for c in self._match_card_selector(player_id, ps.discard, selector, card) if self._card_selectable_by_action(c)]
            if self.debug_selector_log:
                self.log_msg(f"选择器命中(弃牌)：{len(matched)}")
        if choice and 'target_instance_id' in choice:
            target = next((c for c in ps.discard if c.instance_id == choice['target_instance_id']), None)
            if target and self._card_selectable_by_action(target) and ps.can_add_to_hand():
                ps.discard.remove(target)
                target.instance_flags.add('symbiosis')
                ps.add_to_hand(target)
                if log:
                    self.log_msg(log)
            else:
                self.log_msg(log or f"{self.pn(player_id)}从弃牌堆取牌失败")
        elif choice and 'target_def_id' in choice:
            sel = {'selector': 'by_id', 'id': choice['target_def_id']}
            matched = [c for c in self._match_card_selector(player_id, ps.discard, sel, card) if self._card_selectable_by_action(c)]
            target = matched[0] if matched else None
            if target is None and isinstance(selector, dict):
                matched2 = [c for c in self._match_card_selector(player_id, ps.discard, selector, card) if self._card_selectable_by_action(c)]
                target = matched2[0] if matched2 else None
            if target and self._card_selectable_by_action(target) and ps.can_add_to_hand():
                ps.discard.remove(target)
                target.instance_flags.add('symbiosis')
                ps.add_to_hand(target)
                if log:
                    self.log_msg(log)
            else:
                self.log_msg(log or f"{self.pn(player_id)}从弃牌堆取牌失败")
        else:
            self.log_msg(log or f"{self.pn(player_id)}未选择牌")

    def _atomic_set_health(self, player_id, card, params, log, choice, context):
        amount = self._eval_int(player_id, params.get('amount', params.get('value', 60)), card, 60)
        for target_id in self._resolve_targets(player_id, params.get('target', 'self')):
            if 0 <= target_id < len(self.players):
                self.players[target_id].health = max(0, min(amount, self.players[target_id].max_health))
                self._note_achievement_health(target_id)
                self.log_msg(log or f"{self.pn(target_id)}血量设为{amount}")

    def _atomic_set_invincible(self, player_id, card, params, log, choice, context):
        if self._status_application_blocked(player_id, 'invincible'):
            return
        self._set_invincible_until_next_own_turn_end(player_id)
        self.log_msg(log or f"{self.pn(player_id)}获得无敌直到下一个自己回合结束")

    def _atomic_set_untargetable(self, player_id, card, params, log, choice, context):
        if self._status_application_blocked(player_id, 'untargetable'):
            return
        self.players[player_id].untargetable = max(0, int(getattr(self.players[player_id], 'untargetable', 0) or 0)) + 1
        self.players[player_id].shovel_active = True
        self._note_achievement_status_peak(player_id)
        self.log_msg(log or f"{self.pn(player_id)}无法被攻击选中")

    def _atomic_block_enemy_attacks(self, player_id, card, params, log, choice, context):
        duration = params.get('duration', 1)
        opp = self.players[1 - player_id]
        if self._status_application_blocked(1 - player_id, 'attack_blocked'):
            return
        opp.attack_blocked = max(opp.attack_blocked, duration)
        self._note_achievement_status_peak(1 - player_id)
        self.log_msg(log or f"{self.pn(1 - player_id)}无法使用攻击牌{duration}回合")

    def _atomic_force_enemy_attacks_only(self, player_id, card, params, log, choice, context):
        duration = params.get('duration', 1)
        opp = self.players[1 - player_id]
        if self._status_application_blocked(1 - player_id, 'attack_only'):
            return
        opp.attack_only = max(opp.attack_only, duration)
        self.log_msg(log or f"{self.pn(1 - player_id)}仅可使用攻击牌{duration}回合")

    def _atomic_block_own_actions(self, player_id, card, params, log, choice, context):
        if self._status_application_blocked(player_id, 'shovel_active'):
            return
        self.players[player_id].shovel_active = True
        self.log_msg(log or f"{self.pn(player_id)}无法使用卡牌")

    def _atomic_counter_dodge(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        self.players[player_id].dodge += amount
        self._note_achievement_status_peak(player_id)
        self.log_msg(log or f"{self.pn(player_id)}获得{amount}闪避")

    def _atomic_counter_nazar(self, player_id, card, params, log, choice, context):
        if self._status_application_blocked(player_id, 'nazar'):
            return
        amount = self._eval_int(player_id, params.get('amount', 2), card, 2)
        self._add_nazar_status_value(player_id, amount)
        self.log_msg(log or f"{self.pn(player_id)}获得{amount}层邪眼")

    def _atomic_counter_negate_skill(self, player_id, card, params, log, choice, context):
        if self._status_application_blocked(player_id, 'negate_next_skill'):
            return
        self.players[player_id].negate_next_skill = True
        self.log_msg(log or f"{self.pn(player_id)}的下次技能牌将失效")

    def _atomic_counter_equip_protect(self, player_id, card, params, log, choice, context):
        if self._status_application_blocked(player_id, 'equipment_protection'):
            return
        amount = params.get('amount', 1)
        self.players[player_id].equipment_protection += amount
        self._note_achievement_status_peak(player_id)
        self.log_msg(log or f"{self.pn(player_id)}获得{amount}装备保护")

    def _atomic_add_equipment_armor(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if not (0 <= target_id < len(self.players)):
            return
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        changed = 0
        for eq in list(getattr(self.players[target_id], 'equipment', []) or []):
            if 'indestructible' in eq.card_instance.flags:
                continue
            eq.armor = max(0, int(getattr(eq, 'armor', 0) or 0)) + amount
            changed += 1
        if changed > 0:
            self.log_msg(log or f"{self.pn(target_id)}的所有装备获得{amount}层装备护甲")

    def _atomic_destroy_current_equipment(self, player_id, card, params, log, choice, context):
        instance_id = getattr(card, 'instance_id', None)
        for owner_id, owner_state in enumerate(self.players):
            for eq in list(owner_state.equipment):
                if getattr(eq.card_instance, 'instance_id', None) == instance_id:
                    if self._destroy_equipment(owner_id, eq, check_protection=False, source_id=player_id):
                        if log:
                            self.log_msg(log)
                    return

    def _atomic_counter_block_enemy_attacks(self, player_id, card, params, log, choice, context):
        duration = params.get('duration', 1)
        opp = self.players[1 - player_id]
        if self._status_application_blocked(1 - player_id, 'attack_blocked'):
            return
        opp.attack_blocked = max(opp.attack_blocked, duration)
        self._note_achievement_status_peak(1 - player_id)
        self.log_msg(log or f"{self.pn(1 - player_id)}无法使用攻击牌")

    def _atomic_counter_set_invincible_then_die(self, player_id, card, params, log, choice, context):
        if self._status_application_blocked(player_id, 'bandage_active'):
            return
        self.players[player_id].bandage_active = True
        self.log_msg(log or f"{self.pn(player_id)}受到致命伤害时将无敌至下一个自己回合结束")

    def _atomic_equip_sponge(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        if not (0 <= target_id < len(self.players)):
            target_id = player_id
        if self._status_application_blocked(target_id, 'sponge_active'):
            return
        self.players[target_id].sponge_active = True
        self.log_msg(log or f"{self.pn(target_id)}伤害转为毒伤")

    def _atomic_equip_reduce_enemy_draw(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        self.players[1 - player_id].sluggish += amount
        self._note_achievement_status_peak(1 - player_id)
        self.log_msg(log or f"敌方获得{amount}层迟缓")

    def _atomic_equip_reduce_enemy_e(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        self.players[1 - player_id].overload += amount
        self._note_achievement_status_peak(1 - player_id)
        self.log_msg(log or f"敌方获得{amount}层超载")

    def _atomic_equip_reduce_own_draw(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        self.players[player_id].sluggish += amount
        self._note_achievement_status_peak(player_id)
        self.log_msg(log or f"{self.pn(player_id)}获得{amount}层迟缓")

    def _atomic_equip_reduce_own_e(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        self.players[player_id].overload += amount
        self._note_achievement_status_peak(player_id)
        self.log_msg(log or f"{self.pn(player_id)}获得{amount}层超载")

    def _atomic_equip_add_toxic(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        if self._status_application_blocked(1 - player_id, 'toxic'):
            return
        self.players[1 - player_id].toxic += amount
        self._note_achievement_status_peak(1 - player_id)
        self.log_msg(log or f"敌方+{amount}淬毒")

    def _atomic_equip_set_health(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 60)
        self.players[player_id].health = amount
        self._note_achievement_health(player_id)
        self.log_msg(log or f"{self.pn(player_id)}血量设为{amount}")

    def _atomic_equip_on_destroy_remove_poison_damage(self, player_id, card, params, log, choice, context):
        pass

    def _atomic_on_fatal_invincible_then_die(self, player_id, card, params, log, choice, context):
        if self._status_application_blocked(player_id, 'bandage_active'):
            return
        self.players[player_id].bandage_active = True
        self.log_msg(log or f"{self.pn(player_id)}受到致命伤害时将无敌至下一个自己回合结束，然后死亡")

    def _atomic_on_fatal_set_health_exile(self, player_id, card, params, log, choice, context):
        health_amount = params.get('health', 5)
        self.log_msg(log or f"{self.pn(player_id)}的{card.name_cn}被动效果：受到致命伤害时清除所有效果，生命值设为{health_amount}，无敌直到下一个自己回合结束")

    def _atomic_deal_damage_multi(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        amount = params.get('amount', 6)
        times = params.get('times', 1)
        total = 0
        for _ in range(times):
            try:
                total += self.deal_attack_damage(target_id, amount, attacker_id=player_id)
            except TypeError:
                total += self.deal_attack_damage(target_id, amount)
        if log:
            self.log_msg(log)

    def _atomic_remove_armor(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        amount = params.get('amount', 1)
        self.players[target_id].armor = max(0, self.players[target_id].armor - amount)
        self.log_msg(log or f"{self.pn(target_id)}失去{amount}护甲")

    def _atomic_set_armor(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = params.get('amount', 0)
        self.players[target_id].armor = amount
        self.log_msg(log or f"{self.pn(target_id)}护甲设为{amount}")

    def _atomic_dodge_this(self, player_id, card, params, log, choice, context):
        self.players[player_id].dodge += 1
        self.log_msg(log or f"{self.pn(player_id)}获得1层闪避（针对本次攻击）")

    def _atomic_clear_buffs(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        ps = self.players[target_id]
        ps.armor = 0
        ps.dodge = 0
        self._clear_invincible_state(target_id)
        ps.equipment_protection = 0
        self.log_msg(log or f"{self.pn(target_id)}的所有正面效果已清除")

    def _atomic_clear_debuffs(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        ps = self.players[target_id]
        ps.poison = 0
        ps.fire = 0
        ps.toxic = 0
        ps.stagnation = 0
        ps.blind = 0
        self.log_msg(log or f"{self.pn(target_id)}的所有负面效果已清除")

    def _atomic_clear_all_effects(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        ps = self.players[target_id]
        ps.poison = 0
        ps.fire = 0
        ps.toxic = 0
        ps.stagnation = 0
        ps.blind = 0
        ps.armor = 0
        ps.dodge = 0
        self._clear_invincible_state(target_id)
        ps.equipment_protection = 0
        self.log_msg(log or f"{self.pn(target_id)}的所有效果已清除")

    def _atomic_clear_status(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        status = params.get('status', '')
        ps = self.players[target_id]
        status_map = {'poison': 'poison', 'burn': 'fire',
                      'toxic': 'toxic', 'dodge': 'dodge', 'invincible': 'invincible',
                      'stagnation': 'stagnation', 'blind': 'blind',
                      'untargetable': 'untargetable', 'equip_protection': 'equipment_protection'}
        attr = status_map.get(status)
        if attr and hasattr(ps, attr):
            if attr == 'invincible':
                self._clear_invincible_state(target_id)
            elif isinstance(getattr(ps, attr), bool):
                setattr(ps, attr, False)
            else:
                setattr(ps, attr, 0)
            self.log_msg(log or f"{self.pn(target_id)}的{status}已清除")

    def _atomic_cost_e(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self._spend_resource(target_id, 'elixir', amount, card)
        self.log_msg(log or f"{self.pn(target_id)}消耗{amount}E")

    def _atomic_cost_m(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self._spend_resource(target_id, 'magic', amount, card)
        self.log_msg(log or f"{self.pn(target_id)}消耗{amount}M")

    def _atomic_mod_e_regen(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = params.get('amount', 1)
        self.players[target_id].e_regen_mod = getattr(self.players[target_id], 'e_regen_mod', 0) + amount
        self.log_msg(log or f"{self.pn(target_id)}每回合能量回复{amount:+d}")

    def _atomic_mod_m_regen(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = params.get('amount', 1)
        self.players[target_id].m_regen_mod = getattr(self.players[target_id], 'm_regen_mod', 0) + amount
        self.log_msg(log or f"{self.pn(target_id)}每回合魔力回复{amount:+d}")

    def _atomic_mod_draw(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = params.get('amount', 1)
        self.players[target_id].draw_mod = getattr(self.players[target_id], 'draw_mod', 0) + amount
        self.log_msg(log or f"{self.pn(target_id)}每回合抽牌数{amount:+d}")

    def _atomic_discard(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        ps = self.players[player_id]
        for _ in range(min(amount, len(ps.hand))):
            c = ps.hand.pop()
            self._discard_card(ps, c)
        self.log_msg(log or f"{self.pn(player_id)}丢弃{amount}张手牌")

    def _atomic_choose_from_exile(self, player_id, card, params, log, choice, context):
        ps = self.players[player_id]
        target = None
        if choice and 'target_def_id' in choice:
            sel = {'selector': 'by_id', 'id': choice['target_def_id']}
            matched = [c for c in self._match_card_selector(player_id, ps.exile, sel, card) if self._card_selectable_by_action(c)]
            target = matched[0] if matched else None
        if target and self._card_selectable_by_action(target) and ps.can_add_to_hand():
            ps.exile.remove(target)
            ps.add_to_hand(target)
            if log:
                self.log_msg(log)
        else:
            self.log_msg(log or f"{self.pn(player_id)}未选择牌")

    def _atomic_reveal_deck_top(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        amount = params.get('amount', 1)
        opp = self.players[target_id]
        top_cards = opp.deck[:amount]
        names = ', '.join(c.name_cn for c in top_cards)
        self.log_msg(log or f"{self.pn(target_id)}牌堆顶{amount}张：{names}")

    def _atomic_copy_card(self, player_id, card, params, log, choice, context):
        ps = self.players[player_id]
        target = self._resolve_card_ref(player_id, params.get('card'), card)
        if target is None and isinstance(context, dict):
            context_target = context.get('chosen_card') or context.get('selected_card')
            if isinstance(context_target, CardInstance):
                target = context_target
        if choice and 'target_instance_id' in choice:
            target = ps.find_hand_card(choice['target_instance_id']) or self._find_card_by_instance_id(choice['target_instance_id'])
        if target and self._card_selectable_by_action(target) and ps.can_add_to_hand():
            if card is not None and card.def_id == 'Mimic' and not self._pay_mimic_special_cost(player_id, target, card):
                return
            if card is not None and card.def_id == 'Mimic':
                new_card = self._make_mimic_copy_card(target)
            else:
                new_card = target.copy()
                self._apply_setup_modifiers_to_card(player_id, new_card)
            ps.add_to_hand(new_card)
            self._enforce_unique_cards_for_player(player_id, preferred_card=new_card)
            self._remember_created_card(new_card, context)
            if log:
                self.log_msg(log)
        elif not target:
            self.log_msg(log or f"{self.pn(player_id)}未选择要复制的牌")

    def _atomic_random_discard_from_hand(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        amount = params.get('amount', 1)
        ts = self.players[target_id]
        for _ in range(min(amount, len(ts.hand))):
            c = random.choice(ts.hand)
            ts.hand.remove(c)
            self._discard_card(ts, c)
        self.log_msg(log or f"{self.pn(target_id)}随机弃置{amount}张手牌")

    def _atomic_put_card_to_deck(self, player_id, card, params, log, choice, context):
        position = params.get('position', 'top')
        ps = self.players[player_id]
        if choice and 'target_instance_id' in choice:
            target = ps.find_hand_card(choice['target_instance_id'])
            if target:
                ps.hand.remove(target)
                if position == 'bottom':
                    ps.deck.append(target)
                else:
                    ps.deck.insert(0, target)
                self.log_msg(log or f"{self.pn(player_id)}将{target.name_cn}放入牌堆{position}")
        else:
            self.log_msg(log or f"{self.pn(player_id)}未选择牌")

    def _atomic_shuffle_discard_into_deck(self, player_id, card, params, log, choice, context):
        ps = self.players[player_id]
        ps.deck.extend(ps.discard)
        ps.discard.clear()
        random.shuffle(ps.deck)
        self.log_msg(log or f"{self.pn(player_id)}将弃牌堆洗入牌堆")

    def _atomic_give_card_to_hand(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        card_ref = self._resolve_card_id_ref(player_id, params.get('card', ''), card)
        ts = self.players[target_id]
        if card_ref:
            card_def = CARD_DEFS.get(card_ref) or CARD_DEFS.get(ERROR_CARD_ID)
            if not card_def:
                return
            if card_def.id != ERROR_CARD_ID and not ts.can_add_to_hand():
                return
            new_card = CardInstance(def_id=card_def.id)
            self._apply_setup_modifiers_to_card(target_id, new_card)
            ts.add_to_hand(new_card)
            self._enforce_unique_cards_for_player(target_id, preferred_card=new_card)
            self._remember_created_card(new_card, context)
            if log and card_def.id != ERROR_CARD_ID:
                self.log_msg(log)

    def _atomic_give_magic_orb_to_hand(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if not (0 <= target_id < len(self.players)):
            return
        ts = self.players[target_id]
        card_def = CARD_DEFS.get('ManaOrb') or CARD_DEFS.get(ERROR_CARD_ID)
        if not card_def or (card_def.id != ERROR_CARD_ID and not ts.can_add_to_hand()):
            return
        new_card = CardInstance(def_id=card_def.id)
        new_card.instance_flags.update(normalize_card_flags(['symbiosis', 'exile', 'void']))
        self._apply_setup_modifiers_to_card(target_id, new_card)
        ts.add_to_hand(new_card)
        self._remember_created_card(new_card, context)
        if log and card_def.id != ERROR_CARD_ID:
            self.log_msg(log)

    def _atomic_give_card_to_deck(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        card_ref = self._resolve_card_id_ref(player_id, params.get('card', ''), card)
        position = params.get('position', 'top')
        ts = self.players[target_id]
        if card_ref:
            card_def = CARD_DEFS.get(card_ref) or CARD_DEFS.get(ERROR_CARD_ID)
            if not card_def:
                return
            new_card = CardInstance(def_id=card_def.id)
            self._apply_setup_modifiers_to_card(target_id, new_card)
            if position == 'bottom':
                ts.deck.append(new_card)
            elif position == 'random':
                ts.deck.insert(random.randint(0, len(ts.deck)), new_card)
            else:
                ts.deck.insert(0, new_card)
            self._remember_created_card(new_card, context)
            if log and card_def.id != ERROR_CARD_ID:
                self.log_msg(log)

    def _atomic_give_card_to_discard(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        card_ref = self._resolve_card_id_ref(player_id, params.get('card', ''), card)
        ts = self.players[target_id]
        if card_ref:
            card_def = CARD_DEFS.get(card_ref) or CARD_DEFS.get(ERROR_CARD_ID)
            if not card_def:
                return
            new_card = CardInstance(def_id=card_def.id)
            self._apply_setup_modifiers_to_card(target_id, new_card)
            self._discard_card(ts, new_card)
            self._remember_created_card(new_card, context)
            if log and card_def.id != ERROR_CARD_ID:
                self.log_msg(log)

    def _atomic_remove_specific_card(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        zone = params.get('zone', 'hand')
        card_ref = params.get('card', '')
        ts = self.players[target_id]
        if zone == 'equipment':
            target_card = self._resolve_card_ref(player_id, card_ref, card)
            eq = ts.find_equipment(getattr(target_card, 'instance_id', None)) if target_card is not None else None
            if eq is not None:
                eq_name = eq.card_def.name_cn
                destroyed = self._destroy_equipment(target_id, eq, source_id=player_id)
                if destroyed:
                    self.log_msg(log or f"{self.pn(player_id)}摧毁了{self.pn(target_id)}的{eq_name}")
                elif log:
                    self.log_msg(log)
            return
        zone_map = {'hand': ts.hand, 'deck': ts.deck, 'discard': ts.discard, 'exile': ts.exile}
        target_zone = zone_map.get(zone, ts.hand)
        target_card = self._resolve_card_ref(player_id, card_ref, card)
        matched = [target_card] if target_card in target_zone else []
        if not matched:
            sel = card_ref if isinstance(card_ref, dict) and card_ref.get('selector') else {'selector': 'by_id', 'id': card_ref}
            matched = self._match_card_selector(player_id, target_zone, sel, card)
        if matched:
            c = matched[0]
            target_zone.remove(c)
            self.log_msg(log or f"{self.pn(target_id)}的{c.name_cn}从{zone}中被消除")



    def _atomic_destroy_all_field_equip(self, player_id, card, params, log, choice, context):
        for pid in [0, 1]:
            for eq in self.players[pid].equipment[:]:
                eq_name = eq.card_def.name_cn
                if self._destroy_equipment(pid, eq, source_id=player_id):
                    self.log_msg(log or f"{self.pn(player_id)}摧毁了{self.pn(pid)}的{eq_name}")
                elif log:
                    self.log_msg(log)

    def _atomic_remove_equip_protection(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if not self._valid_player_id(target_id):
            return
        self.players[target_id].equipment_protection = 0
        self.log_msg(log or f"{self.pn(target_id)}的装备保护被移除")


    def _atomic_block_card_type(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if not self._valid_player_id(target_id):
            return
        card_type = params.get('card_type', 'thorn')
        duration = params.get('duration', 1)
        ts = self.players[target_id]
        if self._status_application_blocked(target_id, 'attack_blocked' if card_type == 'thorn' else f'{card_type}_blocked'):
            return
        if card_type == 'thorn':
            ts.attack_blocked = max(ts.attack_blocked, duration)
        elif card_type == 'bloom':
            ts.skill_blocked = getattr(ts, 'skill_blocked', 0)
            ts.skill_blocked = max(ts.skill_blocked, duration)
        self.log_msg(log or f"{self.pn(target_id)}无法使用{card_type}牌{duration}回合")

    def _atomic_force_card_type(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if not self._valid_player_id(target_id):
            return
        card_type = params.get('card_type', 'thorn')
        duration = params.get('duration', 1)
        ts = self.players[target_id]
        if card_type == 'thorn':
            if self._status_application_blocked(target_id, 'attack_only'):
                return
            ts.attack_only = max(ts.attack_only, duration)
        self.log_msg(log or f"{self.pn(target_id)}仅可使用{card_type}牌{duration}回合")

    def _atomic_nullify_current_card(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if not self._valid_player_id(target_id):
            return
        card_type = params.get('card_type', 'thorn')
        ts = self.players[target_id]
        if self._status_application_blocked(target_id, f'negate_{card_type}'):
            return
        ts.negate_next = getattr(ts, 'negate_next', None)
        ts.negate_next = card_type
        self.log_msg(log or f"{self.pn(target_id)}的{card_type}牌将失效")

    def _atomic_skip_turn(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if not self._valid_player_id(target_id):
            return
        amount = int(params.get('amount', 1))
        if self._status_application_blocked(target_id, 'skip_turn'):
            return
        self.players[target_id].skip_turn += amount
        self._note_achievement_status_peak(target_id)
        self.log_msg(log or f"{self.pn(target_id)}+{amount}层眩晕")

    def _atomic_extra_turn(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if not self._valid_player_id(target_id):
            return
        self.players[target_id].extra_turn = True
        self.log_msg(log or f"{self.pn(target_id)}获得一个额外回合")

    def _atomic_force_end_turn(self, player_id, card, params, log, choice, context):
        self.players[player_id].force_end_turn = True
        self.log_msg(log or f"{self.pn(player_id)}强制结束当前回合")

    def _atomic_mark_self_damage_source(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if not self._valid_player_id(target_id):
            return
        self.players[target_id].self_damage_next = True
        self.log_msg(log or f"{self.pn(target_id)}下次伤害来源标记为自身")

    def _atomic_fission(self, player_id, card, params, log, choice, context):
        card_type = params.get('card_type', 'thorn')
        times = self._eval_int(player_id, params.get('times', 1), card, 1)
        ps = self.players[player_id]
        target = ps.find_hand_card(choice.get('target_instance_id')) if isinstance(choice, dict) and 'target_instance_id' in choice else None
        targets = [target] if target is not None else [c for c in ps.hand if c.card_def.card_type == card_type and c is not card]
        targets = [c for c in targets if c and self._card_selectable_by_action(c) and c.card_def.card_type == card_type]
        if targets:
            t = targets[0]
            t.fission_level = clamp_card_layer(max(1, int(getattr(t, 'fission_level', 1))) + times)
            t.fission_count = t.fission_level - 1
            if log:
                self.log_msg(log)
        else:
            self.log_msg(log or f"{self.pn(player_id)}没有可裂变的{card_type}牌")

    def _atomic_multiply_next_damage(self, player_id, card, params, log, choice, context):
        multiplier = self._eval_int(player_id, params.get('multiplier', 1), card, 1)
        ps = self.players[player_id]
        ps.damage_multiplier = getattr(ps, 'damage_multiplier', 1.0) * multiplier
        self.log_msg(log or f"{self.pn(player_id)}下次伤害x{multiplier}")

    def _atomic_reduce_next_cost(self, player_id, card, params, log, choice, context):
        self._atomic_modify_hand_card_cost(player_id, card, params, log, -1)

    def _atomic_increase_next_cost(self, player_id, card, params, log, choice, context):
        self._atomic_modify_hand_card_cost(player_id, card, params, log, 1)

    def _atomic_modify_hand_card_cost(self, player_id, card, params, log, direction: int):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if not (0 <= target_id < len(self.players)):
            return
        amount = abs(self._eval_int(player_id, params.get('amount', 1), card, 1))
        if amount <= 0:
            return
        card_type = str(params.get('card_type', '') or '').strip()
        changed = 0
        for hand_card in list(getattr(self.players[target_id], 'hand', []) or []):
            if card_type and getattr(hand_card.card_def, 'card_type', '') != card_type:
                continue
            if direction < 0:
                hand_card.temp_swift_value = max(0, int(getattr(hand_card, 'temp_swift_value', 0) or 0)) + amount
                hand_card.instance_flags.add('temp_swift')
            else:
                hand_card.temp_heavy_value = max(0, int(getattr(hand_card, 'temp_heavy_value', 0) or 0)) + amount
                hand_card.instance_flags.add('temp_heavy')
            changed += 1
        if changed > 0 and log:
            self.log_msg(log)

    def _merge_fusion_card_layers(self, keep: CardInstance, cards: List[CardInstance]):
        if not keep or not cards:
            return
        keep.fusion_level = clamp_card_layer(sum(clamp_card_layer(getattr(c, 'fusion_level', 1)) for c in cards))
        keep.fission_level = clamp_card_layer(max(clamp_card_layer(getattr(c, 'fission_level', 1)) for c in cards))
        keep.fusion_multiplier = float(keep.fusion_level)
        keep.fission_count = keep.fission_level - 1

        for attr in ('swift_value', 'magic_swift_value', 'power_value', 'bonus_damage', 'temp_swift_value', 'temp_heavy_value', 'temp_magic_heavy_value'):
            setattr(keep, attr, max(0, max(int(getattr(c, attr, 0) or 0) for c in cards)))

        # Layered special-effect tags remain active if any merged card had them.
        keep.instance_flags.update(*(getattr(c, 'instance_flags', set()) or set() for c in cards))
        keep.disabled_flags.intersection_update(*(getattr(c, 'disabled_flags', set()) or set() for c in cards))
        layer_flag_by_attr = {
            'swift_value': 'swift',
            'magic_swift_value': 'magic_swift',
            'power_value': 'power',
            'temp_swift_value': 'temp_swift',
            'temp_heavy_value': 'temp_heavy',
            'temp_magic_heavy_value': 'temp_magic_heavy',
        }
        for attr, flag in layer_flag_by_attr.items():
            if int(getattr(keep, attr, 0) or 0) > 0:
                keep.instance_flags.add(flag)
                keep.disabled_flags.discard(flag)
            elif flag in keep.instance_flags:
                keep.instance_flags.discard(flag)

    def _atomic_fusion(self, player_id, card, params, log, choice, context):
        count = self._eval_int(player_id, params.get('count', params.get('min_count', 2)), card, 2)
        max_count = self._eval_int(player_id, params.get('max_count', count), card, count)
        if getattr(card, 'def_id', '') == 'Fusion':
            count = 2
            max_count = 2
        card_type = params.get('card_type', 'thorn')
        ps = self.players[player_id]
        if isinstance(choice, dict) and 'target_instance_ids' in choice:
            selected = [ps.find_hand_card(i) for i in choice.get('target_instance_ids', [])]
            selected = [c for c in selected if c is not None and self._card_selectable_by_action(c)]
        else:
            selected = [c for c in ps.hand if c.card_def.card_type == card_type and c is not card and self._card_selectable_by_action(c)][:max_count]
        if len(selected) >= count:
            selected = selected[:max_count]
            if any(c.card_def.card_type != card_type for c in selected) or len({c.def_id for c in selected}) != 1:
                self.log_msg(log or f"{self.pn(player_id)}聚变目标无效")
                return
            keep = selected[0]
            self._merge_fusion_card_layers(keep, selected)
            for c in selected[1:]:
                ps.hand.remove(c)
                self._discard_card(ps, c)
            if log:
                self.log_msg(log)
        else:
            self.log_msg(log or f"{self.pn(player_id)}没有足够的{card_type}牌聚变")

    def _atomic_add_tag(self, player_id, card, params, log, choice, context):
        tag = normalize_card_flag(params.get('tag', ''))
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if tag and target_card:
            target_card.instance_flags = getattr(target_card, 'instance_flags', set())
            target_card.instance_flags.add(tag)
            self.log_msg(log or f"{target_card.name_cn}获得标签{tag}")

    def _atomic_third_eye_precision_or_hidden(self, player_id, card, params, log, choice, context):
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'chosen_card'}), card)
        if target_card is None and isinstance(context, dict):
            value = context.get('chosen_card')
            if isinstance(value, CardInstance):
                target_card = value
        if target_card is None:
            return
        if 'precision' in self._effective_card_flags(target_card):
            target_card.instance_flags.add('stealth')
            applied = '隐匿'
        else:
            target_card.instance_flags.add('precision')
            applied = '精准'
        self.log_msg(log or f"{target_card.name_cn}获得{applied}")

    def _atomic_grant_temp_swift_highest_e(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if not self._valid_player_id(target_id):
            return
        amount = max(0, self._eval_int(player_id, params.get('amount', 3), card, 3))
        if amount <= 0:
            return
        candidates = [c for c in self.players[target_id].hand if self._card_selectable_by_action(c)]
        if not candidates:
            return
        max_cost = max(int(getattr(c, 'cost_e', 0) or 0) for c in candidates)
        target_card = next(c for c in candidates if int(getattr(c, 'cost_e', 0) or 0) == max_cost)
        target_card.temp_swift_value = max(int(getattr(target_card, 'temp_swift_value', 0) or 0), amount)
        target_card.instance_flags.add('temp_swift')
        target_card.disabled_flags.discard('temp_swift')
        self.log_msg(log or f"{target_card.name_cn}获得暂时迅捷:{amount}")

    def _atomic_add_tag_to_zone(self, player_id, card, params, log, choice, context):
        """Add a tag to all cards in a zone, optionally filtered by card_type."""
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if not self._valid_player_id(target_id):
            return
        zone = str(params.get('zone', 'hand')).lower()
        tag = str(params.get('tag', '')).strip()
        card_type_filter = str(params.get('card_type', '')).strip().lower()
        if not tag:
            return
        tag = normalize_card_flag(tag)
        ps = self.players[target_id]
        zone_cards = {
            'hand': ps.hand,
            'deck': ps.deck,
            'discard': ps.discard,
            'exile': ps.exile,
        }.get(zone, [])
        count = 0
        for c in zone_cards:
            if card_type_filter and getattr(c, 'card_type', '') != card_type_filter:
                continue
            if tag not in c.flags:
                c.instance_flags.add(tag)
                count += 1
        if log:
            self.log_msg(log)
        else:
            type_desc = f"{card_type_filter}牌" if card_type_filter else "牌"
            self.log_msg(f"{self.pn(player_id)}给{self.pn(target_id)}的{zone}区{count}张{type_desc}添加了{tag}标签")

    def _atomic_cogwheel_mark(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'choice_target'))
        if not (0 <= target_id < len(self.players)):
            return
        if not hasattr(self, '_cogwheel_active'):
            self._cogwheel_active = {}
        if not hasattr(self, '_cogwheel_exclude_instance_ids'):
            self._cogwheel_exclude_instance_ids = {}
        self._cogwheel_active[target_id] = True
        self._cogwheel_exclude_instance_ids[target_id] = int(getattr(card, 'instance_id', -1) or -1)
        self._return_cogwheel_cards_now(target_id)
        if log:
            self.log_msg(log)

    def _atomic_honey_control(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'choice_target'))
        if not (0 <= target_id < len(self.players)):
            return
        duration = max(1, self._eval_int(player_id, params.get('duration', 1), card))
        self.players[target_id].honey_control_turns = max(
            int(getattr(self.players[target_id], 'honey_control_turns', 0) or 0),
            duration,
        )
        self.log_msg(log or f"{self.pn(player_id)}使{self.pn(target_id)}下回合进入自动控制")

    def _atomic_assembler_effect(self, player_id, card, params, log, choice, context):
        """Assembler: choose a hand card to exile, then random effect."""
        ps = self.players[player_id]
        target_id = self._resolve_target(player_id, params.get('target', 'choice_target'))
        if not self._valid_player_id(target_id):
            return
        target_ps = self.players[target_id]
        if choice and isinstance(choice, dict) and 'target_instance_id' in choice:
            # Phase 2: choice resolved, apply effect
            target_id = self._resolve_target(player_id, choice.get('target_player_id', choice.get('target_id', target_id)))
            if not self._valid_player_id(target_id):
                return
            target_ps = self.players[target_id]
            target = ps.find_hand_card(choice['target_instance_id'])
            if target:
                ps.hand.remove(target)
                self._put_card_in_exile(player_id, target)
                self.log_msg(f"{self.pn(player_id)}放逐了{target.name_cn}")
            # Random effect
            import random as _random
            roll = _random.randint(1, 3)
            if roll == 1:
                new_card = CardInstance(def_id='Laser')
                new_card.swift_value = 2
                new_card.instance_flags.add('swift')
                self._apply_setup_modifiers_to_card(target_id, new_card)
                target_ps.add_to_hand(new_card)
                self.log_msg(f"{self.pn(player_id)}的重构机：{self.pn(target_id)}获得激光器")
            elif roll == 2:
                new_card = CardInstance(def_id='Sawblade')
                new_card.swift_value = 2
                new_card.instance_flags.add('swift')
                self._apply_setup_modifiers_to_card(target_id, new_card)
                target_ps.add_to_hand(new_card)
                self.log_msg(f"{self.pn(player_id)}的重构机：{self.pn(target_id)}获得锯片")
            else:
                target_ps.fragment_stacks += 2
                new_card = CardInstance(def_id='Fragment')
                self._apply_setup_modifiers_to_card(target_id, new_card)
                target_ps.add_to_hand(new_card)
                self.log_msg(f"{self.pn(player_id)}的重构机：{self.pn(target_id)}获得2层碎片和1张碎片")
        else:
            # Phase 1: show choice
            hand_cards = [c.to_dict() for c in ps.hand if c.instance_id != card.instance_id]
            if hand_cards:
                self.pending_choice = {
                    'player_id': player_id,
                    'choice_type': 'choose_card_from_hand',
                    'card': card.to_dict(),
                    'hand_cards': hand_cards,
                    'message': '重构机：选择一张手牌放逐',
                    'target_player_id': target_id,
                    'original_choice': {'target_player_id': target_id},
                }

    def _atomic_request_reorder_deck(self, player_id, card, params, log, choice, context):
        """Request reorder of opponent's deck (Magic Goggles)."""
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        target_ps = self.players[target_id]
        deck_cards = [c.to_dict() for c in target_ps.deck]
        if deck_cards:
            self.pending_choice = {
                'player_id': player_id,
                'choice_type': 'reorder_deck',
                'choice_params': {'cancellable': False},
                'card': card.to_dict() if card else {},
                'target_player_id': target_id,
                'deck_cards': deck_cards,
                'message': params.get('message', '调整对手牌堆顺序'),
            }
            if log:
                self.log_msg(log)
            else:
                self.log_msg(f"{self.pn(player_id)}查看并重排{self.pn(target_id)}的牌堆")

    def _atomic_goggles_enable(self, player_id, card, params, log, choice, context):
        """Enable deck+discard ordered viewing for player (Goggles)."""
        target_id = self._resolve_target(player_id, params.get('target', 'choice_target'))
        if not hasattr(self, '_goggles_views') or not isinstance(getattr(self, '_goggles_views', None), dict):
            self._goggles_views = {}
        self._goggles_views.setdefault(player_id, set()).add(target_id)
        if log:
            self.log_msg(log)
        else:
            self.log_msg(f"{self.pn(player_id)}给{self.pn(target_id)}启用了牌堆查看")

    def _goggles_view_targets_for(self, viewer_id: int) -> Set[int]:
        targets: Set[int] = set()
        views = getattr(self, '_goggles_views', None)
        if isinstance(views, dict):
            raw_targets = views.get(viewer_id, set())
            if isinstance(raw_targets, (set, list, tuple)):
                for tid in raw_targets:
                    try:
                        tid_int = int(tid)
                    except (TypeError, ValueError):
                        continue
                    if 0 <= tid_int < len(self.players):
                        targets.add(tid_int)
        # Backward compatibility for older in-memory games before the mapping fix.
        legacy = getattr(self, '_goggles_players', None)
        if isinstance(legacy, set) and viewer_id in legacy:
            targets.add(viewer_id)
        return targets

    def _atomic_reveal_tag_hand(self, player_id, card, params, log, choice, context):
        """Reveal opponent hand cards that have a specific tag. Also adds revealed_tag_cards to state."""
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        tag = str(params.get('tag', 'revealed')).strip()
        opp = self.players[target_id]
        revealed_cards = [c for c in opp.hand if tag in c.flags and not self._card_is_sublime(c)]
        if revealed_cards:
            if not hasattr(self, '_revealed_tag_cards'):
                self._revealed_tag_cards = {}
            self._revealed_tag_cards.setdefault(player_id, [])
            self._revealed_tag_cards[player_id] = [c.to_dict() for c in revealed_cards]
        if log:
            self.log_msg(log)

    def _atomic_remove_tag(self, player_id, card, params, log, choice, context):
        tag = normalize_card_flag(params.get('tag', ''))
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if tag and target_card and hasattr(target_card, 'instance_flags'):
            target_card.instance_flags.discard(tag)
            self.log_msg(log or f"{target_card.name_cn}移除标签{tag}")

    def _atomic_transform_card(self, player_id, card, params, log, choice, context):
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if target_card:
            self.log_msg(log or f"{self.pn(player_id)}变换{target_card.name_cn}效果触发")
        else:
            self.log_msg(log or f"{self.pn(player_id)}变换卡牌效果触发")

    def _atomic_gain_durability(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if target_card:
            target_card.durability = getattr(target_card, 'durability', 0) + amount
            self.log_msg(log or f"{target_card.name_cn}耐久+{amount}")

    def _atomic_lose_durability(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if target_card:
            target_card.durability = max(0, getattr(target_card, 'durability', 0) - amount)
            self.log_msg(log or f"{target_card.name_cn}耐久-{amount}")

    def _atomic_set_durability(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 3)
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if target_card:
            target_card.durability = amount
            self.log_msg(log or f"{target_card.name_cn}耐久设为{amount}")

    def _atomic_record_play_count(self, player_id, card, params, log, choice, context):
        if card:
            card.play_count = getattr(card, 'play_count', 0) + 1
            self.log_msg(log or f"{card.name_cn}打出次数：{card.play_count}")

    def _atomic_record_equip_turns(self, player_id, card, params, log, choice, context):
        if card:
            card.equip_turns = getattr(card, 'equip_turns', 0) + 1
            self.log_msg(log or f"{card.name_cn}装备回合数：{card.equip_turns}")

    def _atomic_reset_counter(self, player_id, card, params, log, choice, context):
        if card:
            card.play_count = 0
            card.equip_turns = 0
            self.log_msg(log or f"{card.name_cn}计数已重置")

    def _atomic_create_counter(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        name = params.get('name', 'counter1')
        if card:
            if not hasattr(card, 'custom_counters'):
                card.custom_counters = {}
            card.custom_counters[name] = card.custom_counters.get(name, 0) + amount
            self.log_msg(log or f"{card.name_cn}计数器{name}+{amount}")

    def _atomic_exile_this(self, player_id, card, params, log, choice, context):
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if not target_card:
            return
        owner_id, _ = self._remove_card_from_current_zone(target_card)
        if owner_id is None:
            owner_id = player_id
        self._put_card_in_exile(owner_id, target_card)
        self.log_msg(log or f"{target_card.name_cn}被放逐")

    def _atomic_move_to_discard(self, player_id, card, params, log, choice, context):
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if not target_card:
            return
        owner_before, _, _ = self._find_card_location(target_card)
        current_iid = getattr(card, 'instance_id', None)
        chosen_cards = (context or {}).get('chosen_cards') if isinstance(context, dict) else None
        active_discard = (
            target_card is not card
            and getattr(target_card, 'instance_id', None) != current_iid
            and isinstance(chosen_cards, list)
            and any(getattr(chosen, 'instance_id', None) == getattr(target_card, 'instance_id', None) for chosen in chosen_cards)
        )
        owner_id, _ = self._remove_card_from_current_zone(target_card)
        if owner_id is None:
            owner_id = owner_before if owner_before is not None else player_id
        self._discard_card(self.players[owner_id], target_card)
        if active_discard:
            self._record_ocean_active_discard(owner_id, 1)
        if params.get('silent') or params.get('hide_log') or (isinstance(context, dict) and context.get('suppress_detail_logs')):
            return
        self.log_msg(log or f"{target_card.name_cn}移入弃牌堆")

    def _atomic_move_to_hand(self, player_id, card, params, log, choice, context):
        is_magnet = str(getattr(card, 'def_id', '') or '').lower().endswith('magnet')
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'selected_card'}), card)
        if not target_card:
            if is_magnet:
                self._clear_hand_reveal_for_player(player_id)
            return
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if not (0 <= target_id < len(self.players)):
            if is_magnet:
                self._clear_hand_reveal_for_player(player_id)
            return
        if not self.players[target_id].can_add_to_hand():
            if is_magnet:
                self._clear_hand_reveal_for_player(player_id)
            return
        owner_id, zone_name = self._remove_card_from_current_zone(target_card)
        self.players[target_id].add_to_hand(target_card)
        if is_magnet:
            if owner_id is not None and owner_id != target_id and zone_name == 'hand':
                self.log_msg(log or f"{self.pn(player_id)}用磁铁从{self.pn(owner_id)}手牌中获得了{target_card.name_cn}")
            self._clear_hand_reveal_for_player(player_id)

    def _atomic_move_to_deck(self, player_id, card, params, log, choice, context):
        position = params.get('position', 'top')
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if not target_card:
            return
        owner_id, _ = self._remove_card_from_current_zone(target_card)
        if owner_id is None:
            owner_id = player_id
        if position == 'bottom':
            self.players[owner_id].deck.append(target_card)
        elif position == 'random':
            insert_at = random.randint(0, len(self.players[owner_id].deck))
            self.players[owner_id].deck.insert(insert_at, target_card)
        else:
            self.players[owner_id].deck.insert(0, target_card)
        if params.get('silent') or params.get('no_log'):
            return
        self.log_msg(log or f"{target_card.name_cn}移入牌堆{position}")

    def _atomic_global_damage_mult(self, player_id, card, params, log, choice, context):
        multiplier = params.get('multiplier', 1.0)
        self.global_damage_mult = getattr(self, 'global_damage_mult', 1.0) * multiplier
        self.log_msg(log or f"全场伤害倍率x{multiplier}")

    def _atomic_global_heal_mult(self, player_id, card, params, log, choice, context):
        multiplier = params.get('multiplier', 1.0)
        self.global_heal_mult = getattr(self, 'global_heal_mult', 1.0) * multiplier
        self.log_msg(log or f"全场治疗倍率x{multiplier}")

    def _atomic_global_cost_mult(self, player_id, card, params, log, choice, context):
        multiplier = params.get('multiplier', 1.0)
        self.global_cost_mult = getattr(self, 'global_cost_mult', 1.0) * multiplier
        self.log_msg(log or f"全场费用倍率x{multiplier}")

    def _atomic_swap_health(self, player_id, card, params, log, choice, context):
        t1 = self._resolve_target(player_id, params.get('target1', 'self'))
        t2 = self._resolve_target(player_id, params.get('target2', 'enemy'))
        h1 = self.players[t1].health
        h2 = self.players[t2].health
        self.players[t1].health = h2
        self.players[t2].health = h1
        self._note_achievement_health(t1)
        self._note_achievement_health(t2)
        self.log_msg(log or f"{self.pn(t1)}与{self.pn(t2)}交换生命值")

    def _atomic_swap_hands(self, player_id, card, params, log, choice, context):
        t1 = self._resolve_target(player_id, params.get('target1', 'self'))
        t2 = self._resolve_target(player_id, params.get('target2', 'enemy'))
        self.players[t1].hand, self.players[t2].hand = self.players[t2].hand, self.players[t1].hand
        self.log_msg(log or f"{self.pn(t1)}与{self.pn(t2)}交换手牌")

    def _atomic_broadcast_event(self, player_id, card, params, log, choice, context):
        event_name = params.get('event_name', '')
        self.log_msg(log or f"广播事件：{event_name}")

    def _atomic_modify_damage(self, player_id, card, params, log, choice, context):
        formula = params.get('formula', 'value')
        self.log_msg(log or f"修改伤害公式：{formula}")




    def _atomic_if(self, player_id, card, params, log, choice, context):
        if self._eval_condition(player_id, params.get('condition'), card):
            self._run_effect_list(player_id, card, params.get('then', []), choice, context)

    def _atomic_if_else(self, player_id, card, params, log, choice, context):
        if self._eval_condition(player_id, params.get('condition'), card):
            self._run_effect_list(player_id, card, params.get('then', []), choice, context)
        else:
            self._run_effect_list(player_id, card, params.get('else', []), choice, context)

    def _atomic_repeat(self, player_id, card, params, log, choice, context):
        times = max(0, int(self._eval_expr(player_id, params.get('times', 1), card)))
        body = params.get('body', [])
        base_context = context if isinstance(context, dict) else ({'context': context} if context else {})
        for index in range(times):
            try:
                self._run_effect_list(player_id, card, body, choice, {**base_context, 'repeat_index': index + 1})
            except ModLoopContinue:
                continue
            except ModLoopBreak:
                break

    def _atomic_repeat_until(self, player_id, card, params, log, choice, context):
        body = params.get('body', [])
        max_loops = 64
        loops = 0
        base_context = context if isinstance(context, dict) else ({'context': context} if context else {})
        while loops < max_loops and not self._eval_condition(player_id, params.get('condition'), card):
            try:
                self._run_effect_list(player_id, card, body, choice, {**base_context, 'repeat_index': loops + 1})
            except ModLoopContinue:
                loops += 1
                continue
            except ModLoopBreak:
                break
            loops += 1

    def _atomic_for_each(self, player_id, card, params, log, choice, context):
        body = params.get('body', [])
        base_context = context if isinstance(context, dict) else ({'context': context} if context else {})
        for index, tid in enumerate(self._resolve_targets(player_id, params.get('targets', 'friendly')), start=1):
            try:
                self._run_effect_list(tid, card, body, choice, {**base_context, 'loop_player_id': tid, 'loop_index': index})
            except ModLoopContinue:
                continue
            except ModLoopBreak:
                break

    def _atomic_for_each_selected_card(self, player_id, card, params, log, choice, context):
        active_choice = choice if isinstance(choice, dict) else getattr(self, '_active_choice', None)
        if not isinstance(active_choice, dict):
            return
        ids = active_choice.get('target_instance_ids')
        if not isinstance(ids, list):
            ids = [active_choice.get('target_instance_id')] if active_choice.get('target_instance_id') is not None else []
        ids_snapshot = list(ids)
        original_id = active_choice.get('target_instance_id')
        original_index = active_choice.get('_selected_card_index')
        original_snapshot = active_choice.get('_selected_card_ids_snapshot')
        body = params.get('body', [])
        base_context = context if isinstance(context, dict) else ({'context': context} if context else {})
        try:
            active_choice['_selected_card_ids_snapshot'] = ids_snapshot
            for idx, instance_id in enumerate(ids_snapshot, start=1):
                selected_card = self._find_card_by_instance_id(instance_id)
                if selected_card is not None and not self._card_selectable_by_action(selected_card):
                    selected_card = None
                active_choice['target_instance_id'] = instance_id
                active_choice['_selected_card_index'] = idx
                try:
                    child_context = {**base_context, 'selected_card_index': idx}
                    if selected_card is not None:
                        child_context['chosen_card'] = selected_card
                        child_context['selected_card'] = selected_card
                    self._run_effect_list(player_id, card, body, active_choice, child_context)
                except ModLoopContinue:
                    continue
                except ModLoopBreak:
                    break
        finally:
            if original_id is None:
                active_choice.pop('target_instance_id', None)
            else:
                active_choice['target_instance_id'] = original_id
            if original_index is None:
                active_choice.pop('_selected_card_index', None)
            else:
                active_choice['_selected_card_index'] = original_index
            if original_snapshot is None:
                active_choice.pop('_selected_card_ids_snapshot', None)
            else:
                active_choice['_selected_card_ids_snapshot'] = original_snapshot

    def _atomic_break(self, player_id, card, params, log, choice, context):
        raise ModLoopBreak()

    def _atomic_continue(self, player_id, card, params, log, choice, context):
        raise ModLoopContinue()

    def _atomic_after_all(self, player_id, card, params, log, choice, context):
        self._run_effect_list(player_id, card, params.get('body', []), choice, context)

    def _atomic_random(self, player_id, card, params, log, choice, context):
        branch = params.get('a', []) if random.random() < 0.5 else params.get('b', [])
        self._run_effect_list(player_id, card, branch, choice, context)












    def _atomic_batch_status_add(self, player_id, card, params, log, choice, context):
        for tid in self._resolve_targets(player_id, params.get('targets', 'friendly')):
            self._atomic_status_add_named(player_id, card, {'target': 'self' if tid == player_id else 'enemy', 'status': params.get('status', ''), 'amount': params.get('amount', 1)}, log, choice, context)

    def _atomic_batch_status_remove(self, player_id, card, params, log, choice, context):
        for tid in self._resolve_targets(player_id, params.get('targets', 'friendly')):
            self._atomic_status_remove_named(player_id, card, {'target': 'self' if tid == player_id else 'enemy', 'status': params.get('status', '')}, log, choice, context)

    def _atomic_tag_add_named(self, player_id, card, params, log, choice, context):
        tag = normalize_card_flag(params.get('tag', ''))
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if tag and target_card:
            target_card.instance_flags = getattr(target_card, 'instance_flags', set())
            target_card.instance_flags.add(tag)
            self.log_msg(log or f"{target_card.name_cn}添加标签[{tag}]")

    def _atomic_tag_remove_named(self, player_id, card, params, log, choice, context):
        tag = normalize_card_flag(params.get('tag', ''))
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if tag and target_card:
            target_card.instance_flags = getattr(target_card, 'instance_flags', set())
            target_card.instance_flags.discard(tag)
            self.log_msg(log or f"{target_card.name_cn}移除标签[{tag}]")

    def _atomic_batch_tag_add(self, player_id, card, params, log, choice, context):
        self._atomic_tag_add_named(player_id, card, {'tag': params.get('tag', '')}, log, choice, context)

    def _atomic_batch_tag_remove(self, player_id, card, params, log, choice, context):
        self._atomic_tag_remove_named(player_id, card, {'tag': params.get('tag', '')}, log, choice, context)

    def _is_status_immune(self, player_id: int) -> bool:
        ps = self.players[player_id]
        custom = getattr(ps, 'custom_statuses', {}) or {}
        for key in ('status_immune', 'immune', '状态免疫'):
            raw = custom.get(key, 0)
            if isinstance(raw, dict):
                raw = raw.get('stacks', raw.get('stack', raw.get('value', raw.get('layers', 0))))
            try:
                if int(raw or 0) > 0:
                    return True
            except Exception:
                if raw:
                    return True
        return False

    def _is_suppressed_status_var(self, player_id: int, name: str) -> bool:
        """Return true when a custom variable is an alias for a suppressed built-in status."""
        try:
            player_id = int(player_id)
        except Exception:
            return False
        if not (0 <= player_id < len(self.players)):
            return False
        if not self._is_status_immune(player_id):
            return False
        return str(name) in ('三角形层数', '\u4e09\u89d2\u5f62\u5c42\u6570')

    def _modified_attack_damage(self, base: int, card: CardInstance) -> int:
        bonus_damage = max(0, int(getattr(card, 'bonus_damage', 0)))
        if getattr(card, 'def_id', '') == 'Tomato':
            bonus_damage = min(18, bonus_damage)
        base += bonus_damage
        fusion = max(1, int(getattr(card, 'fusion_level', 1)))
        fission = max(1, int(getattr(card, 'fission_level', 1)))
        return math.ceil(base * fusion / fission)

    def _fission_dmg(self, base: int, card: CardInstance) -> int:
        return self._modified_attack_damage(base, card)

    def _effect_basic(self, player_id: int, card: CardInstance, choice=None):
        dmg = self._modified_attack_damage(6, card)
        self.log_msg(f"{self.pn(player_id)}使用基本攻击！造成{dmg}伤害")
        self.deal_attack_damage(1 - player_id, dmg)

    def _effect_bone(self, player_id: int, card: CardInstance, choice=None):
        dmg = self._modified_attack_damage(12, card)
        self.log_msg(f"{self.pn(player_id)}使用骨头！造成{dmg}伤害")
        self.deal_attack_damage(1 - player_id, dmg)

    def _effect_stinger(self, player_id: int, card: CardInstance, choice=None):
        dmg = self._modified_attack_damage(20, card)
        self.log_msg(f"{self.pn(player_id)}使用刺！造成{dmg}伤害")
        self.deal_attack_damage(1 - player_id, dmg, is_precision=True)

    def _effect_sand(self, player_id: int, card: CardInstance, choice=None):
        dmg = self._modified_attack_damage(3, card)
        hits = self._card_total_hits(card, 4)
        self.log_msg(f"{self.pn(player_id)}使用沙子！造成{dmg}x{hits}伤害")
        self.deal_attack_damage(1 - player_id, dmg, hits)

    def _effect_wing(self, player_id: int, card: CardInstance, choice=None):
        dmg = self._modified_attack_damage(8, card)
        hits = self._card_total_hits(card, 2)
        self.log_msg(f"{self.pn(player_id)}使用翅膀！造成{dmg}x{hits}伤害")
        self.deal_attack_damage(1 - player_id, dmg, hits)

    def _effect_light(self, player_id: int, card: CardInstance, choice=None):
        dmg = self._modified_attack_damage(2, card)
        hits = self._card_total_hits(card, 2)
        self.log_msg(f"{self.pn(player_id)}使用轻！造成{dmg}x{hits}伤害")
        self.deal_attack_damage(1 - player_id, dmg, hits)

    def _effect_fang(self, player_id: int, card: CardInstance, choice=None):
        dmg = self._modified_attack_damage(8, card)
        dealt = self.deal_attack_damage(1 - player_id, dmg)
        if dealt > 0:
            heal = max(0, int(math.floor(int(dealt or 0) * 0.8)))
            if heal > 0:
                self.players[player_id].heal(heal)
            self.log_msg(f"{self.pn(player_id)}使用尖牙！造成{dealt}伤害，回复{heal}H")
        else:
            self.log_msg(f"{self.pn(player_id)}使用尖牙！未造成伤害")

    def _effect_triangle(self, player_id: int, card: CardInstance, choice=None):
        ps = self.players[player_id]
        immune = self._is_status_immune(player_id)
        base = 6 + (0 if immune else 3 * ps.triangle_stacks)
        dmg = self._modified_attack_damage(base, card)
        if int(getattr(card, 'fission_hit', 0) or 0) == 0:
            self._log_card_play(player_id, card)
        dealt = self.deal_attack_damage(1 - player_id, dmg)
        if dealt > 0 and not immune:
            if ps.triangle_stacks < 4:
                ps.triangle_stacks += 1

    def _effect_magicbone(self, player_id: int, card: CardInstance, choice=None):
        dmg = self._modified_attack_damage(15, card)
        self.deal_attack_damage(1 - player_id, dmg)
        self.log_msg(f"{self.pn(player_id)}使用魔法骨头！造成{dmg}伤害")

    def _effect_magicstinger(self, player_id: int, card: CardInstance, choice=None):
        dmg = self._modified_attack_damage(30, card)
        self.deal_attack_damage(1 - player_id, dmg, is_precision=True)
        self.log_msg(f"{self.pn(player_id)}使用魔法刺！造成{dmg}伤害")

    def _effect_fission(self, player_id: int, card: CardInstance, choice=None):
        ps = self.players[player_id]
        if choice and 'target_instance_id' in choice:
            target = ps.find_hand_card(choice['target_instance_id'])
            if target and self._card_selectable_by_action(target) and target.card_type == 'thorn':
                target.fission_level = clamp_card_layer(max(1, int(getattr(target, 'fission_level', 1))) + 2)
                target.fission_count = target.fission_level - 1
                self.log_msg(f"{self.pn(player_id)}使用裂变")
            else:
                self.log_msg(f"{self.pn(player_id)}使用裂变，但目标无效")
        else:
            self.log_msg(f"{self.pn(player_id)}使用裂变，但未选择目标")

    def _effect_fusion(self, player_id: int, card: CardInstance, choice=None):
        ps = self.players[player_id]
        if choice and 'target_instance_ids' in choice:
            ids = choice['target_instance_ids']
            if len(ids) < 2:
                self.log_msg(f"{self.pn(player_id)}使用聚变，但选择不足2张")
                return
            cards = [ps.find_hand_card(i) for i in ids]
            cards = [c for c in cards if c is not None and self._card_selectable_by_action(c)]
            if len(cards) < 2:
                return
            if len(cards) != 2:
                cards = cards[:2]
            if any(c.card_type != 'thorn' for c in cards) or len({c.def_id for c in cards}) != 1:
                self.log_msg(f"{self.pn(player_id)}使用聚变，但目标不是同名攻击牌")
                return
            first = cards[0]
            self._merge_fusion_card_layers(first, cards)
            for c in cards[1:]:
                ps.hand.remove(c)
                self._discard_card(ps, c)
            self.log_msg(f"{self.pn(player_id)}使用聚变")
        else:
            self.log_msg(f"{self.pn(player_id)}使用聚变，但未选择目标")

    def _effect_iris(self, player_id: int, card: CardInstance, choice=None):
        if self._status_application_blocked(1 - player_id, 'poison'):
            return
        self.players[1 - player_id].poison += 10
        self.log_msg(f"{self.pn(player_id)}使用鸢尾！敌方+10中毒")

    def _effect_fire(self, player_id: int, card: CardInstance, choice=None):
        if self._status_application_blocked(1 - player_id, 'fire'):
            return
        self.players[1 - player_id].fire += 2
        self.log_msg(f"{self.pn(player_id)}使用火！敌方+2灼烧")

    def _effect_fries(self, player_id: int, card: CardInstance, choice=None):
        self.players[player_id].heal(12)
        self.log_msg(f"{self.pn(player_id)}使用薯条：+12H")

    def _effect_rose(self, player_id: int, card: CardInstance, choice=None):
        self.players[player_id].heal(7)
        self.log_msg(f"{self.pn(player_id)}使用玫瑰：+7H")

    def _effect_manaorb(self, player_id: int, card: CardInstance, choice=None):
        self.players[player_id].gain_magic(3)
        self.log_msg(f"{self.pn(player_id)}使用魔法球：+3M")

    def _effect_coffee(self, player_id: int, card: CardInstance, choice=None):
        prev_choice = getattr(self, '_active_choice', None)
        if isinstance(choice, dict):
            self._active_choice = choice
        try:
            target_id = self._resolve_target(player_id, 'choice_target')
        finally:
            self._active_choice = prev_choice
        if not (0 <= target_id < len(self.players)):
            target_id = player_id
        ps = self.players[target_id]
        bonus = 1
        coffee_var = '\u5496\u5561\u9996\u6b21\u4f7f\u7528'
        first_marker = int(ps.custom_vars.get(coffee_var, 1 if ps.coffee_first_use else 0))
        if ps.coffee_first_use and first_marker > 0:
            bonus = 2
        ps.coffee_first_use = False
        ps.custom_vars[coffee_var] = 0
        ps.gain_elixir(bonus)
        self.log_msg(f"{self.pn(target_id)}使用咖啡：+{bonus}E")

    def _effect_chilli(self, player_id: int, card: CardInstance, choice=None):
        ps = self.players[player_id]
        if choice and 'target_instance_id' in choice:
            target = ps.find_hand_card(choice['target_instance_id'])
            if target and self._card_selectable_by_action(target):
                ps.remove_hand_card(target.instance_id)
                self._discard_card(ps, target)
                ps.draw_cards(1)
                self.log_msg(f"{self.pn(player_id)}使用辣椒，弃1张并抽1张牌")
        else:
            ps.draw_cards(1)
            self.log_msg(f"{self.pn(player_id)}使用辣椒，抽1张牌")

    def _effect_chromosome(self, player_id: int, card: CardInstance, choice=None):
        ps = self.players[player_id]
        if choice and 'target_instance_id' in choice:
            for i, c in enumerate(ps.discard):
                if c.instance_id == choice['target_instance_id'] and self._card_selectable_by_action(c):
                    found = ps.discard.pop(i)
                    if ps.can_add_to_hand():
                        found.instance_flags.add('symbiosis')
                        ps.add_to_hand(found)
                    else:
                        ps.discard.append(found)
                    self.log_msg(f"{self.pn(player_id)}使用了{card.name_cn}")
                    return
        if choice and 'target_def_id' in choice:
            target_def = choice['target_def_id']
            for i, c in enumerate(ps.discard):
                if c.def_id == target_def and self._card_selectable_by_action(c):
                    found = ps.discard.pop(i)
                    if ps.can_add_to_hand():
                        found.instance_flags.add('symbiosis')
                        ps.add_to_hand(found)
                    else:
                        ps.discard.append(found)
                    self.log_msg(f"{self.pn(player_id)}使用了{card.name_cn}")
                    return
        self.log_msg(f"{self.pn(player_id)}使用了{card.name_cn}，但未找到目标")

    def _effect_sewage(self, player_id: int, card: CardInstance, choice=None):
        opp = self.players[1 - player_id]
        if choice and 'target_instance_id' in choice:
            eq = opp.find_equipment(choice['target_instance_id'])
            if eq and 'indestructible' not in eq.card_instance.flags:
                destroyed = self._destroy_equipment(1 - player_id, eq, source_id=player_id)
                if destroyed:
                    self.log_msg(f"{self.pn(player_id)}使用污水！摧毁了敌方的{eq.card_def.name_cn}")
                else:
                    self.log_msg(f"{self.pn(player_id)}使用污水，但装备保护抵消了摧毁")
            else:
                self.log_msg(f"{self.pn(player_id)}使用污水，但没有可摧毁的装备")
        else:
            destroyable = [e for e in opp.equipment if 'indestructible' not in e.card_instance.flags]
            if destroyable:
                eq = destroyable[0]
                destroyed = self._destroy_equipment(1 - player_id, eq, source_id=player_id)
                if destroyed:
                    self.log_msg(f"{self.pn(player_id)}使用污水！摧毁了敌方的{eq.card_def.name_cn}")
                else:
                    self.log_msg(f"{self.pn(player_id)}使用污水，但装备保护抵消了摧毁")
            else:
                self.log_msg(f"{self.pn(player_id)}使用污水，但没有可摧毁的装备")

    def _effect_magicsewage(self, player_id: int, card: CardInstance, choice=None):
        destroyed_count = 0
        for pid in range(len(self.players)):
            p = self.players[pid]
            to_destroy = [e for e in p.equipment if 'indestructible' not in e.card_instance.flags]
            for eq in to_destroy:
                destroyed = self._destroy_equipment(pid, eq, source_id=player_id)
                if destroyed:
                    destroyed_count += 1
                    self.log_msg(f"魔法污水摧毁了{self.pn(pid)}的{eq.card_def.name_cn}")
                else:
                    self.log_msg(f"魔法污水试图摧毁{self.pn(pid)}的{eq.card_def.name_cn}，但装备保护抵消了")
        if destroyed_count > 0:
            self.players[player_id].gain_elixir(destroyed_count)
            self.log_msg(f"{self.pn(player_id)}回复{destroyed_count}E")

    def _effect_mimic(self, player_id: int, card: CardInstance, choice=None):
        ps = self.players[player_id]
        if choice and 'target_instance_id' in choice:
            target = ps.find_hand_card(choice['target_instance_id'])
            if target:
                if not self._pay_mimic_special_cost(player_id, target, card):
                    return
                copy_card = self._make_mimic_copy_card(target)
                copy_card.mimic_discount = 0
                if ps.can_add_to_hand():
                    ps.add_to_hand(copy_card)
                    self._enforce_unique_cards_for_player(player_id, preferred_card=copy_card)
                    self.log_msg(f"{self.pn(player_id)}使用了{card.name_cn}")
                else:
                    self.log_msg(f"{self.pn(player_id)}使用了{card.name_cn}，但手牌已满")

    def _effect_yggdrasil(self, player_id: int, card: CardInstance, choice=None):
        target_id = self._choice_target_from_choice(choice, player_id)
        if not (0 <= target_id < len(self.players)):
            target_id = player_id
        if self.players[target_id].health <= 0:
            self._trigger_yggdrasil_effect(target_id, card, source_player_id=player_id, exile_played_card=True)
        else:
            self.players[target_id].heal(20)
            self.log_msg(f"{self.pn(player_id)}使用世界树之叶！{self.pn(target_id)}回复20H")

    def _effect_leaf(self, player_id: int, card: CardInstance, choice=None):
        pass

    def _effect_yucca(self, player_id: int, card: CardInstance, choice=None):
        pass

    def _effect_disc(self, player_id: int, card: CardInstance, choice=None):
        pass

    def _effect_battery(self, player_id: int, card: CardInstance, choice=None):
        pass

    def _effect_magicleaf(self, player_id: int, card: CardInstance, choice=None):
        pass

    def _effect_magicyucca(self, player_id: int, card: CardInstance, choice=None):
        pass

    def _effect_magicbattery(self, player_id: int, card: CardInstance, choice=None):
        pass

    def _effect_powder(self, player_id: int, card: CardInstance, choice=None):
        pass

    def _effect_goldenleaf(self, player_id: int, card: CardInstance, choice=None):
        pass

    def _effect_pincer(self, player_id: int, card: CardInstance, choice=None):
        pass

    def _effect_cancer(self, player_id: int, card: CardInstance, choice=None):
        opp = self.players[1 - player_id]
        if self._status_application_blocked(1 - player_id, 'toxic'):
            return
        opp.toxic += 1
        self.log_msg(f"{self.pn(player_id)}装备了癌细胞！敌方+1淬毒")

    def _effect_corruption(self, player_id: int, card: CardInstance, choice=None):
        self.log_msg(f"{self.pn(player_id)}装备了腐化！下回合起全场伤害x1.5")

    def _effect_mark(self, player_id: int, card: CardInstance, choice=None):
        pass

    def _effect_mine(self, player_id: int, card: CardInstance, choice=None):
        pass

    def _refresh_equipment_derived_player_flags(self, player_id: int = -1):
        for ps in self.players:
            ps.sponge_active = False
        for owner_id, owner_state in enumerate(self.players):
            for eq in list(getattr(owner_state, 'equipment', []) or []):
                if not self._equipment_is(eq, 'Sponge', 'ocean:sponge', 'troll_cards:sponge', 'vanilla:sponge'):
                    continue
                target_id = self._equipment_effect_target_id(eq, owner_id)
                if self._status_application_blocked(target_id, 'sponge_active'):
                    continue
                self.players[target_id].sponge_active = True

        # Pill applies status immunity through its card event to the chosen effect target.
        # Equipment itself stays in the user's equipment area, so deriving the status from
        # the equipment owner would incorrectly make both players immune.
        for pid in range(len(self.players)):
            self._hel_sync_crit_multiplier_display(pid)

    def _clear_status_immune_aliases(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        ps.custom_statuses = getattr(ps, 'custom_statuses', {}) or {}
        for key in ('status_immune', 'immune', '状态免疫'):
            ps.custom_statuses.pop(key, None)

    def _equipment_effect_target_id(self, eq: EquipmentInstance, fallback_owner_id: int) -> int:
        try:
            target_id = int(getattr(eq, 'effect_target', fallback_owner_id))
        except Exception:
            target_id = fallback_owner_id
        if not (0 <= target_id < len(self.players)):
            target_id = fallback_owner_id
        return target_id

    def _has_other_pill_targeting(self, target_id: int, exclude_eq: Optional[EquipmentInstance] = None) -> bool:
        if not (0 <= target_id < len(self.players)):
            return False
        for owner_id, player in enumerate(self.players):
            for candidate in getattr(player, 'equipment', []) or []:
                if candidate is exclude_eq:
                    continue
                if not self._equipment_is(candidate, 'Pill', 'vanilla:pill', 'troll_cards:pill'):
                    continue
                if self._equipment_effect_target_id(candidate, owner_id) == target_id:
                    return True
        return False

    def _has_other_sponge_targeting(self, target_id: int, exclude_eq: Optional[EquipmentInstance] = None) -> bool:
        if not (0 <= target_id < len(self.players)):
            return False
        for owner_id, player in enumerate(self.players):
            for candidate in getattr(player, 'equipment', []) or []:
                if candidate is exclude_eq:
                    continue
                if not self._equipment_is(candidate, 'Sponge', 'ocean:sponge', 'troll_cards:sponge', 'vanilla:sponge'):
                    continue
                if self._equipment_effect_target_id(candidate, owner_id) == target_id:
                    return True
        return False

    def _cleanup_equipment_derived_effects(self, owner_id: int, eq: EquipmentInstance,
                                           *, run_destroy_event: bool = True) -> None:
        if not (0 <= owner_id < len(self.players)) or eq is None:
            return
        effect_target_id = self._equipment_effect_target_id(eq, owner_id)
        if self._equipment_is(eq, 'Disc', 'vanilla:disc'):
            self.players[effect_target_id].armor = max(0, self.players[effect_target_id].armor - 2)
        if self._equipment_is(eq, 'ElectricWeb', 'factory:electricweb'):
            self._cleanup_electric_web_draw_damage(eq)

        is_pill = self._equipment_is(eq, 'Pill', 'vanilla:pill', 'troll_cards:pill')
        has_destroy_script = self._has_card_event(eq.card_def, 'equipment_destroy')
        if run_destroy_event and has_destroy_script:
            self._run_card_event(owner_id, eq.card_instance, 'equipment_destroy', None,
                                 {'source_id': owner_id, 'target_id': effect_target_id,
                                  'equipment_owner_id': owner_id})
        elif (
            self._equipment_is(eq, 'Sponge', 'ocean:sponge', 'troll_cards:sponge', 'vanilla:sponge')
            and self.players[effect_target_id].sponge_active
            and not self._has_other_sponge_targeting(effect_target_id, exclude_eq=eq)
        ):
            target_state = self.players[effect_target_id]
            poison_layers = target_state.poison
            target_state.sponge_active = False
            target_state.poison = 0
            if poison_layers > 0:
                physical_dmg = poison_layers * 2
                target_state.health -= physical_dmg
                self._note_achievement_health(effect_target_id)
                self.log_msg(f"海绵被摧毁！{self.pn(effect_target_id)}去除{poison_layers}层中毒，受到{physical_dmg}点物理伤害")
                self._check_yggdrasil(effect_target_id)
            else:
                self.log_msg("海绵被摧毁！无中毒层数")

        if is_pill:
            if not (run_destroy_event and has_destroy_script):
                self._clear_status_immune_aliases(effect_target_id)
                self.log_msg("药丸被摧毁！状态免疫失效")
            # Clean up immunity that may have been applied to the equipment owner by older
            # owner-derived Pill logic. Keep it if another active Pill still targets them.
            if owner_id != effect_target_id and not self._has_other_pill_targeting(owner_id, exclude_eq=eq):
                self._clear_status_immune_aliases(owner_id)

        root_layers = 0
        try:
            root_layers = int((getattr(eq, 'custom_vars', {}) or {}).get('jungle_root_layers', 0) or 0)
        except Exception:
            root_layers = 0
        if root_layers > 0:
            current = self._custom_status_value(effect_target_id, 'jungle:root_status', 'jungle:root', 'root_status')
            self._set_custom_status_alias_group(
                effect_target_id,
                'jungle:root_status',
                ('jungle:root_status', 'jungle:root', 'root_status'),
                max(0, current - root_layers),
            )
            eq.custom_vars['jungle_root_layers'] = 0

    def _destroy_equipment(self, owner_id: int, eq: EquipmentInstance, check_protection: bool = True,
                           source_id: Optional[int] = None) -> bool:
        ps = self.players[owner_id]
        if 'indestructible' in eq.card_instance.flags:
            return False
        if check_protection and int(getattr(eq, 'armor', 0) or 0) > 0:
            eq.armor = max(0, int(getattr(eq, 'armor', 0) or 0) - 1)
            self.log_msg(f"{self.pn(owner_id)}的{eq.card_def.name_cn}装备护甲抵消了摧毁（剩余{eq.armor}）")
            return False
        if check_protection and ps.equipment_protection > 0:
            ps.equipment_protection -= 1
            self.log_msg(f"{self.pn(owner_id)}的装备保护抵消了摧毁！")
            return False
        self._cleanup_equipment_derived_effects(owner_id, eq, run_destroy_event=True)
        ps.equipment.remove(eq)
        if 'exile' in eq.card_instance.flags:
            self._put_card_in_exile(owner_id, eq.card_instance)
        else:
            self._discard_card(ps, eq.card_instance)
        self._refresh_equipment_derived_player_flags(owner_id)
        self._refresh_hand_limit_bonuses()
        self._note_achievement_equipment_destroyed(source_id)
        self._note_achievement_equipment_count(owner_id)
        self._dispatch_card_event('equipment_destroyed', owner_id if source_id is None else source_id,
                                  eq.card_instance, target_id=owner_id,
                                  equipment=eq, equipment_owner_id=owner_id)
        return True

    def check_equipment_destroy_response(self, owner_id: int, eq: EquipmentInstance) -> dict:
        ps = self.players[owner_id]
        has_magic_nazar = any(c.card_def.response_trigger == 'equipment_destroy' for c in ps.hand)
        if has_magic_nazar and ps.equipment_protection == 0 and int(getattr(eq, 'armor', 0) or 0) <= 0:
            return {'needs_response': True, 'response_type': 'equipment_destroy',
                    'equipment': eq.to_dict(), 'owner_id': owner_id}
        return {'needs_response': False}


    def end_turn(self, player_id: int) -> dict:
        if self.current_player != player_id:
            return {'success': False, 'error': '不是你的回合'}
        if self.pending_response is not None:
            return {'success': False, 'error': '等待对手反制响应'}
        self._end_player_turn(player_id)
        return {'success': True}

    def _end_player_turn(self, player_id: int):
        ps = self.players[player_id]
        opp = self.players[1 - player_id]
        self._run_v2_event_hooks('turn_end', {
            'source_player': player_id,
            'target_player': player_id,
            'vars': {'player_id': player_id},
            'current_action': {'player_id': player_id},
        })
        if self.game_over or getattr(self, 'pending_v2_ui', None):
            return
        self._run_hand_owner_turn_end_events(player_id)
        if self.game_over or getattr(self, 'pending_v2_ui', None):
            return
        self._clear_ocean_card_hand_blind_turn_end(player_id)
        self._trigger_v2_status_events_for_player(player_id, 'on_turn_end', {'player_id': player_id})
        if self.game_over or getattr(self, 'pending_v2_ui', None):
            return
        self._run_owner_turn_end_equipment(player_id)
        if self.game_over or getattr(self, 'pending_v2_ui', None):
            return
        self._decay_equipment_armor_end_turn(player_id)
        if ps.bandage_death_pending and self._should_expire_invincible_on_turn_end(player_id):
            ps.health = 0
            ps.bandage_death_pending = False
            self._clear_invincible_state(player_id)
            self.log_msg(f"{self.pn(player_id)}的绷带效果结束，死亡！")
            if self._start_turn_status_damage_would_defeat(1 - player_id):
                self._resolve_start_turn_status_damage_for_transition(1 - player_id)
            self._check_game_over()
            if self.game_over:
                return
        if ps.bandage_active and ps.invincible:
            ps.bandage_active = False
            ps.bandage_death_pending = True
            self.log_msg(f"{self.pn(player_id)}的绷带无敌将持续到下一个自己回合结束")
        # Fracture: clear at end of own turn. Status immunity suppresses the effect, not decay.
        if ps.fracture > 0:
            ps.fracture = 0
            self.log_msg(f"{self.pn(player_id)}的破损效果消失")
        # Weakness: decrement at end of own turn.
        if ps.weakness > 0:
            ps.weakness = max(0, ps.weakness - 1)
            if ps.weakness == 0:
                self.log_msg(f"{self.pn(player_id)}的虚弱效果消失")
        # Bleed: halve at end of turn.
        if ps.bleed > 0:
            ps.bleed = max(0, ps.bleed // 2)
            if ps.bleed == 0:
                self.log_msg(f"{self.pn(player_id)}的流血效果消失")
        try:
            hel_turn_bonus = float((getattr(ps, 'custom_vars', {}) or {}).get('hel_crit_multiplier_turn_bonus', 0) or 0)
        except Exception:
            hel_turn_bonus = 0
        if hel_turn_bonus != 0:
            ps.custom_vars['hel_crit_multiplier_turn_bonus'] = 0
            self._hel_sync_crit_multiplier_display(player_id)
            self.log_msg(f"{self.pn(player_id)}的临时暴击倍率结束")
        self._decay_end_turn_layer_statuses(player_id)
        # Track M gained this turn for next turn's check
        ps.m_gained_last_turn = ps.m_gained_this_turn
        ps.m_gained_this_turn = False
        self._return_cogwheel_cards_now(player_id)
        void_cards = [c for c in ps.hand if 'void' in c.flags]
        for c in void_cards:
            ps.hand.remove(c)
            self._void_exile_card(player_id, c)
        self._decay_action_limit_status(player_id, 'attack_blocked', 'attack_blocked', '禁攻')
        self._decay_action_limit_status(player_id, 'attack_only', 'attack_only', '仅攻击')
        self._decay_action_limit_status(player_id, 'magic_blocked', 'magic_blocked', '魔力封锁')
        if (
            ps.invincible
            and not ps.bandage_active
            and not ps.bandage_death_pending
            and self._should_expire_invincible_on_turn_end(player_id)
        ):
            self._clear_invincible_state(player_id)
            self.log_msg(f"{self.pn(player_id)}的无敌效果结束")
        self._save_last_turn_damage_snapshot(player_id)
        if player_id == self.first_player:
            other = 1 - self.first_player
            self._start_player_turn(other)
        else:
            self._end_round()

    def _void_exile_card(self, owner_id: int, card: CardInstance):
        if not (0 <= owner_id < len(self.players)) or card is None:
            return
        ps = self.players[owner_id]
        already_exiled = card in ps.exile
        self._put_card_in_exile(owner_id, card, trigger=False)
        self.log_msg(f"{self.pn(owner_id)}的{card.name_cn}因虚无被放逐")
        if not already_exiled:
            self._handle_card_exiled(owner_id, card)
        context = {
            'event': 'void_exile',
            'current_event': 'void_exile',
            'source_id': owner_id,
            'target_id': owner_id,
            'void_exiled_card': card,
        }
        if self._has_card_event(getattr(card, 'card_def', None), 'on_void_exile'):
            self._run_card_event(owner_id, card, 'on_void_exile', None, context)
        # Singularity listens globally for cards exiled by Void.
        for eq_owner_id, owner in enumerate(getattr(self, 'players', []) or []):
            for eq in list(getattr(owner, 'equipment', []) or []):
                if not self._equipment_is(eq, 'void:singularity', 'Singularity'):
                    continue
                target_id = int(getattr(eq, 'effect_target', eq_owner_id))
                if not self._valid_player_id(target_id):
                    continue
                self._deal_direct_damage(
                    target_id,
                    2,
                    '奇点',
                    eq_owner_id,
                    damage_type=DAMAGE_TYPE_MAGIC,
                    damage_tag=DAMAGE_TAG_BATTERY,
                )

    def _run_owner_turn_end_equipment(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        for owner_id, eq in self._iter_equipment_targeting_player(player_id):
            if not self._has_card_event(eq.card_def, 'owner_turn_end'):
                continue
            target_id = getattr(eq, 'effect_target', owner_id)
            if not isinstance(target_id, int) or not (0 <= target_id < len(self.players)):
                target_id = player_id
            self._run_card_event(owner_id, eq.card_instance, 'owner_turn_end', None, {
                'event': 'owner_turn_end',
                'source_id': owner_id,
                'target_id': target_id,
                'current_equipment': eq,
                'selected_equipment_instance_id': getattr(eq.card_instance, 'instance_id', None),
                'selected_equipment_owner_id': owner_id,
            })

    def _decay_equipment_armor_end_turn(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        for eq in list(self.players[player_id].equipment):
            armor = int(getattr(eq, 'armor', 0) or 0)
            if armor > 0:
                eq.armor = max(0, armor - 1)
            if self.game_over or getattr(self, 'pending_v2_ui', None):
                return

    def _end_round(self):
        self.round_num += 1
        if self.game_over:
            return
        self._start_draw_phase()

    def get_hand_card_ids(self, player_id: int) -> List[int]:
        return [c.instance_id for c in self.players[player_id].hand]

    def get_equipment_ids(self, player_id: int) -> List[int]:
        return [e.card_instance.instance_id for e in self.players[player_id].equipment]

    def get_counter_cards(self, player_id: int, trigger_type: str) -> List[CardInstance]:
        ps = self.players[player_id]
        return [
            c for c in ps.hand
            if c.card_def.response_trigger == trigger_type
            and self._counter_card_can_counter_pending(player_id, c)
        ]

    def get_attack_cards_in_hand(self, player_id: int) -> List[CardInstance]:
        return [c for c in self.players[player_id].hand if c.card_type == 'thorn']

    def get_enemy_equipment(self, player_id: int) -> List[EquipmentInstance]:
        return self.players[1 - player_id].equipment

    def _resolve_target(self, player_id, target_str):
        if isinstance(target_str, int):
            return target_str
        if not target_str or target_str == 'self':
            return player_id
        elif target_str in ('target', 'choice_target', 'selected_target', 'chosen_target'):
            selected = self._selected_choice_target(-1)
            if self._target_can_be_selected(player_id, selected, allow_self=True):
                return selected
            enemy_id = 1 - player_id
            return enemy_id if self._target_can_be_selected(player_id, enemy_id, allow_self=False) else -1
        elif target_str == 'enemy':
            enemy_id = 1 - player_id
            return enemy_id if self._target_can_be_selected(player_id, enemy_id, allow_self=False) else -1
        elif target_str == 'both':
            return -1
        elif target_str == 'random':
            return random.choice([player_id, 1 - player_id])
        return player_id
    def _resolve_targets(self, player_id, target_str):
        if isinstance(target_str, int):
            return [target_str] if 0 <= target_str < len(self.players) else []
        if target_str in ('all_players', 'all'):
            return list(range(len(self.players)))
        if target_str in ('both', 'random_side'):
            return [0, 1]
        if target_str in ('friendly', 'self', None, ''):
            return [player_id]
        if target_str == 'all_friendlies':
            return [player_id]
        if target_str == 'teammate':
            return [player_id]
        if target_str == 'enemy':
            enemy_id = 1 - player_id
            return [enemy_id] if self._target_can_be_selected(player_id, enemy_id, allow_self=False) else []
        if target_str == 'all_enemies':
            enemy_id = 1 - player_id
            return [enemy_id] if self._target_can_be_selected(player_id, enemy_id, allow_self=False) else []
        if target_str == 'random_friendly':
            return [player_id]
        if target_str == 'random_enemy':
            enemy_id = 1 - player_id
            return [enemy_id] if self._target_can_be_selected(player_id, enemy_id, allow_self=False) else []
        if target_str == 'random_player':
            return [random.choice([0, 1])]
        rid = self._resolve_target(player_id, target_str)
        if rid == -1:
            return []
        return [rid]
    def _card_needs_choice(self, card: CardInstance) -> bool:
        if card.def_id in ('Fission', 'Fusion', 'Mimic', 'Chromosome', 'Sewage', 'Chilli', 'Compass', 'Magnet'):
            return True
        if card.card_def.effects:
            for e in card.card_def.effects:
                if isinstance(e, dict) and e.get('type', '') in ('choose_from_deck', 'choose_from_discard', 'steal_enemy_card'):
                    return True
        return False
    def _get_choice_type(self, card: CardInstance) -> str:
        if card.def_id == 'Fission':
            return 'choose_attack_from_hand'
        elif card.def_id == 'Fusion':
            return 'choose_same_attacks_from_hand'
        elif card.def_id == 'Mimic':
            return 'choose_card_from_hand'
        elif card.def_id == 'Chromosome':
            return 'choose_card_from_discard'
        elif card.def_id == 'Sewage':
            return 'choose_enemy_equipment'
        elif card.def_id == 'Chilli':
            return 'choose_card_to_discard'
        elif card.def_id == 'Compass':
            return 'choose_from_deck'
        elif card.def_id == 'Magnet':
            return 'choose_from_enemy_hand'
        if card.card_def.effects:
            for e in card.card_def.effects:
                if isinstance(e, dict):
                    t = e.get('type', '')
                    if t == 'choose_from_deck':
                        return 'choose_from_deck'
                    elif t == 'choose_from_discard':
                        return 'choose_from_discard'
                    elif t == 'steal_enemy_card':
                        return 'choose_from_enemy_hand'
        return ''
    def _eval_expr(self, player_id, expr, card=None):
        if isinstance(expr, (int, float, bool)):
            return expr
        if isinstance(expr, str):
            text = expr.strip()
            if text and text[0] in '{[':
                try:
                    return self._eval_expr(player_id, json.loads(text), card)
                except Exception:
                    pass
            try:
                return int(expr)
            except Exception:
                return expr
        if not isinstance(expr, dict):
            return 0
        ref = expr.get('ref')
        if ref == 'var':
            tid = self._resolve_target(player_id, expr.get('target', 'self'))
            name = str(expr.get('name', 'var'))
            if self._is_suppressed_status_var(tid, name):
                return 0
            return int(self.players[tid].custom_vars.get(name, 0))
        if ref == 'target_attribute':
            tid = self._resolve_target(player_id, expr.get('target', 'self'))
            return int(self._get_player_property_value(tid, expr.get('attr', 'health')))
        if ref == 'math_op':
            a = int(self._eval_expr(player_id, expr.get('a', 0), card))
            b = int(self._eval_expr(player_id, expr.get('b', 0), card))
            op = expr.get('op', '+')
            if op == '+': return a + b
            if op == '-': return a - b
            if op == '*': return a * b
            if op == '/': return 0 if b == 0 else a // b
            return 0
        if ref == 'status_count':
            tid = self._resolve_target(player_id, expr.get('target', 'self'))
            ps = self.players[tid]
            status = str(expr.get('status', ''))
            counts = {
                'poison': ps.poison,
                '中毒': ps.poison,
                'burn': ps.fire,
                'fire': ps.fire,
                '灼烧': ps.fire,
                'toxic': ps.toxic,
                '淬毒': ps.toxic,
                'dodge': ps.dodge,
                '闪避': ps.dodge,
                'equip_protection': ps.equipment_protection,
                'equipment_protection': ps.equipment_protection,
                '装备摧毁保护': ps.equipment_protection,
                '装备保护': ps.equipment_protection,
            }
            return int(counts.get(status, 0))
        if ref == 'hand_size':
            tid = self._resolve_target(player_id, expr.get('target', 'self'))
            return len(self.players[tid].hand)
        if ref == 'hand_limit':
            tid = self._resolve_target(player_id, expr.get('target', 'self'))
            return self.players[tid].hand_limit()
        if ref == 'discard_size':
            tid = self._resolve_target(player_id, expr.get('target', 'self'))
            return len(self.players[tid].discard)
        if ref == 'exile_size':
            tid = self._resolve_target(player_id, expr.get('target', 'self'))
            return len(self.players[tid].exile)
        if ref == 'deck_remaining':
            tid = self._resolve_target(player_id, expr.get('target', 'self'))
            return len(self.players[tid].deck)
        if ref == 'turn_number':
            return int(self.round_num)
        if ref == 'play_count':
            return int(getattr(card, 'play_count', 0)) if card is not None else 0
        if ref == 'equip_turns':
            return int(getattr(card, 'equip_turns', 0)) if card is not None else 0
        if ref == 'durability':
            return int(getattr(card, 'durability', 0)) if card is not None else 0
        if ref == 'incoming_damage':
            return int(self._incoming_damage_hint[player_id])
        if ref == 'last_damage':
            tid = self._resolve_target(player_id, expr.get('target', 'self')) if isinstance(expr, dict) else player_id
            return int(self._last_damage_value[tid])
        if ref == 'equip_count':
            tid = self._resolve_target(player_id, expr.get('target', 'self'))
            return len(self.players[tid].equipment)
        if ref == 'round':
            v = float(self._eval_expr(player_id, expr.get('value', 0), card))
            mode = expr.get('mode', 'round')
            return int(math.ceil(v) if mode == 'ceil' else math.floor(v) if mode == 'floor' else round(v))
        if ref == 'min_max':
            a = int(self._eval_expr(player_id, expr.get('a', 0), card))
            b = int(self._eval_expr(player_id, expr.get('b', 0), card))
            return max(a, b) if expr.get('mode', 'max') == 'max' else min(a, b)
        if ref == 'clamp':
            v = int(self._eval_expr(player_id, expr.get('value', 0), card))
            mn = int(self._eval_expr(player_id, expr.get('min', 0), card))
            mx = int(self._eval_expr(player_id, expr.get('max', 99), card))
            return max(mn, min(mx, v))
        return 0
    def _eval_condition(self, player_id, cond, card=None):
        if isinstance(cond, bool):
            return cond
        if isinstance(cond, str):
            text = cond.strip()
            if text and text[0] in '{[':
                try:
                    return self._eval_condition(player_id, json.loads(text), card)
                except Exception:
                    pass
            if text in ('true', 'True'): return True
            if text in ('false', 'False'): return False
            return False
        if not isinstance(cond, dict):
            return False
        op = cond.get('op')
        if op == 'compare':
            a = self._eval_expr(player_id, cond.get('a', 0), card)
            b = self._eval_expr(player_id, cond.get('b', 0), card)
            cmp = cond.get('operator', '=')
            return (a == b) if cmp == '=' else (a != b) if cmp == '!=' else (a < b) if cmp == '<' else (a > b) if cmp == '>' else (a <= b) if cmp == '<=' else (a >= b)
        if op == 'var_compare':
            tid = self._resolve_target(player_id, cond.get('target', 'self'))
            name = str(cond.get('name', 'var'))
            if self._is_suppressed_status_var(tid, name):
                a = 0
            else:
                a = int(self.players[tid].custom_vars.get(name, 0))
            b = int(self._eval_expr(player_id, cond.get('value', 0), card))
            cmp = cond.get('operator', '=')
            return (a == b) if cmp == '=' else (a != b) if cmp == '!=' else (a < b) if cmp == '<' else (a > b) if cmp == '>' else (a <= b) if cmp == '<=' else (a >= b)
        if op == 'has_status_named':
            tid = self._resolve_target(player_id, cond.get('target', 'self'))
            status = str(cond.get('status', '')).strip()
            if self._is_status_immune(tid) and status not in ('status_immune', 'immune', '状态免疫'):
                return False
            if status in ('邪眼', 'Nazar', 'nazar'):
                return self._nazar_status_value(tid) > 0
            ps = self.players[tid]
            status_map = {
                'poison': ps.poison > 0,
                '中毒': ps.poison > 0,
                'burn': ps.fire > 0,
                'fire': ps.fire > 0,
                '灼烧': ps.fire > 0,
                'toxic': ps.toxic > 0,
                '淬毒': ps.toxic > 0,
                'dodge': ps.dodge > 0,
                '闪避': ps.dodge > 0,
                'equip_protection': ps.equipment_protection > 0,
                'equipment_protection': ps.equipment_protection > 0,
                '装备摧毁保护': ps.equipment_protection > 0,
                '装备保护': ps.equipment_protection > 0,
            }
            if status in status_map:
                return bool(status_map[status])
            return False
        if op == 'has_status':
            tid = self._resolve_target(player_id, cond.get('target', 'self'))
            status = str(cond.get('status', '')).strip()
            if self._is_status_immune(tid) and status not in ('status_immune', 'immune', '状态免疫'):
                return False
            ps = self.players[tid]
            status_map = {
                'poison': ps.poison > 0,
                'burn': ps.fire > 0,
                'toxic': ps.toxic > 0,
                'dodge': ps.dodge > 0,
                'equip_protection': ps.equipment_protection > 0,
                'equipment_protection': ps.equipment_protection > 0,
                '装备摧毁保护': ps.equipment_protection > 0,
                '装备保护': ps.equipment_protection > 0,
                'invincible': bool(ps.invincible),
                'untargetable': bool(ps.untargetable),
            }
            return bool(status_map.get(status, False))
        if op == 'target_attribute':
            tid = self._resolve_target(player_id, cond.get('target', 'self'))
            a = int(self._get_player_property_value(tid, cond.get('attr', 'health')))
            b = int(self._eval_expr(player_id, cond.get('value', 0), card))
            cmp = cond.get('operator', '=')
            return (a == b) if cmp == '=' else (a != b) if cmp == '!=' else (a < b) if cmp == '<' else (a > b) if cmp == '>' else (a <= b) if cmp == '<=' else (a >= b)
        if op == 'and':
            return bool(self._eval_condition(player_id, cond.get('a'), card) and self._eval_condition(player_id, cond.get('b'), card))
        if op == 'or':
            return bool(self._eval_condition(player_id, cond.get('a'), card) or self._eval_condition(player_id, cond.get('b'), card))
        if op == 'not':
            return not bool(self._eval_condition(player_id, cond.get('value'), card))
        if op == 'turn_number':
            a = int(self.round_num)
            b = int(self._eval_expr(player_id, cond.get('value', 0), card))
            cmp = cond.get('operator', '=')
            return (a == b) if cmp == '=' else (a != b) if cmp == '!=' else (a < b) if cmp == '<' else (a > b) if cmp == '>' else (a <= b) if cmp == '<=' else (a >= b)
        if op == 'hand_full':
            tid = self._resolve_target(player_id, cond.get('target', 'self'))
            return not self.players[tid].can_add_to_hand()
        if op == 'hand_has_type':
            tid = self._resolve_target(player_id, cond.get('target', 'self'))
            ctype = cond.get('card_type', 'thorn')
            return any(c.card_type == ctype for c in self.players[tid].hand)
        if op == 'zone_contains':
            tid = self._resolve_target(player_id, cond.get('target', 'self'))
            zone = cond.get('zone', 'hand')
            card_selector = cond.get('card')
            zone_map = {'hand': self.players[tid].hand, 'deck': self.players[tid].deck, 'discard': self.players[tid].discard, 'exile': self.players[tid].exile}
            pool = zone_map.get(zone, [])
            if isinstance(card_selector, dict):
                return len(self._match_card_selector(player_id, pool, card_selector, card)) > 0
            return len(pool) > 0
        if op == 'event_card_type':
            return bool(card is not None and card.card_type == cond.get('card_type'))
        if op == 'equip_turns':
            a = int(getattr(card, 'equip_turns', 0)) if card is not None else 0
            b = int(self._eval_expr(player_id, cond.get('value', 0), card))
            cmp = cond.get('operator', '=')
            return (a == b) if cmp == '=' else (a != b) if cmp == '!=' else (a < b) if cmp == '<' else (a > b) if cmp == '>' else (a <= b) if cmp == '<=' else (a >= b)
        if op == 'durability':
            a = int(getattr(card, 'durability', 0)) if card is not None else 0
            b = int(self._eval_expr(player_id, cond.get('value', 0), card))
            cmp = cond.get('operator', '=')
            return (a == b) if cmp == '=' else (a != b) if cmp == '!=' else (a < b) if cmp == '<' else (a > b) if cmp == '>' else (a <= b) if cmp == '<=' else (a >= b)
        if op == 'damage_value':
            a = int(self._incoming_damage_hint[player_id])
            b = int(self._eval_expr(player_id, cond.get('value', 0), card))
            cmp = cond.get('operator', '=')
            return (a == b) if cmp == '=' else (a != b) if cmp == '!=' else (a < b) if cmp == '<' else (a > b) if cmp == '>' else (a <= b) if cmp == '<=' else (a >= b)
        if op == 'has_equip':
            tid = self._resolve_target(player_id, cond.get('target', 'self'))
            return len(self.players[tid].equipment) > 0
        return False

    EVENT_EFFECT_TYPES = {
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
    }

    _base_eval_expr = _eval_expr
    _base_eval_condition = _eval_condition
    _base_resolve_target = _resolve_target
    _base_resolve_targets = _resolve_targets
    _base_card_needs_choice = _card_needs_choice
    _base_get_choice_type = _get_choice_type

    SCRIPT_ENTRY_ALIASES = {
        'play': ('onPlay', 'play', 'on_play'),
        'owner_turn_start': ('onOwnerTurnStart', 'owner_turn_start', 'on_owner_turn_start'),
        'target_turn_start': ('onTargetTurnStart', 'target_turn_start', 'on_target_turn_start'),
        'owner_turn_end': ('onOwnerTurnEnd', 'owner_turn_end', 'on_owner_turn_end'),
        'enemy_turn_start': ('onEnemyTurnStart', 'enemy_turn_start', 'on_enemy_turn_start'),
        'any_turn_start': ('onAnyTurnStart', 'any_turn_start', 'on_any_turn_start'),
        'damage_taken': ('onDamageTaken', 'damage_taken', 'on_damage_taken'),
        'equipment_trigger': ('onEquipmentTrigger', 'equipment_trigger', 'on_equipment_trigger'),
        'equipment_destroy': ('onEquipmentDestroy', 'equipment_destroy', 'on_equipment_destroy', 'onDestroy'),
        'hand_owner_turn_start': ('onHandOwnerTurnStart', 'hand_owner_turn_start', 'on_hand_owner_turn_start'),
        'hand_owner_turn_end': ('onHandOwnerTurnEnd', 'hand_owner_turn_end', 'on_hand_owner_turn_end'),
        'enter_hand': ('onEnterHand', 'enter_hand', 'on_enter_hand'),
        'discard_owner_turn_start': ('onDiscardOwnerTurnStart', 'discard_owner_turn_start', 'on_discard_owner_turn_start'),
        'deck_owner_turn_start': ('onDeckOwnerTurnStart', 'deck_owner_turn_start', 'on_deck_owner_turn_start'),
        'card_used': ('onCardUsed', 'card_used', 'on_card_used'),
        'equipment_triggered': ('onEquipmentTriggered', 'equipment_triggered', 'on_equipment_triggered'),
        'equipment_destroyed': ('onEquipmentDestroyed', 'equipment_destroyed', 'on_equipment_destroyed'),
        'resource_spent': ('onResourceSpent', 'resource_spent', 'on_resource_spent'),
        'player_stat_changed': ('onPlayerStatChanged', 'player_stat_changed', 'on_player_stat_changed'),
        'response': ('onResponse', 'response', 'on_response'),
    }

    CHOICE_EFFECT_TYPES = {'request_target', 'request_card', 'request_confirm'}

    def _script_effects_from(self, script):
        if isinstance(script, dict):
            effects = script.get('effects', [])
            return effects if isinstance(effects, list) else []
        return script if isinstance(script, list) else []

    def _has_script_entry(self, card_def, entry: str) -> bool:
        scripts = getattr(card_def, 'scripts', None) or {}
        if not isinstance(scripts, dict):
            return False
        for key in self.SCRIPT_ENTRY_ALIASES.get(entry, (entry,)):
            if key in scripts:
                return True
        return False

    def _get_script_effects(self, card_def, entry: str):
        scripts = getattr(card_def, 'scripts', None) or {}
        if not isinstance(scripts, dict):
            return []
        for key in self.SCRIPT_ENTRY_ALIASES.get(entry, (entry,)):
            if key in scripts:
                return self._script_effects_from(scripts.get(key))
        return []

    def _card_has_script(self, card_def) -> bool:
        scripts = getattr(card_def, 'scripts', None) or {}
        return isinstance(scripts, dict) and bool(scripts)

    def _has_card_event(self, card_def, event_name: str) -> bool:
        if self._has_script_entry(card_def, event_name):
            return True
        event_type = f'on_{event_name}'
        if self._card_has_v2_event(card_def, event_type):
            return True
        return any(isinstance(effect, dict) and effect.get('type') == event_type for effect in (card_def.effects or []))

    def _card_event_requires_self_destroy(self, card_def, event_name: str) -> bool:
        def walk_steps(value):
            if isinstance(value, list):
                return any(walk_steps(item) for item in value)
            if not isinstance(value, dict):
                return False
            if str(value.get('op') or value.get('type') or '') in ('destroy_self_equipment', 'destroy_current_equipment'):
                return True
            for key in ('steps', 'effects', 'body', 'then', 'else', 'on_cancel'):
                if walk_steps(value.get(key)):
                    return True
            params = value.get('params')
            return isinstance(params, dict) and walk_steps(params)

        event_name = str(event_name or '')
        v2_key = event_name if event_name.startswith('on_') else f'on_{event_name}'
        events = getattr(card_def, 'v2_events', None) or {}
        event_def = events.get(v2_key) if isinstance(events, dict) else None
        if isinstance(event_def, dict):
            if event_def.get('destroy_self'):
                return True
            if walk_steps(event_def.get('steps', event_def.get('effects', []))):
                return True
        elif isinstance(event_def, list) and walk_steps(event_def):
            return True
        for effect in getattr(card_def, 'effects', None) or []:
            if not isinstance(effect, dict) or effect.get('type') != v2_key:
                continue
            params = effect.get('params', {}) or {}
            if params.get('destroy_self') or walk_steps(params.get('effects', [])):
                return True
        return False

    def _play_effects_for_card(self, card: CardInstance):
        if self._card_has_script(card.card_def):
            return self._get_script_effects(card.card_def, 'play')
        return card.card_def.effects or []

    def _v2_play_steps_for_card(self, card: CardInstance):
        events = getattr(card.card_def, 'v2_events', None) or {}
        event_def = events.get('on_play')
        if isinstance(event_def, dict):
            steps = event_def.get('steps', event_def.get('effects', []))
            return steps if isinstance(steps, list) else []
        return event_def if isinstance(event_def, list) else []

    def _effect_type(self, effect) -> str:
        if not isinstance(effect, dict):
            return ''
        return str(effect.get('type') or effect.get('op') or '')

    def _effect_params(self, effect) -> dict:
        if not isinstance(effect, dict):
            return {}
        params = effect.get('params')
        if isinstance(params, dict):
            return params
        return {
            key: value
            for key, value in effect.items()
            if key not in {'type', 'op', 'log', 'then', 'else', 'steps', 'body', 'condition', 'cond'}
        }

    def _walk_choice_effects(self, effects):
        for effect in effects or []:
            if not isinstance(effect, dict):
                continue
            effect_type = self._effect_type(effect)
            if effect_type in self.EVENT_EFFECT_TYPES:
                continue
            yield effect
            params = self._effect_params(effect)
            for key in ('then', 'else', 'body', 'effects', 'a', 'b'):
                nested = params.get(key)
                if isinstance(nested, list):
                    yield from self._walk_choice_effects(nested)
                direct_nested = effect.get(key)
                if isinstance(direct_nested, list):
                    yield from self._walk_choice_effects(direct_nested)

    def _get_choice_request(self, card: CardInstance, choice: Optional[dict] = None):
        if self._card_is(card, 'PokerCard', 'hel:poker_card'):
            suit = str((choice or {}).get('hel_suit') or '') if isinstance(choice, dict) else ''
            if suit not in ('heart', 'diamond', 'spade', 'club'):
                owner_id, zone_name, _ = self._find_card_location(card)
                if owner_id is not None and zone_name == 'hand' and self._hel_luck_value(owner_id) + 4 > 12:
                    return {
                        'type': 'request_confirm',
                        'params': {
                            'choice_type': 'hel_card_suit',
                            'title': '选择花色',
                            'options': ['heart', 'diamond', 'spade', 'club'],
                            'labels': [
                                '♥ 红桃：回复自己7H',
                                '♦ 方片：本次最终伤害+6D',
                                '♠ 黑桃：抽1张牌',
                                '♣ 梅花：对目标施加3P',
                            ],
                            'cancellable': False,
                        },
                    }
        effects = list(self._play_effects_for_card(card) or []) + list(self._v2_play_steps_for_card(card) or [])
        for effect in self._walk_choice_effects(effects):
            effect_type = self._effect_type(effect)
            is_choice_effect = effect_type in self.CHOICE_EFFECT_TYPES or effect_type in (
                'discard_choice_then_draw', 'destroy_equipment_choice_or_first',
                'choose_from_deck', 'choose_from_discard', 'steal_enemy_card',
            )
            if not is_choice_effect:
                continue
            if self._choice_request_satisfied(effect, choice, card):
                continue
            if effect_type in self.CHOICE_EFFECT_TYPES:
                return effect
            if effect_type in ('discard_choice_then_draw', 'destroy_equipment_choice_or_first',
                               'choose_from_deck', 'choose_from_discard', 'steal_enemy_card'):
                return effect
        return None

    def _selected_choice_target(self, default=-1):
        choice = getattr(self, '_active_choice', None) or {}
        if not isinstance(choice, dict):
            return default
        for key in ('target_player', 'target_player_id', 'target_id'):
            if key in choice:
                try:
                    return int(choice.get(key))
                except Exception:
                    return default
        return default

    def _find_card_location(self, needle):
        if needle is None:
            return None, '', None
        needle_id = getattr(needle, 'instance_id', None)
        for pid, ps in enumerate(self.players):
            for zone_name in ('hand', 'deck', 'discard', 'exile'):
                zone = getattr(ps, zone_name, [])
                for card_obj in zone:
                    if card_obj is needle or (needle_id is not None and getattr(card_obj, 'instance_id', None) == needle_id):
                        return pid, zone_name, card_obj
            for eq in getattr(ps, 'equipment', []):
                card_obj = getattr(eq, 'card_instance', None)
                if card_obj is needle or (needle_id is not None and getattr(card_obj, 'instance_id', None) == needle_id):
                    return pid, 'equipment', card_obj
        return None, '', None

    def _find_card_by_instance_id(self, instance_id):
        try:
            iid = int(instance_id)
        except Exception:
            return None
        for ps in self.players:
            for zone_name in ('hand', 'deck', 'discard', 'exile'):
                for card_obj in getattr(ps, zone_name, []):
                    if getattr(card_obj, 'instance_id', None) == iid:
                        return card_obj
            for eq in getattr(ps, 'equipment', []):
                card_obj = getattr(eq, 'card_instance', None)
                if getattr(card_obj, 'instance_id', None) == iid:
                    return card_obj
        return None

    def _remember_created_card(self, card_obj, context=None):
        if card_obj is None:
            return
        self._last_created_card_instance_id = getattr(card_obj, 'instance_id', None)
        if isinstance(context, dict):
            context['last_created_card_instance_id'] = self._last_created_card_instance_id

    def _resolve_card_ref(self, player_id, card_ref, current_card=None):
        if isinstance(card_ref, CardInstance):
            return card_ref
        if card_ref is None:
            return current_card
        if isinstance(card_ref, str):
            if card_ref in ('current_card', 'this', 'this_card'):
                return current_card
            if card_ref in ('selected_card', 'choice_card', 'chosen_card'):
                context = getattr(self, '_active_effect_context', {}) or {}
                if isinstance(context, dict):
                    context_card = context.get('chosen_card') or context.get('selected_card')
                    if isinstance(context_card, CardInstance):
                        return context_card
                return self._resolve_card_ref(player_id, {'ref': 'selected_card'}, current_card)
            if card_ref in ('last_created_card', 'created_card', 'last_copied_card'):
                return self._resolve_card_ref(player_id, {'ref': 'last_created_card'}, current_card)
            return None
        if not isinstance(card_ref, dict):
            return None
        ref = card_ref.get('ref') or card_ref.get('op') or card_ref.get('type')
        if ref in ('event_card', 'used_card', 'trigger_card', 'destroyed_card'):
            context = getattr(self, '_active_effect_context', {}) or {}
            instance_id = context.get('event_card_instance_id') if isinstance(context, dict) else None
            return self._find_card_by_instance_id(instance_id)
        if ref in ('current_card', 'this_card'):
            return current_card
        if ref in ('last_created_card', 'created_card', 'last_copied_card'):
            context = getattr(self, '_active_effect_context', {}) or {}
            instance_id = context.get('last_created_card_instance_id') if isinstance(context, dict) else None
            if instance_id is None:
                instance_id = getattr(self, '_last_created_card_instance_id', None)
            return self._find_card_by_instance_id(instance_id)
        if ref == 'card_instance':
            return self._find_card_by_instance_id(card_ref.get('instance_id'))
        if ref == 'var':
            raw = self._var_store_for_target(player_id, card_ref.get('target', 'self')).get(str(card_ref.get('name', 'var')))
            if isinstance(raw, list):
                raw = raw[0] if raw else None
            return self._resolve_card_ref(player_id, raw, current_card)
        if ref == 'list_item':
            return self._resolve_card_ref(player_id, self._list_item_raw(player_id, card_ref, current_card), current_card)
        if ref in ('selected_card', 'choice_card', 'chosen_card'):
            context = getattr(self, '_active_effect_context', {}) or {}
            if isinstance(context, dict):
                context_card = context.get('chosen_card') or context.get('selected_card')
                if isinstance(context_card, CardInstance):
                    return context_card
            choice = getattr(self, '_active_choice', None) or {}
            if isinstance(choice, dict):
                instance_id = choice.get('target_instance_id')
                if instance_id is None and isinstance(choice.get('target_instance_ids'), list) and choice.get('target_instance_ids'):
                    instance_id = choice.get('target_instance_ids')[0]
                found = self._find_card_by_instance_id(instance_id)
                return found if found is not None and not self._card_is_sublime(found) else None
            return None
        if ref == 'selected_card_at':
            choice = getattr(self, '_active_choice', None) or {}
            if not isinstance(choice, dict):
                return None
            ids = choice.get('_selected_card_ids_snapshot') or choice.get('target_instance_ids')
            if not isinstance(ids, list):
                ids = [choice.get('target_instance_id')] if choice.get('target_instance_id') is not None else []
            index = self._eval_int(player_id, card_ref.get('index', 1), current_card, 1) - 1
            found = self._find_card_by_instance_id(ids[index]) if 0 <= index < len(ids) else None
            return found if found is not None and not self._card_is_sublime(found) else None
        if ref == 'zone_card':
            tid = self._resolve_target(player_id, card_ref.get('target', 'self'))
            if not (0 <= tid < len(self.players)):
                return None
            zone_name = str(card_ref.get('zone', 'hand'))
            ps = self.players[tid]
            if zone_name == 'equipment':
                zone = [eq.card_instance for eq in ps.equipment]
            else:
                zone = getattr(ps, zone_name, [])
            index = self._eval_int(player_id, card_ref.get('index', 1), current_card, 1) - 1
            return zone[index] if 0 <= index < len(zone) else None
        return None

    def _resolve_card_id_ref(self, player_id, card_ref, current_card=None):
        if isinstance(card_ref, str):
            return card_ref
        if isinstance(card_ref, dict) and card_ref.get('ref') == 'card_by_id':
            return str(card_ref.get('id', ''))
        if isinstance(card_ref, dict) and card_ref.get('ref') in ('var', 'list_item'):
            raw = self._var_store_for_target(player_id, card_ref.get('target', 'self')).get(str(card_ref.get('name', 'var'))) if card_ref.get('ref') == 'var' else self._list_item_raw(player_id, card_ref, current_card)
            if isinstance(raw, list):
                raw = raw[0] if raw else ''
            if isinstance(raw, str):
                return raw
            card_obj = self._resolve_card_ref(player_id, raw, current_card)
            return getattr(card_obj, 'def_id', '') if card_obj is not None else ''
        card_obj = self._resolve_card_ref(player_id, card_ref, current_card)
        return getattr(card_obj, 'def_id', '') if card_obj is not None else ''

    def _get_card_definition(self, player_id, card_ref, current_card=None):
        card_id = self._resolve_card_id_ref(player_id, card_ref, current_card)
        if not card_id:
            return None
        return CARD_DEFS.get(card_id)

    def _get_card_def_property_value(self, player_id, card_ref, prop, current_card=None):
        card_def = self._get_card_definition(player_id, card_ref, current_card)
        if card_def is None:
            return 0
        prop = str(prop or 'cost_e')
        if prop in ('flags', 'tags'):
            return sorted(str(flag) for flag in getattr(card_def, 'flags', set()) or set())
        if prop in ('cost_e', 'cost_m', 'count', 'trigger_cost_e'):
            return int(getattr(card_def, prop, 0) or 0)
        if prop in ('effect_text', 'description', 'card_type', 'quality', 'name_cn', 'name_en', 'trigger_effect_text', 'id'):
            return str(getattr(card_def, prop, '') or '')
        return getattr(card_def, prop, 0)

    def _get_card_def_tags(self, player_id, card_ref, current_card=None):
        card_def = self._get_card_definition(player_id, card_ref, current_card)
        if card_def is None:
            return []
        return sorted(str(flag) for flag in getattr(card_def, 'flags', set()) or set())

    def _remove_card_from_current_zone(self, target_card):
        owner_id, zone_name, card_obj = self._find_card_location(target_card)
        if owner_id is None or card_obj is None:
            return None, ''
        ps = self.players[owner_id]
        if zone_name == 'equipment':
            for eq in list(ps.equipment):
                if eq.card_instance is card_obj or eq.card_instance.instance_id == card_obj.instance_id:
                    self._cleanup_equipment_derived_effects(owner_id, eq, run_destroy_event=False)
                    ps.equipment.remove(eq)
                    self._refresh_equipment_derived_player_flags(owner_id)
                    self._refresh_hand_limit_bonuses()
                    return owner_id, zone_name
            return owner_id, zone_name
        zone = getattr(ps, zone_name, None)
        if isinstance(zone, list) and card_obj in zone:
            zone.remove(card_obj)
        return owner_id, zone_name

    def _var_store_for_target(self, player_id, target):
        if target == 'global':
            if not hasattr(self, 'custom_vars'):
                self.custom_vars = {}
            return self.custom_vars
        if target == 'team':
            if not hasattr(self, 'team_custom_vars'):
                self.team_custom_vars = {}
            team_id = self.team_of(player_id) if hasattr(self, 'team_of') else player_id
            key = str(team_id)
            if key not in self.team_custom_vars:
                self.team_custom_vars[key] = {}
            return self.team_custom_vars[key]
        tid = self._resolve_target(player_id, target)
        if not (0 <= tid < len(self.players)):
            tid = player_id
        return self.players[tid].custom_vars

    def _var_target_refs(self, player_id, target):
        if target in ('global', 'team'):
            return [target]
        return self._resolve_targets(player_id, target)

    def _scalar_value(self, value, default=0):
        if isinstance(value, list):
            return self._scalar_value(value[0], default) if value else default
        if isinstance(value, dict):
            if value.get('ref') == 'card_instance':
                card = self._find_card_by_instance_id(value.get('instance_id'))
                return getattr(card, 'def_id', default) if card is not None else default
            return default
        return default if value is None else value

    def _serializable_list_item(self, item):
        if isinstance(item, CardInstance):
            return {'ref': 'card_instance', 'instance_id': item.instance_id}
        if isinstance(item, list):
            return [self._serializable_list_item(v) for v in item]
        if isinstance(item, dict):
            return {k: self._serializable_list_item(v) for k, v in item.items()}
        return item

    def _zone_list(self, player_id, target, zone_name):
        tid = self._resolve_target(player_id, target)
        if not (0 <= tid < len(self.players)):
            return []
        ps = self.players[tid]
        zone = [eq.card_instance for eq in ps.equipment] if zone_name == 'equipment' else getattr(ps, zone_name, [])
        return [{'ref': 'card_instance', 'instance_id': c.instance_id} for c in zone or [] if c is not None]

    def _eval_list(self, player_id, expr, card=None):
        if isinstance(expr, str):
            text = expr.strip()
            if (text.startswith('[') and text.endswith(']')) or (text.startswith('{') and text.endswith('}')):
                try:
                    return self._eval_list(player_id, json.loads(text), card)
                except Exception:
                    pass
            value = self._eval_expr(player_id, expr, card)
            return value if isinstance(value, list) else [value]
        if isinstance(expr, list):
            return [self._serializable_list_item(v) for v in expr]
        if not isinstance(expr, dict):
            return [] if expr is None else [expr]
        ref = expr.get('ref')
        if ref in ('list', 'list_create'):
            return [self._serializable_list_item(self._eval_raw_item(player_id, item, card)) for item in expr.get('items', [])]
        if ref == 'list_var':
            raw = self._var_store_for_target(player_id, expr.get('target', 'self')).get(str(expr.get('name', 'var')), [])
            return list(raw) if isinstance(raw, list) else ([] if raw is None else [raw])
        if ref == 'var':
            raw = self._var_store_for_target(player_id, expr.get('target', 'self')).get(str(expr.get('name', 'var')), 0)
            return list(raw) if isinstance(raw, list) else ([] if raw is None else [raw])
        if ref == 'zone_list':
            return self._zone_list(player_id, expr.get('target', 'self'), str(expr.get('zone', 'hand')))
        if ref == 'card_def_tags':
            return self._get_card_def_tags(player_id, expr.get('card', ''), card)
        if ref == 'list_item':
            item = self._list_item_raw(player_id, expr, card)
            return [] if item is None else [item]
        value = self._eval_expr(player_id, expr, card)
        return value if isinstance(value, list) else [value]

    def _list_item_raw(self, player_id, expr, card=None):
        values = self._eval_list(player_id, expr.get('list', []), card) if isinstance(expr, dict) else []
        index = self._eval_int(player_id, expr.get('index', 1), card, 1) - 1 if isinstance(expr, dict) else 0
        return values[index] if 0 <= index < len(values) else None

    def _eval_raw_item(self, player_id, expr, card=None):
        if isinstance(expr, dict):
            ref = expr.get('ref')
            if ref == 'list_item':
                return self._list_item_raw(player_id, expr, card)
            if ref in ('card_instance', 'zone_card', 'selected_card', 'selected_card_at', 'current_card', 'this_card', 'event_card', 'used_card', 'trigger_card', 'destroyed_card', 'last_created_card', 'created_card', 'last_copied_card'):
                resolved = self._resolve_card_ref(player_id, expr, card)
                return self._serializable_list_item(resolved) if resolved is not None else expr
            if ref == 'var':
                raw = self._var_store_for_target(player_id, expr.get('target', 'self')).get(str(expr.get('name', 'var')))
                return raw[0] if isinstance(raw, list) and raw else raw
        return self._eval_expr(player_id, expr, card)

    def _eval_var_assignment_value(self, player_id, expr, card=None):
        if isinstance(expr, list):
            return self._serializable_list_item(expr[0]) if expr else 0
        if isinstance(expr, dict) and expr.get('ref') in ('list', 'list_create', 'list_var', 'zone_list', 'card_def_tags'):
            values = self._eval_list(player_id, expr, card)
            return self._serializable_list_item(values[0]) if values else 0
        return self._serializable_list_item(self._eval_raw_item(player_id, expr, card))

    def _same_list_item(self, a, b):
        a = self._serializable_list_item(a)
        b = self._serializable_list_item(b)
        if isinstance(a, dict) and a.get('ref') == 'card_instance' and isinstance(b, str):
            card = self._find_card_by_instance_id(a.get('instance_id'))
            return card is not None and card.def_id == b
        if isinstance(b, dict) and b.get('ref') == 'card_instance' and isinstance(a, str):
            card = self._find_card_by_instance_id(b.get('instance_id'))
            return card is not None and card.def_id == a
        return a == b

    def _effect_tree_uses_event_target(self, value):
        if value in ('event_target', 'target', 'choice_target', 'selected_target', 'chosen_target'):
            return True
        if isinstance(value, list):
            return any(self._effect_tree_uses_event_target(item) for item in value)
        if isinstance(value, dict):
            return any(self._effect_tree_uses_event_target(item) for item in value.values())
        return False

    def _equipment_trigger_forbids_self_target(self, card_def):
        if not card_def or 'self_only' in getattr(card_def, 'flags', set()):
            return False
        events = getattr(card_def, 'v2_events', None) or {}
        event_def = events.get('on_equipment_trigger')
        return self._effect_tree_uses_event_target(event_def)

    def _resolve_target(self, player_id, target_str):
        context = getattr(self, '_active_effect_context', {}) or {}
        if isinstance(target_str, dict) and target_str.get('ref') == 'card_owner':
            target_card = self._resolve_card_ref(player_id, target_str.get('card'), None)
            owner_id, _, _ = self._find_card_location(target_card)
            return player_id if owner_id is None else owner_id
        if isinstance(target_str, int):
            return target_str if 0 <= target_str < len(self.players) else -1
        if target_str in ('choice_target', 'selected_target', 'chosen_target'):
            target_id = self._selected_choice_target(-1)
            if 0 <= target_id < len(self.players):
                return target_id
            try:
                context_target = int(context.get('target_id', -1))
            except Exception:
                context_target = -1
            return context_target if 0 <= context_target < len(self.players) else -1
        if target_str == 'target':
            target_id = self._selected_choice_target(-1)
            if self._target_can_be_selected(player_id, target_id, allow_self=True):
                return target_id
            try:
                context_target = int(context.get('target_id', -1))
            except Exception:
                context_target = -1
            if 0 <= context_target < len(self.players):
                return context_target
            return -1
        if target_str == 'event_target':
            return int(context.get('target_id', player_id))
        if target_str in ('event_source', 'source', 'last_actor', 'damage_source'):
            return int(context.get('source_id', player_id))
        return self._base_resolve_target(player_id, target_str)

    def _resolve_targets(self, player_id, target_str):
        if isinstance(target_str, int):
            return [target_str] if 0 <= target_str < len(self.players) else []
        if isinstance(target_str, dict) and target_str.get('ref') == 'card_owner':
            tid = self._resolve_target(player_id, target_str)
            return [] if tid < 0 else [tid]
        if target_str in ('choice_target', 'selected_target', 'chosen_target', 'event_target', 'target', 'event_source', 'source', 'last_actor', 'damage_source'):
            context = getattr(self, '_active_effect_context', None)
            if target_str in ('choice_target', 'selected_target', 'chosen_target', 'target') and isinstance(context, dict):
                wide_targets = context.get('wide_strike_targets')
                if isinstance(wide_targets, list):
                    return [
                        int(tid) for tid in wide_targets
                        if isinstance(tid, int) and 0 <= tid < len(self.players)
                    ]
            tid = self._resolve_target(player_id, target_str)
            return [] if tid < 0 else [tid]
        return self._base_resolve_targets(player_id, target_str)

    def _valid_player_id(self, player_id) -> bool:
        try:
            player_id = int(player_id)
        except Exception:
            return False
        return 0 <= player_id < len(self.players)

    def _log_mod_runtime_error(self, effect_type, exc, player_id=None, card=None):
        self.log_msg(MOD_RUNTIME_ERROR_MESSAGE)
        record_mod_runtime_error(
            f'{type(exc).__name__}: {exc}',
            effect_type=effect_type,
            player_id=player_id,
            card_id=getattr(card, 'def_id', None),
            room_phase=getattr(self, 'phase', ''),
        )

    def _run_effect_list(self, player_id, card, effects, choice, context):
        prev_context = getattr(self, '_active_effect_context', None)
        prev_choice = getattr(self, '_active_choice', None)
        context_dict = context if isinstance(context, dict) else ({'context': context} if context else {})
        self._active_effect_context = context_dict
        if isinstance(choice, dict):
            self._active_choice = choice
        try:
            for eff in effects or []:
                et = eff if isinstance(eff, str) else self._effect_type(eff)
                pm = {} if isinstance(eff, str) else self._effect_params(eff)
                lg = None if isinstance(eff, str) else eff.get('log')
                rt = self._EFFECT_ALIASES.get(et, et)
                if et in self.EVENT_EFFECT_TYPES or rt in self.EVENT_EFFECT_TYPES:
                    continue
                if (
                    isinstance(choice, dict)
                    and choice.get('cancelled')
                    and rt in self.CHOICE_EFFECT_TYPES
                    and not pm.get('continue_on_cancel')
                ):
                    break
                fn = getattr(self, f'_atomic_{rt}', None)
                try:
                    before_stats = self._snapshot_player_stats()
                    if callable(fn):
                        fn(player_id, card, pm, lg, choice, context_dict)
                    elif lg:
                        self.log_msg(lg)
                    else:
                        self._log_mod_runtime_error(et, RuntimeError(f'Unknown effect: {et}'), player_id, card)
                    if rt not in ('if', 'if_else', 'repeat', 'repeat_until', 'for_each',
                                  'for_each_selected_card', 'for_each_list', 'timed_effect',
                                  'countdown_var', 'cost_e', 'cost_m'):
                        self._dispatch_player_stat_changes(before_stats, player_id, card)
                except (ModLoopBreak, ModLoopContinue):
                    raise
                except Exception as exc:
                    self._log_mod_runtime_error(et, exc, player_id, card)
        finally:
            self._active_effect_context = prev_context
            self._active_choice = prev_choice

    def _same_timer_side(self, player_a: int, player_b: int) -> bool:
        if not (0 <= player_a < len(self.players) and 0 <= player_b < len(self.players)):
            return False
        team_of = getattr(self, 'team_of', None)
        if callable(team_of):
            try:
                return team_of(player_a) == team_of(player_b)
            except Exception:
                return player_a == player_b
        return player_a == player_b

    def _opposite_timer_side(self, player_a: int, player_b: int) -> bool:
        if not (0 <= player_a < len(self.players) and 0 <= player_b < len(self.players)):
            return False
        team_of = getattr(self, 'team_of', None)
        if callable(team_of):
            try:
                return team_of(player_a) != team_of(player_b)
            except Exception:
                return player_a != player_b
        return player_a != player_b

    def _timer_trigger_matches(self, entry: dict, current_player: int) -> bool:
        trigger = str(entry.get('trigger') or 'target_turn_start')
        owner_id = int(entry.get('owner_id', current_player))
        target_id = int(entry.get('target_id', owner_id))
        if trigger in ('target_turn_start', 'turn_start'):
            return current_player == target_id
        if trigger == 'owner_turn_start':
            return current_player == owner_id
        if trigger == 'friendly_turn_start':
            return self._same_timer_side(owner_id, current_player)
        if trigger == 'enemy_turn_start':
            return self._opposite_timer_side(owner_id, current_player)
        if trigger == 'any_turn_start':
            return True
        return False

    def _timer_targets(self, player_id: int, target) -> List[int]:
        if target in ('global', 'team'):
            return [player_id]
        try:
            ids = self._resolve_targets(player_id, target)
        except Exception:
            ids = [player_id]
        ids = [int(pid) for pid in ids if isinstance(pid, int) and 0 <= pid < len(self.players)]
        return ids or [player_id]

    def _clone_timer_effects(self, effects):
        try:
            return json.loads(json.dumps(effects or [], ensure_ascii=False))
        except Exception:
            return list(effects or [])

    def _register_timed_effect(self, owner_id: int, target_id: int, trigger: str, duration: int, effects, card=None):
        if duration <= 0 or not effects:
            return
        if not hasattr(self, 'timed_effects') or not isinstance(self.timed_effects, list):
            self.timed_effects = []
        entry = {
            'owner_id': owner_id,
            'target_id': target_id,
            'trigger': trigger or 'target_turn_start',
            'remaining': max(1, min(int(duration), 999)),
            'effects': self._clone_timer_effects(effects),
        }
        if card is not None and getattr(card, 'instance_id', None) is not None:
            entry['card_instance_id'] = card.instance_id
        self.timed_effects.append(entry)
        if len(self.timed_effects) > 200:
            self.timed_effects = self.timed_effects[-200:]

    def _run_timed_effects_for_turn(self, current_player: int):
        if not getattr(self, 'timed_effects', None):
            return
        kept = []
        for entry in list(self.timed_effects):
            if not isinstance(entry, dict):
                continue
            if not self._timer_trigger_matches(entry, current_player):
                kept.append(entry)
                continue
            owner_id = int(entry.get('owner_id', current_player))
            target_id = int(entry.get('target_id', owner_id))
            remaining = int(entry.get('remaining', 0))
            timer_card = None
            if entry.get('card_instance_id') is not None:
                timer_card = self._find_card_by_instance_id(entry.get('card_instance_id'))
            self._run_effect_list(
                owner_id,
                timer_card,
                entry.get('effects', []),
                None,
                {
                    'event': 'timed_effect',
                    'source_id': owner_id,
                    'target_id': target_id,
                    'timer_current_player': current_player,
                    'timer_remaining': remaining,
                },
            )
            entry['remaining'] = remaining - 1
            if entry['remaining'] > 0:
                kept.append(entry)
        self.timed_effects = kept

    def _atomic_timed_effect(self, player_id, card, params, log, choice, context):
        trigger = str(params.get('trigger') or 'target_turn_start')
        duration = self._eval_int(player_id, params.get('duration', params.get('turns', 1)), card, 1)
        effects = params.get('effects', params.get('body', [])) or []
        for target_id in self._timer_targets(player_id, params.get('target', 'self')):
            self._register_timed_effect(player_id, target_id, trigger, duration, effects, card)

    def _atomic_delayed_blind_next_turn(self, player_id, card, params, log, choice, context):
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        effects = [{'type': 'status_add_named', 'params': {'target': 'target', 'status': 'blind', 'amount': amount}}]
        for target_id in self._timer_targets(player_id, params.get('target', 'target')):
            self._register_timed_effect(player_id, target_id, 'target_turn_start', 1, effects, card)
            if log:
                self.log_msg(log)

    def _atomic_delayed_reveal_hand_next_turn(self, player_id, card, params, log, choice, context):
        effects = [{'type': 'reveal_enemy_hand', 'params': {'target': 'target'}}]
        for target_id in self._timer_targets(player_id, params.get('target', 'target')):
            self._register_timed_effect(player_id, target_id, 'target_turn_start', 1, effects, card)
            if log:
                self.log_msg(log)

    def _atomic_countdown_var(self, player_id, card, params, log, choice, context):
        target = params.get('target', 'self')
        name = str(params.get('name', 'timer'))
        duration = self._eval_int(player_id, params.get('duration', params.get('turns', 1)), card, 1)
        trigger = str(params.get('trigger') or 'target_turn_start')
        self._atomic_var_set(player_id, card, {'target': target, 'name': name, 'value': duration}, log, choice, context)
        for target_id in self._timer_targets(player_id, target):
            effect_target = target if target in ('global', 'team') else target_id
            effects = [{'type': 'var_sub', 'params': {'target': effect_target, 'name': name, 'value': 1}}]
            self._register_timed_effect(player_id, target_id, trigger, duration, effects)

    def _eval_expr(self, player_id, expr, card=None):
        if isinstance(expr, dict):
            ref = expr.get('ref') or expr.get('op') or expr.get('type')
            if ref in ('const', 'literal'):
                return expr.get('value', expr.get('const', 0))
            if ref in ('add', 'sub', 'mul', 'div', '+', '-', '*', '/', 'min', 'max'):
                op = {'+': 'add', '-': 'sub', '*': 'mul', '/': 'div'}.get(ref, ref)
                values = expr.get('values')
                if values is None:
                    values = [expr.get('a', 0), expr.get('b', 0)]
                nums = [self._eval_expr(player_id, value, card) for value in values]
                nums = [int(self._scalar_value(num, 0)) for num in nums]
                if op == 'add':
                    return sum(nums)
                if op == 'sub':
                    return nums[0] - sum(nums[1:]) if nums else 0
                if op == 'mul':
                    out = 1
                    for num in nums:
                        out *= num
                    return out
                if op == 'div':
                    return 0 if len(nums) < 2 or nums[1] == 0 else nums[0] // nums[1]
                if op == 'min':
                    return min(nums) if nums else 0
                if op == 'max':
                    return max(nums) if nums else 0
            if ref == 'equip_turns':
                eq = self._find_equipment_for_card(player_id, card)
                return int(eq.turns_equipped) if eq is not None else int(getattr(card, 'equip_turns', 0) if card is not None else 0)
            if ref == 'durability':
                return int(getattr(card, 'durability', 0)) if card is not None else 0
            if ref == 'equipment_count_named':
                tid = self._resolve_target(player_id, expr.get('target', 'self'))
                card_id = str(expr.get('card_id', '') or '')
                if tid < 0:
                    ids = range(len(self.players))
                else:
                    ids = [tid]
                id_set = set(ids)
                return sum(
                    1
                    for owner_id, ps in enumerate(self.players)
                    for eq in ps.equipment
                    if eq.def_id == card_id
                    and int(getattr(eq, 'effect_target', getattr(eq, 'owner', owner_id))) in id_set
                )
            if ref == 'damage_source':
                context = getattr(self, '_active_effect_context', {}) or {}
                return int(context.get('source_id', player_id))
            if ref in ('damage_amount', 'current_damage'):
                context = getattr(self, '_active_effect_context', {}) or {}
                return int(context.get('damage', context.get('amount', 0)) or 0)
            if ref == 'timer_remaining':
                context = getattr(self, '_active_effect_context', {}) or {}
                return int(context.get('timer_remaining', 0))
            if ref == 'loop_index':
                context = getattr(self, '_active_effect_context', {}) or {}
                return int(context.get('loop_index', context.get('list_index', context.get('equipment_index', context.get('repeat_index', 0)))) or 0)
            if ref == 'status_count':
                target_id = self._resolve_target(player_id, expr.get('target', 'self'))
                return self._get_status_count(target_id, expr.get('status', ''))
            if ref == 'zone_count':
                target_id = self._resolve_target(player_id, expr.get('target', 'self'))
                return self._zone_size(target_id, expr.get('zone', 'hand'))
            if ref in ('turn_damage_taken', 'turn_damage_dealt', 'last_turn_damage_taken',
                       'last_turn_damage_dealt', 'total_damage_taken', 'total_damage_dealt'):
                target_id = self._resolve_target(player_id, expr.get('target', 'self'))
                return self._get_player_property_value(target_id, ref)
            if ref == 'choice_target':
                return int(self._selected_choice_target(-1))
            if ref == 'choice_confirmed':
                active_choice = getattr(self, '_active_choice', None) or {}
                if not isinstance(active_choice, dict):
                    return 0
                return 1 if bool(active_choice.get('confirmed') or active_choice.get('accepted')) else 0
            if ref == 'selected_card_index':
                active_choice = getattr(self, '_active_choice', None) or {}
                if not isinstance(active_choice, dict):
                    return 0
                return int(active_choice.get('_selected_card_index', 0))
            if ref == 'selected_cards_count':
                active_choice = getattr(self, '_active_choice', None) or {}
                if not isinstance(active_choice, dict):
                    return 0
                ids = active_choice.get('target_instance_ids')
                if isinstance(ids, list):
                    return len(ids)
                return 1 if active_choice.get('target_instance_id') is not None else 0
            if ref in ('card_property', 'card_prop'):
                target_card = self._resolve_card_ref(player_id, expr.get('card', {'ref': 'current_card'}), card)
                if target_card is None:
                    return 0
                prop = str(expr.get('property', expr.get('prop', 'fusion_level')) or 'fusion_level')
                if prop == 'paid_e':
                    return int(getattr(target_card, '_paid_e_this_play', getattr(target_card, 'cost_e', 0)) or 0)
                if prop == 'paid_m':
                    return int(getattr(target_card, '_paid_m_this_play', getattr(target_card, 'cost_m', 0)) or 0)
                if prop == 'cost_e':
                    return int(target_card.cost_e)
                if prop == 'cost_m':
                    return int(target_card.cost_m)
                if prop == 'cost_e_override':
                    return int(target_card.cost_e_override if target_card.cost_e_override is not None else target_card.card_def.cost_e)
                if prop == 'cost_m_override':
                    return int(target_card.cost_m_override if target_card.cost_m_override is not None else target_card.card_def.cost_m)
                return int(getattr(target_card, prop, 0))
            if ref == 'card_tag_count':
                target_card = self._resolve_card_ref(player_id, expr.get('card', {'ref': 'current_card'}), card)
                if target_card is None:
                    return 0
                flags = normalize_card_flags(getattr(target_card.card_def, 'flags', set()) or set())
                flags.update(normalize_card_flags(getattr(target_card, 'instance_flags', set()) or set()))
                flags.difference_update(normalize_card_flags(getattr(target_card, 'disabled_flags', set()) or set()))
                return len(flags)
            if ref == 'card_def_property':
                return self._get_card_def_property_value(player_id, expr.get('card', ''), expr.get('property', 'cost_e'), card)
            if ref == 'card_def_tags':
                return self._get_card_def_tags(player_id, expr.get('card', ''), card)
            if ref in ('equipment_property', 'equipment_prop'):
                eq = self._resolve_equipment_ref(player_id, expr.get('equipment', {'ref': 'current_equipment'}), card)
                return self._get_equipment_property_value(eq, expr.get('property', expr.get('prop', 'turns_equipped')))
            if ref == 'player_property':
                target_id = self._resolve_target(player_id, expr.get('target', 'self'))
                return self._get_player_property_value(target_id, expr.get('property', 'health'))
            if ref == 'var':
                target = expr.get('target', 'self')
                name = str(expr.get('name', 'var'))
                target_id = self._resolve_target(player_id, target)
                if self._is_suppressed_status_var(target_id, name):
                    return 0
                return self._scalar_value(self._var_store_for_target(player_id, target).get(name, 0), 0)
            if ref == 'list_var':
                return self._scalar_value(self._eval_list(player_id, expr, card), 0)
            if ref == 'list':
                return self._scalar_value(self._eval_list(player_id, expr, card), 0)
            if ref == 'zone_list':
                return self._scalar_value(self._eval_list(player_id, expr, card), 0)
            if ref == 'list_length':
                return len(self._eval_list(player_id, expr.get('list', []), card))
            if ref == 'list_item':
                return self._scalar_value(self._list_item_raw(player_id, expr, card), 0)
        return self._base_eval_expr(player_id, expr, card)

    def _eval_condition(self, player_id, cond, card=None):
        if isinstance(cond, dict) and cond.get('op') == 'equip_turns':
            a = self._eval_expr(player_id, {'ref': 'equip_turns'}, card)
            b = int(self._eval_expr(player_id, cond.get('value', 0), card))
            cmp = cond.get('operator', '=')
            return (a == b) if cmp == '=' else (a != b) if cmp == '!=' else (a < b) if cmp == '<' else (a > b) if cmp == '>' else (a <= b) if cmp == '<=' else (a >= b)
        if isinstance(cond, dict) and cond.get('op') == 'var_compare':
            name = str(cond.get('name', 'var'))
            target_ref = self._resolve_target(player_id, cond.get('target', 'self'))
            if self._is_suppressed_status_var(target_ref, name):
                a = 0
            else:
                a = int(self._scalar_value(self._var_store_for_target(player_id, cond.get('target', 'self')).get(name, 0), 0))
            b = int(self._eval_expr(player_id, cond.get('value', 0), card))
            cmp = cond.get('operator', '=')
            return (a == b) if cmp == '=' else (a != b) if cmp == '!=' else (a < b) if cmp == '<' else (a > b) if cmp == '>' else (a <= b) if cmp == '<=' else (a >= b)
        if isinstance(cond, dict) and cond.get('op') in ('has_status_named', 'has_status'):
            target_id = self._resolve_target(player_id, cond.get('target', 'self'))
            status_name = str(cond.get('name', cond.get('status', cond.get('id', ''))))
            if self._is_status_immune(target_id) and status_name not in ('status_immune', 'immune', '状态免疫'):
                return False
        if isinstance(cond, dict) and cond.get('op') == 'list_contains':
            values = self._eval_list(player_id, cond.get('list', []), card)
            item = self._serializable_list_item(self._eval_raw_item(player_id, cond.get('item', 0), card))
            return any(self._same_list_item(value, item) for value in values)
        if isinstance(cond, dict) and cond.get('op') == 'damage_source_relation':
            context = getattr(self, '_active_effect_context', {}) or {}
            source_id = int(context.get('source_id', player_id))
            target_id = int(context.get('target_id', player_id))
            relation = str(cond.get('relation', 'any'))
            if relation == 'any':
                return 0 <= source_id < len(self.players)
            if relation == 'self':
                return source_id == target_id
            same_side = self._same_timer_side(source_id, target_id)
            if relation in ('friendly', 'ally'):
                return same_side and source_id != target_id
            if relation == 'same_side':
                return same_side
            if relation == 'enemy':
                return self._opposite_timer_side(source_id, target_id)
            return False
        if isinstance(cond, dict) and cond.get('op') == 'event_card_type':
            context = getattr(self, '_active_effect_context', {}) or {}
            expected = str(cond.get('card_type', 'any') or 'any')
            actual = str(context.get('event_card_type', '') or '')
            return expected == 'any' or expected == actual
        if isinstance(cond, dict) and cond.get('op') == 'has_tag':
            target_card = self._resolve_card_ref(player_id, cond.get('card', {'ref': 'current_card'}), card)
            if target_card is None:
                return False
            tag = normalize_card_flag(cond.get('tag', ''))
            flags = normalize_card_flags(getattr(target_card.card_def, 'flags', set()) or set())
            flags.update(normalize_card_flags(getattr(target_card, 'instance_flags', set()) or set()))
            flags.difference_update(normalize_card_flags(getattr(target_card, 'disabled_flags', set()) or set()))
            return tag in flags
        return self._base_eval_condition(player_id, cond, card)

    def _eval_int(self, player_id, value, card=None, default=0):
        try:
            return int(self._scalar_value(self._eval_expr(player_id, value, card), default))
        except Exception:
            try:
                return int(value)
            except Exception:
                return default

    def _card_needs_choice(self, card: CardInstance) -> bool:
        if 'wide_strike' in self._effective_card_flags(card):
            return False
        if self._card_is(card, 'Spikeball', 'ocean:spikeball'):
            owner_id, zone_name, _ = self._find_card_location(card)
            if owner_id is not None and zone_name == 'hand':
                try:
                    if len(self.players[owner_id].hand) < 4:
                        return False
                except Exception:
                    pass
        if self._base_card_needs_choice(card):
            return True
        if self._get_choice_request(card) is not None:
            return True
        return self._v2_play_requires_choice_target(card) or self._root_play_requires_owner_target(card)

    def _get_choice_type(self, card: CardInstance) -> str:
        if 'wide_strike' in self._effective_card_flags(card):
            return ''
        effect = self._get_choice_request(card)
        if effect:
            return self._choice_type_for_effect(effect, card)
        if self._v2_play_requires_choice_target(card) or self._root_play_requires_owner_target(card):
            return 'choose_target'
        base = self._base_get_choice_type(card)
        return base or ''

    def _choice_satisfies_request(self, card: CardInstance, choice) -> bool:
        if not self._card_needs_choice(card):
            return True
        if not isinstance(choice, dict):
            return False
        if self._get_choice_request(card, choice) is not None:
            return False
        if 'wide_strike' in self._effective_card_flags(card):
            return True
        if self._v2_play_requires_choice_target(card) or self._root_play_requires_owner_target(card):
            return self._choice_target_from_choice(choice) >= 0
        return True

    def _process_atomic_effects(self, player_id: int, card: CardInstance, choice: Optional[dict], context: str):
        context_name = context if isinstance(context, str) else str((context or {}).get('context', ''))
        context_dict = context if isinstance(context, dict) else ({'context': context} if context else {})
        effects = self._play_effects_for_card(card) if context_name == 'play' else card.card_def.effects
        prev_choice = getattr(self, '_active_choice', None)
        if isinstance(choice, dict):
            self._active_choice = choice
        try:
            for effect in effects:
                if isinstance(effect, str):
                    eff_type = effect
                    params = {}
                    log = ''
                else:
                    eff_type = effect.get('type', '')
                    params = effect.get('params', {})
                    log = effect.get('log', '')
                if context_name == 'play' and eff_type in self.EVENT_EFFECT_TYPES:
                    continue
                if eff_type in self.PASSIVE_EFFECT_TYPES and context_name == 'play':
                    if log:
                        self.log_msg(log)
                    continue
                resolved_type = self._EFFECT_ALIASES.get(eff_type, eff_type)
                handler = getattr(self, f'_atomic_{resolved_type}', None)
                try:
                    before_stats = self._snapshot_player_stats()
                    if handler:
                        handler(player_id, card, params, log, choice, context_dict)
                    elif log:
                        self.log_msg(log)
                    else:
                        self._log_mod_runtime_error(eff_type, RuntimeError(f'Unknown effect: {eff_type}'), player_id, card)
                    if resolved_type not in ('if', 'if_else', 'repeat', 'repeat_until', 'for_each',
                                             'for_each_selected_card', 'for_each_list', 'timed_effect',
                                             'countdown_var', 'cost_e', 'cost_m'):
                        self._dispatch_player_stat_changes(before_stats, player_id, card)
                except (ModLoopBreak, ModLoopContinue) as exc:
                    self._log_mod_runtime_error(eff_type, RuntimeError(f'{type(exc).__name__} outside loop'), player_id, card)
                except Exception as exc:
                    self._log_mod_runtime_error(eff_type, exc, player_id, card)
        finally:
            self._active_choice = prev_choice

    def _apply_card_effect(self, player_id: int, card: CardInstance, choice: Optional[dict] = None):
        previous_card = getattr(self, '_active_v2_card', None)
        self._active_v2_card = card
        try:
            if self._card_is(card, 'Yggdrasil', 'vanilla:yggdrasil'):
                self._effect_yggdrasil(player_id, card, choice)
                return
            # For thorn cards with damage/hits but no dedicated effect handler,
            # apply attack damage only if the card has no v2 on_play event
            # (v2 events handle their own damage logic)
            card_damage = getattr(card.card_def, 'damage', 0)
            card_hits_val = self._card_total_hits(card)
            has_v2_play = self._card_has_v2_event(card.card_def, 'on_play')
            if card.card_type == 'thorn' and card_damage > 0 and not has_v2_play:
                method_name = f'_effect_{card.def_id.lower()}'
                if not hasattr(self, method_name):
                    dmg = self._modified_attack_damage(card_damage, card)
                    is_precision = 'precision' in self._effective_card_flags(card)
                    if 'wide_strike' in self._effective_card_flags(card):
                        target_ids = self._wide_strike_target_ids(player_id, card)
                    elif hasattr(self, '_selected_attack_target'):
                        target_id = self._selected_attack_target(player_id, choice)
                        target_ids = [target_id]
                    else:
                        target_id = 1 - player_id
                        target_ids = [target_id]
                    for target_id in target_ids:
                        if not (0 <= int(target_id) < len(self.players)):
                            continue
                        self.deal_attack_damage(target_id, dmg, card_hits_val, is_precision=is_precision, attacker_id=player_id, source_card=card)
            if self._card_has_v2_event(card.card_def, 'on_play'):
                self._run_v2_card_event(player_id, card, 'on_play', choice)
                return
            if self._card_has_script(card.card_def) or card.card_def.effects:
                self._process_atomic_effects(player_id, card, choice, 'play')
                return
            method_name = f'_effect_{card.def_id.lower()}'
            if hasattr(self, method_name):
                getattr(self, method_name)(player_id, card, choice)
            else:
                self.log_msg(f"{self.pn(player_id)}使用了{card.name_cn}")
        finally:
            self._active_v2_card = previous_card

    def _uses_atomic_play_effects(self, card: CardInstance) -> bool:
        return bool(self._card_has_v2_event(card.card_def, 'on_play') or self._card_has_script(card.card_def) or card.card_def.effects)

    def _is_chilli_card(self, card: Optional[CardInstance]) -> bool:
        if card is None:
            return False
        card_def = getattr(card, 'card_def', None)
        values = {
            str(getattr(card, 'def_id', '') or ''),
            str(getattr(card_def, 'id', '') or ''),
            str(getattr(card_def, 'legacy_id', '') or ''),
            str(getattr(card_def, 'name_cn', '') or ''),
            str(getattr(card_def, 'name_en', '') or ''),
        }
        normalized = {value.strip().lower().replace(' ', '') for value in values if value}
        return bool(
            values.intersection({'Chilli', 'vanilla:chilli', '辣椒', 'MagicChilli', 'vanilla:magicchilli', '魔法辣椒', 'Magic Chilli'})
            or normalized.intersection({'chilli', 'vanilla:chilli', 'magicchilli', 'vanilla:magicchilli'})
        )

    def _log_chilli_summary(self, player_id: int, discarded: bool, card: Optional[CardInstance] = None, discard_count: int = 0):
        card_def = getattr(card, 'card_def', None)
        values = {
            str(getattr(card, 'def_id', '') or ''),
            str(getattr(card_def, 'id', '') or ''),
            str(getattr(card_def, 'legacy_id', '') or ''),
            str(getattr(card_def, 'name_cn', '') or ''),
            str(getattr(card_def, 'name_en', '') or ''),
        }
        normalized = {value.strip().lower().replace(' ', '') for value in values if value}
        if values.intersection({'MagicChilli', 'vanilla:magicchilli', '魔法辣椒', 'Magic Chilli'}) or normalized.intersection({'magicchilli', 'vanilla:magicchilli'}):
            if discarded:
                self.log_msg(f"{self.pn(player_id)}使用魔法辣椒，弃{max(1, int(discard_count or 0))}张并抽至手牌上限")
            else:
                self.log_msg(f"{self.pn(player_id)}使用魔法辣椒，抽至手牌上限")
            return
        if discarded:
            self.log_msg(f"{self.pn(player_id)}使用辣椒，弃1张并抽1张牌")
        else:
            self.log_msg(f"{self.pn(player_id)}使用辣椒，抽1张牌")

    def _card_has_v2_event(self, card_def, event_name: str) -> bool:
        return self._get_v2_event_def(card_def, event_name) is not None

    def _get_v2_event_def(self, card_def, event_name: str):
        events = getattr(card_def, 'v2_events', None)
        if not isinstance(events, dict):
            return None
        if events.get(event_name):
            return events.get(event_name)
        if event_name.startswith('on_'):
            legacy_name = event_name[3:]
            if events.get(legacy_name):
                return events.get(legacy_name)
        return None

    def _card_is_self_only(self, card: Optional[CardInstance]) -> bool:
        if card is None:
            return False
        flags = set(getattr(card, 'flags', set()) or set())
        card_def = getattr(card, 'card_def', None)
        if card_def is not None:
            flags.update(getattr(card_def, 'flags', []) or [])
        return 'self_only' in flags or 'tag_self_only' in flags

    def _effect_tree_uses_target_selector(self, value, depth: int = 0) -> bool:
        if depth > 20:
            return False
        if isinstance(value, str):
            return value in ('target', 'event_target')
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ('target', 'targets', 'target_player', 'effect_target') and self._effect_tree_uses_target_selector(item, depth + 1):
                    return True
                if self._effect_tree_uses_target_selector(item, depth + 1):
                    return True
            return False
        if isinstance(value, (list, tuple)):
            return any(self._effect_tree_uses_target_selector(item, depth + 1) for item in value)
        return False

    def _effect_tree_uses_choice_target(self, value, depth: int = 0) -> bool:
        if depth > 20:
            return False
        if isinstance(value, str):
            return value in ('choice_target', 'chosen_target', 'selected_target')
        if isinstance(value, dict):
            return any(self._effect_tree_uses_choice_target(item, depth + 1) for item in value.values())
        if isinstance(value, (list, tuple)):
            return any(self._effect_tree_uses_choice_target(item, depth + 1) for item in value)
        return False

    def _v2_play_requires_choice_target(self, card: Optional[CardInstance]) -> bool:
        if card is None or not getattr(card, 'card_def', None):
            return False
        if card.card_type in ('thorn', 'guard'):
            return False
        if self._card_is_self_only(card):
            return False
        events = getattr(card.card_def, 'v2_events', None) or {}
        event_def = events.get('on_play')
        return self._effect_tree_uses_choice_target(event_def) or self._effect_tree_uses_target_selector(event_def)

    def _root_equipment_events_use_effect_target(self, card: Optional[CardInstance]) -> bool:
        if card is None or not getattr(card, 'card_def', None):
            return False
        events = getattr(card.card_def, 'v2_events', None) or {}
        for event_name, event_def in events.items():
            name = str(event_name or '')
            if name in ('on_play', 'play'):
                continue
            # Manual trigger cards choose their target when triggered, not when equipped.
            if 'trigger' in name:
                continue
            if not (
                'equip' in name
                or 'turn_start' in name
                or 'turn_end' in name
                or 'damage' in name
                or 'destroy' in name
            ):
                continue
            if self._effect_tree_uses_choice_target(event_def) or self._effect_tree_uses_target_selector(event_def):
                return True
        return False

    def _root_play_requires_owner_target(self, card: Optional[CardInstance]) -> bool:
        if card is None or getattr(card, 'card_type', '') != 'root':
            return False
        if self._card_is_self_only(card):
            return False
        if self._root_equipment_events_use_effect_target(card):
            return True
        target_on_equip_ids = {
            'Cactus', 'desert_cards_addition:cactus',
            'Coconut', 'desert_cards_addition:coconut',
            'Uranium', 'factory:uranium',
            'MagicUranium', 'factory:magicuranium',
            'Cutter', 'factory:cutter',
            'ElectricWeb', 'factory:electricweb',
            'Goggles', 'factory:goggles',
            'Soil', 'garden:soil',
            'Web', 'garden:web',
            'Faster', 'garden:faster',
            'Cotton', 'jungle:cotton',
            'MagicCotton', 'jungle:magic_cotton',
            'Plank', 'jungle:plank',
            'Root', 'jungle:root',
            'Sponge', 'ocean:sponge', 'troll_cards:sponge',
            'Pill', 'vanilla:pill', 'troll_cards:pill',
            'Leaf', 'vanilla:leaf',
            'Yucca', 'vanilla:yucca',
            'Disc', 'vanilla:disc',
            'Battery', 'vanilla:battery',
            'MagicLeaf', 'vanilla:magicleaf',
            'MagicYucca', 'vanilla:magicyucca',
            'MagicBattery', 'vanilla:magicbattery',
            'Powder', 'vanilla:powder',
            'GoldenLeaf', 'vanilla:goldenleaf',
            'Pincer', 'vanilla:pincer',
            'Cancer', 'vanilla:cancer',
            'MagicGoldenLeaf', 'vanilla:magicgoldenleaf',
        }
        return self._card_matches_any_id(card, getattr(card, 'card_def', None), target_on_equip_ids)

    def _default_enemy_target_for_event(self, player_id: int) -> int:
        if hasattr(self, 'get_enemies'):
            try:
                enemies = list(self.get_enemies(player_id))
            except Exception:
                enemies = []
        else:
            enemies = [1 - player_id] if len(self.players) == 2 else []
        for target_id in enemies:
            if self._target_can_be_selected(player_id, target_id, allow_self=False):
                return target_id
        return -1

    def _infer_v2_event_target(self, player_id: int, card: CardInstance, event_name: str,
                               choice: Optional[dict], extra_context: Optional[dict]) -> int:
        if event_name != 'on_play':
            return -1
        events = getattr(card.card_def, 'v2_events', None) or {}
        event_def = events.get(event_name)
        uses_choice_target = self._effect_tree_uses_choice_target(event_def)
        uses_implicit_target = self._effect_tree_uses_target_selector(event_def)
        if not uses_choice_target and not uses_implicit_target:
            return -1
        if self._card_is_self_only(card) and card.card_type != 'thorn':
            return player_id
        if card.card_type == 'guard':
            return player_id
        if isinstance(choice, dict):
            selected = self._selected_choice_target(-1)
            if 0 <= selected < len(self.players):
                return selected
            for key in ('target_player', 'target_player_id', 'target_id'):
                if key in choice:
                    try:
                        selected = int(choice.get(key))
                    except Exception:
                        selected = -1
                    if 0 <= selected < len(self.players):
                        return selected
        if uses_choice_target and not uses_implicit_target and card.card_type not in ('thorn', 'guard'):
            return -1
        selected = self._default_enemy_target_for_event(player_id)
        if selected >= 0:
            return selected
        return -1

    def _run_v2_card_event(self, player_id: int, card: CardInstance, event_name: str,
                           choice: Optional[dict] = None, extra_context: Optional[dict] = None):
        event_def = self._get_v2_event_def(card.card_def, event_name)
        extra_context = extra_context if isinstance(extra_context, dict) else {}
        current_eq = self._find_equipment_for_card(player_id, card) if event_name != 'on_play' else None
        target_id = -1
        target_explicit = False
        if isinstance(choice, dict):
            for key in ('target_player', 'target_player_id', 'target_id'):
                if key in choice:
                    try:
                        target_id = int(choice.get(key))
                        target_explicit = True
                        break
                    except Exception:
                        target_id = -1
        if target_id < 0:
            for key in ('target_player', 'target_player_id', 'target_id'):
                if key in extra_context:
                    try:
                        target_id = int(extra_context.get(key))
                        target_explicit = bool(extra_context.get('target_player_explicit', True))
                        break
                    except Exception:
                        target_id = -1
        if target_id < 0 or target_id >= len(self.players):
            inferred_target = self._infer_v2_event_target(player_id, card, event_name, choice, extra_context)
            if 0 <= inferred_target < len(self.players):
                target_id = inferred_target
        if (target_id < 0 or target_id >= len(self.players)) and event_name != 'on_play':
            target_id = player_id
        context_target_id = extra_context.get('target_id', target_id)
        if isinstance(choice, dict):
            for key in ('target_player', 'target_player_id', 'target_id'):
                if key in choice:
                    try:
                        context_target_id = int(choice.get(key))
                        break
                    except Exception:
                        pass
        context = {
            'source_player': player_id,
            'target_player': target_id,
            'source_id': extra_context.get('source_id', player_id),
            'target_id': context_target_id,
            'damage_source': extra_context.get('damage_source', extra_context.get('source_id', player_id)),
            'target_player_explicit': target_explicit,
            'card': card,
            'room': getattr(self, 'room', None),
            'loadout': getattr(self, 'v2_loadout', None),
            'vars': {**dict(extra_context), 'listener_owner_id': player_id},
            'last_damage': int(extra_context.get('last_damage', extra_context.get('damage', extra_context.get('damage_amount', 0))) or 0),
            'damage': int(extra_context.get('damage', extra_context.get('damage_amount', 0)) or 0),
            'damage_amount': int(extra_context.get('damage_amount', extra_context.get('damage', 0)) or 0),
            'event_value': extra_context.get('event_value', extra_context.get('damage_amount', extra_context.get('damage', 0))),
            'current_event': event_name,
            'current_action': {'choice': choice or {}, **extra_context},
        }
        if event_name == 'on_play' and 'wide_strike' in self._effective_card_flags(card):
            wide_targets = self._wide_strike_target_ids(player_id, card)
            context['wide_strike_targets'] = wide_targets
            context['target_players'] = wide_targets
            context['vars']['wide_strike_targets'] = wide_targets
            context['current_action']['wide_strike_targets'] = wide_targets
            if wide_targets:
                context['target_player'] = wide_targets[0]
                context['target_id'] = wide_targets[0]
                context['target_player_explicit'] = False
        if current_eq is not None:
            context['current_equipment'] = current_eq
            context['selected_equipment_instance_id'] = current_eq.card_instance.instance_id
            context['selected_equipment_owner_id'] = player_id
        if event_name == 'on_play' and self._is_chilli_card(card):
            context['suppress_detail_logs'] = True
        if isinstance(choice, dict):
            instance_ids = []
            if choice.get('target_instance_id') is not None:
                instance_ids.append(choice.get('target_instance_id'))
            if isinstance(choice.get('target_instance_ids'), list):
                instance_ids.extend(choice.get('target_instance_ids'))
            chosen_cards = []
            seen_ids = set()
            for instance_id in instance_ids:
                try:
                    iid = int(instance_id)
                except Exception:
                    continue
                if iid in seen_ids:
                    continue
                seen_ids.add(iid)
                selected = self._find_card_by_instance_id(iid)
                if selected is not None and self._card_selectable_by_action(selected):
                    chosen_cards.append(selected)
            if chosen_cards:
                context['chosen_card'] = chosen_cards[0]
                context['chosen_cards'] = chosen_cards
        result = run_v2_event(self, context, event_def)
        if isinstance(result, dict) and result.get('needs_v2_ui'):
            self._store_v2_ui_pause(result.get('v2_ui_pause') or {}, card)
        elif event_name == 'on_play' and self._is_chilli_card(card):
            chosen_cards = context.get('chosen_cards') if isinstance(context.get('chosen_cards'), list) else []
            self._log_chilli_summary(player_id, bool(chosen_cards), card, len(chosen_cards))
        return result

    def _store_v2_ui_pause(self, pause: dict, card: Optional[CardInstance] = None):
        if not isinstance(pause, dict):
            return
        request_id = str(pause.get('request_id') or '')
        component = pause.get('component') if isinstance(pause.get('component'), dict) else {}
        context = pause.get('context') if isinstance(pause.get('context'), dict) else {}
        target_player = pause.get('target_player', context.get('source_player', 0))
        try:
            target_player = int(target_player)
        except Exception:
            target_player = 0
        if target_player < 0 or target_player >= len(self.players):
            target_player = 0
        self.pending_v2_ui = {
            'request_id': request_id,
            'player_id': target_player,
            'component': component,
            'save_as': str(pause.get('save_as') or 'ui_result'),
            'timeout_ms': int(pause.get('timeout_ms') or 0),
            'on_cancel': pause.get('on_cancel', []) if isinstance(pause.get('on_cancel', []), list) else [],
            'remaining_steps': pause.get('remaining_steps', []) if isinstance(pause.get('remaining_steps', []), list) else [],
            'context': context,
            'card': card.to_dict() if card is not None else (
                context.get('card').to_dict() if isinstance(context.get('card'), CardInstance) else None
            ),
        }

    def _public_v2_ui(self, for_player: int) -> Optional[dict]:
        pending = getattr(self, 'pending_v2_ui', None)
        if not pending or pending.get('player_id') != for_player:
            return None
        return {
            'request_id': pending.get('request_id'),
            'component': pending.get('component'),
            'card': pending.get('card'),
            'timeout_ms': pending.get('timeout_ms', 0),
        }

    def handle_v2_ui_response(self, player_id: int, request_id: str, response: Optional[dict]) -> dict:
        pending = getattr(self, 'pending_v2_ui', None)
        if not pending:
            return {'success': False, 'error': 'No pending v2 UI request'}
        if pending.get('player_id') != player_id or str(pending.get('request_id')) != str(request_id):
            return {'success': False, 'error': 'Invalid v2 UI response'}
        context = pending.get('context') if isinstance(pending.get('context'), dict) else {}
        component = pending.get('component') if isinstance(pending.get('component'), dict) else {}
        try:
            clean = validate_v2_ui_response(self, context, component, response or {})
            self.pending_v2_ui = None
            button = clean.get('button')
            button_role = self._v2_button_role(component, button)
            if button_role == 'cancel':
                cancel_steps = pending.get('on_cancel', []) if isinstance(pending.get('on_cancel', []), list) else []
                if cancel_steps:
                    result = run_v2_steps(self, context, cancel_steps)
                    if isinstance(result, dict) and result.get('needs_v2_ui'):
                        self._store_v2_ui_pause(result.get('v2_ui_pause') or {})
                        return {'success': True, 'needs_v2_ui': True}
                return {'success': True, 'cancelled': True}
            context.setdefault('vars', {})[pending.get('save_as') or 'ui_result'] = clean.get('values', {})
            context['current_action'] = {
                **(context.get('current_action') if isinstance(context.get('current_action'), dict) else {}),
                'v2_ui': clean,
            }
            result = run_v2_steps(self, context, pending.get('remaining_steps') or [])
            if isinstance(result, dict) and result.get('needs_v2_ui'):
                self._store_v2_ui_pause(result.get('v2_ui_pause') or {})
                return {'success': True, 'needs_v2_ui': True}
            self._check_game_over()
            return {'success': True}
        except Exception as exc:
            self.pending_v2_ui = None
            self._log_mod_runtime_error('request_ui', exc, player_id, None)
            return {'success': False, 'error': str(exc)}

    def _v2_button_role(self, component: dict, button_id: str) -> str:
        for button in component.get('buttons', []) if isinstance(component.get('buttons'), list) else []:
            if isinstance(button, dict) and str(button.get('id')) == str(button_id):
                return str(button.get('role') or ('cancel' if button_id == 'cancel' else 'confirm'))
        return 'cancel' if button_id == 'cancel' else 'confirm'

    def _card_log_marker(self, card: CardInstance) -> str:
        try:
            payload = card.to_dict()
            payload.pop('instance_id', None)
            hidden_log_flags = {'ocean_no_auto', 'ocean_spikeball_boosted', 'multi_petal_fission'}
            payload['instance_flags'] = [
                flag for flag in (payload.get('instance_flags') or [])
                if normalize_card_flag(flag) not in hidden_log_flags
            ]
            raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            encoded = base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')
            return f'\u2063CARD:{encoded}\u2063'
        except Exception:
            return ''

    def _log_card_play(self, player_id: int, card: CardInstance):
        self.log_msg(f"{self.pn(player_id)}使用了{card.name_cn}{self._card_log_marker(card)}")

    def _log_equipment_trigger(self, player_id: int, eq: EquipmentInstance):
        card = getattr(eq, 'card_instance', None)
        if card is None:
            return
        self.log_msg(f"{self.pn(player_id)}触发{card.name_cn}{self._card_log_marker(card)}")

    def _effective_card_flags(self, target_card: Optional[CardInstance]) -> Set[str]:
        if target_card is None:
            return set()
        flags = normalize_card_flags(getattr(target_card.card_def, 'flags', set()) or set())
        flags.update(normalize_card_flags(getattr(target_card, 'instance_flags', set()) or set()))
        flags.difference_update(normalize_card_flags(getattr(target_card, 'disabled_flags', set()) or set()))
        return flags

    def _card_blocks_response(self, card: Optional[CardInstance]) -> bool:
        return 'stealth' in self._effective_card_flags(card)

    def _wide_strike_target_ids(self, player_id: int, card: Optional[CardInstance]) -> List[int]:
        flags = self._effective_card_flags(card)
        is_attack = bool(getattr(card, 'card_type', '') == 'thorn')
        allow_self = 'self_target' in flags or not is_attack
        targets: List[int] = []
        team_of = getattr(self, 'team_of', None)
        own_team = None
        if callable(team_of):
            try:
                own_team = team_of(player_id)
            except Exception:
                own_team = None
        for tid in range(len(getattr(self, 'players', []) or [])):
            if tid == player_id:
                if not allow_self:
                    continue
            elif is_attack and own_team is not None:
                try:
                    if team_of(tid) == own_team:
                        continue
                except Exception:
                    pass
            if self._target_can_be_selected(player_id, tid, allow_self=allow_self):
                targets.append(tid)
        return targets

    def _event_relation_matches(self, listener_owner: int, actor_id: int, relation: str) -> bool:
        relation = str(relation or 'any')
        if relation in ('any', 'all', 'both'):
            return 0 <= actor_id < len(self.players)
        if relation in ('self', 'owner'):
            return actor_id == listener_owner
        if relation in ('teammate', 'ally'):
            return self._same_timer_side(listener_owner, actor_id) and actor_id != listener_owner
        if relation in ('friendly', 'same_side'):
            return self._same_timer_side(listener_owner, actor_id)
        if relation == 'enemy':
            return self._opposite_timer_side(listener_owner, actor_id)
        return False

    def _event_wrapper_matches(self, owner_id: int, event_name: str, params: dict,
                               extra_context: Optional[dict]) -> bool:
        context = extra_context or {}
        relation = str(params.get('relation', 'any') or 'any')
        actor_id = int(context.get('source_id', owner_id))
        if event_name == 'equipment_destroyed':
            actor_id = int(context.get('target_id', actor_id))
        if event_name == 'player_stat_changed':
            actor_id = int(context.get('target_id', actor_id))
        if not self._event_relation_matches(owner_id, actor_id, relation):
            return False
        if event_name == 'card_used':
            expected_type = str(params.get('card_type', 'any') or 'any')
            actual_type = str(context.get('event_card_type', '') or '')
            if expected_type != 'any' and actual_type != expected_type:
                return False
        if event_name == 'resource_spent':
            expected_resource = str(params.get('resource', 'elixir') or 'elixir')
            actual_resource = str(context.get('resource', '') or '')
            if expected_resource != actual_resource:
                return False
            threshold = max(1, self._eval_int(owner_id, params.get('amount', 1), None, 1))
            if int(context.get('amount', 0) or 0) < threshold:
                return False
        if event_name == 'player_stat_changed':
            expected_prop = str(params.get('property', 'health') or 'health')
            actual_prop = str(context.get('property', '') or '')
            if expected_prop != actual_prop:
                return False
            expected_dir = str(params.get('direction', 'change') or 'change')
            actual_dir = str(context.get('direction', 'change') or 'change')
            if expected_dir != 'change' and expected_dir != actual_dir:
                return False
        return True

    def _resource_event_repeat_count(self, owner_id: int, params: dict, extra_context: Optional[dict]) -> int:
        if not extra_context:
            return 1
        amount = int(extra_context.get('amount', 0) or 0)
        threshold = max(1, self._eval_int(owner_id, params.get('amount', 1), None, 1))
        return max(1, amount // threshold)

    def _iter_event_listener_cards(self):
        seen = set()
        for owner_id, ps in enumerate(self.players):
            for eq in list(getattr(ps, 'equipment', [])):
                card_obj = getattr(eq, 'card_instance', None)
                iid = getattr(card_obj, 'instance_id', None)
                if card_obj is not None and iid not in seen:
                    seen.add(iid)
                    yield owner_id, card_obj, eq
            for card_obj in list(getattr(ps, 'hand', [])):
                iid = getattr(card_obj, 'instance_id', None)
                if card_obj is not None and iid not in seen:
                    seen.add(iid)
                    yield owner_id, card_obj, None

    def _dispatch_card_event(self, event_name: str, source_id: int, event_card: Optional[CardInstance] = None,
                             target_id: Optional[int] = None, equipment: Optional[EquipmentInstance] = None,
                             equipment_owner_id: Optional[int] = None, choice: Optional[dict] = None,
                             extra_context: Optional[dict] = None):
        try:
            card_user_id = int(source_id)
        except (TypeError, ValueError):
            card_user_id = -1
        if event_name == 'card_used' and event_card is not None and 0 <= card_user_id < len(self.players):
            ps = self.players[card_user_id]
            ps.achievement_total_card_plays = max(
                0,
                int(getattr(ps, 'achievement_total_card_plays', 0) or 0),
            ) + 1
        event_card_id = getattr(event_card, 'instance_id', None)
        context = {
            'source_id': source_id,
            'target_id': source_id if target_id is None else target_id,
            'event_card_instance_id': event_card_id,
            'event_card_def_id': getattr(event_card, 'def_id', ''),
            'event_card_type': getattr(event_card, 'card_type', getattr(getattr(event_card, 'card_def', None), 'card_type', '')),
            'event_card_cost_e': int(getattr(event_card, '_paid_e_this_play', getattr(event_card, 'cost_e', 0)) or 0) if event_card is not None else 0,
            'event_card_cost_m': int(getattr(event_card, '_paid_m_this_play', getattr(event_card, 'cost_m', 0)) or 0) if event_card is not None else 0,
        }
        if equipment is not None:
            context['selected_equipment_instance_id'] = getattr(getattr(equipment, 'card_instance', None), 'instance_id', None)
            context['selected_equipment_owner_id'] = equipment_owner_id if equipment_owner_id is not None else source_id
        if isinstance(extra_context, dict):
            context.update(extra_context)
        for owner_id, listener_card, _ in list(self._iter_event_listener_cards()):
            if getattr(listener_card, 'instance_id', None) == event_card_id:
                continue
            if not self._has_card_event(listener_card.card_def, event_name):
                continue
            listener_context = dict(context)
            listener_eq = self._find_equipment_for_card(owner_id, listener_card)
            if listener_eq is not None:
                listener_context['selected_equipment_instance_id'] = listener_eq.card_instance.instance_id
                listener_context['selected_equipment_owner_id'] = owner_id
            self._run_card_event(owner_id, listener_card, event_name, choice, listener_context)

    def _has_fatal_prevention(self, player_id: int) -> bool:
        if not (0 <= player_id < len(self.players)):
            return False
        ps = self.players[player_id]
        if (ps.bandage_active or ps.invincible) and not self._is_status_immune(player_id):
            return True
        for card in list(ps.hand):
            if getattr(card, 'def_id', '') == 'Yggdrasil':
                return True
            for effect in getattr(card.card_def, 'effects', []) or []:
                if isinstance(effect, dict) and effect.get('type') == 'on_fatal_set_health_exile':
                    return True
        return False

    def _start_turn_status_damage_would_defeat(self, player_id: int) -> bool:
        if not (0 <= player_id < len(self.players)):
            return False
        ps = self.players[player_id]
        if ps.health <= 0:
            return True
        if self._is_status_immune(player_id):
            return False
        if self._has_fatal_prevention(player_id):
            return False
        multiplier = self._get_corruption_multiplier()
        pending_damage = (
            math.ceil(max(0, int(ps.poison or 0)) * multiplier)
            + math.ceil(max(0, int(ps.fire or 0)) * multiplier)
        )
        return pending_damage >= ps.health

    def _resolve_start_turn_status_damage_for_transition(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        if self._is_status_immune(player_id):
            return
        ps = self.players[player_id]
        self._game_over_defer_depth += 1
        try:
            if ps.poison > 0:
                dmg = ps.poison
                self._deal_direct_damage(player_id, dmg, '中毒', damage_type=DAMAGE_TYPE_MAGIC, damage_tag=DAMAGE_TAG_POISON)
                if ps.health > 0 and not self.game_over:
                    self._decay_poison_after_turn_start(player_id)
                    self._apply_toxic_poison_after_poison_settlement(player_id)
            if ps.health > 0 and not self.game_over and ps.fire > 0:
                self._deal_direct_damage(player_id, ps.fire, '灼烧', damage_type=DAMAGE_TYPE_MAGIC, damage_tag=DAMAGE_TAG_FIRE)
        finally:
            self._game_over_defer_depth -= 1

    TRACKED_PLAYER_STATS = (
        'health', 'max_health', 'elixir', 'max_elixir', 'magic', 'max_magic',
        'armor', 'dodge', 'poison', 'fire', 'toxic',
        'equipment_protection', 'hand_limit',
    )

    def _snapshot_player_stats(self):
        return [
            {prop: self._get_player_property_value(pid, prop) for prop in self.TRACKED_PLAYER_STATS}
            for pid in range(len(self.players))
        ]

    def _dispatch_player_stat_changes(self, before, source_id: int, source_card: Optional[CardInstance] = None):
        if not before:
            return
        depth = int(getattr(self, '_stat_change_event_depth', 0))
        if depth >= 4:
            return
        self._stat_change_event_depth = depth + 1
        try:
            for pid in range(min(len(before), len(self.players))):
                for prop, old_value in before[pid].items():
                    new_value = self._get_player_property_value(pid, prop)
                    if new_value == old_value:
                        continue
                    direction = 'increase' if new_value > old_value else 'decrease'
                    self._dispatch_card_event(
                        'player_stat_changed',
                        source_id,
                        source_card,
                        target_id=pid,
                        extra_context={
                            'property': prop,
                            'old_value': old_value,
                            'new_value': new_value,
                            'delta': new_value - old_value,
                            'direction': direction,
                        },
                    )
        finally:
            self._stat_change_event_depth = depth

    def _spend_resource(self, player_id: int, resource: str, amount: int, source_card: Optional[CardInstance] = None) -> int:
        if not (0 <= player_id < len(self.players)):
            return 0
        amount = max(0, int(amount or 0))
        if amount <= 0:
            return 0
        ps = self.players[player_id]
        attr = 'magic' if resource == 'magic' else 'elixir'
        before = self._snapshot_player_stats()
        actual = min(amount, int(getattr(ps, attr, 0)))
        setattr(ps, attr, max(0, int(getattr(ps, attr, 0)) - amount))
        if actual > 0:
            self._dispatch_card_event(
                'resource_spent',
                player_id,
                source_card,
                target_id=player_id,
                extra_context={'resource': attr, 'amount': actual},
            )
        self._dispatch_player_stat_changes(before, player_id, source_card)
        return actual

    def _equipment_trigger_max_uses(self, eq: EquipmentInstance) -> int:
        if eq is None:
            return 0
        events = getattr(eq.card_def, 'v2_events', None)
        if isinstance(events, dict):
            event_def = events.get('on_equipment_trigger')
            if isinstance(event_def, dict):
                value = event_def.get('max_uses_per_turn', event_def.get('max_uses', 0))
                try:
                    return max(0, int(value or 0))
                except Exception:
                    return 0
        for effect in getattr(eq.card_def, 'effects', []) or []:
            if not isinstance(effect, dict) or effect.get('type') != 'on_equipment_trigger':
                continue
            params = effect.get('params', {}) or {}
            value = params.get('max_uses_per_turn', params.get('max_uses', 0))
            try:
                return max(0, int(value or 0))
            except Exception:
                return 0
        return 0

    def _run_card_event(self, owner_id: int, card: CardInstance, event_name: str,
                        choice: Optional[dict] = None, extra_context: Optional[dict] = None) -> bool:
        v2_event_name = f'on_{event_name}'
        event_def = self._get_v2_event_def(card.card_def, v2_event_name)
        if event_def:
            self._run_v2_card_event(owner_id, card, v2_event_name, choice, extra_context)
            return True
        if self._has_script_entry(card.card_def, event_name):
            effects = self._get_script_effects(card.card_def, event_name)
            if not effects:
                return False
            self._run_effect_list(
                owner_id,
                card,
                effects,
                choice,
                {'event': event_name, **(extra_context or {})},
            )
            return True
        event_type = f'on_{event_name}'
        ran = False
        for effect in card.card_def.effects or []:
            if not isinstance(effect, dict) or effect.get('type') != event_type:
                continue
            params = effect.get('params', {}) or {}
            if not self._event_wrapper_matches(owner_id, event_name, params, extra_context):
                continue
            if event_type == 'on_equipment_trigger' and params.get('destroy_self'):
                eq = self._find_equipment_for_card(owner_id, card)
                if eq is not None and not self._destroy_equipment(owner_id, eq):
                    ran = True
                    continue
            repeat_count = self._resource_event_repeat_count(owner_id, params, extra_context) if event_name == 'resource_spent' else 1
            for repeat_index in range(repeat_count):
                self._run_effect_list(
                    owner_id,
                    card,
                    params.get('effects', []),
                    choice,
                    {'event': event_name, 'repeat_index': repeat_index + 1, **(extra_context or {}), 'listener_owner_id': owner_id},
                )
            ran = True
        return ran

    def _run_zone_owner_turn_start_events(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        for zone_name, event_name in (
            ('hand', 'hand_owner_turn_start'),
            ('discard', 'discard_owner_turn_start'),
            ('deck', 'deck_owner_turn_start'),
        ):
            zone = getattr(ps, zone_name, [])
            for zone_card in list(zone):
                if zone_card in zone and self._has_card_event(zone_card.card_def, event_name):
                    self._run_card_event(player_id, zone_card, event_name, None,
                                         {'source_id': player_id, 'target_id': player_id, 'zone': zone_name})

    def _run_hand_owner_turn_end_events(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        for zone_card in list(ps.hand):
            if zone_card in ps.hand and self._has_card_event(zone_card.card_def, 'hand_owner_turn_end'):
                self._run_card_event(player_id, zone_card, 'hand_owner_turn_end', None,
                                     {'source_id': player_id, 'target_id': player_id, 'zone': 'hand'})

    def _equipment_turn_start_key(self, eq) -> int:
        return int(getattr(getattr(eq, 'card_instance', None), 'instance_id', id(eq)) or id(eq))

    def _effect_tree_contains_heal(self, value, depth: int = 0) -> bool:
        if depth > 16:
            return False
        if isinstance(value, dict):
            op = str(value.get('op') or value.get('type') or '').strip()
            if op == 'heal':
                return True
            return any(self._effect_tree_contains_heal(v, depth + 1) for v in value.values())
        if isinstance(value, (list, tuple)):
            return any(self._effect_tree_contains_heal(item, depth + 1) for item in value)
        return False

    def _owner_turn_start_equipment_heals(self, eq) -> bool:
        if eq is None:
            return False
        if getattr(eq, 'def_id', '') in ('Leaf', 'Yucca'):
            return True
        card_def = getattr(eq, 'card_def', None)
        if card_def is None:
            return False
        events = getattr(card_def, 'v2_events', None)
        if isinstance(events, dict) and self._effect_tree_contains_heal(events.get('on_owner_turn_start')):
            return True
        for effect in getattr(card_def, 'effects', []) or []:
            if isinstance(effect, dict) and effect.get('type') == 'on_owner_turn_start':
                if self._effect_tree_contains_heal(effect):
                    return True
        if self._has_script_entry(card_def, 'owner_turn_start'):
            return self._effect_tree_contains_heal(self._get_script_effects(card_def, 'owner_turn_start'))
        return False

    def _iter_equipment_targeting_player(self, player_id: int):
        for owner_id, owner_state in enumerate(self.players):
            for eq in list(getattr(owner_state, 'equipment', [])):
                try:
                    effect_target = int(getattr(eq, 'effect_target', owner_id))
                except (TypeError, ValueError):
                    effect_target = owner_id
                if effect_target == player_id:
                    yield owner_id, eq

    def _decay_poison_after_turn_start(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        if ps.poison <= 0:
            return
        if getattr(ps, 'stagnation', 0) > 0 and not self._is_status_immune(player_id):
            self.log_msg(f"{self.pn(player_id)}的滞留使中毒未减半")
            return
        ps.poison = ps.poison // 2
        if ps.poison > 0:
            self.log_msg(f"{self.pn(player_id)}中毒减半为{ps.poison}层")

    def _apply_toxic_poison_after_poison_settlement(self, player_id: int):
        if not (0 <= player_id < len(self.players)) or self._is_status_immune(player_id):
            return
        amount = self._custom_status_value(player_id, 'jungle:toxic_poison', 'toxic_poison', '剧毒')
        if amount <= 0:
            return
        ps = self.players[player_id]
        ps.poison += amount
        self._normalize_status_value(ps, 'poison')
        self.log_msg(f"{self.pn(player_id)}的剧毒施加{amount}层中毒")

    def _decay_end_turn_layer_statuses(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        for attr, label in (('stagnation', '滞留'),):
            value = int(getattr(ps, attr, 0) or 0)
            if value <= 0:
                continue
            value = max(0, value - 1)
            setattr(ps, attr, value)
            if value == 0:
                self.log_msg(f"{self.pn(player_id)}的{label}效果消失")

    def _apply_blind_turn_start(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        blind_level = int(getattr(ps, 'blind', 0) or 0)
        if blind_level <= 0:
            return
        if self._is_status_immune(player_id):
            ps.blind = 0
            return
        if ps.hand:
            random.shuffle(ps.hand)
            self.log_msg(f"{self.pn(player_id)}因失明打乱手牌")
        ps.blind = 0

    def _apply_ocean_card_turn_start(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        reduced = 0
        for card in list(getattr(ps, 'hand', []) or []):
            charge = int(getattr(card, 'charge_value', 0) or 0)
            if charge > 0:
                card.charge_value = max(0, charge - 1)
                reduced += 1
                if card.charge_value <= 0:
                    card.instance_flags.discard('charge')
        if reduced:
            self.log_msg(f"{self.pn(player_id)}的手牌电荷减少")

    def _clear_ocean_card_hand_blind_turn_end(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        cleared = 0
        for card in list(getattr(self.players[player_id], 'hand', []) or []):
            if int(getattr(card, 'hand_blind_turns', 0) or 0) > 0:
                card.hand_blind_turns = 0
                card.instance_flags.discard('ocean_blinded')
                cleared += 1
        if cleared:
            self.log_msg(f"{self.pn(player_id)}的{cleared}张手牌蒙蔽消失")

    def _clear_turn_start_action_statuses(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        immune = self._is_status_immune(player_id)
        cleared = []
        for attr, label in (('blind', '失明'),):
            value = int(getattr(ps, attr, 0) or 0)
            if value <= 0:
                continue
            if attr == 'blind' and ps.hand and not immune:
                random.shuffle(ps.hand)
                self.log_msg(f"{self.pn(player_id)}因失明打乱手牌")
            setattr(ps, attr, 0)
            cleared.append(label)
        if cleared:
            self.log_msg(f"{self.pn(player_id)}的{ '、'.join(cleared) }效果清除")

    def _clear_sluggish_after_draw(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        ps = self.players[player_id]
        if int(getattr(ps, 'sluggish', 0) or 0) <= 0:
            return
        ps.sluggish = 0
        self.log_msg(f"{self.pn(player_id)}的迟缓效果清除")

    def _return_cogwheel_cards_now(self, player_id: int):
        if not (0 <= player_id < len(self.players)):
            return
        if not getattr(self, '_cogwheel_active', {}).get(player_id):
            return
        ps = self.players[player_id]
        exclude_id = int(getattr(self, '_cogwheel_exclude_instance_ids', {}).get(player_id, -1) or -1)
        exclude_def_id = ''
        for zone in (getattr(ps, 'hand', []), getattr(ps, 'discard', []), getattr(ps, 'exile', [])):
            for c in list(zone or []):
                try:
                    if int(getattr(c, 'instance_id', -1) or -1) == exclude_id:
                        exclude_def_id = str(getattr(c, 'def_id', '') or '')
                        break
                except Exception:
                    continue
            if exclude_def_id:
                break
        played_ids = list(getattr(ps, 'cards_played_this_turn_instance_ids', []) or [])
        returned = []
        for instance_id in played_ids:
            try:
                iid = int(instance_id)
            except Exception:
                continue
            if iid == exclude_id:
                continue
            found = None
            source_zone = None
            for zone in (getattr(ps, 'deck', []), getattr(ps, 'discard', [])):
                for c in list(zone):
                    if int(getattr(c, 'instance_id', -1) or -1) == iid:
                        found = c
                        source_zone = zone
                        break
                if found is not None:
                    break
            if found is None:
                continue
            if not self._card_selectable_by_action(found):
                continue
            if str(getattr(found, 'def_id', '') or '') in ('factory:cogwheel', 'Cogwheel'):
                continue
            if exclude_def_id and str(getattr(found, 'def_id', '') or '') == exclude_def_id:
                continue
            if not ps.can_add_to_hand():
                continue
            source_zone.remove(found)
            found.mimic_discount = 0
            found.instance_flags.add('symbiosis')
            ps.add_to_hand(found)
            returned.append(found.name_cn)
        self._cogwheel_active[player_id] = False
        if hasattr(self, '_cogwheel_exclude_instance_ids'):
            self._cogwheel_exclude_instance_ids.pop(player_id, None)
        if returned:
            self.log_msg(f"{self.pn(player_id)}的齿轮效果：{len(returned)}张牌回到手中并获得共生")

    def _effect_tree_contains_action_status(self, value, depth: int = 0) -> bool:
        if depth > 30:
            return False
        action_statuses = {
            'sluggish', '迟缓', 'foresight', '预知', 'blind', '失明',
            'stunned', 'dizzy', 'skip_turn', '眩晕', 'attack_blocked', '禁攻',
            'attack_only', '仅攻击', 'magic_blocked', '魔力封锁',
        }
        if isinstance(value, dict):
            op = str(value.get('op') or value.get('type') or '')
            status = value.get('status') or value.get('name') or value.get('id')
            if op == 'electric_web_arm':
                return True
            if op in ('add_status', 'status_add_named', 'set_status', 'set_status_named') and str(status) in action_statuses:
                return True
            return any(self._effect_tree_contains_action_status(v, depth + 1) for v in value.values())
        if isinstance(value, list):
            return any(self._effect_tree_contains_action_status(v, depth + 1) for v in value)
        return False

    def _owner_turn_start_equipment_action_statuses(self, eq) -> bool:
        card_def = getattr(eq, 'card_def', None)
        if card_def is None:
            return False
        events = getattr(card_def, 'v2_events', None)
        if isinstance(events, dict) and self._effect_tree_contains_action_status(events.get('on_owner_turn_start')):
            return True
        for effect in getattr(card_def, 'effects', []) or []:
            if isinstance(effect, dict) and effect.get('type') == 'on_owner_turn_start':
                if self._effect_tree_contains_action_status(effect):
                    return True
        if self._has_script_entry(card_def, 'owner_turn_start'):
            return self._effect_tree_contains_action_status(self._get_script_effects(card_def, 'owner_turn_start'))
        return False

    def _run_owner_turn_start_action_status_equipment(self, player_id: int) -> set:
        handled = set()
        for owner_id, eq in self._iter_equipment_targeting_player(player_id):
            if not self._owner_turn_start_equipment_action_statuses(eq):
                continue
            key = self._equipment_turn_start_key(eq)
            if key in handled:
                continue
            eq.turns_equipped += 1
            handled.add(key)
            if self._has_card_event(eq.card_def, 'owner_turn_start'):
                self._run_card_event(owner_id, eq.card_instance, 'owner_turn_start', None,
                                     {'source_id': owner_id, 'target_id': player_id})
        return handled

    def _run_owner_turn_start_healing_equipment(self, player_id: int) -> set:
        if not (0 <= player_id < len(self.players)):
            return set()
        ps = self.players[player_id]
        handled = set()
        for owner_id, eq in self._iter_equipment_targeting_player(player_id):
            if not self._owner_turn_start_equipment_heals(eq):
                continue
            key = self._equipment_turn_start_key(eq)
            if key in handled:
                continue
            eq.turns_equipped += 1
            handled.add(key)
            if self._has_card_event(eq.card_def, 'owner_turn_start') and self._run_card_event(
                    owner_id, eq.card_instance, 'owner_turn_start', None,
                    {'source_id': owner_id, 'target_id': player_id}):
                continue
            if eq.def_id == 'Leaf':
                ps.heal(2)
                self.log_msg(f"{eq.card_def.name_cn}效果：{self.pn(player_id)}+2H")
            elif eq.def_id == 'Yucca':
                self._apply_yucca_turn_start_heal(player_id, eq.card_def.name_cn)
        return handled

    def _run_magic_yucca_pre_draw_equipment(self, player_id: int) -> set:
        if not (0 <= player_id < len(self.players)):
            return set()
        handled = set()
        for owner_id, eq in self._iter_equipment_targeting_player(player_id):
            if eq.def_id != 'MagicYucca':
                continue
            key = self._equipment_turn_start_key(eq)
            if key in handled:
                continue
            eq.turns_equipped += 1
            handled.add(key)
            effect_target_id = int(getattr(eq, 'effect_target', owner_id))
            if not (0 <= effect_target_id < len(self.players)):
                effect_target_id = player_id
            if self._has_card_event(eq.card_def, 'owner_turn_start'):
                self._run_card_event(owner_id, eq.card_instance, 'owner_turn_start', None,
                                     {'source_id': owner_id, 'target_id': effect_target_id})
        return handled

    def _apply_turn_start_effects(self, player_id: int):
        ps = self.players[player_id]
        self._sewers_clear_light_bulb_at_turn_start(player_id)
        opp_id = 1 - player_id
        opp = self.players[opp_id]
        self._save_turn_start_snapshot(player_id)
        self._antennae_reveal[player_id] = None
        self._reset_turn_damage_counters()
        self._run_v2_event_hooks('turn_start', {
            'source_player': player_id,
            'target_player': player_id,
            'vars': {'player_id': player_id},
            'current_action': {'player_id': player_id},
        })
        self._trigger_v2_status_events_for_player(player_id, 'on_turn_start', {'player_id': player_id})
        if self.game_over or getattr(self, 'pending_v2_ui', None):
            return
        self._apply_ocean_card_turn_start(player_id)
        self._apply_jungle_turn_start_statuses(player_id)
        self._run_zone_owner_turn_start_events(player_id)
        self._run_timed_effects_for_turn(player_id)
        untargetable_layers = max(0, int(getattr(ps, 'untargetable', 0) or 0))
        if untargetable_layers > 0:
            ps.untargetable = max(0, untargetable_layers - 1)
            if ps.untargetable <= 0:
                self.log_msg(f"{self.pn(player_id)}的不可选中效果结束")
        if ps.shovel_active:
            ps.shovel_active = False
        self._clear_turn_start_action_statuses(player_id)
        early_owner_turn_start_equipment = self._run_owner_turn_start_action_status_equipment(player_id)
        if self.game_over or getattr(self, 'pending_v2_ui', None):
            return
        early_owner_turn_start_equipment |= self._run_magic_yucca_pre_draw_equipment(player_id)
        if self.game_over or getattr(self, 'pending_v2_ui', None):
            return
        ocean_action_skip = int(ps.custom_vars.get('ocean_action_skip_turns', 0) or 0)
        skip_draw_recovery = ocean_action_skip > 0
        if skip_draw_recovery:
            ps.custom_vars['ocean_action_skip_turns'] = ocean_action_skip - 1
            self._skip_current_turn_after_start = True
        self._defer_turn_start_death_checks = True
        if self.round_num > 1 and not skip_draw_recovery:
            sluggish_reduction = ps.sluggish if not self._is_status_immune(player_id) else 0
            draw_count = max(0, DRAW_PER_TURN - sluggish_reduction)
            if self._queue_foresight_replace_choice(player_id, draw_count, 'turn_start_after_foresight'):
                self._pending_turn_start_early_owner_equipment = set(early_owner_turn_start_equipment)
                return
            drawn = self._draw_cards_with_v2_hooks(player_id, draw_count, 'turn_start')
            self.log_msg(f"{self.pn(player_id)}抽{len(drawn)}张牌")
            if sluggish_reduction > 0:
                self.log_msg(f"{self.pn(player_id)}的迟缓减少{min(sluggish_reduction, DRAW_PER_TURN)}张抽牌")
            self._clear_sluggish_after_draw(player_id)
        for owner_id, owner_state in enumerate(self.players):
            for eq in list(owner_state.equipment):
                if self._has_card_event(eq.card_def, 'any_turn_start'):
                    self._run_card_event(owner_id, eq.card_instance, 'any_turn_start', None,
                                         {'source_id': owner_id, 'target_id': player_id})
        for eq in list(opp.equipment):
            if self._has_card_event(eq.card_def, 'enemy_turn_start') and self._run_card_event(
                    opp_id, eq.card_instance, 'enemy_turn_start', None,
                    {'source_id': opp_id, 'target_id': player_id}):
                continue
            if eq.def_id == 'Corruption' and not eq.corruption_active:
                eq.corruption_active = True
                self.log_msg(f"{self.pn(opp_id)}的腐化效果激活")
        early_owner_turn_start_equipment |= self._run_owner_turn_start_healing_equipment(player_id)
        if self.game_over or getattr(self, 'pending_v2_ui', None):
            self._defer_turn_start_death_checks = False
            return
        self._hel_apply_blazing_fire_turn_start(player_id)
        if ps.poison > 0:
            if not self._is_status_immune(player_id):
                dmg = ps.poison
                self._deal_direct_damage(player_id, dmg, '中毒', damage_type=DAMAGE_TYPE_MAGIC, damage_tag=DAMAGE_TAG_POISON)
            self._decay_poison_after_turn_start(player_id)
            self._apply_toxic_poison_after_poison_settlement(player_id)
        if ps.fire > 0 and not self._is_status_immune(player_id):
            self._deal_direct_damage(player_id, ps.fire, '灼烧', damage_type=DAMAGE_TYPE_MAGIC, damage_tag=DAMAGE_TAG_FIRE)
        if self.round_num > 1 and not skip_draw_recovery:
            elixir_recovery = ELIXIR_RECOVERY
            for eq in list(opp.equipment):
                if eq.card_def.effects:
                    for effect in eq.card_def.effects:
                        if isinstance(effect, dict) and effect.get('type') == 'aura_enemy_elixir_recovery':
                            elixir_recovery += self._eval_int(opp_id, effect.get('params', {}).get('amount', 0), eq.card_instance)
                    continue
                if eq.def_id == 'Pincer':
                    ps.overload += 1
                    self.log_msg(f"{self.pn(player_id)}被螫针施加1层超载")
            if self.opening_event_picks[player_id] == 6:
                elixir_recovery += 1
            ps.gain_elixir(elixir_recovery)
            self.log_msg(f"{self.pn(player_id)}回复{elixir_recovery}E")
        # Overload: deduct E at turn start, then clear
        if ps.overload > 0:
            if not self._is_status_immune(player_id):
                deduct = min(ps.overload, ps.elixir)
                ps.elixir -= deduct
                self.log_msg(f"{self.pn(player_id)}的超载扣除{deduct}E")
            ps.overload = 0
        for owner_state in self.players:
            for eq in getattr(owner_state, 'equipment', []):
                eq.uses_this_turn = 0
        for owner_id, eq in self._iter_equipment_targeting_player(player_id):
            eq_key = self._equipment_turn_start_key(eq)
            if eq_key not in early_owner_turn_start_equipment:
                eq.turns_equipped += 1
            else:
                continue
            effect_target_id = int(getattr(eq, 'effect_target', owner_id))
            if not (0 <= effect_target_id < len(self.players)):
                effect_target_id = player_id
            if self._has_card_event(eq.card_def, 'target_turn_start') and self._run_card_event(
                    owner_id, eq.card_instance, 'target_turn_start', None,
                    {'source_id': owner_id, 'target_id': effect_target_id}):
                continue
            if self._has_card_event(eq.card_def, 'owner_turn_start') and self._run_card_event(
                    owner_id, eq.card_instance, 'owner_turn_start', None,
                    {'source_id': owner_id, 'target_id': effect_target_id}):
                continue
            if eq.def_id == 'Leaf':
                ps.heal(2)
                self.log_msg(f"{self.pn(player_id)}的叶子效果：+2H")
            elif eq.def_id == 'Yucca':
                self._apply_yucca_turn_start_heal(player_id)
            elif eq.def_id == 'MagicLeaf':
                ps.gain_magic(1)
                self.log_msg(f"{self.pn(player_id)}的魔法叶效果：+1M")
            elif eq.def_id == 'Powder':
                ps.gain_elixir(2)
                self.log_msg(f"{self.pn(player_id)}的粉末效果：+2E")
            elif eq.def_id == 'GoldenLeaf':
                ps.draw_cards(1)
                self.log_msg(f"{self.pn(player_id)}的黄金叶效果：多抽1张牌")
        if not self.game_over:
            self._apply_jungle_turn_start_regen(player_id)
        self._defer_turn_start_death_checks = False
        if ps.health <= 0:
            self._check_yggdrasil(player_id)
            self._check_game_over()

    def _queue_foresight_replace_choice(self, player_id: int, draw_count: int, resume_handler: str) -> bool:
        ps = self.players[player_id]
        if ps.foresight <= 0:
            return False
        if self._is_status_immune(player_id) or not ps.deck or not ps.hand:
            ps.foresight = 0
            self.log_msg(f"{self.pn(player_id)}的预知效果清除")
            return False
        select_limit = min(ps.foresight, len(ps.hand), len(ps.deck))
        if select_limit <= 0:
            ps.foresight = 0
            self.log_msg(f"{self.pn(player_id)}的预知效果清除")
            return False
        self._pending_foresight = {
            'player_id': player_id,
            'draw_count': draw_count,
            'select_limit': select_limit,
            'resume_handler': resume_handler,
        }
        self.pending_choice = {
            'player_id': player_id,
            'choice_type': 'foresight_replace',
            'card': None,
            'choice_params': {'max_count': select_limit},
            'hand_cards': [c.to_dict() for c in ps.hand],
            'max_replace': select_limit,
            'message': f'预知：选择最多{select_limit}张手牌丢弃，然后抽对应张牌',
        }
        return True

    def _resume_turn_start_after_foresight(self, player_id: int, foresight_result: Optional[dict] = None):
        ps = self.players[player_id]
        opp_id = 1 - player_id
        opp = self.players[opp_id]
        early_owner_turn_start_equipment = getattr(self, '_pending_turn_start_early_owner_equipment', set()) or set()
        self._pending_turn_start_early_owner_equipment = set()
        self._defer_turn_start_death_checks = True
        for owner_id, owner_state in enumerate(self.players):
            for eq in list(owner_state.equipment):
                if self._has_card_event(eq.card_def, 'any_turn_start'):
                    self._run_card_event(owner_id, eq.card_instance, 'any_turn_start', None,
                                         {'source_id': owner_id, 'target_id': player_id})
        for eq in list(opp.equipment):
            if self._has_card_event(eq.card_def, 'enemy_turn_start') and self._run_card_event(
                    opp_id, eq.card_instance, 'enemy_turn_start', None,
                    {'source_id': opp_id, 'target_id': player_id}):
                continue
            if eq.def_id == 'Corruption' and not eq.corruption_active:
                eq.corruption_active = True
                self.log_msg(f"{self.pn(opp_id)}的腐化效果激活")
        early_owner_turn_start_equipment |= self._run_owner_turn_start_healing_equipment(player_id)
        if self.game_over or getattr(self, 'pending_v2_ui', None):
            self._defer_turn_start_death_checks = False
            return
        self._hel_apply_blazing_fire_turn_start(player_id)
        if self.round_num > 1:
            draw_count = max(0, int((foresight_result or {}).get('draw_count', 0) or 0))
            drawn = self._draw_cards_with_v2_hooks(player_id, draw_count, 'turn_start')
            self.log_msg(f"{self.pn(player_id)}抽{len(drawn)}张牌")
            if ps.sluggish > 0 and not self._is_status_immune(player_id):
                self.log_msg(f"{self.pn(player_id)}的迟缓减少{min(ps.sluggish, DRAW_PER_TURN)}张抽牌")
            self._clear_sluggish_after_draw(player_id)
        if ps.poison > 0:
            if not self._is_status_immune(player_id):
                dmg = ps.poison
                self._deal_direct_damage(player_id, dmg, '中毒', damage_type=DAMAGE_TYPE_MAGIC, damage_tag=DAMAGE_TAG_POISON)
            self._decay_poison_after_turn_start(player_id)
            self._apply_toxic_poison_after_poison_settlement(player_id)
        if ps.fire > 0 and not self._is_status_immune(player_id):
            self._deal_direct_damage(player_id, ps.fire, '灼烧', damage_type=DAMAGE_TYPE_MAGIC, damage_tag=DAMAGE_TAG_FIRE)
        if self.round_num > 1:
            elixir_recovery = ELIXIR_RECOVERY
            for eq in list(opp.equipment):
                if eq.card_def.effects:
                    for effect in eq.card_def.effects:
                        if isinstance(effect, dict) and effect.get('type') == 'aura_enemy_elixir_recovery':
                            elixir_recovery += self._eval_int(opp_id, effect.get('params', {}).get('amount', 0), eq.card_instance)
                    continue
                if eq.def_id == 'Pincer':
                    ps.overload += 1
                    self.log_msg(f"{self.pn(player_id)}被螫针施加1层超载")
            if self.opening_event_picks[player_id] == 6:
                elixir_recovery += 1
            ps.gain_elixir(elixir_recovery)
            self.log_msg(f"{self.pn(player_id)}回复{elixir_recovery}E")
        if ps.overload > 0:
            if not self._is_status_immune(player_id):
                deduct = min(ps.overload, ps.elixir)
                ps.elixir -= deduct
                self.log_msg(f"{self.pn(player_id)}的超载扣除{deduct}E")
            ps.overload = 0
        for owner_state in self.players:
            for eq in getattr(owner_state, 'equipment', []):
                eq.uses_this_turn = 0
        for owner_id, eq in self._iter_equipment_targeting_player(player_id):
            eq_key = self._equipment_turn_start_key(eq)
            if eq_key not in early_owner_turn_start_equipment:
                eq.turns_equipped += 1
            else:
                continue
            effect_target_id = int(getattr(eq, 'effect_target', owner_id))
            if not (0 <= effect_target_id < len(self.players)):
                effect_target_id = player_id
            if self._has_card_event(eq.card_def, 'owner_turn_start') and self._run_card_event(
                    owner_id, eq.card_instance, 'owner_turn_start', None,
                    {'source_id': owner_id, 'target_id': effect_target_id}):
                continue
            if eq.def_id == 'Leaf':
                ps.heal(2)
                self.log_msg(f"{self.pn(player_id)}的叶子效果：+2H")
            elif eq.def_id == 'Yucca':
                self._apply_yucca_turn_start_heal(player_id)
            elif eq.def_id == 'MagicLeaf':
                ps.gain_magic(1)
                self.log_msg(f"{self.pn(player_id)}的魔法叶效果：+1M")
            elif eq.def_id == 'Powder':
                ps.gain_elixir(2)
                self.log_msg(f"{self.pn(player_id)}的粉末效果：+2E")
            elif eq.def_id == 'GoldenLeaf':
                ps.draw_cards(1)
                self.log_msg(f"{self.pn(player_id)}的黄金叶效果：多抽1张牌")
        if not self.game_over:
            self._apply_jungle_turn_start_regen(player_id)
        self._defer_turn_start_death_checks = False
        if ps.health <= 0:
            self._check_yggdrasil(player_id)
            self._check_game_over()
        if self.game_over:
            return
        if getattr(self, '_skip_current_turn_after_start', False):
            self._skip_current_turn_after_start = False
            self.log_msg(f"{self.pn(player_id)}被魔法珊瑚影响，跳过本回合行动")
            self._end_player_turn(player_id)
            return
        if ps.forced_skip_turn > 0:
            ps.forced_skip_turn -= 1
            self.log_msg(f"{self.pn(player_id)}被跳过本回合")
            self._end_player_turn(player_id)
            return
        if ps.skip_turn > 0 and self._is_status_immune(player_id):
            ps.skip_turn = max(0, int(ps.skip_turn) - 1)
        elif ps.skip_turn > 0:
            ps.skip_turn -= 1
            self.log_msg(f"{self.pn(player_id)}被眩晕，跳过本回合！")
            self._end_player_turn(player_id)
            return
        if ps.health <= 0:
            self._check_yggdrasil(player_id)
            if ps.health <= 0:
                self._check_game_over()
                return
        self._enter_player_action_phase(player_id)

    def deal_attack_damage(self, target_id: int, amount: int, hits: int = 1,
                           is_battery: bool = False, is_precision: bool = False,
                           attacker_id: int = -1,
                           source_card: Optional[CardInstance] = None) -> int:
        if not isinstance(target_id, int):
            try:
                target_id = int(target_id)
            except Exception:
                return 0
        if not (0 <= target_id < len(self.players)):
            return 0
        hits = clamp_damage_hits(hits)
        if source_card is not None:
            self._clamp_card_layers(source_card)
        ps = self.players[target_id]
        if ps.health <= 0:
            return 0
        if attacker_id < 0:
            attacker_id = 1 - target_id
        if ps.untargetable and not is_battery and not self._is_status_immune(target_id):
            self.log_msg(f"{self.pn(target_id)}无法被攻击选中")
            return 0
        total_dealt = 0
        if not isinstance(getattr(self, '_last_positive_damage_hits', None), list) or len(self._last_positive_damage_hits) != len(self.players):
            self._last_positive_damage_hits = [0] * len(self.players)
        self._last_positive_damage_hits[target_id] = 0
        immune = self._is_status_immune(target_id)
        for _ in range(hits):
            precision_dodged = False
            plank_blocks_attack = False
            if ps.dodge > 0 and not immune:
                ps.dodge -= 1
                if is_precision:
                    precision_dodged = True
                    if not getattr(self, '_suppress_next_precision_dodge_log', False):
                        self.log_msg(f"{self.pn(target_id)}的闪避被精准消耗")
                else:
                    self.log_msg(f"{self.pn(target_id)}闪避了攻击")
                    continue
            if ps.invincible and not immune:
                self.log_msg(f"{self.pn(target_id)}无敌，免疫伤害")
                continue
            if amount <= 0 and hits <= 1:
                break
            if source_card is not None and self._has_equipment(target_id, 'Plank', 'jungle:plank'):
                try:
                    if int(getattr(source_card, 'cost_e', 0) or 0) <= 1:
                        plank_blocks_attack = True
                except Exception:
                    pass
            dmg = amount
            power = 0
            if source_card is not None:
                try:
                    power = max(0, int(getattr(source_card, 'power_value', 0) or 0))
                except Exception:
                    power = 0
            if power > 0:
                dmg += int(math.ceil(power / max(1, int(hits or 1))))
            if 0 <= attacker_id < len(self.players):
                multiplier = float(getattr(self.players[attacker_id], 'damage_multiplier', 1.0) or 1.0)
                if multiplier != 1.0:
                    dmg = int(math.ceil(dmg * multiplier))
                    self.players[attacker_id].damage_multiplier = 1.0
                try:
                    puppeteer_multiplier = float((getattr(self.players[attacker_id], 'custom_vars', {}) or {}).get('void_puppeteer_damage_multiplier', 1.0) or 1.0)
                except Exception:
                    puppeteer_multiplier = 1.0
                if puppeteer_multiplier != 1.0:
                    dmg = int(math.ceil(dmg * puppeteer_multiplier))
            if self.halve_next_attack:
                dmg = math.ceil(dmg / 2)
            elif precision_dodged:
                dmg = math.ceil(dmg / 2)
            dmg = self._apply_corruption_multiplier_to_damage(dmg, log=False)
            dmg = self._apply_damage_dealt_equipment_multiplier(dmg, attacker_id)
            if plank_blocks_attack:
                dmg = 0
            nazar_stacks = 0 if immune else self._nazar_status_value(target_id)
            if dmg > 0 and nazar_stacks > 0:
                original_dmg = dmg
                dmg = max(1, dmg - 9)
                if original_dmg >= 10:
                    self._set_nazar_status_value(target_id, nazar_stacks - 1)
            damage_context = self._v2_damage_context(
                target_id,
                dmg,
                attacker_id,
                damage_kind='attack',
                damage_tag=DAMAGE_TAG_PHYSICAL,
                damage_type=DAMAGE_TYPE_PHYSICAL,
                is_battery=is_battery,
                is_precision=is_precision,
            )
            dmg = self._run_v2_damage_modifiers(damage_context, dmg)
            if getattr(self, 'pending_v2_ui', None):
                break
            # Weakness belongs to the attacker: it reduces physical damage they deal to others.
            attacker_state = self.players[attacker_id] if 0 <= attacker_id < len(self.players) else None
            attacker_immune = self._is_status_immune(attacker_id) if attacker_state is not None else False
            if dmg > 0 and attacker_state is not None and attacker_state.weakness > 0 and not attacker_immune:
                reduction = min(0.6, 0.2 * attacker_state.weakness)
                dmg = max(1, int(dmg * (1.0 - reduction)))
            dmg, _hel_crit = self._hel_apply_lucky_crit_to_damage(attacker_id, dmg, source_card)
            if immune:
                root_armor = 0
                fragile = 0
            else:
                root_armor = self._custom_status_value(target_id, 'jungle:root', 'jungle:root_status', 'root_status')
                fragile = self._custom_status_value(target_id, 'jungle:fragile', 'fragile')
            effective_armor = int(ps.armor) + root_armor - fragile
            dmg = max(0, dmg - effective_armor)
            if ps.sponge_active and dmg > 0 and not immune:
                converted = min(10, dmg // 2)
                ps.poison += converted
                dmg = 0
            dmg = self._apply_universal_damage_shields(target_id, dmg, attacker_id, '攻击', DAMAGE_TYPE_PHYSICAL)
            if (
                dmg > 0
                and getattr(self, '_prediction_capture_target_id', None) == target_id
                and int(getattr(self, '_prediction_first_attack_damage', 0) or 0) <= 0
            ):
                self._prediction_first_attack_damage = int(dmg)
            ps.health -= dmg
            self._note_achievement_health(target_id)
            total_dealt += dmg
            if dmg > 0:
                self._last_positive_damage_hits[target_id] += 1
            self._record_damage(target_id, dmg, attacker_id)
            self.log_msg(f"{self.pn(target_id)}受到{dmg}点伤害（H={ps.health}）")
            self._run_v2_after_damage_hooks(damage_context, dmg)
            if dmg > 0:
                self._apply_ocean_blood_debt_after_physical_damage(target_id, attacker_id)
            if dmg > 0 and not immune:
                root_layers = self._custom_status_value(target_id, 'jungle:root', 'jungle:root_status', 'root_status')
                if root_layers > 0:
                    self._set_custom_status_alias_group(target_id, 'jungle:root_status', ('jungle:root', 'jungle:root_status', 'root_status'), root_layers - 1)
                    self._consume_jungle_root_layer_from_equipment(target_id)
            if dmg > 0 and ps.toxic > 0 and not immune:
                ps.poison += ps.toxic
            self._game_over_defer_depth += 1
            try:
                self._check_yggdrasil(target_id)
                if dmg > 0 and not is_battery:
                    for equipment_owner_id, eq in list(self._iter_equipment_targeting_player(target_id)):
                        if self._card_is(eq.card_instance, 'Battery', 'vanilla:battery'):
                            dealt = self._deal_direct_damage(
                                attacker_id, 3, '电池电击', target_id,
                                damage_type=DAMAGE_TYPE_MAGIC,
                                damage_tag=DAMAGE_TAG_BATTERY,
                            )
                            if dealt > 0:
                                self.log_msg(f"{self.pn(target_id)}的电池效果：对{self.pn(attacker_id)}造成3电伤")
                            else:
                                self.log_msg(f"{self.pn(target_id)}的电池触发，但{self.pn(attacker_id)}未受到电伤")
                        elif self._card_is(eq.card_instance, 'MagicBattery', 'vanilla:magicbattery'):
                            owner_state = self.players[equipment_owner_id]
                            if owner_state.magic_battery_m_this_turn < 3:
                                owner_state.gain_magic(1)
                                owner_state.magic_battery_m_this_turn += 1
                                owner_state.custom_vars['魔法电池本回合回魔'] = owner_state.magic_battery_m_this_turn
                                self.log_msg(f"{self.pn(equipment_owner_id)}的魔法电池效果：+1M")
                        elif self._has_card_event(eq.card_def, 'damage_taken') and self._run_card_event(
                                target_id, eq.card_instance, 'damage_taken', None,
                                {
                                    'source_id': attacker_id,
                                    'target_id': target_id,
                                    'damage': dmg,
                                    'selected_equipment_instance_id': eq.card_instance.instance_id,
                                    'selected_equipment_owner_id': equipment_owner_id,
                                }):
                            continue
            finally:
                self._game_over_defer_depth -= 1
            self._check_game_over()
            if ps.health <= 0:
                break
        return total_dealt

    def _execute_card_effect(self, player_id: int, card: CardInstance, choice: Optional[dict] = None) -> dict:
        ps = self.players[player_id]
        result = {'success': True, 'card': card.to_dict()}
        if 'ocean_nitro_negated' in getattr(card, 'instance_flags', set()):
            card.instance_flags.discard('ocean_nitro_negated')
            self._log_card_play(player_id, card)
            reset_card_after_play(card)
            if 'exile' in card.flags:
                self._put_card_in_exile(ps.player_id, card)
            else:
                self._discard_card(ps, card)
            self._dispatch_card_event('card_used', player_id, card, target_id=player_id, choice=choice)
            self._run_v2_play_hook('after_play_card', player_id, card, choice)
            result['card'] = card.to_dict()
            result['countered'] = True
            return result
        if card.card_type == 'thorn' and (card.fission_level > 1 or card.fusion_level > 1):
            self.log_msg(f"[特效] {card.name_cn} 聚变={card.fusion_level} 裂变={card.fission_level}")
        if self.negated_card and card.card_type == 'bloom':
            self.negated_card = False
            self._log_card_play(player_id, card)
            reset_card_after_play(card)
            if 'exile' in card.flags:
                self._put_card_in_exile(ps.player_id, card)
            else:
                self._discard_card(ps, card)
            self._dispatch_card_event('card_used', player_id, card, target_id=player_id, choice=choice)
            self._run_v2_play_hook('after_play_card', player_id, card, choice)
            result['countered'] = True
            result['negated'] = True
            return result
        # Magic Nazar: check for magic_nazar status on opponent
        if card.card_type == 'bloom':
            for opp_id in self._magic_nazar_counter_player_ids(player_id, card, choice):
                if not (0 <= opp_id < len(self.players)):
                    continue
                opp = self.players[opp_id]
                magic_nazar_stacks = 0 if self._is_status_immune(opp_id) else int(opp.custom_statuses.get('magic_nazar', 0) or 0)
                if magic_nazar_stacks <= 0:
                    continue
                card_cost_e = int(getattr(card, '_paid_e_this_play', getattr(card, 'cost_e', 0)) or 0)
                if card_cost_e <= 1:
                    self.log_msg(f"{self.pn(player_id)}的{card.name_cn}被魔法邪眼反制，失效！")
                    opp.custom_statuses['magic_nazar'] = magic_nazar_stacks - 1
                    if opp.custom_statuses['magic_nazar'] <= 0:
                        opp.custom_statuses.pop('magic_nazar', None)
                    self._log_card_play(player_id, card)
                    reset_card_after_play(card)
                    if 'exile' in card.flags:
                        self._put_card_in_exile(ps.player_id, card)
                    else:
                        self._discard_card(ps, card)
                    self._dispatch_card_event('card_used', player_id, card, target_id=player_id, choice=choice)
                    self._run_v2_play_hook('after_play_card', player_id, card, choice)
                    return result
                break
        self.negated_card = False
        needs_choice = self._card_needs_choice(card)
        if needs_choice and not self._choice_satisfies_request(card, choice):
            queued = self._queue_card_choice(player_id, card, choice, already_paid=True)
            if queued:
                return queued
        if card.def_id == 'Mimic' and isinstance(choice, dict) and choice.get('target_instance_id') is not None:
            target = ps.find_hand_card(choice.get('target_instance_id'))
            if target is not None and not self._card_selectable_by_action(target):
                self._undo_pending_choice_play_side_effects(player_id, card)
                return {'success': False, 'error': '目标无效'}
            if target is not None and not self._can_pay_mimic_special_cost(player_id, target):
                self._undo_pending_choice_play_side_effects(player_id, card)
                return {'success': False, 'error': '\u80fd\u91cf\u4e0d\u8db3'}
        play_log_marker = len(self.log)
        if self._uses_atomic_play_effects(card) and not self._is_chilli_card(card):
            self._log_card_play(player_id, card)
        if card.card_type == 'thorn':
            self._clamp_card_layers(card)
            fission_level = clamp_card_layer(getattr(card, 'fission_level', 1))
            for hit_idx in range(fission_level):
                if self.game_over:
                    break
                card.fission_hit = hit_idx
                self._apply_card_effect(player_id, card, choice)
            card.fission_hit = 0
        else:
            self._apply_card_effect(player_id, card, choice)
        # Check if an effect (e.g. request_reorder_deck/assembler_effect) set pending_choice during execution
        # Must check BEFORE card disposition (discard/equip) to allow the choice to complete first
        if self.pending_choice is not None:
            if getattr(self, '_auto_resolve_choices_for', None) == player_id:
                auto_pending = self.pending_choice
                auto_choice = self._default_choice_for_pending(auto_pending)
                if isinstance(auto_choice, dict):
                    auto_result = self.resolve_choice(player_id, auto_choice)
                    if self.pending_choice is None:
                        return auto_result if isinstance(auto_result, dict) else {'success': True}
            pending = self.pending_choice
            if pending.get('choice_type') == 'magic_salt_reflect':
                pass
            else:
                keep_paid_choice = pending.get('choice_type') in ('choose_ocean_sapphire',)
                if keep_paid_choice:
                    pending['play_log_marker'] = play_log_marker
                else:
                    self._undo_pending_choice_play_side_effects(player_id, card, play_log_marker=play_log_marker)
                return {
                    'success': True,
                    'needs_choice': True,
                    'choice_type': pending.get('choice_type', ''),
                    'choice_params': pending.get('choice_params', {}),
                    'card': card.to_dict(),
                    'hand_cards': pending.get('hand_cards', []),
                    'deck_cards': pending.get('deck_cards', []),
                    'discard_cards': pending.get('discard_cards', []),
                    'target_player_id': pending.get('target_player_id'),
                    'max_replace': pending.get('max_replace'),
                    'message': pending.get('message', ''),
                }
        # Fracture: take damage when playing a card
        if ps.fracture > 0 and not self._is_status_immune(player_id):
            frac_dmg = ps.fracture
            self._deal_direct_damage(player_id, frac_dmg, '破损', player_id,
                                     damage_type=DAMAGE_TYPE_MAGIC, damage_tag=DAMAGE_TAG_DIRECT)
        # Bleed: take damage when playing attack card
        if ps.bleed > 0 and card.card_type == 'thorn' and not self._is_status_immune(player_id):
            bleed_dmg = ps.bleed
            self._deal_direct_damage(player_id, bleed_dmg, '流血', player_id,
                                     damage_type=DAMAGE_TYPE_MAGIC, damage_tag=DAMAGE_TAG_DIRECT)
        placed_as_equipment = bool(getattr(card, '_placed_as_equipment', False))
        script_controls_play = self._card_has_script(card.card_def)
        explicit_equip_owner = hasattr(card, '_placed_as_equipment_owner')
        equip_owner_id = int(getattr(card, '_placed_as_equipment_owner', player_id))
        if equip_owner_id < 0 or equip_owner_id >= len(self.players):
            equip_owner_id = player_id
        equip_owner = self.players[equip_owner_id]
        reset_card_after_play(card)
        if (card.card_type == 'root' and not script_controls_play) or placed_as_equipment:
            eq = self._find_equipment_for_card(equip_owner_id, card)
            if eq is None:
                eq = EquipmentInstance(card, equip_owner_id)
                if isinstance(choice, dict):
                    for key in ('target_player', 'target_player_id', 'target_id'):
                        if key in choice:
                            try:
                                selected_effect_target = int(choice.get(key))
                            except Exception:
                                selected_effect_target = -1
                            if 0 <= selected_effect_target < len(self.players):
                                eq.effect_target = selected_effect_target
                                break
                if self._equipment_is(eq, 'Disc', 'vanilla:disc') and not card.card_def.effects:
                    effect_target = int(getattr(eq, 'effect_target', getattr(eq, 'owner', equip_owner_id)))
                    if not (0 <= effect_target < len(self.players)):
                        effect_target = equip_owner_id
                    self.players[effect_target].armor += 2
                    self._note_achievement_status_peak(effect_target)
                equip_owner.equipment.append(eq)
                self._note_achievement_equipment_count(equip_owner_id)
                self._refresh_hand_limit_bonuses()
                self.log_msg(f"{self.pn(equip_owner_id)}装备了{card.name_cn}")
            if hasattr(card, '_placed_as_equipment'):
                delattr(card, '_placed_as_equipment')
            if hasattr(card, '_placed_as_equipment_owner'):
                delattr(card, '_placed_as_equipment_owner')
        elif 'return_to_hand' in card.instance_flags:
            card.instance_flags.discard('return_to_hand')
            ps.add_to_hand(card)
            self.log_msg(f"{self.pn(player_id)}的{card.name_cn}立即回到手中")
        elif 'rebound' in card.flags:
            ps.add_to_hand(card)
            self.log_msg(f"{self.pn(player_id)}的{card.name_cn}因回转回到手中")
        elif 'floating' in card.flags:
            owner_id, zone_name, _ = self._find_card_location(card)
            if owner_id is None or zone_name is None:
                insert_at = random.randint(0, len(ps.deck)) if ps.deck else 0
                ps.deck.insert(insert_at, card)
                self.log_msg(f"{self.pn(player_id)}的{card.name_cn}因漂浮洗入抽牌堆")
        elif 'exile' in card.flags:
            owner_id, zone_name, _ = self._find_card_location(card)
            if owner_id is None or zone_name is None:
                self._put_card_in_exile(ps.player_id, card)
        else:
            owner_id, zone_name, _ = self._find_card_location(card)
            if owner_id is None or zone_name is None:
                self._discard_card(ps, card)
        target_id = player_id
        if isinstance(choice, dict):
            for key in ('target_player', 'target_player_id', 'target_id'):
                if key in choice:
                    try:
                        target_id = int(choice.get(key))
                        break
                    except Exception:
                        target_id = player_id
        self._dispatch_card_event('card_used', player_id, card, target_id=target_id, choice=choice)
        self._run_v2_play_hook('after_play_card', player_id, card, choice)
        self._check_game_over()
        if getattr(self, 'pending_v2_ui', None):
            result['needs_v2_ui'] = True
        try:
            ps.custom_vars['void_last_played_def_id'] = getattr(card, 'def_id', '')
            ps.custom_vars.pop('void_current_previous_def_id', None)
        except Exception:
            pass
        return result

    def _atomic_place_as_equip(self, player_id, card, params, log, choice, context):
        source = self.players[player_id]
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if target_card is None:
            return
        owner_expr = params.get('owner', params.get('equip_owner'))
        owner_id = self._resolve_target(player_id, owner_expr) if owner_expr is not None else player_id
        if owner_id < 0 or owner_id >= len(self.players):
            owner_id = player_id
        owner = self.players[owner_id]
        if target_card in source.hand:
            source.hand.remove(target_card)
        else:
            self._remove_card_from_current_zone(target_card)
        if self._find_equipment_for_card(owner_id, target_card) is None:
            target_card.durability = target_card.card_def.durability if getattr(target_card.card_def, 'durability', 0) > 0 else 3
            eq = EquipmentInstance(target_card, owner_id)
            if 'effect_target' in params:
                effect_target = self._resolve_target(player_id, params.get('effect_target'))
                if not (0 <= effect_target < len(self.players)) and isinstance(context, dict):
                    try:
                        effect_target = int(context.get('target_id', -1))
                    except Exception:
                        effect_target = -1
                if 0 <= effect_target < len(self.players):
                    eq.effect_target = effect_target
            else:
                selected_target = self._selected_choice_target(-1)
                if not (0 <= selected_target < len(self.players)) and isinstance(context, dict):
                    try:
                        selected_target = int(context.get('target_id', -1))
                    except Exception:
                        selected_target = -1
                if 0 <= selected_target < len(self.players):
                    eq.effect_target = selected_target
            owner.equipment.append(eq)
            self._note_achievement_equipment_count(owner_id)
            self._refresh_hand_limit_bonuses()
            self.log_msg(log or f"{self.pn(owner_id)}装备了{target_card.name_cn}")
        if target_card is card:
            card._placed_as_equipment = True
            card._placed_as_equipment_owner = owner_id

    def _atomic_add_equipment_to_zone(self, player_id, card, params, log, choice, context):
        card_id = self._resolve_card_id_ref(player_id, params.get('card', 'Leaf'), card)
        card_def = CARD_DEFS.get(card_id)
        owner_ids = self._resolve_targets(player_id, params.get('target', params.get('owner', 'self')))
        if not owner_ids:
            owner_ids = [player_id]
        if card_def is None:
            error_def = CARD_DEFS.get(ERROR_CARD_ID)
            if not error_def:
                return
            for owner_id in owner_ids:
                if owner_id < 0 or owner_id >= len(self.players):
                    continue
                new_card = CardInstance(def_id=ERROR_CARD_ID)
                self.players[owner_id].add_to_hand(new_card)
                self._remember_created_card(new_card, context if isinstance(context, dict) else None)
            return
        for owner_id in owner_ids:
            if owner_id < 0 or owner_id >= len(self.players):
                continue
            new_card = CardInstance(def_id=card_def.id)
            self._apply_setup_modifiers_to_card(owner_id, new_card)
            new_card.durability = card_def.durability if getattr(card_def, 'durability', 0) > 0 else 3
            eq = EquipmentInstance(new_card, owner_id)
            if 'effect_target' in params:
                effect_target = self._resolve_target(player_id, params.get('effect_target'))
                if 0 <= effect_target < len(self.players):
                    eq.effect_target = effect_target
            else:
                eq.effect_target = owner_id
            self.players[owner_id].equipment.append(eq)
            self._note_achievement_equipment_count(owner_id)
            self._refresh_hand_limit_bonuses()
            self._remember_created_card(new_card, context if isinstance(context, dict) else None)
            self.log_msg(log or f"{self.pn(owner_id)}获得装备{card_def.name_cn}")

    def _atomic_request_target(self, player_id, card, params, log, choice, context):
        return None

    def _atomic_request_card(self, player_id, card, params, log, choice, context):
        return None

    def _atomic_request_confirm(self, player_id, card, params, log, choice, context):
        return None

    def _atomic_response_declare(self, player_id, card, params, log, choice, context):
        return None

    def _atomic_trigger_manual(self, player_id, card, params, log, choice, context):
        return None

    def _atomic_aura_enemy_elixir_recovery(self, player_id, card, params, log, choice, context):
        return None

    def _atomic_destroy_self_equipment(self, player_id, card, params, log, choice, context):
        eq = self._find_equipment_for_card(player_id, card)
        if eq is not None:
            self._destroy_equipment(player_id, eq, check_protection=False)

    def _atomic_deal_damage(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if not self._valid_player_id(target_id):
            return
        amount = self._eval_int(player_id, params.get('amount', 6), card, 6)
        hits = self._card_total_hits(card, self._eval_int(player_id, params.get('hits', 1), card, 1))
        is_precision = bool(params.get('is_precision', False)) or 'precision' in self._effective_card_flags(card)
        amount = self._modified_attack_damage(amount, card)
        self._incoming_damage_hint[target_id] = int(amount)
        try:
            dealt = self.deal_attack_damage(target_id, amount, hits, is_precision=is_precision, attacker_id=player_id, source_card=card)
        except TypeError:
            dealt = self.deal_attack_damage(target_id, amount, hits, is_precision=is_precision)
        self._last_damage_value[target_id] = int(dealt)
        on_hit = params.get('on_hit')
        if dealt > 0 and isinstance(on_hit, list):
            hit_count = 1
            try:
                hit_count = max(1, int((getattr(self, '_last_positive_damage_hits', []) or [])[target_id] or 0))
            except Exception:
                hit_count = 1
            for hit_index in range(hit_count):
                child_context = dict(context or {})
                child_context.update({
                    'event': 'on_hit',
                    'source_id': player_id,
                    'target_id': target_id,
                    'damage': int(dealt),
                    'hit_index': hit_index,
                })
                self._run_effect_list(player_id, card, on_hit, choice, child_context)
        if log:
            self.log_msg(log)

    def _atomic_direct_damage(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if not self._valid_player_id(target_id):
            return
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        source = str(params.get('source', card.name_cn if card else '效果'))
        self._deal_direct_damage(
            target_id,
            amount,
            source,
            player_id,
            damage_type=params.get('damage_type'),
            damage_tag=params.get('damage_tag'),
        )

    def _atomic_lifesteal_damage(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if not self._valid_player_id(target_id):
            return
        amount = self._eval_int(player_id, params.get('amount', 8), card, 8)
        amount = self._modified_attack_damage(amount, card)
        heal = self._eval_int(player_id, params.get('heal', 4), card, 4)
        heal_ratio = params.get('heal_percent', params.get('ratio', None))
        try:
            is_precision = 'precision' in self._effective_card_flags(card)
            dealt = self.deal_attack_damage(target_id, amount, is_precision=is_precision, attacker_id=player_id, source_card=card)
        except TypeError:
            dealt = self.deal_attack_damage(target_id, amount)
        self._last_damage_value[target_id] = int(dealt)
        if dealt > 0:
            if heal_ratio is not None:
                try:
                    heal = max(0, int(math.floor(int(dealt or 0) * float(heal_ratio or 0))))
                except Exception:
                    heal = 0
            self.players[player_id].heal(heal)
            self.log_msg(log or f"{self.pn(player_id)}回复{heal}H")

    def _atomic_triangle_damage(self, player_id, card, params, log, choice, context):
        base = self._eval_int(player_id, params.get('base', 6), card, 6)
        per_stack = self._eval_int(player_id, params.get('per_stack', 3), card, 3)
        stack_name = str(params.get('stack_name', '三角形层数'))
        immune = self._is_suppressed_status_var(player_id, stack_name)
        current_stack = 0 if immune else int(self.players[player_id].custom_vars.get(stack_name, getattr(self.players[player_id], 'triangle_stacks', 0)))
        amount = base + per_stack * current_stack
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if not self._valid_player_id(target_id):
            return
        try:
            is_precision = 'precision' in self._effective_card_flags(card)
            dealt = self.deal_attack_damage(target_id, amount, is_precision=is_precision, attacker_id=player_id, source_card=card)
        except TypeError:
            dealt = self.deal_attack_damage(target_id, amount)
        self._last_damage_value[target_id] = int(dealt)
        if dealt > 0 and not immune:
            max_stacks = self._eval_int(player_id, params.get('max_stacks', 4), card, 4)
            new_stack = min(max_stacks, current_stack + 1)
            self.players[player_id].custom_vars[stack_name] = new_stack
            if stack_name == '三角形层数':
                self.players[player_id].triangle_stacks = new_stack

    def _atomic_discard_choice_then_draw(self, player_id, card, params, log, choice, context):
        ps = self.players[player_id]
        discarded = False
        if choice and 'target_instance_id' in choice:
            target = ps.find_hand_card(choice['target_instance_id'])
            if target and self._card_selectable_by_action(target) and getattr(target, 'instance_id', None) != getattr(card, 'instance_id', None):
                ps.hand.remove(target)
                self._discard_card(ps, target)
                discarded = True
        ps.draw_cards(1)
        if self._is_chilli_card(card):
            self._log_chilli_summary(player_id, discarded, card, 1 if discarded else 0)
            return
        self.log_msg(log or f"{self.pn(player_id)}抽1张牌")

    def _atomic_coffee_gain_e(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if not (0 <= target_id < len(self.players)):
            target_id = player_id
        target = self.players[target_id]
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        first_bonus = self._eval_int(player_id, params.get('first_bonus', 1), card, 1)
        bonus = first_bonus if getattr(target, 'coffee_first_use', False) else 0
        target.gain_elixir(amount + bonus)
        target.coffee_first_use = False
        target.custom_vars['咖啡首次使用'] = 0
        self.log_msg(log or f"{self.pn(target_id)}获得{amount + bonus}E")

    def _atomic_copy_choice_with_discount(self, player_id, card, params, log, choice, context):
        ps = self.players[player_id]
        if not (choice and 'target_instance_id' in choice):
            return
        target = ps.find_hand_card(choice['target_instance_id'])
        if target is None or not self._card_selectable_by_action(target) or not ps.can_add_to_hand():
            return
        if card is not None and card.def_id == 'Mimic' and not self._pay_mimic_special_cost(player_id, target, card):
            return
        copy_card = self._make_mimic_copy_card(target)
        default_discount = 0 if card is not None and card.def_id == 'Mimic' else 1
        copy_card.mimic_discount = self._eval_int(player_id, params.get('discount_e', default_discount), card, default_discount)
        ps.add_to_hand(copy_card)
        self._enforce_unique_cards_for_player(player_id, preferred_card=copy_card)
        if log:
            self.log_msg(log)

    def _set_card_property_value(self, player_id, current_card, params, value):
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), current_card)
        if target_card is None:
            return None
        prop = str(params.get('property', 'fusion_level'))
        if prop == 'cost_e':
            prop = 'cost_e_override'
        elif prop == 'cost_m':
            prop = 'cost_m_override'
        value = int(value)
        if prop in ('fusion_level', 'fission_level'):
            value = clamp_card_layer(value)
        elif prop == 'extra_hits':
            value = clamp_card_extra_hits(value)
        elif prop in ('mimic_discount', 'cost_e_override', 'cost_m_override', 'bonus_damage', 'return_to_hand_turns',
                      'held_turns', 'swift_value', 'magic_swift_value', 'power_value', 'temp_swift_value', 'temp_heavy_value', 'temp_magic_heavy_value'):
            value = max(0, value)
        if getattr(target_card, 'def_id', '') == 'Tomato':
            if prop == 'held_turns':
                value = min(6, value)
            elif prop == 'bonus_damage':
                value = min(18, value)
            elif prop == 'power_value':
                value = min(18, value)
        if prop in ('fusion_level', 'fission_level', 'extra_hits', 'mimic_discount', 'cost_e_override', 'cost_m_override',
                    'bonus_damage', 'return_to_hand_turns', 'held_turns', 'swift_value', 'magic_swift_value',
                    'power_value', 'temp_swift_value', 'temp_heavy_value', 'temp_magic_heavy_value'):
            setattr(target_card, prop, value)
            if prop == 'fusion_level':
                target_card.fusion_multiplier = float(value)
            elif prop == 'fission_level':
                target_card.fission_count = max(0, int(value) - 1)
            elif prop == 'swift_value':
                if value > 0:
                    target_card.instance_flags.add('swift')
                    target_card.disabled_flags.discard('swift')
                else:
                    target_card.instance_flags.discard('swift')
                    target_card.disabled_flags.add('swift')
            elif prop == 'magic_swift_value':
                if value > 0:
                    target_card.instance_flags.add('magic_swift')
                    target_card.disabled_flags.discard('magic_swift')
                else:
                    target_card.instance_flags.discard('magic_swift')
                    target_card.disabled_flags.add('magic_swift')
            elif prop == 'power_value':
                if value > 0:
                    target_card.instance_flags.add('power')
                    target_card.disabled_flags.discard('power')
                else:
                    target_card.instance_flags.discard('power')
                    target_card.disabled_flags.add('power')
            elif prop == 'temp_swift_value':
                if value > 0:
                    target_card.instance_flags.add('temp_swift')
                    target_card.disabled_flags.discard('temp_swift')
                else:
                    target_card.instance_flags.discard('temp_swift')
                    target_card.disabled_flags.add('temp_swift')
            elif prop == 'temp_heavy_value':
                if value > 0:
                    target_card.instance_flags.add('temp_heavy')
                    target_card.disabled_flags.discard('temp_heavy')
                else:
                    target_card.instance_flags.discard('temp_heavy')
                    target_card.disabled_flags.add('temp_heavy')
            elif prop == 'temp_magic_heavy_value':
                if value > 0:
                    target_card.instance_flags.add('temp_magic_heavy')
                    target_card.disabled_flags.discard('temp_magic_heavy')
                else:
                    target_card.instance_flags.discard('temp_magic_heavy')
                    target_card.disabled_flags.add('temp_magic_heavy')
        return target_card

    def _get_card_property_numeric_value(self, target_card, prop):
        if prop in ('cost_e', 'cost_e_override'):
            value = target_card.cost_e_override if target_card.cost_e_override is not None else target_card.card_def.cost_e
        elif prop in ('cost_m', 'cost_m_override'):
            value = target_card.cost_m_override if target_card.cost_m_override is not None else target_card.card_def.cost_m
        else:
            value = getattr(target_card, prop, 0)
        if value is None:
            return 0
        value = int(value)
        if getattr(target_card, 'def_id', '') == 'Tomato':
            if prop == 'held_turns':
                return min(6, max(0, value))
            if prop == 'bonus_damage':
                return min(18, max(0, value))
            if prop == 'power_value':
                return min(18, max(0, value))
        return value

    def _atomic_card_prop_set(self, player_id, card, params, log, choice, context):
        value = self._eval_int(player_id, params.get('value', 0), card)
        target_card = self._set_card_property_value(player_id, card, params, value)
        if target_card is not None and log:
            self.log_msg(log)

    def _atomic_card_prop_add(self, player_id, card, params, log, choice, context):
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if target_card is None:
            return
        prop = str(params.get('property', params.get('prop', 'fusion_level')))
        current = self._get_card_property_numeric_value(target_card, prop)
        amount = self._eval_int(player_id, params.get('amount', params.get('value', 0)), card)
        if (
            prop == 'fission_level'
            and getattr(card, 'def_id', '') == 'Fission'
            and 'multi_petal' in getattr(card, 'setup_modifiers', set())
            and int(amount) == 1
        ):
            amount = 2
        value = current + amount
        self._set_card_property_value(player_id, card, {'card': params.get('card', {'ref': 'current_card'}), 'property': prop}, value)
        if log:
            self.log_msg(log)

    def _atomic_card_prop_mul(self, player_id, card, params, log, choice, context):
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if target_card is None:
            return
        prop = str(params.get('property', 'fusion_level'))
        current = self._get_card_property_numeric_value(target_card, prop)
        multiplier = self._eval_int(player_id, params.get('multiplier', params.get('amount', 1)), card, 1)
        self._set_card_property_value(player_id, card, {'card': params.get('card', {'ref': 'current_card'}), 'property': prop}, current * multiplier)
        if log:
            self.log_msg(log)

    def _atomic_card_damage_multiply(self, player_id, card, params, log, choice, context):
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if target_card is None:
            return
        multiplier = self._eval_int(player_id, params.get('multiplier', 2), card, 2)
        current = max(1, int(getattr(target_card, 'fusion_level', 1)))
        self._set_card_property_value(player_id, card, {'card': params.get('card', {'ref': 'current_card'}), 'property': 'fusion_level'}, current * multiplier)
        if log:
            self.log_msg(log)

    def _atomic_clear_tags(self, player_id, card, params, log, choice, context):
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if target_card is None:
            return
        all_flags = self._effective_card_flags(target_card)
        target_card.instance_flags = set()
        target_card.disabled_flags = set(getattr(target_card, 'disabled_flags', set()) or set())
        target_card.disabled_flags.update(all_flags)
        if log:
            self.log_msg(log)

    def _atomic_equipment_prop_set(self, player_id, card, params, log, choice, context):
        value = self._eval_int(player_id, params.get('value', 0), card)
        eq = self._set_equipment_property_value(player_id, card, params, value)
        if eq is not None and log:
            self.log_msg(log)

    def _atomic_equipment_prop_add(self, player_id, card, params, log, choice, context):
        eq = self._resolve_equipment_ref(player_id, params.get('equipment', {'ref': 'current_equipment'}), card)
        if eq is None:
            return
        prop = str(params.get('property', 'turns_equipped'))
        current = self._get_equipment_property_value(eq, prop)
        value = current + self._eval_int(player_id, params.get('amount', 0), card)
        self._set_equipment_property_value(player_id, card, params, value)
        if log:
            self.log_msg(log)

    def _atomic_player_prop_set(self, player_id, card, params, log, choice, context):
        prop = str(params.get('property') or params.get('prop', 'health'))
        value = self._eval_int(player_id, params.get('value', 0), card)
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            if self._set_player_property_value(tid, prop, value) is not None and log:
                self.log_msg(log)

    def _atomic_player_prop_add(self, player_id, card, params, log, choice, context):
        prop = str(params.get('property') or params.get('prop', 'health'))
        amount = self._eval_int(player_id, params.get('amount') or params.get('value', 0), card)
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            current = self._get_player_property_value(tid, prop)
            if self._set_player_property_value(tid, prop, current + amount) is not None and log:
                self.log_msg(log)

    def _atomic_discard_hand_by_paid_e(self, player_id, card, params, log, choice, context):
        threshold = params.get('threshold', params.get('amount', None))
        if threshold is None:
            threshold = getattr(card, '_paid_e_this_play', getattr(card, 'cost_e', 0))
        threshold = self._eval_int(player_id, threshold, card)
        target_ref = params.get('target', params.get('targets', 'all_players'))
        if target_ref in ('all_players', 'all', 'both'):
            targets = list(range(len(self.players)))
        else:
            targets = self._resolve_targets(player_id, target_ref)
        total = 0
        for tid in targets:
            if not (0 <= tid < len(self.players)):
                continue
            ps = self.players[tid]
            matched = [c for c in list(ps.hand) if getattr(c, 'def_id', '') != ERROR_CARD_ID and int(getattr(c, 'cost_e', 0) or 0) <= threshold]
            for target_card in matched:
                if target_card in ps.hand:
                    ps.hand.remove(target_card)
                    self._discard_card(ps, target_card)
                    total += 1
        if log:
            self.log_msg(log)
        elif total > 0:
            self.log_msg(f"风吹走了{total}张牌")

    def _atomic_restore_turn_start_stats(self, player_id, card, params, log, choice, context):
        extra_self_e_loss = self._eval_int(player_id, params.get('extra_self_e_loss', 0), card)
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            if params.get('exclude_self') and tid == player_id:
                continue
            self._restore_turn_start_snapshot(tid, extra_self_e_loss if tid == player_id else 0)
        if log:
            self.log_msg(log)

    def _atomic_restore_match_start_stats(self, player_id, card, params, log, choice, context):
        extra_self_e_loss = self._eval_int(player_id, params.get('extra_self_e_loss', 0), card)
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            if params.get('exclude_self') and tid == player_id:
                continue
            if getattr(self.players[tid], 'health', 0) <= 0:
                continue
            self._restore_match_start_snapshot(tid, extra_self_e_loss if tid == player_id else 0)
        if log:
            self.log_msg(log)

    def _atomic_counter_pending_attack_damage(self, player_id, card, params, log, choice, context):
        ratio = float(params.get('ratio', params.get('multiplier', 0.5)) or 0)
        incoming = 0
        if isinstance(context, dict):
            try:
                incoming = int(context.get('first_hit_damage', context.get('first_damage', 0)) or 0)
            except Exception:
                incoming = 0
            parts = context.get('incoming_damage_parts')
            if isinstance(parts, (list, tuple)) and parts:
                try:
                    incoming = int(context.get('first_hit_damage') or context.get('first_damage') or parts[0] or 0)
                except Exception:
                    incoming = 0
            # Do not fall back to total incoming damage here. Salt-style
            # counters reflect only the first hit of a multi-hit card; old
            # prediction fallbacks may store the total as one synthetic part.
        amount = max(0, int(math.ceil(incoming * ratio)))
        if amount <= 0:
            return
        source = str(params.get('source', getattr(card, 'name_cn', '反击')))
        damage_type = params.get('damage_type', DAMAGE_TYPE_PHYSICAL)
        damage_tag = params.get('damage_tag', DAMAGE_TAG_DIRECT)
        target_ref = params.get('target', 'target')
        if target_ref in ('all_enemies', 'enemies'):
            targets = list(self.get_all_enemies(player_id)) if hasattr(self, 'get_all_enemies') else [1 - player_id]
        else:
            targets = self._resolve_targets(player_id, target_ref)
        mode = str(params.get('mode', params.get('damage_mode', 'attack')) or 'attack').lower()
        for tid in targets:
            if 0 <= tid < len(self.players):
                if mode in ('direct', 'effect'):
                    self._deal_direct_damage(tid, amount, source, player_id, damage_type=damage_type, damage_tag=damage_tag)
                else:
                    self.deal_attack_damage(tid, amount, 1, is_precision=False, attacker_id=player_id)
        if log:
            self.log_msg(log)

    def _atomic_lose_health(self, player_id, card, params, log, choice, context):
        amount = max(0, self._eval_int(player_id, params.get('amount', 0), card))
        source_id = self._resolve_target(player_id, params.get('source', 'self'))
        source = str(params.get('source_text', getattr(card, 'name_cn', '效果')))
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            if not (0 <= tid < len(self.players)) or amount <= 0:
                continue
            ps = self.players[tid]
            if ps.invincible:
                self.log_msg(f"{self.pn(tid)}无敌，免疫{source}伤害")
                continue
            ps.health -= amount
            self._note_achievement_health(tid)
            self._record_damage(tid, amount, source_id)
            self.log_msg(log or f"{self.pn(tid)}受到{amount}点{source}伤害（H={ps.health}）")
            self._check_yggdrasil(tid)
        self._check_game_over()

    def _atomic_destroy_equipment_choice_or_first(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if target_id < 0:
            return
        ts = self.players[target_id]
        eq = None
        if choice and 'target_instance_id' in choice:
            eq = ts.find_equipment(choice['target_instance_id'])
        if eq is None and ts.equipment:
            eq = ts.equipment[0]
        if eq is not None:
            eq_name = eq.card_def.name_cn
            if self._destroy_equipment(target_id, eq, source_id=player_id):
                self.log_msg(log or f"{self.pn(player_id)}摧毁了{self.pn(target_id)}的{eq_name}")
            elif log:
                self.log_msg(log)

    def _atomic_destroy_random_equip(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if target_id < 0:
            return
        pool = [eq for eq in self.players[target_id].equipment if 'indestructible' not in eq.card_instance.flags]
        if not pool:
            return
        eq = random.choice(pool)
        eq_name = eq.card_def.name_cn
        if self._destroy_equipment(target_id, eq, source_id=player_id):
            self.log_msg(log or f"{self.pn(player_id)}摧毁了{self.pn(target_id)}的{eq_name}")
        elif log:
            self.log_msg(log)

    def _atomic_destroy_all_equip(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if target_id < 0:
            return
        for eq in list(self.players[target_id].equipment):
            if 'indestructible' not in eq.card_instance.flags:
                eq_name = eq.card_def.name_cn
                if self._destroy_equipment(target_id, eq, source_id=player_id):
                    self.log_msg(log or f"{self.pn(player_id)}摧毁了{self.pn(target_id)}的{eq_name}")
                elif log:
                    self.log_msg(log)

    def _atomic_destroy_all_destroyable_equipment(self, player_id, card, params, log, choice, context):
        destroyed_count = 0
        for tid in self._resolve_targets(player_id, params.get('target', 'both')):
            for eq in list(self.players[tid].equipment):
                if 'indestructible' not in eq.card_instance.flags:
                    eq_name = eq.card_def.name_cn
                    if self._destroy_equipment(tid, eq, source_id=player_id):
                        destroyed_count += 1
                        self.log_msg(log or f"{self.pn(player_id)}摧毁了{self.pn(tid)}的{eq_name}")
                    elif log:
                        self.log_msg(log)
        if isinstance(context, dict):
            context['last_destroyed_equipment_count'] = destroyed_count
            vars_obj = context.setdefault('vars', {})
            if isinstance(vars_obj, dict):
                vars_obj['last_destroyed_equipment_count'] = destroyed_count

    def _atomic_activate_corruption(self, player_id, card, params, log, choice, context):
        eq = self._find_equipment_for_card(player_id, card)
        if eq is not None:
            eq.corruption_active = True

    def _atomic_heal(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if not (0 <= target_id < len(self.players)):
            return
        amount = self._eval_int(player_id, params.get('amount', 0), card)
        self.players[target_id].heal(amount)
        self.log_msg(log or f"{self.pn(target_id)}回复{amount}H")

    def _atomic_draw(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if not (0 <= target_id < len(self.players)):
            return
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self.players[target_id].draw_cards(amount)
        self.log_msg(log or f"{self.pn(target_id)}抽{amount}张牌")

    def _atomic_draw_to_hand_limit(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if not (0 <= target_id < len(self.players)):
            return
        ps = self.players[target_id]
        hand_limit = ps.hand_limit() if callable(getattr(ps, 'hand_limit', None)) else getattr(ps, 'hand_limit', HAND_LIMIT)
        amount = max(0, int(hand_limit) - len(ps.hand))
        if amount <= 0:
            return
        ps.draw_cards(amount)
        if not (isinstance(context, dict) and context.get('suppress_detail_logs')):
            self.log_msg(log or f"{self.pn(target_id)}抽{amount}张牌")

    def _atomic_gain_e(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if not (0 <= target_id < len(self.players)):
            return
        amount_expr = params.get('amount', 1)
        if isinstance(amount_expr, dict) and amount_expr.get('ref') in ('context_var', 'temp_var'):
            amount = int((context or {}).get(str(amount_expr.get('name', '')), 0) or 0)
        else:
            amount = self._eval_int(player_id, amount_expr, card, 1)
        if amount <= 0:
            return
        self.players[target_id].gain_elixir(amount)
        self.log_msg(log or f"{self.pn(target_id)}获得{amount}E")

    def _atomic_gain_m(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if not (0 <= target_id < len(self.players)):
            return
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self.players[target_id].gain_magic(amount)
        self.log_msg(log or f"{self.pn(target_id)}获得{amount}M")

    def _atomic_magic_salt_reflect(self, player_id, card, params, log, choice, context):
        if not isinstance(context, dict):
            return
        if self.pending_choice is not None or getattr(self, 'pending_response', None) is not None or getattr(self, 'pending_v2_ui', None) is not None:
            return
        try:
            damage = int(context.get('damage', 0) or 0)
            attacker_id = int(context.get('source_id', -1))
            target_id = int(context.get('target_id', player_id))
        except Exception:
            return
        if damage <= 0 or not self._valid_player_id(attacker_id) or not self._valid_player_id(target_id):
            return
        owner_id = player_id
        try:
            owner_id = int((context or {}).get('selected_equipment_owner_id', owner_id))
        except Exception:
            pass
        eq = self._find_equipment_for_card(owner_id, card)
        if eq is not None:
            owner_id = int(getattr(eq, 'owner', player_id))
        if not self._valid_player_id(owner_id):
            owner_id = player_id
        cost_m = max(0, self._eval_int(player_id, params.get('cost_m', 1), card, 1))
        owner = self.players[owner_id]
        if owner.magic < cost_m:
            return
        ratio = float(params.get('ratio', 0.5) or 0.5)
        reflect = int(math.ceil(damage * ratio))
        if reflect <= 0:
            return
        self.pending_choice = {
            'card': card.to_dict(),
            'player_id': owner_id,
            'choice_type': 'magic_salt_reflect',
            'choice_params': {
                'owner_id': owner_id,
                'attacker_id': attacker_id,
                'target_id': target_id,
                'damage': damage,
                'reflect': reflect,
                'ratio': ratio,
                'cost_m': cost_m,
                'cancellable': True,
                'title': '魔法盐',
                'message': f'是否支付{cost_m}M，对{self.pn(attacker_id)}反弹{reflect}D？',
                'ok_text': '支付并反伤',
                'cancel_text': '不触发',
            },
            'already_paid': True,
            'message': f'是否支付{cost_m}M，对{self.pn(attacker_id)}反弹{reflect}D？',
        }

    def _atomic_gain_armor(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if not (0 <= target_id < len(self.players)):
            return
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self.players[target_id].armor += amount
        self._note_achievement_status_peak(target_id)
        self.log_msg(log or f"{self.pn(target_id)}获得{amount}护甲")

    def _atomic_gain_dodge(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if not (0 <= target_id < len(self.players)):
            return
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self.players[target_id].dodge += amount
        self._note_achievement_status_peak(target_id)
        self.log_msg(log or f"{self.pn(target_id)}获得{amount}闪避")

    def _atomic_apply_poison(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if not self._valid_player_id(target_id):
            return
        if self._status_application_blocked(target_id, 'poison'):
            return
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self.players[target_id].poison += amount
        self._normalize_status_value(self.players[target_id], 'poison')
        self._note_achievement_status_peak(target_id)
        self.log_msg(log or f"{self.pn(target_id)}+{amount}中毒")

    def _atomic_apply_burn(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if not self._valid_player_id(target_id):
            return
        if self._status_application_blocked(target_id, 'fire'):
            return
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self.players[target_id].fire += amount
        self._normalize_status_value(self.players[target_id], 'fire')
        self._note_achievement_status_peak(target_id)
        self.log_msg(log or f"{self.pn(target_id)}+{amount}灼烧")

    def _atomic_apply_toxic(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if not self._valid_player_id(target_id):
            return
        if self._status_application_blocked(target_id, 'toxic'):
            return
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self.players[target_id].toxic += amount
        self._normalize_status_value(self.players[target_id], 'toxic')
        self._note_achievement_status_peak(target_id)
        self.log_msg(log or f"{self.pn(target_id)}+{amount}淬毒")

    def _atomic_apply_jungle_status(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if not self._valid_player_id(target_id):
            return
        status = str(params.get('status', 'jungle:shield'))
        if self._status_application_blocked(target_id, status):
            return
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self._add_custom_status_value(target_id, status, amount)
        label = str(params.get('label') or status.split(':')[-1])
        if log is not False:
            self.log_msg(log or f"{self.pn(target_id)}获得{amount}层{label}")

    def _atomic_apply_turn_regen(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if self._status_application_blocked(target_id, 'turn_magic_turns' if str(params.get('kind', 'heal')) == 'magic' else 'turn_heal_turns'):
            return
        turns = self._eval_int(player_id, params.get('turns', 1), card, 1)
        power = self._eval_int(player_id, params.get('power', 1), card, 1)
        kind = str(params.get('kind', 'heal'))
        if kind == 'magic':
            merged_turns, merged_power = self._merge_turn_regen_status(target_id, 'magic', turns, power)
            self.players[target_id].gain_magic(power)
            remaining_turns = max(0, merged_turns - 1)
            self._set_custom_status_alias_group(target_id, 'jungle:turn_magic_turns', ('jungle:turn_magic_turns', 'turn_magic_turns'), remaining_turns)
            if remaining_turns <= 0:
                self._set_custom_status_alias_group(target_id, 'jungle:turn_magic_power', ('jungle:turn_magic_power', 'turn_magic_power'), 0)
            self.log_msg(log or f"{self.pn(target_id)}获得魔力回合回复：{remaining_turns};{merged_power}，+{power}M")
        else:
            merged_turns, merged_power = self._merge_turn_regen_status(target_id, 'heal', turns, power)
            self.players[target_id].heal(power)
            remaining_turns = max(0, merged_turns - 1)
            self._set_custom_status_alias_group(target_id, 'jungle:turn_heal_turns', ('jungle:turn_heal_turns', 'turn_heal_turns'), remaining_turns)
            if remaining_turns <= 0:
                self._set_custom_status_alias_group(target_id, 'jungle:turn_heal_power', ('jungle:turn_heal_power', 'turn_heal_power'), 0)
            self.log_msg(log or f"{self.pn(target_id)}获得回合回复：{remaining_turns};{merged_power}，+{power}H")

    def _atomic_magic_grapes_damage(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        base = self._eval_int(player_id, params.get('amount', 4), card, 4)
        repeats = 1 + len(getattr(self.players[target_id], 'equipment', []) or [])
        total = 0
        for _ in range(repeats):
            total += self._deal_direct_damage(
                target_id,
                base,
                params.get('source', '电击'),
                player_id,
                damage_type=DAMAGE_TYPE_MAGIC,
                damage_tag=DAMAGE_TAG_BATTERY,
            )
        self._last_damage_value[target_id] = int(total)

    def _atomic_create_copies_to_deck_top(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        def_id = str(params.get('def_id') or (getattr(card, 'def_id', '') if card else ''))
        count = min(20, max(0, self._eval_int(player_id, params.get('count', 1), card, 1)))
        flags = normalize_card_flags(params.get('flags', []))
        swift = self._eval_int(player_id, params.get('swift_value', 0), card, 0)
        magic_swift = self._eval_int(player_id, params.get('magic_swift_value', 0), card, 0)
        power = self._eval_int(player_id, params.get('power_value', 0), card, 0)
        extra_hits = clamp_card_extra_hits(self._eval_int(player_id, params.get('extra_hits', 0), card, 0))
        ps = self.players[target_id]
        made = []
        for _ in range(max(0, count)):
            new_card = CardInstance(def_id)
            new_card.instance_flags.update(flags)
            if swift > 0:
                new_card.swift_value = swift
                new_card.instance_flags.add('swift')
            if magic_swift > 0:
                new_card.magic_swift_value = magic_swift
                new_card.instance_flags.add('magic_swift')
            if power > 0:
                new_card.power_value = power
                new_card.instance_flags.add('power')
            if extra_hits > 0:
                new_card.extra_hits = extra_hits
                new_card.setup_modifiers.add('explicit_extra_hits')
            self._apply_setup_modifiers_to_card(target_id, new_card)
            ps.deck.insert(0, new_card)
            made.append(new_card)
        if log:
            self.log_msg(log)

    def _atomic_consume_magic_for_status(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if self._status_application_blocked(target_id, params.get('status', 'jungle:toxic_poison')):
            return
        source_id = self._resolve_target(player_id, params.get('source', 'self'))
        status = str(params.get('status', 'jungle:toxic_poison'))
        amount = max(0, int(getattr(self.players[source_id], 'magic', 0) or 0))
        if amount <= 0:
            return
        self.players[source_id].magic = 0
        self._add_custom_status_value(target_id, status, amount)
        if params.get('also_poison'):
            self.players[target_id].poison += amount
            self._normalize_status_value(self.players[target_id], 'poison')
            self._note_achievement_status_peak(target_id)
        label = str(params.get('label') or '剧毒')
        if params.get('also_poison'):
            self.log_msg(log or f"{self.pn(target_id)}+{amount}层{label}和{amount}P")
        else:
            self.log_msg(log or f"{self.pn(target_id)}+{amount}层{label}")

    def _atomic_jungle_root_gain(self, player_id, card, params, log, choice, context):
        owner_id = self._resolve_target(player_id, params.get('target', 'self'))
        if self._status_application_blocked(owner_id, 'jungle:root_status'):
            return
        amount = self._eval_int(player_id, params.get('amount', 2), card, 2)
        self._add_custom_status_value(owner_id, 'jungle:root_status', amount)
        _, eq = self._find_equipment_by_card_instance_id(getattr(card, 'instance_id', None))
        if eq is not None:
            eq.custom_vars['jungle_root_layers'] = int(eq.custom_vars.get('jungle_root_layers', 0) or 0) + amount
        self._note_achievement_status_peak(owner_id)
        self.log_msg(log or f"{self.pn(owner_id)}获得{amount}层树根")

    def _atomic_jungle_root_remove_owned(self, player_id, card, params, log, choice, context):
        owner_id = self._resolve_target(player_id, params.get('target', 'self'))
        _, eq = self._find_equipment_by_card_instance_id(getattr(card, 'instance_id', None))
        amount = int(eq.custom_vars.get('jungle_root_layers', 0) or 0) if eq is not None else 0
        if amount > 0:
            self._set_custom_status_value(owner_id, 'jungle:root_status', max(0, self._custom_status_value(owner_id, 'jungle:root_status') - amount))
            if eq is not None:
                eq.custom_vars['jungle_root_layers'] = 0

    def _consume_jungle_root_layer_from_equipment(self, owner_id: int):
        if not (0 <= owner_id < len(self.players)):
            return
        candidates = []
        for equip_owner_id, owner_state in enumerate(self.players):
            for eq in list(getattr(owner_state, 'equipment', []) or []):
                tracked_layers = int(eq.custom_vars.get('jungle_root_layers', 0) or 0)
                if tracked_layers <= 0 and not self._card_matches_any_id(eq.card_instance, eq.card_def, ['Root', 'jungle:root']):
                    continue
                try:
                    effect_target = int(getattr(eq, 'effect_target', equip_owner_id))
                except (TypeError, ValueError):
                    effect_target = equip_owner_id
                if effect_target != owner_id:
                    continue
                candidates.append(eq)
        for eq in candidates:
            layers = int(eq.custom_vars.get('jungle_root_layers', 0) or 0)
            if layers <= 0:
                continue
            eq.custom_vars['jungle_root_layers'] = layers - 1
            return

    def _card_matches_any_id(self, card=None, card_def=None, ids=None) -> bool:
        """Return whether a card/equipment definition matches any legacy or namespaced id."""
        wanted = {str(item).strip().lower() for item in (ids or []) if str(item).strip()}
        if not wanted:
            return False
        candidates = []
        for obj in (card, card_def):
            if obj is None:
                continue
            for attr in ('def_id', 'id', 'legacy_id'):
                value = getattr(obj, attr, None)
                if value not in (None, ''):
                    candidates.append(str(value))
            nested_def = getattr(obj, 'card_def', None)
            if nested_def is not None and nested_def is not obj:
                for attr in ('def_id', 'id', 'legacy_id'):
                    value = getattr(nested_def, attr, None)
                    if value not in (None, ''):
                        candidates.append(str(value))
        for value in candidates:
            text = value.strip().lower()
            if text in wanted or text.split(':')[-1] in wanted:
                return True
        return False

    def _atomic_plank_immunity(self, player_id, card, params, log, choice, context):
        # Implemented through damage modifier hook; kept as an atomic no-op for readable mod data.
        return None

    def _atomic_magic_relic_trigger(self, player_id, card, params, log, choice, context):
        if not hasattr(self, 'get_teammate'):
            return
        try:
            mate_id = self.get_teammate(player_id)
        except Exception:
            return
        if not (0 <= mate_id < len(self.players)):
            return
        mate = self.players[mate_id]
        if int(getattr(mate, 'magic', 0) or 0) < 2:
            return
        mate.magic -= 2
        self.players[player_id].gain_magic(3)
        self.log_msg(log or f"{self.pn(player_id)}的魔法遗物消耗{self.pn(mate_id)}2M，自己+3M")

    def _atomic_yin_yang_effect(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        if not (0 <= target_id < len(self.players)):
            return
        ps = self.players[target_id]
        draw_count = len(ps.deck)
        hand_cards = list(ps.hand)
        ps.hand.clear()
        ps.deck.extend(hand_cards)
        drawn = ps.draw_cards(draw_count)
        self.log_msg(log or f"{self.pn(target_id)}将手牌置入牌堆底并抽{len(drawn)}张牌")

    def _atomic_shuffle_hand(self, player_id, card, params, log, choice, context):
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            if not (0 <= tid < len(self.players)):
                continue
            ps = self.players[tid]
            if ps.hand and not self._is_status_immune(tid):
                random.shuffle(ps.hand)
                self.log_msg(log or f"{self.pn(tid)}因失明打乱手牌")

    def _atomic_flower_burst(self, player_id, card, params, log, choice, context):
        eq = self._find_equipment_for_card(player_id, card)
        if eq is None or int(getattr(eq, 'turns_equipped', 0) or 0) < 1:
            self.log_msg(f"{self.pn(player_id)}的花朵还未成熟")
            return
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        if 0 <= target_id < len(self.players):
            amount = self._eval_int(player_id, params.get('amount', 18), card, 18)
            if self._status_application_blocked(target_id, 'poison'):
                self._destroy_equipment(player_id, eq, check_protection=False)
                return
            self.players[target_id].poison += amount
            self._normalize_status_value(self.players[target_id], 'poison')
            self.log_msg(log or f"{self.pn(target_id)}+{amount}中毒")
        self._destroy_equipment(player_id, eq, check_protection=False)

    def _ocean_selectable_targets(
            self,
            player_id: int,
            allow_self: bool = False,
            enemies_only: bool = True) -> List[int]:
        targets = []
        team_of = getattr(self, 'team_of', None)
        own_team = None
        if callable(team_of):
            try:
                own_team = team_of(player_id)
            except Exception:
                own_team = None
        for tid in range(len(getattr(self, 'players', []) or [])):
            if tid == player_id:
                if not allow_self:
                    continue
            elif enemies_only and own_team is not None:
                try:
                    if team_of(tid) == own_team:
                        continue
                except Exception:
                    pass
            if self._target_can_be_selected(player_id, tid, allow_self=allow_self):
                targets.append(tid)
        return targets

    def _atomic_ocean_for_each_selectable_target(self, player_id, card, params, log, choice, context):
        is_attack = bool(getattr(card, 'card_type', '') == 'thorn')
        allow_self = 'self_target' in self._effective_card_flags(card) or not is_attack
        body = params.get('body') or params.get('steps') or []
        if not isinstance(body, list):
            return
        for target_id in self._ocean_selectable_targets(player_id, allow_self=allow_self, enemies_only=is_attack):
            if self.game_over:
                break
            child_context = dict(context or {})
            child_context.update({'target_id': target_id, 'target_player': target_id})
            child_context.pop('wide_strike_targets', None)
            child_context.pop('target_players', None)
            child_choice = {'target_player_id': target_id, 'target_player': target_id, 'target_id': target_id}
            child_context['choice'] = child_choice
            child_context['current_action'] = child_choice
            child_context['target_player_explicit'] = True
            vars_dict = dict(child_context.get('vars') or {})
            vars_dict['target_player'] = target_id
            vars_dict.pop('wide_strike_targets', None)
            child_context['vars'] = vars_dict
            self._run_effect_list(player_id, card, body, child_choice, child_context)

    def _atomic_ocean_charge_self_damage(self, player_id, card, params, log, choice, context):
        amount = max(0, int(getattr(card, 'charge_value', 0) or 0)) if card is not None else 0
        if amount <= 0:
            return
        self._deal_direct_damage(
            player_id,
            amount,
            '电荷',
            player_id,
            damage_type=DAMAGE_TYPE_MAGIC,
            damage_tag=DAMAGE_TAG_BATTERY,
        )

    def _atomic_ocean_spikeball_damage(self, player_id, card, params, log, choice, context):
        hand_count = len(getattr(self.players[player_id], 'hand', []) or [])
        boosted = hand_count < 4
        if boosted:
            if card is not None:
                card.instance_flags.add('precision')
                card.instance_flags.add('wide_strike')
            targets = self._ocean_selectable_targets(player_id, allow_self=True, enemies_only=False)
            amount = self._eval_int(player_id, params.get('boosted_amount', 20), card, 20)
        else:
            target_id = self._resolve_target(player_id, params.get('target', 'target'))
            targets = [target_id] if self._valid_player_id(target_id) else []
            amount = self._eval_int(player_id, params.get('amount', 6), card, 6)
        is_precision = 'precision' in self._effective_card_flags(card)
        for target_id in targets:
            if self.game_over:
                break
            self._atomic_ocean_charge_self_damage(player_id, card, {}, '', choice, context)
            self.deal_attack_damage(target_id, amount, 1, is_precision=is_precision, attacker_id=player_id, source_card=card)

    def _atomic_ocean_random_blind_hand(self, player_id, card, params, log, choice, context):
        count = max(0, self._eval_int(player_id, params.get('count', 3), card, 3))
        for target_id in self._resolve_targets(player_id, params.get('target', 'target')):
            if not self._valid_player_id(target_id):
                continue
            hand = list(getattr(self.players[target_id], 'hand', []) or [])
            if count > 0 and len(hand) > count:
                hand = random.sample(hand, count)
            for hand_card in hand:
                hand_card.hand_blind_turns = max(1, int(getattr(hand_card, 'hand_blind_turns', 0) or 0))
                hand_card.instance_flags.add('ocean_blinded')
            if self.players[target_id].hand:
                random.shuffle(self.players[target_id].hand)
            if hand:
                self.log_msg(log or f"{self.pn(target_id)}的{len(hand)}张手牌被蒙蔽")

    def _atomic_ocean_add_charge_to_hand(self, player_id, card, params, log, choice, context):
        amount = max(0, self._eval_int(player_id, params.get('amount', 3), card, 3))
        count = params.get('count', None)
        count = None if count in (None, 'all', '全部') else max(0, self._eval_int(player_id, count, card, 0))
        for target_id in self._resolve_targets(player_id, params.get('target', 'target')):
            if not self._valid_player_id(target_id):
                continue
            if params.get('require_hit'):
                last_damage = 0
                if isinstance(context, dict):
                    try:
                        if int(context.get('target_id', target_id)) == int(target_id):
                            last_damage = int(context.get('last_damage', 0) or 0)
                    except Exception:
                        last_damage = 0
                if last_damage <= 0:
                    try:
                        last_damage = int(self._last_damage_value[target_id] or 0)
                    except Exception:
                        last_damage = 0
                if last_damage <= 0:
                    continue
            hand = list(getattr(self.players[target_id], 'hand', []) or [])
            if count is not None and len(hand) > count:
                hand = random.sample(hand, count)
            for hand_card in hand:
                hand_card.charge_value = max(0, int(getattr(hand_card, 'charge_value', 0) or 0) + amount)
                hand_card.instance_flags.add('charge')
            if hand:
                self.log_msg(log or f"{self.pn(target_id)}的{len(hand)}张手牌获得{amount}层电荷")

    def _ocean_visible_status_count(self, player_id: int) -> int:
        if not self._valid_player_id(player_id):
            return 0
        ps = self.players[player_id]
        count = 0
        for attr in (
            'poison', 'fire', 'toxic', 'dodge', 'armor', 'sluggish', 'overload', 'foresight',
            'fracture', 'stagnation', 'blind', 'heal_block', 'weakness', 'bleed',
            'fragment_stacks', 'skip_turn', 'attack_blocked',
        ):
            try:
                if int(getattr(ps, attr, 0) or 0) > 0:
                    count += 1
            except Exception:
                continue
        for value in (getattr(ps, 'custom_statuses', {}) or {}).values():
            try:
                if int(value or 0) > 0:
                    count += 1
            except Exception:
                continue
        return count

    def _atomic_ocean_status_tag_damage(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        if not self._valid_player_id(target_id):
            return
        base = self._eval_int(player_id, params.get('base', 30), card, 30)
        per_status = self._eval_int(player_id, params.get('per_status', 10), card, 10)
        per_tag = self._eval_int(player_id, params.get('per_tag', 10), card, 10)
        tag_count = len(self._effective_card_flags(card))
        amount = base + self._ocean_visible_status_count(target_id) * per_status + tag_count * per_tag
        is_precision = 'precision' in self._effective_card_flags(card)
        self.deal_attack_damage(target_id, amount, is_precision=is_precision, attacker_id=player_id, source_card=card)

    def _atomic_ocean_discard_count_damage(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        if not self._valid_player_id(target_id):
            return
        base = self._eval_int(player_id, params.get('base', 2), card, 2)
        per = self._eval_int(player_id, params.get('per', 1), card, 1)
        count = int(self.players[player_id].custom_vars.get('ocean_active_discards', 0) or 0)
        is_precision = 'precision' in self._effective_card_flags(card)
        self.deal_attack_damage(target_id, base + count * per, is_precision=is_precision, attacker_id=player_id, source_card=card)

    def _atomic_ocean_magic_coral_tick(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        last_damage = 0
        if isinstance(context, dict):
            try:
                last_damage = int(context.get('last_damage', 0) or 0)
            except Exception:
                last_damage = 0
        if last_damage <= 0 and self._valid_player_id(target_id):
            last_damage = int(self._last_damage_value[target_id] or 0)
        if self._valid_player_id(target_id) and last_damage <= 0:
            return
        times = self._card_total_hits(card, self._eval_int(player_id, params.get('times', 1), card, 1))
        for _ in range(max(0, times)):
            for target_id in range(len(self.players)):
                current = int(self.players[target_id].custom_vars.get('ocean_action_skip_turns', 0) or 0)
                self.players[target_id].custom_vars['ocean_action_skip_turns'] = current + 1
            self.log_msg(log or "全体玩家下回合跳过")

    def _atomic_ocean_add_blood_debt(self, player_id, card, params, log, choice, context):
        if params.get('require_physical_damage'):
            try:
                if int((context or {}).get('damage', 0) or 0) <= 0:
                    return
            except Exception:
                return
        target_selector = params.get('target', 'target')
        current_event = str((context or {}).get('current_event') or (context or {}).get('event') or '')
        if current_event in ('on_damage_taken', 'damage_taken') and (context or {}).get('source_id') is not None:
            try:
                target_ids = [int((context or {}).get('source_id'))]
            except Exception:
                target_ids = []
        elif target_selector in ('source', 'event_source', 'last_actor', 'damage_source'):
            try:
                target_ids = [int((context or {}).get('source_id', player_id))]
            except Exception:
                target_ids = [player_id]
        else:
            target_ids = self._resolve_targets(player_id, target_selector)
        for target_id in target_ids:
            if self._valid_player_id(target_id):
                self._add_custom_status_value(target_id, 'ocean:blood_debt', self._eval_int(player_id, params.get('amount', 1), card, 1))
                self.log_msg(log or f"{self.pn(target_id)}+1层血债")

    def _atomic_ocean_dead_leaf_slow_if_no_counter(self, player_id, card, params, log, choice, context):
        for target_id in self._resolve_targets(player_id, params.get('target', 'target')):
            if not self._valid_player_id(target_id):
                continue
            has_counter = any(
                getattr(hand_card.card_def, 'card_type', '') == 'guard'
                or bool(getattr(hand_card.card_def, 'response_trigger', '') or '')
                for hand_card in list(getattr(self.players[target_id], 'hand', []) or [])
            )
            if has_counter:
                continue
            amount = max(0, self._eval_int(player_id, params.get('amount', 1), card, 1))
            if amount <= 0:
                continue
            self.players[target_id].sluggish += amount
            self._note_achievement_status_peak(target_id)
            self.log_msg(log or f"{self.pn(target_id)}下个回合少抽{amount}张牌")

    def _apply_ocean_blood_debt_after_physical_damage(self, target_id: int, attacker_id: int):
        if not (self._valid_player_id(target_id) and self._valid_player_id(attacker_id)):
            return
        stacks = self._custom_status_value(target_id, 'ocean:blood_debt', 'blood_debt', '血债')
        if stacks <= 0:
            return
        self._set_custom_status_alias_group(target_id, 'ocean:blood_debt', ('ocean:blood_debt', 'blood_debt', '血债'), 0)
        self.players[attacker_id].gain_elixir(stacks)
        self.log_msg(f"{self.pn(target_id)}的血债解除，{self.pn(attacker_id)}获得{stacks}E")

    def _atomic_ocean_mark_auto_play(self, player_id, card, params, log, choice, context):
        if 'ocean_no_auto' in getattr(card, 'instance_flags', set()):
            return
        try:
            if int(getattr(card, 'fission_hit', 0) or 0) > 0:
                return
        except Exception:
            pass
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        if not self._valid_player_id(target_id):
            return
        ps = self.players[player_id]
        entries = ps.custom_vars.get('ocean_auto_cards')
        if not isinstance(entries, list):
            entries = []
        entries.append({
            'def_id': getattr(card, 'def_id', ''),
            'card': card.to_dict() if hasattr(card, 'to_dict') else None,
            'target_id': target_id,
            'swift_value': self._eval_int(player_id, params.get('swift_value', 0), card, 0),
            'magic_swift_value': self._eval_int(player_id, params.get('magic_swift_value', 0), card, 0),
            'exile': bool(params.get('exile', True)),
            'no_auto': True,
        })
        ps.custom_vars['ocean_auto_cards'] = entries

    def _atomic_ocean_sapphire_mark(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        if not self._valid_player_id(target_id):
            return
        chosen = None
        if isinstance(context, dict):
            chosen = context.get('chosen_card')
        if chosen is None and isinstance(choice, dict):
            try:
                iid = int(choice.get('target_instance_id'))
            except Exception:
                iid = -1
            if iid >= 0:
                chosen = self.players[player_id].find_hand_card(iid)
        if chosen is None or not self._card_selectable_by_action(chosen) or getattr(chosen, 'card_type', '') != 'thorn':
            return
        chosen_flags = self._effective_card_flags(chosen)
        if 'unique' in chosen_flags or 'exile' in chosen_flags:
            return
        if chosen not in self.players[player_id].hand:
            return
        self.players[player_id].hand.remove(chosen)
        chosen.instance_flags.add('exile')
        self._put_card_in_exile(player_id, chosen)
        entries = self.players[player_id].custom_vars.get('ocean_auto_cards')
        if not isinstance(entries, list):
            entries = []
        entries.append({
            'def_id': getattr(chosen, 'def_id', ''),
            'card': chosen.to_dict() if hasattr(chosen, 'to_dict') else None,
            'target_id': target_id,
            'swift_value': int(getattr(chosen, 'swift_value', 0) or 0),
            'magic_swift_value': int(getattr(chosen, 'magic_swift_value', 0) or 0),
            'exile': True,
            'no_auto': True,
        })
        self.players[player_id].custom_vars['ocean_auto_cards'] = entries
        self.log_msg(log or f"{self.pn(player_id)}的蓝宝石放逐1张攻击牌")

    def _void_zone_cards(self, target_id: int, zone: str) -> List[CardInstance]:
        if not self._valid_player_id(target_id):
            return []
        ps = self.players[target_id]
        zone_name = str(zone or 'hand')
        if zone_name == 'deck':
            return list(getattr(ps, 'deck', []) or [])
        if zone_name == 'discard':
            return list(getattr(ps, 'discard', []) or [])
        if zone_name == 'exile':
            return list(getattr(ps, 'exile', []) or [])
        return list(getattr(ps, 'hand', []) or [])

    def _void_selected_card(self, target_id: int, zone: str, choice) -> Optional[CardInstance]:
        if not isinstance(choice, dict):
            return None
        try:
            iid = int(choice.get('target_instance_id'))
        except Exception:
            iid = -1
        if iid < 0:
            return None
        for c in self._void_zone_cards(target_id, zone):
            if getattr(c, 'instance_id', None) == iid and self._card_selectable_by_action(c):
                return c
        return None

    def _void_remove_card_from_zone(self, target_id: int, card: CardInstance) -> bool:
        if not self._valid_player_id(target_id) or card is None:
            return False
        ps = self.players[target_id]
        for zone in (ps.hand, ps.deck, ps.discard, ps.exile):
            if card in zone:
                zone.remove(card)
                return True
        return False

    def _void_add_card_to_deck_random(self, target_id: int, card: CardInstance):
        if not self._valid_player_id(target_id) or card is None:
            return
        deck = self.players[target_id].deck
        deck.insert(random.randint(0, len(deck)) if deck else 0, card)

    def _void_weighted_card_id(self, card_type: Optional[str] = None, exclude: Optional[Set[str]] = None) -> Optional[str]:
        exclude = exclude or set()
        allowed_ids = getattr(self, 'allowed_card_ids', None)
        allowed_ids = set(allowed_ids or []) if allowed_ids is not None else None
        weighted = []
        for def_id, card_def in CARD_DEFS.items():
            if def_id in exclude or def_id == ERROR_CARD_ID:
                continue
            if allowed_ids is not None and def_id not in allowed_ids:
                continue
            if card_type and getattr(card_def, 'card_type', '') != card_type:
                continue
            if int(getattr(card_def, 'count', 0) or 0) <= 0:
                continue
            if 'sublime' in normalize_card_flags(getattr(card_def, 'flags', set()) or set()):
                continue
            weighted.extend([def_id] * max(1, int(getattr(card_def, 'count', 0) or 0)))
        return random.choice(weighted) if weighted else None

    def _void_resolve_card_def_id(self, raw_id: Any) -> Optional[str]:
        text = str(raw_id or '').strip()
        if not text:
            return None
        if text in CARD_DEFS:
            return text
        for def_id, card_def in CARD_DEFS.items():
            resource = getattr(card_def, 'v2_resource', {}) or {}
            known = {
                str(resource.get('id', '') or ''),
                str(resource.get('legacy_id', '') or ''),
                str(resource.get('runtime_id', '') or ''),
                str(getattr(card_def, 'id', '') or ''),
            }
            if text in known:
                return def_id
        path = text.split(':', 1)[1] if ':' in text else text
        pascal = ''.join(part.capitalize() for part in path.replace('-', '_').split('_') if part)
        return pascal if pascal in CARD_DEFS else None

    def _atomic_void_exile_target_hand(self, player_id, card, params, log, choice, context):
        for target_id in self._resolve_targets(player_id, params.get('target', 'target')):
            if not self._valid_player_id(target_id):
                continue
            cards = [c for c in list(self.players[target_id].hand) if self._card_selectable_by_action(c)]
            for hand_card in cards:
                self.players[target_id].hand.remove(hand_card)
                self._put_card_in_exile(target_id, hand_card)
            amount = len(cards)
            if amount > 0:
                self.players[target_id].weakness = max(0, int(getattr(self.players[target_id], 'weakness', 0) or 0)) + amount
                self.log_msg(log or f"{self.pn(target_id)}被放逐{amount}张手牌并获得{amount}层虚弱")

    def _atomic_void_move_selected_card(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        from_zone = str(params.get('from_zone', 'discard'))
        to_zone = str(params.get('to_zone', 'deck_top'))
        selected = self._void_selected_card(target_id, from_zone, choice)
        if selected is None:
            self.log_msg(log or f"{self.pn(player_id)}没有选择可用的牌")
            return
        self._void_remove_card_from_zone(target_id, selected)
        if to_zone == 'deck_top':
            self.players[target_id].deck.insert(0, selected)
        elif to_zone == 'deck_random':
            self._void_add_card_to_deck_random(target_id, selected)
        elif to_zone == 'hand':
            self.players[target_id].add_to_hand(selected)
        elif to_zone == 'exile':
            self._put_card_in_exile(target_id, selected)
        else:
            self._discard_card(self.players[target_id], selected)
        if log:
            self.log_msg(log)

    def _atomic_void_give_selected_hand_flag(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if not self._valid_player_id(target_id):
            return
        selected = self._void_selected_card(target_id, 'hand', choice)
        if selected is None:
            self.log_msg(log or f"{self.pn(player_id)}没有选择可用的牌")
            return
        flag = normalize_card_flag(params.get('flag', 'floating'))
        if flag:
            selected.instance_flags.add(flag)
        if log:
            self.log_msg(log)

    def _atomic_void_add_card_to_deck(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        def_id = self._void_resolve_card_def_id(self._resolve_card_id_ref(player_id, params.get('def_id', 'void:air'), card))
        if not self._valid_player_id(target_id) or def_id not in CARD_DEFS:
            return
        new_card = CardInstance(def_id)
        flags = normalize_card_flags(params.get('flags', []))
        new_card.instance_flags.update(flags)
        self._apply_setup_modifiers_to_card(target_id, new_card)
        if params.get('position') == 'random':
            self._void_add_card_to_deck_random(target_id, new_card)
        else:
            self.players[target_id].deck.insert(0, new_card)
        if log:
            self.log_msg(log)

    def _atomic_void_copy_response_card(self, player_id, card, params, log, choice, context):
        original = (context or {}).get('original_card') if isinstance(context, dict) else None
        if not isinstance(original, CardInstance):
            return
        copy_card = original.copy()
        copy_card.instance_flags.add('exile')
        self.players[player_id].add_to_hand(copy_card)
        if log:
            self.log_msg(log)

    def _atomic_void_antimatter_damage(self, player_id, card, params, log, choice, context):
        last_def = str(self.players[player_id].custom_vars.get('void_current_previous_def_id', self.players[player_id].custom_vars.get('void_last_played_def_id', '')) or '')
        if last_def in ('void:antimatter', 'Antimatter'):
            card.instance_flags.add('exile')
        amount = self._eval_int(player_id, params.get('amount', 10), card, 10)
        target_id = -1
        if isinstance(context, dict):
            try:
                target_id = int(context.get('target_player', context.get('target_id', -1)))
            except Exception:
                target_id = -1
        if not self._valid_player_id(target_id):
            try:
                target_id = self._selected_attack_target(player_id, choice)
            except Exception:
                target_id = -1
        if not self._valid_player_id(target_id):
            target_id = self._resolve_target(player_id, 'enemy')
        if not self._valid_player_id(target_id):
            return
        is_precision = 'precision' in self._effective_card_flags(card)
        amount = self._modified_attack_damage(amount, card)
        self.deal_attack_damage(target_id, amount, 1, is_precision=is_precision, attacker_id=player_id, source_card=card)

    def _atomic_void_damage_all_except_self(self, player_id, card, params, log, choice, context):
        amount = self._eval_int(player_id, params.get('amount', 25), card, 25)
        for target_id in range(len(self.players)):
            if target_id == player_id:
                continue
            if not self._target_can_be_selected(player_id, target_id, allow_self=False):
                continue
            self.deal_attack_damage(target_id, amount, 1, attacker_id=player_id, source_card=card)

    def _atomic_void_quantum_randomize(self, player_id, card, params, log, choice, context):
        max_cost = self._eval_int(player_id, params.get('max_cost', 3), card, 3)
        for hand_card in list(self.players[player_id].hand):
            if int(getattr(hand_card.card_def, 'cost_e', 0) or 0) <= max_cost:
                hand_card.cost_e_override = random.randint(0, max_cost)
        if log:
            self.log_msg(log)

    def _atomic_void_satan_swap(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        if not self._valid_player_id(target_id) or target_id == player_id:
            return
        a, b = self.players[player_id], self.players[target_id]
        a_h, a_e, a_m = a.health, a.elixir, a.magic
        b_h, b_e, b_m = b.health, b.elixir, b.magic
        a.health, a.elixir, a.magic = min(b_h, a.max_health), min(b_e, a.max_elixir), min(b_m, a.max_magic)
        b.health, b.elixir, b.magic = min(a_h, b.max_health), min(a_e, b.max_elixir), min(a_m, b.max_magic)
        self.log_msg(log or f"{self.pn(player_id)}与{self.pn(target_id)}交换了H/E/M")

    def _atomic_void_turn_count_damage(self, player_id, card, params, log, choice, context):
        base = self._eval_int(player_id, params.get('base', 6), card, 6)
        per = self._eval_int(player_id, params.get('per', 4), card, 4)
        played = getattr(self.players[player_id], 'cards_played_this_turn', {}) or {}
        count = max(0, sum(int(v or 0) for v in played.values()) - 1)
        amount = max(0, base + per * count)
        self._atomic_deal_damage(player_id, card, {'target': params.get('target', 'target'), 'amount': amount}, log, choice, context)

    def _atomic_void_magic_relativity_damage_end(self, player_id, card, params, log, choice, context):
        base = self._eval_int(player_id, params.get('base', 28), card, 28)
        per = self._eval_int(player_id, params.get('per', -5), card, -5)
        played = getattr(self.players[player_id], 'cards_played_this_turn', {}) or {}
        count = max(0, sum(int(v or 0) for v in played.values()) - 1)
        amount = max(0, base + per * count)
        self._atomic_deal_damage(player_id, card, {'target': params.get('target', 'target'), 'amount': amount}, log, choice, context)
        self.end_turn(player_id)

    def _atomic_void_exile_selected_card(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        zone = str(params.get('zone', 'hand'))
        selected = self._void_selected_card(target_id, zone, choice)
        if selected is None:
            self.log_msg(log or f"{self.pn(player_id)}没有选择可用的牌")
            return
        self._void_remove_card_from_zone(target_id, selected)
        self._put_card_in_exile(target_id, selected)
        add_def = params.get('add_def_id')
        if add_def:
            def_id = self._void_resolve_card_def_id(self._resolve_card_id_ref(player_id, add_def, card))
            if def_id in CARD_DEFS:
                new_card = CardInstance(def_id)
                self._apply_setup_modifiers_to_card(target_id, new_card)
                if zone == 'deck':
                    self._void_add_card_to_deck_random(target_id, new_card)
                else:
                    self.players[target_id].add_to_hand(new_card)
        if log:
            self.log_msg(log)

    def _atomic_void_add_temp_heavy_to_hand(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = max(0, self._eval_int(player_id, params.get('amount', 1), card, 1))
        prop = str(params.get('kind', 'e'))
        for hand_card in list(self.players[target_id].hand):
            if prop == 'm':
                hand_card.temp_magic_heavy_value = max(0, int(getattr(hand_card, 'temp_magic_heavy_value', 0) or 0)) + amount
                hand_card.instance_flags.add('temp_magic_heavy')
            else:
                hand_card.temp_heavy_value = max(0, int(getattr(hand_card, 'temp_heavy_value', 0) or 0)) + amount
                hand_card.instance_flags.add('temp_heavy')
        if log:
            self.log_msg(log)

    def _atomic_void_add_void_to_hand(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if not self._valid_player_id(target_id):
            return
        new_card = CardInstance(self._void_resolve_card_def_id('void:void') or ERROR_CARD_ID)
        self.players[target_id].add_to_hand(new_card)
        if log:
            self.log_msg(log)

    def _atomic_void_kitty_auto_play(self, player_id, card, params, log, choice, context):
        if not self._valid_player_id(player_id):
            return
        owner = self.players[player_id]
        if int(getattr(owner, 'skip_turn', 0) or 0) > 0 or int(getattr(owner, 'forced_skip_turn', 0) or 0) > 0:
            return
        candidates = [pid for pid in range(len(self.players)) if pid != player_id and self.players[pid].health > 0]
        if not candidates:
            return
        actor_id = random.choice(candidates)
        actor = self.players[actor_id]
        top_card = next((c for c in list(actor.deck) if self._card_selectable_by_action(c)), None)
        if top_card is None:
            return
        flags = self._effective_card_flags(top_card)
        target_id = -1
        if top_card.card_type == 'thorn':
            target_id = self._first_auto_attack_target(actor_id)
            if target_id < 0:
                return
        elif 'self_only' not in flags and (self._v2_play_requires_choice_target(top_card) or self._root_play_requires_owner_target(top_card)):
            target_id = self._first_auto_attack_target(actor_id)
            if target_id < 0:
                return
        if top_card not in actor.deck:
            return
        actor.deck.remove(top_card)
        actor.add_to_hand(top_card, trigger_enter_hand=False)
        auto_choice = {'target_player_id': target_id, 'target_player': target_id, 'target_id': target_id} if target_id >= 0 else {}
        self.log_msg(log or f"小猫使{self.pn(actor_id)}自动打出{top_card.name_cn}")
        previous_auto_actor = getattr(self, '_allow_out_of_turn_auto_play_for', None)
        previous_auto_choice = getattr(self, '_auto_resolve_choices_for', None)
        previous_auto_no_cost = getattr(self, '_auto_play_no_cost_for', None)
        self._allow_out_of_turn_auto_play_for = actor_id
        self._auto_resolve_choices_for = actor_id
        self._auto_play_no_cost_for = actor_id
        try:
            self.play_card(actor_id, top_card.instance_id, auto_choice)
        finally:
            self._allow_out_of_turn_auto_play_for = previous_auto_actor
            self._auto_resolve_choices_for = previous_auto_choice
            self._auto_play_no_cost_for = previous_auto_no_cost

    def _atomic_void_transform_own_cards(self, player_id, card, params, log, choice, context):
        ps = self.players[player_id]
        for zone in (ps.hand, ps.deck, ps.discard):
            for idx, old in enumerate(list(zone)):
                new_id = self._void_weighted_card_id(getattr(old.card_def, 'card_type', ''), exclude={getattr(old, 'def_id', '')})
                if not new_id:
                    continue
                new_card = CardInstance(new_id)
                self._apply_setup_modifiers_to_card(player_id, new_card)
                zone[idx] = new_card
        for eq in list(ps.equipment):
            new_id = self._void_weighted_card_id('root', exclude={getattr(eq, 'def_id', '')})
            if not new_id:
                continue
            armor = getattr(eq, 'armor', 0)
            target = getattr(eq, 'effect_target', player_id)
            eq.card_instance = CardInstance(new_id)
            eq.armor = armor
            flags = self._effective_card_flags(eq.card_instance)
            eq.effect_target = player_id if 'self_only' in flags else target
        self._refresh_hand_limit_bonuses()
        if log:
            self.log_msg(log)

    def _atomic_void_magic_corruption(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        if not self._valid_player_id(target_id):
            return
        new_card = CardInstance(self._void_resolve_card_def_id('Corruption') or self._void_resolve_card_def_id('vanilla:corruption') or ERROR_CARD_ID)
        eq = EquipmentInstance(new_card, target_id)
        eq.effect_target = target_id
        eq.corruption_active = True
        self.players[target_id].equipment.append(eq)
        if log:
            self.log_msg(log)

    def _atomic_void_soap_wide_strike(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        if not self._valid_player_id(target_id):
            return
        for zone in (self.players[target_id].hand, self.players[target_id].deck, self.players[target_id].discard):
            for target_card in zone:
                if getattr(target_card.card_def, 'card_type', '') == 'thorn':
                    target_card.instance_flags.add('wide_strike')
        if log:
            self.log_msg(log)

    def _atomic_void_magic_wing_damage(self, player_id, card, params, log, choice, context):
        extra_limit = max(0, self._eval_int(player_id, params.get('extra_limit', 4), card, 4))
        spend = min(extra_limit, int(getattr(self.players[player_id], 'magic', 0) or 0))
        if spend > 0:
            self._spend_resource(player_id, 'magic', spend, card)
        amount = self._eval_int(player_id, params.get('base', 4), card, 4) + spend * self._eval_int(player_id, params.get('per', 4), card, 4)
        self._atomic_deal_damage(player_id, card, {'target': params.get('target', 'target'), 'amount': amount}, log, choice, context)

    def _atomic_void_toggle_void_hand(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        if not self._valid_player_id(target_id):
            return
        for hand_card in list(self.players[target_id].hand):
            if 'void' in self._effective_card_flags(hand_card):
                hand_card.instance_flags.discard('void')
                hand_card.disabled_flags.add('void')
            else:
                hand_card.instance_flags.add('void')
                hand_card.disabled_flags.discard('void')
        if log:
            self.log_msg(log)

    def _atomic_void_set_void_all_cards(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        if not self._valid_player_id(target_id):
            return
        enabled = bool(params.get('enabled', True))
        ps = self.players[target_id]
        for zone in (ps.hand, ps.deck, ps.discard):
            for zone_card in list(zone):
                if enabled:
                    zone_card.instance_flags.add('void')
                    zone_card.disabled_flags.discard('void')
                else:
                    zone_card.instance_flags.discard('void')
                    zone_card.disabled_flags.add('void')
        if log:
            self.log_msg(log)

    def _atomic_void_scythe_damage(self, player_id, card, params, log, choice, context):
        base = self._eval_int(player_id, params.get('base', 40), card, 40)
        per = self._eval_int(player_id, params.get('per_hand', 5), card, 5)
        remaining = max(0, len(getattr(self.players[player_id], 'hand', []) or []))
        amount = max(0, base - per * remaining)
        self._atomic_deal_damage(player_id, card, {'target': params.get('target', 'target'), 'amount': amount}, log, choice, context)

    def _atomic_void_puppeteer(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        if not self._valid_player_id(target_id):
            return
        ps = self.players[target_id]
        ps.honey_control_turns = max(1, int(getattr(ps, 'honey_control_turns', 0) or 0) + 1)
        ps.custom_vars['void_puppeteer_damage_multiplier'] = max(float(ps.custom_vars.get('void_puppeteer_damage_multiplier', 1.0) or 1.0), 1.5)
        ps.custom_vars['honey_lowest_enemy'] = True
        if log:
            self.log_msg(log)

    def _atomic_sewers_lotus_heal(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        if not (0 <= target_id < len(self.players)):
            return
        target = self.players[target_id]
        amount = 5 + max(0, int(getattr(target, 'poison', 0) or 0)) * 2
        before = int(getattr(target, 'health', 0) or 0)
        target.heal(amount)
        healed = max(0, int(getattr(target, 'health', 0) or 0) - before)
        if healed > 0:
            self.log_msg(log or f"{self.pn(target_id)}回复{healed}H")

    def _atomic_sewers_activate_light_bulb(self, player_id, card, params, log, choice, context):
        if not (0 <= player_id < len(self.players)):
            return
        self.players[player_id].custom_vars['sewers_light_bulb_active'] = 1

    def _atomic_sewers_broccoli_attack(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        if not (0 <= target_id < len(self.players)):
            return
        target = self.players[target_id]
        dodge_before = max(0, int(getattr(target, 'dodge', 0) or 0))
        self.deal_attack_damage(target_id, 10, 1, attacker_id=player_id, source_card=card)
        dodge_after = max(0, int(getattr(target, 'dodge', 0) or 0))
        if dodge_after < dodge_before:
            self.deal_attack_damage(target_id, 3, 2, attacker_id=player_id, source_card=card)

    def _atomic_sewers_blood_rose(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        if not (0 <= target_id < len(self.players)):
            return
        dealt = self.deal_attack_damage(
            target_id,
            3,
            1,
            is_precision=True,
            attacker_id=player_id,
            source_card=card,
        )
        owner = self.players[player_id]
        before = int(getattr(owner, 'health', 0) or 0)
        owner.heal(max(0, int(dealt or 0)) * 4)
        healed = max(0, int(getattr(owner, 'health', 0) or 0) - before)
        if healed > 0:
            self.log_msg(f"{self.pn(player_id)}回复{healed}H")
        target = self.players[target_id]
        target.blind = max(0, int(getattr(target, 'blind', 0) or 0)) + 1
        self._normalize_status_value(target, 'blind')
        self._note_achievement_status_peak(target_id)
        if target.hand and not self._is_status_immune(target_id):
            random.shuffle(target.hand)
            self.log_msg(f"{self.pn(target_id)}因失明打乱手牌")

    def _atomic_hel_add_luck(self, player_id, card, params, log, choice, context):
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        for target_id in self._resolve_targets(player_id, params.get('target', 'self')):
            if not self._valid_player_id(target_id):
                continue
            self._hel_add_luck_value(target_id, amount)
            self.log_msg(log or f"{self.pn(target_id)}获得{amount}层幸运")

    def _atomic_hel_add_crit_multiplier(self, player_id, card, params, log, choice, context):
        amount = float(params.get('amount', 0.5) or 0.5)
        temporary = bool(params.get('temporary', False))
        for target_id in self._resolve_targets(player_id, params.get('target', 'target')):
            if not self._valid_player_id(target_id):
                continue
            ps = self.players[target_id]
            key = 'hel_crit_multiplier_turn_bonus' if temporary else 'hel_crit_multiplier_bonus'
            try:
                before = float(ps.custom_vars.get(key, 0) or 0)
            except Exception:
                before = 0.0
            ps.custom_vars[key] = before + amount
            self._hel_sync_crit_multiplier_display(target_id)
            self.log_msg(log or f"{self.pn(target_id)}暴击倍率+{amount:g}×")

    def _atomic_hel_apply_blazing_fire(self, player_id, card, params, log, choice, context):
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        for target_id in self._resolve_targets(player_id, params.get('target', 'target')):
            if self._valid_player_id(target_id):
                self._add_custom_status_value(target_id, 'hel:blazing_fire', amount)
                self.log_msg(log or f"{self.pn(target_id)}获得{amount}层烈火")

    def _hel_target_from_params(self, player_id, card, params, choice, context):
        target_id = -1
        if isinstance(context, dict):
            try:
                target_id = int(context.get('target_player', context.get('target_id', -1)))
            except Exception:
                target_id = -1
        if not self._valid_player_id(target_id):
            target_id = self._resolve_target(player_id, params.get('target', 'target'))
        return target_id

    def _atomic_hel_lucky_attack(self, player_id, card, params, log, choice, context):
        target_id = self._hel_target_from_params(player_id, card, params, choice, context)
        if not self._valid_player_id(target_id):
            return
        amount = self._eval_int(player_id, params.get('amount', 6), card, 6)
        hits = self._card_total_hits(card, self._eval_int(player_id, params.get('hits', 1), card, 1))
        is_precision = bool(params.get('is_precision')) or 'precision' in self._effective_card_flags(card)
        amount = self._modified_attack_damage(amount, card)
        prev_hits = getattr(self, '_hel_current_crit_hits', 0)
        self._hel_current_crit_hits = 0
        self._hel_last_hit_was_crit = False
        dealt = self.deal_attack_damage(target_id, amount, hits, is_precision=is_precision, attacker_id=player_id, source_card=card)
        crit_hits = int(getattr(self, '_hel_current_crit_hits', 0) or 0)
        self._hel_last_attack_crit_hits = crit_hits
        self._hel_current_crit_hits = prev_hits
        self._last_damage_value[target_id] = int(dealt)
        on_crit = params.get('on_crit')
        if crit_hits > 0 and isinstance(on_crit, list):
            child_context = dict(context or {})
            child_context.update({'event': 'on_crit', 'source_id': player_id, 'target_id': target_id, 'damage': int(dealt), 'crit_hits': crit_hits})
            self._run_effect_list(player_id, card, on_crit, choice, child_context)
        on_hit = params.get('on_hit')
        if dealt > 0 and isinstance(on_hit, list):
            hit_count = max(1, int((getattr(self, '_last_positive_damage_hits', []) or [0])[target_id] or 0))
            for hit_index in range(hit_count):
                child_context = dict(context or {})
                child_context.update({'event': 'on_hit', 'source_id': player_id, 'target_id': target_id, 'damage': int(dealt), 'hit_index': hit_index})
                self._run_effect_list(player_id, card, on_hit, choice, child_context)

    def _atomic_hel_card_attack(self, player_id, card, params, log, choice, context):
        suit = ''
        if isinstance(choice, dict):
            suit = str(choice.get('hel_suit') or '')
        if suit not in ('heart', 'diamond', 'spade', 'club'):
            suit = random.choice(['heart', 'diamond', 'spade', 'club'])
        if card is not None:
            card._hel_card_suit = suit
        self._atomic_hel_lucky_attack(player_id, card, params, log, choice, context)
        target_id = self._hel_target_from_params(player_id, card, params, choice, context)
        crit_hits = int(getattr(self, '_hel_last_attack_crit_hits', 0) or 0)
        if crit_hits > 0 and self._valid_player_id(target_id) and int(getattr(self, '_last_damage_value', [0] * len(self.players))[target_id] or 0) > 0:
            if suit == 'heart' and self.players[player_id].health < self.players[player_id].max_health / 2:
                self.players[player_id].heal(7)
                self.log_msg(f"{self.pn(player_id)}的纸牌♥回复7H")
            elif suit == 'spade':
                drawn = self.players[player_id].draw_cards(1)
                self.log_msg(f"{self.pn(player_id)}的纸牌♠抽{len(drawn)}张牌")
            elif suit == 'club':
                self.players[target_id].poison += 3
                self._normalize_status_value(self.players[target_id], 'poison')
                self.log_msg(f"{self.pn(target_id)}+3中毒")
        if card is not None and hasattr(card, '_hel_card_suit'):
            delattr(card, '_hel_card_suit')

    def _atomic_hel_chip_attack(self, player_id, card, params, log, choice, context):
        target_id = self._hel_target_from_params(player_id, card, params, choice, context)
        if not self._valid_player_id(target_id):
            return
        amount = self._eval_int(player_id, params.get('amount', 6), card, 6)
        old_no = getattr(card, '_hel_no_luck_crit', False) if card is not None else False
        if card is not None:
            card._hel_no_luck_crit = True
        dealt = self.deal_attack_damage(target_id, self._modified_attack_damage(amount, card), 1, attacker_id=player_id, source_card=card)
        if card is not None:
            card._hel_no_luck_crit = old_no
        if self._hel_luck_value(player_id) >= 3 and card is not None:
            card.instance_flags.add('return_to_hand')

    def _atomic_hel_blood_dice(self, player_id, card, params, log, choice, context):
        self._hel_add_luck_value(player_id, self._eval_int(player_id, params.get('luck', 12), card, 12))
        if card is not None:
            card._hel_force_crit = True
        self.deal_attack_damage(
            player_id,
            self._eval_int(player_id, params.get('self_damage', 6), card, 6),
            1,
            attacker_id=player_id,
            source_card=card,
        )
        if card is not None and hasattr(card, '_hel_force_crit'):
            delattr(card, '_hel_force_crit')
        self.log_msg(log or f"{self.pn(player_id)}获得12层幸运")

    def _atomic_hel_magic_dice_attack(self, player_id, card, params, log, choice, context):
        target_id = self._hel_target_from_params(player_id, card, params, choice, context)
        if not self._valid_player_id(target_id):
            return
        prev_hits = getattr(self, '_hel_current_crit_hits', 0)
        self._hel_current_crit_hits = 0
        dealt = self.deal_attack_damage(target_id, self._modified_attack_damage(6, card), 1, attacker_id=player_id, source_card=card)
        crit = int(getattr(self, '_hel_current_crit_hits', 0) or 0) > 0
        self._hel_current_crit_hits = prev_hits
        if crit:
            luck = self._custom_status_value(player_id, *self._hel_luck_keys())
            self._hel_set_luck_value(player_id, 0)
            if luck > 0:
                self._deal_direct_damage(target_id, luck * 2, '魔法骰子电伤', player_id, damage_type=DAMAGE_TYPE_MAGIC, damage_tag=DAMAGE_TAG_BATTERY)

    def _atomic_hel_trigger_fire_once(self, player_id, card, params, log, choice, context):
        target_id = self._hel_target_from_params(player_id, card, params, choice, context)
        if not self._valid_player_id(target_id):
            return
        ps = self.players[target_id]
        fire = max(0, int(getattr(ps, 'fire', 0) or 0))
        if fire > 0 and not self._is_status_immune(target_id):
            self._deal_direct_damage(target_id, fire, '灼烧', damage_type=DAMAGE_TYPE_MAGIC, damage_tag=DAMAGE_TAG_FIRE)
        if fire > 0:
            ps.fire = max(0, fire - self._eval_int(player_id, params.get('reduce', 1), card, 1))

    def _atomic_hel_magic_gunpowder(self, player_id, card, params, log, choice, context):
        target_id = self._hel_target_from_params(player_id, card, params, choice, context)
        if not self._valid_player_id(target_id):
            return
        amount = max(0, int(getattr(self.players[target_id], 'fire', 0) or 0))
        self.players[player_id].gain_magic(amount)
        self.log_msg(log or f"{self.pn(player_id)}回复{amount}M")

    def _atomic_hel_fire_by_equipment(self, player_id, card, params, log, choice, context):
        target_id = self._hel_target_from_params(player_id, card, params, choice, context)
        if not self._valid_player_id(target_id):
            return
        amount = 2 + len(getattr(self.players[target_id], 'equipment', []) or [])
        self.players[target_id].fire += amount
        self._normalize_status_value(self.players[target_id], 'fire')
        self.log_msg(log or f"{self.pn(target_id)}+{amount}层灼烧")

    def _atomic_hel_bugatti_draw(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'target'))
        if not self._valid_player_id(target_id):
            target_id = player_id
        drawn = self.players[target_id].draw_cards(self._eval_int(player_id, params.get('amount', 2), card, 2))
        self.log_msg(log or f"{self.pn(target_id)}因布加迪多抽{len(drawn)}张牌")

    def _atomic_hel_magic_clover_trigger(self, player_id, card, params, log, choice, context):
        eq = self._find_equipment_for_card(player_id, card)
        if eq is None or int(getattr(eq, 'turns_equipped', 0) or 0) < 1:
            self.log_msg(f"{self.pn(player_id)}的魔法幸运草还未成熟")
            return
        target_id = self._hel_target_from_params(player_id, card, params, choice, context)
        if not self._valid_player_id(target_id):
            return
        self.players[target_id].custom_vars['hel_crit_multiplier_turn_bonus'] = float(self.players[target_id].custom_vars.get('hel_crit_multiplier_turn_bonus', 0) or 0) + 1.0
        self._hel_sync_crit_multiplier_display(target_id)
        self._hel_add_luck_value(target_id, 8)
        self.log_msg(log or f"{self.pn(target_id)}本回合暴击倍率+1×并获得8层幸运")
        self._destroy_equipment(player_id, eq, check_protection=False)

    def _run_ocean_auto_cards_turn_start(self, player_id: int):
        if not self._valid_player_id(player_id):
            return
        ps = self.players[player_id]
        entries = ps.custom_vars.get('ocean_auto_cards')
        if not isinstance(entries, list) or not entries:
            return
        for entry in list(entries):
            if self.game_over or self.phase != 'action':
                break
            target_id = int(entry.get('target_id', -1))
            if not self._target_can_be_selected(player_id, target_id, allow_self=False):
                continue
            def_id = str(entry.get('def_id') or '')
            if def_id not in CARD_DEFS:
                continue
            card_data = entry.get('card') if isinstance(entry.get('card'), dict) else None
            temp_card = fresh_card_copy_from_dict(card_data, def_id) if card_data else CardInstance(def_id)
            temp_card.instance_flags.add('exile')
            temp_card.instance_flags.add('ocean_no_auto')
            temp_card.disabled_flags.add('rebound')
            if int(entry.get('swift_value', 0) or 0) > 0:
                temp_card.swift_value = int(entry.get('swift_value', 0) or 0)
                temp_card.instance_flags.add('swift')
            if int(entry.get('magic_swift_value', 0) or 0) > 0:
                temp_card.magic_swift_value = int(entry.get('magic_swift_value', 0) or 0)
                temp_card.instance_flags.add('magic_swift')
            if temp_card.cost_e > ps.elixir or temp_card.cost_m > ps.magic:
                continue
            ps.add_to_hand(temp_card, trigger_enter_hand=False)
            auto_choice = {'target_player_id': target_id, 'target_player': target_id, 'target_id': target_id}
            previous_auto_actor = getattr(self, '_allow_out_of_turn_auto_play_for', None)
            previous_auto_choice = getattr(self, '_auto_resolve_choices_for', None)
            self._allow_out_of_turn_auto_play_for = player_id
            self._auto_resolve_choices_for = player_id
            try:
                if len(getattr(self, 'players', []) or []) > 2:
                    result = self.play_card(player_id, temp_card.instance_id, target_id, auto_choice)
                else:
                    result = self.play_card(player_id, temp_card.instance_id, auto_choice)
            finally:
                self._allow_out_of_turn_auto_play_for = previous_auto_actor
                self._auto_resolve_choices_for = previous_auto_choice
            if temp_card in ps.hand and not result.get('needs_choice') and not result.get('needs_v2_ui'):
                ps.hand.remove(temp_card)
            if not result.get('success') and not result.get('needs_response') and not result.get('needs_choice') and not result.get('needs_v2_ui'):
                continue
            if self.pending_response is not None or self.pending_choice is not None or getattr(self, 'pending_v2_ui', None):
                break

    def _atomic_status_add_named(self, player_id, card, params, log, choice, context):
        status = str(params.get('status', '')).strip()
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            if self._status_application_blocked(tid, status):
                continue
            ps = self.players[tid]
            if status in ('poison', '中毒'):
                ps.poison += amount
            elif status in ('burn', 'fire', '灼烧'):
                ps.fire += amount
            elif status in ('toxic', '淬毒'):
                ps.toxic += amount
            elif status in ('dodge', '闪避'):
                ps.dodge += amount
            elif status in ('equip_protection', 'equipment_protection', '装备摧毁保护', '装备保护'):
                ps.equipment_protection += amount
            elif status in ('sluggish', '迟缓'):
                ps.sluggish += amount
            elif status in ('overload', '超载'):
                ps.overload += amount
            elif status in ('foresight', '预知'):
                ps.foresight += amount
            elif status in ('fracture', '破损'):
                ps.fracture += amount
            elif status in ('stagnation', '滞留'):
                ps.stagnation += amount
            elif status in ('blind', '失明'):
                ps.blind += amount
            elif status in ('heal_block', '禁疗'):
                ps.heal_block += amount
            elif status in ('attack_blocked', '禁攻'):
                ps.attack_blocked += amount
            elif status in ('weakness', '虚弱'):
                ps.weakness += amount
            elif status in ('bleed', '流血'):
                ps.bleed += amount
            elif status in ('fragment', 'fragment_stacks', '碎片'):
                ps.fragment_stacks += amount
            elif status in ('stunned', 'dizzy', 'skip_turn', '眩晕'):
                ps.skip_turn += amount
            elif status in self._unable_counter_keys():
                self._add_custom_status_value(tid, 'ocean:unable_counter', amount)
            elif status in ('邪眼', 'Nazar', 'nazar'):
                self._add_nazar_status_value(tid, amount)
            elif status in ('status_immune', 'immune', '状态免疫'):
                ps.custom_statuses = getattr(ps, 'custom_statuses', {})
                for key in ('status_immune', 'immune', '状态免疫'):
                    ps.custom_statuses.pop(key, None)
                if amount > 0:
                    ps.custom_statuses['status_immune'] = 1
            elif status:
                ps.custom_statuses = getattr(ps, 'custom_statuses', {})
                ps.custom_statuses[status] = int(ps.custom_statuses.get(status, 0) or 0) + amount
            self._normalize_status_value(ps, status)
            self._note_achievement_status_peak(tid)
            if status in self._unable_counter_keys():
                self._apply_unable_counter_to_current_hand(tid)

    def _atomic_status_remove_named(self, player_id, card, params, log, choice, context):
        status = str(params.get('status', '')).strip()
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            ps = self.players[tid]
            if status in ('poison', '中毒'):
                ps.poison = 0
            elif status in ('burn', 'fire', '灼烧'):
                ps.fire = 0
            elif status in ('toxic', '淬毒'):
                ps.toxic = 0
            elif status in ('dodge', '闪避'):
                ps.dodge = 0
            elif status in ('equip_protection', 'equipment_protection', '装备摧毁保护', '装备保护'):
                ps.equipment_protection = 0
            elif status in ('sluggish', '迟缓'):
                ps.sluggish = 0
            elif status in ('overload', '超载'):
                ps.overload = 0
            elif status in ('foresight', '预知'):
                ps.foresight = 0
            elif status in ('fracture', '破损'):
                ps.fracture = 0
            elif status in ('stagnation', '滞留'):
                ps.stagnation = 0
            elif status in ('blind', '失明'):
                ps.blind = 0
            elif status in ('heal_block', '禁疗'):
                ps.heal_block = 0
            elif status in ('weakness', '虚弱'):
                ps.weakness = 0
            elif status in ('bleed', '流血'):
                ps.bleed = 0
            elif status in ('fragment', 'fragment_stacks', '碎片'):
                ps.fragment_stacks = 0
            elif status in ('stunned', 'dizzy', 'skip_turn', '眩晕'):
                ps.skip_turn = 0
            elif status in self._unable_counter_keys():
                for key in self._unable_counter_keys():
                    self._set_custom_status_value(tid, key, 0)
            elif status in ('邪眼', 'Nazar', 'nazar'):
                self._set_nazar_status_value(tid, 0)
            elif status in ('status_immune', 'immune', '状态免疫'):
                ps.custom_statuses = getattr(ps, 'custom_statuses', {})
                for key in ('status_immune', 'immune', '状态免疫'):
                    ps.custom_statuses.pop(key, None)
            elif status:
                ps.custom_statuses = getattr(ps, 'custom_statuses', {})
                ps.custom_statuses.pop(status, None)

    def _sync_custom_var_alias(self, ps, name: str):
        try:
            value = int(self._scalar_value(ps.custom_vars.get(name, 0), 0))
        except Exception:
            value = 0
        if name == '\u4e09\u89d2\u5f62\u5c42\u6570':
            ps.triangle_stacks = max(0, value)
        elif name == '\u5496\u5561\u9996\u6b21\u4f7f\u7528':
            ps.coffee_first_use = bool(value)

    def _atomic_var_set(self, player_id, card, params, log, choice, context):
        for target_ref in self._var_target_refs(player_id, params.get('target', 'self')):
            store = self._var_store_for_target(player_id, target_ref)
            name = str(params.get('name', 'var'))
            if isinstance(target_ref, int) and self._is_suppressed_status_var(target_ref, name):
                continue
            store[name] = self._eval_var_assignment_value(player_id, params.get('value', 0), card)
            if isinstance(target_ref, int):
                self._sync_custom_var_alias(self.players[target_ref], name)

    def _atomic_var_add(self, player_id, card, params, log, choice, context):
        for target_ref in self._var_target_refs(player_id, params.get('target', 'self')):
            store = self._var_store_for_target(player_id, target_ref)
            name = str(params.get('name', 'var'))
            if isinstance(target_ref, int) and self._is_suppressed_status_var(target_ref, name):
                continue
            store[name] = int(self._scalar_value(store.get(name, 0), 0)) + self._eval_int(player_id, params.get('value', 0), card)
            if isinstance(target_ref, int):
                self._sync_custom_var_alias(self.players[target_ref], name)

    def _atomic_var_sub(self, player_id, card, params, log, choice, context):
        for target_ref in self._var_target_refs(player_id, params.get('target', 'self')):
            store = self._var_store_for_target(player_id, target_ref)
            name = str(params.get('name', 'var'))
            if isinstance(target_ref, int) and self._is_suppressed_status_var(target_ref, name):
                continue
            store[name] = int(self._scalar_value(store.get(name, 0), 0)) - self._eval_int(player_id, params.get('value', 0), card)
            if isinstance(target_ref, int):
                self._sync_custom_var_alias(self.players[target_ref], name)

    def _atomic_var_mul(self, player_id, card, params, log, choice, context):
        for target_ref in self._var_target_refs(player_id, params.get('target', 'self')):
            store = self._var_store_for_target(player_id, target_ref)
            name = str(params.get('name', 'var'))
            if isinstance(target_ref, int) and self._is_suppressed_status_var(target_ref, name):
                continue
            store[name] = int(self._scalar_value(store.get(name, 0), 0)) * self._eval_int(player_id, params.get('value', 1), card, 1)
            if isinstance(target_ref, int):
                self._sync_custom_var_alias(self.players[target_ref], name)

    def _atomic_var_div(self, player_id, card, params, log, choice, context):
        for target_ref in self._var_target_refs(player_id, params.get('target', 'self')):
            store = self._var_store_for_target(player_id, target_ref)
            name = str(params.get('name', 'var'))
            if isinstance(target_ref, int) and self._is_suppressed_status_var(target_ref, name):
                continue
            div = self._eval_int(player_id, params.get('value', 1), card, 1)
            current = int(self._scalar_value(store.get(name, 0), 0))
            store[name] = current if div == 0 else current // div
            if isinstance(target_ref, int):
                self._sync_custom_var_alias(self.players[target_ref], name)

    def _atomic_list_set(self, player_id, card, params, log, choice, context):
        for target_ref in self._var_target_refs(player_id, params.get('target', 'self')):
            store = self._var_store_for_target(player_id, target_ref)
            store[str(params.get('name', 'list'))] = [self._serializable_list_item(v) for v in self._eval_list(player_id, params.get('list', []), card)]

    def _atomic_list_append(self, player_id, card, params, log, choice, context):
        for target_ref in self._var_target_refs(player_id, params.get('target', 'self')):
            store = self._var_store_for_target(player_id, target_ref)
            name = str(params.get('name', 'list'))
            current = store.get(name, [])
            if not isinstance(current, list):
                current = [] if current is None else [current]
            current.append(self._serializable_list_item(self._eval_raw_item(player_id, params.get('item', 0), card)))
            store[name] = current

    def _atomic_list_insert(self, player_id, card, params, log, choice, context):
        for target_ref in self._var_target_refs(player_id, params.get('target', 'self')):
            store = self._var_store_for_target(player_id, target_ref)
            name = str(params.get('name', 'list'))
            current = store.get(name, [])
            if not isinstance(current, list):
                current = [] if current is None else [current]
            index = max(0, min(len(current), self._eval_int(player_id, params.get('index', 1), card, 1) - 1))
            current.insert(index, self._serializable_list_item(self._eval_raw_item(player_id, params.get('item', 0), card)))
            store[name] = current

    def _atomic_list_delete(self, player_id, card, params, log, choice, context):
        for target_ref in self._var_target_refs(player_id, params.get('target', 'self')):
            store = self._var_store_for_target(player_id, target_ref)
            name = str(params.get('name', 'list'))
            current = store.get(name, [])
            if not isinstance(current, list):
                current = [] if current is None else [current]
            index = self._eval_int(player_id, params.get('index', 1), card, 1) - 1
            if 0 <= index < len(current):
                current.pop(index)
            store[name] = current

    def _atomic_list_clear(self, player_id, card, params, log, choice, context):
        for target_ref in self._var_target_refs(player_id, params.get('target', 'self')):
            self._var_store_for_target(player_id, target_ref)[str(params.get('name', 'list'))] = []

    def _atomic_for_each_list(self, player_id, card, params, log, choice, context):
        name = str(params.get('name', 'item'))
        body = params.get('body', [])
        store = self._var_store_for_target(player_id, params.get('target', 'self'))
        had_old = name in store
        old_value = store.get(name)
        base_context = context if isinstance(context, dict) else ({'context': context} if context else {})
        try:
            for index, item in enumerate(self._eval_list(player_id, params.get('list', []), card), start=1):
                store[name] = self._serializable_list_item(item)
                try:
                    self._run_effect_list(player_id, card, body, choice, {**base_context, 'list_index': index})
                except ModLoopContinue:
                    continue
                except ModLoopBreak:
                    break
        finally:
            if had_old:
                store[name] = old_value
            else:
                store.pop(name, None)

    def _equipment_matches_loop_filter(self, player_id, eq, params, card):
        loop_filter = str(params.get('filter', 'all') or 'all')
        if loop_filter in ('all', 'any'):
            return True
        if loop_filter in ('destroyable', 'can_destroy'):
            return 'indestructible' not in eq.card_instance.flags
        if loop_filter in ('indestructible', 'cannot_destroy'):
            return 'indestructible' in eq.card_instance.flags
        if loop_filter in ('named', 'card_id'):
            expected = ''
            selector = params.get('card')
            if selector is not None:
                expected = self._resolve_card_id_ref(player_id, selector, card)
            expected = expected or str(params.get('card_id', '') or '')
            return bool(expected) and eq.def_id == expected
        if loop_filter in ('current_target', 'effect_target'):
            target_id = self._resolve_target(player_id, params.get('effect_target', params.get('target', 'self')))
            return getattr(eq, 'effect_target', getattr(eq, 'owner', -1)) == target_id
        return True

    def _atomic_for_each_equipment(self, player_id, card, params, log, choice, context):
        body = params.get('body', []) or []
        targets = self._resolve_targets(player_id, params.get('target', 'self'))
        previous_selected = (context or {}).get('selected_equipment_instance_id') if isinstance(context, dict) else None
        loop_items = []
        for target_id in targets:
            if not (0 <= target_id < len(self.players)):
                continue
            for eq in list(self.players[target_id].equipment):
                if self._equipment_matches_loop_filter(player_id, eq, params, card):
                    loop_items.append((target_id, eq))
        try:
            for index, (owner_id, eq) in enumerate(loop_items, start=1):
                loop_context = {
                    **(context or {}),
                    'selected_equipment_instance_id': eq.card_instance.instance_id,
                    'selected_equipment_owner_id': owner_id,
                    'equipment_index': index,
                }
                try:
                    self._run_effect_list(player_id, card, body, choice, loop_context)
                except ModLoopContinue:
                    continue
                except ModLoopBreak:
                    break
        finally:
            if isinstance(context, dict) and previous_selected is not None:
                context['selected_equipment_instance_id'] = previous_selected

    def _atomic_batch_var_add(self, player_id, card, params, log, choice, context):
        for tid in self._resolve_targets(player_id, params.get('targets', 'friendly')):
            self._atomic_var_add(player_id, card, {'target': tid, 'name': params.get('name', 'var'), 'value': params.get('value', 0)}, log, choice, context)

    def _atomic_batch_var_sub(self, player_id, card, params, log, choice, context):
        for tid in self._resolve_targets(player_id, params.get('targets', 'friendly')):
            self._atomic_var_sub(player_id, card, {'target': tid, 'name': params.get('name', 'var'), 'value': params.get('value', 0)}, log, choice, context)

    def _atomic_batch_var_mul(self, player_id, card, params, log, choice, context):
        for tid in self._resolve_targets(player_id, params.get('targets', 'friendly')):
            self._atomic_var_mul(player_id, card, {'target': tid, 'name': params.get('name', 'var'), 'value': params.get('value', 1)}, log, choice, context)

    def _atomic_batch_var_div(self, player_id, card, params, log, choice, context):
        for tid in self._resolve_targets(player_id, params.get('targets', 'friendly')):
            self._atomic_var_div(player_id, card, {'target': tid, 'name': params.get('name', 'var'), 'value': params.get('value', 1)}, log, choice, context)

    def use_trigger(self, player_id: int, equipment_instance_id: int, target_player_id: int = -1) -> dict:
        if self.current_player != player_id:
            return {'success': False, 'error': '不是你的回合'}
        ps = self.players[player_id]
        eq = ps.find_equipment(equipment_instance_id)
        if eq is None:
            return {'success': False, 'error': '装备不存在'}
        has_mod_trigger = self._has_card_event(eq.card_def, 'equipment_trigger')
        if eq.card_def.trigger_cost_e < 0 and not has_mod_trigger:
            return {'success': False, 'error': '该装备没有触发效果'}
        if eq.turns_equipped < 1:
            return {'success': False, 'error': '装备需要装备一回合后才能触发'}
        trigger_cost = max(0, int(eq.card_def.trigger_cost_e or 0))
        trigger_cost_m = max(0, int(getattr(eq.card_def, 'trigger_cost_m', 0) or eq.card_def.v2_resource.get('trigger_cost_m', 0) or 0))
        if trigger_cost > ps.elixir:
            return {'success': False, 'error': '能量不足'}
        if trigger_cost_m > ps.magic:
            return {'success': False, 'error': '魔力不足'}
        max_uses = self._equipment_trigger_max_uses(eq)
        if max_uses > 0 and int(getattr(eq, 'uses_this_turn', 0)) >= max_uses:
            return {'success': False, 'error': f'该装备本回合最多触发{max_uses}次'}
        try:
            target_id = int(target_player_id)
        except Exception:
            target_id = -1
        if not (0 <= target_id < len(self.players)):
            target_id = 1 - player_id
        if not self._target_can_be_selected(player_id, target_id, allow_self=True):
            return {'success': False, 'error': '没有可选中的玩家'}
        if self._equipment_trigger_forbids_self_target(eq.card_def) and target_id == player_id:
            return {'success': False, 'error': '不能选择自己作为目标'}
        self._spend_resource(player_id, 'elixir', trigger_cost, eq.card_instance)
        self._spend_resource(player_id, 'magic', trigger_cost_m, eq.card_instance)
        eq.uses_this_turn = int(getattr(eq, 'uses_this_turn', 0)) + 1
        self._log_equipment_trigger(player_id, eq)
        choice = {'target_player': target_id, 'target_player_id': target_id, 'target_id': target_id}
        if has_mod_trigger and self._run_card_event(player_id, eq.card_instance, 'equipment_trigger', choice,
                                                    {'source_id': player_id, 'target_id': target_id}):
            self._dispatch_card_event('equipment_triggered', player_id, eq.card_instance,
                                      target_id=target_id, equipment=eq, equipment_owner_id=player_id)
            self._check_game_over()
            return {'success': True, 'target_player_id': target_id}
        opp_id = target_id
        if eq.def_id == 'Leaf':
            if self._destroy_equipment(player_id, eq, check_protection=False):
                self.deal_attack_damage(opp_id, 8)
        elif eq.def_id == 'Mark':
            if self._destroy_equipment(player_id, eq, check_protection=False):
                if not self._status_application_blocked(opp_id, 'skip_turn'):
                    self.players[opp_id].skip_turn += 1
        elif eq.def_id == 'Mine':
            if self._destroy_equipment(player_id, eq, check_protection=False):
                self.deal_attack_damage(opp_id, 20)
        self._dispatch_card_event('equipment_triggered', player_id, eq.card_instance,
                                  target_id=opp_id, equipment=eq, equipment_owner_id=player_id)
        self._check_game_over()
        return {'success': True, 'target_player_id': target_id}

