import random
import math
import json
from typing import List, Dict, Optional, Tuple, Set
from engine_runtime_ext import install_runtime_ext
from cards import (
    CardDef, CardInstance, CARD_DEFS, DRAFT_RATIO, DRAFT_REROLLS,
    HAND_LIMIT, DRAW_PER_TURN, ELIXIR_RECOVERY, BASE_MAX_HEALTH,
    BASE_MAX_ELIXIR, BASE_MAX_MAGIC, INITIAL_HEALTH, INITIAL_ELIXIR,
    INITIAL_MAGIC, FIRST_PLAYER_ELIXIR, SECOND_PLAYER_HEALTH,
    DECK_SIZE, INITIAL_HAND_SIZE, FIRST_PLAYER_HAND_SIZE, build_draft_pool, generate_draft_options,
    create_deck_from_draft, ERROR_CARD_ID,
)
from runtime_errors import MOD_RUNTIME_ERROR_MESSAGE, record_mod_runtime_error


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
        return ei


def reset_card_for_discard(card: CardInstance):
    card.mimic_discount = 0
    if card.card_type == 'thorn':
        card.fission_level = 1
        card.fusion_level = 1
        card.fission_count = 0
        card.fusion_multiplier = 1.0
        card.fission_hit = 0
        if card.def_id == 'Tomato':
            card.bonus_damage = 0
            card.held_turns = 0


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
        self.vulnerable: int = 0
        self.toxic: int = 0
        self.triangle_stacks: int = 0
        self.dodge: int = 0
        self.nazar_active: bool = False
        self.nazar_big_hits: int = 0
        self.equipment_protection: int = 0
        self.magic_battery_m_this_turn: int = 0
        self.coffee_first_use: bool = True
        self.invincible: bool = False
        self.skip_turn: bool = False
        self.damage_multiplier: float = 1.0
        self.bandage_active: bool = False
        self.bandage_death_pending: bool = False
        self.attack_blocked: int = 0
        self.untargetable: bool = False
        self.sponge_active: bool = False
        self.shovel_active: bool = False
        self.attack_only: int = 0
        self.enemy_draw_reduction: int = 0
        self.enemy_e_reduction: int = 0
        self.hand: List[CardInstance] = []
        self.deck: List[CardInstance] = []
        self.discard: List[CardInstance] = []
        self.exile: List[CardInstance] = []
        self.equipment: List[EquipmentInstance] = []
        self.extra_hand_limit_bonus: int = 0
        self.cards_played_this_turn: Dict[str, int] = {}
        self.turn_damage_taken: int = 0
        self.turn_damage_dealt: int = 0
        self.total_damage_taken: int = 0
        self.total_damage_dealt: int = 0
        self.custom_vars: Dict[str, int] = {
            '\u5496\u5561\u9996\u6b21\u4f7f\u7528': 1,
            '\u4e09\u89d2\u5f62\u5c42\u6570': 0,
            '\u9b54\u6cd5\u7535\u6c60\u672c\u56de\u5408\u56de\u9b54': 0,
        }
        self.custom_statuses: Dict[str, int] = {}
        self.negate_next_skill: bool = False
        self.is_first_player: bool = False
        self._enter_hand_callback = None

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
            'vulnerable': self.vulnerable,
            'toxic': self.toxic,
            'triangle_stacks': self.triangle_stacks,
            'dodge': self.dodge,
            'nazar_active': self.nazar_active,
            'nazar_big_hits': self.nazar_big_hits,
            'equipment_protection': self.equipment_protection,
            'invincible': self.invincible,
            'skip_turn': self.skip_turn,
            'damage_multiplier': self.damage_multiplier,
            'bandage_active': self.bandage_active,
            'bandage_death_pending': self.bandage_death_pending,
            'attack_blocked': self.attack_blocked,
            'untargetable': self.untargetable,
            'sponge_active': self.sponge_active,
            'shovel_active': self.shovel_active,
            'attack_only': self.attack_only,
            'enemy_draw_reduction': self.enemy_draw_reduction,
            'enemy_e_reduction': self.enemy_e_reduction,
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
            'total_damage_taken': self.total_damage_taken,
            'total_damage_dealt': self.total_damage_dealt,
            'custom_statuses': dict(self.custom_statuses),
        }
        if include_private:
            d['hand'] = [c.to_dict() for c in self.hand]
            d['deck'] = [c.to_dict() for c in self.deck]
            d['discard'] = [c.to_dict() for c in self.discard]
            d['exile'] = [c.to_dict() for c in self.exile]
            d['cards_played_this_turn'] = dict(self.cards_played_this_turn)
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
        ps.vulnerable = d['vulnerable']
        ps.toxic = d.get('toxic', 0)
        ps.triangle_stacks = d.get('triangle_stacks', 0)
        ps.dodge = d.get('dodge', 0)
        ps.nazar_active = d.get('nazar_active', False)
        ps.nazar_big_hits = d.get('nazar_big_hits', 0)
        ps.equipment_protection = d.get('equipment_protection', 0)
        ps.invincible = d.get('invincible', False)
        ps.skip_turn = d.get('skip_turn', False)
        ps.damage_multiplier = d.get('damage_multiplier', 1.0)
        ps.bandage_active = d.get('bandage_active', False)
        ps.bandage_death_pending = d.get('bandage_death_pending', False)
        ps.attack_blocked = d.get('attack_blocked', 0)
        ps.untargetable = d.get('untargetable', False)
        ps.sponge_active = d.get('sponge_active', False)
        ps.shovel_active = d.get('shovel_active', False)
        ps.attack_only = d.get('attack_only', 0)
        ps.enemy_draw_reduction = d.get('enemy_draw_reduction', 0)
        ps.enemy_e_reduction = d.get('enemy_e_reduction', 0)
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
        ps.turn_damage_taken = int(d.get('turn_damage_taken', 0))
        ps.turn_damage_dealt = int(d.get('turn_damage_dealt', 0))
        ps.total_damage_taken = int(d.get('total_damage_taken', 0))
        ps.total_damage_dealt = int(d.get('total_damage_dealt', 0))
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
        return HAND_LIMIT + own_golden_leaf + max(0, int(getattr(self, 'extra_hand_limit_bonus', 0)))

    def rule_hand_size(self) -> int:
        return sum(1 for c in self.hand if c.def_id != ERROR_CARD_ID)

    def can_add_to_hand(self) -> bool:
        return self.rule_hand_size() < self.hand_limit()

    def hand_space(self) -> int:
        return max(0, self.hand_limit() - self.rule_hand_size())

    def add_to_hand(self, card: CardInstance):
        self.hand.append(card)
        callback = getattr(self, '_enter_hand_callback', None)
        if callback:
            callback(self.player_id, card)

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
        return drawn

    def heal(self, amount: int):
        self.health = min(self.health + amount, self.base_max_health)

    def gain_elixir(self, amount: int):
        self.elixir = min(self.elixir + amount, self.max_elixir)

    def gain_magic(self, amount: int):
        self.magic = min(self.magic + amount, self.max_magic)


class GameEngine:
    OPENING_EVENTS = {
        1: {'id': 1, 'name': '生命强化', 'desc': '最大生命值+20', 'position': 1},
        2: {'id': 2, 'name': '魔力转化', 'desc': '选择1-3张牌，分别选择魔法牌转化，开局回复5M', 'position': 2},
        3: {'id': 3, 'name': '光之洗礼', 'desc': '将最多五张牌转化为Light（萌芽、共生）', 'position': 2},
        8: {'id': 8, 'name': '绝境求生', 'desc': '最大生命值-20，将一张牌变化为世界树之叶', 'position': 2},
        4: {'id': 4, 'name': '烈焰预兆', 'desc': '开局对所有敌方玩家施加2层灼烧', 'position': 3},
        5: {'id': 5, 'name': '命运抽签', 'desc': '前二回合开始时抽牌至手牌已满', 'position': 3},
        6: {'id': 6, 'name': '能量涌动', 'desc': '前三回合开始时额外回复2E', 'position': 3},
        7: {'id': 7, 'name': '先手压制', 'desc': '必定先手，先手多回复3E并抽4张牌', 'position': 3},
    }
    MAGIC_CARD_POOL = ['MagicBone', 'MagicStinger', 'MagicSewage', 'MagicNazar', 'MagicBubble']

    _EFFECT_ALIASES = {
        'damage': 'deal_damage',
        'damage_multi': 'deal_damage_multi',
        'poison': 'apply_poison',
        'burn': 'apply_burn',
        'vulnus': 'apply_vulnerable',
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
    }

    def _resolve_target(self, player_id, target_str):
        if not target_str or target_str == 'self':
            return player_id
        elif target_str == 'enemy':
            return 1 - player_id
        elif target_str == 'both':
            return -1
        elif target_str == 'random':
            return random.choice([player_id, 1 - player_id])
        return player_id

    def _resolve_targets(self, player_id, target_str):
        if target_str in ('both', 'random_side'):
            return [0, 1]
        if target_str in ('friendly', 'self', None, ''):
            return [player_id]
        if target_str == 'teammate':
            return [player_id]
        if target_str == 'enemy':
            return [1 - player_id]
        if target_str == 'random_friendly':
            return [player_id]
        if target_str == 'random_enemy':
            return [1 - player_id]
        if target_str == 'random_player':
            return [random.choice([0, 1])]
        rid = self._resolve_target(player_id, target_str)
        if rid == -1:
            return [0, 1]
        return [rid]

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
        return 0

    def _get_status_count(self, target_id, status):
        if target_id < 0:
            return sum(self._get_status_count(pid, status) for pid in range(len(self.players)))
        if not (0 <= target_id < len(self.players)):
            return 0
        ps = self.players[target_id]
        status = str(status or '').strip()
        counts = {
            'poison': ps.poison,
            '中毒': ps.poison,
            'burn': ps.fire,
            'fire': ps.fire,
            '灼烧': ps.fire,
            'vulnus': ps.vulnerable,
            'vulnerable': ps.vulnerable,
            '易伤': ps.vulnerable,
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
            'untargetable': 1 if ps.untargetable else 0,
            '不可选中': 1 if ps.untargetable else 0,
            '邪眼': ps.nazar_big_hits if ps.nazar_active else 0,
            'Nazar': ps.nazar_big_hits if ps.nazar_active else 0,
        }
        if status in counts:
            return int(counts.get(status, 0))
        return int(getattr(ps, 'custom_statuses', {}).get(status, 0) or 0)

    def _custom_status_definition(self, status):
        status = str(status or '').strip()
        if not status:
            return None
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
        elif status in ('vulnus', 'vulnerable', '易伤'):
            ps.vulnerable = max(0, int(ps.vulnerable))
        elif status in ('toxic', '淬毒'):
            ps.toxic = max(0, int(ps.toxic))
        elif status in ('dodge', '闪避'):
            ps.dodge = max(0, int(ps.dodge))
        elif status in ('equip_protection', 'equipment_protection', '装备摧毁保护', '装备保护'):
            ps.equipment_protection = max(0, int(ps.equipment_protection))
        elif status in ('邪眼', 'Nazar'):
            if int(ps.nazar_big_hits) <= 0:
                ps.nazar_big_hits = 0
                ps.nazar_active = False
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

    def _record_damage(self, target_id, amount, source_id=None):
        try:
            amount = int(amount)
        except Exception:
            amount = 0
        if amount <= 0:
            return
        if 0 <= target_id < len(self.players):
            target = self.players[target_id]
            target.turn_damage_taken += amount
            target.total_damage_taken += amount
        if isinstance(source_id, int) and 0 <= source_id < len(self.players):
            source = self.players[source_id]
            source.turn_damage_dealt += amount
            source.total_damage_dealt += amount

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
        if prop in ('dodge', 'poison', 'fire', 'vulnerable', 'toxic', 'equipment_protection',
                    'attack_blocked', 'attack_only', 'enemy_draw_reduction', 'enemy_e_reduction',
                    'nazar_big_hits'):
            return int(getattr(ps, prop, 0))
        if prop in ('invincible', 'untargetable', 'bandage_active', 'sponge_active', 'shovel_active',
                    'skip_turn', 'negate_next_skill', 'nazar_active'):
            return 1 if bool(getattr(ps, prop, False)) else 0
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
        if prop in ('turn_damage_taken', 'turn_damage_dealt', 'total_damage_taken', 'total_damage_dealt'):
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
            'poison', 'fire', 'vulnerable', 'toxic', 'equipment_protection',
            'attack_blocked', 'attack_only', 'enemy_draw_reduction', 'enemy_e_reduction',
            'nazar_big_hits', 'extra_hand_limit_bonus', 'hand_limit_bonus',
        }
        bool_props = {
            'invincible', 'untargetable', 'bandage_active', 'sponge_active', 'shovel_active',
            'skip_turn', 'negate_next_skill', 'nazar_active',
        }
        if prop in non_negative:
            if prop == 'hand_limit_bonus':
                prop = 'extra_hand_limit_bonus'
            if prop == 'max_energy':
                prop = 'max_elixir'
            setattr(ps, prop, max(0, value))
            if prop == 'max_health':
                ps.base_max_health = ps.max_health
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
        self.halve_next_attack: bool = False
        self.game_over: bool = False
        self.winner: int = -1
        self._game_over_defer_depth: int = 0
        self.negated_card: bool = False
        self._yggdrasil_check: bool = True
        self._antenna_reveal: List[Optional[list]] = [None, None]
        self.opening_event_options: List[List[dict]] = [[], []]
        self.opening_event_picks: List[Optional[int]] = [None, None]
        self.opening_event_sub_choices: List[Optional[dict]] = [None, None]
        self.opening_event_magic_options: List[List[List[str]]] = [[[], [], []], [[], [], []]]
        self.player_names: List[str] = ['玩家1', '玩家2']
        self.debug_selector_log: bool = False
        self._last_damage_value: List[int] = [0, 0]
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
        self.log.append(msg)

    def _bind_player_callbacks(self):
        for ps in getattr(self, 'players', []):
            ps._enter_hand_callback = self._handle_card_enter_hand

    def _handle_card_enter_hand(self, player_id: int, card: CardInstance):
        if not (0 <= player_id < len(getattr(self, 'players', []))):
            return
        if not self._has_card_event(card.card_def, 'enter_hand'):
            return
        self._run_card_event(player_id, card, 'enter_hand', None, {
            'source_id': player_id,
            'target_id': player_id,
            'zone': 'hand',
        })

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

    def _visible_card_dicts(self, cards, viewer_id: int, owner_id: int):
        return [
            c.to_dict() for c in cards
            if owner_id == viewer_id or c.def_id != ERROR_CARD_ID
        ]

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
        opponent = 1 - for_player
        opp_data = self.players[opponent].to_dict(include_private=False)
        opp_data['hand_count'] = len([c for c in self.players[opponent].hand if c.def_id != ERROR_CARD_ID])
        opp_data['deck_count'] = len([c for c in self.players[opponent].deck if c.def_id != ERROR_CARD_ID])
        opp_data['discard_count'] = len([c for c in self.players[opponent].discard if c.def_id != ERROR_CARD_ID])
        opp_data['exile_count'] = len([c for c in self.players[opponent].exile if c.def_id != ERROR_CARD_ID])
        if self.pending_choice and self.pending_choice.get('player_id') == for_player:
            ct = self.pending_choice.get('choice_type', '')
            if ct in ('choose_from_enemy_hand',):
                opp_data['hand'] = self._visible_card_dicts(self.players[opponent].hand, for_player, opponent)
            target_id = self.pending_choice.get('target_player_id')
            params = self.pending_choice.get('choice_params', {}) or {}
            if target_id == opponent and ct in ('choose_card_from_hand', 'choose_from_deck', 'choose_from_discard', 'choose_from_exile', 'choose_equipment'):
                zone = params.get('zone', '')
                if ct == 'choose_card_from_hand' or zone == 'hand':
                    opp_data['hand'] = self._visible_card_dicts(self.players[opponent].hand, for_player, opponent)
                if ct == 'choose_from_deck' or zone == 'deck':
                    opp_data['deck'] = self._visible_card_dicts(self.players[opponent].deck, for_player, opponent)
                if ct == 'choose_from_discard' or zone == 'discard':
                    opp_data['discard'] = self._visible_card_dicts(self.players[opponent].discard, for_player, opponent)
                if ct == 'choose_from_exile' or zone == 'exile':
                    opp_data['exile'] = self._visible_card_dicts(self.players[opponent].exile, for_player, opponent)
        if self._antenna_reveal[for_player]:
            opp_data['revealed_hand'] = self._visible_card_dicts(self.players[opponent].hand, for_player, opponent)
        log_start = 0
        return {
            'phase': self.phase,
            'current_player': self.current_player,
            'round_num': self.round_num,
            'game_over': self.game_over,
            'winner': self.winner,
            'you': self.players[for_player].to_dict(include_private=True),
            'opponent': opp_data,
            'log': list(self.log),
            'log_start': log_start,
            'log_total': len(self.log),
            'pending_response': self.pending_response,
            'pending_choice': self.pending_choice,
            'opening_event_picks': self.opening_event_picks,
            'antenna_reveal': self._antenna_reveal[for_player],
        }

    def start_draft(self):
        self.phase = 'draft'
        self.draft_pool = build_draft_pool(self.allowed_card_ids)
        self.draft_picks = [[], []]
        self.draft_rerolls = [DRAFT_REROLLS, DRAFT_REROLLS]
        self.draft_round = 0
        self.draft_type_order = []
        for card_type, count in DRAFT_RATIO.items():
            self.draft_type_order.extend([card_type] * count)
        random.shuffle(self.draft_type_order)
        self._generate_draft_options_for_player(0)
        self._generate_draft_options_for_player(1)

    def _generate_draft_options_for_player(self, player_id: int):
        if len(self.draft_picks[player_id]) >= DECK_SIZE:
            if len(self.draft_picks[0]) >= DECK_SIZE and len(self.draft_picks[1]) >= DECK_SIZE:
                self.phase = 'event_select'
                self._generate_opening_events()
            return
        card_type = self.draft_type_order[len(self.draft_picks[player_id])]
        self.draft_options[player_id] = generate_draft_options(self.draft_pool, card_type, 3)

    def _generate_draft_options(self):
        self._generate_draft_options_for_player(0)
        self._generate_draft_options_for_player(1)

    def draft_pick(self, player_id: int, def_id: str) -> bool:
        if len(self.draft_picks[player_id]) >= DECK_SIZE:
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
        if len(self.draft_picks[player_id]) >= DECK_SIZE:
            return False
        old_ids = [c.def_id for c in self.draft_options[player_id]]
        self.draft_rerolls[player_id] -= 1
        card_type = self.draft_type_order[len(self.draft_picks[player_id])]
        options = generate_draft_options(self.draft_pool, card_type, 3, exclude_def_ids=old_ids)
        self.draft_options[player_id] = options
        return True

    def _generate_opening_events(self):
        pos1 = [e for e in self.OPENING_EVENTS.values() if e['position'] == 1]
        pos2 = [e for e in self.OPENING_EVENTS.values() if e['position'] == 2]
        pos3 = [e for e in self.OPENING_EVENTS.values() if e['position'] == 3]
        magic_pool = [def_id for def_id in self.MAGIC_CARD_POOL if self._card_allowed(def_id)]
        for i in range(2):
            slot1 = pos1[0] if pos1 else None
            slot2 = random.choice(pos2) if pos2 else None
            slot3 = random.choice(pos3) if pos3 else None
            self.opening_event_options[i] = [slot1, slot2, slot3]
            for j in range(3):
                self.opening_event_magic_options[i][j] = random.sample(
                    magic_pool, min(3, len(magic_pool)))

    def _card_allowed(self, def_id: str) -> bool:
        return self.allowed_card_ids is None or def_id in self.allowed_card_ids

    def select_opening_event(self, player_id: int, event_id: int) -> bool:
        if self.phase != 'event_select':
            return False
        valid = any(e['id'] == event_id for e in self.opening_event_options[player_id] if e)
        if not valid:
            return False
        self.opening_event_picks[player_id] = event_id
        return True

    def both_events_selected(self) -> bool:
        return self.opening_event_picks[0] is not None and self.opening_event_picks[1] is not None

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
        for i in range(2):
            ps = self.players[i]
            if i != self.first_player:
                ps.health = SECOND_PLAYER_HEALTH
                ps.max_health = SECOND_PLAYER_HEALTH
                ps.base_max_health = SECOND_PLAYER_HEALTH
        for i in range(2):
            self._apply_opening_event(i)
        for i in range(2):
            ps = self.players[i]
            if i == self.first_player:
                ps.elixir = FIRST_PLAYER_ELIXIR
                hand_size = FIRST_PLAYER_HAND_SIZE
                if self.opening_event_picks[i] == 7 and len(force_first) == 1:
                    hand_size = 4
                    ps.elixir += 3
                ps.draw_cards(hand_size)
            else:
                ps.draw_cards(INITIAL_HAND_SIZE)
        self.round_num = 1
        self.log_msg(f"游戏开始！{self.pn(self.first_player)}先手。")
        self.log_msg(f"=== 第{self.round_num}回合 ===")
        self._start_player_turn(self.first_player)

    def _opening_event_enemy_targets(self, player_id: int):
        target_id = 1 - player_id
        return [target_id] if 0 <= target_id < len(self.players) else []

    def _apply_opening_event(self, player_id: int):
        ps = self.players[player_id]
        event_id = self.opening_event_picks[player_id]
        sub = self.opening_event_sub_choices[player_id]
        if event_id == 1:
            ps.max_health += 20
            ps.base_max_health += 20
            ps.health += 20
            self.log_msg(f"{self.pn(player_id)}【生命强化】：最大生命值+20")
        elif event_id == 2:
            ps.gain_magic(5)
            self.log_msg(f"{self.pn(player_id)}【魔力转化】：+5M")
            if sub and 'conversions' in sub:
                conversions = sub['conversions']
                converted = 0
                for conv in conversions:
                    magic_def = conv.get('magic_def_id')
                    source_def = conv.get('source_def_id')
                    if magic_def and source_def and self._card_allowed(magic_def):
                        for j in range(len(ps.deck)):
                            if ps.deck[j].def_id == source_def:
                                ps.deck[j] = CardInstance(def_id=magic_def)
                                converted += 1
                                magic_name = CARD_DEFS.get(magic_def, CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn
                                source_name = CARD_DEFS.get(source_def, CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn
                                self.log_msg(f"{self.pn(player_id)}【魔力转化】：{source_name}变为{magic_name}")
                                break
        elif event_id == 3:
            converted = 0
            if self._card_allowed('Light') and sub and 'convert_def_ids' in sub:
                target_def_ids = list(sub['convert_def_ids'])
                converted = 0
                for target_def in target_def_ids:
                    for j in range(len(ps.deck)):
                        if ps.deck[j].def_id == target_def and converted < 5:
                            light_card = CardInstance(def_id='Light')
                            light_card.instance_flags = {'sprout', 'symbiosis'}
                            ps.deck[j] = light_card
                            converted += 1
                            break
                self.log_msg(f"{self.pn(player_id)}【光之洗礼】：{converted}张牌变为Light(萌芽+共生)")
        elif event_id == 4:
            target_ids = self._opening_event_enemy_targets(player_id)
            for target_id in target_ids:
                self.players[target_id].fire += 2
            target_label = "敌方全体" if len(target_ids) > 1 else "敌方"
            self.log_msg(f"{self.pn(player_id)}【烈焰预兆】：{target_label}+2灼烧")
        elif event_id == 5:
            self.log_msg(f"{self.pn(player_id)}【命运抽签】：前二回合抽牌至手牌满")
        elif event_id == 6:
            self.log_msg(f"{self.pn(player_id)}【能量涌动】：前三回合额外回复2E")
        elif event_id == 7:
            self.log_msg(f"{self.pn(player_id)}【先手压制】：先手回复3E并抽4张牌")
        elif event_id == 8:
            ps.max_health -= 20
            ps.base_max_health -= 20
            ps.health -= 20
            if not self._card_allowed('Yggdrasil'):
                return
            if sub and 'yggdrasil_convert_def_id' in sub:
                target_def = sub['yggdrasil_convert_def_id']
                for j in range(len(ps.deck)):
                    if ps.deck[j].def_id == target_def:
                        ps.deck[j] = CardInstance(def_id='Yggdrasil')
                        target_name = CARD_DEFS.get(target_def, CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn
                        self.log_msg(f"{self.pn(player_id)}【绝境求生】：最大生命值-20，{target_name}变为Yggdrasil")
                        break
            else:
                for j in range(len(ps.deck) - 1, -1, -1):
                    if ps.deck[j].def_id != 'Yggdrasil':
                        ps.deck[j] = CardInstance(def_id='Yggdrasil')
                        self.log_msg(f"{self.pn(player_id)}【绝境求生】：最大生命值-20，一张牌变为Yggdrasil")
                        break

    def _start_draw_phase(self):
        self.phase = 'draw'
        for i in range(2):
            ps = self.players[i]
            ps.cards_played_this_turn = {}
            ps.magic_battery_m_this_turn = 0
            ps.custom_vars['\u9b54\u6cd5\u7535\u6c60\u672c\u56de\u5408\u56de\u9b54'] = 0
        self.log_msg(f"=== 第{self.round_num}回合 ===")
        self._start_player_turn(self.first_player)

    def _start_player_turn(self, player_id: int):
        self.current_player = player_id
        ps = self.players[player_id]
        opp = self.players[1 - player_id]
        self._apply_turn_start_effects(player_id)
        if self.game_over:
            return
        if ps.skip_turn:
            ps.skip_turn = False
            self.log_msg(f"{self.pn(player_id)}被眩晕，跳过本回合！")
            self._end_player_turn(player_id)
            return
        if ps.health <= 0:
            self._check_yggdrasil(player_id)
            if ps.health <= 0:
                self._check_game_over()
                return
        self.phase = 'action'

    def _apply_turn_start_effects(self, player_id: int):
        ps = self.players[player_id]
        opp = self.players[1 - player_id]
        self._antenna_reveal[player_id] = None
        if ps.shovel_active:
            ps.shovel_active = False
            ps.untargetable = False
            self.log_msg(f"{self.pn(player_id)}的铲子效果结束")
        if self.round_num > 1:
            draw_count = DRAW_PER_TURN - ps.enemy_draw_reduction
            draw_count = max(0, draw_count)
            ps.draw_cards(draw_count)
            self.log_msg(f"{self.pn(player_id)}抽{draw_count}张牌")
        for eq in opp.equipment:
            if eq.def_id == 'Corruption' and not eq.corruption_active:
                eq.corruption_active = True
                self.log_msg(f"{self.pn(1 - player_id)}的腐化效果激活！全场伤害翻倍！")
        if ps.poison > 0:
            dmg = ps.poison
            self._deal_direct_damage(player_id, dmg, '中毒')
            if self.game_over or ps.health <= 0:
                return
            ps.poison = ps.poison // 2
            if ps.poison > 0:
                self.log_msg(f"{self.pn(player_id)}中毒减半为{ps.poison}层")
        if ps.fire > 0:
            dmg = ps.fire
            self._deal_direct_damage(player_id, dmg, '灼烧')
            if self.game_over or ps.health <= 0:
                return
        if self.round_num > 1:
            elixir_recovery = ELIXIR_RECOVERY
            for eq in opp.equipment:
                if eq.def_id == 'Pincer':
                    elixir_recovery -= 1
                    self.log_msg(f"{self.pn(player_id)}受到螫针影响，能量回复-1")
            elixir_recovery -= ps.enemy_e_reduction
            elixir_recovery = max(0, elixir_recovery)
            ps.gain_elixir(elixir_recovery)
            self.log_msg(f"{self.pn(player_id)}回复{elixir_recovery}E")
        if self.opening_event_picks[player_id] == 5 and self.round_num <= 2:
            draw_needed = ps.hand_space()
            if draw_needed > 0:
                ps.draw_cards(draw_needed)
                self.log_msg(f"{self.pn(player_id)}【命运抽签】：抽{draw_needed}张至手牌满")
        if self.opening_event_picks[player_id] == 6 and self.round_num <= 3:
            ps.gain_elixir(2)
            self.log_msg(f"{self.pn(player_id)}【能量涌动】：额外+2E")
        for eq in ps.equipment:
            eq.turns_equipped += 1
            if eq.def_id == 'Leaf':
                ps.heal(2)
                self.log_msg(f"{self.pn(player_id)}的叶子效果：+2H")
            elif eq.def_id == 'Yucca':
                ps.heal(5)
                self.log_msg(f"{self.pn(player_id)}的丝兰效果：+5H")
            elif eq.def_id == 'MagicLeaf':
                ps.gain_magic(1)
                self.log_msg(f"{self.pn(player_id)}的魔法叶效果：+1M")
            elif eq.def_id == 'MagicYucca':
                ps.gain_magic(2)
                self.log_msg(f"{self.pn(player_id)}的魔法丝兰效果：+2M")
            elif eq.def_id == 'Powder':
                ps.gain_elixir(2)
                self.log_msg(f"{self.pn(player_id)}的粉末效果：+2E")
            elif eq.def_id == 'GoldenLeaf':
                ps.draw_cards(1)
                self.log_msg(f"{self.pn(player_id)}的黄金叶效果：多抽1张牌")

    def _deal_direct_damage(self, player_id: int, amount: int, source: str = '', source_id: int = None):
        ps = self.players[player_id]
        if ps.invincible:
            self.log_msg(f"{self.pn(player_id)}无敌，免疫{source}伤害！")
            return 0
        actual = amount
        corruption_count = self._get_corruption_count()
        if corruption_count > 0:
            actual = actual * (2 ** corruption_count)
            self.log_msg(f"腐化效果：伤害x{2 ** corruption_count}")
        ps.health -= actual
        self._record_damage(player_id, actual, source_id)
        self.log_msg(f"{self.pn(player_id)}受到{actual}点{source}伤害（H={ps.health}）")
        self._check_yggdrasil(player_id)
        self._check_game_over()
        return actual

    def deal_attack_damage(self, target_id: int, amount: int, hits: int = 1, is_battery: bool = False, is_precision: bool = False) -> int:
        ps = self.players[target_id]
        opp_id = 1 - target_id
        opp = self.players[opp_id]
        if ps.untargetable and not is_battery:
            self.log_msg(f"{self.pn(target_id)}无法被攻击选中！")
            return 0
        total_dealt = 0
        for h in range(hits):
            if ps.dodge > 0:
                ps.dodge -= 1
                if is_precision:
                    self.log_msg(f"{self.pn(target_id)}的闪避被精准消耗！")
                else:
                    self.log_msg(f"{self.pn(target_id)}闪避了攻击！")
                    continue
            if ps.invincible:
                self.log_msg(f"{self.pn(target_id)}无敌，免疫伤害！")
                continue
            if amount <= 0 and hits <= 1:
                break
            dmg = amount
            if self.halve_next_attack:
                dmg = math.ceil(dmg / 2)
                self.log_msg(f"精准被反制，伤害减半：{amount}->{dmg}")
            corruption_count = self._get_corruption_count()
            if corruption_count > 0:
                dmg = dmg * (2 ** corruption_count)
                self.log_msg(f"腐化效果：伤害x{2 ** corruption_count}")
            if ps.nazar_active:
                original_dmg = dmg
                dmg = max(1, dmg - 9)
                self.log_msg(f"邪眼护符效果：伤害{original_dmg}->{dmg}")
                if original_dmg >= 10:
                    ps.nazar_big_hits += 1
                    if ps.nazar_big_hits >= 2:
                        ps.nazar_active = False
                        ps.nazar_big_hits = 0
                        self.log_msg(f"{self.pn(target_id)}的邪眼护符被击破！")
            dmg = max(0, dmg - ps.armor)
            if ps.sponge_active and dmg > 0:
                poison_add = dmg // 2
                ps.poison += poison_add
                self.log_msg(f"海绵效果：{self.pn(target_id)}将{dmg}伤害转为{poison_add}层中毒")
                dmg = 0
            ps.health -= dmg
            total_dealt += dmg
            self.log_msg(f"{self.pn(target_id)}受到{dmg}点伤害（H={ps.health}）")
            if ps.toxic > 0:
                ps.poison += ps.toxic
                self.log_msg(f"淬毒效果：{self.pn(target_id)}+{ps.toxic}层中毒")
            self._game_over_defer_depth += 1
            try:
                self._check_yggdrasil(target_id)
                if dmg > 0 and not is_battery:
                    for eq in list(ps.equipment):
                        if eq.def_id == 'Battery':
                            self.log_msg(f"{self.pn(target_id)}的电池效果：对敌方造成3D")
                        self._deal_direct_damage(opp_id, 3, '电池', target_id)
                        if eq.def_id == 'MagicBattery':
                            if ps.magic_battery_m_this_turn < 3:
                                ps.gain_magic(1)
                                ps.magic_battery_m_this_turn += 1
                                self.log_msg(f"{self.pn(target_id)}的魔法电池效果：+1M")
            finally:
                self._game_over_defer_depth -= 1
            if ps.health <= 0 or opp.health <= 0:
                self._check_game_over()
                break
        return total_dealt

    def _get_corruption_count(self) -> int:
        count = 0
        for ps in self.players:
            for eq in ps.equipment:
                if eq.def_id == 'Corruption' and eq.corruption_active:
                    count += 1
        return count

    def _check_yggdrasil(self, player_id: int):
        ps = self.players[player_id]
        if ps.health <= 0 and self._yggdrasil_check:
            if ps.bandage_active:
                ps.health = 1
                ps.invincible = True
                ps.bandage_active = False
                ps.bandage_death_pending = True
                self.log_msg(f"{self.pn(player_id)}的绷带发动！无敌直到下个友方回合结束，然后死亡")
                self._check_game_over()
                return
            for card in ps.hand[:]:
                if card.def_id == 'Yggdrasil':
                    ps.health = 5
                    ps.invincible = True
                    ps.poison = 0
                    ps.fire = 0
                    ps.vulnerable = 0
                    ps.toxic = 0
                    ps.triangle_stacks = 0
                    ps.dodge = 0
                    ps.nazar_active = False
                    ps.nazar_big_hits = 0
                    ps.armor = 0
                    ps.equipment_protection = 0
                    ps.negate_next_skill = False
                    ps.skip_turn = False
                    ps.damage_multiplier = 1.0
                    ps.hand.remove(card)
                    ps.exile.append(card)
                    self.log_msg(f"{self.pn(player_id)}的世界树之叶发动！清除己方所有效果，生命值设为5，本回合无敌！")
                    self._check_game_over()
                    return
                if card.card_def and card.card_def.effects:
                    for effect in card.card_def.effects:
                        eff_type = effect if isinstance(effect, str) else effect.get('type', '')
                        if eff_type == 'on_fatal_set_health_exile':
                            params = effect.get('params', {}) if isinstance(effect, dict) else {}
                            log = effect.get('log', '') if isinstance(effect, dict) else ''
                            health_amount = params.get('health', 5)
                            ps.health = health_amount
                            ps.invincible = True
                            ps.poison = 0
                            ps.fire = 0
                            ps.vulnerable = 0
                            ps.toxic = 0
                            ps.triangle_stacks = 0
                            ps.dodge = 0
                            ps.nazar_active = False
                            ps.nazar_big_hits = 0
                            ps.armor = 0
                            ps.equipment_protection = 0
                            ps.negate_next_skill = False
                            ps.skip_turn = False
                            ps.damage_multiplier = 1.0
                            ps.hand.remove(card)
                            ps.exile.append(card)
                            self.log_msg(log or f"{self.pn(player_id)}的{card.name_cn}发动！清除己方所有效果，生命值设为{health_amount}，本回合无敌！")
                            self._check_game_over()
                            return

    def _check_game_over(self):
        if self._game_over_defer_depth > 0:
            return
        if self.players[0].health <= 0 and self.players[1].health <= 0:
            self.game_over = True
            self.winner = -1
            self.phase = 'game_over'
            self.log_msg("双方生命值同时归零！平局！")
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
        if card_def.card_type == 'guard' and not self._has_script_entry(card_def, 'play') and not card_def.effects:
            return False, "反制牌只能通过响应机制使用"
        if self.phase != 'action' or self.current_player != player_id:
            return False, "不是你的回合"
        if ps.attack_blocked > 0 and card_def.card_type == 'thorn':
            return False, "本回合无法使用攻击牌"
        if ps.attack_only > 0 and card_def.card_type != 'thorn':
            return False, "本回合只能使用攻击牌"
        if ps.shovel_active:
            return False, "链子效果中，无法使用卡牌"
        extra_e = self._get_extra_e_for_card(player_id, card)
        total_e = card.cost_e + extra_e
        if total_e > ps.elixir:
            return False, f"能量不足（需要{total_e}E，当前{ps.elixir}E）"
        if card.cost_m > ps.magic:
            return False, f"魔力不足（需要{card.cost_m}M，当前{ps.magic}M）"
        return True, ""

    def _get_extra_e_for_card(self, player_id: int, card: CardInstance) -> int:
        ps = self.players[player_id]
        dup_count = ps.cards_played_this_turn.get(card.def_id, 0)
        if 'symbiosis' in card.flags:
            return 0
        return dup_count

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
        can_play, reason = self.can_play_card(player_id, card)
        if not can_play:
            return {'success': False, 'error': reason}
        extra_e = self._get_extra_e_for_card(player_id, card)
        total_e = card.cost_e + extra_e
        self._spend_resource(player_id, 'elixir', total_e, card)
        self._spend_resource(player_id, 'magic', card.cost_m, card)
        ps.cards_played_this_turn[card.def_id] = ps.cards_played_this_turn.get(card.def_id, 0) + 1
        card_removed = ps.remove_hand_card(card_instance_id)
        if card_removed is None:
            return {'success': False, 'error': '移出手牌失败'}
        needs_response = self._check_response_needed(player_id, card)
        if not needs_response:
            needs_response = self._check_precision_response_needed(player_id, card)
        if needs_response:
            self.pending_response = {
                'card': card.to_dict(),
                'player_id': player_id,
                'original_choice': choice,
                'is_precision': 'precision' in card.flags,
            }
            return {'success': True, 'needs_response': True, 'card': card.to_dict()}
        return self._execute_card_effect(player_id, card, choice)

    def _check_response_needed(self, player_id: int, card: CardInstance) -> bool:
        if 'precision' in card.flags:
            return False
        opp = self.players[1 - player_id]
        if any(c.card_def.response_trigger == 'any' for c in opp.hand):
            return True
        if card.card_type == 'thorn':
            for c in opp.hand:
                if c.card_def.response_trigger == 'thorn':
                    return True
        if card.card_type == 'bloom':
            for c in opp.hand:
                if c.card_def.response_trigger == 'bloom':
                    return True
        if card.card_type == 'root':
            for c in opp.hand:
                if c.card_def.response_trigger == 'root':
                    return True
        if self._would_destroy_equipment(card):
            for c in opp.hand:
                if c.card_def.response_trigger == 'equipment_destroy':
                    return True
        if self._would_heal(card):
            for c in opp.hand:
                if c.card_def.response_trigger == 'heal':
                    return True
        return False

    def _check_precision_response_needed(self, player_id: int, card: CardInstance) -> bool:
        if 'precision' not in card.flags:
            return False
        opp = self.players[1 - player_id]
        for c in opp.hand:
            if c.card_def.response_trigger == 'thorn':
                return True
        return False

    def _would_destroy_equipment(self, card: CardInstance) -> bool:
        return card.def_id in ('Sewage', 'MagicSewage')

    def _would_heal(self, card: CardInstance) -> bool:
        if card is None:
            return False
        if getattr(card.card_def, 'heal', 0):
            return True
        for effect in self._play_effects_for_card(card):
            if not isinstance(effect, dict):
                continue
            effect_type = effect.get('type', '')
            if effect_type in ('heal', 'lifesteal_damage'):
                return True
        return False

    def handle_response(self, responder_id: int, card_instance_id: Optional[int]) -> dict:
        if self.pending_response is None:
            return {'success': False, 'error': '没有待响应的操作'}
        pending = self.pending_response
        self.pending_response = None
        player_id = pending['player_id']
        card = CardInstance.from_dict(pending['card'])
        choice = pending.get('original_choice')
        if card_instance_id is not None:
            responder = self.players[responder_id]
            counter_card = responder.find_hand_card(card_instance_id)
            if counter_card is None:
                return self._execute_card_effect(player_id, card, choice)
            if counter_card.cost_e > responder.elixir or counter_card.cost_m > responder.magic:
                return self._execute_card_effect(player_id, card, choice)
            can_respond = False
            played_card_def = card.card_def
            if played_card_def.card_type == 'thorn' and counter_card.card_def.response_trigger == 'thorn':
                can_respond = True
            elif played_card_def.card_type == 'bloom' and counter_card.card_def.response_trigger == 'bloom':
                can_respond = True
            elif played_card_def.card_type == 'root' and counter_card.card_def.response_trigger == 'root':
                can_respond = True
            elif counter_card.card_def.response_trigger == 'any':
                can_respond = True
            elif self._would_heal(card) and counter_card.card_def.response_trigger == 'heal':
                can_respond = True
            elif self._would_destroy_equipment(card) and counter_card.card_def.response_trigger == 'equipment_destroy':
                can_respond = True
            if not can_respond:
                return self._execute_card_effect(player_id, card, choice)
            self._spend_resource(responder_id, 'elixir', counter_card.cost_e, counter_card)
            self._spend_resource(responder_id, 'magic', counter_card.cost_m, counter_card)
            counter_removed = responder.remove_hand_card(card_instance_id)
            if counter_removed is None:
                return self._execute_card_effect(player_id, card, choice)
            self.log_msg(f"{self.pn(responder_id)}使用{counter_removed.name_cn}进行反制！")
            self._execute_counter_effect(responder_id, counter_removed, card, player_id)
            is_precision = pending.get('is_precision', False)
            if counter_removed.def_id == 'Bubble':
                if is_precision:
                    self._execute_card_effect_half_damage(player_id, card, choice)
                    return {'success': True, 'countered': True, 'precision_halved': True, 'card': card.to_dict()}
                self._execute_card_effect(player_id, card, choice)
                return {'success': True, 'countered': True, 'card': card.to_dict()}
            if counter_removed.def_id == 'MagicBubble':
                self.negated_card = True
            return self._execute_card_effect(player_id, card, choice)
        return self._execute_card_effect(player_id, card, choice)

    def _execute_counter_effect(self, responder_id: int, counter_card: CardInstance, original_card: CardInstance, original_player_id: Optional[int] = None):
        ps = self.players[responder_id]
        opp = self.players[1 - responder_id]
        if self._has_script_entry(counter_card.card_def, 'response'):
            self._run_effect_list(
                responder_id,
                counter_card,
                self._get_script_effects(counter_card.card_def, 'response'),
                None,
                {'event': 'response', 'source_id': responder_id, 'target_id': original_player_id if original_player_id is not None else 1 - responder_id},
            )
            return
        if counter_card.def_id == 'Bubble':
            ps.dodge += 1
            self.log_msg(f"{self.pn(responder_id)}获得1层闪避")
        elif counter_card.def_id == 'Nazar':
            ps.nazar_active = True
            ps.nazar_big_hits = 0
            self.log_msg(f"{self.pn(responder_id)}获得邪眼护符效果")
        elif counter_card.def_id == 'MagicNazar':
            ps.equipment_protection += 1
            self.log_msg(f"{self.pn(responder_id)}获得1层装备保护")
        elif counter_card.def_id == 'MagicBubble':
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
        if 'exile' in counter_card.flags:
            ps.exile.append(counter_card)
        else:
            self._discard_card(ps, counter_card)
        self._dispatch_card_event('card_used', responder_id, counter_card,
                                  target_id=original_player_id if original_player_id is not None else responder_id)

    def _reset_one_shot_attack_attrs(self, card: CardInstance):
        reset_card_for_discard(card)

    def _discard_card(self, ps, card: CardInstance):
        reset_card_for_discard(card)
        ps.discard.append(card)

    def _execute_card_effect(self, player_id: int, card: CardInstance, choice: Optional[dict] = None) -> dict:
        ps = self.players[player_id]
        opp = self.players[1 - player_id]
        result = {'success': True, 'card': card.to_dict()}
        if card.card_type == 'thorn' and (card.fission_level > 1 or card.fusion_level > 1):
            self.log_msg(f"[特效] {card.name_cn} 聚变={card.fusion_level} 裂变={card.fission_level}")
        if self.negated_card and card.card_type == 'bloom':
            self.negated_card = False
            self.log_msg(f"{self.pn(player_id)}的{card.name_cn}被魔法泡泡反制，失效！")
            if 'exile' in card.flags:
                ps.exile.append(card)
            else:
                self._discard_card(ps, card)
            return result
        self.negated_card = False
        needs_choice = self._card_needs_choice(card)
        if needs_choice and choice is None:
            self.pending_choice = {
                'card': card.to_dict(),
                'player_id': player_id,
                'choice_type': self._get_choice_type(card),
            }
            ps.hand.insert(0, card)
            ps.elixir += card.cost_e + ps.cards_played_this_turn.get(card.def_id, 1) - 1
            ps.magic += card.cost_m
            ps.cards_played_this_turn[card.def_id] = max(0, ps.cards_played_this_turn.get(card.def_id, 1) - 1)
            return {'success': True, 'needs_choice': True, 'choice_type': self._get_choice_type(card), 'card': card.to_dict()}
        if card.card_type == 'thorn':
            fission_level = max(1, int(getattr(card, 'fission_level', 1)))
            for hit_idx in range(fission_level):
                if self.game_over:
                    break
                card.fission_hit = hit_idx
                self._apply_card_effect(player_id, card, choice)
            card.fission_hit = 0
        else:
            self._apply_card_effect(player_id, card, choice)
        if card.card_type == 'root':
            eq = EquipmentInstance(card, player_id)
            if eq.def_id == 'Disc':
                ps.armor += 2
                self.log_msg(f"{self.pn(player_id)}获得2点护甲")
            ps.equipment.append(eq)
            self.log_msg(f"{self.pn(player_id)}装备了{card.name_cn}")
        elif 'exile' in card.flags:
            ps.exile.append(card)
            self.log_msg(f"{self.pn(player_id)}的{card.name_cn}被放逐")
        else:
            card.mimic_discount = 0
            self._discard_card(ps, card)
        self._check_game_over()
        return result

    def _execute_card_effect_half_damage(self, player_id: int, card: CardInstance, choice: Optional[dict] = None) -> dict:
        self.log_msg(f"{self.pn(player_id)}的精准牌被闪避反制，伤害减半！")
        self.halve_next_attack = True
        result = self._execute_card_effect(player_id, card, choice)
        self.halve_next_attack = False
        return result

    def _get_card_base_damage(self, card: CardInstance) -> int:
        dmg_map = {
            'Basic': 6, 'Bone': 12, 'Stinger': 20, 'Sand': 3,
            'Wing': 8, 'Light': 2, 'Fang': 8, 'Triangle': 6,
            'MagicBone': 15, 'MagicStinger': 30,
        }
        base = dmg_map.get(card.def_id, 0)
        return self._modified_attack_damage(base, card)

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

    def resolve_choice(self, player_id: int, choice: dict) -> dict:
        if self.pending_choice is None:
            return {'success': False, 'error': '没有待选择操作'}
        pending = self.pending_choice
        self.pending_choice = None
        card = CardInstance.from_dict(pending['card'])
        ps = self.players[player_id]
        if choice is None:
            if ps.find_hand_card(card.instance_id) is None:
                ps.hand.insert(0, card)
            return {'success': False, 'error': '选择已取消'}
        dup_count = ps.cards_played_this_turn.get(card.def_id, 0)
        extra_e = dup_count
        total_e = card.cost_e + extra_e
        self._spend_resource(player_id, 'elixir', total_e, card)
        self._spend_resource(player_id, 'magic', card.cost_m, card)
        ps.cards_played_this_turn[card.def_id] = dup_count + 1
        hand_card = ps.find_hand_card(card.instance_id)
        if hand_card:
            ps.remove_hand_card(card.instance_id)
        return self._execute_card_effect(player_id, card, choice)

    def _apply_card_effect(self, player_id: int, card: CardInstance, choice: Optional[dict] = None):
        ps = self.players[player_id]
        opp = self.players[1 - player_id]
        opp_id = 1 - player_id
        method_name = f'_effect_{card.def_id.lower()}'
        if hasattr(self, method_name):
            getattr(self, method_name)(player_id, card, choice)
        elif card.card_def.effects:
            self._process_atomic_effects(player_id, card, choice, 'play')
        else:
            self.log_msg(f"{self.pn(player_id)}使用了{card.name_cn}")

    PASSIVE_EFFECT_TYPES = {'on_fatal_set_health_exile', 'on_fatal_invincible_then_die'}

    def _process_atomic_effects(self, player_id: int, card: CardInstance, choice: Optional[dict], context: str):
        ps = self.players[player_id]
        opp = self.players[1 - player_id]
        for effect in card.card_def.effects:
            if isinstance(effect, str):
                eff_type = effect
                params = {}
                log = ''
            else:
                eff_type = effect.get('type', '')
                params = effect.get('params', {})
                log = effect.get('log', '')
            if eff_type in self.PASSIVE_EFFECT_TYPES and context == 'play':
                if log:
                    self.log_msg(log)
                else:
                    self.log_msg(f"{self.pn(player_id)}的{card.name_cn}被动效果已就绪")
                continue
            resolved_type = self._EFFECT_ALIASES.get(eff_type, eff_type)
            handler = getattr(self, f'_atomic_{resolved_type}', None)
            if handler:
                handler(player_id, card, params, log, choice, context)
            elif log:
                self.log_msg(log)
            else:
                self.log_msg(f"未知效果: {eff_type}")

    def _atomic_log(self, player_id, card, params, log, choice, context):
        msg = log or params.get('msg', '')
        if msg:
            self.log_msg(msg.format(p=player_id + 1, name=card.name_cn))

    def _atomic_deal_damage(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        amount = params.get('amount', 6)
        hits = params.get('hits', 1)
        is_precision = params.get('is_precision', False)
        amount = self._modified_attack_damage(amount, card)
        self._incoming_damage_hint[target_id] = int(amount)
        dealt = self.deal_attack_damage(target_id, amount, hits, is_precision=is_precision)
        self._last_damage_value[target_id] = int(dealt)
        self.log_msg(log or f"{self.pn(player_id)}对{self.pn(target_id)}造成{dealt}伤害")

    def _atomic_heal(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = params.get('amount', 0)
        self.players[target_id].heal(amount)
        self.log_msg(log or f"{self.pn(target_id)}回复{amount}H")

    def _atomic_draw(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        self.players[player_id].draw_cards(amount)
        self.log_msg(log or f"{self.pn(player_id)}抽{amount}张牌")

    def _atomic_gain_e(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = params.get('amount', 1)
        self.players[target_id].gain_elixir(amount)
        self.log_msg(log or f"{self.pn(target_id)}获得{amount}E")

    def _atomic_gain_m(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = params.get('amount', 1)
        self.players[target_id].gain_magic(amount)
        self.log_msg(log or f"{self.pn(target_id)}获得{amount}M")

    def _atomic_gain_armor(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = params.get('amount', 1)
        self.players[target_id].armor += amount
        self.log_msg(log or f"{self.pn(target_id)}获得{amount}护甲")

    def _atomic_gain_dodge(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = params.get('amount', 1)
        self.players[target_id].dodge += amount
        self.log_msg(log or f"{self.pn(target_id)}获得{amount}闪避")

    def _atomic_apply_poison(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        amount = params.get('amount', 1)
        self.players[target_id].poison += amount
        self.log_msg(log or f"{self.pn(target_id)}+{amount}中毒")

    def _atomic_apply_burn(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        amount = params.get('amount', 1)
        self.players[target_id].fire += amount
        self.log_msg(log or f"{self.pn(target_id)}+{amount}灼烧")

    def _atomic_apply_toxic(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        amount = params.get('amount', 1)
        self.players[target_id].toxic += amount
        self.log_msg(log or f"{self.pn(target_id)}+{amount}淬毒")

    def _atomic_apply_vulnerable(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        amount = params.get('amount', 1)
        self.players[target_id].vulnerable += amount
        self.log_msg(log or f"{self.pn(target_id)}+{amount}易伤")

    def _atomic_reveal_enemy_hand(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        opp = self.players[target_id]
        card_names = ', '.join(c.name_cn for c in opp.hand)
        self._antenna_reveal[player_id] = [c.to_dict() for c in opp.hand]
        self.log_msg(log or f"{self.pn(player_id)}窥探{self.pn(target_id)}手牌：{card_names}")

    def _atomic_steal_enemy_card(self, player_id, card, params, log, choice, context):
        ps = self.players[player_id]
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        opp = self.players[target_id]
        if choice and 'target_instance_id' in choice:
            target = opp.find_hand_card(choice['target_instance_id'])
            if target and ps.can_add_to_hand():
                opp.hand.remove(target)
                ps.add_to_hand(target)
                if log:
                    self.log_msg(log)
            else:
                self.log_msg(log or f"{self.pn(player_id)}夺取失败")
        else:
            self.log_msg(log or f"{self.pn(player_id)}未选择要夺取的牌")

    def _atomic_choose_from_deck(self, player_id, card, params, log, choice, context):
        ps = self.players[player_id]
        selector = params.get('selector')
        if isinstance(selector, dict):
            matched = self._match_card_selector(player_id, ps.deck, selector, card)
            if self.debug_selector_log:
                self.log_msg(f"选择器命中(牌堆)：{len(matched)}")
        if choice and 'target_instance_id' in choice:
            target = next((c for c in ps.deck if c.instance_id == choice['target_instance_id']), None)
            if target is None and isinstance(selector, dict):
                matched = self._match_card_selector(player_id, ps.deck, selector, card)
                target = matched[0] if matched else None
            if target and ps.can_add_to_hand():
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
            matched = self._match_card_selector(player_id, ps.discard, selector, card)
            if self.debug_selector_log:
                self.log_msg(f"选择器命中(弃牌)：{len(matched)}")
        if choice and 'target_def_id' in choice:
            sel = {'selector': 'by_id', 'id': choice['target_def_id']}
            matched = self._match_card_selector(player_id, ps.discard, sel, card)
            target = matched[0] if matched else None
            if target is None and isinstance(selector, dict):
                matched2 = self._match_card_selector(player_id, ps.discard, selector, card)
                target = matched2[0] if matched2 else None
            if target and ps.can_add_to_hand():
                ps.discard.remove(target)
                ps.add_to_hand(target)
                if log:
                    self.log_msg(log)
            else:
                self.log_msg(log or f"{self.pn(player_id)}从弃牌堆取牌失败")
        else:
            self.log_msg(log or f"{self.pn(player_id)}未选择牌")

    def _atomic_set_health(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 60)
        self.players[player_id].health = amount
        self.log_msg(log or f"{self.pn(player_id)}血量设为{amount}")

    def _atomic_set_invincible(self, player_id, card, params, log, choice, context):
        self.players[player_id].invincible = True
        self.log_msg(log or f"{self.pn(player_id)}获得无敌")

    def _atomic_set_untargetable(self, player_id, card, params, log, choice, context):
        self.players[player_id].untargetable = True
        self.players[player_id].shovel_active = True
        self.log_msg(log or f"{self.pn(player_id)}无法被攻击选中")

    def _atomic_block_enemy_attacks(self, player_id, card, params, log, choice, context):
        duration = params.get('duration', 1)
        opp = self.players[1 - player_id]
        opp.attack_blocked = max(opp.attack_blocked, duration)
        self.log_msg(log or f"{self.pn(1 - player_id)}无法使用攻击牌{duration}回合")

    def _atomic_force_enemy_attacks_only(self, player_id, card, params, log, choice, context):
        duration = params.get('duration', 1)
        opp = self.players[1 - player_id]
        opp.attack_only = max(opp.attack_only, duration)
        self.log_msg(log or f"{self.pn(1 - player_id)}仅可使用攻击牌{duration}回合")

    def _atomic_block_own_actions(self, player_id, card, params, log, choice, context):
        self.players[player_id].shovel_active = True
        self.log_msg(log or f"{self.pn(player_id)}无法使用卡牌")

    def _atomic_counter_dodge(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        self.players[player_id].dodge += amount
        self.log_msg(log or f"{self.pn(player_id)}获得{amount}闪避")

    def _atomic_counter_nazar(self, player_id, card, params, log, choice, context):
        self.players[player_id].nazar_active = True
        self.players[player_id].nazar_big_hits = 0
        self.log_msg(log or f"{self.pn(player_id)}获得邪眼护符效果")

    def _atomic_counter_negate_skill(self, player_id, card, params, log, choice, context):
        self.players[player_id].negate_next_skill = True
        self.log_msg(log or f"{self.pn(player_id)}的下次技能牌将失效")

    def _atomic_counter_equip_protect(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        self.players[player_id].equipment_protection += amount
        self.log_msg(log or f"{self.pn(player_id)}获得{amount}装备保护")

    def _atomic_counter_block_enemy_attacks(self, player_id, card, params, log, choice, context):
        duration = params.get('duration', 1)
        opp = self.players[1 - player_id]
        opp.attack_blocked = max(opp.attack_blocked, duration)
        self.log_msg(log or f"{self.pn(1 - player_id)}无法使用攻击牌")

    def _atomic_counter_set_invincible_then_die(self, player_id, card, params, log, choice, context):
        self.players[player_id].bandage_active = True
        self.log_msg(log or f"{self.pn(player_id)}受到致命伤害时将无敌至下个友方回合结束")

    def _atomic_equip_sponge(self, player_id, card, params, log, choice, context):
        self.players[player_id].sponge_active = True
        self.log_msg(log or f"{self.pn(player_id)}伤害转为毒伤")

    def _atomic_equip_reduce_enemy_draw(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        self.players[1 - player_id].enemy_draw_reduction += amount
        self.log_msg(log or f"敌方每回合少抽{amount}牌")

    def _atomic_equip_reduce_enemy_e(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        self.players[1 - player_id].enemy_e_reduction += amount
        self.log_msg(log or f"敌方每回合少回{amount}E")

    def _atomic_equip_reduce_own_draw(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        self.players[player_id].enemy_draw_reduction += amount
        self.log_msg(log or f"己方每回合少抽{amount}牌")

    def _atomic_equip_reduce_own_e(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        self.players[player_id].enemy_e_reduction += amount
        self.log_msg(log or f"己方每回合少回{amount}E")

    def _atomic_equip_add_toxic(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        self.players[1 - player_id].toxic += amount
        self.log_msg(log or f"敌方+{amount}淬毒")

    def _atomic_equip_set_health(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 60)
        self.players[player_id].health = amount
        self.log_msg(log or f"{self.pn(player_id)}血量设为{amount}")

    def _atomic_equip_on_destroy_remove_poison_damage(self, player_id, card, params, log, choice, context):
        pass

    def _atomic_on_fatal_invincible_then_die(self, player_id, card, params, log, choice, context):
        self.players[player_id].bandage_active = True
        self.log_msg(log or f"{self.pn(player_id)}受到致命伤害时将无敌至下个友方回合结束，然后死亡")

    def _atomic_on_fatal_set_health_exile(self, player_id, card, params, log, choice, context):
        health_amount = params.get('health', 5)
        self.log_msg(log or f"{self.pn(player_id)}的{card.name_cn}被动效果：受到致命伤害时清除所有效果，生命值设为{health_amount}，本回合无敌")

    def _atomic_deal_damage_multi(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        amount = params.get('amount', 6)
        times = params.get('times', 1)
        total = 0
        for _ in range(times):
            total += self.deal_attack_damage(target_id, amount)
        self.log_msg(log or f"{self.pn(player_id)}对{self.pn(target_id)}造成{times}x{amount}={total}伤害")

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
        ps.invincible = False
        ps.equipment_protection = 0
        self.log_msg(log or f"{self.pn(target_id)}的所有正面效果已清除")

    def _atomic_clear_debuffs(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        ps = self.players[target_id]
        ps.poison = 0
        ps.fire = 0
        ps.vulnerable = 0
        ps.toxic = 0
        self.log_msg(log or f"{self.pn(target_id)}的所有负面效果已清除")

    def _atomic_clear_all_effects(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        ps = self.players[target_id]
        ps.poison = 0
        ps.fire = 0
        ps.vulnerable = 0
        ps.toxic = 0
        ps.armor = 0
        ps.dodge = 0
        ps.invincible = False
        ps.equipment_protection = 0
        self.log_msg(log or f"{self.pn(target_id)}的所有效果已清除")

    def _atomic_clear_status(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        status = params.get('status', '')
        ps = self.players[target_id]
        status_map = {'poison': 'poison', 'burn': 'fire', 'vulnus': 'vulnerable',
                      'toxic': 'toxic', 'dodge': 'dodge', 'invincible': 'invincible',
                      'untargetable': 'untargetable', 'equip_protection': 'equipment_protection'}
        attr = status_map.get(status)
        if attr and hasattr(ps, attr):
            if isinstance(getattr(ps, attr), bool):
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
            matched = self._match_card_selector(player_id, ps.exile, sel, card)
            target = matched[0] if matched else None
        if target and ps.can_add_to_hand():
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
        if choice and 'target_instance_id' in choice:
            target = ps.find_hand_card(choice['target_instance_id'])
        if target and ps.can_add_to_hand():
            new_card = target.copy()
            ps.add_to_hand(new_card)
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
                self._destroy_equipment(target_id, eq)
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

    def _atomic_destroy_random_equip(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        ts = self.players[target_id]
        if ts.equipment:
            eq = random.choice(ts.equipment)
            self._destroy_equipment(target_id, eq)
            self.log_msg(log or f"{self.pn(target_id)}的{eq.name_cn}被摧毁")
        else:
            self.log_msg(log or f"{self.pn(target_id)}没有装备")

    def _atomic_destroy_all_equip(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        ts = self.players[target_id]
        for eq in ts.equipment[:]:
            self._destroy_equipment(target_id, eq)
        self.log_msg(log or f"{self.pn(target_id)}的所有装备被摧毁")

    def _atomic_destroy_all_field_equip(self, player_id, card, params, log, choice, context):
        for pid in [0, 1]:
            for eq in self.players[pid].equipment[:]:
                self._destroy_equipment(pid, eq)
        self.log_msg(log or "场上所有装备被摧毁")

    def _atomic_remove_equip_protection(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        self.players[target_id].equipment_protection = 0
        self.log_msg(log or f"{self.pn(target_id)}的装备保护被移除")

    def _atomic_place_as_equip(self, player_id, card, params, log, choice, context):
        ps = self.players[player_id]
        if card in ps.hand:
            ps.hand.remove(card)
        card.durability = card.card_def.durability if card.card_def.durability > 0 else 3
        ps.equipment.append(card)
        self.log_msg(log or f"{self.pn(player_id)}将{card.name_cn}作为装备置于场上")

    def _atomic_block_card_type(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        card_type = params.get('card_type', 'thorn')
        duration = params.get('duration', 1)
        ts = self.players[target_id]
        if card_type == 'thorn':
            ts.attack_blocked = max(ts.attack_blocked, duration)
        elif card_type == 'bloom':
            ts.skill_blocked = getattr(ts, 'skill_blocked', 0)
            ts.skill_blocked = max(ts.skill_blocked, duration)
        self.log_msg(log or f"{self.pn(target_id)}无法使用{card_type}牌{duration}回合")

    def _atomic_force_card_type(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        card_type = params.get('card_type', 'thorn')
        duration = params.get('duration', 1)
        ts = self.players[target_id]
        if card_type == 'thorn':
            ts.attack_only = max(ts.attack_only, duration)
        self.log_msg(log or f"{self.pn(target_id)}仅可使用{card_type}牌{duration}回合")

    def _atomic_nullify_current_card(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        card_type = params.get('card_type', 'thorn')
        ts = self.players[target_id]
        ts.negate_next = getattr(ts, 'negate_next', None)
        ts.negate_next = card_type
        self.log_msg(log or f"{self.pn(target_id)}的{card_type}牌将失效")

    def _atomic_skip_turn(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        self.players[target_id].skip_turn = True
        self.log_msg(log or f"{self.pn(target_id)}的下一个回合将被跳过")

    def _atomic_extra_turn(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        self.players[target_id].extra_turn = True
        self.log_msg(log or f"{self.pn(target_id)}获得一个额外回合")

    def _atomic_force_end_turn(self, player_id, card, params, log, choice, context):
        self.players[player_id].force_end_turn = True
        self.log_msg(log or f"{self.pn(player_id)}强制结束当前回合")

    def _atomic_mark_self_damage_source(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        self.players[target_id].self_damage_next = True
        self.log_msg(log or f"{self.pn(target_id)}下次伤害来源标记为自身")

    def _atomic_fission(self, player_id, card, params, log, choice, context):
        card_type = params.get('card_type', 'thorn')
        times = self._eval_int(player_id, params.get('times', 1), card, 1)
        ps = self.players[player_id]
        target = ps.find_hand_card(choice.get('target_instance_id')) if isinstance(choice, dict) and 'target_instance_id' in choice else None
        targets = [target] if target is not None else [c for c in ps.hand if c.card_def.card_type == card_type and c is not card]
        targets = [c for c in targets if c and c.card_def.card_type == card_type]
        if targets:
            t = targets[0]
            t.fission_level = max(1, int(getattr(t, 'fission_level', 1))) + times
            t.fission_count = t.fission_level - 1
            self.log_msg(log or f"{self.pn(player_id)}的{t.name_cn}裂变+{times}")
        else:
            self.log_msg(log or f"{self.pn(player_id)}没有可裂变的{card_type}牌")

    def _atomic_multiply_next_damage(self, player_id, card, params, log, choice, context):
        multiplier = self._eval_int(player_id, params.get('multiplier', 1), card, 1)
        ps = self.players[player_id]
        ps.damage_multiplier = getattr(ps, 'damage_multiplier', 1.0) * multiplier
        self.log_msg(log or f"{self.pn(player_id)}下次伤害x{multiplier}")

    def _atomic_reduce_next_cost(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        ps = self.players[player_id]
        ps.cost_reduction = getattr(ps, 'cost_reduction', 0) + amount
        self.log_msg(log or f"{self.pn(player_id)}下次费用-{amount}")

    def _atomic_increase_next_cost(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        ps = self.players[player_id]
        ps.cost_increase = getattr(ps, 'cost_increase', 0) + amount
        self.log_msg(log or f"{self.pn(player_id)}下次费用+{amount}")

    def _atomic_fusion(self, player_id, card, params, log, choice, context):
        count = self._eval_int(player_id, params.get('count', params.get('min_count', 2)), card, 2)
        max_count = self._eval_int(player_id, params.get('max_count', count), card, count)
        card_type = params.get('card_type', 'thorn')
        ps = self.players[player_id]
        if isinstance(choice, dict) and 'target_instance_ids' in choice:
            selected = [ps.find_hand_card(i) for i in choice.get('target_instance_ids', [])]
            selected = [c for c in selected if c is not None]
        else:
            selected = [c for c in ps.hand if c.card_def.card_type == card_type and c is not card][:max_count]
        if len(selected) >= count:
            selected = selected[:max_count]
            if any(c.card_def.card_type != card_type for c in selected) or len({c.def_id for c in selected}) != 1:
                self.log_msg(log or f"{self.pn(player_id)}聚变目标无效")
                return
            keep = selected[0]
            keep.fusion_level = sum(max(1, int(getattr(c, 'fusion_level', 1))) for c in selected)
            keep.fission_level = max(max(1, int(getattr(c, 'fission_level', 1))) for c in selected)
            keep.fusion_multiplier = float(keep.fusion_level)
            keep.fission_count = keep.fission_level - 1
            for c in selected[1:]:
                ps.hand.remove(c)
                self._discard_card(ps, c)
            self.log_msg(log or f"{self.pn(player_id)}聚变：{keep.name_cn}聚变{keep.fusion_level} 裂变{keep.fission_level}")
        else:
            self.log_msg(log or f"{self.pn(player_id)}没有足够的{card_type}牌聚变")

    def _atomic_add_tag(self, player_id, card, params, log, choice, context):
        tag = params.get('tag', '')
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if tag and target_card:
            target_card.instance_flags = getattr(target_card, 'instance_flags', set())
            target_card.instance_flags.add(tag)
            self.log_msg(log or f"{target_card.name_cn}获得标签{tag}")

    def _atomic_remove_tag(self, player_id, card, params, log, choice, context):
        tag = params.get('tag', '')
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
        self.players[owner_id].exile.append(target_card)
        self.log_msg(log or f"{target_card.name_cn}被放逐")

    def _atomic_move_to_discard(self, player_id, card, params, log, choice, context):
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if not target_card:
            return
        owner_id, _ = self._remove_card_from_current_zone(target_card)
        if owner_id is None:
            owner_id = player_id
        self._discard_card(self.players[owner_id], target_card)
        self.log_msg(log or f"{target_card.name_cn}移入弃牌堆")

    def _atomic_move_to_hand(self, player_id, card, params, log, choice, context):
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'selected_card'}), card)
        if not target_card:
            return
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        if not (0 <= target_id < len(self.players)):
            return
        if not self.players[target_id].can_add_to_hand():
            return
        self._remove_card_from_current_zone(target_card)
        self.players[target_id].add_to_hand(target_card)
        self.log_msg(log or f"{target_card.name_cn}移入{self.pn(target_id)}手牌")

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
                'vulnus': ps.vulnerable,
                'vulnerable': ps.vulnerable,
                '易伤': ps.vulnerable,
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
            a = int(self.players[tid].custom_vars.get(name, 0))
            b = int(self._eval_expr(player_id, cond.get('value', 0), card))
            cmp = cond.get('operator', '=')
            return (a == b) if cmp == '=' else (a != b) if cmp == '!=' else (a < b) if cmp == '<' else (a > b) if cmp == '>' else (a <= b) if cmp == '<=' else (a >= b)
        if op == 'has_status_named':
            tid = self._resolve_target(player_id, cond.get('target', 'self'))
            status = str(cond.get('status', '')).strip()
            if status == '邪眼':
                return bool(self.players[tid].nazar_active)
            ps = self.players[tid]
            status_map = {
                'poison': ps.poison > 0,
                '中毒': ps.poison > 0,
                'burn': ps.fire > 0,
                'fire': ps.fire > 0,
                '灼烧': ps.fire > 0,
                'vulnus': ps.vulnerable > 0,
                'vulnerable': ps.vulnerable > 0,
                '易伤': ps.vulnerable > 0,
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
            ps = self.players[tid]
            status_map = {
                'poison': ps.poison > 0,
                'burn': ps.fire > 0,
                'vulnus': ps.vulnerable > 0,
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

    def _run_effect_list(self, player_id, card, effects, choice, context):
        for eff in effects or []:
            et = eff if isinstance(eff, str) else eff.get('type', '')
            pm = {} if isinstance(eff, str) else eff.get('params', {})
            lg = None if isinstance(eff, str) else eff.get('log')
            rt = self._EFFECT_ALIASES.get(et, et)
            fn = getattr(self, f'_atomic_{rt}', None)
            if callable(fn):
                fn(player_id, card, pm, lg, choice, context)
            elif lg:
                self.log_msg(lg)
            else:
                self.log_msg(f"未实现效果: {et}")

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
        original_id = active_choice.get('target_instance_id')
        original_index = active_choice.get('_selected_card_index')
        body = params.get('body', [])
        base_context = context if isinstance(context, dict) else ({'context': context} if context else {})
        try:
            for idx, instance_id in enumerate(list(ids), start=1):
                active_choice['target_instance_id'] = instance_id
                active_choice['_selected_card_index'] = idx
                try:
                    self._run_effect_list(player_id, card, body, active_choice, {**base_context, 'selected_card_index': idx})
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

    def _atomic_break(self, player_id, card, params, log, choice, context):
        raise ModLoopBreak()

    def _atomic_continue(self, player_id, card, params, log, choice, context):
        raise ModLoopContinue()

    def _atomic_after_all(self, player_id, card, params, log, choice, context):
        self._run_effect_list(player_id, card, params.get('body', []), choice, context)

    def _atomic_random(self, player_id, card, params, log, choice, context):
        branch = params.get('a', []) if random.random() < 0.5 else params.get('b', [])
        self._run_effect_list(player_id, card, branch, choice, context)

    def _atomic_var_set(self, player_id, card, params, log, choice, context):
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            ps = self.players[tid]
            name = str(params.get('name', 'var'))
            ps.custom_vars[name] = int(params.get('value', 0))
            self.log_msg(log or f"{self.pn(tid)}变量[{name}]={ps.custom_vars[name]}")

    def _atomic_var_add(self, player_id, card, params, log, choice, context):
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            ps = self.players[tid]
            name = str(params.get('name', 'var'))
            ps.custom_vars[name] = int(ps.custom_vars.get(name, 0) + int(params.get('value', 0)))
            self.log_msg(log or f"{self.pn(tid)}变量[{name}]={ps.custom_vars[name]}")

    def _atomic_var_sub(self, player_id, card, params, log, choice, context):
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            ps = self.players[tid]
            name = str(params.get('name', 'var'))
            ps.custom_vars[name] = int(ps.custom_vars.get(name, 0) - int(params.get('value', 0)))
            self.log_msg(log or f"{self.pn(tid)}变量[{name}]={ps.custom_vars[name]}")

    def _atomic_var_mul(self, player_id, card, params, log, choice, context):
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            ps = self.players[tid]
            name = str(params.get('name', 'var'))
            ps.custom_vars[name] = int(ps.custom_vars.get(name, 0) * int(params.get('value', 1)))
            self.log_msg(log or f"{self.pn(tid)}变量[{name}]={ps.custom_vars[name]}")

    def _atomic_var_div(self, player_id, card, params, log, choice, context):
        div = max(1, int(params.get('value', 1)))
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            ps = self.players[tid]
            name = str(params.get('name', 'var'))
            ps.custom_vars[name] = int(ps.custom_vars.get(name, 0) // div)
            self.log_msg(log or f"{self.pn(tid)}变量[{name}]={ps.custom_vars[name]}")

    def _atomic_batch_var_add(self, player_id, card, params, log, choice, context):
        for tid in self._resolve_targets(player_id, params.get('targets', 'friendly')):
            self._atomic_var_add(player_id, card, {'target': 'self' if tid == player_id else 'enemy', 'name': params.get('name', 'var'), 'value': params.get('value', 0)}, log, choice, context)

    def _atomic_batch_var_sub(self, player_id, card, params, log, choice, context):
        for tid in self._resolve_targets(player_id, params.get('targets', 'friendly')):
            self._atomic_var_sub(player_id, card, {'target': 'self' if tid == player_id else 'enemy', 'name': params.get('name', 'var'), 'value': params.get('value', 0)}, log, choice, context)

    def _atomic_batch_var_mul(self, player_id, card, params, log, choice, context):
        for tid in self._resolve_targets(player_id, params.get('targets', 'friendly')):
            self._atomic_var_mul(player_id, card, {'target': 'self' if tid == player_id else 'enemy', 'name': params.get('name', 'var'), 'value': params.get('value', 1)}, log, choice, context)

    def _atomic_batch_var_div(self, player_id, card, params, log, choice, context):
        for tid in self._resolve_targets(player_id, params.get('targets', 'friendly')):
            self._atomic_var_div(player_id, card, {'target': 'self' if tid == player_id else 'enemy', 'name': params.get('name', 'var'), 'value': params.get('value', 1)}, log, choice, context)

    def _atomic_status_add_named(self, player_id, card, params, log, choice, context):
        status = str(params.get('status', '')).strip()
        amount = int(params.get('amount', 1))
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            ps = self.players[tid]
            if status == '邪眼':
                ps.nazar_active = True
                ps.nazar_big_hits = max(0, ps.nazar_big_hits + amount)
            elif status in ('poison', '中毒'):
                ps.poison += amount
            elif status in ('burn', 'fire', '灼烧'):
                ps.fire += amount
            elif status in ('vulnus', 'vulnerable', '易伤'):
                ps.vulnerable += amount
            elif status in ('toxic', '淬毒'):
                ps.toxic += amount
            elif status in ('dodge', '闪避'):
                ps.dodge += amount
            elif status in ('equip_protection', 'equipment_protection', '装备摧毁保护', '装备保护'):
                ps.equipment_protection += amount
            self.log_msg(log or f"{self.pn(tid)}获得状态[{status}] {amount}")

    def _atomic_status_remove_named(self, player_id, card, params, log, choice, context):
        status = str(params.get('status', '')).strip()
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            ps = self.players[tid]
            if status == '邪眼':
                ps.nazar_active = False
                ps.nazar_big_hits = 0
            elif status in ('poison', '中毒'):
                ps.poison = 0
            elif status in ('burn', 'fire', '灼烧'):
                ps.fire = 0
            elif status in ('vulnus', 'vulnerable', '易伤'):
                ps.vulnerable = 0
            elif status in ('toxic', '淬毒'):
                ps.toxic = 0
            elif status in ('dodge', '闪避'):
                ps.dodge = 0
            elif status in ('equip_protection', 'equipment_protection', '装备摧毁保护', '装备保护'):
                ps.equipment_protection = 0
            self.log_msg(log or f"{self.pn(tid)}移除状态[{status}]")

    def _atomic_batch_status_add(self, player_id, card, params, log, choice, context):
        for tid in self._resolve_targets(player_id, params.get('targets', 'friendly')):
            self._atomic_status_add_named(player_id, card, {'target': 'self' if tid == player_id else 'enemy', 'status': params.get('status', ''), 'amount': params.get('amount', 1)}, log, choice, context)

    def _atomic_batch_status_remove(self, player_id, card, params, log, choice, context):
        for tid in self._resolve_targets(player_id, params.get('targets', 'friendly')):
            self._atomic_status_remove_named(player_id, card, {'target': 'self' if tid == player_id else 'enemy', 'status': params.get('status', '')}, log, choice, context)

    def _atomic_tag_add_named(self, player_id, card, params, log, choice, context):
        tag = str(params.get('tag', '')).strip()
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if tag and target_card:
            target_card.instance_flags = getattr(target_card, 'instance_flags', set())
            target_card.instance_flags.add(tag)
            self.log_msg(log or f"{target_card.name_cn}添加标签[{tag}]")

    def _atomic_tag_remove_named(self, player_id, card, params, log, choice, context):
        tag = str(params.get('tag', '')).strip()
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if tag and target_card:
            target_card.instance_flags = getattr(target_card, 'instance_flags', set())
            target_card.instance_flags.discard(tag)
            self.log_msg(log or f"{target_card.name_cn}移除标签[{tag}]")

    def _atomic_batch_tag_add(self, player_id, card, params, log, choice, context):
        self._atomic_tag_add_named(player_id, card, {'tag': params.get('tag', '')}, log, choice, context)

    def _atomic_batch_tag_remove(self, player_id, card, params, log, choice, context):
        self._atomic_tag_remove_named(player_id, card, {'tag': params.get('tag', '')}, log, choice, context)

    def _modified_attack_damage(self, base: int, card: CardInstance) -> int:
        base += max(0, int(getattr(card, 'bonus_damage', 0)))
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
        hits = 4
        self.log_msg(f"{self.pn(player_id)}使用沙子！造成{dmg}x{hits}伤害")
        self.deal_attack_damage(1 - player_id, dmg, hits)

    def _effect_wing(self, player_id: int, card: CardInstance, choice=None):
        dmg = self._modified_attack_damage(8, card)
        hits = 2
        self.log_msg(f"{self.pn(player_id)}使用翅膀！造成{dmg}x{hits}伤害")
        self.deal_attack_damage(1 - player_id, dmg, hits)

    def _effect_light(self, player_id: int, card: CardInstance, choice=None):
        dmg = self._modified_attack_damage(2, card)
        hits = 2
        self.log_msg(f"{self.pn(player_id)}使用轻！造成{dmg}x{hits}伤害")
        self.deal_attack_damage(1 - player_id, dmg, hits)

    def _effect_fang(self, player_id: int, card: CardInstance, choice=None):
        dmg = self._modified_attack_damage(8, card)
        dealt = self.deal_attack_damage(1 - player_id, dmg)
        if dealt > 0:
            self.players[player_id].heal(4)
            self.log_msg(f"{self.pn(player_id)}使用尖牙！造成{dealt}伤害，回复4H")
        else:
            self.log_msg(f"{self.pn(player_id)}使用尖牙！未造成伤害")

    def _effect_triangle(self, player_id: int, card: CardInstance, choice=None):
        ps = self.players[player_id]
        base = 6 + 3 * ps.triangle_stacks
        dmg = self._modified_attack_damage(base, card)
        dealt = self.deal_attack_damage(1 - player_id, dmg)
        if dealt > 0:
            if ps.triangle_stacks < 4:
                ps.triangle_stacks += 1
            self.log_msg(f"{self.pn(player_id)}使用三角形！造成{dealt}伤害，三角形层数+1（{ps.triangle_stacks}）")
        else:
            self.log_msg(f"{self.pn(player_id)}使用三角形！未造成伤害")

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
            if target and target.card_type == 'thorn':
                target.fission_level = max(1, int(getattr(target, 'fission_level', 1))) + 2
                target.fission_count = target.fission_level - 1
                self.log_msg(f"{self.pn(player_id)}使用裂变：{target.name_cn}裂变层数+2")
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
            cards = [c for c in cards if c is not None]
            if len(cards) < 2:
                return
            if len(cards) > 3:
                cards = cards[:3]
            if any(c.card_type != 'thorn' for c in cards) or len({c.def_id for c in cards}) != 1:
                self.log_msg(f"{self.pn(player_id)}使用聚变，但目标不是同名攻击牌")
                return
            first = cards[0]
            first.fusion_level = sum(max(1, int(getattr(c, 'fusion_level', 1))) for c in cards)
            first.fission_level = max(max(1, int(getattr(c, 'fission_level', 1))) for c in cards)
            first.fusion_multiplier = float(first.fusion_level)
            first.fission_count = first.fission_level - 1
            for c in cards[1:]:
                ps.hand.remove(c)
                self._discard_card(ps, c)
            self.log_msg(f"{self.pn(player_id)}使用聚变：{first.name_cn}聚变{first.fusion_level} 裂变{first.fission_level}，合并{len(cards)}张")
        else:
            self.log_msg(f"{self.pn(player_id)}使用聚变，但未选择目标")

    def _effect_iris(self, player_id: int, card: CardInstance, choice=None):
        self.players[1 - player_id].poison += 10
        self.log_msg(f"{self.pn(player_id)}使用鸢尾！敌方+10中毒")

    def _effect_fire(self, player_id: int, card: CardInstance, choice=None):
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
            if target:
                ps.remove_hand_card(target.instance_id)
                ps.discard.append(target)
                ps.draw_cards(1)
                self.log_msg(f"{self.pn(player_id)}使用辣椒！丢弃{target.name_cn}，抽1张牌")
        else:
            ps.draw_cards(1)
            self.log_msg(f"{self.pn(player_id)}使用辣椒！抽1张牌")

    def _effect_chromosome(self, player_id: int, card: CardInstance, choice=None):
        ps = self.players[player_id]
        if choice and 'target_def_id' in choice:
            target_def = choice['target_def_id']
            for i, c in enumerate(ps.discard):
                if c.def_id == target_def:
                    found = ps.discard.pop(i)
                    if ps.can_add_to_hand():
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
                destroyed = self._destroy_equipment(1 - player_id, eq)
                if destroyed:
                    self.log_msg(f"{self.pn(player_id)}使用污水！摧毁了敌方的{eq.card_def.name_cn}")
                else:
                    self.log_msg(f"{self.pn(player_id)}使用污水，但装备保护抵消了摧毁")
            else:
                self.log_msg(f"{self.pn(player_id)}使用污水，但目标不可摧毁或不存在")
        else:
            destroyable = [e for e in opp.equipment if 'indestructible' not in e.card_instance.flags]
            if destroyable:
                eq = destroyable[0]
                destroyed = self._destroy_equipment(1 - player_id, eq)
                if destroyed:
                    self.log_msg(f"{self.pn(player_id)}使用污水！摧毁了敌方的{eq.card_def.name_cn}")
                else:
                    self.log_msg(f"{self.pn(player_id)}使用污水，但装备保护抵消了摧毁")

    def _effect_magicsewage(self, player_id: int, card: CardInstance, choice=None):
        for pid in range(2):
            p = self.players[pid]
            to_destroy = [e for e in p.equipment if 'indestructible' not in e.card_instance.flags]
            for eq in to_destroy:
                destroyed = self._destroy_equipment(pid, eq)
                if destroyed:
                    self.log_msg(f"魔法污水摧毁了{self.pn(pid)}的{eq.card_def.name_cn}")
                else:
                    self.log_msg(f"魔法污水试图摧毁{self.pn(pid)}的{eq.card_def.name_cn}，但装备保护抵消了")

    def _effect_mimic(self, player_id: int, card: CardInstance, choice=None):
        ps = self.players[player_id]
        if choice and 'target_instance_id' in choice:
            target = ps.find_hand_card(choice['target_instance_id'])
            if target:
                copy_card = target.copy()
                copy_card.mimic_discount = 1
                if ps.can_add_to_hand():
                    ps.add_to_hand(copy_card)
                    self.log_msg(f"{self.pn(player_id)}使用了{card.name_cn}")
                else:
                    self.log_msg(f"{self.pn(player_id)}使用了{card.name_cn}，但手牌已满")

    def _effect_yggdrasil(self, player_id: int, card: CardInstance, choice=None):
        ps = self.players[player_id]
        ps.heal(20)
        self.log_msg(f"{self.pn(player_id)}使用世界树之叶！+20H")

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
        opp.toxic += 1
        self.log_msg(f"{self.pn(player_id)}装备了癌细胞！敌方+1淬毒")

    def _effect_corruption(self, player_id: int, card: CardInstance, choice=None):
        self.log_msg(f"{self.pn(player_id)}装备了腐化！下回合起全场伤害翻倍")

    def _effect_mark(self, player_id: int, card: CardInstance, choice=None):
        pass

    def _effect_mine(self, player_id: int, card: CardInstance, choice=None):
        pass

    def _destroy_equipment(self, owner_id: int, eq: EquipmentInstance, check_protection: bool = True,
                           source_id: Optional[int] = None) -> bool:
        ps = self.players[owner_id]
        if check_protection and ps.equipment_protection > 0:
            ps.equipment_protection -= 1
            self.log_msg(f"{self.pn(owner_id)}的装备保护抵消了摧毁！")
            return False
        if eq.def_id == 'Disc':
            effect_target = int(getattr(eq, 'effect_target', getattr(eq, 'owner', owner_id)))
            if not (0 <= effect_target < len(self.players)):
                effect_target = owner_id
            self.players[effect_target].armor = max(0, self.players[effect_target].armor - 2)
        has_destroy_script = self._has_card_event(eq.card_def, 'equipment_destroy')
        if has_destroy_script:
            self._run_card_event(owner_id, eq.card_instance, 'equipment_destroy', None,
                                 {'source_id': owner_id, 'target_id': owner_id})
        elif eq.def_id == 'Sponge' and ps.sponge_active:
            poison_layers = ps.poison
            ps.sponge_active = False
            ps.poison = 0
            if poison_layers > 0:
                physical_dmg = poison_layers * 2
                ps.health -= physical_dmg
                self.log_msg(f"海绵被摧毁！去除{poison_layers}层中毒，受到{physical_dmg}点物理伤害")
                self._check_yggdrasil(player_id)
            else:
                self.log_msg("海绵被摧毁！无中毒层数")
        if not has_destroy_script and eq.def_id == 'Pill':
            ps.enemy_draw_reduction = max(0, ps.enemy_draw_reduction - 1)
            ps.enemy_e_reduction = max(0, ps.enemy_e_reduction - 1)
            self.log_msg("药丸被摧毁！己方抽牌和回E恢复正常")
        ps.equipment.remove(eq)
        if 'exile' in eq.card_instance.flags:
            ps.exile.append(eq.card_instance)
        else:
            self._discard_card(ps, eq.card_instance)
        self._dispatch_card_event('equipment_destroyed', owner_id if source_id is None else source_id,
                                  eq.card_instance, target_id=owner_id,
                                  equipment=eq, equipment_owner_id=owner_id)
        return True

    def check_equipment_destroy_response(self, owner_id: int, eq: EquipmentInstance) -> dict:
        ps = self.players[owner_id]
        has_magic_nazar = any(c.card_def.response_trigger == 'equipment_destroy' for c in ps.hand)
        if has_magic_nazar and ps.equipment_protection == 0:
            return {'needs_response': True, 'response_type': 'equipment_destroy',
                    'equipment': eq.to_dict(), 'owner_id': owner_id}
        return {'needs_response': False}

    def use_trigger(self, player_id: int, equipment_instance_id: int) -> dict:
        if self.current_player != player_id:
            return {'success': False, 'error': '不是你的回合'}
        ps = self.players[player_id]
        eq = ps.find_equipment(equipment_instance_id)
        if eq is None:
            return {'success': False, 'error': '装备不存在'}
        if eq.card_def.trigger_cost_e < 0:
            return {'success': False, 'error': '该装备没有触发效果'}
        if eq.turns_equipped < 1:
            return {'success': False, 'error': '装备需要装备一回合后才能触发'}
        if eq.card_def.trigger_cost_e > ps.elixir:
            return {'success': False, 'error': '能量不足'}
        ps.elixir -= eq.card_def.trigger_cost_e
        opp_id = 1 - player_id
        opp = self.players[opp_id]
        if eq.def_id == 'Leaf':
            destroyed = self._destroy_equipment(player_id, eq)
            if destroyed:
                self.deal_attack_damage(opp_id, 8)
                self.log_msg(f"{self.pn(player_id)}触发叶子！造成8D")
        elif eq.def_id == 'Mark':
            destroyed = self._destroy_equipment(player_id, eq)
            if destroyed:
                opp.skip_turn = True
                self.log_msg(f"{self.pn(player_id)}触发标记！敌方下回合不能行动")
        elif eq.def_id == 'Mine':
            destroyed = self._destroy_equipment(player_id, eq)
            if destroyed:
                self.deal_attack_damage(opp_id, 20)
                self.log_msg(f"{self.pn(player_id)}触发地雷！造成20D")
        self._check_game_over()
        return {'success': True}

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
        if ps.bandage_death_pending:
            ps.health = 0
            ps.bandage_death_pending = False
            ps.invincible = False
            self.log_msg(f"{self.pn(player_id)}的绷带效果结束，死亡！")
            self._check_game_over()
            if self.game_over:
                return
        if ps.bandage_active and ps.invincible:
            ps.bandage_active = False
            ps.bandage_death_pending = True
            self.log_msg(f"{self.pn(player_id)}的绷带无敌将持续到下个友方回合结束")
        void_cards = [c for c in ps.hand if 'void' in c.flags]
        for c in void_cards:
            ps.hand.remove(c)
            ps.exile.append(c)
            self.log_msg(f"{self.pn(player_id)}的{c.name_cn}因虚无被放逐")
        if ps.attack_blocked > 0:
            ps.attack_blocked -= 1
        if ps.attack_only > 0:
            ps.attack_only -= 1
        if player_id == self.first_player:
            other = 1 - self.first_player
            self._start_player_turn(other)
        else:
            self._end_round()

    def _end_round(self):
        for pid in range(2):
            ps = self.players[pid]
            if ps.invincible and not ps.bandage_active and not ps.bandage_death_pending:
                ps.invincible = False
                self.log_msg(f"{self.pn(pid)}的无敌效果结束")
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
        return [c for c in ps.hand if c.card_def.response_trigger == trigger_type]

    def get_attack_cards_in_hand(self, player_id: int) -> List[CardInstance]:
        return [c for c in self.players[player_id].hand if c.card_type == 'thorn']

    def get_enemy_equipment(self, player_id: int) -> List[EquipmentInstance]:
        return self.players[1 - player_id].equipment

    EVENT_EFFECT_TYPES = {
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
        'enemy_turn_start': ('onEnemyTurnStart', 'enemy_turn_start', 'on_enemy_turn_start'),
        'any_turn_start': ('onAnyTurnStart', 'any_turn_start', 'on_any_turn_start'),
        'damage_taken': ('onDamageTaken', 'damage_taken', 'on_damage_taken'),
        'equipment_trigger': ('onEquipmentTrigger', 'equipment_trigger', 'on_equipment_trigger'),
        'equipment_destroy': ('onEquipmentDestroy', 'equipment_destroy', 'on_equipment_destroy', 'onDestroy'),
        'hand_owner_turn_start': ('onHandOwnerTurnStart', 'hand_owner_turn_start', 'on_hand_owner_turn_start'),
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
        return any(isinstance(effect, dict) and effect.get('type') == event_type for effect in (card_def.effects or []))

    def _play_effects_for_card(self, card: CardInstance):
        if self._card_has_script(card.card_def):
            return self._get_script_effects(card.card_def, 'play')
        return card.card_def.effects or []

    def _walk_choice_effects(self, effects):
        for effect in effects or []:
            if not isinstance(effect, dict):
                continue
            effect_type = effect.get('type', '')
            if effect_type in self.EVENT_EFFECT_TYPES:
                continue
            yield effect
            params = effect.get('params', {}) or {}
            for key in ('then', 'else', 'body', 'effects', 'a', 'b'):
                nested = params.get(key)
                if isinstance(nested, list):
                    yield from self._walk_choice_effects(nested)

    def _get_choice_request(self, card: CardInstance):
        for effect in self._walk_choice_effects(self._play_effects_for_card(card)):
            effect_type = effect.get('type', '')
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
            return current_card if card_ref in ('current_card', 'this') else None
        if not isinstance(card_ref, dict):
            return None
        ref = card_ref.get('ref')
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
        if ref in ('selected_card', 'choice_card'):
            choice = getattr(self, '_active_choice', None) or {}
            if isinstance(choice, dict):
                instance_id = choice.get('target_instance_id')
                if instance_id is None and isinstance(choice.get('target_instance_ids'), list) and choice.get('target_instance_ids'):
                    instance_id = choice.get('target_instance_ids')[0]
                return self._find_card_by_instance_id(instance_id)
            return None
        if ref == 'selected_card_at':
            choice = getattr(self, '_active_choice', None) or {}
            if not isinstance(choice, dict):
                return None
            ids = choice.get('target_instance_ids')
            if not isinstance(ids, list):
                ids = [choice.get('target_instance_id')] if choice.get('target_instance_id') is not None else []
            index = self._eval_int(player_id, card_ref.get('index', 1), current_card, 1) - 1
            return self._find_card_by_instance_id(ids[index]) if 0 <= index < len(ids) else None
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
                    ps.equipment.remove(eq)
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

    def _resolve_target(self, player_id, target_str):
        context = getattr(self, '_active_effect_context', {}) or {}
        if isinstance(target_str, dict) and target_str.get('ref') == 'card_owner':
            target_card = self._resolve_card_ref(player_id, target_str.get('card'), None)
            owner_id, _, _ = self._find_card_location(target_card)
            return player_id if owner_id is None else owner_id
        if isinstance(target_str, int):
            return target_str
        if target_str in ('choice_target', 'selected_target', 'chosen_target'):
            target_id = self._selected_choice_target(player_id)
            return target_id if 0 <= target_id < len(self.players) else player_id
        if target_str in ('event_target', 'target'):
            return int(context.get('target_id', player_id))
        if target_str in ('event_source', 'source', 'last_actor', 'damage_source'):
            return int(context.get('source_id', player_id))
        return self._base_resolve_target(player_id, target_str)

    def _resolve_targets(self, player_id, target_str):
        if isinstance(target_str, dict) and target_str.get('ref') == 'card_owner':
            tid = self._resolve_target(player_id, target_str)
            return [] if tid < 0 else [tid]
        if target_str in ('choice_target', 'selected_target', 'chosen_target', 'event_target', 'target', 'event_source', 'source', 'last_actor', 'damage_source'):
            tid = self._resolve_target(player_id, target_str)
            return [] if tid < 0 else [tid]
        return self._base_resolve_targets(player_id, target_str)

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
                et = eff if isinstance(eff, str) else eff.get('type', '')
                pm = {} if isinstance(eff, str) else eff.get('params', {})
                lg = None if isinstance(eff, str) else eff.get('log')
                rt = self._EFFECT_ALIASES.get(et, et)
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
            ref = expr.get('ref')
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
            if ref == 'damage_amount':
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
            if ref in ('turn_damage_taken', 'turn_damage_dealt', 'total_damage_taken', 'total_damage_dealt'):
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
            if ref == 'card_property':
                target_card = self._resolve_card_ref(player_id, expr.get('card', {'ref': 'current_card'}), card)
                if target_card is None:
                    return 0
                prop = str(expr.get('property', 'fusion_level'))
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
                flags = set(getattr(target_card.card_def, 'flags', set()) or set())
                flags.update(getattr(target_card, 'instance_flags', set()) or set())
                flags.difference_update(getattr(target_card, 'disabled_flags', set()) or set())
                return len(flags)
            if ref == 'card_def_property':
                return self._get_card_def_property_value(player_id, expr.get('card', ''), expr.get('property', 'cost_e'), card)
            if ref == 'card_def_tags':
                return self._get_card_def_tags(player_id, expr.get('card', ''), card)
            if ref == 'equipment_property':
                eq = self._resolve_equipment_ref(player_id, expr.get('equipment', {'ref': 'current_equipment'}), card)
                return self._get_equipment_property_value(eq, expr.get('property', 'turns_equipped'))
            if ref == 'player_property':
                target_id = self._resolve_target(player_id, expr.get('target', 'self'))
                return self._get_player_property_value(target_id, expr.get('property', 'health'))
            if ref == 'var':
                target = expr.get('target', 'self')
                name = str(expr.get('name', 'var'))
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
            a = int(self._scalar_value(self._var_store_for_target(player_id, cond.get('target', 'self')).get(name, 0), 0))
            b = int(self._eval_expr(player_id, cond.get('value', 0), card))
            cmp = cond.get('operator', '=')
            return (a == b) if cmp == '=' else (a != b) if cmp == '!=' else (a < b) if cmp == '<' else (a > b) if cmp == '>' else (a <= b) if cmp == '<=' else (a >= b)
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
            tag = str(cond.get('tag', '')).strip()
            flags = set(getattr(target_card.card_def, 'flags', set()) or set())
            flags.update(getattr(target_card, 'instance_flags', set()) or set())
            flags.difference_update(getattr(target_card, 'disabled_flags', set()) or set())
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
        if self._base_card_needs_choice(card):
            return True
        return self._get_choice_request(card) is not None

    def _get_choice_type(self, card: CardInstance) -> str:
        effect = self._get_choice_request(card)
        if effect:
            effect_type = effect.get('type', '')
            params = effect.get('params', {}) or {}
            if effect_type == 'request_target':
                return 'choose_target'
            if effect_type == 'request_card':
                if params.get('multi') or params.get('choice_type') == 'choose_cards_from_hand':
                    return 'choose_cards_from_hand'
                return params.get('choice_type') or params.get('zone') or 'choose_card_from_hand'
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
        base = self._base_get_choice_type(card)
        return base or ''

    def _choice_satisfies_request(self, card: CardInstance, choice) -> bool:
        if not self._card_needs_choice(card):
            return True
        if not isinstance(choice, dict):
            return False
        choice_request = self._get_choice_request(card)
        choice_type = self._get_choice_type(card)
        params = choice_request.get('params', {}) if isinstance(choice_request, dict) else {}
        effect_type = choice_request.get('type', '') if isinstance(choice_request, dict) else ''
        if choice.get('cancelled') and params.get('continue_on_cancel'):
            return True
        if effect_type == 'request_target' or choice_type == 'choose_target':
            return any(key in choice for key in ('target_player', 'target_player_id', 'target_id'))
        if effect_type == 'request_confirm' or choice_type == 'confirm':
            return any(key in choice for key in ('confirmed', 'accepted'))
        if choice_type == 'choose_same_attacks_from_hand':
            ids = choice.get('target_instance_ids')
            return isinstance(ids, list) and bool(ids)
        if choice_type == 'choose_cards_from_hand':
            ids = choice.get('target_instance_ids')
            if isinstance(ids, list) and bool(ids):
                return True
            min_count = self._eval_int(0, params.get('min_count', 1), card, 1) if params else 1
            max_count = self._eval_int(0, params.get('max_count', min_count), card, min_count) if params else 1
            if min_count <= 1 and max_count <= 1 and choice.get('target_instance_id') is not None:
                return True
            return False
        if choice_type in ('choose_card_from_discard',):
            return choice.get('target_def_id') is not None or choice.get('target_instance_id') is not None
        if choice_type in (
            'choose_attack_from_hand', 'choose_card_from_hand', 'choose_card_to_discard',
            'choose_from_deck', 'choose_from_discard', 'choose_from_exile',
            'choose_equipment', 'choose_enemy_equipment', 'choose_from_enemy_hand',
        ):
            return choice.get('target_instance_id') is not None or choice.get('target_def_id') is not None
        return bool(choice)

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
        if self._card_has_script(card.card_def) or card.card_def.effects:
            self._process_atomic_effects(player_id, card, choice, 'play')
            return
        method_name = f'_effect_{card.def_id.lower()}'
        if hasattr(self, method_name):
            getattr(self, method_name)(player_id, card, choice)
        else:
            self.log_msg(f"{self.pn(player_id)}使用了{card.name_cn}")

    def _uses_atomic_play_effects(self, card: CardInstance) -> bool:
        return bool(self._card_has_script(card.card_def) or card.card_def.effects)

    def _log_card_play(self, player_id: int, card: CardInstance):
        self.log_msg(f"{self.pn(player_id)}使用了{card.name_cn}")

    def _effective_card_flags(self, target_card: Optional[CardInstance]) -> Set[str]:
        if target_card is None:
            return set()
        flags = set(getattr(target_card.card_def, 'flags', set()) or set())
        flags.update(getattr(target_card, 'instance_flags', set()) or set())
        flags.difference_update(getattr(target_card, 'disabled_flags', set()) or set())
        return flags

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
        event_card_id = getattr(event_card, 'instance_id', None)
        context = {
            'source_id': source_id,
            'target_id': source_id if target_id is None else target_id,
            'event_card_instance_id': event_card_id,
            'event_card_type': getattr(event_card, 'card_type', getattr(getattr(event_card, 'card_def', None), 'card_type', '')),
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
            self._run_card_event(owner_id, listener_card, event_name, choice, context)

    TRACKED_PLAYER_STATS = (
        'health', 'max_health', 'elixir', 'max_elixir', 'magic', 'max_magic',
        'armor', 'dodge', 'poison', 'fire', 'vulnerable', 'toxic',
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
                    {'event': event_name, 'repeat_index': repeat_index + 1, **(extra_context or {})},
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

    def _apply_turn_start_effects(self, player_id: int):
        ps = self.players[player_id]
        opp_id = 1 - player_id
        opp = self.players[opp_id]
        self._antenna_reveal[player_id] = None
        self._reset_turn_damage_counters()
        self._run_zone_owner_turn_start_events(player_id)
        self._run_timed_effects_for_turn(player_id)
        if ps.shovel_active:
            ps.shovel_active = False
            ps.untargetable = False
            self.log_msg(f"{self.pn(player_id)}的铲子效果结束")
        if self.round_num > 1:
            draw_count = max(0, DRAW_PER_TURN - ps.enemy_draw_reduction)
            ps.draw_cards(draw_count)
            self.log_msg(f"{self.pn(player_id)}抽{draw_count}张牌")
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
        if ps.poison > 0:
            dmg = ps.poison
            self._deal_direct_damage(player_id, dmg, '中毒')
            if self.game_over or ps.health <= 0:
                return
            ps.poison = ps.poison // 2
        if ps.fire > 0:
            self._deal_direct_damage(player_id, ps.fire, '灼烧')
            if self.game_over or ps.health <= 0:
                return
        if self.round_num > 1:
            elixir_recovery = ELIXIR_RECOVERY
            for eq in list(opp.equipment):
                if eq.card_def.effects:
                    for effect in eq.card_def.effects:
                        if isinstance(effect, dict) and effect.get('type') == 'aura_enemy_elixir_recovery':
                            elixir_recovery += self._eval_int(opp_id, effect.get('params', {}).get('amount', 0), eq.card_instance)
                    continue
                if eq.def_id == 'Pincer':
                    elixir_recovery -= 1
            elixir_recovery = max(0, elixir_recovery - ps.enemy_e_reduction)
            ps.gain_elixir(elixir_recovery)
            self.log_msg(f"{self.pn(player_id)}回复{elixir_recovery}E")
        if self.opening_event_picks[player_id] == 5 and self.round_num <= 2:
            draw_needed = ps.hand_space()
            if draw_needed > 0:
                ps.draw_cards(draw_needed)
                self.log_msg(f"{self.pn(player_id)}抽{draw_needed}张至手牌满")
        if self.opening_event_picks[player_id] == 6 and self.round_num <= 3:
            ps.gain_elixir(2)
            self.log_msg(f"{self.pn(player_id)}额外+2E")
        for owner_state in self.players:
            for eq in getattr(owner_state, 'equipment', []):
                eq.uses_this_turn = 0
        for eq in list(ps.equipment):
            eq.turns_equipped += 1
            if self._has_card_event(eq.card_def, 'owner_turn_start') and self._run_card_event(
                    player_id, eq.card_instance, 'owner_turn_start', None,
                    {'source_id': player_id, 'target_id': player_id}):
                continue
            if eq.def_id == 'Leaf':
                ps.heal(2)
                self.log_msg(f"{self.pn(player_id)}的叶子效果：+2H")
            elif eq.def_id == 'Yucca':
                ps.heal(5)
                self.log_msg(f"{self.pn(player_id)}的丝兰效果：+5H")
            elif eq.def_id == 'MagicLeaf':
                ps.gain_magic(1)
                self.log_msg(f"{self.pn(player_id)}的魔法叶效果：+1M")
            elif eq.def_id == 'MagicYucca':
                ps.gain_magic(2)
                self.log_msg(f"{self.pn(player_id)}的魔法丝兰效果：+2M")
            elif eq.def_id == 'Powder':
                ps.gain_elixir(2)
                self.log_msg(f"{self.pn(player_id)}的粉末效果：+2E")
            elif eq.def_id == 'GoldenLeaf':
                ps.draw_cards(1)
                self.log_msg(f"{self.pn(player_id)}的黄金叶效果：多抽1张牌")

    def deal_attack_damage(self, target_id: int, amount: int, hits: int = 1,
                           is_battery: bool = False, is_precision: bool = False,
                           attacker_id: int = -1) -> int:
        ps = self.players[target_id]
        if attacker_id < 0:
            attacker_id = 1 - target_id
        if ps.untargetable and not is_battery:
            self.log_msg(f"{self.pn(target_id)}无法被攻击选中")
            return 0
        total_dealt = 0
        for _ in range(hits):
            if ps.dodge > 0:
                ps.dodge -= 1
                if is_precision:
                    self.log_msg(f"{self.pn(target_id)}的闪避被精准消耗")
                else:
                    self.log_msg(f"{self.pn(target_id)}闪避了攻击")
                    continue
            if ps.invincible:
                self.log_msg(f"{self.pn(target_id)}无敌，免疫伤害")
                continue
            if amount <= 0 and hits <= 1:
                break
            dmg = amount
            if self.halve_next_attack:
                dmg = math.ceil(dmg / 2)
            corruption_count = self._get_corruption_count()
            if corruption_count > 0:
                dmg *= (2 ** corruption_count)
            if ps.nazar_active:
                original_dmg = dmg
                dmg = max(1, dmg - 9)
                if original_dmg >= 10:
                    ps.nazar_big_hits += 1
                    if ps.nazar_big_hits >= 2:
                        ps.nazar_active = False
                        ps.nazar_big_hits = 0
            dmg = max(0, dmg - ps.armor)
            if ps.sponge_active and dmg > 0:
                ps.poison += dmg // 2
                dmg = 0
            ps.health -= dmg
            total_dealt += dmg
            self._record_damage(target_id, dmg, attacker_id)
            self.log_msg(f"{self.pn(target_id)}受到{dmg}点伤害（H={ps.health}）")
            if ps.toxic > 0:
                ps.poison += ps.toxic
            self._check_yggdrasil(target_id)
            if self.game_over:
                break
            if dmg > 0 and not is_battery:
                for eq in list(ps.equipment):
                    if self._has_card_event(eq.card_def, 'damage_taken') and self._run_card_event(
                            target_id, eq.card_instance, 'damage_taken', None,
                            {'source_id': attacker_id, 'target_id': target_id, 'damage': dmg}):
                        continue
                    if eq.def_id == 'Battery':
                        self._deal_direct_damage(attacker_id, 3, '电池', target_id)
                        self.log_msg(f"{self.pn(target_id)}的电池效果：对{self.pn(attacker_id)}造成3D")
                    elif eq.def_id == 'MagicBattery' and ps.magic_battery_m_this_turn < 3:
                        ps.gain_magic(1)
                        ps.magic_battery_m_this_turn += 1
                        self.log_msg(f"{self.pn(target_id)}的魔法电池效果：+1M")
            if self.game_over:
                break
            self._check_game_over()
            if ps.health <= 0:
                break
        return total_dealt

    def _execute_card_effect(self, player_id: int, card: CardInstance, choice: Optional[dict] = None) -> dict:
        ps = self.players[player_id]
        result = {'success': True, 'card': card.to_dict()}
        if card.card_type == 'thorn' and (card.fission_level > 1 or card.fusion_level > 1):
            self.log_msg(f"[特效] {card.name_cn} 聚变={card.fusion_level} 裂变={card.fission_level}")
        if self.negated_card and card.card_type == 'bloom':
            self.negated_card = False
            self._log_card_play(player_id, card)
            if 'exile' in card.flags:
                ps.exile.append(card)
            else:
                self._discard_card(ps, card)
            self._dispatch_card_event('card_used', player_id, card, target_id=player_id, choice=choice)
            return result
        self.negated_card = False
        needs_choice = self._card_needs_choice(card)
        if needs_choice and not self._choice_satisfies_request(card, choice):
            choice_request = self._get_choice_request(card)
            choice_params = (choice_request.get('params', {}) if isinstance(choice_request, dict) else {}) or {}
            choice_type = self._get_choice_type(card)
            choice_target_id = None
            if isinstance(choice_request, dict):
                request_type = choice_request.get('type')
                target_defaults = {
                    'request_card': 'self',
                    'choose_from_deck': 'self',
                    'choose_from_discard': 'self',
                    'destroy_equipment_choice_or_first': 'enemy',
                    'steal_enemy_card': 'enemy',
                }
                if request_type in target_defaults:
                    choice_target_id = self._resolve_target(player_id, choice_params.get('target', target_defaults[request_type]))
            self.pending_choice = {
                'card': card.to_dict(),
                'player_id': player_id,
                'choice_type': choice_type,
                'choice_params': choice_params,
                'original_choice': dict(choice) if isinstance(choice, dict) else None,
            }
            if choice_target_id is not None:
                self.pending_choice['target_player_id'] = choice_target_id
            ps.hand.insert(0, card)
            ps.elixir += card.cost_e + ps.cards_played_this_turn.get(card.def_id, 1) - 1
            ps.magic += card.cost_m
            ps.cards_played_this_turn[card.def_id] = max(0, ps.cards_played_this_turn.get(card.def_id, 1) - 1)
            return {
                'success': True,
                'needs_choice': True,
                'choice_type': choice_type,
                'choice_params': choice_params,
                'target_player_id': choice_target_id,
                'card': card.to_dict(),
            }
        if self._uses_atomic_play_effects(card):
            self._log_card_play(player_id, card)
        if card.card_type == 'thorn':
            fission_level = max(1, int(getattr(card, 'fission_level', 1)))
            for hit_idx in range(fission_level):
                if self.game_over:
                    break
                card.fission_hit = hit_idx
                self._apply_card_effect(player_id, card, choice)
            card.fission_hit = 0
        else:
            self._apply_card_effect(player_id, card, choice)
        placed_as_equipment = bool(getattr(card, '_placed_as_equipment', False))
        script_controls_play = self._card_has_script(card.card_def)
        equip_owner_id = int(getattr(card, '_placed_as_equipment_owner', player_id))
        if equip_owner_id < 0 or equip_owner_id >= len(self.players):
            equip_owner_id = player_id
        equip_owner = self.players[equip_owner_id]
        if (card.card_type == 'root' and not script_controls_play) or placed_as_equipment:
            eq = self._find_equipment_for_card(equip_owner_id, card)
            if eq is None:
                eq = EquipmentInstance(card, equip_owner_id)
                if eq.def_id == 'Disc' and not card.card_def.effects:
                    effect_target = int(getattr(eq, 'effect_target', getattr(eq, 'owner', equip_owner_id)))
                    if not (0 <= effect_target < len(self.players)):
                        effect_target = equip_owner_id
                    self.players[effect_target].armor += 2
                equip_owner.equipment.append(eq)
                self.log_msg(f"{self.pn(equip_owner_id)}装备了{card.name_cn}")
            if hasattr(card, '_placed_as_equipment'):
                delattr(card, '_placed_as_equipment')
            if hasattr(card, '_placed_as_equipment_owner'):
                delattr(card, '_placed_as_equipment_owner')
        elif 'exile' in card.flags:
            owner_id, zone_name, _ = self._find_card_location(card)
            if owner_id is None or zone_name is None:
                ps.exile.append(card)
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
        self._check_game_over()
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
                if 0 <= effect_target < len(self.players):
                    eq.effect_target = effect_target
            else:
                selected_target = self._selected_choice_target(-1)
                if 0 <= selected_target < len(self.players):
                    eq.effect_target = selected_target
            owner.equipment.append(eq)
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
            new_card.durability = card_def.durability if getattr(card_def, 'durability', 0) > 0 else 3
            eq = EquipmentInstance(new_card, owner_id)
            if 'effect_target' in params:
                effect_target = self._resolve_target(player_id, params.get('effect_target'))
                if 0 <= effect_target < len(self.players):
                    eq.effect_target = effect_target
            else:
                eq.effect_target = owner_id
            self.players[owner_id].equipment.append(eq)
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

    def _atomic_aura_enemy_elixir_recovery(self, player_id, card, params, log, choice, context):
        return None

    def _atomic_destroy_self_equipment(self, player_id, card, params, log, choice, context):
        eq = self._find_equipment_for_card(player_id, card)
        if eq is not None:
            self._destroy_equipment(player_id, eq)

    def _atomic_deal_damage(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        amount = self._eval_int(player_id, params.get('amount', 6), card, 6)
        hits = max(1, self._eval_int(player_id, params.get('hits', 1), card, 1))
        is_precision = bool(params.get('is_precision', False))
        amount = self._modified_attack_damage(amount, card)
        self._incoming_damage_hint[target_id] = int(amount)
        try:
            dealt = self.deal_attack_damage(target_id, amount, hits, is_precision=is_precision, attacker_id=player_id)
        except TypeError:
            dealt = self.deal_attack_damage(target_id, amount, hits, is_precision=is_precision)
        self._last_damage_value[target_id] = int(dealt)
        self.log_msg(log or f"{self.pn(player_id)}对{self.pn(target_id)}造成{dealt}伤害")

    def _atomic_direct_damage(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self._deal_direct_damage(target_id, amount, str(params.get('source', card.name_cn if card else '效果')), player_id)

    def _atomic_lifesteal_damage(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        amount = self._eval_int(player_id, params.get('amount', 8), card, 8)
        heal = self._eval_int(player_id, params.get('heal', 4), card, 4)
        try:
            dealt = self.deal_attack_damage(target_id, amount, attacker_id=player_id)
        except TypeError:
            dealt = self.deal_attack_damage(target_id, amount)
        self._last_damage_value[target_id] = int(dealt)
        if dealt > 0:
            self.players[player_id].heal(heal)
            self.log_msg(log or f"{self.pn(player_id)}回复{heal}H")

    def _atomic_triangle_damage(self, player_id, card, params, log, choice, context):
        base = self._eval_int(player_id, params.get('base', 6), card, 6)
        per_stack = self._eval_int(player_id, params.get('per_stack', 3), card, 3)
        stack_name = str(params.get('stack_name', '三角形层数'))
        current_stack = int(self.players[player_id].custom_vars.get(stack_name, getattr(self.players[player_id], 'triangle_stacks', 0)))
        amount = base + per_stack * current_stack
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        try:
            dealt = self.deal_attack_damage(target_id, amount, attacker_id=player_id)
        except TypeError:
            dealt = self.deal_attack_damage(target_id, amount)
        self._last_damage_value[target_id] = int(dealt)
        if dealt > 0:
            max_stacks = self._eval_int(player_id, params.get('max_stacks', 4), card, 4)
            new_stack = min(max_stacks, current_stack + 1)
            self.players[player_id].custom_vars[stack_name] = new_stack
            if stack_name == '三角形层数':
                self.players[player_id].triangle_stacks = new_stack

    def _atomic_discard_choice_then_draw(self, player_id, card, params, log, choice, context):
        ps = self.players[player_id]
        if choice and 'target_instance_id' in choice:
            target = ps.find_hand_card(choice['target_instance_id'])
            if target:
                ps.hand.remove(target)
                ps.discard.append(target)
        ps.draw_cards(1)
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
        if target is None or not ps.can_add_to_hand():
            return
        copy_card = target.copy()
        copy_card.mimic_discount = self._eval_int(player_id, params.get('discount_e', 1), card, 1)
        ps.add_to_hand(copy_card)
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
            value = max(1, value)
        elif prop in ('mimic_discount', 'cost_e_override', 'cost_m_override', 'bonus_damage', 'return_to_hand_turns', 'held_turns'):
            value = max(0, value)
        if prop in ('fusion_level', 'fission_level', 'mimic_discount', 'cost_e_override', 'cost_m_override',
                    'bonus_damage', 'return_to_hand_turns', 'held_turns'):
            setattr(target_card, prop, value)
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
        return int(value)

    def _atomic_card_prop_set(self, player_id, card, params, log, choice, context):
        value = self._eval_int(player_id, params.get('value', 0), card)
        target_card = self._set_card_property_value(player_id, card, params, value)
        if target_card is not None and log:
            self.log_msg(log)

    def _atomic_card_prop_add(self, player_id, card, params, log, choice, context):
        target_card = self._resolve_card_ref(player_id, params.get('card', {'ref': 'current_card'}), card)
        if target_card is None:
            return
        prop = str(params.get('property', 'fusion_level'))
        current = self._get_card_property_numeric_value(target_card, prop)
        value = current + self._eval_int(player_id, params.get('amount', 0), card)
        self._set_card_property_value(player_id, card, params, value)
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
        prop = str(params.get('property', 'health'))
        value = self._eval_int(player_id, params.get('value', 0), card)
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            if self._set_player_property_value(tid, prop, value) is not None and log:
                self.log_msg(log)

    def _atomic_player_prop_add(self, player_id, card, params, log, choice, context):
        prop = str(params.get('property', 'health'))
        amount = self._eval_int(player_id, params.get('amount', 0), card)
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            current = self._get_player_property_value(tid, prop)
            if self._set_player_property_value(tid, prop, current + amount) is not None and log:
                self.log_msg(log)

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
            self._destroy_equipment(target_id, eq)

    def _atomic_destroy_random_equip(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if target_id < 0:
            return
        pool = [eq for eq in self.players[target_id].equipment if 'indestructible' not in eq.card_instance.flags]
        if not pool:
            return
        eq = random.choice(pool)
        self._destroy_equipment(target_id, eq)

    def _atomic_destroy_all_equip(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if target_id < 0:
            return
        for eq in list(self.players[target_id].equipment):
            if 'indestructible' not in eq.card_instance.flags:
                self._destroy_equipment(target_id, eq)

    def _atomic_destroy_all_destroyable_equipment(self, player_id, card, params, log, choice, context):
        for tid in self._resolve_targets(player_id, params.get('target', 'both')):
            for eq in list(self.players[tid].equipment):
                if 'indestructible' not in eq.card_instance.flags:
                    self._destroy_equipment(tid, eq)

    def _atomic_activate_corruption(self, player_id, card, params, log, choice, context):
        eq = self._find_equipment_for_card(player_id, card)
        if eq is not None:
            eq.corruption_active = True

    def _atomic_heal(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = self._eval_int(player_id, params.get('amount', 0), card)
        self.players[target_id].heal(amount)
        self.log_msg(log or f"{self.pn(target_id)}回复{amount}H")

    def _atomic_draw(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self.players[target_id].draw_cards(amount)
        self.log_msg(log or f"{self.pn(target_id)}抽{amount}张牌")

    def _atomic_gain_e(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self.players[target_id].gain_elixir(amount)
        self.log_msg(log or f"{self.pn(target_id)}获得{amount}E")

    def _atomic_gain_m(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self.players[target_id].gain_magic(amount)
        self.log_msg(log or f"{self.pn(target_id)}获得{amount}M")

    def _atomic_gain_armor(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self.players[target_id].armor += amount
        self.log_msg(log or f"{self.pn(target_id)}获得{amount}护甲")

    def _atomic_gain_dodge(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self.players[target_id].dodge += amount
        self.log_msg(log or f"{self.pn(target_id)}获得{amount}闪避")

    def _atomic_apply_poison(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self.players[target_id].poison += amount
        self._normalize_status_value(self.players[target_id], 'poison')
        self.log_msg(log or f"{self.pn(target_id)}+{amount}中毒")

    def _atomic_apply_burn(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self.players[target_id].fire += amount
        self._normalize_status_value(self.players[target_id], 'fire')
        self.log_msg(log or f"{self.pn(target_id)}+{amount}灼烧")

    def _atomic_apply_toxic(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self.players[target_id].toxic += amount
        self._normalize_status_value(self.players[target_id], 'toxic')
        self.log_msg(log or f"{self.pn(target_id)}+{amount}淬毒")

    def _atomic_apply_vulnerable(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        self.players[target_id].vulnerable += amount
        self._normalize_status_value(self.players[target_id], 'vulnerable')
        self.log_msg(log or f"{self.pn(target_id)}+{amount}易伤")

    def _atomic_status_add_named(self, player_id, card, params, log, choice, context):
        status = str(params.get('status', '')).strip()
        amount = self._eval_int(player_id, params.get('amount', 1), card, 1)
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            ps = self.players[tid]
            if status in ('poison', '中毒'):
                ps.poison += amount
            elif status in ('burn', 'fire', '灼烧'):
                ps.fire += amount
            elif status in ('vulnus', 'vulnerable', '易伤'):
                ps.vulnerable += amount
            elif status in ('toxic', '淬毒'):
                ps.toxic += amount
            elif status in ('dodge', '闪避'):
                ps.dodge += amount
            elif status in ('equip_protection', 'equipment_protection', '装备摧毁保护', '装备保护'):
                ps.equipment_protection += amount
            elif status in ('邪眼', 'Nazar'):
                ps.nazar_active = True
                ps.nazar_big_hits = max(0, ps.nazar_big_hits + amount)
            elif status:
                ps.custom_statuses = getattr(ps, 'custom_statuses', {})
                ps.custom_statuses[status] = int(ps.custom_statuses.get(status, 0) or 0) + amount
            self._normalize_status_value(ps, status)

    def _atomic_status_remove_named(self, player_id, card, params, log, choice, context):
        status = str(params.get('status', '')).strip()
        for tid in self._resolve_targets(player_id, params.get('target', 'self')):
            ps = self.players[tid]
            if status in ('poison', '中毒'):
                ps.poison = 0
            elif status in ('burn', 'fire', '灼烧'):
                ps.fire = 0
            elif status in ('vulnus', 'vulnerable', '易伤'):
                ps.vulnerable = 0
            elif status in ('toxic', '淬毒'):
                ps.toxic = 0
            elif status in ('dodge', '闪避'):
                ps.dodge = 0
            elif status in ('equip_protection', 'equipment_protection', '装备摧毁保护', '装备保护'):
                ps.equipment_protection = 0
            elif status in ('邪眼', 'Nazar'):
                ps.nazar_active = False
                ps.nazar_big_hits = 0
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
            store[name] = self._eval_var_assignment_value(player_id, params.get('value', 0), card)
            if isinstance(target_ref, int):
                self._sync_custom_var_alias(self.players[target_ref], name)

    def _atomic_var_add(self, player_id, card, params, log, choice, context):
        for target_ref in self._var_target_refs(player_id, params.get('target', 'self')):
            store = self._var_store_for_target(player_id, target_ref)
            name = str(params.get('name', 'var'))
            store[name] = int(self._scalar_value(store.get(name, 0), 0)) + self._eval_int(player_id, params.get('value', 0), card)
            if isinstance(target_ref, int):
                self._sync_custom_var_alias(self.players[target_ref], name)

    def _atomic_var_sub(self, player_id, card, params, log, choice, context):
        for target_ref in self._var_target_refs(player_id, params.get('target', 'self')):
            store = self._var_store_for_target(player_id, target_ref)
            name = str(params.get('name', 'var'))
            store[name] = int(self._scalar_value(store.get(name, 0), 0)) - self._eval_int(player_id, params.get('value', 0), card)
            if isinstance(target_ref, int):
                self._sync_custom_var_alias(self.players[target_ref], name)

    def _atomic_var_mul(self, player_id, card, params, log, choice, context):
        for target_ref in self._var_target_refs(player_id, params.get('target', 'self')):
            store = self._var_store_for_target(player_id, target_ref)
            name = str(params.get('name', 'var'))
            store[name] = int(self._scalar_value(store.get(name, 0), 0)) * self._eval_int(player_id, params.get('value', 1), card, 1)
            if isinstance(target_ref, int):
                self._sync_custom_var_alias(self.players[target_ref], name)

    def _atomic_var_div(self, player_id, card, params, log, choice, context):
        for target_ref in self._var_target_refs(player_id, params.get('target', 'self')):
            store = self._var_store_for_target(player_id, target_ref)
            name = str(params.get('name', 'var'))
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

    def use_trigger(self, player_id: int, equipment_instance_id: int) -> dict:
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
        trigger_cost = max(0, eq.card_def.trigger_cost_e)
        if trigger_cost > ps.elixir:
            return {'success': False, 'error': '能量不足'}
        max_uses = self._equipment_trigger_max_uses(eq)
        if max_uses > 0 and int(getattr(eq, 'uses_this_turn', 0)) >= max_uses:
            return {'success': False, 'error': f'该装备本回合最多触发{max_uses}次'}
        self._spend_resource(player_id, 'elixir', trigger_cost, eq.card_instance)
        eq.uses_this_turn = int(getattr(eq, 'uses_this_turn', 0)) + 1
        if has_mod_trigger and self._run_card_event(player_id, eq.card_instance, 'equipment_trigger', None,
                                                    {'source_id': player_id, 'target_id': 1 - player_id}):
            self._dispatch_card_event('equipment_triggered', player_id, eq.card_instance,
                                      target_id=1 - player_id, equipment=eq, equipment_owner_id=player_id)
            self._check_game_over()
            return {'success': True}
        opp_id = 1 - player_id
        if eq.def_id == 'Leaf':
            if self._destroy_equipment(player_id, eq):
                self.deal_attack_damage(opp_id, 8)
        elif eq.def_id == 'Mark':
            if self._destroy_equipment(player_id, eq):
                self.players[opp_id].skip_turn = True
        elif eq.def_id == 'Mine':
            if self._destroy_equipment(player_id, eq):
                self.deal_attack_damage(opp_id, 20)
        self._dispatch_card_event('equipment_triggered', player_id, eq.card_instance,
                                  target_id=opp_id, equipment=eq, equipment_owner_id=player_id)
        self._check_game_over()
        return {'success': True}


install_runtime_ext(GameEngine)
