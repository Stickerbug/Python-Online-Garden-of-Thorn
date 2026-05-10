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
            'triangle_stacks': self.triangle_stacks,
            'dodge': self.dodge,
            'nazar_active': self.nazar_active,
            'nazar_big_hits': self.nazar_big_hits,
            'equipment_protection': self.equipment_protection,
            'invincible': self.invincible,
            'skip_turn': self.skip_turn,
            'damage_multiplier': self.damage_multiplier,
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
        ps.triangle_stacks = d.get('triangle_stacks', 0)
        ps.dodge = d.get('dodge', 0)
        ps.nazar_active = d.get('nazar_active', False)
        ps.nazar_big_hits = d.get('nazar_big_hits', 0)
        ps.equipment_protection = d.get('equipment_protection', 0)
        ps.invincible = d.get('invincible', False)
        ps.skip_turn = d.get('skip_turn', False)
        ps.damage_multiplier = d.get('damage_multiplier', 1.0)
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
        return drawn

    def heal(self, amount: int):
        self.health = min(self.health + amount, self.base_max_health)

    def gain_elixir(self, amount: int):
        self.elixir = min(self.elixir + amount, self.max_elixir)

    def gain_magic(self, amount: int):
        self.magic = min(self.magic + amount, self.max_magic)


class GameEngine:
    def __init__(self):
        self.players = [PlayerState(0), PlayerState(1)]
        self.current_player: int = 0
        self.first_player: int = 0
        self.round_num: int = 0
        self.phase: str = 'waiting'
        self.log: List[str] = []
        self.draft_pool: List[CardInstance] = []
        self.draft_options: List[List[CardInstance]] = [[], []]
        self.draft_picks: List[List[str]] = [[], []]
        self.draft_rerolls: List[int] = [DRAFT_REROLLS, DRAFT_REROLLS]
        self.draft_round: int = 0
        self.draft_type_order: List[str] = []
        self.pending_response: Optional[dict] = None
        self.pending_choice: Optional[dict] = None
        self.game_over: bool = False
        self.winner: int = -1
        self.negated_card: bool = False
        self._yggdrasil_check: bool = True

    def log_msg(self, msg: str):
        self.log.append(msg)

    def get_public_state(self, for_player: int) -> dict:
        opponent = 1 - for_player
        return {
            'phase': self.phase,
            'current_player': self.current_player,
            'round_num': self.round_num,
            'game_over': self.game_over,
            'winner': self.winner,
            'you': self.players[for_player].to_dict(include_private=True),
            'opponent': self.players[opponent].to_dict(include_private=False),
            'log': self.log[-50:],
            'pending_response': self.pending_response,
            'pending_choice': self.pending_choice,
        }

    def start_draft(self):
        self.phase = 'draft'
        self.draft_pool = build_draft_pool()
        self.draft_picks = [[], []]
        self.draft_rerolls = [DRAFT_REROLLS, DRAFT_REROLLS]
        self.draft_round = 0
        self.draft_type_order = []
        for card_type, count in DRAFT_RATIO.items():
            self.draft_type_order.extend([card_type] * count)
        random.shuffle(self.draft_type_order)
        self._generate_draft_options()

    def _generate_draft_options(self):
        if self.draft_round >= DECK_SIZE:
            self.phase = 'draft_complete'
            return
        card_type = self.draft_type_order[self.draft_round]
        self.draft_options[0] = generate_draft_options(self.draft_pool, card_type, 3)
        self.draft_options[1] = generate_draft_options(self.draft_pool, card_type, 3)

    def draft_pick(self, player_id: int, def_id: str) -> bool:
        if len(self.draft_picks[player_id]) > self.draft_round:
            return False
        options = self.draft_options[player_id]
        found = None
        for opt in options:
            if opt.def_id == def_id:
                found = opt
                break
        if found is None:
            return False
        self.draft_picks[player_id].append(def_id)
        self.draft_options[player_id] = [o for o in self.draft_options[player_id] if o.def_id != def_id]
        if len(self.draft_picks[0]) > self.draft_round and len(self.draft_picks[1]) > self.draft_round:
            self.draft_round += 1
            self._generate_draft_options()
        return True

    def draft_reroll(self, player_id: int) -> bool:
        if self.draft_rerolls[player_id] <= 0:
            return False
        self.draft_rerolls[player_id] -= 1
        card_type = self.draft_type_order[self.draft_round]
        options = generate_draft_options(self.draft_pool, card_type, 3)
        self.draft_options[player_id] = options
        return True

    def start_game(self):
        self.phase = 'playing'
        self.first_player = random.randint(0, 1)
        self.current_player = self.first_player
        for i in range(2):
            ps = self.players[i]
            ps.is_first_player = (i == self.first_player)
            ps.deck = create_deck_from_draft(self.draft_picks[i])
            ps.health = INITIAL_HEALTH
            ps.max_health = BASE_MAX_HEALTH
            ps.base_max_health = BASE_MAX_HEALTH
            ps.elixir = INITIAL_ELIXIR
            ps.magic = INITIAL_MAGIC
            if i == self.first_player:
                ps.elixir = FIRST_PLAYER_ELIXIR
                ps.draw_cards(FIRST_PLAYER_HAND_SIZE)
            else:
                ps.health = SECOND_PLAYER_HEALTH
                ps.max_health = SECOND_PLAYER_HEALTH
                ps.draw_cards(INITIAL_HAND_SIZE)
        self.round_num = 1
        self.log_msg(f"游戏开始！玩家{self.first_player + 1}先手。")
        self.log_msg(f"=== 第{self.round_num}回合 ===")
        self._start_player_turn(self.first_player)

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
        if ps.skip_turn:
            ps.skip_turn = False
            self.log_msg(f"玩家{player_id + 1}被眩晕，跳过本回合！")
            self._end_player_turn(player_id)
            return
        self._apply_turn_start_effects(player_id)
        if self.game_over:
            return
        if ps.health <= 0:
            self._check_game_over()
            return
        self.phase = 'action'

    def _apply_turn_start_effects(self, player_id: int):
        ps = self.players[player_id]
        opp = self.players[1 - player_id]
        if ps.poison > 0:
            dmg = ps.poison
            self._deal_direct_damage(player_id, dmg, '中毒')
            if self.game_over or ps.health <= 0:
                return
            ps.poison = ps.poison // 2
            if ps.poison > 0:
                self.log_msg(f"玩家{player_id + 1}中毒减半为{ps.poison}层")
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
                    self.log_msg(f"玩家{player_id + 1}受螫针影响，能量回复-1")
            ps.gain_elixir(elixir_recovery)
            self.log_msg(f"玩家{player_id + 1}回复{elixir_recovery}E")
        for eq in ps.equipment:
            eq.turns_equipped += 1
            if eq.def_id == 'Leaf':
                ps.heal(2)
                self.log_msg(f"玩家{player_id + 1}的叶子效果：+2H")
            elif eq.def_id == 'Yucca':
                ps.heal(5)
                self.log_msg(f"玩家{player_id + 1}的丝兰效果：+5H")
            elif eq.def_id == 'MagicLeaf':
                ps.gain_magic(1)
                self.log_msg(f"玩家{player_id + 1}的魔法叶效果：+1M")
            elif eq.def_id == 'MagicYucca':
                ps.gain_magic(2)
                self.log_msg(f"玩家{player_id + 1}的魔法丝兰效果：+2M")
            elif eq.def_id == 'Powder':
                ps.gain_elixir(2)
                self.log_msg(f"玩家{player_id + 1}的粉末效果：+2E")
            elif eq.def_id == 'GoldenLeaf':
                ps.draw_cards(1)
                self.log_msg(f"玩家{player_id + 1}的黄金叶效果：多抽1张牌")
        for eq in ps.equipment:
            if eq.def_id == 'Cancer':
                opp.vulnerable += 2
                self.log_msg(f"玩家{player_id + 1}的癌细胞效果：敌方+2易伤")
        for eq in opp.equipment:
            if eq.def_id == 'Corruption' and not eq.corruption_active:
                eq.corruption_active = True
                self.log_msg(f"玩家{1 - player_id + 1}的腐化效果激活！全场伤害翻倍！")

    def _deal_direct_damage(self, player_id: int, amount: int, source: str = ''):
        ps = self.players[player_id]
        if ps.invincible:
            self.log_msg(f"玩家{player_id + 1}无敌，免疫{source}伤害！")
            return
        actual = amount
        corruption_count = self._get_corruption_count()
        if corruption_count > 0:
            actual = actual * (2 ** corruption_count)
            self.log_msg(f"腐化效果：伤害×{2 ** corruption_count}")
        if ps.vulnerable > 0:
            actual += ps.vulnerable
        ps.health -= actual
        self.log_msg(f"玩家{player_id + 1}受到{actual}点{source}伤害（H={ps.health}）")
        self._check_yggdrasil(player_id)
        self._check_game_over()

    def deal_attack_damage(self, target_id: int, amount: int, hits: int = 1, is_battery: bool = False) -> int:
        ps = self.players[target_id]
        opp_id = 1 - target_id
        opp = self.players[opp_id]
        total_dealt = 0
        for h in range(hits):
            if ps.dodge > 0:
                ps.dodge -= 1
                self.log_msg(f"玩家{target_id + 1}闪避了攻击！")
                continue
            if ps.invincible:
                self.log_msg(f"玩家{target_id + 1}无敌，免疫伤害！")
                continue
            if amount <= 0 and hits <= 1:
                break
            dmg = amount
            if ps.nazar_active:
                original_dmg = dmg
                dmg = max(1, dmg - 9)
                self.log_msg(f"邪眼护符效果：伤害{original_dmg}→{dmg}")
                if original_dmg >= 10:
                    ps.nazar_big_hits += 1
                    if ps.nazar_big_hits >= 2:
                        ps.nazar_active = False
                        ps.nazar_big_hits = 0
                        self.log_msg(f"玩家{target_id + 1}的邪眼护符被击碎！")
            corruption_count = self._get_corruption_count()
            if corruption_count > 0:
                dmg = dmg * (2 ** corruption_count)
                self.log_msg(f"腐化效果：伤害×{2 ** corruption_count}")
            dmg = max(0, dmg - ps.armor)
            if ps.vulnerable > 0:
                dmg += ps.vulnerable
                self.log_msg(f"易伤效果：伤害+{ps.vulnerable}")
            ps.health -= dmg
            total_dealt += dmg
            self.log_msg(f"玩家{target_id + 1}受到{dmg}点伤害（H={ps.health}）")
            if not is_battery:
                for eq in ps.equipment:
                    if eq.def_id == 'Battery':
                        self.log_msg(f"玩家{target_id + 1}的电池效果：对敌方造成3D")
                        self._deal_direct_damage(opp_id, 3, '电池')
                    if eq.def_id == 'MagicBattery':
                        if ps.magic_battery_m_this_turn < 3:
                            ps.gain_magic(1)
                            ps.magic_battery_m_this_turn += 1
                            self.log_msg(f"玩家{target_id + 1}的魔法电池效果：+1M")
            self._check_yggdrasil(target_id)
            if ps.health <= 0:
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
            for card in ps.hand[:]:
                if card.def_id == 'Yggdrasil':
                    ps.health = 1
                    ps.invincible = True
                    ps.poison = 0
                    ps.fire = 0
                    ps.vulnerable = 0
                    ps.dodge = 0
                    ps.nazar_active = False
                    ps.nazar_big_hits = 0
                    ps.equipment_protection = 0
                    ps.negate_next_skill = False
                    ps.skip_turn = False
                    ps.hand.remove(card)
                    ps.exile.append(card)
                    self.log_msg(f"玩家{player_id + 1}的世界树之叶发动！死而复生，本回合无敌！")
                    self._check_game_over()
                    return

    def _check_game_over(self):
        for i in range(2):
            if self.players[i].health <= 0:
                self.game_over = True
                self.winner = 1 - i
                self.phase = 'game_over'
                self.log_msg(f"玩家{i + 1}生命值归零！玩家{self.winner + 1}获胜！")
                return

    def can_play_card(self, player_id: int, card: CardInstance) -> Tuple[bool, str]:
        ps = self.players[player_id]
        card_def = card.card_def
        if card_def.card_type == 'counter':
            return False, "反制卡只能通过响应机制使用"
        if self.phase != 'action' or self.current_player != player_id:
            return False, "不是你的回合"
        dup_count = ps.cards_played_this_turn.get(card.def_id, 0)
        extra_e = dup_count
        total_e = card.cost_e + extra_e
        if total_e > ps.elixir:
            return False, f"能量不足（需要{total_e}E，当前{ps.elixir}E）"
        if card.cost_m > ps.magic:
            return False, f"魔力不足（需要{card.cost_m}M，当前{ps.magic}M）"
        return True, ""

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
        dup_count = ps.cards_played_this_turn.get(card.def_id, 0)
        extra_e = dup_count
        total_e = card.cost_e + extra_e
        ps.elixir -= total_e
        ps.magic -= card.cost_m
        ps.cards_played_this_turn[card.def_id] = dup_count + 1
        card_removed = ps.remove_hand_card(card_instance_id)
        if card_removed is None:
            return {'success': False, 'error': '移除手牌失败'}
        needs_response = self._check_response_needed(player_id, card)
        if needs_response:
            self.pending_response = {
                'card': card.to_dict(),
                'player_id': player_id,
                'original_choice': choice,
            }
            return {'success': True, 'needs_response': True, 'card': card.to_dict()}
        return self._execute_card_effect(player_id, card, choice)

    def _check_response_needed(self, player_id: int, card: CardInstance) -> bool:
        if 'precision' in card.flags:
            return False
        opp = self.players[1 - player_id]
        if card.card_type == 'attack':
            for c in opp.hand:
                if c.card_def.response_trigger == 'attack':
                    return True
        if card.card_type == 'skill':
            for c in opp.hand:
                if c.card_def.response_trigger == 'skill':
                    return True
        if self._would_destroy_equipment(card):
            for c in opp.hand:
                if c.card_def.response_trigger == 'equipment_destroy':
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
            if played_card_def.card_type == 'attack' and counter_card.card_def.response_trigger == 'attack':
                can_respond = True
            elif played_card_def.card_type == 'skill' and counter_card.card_def.response_trigger == 'skill':
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
            self.log_msg(f"玩家{responder_id + 1}使用{counter_removed.name_cn}进行反制！")
            self._execute_counter_effect(responder_id, counter_removed, card)
            if counter_removed.def_id == 'Bubble':
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
            self.log_msg(f"玩家{responder_id + 1}获得1层闪避")
        elif counter_card.def_id == 'Nazar':
            ps.nazar_active = True
            ps.nazar_big_hits = 0
            self.log_msg(f"玩家{responder_id + 1}获得邪眼护符效果")
        elif counter_card.def_id == 'MagicNazar':
            ps.equipment_protection += 1
            self.log_msg(f"玩家{responder_id + 1}获得1层装备保护")
        elif counter_card.def_id == 'MagicBubble':
            ps.negate_next_skill = True
            self.log_msg(f"玩家{responder_id + 1}的魔法泡泡：敌方下次技能牌失效")
        if 'exile' in counter_card.flags:
            ps.exile.append(counter_card)
        else:
            ps.discard.append(counter_card)

    def _execute_card_effect(self, player_id: int, card: CardInstance, choice: Optional[dict] = None) -> dict:
        ps = self.players[player_id]
        opp = self.players[1 - player_id]
        result = {'success': True, 'card': card.to_dict()}
        if self.negated_card and card.card_type == 'skill':
            self.negated_card = False
            self.log_msg(f"玩家{player_id + 1}的{card.name_cn}被魔法泡泡反制，失效！")
            if 'exile' in card.flags:
                ps.exile.append(card)
            else:
                ps.discard.append(card)
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
        self._apply_card_effect(player_id, card, choice)
        if card.card_type == 'equipment':
            eq = EquipmentInstance(card, player_id)
            if eq.def_id == 'Disc':
                has_disc = any(e.def_id == 'Disc' for e in ps.equipment)
                if has_disc:
                    self.log_msg(f"圆盘不可叠加，旧圆盘被替换")
                    old_disc = [e for e in ps.equipment if e.def_id == 'Disc']
                    for od in old_disc:
                        ps.armor = max(0, ps.armor - 2)
                    ps.equipment = [e for e in ps.equipment if e.def_id != 'Disc']
                ps.armor += 2
                self.log_msg(f"玩家{player_id + 1}获得2点护甲")
            ps.equipment.append(eq)
            self.log_msg(f"玩家{player_id + 1}装备了{card.name_cn}")
        elif 'exile' in card.flags:
            ps.exile.append(card)
            self.log_msg(f"玩家{player_id + 1}的{card.name_cn}被放逐")
        else:
            ps.discard.append(card)
        self._check_game_over()
        return result

    def _card_needs_choice(self, card: CardInstance) -> bool:
        return card.def_id in ('Fission', 'Fusion', 'Mimic', 'Chromosome', 'Sewage', 'Chilli')

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
        else:
            self.log_msg(f"玩家{player_id + 1}使用了{card.name_cn}")

    def _effect_basic(self, player_id: int, card: CardInstance, choice=None):
        dmg = 6
        if card.fission_count > 0:
            dmg = math.ceil(dmg / 3)
        dmg = int(dmg * card.fusion_multiplier)
        self.log_msg(f"玩家{player_id + 1}使用基本攻击！造成{dmg}伤害")
        self.deal_attack_damage(1 - player_id, dmg)

    def _effect_bone(self, player_id: int, card: CardInstance, choice=None):
        dmg = 12
        if card.fission_count > 0:
            dmg = math.ceil(dmg / 3)
        dmg = int(dmg * card.fusion_multiplier)
        self.log_msg(f"玩家{player_id + 1}使用骨头！造成{dmg}伤害")
        self.deal_attack_damage(1 - player_id, dmg)

    def _effect_stinger(self, player_id: int, card: CardInstance, choice=None):
        dmg = 20
        if card.fission_count > 0:
            dmg = math.ceil(dmg / 3)
        dmg = int(dmg * card.fusion_multiplier)
        self.log_msg(f"玩家{player_id + 1}使用刺！造成{dmg}伤害")
        self.deal_attack_damage(1 - player_id, dmg)

    def _effect_sand(self, player_id: int, card: CardInstance, choice=None):
        dmg = 3
        hits = 4
        if card.fission_count > 0:
            dmg = math.ceil(dmg / 3)
        dmg = int(dmg * card.fusion_multiplier)
        self.log_msg(f"玩家{player_id + 1}使用沙子！造成{dmg}×{hits}伤害")
        self.deal_attack_damage(1 - player_id, dmg, hits)

    def _effect_wing(self, player_id: int, card: CardInstance, choice=None):
        dmg = 8
        hits = 2
        if card.fission_count > 0:
            dmg = math.ceil(dmg / 3)
        dmg = int(dmg * card.fusion_multiplier)
        self.log_msg(f"玩家{player_id + 1}使用翅膀！造成{dmg}×{hits}伤害")
        self.deal_attack_damage(1 - player_id, dmg, hits)

    def _effect_light(self, player_id: int, card: CardInstance, choice=None):
        dmg = 2
        hits = 2
        if card.fission_count > 0:
            dmg = math.ceil(dmg / 3)
        dmg = int(dmg * card.fusion_multiplier)
        self.log_msg(f"玩家{player_id + 1}使用轻！造成{dmg}×{hits}伤害")
        self.deal_attack_damage(1 - player_id, dmg, hits)

    def _effect_fang(self, player_id: int, card: CardInstance, choice=None):
        dmg = 8
        if card.fission_count > 0:
            dmg = math.ceil(dmg / 3)
        dmg = int(dmg * card.fusion_multiplier)
        self.deal_attack_damage(1 - player_id, dmg)
        self.players[player_id].heal(4)
        self.log_msg(f"玩家{player_id + 1}使用尖牙！造成{dmg}伤害，回复4H")

    def _effect_triangle(self, player_id: int, card: CardInstance, choice=None):
        ps = self.players[player_id]
        if ps.triangle_stacks < 4:
            ps.triangle_stacks += 1
        dmg = 6 + 3 * ps.triangle_stacks
        if card.fission_count > 0:
            dmg = math.ceil(dmg / 3)
        dmg = int(dmg * card.fusion_multiplier)
        self.log_msg(f"玩家{player_id + 1}使用三角形！造成{dmg}伤害，三角形层数+1（{ps.triangle_stacks}）")
        self.deal_attack_damage(1 - player_id, dmg)

    def _effect_magicbone(self, player_id: int, card: CardInstance, choice=None):
        dmg = 15
        if card.fission_count > 0:
            dmg = math.ceil(dmg / 3)
        dmg = int(dmg * card.fusion_multiplier)
        self.deal_attack_damage(1 - player_id, dmg)
        self.log_msg(f"玩家{player_id + 1}使用魔法骨头！造成{dmg}伤害")

    def _effect_magicstinger(self, player_id: int, card: CardInstance, choice=None):
        dmg = 30
        if card.fission_count > 0:
            dmg = math.ceil(dmg / 3)
        dmg = int(dmg * card.fusion_multiplier)
        self.deal_attack_damage(1 - player_id, dmg)
        self.log_msg(f"玩家{player_id + 1}使用魔法刺！造成{dmg}伤害")

    def _effect_fission(self, player_id: int, card: CardInstance, choice=None):
        ps = self.players[player_id]
        if choice and 'target_instance_id' in choice:
            target = ps.find_hand_card(choice['target_instance_id'])
            if target and target.card_type == 'attack':
                target.fission_count = 2
                self.log_msg(f"玩家{player_id + 1}使用裂变！{target.name_cn}将额外打出2次，伤害变为1/3")
                for _ in range(1 + target.fission_count):
                    self._apply_card_effect(player_id, target)
                    if self.game_over:
                        break
                ps.remove_hand_card(target.instance_id)
                ps.discard.append(target)
        else:
            self.log_msg(f"玩家{player_id + 1}使用裂变，但未选择目标")

    def _effect_fusion(self, player_id: int, card: CardInstance, choice=None):
        ps = self.players[player_id]
        if choice and 'target_instance_ids' in choice:
            ids = choice['target_instance_ids']
            if len(ids) < 2:
                self.log_msg(f"玩家{player_id + 1}使用聚变，但选择不足2张")
                return
            cards = [ps.find_hand_card(i) for i in ids]
            cards = [c for c in cards if c is not None]
            if len(cards) < 2:
                return
            first = cards[0]
            multiplier = len(cards)
            first.fusion_multiplier = multiplier
            for c in cards[1:]:
                ps.hand.remove(c)
                ps.discard.append(c)
            self.log_msg(f"玩家{player_id + 1}使用聚变！{first.name_cn}伤害×{multiplier}，丢弃{len(cards) - 1}张")

    def _effect_iris(self, player_id: int, card: CardInstance, choice=None):
        self.players[1 - player_id].poison += 10
        self.log_msg(f"玩家{player_id + 1}使用鸢尾！敌方+10中毒")

    def _effect_fire(self, player_id: int, card: CardInstance, choice=None):
        self.players[1 - player_id].fire += 2
        self.log_msg(f"玩家{player_id + 1}使用火！敌方+2灼烧")

    def _effect_fries(self, player_id: int, card: CardInstance, choice=None):
        self.players[player_id].heal(12)
        self.log_msg(f"玩家{player_id + 1}使用薯条！+12H")

    def _effect_rose(self, player_id: int, card: CardInstance, choice=None):
        self.players[player_id].heal(7)
        self.log_msg(f"玩家{player_id + 1}使用玫瑰！+7H")

    def _effect_manaorb(self, player_id: int, card: CardInstance, choice=None):
        self.players[player_id].gain_magic(3)
        self.log_msg(f"玩家{player_id + 1}使用魔法球！+3M")

    def _effect_coffee(self, player_id: int, card: CardInstance, choice=None):
        ps = self.players[player_id]
        bonus = 1
        if ps.coffee_first_use:
            bonus = 2
            ps.coffee_first_use = False
        ps.gain_elixir(bonus)
        self.log_msg(f"玩家{player_id + 1}使用咖啡！+{bonus}E")

    def _effect_chilli(self, player_id: int, card: CardInstance, choice=None):
        ps = self.players[player_id]
        if choice and 'target_instance_id' in choice:
            target = ps.find_hand_card(choice['target_instance_id'])
            if target:
                ps.remove_hand_card(target.instance_id)
                ps.discard.append(target)
                ps.draw_cards(1)
                self.log_msg(f"玩家{player_id + 1}使用辣椒！丢弃{target.name_cn}，抽1张牌")
        else:
            ps.draw_cards(1)
            self.log_msg(f"玩家{player_id + 1}使用辣椒！抽1张牌")

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
                    self.log_msg(f"玩家{player_id + 1}使用染色体！从弃牌堆找到{found.name_cn}")
                    return
        self.log_msg(f"玩家{player_id + 1}使用染色体，但未找到目标")

    def _effect_sewage(self, player_id: int, card: CardInstance, choice=None):
        opp = self.players[1 - player_id]
        if choice and 'target_instance_id' in choice:
            eq = opp.find_equipment(choice['target_instance_id'])
            if eq and 'indestructible' not in eq.card_def.flags:
                destroyed = self._destroy_equipment(1 - player_id, eq)
                if destroyed:
                    self.log_msg(f"玩家{player_id + 1}使用污水！摧毁了敌方的{eq.card_def.name_cn}")
                else:
                    self.log_msg(f"玩家{player_id + 1}使用污水，但装备保护抵消了摧毁")
            else:
                self.log_msg(f"玩家{player_id + 1}使用污水，但目标不可摧毁或不存在")
        else:
            destroyable = [e for e in opp.equipment if 'indestructible' not in e.card_def.flags]
            if destroyable:
                eq = destroyable[0]
                destroyed = self._destroy_equipment(1 - player_id, eq)
                if destroyed:
                    self.log_msg(f"玩家{player_id + 1}使用污水！摧毁了敌方的{eq.card_def.name_cn}")
                else:
                    self.log_msg(f"玩家{player_id + 1}使用污水，但装备保护抵消了摧毁")

    def _effect_magicsewage(self, player_id: int, card: CardInstance, choice=None):
        for pid in range(2):
            p = self.players[pid]
            to_destroy = [e for e in p.equipment if 'indestructible' not in e.card_def.flags]
            for eq in to_destroy:
                destroyed = self._destroy_equipment(pid, eq)
                if destroyed:
                    self.log_msg(f"魔法污水摧毁了玩家{pid + 1}的{eq.card_def.name_cn}")
                else:
                    self.log_msg(f"魔法污水试图摧毁玩家{pid + 1}的{eq.card_def.name_cn}，但装备保护抵消了")

    def _effect_mimic(self, player_id: int, card: CardInstance, choice=None):
        ps = self.players[player_id]
        if choice and 'target_instance_id' in choice:
            target = ps.find_hand_card(choice['target_instance_id'])
            if target:
                copy_card = target.copy()
                copy_card.mimic_discount = 1
                if len(ps.hand) < HAND_LIMIT:
                    ps.hand.append(copy_card)
                    self.log_msg(f"玩家{player_id + 1}使用拟态！复制了{target.name_cn}（费用-1）")
                else:
                    self.log_msg(f"玩家{player_id + 1}使用拟态，但手牌已满")

    def _effect_yggdrasil(self, player_id: int, card: CardInstance, choice=None):
        ps = self.players[player_id]
        ps.heal(20)
        self.log_msg(f"玩家{player_id + 1}使用世界树之叶！+20H")

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
        pass

    def _effect_corruption(self, player_id: int, card: CardInstance, choice=None):
        self.log_msg(f"玩家{player_id + 1}装备了腐化！下回合起全场伤害翻倍")

    def _effect_mark(self, player_id: int, card: CardInstance, choice=None):
        pass

    def _effect_mine(self, player_id: int, card: CardInstance, choice=None):
        pass

    def _destroy_equipment(self, owner_id: int, eq: EquipmentInstance, check_protection: bool = True) -> bool:
        ps = self.players[owner_id]
        if check_protection and ps.equipment_protection > 0:
            ps.equipment_protection -= 1
            self.log_msg(f"玩家{owner_id + 1}的装备保护抵消了摧毁！")
            return False
        if eq.def_id == 'Disc':
            ps.armor = max(0, ps.armor - 2)
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
        if eq.def_id == 'Leaf':
            destroyed = self._destroy_equipment(player_id, eq)
            if destroyed:
                self.deal_attack_damage(opp_id, 8)
                self.log_msg(f"玩家{player_id + 1}触发叶子！造成8D")
        elif eq.def_id == 'Mark':
            destroyed = self._destroy_equipment(player_id, eq)
            if destroyed:
                self.log_msg(f"玩家{player_id + 1}触发标记！敌方回合立即结束")
                self.pending_response = None
                if self.current_player == opp_id:
                    self._end_player_turn(opp_id)
        elif eq.def_id == 'Mine':
            destroyed = self._destroy_equipment(player_id, eq)
            if destroyed:
                self.deal_attack_damage(opp_id, 20)
                self.log_msg(f"玩家{player_id + 1}触发地雷！造成20D")
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
        void_cards = [c for c in ps.hand if 'void' in c.flags]
        for c in void_cards:
            ps.hand.remove(c)
            ps.exile.append(c)
            self.log_msg(f"玩家{player_id + 1}的{c.name_cn}因虚无被放逐")
        ps.draw_cards(DRAW_PER_TURN)
        self.log_msg(f"玩家{player_id + 1}抽{DRAW_PER_TURN}张牌")
        if player_id == self.first_player:
            other = 1 - self.first_player
            self._start_player_turn(other)
        else:
            self._end_round()

    def _end_round(self):
        for pid in range(2):
            ps = self.players[pid]
            if ps.invincible:
                ps.invincible = False
                self.log_msg(f"玩家{pid + 1}的无敌效果结束")
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
        return [c for c in self.players[player_id].hand if c.card_type == 'attack']

    def get_enemy_equipment(self, player_id: int) -> List[EquipmentInstance]:
        return self.players[1 - player_id].equipment
