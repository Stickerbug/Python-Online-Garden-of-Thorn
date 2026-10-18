# -*- coding: utf-8 -*-
"""双席合作编排层（2026-10-12，重写取代 v10 白名单执行器）。

主引擎（story_engine）经席位挂载后已是"多人就绪"的单人形状——本层只做
协调语义（都基于主引擎原动作，不改结算）：
- 同时英雄回合：combat 动作直接透传（ready 栅栏在引擎内）；
- 地图投票：各席投票，全员投完解析（一致=进入；分歧=按票数加权纯哈希）；
- 逐席赐福：各席各自选择（挂载各自结算），全员选完才进入地图；
- 逐席奖励：战斗胜利后复制一份奖励给每席，各自领取，全员完成才回地图；
- 房间/阶段屏障：rest/shop/event 各席各自 resolve，全员完成才推进。

协调状态挂在 state['coord']（不入 SHARED_COMBAT_KEYS，旅程级而非战斗级）。
"""

import copy
import hashlib
import math

from story_engine import (
    StoryActionError,
    _living_seats,
    _mount_seat,
    _reward_claims,
    _seat_count,
    apply_story_action,
)

# 直接透传给主引擎的动作（战斗与旅程杂项；战斗内 ready 栅栏由引擎管理）
_PASS_THROUGH = {
    'play_card', 'end_turn', 'use_enchantment_book', 'discard_enchantment_book',
    'resolve_card_choice', 'opening_redraw', 'resolve_deck_operation',
    'surrender', 'dev_set_values', 'dev_give_card', 'dev_spawn_boss',
    'dev_jump_node', 'restart_floor', 'resume_node', 'choose_stage',
}


def _seat_seed(seed, seat):
    """席位后缀种子：同一场旅程里各席的随机流相互独立（奖励/商店内容不同）。"""
    return f'{seed}:seat{seat}'


def _mount_coop_deck_ops(state, seat):
    """待选牌操作（裂解选牌/升级/删除/变化/附魔等窗口）按席位隔离。

    引擎的 state['pending_deck_operations'] 是旅程级共享队列——若不过滤，
    队友拾取"裂解"等遗物时另一席也会弹出选牌窗口（且能用自己 unrelated 的
    牌结算别人的操作）。完整队列保存在 coord['deck_ops_by_seat']，行动/读取
    前只把本席队列挂到 state 键上（引擎其余读写不用改）。"""
    coord = _coord(state)
    by_seat = coord.get('deck_ops_by_seat')
    if by_seat is None:
        by_seat = {}
        for op in list(state.get('pending_deck_operations') or []):
            key = str(op.get('seat', 0)) if isinstance(op, dict) else '0'
            by_seat.setdefault(key, []).append(op)
        coord['deck_ops_by_seat'] = by_seat
    state['pending_deck_operations'] = list(by_seat.get(str(seat)) or [])


def _sync_coop_deck_ops(state, seat):
    """行动后把本席队列（可能被结算移除/追加了新操作）写回 coord 账本。"""
    coord = _coord(state)
    by_seat = coord.get('deck_ops_by_seat')
    if by_seat is None:
        return
    by_seat[str(seat)] = list(state.get('pending_deck_operations') or [])


def mount_coop_deck_ops_view(state, seat):
    """读视角投影：只看本席的待选牌操作窗口（run GET/动作响应用）。

    对局中途升级（旧共享队列）：按操作上的 seat 标记初始化分组。"""
    if _seat_count(state) <= 1:
        return
    coord = _coord(state)
    if coord.get('deck_ops_by_seat') is None:
        _mount_coop_deck_ops(state, seat)
        return
    state['pending_deck_operations'] = copy.deepcopy(
        (coord.get('deck_ops_by_seat') or {}).get(str(seat)) or [])


def _differentiate_reward_per_seat(state, base, seat, seed):
    """胜利奖励的随机内容按席位重掷：金币区间/卡牌三选/遗物/附魔书。

    只重掷基础奖励里实际存在的字段（结构与其余字段原样保留）。
    调用前需已挂载对应席位（卡池/遗物池依赖该席的角色与遗物）。
    """
    from story_engine import (
        _boss_relic_choices, _difficulty, _random_enchantment_book,
        _random_relic, _reward_choices, _rng,
    )
    if not isinstance(base, dict):
        return copy.deepcopy(base)
    reward = copy.deepcopy(base)
    room_type = str(reward.get('room_type') or 'combat')
    seat_seed = _seat_seed(seed, seat)
    if isinstance(reward.get('gold'), int) and int(reward['gold']) > 0:
        # 乘区奖励（秘密通道×N等）保持原值只按比例换算；普通奖励按区间重掷。
        multiplied = str(reward.get('source') or '') in ('secret_passage', 'snatch') \
            or int(reward.get('round_total') or 0) >= 2
        rng = _rng(state, seat_seed, 'coop_seat_reward_gold')
        low, high = {'boss': (100, 120), 'elite': (25, 35)}.get(room_type, (10, 20))
        gold = rng.randint(low, high)
        if _difficulty(state) in ('hard', 'lunatic'):
            gold = math.floor(gold * 0.75)
        if multiplied:
            # 按原值与区间中点的比例换算，保持乘区量级
            gold = max(1, round(gold * int(reward['gold']) / max(1, (low + high) // 2)))
        reward['gold'] = gold
        if isinstance(reward.get('claims'), dict):
            reward['claims']['gold'] = gold <= 0
    if isinstance(reward.get('cards'), list):
        reward['cards'] = _reward_choices(state, seat_seed, room_type)
    base_relic = reward.get('relic')
    if isinstance(base_relic, list) and base_relic:
        reward['relic'] = _boss_relic_choices(state, seat_seed)
    elif base_relic:
        reward['relic'] = _random_relic(state, seat_seed)
    if reward.get('enchantment_book'):
        reward['enchantment_book'] = _random_enchantment_book(
            state, seat_seed, f'coop_seat_book:{room_type}')
    return reward


def _per_seat_rewards(state, base, seed, actor_seat=0):
    """按席位挂载并重掷各自奖励（不同角色/遗物的席位拿各自的卡池与遗物池）。

    结束后必须恢复行动席挂载：combat 为 None（奖励阶段）时 _mount_seat 只切
    state['player'] 别名，漏恢复会让后续单人结算写进最后一席的账户。
    """
    rewards = {}
    for seat in range(_seat_count(state)):
        _mount_seat(state, seat)
        rewards[str(seat)] = _differentiate_reward_per_seat(state, base, seat, seed)
    _mount_seat(state, actor_seat)
    return rewards


def _coord(state):
    coord = state.get('coord')
    if not isinstance(coord, dict):
        coord = {}
        state['coord'] = coord
    return coord


def _all_seats_acted(state, key):
    """key 集合覆盖全部存活席（战斗倒地席不阻塞推进）。"""
    seats = set(key)
    living = set(_living_seats(state)) or set(range(_seat_count(state)))
    return living <= seats


def _weighted_vote_pick(state, votes):
    """分歧投票：按票数加权的确定性哈希（不消耗 RNG 流）。"""
    tally = {}
    for node_id in votes.values():
        tally[node_id] = tally.get(node_id, 0) + 1
    namespace = f"coop_map_vote:{state.get('current_node_id') or 'start'}:{state.get('current_floor') or 1}"
    digest = hashlib.sha256(
        f"{state.get('journey_seed')}:{namespace}".encode('utf-8')
    ).hexdigest()
    roll = int(digest[:8], 16) % sum(tally.values())
    for node_id, weight in tally.items():
        if roll < weight:
            return node_id
        roll -= weight
    return next(iter(tally))


def _restore_pending_blessing(state):
    """赐福未全员完成：回到赐福阶段并重新锁回首层节点。"""
    state['phase'] = 'blessing'
    floors = (state.get('map') or {}).get('floors') or []
    if floors:
        for node in floors[0].get('nodes') or []:
            node['status'] = 'locked'
        floors[0]['nodes'][0]['status'] = 'available'


def apply_coop_action(source_state, seat, action_type, payload, seed):
    """双席协调入口：seat=行动席。返回 (state, events)。

    外层包一层"待选牌操作席位隔离"（裂解/升级/删除等窗口只属于行动席）：
    行动前只挂本席队列，行动后写回 coord 账本。"""
    state = source_state
    multi = _seat_count(state) > 1
    if multi:
        _mount_coop_deck_ops(state, seat)
    try:
        state, events = _apply_coop_action_impl(state, seat, action_type, payload, seed)
    finally:
        if multi:
            _sync_coop_deck_ops(state, seat)
    return state, events


def _apply_coop_action_impl(state, seat, action_type, payload, seed):
    action_type = str(action_type or '').strip().lower()
    payload = payload if isinstance(payload, dict) else {}
    seat = max(0, min(int(seat), _seat_count(state) - 1))
    coord = _coord(state)
    _mount_seat(state, seat)

    if action_type in _PASS_THROUGH:
        return apply_story_action(state, action_type, payload, seed)

    if action_type == 'start_journey':
        # 难度选择（任一席选定即全员生效）：共享参数由行动席结算一次，
        # 玩家层难度效果（困难/疯狂腐化卡、Boss Rush 特色卡组）逐席补齐。
        if state.get('phase') != 'journey_setup':
            raise StoryActionError('JOURNEY_ALREADY_STARTED', '旅程已经开始')
        state, events = apply_story_action(state, 'start_journey', payload, seed)
        difficulty = str(state.get('difficulty') or 'normal')
        journey_mode = str(state.get('journey_mode') or 'standard')
        if difficulty in ('hard', 'lunatic') or journey_mode == 'boss_rush':
            from story_engine import _gain_deck_card, _new_card
            for s in range(_seat_count(state)):
                if s == seat:
                    continue
                _mount_seat(state, s)
                player = state['player']
                if difficulty in ('hard', 'lunatic') and not any(
                    card.get('def_id') == 'corruption' for card in player.get('deck', [])
                ):
                    _gain_deck_card(state, 'corruption', events, source='difficulty')
                if journey_mode == 'boss_rush':
                    signature = [
                        card for card in player.get('deck', [])
                        if card.get('def_id') not in ('basic', 'rose')
                    ]
                    player['deck'] = signature or [_new_card(state, 'amulet')]
            _mount_seat(state, seat)
        return state, events

    if action_type == 'choose_easy_relic':
        # 简单难度天赋逐席独立选：首席选定后回到天赋阶段等其余席，全员完成才推进。
        options_before = list(state.get('easy_relic_options') or [])
        done = set(coord.get('easy_relic_done') or [])
        if seat in done:
            raise StoryActionError('EASY_RELIC_ALREADY_CHOSEN', '本席已选择天赋')
        state, events = apply_story_action(state, 'choose_easy_relic', payload, seed)
        coord = _coord(state)
        done = set(coord.get('easy_relic_done') or []) | {seat}
        if not _all_seats_acted(state, done):
            coord['easy_relic_done'] = sorted(done)
            state['phase'] = 'easy_relic'
            state['easy_relic_options'] = options_before
        else:
            coord['easy_relic_done'] = []
        return state, events

    if action_type == 'choose_blessing':
        # apply_story_action 会深拷贝 state：选项与协调簿需要在返回后的新 state 上读写。
        options_before = list(state.get('blessing_options') or [])
        done = set(coord.get('blessing_done') or [])
        if seat in done:
            raise StoryActionError('BLESSING_ALREADY_CHOSEN', '本席已选择赐福')
        state, events = apply_story_action(state, 'choose_blessing', payload, seed)
        coord = _coord(state)
        done = set(coord.get('blessing_done') or [])
        done.add(seat)
        coord['blessing_done'] = sorted(done)
        if not _all_seats_acted(state, done):
            # 其余席未选：回退到赐福阶段（本席的赐福已生效在各自 players 上），
            # 并恢复选项供其余席选择。
            _restore_pending_blessing(state)
            state['blessing_options'] = options_before
        else:
            # 全员完成：清完成名单（2026-10-14 修复——残留会让第二幕/Boss Rush
            # 下一块的赐福全员报 BLESSING_ALREADY_CHOSEN）。
            coord['blessing_done'] = []
        return state, events

    if action_type == 'enter_node':
        if state.get('phase') != 'map':
            raise StoryActionError('NOT_ON_MAP', '当前不在地图阶段')
        votes = dict(coord.get('votes') or {})
        votes[seat] = str(payload.get('node_id') or '')
        coord['votes'] = votes
        if not _all_seats_acted(state, votes):
            # 等其余席投票：本动作不产生事件，轮询可见 coord.votes。
            return state, [{'type': 'map_vote_cast', 'seat': seat,
                            'node_id': votes[seat]}]
        if len(set(votes.values())) != 1:
            # 2026-10-18 设计：投票不一致→重投（清空票箱，全员重选直到一致）。
            # vote_revote_count 递增供轮询方（先投票的玩家）感知并提示。
            coord['votes'] = {}
            coord['vote_revote_count'] = int(coord.get('vote_revote_count') or 0) + 1
            return state, [{'type': 'map_vote_revote', 'votes': votes}]
        winner = votes[seat]
        _mount_seat(state, 0)
        state, events = apply_story_action(
            state, 'enter_node', {'node_id': winner}, seed)
        coord = _coord(state)
        coord['votes'] = {}
        coord['room_done'] = []
        events.insert(0, {
            'type': 'map_vote_resolved',
            'votes': votes,
            'winner': winner,
        })
        return state, events

    if action_type == 'choose_reward':
        rewards_by_seat = coord.get('rewards_by_seat')
        if not rewards_by_seat:
            # 首次进入（或上一轮奖励完成后残留的空账本）：按席位重掷随机内容
            # （金币/卡牌/遗物/附魔书——两席不再拿同一份奖励）。2026-10-14 修复：
            # 此前只认 None——上一轮完成后残留空字典+旧完成名单，第二次奖励
            # 全员 REWARD_ALREADY_DONE 卡死。
            base = state.get('reward')
            rewards_by_seat = _per_seat_rewards(state, base, seed, actor_seat=seat)
            coord['rewards_by_seat'] = rewards_by_seat
            coord['reward_done'] = []
            state['reward'] = None
        coord = _coord(state)
        rewards_by_seat = coord.get('rewards_by_seat') or {}
        done = set(coord.get('reward_done') or [])
        if str(seat) in done:
            raise StoryActionError('REWARD_ALREADY_DONE', '本席已完成奖励选择')
        own = rewards_by_seat.get(str(seat))
        if not own:
            raise StoryActionError('NO_REWARD', '本席没有待选奖励')
        reward_type = str(payload.get('reward_type') or '').strip().lower()
        others_pending = any(key != str(seat) for key in rewards_by_seat)
        if reward_type in ('continue', 'leave') and others_pending:
            # 非最终席的离场/继续：只记账完成，不走单人结算——节点的完成与
            # 进层推进必须等全员结束由最终席触发恰好一次（2026-10-13 修复：
            # 此前"选了卡"即视为完成，节点推进从未发生，阶段卡死在 reward）。
            if reward_type == 'continue':
                claims = _reward_claims(own)
                if not all(claims.values()):
                    raise StoryActionError('REWARD_INCOMPLETE', '请先处理全部奖励')
            done.add(str(seat))
            coord['reward_done'] = sorted(done)
            rewards_by_seat.pop(str(seat), None)
            state['reward'] = None
            state['phase'] = 'reward'
            return state, [{'type': 'reward_seat_done', 'seat': seat}]
        state['reward'] = copy.deepcopy(own)
        state, events = apply_story_action(state, 'choose_reward', payload, seed)
        # apply 深拷贝了 state：到新 state 的协调簿上落账。
        coord = _coord(state)
        rewards_by_seat = coord.get('rewards_by_seat') or {}
        done = set(coord.get('reward_done') or [])
        remaining = state.get('reward')
        # 完成口径与单人一致：奖励被单人结算收尾（leave/continue 或
        # boss_rush 起始牌的自动收尾）才视为完成；仅领完所有项不算——
        # 客户端会显示「继续」，由 continue/leave 走上面的记账或最终结算。
        seat_finished = remaining is None or bool(
            isinstance(remaining, dict) and remaining.get('left')
        )
        if seat_finished:
            done.add(str(seat))
            coord['reward_done'] = sorted(done)
            rewards_by_seat.pop(str(seat), None)
        else:
            rewards_by_seat[str(seat)] = remaining
        state['reward'] = None
        if coord.get('rewards_by_seat'):
            # 还有席位没完成：保持奖励阶段。
            state['phase'] = 'reward'
        else:
            # 全员完成：彻底清账（空字典与完成名单残留会卡死下一轮奖励）。
            coord.pop('rewards_by_seat', None)
            coord['reward_done'] = []
        return state, events

    if action_type == 'resolve_room':
        # 逐席房间（2026-10-13 重写，同奖励模式）：首次交互把房间复制一份给
        # 每席，各自独立选择/购物/休息；某席的房间被单人结算消掉（事件/休息
        # 的一次性选择、商店离场）即该席完成；全员完成后节点推进恰好一次
        # （由最终席的单人结算完成）。修复：此前动作直通共享房间——第一人
        # 选择即消费房间（他人无法选择），第一人离场即全员被踢出。
        rooms = coord.get('rooms_by_seat')
        if not rooms:
            shared_room = state.get('room')
            if not isinstance(shared_room, dict) or not shared_room:
                raise StoryActionError('NO_ROOM', '当前没有待处理的房间')
            if shared_room.get('type') == 'shop':
                # 商店按席位重新生成（库存/价格各自随机；依赖各席角色与遗物）。
                # 结束后恢复行动席挂载（商店阶段 combat 为 None，漏恢复会让
                # 后续购买结算写进最后一席的账户）。
                from story_engine import _make_shop
                rooms = {}
                for s in range(_seat_count(state)):
                    _mount_seat(state, s)
                    rooms[str(s)] = _make_shop(state, _seat_seed(seed, s))
                _mount_seat(state, seat)
            else:
                rooms = {
                    str(s): copy.deepcopy(shared_room)
                    for s in range(_seat_count(state))
                }
            coord['rooms_by_seat'] = rooms
            coord['room_done'] = []
        coord = _coord(state)
        rooms = coord.get('rooms_by_seat') or {}
        done = set(coord.get('room_done') or [])
        if str(seat) in done:
            raise StoryActionError('ROOM_ALREADY_DONE', '本席已完成该房间')
        own = rooms.get(str(seat))
        if not isinstance(own, dict) or not own:
            raise StoryActionError('NO_ROOM', '本席没有待处理的房间')
        state['room'] = copy.deepcopy(own)
        # 席位后缀种子：房内随机（商店补货/抽奖机等）各席独立
        state, events = apply_story_action(state, 'resolve_room', payload, _seat_seed(seed, seat))
        coord = _coord(state)
        rooms = coord.get('rooms_by_seat') or {}
        done = set(coord.get('room_done') or [])
        remaining_room = state.get('room')
        seat_finished = (
            not isinstance(remaining_room, dict)
            or not remaining_room
            or str(state.get('phase') or '') != 'room'
        )
        if seat_finished:
            done.add(str(seat))
            coord['room_done'] = sorted(done)
            rooms.pop(str(seat), None)
        else:
            rooms[str(seat)] = remaining_room
        state['room'] = None
        if rooms:
            # 还有席位没完成：保持房间阶段（读视角由 mount_coop_room_view 投影）。
            state['phase'] = 'room'
            return state, events
        coord.pop('rooms_by_seat', None)
        coord['room_done'] = []
        return state, events

    # 其余未知动作：透传（单人语义，按行动席挂载）。
    return apply_story_action(state, action_type, payload, seed)


def mount_coop_room_view(state, seat):
    """观看席视角投影：房间协调期间把本席的房间副本挂到 state['room']。

    只在读路径（GET / 动作响应投影）调用；行动路径 resolve_room 结算前会用
    本席副本覆盖 state['room']，结算后按剩余情况落账并清空。"""
    if state.get('phase') != 'room':
        return
    own = (state.get('coord') or {}).get('rooms_by_seat', {}).get(str(seat))
    if isinstance(own, dict) and own:
        state['room'] = copy.deepcopy(own)


def mount_coop_reward_view(state, seat):
    """观看席视角投影：奖励协调期间把本席待选奖励挂到 state['reward'] 供前端渲染。

    只在读路径（GET / 动作响应投影）调用。行动路径不受影响：choose_reward
    结算前会用本席副本覆盖 state['reward']，结算后按剩余情况落账并清空。
    每次读都归一化：本席有待选则投影，没有则清空——否则上一个观看席的
    投影副本会残留在共享 state 上，泄漏给等待席。"""
    if state.get('phase') != 'reward':
        return
    rewards_by_seat = (state.get('coord') or {}).get('rewards_by_seat')
    if rewards_by_seat is None:
        # 协调未开始：共享奖励仍挂载（战斗胜利后、任一席首次选择前），两席均可见。
        return
    own = rewards_by_seat.get(str(seat))
    state['reward'] = copy.deepcopy(own) if own is not None else None


def coop_coord_summary(state):
    """给前端的协调态摘要（投票进度/各席完成度）。"""
    coord = state.get('coord') or {}
    return {
        'votes': coord.get('votes') or {},
        'vote_revote_count': int(coord.get('vote_revote_count') or 0),
        'blessing_done': coord.get('blessing_done') or [],
        'reward_pending_seats': sorted(
            int(s) for s in (coord.get('rewards_by_seat') or {}).keys()
        ),
        'room_done': coord.get('room_done') or [],
        'room_pending_seats': sorted(
            int(s) for s in (coord.get('rooms_by_seat') or {}).keys()
        ),
    }
