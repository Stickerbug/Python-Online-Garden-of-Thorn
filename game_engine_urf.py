import random
from typing import List, Optional

from game_engine import GameEngine, PlayerState
from cards import (
    CardInstance, CARD_DEFS, INITIAL_HEALTH, INITIAL_ELIXIR,
    INITIAL_MAGIC, FIRST_PLAYER_ELIXIR, SECOND_PLAYER_HEALTH,
    BASE_MAX_HEALTH, DRAW_PER_TURN, ELIXIR_RECOVERY,
)


URF_HAND_LIMIT = 10
URF_EQUIPMENT_LIMIT = 3
URF_STARTING_HAND_COUNTS = {
    'thorn': 4,
    'bloom': 3,
    'root': 2,
    'guard': 1,
}
CARD_TYPE_CN = {
    'thorn': '攻击',
    'bloom': '技能',
    'root': '装备',
    'guard': '反制',
}


INFINITE_EXCLUDED_IDS = {
    'Triangle',
    'MagicBone', 'MagicStinger', 'MagicSewage', 'MagicLeaf', 'MagicYucca',
    'MagicBattery', 'MagicNazar', 'MagicBubble',
    'ManaOrb', 'Chromosome', 'Chilli', 'GoldenLeaf', 'Compass',
}

INFINITE_EXCLUDED_EFFECTS = {
    'draw', 'choose_from_deck', 'reveal_deck_top', 'put_card_to_deck',
    'shuffle_discard_into_deck', 'give_card_to_deck', 'mod_draw',
    'equip_reduce_enemy_draw', 'equip_reduce_own_draw',
    'gain_m', 'mod_m_regen', 'trigger_on_self_magic_heal_cumulative',
}


def is_infinite_excluded(card_def) -> bool:
    if not card_def:
        return True
    if 'infinite_exclude' in getattr(card_def, 'flags', set()):
        return True
    if card_def.id in INFINITE_EXCLUDED_IDS:
        return True
    if card_def.cost_m > 0:
        return True
    if card_def.id.startswith('Magic') or card_def.name_en.startswith('Magic '):
        return True
    effects = list(getattr(card_def, 'effects', []) or [])
    effects.extend(getattr(card_def, 'trigger_effects', []) or [])
    for effect in effects:
        effect_type = effect.get('type') if isinstance(effect, dict) else effect
        if effect_type in INFINITE_EXCLUDED_EFFECTS:
            return True
    return False


class InfinitePlayerState(PlayerState):
    def __init__(self, player_id: int, engine):
        super().__init__(player_id)
        self._infinite_engine = engine

    def _draw_one_infinite(self, card_type: Optional[str] = None) -> Optional[CardInstance]:
        return self._infinite_engine.create_infinite_card(card_type)

    def draw_cards(self, count: int) -> List[CardInstance]:
        drawn = []
        sprout_queue = []
        for _ in range(count):
            card = self._draw_one_infinite()
            if card is None:
                break
            if self._infinite_engine.add_card_to_urf_hand(self.player_id, card, log=False):
                drawn.append(card)
                if 'sprout' in card.flags:
                    sprout_queue.append(card)
        while sprout_queue:
            trigger = sprout_queue.pop(0)
            if trigger not in self.hand:
                continue
            extra = self._draw_one_infinite()
            if extra is None:
                break
            if self._infinite_engine.add_card_to_urf_hand(self.player_id, extra, log=False):
                drawn.append(extra)
                if 'sprout' in extra.flags:
                    sprout_queue.append(extra)
        return drawn


class GameEngineInfiniteFire(GameEngine):
    mode = 'infinite_fire'

    def __init__(self):
        super().__init__()
        self.players = [InfinitePlayerState(0, self), InfinitePlayerState(1, self)]
        self.infinite_card_pool: List[str] = []
        self.infinite_card_weights: List[int] = []
        self.infinite_by_type = {}

    def _build_infinite_pool(self):
        ids = []
        weights = []
        for def_id, card_def in CARD_DEFS.items():
            if def_id == 'Yggdrasil':
                continue
            if self.allowed_card_ids is not None and def_id not in self.allowed_card_ids:
                continue
            if is_infinite_excluded(card_def):
                continue
            weight = max(1, int(getattr(card_def, 'count', 1) or 1))
            ids.append(def_id)
            weights.append(weight)
        self.infinite_card_pool = ids
        self.infinite_card_weights = weights
        by_type = {}
        for def_id in ids:
            card_def = CARD_DEFS[def_id]
            card_type = card_def.card_type
            by_type.setdefault(card_type, {'ids': [], 'weights': []})
            by_type[card_type]['ids'].append(def_id)
            by_type[card_type]['weights'].append(max(1, int(getattr(card_def, 'count', 1) or 1)))
        self.infinite_by_type = by_type

    def create_infinite_card(self, card_type: Optional[str] = None) -> Optional[CardInstance]:
        if not self.infinite_card_pool:
            self._build_infinite_pool()
        if card_type:
            pool = self.infinite_by_type.get(card_type) or {}
            ids = pool.get('ids') or []
            weights = pool.get('weights') or []
            if not ids:
                return None
            return CardInstance(def_id=random.choices(ids, weights=weights, k=1)[0])
        if not self.infinite_card_pool:
            return None
        def_id = random.choices(self.infinite_card_pool, weights=self.infinite_card_weights, k=1)[0]
        return CardInstance(def_id=def_id)

    def add_card_to_urf_hand(self, player_id: int, card: CardInstance, log: bool = True) -> bool:
        ps = self.players[player_id]
        if len(ps.hand) >= URF_HAND_LIMIT:
            ps.discard.append(card)
            if log:
                self.log_msg(f"{self.pn(player_id)}手牌已满，{card.name_cn}进入弃牌堆")
            return False
        ps.hand.append(card)
        return True

    def _draw_to_hand_by_type(self, player_id: int, card_type: str):
        card = self.create_infinite_card(card_type)
        if not card:
            return
        added = self.add_card_to_urf_hand(player_id, card, log=True)
        if added:
            type_name = CARD_TYPE_CN.get(card_type, card_type)
            self.log_msg(f"{self.pn(player_id)}补充1张{type_name}牌：{card.name_cn}")

    def _fusion_extra_replenish_types(self, player_id: int, card: Optional[CardInstance], choice) -> List[str]:
        if not card or card.def_id != 'Fusion' or not isinstance(choice, dict):
            return []
        ids = choice.get('target_instance_ids') or []
        if not isinstance(ids, list) or len(ids) < 2:
            return []
        selected = []
        for instance_id in ids[:3]:
            target = self.players[player_id].find_hand_card(instance_id)
            if target is not None and target.instance_id != card.instance_id:
                selected.append(target)
        if len(selected) < 2:
            return []
        if any(c.card_type != 'thorn' for c in selected):
            return []
        if len({c.def_id for c in selected}) != 1:
            return []
        return [selected[0].card_type] * (len(selected) - 1)

    def _deal_starting_hand(self, ps: InfinitePlayerState):
        ps.hand = []
        for card_type, count in URF_STARTING_HAND_COUNTS.items():
            for _ in range(count):
                card = self.create_infinite_card(card_type)
                if card:
                    ps.hand.append(card)

    def start_draft(self):
        self.start_game()

    def start_game(self):
        self.phase = 'playing'
        self._build_infinite_pool()
        self.first_player = random.randint(0, 1)
        self.current_player = self.first_player
        self.opening_event_picks = [None, None]
        self.opening_event_sub_choices = [None, None]
        for i in range(2):
            ps = self.players[i]
            ps.is_first_player = (i == self.first_player)
            ps.deck = []
            ps.discard = []
            ps.exile = []
            ps.hand = []
            ps.equipment = []
            ps.health = INITIAL_HEALTH
            ps.max_health = BASE_MAX_HEALTH
            ps.base_max_health = BASE_MAX_HEALTH
            ps.elixir = INITIAL_ELIXIR
            ps.magic = INITIAL_MAGIC
            ps.urf_replace_available = True
            ps.urf_sell_available = True
        other = 1 - self.first_player
        self.players[other].health = SECOND_PLAYER_HEALTH
        self.players[other].max_health = SECOND_PLAYER_HEALTH
        self.players[other].base_max_health = SECOND_PLAYER_HEALTH
        for i in range(2):
            ps = self.players[i]
            if i == self.first_player:
                ps.elixir = FIRST_PLAYER_ELIXIR
            self._deal_starting_hand(ps)
        self.round_num = 1
        self.log_msg(f"无限火力开始！{self.pn(self.first_player)}先手。")
        self.log_msg(f"=== 第{self.round_num}回合 ===")
        self._start_player_turn(self.first_player)

    def _start_draw_phase(self):
        for i in range(2):
            ps = self.players[i]
            ps.cards_played_this_turn = {}
            ps.magic_battery_m_this_turn = 0
            ps.coffee_first_use = True
            ps.custom_vars['咖啡首次使用'] = 1
            ps.urf_replace_available = True
            ps.urf_sell_available = True
        self.log_msg(f"=== 第{self.round_num}回合 ===")
        self._start_player_turn(self.first_player)

    def _start_player_turn(self, player_id: int):
        ps = self.players[player_id]
        ps.urf_replace_available = True
        ps.urf_sell_available = True
        super()._start_player_turn(player_id)

    def _apply_turn_start_effects(self, player_id: int):
        ps = self.players[player_id]
        opp_id = 1 - player_id
        opp = self.players[opp_id]
        self._antenna_reveal[player_id] = None
        if ps.shovel_active:
            ps.shovel_active = False
            ps.untargetable = False
            self.log_msg(f"{self.pn(player_id)}的铲子效果结束")
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
            self._deal_direct_damage(player_id, ps.poison, '中毒')
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
                ps.draw_cards(DRAW_PER_TURN)
                self.log_msg(f"{self.pn(player_id)}的黄金叶效果：补充手牌")

    def can_play_card(self, player_id: int, card: CardInstance):
        ok, reason = super().can_play_card(player_id, card)
        if not ok:
            return ok, reason
        if card.card_type == 'root' and len(self.players[player_id].equipment) >= URF_EQUIPMENT_LIMIT:
            return False, f'无限火力装备上限为{URF_EQUIPMENT_LIMIT}，请先售卖装备'
        return True, ''

    def play_card(self, player_id: int, card_instance_id: int, choice=None) -> dict:
        ps = self.players[player_id]
        card = ps.find_hand_card(card_instance_id)
        card_type = card.card_type if card else None
        extra_replenish_types = self._fusion_extra_replenish_types(player_id, card, choice)
        result = super().play_card(player_id, card_instance_id, choice)
        if result.get('success') and not result.get('needs_choice') and card_type:
            self._draw_to_hand_by_type(player_id, card_type)
            for extra_type in extra_replenish_types:
                self._draw_to_hand_by_type(player_id, extra_type)
        return result

    def resolve_choice(self, player_id: int, choice: dict) -> dict:
        pending = self.pending_choice or {}
        pending_card = None
        card_type = None
        if pending.get('card'):
            try:
                pending_card = CardInstance.from_dict(pending['card'])
                card_type = pending_card.card_type
            except Exception:
                card_type = None
        extra_replenish_types = self._fusion_extra_replenish_types(player_id, pending_card, choice)
        result = super().resolve_choice(player_id, choice)
        if result.get('success') and card_type:
            self._draw_to_hand_by_type(player_id, card_type)
            for extra_type in extra_replenish_types:
                self._draw_to_hand_by_type(player_id, extra_type)
        return result

    def handle_response(self, responder_id: int, card_instance_id: Optional[int]) -> dict:
        pending = self.pending_response or {}
        player_id = pending.get('player_id')
        counter_type = None
        counter_instance_id = None
        if card_instance_id is not None and 0 <= responder_id < len(self.players):
            counter = self.players[responder_id].find_hand_card(card_instance_id)
            if counter:
                counter_type = counter.card_type
                counter_instance_id = counter.instance_id
        result = super().handle_response(responder_id, card_instance_id)
        if result.get('success') and counter_type and counter_instance_id is not None:
            if self.players[responder_id].find_hand_card(counter_instance_id) is None:
                self._draw_to_hand_by_type(responder_id, counter_type)
        return result

    def _effect_mimic(self, player_id: int, card: CardInstance, choice=None):
        ps = self.players[player_id]
        if choice and 'target_instance_id' in choice:
            target = ps.find_hand_card(choice['target_instance_id'])
            if target:
                copy_card = target.copy()
                copy_card.mimic_discount = 1
                if self.add_card_to_urf_hand(player_id, copy_card, log=False):
                    self.log_msg(f"{self.pn(player_id)}使用拟态！复制了{target.name_cn}（费用-1）")
                else:
                    self.log_msg(f"{self.pn(player_id)}使用拟态，但手牌已满")

    def replace_hand_card(self, player_id: int, card_instance_id: int) -> dict:
        if self.phase != 'action' or self.current_player != player_id:
            return {'success': False, 'error': '不是你的回合'}
        ps = self.players[player_id]
        if not getattr(ps, 'urf_replace_available', True):
            return {'success': False, 'error': '本回合已经替换过手牌'}
        card = ps.remove_hand_card(card_instance_id)
        if not card:
            return {'success': False, 'error': '卡牌不在手中'}
        ps.discard.append(card)
        new_card = self.create_infinite_card(card.card_type)
        if new_card:
            self.add_card_to_urf_hand(player_id, new_card, log=True)
            self.log_msg(f"{self.pn(player_id)}替换了{card.name_cn}，获得{new_card.name_cn}")
        ps.urf_replace_available = False
        return {'success': True}

    def sell_equipment(self, player_id: int, equipment_instance_id: int) -> dict:
        if self.phase != 'action' or self.current_player != player_id:
            return {'success': False, 'error': '不是你的回合'}
        ps = self.players[player_id]
        if not getattr(ps, 'urf_sell_available', True):
            return {'success': False, 'error': '本回合已经售卖过装备'}
        eq = ps.find_equipment(equipment_instance_id)
        if not eq:
            return {'success': False, 'error': '装备不存在'}
        if 'indestructible' in eq.card_instance.flags:
            return {'success': False, 'error': '不可摧毁装备不能被售卖'}
        eq = ps.remove_equipment(equipment_instance_id)
        if not eq:
            return {'success': False, 'error': '装备不存在'}
        refund_e = (eq.card_def.cost_e + 1) // 2
        refund_m = (eq.card_def.cost_m + 1) // 2
        ps.gain_elixir(refund_e)
        ps.gain_magic(refund_m)
        ps.discard.append(eq.card_instance)
        ps.urf_sell_available = False
        self.log_msg(f"{self.pn(player_id)}售卖{eq.card_def.name_cn}，回复{refund_e}E/{refund_m}M")
        return {'success': True}

    def get_public_state(self, for_player: int) -> dict:
        state = super().get_public_state(for_player)
        state['mode'] = 'urf'
        state['infinite_fire'] = True
        state['you']['deck_count'] = '∞'
        state['opponent']['deck_count'] = '∞'
        state['urf_replace_available'] = getattr(self.players[for_player], 'urf_replace_available', True)
        state['urf_sell_available'] = getattr(self.players[for_player], 'urf_sell_available', True)
        state['urf_hand_limit'] = URF_HAND_LIMIT
        return state
