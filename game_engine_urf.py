import random
from typing import List, Optional, Set

from game_engine import GameEngine, PlayerState
from cards import (
    CardInstance, CARD_DEFS, INITIAL_HEALTH, INITIAL_ELIXIR,
    INITIAL_MAGIC, FIRST_PLAYER_ELIXIR, SECOND_PLAYER_HEALTH,
    INITIAL_HAND_SIZE, FIRST_PLAYER_HAND_SIZE, BASE_MAX_HEALTH,
)

URF_HAND_LIMIT = 8


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

    def _draw_one_infinite(self) -> Optional[CardInstance]:
        return self._infinite_engine.create_infinite_card()

    def draw_cards(self, count: int) -> List[CardInstance]:
        drawn = []
        sprout_queue = []
        for _ in range(count):
            card = self._draw_one_infinite()
            if card is None:
                break
            if len(self.hand) >= URF_HAND_LIMIT:
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
            if trigger not in self.hand:
                continue
            extra = self._draw_one_infinite()
            if extra is None:
                break
            if len(self.hand) < URF_HAND_LIMIT:
                self.hand.append(extra)
                drawn.append(extra)
                if 'sprout' in extra.flags:
                    sprout_queue.append(extra)
            else:
                self.discard.append(extra)
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
            ctype = CARD_DEFS[def_id].card_type
            by_type.setdefault(ctype, {'ids': [], 'weights': []})
            by_type[ctype]['ids'].append(def_id)
            by_type[ctype]['weights'].append(max(1, int(getattr(CARD_DEFS[def_id], 'count', 1) or 1)))
        self.infinite_by_type = by_type

    def create_infinite_card(self, card_type: Optional[str] = None) -> Optional[CardInstance]:
        if not self.infinite_card_pool:
            self._build_infinite_pool()
        if card_type:
            pool = self.infinite_by_type.get(card_type) or {}
            ids = pool.get('ids') or []
            weights = pool.get('weights') or []
            if ids:
                return CardInstance(def_id=random.choices(ids, weights=weights, k=1)[0])
        if not self.infinite_card_pool:
            return None
        def_id = random.choices(self.infinite_card_pool, weights=self.infinite_card_weights, k=1)[0]
        return CardInstance(def_id=def_id)

    def _draw_to_hand_by_type(self, player_id: int, card_type: str):
        card = self.create_infinite_card(card_type)
        if not card:
            return
        ps = self.players[player_id]
        if len(ps.hand) >= URF_HAND_LIMIT:
            ps.discard.append(card)
        else:
            ps.hand.append(card)
            self.log_msg(f"{self.pn(player_id)}补充1张{card_type}牌：{card.name_cn}")

    def _deal_starting_hand(self, ps):
        ps.hand = []
        for card_type in ('thorn', 'bloom', 'root', 'guard'):
            for _ in range(2):
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
            ps.urf_replace_available = True
            ps.urf_sell_available = True
        self.log_msg(f"=== 第{self.round_num}回合 ===")
        self._start_player_turn(self.first_player)

    def _start_player_turn(self, player_id: int):
        ps = self.players[player_id]
        ps.urf_replace_available = True
        ps.urf_sell_available = True
        super()._start_player_turn(player_id)

    def can_play_card(self, player_id: int, card: CardInstance):
        ok, reason = super().can_play_card(player_id, card)
        if not ok:
            return ok, reason
        if card.card_type == 'root' and len(self.players[player_id].equipment) >= 3:
            return False, '无限火力装备上限为3，请先售卖装备'
        return True, ''

    def play_card(self, player_id: int, card_instance_id: int, choice=None) -> dict:
        ps = self.players[player_id]
        card = ps.find_hand_card(card_instance_id)
        card_type = card.card_type if card else None
        result = super().play_card(player_id, card_instance_id, choice)
        if result.get('success') and not result.get('needs_response') and not result.get('needs_choice') and card_type:
            self._draw_to_hand_by_type(player_id, card_type)
        return result

    def handle_response(self, responder_id: int, card_instance_id: Optional[int]) -> dict:
        pending = self.pending_response or {}
        player_id = pending.get('player_id')
        card_type = None
        if pending.get('card'):
            card_type = CardInstance.from_dict(pending['card']).card_type
        result = super().handle_response(responder_id, card_instance_id)
        if result.get('success') and player_id is not None and card_type:
            self._draw_to_hand_by_type(player_id, card_type)
        return result

    def replace_hand_card(self, player_id: int, card_instance_id: int) -> dict:
        if self.phase != 'action' or self.current_player != player_id:
            return {'success': False, 'error': '不是你的回合'}
        ps = self.players[player_id]
        if not getattr(ps, 'urf_replace_available', True):
            return {'success': False, 'error': '本回合已替换过手牌'}
        card = ps.remove_hand_card(card_instance_id)
        if not card:
            return {'success': False, 'error': '卡牌不在手中'}
        ps.discard.append(card)
        new_card = self.create_infinite_card(card.card_type)
        if new_card:
            ps.hand.append(new_card)
            self.log_msg(f"{self.pn(player_id)}替换了{card.name_cn}，获得{new_card.name_cn}")
        ps.urf_replace_available = False
        return {'success': True}

    def sell_equipment(self, player_id: int, equipment_instance_id: int) -> dict:
        if self.phase != 'action' or self.current_player != player_id:
            return {'success': False, 'error': '不是你的回合'}
        ps = self.players[player_id]
        if not getattr(ps, 'urf_sell_available', True):
            return {'success': False, 'error': '本回合已售卖过装备'}
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
        return state
