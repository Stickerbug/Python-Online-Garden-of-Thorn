import random
import math
from typing import List, Dict, Optional, Tuple, Set
from game_engine import GameEngine, PlayerState, EquipmentInstance
from cards import (
    CardDef, CardInstance, CARD_DEFS, DRAFT_RATIO, DRAFT_REROLLS,
    HAND_LIMIT, DRAW_PER_TURN, ELIXIR_RECOVERY, BASE_MAX_HEALTH,
    BASE_MAX_ELIXIR, BASE_MAX_MAGIC, INITIAL_HEALTH, INITIAL_ELIXIR,
    INITIAL_MAGIC, FIRST_PLAYER_ELIXIR, SECOND_PLAYER_HEALTH,
    DECK_SIZE, INITIAL_HAND_SIZE, FIRST_PLAYER_HAND_SIZE, build_draft_pool, generate_draft_options,
    create_deck_from_draft,
)


class GameEngine2v2(GameEngine):
    def __init__(self):
        self.num_players = 4
        self.teams: List[List[int]] = [[0, 1], [2, 3]]
        self.players = [PlayerState(i) for i in range(4)]
        self.current_player: int = 0
        self.first_player: int = 0
        self.turn_order: List[int] = [0, 2, 1, 3]
        self.turn_index: int = 0
        self.round_num: int = 0
        self.phase: str = 'waiting'
        self.log: List[str] = []
        self.draft_pool: List[CardInstance] = []
        self.allowed_card_ids: Optional[Set[str]] = None
        self.draft_options: List[List[CardInstance]] = [[], [], [], []]
        self.draft_picks: List[List[str]] = [[], [], [], []]
        self.draft_rerolls: List[int] = [DRAFT_REROLLS] * 4
        self.draft_round: int = 0
        self.draft_type_order: List[str] = []
        self.pending_response: Optional[dict] = None
        self.pending_choice: Optional[dict] = None
        self.halve_next_attack: bool = False
        self.game_over: bool = False
        self.winner: int = -1
        self.winning_team: int = -1
        self._game_over_defer_depth: int = 0
        self.negated_card: bool = False
        self._yggdrasil_check: bool = True
        self._antenna_reveal: List[Optional[list]] = [None] * 4
        self.opening_event_options: List[List[dict]] = [[], [], [], []]
        self.opening_event_picks: List[Optional[int]] = [None] * 4
        self.opening_event_sub_choices: List[Optional[dict]] = [None] * 4
        self.opening_event_magic_options: List[List[List[str]]] = [[[], [], []] for _ in range(4)]
        self.player_names: List[str] = ['玩家1', '玩家2', '玩家3', '玩家4']
        self.debug_selector_log: bool = False
        self._last_damage_value: List[int] = [0] * 4
        self._incoming_damage_hint: List[int] = [0] * 4
        self._last_attacker: Dict[int, int] = {}

    def team_of(self, player_id: int) -> int:
        for ti, team in enumerate(self.teams):
            if player_id in team:
                return ti
        return -1

    def get_teammate(self, player_id: int) -> int:
        team = self.teams[self.team_of(player_id)]
        for p in team:
            if p != player_id:
                return p
        return -1

    def get_enemies(self, player_id: int) -> List[int]:
        my_team = self.team_of(player_id)
        enemies = []
        for ti, team in enumerate(self.teams):
            if ti != my_team:
                for p in team:
                    if self.players[p].health > 0:
                        enemies.append(p)
        return enemies

    def get_all_enemies(self, player_id: int) -> List[int]:
        my_team = self.team_of(player_id)
        enemies = []
        for ti, team in enumerate(self.teams):
            if ti != my_team:
                enemies.extend(team)
        return enemies

    def is_ally(self, player_id: int, other_id: int) -> bool:
        return self.team_of(player_id) == self.team_of(other_id)

    def is_enemy(self, player_id: int, other_id: int) -> bool:
        return self.team_of(player_id) != self.team_of(other_id)

    def _resolve_target(self, player_id, target_str):
        if target_str is None or target_str == '' or target_str == 'self':
            return player_id
        if isinstance(target_str, int):
            return target_str
        if target_str == 'enemy':
            enemies = self.get_enemies(player_id)
            return enemies[0] if enemies else -1
        if target_str == 'both':
            return -1
        if target_str == 'random':
            enemies = self.get_enemies(player_id)
            return random.choice(enemies) if enemies else -1
        if target_str == 'teammate':
            return self.get_teammate(player_id)
        return player_id

    def _resolve_targets(self, player_id, target_str):
        if target_str in ('both', 'random_side'):
            return list(range(self.num_players))
        if target_str in ('friendly', 'self', None, ''):
            return [player_id]
        if target_str == 'teammate':
            mate = self.get_teammate(player_id)
            return [mate] if mate >= 0 else []
        if target_str == 'enemy':
            return self.get_enemies(player_id)
        if target_str == 'all_enemies':
            return self.get_all_enemies(player_id)
        if target_str == 'random_friendly':
            team = self.teams[self.team_of(player_id)]
            alive = [p for p in team if self.players[p].health > 0]
            return [random.choice(alive)] if alive else []
        if target_str == 'random_enemy':
            enemies = self.get_enemies(player_id)
            return [random.choice(enemies)] if enemies else []
        if target_str == 'random_player':
            alive = [i for i in range(self.num_players) if self.players[i].health > 0]
            return [random.choice(alive)] if alive else []
        rid = self._resolve_target(player_id, target_str)
        if rid == -1:
            return list(range(self.num_players))
        return [rid]

    def get_public_state(self, for_player: int) -> dict:
        teammate_id = self.get_teammate(for_player)
        enemy_ids = self.get_all_enemies(for_player)

        opp_data_list = []
        for eid in enemy_ids:
            ed = self.players[eid].to_dict(include_private=False)
            if self._antenna_reveal[for_player]:
                ed['revealed_hand'] = [c.to_dict() for c in self.players[eid].hand]
            opp_data_list.append(ed)

        teammate_data = None
        if teammate_id >= 0:
            teammate_data = self.players[teammate_id].to_dict(include_private=True)
            if self.pending_choice and self.pending_choice.get('player_id') == for_player:
                ct = self.pending_choice.get('choice_type', '')
                if ct in ('choose_from_enemy_hand',):
                    for eid in enemy_ids:
                        opp_data_list[enemy_ids.index(eid)]['hand'] = [c.to_dict() for c in self.players[eid].hand]

        log_start = max(0, len(self.log) - 50)
        return {
            'phase': self.phase,
            'current_player': self.current_player,
            'round_num': self.round_num,
            'game_over': self.game_over,
            'winner': self.winner,
            'winning_team': self.winning_team,
            'you': self.players[for_player].to_dict(include_private=True),
            'opponent': opp_data_list[0] if len(opp_data_list) > 0 else {},
            'opponent2': opp_data_list[1] if len(opp_data_list) > 1 else {},
            'teammate': teammate_data,
            'teammate_id': teammate_id,
            'enemy_ids': enemy_ids,
            'team_id': self.team_of(for_player),
            'teams': self.teams,
            'log': self.log[log_start:],
            'log_start': log_start,
            'log_total': len(self.log),
            'pending_response': self.pending_response,
            'pending_choice': self.pending_choice,
            'pending_ally_request': getattr(self, 'pending_ally_request', None),
            'opening_event_picks': self.opening_event_picks,
            'antenna_reveal': self._antenna_reveal[for_player],
            'mode': '2v2',
        }

    def start_draft(self):
        self.phase = 'draft'
        self.draft_pool = build_draft_pool(self.allowed_card_ids)
        self.draft_picks = [[], [], [], []]
        self.draft_rerolls = [DRAFT_REROLLS] * 4
        self.draft_round = 0
        self.draft_type_order = []
        for card_type, count in DRAFT_RATIO.items():
            self.draft_type_order.extend([card_type] * count)
        random.shuffle(self.draft_type_order)
        for i in range(4):
            self._generate_draft_options_for_player(i)

    def draft_pick(self, player_id: int, card_def_id: str) -> dict:
        if player_id < 0 or player_id >= 4:
            return {'success': False, 'error': '无效玩家'}
        if self.phase != 'draft':
            return {'success': False, 'error': '不在选牌阶段'}
        options = self.draft_options[player_id]
        found = None
        for c in options:
            if c.def_id == card_def_id:
                found = c
                break
        if found is None:
            return {'success': False, 'error': '该牌不在选项中'}
        self.draft_picks[player_id].append(card_def_id)
        if len(self.draft_picks[player_id]) >= DECK_SIZE:
            pass
        else:
            self._generate_draft_options_for_player(player_id)
        all_done = all(len(p) >= DECK_SIZE for p in self.draft_picks)
        if all_done:
            self.phase = 'event_select'
            self._generate_opening_events()
        return {'success': True, 'picks': self.draft_picks[player_id], 'all_done': all_done}

    def start_game(self):
        self.phase = 'playing'
        force_first = []
        for i in range(4):
            if self.opening_event_picks[i] == 7:
                force_first.append(i)
        if len(force_first) == 1:
            self.first_player = force_first[0]
        else:
            first_team = random.randint(0, 1)
            first_in_team = random.choice(self.teams[first_team])
            self.first_player = first_in_team

        self.turn_order = self._build_turn_order(self.first_player)
        self.turn_index = 0
        self.current_player = self.turn_order[0]

        for i in range(4):
            ps = self.players[i]
            ps.is_first_player = (i == self.first_player)
            ps.deck = create_deck_from_draft(self.draft_picks[i])
            ps.health = INITIAL_HEALTH
            ps.max_health = BASE_MAX_HEALTH
            ps.base_max_health = BASE_MAX_HEALTH
            ps.elixir = INITIAL_ELIXIR
            ps.magic = INITIAL_MAGIC

        for i in range(4):
            self._apply_opening_event(i)

        for i in range(4):
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
        self.log_msg(f"2v2游戏开始！{self.pn(self.first_player)}先手。")
        self.log_msg(f"回合顺序：{' → '.join(self.pn(p) for p in self.turn_order)}")
        self.log_msg(f"=== 第{self.round_num}回合 ===")
        self._start_player_turn(self.first_player)

    def _build_turn_order(self, first_player: int) -> List[int]:
        first_team = self.team_of(first_player)
        second_team = 1 - first_team
        first_mate = self.get_teammate(first_player)
        second_team_players = self.teams[second_team]
        order = [first_player]
        if first_mate >= 0:
            second = second_team_players[0]
            third = first_mate
            fourth = second_team_players[1] if len(second_team_players) > 1 else second_team_players[0]
            order = [first_player, second, third, fourth]
        else:
            order = [first_player, second_team_players[0]]
        return order

    def _start_player_turn(self, player_id: int):
        ps = self.players[player_id]
        if ps.health <= 0:
            self._advance_turn()
            return
        self.current_player = player_id
        ps.gain_elixir(ELIXIR_RECOVERY)
        ps.gain_magic(1)
        ps.cards_played_this_turn = {}
        ps.magic_battery_m_this_turn = 0
        ps.coffee_first_use = True
        if ps.bandage_death_pending:
            ps.health = 0
            ps.bandage_death_pending = False
            self.log_msg(f"{self.pn(player_id)}的绷带效果结束，生命值归零！")
            self._on_player_death(player_id)
            if self.game_over:
                return
            self._advance_turn()
            return
        if ps.skip_turn:
            ps.skip_turn = False
            self.log_msg(f"{self.pn(player_id)}被跳过本回合！")
            self._advance_turn()
            return
        draw_count = DRAW_PER_TURN
        if ps.enemy_draw_reduction > 0:
            draw_count = max(0, draw_count - ps.enemy_draw_reduction)
            ps.enemy_draw_reduction -= 1
        ps.draw_cards(draw_count)
        if ps.fire > 0:
            fire_dmg = ps.fire
            ps.health -= fire_dmg
            self.log_msg(f"{self.pn(player_id)}受到{fire_dmg}灼烧伤害（H={ps.health}）")
            ps.fire = 0
            self._check_yggdrasil(player_id)
            if self.game_over:
                return
            self._check_game_over()
            if self.game_over:
                return
        if ps.poison > 0:
            poison_dmg = ps.poison
            ps.health -= poison_dmg
            self.log_msg(f"{self.pn(player_id)}受到{poison_dmg}中毒伤害（H={ps.health}）")
            ps.poison = 0
            self._check_yggdrasil(player_id)
            if self.game_over:
                return
            self._check_game_over()
            if self.game_over:
                return
        for eq in ps.equipment:
            eq.turns_equipped += 1
            if eq.corruption_active:
                ps.health -= 1
                self.log_msg(f"{self.pn(player_id)}的{eq.card_def.name_cn}腐化：-1HP")
        self._check_game_over()
        self.phase = 'action'

    def _advance_turn(self):
        self.turn_index = (self.turn_index + 1) % len(self.turn_order)
        if self.turn_index == 0:
            self._end_round()
        else:
            next_player = self.turn_order[self.turn_index]
            self._start_player_turn(next_player)

    def _end_player_turn(self, player_id: int):
        ps = self.players[player_id]
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
        self._advance_turn()

    def _end_round(self):
        for pid in range(4):
            ps = self.players[pid]
            if ps.invincible and not ps.bandage_active:
                ps.invincible = False
                self.log_msg(f"{self.pn(pid)}的无敌效果结束")
        self.round_num += 1
        if self.game_over:
            return
        self._start_draw_phase()

    def _start_draw_phase(self):
        self.log_msg(f"=== 第{self.round_num}回合 ===")
        self.turn_index = 0
        for pid in range(4):
            ps = self.players[pid]
            if ps.health > 0:
                ps.elixir = min(ps.elixir + ELIXIR_RECOVERY, ps.max_elixir)
                ps.magic = min(ps.magic + 1, ps.max_magic)
        first = self.turn_order[0]
        self._start_player_turn(first)

    def _check_game_over(self):
        if self._game_over_defer_depth > 0:
            return
        team0_alive = any(self.players[p].health > 0 for p in self.teams[0])
        team1_alive = any(self.players[p].health > 0 for p in self.teams[1])
        if not team0_alive and not team1_alive:
            self.game_over = True
            self.winning_team = -1
            self.winner = -1
            self.phase = 'game_over'
            self.log_msg("双方队伍全部阵亡！平局！")
            return
        if not team0_alive:
            self.game_over = True
            self.winning_team = 1
            self.winner = 1
            self.phase = 'game_over'
            self.log_msg(f"队伍{self.teams[1]}获胜！")
            return
        if not team1_alive:
            self.game_over = True
            self.winning_team = 0
            self.winner = 0
            self.phase = 'game_over'
            self.log_msg(f"队伍{self.teams[0]}获胜！")
            return

    def _on_player_death(self, player_id: int):
        ps = self.players[player_id]
        surviving_equip = []
        for eq in ps.equipment:
            if 'indestructible' in eq.card_def.flags:
                surviving_equip.append(eq)
            else:
                self.log_msg(f"{self.pn(player_id)}的{eq.card_def.name_cn}被摧毁")
        ps.equipment = surviving_equip
        self._check_game_over()

    def surrender(self, player_id: int):
        if self.game_over:
            return {'success': False, 'error': '游戏已结束'}
        team = self.team_of(player_id)
        self.game_over = True
        self.winning_team = 1 - team
        self.winner = 1 - team
        self.phase = 'game_over'
        self.log_msg(f"{self.pn(player_id)}投降，队伍{self.teams[self.winning_team]}获胜！")
        return {'success': True}

    def _check_response_needed(self, player_id: int, card: CardInstance) -> bool:
        if 'precision' in card.flags:
            return False
        enemy_ids = self.get_all_enemies(player_id)
        for eid in enemy_ids:
            opp = self.players[eid]
            if opp.health <= 0:
                continue
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
        enemy_ids = self.get_all_enemies(player_id)
        for eid in enemy_ids:
            opp = self.players[eid]
            if opp.health <= 0:
                continue
            for c in opp.hand:
                if c.card_def.response_trigger == 'thorn':
                    return True
        return False

    def play_card(self, player_id: int, card_instance_id: int, target_player_id: int = -1, choice=None) -> dict:
        if self.game_over:
            return {'success': False, 'error': '游戏已结束'}
        if self.current_player != player_id:
            return {'success': False, 'error': '不是你的回合'}
        ps = self.players[player_id]
        card = ps.find_hand_card(card_instance_id)
        if card is None:
            return {'success': False, 'error': '手牌中没有这张牌'}
        can, reason = self.can_play_card(player_id, card)
        if not can:
            return {'success': False, 'error': reason}
        ps.elixir -= card.cost_e
        ps.magic -= card.cost_m
        ps.remove_hand_card(card_instance_id)
        if 'exile' in card.flags:
            ps.exile.append(card)
        else:
            ps.discard.append(card)
        if card.card_type == 'thorn':
            ps.cards_played_this_turn[card.def_id] = ps.cards_played_this_turn.get(card.def_id, 0) + 1
        if target_player_id >= 0:
            if choice is None:
                choice = {}
            choice['target_player'] = target_player_id
        needs_response = self._check_response_needed(player_id, card)
        needs_precision_response = self._check_precision_response_needed(player_id, card)
        if needs_response or needs_precision_response:
            enemy_ids = self.get_all_enemies(player_id)
            counter_cards = []
            for eid in enemy_ids:
                opp = self.players[eid]
                if opp.health <= 0:
                    continue
                for c in opp.hand:
                    if self._card_can_counter(c, card):
                        counter_cards.append({'instance_id': c.instance_id, 'def_id': c.def_id,
                                              'cost_e_override': c.cost_e_override,
                                              'cost_m_override': c.cost_m_override,
                                              'responder_id': eid})
            self.pending_response = {
                'player_id': player_id,
                'card': card.to_dict(),
                'original_choice': choice,
                'counter_cards': counter_cards,
                'is_precision': needs_precision_response and not needs_response,
            }
            return {'success': True, 'needs_response': True, 'card': card.to_dict()}
        return self._execute_card_effect(player_id, card, choice)

    def _card_can_counter(self, counter_card: CardInstance, played_card: CardInstance) -> bool:
        played_def = played_card.card_def
        if played_def.card_type == 'thorn' and counter_card.card_def.response_trigger == 'thorn':
            return True
        if played_def.card_type == 'bloom' and counter_card.card_def.response_trigger == 'bloom':
            return True
        if self._would_destroy_equipment(played_card) and counter_card.card_def.response_trigger == 'equipment_destroy':
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
            if not self._card_can_counter(counter_card, card):
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

    def use_trigger(self, player_id: int, equipment_instance_id: int, target_player_id: int = -1) -> dict:
        if self.current_player != player_id and not self.is_ally(self.current_player, player_id):
            return {'success': False, 'error': '只能在己方回合触发装备'}
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
        if target_player_id < 0:
            enemies = self.get_enemies(player_id)
            target_player_id = enemies[0] if enemies else -1
        self._execute_trigger_effect(player_id, eq, target_player_id)
        self._check_game_over()
        return {'success': True}

    def _execute_trigger_effect(self, player_id: int, eq: EquipmentInstance, target_id: int):
        destroyed = self._destroy_equipment(player_id, eq)
        if not destroyed:
            return
        opp = self.players[target_id] if target_id >= 0 else None
        if eq.def_id == 'Leaf':
            if opp:
                self.deal_attack_damage(target_id, 8)
                self.log_msg(f"{self.pn(player_id)}触发叶子！对{self.pn(target_id)}造成8D")
        elif eq.def_id == 'Mark':
            if opp:
                opp.skip_turn = True
                self.log_msg(f"{self.pn(player_id)}触发标记！{self.pn(target_id)}下回合不能行动")
        elif eq.def_id == 'Mine':
            if opp:
                self.deal_attack_damage(target_id, 20)
                self.log_msg(f"{self.pn(player_id)}触发地雷！对{self.pn(target_id)}造成20D")

    def deal_attack_damage(self, target_id: int, amount: int, hits: int = 1,
                           is_battery: bool = False, is_precision: bool = False,
                           attacker_id: int = -1) -> int:
        ps = self.players[target_id]
        if attacker_id < 0 and hasattr(self, '_last_attacker'):
            attacker_id = self._last_attacker.get(target_id, -1)
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
                self.log_msg(f"精准被反制，伤害减半：{amount}→{dmg}")
            corruption_count = self._get_corruption_count()
            if corruption_count > 0:
                dmg = dmg * (2 ** corruption_count)
                self.log_msg(f"腐化效果：伤害×{2 ** corruption_count}")
            if ps.nazar_active:
                original_dmg = dmg
                dmg = max(1, dmg - 9)
                self.log_msg(f"邪眼护符效果：伤害{original_dmg}→{dmg}")
                if original_dmg >= 10:
                    ps.nazar_big_hits += 1
                    if ps.nazar_big_hits >= 2:
                        ps.nazar_active = False
                        ps.nazar_big_hits = 0
                        self.log_msg(f"{self.pn(target_id)}的邪眼护符被击碎！")
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
            self._check_yggdrasil(target_id)
            if self.game_over:
                break
            if dmg > 0 and not is_battery:
                for eq in ps.equipment:
                    if eq.def_id == 'Battery':
                        if attacker_id >= 0:
                            self._deal_direct_damage(attacker_id, 3, '电池')
                            self.log_msg(f"{self.pn(target_id)}的电池效果：对{self.pn(attacker_id)}造成3D")
                    if eq.def_id == 'MagicBattery':
                        if ps.magic_battery_m_this_turn < 3:
                            ps.gain_magic(1)
                            ps.magic_battery_m_this_turn += 1
                            self.log_msg(f"{self.pn(target_id)}的魔法电池效果：+1M")
            if self.game_over:
                break
            self._check_game_over()
            if ps.health <= 0:
                break
        return total_dealt

    def get_counter_cards(self, player_id: int, trigger_type: str) -> List[CardInstance]:
        ps = self.players[player_id]
        return [c for c in ps.hand if c.card_def.response_trigger == trigger_type]

    def get_enemy_equipment(self, player_id: int) -> List[EquipmentInstance]:
        result = []
        for eid in self.get_all_enemies(player_id):
            result.extend(self.players[eid].equipment)
        return result

    def draft_reroll(self, player_id: int) -> dict:
        if player_id < 0 or player_id >= 4:
            return {'success': False, 'error': '无效玩家'}
        if self.phase != 'draft':
            return {'success': False, 'error': '不在选牌阶段'}
        if self.draft_rerolls[player_id] <= 0:
            return {'success': False, 'error': '没有重选次数'}
        self.draft_rerolls[player_id] -= 1
        self._generate_draft_options_for_player(player_id)
        return {'success': True, 'rerolls_left': self.draft_rerolls[player_id]}

    def _generate_draft_options_for_player(self, player_id: int):
        if len(self.draft_picks[player_id]) >= DECK_SIZE:
            return
        card_type = self.draft_type_order[len(self.draft_picks[player_id])]
        self.draft_options[player_id] = generate_draft_options(self.draft_pool, card_type, 3)

    def _generate_opening_events(self):
        pos1 = [e for e in self.OPENING_EVENTS.values() if e['position'] == 1]
        pos2 = [e for e in self.OPENING_EVENTS.values() if e['position'] == 2]
        pos3 = [e for e in self.OPENING_EVENTS.values() if e['position'] == 3]
        for i in range(4):
            slot1 = pos1[0] if pos1 else None
            slot2 = random.choice(pos2) if pos2 else None
            slot3 = random.choice(pos3) if pos3 else None
            self.opening_event_options[i] = [slot1, slot2, slot3]
            for j in range(3):
                self.opening_event_magic_options[i][j] = random.sample(
                    self.MAGIC_CARD_POOL, min(3, len(self.MAGIC_CARD_POOL)))

    def _is_valid_player_id(self, player_id) -> bool:
        return isinstance(player_id, int) and 0 <= player_id < self.num_players

    def _is_valid_enemy_target(self, player_id: int, target_id) -> bool:
        return self._is_valid_player_id(target_id) and self.is_enemy(player_id, target_id) and self.players[target_id].health > 0

    def _is_valid_effect_target(self, player_id: int, target_id) -> bool:
        return self._is_valid_player_id(target_id) and self.players[target_id].health > 0

    def _card_requires_target(self, card: CardInstance) -> bool:
        if card.card_type == 'guard':
            return False
        if 'self_only' in card.flags:
            return False
        if card.card_type == 'root' and card.card_def.trigger_cost_e >= 0:
            return False
        return card.card_type in ('thorn', 'bloom', 'root')

    def _selected_effect_target(self, player_id: int, choice=None) -> int:
        target_id = choice.get('target_player', -1) if isinstance(choice, dict) else -1
        if self._is_valid_effect_target(player_id, target_id):
            return target_id
        return player_id

    def _selected_enemy_target(self, player_id: int, choice=None) -> int:
        target_id = choice.get('target_player', -1) if isinstance(choice, dict) else -1
        if self._is_valid_effect_target(player_id, target_id):
            return target_id
        enemies = self.get_enemies(player_id)
        return enemies[0] if enemies else -1

    def _resolve_target(self, player_id, target_str):
        if getattr(self, '_active_choice', None):
            selected = self._active_choice.get('target_player')
            if self._is_valid_effect_target(player_id, selected):
                if target_str in ('self', 'friendly', 'enemy', None, ''):
                    return selected
        if target_str is None or target_str == '' or target_str == 'self':
            return player_id
        if isinstance(target_str, int):
            return target_str
        if target_str == 'enemy':
            enemies = self.get_enemies(player_id)
            return enemies[0] if enemies else -1
        if target_str == 'both':
            return -1
        if target_str == 'random':
            enemies = self.get_enemies(player_id)
            return random.choice(enemies) if enemies else -1
        if target_str == 'teammate':
            return self.get_teammate(player_id)
        return player_id

    def _start_draw_phase(self):
        self.log_msg(f"=== 第{self.round_num}回合 ===")
        self.turn_index = 0
        self._start_player_turn(self.turn_order[0])

    def _start_player_turn(self, player_id: int):
        self.current_player = player_id
        ps = self.players[player_id]
        if ps.health <= 0:
            self._advance_turn()
            return
        self._skip_current_turn_after_start = False
        self._apply_turn_start_effects_2v2(player_id)
        if self.game_over:
            return
        if getattr(self, '_skip_current_turn_after_start', False) or ps.health <= 0:
            self._advance_turn()
            return
        if not self.game_over:
            self.phase = 'action'

    def _apply_turn_start_effects_2v2(self, player_id: int):
        ps = self.players[player_id]
        self._antenna_reveal[player_id] = None
        ps.cards_played_this_turn = {}
        ps.magic_battery_m_this_turn = 0
        ps.coffee_first_use = True
        if ps.shovel_active:
            ps.shovel_active = False
            ps.untargetable = False
            self.log_msg(f"{self.pn(player_id)}的铲子效果结束")
        if ps.bandage_death_pending:
            ps.health = 0
            ps.bandage_death_pending = False
            ps.invincible = False
            self.log_msg(f"{self.pn(player_id)}的绷带效果结束，死亡！")
            self._on_player_death(player_id)
            return
        if ps.skip_turn:
            ps.skip_turn = False
            self.log_msg(f"{self.pn(player_id)}被跳过本回合！")
            self._skip_current_turn_after_start = True
            return
        if self.round_num > 1:
            draw_count = max(0, DRAW_PER_TURN - ps.enemy_draw_reduction)
            if ps.enemy_draw_reduction > 0:
                ps.enemy_draw_reduction -= 1
            ps.draw_cards(draw_count)
            self.log_msg(f"{self.pn(player_id)}抽{draw_count}张牌")
            elixir_recovery = ELIXIR_RECOVERY
            for eid in self.get_all_enemies(player_id):
                for eq in self.players[eid].equipment:
                    if eq.def_id == 'Pincer':
                        elixir_recovery -= 1
            elixir_recovery = max(0, elixir_recovery - ps.enemy_e_reduction)
            ps.gain_elixir(elixir_recovery)
            ps.gain_magic(1)
            self.log_msg(f"{self.pn(player_id)}回复{elixir_recovery}E，+1M")
        if self.opening_event_picks[player_id] == 5 and self.round_num <= 2:
            draw_needed = HAND_LIMIT - len(ps.hand)
            if draw_needed > 0:
                ps.draw_cards(draw_needed)
                self.log_msg(f"{self.pn(player_id)}【命运抽签】：抽{draw_needed}张至手牌满")
        if self.opening_event_picks[player_id] == 6 and self.round_num <= 3:
            ps.gain_elixir(2)
            self.log_msg(f"{self.pn(player_id)}【能量涌动】：额外+2E")
        for eid in self.get_all_enemies(player_id):
            for eq in self.players[eid].equipment:
                if eq.def_id == 'Corruption' and not eq.corruption_active:
                    eq.corruption_active = True
                    self.log_msg(f"{self.pn(eid)}的腐化效果激活！")
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
        for eq in list(ps.equipment):
            eq.turns_equipped += 1
        for owner_id, owner_state in enumerate(self.players):
            for eq in list(owner_state.equipment):
                if getattr(eq, 'effect_target', owner_id) != player_id:
                    continue
            if eq.corruption_active:
                self._deal_direct_damage(player_id, 1, eq.card_def.name_cn)
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
        self._check_game_over()

    def _execute_card_effect(self, player_id: int, card: CardInstance, choice=None) -> dict:
        self._active_choice = choice if isinstance(choice, dict) else {}
        try:
            result = super()._execute_card_effect(player_id, card, choice)
            if result.get('needs_choice') and isinstance(choice, dict) and 'target_player' in choice:
                result['player_id'] = player_id
                result['target_player_id'] = choice.get('target_player')
                if self.pending_choice is not None:
                    self.pending_choice['original_choice'] = dict(choice)
            if card.card_type == 'root':
                target_id = self._selected_effect_target(player_id, choice)
                for eq in self.players[player_id].equipment:
                    if eq.card_instance.instance_id == card.instance_id:
                        eq.effect_target = target_id
                        break
            return result
        finally:
            self._active_choice = None

    def resolve_choice(self, player_id: int, choice: dict) -> dict:
        if self.pending_choice is not None:
            original = self.pending_choice.get('original_choice')
            if isinstance(original, dict):
                merged = dict(original)
                if isinstance(choice, dict):
                    merged.update(choice)
                choice = merged
        return super().resolve_choice(player_id, choice)

    def play_card(self, player_id: int, card_instance_id: int, target_player_id: int = -1, choice=None) -> dict:
        ps = self.players[player_id] if self._is_valid_player_id(player_id) else None
        card = ps.find_hand_card(card_instance_id) if ps else None
        if card is None:
            return {'success': False, 'error': '手牌中没有这张牌'}
        if 'self_only' in card.flags or card.card_type == 'guard':
            target_player_id = player_id
        elif self._card_requires_target(card) and not self._is_valid_effect_target(player_id, target_player_id):
            return {'success': False, 'error': '必须选择一名存活玩家'}
        if target_player_id >= 0:
            if choice is None:
                choice = {}
            choice['target_player'] = target_player_id
        if target_player_id != player_id and self.is_ally(player_id, target_player_id):
            if not (choice and choice.get('_ally_approved')):
                self.pending_ally_request = {
                    'player_id': player_id,
                    'target_player_id': target_player_id,
                    'card_instance_id': card_instance_id,
                    'card': card.to_dict(),
                    'choice': dict(choice or {}),
                }
                return {'success': True, 'needs_ally_consent': True, 'card': card.to_dict(), 'target_player_id': target_player_id}
        if self.game_over:
            return {'success': False, 'error': '游戏已经结束'}
        if self.current_player != player_id:
            return {'success': False, 'error': '不是你的回合'}
        can, reason = self.can_play_card(player_id, card)
        if not can:
            return {'success': False, 'error': reason}
        ps.elixir -= card.cost_e
        ps.magic -= card.cost_m
        ps.remove_hand_card(card_instance_id)
        if 'exile' in card.flags:
            ps.exile.append(card)
        else:
            ps.discard.append(card)
        if card.card_type == 'thorn':
            ps.cards_played_this_turn[card.def_id] = ps.cards_played_this_turn.get(card.def_id, 0) + 1
        self._active_choice = choice if isinstance(choice, dict) else {}
        try:
            needs_response = self._check_response_needed(player_id, card)
            needs_precision_response = self._check_precision_response_needed(player_id, card)
            if needs_response or needs_precision_response:
                target_id = self._selected_effect_target(player_id, choice)
                counter_cards = []
                if self._is_valid_player_id(target_id) and self.is_enemy(player_id, target_id) and self.players[target_id].health > 0:
                    for c in self.players[target_id].hand:
                        if self._card_can_counter(c, card):
                            counter_cards.append({
                                'instance_id': c.instance_id,
                                'def_id': c.def_id,
                                'cost_e_override': c.cost_e_override,
                                'cost_m_override': c.cost_m_override,
                                'responder_id': target_id,
                            })
                self.pending_response = {
                    'player_id': player_id,
                    'card': card.to_dict(),
                    'original_choice': choice,
                    'counter_cards': counter_cards,
                    'is_precision': needs_precision_response and not needs_response,
                }
                return {'success': True, 'needs_response': True, 'card': card.to_dict()}
            return self._execute_card_effect(player_id, card, choice)
        finally:
            self._active_choice = None

    def handle_ally_consent(self, target_player_id: int, accepted: bool) -> dict:
        req = getattr(self, 'pending_ally_request', None)
        if not req or req.get('target_player_id') != target_player_id:
            return {'success': False, 'error': '没有待同意的队友用牌'}
        self.pending_ally_request = None
        player_id = req['player_id']
        card = CardInstance.from_dict(req['card'])
        if not accepted:
            self.log_msg(f"{self.pn(target_player_id)}拒绝{self.pn(player_id)}对其使用{card.name_cn}")
            return {'success': True, 'declined': True}
        choice = dict(req.get('choice') or {})
        choice['_ally_approved'] = True
        return self.play_card(player_id, req['card_instance_id'], target_player_id=target_player_id, choice=choice)

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
        if ps.health <= 0:
            self._on_player_death(player_id)
        self._check_game_over()

    def _on_player_death(self, player_id: int):
        ps = self.players[player_id]
        surviving_equip = []
        for eq in ps.equipment:
            if 'indestructible' in eq.card_def.flags:
                surviving_equip.append(eq)
            else:
                ps.discard.append(eq.card_instance)
                self.log_msg(f"{self.pn(player_id)}的{eq.card_def.name_cn}因死亡被摧毁")
        ps.equipment = surviving_equip
        self._check_game_over()

    def deal_attack_damage(self, target_id: int, amount: int, hits: int = 1,
                           is_battery: bool = False, is_precision: bool = False,
                           attacker_id: int = -1) -> int:
        if not self._is_valid_player_id(target_id):
            return 0
        ps = self.players[target_id]
        if attacker_id < 0:
            attacker_id = self._last_attacker.get(target_id, -1)
        if ps.untargetable and not is_battery:
            self.log_msg(f"{self.pn(target_id)}无法被攻击选中！")
            return 0
        total_dealt = 0
        for _ in range(hits):
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
            dmg = amount
            if self.halve_next_attack:
                dmg = math.ceil(dmg / 2)
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
                        if eq.def_id == 'Battery' and attacker_id >= 0:
                            self._deal_direct_damage(attacker_id, 3, '电池')
                            self.log_msg(f"{self.pn(target_id)}的电池效果：对{self.pn(attacker_id)}造成3D")
                        elif eq.def_id == 'MagicBattery' and ps.magic_battery_m_this_turn < 3:
                            ps.gain_magic(1)
                            ps.magic_battery_m_this_turn += 1
                            self.log_msg(f"{self.pn(target_id)}的魔法电池效果：+1M")
            finally:
                self._game_over_defer_depth -= 1
            if ps.health <= 0:
                self._on_player_death(target_id)
            self._check_game_over()
            if self.game_over or ps.health <= 0:
                break
        return total_dealt

    def _attack_target(self, player_id: int, choice=None) -> int:
        return self._selected_enemy_target(player_id, choice)

    def _effect_basic(self, player_id: int, card: CardInstance, choice=None):
        target = self._attack_target(player_id, choice)
        dmg = self._modified_attack_damage(6, card)
        self.log_msg(f"{self.pn(player_id)}使用基本攻击！对{self.pn(target)}造成{dmg}伤害")
        self.deal_attack_damage(target, dmg, attacker_id=player_id)

    def _effect_bone(self, player_id: int, card: CardInstance, choice=None):
        target = self._attack_target(player_id, choice)
        dmg = self._modified_attack_damage(12, card)
        self.log_msg(f"{self.pn(player_id)}使用骨头！对{self.pn(target)}造成{dmg}伤害")
        self.deal_attack_damage(target, dmg, attacker_id=player_id)

    def _effect_stinger(self, player_id: int, card: CardInstance, choice=None):
        target = self._attack_target(player_id, choice)
        dmg = self._modified_attack_damage(20, card)
        self.log_msg(f"{self.pn(player_id)}使用刺！对{self.pn(target)}造成{dmg}伤害")
        self.deal_attack_damage(target, dmg, is_precision=True, attacker_id=player_id)

    def _effect_sand(self, player_id: int, card: CardInstance, choice=None):
        target = self._attack_target(player_id, choice)
        dmg = self._modified_attack_damage(3, card)
        self.log_msg(f"{self.pn(player_id)}使用沙子！对{self.pn(target)}造成{dmg}x4伤害")
        self.deal_attack_damage(target, dmg, 4, attacker_id=player_id)

    def _effect_wing(self, player_id: int, card: CardInstance, choice=None):
        target = self._attack_target(player_id, choice)
        dmg = self._modified_attack_damage(8, card)
        self.log_msg(f"{self.pn(player_id)}使用翅膀！对{self.pn(target)}造成{dmg}x2伤害")
        self.deal_attack_damage(target, dmg, 2, attacker_id=player_id)

    def _effect_light(self, player_id: int, card: CardInstance, choice=None):
        target = self._attack_target(player_id, choice)
        dmg = self._modified_attack_damage(2, card)
        self.log_msg(f"{self.pn(player_id)}使用轻！对{self.pn(target)}造成{dmg}x2伤害")
        self.deal_attack_damage(target, dmg, 2, attacker_id=player_id)

    def _effect_fang(self, player_id: int, card: CardInstance, choice=None):
        target = self._attack_target(player_id, choice)
        dmg = self._modified_attack_damage(8, card)
        dealt = self.deal_attack_damage(target, dmg, attacker_id=player_id)
        if dealt > 0:
            self.players[player_id].heal(4)
            self.log_msg(f"{self.pn(player_id)}使用尖牙！回复4H")

    def _effect_triangle(self, player_id: int, card: CardInstance, choice=None):
        target = self._attack_target(player_id, choice)
        ps = self.players[player_id]
        dmg = self._modified_attack_damage(6 + 3 * ps.triangle_stacks, card)
        dealt = self.deal_attack_damage(target, dmg, attacker_id=player_id)
        if dealt > 0 and ps.triangle_stacks < 4:
            ps.triangle_stacks += 1
            self.log_msg(f"{self.pn(player_id)}三角形层数+1（{ps.triangle_stacks}）")

    def _effect_magicbone(self, player_id: int, card: CardInstance, choice=None):
        target = self._attack_target(player_id, choice)
        dmg = self._modified_attack_damage(15, card)
        self.deal_attack_damage(target, dmg, attacker_id=player_id)
        self.log_msg(f"{self.pn(player_id)}使用魔法骨头！对{self.pn(target)}造成{dmg}伤害")

    def _effect_magicstinger(self, player_id: int, card: CardInstance, choice=None):
        target = self._attack_target(player_id, choice)
        dmg = self._modified_attack_damage(30, card)
        self.deal_attack_damage(target, dmg, is_precision=True, attacker_id=player_id)
        self.log_msg(f"{self.pn(player_id)}使用魔法刺！对{self.pn(target)}造成{dmg}伤害")

    def _effect_iris(self, player_id: int, card: CardInstance, choice=None):
        target = self._attack_target(player_id, choice)
        self.players[target].poison += 10
        self.log_msg(f"{self.pn(player_id)}使用鸢尾！{self.pn(target)}+10中毒")

    def _effect_fire(self, player_id: int, card: CardInstance, choice=None):
        target = self._attack_target(player_id, choice)
        self.players[target].fire += 2
        self.log_msg(f"{self.pn(player_id)}使用火！{self.pn(target)}+2灼烧")

    def _effect_cancer(self, player_id: int, card: CardInstance, choice=None):
        target = self._attack_target(player_id, choice)
        self.players[target].toxic += 1
        self.log_msg(f"{self.pn(player_id)}装备了癌细胞！{self.pn(target)}+1淬毒")

    def _apply_turn_start_effects_2v2(self, player_id: int):
        ps = self.players[player_id]
        self._antenna_reveal[player_id] = None
        ps.cards_played_this_turn = {}
        ps.magic_battery_m_this_turn = 0
        ps.coffee_first_use = True
        if ps.shovel_active:
            ps.shovel_active = False
            ps.untargetable = False
            self.log_msg(f"{self.pn(player_id)}的铲子效果结束")
        if ps.bandage_death_pending:
            ps.health = 0
            ps.bandage_death_pending = False
            ps.invincible = False
            self.log_msg(f"{self.pn(player_id)}的绷带效果结束，死亡！")
            self._on_player_death(player_id)
            return
        if ps.skip_turn:
            ps.skip_turn = False
            self.log_msg(f"{self.pn(player_id)}被跳过本回合！")
            self._skip_current_turn_after_start = True
            return
        if self.round_num > 1:
            draw_count = max(0, DRAW_PER_TURN - ps.enemy_draw_reduction)
            if ps.enemy_draw_reduction > 0:
                ps.enemy_draw_reduction -= 1
            ps.draw_cards(draw_count)
            self.log_msg(f"{self.pn(player_id)}抽{draw_count}张牌")
            pincer_reduction = sum(
                1
                for owner_id, owner_state in enumerate(self.players)
                for eq in owner_state.equipment
                if eq.def_id == 'Pincer' and getattr(eq, 'effect_target', owner_id) == player_id
            )
            elixir_recovery = max(0, ELIXIR_RECOVERY - ps.enemy_e_reduction - pincer_reduction)
            ps.gain_elixir(elixir_recovery)
            ps.gain_magic(1)
            self.log_msg(f"{self.pn(player_id)}回复{elixir_recovery}E，+1M")
        if self.opening_event_picks[player_id] == 5 and self.round_num <= 2:
            draw_needed = HAND_LIMIT - len(ps.hand)
            if draw_needed > 0:
                ps.draw_cards(draw_needed)
                self.log_msg(f"{self.pn(player_id)}【命运抽签】：抽{draw_needed}张至手牌满")
        if self.opening_event_picks[player_id] == 6 and self.round_num <= 3:
            ps.gain_elixir(2)
            self.log_msg(f"{self.pn(player_id)}【能量涌动】：额外+2E")
        for eid in self.get_all_enemies(player_id):
            for eq in self.players[eid].equipment:
                if eq.def_id == 'Corruption' and not eq.corruption_active:
                    eq.corruption_active = True
                    self.log_msg(f"{self.pn(eid)}的腐化效果激活！")
        if ps.poison > 0:
            self._deal_direct_damage(player_id, ps.poison, '中毒')
            if self.game_over or ps.health <= 0:
                return
            ps.poison = ps.poison // 2
        if ps.fire > 0:
            self._deal_direct_damage(player_id, ps.fire, '灼烧')
            if self.game_over or ps.health <= 0:
                return
        for eq in list(ps.equipment):
            eq.turns_equipped += 1
        for owner_id, owner_state in enumerate(self.players):
            for eq in list(owner_state.equipment):
                if getattr(eq, 'effect_target', owner_id) != player_id:
                    continue
                if eq.corruption_active:
                    self._deal_direct_damage(player_id, 1, eq.card_def.name_cn)
                if eq.def_id == 'Leaf':
                    ps.heal(2)
                    self.log_msg(f"{eq.card_def.name_cn}效果：{self.pn(player_id)}+2H")
                elif eq.def_id == 'Yucca':
                    ps.heal(5)
                    self.log_msg(f"{eq.card_def.name_cn}效果：{self.pn(player_id)}+5H")
                elif eq.def_id == 'MagicLeaf':
                    ps.gain_magic(1)
                    self.log_msg(f"{eq.card_def.name_cn}效果：{self.pn(player_id)}+1M")
                elif eq.def_id == 'MagicYucca':
                    ps.gain_magic(2)
                    self.log_msg(f"{eq.card_def.name_cn}效果：{self.pn(player_id)}+2M")
                elif eq.def_id == 'Powder':
                    ps.gain_elixir(2)
                    self.log_msg(f"{eq.card_def.name_cn}效果：{self.pn(player_id)}+2E")
                elif eq.def_id == 'GoldenLeaf':
                    ps.draw_cards(1)
                    self.log_msg(f"{eq.card_def.name_cn}效果：{self.pn(player_id)}多抽1张牌")
        self._check_game_over()

    def use_trigger(self, player_id: int, equipment_instance_id: int, target_player_id: int = -1) -> dict:
        if self.current_player != player_id and not self.is_ally(self.current_player, player_id):
            return {'success': False, 'error': '只能在己方回合触发装备'}
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
        if not self._is_valid_effect_target(player_id, target_player_id):
            return {'success': False, 'error': '必须选择一名存活玩家'}
        ps.elixir -= eq.card_def.trigger_cost_e
        self._execute_trigger_effect(player_id, eq, target_player_id)
        self._check_game_over()
        return {'success': True}

    def _check_response_needed(self, player_id: int, card: CardInstance) -> bool:
        if 'precision' in card.flags:
            return False
        target_id = self._selected_effect_target(player_id, getattr(self, '_active_choice', None))
        if not self._is_valid_player_id(target_id) or not self.is_enemy(player_id, target_id):
            return False
        opp = self.players[target_id]
        if card.card_type == 'thorn':
            return any(c.card_def.response_trigger == 'thorn' for c in opp.hand)
        if card.card_type == 'bloom':
            return any(c.card_def.response_trigger == 'bloom' for c in opp.hand)
        if self._would_destroy_equipment(card):
            return any(c.card_def.response_trigger == 'equipment_destroy' for c in opp.hand)
        return False

    def _check_precision_response_needed(self, player_id: int, card: CardInstance) -> bool:
        if 'precision' not in card.flags:
            return False
        target_id = self._selected_effect_target(player_id, getattr(self, '_active_choice', None))
        if not self._is_valid_player_id(target_id) or not self.is_enemy(player_id, target_id):
            return False
        return any(c.card_def.response_trigger == 'thorn' for c in self.players[target_id].hand)

    def both_events_selected(self) -> bool:
        return all(p is not None for p in self.opening_event_picks)
