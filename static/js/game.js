const DEBUG_CLIENT_LOGS = false;
const debugLog = (...args) => {
    if (DEBUG_CLIENT_LOGS) console.log(...args);
};
const GTN_BETA_MODE = !!window.__GTN_BETA_MODE__;
const GTN_BETA_STORAGE_EXACT_KEYS = new Set([
    'gtn_theme',
    'gtn_lang',
    'gtn_ui_style',
    'gtn_ui_style_v2_migrated',
    'gtn_hidden_features_enabled',
    'gtn_show_english_card_names',
    'gtn_show_card_images',
    'gtn_skin_config',
    'gtn_server',
    'gtn_disabled_mods',
    'gtn_community_mods',
    'gtn_settings_mod_tab',
    'gtn_solo_decks',
    'gtn_seen_intro',
    'preferred_mode',
]);
const GTN_BETA_STORAGE_PREFIXES = [
    'gtn_settings_mod_detail_',
    'gtn_cards_cache_',
    'gtn_opening_events_cache_',
];
function gtnBetaStorageKey(key) {
    if (!GTN_BETA_MODE) return key;
    const raw = String(key || '');
    if (!raw) return key;
    if (raw === 'preferred_mode') return 'gtn_beta_preferred_mode';
    if (GTN_BETA_STORAGE_EXACT_KEYS.has(raw)) return `gtn_beta_${raw.slice(4)}`;
    for (const prefix of GTN_BETA_STORAGE_PREFIXES) {
        if (raw.startsWith(prefix)) return `gtn_beta_${raw.slice(4)}`;
    }
    return key;
}
(() => {
    if (!GTN_BETA_MODE || !window.localStorage) return;
    const proto = Object.getPrototypeOf(window.localStorage);
    if (!proto || proto.__gtnBetaStoragePatched) return;
    const rawGet = proto.getItem;
    const rawSet = proto.setItem;
    const rawRemove = proto.removeItem;
    proto.getItem = function(key) { return rawGet.call(this, gtnBetaStorageKey(key)); };
    proto.setItem = function(key, value) { return rawSet.call(this, gtnBetaStorageKey(key), value); };
    proto.removeItem = function(key) { return rawRemove.call(this, gtnBetaStorageKey(key)); };
    Object.defineProperty(proto, '__gtnBetaStoragePatched', { value: true });
})();

const I18N = {
    en: {
        round: 'Round', your_turn: 'Your Turn', opponent_turn: "Opponent's Turn", you: 'You', opponent: 'Opponent',
        draw_phase: 'Draw Phase', game_over: 'Game Over', invite: 'Invite', accept: 'Accept', decline: 'Decline',
        return_lobby: 'Return to Lobby', draft_phase: 'Draft Phase', draft_reroll: 'Refresh', draft_selected: 'Selected',
        select_event: 'Select Event', waiting_opponent: 'Waiting for opponent', play_card: 'Play', end_turn: 'End Turn',
        surrender: 'Surrender', view_deck: 'View Deck', counter: 'Counter', no_counter: 'Pass', waiting_response: 'Waiting for response',
        victory: 'Victory', defeat: 'Defeat', draw: 'Draw', rematch: 'Rematch', connecting: 'Connecting...', disconnected: 'Disconnected',
        login_failed: 'Login Failed', nickname: 'Nickname', enter_lobby: 'Enter Lobby', online_players: 'Online Players',
        no_other_players: 'No other players', invite_sent: 'Invite sent', invite_received: 'Invite received', invite_message: 'invites you to a match',
        invite_declined: 'Invite declined', ongoing_games: 'Ongoing Games', spectate: 'Spectate', draft_info: 'Draft', draft_complete: 'Draft Complete',
        draft_waiting: 'Waiting for opponent to finish drafting', draft_cost: 'Cost', select_this_event: 'Select This Event',
        event_selected: 'Event selected: {0}', event_waiting: 'Waiting for opponent to select an event', event_reroll: 'Refresh', status_event_select: 'Selecting Event', status_drafting: 'Drafting', status_sub_choice: 'Event Setup', status_ready: 'Ready', drag_to_play: 'Drag to Play',
        drag_to_play_full: 'Drag here to play', tap_play_hint: 'Tap a card, then confirm to play', confirm_play: 'Play {0}', cancel_play: 'Cancel',
        classic_select_card: 'Choose a card',
        prediction_target: 'Target',
        prediction_self: 'Self',
        classic_play_center: 'Click the stage to play',
        classic_target_enemy: 'Click opponent to play',
        classic_target_self: 'Click yourself to play',
        classic_equip_stage: 'Click your side to equip',
        cannot_play: 'Cannot Play', enemy_attack: 'Enemy Attack', enemy_skill: 'Enemy Skill', enemy_destroy_equip: ', destroys equipment',
        use_card: 'Use', insufficient_resources: 'Insufficient resources', choose_attack_for: 'Choose an attack for {0}', choose_equip_for: 'Choose equipment',
        choose_discard_for: 'Choose a discard for {0}', choose_from_deck_for: 'Choose from deck', choose_from_discard_for: 'Choose from discard for {0}',
        choose_hand_for: 'Choose from hand for {0}', choose_from_enemy_hand_for: 'Choose from enemy hand', choose_attack_group_for: 'Choose attack group for {0}',
        no_attack_cards: 'No attack cards', no_enemy_equipment: 'No enemy equipment', no_enemy_hand: 'No enemy hand', deck_empty: 'Deck empty',
        no_matching_cards: 'No matching cards', no_cards_in_hand: 'No cards in hand',
        discard_empty: 'Discard pile empty', no_same_attack: 'No matching attack cards', confirm_surrender: 'Surrender?', request_rematch: 'Request Rematch',
        opponent_rematch: 'Opponent requests rematch', rematch_sent: 'Rematch request sent', rematch_waiting: 'Waiting for opponent', rematch_agreed: 'Rematch accepted',
        rematch_progress: 'Rematch ({0}/{1})',
        rematch_unavailable_returned: 'A player returned to lobby',
        player_returned_lobby: '{0} returned to lobby',
        agree_rematch: 'Accept Rematch', you_win: 'You Win!', you_lose: 'You Lose!', you_draw: 'Draw!', send: 'Send', cancel: 'Cancel', confirm: 'Confirm', ok: 'OK', close: 'Close', notice: 'Notice',
        opponent_disconnected: 'Opponent disconnected', opponent_reconnected: 'Opponent reconnected', reconnect_title: 'Reconnect', reconnect_prompt: 'Reconnect to the previous match?',
        reconnecting: 'Reconnecting...', reconnect_timeout: 'Reconnect timed out', mod_mismatch_title: 'Mod Mismatch', mod_mismatch_msg: 'Mods do not match, cannot start the match',
        switch_perspective: 'Switch Perspective', leave_spectate: 'Leave Spectate', switch_to_perspective: 'Switch to {0}', battle_log: 'Battle Log',
        equip_info: '{0} ({1} turns)', equip_corruption: '[Corrupted]', equip_trigger_cost: '{0} Trigger: {1}E', status_poison: 'Poison', status_fire: 'Burn', status_toxic: 'Toxic',
        status_triangle: 'Triangle', status_dodge: 'Dodge', status_nazar: 'Nazar', status_equip_protect: 'Equip Protect', status_invincible: 'Invincible', status_immune: 'Status Immune', status_stunned: 'Stunned',
        status_attack_blocked: 'Attack Blocked', status_attack_only: 'Attack Only', status_untargetable: 'Untargetable', status_bandage: 'Bandage', status_sponge: 'Sponge', status_shovel: 'Shovel', status_sluggish: 'Sluggish', status_overload: 'Overload', status_foresight: 'Foresight', status_fracture: 'Fracture', status_stagnation: 'Stagnation', status_blind: 'Blind', status_heal_block: 'Heal Block', status_weakness: 'Weakness', status_bleed: 'Bleed', status_fragment: 'Fragment', status_fragment_stacks: 'Fragment',
        flag_precision: 'Precision', flag_exile: 'Exile', flag_non_stackable: 'Non-stack', flag_indestructible: 'Indestructible', flag_sprout: 'Sprout', flag_symbiosis: 'Symbiosis', flag_attract: 'Attract', flag_void: 'Void', flag_self_only: 'No target', flag_uncancellable: 'Uncancellable', flag_infinite_exclude: 'Removed from Infinite Fire', flag_rebound: 'Rebound', flag_copy: 'Copy', flag_unique: 'Unique', flag_swift: 'Swift', flag_stealth: 'Stealth', flag_revealed: 'Revealed', flag_team_limited: 'Team Limited', flag_team_unique: 'Team Unique', flag_power: 'Power', flag_magic_swift: 'Magic Swift',
        tag_precision: 'Precision', tag_exile: 'Exile', tag_non_stackable: 'Non-stack', tag_indestructible: 'Indestructible', tag_sprout: 'Sprout', tag_symbiosis: 'Symbiosis', tag_attract: 'Attract', tag_void: 'Void', tag_self_only: 'No target', tag_uncancellable: 'Uncancellable', tag_infinite_exclude: 'Removed from Infinite Fire', tag_rebound: 'Rebound', tag_copy: 'Copy', tag_unique: 'Unique', tag_swift: 'Swift', tag_stealth: 'Stealth', tag_revealed: 'Revealed', tag_team_limited: 'Team Limited', tag_team_unique: 'Team Unique', tag_power: 'Power', tag_magic_swift: 'Magic Swift',
        gallery_title: 'Compendium', gallery_cards: 'Cards', gallery_tags: 'Tags', gallery_events: 'Opening Events', gallery_search: 'Search', gallery_no_items: 'No entries.', gallery_cards_with_tag: 'Cards with this tag', gallery_card_count: '{0} cards',
        gallery_type: 'Type', gallery_cost: 'Cost', gallery_tags_label: 'Tags', gallery_description: 'Description', gallery_effect: 'Effect', gallery_trigger: 'Trigger',
        choose_convert_count: 'Choose convert count', choose_magic_card_n: 'Choose magic card #{0}', choose_source_card_n: 'Choose source card #{0}', choose_light_cards: 'Choose Light cards', choose_yggdrasil_card: 'Choose Yggdrasil card',
        convert_label: 'Convert', convert_per_type: 'Max {0} per type', selected_count: 'Selected {0}/{1}', max_selection_warning: 'Cannot exceed {0}', deck_total: 'Deck: {0} cards', view_deck_title: 'View Deck',
        foresight_replace_title: 'Foresight', foresight_replace_desc: 'Discard up to {0} cards from your hand, then draw that many cards', foresight_replace_confirm: 'Replace',
        hand_deck_info_opp: 'Hand: {0} Deck: {1}', hand_deck_discard_info: 'Hand: {0} Deck: {1} Discard: {2}', round_status: 'Round {0} - {1}', server_broadcast: 'Server: {0}', error_msg: 'Error: {0}',
        lobby_status: 'Lobby - {0}', no_counter_countdown: 'No Counter ({0})', select_event_desc: 'Select an opening event', start_draft: 'Start Draft', opponent_selected: 'Opponent selected', opponent_selecting: 'Opponent selecting...',
        card_type_thorn: 'Thorn', card_type_bloom: 'Bloom', card_type_root: 'Root', card_type_guard: 'Guard', fusion_layer: 'Fusion', fission_layer: 'Fission',
        settings_title: 'Settings', settings_appearance: 'Appearance', settings_theme: 'Theme', settings_lang: 'Language', settings_mods: 'Mods', settings_theme_light: 'Light', settings_theme_dark: 'Dark',
        no_games: 'No ongoing games', back_to_home: 'Back to Home', settings_btn: 'Settings', settings_server: 'Server', settings_server_addr: 'Address', not_your_turn: 'Not your turn',
        counter_insufficient: 'Tip: counter cards are not affordable', default_status: 'Garden of Thorn', game_loading: 'Loading...', server_no_response: 'Server is not responding. Check the connection or refresh.',
        spectator_prefix: 'Spectate', lobby_title: 'Lobby', online_count: 'Online: {0}', chat_title: 'Chat', solo_training: 'Solo Training', load_last: 'Load Last', save_decks: 'Save Decks', start_training: 'Start Training', clear_deck: 'Clear Deck',
        solo_deck_a: 'Your Deck', solo_deck_b: 'Opponent Deck', search_cards: 'Search cards', pause_edit: 'Pause & Edit', set_next_draw: 'Set Next Draw', solo_saved: 'Training decks saved',
        solo_need_15: 'Both decks must contain exactly 15 cards', solo_event_a: 'Your opening event', solo_event_b: 'Opponent opening event', no_event: 'None', edit_tags: 'Edit Tags',
        login_need_nickname: 'Please enter a nickname', login_name_too_long: 'Nickname too long (max 8 CJK or 16 Latin chars)', login_name_not_numbers: 'Nickname cannot be only numbers',
        login_name_not_symbols: 'Nickname cannot be only symbols', login_name_no_repeat_symbols: '- and _ cannot appear consecutively',
        operation_failed: 'Operation failed', server_not_connected: 'Not connected to server', no_mod_files: 'No mod files found', load_success: 'Loaded', load_failed: 'Load failed', save_success: 'Saved', save_failed: 'Save failed: {0}',
        solo_invalid_card: 'The mod supporting this card is missing or invalid',
        solo_invalid_deck_cards: 'The deck contains invalid cards. Enable the required mod or remove those cards first.',
        json_valid: 'Valid JSON', json_invalid: 'Invalid JSON: {0}', init_scripts: 'Initializing scripts...', init_theme_lang: 'Applying theme and language...', init_fonts: 'Loading fonts...', init_fonts_done: 'Fonts loaded',
        init_bindings: 'Binding UI events...', init_done: 'Loaded', next_draw_count: 'Set Next Draw (count)', next_draw_pick: 'Set Next Draw ({0}/{1})',
        login_invalid_nickname: 'Invalid nickname. Use 1-16 display-width characters; avoid pure numbers, pure symbols, or repeated -/_.', login_nickname_exists: 'Nickname already exists',
        training_start: 'Solo training starts. First player: {0}.', training_set_draw: 'Training: {0} sets next draw to {1}',
        hand_deck_zero_opp: 'Hand:0 Deck:0',
        hand_deck_zero_you: 'Hand:0 Deck:0 Discard:0',
        rotate_hint_sub: 'Rotate to Landscape',
        error_game_over: 'The game is over',
        error_waiting_counter: 'Waiting for the opponent to respond',
        error_card_not_in_hand: 'Card is not in hand',
        error_remove_from_hand_failed: 'Failed to remove card from hand',
        error_no_pending_response: 'No pending response',
        error_no_pending_choice: 'No pending choice',
        error_choice_cancelled: 'Choice cancelled',
        error_not_your_turn: 'Not your turn',
        error_equipment_missing: 'Equipment does not exist',
        error_equipment_no_trigger: 'This equipment has no trigger effect',
        error_equipment_turn_needed: 'This equipment must stay equipped for one turn before triggering',
        error_not_enough_e: 'Not enough E',
        error_target_invalid: 'Invalid target',
        error_action_blocked: 'You cannot use cards right now',
        error_attack_blocked: 'You cannot use Thorn cards this turn',
        error_attack_only: 'Only Thorn cards can be used this turn',
        error_waiting_response_ui: 'Waiting for response',
        app_subtitle: 'LAN card battle',
        nickname_placeholder: 'Enter nickname',
        message_placeholder: 'Type a message...',
        server_placeholder: 'Leave empty for default server',
        server_hint: 'Default server: {0} (leave empty to use default)',
        init_cards_mods: 'Loading cards and mods (/api/cards)...',
        init_opening_events: 'Loading opening events (/api/opening-events)...',
        mod_editor: 'Mod Editor',
        mod_editor_placeholder: 'Paste or edit mod JSON here...',
        load_mod: 'Load Mod',
        save: 'Save',
        validate_json: 'Validate JSON',
        rotate_prompt: 'Please play in landscape mode',
        continue_enter: 'Continue',
        mod_default_name: 'Mod {0}',
        mod_selection_force_vanilla: 'Enabled the vanilla card mod because the selected mods must contain at least one Thorn, Bloom, Root, and Guard card.',
    mode_select: 'Mode', mode_1v1: '1v1', mode_2v2: '2v2', mode_urf: 'Infinite Fire',
        form_team: 'Form Team', leave_team: 'Leave Team', invite_team: 'Invite Team',
        team_invite_msg: '{0} invites you to form a team', team_formed_msg: 'Team formed with {0}',
        team_disbanded_msg: 'Team disbanded', team_match_invite_msg: 'Team {0} challenges your team',
        team_match_declined_msg: 'Team match declined', team_declined_msg: 'Team invite declined',
        select_target: 'Select Target', enemy_label: 'Enemy', ally_label: 'Ally',
        teammate: 'Teammate', team_chat: 'Team Chat', team_chat_placeholder: 'Message teammates...',
        trigger_on_ally_turn: 'Trigger equipment (ally turn)', player_dead: 'Defeated',
        choose_target: 'Choose Target', ally_consent_title: 'Teammate Card Use', ally_consent_msg: '{0} wants to use {1} on you',
        ally_accept_countdown: 'Accept ({0})', ally_decline: 'Decline',
        mode_switch_confirm: 'Switching mode will leave your current team.\nContinue?',
        waiting_for_team: 'Waiting for another team...',
        all_players_draft_status: 'Draft Status',
        urf_replace: 'Replace Card', urf_sell: 'Sell Equipment'
    }
};
I18N.zh = { ...I18N.en,
    round: '回合', your_turn: '你的回合', opponent_turn: '对方回合', you: '你', opponent: '对手',
    draw_phase: '抽牌阶段', game_over: '游戏结束', invite: '邀请', accept: '接受', decline: '拒绝', return_lobby: '返回大厅',
    draft_phase: '选牌阶段', draft_reroll: '刷新', draft_selected: '已选择', select_event: '选择配装倾向', waiting_opponent: '等待对方',
    play_card: '打出', end_turn: '结束回合', surrender: '投降', view_deck: '查看牌堆', counter: '反制', no_counter: '不反制', waiting_response: '等待响应',
    victory: '胜利', defeat: '失败', draw: '平局', rematch: '再来一局', connecting: '连接中...', disconnected: '已断开连接',
    login_failed: '登录失败', nickname: '昵称', enter_lobby: '进入大厅', online_players: '在线玩家', no_other_players: '暂无其他玩家',
    invite_sent: '邀请已发送', invite_received: '收到邀请', invite_message: '邀请你进行对战', invite_declined: '邀请被拒绝',
    ongoing_games: '进行中的对局', spectate: '观战', draft_info: '选牌', draft_complete: '选牌完成', draft_waiting: '等待对方完成选牌',
    draft_cost: '费用', select_this_event: '选择此事件', event_selected: '已选择事件：{0}', event_waiting: '等待对方选择事件', event_reroll: '刷新', status_event_select: '选择配装', status_drafting: '选牌中', status_sub_choice: '配装处理', status_ready: '已完成',
    drag_to_play: '拖动打出', cannot_play: '无法打出', enemy_attack: '敌方攻击', enemy_skill: '敌方技能', enemy_destroy_equip: '，摧毁装备',
    drag_to_play_full: '拖动到此处以出牌', tap_play_hint: '点击手牌后确认出牌', confirm_play: '打出 {0}', cancel_play: '取消出牌',
    classic_select_card: '选择一张手牌',
    prediction_target: '对目标',
    prediction_self: '对自己',
    classic_play_center: '点击战场打出',
    classic_target_enemy: '点击对手使用',
    classic_target_self: '点击自己使用',
    classic_equip_stage: '点击己方装备',
    use_card: '使用', insufficient_resources: '资源不足', choose_attack_for: '为 {0} 选择攻击牌', choose_equip_for: '选择装备牌',
    choose_discard_for: '为 {0} 选择弃牌', choose_from_deck_for: '从牌堆选择', choose_from_discard_for: '为 {0} 从弃牌堆选择', choose_hand_for: '为 {0} 从手牌选择',
    choose_from_enemy_hand_for: '从敌方手牌选择', choose_attack_group_for: '为 {0} 选择攻击组', no_attack_cards: '没有攻击牌', no_enemy_equipment: '对方没有装备',
    no_enemy_hand: '对方没有手牌', deck_empty: '牌堆为空', no_matching_cards: '没有符合条件的牌', no_cards_in_hand: '手牌为空', discard_empty: '弃牌堆为空', no_same_attack: '没有同名攻击牌',
    confirm_surrender: '确认投降？', request_rematch: '请求再来一局', opponent_rematch: '对方请求再来一局', rematch_sent: '已发送再来一局请求',
    rematch_waiting: '等待对方', rematch_agreed: '对方已接受', agree_rematch: '接受再来一局', rematch_progress: '再来一局({0}/{1})', you_win: '你赢了！', you_lose: '你输了！', you_draw: '平局！',
    rematch_unavailable_returned: '有玩家已返回大厅', player_returned_lobby: '{0}已返回大厅',
    send: '发送', cancel: '取消', confirm: '确认', ok: '确定', close: '关闭', notice: '提示', opponent_disconnected: '对手已断开连接', opponent_reconnected: '对手已重新连接',
    reconnect_title: '重连', reconnect_prompt: '是否重连到上一局对战？', reconnecting: '重连中...', reconnect_timeout: '重连超时',
    mod_mismatch_title: '模组不匹配', mod_mismatch_msg: '模组不一致，无法开始对局', switch_perspective: '切换视角', leave_spectate: '退出观战', switch_to_perspective: '切换到 {0}',
    battle_log: '战斗日志', equip_info: '{0}（{1}回合）', equip_corruption: '[已腐化]', equip_trigger_cost: '{0} 触发：{1}E',
    status_poison: '中毒', status_fire: '灼烧', status_toxic: '淬毒', status_triangle: '三角形', status_dodge: '闪避', status_nazar: '邪眼',
    status_equip_protect: '装备保护', status_invincible: '无敌', status_immune: '状态免疫', status_stunned: '眩晕', status_attack_blocked: '禁攻', status_attack_only: '仅攻击',
    status_untargetable: '不可选中', status_bandage: '绷带', status_sponge: '海绵', status_shovel: '铲子',
    status_sluggish: '迟缓', status_overload: '超载', status_foresight: '预知', status_fracture: '破损', status_stagnation: '滞留', status_blind: '失明', status_heal_block: '禁疗', status_weakness: '虚弱', status_bleed: '流血', status_fragment: '碎片', status_fragment_stacks: '碎片',
    flag_precision: '精准', flag_exile: '放逐', flag_non_stackable: '不可叠加', flag_indestructible: '不可摧毁', flag_sprout: '萌芽', flag_symbiosis: '共生', flag_attract: '吸引', flag_void: '虚无', flag_self_only: '不选择目标', flag_uncancellable: '不可取消', flag_infinite_exclude: '无限火力移除', flag_rebound: '回转', flag_copy: '副本', flag_unique: '唯一', flag_swift: '迅捷', flag_stealth: '隐匿', flag_revealed: '被揭示', flag_team_limited: '队伍限定', flag_team_unique: '队伍独一', flag_power: '威力', flag_magic_swift: '魔力迅捷',
    choose_convert_count: '选择转化数量', choose_magic_card_n: '选择第 {0} 张魔法牌', choose_source_card_n: '选择第 {0} 张源牌', choose_light_cards: '选择 Light 牌', choose_yggdrasil_card: '选择世界树之叶牌',
    convert_label: '转化', convert_per_type: '每种最多 {0} 张', selected_count: '已选择 {0}/{1}', max_selection_warning: '不能超过 {0}',
    foresight_replace_title: '预知', foresight_replace_desc: '选择最多{0}张手牌丢弃，然后抽对应张牌', foresight_replace_confirm: '替换',
    deck_total: '牌堆：{0} 张', view_deck_title: '查看牌堆', hand_deck_info_opp: '手牌：{0} 牌堆：{1}', hand_deck_discard_info: '手牌：{0} 牌堆：{1} 弃牌：{2}',
    round_status: '第 {0} 回合 - {1}', server_broadcast: '系统：{0}', error_msg: '错误：{0}', lobby_status: '大厅 - {0}', no_counter_countdown: '不反制（{0}）',
    select_event_desc: '选择一个配装倾向', start_draft: '开始选牌', opponent_selected: '对方已选择', opponent_selecting: '对方选择中...',
    settings_title: '设置', settings_appearance: '外观', settings_theme: '主题', settings_lang: '语言', settings_mods: '模组', settings_theme_light: '明亮', settings_theme_dark: '黑暗',
    no_games: '暂无进行中的对局', back_to_home: '返回主页', settings_btn: '设置', settings_server: '服务器', settings_server_addr: '地址', not_your_turn: '还没轮到你',
    counter_insufficient: '提示：当前没有可支付的反制牌', default_status: 'Garden of Thorn', game_loading: '加载中...', server_no_response: '服务器没有响应，请检查连接或刷新页面。',
    spectator_prefix: '观战', lobby_title: '大厅', online_count: '在线：{0}', chat_title: '聊天',
    lobby_phase_event_select: '配装选择', lobby_phase_draw: '抽牌',
    solo_training: '单人训练场', load_last: '载入上次', save_decks: '保存牌组', start_training: '开始训练', clear_deck: '清空牌组', solo_deck_a: '你的牌组', solo_deck_b: '对方牌组',
    search_cards: '搜索卡牌', pause_edit: '暂停并编辑', set_next_draw: '设置下次抽牌', solo_saved: '训练牌组已保存', solo_need_15: '双方牌组都必须正好为 15 张',
    solo_event_a: '你的配装倾向', solo_event_b: '对方配装倾向', no_event: '无', edit_tags: '编辑标签',
    login_need_nickname: '请输入昵称', login_name_too_long: '昵称过长（最多 8 个中文或 16 个拉丁字符）', login_name_not_numbers: '昵称不能全为数字', login_name_not_symbols: '昵称不能全为符号', login_name_no_repeat_symbols: '- 和 _ 不能连续出现',
        operation_failed: '操作失败', server_not_connected: '未连接到服务器', no_mod_files: '未找到模组文件', load_success: '加载成功', load_failed: '加载失败', save_success: '保存成功', save_failed: '保存失败：{0}',
        solo_invalid_card: '支持此卡的模组不存在或已失效',
        solo_invalid_deck_cards: '牌组中存在失效卡。请启用对应模组或移除失效卡后再开始训练。',
    json_valid: 'JSON 格式正确', json_invalid: 'JSON 格式错误：{0}', init_scripts: '初始化脚本...', init_theme_lang: '应用主题和语言...', init_fonts: '加载字体文件...', init_fonts_done: '字体加载完成', init_bindings: '绑定界面事件...', init_done: '加载完成',
    next_draw_count: '设置下次抽牌（张数）', next_draw_pick: '设置下次抽牌（{0}/{1}）',
    login_invalid_nickname: '昵称无效：长度需在 1-16 显示宽度之间，且不能为纯数字、纯符号或连续 -/_。', login_nickname_exists: '昵称已存在',
    training_start: '单人训练场开始！{0}先手。', training_set_draw: '训练场：{0} 设置下次抽牌：{1}',
    hand_deck_zero_opp: '手牌:0 牌堆:0',
    hand_deck_zero_you: '手牌:0 牌堆:0 弃牌:0',
    rotate_hint_sub: '请旋转至横屏',
    error_game_over: '游戏已结束',
    error_waiting_counter: '等待对手反制响应',
    error_card_not_in_hand: '卡牌不在手中',
    error_remove_from_hand_failed: '移出手牌失败',
    error_no_pending_response: '没有待响应的操作',
    error_no_pending_choice: '没有待选择操作',
    error_choice_cancelled: '选择已取消',
    error_not_your_turn: '不是你的回合',
    error_equipment_missing: '装备不存在',
    error_equipment_no_trigger: '该装备没有触发效果',
    error_equipment_turn_needed: '装备需要装备一回合后才能触发',
    error_not_enough_e: '能量不足',
    error_target_invalid: '目标无效',
    error_action_blocked: '当前无法使用卡牌',
    error_attack_blocked: '本回合无法使用攻击牌',
    error_attack_only: '本回合只能使用攻击牌',
    error_waiting_response_ui: '等待响应',
    tag_precision: '精准', tag_exile: '放逐', tag_non_stackable: '不可叠加', tag_indestructible: '不可摧毁', tag_sprout: '萌芽', tag_symbiosis: '共生', tag_attract: '吸引', tag_void: '虚无', tag_self_only: '不选择目标', tag_uncancellable: '不可取消', tag_infinite_exclude: '无限火力移除', tag_rebound: '回转', tag_copy: '副本', tag_unique: '唯一', tag_swift: '迅捷', tag_stealth: '隐匿', tag_revealed: '被揭示', tag_team_limited: '队伍限定', tag_team_unique: '队伍独一', tag_power: '威力', tag_magic_swift: '魔力迅捷',
    gallery_title: '图鉴', gallery_cards: '卡牌', gallery_tags: '标签', gallery_events: '配装倾向', gallery_statuses: '状态', gallery_search: '搜索', gallery_no_items: '暂无条目。', gallery_cards_with_tag: '拥有此标签的卡牌', gallery_card_count: '{0} 张卡牌',
    gallery_type: '类型', gallery_cost: '费用', gallery_tags_label: '标签', gallery_description: '描述', gallery_effect: '效果', gallery_trigger: '触发',
    mode_select: '模式', mode_1v1: '1v1', mode_2v2: '2v2', mode_urf: '无限火力',
    form_team: '组队', leave_team: '离开队伍', invite_team: '邀请队伍',
    team_invite_msg: '{0} 邀请你组队', team_formed_msg: '已与 {0} 组队',
    team_disbanded_msg: '队伍已解散', team_match_invite_msg: '队伍 {0} 向你们发起挑战',
    team_match_declined_msg: '队伍挑战被拒绝', team_declined_msg: '组队邀请被拒绝',
    select_target: '选择目标', enemy_label: '敌方', ally_label: '友方',
    teammate: '队友', team_chat: '队内聊天', team_chat_placeholder: '发送队内消息...',
    trigger_on_ally_turn: '触发装备（队友回合）', player_dead: '已阵亡',
    choose_target: '选择目标', ally_consent_title: '队友用牌确认', ally_consent_msg: '{0} 想对你使用 {1}',
    ally_accept_countdown: '同意（{0}）', ally_decline: '不同意',
    mode_switch_confirm: '切换模式将离开当前队伍，\n是否确认？',
    waiting_for_team: '等待另一支队伍...',
    all_players_draft_status: '选牌状态',
    urf_replace: '替换手牌', urf_sell: '售卖装备',
    fusion_layer: '聚变', fission_layer: '裂变',
    app_subtitle: '在线联机卡牌对战',
    nickname_placeholder: '输入昵称',
    message_placeholder: '输入消息...',
    server_placeholder: '留空使用默认服务器',
    server_hint: '默认服务器：{0}（留空则使用默认服务器）',
    init_cards_mods: '加载卡牌与模组（/api/cards）...',
    init_opening_events: '加载配装倾向（/api/opening-events）...',
    mod_editor: '模组编辑器',
    mod_editor_placeholder: '在此粘贴或编辑模组 JSON...',
    load_mod: '加载模组',
    save: '保存',
    validate_json: '验证 JSON',
    rotate_prompt: '请横屏游玩',
    continue_enter: '继续进入',
    mod_default_name: '模组 {0}',
    mod_selection_force_vanilla: '已强制启用原版卡牌模组：已选模组必须至少包含攻击、技能、装备、反制各1张。'
};
I18N.fr = { ...I18N.en,
    round: 'Tour', your_turn: 'Votre Tour', opponent_turn: "Tour de l'adversaire", you: 'Vous', opponent: 'Adversaire',
    draw_phase: 'Phase de Pioche', game_over: 'Fin de Partie', invite: 'Inviter', accept: 'Accepter', decline: 'Refuser', return_lobby: 'Retour au Salon',
    draft_phase: 'Phase de Draft', draft_reroll: 'Relancer', draft_selected: 'Sélectionné', select_event: "Choisir Événement", waiting_opponent: "En attente de l'adversaire",
    play_card: 'Jouer', end_turn: 'Fin du Tour', surrender: 'Abandonner', view_deck: 'Voir le Deck', counter: 'Contre', no_counter: 'Pas de Contre', waiting_response: 'En attente de réponse',
    victory: 'Victoire', defeat: 'Défaite', draw: 'Égalité', rematch: 'Rejouer', connecting: 'Connexion...', disconnected: 'Déconnecté',
    login_failed: 'Échec de connexion', nickname: 'Pseudo', enter_lobby: 'Entrer dans le Salon', online_players: 'Joueurs en ligne', no_other_players: 'Aucun autre joueur',
    invite_sent: 'Invitation envoyée', invite_received: 'Invitation reçue', invite_message: 'vous invite à jouer', invite_declined: 'Invitation refusée',
    ongoing_games: 'Parties en cours', spectate: 'Observer', draft_info: 'Draft', draft_complete: 'Draft terminé', draft_waiting: "En attente de l'adversaire",
    draft_cost: 'Coût', select_this_event: 'Choisir cet événement', event_selected: 'Événement choisi', event_waiting: "En attente du choix de l'adversaire",
    drag_to_play: 'Glisser pour jouer', cannot_play: 'Impossible de jouer',
    enemy_attack: 'Attaque ennemie', enemy_skill: 'Compétence ennemie', enemy_destroy_equip: "Destruction d'équipement ennemi",
    use_card: 'Utiliser', insufficient_resources: 'Ressources insuffisantes', choose_attack_for: 'Choisir une attaque pour', choose_equip_for: 'Choisir un équipement',
    choose_discard_for: 'Choisir une carte à défausser', choose_from_deck_for: 'Choisir depuis le deck', choose_from_discard_for: 'Choisir depuis la défausse', choose_hand_for: 'Choisir depuis la main',
    choose_from_enemy_hand_for: 'Choisir depuis la main ennemie', choose_attack_group_for: "Choisir un groupe d'attaque",
    no_attack_cards: "Aucune carte d'attaque", no_enemy_equipment: 'Aucun équipement ennemi', no_enemy_hand: 'Aucune main ennemie', deck_empty: 'Deck vide', discard_empty: 'Défausse vide',
    no_same_attack: "Aucune carte d'attaque identique", confirm_surrender: "Confirmer l'abandon ?", request_rematch: 'Demander une revanche',
    opponent_rematch: "L'adversaire demande une revanche", rematch_sent: 'Demande de revanche envoyée', rematch_waiting: "En attente de l'adversaire", rematch_agreed: 'Revanche acceptée',
    rematch_progress: 'Rejouer ({0}/{1})',
    agree_rematch: 'Accepter la revanche', you_win: 'Victoire !', you_lose: 'Défaite !', you_draw: 'Égalité !',
    send: 'Envoyer', cancel: 'Annuler', ok: 'OK', close: 'Fermer', notice: 'Notice',
    opponent_disconnected: 'Adversaire déconnecté', opponent_reconnected: 'Adversaire reconnecté',
    reconnect_title: 'Reconnexion', reconnect_prompt: 'Se reconnecter à la partie précédente ?', reconnecting: 'Reconnexion...', reconnect_timeout: 'Délai de reconnexion écoulé',
    mod_mismatch_title: 'Mods incompatibles', mod_mismatch_msg: 'Les mods ne correspondent pas, impossible de commencer',
    switch_perspective: 'Changer de perspective', leave_spectate: "Quitter l'observation", switch_to_perspective: 'Passer à la perspective de {0}',
    battle_log: 'Journal de combat', equip_info: '{0}({1} tours)', equip_corruption: '[Corrompu]', equip_trigger_cost: '{0} Déclencher:{1}E',
    status_poison: 'Poison', status_fire: 'Brûlure', status_toxic: 'Toxique', status_triangle: 'Triangle', status_dodge: 'Esquive',
    status_nazar: 'Nazar', status_equip_protect: 'Prot. Équip.', status_invincible: 'Invincible', status_immune: 'Immunité statut', status_stunned: 'Étourdi', status_attack_blocked: 'Atq bloquée', status_attack_only: 'Atq seule',
    status_untargetable: 'Non ciblable', status_bandage: 'Bandage', status_sponge: 'Éponge', status_shovel: 'Pelle',
    status_sluggish: 'Lenteur', status_overload: 'Surcharge', status_foresight: 'Prévoyance', status_fracture: 'Fracture', status_stagnation: 'Stagnation', status_blind: 'Cécité', status_heal_block: 'Anti-soin', status_weakness: 'Faiblesse', status_bleed: 'Saignement', status_fragment: 'Fragment', status_fragment_stacks: 'Fragment',
    flag_precision: 'Précision', flag_exile: 'Exil', flag_non_stackable: 'Non-cumul', flag_indestructible: 'Indestructible', flag_sprout: 'Pousse', flag_symbiosis: 'Symbiose', flag_copy: 'Copie', flag_unique: 'Unique', flag_swift: 'Rapidité', flag_stealth: 'Furtif', flag_revealed: 'Révélé',
    choose_convert_count: 'Nombre de conversions', choose_magic_card_n: 'Carte magie n°{0}', choose_source_card_n: 'Carte source n°{0}',
    choose_light_cards: 'Cartes de conversion Lumière', choose_yggdrasil_card: 'Carte Arbre-Monde', convert_label: 'Convertir', convert_per_type: 'Max {0} par type',
    selected_count: 'Sélectionné {0}/{1}', max_selection_warning: 'Ne peut pas dépasser {0}', deck_total: 'Deck : {0} cartes', view_deck_title: 'Voir le deck',
    hand_deck_info_opp: 'Main:{0} Deck:{1}', hand_deck_discard_info: 'Main:{0} Deck:{1} Défausse:{2}', round_status: 'Tour {0} - {1}',
    server_broadcast: 'Serveur : {0}', error_msg: 'Erreur : {0}', lobby_status: 'Salon - {0}', no_counter_countdown: 'Pas de contre({0})',
    select_event_desc: "Choisir un événement de départ", opponent_selected: 'Adversaire a choisi', opponent_selecting: 'Adversaire choisit...',
    card_type_thorn: 'Thorn', card_type_bloom: 'Bloom', card_type_root: 'Root', card_type_guard: 'Guard',
    settings_title: 'Paramètres', settings_appearance: 'Apparence', settings_theme: 'Thème', settings_lang: 'Langue', settings_mods: 'Mods', settings_theme_light: 'Clair', settings_theme_dark: 'Sombre',
    no_games: 'Aucune partie en cours', back_to_home: "Retour à l'accueil", settings_btn: 'Paramètres', settings_server: 'Serveur', settings_server_addr: 'Adresse',
    not_your_turn: "Ce n'est pas votre tour", counter_insufficient: 'Conseil : Ressources insuffisantes pour les cartes de contre', default_status: 'Garden of Thorn',
    game_loading: 'Chargement...', server_no_response: 'Le serveur ne répond pas. Vérifiez votre connexion.',
    spectator_prefix: 'Spectateur', lobby_title: 'Salon', online_count: 'En ligne: {0}', chat_title: 'Chat',
    solo_training: 'Entraînement solo', load_last: 'Charger', save_decks: 'Sauver decks', start_training: 'Commencer', clear_deck: 'Vider deck',
    solo_deck_a: 'Votre deck', solo_deck_b: 'Deck adverse', search_cards: 'Chercher cartes', pause_edit: 'Pause édition',
    set_next_draw: 'Fixer prochaine pioche', solo_saved: 'Decks sauvegardés', solo_need_15: 'Les deux decks doivent avoir exactement 15 cartes',
    solo_event_a: 'Événement de départ', solo_event_b: 'Événement adverse', no_event: 'Aucun',
    edit_tags: 'Modifier tags', tag_precision: 'Précision', tag_exile: 'Exil', tag_non_stackable: 'Non-cumul',
    tag_indestructible: 'Indestructible', tag_sprout: 'Pousse', tag_symbiosis: 'Symbiose', tag_attract: 'Attraction', tag_void: 'Vide', tag_self_only: 'Sans cible', tag_uncancellable: 'Non annulable', tag_rebound: 'Retour', tag_copy: 'Copie', tag_unique: 'Unique', tag_swift: 'Rapidité', tag_stealth: 'Furtif', tag_revealed: 'Révélé', tag_infinite_exclude: 'Retiré d’Infinite Fire',
    fusion_layer: 'Fusion', fission_layer: 'Fission',
    app_subtitle: 'Combat de cartes en réseau local',
    nickname_placeholder: 'Saisir un pseudo',
    message_placeholder: 'Saisir un message...',
    hand_deck_zero_opp: 'Main:0 Deck:0',
    hand_deck_zero_you: 'Main:0 Deck:0 Défausse:0',
    rotate_hint_sub: 'Passez en mode paysage',
    server_placeholder: 'Laisser vide pour le serveur par défaut',
    server_hint: 'Serveur par défaut : {0} (laisser vide pour l’utiliser)',
    init_cards_mods: 'Chargement des cartes et mods (/api/cards)...',
    init_opening_events: 'Chargement des événements initiaux (/api/opening-events)...',
    mod_editor: 'Éditeur de mod',
    mod_editor_placeholder: 'Collez ou modifiez le JSON du mod ici...',
    load_mod: 'Charger le mod',
    save: 'Enregistrer',
    validate_json: 'Valider le JSON',
    rotate_prompt: 'Veuillez jouer en mode paysage',
    continue_enter: 'Continuer',
    mod_default_name: 'Mod {0}'
};
I18N.pt = { ...I18N.en,
    round: 'Turno', your_turn: 'Seu Turno', opponent_turn: 'Turno do Oponente', you: 'Você', opponent: 'Oponente',
    draw_phase: 'Fase de Compra', game_over: 'Fim de Jogo', invite: 'Convidar', accept: 'Aceitar', decline: 'Recusar', return_lobby: 'Voltar ao Lobby',
    draft_phase: 'Fase de Draft', draft_reroll: 'Rerrolar', draft_selected: 'Selecionado', select_event: 'Escolher Evento', waiting_opponent: 'Aguardando Oponente',
    play_card: 'Jogar', end_turn: 'Finalizar Turno', surrender: 'Render-se', view_deck: 'Ver Deck', counter: 'Contra-atacar', no_counter: 'Sem Contra', waiting_response: 'Aguardando resposta',
    victory: 'Vitória', defeat: 'Derrota', draw: 'Empate', rematch: 'Jogar Novamente', connecting: 'Conectando...', disconnected: 'Desconectado',
    login_failed: 'Falha no login', nickname: 'Apelido', enter_lobby: 'Entrar no Lobby', online_players: 'Jogadores Online', no_other_players: 'Nenhum outro jogador',
    invite_sent: 'Convite Enviado', invite_received: 'Convite Recebido', invite_message: 'convida você para uma partida', invite_declined: 'Convite Recusado',
    ongoing_games: 'Partidas em Andamento', spectate: 'Assistir', draft_info: 'Draft', draft_complete: 'Draft Completo', draft_waiting: 'Aguardando oponente terminar o draft',
    draft_cost: 'Custo', select_this_event: 'Selecionar Este Evento', event_selected: 'Evento Selecionado', event_waiting: 'Aguardando oponente selecionar evento',
    drag_to_play: 'Arraste para Jogar', cannot_play: 'Não Pode Jogar',
    enemy_attack: 'Ataque Inimigo', enemy_skill: 'Habilidade Inimiga', enemy_destroy_equip: 'Destruir Equipamento Inimigo',
    use_card: 'Usar', insufficient_resources: 'Recursos Insuficientes', choose_attack_for: 'Escolher ataque para', choose_equip_for: 'Escolher equipamento',
    choose_discard_for: 'Escolher descarte', choose_from_deck_for: 'Escolher do deck', choose_from_discard_for: 'Escolher da pilha de descarte', choose_hand_for: 'Escolher da mão',
    choose_from_enemy_hand_for: 'Escolher da mão inimiga', choose_attack_group_for: 'Escolher grupo de ataque',
    no_attack_cards: 'Sem cartas de ataque', no_enemy_equipment: 'Sem equipamento inimigo', no_enemy_hand: 'Sem mão inimiga', deck_empty: 'Deck vazio', discard_empty: 'Pilha de descarte vazia',
    no_same_attack: 'Sem cartas de ataque iguais', confirm_surrender: 'Confirmar rendição?', request_rematch: 'Pedir revanche',
    opponent_rematch: 'Oponente pede revanche', rematch_sent: 'Pedido de revanche enviado', rematch_waiting: 'Aguardando oponente', rematch_agreed: 'Revanche aceita',
    rematch_progress: 'Jogar novamente ({0}/{1})',
    agree_rematch: 'Aceitar revanche', you_win: 'Vitória!', you_lose: 'Derrota!', you_draw: 'Empate!',
    send: 'Enviar', cancel: 'Cancelar', ok: 'OK', close: 'Fechar', notice: 'Aviso',
    opponent_disconnected: 'Oponente desconectou', opponent_reconnected: 'Oponente reconectou',
    reconnect_title: 'Reconectar', reconnect_prompt: 'Reconectar à partida anterior?', reconnecting: 'Reconectando...', reconnect_timeout: 'Tempo de reconexão esgotado',
    mod_mismatch_title: 'Mods incompatíveis', mod_mismatch_msg: 'Mods inconsistentes, não é possível iniciar a partida',
    switch_perspective: 'Trocar Perspectiva', leave_spectate: 'Sair da Observação', switch_to_perspective: 'Trocar para perspectiva de {0}',
    battle_log: 'Registro de Batalha', equip_info: '{0}({1} turnos)', equip_corruption: '[Corrompido]', equip_trigger_cost: '{0} Ativar:{1}E',
    status_poison: 'Veneno', status_fire: 'Queima', status_toxic: 'Tóxico', status_triangle: 'Triângulo', status_dodge: 'Esquiva',
    status_nazar: 'Nazar', status_equip_protect: 'Prot. Equip.', status_invincible: 'Invencível', status_immune: 'Imune a status', status_stunned: 'Atordoado', status_attack_blocked: 'Atq Bloqueado', status_attack_only: 'Só Atq',
    status_untargetable: 'Inalvejável', status_bandage: 'Bandagem', status_sponge: 'Esponja', status_shovel: 'Pá',
    status_sluggish: 'Letargia', status_overload: 'Sobrecarga', status_foresight: 'Previsão', status_fracture: 'Fratura', status_stagnation: 'Estagnação', status_blind: 'Cegueira', status_heal_block: 'Anti-cura', status_weakness: 'Fraqueza', status_bleed: 'Sangramento', status_fragment: 'Fragmento', status_fragment_stacks: 'Fragmento',
    flag_precision: 'Precisão', flag_exile: 'Exílio', flag_non_stackable: 'Não-acumulável', flag_indestructible: 'Indestrutível', flag_sprout: 'Brotar', flag_symbiosis: 'Simbiose', flag_copy: 'Cópia', flag_unique: 'Único', flag_swift: 'Rapidez', flag_stealth: 'Furtivo', flag_revealed: 'Revelado',
    choose_convert_count: 'Escolher quantidade de conversão', choose_magic_card_n: 'Carta mágica n°{0}', choose_source_card_n: 'Carta fonte n°{0}',
    choose_light_cards: 'Cartas de conversão Luz', choose_yggdrasil_card: 'Carta Árvore-Mundo', convert_label: 'Converter', convert_per_type: 'Máx {0} por tipo',
    selected_count: 'Selecionado {0}/{1}', max_selection_warning: 'Não pode exceder {0}', deck_total: 'Deck: {0} cartas', view_deck_title: 'Ver Deck',
    hand_deck_info_opp: 'Mão:{0} Deck:{1}', hand_deck_discard_info: 'Mão:{0} Deck:{1} Descarte:{2}', round_status: 'Turno {0} - {1}',
    server_broadcast: 'Servidor: {0}', error_msg: 'Erro: {0}', lobby_status: 'Lobby - {0}', no_counter_countdown: 'Sem Contra({0})',
    select_event_desc: 'Escolha um evento inicial', opponent_selected: 'Oponente Selecionou', opponent_selecting: 'Oponente Selecionando...',
    card_type_thorn: 'Thorn', card_type_bloom: 'Bloom', card_type_root: 'Root', card_type_guard: 'Guard',
    settings_title: 'Configurações', settings_appearance: 'Aparência', settings_theme: 'Tema', settings_lang: 'Idioma', settings_mods: 'Mods', settings_theme_light: 'Claro', settings_theme_dark: 'Escuro',
    no_games: 'Nenhuma partida em andamento', back_to_home: 'Voltar ao Início', settings_btn: 'Configurações', settings_server: 'Servidor', settings_server_addr: 'Endereço',
    not_your_turn: 'Não é seu turno', counter_insufficient: 'Dica: Recursos insuficientes para cartas de contra-ataque', default_status: 'Garden of Thorn',
    game_loading: 'Carregando...', server_no_response: 'Servidor sem resposta. Verifique sua conexão.',
    spectator_prefix: 'Espectar', lobby_title: 'Lobby', online_count: 'Online: {0}', chat_title: 'Chat',
    solo_training: 'Treino Solo', load_last: 'Carregar Último', save_decks: 'Salvar Decks', start_training: 'Iniciar Treino', clear_deck: 'Limpar deck',
    solo_deck_a: 'Seu Deck', solo_deck_b: 'Deck Oponente', search_cards: 'Buscar cartas', pause_edit: 'Pausar e Editar',
    set_next_draw: 'Definir Próxima Compra', solo_saved: 'Decks salvos', solo_need_15: 'Ambos os decks devem ter exatamente 15 cartas',
    solo_event_a: 'Evento inicial', solo_event_b: 'Evento do oponente', no_event: 'Nenhum',
    edit_tags: 'Editar tags', tag_precision: 'Precisão', tag_exile: 'Exílio', tag_non_stackable: 'Não acumula',
    tag_indestructible: 'Indestrutível', tag_sprout: 'Broto', tag_symbiosis: 'Simbiose', tag_attract: 'Atrair', tag_void: 'Vazio', tag_self_only: 'Sem alvo', tag_uncancellable: 'Não cancelável', tag_copy: 'Cópia', tag_unique: 'Único', tag_swift: 'Rapidez', tag_stealth: 'Furtivo', tag_revealed: 'Revelado', tag_infinite_exclude: 'Removido do Infinite Fire', tag_rebound: 'Retorno',
    fusion_layer: 'Fusão', fission_layer: 'Fissão',
    app_subtitle: 'Batalha de cartas em rede local',
    nickname_placeholder: 'Digite um apelido',
    message_placeholder: 'Digite uma mensagem...',
    hand_deck_zero_opp: 'Mão:0 Deck:0',
    hand_deck_zero_you: 'Mão:0 Deck:0 Descarte:0',
    rotate_hint_sub: 'Gire para o modo paisagem',
    server_placeholder: 'Deixe vazio para o servidor padrão',
    server_hint: 'Servidor padrão: {0} (deixe vazio para usar o padrão)',
    init_cards_mods: 'Carregando cartas e mods (/api/cards)...',
    init_opening_events: 'Carregando eventos iniciais (/api/opening-events)...',
    mod_editor: 'Editor de Mod',
    mod_editor_placeholder: 'Cole ou edite o JSON do mod aqui...',
    load_mod: 'Carregar Mod',
    save: 'Salvar',
    validate_json: 'Validar JSON',
    rotate_prompt: 'Jogue em modo paisagem',
    continue_enter: 'Continuar',
    mod_default_name: 'Mod {0}'
};
I18N.ja = { ...I18N.en,
    round: 'ターン', your_turn: 'あなたのターン', opponent_turn: '相手のターン', you: 'あなた', opponent: '相手',
    draw_phase: 'ドローフェイズ', game_over: 'ゲーム終了', invite: '招待', accept: '承諾', decline: '拒否', return_lobby: 'ロビーに戻る',
    draft_phase: 'ドラフトフェイズ', draft_reroll: 'リロール', draft_selected: '選択済み', select_event: 'イベント選択', waiting_opponent: '相手を待っています',
    play_card: 'プレイ', end_turn: 'ターン終了', surrender: '降参', view_deck: 'デッキ確認', counter: 'カウンター', no_counter: 'カウンターなし', waiting_response: '応答待ち',
    victory: '勝利', defeat: '敗北', draw: '引き分け', rematch: '再戦', connecting: '接続中...', disconnected: '切断されました',
    login_failed: 'ログイン失敗', nickname: 'ニックネーム', enter_lobby: 'ロビーに入る', online_players: 'オンラインプレイヤー', no_other_players: '他のプレイヤーはいません',
    invite_sent: '招待を送信しました', invite_received: '招待を受信しました', invite_message: 'が対戦に招待しています', invite_declined: '招待が拒否されました',
    ongoing_games: '進行中の対戦', spectate: '観戦', draft_info: 'ドラフト', draft_complete: 'ドラフト完了', draft_waiting: '相手のドラフト完了を待っています',
    draft_cost: 'コスト', select_this_event: 'このイベントを選択', event_selected: 'イベント選択済み', event_waiting: '相手のイベント選択を待っています',
    drag_to_play: 'ドラッグしてプレイ', cannot_play: 'プレイ不可',
    enemy_attack: '敵の攻撃', enemy_skill: '敵のスキル', enemy_destroy_equip: '敵の装備破壊',
    use_card: '使用', insufficient_resources: 'リソース不足', choose_attack_for: '攻撃カードを選択', choose_equip_for: '装備を選択',
    choose_discard_for: '捨て札を選択', choose_from_deck_for: 'デッキから選択', choose_from_discard_for: '捨て札から選択', choose_hand_for: '手札から選択',
    choose_from_enemy_hand_for: '相手の手札から選択', choose_attack_group_for: '攻撃グループを選択',
    no_attack_cards: '攻撃カードなし', no_enemy_equipment: '敵の装備なし', no_enemy_hand: '敵の手札なし', deck_empty: 'デッキ空', discard_empty: '捨て札空',
    no_same_attack: '同じ攻撃カードなし', confirm_surrender: '降参しますか？', request_rematch: '再戦をリクエスト',
    opponent_rematch: '相手が再戦をリクエストしています', rematch_sent: '再戦リクエスト送信済み', rematch_waiting: '相手の確認待ち', rematch_agreed: '再戦が合意されました',
    rematch_progress: '再戦({0}/{1})',
    agree_rematch: '再戦に同意', you_win: '勝利！', you_lose: '敗北！', you_draw: '引き分け！',
    send: '送信', cancel: 'キャンセル', ok: 'OK', close: '閉じる', notice: 'お知らせ',
    opponent_disconnected: '相手が切断しました', opponent_reconnected: '相手が再接続しました',
    reconnect_title: '再接続', reconnect_prompt: '前の対戦に再接続しますか？', reconnecting: '再接続中...', reconnect_timeout: '再接続タイムアウト',
    mod_mismatch_title: 'Mod不一致', mod_mismatch_msg: 'Modが一致しません。対戦を開始できません',
    switch_perspective: '視点切替', leave_spectate: '観戦終了', switch_to_perspective: '{0}の視点に切替',
    battle_log: 'バトルログ', equip_info: '{0}({1}ターン)', equip_corruption: '[腐敗]', equip_trigger_cost: '{0} 発動:{1}E',
    status_poison: '毒', status_fire: '火傷', status_toxic: '猛毒', status_triangle: '三角形', status_dodge: '回避',
    status_nazar: 'ナザール', status_equip_protect: '装備保護', status_invincible: '無敵', status_immune: '状態免疫', status_stunned: 'スタン', status_attack_blocked: '攻撃封印', status_attack_only: '攻撃のみ',
    status_untargetable: '対象不可', status_bandage: '包帯', status_sponge: 'スポンジ', status_shovel: 'シャベル',
    status_sluggish: '遅鈍', status_overload: '過負荷', status_foresight: '予知', status_fracture: '破損', status_stagnation: '滞留', status_blind: '失明', status_heal_block: '治療封じ', status_weakness: '虚弱', status_bleed: '出血', status_fragment: '破片', status_fragment_stacks: '破片',
    flag_precision: '精密', flag_exile: '追放', flag_non_stackable: '非スタック', flag_indestructible: '破壊不可', flag_sprout: '発芽', flag_symbiosis: '共生', flag_copy: '複製', flag_unique: '唯一', flag_swift: '迅捷', flag_stealth: '隠密', flag_revealed: '公開',
    choose_convert_count: '変換回数を選択', choose_magic_card_n: 'マジックカード第{0}枚', choose_source_card_n: 'ソースカード第{0}枚',
    choose_light_cards: '光変換カードを選択', choose_yggdrasil_card: '世界樹変換カードを選択', convert_label: '変換', convert_per_type: 'タイプごとに最大{0}枚',
    selected_count: '選択済み {0}/{1}', max_selection_warning: '{0}を超えることはできません', deck_total: 'デッキ: {0}枚', view_deck_title: 'デッキ確認',
    hand_deck_info_opp: '手札:{0} デッキ:{1}', hand_deck_discard_info: '手札:{0} デッキ:{1} 捨て札:{2}', round_status: '第{0}ターン - {1}',
    server_broadcast: 'サーバー: {0}', error_msg: 'エラー: {0}', lobby_status: 'ロビー - {0}', no_counter_countdown: 'カウンターなし({0})',
    select_event_desc: 'オープニングイベントを選択', opponent_selected: '相手が選択済み', opponent_selecting: '相手が選択中...',
    card_type_thorn: 'Thorn', card_type_bloom: 'Bloom', card_type_root: 'Root', card_type_guard: 'Guard',
    settings_title: '設定', settings_appearance: '外観', settings_theme: 'テーマ', settings_lang: '言語', settings_mods: 'Mod', settings_theme_light: 'ライト', settings_theme_dark: 'ダーク',
    no_games: '進行中の対戦なし', back_to_home: 'ホームに戻る', settings_btn: '設定', settings_server: 'サーバー', settings_server_addr: 'アドレス',
    not_your_turn: 'あなたのターンではありません', counter_insufficient: 'ヒント：カウンターに必要なリソースが不足しています', default_status: 'Garden of Thorn',
    game_loading: '読み込み中...', server_no_response: 'サーバーが応答しません。接続を確認してください。',
    spectator_prefix: '観戦', lobby_title: 'ロビー', online_count: 'オンライン: {0}', chat_title: 'チャット',
    solo_training: 'ソロ練習場', load_last: '前回を読み込む', save_decks: 'デッキ保存', start_training: '開始', clear_deck: 'デッキを空にする',
    solo_deck_a: '自分のデッキ', solo_deck_b: '相手デッキ', search_cards: 'カード検索', pause_edit: '中断して編集',
    set_next_draw: '次のドロー設定', solo_saved: '練習デッキを保存しました', solo_need_15: '両方のデッキは15枚ちょうど必要です',
    solo_event_a: '自分の開局イベント', solo_event_b: '相手の開局イベント', no_event: 'なし',
    edit_tags: 'タグ編集', tag_precision: '精密', tag_exile: '追放', tag_non_stackable: '非重複',
    tag_indestructible: '破壊不可', tag_sprout: '萌芽', tag_symbiosis: '共生', tag_attract: '誘引', tag_void: '虚無', tag_self_only: '対象選択なし', tag_uncancellable: 'キャンセル不可', tag_copy: '複製', tag_unique: '唯一', tag_swift: '迅捷', tag_stealth: '隠密', tag_revealed: '公開', tag_infinite_exclude: 'Infinite Fireから削除', tag_rebound: '回転',
    fusion_layer: '融合', fission_layer: '分裂',
    app_subtitle: 'LANカード対戦',
    nickname_placeholder: 'ニックネームを入力',
    message_placeholder: 'メッセージを入力...',
    hand_deck_zero_opp: '手札:0 デッキ:0',
    hand_deck_zero_you: '手札:0 デッキ:0 捨て札:0',
    rotate_hint_sub: '横向きにしてください',
    server_placeholder: '空欄なら既定サーバーを使用',
    server_hint: '既定サーバー：{0}（空欄なら既定を使用）',
    init_cards_mods: 'カードとModを読み込み中（/api/cards）...',
    init_opening_events: '開始イベントを読み込み中（/api/opening-events）...',
    mod_editor: 'Modエディター',
    mod_editor_placeholder: 'ここにMod JSONを貼り付けるか編集...',
    load_mod: 'Modを読み込む',
    save: '保存',
    validate_json: 'JSONを検証',
    rotate_prompt: '横向きでプレイしてください',
    continue_enter: '続ける',
    mod_default_name: 'Mod {0}'
};
const GAME_TITLE = 'Garden of Thorn 荆棘花园';
Object.values(I18N).forEach(dict => {
    dict.default_status = GAME_TITLE;
    dict.tutorial_hint_play_fusioned = dict.tutorial_hint_play_fusioned || '聚变后的攻击牌已经准备好了。当前能量足够，把它打出看看强化后的伤害。';
    dict.target_pick_hint = dict.target_pick_hint || 'Click a highlighted player area.';
    dict.waiting_opponent_counter = dict.waiting_opponent_counter || dict.waiting_response || 'Waiting for response';
    dict.tutorial_victory_message = dict.tutorial_victory_message || '恭喜你，成功完成了新手教程！\n希望你能在 Garden of Thorn 中玩得开心！';
    dict.tutorial_defeat_message = dict.tutorial_defeat_message || '哎呀，对局失败了。没关系，祝你在接下来的游戏中越打越顺！';
    dict.tutorial_retry = dict.tutorial_retry || '重试教程';
    dict.tutorial_start = dict.tutorial_start || '新手引导';
    dict.tutorial_skip = dict.tutorial_skip || '跳过引导';
    dict.tutorial_intro = dict.tutorial_intro || '现在，让我们开始新手教程吧！';
    dict.tutorial_hint_play = dict.tutorial_hint_play || '先打出一张 Thorn 攻击牌，观察对手 H 的变化。';
    dict.tutorial_hint_end = dict.tutorial_hint_end || '行动完成后，点击“结束回合”，把节奏交给对手。';
    dict.tutorial_hint_enemy = dict.tutorial_hint_enemy || '现在观察对手行动。注意战斗日志和 H/E/M 的变化。';
    dict.tutorial_hint_deck = dict.tutorial_hint_deck || '先看看抽牌堆：点击“查看牌堆”，了解接下来可能抽到什么。';
    dict.tutorial_hint_continue = dict.tutorial_hint_continue || '继续出牌并结束回合。稍后你会抽到反制牌；等对手攻击时，使用反制响应。';
    dict.tutorial_hint_counter = dict.tutorial_hint_counter || '这是反制窗口。对手打出攻击牌时，可以选择可支付的反制牌，或等待倒计时选择不反制。';
    dict.tutorial_hint_bloom = dict.tutorial_hint_bloom || 'Bloom 技能牌用于回复、施加状态或改变资源。试着打出一张技能牌，观察效果和资源变化。';
    dict.tutorial_hint_root = dict.tutorial_hint_root || 'Root 装备牌会持续生效或在满足条件后触发。先打出一张，下一回合再观察它的作用。';
    dict.tutorial_hint_fission = dict.tutorial_hint_fission || '现在，让我们来看看不同类型的牌。裂变是一张 Bloom 技能牌。普通攻击被裂变后总伤害可能接近不变，但三角形会在每段伤害后成长。把裂变用于三角形。';
    dict.tutorial_hint_play_fissioned = dict.tutorial_hint_play_fissioned || '三角形已经带有裂变层数。现在把它打出，观察每段伤害和三角形层数如何连续结算。';
    dict.tutorial_hint_fusion = dict.tutorial_hint_fusion || '聚变也是 Bloom 技能牌。它会选择2-3张同名攻击牌，合成为一张更强的牌。选择同名攻击牌完成聚变。';
});
I18N.en.tutorial_start = 'Tutorial';
I18N.en.target_pick_hint = 'Click a highlighted player area.';
I18N.en.waiting_opponent_counter = 'Waiting for opponent counter';
I18N.en.tutorial_hint_play_fusioned = 'The fused attack is ready. You have enough E now; play it to see the boosted damage.';
I18N.en.tutorial_victory_message = 'Congratulations, you completed the tutorial!\nHave fun in Garden of Thorn!';
I18N.en.tutorial_defeat_message = 'The tutorial match was lost. That is fine; the next match will be smoother.';
I18N.en.tutorial_retry = 'Retry Tutorial';
I18N.en.tutorial_skip = 'Skip Tutorial';
I18N.fr.tutorial_hint_play_fusioned = "L'attaque fusionnée est prête. Vous avez assez d'E : jouez-la pour voir les dégâts renforcés.";
I18N.fr.tutorial_victory_message = 'Félicitations, vous avez terminé le tutoriel !\nAmusez-vous bien dans Garden of Thorn !';
I18N.fr.tutorial_defeat_message = 'La partie du tutoriel est perdue. Ce n’est pas grave : la prochaine sera plus fluide.';
I18N.fr.tutorial_retry = 'Réessayer le tutoriel';
I18N.fr.target_pick_hint = 'Cliquez sur une zone de joueur surlignée.';
I18N.pt.tutorial_hint_play_fusioned = 'O ataque fundido está pronto. Você tem E suficiente; jogue-o para ver o dano aumentado.';
I18N.pt.tutorial_victory_message = 'Parabéns, você concluiu o tutorial!\nDivirta-se em Garden of Thorn!';
I18N.pt.tutorial_defeat_message = 'A partida do tutorial foi perdida. Tudo bem; a próxima será mais tranquila.';
I18N.pt.tutorial_retry = 'Tentar tutorial de novo';
I18N.pt.target_pick_hint = 'Clique na área de jogador destacada.';
I18N.ja.tutorial_hint_play_fusioned = '融合した攻撃カードの準備ができました。Eは足りています。打ち出して強化後のダメージを見てみましょう。';
I18N.ja.tutorial_victory_message = 'おめでとうございます。チュートリアルを完了しました！\nGarden of Thorn を楽しんでください！';
I18N.ja.tutorial_defeat_message = 'チュートリアルの対局に敗北しました。大丈夫です。次の対局ではもっと動きが見えてきます。';
I18N.ja.tutorial_retry = 'チュートリアルをやり直す';
I18N.ja.target_pick_hint = '強調表示されたプレイヤー欄を押してください。';
I18N.en.tutorial_intro = 'Now, let’s begin the tutorial.';
I18N.en.tutorial_hint_play = 'Play a Thorn attack first, then watch the opponent’s H change.';
I18N.en.tutorial_hint_end = 'After acting, press End Turn to pass the pace to the opponent.';
I18N.en.tutorial_hint_enemy = 'Now watch the opponent act. Track the battle log and H/E/M bars.';
I18N.en.tutorial_hint_deck = 'Check your draw deck: press View Deck to see what may come next.';
I18N.en.tutorial_hint_continue = 'Keep playing cards and end your turn. Later you will draw a Guard card; use it to respond when the opponent attacks.';
I18N.en.tutorial_hint_counter = 'This is the counter window. When the opponent plays an attack, choose an affordable Guard card or let the countdown pass.';
I18N.en.tutorial_hint_bloom = 'Bloom skill cards heal, apply states, or change resources. Play one and watch the effect and resource changes.';
I18N.en.tutorial_hint_root = 'Root equipment cards provide ongoing or triggered effects. Play one now and observe it next turn.';
I18N.en.tutorial_hint_fission = 'Now let’s look at different card types. Fission is a Bloom skill card. Splitting a basic attack may keep total damage close, but Triangle grows after each hit. Use Fission on Triangle.';
I18N.en.tutorial_hint_play_fissioned = 'Triangle now has Fission. Play it and watch each hit resolve while Triangle stacks grow.';
I18N.en.tutorial_hint_fusion = 'Fusion is also a Bloom skill card. It chooses 2-3 same-name attacks and combines them into one stronger card.';
I18N.zh.tutorial_start = '新手引导';
I18N.zh.target_pick_hint = '点击高亮的玩家区域。';
I18N.zh.tutorial_skip = '跳过引导';
I18N.zh.tutorial_intro = '现在，让我们开始新手教程吧！';
I18N.zh.tutorial_hint_play = '先打出一张 Thorn 攻击牌，观察对手 H 的变化。';
I18N.zh.tutorial_hint_end = '行动完成后，点击“结束回合”，把节奏交给对手。';
I18N.zh.tutorial_hint_enemy = '现在观察对手行动。注意战斗日志和 H/E/M 的变化。';
I18N.zh.tutorial_hint_deck = '先看看抽牌堆：点击“查看牌堆”，了解接下来可能抽到什么。';
I18N.zh.tutorial_hint_continue = '继续出牌并结束回合。稍后你会抽到反制牌；等对手攻击时，使用反制响应。';
I18N.zh.tutorial_hint_counter = '这是反制窗口。对手打出攻击牌时，可以选择可支付的反制牌，或等待倒计时选择不反制。';
I18N.zh.tutorial_hint_bloom = 'Bloom 技能牌用于回复、施加状态或改变资源。试着打出一张技能牌，观察效果和资源变化。';
I18N.zh.tutorial_hint_root = 'Root 装备牌会持续生效或在满足条件后触发。先打出一张，下一回合再观察它的作用。';
I18N.zh.tutorial_hint_fission = '现在，让我们来看看不同类型的牌。裂变是一张 Bloom 技能牌。普通攻击被裂变后总伤害可能接近不变，但三角形会在每段伤害后成长。把裂变用于三角形。';
I18N.zh.tutorial_hint_play_fissioned = '三角形已经带有裂变层数。现在把它打出，观察每段伤害和三角形层数如何连续结算。';
I18N.zh.tutorial_hint_fusion = '聚变也是 Bloom 技能牌。它会选择2-3张同名攻击牌，合成为一张更强的牌。选择同名攻击牌完成聚变。';
Object.assign(I18N.en, { tutorial_hint_free: 'You have seen the core actions. Now try your own line: play useful cards, watch H/E/M, then end your turn.' });
Object.assign(I18N.zh, { tutorial_hint_free: '核心操作已经看过了。现在可以自己判断：打出合适的牌，观察 H/E/M，然后结束回合。' });
Object.assign(I18N.fr, { tutorial_hint_free: 'Vous avez vu les actions principales. Essayez maintenant votre propre ligne : jouez les bonnes cartes, observez H/E/M, puis terminez le tour.' });
Object.assign(I18N.pt, { tutorial_hint_free: 'Você já viu as ações principais. Agora jogue por conta própria: use cartas úteis, observe H/E/M e termine o turno.' });
Object.assign(I18N.ja, { tutorial_hint_free: '基本操作は確認できました。ここからは自分で判断して、有効なカードを使い、H/E/Mを見てターンを終了しましょう。' });
Object.assign(I18N.zh, { waiting_opponent_counter: '等待对方反制' });
Object.assign(I18N.fr, { waiting_opponent_counter: 'En attente du contre adverse' });
Object.assign(I18N.pt, { waiting_opponent_counter: 'Aguardando resposta do oponente' });
Object.assign(I18N.ja, { waiting_opponent_counter: 'Waiting for opponent counter' });

Object.assign(I18N.zh, {
    about_title: '关于', about_gameplay: '游戏玩法', about_credits: '致谢', about_contact: '联系方式',
    credits_developer: '开发者', credits_design: '设计', credits_art: '美工', credits_special: '特别鸣谢',
    rules_intro_title: '游戏介绍', rules_type_thorn: '攻击(Thorn)', rules_type_bloom: '技能(Bloom)', rules_type_root: '装备(Root)', rules_type_guard: '反制(Guard)',
    rules_goal_title: '基本目标',
    rules_goal_text: 'Garden of Thorn 荆棘花园 是多人卡牌对战游戏。一般情况下，你的目标是通过使用四类牌：{thorn}、{bloom}、{root}和{guard}，让对方阵营的 H 降到 0，同时保护自己和队友的 H。',
    rules_resources_title: '资源',
    rules_resources_text: 'H(Health) 是生命。H 降到 0 时，玩家通常会失去继续行动的能力；在 2v2 中，一方全部玩家阵亡才会判负。E(Elixir) 是能量，大多数卡牌消耗 E。M(Magic) 是魔力，部分魔法牌消耗 M。通常只有在自己的回合开始时，玩家才会抽牌并回复资源。',
    rules_types_title: '卡牌类型',
    rules_types_text: '{thornRaw} 是攻击牌，用于造成直接伤害，例如 {basic}、{bone}。{bloomRaw} 是技能牌，用于回复、施加状态、调整资源或改变局面，例如 {fire}。{rootRaw} 是装备牌，打出后提供持续效果或可触发效果，例如 {leaf}。{guardRaw} 是反制牌，不能像普通手牌一样主动打出，需要在对方行动满足条件时响应。',
    rules_flow_title: '回合流程',
    rules_flow_text: '正常模式通常先进行选牌，再选择配装倾向，然后进入对局。轮到你时，系统会处理回合开始效果、抽牌和资源回复。之后你可以打出手牌，或触发已经装备至少一回合且满足条件的装备。完成行动后，点击结束回合，将行动权交给下一位玩家。2v2 中回合顺序会在两队之间交替；玩家阵亡不会改变既定顺序，但阵亡玩家的回合会被跳过。',
    rules_keywords_title: '常见关键词',
    rules_keywords_text: '<b>放逐</b>表示卡牌打出或结算后进入放逐区，通常不会再回到牌堆或弃牌堆。<b>精准</b>表示攻击被闪避响应时改为造成一半伤害。<b>不可摧毁</b>表示装备不能被摧毁效果破坏。<b>萌芽</b>表示抽到该牌时会额外抽牌。<b>共生</b>表示该牌不受同名卡连续使用费用惩罚。部分模式或模组可能加入额外关键词，以实际卡牌显示为准。',
    rules_examples_title: '示例',
    rules_examples_text: '{stinger} 是高伤害精准攻击；{sewage} 可以摧毁装备；{bubble} 可以响应攻击并提供闪避。点击示例卡牌名可在图鉴中查看对应卡牌。',
    rules_skip_confirm_title: '提示',
    rules_skip_confirm_msg: '你确认要跳过游戏介绍吗？\n可以在 关于>游戏玩法 中再次打开此界面。',
    gallery_back_rules: '返回介绍', gallery_explanation: '说明',
    tag_desc_precision: '攻击类关键词。精准攻击被闪避响应时不会完全失效，而是改为造成一半伤害。',
    tag_desc_exile: '结算去向关键词。带有此标签的卡牌在打出或结算后进入放逐区，而不是进入弃牌堆。',
    tag_desc_non_stackable: '装备类关键词。该效果可以多次装备，但同类效果不会重复叠加；多个副本主要用于在部分装备被摧毁后保留后续副本。',
    tag_desc_indestructible: '装备类关键词。该牌作为装备时不能被摧毁效果破坏；玩家死亡时也会保留不可摧毁装备。',
    tag_desc_sprout: '抽牌类关键词。抽到带有萌芽的牌时，会额外抽牌；若手牌已满，仍遵循正常爆牌/弃牌规则。',
    tag_desc_symbiosis: '费用类关键词。该牌不受同名卡连续使用费用惩罚，适合在同一回合多次使用。',
    tag_desc_attract: '手牌上限关键词。手牌满时，带有吸引的牌会优先挤掉没有吸引的牌，减少关键牌爆掉的风险。',
    tag_desc_void: '回合结束关键词。带有虚无的牌如果留在手牌中，会在回合结束时被放逐。',
    tag_desc_self_only: '目标选择关键词。打出这张牌时不弹出目标选择窗口，效果会按卡牌自身规则结算。',
    tag_desc_uncancellable: '选择限制关键词。该牌弹出选择窗口时不显示取消按钮，玩家必须完成选择。用于避免通过0消耗选择牌窗口查看隐藏信息后取消，例如磁铁查看敌方手牌。',
    tag_desc_infinite_exclude: '模式限制关键词。该牌不会进入无限火力的随机牌库，用于排除与该模式机制冲突的牌。',
    tag_desc_copy: '抽牌关键词。当此牌进入手中时，将层数张放逐复制加入手中。',
    tag_desc_unique: '牌库关键词。整场对局自己总牌库中仅允许出现一张，多余的将被放逐。',
    tag_desc_swift: '费用关键词。此牌的E消耗减少X（最低0E）。',
    tag_desc_rebound: '结算去向关键词。带有回转的牌打出并结算后，会立即回到使用者手牌。',
    tag_desc_stealth: '响应关键词。此牌不会触发对手的响应窗口。',
    tag_desc_revealed: '可见性关键词。此牌在手中时永久对对手展示。',
    tag_desc_default: '模组或扩展标签。该标签的具体含义由对应模组或卡牌效果定义。'
});

Object.assign(I18N.en, {
    about_title: 'About', about_gameplay: 'How to Play', about_credits: 'Credits', about_contact: 'Contact',
    credits_developer: 'Developer', credits_design: 'Design', credits_art: 'Art', credits_special: 'Special Thanks',
    rules_intro_title: 'Game Introduction', rules_type_thorn: 'Thorn attacks', rules_type_bloom: 'Bloom skills', rules_type_root: 'Root equipment', rules_type_guard: 'Guard counters',
    rules_goal_title: 'Goal',
    rules_goal_text: 'Garden of Thorn 荆棘花园 is a multiplayer card battle game. In most modes, your goal is to use four card types: {thorn}, {bloom}, {root}, and {guard}, reduce the opposing side’s H to 0, and protect your own side’s H.',
    rules_resources_title: 'Resources',
    rules_resources_text: 'H(Health) is life. When H reaches 0, that player usually loses the ability to act; in 2v2, a side loses only when all of its players are defeated. E(Elixir) is energy and pays for most cards. M(Magic) pays for some magic cards. Usually, a player draws cards and recovers resources only at the start of their own turn.',
    rules_types_title: 'Card Types',
    rules_types_text: '{thornRaw} cards deal direct damage, such as {basic} and {bone}. {bloomRaw} cards heal, apply states, adjust resources, or change the board, such as {fire}. {rootRaw} cards provide ongoing or triggered effects after being played, such as {leaf}. {guardRaw} cards are counters; they are not played like normal hand cards and respond only when an opponent’s action meets their condition.',
    rules_flow_title: 'Turn Flow',
    rules_flow_text: 'A normal match usually starts with drafting cards, choosing opening events, and then entering battle. On your turn, start-of-turn effects, draws, and resource recovery resolve first. Then you may play hand cards or trigger equipment that has been equipped for at least one turn and meets its condition. End your turn to pass action to the next player. In 2v2, turns alternate between teams; defeated players do not change the order, but their turns are skipped.',
    rules_keywords_title: 'Common Keywords',
    rules_keywords_text: '<b>Exile</b> means the card goes to exile after being played or resolved instead of the discard pile. <b>Precision</b> means if the attack is dodged, it deals half damage instead of failing completely. <b>Indestructible</b> means equipment cannot be destroyed by destroy effects. <b>Sprout</b> draws extra cards when drawn. <b>Symbiosis</b> ignores same-name card cost penalties. Some modes or mods may add more keywords; the card text is authoritative.',
    rules_examples_title: 'Examples',
    rules_examples_text: '{stinger} is a high-damage Precision attack; {sewage} can destroy equipment; {bubble} can respond to attacks and grant Dodge. Click an example card name to open it in the compendium.',
    rules_skip_confirm_title: 'Notice',
    rules_skip_confirm_msg: 'Skip the game introduction?\nYou can open it again from About > How to Play.',
    gallery_back_rules: 'Back to Introduction', gallery_explanation: 'Explanation',
    tutorial_start: 'Tutorial', tutorial_skip: 'Skip Tutorial', tutorial_intro: 'Now, let’s begin the tutorial.',
    tutorial_hint_play: 'Play a Thorn attack first, then watch the opponent’s H change.',
    tutorial_hint_end: 'After acting, press End Turn to pass the pace to the opponent.',
    tutorial_hint_enemy: 'Now watch the opponent act. Track the battle log and H/E/M bars.',
    tutorial_hint_deck: 'Check your draw deck: press View Deck to see what may come next.',
    tutorial_hint_continue: 'Keep playing cards and end your turn. Later you will draw a Guard card; use it to respond when the opponent attacks.',
    tutorial_hint_counter: 'This is the counter window. When the opponent plays an attack, choose an affordable Guard card or let the countdown pass.',
    tutorial_hint_bloom: 'Bloom skill cards heal, apply states, or change resources. Play one and watch the effect and resource changes.',
    tutorial_hint_root: 'Root equipment cards provide ongoing or triggered effects after being played. Play one now and observe it next turn.',
    tutorial_hint_fission: 'Now let’s look at different card types. Fission is a Bloom skill card. Splitting a basic attack may keep total damage close, but Triangle grows after each hit. Use Fission on Triangle.',
    tutorial_hint_play_fissioned: 'Triangle now has Fission. Play it and watch each hit resolve while Triangle stacks grow.',
    tutorial_hint_fusion: 'Fusion is also a Bloom skill card. It chooses 2-3 same-name attacks and combines them into one stronger card.',
    tutorial_hint_play_fusioned: 'The fused attack is ready. You have enough E now; play it to see the boosted damage.',
    tutorial_victory_message: 'Congratulations, you completed the tutorial!\nHave fun in Garden of Thorn!',
    tutorial_defeat_message: 'The tutorial match was lost. That is fine; the next match will be smoother.',
    tutorial_retry: 'Retry Tutorial',
    tag_desc_precision: 'Attack keyword. A Precision attack does not fully fail when dodged; it deals half damage instead.',
    tag_desc_exile: 'Resolution keyword. This card goes to exile after being played or resolved instead of going to the discard pile.',
    tag_desc_non_stackable: 'Equipment keyword. Multiple copies may be equipped, but the same effect does not stack; spare copies mainly keep the effect available after one copy is destroyed.',
    tag_desc_indestructible: 'Equipment keyword. This equipment cannot be destroyed by destroy effects and also remains when its owner is defeated.',
    tag_desc_sprout: 'Draw keyword. When drawn, this card draws extra cards; hand limit and overflow rules still apply.',
    tag_desc_symbiosis: 'Cost keyword. This card ignores same-name card cost penalties.',
    tag_desc_attract: 'Hand-limit keyword. When your hand is full, Attract cards push out non-Attract cards first.',
    tag_desc_void: 'End-turn keyword. If this card remains in hand at end of turn, it is exiled.',
    tag_desc_self_only: 'Targeting keyword. This card does not open a target picker when played; its effect resolves by its own rules.',
    tag_desc_uncancellable: 'Choice keyword. Selection windows from this card do not show a cancel button; the player must complete the choice. This prevents checking hidden information for 0 cost and canceling, such as with Magnet.',
    tag_desc_infinite_exclude: 'Mode keyword. This card is excluded from Infinite Fire random pools because it conflicts with that mode.',
    tag_desc_copy: 'Draw keyword. When this card enters your hand, add N exile copies to your hand.',
    tag_desc_unique: 'Deck keyword. Only one copy of this card is allowed in your deck; extras are exiled.',
    tag_desc_swift: 'Cost keyword. This card\'s E cost is reduced by X (minimum 0E).',
    tag_desc_rebound: 'Resolution keyword. After being played and resolved, this card immediately returns to its user’s hand.',
    tag_desc_default: 'Mod or extension tag. Its exact meaning is defined by the relevant mod or card effect.',
    tag_desc_stealth: 'Response keyword. This card does not trigger opponent response windows.',
    tag_desc_revealed: 'Visibility keyword. This card is permanently visible to the opponent while in hand.'
});

Object.assign(I18N.fr, {
    about_title: 'À propos', about_gameplay: 'Règles', about_credits: 'Crédits', about_contact: 'Contact',
    credits_developer: 'Développeur', credits_design: 'Design', credits_art: 'Art', credits_special: 'Remerciements',
    rules_intro_title: 'Présentation du jeu', rules_type_thorn: 'attaques Thorn', rules_type_bloom: 'compétences Bloom', rules_type_root: 'équipements Root', rules_type_guard: 'contres Guard',
    rules_goal_title: 'Objectif',
    rules_goal_text: 'Garden of Thorn 荆棘花园 est un jeu de cartes multijoueur. Dans la plupart des modes, votre objectif est d’utiliser quatre types de cartes : {thorn}, {bloom}, {root} et {guard}, afin de réduire le H du camp adverse à 0 tout en protégeant votre camp.',
    rules_resources_title: 'Ressources',
    rules_resources_text: 'H(Health) représente la vie. À 0 H, un joueur perd généralement sa capacité d’agir ; en 2v2, un camp perd seulement lorsque tous ses joueurs sont vaincus. E(Elixir) paie la plupart des cartes. M(Magic) paie certaines cartes magiques. En général, un joueur pioche et récupère des ressources uniquement au début de son propre tour.',
    rules_types_title: 'Types de cartes',
    rules_types_text: 'Les cartes {thornRaw} infligent des dégâts directs, comme {basic} et {bone}. Les cartes {bloomRaw} soignent, appliquent des états, modifient les ressources ou changent la situation, comme {fire}. Les cartes {rootRaw} fournissent des effets continus ou déclenchés après avoir été jouées, comme {leaf}. Les cartes {guardRaw} sont des contres : elles répondent à une action adverse qui remplit leur condition.',
    rules_flow_title: 'Déroulement',
    rules_flow_text: 'Un match normal commence par le draft, le choix des événements de départ, puis le combat. À votre tour, les effets de début de tour, la pioche et la récupération se résolvent d’abord. Vous pouvez ensuite jouer des cartes ou déclencher un équipement équipé depuis au moins un tour. Terminez votre tour pour passer au joueur suivant. En 2v2, les tours alternent entre les équipes ; les joueurs vaincus ne changent pas l’ordre, mais leur tour est sauté.',
    rules_keywords_title: 'Mots-clés courants',
    rules_keywords_text: '<b>Exil</b> signifie que la carte va dans l’exil après avoir été jouée ou résolue. <b>Précision</b> signifie qu’une attaque esquivée inflige la moitié des dégâts. <b>Indestructible</b> signifie qu’un équipement ne peut pas être détruit par les effets de destruction. <b>Germination</b> pioche des cartes supplémentaires quand la carte est piochée. <b>Symbiose</b> ignore les pénalités de coût des cartes de même nom. Le texte de la carte fait foi.',
    rules_examples_title: 'Exemples',
    rules_examples_text: '{stinger} est une attaque Précision à gros dégâts ; {sewage} peut détruire un équipement ; {bubble} peut répondre aux attaques et donner Esquive. Cliquez sur un nom de carte pour l’ouvrir dans le compendium.',
    rules_skip_confirm_title: 'Notice',
    rules_skip_confirm_msg: 'Passer la présentation du jeu ?\nVous pourrez la rouvrir dans À propos > Règles.',
    gallery_title: 'Encyclopédie', gallery_cards: 'Cartes', gallery_tags: 'Tags', gallery_events: 'Événements de départ',
    gallery_search: 'Rechercher', gallery_no_items: 'Aucune entrée.', gallery_cards_with_tag: 'Cartes avec ce tag',
    gallery_card_count: '{0} cartes', gallery_type: 'Type', gallery_cost: 'Coût', gallery_tags_label: 'Tags',
    gallery_description: 'Description', gallery_effect: 'Effet', gallery_trigger: 'Déclenchement',
    gallery_back_rules: 'Retour à la présentation', gallery_explanation: 'Explication',
    tutorial_start: 'Tutoriel', tutorial_skip: 'Passer', tutorial_intro: 'Commençons le tutoriel.',
    tutorial_hint_play: 'Jouez d’abord une attaque Thorn et observez le H adverse.',
    tutorial_hint_end: 'Après votre action, appuyez sur Fin du tour.',
    tutorial_hint_enemy: 'Observez maintenant l’adversaire. Suivez le journal et les barres H/E/M.',
    tutorial_hint_deck: 'Regardez votre pioche : appuyez sur Voir le deck.',
    tutorial_hint_continue: 'Continuez à jouer et terminez le tour. Vous piocherez bientôt une carte Guard pour répondre à une attaque.',
    tutorial_hint_counter: 'Ceci est la fenêtre de contre. Choisissez une carte Guard payable ou laissez le compte à rebours passer.',
    tutorial_hint_bloom: 'Les cartes Bloom soignent, appliquent des états ou changent les ressources. Jouez-en une pour voir l’effet.',
    tutorial_hint_root: 'Les cartes Root fournissent des effets continus ou déclenchés. Jouez-en une et observez-la au prochain tour.',
    tutorial_hint_fission: 'Voyons les types de cartes. Fission est une Bloom : sur une attaque simple, le total peut rester proche, mais Triangle grandit après chaque touche. Utilisez Fission sur Triangle.',
    tutorial_hint_play_fissioned: 'Triangle possède maintenant Fission. Jouez-le et observez chaque dégât et chaque couche.',
    tutorial_hint_fusion: 'Fusion est aussi une Bloom. Elle combine 2-3 attaques de même nom en une carte plus forte.',
    tutorial_hint_play_fusioned: 'L’attaque fusionnée est prête. Vous avez assez de E : jouez-la pour voir les dégâts augmentés.',
    tutorial_victory_message: 'Félicitations, vous avez terminé le tutoriel !\nAmusez-vous bien dans Garden of Thorn !',
    tutorial_defeat_message: 'La partie du tutoriel est perdue. Ce n’est pas grave : la prochaine sera plus fluide.',
    tutorial_retry: 'Réessayer',
});

Object.assign(I18N.pt, {
    about_title: 'Sobre', about_gameplay: 'Como jogar', about_credits: 'Créditos', about_contact: 'Contato',
    credits_developer: 'Desenvolvedor', credits_design: 'Design', credits_art: 'Arte', credits_special: 'Agradecimentos',
    rules_intro_title: 'Introdução do jogo', rules_type_thorn: 'ataques Thorn', rules_type_bloom: 'habilidades Bloom', rules_type_root: 'equipamentos Root', rules_type_guard: 'respostas Guard',
    rules_goal_title: 'Objetivo',
    rules_goal_text: 'Garden of Thorn 荆棘花园 é um jogo de cartas multijogador. Na maioria dos modos, seu objetivo é usar quatro tipos de cartas: {thorn}, {bloom}, {root} e {guard}, reduzir o H do lado inimigo a 0 e proteger seu lado.',
    rules_resources_title: 'Recursos',
    rules_resources_text: 'H(Health) é vida. Ao chegar a 0 H, o jogador geralmente perde a capacidade de agir; no 2v2, um lado perde apenas quando todos os seus jogadores são derrotados. E(Elixir) paga a maioria das cartas. M(Magic) paga algumas cartas mágicas. Normalmente, um jogador compra cartas e recupera recursos apenas no começo do próprio turno.',
    rules_types_title: 'Tipos de carta',
    rules_types_text: 'Cartas {thornRaw} causam dano direto, como {basic} e {bone}. Cartas {bloomRaw} curam, aplicam estados, ajustam recursos ou mudam o campo, como {fire}. Cartas {rootRaw} dão efeitos contínuos ou acionáveis depois de jogadas, como {leaf}. Cartas {guardRaw} são respostas usadas quando uma ação inimiga satisfaz sua condição.',
    rules_flow_title: 'Fluxo do turno',
    rules_flow_text: 'Uma partida normal geralmente começa com escolha de cartas, eventos iniciais e depois combate. No seu turno, efeitos de início, compra e recuperação são resolvidos primeiro. Depois você pode jogar cartas ou acionar equipamentos equipados há pelo menos um turno. Termine o turno para passar ao próximo jogador. No 2v2, os turnos alternam entre equipes; jogadores derrotados não mudam a ordem, mas têm seus turnos pulados.',
    rules_keywords_title: 'Palavras-chave',
    rules_keywords_text: '<b>Exílio</b> envia a carta ao exílio após ser jogada ou resolvida. <b>Precisão</b> faz uma ataque esquivado causar metade do dano. <b>Indestrutível</b> impede que equipamento seja destruído por efeitos de destruição. <b>Broto</b> compra cartas extras quando comprado. <b>Simbiose</b> ignora penalidades de custo por cartas de mesmo nome. O texto da carta é a fonte final.',
    rules_examples_title: 'Exemplos',
    rules_examples_text: '{stinger} é um ataque de Precisão com alto dano; {sewage} pode destruir equipamento; {bubble} responde a ataques e concede Esquiva. Clique no nome de uma carta para abri-la no compêndio.',
    rules_skip_confirm_title: 'Aviso',
    rules_skip_confirm_msg: 'Pular a introdução do jogo?\nVocê pode reabri-la em Sobre > Como jogar.',
    gallery_title: 'Compêndio', gallery_cards: 'Cartas', gallery_tags: 'Tags', gallery_events: 'Eventos iniciais',
    gallery_search: 'Buscar', gallery_no_items: 'Nenhuma entrada.', gallery_cards_with_tag: 'Cartas com esta tag',
    gallery_card_count: '{0} cartas', gallery_type: 'Tipo', gallery_cost: 'Custo', gallery_tags_label: 'Tags',
    gallery_description: 'Descrição', gallery_effect: 'Efeito', gallery_trigger: 'Acionamento',
    gallery_back_rules: 'Voltar à introdução', gallery_explanation: 'Explicação',
    tutorial_start: 'Tutorial', tutorial_skip: 'Pular', tutorial_intro: 'Agora vamos começar o tutorial.',
    tutorial_hint_play: 'Jogue primeiro um ataque Thorn e observe o H do oponente.',
    tutorial_hint_end: 'Depois de agir, pressione Finalizar turno.',
    tutorial_hint_enemy: 'Observe o oponente. Acompanhe o registro e as barras H/E/M.',
    tutorial_hint_deck: 'Veja seu deck de compra: pressione Ver Deck.',
    tutorial_hint_continue: 'Continue jogando e finalize o turno. Mais tarde você comprará uma carta Guard para responder a um ataque.',
    tutorial_hint_counter: 'Esta é a janela de resposta. Escolha uma carta Guard pagável ou deixe a contagem passar.',
    tutorial_hint_bloom: 'Cartas Bloom curam, aplicam estados ou mudam recursos. Jogue uma e observe.',
    tutorial_hint_root: 'Cartas Root dão efeitos contínuos ou acionáveis. Jogue uma e veja seu efeito no próximo turno.',
    tutorial_hint_fission: 'Vamos ver tipos diferentes. Fission é uma Bloom: em ataques simples o total pode ficar parecido, mas Triangle cresce após cada acerto. Use Fission em Triangle.',
    tutorial_hint_play_fissioned: 'Triangle agora tem Fission. Jogue-o e observe cada acerto e camada.',
    tutorial_hint_fusion: 'Fusion também é Bloom. Ela combina 2-3 ataques de mesmo nome em uma carta mais forte.',
    tutorial_hint_play_fusioned: 'O ataque fundido está pronto. Você tem E suficiente; jogue-o para ver o dano aumentado.',
    tutorial_victory_message: 'Parabéns, você concluiu o tutorial!\nDivirta-se em Garden of Thorn!',
    tutorial_defeat_message: 'A partida do tutorial foi perdida. Tudo bem; a próxima será mais tranquila.',
    tutorial_retry: 'Tentar de novo',
});


Object.assign(I18N.ja, {
    about_title: '概要', about_gameplay: '遊び方', about_credits: 'クレジット', about_contact: '連絡先',
    credits_developer: '開発者', credits_design: 'デザイン', credits_art: '美術', credits_special: 'Special Thanks',
    rules_intro_title: 'ゲーム紹介', rules_type_thorn: '攻撃(Thorn)', rules_type_bloom: 'スキル(Bloom)', rules_type_root: '装備(Root)', rules_type_guard: 'カウンター(Guard)',
    rules_goal_title: '基本目標',
    rules_goal_text: 'Garden of Thorn 荆棘花园 はマルチプレイヤーカード対戦ゲームです。多くのモードでは、{thorn}、{bloom}、{root}、{guard}の4種類のカードを使い、相手側の H を 0 にしながら自分側の H を守ることが目標です。',
    rules_resources_title: 'リソース',
    rules_resources_text: 'H(Health) は生命です。H が 0 になると通常そのプレイヤーは行動できなくなります。2v2 では、片側の全プレイヤーが倒れたときに敗北します。E(Elixir) は多くのカードの支払いに使います。M(Magic) は一部の魔法カードに使います。通常、ドローとリソース回復は自分のターン開始時だけ行われます。',
    rules_types_title: 'カードタイプ',
    rules_types_text: '{thornRaw} は直接ダメージを与えるカードで、例は {basic}、{bone} です。{bloomRaw} は回復、状態付与、リソース調整などを行うカードで、例は {fire} です。{rootRaw} は使用後に継続効果や発動効果を持つカードで、例は {leaf} です。{guardRaw} は相手の行動が条件を満たしたときに反応するカウンターです。',
    rules_flow_title: 'ターンの流れ',
    rules_flow_text: '通常モードでは、カード選択、開局イベント選択、その後に対局へ入ります。自分のターンでは、ターン開始効果、ドロー、リソース回復が先に処理されます。その後、手札を使ったり、1ターン以上装備され条件を満たす装備を発動できます。行動後はターン終了を押して次のプレイヤーへ移ります。2v2 ではチーム間で交互に進み、倒れたプレイヤーは順番を変えず、そのターンだけ飛ばされます。',
    rules_keywords_title: '主なキーワード',
    rules_keywords_text: '<b>追放</b>は、プレイまたは解決後に捨て札ではなく追放領域へ行くことを示します。<b>精密</b>は、回避されたときに半分のダメージを与えることを示します。<b>破壊不可</b>は破壊効果で装備が破壊されないことを示します。<b>萌芽</b>は引いたときに追加ドローします。<b>共生</b>は同名カードの費用ペナルティを受けません。最終的な効果はカード本文を優先します。',
    rules_examples_title: '例',
    rules_examples_text: '{stinger} は高ダメージの精密攻撃です。{sewage} は装備を破壊できます。{bubble} は攻撃に反応して回避を得ます。カード名をクリックすると図鑑で確認できます。',
    rules_skip_confirm_title: '確認',
    rules_skip_confirm_msg: 'ゲーム紹介をスキップしますか？\n概要 > 遊び方 から再度開けます。',
    gallery_title: '図鑑', gallery_cards: 'カード', gallery_tags: 'タグ', gallery_events: '開局イベント',
    gallery_search: '検索', gallery_no_items: '項目がありません。', gallery_cards_with_tag: 'このタグを持つカード',
    gallery_card_count: '{0}枚のカード', gallery_type: 'タイプ', gallery_cost: 'コスト', gallery_tags_label: 'タグ',
    gallery_description: '説明', gallery_effect: '効果', gallery_trigger: '発動',
    gallery_back_rules: '紹介に戻る', gallery_explanation: '説明',
    tutorial_start: 'チュートリアル', tutorial_skip: 'スキップ', tutorial_intro: 'それではチュートリアルを始めましょう。',
    tutorial_hint_play: 'まず Thorn 攻撃カードを使い、相手の H の変化を確認しましょう。',
    tutorial_hint_end: '行動したら、ターン終了を押します。',
    tutorial_hint_enemy: '相手の行動を見ましょう。ログと H/E/M を確認してください。',
    tutorial_hint_deck: '山札を確認します。「デッキ確認」を押しましょう。',
    tutorial_hint_continue: 'カードを使ってターン終了しましょう。後で Guard を引いたら、相手の攻撃に反応できます。',
    tutorial_hint_counter: 'これはカウンター画面です。支払える Guard を選ぶか、カウントダウンを待ちます。',
    tutorial_hint_bloom: 'Bloom は回復、状態付与、リソース変更を行います。1枚使って効果を見ましょう。',
    tutorial_hint_root: 'Root は継続効果や発動効果を持ちます。1枚使って、次のターンに効果を確認しましょう。',
    tutorial_hint_fission: '別のタイプを見てみましょう。裂変は Bloom です。通常攻撃では総ダメージが近いこともありますが、三角形は各ヒット後に成長します。三角形に裂変を使いましょう。',
    tutorial_hint_play_fissioned: '三角形に裂変が付きました。使って、各ヒットと層の増え方を確認しましょう。',
    tutorial_hint_fusion: '聚变も Bloom です。同名攻撃カード2-3枚を1枚の強いカードにまとめます。',
    tutorial_hint_play_fusioned: '融合した攻撃カードの準備ができました。Eは足りています。打ち出して強化後のダメージを見てみましょう。',
    tutorial_victory_message: 'おめでとうございます。チュートリアルを完了しました！\nGarden of Thorn を楽しんでください！',
    tutorial_defeat_message: 'チュートリアルの対局に敗北しました。大丈夫です。次の対局ではもっと動きが見えてきます。',
    tutorial_retry: 'やり直す',
});

Object.assign(I18N.fr, {
    tag_desc_precision: 'Mot-clé d’attaque. Une attaque Précision esquivée inflige la moitié des dégâts au lieu d’échouer entièrement.',
    tag_desc_exile: 'Mot-clé de résolution. Cette carte va dans l’exil après avoir été jouée ou résolue, au lieu de la défausse.',
    tag_desc_non_stackable: 'Mot-clé d’équipement. Plusieurs copies peuvent être équipées, mais le même effet ne se cumule pas ; les copies restantes servent surtout si une copie est détruite.',
    tag_desc_indestructible: 'Mot-clé d’équipement. Cet équipement ne peut pas être détruit par les effets de destruction et reste aussi quand son propriétaire est vaincu.',
    tag_desc_sprout: 'Mot-clé de pioche. Quand cette carte est piochée, elle pioche des cartes supplémentaires ; les limites de main restent applicables.',
    tag_desc_symbiosis: 'Mot-clé de coût. Cette carte ignore les pénalités de coût des cartes de même nom.',
    tag_desc_attract: 'Mot-clé de limite de main. Quand la main est pleine, les cartes Attraction repoussent d’abord les cartes sans Attraction.',
    tag_desc_void: 'Mot-clé de fin de tour. Si cette carte reste en main à la fin du tour, elle est exilée.',
    tag_desc_self_only: 'Mot-clé de ciblage. Cette carte n’ouvre pas de sélection de cible et résout son effet selon ses propres règles.',
    tag_desc_uncancellable: 'Mot-clé de choix. Les fenêtres de choix de cette carte n’affichent pas de bouton Annuler ; le joueur doit terminer le choix. Cela évite de consulter une information cachée gratuitement puis d’annuler, par exemple avec Aimant.',
    tag_desc_infinite_exclude: 'Mot-clé de mode. Cette carte est exclue de la réserve aléatoire d’Infinite Fire car elle entre en conflit avec ce mode.',
    tag_desc_copy: 'Mot-clé de pioche. Quand cette carte entre en main, ajoute N copies exilées.',
    tag_desc_unique: 'Mot-clé de deck. Une seule copie autorisée; les excédentaires sont exilées.',
    tag_desc_swift: 'Mot-clé de coût. Le coût E de cette carte est réduit de X (minimum 0E).',
    tag_desc_rebound: 'Mot-clé de résolution. Après avoir été jouée et résolue, cette carte revient immédiatement dans la main de son utilisateur.',
    tag_desc_default: 'Tag de mod ou d\'extension. Son sens exact est défini par le mod ou l\'effet de carte correspondant.',
    tag_desc_stealth: 'Mot-clé de réponse. Cette carte ne déclenche pas la fenêtre de réponse adverse.',
    tag_desc_revealed: 'Mot-clé de visibilité. Cette carte est visible en permanence pour l\'adversaire en main.'
});

Object.assign(I18N.pt, {
    tag_desc_precision: 'Palavra-chave de ataque. Um ataque com Precisão, ao ser esquivado, causa metade do dano em vez de falhar por completo.',
    tag_desc_exile: 'Palavra-chave de resolução. Esta carta vai para o exílio após ser jogada ou resolvida, em vez de ir para o descarte.',
    tag_desc_non_stackable: 'Palavra-chave de equipamento. Várias cópias podem ser equipadas, mas o mesmo efeito não acumula; cópias extras servem quando uma é destruída.',
    tag_desc_indestructible: 'Palavra-chave de equipamento. Este equipamento não pode ser destruído por efeitos de destruição e permanece quando o dono é derrotado.',
    tag_desc_sprout: 'Palavra-chave de compra. Ao ser comprada, esta carta compra cartas extras; limites de mão ainda se aplicam.',
    tag_desc_symbiosis: 'Palavra-chave de custo. Esta carta ignora penalidades de custo por cartas de mesmo nome.',
    tag_desc_attract: 'Palavra-chave de limite de mão. Quando a mão está cheia, cartas com Atração empurram primeiro cartas sem Atração.',
    tag_desc_void: 'Palavra-chave de fim de turno. Se esta carta ficar na mão no fim do turno, ela é exilada.',
    tag_desc_self_only: 'Palavra-chave de alvo. Esta carta não abre seleção de alvo; seu efeito resolve pelas próprias regras.',
    tag_desc_uncancellable: 'Palavra-chave de escolha. Janelas de escolha desta carta não mostram botão de cancelar; o jogador deve concluir a escolha. Isso evita ver informação oculta de graça e cancelar, como com Magnet.',
    tag_desc_infinite_exclude: 'Palavra-chave de modo. Esta carta não entra no conjunto aleatório de Infinite Fire por conflitar com esse modo.',
    tag_desc_copy: 'Palavra-chave de compra. Quando esta carta entra na mão, adicione N cópias exiladas.',
    tag_desc_unique: 'Palavra-chave de deck. Apenas uma cópia permitida; extras são exiladas.',
    tag_desc_swift: 'Palavra-chave de custo. O custo E desta carta é reduzido em X (mínimo 0E).',
    tag_desc_rebound: 'Palavra-chave de resolução. Depois de jogada e resolvida, esta carta volta imediatamente para a mão do usuário.',
    tag_desc_default: 'Tag de mod ou extensão. O significado exato é definido pelo mod ou pelo efeito da carta.',
    tag_desc_stealth: 'Palavra-chave de resposta. Esta carta não aciona a janela de resposta do oponente.',
    tag_desc_revealed: 'Palavra-chave de visibilidade. Esta carta é visível permanentemente para o oponente na mão.'
});


Object.assign(I18N.ja, {
    tag_desc_precision: '攻撃キーワード。精密攻撃が回避された場合、完全に失敗せず半分のダメージを与えます。',
    tag_desc_exile: '解決先キーワード。このカードはプレイまたは解決後、捨て札ではなく追放領域へ行きます。',
    tag_desc_non_stackable: '装備キーワード。複数装備できますが、同じ効果は重複しません。主に一つが破壊された後も効果を残すための予備です。',
    tag_desc_indestructible: '装備キーワード。この装備は破壊効果で破壊されず、持ち主が倒れても残ります。',
    tag_desc_sprout: 'ドローキーワード。引いたとき追加でカードを引きます。手札上限やあふれ処理は通常通りです。',
    tag_desc_symbiosis: 'コストキーワード。同名カード連続使用による費用ペナルティを受けません。',
    tag_desc_attract: '手札上限キーワード。手札が満杯のとき、吸引カードは吸引を持たないカードを優先して押し出します。',
    tag_desc_void: 'ターン終了キーワード。このカードがターン終了時に手札に残っている場合、追放されます。',
    tag_desc_self_only: '対象選択キーワード。このカードは使用時に対象選択を開かず、カード自身のルールで解決します。',
    tag_desc_uncancellable: '選択制限キーワード。このカードの選択画面にはキャンセルボタンが表示されず、必ず選択を完了します。Magnet のように0コストで非公開情報を見てからキャンセルすることを防ぎます。',
    tag_desc_infinite_exclude: 'モード制限キーワード。このカードは Infinite Fire のランダムカードプールに入りません。',
    tag_desc_copy: 'ドローキーワード。このカードが手札に入った時、追放コピーをN枚手札に加える。',
    tag_desc_unique: 'デッキキーワード。デッキに1枚のみ許可され、超過分は追放される。',
    tag_desc_swift: 'コストキーワード。このカードのE消費がX減少（最低0E）。',
    tag_desc_rebound: '解決先キーワード。打ち出して解決した後、ただちに使用者の手札へ戻ります。',
    tag_desc_default: 'Mod または拡張タグです。具体的な意味は対応する Mod またはカード効果で定義されます。',
    tag_desc_stealth: '応答キーワード。このカードは相手の応答ウィンドウをトリガーしません。',
    tag_desc_revealed: '可視性キーワード。このカードは手札にある間、相手に永久に表示されます。'
});

Object.assign(I18N.zh, {
    gallery_related_cards: '相关卡牌',
    tag_desc_fusion_layer: '特殊机制，不是普通标签。聚变层数与裂变层数共同决定攻击牌下一次打出时的结算：总伤害先按聚变层数放大，再按裂变层数拆成多次伤害，每次伤害为 ceil(原始伤害×聚变层数/裂变层数)。打出聚变时，选择2-3张同名攻击牌，将聚变层数相加，裂变层数取最大，合并为一张牌。牌进入弃牌堆后会恢复为默认聚变1。',
    tag_desc_fission_layer: '特殊机制，不是普通标签。裂变层数表示攻击牌打出时会拆成多少次结算，并与聚变层数共同作用：每次伤害为 ceil(原始伤害×聚变层数/裂变层数)。如果卡牌每次命中都会改变后续伤害，例如三角形，每一次裂变命中都会按当时的层数重新计算。牌进入弃牌堆后会恢复为默认裂变1。'
});
Object.assign(I18N.en, {
    gallery_related_cards: 'Related cards',
    tag_desc_fusion_layer: 'Special mechanic, not a normal tag. Fusion and Fission work together when an attack is next played: total damage is first scaled by Fusion, then split into Fission hits. Each hit deals ceil(base damage × Fusion / Fission). Playing Fusion chooses 2-3 same-name attacks, adds their Fusion levels, keeps the highest Fission level, and merges them into one card. When the card enters the discard pile, Fusion resets to the default 1.',
    tag_desc_fission_layer: 'Special mechanic, not a normal tag. Fission is the number of hits an attack is split into, and it works together with Fusion: each hit deals ceil(base damage × Fusion / Fission). If a card changes later damage after each hit, such as Triangle, every Fission hit recalculates from the current layer count. When the card enters the discard pile, Fission resets to the default 1.'
});
Object.assign(I18N.fr, {
    gallery_related_cards: 'Cartes liées',
    tag_desc_fusion_layer: 'Mécanique spéciale, pas un tag normal. Fusion et Fission agissent ensemble quand une attaque est jouée : les dégâts totaux sont d’abord multipliés par Fusion, puis divisés en plusieurs touches de Fission. Chaque touche inflige ceil(dégâts de base × Fusion / Fission). Jouer Fusion choisit 2-3 attaques de même nom, additionne leurs niveaux de Fusion, garde le plus haut niveau de Fission et les fusionne en une carte. Quand la carte va dans la défausse, Fusion revient à 1.',
    tag_desc_fission_layer: 'Mécanique spéciale, pas un tag normal. Fission indique en combien de touches une attaque est divisée, et agit avec Fusion : chaque touche inflige ceil(dégâts de base × Fusion / Fission). Si une carte modifie les dégâts suivants à chaque touche, comme Triangle, chaque touche de Fission recalcule avec les couches actuelles. Quand la carte va dans la défausse, Fission revient à 1.'
});
Object.assign(I18N.pt, {
    gallery_related_cards: 'Cartas relacionadas',
    tag_desc_fusion_layer: 'Mecânica especial, não é uma tag normal. Fusão e Fissão funcionam juntas quando um ataque é jogado: o dano total primeiro é multiplicado pela Fusão e depois dividido em golpes de Fissão. Cada golpe causa ceil(dano base × Fusão / Fissão). Jogar Fusão escolhe 2-3 ataques de mesmo nome, soma seus níveis de Fusão, mantém o maior nível de Fissão e une tudo em uma carta. Quando a carta entra no descarte, Fusão volta ao padrão 1.',
    tag_desc_fission_layer: 'Mecânica especial, não é uma tag normal. Fissão é o número de golpes em que um ataque é dividido, e funciona junto com Fusão: cada golpe causa ceil(dano base × Fusão / Fissão). Se uma carta muda o dano posterior a cada acerto, como Triângulo, cada golpe de Fissão recalcula com as camadas atuais. Quando a carta entra no descarte, Fissão volta ao padrão 1.'
});
Object.assign(I18N.ja, {
    gallery_related_cards: '関連カード',
    tag_desc_fusion_layer: '通常のタグではなく特殊な仕組みです。融合と分裂は攻撃カードを次に打ち出す時に共同で作用します。総ダメージはまず融合層で拡大され、その後分裂層の回数に分けられます。各ヒットは ceil(基礎ダメージ×融合/分裂) を与えます。融合を使うと同名攻撃カード2-3枚を選び、融合層を合計し、分裂層は最大値を取り、1枚のカードにします。カードが捨て札に入ると融合は既定値1に戻ります。',
    tag_desc_fission_layer: '通常のタグではなく特殊な仕組みです。分裂層は攻撃カードが何回に分かれて解決されるかを表し、融合層と共同で作用します。各ヒットは ceil(基礎ダメージ×融合/分裂) を与えます。三角形のようにヒットごとに以後のダメージが変わるカードは、各分裂ヒットでその時点の層数を使って再計算します。カードが捨て札に入ると分裂は既定値1に戻ります。'
});

Object.assign(I18N.en, { settings_show_english_card_names: 'Show English card names', settings_show_card_images: 'Show card images' });
Object.assign(I18N.zh, { settings_show_english_card_names: '显示卡牌英文名称', settings_show_card_images: '显示卡牌图片' });
Object.assign(I18N.fr, { settings_show_english_card_names: 'Afficher les noms anglais des cartes', settings_show_card_images: 'Afficher les images des cartes' });
Object.assign(I18N.pt, { settings_show_english_card_names: 'Mostrar nomes ingleses das cartas', settings_show_card_images: 'Mostrar imagens das cartas' });
Object.assign(I18N.ja, { settings_show_english_card_names: '英語のカード名を表示', settings_show_card_images: 'カード画像を表示' });
Object.assign(I18N.en, { official_mods: 'Official Mods', community_mods: 'Community Mods', upload_mod: 'Upload Mod', refresh: 'Refresh', no_community_mods: 'No community mods found', mod_beta_warning: 'In testing, not recommended' });
Object.assign(I18N.zh, { official_mods: '官方模组', community_mods: '社区模组', upload_mod: '上传模组', refresh: '刷新', no_community_mods: '未找到社区模组', mod_beta_warning: '测试中，不推荐使用' });
Object.assign(I18N.fr, { mod_beta_warning: 'En test, déconseillé' });
Object.assign(I18N.pt, { mod_beta_warning: 'Em teste, não recomendado' });
Object.assign(I18N.ja, { mod_beta_warning: 'テスト中、非推奨' });
Object.assign(I18N.en, {
    community_current: 'Current community mod', community_disabled: 'Disabled', community_disable: 'Disable community mod',
    community_upload_hint: 'Sign in to upload. The file is sent directly to the community mod store.',
    community_login_required: 'Sign in with an account before uploading community mods.',
    community_select: 'Use', community_selected: 'Selected', community_update: 'Update', community_delete: 'Delete',
    community_owned_by_you: 'Yours', community_uploaded_at: 'Uploaded {0}', community_delete_confirm: 'Delete this community mod?',
    community_uploading: 'Uploading...', community_upload_success: 'Uploaded: {0}', community_update_success: 'Updated: {0}',
    community_delete_success: 'Deleted community mod', community_file_summary: '{0} · v{1} · {2} cards', community_cards_count: '{0} cards'
});
Object.assign(I18N.zh, {
    community_current: '当前社区模组', community_disabled: '未启用', community_disable: '停用社区模组',
    community_upload_hint: '上传需要登录账号，文件会直接上传到社区模组仓库。',
    community_login_required: '请先登录账号，再上传社区模组。',
    community_select: '使用', community_selected: '已选择', community_update: '上传更新', community_delete: '删除',
    community_owned_by_you: '你上传的', community_uploaded_at: '上传于 {0}', community_delete_confirm: '确定删除这个社区模组吗？',
    community_uploading: '正在上传...', community_upload_success: '上传成功：{0}', community_update_success: '更新成功：{0}',
    community_delete_success: '已删除社区模组', community_file_summary: '{0} · v{1} · {2} 张卡牌', community_cards_count: '{0} 张卡牌'
});
Object.assign(I18N.fr, {
    community_current: 'Mod communautaire actuel', community_disabled: 'Désactivé', community_disable: 'Désactiver',
    community_upload_hint: 'Connectez-vous pour téléverser. Le fichier va directement dans le stockage communautaire.',
    community_login_required: 'Connectez-vous avant de téléverser un mod communautaire.',
    community_select: 'Utiliser', community_selected: 'Sélectionné', community_update: 'Mettre à jour', community_delete: 'Supprimer',
    community_owned_by_you: 'À vous', community_uploaded_at: 'Envoyé {0}', community_delete_confirm: 'Supprimer ce mod ?',
    community_uploading: 'Téléversement...', community_upload_success: 'Téléversé : {0}', community_update_success: 'Mis à jour : {0}',
    community_delete_success: 'Mod supprimé', community_file_summary: '{0} · v{1} · {2} cartes', community_cards_count: '{0} cartes'
});
Object.assign(I18N.pt, {
    community_current: 'Mod comunitário atual', community_disabled: 'Desativado', community_disable: 'Desativar',
    community_upload_hint: 'Entre para enviar. O arquivo vai direto para o armazenamento da comunidade.',
    community_login_required: 'Entre com uma conta antes de enviar mods comunitários.',
    community_select: 'Usar', community_selected: 'Selecionado', community_update: 'Atualizar', community_delete: 'Excluir',
    community_owned_by_you: 'Seu', community_uploaded_at: 'Enviado {0}', community_delete_confirm: 'Excluir este mod?',
    community_uploading: 'Enviando...', community_upload_success: 'Enviado: {0}', community_update_success: 'Atualizado: {0}',
    community_delete_success: 'Mod excluído', community_file_summary: '{0} · v{1} · {2} cartas', community_cards_count: '{0} cartas'
});
Object.assign(I18N.ja, {
    community_current: '現在のコミュニティMod', community_disabled: '未使用', community_disable: 'コミュニティModを無効化',
    community_upload_hint: 'アップロードにはログインが必要です。ファイルは直接コミュニティMod保存先へ送信されます。',
    community_login_required: 'コミュニティModをアップロードする前にログインしてください。',
    community_select: '使用', community_selected: '選択中', community_update: '更新', community_delete: '削除',
    community_owned_by_you: '自分のMod', community_uploaded_at: 'アップロード {0}', community_delete_confirm: 'このModを削除しますか？',
    community_uploading: 'アップロード中...', community_upload_success: 'アップロード成功：{0}', community_update_success: '更新成功：{0}',
    community_delete_success: 'コミュニティModを削除しました', community_file_summary: '{0} · v{1} · {2}枚', community_cards_count: '{0}枚'
});
Object.assign(I18N.en, { community_upload: 'Upload mod', community_json_only: 'Only .json or .gtnmod files are allowed', community_file_too_large: 'File is too large. JSON max 150KB, GTNMOD max 1MB', community_json_parse_failed: 'JSON parse failed: {0}', community_upload_url_failed: 'Could not create upload URL', community_r2_upload_failed: 'R2 upload failed: HTTP {0}', community_register_failed: 'Registration failed', community_delete_failed: 'Delete failed' });
Object.assign(I18N.zh, { community_upload: '上传模组', community_json_only: '只允许上传 .json 或 .gtnmod 文件', community_file_too_large: '文件过大，JSON 最大 150KB，GTNMOD 最大 1MB', community_json_parse_failed: 'JSON 解析失败：{0}', community_upload_url_failed: '无法创建上传地址', community_r2_upload_failed: 'R2 上传失败 HTTP {0}', community_register_failed: '登记失败', community_delete_failed: '删除失败' });
Object.assign(I18N.fr, { community_upload: 'Téléverser', community_json_only: 'Seuls les fichiers .json ou .gtnmod sont autorisés', community_file_too_large: 'Fichier trop volumineux. JSON 300 Ko, GTNMOD 5 Mo', community_json_parse_failed: 'Échec d’analyse JSON : {0}', community_upload_url_failed: 'Impossible de créer l’URL de téléversement', community_r2_upload_failed: 'Échec R2 : HTTP {0}', community_register_failed: 'Échec d’enregistrement', community_delete_failed: 'Échec de suppression' });
Object.assign(I18N.pt, { community_upload: 'Enviar mod', community_json_only: 'Somente arquivos .json ou .gtnmod são permitidos', community_file_too_large: 'Arquivo grande demais. JSON 150KB, GTNMOD 1MB', community_json_parse_failed: 'Falha ao ler JSON: {0}', community_upload_url_failed: 'Não foi possível criar URL de envio', community_r2_upload_failed: 'Falha no R2: HTTP {0}', community_register_failed: 'Falha ao registrar', community_delete_failed: 'Falha ao excluir' });
Object.assign(I18N.ja, { community_upload: 'Modをアップロード', community_json_only: '.json または .gtnmod のみアップロードできます', community_file_too_large: 'ファイルが大きすぎます。JSON 最大150KB、GTNMOD 最大1MB', community_json_parse_failed: 'JSON 解析失敗：{0}', community_upload_url_failed: 'アップロードURLを作成できません', community_r2_upload_failed: 'R2 アップロード失敗 HTTP {0}', community_register_failed: '登録失敗', community_delete_failed: '削除失敗' });
Object.assign(I18N.en, { community_upload_progress: '{0}/{1} · {2}/s · ETA {3}', community_upload_registering: 'Registering and validating...' });
Object.assign(I18N.zh, { community_upload_progress: '{0}/{1} · {2}/秒 · 预计剩余 {3}', community_upload_registering: '正在登记并校验...' });
Object.assign(I18N.fr, { community_upload_progress: '{0}/{1} · {2}/s · reste {3}', community_upload_registering: 'Enregistrement et validation...' });
Object.assign(I18N.pt, { community_upload_progress: '{0}/{1} · {2}/s · restante {3}', community_upload_registering: 'Registrando e validando...' });
Object.assign(I18N.ja, { community_upload_progress: '{0}/{1} · {2}/秒 · 残り {3}', community_upload_registering: '登録と検証中...' });
Object.assign(I18N.en, { mod_validation_error: 'Format error' });
Object.assign(I18N.zh, { mod_validation_error: '格式错误' });
Object.assign(I18N.fr, { mod_validation_error: 'Erreur de format' });
Object.assign(I18N.pt, { mod_validation_error: 'Erro de formato' });
Object.assign(I18N.ja, { mod_validation_error: '形式エラー' });
Object.assign(I18N.en, { admin_prefix: 'Admin', login_admin_reserved: 'This nickname is occupied by the administrator' });
Object.assign(I18N.zh, { admin_prefix: '管理员', login_admin_reserved: '此昵称被管理员占用' });
Object.assign(I18N.fr, { admin_prefix: 'Admin', login_admin_reserved: 'Ce pseudo est occupé par l’administrateur' });
Object.assign(I18N.pt, { admin_prefix: 'Administrador', login_admin_reserved: 'Este apelido está ocupado pelo administrador' });
Object.assign(I18N.ja, { admin_prefix: '管理者', login_admin_reserved: 'このニックネームは管理者が使用しています' });
Object.assign(I18N.en, { chat_rate_limited: 'Chat rate limit reached. Please wait.' });
Object.assign(I18N.zh, { chat_rate_limited: '聊天发送过快，请稍后再试。' });
Object.assign(I18N.fr, { chat_rate_limited: 'Messages trop fréquents. Veuillez patienter.' });
Object.assign(I18N.pt, { chat_rate_limited: 'Mensagens muito frequentes. Aguarde um pouco.' });
Object.assign(I18N.ja, { chat_rate_limited: 'チャットの送信が速すぎます。少し待ってください。' });
Object.assign(I18N.en, {
    account: 'Account', account_guest: 'Guest Mode', account_username: 'Username', account_password: 'Password',
    account_password_confirm: 'Confirm Password', account_old_password: 'Current Password', account_new_password: 'New Password',
    account_new_password_confirm: 'Confirm New Password', account_change_password: 'Change Password', account_password_changed: 'Password changed',
    account_login: 'Log In', account_register: 'Register', account_enter: 'Enter with Account', account_logout: 'Log Out',
    account_not_logged_in: 'Not logged in', account_logged_in_as: 'Signed in as {0}', account_stats: 'Games {0} / Wins {1} / Losses {2} / Draws {3}',
    account_need_login: 'Log in or register first', account_error: 'Account error', account_password_mismatch: 'Passwords do not match', guest_enter: 'Enter as Guest',
    login_registered_reserved: 'This nickname belongs to a registered account'
});
Object.assign(I18N.zh, {
    account: '账号', account_guest: '游客模式', account_username: '用户名', account_password: '密码',
    account_password_confirm: '确认密码', account_old_password: '原密码', account_new_password: '新密码',
    account_new_password_confirm: '确认新密码', account_change_password: '修改密码', account_password_changed: '密码已修改',
    account_login: '登录', account_register: '注册', account_enter: '账号进入', account_logout: '退出登录',
    account_not_logged_in: '未登录', account_logged_in_as: '已登录：{0}', account_stats: '对局 {0} / 胜 {1} / 负 {2} / 平 {3}',
    account_need_login: '请先登录或注册账号', account_error: '账号错误', account_password_mismatch: '两次输入的密码不一致', guest_enter: '游客进入',
    login_registered_reserved: '此昵称属于已注册账号'
});
Object.assign(I18N.fr, {
    account: 'Compte', account_guest: 'Mode invité', account_username: 'Nom', account_password: 'Mot de passe',
    account_password_confirm: 'Confirmer', account_old_password: 'Mot de passe actuel', account_new_password: 'Nouveau mot de passe',
    account_new_password_confirm: 'Confirmer le nouveau', account_change_password: 'Changer le mot de passe', account_password_changed: 'Mot de passe changé',
    account_login: 'Connexion', account_register: 'Inscription', account_enter: 'Entrer avec le compte', account_logout: 'Déconnexion',
    account_not_logged_in: 'Non connecté', account_logged_in_as: 'Connecté : {0}', account_stats: 'Parties {0} / V {1} / D {2} / N {3}',
    account_need_login: 'Connectez-vous ou inscrivez-vous', account_error: 'Erreur de compte', account_password_mismatch: 'Les mots de passe ne correspondent pas', guest_enter: 'Entrer en invité',
    login_registered_reserved: 'Ce pseudo appartient à un compte'
});
Object.assign(I18N.pt, {
    account: 'Conta', account_guest: 'Modo convidado', account_username: 'Usuário', account_password: 'Senha',
    account_password_confirm: 'Confirmar senha', account_old_password: 'Senha atual', account_new_password: 'Nova senha',
    account_new_password_confirm: 'Confirmar nova senha', account_change_password: 'Alterar senha', account_password_changed: 'Senha alterada',
    account_login: 'Entrar', account_register: 'Registrar', account_enter: 'Entrar com conta', account_logout: 'Sair',
    account_not_logged_in: 'Não conectado', account_logged_in_as: 'Conectado: {0}', account_stats: 'Jogos {0} / V {1} / D {2} / E {3}',
    account_need_login: 'Entre ou registre-se primeiro', account_error: 'Erro da conta', account_password_mismatch: 'As senhas não coincidem', guest_enter: 'Entrar como convidado',
    login_registered_reserved: 'Este nome pertence a uma conta'
});
Object.assign(I18N.ja, {
    account: 'アカウント', account_guest: 'ゲスト', account_username: 'ユーザー名', account_password: 'パスワード',
    account_password_confirm: '確認', account_old_password: '現在のパスワード', account_new_password: '新しいパスワード',
    account_new_password_confirm: '新しい確認', account_change_password: 'パスワード変更', account_password_changed: '変更しました',
    account_login: 'ログイン', account_register: '登録', account_enter: 'アカウントで入る', account_logout: 'ログアウト',
    account_not_logged_in: '未ログイン', account_logged_in_as: 'ログイン中: {0}', account_stats: '対戦 {0} / 勝 {1} / 負 {2} / 引分 {3}',
    account_need_login: '先にログインまたは登録してください', account_error: 'アカウントエラー', account_password_mismatch: 'パスワードが一致しません', guest_enter: 'ゲストで入る',
    login_registered_reserved: 'この名前は登録済みアカウントです'
});
Object.assign(I18N.en, {
    skin: 'Skin', skin_title: 'Skin', skin_primary_color: 'Main Color', skin_eye_shape: 'Eye Shape',
    skin_eye_oval: 'Oval', skin_eye_rectangle: 'Rectangle', skin_eye_diamond: 'Diamond', skin_eye_hexagon: 'Hexagon',
    skin_face_layout_placeholder: 'Face Layout: coming soon', skin_face_shape_placeholder: 'Face Shape: coming soon',
    skin_sync_guest: 'Guest skin is saved locally. Account skin is saved on the server.',
    skin_save: 'Save', skin_reset: 'Reset', skin_saved: 'Skin saved'
});
Object.assign(I18N.zh, {
    skin: '皮肤', skin_title: '皮肤', skin_primary_color: '主颜色', skin_eye_shape: '眼睛形状',
    skin_eye_oval: '椭圆', skin_eye_rectangle: '长方形', skin_eye_diamond: '菱形', skin_eye_hexagon: '六边形',
    skin_face_layout_placeholder: '脸部布局：暂未开放', skin_face_shape_placeholder: '脸型：暂未开放',
    skin_sync_guest: '游客皮肤会保存在本地；账号皮肤会保存到服务器。',
    skin_save: '保存', skin_reset: '恢复默认', skin_saved: '皮肤已保存'
});
Object.assign(I18N.fr, {
    skin: 'Apparence', skin_title: 'Apparence', skin_primary_color: 'Couleur', skin_eye_shape: 'Yeux',
    skin_eye_oval: 'Ovale', skin_eye_rectangle: 'Rectangle', skin_eye_diamond: 'Losange', skin_eye_hexagon: 'Hexagone',
    skin_face_layout_placeholder: 'Disposition du visage : bientôt', skin_face_shape_placeholder: 'Forme du visage : bientôt',
    skin_sync_guest: 'Invité : local. Compte : serveur.',
    skin_save: 'Enregistrer', skin_reset: 'Réinitialiser', skin_saved: 'Apparence enregistrée'
});
Object.assign(I18N.pt, {
    skin: 'Visual', skin_title: 'Visual', skin_primary_color: 'Cor', skin_eye_shape: 'Olhos',
    skin_eye_oval: 'Oval', skin_eye_rectangle: 'Retângulo', skin_eye_diamond: 'Diamante', skin_eye_hexagon: 'Hexágono',
    skin_face_layout_placeholder: 'Layout do rosto: em breve', skin_face_shape_placeholder: 'Formato do rosto: em breve',
    skin_sync_guest: 'Convidado: local. Conta: servidor.',
    skin_save: 'Salvar', skin_reset: 'Redefinir', skin_saved: 'Visual salvo'
});
Object.assign(I18N.ja, {
    skin: 'スキン', skin_title: 'スキン', skin_primary_color: 'メイン色', skin_eye_shape: '目の形',
    skin_eye_oval: '楕円', skin_eye_rectangle: '長方形', skin_eye_diamond: 'ひし形', skin_eye_hexagon: '六角形',
    skin_face_layout_placeholder: '顔レイアウト：準備中', skin_face_shape_placeholder: '顔の形：準備中',
    skin_sync_guest: 'ゲストはローカル保存、アカウントはサーバー保存です。',
    skin_save: '保存', skin_reset: '初期化', skin_saved: 'スキンを保存しました'
});
Object.assign(I18N.en, {
    friends: 'Friends', player_id: 'ID', friend_add_placeholder: 'Nickname or ID', friend_add: 'Add',
    friend_requests: 'Friend Requests', friend_sent: 'Sent', friend_list: 'My Friends',
    friend_accept: 'Accept', friend_decline: 'Decline', friend_ignore: 'Ignore', friend_remove: 'Remove',
    friend_empty: 'No friends yet.', friend_request_empty: 'No pending requests.', friend_sent_empty: 'No sent requests.',
    friend_added: 'Friend request sent', friend_added_direct: 'Friend added', friend_removed: 'Friend removed', friend_updated: 'Updated', friend_remove_confirm: 'Remove this friend?',
    friend_auto_added: '{0} added you as a friend',
    social: 'Social', social_login_hint: 'Sign in to use social settings.',
    social_accept_requests: 'Accept friend requests', social_search_nickname: 'Allow adding me by nickname',
    social_search_id: 'Allow adding me by ID', social_settings_saved: 'Social settings saved',
    last_login: 'Last seen: {0}', win_rate: 'Win rate: {0}%', recent_matches: 'Recent matches',
    friend_profile: 'Profile', direct_messages: 'Direct Messages'
});
Object.assign(I18N.zh, {
    friends: '好友', player_id: 'ID', friend_add_placeholder: '输入昵称或ID', friend_add: '添加',
    friend_requests: '好友请求', friend_sent: '已发送', friend_list: '我的好友',
    friend_accept: '同意', friend_decline: '拒绝', friend_ignore: '忽略', friend_remove: '删除',
    friend_empty: '暂无好友。', friend_request_empty: '暂无好友请求。', friend_sent_empty: '暂无已发送请求。',
    friend_added: '好友请求已发送', friend_added_direct: '已添加好友', friend_removed: '好友已删除', friend_updated: '已更新', friend_remove_confirm: '确认删除这个好友吗？',
    friend_auto_added: '{0}已加你为好友',
    social: '社交', social_login_hint: '登录账号后可以使用社交设置。',
    social_accept_requests: '接受好友请求', social_search_nickname: '允许通过昵称添加我',
    social_search_id: '允许通过ID添加我', social_settings_saved: '社交设置已保存',
    last_login: '上次下线：{0}', win_rate: '胜率：{0}%', recent_matches: '最近对局',
    friend_profile: '资料', direct_messages: '私信'
});
Object.assign(I18N.fr, {
    friends: 'Amis', player_id: 'ID', friend_add_placeholder: 'Pseudo ou ID', friend_add: 'Ajouter',
    friend_requests: 'Demandes', friend_sent: 'Envoyées', friend_list: 'Mes amis',
    friend_accept: 'Accepter', friend_decline: 'Refuser', friend_ignore: 'Ignorer', friend_remove: 'Retirer',
    friend_empty: 'Aucun ami.', friend_request_empty: 'Aucune demande.', friend_sent_empty: 'Aucune demande envoyée.',
    friend_added: 'Demande envoyée', friend_added_direct: 'Ami ajouté', friend_removed: 'Ami retiré', friend_updated: 'Mis à jour', friend_remove_confirm: 'Retirer cet ami ?',
    friend_auto_added: '{0} vous a ajouté en ami',
    social: 'Social', social_login_hint: 'Connectez-vous pour utiliser les réglages sociaux.',
    social_accept_requests: 'Accepter les demandes', social_search_nickname: 'Autoriser par pseudo',
    social_search_id: 'Autoriser par ID', social_settings_saved: 'Réglages enregistrés',
    last_login: 'Dernière activité : {0}', win_rate: 'Taux de victoire : {0}%', recent_matches: 'Parties récentes',
    friend_profile: 'Profil', direct_messages: 'Messages'
});
Object.assign(I18N.pt, {
    friends: 'Amigos', player_id: 'ID', friend_add_placeholder: 'Apelido ou ID', friend_add: 'Adicionar',
    friend_requests: 'Pedidos', friend_sent: 'Enviados', friend_list: 'Meus amigos',
    friend_accept: 'Aceitar', friend_decline: 'Recusar', friend_ignore: 'Ignorar', friend_remove: 'Remover',
    friend_empty: 'Sem amigos.', friend_request_empty: 'Sem pedidos.', friend_sent_empty: 'Sem pedidos enviados.',
    friend_added: 'Pedido enviado', friend_added_direct: 'Amigo adicionado', friend_removed: 'Amigo removido', friend_updated: 'Atualizado', friend_remove_confirm: 'Remover este amigo?',
    friend_auto_added: '{0} adicionou você como amigo',
    social: 'Social', social_login_hint: 'Entre para usar configurações sociais.',
    social_accept_requests: 'Aceitar pedidos', social_search_nickname: 'Permitir por apelido',
    social_search_id: 'Permitir por ID', social_settings_saved: 'Configurações salvas',
    last_login: 'Visto por último: {0}', win_rate: 'Vitórias: {0}%', recent_matches: 'Partidas recentes',
    friend_profile: 'Perfil', direct_messages: 'Mensagens'
});
Object.assign(I18N.ja, {
    friends: 'フレンド', player_id: 'ID', friend_add_placeholder: '名前またはID', friend_add: '追加',
    friend_requests: '申請', friend_sent: '送信済み', friend_list: 'フレンド',
    friend_accept: '承認', friend_decline: '拒否', friend_ignore: '無視', friend_remove: '削除',
    friend_empty: 'フレンドはいません。', friend_request_empty: '申請はありません。', friend_sent_empty: '送信済み申請はありません。',
    friend_added: '申請を送信しました', friend_added_direct: 'フレンドを追加しました', friend_removed: '削除しました', friend_updated: '更新しました', friend_remove_confirm: 'このフレンドを削除しますか？',
    friend_auto_added: '{0}があなたをフレンドに追加しました',
    social: 'ソーシャル', social_login_hint: 'ログインするとソーシャル設定を使えます。',
    social_accept_requests: 'フレンド申請を受け取る', social_search_nickname: '名前で追加を許可',
    social_search_id: 'IDで追加を許可', social_settings_saved: '設定を保存しました',
    last_login: '最終退出: {0}', win_rate: '勝率: {0}%', recent_matches: '最近の対戦',
    friend_profile: 'プロフィール', direct_messages: 'DM'
});
Object.assign(I18N.en, {
    account_replays: 'Recent Replays', replay_viewer: 'Replay Viewer', replay_view: 'View',
    replay_empty: 'No replay in the last 90 days.', replay_loading: 'Loading replays...',
    replay_load_failed: 'Failed to load replay', replay_prev: 'Prev', replay_play: 'Play',
    replay_pause: 'Pause', replay_next: 'Next', replay_instant: 'Instant',
    replay_winner: 'Winner: {0}', replay_round: 'Round {0}', replay_frame_empty: 'No timeline data.',
    replay_loading_progress: 'Loaded {0}/{1} frames', replay_prepare: 'Preparing replay...'
});
Object.assign(I18N.zh, {
    account_replays: '最近回放', replay_viewer: '回放查看器', replay_view: '查看',
    replay_empty: '最近90天暂无回放。', replay_loading: '正在读取回放...',
    replay_load_failed: '回放加载失败', replay_prev: '上一步', replay_play: '播放',
    replay_pause: '暂停', replay_next: '下一步', replay_instant: '立即',
    replay_winner: '胜者：{0}', replay_round: '第{0}回合', replay_frame_empty: '暂无时间线数据。',
    replay_loading_progress: '已加载 {0}/{1} 帧', replay_prepare: '正在准备回放...'
});
Object.assign(I18N.fr, {
    account_replays: 'Replays récents', replay_viewer: 'Lecteur de replay', replay_view: 'Voir',
    replay_empty: 'Aucun replay sur 90 jours.', replay_loading: 'Chargement...',
    replay_load_failed: 'Échec du replay', replay_prev: 'Préc.', replay_play: 'Lire',
    replay_pause: 'Pause', replay_next: 'Suiv.', replay_instant: 'Instant',
    replay_winner: 'Vainqueur : {0}', replay_round: 'Tour {0}', replay_frame_empty: 'Aucune timeline.',
    replay_loading_progress: '{0}/{1} frames chargées', replay_prepare: 'Préparation du replay...'
});
Object.assign(I18N.pt, {
    account_replays: 'Replays recentes', replay_viewer: 'Visualizador', replay_view: 'Ver',
    replay_empty: 'Nenhum replay em 90 dias.', replay_loading: 'Carregando...',
    replay_load_failed: 'Falha ao carregar replay', replay_prev: 'Anterior', replay_play: 'Reproduzir',
    replay_pause: 'Pausar', replay_next: 'Próximo', replay_instant: 'Instantâneo',
    replay_winner: 'Vencedor: {0}', replay_round: 'Rodada {0}', replay_frame_empty: 'Sem timeline.',
    replay_loading_progress: '{0}/{1} quadros carregados', replay_prepare: 'Preparando replay...'
});
Object.assign(I18N.ja, {
    account_replays: '最近のリプレイ', replay_viewer: 'リプレイビューア', replay_view: '表示',
    replay_empty: '90日以内のリプレイはありません。', replay_loading: '読み込み中...',
    replay_load_failed: 'リプレイ読み込み失敗', replay_prev: '前へ', replay_play: '再生',
    replay_pause: '一時停止', replay_next: '次へ', replay_instant: '即時',
    replay_winner: '勝者: {0}', replay_round: 'ラウンド {0}', replay_frame_empty: 'タイムラインなし。',
    replay_loading_progress: '{0}/{1}フレーム読込済み', replay_prepare: 'リプレイ準備中...'
});
Object.assign(I18N.en, { chief_designer_prefix: 'Chief Designer' });
Object.assign(I18N.zh, { admin_prefix: '\u7ba1\u7406\u5458', login_admin_reserved: '\u6b64\u6635\u79f0\u88ab\u7ba1\u7406\u5458\u5360\u7528' });
Object.assign(I18N.en, { console_prefix: 'Console' });
Object.assign(I18N.zh, { console_prefix: '\u63a7\u5236\u53f0' });
Object.assign(I18N.fr, { console_prefix: 'Console' });
Object.assign(I18N.pt, { console_prefix: 'Console' });
Object.assign(I18N.ja, { console_prefix: 'Console' });
Object.assign(I18N.zh, { chief_designer_prefix: '\u603b\u8bbe\u8ba1\u5e08' });
Object.assign(I18N.fr, { chief_designer_prefix: 'Concepteur en chef' });
Object.assign(I18N.pt, { chief_designer_prefix: 'Designer-chefe' });
Object.assign(I18N.ja, { chief_designer_prefix: 'Chief Designer' });
Object.assign(I18N.en, { right_angle_person_prefix: 'Right-Angle Person' });
Object.assign(I18N.zh, { right_angle_person_prefix: '\u76f4\u89d2\u4eba' });
Object.assign(I18N.fr, { right_angle_person_prefix: 'Personne angle droit' });
Object.assign(I18N.pt, { right_angle_person_prefix: 'Pessoa de ângulo reto' });
Object.assign(I18N.ja, { right_angle_person_prefix: '直角人' });
Object.assign(I18N.en, { settings_ui_style: 'UI Style', ui_style_minimal: 'Minimal', ui_style_classic: 'Classic' });
Object.assign(I18N.zh, { settings_ui_style: '界面风格', ui_style_minimal: '简约', ui_style_classic: '经典' });
Object.assign(I18N.fr, { settings_ui_style: 'Style UI', ui_style_minimal: 'Minimal', ui_style_classic: 'Classique' });
Object.assign(I18N.pt, { settings_ui_style: 'Estilo da UI', ui_style_minimal: 'Minimalista', ui_style_classic: 'Clássico' });
Object.assign(I18N.ja, { settings_ui_style: 'UIスタイル', ui_style_minimal: 'ミニマル', ui_style_classic: 'クラシック' });
Object.assign(I18N.en, { mimic_extra_cost: 'Cost {0}E' });
Object.assign(I18N.zh, { mimic_extra_cost: '\u6d88\u8017 {0}E' });
Object.assign(I18N.fr, { mimic_extra_cost: 'Co\u00fbt {0}E' });
Object.assign(I18N.pt, { mimic_extra_cost: 'Custo {0}E' });
Object.assign(I18N.ja, { mimic_extra_cost: '\u6d88\u8cbb {0}E' });
Object.assign(I18N.en, { spectate_unavailable: 'Not spectatable yet' });
Object.assign(I18N.zh, { spectate_unavailable: '\u6682\u4e0d\u80fd\u89c2\u6218' });
Object.assign(I18N.fr, { spectate_unavailable: 'Observation indisponible' });
Object.assign(I18N.pt, { spectate_unavailable: 'Ainda indispon\u00edvel' });
Object.assign(I18N.ja, { spectate_unavailable: '\u307e\u3060\u89b3\u6226\u3067\u304d\u307e\u305b\u3093' });
Object.assign(I18N.en, {
    tutorial_player_you: 'You', tutorial_player_opponent: 'Practice Opponent',
    error_urf_equip_limit: 'Infinite Fire equipment limit is {0}. Sell equipment first.',
    error_urf_replace_used: 'You already replaced a card this turn',
    error_urf_sell_used: 'You already sold equipment this turn',
    error_indestructible_sell: 'Indestructible equipment cannot be sold',
    error_invalid_player: 'Invalid player',
    error_not_draft_phase: 'Not in draft phase',
    error_no_reroll: 'No rerolls remaining',
    error_no_pending_ally_consent: 'No pending teammate card-use request',
    error_card_not_in_options: 'That card is not in the options',
    error_card_not_in_hand_alt: 'That card is not in hand',
    error_target_self_forbidden: 'You cannot choose yourself as the target',
    error_target_alive_required: 'Choose a living player',
    error_equipment_friendly_turn_only: 'Equipment can only be triggered on an allied turn',
    error_game_already_over: 'The game is already over',
});
Object.assign(I18N.zh, {
    tutorial_player_you: '你', tutorial_player_opponent: '练习对手',
    error_urf_equip_limit: '无限火力装备上限为 {0}，请先售卖装备',
    error_urf_replace_used: '本回合已经替换过手牌',
    error_urf_sell_used: '本回合已经售卖过装备',
    error_indestructible_sell: '不可摧毁装备不能被售卖',
    error_invalid_player: '无效玩家',
    error_not_draft_phase: '不在选牌阶段',
    error_no_reroll: '没有重选次数',
    error_no_pending_ally_consent: '没有待同意的队友用牌',
    error_card_not_in_options: '该牌不在选项中',
    error_card_not_in_hand_alt: '手牌中没有这张牌',
    error_target_self_forbidden: '不能选择自己作为目标',
    error_target_alive_required: '必须选择一名存活玩家',
    error_equipment_friendly_turn_only: '只能在友方回合触发装备',
    error_game_already_over: '游戏已经结束',
});
Object.assign(I18N.fr, {
    tutorial_player_you: 'Vous', tutorial_player_opponent: 'Adversaire d’entraînement',
    error_urf_equip_limit: 'Limite d’équipement Infinite Fire : {0}. Vendez d’abord un équipement.',
    error_urf_replace_used: 'Vous avez déjà remplacé une carte ce tour-ci',
    error_urf_sell_used: 'Vous avez déjà vendu un équipement ce tour-ci',
    error_indestructible_sell: 'Un équipement indestructible ne peut pas être vendu',
    error_invalid_player: 'Joueur invalide',
    error_not_draft_phase: 'Pas en phase de sélection',
    error_no_reroll: 'Aucune relance restante',
    error_no_pending_ally_consent: 'Aucune demande alliée en attente',
    error_card_not_in_options: 'Cette carte n’est pas dans les options',
    error_card_not_in_hand_alt: 'Cette carte n’est pas en main',
    error_target_self_forbidden: 'Vous ne pouvez pas vous choisir comme cible',
    error_target_alive_required: 'Choisissez un joueur vivant',
    error_equipment_friendly_turn_only: 'L’équipement ne peut être déclenché que pendant un tour allié',
    error_game_already_over: 'La partie est déjà terminée',
});
Object.assign(I18N.pt, {
    tutorial_player_you: 'Você', tutorial_player_opponent: 'Oponente de treino',
    error_urf_equip_limit: 'Limite de equipamentos do Infinite Fire: {0}. Venda um equipamento primeiro.',
    error_urf_replace_used: 'Você já substituiu uma carta neste turno',
    error_urf_sell_used: 'Você já vendeu um equipamento neste turno',
    error_indestructible_sell: 'Equipamento indestrutível não pode ser vendido',
    error_invalid_player: 'Jogador inválido',
    error_not_draft_phase: 'Não está na fase de escolha',
    error_no_reroll: 'Sem rerrolagens restantes',
    error_no_pending_ally_consent: 'Nenhuma solicitação de aliado pendente',
    error_card_not_in_options: 'Esta carta não está nas opções',
    error_card_not_in_hand_alt: 'Esta carta não está na mão',
    error_target_self_forbidden: 'Você não pode escolher a si mesmo como alvo',
    error_target_alive_required: 'Escolha um jogador vivo',
    error_equipment_friendly_turn_only: 'Equipamentos só podem ser acionados em turno aliado',
    error_game_already_over: 'A partida já terminou',
});
Object.assign(I18N.ja, {
    tutorial_player_you: 'あなた', tutorial_player_opponent: '練習相手',
    error_urf_equip_limit: 'Infinite Fire の装備上限は {0} です。先に装備を売却してください。',
    error_urf_replace_used: 'このターンはすでに手札を入れ替えました',
    error_urf_sell_used: 'このターンはすでに装備を売却しました',
    error_indestructible_sell: '破壊不可の装備は売却できません',
    error_invalid_player: '無効なプレイヤーです',
    error_not_draft_phase: '選択フェーズではありません',
    error_no_reroll: 'リロール回数がありません',
    error_no_pending_ally_consent: '保留中の味方カード使用確認はありません',
    error_card_not_in_options: 'そのカードは選択肢にありません',
    error_card_not_in_hand_alt: 'そのカードは手札にありません',
    error_target_self_forbidden: '自分を対象に選べません',
    error_target_alive_required: '生存しているプレイヤーを選んでください',
    error_equipment_friendly_turn_only: '装備は味方ターン中のみ発動できます',
    error_game_already_over: 'ゲームはすでに終了しています',
});

Object.assign(I18N.en, {
    compact_end_turn: 'End',
    compact_view_deck: 'Deck',
    compact_urf_replace: 'Swap',
    compact_urf_sell: 'Sell',
    compact_set_next_draw: 'Next',
    compact_pause_edit: 'Edit',
    compact_surrender: 'Give Up',
    compact_leave_spectate: 'Leave',
    compact_send: 'Send',
    compact_battle_log: 'Log',
    compact_hand: 'Hand',
    compact_equipment: 'Equip',
    compact_corrupted: 'Corrupt',
    compact_log_start: 'Start',
    compact_log_first: 'first',
    compact_log_order: 'Order',
});
Object.assign(I18N.zh, {
    compact_end_turn: '结束',
    compact_view_deck: '牌堆',
    compact_urf_replace: '换牌',
    compact_urf_sell: '售卖',
    compact_set_next_draw: '设抽',
    compact_pause_edit: '编辑',
    compact_surrender: '投降',
    compact_leave_spectate: '退出',
    compact_send: '发',
    compact_battle_log: '日志',
    compact_hand: '手牌',
    compact_equipment: '装备',
    compact_corrupted: '腐化',
    compact_log_start: '开始',
    compact_log_first: '先',
    compact_log_order: '顺序',
});
Object.assign(I18N.fr, {
    compact_end_turn: 'Fin',
    compact_view_deck: 'Deck',
    compact_urf_replace: 'Swap',
    compact_urf_sell: 'Vendre',
    compact_set_next_draw: 'Suiv.',
    compact_pause_edit: 'Editer',
    compact_surrender: 'Abandon',
    compact_leave_spectate: 'Quitter',
    compact_send: 'Env.',
    compact_battle_log: 'Log',
    compact_hand: 'Main',
    compact_equipment: 'Equip.',
    compact_corrupted: 'Corrompu',
    compact_log_start: 'Debut',
    compact_log_first: 'prem.',
    compact_log_order: 'Ordre',
});
Object.assign(I18N.pt, {
    compact_end_turn: 'Fim',
    compact_view_deck: 'Deck',
    compact_urf_replace: 'Trocar',
    compact_urf_sell: 'Vender',
    compact_set_next_draw: 'Prox.',
    compact_pause_edit: 'Editar',
    compact_surrender: 'Render',
    compact_leave_spectate: 'Sair',
    compact_send: 'Env.',
    compact_battle_log: 'Log',
    compact_hand: 'Mao',
    compact_equipment: 'Equip.',
    compact_corrupted: 'Corromp.',
    compact_log_start: 'Inicio',
    compact_log_first: '1o',
    compact_log_order: 'Ordem',
});
Object.assign(I18N.ja, {
    compact_end_turn: '終了',
    compact_view_deck: '山札',
    compact_urf_replace: '交換',
    compact_urf_sell: '売却',
    compact_set_next_draw: '次',
    compact_pause_edit: '編集',
    compact_surrender: '降参',
    compact_leave_spectate: '退出',
    compact_send: '送信',
    compact_battle_log: 'ログ',
    compact_hand: '手札',
    compact_equipment: '装備',
    compact_corrupted: '腐食',
    compact_log_start: '開始',
    compact_log_first: '先攻',
    compact_log_order: '順番',
});

Object.assign(I18N.en, {
    confirm_team_surrender: 'Request teammate approval to surrender?',
    surrender_consent_title: 'Surrender Request',
    surrender_consent_msg: '{0} wants to surrender. Agree?',
    surrender_accept_countdown: 'Agree ({0})',
    surrender_waiting_teammate: 'Waiting for teammate to approve surrender',
    surrender_declined: 'Teammate declined surrender',
    surrender_confirmed: 'Teammate agreed to surrender',
    surrender_teammate_offline: 'Teammate is not online',
    surrender_pending: 'A surrender request is already pending',
    surrender_no_pending: 'No pending surrender request',
    tomato_layer: 'Layers',
});
Object.assign(I18N.zh, {
    confirm_team_surrender: '请求队友同意投降？',
    surrender_consent_title: '投降确认',
    surrender_consent_msg: '{0} 想要投降，是否同意？',
    surrender_accept_countdown: '同意（{0}）',
    surrender_waiting_teammate: '等待队友同意投降',
    surrender_declined: '队友拒绝投降',
    surrender_confirmed: '队友已同意投降',
    surrender_teammate_offline: '队友不在线，无法投降',
    surrender_pending: '已有待确认的投降请求',
    surrender_no_pending: '没有待确认的投降请求',
    tomato_layer: '层数',
});
Object.assign(I18N.fr, {
    confirm_team_surrender: 'Demander l’accord du coequipier pour abandonner ?',
    surrender_consent_title: 'Demande d’abandon',
    surrender_consent_msg: '{0} veut abandonner. Accepter ?',
    surrender_accept_countdown: 'Accepter ({0})',
    surrender_waiting_teammate: 'En attente de l’accord du coequipier',
    surrender_declined: 'Le coequipier a refuse l’abandon',
    surrender_confirmed: 'Le coequipier a accepte l’abandon',
    surrender_teammate_offline: 'Le coequipier n’est pas en ligne',
    surrender_pending: 'Une demande d’abandon est deja en attente',
    surrender_no_pending: 'Aucune demande d’abandon en attente',
    tomato_layer: 'Couches',
});
Object.assign(I18N.pt, {
    confirm_team_surrender: 'Pedir aprovacao do aliado para render-se?',
    surrender_consent_title: 'Pedido de rendicao',
    surrender_consent_msg: '{0} quer render-se. Concordar?',
    surrender_accept_countdown: 'Concordar ({0})',
    surrender_waiting_teammate: 'Aguardando aprovacao do aliado',
    surrender_declined: 'O aliado recusou a rendicao',
    surrender_confirmed: 'O aliado aceitou a rendicao',
    surrender_teammate_offline: 'O aliado nao esta online',
    surrender_pending: 'Ja existe um pedido de rendicao pendente',
    surrender_no_pending: 'Nao ha pedido de rendicao pendente',
    tomato_layer: 'Camadas',
});
Object.assign(I18N.ja, {
    confirm_team_surrender: '味方の同意を得て降参しますか？',
    surrender_consent_title: '降参確認',
    surrender_consent_msg: '{0} が降参しようとしています。同意しますか？',
    surrender_accept_countdown: '同意（{0}）',
    surrender_waiting_teammate: '味方の降参同意を待っています',
    surrender_declined: '味方が降参を拒否しました',
    surrender_confirmed: '味方が降参に同意しました',
    surrender_teammate_offline: '味方がオンラインではありません',
    surrender_pending: '降参確認がすでに保留中です',
    surrender_no_pending: '保留中の降参確認はありません',
    tomato_layer: '層数',
});

Object.assign(I18N.en, {
    chat_channel_label: 'Chat channel',
    chat_channel_public: 'Public',
    chat_channel_team: 'Team',
    chat_channel_enemy: 'Enemy',
    chat_channel_private_to: 'Whisper -> {0}',
});
Object.assign(I18N.zh, {
    chat_channel_label: '\u804a\u5929\u9891\u9053',
    chat_channel_public: '\u516c\u5f00',
    chat_channel_team: '\u961f\u4f0d',
    chat_channel_enemy: '\u654c\u65b9',
    chat_channel_private_to: '\u79c1\u804a\u2192{0}',
});
Object.assign(I18N.fr, {
    chat_channel_label: 'Canal de chat',
    chat_channel_public: 'Public',
    chat_channel_team: 'Equipe',
    chat_channel_enemy: 'Adversaires',
    chat_channel_private_to: 'Prive -> {0}',
});
Object.assign(I18N.pt, {
    chat_channel_label: 'Canal de chat',
    chat_channel_public: 'Publico',
    chat_channel_team: 'Equipe',
    chat_channel_enemy: 'Inimigos',
    chat_channel_private_to: 'Privado -> {0}',
});
Object.assign(I18N.ja, {
    chat_channel_label: 'Chat channel',
    chat_channel_public: 'Public',
    chat_channel_team: 'Team',
    chat_channel_enemy: 'Enemy',
    chat_channel_private_to: 'Private -> {0}',
});
Object.assign(I18N.en, {
    report: 'Report',
    report_chat: 'Report message',
    report_player: 'Report player',
    report_match: 'Report match',
    report_title: 'Submit Report',
    report_object: 'Object',
    report_category: 'Category',
    report_reason: 'Reason',
    report_reason_placeholder: 'Optional details, up to 300 characters',
    report_submit: 'Submit',
    report_success: 'Report submitted',
    report_login_required: 'Log in to an account before reporting.',
    report_error: 'Report failed: {0}',
    report_category_abusive_language: 'Abusive language',
    report_category_sexual_content: 'Sexual content',
    report_category_spam: 'Spam',
    report_category_privacy_leak: 'Privacy leak',
    report_category_harassment: 'Harassment',
    report_category_cheating: 'Cheating',
    report_category_smurfing: 'Smurfing',
    report_category_boosting: 'Boosting',
    report_category_stalling: 'Stalling',
    report_category_inappropriate_name: 'Inappropriate name',
    report_category_bug_abuse: 'Bug abuse',
    report_category_abnormal_match: 'Abnormal match',
    report_category_other: 'Other',
});
Object.assign(I18N.zh, {
    report: '举报',
    report_chat: '举报消息',
    report_player: '举报玩家',
    report_match: '举报本局',
    report_title: '提交举报',
    report_object: '对象',
    report_category: '分类',
    report_reason: '说明',
    report_reason_placeholder: '可选补充说明，最多300字',
    report_submit: '提交',
    report_success: '举报已提交',
    report_login_required: '请先登录账号再举报。',
    report_error: '举报失败：{0}',
    report_category_abusive_language: '不当言语',
    report_category_sexual_content: '色情内容',
    report_category_spam: '刷屏/广告',
    report_category_privacy_leak: '泄露隐私',
    report_category_harassment: '骚扰',
    report_category_cheating: '作弊',
    report_category_smurfing: '小号扰乱',
    report_category_boosting: '刷分',
    report_category_stalling: '拖延',
    report_category_inappropriate_name: '不当昵称',
    report_category_bug_abuse: '利用漏洞',
    report_category_abnormal_match: '异常对局',
    report_category_other: '其他',
});
Object.assign(I18N.fr, {
    report: 'Signaler',
    report_chat: 'Signaler message',
    report_player: 'Signaler joueur',
    report_match: 'Signaler partie',
    report_title: 'Envoyer un signalement',
    report_object: 'Objet',
    report_category: 'Categorie',
    report_reason: 'Raison',
    report_reason_placeholder: 'Details facultatifs, 300 caracteres max',
    report_submit: 'Envoyer',
    report_success: 'Signalement envoye',
    report_login_required: 'Connectez-vous a un compte pour signaler.',
    report_error: 'Signalement echoue : {0}',
});
Object.assign(I18N.pt, {
    report: 'Denunciar',
    report_chat: 'Denunciar mensagem',
    report_player: 'Denunciar jogador',
    report_match: 'Denunciar partida',
    report_title: 'Enviar denuncia',
    report_object: 'Objeto',
    report_category: 'Categoria',
    report_reason: 'Motivo',
    report_reason_placeholder: 'Detalhes opcionais, ate 300 caracteres',
    report_submit: 'Enviar',
    report_success: 'Denuncia enviada',
    report_login_required: 'Entre com uma conta para denunciar.',
    report_error: 'Falha ao denunciar: {0}',
});
Object.assign(I18N.ja, {
    report: '通報',
    report_chat: 'メッセージを通報',
    report_player: 'プレイヤーを通報',
    report_match: '対戦を通報',
    report_title: '通報を送信',
    report_object: '対象',
    report_category: '分類',
    report_reason: '理由',
    report_reason_placeholder: '任意の補足、300文字以内',
    report_submit: '送信',
    report_success: '通報を送信しました',
    report_login_required: '通報するにはアカウントでログインしてください。',
    report_error: '通報失敗: {0}',
});

const SUPPORTED_LANGS = new Set(['zh', 'en', 'fr', 'pt', 'ja']);
function normalizeLang(lang) {
    return SUPPORTED_LANGS.has(lang) ? lang : 'zh';
}
let currentLang = normalizeLang(localStorage.getItem('gtn_lang') || 'zh');
if (localStorage.getItem('gtn_lang') !== currentLang) localStorage.setItem('gtn_lang', currentLang);
let showEnglishCardNames = localStorage.getItem('gtn_show_english_card_names') !== '0';
let showCardImages = localStorage.getItem('gtn_show_card_images') !== '0';
const UI_STYLE_MIGRATION_KEY = 'gtn_ui_style_v2_migrated';
const HIDDEN_FEATURES_KEY = 'gtn_hidden_features_enabled';
function hiddenFeaturesEnabled() {
    return localStorage.getItem(HIDDEN_FEATURES_KEY) === '1';
}
function migrateStoredUiStyle() {
    let stored = localStorage.getItem('gtn_ui_style') || 'minimal';
    if (!localStorage.getItem(UI_STYLE_MIGRATION_KEY) && stored === 'classic') {
        stored = 'minimal';
        localStorage.setItem('gtn_ui_style', stored);
        localStorage.setItem(UI_STYLE_MIGRATION_KEY, '1');
    }
    if (stored !== 'classic' || !hiddenFeaturesEnabled()) stored = 'minimal';
    if (!hiddenFeaturesEnabled() && localStorage.getItem('gtn_ui_style') === 'classic') {
        localStorage.setItem('gtn_ui_style', 'minimal');
    }
    return stored;
}
let currentUiStyle = migrateStoredUiStyle();
function t(key) { return (I18N[currentLang] && I18N[currentLang][key]) || (I18N.zh[key]) || key; }
function tf(key, ...values) { return t(key).replace(/\{(\d+)\}/g, (_, i) => values[Number(i)] ?? ''); }
const UI = new Proxy({}, { get: (_, key) => t(key) });

function isAdminPlayer(player) {
    return !!(player && (player.is_admin_player || player.isAdminPlayer || player.admin));
}

function isSpecialPlayer(player) {
    return !!(player && (isAdminPlayer(player) || player.is_special_player || player.special_role));
}

function getSpecialRolePrefix(player) {
    if (!player) return '';
    if (player.console_player || player.special_role === 'console') return UI.console_prefix || '控制台';
    if (isAdminPlayer(player)) return UI.admin_prefix;
    if (player.special_role === 'chief_designer') return UI.chief_designer_prefix;
    if (player.special_role === 'right_angle_person') return UI.right_angle_person_prefix;
    if (player.special_role_label) return player.special_role_label;
    return '';
}

function getSpecialRoleColor(player) {
    if (!player) return '';
    if (isAdminPlayer(player)) return 'admin';
    return player.special_role_color || '';
}

function getSpecialSortRank(player) {
    if (!player) return 99;
    const value = Number(player.special_role_sort);
    if (Number.isFinite(value)) return value;
    if (isAdminPlayer(player)) return 0;
    if (isSpecialPlayer(player)) return 1;
    return 99;
}

function getPlayerDisplayName(player, options = {}) {
    const { adminPrefix = true } = options;
    const name = localizeCanonicalPlayerName((player && (player.nickname || player.name)) || '?');
    const prefix = getSpecialRolePrefix(player);
    if (prefix && adminPrefix) return `[${prefix}]${name}`;
    return name;
}

function localizeCanonicalPlayerName(name) {
    const text = String(name || '');
    if (text === '你') return UI.tutorial_player_you || UI.you || text;
    if (text === '练习对手') return UI.tutorial_player_opponent || UI.opponent || text;
    return text;
}

function localizePlayerNameInText(text) {
    return String(text || '')
        .replaceAll('练习对手', UI.tutorial_player_opponent || UI.opponent || '练习对手')
        .replaceAll('你', UI.tutorial_player_you || UI.you || '你');
}

function setPlayerNameContent(el, player, options = {}) {
    if (!el) return;
    const { adminPrefix = true } = options;
    el.textContent = getPlayerDisplayName(player, { adminPrefix });
    el.classList.toggle('admin-name', isAdminPlayer(player));
    el.classList.toggle('bloom-name', getSpecialRoleColor(player) === 'bloom');
    el.classList.toggle('guard-name', getSpecialRoleColor(player) === 'guard');
    el.classList.toggle('account-name', !!(player && player.is_registered_user) && !isSpecialPlayer(player));
    el.classList.toggle('guest-name', !!(player && !player.is_registered_user) && !isSpecialPlayer(player));
}

function appendPlayerNameNode(parent, player, options = {}) {
    const span = document.createElement('span');
    span.className = 'player-name-inline';
    setPlayerNameContent(span, player, options);
    parent.appendChild(span);
    return span;
}

function appendPlayerNameList(parent, players, options = {}) {
    parent.textContent = '';
    (players || []).forEach((player, index) => {
        if (index > 0) parent.appendChild(document.createTextNode(' & '));
        appendPlayerNameNode(parent, player, options);
    });
}

function getChatDisplayName(data) {
    if (data && data.system) return '[系统]';
    const base = (data && data.nickname) || '?';
    const spectator = data && data.is_spectator ? `[${UI.spectator_prefix}]` : '';
    const prefix = getSpecialRolePrefix(data);
    const name = prefix ? `[${prefix}]${base}` : base;
    return `${spectator}${name}`;
}

const REPORT_CATEGORIES = {
    chat_message: ['abusive_language', 'sexual_content', 'spam', 'privacy_leak', 'harassment', 'other'],
    player: ['cheating', 'smurfing', 'boosting', 'stalling', 'inappropriate_name', 'harassment', 'other'],
    match: ['cheating', 'bug_abuse', 'boosting', 'stalling', 'abnormal_match', 'other'],
};

function reportCategoryLabel(category) {
    return t(`report_category_${category}`) || category;
}

function reportObjectLabel(objectType, fallback = '') {
    if (objectType === 'chat_message') return UI.report_chat || UI.report;
    if (objectType === 'player') return UI.report_player || UI.report;
    if (objectType === 'match') return UI.report_match || UI.report;
    return fallback || UI.report || 'Report';
}

function isReportableChatEntry(entry) {
    return !!(entry && !entry.system && (entry.message_id || entry.messageId));
}

function chatEntryReportMeta(entry = {}) {
    return {
        objectType: 'chat_message',
        objectId: String(entry.message_id || entry.messageId || ''),
        targetUserId: entry.sender_user_id || entry.senderUserId || '',
        targetUsername: entry.nickname || entry.sender_name || entry.senderName || entry.nick || '',
        title: UI.report_chat,
    };
}

function createReportButton(config = {}, options = {}) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = options.className || 'report-inline-btn';
    btn.textContent = options.text || UI.report || 'Report';
    btn.title = options.title || btn.textContent;
    btn.setAttribute('aria-label', btn.title);
    btn.onclick = (event) => {
        event.preventDefault();
        event.stopPropagation();
        openReportDialog(config);
    };
    return btn;
}

function getReportMatchObjectId(gs = gameState) {
    if (!gs) return '';
    if (gs.match_id != null) return String(gs.match_id);
    if (gs.room_id != null) return String(gs.room_id);
    const matchKey = String(gs.match_key || '');
    if (matchKey.startsWith('room:')) return matchKey.slice('room:'.length);
    return matchKey;
}

async function openReportDialog(config = {}) {
    if (!currentAccount) {
        gameAlert(UI.report || 'Report', UI.report_login_required || 'Log in to an account before reporting.');
        return;
    }
    const objectType = String(config.objectType || config.object_type || '');
    const objectId = String(config.objectId || config.object_id || '');
    if (!objectType || !objectId) {
        flashStatus(UI.operation_failed, 2200, 'error');
        return;
    }
    const categories = REPORT_CATEGORIES[objectType] || ['other'];
    const title = config.title || reportObjectLabel(objectType);
    const targetUsername = String(config.targetUsername || config.target_username || '');
    const targetUserId = config.targetUserId || config.target_user_id || '';
    showModal(`
        <div class="report-modal">
            <h3>${escapeHtml(UI.report_title || 'Submit Report')}</h3>
            <div class="report-target">
                <span>${escapeHtml(UI.report_object || 'Object')}</span>
                <strong>${escapeHtml(title)}${targetUsername ? ` · ${escapeHtml(targetUsername)}` : ''}</strong>
            </div>
            <label class="report-field">
                <span>${escapeHtml(UI.report_category || 'Category')}</span>
                <select id="report-category">
                    ${categories.map(cat => `<option value="${escapeHtml(cat)}">${escapeHtml(reportCategoryLabel(cat))}</option>`).join('')}
                </select>
            </label>
            <label class="report-field">
                <span>${escapeHtml(UI.report_reason || 'Reason')}</span>
                <textarea id="report-reason" maxlength="300" placeholder="${escapeHtml(UI.report_reason_placeholder || '')}"></textarea>
            </label>
            <div id="report-error" class="report-error hidden"></div>
            <div class="modal-buttons report-actions">
                <button class="btn btn-secondary" id="report-cancel">${escapeHtml(UI.cancel || 'Cancel')}</button>
                <button class="btn btn-danger" id="report-submit">${escapeHtml(UI.report_submit || UI.report || 'Submit')}</button>
            </div>
        </div>
    `);
    const cancelBtn = $('report-cancel');
    const submitBtn = $('report-submit');
    const errorEl = $('report-error');
    if (cancelBtn) cancelBtn.onclick = hideModal;
    if (!submitBtn) return;
    submitBtn.onclick = async () => {
        submitBtn.disabled = true;
        if (errorEl) errorEl.classList.add('hidden');
        const category = $('report-category') ? $('report-category').value : categories[0];
        const reasonText = $('report-reason') ? $('report-reason').value : '';
        try {
            const res = await fetch('/api/report', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    object_type: objectType,
                    object_id: objectId,
                    category,
                    reason_text: reasonText,
                    target_user_id: targetUserId || undefined,
                    target_username: targetUsername || undefined,
                }),
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok || !data.success) {
                throw new Error(data.error || data.message || res.statusText || UI.operation_failed);
            }
            hideModal();
            flashStatus(UI.report_success || 'Report submitted', 2200);
        } catch (err) {
            const message = err && err.message ? err.message : UI.operation_failed;
            if (errorEl) {
                errorEl.textContent = tf('report_error', message);
                errorEl.classList.remove('hidden');
            } else {
                flashStatus(tf('report_error', message), 3000, 'error');
            }
        } finally {
            submitBtn.disabled = false;
        }
    };
}

const COLORS = {
    elixir: '#F1C40F', elixir_text: '#D9A600', elixir_bg: '#FEF9E7',
    magic: '#3498DB', magic_text: '#1A5276', magic_bg: '#EBF5FB',
    health: '#2ECC71', health_text: '#1E8449', health_bg: '#E8F8F5',
    damage: '#C0392B', damage_bg: '#FDEDEC',
    poison: '#8E44AD', poison_bg: '#F4ECF7',
    fire: '#E67E22', fire_bg: '#FEF5E7',
    armor: '#95A5A6', armor_bg: '#F2F3F4', armor_text: '#515A5A',
    bloom: '#1ABC9C', bloom_bg: '#E8F8F5',
    root: '#8D6E63', root_bg: '#EFEBE9',
    guard: '#2980B9', guard_bg: '#EBF5FB',
    precise: '#546E7A', precise_bg: '#ECEFF1',
    banish: '#6C3483', banish_bg: '#F4ECF7',
    non_stack: '#34495E', non_stack_bg: '#EAECEE',
    indestructible: '#D4AC0D', indestructible_bg: '#FEF9E7',
    bg_page: '#F5F5F0', bg_card: '#FFFFFF',
    text_primary: '#2C3E50', text_secondary: '#7F8C8D',
    border_color: '#DCDCDC',
};

const CARD_TYPE_COLORS = {
    thorn: COLORS.damage, bloom: COLORS.bloom, root: COLORS.root, guard: COLORS.guard,
};

const CARD_FLAG_STYLES = {
    precision: { label: '', fg: '#ff6348', bg: 'rgba(255,99,72,0.15)', cls: 'precision' },
    exile: { label: '', fg: '#a29bfe', bg: 'rgba(162,155,254,0.15)', cls: 'exile' },
    non_stackable: { label: '', fg: '#ffa502', bg: 'rgba(255,165,2,0.15)', cls: 'non-stackable' },
    indestructible: { label: '', fg: '#747d8c', bg: 'rgba(116,125,140,0.15)', cls: 'indestructible' },
    sprout: { label: '', fg: '#1a8a4a', bg: 'rgba(26,138,74,0.15)', cls: 'sprout' },
    symbiosis: { label: '', fg: '#2471a3', bg: 'rgba(36,113,163,0.15)', cls: 'symbiosis' },
    attract: { label: '', fg: '#e67e22', bg: 'rgba(230,126,34,0.15)', cls: 'attract' },
    void: { label: '', fg: '#8e44ad', bg: 'rgba(142,68,173,0.15)', cls: 'void' },
    self_only: { label: '', fg: '#2f3542', bg: 'rgba(47,53,66,0.12)', cls: 'self-only' },
    uncancellable: { label: '', fg: '#7f1d1d', bg: 'rgba(127,29,29,0.12)', cls: 'uncancellable' },
    infinite_exclude: { label: '', fg: '#455A64', bg: 'rgba(69,90,100,0.12)', cls: 'infinite-exclude' },
    rebound: { label: '', fg: '#9B59B6', bg: 'rgba(155,89,182,0.14)', cls: 'rebound' },
    copy: { label: '', fg: '#e17055', bg: 'rgba(225,112,85,0.15)', cls: 'copy' },
    unique: { label: '', fg: '#fdcb6e', bg: 'rgba(253,203,110,0.15)', cls: 'unique' },
    swift: { label: '', fg: '#0984e3', bg: 'rgba(9,132,227,0.15)', cls: 'swift' },
    magic_swift: { label: '', fg: '#6C5CE7', bg: 'rgba(108,92,231,0.15)', cls: 'magic-swift' },
    power: { label: '', fg: '#C0392B', bg: 'rgba(192,57,43,0.14)', cls: 'power' },
    team_limited: { label: '', fg: '#607D3B', bg: 'rgba(96,125,59,0.15)', cls: 'team-limited' },
    team_unique: { label: '', fg: '#8D6E63', bg: 'rgba(141,110,99,0.15)', cls: 'team-unique' },
    fusion_layer: { label: '', fg: '#8e44ad', bg: 'rgba(142,68,173,0.15)', cls: 'fusion-layer' },
    fission_layer: { label: '', fg: '#0f766e', bg: 'rgba(15,118,110,0.14)', cls: 'fission-layer' },
    stealth: { label: '', fg: '#2C3E50', bg: '#EBF5FB', cls: 'stealth' },
    revealed: { label: '', fg: '#E74C3C', bg: '#FDEDEC', cls: 'revealed' },
};

const CARD_FLAG_TERM_COLORS = {
    precision: 'var(--color-precise)',
    exile: 'var(--color-banish)',
    non_stackable: 'var(--color-non-stack)',
    indestructible: 'var(--color-indestructible)',
    sprout: 'var(--color-sprout)',
    symbiosis: 'var(--color-symbiosis)',
    attract: 'var(--color-adhere)',
    void: 'var(--color-void)',
    self_only: '#2f3542',
    uncancellable: '#7f1d1d',
    infinite_exclude: '#455A64',
    rebound: '#9B59B6',
    copy: '#e17055',
    unique: '#fdcb6e',
    swift: '#0984e3',
    magic_swift: '#6C5CE7',
    power: '#C0392B',
    team_limited: '#607D3B',
    team_unique: '#8D6E63',
    fusion_layer: 'var(--color-poison)',
    fission_layer: '#0f766e',
    tomato_layer: '#b42318',
    stealth: '#2C3E50',
    revealed: '#E74C3C',
};

const CARD_FLAG_ALIASES = {
    'tag_troll_cards:exile': 'exile',
    'troll_cards:exile': 'exile',
    'tag_troll_cards_exile': 'exile',
    'troll_cards_exile': 'exile',
    sticky: 'rebound',
    tag_sticky: 'rebound',
    'tag_thorn_cards_supplement_1:sticky': 'rebound',
    'thorn_cards_supplement_1:sticky': 'rebound',
    'tag_thorn_cards_supplement_1_sticky': 'rebound',
    'thorn_cards_supplement_1_sticky': 'rebound',
    'tag_troll_cards:copy': 'copy',
    'troll_cards:copy': 'copy',
    'tag_troll_cards:unique': 'unique',
    'troll_cards:unique': 'unique',
    'tag_troll_cards:swift': 'swift',
    'troll_cards:swift': 'swift',
    stealth: 'stealth',
    revealed: 'revealed',
};

const _VANILLA_FLAGS = new Set([
    'precision', 'exile', 'non_stackable', 'indestructible', 'sprout',
    'symbiosis', 'attract', 'void', 'self_only', 'uncancellable',
    'infinite_exclude', 'rebound', 'copy', 'unique',
    'swift', 'stealth', 'revealed', 'team_limited', 'team_unique',
    'power', 'magic_swift',
]);

function normalizeCardFlag(flag) {
    const text = String(flag == null ? '' : flag).trim();
    if (!text) return '';
    const lower = text.toLowerCase();
    if (CARD_FLAG_ALIASES[lower]) return CARD_FLAG_ALIASES[lower];
    // Auto-strip namespace prefix for known vanilla flags (e.g. "factory:rebound" -> "rebound")
    if (lower.includes(':')) {
        const local = lower.split(':').pop();
        if (_VANILLA_FLAGS.has(local)) return local;
    }
    return text;
}

function getCardName(cardDef) {
    if (!cardDef) return '?';
    return getLocalizedCardText(cardDef, 'name_i18n', currentLang === 'zh' ? 'name_cn' : 'name_en');
}

function formatCardIdForDisplay(cardId) {
    return String(cardId || '')
        .replace(/[_-]+/g, ' ')
        .replace(/([a-z0-9])(?=[A-Z])/g, '$1 ')
        .replace(/([A-Z])(?=[A-Z][a-z])/g, '$1 ')
        .replace(/\s+/g, ' ')
        .trim();
}

function getEnglishCardName(cardDef) {
    if (!cardDef) return '';
    if (cardDef.name_en) return cardDef.name_en;
    const i18n = cardDef.name_i18n || {};
    return i18n.en || formatCardIdForDisplay(cardDef.id || cardDef.def_id || '');
}

function shouldShowEnglishCardName(cardDef, localizedName = '') {
    if (currentLang === 'en' || !showEnglishCardNames) return false;
    const englishName = getEnglishCardName(cardDef);
    return !!englishName && englishName !== localizedName;
}

function getCardTypeLabel(cardType) {
    if (!cardType) return '';
    return UI['card_type_' + cardType] || cardType;
}

function getLocalizedCardText(cardDef, key, fallbackKey) {
    if (!cardDef) return '';
    const dict = cardDef[key] || {};
    return dict[currentLang] || dict.en || dict.zh || cardDef[fallbackKey] || cardDef.name_en || cardDef.name_cn || '';
}

function getCardEffectText(cardDef) {
    return getLocalizedCardText(cardDef, 'effect_text_i18n', 'effect_text');
}

function getCardDescriptionText(cardDef) {
    return getLocalizedCardText(cardDef, 'description_i18n', 'description');
}

function getCardTriggerText(cardDef) {
    return getLocalizedCardText(cardDef, 'trigger_effect_text_i18n', 'trigger_effect_text');
}

function normalizeCardIntroText(value) {
    return String(value || '').replace(/\s+/g, '').trim();
}

function hasCardTriggerContent(cardDef) {
    if (!cardDef) return false;
    if (String(cardDef.trigger_effect_text || '').trim()) return true;
    if (Number(cardDef.trigger_cost_e) >= 0) return true;
    if (Array.isArray(cardDef.trigger_effects) && cardDef.trigger_effects.length) return true;
    const events = cardDef.v2_events || {};
    return ['on_equipment_trigger', 'on_turn_start_while_equipped', 'on_before_destroyed'].some(key => {
        const event = events[key];
        const steps = event && (event.steps || event);
        return Array.isArray(steps) && steps.length > 0;
    });
}

function getCardIntroTriggerText(cardDef) {
    if (!hasCardTriggerContent(cardDef)) return '';
    const triggerText = getCardTriggerText(cardDef) || '';
    if (!triggerText) return '';
    const effectText = getCardEffectText(cardDef) || '';
    if (normalizeCardIntroText(triggerText) === normalizeCardIntroText(effectText)) return '';
    return triggerText;
}

function escapeHtml(value) {
    return String(value == null ? '' : value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

const CARD_TEXT_TOKEN_RULES = [
    { cls: 'toxic', re: /^(?:\d+层淬毒|\d+\s*(?:Toxic|Toxique|Tóxico|Токсин)|淬毒\d+)/i },
    { cls: 'fire', re: /^(?:\d+层(?:F|灼烧)|\d+\s*(?:Burn|Brûlure|Brulure|Queima|Горения)|灼焼\d+)/i },
    { cls: 'poison', re: /^(?:\d+层(?:P|中毒)|\d+\s*P|\d+\s*(?:Poison|Veneno|Яда)|毒\d+)/i },
    { cls: 'damage', re: /^(?:[+-]?\d+电伤|\([^)]+\)|（[^）]+）|[+-]?\d+(?:[×x]\d+)?)D(?:[×x]\d+)?/i },
    { cls: 'armor', re: /^[+-]?\d+A/i },
    { cls: 'heal', re: /^\+\d+H/i },
    { cls: 'elixir', re: /^[+-]?\d+E/i },
    { cls: 'magic', re: /^[+-]?\d+M/i },
];

function buildInlineCardDict(defId, modifierText = '') {
    const cardDict = {
        def_id: defId,
        instance_flags: [],
        disabled_flags: [],
    };
    String(modifierText || '')
        .split('|')
        .map(part => part.trim())
        .filter(Boolean)
        .forEach(part => {
            const m = part.match(/^([^:=]+)\s*[:=]\s*(.+)$/);
            const key = normalizeCardFlag(m ? m[1] : part);
            const value = m ? m[2].trim() : '';
            const numberValue = Math.max(0, Math.floor(Number(value || 0)));
            if (key === 'swift') {
                if (numberValue > 0) {
                    cardDict.swift_value = numberValue;
                    cardDict.instance_flags.push('swift');
                }
                return;
            }
            if (key === 'magic_swift') {
                if (numberValue > 0) {
                    cardDict.magic_swift_value = numberValue;
                    cardDict.instance_flags.push('magic_swift');
                }
                return;
            }
            if (key === 'power') {
                if (numberValue > 0) {
                    cardDict.power_value = numberValue;
                    cardDict.instance_flags.push('power');
                }
                return;
            }
            if (key === 'fusion') {
                if (numberValue > 1) cardDict.fusion = numberValue;
                return;
            }
            if (key === 'fission') {
                if (numberValue > 1) cardDict.fission = numberValue;
                return;
            }
            if (key === 'tomato' || key === 'held_turns') {
                if (numberValue > 0) cardDict.held_turns = numberValue;
                return;
            }
            if ((key === 'flag' || key === 'tag') && value) {
                cardDict.instance_flags.push(normalizeCardFlag(value));
            }
        });
    return cardDict;
}

function inlineCardChipHtml(cardDict) {
    const chip = createCardChoiceChip(cardDict, { hideInstanceOnlyFlags: false });
    chip.classList.add('inline-card-chip', 'inline-card-chip-compact');
    chip.dataset.inlineCardChip = '1';
    chip.dataset.cardDict = JSON.stringify(cardDict || {});
    return chip.outerHTML;
}

function bindInlineCardChips(root) {
    if (!root || !root.querySelectorAll) return;
    root.querySelectorAll('.inline-card-chip.choice-card-token[data-inline-card-chip="1"]').forEach(chip => {
        if (chip.dataset.inlineChipBound === '1') return;
        chip.dataset.inlineChipBound = '1';
        let cardDict = null;
        try {
            cardDict = JSON.parse(chip.dataset.cardDict || '{}');
        } catch (_) {
            cardDict = null;
        }
        if (!cardDict || !cardDict.def_id) return;
        const stop = (event) => {
            event.stopPropagation();
        };
        ['click', 'dblclick', 'mousedown', 'mouseup', 'pointerdown', 'pointerup', 'touchstart', 'touchend'].forEach(type => {
            chip.addEventListener(type, stop, { passive: true });
        });
        attachFloatingCardPreview(chip, cardDict);
        attachTermIntroToCard(chip, cardDict);
    });
}

function colorizeCardText(value) {
    const text = String(value || '')
        .replace(/魔法球（萌芽、共生）|魔法球\(萌芽\+共生\)|\[魔法球\]\s*\[\s*萌芽\s*[+＋、,，]\s*共生\s*\]/g, '[[card:ManaOrb|flag=sprout|flag=symbiosis]]')
        .replace(/轻（萌芽、共生）|轻\(萌芽\+共生\)|\[轻\]\s*\[\s*萌芽\s*[+＋、,，]\s*共生\s*\]/g, '[[card:Light|flag=sprout|flag=symbiosis]]');
    let html = '';
    let i = 0;
    while (i < text.length) {
        const rest = text.slice(i);
        const cardMarker = rest.match(/^\[\[card:([a-z0-9_:/-]+)((?:\|[^\]]+)*)\]\]/i);
        if (cardMarker && cardMarker[1]) {
            const defId = cardMarker[1];
            html += inlineCardChipHtml(buildInlineCardDict(defId, cardMarker[2] || ''));
            i += cardMarker[0].length;
            continue;
        }
        let matched = null;
        for (const rule of CARD_TEXT_TOKEN_RULES) {
            const m = rest.match(rule.re);
            if (m && m[0]) {
                matched = { cls: rule.cls, text: m[0] };
                break;
            }
        }
        if (matched) {
            html += `<span class="card-token ${matched.cls}">${escapeHtml(matched.text)}</span>`;
            i += matched.text.length;
        } else {
            html += escapeHtml(text[i]);
            i += 1;
        }
    }
    return html;
}

function getLocalizedEventText(ev, field) {
    if (!ev) return '';
    const dictKey = field === 'name' ? 'name_i18n' : 'desc_i18n';
    const dict = ev[dictKey] || {};
    return dict[currentLang] || dict.en || dict.zh || ev[field] || '';
}

const LOG_TEXT = {
    en: { game_start: 'Game start. {p} goes first.', round: 'Round {n}', draw_cards: '{p} draws {n} cards', recover_e: '{p} recovers {n}E', take_damage: '{p} takes {n} {source} damage (H={h})', use_deal: '{p} uses {card}: deals {n} damage', use_multi: '{p} uses {card}: deals {n} x {times} damage', use_simple: '{p} uses {card}', equip: '{p} equips {card}', exile: '{card} is exiled', counter: '{p} counters with {card}', win: '{loser} reaches 0H. {winner} wins.', draw: 'Both players reached 0H. Draw.', surrender: '{p} surrenders. {winner} wins.', poison: 'Poison', burn: 'Burn', physical: 'physical' },
    fr: { game_start: 'Debut de partie. {p} commence.', round: 'Tour {n}', draw_cards: '{p} pioche {n} cartes', recover_e: '{p} recupere {n}E', take_damage: '{p} subit {n} degats {source} (H={h})', use_deal: '{p} joue {card}: inflige {n} degats', use_multi: '{p} joue {card}: inflige {n} x {times} degats', use_simple: '{p} joue {card}', equip: '{p} equipe {card}', exile: '{card} est exile', counter: '{p} contre avec {card}', win: '{loser} tombe a 0H. {winner} gagne.', draw: 'Les deux joueurs tombent a 0H. Egalite.', surrender: '{p} abandonne. {winner} gagne.', poison: 'Poison', burn: 'Brulure', physical: 'physiques' },
    pt: { game_start: 'Partida iniciada. {p} comeca.', round: 'Turno {n}', draw_cards: '{p} compra {n} cartas', recover_e: '{p} recupera {n}E', take_damage: '{p} sofre {n} de dano {source} (H={h})', use_deal: '{p} usa {card}: causa {n} de dano', use_multi: '{p} usa {card}: causa {n} x {times} de dano', use_simple: '{p} usa {card}', equip: '{p} equipa {card}', exile: '{card} e exilado', counter: '{p} responde com {card}', win: '{loser} chegou a 0H. {winner} vence.', draw: 'Ambos chegaram a 0H. Empate.', surrender: '{p} desistiu. {winner} vence.', poison: 'Veneno', burn: 'Queima', physical: 'fisico' },
    ru: { game_start: 'Game start. {p} goes first.', round: 'Round {n}', draw_cards: '{p} draws {n} cards', recover_e: '{p} recovers {n}E', take_damage: '{p} takes {n} {source} damage (H={h})', use_deal: '{p} uses {card}: deals {n} damage', use_multi: '{p} uses {card}: deals {n} x {times} damage', use_simple: '{p} uses {card}', equip: '{p} equips {card}', exile: '{card} is exiled', counter: '{p} counters with {card}', win: '{loser} reaches 0H. {winner} wins.', draw: 'Both players reached 0H. Draw.', surrender: '{p} surrenders. {winner} wins.', poison: 'Poison', burn: 'Burn', physical: 'physical' },
    ja: { game_start: 'Game start. {p} goes first.', round: 'Round {n}', draw_cards: '{p} draws {n} cards', recover_e: '{p} recovers {n}E', take_damage: '{p} takes {n} {source} damage (H={h})', use_deal: '{p} uses {card}: deals {n} damage', use_multi: '{p} uses {card}: deals {n} x {times} damage', use_simple: '{p} uses {card}', equip: '{p} equips {card}', exile: '{card} is exiled', counter: '{p} counters with {card}', win: '{loser} reaches 0H. {winner} wins.', draw: 'Both players reached 0H. Draw.', surrender: '{p} surrenders. {winner} wins.', poison: 'Poison', burn: 'Burn', physical: 'physical' },
};
LOG_TEXT.ja = {
    game_start: 'ゲーム開始。{p}が先攻。', round: 'ラウンド {n}', draw_cards: '{p}が{n}枚ドロー', recover_e: '{p}が{n}E回復',
    take_damage: '{p}が{n}{source}ダメージを受ける（H={h}）', use_deal: '{p}が{card}を使用：{n}ダメージ',
    use_multi: '{p}が{card}を使用：{n} x {times}ダメージ', use_simple: '{p}が{card}を使用', equip: '{p}が{card}を装備',
    exile: '{card}は追放された', counter: '{p}が{card}でカウンター', win: '{loser}のHが0。{winner}の勝利。',
    draw: '双方のHが0。引き分け。', surrender: '{p}が降参。{winner}の勝利。', poison: '毒', burn: '火傷', physical: '物理'
};
Object.assign(LOG_TEXT.en, {
    solo_start: 'Solo training starts. First player: {p}.',
    tutorial_start: 'Tutorial starts. First player: {p}.',
    urf_start: 'Infinite Fire starts. First player: {p}.',
    team_start: '2v2 starts. First player: {p}.',
    turn_order: 'Turn order: {order}',
    replenish_card: '{p} replenishes 1 {type} card: {card}',
    hand_full_discard: "{p}'s hand is full. {card} goes to discard.",
    replace_card: '{p} replaces {old} and gets {card}',
    chilli_discard_draw: '{p} uses Chilli, discards 1 card and draws 1 card',
    chilli_draw: '{p} uses Chilli and draws 1 card',
    sell_equipment: '{p} sells {card} and recovers {e}E/{m}M',
    team_draw: 'Both teams are defeated. Draw.',
    team_win: 'Team {team} wins.',
    disconnect_loss: '{p} disconnected for too long. {winner} wins.',
    team_disconnect_loss: '{p} disconnected for too long. Team {team} wins.',
});
Object.assign(LOG_TEXT.fr, {
    solo_start: 'Entraînement solo. {p} commence.',
    tutorial_start: 'Tutoriel. {p} commence.',
    urf_start: 'Infinite Fire commence. {p} joue en premier.',
    team_start: '2v2 commence. {p} joue en premier.',
    turn_order: 'Ordre des tours : {order}',
    replenish_card: '{p} récupère 1 carte {type} : {card}',
    hand_full_discard: 'La main de {p} est pleine. {card} va dans la défausse.',
    replace_card: '{p} remplace {old} et obtient {card}',
    chilli_discard_draw: '{p} joue Chilli, défausse 1 carte et pioche 1 carte',
    chilli_draw: '{p} joue Chilli et pioche 1 carte',
    sell_equipment: '{p} vend {card} et récupère {e}E/{m}M',
    team_draw: 'Les deux équipes sont vaincues. Égalité.',
    team_win: 'Équipe {team} gagne.',
    disconnect_loss: '{p} est resté déconnecté trop longtemps. {winner} gagne.',
    team_disconnect_loss: '{p} est resté déconnecté trop longtemps. Équipe {team} gagne.',
});
Object.assign(LOG_TEXT.pt, {
    solo_start: 'Treino solo começa. {p} começa.',
    tutorial_start: 'Tutorial começa. {p} começa.',
    urf_start: 'Infinite Fire começa. {p} joga primeiro.',
    team_start: '2v2 começa. {p} joga primeiro.',
    turn_order: 'Ordem dos turnos: {order}',
    replenish_card: '{p} repõe 1 carta {type}: {card}',
    hand_full_discard: 'A mão de {p} está cheia. {card} vai para o descarte.',
    replace_card: '{p} substitui {old} e recebe {card}',
    chilli_discard_draw: '{p} usa Chilli, descarta 1 carta e compra 1 carta',
    chilli_draw: '{p} usa Chilli e compra 1 carta',
    sell_equipment: '{p} vende {card} e recupera {e}E/{m}M',
    team_draw: 'As duas equipes foram derrotadas. Empate.',
    team_win: 'Equipe {team} vence.',
    disconnect_loss: '{p} ficou desconectado tempo demais. {winner} vence.',
    team_disconnect_loss: '{p} ficou desconectado tempo demais. Equipe {team} vence.',
});
Object.assign(LOG_TEXT.ja, {
    solo_start: '単人訓練開始。{p}が先攻。',
    tutorial_start: 'チュートリアル開始。{p}が先攻。',
    urf_start: 'Infinite Fire開始。{p}が先攻。',
    team_start: '2v2開始。{p}が先攻。',
    turn_order: 'ターン順：{order}',
    replenish_card: '{p}が{type}カードを1枚補充：{card}',
    hand_full_discard: '{p}の手札が満杯。{card}は捨て札へ。',
    replace_card: '{p}が{old}を入れ替え、{card}を得る',
    chilli_discard_draw: '{p}がChilliを使用：1枚捨て、1枚ドロー',
    chilli_draw: '{p}がChilliを使用：1枚ドロー',
    sell_equipment: '{p}が{card}を売却し、{e}E/{m}M回復',
    team_draw: '両チームが全滅。引き分け。',
    team_win: 'チーム{team}の勝利。',
    disconnect_loss: '{p}の切断が長すぎました。{winner}の勝利。',
    team_disconnect_loss: '{p}の切断が長すぎました。チーム{team}の勝利。',
});

Object.assign(LOG_TEXT.en, { battery_counter: 'Battery counter' });
Object.assign(LOG_TEXT.zh || (LOG_TEXT.zh = {}), { battery_counter: '\u7535\u6c60\u53cd\u4f24' });
Object.assign(LOG_TEXT.fr, { battery_counter: 'contre de Batterie' });
Object.assign(LOG_TEXT.pt, { battery_counter: 'contra-ataque da Bateria' });
Object.assign(LOG_TEXT.ja, { battery_counter: '\u96fb\u6c60\u53cd\u6483' });

const LOG_FALLBACK_REPLACE = {
    en: [
        ['受到螫针影响，能量回复-1', 'is affected by Stinger: energy recovery -1'],
        ['中毒减半为', 'Poison halves to '], ['获得邪眼护符效果', 'gains Nazar effect'], ['获得1层装备保护', 'gains 1 Equip Protect'],
        ['获得1层闪避', 'gains 1 Dodge'], ['获得2点护甲', 'gains 2 armor'], ['获得无敌', 'gains Invincible'],
        ['无法使用攻击牌', 'cannot use attack cards'], ['仅可使用攻击牌', 'can only use attack cards'], ['无法使用卡牌', 'cannot use cards'],
        ['每回合少抽', 'draws '], ['每回合能量回复', 'energy recovery per round '], ['每回合魔力回复', 'magic recovery per round '], ['每回合抽牌数', 'draw count per round '],
        ['被摧毁', 'is destroyed'], ['被放逐', 'is exiled'], ['因虚无被放逐', 'is exiled by Void'], ['装备保护抵消了摧毁', 'Equip Protect blocked destruction'],
        ['抽牌至手牌满', 'draws until hand is full'], ['前二回合', 'first two rounds'], ['前三回合', 'first three rounds'],
        ['敌方', 'opponent'], ['己方', 'self'], ['对敌方造成', 'deals to opponent '], ['造成', 'deals '], ['伤害', ' damage'],
        ['回复', 'recovers '], ['获得', 'gains '], ['装备了', 'equips '], ['使用了', 'uses '], ['使用', 'uses '],
        ['摧毁了', 'destroys '], ['但', ' but '], ['未找到目标', 'no target found'], ['未选择目标', 'no target selected'], ['目标无效', 'invalid target'],
        ['目标不可摧毁或不存在', 'target is indestructible or missing'], ['手牌已满', 'hand is full'], ['无中毒层数', 'no poison layers'],
        ['点物理伤害', ' physical damage'], ['层中毒', ' Poison'], ['层灼烧', ' Burn'], ['层闪避', ' Dodge'], ['层装备保护', ' Equip Protect'],
        ['回合', ' rounds'], ['张牌', ' cards'], ['牌堆', 'deck'], ['弃牌堆', 'discard pile'], ['场上所有装备', 'all equipment on field']
    ],
    fr: [
        ['受到螫针影响，能量回复-1', 'subit Stinger : récupération E -1'], ['中毒减半为', 'Poison réduit à '],
        ['获得邪眼护符效果', 'gagne Nazar'], ['获得1层装备保护', 'gagne 1 protection équipement'], ['获得1层闪避', 'gagne 1 esquive'],
        ['获得2点护甲', 'gagne 2 armure'], ['获得无敌', 'gagne invincible'], ['无法使用攻击牌', 'ne peut pas utiliser de cartes Thorn'],
        ['仅可使用攻击牌', 'ne peut utiliser que des cartes Thorn'], ['无法使用卡牌', 'ne peut pas utiliser de cartes'],
        ['被摧毁', 'est détruit'], ['被放逐', 'est exilé'], ['因虚无被放逐', 'est exilé par Void'], ['装备保护抵消了摧毁', 'protection équipement annule la destruction'],
        ['敌方', 'adversaire'], ['己方', 'soi'], ['造成', 'inflige '], ['伤害', ' dégâts'], ['回复', 'récupère '], ['获得', 'gagne '],
        ['装备了', 'équipe '], ['使用了', 'joue '], ['使用', 'joue '], ['摧毁了', 'détruit '], ['但', ' mais '],
        ['层中毒', ' Poison'], ['层灼烧', ' Brûlure'], ['层闪避', ' Esquive'], ['层装备保护', ' Protection équipement'], ['回合', ' tours'], ['张牌', ' cartes']
    ],
    pt: [
        ['受到螫针影响，能量回复-1', 'afetado por Stinger: recuperação E -1'], ['中毒减半为', 'Veneno reduzido para '],
        ['获得邪眼护符效果', 'ganha Nazar'], ['获得1层装备保护', 'ganha 1 proteção de equipamento'], ['获得1层闪避', 'ganha 1 esquiva'],
        ['获得2点护甲', 'ganha 2 armadura'], ['获得无敌', 'ganha invencível'], ['无法使用攻击牌', 'não pode usar cartas Thorn'],
        ['仅可使用攻击牌', 'só pode usar cartas Thorn'], ['无法使用卡牌', 'não pode usar cartas'], ['被摧毁', 'é destruído'], ['被放逐', 'é exilado'],
        ['因虚无被放逐', 'é exilado por Void'], ['装备保护抵消了摧毁', 'proteção de equipamento bloqueou destruição'],
        ['敌方', 'oponente'], ['己方', 'si'], ['造成', 'causa '], ['伤害', ' dano'], ['回复', 'recupera '], ['获得', 'ganha '],
        ['装备了', 'equipa '], ['使用了', 'usa '], ['使用', 'usa '], ['摧毁了', 'destrói '], ['但', ' mas '],
        ['层中毒', ' Veneno'], ['层灼烧', ' Queima'], ['层闪避', ' Esquiva'], ['层装备保护', ' Proteção de equipamento'], ['回合', ' turnos'], ['张牌', ' cartas']
    ],
    ru: [
        ['受到螫针影响，能量回复-1', 'под действием Stinger: восстановление E -1'], ['中毒减半为', 'яд уменьшается до '],
        ['获得邪眼护符效果', 'получает Nazar'], ['获得1层装备保护', 'получает 1 защиту экипировки'], ['获得1层闪避', 'получает 1 уклонение'],
        ['获得2点护甲', 'получает 2 брони'], ['获得无敌', 'получает неуязвимость'], ['无法使用攻击牌', 'не может использовать Thorn'],
        ['仅可使用攻击牌', 'может использовать только Thorn'], ['无法使用卡牌', 'не может использовать карты'], ['被摧毁', 'уничтожено'], ['被放逐', 'изгнано'],
        ['因虚无被放逐', 'изгнано Void'], ['装备保护抵消了摧毁', 'защита экипировки блокировала уничтожение'],
        ['敌方', 'противник'], ['己方', 'свой'], ['造成', 'наносит '], ['伤害', ' урона'], ['回复', 'восстанавливает '], ['获得', 'получает '],
        ['装备了', 'экипирует '], ['使用了', 'использует '], ['使用', 'использует '], ['摧毁了', 'уничтожает '], ['但', ' но '],
        ['层中毒', ' яд'], ['层灼烧', ' ожог'], ['层闪避', ' уклонение'], ['层装备保护', ' защита экипировки'], ['回合', ' раундов'], ['张牌', ' карт']
    ],
    ja: [
        ['受到螫针影响，能量回复-1', 'Stingerの影響：E回復-1'], ['中毒减半为', '毒が半減して'], ['获得邪眼护符效果', 'Nazar効果を得る'],
        ['获得1层装备保护', '装備保護1を得る'], ['获得1层闪避', '回避1を得る'], ['获得2点护甲', '装甲2を得る'], ['获得无敌', '無敵を得る'],
        ['无法使用攻击牌', 'Thornカードを使用不可'], ['仅可使用攻击牌', 'Thornカードのみ使用可'], ['无法使用卡牌', 'カードを使用不可'],
        ['被摧毁', 'は破壊された'], ['被放逐', 'は追放された'], ['因虚无被放逐', 'はVoidで追放された'], ['装备保护抵消了摧毁', '装備保護が破壊を防いだ'],
        ['敌方', '相手'], ['己方', '自分'], ['造成', '与える '], ['伤害', ' ダメージ'], ['回复', '回復 '], ['获得', '得る '],
        ['装备了', '装備 '], ['使用了', '使用 '], ['使用', '使用 '], ['摧毁了', '破壊 '], ['但', ' しかし '],
        ['层中毒', ' 毒'], ['层灼烧', ' 火傷'], ['层闪避', ' 回避'], ['层装备保护', ' 装備保護'], ['回合', 'ターン'], ['张牌', '枚']
    ]
};

function fmtLog(key, values = {}) {
    if (currentLang === 'zh') return null;
    const table = LOG_TEXT[currentLang] || LOG_TEXT.en;
    const template = table[key];
    return template ? template.replace(/\{(\w+)\}/g, (_, k) => values[k] ?? '') : null;
}

function localizedCardNameFromAny(name) {
    for (const cd of Object.values(CARD_DEFS)) {
        if (!cd) continue;
        const names = [cd.name_cn, cd.name_en, ...Object.values(cd.name_i18n || {})].filter(Boolean);
        if (names.includes(name)) return getCardName(cd);
    }
    return name;
}

function localizedCardTypeFromCn(typeName) {
    const text = String(typeName || '');
    if (text === '攻击') return UI.card_type_thorn || 'Thorn';
    if (text === '技能') return UI.card_type_bloom || 'Bloom';
    if (text === '装备') return UI.card_type_root || 'Root';
    if (text === '反制') return UI.card_type_guard || 'Guard';
    return text;
}

function localizeKnownLogText(line) {
    let out = localizePlayerNameInText(line);
    const cardNames = Object.values(CARD_DEFS)
        .filter(cd => cd && cd.name_cn)
        .sort((a, b) => String(b.name_cn).length - String(a.name_cn).length);
    for (const cd of cardNames) {
        out = out.replaceAll(cd.name_cn, getCardName(cd));
    }
    const pairs = LOG_FALLBACK_REPLACE[currentLang] || [];
    for (const [from, to] of pairs) {
        out = out.replaceAll(from, to);
    }
    return localizeDamageSource(out);
}

function localizeDamageSource(source) {
    const table = LOG_TEXT[currentLang] || LOG_TEXT.en;
    const raw = String(source || '');
    if (/电池|電池|battery/i.test(raw)) {
        return table.battery_counter || '电池反伤';
    }
    return raw
        .replaceAll('\u4e2d\u6bd2', table.poison)
        .replaceAll('\u707c\u70e7', table.burn)
        .replaceAll('\u7269\u7406', table.physical);
}

function translateLogLine(line) {
    if (currentLang === 'zh') {
        return String(line || '').replace(/受到(\d+)点电池(?:电击)?伤害/g, '受到$1点电池反伤');
    }
    let m;
    const lp = localizeCanonicalPlayerName;
    if ((m = line.match(/^\u6e38\u620f\u5f00\u59cb\uff01(.+)\u5148\u624b\u3002?$/))) return fmtLog('game_start', { p: lp(m[1]) });
    if ((m = line.match(/^\u5355\u4eba\u8bad\u7ec3\u573a\u5f00\u59cb\uff01(.+)\u5148\u624b\u3002?$/))) return fmtLog('solo_start', { p: lp(m[1]) }) || tf('training_start', lp(m[1]));
    if ((m = line.match(/^\u65b0\u624b\u6559\u7a0b\u5f00\u59cb\uff01(.+)\u5148\u624b\u3002?$/))) return fmtLog('tutorial_start', { p: lp(m[1]) });
    if ((m = line.match(/^\u65e0\u9650\u706b\u529b\u5f00\u59cb\uff01(.+)\u5148\u624b\u3002?$/))) return fmtLog('urf_start', { p: lp(m[1]) });
    if ((m = line.match(/^2v2\u6e38\u620f\u5f00\u59cb\uff01(.+)\u5148\u624b\u3002?$/))) return fmtLog('team_start', { p: lp(m[1]) });
    if ((m = line.match(/^\u56de\u5408\u987a\u5e8f\uff1a(.+)$/))) {
        const order = m[1].split(/\s*[\u2192]\s*/).map(lp).join(' \u2192 ');
        return fmtLog('turn_order', { order });
    }
    if ((m = line.match(/^=== \u7b2c(\d+)\u56de\u5408 ===$/))) return fmtLog('round', { n: m[1] });
    if (line === '\u53cc\u65b9\u751f\u547d\u503c\u540c\u65f6\u5f52\u96f6\uff01\u5e73\u5c40\uff01') return fmtLog('draw');
    if (line === '\u53cc\u65b9\u961f\u4f0d\u5168\u90e8\u9635\u4ea1\uff01\u5e73\u5c40\uff01') return fmtLog('team_draw');
    if ((m = line.match(/^(.+)\u751f\u547d\u503c\u5f52\u96f6\uff01(.+)\u83b7\u80dc\uff01$/))) return fmtLog('win', { loser: lp(m[1]), winner: lp(m[2]) });
    if ((m = line.match(/^(.+)\u6295\u964d\uff0c(.+)\u83b7\u80dc\uff01$/))) return fmtLog('surrender', { p: lp(m[1]), winner: lp(m[2]) });
    if ((m = line.match(/^(.+)\u65ad\u7ebf\u8d85\u65f6\uff0c\u961f\u4f0d(.+)\u83b7\u80dc\uff01$/))) return fmtLog('team_disconnect_loss', { p: lp(m[1]), team: localizePlayerNameInText(m[2]) });
    if ((m = line.match(/^(.+)\u65ad\u7ebf\u8d85\u65f6\uff0c(.+)\u83b7\u80dc\uff01$/))) return fmtLog('disconnect_loss', { p: lp(m[1]), winner: lp(m[2]) });
    if ((m = line.match(/^\u961f\u4f0d(.+)\u83b7\u80dc\uff01$/))) return fmtLog('team_win', { team: localizePlayerNameInText(m[1]) });
    if ((m = line.match(/^(.+)\u62bd(\d+)\u5f20\u724c$/))) return fmtLog('draw_cards', { p: lp(m[1]), n: m[2] });
    if ((m = line.match(/^(.+)\u4f7f\u7528\u8fa3\u6912\uff0c\u5f031\u5f20\u5e76\u62bd1\u5f20\u724c$/))) return fmtLog('chilli_discard_draw', { p: lp(m[1]) });
    if ((m = line.match(/^(.+)\u4f7f\u7528\u8fa3\u6912\uff0c\u62bd1\u5f20\u724c$/))) return fmtLog('chilli_draw', { p: lp(m[1]) });
    if ((m = line.match(/^(.+)\u56de\u590d(\d+)E$/))) return fmtLog('recover_e', { p: lp(m[1]), n: m[2] });
    if ((m = line.match(/^(.+)\u53d7\u5230(\d+)\u70b9(.+)\u4f24\u5bb3\uff08H=(-?\d+)\uff09$/))) return fmtLog('take_damage', { p: lp(m[1]), n: m[2], source: localizeDamageSource(m[3]), h: m[4] });
    if ((m = line.match(/^(.+)\u53d7\u5230(\d+)\u70b9\u4f24\u5bb3\uff08H=(-?\d+)\uff09$/))) return fmtLog('take_damage', { p: lp(m[1]), n: m[2], source: '', h: m[3] });
    if ((m = line.match(/^(.+)\u4f7f\u7528(.+)\uff01\u9020\u6210(\d+)\u4f24\u5bb3$/))) return fmtLog('use_deal', { p: lp(m[1]), card: localizedCardNameFromAny(m[2]), n: m[3] });
    if ((m = line.match(/^(.+)\u4f7f\u7528(.+)\uff01\u9020\u6210(\d+)x(\d+)\u4f24\u5bb3$/))) return fmtLog('use_multi', { p: lp(m[1]), card: localizedCardNameFromAny(m[2]), n: m[3], times: m[4] });
    if ((m = line.match(/^(.+)\u4f7f\u7528\u4e86(.+)$/))) return fmtLog('use_simple', { p: lp(m[1]), card: localizedCardNameFromAny(m[2]) });
    if ((m = line.match(/^(.+)\u88c5\u5907\u4e86(.+)$/))) return fmtLog('equip', { p: lp(m[1]), card: localizedCardNameFromAny(m[2]) });
    if ((m = line.match(/^(.+)\u4f7f\u7528(.+)\u8fdb\u884c\u53cd\u5236\uff01$/))) return fmtLog('counter', { p: lp(m[1]), card: localizedCardNameFromAny(m[2]) });
    if ((m = line.match(/^(.+)\u88ab\u653e\u9010$/))) return fmtLog('exile', { card: localizedCardNameFromAny(m[1]) });
    if ((m = line.match(/^(.+)\u8865\u51451\u5f20(.+)\u724c\uff1a(.+)$/))) return fmtLog('replenish_card', { p: lp(m[1]), type: localizedCardTypeFromCn(m[2]), card: localizedCardNameFromAny(m[3]) });
    if ((m = line.match(/^(.+)\u624b\u724c\u5df2\u6ee1\uff0c(.+)\u8fdb\u5165\u5f03\u724c\u5806$/))) return fmtLog('hand_full_discard', { p: lp(m[1]), card: localizedCardNameFromAny(m[2]) });
    if ((m = line.match(/^(.+)\u66ff\u6362\u4e86(.+)\uff0c\u83b7\u5f97(.+)$/))) return fmtLog('replace_card', { p: lp(m[1]), old: localizedCardNameFromAny(m[2]), card: localizedCardNameFromAny(m[3]) });
    if ((m = line.match(/^(.+)\u552e\u5356(.+)\uff0c\u56de\u590d(\d+)E\/(\d+)M$/))) return fmtLog('sell_equipment', { p: lp(m[1]), card: localizedCardNameFromAny(m[2]), e: m[3], m: m[4] });
    if ((m = line.match(/^\u8bad\u7ec3\u573a\uff1a(.+) \u8bbe\u7f6e\u4e0b\u6b21\u62bd\u724c\uff1a(.+)$/))) return tf('training_set_draw', lp(m[1]), m[2].split('\u3001').map(localizedCardNameFromAny).join(', '));
    return localizeKnownLogText(line);
}

function translateServerMessage(message) {
    if (!message) return UI.operation_failed;
    if (message === 'Operation failed') return UI.operation_failed;
    if (message === 'Invalid chat target') return UI.error_target_invalid;
    if (message === '聊天发送过快') return UI.chat_rate_limited || message;
    if (message === 'Teammate is not online') return UI.surrender_teammate_offline || message;
    if (message === 'A surrender request is already pending') return UI.surrender_pending || message;
    if (message === 'No pending surrender request') return UI.surrender_no_pending || message;
    if (message === 'Surrender requires a teammate') return UI.surrender_teammate_offline || message;
    if (message === '有玩家已返回大厅') return UI.rematch_unavailable_returned || message;
    if (message === '游戏已结束') return UI.error_game_over;
    if (message === '游戏已经结束') return UI.error_game_already_over || UI.error_game_over;
    if (message === '等待对手反制响应') return UI.error_waiting_counter;
    if (message === '卡牌不在手中') return UI.error_card_not_in_hand;
    if (message === '手牌中没有这张牌') return UI.error_card_not_in_hand_alt || UI.error_card_not_in_hand;
    if (message === '该牌不在选项中') return UI.error_card_not_in_options || UI.operation_failed;
    if (message === '移出手牌失败') return UI.error_remove_from_hand_failed;
    if (message === '没有待响应的操作') return UI.error_no_pending_response;
    if (message === '没有待选择操作') return UI.error_no_pending_choice;
    if (message === '选择已取消') return UI.error_choice_cancelled;
    if (message === '不是你的回合') return UI.error_not_your_turn;
    if (message === '无效玩家') return UI.error_invalid_player || UI.operation_failed;
    if (message === '不在选牌阶段') return UI.error_not_draft_phase || UI.operation_failed;
    if (message === '没有重选次数') return UI.error_no_reroll || UI.operation_failed;
    if (message === '没有待同意的队友用牌') return UI.error_no_pending_ally_consent || UI.operation_failed;
    if (message === '装备不存在') return UI.error_equipment_missing;
    if (message === '该装备没有触发效果') return UI.error_equipment_no_trigger;
    if (message === '装备需要装备一回合后才能触发') return UI.error_equipment_turn_needed;
    if (message === '只能在己方回合触发装备') return UI.error_equipment_friendly_turn_only || UI.error_not_your_turn;
    if (message === '能量不足') return UI.error_not_enough_e;
    if (message === '目标无效') return UI.error_target_invalid;
    if (message === '不能选择自己作为目标') return UI.error_target_self_forbidden || UI.error_target_invalid;
    if (message === '必须选择一名存活玩家') return UI.error_target_alive_required || UI.error_target_invalid;
    if (message === '眩晕效果中，无法使用卡牌') return UI.error_action_blocked;
    if (message === '本回合无法使用攻击牌') return UI.error_attack_blocked;
    if (message === '本回合只能使用攻击牌') return UI.error_attack_only;
    if (message === '反制牌只能通过响应机制使用') return UI.error_waiting_response_ui;
    if (message === '本回合已经替换过手牌') return UI.error_urf_replace_used || message;
    if (message === '本回合已经售卖过装备') return UI.error_urf_sell_used || message;
    if (message === '不可摧毁装备不能被售卖') return UI.error_indestructible_sell || message;
    const urfLimit = String(message).match(/^无限火力装备上限为(\d+)，请先售卖装备$/);
    if (urfLimit) return tf('error_urf_equip_limit', urfLimit[1]);
    return message;
}

function translateLoginReason(reason) {
    if (!reason) return UI.login_failed;
    if (reason === 'Invalid nickname. Use 1-16 display-width characters; avoid pure numbers, pure symbols, or repeated -/_.') {
        return UI.login_invalid_nickname;
    }
    if (reason === 'Nickname already exists') return UI.login_nickname_exists;
    if (reason === 'Admin nickname reserved') return UI.login_admin_reserved;
    if (reason === '此昵称被管理员占用') return UI.login_admin_reserved;
    if (reason === 'Account session expired') return UI.account_need_login;
    if (reason === 'Registered nickname reserved') return UI.login_registered_reserved;
    return reason;
}

function formatRemainingDuration(seconds) {
    let value = Math.max(0, Math.floor(Number(seconds) || 0));
    const days = Math.floor(value / 86400);
    value %= 86400;
    const hours = Math.floor(value / 3600);
    value %= 3600;
    const minutes = Math.floor(value / 60);
    const secs = value % 60;
    if (currentLang === 'zh') {
        if (days) return `${days}天${hours}小时`;
        if (hours) return `${hours}小时${minutes}分钟`;
        if (minutes) return `${minutes}分钟${secs}秒`;
        return `${secs}秒`;
    }
    if (days) return `${days}d ${hours}h`;
    if (hours) return `${hours}h ${minutes}m`;
    if (minutes) return `${minutes}m ${secs}s`;
    return `${secs}s`;
}

function moderationMessageFromPayload(data = {}, fallback = '') {
    let message = String(fallback || data.message || data.reason || data.error || '');
    if (data.permanent && !/永久|permanent/i.test(message)) {
        message = `${message} (${currentLang === 'zh' ? '永久' : 'permanent'})`;
    } else if (data.remaining_seconds != null && !/剩余|remaining|left|永久|permanent/i.test(message)) {
        const duration = formatRemainingDuration(data.remaining_seconds);
        message = currentLang === 'zh' ? `${message}（剩余${duration}）` : `${message} (${duration} left)`;
    }
    return message;
}
let playerId = -1;
let mySid = '';
let nickname = '';
let loginCredential = '';
let currentAccount = loadCachedAccount();
let accountMode = 'login';
let socialData = { friends: [], incoming: [], outgoing: [], settings: null, unread_count: 0 };
let friendsMessageTimer = null;
let dmData = { threads: [], unread_count: 0 };
let activeDmThreadId = null;
let activeDmTargetUserId = null;
let activeDmTargetIdentifier = '';
let activeDmMessages = [];
let activeSocialFriendId = null;
let lobbyMentionCandidates = [];
let lobbyMentionMenu = null;
let lobbyMentionActiveRange = null;
const readLobbyMentionIds = new Set();
let accountReplayItems = [];
let accountReplayTimeline = [];
let accountReplayFrameIndex = 0;
let accountReplaySpeed = 1;
let accountReplayTimer = null;
let accountReplayData = null;
let accountReplayPerspective = 0;
let accountReplayReturnContext = null;
let accountReplayTotalFrames = 0;
let accountReplayLoading = false;
let accountReplayLoadToken = 0;
let accountReplayControlsCollapsed = false;
let replayMode = false;
const DEFAULT_SKIN_CONFIG = Object.freeze({ primary_color: '#FFE763', eye_shape: 'oval' });
const SKIN_EYE_SHAPES = new Set(['oval', 'rectangle', 'diamond', 'hexagon']);
const DEFAULT_SKIN_LOOK = Object.freeze({ x: 0.707, y: -0.707 });
const SKIN_LOOK_OFFSET_X_PERCENT = 38;
const SKIN_LOOK_OFFSET_Y_PERCENT = 56;
const SKIN_LOOK_EMIT_INTERVAL_MS = 160;
const SKIN_DAMAGE_HOLD_MS = 3000;
const SKIN_STATUS_DAMAGE_SPLIT_MS = 1500;
let localSkinLook = { ...DEFAULT_SKIN_LOOK };
let lastSkinLookEmitAt = 0;
let lastSkinLookEmitKey = '';
const skinLookByPlayerId = new Map();
const skinDamageMoodByPlayerId = new Map();
const skinMouthTByPlayerId = new Map();
const skinCorruptionByPlayerId = new Map();
let socket = null;
let socketConnectUrl = '';
let socketCreateSeq = 0;
let manualDisconnect = false;
let latencyPingTimer = null;
let skinSaveInFlight = false;
let CARD_DEFS = {};
let gameState = {};
let activeV2UiRequestId = null;
let draftState = {};
let activeViewId = '';
let lastDraftOptionsSignature = '';
let lastDraftPicksSignature = '';
let eventSelectData = {};
let phaseChatEntries = [];
let phaseChatMatchKey = '';
let pregameChatEntries = [];
let pregameChatMatchKey = '';
let lobbyChatHistorySignature = '';
let lobbyPlayers = [];
let lobbyOngoingGames = [];
const FALLBACK_RELEASE_SERVER = 'http://121.41.93.192';
const FALLBACK_BETA_SERVER = 'http://121.41.93.192:8081';
const FALLBACK_PUBLIC_SERVER = GTN_BETA_MODE ? FALLBACK_BETA_SERVER : FALLBACK_RELEASE_SERVER;
const DEFAULT_SERVER = (() => {
    try {
        const origin = String(window.location && window.location.origin || '').trim();
        if (origin && origin !== 'null') return origin;
    } catch (_) {}
    return FALLBACK_PUBLIC_SERVER;
})();
const SERVER_ACTION_TIMEOUT_MS = 6000;
const SOCKET_CONNECT_TIMEOUT_MS = 5000;
const LEGACY_DEFAULT_SERVER_KEYS = new Set([
    'python-online-garden-of-thorn.onrender.com',
    'gtn.stickerbug.top',
    '121.41.93.192',
    '121.41.93.192:5000',
]);
let phase = 'connecting';
let responsePending = false;
let responseData = {};
let choicePending = false;
let choiceData = {};
let isSpectating = false;
let spectatePerspective = 0;
let pendingSpectateRoomId = null;
let activeSpectateRoomId = null;
let responseTimerId = null;
let responseCountdown = 0;
let allyConsentTimerId = null;
let allyConsentCountdown = 0;
let surrenderConsentTimerId = null;
let surrenderConsentCountdown = 0;
let soloMode = false;
let soloDeckA = [];
let soloDeckB = [];
let soloTargetDeck = 'a';
let pendingSoloStart = false;
let pendingSoloFallbackTimer = null;
let openingEvents = [];
let openingEventMagicPool = [];
let CUSTOM_TAG_DEFS = {};
let CUSTOM_STATUS_DEFS = {};
let soloEventA = '';
let soloEventB = '';
let tutorialMode = false;
let pendingTutorialStart = false;
let tutorialReturnTarget = 'home';
let tutorialBotTimer = null;
let tutorialLastLogTotal = 0;
let tutorialDeckViewed = false;
let tutorialCounterSeen = false;
let tutorialIntroActive = false;
let tutorialIntroShown = false;
let tutorialOverlayStartTimer = null;
let tutorialIntroTimer = null;
let tutorialStrictFocus = false;
let tutorialEndHintCount = 0;
let tutorialEndHintKey = '';
let tutorialOverlayRefreshTimer = null;
let suppressSoloPausedHandler = false;
let cardAnimationLockUntil = 0;
let cardAnimationUnlockTimer = null;
let hasPlayerHandSnapshot = false;
let recentlyPlayedExileCards = new Map();
let pendingLocalResourceCosts = [];
let pendingOptimisticResourceCosts = [];
let pendingPlayCard = null;
let pendingServerAction = null;
let pendingServerActionTimer = null;
let optimisticResourceOverride = null;
let selectedPlayCardId = null;
let classicAimPointer = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
let classicAimHoverTarget = '';
let classicAimFrame = 0;
let classicHoverPreviewTimer = null;
let classicHoverInfoEl = null;
let classicHoveredCardId = null;
let actionToastTimer = null;
let combatFloatSeq = 0;
const localSoloRuntime = {
    enabled: false,
    worker: null,
    fallbackPayload: null,
    fallbackKind: '',
};
const LOCAL_SOLO_SUPPORTED_EFFECTS = new Set([
    'damage', 'deal_damage', 'direct_damage', 'lifesteal_damage', 'triangle_damage',
    'heal', 'draw', 'gain_e', 'gain_m', 'add_armor', 'gain_armor', 'gain_dodge',
    'poison', 'apply_poison', 'burn', 'apply_burn', 'toxic', 'apply_toxic',
    'vulnus', 'apply_vulnerable', 'if', 'if_else', 'repeat', 'for_each_selected_card',
    'request_card', 'request_target', 'request_confirm',
    'card_prop_set', 'card_prop_add', 'card_prop_mul', 'card_damage_multiply', 'clear_tags',
    'equipment_prop_set', 'equipment_prop_add',
    'player_prop_set', 'player_prop_add', 'var_set', 'var_add', 'var_sub', 'var_mul', 'var_div',
    'copy_card', 'move_to_discard', 'move_to_hand', 'move_to_deck', 'remove_specific_card',
    'destroy_equipment_choice_or_first', 'destroy_random_equip', 'destroy_all_equip',
    'destroy_all_destroyable_equipment', 'destroy_self_equipment', 'place_as_equip', 'skip_turn',
    'reveal_enemy_hand', 'choose_from_deck', 'choose_from_discard', 'steal_enemy_card',
    'status_remove_named', 'status_add_named', 'clear_status',
    'on_owner_turn_start', 'on_enemy_turn_start', 'on_any_turn_start', 'on_damage_taken',
    'on_equipment_trigger', 'on_equipment_destroy', 'on_hand_owner_turn_start',
    'on_discard_owner_turn_start', 'on_deck_owner_turn_start',
    'on_card_used', 'on_equipment_triggered', 'on_equipment_destroyed',
    'on_resource_spent', 'on_player_stat_changed',
    'on_fatal_set_health_exile',
    'aura_enemy_elixir_recovery', 'nullify_current_card',
]);
const LOCAL_SOLO_SUPPORTED_V2_OPS = new Set([
    ...LOCAL_SOLO_SUPPORTED_EFFECTS,
    'draw_cards', 'add_status', 'remove_status', 'set_status', 'move_card',
    'create_card', 'destroy_equipment', 'log', 'set_health',
    'add_tag', 'remove_tag', 'tag_add_named', 'tag_remove_named',
    'for_each', 'repeat_until', 'for_each_list', 'for_each_equipment',
    'break', 'continue', 'timed_effect', 'countdown_var',
    'give_card_to_hand', 'give_card_to_deck', 'give_card_to_discard',
    'move_to_exile', 'add_equipment_to_zone', 'cost_e', 'cost_m',
    'invincible', 'mod_e_regen', 'mod_m_regen', 'mod_draw', 'equip_protection',
    'const', 'var', 'player_stat', 'card_prop', 'status_stack', 'count',
    'add', 'sub', 'mul', 'div', 'floor', 'ceil', 'min', 'max', 'last_damage',
    'compare', 'and', 'or', 'not', 'has_status_named', 'has_status',
    'zone_count', 'hand_count', 'deck_count', 'discard_count', 'exile_count', 'equipment_count',
    'equipment_prop', 'equipment_property', 'card_property', 'player_property',
    'damage_amount', 'current_damage', 'event_value', 'source_player', 'target_player',
    '<', '<=', '>', '>=', '==', '!=',
    'hand_full', 'selected_cards_count', 'selected_card_index',
    'selected_card_at', 'selected_card', 'last_created_card',
    'goggles_enable', 'request_reorder_deck',
]);
const COMBAT_FLOAT_TOTAL_LIMIT_MS = 5000;
const COMBAT_FLOAT_BASE_DURATION_MS = 1700;
const COMBAT_FLOAT_MIN_DURATION_MS = 620;
const COMBAT_FLOAT_END_PAD_MS = 140;
const COMBAT_FLOAT_MAX_LAST_DELAY_MS = COMBAT_FLOAT_TOTAL_LIMIT_MS - COMBAT_FLOAT_MIN_DURATION_MS - COMBAT_FLOAT_END_PAD_MS;
let targetPickCleanup = null;
let gameOverRenderTimer = null;
let scheduledGameOverState = null;
let gameTimelineEntries = [];
let renderedBattleLogCount = 0;
let renderedBattleLogTotal = 0;
let renderedTimelineDomCount = 0;
let renderedBattleLogSnapshot = [];
let renderedBattleLogMatchKey = '';
let renderedClassicLogSignature = '';
let lastRenderedTurnKey = '';
const lastStatusSignatures = new Map();
const GALLERY_MECHANIC_FLAGS = new Set(['fusion_layer', 'fission_layer']);
const bootLoader = {
    el: null, stepEl: null, fillEl: null, value: 0,
    init() {
        this.el = document.getElementById('boot-loader');
        this.stepEl = document.getElementById('boot-step');
        this.fillEl = document.getElementById('boot-progress-fill');
    },
    step(text, pct) {
        if (!this.el) this.init();
        if (this.stepEl) {
            this.stepEl.dataset.dynamic = '1';
            this.stepEl.textContent = text;
        }
        if (typeof pct === 'number') {
            this.value = Math.max(this.value, pct);
            if (this.fillEl) this.fillEl.style.width = `${this.value}%`;
        }
    },
    done() {        this.step(UI.init_done, 100);
        setTimeout(() => this.el && this.el.classList.add('hidden'), 120);
    }
};

function gameAlert(title, message, buttons) {
    if ((!buttons || buttons.length === 0) && (title === UI.notice || title === t('notice'))) {
        flashStatus(message || title || UI.notice, 2400, 'error');
        return;
    }
    const el = $('game-alert');
    if (!el) return;
    $('game-alert-icon').textContent = '!';
    $('game-alert-title').textContent = title || '';
    $('game-alert-message').textContent = message || '';
    const btnsEl = $('game-alert-buttons');
    btnsEl.innerHTML = '';
    (buttons || [{ text: UI.ok, cls: 'btn-primary', action: () => {} }]).forEach(b => {
        const btn = document.createElement('button');
        btn.className = 'btn ' + (b.cls || 'btn-primary');
        btn.textContent = b.text;
        btn.onclick = () => { el.classList.remove('active'); b.action(); };
        btnsEl.appendChild(btn);
    });
    el.classList.add('active');
}

function gameConfirm(title, message = '') {
    return new Promise((resolve) => {
        gameAlert(title, message, [
            { text: UI.cancel || 'Cancel', cls: 'btn-secondary', action: () => resolve(false) },
            { text: UI.confirm || UI.ok || 'OK', cls: 'btn-primary', action: () => resolve(true) },
        ]);
    });
}

function hideGameAlert() {
    const el = $('game-alert');
    if (el) el.classList.remove('active');
}

function cleanupGamePromptTransientButtons() {
    document.querySelectorAll('#game-prompt .game-prompt-transient-btn').forEach(btn => btn.remove());
}

function gamePrompt(title, options, config = {}) {
    return new Promise((resolve) => {
        const el = $('game-prompt');
        if (!el) { resolve(-1); return; }
        cleanupGamePromptTransientButtons();
        const cancellable = config.cancellable !== false;
        $('game-prompt-title').textContent = title || '';
        const optsEl = $('game-prompt-options');
        let msgEl = $('game-prompt-message');
        if (!msgEl) {
            msgEl = document.createElement('div');
            msgEl.id = 'game-prompt-message';
            msgEl.className = 'game-prompt-message';
            optsEl.parentNode.insertBefore(msgEl, optsEl);
        }
        const message = config.message || config.content || '';
        msgEl.textContent = message;
        msgEl.classList.toggle('hidden', !message);
        optsEl.innerHTML = '';
        options.forEach((opt, i) => {
            const div = document.createElement('div');
            div.className = 'game-prompt-option';
            const disabled = !!(opt && typeof opt === 'object' && opt.disabled);
            if (disabled) {
                div.classList.add('disabled');
                div.setAttribute('aria-disabled', 'true');
            }
            renderChoiceOptionContent(div, opt, i, config);
            div.onclick = () => {
                if (disabled) return;
                removeFloatingCardPreview();
                el.classList.remove('active');
                resolve(i);
            };
            optsEl.appendChild(div);
        });
        const cancelBtn = $('game-prompt-cancel');
        cancelBtn.textContent = UI.cancel;
        cancelBtn.classList.remove('btn-primary');
        cancelBtn.classList.add('btn-secondary');
        cancelBtn.classList.toggle('hidden', !cancellable);
        cancelBtn.style.display = cancellable ? '' : 'none';
        cancelBtn.onclick = () => { removeFloatingCardPreview(); el.classList.remove('active'); resolve(-1); };
        el.classList.add('active');
    });
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('gtn_theme', theme);
    const sel = $('settings-theme-select');
    if (sel) sel.value = theme;
}

function applyUiStyle(style) {
    currentUiStyle = style === 'classic' && hiddenFeaturesEnabled() ? 'classic' : 'minimal';
    document.documentElement.setAttribute('data-ui-style', currentUiStyle);
    localStorage.setItem('gtn_ui_style', currentUiStyle);
    const sel = $('settings-ui-style-select');
    if (sel) sel.value = currentUiStyle;
    updateUiStyleAvailability();
    updateCompactUiText();
    refreshVisibleCardDisplays();
}

function updateUiStyleAvailability() {
    const select = $('settings-ui-style-select');
    if (!select) return;
    const classicOpt = select.querySelector('option[value="classic"]');
    const unlocked = hiddenFeaturesEnabled();
    if (classicOpt) {
        classicOpt.disabled = !unlocked;
        classicOpt.hidden = !unlocked;
    }
    if (!unlocked && select.value === 'classic') select.value = 'minimal';
}

function compactText(normalKey, compactKey) {
    if (!isMinimalUiStyle() || !compactKey) return t(normalKey);
    return t(compactKey);
}

function setCompactButtonText(id, normalKey, compactKey) {
    const el = $(id);
    if (!el) return;
    const full = t(normalKey);
    el.textContent = full;
    el.removeAttribute('title');
    el.removeAttribute('aria-label');
}

function updateCompactUiText() {
    setCompactButtonText('btn-end-turn', 'end_turn', 'compact_end_turn');
    setCompactButtonText('btn-view-deck', 'view_deck', 'compact_view_deck');
    setCompactButtonText('btn-spectate-view-deck', 'view_deck', 'compact_view_deck');
    setCompactButtonText('btn-urf-replace', 'urf_replace', 'compact_urf_replace');
    setCompactButtonText('btn-urf-sell', 'urf_sell', 'compact_urf_sell');
    setCompactButtonText('btn-solo-next-draw', 'set_next_draw', 'compact_set_next_draw');
    setCompactButtonText('btn-solo-edit', 'pause_edit', 'compact_pause_edit');
    setCompactButtonText('classic-view-deck', 'view_deck', 'compact_view_deck');
    setCompactButtonText('classic-switch-perspective', 'switch_perspective', 'switch_perspective');
    setCompactButtonText('classic-urf-replace', 'urf_replace', 'compact_urf_replace');
    setCompactButtonText('classic-urf-sell', 'urf_sell', 'compact_urf_sell');
    setCompactButtonText('classic-solo-next-draw', 'set_next_draw', 'compact_set_next_draw');
    setCompactButtonText('classic-solo-edit', 'pause_edit', 'compact_pause_edit');
    setCompactButtonText('btn-surrender', 'surrender', 'compact_surrender');
    setCompactButtonText('btn-leave-spectate', 'leave_spectate', 'compact_leave_spectate');
    setCompactButtonText('btn-game-chat-send', 'send', 'compact_send');
    const battleLogHeader = document.querySelector('#battle-log .log-header');
    if (battleLogHeader) {
        const full = UI.battle_log;
        battleLogHeader.textContent = full;
        battleLogHeader.title = '';
    }
    const teammateSections = document.querySelectorAll('.teammate-sidebar-section');
    if (teammateSections[0]) teammateSections[0].textContent = compactText('compact_hand', 'compact_hand');
    if (teammateSections[1]) teammateSections[1].textContent = compactText('compact_equipment', 'compact_equipment');
}

function applyLang(lang) {
    lang = normalizeLang(lang);
    currentLang = lang;
    localStorage.setItem('gtn_lang', lang);
    document.documentElement.setAttribute('lang', lang);
    const sel = $('settings-lang-select');
    if (sel) sel.value = lang;
    updateStaticText();
    refreshBaseStatus();
    refreshVisibleCardDisplays();
}

function updateEnglishNameSettingVisibility() {
    const row = $('settings-english-name-row');
    if (row) {
        const hidden = currentLang === 'en';
        row.classList.toggle('hidden', hidden);
        row.style.display = hidden ? 'none' : '';
    }
    const input = $('settings-show-english-names');
    if (input) input.checked = showEnglishCardNames;
}

function applyShowEnglishCardNames(value) {
    showEnglishCardNames = !!value;
    localStorage.setItem('gtn_show_english_card_names', showEnglishCardNames ? '1' : '0');
    updateEnglishNameSettingVisibility();
    refreshVisibleCardDisplays();
}

function updateCardImageSettingInput() {
    const input = $('settings-show-card-images');
    if (input) input.checked = showCardImages;
}

function applyShowCardImages(value) {
    showCardImages = !!value;
    localStorage.setItem('gtn_show_card_images', showCardImages ? '1' : '0');
    updateCardImageSettingInput();
    refreshVisibleCardDisplays();
}

function refreshVisibleCardDisplays() {
    const viewId = getVisibleViewId();
    if (viewId === 'view-game' && gameState) renderGame(gameState);
    if (viewId === 'view-draft' && draftState) renderDraft(draftState, false);
    if (viewId === 'view-solo') renderSoloBuilder();
    if (viewId === 'view-card-gallery') renderCardGallery();
}

function updateStaticText() {
    document.title = GAME_TITLE;
    const bootTitle = document.querySelector('.boot-title');
    if (bootTitle) bootTitle.textContent = GAME_TITLE;
    const titleMain = document.querySelector('.title-main');
    if (titleMain) titleMain.textContent = 'Garden of Thorn';
    const titleSub = document.querySelector('.title-sub');
    if (titleSub) titleSub.textContent = '荆棘花园';
    const subtitle = document.querySelector('#view-login .subtitle');
    if (subtitle) subtitle.textContent = UI.app_subtitle;
    const bootSub = document.querySelector('#boot-loader .boot-sub');
    if (bootSub) bootSub.textContent = UI.game_loading;
    const bootStep = $('boot-step');
    if (bootStep && !bootStep.dataset.dynamic) bootStep.textContent = UI.init_scripts;
    const settingsTitle = $('settings-title');
    if (settingsTitle) settingsTitle.textContent = UI.settings_title;
    const settingsTabAppearance = $('settings-tab-appearance');
    if (settingsTabAppearance) settingsTabAppearance.textContent = UI.settings_appearance;
    const settingsTabServer = $('settings-tab-server');
    if (settingsTabServer) settingsTabServer.textContent = UI.settings_server;
    const settingsTabMods = $('settings-tab-mods');
    if (settingsTabMods) settingsTabMods.textContent = UI.settings_mods;
    const settingsTabSocial = $('settings-tab-social');
    if (settingsTabSocial) settingsTabSocial.textContent = UI.social;
    const settingsAppearance = $('settings-section-appearance');
    if (settingsAppearance) settingsAppearance.textContent = UI.settings_appearance;
    const settingsMods = $('settings-section-mods');
    if (settingsMods) settingsMods.textContent = UI.settings_mods;
    const settingsSocial = $('settings-section-social');
    if (settingsSocial) settingsSocial.textContent = UI.social;
    const socialLoginHint = $('settings-social-login-hint');
    if (socialLoginHint) socialLoginHint.textContent = UI.social_login_hint;
    const acceptFriendLabel = $('settings-label-accept-friend-requests');
    if (acceptFriendLabel) acceptFriendLabel.textContent = UI.social_accept_requests;
    const searchNickLabel = $('settings-label-searchable-by-nickname');
    if (searchNickLabel) searchNickLabel.textContent = UI.social_search_nickname;
    const searchIdLabel = $('settings-label-searchable-by-player-id');
    if (searchIdLabel) searchIdLabel.textContent = UI.social_search_id;
    const settingsOfficialMods = $('settings-label-official-mods');
    if (settingsOfficialMods) settingsOfficialMods.textContent = UI.official_mods;
    const settingsCommunityMods = $('settings-label-community-mods');
    if (settingsCommunityMods) settingsCommunityMods.textContent = UI.community_mods;
    const noCommunityMods = $('settings-no-community-mods');
    if (noCommunityMods) noCommunityMods.textContent = UI.no_community_mods;
    const communityCurrentLabel = $('settings-community-current-label');
    if (communityCurrentLabel) communityCurrentLabel.textContent = UI.community_current;
    const communityDisable = $('btn-community-disable');
    if (communityDisable) communityDisable.textContent = UI.community_disable;
    const refreshCommunity = $('btn-community-refresh');
    if (refreshCommunity) refreshCommunity.textContent = UI.refresh;
    const uploadCommunity = $('btn-community-upload');
    if (uploadCommunity) uploadCommunity.textContent = UI.community_upload || '上传模组';
    const settingsLabelTheme = $('settings-label-theme');
    if (settingsLabelTheme) settingsLabelTheme.textContent = UI.settings_theme;
    const settingsLabelUiStyle = $('settings-label-ui-style');
    if (settingsLabelUiStyle) settingsLabelUiStyle.textContent = UI.settings_ui_style;
    const settingsLabelLang = $('settings-label-lang');
    if (settingsLabelLang) settingsLabelLang.textContent = UI.settings_lang;
    const settingsEnglishNameLabel = $('settings-label-show-english-names');
    if (settingsEnglishNameLabel) settingsEnglishNameLabel.textContent = UI.settings_show_english_card_names;
    const settingsCardImagesLabel = $('settings-label-show-card-images');
    if (settingsCardImagesLabel) settingsCardImagesLabel.textContent = UI.settings_show_card_images;
    updateEnglishNameSettingVisibility();
    updateCardImageSettingInput();
    const themeSelect = $('settings-theme-select');
    if (themeSelect) {
        themeSelect.options[0].textContent = UI.settings_theme_light;
        themeSelect.options[1].textContent = UI.settings_theme_dark;
    }
    const uiStyleSelect = $('settings-ui-style-select');
    if (uiStyleSelect) {
        const minimalOpt = uiStyleSelect.querySelector('option[value="minimal"]');
        const classicOpt = uiStyleSelect.querySelector('option[value="classic"]');
        if (minimalOpt) minimalOpt.textContent = UI.ui_style_minimal;
        if (classicOpt) classicOpt.textContent = UI.ui_style_classic;
        uiStyleSelect.value = currentUiStyle;
        updateUiStyleAvailability();
    }
    const langSelect = $('settings-lang-select');
    if (langSelect) {
        const langLabels = {
            zh: '\u7b80\u4f53\u4e2d\u6587',
            en: 'English (US)',
            fr: 'Francais',
            pt: 'Portugues (Brasil)',
            ja: '\u65e5\u672c\u8a9e',
        };
        Object.entries(langLabels).forEach(([value, label]) => {
            const option = langSelect.querySelector(`option[value="${value}"]`);
            if (option) option.textContent = label;
        });
    }
    const btnSettings = $('btn-open-settings');
    if (btnSettings) btnSettings.textContent = UI.settings_btn;
    const btnCardGallery = $('btn-card-gallery');
    if (btnCardGallery) btnCardGallery.textContent = UI.gallery_title;
    const galleryTitle = $('gallery-title');
    if (galleryTitle) galleryTitle.textContent = UI.gallery_title;
    const galleryTabCards = $('gallery-tab-cards');
    if (galleryTabCards) galleryTabCards.textContent = UI.gallery_cards;
    const galleryTabTags = $('gallery-tab-tags');
    if (galleryTabTags) galleryTabTags.textContent = UI.gallery_tags;
    const galleryTabEvents = $('gallery-tab-events');
    if (galleryTabEvents) galleryTabEvents.textContent = UI.gallery_events;
    const gallerySearch = $('gallery-search');
    if (gallerySearch) gallerySearch.placeholder = UI.gallery_search;
    const btnOpenRules = $('btn-open-rules');
    if (btnOpenRules) btnOpenRules.textContent = UI.rules_intro_title;
    const btnGalleryBack = $('btn-gallery-back');
    if (btnGalleryBack) btnGalleryBack.textContent = galleryReturnToRules ? UI.gallery_back_rules : UI.back_to_home;
    const btnOpenAbout = $('btn-open-about');
    if (btnOpenAbout) btnOpenAbout.textContent = UI.about_title;
    const aboutTitle = document.querySelector('#about-panel .settings-inner > h3');
    if (aboutTitle) aboutTitle.textContent = UI.about_title;
    const aboutTabRules = $('about-tab-rules');
    if (aboutTabRules) aboutTabRules.textContent = UI.about_gameplay;
    const aboutTabCredits = $('about-tab-credits');
    if (aboutTabCredits) aboutTabCredits.textContent = UI.about_credits;
    const creditsDeveloper = $('credits-developer-title');
    if (creditsDeveloper) creditsDeveloper.textContent = UI.credits_developer;
    const creditsDesign = $('credits-design-title');
    if (creditsDesign) creditsDesign.textContent = UI.credits_design || '设计';
    const creditsArt = $('credits-art-title');
    if (creditsArt) creditsArt.textContent = UI.credits_art || '美工';
    const creditsSpecial = $('credits-special-title');
    if (creditsSpecial) creditsSpecial.textContent = UI.credits_special;
    bindHiddenFeatureLongPress();
    renderAboutRulesBody();
    const btnLobbyBack = $('btn-lobby-back');
    if (btnLobbyBack) btnLobbyBack.textContent = UI.back_to_home;
    const btnLobbySettings = $('btn-lobby-settings');
    if (btnLobbySettings) btnLobbySettings.textContent = UI.settings_btn;
    const btnConnect = $('btn-connect');
    if (btnConnect) btnConnect.textContent = UI.enter_lobby;
    const btnSoloTraining = $('btn-solo-training');
    if (btnSoloTraining) btnSoloTraining.textContent = UI.solo_training;
    const btnAccountTop = $('btn-account-top');
    if (btnAccountTop) btnAccountTop.textContent = UI.account;
    const btnFriendsTop = $('btn-friends-top');
    if (btnFriendsTop) btnFriendsTop.textContent = UI.friends;
    const btnSkinTop = $('btn-skin-top');
    if (btnSkinTop) btnSkinTop.textContent = UI.skin;
    const skinTitle = $('skin-title');
    if (skinTitle) skinTitle.textContent = UI.skin_title || UI.skin;
    const skinBack = $('btn-skin-back');
    if (skinBack) skinBack.textContent = UI.back_to_home;
    const skinPrimaryLabel = $('skin-primary-label');
    if (skinPrimaryLabel) skinPrimaryLabel.textContent = UI.skin_primary_color;
    const skinEyeShapeLabel = $('skin-eye-shape-label');
    if (skinEyeShapeLabel) skinEyeShapeLabel.textContent = UI.skin_eye_shape;
    const skinEyeOval = $('skin-eye-oval');
    if (skinEyeOval) skinEyeOval.textContent = UI.skin_eye_oval;
    const skinEyeRectangle = $('skin-eye-rectangle');
    if (skinEyeRectangle) skinEyeRectangle.textContent = UI.skin_eye_rectangle;
    const skinEyeDiamond = $('skin-eye-diamond');
    if (skinEyeDiamond) skinEyeDiamond.textContent = UI.skin_eye_diamond;
    const skinEyeHexagon = $('skin-eye-hexagon');
    if (skinEyeHexagon) skinEyeHexagon.textContent = UI.skin_eye_hexagon;
    const skinLayoutPlaceholder = $('skin-face-layout-placeholder');
    if (skinLayoutPlaceholder) skinLayoutPlaceholder.textContent = UI.skin_face_layout_placeholder;
    const skinShapePlaceholder = $('skin-face-shape-placeholder');
    if (skinShapePlaceholder) skinShapePlaceholder.textContent = UI.skin_face_shape_placeholder;
    const skinSyncNote = $('skin-sync-note');
    if (skinSyncNote) skinSyncNote.textContent = UI.skin_sync_guest;
    const skinSave = $('btn-skin-save');
    if (skinSave) skinSave.textContent = UI.skin_save;
    const skinReset = $('btn-skin-reset');
    if (skinReset) skinReset.textContent = UI.skin_reset;
    const friendsTitle = $('friends-popover-title');
    if (friendsTitle) friendsTitle.textContent = UI.friends;
    const socialDetailTitle = $('social-detail-title');
    if (socialDetailTitle) socialDetailTitle.textContent = UI.social;
    document.querySelectorAll('[data-social-detail-tab]').forEach(btn => {
        const tab = btn.dataset.socialDetailTab;
        if (tab === 'profile') btn.textContent = UI.friend_profile || '资料';
        if (tab === 'dm') btn.textContent = UI.direct_messages || '私信';
        if (tab === 'incoming') btn.textContent = UI.friend_requests;
        if (tab === 'outgoing') btn.textContent = UI.friend_sent;
    });
    const friendIdentifier = $('input-friend-identifier');
    if (friendIdentifier) friendIdentifier.placeholder = UI.friend_add_placeholder;
    const friendAddBtn = $('btn-friend-add');
    if (friendAddBtn) friendAddBtn.textContent = UI.friend_add;
    const incomingTitle = $('friend-incoming-title');
    if (incomingTitle) incomingTitle.textContent = UI.friend_requests;
    const outgoingTitle = $('friend-outgoing-title');
    if (outgoingTitle) outgoingTitle.textContent = UI.friend_sent;
    const friendListTitle = $('friend-list-title');
    if (friendListTitle) friendListTitle.textContent = UI.friend_list;
    const accountPopoverTitle = $('account-popover-title');
    if (accountPopoverTitle) accountPopoverTitle.textContent = UI.account;
    const accountModeLogin = $('btn-account-mode-login');
    if (accountModeLogin) accountModeLogin.textContent = UI.account_login;
    const accountModeRegister = $('btn-account-mode-register');
    if (accountModeRegister) accountModeRegister.textContent = UI.account_register;
    const accountUsernameLabel = $('label-account-username');
    if (accountUsernameLabel) accountUsernameLabel.textContent = UI.account_username;
    const accountPasswordLabel = $('label-account-password');
    if (accountPasswordLabel) accountPasswordLabel.textContent = UI.account_password;
    const accountPasswordConfirmLabel = $('label-account-password-confirm');
    if (accountPasswordConfirmLabel) accountPasswordConfirmLabel.textContent = UI.account_password_confirm;
    const accountPasswordChangeTitle = $('account-password-change-title');
    if (accountPasswordChangeTitle) accountPasswordChangeTitle.textContent = UI.account_change_password;
    const accountOldPasswordLabel = $('label-account-old-password');
    if (accountOldPasswordLabel) accountOldPasswordLabel.textContent = UI.account_old_password;
    const accountNewPasswordLabel = $('label-account-new-password');
    if (accountNewPasswordLabel) accountNewPasswordLabel.textContent = UI.account_new_password;
    const accountNewPasswordConfirmLabel = $('label-account-new-password-confirm');
    if (accountNewPasswordConfirmLabel) accountNewPasswordConfirmLabel.textContent = UI.account_new_password_confirm;
    const accountUsernameInput = $('input-account-username');
    if (accountUsernameInput) accountUsernameInput.placeholder = UI.account_username;
    const accountPasswordInput = $('input-account-password');
    if (accountPasswordInput) accountPasswordInput.placeholder = UI.account_password;
    const accountPasswordConfirmInput = $('input-account-password-confirm');
    if (accountPasswordConfirmInput) accountPasswordConfirmInput.placeholder = UI.account_password_confirm;
    const accountOldPasswordInput = $('input-account-old-password');
    if (accountOldPasswordInput) accountOldPasswordInput.placeholder = UI.account_old_password;
    const accountNewPasswordInput = $('input-account-new-password');
    if (accountNewPasswordInput) accountNewPasswordInput.placeholder = UI.account_new_password;
    const accountNewPasswordConfirmInput = $('input-account-new-password-confirm');
    if (accountNewPasswordConfirmInput) accountNewPasswordConfirmInput.placeholder = UI.account_new_password_confirm;
    const accountLoginBtn = $('btn-account-login');
    if (accountLoginBtn) accountLoginBtn.textContent = UI.account_login;
    const accountRegisterBtn = $('btn-account-register');
    if (accountRegisterBtn) accountRegisterBtn.textContent = UI.account_register;
    const accountChangePasswordBtn = $('btn-account-change-password');
    if (accountChangePasswordBtn) accountChangePasswordBtn.textContent = UI.account_change_password;
    const accountPopoverLogout = $('btn-account-popover-logout');
    if (accountPopoverLogout) accountPopoverLogout.textContent = UI.account_logout;
    const accountReplaysTitle = $('account-replays-title');
    if (accountReplaysTitle) accountReplaysTitle.textContent = UI.account_replays;
    const accountReplaysRefresh = $('btn-account-replays-refresh');
    if (accountReplaysRefresh) accountReplaysRefresh.textContent = UI.refresh;
    const accountReplayTitle = $('account-replay-title');
    if (accountReplayTitle) accountReplayTitle.textContent = UI.replay_viewer;
    document.querySelectorAll('[data-account-replay-control="prev"]').forEach((btn) => { btn.title = UI.replay_prev; if (btn.classList.contains('replay-icon-btn')) btn.textContent = '‹'; });
    document.querySelectorAll('[data-account-replay-control="play"]').forEach((btn) => { btn.title = UI.replay_play; if (btn.classList.contains('replay-icon-btn')) btn.textContent = '▶'; });
    document.querySelectorAll('[data-account-replay-control="pause"]').forEach((btn) => { btn.title = UI.replay_pause; if (btn.classList.contains('replay-icon-btn')) btn.textContent = 'Ⅱ'; });
    document.querySelectorAll('[data-account-replay-control="next"]').forEach((btn) => { btn.title = UI.replay_next; if (btn.classList.contains('replay-icon-btn')) btn.textContent = '›'; });
    document.querySelectorAll('[data-account-replay-speed="instant"]').forEach((btn) => { btn.title = UI.replay_instant; if (btn.classList.contains('replay-speed-btn')) btn.textContent = '»'; });
    const guestDivider = $('guest-divider-label');
    if (guestDivider) guestDivider.textContent = UI.account_guest;
    renderAccountState();
    const noMods = $('settings-no-mods');
    if (noMods) noMods.textContent = UI.no_mod_files;
    const btnSettingsClose = $('btn-settings-close');
    if (btnSettingsClose) btnSettingsClose.textContent = UI.ok;
    const settingsServer = $('settings-section-server');
    if (settingsServer) settingsServer.textContent = UI.settings_server;
    const settingsLabelServer = $('settings-label-server');
    if (settingsLabelServer) settingsLabelServer.textContent = UI.settings_server_addr;
    const serverInput = $('settings-server-input');
    if (serverInput) serverInput.placeholder = UI.server_placeholder;
    const lobbyHeader = document.querySelector('#view-lobby .lobby-header h2');
    if (lobbyHeader) lobbyHeader.textContent = UI.lobby_title;
    const onlinePlayersH3 = document.querySelector('#view-lobby .lobby-left .lobby-section:first-child h3');
    if (onlinePlayersH3) onlinePlayersH3.textContent = UI.online_players;
    const ongoingGamesH3 = document.querySelector('#view-lobby .lobby-left .lobby-section:last-child h3');
    if (ongoingGamesH3) ongoingGamesH3.textContent = UI.ongoing_games;
    const chatH3 = document.querySelector('#view-lobby .lobby-right .lobby-section h3');
    if (chatH3) chatH3.textContent = UI.chat_title;
    const nicknameLabel = document.querySelector('label[for="input-nickname"]');
    if (nicknameLabel) nicknameLabel.textContent = UI.nickname;
    const nicknameInput = $('input-nickname');
    if (nicknameInput) nicknameInput.placeholder = UI.nickname_placeholder;
    if (nicknameInput && !nicknameInput.value) nicknameInput.value = localStorage.getItem('gtn_nickname') || '';
    const gameChatInput = $('game-chat-input');
    if (gameChatInput) gameChatInput.placeholder = UI.message_placeholder;
    const lobbyChatInput = $('lobby-chat-input');
    if (lobbyChatInput) lobbyChatInput.placeholder = UI.message_placeholder;
    const phaseChatInput = $('phase-chat-input');
    if (phaseChatInput) phaseChatInput.placeholder = UI.message_placeholder;
    const phaseChatTitle = $('phase-chat-title');
    if (phaseChatTitle) phaseChatTitle.textContent = UI.chat_title;
    const draftH2 = document.querySelector('#view-draft h2');
    if (draftH2) draftH2.textContent = UI.draft_phase;
    const eventH2 = document.querySelector('#view-event-select h2');
    if (eventH2) eventH2.textContent = UI.select_event;
    const eventDesc = document.querySelector('#view-event-select .event-desc');
    if (eventDesc) eventDesc.textContent = UI.select_event_desc;
    const btnDraftReroll = $('btn-draft-reroll');
    if (btnDraftReroll) btnDraftReroll.textContent = UI.draft_reroll;
    const btnEventReroll = $('btn-event-reroll');
    if (btnEventReroll) btnEventReroll.textContent = UI.event_reroll;
    const btnPhaseChatSend = $('btn-phase-chat-send');
    if (btnPhaseChatSend) btnPhaseChatSend.textContent = UI.send;
    const btnReturnLobby = $('btn-return-lobby');
    if (btnReturnLobby) btnReturnLobby.textContent = UI.return_lobby;
    const btnReportMatch = $('btn-report-match');
    if (btnReportMatch) btnReportMatch.textContent = UI.report_match || UI.report;
    const btnRematch = $('btn-rematch');
    if (btnRematch) btnRematch.textContent = UI.rematch;
    const btnSurrender = $('btn-surrender');
    if (btnSurrender) btnSurrender.textContent = UI.surrender;
    const btnViewDeck = $('btn-view-deck');
    if (btnViewDeck) btnViewDeck.textContent = UI.view_deck;
    const btnSpectateViewDeck = $('btn-spectate-view-deck');
    if (btnSpectateViewDeck) btnSpectateViewDeck.textContent = UI.view_deck;
    const classicViewDeck = $('classic-view-deck');
    if (classicViewDeck) classicViewDeck.textContent = UI.view_deck;
    const classicSwitchPerspective = $('classic-switch-perspective');
    if (classicSwitchPerspective && !classicSwitchPerspective.dataset.dynamic) classicSwitchPerspective.textContent = UI.switch_perspective;
    const btnEndTurn = $('btn-end-turn');
    if (btnEndTurn) btnEndTurn.textContent = UI.end_turn;
    const btnSoloNextDraw = $('btn-solo-next-draw');
    if (btnSoloNextDraw) btnSoloNextDraw.textContent = UI.set_next_draw;
    const btnSoloEdit = $('btn-solo-edit');
    if (btnSoloEdit) btnSoloEdit.textContent = UI.pause_edit;
    const classicSoloNextDraw = $('classic-solo-next-draw');
    if (classicSoloNextDraw) classicSoloNextDraw.textContent = UI.set_next_draw;
    const classicSoloEdit = $('classic-solo-edit');
    if (classicSoloEdit) classicSoloEdit.textContent = UI.pause_edit;
    const classicUrfReplace = $('classic-urf-replace');
    if (classicUrfReplace) classicUrfReplace.textContent = UI.urf_replace;
    const classicUrfSell = $('classic-urf-sell');
    if (classicUrfSell) classicUrfSell.textContent = UI.urf_sell;
    const soloTitle = $('solo-title');
    if (soloTitle) soloTitle.textContent = UI.solo_training;
    const btnSoloLoad = $('btn-solo-load');
    if (btnSoloLoad) btnSoloLoad.textContent = UI.load_last;
    const btnSoloSave = $('btn-solo-save');
    if (btnSoloSave) btnSoloSave.textContent = UI.save_decks;
    const btnSoloStart = $('btn-solo-start');
    if (btnSoloStart) btnSoloStart.textContent = UI.start_training;
    const btnSoloBack = $('btn-solo-back');
    if (btnSoloBack) btnSoloBack.textContent = UI.back_to_home;
    const btnSoloClearA = $('btn-solo-clear-a');
    if (btnSoloClearA) btnSoloClearA.textContent = UI.clear_deck || '清空牌组';
    const btnSoloClearB = $('btn-solo-clear-b');
    if (btnSoloClearB) btnSoloClearB.textContent = UI.clear_deck || '清空牌组';
    const soloSearch = $('solo-card-search');
    if (soloSearch) soloSearch.placeholder = UI.search_cards;
    const soloDeckATitle = $('solo-deck-a-title');
    if (soloDeckATitle) soloDeckATitle.textContent = UI.solo_deck_a;
    const soloDeckBTitle = $('solo-deck-b-title');
    if (soloDeckBTitle) soloDeckBTitle.textContent = UI.solo_deck_b;
    const battleLogHeader = document.querySelector('#battle-log .log-header');
    if (battleLogHeader) battleLogHeader.textContent = UI.battle_log;
    const oppLabel = $('opp-label');
    if (oppLabel && (!gameState || !gameState.opponent_name)) oppLabel.textContent = UI.opponent;
    const youLabel = $('you-label');
    if (youLabel && (!gameState || !gameState.your_name)) youLabel.textContent = UI.you;
    const oppInfo = $('opp-info');
    if (oppInfo && (!gameState || !gameState.opponent)) {
        setPileInfoText(oppInfo, isMinimalUiStyle() ? { text: '✦0 ▣0', title: UI.hand_deck_zero_opp } : { text: UI.hand_deck_zero_opp, title: '' });
    }
    const youInfo = $('you-info');
    if (youInfo && (!gameState || !gameState.you)) {
        setPileInfoText(youInfo, isMinimalUiStyle() ? { text: '✦0 ▣0 ⟲0', title: UI.hand_deck_zero_you } : { text: UI.hand_deck_zero_you, title: '' });
    }
    const onlineCount = $('lobby-online-count');
    if (onlineCount && phase !== 'lobby') onlineCount.textContent = tf('online_count', 0);
    const switchBtn = $('btn-switch-perspective');
    if (switchBtn && !switchBtn.dataset.dynamic) switchBtn.textContent = UI.switch_perspective;
    const leaveSpectateBtn = $('btn-leave-spectate');
    if (leaveSpectateBtn) leaveSpectateBtn.textContent = UI.leave_spectate;
    const promptCancel = $('game-prompt-cancel');
    if (promptCancel) promptCancel.textContent = UI.cancel;
    const modEditorTitle = document.querySelector('#view-mod-editor h2');
    if (modEditorTitle) modEditorTitle.textContent = UI.mod_editor;
    const modEditorArea = $('mod-editor-area');
    if (modEditorArea) modEditorArea.placeholder = UI.mod_editor_placeholder;
    const btnModLoad = $('btn-mod-load');
    if (btnModLoad) btnModLoad.textContent = UI.load_mod;
    const btnModSave = $('btn-mod-save');
    if (btnModSave) btnModSave.textContent = UI.save;
    const btnModValidate = $('btn-mod-validate');
    if (btnModValidate) btnModValidate.textContent = UI.validate_json;
    const btnModBack = $('btn-mod-back');
    if (btnModBack) btnModBack.textContent = UI.back_to_home;
    const rotateText = document.querySelector('.rotate-text');
    if (rotateText) rotateText.textContent = UI.rotate_prompt;
    const rotateSub = document.querySelector('.rotate-text-en');
    if (rotateSub) rotateSub.textContent = UI.rotate_hint_sub;
    const rotateButton = $('btn-dismiss-rotate');
    if (rotateButton) rotateButton.textContent = UI.continue_enter;
    const btnLobbyChatSend = $('btn-lobby-chat-send');
    if (btnLobbyChatSend) btnLobbyChatSend.textContent = UI.send;
    const btnGameChatSend = $('btn-game-chat-send');
    if (btnGameChatSend) btnGameChatSend.textContent = UI.send;
    updateGameChatChannelOptions(gameState);
    updateCompactUiText();
}

function $(id) { return document.getElementById(id); }

function restartTransientClass(el, className, duration = 650) {
    if (!el || !className) return;
    el.classList.remove(className);
    void el.offsetWidth;
    el.classList.add(className);
    setTimeout(() => {
        if (el && el.classList) el.classList.remove(className);
    }, duration);
}

function flashTargetRegion(playerId) {
    const region = getPlayerRegionById(playerId);
    restartTransientClass(region, 'target-feedback-pulse', 720);
}

function maybeAnimateTurnFocus(gs) {
    if (!gs) return;
    const key = `${gs.mode || ''}:${gs.phase || ''}:${gs.round_num || 0}:${normalizePlayerId(gs.current_player)}`;
    const shouldAnimate = lastRenderedTurnKey && lastRenderedTurnKey !== key && gs.phase === 'action';
    lastRenderedTurnKey = key;
    if (!shouldAnimate) return;
    requestAnimationFrame(() => {
        const region = getPlayerRegionById(gs.current_player);
        restartTransientClass(region, 'turn-focus-pulse', 900);
    });
}

function formatRoundStatus(gs, phaseText = '') {
    const roundNum = Number(gs && gs.round_num);
    const phaseName = phaseText || ((gs && gs.phase) === 'draft'
        ? UI.draft_phase
        : (gs && gs.phase) === 'event_select'
            ? UI.select_event
            : '');
    if (!Number.isFinite(roundNum) || roundNum <= 0) {
        if ((gs && gs.phase) === 'draft') return UI.draft_phase;
        if ((gs && gs.phase) === 'event_select') return UI.select_event;
        return phaseName || UI.draft_phase;
    }
    return UI.round_status.replace('{0}', roundNum).replace('{1}', phaseName);
}

function formatCompactRoundStatus(gs, phaseText = '') {
    const roundNum = Number(gs && gs.round_num);
    if (!Number.isFinite(roundNum) || roundNum <= 0) {
        if ((gs && gs.phase) === 'draft') return UI.draft_phase;
        if ((gs && gs.phase) === 'event_select') return UI.select_event;
        return phaseText || UI.draft_phase;
    }
    return `R${roundNum} · ${phaseText}`;
}

function showView(viewId) {
    const el = $(viewId);
    const sameView = activeViewId === viewId && el && !el.classList.contains('hidden');
    if (!sameView) {
        removeFloatingCardPreview();
        document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
        if (el) el.classList.remove('hidden');
        activeViewId = viewId;
        updatePhaseChatPanelVisibility(viewId);
    }
    const accountTop = $('btn-account-top');
    if (accountTop) accountTop.classList.toggle('hidden', viewId !== 'view-login');
    const friendsTop = $('btn-friends-top');
    if (friendsTop) friendsTop.classList.toggle('hidden', viewId !== 'view-login' || !currentAccount);
    const skinTop = $('btn-skin-top');
    if (skinTop) skinTop.classList.toggle('hidden', viewId !== 'view-login');
    if (viewId !== 'view-login') {
        toggleAccountPopover(false);
        toggleFriendsPopover(false);
    }
    if (!sameView && viewId !== 'view-game') {
        const logContainer = $('battle-log');
        const logContent = logContainer ? logContainer.querySelector('.log-content') : null;
        resetBattleLogState(logContent);
        renderedBattleLogMatchKey = '';
        lastRenderedTurnKey = '';
        lastStatusSignatures.clear();
        updateModeSpecificControls({ solo: false, phase: '' });
        refreshBaseStatus(viewId);
    }
}

function isNetworkMatchPhase(value = phase) {
    return !soloMode && !replayMode && [
        'draft', 'event_select', 'event_reveal', 'event_sub_choice', 'playing', 'action', 'draw', 'response', 'choice', 'game_over', 'reconnecting',
    ].includes(String(value || ''));
}

function shouldIgnoreLobbyUpdateWhileInMatch() {
    if (soloMode || replayMode) return false;
    if (isNetworkMatchPhase(phase)) return true;
    return [
        'view-draft',
        'view-event-select',
        'view-game',
        'view-gameover',
    ].includes(activeViewId || '');
}

function clearNetworkMatchStateForLobby() {
    if (soloMode || replayMode) return;
    gameState = {};
    draftState = {};
    eventSelectData = {};
    isSpectating = false;
    pendingSpectateRoomId = null;
    activeSpectateRoomId = null;
    spectatePerspective = 0;
    pendingPlayCard = null;
    responsePending = false;
    responseData = null;
    activeV2UiRequestId = null;
    removeFloatingCardPreview();
    clearSelectedPlayCard();
    clearPendingServerAction();
    resetRematchUiState();
}

let gallerySelectedId = null;
let galleryMode = 'cards';
let rulesScrollTop = 0;
let galleryReturnToRules = false;
let galleryMultiPetalPreviewId = null;
let galleryShowMultiPetalPreview = false;

function bindRulesCardLinks(root) {
    if (!root) return;
    root.querySelectorAll('[data-card]').forEach(link => {
        link.onclick = () => {
            const body = link.closest('#rules-body, #about-rules-body, .rules-body');
            if (body) rulesScrollTop = body.scrollTop;
            galleryReturnToRules = true;
            hideModal();
            closeAbout();
            showCardGallery(link.getAttribute('data-card'));
        };
    });
}

function setAboutPage(page) {
    const isCredits = page === 'credits';
    const rulesPage = $('about-page-rules');
    const creditsPage = $('about-page-credits');
    const rulesTab = $('about-tab-rules');
    const creditsTab = $('about-tab-credits');
    if (rulesPage) rulesPage.classList.toggle('hidden', isCredits);
    if (creditsPage) creditsPage.classList.toggle('hidden', !isCredits);
    if (rulesTab) rulesTab.classList.toggle('active', !isCredits);
    if (creditsTab) creditsTab.classList.toggle('active', isCredits);
}

function formatNamedTemplate(template, values) {
    return String(template || '').replace(/\{([a-zA-Z0-9_]+)\}/g, (_, key) => values[key] ?? '');
}

function rulesTypeSpan(type, label) {
    return `<span class="rules-type ${type}">${escapeHtml(label)}</span>`;
}

function rulesCardLink(id, type) {
    const cd = CARD_DEFS[id];
    const label = cd ? getCardName(cd) : id;
    return `<a class="rules-card-link ${type}" data-card="${escapeHtml(id)}">${escapeHtml(label)}</a>`;
}

function getRulesTemplateValues() {
    const thorn = rulesTypeSpan('thorn', UI.rules_type_thorn || 'Thorn');
    const bloom = rulesTypeSpan('bloom', UI.rules_type_bloom || 'Bloom');
    const root = rulesTypeSpan('root', UI.rules_type_root || 'Root');
    const guard = rulesTypeSpan('guard', UI.rules_type_guard || 'Guard');
    return {
        thorn,
        bloom,
        root,
        guard,
        thornRaw: rulesTypeSpan('thorn', 'Thorn'),
        bloomRaw: rulesTypeSpan('bloom', 'Bloom'),
        rootRaw: rulesTypeSpan('root', 'Root'),
        guardRaw: rulesTypeSpan('guard', 'Guard'),
        basic: rulesCardLink('Basic', 'thorn'),
        bone: rulesCardLink('Bone', 'thorn'),
        fire: rulesCardLink('Fire', 'bloom'),
        leaf: rulesCardLink('Leaf', 'root'),
        stinger: rulesCardLink('Stinger', 'thorn'),
        sewage: rulesCardLink('Sewage', 'bloom'),
        bubble: rulesCardLink('Bubble', 'guard'),
    };
}

function renderRulesBodyHtml() {
    const values = getRulesTemplateValues();
    const paragraph = key => formatNamedTemplate(UI[key], values);
    return `
        <h4>${escapeHtml(UI.rules_goal_title)}</h4>
        <p>${paragraph('rules_goal_text')}</p>
        <h4>${escapeHtml(UI.rules_resources_title)}</h4>
        <p>${paragraph('rules_resources_text')}</p>
        <h4>${escapeHtml(UI.rules_types_title)}</h4>
        <p>${paragraph('rules_types_text')}</p>
        <h4>${escapeHtml(UI.rules_flow_title)}</h4>
        <p>${paragraph('rules_flow_text')}</p>
        <h4>${escapeHtml(UI.rules_keywords_title)}</h4>
        <p>${paragraph('rules_keywords_text')}</p>
        <h4>${escapeHtml(UI.rules_examples_title)}</h4>
        <p>${paragraph('rules_examples_text')}</p>
    `;
}

function renderAboutRulesBody() {
    const aboutBody = $('about-rules-body');
    if (!aboutBody) return;
    aboutBody.innerHTML = renderRulesBodyHtml();
    ensureTutorialButtons();
    bindRulesCardLinks(aboutBody);
}

function ensureTutorialButtons() {
    const aboutBody = $('about-rules-body');
    if (aboutBody && !$('btn-about-tutorial')) {
        const row = document.createElement('div');
        row.className = 'rules-tutorial-entry';
        row.innerHTML = `<button id="btn-about-tutorial" class="btn btn-primary" type="button">${UI.tutorial_start}</button>`;
        aboutBody.insertBefore(row, aboutBody.firstChild);
    }
    const aboutBtn = $('btn-about-tutorial');
    if (aboutBtn) {
        aboutBtn.textContent = UI.tutorial_start;
        aboutBtn.onclick = () => startTutorial('about');
    }
}

function openAbout() {
    const panel = $('about-panel');
    if (panel) panel.classList.remove('hidden');
    setAboutPage('rules');
    ensureTutorialButtons();
    const body = $('about-rules-body');
    bindRulesCardLinks(body);
    if (body && rulesScrollTop) requestAnimationFrame(() => { body.scrollTop = rulesScrollTop; });
}

function closeAbout() {
    const panel = $('about-panel');
    if (panel) panel.classList.add('hidden');
}

function setHiddenFeaturesEnabled(enabled) {
    if (enabled) {
        localStorage.setItem(HIDDEN_FEATURES_KEY, '1');
    } else {
        localStorage.removeItem(HIDDEN_FEATURES_KEY);
        if (currentUiStyle === 'classic') applyUiStyle('minimal');
        else updateUiStyleAvailability();
    }
    updateUiStyleAvailability();
}

function promptHiddenFeatureUnlock() {
    showModal(`
        <div class="hidden-feature-unlock">
            <h3>隐藏功能</h3>
            <label class="report-field">
                <span>请输入内测秘钥：</span>
                <input id="hidden-feature-key-input" type="password" autocomplete="current-password">
            </label>
            <div id="hidden-feature-error" class="report-error hidden"></div>
            <div class="modal-buttons">
                <button id="hidden-feature-cancel" class="btn btn-secondary" type="button">取消</button>
                <button id="hidden-feature-confirm" class="btn btn-primary" type="button">确认</button>
            </div>
        </div>
    `);
    const input = $('hidden-feature-key-input');
    const errorEl = $('hidden-feature-error');
    const cancelBtn = $('hidden-feature-cancel');
    const confirmBtn = $('hidden-feature-confirm');
    if (input) input.focus();
    if (cancelBtn) cancelBtn.onclick = hideModal;
    const submit = async () => {
        if (!confirmBtn || !input) return;
        confirmBtn.disabled = true;
        if (errorEl) errorEl.classList.add('hidden');
        try {
            const res = await fetch('/api/hidden-features/unlock', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: input.value || '' }),
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok || !data.success) throw new Error(data.error || '秘钥错误');
            setHiddenFeaturesEnabled(true);
            hideModal();
            flashStatus('隐藏功能已开启', 1800);
        } catch (err) {
            if (errorEl) {
                errorEl.textContent = err && err.message ? err.message : '解锁失败';
                errorEl.classList.remove('hidden');
            }
        } finally {
            confirmBtn.disabled = false;
        }
    };
    if (confirmBtn) confirmBtn.onclick = submit;
    if (input) input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') submit();
    }, { once: false });
}

function bindHiddenFeatureLongPress() {
    const title = $('credits-special-title');
    if (!title || title.dataset.hiddenFeatureBound === '1') return;
    title.dataset.hiddenFeatureBound = '1';
    title.title = '长按';
    let timer = null;
    const clear = () => {
        if (timer) clearTimeout(timer);
        timer = null;
    };
    const start = (event) => {
        if (event && event.button != null && event.button !== 0) return;
        clear();
        const delay = hiddenFeaturesEnabled() ? 1000 : 2000;
        timer = setTimeout(() => {
            timer = null;
            if (hiddenFeaturesEnabled()) {
                setHiddenFeaturesEnabled(false);
                flashStatus('隐藏功能已关闭', 1800);
            } else {
                promptHiddenFeatureUnlock();
            }
        }, delay);
    };
    title.addEventListener('pointerdown', start);
    title.addEventListener('pointerup', clear);
    title.addEventListener('pointerleave', clear);
    title.addEventListener('pointercancel', clear);
    title.addEventListener('contextmenu', (event) => event.preventDefault());
}

function setGalleryMode(mode) {
    galleryMode = mode || 'cards';
    ['cards', 'tags', 'events', 'statuses'].forEach(name => {
        const tab = $(`gallery-tab-${name}`);
        if (tab) tab.classList.toggle('active', galleryMode === name);
    });
    const search = $('gallery-search');
    if (search) search.placeholder = UI.gallery_search;
}

function showCardGallery(selectedId = null, mode = 'cards') {
    showView('view-card-gallery');
    phase = 'gallery';
    setGalleryMode(mode);
    const backBtn = $('btn-gallery-back');
    if (backBtn) backBtn.textContent = galleryReturnToRules ? UI.gallery_back_rules : UI.back_to_home;
    if (selectedId) gallerySelectedId = selectedId;
    if (!gallerySelectedId || !CARD_DEFS[gallerySelectedId] || gallerySelectedId === 'Error') {
        gallerySelectedId = Object.keys(CARD_DEFS).filter(id => id !== 'Error').sort(compareGalleryCards)[0] || null;
    }
    renderCardGallery();
}

function getCustomTagDef(flag) {
    const normalized = normalizeCardFlag(flag);
    return (CUSTOM_TAG_DEFS && CUSTOM_TAG_DEFS[normalized]) || null;
}

function getCustomStatusDef(statusId) {
    return (CUSTOM_STATUS_DEFS && CUSTOM_STATUS_DEFS[statusId]) || null;
}

function getRegistryText(def, field, fallback = '') {
    if (!def) return fallback;
    const langKey = `${field}_${currentLang}`;
    const cnKey = `${field}_cn`;
    const enKey = `${field}_en`;
    return def[langKey] || def[cnKey] || def[enKey] || def[field] || def.name || fallback;
}

function safeRegistryColor(value, fallback = '#2C3E50') {
    const text = String(value || '').trim();
    if (/^#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$/.test(text)) return text;
    if (/^rgba?\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}(\s*,\s*(0|1|0?\.\d+))?\s*\)$/.test(text)) return text;
    if (/^[a-zA-Z]+$/.test(text)) return text;
    return fallback;
}

function customTagHtml(flag, text = null) {
    const normalized = normalizeCardFlag(flag);
    const def = getCustomTagDef(normalized);
    const label = text || getRegistryText(def, 'name', normalized);
    const color = safeRegistryColor(def && def.color, '#2C3E50');
    const icon = def && def.icon ? `${escapeHtml(def.icon)} ` : '';
    return `<span class="card-flag custom" style="color:${color};border-color:${color};background:#fff">${icon}${escapeHtml(label)}</span>`;
}

function makeGalleryFlagHtml(flag) {
    const normalized = normalizeCardFlag(flag);
    const custom = getCustomTagDef(normalized);
    if (custom) return customTagHtml(normalized);
    const style = CARD_FLAG_STYLES[normalized];
    const label = getFlagLabel(normalized);
    if (style) return `<span class="card-flag ${style.cls}">${label}</span>`;
    return `<span class="card-flag">${label}</span>`;
}

function getGalleryFlagDescription(flag) {
    const normalized = normalizeCardFlag(flag);
    const custom = getCustomTagDef(normalized);
    if (custom) return getRegistryText(custom, 'description', custom.description || '');
    return UI[`tag_desc_${normalized}`] || UI.tag_desc_default;
}

function isGalleryMechanicFlag(flag) {
    return GALLERY_MECHANIC_FLAGS.has(flag);
}

function getGalleryFlagEnglishLabel(flag) {
    const normalized = normalizeCardFlag(flag);
    const custom = getCustomTagDef(normalized);
    if (custom) return custom.name_en || custom.name || normalized;
    return I18N.en[`tag_${normalized}`] || I18N.en[`flag_${normalized}`] || I18N.en[normalized] || normalized;
}

function getGalleryFlagUsers(flag) {
    const normalized = normalizeCardFlag(flag);
    const defs = Object.values(CARD_DEFS).filter(isPublicCardDef);
    if (normalized === 'fusion_layer') return defs.filter(cd => cd && cd.id === 'Fusion');
    if (normalized === 'fission_layer') return defs.filter(cd => cd && cd.id === 'Fission');
    return defs.filter(cd => normalizeFlagList(cd.flags || []).includes(normalized));
}

const GALLERY_CARD_TYPE_ORDER = { thorn: 0, bloom: 1, guard: 2, root: 3 };

function isPublicCardDef(cd) {
    return !!(cd && cd.id !== 'Error');
}

function localizedModNameFromFields(obj, fallback = '') {
    if (!obj) return fallback;
    const zhName = obj.name_cn || obj.source_mod_name_cn;
    const enName = obj.name_en || obj.source_mod_name_en || obj.name || obj.source_mod_name;
    if (currentLang === 'zh' && zhName) return zhName;
    return enName || zhName || fallback || obj.filename || '';
}

function localizedModDescriptionFromFields(obj, fallback = '') {
    if (!obj) return fallback;
    const zhText = obj.description_cn;
    const enText = obj.description_en || obj.description;
    if (currentLang === 'zh' && zhText) return zhText;
    return enText || zhText || fallback || '';
}

function compareGalleryCards(a, b) {
    const ca = typeof a === 'string' ? CARD_DEFS[a] : a;
    const cb = typeof b === 'string' ? CARD_DEFS[b] : b;
    if (!ca && !cb) return String(a || '').localeCompare(String(b || ''), 'en');
    if (!ca) return 1;
    if (!cb) return -1;
    const va = ca.source_mod_is_vanilla ? 0 : 1;
    const vb = cb.source_mod_is_vanilla ? 0 : 1;
    if (va !== vb) return va - vb;
    if (va !== 0) {
        const ma = String(ca.source_mod_name_en || ca.source_mod_sort_name || ca.source_mod_name || ca.source_mod_filename || '').toLowerCase();
        const mb = String(cb.source_mod_name_en || cb.source_mod_sort_name || cb.source_mod_name || cb.source_mod_filename || '').toLowerCase();
        const modCmp = ma.localeCompare(mb, 'en');
        if (modCmp) return modCmp;
    }
    const ta = GALLERY_CARD_TYPE_ORDER[ca.card_type] ?? 99;
    const tb = GALLERY_CARD_TYPE_ORDER[cb.card_type] ?? 99;
    if (ta !== tb) return ta - tb;
    return String(ca.id || '').localeCompare(String(cb.id || ''), 'en');
}

function hasGalleryMultiPetalPreview(cd) {
    if (!cd) return false;
    if (cd.upgraded_image_url || cd.upgraded_image) return true;
    const hits = Number(cd.hits || 1);
    if (Number.isFinite(hits) && hits >= 2) return true;
    const text = `${getCardEffectText(cd) || ''} ${cd.effect_text || ''}`.toLowerCase();
    return /[（(]\s*\d+\s*子瓣\s*[）)]|[x×]\s*\d+\s*层|子瓣/.test(text);
}

function getAllGalleryFlags() {
    const flags = new Set(Object.keys(CARD_FLAG_STYLES));
    Object.keys(CUSTOM_TAG_DEFS || {}).forEach(flag => {
        const normalized = normalizeCardFlag(flag);
        if (normalized) flags.add(normalized);
    });
    Object.values(CARD_DEFS).filter(isPublicCardDef).forEach(cd => (cd.flags || []).forEach(flag => {
        const normalized = normalizeCardFlag(flag);
        if (normalized) flags.add(normalized);
    }));
    return [...flags].sort((a, b) => getFlagLabel(a).localeCompare(getFlagLabel(b)));
}

function renderCardGallery() {
    const list = $('gallery-card-list');
    const detail = $('gallery-detail');
    if (!list || !detail) return;
    const q = (($('gallery-search') || {}).value || '').trim().toLowerCase();
    if (galleryMode === 'tags') {
        renderTagGallery(list, detail, q);
        return;
    }
    if (galleryMode === 'events') {
        renderOpeningEventGallery(list, detail, q);
        return;
    }
    if (galleryMode === 'statuses') {
        renderStatusGallery(list, detail, q);
        return;
    }
    const ids = Object.keys(CARD_DEFS)
        .filter(id => id !== 'Error')
        .filter(id => {
            const cd = CARD_DEFS[id];
            return !q || cardSearchText(id).includes(q);
        })
        .sort(compareGalleryCards);
    list.innerHTML = '';
    ids.forEach(id => {
        const cd = CARD_DEFS[id];
        const flags = [...new Set(normalizeFlagList(cd.flags || []).filter(flag => flag !== 'infinite_exclude'))].map(getFlagLabel).join(' / ');
        const row = document.createElement('div');
        row.className = 'gallery-card-row' + (id === gallerySelectedId ? ' active' : '');
        row.innerHTML = `<div class="gallery-row-title">${getCardName(cd)}</div>${flags ? `<div class="gallery-row-meta">${flags}</div>` : ''}`;
        row.onclick = () => { gallerySelectedId = id; renderCardGallery(); };
        list.appendChild(row);
    });
    if (!ids.includes(gallerySelectedId)) gallerySelectedId = ids[0] || null;
    const cd = CARD_DEFS[gallerySelectedId];
    if (!cd) {
        detail.innerHTML = `<p>${UI.gallery_no_items}</p>`;
        return;
    }
    gallerySelectedId = cd.id;
    if (galleryMultiPetalPreviewId !== cd.id) {
        galleryMultiPetalPreviewId = cd.id;
        galleryShowMultiPetalPreview = false;
    }
    const canPreviewMultiPetal = hasGalleryMultiPetalPreview(cd);
    const previewCardDict = {
        def_id: cd.id,
        instance_flags: [],
        disabled_flags: [],
        extra_hits: canPreviewMultiPetal && galleryShowMultiPetalPreview ? 1 : 0,
    };
    const cardEl = createCardElement(previewCardDict, { small: false, showAllFlags: true });
    detail.innerHTML = `<div class="gallery-detail-card"><div id="gallery-card-preview"></div><div class="gallery-detail-info">
        <h3>${escapeHtml(getCardName(cd))}</h3>
        ${buildCardIntroSummaryHtml(cd)}
        <div class="term-intro-list gallery-term-intro-list">${renderTermIntroItems(collectCardIntroTerms(previewCardDict))}</div>
    </div></div>`;
    const preview = $('gallery-card-preview');
    if (preview) {
        preview.appendChild(cardEl);
        if (canPreviewMultiPetal) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-secondary gallery-multipetal-toggle' + (galleryShowMultiPetalPreview ? ' active' : '');
            btn.textContent = '重瓣';
            btn.onclick = () => {
                galleryShowMultiPetalPreview = !galleryShowMultiPetalPreview;
                renderCardGallery();
            };
            preview.appendChild(btn);
        }
    }
}

function renderTagGallery(list, detail, q) {
    const flags = getAllGalleryFlags().filter(flag => {
        const en = getGalleryFlagEnglishLabel(flag);
        const text = `${flag} ${getFlagLabel(flag)} ${en}`.toLowerCase();
        return !q || text.includes(q);
    });
    if (!flags.includes(gallerySelectedId)) gallerySelectedId = flags[0] || null;
    list.innerHTML = '';
    flags.forEach(flag => {
        const usedBy = getGalleryFlagUsers(flag);
        const row = document.createElement('div');
        row.className = 'gallery-card-row' + (flag === gallerySelectedId ? ' active' : '');
        row.innerHTML = `<div class="gallery-row-title">${getFlagLabel(flag)}</div><div class="gallery-row-meta">${tf('gallery_card_count', usedBy.length)}</div>`;
        row.onclick = () => { gallerySelectedId = flag; renderCardGallery(); };
        list.appendChild(row);
    });
    if (!gallerySelectedId) {
        detail.innerHTML = `<p>${UI.gallery_no_items}</p>`;
        return;
    }
    const usedBy = getGalleryFlagUsers(gallerySelectedId)
        .sort(compareGalleryCards);
    const relatedLabel = isGalleryMechanicFlag(gallerySelectedId)
        ? (UI.gallery_related_cards || UI.gallery_cards_with_tag)
        : UI.gallery_cards_with_tag;
    detail.innerHTML = `<div class="gallery-simple-detail">
        <h3>${getFlagLabel(gallerySelectedId)}</h3>
        <div class="gallery-tag-list">${makeGalleryFlagHtml(gallerySelectedId)}</div>
        <p><b>ID：</b>${gallerySelectedId}</p>
        <p><b>${UI.gallery_explanation}：</b>${getIntroFlagDescription(gallerySelectedId, getCustomTagDef(gallerySelectedId))}</p>
        <p><b>${relatedLabel}：</b>${usedBy.length ? usedBy.map(getCardName).join(' / ') : '-'}</p>
    </div>`;
}

function renderOpeningEventGallery(list, detail, q) {
    const events = (openingEvents || []).filter(ev => {
        const text = [
            ev.id,
            getLocalizedEventText(ev, 'name'),
            getLocalizedEventText(ev, 'desc'),
            (ev.name_i18n || {}).en || '',
            (ev.desc_i18n || {}).en || '',
        ].join(' ').toLowerCase();
        return !q || text.includes(q);
    });
    const eventIds = events.map(ev => `event:${ev.id}`);
    if (!eventIds.includes(gallerySelectedId)) gallerySelectedId = eventIds[0] || null;
    list.innerHTML = '';
    events.forEach(ev => {
        const id = `event:${ev.id}`;
        const row = document.createElement('div');
        row.className = 'gallery-card-row' + (id === gallerySelectedId ? ' active' : '');
        row.innerHTML = `<div class="gallery-row-title">${getLocalizedEventText(ev, 'name') || '?'}</div><div class="gallery-row-meta">${colorizeCardText(getLocalizedEventText(ev, 'desc') || '')}</div>`;
        row.onclick = () => { gallerySelectedId = id; renderCardGallery(); };
        bindInlineCardChips(row);
        list.appendChild(row);
    });
    const selectedEventId = gallerySelectedId ? String(gallerySelectedId).replace('event:', '') : null;
    const ev = events.find(item => String(item.id) === selectedEventId) || events[0];
    if (!ev) {
        detail.innerHTML = `<p>${UI.gallery_no_items}</p>`;
        return;
    }
    gallerySelectedId = `event:${ev.id}`;
    detail.innerHTML = `<div class="gallery-simple-detail">
        <h3>${getLocalizedEventText(ev, 'name') || '?'}</h3>
        <p><b>ID：</b>${ev.id}</p>
        <p>${colorizeCardText(getLocalizedEventText(ev, 'desc') || '')}</p>
    </div>`;
    bindInlineCardChips(detail);
}

function getAllStatusDefs() {
    const result = new Map();
    const termLib = getTermIntroLibrary();
    const builtInList = [
        { key: 'poison', label: UI.status_poison, desc: termLib.P ? termLib.P.desc : '', color: COLORS.poison },
        { key: 'fire', label: UI.status_fire, desc: termLib.F ? termLib.F.desc : '', color: COLORS.fire },
        { key: 'toxic', label: UI.status_toxic, desc: termLib.toxic ? termLib.toxic.desc : '', color: '#6C3483' },
        { key: 'triangle', label: UI.status_triangle || '三角形', desc: '每层会提高三角形的后续伤害，上限 4 层；裂变三角形时，每一段都会按当时层数重新计算。', color: COLORS.non_stack },
        { key: 'nazar', label: UI.status_nazar, desc: '受到较小 D 时回复生命；达到条件后会消耗层数。', color: COLORS.magic },
        { key: 'equip_protect', label: UI.status_equip_protect, desc: '保护装备不被摧毁效果破坏，常用于应对污水这类摧毁装备的牌。', color: COLORS.indestructible },
        { key: 'invincible', label: UI.status_invincible, desc: '无敌期间不会因受到伤害而失败。', color: COLORS.elixir },
        { key: 'status_immune', label: UI.status_immune || '状态免疫', desc: '效果存在时，部分负面状态不会生效。', color: '#16A085' },
        { key: 'stunned', label: UI.status_stunned, desc: '轮到自己回合时，层数减1，跳过一回合主动行动，但装备的被动效果正常。', color: COLORS.damage },
        { key: 'attack_blocked', label: UI.status_attack_blocked, desc: '不能打出攻击牌，直到层数或持续时间结束。', color: COLORS.damage },
        { key: 'attack_only', label: UI.status_attack_only, desc: '只能打出攻击牌，直到层数或持续时间结束。', color: '#D35400' },
        { key: 'untargetable', label: UI.status_untargetable, desc: '不能被部分选择目标的效果指定。', color: '#1A5276' },
        { key: 'bandage', label: UI.status_bandage, desc: '绷带提供临时保护，回合开始时会按规则结束。', color: '#1E8449' },
        { key: 'sponge', label: UI.status_sponge, desc: '海绵相关的临时状态，会影响下一次结算。', color: '#6C3483' },
        { key: 'sluggish', label: UI.status_sluggish, desc: '每回合少抽层数张牌。', color: '#E67E22' },
        { key: 'overload', label: UI.status_overload, desc: '回合开始时扣除对应层数E，到0为止，然后清除全部层数。', color: '#C0392B' },
        { key: 'foresight', label: UI.status_foresight, desc: '回合开始抽牌时，可以选择最多层数张手牌丢弃，然后抽对应张牌。', color: '#2980B9' },
        { key: 'fracture', label: UI.status_fracture, desc: '每打出一张牌减少与层数相同的H，自己回合结束清除。', color: '#7F8C8D' },
        { key: 'stagnation', label: UI.status_stagnation, desc: '回合开始时，中毒仍会造成伤害，但结算后 P 层数不会减半。自己回合结束时滞留层数-1。', color: '#9B59B6' },
        { key: 'blind', label: UI.status_blind, desc: '1层：自己手牌和反制窗口卡只显示类型；2层：战斗日志变灰，自己H/E/M显示为问号，牌连类型也隐藏，并隐藏反制伤害预测；3层及以上：其他玩家H/E/M、自己的牌堆数量和大多数可见数值显示为问号，他人手牌区不显示卡牌，只显示问号。自己回合开始时手牌会被打乱，然后清空失明。', color: '#2C3E50' },
        { key: 'heal_block', label: UI.status_heal_block, desc: '生命回复效果降低50%×层数（上限降低100%），自己回合结束时层数-1。', color: '#E84393' },
        { key: 'weakness', label: UI.status_weakness, desc: '自己对别人造成的物理伤害降低20%×层数（上限降低60%），自己回合结束时层数-1。', color: '#8E44AD' },
        { key: 'bleed', label: UI.status_bleed, desc: '打出攻击牌时受到层数点物理伤害，回合结束时层数下取整减半。', color: '#922B21' },
        { key: 'fragment', label: UI.status_fragment, desc: '获得碎片层数；达到4层时可消耗4层将雷神之锤加入手中。', color: '#795548' },
        { key: 'jungle:fragile', label: '易损', desc: '护甲降低对应层数；若护甲被降到负数，会让受到的物理伤害增加。自己回合开始时清除。', color: '#8E5A2A' },
        { key: 'jungle:shield', label: '护盾', desc: '受到伤害时先消耗护盾层数抵扣等量伤害，包括魔法伤害。自己回合开始时层数减半。', color: '#2E7D7D' },
        { key: 'jungle:turn_heal_turns', label: '回合回复', desc: '写作“回合回复:X;Y”。出现和回合开始时回复Y点H，然后X减少1；X为0时消失。', color: '#F48FB1' },
        { key: 'jungle:turn_magic_turns', label: '魔力回合回复', desc: '写作“魔力回合回复:X;Y”。出现和回合开始时回复Y点M，然后X减少1；X为0时消失。', color: COLORS.magic },
        { key: 'jungle:root_status', label: '树根', desc: '增加护甲；受到物理伤害时减少1层。产生它的树根装备离场时，会清除对应树根。', color: '#6E8B3D' },
        { key: 'jungle:toxic_poison', label: '剧毒', desc: '中毒结算后，额外施加对应层数的中毒。', color: '#5E8C31' },
    ];
    builtInList.forEach(s => result.set(s.key, { ...s, source: 'vanilla' }));
    if (CUSTOM_STATUS_DEFS && typeof CUSTOM_STATUS_DEFS === 'object') {
        Object.entries(CUSTOM_STATUS_DEFS).forEach(([id, def]) => {
            const existing = result.get(id);
            const label = getRegistryText(def, 'name', id);
            const desc = getRegistryText(def, 'description', '');
            const color = safeRegistryColor(def.color, existing ? existing.color : '#1F618D');
            result.set(id, {
                key: id,
                label,
                desc: desc || (existing ? existing.desc : ''),
                color,
                source: def.v2_mod_id || def.source_mod || 'mod',
                customDef: def,
            });
        });
    }
    return result;
}

function renderStatusGallery(list, detail, q) {
    const allStatuses = getAllStatusDefs();
    const statuses = [...allStatuses.values()].filter(s => {
        const text = `${s.key} ${s.label} ${s.desc}`.toLowerCase();
        return !q || text.includes(q);
    });
    const statusIds = statuses.map(s => `status:${s.key}`);
    if (!statusIds.includes(gallerySelectedId)) gallerySelectedId = statusIds[0] || null;
    list.innerHTML = '';
    statuses.forEach(s => {
        const id = `status:${s.key}`;
        const row = document.createElement('div');
        row.className = 'gallery-card-row' + (id === gallerySelectedId ? ' active' : '');
        const sourceTag = s.source === 'vanilla' ? '' : `<span class="gallery-row-meta" style="color:${s.color}">${s.source}</span>`;
        row.innerHTML = `<div class="gallery-row-title" style="color:${s.color}">${escapeHtml(s.label)}</div>${sourceTag}`;
        row.onclick = () => { gallerySelectedId = id; renderCardGallery(); };
        list.appendChild(row);
    });
    const selectedKey = gallerySelectedId ? String(gallerySelectedId).replace('status:', '') : null;
    const s = allStatuses.get(selectedKey);
    if (!s) {
        detail.innerHTML = `<p>${UI.gallery_no_items}</p>`;
        return;
    }
    gallerySelectedId = `status:${s.key}`;
    detail.innerHTML = `<div class="gallery-simple-detail">
        <h3 style="color:${s.color}">${escapeHtml(s.label)}</h3>
        <p><b>ID：</b>${s.key}</p>
        <p><b>来源：</b>${s.source === 'vanilla' ? '原版' : s.source}</p>
        <p>${escapeHtml(s.desc)}</p>
    </div>`;
}

function openRulesModal({ firstVisit = false } = {}) {
    const modal = $('modal');
    const content = $('modal-content');
    if (!modal || !content) return;
    const skipHtml = firstVisit ? `<button id="btn-rules-skip" class="rules-skip-btn btn btn-secondary">${UI.tutorial_skip}</button>` : '';
    content.className = 'modal-inner rules-modal';
    content.innerHTML = `
        ${skipHtml}
        <h3>${UI.rules_intro_title}</h3>
        <div class="rules-body" id="rules-body">
            ${renderRulesBodyHtml()}
        </div>
        <div class="modal-buttons">
            <button id="btn-rules-tutorial" class="btn btn-bloom">${UI.tutorial_start}</button>
            <button id="btn-rules-close" class="btn btn-primary">${firstVisit ? UI.ok : UI.close}</button>
        </div>`;
    modal.classList.remove('hidden');
    modal.classList.add('active');
    const body = $('rules-body');
    if (body && rulesScrollTop) body.scrollTop = rulesScrollTop;
    bindRulesCardLinks(content);
    const close = $('btn-rules-close');
    if (close) close.onclick = () => {
        localStorage.setItem('gtn_seen_intro', '1');
        content.className = 'modal-inner';
        hideModal();
    };
    const tutorialBtn = $('btn-rules-tutorial');
    if (tutorialBtn) tutorialBtn.onclick = () => startTutorial(firstVisit ? 'home' : 'about');
    const skip = $('btn-rules-skip');
    if (skip) skip.onclick = () => {
        gameAlert(UI.rules_skip_confirm_title, UI.rules_skip_confirm_msg, [
            { text: UI.cancel || '取消', cls: 'btn-secondary', action: () => {} },
            { text: UI.tutorial_skip, cls: 'btn-danger', action: () => {
                localStorage.setItem('gtn_seen_intro', '1');
                content.className = 'modal-inner';
                hideModal();
            } }
        ]);
    };
}

function updateStatus(text) {
    const s = $('status-text');
    if (s) {
        s.textContent = text;
        s.style.color = '';
        s.style.fontWeight = '';
    }
}

let _statusTimeout = null;
let _prevStatusText = '';
function getVisibleViewId() {
    const visible = document.querySelector('.view:not(.hidden)');
    return visible ? visible.id : 'view-login';
}

function getViewStatusText(viewId = getVisibleViewId()) {
    if (viewId === 'view-login') return UI.default_status;
    if (viewId === 'view-lobby') return UI.lobby_status.replace('{0}', nickname || '');
    if (viewId === 'view-solo') return UI.solo_training;
    if (viewId === 'view-draft') return UI.draft_phase;
    if (viewId === 'view-event-select') return UI.select_event;
    if (viewId === 'view-card-gallery') return UI.gallery_title;
    if (viewId === 'view-mod-editor') return UI.mod_editor;
    return UI.default_status;
}

function refreshBaseStatus(viewId = getVisibleViewId()) {
    if (viewId === 'view-game' && gameState) {
        renderGame(gameState);
        return;
    }
    updateStatus(getViewStatusText(viewId));
}

function flashStatus(text, duration, type) {
    const s = $('status-text');
    showActionToast(text, duration, type);
    if (!s) return;
    if (_statusTimeout) { clearTimeout(_statusTimeout); _statusTimeout = null; }
    else { _prevStatusText = getViewStatusText(); }
    s.textContent = text;
    if (type === 'error') {
        s.style.color = '#C0392B';
        restartTransientClass(s, 'status-shake', 320);
    } else {
        s.style.color = '#E67E22';
    }
    s.style.fontWeight = '700';
    _statusTimeout = setTimeout(() => {
        s.style.color = '';
        s.style.fontWeight = '';
        s.textContent = _prevStatusText || getViewStatusText();
        _prevStatusText = '';
        _statusTimeout = null;
    }, duration || 2000);
}

function showActionToast(text, duration, type) {
    if (!text) return;
    let toast = $('action-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'action-toast';
        toast.className = 'action-toast hidden';
        document.body.appendChild(toast);
    }
    if (actionToastTimer) {
        clearTimeout(actionToastTimer);
        actionToastTimer = null;
    }
    toast.textContent = text;
    toast.className = `action-toast ${type === 'error' ? 'toast-error' : 'toast-info'}`;
    requestAnimationFrame(() => toast.classList.add('active'));
    actionToastTimer = setTimeout(() => {
        toast.classList.remove('active');
        actionToastTimer = setTimeout(() => {
            toast.classList.add('hidden');
            actionToastTimer = null;
        }, 180);
    }, Math.max(900, duration || 1800));
}

function clearActionToast() {
    const toast = $('action-toast');
    if (actionToastTimer) {
        clearTimeout(actionToastTimer);
        actionToastTimer = null;
    }
    if (toast) {
        toast.className = 'action-toast hidden';
        toast.textContent = '';
    }
}

async function copyPlainText(text) {
    const value = String(text || '').trim();
    if (!value) return false;
    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(value);
            return true;
        }
    } catch (err) {
        console.warn('clipboard write failed', err);
    }
    try {
        const input = document.createElement('textarea');
        input.value = value;
        input.setAttribute('readonly', 'readonly');
        input.style.position = 'fixed';
        input.style.left = '-9999px';
        input.style.top = '0';
        document.body.appendChild(input);
        input.select();
        const ok = document.execCommand('copy');
        document.body.removeChild(input);
        return ok;
    } catch (err) {
        console.warn('fallback copy failed', err);
        return false;
    }
}

function isTouchPlayMode() {
    return !!(window.matchMedia && window.matchMedia('(hover: none), (pointer: coarse)').matches);
}

function ensureDropOverlay() {
    let overlay = $('card-drop-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'card-drop-overlay';
        overlay.className = 'card-drop-overlay hidden';
        overlay.innerHTML = `<div class="card-drop-overlay-text">${UI.drag_to_play_full || UI.drag_to_play || 'Drag here to play'}</div>`;
        document.body.appendChild(overlay);
    }
    return overlay;
}

function isWaitingForOpponentCounter() {
    return !!(pendingPlayCard && gameState && gameState.mode !== '2v2' && gameState.phase !== 'game_over');
}

function isActionBusy(options = {}) {
    const includeAnimation = options.includeAnimation !== false;
    const includePendingPlay = options.includePendingPlay !== false;
    return !!pendingServerAction
        || !!choicePending
        || !!responsePending
        || (includePendingPlay && !!pendingPlayCard)
        || (includeAnimation && isCardAnimationLocked());
}

let lastClientActionRejectToastAt = 0;
function clientRejectAction(message) {
    const now = Date.now();
    if (now - lastClientActionRejectToastAt >= 800) {
        flashStatus(message || UI.operation_failed || '操作失败', 1800, 'error');
        lastClientActionRejectToastAt = now;
    }
}

function hasBlockingPendingState(eventName = '') {
    if (!gameState) return true;
    if (gameState.pending_response || responsePending || pendingPlayCard) return eventName !== 'response';
    if (gameState.pending_choice || choicePending) return eventName !== 'resolve_choice';
    if (gameState.pending_v2_ui) return eventName !== 'v2_ui_response';
    return false;
}

function canSendGameAction(eventName, options = {}) {
    if (!isLocalSoloRuntimeActive() && (!socket || !socket.connected)) {
        clientRejectAction(UI.server_not_connected || UI.server_no_response);
        return false;
    }
    const animationBusy = options.includeAnimation !== false && isCardAnimationLocked();
    const blockedByServerAction = !!pendingServerAction;
    const blockedByChoice = !!choicePending && eventName !== 'resolve_choice';
    const blockedByResponse = (!!responsePending || !!pendingPlayCard) && eventName !== 'response';
    if (blockedByServerAction || blockedByChoice || blockedByResponse || animationBusy) {
        clientRejectAction(UI.waiting_response || UI.operation_failed);
        return false;
    }
    if (hasBlockingPendingState(eventName)) {
        clientRejectAction(UI.waiting_response || UI.operation_failed);
        return false;
    }
    return true;
}

function clearPendingServerAction(options = {}) {
    if (pendingServerActionTimer) {
        clearTimeout(pendingServerActionTimer);
        pendingServerActionTimer = null;
    }
    pendingServerAction = null;
    if (!options.keepOptimistic) {
        optimisticResourceOverride = null;
        pendingOptimisticResourceCosts = [];
    }
    document.body.classList.remove('server-action-pending');
}

function beginPendingServerAction(name, options = {}) {
    clearPendingServerAction();
    pendingServerAction = {
        name: name || 'action',
        createdAt: Date.now(),
    };
    if (options.optimisticResources) {
        optimisticResourceOverride = options.optimisticResources;
        applyOptimisticResourceOverride();
    }
    document.body.classList.add('server-action-pending');
    ['btn-end-turn', 'btn-urf-replace', 'btn-urf-sell'].forEach(id => {
        const btn = $(id);
        if (btn) btn.disabled = true;
    });
    document.querySelectorAll('.btn-equip-trigger').forEach(btn => { btn.disabled = true; });
    const timeoutMs = Math.max(2500, Number(options.timeoutMs) || SERVER_ACTION_TIMEOUT_MS);
    pendingServerActionTimer = setTimeout(() => {
        const stillPending = !!pendingServerAction;
        clearPendingServerAction();
        pendingPlayCard = null;
        clearSelectedPlayCard();
        if (gameState && gameState.phase) renderGame(gameState);
        if (stillPending) flashStatus(UI.server_no_response || UI.operation_failed, 3200, 'error');
    }, timeoutMs);
}

function getOptimisticResourceCost(cardDict, ownerState = null) {
    if (!cardDict) return null;
    const cardDef = getCardDef(cardDict.def_id);
    if (!cardDef) return null;
    const owner = ownerState || (gameState && gameState.you) || {};
    const { totalE, totalM } = getCardDisplayCosts(cardDict, cardDef, owner);
    return {
        totalE: Math.max(0, Number(totalE) || 0),
        totalM: Math.max(0, Number(totalM) || 0),
    };
}

function buildOptimisticResourceOverride(cardDict, ownerState = null, cost = null) {
    const owner = ownerState || (gameState && gameState.you) || {};
    const resourceCost = cost || getOptimisticResourceCost(cardDict, owner);
    if (!resourceCost || (!resourceCost.totalE && !resourceCost.totalM)) return null;
    return {
        playerId: normalizePlayerId(gameState && gameState.your_id),
        elixir: Math.max(0, getBarValueForKey(owner, 'elixir') - resourceCost.totalE),
        magic: Math.max(0, getBarValueForKey(owner, 'magic') - resourceCost.totalM),
        maxElixir: getBarMaxForKey(owner, 'elixir'),
        maxMagic: getBarMaxForKey(owner, 'magic'),
        totalE: resourceCost.totalE,
        totalM: resourceCost.totalM,
    };
}

function applyOptimisticResourceOverride() {
    if (!optimisticResourceOverride) return;
    const events = [];
    if (optimisticResourceOverride.totalE > 0) {
        events.push({
            text: `-${optimisticResourceOverride.totalE}E`,
            kind: 'elixir',
            delay: 0,
            stackIndex: 0,
            barKey: 'elixir',
            barValue: optimisticResourceOverride.elixir,
            barMax: optimisticResourceOverride.maxElixir,
        });
    }
    if (optimisticResourceOverride.totalM > 0) {
        events.push({
            text: `-${optimisticResourceOverride.totalM}M`,
            kind: 'magic',
            delay: optimisticResourceOverride.totalE > 0 ? 120 : 0,
            stackIndex: 1,
            barKey: 'magic',
            barValue: optimisticResourceOverride.magic,
            barMax: optimisticResourceOverride.maxMagic,
        });
    }
    const scheduled = showCombatFloatSequence('.player-section', events);
    animateBarEventSequence('.player-section', scheduled, gameState && gameState.you, {
        ...(gameState && gameState.you),
        elixir: optimisticResourceOverride.elixir,
        magic: optimisticResourceOverride.magic,
    });
}

function getOptimisticPlayerBarsData(playerData) {
    if (!optimisticResourceOverride || !playerData) return playerData;
    return {
        ...playerData,
        elixir: optimisticResourceOverride.elixir,
        magic: optimisticResourceOverride.magic,
    };
}

function updateDropOverlayContent(overlay = $('card-drop-overlay')) {
    if (!overlay) return;
    const waiting = isWaitingForOpponentCounter();
    overlay.classList.toggle('waiting-response', waiting);
    const text = overlay.querySelector('.card-drop-overlay-text');
    if (text) {
        text.textContent = waiting
            ? (UI.waiting_opponent_counter || UI.waiting_response || 'Waiting for response')
            : (UI.drag_to_play_full || UI.drag_to_play || 'Drag here to play');
    }
}

function showDropOverlay() {
    const overlay = ensureDropOverlay();
    updateDropOverlayContent(overlay);
    const bounds = getDropAreaBounds();
    overlay.style.setProperty('--drop-top', `${Math.max(0, bounds.top)}px`);
    overlay.style.setProperty('--drop-bottom', `${Math.max(0, window.innerHeight - bounds.bottom)}px`);
    overlay.classList.remove('hidden');
}

function hideDropOverlay() {
    const overlay = $('card-drop-overlay');
    if (overlay) overlay.classList.add('hidden');
}

function pointInDropArea(pos) {
    const bounds = getDropAreaBounds();
    return pos.y >= bounds.top && pos.y <= bounds.bottom && pos.x >= bounds.left && pos.x <= bounds.right;
}

function getDropAreaBounds() {
    const gameView = $('view-game');
    const playerSection = document.querySelector('.player-section');
    const controls = document.querySelector('.controls-bar');
    const top = gameView ? gameView.getBoundingClientRect().top : 0;
    const bottom = playerSection ? playerSection.getBoundingClientRect().top : window.innerHeight;
    const controlsTop = controls ? controls.getBoundingClientRect().top : window.innerHeight;
    const effectiveBottom = Math.min(bottom, controlsTop);
    return { top, bottom: effectiveBottom, left: 0, right: window.innerWidth };
}

function ensureMobilePlayConfirm() {
    let bar = $('mobile-play-confirm');
    if (!bar) {
        bar = document.createElement('div');
        bar.id = 'mobile-play-confirm';
        bar.className = 'mobile-play-confirm hidden';
        bar.innerHTML = `
            <div class="mobile-play-info"></div>
            <div class="mobile-play-actions">
                <button type="button" class="btn btn-secondary" id="mobile-play-cancel"></button>
                <button type="button" class="btn btn-primary" id="mobile-play-ok"></button>
            </div>
        `;
        document.body.appendChild(bar);
    }
    return bar;
}

function clearSelectedPlayCard(options = {}) {
    selectedPlayCardId = null;
    classicAimHoverTarget = '';
    if (classicAimFrame) {
        cancelAnimationFrame(classicAimFrame);
        classicAimFrame = 0;
    }
    if (classicHoverPreviewTimer) {
        clearTimeout(classicHoverPreviewTimer);
        classicHoverPreviewTimer = null;
    }
    removeClassicHoverInfo();
    document.querySelectorAll('.card.tap-selected').forEach(el => el.classList.remove('tap-selected'));
    document.querySelectorAll('.classic-fighter.is-aim-hover').forEach(el => el.classList.remove('is-aim-hover'));
    const aim = $('classic-aim-layer');
    if (aim) aim.classList.add('hidden');
    const root = $('battle-classic');
    if (root) {
        root.classList.remove('is-aiming', 'is-target-aim', 'is-self-only-aim');
    }
    const bar = $('mobile-play-confirm');
    if (bar) bar.classList.add('hidden');
    updateMinimalPlayCancelZone();
    if (!options.skipRender && shouldUseClassicBattle(gameState)) renderClassicBattle(gameState);
}

function isMinimalTargetSelectionActive() {
    if (!gameState || shouldUseClassicBattle(gameState)) return false;
    if (selectedPlayCardId == null) return false;
    if (isActionBusy({ includeAnimation: false })) return false;
    const hand = (gameState.you || {}).hand || [];
    const cardDict = hand.find(c => c.instance_id === selectedPlayCardId);
    const cardDef = cardDict ? getCardDef(cardDict.def_id) : null;
    if (!cardDict || !cardDef || !canPlayCard(cardDict)) return false;
    return !cardHasSelfOnlyFlag(cardDict, cardDef);
}

function updateMinimalPlayCancelZone() {
    const zone = $('minimal-play-cancel-zone');
    if (!zone) return;
    const label = zone.querySelector('span');
    const text = UI.cancel_play || UI.cancel || '取消打出';
    if (label) label.textContent = text;
    zone.setAttribute('aria-label', text);
    zone.classList.toggle('hidden', !isMinimalTargetSelectionActive());
}

function bindMinimalPlayCancelZone() {
    const zone = $('minimal-play-cancel-zone');
    if (!zone || zone.dataset.bound === '1') return;
    zone.dataset.bound = '1';
    zone.addEventListener('click', (event) => {
        if (!isMinimalTargetSelectionActive()) return;
        event.preventDefault();
        event.stopPropagation();
        clearSelectedPlayCard();
    });
}

function getSelectedClassicCard() {
    const hand = (gameState && gameState.you && gameState.you.hand) || [];
    const cardDict = hand.find(c => c.instance_id === selectedPlayCardId);
    if (!cardDict) return null;
    return normalizeBattleCard(cardDict, gameState.you || {});
}

function isClassicSelfOnlyCard(card) {
    if (!card) return false;
    return cardHasSelfOnlyFlag(card.raw || card, card.cardDef || getCardDef(card.def_id || ''));
}

function ensureClassicAimLayer() {
    const root = $('battle-classic');
    if (!root) return null;
    let svg = $('classic-aim-layer');
    if (!svg) {
        svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.id = 'classic-aim-layer';
        svg.classList.add('classic-aim-layer', 'hidden');
        svg.setAttribute('aria-hidden', 'true');
        svg.setAttribute('focusable', 'false');
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
        marker.setAttribute('id', 'classic-aim-arrowhead');
        marker.setAttribute('markerWidth', '10');
        marker.setAttribute('markerHeight', '10');
        marker.setAttribute('refX', '8');
        marker.setAttribute('refY', '5');
        marker.setAttribute('orient', 'auto');
        marker.setAttribute('markerUnits', 'strokeWidth');
        const head = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        head.setAttribute('d', 'M1,1 L9,5 L1,9 Z');
        marker.appendChild(head);
        defs.appendChild(marker);
        const outline = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        outline.classList.add('classic-aim-outline');
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.classList.add('classic-aim-path');
        path.setAttribute('marker-end', 'url(#classic-aim-arrowhead)');
        const tip = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        tip.classList.add('classic-aim-tip');
        tip.setAttribute('r', '5');
        svg.appendChild(defs);
        svg.appendChild(outline);
        svg.appendChild(path);
        svg.appendChild(tip);
        root.appendChild(svg);
    }
    return svg;
}

function classicAimPathData(x1, y1, x2, y2) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    const dist = Math.hypot(dx, dy);
    if (dist < 6) return `M ${x1.toFixed(1)} ${y1.toFixed(1)} L ${x2.toFixed(1)} ${y2.toFixed(1)}`;
    const points = [];
    const bend = Math.max(-90, Math.min(90, dx * 0.12));
    for (let i = 0; i <= 30; i++) {
        const t = i / 30;
        const logT = Math.log1p(t * 11) / Math.log(12);
        const bow = Math.sin(Math.PI * t) * bend;
        const x = x1 + dx * t + bow * 0.18;
        const y = y1 + dy * logT - Math.sin(Math.PI * t) * Math.min(42, dist * 0.16);
        points.push(`${i ? 'L' : 'M'} ${x.toFixed(1)} ${y.toFixed(1)}`);
    }
    return points.join(' ');
}

function selectedClassicCardCenter() {
    if (selectedPlayCardId == null) return null;
    const wrapper = document.querySelector(`.classic-hand-card[data-instance-id="${selectedPlayCardId}"]`);
    const cardEl = wrapper ? (wrapper.querySelector('.classic-fan-card-inner') || wrapper) : null;
    if (!cardEl) return null;
    const rect = cardEl.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return null;
    return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
}

function updateClassicAimHoverTarget() {
    let hoverId = '';
    const selected = getSelectedClassicCard();
    if (isClassicSelfOnlyCard(selected)) {
        document.querySelectorAll('.classic-fighter.is-aim-hover').forEach(item => item.classList.remove('is-aim-hover'));
        classicAimHoverTarget = '';
        return;
    }
    const el = document.elementFromPoint(classicAimPointer.x, classicAimPointer.y);
    const fighter = el && el.closest ? el.closest('#classic-fighter-self, #classic-fighter-enemy') : null;
    if (fighter && classicCanPlayFromElement(fighter.id)) hoverId = fighter.id;
    if (hoverId === classicAimHoverTarget) return;
    classicAimHoverTarget = hoverId;
    document.querySelectorAll('.classic-fighter.is-aim-hover').forEach(item => item.classList.remove('is-aim-hover'));
    if (hoverId) {
        const target = $(hoverId);
        if (target) target.classList.add('is-aim-hover');
    }
}

function updateClassicAimCurve() {
    const root = $('battle-classic');
    const selected = getSelectedClassicCard();
    const selfOnly = isClassicSelfOnlyCard(selected);
    const svg = ensureClassicAimLayer();
    if (!root || !svg || !selected || selfOnly || !shouldUseClassicBattle(gameState)) {
        if (svg) svg.classList.add('hidden');
        return;
    }
    const center = selectedClassicCardCenter();
    if (!center) {
        svg.classList.add('hidden');
        return;
    }
    svg.setAttribute('viewBox', `0 0 ${window.innerWidth} ${window.innerHeight}`);
    svg.setAttribute('width', String(window.innerWidth));
    svg.setAttribute('height', String(window.innerHeight));
    const d = classicAimPathData(center.x, center.y, classicAimPointer.x, classicAimPointer.y);
    const outline = svg.querySelector('.classic-aim-outline');
    const path = svg.querySelector('.classic-aim-path');
    const tip = svg.querySelector('.classic-aim-tip');
    if (outline) outline.setAttribute('d', d);
    if (path) path.setAttribute('d', d);
    if (tip) {
        tip.setAttribute('cx', classicAimPointer.x.toFixed(1));
        tip.setAttribute('cy', classicAimPointer.y.toFixed(1));
    }
    svg.classList.remove('hidden');
    updateClassicAimHoverTarget();
}

function scheduleClassicAimCurveUpdate() {
    if (!shouldUseClassicBattle(gameState)) return;
    if (classicAimFrame) return;
    classicAimFrame = requestAnimationFrame(() => {
        classicAimFrame = 0;
        updateClassicAimCurve();
    });
}

function onClassicAimPointerMove(event) {
    classicAimPointer = { x: event.clientX, y: event.clientY };
    if (selectedPlayCardId != null && shouldUseClassicBattle(gameState)) scheduleClassicAimCurveUpdate();
}

function cancelClassicSelection(event) {
    if (!shouldUseClassicBattle(gameState) || selectedPlayCardId == null) return false;
    if (event) event.preventDefault();
    clearSelectedPlayCard();
    return true;
}

function selectPlayCardForConfirm(cardInstanceId) {
    if (!isTouchPlayMode()) return false;
    if (isActionBusy()) return false;
    const hand = (gameState.you || {}).hand || [];
    const cardDict = hand.find(c => c.instance_id === cardInstanceId);
    const cardDef = cardDict ? getCardDef(cardDict.def_id) : null;
    if (!cardDict || !cardDef || !canPlayCard(cardDict)) return false;
    selectedPlayCardId = cardInstanceId;
    document.querySelectorAll('.card.tap-selected').forEach(el => el.classList.remove('tap-selected'));
    const cardEl = document.querySelector(`.card[data-instance-id="${cardInstanceId}"]`);
    if (cardEl) cardEl.classList.add('tap-selected');
    const bar = ensureMobilePlayConfirm();
    const info = bar.querySelector('.mobile-play-info');
    const ok = bar.querySelector('#mobile-play-ok');
    const cancel = bar.querySelector('#mobile-play-cancel');
    const name = getBlindedCardDisplayName(cardDict, cardDef);
    if (info) info.textContent = `${UI.tap_play_hint || 'Tap a card, then confirm to play'}：${name}`;
    if (ok) {
        ok.textContent = (UI.confirm_play || 'Play {0}').replace('{0}', name);
        ok.onclick = () => {
            const id = selectedPlayCardId;
            clearSelectedPlayCard();
            if (id != null) onPlayCard(id, { confirmed: true });
        };
    }
    if (cancel) {
        cancel.textContent = UI.cancel_play || UI.cancel || 'Cancel';
        cancel.onclick = clearSelectedPlayCard;
    }
    bar.classList.remove('hidden');
    updateMinimalPlayCancelZone();
    if (shouldUseClassicBattle(gameState)) renderClassicBattle(gameState);
    return true;
}

function selectClassicPlayCard(cardInstanceId, event = null) {
    if (!shouldUseClassicBattle(gameState) || isActionBusy()) return false;
    const hand = (gameState.you || {}).hand || [];
    const cardDict = hand.find(c => c.instance_id === cardInstanceId);
    const cardDef = cardDict ? getCardDef(cardDict.def_id) : null;
    const canSelect = !!(cardDict && cardDef && canPlayCard(cardDict));
    if (!canSelect) {
        if (cardDict) flashStatus(getCannotPlayReason(cardDict), 2200, 'error');
        return false;
    }
    if (event && typeof event.clientX === 'number') classicAimPointer = { x: event.clientX, y: event.clientY };
    removeClassicHoverInfo();
    selectedPlayCardId = cardInstanceId;
    document.querySelectorAll('.card.tap-selected').forEach(el => el.classList.remove('tap-selected'));
    const cardEl = document.querySelector(`.card[data-instance-id="${cardInstanceId}"]`);
    if (cardEl) cardEl.classList.add('tap-selected');
    renderClassicBattle(gameState);
    scheduleClassicAimCurveUpdate();
    return true;
}

async function classicPlaySelectedCard() {
    if (!shouldUseClassicBattle(gameState) || isActionBusy()) return false;
    const id = selectedPlayCardId;
    if (id == null) return false;
    await onPlayCard(id, { confirmed: true });
    return true;
}

function classicCanPlayFromElement(elementId) {
    const hand = (gameState && gameState.you && gameState.you.hand) || [];
    const cardDict = hand.find(c => c.instance_id === selectedPlayCardId);
    const cardDef = cardDict ? getCardDef(cardDict.def_id) : null;
    const card = cardDef ? normalizeBattleCard(cardDict, gameState.you || {}) : null;
    const selfOnly = isClassicSelfOnlyCard(card);
    const role = getClassicPlayRole(card);
    if (elementId === 'classic-play-lane') return selfOnly || role === 'stage';
    if (elementId === 'classic-fighter-enemy') return role === 'enemy';
    if (elementId === 'classic-fighter-self') return !selfOnly && (role === 'self' || role === 'equip');
    return false;
}

function classicCanAutoPlaySelfOnlyFromEvent(event) {
    if (!shouldUseClassicBattle(gameState) || selectedPlayCardId == null || isActionBusy()) return false;
    const selected = getSelectedClassicCard();
    if (!isClassicSelfOnlyCard(selected)) return false;
    const target = event && event.target;
    if (target && target.closest && target.closest('.classic-hand-card, .classic-command-panel, .classic-end-turn, .classic-icon-btn, .classic-log-drawer, .classic-left-rail, .classic-top-hud, .classic-fighter')) {
        return false;
    }
    const hand = $('classic-hand-fan');
    const handRect = hand ? hand.getBoundingClientRect() : null;
    return !handRect || event.clientY < handRect.top;
}

function getClassicPlayedCardAnimationTarget(cardDict, cardDef, targetPlayerId = -1) {
    if (!shouldUseClassicBattle(gameState) || !cardDict || !cardDef) return null;
    const card = normalizeBattleCard(cardDict, (gameState && gameState.you) || {});
    if (isClassicSelfOnlyCard(card)) return null;
    if (targetPlayerId >= 0) {
        const selfId = normalizePlayerId(gameState && gameState.your_id);
        return targetPlayerId === selfId
            ? document.querySelector('#classic-fighter-self .player-avatar') || $('classic-fighter-self')
            : document.querySelector('#classic-fighter-enemy .player-avatar') || $('classic-fighter-enemy');
    }
    const role = getClassicPlayRole(card);
    if (role === 'enemy') return document.querySelector('#classic-fighter-enemy .player-avatar') || $('classic-fighter-enemy');
    if (role === 'self' || role === 'equip') return document.querySelector('#classic-fighter-self .player-avatar') || $('classic-fighter-self');
    return $('classic-play-lane');
}

function showModal(html) {
    removeFloatingCardPreview();
    const content = $('modal-content');
    const modal = $('modal');
    if (content) content.className = 'modal-inner';
    if (content) content.innerHTML = html;
    if (modal) { modal.classList.remove('hidden'); modal.classList.add('active'); }
}

function hideModal() {
    removeFloatingCardPreview();
    activeV2UiRequestId = null;
    const modal = $('modal');
    const content = $('modal-content');
    if (content) content.className = 'modal-inner';
    if (modal) { modal.classList.add('hidden'); modal.classList.remove('active'); }
    if (tutorialMode) {
        showTutorialOverlay();
        setTimeout(updateTutorialOverlay, 60);
    }
}

function getV2Text(obj, base, fallback = '') {
    if (!obj || typeof obj !== 'object') return fallback;
    const langKey = currentLang === 'zh' ? `${base}_cn` : `${base}_${currentLang}`;
    return obj[langKey] || obj[`${base}_en`] || obj[`${base}_cn`] || obj[base] || fallback;
}

function makeV2UiLabel(text) {
    const label = document.createElement('label');
    label.className = 'v2-ui-label';
    label.textContent = text;
    return label;
}

function showV2UiRequest(data = {}) {
    if (isSpectating) return;
    removeFloatingCardPreview();
    const modal = $('modal');
    const content = $('modal-content');
    if (!modal || !content) return;
    const requestId = String(data.request_id || '');
    if (requestId && activeV2UiRequestId === requestId && modal.classList.contains('active') && content.classList.contains('v2-ui-modal')) {
        return;
    }
    activeV2UiRequestId = requestId;
    const component = data.component || {};
    const controlState = {};
    content.className = `modal-inner v2-ui-modal v2-ui-accent-${escapeClassToken((component.style && component.style.accent) || 'default')}`;
    content.innerHTML = '';

    const title = document.createElement('h3');
    title.textContent = getV2Text(component, 'title', UI.notice || 'Notice');
    content.appendChild(title);

    if (data.card) {
        const cardLine = document.createElement('div');
        cardLine.className = 'v2-ui-card-line';
        cardLine.appendChild(createCardChoiceChip(data.card));
        content.appendChild(cardLine);
    }

    const bodyText = getV2Text(component, 'text', '');
    if (bodyText) {
        const p = document.createElement('p');
        p.className = 'v2-ui-text';
        p.textContent = bodyText;
        content.appendChild(p);
    }

    const controls = Array.isArray(component.controls) ? component.controls : [];
    controls.forEach(control => {
        const row = document.createElement('div');
        row.className = `v2-ui-control v2-ui-control-${escapeClassToken(control.type || 'text')}`;
        const labelText = getV2Text(control, 'label', control.id || '');
        const type = control.type || 'text';
        if (type === 'text') {
            const p = document.createElement('p');
            p.className = 'v2-ui-text';
            p.textContent = getV2Text(control, 'text', labelText);
            row.appendChild(p);
        } else if (type === 'slider') {
            row.appendChild(makeV2UiLabel(labelText));
            const wrap = document.createElement('div');
            wrap.className = 'v2-ui-slider-row';
            const input = document.createElement('input');
            input.type = 'range';
            input.min = Number(control.min ?? 0);
            input.max = Number(control.max ?? input.min);
            input.step = Number(control.step ?? 1);
            input.value = Number(control.default ?? input.min);
            const value = document.createElement('span');
            value.className = 'v2-ui-value';
            const sync = () => { value.textContent = input.value; controlState[control.id] = Number(input.value); };
            input.addEventListener('input', sync);
            sync();
            wrap.appendChild(input);
            wrap.appendChild(value);
            row.appendChild(wrap);
        } else if (type === 'number' || type === 'number_input') {
            row.appendChild(makeV2UiLabel(labelText));
            const input = document.createElement('input');
            input.type = 'number';
            input.min = Number(control.min ?? 0);
            input.max = Number(control.max ?? input.min);
            input.step = Number(control.step ?? 1);
            input.value = Number(control.default ?? input.min);
            input.className = 'v2-ui-number';
            const sync = () => { controlState[control.id] = Number(input.value); };
            input.addEventListener('input', sync);
            sync();
            row.appendChild(input);
        } else if (type === 'select') {
            row.appendChild(makeV2UiLabel(labelText));
            const select = document.createElement('select');
            select.className = 'v2-ui-select';
            (control.options || []).forEach(option => {
                const opt = document.createElement('option');
                opt.value = String(option.value);
                opt.textContent = getV2Text(option, 'label', String(option.label || option.value));
                select.appendChild(opt);
            });
            const sync = () => { controlState[control.id] = select.value; };
            select.addEventListener('change', sync);
            sync();
            row.appendChild(select);
        } else if (type === 'card_picker' || type === 'equipment_picker' || type === 'player_picker' || type === 'target_picker') {
            row.appendChild(makeV2UiLabel(labelText));
            const list = document.createElement('div');
            list.className = 'v2-ui-picker-list';
            (control.options || []).forEach(option => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'v2-ui-picker-option';
                btn.dataset.value = String(option.value);
                if (option.card) {
                    btn.appendChild(createCardChoiceChip(option.card));
                } else {
                    btn.textContent = getV2Text(option, 'label', String(option.label || option.value));
                }
                btn.addEventListener('click', () => {
                    list.querySelectorAll('.selected').forEach(el => el.classList.remove('selected'));
                    btn.classList.add('selected');
                    controlState[control.id] = option.value;
                });
                list.appendChild(btn);
            });
            const first = list.querySelector('.v2-ui-picker-option');
            if (first) {
                first.classList.add('selected');
                controlState[control.id] = first.dataset.value;
            }
            row.appendChild(list);
        }
        content.appendChild(row);
    });

    const buttons = Array.isArray(component.buttons) && component.buttons.length
        ? component.buttons
        : [{ id: 'confirm', text_cn: '确认', text_en: 'Confirm' }, { id: 'cancel', text_cn: '取消', text_en: 'Cancel', role: 'cancel' }];
    const buttonRow = document.createElement('div');
    buttonRow.className = 'modal-buttons v2-ui-buttons';
    buttons.forEach(button => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `btn ${button.role === 'cancel' || button.id === 'cancel' ? 'secondary' : 'primary'}`;
        btn.textContent = getV2Text(button, 'text', button.id || 'OK');
        btn.addEventListener('click', () => {
            if (!canSendGameAction('v2_ui_response', { includeAnimation: false })) return;
            hideModal();
            beginPendingServerAction('v2_ui_response', { timeoutMs: SERVER_ACTION_TIMEOUT_MS });
            emitModeEvent('solo_v2_ui_response', 'v2_ui_response', {
                request_id: data.request_id,
                button: button.id,
                values: { ...controlState },
            });
        });
        buttonRow.appendChild(btn);
    });
    content.appendChild(buttonRow);
    modal.classList.remove('hidden');
    modal.classList.add('active');
}

function escapeClassToken(value) {
    return String(value || 'default').replace(/[^a-zA-Z0-9_-]/g, '');
}

const DATA_CACHE_VERSION = 'v8';
const loadedCommunityFontSubsets = new Set();
const communityFontFaceUrls = new Set();

function injectCommunityFontFallback() {
    let style = document.getElementById('community-font-fallback-style');
    if (!style) {
        style = document.createElement('style');
        style.id = 'community-font-fallback-style';
        document.head.appendChild(style);
    }
    style.textContent = `
html.fonts-loaded-main {
  --font-main: 'Kreadon', 'Kreadon Community', 'Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', system-ui, sans-serif;
}
:root {
  --font-card: 'Kreadon Demi', 'Kreadon', 'Kreadon Community', 'Microsoft YaHei', sans-serif;
}`;
}

function installCommunityFontFace(url) {
    const safeUrl = String(url || '').trim();
    if (!safeUrl || communityFontFaceUrls.has(safeUrl)) return;
    communityFontFaceUrls.add(safeUrl);
    let style = document.getElementById('community-font-face-style');
    if (!style) {
        style = document.createElement('style');
        style.id = 'community-font-face-style';
        document.head.appendChild(style);
    }
    const rules = Array.from(communityFontFaceUrls).map(fontUrl => `
@font-face {
  font-family: 'Kreadon Community';
  src: url('${fontUrl.replace(/'/g, '%27')}') format('woff2');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}`).join('\n');
    style.textContent = rules;
    injectCommunityFontFallback();
}

async function loadCommunityFontSubsetForCurrentSelection() {
    const community = getCommunityModSelection();
    if (community.mod_source !== 'community' || !community.community_mods.length) return;
    const key = community.community_mod_hash || JSON.stringify(community.community_mods);
    if (loadedCommunityFontSubsets.has(key)) return;
    loadedCommunityFontSubsets.add(key);
    try {
        const resp = await fetch('/api/font-subsets/community', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mod_source: 'community',
                community_mods: community.community_mods,
            }),
        });
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok || !data.success) throw new Error(data.error || 'community font subset failed');
        const subset = data.font_subset || {};
        if (subset.url) installCommunityFontFace(subset.url);
    } catch (e) {
        console.warn('Failed to load community font subset:', e);
    }
}

function getDataCacheKey(kind) {
    const disabled = getDisabledMods().slice().sort().join(',') || 'none';
    const community = getCommunityModSelection();
    const communityKey = community.mod_source === 'community' ? community.community_mod_hash : 'official';
    return `gtn_${kind}_cache_${DATA_CACHE_VERSION}_${disabled}_${communityKey}`;
}

function readDataCache(kind) {
    try {
        const raw = localStorage.getItem(getDataCacheKey(kind));
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        return parsed && parsed.data ? parsed.data : null;
    } catch (_) {
        return null;
    }
}

function writeDataCache(kind, data) {
    try {
        localStorage.setItem(getDataCacheKey(kind), JSON.stringify({
            ts: Date.now(),
            data,
        }));
    } catch (_) {
        // Cache is only a startup optimization; quota failures are non-fatal.
    }
}

function refreshCardDataViews() {
    if (phase === 'solo_edit') {
        renderSoloEventSelects();
        renderSoloBuilder();
    }
    const gallery = $('view-card-gallery');
    if (gallery && !gallery.classList.contains('hidden')) renderCardGallery();
}

async function fetchCardDefs(options = {}) {
    const useCache = options.useCache !== false;
    const background = !!options.background;
    const cached = useCache ? readDataCache('cards') : null;
    if (cached) {
        CARD_DEFS = cached;
        if (background) {
            refreshCardDefsFromServer({ silent: true });
            return;
        }
    }
    await refreshCardDefsFromServer({ silent: !!cached });
}

async function refreshCardDefsFromServer({ silent = false } = {}) {
    try {
        if (!silent) bootLoader.step(UI.init_cards_mods, 60);
        const resp = await fetch(`/api/cards?${buildModQueryString()}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const nextDefs = await resp.json();
        CARD_DEFS = nextDefs || {};
        writeDataCache('cards', CARD_DEFS);
        await loadCommunityFontSubsetForCurrentSelection();
        refreshCardDataViews();
    } catch (e) {
        console.error('Failed to fetch card defs:', e);
        if (!CARD_DEFS || Object.keys(CARD_DEFS).length === 0) {
            CARD_DEFS = readDataCache('cards') || {};
        }
    }
}

async function fetchOpeningEvents(options = {}) {
    const useCache = options.useCache !== false;
    const background = !!options.background;
    const cached = useCache ? readDataCache('opening_events') : null;
    if (cached) {
        openingEvents = cached.events || [];
        openingEventMagicPool = cached.magic_pool || [];
        setCustomRegistries(cached.custom_tags || [], cached.custom_statuses || []);
        if (background) {
            refreshOpeningEventsFromServer({ silent: true });
            return;
        }
    }
    await refreshOpeningEventsFromServer({ silent: !!cached });
}

async function refreshOpeningEventsFromServer({ silent = false } = {}) {
    try {
        if (!silent) bootLoader.step(UI.init_opening_events, 78);
        const resp = await fetch(`/api/opening-events?${buildModQueryString()}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        openingEvents = data.events || [];
        openingEventMagicPool = data.magic_pool || [];
        setCustomRegistries(data.custom_tags || [], data.custom_statuses || []);
        writeDataCache('opening_events', {
            events: openingEvents,
            magic_pool: openingEventMagicPool,
            custom_tags: data.custom_tags || [],
            custom_statuses: data.custom_statuses || [],
        });
        refreshCardDataViews();
    } catch (e) {
        console.error('Failed to fetch opening events:', e);
        if (!openingEvents.length) {
            const cached = readDataCache('opening_events');
            openingEvents = cached ? (cached.events || []) : [];
            openingEventMagicPool = cached ? (cached.magic_pool || []) : [];
            setCustomRegistries(cached ? (cached.custom_tags || []) : [], cached ? (cached.custom_statuses || []) : []);
        }
    }
}

function setCustomRegistries(tags, statuses) {
    CUSTOM_TAG_DEFS = {};
    (Array.isArray(tags) ? tags : []).forEach(item => {
        if (item && item.id) CUSTOM_TAG_DEFS[String(item.id)] = item;
    });
    CUSTOM_STATUS_DEFS = {};
    (Array.isArray(statuses) ? statuses : []).forEach(item => {
        if (item && item.id) CUSTOM_STATUS_DEFS[String(item.id)] = item;
    });
}

function getCardDef(defId) {
    if (CARD_DEFS[defId]) return CARD_DEFS[defId];
    const raw = String(defId || '');
    if (raw.includes(':')) {
        const local = raw.split(':').pop();
        if (CARD_DEFS[local]) return CARD_DEFS[local];
        const pascal = local
            .split(/[_-]+/)
            .filter(Boolean)
            .map(part => part.charAt(0).toUpperCase() + part.slice(1))
            .join('');
        if (CARD_DEFS[pascal]) return CARD_DEFS[pascal];
    }
    return null;
}

function getCardLocalIds(cardDict, cardDef) {
    const ids = [];
    const push = value => {
        if (value == null) return;
        const raw = String(value).trim();
        if (!raw) return;
        ids.push(raw);
        const local = raw.includes(':') ? raw.split(':').pop() : raw;
        ids.push(local);
        const pascal = local
            .split(/[_-]+/)
            .filter(Boolean)
            .map(part => part.charAt(0).toUpperCase() + part.slice(1))
            .join('');
        if (pascal) ids.push(pascal);
    };
    push(cardDict && cardDict.def_id);
    push(cardDict && cardDict.id);
    push(cardDef && cardDef.id);
    push(cardDef && cardDef.legacy_id);
    return Array.from(new Set(ids));
}

function cardMatchesAnyLocalId(cardDict, cardDef, values) {
    const wanted = new Set((Array.isArray(values) ? values : [values]).map(v => String(v)));
    return getCardLocalIds(cardDict, cardDef).some(id => wanted.has(id));
}

function getFlagLabel(flag) {
    const normalized = normalizeCardFlag(flag);
    const custom = getCustomTagDef(normalized);
    if (custom) return getRegistryText(custom, 'name', normalized);
    if (normalized === 'fusion_layer' || normalized === 'fission_layer') return UI[normalized] || normalized;
    return UI[`tag_${normalized}`] || UI[`flag_${normalized}`] || normalized;
}

function getCardDisplayCosts(cardDict, cardDef, ownerState = null) {
    const baseE = cardDict.cost_e_override != null ? cardDict.cost_e_override : cardDef.cost_e;
    const baseM = cardDict.cost_m_override != null ? cardDict.cost_m_override : cardDef.cost_m;
    const mimicDiscount = Number(cardDict.mimic_discount || 0);
    const flags = new Set([...normalizeFlagList(cardDef.flags || []), ...normalizeFlagList(cardDict.instance_flags || [])]);
    normalizeFlagList(cardDict.disabled_flags || []).forEach(flag => flags.delete(flag));
    const dup = ownerState && ownerState.cards_played_this_turn
        ? Number(ownerState.cards_played_this_turn[cardDict.def_id] || 0)
        : 0;
    const swiftValue = Number(cardDef.swift_value || cardDict.swift_value || 0);
    const effectiveBaseE = Math.max(0, baseE - mimicDiscount - swiftValue);
    let extraE = flags.has('symbiosis') ? 0 : dup;
    if (cardMatchesAnyLocalId(cardDict, cardDef, ['Bamboo', 'jungle:bamboo'])) {
        const hand = Array.isArray(ownerState && ownerState.hand) ? ownerState.hand : [];
        extraE -= hand.filter(c => c && c !== cardDict && cardMatchesAnyLocalId(c, getCardDef(c.def_id || ''), ['Bamboo', 'jungle:bamboo'])).length;
    }
    const totalE = Math.max(0, effectiveBaseE + extraE);
    return { totalE, totalM: baseM, flags };
}

function isOwnBlindActive() {
    return getOwnBlindLevel() > 0;
}

function getOwnBlindLevel() {
    if (!gameState || !gameState.you || isSpectating) return 0;
    return Math.max(0, Math.floor(Number(gameState.you.blind || 0)));
}

function updateBlindVisualClasses(state = gameState) {
    const level = state && state.you && !isSpectating ? Math.max(0, Math.floor(Number(state.you.blind || 0))) : 0;
    const root = document.body;
    if (!root || !root.classList) return;
    for (let i = 1; i <= 4; i++) {
        root.classList.toggle(`blind-level-${i}`, level >= i);
    }
    root.dataset.blindLevel = level > 0 ? String(level) : '';
}

function getCardBlindLevelForSelf(cardDict, options = {}) {
    if (options.blindForSelf || cardDict && cardDict.__blind_for_self) {
        return Math.max(1, Math.floor(Number(options.blindLevel || cardDict.__blind_level || getOwnBlindLevel() || 1)));
    }
    if (options.autoBlindSelf === false) return 0;
    return isOwnHandCardInstance(cardDict) ? getOwnBlindLevel() : 0;
}

function isOwnHandCardInstance(cardDict) {
    if (!cardDict || cardDict.instance_id == null || !gameState || !gameState.you) return false;
    const iid = String(cardDict.instance_id);
    return Array.isArray(gameState.you.hand) && gameState.you.hand.some(card => String(card.instance_id) === iid);
}

function shouldBlindCardForSelf(cardDict, options = {}) {
    return getCardBlindLevelForSelf(cardDict, options) > 0;
}

function getBlindedCardDisplayName(cardDict, cardDef, options = {}) {
    const blindLevel = getCardBlindLevelForSelf(cardDict, options);
    return blindLevel > 0 ? '?' : getCardName(cardDef);
}

function getCardBlindDisplayColor(cardDef, blindLevel = 0) {
    if (blindLevel >= 2) return '#7f8c8d';
    return CARD_TYPE_COLORS[(cardDef && cardDef.card_type) || ''] || COLORS.text_primary;
}

function getCardLayerLabel(cardDict) {
    const fusionLevel = Number(cardDict.fusion_level || 1);
    const fissionLevel = Number(cardDict.fission_level || 1);
    const parts = [];
    if (fusionLevel > 1) parts.push(`${UI.fusion_layer || 'Fusion'}:${fusionLevel}`);
    if (fissionLevel > 1) parts.push(`${UI.fission_layer || 'Fission'}:${fissionLevel}`);
    return parts.length ? ` (${parts.join(' ')})` : '';
}

function getCardArtUrl(cardDict, cardDef) {
    const extraHits = Math.max(0, Number(cardDict && cardDict.extra_hits || 0));
    if (extraHits > 0) {
        const upgraded = (cardDict && (cardDict.upgraded_image_url || cardDict.upgraded_image))
            || (cardDef && (cardDef.upgraded_image_url || cardDef.upgraded_image));
        if (upgraded) return upgraded;
    }
    return (cardDict && (cardDict.image_url || cardDict.image))
        || (cardDef && (cardDef.image_url || cardDef.image))
        || '';
}

function getEquipmentIconHtml(cardInst, cardDef) {
    const imageUrl = getCardArtUrl(cardInst || {}, cardDef || {});
    const type = cardDef && cardDef.card_type ? cardDef.card_type : 'root';
    const typeColor = CARD_TYPE_COLORS[type] || COLORS.root || COLORS.text_primary;
    const fallbackText = (type === 'root' ? 'R' : String(type || '?').slice(0, 1).toUpperCase());
    const style = `--equip-icon-color:${typeColor}`;
    const fallback = `<span class="equip-icon-fallback${imageUrl ? ' hidden' : ''}">${escapeHtml(fallbackText)}</span>`;
    const img = imageUrl
        ? `<img class="equip-icon-img" src="${escapeHtml(imageUrl)}" alt="" loading="lazy" onerror="this.classList.add('hidden');this.nextElementSibling.classList.remove('hidden')">`
        : '';
    return `<span class="equip-icon" style="${style}">${img}${fallback}</span>`;
}

function getCardEffectTextForInstance(cardDict, cardDef) {
    let text = getCardEffectText(cardDef) || '';
    const extraHits = Math.max(0, Number(cardDict && cardDict.extra_hits || 0));
    if (!extraHits || !text || !cardDef) return text;
    const info = getAttackDamageBaseInfo(cardDict || {}, cardDef);
    const baseHits = Math.max(
        1,
        Math.round(Number((info && info.hits) || 1)),
        Math.round(Number(cardDef.hits || 1))
    );
    const nextHits = baseHits + extraHits;
    if (nextHits <= baseHits || baseHits < 2) return text;
    if (info && !info.triangle) {
        const times = '\u00d7';
        const oldHitPattern = new RegExp(`(\\d+\\s*[DＤ]\\s*[x×${times}]\\s*)${baseHits}`, 'g');
        text = text.replace(oldHitPattern, `$1${nextHits}`);
    }
    const baseCopyCount = Math.max(0, baseHits - 1);
    const nextCopyCount = Math.max(0, nextHits - 1);
    if (nextCopyCount > baseCopyCount && baseCopyCount > 0) {
        text = text.replace(
            new RegExp(`(将)${baseCopyCount}(张\\s*\\[\\[card:[^\\]]+\\]\\])`, 'g'),
            `$1${nextCopyCount}$2`
        );
    }
    text = text.replace(new RegExp(`(破损\\s*[x×]\\s*)${baseHits}(\\s*层)`, 'g'), `$1${nextHits}$2`);
    text = text.replace(new RegExp(`${baseHits}(\\s*层\\s*\\d+\\s*级\\s*(?:回合回复|魔力回合回复))`, 'g'), `${nextHits}$1`);
    text = text.replace(new RegExp(`([（(])\\s*${baseHits}\\s*(子瓣|petals?|pétales?|pétalas|лепестка|лепестков|子弁)([^）)]*[）)])`, 'gi'), `$1${nextHits}$2$3`);
    return text;
}

function createCardElement(cardDict, options = {}) {
    const { faceDown = false, small = false, draggable = false, onClick = null, showAllFlags = false, disableIntro = false } = options;
    const el = document.createElement('div');
    el.className = 'card' + (small ? ' card-small' : '') + (faceDown ? ' card-facedown' : '');
    if (faceDown) {
        el.innerHTML = '<div class="card-back">?</div>';
        return el;
    }
    const defId = cardDict.def_id || '';
    const cardDef = getCardDef(defId);
    if (!cardDef) {
        el.textContent = defId || '?';
        return el;
    }
    if (cardDef.card_type) {
        el.classList.add(cardDef.card_type);
    }
    if (defId === 'Assembler' || cardDef.id === 'Assembler' || cardDef.legacy_id === 'Assembler' || cardDef.name_cn === '重构机') {
        el.classList.add('card-assembler');
    }
    if (defId === 'Honey' || cardDef.id === 'Honey' || cardDef.legacy_id === 'Honey' || cardDef.name_cn === '蜂蜜') {
        el.classList.add('card-honey');
    }
    if (cardMatchesAnyLocalId(cardDict, cardDef, ['Grapes', 'MagicGrapes', 'Peas', 'MagicPeas'])
        || ['葡萄', '魔法葡萄', '豌豆', '魔法豌豆'].includes(cardDef.name_cn)) {
        el.classList.add('card-petal-copy');
    }
    const rawTypeLabel = getCardTypeLabel(cardDef.card_type) || cardDef.card_type;
    const blindLevel = getCardBlindLevelForSelf(cardDict, options);
    const blinded = blindLevel > 0;
    const hideTypeByBlind = blindLevel >= 2;
    const typeColor = CARD_TYPE_COLORS[cardDef.card_type] || COLORS.text_primary;
    const displayTypeColor = getCardBlindDisplayColor(cardDef, blindLevel);
    const typeLabel = hideTypeByBlind ? '?' : rawTypeLabel;
    const cardName = blinded ? '?' : getCardName(cardDef);
    const englishName = (!blinded && shouldShowEnglishCardName(cardDef, cardName)) ? getEnglishCardName(cardDef) : '';
    const effectText = blinded ? '?' : getCardEffectTextForInstance(cardDict, cardDef);
    const descriptionText = blinded ? '?' : getCardDescriptionText(cardDef);
    const imageUrl = (!blinded && showCardImages) ? getCardArtUrl(cardDict, cardDef) : '';
    if (blinded) {
        el.classList.add('card-blinded');
        el.classList.toggle('card-blinded-deep', hideTypeByBlind);
        el.dataset.blindLevel = String(blindLevel);
    }
    el.classList.add(englishName ? 'card-has-english' : 'card-no-english');
    el.classList.add(imageUrl ? 'card-has-art' : 'card-no-art');
    const cardArtHtml = imageUrl
        ? `<div class="card-art"><img src="${escapeHtml(imageUrl)}" alt="" loading="lazy" onerror="this.closest('.card-art').classList.add('hidden')"></div>`
        : '';
    const predictionOptions = options.prediction || options.predictionOptions || {};
    const cardOwnerState = options.ownerState || options.attackerState || predictionOptions.attackerState || getCardOwnerStateForPrediction(cardDict) || (gameState && gameState.you);
    const { totalE, totalM, flags } = getCardDisplayCosts(cardDict, cardDef, cardOwnerState);
    const swiftValue = Number(cardDef.swift_value || cardDict.swift_value || 0);
    const magicSwiftValue = Number(cardDef.magic_swift_value || cardDict.magic_swift_value || 0);
    const powerValue = Number(cardDef.power_value || cardDict.power_value || 0);
    const copyCount = Number(cardDef.copy_count || 0);
    el.style.borderColor = displayTypeColor;
    el.dataset.instanceId = cardDict.instance_id;
    el.dataset.defId = defId;
    let flagsHtml = '';
    if (!blinded) for (const flag of flags) {
        if (flag === 'swift' && swiftValue > 0) continue;
        if (flag === 'magic_swift' && magicSwiftValue > 0) continue;
        if (flag === 'power' && powerValue > 0) continue;
        if (flag === 'copy' && copyCount > 0) continue;
        if (!shouldDisplayCardFlag(flag, { showSystemFlags: showAllFlags })) continue;
        const custom = getCustomTagDef(flag);
        if (custom) {
            flagsHtml += customTagHtml(flag);
            continue;
        }
        const style = CARD_FLAG_STYLES[flag];
        if (style) {
            const label = UI['flag_' + flag] || UI['tag_' + flag] || flag;
            flagsHtml += `<span class="card-flag ${style.cls}">${escapeHtml(label)}</span>`;
        }
    }
    const fusionLevel = Number(cardDict.fusion_level || 1);
    const fissionLevel = Number(cardDict.fission_level || 1);
    if (!blinded && fusionLevel > 1) {
        flagsHtml += `<span class="card-flag fusion-layer">${escapeHtml(UI.fusion_layer || 'Fusion')}: ${fusionLevel}</span>`;
    }
    if (!blinded && fissionLevel > 1) {
        flagsHtml += `<span class="card-flag fission-layer">${escapeHtml(UI.fission_layer || 'Fission')}: ${fissionLevel}</span>`;
    }
    if (!blinded && !showAllFlags && defId === 'Tomato' && cardDict.instance_id != null) {
        const tomatoLayer = Math.min(6, Math.max(0, Number(cardDict.held_turns || 0)));
        flagsHtml += `<span class="card-flag tomato-layer">${escapeHtml(UI.tomato_layer || '层数')}: ${tomatoLayer}</span>`;
    }
    if (!blinded && swiftValue > 0) {
        flagsHtml += `<span class="card-flag swift">${escapeHtml(UI.tag_swift || 'Swift')}: ${swiftValue}</span>`;
    }
    if (!blinded && magicSwiftValue > 0) {
        flagsHtml += `<span class="card-flag magic-swift">${escapeHtml(UI.tag_magic_swift || 'Magic Swift')}: ${magicSwiftValue}</span>`;
    }
    if (!blinded && powerValue > 0) {
        flagsHtml += `<span class="card-flag power">${escapeHtml(UI.tag_power || 'Power')}: ${powerValue}</span>`;
    }
    if (!blinded && copyCount > 0) {
        flagsHtml += `<span class="card-flag copy">${escapeHtml(UI.tag_copy || 'Copy')}: ${copyCount}</span>`;
    }
    if (!blinded) {
        flagsHtml += equipmentCounterFlagHtml(cardDict);
    }
    const predictionHtml = blinded ? '' : getCardPlayEffectPredictionHtml(cardDict, {
        ...predictionOptions,
        ownerState: predictionOptions.ownerState || cardOwnerState,
        attackerState: predictionOptions.attackerState || cardOwnerState,
    });
    const bottomHtml = (predictionHtml || flagsHtml)
        ? `<div class="card-bottom-zone ${predictionHtml ? 'has-prediction' : ''}">
                ${predictionHtml || ''}
                ${predictionHtml || flagsHtml ? `<div class="card-flags ${flagsHtml ? '' : 'card-flags-empty'}">${flagsHtml}</div>` : ''}
           </div>`
        : '';
    el.innerHTML = `
        <div class="card-costs">
            <span class="cost-e">${blinded ? '?' : totalE}</span>
            <span class="card-name" style="color:${displayTypeColor}">${escapeHtml(cardName)}</span>
            <span class="cost-m">${blinded ? '?' : totalM}</span>
        </div>
        ${englishName ? `<div class="card-english-name" style="color:${displayTypeColor}">${escapeHtml(englishName)}</div>` : ''}
        ${cardArtHtml}
        <div class="card-type-label-wrap"><span class="card-type-label" style="color:${displayTypeColor}">${escapeHtml(typeLabel)}</span></div>
        <div class="card-effect">${colorizeCardText(effectText || '')}</div>
        ${descriptionText ? `<div class="card-description">${colorizeCardText(descriptionText)}</div>` : ''}
        ${bottomHtml}
    `;
    bindInlineCardChips(el);
    if (draggable) {
        el.classList.add('card-draggable');
        el.addEventListener('mousedown', (e) => startCardDrag(e, el));
        el.addEventListener('touchstart', (e) => startCardDrag(e, el), { passive: false });
    }
    if (onClick) {
        el.addEventListener('click', onClick);
        el.style.cursor = 'pointer';
    }
    if (!disableIntro) {
        attachTermIntroToCard(el, cardDict, {
            ownerState: cardOwnerState,
            prediction: predictionOptions,
            blindForSelf: blinded,
            blindLevel,
        });
    }
    return el;
}

function normalizeFlagList(value) {
    if (!value) return [];
    if (Array.isArray(value)) return value.map(normalizeCardFlag).filter(Boolean);
    if (value instanceof Set) return Array.from(value).map(normalizeCardFlag).filter(Boolean);
    if (typeof value === 'string') return value.split(/[,\s]+/).map(normalizeCardFlag).filter(Boolean);
    if (typeof value === 'object') return Object.entries(value)
        .filter(([_, enabled]) => !!enabled)
        .map(([flag]) => normalizeCardFlag(flag))
        .filter(Boolean);
    return [];
}

function collectCardAddedFlags(cardDict) {
    const fields = ['instance_flags', 'flags', 'tags', 'temporary_flags', 'extra_flags', 'added_flags'];
    const flags = new Set();
    fields.forEach(field => normalizeFlagList(cardDict && cardDict[field]).forEach(flag => flags.add(flag)));
    return flags;
}

function collectCardDisabledFlags(cardDict) {
    const fields = ['disabled_flags', 'removed_flags'];
    const flags = new Set();
    fields.forEach(field => normalizeFlagList(cardDict && cardDict[field]).forEach(flag => flags.add(flag)));
    return flags;
}

function getEffectiveCardFlagSets(cardDict, cardDef) {
    const base = new Set(normalizeFlagList((cardDef && cardDef.flags) || []));
    const added = collectCardAddedFlags(cardDict);
    const disabled = collectCardDisabledFlags(cardDict);
    const effective = new Set([...base, ...added]);
    disabled.forEach(flag => effective.delete(flag));
    return { base, added, disabled, effective };
}

function cardHasSelfOnlyFlag(cardDict, cardDef = null) {
    const resolvedDef = cardDef || getCardDef(cardDict && cardDict.def_id);
    const { effective } = getEffectiveCardFlagSets(cardDict || {}, resolvedDef || {});
    return effective.has('self_only') || effective.has('tag_self_only');
}

function shouldDisplayCardFlag(flag, options = {}) {
    const normalized = normalizeCardFlag(flag);
    if (!normalized) return false;
    if (normalized === 'infinite_exclude') return !!options.showSystemFlags;
    return true;
}

function cardFlagHtml(flag, text = null) {
    const normalized = normalizeCardFlag(flag);
    if (getCustomTagDef(normalized)) return customTagHtml(normalized, text);
    if (normalized === 'fusion_layer') {
        const label = text || `${UI.fusion_layer || 'Fusion'}`;
        return `<span class="card-flag fusion-layer">${escapeHtml(label)}</span>`;
    }
    if (normalized === 'fission_layer') {
        const label = text || `${UI.fission_layer || 'Fission'}`;
        return `<span class="card-flag fission-layer">${escapeHtml(label)}</span>`;
    }
    const style = CARD_FLAG_STYLES[normalized];
    const label = text || UI['flag_' + normalized] || UI['tag_' + normalized] || normalized;
    const cls = style ? style.cls : 'custom';
    return `<span class="card-flag ${cls}">${escapeHtml(label)}</span>`;
}

function equipmentCounterLabel(key) {
    const normalized = String(key || '').trim();
    if (!normalized) return '';
    const lower = normalized.toLowerCase();
    if (lower === 'layers' || lower === 'layer' || lower === 'stacks' || lower === 'stack') return UI.tomato_layer || '层数';
    if (lower === 'durability') return UI.status_durability || '耐久';
    if (lower === 'charges' || lower === 'charge') return UI.status_charges || '充能';
    return normalized;
}

function equipmentCounterFlagHtml(cardDict) {
    const counters = cardDict && cardDict.equipment_counters;
    if (!counters || typeof counters !== 'object') return '';
    return Object.entries(counters)
        .map(([key, value]) => [equipmentCounterLabel(key), Math.floor(Number(value || 0))])
        .filter(([label, value]) => label && value > 0)
        .map(([label, value]) => `<span class="card-flag custom">${escapeHtml(label)}: ${value}</span>`)
        .join('');
}

function buildInstanceOnlyFlagHtml(cardDict, cardDef, options = {}) {
    const { includeLayers = true, includeTomato = true, hideFlags = null } = options;
    if (!cardDict || !cardDef) return '';
    const hideSet = hideFlags ? new Set(hideFlags.map(f => normalizeCardFlag(f))) : null;
    const { base, effective } = getEffectiveCardFlagSets(cardDict, cardDef);
    const parts = [];
    const copyCount = Number(cardDef.copy_count || 0);
    const swiftValue = Number(cardDef.swift_value || cardDict.swift_value || 0);
    const magicSwiftValue = Number(cardDef.magic_swift_value || cardDict.magic_swift_value || 0);
    const powerValue = Number(cardDef.power_value || cardDict.power_value || 0);
    effective.forEach(flag => {
        if (flag === 'swift' && swiftValue > 0) return;
        if (flag === 'magic_swift' && magicSwiftValue > 0) return;
        if (flag === 'power' && powerValue > 0) return;
        if (flag === 'copy' && copyCount > 0) return;
        if (base.has(flag)) return;
        if (!shouldDisplayCardFlag(flag)) return;
        if (hideSet && hideSet.has(normalizeCardFlag(flag))) return;
        parts.push(cardFlagHtml(flag));
    });
    if (includeLayers) {
        const fusionLevel = Math.max(1, Number(cardDict.fusion_level || 1));
        const fissionLevel = Math.max(1, Number(cardDict.fission_level || 1));
        if (fusionLevel > 1) parts.push(cardFlagHtml('fusion_layer', `${UI.fusion_layer || 'Fusion'}: ${fusionLevel}`));
        if (fissionLevel > 1) parts.push(cardFlagHtml('fission_layer', `${UI.fission_layer || 'Fission'}: ${fissionLevel}`));
    }
    if (includeTomato && cardDict.def_id === 'Tomato') {
        const tomatoLayer = Math.min(6, Math.max(0, Number(cardDict.held_turns || 0)));
        if (tomatoLayer > 0) {
            parts.push(`<span class="card-flag tomato-layer">${escapeHtml(UI.tomato_layer || 'Layer')}: ${tomatoLayer}</span>`);
        }
    }
    if (swiftValue > 0) {
        parts.push(cardFlagHtml('swift', `${UI.tag_swift || 'Swift'}: ${swiftValue}`));
    }
    if (magicSwiftValue > 0) {
        parts.push(cardFlagHtml('magic_swift', `${UI.tag_magic_swift || 'Magic Swift'}: ${magicSwiftValue}`));
    }
    if (powerValue > 0) {
        parts.push(cardFlagHtml('power', `${UI.tag_power || 'Power'}: ${powerValue}`));
    }
    if (copyCount > 0) {
        parts.push(cardFlagHtml('copy', `${UI.tag_copy || 'Copy'}: ${copyCount}`));
    }
    const equipmentCountersHtml = equipmentCounterFlagHtml(cardDict);
    if (equipmentCountersHtml) parts.push(equipmentCountersHtml);
    return parts.join('');
}

function createCardChoiceChip(cardDict, options = {}) {
    const chip = document.createElement('span');
    chip.className = 'choice-card-token';
    const defId = (cardDict && cardDict.def_id) || '';
    const cardDef = getCardDef(defId);
    if (!cardDef) {
        const fallback = {
            ManaOrb: { name: currentLang === 'zh' ? '魔法球' : 'Mana Orb', type: 'bloom' },
            Light: { name: currentLang === 'zh' ? '轻' : 'Light', type: 'thorn' },
        }[String(defId)] || null;
        const typeColor = fallback ? (CARD_TYPE_COLORS[fallback.type] || COLORS.text_primary) : COLORS.text_primary;
        const name = document.createElement('span');
        name.className = 'choice-card-name';
        name.style.borderColor = typeColor;
        name.style.color = typeColor;
        name.textContent = fallback ? fallback.name : (defId || '?');
        chip.appendChild(name);
        const flagsHtml = Array.from(new Set(((cardDict && cardDict.instance_flags) || [])
            .map(flag => normalizeCardFlag(flag))
            .filter(flag => shouldDisplayCardFlag(flag, options))))
            .map(flag => cardFlagHtml(flag))
            .join('');
        if (flagsHtml) {
            const flags = document.createElement('span');
            flags.className = 'choice-card-flags';
            flags.innerHTML = flagsHtml;
            chip.appendChild(flags);
        }
        return chip;
    }
    const blindLevel = getCardBlindLevelForSelf(cardDict, options);
    const blinded = blindLevel > 0;
    const hideTypeByBlind = blindLevel >= 2;
    const typeColor = getCardBlindDisplayColor(cardDef, blindLevel);
    if (blinded) {
        chip.classList.add('choice-card-blinded');
        chip.classList.toggle('choice-card-blinded-deep', hideTypeByBlind);
    }
    const name = document.createElement('span');
    name.className = 'choice-card-name';
    name.style.borderColor = typeColor;
    name.style.color = typeColor;
    name.textContent = blinded ? (hideTypeByBlind ? '?' : (getCardTypeLabel(cardDef.card_type) || '?')) : getCardName(cardDef);
    chip.appendChild(name);
    if (!blinded && options.extraCostText) {
        const cost = document.createElement('span');
        cost.className = 'choice-card-extra-cost';
        cost.textContent = options.extraCostText;
        chip.appendChild(cost);
    }
    const flagsHtml = blinded ? '' : buildInstanceOnlyFlagHtml(cardDict, cardDef, options);
    if (flagsHtml) {
        const flags = document.createElement('span');
        flags.className = 'choice-card-flags';
        flags.innerHTML = flagsHtml;
        chip.appendChild(flags);
    }
    const previewOptions = options.previewOptions || options.cardOptions || null;
    const previewCard = blinded ? { ...cardDict, __blind_for_self: true, __blind_level: blindLevel } : cardDict;
    attachFloatingCardPreview(chip, previewCard, { ...(previewOptions || {}), blindForSelf: blinded, blindLevel });
    attachTermIntroToCard(chip, previewCard, { ...(previewOptions || {}), blindForSelf: blinded, blindLevel });
    return chip;
}

function cardChoiceOption(cardDict, extra = {}) {
    const cardDef = getCardDef((cardDict && cardDict.def_id) || '');
    return {
        kind: 'card',
        card: cardDict,
        text: cardDef ? getCardName(cardDef) : ((cardDict && cardDict.def_id) || '?'),
        ...extra,
    };
}

function isMimicCardDict(cardDict) {
    const rawId = String((cardDict && (cardDict.def_id || cardDict.id)) || '');
    return rawId === 'Mimic' || rawId.toLowerCase().endsWith(':mimic');
}

function getMimicSpecialCostForCard(cardDict) {
    if (!cardDict) return 0;
    const fusionExtra = Math.max(0, Math.floor(Number(cardDict.fusion_level || 1)) - 1);
    const fissionExtra = Math.max(0, Math.floor(Number(cardDict.fission_level || 1)) - 1);
    const tomatoLayer = cardDict.def_id === 'Tomato'
        ? Math.min(6, Math.max(0, Math.floor(Number(cardDict.held_turns || 0))))
        : 0;
    return Math.ceil((fusionExtra + fissionExtra + tomatoLayer) / 2);
}

function getAvailableElixirForMimicChoice(sourceCard, ownerState = null) {
    const owner = ownerState || (gameState && gameState.you) || {};
    const current = getBarValueForKey(owner, 'elixir');
    const normalCost = sourceCard ? (getOptimisticResourceCost(sourceCard, owner) || {}).totalE || 0 : 0;
    return Math.max(0, current - normalCost);
}

function mimicCardChoiceOption(cardDict, sourceCard = null, ownerState = null) {
    const cost = getMimicSpecialCostForCard(cardDict);
    const availableE = getAvailableElixirForMimicChoice(sourceCard, ownerState);
    const extraCostText = (UI.mimic_extra_cost || 'Cost {0}E').replace('{0}', cost);
    return cardChoiceOption(cardDict, {
        extraCostText,
        disabled: cost > availableE,
    });
}

function stableJsonForCard(value) {
    if (Array.isArray(value)) return value.map(stableJsonForCard);
    if (value && typeof value === 'object') {
        const out = {};
        Object.keys(value).sort().forEach(key => {
            if (key === 'instance_id' || key === 'responder_id') return;
            out[key] = stableJsonForCard(value[key]);
        });
        return out;
    }
    return value;
}

function counterCardGroupSignature(cardDict) {
    const cardDef = getCardDef((cardDict && cardDict.def_id) || '');
    return JSON.stringify({
        card: stableJsonForCard(cardDict || {}),
        type: cardDef ? cardDef.card_type : '',
        trigger: cardDef ? cardDef.response_trigger : '',
        flags: cardDef ? Array.from(cardDef.flags || []).sort() : [],
    });
}

function cardComboChoiceOption(cards, extra = {}) {
    const list = Array.isArray(cards) ? cards : [];
    return {
        kind: 'card-combo',
        cards: list,
        text: list.map(c => {
            const cd = getCardDef(c.def_id);
            return cd ? getCardName(cd) : c.def_id;
        }).join(' + '),
        ...extra,
    };
}

function equipmentChoiceOption(equipment, extra = {}) {
    const card = equipment && (equipment.card_instance || equipment.card || equipment);
    const cardDict = { ...(card || {}) };
    if (equipment && equipment.custom_vars && typeof equipment.custom_vars === 'object') {
        cardDict.equipment_counters = { ...(cardDict.equipment_counters || {}), ...equipment.custom_vars };
    }
    return cardChoiceOption(cardDict, extra);
}

function cardDefChoiceOption(defId, extra = {}) {
    return cardChoiceOption({ def_id: defId }, extra);
}

const ATTACK_DAMAGE_FALLBACKS = {
    Basic: { amount: 6, hits: 1 },
    Bone: { amount: 12, hits: 1 },
    Stinger: { amount: 20, hits: 1 },
    Sand: { amount: 3, hits: 4 },
    Wing: { amount: 8, hits: 2 },
    Light: { amount: 2, hits: 2 },
    Fang: { amount: 8, hits: 1 },
    Triangle: { amount: 6, hits: 1, triangle: true },
    MagicBone: { amount: 15, hits: 1 },
    MagicStinger: { amount: 30, hits: 1 },
    Claw: { amount: 5, hits: 1 },
    Rice: { amount: 6, hits: 1 },
    Glass: { amount: 5, hits: 1 },
    MagicGlass: { amount: 4, hits: 1 },
    Tomato: { amount: 8, hits: 1 },
};

function firstNumericEffectValue(value) {
    if (typeof value === 'number') return value;
    if (typeof value === 'string' && value.trim() !== '' && !Number.isNaN(Number(value))) return Number(value);
    if (value && typeof value === 'object') {
        if (typeof value.value === 'number') return value.value;
        if (typeof value.amount === 'number') return value.amount;
    }
    return null;
}

function getAttackDamageBaseInfo(cardDict, cardDef) {
    if (!cardDef || cardDef.card_type !== 'thorn') return null;
    const fallback = ATTACK_DAMAGE_FALLBACKS[cardDict.def_id || cardDef.id] || null;
    const onPlay = cardDef.v2_events && cardDef.v2_events.on_play;
    const v2Steps = onPlay && (Array.isArray(onPlay.steps) ? onPlay.steps : (Array.isArray(onPlay) ? onPlay : []));
    const v2DamageStep = (Array.isArray(v2Steps) ? v2Steps : []).find(step => {
        if (!step || typeof step !== 'object') return false;
        const op = step.op || step.type;
        return op === 'deal_damage' || op === 'damage';
    });
    if (v2DamageStep) {
        const params = v2DamageStep.params || v2DamageStep;
        const amount = firstNumericEffectValue(params.amount);
        const hits = firstNumericEffectValue(params.hits);
        if (amount != null) {
            return {
                amount,
                hits: Math.max(1, Number(hits || 1)),
                triangle: false,
                inheritExtraHits: params.inherit_extra_hits !== false && params.use_card_extra_hits !== false,
            };
        }
    }
    const effects = Array.isArray(cardDef.effects) ? cardDef.effects : [];
    const damageEffect = effects.find(effect => {
        const type = effect && effect.type;
        return type === 'damage' || type === 'deal_damage' || type === 'lifesteal_damage' || type === 'triangle_damage';
    });
    if (damageEffect) {
        const params = damageEffect.params || {};
        const amount = firstNumericEffectValue(params.amount);
        const hits = firstNumericEffectValue(params.hits);
        if (amount != null) {
            return {
                amount,
                hits: Math.max(1, Number(hits || (cardDef.hits || (fallback && fallback.hits) || 1))),
                triangle: damageEffect.type === 'triangle_damage' || cardDict.def_id === 'Triangle',
                inheritExtraHits: true,
            };
        }
    }
    const amount = firstNumericEffectValue(cardDef.damage);
    if (amount != null && amount > 0) {
        return {
            amount,
            hits: Math.max(1, Number(cardDef.hits || (fallback && fallback.hits) || 1)),
            triangle: cardDict.def_id === 'Triangle',
            inheritExtraHits: true,
        };
    }
    return fallback;
}

function formatDamageHits(values) {
    const times = '\u00d7';
    const list = (Array.isArray(values) ? values : []).map(v => Math.max(0, Math.ceil(Number(v || 0))));
    if (!list.length) return '';
    if (list.length === 1) return `${list[0]}D`;
    const first = list[0];
    if (list.every(v => v === first)) return `${first}D${times}${list.length}`;
    return list.map(v => `${v}D`).join(' + ');
}

function getResponseAttackerState(data) {
    const pending = (gameState && gameState.pending_response) || {};
    const playerId = normalizePlayerId(
        (data && data.player_id) != null ? data.player_id
            : ((data && data.attacker_id) != null ? data.attacker_id : pending.player_id)
    );
    return playerId == null ? {} : (getPlayerDataById(playerId) || {});
}

function getResponseTargetState(data) {
    const pending = (gameState && gameState.pending_response) || {};
    let targetId = normalizePlayerId(
        (data && data.target_player_id) != null ? data.target_player_id
            : ((data && data.target_id) != null ? data.target_id : pending.target_player_id)
    );
    if (targetId == null) targetId = normalizePlayerId(playerId);
    return targetId == null ? {} : (getPlayerDataById(targetId) || {});
}

function readPlayerHealthValue(playerState, keys, fallback = 0) {
    for (const key of keys) {
        const value = Number(playerState && playerState[key]);
        if (Number.isFinite(value)) return value;
    }
    return fallback;
}

function getClawDamageHits(cardDict, attackerState, targetState, info) {
    const fusion = Math.max(1, Number(cardDict.fusion_level || 1));
    const fission = Math.max(1, Number(cardDict.fission_level || 1));
    const baseHits = Math.max(1, Math.round(Number((info && info.hits) || 1)) + Math.max(0, Number(cardDict.extra_hits || 0)));
    const bonus = Math.max(0, Number(cardDict.bonus_damage || 0));
    const maxHealth = readPlayerHealthValue(targetState, ['max_health', 'maxHp', 'maxH', 'max_h'], 0);
    let health = readPlayerHealthValue(targetState, ['health', 'hp', 'h'], maxHealth);
    if (!maxHealth) {
        const amount = Number((info && info.amount) || 5) + bonus;
        const perHit = Math.ceil(amount * fusion / fission);
        return Array.from({ length: baseHits * fission }, () => perHit);
    }
    const hits = [];
    for (let i = 0; i < baseHits * fission; i++) {
        const base = health >= maxHealth / 2 ? 10 : 5;
        const dealt = Math.ceil((base + bonus) * fusion / fission);
        hits.push(dealt);
        health = Math.max(0, health - dealt);
    }
    return hits;
}

function getActualAttackDamageHits(cardDict, attackerState = {}, targetState = {}) {
    const cardDef = getCardDef((cardDict && cardDict.def_id) || '');
    const info = getAttackDamageBaseInfo(cardDict || {}, cardDef);
    if (!info) return [];
    if ((cardDict.def_id || cardDef.id || '') === 'Claw') {
        return getClawDamageHits(cardDict || {}, attackerState || {}, targetState || {}, info);
    }
    const fusion = Math.max(1, Number(cardDict.fusion_level || 1));
    const fission = Math.max(1, Number(cardDict.fission_level || 1));
    let bonus = Math.max(0, Number(cardDict.bonus_damage || 0));
    if ((cardDict.def_id || '') === 'Tomato') {
        const tomatoLayer = Math.min(6, Math.max(0, Number(cardDict.held_turns || 0)));
        bonus = bonus > 0 ? Math.min(18, bonus) : tomatoLayer * 3;
    }
    if (info.triangle) {
        const startStacks = Math.max(0, Number(attackerState.triangle_stacks || 0));
        const hits = [];
        for (let i = 0; i < fission; i++) {
            const stack = Math.min(4, startStacks + i);
            const amount = Number(info.amount || 0) + 3 * stack + bonus;
            hits.push(Math.ceil(amount * fusion / fission));
        }
        return hits;
    }
    const amount = Number(info.amount || 0) + bonus;
    const perHit = Math.ceil(amount * fusion / fission);
    const inheritExtraHits = info.inheritExtraHits !== false && !cardMatchesAnyLocalId(cardDict, cardDef, ['Peas', 'MagicPeas']);
    const extraHits = inheritExtraHits ? Math.max(0, Number(cardDict.extra_hits || 0)) : 0;
    const totalHits = Math.max(1, Math.round(Number(info.hits || 1)) + extraHits) * fission;
    return Array.from({ length: totalHits }, () => perHit);
}

function getActualAttackDamageText(cardDict, attackerState = {}, targetState = {}) {
    return formatDamageHits(getActualAttackDamageHits(cardDict, attackerState, targetState));
}

function getPredictionPlayerById(id) {
    const pid = normalizePlayerId(id);
    if (pid == null || !gameState) return {};
    return getPlayerDataById(pid) || {};
}

function getPredictionPlayerRefs() {
    if (!gameState) return [];
    const refs = [gameState.you, gameState.teammate, gameState.opponent, gameState.opponent2];
    if (Array.isArray(gameState.spectate_players)) refs.push(...gameState.spectate_players);
    const seen = new Set();
    return refs.filter(player => {
        if (!player) return false;
        const id = normalizePlayerId(player.player_id);
        const key = id != null ? `id:${id}` : player;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });
}

function getCardOwnerStateForPrediction(cardDict) {
    if (!cardDict || cardDict.instance_id == null) return null;
    const instanceId = String(cardDict.instance_id);
    for (const player of getPredictionPlayerRefs()) {
        const zones = [
            Array.isArray(player.hand) ? player.hand : [],
            Array.isArray(player.revealed_hand) ? player.revealed_hand : [],
        ];
        if (zones.some(zone => zone.some(card => String(card && card.instance_id) === instanceId))) {
            return player;
        }
    }
    return null;
}

function getPredictionOwnerId(ownerState) {
    return normalizePlayerId(ownerState && ownerState.player_id);
}

function getDefaultEnemyIdsForPredictionOwner(ownerState) {
    const ownerId = getPredictionOwnerId(ownerState);
    if (!gameState) return [];
    if (gameState.mode === '2v2' && ownerId != null) {
        if (ownerId === 0 || ownerId === 1) return [2, 3];
        if (ownerId === 2 || ownerId === 3) return [0, 1];
    }
    if (ownerId === 0) return [1];
    if (ownerId === 1) return [0];
    return Array.isArray(gameState.enemy_ids)
        ? gameState.enemy_ids.map(normalizePlayerId).filter(id => id != null)
        : [];
}

function getFirstPredictionEnemyState(ownerState) {
    const enemyIds = getDefaultEnemyIdsForPredictionOwner(ownerState);
    if (enemyIds.length) {
        const aliveId = enemyIds.find(id => Number(getPredictionPlayerById(id).health || 0) > 0);
        return getPredictionPlayerById(aliveId != null ? aliveId : enemyIds[0]);
    }
    return gameState && gameState.opponent ? gameState.opponent : {};
}

function getDefaultPredictionTargetState(cardDict, ownerState = null) {
    if (!gameState) return {};
    const targetId = normalizePlayerId(cardDict && (cardDict.target_player_id ?? cardDict.target_id));
    if (targetId != null) return getPredictionPlayerById(targetId);
    return getFirstPredictionEnemyState(ownerState);
}

function cardHasEffectiveFlagForPrediction(cardDict, cardDef, flag) {
    const sets = getEffectiveCardFlagSets(cardDict || {}, cardDef || {});
    return sets.effective.has(flag);
}

function countActiveCorruptionEquipment() {
    if (!gameState) return 0;
    const players = Array.isArray(gameState.spectate_players) && gameState.spectate_players.length
        ? gameState.spectate_players
        : [gameState.you, gameState.teammate, gameState.opponent, gameState.opponent2].filter(Boolean);
    const seenEquipment = new Set();
    let count = 0;
    players.forEach((player, playerIndex) => {
        const ownerId = normalizePlayerId(player && player.player_id);
        (Array.isArray(player && player.equipment) ? player.equipment : []).forEach(eq => {
            const card = eq && (eq.card_instance || eq.card || eq);
            if (!card || card.def_id !== 'Corruption' || !eq.corruption_active) return;
            const instanceId = eq.instance_id ?? eq.equipment_instance_id ?? card.instance_id ?? card.instanceId;
            const key = instanceId != null && instanceId !== ''
                ? `eq:${instanceId}`
                : `owner:${ownerId != null ? ownerId : playerIndex}:slot:${(player.equipment || []).indexOf(eq)}`;
            if (seenEquipment.has(key)) return;
            seenEquipment.add(key);
            count += 1;
        });
    });
    return count;
}

function countDizzyEquipmentForPrediction(attackerState = {}) {
    let count = 0;
    const attackerId = normalizePlayerId(attackerState && attackerState.player_id);
    const players = [gameState && gameState.you, gameState && gameState.teammate, gameState && gameState.opponent, gameState && gameState.opponent2].filter(Boolean);
    players.forEach(player => {
        (Array.isArray(player && player.equipment) ? player.equipment : []).forEach(eq => {
            const card = eq && (eq.card_instance || eq.card || eq);
            const id = String(card && card.def_id || '').toLowerCase();
            const effectTarget = normalizePlayerId(eq && eq.effect_target);
            if (effectTarget != null && attackerId != null && effectTarget !== attackerId) return;
            if (id === 'dizzy' || id.endsWith(':dizzy')) count += 1;
        });
    });
    return count;
}

function countCutterEquipmentForPrediction(attackerState = {}) {
    let count = 0;
    const attackerId = normalizePlayerId(attackerState && attackerState.player_id);
    const players = [gameState && gameState.you, gameState && gameState.teammate, gameState && gameState.opponent, gameState && gameState.opponent2].filter(Boolean);
    players.forEach(player => {
        (Array.isArray(player && player.equipment) ? player.equipment : []).forEach(eq => {
            const card = eq && (eq.card_instance || eq.card || eq);
            const id = String(card && card.def_id || '').toLowerCase();
            const effectTarget = normalizePlayerId(eq && eq.effect_target);
            if (effectTarget != null && attackerId != null && effectTarget !== attackerId) return;
            if (id === 'cutter' || id.endsWith(':cutter')) count += 1;
        });
    });
    return count;
}

function simulateNoCounterAttackHits(cardDict, attackerState = {}, targetState = {}) {
    const cardDef = getCardDef((cardDict && cardDict.def_id) || '');
    const rawHits = getActualAttackDamageHits(cardDict || {}, attackerState || {}, targetState || {});
    if (!rawHits.length) return [];
    const hits = [];
    let dodge = Math.max(0, Number(targetState && targetState.dodge || 0));
    const armor = Math.max(0, Number(targetState && targetState.armor || 0));
    const invincible = !!(targetState && targetState.invincible);
    const sponge = !!(targetState && targetState.sponge_active);
    let nazarActive = !!(targetState && targetState.nazar_active);
    let nazarBigHits = Math.max(0, Number(targetState && targetState.nazar_big_hits || 0));
    const corruptionMult = 1.5 ** countActiveCorruptionEquipment();
    const dizzyMult = 1 + 0.5 * countDizzyEquipmentForPrediction(attackerState);
    const cutterBonus = countCutterEquipmentForPrediction(attackerState);
    const precision = cardHasEffectiveFlagForPrediction(cardDict || {}, cardDef || {}, 'precision');
    rawHits.forEach(raw => {
        let dmg = Math.max(0, Math.ceil(Number(raw || 0)));
        if (cutterBonus > 0) dmg += cutterBonus * 2;
        let precisionDodged = false;
        if (dodge > 0) {
            dodge -= 1;
            if (precision) {
                precisionDodged = true;
            } else {
                hits.push(0);
                return;
            }
        }
        if (invincible) {
            hits.push(0);
            return;
        }
        if (precisionDodged) dmg = Math.ceil(dmg / 2);
        if (dizzyMult > 1) dmg = Math.ceil(dmg * dizzyMult);
        if (corruptionMult > 1) dmg = Math.ceil(dmg * corruptionMult);
        if (nazarActive) {
            const original = dmg;
            dmg = Math.max(1, dmg - 9);
            if (original >= 10) {
                nazarBigHits += 1;
                if (nazarBigHits >= 2) {
                    nazarActive = false;
                    nazarBigHits = 0;
                }
            }
        }
        dmg = Math.max(0, dmg - armor);
        if (sponge && dmg > 0) {
            hits.push(0);
            return;
        }
        hits.push(dmg);
    });
    return hits;
}

function formatPredictionPart(value, suffix, cls) {
    const amount = Math.max(0, Math.ceil(Number(value || 0)));
    if (amount <= 0) return '';
    return `<span class="card-prediction-part ${cls}">${escapeHtml(`${amount}${suffix}`)}</span>`;
}

function formatPredictionDamagePart(hits) {
    const text = formatDamageHits(hits);
    if (!text) return '';
    return `<span class="card-prediction-part damage">${escapeHtml(text)}</span>`;
}

function formatPositiveEffectHits(values, suffix) {
    const times = '\u00d7';
    const list = (Array.isArray(values) ? values : [])
        .map(v => Math.max(0, Math.ceil(Number(v || 0))))
        .filter(v => Number.isFinite(v) && v > 0);
    if (!list.length) return '';
    if (list.length === 1) return `+${list[0]}${suffix}`;
    const first = list[0];
    if (list.every(v => v === first)) return `+${first}${suffix}${times}${list.length}`;
    return list.map(v => `+${v}${suffix}`).join(' ');
}

function formatPredictionSelfPart(values, suffix, cls) {
    const text = formatPositiveEffectHits(values, suffix);
    if (!text) return '';
    return `<span class="card-prediction-part ${cls}">${escapeHtml(text)}</span>`;
}

function pushPositiveValue(list, value, count = 1) {
    const amount = Math.max(0, Math.ceil(Number(value || 0)));
    const rawCount = Number(count);
    const times = Number.isFinite(rawCount) ? Math.max(0, Math.floor(rawCount)) : 1;
    if (amount <= 0 || times <= 0) return;
    for (let i = 0; i < times; i++) list.push(amount);
}

function effectTargetIsSelf(target) {
    if (target == null || target === '') return true;
    if (typeof target === 'string') {
        return ['self', 'source', 'owner', 'you', 'current_player'].includes(target);
    }
    if (target && typeof target === 'object') {
        const ref = String(target.ref || target.selector || target.type || '').toLowerCase();
        const value = String(target.value || target.target || '').toLowerCase();
        return ['self', 'source', 'owner'].includes(ref) || ['self', 'source', 'owner'].includes(value);
    }
    return false;
}

function collectSelfPredictionFromEffects(prediction, cardDict, cardDef, selfState, positiveHitCount) {
    const effects = Array.isArray(cardDef && cardDef.effects) ? cardDef.effects : [];
    effects.forEach(effect => {
        if (!effect || typeof effect !== 'object') return;
        const type = effect.type || effect.op;
        const params = effect.params || effect;
        if (type === 'lifesteal_damage') {
            pushPositiveValue(prediction.self.heal, firstNumericEffectValue(params.heal) || 4, positiveHitCount);
            return;
        }
        if (!effectTargetIsSelf(params.target)) return;
        if (type === 'heal') {
            pushPositiveValue(prediction.self.heal, firstNumericEffectValue(params.amount));
        } else if (type === 'gain_e' || type === 'gain_elixir') {
            pushPositiveValue(prediction.self.elixir, firstNumericEffectValue(params.amount));
        } else if (type === 'gain_m' || type === 'gain_magic') {
            pushPositiveValue(prediction.self.magic, firstNumericEffectValue(params.amount));
        } else if (type === 'gain_armor' || type === 'add_armor') {
            pushPositiveValue(prediction.self.armor, firstNumericEffectValue(params.amount));
        } else if (type === 'coffee_gain_e') {
            pushPositiveValue(prediction.self.elixir, getCoffeePredictionAmount(selfState));
        }
    });
}

function collectSelfPredictionFromV2Steps(prediction, steps, selfState, positiveHitCount) {
    (Array.isArray(steps) ? steps : []).forEach(step => {
        if (!step || typeof step !== 'object') return;
        const op = step.op || step.type;
        const params = step.params && typeof step.params === 'object' ? step.params : step;
        if (op === 'if') {
            return;
        }
        if (op === 'lifesteal_damage') {
            pushPositiveValue(prediction.self.heal, firstNumericEffectValue(params.heal) || 4, positiveHitCount);
            return;
        }
        if (!effectTargetIsSelf(params.target)) return;
        if (op === 'heal') {
            pushPositiveValue(prediction.self.heal, firstNumericEffectValue(params.amount));
        } else if (op === 'gain_e') {
            pushPositiveValue(prediction.self.elixir, firstNumericEffectValue(params.amount));
        } else if (op === 'gain_m') {
            pushPositiveValue(prediction.self.magic, firstNumericEffectValue(params.amount));
        } else if (op === 'add_armor' || op === 'gain_armor') {
            pushPositiveValue(prediction.self.armor, firstNumericEffectValue(params.amount));
        } else if (op === 'coffee_gain_e') {
            pushPositiveValue(prediction.self.elixir, getCoffeePredictionAmount(selfState));
        }
    });
}

function getCoffeePredictionAmount(selfState) {
    const vars = (selfState && selfState.custom_vars) || {};
    const marker = Number(vars['咖啡首次使用']);
    const hasMarker = Number.isFinite(marker);
    const firstUse = hasMarker ? marker > 0 : !!(selfState && selfState.coffee_first_use);
    return firstUse ? 2 : 1;
}

function addKnownSelfPrediction(prediction, cardDict, selfState) {
    const positiveHitCount = prediction.target.damageHits.filter(v => Number(v) > 0).length;
    switch (cardDict.def_id) {
        case 'Fang':
            if (!prediction.self.heal.length) pushPositiveValue(prediction.self.heal, 4, positiveHitCount);
            break;
        case 'Fries':
            if (!prediction.self.heal.length) pushPositiveValue(prediction.self.heal, 12);
            break;
        case 'Rose':
            if (!prediction.self.heal.length) pushPositiveValue(prediction.self.heal, 7);
            break;
        case 'ManaOrb':
            if (!prediction.self.magic.length) pushPositiveValue(prediction.self.magic, 3);
            break;
        case 'Coffee':
            if (!prediction.self.elixir.length) pushPositiveValue(prediction.self.elixir, getCoffeePredictionAmount(selfState));
            break;
        case 'MagicGlass':
            if (!prediction.self.magic.length) pushPositiveValue(prediction.self.magic, 2);
            break;
        default:
            break;
    }
}

function getCardPlayEffectPredictionParts(cardDict, options = {}) {
    const result = {
        target: { damageHits: [], poison: 0, fire: 0 },
        self: { heal: [], elixir: [], magic: [], armor: [] },
        damageHits: [],
        poison: 0,
        fire: 0,
    };
    if (!gameState || !cardDict || !cardDict.def_id) return result;
    const cardDef = getCardDef(cardDict.def_id);
    if (!cardDef) return result;
    const attackerState = options.attackerState || options.ownerState || getCardOwnerStateForPrediction(cardDict) || gameState.you || {};
    const targetState = options.targetState || getDefaultPredictionTargetState(cardDict, attackerState);
    const hasDamageOverride = Object.prototype.hasOwnProperty.call(options, 'damageHits');
    if (cardDef.card_type === 'thorn') {
        const hits = hasDamageOverride
            ? (Array.isArray(options.damageHits) ? options.damageHits : [])
            : simulateNoCounterAttackHits(cardDict, attackerState, targetState);
        result.target.damageHits = hits
            .map(v => Math.max(0, Math.ceil(Number(v || 0))))
            .filter(v => Number.isFinite(v));
        const toxic = Math.max(0, Number(targetState && targetState.toxic || 0));
        const positiveHits = result.target.damageHits.filter(v => Number(v) > 0).length;
        if (toxic > 0 && positiveHits > 0) {
            result.target.poison = toxic * positiveHits;
        }
    } else if (cardDict.def_id === 'Iris') {
        result.target.poison = 10;
    } else if (cardDict.def_id === 'Fire') {
        result.target.fire = 2;
    }
    const positiveHitCount = result.target.damageHits.filter(v => Number(v) > 0).length;
    collectSelfPredictionFromEffects(result, cardDict, cardDef, attackerState, positiveHitCount);
    const onPlay = cardDef.v2_events && cardDef.v2_events.on_play;
    const steps = onPlay && (onPlay.steps || onPlay);
    collectSelfPredictionFromV2Steps(result, steps, attackerState, positiveHitCount);
    addKnownSelfPrediction(result, cardDict, attackerState);
    result.damageHits = result.target.damageHits;
    result.poison = result.target.poison;
    result.fire = result.target.fire;
    return result;
}

function shouldShowCardPlayEffectPrediction(cardDict, options = {}) {
    if (!gameState || !cardDict || !cardDict.def_id) return false;
    if (cardDict.instance_id == null && !options.allowDefinitionCard) return false;
    const activePhases = new Set(['action', 'draw', 'response', 'choice']);
    if (!activePhases.has(gameState.phase)) return false;
    if (cardDict.instance_id != null) {
        const id = String(cardDict.instance_id);
        const ownerState = options.ownerState || options.attackerState || getCardOwnerStateForPrediction(cardDict);
        const ownerHand = ownerState && Array.isArray(ownerState.hand) ? ownerState.hand : null;
        if (ownerHand) {
            if (!ownerHand.some(card => String(card && card.instance_id) === id)) return false;
        } else {
            const hand = gameState && gameState.you && Array.isArray(gameState.you.hand) ? gameState.you.hand : [];
            if (!hand.some(card => String(card && card.instance_id) === id)) return false;
        }
    }
    return true;
}

function getCardPlayEffectPredictionHtml(cardDict, options = {}) {
    if (!shouldShowCardPlayEffectPrediction(cardDict, options)) return '';
    const prediction = getCardPlayEffectPredictionParts(cardDict, options);
    const targetParts = [];
    const selfParts = [];
    if (prediction.target.damageHits.length) targetParts.push(formatPredictionDamagePart(prediction.target.damageHits));
    if (prediction.target.poison > 0) targetParts.push(formatPredictionPart(prediction.target.poison, 'P', 'poison'));
    if (prediction.target.fire > 0) targetParts.push(formatPredictionPart(prediction.target.fire, 'F', 'fire'));
    selfParts.push(formatPredictionSelfPart(prediction.self.heal, 'H', 'heal'));
    selfParts.push(formatPredictionSelfPart(prediction.self.elixir, 'E', 'elixir'));
    selfParts.push(formatPredictionSelfPart(prediction.self.magic, 'M', 'magic'));
    selfParts.push(formatPredictionSelfPart(prediction.self.armor, 'A', 'armor'));
    const sections = [];
    const targetHtml = targetParts.filter(Boolean).join('');
    const selfHtml = selfParts.filter(Boolean).join('');
    if (targetHtml) {
        sections.push(`<span class="card-prediction-section"><span class="card-prediction-label">${escapeHtml(UI.prediction_target || '对目标')}:</span>${targetHtml}</span>`);
    }
    if (selfHtml) {
        sections.push(`<span class="card-prediction-section"><span class="card-prediction-label">${escapeHtml(UI.prediction_self || '对自己')}:</span>${selfHtml}</span>`);
    }
    const html = sections.join('');
    return html ? `<div class="card-prediction">${html}</div>` : '';
}

function normalizePredictionHits(parts) {
    return (Array.isArray(parts) ? parts : [])
        .map(v => Math.max(0, Math.ceil(Number(v || 0))))
        .filter(v => Number.isFinite(v));
}

function getResponseBaseEffectPrediction(data, cardDict, noCounterPrediction = {}) {
    const attackerState = getResponseAttackerState(data);
    const targetState = getResponseTargetState(data);
    const options = {
        attackerState,
        targetState,
        allowDefinitionCard: true,
    };
    if (noCounterPrediction && Object.prototype.hasOwnProperty.call(noCounterPrediction, 'parts')) {
        options.damageHits = normalizePredictionHits(noCounterPrediction.parts);
    }
    return getCardPlayEffectPredictionParts(cardDict, options);
}

function appendResponseEffectToken(parent, text, cls, extraClass = '') {
    if (!parent || !text) return;
    const token = document.createElement('span');
    token.className = `response-damage-preview response-effect-preview card-token ${cls}${extraClass ? ` ${extraClass}` : ''}`;
    token.textContent = text;
    parent.appendChild(token);
}

function appendResponseEffectPreview(parent, prediction) {
    if (!prediction) return;
    const damageText = formatDamageHits(prediction.damageHits || []);
    appendResponseEffectToken(parent, damageText, 'damage');
    if (Number(prediction.poison || 0) > 0) {
        appendResponseEffectToken(parent, `${Math.ceil(Number(prediction.poison))}P`, 'poison');
    }
    if (Number(prediction.fire || 0) > 0) {
        appendResponseEffectToken(parent, `${Math.ceil(Number(prediction.fire))}F`, 'fire');
    }
}

function counterCardCancelsResponseCard(counterCard, responseCard) {
    const counterDef = getCardDef(counterCard && counterCard.def_id);
    const responseDef = getCardDef(responseCard && responseCard.def_id);
    if (!counterDef || !responseDef) return false;
    if (counterCard.def_id === 'MagicBubble' && responseDef.card_type === 'bloom') return true;
    if (counterDef.response_trigger === responseDef.card_type && responseDef.card_type === 'bloom') return true;
    return false;
}

function getResponseCounterStatusReduction(data, cardDict, basePrediction, counterPrediction, counterCard) {
    const reduction = { poison: 0, fire: 0 };
    if (!basePrediction || (!basePrediction.poison && !basePrediction.fire)) return reduction;
    const cardDef = getCardDef(cardDict && cardDict.def_id);
    if (cardDef && cardDef.card_type === 'thorn') {
        const beforeHits = normalizePredictionHits(basePrediction.damageHits);
        const afterHits = normalizePredictionHits(counterPrediction && counterPrediction.after && counterPrediction.after.parts);
        if (beforeHits.length && (counterPrediction && counterPrediction.after && Object.prototype.hasOwnProperty.call(counterPrediction.after, 'parts'))) {
            const beforePositive = beforeHits.filter(v => v > 0).length;
            const afterPositive = afterHits.filter(v => v > 0).length;
            const targetState = getResponseTargetState(data);
            const toxic = Math.max(0, Number(targetState && targetState.toxic || 0));
            reduction.poison = Math.max(0, (beforePositive - afterPositive) * toxic);
        } else if (Number(counterPrediction && counterPrediction.reduction || 0) >= beforeHits.reduce((sum, v) => sum + v, 0)) {
            reduction.poison = Math.max(0, Number(basePrediction.poison || 0));
        }
        return reduction;
    }
    if (counterCardCancelsResponseCard(counterCard, cardDict)) {
        reduction.poison = Math.max(0, Number(basePrediction.poison || 0));
        reduction.fire = Math.max(0, Number(basePrediction.fire || 0));
    }
    return reduction;
}

function appendCounterEffectReductions(parent, prediction) {
    if (!parent || !prediction) return;
    if (Number(prediction.damage || 0) > 0) {
        const reduction = document.createElement('span');
        reduction.className = 'counter-damage-reduction';
        reduction.textContent = prediction.damageText || `-${Math.ceil(Number(prediction.damage))}D`;
        parent.appendChild(reduction);
    }
    if (Number(prediction.poison || 0) > 0) {
        const reduction = document.createElement('span');
        reduction.className = 'counter-status-reduction poison';
        reduction.textContent = `-${Math.ceil(Number(prediction.poison))}P`;
        parent.appendChild(reduction);
    }
    if (Number(prediction.fire || 0) > 0) {
        const reduction = document.createElement('span');
        reduction.className = 'counter-status-reduction fire';
        reduction.textContent = `-${Math.ceil(Number(prediction.fire))}F`;
        parent.appendChild(reduction);
    }
}

let floatingCardPreviewEl = null;
let floatingCardPreviewTimer = null;
let floatingCardPreviewTouchStart = null;

function removeFloatingCardPreview() {
    if (floatingCardPreviewTimer) {
        clearTimeout(floatingCardPreviewTimer);
        floatingCardPreviewTimer = null;
    }
    floatingCardPreviewTouchStart = null;
    if (floatingCardPreviewEl) {
        floatingCardPreviewEl.remove();
        floatingCardPreviewEl = null;
    }
}

function positionFloatingCardPreview(anchor, pos = null) {
    if (!floatingCardPreviewEl) return;
    const rect = anchor ? anchor.getBoundingClientRect() : null;
    const width = floatingCardPreviewEl.offsetWidth || 220;
    const height = floatingCardPreviewEl.offsetHeight || 310;
    const gap = 14;
    let left = rect ? rect.right + gap : ((pos && pos.x) || 0) + gap;
    let top = rect ? rect.top + rect.height * 0.5 - height * 0.5 : ((pos && pos.y) || 0) - height * 0.5;
    if (left + width > window.innerWidth - 8) {
        left = rect ? rect.left - width - gap : ((pos && pos.x) || 0) - width - gap;
    }
    if (top + height > window.innerHeight - 8) top = window.innerHeight - height - 8;
    left = Math.max(8, Math.min(window.innerWidth - width - 8, left));
    top = Math.max(8, Math.min(window.innerHeight - height - 8, top));
    floatingCardPreviewEl.style.left = `${left}px`;
    floatingCardPreviewEl.style.top = `${top}px`;
}

function getCardPredictionOptionsForOwner(cardDict, ownerState = null) {
    const attackerState = ownerState || getCardOwnerStateForPrediction(cardDict) || (gameState && gameState.you) || {};
    return {
        ownerState: attackerState,
        attackerState,
        targetState: getDefaultPredictionTargetState(cardDict, attackerState),
    };
}

function showFloatingCardPreview(cardDict, anchor, pos = null, cardOptions = {}) {
    const cardDef = getCardDef((cardDict && cardDict.def_id) || '');
    if (!cardDef) return;
    removeFloatingCardPreview();
    const preview = document.createElement('div');
    preview.className = 'floating-card-preview';
    const card = createCardElement(cardDict, {
        showAllFlags: false,
        disableIntro: true,
        ...cardOptions,
    });
    card.classList.add('floating-card-preview-card');
    preview.appendChild(card);
    document.body.appendChild(preview);
    floatingCardPreviewEl = preview;
    positionFloatingCardPreview(anchor, pos);
    requestAnimationFrame(() => preview.classList.add('active'));
}

function attachFloatingCardPreview(anchor, cardDict, cardOptions = {}) {
    if (!anchor || !cardDict || !cardDict.def_id) return;
    anchor.addEventListener('mouseenter', (event) => {
        if (window.matchMedia && window.matchMedia('(hover: none), (pointer: coarse)').matches) return;
        showFloatingCardPreview(cardDict, anchor, { x: event.clientX, y: event.clientY }, cardOptions);
    });
    anchor.addEventListener('mousemove', (event) => {
        if (floatingCardPreviewEl) positionFloatingCardPreview(anchor, { x: event.clientX, y: event.clientY });
    });
    anchor.addEventListener('mouseleave', removeFloatingCardPreview);
    anchor.addEventListener('touchstart', (event) => {
        if (!event.touches || !event.touches.length) return;
        const pos = getPointerPos(event);
        floatingCardPreviewTouchStart = pos;
        if (floatingCardPreviewTimer) clearTimeout(floatingCardPreviewTimer);
        floatingCardPreviewTimer = setTimeout(() => {
            showFloatingCardPreview(cardDict, anchor, pos, cardOptions);
        }, CARD_CHIP_PREVIEW_DELAY);
    }, { passive: true });
    anchor.addEventListener('touchmove', (event) => {
        const pos = getPointerPos(event);
        if (floatingCardPreviewEl) positionFloatingCardPreview(anchor, pos);
        if (floatingCardPreviewTouchStart) {
            const dist = Math.hypot(pos.x - floatingCardPreviewTouchStart.x, pos.y - floatingCardPreviewTouchStart.y);
            if (dist > CARD_HOLD_PREVIEW_HIDE_DISTANCE) removeFloatingCardPreview();
        }
    }, { passive: true });
    anchor.addEventListener('touchend', removeFloatingCardPreview, { passive: true });
    anchor.addEventListener('touchcancel', removeFloatingCardPreview, { passive: true });
}

const TERM_INTRO_DELAY = 600;
const TERM_INTRO_MOVE_CANCEL = 18;
let termIntroOverlayEl = null;
let termIntroCardGhostEl = null;

function getTermIntroLibrary() {
    const magicDamageDesc = '不能被护甲、圆盘、邪眼等减少。注意，不是“消耗魔力造成的伤害”。';
    return {
        card_type_thorn: { label: getCardTypeLabel('thorn') || 'Thorn', desc: '攻击牌。需要选择目标，主要用来压低对方 H；2v2 中也可以攻击队友。', color: CARD_TYPE_COLORS.thorn },
        card_type_bloom: { label: getCardTypeLabel('bloom') || 'Bloom', desc: '技能牌。用于回血、抽牌、加状态、调整 E/M 或改变场面。', color: CARD_TYPE_COLORS.bloom },
        card_type_root: { label: getCardTypeLabel('root') || 'Root', desc: '装备牌。有些过一回合后才能主动触发，有些能持续提供效果。', color: CARD_TYPE_COLORS.root },
        card_type_guard: { label: getCardTypeLabel('guard') || 'Guard', desc: '反制牌。仅对方行动弹出反制窗口时可使用，用来闪避、保护装备或减少伤害。', color: CARD_TYPE_COLORS.guard },
        D: { label: 'D：物理伤害(Damage)', desc: '会受护甲、装备、闪避和反制影响。只有实际造成伤害，才会触发淬毒、尖牙回血等效果。', color: COLORS.damage },
        electric_damage: { label: '电伤：电击伤害(Electric Damage)', desc: `一种类似于物理伤害的魔法伤害。${magicDamageDesc}`, color: COLORS.damage },
        magic_damage: { label: '魔法伤害(Magic Damage)', desc: magicDamageDesc, color: COLORS.magic },
        A: { label: 'A：护甲(Armor)', desc: '用于抵消 D；不会减少中毒、灼烧等状态造成的魔法伤害。', color: COLORS.armor_text },
        P: { label: 'P：中毒(Poison)', desc: '你的回合开始时，先受到等同当前 P 层数的魔法伤害；如果没有被击败，P 变为向下取整的一半，例如 10P→5P，5P→2P。', color: COLORS.poison },
        F: { label: 'F：灼烧(Fire)', desc: '你的回合开始时，受到等同当前 F 层数的魔法伤害。灼烧层数不会减少。回合进行到 20 回合及以上后，每回合开始时对所有玩家施加一层灼烧。', color: COLORS.fire },
        toxic: { label: `${UI.status_toxic || '淬毒'}(Toxic)`, desc: '造成实际 D 后，对目标施加与淬毒层数相同的 P 层数。伤害被完全挡住时不会触发。', color: '#6C3483' },
        hand_limit: { label: '手牌上限', desc: '你能保留在手中的最大牌数。抽牌、回手或创建牌时超过上限，就会发生爆牌。', color: COLORS.text_primary },
        overdraw: { label: '爆牌', desc: '手牌超过上限时，多出来的牌不能留在手中，会按规则被移出手牌。装备黄金叶等效果可以提高上限。', color: COLORS.damage },
        overcap: { label: '爆费', desc: 'E 或 M 回复超过上限时，超过部分直接丢失；提前规划资源可以避免浪费。', color: COLORS.elixir },
        deck: { label: '牌堆', desc: '未抽到的牌所在区域。抽牌通常从牌堆顶进入手牌；查看牌堆只能看到抽牌堆。', color: COLORS.text_primary },
        discard: { label: '弃牌堆', desc: '大多数打出后的牌会进入弃牌堆，之后会被重新洗回牌堆。', color: COLORS.text_secondary },
        exile_zone: { label: '放逐区', desc: '被放逐的牌离开正常循环，不会再被抽到。', color: '#7F8C8D' },
        response: { label: UI.counter || '反制', desc: '对方行动满足条件时会出现响应机会。反制能改变对方行动的结果。', color: CARD_TYPE_COLORS.guard },
        same_name_penalty: { label: '同名卡惩罚', desc: '同一回合重复使用同名卡会额外消耗 E；共生牌不受影响。', color: COLORS.elixir },
        revealed: { label: UI.tag_revealed || '被揭示', desc: '在手中时永久对对手展示。', color: '#E74C3C' },
        team_limited: { label: UI.tag_team_limited || '队伍限定', desc: '只会出现在一队至少 2 名玩家的模式；单人训练场可选，但没有实际意义。', color: '#607D3B' },
        team_unique: { label: UI.tag_team_unique || '队伍独一', desc: '同一队伍中若多人选择此牌，随机保留一张，多余的会被放逐。', color: '#8D6E63' },
        power: { label: UI.tag_power || '威力', desc: '此牌造成的每段 D 增加。若是多段 D，会按段数把威力向上分配。', color: '#C0392B' },
        magic_swift: { label: UI.tag_magic_swift || '魔力迅捷', desc: 'M 花费减少对应层数，最低为 0M。', color: '#6C5CE7' },
        fusion_layer: { label: UI.fusion_layer || '聚变', desc: '攻击牌的伤害会被放大。每次伤害按 向上取整(原始伤害×聚变/裂变) 计算。进弃牌堆后恢复为 1。', color: '#8E44AD' },
        fission_layer: { label: UI.fission_layer || '裂变', desc: '攻击牌会被拆成多次命中。每次伤害按 向上取整(原始伤害×聚变/裂变) 计算。进弃牌堆后恢复为 1。', color: '#2874A6' },
        tomato_layer: { label: UI.tomato_layer || '层数', desc: '番茄在手中每保留一回合增加层数，最多 6 层；打出后层数重置。', color: '#C0392B' },
        layers: { label: '层数', desc: '状态或特殊属性的数量。层数越高效果会越强，或持续越久。', color: COLORS.text_primary },
    };
}

function addTermIntroItem(items, seen, key, override = null) {
    if (!key || seen.has(key)) return;
    const library = getTermIntroLibrary();
    const item = override || library[key];
    if (!item) return;
    seen.add(key);
    items.push({
        key,
        label: item.label || key,
        desc: item.desc || item.description || '',
        color: item.color || COLORS.text_primary,
    });
}

function getIntroFlagDescription(flag, custom = null) {
    const normalized = normalizeCardFlag(flag);
    if (custom) return getRegistryText(custom, 'description', '') || '自定义标签。具体效果由对应模组或卡牌说明决定。';
    const desc = {
        precision: '攻击被闪避时不会完全失效，而是把实际伤害变为原来的一半，向上取整。',
        exile: '结算后进入放逐区，而不是弃牌堆；不会再被抽到。',
        non_stackable: '可以装备多张，但同类效果只算一份；一张被摧毁后，剩下的还能继续发挥作用。',
        indestructible: '作为装备时不会被摧毁效果破坏；玩家死亡时也不会被清除。',
        sprout: '抽到时会额外抽牌。手牌满时仍然会爆牌。',
        symbiosis: '同一回合重复使用同名卡时，不会受到同名卡费用惩罚。',
        attract: '爆牌时，会优先挤掉没有吸引的牌。',
        void: '回合结束仍留在手牌中时，会进入放逐区。',
        self_only: '打出时不选择目标；效果按这张牌自身规则结算。',
        uncancellable: '相关选择窗口不能取消，避免免费查看隐藏信息后退出选择。',
        infinite_exclude: '不会进入无限火力随机牌池。',
        rebound: '打出并结算后立即回到手中。',
        copy: '进入手中时，将层数张放逐复制加入手中。',
        unique: '整场对局自己总牌库中仅允许出现一张，多余的将被放逐。',
        swift: 'E花费减少X，最少为0。',
        magic_swift: 'M花费减少X，最少为0。',
        power: '此牌造成的每段D增加。多段D会按段数把威力向上分配。',
        team_limited: '只在一队至少2名玩家的模式出现；单人训练场可选，但没有实际意义。',
        team_unique: '同一队伍中若多人选择此牌，随机保留一张，多余的会被放逐。',
        stealth: '不会触发对手的响应窗口。',
        revealed: '在手中时永久对对手展示。',
        fusion_layer: getTermIntroLibrary().fusion_layer.desc,
        fission_layer: getTermIntroLibrary().fission_layer.desc,
    };
    return desc[normalized] || UI.tag_desc_default || '该标签的具体含义由对应卡牌或模组定义。';
}

function addFlagIntroItem(items, seen, flag) {
    const normalized = normalizeCardFlag(flag);
    if (!normalized || seen.has(`flag:${normalized}`)) return;
    const custom = getCustomTagDef(normalized);
    const label = custom ? getRegistryText(custom, 'name', normalized) : getFlagLabel(normalized);
    const desc = getIntroFlagDescription(normalized, custom);
    const style = CARD_FLAG_STYLES[normalized];
    const color = custom
        ? safeRegistryColor(custom.color, COLORS.text_primary)
        : CARD_FLAG_TERM_COLORS[normalized] || (style && (style.fg || style.color)) || COLORS.text_primary;
    addTermIntroItem(items, seen, `flag:${normalized}`, { label, desc: desc || UI.tag_desc_default || '该标签的具体含义由卡牌效果定义。', color });
}

function buildCardIntroSummaryHtml(cardDef) {
    if (!cardDef) return '';
    const triggerText = getCardIntroTriggerText(cardDef) || '';
    const descriptionText = getCardDescriptionText(cardDef) || '';
    if (!triggerText && !descriptionText) return '';
    return `
        <section class="term-intro-summary">
            ${descriptionText ? `<div class="term-intro-flavor">${colorizeCardText(descriptionText)}</div>` : ''}
            ${triggerText ? `<div class="term-intro-summary-block">
                <div class="term-intro-summary-label">触发</div>
                <div class="term-intro-summary-text">${colorizeCardText(triggerText)}</div>
            </div>` : ''}
        </section>
    `;
}

function buildCardIntroTermsHtml(cardDict) {
    if (cardDict && cardDict.__blind_for_self) {
        return `
            <section class="term-intro-summary">
                <div class="term-intro-flavor">?</div>
                <div class="term-intro-summary-block">
                    <div class="term-intro-summary-label">?</div>
                    <div class="term-intro-summary-text">?</div>
                </div>
            </section>
            ${renderTermIntroItems([{ key: 'blind_unknown', label: '?', desc: '?', color: COLORS.text_primary }])}
        `;
    }
    const cardDef = getCardDef((cardDict && cardDict.def_id) || '');
    return `${buildCardIntroSummaryHtml(cardDef)}${renderTermIntroItems(collectCardIntroTerms(cardDict))}`;
}

function collectCardIntroTerms(cardDict) {
    const cardDef = getCardDef((cardDict && cardDict.def_id) || '');
    const items = [];
    const seen = new Set();
    if (!cardDef) return items;
    addTermIntroItem(items, seen, `card_type_${cardDef.card_type || 'bloom'}`);
    const { flags } = getCardDisplayCosts(cardDict || {}, cardDef, getCardOwnerStateForPrediction(cardDict) || (gameState && gameState.you));
    flags.forEach(flag => {
        if (shouldDisplayCardFlag(flag)) addFlagIntroItem(items, seen, flag);
    });
    const rawText = [
        getCardName(cardDef),
        getCardEffectText(cardDef),
        getCardDescriptionText(cardDef),
        getCardTriggerText(cardDef),
        getCardIntroTriggerText(cardDef),
        cardDef.effect_text,
        cardDef.effect_text_cn,
        cardDef.effect_text_en,
        cardDef.trigger_effect_text,
        cardDef.trigger_effect_text_cn,
        cardDef.trigger_effect_text_en,
        cardDict && cardDict.effect_text,
        cardDict && cardDict.description,
        cardDict && cardDict.trigger_effect_text,
        (cardDef.flags || []).join(' '),
        (cardDef.tags || []).join(' '),
        (() => {
            try { return JSON.stringify(cardDef.v2_events || cardDef.events || {}); }
            catch (_) { return ''; }
        })(),
    ].filter(Boolean).join(' ');
    const probes = [
        [/(\d+\s*D|物理伤害|physical damage|D\b)/i, 'D'],
        [/(\+\s*\d+\s*A|护甲|armor|A\b)/i, 'A'],
        [/(\d+\s*(?:P|层P)|中毒|Poison)/i, 'P'],
        [/(\d+\s*(?:F|层F)|灼烧|Burn)/i, 'F'],
        [/(\d+\s*电伤|电击伤害|电伤|Electric Damage)/i, 'electric_damage'],
        [/(魔法伤害|Magic Damage)/i, 'magic_damage'],
        [/(淬毒|Toxic)/i, 'toxic'],
        [/(抽牌|牌堆|draw|deck)/i, 'deck'],
        [/(弃牌|discard)/i, 'discard'],
        [/(放逐|exile)/i, 'exile_zone'],
        [/(反制|counter|Guard)/i, 'response'],
        [/(爆牌|overflow)/i, 'overdraw'],
        [/(手牌上限|hand limit)/i, 'hand_limit'],
        [/(爆费|上限)/i, 'overcap'],
        [/(同名|共生|same-name)/i, 'same_name_penalty'],
        [/(被揭示|revealed)/i, 'revealed'],
    ];
    probes.forEach(([re, key]) => {
        if (re.test(rawText)) addTermIntroItem(items, seen, key);
    });
    const statusProbes = [
        [/易损|Fragile|jungle:fragile|fragile/i, 'jungle:fragile'],
        [/护盾|Shield|jungle:shield/i, 'jungle:shield'],
        [/魔力回合回复|Turn Magic Regen|jungle:turn_magic_turns|turn_magic/i, 'jungle:turn_magic_turns'],
        [/回合回复|Turn Heal|jungle:turn_heal_turns|turn_heal/i, 'jungle:turn_heal_turns'],
        [/树根|Root(?!牌| card)|jungle:root_status|root_status/i, 'jungle:root_status'],
        [/剧毒|Toxic Poison|jungle:toxic_poison|toxic_poison/i, 'jungle:toxic_poison'],
        [/滞留|Stagnation|stagnation/i, 'stagnation'],
        [/失明|Blind|blind/i, 'blind'],
        [/预知|Foresight|foresight/i, 'foresight'],
        [/破损|Fracture|fracture/i, 'fracture'],
        [/眩晕|Stun|stunned|skip_turn/i, 'stunned'],
        [/禁攻|禁止攻击|attack_blocked/i, 'attack_blocked'],
        [/仅攻击|attack_only/i, 'attack_only'],
        [/状态免疫|status_immune|\bimmune\b/i, 'status_immune'],
        [/流血|Bleed|bleed/i, 'bleed'],
        [/禁疗|Heal Block|heal_block/i, 'heal_block'],
        [/虚弱|Weakness|weakness/i, 'weakness'],
        [/超载|Overload|overload/i, 'overload'],
        [/迟缓|Sluggish|sluggish/i, 'sluggish'],
    ];
    statusProbes.forEach(([re, key]) => {
        if (!re.test(rawText) || seen.has(`status:${key}`)) return;
        const statusItem = getStatusIntroItem({ key });
        addTermIntroItem(items, seen, `status:${key}`, statusItem);
    });
    if (/(虚无|Void)/i.test(rawText)) addFlagIntroItem(items, seen, 'void');
    if (/(回转|Rebound)/i.test(rawText)) addFlagIntroItem(items, seen, 'rebound');
    const fusionLevel = Math.max(1, Number(cardDict && cardDict.fusion_level || 1));
    const fissionLevel = Math.max(1, Number(cardDict && cardDict.fission_level || 1));
    if (fusionLevel > 1 || cardDef.id === 'Fusion') addTermIntroItem(items, seen, 'fusion_layer');
    if (fissionLevel > 1 || cardDef.id === 'Fission') addTermIntroItem(items, seen, 'fission_layer');
    if (cardDef.id === 'Tomato') addTermIntroItem(items, seen, 'tomato_layer');
    if (!items.some(item => item.key === 'D') && cardDef.card_type === 'thorn') addTermIntroItem(items, seen, 'D');
    if (seen.has('P') || seen.has('F')) addTermIntroItem(items, seen, 'magic_damage');
    return items;
}

function getStatusIntroItem(statusInfo) {
    const key = statusInfo && statusInfo.key;
    const customDef = (statusInfo && statusInfo.customDef) || getCustomStatusDef(key);
    if (customDef) {
        return {
            label: getRegistryText(customDef, 'name', key),
            desc: getRegistryText(customDef, 'description', '由模组定义的自定义状态。'),
            color: safeRegistryColor(customDef.color, statusInfo.fg || COLORS.text_primary),
        };
    }
    const builtIns = {
        poison: { label: UI.status_poison, desc: getTermIntroLibrary().P.desc, color: COLORS.poison },
        fire: { label: UI.status_fire, desc: getTermIntroLibrary().F.desc, color: COLORS.fire },
        toxic: { label: UI.status_toxic, desc: getTermIntroLibrary().toxic.desc, color: '#6C3483' },
        vulnerable: { label: '易伤', desc: '受到的物理伤害增加50%。', color: COLORS.damage },
        triangle: { label: UI.status_triangle, desc: '每层会提高三角形的后续伤害，上限 4 层；裂变三角形时，每一段都会按当时层数重新计算。', color: COLORS.non_stack },
        nazar: { label: UI.status_nazar, desc: '受到较小 D 时回复生命；达到条件后会消耗层数。', color: COLORS.magic },
        equip_protect: { label: UI.status_equip_protect, desc: '保护装备不被摧毁效果破坏，常用于应对污水这类摧毁装备的牌。', color: COLORS.indestructible },
        invincible: { label: UI.status_invincible, desc: '无敌期间不会因受到伤害而失败。', color: COLORS.elixir },
        status_immune: { label: UI.status_immune || '状态免疫', desc: '效果存在时，部分负面状态不会生效。', color: '#16A085' },
        immune: { label: UI.status_immune || '状态免疫', desc: '效果存在时，部分负面状态不会生效。', color: '#16A085' },
        stunned: { label: UI.status_stunned, desc: '轮到自己回合时，层数减1，跳过一回合主动行动，但装备的被动效果正常。', color: COLORS.damage },
        attack_blocked: { label: UI.status_attack_blocked, desc: '不能打出攻击牌，直到层数或持续时间结束。', color: COLORS.damage },
        attack_only: { label: UI.status_attack_only, desc: '只能打出攻击牌，直到层数或持续时间结束。', color: '#D35400' },
        untargetable: { label: UI.status_untargetable, desc: '不能被部分选择目标的效果指定。', color: '#1A5276' },
        bandage: { label: UI.status_bandage, desc: '绷带的保护，若状态存在，玩家死亡时会先无敌一回合，下回合死亡。', color: '#1E8449' },
        sponge: { label: UI.status_sponge, desc: '表示海绵的存在。', color: '#6C3483' },
        sluggish: { label: UI.status_sluggish, desc: '每回合少抽层数张牌。', color: '#E67E22' },
        overload: { label: UI.status_overload, desc: '回合开始时扣除对应层数E，到0为止，然后清除全部层数。', color: '#C0392B' },
        foresight: { label: UI.status_foresight, desc: '回合开始抽牌时，可以选择最多层数张手牌丢弃，然后抽对应张牌。', color: '#2980B9' },
        fracture: { label: UI.status_fracture, desc: '每打出一张牌减少与层数相同的H，自己回合结束清除。', color: '#7F8C8D' },
        stagnation: { label: UI.status_stagnation, desc: '回合开始时，中毒仍会造成伤害，但结算后 P 层数不会减半。自己回合结束时滞留层数-1。', color: '#9B59B6' },
        blind: { label: UI.status_blind, desc: '1层：自己手牌和反制窗口卡只显示类型；2层：战斗日志变灰，自己H/E/M显示为问号，牌连类型也隐藏，并隐藏反制伤害预测；3层及以上：其他玩家H/E/M、自己的牌堆数量和大多数可见数值显示为问号，他人手牌区不显示卡牌，只显示问号。自己回合开始时手牌会被打乱，然后清空失明。', color: '#2C3E50' },
        'jungle:fragile': { label: '易损', desc: '护甲降低对应层数；若护甲被降到负数，会让受到的物理伤害增加。自己回合开始时清除。', color: '#8E5A2A' },
        fragile: { label: '易损', desc: '护甲降低对应层数；若护甲被降到负数，会让受到的物理伤害增加。自己回合开始时清除。', color: '#8E5A2A' },
        'jungle:shield': { label: '护盾', desc: '受到伤害时先消耗护盾层数抵扣等量伤害，包括魔法伤害。自己回合开始时层数减半。', color: '#2E7D7D' },
        shield: { label: '护盾', desc: '受到伤害时先消耗护盾层数抵扣等量伤害，包括魔法伤害。自己回合开始时层数减半。', color: '#2E7D7D' },
        'jungle:turn_heal_turns': { label: '回合回复', desc: '写作“回合回复:X;Y”。出现和回合开始时回复Y点H，然后X减少1；X为0时消失。', color: '#F48FB1' },
        turn_heal: { label: '回合回复', desc: '写作“回合回复:X;Y”。出现和回合开始时回复Y点H，然后X减少1；X为0时消失。', color: '#F48FB1' },
        'jungle:turn_magic_turns': { label: '魔力回合回复', desc: '写作“魔力回合回复:X;Y”。出现和回合开始时回复Y点M，然后X减少1；X为0时消失。', color: '#6C5CE7' },
        turn_magic: { label: '魔力回合回复', desc: '写作“魔力回合回复:X;Y”。出现和回合开始时回复Y点M，然后X减少1；X为0时消失。', color: '#6C5CE7' },
        'jungle:root_status': { label: '树根', desc: '增加护甲；受到物理伤害时减少1层。产生它的树根装备离场时，会清除对应树根。', color: '#6E8B3D' },
        root_status: { label: '树根', desc: '增加护甲；受到物理伤害时减少1层。产生它的树根装备离场时，会清除对应树根。', color: '#6E8B3D' },
        'jungle:toxic_poison': { label: '剧毒', desc: '中毒结算后，额外施加对应层数的中毒。', color: '#5E8C31' },
        toxic_poison: { label: '剧毒', desc: '中毒结算后，额外施加对应层数的中毒。', color: '#5E8C31' },
        heal_block: { label: UI.status_heal_block, desc: '生命回复效果降低50%×层数（上限降低100%），自己回合结束时层数-1。', color: '#E84393' },
        weakness: { label: UI.status_weakness, desc: '自己对别人造成的物理伤害降低20%×层数（上限降低60%），自己回合结束时层数-1。', color: '#8E44AD' },
        bleed: { label: UI.status_bleed, desc: '打出攻击牌时受到层数点物理伤害，回合结束时层数下取整减半。', color: '#922B21' },
        fragment: { label: UI.status_fragment, desc: '获得碎片层数；达到4层时可消耗4层将雷神之锤加入手中。', color: '#795548' },
    };
    return builtIns[key] || {
        label: (statusInfo && statusInfo.name) || key || '状态',
        desc: '状态会暂时改变玩家的资源、行动或受伤规则。具体效果由卡牌定义。',
        color: (statusInfo && statusInfo.fg) || COLORS.text_primary,
    };
}

function getStatusDisplayText(statusInfo) {
    const item = getStatusIntroItem(statusInfo || {});
    const value = statusInfo && statusInfo.val != null && String(statusInfo.val) !== '' ? String(statusInfo.val) : '';
    return value ? `${item.label}:${value}` : item.label;
}

function ensureTermIntroOverlay() {
    if (termIntroOverlayEl) return termIntroOverlayEl;
    const overlay = document.createElement('div');
    overlay.id = 'term-intro-overlay';
    overlay.className = 'term-intro-overlay hidden';
    overlay.setAttribute('aria-hidden', 'true');
    overlay.innerHTML = `
        <div class="term-intro-dialog" role="dialog" aria-modal="true">
            <button id="term-intro-close" class="term-intro-close" type="button" aria-label="关闭">×</button>
            <div id="term-intro-card" class="term-intro-card-wrap"></div>
            <section class="term-intro-panel">
                <div id="term-intro-title" class="term-intro-title">术语说明</div>
                <div id="term-intro-list" class="term-intro-list"></div>
            </section>
        </div>
    `;
    document.body.appendChild(overlay);
    overlay.querySelector('#term-intro-close')?.addEventListener('click', hideTermIntroOverlay);
    overlay.addEventListener('click', (event) => {
        if (event.target === overlay) hideTermIntroOverlay();
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && !overlay.classList.contains('hidden')) hideTermIntroOverlay();
    });
    termIntroOverlayEl = overlay;
    return overlay;
}

function hideTermIntroOverlay() {
    if (!termIntroOverlayEl) return;
    removeTermIntroCardGhost();
    termIntroOverlayEl.classList.remove('visible');
    termIntroOverlayEl.classList.remove('card-flying');
    termIntroOverlayEl.classList.add('hidden');
    termIntroOverlayEl.setAttribute('aria-hidden', 'true');
}

function removeTermIntroCardGhost() {
    if (termIntroCardGhostEl) {
        termIntroCardGhostEl.remove();
        termIntroCardGhostEl = null;
    }
}

function cloneDomRect(rect) {
    if (!rect) return null;
    return {
        left: rect.left,
        top: rect.top,
        width: rect.width,
        height: rect.height,
    };
}

function isUsableRect(rect) {
    return rect
        && Number.isFinite(rect.left)
        && Number.isFinite(rect.top)
        && rect.width > 8
        && rect.height > 8;
}

function getTermIntroSourceRect(anchor) {
    const isChip = !!(anchor && anchor.classList && anchor.classList.contains('choice-card-token'));
    if (isChip && floatingCardPreviewEl) {
        const previewCard = floatingCardPreviewEl.querySelector('.floating-card-preview-card') || floatingCardPreviewEl;
        const previewRect = cloneDomRect(previewCard.getBoundingClientRect());
        if (isUsableRect(previewRect)) return previewRect;
    }
    if (!anchor || typeof anchor.getBoundingClientRect !== 'function') return null;
    const rect = cloneDomRect(anchor.getBoundingClientRect());
    return isUsableRect(rect) ? rect : null;
}

function animateTermIntroCardFromSource(cardEl, sourceRect, overlay) {
    if (!cardEl || !isUsableRect(sourceRect)) {
        if (cardEl) cardEl.classList.remove('term-intro-card-hidden');
        if (overlay) overlay.classList.remove('card-flying');
        return;
    }
    const targetRect = cloneDomRect(cardEl.getBoundingClientRect());
    if (!isUsableRect(targetRect)) {
        cardEl.classList.remove('term-intro-card-hidden');
        if (overlay) overlay.classList.remove('card-flying');
        return;
    }
    if (!cardEl.animate) {
        cardEl.classList.remove('term-intro-card-hidden');
        if (overlay) overlay.classList.remove('card-flying');
        return;
    }
    removeTermIntroCardGhost();
    const startX = sourceRect.left - targetRect.left;
    const startY = sourceRect.top - targetRect.top;
    const startScaleX = sourceRect.width / targetRect.width;
    const startScaleY = sourceRect.height / targetRect.height;
    const startTransform = `translate(${startX}px, ${startY}px) scale(${startScaleX}, ${startScaleY})`;
    const ghost = cardEl.cloneNode(true);
    ghost.classList.add('term-intro-card-ghost');
    ghost.classList.remove('term-intro-card-hidden');
    ghost.style.left = `${targetRect.left}px`;
    ghost.style.top = `${targetRect.top}px`;
    ghost.style.width = `${targetRect.width}px`;
    ghost.style.height = `${targetRect.height}px`;
    ghost.style.transform = startTransform;
    ghost.style.opacity = '0.92';
    document.body.appendChild(ghost);
    termIntroCardGhostEl = ghost;
    cardEl.classList.add('term-intro-card-hidden');
    let finished = false;
    const finish = () => {
        if (finished) return;
        finished = true;
        cardEl.classList.remove('term-intro-card-hidden');
        requestAnimationFrame(() => {
            if (termIntroCardGhostEl === ghost) removeTermIntroCardGhost();
            else ghost.remove();
        });
        if (overlay) overlay.classList.remove('card-flying');
    };
    const animation = ghost.animate([
        {
            transform: startTransform,
            opacity: 0.92,
            filter: 'drop-shadow(0 12px 26px rgba(0, 0, 0, 0.24))',
        },
        {
            transform: 'translate(0, 0) scale(1)',
            opacity: 1,
            filter: 'drop-shadow(0 20px 38px rgba(0, 0, 0, 0.28))',
        },
    ], {
        duration: 320,
        easing: 'cubic-bezier(.18,.82,.22,1)',
        fill: 'forwards',
    });
    animation.addEventListener('finish', finish, { once: true });
    animation.addEventListener('cancel', finish, { once: true });
    setTimeout(finish, 460);
}

function renderTermIntroItems(items) {
    if (!items || !items.length) {
        return '<div class="term-intro-empty">这张牌没有需要额外说明的术语。</div>';
    }
    return items.map(item => `
        <article class="term-intro-item" style="--term-color:${escapeHtml(item.color || COLORS.text_primary)}">
            <div class="term-intro-item-title">${escapeHtml(item.label)}</div>
            <div class="term-intro-item-desc">${escapeHtml(item.desc || '')}</div>
        </article>
    `).join('');
}

function showTermIntroForCard(cardDict, cardOptions = {}) {
    const cardDef = getCardDef((cardDict && cardDict.def_id) || '');
    if (!cardDef) return;
    const blinded = shouldBlindCardForSelf(cardDict, cardOptions);
    const introCardDict = blinded ? { ...cardDict, __blind_for_self: true } : cardDict;
    const sourceRect = cardOptions.sourceRect || null;
    removeFloatingCardPreview();
    removeCardHoldPreview();
    if (typeof cleanupDragState === 'function') cleanupDragState();
    const overlay = ensureTermIntroOverlay();
    const cardSlot = overlay.querySelector('#term-intro-card');
    const title = overlay.querySelector('#term-intro-title');
    const list = overlay.querySelector('#term-intro-list');
    cardSlot.innerHTML = '';
    const card = createCardElement(introCardDict, {
        showAllFlags: true,
        disableIntro: true,
        blindForSelf: blinded,
        ownerState: cardOptions.ownerState || getCardOwnerStateForPrediction(cardDict) || (gameState && gameState.you),
        prediction: cardOptions.prediction || getCardPredictionOptionsForOwner(cardDict, cardOptions.ownerState),
    });
    card.classList.add('term-intro-card');
    if (isUsableRect(sourceRect)) card.classList.add('term-intro-card-hidden');
    cardSlot.appendChild(card);
    title.textContent = blinded ? '? · ?' : `${getCardName(cardDef)} · 术语说明`;
    list.innerHTML = buildCardIntroTermsHtml(introCardDict);
    bindInlineCardChips(list);
    overlay.classList.remove('visible');
    overlay.classList.toggle('card-flying', isUsableRect(sourceRect));
    overlay.classList.remove('hidden');
    overlay.setAttribute('aria-hidden', 'false');
    requestAnimationFrame(() => {
        overlay.classList.add('visible');
        requestAnimationFrame(() => animateTermIntroCardFromSource(card, sourceRect, overlay));
    });
}

function showTermIntroForStatus(statusInfo) {
    const overlay = ensureTermIntroOverlay();
    removeFloatingCardPreview();
    removeCardHoldPreview();
    overlay.classList.remove('visible');
    overlay.classList.remove('card-flying');
    const item = getStatusIntroItem(statusInfo || {});
    const cardSlot = overlay.querySelector('#term-intro-card');
    const title = overlay.querySelector('#term-intro-title');
    const list = overlay.querySelector('#term-intro-list');
    const displayText = getStatusDisplayText(statusInfo || {});
    cardSlot.innerHTML = `
        <div class="term-intro-status-card" style="--term-color:${escapeHtml(item.color || COLORS.text_primary)}">
            <span class="status-tag term-intro-status-tag" style="color:${escapeHtml(statusInfo?.fg || item.color || COLORS.text_primary)};background:${escapeHtml(statusInfo?.bg || COLORS.bg_card || '#fff')};border-color:${escapeHtml(statusInfo?.fg || item.color || COLORS.text_primary)}">${escapeHtml(displayText)}</span>
        </div>
    `;
    title.textContent = `${displayText} · 状态说明`;
    const terms = [item];
    if (statusInfo && statusInfo.val) {
        terms.push(getTermIntroLibrary().layers);
    }
    if (['poison', 'fire'].includes(statusInfo && statusInfo.key)) {
        terms.push(getTermIntroLibrary().magic_damage);
    }
    if (statusInfo && statusInfo.key === 'toxic') {
        terms.push(getTermIntroLibrary().P);
    }
    list.innerHTML = renderTermIntroItems(terms);
    overlay.classList.remove('hidden');
    overlay.setAttribute('aria-hidden', 'false');
    requestAnimationFrame(() => overlay.classList.add('visible'));
}

function attachTermIntroLongPress(anchor, onShow) {
    if (!anchor || anchor.dataset.termIntroBound === '1') return;
    anchor.dataset.termIntroBound = '1';
    let timer = null;
    let start = null;
    let docMove = null;
    let docEnd = null;
    const cancel = () => {
        if (timer) clearTimeout(timer);
        timer = null;
        start = null;
        if (docMove) document.removeEventListener('pointermove', docMove);
        if (docEnd) {
            document.removeEventListener('pointerup', docEnd);
            document.removeEventListener('pointercancel', docEnd);
        }
        docMove = null;
        docEnd = null;
    };
    anchor.addEventListener('pointerdown', (event) => {
        if (event.button != null && event.button !== 0) return;
        start = { x: event.clientX, y: event.clientY };
        if (timer) clearTimeout(timer);
        docMove = (moveEvent) => {
            if (!timer || !start) return;
            const dist = Math.hypot(moveEvent.clientX - start.x, moveEvent.clientY - start.y);
            if (dist > TERM_INTRO_MOVE_CANCEL) cancel();
        };
        docEnd = cancel;
        document.addEventListener('pointermove', docMove);
        document.addEventListener('pointerup', docEnd);
        document.addEventListener('pointercancel', docEnd);
        timer = setTimeout(() => {
            timer = null;
            if (docMove) document.removeEventListener('pointermove', docMove);
            if (docEnd) {
                document.removeEventListener('pointerup', docEnd);
                document.removeEventListener('pointercancel', docEnd);
            }
            docMove = null;
            docEnd = null;
            onShow();
        }, TERM_INTRO_DELAY);
    });
    anchor.addEventListener('pointermove', (event) => {
        if (!timer || !start) return;
        const dist = Math.hypot(event.clientX - start.x, event.clientY - start.y);
        if (dist > TERM_INTRO_MOVE_CANCEL) cancel();
    });
    ['pointerup', 'pointerleave', 'pointercancel', 'lostpointercapture'].forEach(type => {
        anchor.addEventListener(type, cancel);
    });
}

function attachTermIntroToCard(anchor, cardDict, cardOptions = {}) {
    if (!anchor || !cardDict || !cardDict.def_id) return;
    attachTermIntroLongPress(anchor, () => {
        showTermIntroForCard(cardDict, {
            ...cardOptions,
            sourceRect: getTermIntroSourceRect(anchor),
        });
    });
}

function attachTermIntroToStatus(anchor, statusInfo) {
    if (!anchor || !statusInfo) return;
    if (getOwnBlindLevel() >= 3) return;
    attachTermIntroLongPress(anchor, () => showTermIntroForStatus(statusInfo));
}

function renderChoiceOptionContent(container, option, index, config = {}) {
    container.innerHTML = '';
    if (config.numbered) {
        const idx = document.createElement('span');
        idx.className = 'choice-option-index';
        idx.textContent = `${index + 1}.`;
        container.appendChild(idx);
    }
    if (option && typeof option === 'object' && option.kind === 'card') {
        container.appendChild(createCardChoiceChip(option.card, option));
    } else if (option && typeof option === 'object' && option.kind === 'card-combo') {
        const wrap = document.createElement('span');
        wrap.className = 'choice-card-combo';
        (option.cards || []).forEach((card, i) => {
            if (i > 0) {
                const sep = document.createElement('span');
                sep.className = 'choice-card-separator';
                sep.textContent = '+';
                wrap.appendChild(sep);
            }
            wrap.appendChild(createCardChoiceChip(card, option));
        });
        container.appendChild(wrap);
    } else {
        const text = document.createElement('span');
        text.className = 'choice-option-text';
        text.textContent = String(option && typeof option === 'object' && option.text != null ? option.text : (option == null ? '' : option));
        container.appendChild(text);
    }
    if (option && typeof option === 'object' && option.detail) {
        const detail = document.createElement('span');
        detail.className = 'choice-option-detail';
        detail.textContent = option.detail;
        container.appendChild(detail);
    }
}

let dragState = null;
const CARD_HOLD_PREVIEW_DELAY = 430;
const CARD_CHIP_PREVIEW_DELAY = 360;
const CARD_HOLD_PREVIEW_HIDE_DISTANCE = 28;

function getPointerPos(e) {
    if (e.touches && e.touches.length > 0) {
        return { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }
    if (e.changedTouches && e.changedTouches.length > 0) {
        return { x: e.changedTouches[0].clientX, y: e.changedTouches[0].clientY };
    }
    return { x: e.clientX, y: e.clientY };
}

function isMinimalUiStyle() {
    return document.documentElement.getAttribute('data-ui-style') === 'minimal';
}

function isClassicBattleUiStyle() {
    return document.documentElement.getAttribute('data-ui-style') === 'classic';
}

function removeCardHoldPreview() {
    if (!dragState) return;
    if (dragState.previewTimer) {
        clearTimeout(dragState.previewTimer);
        dragState.previewTimer = null;
    }
    if (dragState.previewEl) {
        dragState.previewEl.remove();
        dragState.previewEl = null;
    }
}

function updateCardHoldPreview(pos) {
    if (!dragState || !dragState.previewEl || !pos) return;
    const el = dragState.previewEl;
    const anchor = dragState.ghost || dragState.originalCard;
    const rect = anchor ? anchor.getBoundingClientRect() : null;
    const gap = Math.max(28, rect ? rect.width * 0.28 : 28);
    const width = el.offsetWidth || 240;
    const height = el.offsetHeight || 120;
    let left = rect ? rect.right + gap : pos.x + gap;
    if (left + width > window.innerWidth - 8) {
        left = rect ? rect.left - width - gap : pos.x - width - gap;
    }
    let top = rect ? (rect.top + rect.height * 0.5 - height * 0.5) : pos.y - height * 0.5;
    left = Math.max(8, Math.min(window.innerWidth - width - 8, left));
    top = Math.max(8, Math.min(window.innerHeight - height - 8, top));
    el.style.left = `${left}px`;
    el.style.top = `${top}px`;
}

function buildCardHoldPreviewHtml(cardDef, blinded = false) {
    if (!cardDef) return '';
    if (blinded) {
        return `
            <div class="card-hold-preview-title">?</div>
            <div class="card-hold-preview-effect">?</div>
            <div class="card-hold-preview-desc">?</div>
        `;
    }
    const effectText = getCardEffectText(cardDef) || '';
    const descriptionText = getCardDescriptionText(cardDef) || '';
    return `
        <div class="card-hold-preview-title">${escapeHtml(getCardName(cardDef))}</div>
        ${effectText ? `<div class="card-hold-preview-effect">${colorizeCardText(effectText)}</div>` : ''}
        ${descriptionText ? `<div class="card-hold-preview-desc">${colorizeCardText(descriptionText)}</div>` : ''}
    `;
}

function showCardHoldPreview(cardEl, pos) {
    if (!dragState || dragState.previewEl || !isMinimalUiStyle() || dragState.moved) return;
    const cardDef = getCardDef(cardEl.dataset.defId || '');
    if (!cardDef) return;
    const hand = (gameState && gameState.you && gameState.you.hand) || [];
    const instanceId = cardEl.dataset.instanceId;
    const cardDict = hand.find(card => String(card.instance_id) === String(instanceId)) || { def_id: cardEl.dataset.defId };
    const blindLevel = getCardBlindLevelForSelf(cardDict);
    const blinded = blindLevel > 0;
    const typeColor = getCardBlindDisplayColor(cardDef, blindLevel);
    const preview = document.createElement('div');
    preview.className = 'card-hold-preview';
    if (blinded) preview.classList.add('card-hold-preview-blinded');
    preview.style.setProperty('--preview-color', typeColor);
    preview.innerHTML = buildCardHoldPreviewHtml(cardDef, blinded);
    bindInlineCardChips(preview);
    document.body.appendChild(preview);
    dragState.previewEl = preview;
    dragState.previewShown = true;
    hideDropOverlay();
    updateCardHoldPreview(pos);
    requestAnimationFrame(() => preview.classList.add('active'));
}

function startCardDrag(e, cardEl) {
    if (isSpectating) return;
    if (isCardAnimationLocked()) return;
    cleanupDragState();
    e.preventDefault();
    const pos = getPointerPos(e);
    const instanceId = cardEl.dataset.instanceId;
    if (!instanceId) return;
    const rect = cardEl.getBoundingClientRect();
    const ghost = cardEl.cloneNode(true);
    ghost.classList.add('drag-ghost');
    ghost.style.position = 'fixed';
    ghost.style.width = rect.width + 'px';
    ghost.style.pointerEvents = 'none';
    ghost.style.zIndex = '9999';
    ghost.style.opacity = '0.8';
    ghost.style.left = (pos.x - rect.width / 2) + 'px';
    ghost.style.top = (pos.y - rect.height / 2) + 'px';
    document.body.appendChild(ghost);
    cardEl.style.opacity = '0.3';
    dragState = {
        instanceId,
        ghost,
        originalCard: cardEl,
        offsetX: rect.width / 2,
        offsetY: rect.height / 2,
        startX: pos.x,
        startY: pos.y,
        lastX: pos.x,
        lastY: pos.y,
        moved: false,
        previewTimer: null,
        previewEl: null,
        previewShown: false,
        touch: !!(e.touches && e.touches.length)
    };
    showDropOverlay();
}

function onDocumentPointerMove(e) {
    if (!dragState) return;
    e.preventDefault();
    const pos = getPointerPos(e);
    const dx = Math.abs(pos.x - dragState.startX);
    const dy = Math.abs(pos.y - dragState.startY);
    dragState.lastX = pos.x;
    dragState.lastY = pos.y;
    const distance = Math.hypot(dx, dy);
    if (dx > 8 || dy > 8) {
        dragState.moved = true;
        if (dragState.previewTimer) {
            clearTimeout(dragState.previewTimer);
            dragState.previewTimer = null;
        }
    }
    if (dragState.previewEl) {
        updateCardHoldPreview(pos);
        if (distance > CARD_HOLD_PREVIEW_HIDE_DISTANCE) {
            removeCardHoldPreview();
            showDropOverlay();
        }
    }
    dragState.ghost.style.left = (pos.x - dragState.offsetX) + 'px';
    dragState.ghost.style.top = (pos.y - dragState.offsetY) + 'px';
    const overlay = $('card-drop-overlay');
    if (overlay) {
        updateDropOverlayContent(overlay);
        overlay.classList.toggle('drag-over', pointInDropArea(pos));
    }
}

function cleanupDragState() {
    document.querySelectorAll('.drag-ghost').forEach(el => el.remove());
    document.querySelectorAll('.card.dragging').forEach(el => el.classList.remove('dragging'));
    removeCardHoldPreview();
    if (dragState) {
        if (dragState.originalCard) dragState.originalCard.style.opacity = '';
    }
    const playZone = document.getElementById('play-zone');
    if (playZone) playZone.classList.remove('drag-over');
    hideDropOverlay();
    dragState = null;
}

function onDocumentPointerUp(e) {
    if (!dragState) return;
    const pos = getPointerPos(e);
    const wasTap = dragState.touch && !dragState.moved;
    const previewWasShown = !!dragState.previewShown;
    const shouldPlay = pointInDropArea(pos);
    const instanceId = dragState.instanceId;
    cleanupDragState();
    if (wasTap && !previewWasShown) {
        selectPlayCardForConfirm(parseInt(instanceId));
    } else if (shouldPlay) {
        onPlayCard(parseInt(instanceId), { dragDrop: true, confirmed: true });
    }
}

function onDocumentTouchCancel(e) {
    cleanupDragState();
}

document.addEventListener('mousemove', onDocumentPointerMove);
document.addEventListener('mouseup', onDocumentPointerUp);
document.addEventListener('touchmove', onDocumentPointerMove, { passive: false });
document.addEventListener('touchend', onDocumentPointerUp);
document.addEventListener('touchcancel', onDocumentTouchCancel);

function canonicalServerKey(value) {
    return String(value || '')
        .trim()
        .replace(/\/+$/, '')
        .replace(/^https?:\/\//i, '')
        .toLowerCase();
}

function normalizeServerUrl(value) {
    let url = String(value || DEFAULT_SERVER).trim() || DEFAULT_SERVER;
    if (!/^https?:\/\//i.test(url)) {
        const bare = url.replace(/\/+$/, '');
        const isLocal = /^(localhost|127\.0\.0\.1)(:\d+)?$/i.test(bare);
        const isIpv4 = /^\d{1,3}(?:\.\d{1,3}){3}(:\d+)?$/.test(bare);
        const hasExplicitPort = /^[^/]+:\d+$/.test(bare);
        url = `${isLocal || isIpv4 || hasExplicitPort ? 'http' : 'https'}://${url}`;
    }
    return url.replace(/\/+$/, '');
}

function stopLatencyMonitor() {
    if (latencyPingTimer) {
        clearInterval(latencyPingTimer);
        latencyPingTimer = null;
    }
}

function sendLatencyPing() {
    if (!socket || !socket.connected || typeof performance === 'undefined') return;
    try {
        socket.emit('latency_ping', {
            t: performance.now(),
            transport: socket.io && socket.io.engine && socket.io.engine.transport ? socket.io.engine.transport.name : '',
        });
    } catch (e) {
        debugLog('[client] latency ping failed', e);
    }
}

function startLatencyMonitor() {
    stopLatencyMonitor();
    sendLatencyPing();
    latencyPingTimer = setInterval(sendLatencyPing, 10000);
}

function emitSocketLogin() {
    if (!socket || !socket.connected) return false;
    const preferredMode = localStorage.getItem('preferred_mode') || '1v1';
    socket.emit('login', {
        nickname: loginCredential || nickname,
        mode: preferredMode,
        account_login: !!currentAccount,
        beta_mode: GTN_BETA_MODE,
        skin: getCurrentSkinConfig(),
        ...getModLoginPayload(),
    });
    return true;
}

function bindSocketEvent(eventName, handler) {
    if (!socket) return;
    try {
        socket.off(eventName);
    } catch (_) {}
    socket.on(eventName, handler);
}

function connectSocket(serverUrl) {
    stopLocalSoloRuntime();
    let url = normalizeServerUrl(serverUrl);
    const readyState = socket && socket.io ? socket.io._readyState : '';
    const sameEndpoint = socket && socketConnectUrl === url;
    if (sameEndpoint && socket.connected) {
        debugLog('[client] socket reuse connected id=', socket.id, 'url=', url);
        emitSocketLogin();
        return;
    }
    if (sameEndpoint && (readyState === 'opening' || readyState === 'open')) {
        debugLog('[client] socket reuse connecting id=', socket.id, 'url=', url, 'state=', readyState);
        return;
    }
    stopLatencyMonitor();
    if (socket) {
        manualDisconnect = true;
        try {
            socket.removeAllListeners();
        } catch (_) {}
        socket.disconnect();
        socket = null;
    }
    manualDisconnect = false;
    let opts = {
        transports: ['websocket', 'polling'],
        timeout: SOCKET_CONNECT_TIMEOUT_MS,
        reconnectionAttempts: 5,
        reconnectionDelay: 400,
        reconnectionDelayMax: 1600,
        withCredentials: true,
    };
    socket = io(url, opts);
    window.gtnSocket = socket;
    socketConnectUrl = url;
    socketCreateSeq += 1;
    debugLog('[client] socket created #', socketCreateSeq, 'url=', url);

    bindSocketEvent('connect', () => {
        debugLog('[client] socket connected id=', socket.id, 'login nickname=', nickname);
        startLatencyMonitor();
        emitSocketLogin();
    });
    bindSocketEvent('disconnect', () => {
        debugLog('[client] socket disconnected');
        stopLatencyMonitor();
        if (manualDisconnect || phase === 'login') {
            manualDisconnect = false;
            return;
        }
        flashStatus(UI.disconnected, 3000, 'error');
        phase = 'connecting';
    });
    bindSocketEvent('connect_error', (err) => {
        debugLog('[client] socket connect_error', err && err.message ? err.message : err);
        if (phase === 'connecting') {
            flashStatus(UI.server_no_response, 3000, 'error');
        }
    });
    bindSocketEvent('kicked', (data = {}) => {
        const reason = data.reason || UI.disconnected || 'Disconnected';
        debugLog('[client] kicked:', reason);
        flashStatus(translateServerMessage(reason), 5000, 'error');
    });
    bindSocketEvent('latency_pong', (data = {}) => {
        if (typeof performance === 'undefined' || data.t == null) return;
        const rtt = Math.max(0, performance.now() - Number(data.t));
        if (!Number.isFinite(rtt)) return;
        socket.emit('latency_report', {
            rtt_ms: Math.round(rtt * 10) / 10,
            transport: socket.io && socket.io.engine && socket.io.engine.transport ? socket.io.engine.transport.name : '',
        });
    });
    bindSocketEvent('skin_look_update', (data = {}) => {
        const pid = normalizePlayerId(data.player_id);
        if (pid == null) return;
        if (!isSpectating && pid === normalizePlayerId(playerId)) return;
        const look = normalizeSkinLook(data.look || data);
        skinLookByPlayerId.set(pid, look);
        applySkinLookToRenderedAvatars(pid, look);
    });
    bindSocketEvent('login_ok', (data) => {
        debugLog('[client] login ok: sid=', data.sid, 'nickname=', data.nickname);
        mySid = data.sid || '';
        nickname = data.nickname || nickname;
        if (data.authenticated) {
            currentAccount = data.user || currentAccount;
            loginCredential = '';
            renderAccountState();
        } else if (!data.is_special_player && !data.is_admin_player) {
            loginCredential = nickname;
            if (data.skin) saveLocalSkinConfig(data.skin);
        }
        const nickInput = $('input-nickname');
        if (nickInput) nickInput.value = nickname;
        localStorage.setItem('gtn_nickname', nickname);
        if (pendingTutorialStart) {
            pendingTutorialStart = false;
            emitTutorialStart();
            return;
        }
        if (pendingSoloStart) {
            pendingSoloStart = false;
            emitSoloStart();
            return;
        }
        if (data.status === 'reconnecting') {
            phase = 'reconnecting';
            updateStatus(UI.reconnecting || UI.reconnect_title || 'Reconnecting...');
            return;
        }
        phase = 'lobby';
        updateStatus(UI.lobby_status.replace('{0}', nickname));
    });
    bindSocketEvent('login_fail', (data) => {
        showView('view-login');
        const err = $('login-error');
        if (err) err.textContent = moderationMessageFromPayload(data, translateLoginReason(data.reason));
    });
    bindSocketEvent('lobby_update', (data) => {
        debugLog('[client] lobby_update players=', (data.players || []).length);
        lobbyPlayers = data.players || [];
        lobbyOngoingGames = data.ongoing_games || [];
        mySid = data.your_sid || mySid;
        if (shouldIgnoreLobbyUpdateWhileInMatch()) {
            debugLog('[client] ignored lobby_update while in match phase=', phase, 'view=', activeViewId);
            return;
        }
        clearNetworkMatchStateForLobby();
        phase = 'lobby';
        renderLobby(data);
        if (data.chat_history) renderLobbyChatHistory(data.chat_history);
    });
    bindSocketEvent('lobby_chat_history', (data) => {
        renderLobbyChatHistory(data || {});
    });
    bindSocketEvent('dm_update', (data = {}) => {
        dmData.unread_count = Number(data.unread_count || dmData.unread_count || 0);
        updateFriendsBadge();
        loadDmThreads(false);
    });
    bindSocketEvent('invite_received', (data) => {
        debugLog('[client] invite_received:', data);
        showModal(`
            <h3>${UI.invite_received}</h3>
            <p>${data.inviter_name} ${UI.invite_message}</p>
            <div class="modal-buttons">
                <button class="btn btn-primary" id="invite-accept">${UI.accept}</button>
                <button class="btn btn-danger" id="invite-decline">${UI.decline}</button>
            </div>
        `);
        $('invite-accept').onclick = () => {
            debugLog('[client] accept_invite inviter_sid=', data.inviter_sid);
            socket.emit('accept_invite', { inviter_sid: data.inviter_sid });
            hideModal();
        };
        $('invite-decline').onclick = () => {
            debugLog('[client] decline_invite inviter_sid=', data.inviter_sid);
            socket.emit('decline_invite', { inviter_sid: data.inviter_sid });
            hideModal();
        };
    });
    bindSocketEvent('invite_declined', () => {
        flashStatus(UI.invite_declined, 2000);
    });
    bindSocketEvent('team_invite', (data) => {
        showModal(`
            <h3>${UI.form_team}</h3>
            <p>${tf('team_invite_msg', data.from_name)}</p>
            <div class="modal-buttons">
                <button class="btn btn-primary" id="team-accept">${UI.accept}</button>
                <button class="btn btn-danger" id="team-decline">${UI.decline}</button>
            </div>
        `);
        $('team-accept').onclick = () => {
            socket.emit('accept_team', { from_sid: data.from_sid });
            hideModal();
        };
        $('team-decline').onclick = () => {
            socket.emit('decline_team', { from_sid: data.from_sid });
            hideModal();
        };
    });
    bindSocketEvent('team_formed', (data) => {
        flashStatus(tf('team_formed_msg', data.members.join(', ')), 3000);
    });
    bindSocketEvent('team_disbanded', () => {
        flashStatus(UI.team_disbanded_msg, 3000);
    });
    bindSocketEvent('team_declined', (data) => {
        flashStatus(UI.team_declined_msg, 2000);
    });
    bindSocketEvent('team_match_invite', (data) => {
        showModal(`
            <h3>${UI.invite_team}</h3>
            <p>${tf('team_match_invite_msg', data.from_team.join(' & '))}</p>
            <div class="modal-buttons">
                <button class="btn btn-primary" id="match-accept">${UI.accept}</button>
                <button class="btn btn-danger" id="match-decline">${UI.decline}</button>
            </div>
        `);
        $('match-accept').onclick = () => {
            socket.emit('accept_team_match', { from_leader: data.from_leader });
            hideModal();
        };
        $('match-decline').onclick = () => {
            socket.emit('decline_team_match', { from_leader: data.from_leader });
            hideModal();
        };
    });
    bindSocketEvent('team_match_declined', () => {
        flashStatus(UI.team_match_declined_msg, 2000);
    });
    bindSocketEvent('team_match_accepted', () => {
        hideModal();
    });
    bindSocketEvent('game_phase', (data) => {
        debugLog('[client] game_phase:', data.phase);
        phase = data.phase;
        if (!data.solo) soloMode = false;
        if (phase === 'draft') {
            debugLog('[client] entering draft phase, reset rematch flag');
            resetRematchUiState();
            showView('view-draft');
            updateStatus(UI.draft_phase);
        } else if (phase === 'event_select') {
            resetRematchUiState();
            showView('view-event-select');
            updateStatus(UI.select_event);
        } else if (phase === 'event_reveal') {
            resetRematchUiState();
            showView('view-event-select');
            updateStatus(UI.event_selected || UI.select_event);
        } else if (phase === 'playing') {
            resetRematchUiState();
            showView('view-game');
            updateStatus(UI.game_loading || 'Loading...');
        } else if (phase === 'game_over') {
            updateStatus(UI.game_over);
        } else if (phase === 'lobby') {
            showView('view-lobby');
            updateStatus(getViewStatusText('view-lobby'));
        } else if (phase === 'action' || phase === 'draw' || phase === 'response' || phase === 'choice') {
            showView('view-game');
        }
        syncBattleLogMatch(data || {});
        syncPhaseChatMatch(data || {});
    });
    bindSocketEvent('draft_state', (data) => {
        const previousDraftState = draftState;
        const oldOptIds = draftState && draftState.options ? draftState.options.map(o => o.def_id) : [];
        const newOptIds = data.options ? data.options.map(o => o.def_id) : [];
        const isReroll = oldOptIds.length > 0 && JSON.stringify(oldOptIds) !== JSON.stringify(newOptIds) && (draftState ? draftState.rerolls : 0) > (data.rerolls || 0);
        draftState = data;
        syncBattleLogMatch(data || {});
        if (data.your_id != null) playerId = data.your_id;
        mergeSkinLooksFromPayload(data);
        renderDraft(data, isReroll, previousDraftState);
    });
    bindSocketEvent('pregame_status_update', (data) => {
        if (!data || !draftState) return;
        if (phaseContextMatchKey(data) && phaseContextMatchKey(draftState) && phaseContextMatchKey(data) !== phaseContextMatchKey(draftState)) return;
        draftState = {
            ...draftState,
            others_picks_count: data.others_picks_count || draftState.others_picks_count || {},
            others_status: data.others_status || draftState.others_status || {},
            others_total_rounds: data.others_total_rounds || draftState.others_total_rounds || {},
            opponent_picks_count: data.opponent_picks_count ?? draftState.opponent_picks_count,
            player_names: data.player_names || draftState.player_names,
            total_rounds: data.total_rounds || draftState.total_rounds,
            round: data.round || draftState.round,
        };
        if (data.your_id != null) playerId = data.your_id;
        updateDraftInfo(draftState);
    });
    bindSocketEvent('event_select', (data) => {
        debugLog('[client] event_select');
        phase = 'event_select';
        eventSelectData = data;
        syncBattleLogMatch(data || {});
        if (data.your_id != null) playerId = data.your_id;
        mergeSkinLooksFromPayload(data);
        renderEventSelect(data);
    });
    bindSocketEvent('event_reveal', (data) => {
        debugLog('[client] event_reveal');
        phase = 'event_reveal';
        eventSelectData = data;
        syncBattleLogMatch(data || {});
        syncPhaseChatMatch(data || {});
        updatePhaseChatChannelOptions(data || {});
        if (data.your_id != null) playerId = data.your_id;
        mergeSkinLooksFromPayload(data);
        renderEventReveal(data);
    });
    bindSocketEvent('event_sub_choice', (data) => {
        debugLog('[client] event_sub_choice');
        phase = 'event_sub_choice';
        // Keep showing draft view so player can see their picks
        showView('view-draft');
        updateStatus(data.needs_sub_choice ? UI.select_event : UI.event_waiting);
        handleEventSubChoice(data);
    });
    bindSocketEvent('state_update', (data) => {
        debugLog('[client] state_update: phase=', data.phase, 'current_player=', data.current_player, 'your_id=', data.your_id, 'pending_response=', data.pending_response != null, 'spectating=', data.spectating);
        if (data && data.spectating && pendingSpectateRoomId != null && data.room_id != null && Number(data.room_id) !== Number(pendingSpectateRoomId)) {
            debugLog('[client] ignored stale spectate state for room=', data.room_id, 'pending=', pendingSpectateRoomId);
            return;
        }
        if (data && data.spectating && pendingSpectateRoomId == null && !isSpectating) {
            debugLog('[client] ignored late spectate state after leaving, room=', data.room_id);
            return;
        }
        if (data && data.spectating && activeSpectateRoomId != null && data.room_id != null && Number(data.room_id) !== Number(activeSpectateRoomId)) {
            debugLog('[client] ignored spectate state for inactive room=', data.room_id, 'active=', activeSpectateRoomId);
            return;
        }
        const previousGameState = gameState;
        soloMode = !!data.solo;
        syncBattleLogMatch(data || {});
        gameState = data;
        phase = data.phase || phase;
        if (data.spectating) {
            isSpectating = true;
            if (data.room_id != null) activeSpectateRoomId = Number(data.room_id);
            if (data.spectate_perspective != null) spectatePerspective = data.spectate_perspective;
        }
        if (!isSpectating && data.your_id != null) playerId = data.your_id;
        mergeSkinLooksFromPayload(data);
        if (!isSpectating && data.pending_response != null) {
            pendingPlayCard = pendingPlayCard || data.pending_response;
        } else if (!responsePending) {
            pendingPlayCard = null;
        }
        if (data.pending_response === null && responsePending) {
            responsePending = false;
            responseData = null;
            removeFloatingCardPreview();
            const rp = $('response-panel');
            if (rp) { rp.innerHTML = ''; rp.classList.add('hidden'); }
            if (responseTimerId) { clearInterval(responseTimerId); responseTimerId = null; }
        }
        if (pendingPlayCard && data.you && data.you.hand) {
            const stillInHand = data.you.hand.some(c => c.instance_id === pendingPlayCard.instance_id);
            if (!stillInHand) {
                pendingPlayCard = null;
            }
        }
        const keepOptimisticForState = !!optimisticResourceOverride;
        clearPendingServerAction({ keepOptimistic: keepOptimisticForState });
        if (phase === 'game_over') {
            renderGameOverAfterFinalAnimation(previousGameState, data, { fullScreen: true, tutorial: false });
            optimisticResourceOverride = null;
        } else {
            clearScheduledGameOver();
            if (!areSequentialGameStates(previousGameState, data)) {
                pendingLocalResourceCosts = [];
                pendingOptimisticResourceCosts = [];
            }
            queueVisibleHandExileAnimations(previousGameState, data);
            renderGame(data);
            showStateDeltas(previousGameState, data);
            if (data.pending_v2_ui) showV2UiRequest(data.pending_v2_ui);
            optimisticResourceOverride = null;
        }
    });
    bindSocketEvent('solo_state', (data) => {
        clearPendingSoloFallback();
        const previousGameState = gameState;
        soloMode = true;
        tutorialMode = !!data.tutorial || tutorialMode;
        isSpectating = false;
        syncBattleLogMatch(data || {});
        gameState = data;
        phase = data.phase || phase;
        playerId = data.your_id;
        if (data.pending_response == null && !responsePending) {
            pendingPlayCard = null;
        }
        if (data.pending_response === null && responsePending) {
            responsePending = false;
            responseData = null;
            removeFloatingCardPreview();
            const rp = $('response-panel');
            if (rp) { rp.innerHTML = ''; rp.classList.add('hidden'); }
            if (responseTimerId) { clearInterval(responseTimerId); responseTimerId = null; }
        }
        const keepOptimisticForState = !!optimisticResourceOverride;
        clearPendingServerAction({ keepOptimistic: keepOptimisticForState });
        if (phase === 'game_over') {
            if (data.tutorial || tutorialMode) {
                renderGameOverAfterFinalAnimation(previousGameState, data, { fullScreen: true, tutorial: true });
            } else {
                renderGameOverAfterFinalAnimation(previousGameState, data, { fullScreen: false, deferResultLabels: true });
            }
            optimisticResourceOverride = null;
        } else {
            clearScheduledGameOver();
            if (!areSequentialGameStates(previousGameState, data)) {
                pendingLocalResourceCosts = [];
                pendingOptimisticResourceCosts = [];
            }
            queueVisibleHandExileAnimations(previousGameState, data);
            renderGame(data);
            showStateDeltas(previousGameState, data);
            if (data.pending_v2_ui) showV2UiRequest(data.pending_v2_ui);
            optimisticResourceOverride = null;
        }
    if (tutorialMode) {
        scheduleTutorialOverlayStart();
        updateTutorialOverlay();
        scheduleTutorialBotAction();
        setTimeout(updateTutorialOverlay, 80);
    }
    });
    bindSocketEvent('response_request', (data) => {
        debugLog('[RESPONSE] response_request, counter_cards:', (data.counter_cards || []).length);
        clearPendingServerAction({ keepOptimistic: true });
        responsePending = true;
        responseData = data;
        showResponseUI(data);
    });
    bindSocketEvent('ally_consent_request', (data) => {
        showAllyConsentUI(data);
    });
    bindSocketEvent('surrender_consent_request', (data) => {
        showSurrenderConsentUI(data);
    });
    bindSocketEvent('surrender_consent_waiting', () => {
        flashStatus(UI.surrender_waiting_teammate, 3000);
    });
    bindSocketEvent('surrender_consent_result', (data) => {
        const accepted = !!(data && data.accepted);
        flashStatus(accepted ? UI.surrender_confirmed : UI.surrender_declined, 2600, accepted ? undefined : 'error');
    });
    bindSocketEvent('choice_request', (data) => {
        clearPendingServerAction({ keepOptimistic: true });
        choicePending = true;
        choiceData = data;
        pendingPlayCard = null;
        showChoiceUI(data);
    });
    bindSocketEvent('v2_ui_request', (data) => {
        clearPendingServerAction({ keepOptimistic: true });
        pendingPlayCard = null;
        clearSelectedPlayCard();
        showV2UiRequest(data);
    });
    bindSocketEvent('action_rejected', (data) => {
        clearPendingServerAction();
        pendingPlayCard = null;
        clearSelectedPlayCard();
        removeFloatingCardPreview();
        clientRejectAction((data && data.message) || UI.operation_failed);
    });
    bindSocketEvent('chat', (data) => {
        debugLog('[client] chat:', data.nickname, data.text, 'spectator=', data.is_spectator);
        const nick = getChatDisplayName(data);
        if (phase === 'lobby') {
            appendLobbyChat(nick, data.text, data);
        } else if (phase === 'draft' || phase === 'event_select') {
            appendPhaseChat(nick, data.text, data, data);
        } else {
            appendGameChat(nick, data.text, data, data);
        }
    });
    bindSocketEvent('mod_settings_updated', (data) => {
        if (data && data.ok) {
            showActionToast(UI.save_success, 1600, 'success');
            return;
        }
        flashStatus(UI.save_failed.replace('{0}', (data && data.reason) || UI.operation_failed), 3200, 'error');
    });
    bindSocketEvent('server_error', (data) => {
        debugLog('[client] server_error:', data.message);
        clearPendingSoloFallback();
        if (activeViewId === 'view-solo' && phase === 'solo_edit') {
            pendingSoloStart = false;
            window.__pendingSoloPayload = null;
            clearPendingServerAction();
            pendingPlayCard = null;
            clearSelectedPlayCard();
            flashStatus(moderationMessageFromPayload(data, translateServerMessage(data.message)), 3600, 'error');
            return;
        }
        flashStatus(moderationMessageFromPayload(data, translateServerMessage(data.message)), 3600, 'error');
        pendingSpectateRoomId = null;
        clearPendingServerAction();
        pendingPlayCard = null;
        clearSelectedPlayCard();
        if (gameState && gameState.phase && activeViewId === 'view-game' && isNetworkMatchPhase(phase)) {
            renderGame(gameState);
        }
    });
    bindSocketEvent('match_start_failed', (data = {}) => {
        const message = data.message || UI.mod_mismatch_msg || UI.operation_failed;
        debugLog('[client] match_start_failed:', message);
        hideModal();
        clearNetworkMatchStateForLobby();
        phase = 'lobby';
        showView('view-lobby');
        flashStatus(translateServerMessage(message), 4200, 'error');
    });
    bindSocketEvent('opponent_disconnected', (data) => {
        if (data && data.timeout) {
            if (data.stay) {
                hideModal();
                flashStatus(UI.opponent_disconnected, 2400, 'warning');
                return;
            }
            if (data.game_over) {
                hideModal();
                updateStatus(UI.game_over);
                return;
            }
            hideModal();
            updateStatus(UI.opponent_disconnected);
            flashStatus(UI.opponent_disconnected, 2400, 'warning');
            return;
        } else if (data && (data.reconnect_timeout > 0 || data.wait_forever)) {
            showOpponentDCWaiting(data);
        } else {
            showOpponentDCWaiting({
                reconnect_timeout: 0,
                wait_forever: true,
                opponent_nickname: (data && data.opponent_nickname) || UI.opponent || '?',
            });
            flashStatus(UI.opponent_disconnected, 2400, 'warning');
        }
    });
    bindSocketEvent('opponent_reconnected', () => {
        flashStatus(UI.opponent_reconnected, 2000);
        hideModal();
    });
    bindSocketEvent('reconnect_available', (data) => {
        phase = 'reconnecting';
        showModal(`
            <h3>${UI.reconnect_title}</h3>
            <p>${UI.reconnect_prompt}</p>
            <div class="modal-buttons">
                <button class="btn btn-primary" id="reconnect-yes">${UI.ok}</button>
                <button class="btn btn-secondary" id="reconnect-no">${UI.cancel}</button>
            </div>
        `);
        $('reconnect-yes').onclick = () => {
            socket.emit('reconnect_accept', { room_id: data.room_id, old_sid: data.old_sid });
            hideModal();
        };
        $('reconnect-no').onclick = () => {
            socket.emit('reconnect_decline', { room_id: data.room_id, old_sid: data.old_sid });
            hideModal();
        };
    });
    bindSocketEvent('reconnect_timeout', () => {
        flashStatus(UI.reconnect_timeout, 3000, 'error');
        phase = 'lobby';
    });
    bindSocketEvent('rematch_requested', (data = {}) => {
        debugLog('[client] rematch_requested');
        if (data.mode === '2v2' || (gameState && gameState.mode === '2v2')) {
            if (phase === 'game_over') updateGameOverRematchButton(gameState);
            return;
        }
        rematchRequestedByOpponent = true;
        updateRematchState(data);
        updateGameOverRematchButton(gameState);
        updateStatus(UI.opponent_rematch);
    });
    bindSocketEvent('rematch_state', (data = {}) => {
        updateRematchState(data);
        if (data.mode === '2v2') rematchRequestedByOpponent = false;
        if (phase === 'game_over') updateGameOverRematchButton(gameState);
    });
    bindSocketEvent('player_returned_lobby', (data = {}) => {
        const name = data.player_name || data.nickname || '';
        updateRematchState({
            ...(rematchState || {}),
            rematch_blocked: true,
            rematch_blocked_reason: 'player_returned_lobby',
            rematch_returned_player_name: name,
        });
        rematchRequestedByOpponent = false;
        if (gameState) {
            gameState.rematch_blocked = true;
            gameState.rematch_blocked_reason = 'player_returned_lobby';
            gameState.rematch_returned_player_name = name;
        }
        flashStatus(tf('player_returned_lobby', name || UI.opponent), 3600, 'warning');
        if (phase === 'game_over') updateGameOverRematchButton(gameState);
    });
    bindSocketEvent('spectate_enter', (data) => {
        if (data && pendingSpectateRoomId != null && data.room_id != null && Number(data.room_id) !== Number(pendingSpectateRoomId)) {
            debugLog('[client] ignored stale spectate_enter for room=', data.room_id, 'pending=', pendingSpectateRoomId);
            return;
        }
        pendingSpectateRoomId = null;
        activeSpectateRoomId = data && data.room_id != null ? Number(data.room_id) : null;
        isSpectating = true;
        spectatePerspective = 0;
        phase = 'playing';
        showView('view-game');
    });
    bindSocketEvent('spectate_leave', () => {
        clearNetworkMatchStateForLobby();
        pendingSpectateRoomId = null;
        activeSpectateRoomId = null;
        isSpectating = false;
        spectatePerspective = 0;
        phase = 'lobby';
        showView('view-lobby');
    });
    bindSocketEvent('server_broadcast', (data) => {
        flashStatus(data.message || '', 4000);
    });
    bindSocketEvent('solo_paused', () => {
        clearPendingSoloFallback();
        if (suppressSoloPausedHandler) {
            suppressSoloPausedHandler = false;
            return;
        }
        if (tutorialMode) {
            finishTutorialReturn();
            return;
        }
        soloMode = false;
        showSoloTraining();
    });
}

function displayWidth(str) {
    let w = 0;
    for (const ch of str) {
        const code = ch.codePointAt(0);
        if ((code >= 0x4e00 && code <= 0x9fff) || (code >= 0x3040 && code <= 0x30ff) ||
            (code >= 0xac00 && code <= 0xd7af) || (code >= 0xff00 && code <= 0xffef) ||
            (code >= 0x2000 && code <= 0x206f)) {
            w += 2;
        } else {
            w += 1;
        }
    }
    return w;
}

function onLogin() {
    if (currentAccount) {
        onAccountEnter();
        return;
    }
    const nick = $('input-nickname').value.trim();
    const err = $('login-error');
    if (!nick) {
        if (err) err.textContent = UI.login_need_nickname;
        return;
    }
    if (displayWidth(nick) > 16) {
        if (err) err.textContent = UI.login_name_too_long;
        return;
    }
    if (/^\d+$/.test(nick)) {
        if (err) err.textContent = UI.login_name_not_numbers;
        return;
    }
    if (/^[\-_]+$/.test(nick)) {
        if (err) err.textContent = UI.login_name_not_symbols;
        return;
    }
    if (/[\-_]{2,}/.test(nick)) {
        if (err) err.textContent = UI.login_name_no_repeat_symbols;
        return;
    }
    const server = getServerAddress();
    nickname = nick;
    loginCredential = nick;
    if (err) err.textContent = '';
    updateStatus(UI.connecting);
    connectSocket(server);
}

function setAccountError(message) {
    const err = $('account-error');
    if (err) err.textContent = message || '';
}

function clearAccountPasswordInputs() {
    [
        'input-account-password',
        'input-account-password-confirm',
        'input-account-old-password',
        'input-account-new-password',
        'input-account-new-password-confirm',
    ].forEach((id) => {
        const input = $(id);
        if (input) input.value = '';
    });
}

function accountStatsText(user) {
    if (!user) return '';
    return tf(
        'account_stats',
        user.games_played || 0,
        user.wins || 0,
        user.losses || 0,
        user.draws || 0
    );
}

function normalizeSkinConfig(raw) {
    let data = raw;
    if (typeof data === 'string') {
        try { data = JSON.parse(data); } catch (_) { data = {}; }
    }
    if (!data || typeof data !== 'object') data = {};
    const skin = { ...DEFAULT_SKIN_CONFIG };
    const color = String(data.primary_color || data.primaryColor || '').trim();
    if (/^#[0-9a-fA-F]{6}$/.test(color)) skin.primary_color = color.toUpperCase();
    const eyeShape = String(data.eye_shape || data.eyeShape || '').trim().toLowerCase();
    if (SKIN_EYE_SHAPES.has(eyeShape)) skin.eye_shape = eyeShape;
    return skin;
}

function loadLocalSkinConfig() {
    try {
        return normalizeSkinConfig(localStorage.getItem('gtn_skin_config'));
    } catch (_) {
        return { ...DEFAULT_SKIN_CONFIG };
    }
}

function saveLocalSkinConfig(skin) {
    try {
        localStorage.setItem('gtn_skin_config', JSON.stringify(normalizeSkinConfig(skin)));
    } catch (_) {}
}

function getCurrentSkinConfig() {
    if (currentAccount && currentAccount.skin) return normalizeSkinConfig(currentAccount.skin);
    return loadLocalSkinConfig();
}

function setSkinError(message = '') {
    const el = $('skin-error');
    if (el) el.textContent = message || '';
}

function readSkinFormConfig() {
    return normalizeSkinConfig({
        primary_color: $('skin-primary-color')?.value || DEFAULT_SKIN_CONFIG.primary_color,
        eye_shape: $('skin-eye-shape')?.value || DEFAULT_SKIN_CONFIG.eye_shape,
    });
}

function hexToRgb(hex) {
    const text = String(hex || '').replace('#', '');
    if (!/^[0-9a-fA-F]{6}$/.test(text)) return { r: 255, g: 231, b: 99 };
    return {
        r: parseInt(text.slice(0, 2), 16),
        g: parseInt(text.slice(2, 4), 16),
        b: parseInt(text.slice(4, 6), 16),
    };
}

function rgbToHex(rgb) {
    return `#${[rgb.r, rgb.g, rgb.b].map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('')}`.toUpperCase();
}

function deriveSkinBorderColor(color) {
    const rgb = hexToRgb(color);
    return rgbToHex({ r: rgb.r * 0.81, g: rgb.g * 0.81, b: rgb.b * 0.81 });
}

function skinLuminance(color) {
    const { r, g, b } = hexToRgb(color);
    const srgb = [r, g, b].map(v => {
        const c = v / 255;
        return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * srgb[0] + 0.7152 * srgb[1] + 0.0722 * srgb[2];
}

function normalizeSkinLook(raw) {
    if (!raw || typeof raw !== 'object') return { ...DEFAULT_SKIN_LOOK };
    let x = Number(raw.x || 0);
    let y = Number(raw.y || 0);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return { ...DEFAULT_SKIN_LOOK };
    const length = Math.hypot(x, y);
    if (length < 0.001) return { ...DEFAULT_SKIN_LOOK };
    x = Math.max(-1, Math.min(1, x / length));
    y = Math.max(-1, Math.min(1, y / length));
    return {
        x: Math.round(x * 1000) / 1000,
        y: Math.round(y * 1000) / 1000,
    };
}

function skinLookCssVars(rawLook) {
    const look = normalizeSkinLook(rawLook);
    return `--skin-look-x:${(look.x * SKIN_LOOK_OFFSET_X_PERCENT).toFixed(1)}%;--skin-look-y:${(look.y * SKIN_LOOK_OFFSET_Y_PERCENT).toFixed(1)}%`;
}

function isLocalSkinLookPlayerId(id) {
    const pid = normalizePlayerId(id);
    return pid != null && pid === normalizePlayerId(playerId) && !isSpectating && !replayMode;
}

function getSkinLookForPlayerId(id) {
    const pid = normalizePlayerId(id);
    if (pid == null) return { ...DEFAULT_SKIN_LOOK };
    if (isLocalSkinLookPlayerId(pid)) return normalizeSkinLook(localSkinLook);
    return normalizeSkinLook(skinLookByPlayerId.get(pid));
}

function resolveSkinLookForPlayer(id, dataLook = null) {
    const pid = normalizePlayerId(id);
    if (isLocalSkinLookPlayerId(pid)) return normalizeSkinLook(localSkinLook);
    return normalizeSkinLook(dataLook || getSkinLookForPlayerId(pid));
}

function setSkinLookForPlayerId(id, look, { local = false } = {}) {
    const pid = normalizePlayerId(id);
    const normalized = normalizeSkinLook(look);
    if (local || isLocalSkinLookPlayerId(pid)) {
        localSkinLook = normalized;
    }
    if (pid != null) {
        skinLookByPlayerId.set(pid, normalized);
        applySkinLookToRenderedAvatars(pid, normalized);
    }
    if (local || isLocalSkinLookPlayerId(pid) || pid == null) {
        applySkinLookToLocalPreview(normalized);
    }
    return normalized;
}

function applySkinLookVarsToAvatar(avatar, look) {
    if (!avatar || !avatar.style) return;
    const normalized = normalizeSkinLook(look);
    avatar.style.setProperty('--skin-look-x', `${(normalized.x * SKIN_LOOK_OFFSET_X_PERCENT).toFixed(1)}%`);
    avatar.style.setProperty('--skin-look-y', `${(normalized.y * SKIN_LOOK_OFFSET_Y_PERCENT).toFixed(1)}%`);
}

function applySkinLookToRenderedAvatars(id, look) {
    const pid = normalizePlayerId(id);
    if (pid == null) return;
    document.querySelectorAll(`.skin-avatar[data-player-id="${pid}"]`).forEach(avatar => {
        applySkinLookVarsToAvatar(avatar, look);
    });
}

function applySkinLookToLocalPreview(look = localSkinLook) {
    document.querySelectorAll('.skin-avatar[data-look-owner="local"], #skin-preview-avatar .skin-avatar').forEach(avatar => {
        applySkinLookVarsToAvatar(avatar, look);
    });
}

const SKIN_MOUTH_NORMAL_POINTS = Object.freeze([20, 18, 36, 32, 64, 32, 80, 18]);
const SKIN_MOUTH_HURT_POINTS = Object.freeze([20, 26, 36, 12, 64, 12, 80, 26]);
const skinMouthAnimationByAvatar = new WeakMap();

function skinMouthPathAt(t) {
    const amount = Math.max(0, Math.min(1, Number(t) || 0));
    const values = SKIN_MOUTH_NORMAL_POINTS.map((base, index) => {
        const next = SKIN_MOUTH_HURT_POINTS[index];
        return Number((base + (next - base) * amount).toFixed(2));
    });
    return `M ${values[0]} ${values[1]} C ${values[2]} ${values[3]} ${values[4]} ${values[5]} ${values[6]} ${values[7]}`;
}

function setSkinMouthT(avatar, t) {
    if (!avatar) return;
    const amount = Math.max(0, Math.min(1, Number(t) || 0));
    const path = avatar.querySelector('.skin-mouth-line');
    if (path) path.setAttribute('d', skinMouthPathAt(amount));
    avatar.dataset.skinMouthT = String(amount);
    const pid = normalizePlayerId(avatar.dataset.playerId);
    if (pid != null) skinMouthTByPlayerId.set(pid, amount);
}

function getSkinMouthT(avatar) {
    if (!avatar) return 0;
    const stored = Number(avatar.dataset.skinMouthT);
    if (Number.isFinite(stored)) return Math.max(0, Math.min(1, stored));
    return avatar.classList.contains('skin-mouth-hurt') ? 1 : 0;
}

function animateSkinMouthTo(avatar, targetT) {
    if (!avatar) return;
    const target = Math.max(0, Math.min(1, Number(targetT) || 0));
    const current = skinMouthAnimationByAvatar.get(avatar);
    if (current && current.raf) cancelAnimationFrame(current.raf);
    const start = getSkinMouthT(avatar);
    if (Math.abs(start - target) < 0.01) {
        setSkinMouthT(avatar, target);
        skinMouthAnimationByAvatar.delete(avatar);
        return;
    }
    const duration = 360;
    const startTime = performance.now();
    const animation = { raf: 0 };
    const step = (now) => {
        const raw = Math.max(0, Math.min(1, (now - startTime) / duration));
        const eased = raw < 0.5 ? 4 * raw * raw * raw : 1 - Math.pow(-2 * raw + 2, 3) / 2;
        setSkinMouthT(avatar, start + (target - start) * eased);
        if (raw < 1) {
            animation.raf = requestAnimationFrame(step);
        } else {
            setSkinMouthT(avatar, target);
            skinMouthAnimationByAvatar.delete(avatar);
        }
    };
    animation.raf = requestAnimationFrame(step);
    skinMouthAnimationByAvatar.set(avatar, animation);
}

function getActiveSkinDamageMood(playerId) {
    const pid = normalizePlayerId(playerId);
    if (pid == null) return null;
    const entry = skinDamageMoodByPlayerId.get(pid);
    if (!entry) return null;
    if (Number(entry.until || 0) <= Date.now()) {
        skinDamageMoodByPlayerId.delete(pid);
        return null;
    }
    return entry;
}

function skinDamageMoodClasses(playerId) {
    const mood = getActiveSkinDamageMood(playerId);
    if (!mood) return '';
    const kind = String(mood.kind || '');
    return [
        'skin-mouth-hurt',
        kind === 'poison' ? 'skin-hit-poison' : '',
        kind === 'fire' ? 'skin-hit-fire' : '',
    ].filter(Boolean).join(' ');
}

function applySkinDamageMoodToAvatar(avatar, mood) {
    if (!avatar) return;
    if (avatar.classList.contains('is-defeated')) {
        avatar.classList.remove('skin-hit-poison', 'skin-hit-fire');
        const playerAvatar = avatar.closest && avatar.closest('.player-avatar');
        if (playerAvatar) playerAvatar.classList.remove('skin-hit-poison', 'skin-hit-fire');
        setSkinMouthT(avatar, 1);
        return;
    }
    avatar.classList.remove('skin-mouth-hurt', 'skin-hit-poison', 'skin-hit-fire');
    const playerAvatar = avatar.closest && avatar.closest('.player-avatar');
    if (playerAvatar) playerAvatar.classList.remove('skin-hit-poison', 'skin-hit-fire');
    if (!mood) {
        animateSkinMouthTo(avatar, 0);
        return;
    }
    avatar.classList.add('skin-mouth-hurt');
    animateSkinMouthTo(avatar, 1);
    if (mood.kind === 'poison') avatar.classList.add('skin-hit-poison');
    else if (mood.kind === 'fire') avatar.classList.add('skin-hit-fire');
    if (playerAvatar && mood.kind === 'poison') playerAvatar.classList.add('skin-hit-poison');
    else if (playerAvatar && mood.kind === 'fire') playerAvatar.classList.add('skin-hit-fire');
}

function applySkinDamageMoodToRenderedAvatars(playerId) {
    const pid = normalizePlayerId(playerId);
    if (pid == null) return;
    const mood = getActiveSkinDamageMood(pid);
    document.querySelectorAll(`.skin-avatar[data-player-id="${pid}"]`).forEach(avatar => {
        applySkinDamageMoodToAvatar(avatar, mood);
    });
    document.querySelectorAll(`[data-player-target-region][data-player-id="${pid}"]`).forEach(region => {
        region.classList.remove('skin-hit-poison', 'skin-hit-fire');
        if (mood && mood.kind === 'poison') region.classList.add('skin-hit-poison');
        else if (mood && mood.kind === 'fire') region.classList.add('skin-hit-fire');
    });
}

function triggerSkinDamageMood(playerId, kind = 'damage', delay = 0, holdMs = SKIN_DAMAGE_HOLD_MS) {
    const pid = normalizePlayerId(playerId);
    if (pid == null) return;
    const run = () => {
        const current = skinDamageMoodByPlayerId.get(pid);
        if (current && current.timer) clearTimeout(current.timer);
        if (!current || !getActiveSkinDamageMood(pid)) {
            skinMouthTByPlayerId.set(pid, 0);
        }
        const mood = {
            kind: kind === 'poison' || kind === 'fire' ? kind : 'damage',
            until: Date.now() + Math.max(1, Number(holdMs) || SKIN_DAMAGE_HOLD_MS),
            timer: null,
        };
        mood.timer = setTimeout(() => {
            const latest = skinDamageMoodByPlayerId.get(pid);
            if (latest !== mood) return;
            skinDamageMoodByPlayerId.delete(pid);
            applySkinDamageMoodToRenderedAvatars(pid);
        }, Math.max(1, Number(holdMs) || SKIN_DAMAGE_HOLD_MS));
        skinDamageMoodByPlayerId.set(pid, mood);
        applySkinDamageMoodToRenderedAvatars(pid);
    };
    const wait = Math.max(0, Number(delay) || 0);
    if (wait) setTimeout(run, wait);
    else run();
}

function renderSkinAvatar(skinInput, options = {}) {
    const skin = normalizeSkinConfig(skinInput);
    const corrupted = !!options.corrupted;
    const corruptAnimateClass = options.animateCorruption ? ' skin-corruption-animate' : '';
    const mainColor = skin.primary_color;
    const border = deriveSkinBorderColor(mainColor);
    const inverted = skinLuminance(skin.primary_color) < 0.22;
    const invertedClass = inverted ? ' is-inverted' : '';
    const pid = normalizePlayerId(options.playerId);
    const look = options.look || (pid != null ? getSkinLookForPlayerId(pid) : localSkinLook);
    const defeated = !!options.defeated;
    const damageMood = corrupted ? '' : skinDamageMoodClasses(pid);
    const storedMouthT = pid != null ? Number(skinMouthTByPlayerId.get(pid)) : NaN;
    const mouthT = defeated ? 1 : (damageMood && Number.isFinite(storedMouthT) ? storedMouthT : 0);
    const defeatedClass = defeated ? ' is-defeated' : '';
    const defeatedSeed = String(options.defeatedSeed || options.playerId || options.lookOwner || skin.primary_color || 'skin');
    const defeatedRotate = 10 + (hashStringToHue(defeatedSeed) % 341);
    const style = `--skin-main:${escapeHtml(skin.primary_color)};--skin-border:${escapeHtml(border)};--skin-defeat-rotate:${defeatedRotate}deg;${skinLookCssVars(look)}`;
    const ownerAttr = pid != null
        ? ` data-player-id="${pid}"`
        : ` data-look-owner="${escapeHtml(options.lookOwner || 'local')}"`;
    return `
        <div class="skin-avatar skin-eye-shape-${escapeHtml(skin.eye_shape)}${invertedClass}${defeatedClass}${corrupted ? ' is-corrupted' : ''}${corruptAnimateClass}${damageMood ? ` ${damageMood}` : ''}"${ownerAttr} style="${style}">
            <div class="skin-eye skin-eye-left"><span class="skin-pupil"></span></div>
            <div class="skin-eye skin-eye-right"><span class="skin-pupil"></span></div>
            <svg class="skin-mouth" viewBox="0 0 100 56" aria-hidden="true" focusable="false">
                <path class="skin-mouth-line" d="${skinMouthPathAt(mouthT)}"></path>
            </svg>
        </div>
    `;
}

function renderSkinEditorPreview() {
    const preview = $('skin-preview-avatar');
    if (!preview) return;
    preview.innerHTML = renderSkinAvatar(readSkinFormConfig(), { look: localSkinLook, lookOwner: 'local' });
}

function syncSkinFormFromCurrent() {
    const skin = getCurrentSkinConfig();
    const colorInput = $('skin-primary-color');
    if (colorInput) colorInput.value = skin.primary_color;
    const shapeSelect = $('skin-eye-shape');
    if (shapeSelect) shapeSelect.value = skin.eye_shape;
    renderSkinEditorPreview();
}

async function saveSkinFromEditor() {
    if (skinSaveInFlight) return;
    setSkinError('');
    const skin = readSkinFormConfig();
    saveLocalSkinConfig(skin);
    if (currentAccount) {
        skinSaveInFlight = true;
        try {
            const data = await authRequest('/api/auth/skin', { skin }, { timeoutMs: 4000 });
            currentAccount = data.user || { ...currentAccount, skin };
            cacheAccount(currentAccount);
        } catch (err) {
            setSkinError(err.message || UI.account_error);
            return;
        } finally {
            skinSaveInFlight = false;
        }
    }
    renderSkinEditorPreview();
    flashStatus(UI.skin_saved || '皮肤已保存', 1600);
}

function resetSkinEditor() {
    const colorInput = $('skin-primary-color');
    if (colorInput) colorInput.value = DEFAULT_SKIN_CONFIG.primary_color;
    const shapeSelect = $('skin-eye-shape');
    if (shapeSelect) shapeSelect.value = DEFAULT_SKIN_CONFIG.eye_shape;
    renderSkinEditorPreview();
}

function openSkinEditor() {
    setSkinError('');
    syncSkinFormFromCurrent();
    showView('view-skin');
}

function applyClientSoloSkins(data) {
    if (!data || typeof data !== 'object') return data;
    const skins = [getCurrentSkinConfig(), { ...DEFAULT_SKIN_CONFIG }];
    const looks = [normalizeSkinLook(localSkinLook), { ...DEFAULT_SKIN_LOOK }];
    data.player_skins = skins;
    data.player_skin_looks = looks;
    const pidx = Number.isFinite(Number(data.your_id)) ? Number(data.your_id) : 0;
    if (data.you && typeof data.you === 'object') {
        data.you.skin = skins[pidx] || skins[0];
        data.you.skin_look = looks[pidx] || looks[0];
    }
    const opp = 1 - pidx;
    if (data.opponent && typeof data.opponent === 'object') {
        data.opponent.skin = skins[opp] || skins[1];
        data.opponent.skin_look = looks[opp] || looks[1];
    }
    return data;
}

function findLocalSkinLookAvatar(localPid = normalizePlayerId(playerId)) {
    const candidates = [];
    if (localPid != null) {
        candidates.push(...document.querySelectorAll(`.skin-avatar[data-player-id="${localPid}"]`));
    }
    candidates.push(...document.querySelectorAll('#skin-preview-avatar .skin-avatar, .skin-avatar[data-look-owner="local"]'));
    return candidates.find(el => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle ? window.getComputedStyle(el) : null;
        return rect && rect.width > 2 && rect.height > 2 && (!style || (style.display !== 'none' && style.visibility !== 'hidden'));
    }) || null;
}

function shouldEmitSkinLook() {
    if (!socket || !socket.connected) return false;
    if (soloMode || isSpectating) return false;
    if (normalizePlayerId(playerId) == null || normalizePlayerId(playerId) < 0) return false;
    if (!['draft', 'event_select', 'event_reveal', 'playing', 'action', 'draw', 'response', 'choice', 'game_over'].includes(phase)) return false;
    return !!((gameState && gameState.room_id != null) || (draftState && draftState.room_id != null) || (eventSelectData && eventSelectData.room_id != null));
}

function maybeEmitSkinLook(look) {
    if (!shouldEmitSkinLook()) return;
    const normalized = normalizeSkinLook(look);
    const key = `${normalized.x.toFixed(2)},${normalized.y.toFixed(2)}`;
    const now = Date.now();
    if (key === lastSkinLookEmitKey || now - lastSkinLookEmitAt < SKIN_LOOK_EMIT_INTERVAL_MS) return;
    lastSkinLookEmitAt = now;
    lastSkinLookEmitKey = key;
    socket.emit('skin_look', normalized);
}

function mergeSkinLooksFromPayload(data) {
    if (!data || typeof data !== 'object') return;
    const looks = Array.isArray(data.player_skin_looks) ? data.player_skin_looks : [];
    looks.forEach((look, index) => {
        const pid = normalizePlayerId(index);
        if (pid == null) return;
        if (!isSpectating && pid === normalizePlayerId(playerId)) return;
        skinLookByPlayerId.set(pid, normalizeSkinLook(look));
    });
}

function updateSkinEyeTracking(event) {
    if ((isSpectating || replayMode) && activeViewId !== 'view-skin') return;
    const point = { x: Number(event.clientX || 0), y: Number(event.clientY || 0) };
    const localPid = normalizePlayerId(playerId);
    const targetAvatar = findLocalSkinLookAvatar(localPid);
    let cx = Math.max(1, window.innerWidth || 1) / 2;
    let cy = Math.max(1, window.innerHeight || 1) / 2;
    if (targetAvatar) {
        const rect = targetAvatar.getBoundingClientRect();
        if (rect && rect.width > 0 && rect.height > 0) {
            cx = rect.left + rect.width / 2;
            cy = rect.top + rect.height / 2;
        }
    }
    const dx = point.x - cx;
    const dy = point.y - cy;
    if (Math.hypot(dx, dy) < 1.5) {
        return;
    }
    const look = normalizeSkinLook({ x: dx, y: dy });
    setSkinLookForPlayerId(localPid, look, { local: true });
    maybeEmitSkinLook(look);
}

function stopAccountReplayPlayback() {
    if (accountReplayTimer) {
        clearTimeout(accountReplayTimer);
        accountReplayTimer = null;
    }
}

function cloneReplayJson(value) {
    if (value == null) return value;
    try {
        return JSON.parse(JSON.stringify(value));
    } catch (_) {
        return value;
    }
}

function getReplaySnapshot(frame) {
    return (frame && frame.state && typeof frame.state === 'object') ? frame.state : {};
}

function getReplayPerspectives(snapshot) {
    return Array.isArray(snapshot && snapshot.perspectives) ? snapshot.perspectives.filter(p => p && typeof p === 'object') : [];
}

function collectReplayPlayers(snapshot) {
    const perspectives = getReplayPerspectives(snapshot);
    const firstSpectate = perspectives.find(p => Array.isArray(p.spectate_players) && p.spectate_players.length);
    if (firstSpectate) {
        return firstSpectate.spectate_players.map((p, i) => ({
            ...(cloneReplayJson(p) || {}),
            player_id: normalizePlayerId(p && p.player_id) ?? i,
            name: (p && p.name) || (snapshot.player_names || [])[i] || `P${i + 1}`,
        }));
    }
    const players = [];
    perspectives.forEach((perspective, i) => {
        const player = perspective.you || perspective.self || null;
        if (player && typeof player === 'object') {
            players[i] = {
                ...(cloneReplayJson(player) || {}),
                player_id: normalizePlayerId(player.player_id) ?? i,
                name: player.name || perspective.your_name || (snapshot.player_names || [])[i] || `P${i + 1}`,
            };
        }
    });
    if (!players.length && snapshot.you && snapshot.opponent) {
        players[0] = { ...(cloneReplayJson(snapshot.you) || {}), player_id: 0, name: snapshot.your_name || snapshot.you.name || 'P1' };
        players[1] = { ...(cloneReplayJson(snapshot.opponent) || {}), player_id: 1, name: snapshot.opponent_name || snapshot.opponent.name || 'P2' };
        if (snapshot.teammate) players[1] = { ...(cloneReplayJson(snapshot.teammate) || {}), player_id: 1, name: snapshot.teammate_name || snapshot.teammate.name || 'P2' };
        if (snapshot.opponent2) players[3] = { ...(cloneReplayJson(snapshot.opponent2) || {}), player_id: 3, name: (snapshot.opponent_names || [])[1] || snapshot.opponent2.name || 'P4' };
    }
    const names = Array.isArray(snapshot.player_names) ? snapshot.player_names : [];
    return players.filter(Boolean).map((p, i) => ({
        ...p,
        player_id: normalizePlayerId(p.player_id) ?? i,
        name: p.name || names[i] || `P${i + 1}`,
    }));
}

function getReplayTeamLayout(perspective, count) {
    if (count >= 4) {
        const teammate = perspective < 2 ? 1 - perspective : (perspective === 2 ? 3 : 2);
        const enemies = [0, 1, 2, 3].filter(id => id !== perspective && id !== teammate);
        return { teammate, enemies };
    }
    return { teammate: null, enemies: [perspective === 0 ? 1 : 0] };
}

function buildReplaySpectateState(frame, perspective = accountReplayPerspective) {
    const snapshot = getReplaySnapshot(frame);
    const perspectives = getReplayPerspectives(snapshot);
    const players = collectReplayPlayers(snapshot);
    const count = players.length || perspectives.length || 2;
    let safePerspective = Number.isFinite(Number(perspective)) ? Number(perspective) : 0;
    safePerspective = Math.max(0, Math.min(Math.max(0, count - 1), safePerspective));
    let base = {};
    if (perspectives[safePerspective]) {
        base = cloneReplayJson(perspectives[safePerspective]) || {};
    } else if (perspectives[0]) {
        base = cloneReplayJson(perspectives[0]) || {};
    } else {
        base = cloneReplayJson(snapshot) || {};
    }
    const mode = snapshot.mode || base.mode || (players.length >= 4 ? '2v2' : '1v1');
    const playerNames = players.map((p, i) => p.name || (snapshot.player_names || [])[i] || `P${i + 1}`);
    base.mode = mode;
    base.phase = snapshot.phase || frame.phase || base.phase || 'action';
    base.round_num = snapshot.round_num || frame.round || base.round_num || 0;
    base.current_player = snapshot.current_player ?? frame.current_player ?? base.current_player;
    base.game_over = snapshot.game_over ?? base.game_over ?? false;
    base.winner = snapshot.winner ?? base.winner;
    base.winning_team = snapshot.winning_team ?? base.winning_team;
    base.player_names = playerNames;
    base.spectate_players = players;
    base.spectating = true;
    base.replay_mode = true;
    base.your_id = safePerspective;
    base.spectate_perspective = safePerspective;
    base.room_id = `replay-${accountReplayData && accountReplayData.id ? accountReplayData.id : 'local'}`;
    base.match_key = `replay:${accountReplayData && accountReplayData.id ? accountReplayData.id : 'local'}`;
    if (!Array.isArray(base.log)) {
        const logSource = perspectives.find(p => Array.isArray(p.log)) || {};
        base.log = Array.isArray(frame.log) && frame.log.length ? frame.log : (Array.isArray(logSource.log) ? logSource.log : []);
        base.log_start = Number(logSource.log_start || 0);
        base.log_total = Number(logSource.log_total != null ? logSource.log_total : base.log.length);
    }
    playerNames.forEach((name, i) => {
        base[`player${i + 1}_name`] = name;
    });
    if (mode === '2v2' && players.length >= 4) {
        const layout = getReplayTeamLayout(safePerspective, players.length);
        const teammate = players[layout.teammate] || {};
        const enemyIds = layout.enemies.slice(0, 2);
        base.you = players[safePerspective] || {};
        base.teammate = teammate;
        base.opponent = players[enemyIds[0]] || {};
        base.opponent2 = players[enemyIds[1]] || {};
        base.teammate_id = layout.teammate;
        base.enemy_ids = enemyIds;
        base.your_name = playerNames[safePerspective] || `P${safePerspective + 1}`;
        base.teammate_name = playerNames[layout.teammate] || `P${layout.teammate + 1}`;
        base.opponent_names = enemyIds.map(id => playerNames[id] || `P${id + 1}`);
        base.opponent_admin_flags = enemyIds.map(id => !!(players[id] && players[id].is_admin_player));
        base.opponent_specials = enemyIds.map(id => specialPublicReplayFields(players[id]));
        base.your_is_admin_player = !!(players[safePerspective] && players[safePerspective].is_admin_player);
        base.teammate_is_admin_player = !!(teammate && teammate.is_admin_player);
        base.your_special = specialPublicReplayFields(players[safePerspective]);
        base.teammate_special = specialPublicReplayFields(teammate);
    } else if (players.length >= 2) {
        const opponentId = safePerspective === 0 ? 1 : 0;
        base.you = players[safePerspective] || {};
        base.opponent = players[opponentId] || {};
        base.your_name = playerNames[safePerspective] || `P${safePerspective + 1}`;
        base.opponent_name = playerNames[opponentId] || `P${opponentId + 1}`;
        base.your_is_admin_player = !!(players[safePerspective] && players[safePerspective].is_admin_player);
        base.opponent_is_admin_player = !!(players[opponentId] && players[opponentId].is_admin_player);
        base.your_special = specialPublicReplayFields(players[safePerspective]);
        base.opponent_special = specialPublicReplayFields(players[opponentId]);
    }
    return base;
}

function specialPublicReplayFields(player) {
    if (!player || typeof player !== 'object') return {};
    return {
        special_role: player.special_role || '',
        special_role_color: player.special_role_color || '',
        special_role_label: player.special_role_label || '',
        special_role_sort: player.special_role_sort ?? 99,
        role_type: player.role_type || '',
        display_name: player.display_name || player.name || '',
        is_admin_player: !!player.is_admin_player,
    };
}

function replayTimeText(ms) {
    const total = Math.max(0, Math.floor(Number(ms || 0) / 1000));
    const minutes = Math.floor(total / 60);
    const seconds = total % 60;
    return `${minutes}:${String(seconds).padStart(2, '0')}`;
}

function replayActionLabel(frame) {
    if (!frame) return '';
    if (frame.phase === 'setup_summary' || frame.setup_summary) return '配装与起手';
    const action = frame.action || null;
    const snapshot = getReplaySnapshot(frame);
    const names = Array.isArray(snapshot.player_names) ? snapshot.player_names : [];
    const actorName = action && action.actor != null ? localizeCanonicalPlayerName(names[action.actor] || `P${Number(action.actor) + 1}`) : '';
    if (!action) return frame.label || frame.phase || '';
    const payload = action.payload || {};
    const cardDef = payload.def_id ? getCardDef(payload.def_id) : null;
    const cardName = cardDef ? getCardName(cardDef) : (payload.def_id || '');
    const targetName = payload.target_player_id != null ? localizeCanonicalPlayerName(names[payload.target_player_id] || `P${Number(payload.target_player_id) + 1}`) : '';
    const typeMap = {
        play_card: '使用手牌',
        use_trigger: '触发装备',
        response: '反制',
        end_turn: '结束回合',
        resolve_choice: '选择',
        v2_ui_response: '提交窗口',
        ally_consent_response: '回应队友请求',
        urf_replace_card: '替换手牌',
        urf_sell_equipment: '售卖装备',
        surrender: '投降',
        draft_pick: '选择卡牌',
        draft_reroll: '刷新',
        select_opening_event: '选择配装倾向',
        game_over: '对局结束',
        disconnect_timeout: '断线超时',
        admin_delete_card: '管理员删牌',
    };
    const label = typeMap[action.type] || action.type || '动作';
    return [actorName, label, cardName, targetName ? `→ ${targetName}` : ''].filter(Boolean).join(' ');
}

function ensureReplaySetupOverlay() {
    let overlay = $('account-replay-setup-overlay');
    if (overlay) return overlay;
    overlay = document.createElement('div');
    overlay.id = 'account-replay-setup-overlay';
    overlay.className = 'account-replay-setup-overlay hidden';
    document.body.appendChild(overlay);
    return overlay;
}

function hideReplaySetupOverlay() {
    const overlay = $('account-replay-setup-overlay');
    if (overlay) overlay.classList.add('hidden');
}

function replaySetupCardChip(cardDict) {
    const chip = createCardChoiceChip(cardDict || {}, { hideInstanceOnlyFlags: false });
    chip.classList.add('replay-setup-card-chip');
    return chip;
}

function renderReplaySetupOverlay(frame) {
    const overlay = ensureReplaySetupOverlay();
    const summary = (frame && frame.setup_summary) || {};
    const players = Array.isArray(summary.players) ? summary.players : [];
    overlay.innerHTML = '';
    const panel = document.createElement('div');
    panel.className = 'account-replay-setup-panel';

    const head = document.createElement('div');
    head.className = 'account-replay-setup-head';
    const title = document.createElement('div');
    title.className = 'account-replay-setup-title';
    title.textContent = '配装与起手';
    const note = document.createElement('div');
    note.className = 'account-replay-setup-note';
    note.textContent = summary.note || '回放已跳过配装、选牌和开局抽牌过程。';
    head.append(title, note);
    panel.appendChild(head);

    const grid = document.createElement('div');
    grid.className = 'account-replay-setup-grid';
    players.forEach((player, index) => {
        const card = document.createElement('div');
        card.className = 'account-replay-setup-player';
        const name = document.createElement('div');
        name.className = 'account-replay-setup-player-name';
        name.textContent = localizeCanonicalPlayerName(player.name || `P${index + 1}`);
        const event = document.createElement('div');
        event.className = 'account-replay-setup-event';
        event.textContent = player.event_name ? `配装：${player.event_name}` : '配装：未记录';
        card.append(name, event);

        const changes = Array.isArray(player.changes) ? player.changes.filter(item => item && item.text) : [];
        if (changes.length) {
            const changeBox = document.createElement('div');
            changeBox.className = 'account-replay-setup-changes';
            changes.slice(0, 8).forEach(item => {
                const line = document.createElement('div');
                line.className = 'account-replay-setup-change';
                line.textContent = item.label ? `${item.label}：${item.text}` : String(item.text || '');
                changeBox.appendChild(line);
            });
            card.appendChild(changeBox);
        }

        const handTitle = document.createElement('div');
        handTitle.className = 'account-replay-setup-hand-title';
        handTitle.textContent = '起手';
        const hand = document.createElement('div');
        hand.className = 'account-replay-setup-hand';
        const handCards = Array.isArray(player.hand) ? player.hand : [];
        if (handCards.length) {
            handCards.forEach(cardDict => hand.appendChild(replaySetupCardChip(cardDict)));
        } else {
            const empty = document.createElement('span');
            empty.className = 'account-replay-setup-empty';
            empty.textContent = '未记录';
            hand.appendChild(empty);
        }
        card.append(handTitle, hand);
        grid.appendChild(card);
    });
    panel.appendChild(grid);
    overlay.appendChild(panel);
    overlay.classList.remove('hidden');
}

function ensureAccountReplayPlaybackBar() {
    let bar = $('account-replay-playback-bar');
    if (bar) return bar;
    bar = document.createElement('div');
    bar.id = 'account-replay-playback-bar';
    bar.className = 'account-replay-playback-bar hidden';
    bar.innerHTML = `
        <div class="account-replay-playback-head">
            <button class="mini-btn replay-icon-btn" type="button" data-account-replay-live-control="close" title="退出回放">×</button>
            <div id="account-replay-live-meta" class="account-replay-live-meta"></div>
            <button class="mini-btn replay-icon-btn" type="button" data-account-replay-live-control="toggle" title="收起/展开">▴</button>
        </div>
        <div class="account-replay-playback-body">
            <div class="account-replay-playback-main">
                <button class="mini-btn replay-icon-btn" type="button" data-account-replay-live-control="prev" title="上一步">‹</button>
                <button class="mini-btn replay-icon-btn" type="button" data-account-replay-live-control="play" title="播放">▶</button>
                <button class="mini-btn replay-icon-btn" type="button" data-account-replay-live-control="pause" title="暂停">Ⅱ</button>
                <button class="mini-btn replay-speed-btn" type="button" data-account-replay-live-speed="1">1x</button>
                <button class="mini-btn replay-speed-btn" type="button" data-account-replay-live-speed="2">2x</button>
                <button class="mini-btn replay-speed-btn" type="button" data-account-replay-live-speed="4">4x</button>
                <button class="mini-btn replay-speed-btn" type="button" data-account-replay-live-speed="instant">»</button>
                <button class="mini-btn replay-icon-btn" type="button" data-account-replay-live-control="next" title="下一步">›</button>
            </div>
            <div id="account-replay-live-perspectives" class="account-replay-live-perspectives"></div>
            <input id="account-replay-live-progress" class="account-replay-progress" type="range" min="0" max="0" value="0">
            <div id="account-replay-load-progress" class="account-replay-load-progress hidden">
                <div class="account-replay-load-track"><div id="account-replay-load-fill" class="account-replay-load-fill"></div></div>
                <div id="account-replay-load-text" class="account-replay-load-text"></div>
            </div>
        </div>
    `;
    document.body.appendChild(bar);
    bar.addEventListener('click', (event) => {
        const control = event.target.closest('[data-account-replay-live-control]');
        if (control) {
            const action = control.dataset.accountReplayLiveControl;
            if (action === 'close') closeAccountReplayModal();
            if (action === 'prev') stepAccountReplay(-1);
            if (action === 'next') stepAccountReplay(1);
            if (action === 'play') playAccountReplay();
            if (action === 'pause') stopAccountReplayPlayback();
            if (action === 'toggle') {
                accountReplayControlsCollapsed = !accountReplayControlsCollapsed;
                renderAccountReplayPlaybackBar();
            }
            return;
        }
        const speed = event.target.closest('[data-account-replay-live-speed]');
        if (speed) {
            accountReplaySpeed = speed.dataset.accountReplayLiveSpeed === 'instant' ? 'instant' : Number(speed.dataset.accountReplayLiveSpeed || 1);
            renderAccountReplayPlaybackBar();
            if (accountReplayTimer) playAccountReplay();
            return;
        }
        const perspective = event.target.closest('[data-account-replay-perspective]');
        if (perspective) {
            stopAccountReplayPlayback();
            accountReplayPerspective = Number(perspective.dataset.accountReplayPerspective) || 0;
            renderAccountReplayFrame();
        }
    });
    const liveProgress = bar.querySelector('#account-replay-live-progress');
    if (liveProgress) {
        liveProgress.addEventListener('input', (event) => {
            stopAccountReplayPlayback();
            accountReplayFrameIndex = Number(event.target.value) || 0;
            renderAccountReplayFrame();
        });
    }
    return bar;
}

function renderReplayPerspectiveButtons(container, snapshot) {
    if (!container) return;
    const players = collectReplayPlayers(snapshot);
    if (players.length <= 1) {
        container.innerHTML = '';
        return;
    }
    container.innerHTML = players.map((player, i) => `
        <button class="mini-btn account-replay-perspective-btn ${i === accountReplayPerspective ? 'active' : ''}" type="button" data-account-replay-perspective="${i}">
            ${escapeHtml(localizeCanonicalPlayerName(player.name || `P${i + 1}`))}
        </button>
    `).join('');
}

function setAccountReplayLoadProgress(loaded, total, text) {
    const box = $('account-replay-load-progress');
    const fill = $('account-replay-load-fill');
    const label = $('account-replay-load-text');
    const safeTotal = Math.max(0, Number(total) || 0);
    const safeLoaded = Math.max(0, Number(loaded) || 0);
    const visible = accountReplayLoading || (safeTotal > 0 && safeLoaded < safeTotal);
    if (box) box.classList.toggle('hidden', !visible);
    if (fill) {
        const pct = safeTotal > 0 ? Math.max(0, Math.min(100, (safeLoaded / safeTotal) * 100)) : 8;
        fill.style.width = `${pct}%`;
    }
    if (label) {
        label.textContent = text || (safeTotal
            ? tf('replay_loading_progress', safeLoaded, safeTotal)
            : (UI.replay_prepare || UI.replay_loading));
    }
}

function renderAccountReplayPlaybackBar() {
    const frame = accountReplayTimeline[accountReplayFrameIndex] || null;
    const snapshot = getReplaySnapshot(frame);
    const bar = ensureAccountReplayPlaybackBar();
    bar.classList.toggle('hidden', !replayMode);
    bar.classList.toggle('collapsed', !!accountReplayControlsCollapsed);
    const progress = $('account-replay-live-progress');
    if (progress) {
        progress.max = String(Math.max(0, (accountReplayTotalFrames || accountReplayTimeline.length) - 1));
        progress.value = String(accountReplayFrameIndex);
    }
    const meta = $('account-replay-live-meta');
    if (meta) {
        const title = accountReplayData && accountReplayData.meta
            ? [accountReplayData.meta.mode, replayTimeText(frame && frame.t), `${accountReplayFrameIndex + 1}/${Math.max(1, accountReplayTotalFrames || accountReplayTimeline.length)}`].filter(Boolean).join(' · ')
            : `${replayTimeText(frame && frame.t)} · ${accountReplayFrameIndex + 1}/${Math.max(1, accountReplayTotalFrames || accountReplayTimeline.length)}`;
        const action = replayActionLabel(frame);
        meta.textContent = action ? `${title} · ${action}` : title;
    }
    const toggleBtn = bar.querySelector('[data-account-replay-live-control="toggle"]');
    if (toggleBtn) toggleBtn.textContent = accountReplayControlsCollapsed ? '▾' : '▴';
    renderReplayPerspectiveButtons($('account-replay-live-perspectives'), snapshot);
    bar.querySelectorAll('[data-account-replay-live-speed]').forEach(btn => {
        const value = btn.dataset.accountReplayLiveSpeed === 'instant' ? 'instant' : Number(btn.dataset.accountReplayLiveSpeed || 1);
        btn.classList.toggle('active', value === accountReplaySpeed);
    });
    setAccountReplayLoadProgress(
        accountReplayTimeline.filter(Boolean).length,
        accountReplayTotalFrames || accountReplayTimeline.length,
        accountReplayLoading
            ? tf('replay_loading_progress', accountReplayTimeline.filter(Boolean).length, accountReplayTotalFrames || '?')
            : ''
    );
}

function renderAccountReplayList() {
    const list = $('account-replays-list');
    if (!list) return;
    if (!currentAccount) {
        list.innerHTML = '';
        return;
    }
    if (!accountReplayItems.length) {
        list.innerHTML = `<div class="account-replay-sub">${escapeHtml(UI.replay_empty)}</div>`;
        return;
    }
    list.innerHTML = accountReplayItems.map((item) => {
        const players = Array.isArray(item.players) ? item.players.join(' / ') : '';
        const winner = item.winner_name ? tf('replay_winner', item.winner_name) : '';
        const round = tf('replay_round', item.round_num || 0);
        const timeText = formatCommunityTime(item.created_at);
        const subtitle = [timeText, item.mode || '', round, winner].filter(Boolean).join(' · ');
        return `
            <div class="account-replay-item">
                <div>
                    <div class="account-replay-main">${escapeHtml(players || item.mode || '-')}</div>
                    <div class="account-replay-sub">${escapeHtml(subtitle)}</div>
                </div>
                <button class="mini-btn" type="button" data-account-replay-view="${escapeHtml(item.id)}">${escapeHtml(UI.replay_view)}</button>
            </div>
        `;
    }).join('');
}

async function loadAccountReplays() {
    const list = $('account-replays-list');
    if (!currentAccount || !list) return;
    list.innerHTML = `<div class="account-replay-sub">${escapeHtml(UI.replay_loading)}</div>`;
    try {
        const data = await authRequest('/api/replays?limit=8');
        accountReplayItems = Array.isArray(data.items) ? data.items : [];
        renderAccountReplayList();
    } catch (err) {
        list.innerHTML = `<div class="account-replay-sub">${escapeHtml(`${UI.replay_load_failed}: ${err.message || ''}`)}</div>`;
    }
}

function mergeAccountReplayFrames(frames, offset) {
    const start = Math.max(0, Number(offset) || 0);
    (Array.isArray(frames) ? frames : []).forEach((frame, index) => {
        if (frame && typeof frame === 'object') accountReplayTimeline[start + index] = frame;
    });
}

async function fetchAccountReplayFrames(replayId, offset, limit) {
    const data = await authRequest(`/api/replays/${encodeURIComponent(replayId)}/timeline?offset=${offset}&limit=${limit}`);
    if (data.replay) accountReplayData = data.replay;
    accountReplayTotalFrames = Math.max(0, Number(data.total_frames || data.timeline_total || 0) || 0);
    mergeAccountReplayFrames(data.timeline || [], data.offset ?? offset);
    return data;
}

async function continueAccountReplayLoading(replayId, startOffset, token) {
    const chunkSize = 80;
    let offset = Math.max(0, Number(startOffset) || 0);
    while (token === accountReplayLoadToken && offset < accountReplayTotalFrames) {
        const data = await fetchAccountReplayFrames(replayId, offset, chunkSize);
        offset = Math.max(offset + chunkSize, Number(data.offset || offset) + (Array.isArray(data.timeline) ? data.timeline.length : 0));
        renderAccountReplayPlaybackBar();
        if (!accountReplayTimeline[accountReplayFrameIndex]) renderAccountReplayFrame();
        await new Promise(resolve => setTimeout(resolve, 0));
    }
    if (token === accountReplayLoadToken) {
        accountReplayLoading = false;
        renderAccountReplayPlaybackBar();
    }
}

function renderAccountReplayFrame() {
    const frame = accountReplayTimeline[accountReplayFrameIndex] || null;
    const progress = $('account-replay-progress');
    if (progress) {
        progress.max = String(Math.max(0, (accountReplayTotalFrames || accountReplayTimeline.length) - 1));
        progress.value = String(accountReplayFrameIndex);
    }
    const output = $('account-replay-frame');
    if (!frame) {
        if (output) output.textContent = accountReplayLoading ? (UI.replay_loading || UI.replay_prepare) : UI.replay_frame_empty;
        renderAccountReplayPlaybackBar();
        return;
    }
    const replayState = buildReplaySpectateState(frame, accountReplayPerspective);
    replayMode = true;
    isSpectating = true;
    playerId = -1;
    spectatePerspective = accountReplayPerspective;
    gameState = replayState;
    phase = replayState.phase || 'action';
    syncBattleLogMatch(replayState);
    renderGame(replayState);
    if (frame.phase === 'setup_summary' || frame.setup_summary) {
        renderReplaySetupOverlay(frame);
    } else {
        hideReplaySetupOverlay();
    }
    renderAccountReplayPlaybackBar();
    const meta = $('account-replay-meta');
    if (meta) meta.textContent = replayActionLabel(frame);
    renderReplayPerspectiveButtons($('account-replay-perspectives'), getReplaySnapshot(frame));
    if (output) {
        output.innerHTML = `
            <div class="account-replay-empty">
                ${escapeHtml(replayActionLabel(frame) || UI.replay_viewer)}
            </div>
        `;
    }
}

function stepAccountReplay(delta) {
    if (!accountReplayTimeline.length && !accountReplayTotalFrames) return;
    accountReplayFrameIndex = Math.max(0, Math.min((accountReplayTotalFrames || accountReplayTimeline.length) - 1, accountReplayFrameIndex + delta));
    renderAccountReplayFrame();
}

function switchAccountReplayPerspective() {
    if (!accountReplayTimeline.length) return;
    const frame = accountReplayTimeline[accountReplayFrameIndex] || null;
    const players = collectReplayPlayers(getReplaySnapshot(frame));
    const count = Math.max(1, players.length);
    accountReplayPerspective = (Number(accountReplayPerspective || 0) + 1) % count;
    spectatePerspective = accountReplayPerspective;
    renderAccountReplayFrame();
}

function playAccountReplay() {
    stopAccountReplayPlayback();
    const totalFrames = accountReplayTotalFrames || accountReplayTimeline.length;
    if (!totalFrames || accountReplayFrameIndex >= totalFrames - 1) return;
    if (accountReplaySpeed === 'instant') {
        accountReplayFrameIndex = totalFrames - 1;
        renderAccountReplayFrame();
        return;
    }
    const current = accountReplayTimeline[accountReplayFrameIndex] || {};
    const next = accountReplayTimeline[accountReplayFrameIndex + 1] || null;
    if (!next && accountReplayLoading) {
        accountReplayTimer = setTimeout(playAccountReplay, 180);
        return;
    }
    if (!next) return;
    const delay = Math.max(80, ((Number(next.t) || 0) - (Number(current.t) || 0)) / Number(accountReplaySpeed || 1));
    accountReplayTimer = setTimeout(() => {
        stepAccountReplay(1);
        playAccountReplay();
    }, delay);
}

async function openAccountReplay(replayId) {
    stopAccountReplayPlayback();
    const loadToken = ++accountReplayLoadToken;
    accountReplayReturnContext = {
        viewId: getVisibleViewId(),
        gameState: cloneReplayJson(gameState || {}),
        phase,
        playerId,
        isSpectating,
        spectatePerspective,
        activeSpectateRoomId,
        pendingSpectateRoomId,
    };
    const modal = $('account-replay-modal');
    const output = $('account-replay-frame');
    accountReplayData = { id: replayId };
    accountReplayTimeline = [];
    accountReplayTotalFrames = 0;
    accountReplayFrameIndex = 0;
    accountReplayPerspective = 0;
    accountReplayLoading = true;
    replayMode = false;
    if (modal) modal.classList.remove('hidden');
    if (output) {
        output.innerHTML = `
            <div class="account-replay-loading">
                <div class="account-replay-load-track"><div class="account-replay-load-fill" style="width:8%"></div></div>
                <div class="account-replay-load-text">${escapeHtml(UI.replay_prepare || UI.replay_loading)}</div>
            </div>
        `;
    }
    try {
        await fetchAccountReplayFrames(replayId, 0, 24);
        if (loadToken !== accountReplayLoadToken) return;
        replayMode = true;
        if (modal) modal.classList.add('hidden');
        ensureAccountReplayPlaybackBar();
        renderAccountReplayFrame();
        continueAccountReplayLoading(replayId, accountReplayTimeline.filter(Boolean).length, loadToken).catch((err) => {
            if (loadToken !== accountReplayLoadToken) return;
            accountReplayLoading = false;
            flashStatus(`${UI.replay_load_failed}: ${err.message || ''}`, 4000);
            renderAccountReplayPlaybackBar();
        });
    } catch (err) {
        if (loadToken !== accountReplayLoadToken) return;
        accountReplayLoading = false;
        replayMode = false;
        if (output) output.textContent = `${UI.replay_load_failed}: ${err.message || ''}`;
    }
}

function closeAccountReplayModal() {
    stopAccountReplayPlayback();
    accountReplayLoadToken += 1;
    const modal = $('account-replay-modal');
    if (modal) modal.classList.add('hidden');
    const bar = $('account-replay-playback-bar');
    if (bar) bar.classList.add('hidden');
    hideReplaySetupOverlay();
    replayMode = false;
    accountReplayData = null;
    accountReplayTimeline = [];
    accountReplayFrameIndex = 0;
    accountReplayPerspective = 0;
    accountReplayTotalFrames = 0;
    accountReplayLoading = false;
    const ctx = accountReplayReturnContext || {};
    accountReplayReturnContext = null;
    isSpectating = !!ctx.isSpectating;
    spectatePerspective = ctx.spectatePerspective || 0;
    activeSpectateRoomId = ctx.activeSpectateRoomId || null;
    pendingSpectateRoomId = ctx.pendingSpectateRoomId || null;
    playerId = Number.isFinite(Number(ctx.playerId)) ? Number(ctx.playerId) : -1;
    phase = ctx.phase || phase;
    gameState = ctx.gameState || {};
    if (ctx.viewId && ctx.viewId !== 'view-game') {
        showView(ctx.viewId);
    } else if (ctx.viewId === 'view-game' && gameState && gameState.phase) {
        renderGame(gameState);
    } else {
        showView(currentAccount ? 'view-login' : 'view-login');
    }
}

function loadCachedAccount() {
    try {
        const raw = localStorage.getItem('gtn_account_user');
        if (!raw) return null;
        const user = JSON.parse(raw);
        return user && user.username ? user : null;
    } catch (_) {
        return null;
    }
}

function cacheAccount(user) {
    try {
        if (user && user.username) {
            const safeUser = {
                id: user.id,
                username: user.username,
                player_id: user.player_id || '',
                display_name: user.display_name || user.username,
                games_played: user.games_played || 0,
                wins: user.wins || 0,
                losses: user.losses || 0,
                draws: user.draws || 0,
                accept_friend_requests: user.accept_friend_requests !== false,
                searchable_by_nickname: user.searchable_by_nickname !== false,
                searchable_by_player_id: user.searchable_by_player_id !== false,
                skin: normalizeSkinConfig(user.skin || {}),
            };
            localStorage.setItem('gtn_account_user', JSON.stringify(safeUser));
        } else {
            localStorage.removeItem('gtn_account_user');
        }
    } catch (_) {}
}

function renderAccountState() {
    const accountDisplay = currentAccount ? (currentAccount.display_name || currentAccount.username) : '';
    const accountText = currentAccount ? tf('account_logged_in_as', accountDisplay) : UI.account_not_logged_in;
    const popName = $('account-popover-name');
    if (popName) {
        if (currentAccount?.player_id) {
            popName.innerHTML = `${escapeHtml(accountText)} <span class="account-player-id">${escapeHtml(UI.player_id)}: ${escapeHtml(currentAccount.player_id)}</span>`;
        } else {
            popName.textContent = accountText;
        }
    }
    const stats = accountStatsText(currentAccount);
    const popStats = $('account-popover-stats');
    if (popStats) popStats.textContent = stats;
    const replaySection = $('account-replays-section');
    if (replaySection) replaySection.classList.toggle('hidden', !currentAccount);
    const authForm = $('account-auth-form');
    if (authForm) authForm.classList.toggle('hidden', !!currentAccount);
    const passwordChangeForm = $('account-password-change-form');
    if (passwordChangeForm) passwordChangeForm.classList.toggle('hidden', !currentAccount);
    const popLogout = $('btn-account-popover-logout');
    if (popLogout) {
        popLogout.disabled = !currentAccount;
        popLogout.classList.toggle('hidden', !currentAccount);
    }
    const btnConnect = $('btn-connect');
    if (btnConnect) btnConnect.textContent = UI.enter_lobby;
    const friendsTop = $('btn-friends-top');
    const loginVisible = !$('view-login')?.classList.contains('hidden');
    if (friendsTop) friendsTop.classList.toggle('hidden', !currentAccount || !loginVisible);
    const skinTop = $('btn-skin-top');
    if (skinTop) skinTop.classList.toggle('hidden', !loginVisible);
    const guestDivider = $('guest-divider-label')?.closest('.login-divider');
    if (guestDivider) guestDivider.classList.toggle('hidden', !!currentAccount);
    const nicknameInput = $('input-nickname');
    const accountNickDisplay = $('account-nickname-display');
    if (nicknameInput) {
        nicknameInput.classList.toggle('hidden', !!currentAccount);
        if (currentAccount) nicknameInput.value = accountDisplay;
    }
    if (accountNickDisplay) {
        accountNickDisplay.textContent = accountDisplay || '';
        accountNickDisplay.classList.toggle('hidden', !currentAccount);
    }
    cacheAccount(currentAccount);
    renderSocialSettings();
    renderFriendsState();
    renderAccountMode();
    updateCommunityUploadState();
    renderCommunityModList();
    if (activeViewId === 'view-skin') syncSkinFormFromCurrent();
}

function renderAccountMode() {
    const isRegister = accountMode === 'register';
    const loginTab = $('btn-account-mode-login');
    const registerTab = $('btn-account-mode-register');
    if (loginTab) loginTab.classList.toggle('active', !isRegister);
    if (registerTab) registerTab.classList.toggle('active', isRegister);
    const confirmRow = $('account-confirm-row');
    const confirmInput = $('input-account-password-confirm');
    if (confirmRow) {
        confirmRow.classList.toggle('hidden', !isRegister);
        confirmRow.hidden = !isRegister;
        confirmRow.setAttribute('aria-hidden', isRegister ? 'false' : 'true');
    }
    if (confirmInput) {
        confirmInput.disabled = !isRegister;
        if (!isRegister) confirmInput.value = '';
    }
    const loginBtn = $('btn-account-login');
    if (loginBtn) loginBtn.classList.toggle('hidden', isRegister || !!currentAccount);
    const registerBtn = $('btn-account-register');
    if (registerBtn) registerBtn.classList.toggle('hidden', !isRegister || !!currentAccount);
    const changePasswordBtn = $('btn-account-change-password');
    if (changePasswordBtn) changePasswordBtn.classList.toggle('hidden', !currentAccount);
}

function setAccountMode(mode) {
    accountMode = mode === 'register' ? 'register' : 'login';
    setAccountError('');
    clearAccountPasswordInputs();
    renderAccountMode();
}

async function authRequest(path, body, options = {}) {
    const timeoutMs = Math.max(0, Number(options.timeoutMs) || 0);
    const controller = timeoutMs > 0 && typeof AbortController !== 'undefined' ? new AbortController() : null;
    const timer = controller ? setTimeout(() => controller.abort(), timeoutMs) : null;
    try {
        const res = await fetch(path, {
            method: body === undefined ? 'GET' : 'POST',
            headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: body === undefined ? undefined : JSON.stringify(body),
            signal: controller ? controller.signal : undefined,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.success === false) {
            throw new Error(moderationMessageFromPayload(data, data.error || UI.account_error));
        }
        return data;
    } catch (err) {
        if (err && err.name === 'AbortError') {
            throw new Error(UI.server_no_response || '服务器响应超时');
        }
        throw err;
    } finally {
        if (timer) clearTimeout(timer);
    }
}

async function refreshAuthMe() {
    try {
        const data = await authRequest('/api/auth/me');
        currentAccount = data.authenticated ? data.user : null;
    } catch (_) {
        currentAccount = currentAccount || loadCachedAccount();
    }
    renderAccountState();
    if (currentAccount) loadFriends(false);
}

async function onAccountLogin() {
    setAccountError('');
    const username = ($('input-account-username')?.value || '').trim();
    const password = $('input-account-password')?.value || '';
    const confirmInput = $('input-account-password-confirm');
    if (confirmInput) confirmInput.value = '';
    try {
        const data = await authRequest('/api/auth/login', { username, password });
        currentAccount = data.user || null;
        accountMode = 'login';
        clearAccountPasswordInputs();
        renderAccountState();
        loadFriends(false);
        loadAccountReplays();
    } catch (err) {
        setAccountError(err.message || UI.account_error);
    }
}

async function onAccountRegister() {
    setAccountError('');
    const username = ($('input-account-username')?.value || '').trim();
    const password = $('input-account-password')?.value || '';
    const passwordConfirm = $('input-account-password-confirm')?.value || '';
    if (password !== passwordConfirm) {
        setAccountError(UI.account_password_mismatch);
        return;
    }
    try {
        const data = await authRequest('/api/auth/register', { username, password, password_confirm: passwordConfirm });
        currentAccount = data.user || null;
        accountMode = 'login';
        clearAccountPasswordInputs();
        renderAccountState();
        loadFriends(false);
        loadAccountReplays();
    } catch (err) {
        setAccountError(err.message || UI.account_error);
    }
}

async function onAccountChangePassword() {
    setAccountError('');
    const oldPassword = $('input-account-old-password')?.value || '';
    const newPassword = $('input-account-new-password')?.value || '';
    const newPasswordConfirm = $('input-account-new-password-confirm')?.value || '';
    if (newPassword !== newPasswordConfirm) {
        setAccountError(UI.account_password_mismatch);
        return;
    }
    try {
        const data = await authRequest('/api/auth/change-password', {
            old_password: oldPassword,
            new_password: newPassword,
            new_password_confirm: newPasswordConfirm,
        });
        currentAccount = data.user || currentAccount;
        clearAccountPasswordInputs();
        setAccountError(UI.account_password_changed);
        renderAccountState();
    } catch (err) {
        setAccountError(err.message || UI.account_error);
    }
}

async function onAccountLogout() {
    try {
        await authRequest('/api/auth/logout', {});
    } catch (_) {}
    currentAccount = null;
    socialData = { friends: [], incoming: [], outgoing: [], settings: null, unread_count: 0 };
    dmData = { threads: [], unread_count: 0 };
    activeDmThreadId = null;
    activeDmTargetUserId = null;
    activeDmMessages = [];
    accountReplayItems = [];
    accountReplayTimeline = [];
    closeAccountReplayModal();
    accountMode = 'login';
    cacheAccount(null);
    clearAccountPasswordInputs();
    renderAccountState();
}

function onAccountEnter() {
    const err = $('login-error');
    if (!currentAccount) {
        setAccountError(UI.account_need_login);
        return;
    }
    nickname = currentAccount.username;
    loginCredential = '';
    if (err) err.textContent = '';
    setAccountError('');
    updateStatus(UI.connecting);
    connectSocket(getServerAddress());
}

function toggleAccountPopover(force) {
    const pop = $('account-popover');
    if (!pop) return;
    const show = typeof force === 'boolean' ? force : pop.classList.contains('hidden');
    pop.classList.toggle('hidden', !show);
    if (show) {
        refreshAuthMe().then(() => {
            if (currentAccount) loadAccountReplays();
        });
    }
}

function friendDateText(value) {
    if (!value) return '-';
    const parsed = new Date(String(value).replace('Z', '+00:00'));
    if (Number.isNaN(parsed.getTime())) return String(value);
    return parsed.toLocaleString();
}

function friendStatsLine(user) {
    if (!user) return '';
    return `${tf('win_rate', Number(user.win_rate || 0).toFixed(1))} · ${accountStatsText(user)}`;
}

function friendMatchResultText(result) {
    const key = String(result || '').toLowerCase();
    if (key === 'win') return UI.victory || 'Win';
    if (key === 'loss' || key === 'lose') return UI.defeat || 'Loss';
    if (key === 'draw') return UI.draw || 'Draw';
    return result || '';
}

function friendItemUserId(item) {
    const user = item && item.user ? item.user : {};
    return user.id == null ? '' : String(user.id);
}

function findFriendItemByUserId(userId) {
    const id = String(userId || '');
    return (Array.isArray(socialData.friends) ? socialData.friends : []).find(item => friendItemUserId(item) === id) || null;
}

function friendCardHtml(item, type) {
    const user = item?.user || {};
    const matches = Array.isArray(item?.matches) ? item.matches : [];
    const isNotice = item?.notice_type === 'auto_add' || item?.status === 'notice';
    const showPrivateInfo = type === 'friend';
    if (type === 'friend') {
        const unreadThread = (Array.isArray(dmData.threads) ? dmData.threads : []).find(thread => {
            const threadUser = thread.user || {};
            return String(threadUser.id || '') === String(user.id || '');
        });
        const unread = Number(unreadThread?.unread_count || 0);
        const active = String(activeSocialFriendId || '') === String(user.id || '');
        return `
          <button class="friend-name-row${active ? ' active' : ''}" type="button" data-friend-open="${escapeHtml(user.id)}">
            <span class="friend-name">${escapeHtml(user.username || '-')}</span>
            ${unread > 0 ? `<span class="dm-unread">${escapeHtml(unread > 99 ? '99+' : String(unread))}</span>` : ''}
          </button>`;
    }
    const matchText = matches.length
        ? matches.slice(0, 3).map(match => escapeHtml(`${match.mode || '-'} ${friendMatchResultText(match.result)} ${friendDateText(match.ended_at || match.started_at)}`)).join('<br>')
        : escapeHtml(`${UI.recent_matches}: -`);
    let actions = '';
    if (type === 'incoming' && !isNotice) {
        actions = `
          <button class="mini-btn" type="button" data-friend-respond="${escapeHtml(item.request_id)}" data-friend-action="accept">${escapeHtml(UI.friend_accept)}</button>
          <button class="mini-btn" type="button" data-friend-respond="${escapeHtml(item.request_id)}" data-friend-action="decline">${escapeHtml(UI.friend_decline)}</button>
          <button class="mini-btn" type="button" data-friend-respond="${escapeHtml(item.request_id)}" data-friend-action="ignore">${escapeHtml(UI.friend_ignore)}</button>`;
    } else if (type === 'friend') {
        actions = `
          <button class="mini-btn" type="button" data-dm-open-user="${escapeHtml(user.id)}" data-dm-open-name="${escapeHtml(user.username || '')}">私信</button>
          <button class="mini-btn" type="button" data-friend-remove="${escapeHtml(user.id)}">${escapeHtml(UI.friend_remove)}</button>`;
    } else {
        actions = `<button class="mini-btn" type="button" data-dm-open-user="${escapeHtml(user.id)}" data-dm-open-name="${escapeHtml(user.username || '')}">私信</button>`;
    }
    const noticeText = isNotice ? `<div class="friend-sub friend-notice">${escapeHtml(tf('friend_auto_added', user.username || '-'))}</div>` : '';
    return `
      <div class="friend-card">
        <div class="friend-card-head">
          <span class="friend-name">${escapeHtml(user.username || '-')}</span>
          <span class="friend-id">${escapeHtml(user.player_id || '')}</span>
        </div>
        ${noticeText}
        ${showPrivateInfo ? `<div class="friend-sub">${escapeHtml(friendStatsLine(user))}</div>` : ''}
        ${showPrivateInfo ? `<div class="friend-sub">${escapeHtml(tf('last_login', friendDateText(user.last_login_at)))}</div>` : ''}
        ${showPrivateInfo ? `<div class="friend-sub"><b>${escapeHtml(UI.recent_matches)}</b><br>${matchText}</div>` : ''}
        ${actions ? `<div class="friend-actions">${actions}</div>` : ''}
      </div>`;
}

function renderFriendSection(id, items, emptyText, type) {
    const el = $(id);
    if (!el) return;
    const list = Array.isArray(items) ? items : [];
    if (!list.length) {
        el.innerHTML = `<div class="friend-empty">${escapeHtml(emptyText)}</div>`;
        return;
    }
    el.innerHTML = list.map(item => friendCardHtml(item, type)).join('');
}

function renderFriendsState() {
    renderFriendSection('friend-incoming-list', socialData.incoming, UI.friend_request_empty, 'incoming');
    renderFriendSection('friend-outgoing-list', socialData.outgoing, UI.friend_sent_empty, 'outgoing');
    renderFriendSection('friends-list', socialData.friends, UI.friend_empty, 'friend');
    renderFriendDetailProfile();
    renderDmThreads();
    updateFriendsBadge();
}

function showSocialDetailTab(tabName = 'profile') {
    const tab = String(tabName || 'profile');
    document.querySelectorAll('[data-social-detail-tab]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.socialDetailTab === tab);
    });
    ['profile', 'dm', 'incoming', 'outgoing'].forEach(name => {
        const page = $(`social-detail-page-${name}`);
        if (page) page.classList.toggle('hidden', name !== tab);
    });
}

function toggleSocialDetailModal(force, tabName = 'profile') {
    const modal = $('social-detail-modal');
    if (!modal) return;
    const show = typeof force === 'boolean' ? force : modal.classList.contains('hidden');
    modal.classList.toggle('hidden', !show);
    if (show) {
        toggleFriendsPopover(false);
        toggleAccountPopover(false);
        showSocialDetailTab(tabName);
        renderFriendDetailProfile();
    }
}

function openFriendDetail(userId, tabName = 'profile') {
    if (userId != null && userId !== '') {
        activeSocialFriendId = String(userId);
    }
    toggleSocialDetailModal(true, tabName);
}

function renderFriendDetailProfile() {
    const el = $('friend-detail-profile');
    if (!el) return;
    const item = findFriendItemByUserId(activeSocialFriendId) || (Array.isArray(socialData.friends) ? socialData.friends[0] : null);
    if (!item) {
        activeSocialFriendId = null;
        el.innerHTML = `<div class="friend-empty">${escapeHtml(UI.friend_empty)}</div>`;
        return;
    }
    const user = item.user || {};
    activeSocialFriendId = String(user.id || '');
    const matches = Array.isArray(item.matches) ? item.matches : [];
    const matchHtml = matches.length
        ? matches.slice(0, 8).map(match => `
            <div class="friend-detail-match">${escapeHtml(`${match.mode || '-'} · ${friendMatchResultText(match.result)} · ${friendDateText(match.ended_at || match.started_at)}`)}</div>
          `).join('')
        : `<div class="friend-empty">${escapeHtml(`${UI.recent_matches}: -`)}</div>`;
    const lastSeenLabel = String(UI.last_login || '上次下线').replace(/\{0\}/g, '').replace(/[：:]\s*$/, '').trim() || '上次下线';
    el.innerHTML = `
      <div class="friend-detail-name">
        <span>${escapeHtml(user.username || '-')}</span>
        <span class="friend-id">${escapeHtml(user.player_id || '')}</span>
      </div>
      <div class="friend-detail-grid">
        <div class="friend-detail-stat"><b>${escapeHtml(UI.stats || '统计信息')}</b>${escapeHtml(friendStatsLine(user))}</div>
        <div class="friend-detail-stat"><b>${escapeHtml(lastSeenLabel)}</b>${escapeHtml(friendDateText(user.last_login_at))}</div>
      </div>
      <div class="friend-detail-actions">
        <button class="mini-btn" type="button" data-dm-open-user="${escapeHtml(user.id)}" data-dm-open-name="${escapeHtml(user.username || '')}">私信</button>
        <button class="mini-btn" type="button" data-friend-remove="${escapeHtml(user.id)}">${escapeHtml(UI.friend_remove)}</button>
      </div>
      <div>
        <div class="friend-section-title">${escapeHtml(UI.recent_matches)}</div>
        <div class="friend-detail-matches">${matchHtml}</div>
      </div>`;
}

function setFriendsError(message, tone = 'error', autoHideMs = 0) {
    const el = $('friends-error');
    if (!el) return;
    if (friendsMessageTimer) {
        clearTimeout(friendsMessageTimer);
        friendsMessageTimer = null;
    }
    el.textContent = message || '';
    el.classList.toggle('message-neutral', tone === 'neutral');
    el.classList.toggle('message-success', tone === 'success');
    if (message && autoHideMs > 0) {
        friendsMessageTimer = setTimeout(() => {
            el.textContent = '';
            el.classList.remove('message-neutral', 'message-success');
            friendsMessageTimer = null;
        }, autoHideMs);
    }
}

function updateFriendsBadge() {
    const btn = $('btn-friends-top');
    if (!btn) return;
    const count = Number(socialData.unread_count || 0) + Number(dmData.unread_count || 0);
    if (count > 0) {
        btn.dataset.badge = count > 99 ? '99+' : String(count);
        btn.classList.add('has-badge');
    } else {
        delete btn.dataset.badge;
        btn.classList.remove('has-badge');
    }
}

async function loadFriends(markRead = false) {
    if (!currentAccount) {
        socialData = { friends: [], incoming: [], outgoing: [], settings: null, unread_count: 0 };
        renderFriendsState();
        return;
    }
    try {
        const suffix = markRead ? '?mark_read=1' : '';
        const data = await authRequest(`/api/social/friends${suffix}`);
        socialData = {
            friends: Array.isArray(data.friends) ? data.friends : [],
            incoming: Array.isArray(data.incoming) ? data.incoming : [],
            outgoing: Array.isArray(data.outgoing) ? data.outgoing : [],
            settings: data.settings || null,
            unread_count: Number(data.unread_count || 0),
        };
        if (socialData.settings && currentAccount) {
            currentAccount = { ...currentAccount, ...socialData.settings };
            cacheAccount(currentAccount);
            renderSocialSettings();
        }
        renderFriendsState();
        loadDmThreads(false);
    } catch (err) {
        setFriendsError(err.message || UI.account_error);
    }
}

function renderDmThreads() {
    const list = $('dm-thread-list');
    if (!list) return;
    const threads = Array.isArray(dmData.threads) ? dmData.threads : [];
    if (!threads.length) {
        list.innerHTML = `<div class="friend-empty">暂无私信</div>`;
    } else {
        list.innerHTML = threads.map(thread => {
            const user = thread.user || {};
            const unread = Number(thread.unread_count || 0);
            const active = String(thread.thread_id) === String(activeDmThreadId);
            return `
              <button class="dm-thread-item${active ? ' active' : ''}" type="button" data-dm-thread="${escapeHtml(thread.thread_id)}">
                <span class="dm-thread-name">${escapeHtml(user.username || '-')}</span>
                ${unread > 0 ? `<span class="dm-unread">${escapeHtml(unread > 99 ? '99+' : String(unread))}</span>` : ''}
                <span class="dm-thread-preview">${escapeHtml(thread.last_message || '暂无消息')}</span>
              </button>`;
        }).join('');
    }
    const title = $('dm-title');
    if (title) {
        const unread = Number(dmData.unread_count || 0);
        title.textContent = unread > 0 ? `私信 (${unread > 99 ? '99+' : unread})` : '私信';
    }
}

function renderDmMessages() {
    const list = $('dm-message-list');
    if (!list) return;
    if (!activeDmThreadId && !activeDmTargetUserId) {
        list.innerHTML = `<div class="friend-empty">选择会话或输入昵称/ID后发送第一条私信</div>`;
        const title = $('dm-chat-title');
        if (title) title.textContent = '选择一个会话';
        return;
    }
    const currentUserId = currentAccount && currentAccount.id;
    list.innerHTML = '';
    const fragment = document.createDocumentFragment();
    (Array.isArray(activeDmMessages) ? activeDmMessages : []).forEach(msg => {
        const row = document.createElement('div');
        row.className = Number(msg.sender_user_id) === Number(currentUserId) ? 'dm-message self' : 'dm-message other';
        const bubble = document.createElement('div');
        bubble.className = 'dm-bubble';
        bubble.textContent = msg.message || '';
        row.appendChild(bubble);
        fragment.appendChild(row);
    });
    list.appendChild(fragment);
    list.scrollTop = list.scrollHeight;
}

async function loadDmThreads(renderOnly = true) {
    if (!currentAccount) {
        dmData = { threads: [], unread_count: 0 };
        activeDmThreadId = null;
        activeDmTargetUserId = null;
        activeDmTargetIdentifier = '';
        activeDmMessages = [];
        renderDmThreads();
        renderDmMessages();
        updateFriendsBadge();
        return;
    }
    try {
        const data = await authRequest('/api/social/dm/threads?limit=80');
        dmData = {
            threads: Array.isArray(data.threads) ? data.threads : [],
            unread_count: Number(data.unread_count || 0),
        };
        renderDmThreads();
        updateFriendsBadge();
        if (!renderOnly && activeDmThreadId) {
            await openDmThread(activeDmThreadId);
        }
    } catch (err) {
        setFriendsError(err.message || UI.account_error);
    }
}

async function openDmThread(threadId) {
    if (!threadId) return;
    try {
        const data = await authRequest(`/api/social/dm/messages?thread_id=${encodeURIComponent(threadId)}&limit=120&mark_read=1`);
        activeDmThreadId = data.thread_id || threadId;
        activeDmTargetUserId = data.user && data.user.id;
        activeDmTargetIdentifier = '';
        if (activeDmTargetUserId) activeSocialFriendId = String(activeDmTargetUserId);
        activeDmMessages = Array.isArray(data.messages) ? data.messages : [];
        const title = $('dm-chat-title');
        if (title) title.textContent = data.user && data.user.username ? `与 ${data.user.username} 的私信` : '私信';
        dmData.unread_count = Number(data.unread_count || 0);
        renderDmThreads();
        renderDmMessages();
        renderFriendDetailProfile();
        updateFriendsBadge();
    } catch (err) {
        setFriendsError(err.message || UI.account_error);
    }
}

function startDmToUser(userId, username = '') {
    activeDmThreadId = null;
    activeDmTargetUserId = userId || null;
    activeDmTargetIdentifier = '';
    if (userId) activeSocialFriendId = String(userId);
    activeDmMessages = [];
    const title = $('dm-chat-title');
    if (title) title.textContent = username ? `给 ${username} 发私信` : '新私信';
    renderDmThreads();
    renderDmMessages();
    renderFriendDetailProfile();
    toggleSocialDetailModal(true, 'dm');
    const input = $('dm-message-input');
    if (input) input.focus();
}

async function startDmFromIdentifier() {
    const input = $('input-friend-identifier');
    const identifier = (input?.value || '').trim();
    if (!identifier) return;
    activeDmThreadId = null;
    activeDmTargetUserId = null;
    activeDmTargetIdentifier = identifier;
    activeDmMessages = [];
    const title = $('dm-chat-title');
    if (title) title.textContent = `给 ${identifier} 发私信`;
    toggleSocialDetailModal(true, 'dm');
    const msgInput = $('dm-message-input');
    if (msgInput) msgInput.focus();
}

async function sendDmMessage() {
    const input = $('dm-message-input');
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;
    const identifier = activeDmTargetIdentifier || ($('input-friend-identifier')?.value || '').trim();
    const payload = { text };
    if (activeDmTargetUserId) payload.target_user_id = activeDmTargetUserId;
    else if (identifier) payload.identifier = identifier;
    else {
        setFriendsError('请选择私信对象或输入昵称/ID');
        return;
    }
    try {
        const data = await authRequest('/api/social/dm/send', payload);
        input.value = '';
        activeDmThreadId = data.thread_id || activeDmThreadId;
        activeDmTargetUserId = data.user && data.user.id ? data.user.id : activeDmTargetUserId;
        activeDmTargetIdentifier = '';
        activeDmMessages = Array.isArray(data.messages) ? data.messages : activeDmMessages;
        const title = $('dm-chat-title');
        if (title && data.user && data.user.username) title.textContent = `与 ${data.user.username} 的私信`;
        await loadDmThreads(true);
        renderDmMessages();
    } catch (err) {
        setFriendsError(err.message || UI.account_error);
    }
}

async function addFriendFromInput() {
    setFriendsError('');
    const input = $('input-friend-identifier');
    const identifier = (input?.value || '').trim();
    if (!identifier) return;
    try {
        const outgoingBefore = Array.isArray(socialData.outgoing) ? socialData.outgoing.length : 0;
        const data = await authRequest('/api/social/friends/add', { identifier });
        socialData = {
            friends: Array.isArray(data.friends) ? data.friends : [],
            incoming: Array.isArray(data.incoming) ? data.incoming : [],
            outgoing: Array.isArray(data.outgoing) ? data.outgoing : [],
            settings: data.settings || socialData.settings,
            unread_count: Number(data.unread_count || 0),
        };
        if (input) input.value = '';
        const outgoingAfter = Array.isArray(socialData.outgoing) ? socialData.outgoing.length : 0;
        setFriendsError(outgoingAfter > outgoingBefore ? UI.friend_added : (UI.friend_added_direct || UI.friend_updated), 'neutral', 2200);
        renderFriendsState();
    } catch (err) {
        setFriendsError(err.message || UI.account_error);
    }
}

async function respondFriendRequest(requestId, action) {
    try {
        const data = await authRequest('/api/social/friends/respond', { request_id: requestId, action });
        socialData = {
            friends: Array.isArray(data.friends) ? data.friends : [],
            incoming: Array.isArray(data.incoming) ? data.incoming : [],
            outgoing: Array.isArray(data.outgoing) ? data.outgoing : [],
            settings: data.settings || socialData.settings,
            unread_count: Number(data.unread_count || 0),
        };
        setFriendsError(UI.friend_updated, 'neutral', 1800);
        renderFriendsState();
    } catch (err) {
        setFriendsError(err.message || UI.account_error);
    }
}

async function removeFriend(userId) {
    if (!confirm(UI.friend_remove_confirm || '确认删除这个好友吗？')) return;
    try {
        const data = await authRequest('/api/social/friends/remove', { user_id: userId });
        socialData = {
            friends: Array.isArray(data.friends) ? data.friends : [],
            incoming: Array.isArray(data.incoming) ? data.incoming : [],
            outgoing: Array.isArray(data.outgoing) ? data.outgoing : [],
            settings: data.settings || socialData.settings,
            unread_count: Number(data.unread_count || 0),
        };
        setFriendsError(UI.friend_removed, 'neutral', 1800);
        renderFriendsState();
    } catch (err) {
        setFriendsError(err.message || UI.account_error);
    }
}

function toggleFriendsPopover(force) {
    const pop = $('friends-popover');
    if (!pop) return;
    const show = typeof force === 'boolean' ? force : pop.classList.contains('hidden');
    pop.classList.toggle('hidden', !show);
    if (show) {
        toggleAccountPopover(false);
        loadFriends(true);
    }
}

function renderSocialSettings() {
    const ids = [
        ['settings-accept-friend-requests', 'accept_friend_requests'],
        ['settings-searchable-by-nickname', 'searchable_by_nickname'],
        ['settings-searchable-by-player-id', 'searchable_by_player_id'],
    ];
    ids.forEach(([id, key]) => {
        const input = $(id);
        if (!input) return;
        input.disabled = !currentAccount;
        input.checked = currentAccount ? currentAccount[key] !== false : true;
    });
    const hint = $('settings-social-login-hint');
    if (hint) hint.classList.toggle('hidden', !!currentAccount);
}

async function saveSocialSettings() {
    if (!currentAccount) {
        renderSocialSettings();
        return;
    }
    const payload = {
        accept_friend_requests: !!$('settings-accept-friend-requests')?.checked,
        searchable_by_nickname: !!$('settings-searchable-by-nickname')?.checked,
        searchable_by_player_id: !!$('settings-searchable-by-player-id')?.checked,
    };
    const status = $('settings-social-status');
    try {
        const data = await authRequest('/api/social/settings', payload);
        currentAccount = data.user || { ...currentAccount, ...payload };
        if (status) status.textContent = UI.social_settings_saved;
        renderAccountState();
    } catch (err) {
        if (status) status.textContent = err.message || UI.account_error;
        renderSocialSettings();
    }
}

function getServerAddress() {
    localStorage.removeItem('gtn_server');
    return DEFAULT_SERVER;
}

function isLocalSoloRuntimeActive() {
    return !!(localSoloRuntime.enabled && localSoloRuntime.worker);
}

function clearPendingSoloFallback() {
    if (pendingSoloFallbackTimer) {
        clearTimeout(pendingSoloFallbackTimer);
        pendingSoloFallbackTimer = null;
    }
}

function scheduleSoloOfflineFallback(kind, payload) {
    clearPendingSoloFallback();
    pendingSoloFallbackTimer = setTimeout(() => {
        pendingSoloFallbackTimer = null;
        if (soloMode || (gameState && gameState.solo)) return;
        if (socket && socket.connected) return;
        pendingSoloStart = false;
        pendingTutorialStart = false;
        window.__pendingSoloPayload = null;
        if (startLocalSoloRuntime(kind, payload)) {
            flashStatus('服务器未连接，已切换到本地训练', 2600, 'warning');
        } else {
            flashStatus(UI.server_no_response || UI.operation_failed, 3200, 'error');
        }
    }, 5000);
}

function effectsAreLocalSoloSupported(effects) {
    if (!Array.isArray(effects)) return true;
    for (const effect of effects) {
        if (!effect || typeof effect !== 'object') continue;
        const effectType = effect.type || '';
        if (effectType && !LOCAL_SOLO_SUPPORTED_EFFECTS.has(effectType)) return false;
        const params = effect.params || {};
        for (const key of ['then', 'else', 'body', 'effects']) {
            if (Array.isArray(params[key]) && !effectsAreLocalSoloSupported(params[key])) return false;
        }
    }
    return true;
}

function v2StepsAreLocalSoloSupported(value) {
    if (Array.isArray(value)) return value.every(v2StepsAreLocalSoloSupported);
    if (!value || typeof value !== 'object') return true;
    const op = value.op || value.type || '';
    if (op && !LOCAL_SOLO_SUPPORTED_V2_OPS.has(op)) return false;
    return Object.values(value).every(v2StepsAreLocalSoloSupported);
}

function v2EventsAreLocalSoloSupported(cardDef) {
    const events = (cardDef.v2_events && typeof cardDef.v2_events === 'object')
        ? cardDef.v2_events
        : ((cardDef.v2_resource && cardDef.v2_resource.events && typeof cardDef.v2_resource.events === 'object')
            ? cardDef.v2_resource.events
            : {});
    return Object.values(events).every(eventDef => {
        const steps = Array.isArray(eventDef) ? eventDef : (eventDef && (eventDef.steps || eventDef.effects));
        return v2StepsAreLocalSoloSupported(steps || []);
    });
}

function cardIsLocalSoloSupported(cardDef) {
    if (!cardDef) return false;
    if (!effectsAreLocalSoloSupported(cardDef.effects || [])) return false;
    if (!v2EventsAreLocalSoloSupported(cardDef)) return false;
    const scripts = cardDef.scripts || {};
    for (const script of Object.values(scripts)) {
        const effects = Array.isArray(script) ? script : (script && script.effects);
        if (!effectsAreLocalSoloSupported(effects || [])) return false;
    }
    return true;
}

function soloPayloadIsLocalSupported(payload) {
    if (!window.Worker || !payload) return false;
    const deck = [...(payload.deck0 || []), ...(payload.deck1 || [])];
    return deck.every(entry => {
        const defId = typeof entry === 'string' ? entry : entry && entry.def_id;
        return cardIsLocalSoloSupported(getCardDef(defId));
    });
}

function stopLocalSoloRuntime() {
    if (localSoloRuntime.worker) {
        try { localSoloRuntime.worker.terminate(); } catch (_) {}
    }
    localSoloRuntime.enabled = false;
    localSoloRuntime.worker = null;
    localSoloRuntime.fallbackPayload = null;
    localSoloRuntime.fallbackKind = '';
}

function handleLocalGamePhase(data) {
    phase = data.phase || phase;
    if (data.solo) soloMode = true;
    if (data.tutorial) tutorialMode = true;
    if (phase === 'playing' || phase === 'action' || phase === 'draw' || phase === 'response' || phase === 'choice') {
        showView('view-game');
        updateStatus(UI.game_loading || 'Loading...');
    } else if (phase === 'game_over') {
        updateStatus(UI.game_over);
    }
    syncBattleLogMatch(data || {});
    syncPhaseChatMatch(data || {});
}

function handleLocalSoloState(data) {
    applyClientSoloSkins(data);
    const previousGameState = gameState;
    soloMode = true;
    tutorialMode = !!data.tutorial || tutorialMode;
    isSpectating = false;
    syncBattleLogMatch(data || {});
    gameState = data;
    phase = data.phase || phase;
    playerId = data.your_id;
    if (data.pending_response == null && !responsePending) {
        pendingPlayCard = null;
    }
    if (data.pending_response === null && responsePending) {
        responsePending = false;
        responseData = null;
        removeFloatingCardPreview();
        const rp = $('response-panel');
        if (rp) { rp.innerHTML = ''; rp.classList.add('hidden'); }
        if (responseTimerId) { clearInterval(responseTimerId); responseTimerId = null; }
    }
    const keepOptimisticForState = !!optimisticResourceOverride;
    clearPendingServerAction({ keepOptimistic: keepOptimisticForState });
    if (phase === 'game_over') {
        if (data.tutorial || tutorialMode) {
            renderGameOverAfterFinalAnimation(previousGameState, data, { fullScreen: true, tutorial: true });
        } else {
            renderGameOverAfterFinalAnimation(previousGameState, data, { fullScreen: false, deferResultLabels: true });
        }
        optimisticResourceOverride = null;
    } else {
        clearScheduledGameOver();
        if (!areSequentialGameStates(previousGameState, data)) {
            pendingLocalResourceCosts = [];
            pendingOptimisticResourceCosts = [];
        }
        queueVisibleHandExileAnimations(previousGameState, data);
        renderGame(data);
        showStateDeltas(previousGameState, data);
        optimisticResourceOverride = null;
    }
    if (tutorialMode) {
        scheduleTutorialOverlayStart();
        updateTutorialOverlay();
        scheduleTutorialBotAction();
        setTimeout(updateTutorialOverlay, 80);
    }
}

function handleLocalSoloMessage(event) {
    const message = event.data || {};
    const data = message.data || {};
    if (message.type === 'game_phase') {
        handleLocalGamePhase(data);
    } else if (message.type === 'solo_state') {
        handleLocalSoloState(data);
    } else if (message.type === 'response_request') {
        clearPendingServerAction({ keepOptimistic: true });
        responsePending = true;
        responseData = data;
        showResponseUI(data);
    } else if (message.type === 'choice_request') {
        clearPendingServerAction({ keepOptimistic: true });
        choicePending = true;
        choiceData = data;
        pendingPlayCard = null;
        showChoiceUI(data);
    } else if (message.type === 'server_error') {
        clearPendingServerAction();
        flashStatus(translateServerError(data.message), 3000, 'error');
        if (gameState && gameState.phase) renderGame(gameState);
    } else if (message.type === 'solo_paused') {
        const wasTutorial = tutorialMode;
        stopLocalSoloRuntime();
        soloMode = false;
        tutorialMode = false;
        if (wasTutorial) finishTutorialReturn();
        else showSoloTraining();
    } else if (message.type === 'fallback_required') {
        const payload = localSoloRuntime.fallbackPayload;
        const kind = localSoloRuntime.fallbackKind;
        stopLocalSoloRuntime();
        if (kind === 'tutorial') {
            pendingTutorialStart = true;
        } else {
            pendingSoloStart = true;
            window.__pendingSoloPayload = payload;
        }
        connectSocket(getServerAddress());
    }
}

function startLocalSoloRuntime(kind, payload) {
    if (!soloPayloadIsLocalSupported(payload)) return false;
    stopLocalSoloRuntime();
    try {
        const worker = new Worker('/static/js/local_solo_worker.js?v=18');
        localSoloRuntime.worker = worker;
        localSoloRuntime.enabled = true;
        localSoloRuntime.fallbackPayload = payload;
        localSoloRuntime.fallbackKind = kind;
        worker.onmessage = handleLocalSoloMessage;
        worker.onerror = () => {
            const fallbackPayload = localSoloRuntime.fallbackPayload;
            const fallbackKind = localSoloRuntime.fallbackKind;
            stopLocalSoloRuntime();
            if (fallbackKind === 'tutorial') {
                pendingTutorialStart = true;
            } else {
                pendingSoloStart = true;
                window.__pendingSoloPayload = fallbackPayload;
            }
            connectSocket(getServerAddress());
        };
        worker.postMessage({
            type: kind === 'tutorial' ? 'tutorial_start' : 'solo_start',
            payload,
            cardDefs: CARD_DEFS,
            openingEvents,
            openingEventMagicPool,
        });
        return true;
    } catch (e) {
        console.error('Failed to start local solo runtime:', e);
        stopLocalSoloRuntime();
        return false;
    }
}

function emitSoloEvent(eventName, payload = {}) {
    if (isLocalSoloRuntimeActive()) {
        localSoloRuntime.worker.postMessage({ type: eventName, payload });
        return;
    }
    if (socket) socket.emit(eventName, payload);
}

function emitModeEvent(soloEventName, onlineEventName, payload = {}) {
    if (soloMode) emitSoloEvent(soloEventName, payload);
    else if (socket) socket.emit(onlineEventName, payload);
}

function showSoloTraining() {
    soloMode = false;
    phase = 'solo_edit';
    clearActionToast();
    showView('view-solo');
    updateStatus(UI.solo_training);
    try {
        loadSoloDecks(false);
    } catch (err) {
        console.error('[solo] failed to load saved decks', err);
        localStorage.removeItem('gtn_solo_decks');
        soloDeckA = [];
        soloDeckB = [];
        soloEventA = '';
        soloEventB = '';
    }
    try {
        renderSoloEventSelects();
        renderSoloBuilder();
    } catch (err) {
        console.error('[solo] failed to render builder', err);
        flashStatus(UI.operation_failed || '操作失败', 2400, 'error');
    }
}

function loadSoloDecks(showNotice = true) {
    let saved = null;
    try {
        saved = JSON.parse(localStorage.getItem('gtn_solo_decks') || 'null');
    } catch (err) {
        localStorage.removeItem('gtn_solo_decks');
        saved = null;
    }
    if (saved && Array.isArray(saved.deck0) && Array.isArray(saved.deck1)) {
        const normalizeDeck = (deck) => deck
            .map(entry => typeof entry === 'string'
                ? { def_id: entry, instance_flags: [], disabled_flags: [] }
                : { def_id: entry.def_id, instance_flags: [...(entry.instance_flags || [])], disabled_flags: [...(entry.disabled_flags || [])] })
            .filter(entry => entry)
            .slice(0, 15);
        soloDeckA = normalizeDeck(saved.deck0);
        soloDeckB = normalizeDeck(saved.deck1);
        soloEventA = saved.event0 != null ? String(saved.event0) : '';
        soloEventB = saved.event1 != null ? String(saved.event1) : '';
        if (showNotice) flashStatus(UI.load_last, 1200);
    }
}

function saveSoloDecks() {
    localStorage.setItem('gtn_solo_decks', JSON.stringify({ deck0: soloDeckA, deck1: soloDeckB, event0: soloEventA, event1: soloEventB }));
    flashStatus(UI.solo_saved, 1600);
}

function startTutorial(returnTarget = 'home') {
    tutorialReturnTarget = returnTarget;
    if (returnTarget === 'home') localStorage.setItem('gtn_seen_intro', '1');
    tutorialLastLogTotal = 0;
    tutorialDeckViewed = false;
    tutorialCounterSeen = false;
    tutorialIntroActive = false;
    tutorialIntroShown = false;
    if (tutorialOverlayStartTimer) { clearTimeout(tutorialOverlayStartTimer); tutorialOverlayStartTimer = null; }
    if (tutorialIntroTimer) { clearTimeout(tutorialIntroTimer); tutorialIntroTimer = null; }
    tutorialEndHintCount = 0;
    tutorialEndHintKey = '';
    pendingTutorialStart = false;
    closeAbout();
    hideModal();
    hideGameAlert();
    tutorialMode = true;
    hideTutorialOverlay();
    const nickInput = $('input-nickname');
    const stored = localStorage.getItem('gtn_nickname') || '';
    nickname = (nickInput && nickInput.value.trim()) || stored || `新手${Math.floor(1000 + Math.random() * 9000)}`;
    if (nickInput && !nickInput.value.trim()) nickInput.value = nickname;
    localStorage.setItem('gtn_nickname', nickname);
    updateStatus(UI.tutorial_start);
    const tutorialPayload = { playerNames: [UI.tutorial_player_you || '你', UI.tutorial_player_opponent || '练习对手'] };
    if (startLocalSoloRuntime('tutorial', tutorialPayload)) {
        return;
    }
    if (!socket || !socket.connected) {
        pendingTutorialStart = true;
        connectSocket(getServerAddress());
        return;
    }
    emitTutorialStart();
}

function emitTutorialStart() {
    tutorialMode = true;
    emitSoloEvent('tutorial_start', {});
}

function showTutorialOverlay() {
    let overlay = $('tutorial-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'tutorial-overlay';
        overlay.className = 'tutorial-overlay';
        overlay.innerHTML = `
            <div class="tutorial-click-shield hidden" aria-hidden="true"></div>
            <button id="btn-tutorial-skip" class="btn btn-secondary tutorial-skip" type="button"></button>
            <div class="tutorial-card">
                <div class="tutorial-kicker"></div>
                <div class="tutorial-text"></div>
            </div>
            <div class="tutorial-arrow" aria-hidden="true"></div>
        `;
        document.body.appendChild(overlay);
    }
    overlay.classList.remove('hidden');
    const skip = $('btn-tutorial-skip');
    if (skip) {
        skip.textContent = UI.tutorial_skip;
        skip.onclick = skipTutorial;
    }
    updateTutorialOverlay();
}

function scheduleTutorialOverlayStart() {
    if (!tutorialMode || tutorialIntroShown || tutorialOverlayStartTimer) return;
    if (!gameState || !gameState.tutorial) return;
    tutorialOverlayStartTimer = setTimeout(() => {
        tutorialOverlayStartTimer = null;
        if (!tutorialMode || !gameState || !gameState.tutorial) return;
        tutorialIntroActive = true;
        showTutorialOverlay();
        if (tutorialIntroTimer) clearTimeout(tutorialIntroTimer);
        tutorialIntroTimer = setTimeout(() => {
            tutorialIntroTimer = null;
            tutorialIntroActive = false;
            tutorialIntroShown = true;
            updateTutorialOverlay();
        }, 1500);
    }, 500);
}

function hideTutorialOverlay() {
    const overlay = $('tutorial-overlay');
    if (overlay) overlay.classList.add('hidden');
    tutorialStrictFocus = false;
    tutorialEndHintCount = 0;
    tutorialEndHintKey = '';
}

function onTutorialGuardClick(e) {
    if (!tutorialMode || !tutorialStrictFocus) return;
    const target = e.target;
    if (!(target instanceof Element)) return;
    if (target.closest('.tutorial-highlight, #btn-tutorial-skip')) return;
    e.preventDefault();
    e.stopPropagation();
}

document.addEventListener('click', onTutorialGuardClick, true);

function updateTutorialOverlay() {
    if (!tutorialMode) return;
    const overlay = $('tutorial-overlay');
    if (!overlay) return;
    document.querySelectorAll('.tutorial-highlight').forEach(el => el.classList.remove('tutorial-highlight'));
    document.querySelectorAll('.tutorial-card-target').forEach(el => el.classList.remove('tutorial-card-target'));
    const kicker = overlay.querySelector('.tutorial-kicker');
    const text = overlay.querySelector('.tutorial-text');
    const arrow = overlay.querySelector('.tutorial-arrow');
    const shield = overlay.querySelector('.tutorial-click-shield');
    if (tutorialIntroActive) {
        if (shield) shield.classList.add('hidden');
        if (kicker) kicker.textContent = UI.tutorial_start;
        if (text) text.textContent = UI.tutorial_intro || '现在，让我们开始新手教程吧！';
        if (arrow) positionTutorialArrow(arrow, '');
        return;
    }
    const myTurn = gameState && gameState.current_player === 0 && gameState.phase === 'action';
    const enemyTurn = gameState && gameState.current_player === 1 && gameState.phase === 'action';
    const playedThisTurn = Object.values((gameState && gameState.you && gameState.you.cards_played_this_turn) || {})
        .reduce((sum, n) => sum + Number(n || 0), 0);
    const hand = (gameState && gameState.you && gameState.you.hand) || [];
    const hasPlayableType = (type) => hand.some(c => {
        const cd = getCardDef(c.def_id);
        return cd && cd.card_type === type && canPlayCard(c);
    });
    const hasFissionTarget = hand.some(c => {
        const cd = getCardDef(c.def_id);
        return cd && cd.card_type === 'thorn';
    });
    const attackCounts = {};
    hand.forEach(c => {
        const cd = getCardDef(c.def_id);
        if (cd && cd.card_type === 'thorn') attackCounts[c.def_id] = (attackCounts[c.def_id] || 0) + 1;
    });
    const hasFusionTargets = Object.values(attackCounts).some(n => n >= 2);
    const hasFission = hasFissionTarget && hand.some(c => c.def_id === 'Fission' && canPlayCard(c));
    const hasFusion = hasFusionTargets && hand.some(c => c.def_id === 'Fusion' && canPlayCard(c));
    const hasCounter = hand.some(c => {
        const cd = getCardDef(c.def_id);
        return cd && cd.card_type === 'guard';
    });
    const hasFissionedAttack = hand.some(c => {
        const cd = getCardDef(c.def_id);
        return cd && cd.card_type === 'thorn' && Number(c.fission_level || 1) > 1 && canPlayCard(c);
    });
    const hasFusionedAttack = hand.some(c => {
        const cd = getCardDef(c.def_id);
        return cd && cd.card_type === 'thorn' && Number(c.fusion_level || 1) > 1 && canPlayCard(c);
    });
    const hasEnhancedAttack = hasFissionedAttack || hasFusionedAttack;
    const shouldShowDeckHint = !!(gameState && (gameState.round_num || 0) >= 2 && myTurn && !tutorialDeckViewed);
    const shouldShowCounterHint = !!responsePending;
    const endHintCandidate = !!(!enemyTurn && myTurn && playedThisTurn > 0 && !hasEnhancedAttack);
    if (endHintCandidate) {
        const key = `${gameState.round_num || 0}:${gameState.current_player || 0}`;
        if (tutorialEndHintKey !== key) {
            tutorialEndHintKey = key;
            tutorialEndHintCount += 1;
        }
    }
    const shouldShowEndHint = endHintCandidate && tutorialEndHintCount <= 2;
    const shouldFocusEndHint = shouldShowEndHint && tutorialEndHintCount <= 1;
    const strictFocus = shouldShowCounterHint || shouldShowDeckHint || shouldFocusEndHint;
    tutorialStrictFocus = strictFocus;
    if (shield) shield.classList.toggle('hidden', !strictFocus);
    if (shouldShowCounterHint) tutorialCounterSeen = true;
    if (kicker) kicker.textContent = UI.tutorial_start;
    if (text) {
        text.textContent = shouldShowCounterHint
            ? UI.tutorial_hint_counter
            : enemyTurn
            ? UI.tutorial_hint_enemy
            : shouldShowDeckHint
                ? UI.tutorial_hint_deck
                : (myTurn && hasFissionedAttack)
                    ? UI.tutorial_hint_play_fissioned
                    : (myTurn && hasFusionedAttack)
                    ? UI.tutorial_hint_play_fusioned
                : shouldShowEndHint
                    ? UI.tutorial_hint_end
                    : (myTurn && (gameState.round_num || 0) <= 1)
                    ? UI.tutorial_hint_play
                    : (myTurn && hasFission)
                    ? UI.tutorial_hint_fission
                    : (myTurn && hasFusion)
                        ? UI.tutorial_hint_fusion
                        : (myTurn && hasPlayableType('root'))
                            ? UI.tutorial_hint_root
                            : (myTurn && hasPlayableType('bloom'))
                                ? UI.tutorial_hint_bloom
                    : (tutorialDeckViewed && !tutorialCounterSeen && hasCounter)
                        ? UI.tutorial_hint_continue
                        : UI.tutorial_hint_free;
    }
    if (arrow) {
        let arrowMode = '';
        if (!enemyTurn && !shouldShowCounterHint && !shouldShowDeckHint && myTurn && hasFissionedAttack) {
            arrowMode = 'fissioned';
        } else if (!enemyTurn && !shouldShowCounterHint && !shouldShowDeckHint && myTurn && hasFusionedAttack) {
            arrowMode = 'fusioned';
        } else if (!enemyTurn && !shouldShowCounterHint && !shouldShowDeckHint && myTurn && playedThisTurn === 0) {
            if ((gameState.round_num || 0) <= 1) arrowMode = 'play';
            else if (hasFission) arrowMode = 'fission';
            else if (hasFusion) arrowMode = 'fusion';
            else if (hasPlayableType('root')) arrowMode = 'root';
            else if (hasPlayableType('bloom')) arrowMode = 'bloom';
            else arrowMode = 'play';
        }
        positionTutorialArrow(arrow, arrowMode);
    }
    if (shouldShowCounterHint) {
        const panel = $('response-panel');
        if (panel) panel.classList.add('tutorial-highlight');
    } else if (!enemyTurn && shouldShowDeckHint) {
        const btn = $('btn-view-deck');
        if (btn) btn.classList.add('tutorial-highlight');
    } else if (shouldFocusEndHint) {
        const btn = $('btn-end-turn');
        if (btn) btn.classList.add('tutorial-highlight');
    }
}

function scheduleTutorialOverlayRefresh(delay = 320) {
    if (!tutorialMode) return;
    if (tutorialOverlayRefreshTimer) clearTimeout(tutorialOverlayRefreshTimer);
    tutorialOverlayRefreshTimer = setTimeout(() => {
        tutorialOverlayRefreshTimer = null;
        updateTutorialOverlay();
    }, delay);
}

function positionTutorialArrow(arrow, mode) {
    if (arrow) arrow.classList.remove('active');
    if (arrow) {
        arrow.style.removeProperty('--tutorial-arrow-x');
        arrow.style.removeProperty('--tutorial-arrow-top');
        arrow.style.removeProperty('--tutorial-arrow-h');
    }
    if (!mode) {
        return;
    }
    if (mode) {
        const cards = [...document.querySelectorAll('#you-hand .card.card-draggable:not(.card-disabled)')];
        const playable = cards.find(el => {
            const id = Number(el.dataset.instanceId);
            const hand = (gameState && gameState.you && gameState.you.hand) || [];
            const card = hand.find(c => c.instance_id === id);
            const cd = card ? getCardDef(card.def_id) : null;
            if (!card || !cd) return false;
            if (mode === 'fission') return card.def_id === 'Fission';
            if (mode === 'fissioned') return cd.card_type === 'thorn' && Number(card.fission_level || 1) > 1;
            if (mode === 'fusion') return card.def_id === 'Fusion';
            if (mode === 'fusioned') return cd.card_type === 'thorn' && Number(card.fusion_level || 1) > 1;
            if (mode === 'root') return cd.card_type === 'root';
            if (mode === 'bloom') return cd.card_type === 'bloom';
            return cd.card_type === 'thorn';
        }) || cards[0] || document.querySelector('#you-hand .card:not(.card-disabled)');
        if (playable) {
            playable.classList.add('tutorial-card-target');
            const rect = playable.getBoundingClientRect();
            const arrowHeight = Math.min(74, Math.max(52, rect.height * 0.86));
            const overlap = Math.min(10, rect.height * 0.16);
            const top = Math.max(8, rect.top - arrowHeight + overlap);
            arrow.style.setProperty('--tutorial-arrow-x', `${rect.left + rect.width / 2}px`);
            arrow.style.setProperty('--tutorial-arrow-top', `${top}px`);
            arrow.style.setProperty('--tutorial-arrow-h', `${arrowHeight}px`);
            arrow.classList.add('active');
        }
        return;
    }
}

function stopTutorialUiForGameOver() {
    if (tutorialBotTimer) {
        clearTimeout(tutorialBotTimer);
        tutorialBotTimer = null;
    }
    if (tutorialOverlayStartTimer) {
        clearTimeout(tutorialOverlayStartTimer);
        tutorialOverlayStartTimer = null;
    }
    if (tutorialIntroTimer) {
        clearTimeout(tutorialIntroTimer);
        tutorialIntroTimer = null;
    }
    if (tutorialOverlayRefreshTimer) {
        clearTimeout(tutorialOverlayRefreshTimer);
        tutorialOverlayRefreshTimer = null;
    }
    tutorialMode = false;
    pendingTutorialStart = false;
    tutorialDeckViewed = false;
    tutorialCounterSeen = false;
    tutorialIntroActive = false;
    tutorialIntroShown = false;
    tutorialStrictFocus = false;
    tutorialEndHintCount = 0;
    tutorialEndHintKey = '';
    hideTutorialOverlay();
    document.querySelectorAll('.tutorial-highlight').forEach(el => el.classList.remove('tutorial-highlight'));
    document.querySelectorAll('.tutorial-card-target').forEach(el => el.classList.remove('tutorial-card-target'));
    clearSelectedPlayCard();
    pendingPlayCard = null;
}

function skipTutorial() {
    if (tutorialBotTimer) {
        clearTimeout(tutorialBotTimer);
        tutorialBotTimer = null;
    }
    if ((socket && socket.connected && tutorialMode) || isLocalSoloRuntimeActive()) {
        emitSoloEvent('solo_pause', {});
    } else {
        finishTutorialReturn();
    }
}

function finishTutorialReturn() {
    tutorialMode = false;
    pendingTutorialStart = false;
    tutorialDeckViewed = false;
    tutorialCounterSeen = false;
    tutorialIntroActive = false;
    tutorialIntroShown = false;
    tutorialStrictFocus = false;
    if (tutorialOverlayStartTimer) { clearTimeout(tutorialOverlayStartTimer); tutorialOverlayStartTimer = null; }
    if (tutorialIntroTimer) { clearTimeout(tutorialIntroTimer); tutorialIntroTimer = null; }
    if (tutorialOverlayRefreshTimer) { clearTimeout(tutorialOverlayRefreshTimer); tutorialOverlayRefreshTimer = null; }
    soloMode = false;
    hideTutorialOverlay();
    document.querySelectorAll('.tutorial-highlight').forEach(el => el.classList.remove('tutorial-highlight'));
    document.querySelectorAll('.tutorial-card-target').forEach(el => el.classList.remove('tutorial-card-target'));
    clearSelectedPlayCard();
    pendingPlayCard = null;
    if (tutorialReturnTarget === 'about') {
        showView('view-login');
        openAbout();
    } else {
        showView('view-login');
    }
}

function scheduleTutorialBotAction() {
    if (!tutorialMode || (!socket && !isLocalSoloRuntimeActive()) || !gameState || gameState.phase === 'game_over') return;
    if (tutorialBotTimer) clearTimeout(tutorialBotTimer);
    if (gameState.current_player !== 1 || gameState.pending_response || choicePending || responsePending) return;
    tutorialBotTimer = setTimeout(() => {
        if (!tutorialMode || (!socket && !isLocalSoloRuntimeActive()) || !gameState || gameState.current_player !== 1) return;
        emitSoloEvent('tutorial_bot_action', {});
    }, 2100);
}

function getSearchLocalizedText(source, i18nKey, fallbackKey) {
    if (!source) return '';
    const dict = source[i18nKey] || {};
    const parts = [
        dict[currentLang],
        dict.en,
        fallbackKey ? source[fallbackKey] : '',
    ];
    return [...new Set(parts.filter(Boolean))].join(' ');
}

const BUILTIN_PINYIN_SEARCH_MODS = new Set([
    'vanillacards.gtnmod',
    'trollcards.gtnmod',
    'thorncardssupplement1.gtnmod',
]);

const BUILTIN_CARD_PINYIN_ALIASES = {
    Basic: 'ji ben',
    Bone: 'gu tou',
    Stinger: 'ci',
    Sand: 'sha zi',
    Wing: 'chi bang',
    Light: 'qing',
    Fang: 'jian ya',
    Triangle: 'san jiao xing',
    MagicBone: 'mo fa gu tou',
    MagicStinger: 'mo fa ci',
    Fission: 'lie bian',
    Fusion: 'ju bian',
    Iris: 'yuan wei',
    Fire: 'huo',
    Fries: 'shu tiao',
    Rose: 'mei gui',
    ManaOrb: 'mo fa qiu',
    Coffee: 'ka fei',
    Chilli: 'la jiao',
    Chromosome: 'ran se ti',
    Sewage: 'wu shui',
    MagicSewage: 'mo fa wu shui',
    Mimic: 'ni tai',
    Yggdrasil: 'shi jie shu zhi ye shi jie shu',
    Leaf: 'ye zi',
    Yucca: 'si lan',
    Disc: 'yuan pan',
    Battery: 'dian chi',
    MagicLeaf: 'mo fa ye',
    MagicYucca: 'mo fa si lan',
    MagicBattery: 'mo fa dian chi',
    Powder: 'fen mo',
    GoldenLeaf: 'huang jin ye',
    Pincer: 'shi zhen zhe zhen',
    Cancer: 'ai xi bao',
    Corruption: 'fu hua',
    Mark: 'biao ji',
    Mine: 'di lei',
    Bubble: 'pao pao',
    Nazar: 'xie yan hu fu',
    MagicNazar: 'mo fa xie yan',
    MagicBubble: 'mo fa pao pao',
    Bandage: 'beng dai',
    Jelly: 'guo dong',
    Shovel: 'chan zi',
    Compass: 'zhi nan zhen',
    Sponge: 'hai mian',
    Poo: 'bian bian',
    Honey: 'feng mi',
    Pill: 'yao wan',
    Magnet: 'ci tie',
    Antennae: 'chu jiao',
    Claw: 'zhua zi',
    Rice: 'mi',
    Glass: 'bo li',
    MagicGlass: 'mo fa bo li',
    Tomato: 'fan qie',
};

function getBuiltinCardPinyinSearchText(cd) {
    if (currentLang !== 'zh' || !cd) return '';
    const filename = String(cd.source_mod_filename || '').toLowerCase();
    if (!cd.source_mod_is_vanilla && !BUILTIN_PINYIN_SEARCH_MODS.has(filename)) return '';
    const alias = BUILTIN_CARD_PINYIN_ALIASES[cd.id];
    if (!alias) return '';
    const spaced = String(alias).toLowerCase().trim().replace(/\s+/g, ' ');
    const compact = spaced.replace(/\s+/g, '');
    return `${spaced} ${compact}`;
}

function cardSearchText(defId) {
    const cd = getCardDef(defId);
    if (!cd) return defId.toLowerCase();
    const flagText = normalizeFlagList([...(normalizeFlagList(cd.flags || [])), ...(normalizeFlagList(cd.tags || []))]).map(flag => {
        const current = getFlagLabel(flag);
        const en = I18N.en[`tag_${flag}`] || I18N.en[`flag_${flag}`] || flag;
        return `${current} ${en}`;
    }).join(' ');
    return [
        cd.id,
        getCardName(cd),
        getSearchLocalizedText(cd, 'name_i18n', currentLang === 'zh' ? 'name_cn' : 'name_en'),
        cd.name_en || '',
        getCardEffectText(cd),
        getSearchLocalizedText(cd, 'effect_text_i18n', 'effect_text'),
        getCardDescriptionText(cd),
        getSearchLocalizedText(cd, 'description_i18n', 'description'),
        flagText,
        getBuiltinCardPinyinSearchText(cd),
    ].join(' ').toLowerCase();
}

function renderSoloEventSelects() {
    const labelA = $('solo-event-a-label');
    if (labelA) labelA.textContent = UI.solo_event_a;
    const labelB = $('solo-event-b-label');
    if (labelB) labelB.textContent = UI.solo_event_b;
    const buildOptions = (selectEl, selectedVal) => {
        if (!selectEl) return;
        selectEl.innerHTML = `<option value="">${UI.no_event}</option>`;
        openingEvents.forEach(ev => {
            const opt = document.createElement('option');
            opt.value = String(ev.id);
            opt.textContent = getLocalizedEventText(ev, 'name') || String(ev.id);
            opt.selected = String(selectedVal) === String(ev.id);
            selectEl.appendChild(opt);
        });
    };
    buildOptions($('solo-event-a'), soloEventA);
    buildOptions($('solo-event-b'), soloEventB);
    if ($('solo-event-a')) $('solo-event-a').value = soloEventA;
    if ($('solo-event-b')) $('solo-event-b').value = soloEventB;
}

function renderSoloBuilder() {
    const q = (($('solo-card-search') || {}).value || '').trim().toLowerCase();
    const list = $('solo-card-list');
    if (list) {
        list.innerHTML = '';
        Object.keys(CARD_DEFS)
            .filter(defId => defId !== 'Error')
            .filter(defId => !q || cardSearchText(defId).includes(q))
            .sort(compareGalleryCards)
            .forEach(defId => {
                const row = document.createElement('div');
                row.className = 'solo-card-row';
                const cd = CARD_DEFS[defId];
                row.innerHTML = `<span>${getCardName(cd)}</span><small>${getCardTypeLabel(cd.card_type)} ${cd.cost_e}E/${cd.cost_m}M</small>`;
                row.onclick = () => addSoloCard(defId);
                list.appendChild(row);
            });
    }
    renderSoloDeck('a', soloDeckA);
    renderSoloDeck('b', soloDeckB);
}

function renderSoloDeck(which, deck) {
    const el = $(which === 'a' ? 'solo-deck-a' : 'solo-deck-b');
    const count = $(which === 'a' ? 'solo-deck-a-count' : 'solo-deck-b-count');
    if (count) count.textContent = `${deck.length}/15`;
    if (!el) return;
    const panel = el.closest('.solo-deck-panel');
    el.innerHTML = '';
    const selected = soloTargetDeck === which;
    el.classList.toggle('active', selected);
    if (panel) {
        panel.classList.toggle('active', selected);
        panel.onclick = () => {
            if (soloTargetDeck !== which) {
                soloTargetDeck = which;
                renderSoloBuilder();
            }
        };
    }
    el.onclick = () => {
        if (soloTargetDeck !== which) {
            soloTargetDeck = which;
            renderSoloBuilder();
        }
    };
    deck.forEach((defId, idx) => {
        const card = deck[idx];
        const cd = getCardDef(card.def_id);
        const invalid = !cd;
        const baseFlags = new Set([
            ...normalizeFlagList(cd && cd.flags),
            ...normalizeFlagList(cd && cd.tags),
        ]);
        const disabledFlags = new Set(card.disabled_flags || []);
        const effectiveFlags = new Set([...normalizeFlagList(card.instance_flags || []), ...baseFlags]);
        normalizeFlagList(disabledFlags).forEach(flag => effectiveFlags.delete(flag));
        const flagText = [...effectiveFlags].map(getFlagLabel).join(', ');
        const row = document.createElement('div');
        row.className = `solo-deck-card${invalid ? ' invalid' : ''}`;
        row.innerHTML = `
            <div class="solo-deck-card-main">
                <span>${idx + 1}. ${cd ? getCardName(cd) : escapeHtml(card.def_id || '?')}</span>
                ${invalid ? `<small class="solo-invalid-card">${UI.solo_invalid_card}</small>` : (flagText ? `<small>${flagText}</small>` : '')}
            </div>
            <div class="solo-deck-card-actions">
                ${invalid ? '' : `<button class="btn btn-small solo-tag-btn">${UI.edit_tags}</button>`}
                <button class="btn btn-small">${UI.cancel}</button>
            </div>`;
        const tagBtn = row.querySelector('.solo-tag-btn');
        if (tagBtn) {
            tagBtn.onclick = async (e) => {
                e.stopPropagation();
                await editSoloCardFlags(which, idx);
            };
        }
        row.querySelector('.solo-deck-card-actions button:last-child').onclick = (e) => {
            e.stopPropagation();
            deck.splice(idx, 1);
            renderSoloBuilder();
        };
        el.appendChild(row);
    });
}

function clearSoloDeck(which) {
    if (which === 'a') {
        soloDeckA = [];
    } else {
        soloDeckB = [];
    }
    soloTargetDeck = which;
    renderSoloBuilder();
}

function addSoloCard(defId) {
    const deck = soloTargetDeck === 'a' ? soloDeckA : soloDeckB;
    if (deck.length >= 15) return;
    deck.push({ def_id: defId, instance_flags: [], disabled_flags: [] });
    renderSoloBuilder();
}

async function editSoloCardFlags(which, idx) {
    const deck = which === 'a' ? soloDeckA : soloDeckB;
    const card = deck[idx];
    if (!card) return;
    const cd = getCardDef(card.def_id);
    const allFlags = ['precision', 'exile', 'non_stackable', 'indestructible', 'sprout', 'symbiosis', 'attract', 'void', 'self_only', 'uncancellable', 'copy', 'unique', 'swift', 'stealth', 'revealed'];
    const base = new Set([
        ...normalizeFlagList(cd && cd.flags),
        ...normalizeFlagList(cd && cd.tags),
    ]);
    const added = new Set(normalizeFlagList(card.instance_flags || []));
    const disabled = new Set(normalizeFlagList(card.disabled_flags || []));
    const effective = (flag) => (base.has(flag) || added.has(flag)) && !disabled.has(flag);
    const options = allFlags.map(flag => `${effective(flag) ? '[x]' : '[ ]'} ${getFlagLabel(flag)}`);
    const picked = await gamePrompt(UI.edit_tags, options);
    if (picked < 0 || picked >= allFlags.length) return;
    const flag = allFlags[picked];
    if (effective(flag)) {
        if (base.has(flag)) disabled.add(flag);
        added.delete(flag);
    } else {
        if (base.has(flag)) disabled.delete(flag);
        else added.add(flag);
    }
    card.instance_flags = [...added];
    card.disabled_flags = [...disabled];
    renderSoloBuilder();
    await editSoloCardFlags(which, idx);
}

async function buildSoloEventSubChoice(eventId, deck, label) {
    if (eventId === 2) {
        const conversions = [];
        const countOptions = ['1', '2', '3'];
        const countSel = await gamePrompt(UI.choose_convert_count, countOptions, { cancellable: false });
        if (countSel < 0) return false;
        for (let i = 0; i <= countSel; i++) {
            const sourceOptions = deck.map((entry, idx) => cardChoiceOption(entry, { detail: `#${idx + 1}` }));
            const sourceSel = await gamePrompt(`${label} ${UI.choose_source_card_n.replace('{0}', i + 1)}`, sourceOptions, { cancellable: false });
            if (sourceSel < 0) return false;
            conversions.push({
                source_def_id: deck[sourceSel].def_id,
            });
        }
        return { conversions };
    }
    if (eventId === 3) {
        const convert_def_ids = [];
        const countOptions = ['1', '2', '3', '4', '5'];
        const countSel = await gamePrompt(UI.choose_convert_count, countOptions, { cancellable: false });
        if (countSel < 0) return false;
        for (let i = 0; i <= countSel; i++) {
            const sourceOptions = deck.map((entry, idx) => cardChoiceOption(entry, { detail: `#${idx + 1}` }));
            const sourceSel = await gamePrompt(`${label} ${UI.choose_source_card_n.replace('{0}', i + 1)}`, sourceOptions, { cancellable: false });
            if (sourceSel < 0) return false;
            convert_def_ids.push(deck[sourceSel].def_id);
        }
        return { convert_def_ids };
    }
    if (eventId === 5) {
        return await showFatedDrawChoice();
    }
    if (eventId === 8) {
        const sourceOptions = deck.map((entry, idx) => cardChoiceOption(entry, { detail: `#${idx + 1}` }));
        const sourceSel = await gamePrompt(`${label} ${UI.choose_yggdrasil_card}`, sourceOptions, { cancellable: false });
        if (sourceSel < 0) return false;
        return { yggdrasil_convert_def_id: deck[sourceSel].def_id };
    }
    return null;
}

async function startSoloTraining() {
    if (soloDeckA.length !== 15 || soloDeckB.length !== 15) {
        gameAlert(UI.notice, UI.solo_need_15);
        return;
    }
    await refreshCardDefsFromServer({ silent: true });
    if (soloDeckA.concat(soloDeckB).some(card => !card || !getCardDef(card.def_id))) {
        gameAlert(UI.notice, UI.solo_invalid_deck_cards);
        return;
    }
    const event0 = soloEventA ? Number(soloEventA) : null;
    const event1 = soloEventB ? Number(soloEventB) : null;
    const sub0 = await buildSoloEventSubChoice(event0, soloDeckA, UI.solo_deck_a);
    if (sub0 === false) return;
    const sub1 = await buildSoloEventSubChoice(event1, soloDeckB, UI.solo_deck_b);
    if (sub1 === false) return;
    saveSoloDecks();
    const payload = { deck0: soloDeckA, deck1: soloDeckB, event0, event1, sub0, sub1, ...getModLoginPayload() };
    if (socket && socket.connected) {
        clearPendingSoloFallback();
        emitSoloStart(payload);
        return;
    }
    nickname = (($('input-nickname') && $('input-nickname').value) || nickname || 'Solo').trim() || 'Solo';
    pendingSoloStart = true;
    window.__pendingSoloPayload = payload;
    connectSocket(getServerAddress());
    scheduleSoloOfflineFallback('solo', payload);
}

function shouldAnimateSkinCorruption(playerId, corrupted, scope = 'default') {
    const pid = normalizePlayerId(playerId);
    if (pid == null) return false;
    const key = `${scope}:${pid}`;
    const was = skinCorruptionByPlayerId.get(key);
    skinCorruptionByPlayerId.set(key, !!corrupted);
    return !!corrupted && was === false;
}

function playerHasCorruptionEquipment(playerData) {
    const equipment = Array.isArray(playerData && playerData.equipment) ? playerData.equipment : [];
    return equipment.some(eq => {
        const card = eq && (eq.card_instance || eq.card || eq);
        const defId = String((card && card.def_id) || eq.def_id || '').trim();
        return defId === 'Corruption' && !!eq.corruption_active;
    });
}

function emitSoloStart(payload = null) {
    soloMode = true;
    const finalPayload = payload || window.__pendingSoloPayload || { deck0: soloDeckA, deck1: soloDeckB };
    window.__pendingSoloPayload = null;
    emitSoloEvent('solo_start', finalPayload);
}

function renderLobby(data) {
    showView('view-lobby');
    const lobbyPlayers = data.players || [];
    const games = data.ongoing_games || [];
    const teamList = data.teams || [];
    const myTeam = data.your_team || null;
    const myTeamLeader = data.your_team_leader || null;
    const serverMode = data.your_mode || '1v1';
    debugLog('[client] renderLobby: players=', lobbyPlayers.length, 'mySid=', mySid, 'myTeam=', myTeam, 'mode=', serverMode);
    const modeCounts = data.mode_counts && typeof data.mode_counts === 'object'
        ? data.mode_counts
        : lobbyPlayers.reduce((acc, player) => {
            const mode = player.mode || '1v1';
            if (mode === '1v1' || mode === '2v2' || mode === 'urf') {
                acc[mode] = (acc[mode] || 0) + 1;
            }
            return acc;
        }, { '1v1': 0, '2v2': 0, urf: 0 });

    const modeTabs = $('lobby-mode-tabs');
    if (modeTabs) {
        const cachedMode = localStorage.getItem('preferred_mode') || '1v1';
        const currentMode = serverMode || cachedMode;
        modeTabs.querySelectorAll('.mode-tab').forEach(tab => {
            const tabMode = tab.getAttribute('data-mode');
            const label = UI[`mode_${tabMode}`] || tabMode;
            tab.textContent = `${label} (${Number(modeCounts[tabMode] || 0)})`;
            if (tabMode === currentMode) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
            tab.onclick = async () => {
                const newMode = tab.getAttribute('data-mode');
                if (newMode === currentMode) return;
                if (myTeam && newMode !== '2v2') {
                    const confirmed = await gameConfirm(UI.notice || '', UI.mode_switch_confirm);
                    if (!confirmed) return;
                }
                localStorage.setItem('preferred_mode', newMode);
                socket.emit('set_mode', { mode: newMode });
            };
        });
    }

    const currentMode = (modeTabs && modeTabs.querySelector('.mode-tab.active'))
        ? modeTabs.querySelector('.mode-tab.active').getAttribute('data-mode')
        : (localStorage.getItem('preferred_mode') || '1v1');

    const playerBySid = new Map(lobbyPlayers.map(p => [p.sid, p]));
    const adminSort = (a, b) => {
        const rankDelta = getSpecialSortRank(a) - getSpecialSortRank(b);
        if (rankDelta) return rankDelta;
        return String(a.nickname || '').localeCompare(String(b.nickname || ''));
    };
    const teamSpecialRank = (team) => Math.min(
        team.special_role_sort ?? 99,
        ...((team.member_infos || []).map(getSpecialSortRank)),
        ...((team.member_sids || []).map(sid => getSpecialSortRank(playerBySid.get(sid)))),
    );
    const teamHasAdmin = (team) => teamSpecialRank(team) < 99;
    const filteredPlayers = lobbyPlayers.filter(p => {
        const pMode = p.mode || '1v1';
        return pMode === currentMode;
    }).sort(adminSort);

    const onlineCount = $('lobby-online-count');
    if (onlineCount) onlineCount.textContent = tf('online_count', filteredPlayers.length);

    const teamSection = $('lobby-team-section');
    if (teamSection) {
        teamSection.innerHTML = '';
        if (myTeam && currentMode === '2v2') {
            const teamMembers = myTeam.map(sid => playerBySid.get(sid) || { nickname: '?' });
            const teamInfoDiv = document.createElement('div');
            teamInfoDiv.className = 'team-info';
            teamInfoDiv.appendChild(document.createTextNode(`${UI.teammate}: `));
            appendPlayerNameList(teamInfoDiv, teamMembers, { adminPrefix: false });
            teamInfoDiv.appendChild(document.createTextNode(' '));
            const leaveBtn = document.createElement('button');
            leaveBtn.textContent = UI.leave_team;
            leaveBtn.className = 'btn btn-danger btn-sm';
            leaveBtn.onclick = () => socket.emit('leave_team');
            teamInfoDiv.appendChild(leaveBtn);
            teamSection.appendChild(teamInfoDiv);
        }
    }

    const list = $('lobby-players');
    if (!list) return;
    list.innerHTML = '';
    const renderPlayerRow = (p, buttonMode) => {
        const row = document.createElement('div');
        row.className = 'lobby-player-row';
        const isMe = p.sid === mySid;
        const nameSpan = document.createElement('span');
        nameSpan.className = isMe ? 'player-name player-self' : 'player-name';
        setPlayerNameContent(nameSpan, p, { adminPrefix: true });
        row.appendChild(nameSpan);
        const actions = document.createElement('div');
        actions.className = 'lobby-player-actions';
        if (!isMe && buttonMode === 'team' && !myTeam) {
            const btn = document.createElement('button');
            btn.textContent = UI.form_team;
            btn.className = 'btn btn-primary btn-sm';
            btn.onclick = () => socket.emit('form_team', { target_sid: p.sid });
            actions.appendChild(btn);
        } else if (!isMe && buttonMode === 'invite') {
            const btn = document.createElement('button');
            btn.textContent = UI.invite;
            btn.className = 'btn btn-primary';
            btn.onclick = () => {
                debugLog('[client] invite target_sid=', p.sid);
                socket.emit('invite', { target_sid: p.sid });
                updateStatus(UI.invite_sent);
            };
            actions.appendChild(btn);
        }
        if (!isMe) {
            actions.appendChild(createReportButton({
                objectType: 'player',
                objectId: String(p.user_id || p.sid || p.nickname || ''),
                targetUserId: p.user_id || '',
                targetUsername: p.nickname || '',
                title: UI.report_player,
            }, {
                className: 'report-inline-btn lobby-report-btn',
                text: UI.report,
                title: UI.report_player,
            }));
        }
        if (actions.children.length) row.appendChild(actions);
        list.appendChild(row);
    };
    const renderTeamRow = (team) => {
        const isMyTeamRow = myTeam && team.member_sids.some(s => myTeam.includes(s));
        const row = document.createElement('div');
        row.className = 'lobby-team-row';
        const nameSpan = document.createElement('span');
        nameSpan.className = 'player-name';
        const memberInfos = (team.member_infos && team.member_infos.length)
            ? team.member_infos
            : (team.member_sids || []).map(sid => playerBySid.get(sid) || { nickname: '?' });
        appendPlayerNameList(nameSpan, memberInfos, { adminPrefix: false });
        row.appendChild(nameSpan);
        if (!isMyTeamRow && myTeam) {
            const btn = document.createElement('button');
            btn.textContent = UI.invite_team;
            btn.className = 'btn btn-primary btn-sm';
            btn.onclick = () => socket.emit('invite_team', { target_team_leader: team.leader });
            row.appendChild(btn);
        }
        list.appendChild(row);
    };

    if (currentMode === '2v2') {
        const teamsInMode = teamList.filter(t => {
            return t.member_sids.some(sid => {
                const p = playerBySid.get(sid);
                return p && (p.mode || '1v1') === '2v2';
            });
        }).sort((a, b) => {
            const rankDelta = teamSpecialRank(a) - teamSpecialRank(b);
            if (rankDelta) return rankDelta;
            return String((a.members || [])[0] || '').localeCompare(String((b.members || [])[0] || ''));
        });
        const teamedSids = new Set();
        teamsInMode.forEach(t => t.member_sids.forEach(s => teamedSids.add(s)));
        const unteamed = filteredPlayers.filter(p => !teamedSids.has(p.sid));

        if (teamsInMode.length === 0 && unteamed.length === 0) {
            list.innerHTML = `<div class="empty-hint">${UI.no_other_players}</div>`;
        } else {
            teamsInMode.filter(teamHasAdmin).forEach(renderTeamRow);
            unteamed.filter(isSpecialPlayer).forEach(p => renderPlayerRow(p, 'team'));
            teamsInMode.filter(team => !teamHasAdmin(team)).forEach(renderTeamRow);
            unteamed.filter(p => !isSpecialPlayer(p)).forEach(p => renderPlayerRow(p, 'team'));
        }
    } else {
        if (filteredPlayers.length === 0) {
            list.innerHTML = `<div class="empty-hint">${UI.no_other_players}</div>`;
        } else {
            filteredPlayers.forEach(p => renderPlayerRow(p, 'invite'));
        }
    }

    const gamesList = $('lobby-games');
    if (gamesList) {
        gamesList.innerHTML = '';
        const visibleGames = games.filter(g => !g.both_disconnected);
        if (visibleGames.length > 0) {
            visibleGames.forEach(g => {
                const row = document.createElement('div');
                row.className = 'lobby-game-row';
                const roundNum = Number(g.round || 0);
                const phaseLabel = (() => {
                    if (g.phase === 'event_select') return UI.lobby_phase_event_select || UI.status_event_select || UI.select_event || '配装选择';
                    if (['draft', 'event_reveal', 'sub_choice', 'event_sub_choice'].includes(g.phase)) return UI.lobby_phase_draw || '抽牌';
                    return `${UI.round}${roundNum}`;
                })();
                let gameLabel;
                if (g.mode === '2v2') {
                    gameLabel = `${g.player1} & ${g.player2} vs ${g.player3 || '?'} & ${g.player4 || '?'} (${phaseLabel})`;
                } else if (g.mode === 'urf') {
                    gameLabel = `${g.player1} vs ${g.player2} [${UI.mode_urf || 'Infinite Fire'}] (${phaseLabel})`;
                } else {
                    gameLabel = `${g.player1} vs ${g.player2} (${phaseLabel})`;
                }
                row.innerHTML = `<span>${gameLabel}</span>`;
                const canSpectate = g.can_spectate !== false && !['draft', 'event_select'].includes(g.phase);
                if (canSpectate) {
                    const btn = document.createElement('button');
                    btn.textContent = UI.spectate;
                    btn.className = 'btn btn-secondary spectate-btn';
                    btn.onclick = () => {
                        pendingSpectateRoomId = Number(g.room_id);
                        activeSpectateRoomId = null;
                        socket.emit('spectate', { room_id: g.room_id });
                    };
                    row.appendChild(btn);
                }
                gamesList.appendChild(row);
            });
        } else {
            gamesList.innerHTML = `<div class="empty-hint">${UI.no_games}</div>`;
        }
    }
    updateStatus(UI.lobby_status.replace('{0}', nickname));
}

function updateDraftInfo(data) {
    if (!data) return;
    const picks = data.picks || [];
    const rerolls = data.rerolls || 0;
    const round = data.round || 0;
    const totalRounds = data.total_rounds || 15;
    const is2v2 = data.mode === '2v2';
    const othersPicksCount = data.others_picks_count || {};
    const othersTotalRounds = data.others_total_rounds || {};
    const oppPicksCount = Number.isFinite(Number(data.opponent_picks_count))
        ? Number(data.opponent_picks_count)
        : Number(Object.values(othersPicksCount)[0] || 0);
    const othersStatus = data.others_status || {};
    const info = $('draft-info');
    if (info) {
        if (is2v2) {
            const pNames = data.player_names || [];
            const othersInfo = Object.entries(othersStatus).map(([idx, status]) => {
                const pidx = parseInt(idx);
                const name = pNames[pidx] || `P${pidx + 1}`;
                let statusStr = '';
                if (status === 'drafting') {
                    statusStr = `${UI.status_drafting || '选牌中'} ${othersPicksCount[idx] || 0}/${othersTotalRounds[idx] || totalRounds}`;
                } else if (status === 'sub_choice') {
                    statusStr = UI.status_sub_choice || '配装处理';
                } else if (status === 'ready') {
                    statusStr = UI.status_ready || '已完成';
                } else if (status === 'event_select') {
                    statusStr = UI.status_event_select || '选择配装';
                } else {
                    statusStr = `${othersPicksCount[idx] || 0}/${totalRounds}`;
                }
                return `${name}: ${statusStr}`;
            }).join(' | ');
            if (picks.length >= totalRounds) {
                info.textContent = `${UI.draft_complete} | ${othersInfo}`;
            } else {
                info.textContent = `${UI.draft_info} ${round}/${totalRounds} | ${UI.draft_reroll}: ${rerolls} | ${othersInfo}`;
            }
        } else {
            // 1v1: show opponent status
            const oppIdx = 1 - (data.your_id || 0);
            const oppStatus = othersStatus[oppIdx];
            let oppStatusText = '';
            if (oppStatus === 'drafting') {
                oppStatusText = `${UI.status_drafting || '选牌中'} ${oppPicksCount}/${othersTotalRounds[oppIdx] || totalRounds}`;
            } else if (oppStatus === 'sub_choice') {
                oppStatusText = UI.status_sub_choice || '配装处理';
            } else if (oppStatus === 'ready') {
                oppStatusText = UI.status_ready || '已完成';
            } else if (oppStatus === 'event_select') {
                oppStatusText = UI.status_event_select || '选择配装';
            } else {
                oppStatusText = `${oppPicksCount}/${totalRounds}`;
            }
            if (picks.length >= totalRounds) {
                info.textContent = `${UI.draft_complete} | ${UI.waiting_opponent}: ${oppStatusText}`;
            } else {
                info.textContent = `${UI.draft_info} ${round}/${totalRounds} | ${UI.draft_reroll}: ${rerolls} | ${UI.waiting_opponent}: ${oppStatusText}`;
            }
        }
    }
}

function renderDraft(data, isReroll, previousDraftState = null) {
    showView('view-draft');
    syncPhaseChatMatch(data || {});
    updatePhaseChatChannelOptions(data || {});
    const picks = data.picks || [];
    const options = data.options || [];
    const rerolls = data.rerolls || 0;
    const totalRounds = data.total_rounds || 15;
    const prevPicks = previousDraftState ? (previousDraftState.picks || []).length : -1;
    const iJustPicked = picks.length > prevPicks;
    const shouldAnimate = isReroll || iJustPicked;
    updateDraftInfo(data);
    const optionsEl = $('draft-options');
    if (optionsEl) {
        const optionIds = options.map(opt => {
            if (typeof opt === 'string') return opt;
            return [
                opt.def_id || opt.id || '',
                opt.instance_id || '',
                opt.fusion_level || 1,
                opt.fission_level || 1,
                opt.tomato_level || 0,
                (opt.flags || []).join('|'),
            ].join(':');
        });
        const optionsSignature = JSON.stringify({
            match: phaseContextMatchKey(data),
            lang: currentLang,
            ui: currentUiStyle,
            waiting: picks.length >= totalRounds,
            options: optionIds,
        });
        if (optionsSignature !== lastDraftOptionsSignature) {
            lastDraftOptionsSignature = optionsSignature;
            optionsEl.innerHTML = '';
            if (picks.length >= totalRounds) {
                const myStatus = phase === 'event_sub_choice' ? 'sub_choice' : 'ready';
                const hintText = myStatus === 'sub_choice'
                    ? (UI.status_sub_choice || '配装处理')
                    : (UI.draft_waiting || '等待对方完成选牌');
                optionsEl.innerHTML = `<div class="empty-hint">${hintText}</div>`;
            } else {
                options.forEach((opt, i) => {
                    const card = createCardElement(opt, {});
                    card.style.cursor = 'pointer';
                    card.onclick = () => socket.emit('draft_pick', { def_id: opt.def_id });
                    if (shouldAnimate) {
                        card.style.opacity = '0';
                        card.style.transform = 'scale(0.6)';
                        card.style.transition = 'opacity 0.15s ease-out, transform 0.15s ease-out';
                        if (isReroll) {
                            card.style.transitionDelay = (i * 0.05) + 's';
                        }
                        requestAnimationFrame(() => {
                            requestAnimationFrame(() => {
                                card.style.opacity = '1';
                                card.style.transform = 'scale(1)';
                            });
                        });
                    }
                    optionsEl.appendChild(card);
                });
            }
        }
    }
    const picksEl = $('draft-picks');
    if (picksEl) {
        const setupPreviewCards = Array.isArray(data.setup_preview_cards) && data.setup_preview_cards.length
            ? data.setup_preview_cards
            : null;
        const picksSignature = JSON.stringify({
            match: phaseContextMatchKey(data),
            lang: currentLang,
            ui: currentUiStyle,
            picks,
            setupPreviewCards,
        });
        if (picksSignature !== lastDraftPicksSignature) {
            lastDraftPicksSignature = picksSignature;
            picksEl.innerHTML = '';
            const chipCards = setupPreviewCards || picks.map(defId => ({ def_id: defId }));
            chipCards.forEach(cardDict => {
                const defId = cardDict && cardDict.def_id;
                const cardDef = getCardDef(defId);
                const tag = createCardChoiceChip(cardDict, { includeLayers: false, includeTomato: false });
                tag.classList.add('draft-pick-token');
                if (!cardDef) tag.textContent = defId;
                picksEl.appendChild(tag);
            });
        }
    }
    const rerollBtn = $('btn-draft-reroll');
    if (rerollBtn) {
        const canReroll = rerolls > 0 && picks.length < totalRounds;
        rerollBtn.textContent = `${UI.draft_reroll || '刷新'} (${rerolls})`;
        rerollBtn.disabled = !canReroll;
        rerollBtn.style.opacity = canReroll ? '1' : '0.4';
        rerollBtn.style.cursor = canReroll ? 'pointer' : 'not-allowed';
        rerollBtn.style.pointerEvents = canReroll ? 'auto' : 'none';

        rerollBtn.onclick = function(e) {
            const currentRerolls = draftState ? draftState.rerolls : 0;
            const currentPicks = draftState ? (draftState.picks || []).length : 0;
            const currentTotal = draftState ? (draftState.total_rounds || 15) : 15;
            if (currentRerolls > 0 && currentPicks < currentTotal && socket) {
                socket.emit('draft_reroll');
            }
        };
    }
}

function renderEventSelect(data) {
    showView('view-event-select');
    syncPhaseChatMatch(data || {});
    updatePhaseChatChannelOptions(data || {});
    const events = data.events || [];
    const myPick = data.my_pick;
    const container = $('event-options');
    if (!container) return;
    container.classList.remove('event-reveal-container');
    container.innerHTML = '';
    const rerollBtn = $('btn-event-reroll');
    // If already selected, this render shouldn't happen (player should be in draft view)
    // But just in case, show a simple message
    if (myPick != null) {
        if (rerollBtn) rerollBtn.style.display = 'none';
        let eventName = '?';
        for (const ev of events) {
            if (ev && String(ev.id) === String(myPick)) { eventName = getLocalizedEventText(ev, 'name') || '?'; break; }
        }
        container.innerHTML = `<div class="event-selected">${UI.event_selected.replace('{0}', eventName)}</div>`;
        container.dataset.eventSelectSignature = '';
        return;
    }
    const eventSignature = JSON.stringify({
        lang: currentLang,
        events: events.map(ev => ev ? [
            String(ev.id),
            getLocalizedEventText(ev, 'name') || '',
            getLocalizedEventText(ev, 'desc') || '',
            ev.color || '',
        ] : null),
    });
    if (container.dataset.eventSelectSignature === eventSignature && container.querySelector('.event-options')) {
        const rerolls = Number(data.rerolls || 0);
        if (rerollBtn) {
            const canReroll = rerolls > 0;
            rerollBtn.textContent = `${UI.event_reroll || '刷新'} (${rerolls})`;
            rerollBtn.disabled = !canReroll;
            rerollBtn.style.opacity = canReroll ? '1' : '0.4';
            rerollBtn.style.cursor = canReroll ? 'pointer' : 'not-allowed';
            rerollBtn.style.pointerEvents = canReroll ? 'auto' : 'none';
            rerollBtn.style.display = '';
            rerollBtn.onclick = () => {
                socket.emit('reroll_opening_event');
            };
        }
        return;
    }
    container.dataset.eventSelectSignature = eventSignature;
    const eventsRow = document.createElement('div');
    eventsRow.className = 'event-options';
    events.forEach((ev, i) => {
        if (!ev) return;
        const borderColors = { 1: COLORS.health, 2: COLORS.magic, 3: COLORS.magic, 4: COLORS.fire, 5: COLORS.fire, 6: COLORS.fire, 7: COLORS.fire, 8: COLORS.magic };
        const bc = ev.color || borderColors[ev.id] || COLORS.magic;
        const card = document.createElement('div');
        card.className = 'event-card';
        card.style.borderColor = bc;

        card.innerHTML = `
            <div class="event-header" style="background:${bc}"><span>${i + 1}. ${getLocalizedEventText(ev, 'name') || '?'}</span></div>
            <div class="event-desc">${colorizeCardText(getLocalizedEventText(ev, 'desc') || '')}</div>
        `;
        bindInlineCardChips(card);
        card.onclick = () => onEventSelect(ev.id);
        card.style.cursor = 'pointer';
        card.style.opacity = '0';
        card.style.transform = 'scale(0.6)';
        card.style.transition = 'opacity 0.15s ease-out, transform 0.15s ease-out';
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                card.style.opacity = '1';
                card.style.transform = 'scale(1)';
            });
        });
        eventsRow.appendChild(card);
    });
    container.appendChild(eventsRow);
    // Use the HTML button for reroll (shared refresh count with draft)
    const rerolls = Number(data.rerolls || 0);
    if (rerollBtn) {
        const canReroll = rerolls > 0;
        rerollBtn.textContent = `${UI.event_reroll || '刷新'} (${rerolls})`;
        rerollBtn.disabled = !canReroll;
        rerollBtn.style.opacity = canReroll ? '1' : '0.4';
        rerollBtn.style.cursor = canReroll ? 'pointer' : 'not-allowed';
        rerollBtn.style.pointerEvents = canReroll ? 'auto' : 'none';
        rerollBtn.style.display = '';
        rerollBtn.onclick = () => {
            socket.emit('reroll_opening_event');
        };
    }
}

function renderEventReveal(data) {
    showView('view-event-select');
    syncPhaseChatMatch(data || {});
    updatePhaseChatChannelOptions(data || {});
    const container = $('event-options');
    if (!container) return;
    const rerollBtn = $('btn-event-reroll');
    if (rerollBtn) rerollBtn.style.display = 'none';
    const picks = data.picks || [];
    container.innerHTML = '';
    container.dataset.eventSelectSignature = '';
    container.classList.add('event-reveal-container');
    const title = document.createElement('div');
    title.className = 'event-selected';
    title.textContent = '配装已公开';
    container.appendChild(title);
    const eventsRow = document.createElement('div');
    eventsRow.className = 'event-options event-reveal-options';
    picks.forEach((item) => {
        const ev = item.event || {};
        const bc = ev.color || COLORS.magic;
        const card = document.createElement('div');
        card.className = 'event-card event-reveal-card';
        card.style.borderColor = bc;
        const playerName = item.player_name || `P${(item.player_id || 0) + 1}`;
        card.innerHTML = `
            <div class="event-header" style="background:${bc}"><span>${escapeHtml(playerName)}</span></div>
            <div class="event-desc"><b>${escapeHtml(getLocalizedEventText(ev, 'name') || '?')}</b></div>
            <div class="event-desc">${colorizeCardText(getLocalizedEventText(ev, 'desc') || '')}</div>
            <div class="event-desc">${item.ready ? (UI.status_drafting || '选牌中') : (UI.waiting_opponent || '等待')}</div>
        `;
        bindInlineCardChips(card);
        eventsRow.appendChild(card);
    });
    container.appendChild(eventsRow);
    const actionRow = document.createElement('div');
    actionRow.className = 'event-reveal-actions';
    const btn = document.createElement('button');
    btn.className = 'btn btn-primary event-reveal-start-btn';
    btn.textContent = data.my_ready ? (UI.status_drafting || '选牌中') : (UI.start_draft || '开始选牌');
    btn.disabled = !!data.my_ready;
    btn.onclick = () => {
        if (socket && !data.my_ready) socket.emit('confirm_opening_reveal');
    };
    actionRow.appendChild(btn);
    container.appendChild(actionRow);
}

async function onEventSelect(eventId) {
    // Sub-choices (magic conversion, light conversion, etc.) are deferred
    // until after draft, so we don't prompt for them here
    socket.emit('select_opening_event', { event_id: eventId, sub_choice: null });
    // Server will send draft phase immediately, no need to show waiting
}

async function handleEventSubChoice(data) {
    const eventId = data.event_id;
    const needsSubChoice = data.needs_sub_choice;
    if (!needsSubChoice) {
        // No sub-choice needed, just submit empty
        socket.emit('submit_event_sub_choice', { sub_choice: null });
        updateStatus(UI.event_waiting);
        return;
    }
    // Store data for sub-choice flows
    eventSelectData = data;
    let subChoice = null;
    if (String(eventId) === '2') {
        subChoice = await showMagicConversionFlow();
        if (subChoice === false) subChoice = null;
    } else if (String(eventId) === '3') {
        subChoice = await showLightConversionChoice();
        if (subChoice === false) subChoice = null;
    } else if (String(eventId) === '5') {
        subChoice = await showFatedDrawChoice(eventSelectData.fated_draw_pool || []);
        if (subChoice === false) subChoice = { add_def_ids: [] };
    } else if (String(eventId) === '8') {
        subChoice = await showYggdrasilConversionChoice();
        if (subChoice === false) subChoice = null;
    }
    socket.emit('submit_event_sub_choice', { sub_choice: subChoice });
}

async function showFatedDrawChoice(poolCards) {
    const sourcePool = (poolCards && poolCards.length)
        ? poolCards
        : Object.keys(CARD_DEFS || {}).filter(defId => {
            const cd = getCardDef(defId);
            return cd && defId !== 'Error' && Number(cd.count || 0) > 0;
        });
    const normalizedPool = (sourcePool || [])
        .map(card => typeof card === 'string' ? { def_id: card } : card)
        .filter(card => {
            const cd = getCardDef(card.def_id);
            return cd && card.def_id !== 'Error' && Number(cd.count || 0) > 0;
        })
        .sort((a, b) => compareGalleryCards(a.def_id, b.def_id));
    return new Promise((resolve) => {
        const el = $('game-prompt');
        if (!el) { resolve({ add_def_ids: [] }); return; }
        $('game-prompt-title').textContent = '命运抽签：选择1张牌洗入牌库';
        const optsEl = $('game-prompt-options');
        optsEl.innerHTML = '';
        const selected = [];
        let confirmBtn = null;
        const selectedBox = document.createElement('div');
        selectedBox.className = 'choice-selected-cards';
        selectedBox.style.display = 'flex';
        selectedBox.style.flexWrap = 'wrap';
        selectedBox.style.gap = '6px';
        selectedBox.style.marginBottom = '8px';
        const search = document.createElement('input');
        search.type = 'text';
        search.placeholder = UI.search || '搜索';
        search.style.width = '100%';
        search.style.marginBottom = '8px';
        search.style.padding = '7px 9px';
        search.style.border = '1px solid var(--border-color)';
        search.style.borderRadius = 'var(--radius-sm)';
        search.style.background = 'var(--input-bg, #fff)';
        search.style.color = 'var(--text-color)';
        const list = document.createElement('div');
        list.className = 'fated-draw-card-list';
        list.style.display = 'grid';
        list.style.gridTemplateColumns = 'repeat(auto-fill, minmax(132px, 1fr))';
        list.style.gap = '6px';
        list.style.maxHeight = '44vh';
        list.style.overflow = 'auto';

        function renderSelected() {
            selectedBox.innerHTML = '';
            if (!selected.length) {
                const empty = document.createElement('span');
                empty.className = 'choice-option-detail';
                empty.textContent = '请选择1张牌';
                selectedBox.appendChild(empty);
            }
            selected.forEach((defId, idx) => {
                const chip = createCardChoiceChip({ def_id: defId }, { includeLayers: false, includeTomato: false });
                chip.style.cursor = 'pointer';
                chip.title = UI.cancel || '移除';
                chip.onclick = () => {
                    selected.splice(idx, 1);
                    renderSelected();
                    renderList();
                };
                selectedBox.appendChild(chip);
            });
            if (confirmBtn) {
                confirmBtn.disabled = selected.length !== 1;
            }
        }

        function renderList() {
            const q = search.value.trim().toLowerCase();
            list.innerHTML = '';
            normalizedPool
                .filter(card => !q || cardSearchText(card.def_id).includes(q))
                .forEach(card => {
                    const row = document.createElement('button');
                    row.type = 'button';
                    row.className = 'game-prompt-option';
                    row.style.justifyContent = 'flex-start';
                    row.style.minHeight = '34px';
                    row.disabled = selected.length >= 1;
                    row.appendChild(createCardChoiceChip(card, { includeLayers: true, includeTomato: true }));
                    row.onclick = () => {
                        if (selected.length >= 1) return;
                        selected.push(card.def_id);
                        renderSelected();
                        renderList();
                    };
                    list.appendChild(row);
                });
        }

        optsEl.appendChild(selectedBox);
        optsEl.appendChild(search);
        optsEl.appendChild(list);
        const cancelBtn = $('game-prompt-cancel');
        cancelBtn.classList.add('hidden');
        cancelBtn.style.display = 'none';
        cancelBtn.onclick = null;
        search.oninput = renderList;
        renderSelected();
        renderList();
        confirmBtn = document.createElement('button');
        confirmBtn.className = 'btn btn-primary';
        confirmBtn.textContent = UI.ok;
        confirmBtn.style.marginTop = '10px';
        confirmBtn.disabled = true;
        confirmBtn.onclick = () => {
            if (selected.length !== 1) return;
            removeFloatingCardPreview();
            el.classList.remove('active');
            resolve({ add_def_ids: selected.slice(0, 1) });
        };
        optsEl.appendChild(confirmBtn);
        el.classList.add('active');
        setTimeout(() => search.focus(), 30);
    });
}

async function showMagicConversionFlow() {
    const data = eventSelectData;
    const draftPicks = data.draft_picks || [];
    if (!draftPicks.length) return null;
    const counts = {};
    draftPicks.forEach(d => { counts[d] = (counts[d] || 0) + 1; });
    const cardTypes = Object.keys(counts).sort((a, b) => (getCardName(getCardDef(a)) || a).localeCompare(getCardName(getCardDef(b)) || b));
    const countOptions = [];
    for (let i = 1; i < Math.min(4, cardTypes.length + 1); i++) countOptions.push(String(i));
    const convertCountIdx = await gamePrompt(UI.choose_convert_count, countOptions, { cancellable: false });
    if (convertCountIdx < 0) return false;
    const convertCount = convertCountIdx + 1;
    const conversions = [];
    const remainingCounts = { ...counts };
    for (let i = 0; i < convertCount; i++) {
        const availableTypes = cardTypes.filter(d => (remainingCounts[d] || 0) > 0);
        const availableDisplay = availableTypes.map(did => cardDefChoiceOption(did, { detail: `x${remainingCounts[did]}` }));
        const sourceSel = await gamePrompt(UI.choose_source_card_n.replace('{0}', i + 1), availableDisplay, { cancellable: false });
        if (sourceSel < 0) return false;
        remainingCounts[availableTypes[sourceSel]] = (remainingCounts[availableTypes[sourceSel]] || 0) - 1;
        conversions.push({ source_def_id: availableTypes[sourceSel] });
    }
    return conversions.length ? { conversions } : null;
}

async function showLightConversionChoice() {
    const draftPicks = eventSelectData.draft_picks || [];
    const counts = {};
    draftPicks.forEach(d => { if (d !== 'Light') counts[d] = (counts[d] || 0) + 1; });
    const entries = Object.entries(counts).sort((a, b) => (getCardName(getCardDef(a[0])) || a[0]).localeCompare(getCardName(getCardDef(b[0])) || b[0]));
    if (!entries.length) return null;
    return new Promise((resolve) => {
        const el = $('game-prompt');
        if (!el) { resolve(null); return; }
        cleanupGamePromptTransientButtons();
        $('game-prompt-title').textContent = UI.choose_light_cards + ` (${UI.convert_per_type.replace('{0}', 5)})`;
        const optsEl = $('game-prompt-options');
        optsEl.innerHTML = '';
        const inputs = {};
        const MAX_TOTAL = 5;
        function getTotal(exclude) {
            let t = 0;
            entries.forEach(([did]) => {
                if (did !== exclude) t += Math.max(0, parseInt(inputs[did]?.value) || 0);
            });
            return t;
        }
        entries.forEach(([did, cnt]) => {
            const cd = getCardDef(did);
            const row = document.createElement('div');
            row.className = 'game-prompt-option';
            row.style.cursor = 'default';
            const label = document.createElement('span');
            label.style.flex = '1';
            label.style.display = 'flex';
            label.style.alignItems = 'center';
            label.style.gap = '6px';
            label.textContent = '';
            label.appendChild(createCardChoiceChip({ def_id: did }, { includeLayers: false, includeTomato: false }));
            const count = document.createElement('span');
            count.className = 'choice-option-detail';
            count.textContent = `x${cnt}`;
            label.appendChild(count);
            const input = document.createElement('input');
            input.type = 'number';
            input.min = '0';
            input.max = String(Math.min(cnt, MAX_TOTAL));
            input.value = '0';
            input.style.width = '48px';
            input.style.textAlign = 'center';
            input.style.padding = '4px';
            input.style.fontSize = '13px';
            input.style.fontFamily = 'var(--font-main)';
            input.style.border = '1px solid var(--border-color)';
            input.style.borderRadius = 'var(--radius-sm)';
            input.style.outline = 'none';
            input.addEventListener('click', (e) => e.stopPropagation());
            input.addEventListener('input', () => {
                let val = parseInt(input.value);
                if (isNaN(val) || val < 0) val = 0;
                const othersTotal = getTotal(did);
                const maxAllowed = Math.min(cnt, MAX_TOTAL - othersTotal);
                if (val > maxAllowed) {
                    val = Math.max(0, maxAllowed);
                    input.value = val;
                }
            });
            inputs[did] = input;
            row.appendChild(label);
            row.appendChild(input);
            optsEl.appendChild(row);
        });
        const cancelBtn = $('game-prompt-cancel');
        cancelBtn.textContent = UI.ok;
        cancelBtn.classList.remove('hidden');
        cancelBtn.style.display = '';
        cancelBtn.classList.remove('btn-secondary');
        cancelBtn.classList.add('btn-primary');
        cancelBtn.onclick = (e) => {
            e.stopPropagation();
            el.classList.remove('active');
            cancelBtn.textContent = UI.cancel;
            cancelBtn.classList.remove('btn-primary');
            cancelBtn.classList.add('btn-secondary');
            const convertDefIds = [];
            let total = 0;
            entries.forEach(([did, cnt]) => {
                const val = Math.min(parseInt(inputs[did].value) || 0, Math.min(cnt, MAX_TOTAL - total));
                for (let i = 0; i < val; i++) convertDefIds.push(did);
                total += val;
            });
            resolve({ convert_def_ids: convertDefIds });
        };
        el.classList.add('active');
    });
}

async function showYggdrasilConversionChoice() {
    const draftPicks = eventSelectData.draft_picks || [];
    const counts = {};
    draftPicks.forEach(d => { if (d !== 'Yggdrasil') counts[d] = (counts[d] || 0) + 1; });
    const options = Object.keys(counts).sort((a, b) => (getCardName(getCardDef(a)) || a).localeCompare(getCardName(getCardDef(b)) || b));
    const display = options.map(did => cardDefChoiceOption(did, { detail: `x${counts[did]}` }));
    const sel = await gamePrompt(UI.choose_yggdrasil_card, display, { cancellable: false });
    if (sel < 0 || sel >= options.length) return false;
    return { yggdrasil_convert_def_id: options[sel] };
}

async function showCardConversionChoice(draftPicks, maxCount, title) {
    const counts = {};
    draftPicks.forEach(d => {
        if (d === 'Light' && maxCount === 5) return;
        counts[d] = (counts[d] || 0) + 1;
    });
    const entries = Object.entries(counts).sort((a, b) => (getCardName(getCardDef(a[0])) || a[0]).localeCompare(getCardName(getCardDef(b[0])) || b[0]));
    const display = entries.map(([did, cnt]) => cardDefChoiceOption(did, { detail: `x${cnt}` }));
    const sel = await gamePrompt(title + ` (${UI.convert_per_type.replace('{0}', maxCount)})`, display);
    if (sel < 0) return false;
    return null;
}

function debugLayout() {
    const gc = document.querySelector('.game-container');
    const view = document.getElementById('view-game');
    const app = document.getElementById('app');
    const oppSection = gc ? gc.querySelector('.opp-section') : null;
    const playerSection = gc ? gc.querySelector('.player-section') : null;
    const middleSection = gc ? gc.querySelector('.middle-section') : null;
    const battleLog = gc ? gc.querySelector('.battle-log') : null;
    const logContent = gc ? gc.querySelector('.log-content') : null;
    const logHeader = gc ? gc.querySelector('.log-header') : null;
    
    debugLog('[LAYOUT DEBUG] =====');
    debugLog('[LAYOUT DEBUG] app: display=', app ? getComputedStyle(app).display : '?',
                'height=', app ? app.clientHeight : '?',
                'computedH=', app ? getComputedStyle(app).height : '?');
    debugLog('[LAYOUT DEBUG] view-game: display=', view ? getComputedStyle(view).display : '?',
                'flex=', view ? getComputedStyle(view).flex : '?',
                'height=', view ? view.clientHeight : '?',
                'computedH=', view ? getComputedStyle(view).height : '?');
    debugLog('[LAYOUT DEBUG] game-container: display=', gc ? getComputedStyle(gc).display : '?',
                'gridRows=', gc ? getComputedStyle(gc).gridTemplateRows : '?',
                'height=', gc ? gc.clientHeight : '?',
                'computedH=', gc ? getComputedStyle(gc).height : '?');
    debugLog('[LAYOUT DEBUG] opp-section: gridRow=', oppSection ? getComputedStyle(oppSection).gridRow : '?',
                'height=', oppSection ? oppSection.offsetHeight : '?');
    debugLog('[LAYOUT DEBUG] middle-section: gridRow=', middleSection ? getComputedStyle(middleSection).gridRow : '?',
                'display=', middleSection ? getComputedStyle(middleSection).display : '?',
                'flexDir=', middleSection ? getComputedStyle(middleSection).flexDirection : '?',
                'height=', middleSection ? middleSection.offsetHeight : '?',
                'computedH=', middleSection ? getComputedStyle(middleSection).height : '?');
    debugLog('[LAYOUT DEBUG] player-section: gridRow=', playerSection ? getComputedStyle(playerSection).gridRow : '?',
                'height=', playerSection ? playerSection.offsetHeight : '?');
    debugLog('[LAYOUT DEBUG] battle-log: flex=', battleLog ? getComputedStyle(battleLog).flex : '?',
                'height=', battleLog ? battleLog.offsetHeight : '?',
                'computedH=', battleLog ? getComputedStyle(battleLog).height : '?');
    debugLog('[LAYOUT DEBUG] log-header: height=', logHeader ? logHeader.offsetHeight : '?');
    debugLog('[LAYOUT DEBUG] log-content: flex=', logContent ? getComputedStyle(logContent).flex : '?',
                'maxHeight=', logContent ? getComputedStyle(logContent).maxHeight : '?',
                'height=', logContent ? logContent.offsetHeight : '?',
                'computedH=', logContent ? getComputedStyle(logContent).height : '?');
    debugLog('[LAYOUT DEBUG] sum=', (oppSection ? oppSection.offsetHeight : 0) + (middleSection ? middleSection.offsetHeight : 0) + (playerSection ? playerSection.offsetHeight : 0));
}

function adjustCardSize() {
    const gc = document.querySelector('.game-container');
    if (!gc) return;
    const oppSection = gc.querySelector('.opp-section');
    const playerSection = gc.querySelector('.player-section');
    if (!oppSection || !playerSection) return;
    const gcHeight = gc.clientHeight;
    if (gcHeight <= 0) return;
    const oppH = oppSection.offsetHeight;
    const playerH = playerSection.offsetHeight;
    const totalNeeded = oppH + playerH;
    if (totalNeeded <= gcHeight) return;
    const currentCardW = gc.querySelector('.card') ? gc.querySelector('.card').offsetWidth : 100;
    const scale = gcHeight / totalNeeded;
    const newW = Math.max(40, Math.floor(currentCardW * scale * 0.9));
    gc.style.setProperty('--card-w', newW + 'px');
    requestAnimationFrame(() => {
        const oppH2 = oppSection.offsetHeight;
        const playerH2 = playerSection.offsetHeight;
        const total2 = oppH2 + playerH2;
        if (total2 > gcHeight) {
            const newerW = Math.max(40, Math.floor(newW * gcHeight / total2 * 0.9));
            gc.style.setProperty('--card-w', newerW + 'px');
        }
    });
}

let _adjustTimer = null;
function scheduleAdjust() {
    if (_adjustTimer) clearTimeout(_adjustTimer);
    _adjustTimer = setTimeout(() => {
        adjustCardSize();
        _adjustTimer = null;
    }, 80);
}

function isMyTurn() {
    if (!gameState) return false;
    if (playerId < 0) return false;
    return gameState.phase === 'action' && gameState.current_player === playerId;
}

function isUrfEquipmentSellable(eq) {
    const inst = (eq && eq.card_instance) || {};
    const cardDef = getCardDef(inst.def_id);
    const flags = new Set([
        ...((cardDef && cardDef.flags) || []),
        ...((inst && inst.instance_flags) || []),
    ]);
    return !flags.has('indestructible');
}

function chatChannelOptionLabel(key) {
    return `[${t(key)}]`;
}

function chatPlayerNameFromContext(ctx, id) {
    const names = ctx && Array.isArray(ctx.player_names) ? ctx.player_names : null;
    if (names && names[id]) return localizeCanonicalPlayerName(names[id]);
    return getPlayerNameById(id);
}

function populateChatChannelSelect(select, ctx) {
    if (!select) return;
    const mode = String((ctx && ctx.mode) || '');
    const show = mode === '2v2' && !!(ctx && !ctx.spectating && !isSpectating && ctx.phase !== 'game_over');
    select.classList.toggle('hidden', !show);
    select.disabled = !show;
    select.title = UI.chat_channel_label;
    select.setAttribute('aria-label', UI.chat_channel_label);
    if (!show) {
        if (select.dataset.signature !== 'hidden') {
            select.innerHTML = '';
            select.dataset.signature = 'hidden';
        }
        select.value = 'public';
        return;
    }

    const previous = select.value || 'public';
    const options = [
        { value: 'public', label: chatChannelOptionLabel('chat_channel_public') },
        { value: 'team', label: chatChannelOptionLabel('chat_channel_team') },
        { value: 'enemy', label: chatChannelOptionLabel('chat_channel_enemy') },
    ];
    const enemyIds = (ctx.enemy_ids || []).map(normalizePlayerId).filter(id => id !== null);
    enemyIds.forEach(id => {
        options.push({
            value: `private:${id}`,
            label: `[${tf('chat_channel_private_to', chatPlayerNameFromContext(ctx, id))}]`,
        });
    });
    const signature = JSON.stringify(options);
    if (select.dataset.signature === signature) {
        select.value = options.some(option => option.value === previous) ? previous : 'public';
        return;
    }

    select.innerHTML = '';
    options.forEach(optionData => {
        const option = document.createElement('option');
        option.value = optionData.value;
        option.textContent = optionData.label;
        select.appendChild(option);
    });
    select.dataset.signature = signature;
    select.value = options.some(option => option.value === previous) ? previous : 'public';
}

function ensureGameChatChannelSelect() {
    let select = $('game-chat-channel');
    if (select) return select;
    const input = $('game-chat-input');
    if (!input || !input.parentNode) return null;
    select = document.createElement('select');
    select.id = 'game-chat-channel';
    select.className = 'game-chat-channel hidden';
    select.setAttribute('aria-label', UI.chat_channel_label);
    input.parentNode.insertBefore(select, input);
    return select;
}

function updateGameChatChannelOptions(gs) {
    const select = ensureGameChatChannelSelect();
    populateChatChannelSelect(select, gs);
}

function currentPhaseChatContext() {
    if (phase === 'draft') return draftState || {};
    if (phase === 'event_select') return eventSelectData || {};
    return {};
}

function phaseContextMatchKey(ctx) {
    if (!ctx) return '';
    return String(ctx.match_key || (ctx.room_id != null ? `room:${ctx.room_id}` : ''));
}

function syncPhaseChatMatch(ctx) {
    const key = phaseContextMatchKey(ctx);
    if (key && phaseChatMatchKey && phaseChatMatchKey !== key) {
        phaseChatEntries = [];
        pregameChatEntries = [];
    }
    if (key) {
        phaseChatMatchKey = key;
        pregameChatMatchKey = key;
    }
}

function resetMatchRuntimeState(options = {}) {
    if (targetPickCleanup) {
        try { targetPickCleanup(); } catch (_) {}
        targetPickCleanup = null;
    }
    cleanupDragState();
    clearScheduledGameOver();
    clearPendingServerAction();
    clearSelectedPlayCard({ skipRender: true });
    removeFloatingCardPreview();
    hideGameAlert();
    responsePending = false;
    responseData = {};
    choicePending = false;
    choiceData = {};
    activeV2UiRequestId = null;
    pendingPlayCard = null;
    optimisticResourceOverride = null;
    pendingLocalResourceCosts = [];
    pendingOptimisticResourceCosts = [];
    hasPlayerHandSnapshot = false;
    recentlyPlayedExileCards.clear();
    lastRenderedTurnKey = '';
    lastStatusSignatures.clear();
    if (responseTimerId) {
        clearInterval(responseTimerId);
        responseTimerId = null;
    }
    if (allyConsentTimerId) {
        clearInterval(allyConsentTimerId);
        allyConsentTimerId = null;
    }
    if (surrenderConsentTimerId) {
        clearInterval(surrenderConsentTimerId);
        surrenderConsentTimerId = null;
    }
    if (cardAnimationUnlockTimer) {
        clearTimeout(cardAnimationUnlockTimer);
        cardAnimationUnlockTimer = null;
    }
    cardAnimationLockUntil = 0;
    const responsePanel = $('response-panel');
    if (responsePanel) {
        responsePanel.innerHTML = '';
        responsePanel.classList.add('hidden');
    }
    const prompt = $('game-prompt');
    if (prompt) prompt.classList.remove('active');
    const dropOverlay = $('card-drop-overlay');
    if (dropOverlay) dropOverlay.classList.add('hidden');
    const mobileBar = $('mobile-play-confirm');
    if (mobileBar) mobileBar.classList.add('hidden');
    const aim = $('classic-aim-layer');
    if (aim) aim.classList.add('hidden');
    document.body.classList.remove('server-action-pending', 'card-dragging');
    if (options.clearGameState) {
        gameState = {};
    }
    updateBlindVisualClasses({});
}

function syncBattleLogMatch(ctx) {
    const key = phaseContextMatchKey(ctx);
    if (!key) return;
    if (renderedBattleLogMatchKey !== key) {
        const container = $('battle-log');
        const content = container ? container.querySelector('.log-content') : null;
        if (renderedBattleLogMatchKey) {
            resetMatchRuntimeState({ clearGameState: true });
        }
        resetBattleLogState(content);
        renderedBattleLogMatchKey = key;
        lastDraftOptionsSignature = '';
        lastDraftPicksSignature = '';
    }
}

function updatePhaseChatChannelOptions(ctx = currentPhaseChatContext()) {
    populateChatChannelSelect($('phase-chat-channel'), ctx);
}

function updatePhaseChatPanelVisibility(viewId) {
    const panel = $('phase-chat-panel');
    if (!panel) return;
    const show = viewId === 'view-draft' || viewId === 'view-event-select';
    panel.classList.toggle('hidden', !show);
    if (show) {
        const title = $('phase-chat-title');
        if (title) title.textContent = UI.chat_title;
        updatePhaseChatChannelOptions();
        renderPhaseChat();
    }
}

function makeChatTimelineEntry(nick, text, meta = {}, channelMeta = {}) {
    return {
        type: 'chat',
        nick,
        text,
        message_id: meta.message_id || meta.messageId || '',
        sender_user_id: meta.sender_user_id || meta.senderUserId || meta.user_id || '',
        sender_name: meta.sender_name || meta.senderName || meta.nickname || nick,
        nickname: meta.nickname || nick,
        system: !!meta.system,
        isAdmin: isAdminPlayer(meta),
        specialRoleColor: getSpecialRoleColor(meta),
        channel: channelMeta.chat_channel || channelMeta.channel || '',
        targetName: channelMeta.chat_target_name || channelMeta.targetName || '',
    };
}

function renderPhaseChat() {
    const container = $('phase-chat-log');
    if (!container) return;
    container.innerHTML = '';
    const fragment = document.createDocumentFragment();
    phaseChatEntries.forEach(entry => fragment.appendChild(createBattleLogElement(entry)));
    container.appendChild(fragment);
    container.scrollTop = container.scrollHeight;
}

function appendPhaseChat(nick, text, meta = {}, channelMeta = {}) {
    const ctx = currentPhaseChatContext();
    syncPhaseChatMatch(ctx);
    const entry = makeChatTimelineEntry(nick, text, meta, channelMeta);
    phaseChatEntries.push(entry);
    if (phaseChatEntries.length > 120) phaseChatEntries.shift();
    pregameChatEntries.push(entry);
    if (pregameChatEntries.length > 120) pregameChatEntries.shift();
    renderPhaseChat();
}

function seedPregameChatEntriesForBattleLog() {
    if (!pregameChatEntries.length) return;
    const matchKey = phaseContextMatchKey(gameState);
    if (pregameChatMatchKey && matchKey && pregameChatMatchKey !== matchKey) return;
    if (gameTimelineEntries.some(entry => entry && entry.pregameChatSeed)) return;
    pregameChatEntries.forEach((entry, index) => {
        gameTimelineEntries.push({ ...entry, pregame: true, pregameChatSeed: index === 0 });
    });
}

function applyChatChannelPayload(payload, selectId) {
    const channelSelect = $(selectId);
    if (channelSelect && !channelSelect.disabled && !channelSelect.classList.contains('hidden')) {
        const value = channelSelect.value || 'public';
        if (value.startsWith('private:')) {
            payload.channel = 'private';
            payload.target_player_id = Number(value.slice('private:'.length));
        } else {
            payload.channel = value;
        }
    }
    return payload;
}

function updateModeSpecificControls(gs) {
    const inSoloGame = !!gs?.solo;
    const inTutorial = !!gs?.tutorial || tutorialMode;
    const gameOver = gs?.phase === 'game_over';
    const soloNextDrawBtn = $('btn-solo-next-draw');
    const soloEditBtn = $('btn-solo-edit');
    const viewDeckBtn = $('btn-view-deck');
    const spectateViewDeckBtn = $('btn-spectate-view-deck');
    const urfReplaceBtn = $('btn-urf-replace');
    const urfSellBtn = $('btn-urf-sell');
    const surrenderBtn = $('btn-surrender');
    const spectateControls = $('spectate-controls');
    const gameControls = $('game-controls');
    const playZone = $('play-zone');
    const controlsRight = document.querySelector('.controls-right');

    const showSoloNextDraw = inSoloGame && !inTutorial && !gameOver && !isSpectating && !replayMode;
    const showSoloEdit = inSoloGame && !inTutorial && !isSpectating && !replayMode;
    const showSpectateControls = !!isSpectating;
    const showGameControls = !isSpectating && !replayMode;
    const showPlayZone = !isSpectating;

    if (soloNextDrawBtn) {
        soloNextDrawBtn.classList.toggle('hidden', !showSoloNextDraw);
        soloNextDrawBtn.style.display = showSoloNextDraw ? '' : 'none';
    }
    if (soloEditBtn) {
        soloEditBtn.classList.toggle('hidden', !showSoloEdit);
        soloEditBtn.style.display = showSoloEdit ? '' : 'none';
    }
    if (surrenderBtn) {
        const showSurrender = !inSoloGame && !gameOver;
        surrenderBtn.classList.toggle('hidden', !showSurrender);
        surrenderBtn.style.display = showSurrender ? '' : 'none';
    }
    if (viewDeckBtn) {
        const showViewDeck = gs?.mode !== 'urf';
        viewDeckBtn.classList.toggle('hidden', !showViewDeck);
        viewDeckBtn.style.display = showViewDeck ? '' : 'none';
    }
    if (spectateViewDeckBtn) {
        const showSpectateViewDeck = isSpectating && gs?.mode !== 'urf';
        spectateViewDeckBtn.classList.toggle('hidden', !showSpectateViewDeck);
        spectateViewDeckBtn.style.display = showSpectateViewDeck ? '' : 'none';
    }
    if (urfReplaceBtn) {
        const show = gs?.mode === 'urf' && !isSpectating && !gameOver;
        urfReplaceBtn.textContent = UI.urf_replace || '替换手牌';
        urfReplaceBtn.title = '';
        urfReplaceBtn.classList.toggle('hidden', !show);
        urfReplaceBtn.style.display = show ? '' : 'none';
        urfReplaceBtn.disabled = !isMyTurn() || isActionBusy({ includeAnimation: false }) || !gs?.urf_replace_available;
    }
    if (urfSellBtn) {
        const show = gs?.mode === 'urf' && !isSpectating && !gameOver;
        const sellableEquipment = ((gs.you || {}).equipment || []).filter(isUrfEquipmentSellable);
        urfSellBtn.textContent = UI.urf_sell || '售卖装备';
        urfSellBtn.title = '';
        urfSellBtn.classList.toggle('hidden', !show);
        urfSellBtn.style.display = show ? '' : 'none';
        urfSellBtn.disabled = !isMyTurn() || isActionBusy({ includeAnimation: false }) || !gs?.urf_sell_available || !sellableEquipment.length;
    }
    if (spectateControls) {
        spectateControls.classList.toggle('hidden', !showSpectateControls);
        spectateControls.style.display = showSpectateControls ? '' : 'none';
    }
    const switchBtn = $('btn-switch-perspective');
    if (switchBtn) {
        const count = Array.isArray(gs?.spectate_players) ? gs.spectate_players.length : 0;
        const showSwitch = isSpectating && count > 1;
        switchBtn.dataset.dynamic = showSwitch ? '1' : '';
        switchBtn.classList.toggle('hidden', !showSwitch);
        switchBtn.style.display = showSwitch ? '' : 'none';
        if (showSwitch) {
            const current = getSpectatePerspectivePlayer(gs);
            switchBtn.textContent = current && current.name
                ? `${UI.switch_perspective}: ${localizeCanonicalPlayerName(current.name)}`
                : UI.switch_perspective;
        }
    }
    const leaveBtn = $('btn-leave-spectate');
    if (leaveBtn && replayMode) leaveBtn.textContent = UI.close || 'Close';
    if (gameControls) gameControls.style.display = showGameControls ? '' : 'none';
    if (playZone) playZone.style.display = showPlayZone ? '' : 'none';
    if (controlsRight) controlsRight.style.display = replayMode ? 'none' : '';
    updateGameChatChannelOptions(gs);
}

function setClassicControlButton(id, visible, options = {}) {
    const btn = $(id);
    if (!btn) return false;
    btn.classList.toggle('hidden', !visible);
    btn.style.display = visible ? '' : 'none';
    if (options.text != null) btn.textContent = options.text;
    if (options.title != null) btn.title = options.title;
    btn.disabled = !!options.disabled;
    return !!visible;
}

function updateClassicExtraControls(gs) {
    const panel = $('classic-extra-controls');
    if (!panel) return;
    const inSoloGame = !!gs?.solo;
    const inTutorial = !!gs?.tutorial || tutorialMode;
    const gameOver = gs?.phase === 'game_over';
    const isUrf = gs?.mode === 'urf';
    const myTurn = isMyTurn();
    const busy = isActionBusy({ includeAnimation: false });
    let visibleCount = 0;
    const spectatePlayerCount = Array.isArray(gs?.spectate_players) ? gs.spectate_players.length : 0;
    const currentSpectatePlayer = getSpectatePerspectivePlayer(gs);

    if (setClassicControlButton('classic-switch-perspective', isSpectating && spectatePlayerCount > 1, {
        text: currentSpectatePlayer && currentSpectatePlayer.name
            ? `${UI.switch_perspective}: ${localizeCanonicalPlayerName(currentSpectatePlayer.name)}`
            : UI.switch_perspective,
        disabled: false,
    })) visibleCount += 1;
    const classicSwitch = $('classic-switch-perspective');
    if (classicSwitch) classicSwitch.dataset.dynamic = (isSpectating && spectatePlayerCount > 1) ? '1' : '';

    if (setClassicControlButton('classic-view-deck', !isUrf, {
        text: UI.view_deck,
        disabled: false,
    })) visibleCount += 1;
    if (setClassicControlButton('classic-solo-next-draw', inSoloGame && !inTutorial && !gameOver && !isSpectating, {
        text: UI.set_next_draw,
        disabled: busy,
    })) visibleCount += 1;
    if (setClassicControlButton('classic-solo-edit', inSoloGame && !inTutorial && !isSpectating, {
        text: UI.pause_edit,
        disabled: busy,
    })) visibleCount += 1;

    const showUrf = isUrf && !isSpectating && !gameOver;
    if (setClassicControlButton('classic-urf-replace', showUrf, {
        text: UI.urf_replace || '替换手牌',
        disabled: !myTurn || busy || !gs?.urf_replace_available,
    })) visibleCount += 1;

    const sellableEquipment = ((gs?.you || {}).equipment || []).filter(isUrfEquipmentSellable);
    if (setClassicControlButton('classic-urf-sell', showUrf, {
        text: UI.urf_sell || '售卖装备',
        disabled: !myTurn || busy || !gs?.urf_sell_available || !sellableEquipment.length,
    })) visibleCount += 1;

    panel.classList.toggle('hidden', visibleCount === 0);
}

function formatPlayerPileInfo(playerData, includeDiscard, opponentStyle = false) {
    const blindLevel = getOwnBlindLevel();
    const pid = normalizePlayerId(playerData && playerData.player_id);
    const isSelf = pid != null && pid === normalizePlayerId(gameState && gameState.your_id);
    if (blindLevel >= 3) {
        const text = includeDiscard ? UI.hand_deck_discard_info.replace('{0}', '?').replace('{1}', '?').replace('{2}', '?')
            : UI.hand_deck_info_opp.replace('{0}', '?').replace('{1}', '?');
        return { text, title: '', opponentStyle };
    }
    const hand = playerData.hand_count || 0;
    const deck = playerData.deck_count || 0;
    const discard = playerData.discard_count || 0;
    const full = includeDiscard
        ? UI.hand_deck_discard_info.replace('{0}', hand).replace('{1}', deck).replace('{2}', discard)
        : UI.hand_deck_info_opp.replace('{0}', hand).replace('{1}', deck);
    if (!isMinimalUiStyle()) return { text: full, title: '' };
    const compact = includeDiscard ? `✦${hand} ▣${deck} ⟲${discard}` : `✦${hand} ▣${deck}`;
    return { text: compact, title: full, opponentStyle };
}

function setPileInfoText(el, info) {
    if (!el || !info) return;
    el.textContent = info.text;
    el.title = info.title || '';
    el.classList.toggle('compact-info', !!info.title);
}

function getBattlePlayerId(gs, slot) {
    if (!gs) return null;
    if (slot === 'self') return normalizePlayerId(gs.your_id);
    if (slot === 'enemy') {
        if (gs.mode === '2v2') return normalizePlayerId((gs.enemy_ids || [])[0]);
        const yourId = normalizePlayerId(gs.your_id);
        if (yourId == null) return null;
        return yourId === 1 ? 0 : 1;
    }
    return null;
}

function normalizeBattlePlayer(gs, raw, slot) {
    const data = raw || {};
    const id = getBattlePlayerId(gs, slot);
    const name = slot === 'self'
        ? (gs.your_name || data.name || UI.you)
        : (gs.opponent_name || data.name || UI.opponent);
    return {
        id,
        name: localizeCanonicalPlayerName(name),
        avatar_url: data.avatar_url || data.avatar || '',
        avatar_id: data.avatar_id || '',
        skin: normalizeSkinConfig(data.skin || (Array.isArray(gs.player_skins) && id != null ? gs.player_skins[id] : null)),
        skin_look: resolveSkinLookForPlayer(id, data.skin_look || (Array.isArray(gs.player_skin_looks) && id != null ? gs.player_skin_looks[id] : null)),
        hp: Number(data.health || 0),
        maxHp: Number(data.max_health || 100),
        e: Number(data.elixir || 0),
        maxE: Number(data.max_elixir || 10),
        m: Number(data.magic || 0),
        maxM: Number(data.max_magic || 10),
        armor: Number(data.armor || 0),
        statuses: data,
        equipment: Array.isArray(data.equipment) ? data.equipment : [],
        hasCorruptionEquipment: playerHasCorruptionEquipment(data),
        handCount: Number(data.hand_count || 0),
        deckCount: Number(data.deck_count || 0),
        discardCount: Number(data.discard_count || 0),
        exileCount: Number(data.exile_count || 0),
        isCurrent: normalizePlayerId(gs.current_player) === id,
        isDefeated: Number(data.health || 0) <= 0,
        raw: data,
    };
}

function normalizeBattleCard(cardDict, ownerState) {
    const card = cardDict || {};
    const cardDef = getCardDef(card.def_id || '');
    const costs = cardDef ? getCardDisplayCosts(card, cardDef, ownerState) : { totalE: 0, totalM: 0, flags: new Set() };
    const image = card.image || card.image_url || (cardDef && (cardDef.image || cardDef.image_url)) || '';
    const blindLevel = cardDef ? getCardBlindLevelForSelf(card) : 0;
    return {
        ...card,
        def_id: card.def_id || '',
        instance_id: card.instance_id,
        name: cardDef ? getBlindedCardDisplayName(card, cardDef) : (card.def_id || '?'),
        card_type: cardDef ? cardDef.card_type : '',
        cost_e: costs.totalE,
        cost_m: costs.totalM,
        effect_text: cardDef ? getCardEffectText(cardDef) : '',
        description: cardDef ? getCardDescriptionText(cardDef) : '',
        flags: Array.from(costs.flags || []),
        image,
        image_url: image,
        blind_level: blindLevel,
        cardDef,
        raw: card,
    };
}

function buildBattleViewModel(state) {
    const gs = state || {};
    const you = gs.you || {};
    const opponent = gs.opponent || {};
    const self = normalizeBattlePlayer(gs, you, 'self');
    const enemy = normalizeBattlePlayer(gs, opponent, 'enemy');
    const hand = (you.hand || []).map(card => normalizeBattleCard(card, you));
    const selected = hand.find(card => card.instance_id === selectedPlayCardId) || null;
    const phaseText = gs.phase === 'action'
        ? (isMyTurn() ? UI.your_turn : UI.opponent_turn)
        : gs.phase === 'draw' ? UI.draw_phase
        : gs.phase === 'response' ? UI.waiting_response
        : gs.phase === 'choice' ? UI.choose_target
        : gs.phase === 'draft' ? UI.draft_phase
        : gs.phase === 'event_select' ? UI.select_event
        : gs.phase === 'game_over' ? UI.game_over
        : (gs.phase || '');
    return {
        self,
        enemy,
        hand,
        selectedCard: selected,
        turn: {
            round: Number(gs.round_num || 0),
            phase: gs.phase || '',
            phaseText,
            currentPlayer: normalizePlayerId(gs.current_player),
            isMyTurn: isMyTurn(),
            mode: gs.mode || '',
            modeText: gs.mode === 'urf' ? '无限火力' : (gs.mode === '2v2' ? '2v2' : '1v1'),
        },
        pendingResponse: gs.pending_response || (responsePending ? responseData : null),
        playableCards: new Set((you.hand || []).filter(canPlayCard).map(card => card.instance_id)),
        log: Array.isArray(gs.log) ? gs.log : [],
        deckCount: Number(you.deck_count || (you.deck || []).length || 0),
        discardCount: Number(you.discard_count || (you.discard || []).length || 0),
        exileCount: Number(you.exile_count || (you.exile || []).length || 0),
        raw: gs,
    };
}

function shouldUseClassicBattle(gs) {
    if (!isClassicBattleUiStyle() || !gs) return false;
    if (isSpectating || gs.mode === '2v2') return false;
    return ['action', 'draw', 'response', 'choice', 'game_over'].includes(gs.phase);
}

function hashStringToHue(value) {
    const text = String(value || '?');
    let hash = 0;
    for (let i = 0; i < text.length; i++) {
        hash = ((hash << 5) - hash + text.charCodeAt(i)) | 0;
    }
    return Math.abs(hash) % 360;
}

function renderPlayerAvatar(player, options = {}) {
    const p = player || {};
    const hue = hashStringToHue(p.name);
    const initial = String(p.name || '?').trim().slice(0, 1).toUpperCase() || '✿';
    const active = p.isCurrent ? ' is-current' : '';
    const defeated = p.isDefeated ? ' is-defeated' : '';
    const targetable = options.targetable ? ' is-targetable' : '';
    const style = `--avatar-hue:${hue};--avatar-color:hsl(${hue} 62% 52%);--avatar-color-2:hsl(${(hue + 44) % 360} 70% 58%)`;
    const image = p.avatar_url ? `<img class="player-avatar-img" src="${escapeHtml(p.avatar_url)}" alt="">` : '';
    const skinHtml = renderSkinAvatar(p.skin || DEFAULT_SKIN_CONFIG, {
        playerId: p.id,
        look: resolveSkinLookForPlayer(p.id, p.skin_look),
        defeated: p.isDefeated,
        defeatedSeed: `${p.id ?? ''}:${p.name || ''}`,
        corrupted: !!p.hasCorruptionEquipment,
        animateCorruption: shouldAnimateSkinCorruption(p.id, !!p.hasCorruptionEquipment, 'classic'),
    });
    const skinClass = image ? '' : ' has-skin';
    return `
        <div class="player-avatar${skinClass}${active}${defeated}${targetable}" style="${style}">
            ${image || skinHtml || `<div class="player-avatar-flower"><span>${escapeHtml(initial)}</span></div>`}
        </div>
    `;
}

function renderMiniPlayerSkin(containerId, playerData = {}, id = null) {
    const el = $(containerId);
    if (!el) return;
    const data = playerData || {};
    const pid = normalizePlayerId(id != null ? id : data.player_id);
    const corrupted = playerHasCorruptionEquipment(data);
    el.innerHTML = renderSkinAvatar(data.skin || DEFAULT_SKIN_CONFIG, {
        playerId: pid,
        look: resolveSkinLookForPlayer(pid, data.skin_look),
        defeated: Number(data.health || 0) <= 0 || !!data.isDefeated || !!data.is_defeated,
        defeatedSeed: `${pid ?? ''}:${data.name || data.player_name || ''}`,
        corrupted,
        animateCorruption: shouldAnimateSkinCorruption(pid, corrupted, containerId || 'mini'),
    });
}

function renderClassicStatusList(player) {
    const tmp = document.createElement('div');
    renderStatusTagsToElement(tmp, player && player.raw ? player.raw : {});
    return tmp.innerHTML || '<span class="classic-empty-mark">-</span>';
}

function renderStatusTagsToElement(container, playerData) {
    if (!container) return;
    const tempId = `classic-status-${Math.random().toString(36).slice(2)}`;
    container.id = tempId;
    const restore = {
        parent: container.parentNode,
        next: container.nextSibling,
    };
    if (!container.parentNode) {
        container.style.position = 'absolute';
        container.style.left = '-9999px';
        container.style.top = '-9999px';
        document.body.appendChild(container);
    }
    renderStatusTags(tempId, playerData || {});
    lastStatusSignatures.delete(tempId);
    container.removeAttribute('id');
    if (!restore.parent) {
        container.remove();
        container.style.position = '';
        container.style.left = '';
        container.style.top = '';
    } else if (restore.next && container.nextSibling !== restore.next) {
        restore.parent.insertBefore(container, restore.next);
    }
}

function renderClassicEquipmentList(player) {
    const equipment = (player && player.equipment) || [];
    if (!equipment.length) return '<span class="classic-empty-mark">-</span>';
    return equipment.map(eq => {
        const cardInst = eq.card_instance || {};
        const cardDef = getCardDef(cardInst.def_id || '');
        const name = cardDef ? getCardName(cardDef) : (cardInst.def_id || '?');
        const typeColor = cardDef ? (CARD_TYPE_COLORS[cardDef.card_type] || COLORS.text_primary) : COLORS.text_primary;
        const instanceId = cardInst.instance_id != null ? String(cardInst.instance_id) : '';
        return `<span class="classic-equip-chip" data-instance-id="${escapeHtml(instanceId)}" style="--chip-color:${typeColor}">${getEquipmentIconHtml(cardInst, cardDef)}<span class="classic-equip-name">${escapeHtml(name)}</span></span>`;
    }).join('');
}

function attachClassicEquipmentPreviews(container, player) {
    if (!container || !player) return;
    const equipment = (player.equipment || []);
    container.querySelectorAll('.classic-equip-chip[data-instance-id]').forEach(chip => {
        const instanceId = Number(chip.dataset.instanceId);
        const eq = equipment.find(item => {
            const cardInst = item && (item.card_instance || item.card || item);
            return Number(cardInst && cardInst.instance_id) === instanceId;
        });
        const cardInst = eq && (eq.card_instance || eq.card || eq);
        if (cardInst && cardInst.def_id) {
            attachFloatingCardPreview(chip, cardInst);
            attachTermIntroToCard(chip, cardInst);
        }
    });
}

function attachClassicStatusIntros(container) {
    if (!container) return;
    container.querySelectorAll('.classic-status-ring .status-tag').forEach(tag => {
        attachTermIntroToStatus(tag, {
            key: tag.dataset.statusKey || '',
            name: tag.dataset.statusName || tag.textContent || '',
            val: tag.dataset.statusValue || '',
            fg: tag.style.color || '',
        });
    });
}

function renderClassicResourceOrbs(container, current, max, spend = 0, kind = 'e', masked = false) {
    if (!container) return;
    container.classList.toggle('blind-resource-masked', !!masked);
    if (masked) {
        container.dataset.current = '?';
        container.dataset.max = '?';
        container.dataset.spend = '0';
        container.textContent = '?';
        return;
    }
    const cur = Math.max(0, Number(current) || 0);
    const total = Math.max(0, Math.min(16, Number(max) || 0));
    const cost = Math.max(0, Number(spend) || 0);
    container.dataset.current = String(cur);
    container.dataset.max = String(total);
    container.dataset.spend = String(cost);
    container.innerHTML = '';
    for (let i = 0; i < total; i++) {
        const orb = document.createElement('span');
        orb.className = `classic-orb classic-orb-${kind}`;
        if (i < cur) orb.classList.add('is-filled');
        if (cost && i >= Math.max(0, cur - cost) && i < cur) orb.classList.add('will-spend');
        if (cost && i >= cur && i < cost) orb.classList.add('is-missing');
        container.appendChild(orb);
    }
    if (!total) container.textContent = '0';
}

function getClassicResourcePreviewCard(vm = null) {
    if (vm && vm.selectedCard) return vm.selectedCard;
    const selected = getSelectedClassicCard();
    if (selected) return selected;
    const hoverId = classicHoveredCardId == null ? null : Number(classicHoveredCardId);
    if (hoverId == null || !Number.isFinite(hoverId)) return null;
    if (vm && Array.isArray(vm.hand)) {
        const found = vm.hand.find(card => Number(card.instance_id) === hoverId);
        if (found) return found;
    }
    const raw = ((gameState && gameState.you && gameState.you.hand) || []).find(card => Number(card.instance_id) === hoverId);
    return raw ? normalizeBattleCard(raw, (gameState && gameState.you) || {}) : null;
}

function applyClassicResourcePreview(card = null, ownerState = null) {
    const root = $('battle-classic');
    const you = ownerState || ((gameState && gameState.you) || {});
    const preview = card || null;
    const costE = preview ? Number(preview.cost_e || 0) : 0;
    const costM = preview ? Number(preview.cost_m || 0) : 0;
    const missing = !!preview && (costE > Number(you.elixir || 0) || costM > Number(you.magic || 0));
    if (root) {
        root.classList.toggle('has-resource-preview', !!preview);
        root.classList.toggle('has-missing-resource', missing);
    }
    renderClassicResourceOrbs($('classic-e-orbs'), you.elixir, you.max_elixir, costE, 'e');
    renderClassicResourceOrbs($('classic-m-orbs'), you.magic, you.max_magic, costM, 'm');
}

function getClassicPlayRole(card) {
    const type = card && card.card_type;
    if (type === 'thorn') return 'enemy';
    if (type === 'root') return 'equip';
    if (type === 'bloom') {
        const cardDef = card.cardDef || getCardDef(card.def_id || '');
        if (cardEffectTargetsEnemy(cardDef)) return 'enemy';
        return 'self';
    }
    return 'stage';
}

function cardEffectTargetsEnemy(cardDef) {
    if (!cardDef) return false;
    const ids = new Set(['Iris', 'Fire', 'Cancer']);
    if (ids.has(cardDef.id)) return true;
    const inspect = (value) => {
        if (value == null) return false;
        if (typeof value === 'string') return ['enemy', 'target', 'all_enemies', 'random_enemy'].includes(value);
        if (Array.isArray(value)) return value.some(inspect);
        if (typeof value === 'object') return Object.entries(value).some(([key, child]) => {
            if (['target', 'targets', 'target1', 'target2', 'items'].includes(key) && inspect(child)) return true;
            return inspect(child);
        });
        return false;
    };
    if (inspect(cardDef.effects || [])) return true;
    if (inspect(cardDef.scripts || {})) return true;
    const v2Events = (cardDef.v2_events && typeof cardDef.v2_events === 'object')
        ? cardDef.v2_events
        : ((cardDef.v2_resource && cardDef.v2_resource.events && typeof cardDef.v2_resource.events === 'object')
            ? cardDef.v2_resource.events
            : {});
    return inspect(v2Events);
}

function getClassicPlayHint(card) {
    if (!card) return UI.classic_select_card || UI.your_turn;
    if (isClassicSelfOnlyCard(card)) return UI.classic_target_self || UI.classic_play_center || UI.drag_to_play;
    const role = getClassicPlayRole(card);
    if (role === 'enemy') return UI.classic_target_enemy || UI.drag_to_play;
    if (role === 'self') return UI.classic_target_self || UI.drag_to_play;
    if (role === 'equip') return UI.classic_equip_stage || UI.drag_to_play;
    return UI.classic_play_center || UI.drag_to_play;
}

function renderClassicPlayLane(vm) {
    const lane = $('classic-play-lane');
    if (!lane) return;
    const selected = vm && vm.selectedCard;
    const role = getClassicPlayRole(selected);
    const selfOnly = isClassicSelfOnlyCard(selected);
    lane.classList.toggle('is-armed', !!selected && (selfOnly || role === 'stage'));
    lane.classList.toggle('is-aim-passive', !!selected && !selfOnly && role !== 'stage');
    lane.classList.toggle('is-self-only', !!selected && selfOnly);
    lane.classList.toggle('is-equip-role', role === 'equip');
    lane.classList.toggle('is-self-role', role === 'self');
    lane.classList.toggle('is-enemy-role', role === 'enemy');
    const text = selected ? getClassicPlayHint(selected) : (UI.classic_select_card || UI.drag_to_play);
    lane.innerHTML = `
        <div class="classic-lane-mark" aria-hidden="true"></div>
        <div class="classic-lane-text">${escapeHtml(text)}</div>
    `;
}

function removeClassicHoverInfo() {
    if (classicHoverPreviewTimer) {
        clearTimeout(classicHoverPreviewTimer);
        classicHoverPreviewTimer = null;
    }
    if (classicHoverInfoEl) {
        classicHoverInfoEl.remove();
        classicHoverInfoEl = null;
    }
}

function positionClassicHoverInfo(anchor) {
    if (!classicHoverInfoEl || !anchor) return;
    const rect = anchor.getBoundingClientRect();
    const width = classicHoverInfoEl.offsetWidth || 260;
    const height = classicHoverInfoEl.offsetHeight || 140;
    const gap = Math.max(14, Math.min(28, rect.width * 0.18));
    let left = rect.right + gap;
    if (left + width > window.innerWidth - 8) left = rect.left - width - gap;
    let top = rect.top + rect.height * 0.5 - height * 0.5;
    left = Math.max(8, Math.min(window.innerWidth - width - 8, left));
    top = Math.max(8, Math.min(window.innerHeight - height - 8, top));
    classicHoverInfoEl.style.left = `${left}px`;
    classicHoverInfoEl.style.top = `${top}px`;
}

function showClassicHoverInfo(card, anchor) {
    if (!card || !card.def_id || !anchor) return;
    if (window.matchMedia && window.matchMedia('(hover: none), (pointer: coarse)').matches) return;
    const cardDef = card.cardDef || getCardDef(card.def_id || '');
    if (!cardDef) return;
    removeClassicHoverInfo();
    const blindLevel = getCardBlindLevelForSelf(card.raw || card);
    const typeColor = getCardBlindDisplayColor(cardDef, blindLevel);
    const preview = document.createElement('div');
    preview.className = 'card-hold-preview classic-hover-info';
    if (blindLevel > 0) preview.classList.add('card-hold-preview-blinded');
    preview.style.setProperty('--preview-color', typeColor);
    preview.innerHTML = buildCardHoldPreviewHtml(cardDef, blindLevel > 0);
    document.body.appendChild(preview);
    classicHoverInfoEl = preview;
    positionClassicHoverInfo(anchor);
    requestAnimationFrame(() => {
        positionClassicHoverInfo(anchor);
        preview.classList.add('active');
    });
}

function renderClassicFighter(container, player, side, selectedCard = null) {
    if (!container) return;
    const hpPct = player.maxHp > 0 ? Math.max(0, Math.min(100, (player.hp / player.maxHp) * 100)) : 0;
    const role = getClassicPlayRole(selectedCard);
    const selfOnly = isClassicSelfOnlyCard(selectedCard);
    const isHardTarget = !!selectedCard && !selfOnly && (role === side || (role === 'enemy' && side === 'enemy') || (role === 'self' && side === 'self'));
    const isSelfOnlyTarget = !!selectedCard && selfOnly && side === 'self';
    const isSoftTarget = (!!selectedCard && !selfOnly && role === 'equip' && side === 'self') || isSelfOnlyTarget;
    container.classList.toggle('is-current', !!player.isCurrent);
    container.classList.toggle('is-defeated', !!player.isDefeated);
    container.classList.toggle('is-play-target', isHardTarget);
    container.classList.toggle('is-soft-target', isSoftTarget);
    container.classList.toggle('is-self-only-target', isSelfOnlyTarget);
    const intentText = side === 'enemy'
        ? (player.isCurrent ? (UI.opponent_turn || 'Opponent') : (selectedCard && role === 'enemy' ? (UI.classic_target_enemy || '') : ''))
        : (player.isCurrent ? (UI.your_turn || 'Your turn') : (selectedCard && !selfOnly && (role === 'self' || role === 'equip') ? getClassicPlayHint(selectedCard) : ''));
    container.innerHTML = `
        <div class="classic-fighter-name">${escapeHtml(player.name || '?')}</div>
        ${intentText ? `<div class="classic-intent-badge">${escapeHtml(intentText)}</div>` : '<div class="classic-intent-badge is-empty"></div>'}
        ${renderPlayerAvatar(player)}
        <div class="classic-hp-wrap" data-bar-key="health" data-bar-label="H" data-bar-armor="${Number(player.armor || 0)}">
            <div class="classic-hp-track"><div class="classic-hp-fill" style="width:${hpPct}%"></div></div>
            <div class="classic-hp-text">H ${player.hp}/${player.maxHp}${player.armor ? ` · A ${player.armor}` : ''}</div>
        </div>
        <div class="classic-status-ring">${renderClassicStatusList(player)}</div>
        <div class="classic-equipment-ring">${renderClassicEquipmentList(player)}</div>
    `;
    attachClassicEquipmentPreviews(container, player);
    attachClassicStatusIntros(container);
}

function renderClassicHand(vm) {
    const container = $('classic-hand-fan');
    if (!container) return;
    removeClassicHoverInfo();
    const oldRects = new Map();
    container.querySelectorAll('.classic-hand-card[data-instance-id]').forEach(el => {
        oldRects.set(String(el.dataset.instanceId), el.getBoundingClientRect());
    });
    container.innerHTML = '';
    const hand = vm.hand || [];
    const count = hand.length;
    hand.forEach((card, index) => {
        const rawCard = card.raw || card;
        const cardDef = getCardDef(rawCard.def_id || '');
        const playable = vm.playableCards.has(card.instance_id);
        const offset = index - (count - 1) / 2;
        const rotate = Math.max(-13, Math.min(13, offset * 4.2));
        const lift = Math.max(0, 18 - Math.abs(offset) * 4);
        const wrap = document.createElement('div');
        wrap.className = 'classic-hand-card';
        wrap.dataset.instanceId = card.instance_id == null ? '' : String(card.instance_id);
        wrap.dataset.defId = card.def_id;
        wrap.style.setProperty('--fan-rot', `${rotate}deg`);
        wrap.style.setProperty('--fan-rot-inverse', `${-rotate}deg`);
        wrap.style.setProperty('--fan-y', `${-lift}px`);
        wrap.style.setProperty('--fan-z', String(100 + Math.round(20 - Math.abs(offset))));
        if (!playable) wrap.classList.add('card-disabled');
        if (selectedPlayCardId === card.instance_id) wrap.classList.add('is-selected');
        const cardEl = createCardElement(rawCard, {
            draggable: false,
            onClick: playable
                ? (event) => selectClassicPlayCard(card.instance_id, event)
                : () => flashStatus(getCannotPlayReason(rawCard), 2200, 'error'),
            ownerState: vm.self.raw || gameState.you || {},
            prediction: getCardPredictionOptionsForOwner(rawCard, vm.self.raw || gameState.you || {}),
        });
        cardEl.classList.add('classic-fan-card-inner');
        wrap.appendChild(cardEl);
        wrap.addEventListener('mouseenter', () => {
            removeClassicHoverInfo();
            classicHoveredCardId = card.instance_id;
            if (!selectedPlayCardId) applyClassicResourcePreview(card, gameState && gameState.you);
            classicHoverPreviewTimer = setTimeout(() => {
                classicHoverPreviewTimer = null;
                showClassicHoverInfo(card, wrap);
            }, 200);
        });
        wrap.addEventListener('mousemove', () => {
            if (classicHoverInfoEl) positionClassicHoverInfo(wrap);
        });
        wrap.addEventListener('mouseleave', () => {
            const leavingId = classicHoveredCardId;
            removeClassicHoverInfo();
            if (leavingId === card.instance_id) {
                classicHoveredCardId = null;
                applyClassicResourcePreview(getSelectedClassicCard(), gameState && gameState.you);
            }
        });
        container.appendChild(wrap);
    });
}

function renderClassicLog(vm) {
    const content = $('classic-log-content');
    if (!content) return;
    const drawer = $('classic-log-drawer') || content.closest('.classic-log-drawer');
    if (drawer) drawer.classList.toggle('blind-log-masked', getOwnBlindLevel() >= 2);
    const entries = gameTimelineEntries.length
        ? gameTimelineEntries.slice(-80)
        : (vm.log || []).slice(-80).map(text => ({ type: 'battle', text }));
    const signature = `${currentLang}|${entries.map(entry => {
        if (!entry) return '';
        if (entry.type === 'chat') {
            return `c:${entry.channel || ''}:${entry.nick || ''}:${entry.text || ''}:${entry.system ? 1 : 0}:${entry.isAdmin ? 1 : 0}:${entry.specialRoleColor || ''}`;
        }
        return `b:${entry.text || ''}`;
    }).join('\n')}`;
    if (content.dataset.renderSignature === signature) return;
    const wasAtBottom = content.scrollTop + content.clientHeight >= content.scrollHeight - 30;
    content.innerHTML = '';
    entries.forEach(entry => content.appendChild(createBattleLogElement(entry)));
    content.dataset.renderSignature = signature;
    renderedClassicLogSignature = signature;
    if (wasAtBottom) content.scrollTop = content.scrollHeight;
}

function renderClassicBattle(gs) {
    const root = $('battle-classic');
    const oldContainer = document.querySelector('.game-container');
    if (!root || !oldContainer) return false;
    if (!shouldUseClassicBattle(gs)) {
        root.classList.add('hidden');
        root.setAttribute('aria-hidden', 'true');
        oldContainer.classList.remove('classic-battle-hidden');
        return false;
    }
    try {
        const vm = buildBattleViewModel(gs);
        root.classList.remove('hidden');
        root.setAttribute('aria-hidden', 'false');
        oldContainer.classList.add('classic-battle-hidden');
        const selected = vm.selectedCard;
        const resourcePreviewCard = getClassicResourcePreviewCard(vm);
        const selectedRole = getClassicPlayRole(selected);
        const selectedSelfOnly = isClassicSelfOnlyCard(selected);
        const missingResource = !!resourcePreviewCard && ((Number(resourcePreviewCard.cost_e || 0) > Number(vm.self.e || 0)) || (Number(resourcePreviewCard.cost_m || 0) > Number(vm.self.m || 0)));
        root.classList.toggle('has-selected-card', !!selected);
        root.classList.toggle('has-resource-preview', !!resourcePreviewCard);
        root.classList.toggle('has-missing-resource', missingResource);
        root.classList.toggle('is-aiming', !!selected);
        root.classList.toggle('is-self-only-aim', !!selected && selectedSelfOnly);
        root.classList.toggle('is-target-aim', !!selected && !selectedSelfOnly);
        root.dataset.selectedRole = selected ? selectedRole : '';
        $('classic-mode').textContent = vm.turn.modeText || '1v1';
        $('classic-round').textContent = formatCompactRoundStatus(gs, vm.turn.phaseText);
        $('classic-phase').textContent = vm.turn.phaseText || '';
        $('classic-action-hint').textContent = selected ? getClassicPlayHint(selected) : (vm.turn.isMyTurn ? UI.your_turn : UI.opponent_turn);
        const blindLevel = getOwnBlindLevel();
        const maskOwnResources = blindLevel >= 2;
        const maskOwnPiles = blindLevel >= 3;
        renderClassicResourceOrbs($('classic-e-orbs'), vm.self.e, vm.self.maxE, resourcePreviewCard ? resourcePreviewCard.cost_e : 0, 'e', maskOwnResources);
        renderClassicResourceOrbs($('classic-m-orbs'), vm.self.m, vm.self.maxM, resourcePreviewCard ? resourcePreviewCard.cost_m : 0, 'm', maskOwnResources);
        $('classic-deck-count').textContent = `▣${maskOwnPiles ? '?' : vm.deckCount}`;
        $('classic-discard-count').textContent = `⟲${maskOwnPiles ? '?' : vm.discardCount}`;
        $('classic-exile-count').textContent = `◇${maskOwnPiles ? '?' : vm.exileCount}`;
        renderClassicFighter($('classic-fighter-self'), vm.self, 'self', selected);
        renderClassicFighter($('classic-fighter-enemy'), vm.enemy, 'enemy', selected);
        renderClassicPlayLane(vm);
        renderClassicHand(vm);
        renderClassicLog(vm);
        if (selected) scheduleClassicAimCurveUpdate();
        else {
            const aim = $('classic-aim-layer');
            if (aim) aim.classList.add('hidden');
        }
        const endBtn = $('classic-end-turn');
        if (endBtn) {
            endBtn.textContent = UI.end_turn;
            endBtn.disabled = !vm.turn.isMyTurn || isActionBusy({ includeAnimation: false }) || gs.phase === 'game_over';
            endBtn.classList.toggle('is-ready', !endBtn.disabled);
        }
        updateClassicExtraControls(gs);
        return true;
    } catch (error) {
        console.error('[classic-ui] render failed', error);
        root.classList.add('hidden');
        root.setAttribute('aria-hidden', 'true');
        oldContainer.classList.remove('classic-battle-hidden');
        return false;
    }
}

function renderGame(data) {
    cleanupDragState();
    showView('view-game');
    const gs = data || gameState;
    const you = gs.you || {};
    const opp = gs.opponent || {};
    const opp2 = gs.opponent2 || {};
    const teammate = gs.teammate || {};
    const is2v2 = gs.mode === '2v2';
    const myTurn = isMyTurn();
    debugLog('[RENDER] renderGame: phase=', gs.phase, 'current_player=', gs.current_player, 'playerId=', playerId, 'myTurn=', myTurn, 'is2v2=', is2v2);

    const gameContainer = document.querySelector('.game-container');
    if (gameContainer) {
        if (is2v2) {
            gameContainer.classList.add('mode-2v2');
        } else {
            gameContainer.classList.remove('mode-2v2');
        }
        gameContainer.classList.toggle('mode-spectate', !!isSpectating);
        gameContainer.classList.toggle('mode-tutorial', !!gs.tutorial || tutorialMode);
        gameContainer.classList.toggle('mode-solo', !!gs.solo);
        gameContainer.classList.toggle('mode-urf', gs.mode === 'urf');
        gameContainer.classList.toggle('mode-replay', !!replayMode || !!gs.replay_mode);
    }

    const opp2Half = $('opp2-half');
    const oppDivider = $('opp-divider');
    const teammateSidebar = $('teammate-sidebar');
    if (opp2Half) opp2Half.classList.toggle('hidden', !is2v2);
    if (oppDivider) oppDivider.classList.toggle('hidden', !is2v2);
    if (teammateSidebar) teammateSidebar.classList.toggle('hidden', !is2v2);
    syncPlayerRegionTargets(gs);
    maybeAnimateTurnFocus(gs);

    const oppLabel = $('opp-label');
    const youLabel = $('you-label');
    const makeNamePayload = (name, isAdmin, special = {}) => ({
        nickname: name,
        is_admin_player: !!(isAdmin || (special && special.is_admin_player)),
        ...(special || {}),
    });
    const setGameNameLabel = (el, name, isAdmin, special = {}) => {
        setPlayerNameContent(el, makeNamePayload(name, isAdmin, special), { adminPrefix: false });
    };
    if (isSpectating) {
        if (is2v2) {
            if (youLabel) setGameNameLabel(youLabel, gs.your_name || gs.player1_name || 'P1', gs.your_is_admin_player || gs.player1_is_admin_player, gs.your_special || gs.player1_special);
            if (oppLabel) setGameNameLabel(oppLabel, (gs.opponent_names || [])[0] || gs.player3_name || 'P3', (gs.opponent_admin_flags || [])[0] || gs.player3_is_admin_player, (gs.opponent_specials || [])[0] || gs.player3_special);
            const opp2Label = $('opp2-label');
            if (opp2Label) setGameNameLabel(opp2Label, (gs.opponent_names || [])[1] || gs.player4_name || 'P4', (gs.opponent_admin_flags || [])[1] || gs.player4_is_admin_player, (gs.opponent_specials || [])[1] || gs.player4_special);
            const tmLabel = $('teammate-label');
            if (tmLabel) setGameNameLabel(tmLabel, gs.teammate_name || gs.player2_name || 'P2', gs.teammate_is_admin_player || gs.player2_is_admin_player, gs.teammate_special || gs.player2_special);
        } else {
            if (oppLabel) setGameNameLabel(oppLabel, gs.opponent_name || gs.player2_name || 'P2', gs.opponent_is_admin_player || gs.player2_is_admin_player, gs.opponent_special || gs.player2_special);
            if (youLabel) setGameNameLabel(youLabel, gs.your_name || gs.player1_name || 'P1', gs.your_is_admin_player || gs.player1_is_admin_player, gs.your_special || gs.player1_special);
        }
    } else if (is2v2) {
        const oppNames = gs.opponent_names || [];
        if (oppLabel) setGameNameLabel(oppLabel, oppNames[0] || UI.opponent, (gs.opponent_admin_flags || [])[0], (gs.opponent_specials || [])[0]);
        const opp2Label = $('opp2-label');
        if (opp2Label) setGameNameLabel(opp2Label, oppNames[1] || (UI.opponent + '2'), (gs.opponent_admin_flags || [])[1], (gs.opponent_specials || [])[1]);
        const tmLabel = $('teammate-label');
        if (tmLabel) setGameNameLabel(tmLabel, gs.teammate_name || UI.teammate, gs.teammate_is_admin_player, gs.teammate_special);
        if (youLabel) setGameNameLabel(youLabel, gs.your_name || UI.you, gs.your_is_admin_player, gs.your_special);
    } else {
        if (oppLabel) setGameNameLabel(oppLabel, gs.opponent_name || UI.opponent, gs.opponent_is_admin_player, gs.opponent_special);
        if (youLabel) setGameNameLabel(youLabel, gs.your_name || UI.you, gs.your_is_admin_player, gs.your_special);
    }
    if (!!gs.solo && gs.phase === 'game_over') {
        const winner = gs.winner;
        const youResult = winner === -1 ? UI.draw : (winner === playerId ? UI.victory : UI.defeat);
        const oppResult = winner === -1 ? UI.draw : (winner === playerId ? UI.defeat : UI.victory);
        if (youLabel) youLabel.textContent = `${localizeCanonicalPlayerName(gs.your_name || UI.you)} - ${youResult}`;
        if (oppLabel) oppLabel.textContent = `${localizeCanonicalPlayerName(gs.opponent_name || UI.opponent)} - ${oppResult}`;
    }

    const yourPlayerId = normalizePlayerId(gs.your_id);
    const enemyIdsForSkin = Array.isArray(gs.enemy_ids) ? gs.enemy_ids.map(normalizePlayerId) : [];
    const opponentSkinId = is2v2 ? enemyIdsForSkin[0] : (yourPlayerId === 1 ? 0 : 1);
    renderMiniPlayerSkin('opp-skin', opp, opponentSkinId);
    renderMiniPlayerSkin('you-skin', you, yourPlayerId);
    renderMiniPlayerSkin('opp2-skin', opp2, enemyIdsForSkin[1]);
    renderMiniPlayerSkin('teammate-skin', teammate, gs.teammate_id);
    updateBlindVisualClasses(gs);

    renderPlayerBars('opp-bars', opp);
    renderPlayerBars('you-bars', getOptimisticPlayerBarsData(you));
    renderStatusTags('opp-status', opp);
    renderStatusTags('you-status', you);
    renderOppHand(opp);
    renderPlayerHand(you);
    renderEquipment('opp-equip', opp, false);
    renderEquipment('you-equip', you, true);

    if (is2v2) {
        renderPlayerBars('opp2-bars', opp2);
        renderStatusTags('opp2-status', opp2);
        renderOppHand(opp2, 'opp2-hand');
        renderEquipment('opp2-equip', opp2, false);
        renderPlayerBars('teammate-bars', teammate);
        renderStatusTags('teammate-status', teammate);
        renderTeammateHand(teammate);
        renderEquipment('teammate-equip', teammate, false);
        const opp2Info = $('opp2-info');
        if (opp2Info) setPileInfoText(opp2Info, formatPlayerPileInfo(opp2, false, true));
        const tmInfo = $('teammate-info');
        if (tmInfo) setPileInfoText(tmInfo, formatPlayerPileInfo(teammate, true));
    }

    renderLog(gs.log || [], gs.log_start || 0, gs.log_total);

    let phaseText;
    if (is2v2) {
        const cpName = gs.current_player === playerId ? localizeCanonicalPlayerName(gs.your_name || UI.you) :
            (gs.current_player === gs.teammate_id ? localizeCanonicalPlayerName(gs.teammate_name || UI.teammate) :
            localizeCanonicalPlayerName((gs.opponent_names || [])[gs.enemy_ids ? gs.enemy_ids.indexOf(gs.current_player) : -1] || '...'));
        phaseText = gs.phase === 'action' ? (myTurn ? UI.your_turn : `${UI.opponent_turn}：${cpName}`)
            : gs.phase === 'draw' ? UI.draw_phase
            : gs.phase === 'game_over' ? UI.game_over : '';
    } else {
        phaseText = gs.phase === 'action' ? (myTurn ? UI.your_turn : UI.opponent_turn)
            : gs.phase === 'draw' ? UI.draw_phase
            : gs.phase === 'game_over' ? UI.game_over : '';
    }
    const fullRoundStatus = formatRoundStatus(gs, phaseText);
    updateStatus(isMinimalUiStyle() ? formatCompactRoundStatus(gs, phaseText) : fullRoundStatus);
    const statusTextEl = $('status-text');
    if (statusTextEl) statusTextEl.title = isMinimalUiStyle() ? fullRoundStatus : '';

    const endTurnBtn = $('btn-end-turn');
    if (endTurnBtn) {
        endTurnBtn.disabled = !myTurn || isSpectating || gs.phase === 'game_over' || isActionBusy({ includeAnimation: false });
    }
    const inSoloGame = !!gs.solo;
    const playZone = $('play-zone');
    if (playZone) {
        if (myTurn && !isSpectating) {
            playZone.classList.add('active');
        } else {
            playZone.classList.remove('active');
        }
    }
    if (pendingPlayCard) {
        renderPendingCard();
    } else if (playZone) {
        playZone.innerHTML = `<div class="play-zone-hint">${UI.drag_to_play}</div>`;
    }
    updateDropOverlayContent();
    if (inSoloGame && gs.phase === 'game_over' && playZone) {
        playZone.innerHTML = `
            <div class="solo-gameover-actions">
                <button class="btn btn-primary" onclick="startSoloTraining()">${UI.rematch}</button>
                <button class="btn btn-secondary" onclick="showSoloTraining()">${UI.return_lobby}</button>
            </div>
        `;
    }
    updateModeSpecificControls(gs);
    const oppInfo = $('opp-info');
    if (oppInfo) {
        oppInfo.style.display = gs.mode === 'urf' ? 'none' : '';
        if (gs.mode === 'urf') {
            oppInfo.textContent = '';
            oppInfo.title = '';
            oppInfo.classList.remove('compact-info');
        } else {
            setPileInfoText(oppInfo, formatPlayerPileInfo(opp, false, true));
        }
    }
    const youInfo = $('you-info');
    if (youInfo) {
        youInfo.style.display = gs.mode === 'urf' ? 'none' : '';
        if (gs.mode === 'urf') {
            youInfo.textContent = '';
            youInfo.title = '';
            youInfo.classList.remove('compact-info');
        } else {
            setPileInfoText(youInfo, formatPlayerPileInfo(you, true));
        }
    }
    scheduleAdjust();
    renderClassicBattle(gs);
    updateMinimalPlayCancelZone();
}

function renderPlayerBars(containerId, playerData) {
    const container = $(containerId);
    if (!container) return;
    container.dataset.playerBars = '1';
    const blindLevel = getOwnBlindLevel();
    const pid = normalizePlayerId(playerData && playerData.player_id);
    const region = container.closest('[data-player-target-region], .player-section, .opp-half, #teammate-sidebar, #classic-fighter-self, #classic-fighter-enemy');
    if (region && pid != null) {
        region.dataset.playerTargetRegion = region.dataset.playerTargetRegion || '1';
        region.dataset.playerId = String(pid);
    }
    const isSelf = pid != null && pid === normalizePlayerId(gameState && gameState.your_id);
    const masked = (isSelf && blindLevel >= 2) || (!isSelf && blindLevel >= 3);
    container.classList.toggle('blind-resource-masked', masked);
    const bars = [
        { key: 'health', cur: playerData.health || 0, max: playerData.max_health || 100, color: COLORS.health, bg: COLORS.health_bg, label: 'H' },
        { key: 'elixir', cur: playerData.elixir || 0, max: playerData.max_elixir || 10, color: COLORS.elixir, bg: COLORS.elixir_bg, label: 'E' },
        { key: 'magic', cur: playerData.magic || 0, max: playerData.max_magic || 10, color: COLORS.magic, bg: COLORS.magic_bg, label: 'M' },
    ];
    if (container.children.length !== bars.length) {
        container.innerHTML = '';
        bars.forEach(bar => {
            const wrapper = document.createElement('div');
            wrapper.className = 'bar-wrapper';
            wrapper.dataset.barKey = bar.key;
            wrapper.innerHTML = `
                <span class="bar-label" style="color:${bar.color}">${bar.label}</span>
                <div class="bar-track" style="background:${bar.bg}">
                    <div class="bar-fill" style="background:${bar.color};width:0%"></div>
                    <span class="bar-text">0/0</span>
                </div>
            `;
            container.appendChild(wrapper);
        });
    }
    const wrappers = container.querySelectorAll('.bar-wrapper');
    bars.forEach((bar, i) => {
        if (!wrappers[i]) return;
        wrappers[i].dataset.barKey = bar.key;
        const fill = wrappers[i].querySelector('.bar-fill');
        const text = wrappers[i].querySelector('.bar-text');
        const pct = bar.max > 0 ? Math.max(0, Math.min(100, (bar.cur / bar.max) * 100)) : 0;
        if (fill) fill.style.width = masked ? '0%' : pct + '%';
        if (text) text.textContent = masked ? '?' : `${bar.cur}/${bar.max}`;
        wrappers[i].classList.toggle('blind-masked', masked);
    });
}

function renderStatusTags(containerId, playerData) {
    const container = $(containerId);
    if (!container) return;
    container.innerHTML = '';
    const tags = [];
    const p = playerData;
    const maskStatusValues = getOwnBlindLevel() >= 3;
    const hideStatusIntro = getOwnBlindLevel() >= 3;
    const customStatuses = (p.custom_statuses && typeof p.custom_statuses === 'object') ? p.custom_statuses : {};
    const customCount = (...keys) => {
        for (const key of keys) {
            const value = Number(customStatuses[key] || 0);
            if (Number.isFinite(value) && value > 0) return value;
        }
        return 0;
    };
    if (p.poison > 0) tags.push({ key: 'poison', name: UI.status_poison, abbr: 'P', val: p.poison, fg: COLORS.poison, bg: COLORS.poison_bg });
    if (p.fire > 0) tags.push({ key: 'fire', name: UI.status_fire, abbr: 'F', val: p.fire, fg: COLORS.fire, bg: COLORS.fire_bg });
    if (p.toxic > 0) tags.push({ key: 'toxic', name: UI.status_toxic, abbr: 'T', val: p.toxic, fg: '#6C3483', bg: '#F4ECF7' });
    if (p.triangle_stacks > 0) tags.push({ key: 'triangle', name: UI.status_triangle, abbr: '△', val: p.triangle_stacks, fg: COLORS.non_stack, bg: COLORS.non_stack_bg });
    if (p.nazar_active) tags.push({ key: 'nazar', name: UI.status_nazar, abbr: 'Nz', val: `${p.nazar_big_hits || 0}/2`, fg: COLORS.magic_text, bg: COLORS.magic_bg });
    if (p.equipment_protection > 0) tags.push({ key: 'equip_protect', name: UI.status_equip_protect, abbr: 'EP', val: p.equipment_protection, fg: COLORS.indestructible, bg: COLORS.indestructible_bg });
    if (p.invincible) tags.push({ key: 'invincible', name: UI.status_invincible, abbr: 'Inv', val: '', fg: COLORS.elixir_text, bg: COLORS.elixir_bg });
    const statusImmune = customCount('status_immune', 'immune', '状态免疫');
    if (statusImmune > 0) tags.push({ key: 'status_immune', name: UI.status_immune || '状态免疫', abbr: 'Imm', val: '', fg: '#16A085', bg: '#E8F8F5' });
    if (p.skip_turn > 0) tags.push({ key: 'stunned', name: UI.status_stunned, abbr: 'Stn', val: p.skip_turn, fg: COLORS.damage, bg: COLORS.damage_bg });
    const attackBlocked = Math.max(Number(p.attack_blocked || 0), customCount('attack_blocked', '禁攻'));
    const attackOnly = Math.max(Number(p.attack_only || 0), customCount('attack_only', '仅攻击'));
    if (attackBlocked > 0) tags.push({ key: 'attack_blocked', name: UI.status_attack_blocked, abbr: 'NoT', val: attackBlocked, fg: '#C0392B', bg: '#FDEDEC' });
    if (attackOnly > 0) tags.push({ key: 'attack_only', name: UI.status_attack_only, abbr: 'TOnly', val: attackOnly, fg: '#D35400', bg: '#FEF5E7' });
    if (p.untargetable) tags.push({ key: 'untargetable', name: UI.status_untargetable, abbr: 'Unt', val: '', fg: '#1A5276', bg: '#EBF5FB' });
    if (p.bandage_active) tags.push({ key: 'bandage', name: UI.status_bandage, abbr: 'Bdg', val: '', fg: '#1E8449', bg: '#E8F8F5' });
    if (p.sponge_active) tags.push({ key: 'sponge', name: UI.status_sponge, abbr: 'Spg', val: '', fg: '#6C3483', bg: '#F4ECF7' });
    if (p.sluggish > 0) tags.push({ key: 'sluggish', name: UI.status_sluggish, abbr: 'Slg', val: p.sluggish, fg: '#E67E22', bg: '#FEF5E7' });
    if (p.overload > 0) tags.push({ key: 'overload', name: UI.status_overload, abbr: 'Ovl', val: p.overload, fg: '#C0392B', bg: '#FDEDEC' });
    if (p.foresight > 0) tags.push({ key: 'foresight', name: UI.status_foresight, abbr: 'Fsi', val: p.foresight, fg: '#2980B9', bg: '#EBF5FB' });
    if (p.fracture > 0) tags.push({ key: 'fracture', name: UI.status_fracture, abbr: 'Frc', val: p.fracture, fg: '#7F8C8D', bg: '#F2F3F4' });
    if (p.stagnation > 0) tags.push({ key: 'stagnation', name: UI.status_stagnation, abbr: 'Stg', val: p.stagnation, fg: '#9B59B6', bg: '#F4ECF7' });
    if (p.blind > 0) tags.push({ key: 'blind', name: UI.status_blind, abbr: 'Bln', val: p.blind, fg: '#2C3E50', bg: '#EBEDEF' });
    if (p.heal_block > 0) tags.push({ key: 'heal_block', name: UI.status_heal_block, abbr: 'HB', val: p.heal_block, fg: '#E84393', bg: '#FDEDF2' });
    if (p.weakness > 0) tags.push({ key: 'weakness', name: UI.status_weakness, abbr: 'Wk', val: p.weakness, fg: '#8E44AD', bg: '#F4ECF7' });
    if (p.bleed > 0) tags.push({ key: 'bleed', name: UI.status_bleed, abbr: 'Bld', val: p.bleed, fg: '#922B21', bg: '#FDEDEC' });
    if (p.fragment_stacks > 0) tags.push({ key: 'fragment', name: UI.status_fragment, abbr: 'Frg', val: p.fragment_stacks, fg: '#795548', bg: '#EFEBE9' });
    const customStatusSum = (...keys) => keys.reduce((sum, key) => sum + Number(customStatuses[key] || 0), 0);
    const customStatusMax = (...keys) => keys.reduce((max, key) => Math.max(max, Number(customStatuses[key] || 0)), 0);
    const turnHealTurns = customStatusSum('jungle:turn_heal_turns', 'turn_heal_turns');
    const turnHealPower = customStatusMax('jungle:turn_heal_power', 'turn_heal_power');
    if (turnHealTurns > 0 && turnHealPower > 0) {
        tags.push({ key: 'jungle:turn_heal_turns', name: '回合回复', abbr: 'Reg', val: `${turnHealTurns};${turnHealPower}`, fg: '#F48FB1', bg: '#FDEDF2' });
    }
    const turnMagicTurns = customStatusSum('jungle:turn_magic_turns', 'turn_magic_turns');
    const turnMagicPower = customStatusMax('jungle:turn_magic_power', 'turn_magic_power');
    if (turnMagicTurns > 0 && turnMagicPower > 0) {
        tags.push({ key: 'jungle:turn_magic_turns', name: '魔力回合回复', abbr: 'MReg', val: `${turnMagicTurns};${turnMagicPower}`, fg: '#6C5CE7', bg: '#F0ECFF' });
    }
    const jungleStatusDisplay = [
        { keys: ['jungle:fragile', 'fragile'], name: '易损', abbr: '易损', fg: '#8E5A2A', bg: '#F7EFE8', title: '护甲降低对应层数；若降为负数，会使物理伤害增加。自己回合开始时清除。' },
        { keys: ['jungle:shield', 'shield'], name: '护盾', abbr: '护盾', fg: '#2E7D7D', bg: '#E8F6F6', title: '消耗层数抵扣等量伤害，包括魔法伤害。自己回合开始时层数减半。' },
        { keys: ['jungle:root_status', 'jungle:root', 'root_status'], name: '树根', abbr: '树根', fg: '#6E8B3D', bg: '#EEF5E5', title: '增加护甲；受到物理伤害时减少1层。' },
        { keys: ['jungle:toxic_poison', 'toxic_poison'], name: '剧毒', abbr: '剧毒', fg: '#5E8C31', bg: '#EEF6E7', title: '中毒结算后施加对应层数的中毒。' },
    ];
    jungleStatusDisplay.forEach((info) => {
        const count = customStatusSum(...info.keys);
        if (count > 0) tags.push({ key: info.keys[0], name: info.name, abbr: info.abbr, val: count, fg: info.fg, bg: info.bg, title: info.title });
    });
    if (customStatuses && typeof customStatuses === 'object') {
        const builtinKeys = new Set(['poison','fire','vulnerable','toxic','dodge','armor','sluggish','overload','foresight','fracture','stagnation','blind','heal_block','weakness','bleed','fragment','fragment_stacks','stunned','skip_turn','attack_blocked','禁攻','attack_only','仅攻击','status_immune','immune','状态免疫','jungle:turn_heal_turns','jungle:turn_heal_power','turn_heal_turns','turn_heal_power','jungle:turn_magic_turns','jungle:turn_magic_power','turn_magic_turns','turn_magic_power', ...jungleStatusDisplay.flatMap(info => info.keys)]);
        Object.entries(customStatuses).forEach(([name, value]) => {
            const count = Number(value || 0);
            if (count < 0) return;
            if (builtinKeys.has(name)) return;
            const def = getCustomStatusDef(name);
            if (def && def.visible === false) return;
            const label = def ? getRegistryText(def, 'name', name) : name;
            const icon = def && def.icon ? `${def.icon} ` : '';
            const color = safeRegistryColor(def && def.color, '#1F618D');
            tags.push({
                key: name,
                name: `${icon}${label}`,
                abbr: String(label).slice(0, 3),
                val: count,
                fg: color,
                bg: '#EAF2F8',
                customDef: def,
                title: def ? getRegistryText(def, 'description', '') : '',
            });
        });
    }
    const previousSignature = lastStatusSignatures.get(containerId);
    const previousItems = new Set(previousSignature ? previousSignature.split('\u0001') : []);
    const nextItems = [];
    tags.forEach(t => {
        const el = document.createElement('span');
        el.className = 'status-tag';
        el.style.color = t.fg;
        el.style.background = t.bg;
        const shownVal = maskStatusValues && t.val ? '?' : t.val;
        const fullText = shownVal ? `${t.name}:${shownVal}` : t.name;
        nextItems.push(fullText);
        el.textContent = fullText;
        el.title = hideStatusIntro ? '' : (t.title || '');
        el.dataset.statusKey = t.key || '';
        el.dataset.statusName = t.name || '';
        el.dataset.statusValue = hideStatusIntro ? '' : (shownVal == null ? '' : String(shownVal));
        if (previousSignature !== undefined && !previousItems.has(fullText)) {
            el.classList.add('status-tag-changed');
        }
        if (!hideStatusIntro) attachTermIntroToStatus(el, t);
        container.appendChild(el);
    });
    lastStatusSignatures.set(containerId, nextItems.join('\u0001'));
}

function appendUnknownHandMarker(container) {
    if (!container) return;
    const marker = document.createElement('div');
    marker.className = 'unknown-hand-marker';
    marker.textContent = '?';
    marker.setAttribute('aria-label', '?');
    container.appendChild(marker);
}

function renderOppHand(oppData, containerId = 'opp-hand') {
    const container = $(containerId);
    if (!container) return;
    removeFloatingCardPreview();
    container.innerHTML = '';
    const revealedHand = oppData.revealed_hand || oppData.hand;
    const revealedTagCards = oppData.revealed_tag_cards || [];
    if (revealedHand && revealedHand.length > 0) {
        revealedHand.forEach(cd => {
            const prediction = getCardPredictionOptionsForOwner(cd, oppData);
            const el = isSpectating
                ? createCardElement(cd, { small: true, prediction, ownerState: oppData })
                : createCardChoiceChip(cd, { previewOptions: { prediction, ownerState: oppData } });
            el.classList.add(isSpectating ? 'opp-hand-card' : 'opp-hand-chip');
            if (isSpectating) attachFloatingCardPreview(el, cd, { prediction, ownerState: oppData });
            container.appendChild(el);
        });
    } else if (revealedTagCards.length > 0) {
        const count = oppData.hand_count || 0;
        const sortedRevealed = [...revealedTagCards].sort((a, b) => (a.instance_id || 0) - (b.instance_id || 0));
        const hiddenCount = Math.max(0, count - sortedRevealed.length);
        // Show revealed cards as chips (hide 'revealed' tag on chip, but keep in preview)
        sortedRevealed.forEach(cd => {
            const prediction = getCardPredictionOptionsForOwner(cd, oppData);
            const el = isSpectating
                ? createCardElement(cd, { small: true, prediction, ownerState: oppData })
                : createCardChoiceChip(cd, { hideFlags: ['revealed'], previewOptions: { prediction, ownerState: oppData } });
            el.classList.add(isSpectating ? 'opp-hand-card' : 'opp-hand-chip');
            if (isSpectating) attachFloatingCardPreview(el, cd, { prediction, ownerState: oppData });
            container.appendChild(el);
        });
        for (let i = 0; i < hiddenCount; i++) {
            const card = createCardElement({}, { faceDown: true, small: true });
            container.appendChild(card);
        }
    } else {
        const count = oppData.hand_count || 0;
        if (getOwnBlindLevel() >= 3 && count > 0) {
            appendUnknownHandMarker(container);
            return;
        }
        for (let i = 0; i < count; i++) {
            const card = createCardElement({}, { faceDown: true, small: true });
            container.appendChild(card);
        }
    }
}

function renderTeammateHand(teammateData) {
    const container = $('teammate-hand');
    if (!container) return;
    removeFloatingCardPreview();
    container.innerHTML = '';
    const hand = teammateData.hand || [];
    if (getOwnBlindLevel() >= 3 && hand.length > 0) {
        appendUnknownHandMarker(container);
        return;
    }
    hand.forEach(card => {
        const prediction = getCardPredictionOptionsForOwner(card, teammateData);
        const el = isSpectating ? createCardElement(card, { small: true, prediction, ownerState: teammateData }) : createTeammateHandChip(card, teammateData);
        if (isSpectating) attachFloatingCardPreview(el, card, { prediction, ownerState: teammateData });
        container.appendChild(el);
    });
}

function createTeammateHandChip(cardDict, ownerState = null) {
    const cardDef = getCardDef(cardDict.def_id);
    const typeColor = cardDef ? (CARD_TYPE_COLORS[cardDef.card_type] || COLORS.border_color) : COLORS.border_color;
    const name = cardDef ? getCardName(cardDef) : (cardDict.def_id || '?');
    const el = document.createElement('span');
    el.className = 'teammate-hand-chip';
    el.dataset.instanceId = cardDict.instance_id || '';
    el.dataset.defId = cardDict.def_id || '';
    el.textContent = name;
    el.title = name;
    el.style.borderColor = typeColor;
    el.style.color = typeColor;
    attachFloatingCardPreview(el, cardDict, {
        ownerState,
        prediction: getCardPredictionOptionsForOwner(cardDict, ownerState),
    });
    attachTermIntroToCard(el, cardDict, {
        ownerState,
        prediction: getCardPredictionOptionsForOwner(cardDict, ownerState),
    });
    return el;
}

function renderPlayerHand(playerData) {
    const container = $('you-hand');
    if (!container) return;
    const oldRects = new Map();
    container.querySelectorAll('.card[data-instance-id]').forEach(el => {
        oldRects.set(String(el.dataset.instanceId), el.getBoundingClientRect());
    });
    container.innerHTML = '';
    const hand = playerData.hand || [];
    const handSlots = Math.max(7, Math.min(10, hand.length || 0));
    container.style.setProperty('--hand-card-slots', String(handSlots + 0.35));
    if (selectedPlayCardId != null && !hand.some(c => c.instance_id === selectedPlayCardId)) {
        clearSelectedPlayCard();
    }
    const myTurn = isMyTurn();
    hand.forEach(cardDict => {
        const cardDef = getCardDef(cardDict.def_id);
        const canPlay = myTurn && !isActionBusy({ includeAnimation: false }) && canPlayCard(cardDict);
        const card = createCardElement(cardDict, {
            small: !!isSpectating,
            draggable: !isSpectating && canPlay && cardDef && cardDef.card_type !== 'guard',
            onClick: canPlay ? () => selectPlayCardForConfirm(cardDict.instance_id) : null,
            ownerState: playerData,
            prediction: getCardPredictionOptionsForOwner(cardDict, playerData),
        });
        if (selectedPlayCardId === cardDict.instance_id) {
            card.classList.add('tap-selected');
        }
        if (!canPlay) {
            card.classList.add('card-disabled');
        }
        container.appendChild(card);
    });
    animateHandLayoutChanges(container, oldRects, hand);
    hasPlayerHandSnapshot = true;
}

function canPlayCard(cardDict) {
    const gs = gameState;
    const you = gs.you || {};
    if (gs.phase !== 'action') return false;
    if (!isMyTurn()) return false;
    if (you.shovel_active) return false;
    const cardDef = getCardDef(cardDict.def_id);
    if (!cardDef) return false;
    if (cardDef.card_type === 'guard' && !cardHasPlayableScript(cardDef) && !(cardDef.effects || []).length) return false;
    if (getActionLimitStatusValue(you, 'attack_blocked', '禁攻') > 0 && cardDef.card_type === 'thorn') return false;
    if (getActionLimitStatusValue(you, 'attack_only', '仅攻击') > 0 && cardDef.card_type !== 'thorn') return false;
    const elixir = you.elixir || 0;
    const magic = you.magic || 0;
    const { totalE, totalM } = getCardDisplayCosts(cardDict, cardDef, you);
    if (totalE > elixir) return false;
    if (totalM > magic) return false;
    return true;
}

function getActionLimitStatusValue(playerData, ...keys) {
    const data = playerData || {};
    let value = 0;
    keys.forEach(key => {
        value = Math.max(value, Number(data[key] || 0));
    });
    const custom = data.custom_statuses || {};
    keys.forEach(key => {
        const raw = custom[key];
        if (raw && typeof raw === 'object') {
            value = Math.max(value, Number(raw.stacks ?? raw.stack ?? raw.value ?? raw.layers ?? 0));
        } else {
            value = Math.max(value, Number(raw || 0));
        }
    });
    return value;
}

function getCannotPlayReason(cardDict) {
    const gs = gameState || {};
    const you = gs.you || {};
    const cardDef = cardDict ? getCardDef(cardDict.def_id) : null;
    if (!cardDict || !cardDef) return UI.cannot_play;
    if (gs.phase !== 'action') return UI.error_waiting_response_ui || UI.cannot_play;
    if (!isMyTurn()) return UI.error_not_your_turn || UI.not_your_turn || UI.cannot_play;
    if (you.shovel_active) return UI.error_action_blocked || UI.cannot_play;
    if (cardDef.card_type === 'guard' && !cardHasPlayableScript(cardDef) && !(cardDef.effects || []).length) {
        return UI.error_waiting_response_ui || UI.cannot_play;
    }
    if (getActionLimitStatusValue(you, 'attack_blocked', '禁攻') > 0 && cardDef.card_type === 'thorn') return UI.error_attack_blocked || UI.cannot_play;
    if (getActionLimitStatusValue(you, 'attack_only', '仅攻击') > 0 && cardDef.card_type !== 'thorn') return UI.error_attack_only || UI.cannot_play;
    const { totalE, totalM } = getCardDisplayCosts(cardDict, cardDef, you);
    const reasons = [];
    if (totalE > (you.elixir || 0)) reasons.push(UI.error_not_enough_e || UI.insufficient_resources || UI.cannot_play);
    if (totalM > (you.magic || 0)) reasons.push(UI.insufficient_resources || UI.cannot_play);
    return reasons.length ? [...new Set(reasons)].join(' / ') : UI.cannot_play;
}

function isFriendlyTurn() {
    if (!gameState || gameState.spectating) return false;
    if (isMyTurn()) return true;
    return gameState.mode === '2v2' && gameState.current_player === gameState.teammate_id;
}

function getEnemyTargetOptions() {
    if (!gameState || gameState.mode !== '2v2') return [];
    const ids = gameState.enemy_ids || [];
    const names = gameState.opponent_names || [];
    const opponents = [gameState.opponent || {}, gameState.opponent2 || {}];
    return ids.map((id, i) => {
        const data = opponents[i] || {};
        return {
            id,
            label: `${localizeCanonicalPlayerName(names[i] || (UI.opponent + (i + 1)))} H:${data.health || 0}/${data.max_health || 0}`,
            alive: (data.health || 0) > 0
        };
    }).filter(x => x.alive);
}

function cardHasPlayableScript(cardDef) {
    const scripts = cardDef && cardDef.scripts;
    if (!scripts || typeof scripts !== 'object') return false;
    return ['onPlay', 'play', 'on_play'].some(key => Object.prototype.hasOwnProperty.call(scripts, key));
}

function normalizePlayerId(id) {
    if (id === null || id === undefined || id === '') return null;
    const value = Number(id);
    return Number.isInteger(value) ? value : null;
}

function getPlayerNameById(id) {
    id = normalizePlayerId(id);
    const fallback = id == null ? '?' : `P${id + 1}`;
    if (!gameState) return fallback;
    const spectatePlayer = Array.isArray(gameState.spectate_players)
        ? gameState.spectate_players.find(p => normalizePlayerId(p && p.player_id) === id)
        : null;
    if (spectatePlayer && spectatePlayer.name) {
        return localizeCanonicalPlayerName(spectatePlayer.name);
    }
    const directName = gameState[`player${id + 1}_name`];
    if (directName) return localizeCanonicalPlayerName(directName);
    const nameList = Array.isArray(gameState.player_names) ? gameState.player_names : [];
    if (nameList[id]) return localizeCanonicalPlayerName(nameList[id]);
    if (id === normalizePlayerId(gameState.your_id)) return localizeCanonicalPlayerName(gameState.your_name || UI.you);
    if (id === normalizePlayerId(gameState.teammate_id)) return localizeCanonicalPlayerName(gameState.teammate_name || UI.teammate);
    const oneVsOneOpponentId = gameState.your_id != null ? 1 - normalizePlayerId(gameState.your_id) : null;
    if ((!Array.isArray(gameState.enemy_ids) || !gameState.enemy_ids.length) && id === oneVsOneOpponentId) {
        return localizeCanonicalPlayerName(gameState.opponent_name || UI.opponent);
    }
    const enemyIndex = (gameState.enemy_ids || []).map(normalizePlayerId).indexOf(id);
    if (enemyIndex >= 0) return localizeCanonicalPlayerName((gameState.opponent_names || [])[enemyIndex] || `${UI.opponent}${enemyIndex + 1}`);
    return fallback;
}

function getPlayerDataById(id) {
    id = normalizePlayerId(id);
    if (!gameState) return {};
    if (Array.isArray(gameState.spectate_players)) {
        const spectatePlayer = gameState.spectate_players.find(p => normalizePlayerId(p && p.player_id) === id);
        if (spectatePlayer) return spectatePlayer;
    }
    if (id === normalizePlayerId(gameState.your_id)) return gameState.you || {};
    if (id === normalizePlayerId(gameState.teammate_id)) return gameState.teammate || {};
    const oneVsOneOpponentId = gameState.your_id != null ? 1 - normalizePlayerId(gameState.your_id) : null;
    if ((!Array.isArray(gameState.enemy_ids) || !gameState.enemy_ids.length) && id === oneVsOneOpponentId) {
        return gameState.opponent || {};
    }
    const enemyIndex = (gameState.enemy_ids || []).map(normalizePlayerId).indexOf(id);
    if (enemyIndex === 0) return gameState.opponent || {};
    if (enemyIndex === 1) return gameState.opponent2 || {};
    return {};
}

function syncPlayerRegionTargets(gs) {
    const clear = () => document.querySelectorAll('[data-player-target-region]')
        .forEach(el => {
            el.removeAttribute('data-player-id');
            el.classList.remove('target-pickable', 'target-picked');
        });
    clear();
    if (!gs) return;
    const useClassicRefs = shouldUseClassicBattle(gs);
    const assign = (selector, id) => {
        const el = document.querySelector(selector);
        const pid = normalizePlayerId(id);
        if (!el || pid == null) return;
        el.dataset.playerTargetRegion = '1';
        el.dataset.playerId = String(pid);
    };
    if (useClassicRefs) {
        assign('#classic-fighter-self', gs.your_id);
        assign('#classic-fighter-enemy', gs.mode === '2v2' ? (gs.enemy_ids || [])[0] : (normalizePlayerId(gs.your_id) === 1 ? 0 : 1));
        return;
    }
    assign('.player-section', gs.your_id);
    assign('.opp-half.opp-left', gs.mode === '2v2' ? (gs.enemy_ids || [])[0] : (normalizePlayerId(gs.your_id) === 1 ? 0 : 1));
    if (gs.mode === '2v2') {
        assign('#opp2-half', (gs.enemy_ids || [])[1]);
        assign('#teammate-sidebar', gs.teammate_id);
    }
}

function isVisibleTargetRegion(el) {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    if (!rect || rect.width <= 2 || rect.height <= 2) return false;
    const style = window.getComputedStyle ? window.getComputedStyle(el) : null;
    return !style || (style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity || 1) > 0);
}

function getPlayerRegionById(id) {
    const pid = normalizePlayerId(id);
    if (pid == null) return null;
    const regions = Array.from(document.querySelectorAll(`[data-player-target-region][data-player-id="${pid}"]`));
    return regions.find(isVisibleTargetRegion) || regions[0] || null;
}

function choosePlayerTargetOnBoard(title, targets) {
    if (!Array.isArray(targets) || !targets.length) return Promise.resolve(null);
    const regions = targets
        .map(target => ({ target, el: getPlayerRegionById(target.id) }))
        .filter(item => item.el && isVisibleTargetRegion(item.el));
    if (!regions.length || regions.length < targets.length) return Promise.resolve(null);
    return new Promise(resolve => {
        if (targetPickCleanup) targetPickCleanup();
        let settled = false;
        let outsideEnabled = false;
        const handlers = new Map();
        const finish = (value) => {
            if (settled) return;
            settled = true;
            regions.forEach(({ el }) => {
                el.classList.remove('target-pickable', 'target-picked');
                el.removeEventListener('click', handlers.get(el), true);
            });
            handlers.clear();
            document.removeEventListener('pointerdown', outsideHandler, true);
            document.removeEventListener('keydown', keyHandler, true);
            document.removeEventListener('contextmenu', contextHandler, true);
            if (targetPickCleanup === finishCancel) targetPickCleanup = null;
            resolve(value);
        };
        const finishCancel = () => finish(-1);
        const isPickableNode = (node) => !!(node && node.closest && node.closest('[data-player-target-region].target-pickable'));
        const outsideHandler = (event) => {
            if (!outsideEnabled || isPickableNode(event.target)) return;
            event.preventDefault();
            finishCancel();
        };
        const keyHandler = (event) => {
            if (event.key !== 'Escape') return;
            event.preventDefault();
            finishCancel();
        };
        const contextHandler = (event) => {
            event.preventDefault();
            finishCancel();
        };
        regions.forEach(({ target, el }) => {
            const handler = (event) => {
                event.preventDefault();
                event.stopPropagation();
                el.classList.add('target-picked');
                flashTargetRegion(target.id);
                setTimeout(() => finish(target.id), 90);
            };
            handlers.set(el, handler);
            el.classList.add('target-pickable');
            el.addEventListener('click', handler, true);
        });
        document.addEventListener('pointerdown', outsideHandler, true);
        document.addEventListener('keydown', keyHandler, true);
        document.addEventListener('contextmenu', contextHandler, true);
        setTimeout(() => { outsideEnabled = true; }, 0);
        targetPickCleanup = finishCancel;
    });
}

function getStatePlayerRefs(gs) {
    if (!gs) return [];
    const refs = [];
    const add = (id, data, selector) => {
        const pid = normalizePlayerId(id);
        if (pid == null || !data) return;
        refs.push({ id: pid, data, selector });
    };
    const yourId = normalizePlayerId(gs.your_id);
    const useClassicRefs = shouldUseClassicBattle(gs);
    add(yourId, gs.you, useClassicRefs ? '#classic-fighter-self' : '.player-section');
    if (gs.mode === '2v2') {
        const enemyIds = gs.enemy_ids || [];
        add(enemyIds[0], gs.opponent, '.opp-half.opp-left');
        add(enemyIds[1], gs.opponent2, '#opp2-half');
        add(gs.teammate_id, gs.teammate, '#teammate-sidebar');
    } else {
        add(yourId === 1 ? 0 : 1, gs.opponent, useClassicRefs ? '#classic-fighter-enemy' : '.opp-half.opp-left');
    }
    return refs;
}

function areSequentialGameStates(previous, next, options = {}) {
    if (!previous || !next || previous === next) return false;
    if (!previous.phase || !next.phase) return false;
    if ((previous.mode || '') !== (next.mode || '')) return false;
    if (!!previous.solo !== !!next.solo) return false;
    if (!!previous.spectating !== !!next.spectating) return false;
    if (previous.spectating && next.spectating) {
        if (Number(previous.room_id) !== Number(next.room_id)) return false;
        if (normalizePlayerId(previous.spectate_perspective) !== normalizePlayerId(next.spectate_perspective)) return false;
    }
    const previousYourId = normalizePlayerId(previous.your_id);
    const nextYourId = normalizePlayerId(next.your_id);
    if (previousYourId !== nextYourId) {
        const allowSoloPerspectiveShift = !!options.allowSoloPerspectiveShift && previous.solo && next.solo;
        if (!allowSoloPerspectiveShift) return false;
    }
    const prevTotal = Number(previous.log_total);
    const nextTotal = Number(next.log_total);
    if (Number.isFinite(prevTotal) && Number.isFinite(nextTotal) && nextTotal < prevTotal) return false;
    const prevRound = Number(previous.round_num);
    const nextRound = Number(next.round_num);
    if (Number.isFinite(prevRound) && Number.isFinite(nextRound) && nextRound < prevRound) return false;
    if (previous.phase === 'game_over' && next.phase !== 'game_over') return false;
    return true;
}

function getCombatFloatAnchor(region, kind) {
    if (!region) return null;
    if (region.id === 'classic-fighter-self') {
        if (kind === 'elixir') return $('classic-e-orbs') || region;
        if (kind === 'magic') return $('classic-m-orbs') || region;
    }
    const barKey = kind === 'elixir' ? 'elixir'
        : kind === 'magic' ? 'magic'
        : (kind === 'damage' || kind === 'heal') ? 'health'
        : '';
    if (barKey) {
        const bar = region.querySelector(`[data-bar-key="${barKey}"] .bar-track`) || region.querySelector(`[data-bar-key="${barKey}"]`);
        if (bar) return bar;
    }
    return region.querySelector('.classic-status-ring') || region.querySelector('.status-tags') || region.querySelector('.player-info-bar') || region;
}

function getCombatFloatTimeline(events) {
    const normalized = (events || [])
        .filter(event => event && event.text)
        .map((event, order) => {
            const rawDelay = Number(event.delay);
            return {
                ...event,
                order,
                rawDelay: Number.isFinite(rawDelay) ? Math.max(0, rawDelay) : 0,
            };
        });
    if (!normalized.length) return { events: [], duration: COMBAT_FLOAT_BASE_DURATION_MS, totalMs: 0 };
    const rawMaxDelay = normalized.reduce((max, event) => Math.max(max, event.rawDelay), 0);
    const targetMaxDelay = Math.min(rawMaxDelay, Math.max(0, COMBAT_FLOAT_MAX_LAST_DELAY_MS));
    const scale = rawMaxDelay > 0 && rawMaxDelay > targetMaxDelay ? targetMaxDelay / rawMaxDelay : 1;
    let maxDelay = 0;
    const slotCounts = new Map();
    const scheduled = normalized.map(event => {
        const delay = Math.round(event.rawDelay * scale);
        maxDelay = Math.max(maxDelay, delay);
        const slotKey = `${Math.round(delay / 24)}:${event.kind || 'info'}`;
        const sameSlotIndex = slotCounts.get(slotKey) || 0;
        slotCounts.set(slotKey, sameSlotIndex + 1);
        const baseStack = Number.isFinite(Number(event.stackIndex)) ? Number(event.stackIndex) : 0;
        return {
            ...event,
            delay,
            stackIndex: baseStack + sameSlotIndex,
        };
    });
    const durationRoom = COMBAT_FLOAT_TOTAL_LIMIT_MS - maxDelay - COMBAT_FLOAT_END_PAD_MS;
    const duration = Math.max(COMBAT_FLOAT_MIN_DURATION_MS, Math.min(COMBAT_FLOAT_BASE_DURATION_MS, durationRoom));
    return {
        events: scheduled,
        duration,
        totalMs: Math.min(COMBAT_FLOAT_TOTAL_LIMIT_MS, maxDelay + duration + COMBAT_FLOAT_END_PAD_MS),
    };
}

function showCombatFloat(selector, text, kind, index = 0, options = {}) {
    if (!text || !selector) return;
    const region = document.querySelector(selector);
    const anchor = getCombatFloatAnchor(region, kind);
    if (!region || !anchor) return;
    const rect = anchor.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const el = document.createElement('div');
    el.className = `combat-float combat-${kind || 'info'}`;
    el.textContent = text;
    const lane = Math.max(0, Math.floor(Number(index) || 0));
    const row = lane % 5;
    const band = Math.floor(lane / 5);
    const side = lane % 2 === 0 ? -1 : 1;
    const laneX = side * Math.min(42, 6 + band * 12);
    const laneY = row * 12;
    const duration = Math.max(320, Number(options.duration) || COMBAT_FLOAT_BASE_DURATION_MS);
    const x = rect.left + rect.width - 8 + laneX;
    const y = rect.top + rect.height * 0.5 + laneY;
    el.style.left = `${Math.min(window.innerWidth - 10, Math.max(10, x))}px`;
    el.style.top = `${Math.min(window.innerHeight - 10, Math.max(10, y))}px`;
    el.style.setProperty('--float-x', `${side * Math.min(18, 6 + band * 4)}px`);
    el.style.setProperty('--float-duration', `${duration}ms`);
    el.dataset.floatId = String(++combatFloatSeq);
    document.body.appendChild(el);
    setTimeout(() => el.remove(), duration + 180);
}

function showCombatFloatSequence(selector, events, interval = 200) {
    const timeline = getCombatFloatTimeline(events, interval);
    timeline.events.forEach(event => {
        setTimeout(() => {
            showCombatFloat(selector, event.text, event.kind, event.stackIndex, { duration: timeline.duration });
        }, Math.max(0, event.delay));
    });
    return timeline.events;
}

function scheduleSkinDamageMoods(playerId, events) {
    const list = (events || []).filter(Boolean);
    const hasPoison = list.some(event => event.kind === 'poison');
    const hasFire = list.some(event => event.kind === 'fire');
    if (hasPoison && hasFire) {
        const firstDelay = Math.min(...list
            .filter(event => event.kind === 'poison' || event.kind === 'fire')
            .map(event => Math.max(0, Number(event.delay) || 0)));
        triggerSkinDamageMood(playerId, 'poison', firstDelay, SKIN_STATUS_DAMAGE_SPLIT_MS);
        triggerSkinDamageMood(playerId, 'fire', firstDelay + SKIN_STATUS_DAMAGE_SPLIT_MS, SKIN_STATUS_DAMAGE_SPLIT_MS);
        list.filter(event => event.kind !== 'poison' && event.kind !== 'fire').forEach(event => {
            triggerSkinDamageMood(playerId, event.kind || 'damage', event.delay || 0);
        });
        return;
    }
    list.forEach(event => {
        if (!event) return;
        triggerSkinDamageMood(playerId, event.kind || 'damage', event.delay || 0);
    });
}

function getBarMaxForKey(data, key) {
    const value = key === 'health' ? data && data.max_health
        : key === 'elixir' ? data && data.max_elixir
        : key === 'magic' ? data && data.max_magic
        : 0;
    const fallback = key === 'health' ? 100 : 10;
    return Number.isFinite(Number(value)) ? Number(value) : fallback;
}

function getBarValueForKey(data, key) {
    const value = key === 'health' ? data && data.health
        : key === 'elixir' ? data && data.elixir
        : key === 'magic' ? data && data.magic
        : 0;
    return Number.isFinite(Number(value)) ? Number(value) : 0;
}

function shouldMaskRenderedBarRegion(region) {
    if (!region) return false;
    const blindLevel = getOwnBlindLevel();
    if (blindLevel < 2) return false;
    const pid = normalizePlayerId(region.dataset && region.dataset.playerId);
    const selfId = normalizePlayerId(gameState && gameState.your_id);
    if (pid == null || selfId == null) return false;
    return (pid === selfId && blindLevel >= 2) || (pid !== selfId && blindLevel >= 3);
}

function setRenderedBarValue(selector, key, value, max, immediate = false) {
    const region = document.querySelector(selector);
    let wrapper = region && region.querySelector(`[data-bar-key="${key}"]`);
    if (!wrapper && region && region.id === 'classic-fighter-self' && (key === 'elixir' || key === 'magic')) {
        const orbs = key === 'elixir' ? $('classic-e-orbs') : $('classic-m-orbs');
        wrapper = orbs ? orbs.closest('.classic-resource-block') : null;
    }
    if (!wrapper) return;
    const fill = wrapper.querySelector('.bar-fill') || wrapper.querySelector('.classic-hp-fill');
    const text = wrapper.querySelector('.bar-text') || wrapper.querySelector('.classic-hp-text');
    const cur = Number.isFinite(Number(value)) ? Number(value) : 0;
    const maxValue = Number.isFinite(Number(max)) && Number(max) > 0 ? Number(max) : getBarMaxForKey({}, key);
    const masked = shouldMaskRenderedBarRegion(region);
    if (wrapper.classList.contains('classic-resource-block')) {
        renderClassicResourceOrbs(wrapper.querySelector('.classic-orbs'), cur, maxValue, 0, key === 'magic' ? 'm' : 'e', masked);
        if (!immediate) {
            wrapper.classList.remove('classic-resource-pop');
            wrapper.offsetHeight;
            wrapper.classList.add('classic-resource-pop');
            setTimeout(() => wrapper.classList.remove('classic-resource-pop'), 420);
        }
        return;
    }
    wrapper.classList.toggle('blind-masked', masked);
    if (masked) {
        if (fill) {
            if (immediate) fill.classList.add('bar-fill-instant');
            fill.style.width = '0%';
            if (immediate) {
                fill.offsetHeight;
                requestAnimationFrame(() => fill.classList.remove('bar-fill-instant'));
            }
        }
        if (text) text.textContent = '?';
        wrapper.dataset.renderedValue = '?';
        return;
    }
    const pct = Math.max(0, Math.min(100, (cur / maxValue) * 100));
    const prevValue = Number(wrapper.dataset.renderedValue);
    if (fill) {
        if (immediate) fill.classList.add('bar-fill-instant');
        fill.style.width = `${pct}%`;
        if (immediate) {
            fill.offsetHeight;
            requestAnimationFrame(() => fill.classList.remove('bar-fill-instant'));
        }
    }
    if (text) {
        const label = wrapper.dataset.barLabel || '';
        const armor = Number(wrapper.dataset.barArmor || 0);
        const suffix = label === 'H' && armor ? ` · A ${armor}` : '';
        text.textContent = label ? `${label} ${cur}/${maxValue}${suffix}` : `${cur}/${maxValue}`;
    }
    wrapper.dataset.renderedValue = String(cur);
    if (!immediate && wrapper.classList.contains('classic-hp-wrap')) {
        const changed = Number.isFinite(prevValue) ? cur - prevValue : 0;
        const cls = changed < 0 ? 'classic-hp-hit' : changed > 0 ? 'classic-hp-heal' : 'classic-hp-change';
        wrapper.classList.remove('classic-hp-hit', 'classic-hp-heal', 'classic-hp-change');
        wrapper.offsetHeight;
        wrapper.classList.add(cls);
        const fighter = wrapper.closest('.classic-fighter');
        if (fighter && changed < 0) {
            fighter.classList.remove('classic-hit-shake');
            fighter.offsetHeight;
            fighter.classList.add('classic-hit-shake');
            setTimeout(() => fighter.classList.remove('classic-hit-shake'), 520);
        }
        setTimeout(() => wrapper.classList.remove(cls), 520);
    }
}

function animateBarEventSequence(selector, scheduledEvents, oldData, newData, options = {}) {
    const affected = new Set((scheduledEvents || []).map(event => event && event.barKey).filter(Boolean));
    Object.keys(options.startValues || {}).forEach(key => affected.add(key));
    if (!affected.size) return;
    affected.forEach(key => {
        const startValue = Object.prototype.hasOwnProperty.call(options.startValues || {}, key)
            ? options.startValues[key]
            : getBarValueForKey(oldData, key);
        setRenderedBarValue(selector, key, startValue, getBarMaxForKey(newData, key), true);
    });
    let maxDelay = 0;
    (scheduledEvents || []).forEach(event => {
        if (!event || !event.barKey || !Number.isFinite(Number(event.barValue))) return;
        const delay = Math.max(0, Number(event.delay) || 0);
        maxDelay = Math.max(maxDelay, delay);
        setTimeout(() => {
            setRenderedBarValue(
                selector,
                event.barKey,
                Number(event.barValue),
                Number.isFinite(Number(event.barMax)) ? Number(event.barMax) : getBarMaxForKey(newData, event.barKey)
            );
        }, delay);
    });
    setTimeout(() => {
        affected.forEach(key => {
            setRenderedBarValue(selector, key, getBarValueForKey(newData, key), getBarMaxForKey(newData, key));
        });
    }, Math.min(COMBAT_FLOAT_TOTAL_LIMIT_MS, maxDelay + 80));
}

function queueLocalResourceCost(cardDict, ownerState = null, options = {}) {
    if (!cardDict) return;
    const cardDef = getCardDef(cardDict.def_id);
    if (!cardDef) return;
    const { totalE, totalM } = getCardDisplayCosts(cardDict, cardDef, ownerState || (gameState && gameState.you));
    if (!totalE && !totalM) return;
    pendingLocalResourceCosts.push({
        playerId: normalizePlayerId(gameState && gameState.your_id),
        instanceId: cardInstanceKey(cardDict),
        totalE: Math.max(0, Number(totalE) || 0),
        totalM: Math.max(0, Number(totalM) || 0),
        shownOptimistically: !!options.shownOptimistically,
        createdAt: Date.now(),
    });
    pendingLocalResourceCosts = pendingLocalResourceCosts
        .filter(item => item && Date.now() - Number(item.createdAt || 0) < 6000)
        .slice(-8);
}

function takeLocalResourceCostForState(ref, oldData, newData) {
    const playerId = normalizePlayerId(ref && ref.id);
    if (playerId == null || !pendingLocalResourceCosts.length) return null;
    const oldHandIds = new Set(((oldData && oldData.hand) || []).map(cardInstanceKey).filter(Boolean));
    const newHandIds = new Set(((newData && newData.hand) || []).map(cardInstanceKey).filter(Boolean));
    const idx = pendingLocalResourceCosts.findIndex(item => {
        if (!item || normalizePlayerId(item.playerId) !== playerId) return false;
        if (!item.instanceId) return false;
        return oldHandIds.has(String(item.instanceId)) && !newHandIds.has(String(item.instanceId));
    });
    if (idx < 0) return null;
    return pendingLocalResourceCosts.splice(idx, 1)[0];
}

function queueOptimisticResourceCost(cost) {
    if (!cost || (!cost.totalE && !cost.totalM)) return;
    pendingOptimisticResourceCosts.push({
        playerId: normalizePlayerId(gameState && gameState.your_id),
        totalE: Math.max(0, Number(cost.totalE) || 0),
        totalM: Math.max(0, Number(cost.totalM) || 0),
        shownOptimistically: true,
        createdAt: Date.now(),
    });
    pendingOptimisticResourceCosts = pendingOptimisticResourceCosts
        .filter(item => item && Date.now() - Number(item.createdAt || 0) < 6000)
        .slice(-8);
}

function takeOptimisticResourceCostForState(ref) {
    const playerId = normalizePlayerId(ref && ref.id);
    if (playerId == null || !pendingOptimisticResourceCosts.length) return null;
    const idx = pendingOptimisticResourceCosts.findIndex(item => item && normalizePlayerId(item.playerId) === playerId);
    if (idx < 0) return null;
    return pendingOptimisticResourceCosts.splice(idx, 1)[0];
}

function getNewBattleLogLines(previous, next) {
    const nextLog = Array.isArray(next && next.log) ? next.log : [];
    const nextStart = Number(next && next.log_start) || 0;
    const prevLog = Array.isArray(previous && previous.log) ? previous.log : [];
    const prevStart = Number(previous && previous.log_start) || 0;
    const prevTotalRaw = previous && previous.log_total;
    const prevTotal = Number.isFinite(Number(prevTotalRaw)) ? Number(prevTotalRaw) : prevStart + prevLog.length;
    let startIndex = Math.max(0, prevTotal - nextStart);
    if (startIndex > nextLog.length) startIndex = 0;
    return nextLog.slice(startIndex);
}

function splitDamageLogTarget(before) {
    const text = String(before || '');
    const comma = Math.max(text.lastIndexOf('，'), text.lastIndexOf(','));
    return (comma >= 0 ? text.slice(comma + 1) : text).trim();
}

function parseDamagePartsText(raw, repeatRaw = null) {
    const text = String(raw || '').trim();
    if (!text) return [];
    let parts = [];
    if (/^\d+(?:\+\d+)+$/.test(text)) {
        parts = text.split('+').map(v => Number(v));
    } else if (/^\d+$/.test(text)) {
        const amount = Number(text);
        const repeat = repeatRaw == null || repeatRaw === '' ? 1 : Number(repeatRaw);
        const count = Number.isFinite(repeat) ? Math.max(1, Math.floor(repeat)) : 1;
        parts = Array.from({ length: count }, () => amount);
    }
    return parts.filter(v => Number.isFinite(v) && v > 0);
}

function damageVisualKindFromSource(source, rawLine = '') {
    const text = `${source || ''} ${rawLine || ''}`;
    if (/(中毒|毒伤|poison|\bP\b|P伤害)/i.test(text)) return 'poison';
    if (/(灼烧|火伤|burn|fire|\bF\b|F伤害)/i.test(text)) return 'fire';
    return 'damage';
}

function expandDamageLogHits(name, parts, hpText, source = '', rawLine = '') {
    const cleanParts = (Array.isArray(parts) ? parts : [])
        .map(v => Math.max(0, Math.ceil(Number(v || 0))))
        .filter(v => Number.isFinite(v) && v > 0);
    if (!name || !cleanParts.length) return [];
    const hpRaw = String(hpText || '').trim();
    const hpParts = hpRaw.split('→')
        .map(part => Number(String(part || '').trim()))
        .filter(value => Number.isFinite(value));
    const hasHpChain = hpParts.length >= 2;
    const startHp = hasHpChain ? hpParts[0] : null;
    const endHp = hasHpChain ? hpParts[hpParts.length - 1] : Number(hpRaw);
    let staged = Number.isFinite(startHp) ? startHp : null;
    const visualKind = damageVisualKindFromSource(source, rawLine);
    return cleanParts.map((amount, index) => {
        let health = null;
        if (hasHpChain && Number.isFinite(hpParts[index + 1])) {
            health = hpParts[index + 1];
            staged = health;
        } else if (Number.isFinite(staged)) {
            staged -= amount;
            health = staged;
        } else if (index === cleanParts.length - 1 && Number.isFinite(endHp)) {
            health = endHp;
        }
        if (index === cleanParts.length - 1 && Number.isFinite(endHp)) {
            health = endHp;
        }
        return { name, amount, health, source, visualKind };
    });
}

function parseDamageLogLine(line) {
    const text = String(line || '');
    const hpSuffix = '[（(]H=([^）)]+)[）)]$';
    let match = text.match(new RegExp(`^(.+?)受到[（(](\\d+(?:\\+\\d+)*)[）)]D${hpSuffix}`));
    if (match) {
        return expandDamageLogHits(splitDamageLogTarget(match[1]), parseDamagePartsText(match[2]), match[3], 'D', text);
    }
    match = text.match(new RegExp(`^(.+?)受到(\\d+)D(?:[×x](\\d+))?${hpSuffix}`));
    if (match) {
        return expandDamageLogHits(splitDamageLogTarget(match[1]), parseDamagePartsText(match[2], match[3]), match[4], 'D', text);
    }
    match = text.match(new RegExp(`^(.+?)受到(\\d+(?:\\+\\d+)*)(中毒|毒伤|灼烧|火伤|P|F|Poison|Burn|Fire)伤害${hpSuffix}`, 'i'));
    if (match) {
        return expandDamageLogHits(splitDamageLogTarget(match[1]), parseDamagePartsText(match[2]), match[4], match[3], text);
    }
    match = text.match(new RegExp(`^(.+?)受到(\\d+(?:\\+\\d+)*)点([^（）()]*?)伤害${hpSuffix}`));
    if (match) {
        return expandDamageLogHits(splitDamageLogTarget(match[1]), parseDamagePartsText(match[2]), match[4], match[3], text);
    }
    match = text.match(new RegExp(`^(.+?)受到(\\d+)点([^（）()]*?)${hpSuffix}`));
    if (match) {
        return expandDamageLogHits(splitDamageLogTarget(match[1]), parseDamagePartsText(match[2]), match[4], match[3], text);
    }
    return [];
}

function getStatePlayerDisplayNames(gs, ref) {
    const names = new Set();
    const id = normalizePlayerId(ref && ref.id);
    const data = (ref && ref.data) || {};
    if (data.name) names.add(String(data.name));
    if (id == null || !gs) return names;
    if (Array.isArray(gs.spectate_players)) {
        const p = gs.spectate_players.find(item => normalizePlayerId(item && item.player_id) === id);
        if (p && p.name) names.add(String(p.name));
    }
    if (id === normalizePlayerId(gs.your_id) && gs.your_name) names.add(String(gs.your_name));
    if (id === normalizePlayerId(gs.teammate_id) && gs.teammate_name) names.add(String(gs.teammate_name));
    if (gs.mode === '2v2') {
        const enemyIndex = (gs.enemy_ids || []).map(normalizePlayerId).indexOf(id);
        if (enemyIndex >= 0 && (gs.opponent_names || [])[enemyIndex]) {
            names.add(String((gs.opponent_names || [])[enemyIndex]));
        }
    } else {
        const yourId = normalizePlayerId(gs.your_id);
        if (id !== yourId && gs.opponent_name) names.add(String(gs.opponent_name));
    }
    if (gs[`player${id + 1}_name`]) names.add(String(gs[`player${id + 1}_name`]));
    return names;
}

function getDamageLogEventsByPlayer(previous, next) {
    const refs = getStatePlayerRefs(next);
    const nameToId = new Map();
    refs.forEach(ref => {
        getStatePlayerDisplayNames(next, ref).forEach(name => {
            if (name) nameToId.set(name, ref.id);
        });
    });
    const out = new Map();
    getNewBattleLogLines(previous, next).forEach(line => {
        const parsedHits = parseDamageLogLine(line);
        if (!parsedHits.length) return;
        parsedHits.forEach(parsed => {
            const id = nameToId.get(parsed.name);
            if (id == null) return;
            if (!out.has(id)) out.set(id, []);
            out.get(id).push(parsed);
        });
    });
    return out;
}

function inferStatusDamageKindForRef(previous, next, ref, oldData, newData, healthDelta, damageHits) {
    if (Number(healthDelta || 0) >= 0) return null;
    if ((damageHits || []).some(hit => hit && (hit.visualKind === 'poison' || hit.visualKind === 'fire'))) return null;
    const names = getStatePlayerDisplayNames(next, ref);
    const lines = getNewBattleLogLines(previous, next);
    for (const line of lines) {
        const kind = damageVisualKindFromSource('', line);
        if (kind !== 'poison' && kind !== 'fire') continue;
        const parsed = parseDamageLogLine(line);
        const matchedByParsedTarget = parsed.some(hit => hit && names.has(hit.name));
        const matchedByText = [...names].some(name => name && String(line).includes(name));
        if (matchedByParsedTarget || matchedByText) return kind;
    }
    if ((damageHits || []).length) return null;
    const refId = normalizePlayerId(ref && ref.id);
    const currentId = normalizePlayerId(next && next.current_player);
    if (refId == null || currentId !== refId) return null;
    const oldPoison = Number(oldData && oldData.poison || 0);
    const newPoison = Number(newData && newData.poison || 0);
    const oldFire = Number(oldData && oldData.fire || 0);
    if (oldPoison > 0 && newPoison < oldPoison) return 'poison';
    if (oldFire > 0) return 'fire';
    return null;
}

function showStateDeltas(previous, next) {
    if (!areSequentialGameStates(previous, next, { allowSoloPerspectiveShift: true })) return;
    if (!next.phase || next.phase === 'draft' || next.phase === 'event_select') return;
    const prev = new Map(getStatePlayerRefs(previous).map(ref => [ref.id, ref]));
    const damageLogEvents = getDamageLogEventsByPlayer(previous, next);
    getStatePlayerRefs(next).forEach(ref => {
        const oldRef = prev.get(ref.id);
        if (!oldRef) return;
        const oldData = oldRef.data || {};
        const newData = ref.data || {};
        const events = [];
        const healthDelta = Number(newData.health || 0) - Number(oldData.health || 0);
        let elixirDelta = Number(newData.elixir || 0) - Number(oldData.elixir || 0);
        let magicDelta = Number(newData.magic || 0) - Number(oldData.magic || 0);
        const armorDelta = Number(newData.armor || 0) - Number(oldData.armor || 0);
        const poisonDelta = Number(newData.poison || 0) - Number(oldData.poison || 0);
        const fireDelta = Number(newData.fire || 0) - Number(oldData.fire || 0);
        const oldEquipCount = Array.isArray(oldData.equipment) ? oldData.equipment.length : 0;
        const newEquipCount = Array.isArray(newData.equipment) ? newData.equipment.length : 0;
        const localCost = takeLocalResourceCostForState(ref, oldData, newData);
        const resourceCost = localCost || takeOptimisticResourceCostForState(ref);
        const resourceDelay = resourceCost ? 220 : 0;
        const damageHits = damageLogEvents.get(ref.id) || [];
        const healthMax = getBarMaxForKey(newData, 'health');
        const elixirMax = getBarMaxForKey(newData, 'elixir');
        const magicMax = getBarMaxForKey(newData, 'magic');
        const oldHealth = getBarValueForKey(oldData, 'health');
        const newHealth = getBarValueForKey(newData, 'health');
        const oldElixir = getBarValueForKey(oldData, 'elixir');
        const newElixir = getBarValueForKey(newData, 'elixir');
        const oldMagic = getBarValueForKey(oldData, 'magic');
        const newMagic = getBarValueForKey(newData, 'magic');
        let stagedHealth = oldHealth;
        let lastHealthDelay = 0;
        const skinDamageEvents = [];
        const inferredStatusDamageKind = inferStatusDamageKindForRef(previous, next, ref, oldData, newData, healthDelta, damageHits);
        if (damageHits.length) {
            damageHits.forEach((hit, hitIndex) => {
                const amount = Number(hit && hit.amount);
                if (!Number.isFinite(amount) || amount <= 0) return;
                const delay = hitIndex * 200;
                stagedHealth = Number.isFinite(Number(hit.health)) ? Number(hit.health) : stagedHealth - amount;
                lastHealthDelay = delay;
                skinDamageEvents.push({ delay, kind: hit.visualKind || 'damage' });
                events.push({
                    text: `-${amount}H`,
                    kind: 'damage',
                    delay,
                    stackIndex: 0,
                    barKey: 'health',
                    barValue: stagedHealth,
                    barMax: healthMax,
                });
            });
            if (stagedHealth !== newHealth) {
                const delta = newHealth - stagedHealth;
                events.push({
                    text: `${delta > 0 ? '+' : ''}${delta}H`,
                    kind: delta > 0 ? 'heal' : 'damage',
                    delay: lastHealthDelay + 200,
                    stackIndex: 0,
                    barKey: 'health',
                    barValue: newHealth,
                    barMax: healthMax,
                });
            }
        } else if (healthDelta < 0) {
            events.push({ text: `${healthDelta}H`, kind: 'damage', barKey: 'health', barValue: newHealth, barMax: healthMax });
            skinDamageEvents.push({ delay: 0, kind: 'damage' });
        } else if (healthDelta > 0) {
            events.push({ text: `+${healthDelta}H`, kind: 'heal', barKey: 'health', barValue: newHealth, barMax: healthMax });
        }
        if (armorDelta > 0) events.push({ text: `+${armorDelta}A`, kind: 'armor' });
        else if (armorDelta < 0) events.push({ text: `${armorDelta}A`, kind: 'armor' });
        if (poisonDelta > 0) events.push({ text: `+${poisonDelta}P`, kind: 'poison' });
        else if (poisonDelta < 0) events.push({ text: `${poisonDelta}P`, kind: 'poison' });
        if (fireDelta > 0) events.push({ text: `+${fireDelta}F`, kind: 'fire' });
        else if (fireDelta < 0) events.push({ text: `${fireDelta}F`, kind: 'fire' });
        let stagedElixir = oldElixir;
        let stagedMagic = oldMagic;
        const barStartValues = {};
        if (resourceCost && resourceCost.totalE > 0) {
            stagedElixir -= resourceCost.totalE;
            if (resourceCost.shownOptimistically) {
                barStartValues.elixir = stagedElixir;
            } else {
                events.push({
                    text: `-${resourceCost.totalE}E`,
                    kind: 'elixir',
                    delay: 0,
                    stackIndex: 0,
                    barKey: 'elixir',
                    barValue: stagedElixir,
                    barMax: elixirMax,
                });
            }
            elixirDelta += resourceCost.totalE;
        }
        if (resourceCost && resourceCost.totalM > 0) {
            stagedMagic -= resourceCost.totalM;
            if (resourceCost.shownOptimistically) {
                barStartValues.magic = stagedMagic;
            } else {
                events.push({
                    text: `-${resourceCost.totalM}M`,
                    kind: 'magic',
                    delay: resourceCost.totalE > 0 ? 120 : 0,
                    stackIndex: 1,
                    barKey: 'magic',
                    barValue: stagedMagic,
                    barMax: magicMax,
                });
            }
            magicDelta += resourceCost.totalM;
        }
        if (elixirDelta > 0) {
            events.push({ text: `+${elixirDelta}E`, kind: 'elixir', delay: resourceDelay, stackIndex: resourceCost ? 1 : undefined, barKey: 'elixir', barValue: newElixir, barMax: elixirMax });
        } else if (elixirDelta < 0) {
            events.push({ text: `${elixirDelta}E`, kind: 'elixir', delay: resourceDelay, stackIndex: resourceCost ? 1 : undefined, barKey: 'elixir', barValue: newElixir, barMax: elixirMax });
        }
        if (magicDelta > 0) {
            events.push({ text: `+${magicDelta}M`, kind: 'magic', delay: resourceDelay, stackIndex: resourceCost ? 2 : undefined, barKey: 'magic', barValue: newMagic, barMax: magicMax });
        } else if (magicDelta < 0) {
            events.push({ text: `${magicDelta}M`, kind: 'magic', delay: resourceDelay, stackIndex: resourceCost ? 2 : undefined, barKey: 'magic', barValue: newMagic, barMax: magicMax });
        }
        if (inferredStatusDamageKind && !skinDamageEvents.some(event => event.kind === 'poison' || event.kind === 'fire')) {
            if (skinDamageEvents.length) skinDamageEvents[0].kind = inferredStatusDamageKind;
            else skinDamageEvents.push({ delay: 0, kind: inferredStatusDamageKind });
        }
        const scheduledEvents = showCombatFloatSequence(ref.selector, events);
        scheduleSkinDamageMoods(ref.id, skinDamageEvents);
        animateBarEventSequence(ref.selector, scheduledEvents, oldData, newData, { startValues: barStartValues });
        if (newEquipCount > oldEquipCount) {
            setTimeout(() => animateEquipmentForRegion(ref.selector), 30);
        }
    });
}

function clearScheduledGameOver() {
    if (gameOverRenderTimer) {
        clearTimeout(gameOverRenderTimer);
        gameOverRenderTimer = null;
    }
    scheduledGameOverState = null;
}

function estimateGameOverAnimationDelay(previous, next) {
    if (!previous || !next || !areSequentialGameStates(previous, next, { allowSoloPerspectiveShift: true })) return 0;
    const damageCount = getNewBattleLogLines(previous, next)
        .reduce((count, line) => count + parseDamageLogLine(line).length, 0);
    if (damageCount <= 0) return 650;
    const rawLastDelay = Math.max(0, damageCount - 1) * 200;
    const lastDelay = Math.min(rawLastDelay, Math.max(0, COMBAT_FLOAT_MAX_LAST_DELAY_MS));
    const durationRoom = COMBAT_FLOAT_TOTAL_LIMIT_MS - lastDelay - COMBAT_FLOAT_END_PAD_MS;
    const duration = Math.max(COMBAT_FLOAT_MIN_DURATION_MS, Math.min(COMBAT_FLOAT_BASE_DURATION_MS, durationRoom));
    return Math.min(COMBAT_FLOAT_TOTAL_LIMIT_MS, Math.max(950, lastDelay + duration + COMBAT_FLOAT_END_PAD_MS));
}

function renderGameOverAfterFinalAnimation(previous, next, options = {}) {
    clearScheduledGameOver();
    const shouldAnimate = previous
        && next
        && previous.phase !== 'game_over'
        && next.phase === 'game_over'
        && areSequentialGameStates(previous, next, { allowSoloPerspectiveShift: true });
    if (!shouldAnimate) {
        if (options.tutorial) stopTutorialUiForGameOver();
        if (options.fullScreen === false) renderGame(next);
        else renderGameOver(next);
        return;
    }
    if (options.tutorial) stopTutorialUiForGameOver();
    showView('view-game');
    const previewState = options.deferResultLabels
        ? { ...next, phase: (previous && previous.phase && previous.phase !== 'game_over') ? previous.phase : 'action' }
        : next;
    renderGame(previewState);
    showStateDeltas(previous, next);
    updateStatus(UI.game_over);
    const delay = estimateGameOverAnimationDelay(previous, next);
    scheduledGameOverState = next;
    gameOverRenderTimer = setTimeout(() => {
        gameOverRenderTimer = null;
        const finalState = gameState && gameState.phase === 'game_over'
            ? gameState
            : scheduledGameOverState;
        scheduledGameOverState = null;
        if (!finalState || finalState.phase !== 'game_over') return;
        if (options.fullScreen === false) renderGame(finalState);
        else renderGameOver(finalState);
    }, delay);
}

function normalizeTargetCandidates(candidates) {
    if (Array.isArray(candidates)) return candidates.map(String);
    if (candidates == null || candidates === '') return ['enemy'];
    return String(candidates).split(',').map(s => s.trim()).filter(Boolean);
}

function targetCandidateAllows(role, candidates) {
    const set = new Set(normalizeTargetCandidates(candidates));
    if (set.has('both') || set.has('all') || set.has('random_player') || set.has('random_side')) return true;
    if (role === 'self') return set.has('self') || set.has('friendly') || set.has('random_friendly');
    if (role === 'teammate') return set.has('teammate') || set.has('friendly') || set.has('random_friendly');
    if (role === 'enemy') return set.has('enemy') || set.has('all_enemies') || set.has('random_enemy');
    return false;
}

function getPlayerTargetOptions({ includeSelf = false, aliveOnly = true, candidates = 'enemy' } = {}) {
    if (!gameState) return [];
    const out = [];
    const add = (id, data, group, role) => {
        const targetId = normalizePlayerId(id);
        if (targetId == null || (!includeSelf && targetId === normalizePlayerId(gameState.your_id))) return;
        if (!targetCandidateAllows(role, candidates)) return;
        const stateData = getPlayerDataById(targetId) || data || {};
        const alive = (stateData && Number(stateData.health || 0) > 0);
        if (aliveOnly && !alive) return;
        if (targetId !== normalizePlayerId(gameState.your_id) && stateData && stateData.untargetable) return;
        out.push({
            id: targetId,
            group,
            label: `${group} ${getPlayerNameById(targetId)} H:${stateData ? (stateData.health || 0) : 0}/${stateData ? (stateData.max_health || 0) : 0}`,
            alive
        });
    };
    if (gameState.mode !== '2v2') {
        const yourId = normalizePlayerId(gameState.your_id);
        const enemyId = yourId === 1 ? 0 : 1;
        add(enemyId, gameState.opponent || {}, UI.enemy_label || UI.opponent, 'enemy');
        add(yourId, gameState.you || {}, UI.you, 'self');
        return out;
    }
    const enemies = [gameState.opponent || {}, gameState.opponent2 || {}];
    (gameState.enemy_ids || []).forEach((id, i) => add(id, enemies[i], UI.enemy_label || UI.opponent, 'enemy'));
    if (gameState.teammate_id != null) add(gameState.teammate_id, gameState.teammate || {}, UI.ally_label || UI.teammate, 'teammate');
    add(gameState.your_id, gameState.you || {}, UI.you, 'self');
    return out;
}

async function choosePlayerTarget(title, opts = {}) {
    const targets = getPlayerTargetOptions(opts);
    if (!targets.length) {
        gameAlert(UI.notice, UI.no_valid_target || 'No valid target');
        return -1;
    }
    if (targets.length === 1) {
        flashTargetRegion(targets[0].id);
        return targets[0].id;
    }
    const boardTarget = await choosePlayerTargetOnBoard(title, targets);
    if (boardTarget !== null) {
        return boardTarget;
    }
    if (gameState && gameState.mode === '2v2') {
        return -1;
    }
    const sel = await simpleChoice(title || UI.choose_target || UI.select_target || 'Choose target', targets.map(t => t.label));
    const selectedId = sel >= 0 ? targets[sel].id : -1;
    if (selectedId >= 0) flashTargetRegion(selectedId);
    return selectedId;
}

function getCardTargetPickOptions(cardDef) {
    if (!cardDef || !gameState) {
        return {};
    }
    if (cardHasSelfOnlyFlag({}, cardDef) && cardDef.card_type !== 'thorn') {
        return { includeSelf: true, candidates: 'self', aliveOnly: true };
    }
    if (cardDef.card_type === 'thorn') {
        return {
            includeSelf: false,
            candidates: gameState.mode === '2v2' ? 'all' : 'enemy',
            aliveOnly: true,
        };
    }
    return { includeSelf: true, candidates: 'all', aliveOnly: true };
}

function effectTreeUsesEventTarget(value) {
    if (['event_target', 'target', 'enemy', 'choice_target', 'selected_target', 'chosen_target'].includes(value)) return true;
    if (Array.isArray(value)) return value.some(effectTreeUsesEventTarget);
    if (value && typeof value === 'object') {
        return Object.values(value).some(effectTreeUsesEventTarget);
    }
    return false;
}

function getEquipmentTriggerPayloads(cardDef) {
    if (!cardDef || cardDef.card_type !== 'root') return [];
    const payloads = [];
    const effects = Array.isArray(cardDef.effects) ? cardDef.effects : [];
    effects.forEach(effect => {
        if (effect && effect.type === 'on_equipment_trigger') {
            payloads.push(effect.params || effect);
        }
    });
    const scripts = cardDef.scripts && typeof cardDef.scripts === 'object' ? cardDef.scripts : {};
    ['onEquipmentTrigger', 'on_equipment_trigger', 'equipment_trigger'].forEach(key => {
        if (scripts[key]) payloads.push(scripts[key]);
    });
    const v2Events = (cardDef.v2_events && typeof cardDef.v2_events === 'object')
        ? cardDef.v2_events
        : ((cardDef.v2_resource && cardDef.v2_resource.events && typeof cardDef.v2_resource.events === 'object')
            ? cardDef.v2_resource.events
            : {});
    ['on_equipment_trigger', 'equipment_trigger'].forEach(key => {
        if (v2Events[key]) payloads.push(v2Events[key]);
    });
    return payloads;
}

function equipmentChoosesTargetOnTrigger(cardDef) {
    if (!cardDef || cardDef.card_type !== 'root') return false;
    const triggerCost = Number(cardDef.trigger_cost_e);
    if (!Number.isFinite(triggerCost) || triggerCost < 0) return false;
    return true;
}

function equipmentTriggerForbidsSelfTarget(cardDef) {
    if (!cardDef || cardDef.card_type !== 'root') return false;
    if (cardHasSelfOnlyFlag({}, cardDef)) return false;
    return getEquipmentTriggerPayloads(cardDef).some(effectTreeUsesEventTarget);
}

function getCardPlayPayloads(cardDef) {
    if (!cardDef) return [];
    const payloads = [];
    const effects = Array.isArray(cardDef.effects) ? cardDef.effects : [];
    effects.forEach(effect => {
        if (effect && (effect.type === 'on_play' || effect.type === 'play')) {
            payloads.push(effect.params || effect);
        }
    });
    const scripts = cardDef.scripts && typeof cardDef.scripts === 'object' ? cardDef.scripts : {};
    ['onPlay', 'on_play', 'play'].forEach(key => {
        if (scripts[key]) payloads.push(scripts[key]);
    });
    const v2Events = (cardDef.v2_events && typeof cardDef.v2_events === 'object')
        ? cardDef.v2_events
        : ((cardDef.v2_resource && cardDef.v2_resource.events && typeof cardDef.v2_resource.events === 'object')
            ? cardDef.v2_resource.events
            : {});
    ['on_play', 'play', 'onPlay'].forEach(key => {
        if (v2Events[key]) payloads.push(v2Events[key]);
    });
    return payloads;
}

function cardPlayChoosesTarget(cardDef) {
    return getCardPlayPayloads(cardDef).some(effectTreeUsesEventTarget);
}

async function chooseEnemyTarget(title) {
    const targets = getEnemyTargetOptions();
    if (!targets.length) {
        gameAlert(UI.notice, UI.no_valid_target || 'No valid target');
        return -1;
    }
    if (targets.length === 1) {
        flashTargetRegion(targets[0].id);
        return targets[0].id;
    }
    const sel = await simpleChoice(title || UI.choose_target || UI.select_target || 'Choose target', targets.map(t => t.label));
    const selectedId = sel >= 0 ? targets[sel].id : -1;
    if (selectedId >= 0) flashTargetRegion(selectedId);
    return selectedId;
}

function cardNeedsPlayerTarget(cardDef, cardDict = null) {
    const gs = gameState || {};
    if (!cardDef) return false;
    if (cardHasSelfOnlyFlag(cardDict || {}, cardDef) && cardDef.card_type !== 'thorn') return false;
    if (cardDef.card_type === 'guard') return false;
    if (cardDef.card_type === 'thorn') return gs.mode === '2v2';
    if (cardDef.card_type === 'root') return true;
    if (['bloom', 'root'].includes(cardDef.card_type)) return true;
    return false;
}

function cardNeedsEnemyPlayerTarget(cardDef) {
    if (!cardDef) return false;
    if (cardDef.card_type === 'thorn') return true;
    const ids = new Set(['Iris', 'Fire', 'Cancer']);
    if (ids.has(cardDef.id)) return true;
    const effects = Array.isArray(cardDef.effects) ? cardDef.effects : [];
    if (effects.some(effect => {
        const params = effect && effect.params ? effect.params : {};
        const target = params.target || params.targets || params.target1 || params.target2;
        return ['enemy', 'all_enemies', 'random_enemy'].includes(target);
    })) return true;
    const v2Events = (cardDef.v2_events && typeof cardDef.v2_events === 'object')
        ? cardDef.v2_events
        : ((cardDef.v2_resource && cardDef.v2_resource.events && typeof cardDef.v2_resource.events === 'object')
            ? cardDef.v2_resource.events
            : {});
    return Object.values(v2Events).some(effectTreeUsesEventTarget);
}

function renderEquipment(containerId, playerData, isMyEquipment) {
    const container = $(containerId);
    if (!container) return;
    container.innerHTML = '';
    const equipment = playerData.equipment || [];
    equipment.forEach(eqDict => {
        const cardInst = eqDict.card_instance || {};
        const cardDef = getCardDef(cardInst.def_id);
        if (!cardDef) return;
        const turns = eqDict.turns_equipped || 0;
        const corruption = eqDict.corruption_active || false;
        const el = document.createElement('div');
        el.className = 'equip-item';
        const indestructible = (cardDef.flags || []).includes('indestructible');
        if (indestructible) {
            el.style.color = COLORS.indestructible;
            el.style.background = COLORS.indestructible_bg;
        }
        const targetId = normalizePlayerId(eqDict.effect_target);
        const ownerId = normalizePlayerId(playerData.player_id ?? eqDict.owner);
        const targetSuffix = gameState && gameState.mode === '2v2' && targetId != null && targetId !== ownerId
            ? `→${getPlayerNameById(targetId)}`
            : '';
        const customVars = eqDict.custom_vars || {};
        const layerValue = Number(customVars.layers || customVars.layer || 0);
        const layerSuffix = layerValue > 0 ? ` · 层数:${layerValue}` : '';
        const equipName = `${getCardName(cardDef)}${targetSuffix ? `(${targetSuffix})` : ''}`;
        const equipDisplayName = `${equipName}${layerSuffix}`;
        const fullText = UI.equip_info.replace('{0}', equipName).replace('{1}', turns) + layerSuffix + (corruption ? UI.equip_corruption : '');
        const compactTextValue = `${equipName}${turns ? ` · ${turns}` : ''}${layerSuffix}${corruption ? ` · ${UI.compact_corrupted}` : ''}`;
        const text = isMinimalUiStyle() ? compactTextValue : fullText;
        const triggerReady = !(cardInst.def_id === 'Flower' && turns < 2);
        if (cardDef.trigger_cost_e >= 0 && isMyEquipment && turns >= 1 && triggerReady && isFriendlyTurn() && !isSpectating) {
            const btn = document.createElement('button');
            btn.className = 'btn btn-small btn-equip-trigger';
            const triggerText = UI.equip_trigger_cost.replace('{0}', fullText).replace('{1}', cardDef.trigger_cost_e);
            const visibleText = isMinimalUiStyle() ? `⚡ ${equipDisplayName} ${cardDef.trigger_cost_e}E` : triggerText;
            btn.innerHTML = `${getEquipmentIconHtml(cardInst, cardDef)}<span class="equip-trigger-text">${escapeHtml(visibleText)}</span>`;
            btn.title = isMinimalUiStyle() ? triggerText : '';
            btn.disabled = isActionBusy({ includeAnimation: false });
            attachFloatingCardPreview(btn, cardInst);
            btn.onclick = async () => {
                if (!canSendGameAction('use_trigger', { includeAnimation: false })) return;
                const payload = { equipment_instance_id: cardInst.instance_id };
                if (equipmentChoosesTargetOnTrigger(cardDef)) {
                    const targetId = cardHasSelfOnlyFlag(cardInst, cardDef)
                        ? normalizePlayerId(gameState && gameState.your_id)
                        : await choosePlayerTarget(
                            UI.choose_target || UI.select_target || 'Choose target',
                            equipmentTriggerForbidsSelfTarget(cardDef)
                                ? { includeSelf: false, candidates: 'all', aliveOnly: true }
                                : { includeSelf: true, candidates: 'all', aliveOnly: true },
                        );
                    if (targetId < 0) return;
                    payload.target_player_id = targetId;
                }
                const triggerCost = Math.max(0, Number(cardDef.trigger_cost_e) || 0);
                if (triggerCost > 0) {
                    const optimisticCost = { totalE: triggerCost, totalM: 0 };
                    const override = {
                        playerId: normalizePlayerId(gameState && gameState.your_id),
                        elixir: Math.max(0, getBarValueForKey(gameState && gameState.you, 'elixir') - triggerCost),
                        magic: getBarValueForKey(gameState && gameState.you, 'magic'),
                        maxElixir: getBarMaxForKey(gameState && gameState.you, 'elixir'),
                        maxMagic: getBarMaxForKey(gameState && gameState.you, 'magic'),
                        totalE: triggerCost,
                        totalM: 0,
                    };
                    beginPendingServerAction('trigger', { optimisticResources: override, timeoutMs: SERVER_ACTION_TIMEOUT_MS });
                    queueOptimisticResourceCost(optimisticCost);
                } else {
                    beginPendingServerAction('trigger', { timeoutMs: SERVER_ACTION_TIMEOUT_MS });
                }
                emitModeEvent('solo_use_trigger', 'use_trigger', payload);
            };
            container.appendChild(btn);
        } else {
            el.innerHTML = `${getEquipmentIconHtml(cardInst, cardDef)}<span class="equip-name">${escapeHtml(text)}</span>`;
            el.title = isMinimalUiStyle() ? fullText : '';
            attachFloatingCardPreview(el, cardInst);
            container.appendChild(el);
        }
    });
}

function createBattleLogElement(entry) {
    const el = document.createElement('div');
    if (entry.type === 'chat') {
        el.className = 'log-entry log-chat';
        const channelLabel = getChatChannelLogLabel(entry);
        if (channelLabel) {
            const channelSpan = document.createElement('span');
            channelSpan.className = `chat-channel chat-channel-${entry.channel || 'public'}`;
            channelSpan.textContent = `[${channelLabel}] `;
            el.appendChild(channelSpan);
        }
    const nameSpan = document.createElement('span');
    nameSpan.className = 'chat-nick';
    if (entry.system) nameSpan.classList.add('system-name');
    if (entry.isAdmin) nameSpan.classList.add('admin-name');
        if (entry.specialRoleColor === 'bloom') nameSpan.classList.add('bloom-name');
        if (entry.specialRoleColor === 'guard') nameSpan.classList.add('guard-name');
        nameSpan.textContent = entry.system ? `${entry.nick} ` : `${entry.nick}: `;
        el.appendChild(nameSpan);
        el.appendChild(document.createTextNode(entry.text));
        const repeatCount = Number(entry.repeatCount || entry.repeat_count || 1);
        if (repeatCount > 1) {
            const repeatSpan = document.createElement('span');
            repeatSpan.className = 'chat-repeat-count';
            repeatSpan.textContent = ` ×${repeatCount}`;
            el.appendChild(repeatSpan);
        }
        if (isReportableChatEntry(entry)) {
            el.appendChild(createReportButton(chatEntryReportMeta(entry), {
                className: 'report-inline-btn chat-report-btn',
                text: UI.report,
                title: UI.report_chat,
            }));
        }
        return el;
    }
    const line = entry.text || '';
    const displayLine = translateLogLine(line);
    const styleLine = String(displayLine || line).toLowerCase();
    el.className = 'log-entry';
    if (styleLine.includes('damage') || styleLine.includes('degats') || styleLine.includes('dano') || styleLine.includes('\u9020\u6210') || styleLine.includes('\u4f24\u5bb3') || line.includes('D')) el.classList.add('log-damage');
    else if (styleLine.includes('+h') || styleLine.includes('recover') || styleLine.includes('recupera') || styleLine.includes('\u56de\u590d') || styleLine.includes('\u56de\u5fa9')) el.classList.add('log-heal');
    else if (styleLine.includes('poison') || styleLine.includes('veneno') || styleLine.includes('\u4e2d\u6bd2') || styleLine.includes('\u6bd2')) el.classList.add('log-poison');
    else if (styleLine.includes('burn') || styleLine.includes('queima') || styleLine.includes('\u707c\u70e7') || styleLine.includes('\u706b\u50b7')) el.classList.add('log-fire');
    else if (styleLine.includes('+e') || styleLine.includes('energy') || styleLine.includes('energia') || styleLine.includes('\u80fd\u91cf')) el.classList.add('log-elixir');
    else if (styleLine.includes('+m') || styleLine.includes('magic') || styleLine.includes('magie') || styleLine.includes('mana') || styleLine.includes('\u9b54\u529b')) el.classList.add('log-magic');
    else if (line.includes('===')) el.classList.add('log-round');
    el.textContent = displayLine;
    return el;
}

function resetBattleLogDom(content) {
    if (content) content.innerHTML = '';
    renderedTimelineDomCount = 0;
}

function resetBattleLogState(content) {
    gameTimelineEntries = [];
    renderedBattleLogCount = 0;
    renderedBattleLogTotal = 0;
    renderedClassicLogSignature = '';
    renderedBattleLogSnapshot = [];
    const classicContent = $('classic-log-content');
    if (classicContent) {
        classicContent.dataset.renderSignature = '';
        classicContent.innerHTML = '';
    }
    resetBattleLogDom(content);
}

function parseBattleDamageLogForCompact(line) {
    const text = String(line || '');
    let pointMatch = text.match(/^(.+?)受到(\d+(?:\+\d+)*)点(?:[^（）()]*?)伤害[（(]H=([^）)]+)[）)]$/);
    if (pointMatch) {
        const parts = pointMatch[2].split('+').map(v => Number(v || 0));
        return {
            target: pointMatch[1],
            units: [{ expr: formatBattleDamagePartsForCompact(parts), parts }],
            hp: String(pointMatch[3] || '').split('→').filter(Boolean),
        };
    }
    let match = text.match(/^(.+?)受到(\d+)D(?:×(\d+))?(?:×(\d+))?[（(]H=([^）)]+)[）)]$/);
    if (match) {
        const inner = Math.max(1, Number(match[3] || 1));
        const outer = Math.max(1, Number(match[4] || 1));
        const expr = `${match[2]}D${inner > 1 ? `×${inner}` : ''}`;
        return {
            target: match[1],
            units: Array.from({ length: outer }, () => ({ expr, parts: Array(inner).fill(Number(match[2])) })),
            hp: String(match[5] || '').split('→').filter(Boolean),
        };
    }
    match = text.match(/^(.+?)受到[（(](\d+(?:\+\d+)*)[）)]D[（(]H=([^）)]+)[）)]$/);
    if (match) {
        const parts = match[2].split('+').map(v => Number(v || 0));
        return {
            target: match[1],
            units: [{ expr: `(${parts.join('+')})D`, parts }],
            hp: String(match[3] || '').split('→').filter(Boolean),
        };
    }
    return null;
}

function formatBattleDamagePartsForCompact(parts) {
    const values = (parts || []).map(v => Number(v || 0));
    if (!values.length) return '0D';
    if (values.length === 1) return `${values[0]}D`;
    if (values.every(v => v === values[0])) return `${values[0]}D×${values.length}`;
    return `(${values.join('+')})D`;
}

function formatBattleDamageUnitsForCompact(units) {
    const clean = (units || []).map(unit => ({
        expr: String(unit && unit.expr || ''),
        parts: Array.isArray(unit && unit.parts) ? unit.parts.map(v => Number(v || 0)) : [],
    })).filter(unit => unit.expr);
    if (!clean.length) return '0D';
    if (clean.every(unit => unit.expr === clean[0].expr)) {
        return clean.length === 1 ? clean[0].expr : `${clean[0].expr}×${clean.length}`;
    }
    const parts = clean.flatMap(unit => unit.parts);
    if (parts.length && parts.every(v => v === parts[0])) return `${parts[0]}D×${parts.length}`;
    return `(${parts.join('+')})D`;
}

function mergeBattleHpChainForCompact(a, b) {
    const left = Array.isArray(a) ? a.slice() : [];
    const right = Array.isArray(b) ? b.slice() : [];
    if (!left.length) return right;
    if (!right.length) return left;
    if (left[left.length - 1] === right[0]) return left.concat(right.slice(1));
    return left.concat(right);
}

function parseBattleUseLogForCompact(line) {
    const match = String(line || '').match(/^(.+?)使用了?([^，]+?)(?: ×(\d+))?$/);
    if (!match) return null;
    return { actor: match[1], card: match[2], count: Math.max(1, Number(match[3] || 1)) };
}

function formatBattleUseLogForCompact(use) {
    if (!use) return '';
    return `${use.actor}使用了${use.card}${use.count > 1 ? ` ×${use.count}` : ''}`;
}

function formatBattleDamageLogForCompact(damage) {
    if (!damage) return '';
    return `${damage.target}受到${formatBattleDamageUnitsForCompact(damage.units)}（H=${(damage.hp || []).join('→')}）`;
}

function compactBattleLogLinesForDisplay(log) {
    const output = [];
    const rawLines = Array.isArray(log) ? log.map(line => String(line || '')) : [];
    for (const line of rawLines) {
        const use = parseBattleUseLogForCompact(line);
        if (use) {
            const last = output[output.length - 1];
            const previous = output[output.length - 2];
            if (last && last.kind === 'damage') {
                if (previous && previous.kind === 'use' && previous.actor === use.actor && previous.card === use.card) {
                    previous.count += use.count;
                } else {
                    output.splice(output.length - 1, 0, { kind: 'use', ...use });
                }
                continue;
            }
            if (last && last.kind === 'use' && last.actor === use.actor && last.card === use.card) {
                last.count += use.count;
                continue;
            }
            output.push({ kind: 'use', ...use });
            continue;
        }
        const damage = parseBattleDamageLogForCompact(line);
        if (damage) {
            const last = output[output.length - 1];
            if (last && last.kind === 'damage' && last.target === damage.target) {
                last.units = (last.units || []).concat(damage.units || []);
                last.hp = mergeBattleHpChainForCompact(last.hp, damage.hp);
                continue;
            }
            output.push({ kind: 'damage', ...damage });
            continue;
        }
        output.push({ kind: 'raw', text: line });
    }
    return output.map(entry => {
        if (entry.kind === 'use') return formatBattleUseLogForCompact(entry);
        if (entry.kind === 'damage') return formatBattleDamageLogForCompact(entry);
        return entry.text || '';
    });
}

function renderLog(log, logStart = 0, logTotal = null) {
    const container = $('battle-log');
    if (!container) return;
    container.classList.toggle('blind-log-masked', getOwnBlindLevel() >= 2);
    let content = container.querySelector('.log-content');
    if (!content) {
        content = document.createElement('div');
        content.className = 'log-content';
        container.appendChild(content);
    }
    const wasAtBottom = content.scrollTop + content.clientHeight >= content.scrollHeight - 30;
    if (content.dataset.renderLang !== currentLang) {
        content.dataset.renderLang = currentLang;
        resetBattleLogState(content);
    }
    if (!Array.isArray(log)) log = [];
    log = compactBattleLogLinesForDisplay(log);
    logStart = 0;
    logTotal = log.length;
    const matchKey = phaseContextMatchKey(gameState);
    if (matchKey && renderedBattleLogMatchKey && renderedBattleLogMatchKey !== String(matchKey)) {
        resetBattleLogState(content);
    }
    if (matchKey) renderedBattleLogMatchKey = String(matchKey);
    if (logTotal < renderedBattleLogTotal || logStart > renderedBattleLogTotal) {
        resetBattleLogState(content);
        renderedBattleLogTotal = logStart;
    }
    const nextBattleSnapshot = log.map(line => String(line || ''));
    const canAppendBattleLog = renderedBattleLogSnapshot.length <= nextBattleSnapshot.length
        && renderedBattleLogSnapshot.every((line, index) => line === nextBattleSnapshot[index]);
    if (!canAppendBattleLog) {
        resetBattleLogState(content);
        renderedBattleLogTotal = logStart;
    }
    seedPregameChatEntriesForBattleLog();
    let startIndex = Math.max(0, renderedBattleLogTotal - logStart);
    if (startIndex > log.length) startIndex = 0;
    for (let i = startIndex; i < log.length; i++) {
        gameTimelineEntries.push({ type: 'battle', text: log[i] });
    }
    renderedBattleLogCount = log.length;
    renderedBattleLogTotal = logTotal;
    renderedBattleLogSnapshot = nextBattleSnapshot;
    if (renderedTimelineDomCount > gameTimelineEntries.length || content.children.length === 0) {
        resetBattleLogDom(content);
    }
    if (renderedTimelineDomCount < gameTimelineEntries.length) {
        const fragment = document.createDocumentFragment();
        for (let i = renderedTimelineDomCount; i < gameTimelineEntries.length; i++) {
            fragment.appendChild(createBattleLogElement(gameTimelineEntries[i]));
        }
        content.appendChild(fragment);
        renderedTimelineDomCount = gameTimelineEntries.length;
    }
    if (wasAtBottom) content.scrollTop = content.scrollHeight;
}

function getChatChannelLogLabel(entry) {
    const channel = entry && entry.channel;
    if (!channel) return '';
    if (channel === 'team') return t('chat_channel_team');
    if (channel === 'enemy') return t('chat_channel_enemy');
    if (channel === 'private') return tf('chat_channel_private_to', localizeCanonicalPlayerName(entry.targetName || '?'));
    return t('chat_channel_public');
}

function appendLobbyChat(nick, text, meta = {}) {
    const container = $('lobby-chat-log');
    if (!container) return;
    appendLobbyChatEntry({
        type: 'chat',
        nickname: meta.nickname || nick,
        display_nick: nick,
        message_id: meta.message_id || meta.messageId || '',
        sender_user_id: meta.sender_user_id || meta.senderUserId || meta.user_id || '',
        sender_name: meta.sender_name || meta.senderName || meta.nickname || nick,
        text,
        repeat_count: meta.repeat_count || 1,
        ...meta,
    });
}

function currentUserMentionKeys() {
    const keys = new Set();
    if (currentAccount) {
        if (currentAccount.id != null) keys.add(`user:${currentAccount.id}`);
        if (currentAccount.username) keys.add(`name:${String(currentAccount.username).toLowerCase()}`);
        if (currentAccount.player_id) keys.add(`pid:${String(currentAccount.player_id).toUpperCase()}`);
    }
    if (nickname) keys.add(`name:${String(nickname).toLowerCase()}`);
    return keys;
}

function entryMentionsCurrentUser(entry) {
    const mentions = Array.isArray(entry.mentions) ? entry.mentions : [];
    if (!mentions.length) return false;
    const keys = currentUserMentionKeys();
    return mentions.some(item => {
        if (!item) return false;
        if (item.user_id != null && keys.has(`user:${item.user_id}`)) return true;
        if (item.nickname && keys.has(`name:${String(item.nickname).toLowerCase()}`)) return true;
        if (item.player_id && keys.has(`pid:${String(item.player_id).toUpperCase()}`)) return true;
        return false;
    });
}

function lobbyChatEntryKey(entry = {}) {
    return String(entry.message_id || entry.messageId || entry.id || `${entry.time || ''}:${entry.nickname || ''}:${entry.text || ''}`);
}

function currentUserMentionTokens(entry = {}) {
    const tokens = new Set();
    const keys = currentUserMentionKeys();
    (Array.isArray(entry.mentions) ? entry.mentions : []).forEach(item => {
        if (!item) return;
        const matches =
            (item.user_id != null && keys.has(`user:${item.user_id}`))
            || (item.nickname && keys.has(`name:${String(item.nickname).toLowerCase()}`))
            || (item.player_id && keys.has(`pid:${String(item.player_id).toUpperCase()}`));
        if (!matches) return;
        if (item.nickname) tokens.add(String(item.nickname).toLowerCase());
        if (item.player_id) tokens.add(String(item.player_id).toUpperCase());
    });
    return tokens;
}

function appendChatTextWithMentions(parent, text, mentions = [], ownMentionTokens = new Set(), shouldFlashOwnMention = false) {
    const raw = String(text || '');
    const mentionNames = [];
    (Array.isArray(mentions) ? mentions : []).forEach(item => {
        if (!item) return;
        if (item.nickname) mentionNames.push(String(item.nickname));
        if (item.player_id) mentionNames.push(String(item.player_id));
    });
    const unique = [...new Set(mentionNames.filter(Boolean))].sort((a, b) => b.length - a.length);
    if (!unique.length) {
        parent.appendChild(document.createTextNode(raw));
        return;
    }
    const pattern = new RegExp('(@(?:' + unique.map(name => name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|') + '))(?![\\w\\u4e00-\\u9fff\\u3040-\\u30ff\\uac00-\\ud7af-])', 'gi');
    let last = 0;
    raw.replace(pattern, (match, token, offset) => {
        if (offset > last) parent.appendChild(document.createTextNode(raw.slice(last, offset)));
        const span = document.createElement('span');
        span.className = 'chat-mention-token';
        const tokenName = String(match || '').replace(/^@/, '');
        if (shouldFlashOwnMention && (ownMentionTokens.has(tokenName.toLowerCase()) || ownMentionTokens.has(tokenName.toUpperCase()))) {
            span.classList.add('mention-flash');
        }
        span.textContent = match;
        parent.appendChild(span);
        last = offset + match.length;
        return match;
    });
    if (last < raw.length) parent.appendChild(document.createTextNode(raw.slice(last)));
}

function appendLobbyChatEntry(entry = {}) {
    const container = $('lobby-chat-log');
    if (!container) return;
    if (entry.type === 'time') {
        const timeEl = document.createElement('div');
        timeEl.className = 'chat-time-separator';
        timeEl.textContent = entry.display_time || entry.displayTime || '';
        container.appendChild(timeEl);
        container.scrollTop = container.scrollHeight;
        return;
    }
    const el = document.createElement('div');
    el.className = 'chat-msg';
    const nameSpan = document.createElement('span');
    nameSpan.className = 'chat-nick';
    if (entry.system) nameSpan.classList.add('system-name');
    if (isAdminPlayer(entry)) nameSpan.classList.add('admin-name');
    if (getSpecialRoleColor(entry) === 'bloom') nameSpan.classList.add('bloom-name');
    if (getSpecialRoleColor(entry) === 'guard') nameSpan.classList.add('guard-name');
    const nick = entry.display_nick || getChatDisplayName(entry);
    nameSpan.textContent = entry.system ? `${nick} ` : `${nick}: `;
    el.appendChild(nameSpan);
    const mentionKey = lobbyChatEntryKey(entry);
    const ownMentionTokens = currentUserMentionTokens(entry);
    const shouldFlashOwnMention = ownMentionTokens.size > 0 && !readLobbyMentionIds.has(mentionKey);
    if (shouldFlashOwnMention) {
        el.dataset.mentionId = mentionKey;
    }
    appendChatTextWithMentions(el, entry.text || '', entry.mentions || [], ownMentionTokens, shouldFlashOwnMention);
    const repeatCount = Number(entry.repeat_count || entry.repeatCount || 1);
    if (repeatCount > 1) {
        const repeatSpan = document.createElement('span');
        repeatSpan.className = 'chat-repeat-count';
        repeatSpan.textContent = ` ×${repeatCount}`;
        el.appendChild(repeatSpan);
    }
    if (isReportableChatEntry(entry)) {
        el.appendChild(createReportButton(chatEntryReportMeta(entry), {
            className: 'report-inline-btn chat-report-btn',
            text: UI.report,
            title: UI.report_chat,
        }));
    }
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
}

function renderLobbyChatHistory(data = {}) {
    const container = $('lobby-chat-log');
    if (!container) return;
    const items = Array.isArray(data.items) ? data.items : [];
    const signature = JSON.stringify(items.map(entry => [
        entry && entry.type,
        entry && entry.id,
        entry && entry.time,
        entry && entry.nickname,
        entry && entry.text,
        entry && entry.repeat_count,
        entry && entry.display_time,
        entry && entry.chat_channel,
        entry && entry.system,
        entry && JSON.stringify(entry.mentions || []),
    ]));
    if (signature === lobbyChatHistorySignature) return;
    lobbyChatHistorySignature = signature;
    container.innerHTML = '';
    items.forEach(entry => appendLobbyChatEntry(entry));
    container.scrollTop = container.scrollHeight;
}

function appendGameChat(nick, text, meta = {}, channelMeta = {}) {
    gameTimelineEntries.push({
        type: 'chat',
        nick,
        text,
        message_id: meta.message_id || meta.messageId || '',
        sender_user_id: meta.sender_user_id || meta.senderUserId || meta.user_id || '',
        sender_name: meta.sender_name || meta.senderName || meta.nickname || nick,
        nickname: meta.nickname || nick,
        system: !!meta.system,
        isAdmin: isAdminPlayer(meta),
        specialRoleColor: getSpecialRoleColor(meta),
        channel: channelMeta.chat_channel || channelMeta.channel || '',
        targetName: channelMeta.chat_target_name || channelMeta.targetName || '',
    });
    renderLog((gameState && gameState.log) || [], (gameState && gameState.log_start) || 0, gameState && gameState.log_total);
}

function renderPendingCard() {
    const playZone = $('play-zone');
    if (!playZone || !pendingPlayCard) return;
    const cardDef = getCardDef(pendingPlayCard.def_id);
    const typeColor = cardDef ? (CARD_TYPE_COLORS[cardDef.card_type] || COLORS.text_primary) : COLORS.text_primary;
    const typeLabel = cardDef ? getCardTypeLabel(cardDef.card_type) : '';
    playZone.innerHTML = `
        <div class="pending-card" style="border-color:${typeColor}">
            <div style="color:${typeColor};font-weight:bold">${cardDef ? getCardName(cardDef) : '?'}</div>
            <div style="color:${typeColor};font-size:11px">${typeLabel}</div>
            <div style="color:${COLORS.damage};font-size:11px">${UI.waiting_response}</div>
        </div>
    `;
}

function isCardAnimationLocked() {
    return Date.now() < cardAnimationLockUntil;
}

function scheduleCardAnimationUnlock() {
    if (cardAnimationUnlockTimer) clearTimeout(cardAnimationUnlockTimer);
    const delay = Math.max(30, cardAnimationLockUntil - Date.now() + 30);
    cardAnimationUnlockTimer = setTimeout(() => {
        if (isCardAnimationLocked()) {
            scheduleCardAnimationUnlock();
            return;
        }
        document.body.classList.remove('card-animation-lock');
        cardAnimationUnlockTimer = null;
    }, delay);
}

function lockCardAnimation(duration = 320) {
    cardAnimationLockUntil = Math.max(cardAnimationLockUntil, Date.now() + duration);
    document.body.classList.add('card-animation-lock');
    scheduleCardAnimationUnlock();
}

function cardInstanceKey(card) {
    if (!card || card.instance_id == null) return '';
    return String(card.instance_id);
}

function cardHasExileLikeExit(card) {
    if (!card) return false;
    if (card.def_id === 'Yggdrasil') return true;
    const cardDef = getCardDef(card.def_id);
    const flags = new Set([
        ...((cardDef && cardDef.flags) || []),
        ...((card && card.instance_flags) || []),
    ]);
    return flags.has('exile');
}

function ensureLobbyMentionMenu() {
    if (lobbyMentionMenu) return lobbyMentionMenu;
    lobbyMentionMenu = document.createElement('div');
    lobbyMentionMenu.id = 'lobby-mention-menu';
    lobbyMentionMenu.className = 'mention-menu hidden';
    document.body.appendChild(lobbyMentionMenu);
    lobbyMentionMenu.addEventListener('mousedown', (event) => {
        const item = event.target.closest('[data-mention-index]');
        if (!item) return;
        event.preventDefault();
        const idx = Number(item.dataset.mentionIndex);
        const candidate = lobbyMentionCandidates[idx];
        if (candidate) insertLobbyMention(candidate);
    });
    return lobbyMentionMenu;
}

function getLobbyMentionCandidates() {
    const selfKeys = currentUserMentionKeys();
    return (Array.isArray(lobbyPlayers) ? lobbyPlayers : [])
        .map(player => ({
            nickname: player.nickname || player.name || '',
            player_id: player.player_id || '',
            user_id: player.user_id || '',
        }))
        .filter(item => item.nickname && !selfKeys.has(`name:${String(item.nickname).toLowerCase()}`));
}

function findLobbyMentionRange(input) {
    if (!input) return null;
    const value = input.value || '';
    const pos = input.selectionStart ?? value.length;
    const before = value.slice(0, pos);
    const match = before.match(/(^|\s)@([^\s@]*)$/);
    if (!match) return null;
    const start = before.length - match[0].length + match[1].length;
    return { start, end: pos, query: match[2] || '' };
}

function updateLobbyMentionMenu() {
    const input = $('lobby-chat-input');
    const menu = ensureLobbyMentionMenu();
    const range = findLobbyMentionRange(input);
    lobbyMentionActiveRange = range;
    if (!input || !range) {
        menu.classList.add('hidden');
        return;
    }
    const query = String(range.query || '').toLowerCase();
    lobbyMentionCandidates = getLobbyMentionCandidates()
        .filter(item => !query || String(item.nickname).toLowerCase().includes(query) || String(item.player_id).toLowerCase().includes(query))
        .slice(0, 8);
    if (!lobbyMentionCandidates.length) {
        menu.classList.add('hidden');
        return;
    }
    menu.innerHTML = lobbyMentionCandidates.map((item, index) => `
        <button type="button" class="mention-menu-item" data-mention-index="${index}">
          <span>@${escapeHtml(item.nickname)}</span>
          ${item.player_id ? `<small>${escapeHtml(item.player_id)}</small>` : ''}
        </button>
    `).join('');
    const rect = input.getBoundingClientRect();
    menu.style.left = `${Math.max(8, rect.left)}px`;
    menu.style.top = `${Math.max(8, rect.top - Math.min(220, menu.offsetHeight || 180) - 6)}px`;
    menu.style.width = `${Math.min(260, Math.max(180, rect.width))}px`;
    menu.classList.remove('hidden');
}

function insertLobbyMention(candidate) {
    const input = $('lobby-chat-input');
    if (!input || !lobbyMentionActiveRange) return;
    const value = input.value || '';
    const token = `@${candidate.nickname} `;
    input.value = value.slice(0, lobbyMentionActiveRange.start) + token + value.slice(lobbyMentionActiveRange.end);
    const pos = lobbyMentionActiveRange.start + token.length;
    input.focus();
    input.setSelectionRange(pos, pos);
    if (lobbyMentionMenu) lobbyMentionMenu.classList.add('hidden');
}

function clearLobbyMentionFlash() {
    document.querySelectorAll('#lobby-chat-log [data-mention-id]').forEach(el => {
        if (el.dataset.mentionId) readLobbyMentionIds.add(el.dataset.mentionId);
        el.removeAttribute('data-mention-id');
    });
    document.querySelectorAll('#lobby-chat-log .mention-flash').forEach(el => el.classList.remove('mention-flash'));
}

function markRecentlyPlayedExileCard(card) {
    const id = cardInstanceKey(card);
    if (!id) return;
    const expiresAt = Date.now() + 4200;
    recentlyPlayedExileCards.set(id, expiresAt);
    setTimeout(() => {
        if (recentlyPlayedExileCards.get(id) === expiresAt) {
            recentlyPlayedExileCards.delete(id);
        }
    }, 4300);
}

function wasRecentlyPlayedExileCard(id) {
    if (!id) return false;
    const expiresAt = recentlyPlayedExileCards.get(String(id));
    if (!expiresAt) return false;
    if (expiresAt < Date.now()) {
        recentlyPlayedExileCards.delete(String(id));
        return false;
    }
    return true;
}

function getNewlyExiledHandCards(previousPlayer, nextPlayer) {
    const oldHand = (previousPlayer && previousPlayer.hand) || [];
    const newHand = (nextPlayer && nextPlayer.hand) || [];
    if (!oldHand.length) return [];
    const newHandIds = new Set(newHand.map(cardInstanceKey).filter(Boolean));
    const oldExileIds = new Set(((previousPlayer && previousPlayer.exile) || []).map(cardInstanceKey).filter(Boolean));
    const nextExileIds = new Set(((nextPlayer && nextPlayer.exile) || []).map(cardInstanceKey).filter(Boolean));
    const exileCountIncreased = Number((nextPlayer && nextPlayer.exile_count) || 0) > Number((previousPlayer && previousPlayer.exile_count) || 0);
    return oldHand.filter(card => {
        const id = cardInstanceKey(card);
        if (!id || newHandIds.has(id)) return false;
        if (wasRecentlyPlayedExileCard(id)) {
            recentlyPlayedExileCards.delete(id);
            return false;
        }
        if (nextExileIds.has(id) && !oldExileIds.has(id)) return true;
        return exileCountIncreased && cardHasExileLikeExit(card);
    });
}

function animateCardShatterFromElement(cardEl, delay = 0) {
    if (!cardEl) return;
    const rect = cardEl.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;
    const wrap = document.createElement('div');
    wrap.className = 'card-shatter-wrap';
    wrap.style.left = `${rect.left}px`;
    wrap.style.top = `${rect.top}px`;
    wrap.style.width = `${rect.width}px`;
    wrap.style.height = `${rect.height}px`;
    const pieces = [
        { clip: 'polygon(0 0, 48% 0, 38% 34%, 0 45%)', x: -22, y: -18, r: -13 },
        { clip: 'polygon(48% 0, 100% 0, 100% 38%, 58% 32%, 38% 34%)', x: 20, y: -20, r: 12 },
        { clip: 'polygon(0 45%, 38% 34%, 44% 63%, 0 72%)', x: -28, y: 3, r: -18 },
        { clip: 'polygon(38% 34%, 58% 32%, 64% 66%, 44% 63%)', x: 0, y: -2, r: 7 },
        { clip: 'polygon(58% 32%, 100% 38%, 100% 70%, 64% 66%)', x: 28, y: 4, r: 18 },
        { clip: 'polygon(0 72%, 44% 63%, 40% 100%, 0 100%)', x: -18, y: 24, r: 11 },
        { clip: 'polygon(44% 63%, 64% 66%, 100% 70%, 100% 100%, 40% 100%)', x: 24, y: 26, r: -10 },
    ];
    pieces.forEach((piece, index) => {
        const shard = cardEl.cloneNode(true);
        shard.classList.remove('card-play-flash', 'fusion-merge-clone', 'fusion-core-pulse', 'hand-card-animating');
        shard.classList.add('card-shatter-piece');
        shard.style.left = '';
        shard.style.top = '';
        shard.style.right = '';
        shard.style.bottom = '';
        shard.style.width = '100%';
        shard.style.height = '100%';
        shard.style.clipPath = piece.clip;
        shard.style.setProperty('--shard-x', `${piece.x}px`);
        shard.style.setProperty('--shard-y', `${piece.y}px`);
        shard.style.setProperty('--shard-rot', `${piece.r}deg`);
        shard.style.animationDelay = `${delay + index * 18}ms`;
        wrap.appendChild(shard);
    });
    const crack = document.createElement('div');
    crack.className = 'card-shatter-crack';
    crack.style.animationDelay = `${delay}ms`;
    wrap.appendChild(crack);
    document.body.appendChild(wrap);
    lockCardAnimation(delay + 560);
    setTimeout(() => {
        wrap.remove();
        scheduleTutorialOverlayRefresh(30);
    }, delay + 680);
}

function queueVisibleHandExileAnimations(previous, next) {
    if (!areSequentialGameStates(previous, next) || isSpectating) return;
    const removed = getNewlyExiledHandCards(previous.you || {}, next.you || {});
    if (!removed.length) return;
    const hand = $('you-hand');
    if (!hand) return;
    removed.forEach((card, index) => {
        const id = cardInstanceKey(card);
        const cardEl = id ? hand.querySelector(`.card[data-instance-id="${id}"]`) : null;
        if (cardEl) animateCardShatterFromElement(cardEl, index * 70);
    });
}

function getDrawSourcePoint(finalRect) {
    if (!finalRect) return { x: -80, y: window.innerHeight * 0.82 };
    const hand = $('you-hand');
    const rect = hand ? hand.getBoundingClientRect() : null;
    const offset = Math.max(48, finalRect.width * 0.9);
    return {
        x: (rect ? rect.right : window.innerWidth) + offset,
        y: finalRect.top + finalRect.height / 2,
    };
}

function animateDrawnCard(cardEl, index = 0) {
    if (!cardEl) return 0;
    const finalRect = cardEl.getBoundingClientRect();
    const source = getDrawSourcePoint(finalRect);
    const finalX = finalRect.left + finalRect.width / 2;
    const finalY = finalRect.top + finalRect.height / 2;
    const dx = source.x - finalX;
    const dy = source.y - finalY;
    const delay = Math.min(index * 42, 126);
    const duration = 230;
    cardEl.classList.add('hand-card-animating');
    cardEl.style.transition = 'none';
    cardEl.style.opacity = '0';
    cardEl.style.transform = `translate3d(${dx}px, ${dy}px, 0) scale(0.78)`;
    lockCardAnimation(delay + duration + 90);
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            cardEl.style.transition = `transform ${duration}ms cubic-bezier(.2,.8,.2,1) ${delay}ms, opacity ${Math.max(160, duration - 50)}ms ease ${delay}ms`;
            cardEl.style.opacity = '';
            cardEl.style.transform = '';
        });
    });
    setTimeout(() => {
        cardEl.classList.remove('hand-card-animating');
        cardEl.style.transition = '';
        cardEl.style.opacity = '';
        cardEl.style.transform = '';
        scheduleTutorialOverlayRefresh(30);
    }, delay + duration + 80);
    return delay + duration;
}

function animateShiftedCard(cardEl, oldRect, delayed) {
    if (!cardEl || !oldRect) return 0;
    const newRect = cardEl.getBoundingClientRect();
    const dx = oldRect.left - newRect.left;
    const dy = oldRect.top - newRect.top;
    if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) return 0;
    const delay = delayed ? 70 : 0;
    const duration = 210;
    cardEl.classList.add('hand-card-animating');
    cardEl.style.transition = 'none';
    cardEl.style.transform = `translate3d(${dx}px, ${dy}px, 0)`;
    lockCardAnimation(delay + duration + 80);
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            cardEl.style.transition = `transform ${duration}ms cubic-bezier(.22,.82,.28,1) ${delay}ms`;
            cardEl.style.transform = '';
        });
    });
    setTimeout(() => {
        cardEl.classList.remove('hand-card-animating');
        cardEl.style.transition = '';
        cardEl.style.transform = '';
        scheduleTutorialOverlayRefresh(30);
    }, delay + duration + 70);
    return delay + duration;
}

function animateHandLayoutChanges(container, oldRects, hand) {
    if (!hasPlayerHandSnapshot || isSpectating || !container || !oldRects || oldRects.size === 0) return;
    const nextIds = new Set(hand.map(c => String(c.instance_id)));
    const removedCount = [...oldRects.keys()].filter(id => !nextIds.has(id)).length;
    let drawIndex = 0;
    hand.forEach(cardDict => {
        const id = String(cardDict.instance_id);
        const cardEl = container.querySelector(`.card[data-instance-id="${id}"]`);
        if (!cardEl) return;
        if (oldRects.has(id)) {
            animateShiftedCard(cardEl, oldRects.get(id), removedCount > 0);
        } else {
            animateDrawnCard(cardEl, drawIndex);
            drawIndex += 1;
        }
    });
}

function animatePlayedCard(cardInstanceId, options = {}) {
    const cardEl = document.querySelector(`.card[data-instance-id="${cardInstanceId}"]`);
    if (!cardEl) return;
    const rect = cardEl.getBoundingClientRect();
    const flash = cardEl.cloneNode(true);
    flash.classList.add('card-play-flash');
    flash.style.left = `${rect.left}px`;
    flash.style.top = `${rect.top}px`;
    flash.style.width = `${rect.width}px`;
    let targeted = false;
    if (options.targetElement) {
        const targetRect = options.targetElement.getBoundingClientRect();
        if (targetRect.width > 0 && targetRect.height > 0) {
            const dx = targetRect.left + targetRect.width / 2 - (rect.left + rect.width / 2);
            const dy = targetRect.top + targetRect.height / 2 - (rect.top + rect.height / 2);
            flash.classList.add('card-play-flash-targeted');
            flash.style.setProperty('--play-dx', `${dx}px`);
            flash.style.setProperty('--play-dy', `${dy}px`);
            targeted = true;
        }
    }
    document.body.appendChild(flash);
    if (options.shatterAfter) {
        lockCardAnimation(targeted ? 980 : 900);
        setTimeout(() => {
            animateCardShatterFromElement(flash);
            flash.remove();
        }, targeted ? 420 : 340);
        setTimeout(() => flash.remove(), targeted ? 900 : 760);
    } else {
        lockCardAnimation(targeted ? 500 : 360);
        setTimeout(() => flash.remove(), targeted ? 560 : 420);
    }
}

function animateFusionMerge(fusionCardId, targetIds = [], options = {}) {
    const startDelay = Number(options.startDelay || 0);
    const fusionEl = document.querySelector(`.card[data-instance-id="${fusionCardId}"]`);
    if (!fusionEl || !Array.isArray(targetIds) || !targetIds.length) {
        animatePlayedCard(fusionCardId);
        return;
    }
    const fusionRect = fusionEl.getBoundingClientRect();
    const centerX = fusionRect.left + fusionRect.width / 2;
    const centerY = fusionRect.top + fusionRect.height / 2;
    const clones = [];
    targetIds.slice(0, 3).forEach((id, index) => {
        const source = document.querySelector(`.card[data-instance-id="${id}"]`);
        if (!source) return;
        const rect = source.getBoundingClientRect();
        const clone = source.cloneNode(true);
        clone.classList.add('fusion-merge-clone');
        clone.style.left = `${rect.left}px`;
        clone.style.top = `${rect.top}px`;
        clone.style.width = `${rect.width}px`;
        clone.style.setProperty('--fusion-dx', `${centerX - (rect.left + rect.width / 2)}px`);
        clone.style.setProperty('--fusion-dy', `${centerY - (rect.top + rect.height / 2)}px`);
        clone.style.animationDelay = `${startDelay + index * 55}ms`;
        document.body.appendChild(clone);
        clones.push(clone);
    });
    const pulse = fusionEl.cloneNode(true);
    pulse.classList.add('fusion-core-pulse');
    pulse.style.left = `${fusionRect.left}px`;
    pulse.style.top = `${fusionRect.top}px`;
    pulse.style.width = `${fusionRect.width}px`;
    pulse.style.animationDelay = `${startDelay + Math.min(180, clones.length * 55 + 40)}ms`;
    document.body.appendChild(pulse);
    lockCardAnimation(startDelay + 680);
    setTimeout(() => {
        clones.forEach(el => el.remove());
        pulse.remove();
    }, startDelay + 780);
}

function animateEquipmentForRegion(selector) {
    const region = document.querySelector(selector);
    if (!region) return;
    const items = region.querySelectorAll('.equip-item, .equip-card, .btn-equip-trigger');
    const item = items[items.length - 1];
    if (!item) return;
    item.classList.remove('equip-pop-in');
    void item.offsetWidth;
    item.classList.add('equip-pop-in');
    setTimeout(() => item.classList.remove('equip-pop-in'), 520);
}

function cardChoiceIdentity(card) {
    if (!card) return '';
    const sortList = (list) => (Array.isArray(list) ? [...list].sort() : []).join(',');
    const cardDef = getCardDef(card.def_id || '');
    const flagSets = getEffectiveCardFlagSets(card, cardDef);
    const effectiveFlags = Array.from(flagSets.effective || []);
    const addedFlags = Array.from(flagSets.added || []);
    const disabledFlags = Array.from(flagSets.disabled || []);
    return [
        card.def_id || '',
        Number(card.fusion_level || 1),
        Number(card.fission_level || 1),
        card.cost_e_override == null ? '' : card.cost_e_override,
        card.cost_m_override == null ? '' : card.cost_m_override,
        sortList(effectiveFlags),
        sortList(addedFlags),
        sortList(disabledFlags),
        Number(card.bonus_damage || 0),
        Number(card.held_turns || 0),
        Number(card.return_to_hand_turns || 0),
        Number(card.mimic_discount || 0),
    ].join('|');
}

function dedupeCardCombos(combos) {
    const seen = new Set();
    const result = [];
    combos.forEach(combo => {
        const key = combo.map(cardChoiceIdentity).sort().join(' + ');
        if (seen.has(key)) return;
        seen.add(key);
        result.push(combo);
    });
    return result;
}

function buildFusionCombosForGroup(group) {
    const combos = [];
    for (let i = 0; i < group.length; i++) {
        for (let j = i + 1; j < group.length; j++) {
            combos.push([group[i], group[j]]);
            for (let k = j + 1; k < group.length; k++) {
                combos.push([group[i], group[j], group[k]]);
            }
        }
    }
    return dedupeCardCombos(combos);
}

async function onPlayCard(cardInstanceId, options = {}) {
    if (isSpectating) return;
    if (!canSendGameAction('play_card')) return;
    const hand = (gameState.you || {}).hand || [];
    const cardDict = hand.find(c => c.instance_id === cardInstanceId);
    if (!cardDict) return;
    if (!canPlayCard(cardDict)) {
        flashStatus(getCannotPlayReason(cardDict), 2600, 'error');
        return;
    }
    if (isTouchPlayMode() && !options.confirmed && !options.dragDrop) {
        selectPlayCardForConfirm(cardInstanceId);
        return;
    }
    const cardDef = getCardDef(cardDict.def_id);
    if (cardDef && cardDef.card_type === 'thorn' && gameState && gameState.mode !== '2v2') {
        const opponent = gameState.opponent || {};
        if (opponent.untargetable) {
            flashStatus('对方无法被选中', 2200, 'error');
            return;
        }
    }
    let targetPlayerId = -1;
    if (cardHasSelfOnlyFlag(cardDict, cardDef) && (!cardDef || cardDef.card_type !== 'thorn')) {
        targetPlayerId = normalizePlayerId(gameState.your_id);
    } else if (cardNeedsPlayerTarget(cardDef, cardDict)) {
        targetPlayerId = await choosePlayerTarget(
            UI.choose_target || UI.select_target || 'Choose target',
            getCardTargetPickOptions(cardDef),
        );
        if (targetPlayerId < 0) return;
    }
    const choice = await getCardChoice(cardDict, targetPlayerId);
    if (choice === false) return;
    clearSelectedPlayCard();
    const shouldShatterAfterPlay = cardHasExileLikeExit(cardDict);
    if (shouldShatterAfterPlay) markRecentlyPlayedExileCard(cardDict);
    const optimisticCost = getOptimisticResourceCost(cardDict, gameState && gameState.you);
    const optimisticResources = buildOptimisticResourceOverride(cardDict, gameState && gameState.you, optimisticCost);
    queueLocalResourceCost(cardDict, gameState && gameState.you, { shownOptimistically: !!optimisticResources });
    if (cardDict.def_id === 'Fusion' && choice && Array.isArray(choice.target_instance_ids)) {
        animateFusionMerge(cardInstanceId, choice.target_instance_ids, { startDelay: 300 });
    } else {
        animatePlayedCard(cardInstanceId, {
            shatterAfter: shouldShatterAfterPlay,
            targetElement: getClassicPlayedCardAnimationTarget(cardDict, cardDef, targetPlayerId),
        });
    }
    pendingPlayCard = cardDict;
    renderPendingCard();
    beginPendingServerAction('play_card', { optimisticResources, timeoutMs: SERVER_ACTION_TIMEOUT_MS });
    emitModeEvent('solo_play_card', 'play_card', { card_instance_id: cardInstanceId, choice, target_player_id: targetPlayerId });
}

async function getCardChoice(cardDict, targetPlayerId = -1) {
    const defId = cardDict.def_id;
    const sourceCardDef = getCardDef(defId);
    const sourceCardName = sourceCardDef ? getBlindedCardDisplayName(cardDict, sourceCardDef) : '';
    const hand = (gameState.you || {}).hand || [];
    if (defId === 'Fission') {
        const attacks = hand.filter(c => {
            const cd = getCardDef(c.def_id);
            return cd && cd.card_type === 'thorn' && c.instance_id !== cardDict.instance_id;
        });
        if (!attacks.length) { gameAlert(UI.notice, UI.no_attack_cards); return false; }
        const options = attacks.map(a => cardChoiceOption(a));
        const sel = await simpleChoice(UI.choose_attack_for.replace('{0}', sourceCardName), options);
        if (sel < 0) return false;
        return { target_instance_id: attacks[sel].instance_id, target_instance_ids: [attacks[sel].instance_id] };
    } else if (defId === 'Fusion') {
        const attacks = hand.filter(c => {
            const cd = getCardDef(c.def_id);
            return cd && cd.card_type === 'thorn' && c.instance_id !== cardDict.instance_id;
        });
        const groups = {};
        attacks.forEach(a => {
            const g = groups[a.def_id] || (groups[a.def_id] = []);
            g.push(a);
        });
        const validGroups = Object.entries(groups).filter(([_, v]) => v.length >= 2);
        if (!validGroups.length) { gameAlert(UI.notice, UI.no_same_attack); return false; }
        let group = validGroups[0][1];
        if (validGroups.length > 1) {
            const groupOptions = validGroups.map(([k, v]) => cardChoiceOption(v[0], { detail: `x${v.length}` }));
            const sel = await simpleChoice(UI.choose_attack_group_for.replace('{0}', sourceCardName), groupOptions);
            if (sel < 0) return false;
            group = validGroups[sel][1];
        }
        const uniqueCombos = buildFusionCombosForGroup(group);
        const comboOptions = uniqueCombos.map(combo => cardComboChoiceOption(combo));
        const comboSel = await simpleChoice(UI.choose_attack_group_for.replace('{0}', sourceCardName), comboOptions);
        if (comboSel < 0) return false;
        return { target_instance_ids: uniqueCombos[comboSel].map(c => c.instance_id) };
    } else if (isMimicCardDict(cardDict)) {
        const others = hand.filter(c => c.instance_id !== cardDict.instance_id);
        if (!others.length) { gameAlert(UI.notice, UI.no_attack_cards); return false; }
        const options = others.map(c => mimicCardChoiceOption(c, cardDict, gameState && gameState.you));
        const sel = await simpleChoice(UI.choose_hand_for.replace('{0}', sourceCardName), options);
        if (sel < 0) return false;
        return { target_instance_id: others[sel].instance_id };
    } else if (defId === 'Chromosome') {
        const discard = (gameState.you || {}).discard || [];
        if (!discard.length) { gameAlert(UI.notice, UI.discard_empty); return false; }
        const options = discard.map(c => cardChoiceOption(c));
        const sel = await simpleChoice(UI.choose_from_discard_for.replace('{0}', sourceCardName), options);
        if (sel < 0) return false;
        return { target_def_id: discard[sel].def_id };
    } else if (defId === 'Sewage') {
        const targetData = targetPlayerId >= 0 ? getPlayerDataById(targetPlayerId) : (gameState.opponent || {});
        const oppEq = targetData.equipment || [];
        const destroyable = oppEq.filter(e => {
            const cd = getCardDef((e.card_instance || {}).def_id);
            if (!cd) return false;
            const inst = e.card_instance || {};
            const flags = new Set([...(cd.flags || []), ...(inst.instance_flags || [])]);
            (inst.disabled_flags || []).forEach(flag => flags.delete(flag));
            return !flags.has('indestructible');
        });
        if (!destroyable.length) { gameAlert(UI.notice, UI.no_enemy_equipment); return false; }
        const options = destroyable.map(e => equipmentChoiceOption(e));
        const sel = await simpleChoice(UI.choose_equip_for.replace('{0}', sourceCardName), options);
        if (sel < 0) return false;
        return { target_instance_id: destroyable[sel].card_instance.instance_id };
    } else if (defId === 'Chilli') {
        const others = hand.filter(c => c.instance_id !== cardDict.instance_id);
        if (others.length) {
            const options = others.map(c => cardChoiceOption(c));
            const sel = await simpleChoice(UI.choose_discard_for.replace('{0}', sourceCardName), options);
            if (sel < 0) return false;
            return { target_instance_id: others[sel].instance_id };
        }
        return null;
    }
    return null;
}

async function simpleChoice(title, options, config = {}) {
    if (!options.length) return -1;
    return await gamePrompt(title, options, { ...config, numbered: config.numbered !== false });
}

function multiChoice(title, options, config = {}) {
    return new Promise((resolve) => {
        const el = $('game-prompt');
        if (!el) { resolve([]); return; }
        if (!options.length) { resolve([]); return; }
        const min = Number(config.min || config.min_count || 1);
        const max = Number(config.max || config.max_count || options.length);
        const cancellable = config.cancellable !== false;
        $('game-prompt-title').textContent = title || '';
        const optsEl = $('game-prompt-options');
        let msgEl = $('game-prompt-message');
        if (!msgEl) {
            msgEl = document.createElement('div');
            msgEl.id = 'game-prompt-message';
            msgEl.className = 'game-prompt-message';
            optsEl.parentNode.insertBefore(msgEl, optsEl);
        }
        const message = config.message || config.content || '';
        msgEl.textContent = message;
        msgEl.classList.toggle('hidden', !message);
        optsEl.innerHTML = '';
        const selected = new Set();
        const confirmBtn = document.createElement('button');
        confirmBtn.className = 'btn btn-primary';
        const updateConfirm = () => {
            const count = selected.size;
            const ok = count >= min && count <= max;
            confirmBtn.classList.toggle('disabled', !ok);
            confirmBtn.textContent = `${config.confirmText || UI.ok || '确定'} (${count}/${min}-${max})`;
        };
        options.forEach((opt, i) => {
            const div = document.createElement('div');
            div.className = 'game-prompt-option';
            renderChoiceOptionContent(div, opt, i, { ...config, numbered: true });
            div.onclick = () => {
                if (selected.has(i)) {
                    selected.delete(i);
                } else {
                    if (selected.size >= max) return;
                    selected.add(i);
                }
                div.classList.toggle('selected', selected.has(i));
                updateConfirm();
            };
            optsEl.appendChild(div);
        });
        confirmBtn.onclick = () => {
            if (confirmBtn.classList.contains('disabled')) return;
            removeFloatingCardPreview();
            el.classList.remove('active');
            resolve(Array.from(selected).sort((a, b) => a - b));
        };
        // Place confirm button next to cancel button in the buttons row
        const cancelBtn = $('game-prompt-cancel');
        cancelBtn.textContent = UI.cancel;
        cancelBtn.classList.toggle('hidden', !cancellable);
        cancelBtn.style.display = cancellable ? '' : 'none';
        cancelBtn.onclick = () => { removeFloatingCardPreview(); el.classList.remove('active'); resolve([]); };
        // Insert confirm after cancel in the buttons row
        const buttonsRow = cancelBtn.parentNode;
        if (confirmBtn.parentNode) confirmBtn.parentNode.removeChild(confirmBtn);
        buttonsRow.appendChild(confirmBtn);
        const cleanup = () => {
            if (confirmBtn.parentNode) confirmBtn.parentNode.removeChild(confirmBtn);
        };
        updateConfirm();
        el.classList.add('active');
        // Cleanup on resolve
        const origResolve = resolve;
        resolve = (val) => { cleanup(); origResolve(val); };
    });
}

function showResponseUI(data) {
    if (isSpectating) return;
    removeFloatingCardPreview();
    const counterCards = data.counter_cards || [];
    const you = gameState.you || {};
    const myElixir = you.elixir || 0;
    const myMagic = you.magic || 0;
    debugLog('[RESPONSE] showResponseUI: counterCards=', counterCards.length, 'myElixir=', myElixir, 'myMagic=', myMagic);
    if (!counterCards.length) {
        debugLog('[RESPONSE] no counter cards, auto pass');
        onRespond(null);
        return;
    }
    let hasAffordable = false;
    const cardCosts = counterCards.map(cc => {
        const ccDef = getCardDef(cc.def_id);
        const costE = cc.cost_e_override != null ? cc.cost_e_override : (ccDef ? ccDef.cost_e : 0);
        const costM = cc.cost_m_override != null ? cc.cost_m_override : (ccDef ? ccDef.cost_m : 0);
        const canAfford = costE <= myElixir && costM <= myMagic;
        if (canAfford) hasAffordable = true;
        return { cc, ccDef, costE, costM, canAfford };
    });
    const groupedCardCosts = [];
    const groupedBySignature = new Map();
    cardCosts.forEach(item => {
        const signature = counterCardGroupSignature(item.cc);
        let group = groupedBySignature.get(signature);
        if (!group) {
            group = {
                ...item,
                items: [],
                count: 0,
                canAffordAny: false,
            };
            groupedBySignature.set(signature, group);
            groupedCardCosts.push(group);
        }
        group.items.push(item);
        group.count += 1;
        if (item.canAfford) {
            group.canAffordAny = true;
            if (!group.canAfford) {
                group.cc = item.cc;
                group.ccDef = item.ccDef;
                group.costE = item.costE;
                group.costM = item.costM;
                group.canAfford = item.canAfford;
            }
        }
    });
    if (!hasAffordable) {
        flashStatus(UI.counter_insufficient, 3000);
    }
    const container = $('response-panel');
    if (!container) { onRespond(null); return; }
    container.innerHTML = '';
    container.classList.remove('hidden');
    container.classList.add('visible');
    const cardDict = data.card || {};
    const cardDef = getCardDef(cardDict.def_id);
    const blindLevel = getOwnBlindLevel();
    const hideResponsePrediction = blindLevel >= 2;
    let triggerDesc = '';
    if (cardDef) {
        if (cardDef.card_type === 'thorn') triggerDesc = UI.enemy_attack;
        else if (cardDef.card_type === 'bloom') triggerDesc = UI.enemy_skill;
        if (cardDef.id === 'Sewage' || cardDef.id === 'MagicSewage') triggerDesc += UI.enemy_destroy_equip;
    }
    const responseWindowDef = cardCosts.map(item => item.ccDef).find(cd => cd && (cd.response_title || cd.response_content));
    if (responseWindowDef && responseWindowDef.response_title) {
        const title = document.createElement('div');
        title.className = 'response-label response-title';
        title.textContent = responseWindowDef.response_title;
        container.appendChild(title);
    }
    const label = document.createElement('div');
    label.className = 'response-label response-trigger-label';
    const prefix = document.createElement('span');
    prefix.className = 'response-trigger-prefix';
    prefix.textContent = triggerDesc ? `${triggerDesc}:` : '';
    if (prefix.textContent) label.appendChild(prefix);
    label.appendChild(createCardChoiceChip(cardDict, blindLevel > 0 ? { blindForSelf: true, blindLevel } : {}));
    const prediction = data.damage_prediction || {};
    const noCounterPrediction = prediction.no_counter || {};
    const baseEffectPrediction = getResponseBaseEffectPrediction(data, cardDict, noCounterPrediction);
    if (!hideResponsePrediction) appendResponseEffectPreview(label, baseEffectPrediction);
    container.appendChild(label);
    if (responseWindowDef && responseWindowDef.response_content) {
        const content = document.createElement('div');
        content.className = 'response-label response-content';
        content.textContent = responseWindowDef.response_content;
        container.appendChild(content);
    }
    const btnRow = document.createElement('div');
    btnRow.className = 'response-btn-row';
    groupedCardCosts.forEach(({ cc, ccDef, costE, costM, canAffordAny, count }) => {
        if (!ccDef) return;
        const costStr = costM === 0 ? `${costE}E` : `${costE}E/${costM}M`;
        const btn = document.createElement('button');
        btn.className = 'btn counter-card-btn ' + (canAffordAny ? 'btn-primary' : 'btn-counter-disabled');
        btn.appendChild(createCardChoiceChip(cc));
        if (count > 1) {
            const countEl = document.createElement('span');
            countEl.className = 'counter-card-count';
            countEl.textContent = `×${count}`;
            btn.appendChild(countEl);
        }
        const cost = document.createElement('span');
        cost.className = 'counter-card-cost';
        cost.textContent = blindLevel > 0 ? '[?]' : `[${costStr}]`;
        btn.appendChild(cost);
        if (!hideResponsePrediction) {
            const counterPrediction = prediction.counters && prediction.counters[String(cc.instance_id)];
            const statusReduction = getResponseCounterStatusReduction(data, cardDict, baseEffectPrediction, counterPrediction, cc);
            appendCounterEffectReductions(btn, {
                damage: Math.max(0, Number(counterPrediction && counterPrediction.reduction || 0)),
                damageText: counterPrediction && counterPrediction.reduction_display,
                poison: statusReduction.poison,
                fire: statusReduction.fire,
            });
        }
        btn.disabled = !canAffordAny;
        btn.onclick = () => onRespond(cc.instance_id);
        btnRow.appendChild(btn);
    });
    container.appendChild(btnRow);
    responseCountdown = tutorialMode ? 10 : (hasAffordable ? 5 : 2);
    const passBtn = document.createElement('button');
    passBtn.className = 'btn btn-danger';
    passBtn.id = 'pass-btn';
    passBtn.textContent = UI.no_counter_countdown.replace('{0}', responseCountdown);
    passBtn.onclick = () => onRespond(null);
    container.appendChild(passBtn);
    if (responseTimerId) clearInterval(responseTimerId);
    responseTimerId = setInterval(() => {
        responseCountdown--;
        if (responseCountdown <= 0) {
            onRespond(null);
            return;
        }
        const pb = $('pass-btn');
        if (pb) pb.textContent = UI.no_counter_countdown.replace('{0}', responseCountdown);
    }, 1000);
}

function onRespond(cardInstanceId) {
    if (!canSendGameAction('response', { includeAnimation: false })) return;
    removeFloatingCardPreview();
    if (responseTimerId) { clearInterval(responseTimerId); responseTimerId = null; }
    responsePending = false;
    if (tutorialMode) tutorialCounterSeen = true;
    if (cardInstanceId != null) {
        const hand = (gameState.you || {}).hand || [];
        const cardDict = hand.find(c => c.instance_id === cardInstanceId);
        const shouldShatterAfterPlay = cardHasExileLikeExit(cardDict);
        if (shouldShatterAfterPlay) markRecentlyPlayedExileCard(cardDict);
        const optimisticCost = getOptimisticResourceCost(cardDict, gameState && gameState.you);
        const optimisticResources = buildOptimisticResourceOverride(cardDict, gameState && gameState.you, optimisticCost);
        queueLocalResourceCost(cardDict, gameState && gameState.you, { shownOptimistically: !!optimisticResources });
        animatePlayedCard(cardInstanceId, { shatterAfter: shouldShatterAfterPlay });
        beginPendingServerAction('response', { optimisticResources, timeoutMs: SERVER_ACTION_TIMEOUT_MS });
    } else {
        beginPendingServerAction('response', { timeoutMs: SERVER_ACTION_TIMEOUT_MS });
    }
    const container = $('response-panel');
    if (container) { container.innerHTML = ''; container.classList.add('hidden'); container.classList.remove('visible'); }
    emitModeEvent('solo_response', 'response', { card_instance_id: cardInstanceId });
}

function showAllyConsentUI(data) {
    if (isSpectating || !socket) return;
    removeFloatingCardPreview();
    const container = $('response-panel');
    if (!container) {
        socket.emit('ally_consent_response', { accepted: false });
        return;
    }
    if (allyConsentTimerId) clearInterval(allyConsentTimerId);
    const cardDict = data.card || {};
    const cardDef = getCardDef(cardDict.def_id);
    const allyBlindLevel = getOwnBlindLevel();
    const cardName = cardDef ? (allyBlindLevel > 0 ? '?' : getCardName(cardDef)) : (cardDict.def_id || '?');
    container.innerHTML = '';
    container.classList.remove('hidden');
    container.classList.add('visible');
    const label = document.createElement('div');
    label.className = 'response-label';
    label.textContent = UI.ally_consent_title || 'Teammate Card Use';
    container.appendChild(label);
    const msg = document.createElement('div');
    msg.className = 'response-label';
    msg.textContent = (UI.ally_consent_msg || '{0} wants to use {1} on you')
        .replace('{0}', localizeCanonicalPlayerName(data.from_name || UI.teammate))
        .replace('{1}', cardName);
    container.appendChild(msg);
    const row = document.createElement('div');
    row.className = 'response-btn-row';
    const acceptBtn = document.createElement('button');
    acceptBtn.className = 'btn btn-primary';
    const declineBtn = document.createElement('button');
    declineBtn.className = 'btn btn-danger';
    acceptBtn.textContent = UI.accept || 'Accept';
    acceptBtn.onclick = () => respondAllyConsent(true);
    declineBtn.onclick = () => respondAllyConsent(false);
    row.appendChild(acceptBtn);
    row.appendChild(declineBtn);
    container.appendChild(row);
    allyConsentCountdown = 5;
    declineBtn.textContent = `${UI.ally_decline || UI.decline || 'Decline'} (${allyConsentCountdown})`;
    allyConsentTimerId = setInterval(() => {
        allyConsentCountdown--;
        if (allyConsentCountdown <= 0) {
            respondAllyConsent(false);
            return;
        }
        declineBtn.textContent = `${UI.ally_decline || UI.decline || 'Decline'} (${allyConsentCountdown})`;
    }, 1000);
}

function respondAllyConsent(accepted) {
    removeFloatingCardPreview();
    if (allyConsentTimerId) { clearInterval(allyConsentTimerId); allyConsentTimerId = null; }
    const container = $('response-panel');
    if (container) { container.innerHTML = ''; container.classList.add('hidden'); container.classList.remove('visible'); }
    beginPendingServerAction('ally_consent', { timeoutMs: SERVER_ACTION_TIMEOUT_MS });
    socket.emit('ally_consent_response', { accepted: !!accepted });
}

function showSurrenderConsentUI(data) {
    if (isSpectating || !socket) return;
    removeFloatingCardPreview();
    const container = $('response-panel');
    if (!container) {
        socket.emit('surrender_consent_response', { accepted: false });
        return;
    }
    if (surrenderConsentTimerId) clearInterval(surrenderConsentTimerId);
    container.innerHTML = '';
    container.classList.remove('hidden');
    container.classList.add('visible');
    const label = document.createElement('div');
    label.className = 'response-label';
    label.textContent = UI.surrender_consent_title || UI.confirm_surrender || 'Surrender Request';
    container.appendChild(label);
    const msg = document.createElement('div');
    msg.className = 'response-label';
    msg.textContent = (UI.surrender_consent_msg || '{0} wants to surrender. Agree?')
        .replace('{0}', localizeCanonicalPlayerName(data && data.from_name ? data.from_name : UI.teammate));
    container.appendChild(msg);
    const row = document.createElement('div');
    row.className = 'response-btn-row';
    const acceptBtn = document.createElement('button');
    acceptBtn.className = 'btn btn-danger';
    const declineBtn = document.createElement('button');
    declineBtn.className = 'btn btn-secondary';
    acceptBtn.textContent = UI.accept || 'Accept';
    acceptBtn.onclick = () => respondSurrenderConsent(true);
    declineBtn.onclick = () => respondSurrenderConsent(false);
    row.appendChild(acceptBtn);
    row.appendChild(declineBtn);
    container.appendChild(row);
    surrenderConsentCountdown = 5;
    declineBtn.textContent = `${UI.decline || 'Decline'} (${surrenderConsentCountdown})`;
    surrenderConsentTimerId = setInterval(() => {
        surrenderConsentCountdown--;
        if (surrenderConsentCountdown <= 0) {
            respondSurrenderConsent(false);
            return;
        }
        declineBtn.textContent = `${UI.decline || 'Decline'} (${surrenderConsentCountdown})`;
    }, 1000);
}

function respondSurrenderConsent(accepted) {
    removeFloatingCardPreview();
    if (surrenderConsentTimerId) { clearInterval(surrenderConsentTimerId); surrenderConsentTimerId = null; }
    const container = $('response-panel');
    if (container) { container.innerHTML = ''; container.classList.add('hidden'); container.classList.remove('visible'); }
    if (socket) socket.emit('surrender_consent_response', { accepted: !!accepted });
}

async function showReorderDeckUI(deckCards, titleText) {
    const modal = $('modal');
    const content = $('modal-content');
    if (!modal || !content) return null;
    removeFloatingCardPreview();
    const order = deckCards.map(c => c.instance_id);
    content.className = 'modal-inner view-deck-modal';
    content.innerHTML = '';
    const title = document.createElement('h3');
    title.textContent = titleText;
    content.appendChild(title);
    const hint = document.createElement('p');
    hint.className = 'deck-total';
    hint.textContent = '拖拽三横线调整顺序（最上方先抽到）';
    content.appendChild(hint);
    const list = document.createElement('div');
    list.className = 'deck-list reorder-deck-list';

    // Build rows
    const rows = [];
    deckCards.forEach((c, idx) => {
        const row = document.createElement('div');
        row.className = 'reorder-deck-entry';
        row.dataset.idx = idx;
        // Drag handle (hamburger icon)
        const handle = document.createElement('span');
        handle.className = 'reorder-handle';
        handle.innerHTML = '&#9776;';
        handle.setAttribute('aria-label', '拖拽排序');
        row.appendChild(handle);
        row.appendChild(createCardChoiceChip(c));
        const numEl = document.createElement('span');
        numEl.className = 'choice-option-detail deck-entry-count reorder-deck-num';
        numEl.textContent = `#${idx + 1}`;
        row.appendChild(numEl);
        list.appendChild(row);
        rows.push(row);
    });

    // Pointer-based smooth drag reorder
    let dragRow = null;
    let dragOffsetY = 0;
    let placeholder = null;
    let dragClone = null;

    function moveDrag(e) {
        if (!dragRow || !dragClone) return;
        dragClone.style.top = (e.clientY - dragOffsetY) + 'px';

        // Find insertion point among current visible rows (skip placeholder & dragging row)
        let insertBefore = null;
        const children = list.children;
        for (let i = 0; i < children.length; i++) {
            const child = children[i];
            if (child === placeholder || child === dragRow) continue;
            const rect = child.getBoundingClientRect();
            if (rect.top + rect.height / 2 > e.clientY) {
                insertBefore = child;
                break;
            }
        }

        if (insertBefore) {
            list.insertBefore(placeholder, insertBefore);
        } else {
            list.appendChild(placeholder);
        }
    }

    function endDrag() {
        if (!dragRow) return;

        // Insert drag row at placeholder position
        list.insertBefore(dragRow, placeholder);
        placeholder.remove();
        dragClone.remove();

        dragRow.classList.remove('reorder-dragging');
        dragRow = null;
        dragClone = null;
        placeholder = null;

        // Rebuild order from current DOM order
        const currentRows = list.querySelectorAll('.reorder-deck-entry');
        order.length = 0;
        currentRows.forEach((el, i) => {
            el.dataset.idx = i;
            const num = el.querySelector('.reorder-deck-num');
            if (num) num.textContent = `#${i + 1}`;
            const origIdx = rows.indexOf(el);
            if (origIdx >= 0) order.push(deckCards[origIdx].instance_id);
        });

        document.removeEventListener('pointermove', moveDrag);
        document.removeEventListener('pointerup', endDrag);
    }

    rows.forEach(row => {
        const handle = row.querySelector('.reorder-handle');
        handle.addEventListener('pointerdown', e => {
            e.preventDefault();
            const rect = row.getBoundingClientRect();
            dragRow = row;
            dragOffsetY = e.clientY - rect.top;

            // Create placeholder at current position
            placeholder = document.createElement('div');
            placeholder.className = 'reorder-placeholder';
            placeholder.style.height = rect.height + 'px';
            list.insertBefore(placeholder, row);

            // Hide original row (remove from flow)
            row.classList.add('reorder-dragging');

            // Create floating clone
            dragClone = row.cloneNode(true);
            dragClone.className = 'reorder-deck-entry reorder-clone';
            dragClone.style.position = 'fixed';
            dragClone.style.left = rect.left + 'px';
            dragClone.style.top = rect.top + 'px';
            dragClone.style.width = rect.width + 'px';
            dragClone.style.zIndex = '10000';
            dragClone.style.pointerEvents = 'none';
            document.body.appendChild(dragClone);

            document.addEventListener('pointermove', moveDrag);
            document.addEventListener('pointerup', endDrag);
        });
    });

    content.appendChild(list);
    const buttons = document.createElement('div');
    buttons.className = 'modal-buttons';
    const confirmBtn = document.createElement('button');
    confirmBtn.className = 'btn btn-primary';
    confirmBtn.textContent = UI.ok || '确定';
    confirmBtn.onclick = () => {
        modal.classList.add('hidden');
        modal.classList.remove('active');
    };
    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn btn-danger';
    cancelBtn.textContent = UI.cancel || '取消';
    cancelBtn.onclick = () => {
        order.length = 0;
        modal.classList.add('hidden');
        modal.classList.remove('active');
    };
    buttons.appendChild(cancelBtn);
    buttons.appendChild(confirmBtn);
    content.appendChild(buttons);
    modal.classList.remove('hidden');
    modal.classList.add('active');
    return new Promise(resolve => {
        const checkClosed = () => {
            if (modal.classList.contains('hidden') || !modal.classList.contains('active')) {
                if (order.length > 0) {
                    resolve({ new_order: order });
                } else {
                    resolve(null);
                }
            } else {
                requestAnimationFrame(checkClosed);
            }
        };
        confirmBtn.addEventListener('click', () => setTimeout(checkClosed, 50));
        cancelBtn.addEventListener('click', () => setTimeout(checkClosed, 50));
    });
}

async function showChoiceUI(data) {
    if (isSpectating) return;
    removeFloatingCardPreview();
    const choiceType = data.choice_type || '';
    const cardDict = data.card || {};
    const cardDef = getCardDef(cardDict.def_id);
    const cardName = cardDef ? (getOwnBlindLevel() > 0 ? '?' : getCardName(cardDef)) : '?';
    const choiceParams = data.choice_params || {};
    const choicePromptConfig = {
        cancellable: choiceParams.cancellable !== false && !(cardDef && (cardDef.flags || []).includes('uncancellable')),
        message: choiceParams.content || choiceParams.message || ''
    };
    const choiceTitle = fallback => choiceParams.title || fallback;
    const choiceTargetId = data.target_player_id != null ? normalizePlayerId(data.target_player_id) : null;
    const choiceTargetData = () => (choiceTargetId != null ? (getPlayerDataById(choiceTargetId) || {}) : (gameState.you || {}));
    let choiceResult = null;
    if (choiceType === 'choose_attack_from_hand') {
        const attacks = ((gameState.you || {}).hand || []).filter(c => {
            const cd = getCardDef(c.def_id);
            return cd && cd.card_type === 'thorn';
        });
        if (!attacks.length) { gameAlert(UI.notice, UI.no_attack_cards); }
        else {
            const options = attacks.map(a => cardChoiceOption(a));
            const sel = await simpleChoice(choiceTitle(UI.choose_attack_for.replace('{0}', cardName)), options, choicePromptConfig);
            if (sel >= 0 && sel < attacks.length) choiceResult = { target_instance_id: attacks[sel].instance_id };
        }
    } else if (choiceType === 'choose_enemy_equipment') {
        const oppEq = (gameState.opponent || {}).equipment || [];
        if (!oppEq.length) { gameAlert(UI.notice, UI.no_enemy_equipment); }
        else {
            const options = oppEq.map(e => equipmentChoiceOption(e));
            const sel = await simpleChoice(choiceTitle(UI.choose_equip_for.replace('{0}', cardName)), options, choicePromptConfig);
            if (sel >= 0 && sel < oppEq.length) choiceResult = { target_instance_id: oppEq[sel].card_instance.instance_id };
        }
    } else if (choiceType === 'choose_card_to_discard') {
        const otherCards = (gameState.you || {}).hand || [];
        if (otherCards.length) {
            const options = otherCards.map(c => cardChoiceOption(c));
            const sel = await simpleChoice(choiceTitle(UI.choose_discard_for.replace('{0}', cardName)), options, choicePromptConfig);
            if (sel >= 0 && sel < otherCards.length) choiceResult = { target_instance_id: otherCards[sel].instance_id };
        }
    } else if (choiceType === 'choose_card_from_deck') {
        const deck = (gameState.you || {}).deck || [];
        if (!deck.length) {
            gameAlert(UI.notice, UI.deck_empty);
            choiceResult = { cancelled: true };
        }
        else {
            const options = deck.map(c => cardChoiceOption(c));
            const sel = await simpleChoice(choiceTitle(UI.choose_from_deck_for.replace('{0}', cardName)), options, choicePromptConfig);
            if (sel >= 0 && sel < deck.length) choiceResult = { target_def_id: deck[sel].def_id };
        }
    } else if (choiceType === 'choose_card_from_discard') {
        const discard = (gameState.you || {}).discard || [];
        if (!discard.length) {
            gameAlert(UI.notice, UI.discard_empty);
            choiceResult = { cancelled: true };
        }
        else {
            const options = discard.map(c => cardChoiceOption(c));
            const sel = await simpleChoice(choiceTitle(UI.choose_from_discard_for.replace('{0}', cardName)), options, choicePromptConfig);
            if (sel >= 0 && sel < discard.length) choiceResult = { target_def_id: discard[sel].def_id };
        }
    } else if (choiceType === 'choose_same_attacks_from_hand') {
        const attacks = ((gameState.you || {}).hand || []).filter(c => {
            const cd = getCardDef(c.def_id);
            return cd && cd.card_type === 'thorn';
        });
        const groups = {};
        attacks.forEach(a => { const g = groups[a.def_id] || (groups[a.def_id] = []); g.push(a); });
        const validGroups = Object.entries(groups).filter(([_, v]) => v.length >= 2);
        if (!validGroups.length) { gameAlert(UI.notice, UI.no_same_attack); }
        else {
            let group = validGroups[0][1];
            let groupAccepted = true;
            if (validGroups.length > 1) {
                const groupOptions = validGroups.map(([k, v]) => cardChoiceOption(v[0], { detail: `x${v.length}` }));
                const sel = await simpleChoice(UI.choose_attack_group_for.replace('{0}', cardName), groupOptions, choicePromptConfig);
                groupAccepted = sel >= 0;
                if (groupAccepted) group = validGroups[sel][1];
            }
            if (groupAccepted) {
                const uniqueCombos = buildFusionCombosForGroup(group);
                const comboOptions = uniqueCombos.map(combo => cardComboChoiceOption(combo));
                const comboSel = await simpleChoice(choiceTitle(UI.choose_attack_group_for.replace('{0}', cardName)), comboOptions, choicePromptConfig);
                if (comboSel >= 0) choiceResult = { target_instance_ids: uniqueCombos[comboSel].map(c => c.instance_id) };
            }
        }
    } else if (choiceType === 'choose_cards_from_hand') {
        const allCards = choiceTargetData().hand || [];
        const wantedType = choiceParams.card_type || 'any';
        const minCount = Number(choiceParams.min_count || 1);
        const maxCount = Math.max(minCount, Number(choiceParams.max_count || minCount));
        const cards = allCards.filter(c => {
            const cd = getCardDef(c.def_id);
            return wantedType === 'any' || (cd && cd.card_type === wantedType);
        });
        if (!cards.length) { gameAlert(UI.notice, UI.no_valid_target || '没有可选择的卡牌'); }
        else if (choiceParams.same_name) {
            const groups = {};
            cards.forEach(c => { const g = groups[c.def_id] || (groups[c.def_id] = []); g.push(c); });
            const combos = [];
            const collect = (group, start, picked) => {
                if (picked.length >= minCount) combos.push([...picked]);
                if (picked.length >= maxCount) return;
                for (let i = start; i < group.length; i++) {
                    picked.push(group[i]);
                    collect(group, i + 1, picked);
                    picked.pop();
                }
            };
            Object.values(groups).forEach(group => {
                if (group.length >= minCount) collect(group, 0, []);
            });
            const uniqueCombos = dedupeCardCombos(combos);
            if (!uniqueCombos.length) { gameAlert(UI.notice, UI.no_valid_target || '没有可选择的组合'); }
            else {
                const options = uniqueCombos.map(combo => cardComboChoiceOption(combo));
                const sel = await simpleChoice(choiceTitle(UI.choose_hand_for.replace('{0}', cardName)), options, choicePromptConfig);
                if (sel >= 0 && sel < uniqueCombos.length) choiceResult = { target_instance_ids: uniqueCombos[sel].map(c => c.instance_id) };
            }
        } else {
            const options = cards.map(c => cardChoiceOption(c));
            const selected = await multiChoice(choiceTitle(UI.choose_hand_for.replace('{0}', cardName)), options, {
                ...choicePromptConfig,
                min: minCount,
                max: maxCount,
            });
            if (selected.length >= minCount) choiceResult = { target_instance_ids: selected.map(i => cards[i].instance_id) };
        }
    } else if (choiceType === 'choose_card_from_hand') {
        const isMimicChoice = isMimicCardDict(cardDict);
        const filter = choiceParams.filter || {};
        let otherCards = (choiceTargetData().hand || []).filter(c => (
            !isMimicChoice || c.instance_id !== cardDict.instance_id
        ));
        if (filter.card_type) {
            const allowedTypes = Array.isArray(filter.card_type) ? filter.card_type : [filter.card_type];
            otherCards = otherCards.filter(c => {
                const def = getCardDef(c.def_id);
                return def && allowedTypes.includes(def.card_type);
            });
        }
        if (filter.exclude_current && cardDict.instance_id) {
            otherCards = otherCards.filter(c => c.instance_id !== cardDict.instance_id);
        }
        if (otherCards.length) {
            const options = otherCards.map(c => (
                isMimicChoice
                    ? mimicCardChoiceOption(c, cardDict, gameState && gameState.you)
                    : cardChoiceOption(c)
            ));
            const sel = await simpleChoice(choiceTitle(UI.choose_hand_for.replace('{0}', cardName)), options, choicePromptConfig);
            if (sel >= 0 && sel < otherCards.length) choiceResult = { target_instance_id: otherCards[sel].instance_id };
        } else {
            const noMatchMsg = filter.card_type ? UI.no_matching_cards || '没有符合条件的牌' : (UI.no_cards_in_hand || '手牌为空');
            gameAlert(UI.notice, noMatchMsg);
        }
    } else if (choiceType === 'choose_from_deck') {
        const deck = choiceTargetData().deck || [];
        if (!deck.length) {
            gameAlert(UI.notice, UI.deck_empty);
            choiceResult = { cancelled: true };
        }
        else {
            const options = deck.map(c => cardChoiceOption(c));
            const sel = await simpleChoice(choiceTitle(UI.choose_from_deck_for.replace('{0}', cardName)), options, choicePromptConfig);
            if (sel >= 0 && sel < deck.length) choiceResult = { target_instance_id: deck[sel].instance_id };
        }
    } else if (choiceType === 'choose_from_discard') {
        const discard = choiceTargetData().discard || [];
        if (!discard.length) {
            gameAlert(UI.notice, UI.discard_empty);
            choiceResult = { cancelled: true };
        }
        else {
            const options = discard.map(c => cardChoiceOption(c));
            const sel = await simpleChoice(choiceTitle(UI.choose_from_discard_for.replace('{0}', cardName)), options, choicePromptConfig);
            if (sel >= 0 && sel < discard.length) choiceResult = { target_instance_id: discard[sel].instance_id, target_def_id: discard[sel].def_id };
        }
    } else if (choiceType === 'choose_from_exile') {
        const exile = choiceTargetData().exile || [];
        if (!exile.length) {
            gameAlert(UI.notice, UI.no_valid_target || '无可选卡牌');
            choiceResult = { cancelled: true };
        }
        else {
            const options = exile.map(c => cardChoiceOption(c));
            const sel = await simpleChoice(choiceTitle('从放逐区选择'), options, choicePromptConfig);
            if (sel >= 0 && sel < exile.length) choiceResult = { target_instance_id: exile[sel].instance_id, target_def_id: exile[sel].def_id };
        }
    } else if (choiceType === 'choose_equipment') {
        const equipment = choiceTargetData().equipment || [];
        if (!equipment.length) { gameAlert(UI.notice, UI.no_valid_target || '无可选装备'); }
        else {
            const options = equipment.map(e => equipmentChoiceOption(e));
            const sel = await simpleChoice(choiceTitle('选择装备'), options, choicePromptConfig);
            if (sel >= 0 && sel < equipment.length) choiceResult = { target_instance_id: equipment[sel].card_instance.instance_id };
        }
    } else if (choiceType === 'choose_from_enemy_hand') {
        const targetId = data.target_player_id != null ? data.target_player_id : -1;
        const targetData = targetId >= 0 ? getPlayerDataById(targetId) : (gameState.opponent || {});
        const fallbackOpponent = gameState.opponent || {};
        const oppHand = targetData.hand || targetData.revealed_hand || fallbackOpponent.hand || fallbackOpponent.revealed_hand || [];
        if (!oppHand.length) { gameAlert(UI.notice, UI.no_enemy_hand); }
        else {
            const options = oppHand.map(c => cardChoiceOption(c));
            const sel = await simpleChoice(choiceTitle(UI.choose_from_enemy_hand_for.replace('{0}', cardName)), options, choicePromptConfig);
            if (sel >= 0 && sel < oppHand.length) choiceResult = { target_instance_id: oppHand[sel].instance_id };
        }
    } else if (choiceType === 'choose_target') {
        const candidates = choiceParams.candidates || choiceParams.target || choiceParams.targets || 'enemy';
        const candidateList = normalizeTargetCandidates(candidates);
        const includeSelf = choiceParams.include_self === true
            || candidateList.some(c => ['self', 'friendly', 'both', 'all', 'random_friendly', 'random_player', 'random_side'].includes(c));
        const targetId = await choosePlayerTarget(choiceTitle(UI.choose_target || UI.select_target || 'Choose target'), {
            includeSelf,
            aliveOnly: choiceParams.alive_only !== false,
            candidates,
        });
        if (targetId >= 0) choiceResult = { target_player: targetId, target_player_id: targetId };
    } else if (choiceType === 'foresight_replace') {
        const handCards = data.hand_cards || data.deck_cards || [];
        const maxReplace = Number(choiceParams.max_count || choiceParams.count || 1);
        if (!handCards.length) { gameAlert(UI.notice, UI.no_valid_target || '没有可选择的卡牌'); }
        else {
            const options = handCards.map(c => cardChoiceOption(c));
            const selected = await multiChoice(
                choiceTitle(UI.foresight_replace_title || 'Foresight'),
                options,
                {
                    ...choicePromptConfig,
                    min: 0,
                    max: maxReplace,
                    message: (UI.foresight_replace_desc || 'Select up to {0} cards to draw').replace('{0}', maxReplace),
                    confirmText: UI.foresight_replace_confirm || 'Draw',
                }
            );
            if (selected.length > 0) choiceResult = { selected_instance_ids: selected.map(i => handCards[i].instance_id) };
            else choiceResult = { selected_instance_ids: [] };
        }
    } else if (choiceType === 'confirm') {
        const sel = await simpleChoice(choiceTitle(UI.notice || 'Confirm'), [
            choiceParams.ok_text || UI.ok || 'OK',
            choiceParams.cancel_text || UI.cancel || 'Cancel',
        ], choicePromptConfig);
        if (sel >= 0) choiceResult = { confirmed: sel === 0, accepted: sel === 0 };
    } else if (choiceType === 'reorder_deck') {
        const deckCards = data.deck_cards || [];
        if (!deckCards.length) { gameAlert(UI.notice, UI.deck_empty); }
        else {
            choiceResult = await showReorderDeckUI(deckCards, data.message || '调整牌堆顺序');
        }
    }
    if (!choiceResult && choiceParams.continue_on_cancel) {
        choiceResult = { cancelled: true };
    }
    if (!choiceResult) {
        choicePending = false;
        clearPendingServerAction();
        return;
    }
    choicePending = false;
    if (!canSendGameAction('resolve_choice', { includeAnimation: false })) {
        choicePending = true;
        return;
    }
    beginPendingServerAction('resolve_choice', { timeoutMs: SERVER_ACTION_TIMEOUT_MS });
    emitModeEvent('solo_resolve_choice', 'resolve_choice', { choice: choiceResult });
}

let rematchRequestedByOpponent = false;
let rematchState = null;

function resetRematchUiState() {
    rematchRequestedByOpponent = false;
    rematchState = null;
}

function updateRematchState(data = {}) {
    const votes = Number(data.votes ?? data.rematch_votes ?? 0);
    const total = Number(data.total ?? data.rematch_total ?? 0);
    rematchState = {
        votes: Number.isFinite(votes) ? Math.max(0, votes) : 0,
        total: Number.isFinite(total) ? Math.max(0, total) : 0,
        hasVoted: !!(data.has_voted ?? data.rematch_has_voted),
        mode: data.mode || (gameState && gameState.mode) || '',
        blocked: !!(data.rematch_blocked || data.blocked),
        blockedReason: data.rematch_blocked_reason || data.blocked_reason || '',
        returnedPlayerName: data.rematch_returned_player_name || data.returned_player_name || data.player_name || '',
    };
}

function syncRematchStateFromGameState(gs) {
    if (!gs || gs.rematch_total === undefined) return;
    updateRematchState({
        votes: gs.rematch_votes,
        total: gs.rematch_total,
        has_voted: gs.rematch_has_voted,
        mode: gs.mode,
        rematch_blocked: gs.rematch_blocked,
        rematch_blocked_reason: gs.rematch_blocked_reason,
        rematch_returned_player_name: gs.rematch_returned_player_name,
    });
}

function isTeamRematchGame(gs) {
    const mode = (gs && gs.mode) || (rematchState && rematchState.mode) || '';
    return mode === '2v2' || !!(gs && Array.isArray(gs.teams));
}

function getRematchProgress(gs) {
    const teamMode = isTeamRematchGame(gs);
    const fallbackTotal = teamMode ? 4 : 2;
    const votes = Number((rematchState && rematchState.votes) ?? (gs && gs.rematch_votes) ?? 0);
    const total = Number((rematchState && rematchState.total) ?? (gs && gs.rematch_total) ?? fallbackTotal);
    const hasVoted = !!((rematchState && rematchState.hasVoted) ?? (gs && gs.rematch_has_voted));
    const blocked = !!((rematchState && rematchState.blocked) ?? (gs && gs.rematch_blocked));
    return {
        votes: Number.isFinite(votes) ? Math.max(0, votes) : 0,
        total: Number.isFinite(total) && total > 0 ? total : fallbackTotal,
        hasVoted,
        blocked,
    };
}

function formatRematchProgress(votes, total) {
    return tf('rematch_progress', votes, total);
}

function updateGameOverRematchButton(gs) {
    const rematchBtn = $('btn-rematch');
    if (!rematchBtn) return;
    const progress = getRematchProgress(gs);
    const teamMode = isTeamRematchGame(gs);
    if (progress.blocked) {
        rematchBtn.textContent = UI.rematch_unavailable_returned || 'A player returned to lobby';
        rematchBtn.disabled = true;
        rematchBtn.onclick = null;
    } else if (teamMode) {
        rematchBtn.textContent = formatRematchProgress(progress.votes, progress.total);
        rematchBtn.disabled = progress.hasVoted;
        rematchBtn.onclick = () => {
            if (!socket || rematchBtn.disabled) return;
            socket.emit('rematch');
            const nextVotes = Math.min(progress.total, Math.max(progress.votes + (progress.hasVoted ? 0 : 1), progress.votes));
            rematchState = { ...progress, votes: nextVotes, hasVoted: true, mode: '2v2' };
            rematchBtn.textContent = formatRematchProgress(nextVotes, progress.total);
            rematchBtn.disabled = true;
        };
    } else if (progress.hasVoted) {
        rematchBtn.textContent = UI.rematch_sent;
        rematchBtn.disabled = true;
        rematchBtn.onclick = null;
    } else if (rematchRequestedByOpponent) {
        rematchBtn.textContent = UI.agree_rematch;
        rematchBtn.disabled = false;
        rematchBtn.onclick = () => {
            if (!socket) { debugLog('[REMATCH] socket missing'); return; }
            debugLog('[REMATCH] emit rematch accept');
            socket.emit('rematch');
            rematchBtn.textContent = UI.rematch_sent;
            rematchBtn.disabled = true;
        };
    } else {
        rematchBtn.textContent = UI.rematch;
        rematchBtn.disabled = false;
        rematchBtn.onclick = () => {
            if (!socket) { debugLog('[REMATCH] socket missing'); return; }
            debugLog('[REMATCH] emit rematch request');
            socket.emit('rematch');
            rematchBtn.textContent = UI.rematch_sent;
            rematchBtn.disabled = true;
        };
    }
}

function renderGameOver(data) {
    const gs = data || gameState;
    resetMatchRuntimeState({ clearGameState: false });
    showView('view-gameover');
    syncRematchStateFromGameState(gs);
    const isTutorialGameOver = !!gs.tutorial;
    const isSpectatorGameOver = !!(gs.spectating || isSpectating || gs.your_id === -1 || playerId === -1);
    const winner = gs.winner;
    const isDraw = winner === -1 || winner === null || winner === undefined;
    const is2v2GameOver = gs.mode === '2v2' || Array.isArray(gs.teams);
    const winningTeam = gs.winning_team !== undefined ? gs.winning_team : winner;
    const myTeam = gs.team_id;
    const isWin = is2v2GameOver
        ? (Number(winningTeam) === Number(myTeam))
        : (winner === playerId);
    const title = $('gameover-title');
    if (title) {
        title.textContent = isSpectatorGameOver ? UI.game_over : (isDraw ? UI.draw : (isWin ? UI.victory : UI.defeat));
        title.style.whiteSpace = '';
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        if (isSpectatorGameOver || isDraw) {
            title.style.color = isDark ? '#E5E7EB' : '#374151';
            title.style.background = isDark ? 'rgba(229, 231, 235, 0.14)' : 'rgba(55, 65, 81, 0.12)';
        } else {
            title.style.color = isWin ? COLORS.health : COLORS.damage;
            title.style.background = isWin
                ? (isDark ? 'rgba(46, 204, 113, 0.15)' : COLORS.health_bg)
                : (isDark ? 'rgba(192, 57, 43, 0.15)' : COLORS.damage_bg);
        }
    }
    const message = $('gameover-message');
    if (message) {
        const tutorialMessage = isTutorialGameOver && !isDraw
            ? (isWin ? UI.tutorial_victory_message : UI.tutorial_defeat_message)
            : '';
        message.textContent = tutorialMessage;
        message.classList.toggle('hidden', !tutorialMessage);
    }
    const logContainer = $('gameover-log');
    if (logContainer) {
        logContainer.innerHTML = '';
        (gs.log || []).forEach(line => {
            const el = document.createElement('div');
            el.className = 'log-entry';
            el.textContent = translateLogLine(line);
            logContainer.appendChild(el);
        });
    }
    const rematchBtn = $('btn-rematch');
    if (rematchBtn) {
        rematchBtn.classList.remove('hidden');
        rematchBtn.style.display = '';
        if (isSpectatorGameOver) {
            rematchBtn.classList.add('hidden');
            rematchBtn.style.display = 'none';
            rematchBtn.disabled = true;
            rematchBtn.onclick = null;
        } else if (isTutorialGameOver && isWin) {
            rematchBtn.classList.add('hidden');
            rematchBtn.style.display = 'none';
            rematchBtn.disabled = true;
            rematchBtn.onclick = null;
        } else if (isTutorialGameOver) {
            rematchBtn.textContent = UI.tutorial_retry || UI.rematch;
            rematchBtn.disabled = false;
            rematchBtn.onclick = () => startTutorial('home');
        } else {
            updateGameOverRematchButton(gs);
        }
    }
    const reportMatchBtn = $('btn-report-match');
    if (reportMatchBtn) {
        const matchObjectId = getReportMatchObjectId(gs);
        const showReportMatch = !!matchObjectId && !isTutorialGameOver && !soloMode && gs.mode !== 'solo';
        reportMatchBtn.textContent = UI.report_match || UI.report || 'Report';
        reportMatchBtn.classList.toggle('hidden', !showReportMatch);
        reportMatchBtn.style.display = showReportMatch ? '' : 'none';
        reportMatchBtn.onclick = showReportMatch ? (() => openReportDialog({
            objectType: 'match',
            objectId: matchObjectId,
            title: UI.report_match,
        })) : null;
    }
    const returnLobbyBtn = $('btn-return-lobby');
    if (returnLobbyBtn) {
        if (isTutorialGameOver) {
            returnLobbyBtn.textContent = UI.back_to_home || UI.return_lobby;
            returnLobbyBtn.onclick = () => {
                if (socket || isLocalSoloRuntimeActive()) {
                    suppressSoloPausedHandler = true;
                    emitSoloEvent('solo_pause', {});
                }
                soloMode = false;
                stopTutorialUiForGameOver();
                showView('view-login');
                phase = 'login';
                updateStatus(UI.default_status);
            };
        } else {
            returnLobbyBtn.textContent = UI.return_lobby;
            returnLobbyBtn.onclick = () => {
                if (!socket) return;
                socket.emit('return_lobby');
                clearNetworkMatchStateForLobby();
                showView('view-lobby');
                phase = 'lobby';
            };
        }
    }
}

function showOpponentDCWaiting(data) {
    const timeout = data.reconnect_timeout || 120;
    const oppName = data.opponent_nickname || '?';
    if (data && data.wait_forever) {
        showModal(`
            <div class="disconnect-modal">
                <h3>${UI.opponent_disconnected}</h3>
                <p id="dc-countdown" class="disconnect-countdown">${oppName}</p>
            </div>
        `);
        return;
    }
    let remaining = timeout;
    showModal(`
        <div class="disconnect-modal">
            <h3>${UI.opponent_disconnected}</h3>
            <p id="dc-countdown" class="disconnect-countdown">${oppName} ${remaining}s</p>
        </div>
    `);
    const timer = setInterval(() => {
        remaining--;
        const el = $('dc-countdown');
        if (el) el.textContent = `${oppName} ${remaining}s`;
        if (remaining <= 0) { clearInterval(timer); hideModal(); }
    }, 1000);
}

function onEndTurn() {
    if (!canSendGameAction('end_turn', { includeAnimation: false })) return;
    if (!isMyTurn()) {
        flashStatus(UI.not_your_turn, 2000, 'error');
        return;
    }
    if (socket || isLocalSoloRuntimeActive()) {
        beginPendingServerAction('end_turn', { timeoutMs: SERVER_ACTION_TIMEOUT_MS });
        emitModeEvent('solo_end_turn', 'end_turn', {});
    } else {
        updateStatus(UI.server_not_connected);
    }
}

async function onSoloNextDraw() {
    if (!soloMode || (!socket && !isLocalSoloRuntimeActive())) return;
    const deck = (gameState.you || {}).deck || [];
    if (!deck.length) {
        gameAlert(UI.notice, UI.deck_empty);
        return;
    }
    const maxCount = Math.min(5, deck.length);
    const countOptions = Array.from({ length: maxCount }, (_, i) => String(i + 1));
    const countSel = await simpleChoice(UI.next_draw_count, countOptions);
    if (countSel < 0) return;
    const pickCount = countSel + 1;
    const pool = deck.map(c => ({ ...c }));
    const chosen = [];
    for (let i = 0; i < pickCount; i++) {
        if (!pool.length) break;
        const options = pool.map(p => cardChoiceOption(p));
        const sel = await simpleChoice(tf('next_draw_pick', i + 1, pickCount), options);
        if (sel < 0) return;
        chosen.push(pool[sel].def_id);
        pool.splice(sel, 1);
    }
    if (!chosen.length) return;
    emitSoloEvent('solo_set_next_draw', { def_ids: chosen });
}

function onSurrender() {
    const message = gameState && gameState.mode === '2v2' ? UI.confirm_team_surrender : UI.confirm_surrender;
    gameAlert(message, '', [
        { text: UI.ok, cls: 'btn-danger', action: () => {
            if (socket) {
                emitModeEvent('solo_pause', 'surrender', {});
            }
        }},
        { text: UI.cancel, cls: 'btn-secondary', action: () => {} }
    ]);
}

function getSpectatePerspectivePlayer(gs = gameState) {
    if (!gs || !Array.isArray(gs.spectate_players) || !gs.spectate_players.length) {
        return null;
    }
    const current = normalizePlayerId(gs.spectate_perspective != null ? gs.spectate_perspective : spectatePerspective);
    if (current != null) {
        const byId = gs.spectate_players.find(p => normalizePlayerId(p && p.player_id) === current);
        if (byId) return byId;
    }
    return gs.spectate_players[0] || null;
}

function getDeckViewerPlayer() {
    if (isSpectating || (gameState && gameState.spectating)) {
        return getSpectatePerspectivePlayer(gameState) || gameState.you || {};
    }
    return (gameState && gameState.you) || {};
}

function onViewDeck() {
    if (gameState && gameState.mode === 'urf') {
        return;
    }
    if (tutorialMode) {
        tutorialDeckViewed = true;
        hideTutorialOverlay();
        setTimeout(updateTutorialOverlay, 80);
    }
    const deckPlayer = getDeckViewerPlayer();
    const hasOrderedDeck = !!deckPlayer.deck_ordered;
    const deck = deckPlayer.deck_ordered || deckPlayer.deck || [];
    const blindDeck = getOwnBlindLevel() >= 3 && !isSpectating;
    const modal = $('modal');
    const content = $('modal-content');
    if (!modal || !content) return;
    removeFloatingCardPreview();
    content.className = 'modal-inner view-deck-modal';
    content.innerHTML = '';
    const title = document.createElement('h3');
    const deckOwnerName = (isSpectating || (gameState && gameState.spectating)) && deckPlayer && deckPlayer.name
        ? localizeCanonicalPlayerName(deckPlayer.name)
        : '';
    title.textContent = deckOwnerName ? `${UI.view_deck_title} - ${deckOwnerName}` : UI.view_deck_title;
    content.appendChild(title);
    const total = document.createElement('p');
    total.className = 'deck-total';
    total.textContent = UI.deck_total.replace('{0}', blindDeck ? '?' : deck.length);
    content.appendChild(total);
    const list = document.createElement('div');
    list.className = 'deck-list';
    if (blindDeck) {
        const row = document.createElement('div');
        row.className = 'deck-entry deck-entry-blinded';
        const unknown = document.createElement('span');
        unknown.className = 'choice-card-token choice-card-blinded';
        const unknownName = document.createElement('span');
        unknownName.className = 'choice-card-name';
        unknownName.textContent = '?';
        unknown.appendChild(unknownName);
        row.appendChild(unknown);
        list.appendChild(row);
    } else if (hasOrderedDeck) {
        // Goggles: show deck in order (top to bottom)
        deck.forEach((c, idx) => {
            const row = document.createElement('div');
            row.className = 'deck-entry';
            const numEl = document.createElement('span');
            numEl.className = 'choice-option-detail deck-entry-count';
            numEl.textContent = `#${idx + 1}`;
            row.appendChild(createCardChoiceChip(c));
            row.appendChild(numEl);
            list.appendChild(row);
        });
    } else {
        const groups = new Map();
        deck.forEach(c => {
            const key = cardChoiceIdentity(c);
            const group = groups.get(key) || { card: c, count: 0 };
            group.count += 1;
            groups.set(key, group);
        });
        Array.from(groups.values()).sort((a, b) => {
            const ad = getCardDef(a.card.def_id);
            const bd = getCardDef(b.card.def_id);
            if (ad && bd) return compareGalleryCards(a.card.def_id, b.card.def_id);
            return (ad ? getCardName(ad) : a.card.def_id || '').localeCompare(bd ? getCardName(bd) : b.card.def_id || '');
        }).forEach(({ card, count }) => {
            const row = document.createElement('div');
            row.className = 'deck-entry';
            row.appendChild(createCardChoiceChip(card));
            const countEl = document.createElement('span');
            countEl.className = 'choice-option-detail deck-entry-count';
            countEl.textContent = `x${count}`;
            row.appendChild(countEl);
            list.appendChild(row);
        });
    }
    content.appendChild(list);
    const buttons = document.createElement('div');
    buttons.className = 'modal-buttons';
    const closeBtn = document.createElement('button');
    closeBtn.className = 'btn btn-danger';
    closeBtn.textContent = UI.close;
    closeBtn.onclick = hideModal;
    buttons.appendChild(closeBtn);
    content.appendChild(buttons);
    modal.classList.remove('hidden');
    modal.classList.add('active');
}

async function onUrfReplaceCard() {
    if (!gameState || gameState.mode !== 'urf' || !isMyTurn()) return;
    if (isActionBusy({ includeAnimation: false })) return;
    const hand = (gameState.you || {}).hand || [];
    if (!hand.length) return;
    const options = hand.map(c => cardChoiceOption(c));
    const sel = await simpleChoice(UI.urf_replace || '替换手牌', options);
    if (sel < 0) return;
    beginPendingServerAction('urf_replace', { timeoutMs: SERVER_ACTION_TIMEOUT_MS });
    socket.emit('urf_replace_card', { card_instance_id: hand[sel].instance_id });
}

async function onUrfSellEquipment() {
    if (!gameState || gameState.mode !== 'urf' || !isMyTurn()) return;
    if (isActionBusy({ includeAnimation: false })) return;
    const equipment = ((gameState.you || {}).equipment || []).filter(isUrfEquipmentSellable);
    if (!equipment.length) return;
    const options = equipment.map(eq => equipmentChoiceOption(eq));
    const sel = await simpleChoice(UI.urf_sell || '售卖装备', options);
    if (sel < 0) return;
    const inst = (equipment[sel].card_instance || {});
    beginPendingServerAction('urf_sell', { timeoutMs: SERVER_ACTION_TIMEOUT_MS });
    socket.emit('urf_sell_equipment', { equipment_instance_id: inst.instance_id });
}

function onLobbyChatSend() {
    const input = $('lobby-chat-input');
    if (!input) return;
    const text = input.value.trim();
    if (text && socket) {
        socket.emit('chat', { text });
        input.value = '';
    }
}

function onGameChatSend() {
    const input = $('game-chat-input');
    if (!input) return;
    const text = input.value.trim();
    if (text && socket) {
        const payload = applyChatChannelPayload({ text }, 'game-chat-channel');
        socket.emit('chat', payload);
        input.value = '';
    }
}

function onPhaseChatSend() {
    const input = $('phase-chat-input');
    if (!input) return;
    const text = input.value.trim();
    if (text && socket) {
        const payload = applyChatChannelPayload({ text }, 'phase-chat-channel');
        socket.emit('chat', payload);
        input.value = '';
    }
}

function setupPlayZoneDrop() {
}

let settingsMods = [];
let settingsCommunityMods = [];
let settingsAllowServerEdit = true;
let settingsActiveTab = 'appearance';
let settingsActiveModTab = ['official', 'community'].includes(localStorage.getItem('gtn_settings_mod_tab'))
    ? localStorage.getItem('gtn_settings_mod_tab')
    : 'official';
const VANILLA_MOD_FILENAME = 'Vanilla Cards.gtnmod';
const DEFAULT_ENABLED_OFFICIAL_MOD_FILENAMES = new Set([
    VANILLA_MOD_FILENAME,
    'Troll Cards.gtnmod',
    'Thorn Cards.gtnmod',
]);
const FALLBACK_DEFAULT_DISABLED_MODS = [
    'Desert Cards Addition.gtnmod',
    'Factory Cards.gtnmod',
    'Garden Cards Addition.gtnmod',
];
const REQUIRED_MOD_CARD_TYPES = ['thorn', 'bloom', 'root', 'guard'];
const COMMUNITY_JSON_MAX_BYTES = 150 * 1024;
const COMMUNITY_GTNMOD_MAX_BYTES = 1024 * 1024;
let communityUploadInProgress = false;

function getCommunityModSelection() {
    // Community mods require hidden features enabled
    if (!hiddenFeaturesEnabled()) {
        return { mod_source: 'official', community_mods: [], community_mod_url: '', community_mod_hash: '', community_mod_name: '' };
    }
    let mods = [];
    try {
        const raw = localStorage.getItem('gtn_community_mods');
        mods = raw ? JSON.parse(raw) : [];
    } catch {
        mods = [];
    }
    if (!Array.isArray(mods)) mods = [];
    const clean = [];
    const seen = new Set();
    mods.forEach(mod => {
        if (!mod || typeof mod !== 'object') return;
        const publicUrl = String(mod.public_url || mod.url || '').trim();
        const sha256 = String(mod.sha256 || mod.hash || '').trim().toLowerCase();
        if (!publicUrl || !/^[0-9a-f]{64}$/.test(sha256) || seen.has(sha256)) return;
        seen.add(sha256);
        clean.push({
            public_url: publicUrl,
            sha256,
            name: String(mod.name || '').trim(),
            uploaded_at: String(mod.uploaded_at || '').trim(),
        });
    });
    if (!clean.length) {
        return { mod_source: 'official', community_mods: [], community_mod_url: '', community_mod_hash: '', community_mod_name: '' };
    }
    const names = clean.map(mod => mod.name || mod.sha256.slice(0, 8)).join(' / ');
    return {
        mod_source: 'community',
        community_mods: clean,
        community_mod_url: clean.length === 1 ? clean[0].public_url : '',
        community_mod_hash: clean.map(mod => mod.sha256).sort().join(','),
        community_mod_name: names,
    };
}

function getSettingsModSourceTab() {
    return getCommunityModSelection().mod_source;
}

function getModLoginPayload() {
    return { disabled_mods: getDisabledMods(), ...getCommunityModSelection() };
}

function buildModQueryString() {
    const params = new URLSearchParams();
    params.set('disabled_mods', getDisabledMods().join(','));
    const community = getCommunityModSelection();
    params.set('mod_source', community.mod_source);
    if (community.mod_source === 'community') {
        params.set('community_mods', JSON.stringify(community.community_mods));
    }
    return params.toString();
}

function openSettings(options = {}) {
    settingsAllowServerEdit = !options.hideServer;
    const panel = $('settings-panel');
    if (panel) panel.classList.remove('hidden');
    if (!settingsAllowServerEdit && settingsActiveTab === 'server') settingsActiveTab = 'appearance';
    renderSettingsTabs();
    loadSettingsMods();
    const serverInput = $('settings-server-input');
    if (serverInput && settingsAllowServerEdit) {
        localStorage.removeItem('gtn_server');
        serverInput.value = '';
        serverInput.placeholder = DEFAULT_SERVER;
    }
    const serverHint = $('settings-server-hint');
    if (serverHint && settingsAllowServerEdit) {
        serverHint.textContent = tf('server_hint', DEFAULT_SERVER);
    }
    renderModSourceControls();
    renderSocialSettings();
}

function setSettingsTab(tab) {
    if (tab === 'server' && !settingsAllowServerEdit) tab = 'appearance';
    settingsActiveTab = ['appearance', 'server', 'mods', 'social'].includes(tab) ? tab : 'appearance';
    renderSettingsTabs();
}

function renderSettingsTabs() {
    const hidden = hiddenFeaturesEnabled();
    const tabs = ['appearance', 'server', 'mods', 'social'];
    tabs.forEach(tab => {
        const btn = $(`settings-tab-${tab}`);
        const page = $(`settings-page-${tab}`);
        const active = settingsActiveTab === tab;
        if (btn) {
            btn.classList.toggle('active', active);
            btn.setAttribute('aria-pressed', active ? 'true' : 'false');
            if (tab === 'server') btn.classList.toggle('hidden', !settingsAllowServerEdit);
        }
        if (page) {
            page.classList.toggle('hidden', !active || (tab === 'server' && !settingsAllowServerEdit));
        }
    });
}

function closeSettings() {
    const panel = $('settings-panel');
    if (panel) panel.classList.add('hidden');
}

async function loadSettingsMods() {
    const listEl = $('settings-mods-list');
    const noModsEl = $('settings-no-mods');
    if (!listEl) return;
    try {
        const resp = await fetch('/api/mods');
        const mods = await resp.json();
        settingsMods = mods || [];
    } catch (e) {
        settingsMods = [];
    }
    renderOfficialModList();
    loadSettingsCommunityMods();
    renderModSourceControls();
}

function settingsModDetailKey(kind, key) {
    return `gtn_settings_mod_detail_${kind}_${encodeURIComponent(String(key || 'unknown'))}`;
}

function isSettingsModDetailOpen(kind, key) {
    return localStorage.getItem(settingsModDetailKey(kind, key)) === 'open';
}

function setSettingsModDetailOpen(kind, key, open) {
    localStorage.setItem(settingsModDetailKey(kind, key), open ? 'open' : 'closed');
    if (kind === 'community') renderCommunityModList();
    else renderOfficialModList();
}

function createSettingsModCaret(kind, key, expanded) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'settings-mod-item-toggle';
    btn.textContent = '>';
    btn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    btn.onclick = () => setSettingsModDetailOpen(kind, key, !expanded);
    return btn;
}

const BETA_TESTING_MOD_IDS = new Set(['jungle', 'desert_cards_addition', 'garden', 'factory']);

function isBetaTestingMod(mod) {
    const info = mod?.info || {};
    const candidates = [
        info.id,
        info.name,
        info.name_cn,
        info.name_en,
        mod?.filename,
        mod?.name,
    ].filter(Boolean).map(value => String(value).toLowerCase());
    return candidates.some(value =>
        BETA_TESTING_MOD_IDS.has(value)
        || value.includes('jungle cards addition')
        || value.includes('desert cards addition')
        || value.includes('garden cards addition')
        || value.includes('factory cards addition')
        || value.includes('丛林卡')
        || value.includes('沙漠卡')
        || value.includes('花园卡')
        || value.includes('工厂卡')
    );
}

function createModBetaWarningBadge() {
    const label = UI.mod_beta_warning || '测试中，不推荐使用';
    const badge = document.createElement('span');
    badge.className = 'mod-beta-warning';
    badge.title = label;
    badge.setAttribute('aria-label', label);

    const icon = document.createElement('span');
    icon.className = 'mod-beta-warning-icon';
    icon.textContent = '!';
    badge.appendChild(icon);

    const text = document.createElement('span');
    text.className = 'mod-beta-warning-text';
    text.textContent = label;
    badge.appendChild(text);
    return badge;
}

function renderOfficialModList() {
    const listEl = $('settings-mods-list');
    const noModsEl = $('settings-no-mods');
    if (!listEl) return;
    listEl.innerHTML = '';
    if (settingsMods.length === 0) {
        if (noModsEl) noModsEl.style.display = '';
        return;
    }
    if (noModsEl) noModsEl.style.display = 'none';
    const disabled = getDisabledMods();
    settingsMods.forEach((mod, i) => {
        const info = mod.info || {};
        const name = localizedModNameFromFields(info, mod.filename || tf('mod_default_name', i + 1));
        const version = info.version || '';
        const filename = mod.filename || '';
        const errors = Array.isArray(mod.errors) ? mod.errors.filter(Boolean) : [];
        const expanded = isSettingsModDetailOpen('official', filename || name);
        const item = document.createElement('div');
        item.className = 'settings-mod-item settings-mod-card';
        if (errors.length) item.classList.add('mod-error');
        if (expanded) item.classList.add('mod-expanded');
        item.appendChild(createSettingsModCaret('official', filename || name, expanded));
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.id = `mod-cb-${i}`;
        cb.checked = !errors.length && !disabled.includes(filename);
        cb.disabled = errors.length > 0;
        cb.dataset.filename = filename;
        item.appendChild(cb);
        const main = document.createElement('div');
        main.className = 'settings-mod-item-main';
        const label = document.createElement('label');
        label.htmlFor = cb.id;
        label.textContent = name;
        main.appendChild(label);
        if (version) {
            const ver = document.createElement('span');
            ver.className = 'mod-version';
            ver.textContent = `v${version}`;
            main.appendChild(ver);
        }
        if (isBetaTestingMod(mod)) {
            main.appendChild(createModBetaWarningBadge());
        }
        item.appendChild(main);
        const details = document.createElement('div');
        details.className = 'settings-mod-card-details' + (expanded ? '' : ' hidden');
        const metaParts = [];
        if (filename) metaParts.push(filename);
        if (info.author) metaParts.push(info.author);
        if (mod.cards_count != null) metaParts.push(tf('community_cards_count', mod.cards_count));
        const counts = getModCardTypeCounts(mod);
        const countText = REQUIRED_MOD_CARD_TYPES
            .map(type => `${getCardTypeLabel(type)}:${Number(counts[type] || 0)}`)
            .join(' / ');
        if (countText) metaParts.push(countText);
        if (metaParts.length) {
            const meta = document.createElement('div');
            meta.className = 'mod-meta';
            meta.textContent = metaParts.join(' · ');
            details.appendChild(meta);
        }
        const descText = localizedModDescriptionFromFields(info, mod.description || '');
        if (descText) {
            const desc = document.createElement('div');
            desc.className = 'mod-description';
            desc.textContent = descText;
            details.appendChild(desc);
        }
        if (errors.length) {
            const err = document.createElement('span');
            err.className = 'mod-error-text';
            err.textContent = `${UI.mod_validation_error || '格式错误'}：${errors.slice(0, 3).join('；')}`;
            err.title = errors.join('\n');
            details.appendChild(err);
        }
        item.appendChild(details);
        listEl.appendChild(item);
    });
}

function setSettingsModSourceTab(tab) {
    if (tab === 'community' && !hiddenFeaturesEnabled()) tab = 'official';
    settingsActiveModTab = tab === 'community' ? 'community' : 'official';
    localStorage.setItem('gtn_settings_mod_tab', settingsActiveModTab);
    renderModSourceControls();
}

function renderModSourceTabs() {
    const hidden = hiddenFeaturesEnabled();
    ['official', 'community'].forEach(kind => {
        const btn = $(`settings-mod-tab-${kind}`);
        if (!btn) return;
        const active = settingsActiveModTab === kind;
        btn.classList.toggle('active', active);
        btn.setAttribute('aria-pressed', active ? 'true' : 'false');
        // Hide community tab when hidden features disabled
        if (kind === 'community') btn.classList.toggle('hidden', !hidden);
    });
}

function renderModSourceControls() {
    const officialBox = $('settings-official-mods');
    const communityBox = $('settings-community-mods');
    const hidden = hiddenFeaturesEnabled();
    // Force official tab when hidden features disabled
    if (!hidden && settingsActiveModTab === 'community') settingsActiveModTab = 'official';
    renderModSourceTabs();
    if (officialBox) officialBox.classList.toggle('hidden', settingsActiveModTab !== 'official');
    if (communityBox) communityBox.classList.toggle('hidden', settingsActiveModTab !== 'community' || !hidden);
    renderCommunityCurrent();
}

function setModSource(source) {
    if (source !== 'community') localStorage.setItem('gtn_community_mods', '[]');
    renderModSourceControls();
    renderCommunityModList();
}

function refreshCardsAfterCommunityChange() {
    fetchCardDefs({ useCache: false }).then(() => fetchOpeningEvents({ useCache: false })).then(() => {
        loadSoloDecks(false);
        renderSoloBuilder();
    });
    if (socket && socket.connected && phase === 'lobby') {
        socket.emit('update_mod_settings', { disabled_mods: getDisabledMods(), ...getCommunityModSelection() });
    }
}

function clearCommunityModSelection() {
    localStorage.setItem('gtn_community_mods', '[]');
    renderModSourceControls();
    renderCommunityModList();
    refreshCardsAfterCommunityChange();
}

function formatCommunityTime(value) {
    const text = String(value || '').trim();
    if (!text) return '';
    const parsed = new Date(text);
    if (Number.isNaN(parsed.getTime())) return text;
    return parsed.toLocaleString();
}

function communityModTitle(mod, index = 0) {
    return localizedModNameFromFields(mod, mod.name || `Community Mod ${index + 1}`);
}

function setSelectedCommunityMods(mods) {
    const clean = [];
    const seen = new Set();
    (Array.isArray(mods) ? mods : []).forEach(mod => {
        if (!mod || typeof mod !== 'object') return;
        const publicUrl = String(mod.public_url || mod.url || '').trim();
        const sha256 = String(mod.sha256 || mod.hash || '').trim().toLowerCase();
        if (!publicUrl || !/^[0-9a-f]{64}$/.test(sha256) || seen.has(sha256)) return;
        seen.add(sha256);
        clean.push({
            public_url: publicUrl,
            sha256,
            name: String(mod.name || '').trim(),
            uploaded_at: String(mod.uploaded_at || '').trim(),
        });
    });
    localStorage.setItem('gtn_community_mods', JSON.stringify(clean));
}

function toggleCommunityModSelection(mod, enabled) {
    if (!mod || !mod.sha256 || !mod.public_url) return;
    const selected = getCommunityModSelection().community_mods || [];
    const filtered = selected.filter(item => item.sha256 !== mod.sha256);
    if (enabled) {
        filtered.push({
            public_url: mod.public_url || '',
            sha256: mod.sha256 || '',
            name: mod.name || '',
        });
    }
    setSelectedCommunityMods(filtered);
    renderCommunityCurrent();
    renderCommunityModList();
    refreshCardsAfterCommunityChange();
}

function renderCommunityCurrent() {
    const nameEl = $('settings-community-current-name');
    const metaEl = $('settings-community-current-meta');
    const disableBtn = $('btn-community-disable');
    if (!nameEl && !metaEl && !disableBtn) return;
    const selected = getCommunityModSelection();
    const selectedHashes = new Set((selected.community_mods || []).map(mod => mod.sha256));
    const current = settingsCommunityMods.filter(mod => selectedHashes.has(mod.sha256));
    if (!current.length && selected.mod_source !== 'community') {
        if (nameEl) nameEl.textContent = UI.community_disabled;
        if (metaEl) metaEl.textContent = '';
        if (disableBtn) disableBtn.disabled = true;
        return;
    }
    if (nameEl) nameEl.textContent = current.length
        ? current.map((mod, i) => communityModTitle(mod, i)).join(' / ')
        : (selected.community_mod_name || UI.community_disabled);
    if (metaEl) metaEl.textContent = current.length
        ? `${current.length} ${UI.community_mods}`
        : '';
    if (disableBtn) disableBtn.disabled = false;
}

function formatCommunityUploadBytes(bytes) {
    const value = Math.max(0, Number(bytes) || 0);
    if (value < 1024) return `${Math.round(value)} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(value < 100 * 1024 ? 1 : 0)} KB`;
    return `${(value / (1024 * 1024)).toFixed(2)} MB`;
}

function formatCommunityUploadDuration(seconds) {
    const value = Number(seconds);
    if (!Number.isFinite(value) || value < 0) return '--';
    if (value < 1) return '<1s';
    if (value < 60) return `${Math.ceil(value)}s`;
    const minutes = Math.floor(value / 60);
    const rest = Math.ceil(value % 60);
    return rest ? `${minutes}m ${rest}s` : `${minutes}m`;
}

function setCommunityUploadProgress(loaded, total, text) {
    const box = $('community-upload-progress');
    const fill = $('community-upload-progress-fill');
    const textEl = $('community-upload-progress-text');
    if (!box) return;
    box.classList.remove('hidden');
    const safeTotal = Math.max(0, Number(total) || 0);
    const safeLoaded = Math.max(0, Number(loaded) || 0);
    const percent = safeTotal > 0 ? Math.max(0, Math.min(100, (safeLoaded / safeTotal) * 100)) : 0;
    if (fill) fill.style.width = `${percent}%`;
    if (textEl) textEl.textContent = text || '';
}

function hideCommunityUploadProgress() {
    const box = $('community-upload-progress');
    const fill = $('community-upload-progress-fill');
    const textEl = $('community-upload-progress-text');
    if (fill) fill.style.width = '0%';
    if (textEl) textEl.textContent = '';
    if (box) box.classList.add('hidden');
}

function buildCommunityUploadProgressText(loaded, total, startedAt) {
    const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    const elapsed = Math.max(0.1, (now - startedAt) / 1000);
    const safeTotal = Math.max(Number(total) || 0, Number(loaded) || 0);
    const safeLoaded = Math.max(0, Number(loaded) || 0);
    const speed = safeLoaded / elapsed;
    const eta = speed > 0 && safeTotal > safeLoaded
        ? (safeTotal - safeLoaded) / speed
        : (safeTotal > safeLoaded ? NaN : 0);
    return tf(
        'community_upload_progress',
        formatCommunityUploadBytes(safeLoaded),
        formatCommunityUploadBytes(safeTotal),
        formatCommunityUploadBytes(speed),
        formatCommunityUploadDuration(eta)
    );
}

function uploadCommunityFileToR2(url, file, contentType, onProgress) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('PUT', url, true);
        xhr.setRequestHeader('Content-Type', contentType);
        xhr.upload.onprogress = event => {
            const total = event.lengthComputable ? event.total : (file?.size || event.loaded || 0);
            onProgress?.(event.loaded || 0, total);
        };
        xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve(xhr);
            } else {
                reject(new Error(tf('community_r2_upload_failed', xhr.status || 0)));
            }
        };
        xhr.onerror = () => reject(new Error(tf('community_r2_upload_failed', xhr.status || 0)));
        xhr.onabort = () => reject(new Error(tf('community_r2_upload_failed', xhr.status || 0)));
        xhr.send(file);
    });
}

function updateCommunityUploadState() {
    const btn = $('btn-community-upload');
    if (!btn) return;
    btn.disabled = !currentAccount || communityUploadInProgress;
    btn.title = currentAccount ? '' : (UI.community_upload_hint || '');
}

function validateCommunityUploadFile(file) {
    const name = String(file?.name || '').toLowerCase();
    if (!name.endsWith('.json') && !name.endsWith('.gtnmod')) {
        throw new Error(UI.community_json_only);
    }
    const maxBytes = name.endsWith('.gtnmod') ? COMMUNITY_GTNMOD_MAX_BYTES : COMMUNITY_JSON_MAX_BYTES;
    if (file.size > maxBytes) {
        throw new Error(UI.community_file_too_large);
    }
}

async function uploadCommunityModFile(file) {
    const statusEl = $('settings-community-status');
    const setStatus = text => { if (statusEl) statusEl.textContent = text || ''; };
    if (communityUploadInProgress) return;
    if (!currentAccount) {
        hideCommunityUploadProgress();
        setStatus(UI.account_need_login || UI.community_upload_hint || '');
        return;
    }
    communityUploadInProgress = true;
    updateCommunityUploadState();
    try {
        hideCommunityUploadProgress();
        validateCommunityUploadFile(file);
        const lowerName = String(file.name || '').toLowerCase();
        if (lowerName.endsWith('.json')) {
            try {
                JSON.parse(await file.text());
            } catch (e) {
                throw new Error(tf('community_json_parse_failed', e.message || String(e)));
            }
        }
        const uploadTotal = file.size || 0;
        const uploadStartedAt = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
        setStatus(UI.community_uploading);
        setCommunityUploadProgress(0, uploadTotal, buildCommunityUploadProgressText(0, uploadTotal, uploadStartedAt));
        const urlResp = await fetch('/api/community-mods/upload-url', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: file.name }),
        });
        const urlData = await urlResp.json().catch(() => ({}));
        if (!urlResp.ok || !urlData.success) throw new Error(urlData.error || UI.community_upload_url_failed);
        const contentType = urlData.content_type || (lowerName.endsWith('.gtnmod') ? 'application/zip' : 'application/json');
        await uploadCommunityFileToR2(urlData.put_url, file, contentType, (loaded, total) => {
            const safeTotal = total || uploadTotal || loaded;
            setCommunityUploadProgress(loaded, safeTotal, buildCommunityUploadProgressText(loaded, safeTotal, uploadStartedAt));
        });
        setCommunityUploadProgress(uploadTotal, uploadTotal, UI.community_upload_registering);
        const registerResp = await fetch('/api/community-mods/register', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key: urlData.key, public_url: urlData.public_url, uploader_name: currentAccount.username || '' }),
        });
        const registerData = await registerResp.json().catch(() => ({}));
        if (!registerResp.ok || !registerData.success) {
            const errorText = Array.isArray(registerData.errors) ? registerData.errors.join('；') : (registerData.error || UI.community_register_failed);
            throw new Error(errorText);
        }
        const mod = registerData.mod || {};
        const uploadSuccess = tf('community_upload_success', mod.name || file.name);
        const warnings = Array.isArray(registerData.warnings) ? registerData.warnings.filter(Boolean) : [];
        const warningSuffix = warnings.length ? ` · ${warnings[0]}` : '';
        setStatus(`${uploadSuccess}${warningSuffix}`);
        setCommunityUploadProgress(uploadTotal, uploadTotal, `${uploadSuccess}${warningSuffix}`);
        await loadSettingsCommunityMods();
    } catch (e) {
        setStatus(e.message || String(e));
    } finally {
        communityUploadInProgress = false;
        updateCommunityUploadState();
    }
}

async function loadSettingsCommunityMods() {
    const listEl = $('settings-community-mods-list');
    const noModsEl = $('settings-no-community-mods');
    const statusEl = $('settings-community-status');
    if (!listEl) return;
    try {
        const resp = await fetch('/api/community-mods');
        const data = await resp.json();
        settingsCommunityMods = Array.isArray(data) ? data : (data.mods || []);
        const available = new Set(settingsCommunityMods.map(mod => mod.sha256).filter(Boolean));
        const selected = getCommunityModSelection().community_mods || [];
        const pruned = selected.filter(mod => available.has(mod.sha256));
        if (selected.length !== pruned.length) setSelectedCommunityMods(pruned);
        if (statusEl) statusEl.textContent = data && data.error ? data.error : '';
    } catch (e) {
        settingsCommunityMods = [];
        if (statusEl) statusEl.textContent = e.message || String(e);
    }
    renderCommunityModList();
    renderCommunityCurrent();
}

function renderCommunityModList() {
    const listEl = $('settings-community-mods-list');
    const noModsEl = $('settings-no-community-mods');
    if (!listEl) return;
    listEl.innerHTML = '';
    const selected = getCommunityModSelection();
    if (!settingsCommunityMods.length) {
        if (noModsEl) noModsEl.style.display = '';
        renderCommunityCurrent();
        updateCommunityUploadState();
        return;
    }
    if (noModsEl) noModsEl.style.display = 'none';
    const selectedHashes = new Set((selected.community_mods || []).map(mod => mod.sha256));
    settingsCommunityMods.forEach((mod, i) => {
        const item = document.createElement('div');
        item.className = 'settings-community-card settings-mod-card';
        const expandKey = mod.sha256 || mod.public_url || communityModTitle(mod, i);
        const expanded = isSettingsModDetailOpen('community', expandKey);
        if (expanded) item.classList.add('mod-expanded');
        const isSelected = selectedHashes.has(mod.sha256);
        if (isSelected) {
            item.classList.add('community-selected');
        }
        item.appendChild(createSettingsModCaret('community', expandKey, expanded));
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'community-card-check';
        checkbox.checked = isSelected;
        checkbox.title = isSelected ? UI.community_selected : UI.community_select;
        checkbox.onchange = () => toggleCommunityModSelection(mod, checkbox.checked);
        const main = document.createElement('div');
        main.className = 'community-card-main';
        const title = document.createElement('div');
        title.className = 'community-card-title';
        const titleText = document.createElement('span');
        titleText.textContent = communityModTitle(mod, i);
        title.appendChild(titleText);
        if (isSelected) {
            const badge = document.createElement('span');
            badge.className = 'community-badge';
            badge.textContent = UI.community_selected;
            title.appendChild(badge);
        }
        if (mod.can_manage) {
            const badge = document.createElement('span');
            badge.className = 'community-badge';
            badge.textContent = UI.community_owned_by_you;
            title.appendChild(badge);
        }
        main.appendChild(title);
        item.append(checkbox, main);
        const details = document.createElement('div');
        details.className = 'settings-mod-card-details' + (expanded ? '' : ' hidden');
        const meta = document.createElement('div');
        meta.className = 'community-card-meta';
        const metaParts = [];
        if (mod.version) metaParts.push(`v${mod.version}`);
        if (mod.author) metaParts.push(mod.author);
        if (mod.cards_count != null) metaParts.push(tf('community_cards_count', mod.cards_count));
        if (mod.uploaded_at) metaParts.push(tf('community_uploaded_at', formatCommunityTime(mod.uploaded_at)));
        meta.textContent = metaParts.join(' · ');
        if (meta.textContent) details.appendChild(meta);
        const communityDescText = localizedModDescriptionFromFields(mod, mod.description || '');
        if (communityDescText) {
            const desc = document.createElement('div');
            desc.className = 'community-card-desc';
            desc.textContent = communityDescText;
            details.appendChild(desc);
        }
        const warnings = Array.isArray(mod.warnings) ? mod.warnings.filter(Boolean) : [];
        if (warnings.length) {
            const warning = document.createElement('div');
            warning.className = 'community-card-warning';
            warning.textContent = warnings.slice(0, 3).join('；');
            warning.title = warnings.join('\n');
            details.appendChild(warning);
        }
        const actions = document.createElement('div');
        actions.className = 'community-card-actions';
        const selectBtn = document.createElement('button');
        selectBtn.type = 'button';
        selectBtn.className = 'btn ' + (isSelected ? 'btn-primary' : 'btn-secondary');
        selectBtn.textContent = isSelected ? UI.community_selected : UI.community_select;
        selectBtn.onclick = () => toggleCommunityModSelection(mod, !isSelected);
        actions.appendChild(selectBtn);
        if (mod.can_manage) {
            const deleteBtn = document.createElement('button');
            deleteBtn.type = 'button';
            deleteBtn.className = 'btn btn-danger';
            deleteBtn.textContent = UI.community_delete;
            deleteBtn.onclick = () => deleteCommunityMod(mod);
            actions.append(deleteBtn);
        }
        details.appendChild(actions);
        item.appendChild(details);
        listEl.appendChild(item);
    });
    renderCommunityCurrent();
    updateCommunityUploadState();
}

async function deleteCommunityMod(mod) {
    const statusEl = $('settings-community-status');
    const setStatus = text => { if (statusEl) statusEl.textContent = text || ''; };
    if (!mod || !mod.sha256) return;
    if (!window.confirm(UI.community_delete_confirm)) return;
    try {
        const resp = await fetch(`/api/community-mods/${encodeURIComponent(mod.sha256)}`, {
            method: 'DELETE',
            credentials: 'same-origin',
        });
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok || !data.success) throw new Error(data.error || UI.community_delete_failed);
        const selected = getCommunityModSelection();
        if ((selected.community_mods || []).some(item => item.sha256 === mod.sha256)) {
            setSelectedCommunityMods((selected.community_mods || []).filter(item => item.sha256 !== mod.sha256));
            refreshCardsAfterCommunityChange();
        }
        setStatus(UI.community_delete_success);
        await loadSettingsCommunityMods();
    } catch (e) {
        setStatus(e.message || String(e));
    }
}

function getDisabledMods() {
    try {
        const raw = localStorage.getItem('gtn_disabled_mods');
        let disabled = raw ? JSON.parse(raw) : getDefaultDisabledMods();
        if (shouldMigrateLegacyOfficialModDefault(disabled) || shouldMigrateOfficialModDefaultV3(disabled)) {
            disabled = getDefaultDisabledMods();
            localStorage.setItem('gtn_disabled_mods', JSON.stringify(disabled));
            localStorage.setItem('gtn_official_mod_default_v2', '1');
            localStorage.setItem('gtn_official_mod_default_v3', '1');
        }
        return coerceValidDisabledMods(disabled).disabled;
    } catch (e) {
        return coerceValidDisabledMods(getDefaultDisabledMods()).disabled;
    }
}

function getDefaultDisabledMods() {
    if (!Array.isArray(settingsMods) || settingsMods.length === 0) {
        return FALLBACK_DEFAULT_DISABLED_MODS.slice();
    }
    return settingsMods
        .map(mod => mod.filename || '')
        .filter(filename => filename && !DEFAULT_ENABLED_OFFICIAL_MOD_FILENAMES.has(filename));
}

function getLegacyDefaultDisabledMods() {
    if (!Array.isArray(settingsMods) || settingsMods.length === 0) return [];
    return settingsMods
        .map(mod => mod.filename || '')
        .filter(filename => filename && filename !== VANILLA_MOD_FILENAME);
}

function shouldMigrateLegacyOfficialModDefault(disabled) {
    if (localStorage.getItem('gtn_official_mod_default_v2') === '1') return false;
    if (!Array.isArray(disabled) || !Array.isArray(settingsMods) || settingsMods.length === 0) return false;
    const legacy = getLegacyDefaultDisabledMods();
    if (!legacy.length || disabled.length !== legacy.length) return false;
    const currentSet = new Set(disabled.map(String));
    return legacy.every(filename => currentSet.has(filename));
}

function shouldMigrateOfficialModDefaultV3(disabled) {
    if (localStorage.getItem('gtn_official_mod_default_v3') === '1') return false;
    if (!Array.isArray(disabled)) return false;
    return disabled.length === 0;
}

function getModCardTypeCounts(mod) {
    const counts = { thorn: 0, bloom: 0, root: 0, guard: 0 };
    const provided = mod && mod.card_type_counts;
    if (provided && typeof provided === 'object') {
        REQUIRED_MOD_CARD_TYPES.forEach(type => {
            counts[type] = Number(provided[type] || 0);
        });
        return counts;
    }
    (mod && mod.cards ? mod.cards : []).forEach(card => {
        const type = card.card_type;
        if (Object.prototype.hasOwnProperty.call(counts, type) && Number(card.count || 0) > 0) {
            counts[type] += 1;
        }
    });
    return counts;
}

function modSelectionHasRequiredTypes(disabled) {
    if (!Array.isArray(settingsMods) || settingsMods.length === 0) return true;
    const disabledSet = new Set(disabled || []);
    const counts = { thorn: 0, bloom: 0, root: 0, guard: 0 };
    settingsMods.forEach(mod => {
        const filename = mod.filename || '';
        if (!filename || disabledSet.has(filename) || (mod.errors && mod.errors.length)) return;
        const modCounts = getModCardTypeCounts(mod);
        REQUIRED_MOD_CARD_TYPES.forEach(type => {
            counts[type] += Number(modCounts[type] || 0);
        });
    });
    return REQUIRED_MOD_CARD_TYPES.every(type => counts[type] > 0);
}

function coerceValidDisabledMods(disabled) {
    const next = Array.isArray(disabled) ? disabled.filter(Boolean).map(String) : [];
    let forcedVanilla = false;
    if (!modSelectionHasRequiredTypes(next)) {
        const idx = next.indexOf(VANILLA_MOD_FILENAME);
        if (idx >= 0) {
            next.splice(idx, 1);
            forcedVanilla = true;
        }
    }
    return { disabled: Array.from(new Set(next)), forcedVanilla };
}

function saveDisabledMods() {
    const listEl = $('settings-mods-list');
    if (!listEl) return;
    const checkboxes = listEl.querySelectorAll('input[type="checkbox"]');
    let disabled = [];
    checkboxes.forEach(cb => {
        if (!cb.checked && cb.dataset.filename) {
            disabled.push(cb.dataset.filename);
        }
    });
    const coerced = coerceValidDisabledMods(disabled);
    disabled = coerced.disabled;
    if (coerced.forcedVanilla) {
        checkboxes.forEach(cb => {
            if (cb.dataset.filename === VANILLA_MOD_FILENAME) cb.checked = true;
        });
        showActionToast(tf('mod_selection_force_vanilla'), 2800, 'error');
    }
    localStorage.setItem('gtn_disabled_mods', JSON.stringify(disabled));
    const serverInput = $('settings-server-input');
    if (serverInput && settingsAllowServerEdit) {
        localStorage.removeItem('gtn_server');
        serverInput.value = '';
    }
    if (socket && socket.connected && phase === 'lobby') {
        socket.emit('update_mod_settings', { disabled_mods: disabled, ...getCommunityModSelection() });
    }
    fetchCardDefs({ useCache: false }).then(() => fetchOpeningEvents({ useCache: false })).then(() => {
        loadSoloDecks(false);
        renderSoloBuilder();
    });
}

function initModEditor() {
    const editorArea = $('mod-editor-area');
    const loadBtn = $('btn-mod-load');
    const saveBtn = $('btn-mod-save');
    const validateBtn = $('btn-mod-validate');
    const backBtn = $('btn-mod-back');
    const statusEl = $('mod-editor-status');
    if (loadBtn) {
        loadBtn.onclick = async () => {
            try {
                const resp = await fetch('/api/mods');
                const mods = await resp.json();
                if (editorArea) editorArea.value = JSON.stringify(mods, null, 2);
                if (statusEl) statusEl.textContent = UI.load_success;
            } catch (e) {
                if (editorArea) editorArea.value = '';
                if (statusEl) statusEl.textContent = UI.load_failed;
            }
        };
    }
    if (saveBtn) {
        saveBtn.onclick = async () => {
            try {
                const data = JSON.parse(editorArea ? editorArea.value : '');
                const resp = await fetch('/api/mods/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data),
                });
                const result = await resp.json();
                if (statusEl) statusEl.textContent = result.message || UI.save_success;
            } catch (e) {
                if (statusEl) statusEl.textContent = tf('save_failed', e.message);
            }
        };
    }
    if (validateBtn) {
        validateBtn.onclick = () => {
            try {
                JSON.parse(editorArea ? editorArea.value : '');
                if (statusEl) statusEl.textContent = UI.json_valid;
            } catch (e) {
                if (statusEl) statusEl.textContent = tf('json_invalid', e.message);
            }
        };
    }
    if (backBtn) {
        backBtn.onclick = () => {
            showView('view-lobby');
        };
    }
}

function setupFullscreenPrompt() {
    const rotateHint = document.getElementById('rotate-hint');
    if (rotateHint) rotateHint.style.display = 'none';
    const isMobile = /Android|iPhone|iPad|iPod|webOS/i.test(navigator.userAgent) || 
                     (navigator.maxTouchPoints > 1 && window.innerWidth < 1024);
    if (!isMobile) return;
    const rotateDismiss = document.getElementById('btn-dismiss-rotate');
    if (rotateDismiss) {
        rotateDismiss.onclick = () => {
            const rotateHint = document.getElementById('rotate-hint');
            if (rotateHint) rotateHint.style.display = 'none';
        };
    }
}

async function init() {
    bootLoader.init();
    bootLoader.step(UI.init_scripts, 10);
    debugLog('[INIT] game init start');
    window.addEventListener('error', (event) => {
        console.error('[INIT/runtime-error]', event.message, event.filename, event.lineno, event.colno, event.error);
    });
    window.addEventListener('unhandledrejection', (event) => {
        console.error('[INIT/unhandled-rejection]', event.reason);
    });
    const bindClickOnce = (id, handler) => {
        const el = $(id);
        if (!el || el.dataset.gtnClickBound === '1') return;
        el.dataset.gtnClickBound = '1';
        el.addEventListener('click', handler);
    };
    bindClickOnce('btn-solo-training', showSoloTraining);
    bindClickOnce('btn-connect', onLogin);
    bindClickOnce('btn-open-settings', openSettings);
    bindClickOnce('btn-card-gallery', () => showCardGallery());
    bindClickOnce('btn-open-about', openAbout);

    document.addEventListener('contextmenu', (e) => {
        if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
        }
    });
    const savedTheme = localStorage.getItem('gtn_theme') || 'light';
    applyTheme(savedTheme);
    applyUiStyle(migrateStoredUiStyle());
    const savedLang = normalizeLang(localStorage.getItem('gtn_lang') || 'zh');
    applyLang(savedLang);
    bootLoader.step(UI.init_theme_lang, 24);
    bootLoader.step(UI.init_fonts, 36);
    if (document.fonts && document.fonts.ready) {
        try { await document.fonts.ready; } catch (_) {}
    }
    bootLoader.step(UI.init_fonts_done, 48);
    debugLog('[INIT] theme/language applied');
    await loadSettingsMods();
    await fetchCardDefs({ useCache: true, background: true });
    await fetchOpeningEvents({ useCache: true, background: true });
    await refreshAuthMe();
    bootLoader.step(UI.init_bindings, 90);
    debugLog('[INIT] card definitions loaded, count=', Object.keys(CARD_DEFS).length);
    bindClickOnce('btn-connect', onLogin);
    if ($('btn-account-login')) $('btn-account-login').addEventListener('click', onAccountLogin);
    if ($('btn-account-register')) $('btn-account-register').addEventListener('click', onAccountRegister);
    if ($('btn-account-change-password')) $('btn-account-change-password').addEventListener('click', onAccountChangePassword);
    if ($('btn-account-mode-login')) $('btn-account-mode-login').addEventListener('click', () => setAccountMode('login'));
    if ($('btn-account-mode-register')) $('btn-account-mode-register').addEventListener('click', () => setAccountMode('register'));
    if ($('btn-account-top')) $('btn-account-top').addEventListener('click', () => toggleAccountPopover());
    if ($('btn-friends-top')) $('btn-friends-top').addEventListener('click', () => toggleFriendsPopover());
    if ($('btn-skin-top')) $('btn-skin-top').addEventListener('click', openSkinEditor);
    if ($('btn-skin-back')) $('btn-skin-back').addEventListener('click', () => showView('view-login'));
    if ($('btn-skin-save')) $('btn-skin-save').addEventListener('click', saveSkinFromEditor);
    if ($('btn-skin-reset')) $('btn-skin-reset').addEventListener('click', resetSkinEditor);
    if ($('skin-primary-color')) $('skin-primary-color').addEventListener('input', renderSkinEditorPreview);
    if ($('skin-eye-shape')) $('skin-eye-shape').addEventListener('change', renderSkinEditorPreview);
    document.addEventListener('pointermove', updateSkinEyeTracking, { passive: true });
    if ($('btn-account-popover-close')) $('btn-account-popover-close').addEventListener('click', () => toggleAccountPopover(false));
    if ($('btn-friends-popover-close')) $('btn-friends-popover-close').addEventListener('click', () => toggleFriendsPopover(false));
    if ($('btn-social-detail-close')) $('btn-social-detail-close').addEventListener('click', () => toggleSocialDetailModal(false));
    document.querySelectorAll('[data-social-detail-tab]').forEach(btn => {
        btn.addEventListener('click', () => showSocialDetailTab(btn.dataset.socialDetailTab || 'profile'));
    });
    if ($('btn-account-popover-logout')) $('btn-account-popover-logout').addEventListener('click', onAccountLogout);
    if ($('btn-friend-add')) $('btn-friend-add').addEventListener('click', addFriendFromInput);
    if ($('btn-dm-start')) $('btn-dm-start').addEventListener('click', startDmFromIdentifier);
    if ($('btn-dm-refresh')) $('btn-dm-refresh').addEventListener('click', () => loadDmThreads(false));
    if ($('btn-dm-send')) $('btn-dm-send').addEventListener('click', sendDmMessage);
    const dmMessageInput = $('dm-message-input');
    if (dmMessageInput) {
        dmMessageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendDmMessage();
        });
    }
    const friendIdentifierInput = $('input-friend-identifier');
    if (friendIdentifierInput) {
        friendIdentifierInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') addFriendFromInput();
        });
    }
    document.addEventListener('click', (event) => {
        const respondBtn = event.target.closest('[data-friend-respond]');
        if (respondBtn) {
            event.preventDefault();
            respondFriendRequest(respondBtn.dataset.friendRespond, respondBtn.dataset.friendAction);
            return;
        }
        const removeBtn = event.target.closest('[data-friend-remove]');
        if (removeBtn) {
            event.preventDefault();
            removeFriend(removeBtn.dataset.friendRemove);
            return;
        }
        const friendOpenBtn = event.target.closest('[data-friend-open]');
        if (friendOpenBtn) {
            event.preventDefault();
            openFriendDetail(friendOpenBtn.dataset.friendOpen, 'profile');
            return;
        }
        const dmThreadBtn = event.target.closest('[data-dm-thread]');
        if (dmThreadBtn) {
            event.preventDefault();
            openDmThread(dmThreadBtn.dataset.dmThread);
            toggleSocialDetailModal(true, 'dm');
            return;
        }
        const dmUserBtn = event.target.closest('[data-dm-open-user]');
        if (dmUserBtn) {
            event.preventDefault();
            startDmToUser(dmUserBtn.dataset.dmOpenUser, dmUserBtn.dataset.dmOpenName || '');
        }
    });
    if ($('btn-account-replays-refresh')) $('btn-account-replays-refresh').addEventListener('click', loadAccountReplays);
    if ($('btn-account-replay-close')) $('btn-account-replay-close').addEventListener('click', closeAccountReplayModal);
    if ($('account-replay-progress')) {
        $('account-replay-progress').addEventListener('input', (event) => {
            stopAccountReplayPlayback();
            accountReplayFrameIndex = Number(event.target.value) || 0;
            renderAccountReplayFrame();
        });
    }
    document.querySelectorAll('[data-account-replay-control]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const action = btn.dataset.accountReplayControl;
            if (action === 'prev') stepAccountReplay(-1);
            if (action === 'next') stepAccountReplay(1);
            if (action === 'play') playAccountReplay();
            if (action === 'pause') stopAccountReplayPlayback();
        });
    });
    document.querySelectorAll('[data-account-replay-speed]').forEach((btn) => {
        btn.addEventListener('click', () => {
            accountReplaySpeed = btn.dataset.accountReplaySpeed === 'instant' ? 'instant' : Number(btn.dataset.accountReplaySpeed || 1);
            if (accountReplayTimer) playAccountReplay();
        });
    });
    document.addEventListener('click', (event) => {
        const replayButton = event.target.closest('[data-account-replay-view]');
        if (replayButton) {
            event.preventDefault();
            openAccountReplay(replayButton.dataset.accountReplayView);
        }
    });
    const accountPasswordInput = $('input-account-password');
    if (accountPasswordInput) {
        accountPasswordInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') (accountMode === 'register' ? onAccountRegister() : onAccountLogin());
        });
    }
    const accountConfirmInput = $('input-account-password-confirm');
    if (accountConfirmInput) {
        accountConfirmInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') onAccountRegister();
        });
    }
    ['input-account-old-password', 'input-account-new-password', 'input-account-new-password-confirm'].forEach((id) => {
        const input = $(id);
        if (input) {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') onAccountChangePassword();
            });
        }
    });
    const accountUsernameInput = $('input-account-username');
    if (accountUsernameInput) {
        accountUsernameInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') (accountMode === 'register' ? onAccountRegister() : onAccountLogin());
        });
    }
    bindClickOnce('btn-solo-training', showSoloTraining);
    bindClickOnce('btn-card-gallery', () => showCardGallery());
    bindClickOnce('btn-open-about', openAbout);
    const savedNick = localStorage.getItem('gtn_nickname') || '';
    const nickInput = $('input-nickname');
    if (savedNick && displayWidth(savedNick) <= 16) nickInput.value = savedNick;
    nickInput.removeAttribute('maxlength');
    nickInput.addEventListener('input', () => {
        let val = nickInput.value;
        while (val && displayWidth(val) > 16) {
            val = val.slice(0, -1);
        }
        if (val !== nickInput.value) nickInput.value = val;
    });
    nickInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') onLogin();
    });
    bindClickOnce('btn-open-settings', openSettings);
    $('btn-settings-close').addEventListener('click', () => { saveDisabledMods(); closeSettings(); });
    if ($('btn-lobby-settings')) $('btn-lobby-settings').addEventListener('click', () => openSettings({ hideServer: true }));
    if ($('settings-tab-appearance')) $('settings-tab-appearance').addEventListener('click', () => setSettingsTab('appearance'));
    if ($('settings-tab-server')) $('settings-tab-server').addEventListener('click', () => setSettingsTab('server'));
    if ($('settings-tab-mods')) $('settings-tab-mods').addEventListener('click', () => setSettingsTab('mods'));
    if ($('settings-tab-social')) $('settings-tab-social').addEventListener('click', () => setSettingsTab('social'));
    ['settings-accept-friend-requests', 'settings-searchable-by-nickname', 'settings-searchable-by-player-id'].forEach((id) => {
        const input = $(id);
        if (input) input.addEventListener('change', saveSocialSettings);
    });
    if ($('settings-mod-tab-official')) $('settings-mod-tab-official').addEventListener('click', () => setSettingsModSourceTab('official'));
    if ($('settings-mod-tab-community')) $('settings-mod-tab-community').addEventListener('click', () => setSettingsModSourceTab('community'));
    if ($('btn-community-refresh')) $('btn-community-refresh').addEventListener('click', loadSettingsCommunityMods);
    if ($('btn-community-disable')) $('btn-community-disable').addEventListener('click', clearCommunityModSelection);
    if ($('btn-community-upload')) $('btn-community-upload').addEventListener('click', () => $('community-mod-file-input')?.click());
    if ($('community-mod-file-input')) $('community-mod-file-input').addEventListener('change', async (event) => {
        const file = event.target.files && event.target.files[0];
        if (file) await uploadCommunityModFile(file);
        event.target.value = '';
    });
    if ($('about-tab-rules')) $('about-tab-rules').addEventListener('click', () => setAboutPage('rules'));
    if ($('about-tab-credits')) $('about-tab-credits').addEventListener('click', () => setAboutPage('credits'));
    if ($('btn-about-close')) $('btn-about-close').addEventListener('click', closeAbout);
    if ($('btn-credit-bilibili')) $('btn-credit-bilibili').addEventListener('click', () => window.open('https://space.bilibili.com/1490695733', '_blank', 'noopener'));
    if ($('btn-credit-github')) $('btn-credit-github').addEventListener('click', () => window.open('https://github.com/Stickerbug', '_blank', 'noopener'));
    document.querySelectorAll('[data-copy-text]').forEach(btn => {
        btn.addEventListener('click', async () => {
            const ok = await copyPlainText(btn.dataset.copyText || btn.textContent || '');
            showActionToast(ok ? '已复制' : '复制失败', ok ? 1200 : 1600, ok ? 'info' : 'error');
        });
    });
    $('settings-theme-select').addEventListener('change', (e) => { applyTheme(e.target.value); });
    const uiStyleSelect = $('settings-ui-style-select');
    if (uiStyleSelect) uiStyleSelect.addEventListener('change', (e) => { applyUiStyle(e.target.value); });
    $('settings-lang-select').addEventListener('change', (e) => { applyLang(e.target.value); });
    const englishNameToggle = $('settings-show-english-names');
    if (englishNameToggle) {
        englishNameToggle.checked = showEnglishCardNames;
        englishNameToggle.addEventListener('change', (e) => applyShowEnglishCardNames(e.target.checked));
    }
    const cardImagesToggle = $('settings-show-card-images');
    if (cardImagesToggle) {
        cardImagesToggle.checked = showCardImages;
        cardImagesToggle.addEventListener('change', (e) => applyShowCardImages(e.target.checked));
    }
    $('btn-lobby-back').addEventListener('click', () => {
        phase = 'login';
        manualDisconnect = true;
        if (socket) {
            try { socket.removeAllListeners(); } catch (_) {}
            socket.disconnect();
            socket = null;
            socketConnectUrl = '';
            window.gtnSocket = null;
        }
        showView('view-login');
        updateStatus(UI.default_status);
    });
    $('btn-surrender').addEventListener('click', onSurrender);
    $('btn-end-turn').addEventListener('click', onEndTurn);
    if ($('classic-end-turn')) $('classic-end-turn').addEventListener('click', onEndTurn);
    if ($('classic-settings')) $('classic-settings').addEventListener('click', () => openSettings({ hideServer: true }));
    document.addEventListener('mousemove', onClassicAimPointerMove);
    document.addEventListener('pointermove', onClassicAimPointerMove);
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') cancelClassicSelection(event);
    });
    document.addEventListener('contextmenu', (event) => {
        if (cancelClassicSelection(event)) return;
    });
    if ($('battle-classic')) {
        $('battle-classic').addEventListener('click', (event) => {
            if (classicCanAutoPlaySelfOnlyFromEvent(event)) {
                event.preventDefault();
                classicPlaySelectedCard();
            }
        });
    }
    ['classic-play-lane', 'classic-fighter-self', 'classic-fighter-enemy'].forEach(id => {
        const el = $(id);
        if (el) el.addEventListener('click', (event) => {
            if (shouldUseClassicBattle(gameState) && selectedPlayCardId != null && classicCanPlayFromElement(id)) {
                event.preventDefault();
                classicPlaySelectedCard();
            }
        });
    });
    if ($('classic-log-toggle')) {
        $('classic-log-toggle').addEventListener('click', () => {
            const drawer = $('classic-log-drawer');
            if (drawer) drawer.classList.toggle('is-open');
        });
    }
    const handleSoloPauseEdit = () => { if (socket || isLocalSoloRuntimeActive()) emitSoloEvent('solo_pause', {}); else showSoloTraining(); };
    $('btn-view-deck').addEventListener('click', onViewDeck);
    if ($('btn-spectate-view-deck')) $('btn-spectate-view-deck').addEventListener('click', onViewDeck);
    if ($('btn-switch-perspective')) {
        $('btn-switch-perspective').addEventListener('click', () => {
            if (replayMode) {
                switchAccountReplayPerspective();
                return;
            }
            if (socket && isSpectating) socket.emit('switch_spectate_perspective', {});
        });
    }
    if ($('classic-view-deck')) $('classic-view-deck').addEventListener('click', onViewDeck);
    if ($('classic-switch-perspective')) {
        $('classic-switch-perspective').addEventListener('click', () => {
            if (replayMode) {
                switchAccountReplayPerspective();
                return;
            }
            if (socket && isSpectating) socket.emit('switch_spectate_perspective', {});
        });
    }
    if ($('btn-urf-replace')) $('btn-urf-replace').addEventListener('click', onUrfReplaceCard);
    if ($('classic-urf-replace')) $('classic-urf-replace').addEventListener('click', onUrfReplaceCard);
    if ($('btn-urf-sell')) $('btn-urf-sell').addEventListener('click', onUrfSellEquipment);
    if ($('classic-urf-sell')) $('classic-urf-sell').addEventListener('click', onUrfSellEquipment);
    $('btn-solo-next-draw').addEventListener('click', onSoloNextDraw);
    if ($('classic-solo-next-draw')) $('classic-solo-next-draw').addEventListener('click', onSoloNextDraw);
    $('btn-solo-edit').addEventListener('click', handleSoloPauseEdit);
    if ($('classic-solo-edit')) $('classic-solo-edit').addEventListener('click', handleSoloPauseEdit);
    $('solo-card-search').addEventListener('input', renderSoloBuilder);
    $('btn-solo-clear-a').addEventListener('click', (e) => { e.stopPropagation(); clearSoloDeck('a'); });
    $('btn-solo-clear-b').addEventListener('click', (e) => { e.stopPropagation(); clearSoloDeck('b'); });
    $('solo-event-a').addEventListener('change', (e) => { soloEventA = e.target.value; });
    $('solo-event-b').addEventListener('change', (e) => { soloEventB = e.target.value; });
    $('btn-solo-load').addEventListener('click', () => { loadSoloDecks(true); renderSoloBuilder(); });
    $('btn-solo-save').addEventListener('click', saveSoloDecks);
    $('btn-solo-start').addEventListener('click', startSoloTraining);
    $('btn-solo-back').addEventListener('click', () => showView('view-login'));
    if ($('gallery-search')) $('gallery-search').addEventListener('input', renderCardGallery);
    if ($('gallery-tab-cards')) $('gallery-tab-cards').addEventListener('click', () => { setGalleryMode('cards'); gallerySelectedId = null; renderCardGallery(); });
    if ($('gallery-tab-tags')) $('gallery-tab-tags').addEventListener('click', () => { setGalleryMode('tags'); gallerySelectedId = null; renderCardGallery(); });
    if ($('gallery-tab-events')) $('gallery-tab-events').addEventListener('click', () => { setGalleryMode('events'); gallerySelectedId = null; renderCardGallery(); });
    if ($('gallery-tab-statuses')) $('gallery-tab-statuses').addEventListener('click', () => { setGalleryMode('statuses'); gallerySelectedId = null; renderCardGallery(); });
    if ($('btn-open-rules')) $('btn-open-rules').addEventListener('click', () => openAbout());
    if ($('btn-gallery-back')) $('btn-gallery-back').addEventListener('click', () => {
        if (galleryReturnToRules) {
            galleryReturnToRules = false;
            showView('view-login');
            openAbout();
        } else {
            showView('view-login');
        }
    });
    $('btn-return-lobby').addEventListener('click', () => {
        if (socket) socket.emit('return_lobby', {});
        showView('view-lobby');
        phase = 'lobby';
    });
    $('btn-leave-spectate').addEventListener('click', () => {
        if (replayMode) {
            closeAccountReplayModal();
            return;
        }
        if (socket) socket.emit('leave_spectate', {});
    });
    $('btn-lobby-chat-send').addEventListener('click', onLobbyChatSend);
    $('lobby-chat-input').addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && lobbyMentionMenu) lobbyMentionMenu.classList.add('hidden');
        if (e.key === 'Enter' && lobbyMentionMenu && !lobbyMentionMenu.classList.contains('hidden') && lobbyMentionCandidates[0]) {
            e.preventDefault();
            insertLobbyMention(lobbyMentionCandidates[0]);
            return;
        }
        if (e.key === 'Enter') onLobbyChatSend();
    });
    $('lobby-chat-input').addEventListener('input', updateLobbyMentionMenu);
    $('lobby-chat-input').addEventListener('focus', () => {
        clearLobbyMentionFlash();
        updateLobbyMentionMenu();
    });
    $('lobby-chat-input').addEventListener('blur', () => {
        setTimeout(() => { if (lobbyMentionMenu) lobbyMentionMenu.classList.add('hidden'); }, 120);
    });
    $('btn-game-chat-send').addEventListener('click', onGameChatSend);
    $('game-chat-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') onGameChatSend();
    });
    const phaseChatSend = $('btn-phase-chat-send');
    if (phaseChatSend) phaseChatSend.addEventListener('click', onPhaseChatSend);
    const phaseChatInput = $('phase-chat-input');
    if (phaseChatInput) phaseChatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') onPhaseChatSend();
    });
    setupPlayZoneDrop();
    bindMinimalPlayCancelZone();
    initModEditor();
    showView('view-login');
    setupFullscreenPrompt();
    bootLoader.done();
    document.getElementById('app').style.visibility = 'visible';
    if (!localStorage.getItem('gtn_seen_intro')) {
        setTimeout(() => openRulesModal({ firstVisit: true }), 250);
    }
}

document.addEventListener('DOMContentLoaded', init);
window.addEventListener('resize', () => {
    const gc = document.querySelector('.game-container');
    if (gc) gc.style.removeProperty('--card-w');
    scheduleAdjust();
    if (tutorialMode) setTimeout(updateTutorialOverlay, 80);
});
debugLog('[LOAD] game.js loaded, onEndTurn=', typeof onEndTurn);
