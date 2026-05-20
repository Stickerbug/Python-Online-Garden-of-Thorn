import random
import math
from typing import List, Dict, Optional, Tuple, Set
from cards import (
    CardDef, CardInstance, CARD_DEFS, DRAFT_RATIO, DRAFT_REROLLS,
    HAND_LIMIT, DRAW_PER_TURN, ELIXIR_RECOVERY, BASE_MAX_HEALTH,
    BASE_MAX_ELIXIR, BASE_MAX_MAGIC, INITIAL_HEALTH, INITIAL_ELIXIR,
    INITIAL_MAGIC, FIRST_PLAYER_ELIXIR, SECOND_PLAYER_HEALTH,
    DECK_SIZE, INITIAL_HAND_SIZE, FIRST_PLAYER_HAND_SIZE, build_draft_pool, generate_draft_options,
    create_deck_from_draft,
)


class EquipmentInstance:
    def __init__(self, card_instance: CardInstance, owner: int):
        self.card_instance = card_instance
        self.owner = owner
        self.turns_equipped: int = 0
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
            'turns_equipped': self.turns_equipped,
            'corruption_active': self.corruption_active,
        }

    @staticmethod
    def from_dict(d: dict) -> 'EquipmentInstance':
        ei = EquipmentInstance(
            CardInstance.from_dict(d['card_instance']),
            d['owner']
        )
        ei.turns_equipped = d.get('turns_equipped', 0)
        ei.corruption_active = d.get('corruption_active', False)
        return ei


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
        self.cards_played_this_turn: Dict[str, int] = {}
        self.negate_next_skill: bool = False
        self.is_first_player: bool = False

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
            'negate_next_skill': self.negate_next_skill,
            'is_first_player': self.is_first_player,
            'coffee_first_use': self.coffee_first_use,
            'equipment': [e.to_dict() for e in self.equipment],
            'deck_count': len(self.deck),
            'discard_count': len(self.discard),
            'exile_count': len(self.exile),
            'hand_count': len(self.hand),
        }
        if include_private:
            d['hand'] = [c.to_dict() for c in self.hand]
            d['deck'] = [c.to_dict() for c in self.deck]
            d['discard'] = [c.to_dict() for c in self.discard]
            d['exile'] = [c.to_dict() for c in self.exile]
            d['cards_played_this_turn'] = dict(self.cards_played_this_turn)
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
            if len(self.hand) >= HAND_LIMIT:
                attract_cards = [c for c in self.hand if 'attract' in c.flags]
                non_attract_cards = [c for c in self.hand if 'attract' not in c.flags]
                if 'attract' in card.flags and non_attract_cards:
                    discard_card = non_attract_cards[0]
                    self.hand.remove(discard_card)
                    self.discard.append(discard_card)
                    self.hand.append(card)
                    drawn.append(card)
                else:
                    self.discard.append(card)
            else:
                self.hand.append(card)
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
                if len(self.hand) < HAND_LIMIT:
                    self.hand.append(extra)
                    drawn.append(extra)
                    if 'sprout' in extra.flags:
                        sprout_queue.append(extra)
                else:
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
        4: {'id': 4, 'name': '烈焰预兆', 'desc': '开局对敌方施加3层灼烧', 'position': 3},
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

    def pn(self, pid: int) -> str:
        return self.player_names[pid] if 0 <= pid < len(self.player_names) else f'玩家{pid+1}'

    def log_msg(self, msg: str):
        self.log.append(msg)

    def get_public_state(self, for_player: int) -> dict:
        opponent = 1 - for_player
        opp_data = self.players[opponent].to_dict(include_private=False)
        if self.pending_choice and self.pending_choice.get('player_id') == for_player:
            ct = self.pending_choice.get('choice_type', '')
            if ct in ('choose_from_enemy_hand',):
                opp_data['hand'] = [c.to_dict() for c in self.players[opponent].hand]
        if self._antenna_reveal[for_player]:
            opp_data['revealed_hand'] = [c.to_dict() for c in self.players[opponent].hand]
        return {
            'phase': self.phase,
            'current_player': self.current_player,
            'round_num': self.round_num,
            'game_over': self.game_over,
            'winner': self.winner,
            'you': self.players[for_player].to_dict(include_private=True),
            'opponent': opp_data,
            'log': self.log[-50:],
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
        for i in range(2):
            slot1 = pos1[0] if pos1 else None
            slot2 = random.choice(pos2) if pos2 else None
            slot3 = random.choice(pos3) if pos3 else None
            self.opening_event_options[i] = [slot1, slot2, slot3]
            for j in range(3):
                self.opening_event_magic_options[i][j] = random.sample(
                    self.MAGIC_CARD_POOL, min(3, len(self.MAGIC_CARD_POOL)))

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

    def _apply_opening_event(self, player_id: int):
        ps = self.players[player_id]
        opp = self.players[1 - player_id]
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
                    if magic_def and source_def:
                        for j in range(len(ps.deck)):
                            if ps.deck[j].def_id == source_def:
                                ps.deck[j] = CardInstance(def_id=magic_def)
                                converted += 1
                                magic_name = CARD_DEFS.get(magic_def, CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn
                                source_name = CARD_DEFS.get(source_def, CardDef('', '', '', 0, 0, '', 0, '', '', '')).name_cn
                                self.log_msg(f"{self.pn(player_id)}【魔力转化】：{source_name}变为{magic_name}")
                                break
        elif event_id == 3:
            if sub and 'convert_def_ids' in sub:
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
            else:
                converted = 0
                for j in range(len(ps.deck) - 1, -1, -1):
                    if ps.deck[j].def_id != 'Light' and converted < 5:
                        light_card = CardInstance(def_id='Light')
                        light_card.instance_flags = {'sprout', 'symbiosis'}
                        ps.deck[j] = light_card
                        converted += 1
                self.log_msg(f"{self.pn(player_id)}【光之洗礼】：{converted}张牌变为Light(萌芽+共生)")
        elif event_id == 4:
            opp.fire += 2
            self.log_msg(f"{self.pn(player_id)}【烈焰预兆】：敌方+2灼烧")
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
        if ps.bandage_death_pending:
            ps.health = 0
            ps.bandage_death_pending = False
            ps.invincible = False
            self.log_msg(f"{self.pn(player_id)}的绷带效果结束，死亡！")
            self._check_game_over()
            return
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
            draw_needed = HAND_LIMIT - len(ps.hand)
            if draw_needed > 0:
                ps.draw_cards(draw_needed)
                self.log_msg(f"{self.pn(player_id)}【命运抽签】：抽{draw_needed}张至手牌满")
        if self.opening_event_picks[player_id] == 6 and self.round_num <= 3:
            ps.gain_elixir(1)
            self.log_msg(f"{self.pn(player_id)}【能量涌动】：额外+1E")
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

    def _deal_direct_damage(self, player_id: int, amount: int, source: str = ''):
        ps = self.players[player_id]
        if ps.invincible:
            self.log_msg(f"{self.pn(player_id)}无敌，免疫{source}伤害！")
            return
        actual = amount
        corruption_count = self._get_corruption_count()
        if corruption_count > 0:
            actual = actual * (2 ** corruption_count)
            self.log_msg(f"腐化效果：伤害x{2 ** corruption_count}")
        ps.health -= actual
        self.log_msg(f"{self.pn(player_id)}受到{actual}点{source}伤害（H={ps.health}）")
        self._check_yggdrasil(player_id)
        self._check_game_over()

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
                            self._deal_direct_damage(opp_id, 3, '电池')
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
        if card_def.card_type == 'guard':
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
        if self.pending_response is not None:
            return {'success': False, 'error': '等待对手反制响应'}
        ps = self.players[player_id]
        card = ps.find_hand_card(card_instance_id)
        if card is None:
            return {'success': False, 'error': '卡牌不在手中'}
        can_play, reason = self.can_play_card(player_id, card)
        if not can_play:
            return {'success': False, 'error': reason}
        extra_e = self._get_extra_e_for_card(player_id, card)
        total_e = card.cost_e + extra_e
        ps.elixir -= total_e
        ps.magic -= card.cost_m
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
        if card.card_type == 'thorn':
            for c in opp.hand:
                if c.card_def.response_trigger == 'thorn':
                    return True
        if card.card_type == 'bloom':
            for c in opp.hand:
                if c.card_def.response_trigger == 'bloom':
                    return True
        if self._would_destroy_equipment(card):
            for c in opp.hand:
                if c.card_def.response_trigger == 'equipment_destroy':
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
            elif self._would_destroy_equipment(card) and counter_card.card_def.response_trigger == 'equipment_destroy':
                can_respond = True
            if not can_respond:
                return self._execute_card_effect(player_id, card, choice)
            responder.elixir -= counter_card.cost_e
            responder.magic -= counter_card.cost_m
            counter_removed = responder.remove_hand_card(card_instance_id)
            if counter_removed is None:
                return self._execute_card_effect(player_id, card, choice)
            self.log_msg(f"{self.pn(responder_id)}使用{counter_removed.name_cn}进行反制！")
            self._execute_counter_effect(responder_id, counter_removed, card)
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

    def _execute_counter_effect(self, responder_id: int, counter_card: CardInstance, original_card: CardInstance):
        ps = self.players[responder_id]
        opp = self.players[1 - responder_id]
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
            ps.discard.append(counter_card)

    def _reset_one_shot_attack_attrs(self, card: CardInstance):
        card.fission_level = 1
        card.fusion_level = 1
        card.fission_count = 0
        card.fusion_multiplier = 1.0
        card.fission_hit = 0

    def _discard_card(self, ps, card: CardInstance):
        if card.card_type == 'thorn':
            self._reset_one_shot_attack_attrs(card)
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
                self._apply_card_effect(player_id, card, choice if hit_idx == 0 else None)
            card.fission_hit = 0
        else:
            self._apply_card_effect(player_id, card, choice)
        if card.card_type == 'root':
            eq = EquipmentInstance(card, player_id)
            if eq.def_id == 'Disc':
                has_disc = any(e.def_id == 'Disc' for e in ps.equipment)
                if has_disc:
                    self.log_msg("圆盘不可叠加，旧圆盘被替换")
                    old_disc = [e for e in ps.equipment if e.def_id == 'Disc']
                    for od in old_disc:
                        ps.armor = max(0, ps.armor - 2)
                    ps.equipment = [e for e in ps.equipment if e.def_id != 'Disc']
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
            ps.hand.insert(0, card)
            dup_count = ps.cards_played_this_turn.get(card.def_id, 0)
            ps.elixir += card.cost_e + max(0, dup_count - 1)
            ps.magic += card.cost_m
            if dup_count > 0:
                ps.cards_played_this_turn[card.def_id] = dup_count - 1
            return {'success': False, 'error': '选择已取消'}
        dup_count = ps.cards_played_this_turn.get(card.def_id, 0)
        extra_e = dup_count
        total_e = card.cost_e + extra_e
        ps.elixir -= total_e
        ps.magic -= card.cost_m
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
        dealt = self.deal_attack_damage(target_id, amount, hits, is_precision=is_precision)
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
            if target and len(ps.hand) < HAND_LIMIT:
                opp.hand.remove(target)
                ps.hand.append(target)
                self.log_msg(log or f"{self.pn(player_id)}从敌方手中夺取{target.name_cn}")
            else:
                self.log_msg(log or f"{self.pn(player_id)}夺取失败")
        else:
            self.log_msg(log or f"{self.pn(player_id)}未选择要夺取的牌")

    def _atomic_choose_from_deck(self, player_id, card, params, log, choice, context):
        ps = self.players[player_id]
        if choice and 'target_instance_id' in choice:
            target = None
            for c in ps.deck:
                if c.instance_id == choice['target_instance_id']:
                    target = c
                    break
            if target and len(ps.hand) < HAND_LIMIT:
                ps.deck.remove(target)
                ps.hand.append(target)
                self.log_msg(log or f"{self.pn(player_id)}从牌堆取出{target.name_cn}")
            else:
                self.log_msg(log or f"{self.pn(player_id)}从牌堆取牌失败")
        else:
            self.log_msg(log or f"{self.pn(player_id)}未选择牌")

    def _atomic_choose_from_discard(self, player_id, card, params, log, choice, context):
        ps = self.players[player_id]
        if choice and 'target_def_id' in choice:
            target = None
            for c in ps.discard:
                if c.def_id == choice['target_def_id']:
                    target = c
                    break
            if target and len(ps.hand) < HAND_LIMIT:
                ps.discard.remove(target)
                ps.hand.append(target)
                self.log_msg(log or f"{self.pn(player_id)}从弃牌堆取出{target.name_cn}")
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
        amount = params.get('amount', 1)
        self.players[target_id].elixir = max(0, self.players[target_id].elixir - amount)
        self.log_msg(log or f"{self.pn(target_id)}消耗{amount}E")

    def _atomic_cost_m(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        amount = params.get('amount', 1)
        self.players[target_id].magic = max(0, self.players[target_id].magic - amount)
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
        if choice and 'target_def_id' in choice:
            target = None
            for c in ps.exile:
                if c.def_id == choice['target_def_id']:
                    target = c
                    break
            if target and len(ps.hand) < HAND_LIMIT:
                ps.exile.remove(target)
                ps.hand.append(target)
                self.log_msg(log or f"{self.pn(player_id)}从放逐区取出{target.name_cn}")
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
        if choice and 'target_instance_id' in choice:
            target = ps.find_hand_card(choice['target_instance_id'])
            if target and len(ps.hand) < HAND_LIMIT:
                copy = CardInstance(target.card_def, target.owner)
                ps.hand.append(copy)
                self.log_msg(log or f"{self.pn(player_id)}复制了{target.name_cn}")
        else:
            self.log_msg(log or f"{self.pn(player_id)}未选择要复制的牌")

    def _atomic_random_discard_from_hand(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        amount = params.get('amount', 1)
        ts = self.players[target_id]
        for _ in range(min(amount, len(ts.hand))):
            c = random.choice(ts.hand)
            ts.hand.remove(c)
            ts.discard.append(c)
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
        card_ref = params.get('card', '')
        ts = self.players[target_id]
        if card_ref and len(ts.hand) < HAND_LIMIT:
            card_def = CARD_DEFS.get(card_ref)
            if card_def:
                new_card = CardInstance(card_def, target_id)
                ts.hand.append(new_card)
                self.log_msg(log or f"{self.pn(target_id)}获得{card_def.name_cn}")
            else:
                self.log_msg(log or f"未知卡牌: {card_ref}")

    def _atomic_give_card_to_deck(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        card_ref = params.get('card', '')
        position = params.get('position', 'top')
        ts = self.players[target_id]
        if card_ref:
            card_def = CARD_DEFS.get(card_ref)
            if card_def:
                new_card = CardInstance(card_def, target_id)
                if position == 'bottom':
                    ts.deck.append(new_card)
                else:
                    ts.deck.insert(0, new_card)
                self.log_msg(log or f"{self.pn(target_id)}牌堆获得{card_def.name_cn}")

    def _atomic_give_card_to_discard(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        card_ref = params.get('card', '')
        ts = self.players[target_id]
        if card_ref:
            card_def = CARD_DEFS.get(card_ref)
            if card_def:
                new_card = CardInstance(card_def, target_id)
                ts.discard.append(new_card)
                self.log_msg(log or f"{self.pn(target_id)}弃牌堆获得{card_def.name_cn}")

    def _atomic_remove_specific_card(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'self'))
        zone = params.get('zone', 'hand')
        card_ref = params.get('card', '')
        ts = self.players[target_id]
        zone_map = {'hand': ts.hand, 'deck': ts.deck, 'discard': ts.discard, 'exile': ts.exile}
        target_zone = zone_map.get(zone, ts.hand)
        for c in target_zone[:]:
            if c.def_id == card_ref:
                target_zone.remove(c)
                self.log_msg(log or f"{self.pn(target_id)}的{c.name_cn}从{zone}中被消除")
                break

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
        times = params.get('times', 1)
        ps = self.players[player_id]
        targets = [c for c in ps.hand if c.card_def.card_type == card_type and c is not card]
        if targets:
            t = targets[0]
            t.fission_level = max(1, int(getattr(t, 'fission_level', 1))) + times
            t.fission_count = t.fission_level - 1
            self.log_msg(log or f"{self.pn(player_id)}的{t.name_cn}裂变+{times}")
        else:
            self.log_msg(log or f"{self.pn(player_id)}没有可裂变的{card_type}牌")

    def _atomic_multiply_next_damage(self, player_id, card, params, log, choice, context):
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
        count = params.get('count', 2)
        card_type = params.get('card_type', 'thorn')
        ps = self.players[player_id]
        same_type = [c for c in ps.hand if c.card_def.card_type == card_type and c is not card]
        if len(same_type) >= count:
            selected = same_type[:count]
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
        if tag and card:
            card.instance_flags = getattr(card, 'instance_flags', set())
            card.instance_flags.add(tag)
            self.log_msg(log or f"{card.name_cn}获得标签{tag}")

    def _atomic_remove_tag(self, player_id, card, params, log, choice, context):
        tag = params.get('tag', '')
        if tag and card and hasattr(card, 'instance_flags'):
            card.instance_flags.discard(tag)
            self.log_msg(log or f"{card.name_cn}移除标签{tag}")

    def _atomic_transform_card(self, player_id, card, params, log, choice, context):
        self.log_msg(log or f"{self.pn(player_id)}变换卡牌效果触发")

    def _atomic_gain_durability(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        if card:
            card.durability = getattr(card, 'durability', 0) + amount
            self.log_msg(log or f"{card.name_cn}耐久+{amount}")

    def _atomic_lose_durability(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 1)
        if card:
            card.durability = max(0, getattr(card, 'durability', 0) - amount)
            self.log_msg(log or f"{card.name_cn}耐久-{amount}")

    def _atomic_set_durability(self, player_id, card, params, log, choice, context):
        amount = params.get('amount', 3)
        if card:
            card.durability = amount
            self.log_msg(log or f"{card.name_cn}耐久设为{amount}")

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
        ps = self.players[player_id]
        if card in ps.hand:
            ps.hand.remove(card)
            ps.exile.append(card)
        elif card in ps.equipment:
            ps.equipment.remove(card)
            ps.exile.append(card)
        self.log_msg(log or f"{card.name_cn}被放逐")

    def _atomic_move_to_discard(self, player_id, card, params, log, choice, context):
        ps = self.players[player_id]
        if card in ps.hand:
            ps.hand.remove(card)
            ps.discard.append(card)
        elif card in ps.equipment:
            ps.equipment.remove(card)
            ps.discard.append(card)
        self.log_msg(log or f"{card.name_cn}移入弃牌堆")

    def _atomic_move_to_deck(self, player_id, card, params, log, choice, context):
        position = params.get('position', 'top')
        ps = self.players[player_id]
        if card in ps.hand:
            ps.hand.remove(card)
            if position == 'bottom':
                ps.deck.append(card)
            else:
                ps.deck.insert(0, card)
        self.log_msg(log or f"{card.name_cn}移入牌堆{position}")

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

    def _modified_attack_damage(self, base: int, card: CardInstance) -> int:
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
        ps = self.players[player_id]
        bonus = 1
        if ps.coffee_first_use:
            bonus = 2
            ps.coffee_first_use = False
        ps.gain_elixir(bonus)
        self.log_msg(f"{self.pn(player_id)}使用咖啡：+{bonus}E")

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
                    if len(ps.hand) < HAND_LIMIT:
                        ps.hand.append(found)
                    else:
                        ps.discard.append(found)
                    self.log_msg(f"{self.pn(player_id)}使用染色体！从弃牌堆找到{found.name_cn}")
                    return
        self.log_msg(f"{self.pn(player_id)}使用染色体，但未找到目标")

    def _effect_sewage(self, player_id: int, card: CardInstance, choice=None):
        opp = self.players[1 - player_id]
        if choice and 'target_instance_id' in choice:
            eq = opp.find_equipment(choice['target_instance_id'])
            if eq and 'indestructible' not in eq.card_def.flags:
                destroyed = self._destroy_equipment(1 - player_id, eq)
                if destroyed:
                    self.log_msg(f"{self.pn(player_id)}使用污水！摧毁了敌方的{eq.card_def.name_cn}")
                else:
                    self.log_msg(f"{self.pn(player_id)}使用污水，但装备保护抵消了摧毁")
            else:
                self.log_msg(f"{self.pn(player_id)}使用污水，但目标不可摧毁或不存在")
        else:
            destroyable = [e for e in opp.equipment if 'indestructible' not in e.card_def.flags]
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
            to_destroy = [e for e in p.equipment if 'indestructible' not in e.card_def.flags]
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
                if len(ps.hand) < HAND_LIMIT:
                    ps.hand.append(copy_card)
                    self.log_msg(f"{self.pn(player_id)}使用拟态！复制了{target.name_cn}（费用-1）")
                else:
                    self.log_msg(f"{self.pn(player_id)}使用拟态，但手牌已满")

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

    def _destroy_equipment(self, owner_id: int, eq: EquipmentInstance, check_protection: bool = True) -> bool:
        ps = self.players[owner_id]
        if check_protection and ps.equipment_protection > 0:
            ps.equipment_protection -= 1
            self.log_msg(f"{self.pn(owner_id)}的装备保护抵消了摧毁！")
            return False
        if eq.def_id == 'Disc':
            ps.armor = max(0, ps.armor - 2)
        if eq.def_id == 'Sponge' and ps.sponge_active:
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
        if eq.def_id == 'Pill':
            ps.enemy_draw_reduction = max(0, ps.enemy_draw_reduction - 1)
            ps.enemy_e_reduction = max(0, ps.enemy_e_reduction - 1)
            self.log_msg("药丸被摧毁！己方抽牌和回E恢复正常")
        ps.equipment.remove(eq)
        if 'exile' in eq.card_def.flags:
            ps.exile.append(eq.card_instance)
        else:
            ps.discard.append(eq.card_instance)
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
        if ps.bandage_active and ps.invincible:
            ps.invincible = False
            ps.bandage_active = False
            ps.bandage_death_pending = True
            self.log_msg(f"{self.pn(player_id)}的绷带无敌结束，将在下回合开始时死亡")
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
            if ps.invincible and not ps.bandage_active:
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
