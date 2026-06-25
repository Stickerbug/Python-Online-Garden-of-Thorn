import random
import math
from typing import List, Dict, Optional, Tuple, Set
from game_engine import GameEngine, PlayerState, EquipmentInstance
from damage_types import (
    DAMAGE_TAG_BATTERY, DAMAGE_TAG_DIRECT, DAMAGE_TAG_FIRE, DAMAGE_TAG_PHYSICAL, DAMAGE_TAG_POISON,
    DAMAGE_TYPE_MAGIC, DAMAGE_TYPE_PHYSICAL, infer_damage_type, status_damage_tag,
)
from cards import (
    CardDef, CardInstance, CARD_DEFS, DRAFT_RATIO, DRAFT_REROLLS,
    DRAW_PER_TURN, ELIXIR_RECOVERY, BASE_MAX_HEALTH,
    BASE_MAX_ELIXIR, BASE_MAX_MAGIC, INITIAL_HEALTH, INITIAL_ELIXIR,
    INITIAL_MAGIC, FIRST_PLAYER_ELIXIR, SECOND_PLAYER_HEALTH,
    DECK_SIZE, INITIAL_HAND_SIZE, FIRST_PLAYER_HAND_SIZE, build_draft_pool, generate_draft_options,
    create_deck_from_draft, ERROR_CARD_ID, clamp_damage_hits,
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
        self.winning_team: int = -1
        self._game_over_defer_depth: int = 0
        self.negated_card: bool = False
        self._yggdrasil_check: bool = True
        self._antennae_reveal: List[Optional[list]] = [None] * 4
        self._antennae_reveal_targets: List[Optional[int]] = [None] * 4
        self.opening_event_options: List[List[dict]] = [[], [], [], []]
        self.opening_event_picks: List[Optional[int]] = [None] * 4
        self.opening_event_sub_choices: List[Optional[dict]] = [None] * 4
        self.opening_event_magic_options: List[List[List[str]]] = [[[], [], []] for _ in range(4)]
        # Per-player ready state: True when draft done AND sub-choice done (if any)
        self.player_ready: List[bool] = [False] * 4
        self.player_draft_started: List[bool] = [False] * 4
        self.player_names: List[str] = ['玩家1', '玩家2', '玩家3', '玩家4']
        self.debug_selector_log: bool = False
        self._last_damage_value: List[int] = [0] * 4
        self._last_positive_damage_hits: List[int] = [0] * 4
        self._incoming_damage_hint: List[int] = [0] * 4
        self._last_attacker: Dict[int, int] = {}
        self.custom_vars: Dict[str, int] = {}
        self.team_custom_vars: Dict[str, Dict[str, int]] = {}
        self._last_created_card_instance_id: Optional[int] = None
        self._pending_foresight: Optional[dict] = None
        self.timed_effects: List[dict] = []
        self._init_mod_variables()
        self._bind_player_callbacks()

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

    def _opening_event_enemy_targets(self, player_id: int):
        return self.get_all_enemies(player_id)

    def is_ally(self, player_id: int, other_id: int) -> bool:
        return self.team_of(player_id) == self.team_of(other_id)

    def is_enemy(self, player_id: int, other_id: int) -> bool:
        return self.team_of(player_id) != self.team_of(other_id)

    def _refresh_hand_limit_bonuses(self):
        for ps in self.players:
            ps.extra_hand_limit_bonus = 0
        for owner_id, owner_state in enumerate(self.players):
            for eq in owner_state.equipment:
                if eq.def_id != 'GoldenLeaf':
                    continue
                target_id = getattr(eq, 'effect_target', owner_id)
                if target_id != owner_id and 0 <= target_id < len(self.players):
                    self.players[target_id].extra_hand_limit_bonus += 1



    def get_public_state(self, for_player: int) -> dict:
        self._refresh_hand_limit_bonuses()
        teammate_id = self.get_teammate(for_player)
        enemy_ids = self.get_all_enemies(for_player)

        opp_data_list = []
        for eid in enemy_ids:
            ed = self.players[eid].to_dict(include_private=False)
            ed['hand_count'] = len([c for c in self.players[eid].hand if c.def_id != ERROR_CARD_ID])
            ed['deck_count'] = len([c for c in self.players[eid].deck if c.def_id != ERROR_CARD_ID])
            ed['discard_count'] = len([c for c in self.players[eid].discard if c.def_id != ERROR_CARD_ID])
            ed['exile_count'] = len([c for c in self.players[eid].exile if c.def_id != ERROR_CARD_ID])
            reveal_target = getattr(self, '_antennae_reveal_targets', [None] * self.num_players)[for_player]
            if self._antennae_reveal[for_player] and reveal_target == eid:
                ed['revealed_hand'] = self._visible_card_dicts(self.players[eid].hand, for_player, eid)
            revealed_tag_cards = [
                c.to_dict()
                for c in self.players[eid].hand
                if c.def_id != ERROR_CARD_ID and 'revealed' in getattr(c, 'flags', set())
            ]
            if revealed_tag_cards:
                ed['revealed_tag_cards'] = revealed_tag_cards
            opp_data_list.append(ed)

        teammate_data = None
        if teammate_id >= 0:
            teammate_data = self.players[teammate_id].to_dict(include_private=True)
            self._redact_error_cards_from_payload(teammate_data)
            if self.pending_choice and self.pending_choice.get('player_id') == for_player:
                ct = self.pending_choice.get('choice_type', '')
                target_id = self.pending_choice.get('target_player_id')
                if ct in ('choose_from_enemy_hand',):
                    if target_id in enemy_ids:
                        opp_data_list[enemy_ids.index(target_id)]['hand'] = self._visible_card_dicts(self.players[target_id].hand, for_player, target_id)
                params = self.pending_choice.get('choice_params', {}) or {}
                if target_id in enemy_ids and ct in ('choose_card_from_hand', 'choose_from_deck', 'choose_from_discard', 'choose_from_exile', 'choose_equipment'):
                    ed = opp_data_list[enemy_ids.index(target_id)]
                    zone = params.get('zone', '')
                    if ct == 'choose_card_from_hand' or zone == 'hand':
                        ed['hand'] = self._visible_card_dicts(self.players[target_id].hand, for_player, target_id)
                    if ct == 'choose_from_deck' or zone == 'deck':
                        ed['deck'] = self._visible_card_dicts(self.players[target_id].deck, for_player, target_id)
                    if ct == 'choose_from_discard' or zone == 'discard':
                        ed['discard'] = self._visible_card_dicts(self.players[target_id].discard, for_player, target_id)
                    if ct == 'choose_from_exile' or zone == 'exile':
                        ed['exile'] = self._visible_card_dicts(self.players[target_id].exile, for_player, target_id)

        log_start = 0
        self._mark_log_visible()
        you_data = self.players[for_player].to_dict(include_private=True)
        return {
            'phase': self.phase,
            'current_player': self.current_player,
            'round_num': self.round_num,
            'game_over': self.game_over,
            'winner': self.winner,
            'winning_team': self.winning_team,
            'you': you_data,
            'opponent': opp_data_list[0] if len(opp_data_list) > 0 else {},
            'opponent2': opp_data_list[1] if len(opp_data_list) > 1 else {},
            'teammate': teammate_data,
            'teammate_id': teammate_id,
            'enemy_ids': enemy_ids,
            'team_id': self.team_of(for_player),
            'teams': self.teams,
            'log': list(self.log),
            'log_start': log_start,
            'log_total': len(self.log),
            'pending_response': self.pending_response,
            'pending_choice': self.pending_choice,
            'pending_v2_ui': self._public_v2_ui(for_player),
            'pending_ally_request': getattr(self, 'pending_ally_request', None),
            'opening_event_picks': self.opening_event_picks,
            'antennae_reveal': self._antennae_reveal[for_player],
            'mode': '2v2',
        }

    def start_event_select_first(self):
        """Start event_select phase before draft. Called after matching."""
        self.phase = 'event_select'
        self.draft_rerolls = [DRAFT_REROLLS] * 4
        self.player_ready = [False] * 4
        self.player_draft_started = [False] * 4
        self._generate_opening_events()

    def start_draft_for_player(self, player_id: int):
        """Initialize draft for a specific player after they select their event.
        Called independently per player - no need to wait for others."""
        # Initialize draft pool and type order on first call
        if not self.draft_pool:
            self.draft_pool = build_draft_pool(self.allowed_card_ids)
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
        if len(self.draft_picks[player_id]) >= self.draft_target_count(player_id):
            pass
        else:
            self._generate_draft_options_for_player(player_id)
        all_done = all(len(self.draft_picks[i]) >= self.draft_target_count(i) for i in range(4))
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
            ps.deck = create_deck_from_draft(self.draft_picks[i], self.allowed_card_ids)
            ps.health = INITIAL_HEALTH
            ps.max_health = BASE_MAX_HEALTH
            ps.base_max_health = BASE_MAX_HEALTH
            ps.elixir = INITIAL_ELIXIR
            ps.magic = INITIAL_MAGIC
        for pid in range(4):
            self._enforce_unique_cards_for_player(pid)
        self._enforce_team_unique_cards()
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
                if self.opening_event_picks[i] == 5:
                    hand_size = max(0, hand_size - 1)
                ps.draw_cards(hand_size)
            else:
                hand_size = INITIAL_HAND_SIZE
                if self.opening_event_picks[i] == 5:
                    hand_size = max(0, hand_size - 1)
                ps.draw_cards(hand_size)

        self._save_all_match_start_snapshots()
        self.round_num = 1
        self.log_msg(f"2v2游戏开始！{self.pn(self.first_player)}先手。")
        self.log_msg(f"回合顺序：{' → '.join(self.pn(p) for p in self.turn_order)}")
        self.log_msg(f"=== 第{self.round_num}回合 ===")
        self._start_player_turn(self.first_player)

    def _enforce_team_unique_cards(self):
        for team in self.teams:
            grouped = {}
            for pid in team:
                ps = self.players[pid]
                for zone in (ps.hand, ps.deck, ps.discard):
                    for card in list(zone):
                        if 'team_unique' in self._effective_card_flags(card):
                            grouped.setdefault(card.def_id, []).append((pid, zone, card))
            for _def_id, entries in grouped.items():
                if len(entries) <= 1:
                    continue
                keep = random.choice(entries)
                for pid, zone, card in entries:
                    if (pid, zone, card) == keep:
                        continue
                    if card in zone:
                        zone.remove(card)
                        self.players[pid].exile.append(card)
                        self.log_msg(f"{self.pn(pid)}的{card.name_cn}因队伍独一被放逐")

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


    def _advance_turn(self):
        self.turn_index = (self.turn_index + 1) % len(self.turn_order)
        if self.turn_index == 0:
            self._end_round()
        else:
            next_player = self.turn_order[self.turn_index]
            self._start_player_turn(next_player)

    def _end_player_turn(self, player_id: int):
        ps = self.players[player_id]
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
            self.log_msg(f"{self.pn(player_id)}的绷带效果结束，生命值归零！")
            self._on_player_death(player_id)
            if self.game_over:
                return
        if ps.bandage_active and ps.invincible:
            ps.bandage_active = False
            ps.bandage_death_pending = True
            self.log_msg(f"{self.pn(player_id)}的绷带无敌将持续到下一个自己回合结束")
        # Fracture: clear at end of own turn
        if ps.fracture > 0:
            ps.fracture = 0
            self.log_msg(f"{self.pn(player_id)}的破损效果消失")
        # Heal block: decrement at end of own turn
        if ps.heal_block > 0:
            ps.heal_block = max(0, ps.heal_block - 1)
            if ps.heal_block == 0:
                self.log_msg(f"{self.pn(player_id)}的禁疗效果消失")
        # Weakness: decrement at end of own turn
        if ps.weakness > 0:
            ps.weakness = max(0, ps.weakness - 1)
            if ps.weakness == 0:
                self.log_msg(f"{self.pn(player_id)}的虚弱效果消失")
        # Bleed: halve at end of turn
        if ps.bleed > 0:
            ps.bleed = max(0, ps.bleed // 2)
            if ps.bleed == 0:
                self.log_msg(f"{self.pn(player_id)}的流血效果消失")
        self._decay_end_turn_layer_statuses(player_id)
        # Track M gained this turn for next turn's check
        ps.m_gained_last_turn = ps.m_gained_this_turn
        ps.m_gained_this_turn = False
        self._return_cogwheel_cards_now(player_id)
        void_cards = [c for c in ps.hand if 'void' in c.flags]
        for c in void_cards:
            ps.hand.remove(c)
            ps.exile.append(c)
            self.log_msg(f"{self.pn(player_id)}的{c.name_cn}因虚无被放逐")
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
        self._advance_turn()

    def _end_round(self):
        self.round_num += 1
        if self.game_over:
            return
        self._start_draw_phase()


    def _check_game_over(self):
        if self._game_over_defer_depth > 0:
            return
        for i in range(self.num_players):
            if self.players[i].health <= 0:
                self._check_yggdrasil(i)
        team0_alive = any(self.players[p].health > 0 for p in self.teams[0])
        team1_alive = any(self.players[p].health > 0 for p in self.teams[1])
        if not team0_alive and not team1_alive:
            self.game_over = True
            self.winning_team = -1
            self.winner = -1
            self.phase = 'game_over'
            self.log_msg("双方队伍全部阵亡！平局！")
            return
        if self.game_over:
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

    def _clear_dead_player_private_zones(self, player_id: int):
        if not self._is_valid_player_id(player_id):
            return
        # Dead players can be revived, so keep their hand/deck intact.
        return


    def _remove_equipment_targeting_dead_player(self, dead_player_id: int):
        if not self._is_valid_player_id(dead_player_id):
            return
        for owner_id, owner_state in enumerate(self.players):
            for eq in list(owner_state.equipment):
                if getattr(eq, 'effect_target', owner_id) != dead_player_id:
                    continue
                if 'indestructible' in eq.card_instance.flags:
                    continue
                if self._destroy_equipment(owner_id, eq, check_protection=False):
                    self.log_msg(f"{self.pn(owner_id)}的{eq.card_def.name_cn}因目标死亡移出装备区")

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




    def _card_can_counter(self, counter_card: CardInstance, played_card: CardInstance) -> bool:
        played_def = played_card.card_def
        if counter_card.card_def.response_trigger == 'any':
            return True
        if played_def.card_type == 'thorn' and counter_card.card_def.response_trigger == 'thorn':
            return True
        if played_def.card_type == 'bloom' and counter_card.card_def.response_trigger == 'bloom':
            return True
        if played_def.card_type == 'root' and counter_card.card_def.response_trigger == 'root':
            return True
        if self._would_heal(played_card) and counter_card.card_def.response_trigger == 'heal':
            return True
        if self._would_destroy_equipment(played_card) and counter_card.card_def.response_trigger == 'equipment_destroy':
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
            if counter_card.cost_e > responder.elixir or counter_card.cost_m > responder.magic:
                return self._after_response_result(player_id, self._execute_card_effect(player_id, card, choice))
            if not self._card_can_counter(counter_card, card):
                return self._after_response_result(player_id, self._execute_card_effect(player_id, card, choice))
            self._spend_resource(responder_id, 'elixir', counter_card.cost_e, counter_card)
            self._spend_resource(responder_id, 'magic', counter_card.cost_m, counter_card)
            counter_removed = responder.remove_hand_card(card_instance_id)
            if counter_removed is None:
                return self._after_response_result(player_id, self._execute_card_effect(player_id, card, choice))
            self.log_msg(f"{self.pn(responder_id)}使用{counter_removed.name_cn}进行反制！")
            dodge_before_counter = int(getattr(responder, 'dodge', 0) or 0)
            self._game_over_defer_depth += 1
            try:
                self._execute_counter_effect(responder_id, counter_removed, card, player_id, pending_damage_prediction)
                is_precision = pending.get('is_precision', False)
                if counter_removed.def_id == 'Bubble':
                    if is_precision:
                        self._execute_card_effect_half_damage(player_id, card, choice)
                        responder.dodge = min(int(getattr(responder, 'dodge', 0) or 0), dodge_before_counter)
                        return self._after_response_result(player_id, {'success': True, 'countered': True, 'precision_halved': True, 'card': card.to_dict()})
                    self._execute_card_effect(player_id, card, choice)
                    responder.dodge = min(int(getattr(responder, 'dodge', 0) or 0), dodge_before_counter)
                    return self._after_response_result(player_id, {'success': True, 'countered': True, 'card': card.to_dict()})
                if counter_removed.def_id == 'MagicBubble':
                    self.negated_card = True
                return self._after_response_result(player_id, self._execute_card_effect(player_id, card, choice))
            finally:
                self._game_over_defer_depth -= 1
                self._check_game_over()
        return self._after_response_result(player_id, self._execute_card_effect(player_id, card, choice))


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
                if self._status_application_blocked(target_id, 'skip_turn'):
                    return
                opp.skip_turn += 1
                self.log_msg(f"{self.pn(player_id)}触发标记！{self.pn(target_id)}+1层眩晕")
        elif eq.def_id == 'Mine':
            if opp:
                self.deal_attack_damage(target_id, 20)
                self.log_msg(f"{self.pn(player_id)}触发地雷！对{self.pn(target_id)}造成20D")


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
        if len(self.draft_picks[player_id]) >= self.draft_target_count(player_id):
            return
        card_type = self.draft_type_order[len(self.draft_picks[player_id])]
        self.draft_options[player_id] = generate_draft_options(self.draft_pool, card_type, 3)

    def _generate_opening_events(self):
        pool = self._all_opening_events()
        for i in range(4):
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
            self.opening_event_magic_options[i] = [[] for _ in options]

    def _is_valid_player_id(self, player_id) -> bool:
        return isinstance(player_id, int) and 0 <= player_id < self.num_players

    def _normalize_player_id(self, player_id, default: int = -1) -> int:
        try:
            return int(player_id)
        except (TypeError, ValueError):
            return default

    def _is_valid_enemy_target(self, player_id: int, target_id) -> bool:
        return (
            self._is_valid_player_id(target_id)
            and self.is_enemy(player_id, target_id)
            and self.players[target_id].health > 0
            and not (bool(getattr(self.players[target_id], 'untargetable', False)) and not self._is_status_immune(target_id))
        )

    def _is_valid_attack_target(self, player_id: int, target_id) -> bool:
        return (
            self._is_valid_player_id(target_id)
            and target_id != player_id
            and self.players[target_id].health > 0
            and not (bool(getattr(self.players[target_id], 'untargetable', False)) and not self._is_status_immune(target_id))
        )

    def _is_valid_effect_target(self, player_id: int, target_id) -> bool:
        return (
            self._is_valid_player_id(target_id)
            and self.players[target_id].health > 0
            and (
                target_id == player_id
                or not (bool(getattr(self.players[target_id], 'untargetable', False)) and not self._is_status_immune(target_id))
            )
        )

    def _card_requires_target(self, card: CardInstance) -> bool:
        if card.card_type == 'guard':
            return False
        if self._card_is_self_only(card) and card.card_type != 'thorn':
            return False
        if card.card_type == 'thorn':
            return True
        if card.card_type in ('bloom', 'root'):
            return self._v2_play_requires_choice_target(card) or self._root_play_requires_owner_target(card)
        return False

    def _selected_effect_target(self, player_id: int, choice=None) -> int:
        target_id = -1
        if isinstance(choice, dict):
            for key in ('target_player', 'target_player_id', 'target_id'):
                if key in choice:
                    target_id = choice.get(key)
                    break
        if self._is_valid_effect_target(player_id, target_id):
            return target_id
        return player_id

    def _selected_enemy_target(self, player_id: int, choice=None) -> int:
        target_id = -1
        if isinstance(choice, dict):
            for key in ('target_player', 'target_player_id', 'target_id'):
                if key in choice:
                    target_id = choice.get(key)
                    break
        if self._is_valid_enemy_target(player_id, target_id):
            return target_id
        enemies = self.get_enemies(player_id)
        for enemy_id in enemies:
            if self._is_valid_enemy_target(player_id, enemy_id):
                return enemy_id
        return -1

    def _selected_attack_target(self, player_id: int, choice=None) -> int:
        target_id = -1
        if isinstance(choice, dict):
            for key in ('target_player', 'target_player_id', 'target_id'):
                if key in choice:
                    target_id = choice.get(key)
                    break
        if self._is_valid_attack_target(player_id, target_id):
            return target_id
        enemies = self.get_enemies(player_id)
        for enemy_id in enemies:
            if self._is_valid_attack_target(player_id, enemy_id):
                return enemy_id
        return -1


    def _start_draw_phase(self):
        self.log_msg(f"=== 第{self.round_num}回合 ===")
        self._apply_late_round_fire_pressure()
        if self.game_over:
            return
        self.turn_index = 0
        self._start_player_turn(self.turn_order[0])

    def _start_player_turn(self, player_id: int):
        self.current_player = player_id
        self._refresh_hand_limit_bonuses()
        ps = self.players[player_id]
        if ps.health <= 0:
            self._advance_turn()
            return
        self._skip_current_turn_after_start = False
        self._apply_turn_start_effects_2v2(player_id)
        if self.game_over:
            return
        if self.pending_choice is not None or getattr(self, 'pending_v2_ui', None):
            return
        if getattr(self, '_skip_current_turn_after_start', False) or ps.health <= 0:
            self._advance_turn()
            return
        if not self.game_over:
            self.phase = 'action'
            self._continue_honey_control_if_needed(player_id)


    def _execute_card_effect(self, player_id: int, card: CardInstance, choice=None) -> dict:
        self._active_choice = choice if isinstance(choice, dict) else {}
        try:
            result = super()._execute_card_effect(player_id, card, choice)
            if result.get('needs_choice') and isinstance(choice, dict) and 'target_player' in choice:
                result['player_id'] = player_id
                if self.pending_choice is not None:
                    self.pending_choice['original_choice'] = dict(choice)
                    if self.pending_choice.get('target_player_id') is not None:
                        result['target_player_id'] = self.pending_choice.get('target_player_id')
            if card.card_type == 'root':
                target_id = self._selected_effect_target(player_id, choice)
                found = False
                for owner in self.players:
                    for eq in owner.equipment:
                        if eq.card_instance.instance_id == card.instance_id:
                            eq.effect_target = target_id
                            found = True
                            break
                    if found:
                        break
            return result
        finally:
            self._active_choice = None

    def _magic_nazar_counter_player_ids(self, player_id: int, card: Optional[CardInstance] = None,
                                        choice: Optional[dict] = None) -> List[int]:
        return [pid for pid in self.get_all_enemies(player_id) if self.players[pid].health > 0]

    def _atomic_reveal_enemy_hand(self, player_id, card, params, log, choice, context):
        target_id = self._resolve_target(player_id, params.get('target', 'enemy'))
        if not self._is_valid_player_id(target_id):
            return
        opp = self.players[target_id]
        self._antennae_reveal[player_id] = [c.to_dict() for c in opp.hand]
        if not hasattr(self, '_antennae_reveal_targets'):
            self._antennae_reveal_targets = [None] * self.num_players
        self._antennae_reveal_targets[player_id] = target_id
        self.log_msg(log or f"{self.pn(player_id)}查看了{self.pn(target_id)}的手牌")

    def resolve_choice(self, player_id: int, choice: dict) -> dict:
        if self.pending_choice is not None:
            original = self.pending_choice.get('original_choice')
            if isinstance(original, dict):
                merged = dict(original)
                if isinstance(choice, dict):
                    merged.update(choice)
                choice = merged
        return super().resolve_choice(player_id, choice)

    def _check_card_response_after_choice(self, player_id: int, card: CardInstance, choice: Optional[dict]) -> Optional[dict]:
        prev_choice = getattr(self, '_active_choice', None)
        if isinstance(choice, dict):
            self._active_choice = choice
        try:
            needs_response = self._check_response_needed(player_id, card)
            needs_precision_response = self._check_precision_response_needed(player_id, card)
        finally:
            self._active_choice = prev_choice
        if not (needs_response or needs_precision_response):
            return None
        target_id = self._selected_effect_target(player_id, choice)
        equipment_destroy_responders = self._equipment_destroy_response_player_ids(player_id, card, choice)
        if card.card_type == 'bloom':
            responder_ids = [enemy_id for enemy_id in self.get_all_enemies(player_id) if self.players[enemy_id].health > 0]
        elif self._would_heal(card):
            responder_ids = [enemy_id for enemy_id in self.get_all_enemies(player_id) if self.players[enemy_id].health > 0]
        elif self._is_valid_player_id(target_id) and self.is_enemy(player_id, target_id) and self.players[target_id].health > 0:
            responder_ids = [target_id]
        else:
            responder_ids = []
        responder_ids = list(dict.fromkeys([*responder_ids, *equipment_destroy_responders]))
        counter_cards = []
        has_payable_counter = False
        for responder_id in responder_ids:
            for c in self.players[responder_id].hand:
                if self._card_can_counter(c, card):
                    if self._can_pay_counter_card(responder_id, c):
                        has_payable_counter = True
                    counter_cards.append({
                        'instance_id': c.instance_id,
                        'def_id': c.def_id,
                        'cost_e_override': c.cost_e_override,
                        'cost_m_override': c.cost_m_override,
                        'responder_id': responder_id,
                    })
        if not has_payable_counter:
            return None
        self.pending_response = {
            'player_id': player_id,
            'target_player_id': target_id,
            'card': card.to_dict(),
            'original_choice': choice,
            'counter_cards': counter_cards,
            'is_precision': needs_precision_response and not needs_response,
        }
        return {'success': True, 'needs_response': True, 'card': card.to_dict()}

    def _equipment_destroy_response_player_ids(self, player_id: int, card: Optional[CardInstance], choice: Optional[dict] = None) -> List[int]:
        if card is None or not self._would_destroy_equipment(card):
            return []
        owners: List[int] = []
        def add_owner(owner_id: int):
            if not self._is_valid_player_id(owner_id) or self.players[owner_id].health <= 0:
                return
            if owner_id not in owners:
                owners.append(owner_id)

        def has_destroyable_equipment(owner_id: int) -> bool:
            if not self._is_valid_player_id(owner_id):
                return False
            return any('indestructible' not in eq.card_instance.flags for eq in self.players[owner_id].equipment)

        card_id = str(getattr(card, 'def_id', '') or '').lower()
        legacy_id = str(getattr(getattr(card, 'card_def', None), 'legacy_id', '') or '').lower()
        if card_id in ('magicsewage', 'vanilla:magicsewage') or legacy_id == 'magicsewage':
            for owner_id in range(len(self.players)):
                if has_destroyable_equipment(owner_id):
                    add_owner(owner_id)
            return owners

        target_id = self._selected_effect_target(player_id, choice)
        if not self._is_valid_player_id(target_id):
            return []
        if isinstance(choice, dict) and choice.get('target_instance_id') is not None:
            eq = self.players[target_id].find_equipment(choice.get('target_instance_id'))
            if eq is not None and 'indestructible' not in eq.card_instance.flags:
                add_owner(target_id)
            return owners
        if has_destroyable_equipment(target_id):
            add_owner(target_id)
        return owners

    def play_card(self, player_id: int, card_instance_id: int, target_player_id: int = -1, choice=None) -> dict:
        target_player_id = self._normalize_player_id(target_player_id)
        ps = self.players[player_id] if self._is_valid_player_id(player_id) else None
        card = ps.find_hand_card(card_instance_id) if ps else None
        if card is None:
            return {'success': False, 'error': '手牌中没有这张牌'}
        if card.def_id == ERROR_CARD_ID:
            ps.remove_hand_card(card_instance_id)
            return {'success': True, 'card': card.to_dict(), 'ignored': True}
        if self.pending_response is not None:
            return {'success': False, 'error': '等待对手反制响应'}
        if getattr(self, 'pending_v2_ui', None) is not None:
            return {'success': False, 'error': 'Waiting for mod UI response'}
        if ('self_only' in card.flags and card.card_type != 'thorn') or card.card_type == 'guard':
            target_player_id = player_id
        elif self._card_requires_target(card) and card.card_type == 'thorn' and target_player_id == player_id:
            return {'success': False, 'error': '攻击牌不能选择自己作为目标'}
        elif self._card_requires_target(card) and card.card_type == 'thorn' and not self._is_valid_attack_target(player_id, target_player_id):
            return {'success': False, 'error': '没有可选中的玩家'}
        elif self._card_requires_target(card):
            allow_dead_target = self._card_is(card, 'Yggdrasil', 'vanilla:yggdrasil')
            if allow_dead_target:
                if (not self._is_valid_player_id(target_player_id)
                        or (target_player_id != player_id
                            and bool(getattr(self.players[target_player_id], 'untargetable', False))
                            and not self._is_status_immune(target_player_id))):
                    return {'success': False, 'error': '没有可选中的玩家'}
            elif not self._is_valid_effect_target(player_id, target_player_id):
                return {'success': False, 'error': '没有可选中的玩家'}
        if target_player_id >= 0:
            if choice is None:
                choice = {}
            choice['target_player'] = target_player_id
        if self.game_over:
            return {'success': False, 'error': '娓告垙宸茬粡缁撴潫'}
        if self.current_player != player_id:
            return {'success': False, 'error': '涓嶆槸浣犵殑鍥炲悎'}
        can, reason = self.can_play_card(player_id, card)
        if not can:
            return {'success': False, 'error': reason}
        if target_player_id != player_id and self.is_ally(player_id, target_player_id) and self.players[target_player_id].health > 0:
            if not (choice and choice.get('_ally_approved')):
                self.pending_ally_request = {
                    'player_id': player_id,
                    'target_player_id': target_player_id,
                    'card_instance_id': card_instance_id,
                    'card': card.to_dict(),
                    'choice': dict(choice or {}),
                }
                return {'success': True, 'needs_ally_consent': True, 'card': card.to_dict(), 'target_player_id': target_player_id}
        if self._card_needs_choice(card) and not self._choice_satisfies_request(card, choice):
            queued = self._queue_card_choice(player_id, card, choice, already_paid=False)
            if queued:
                return queued
        if not self._defer_v2_before_play_until_choice(card, choice):
            self._run_v2_play_hook('before_play_card', player_id, card, choice)
            if getattr(self, 'pending_v2_ui', None) is not None:
                return {'success': True, 'needs_v2_ui': True, 'card': card.to_dict()}
        extra_e = self._get_extra_e_for_card(player_id, card)
        card._paid_e_this_play = int(card.cost_e + extra_e)
        self._spend_resource(player_id, 'elixir', card.cost_e + extra_e, card)
        self._spend_resource(player_id, 'magic', card.cost_m, card)
        ps.remove_hand_card(card_instance_id)
        ps.cards_played_this_turn[card.def_id] = ps.cards_played_this_turn.get(card.def_id, 0) + 1
        ps.cards_played_this_turn_instance_ids.append(int(getattr(card, 'instance_id', card_instance_id) or card_instance_id))
        self._apply_magic_acceleration_after_play(player_id, card)
        self._active_choice = choice if isinstance(choice, dict) else {}
        try:
            if self._card_needs_choice(card) and not self._choice_satisfies_request(card, choice):
                return self._execute_card_effect(player_id, card, choice)
            needs_response = self._check_response_needed(player_id, card)
            needs_precision_response = self._check_precision_response_needed(player_id, card)
            if needs_response or needs_precision_response:
                target_id = self._selected_effect_target(player_id, choice)
                counter_cards = []
                has_payable_counter = False
                equipment_destroy_responders = self._equipment_destroy_response_player_ids(player_id, card, choice)
                if card.card_type == 'bloom':
                    responder_ids = [enemy_id for enemy_id in self.get_all_enemies(player_id) if self.players[enemy_id].health > 0]
                elif self._would_heal(card):
                    responder_ids = [enemy_id for enemy_id in self.get_all_enemies(player_id) if self.players[enemy_id].health > 0]
                elif self._is_valid_player_id(target_id) and self.is_enemy(player_id, target_id) and self.players[target_id].health > 0:
                    responder_ids = [target_id]
                else:
                    responder_ids = []
                responder_ids = list(dict.fromkeys([*responder_ids, *equipment_destroy_responders]))
                for responder_id in responder_ids:
                    for c in self.players[responder_id].hand:
                        if self._card_can_counter(c, card):
                            if self._can_pay_counter_card(responder_id, c):
                                has_payable_counter = True
                            counter_cards.append({
                                'instance_id': c.instance_id,
                                'def_id': c.def_id,
                                'cost_e_override': c.cost_e_override,
                                'cost_m_override': c.cost_m_override,
                                'responder_id': responder_id,
                            })
                if has_payable_counter:
                    self.pending_response = {
                        'player_id': player_id,
                        'target_player_id': target_id,
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
        if req.get('action') == 'trigger':
            return self.use_trigger(
                player_id,
                req['equipment_instance_id'],
                target_player_id=target_player_id,
                ally_approved=True,
            )
        choice = dict(req.get('choice') or {})
        choice['_ally_approved'] = True
        return self.play_card(player_id, req['card_instance_id'], target_player_id=target_player_id, choice=choice)

    def _deal_direct_damage(self, player_id: int, amount: int, source: str = '', source_id: int = None,
                            damage_type: Optional[str] = None, damage_tag: Optional[str] = None):
        if not self._is_valid_player_id(player_id):
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
        ps.health -= actual
        self._record_damage(player_id, actual, source_id)
        self.log_msg(f"{self.pn(player_id)}受到{actual}点{source}伤害（H={ps.health}）")
        self._run_v2_after_damage_hooks(damage_context, actual)
        if not getattr(self, '_defer_turn_start_death_checks', False):
            self._check_yggdrasil(player_id)
            if ps.health <= 0:
                self._on_player_death(player_id)
            self._check_game_over()
        return actual

    def _on_player_death(self, player_id: int):
        ps = self.players[player_id]
        surviving_equip = []
        for eq in ps.equipment:
            if 'indestructible' in eq.card_instance.flags:
                surviving_equip.append(eq)
            else:
                owner_id = getattr(eq, 'owner', player_id)
                try:
                    owner_id = int(owner_id)
                except (TypeError, ValueError):
                    owner_id = player_id
                if not self._is_valid_player_id(owner_id):
                    owner_id = player_id
                if 'exile' in eq.card_instance.flags:
                    self.players[owner_id].exile.append(eq.card_instance)
                else:
                    self._discard_card(self.players[owner_id], eq.card_instance)
                self.log_msg(f"{self.pn(player_id)}的{eq.card_def.name_cn}因死亡被摧毁")
        ps.equipment = surviving_equip
        self._remove_equipment_targeting_dead_player(player_id)
        pending_ally = getattr(self, 'pending_ally_request', None)
        if pending_ally and (
            pending_ally.get('player_id') == player_id
            or pending_ally.get('target_player_id') == player_id
        ):
            self.pending_ally_request = None
        self._check_game_over()


    def _attack_target(self, player_id: int, choice=None) -> int:
        return self._selected_attack_target(player_id, choice)

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
        hits = self._card_total_hits(card, 4)
        self.log_msg(f"{self.pn(player_id)}使用沙子！对{self.pn(target)}造成{dmg}x{hits}伤害")
        self.deal_attack_damage(target, dmg, hits, attacker_id=player_id)

    def _effect_wing(self, player_id: int, card: CardInstance, choice=None):
        target = self._attack_target(player_id, choice)
        dmg = self._modified_attack_damage(8, card)
        hits = self._card_total_hits(card, 2)
        self.log_msg(f"{self.pn(player_id)}使用翅膀！对{self.pn(target)}造成{dmg}x{hits}伤害")
        self.deal_attack_damage(target, dmg, hits, attacker_id=player_id)

    def _effect_light(self, player_id: int, card: CardInstance, choice=None):
        target = self._attack_target(player_id, choice)
        dmg = self._modified_attack_damage(2, card)
        hits = self._card_total_hits(card, 2)
        self.log_msg(f"{self.pn(player_id)}使用轻！对{self.pn(target)}造成{dmg}x{hits}伤害")
        self.deal_attack_damage(target, dmg, hits, attacker_id=player_id)

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
        immune = self._is_status_immune(player_id) if hasattr(self, '_is_status_immune') else False
        dmg = self._modified_attack_damage(6 + (0 if immune else 3 * ps.triangle_stacks), card)
        if int(getattr(card, 'fission_hit', 0) or 0) == 0:
            self._log_card_play(player_id, card)
        dealt = self.deal_attack_damage(target, dmg, attacker_id=player_id)
        if dealt > 0 and not immune and ps.triangle_stacks < 4:
            ps.triangle_stacks += 1

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
        if self._status_application_blocked(target, 'poison'):
            return
        self.players[target].poison += 10
        self.log_msg(f"{self.pn(player_id)}使用鸢尾！{self.pn(target)}+10中毒")

    def _effect_fire(self, player_id: int, card: CardInstance, choice=None):
        target = self._attack_target(player_id, choice)
        if self._status_application_blocked(target, 'fire'):
            return
        self.players[target].fire += 2
        self.log_msg(f"{self.pn(player_id)}使用火！{self.pn(target)}+2灼烧")

    def _effect_cancer(self, player_id: int, card: CardInstance, choice=None):
        target = self._attack_target(player_id, choice)
        if self._status_application_blocked(target, 'toxic'):
            return
        self.players[target].toxic += 1
        self.log_msg(f"{self.pn(player_id)}装备了癌细胞！{self.pn(target)}+1淬毒")



    def _check_response_needed(self, player_id: int, card: CardInstance) -> bool:
        flags = self._effective_card_flags(card)
        if 'precision' in flags:
            return False
        if 'stealth' in flags:
            return False
        target_id = self._selected_effect_target(player_id, getattr(self, '_active_choice', None))
        equipment_destroy_responders = self._equipment_destroy_response_player_ids(player_id, card, getattr(self, '_active_choice', None))
        if equipment_destroy_responders and any(
                self._can_pay_counter_card(responder_id, c) and c.card_def.response_trigger == 'equipment_destroy'
                for responder_id in equipment_destroy_responders
                for c in self.players[responder_id].hand
        ):
            return True
        if self._would_heal(card):
            return any(
                self._can_pay_counter_card(enemy_id, c) and c.card_def.response_trigger in ('any', 'heal')
                for enemy_id in self.get_all_enemies(player_id)
                for c in self.players[enemy_id].hand
            )
        if card.card_type == 'bloom':
            return any(
                self._can_pay_counter_card(enemy_id, c) and c.card_def.response_trigger in ('any', 'bloom')
                for enemy_id in self.get_all_enemies(player_id)
                for c in self.players[enemy_id].hand
            )
        if not self._is_valid_player_id(target_id) or not self.is_enemy(player_id, target_id):
            return False
        opp = self.players[target_id]
        if any(self._can_pay_counter_card(target_id, c) and c.card_def.response_trigger == 'any' for c in opp.hand):
            return True
        if card.card_type == 'thorn':
            return any(self._can_pay_counter_card(target_id, c) and c.card_def.response_trigger == 'thorn' for c in opp.hand)
        if card.card_type == 'bloom':
            return any(self._can_pay_counter_card(target_id, c) and c.card_def.response_trigger == 'bloom' for c in opp.hand)
        if card.card_type == 'root':
            return any(self._can_pay_counter_card(target_id, c) and c.card_def.response_trigger == 'root' for c in opp.hand)
        if self._would_destroy_equipment(card):
            return any(self._can_pay_counter_card(target_id, c) and c.card_def.response_trigger == 'equipment_destroy' for c in opp.hand)
        return False

    def _check_precision_response_needed(self, player_id: int, card: CardInstance) -> bool:
        flags = self._effective_card_flags(card)
        if 'precision' not in flags:
            return False
        if 'stealth' in flags:
            return False
        target_id = self._selected_effect_target(player_id, getattr(self, '_active_choice', None))
        if not self._is_valid_player_id(target_id) or not self.is_enemy(player_id, target_id):
            return False
        return any(self._can_pay_counter_card(target_id, c) and c.card_def.response_trigger == 'thorn' for c in self.players[target_id].hand)

    def both_events_selected(self) -> bool:
        return all(p is not None for p in self.opening_event_picks)

    def _apply_turn_start_effects_2v2(self, player_id: int):
        ps = self.players[player_id]
        self._antennae_reveal[player_id] = None
        if hasattr(self, '_antennae_reveal_targets'):
            self._antennae_reveal_targets[player_id] = None
        self._return_cogwheel_cards_now(player_id)
        ps.cards_played_this_turn = {}
        ps.cards_played_this_turn_instance_ids = []
        ps.magic_battery_m_this_turn = 0
        ps.custom_vars['\u9b54\u6cd5\u7535\u6c60\u672c\u56de\u5408\u56de\u9b54'] = 0
        self._run_v2_event_hooks('turn_start', {
            'source_player': player_id,
            'target_player': player_id,
            'vars': {'player_id': player_id},
            'current_action': {'player_id': player_id},
        })
        if self.game_over or getattr(self, 'pending_v2_ui', None):
            return
        self._trigger_v2_status_events_for_player(player_id, 'on_turn_start', {'player_id': player_id})
        if self.game_over or getattr(self, 'pending_v2_ui', None):
            return
        self._apply_jungle_turn_start_statuses(player_id)
        self._run_zone_owner_turn_start_events(player_id)
        self._run_timed_effects_for_turn(player_id)
        if ps.shovel_active:
            ps.shovel_active = False
            ps.untargetable = False
            self.log_msg(f"{self.pn(player_id)}的铲子效果结束")
        self._clear_turn_start_action_statuses(player_id)
        early_owner_turn_start_equipment = self._run_owner_turn_start_action_status_equipment(player_id)
        if self.game_over or getattr(self, 'pending_v2_ui', None):
            return
        self._defer_turn_start_death_checks = True
        turn_will_be_skipped = bool(ps.skip_turn) and not self._is_status_immune(player_id)
        if ps.skip_turn > 0:
            ps.skip_turn = max(0, int(ps.skip_turn) - 1)
        if self.round_num > 1:
            sluggish_reduction = ps.sluggish if not self._is_status_immune(player_id) else 0
            draw_count = max(0, DRAW_PER_TURN - ps.enemy_draw_reduction - sluggish_reduction)
            if ps.enemy_draw_reduction > 0:
                ps.enemy_draw_reduction -= 1
            if self._queue_foresight_replace_choice(player_id, draw_count, 'turn_start_2v2'):
                self._pending_turn_start_2v2_state = {
                    'turn_will_be_skipped': turn_will_be_skipped,
                    'early_owner_turn_start_equipment': set(early_owner_turn_start_equipment),
                }
                return
            drawn = ps.draw_cards(draw_count)
            if sluggish_reduction > 0:
                self.log_msg(f"{self.pn(player_id)}的迟缓减少{min(sluggish_reduction, DRAW_PER_TURN)}张抽牌")
            self._clear_sluggish_after_draw(player_id)
            pincer_overload = sum(
                1
                for owner_id, owner_state in enumerate(self.players)
                for eq in owner_state.equipment
                if not eq.card_def.effects and eq.def_id == 'Pincer' and getattr(eq, 'effect_target', owner_id) == player_id
            )
            if pincer_overload > 0:
                ps.overload += pincer_overload
                self.log_msg(f"{self.pn(player_id)}被螫针施加{pincer_overload}层超载")
            aura_delta = 0
            for owner_id, owner_state in enumerate(self.players):
                for eq in owner_state.equipment:
                    if getattr(eq, 'effect_target', owner_id) != player_id:
                        continue
                    for effect in eq.card_def.effects or []:
                        if isinstance(effect, dict) and effect.get('type') == 'aura_enemy_elixir_recovery':
                            aura_delta += self._eval_int(owner_id, effect.get('params', {}).get('amount', 0), eq.card_instance)
            elixir_recovery = max(0, ELIXIR_RECOVERY - ps.enemy_e_reduction + aura_delta)
            ps.gain_elixir(elixir_recovery)
            self.log_msg(f"{self.pn(player_id)}抽{len(drawn)}张牌，回复{elixir_recovery}E")
            # Overload: deduct E at turn start, then clear
            if ps.overload > 0:
                deduct = min(ps.overload, ps.elixir)
                ps.elixir -= deduct
                self.log_msg(f"{self.pn(player_id)}的超载扣除{deduct}E")
                ps.overload = 0
        if self.opening_event_picks[player_id] == 6 and self.round_num <= 3:
            ps.gain_elixir(2)
        for owner_state in self.players:
            for eq in getattr(owner_state, 'equipment', []):
                eq.uses_this_turn = 0
        for owner_id, owner_state in enumerate(self.players):
            for eq in list(owner_state.equipment):
                if self._has_card_event(eq.card_def, 'any_turn_start'):
                    self._run_card_event(owner_id, eq.card_instance, 'any_turn_start', None,
                                         {'source_id': owner_id, 'target_id': player_id})
        for eid in self.get_all_enemies(player_id):
            for eq in list(self.players[eid].equipment):
                if self._has_card_event(eq.card_def, 'enemy_turn_start') and self._run_card_event(
                        eid, eq.card_instance, 'enemy_turn_start', None,
                        {'source_id': eid, 'target_id': player_id}):
                    continue
                if eq.def_id == 'Corruption' and not eq.corruption_active:
                    eq.corruption_active = True
                    self.log_msg(f"{self.pn(eid)}的腐化效果激活")
        early_owner_turn_start_equipment |= self._run_owner_turn_start_healing_equipment(player_id)
        if self.game_over or getattr(self, 'pending_v2_ui', None):
            self._defer_turn_start_death_checks = False
            return
        if ps.poison > 0:
            if not self._is_status_immune(player_id):
                self._deal_direct_damage(player_id, ps.poison, '中毒', damage_type=DAMAGE_TYPE_MAGIC, damage_tag=DAMAGE_TAG_POISON)
            self._decay_poison_after_turn_start(player_id)
            self._apply_toxic_poison_after_poison_settlement(player_id)
        if ps.fire > 0 and not self._is_status_immune(player_id):
            self._deal_direct_damage(player_id, ps.fire, '灼烧', damage_type=DAMAGE_TYPE_MAGIC, damage_tag=DAMAGE_TAG_FIRE)
        for owner_id, owner_state in enumerate(self.players):
            for eq in list(owner_state.equipment):
                if getattr(eq, 'effect_target', owner_id) != player_id:
                    continue
                if self._equipment_turn_start_key(eq) not in early_owner_turn_start_equipment:
                    eq.turns_equipped += 1
        for owner_id, owner_state in enumerate(self.players):
            for eq in list(owner_state.equipment):
                if getattr(eq, 'effect_target', owner_id) != player_id:
                    continue
                if self._equipment_turn_start_key(eq) in early_owner_turn_start_equipment:
                    continue
                handled = False
                if self._has_card_event(eq.card_def, 'owner_turn_start'):
                    handled = self._run_card_event(owner_id, eq.card_instance, 'owner_turn_start', None,
                                                   {'source_id': owner_id, 'target_id': player_id})
                if handled or eq.card_def.effects:
                    continue
                if eq.corruption_active:
                    self._deal_direct_damage(player_id, 1, eq.card_def.name_cn)
                if eq.def_id == 'Leaf':
                    ps.heal(2)
                    self.log_msg(f"{eq.card_def.name_cn}效果：{self.pn(player_id)}+2H")
                elif eq.def_id == 'Yucca':
                    self._apply_yucca_turn_start_heal(player_id, eq.card_def.name_cn)
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
        if not self.game_over:
            self._apply_jungle_turn_start_regen(player_id)
        self._defer_turn_start_death_checks = False
        if ps.health <= 0:
            self._check_yggdrasil(player_id)
            if ps.health <= 0:
                self._on_player_death(player_id)
            self._check_game_over()
        if turn_will_be_skipped:
            self.log_msg(f"{self.pn(player_id)}被跳过本回合")
            self._skip_current_turn_after_start = True
        self._check_game_over()
        if self.game_over:
            return
        if getattr(self, '_skip_current_turn_after_start', False) or ps.health <= 0:
            self._advance_turn()
            return
        self.phase = 'action'
        self._continue_honey_control_if_needed(player_id)

    def _resume_turn_start_2v2(self, player_id: int, foresight_result: Optional[dict] = None):
        state = getattr(self, '_pending_turn_start_2v2_state', None) or {}
        self._pending_turn_start_2v2_state = None
        ps = self.players[player_id]
        early_owner_turn_start_equipment = set(state.get('early_owner_turn_start_equipment') or set())
        turn_will_be_skipped = bool(state.get('turn_will_be_skipped'))
        self._defer_turn_start_death_checks = True
        if self.round_num > 1:
            draw_count = max(0, int((foresight_result or {}).get('draw_count', 0) or 0))
            drawn = ps.draw_cards(draw_count)
            if ps.sluggish > 0 and not self._is_status_immune(player_id):
                self.log_msg(f"{self.pn(player_id)}的迟缓减少{min(ps.sluggish, DRAW_PER_TURN)}张抽牌")
            self._clear_sluggish_after_draw(player_id)
            pincer_overload = sum(
                1
                for owner_id, owner_state in enumerate(self.players)
                for eq in owner_state.equipment
                if not eq.card_def.effects and eq.def_id == 'Pincer' and getattr(eq, 'effect_target', owner_id) == player_id
            )
            if pincer_overload > 0:
                ps.overload += pincer_overload
                self.log_msg(f"{self.pn(player_id)}被螫针施加{pincer_overload}层超载")
            aura_delta = 0
            for owner_id, owner_state in enumerate(self.players):
                for eq in owner_state.equipment:
                    if getattr(eq, 'effect_target', owner_id) != player_id:
                        continue
                    for effect in eq.card_def.effects or []:
                        if isinstance(effect, dict) and effect.get('type') == 'aura_enemy_elixir_recovery':
                            aura_delta += self._eval_int(owner_id, effect.get('params', {}).get('amount', 0), eq.card_instance)
            elixir_recovery = max(0, ELIXIR_RECOVERY - ps.enemy_e_reduction + aura_delta)
            ps.gain_elixir(elixir_recovery)
            self.log_msg(f"{self.pn(player_id)}抽{len(drawn)}张牌，回复{elixir_recovery}E")
            if ps.overload > 0:
                deduct = min(ps.overload, ps.elixir)
                ps.elixir -= deduct
                self.log_msg(f"{self.pn(player_id)}的超载扣除{deduct}E")
                ps.overload = 0
        if self.opening_event_picks[player_id] == 6 and self.round_num <= 3:
            ps.gain_elixir(2)
        for owner_state in self.players:
            for eq in getattr(owner_state, 'equipment', []):
                eq.uses_this_turn = 0
        for owner_id, owner_state in enumerate(self.players):
            for eq in list(owner_state.equipment):
                if self._has_card_event(eq.card_def, 'any_turn_start'):
                    self._run_card_event(owner_id, eq.card_instance, 'any_turn_start', None,
                                         {'source_id': owner_id, 'target_id': player_id})
        for eid in self.get_all_enemies(player_id):
            for eq in list(self.players[eid].equipment):
                if self._has_card_event(eq.card_def, 'enemy_turn_start') and self._run_card_event(
                        eid, eq.card_instance, 'enemy_turn_start', None,
                        {'source_id': eid, 'target_id': player_id}):
                    continue
                if eq.def_id == 'Corruption' and not eq.corruption_active:
                    eq.corruption_active = True
                    self.log_msg(f"{self.pn(eid)}的腐化效果激活")
        early_owner_turn_start_equipment |= self._run_owner_turn_start_healing_equipment(player_id)
        if self.game_over or getattr(self, 'pending_v2_ui', None):
            self._defer_turn_start_death_checks = False
            return
        if ps.poison > 0:
            if not self._is_status_immune(player_id):
                self._deal_direct_damage(player_id, ps.poison, '中毒', damage_type=DAMAGE_TYPE_MAGIC, damage_tag=DAMAGE_TAG_POISON)
            self._decay_poison_after_turn_start(player_id)
            self._apply_toxic_poison_after_poison_settlement(player_id)
        if ps.fire > 0 and not self._is_status_immune(player_id):
            self._deal_direct_damage(player_id, ps.fire, '灼烧', damage_type=DAMAGE_TYPE_MAGIC, damage_tag=DAMAGE_TAG_FIRE)
        for owner_id, owner_state in enumerate(self.players):
            for eq in list(owner_state.equipment):
                if getattr(eq, 'effect_target', owner_id) != player_id:
                    continue
                if self._equipment_turn_start_key(eq) not in early_owner_turn_start_equipment:
                    eq.turns_equipped += 1
        for owner_id, owner_state in enumerate(self.players):
            for eq in list(owner_state.equipment):
                if getattr(eq, 'effect_target', owner_id) != player_id:
                    continue
                if self._equipment_turn_start_key(eq) in early_owner_turn_start_equipment:
                    continue
                handled = False
                if self._has_card_event(eq.card_def, 'owner_turn_start'):
                    handled = self._run_card_event(owner_id, eq.card_instance, 'owner_turn_start', None,
                                                   {'source_id': owner_id, 'target_id': player_id})
                if handled or eq.card_def.effects:
                    continue
                if eq.corruption_active:
                    self._deal_direct_damage(player_id, 1, eq.card_def.name_cn)
                if eq.def_id == 'Leaf':
                    ps.heal(2)
                    self.log_msg(f"{eq.card_def.name_cn}效果：{self.pn(player_id)}+2H")
                elif eq.def_id == 'Yucca':
                    self._apply_yucca_turn_start_heal(player_id, eq.card_def.name_cn)
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
        if not self.game_over:
            self._apply_jungle_turn_start_regen(player_id)
        self._defer_turn_start_death_checks = False
        if ps.health <= 0:
            self._check_yggdrasil(player_id)
            if ps.health <= 0:
                self._on_player_death(player_id)
            self._check_game_over()
        if turn_will_be_skipped:
            self.log_msg(f"{self.pn(player_id)}被跳过本回合")
            self._skip_current_turn_after_start = True
        self._check_game_over()

    def deal_attack_damage(self, target_id: int, amount: int, hits: int = 1,
                           is_battery: bool = False, is_precision: bool = False,
                           attacker_id: int = -1, source_card=None) -> int:
        hits = clamp_damage_hits(hits)
        if source_card is not None:
            self._clamp_card_layers(source_card)
        if not self._is_valid_player_id(target_id):
            return 0
        ps = self.players[target_id]
        if attacker_id < 0:
            attacker_id = self._last_attacker.get(target_id, -1)
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
                if not is_precision:
                    self.log_msg(f"{self.pn(target_id)}闪避了攻击")
                    continue
                precision_dodged = True
                self.log_msg(f"{self.pn(target_id)}的闪避被精准消耗")
            if ps.invincible and not immune:
                self.log_msg(f"{self.pn(target_id)}无敌，免疫伤害")
                continue
            if source_card is not None and self._has_equipment(target_id, 'Plank', 'jungle:plank'):
                try:
                    if int(getattr(source_card, 'cost_e', 0) or 0) <= 1:
                        plank_blocks_attack = True
                except Exception:
                    pass
            power = 0
            if source_card is not None:
                try:
                    power = max(0, int(getattr(source_card, 'power_value', 0) or 0))
                except Exception:
                    power = 0
            dmg = amount + int(math.ceil(power / max(1, int(hits or 1))))
            if self.halve_next_attack:
                dmg = math.ceil(dmg / 2)
            elif precision_dodged:
                dmg = math.ceil(dmg / 2)
            dmg = self._apply_corruption_multiplier_to_damage(dmg, log=False)
            dmg = self._apply_damage_dealt_equipment_multiplier(dmg, attacker_id)
            if plank_blocks_attack:
                dmg = 0
            if dmg > 0 and ps.nazar_active and not immune:
                original_dmg = dmg
                dmg = max(1, dmg - 9)
                if original_dmg >= 10:
                    ps.nazar_big_hits += 1
                    if ps.nazar_big_hits >= 2:
                        ps.nazar_active = False
                        ps.nazar_big_hits = 0
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
            ps.health -= dmg
            total_dealt += dmg
            if dmg > 0:
                self._last_positive_damage_hits[target_id] += 1
            self._record_damage(target_id, dmg, attacker_id)
            self.log_msg(f"{self.pn(target_id)}受到{dmg}点伤害（H={ps.health}）")
            self._run_v2_after_damage_hooks(damage_context, dmg)
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
                    target_equipment = [
                        (owner_id, eq)
                        for owner_id, owner_state in enumerate(self.players)
                        for eq in list(owner_state.equipment)
                        if getattr(eq, 'effect_target', owner_id) == target_id
                    ]
                    for owner_id, eq in target_equipment:
                        if self._has_card_event(eq.card_def, 'damage_taken') and self._run_card_event(
                            target_id,
                            eq.card_instance,
                            'damage_taken',
                            None,
                            {'source_id': attacker_id, 'target_id': target_id, 'damage': dmg},
                        ):
                            continue
                        if eq.def_id == 'Battery' and attacker_id >= 0:
                            dealt = self._deal_direct_damage(
                                attacker_id, 3, '电池电击', target_id,
                                damage_type=DAMAGE_TYPE_MAGIC,
                                damage_tag=DAMAGE_TAG_BATTERY,
                            )
                            if dealt > 0:
                                self.log_msg(f"{self.pn(target_id)}的电池效果：对{self.pn(attacker_id)}造成3电伤")
                            else:
                                self.log_msg(f"{self.pn(target_id)}的电池触发，但{self.pn(attacker_id)}未受到电伤")
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

    def _handle_draw_callback(self, player_id, card):
        """Called when a player draws a card. Triggers v2 after_draw event hooks."""
        if not (0 <= player_id < len(getattr(self, 'players', []))):
            return
        self._run_v2_event_hooks('after_draw', {
            'source_player': player_id,
            'target_player': player_id,
            'vars': {'player_id': player_id, 'drawn_card': card.def_id if card else ''},
        })
        self._apply_electric_web_draw_damage(player_id, 1)

    def use_trigger(self, player_id: int, equipment_instance_id: int, target_player_id: int = -1, ally_approved: bool = False) -> dict:
        target_player_id = self._normalize_player_id(target_player_id)
        if self.current_player != player_id and not self.is_ally(self.current_player, player_id):
            return {'success': False, 'error': '只能在己方回合触发装备'}
        ps = self.players[player_id]
        eq = ps.find_equipment(equipment_instance_id)
        if eq is None:
            return {'success': False, 'error': '装备不存在'}
        if 'self_only' in eq.card_instance.flags:
            target_player_id = player_id
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
        if not self._is_valid_effect_target(player_id, target_player_id):
            return {'success': False, 'error': '没有可选中的玩家'}
        if self._equipment_trigger_forbids_self_target(eq.card_def) and target_player_id == player_id:
            return {'success': False, 'error': '不能选择自己作为目标'}
        if target_player_id != player_id and self.is_ally(player_id, target_player_id) and not ally_approved:
            self.pending_ally_request = {
                'action': 'trigger',
                'player_id': player_id,
                'target_player_id': target_player_id,
                'equipment_instance_id': equipment_instance_id,
                'card': eq.card_instance.to_dict(),
            }
            return {'success': True, 'needs_ally_consent': True, 'card': eq.card_instance.to_dict(), 'target_player_id': target_player_id}
        max_uses = self._equipment_trigger_max_uses(eq)
        if max_uses > 0 and int(getattr(eq, 'uses_this_turn', 0)) >= max_uses:
            return {'success': False, 'error': f'该装备本回合最多触发{max_uses}次'}
        self._spend_resource(player_id, 'elixir', trigger_cost, eq.card_instance)
        self._spend_resource(player_id, 'magic', trigger_cost_m, eq.card_instance)
        eq.uses_this_turn = int(getattr(eq, 'uses_this_turn', 0)) + 1
        if has_mod_trigger and self._run_card_event(player_id, eq.card_instance, 'equipment_trigger', None,
                                                    {'source_id': player_id, 'target_id': target_player_id}):
            self._dispatch_card_event('equipment_triggered', player_id, eq.card_instance,
                                      target_id=target_player_id, equipment=eq, equipment_owner_id=player_id)
            self._check_game_over()
            return {'success': True}
        self._execute_trigger_effect(player_id, eq, target_player_id)
        self._dispatch_card_event('equipment_triggered', player_id, eq.card_instance,
                                  target_id=target_player_id, equipment=eq, equipment_owner_id=player_id)
        self._check_game_over()
        return {'success': True}

    def _resolve_target(self, player_id, target_str):
        context = getattr(self, '_active_effect_context', {}) or {}
        if isinstance(target_str, dict) and target_str.get('ref') == 'card_owner':
            target_card = self._resolve_card_ref(player_id, target_str.get('card'), None)
            owner_id, _, _ = self._find_card_location(target_card)
            return player_id if owner_id is None else owner_id
        if target_str in ('choice_target', 'selected_target', 'chosen_target'):
            target_id = self._selected_choice_target(player_id)
            return target_id if self._is_valid_effect_target(player_id, target_id) else -1
        if target_str == 'target':
            selected = self._selected_choice_target(-1)
            if self._is_valid_effect_target(player_id, selected):
                return selected
            target_id = self._normalize_player_id(context.get('target_id', player_id))
            return target_id if self._is_valid_effect_target(player_id, target_id) else -1
        if target_str == 'event_target':
            target_id = self._normalize_player_id(context.get('target_id', player_id))
            return target_id if self._is_valid_effect_target(player_id, target_id) else -1
        if target_str in ('event_source', 'source', 'last_actor', 'damage_source'):
            source_id = self._normalize_player_id(context.get('source_id', player_id))
            return source_id if self._is_valid_player_id(source_id) and self.players[source_id].health > 0 else -1
        if getattr(self, '_active_choice', None):
            selected = self._active_choice.get('target_player')
            if self._is_valid_effect_target(player_id, selected):
                if target_str in ('friendly', 'enemy'):
                    return selected
        if target_str is None or target_str == '' or target_str == 'self':
            return player_id if self._is_valid_effect_target(player_id, player_id) else -1
        if isinstance(target_str, int):
            return target_str if self._is_valid_effect_target(player_id, target_str) else -1
        if target_str == 'enemy':
            enemies = self.get_enemies(player_id)
            for enemy_id in enemies:
                if self._is_valid_enemy_target(player_id, enemy_id):
                    return enemy_id
            return -1
        if target_str == 'both':
            return -1
        if target_str == 'random':
            enemies = self.get_enemies(player_id)
            enemies = [enemy_id for enemy_id in enemies if self._is_valid_enemy_target(player_id, enemy_id)]
            return random.choice(enemies) if enemies else -1
        if target_str == 'teammate':
            teammate_id = self.get_teammate(player_id)
            return teammate_id if self._is_valid_effect_target(player_id, teammate_id) else -1
        return player_id if self._is_valid_effect_target(player_id, player_id) else -1

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

    def _resolve_targets(self, player_id, target_str):
        if isinstance(target_str, dict) and target_str.get('ref') == 'card_owner':
            tid = self._resolve_target(player_id, target_str)
            return [] if tid < 0 else [tid]
        if target_str in ('choice_target', 'selected_target', 'chosen_target', 'event_target', 'target', 'event_source', 'source', 'last_actor', 'damage_source'):
            tid = self._resolve_target(player_id, target_str)
            return [] if tid < 0 else [tid]
        if getattr(self, '_active_choice', None) and target_str in ('friendly', 'enemy'):
            selected = self._active_choice.get('target_player')
            if self._is_valid_effect_target(player_id, selected):
                return [selected]
        if target_str in ('all_players', 'all'):
            return list(range(len(self.players)))
        if target_str in ('both', 'random_side'):
            return [i for i, p in enumerate(self.players) if p.health > 0]
        if target_str in ('friendly', 'self', None, ''):
            return [player_id] if self._is_valid_effect_target(player_id, player_id) else []
        if target_str == 'teammate':
            mate = self.get_teammate(player_id)
            return [mate] if self._is_valid_effect_target(player_id, mate) else []
        if target_str == 'enemy':
            return [i for i in self.get_enemies(player_id) if self._is_valid_enemy_target(player_id, i)]
        if target_str == 'all_enemies':
            return [i for i in self.get_all_enemies(player_id) if self._is_valid_enemy_target(player_id, i)]
        if target_str == 'random_friendly':
            team = self.teams[self.team_of(player_id)]
            alive = [p for p in team if self.players[p].health > 0]
            return [random.choice(alive)] if alive else []
        if target_str == 'random_enemy':
            enemies = [i for i in self.get_enemies(player_id) if self._is_valid_enemy_target(player_id, i)]
            return [random.choice(enemies)] if enemies else []
        if target_str == 'random_player':
            alive = [i for i, p in enumerate(self.players) if p.health > 0]
            return [random.choice(alive)] if alive else []
        tid = self._resolve_target(player_id, target_str)
        if tid == -1:
            return []
        return [tid] if self._is_valid_effect_target(player_id, tid) else []
