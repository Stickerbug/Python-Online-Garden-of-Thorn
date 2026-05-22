const I18N = {
    en: {
        round: 'Round', your_turn: 'Your Turn', opponent_turn: "Opponent's Turn", you: 'You', opponent: 'Opponent',
        draw_phase: 'Draw Phase', game_over: 'Game Over', invite: 'Invite', accept: 'Accept', decline: 'Decline',
        return_lobby: 'Return to Lobby', draft_phase: 'Draft Phase', draft_reroll: 'Reroll', draft_selected: 'Selected',
        select_event: 'Select Event', waiting_opponent: 'Waiting for opponent', play_card: 'Play', end_turn: 'End Turn',
        surrender: 'Surrender', view_deck: 'View Deck', counter: 'Counter', no_counter: 'Pass', waiting_response: 'Waiting for response',
        victory: 'Victory', defeat: 'Defeat', draw: 'Draw', rematch: 'Rematch', connecting: 'Connecting...', disconnected: 'Disconnected',
        login_failed: 'Login Failed', nickname: 'Nickname', enter_lobby: 'Enter Lobby', online_players: 'Online Players',
        no_other_players: 'No other players', invite_sent: 'Invite sent', invite_received: 'Invite received', invite_message: 'invites you to a match',
        invite_declined: 'Invite declined', ongoing_games: 'Ongoing Games', spectate: 'Spectate', draft_info: 'Draft', draft_complete: 'Draft Complete',
        draft_waiting: 'Waiting for opponent to finish drafting', draft_cost: 'Cost', select_this_event: 'Select This Event',
        event_selected: 'Event selected: {0}', event_waiting: 'Waiting for opponent to select an event', drag_to_play: 'Drag to Play',
        cannot_play: 'Cannot Play', enemy_attack: 'Enemy Attack', enemy_skill: 'Enemy Skill', enemy_destroy_equip: ', destroys equipment',
        use_card: 'Use', insufficient_resources: 'Insufficient resources', choose_attack_for: 'Choose an attack for {0}', choose_equip_for: 'Choose equipment',
        choose_discard_for: 'Choose a discard for {0}', choose_from_deck_for: 'Choose from deck', choose_from_discard_for: 'Choose from discard for {0}',
        choose_hand_for: 'Choose from hand for {0}', choose_from_enemy_hand_for: 'Choose from enemy hand', choose_attack_group_for: 'Choose attack group for {0}',
        no_attack_cards: 'No attack cards', no_enemy_equipment: 'No enemy equipment', no_enemy_hand: 'No enemy hand', deck_empty: 'Deck empty',
        discard_empty: 'Discard pile empty', no_same_attack: 'No matching attack cards', confirm_surrender: 'Surrender?', request_rematch: 'Request Rematch',
        opponent_rematch: 'Opponent requests rematch', rematch_sent: 'Rematch request sent', rematch_waiting: 'Waiting for opponent', rematch_agreed: 'Rematch accepted',
        agree_rematch: 'Accept Rematch', you_win: 'You Win!', you_lose: 'You Lose!', you_draw: 'Draw!', send: 'Send', cancel: 'Cancel', ok: 'OK', close: 'Close', notice: 'Notice',
        opponent_disconnected: 'Opponent disconnected', opponent_reconnected: 'Opponent reconnected', reconnect_title: 'Reconnect', reconnect_prompt: 'Reconnect to the previous match?',
        reconnecting: 'Reconnecting...', reconnect_timeout: 'Reconnect timed out', mod_mismatch_title: 'Mod Mismatch', mod_mismatch_msg: 'Mods do not match, cannot start the match',
        switch_perspective: 'Switch Perspective', leave_spectate: 'Leave Spectate', switch_to_perspective: 'Switch to {0}', battle_log: 'Battle Log',
        equip_info: '{0} ({1} turns)', equip_corruption: '[Corrupted]', equip_trigger_cost: '{0} Trigger: {1}E', status_poison: 'Poison', status_fire: 'Burn', status_toxic: 'Toxic',
        status_triangle: 'Triangle', status_dodge: 'Dodge', status_nazar: 'Nazar', status_equip_protect: 'Equip Protect', status_invincible: 'Invincible', status_stunned: 'Stunned',
        status_attack_blocked: 'Attack Blocked', status_attack_only: 'Attack Only', status_untargetable: 'Untargetable', status_bandage: 'Bandage', status_sponge: 'Sponge', status_shovel: 'Shovel',
        flag_precision: 'Precision', flag_exile: 'Exile', flag_non_stackable: 'Non-stack', flag_indestructible: 'Indestructible', flag_sprout: 'Sprout', flag_symbiosis: 'Symbiosis', flag_attract: 'Attract', flag_void: 'Void', flag_self_only: 'Self only', flag_uncancellable: 'Uncancellable',
        tag_precision: 'Precision', tag_exile: 'Exile', tag_non_stackable: 'Non-stack', tag_indestructible: 'Indestructible', tag_sprout: 'Sprout', tag_symbiosis: 'Symbiosis', tag_attract: 'Attract', tag_void: 'Void', tag_self_only: 'Self only', tag_uncancellable: 'Uncancellable',
        gallery_title: 'Compendium', gallery_cards: 'Cards', gallery_tags: 'Tags', gallery_events: 'Opening Events', gallery_search: 'Search', gallery_no_items: 'No entries.', gallery_cards_with_tag: 'Cards with this tag', gallery_card_count: '{0} cards',
        gallery_type: 'Type', gallery_cost: 'Cost', gallery_tags_label: 'Tags', gallery_description: 'Description', gallery_effect: 'Effect', gallery_trigger: 'Trigger',
        choose_convert_count: 'Choose convert count', choose_magic_card_n: 'Choose magic card #{0}', choose_source_card_n: 'Choose source card #{0}', choose_light_cards: 'Choose Light cards', choose_yggdrasil_card: 'Choose Yggdrasil card',
        convert_label: 'Convert', convert_per_type: 'Max {0} per type', selected_count: 'Selected {0}/{1}', max_selection_warning: 'Cannot exceed {0}', deck_total: 'Deck: {0} cards', view_deck_title: 'View Deck',
        hand_deck_info_opp: 'Hand: {0} Deck: {1}', hand_deck_discard_info: 'Hand: {0} Deck: {1} Discard: {2}', round_status: 'Round {0} - {1}', server_broadcast: 'Server: {0}', error_msg: 'Error: {0}',
        lobby_status: 'Lobby - {0}', no_counter_countdown: 'No Counter ({0})', select_event_desc: 'Select an opening event', opponent_selected: 'Opponent selected', opponent_selecting: 'Opponent selecting...',
        card_type_thorn: 'Thorn', card_type_bloom: 'Bloom', card_type_root: 'Root', card_type_guard: 'Guard', fusion_layer: 'Fusion', fission_layer: 'Fission',
        settings_title: 'Settings', settings_appearance: 'Appearance', settings_theme: 'Theme', settings_lang: 'Language', settings_mods: 'Mods', settings_theme_light: 'Light', settings_theme_dark: 'Dark',
        no_games: 'No ongoing games', back_to_home: 'Back to Home', settings_btn: 'Settings', settings_server: 'Server', settings_server_addr: 'Address', not_your_turn: 'Not your turn',
        counter_insufficient: 'Tip: counter cards are not affordable', default_status: 'Garden of Thorn', game_loading: 'Loading...', server_no_response: 'Server is not responding. Check the connection or refresh.',
        spectator_prefix: 'Spectate', lobby_title: 'Lobby', online_count: 'Online: {0}', chat_title: 'Chat', solo_training: 'Solo Training', load_last: 'Load Last', save_decks: 'Save Decks', start_training: 'Start Training',
        solo_deck_a: 'Your Deck', solo_deck_b: 'Opponent Deck', search_cards: 'Search cards', pause_edit: 'Pause & Edit', set_next_draw: 'Set Next Draw', solo_saved: 'Training decks saved',
        solo_need_15: 'Both decks must contain exactly 15 cards', solo_event_a: 'Your opening event', solo_event_b: 'Opponent opening event', no_event: 'None', edit_tags: 'Edit Tags',
        login_need_nickname: 'Please enter a nickname', login_name_too_long: 'Nickname too long (max 8 CJK or 16 Latin chars)', login_name_not_numbers: 'Nickname cannot be only numbers',
        login_name_not_symbols: 'Nickname cannot be only symbols', login_name_no_repeat_symbols: '- and _ cannot appear consecutively',
        operation_failed: 'Operation failed', server_not_connected: 'Not connected to server', no_mod_files: 'No mod files found', load_success: 'Loaded', load_failed: 'Load failed', save_success: 'Saved', save_failed: 'Save failed: {0}',
        json_valid: 'Valid JSON', json_invalid: 'Invalid JSON: {0}', init_scripts: 'Initializing scripts...', init_theme_lang: 'Applying theme and language...', init_fonts: 'Loading fonts...', init_fonts_done: 'Fonts loaded',
        init_bindings: 'Binding UI events...', init_done: 'Loaded', next_draw_count: 'Set Next Draw (count)', next_draw_pick: 'Set Next Draw ({0}/{1})',
        login_invalid_nickname: 'Invalid nickname. Use 1-16 display-width characters; avoid pure numbers, pure symbols, or repeated -/_.', login_nickname_exists: 'Nickname already exists',
        training_start: 'Solo training starts. {0} goes first.', training_set_draw: 'Training: {0} sets next draw to {1}',
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
        mode_switch_confirm: 'Switching mode will leave your current team. Continue?',
        waiting_for_team: 'Waiting for another team...',
        all_players_draft_status: 'Draft Status',
        urf_replace: 'Replace Card', urf_sell: 'Sell Equipment'
    }
};
I18N.zh = { ...I18N.en,
    round: '回合', your_turn: '你的回合', opponent_turn: '对方回合', you: '你', opponent: '对手',
    draw_phase: '抽牌阶段', game_over: '游戏结束', invite: '邀请', accept: '接受', decline: '拒绝', return_lobby: '返回大厅',
    draft_phase: '选牌阶段', draft_reroll: '重抽', draft_selected: '已选择', select_event: '选择开局事件', waiting_opponent: '等待对方',
    play_card: '打出', end_turn: '结束回合', surrender: '投降', view_deck: '查看牌堆', counter: '反制', no_counter: '不反制', waiting_response: '等待响应',
    victory: '胜利', defeat: '失败', draw: '平局', rematch: '再来一局', connecting: '连接中...', disconnected: '已断开连接',
    login_failed: '登录失败', nickname: '昵称', enter_lobby: '进入大厅', online_players: '在线玩家', no_other_players: '暂无其他玩家',
    invite_sent: '邀请已发送', invite_received: '收到邀请', invite_message: '邀请你进行对战', invite_declined: '邀请被拒绝',
    ongoing_games: '进行中的对局', spectate: '观战', draft_info: '选牌', draft_complete: '选牌完成', draft_waiting: '等待对方完成选牌',
    draft_cost: '费用', select_this_event: '选择此事件', event_selected: '已选择事件：{0}', event_waiting: '等待对方选择事件',
    drag_to_play: '拖动打出', cannot_play: '无法打出', enemy_attack: '敌方攻击', enemy_skill: '敌方技能', enemy_destroy_equip: '，摧毁装备',
    use_card: '使用', insufficient_resources: '资源不足', choose_attack_for: '为 {0} 选择攻击牌', choose_equip_for: '选择装备牌',
    choose_discard_for: '为 {0} 选择弃牌', choose_from_deck_for: '从牌堆选择', choose_from_discard_for: '为 {0} 从弃牌堆选择', choose_hand_for: '为 {0} 从手牌选择',
    choose_from_enemy_hand_for: '从敌方手牌选择', choose_attack_group_for: '为 {0} 选择攻击组', no_attack_cards: '没有攻击牌', no_enemy_equipment: '对方没有装备',
    no_enemy_hand: '对方没有手牌', deck_empty: '牌堆为空', discard_empty: '弃牌堆为空', no_same_attack: '没有同名攻击牌',
    confirm_surrender: '确认投降？', request_rematch: '请求再来一局', opponent_rematch: '对方请求再来一局', rematch_sent: '已发送再来一局请求',
    rematch_waiting: '等待对方', rematch_agreed: '对方已接受', agree_rematch: '接受再来一局', you_win: '你赢了！', you_lose: '你输了！', you_draw: '平局！',
    send: '发送', cancel: '取消', ok: '确定', close: '关闭', notice: '提示', opponent_disconnected: '对手已断开连接', opponent_reconnected: '对手已重新连接',
    reconnect_title: '重连', reconnect_prompt: '是否重连到上一局对战？', reconnecting: '重连中...', reconnect_timeout: '重连超时',
    mod_mismatch_title: '模组不匹配', mod_mismatch_msg: '模组不一致，无法开始对局', switch_perspective: '切换视角', leave_spectate: '退出观战', switch_to_perspective: '切换到 {0}',
    battle_log: '战斗日志', equip_info: '{0}（{1}回合）', equip_corruption: '[已腐化]', equip_trigger_cost: '{0} 触发：{1}E',
    status_poison: '中毒', status_fire: '灼烧', status_toxic: '淬毒', status_triangle: '三角形', status_dodge: '闪避', status_nazar: '邪眼',
    status_equip_protect: '装备保护', status_invincible: '无敌', status_stunned: '眩晕', status_attack_blocked: '禁攻', status_attack_only: '仅攻击',
    status_untargetable: '不可选中', status_bandage: '绷带', status_sponge: '海绵', status_shovel: '铲子',
    flag_precision: '精准', flag_exile: '放逐', flag_non_stackable: '不可叠加', flag_indestructible: '不可摧毁', flag_sprout: '萌芽', flag_symbiosis: '共生', flag_attract: '吸引', flag_void: '虚无', flag_self_only: '仅自己可用', flag_uncancellable: '不可取消',
    choose_convert_count: '选择转化数量', choose_magic_card_n: '选择第 {0} 张魔法牌', choose_source_card_n: '选择第 {0} 张源牌', choose_light_cards: '选择 Light 牌', choose_yggdrasil_card: '选择 Yggdrasil 牌',
    convert_label: '转化', convert_per_type: '每种最多 {0} 张', selected_count: '已选择 {0}/{1}', max_selection_warning: '不能超过 {0}',
    deck_total: '牌堆：{0} 张', view_deck_title: '查看牌堆', hand_deck_info_opp: '手牌：{0} 牌堆：{1}', hand_deck_discard_info: '手牌：{0} 牌堆：{1} 弃牌：{2}',
    round_status: '第 {0} 回合 - {1}', server_broadcast: '系统：{0}', error_msg: '错误：{0}', lobby_status: '大厅 - {0}', no_counter_countdown: '不反制（{0}）',
    select_event_desc: '选择一个开局事件', opponent_selected: '对方已选择', opponent_selecting: '对方选择中...',
    settings_title: '设置', settings_appearance: '外观', settings_theme: '主题', settings_lang: '语言', settings_mods: '模组', settings_theme_light: '明亮', settings_theme_dark: '黑暗',
    no_games: '暂无进行中的对局', back_to_home: '返回主页', settings_btn: '设置', settings_server: '服务器', settings_server_addr: '地址', not_your_turn: '还没轮到你',
    counter_insufficient: '提示：当前没有可支付的反制牌', default_status: 'Garden of Thorn', game_loading: '加载中...', server_no_response: '服务器没有响应，请检查连接或刷新页面。',
    spectator_prefix: '观战', lobby_title: '大厅', online_count: '在线：{0}', chat_title: '聊天',
    solo_training: '单人训练场', load_last: '载入上次', save_decks: '保存牌组', start_training: '开始训练', solo_deck_a: '你的牌组', solo_deck_b: '对方牌组',
    search_cards: '搜索卡牌', pause_edit: '暂停并编辑', set_next_draw: '设置下次抽牌', solo_saved: '训练牌组已保存', solo_need_15: '双方牌组都必须正好为 15 张',
    solo_event_a: '你的开局事件', solo_event_b: '对方开局事件', no_event: '无', edit_tags: '编辑标签',
    login_need_nickname: '请输入昵称', login_name_too_long: '昵称过长（最多 8 个中文或 16 个拉丁字符）', login_name_not_numbers: '昵称不能全为数字', login_name_not_symbols: '昵称不能全为符号', login_name_no_repeat_symbols: '- 和 _ 不能连续出现',
    operation_failed: '操作失败', server_not_connected: '未连接到服务器', no_mod_files: '未找到模组文件', load_success: '加载成功', load_failed: '加载失败', save_success: '保存成功', save_failed: '保存失败：{0}',
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
    tag_precision: '精准', tag_exile: '放逐', tag_non_stackable: '不可叠加', tag_indestructible: '不可摧毁', tag_sprout: '萌芽', tag_symbiosis: '共生', tag_attract: '吸引', tag_void: '虚无', tag_self_only: '仅自己可用', tag_uncancellable: '不可取消',
    gallery_title: '图鉴', gallery_cards: '卡牌', gallery_tags: '标签', gallery_events: '开局事件', gallery_search: '搜索', gallery_no_items: '暂无条目。', gallery_cards_with_tag: '拥有此标签的卡牌', gallery_card_count: '{0} 张卡牌',
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
    mode_switch_confirm: '切换模式将离开当前队伍，是否确认？',
    waiting_for_team: '等待另一支队伍...',
    all_players_draft_status: '选牌状态',
    urf_replace: '替换手牌', urf_sell: '售卖装备',
    fusion_layer: '聚变', fission_layer: '裂变',
    app_subtitle: '局域网联机卡牌对战',
    nickname_placeholder: '输入昵称',
    message_placeholder: '输入消息...',
    server_placeholder: '留空使用默认服务器',
    server_hint: '默认服务器：{0}（留空则使用默认服务器）',
    init_cards_mods: '加载卡牌与模组（/api/cards）...',
    init_opening_events: '加载开局事件（/api/opening-events）...',
    mod_editor: '模组编辑器',
    mod_editor_placeholder: '在此粘贴或编辑模组 JSON...',
    load_mod: '加载模组',
    save: '保存',
    validate_json: '验证 JSON',
    rotate_prompt: '请横屏游玩',
    continue_enter: '继续进入',
    mod_default_name: '模组 {0}'
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
    agree_rematch: 'Accepter la revanche', you_win: 'Victoire !', you_lose: 'Défaite !', you_draw: 'Égalité !',
    send: 'Envoyer', cancel: 'Annuler', ok: 'OK', close: 'Fermer', notice: 'Notice',
    opponent_disconnected: 'Adversaire déconnecté', opponent_reconnected: 'Adversaire reconnecté',
    reconnect_title: 'Reconnexion', reconnect_prompt: 'Se reconnecter à la partie précédente ?', reconnecting: 'Reconnexion...', reconnect_timeout: 'Délai de reconnexion écoulé',
    mod_mismatch_title: 'Mods incompatibles', mod_mismatch_msg: 'Les mods ne correspondent pas, impossible de commencer',
    switch_perspective: 'Changer de perspective', leave_spectate: "Quitter l'observation", switch_to_perspective: 'Passer à la perspective de {0}',
    battle_log: 'Journal de combat', equip_info: '{0}({1} tours)', equip_corruption: '[Corrompu]', equip_trigger_cost: '{0} Déclencher:{1}E',
    status_poison: 'Poison', status_fire: 'Brûlure', status_toxic: 'Toxique', status_triangle: 'Triangle', status_dodge: 'Esquive',
    status_nazar: 'Nazar', status_equip_protect: 'Prot. Équip.', status_invincible: 'Invincible', status_stunned: 'Étourdi', status_attack_blocked: 'Atq bloquée', status_attack_only: 'Atq seule',
    status_untargetable: 'Non ciblable', status_bandage: 'Bandage', status_sponge: 'Éponge', status_shovel: 'Pelle',
    flag_precision: 'Précision', flag_exile: 'Exil', flag_non_stackable: 'Non-cumul', flag_indestructible: 'Indestructible', flag_sprout: 'Pousse', flag_symbiosis: 'Symbiose',
    choose_convert_count: 'Nombre de conversions', choose_magic_card_n: 'Carte magie n°{0}', choose_source_card_n: 'Carte source n°{0}',
    choose_light_cards: 'Cartes de conversion Lumière', choose_yggdrasil_card: 'Carte de conversion Yggdrasil', convert_label: 'Convertir', convert_per_type: 'Max {0} par type',
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
    solo_training: 'Entraînement solo', load_last: 'Charger', save_decks: 'Sauver decks', start_training: 'Commencer',
    solo_deck_a: 'Votre deck', solo_deck_b: 'Deck adverse', search_cards: 'Chercher cartes', pause_edit: 'Pause édition',
    set_next_draw: 'Fixer prochaine pioche', solo_saved: 'Decks sauvegardés', solo_need_15: 'Les deux decks doivent avoir exactement 15 cartes',
    solo_event_a: 'Événement de départ', solo_event_b: 'Événement adverse', no_event: 'Aucun',
    edit_tags: 'Modifier tags', tag_precision: 'Précision', tag_exile: 'Exil', tag_non_stackable: 'Non-cumul',
    tag_indestructible: 'Indestructible', tag_sprout: 'Pousse', tag_symbiosis: 'Symbiose', tag_attract: 'Attraction', tag_void: 'Vide', tag_self_only: 'Soi uniquement', tag_uncancellable: 'Non annulable',
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
    agree_rematch: 'Aceitar revanche', you_win: 'Vitória!', you_lose: 'Derrota!', you_draw: 'Empate!',
    send: 'Enviar', cancel: 'Cancelar', ok: 'OK', close: 'Fechar', notice: 'Aviso',
    opponent_disconnected: 'Oponente desconectou', opponent_reconnected: 'Oponente reconectou',
    reconnect_title: 'Reconectar', reconnect_prompt: 'Reconectar à partida anterior?', reconnecting: 'Reconectando...', reconnect_timeout: 'Tempo de reconexão esgotado',
    mod_mismatch_title: 'Mods incompatíveis', mod_mismatch_msg: 'Mods inconsistentes, não é possível iniciar a partida',
    switch_perspective: 'Trocar Perspectiva', leave_spectate: 'Sair da Observação', switch_to_perspective: 'Trocar para perspectiva de {0}',
    battle_log: 'Registro de Batalha', equip_info: '{0}({1} turnos)', equip_corruption: '[Corrompido]', equip_trigger_cost: '{0} Ativar:{1}E',
    status_poison: 'Veneno', status_fire: 'Queima', status_toxic: 'Tóxico', status_triangle: 'Triângulo', status_dodge: 'Esquiva',
    status_nazar: 'Nazar', status_equip_protect: 'Prot. Equip.', status_invincible: 'Invencível', status_stunned: 'Atordoado', status_attack_blocked: 'Atq Bloqueado', status_attack_only: 'Só Atq',
    status_untargetable: 'Inalvejável', status_bandage: 'Bandagem', status_sponge: 'Esponja', status_shovel: 'Pá',
    flag_precision: 'Precisão', flag_exile: 'Exílio', flag_non_stackable: 'Não-acumulável', flag_indestructible: 'Indestrutível', flag_sprout: 'Brotar', flag_symbiosis: 'Simbiose',
    choose_convert_count: 'Escolher quantidade de conversão', choose_magic_card_n: 'Carta mágica n°{0}', choose_source_card_n: 'Carta fonte n°{0}',
    choose_light_cards: 'Cartas de conversão Luz', choose_yggdrasil_card: 'Carta de conversão Yggdrasil', convert_label: 'Converter', convert_per_type: 'Máx {0} por tipo',
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
    solo_training: 'Treino Solo', load_last: 'Carregar Último', save_decks: 'Salvar Decks', start_training: 'Iniciar Treino',
    solo_deck_a: 'Seu Deck', solo_deck_b: 'Deck Oponente', search_cards: 'Buscar cartas', pause_edit: 'Pausar e Editar',
    set_next_draw: 'Definir Próxima Compra', solo_saved: 'Decks salvos', solo_need_15: 'Ambos os decks devem ter exatamente 15 cartas',
    solo_event_a: 'Evento inicial', solo_event_b: 'Evento do oponente', no_event: 'Nenhum',
    edit_tags: 'Editar tags', tag_precision: 'Precisão', tag_exile: 'Exílio', tag_non_stackable: 'Não acumula',
    tag_indestructible: 'Indestrutível', tag_sprout: 'Broto', tag_symbiosis: 'Simbiose', tag_attract: 'Atrair', tag_void: 'Vazio', tag_self_only: 'Somente si', tag_uncancellable: 'Não cancelável',
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
I18N.ru = { ...I18N.en,
    round: 'Раунд', your_turn: 'Ваш Ход', opponent_turn: 'Ход Соперника', you: 'Вы', opponent: 'Соперник',
    draw_phase: 'Фаза Розыгрыша', game_over: 'Конец Игры', invite: 'Пригласить', accept: 'Принять', decline: 'Отклонить', return_lobby: 'Вернуться в Лобби',
    draft_phase: 'Фаза Драфта', draft_reroll: 'Перебрать', draft_selected: 'Выбрано', select_event: 'Выбрать Событие', waiting_opponent: 'Ожидание соперника',
    play_card: 'Разыграть', end_turn: 'Конец Хода', surrender: 'Сдаться', view_deck: 'Посмотреть Колоду', counter: 'Контр-атака', no_counter: 'Без Контр-атаки', waiting_response: 'Ожидание ответа',
    victory: 'Победа', defeat: 'Поражение', draw: 'Ничья', rematch: 'Реванш', connecting: 'Подключение...', disconnected: 'Отключено',
    login_failed: 'Ошибка входа', nickname: 'Псевдоним', enter_lobby: 'Войти в Лобби', online_players: 'Игроки Онлайн', no_other_players: 'Нет других игроков',
    invite_sent: 'Приглашение отправлено', invite_received: 'Приглашение получено', invite_message: 'приглашает вас на матч', invite_declined: 'Приглашение отклонено',
    ongoing_games: 'Текущие Матчи', spectate: 'Наблюдать', draft_info: 'Драфт', draft_complete: 'Драфт Завершён', draft_waiting: 'Ожидание завершения драфта соперника',
    draft_cost: 'Стоимость', select_this_event: 'Выбрать Это Событие', event_selected: 'Событие Выбрано', event_waiting: 'Ожидание выбора события соперником',
    drag_to_play: 'Перетащите для игры', cannot_play: 'Нельзя Играть',
    enemy_attack: 'Атака Врага', enemy_skill: 'Способность Врага', enemy_destroy_equip: 'Уничтожение Снаряжения Врага',
    use_card: 'Использовать', insufficient_resources: 'Недостаточно ресурсов', choose_attack_for: 'Выбрать атаку для', choose_equip_for: 'Выбрать снаряжение',
    choose_discard_for: 'Выбрать сброс', choose_from_deck_for: 'Выбрать из колоды', choose_from_discard_for: 'Выбрать из сброса', choose_hand_for: 'Выбрать из руки',
    choose_from_enemy_hand_for: 'Выбрать из руки врага', choose_attack_group_for: 'Выбрать группу атаки',
    no_attack_cards: 'Нет карт атаки', no_enemy_equipment: 'Нет снаряжения врага', no_enemy_hand: 'Нет руки врага', deck_empty: 'Колода пуста', discard_empty: 'Сброс пуст',
    no_same_attack: 'Нет одинаковых карт атаки', confirm_surrender: 'Подтвердить сдачу?', request_rematch: 'Запросить реванш',
    opponent_rematch: 'Соперник запрашивает реванш', rematch_sent: 'Запрос реванша отправлен', rematch_waiting: 'Ожидание соперника', rematch_agreed: 'Реванш принят',
    agree_rematch: 'Принять реванш', you_win: 'Победа!', you_lose: 'Поражение!', you_draw: 'Ничья!',
    send: 'Отправить', cancel: 'Отмена', ok: 'ОК', close: 'Закрыть', notice: 'Уведомление',
    opponent_disconnected: 'Соперник отключился', opponent_reconnected: 'Соперник переподключился',
    reconnect_title: 'Переподключение', reconnect_prompt: 'Переподключиться к предыдущему матчу?', reconnecting: 'Переподключение...', reconnect_timeout: 'Тайм-аут переподключения',
    mod_mismatch_title: 'Несовместимость модов', mod_mismatch_msg: 'Моды не совпадают, невозможно начать матч',
    switch_perspective: 'Сменить Перспективу', leave_spectate: 'Покинуть Наблюдение', switch_to_perspective: 'Переключиться на перспективу {0}',
    battle_log: 'Журнал Боя', equip_info: '{0}({1} ходов)', equip_corruption: '[Осквернено]', equip_trigger_cost: '{0} Активировать:{1}E',
    status_poison: 'Яд', status_fire: 'Горение', status_toxic: 'Токсичность', status_triangle: 'Треугольник', status_dodge: 'Уклонение',
    status_nazar: 'Назар', status_equip_protect: 'Защита Снар.', status_invincible: 'Неуязвимость', status_stunned: 'Оглушение', status_attack_blocked: 'Атк Заблок.', status_attack_only: 'Только Атк',
    status_untargetable: 'Недоступен', status_bandage: 'Бинт', status_sponge: 'Губка', status_shovel: 'Лопата',
    flag_precision: 'Точность', flag_exile: 'Изгнание', flag_non_stackable: 'Нескладываемый', flag_indestructible: 'Неразрушимый', flag_sprout: 'Росток', flag_symbiosis: 'Симбиоз',
    choose_convert_count: 'Количество конвертации', choose_magic_card_n: 'Магическая карта №{0}', choose_source_card_n: 'Исходная карта №{0}',
    choose_light_cards: 'Карты конвертации Света', choose_yggdrasil_card: 'Карта конвертации Иггдрасиль', convert_label: 'Конвертировать', convert_per_type: 'Макс {0} на тип',
    selected_count: 'Выбрано {0}/{1}', max_selection_warning: 'Нельзя превышать {0}', deck_total: 'Колода: {0} карт', view_deck_title: 'Посмотреть Колоду',
    hand_deck_info_opp: 'Рука:{0} Колода:{1}', hand_deck_discard_info: 'Рука:{0} Колода:{1} Сброс:{2}', round_status: 'Раунд {0} - {1}',
    server_broadcast: 'Сервер: {0}', error_msg: 'Ошибка: {0}', lobby_status: 'Лобби - {0}', no_counter_countdown: 'Без контр-атаки({0})',
    select_event_desc: 'Выберите начальное событие', opponent_selected: 'Соперник выбрал', opponent_selecting: 'Соперник выбирает...',
    card_type_thorn: 'Thorn', card_type_bloom: 'Bloom', card_type_root: 'Root', card_type_guard: 'Guard',
    settings_title: 'Настройки', settings_appearance: 'Внешний вид', settings_theme: 'Тема', settings_lang: 'Язык', settings_mods: 'Моды', settings_theme_light: 'Светлая', settings_theme_dark: 'Тёмная',
    no_games: 'Нет текущих матчей', back_to_home: 'Вернуться на главную', settings_btn: 'Настройки', settings_server: 'Сервер', settings_server_addr: 'Адрес',
    not_your_turn: 'Не ваш ход', counter_insufficient: 'Подсказка: Недостаточно ресурсов для контр-атаки', default_status: 'Garden of Thorn',
    game_loading: 'Загрузка...', server_no_response: 'Сервер не отвечает. Проверьте подключение.',
    spectator_prefix: 'Наблюдатель', lobby_title: 'Лобби', online_count: 'Онлайн: {0}', chat_title: 'Чат',
    solo_training: 'Одиночная тренировка', load_last: 'Загрузить', save_decks: 'Сохранить колоды', start_training: 'Начать',
    solo_deck_a: 'Ваша колода', solo_deck_b: 'Колода соперника', search_cards: 'Поиск карт', pause_edit: 'Пауза и правка',
    set_next_draw: 'Задать следующую карту', solo_saved: 'Колоды сохранены', solo_need_15: 'В обеих колодах должно быть ровно 15 карт',
    solo_event_a: 'Ваше стартовое событие', solo_event_b: 'Событие соперника', no_event: 'Нет',
    edit_tags: 'Изменить теги', tag_precision: 'Точность', tag_exile: 'Изгнание', tag_non_stackable: 'Не складывается',
    tag_indestructible: 'Неразрушимый', tag_sprout: 'Росток', tag_symbiosis: 'Симбиоз', tag_attract: 'Притяжение', tag_void: 'Пустота', tag_self_only: 'Только на себя', tag_uncancellable: 'Нельзя отменить',
    fusion_layer: 'Слияние', fission_layer: 'Деление',
    app_subtitle: 'Карточная дуэль по локальной сети',
    nickname_placeholder: 'Введите никнейм',
    message_placeholder: 'Введите сообщение...',
    hand_deck_zero_opp: 'Рука:0 Колода:0',
    hand_deck_zero_you: 'Рука:0 Колода:0 Сброс:0',
    rotate_hint_sub: 'Поверните экран в альбомный режим',
    server_placeholder: 'Оставьте пустым для сервера по умолчанию',
    server_hint: 'Сервер по умолчанию: {0} (оставьте пустым, чтобы использовать его)',
    init_cards_mods: 'Загрузка карт и модов (/api/cards)...',
    init_opening_events: 'Загрузка начальных событий (/api/opening-events)...',
    mod_editor: 'Редактор модов',
    mod_editor_placeholder: 'Вставьте или измените JSON мода здесь...',
    load_mod: 'Загрузить мод',
    save: 'Сохранить',
    validate_json: 'Проверить JSON',
    rotate_prompt: 'Играйте в альбомной ориентации',
    continue_enter: 'Продолжить',
    mod_default_name: 'Мод {0}'
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
    agree_rematch: '再戦に同意', you_win: '勝利！', you_lose: '敗北！', you_draw: '引き分け！',
    send: '送信', cancel: 'キャンセル', ok: 'OK', close: '閉じる', notice: 'お知らせ',
    opponent_disconnected: '相手が切断しました', opponent_reconnected: '相手が再接続しました',
    reconnect_title: '再接続', reconnect_prompt: '前の対戦に再接続しますか？', reconnecting: '再接続中...', reconnect_timeout: '再接続タイムアウト',
    mod_mismatch_title: 'Mod不一致', mod_mismatch_msg: 'Modが一致しません。対戦を開始できません',
    switch_perspective: '視点切替', leave_spectate: '観戦終了', switch_to_perspective: '{0}の視点に切替',
    battle_log: 'バトルログ', equip_info: '{0}({1}ターン)', equip_corruption: '[腐敗]', equip_trigger_cost: '{0} 発動:{1}E',
    status_poison: '毒', status_fire: '火傷', status_toxic: '猛毒', status_triangle: '三角形', status_dodge: '回避',
    status_nazar: 'ナザール', status_equip_protect: '装備保護', status_invincible: '無敵', status_stunned: 'スタン', status_attack_blocked: '攻撃封印', status_attack_only: '攻撃のみ',
    status_untargetable: '対象不可', status_bandage: '包帯', status_sponge: 'スポンジ', status_shovel: 'シャベル',
    flag_precision: '精密', flag_exile: '追放', flag_non_stackable: '非スタック', flag_indestructible: '破壊不可', flag_sprout: '発芽', flag_symbiosis: '共生',
    choose_convert_count: '変換回数を選択', choose_magic_card_n: 'マジックカード第{0}枚', choose_source_card_n: 'ソースカード第{0}枚',
    choose_light_cards: '光変換カードを選択', choose_yggdrasil_card: 'ユグドラシル変換カードを選択', convert_label: '変換', convert_per_type: 'タイプごとに最大{0}枚',
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
    solo_training: 'ソロ練習場', load_last: '前回を読み込む', save_decks: 'デッキ保存', start_training: '開始',
    solo_deck_a: '自分のデッキ', solo_deck_b: '相手デッキ', search_cards: 'カード検索', pause_edit: '中断して編集',
    set_next_draw: '次のドロー設定', solo_saved: '練習デッキを保存しました', solo_need_15: '両方のデッキは15枚ちょうど必要です',
    solo_event_a: '自分の開局イベント', solo_event_b: '相手の開局イベント', no_event: 'なし',
    edit_tags: 'タグ編集', tag_precision: '精密', tag_exile: '追放', tag_non_stackable: '非重複',
    tag_indestructible: '破壊不可', tag_sprout: '萌芽', tag_symbiosis: '共生', tag_attract: '誘引', tag_void: '虚無', tag_self_only: '自分専用', tag_uncancellable: 'キャンセル不可',
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
let currentLang = localStorage.getItem('got_lang') || 'zh';
function t(key) { return (I18N[currentLang] && I18N[currentLang][key]) || (I18N.zh[key]) || key; }
function tf(key, ...values) { return t(key).replace(/\{(\d+)\}/g, (_, i) => values[Number(i)] ?? ''); }
const UI = new Proxy({}, { get: (_, key) => t(key) });

const COLORS = {
    elixir: '#F1C40F', elixir_text: '#9A7D0A', elixir_bg: '#FEF9E7',
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
};

function getCardName(cardDef) {
    if (!cardDef) return '?';
    return getLocalizedCardText(cardDef, 'name_i18n', currentLang === 'zh' ? 'name_cn' : 'name_en');
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
LOG_TEXT.ru = {
    game_start: 'Начало игры. {p} ходит первым.', round: 'Раунд {n}', draw_cards: '{p} берет карт: {n}', recover_e: '{p} восстанавливает {n}E',
    take_damage: '{p} получает {n} {source} урона (H={h})', use_deal: '{p} использует {card}: наносит {n} урона',
    use_multi: '{p} использует {card}: наносит {n} x {times} урона', use_simple: '{p} использует {card}', equip: '{p} экипирует {card}',
    exile: '{card} изгнана', counter: '{p} контратакует картой {card}', win: '{loser} падает до 0H. {winner} побеждает.',
    draw: 'Оба игрока достигли 0H. Ничья.', surrender: '{p} сдается. {winner} побеждает.', poison: 'яд', burn: 'ожог', physical: 'физический'
};
LOG_TEXT.ja = {
    game_start: 'ゲーム開始。{p}が先攻。', round: 'ラウンド {n}', draw_cards: '{p}が{n}枚ドロー', recover_e: '{p}が{n}E回復',
    take_damage: '{p}が{n}{source}ダメージを受ける（H={h}）', use_deal: '{p}が{card}を使用：{n}ダメージ',
    use_multi: '{p}が{card}を使用：{n} x {times}ダメージ', use_simple: '{p}が{card}を使用', equip: '{p}が{card}を装備',
    exile: '{card}は追放された', counter: '{p}が{card}でカウンター', win: '{loser}のHが0。{winner}の勝利。',
    draw: '双方のHが0。引き分け。', surrender: '{p}が降参。{winner}の勝利。', poison: '毒', burn: '火傷', physical: '物理'
};

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

function localizeDamageSource(source) {
    const table = LOG_TEXT[currentLang] || LOG_TEXT.en;
    return String(source || '')
        .replaceAll('\u4e2d\u6bd2', table.poison)
        .replaceAll('\u707c\u70e7', table.burn)
        .replaceAll('\u7269\u7406', table.physical);
}

function translateLogLine(line) {
    if (currentLang === 'zh') return line;
    let m;
    if ((m = line.match(/^\u6e38\u620f\u5f00\u59cb\uff01(.+)\u5148\u624b\u3002?$/))) return fmtLog('game_start', { p: m[1] });
    if ((m = line.match(/^=== \u7b2c(\d+)\u56de\u5408 ===$/))) return fmtLog('round', { n: m[1] });
    if (line === '\u53cc\u65b9\u751f\u547d\u503c\u540c\u65f6\u5f52\u96f6\uff01\u5e73\u5c40\uff01') return fmtLog('draw');
    if ((m = line.match(/^(.+)\u751f\u547d\u503c\u5f52\u96f6\uff01(.+)\u83b7\u80dc\uff01$/))) return fmtLog('win', { loser: m[1], winner: m[2] });
    if ((m = line.match(/^(.+)\u6295\u964d\uff0c(.+)\u83b7\u80dc\uff01$/))) return fmtLog('surrender', { p: m[1], winner: m[2] });
    if ((m = line.match(/^(.+)\u62bd(\d+)\u5f20\u724c$/))) return fmtLog('draw_cards', { p: m[1], n: m[2] });
    if ((m = line.match(/^(.+)\u56de\u590d(\d+)E$/))) return fmtLog('recover_e', { p: m[1], n: m[2] });
    if ((m = line.match(/^(.+)\u53d7\u5230(\d+)\u70b9(.+)\u4f24\u5bb3\uff08H=(-?\d+)\uff09$/))) return fmtLog('take_damage', { p: m[1], n: m[2], source: localizeDamageSource(m[3]), h: m[4] });
    if ((m = line.match(/^(.+)\u53d7\u5230(\d+)\u70b9\u4f24\u5bb3\uff08H=(-?\d+)\uff09$/))) return fmtLog('take_damage', { p: m[1], n: m[2], source: '', h: m[3] });
    if ((m = line.match(/^(.+)\u4f7f\u7528(.+)\uff01\u9020\u6210(\d+)\u4f24\u5bb3$/))) return fmtLog('use_deal', { p: m[1], card: localizedCardNameFromAny(m[2]), n: m[3] });
    if ((m = line.match(/^(.+)\u4f7f\u7528(.+)\uff01\u9020\u6210(\d+)x(\d+)\u4f24\u5bb3$/))) return fmtLog('use_multi', { p: m[1], card: localizedCardNameFromAny(m[2]), n: m[3], times: m[4] });
    if ((m = line.match(/^(.+)\u4f7f\u7528\u4e86(.+)$/))) return fmtLog('use_simple', { p: m[1], card: localizedCardNameFromAny(m[2]) });
    if ((m = line.match(/^(.+)\u88c5\u5907\u4e86(.+)$/))) return fmtLog('equip', { p: m[1], card: localizedCardNameFromAny(m[2]) });
    if ((m = line.match(/^(.+)\u4f7f\u7528(.+)\u8fdb\u884c\u53cd\u5236\uff01$/))) return fmtLog('counter', { p: m[1], card: localizedCardNameFromAny(m[2]) });
    if ((m = line.match(/^(.+)\u88ab\u653e\u9010$/))) return fmtLog('exile', { card: localizedCardNameFromAny(m[1]) });
    if ((m = line.match(/^\u5355\u4eba\u8bad\u7ec3\u573a\u5f00\u59cb\uff01(.+)\u5148\u624b\u3002$/))) return tf('training_start', m[1]);
    if ((m = line.match(/^\u8bad\u7ec3\u573a\uff1a(.+) \u8bbe\u7f6e\u4e0b\u6b21\u62bd\u724c\uff1a(.+)$/))) return tf('training_set_draw', m[1], m[2].split('\u3001').map(localizedCardNameFromAny).join(', '));
    const table = LOG_TEXT[currentLang] || LOG_TEXT.en;
    return line
        .replaceAll('\u4e2d\u6bd2', table.poison)
        .replaceAll('\u707c\u70e7', table.burn)
        .replaceAll('\u7269\u7406', table.physical);
}

function translateServerMessage(message) {
    if (!message) return UI.operation_failed;
    if (message === 'Operation failed') return UI.operation_failed;
    if (message === '游戏已结束') return UI.error_game_over;
    if (message === '等待对手反制响应') return UI.error_waiting_counter;
    if (message === '卡牌不在手中') return UI.error_card_not_in_hand;
    if (message === '移出手牌失败') return UI.error_remove_from_hand_failed;
    if (message === '没有待响应的操作') return UI.error_no_pending_response;
    if (message === '没有待选择操作') return UI.error_no_pending_choice;
    if (message === '选择已取消') return UI.error_choice_cancelled;
    if (message === '不是你的回合') return UI.error_not_your_turn;
    if (message === '装备不存在') return UI.error_equipment_missing;
    if (message === '该装备没有触发效果') return UI.error_equipment_no_trigger;
    if (message === '装备需要装备一回合后才能触发') return UI.error_equipment_turn_needed;
    if (message === '能量不足') return UI.error_not_enough_e;
    if (message === '目标无效') return UI.error_target_invalid;
    if (message === '链子效果中，无法使用卡牌') return UI.error_action_blocked;
    if (message === '本回合无法使用攻击牌') return UI.error_attack_blocked;
    if (message === '本回合只能使用攻击牌') return UI.error_attack_only;
    if (message === '反制牌只能通过响应机制使用') return UI.error_waiting_response_ui;
    return message;
}

function translateLoginReason(reason) {
    if (!reason) return UI.login_failed;
    if (reason === 'Invalid nickname. Use 1-16 display-width characters; avoid pure numbers, pure symbols, or repeated -/_.') {
        return UI.login_invalid_nickname;
    }
    if (reason === 'Nickname already exists') return UI.login_nickname_exists;
    return reason;
}
let playerId = -1;
let mySid = '';
let nickname = '';
let socket = null;
let CARD_DEFS = {};
let gameState = {};
let draftState = {};
let eventSelectData = {};
let lobbyPlayers = [];
let lobbyOngoingGames = [];
const DEFAULT_SERVER = 'python-online-garden-of-thorn.onrender.com';
let phase = 'connecting';
let responsePending = false;
let responseData = {};
let choicePending = false;
let choiceData = {};
let isSpectating = false;
let spectatePerspective = 0;
let responseTimerId = null;
let responseCountdown = 0;
let allyConsentTimerId = null;
let allyConsentCountdown = 0;
let soloMode = false;
let soloDeckA = [];
let soloDeckB = [];
let soloTargetDeck = 'a';
let pendingSoloStart = false;
let openingEvents = [];
let openingEventMagicPool = [];
let soloEventA = '';
let soloEventB = '';
let pendingPlayCard = null;
let gameTimelineEntries = [];
let renderedBattleLogCount = 0;
let renderedBattleLogTotal = 0;
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

function gamePrompt(title, options) {
    return new Promise((resolve) => {
        const el = $('game-prompt');
        if (!el) { resolve(-1); return; }
        $('game-prompt-title').textContent = title || '';
        const optsEl = $('game-prompt-options');
        optsEl.innerHTML = '';
        options.forEach((opt, i) => {
            const div = document.createElement('div');
            div.className = 'game-prompt-option';
            div.textContent = opt;
            div.onclick = () => { el.classList.remove('active'); resolve(i); };
            optsEl.appendChild(div);
        });
        const cancelBtn = $('game-prompt-cancel');
        cancelBtn.textContent = UI.cancel;
        cancelBtn.onclick = () => { el.classList.remove('active'); resolve(-1); };
        el.classList.add('active');
    });
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('got_theme', theme);
    const sel = $('settings-theme-select');
    if (sel) sel.value = theme;
}

function applyLang(lang) {
    currentLang = lang;
    localStorage.setItem('got_lang', lang);
    document.documentElement.setAttribute('lang', lang);
    const sel = $('settings-lang-select');
    if (sel) sel.value = lang;
    updateStaticText();
}

function updateStaticText() {
    const subtitle = document.querySelector('#view-login .subtitle');
    if (subtitle) subtitle.textContent = UI.app_subtitle;
    const bootSub = document.querySelector('#boot-loader .boot-sub');
    if (bootSub) bootSub.textContent = UI.game_loading;
    const bootStep = $('boot-step');
    if (bootStep && !bootStep.dataset.dynamic) bootStep.textContent = UI.init_scripts;
    const settingsTitle = $('settings-title');
    if (settingsTitle) settingsTitle.textContent = UI.settings_title;
    const settingsAppearance = $('settings-section-appearance');
    if (settingsAppearance) settingsAppearance.textContent = UI.settings_appearance;
    const settingsMods = $('settings-section-mods');
    if (settingsMods) settingsMods.textContent = UI.settings_mods;
    const settingsLabelTheme = $('settings-label-theme');
    if (settingsLabelTheme) settingsLabelTheme.textContent = UI.settings_theme;
    const settingsLabelLang = $('settings-label-lang');
    if (settingsLabelLang) settingsLabelLang.textContent = UI.settings_lang;
    const themeSelect = $('settings-theme-select');
    if (themeSelect) {
        themeSelect.options[0].textContent = UI.settings_theme_light;
        themeSelect.options[1].textContent = UI.settings_theme_dark;
    }
    const langSelect = $('settings-lang-select');
    if (langSelect) {
        langSelect.options[0].textContent = '\u7b80\u4f53\u4e2d\u6587';
        langSelect.options[1].textContent = 'English (US)';
        langSelect.options[2].textContent = 'Francais';
        langSelect.options[3].textContent = 'Portugues (Brasil)';
        langSelect.options[4].textContent = '\u0420\u0443\u0441\u0441\u043a\u0438\u0439';
        langSelect.options[5].textContent = '\u65e5\u672c\u8a9e';
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
    const btnOpenAbout = $('btn-open-about');
    if (btnOpenAbout) btnOpenAbout.textContent = '关于';
    const aboutTabRules = $('about-tab-rules');
    if (aboutTabRules) aboutTabRules.textContent = '游戏玩法';
    const aboutTabCredits = $('about-tab-credits');
    if (aboutTabCredits) aboutTabCredits.textContent = '致谢';
    const creditsDeveloper = $('credits-developer-title');
    if (creditsDeveloper) creditsDeveloper.textContent = '开发者';
    const creditsSpecial = $('credits-special-title');
    if (creditsSpecial) creditsSpecial.textContent = '特别鸣谢';
    const btnLobbyBack = $('btn-lobby-back');
    if (btnLobbyBack) btnLobbyBack.textContent = UI.back_to_home;
    const btnLobbySettings = $('btn-lobby-settings');
    if (btnLobbySettings) btnLobbySettings.textContent = UI.settings_btn;
    const btnConnect = $('btn-connect');
    if (btnConnect) btnConnect.textContent = UI.enter_lobby;
    const btnSoloTraining = $('btn-solo-training');
    if (btnSoloTraining) btnSoloTraining.textContent = UI.solo_training;
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
    if (nicknameInput && !nicknameInput.value) nicknameInput.value = localStorage.getItem('got_nickname') || '';
    const gameChatInput = $('game-chat-input');
    if (gameChatInput) gameChatInput.placeholder = UI.message_placeholder;
    const lobbyChatInput = $('lobby-chat-input');
    if (lobbyChatInput) lobbyChatInput.placeholder = UI.message_placeholder;
    const draftH2 = document.querySelector('#view-draft h2');
    if (draftH2) draftH2.textContent = UI.draft_phase;
    const eventH2 = document.querySelector('#view-event-select h2');
    if (eventH2) eventH2.textContent = UI.select_event;
    const eventDesc = document.querySelector('#view-event-select .event-desc');
    if (eventDesc) eventDesc.textContent = UI.select_event_desc;
    const btnDraftReroll = $('btn-draft-reroll');
    if (btnDraftReroll) btnDraftReroll.textContent = UI.draft_reroll;
    const btnReturnLobby = $('btn-return-lobby');
    if (btnReturnLobby) btnReturnLobby.textContent = UI.return_lobby;
    const btnRematch = $('btn-rematch');
    if (btnRematch) btnRematch.textContent = UI.rematch;
    const btnSurrender = $('btn-surrender');
    if (btnSurrender) btnSurrender.textContent = UI.surrender;
    const btnViewDeck = $('btn-view-deck');
    if (btnViewDeck) btnViewDeck.textContent = UI.view_deck;
    const btnEndTurn = $('btn-end-turn');
    if (btnEndTurn) btnEndTurn.textContent = UI.end_turn;
    const btnSoloNextDraw = $('btn-solo-next-draw');
    if (btnSoloNextDraw) btnSoloNextDraw.textContent = UI.set_next_draw;
    const btnSoloEdit = $('btn-solo-edit');
    if (btnSoloEdit) btnSoloEdit.textContent = UI.pause_edit;
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
    if (oppInfo && (!gameState || !gameState.opponent)) oppInfo.textContent = UI.hand_deck_zero_opp;
    const youInfo = $('you-info');
    if (youInfo && (!gameState || !gameState.you)) youInfo.textContent = UI.hand_deck_zero_you;
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
}

function $(id) { return document.getElementById(id); }

function showView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
    const el = $(viewId);
    if (el) el.classList.remove('hidden');
    if (viewId !== 'view-game') {
        gameTimelineEntries = [];
        renderedBattleLogCount = 0;
        renderedBattleLogTotal = 0;
        updateModeSpecificControls({ solo: false, phase: '' });
    }
}

let gallerySelectedId = null;
let galleryMode = 'cards';
let rulesScrollTop = 0;
let galleryReturnToRules = false;

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

function openAbout() {
    const panel = $('about-panel');
    if (panel) panel.classList.remove('hidden');
    setAboutPage('rules');
    const body = $('about-rules-body');
    bindRulesCardLinks(body);
    if (body && rulesScrollTop) requestAnimationFrame(() => { body.scrollTop = rulesScrollTop; });
}

function closeAbout() {
    const panel = $('about-panel');
    if (panel) panel.classList.add('hidden');
}

function setGalleryMode(mode) {
    galleryMode = mode || 'cards';
    ['cards', 'tags', 'events'].forEach(name => {
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
    if (backBtn) backBtn.textContent = galleryReturnToRules ? '返回介绍' : '返回主页';
    if (selectedId) gallerySelectedId = selectedId;
    if (!gallerySelectedId || !CARD_DEFS[gallerySelectedId]) {
        gallerySelectedId = Object.keys(CARD_DEFS).sort((a, b) => getCardName(CARD_DEFS[a]).localeCompare(getCardName(CARD_DEFS[b])))[0] || null;
    }
    renderCardGallery();
}

function makeGalleryFlagHtml(flag) {
    const style = CARD_FLAG_STYLES[flag];
    const label = getFlagLabel(flag);
    if (style) return `<span class="card-flag ${style.cls}">${label}</span>`;
    return `<span class="card-flag">${label}</span>`;
}

function getAllGalleryFlags() {
    const flags = new Set(Object.keys(CARD_FLAG_STYLES));
    Object.values(CARD_DEFS).forEach(cd => (cd.flags || []).forEach(flag => {
        if (flag !== 'infinite_exclude') flags.add(flag);
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
    const ids = Object.keys(CARD_DEFS)
        .filter(id => {
            const cd = CARD_DEFS[id];
            const flagText = (cd.flags || []).map(getFlagLabel).join(' ');
            const text = `${id} ${cd.name_cn || ''} ${cd.name_en || ''} ${getCardName(cd)} ${getCardEffectText(cd)} ${getCardDescriptionText(cd)} ${flagText}`.toLowerCase();
            return !q || text.includes(q);
        })
        .sort((a, b) => getCardName(CARD_DEFS[a]).localeCompare(getCardName(CARD_DEFS[b])));
    list.innerHTML = '';
    ids.forEach(id => {
        const cd = CARD_DEFS[id];
        const flags = (cd.flags || []).filter(flag => flag !== 'infinite_exclude').map(getFlagLabel).join(' / ');
        const row = document.createElement('div');
        row.className = 'gallery-card-row' + (id === gallerySelectedId ? ' active' : '');
        row.innerHTML = `<div class="gallery-row-title">${getCardName(cd)}</div>${flags ? `<div class="gallery-row-meta">${flags}</div>` : ''}`;
        row.onclick = () => { gallerySelectedId = id; renderCardGallery(); };
        list.appendChild(row);
    });
    const cd = CARD_DEFS[gallerySelectedId] || CARD_DEFS[ids[0]];
    if (!cd) {
        detail.innerHTML = `<p>${UI.gallery_no_items}</p>`;
        return;
    }
    gallerySelectedId = cd.id;
    const cardEl = createCardElement({ def_id: cd.id, instance_flags: [], disabled_flags: [] }, { small: false, showAllFlags: true });
    const flags = (cd.flags || []).filter(flag => flag !== 'infinite_exclude');
    detail.innerHTML = `<div class="gallery-detail-card"><div id="gallery-card-preview"></div><div class="gallery-detail-info">
        <h3>${getCardName(cd)}</h3>
        <p><b>${UI.gallery_type}：</b>${getCardTypeLabel(cd.card_type)}</p>
        <p><b>${UI.gallery_cost}：</b>${cd.cost_e || 0}E / ${cd.cost_m || 0}M</p>
        ${flags.length ? `<p><b>${UI.gallery_tags_label}：</b>${flags.map(getFlagLabel).join(' / ')}</p>` : ''}
        <p><b>${UI.gallery_description}：</b>${getCardDescriptionText(cd) || '-'}</p>
        <p><b>${UI.gallery_effect}：</b>${getCardEffectText(cd) || '-'}</p>
        ${cd.trigger_effect_text ? `<p><b>${UI.gallery_trigger}：</b>${getCardTriggerText(cd)}</p>` : ''}
    </div></div>`;
    const preview = $('gallery-card-preview');
    if (preview) preview.appendChild(cardEl);
}

function renderTagGallery(list, detail, q) {
    const flags = getAllGalleryFlags().filter(flag => {
        const text = `${flag} ${getFlagLabel(flag)}`.toLowerCase();
        return !q || text.includes(q);
    });
    if (!flags.includes(gallerySelectedId)) gallerySelectedId = flags[0] || null;
    list.innerHTML = '';
    flags.forEach(flag => {
        const usedBy = Object.values(CARD_DEFS).filter(cd => (cd.flags || []).includes(flag));
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
    const usedBy = Object.values(CARD_DEFS)
        .filter(cd => (cd.flags || []).includes(gallerySelectedId))
        .sort((a, b) => getCardName(a).localeCompare(getCardName(b)));
    detail.innerHTML = `<div class="gallery-simple-detail">
        <h3>${getFlagLabel(gallerySelectedId)}</h3>
        <div class="gallery-tag-list">${makeGalleryFlagHtml(gallerySelectedId)}</div>
        <p><b>ID：</b>${gallerySelectedId}</p>
        <p><b>${UI.gallery_cards_with_tag}：</b>${usedBy.length ? usedBy.map(getCardName).join(' / ') : '-'}</p>
    </div>`;
}

function renderOpeningEventGallery(list, detail, q) {
    const events = (openingEvents || []).filter(ev => {
        const text = `${ev.id} ${getLocalizedEventText(ev, 'name')} ${getLocalizedEventText(ev, 'desc')}`.toLowerCase();
        return !q || text.includes(q);
    });
    const eventIds = events.map(ev => `event:${ev.id}`);
    if (!eventIds.includes(gallerySelectedId)) gallerySelectedId = eventIds[0] || null;
    list.innerHTML = '';
    events.forEach(ev => {
        const id = `event:${ev.id}`;
        const row = document.createElement('div');
        row.className = 'gallery-card-row' + (id === gallerySelectedId ? ' active' : '');
        row.innerHTML = `<div class="gallery-row-title">${getLocalizedEventText(ev, 'name') || '?'}</div><div class="gallery-row-meta">${getLocalizedEventText(ev, 'desc') || ''}</div>`;
        row.onclick = () => { gallerySelectedId = id; renderCardGallery(); };
        list.appendChild(row);
    });
    const selectedEventId = gallerySelectedId ? Number(String(gallerySelectedId).replace('event:', '')) : null;
    const ev = events.find(item => item.id === selectedEventId) || events[0];
    if (!ev) {
        detail.innerHTML = `<p>${UI.gallery_no_items}</p>`;
        return;
    }
    gallerySelectedId = `event:${ev.id}`;
    detail.innerHTML = `<div class="gallery-simple-detail">
        <h3>${getLocalizedEventText(ev, 'name') || '?'}</h3>
        <p><b>ID：</b>${ev.id}</p>
        <p>${getLocalizedEventText(ev, 'desc') || ''}</p>
    </div>`;
}

function openRulesModal({ firstVisit = false } = {}) {
    const modal = $('modal');
    const content = $('modal-content');
    if (!modal || !content) return;
    const skipHtml = firstVisit ? `<div class="game-alert-message">你确认要跳过游戏介绍吗？<br>可以在 关于&gt;游戏玩法 中再次打开此界面。</div>` : '';
    content.className = 'modal-inner rules-modal';
    content.innerHTML = `
        <h3>游戏介绍</h3>
        ${skipHtml}
        <div class="rules-body" id="rules-body">
            <h4>基本目标</h4>
            <p>Garden of Thorn 荆棘花园 是 1v1 卡牌对战游戏。你的目标是通过攻击、技能、装备和反制，让对方 H 降到 0，同时保护自己的 H。</p>
            <h4>资源</h4>
            <p>H 是生命，E 是能量，M 是魔力。大多数卡牌消耗 E，部分魔法牌消耗 M。回合开始时会抽牌并回复资源。</p>
            <h4>卡牌类型</h4>
            <p><b>Thorn</b> 是攻击牌，例如 <a data-card="Basic">基本</a>、<a data-card="Bone">骨头</a>。<b>Bloom</b> 是技能牌，例如 <a data-card="Fire">火</a>。<b>Root</b> 是装备牌，例如 <a data-card="Leaf">叶子</a>。<b>Guard</b> 是反制牌，会在对方行动时响应。</p>
            <h4>回合流程</h4>
            <p>正常模式先选牌，再选择开局事件，然后进入对局。轮到你时可以打出手牌、触发已装备一回合的装备，最后结束回合。</p>
            <h4>常见关键词</h4>
            <p><b>放逐</b>表示打出或结算后进入放逐区；<b>精准</b>通常能绕过普通闪避；<b>不可摧毁</b>表示不能被摧毁效果破坏；<b>萌芽</b>抽到时额外抽牌；<b>共生</b>不受同名卡费用惩罚。</p>
            <h4>示例</h4>
            <p><a data-card="Stinger">刺</a> 是高伤害精准攻击；<a data-card="Sewage">污水</a> 可以摧毁装备；<a data-card="Bubble">泡泡</a> 可以响应攻击。</p>
        </div>
        <div class="modal-buttons">
            ${firstVisit ? `<button id="btn-rules-skip" class="btn btn-secondary">跳过</button>` : ''}
            <button id="btn-rules-close" class="btn btn-primary">关闭</button>
        </div>`;
    modal.classList.remove('hidden');
    modal.classList.add('active');
    const body = $('rules-body');
    if (body && rulesScrollTop) body.scrollTop = rulesScrollTop;
    bindRulesCardLinks(content);
    const close = $('btn-rules-close');
    if (close) close.onclick = () => {
        localStorage.setItem('got_seen_intro', '1');
        content.className = 'modal-inner';
        hideModal();
    };
    const skip = $('btn-rules-skip');
    if (skip) skip.onclick = () => {
        localStorage.setItem('got_seen_intro', '1');
        content.className = 'modal-inner';
        hideModal();
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
function flashStatus(text, duration, type) {
    const s = $('status-text');
    if (!s) return;
    if (_statusTimeout) { clearTimeout(_statusTimeout); _statusTimeout = null; }
    else { _prevStatusText = s.textContent || ''; }
    s.textContent = text;
    if (type === 'error') {
        s.style.color = '#C0392B';
    } else {
        s.style.color = '#E67E22';
    }
    s.style.fontWeight = '700';
    _statusTimeout = setTimeout(() => {
        s.style.color = '';
        s.style.fontWeight = '';
        s.textContent = _prevStatusText || UI.default_status;
        _prevStatusText = '';
        _statusTimeout = null;
    }, duration || 2000);
}

function showModal(html) {
    const content = $('modal-content');
    const modal = $('modal');
    if (content) content.className = 'modal-inner';
    if (content) content.innerHTML = html;
    if (modal) { modal.classList.remove('hidden'); modal.classList.add('active'); }
}

function hideModal() {
    const modal = $('modal');
    const content = $('modal-content');
    if (content) content.className = 'modal-inner';
    if (modal) { modal.classList.add('hidden'); modal.classList.remove('active'); }
}

async function fetchCardDefs() {
    try {
        bootLoader.step(UI.init_cards_mods, 60);
        const disabledMods = encodeURIComponent(getDisabledMods().join(','));
        const resp = await fetch(`/api/cards?disabled_mods=${disabledMods}`);
        CARD_DEFS = await resp.json();
    } catch (e) {
        console.error('Failed to fetch card defs:', e);
        CARD_DEFS = {};
    }
}

async function fetchOpeningEvents() {
    try {
        bootLoader.step(UI.init_opening_events, 78);
        const resp = await fetch('/api/opening-events');
        const data = await resp.json();
        openingEvents = data.events || [];
        openingEventMagicPool = data.magic_pool || [];
    } catch (e) {
        console.error('Failed to fetch opening events:', e);
        openingEvents = [];
        openingEventMagicPool = [];
    }
}

function getCardDef(defId) {
    return CARD_DEFS[defId] || null;
}

function getFlagLabel(flag) {
    return UI[`tag_${flag}`] || UI[`flag_${flag}`] || flag;
}

function getCardDisplayCosts(cardDict, cardDef, ownerState = null) {
    const baseE = cardDict.cost_e_override != null ? cardDict.cost_e_override : cardDef.cost_e;
    const baseM = cardDict.cost_m_override != null ? cardDict.cost_m_override : cardDef.cost_m;
    const mimicDiscount = Number(cardDict.mimic_discount || 0);
    const flags = new Set([...(cardDef.flags || []), ...(cardDict.instance_flags || [])]);
    const dup = ownerState && ownerState.cards_played_this_turn
        ? Number(ownerState.cards_played_this_turn[cardDict.def_id] || 0)
        : 0;
    const effectiveBaseE = Math.max(0, baseE - mimicDiscount);
    const totalE = effectiveBaseE + (flags.has('symbiosis') ? 0 : dup);
    return { totalE, totalM: baseM, flags };
}

function getCardLayerLabel(cardDict) {
    const fusionLevel = Number(cardDict.fusion_level || 1);
    const fissionLevel = Number(cardDict.fission_level || 1);
    const parts = [];
    if (fusionLevel > 1) parts.push(`${UI.fusion_layer || 'Fusion'}:${fusionLevel}`);
    if (fissionLevel > 1) parts.push(`${UI.fission_layer || 'Fission'}:${fissionLevel}`);
    return parts.length ? ` (${parts.join(' ')})` : '';
}

function createCardElement(cardDict, options = {}) {
    const { faceDown = false, small = false, draggable = false, onClick = null, showAllFlags = false } = options;
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
    const typeColor = CARD_TYPE_COLORS[cardDef.card_type] || COLORS.text_primary;
    const typeLabel = getCardTypeLabel(cardDef.card_type) || cardDef.card_type;
    const cardName = getCardName(cardDef);
    const effectText = getCardEffectText(cardDef);
    const descriptionText = getCardDescriptionText(cardDef);
    const { totalE, totalM, flags } = getCardDisplayCosts(cardDict, cardDef, gameState && gameState.you);
    el.style.borderColor = typeColor;
    el.dataset.instanceId = cardDict.instance_id;
    el.dataset.defId = defId;
    let flagsHtml = '';
    for (const flag of flags) {
        if (!showAllFlags && flag === 'self_only' && (!gameState || gameState.mode !== '2v2')) {
            continue;
        }
        const style = CARD_FLAG_STYLES[flag];
        if (style) {
            const label = UI['flag_' + flag] || UI['tag_' + flag] || flag;
            flagsHtml += `<span class="card-flag ${style.cls}">${label}</span>`;
        }
    }
    const fusionLevel = Number(cardDict.fusion_level || 1);
    const fissionLevel = Number(cardDict.fission_level || 1);
    if (fusionLevel > 1) {
        flagsHtml += `<span class="card-flag fusion-layer">${UI.fusion_layer || 'Fusion'}: ${fusionLevel}</span>`;
    }
    if (fissionLevel > 1) {
        flagsHtml += `<span class="card-flag fission-layer">${UI.fission_layer || 'Fission'}: ${fissionLevel}</span>`;
    }
    el.innerHTML = `
        <div class="card-costs">
            <span class="cost-e">${totalE}</span>
            <span class="card-name" style="color:${typeColor}">${cardName}</span>
            <span class="cost-m">${totalM}</span>
        </div>
        <div class="card-type-label-wrap"><span class="card-type-label" style="color:${typeColor}">${typeLabel}</span></div>
        <div class="card-effect">${effectText || ''}</div>
        ${descriptionText ? `<div class="card-description">${descriptionText}</div>` : ''}
        ${flagsHtml ? `<div class="card-flags">${flagsHtml}</div>` : ''}
    `;
    if (draggable) {
        el.classList.add('card-draggable');
        el.addEventListener('mousedown', (e) => startCardDrag(e, el));
        el.addEventListener('touchstart', (e) => startCardDrag(e, el), { passive: false });
    }
    if (onClick) {
        el.addEventListener('click', onClick);
        el.style.cursor = 'pointer';
    }
    return el;
}

let dragState = null;

function getPointerPos(e) {
    if (e.touches && e.touches.length > 0) {
        return { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }
    if (e.changedTouches && e.changedTouches.length > 0) {
        return { x: e.changedTouches[0].clientX, y: e.changedTouches[0].clientY };
    }
    return { x: e.clientX, y: e.clientY };
}

function startCardDrag(e, cardEl) {
    if (isSpectating) return;
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
    dragState = { instanceId, ghost, originalCard: cardEl, offsetX: rect.width / 2, offsetY: rect.height / 2 };
}

function onDocumentPointerMove(e) {
    if (!dragState) return;
    e.preventDefault();
    const pos = getPointerPos(e);
    dragState.ghost.style.left = (pos.x - dragState.offsetX) + 'px';
    dragState.ghost.style.top = (pos.y - dragState.offsetY) + 'px';
    const playZone = document.getElementById('play-zone');
    if (playZone) {
        const r = playZone.getBoundingClientRect();
        if (pos.x >= r.left && pos.x <= r.right && pos.y >= r.top && pos.y <= r.bottom) {
            playZone.classList.add('drag-over');
        } else {
            playZone.classList.remove('drag-over');
        }
    }
}

function cleanupDragState() {
    document.querySelectorAll('.drag-ghost').forEach(el => el.remove());
    document.querySelectorAll('.card.dragging').forEach(el => el.classList.remove('dragging'));
    if (dragState) {
        if (dragState.originalCard) dragState.originalCard.style.opacity = '';
    }
    const playZone = document.getElementById('play-zone');
    if (playZone) playZone.classList.remove('drag-over');
    dragState = null;
}

function onDocumentPointerUp(e) {
    if (!dragState) return;
    const pos = getPointerPos(e);
    const playZone = document.getElementById('play-zone');
    let shouldPlay = false;
    if (playZone) {
        const r = playZone.getBoundingClientRect();
        if (pos.x >= r.left && pos.x <= r.right && pos.y >= r.top && pos.y <= r.bottom) {
            shouldPlay = true;
        }
    }
    const instanceId = dragState.instanceId;
    cleanupDragState();
    if (shouldPlay) {
        onPlayCard(parseInt(instanceId));
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

function connectSocket(serverUrl) {
    if (socket) {
        socket.disconnect();
        socket = null;
    }
    let url = serverUrl;
    let opts = { transports: ['websocket', 'polling'] };
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        if (url.includes('localhost') || url.includes('127.0.0.1')) {
            url = 'http://' + url;
        } else {
            url = 'https://' + url;
        }
    }
    socket = io(url, opts);

    socket.on('connect', () => {
        console.log('[client] socket connected, login nickname=', nickname);
        const disabledMods = getDisabledMods();
        const preferredMode = localStorage.getItem('preferred_mode') || '1v1';
        socket.emit('login', { nickname, disabled_mods: disabledMods, mode: preferredMode });
    });
    socket.on('disconnect', () => {
        console.log('[client] socket disconnected');
        flashStatus(UI.disconnected, 3000, 'error');
        phase = 'connecting';
    });
    socket.on('login_ok', (data) => {
        console.log('[client] login ok: sid=', data.sid, 'nickname=', data.nickname);
        mySid = data.sid || '';
        nickname = data.nickname || nickname;
        if (pendingSoloStart) {
            pendingSoloStart = false;
            emitSoloStart();
            return;
        }
        phase = 'lobby';
        updateStatus(UI.lobby_status.replace('{0}', nickname));
    });
    socket.on('login_fail', (data) => {
        showView('view-login');
        const err = $('login-error');
        if (err) err.textContent = translateLoginReason(data.reason);
    });
    socket.on('lobby_update', (data) => {
        console.log('[client] lobby_update players=', (data.players || []).length);
        lobbyPlayers = data.players || [];
        lobbyOngoingGames = data.ongoing_games || [];
        mySid = data.your_sid || mySid;
        phase = 'lobby';
        renderLobby(data);
    });
    socket.on('invite_received', (data) => {
        console.log('[client] invite_received:', data);
        showModal(`
            <h3>${UI.invite_received}</h3>
            <p>${data.inviter_name} ${UI.invite_message}</p>
            <div class="modal-buttons">
                <button class="btn btn-primary" id="invite-accept">${UI.accept}</button>
                <button class="btn btn-danger" id="invite-decline">${UI.decline}</button>
            </div>
        `);
        $('invite-accept').onclick = () => {
            console.log('[client] accept_invite inviter_sid=', data.inviter_sid);
            socket.emit('accept_invite', { inviter_sid: data.inviter_sid });
            hideModal();
        };
        $('invite-decline').onclick = () => {
            console.log('[client] decline_invite inviter_sid=', data.inviter_sid);
            socket.emit('decline_invite', { inviter_sid: data.inviter_sid });
            hideModal();
        };
    });
    socket.on('invite_declined', () => {
        flashStatus(UI.invite_declined, 2000);
    });
    socket.on('team_invite', (data) => {
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
    socket.on('team_formed', (data) => {
        flashStatus(tf('team_formed_msg', data.members.join(', ')), 3000);
    });
    socket.on('team_disbanded', () => {
        flashStatus(UI.team_disbanded_msg, 3000);
    });
    socket.on('team_declined', (data) => {
        flashStatus(UI.team_declined_msg, 2000);
    });
    socket.on('team_match_invite', (data) => {
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
    socket.on('team_match_declined', () => {
        flashStatus(UI.team_match_declined_msg, 2000);
    });
    socket.on('team_match_accepted', () => {
        hideModal();
    });
    socket.on('game_phase', (data) => {
        console.log('[client] game_phase:', data.phase);
        phase = data.phase;
        if (!data.solo) soloMode = false;
        if (phase === 'draft') {
            console.log('[client] entering draft phase, reset rematch flag');
            rematchRequestedByOpponent = false;
            showView('view-draft');
            updateStatus(UI.draft_phase);
        } else if (phase === 'event_select') {
            showView('view-event-select');
            updateStatus(UI.select_event);
        } else if (phase === 'playing') {
            showView('view-game');
            updateStatus(UI.game_loading || 'Loading...');
        } else if (phase === 'game_over') {
            showView('view-gameover');
            updateStatus(UI.game_over);
        } else if (phase === 'action' || phase === 'draw' || phase === 'response' || phase === 'choice') {
            showView('view-game');
        }
    });
    socket.on('draft_state', (data) => {
        const oldOptIds = draftState && draftState.options ? draftState.options.map(o => o.def_id) : [];
        const newOptIds = data.options ? data.options.map(o => o.def_id) : [];
        const isReroll = oldOptIds.length > 0 && JSON.stringify(oldOptIds) !== JSON.stringify(newOptIds) && (draftState ? draftState.rerolls : 0) > (data.rerolls || 0);
        draftState = data;
        renderDraft(data, isReroll);
    });
    socket.on('event_select', (data) => {
        console.log('[client] event_select');
        phase = 'event_select';
        eventSelectData = data;
        renderEventSelect(data);
    });
    socket.on('state_update', (data) => {
        console.log('[client] state_update: phase=', data.phase, 'current_player=', data.current_player, 'your_id=', data.your_id, 'pending_response=', data.pending_response != null, 'spectating=', data.spectating);
        soloMode = !!data.solo;
        gameState = data;
        phase = data.phase || phase;
        if (data.spectating) {
            isSpectating = true;
            if (data.spectate_perspective != null) spectatePerspective = data.spectate_perspective;
        }
        if (!isSpectating && data.your_id != null) playerId = data.your_id;
        if (!isSpectating && data.pending_response != null) {
            pendingPlayCard = pendingPlayCard || data.pending_response;
        } else if (!responsePending) {
            pendingPlayCard = null;
        }
        if (data.pending_response === null && responsePending) {
            responsePending = false;
            responseData = null;
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
        if (phase === 'game_over') {
            renderGameOver(data);
        } else {
            renderGame(data);
        }
    });
    socket.on('solo_state', (data) => {
        soloMode = true;
        isSpectating = false;
        gameState = data;
        phase = data.phase || phase;
        playerId = data.your_id;
        if (phase === 'game_over') {
            renderGame(data);
        } else {
            renderGame(data);
        }
    });
    socket.on('response_request', (data) => {
        console.log('[RESPONSE] response_request, counter_cards:', (data.counter_cards || []).length);
        responsePending = true;
        responseData = data;
        showResponseUI(data);
    });
    socket.on('ally_consent_request', (data) => {
        showAllyConsentUI(data);
    });
    socket.on('choice_request', (data) => {
        choicePending = true;
        choiceData = data;
        pendingPlayCard = null;
        showChoiceUI(data);
    });
    socket.on('chat', (data) => {
        console.log('[client] chat:', data.nickname, data.text, 'spectator=', data.is_spectator);
        const nick = data.is_spectator ? `[${UI.spectator_prefix}]${data.nickname}` : data.nickname;
        if (phase === 'lobby') {
            appendLobbyChat(nick, data.text);
        } else {
            appendGameChat(nick, data.text);
        }
    });
    socket.on('server_error', (data) => {
        console.log('[client] server_error:', data.message);
        gameAlert(UI.notice, translateServerMessage(data.message));
        pendingPlayCard = null;
    });
    socket.on('opponent_disconnected', (data) => {
        if (data && data.timeout) {
            updateStatus(UI.opponent_disconnected);
            socket.emit('return_lobby');
            showView('view-lobby');
            phase = 'lobby';
        } else if (data && data.reconnect_timeout > 0) {
            showOpponentDCWaiting(data);
        } else {
            updateStatus(UI.opponent_disconnected);
            socket.emit('return_lobby');
            showView('view-lobby');
            phase = 'lobby';
        }
    });
    socket.on('opponent_reconnected', () => {
        flashStatus(UI.opponent_reconnected, 2000);
        hideModal();
    });
    socket.on('reconnect_available', (data) => {
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
    socket.on('reconnect_timeout', () => {
        flashStatus(UI.reconnect_timeout, 3000, 'error');
        phase = 'lobby';
    });
    socket.on('rematch_requested', () => {
        console.log('[client] rematch_requested');
        rematchRequestedByOpponent = true;
        const btn = $('btn-rematch');
        if (btn) {
            btn.textContent = UI.agree_rematch;
            btn.disabled = false;
            btn.onclick = () => {
                if (!socket) return;
                socket.emit('rematch');
                btn.textContent = UI.rematch_sent;
                btn.disabled = true;
            };
        }
        updateStatus(UI.opponent_rematch);
    });
    socket.on('spectate_enter', (data) => {
        isSpectating = true;
        spectatePerspective = 0;
        phase = 'playing';
        showView('view-game');
    });
    socket.on('spectate_leave', () => {
        isSpectating = false;
        spectatePerspective = 0;
        phase = 'lobby';
        showView('view-lobby');
    });
    socket.on('server_broadcast', (data) => {
        flashStatus(UI.server_broadcast.replace('{0}', data.message || ''), 4000);
    });
    socket.on('solo_paused', () => {
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
    localStorage.setItem('got_nickname', nick);
    if (err) err.textContent = '';
    updateStatus(UI.connecting);
    connectSocket(server);
}

function getServerAddress() {
    const custom = localStorage.getItem('got_server') || '';
    return custom.trim() || DEFAULT_SERVER;
}

function showSoloTraining() {
    soloMode = false;
    phase = 'solo_edit';
    loadSoloDecks(false);
    renderSoloEventSelects();
    renderSoloBuilder();
    showView('view-solo');
    updateStatus(UI.solo_training);
}

function loadSoloDecks(showNotice = true) {
    const saved = JSON.parse(localStorage.getItem('got_solo_decks') || 'null');
    if (saved && Array.isArray(saved.deck0) && Array.isArray(saved.deck1)) {
        const normalizeDeck = (deck) => deck
            .map(entry => typeof entry === 'string'
                ? { def_id: entry, instance_flags: [], disabled_flags: [] }
                : { def_id: entry.def_id, instance_flags: [...(entry.instance_flags || [])], disabled_flags: [...(entry.disabled_flags || [])] })
            .filter(entry => CARD_DEFS[entry.def_id])
            .slice(0, 15);
        soloDeckA = normalizeDeck(saved.deck0);
        soloDeckB = normalizeDeck(saved.deck1);
        soloEventA = saved.event0 != null ? String(saved.event0) : '';
        soloEventB = saved.event1 != null ? String(saved.event1) : '';
        if (showNotice) flashStatus(UI.load_last, 1200);
    }
}

function saveSoloDecks() {
    localStorage.setItem('got_solo_decks', JSON.stringify({ deck0: soloDeckA, deck1: soloDeckB, event0: soloEventA, event1: soloEventB }));
    flashStatus(UI.solo_saved, 1600);
}

function cardSearchText(defId) {
    const cd = getCardDef(defId);
    if (!cd) return defId.toLowerCase();
    const names = cd.name_i18n ? Object.values(cd.name_i18n).join(' ') : '';
    const effects = cd.effect_text_i18n ? Object.values(cd.effect_text_i18n).join(' ') : '';
    const descriptions = cd.description_i18n ? Object.values(cd.description_i18n).join(' ') : '';
    return `${cd.id} ${cd.name_cn || ''} ${cd.name_en || ''} ${names} ${effects} ${descriptions}`.toLowerCase();
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
            .filter(defId => !q || cardSearchText(defId).includes(q))
            .sort((a, b) => getCardName(CARD_DEFS[a]).localeCompare(getCardName(CARD_DEFS[b])))
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
    el.innerHTML = '';
    el.classList.toggle('active', soloTargetDeck === which);
    el.onclick = () => { soloTargetDeck = which; renderSoloBuilder(); };
    deck.forEach((defId, idx) => {
        const card = deck[idx];
        const cd = getCardDef(card.def_id);
        const baseFlags = new Set((cd && cd.flags) || []);
        const disabledFlags = new Set(card.disabled_flags || []);
        const effectiveFlags = new Set([...(card.instance_flags || []), ...baseFlags]);
        disabledFlags.forEach(flag => effectiveFlags.delete(flag));
        const flagText = [...effectiveFlags].map(getFlagLabel).join(', ');
        const row = document.createElement('div');
        row.className = 'solo-deck-card';
        row.innerHTML = `
            <div class="solo-deck-card-main">
                <span>${idx + 1}. ${cd ? getCardName(cd) : card.def_id}</span>
                ${flagText ? `<small>${flagText}</small>` : ''}
            </div>
            <div class="solo-deck-card-actions">
                <button class="btn btn-small solo-tag-btn">${UI.edit_tags}</button>
                <button class="btn btn-small">${UI.cancel}</button>
            </div>`;
        row.querySelector('.solo-tag-btn').onclick = async (e) => {
            e.stopPropagation();
            await editSoloCardFlags(which, idx);
        };
        row.querySelector('.solo-deck-card-actions button:last-child').onclick = (e) => {
            e.stopPropagation();
            deck.splice(idx, 1);
            renderSoloBuilder();
        };
        el.appendChild(row);
    });
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
    const allFlags = ['precision', 'exile', 'non_stackable', 'indestructible', 'sprout', 'symbiosis', 'attract', 'void', 'self_only', 'uncancellable'];
    const base = new Set((cd && cd.flags) || []);
    const added = new Set(card.instance_flags || []);
    const disabled = new Set(card.disabled_flags || []);
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
        const countSel = await gamePrompt(UI.choose_convert_count, countOptions);
        if (countSel < 0) return false;
        for (let i = 0; i <= countSel; i++) {
            const magicDisplay = openingEventMagicPool.map(defId => {
                const cd = getCardDef(defId);
                return cd ? getCardName(cd) : defId;
            });
            const magicSel = await gamePrompt(UI.choose_magic_card_n.replace('{0}', i + 1), magicDisplay);
            if (magicSel < 0) return false;
            const sourceOptions = deck.map((entry, idx) => {
                const cd = getCardDef(entry.def_id);
                return `${idx + 1}. ${cd ? getCardName(cd) : entry.def_id}`;
            });
            const sourceSel = await gamePrompt(`${label} ${UI.choose_source_card_n.replace('{0}', i + 1)}`, sourceOptions);
            if (sourceSel < 0) return false;
            conversions.push({
                magic_def_id: openingEventMagicPool[magicSel],
                source_def_id: deck[sourceSel].def_id,
            });
        }
        return { conversions };
    }
    if (eventId === 3) {
        const convert_def_ids = [];
        const countOptions = ['1', '2', '3', '4', '5'];
        const countSel = await gamePrompt(UI.choose_convert_count, countOptions);
        if (countSel < 0) return false;
        for (let i = 0; i <= countSel; i++) {
            const sourceOptions = deck.map((entry, idx) => {
                const cd = getCardDef(entry.def_id);
                return `${idx + 1}. ${cd ? getCardName(cd) : entry.def_id}`;
            });
            const sourceSel = await gamePrompt(`${label} ${UI.choose_source_card_n.replace('{0}', i + 1)}`, sourceOptions);
            if (sourceSel < 0) return false;
            convert_def_ids.push(deck[sourceSel].def_id);
        }
        return { convert_def_ids };
    }
    if (eventId === 8) {
        const sourceOptions = deck.map((entry, idx) => {
            const cd = getCardDef(entry.def_id);
            return `${idx + 1}. ${cd ? getCardName(cd) : entry.def_id}`;
        });
        const sourceSel = await gamePrompt(`${label} ${UI.choose_yggdrasil_card}`, sourceOptions);
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
    const event0 = soloEventA ? Number(soloEventA) : null;
    const event1 = soloEventB ? Number(soloEventB) : null;
    const sub0 = await buildSoloEventSubChoice(event0, soloDeckA, UI.solo_deck_a);
    if (sub0 === false) return;
    const sub1 = await buildSoloEventSubChoice(event1, soloDeckB, UI.solo_deck_b);
    if (sub1 === false) return;
    saveSoloDecks();
    if (!socket) {
        nickname = ($('input-nickname').value || '').trim() || 'Solo';
        pendingSoloStart = true;
        window.__pendingSoloPayload = { deck0: soloDeckA, deck1: soloDeckB, event0, event1, sub0, sub1 };
        connectSocket(getServerAddress());
        return;
    }
    emitSoloStart({ deck0: soloDeckA, deck1: soloDeckB, event0, event1, sub0, sub1 });
}

function emitSoloStart(payload = null) {
    if (!socket) return;
    soloMode = true;
    const finalPayload = payload || window.__pendingSoloPayload || { deck0: soloDeckA, deck1: soloDeckB };
    window.__pendingSoloPayload = null;
    socket.emit('solo_start', finalPayload);
}

function renderLobby(data) {
    showView('view-lobby');
    const lobbyPlayers = data.players || [];
    const games = data.ongoing_games || [];
    const teamList = data.teams || [];
    const myTeam = data.your_team || null;
    const myTeamLeader = data.your_team_leader || null;
    const serverMode = data.your_mode || '1v1';
    console.log('[client] renderLobby: players=', lobbyPlayers.length, 'mySid=', mySid, 'myTeam=', myTeam, 'mode=', serverMode);

    const modeTabs = $('lobby-mode-tabs');
    if (modeTabs) {
        const cachedMode = localStorage.getItem('preferred_mode') || '1v1';
        const currentMode = serverMode || cachedMode;
        modeTabs.querySelectorAll('.mode-tab').forEach(tab => {
            const tabMode = tab.getAttribute('data-mode');
            tab.textContent = UI[`mode_${tabMode}`] || tab.textContent;
            if (tabMode === currentMode) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
            tab.onclick = () => {
                const newMode = tab.getAttribute('data-mode');
                if (newMode === currentMode) return;
                if (myTeam && newMode !== '2v2') {
                    if (!confirm(UI.mode_switch_confirm)) return;
                }
                localStorage.setItem('preferred_mode', newMode);
                socket.emit('set_mode', { mode: newMode });
            };
        });
    }

    const currentMode = (modeTabs && modeTabs.querySelector('.mode-tab.active'))
        ? modeTabs.querySelector('.mode-tab.active').getAttribute('data-mode')
        : (localStorage.getItem('preferred_mode') || '1v1');

    const filteredPlayers = lobbyPlayers.filter(p => {
        const pMode = p.mode || '1v1';
        return pMode === currentMode;
    });

    const onlineCount = $('lobby-online-count');
    if (onlineCount) onlineCount.textContent = tf('online_count', filteredPlayers.length);

    const teamSection = $('lobby-team-section');
    if (teamSection) {
        teamSection.innerHTML = '';
        if (myTeam && currentMode === '2v2') {
            const teamMembers = myTeam.map(sid => {
                const p = lobbyPlayers.find(pl => pl.sid === sid);
                return p ? p.nickname : '?';
            });
            const teamInfoDiv = document.createElement('div');
            teamInfoDiv.className = 'team-info';
            teamInfoDiv.innerHTML = `${UI.teammate}: ${teamMembers.join(', ')} `;
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

    if (currentMode === '2v2') {
        const teamsInMode = teamList.filter(t => {
            return t.member_sids.some(sid => {
                const p = lobbyPlayers.find(pl => pl.sid === sid);
                return p && (p.mode || '1v1') === '2v2';
            });
        });
        const teamedSids = new Set();
        teamsInMode.forEach(t => t.member_sids.forEach(s => teamedSids.add(s)));
        const unteamed = filteredPlayers.filter(p => !teamedSids.has(p.sid));

        if (teamsInMode.length === 0 && unteamed.length === 0) {
            list.innerHTML = `<div class="empty-hint">${UI.no_other_players}</div>`;
        } else {
            teamsInMode.forEach(team => {
                const isMyTeamRow = myTeam && team.member_sids.some(s => myTeam.includes(s));
                const row = document.createElement('div');
                row.className = 'lobby-team-row';
                const nameSpan = document.createElement('span');
                nameSpan.className = 'player-name';
                nameSpan.textContent = team.members.join(' & ');
                row.appendChild(nameSpan);
                if (!isMyTeamRow && myTeam) {
                    const btn = document.createElement('button');
                    btn.textContent = UI.invite_team;
                    btn.className = 'btn btn-primary btn-sm';
                    btn.onclick = () => socket.emit('invite_team', { target_team_leader: team.leader });
                    row.appendChild(btn);
                }
                list.appendChild(row);
            });
            unteamed.forEach(p => {
                const row = document.createElement('div');
                row.className = 'lobby-player-row';
                const isMe = p.sid === mySid;
                const nameSpan = document.createElement('span');
                nameSpan.className = isMe ? 'player-name player-self' : 'player-name';
                nameSpan.textContent = p.nickname;
                row.appendChild(nameSpan);
                if (!isMe && !myTeam) {
                    const btn = document.createElement('button');
                    btn.textContent = UI.form_team;
                    btn.className = 'btn btn-primary btn-sm';
                    btn.onclick = () => socket.emit('form_team', { target_sid: p.sid });
                    row.appendChild(btn);
                }
                list.appendChild(row);
            });
        }
    } else {
        if (filteredPlayers.length === 0) {
            list.innerHTML = `<div class="empty-hint">${UI.no_other_players}</div>`;
        } else {
            filteredPlayers.forEach(p => {
                const row = document.createElement('div');
                row.className = 'lobby-player-row';
                const isMe = p.sid === mySid;
                const nameSpan = document.createElement('span');
                nameSpan.className = isMe ? 'player-name player-self' : 'player-name';
                nameSpan.textContent = p.nickname;
                row.appendChild(nameSpan);
                if (!isMe) {
                    const btn = document.createElement('button');
                    btn.textContent = UI.invite;
                    btn.className = 'btn btn-primary';
                    btn.onclick = () => {
                        console.log('[client] invite target_sid=', p.sid);
                        socket.emit('invite', { target_sid: p.sid });
                        updateStatus(UI.invite_sent);
                    };
                    row.appendChild(btn);
                }
                list.appendChild(row);
            });
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
                let gameLabel;
                if (g.mode === '2v2') {
                    gameLabel = `${g.player1} & ${g.player2} vs ${g.player3 || '?'} & ${g.player4 || '?'} (${UI.round}${g.round})`;
                } else if (g.mode === 'urf') {
                    gameLabel = `${g.player1} vs ${g.player2} [${UI.mode_urf || 'Infinite Fire'}] (${UI.round}${g.round})`;
                } else {
                    gameLabel = `${g.player1} vs ${g.player2} (${UI.round}${g.round})`;
                }
                row.innerHTML = `<span>${gameLabel}</span>`;
                const btn = document.createElement('button');
                btn.textContent = UI.spectate;
                btn.className = 'btn btn-secondary';
                btn.onclick = () => socket.emit('spectate', { room_id: g.room_id });
                row.appendChild(btn);
                gamesList.appendChild(row);
            });
        } else {
            gamesList.innerHTML = `<div class="empty-hint">${UI.no_games}</div>`;
        }
    }
    updateStatus(UI.lobby_status.replace('{0}', nickname));
}

function renderDraft(data, isReroll) {
    showView('view-draft');
    const picks = data.picks || [];
    const options = data.options || [];
    const rerolls = data.rerolls || 0;
    const round = data.round || 0;
    const totalRounds = data.total_rounds || 15;
    const is2v2 = data.mode === '2v2';
    const oppPicksCount = data.opponent_picks_count || 0;
    const othersPicksCount = data.others_picks_count || {};
    const prevPicks = draftState ? (draftState.picks || []).length : -1;
    const iJustPicked = picks.length > prevPicks;
    const shouldAnimate = isReroll || iJustPicked;
    const info = $('draft-info');
    if (info) {
        if (is2v2) {
            const pNames = data.player_names || [];
            const othersInfo = Object.entries(othersPicksCount).map(([idx, cnt]) => {
                const pidx = parseInt(idx);
                const name = pNames[pidx] || `P${pidx + 1}`;
                return `${name}: ${cnt}/${totalRounds}`;
            }).join(' | ');
            if (picks.length >= totalRounds) {
                info.textContent = `${UI.draft_complete} | ${othersInfo}`;
            } else {
                info.textContent = `${UI.draft_info} ${round}/${totalRounds} | ${UI.draft_reroll}: ${rerolls} | ${othersInfo}`;
            }
        } else {
            if (picks.length >= totalRounds) {
                info.textContent = `${UI.draft_complete} | ${UI.waiting_opponent}: ${oppPicksCount}`;
            } else {
                info.textContent = `${UI.draft_info} ${round}/${totalRounds} | ${UI.draft_reroll}: ${rerolls} | ${UI.waiting_opponent}: ${oppPicksCount}`;
            }
        }
    }
    const optionsEl = $('draft-options');
    if (optionsEl) {
        optionsEl.innerHTML = '';
        if (picks.length >= totalRounds) {
            optionsEl.innerHTML = `<div class="empty-hint">${UI.draft_waiting}</div>`;
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
    const picksEl = $('draft-picks');
    if (picksEl) {
        picksEl.innerHTML = '';
        picks.forEach(defId => {
            const cardDef = getCardDef(defId);
            const tag = document.createElement('span');
            tag.className = 'pick-tag';
            tag.textContent = cardDef ? getCardName(cardDef) : defId;
            tag.style.borderColor = cardDef ? (CARD_TYPE_COLORS[cardDef.card_type] || COLORS.border_color) : COLORS.border_color;
            picksEl.appendChild(tag);
        });
    }
    const rerollBtn = $('btn-draft-reroll');
    if (rerollBtn) {
        const canReroll = rerolls > 0 && picks.length < totalRounds;
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
    const events = data.events || [];
    const oppSelected = data.opponent_selected;
    const myPick = data.my_pick;
    const is2v2 = data.mode === '2v2';
    const othersSelected = data.others_selected || {};
    const container = $('event-options');
    if (!container) return;
    container.innerHTML = '';
    if (myPick != null) {
        let eventName = '?';
        for (const ev of events) {
            if (ev && ev.id === myPick) { eventName = getLocalizedEventText(ev, 'name') || '?'; break; }
        }
        let othersStatusHtml = '';
        if (is2v2) {
            const pNames = data.player_names || [];
            othersStatusHtml = Object.entries(othersSelected).map(([idx, sel]) => {
                const pidx = parseInt(idx);
                const name = pNames[pidx] || `P${pidx + 1}`;
                return sel ? `<span style="color:var(--color-health)">${name} ✓</span>` : `<span style="color:var(--text-secondary)">${name} ...</span>`;
            }).join(' ');
        } else {
            othersStatusHtml = !oppSelected ? `<div class="waiting-msg">${UI.waiting_opponent}</div>` : `<div class="waiting-msg">${UI.opponent_selected}</div>`;
        }
        container.innerHTML = `
            <div class="event-selected">${UI.event_selected.replace('{0}', eventName)}</div>
            <div class="waiting-msg">${othersStatusHtml}</div>
        `;
        return;
    }
    const oppStatus = document.createElement('div');
    oppStatus.className = 'waiting-msg';
    if (is2v2) {
        const pNames = data.player_names || [];
        const statusParts = Object.entries(othersSelected).map(([idx, sel]) => {
            const pidx = parseInt(idx);
            const name = pNames[pidx] || `P${pidx + 1}`;
            return sel ? `<span style="color:var(--color-health)">${name} ✓</span>` : `<span style="color:var(--text-secondary)">${name} ...</span>`;
        });
        oppStatus.innerHTML = statusParts.join(' ');
    } else {
        oppStatus.textContent = oppSelected ? UI.opponent_selected : UI.opponent_selecting;
    }
    oppStatus.style.width = '100%';
    oppStatus.style.textAlign = 'center';
    oppStatus.style.marginBottom = '8px';
    container.appendChild(oppStatus);
    const eventsRow = document.createElement('div');
    eventsRow.className = 'event-options';
    events.forEach((ev, i) => {
        if (!ev) return;
        const borderColors = { 1: COLORS.health, 2: COLORS.magic, 3: COLORS.magic, 4: COLORS.fire, 5: COLORS.fire, 6: COLORS.fire, 7: COLORS.fire, 8: COLORS.magic };
        const bc = borderColors[ev.id] || COLORS.magic;
        const card = document.createElement('div');
        card.className = 'event-card';
        card.style.borderColor = bc;

        card.innerHTML = `
            <div class="event-header" style="background:${bc}"><span>${i + 1}. ${getLocalizedEventText(ev, 'name') || '?'}</span></div>
            <div class="event-desc">${getLocalizedEventText(ev, 'desc') || ''}</div>
        `;
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
}

async function onEventSelect(eventId) {
    let subChoice = null;
    if (eventId === 2) {
        subChoice = await showMagicConversionFlow();
        if (subChoice === false) return;
    } else if (eventId === 3) {
        subChoice = await showLightConversionChoice();
        if (subChoice === false) return;
    } else if (eventId === 8) {
        subChoice = await showYggdrasilConversionChoice();
        if (subChoice === false) return;
    }
    socket.emit('select_opening_event', { event_id: eventId, sub_choice: subChoice });
    updateStatus(UI.event_waiting);
}

async function showMagicConversionFlow() {
    const data = eventSelectData;
    const magicOptionsAll = data.magic_options || [];
    const draftPicks = data.draft_picks || [];
    if (!magicOptionsAll.length || !draftPicks.length) return null;
    const counts = {};
    draftPicks.forEach(d => { counts[d] = (counts[d] || 0) + 1; });
    const cardTypes = Object.keys(counts).sort((a, b) => (getCardName(getCardDef(a)) || a).localeCompare(getCardName(getCardDef(b)) || b));
    const countOptions = [];
    for (let i = 1; i < Math.min(4, cardTypes.length + 1); i++) countOptions.push(String(i));
    const convertCountIdx = await gamePrompt(UI.choose_convert_count, countOptions);
    if (convertCountIdx < 0) return false;
    const convertCount = convertCountIdx + 1;
    const conversions = [];
    const remainingCounts = { ...counts };
    for (let i = 0; i < convertCount; i++) {
        const magicOptions = magicOptionsAll[i] || magicOptionsAll[magicOptionsAll.length - 1] || [];
        const magicDisplay = magicOptions.map(did => {
            const cd = getCardDef(did);
            return cd ? `${getCardName(cd)} (${cd.cost_e}E/${cd.cost_m}M) ${getCardEffectText(cd)}` : did;
        });
        const magicSel = await gamePrompt(UI.choose_magic_card_n.replace('{0}', i + 1), magicDisplay);
        if (magicSel < 0) return false;
        const availableTypes = cardTypes.filter(d => (remainingCounts[d] || 0) > 0);
        const availableDisplay = availableTypes.map(did => {
            const cd = getCardDef(did);
            return cd ? `${getCardName(cd)} (x${remainingCounts[did]})` : did;
        });
        const sourceSel = await gamePrompt(UI.choose_source_card_n.replace('{0}', i + 1), availableDisplay);
        if (sourceSel < 0) return false;
        remainingCounts[availableTypes[sourceSel]] = (remainingCounts[availableTypes[sourceSel]] || 0) - 1;
        conversions.push({ magic_def_id: magicOptions[magicSel], source_def_id: availableTypes[sourceSel] });
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
            label.textContent = `${cd ? getCardName(cd) : did} (x${cnt})`;
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
        cancelBtn.textContent = UI.cancel;
        cancelBtn.onclick = () => {
            el.classList.remove('active');
            resolve(null);
        };
        const confirmBtn = document.createElement('button');
        confirmBtn.className = 'btn btn-primary';
        confirmBtn.textContent = UI.ok;
        confirmBtn.style.marginLeft = '8px';
        confirmBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            el.classList.remove('active');
            const convertDefIds = [];
            let total = 0;
            entries.forEach(([did, cnt]) => {
                const val = Math.min(parseInt(inputs[did].value) || 0, Math.min(cnt, MAX_TOTAL - total));
                for (let i = 0; i < val; i++) convertDefIds.push(did);
                total += val;
            });
            resolve(convertDefIds.length ? { convert_def_ids: convertDefIds } : null);
        });
        cancelBtn.parentNode.appendChild(confirmBtn);
        const cleanup = () => {
            if (confirmBtn.parentNode) confirmBtn.parentNode.removeChild(confirmBtn);
        };
        const origCancelClick = cancelBtn.onclick;
        cancelBtn.onclick = () => { cleanup(); origCancelClick(); };
        confirmBtn.addEventListener('click', () => { cleanup(); }, { once: true });
        el.classList.add('active');
    });
}

async function showYggdrasilConversionChoice() {
    const draftPicks = eventSelectData.draft_picks || [];
    const counts = {};
    draftPicks.forEach(d => { if (d !== 'Yggdrasil') counts[d] = (counts[d] || 0) + 1; });
    const options = Object.keys(counts).sort((a, b) => (getCardName(getCardDef(a)) || a).localeCompare(getCardName(getCardDef(b)) || b));
    const display = options.map(did => {
        const cd = getCardDef(did);
        return cd ? `${getCardName(cd)} (x${counts[did]})` : did;
    });
    const sel = await gamePrompt(UI.choose_yggdrasil_card, display);
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
    const display = entries.map(([did, cnt]) => {
        const cd = getCardDef(did);
        return `${cd ? getCardName(cd) : did} x${cnt}`;
    });
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
    
    console.log('[LAYOUT DEBUG] =====');
    console.log('[LAYOUT DEBUG] app: display=', app ? getComputedStyle(app).display : '?', 
                'height=', app ? app.clientHeight : '?',
                'computedH=', app ? getComputedStyle(app).height : '?');
    console.log('[LAYOUT DEBUG] view-game: display=', view ? getComputedStyle(view).display : '?',
                'flex=', view ? getComputedStyle(view).flex : '?',
                'height=', view ? view.clientHeight : '?',
                'computedH=', view ? getComputedStyle(view).height : '?');
    console.log('[LAYOUT DEBUG] game-container: display=', gc ? getComputedStyle(gc).display : '?',
                'gridRows=', gc ? getComputedStyle(gc).gridTemplateRows : '?',
                'height=', gc ? gc.clientHeight : '?',
                'computedH=', gc ? getComputedStyle(gc).height : '?');
    console.log('[LAYOUT DEBUG] opp-section: gridRow=', oppSection ? getComputedStyle(oppSection).gridRow : '?',
                'height=', oppSection ? oppSection.offsetHeight : '?');
    console.log('[LAYOUT DEBUG] middle-section: gridRow=', middleSection ? getComputedStyle(middleSection).gridRow : '?',
                'display=', middleSection ? getComputedStyle(middleSection).display : '?',
                'flexDir=', middleSection ? getComputedStyle(middleSection).flexDirection : '?',
                'height=', middleSection ? middleSection.offsetHeight : '?',
                'computedH=', middleSection ? getComputedStyle(middleSection).height : '?');
    console.log('[LAYOUT DEBUG] player-section: gridRow=', playerSection ? getComputedStyle(playerSection).gridRow : '?',
                'height=', playerSection ? playerSection.offsetHeight : '?');
    console.log('[LAYOUT DEBUG] battle-log: flex=', battleLog ? getComputedStyle(battleLog).flex : '?',
                'height=', battleLog ? battleLog.offsetHeight : '?',
                'computedH=', battleLog ? getComputedStyle(battleLog).height : '?');
    console.log('[LAYOUT DEBUG] log-header: height=', logHeader ? logHeader.offsetHeight : '?');
    console.log('[LAYOUT DEBUG] log-content: flex=', logContent ? getComputedStyle(logContent).flex : '?',
                'maxHeight=', logContent ? getComputedStyle(logContent).maxHeight : '?',
                'height=', logContent ? logContent.offsetHeight : '?',
                'computedH=', logContent ? getComputedStyle(logContent).height : '?');
    console.log('[LAYOUT DEBUG] sum=', (oppSection ? oppSection.offsetHeight : 0) + (middleSection ? middleSection.offsetHeight : 0) + (playerSection ? playerSection.offsetHeight : 0));
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

function updateModeSpecificControls(gs) {
    const inSoloGame = !!gs?.solo;
    const gameOver = gs?.phase === 'game_over';
    const soloNextDrawBtn = $('btn-solo-next-draw');
    const soloEditBtn = $('btn-solo-edit');
    const viewDeckBtn = $('btn-view-deck');
    const urfReplaceBtn = $('btn-urf-replace');
    const urfSellBtn = $('btn-urf-sell');
    const surrenderBtn = $('btn-surrender');
    const spectateControls = $('spectate-controls');
    const gameControls = $('game-controls');
    const playZone = $('play-zone');

    const showSoloNextDraw = inSoloGame && !gameOver && !isSpectating;
    const showSoloEdit = inSoloGame && !isSpectating;
    const showSpectateControls = !!isSpectating;
    const showGameControls = !isSpectating;
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
        const showSurrender = !(inSoloGame && gameOver);
        surrenderBtn.classList.toggle('hidden', !showSurrender);
        surrenderBtn.style.display = showSurrender ? '' : 'none';
    }
    if (viewDeckBtn) {
        const showViewDeck = gs?.mode !== 'urf';
        viewDeckBtn.classList.toggle('hidden', !showViewDeck);
        viewDeckBtn.style.display = showViewDeck ? '' : 'none';
    }
    if (urfReplaceBtn) {
        const show = gs?.mode === 'urf' && !isSpectating && !gameOver;
        urfReplaceBtn.textContent = UI.urf_replace || '替换手牌';
        urfReplaceBtn.classList.toggle('hidden', !show);
        urfReplaceBtn.style.display = show ? '' : 'none';
        urfReplaceBtn.disabled = !isMyTurn() || !gs?.urf_replace_available;
    }
    if (urfSellBtn) {
        const show = gs?.mode === 'urf' && !isSpectating && !gameOver;
        urfSellBtn.textContent = UI.urf_sell || '售卖装备';
        urfSellBtn.classList.toggle('hidden', !show);
        urfSellBtn.style.display = show ? '' : 'none';
        urfSellBtn.disabled = !isMyTurn() || !gs?.urf_sell_available || !((gs.you || {}).equipment || []).length;
    }
    if (spectateControls) {
        spectateControls.classList.toggle('hidden', !showSpectateControls);
        spectateControls.style.display = showSpectateControls ? '' : 'none';
    }
    const switchBtn = $('btn-switch-perspective');
    if (switchBtn) {
        switchBtn.classList.add('hidden');
        switchBtn.style.display = 'none';
    }
    if (gameControls) gameControls.style.display = showGameControls ? '' : 'none';
    if (playZone) playZone.style.display = showPlayZone ? '' : 'none';
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
    console.log('[RENDER] renderGame: phase=', gs.phase, 'current_player=', gs.current_player, 'playerId=', playerId, 'myTurn=', myTurn, 'is2v2=', is2v2);

    const gameContainer = document.querySelector('.game-container');
    if (gameContainer) {
        if (is2v2) {
            gameContainer.classList.add('mode-2v2');
        } else {
            gameContainer.classList.remove('mode-2v2');
        }
        gameContainer.classList.toggle('mode-spectate', !!isSpectating);
    }

    const opp2Half = $('opp2-half');
    const oppDivider = $('opp-divider');
    const teammateSidebar = $('teammate-sidebar');
    if (opp2Half) opp2Half.classList.toggle('hidden', !is2v2);
    if (oppDivider) oppDivider.classList.toggle('hidden', !is2v2);
    if (teammateSidebar) teammateSidebar.classList.toggle('hidden', !is2v2);

    const oppLabel = $('opp-label');
    const youLabel = $('you-label');
    if (isSpectating) {
        if (is2v2) {
            if (youLabel) youLabel.textContent = gs.your_name || gs.player1_name || 'P1';
            if (oppLabel) oppLabel.textContent = (gs.opponent_names || [])[0] || gs.player3_name || 'P3';
            const opp2Label = $('opp2-label');
            if (opp2Label) opp2Label.textContent = (gs.opponent_names || [])[1] || gs.player4_name || 'P4';
            const tmLabel = $('teammate-label');
            if (tmLabel) tmLabel.textContent = gs.teammate_name || gs.player2_name || 'P2';
        } else {
            if (oppLabel) oppLabel.textContent = gs.opponent_name || gs.player2_name || 'P2';
            if (youLabel) youLabel.textContent = gs.your_name || gs.player1_name || 'P1';
        }
    } else if (is2v2) {
        const oppNames = gs.opponent_names || [];
        if (oppLabel) oppLabel.textContent = oppNames[0] || UI.opponent;
        const opp2Label = $('opp2-label');
        if (opp2Label) opp2Label.textContent = oppNames[1] || (UI.opponent + '2');
        const tmLabel = $('teammate-label');
        if (tmLabel) tmLabel.textContent = gs.teammate_name || UI.teammate;
        if (youLabel) youLabel.textContent = gs.your_name || UI.you;
    } else {
        if (oppLabel) oppLabel.textContent = gs.opponent_name || UI.opponent;
        if (youLabel) youLabel.textContent = gs.your_name || UI.you;
    }
    if (!!gs.solo && gs.phase === 'game_over') {
        const winner = gs.winner;
        const youResult = winner === -1 ? UI.draw : (winner === playerId ? UI.victory : UI.defeat);
        const oppResult = winner === -1 ? UI.draw : (winner === playerId ? UI.defeat : UI.victory);
        if (youLabel) youLabel.textContent = `${gs.your_name || UI.you} - ${youResult}`;
        if (oppLabel) oppLabel.textContent = `${gs.opponent_name || UI.opponent} - ${oppResult}`;
    }

    renderPlayerBars('opp-bars', opp);
    renderPlayerBars('you-bars', you);
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
        if (opp2Info) opp2Info.textContent = UI.hand_deck_info_opp.replace('{0}', opp2.hand_count || 0).replace('{1}', opp2.deck_count || 0);
        const tmInfo = $('teammate-info');
        if (tmInfo) tmInfo.textContent = UI.hand_deck_discard_info.replace('{0}', teammate.hand_count || 0).replace('{1}', teammate.deck_count || 0).replace('{2}', teammate.discard_count || 0);
    }

    renderLog(gs.log || [], gs.log_start || 0, gs.log_total);

    let phaseText;
    if (is2v2) {
        const cpName = gs.current_player === playerId ? (gs.your_name || UI.you) :
            (gs.current_player === gs.teammate_id ? (gs.teammate_name || UI.teammate) :
            ((gs.opponent_names || [])[gs.enemy_ids ? gs.enemy_ids.indexOf(gs.current_player) : -1] || '...'));
        phaseText = gs.phase === 'action' ? (myTurn ? UI.your_turn : `${UI.opponent_turn}：${cpName}`)
            : gs.phase === 'draw' ? UI.draw_phase
            : gs.phase === 'game_over' ? UI.game_over : '';
    } else {
        phaseText = gs.phase === 'action' ? (myTurn ? UI.your_turn : UI.opponent_turn)
            : gs.phase === 'draw' ? UI.draw_phase
            : gs.phase === 'game_over' ? UI.game_over : '';
    }
    updateStatus(UI.round_status.replace('{0}', gs.round_num || 0).replace('{1}', phaseText));

    const endTurnBtn = $('btn-end-turn');
    if (endTurnBtn) {
        endTurnBtn.disabled = !myTurn || isSpectating || gs.phase === 'game_over';
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
    if (oppInfo) oppInfo.textContent = UI.hand_deck_info_opp.replace('{0}', opp.hand_count || 0).replace('{1}', opp.deck_count || 0);
    const youInfo = $('you-info');
    if (youInfo) youInfo.textContent = UI.hand_deck_discard_info.replace('{0}', you.hand_count || 0).replace('{1}', you.deck_count || 0).replace('{2}', you.discard_count || 0);
    scheduleAdjust();
}

function renderPlayerBars(containerId, playerData) {
    const container = $(containerId);
    if (!container) return;
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
        const fill = wrappers[i].querySelector('.bar-fill');
        const text = wrappers[i].querySelector('.bar-text');
        const pct = bar.max > 0 ? Math.max(0, Math.min(100, (bar.cur / bar.max) * 100)) : 0;
        if (fill) fill.style.width = pct + '%';
        if (text) text.textContent = `${bar.cur}/${bar.max}`;
    });
}

function renderStatusTags(containerId, playerData) {
    const container = $(containerId);
    if (!container) return;
    container.innerHTML = '';
    const tags = [];
    const p = playerData;
    if (p.poison > 0) tags.push({ name: UI.status_poison, val: p.poison, fg: COLORS.poison, bg: COLORS.poison_bg });
    if (p.fire > 0) tags.push({ name: UI.status_fire, val: p.fire, fg: COLORS.fire, bg: COLORS.fire_bg });
    if (p.toxic > 0) tags.push({ name: UI.status_toxic, val: p.toxic, fg: '#6C3483', bg: '#F4ECF7' });
    if (p.triangle_stacks > 0) tags.push({ name: UI.status_triangle, val: p.triangle_stacks, fg: COLORS.non_stack, bg: COLORS.non_stack_bg });
    if (p.dodge > 0) tags.push({ name: UI.status_dodge, val: p.dodge, fg: COLORS.guard, bg: COLORS.guard_bg });
    if (p.nazar_active) tags.push({ name: UI.status_nazar, val: `${p.nazar_big_hits || 0}/2`, fg: COLORS.magic_text, bg: COLORS.magic_bg });
    if (p.equipment_protection > 0) tags.push({ name: UI.status_equip_protect, val: p.equipment_protection, fg: COLORS.indestructible, bg: COLORS.indestructible_bg });
    if (p.invincible) tags.push({ name: UI.status_invincible, val: '', fg: COLORS.elixir_text, bg: COLORS.elixir_bg });
    if (p.skip_turn) tags.push({ name: UI.status_stunned, val: '', fg: COLORS.damage, bg: COLORS.damage_bg });
    if (p.attack_blocked > 0) tags.push({ name: UI.status_attack_blocked, val: p.attack_blocked, fg: '#C0392B', bg: '#FDEDEC' });
    if (p.attack_only > 0) tags.push({ name: UI.status_attack_only, val: p.attack_only, fg: '#D35400', bg: '#FEF5E7' });
    if (p.untargetable) tags.push({ name: UI.status_untargetable, val: '', fg: '#1A5276', bg: '#EBF5FB' });
    if (p.bandage_active) tags.push({ name: UI.status_bandage, val: '', fg: '#1E8449', bg: '#E8F8F5' });
    if (p.sponge_active) tags.push({ name: UI.status_sponge, val: '', fg: '#6C3483', bg: '#F4ECF7' });
    if (p.shovel_active) tags.push({ name: UI.status_shovel, val: '', fg: '#5D4037', bg: '#EFEBE9' });
    tags.forEach(t => {
        const el = document.createElement('span');
        el.className = 'status-tag';
        el.style.color = t.fg;
        el.style.background = t.bg;
        el.textContent = t.val ? `${t.name}:${t.val}` : t.name;
        container.appendChild(el);
    });
}

function renderOppHand(oppData, containerId = 'opp-hand') {
    const container = $(containerId);
    if (!container) return;
    container.innerHTML = '';
    const revealedHand = oppData.revealed_hand || oppData.hand;
    if (revealedHand && revealedHand.length > 0) {
        revealedHand.forEach(cd => {
            const card = createCardElement(cd, { small: true });
            container.appendChild(card);
        });
    } else {
        const count = oppData.hand_count || 0;
        for (let i = 0; i < count; i++) {
            const card = createCardElement({}, { faceDown: true, small: true });
            container.appendChild(card);
        }
    }
}

function renderTeammateHand(teammateData) {
    const container = $('teammate-hand');
    if (!container) return;
    container.innerHTML = '';
    const hand = teammateData.hand || [];
    hand.forEach(card => {
        const el = createCardElement(card, { small: true });
        el.style.cursor = 'default';
        container.appendChild(el);
    });
}

function renderPlayerHand(playerData) {
    const container = $('you-hand');
    if (!container) return;
    container.innerHTML = '';
    const hand = playerData.hand || [];
    const myTurn = isMyTurn();
    hand.forEach(cardDict => {
        const cardDef = getCardDef(cardDict.def_id);
        const canPlay = myTurn && canPlayCard(cardDict);
        const card = createCardElement(cardDict, {
            draggable: !isSpectating && canPlay && cardDef && cardDef.card_type !== 'guard',
        });
        if (!canPlay) {
            card.classList.add('card-disabled');
        }
        container.appendChild(card);
    });
}

function canPlayCard(cardDict) {
    const gs = gameState;
    const you = gs.you || {};
    if (gs.phase !== 'action') return false;
    if (!isMyTurn()) return false;
    if (you.shovel_active) return false;
    const cardDef = getCardDef(cardDict.def_id);
    if (!cardDef) return false;
    if (cardDef.card_type === 'guard') return false;
    if ((you.attack_blocked || 0) > 0 && cardDef.card_type === 'thorn') return false;
    if ((you.attack_only || 0) > 0 && cardDef.card_type !== 'thorn') return false;
    const elixir = you.elixir || 0;
    const magic = you.magic || 0;
    const { totalE, totalM } = getCardDisplayCosts(cardDict, cardDef, you);
    if (totalE > elixir) return false;
    if (totalM > magic) return false;
    return true;
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
            label: `${names[i] || (UI.opponent + (i + 1))} H:${data.health || 0}/${data.max_health || 0}`,
            alive: (data.health || 0) > 0
        };
    }).filter(x => x.alive);
}

function getPlayerNameById(id) {
    if (!gameState) return `P${Number(id) + 1}`;
    if (id === gameState.your_id) return gameState.your_name || UI.you;
    if (id === gameState.teammate_id) return gameState.teammate_name || UI.teammate;
    const enemyIndex = (gameState.enemy_ids || []).indexOf(id);
    if (enemyIndex >= 0) return (gameState.opponent_names || [])[enemyIndex] || `${UI.opponent}${enemyIndex + 1}`;
    return `P${Number(id) + 1}`;
}

function getPlayerDataById(id) {
    if (!gameState) return {};
    if (id === gameState.your_id) return gameState.you || {};
    if (id === gameState.teammate_id) return gameState.teammate || {};
    const enemyIndex = (gameState.enemy_ids || []).indexOf(id);
    if (enemyIndex === 0) return gameState.opponent || {};
    if (enemyIndex === 1) return gameState.opponent2 || {};
    return {};
}

function getPlayerTargetOptions({ includeSelf = true, aliveOnly = true } = {}) {
    if (!gameState || gameState.mode !== '2v2') return [];
    const out = [];
    const add = (id, data, group) => {
        if (id == null || (!includeSelf && id === gameState.your_id)) return;
        const alive = (data && Number(data.health || 0) > 0);
        if (aliveOnly && !alive) return;
        out.push({
            id,
            group,
            label: `${group} ${getPlayerNameById(id)} H:${data ? (data.health || 0) : 0}/${data ? (data.max_health || 0) : 0}`,
            alive
        });
    };
    const enemies = [gameState.opponent || {}, gameState.opponent2 || {}];
    (gameState.enemy_ids || []).forEach((id, i) => add(id, enemies[i], UI.enemy_label || UI.opponent));
    if (gameState.teammate_id != null) add(gameState.teammate_id, gameState.teammate || {}, UI.ally_label || UI.teammate);
    add(gameState.your_id, gameState.you || {}, UI.you);
    return out;
}

async function choosePlayerTarget(title, opts = {}) {
    const targets = getPlayerTargetOptions(opts);
    if (!targets.length) {
        gameAlert(UI.notice, UI.no_valid_target || 'No valid target');
        return -1;
    }
    if (targets.length === 1) return targets[0].id;
    const sel = await simpleChoice(title || UI.choose_target || UI.select_target || 'Choose target', targets.map(t => t.label));
    return sel >= 0 ? targets[sel].id : -1;
}

async function chooseEnemyTarget(title) {
    const targets = getEnemyTargetOptions();
    if (!targets.length) {
        gameAlert(UI.notice, UI.no_valid_target || 'No valid target');
        return -1;
    }
    if (targets.length === 1) return targets[0].id;
    const sel = await simpleChoice(title || UI.choose_target || UI.select_target || 'Choose target', targets.map(t => t.label));
    return sel >= 0 ? targets[sel].id : -1;
}

function cardNeedsPlayerTarget(cardDef) {
    if (!cardDef) return false;
    if ((cardDef.flags || []).includes('self_only')) return false;
    if (cardDef.card_type === 'guard') return false;
    if (gs.mode === 'urf' && cardDef.card_type === 'root' && ((you.equipment || []).length >= 3)) return false;
    if (cardDef.card_type === 'root' && Number(cardDef.trigger_cost_e) >= 0) return false;
    if (['thorn', 'bloom', 'root'].includes(cardDef.card_type)) return true;
    return false;
}

function cardNeedsEnemyPlayerTarget(cardDef) {
    if (!cardDef) return false;
    if (cardDef.card_type === 'thorn') return true;
    const ids = new Set(['Iris', 'Fire', 'Cancer']);
    if (ids.has(cardDef.id)) return true;
    const effects = Array.isArray(cardDef.effects) ? cardDef.effects : [];
    return effects.some(effect => {
        const params = effect && effect.params ? effect.params : {};
        const target = params.target || params.targets || params.target1 || params.target2;
        return ['enemy', 'all_enemies', 'random_enemy'].includes(target);
    });
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
        const targetId = eqDict.effect_target;
        const targetSuffix = gameState && gameState.mode === '2v2' && targetId != null && targetId !== (playerData.player_id ?? eqDict.owner)
            ? `→${getPlayerNameById(targetId)}`
            : '';
        let text = UI.equip_info.replace('{0}', `${getCardName(cardDef)}${targetSuffix ? `(${targetSuffix})` : ''}`).replace('{1}', turns);
        if (corruption) text += UI.equip_corruption;
        if (cardDef.trigger_cost_e >= 0 && isMyEquipment && turns >= 1 && isFriendlyTurn() && !isSpectating) {
            const btn = document.createElement('button');
            btn.className = 'btn btn-small btn-equip-trigger';
            btn.textContent = UI.equip_trigger_cost.replace('{0}', text).replace('{1}', cardDef.trigger_cost_e);
            btn.onclick = async () => {
                const payload = { equipment_instance_id: cardInst.instance_id };
                if (gameState && gameState.mode === '2v2' && ['Leaf', 'Mark', 'Mine'].includes(cardDef.id)) {
                    const targetId = await choosePlayerTarget(UI.choose_target || UI.select_target || 'Choose target');
                    if (targetId < 0) return;
                    payload.target_player_id = targetId;
                }
                socket.emit(soloMode ? 'solo_use_trigger' : 'use_trigger', payload);
            };
            container.appendChild(btn);
        } else {
            el.textContent = text;
            container.appendChild(el);
        }
    });
}

function renderLog(log, logStart = 0, logTotal = null) {
    const container = $('battle-log');
    if (!container) return;
    let content = container.querySelector('.log-content');
    if (!content) {
        content = document.createElement('div');
        content.className = 'log-content';
        container.appendChild(content);
    }
    const wasAtBottom = content.scrollTop + content.clientHeight >= content.scrollHeight - 30;
    if (!Array.isArray(log)) log = [];
    logStart = Number.isFinite(Number(logStart)) ? Number(logStart) : 0;
    logTotal = Number.isFinite(Number(logTotal)) ? Number(logTotal) : logStart + log.length;
    if (logTotal < renderedBattleLogTotal || logStart > renderedBattleLogTotal) {
        gameTimelineEntries = gameTimelineEntries.filter(entry => entry.type === 'chat');
        renderedBattleLogCount = 0;
        renderedBattleLogTotal = logStart;
    }
    let startIndex = Math.max(0, renderedBattleLogTotal - logStart);
    if (startIndex > log.length) startIndex = 0;
    for (let i = startIndex; i < log.length; i++) {
        gameTimelineEntries.push({ type: 'battle', text: log[i] });
    }
    renderedBattleLogCount = log.length;
    renderedBattleLogTotal = logTotal;
    if (gameTimelineEntries.length > 200) {
        gameTimelineEntries = gameTimelineEntries.slice(-200);
    }
    content.innerHTML = '';
    gameTimelineEntries.forEach(entry => {
        const el = document.createElement('div');
        if (entry.type === 'chat') {
            el.className = 'log-entry log-chat';
            const nameSpan = document.createElement('span');
            nameSpan.className = 'chat-nick';
            nameSpan.textContent = `${entry.nick}: `;
            el.appendChild(nameSpan);
            el.appendChild(document.createTextNode(entry.text));
        } else {
            const line = entry.text || '';
            const displayLine = translateLogLine(line);
            const styleLine = String(displayLine || line).toLowerCase();
            el.className = 'log-entry';
            if (styleLine.includes('造成') || styleLine.includes('伤害') || styleLine.includes('damage') || styleLine.includes('degats') || styleLine.includes('dano') || styleLine.includes('урон') || styleLine.includes('ダメージ') || line.includes('D')) el.classList.add('log-damage');
            else if (styleLine.includes('+h') || styleLine.includes('回复') || styleLine.includes('recover') || styleLine.includes('récup') || styleLine.includes('recupera') || styleLine.includes('восстан') || styleLine.includes('回復')) el.classList.add('log-heal');
            else if (styleLine.includes('中毒') || styleLine.includes('poison') || styleLine.includes('veneno') || styleLine.includes('яд') || styleLine.includes('毒')) el.classList.add('log-poison');
            else if (styleLine.includes('灼烧') || styleLine.includes('burn') || styleLine.includes('brûl') || styleLine.includes('queima') || styleLine.includes('ожог') || styleLine.includes('火傷')) el.classList.add('log-fire');
            else if (styleLine.includes('+e') || styleLine.includes('能量') || styleLine.includes('energy') || styleLine.includes('énergie') || styleLine.includes('energia') || styleLine.includes('энерг') || styleLine.includes('e回復')) el.classList.add('log-elixir');
            else if (styleLine.includes('+m') || styleLine.includes('魔力') || styleLine.includes('magic') || styleLine.includes('magie') || styleLine.includes('mana') || styleLine.includes('маг') || styleLine.includes('マジック')) el.classList.add('log-magic');
            else if (line.includes('===')) el.classList.add('log-round');
            el.textContent = displayLine;
        }
        content.appendChild(el);
    });
    if (wasAtBottom) content.scrollTop = content.scrollHeight;
}

function appendLobbyChat(nick, text) {
    const container = $('lobby-chat-log');
    if (!container) return;
    const el = document.createElement('div');
    el.className = 'chat-msg';
    const nameSpan = document.createElement('span');
    nameSpan.className = 'chat-nick';
    nameSpan.textContent = `${nick}: `;
    el.appendChild(nameSpan);
    el.appendChild(document.createTextNode(text));
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
}

function appendGameChat(nick, text) {
    gameTimelineEntries.push({ type: 'chat', nick, text });
    if (gameTimelineEntries.length > 200) gameTimelineEntries = gameTimelineEntries.slice(-200);
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

async function onPlayCard(cardInstanceId) {
    if (isSpectating) return;
    const hand = (gameState.you || {}).hand || [];
    const cardDict = hand.find(c => c.instance_id === cardInstanceId);
    if (!cardDict) return;
    if (!canPlayCard(cardDict)) {
        flashStatus(UI.cannot_play, 2000, 'error');
        return;
    }
    const cardDef = getCardDef(cardDict.def_id);
    let targetPlayerId = -1;
    if (!soloMode && gameState.mode === '2v2' && cardNeedsPlayerTarget(cardDef)) {
        targetPlayerId = await choosePlayerTarget(UI.choose_target || UI.select_target || 'Choose target');
        if (targetPlayerId < 0) return;
    }
    const choice = await getCardChoice(cardDict, targetPlayerId);
    if (choice === false) return;
    pendingPlayCard = cardDict;
    renderPendingCard();
    socket.emit(soloMode ? 'solo_play_card' : 'play_card', { card_instance_id: cardInstanceId, choice, target_player_id: targetPlayerId });
}

async function getCardChoice(cardDict, targetPlayerId = -1) {
    const defId = cardDict.def_id;
    const hand = (gameState.you || {}).hand || [];
    if (defId === 'Fission') {
        const attacks = hand.filter(c => {
            const cd = getCardDef(c.def_id);
            return cd && cd.card_type === 'thorn' && c.instance_id !== cardDict.instance_id;
        });
        if (!attacks.length) { gameAlert(UI.notice, UI.no_attack_cards); return false; }
        const options = attacks.map(a => `${getCardDef(a.def_id) ? getCardName(getCardDef(a.def_id)) : a.def_id}${getCardLayerLabel(a)}`);
        const sel = await simpleChoice(UI.choose_attack_for.replace('{0}', getCardDef(defId) ? getCardName(getCardDef(defId)) : ''), options);
        if (sel < 0) return false;
        return { target_instance_id: attacks[sel].instance_id };
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
        const groupOptions = validGroups.map(([k, v]) => `${getCardDef(k) ? getCardName(getCardDef(k)) : k} x${v.length}`);
        const sel = await simpleChoice(UI.choose_attack_group_for.replace('{0}', getCardDef(defId) ? getCardName(getCardDef(defId)) : ''), groupOptions);
        if (sel < 0) return false;
        const group = validGroups[sel][1];
        const combos = [];
        for (let i = 0; i < group.length; i++) {
            for (let j = i + 1; j < group.length; j++) {
                combos.push([group[i], group[j]]);
                for (let k = j + 1; k < group.length; k++) {
                    combos.push([group[i], group[j], group[k]]);
                }
            }
        }
        const comboOptions = combos.map(combo => combo.map(c => `${getCardDef(c.def_id) ? getCardName(getCardDef(c.def_id)) : c.def_id}${getCardLayerLabel(c)}`).join(' + '));
        const comboSel = await simpleChoice(UI.choose_attack_group_for.replace('{0}', getCardDef(defId) ? getCardName(getCardDef(defId)) : ''), comboOptions);
        if (comboSel < 0) return false;
        return { target_instance_ids: combos[comboSel].map(c => c.instance_id) };
    } else if (defId === 'Mimic') {
        const others = hand.filter(c => c.instance_id !== cardDict.instance_id);
        if (!others.length) { gameAlert(UI.notice, UI.no_attack_cards); return false; }
        const options = others.map(c => getCardDef(c.def_id) ? getCardName(getCardDef(c.def_id)) : c.def_id);
        const sel = await simpleChoice(UI.choose_hand_for.replace('{0}', getCardDef(defId) ? getCardName(getCardDef(defId)) : ''), options);
        if (sel < 0) return false;
        return { target_instance_id: others[sel].instance_id };
    } else if (defId === 'Chromosome') {
        const discard = (gameState.you || {}).discard || [];
        if (!discard.length) { gameAlert(UI.notice, UI.discard_empty); return false; }
        const options = discard.map(c => getCardDef(c.def_id) ? getCardName(getCardDef(c.def_id)) : c.def_id);
        const sel = await simpleChoice(UI.choose_from_discard_for.replace('{0}', getCardDef(defId) ? getCardName(getCardDef(defId)) : ''), options);
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
        const options = destroyable.map(e => getCardDef((e.card_instance || {}).def_id) ? getCardName(getCardDef((e.card_instance || {}).def_id)) : '?');
        const sel = await simpleChoice(UI.choose_equip_for.replace('{0}', getCardDef(defId) ? getCardName(getCardDef(defId)) : ''), options);
        if (sel < 0) return false;
        return { target_instance_id: destroyable[sel].card_instance.instance_id };
    } else if (defId === 'Chilli') {
        const others = hand.filter(c => c.instance_id !== cardDict.instance_id);
        if (others.length) {
            const options = others.map(c => getCardDef(c.def_id) ? getCardName(getCardDef(c.def_id)) : c.def_id);
            const sel = await simpleChoice(UI.choose_discard_for.replace('{0}', getCardDef(defId) ? getCardName(getCardDef(defId)) : ''), options);
            if (sel < 0) return false;
            return { target_instance_id: others[sel].instance_id };
        }
        return null;
    }
    return null;
}

async function simpleChoice(title, options) {
    if (!options.length) return -1;
    const display = options.map((o, i) => `${i + 1}. ${o}`);
    return await gamePrompt(title, display);
}

function showResponseUI(data) {
    if (isSpectating) return;
    const counterCards = data.counter_cards || [];
    const you = gameState.you || {};
    const myElixir = you.elixir || 0;
    const myMagic = you.magic || 0;
    console.log('[RESPONSE] showResponseUI: counterCards=', counterCards.length, 'myElixir=', myElixir, 'myMagic=', myMagic);
    if (!counterCards.length) {
        console.log('[RESPONSE] no counter cards, auto pass');
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
    const cardName = cardDef ? getCardName(cardDef) : cardDict.def_id || '?';
    let triggerDesc = '';
    if (cardDef) {
        if (cardDef.card_type === 'thorn') triggerDesc = UI.enemy_attack;
        else if (cardDef.card_type === 'bloom') triggerDesc = UI.enemy_skill;
        if (cardDef.id === 'Sewage' || cardDef.id === 'MagicSewage') triggerDesc += UI.enemy_destroy_equip;
    }
    const label = document.createElement('div');
    label.className = 'response-label';
    label.textContent = `${triggerDesc}: ${cardName}`;
    container.appendChild(label);
    const btnRow = document.createElement('div');
    btnRow.className = 'response-btn-row';
    cardCosts.forEach(({ cc, ccDef, costE, costM, canAfford }) => {
        if (!ccDef) return;
        const costStr = costM === 0 ? `${costE}E` : `${costE}E/${costM}M`;
        const btn = document.createElement('button');
        btn.className = 'btn ' + (canAfford ? 'btn-primary' : 'btn-counter-disabled');
        btn.textContent = `${getCardName(ccDef)}[${costStr}]`;
        btn.disabled = !canAfford;
        btn.onclick = () => onRespond(cc.instance_id);
        btnRow.appendChild(btn);
    });
    container.appendChild(btnRow);
    responseCountdown = hasAffordable ? 5 : 2;
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
    if (responseTimerId) { clearInterval(responseTimerId); responseTimerId = null; }
    responsePending = false;
    const container = $('response-panel');
    if (container) { container.innerHTML = ''; container.classList.add('hidden'); container.classList.remove('visible'); }
    socket.emit(soloMode ? 'solo_response' : 'response', { card_instance_id: cardInstanceId });
}

function showAllyConsentUI(data) {
    if (isSpectating || !socket) return;
    const container = $('response-panel');
    if (!container) {
        socket.emit('ally_consent_response', { accepted: false });
        return;
    }
    if (allyConsentTimerId) clearInterval(allyConsentTimerId);
    const cardDict = data.card || {};
    const cardDef = getCardDef(cardDict.def_id);
    const cardName = cardDef ? getCardName(cardDef) : (cardDict.def_id || '?');
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
        .replace('{0}', data.from_name || UI.teammate)
        .replace('{1}', cardName);
    container.appendChild(msg);
    const row = document.createElement('div');
    row.className = 'response-btn-row';
    const acceptBtn = document.createElement('button');
    acceptBtn.className = 'btn btn-primary';
    const declineBtn = document.createElement('button');
    declineBtn.className = 'btn btn-danger';
    declineBtn.textContent = UI.ally_decline || UI.decline || 'Decline';
    acceptBtn.onclick = () => respondAllyConsent(true);
    declineBtn.onclick = () => respondAllyConsent(false);
    row.appendChild(acceptBtn);
    row.appendChild(declineBtn);
    container.appendChild(row);
    allyConsentCountdown = 5;
    acceptBtn.textContent = (UI.ally_accept_countdown || 'Accept ({0})').replace('{0}', allyConsentCountdown);
    allyConsentTimerId = setInterval(() => {
        allyConsentCountdown--;
        if (allyConsentCountdown <= 0) {
            respondAllyConsent(false);
            return;
        }
        acceptBtn.textContent = (UI.ally_accept_countdown || 'Accept ({0})').replace('{0}', allyConsentCountdown);
    }, 1000);
}

function respondAllyConsent(accepted) {
    if (allyConsentTimerId) { clearInterval(allyConsentTimerId); allyConsentTimerId = null; }
    const container = $('response-panel');
    if (container) { container.innerHTML = ''; container.classList.add('hidden'); container.classList.remove('visible'); }
    socket.emit('ally_consent_response', { accepted: !!accepted });
}

async function showChoiceUI(data) {
    if (isSpectating) return;
    const choiceType = data.choice_type || '';
    const cardDict = data.card || {};
    const cardDef = getCardDef(cardDict.def_id);
    const cardName = cardDef ? getCardName(cardDef) : '?';
    let choiceResult = null;
    if (choiceType === 'choose_attack_from_hand') {
        const attacks = ((gameState.you || {}).hand || []).filter(c => {
            const cd = getCardDef(c.def_id);
            return cd && cd.card_type === 'thorn';
        });
        if (!attacks.length) { gameAlert(UI.notice, UI.no_attack_cards); }
        else {
            const options = attacks.map(a => `${getCardDef(a.def_id) ? getCardName(getCardDef(a.def_id)) : a.def_id}${getCardLayerLabel(a)}`);
            const sel = await simpleChoice(UI.choose_attack_for.replace('{0}', cardName), options);
            if (sel >= 0 && sel < attacks.length) choiceResult = { target_instance_id: attacks[sel].instance_id };
        }
    } else if (choiceType === 'choose_enemy_equipment') {
        const oppEq = (gameState.opponent || {}).equipment || [];
        if (!oppEq.length) { gameAlert(UI.notice, UI.no_enemy_equipment); }
        else {
            const options = oppEq.map(e => getCardDef((e.card_instance || {}).def_id) ? getCardName(getCardDef((e.card_instance || {}).def_id)) : '?');
            const sel = await simpleChoice(UI.choose_equip_for.replace('{0}', cardName), options);
            if (sel >= 0 && sel < oppEq.length) choiceResult = { target_instance_id: oppEq[sel].card_instance.instance_id };
        }
    } else if (choiceType === 'choose_card_to_discard') {
        const otherCards = (gameState.you || {}).hand || [];
        if (otherCards.length) {
            const options = otherCards.map(c => getCardDef(c.def_id) ? getCardName(getCardDef(c.def_id)) : c.def_id);
            const sel = await simpleChoice(UI.choose_discard_for.replace('{0}', cardName), options);
            if (sel >= 0 && sel < otherCards.length) choiceResult = { target_instance_id: otherCards[sel].instance_id };
        }
    } else if (choiceType === 'choose_card_from_deck') {
        const deck = (gameState.you || {}).deck || [];
        if (!deck.length) { gameAlert(UI.notice, UI.deck_empty); }
        else {
            const options = deck.map(c => getCardDef(c.def_id) ? getCardName(getCardDef(c.def_id)) : c.def_id);
            const sel = await simpleChoice(UI.choose_from_deck_for.replace('{0}', cardName), options);
            if (sel >= 0 && sel < deck.length) choiceResult = { target_def_id: deck[sel].def_id };
        }
    } else if (choiceType === 'choose_card_from_discard') {
        const discard = (gameState.you || {}).discard || [];
        if (!discard.length) { gameAlert(UI.notice, UI.discard_empty); }
        else {
            const options = discard.map(c => getCardDef(c.def_id) ? getCardName(getCardDef(c.def_id)) : c.def_id);
            const sel = await simpleChoice(UI.choose_from_discard_for.replace('{0}', cardName), options);
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
            const groupOptions = validGroups.map(([k, v]) => `${getCardDef(k) ? getCardName(getCardDef(k)) : k} x${v.length}`);
            const sel = await simpleChoice(UI.choose_attack_group_for.replace('{0}', cardName), groupOptions);
            if (sel >= 0) {
                const group = validGroups[sel][1];
                const combos = [];
                for (let i = 0; i < group.length; i++) {
                    for (let j = i + 1; j < group.length; j++) {
                        combos.push([group[i], group[j]]);
                        for (let k = j + 1; k < group.length; k++) {
                            combos.push([group[i], group[j], group[k]]);
                        }
                    }
                }
                const comboOptions = combos.map(combo => combo.map(c => `${getCardDef(c.def_id) ? getCardName(getCardDef(c.def_id)) : c.def_id}${getCardLayerLabel(c)}`).join(' + '));
                const comboSel = await simpleChoice(UI.choose_attack_group_for.replace('{0}', cardName), comboOptions);
                if (comboSel >= 0) choiceResult = { target_instance_ids: combos[comboSel].map(c => c.instance_id) };
            }
        }
    } else if (choiceType === 'choose_card_from_hand') {
        const otherCards = (gameState.you || {}).hand || [];
        if (otherCards.length) {
            const options = otherCards.map(c => getCardDef(c.def_id) ? getCardName(getCardDef(c.def_id)) : c.def_id);
            const sel = await simpleChoice(UI.choose_hand_for.replace('{0}', cardName), options);
            if (sel >= 0 && sel < otherCards.length) choiceResult = { target_instance_id: otherCards[sel].instance_id };
        }
    } else if (choiceType === 'choose_from_deck') {
        const deck = (gameState.you || {}).deck || [];
        if (!deck.length) { gameAlert(UI.notice, UI.deck_empty); }
        else {
            const options = deck.map(c => getCardDef(c.def_id) ? getCardName(getCardDef(c.def_id)) : c.def_id);
            const sel = await simpleChoice(UI.choose_from_deck_for.replace('{0}', cardName), options);
            if (sel >= 0 && sel < deck.length) choiceResult = { target_instance_id: deck[sel].instance_id };
        }
    } else if (choiceType === 'choose_from_enemy_hand') {
        const targetId = data.target_player_id != null ? data.target_player_id : -1;
        const oppHand = (targetId >= 0 ? getPlayerDataById(targetId) : (gameState.opponent || {})).hand || [];
        if (!oppHand.length) { gameAlert(UI.notice, UI.no_enemy_hand); }
        else {
            const options = oppHand.map(c => getCardDef(c.def_id) ? getCardName(getCardDef(c.def_id)) : c.def_id);
            const sel = await simpleChoice(UI.choose_from_enemy_hand_for.replace('{0}', cardName), options);
            if (sel >= 0 && sel < oppHand.length) choiceResult = { target_instance_id: oppHand[sel].instance_id };
            else if (oppHand.length) choiceResult = { target_instance_id: oppHand[0].instance_id };
        }
    }
    socket.emit(soloMode ? 'solo_resolve_choice' : 'resolve_choice', { choice: choiceResult });
    choicePending = false;
}

let rematchRequestedByOpponent = false;

function renderGameOver(data) {
    showView('view-gameover');
    const gs = data || gameState;
    const winner = gs.winner;
    const isDraw = winner === -1 || winner === null || winner === undefined;
    const isWin = winner === playerId;
    const title = $('gameover-title');
    if (title) {
        title.textContent = isDraw ? UI.draw : (isWin ? UI.victory : UI.defeat);
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        if (isDraw) {
            title.style.color = isDark ? '#E5E7EB' : '#374151';
            title.style.background = isDark ? 'rgba(229, 231, 235, 0.14)' : 'rgba(55, 65, 81, 0.12)';
        } else {
            title.style.color = isWin ? COLORS.health : COLORS.damage;
            title.style.background = isWin
                ? (isDark ? 'rgba(46, 204, 113, 0.15)' : COLORS.health_bg)
                : (isDark ? 'rgba(192, 57, 43, 0.15)' : COLORS.damage_bg);
        }
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
        if (rematchRequestedByOpponent) {
            rematchBtn.textContent = UI.agree_rematch;
            rematchBtn.disabled = false;
            rematchBtn.onclick = () => {
                if (!socket) { console.log('[REMATCH] socket missing'); return; }
                console.log('[REMATCH] emit rematch accept');
                socket.emit('rematch');
                rematchBtn.textContent = UI.rematch_sent;
                rematchBtn.disabled = true;
            };
        } else {
            rematchBtn.textContent = UI.rematch;
            rematchBtn.disabled = false;
            rematchBtn.onclick = () => {
                if (!socket) { console.log('[REMATCH] socket missing'); return; }
                console.log('[REMATCH] emit rematch request');
                socket.emit('rematch');
                rematchBtn.textContent = UI.rematch_sent;
                rematchBtn.disabled = true;
            };
        }
    }
    const returnLobbyBtn = $('btn-return-lobby');
    if (returnLobbyBtn) {
        returnLobbyBtn.onclick = () => {
            if (!socket) return;
            socket.emit('return_lobby');
            showView('view-lobby');
            phase = 'lobby';
        };
    }
}

function showOpponentDCWaiting(data) {
    const timeout = data.reconnect_timeout || 120;
    const oppName = data.opponent_nickname || '?';
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
    if (!isMyTurn()) {
        flashStatus(UI.not_your_turn, 2000, 'error');
        return;
    }
    if (socket) {
        socket.emit(soloMode ? 'solo_end_turn' : 'end_turn', {});
        const oldPhase = gameState.phase;
        const oldPlayer = gameState.current_player;
        setTimeout(() => {
            if (gameState.phase === oldPhase && gameState.current_player === oldPlayer) {
                flashStatus(UI.server_no_response, 3000, 'error');
            }
        }, 3000);
    } else {
        updateStatus(UI.server_not_connected);
    }
}

async function onSoloNextDraw() {
    if (!soloMode || !socket) return;
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
    const pool = deck.map(c => ({ def_id: c.def_id, label: getCardDef(c.def_id) ? getCardName(getCardDef(c.def_id)) : c.def_id }));
    const chosen = [];
    for (let i = 0; i < pickCount; i++) {
        if (!pool.length) break;
        const options = pool.map((p, idx) => `${idx + 1}. ${p.label}`);
        const sel = await simpleChoice(tf('next_draw_pick', i + 1, pickCount), options);
        if (sel < 0) return;
        chosen.push(pool[sel].def_id);
        pool.splice(sel, 1);
    }
    if (!chosen.length) return;
    socket.emit('solo_set_next_draw', { def_ids: chosen });
}

function onSurrender() {
    gameAlert(UI.confirm_surrender, '', [
        { text: UI.ok, cls: 'btn-danger', action: () => {
            if (socket) {
                socket.emit(soloMode ? 'solo_pause' : 'surrender', {});
            }
        }},
        { text: UI.cancel, cls: 'btn-secondary', action: () => {} }
    ]);
}

function onViewDeck() {
    if (gameState && gameState.mode === 'urf') {
        return;
    }
    const deck = (gameState.you || {}).deck || [];
    const modal = $('modal');
    const content = $('modal-content');
    if (!modal || !content) return;
    const counts = {};
    deck.forEach(c => {
        const cd = getCardDef(c.def_id);
        const name = cd ? getCardName(cd) : c.def_id;
        counts[name] = (counts[name] || 0) + 1;
    });
    let html = `<h3>${UI.view_deck_title}</h3><p>${UI.deck_total.replace('{0}', deck.length)}</p>`;
    Object.entries(counts).sort(([a], [b]) => a.localeCompare(b)).forEach(([name, cnt]) => {
        html += `<div>${name} x${cnt}</div>`;
    });
    html += `<div class="modal-buttons"><button class="btn btn-danger" onclick="hideModal()">${UI.close}</button></div>`;
    content.innerHTML = html;
    modal.classList.remove('hidden');
    modal.classList.add('active');
}

async function onUrfReplaceCard() {
    if (!gameState || gameState.mode !== 'urf' || !isMyTurn()) return;
    const hand = (gameState.you || {}).hand || [];
    if (!hand.length) return;
    const options = hand.map(c => getCardName(getCardDef(c.def_id)) || c.def_id);
    const sel = await simpleChoice(UI.urf_replace || '替换手牌', options);
    if (sel < 0) return;
    socket.emit('urf_replace_card', { card_instance_id: hand[sel].instance_id });
}

async function onUrfSellEquipment() {
    if (!gameState || gameState.mode !== 'urf' || !isMyTurn()) return;
    const equipment = (gameState.you || {}).equipment || [];
    if (!equipment.length) return;
    const options = equipment.map(eq => {
        const inst = eq.card_instance || {};
        return getCardName(getCardDef(inst.def_id)) || inst.def_id;
    });
    const sel = await simpleChoice(UI.urf_sell || '售卖装备', options);
    if (sel < 0) return;
    const inst = (equipment[sel].card_instance || {});
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
        socket.emit('chat', { text });
        input.value = '';
    }
}

function setupPlayZoneDrop() {
}

let settingsMods = [];

function openSettings() {
    const panel = $('settings-panel');
    if (panel) panel.classList.remove('hidden');
    loadSettingsMods();
    const serverInput = $('settings-server-input');
    if (serverInput) {
        const custom = localStorage.getItem('got_server') || '';
        serverInput.value = custom;
    }
    const serverHint = $('settings-server-hint');
    if (serverHint) {
        serverHint.textContent = tf('server_hint', DEFAULT_SERVER);
    }
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
    listEl.innerHTML = '';
    if (settingsMods.length === 0) {
        if (noModsEl) noModsEl.style.display = '';
        return;
    }
    if (noModsEl) noModsEl.style.display = 'none';
    const disabled = getDisabledMods();
    settingsMods.forEach((mod, i) => {
        const info = mod.info || {};
        const name = info.name || mod.filename || tf('mod_default_name', i + 1);
        const version = info.version || '';
        const filename = mod.filename || '';
        const item = document.createElement('div');
        item.className = 'settings-mod-item';
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.id = `mod-cb-${i}`;
        cb.checked = !disabled.includes(filename);
        cb.dataset.filename = filename;
        const label = document.createElement('label');
        label.htmlFor = cb.id;
        label.textContent = name;
        if (version) {
            const ver = document.createElement('span');
            ver.className = 'mod-version';
            ver.textContent = `v${version}`;
            item.appendChild(cb);
            item.appendChild(label);
            item.appendChild(ver);
        } else {
            item.appendChild(cb);
            item.appendChild(label);
        }
        listEl.appendChild(item);
    });
}

function getDisabledMods() {
    try {
        const raw = localStorage.getItem('got_disabled_mods');
        return raw ? JSON.parse(raw) : [];
    } catch (e) {
        return [];
    }
}

function saveDisabledMods() {
    const listEl = $('settings-mods-list');
    if (!listEl) return;
    const checkboxes = listEl.querySelectorAll('input[type="checkbox"]');
    const disabled = [];
    checkboxes.forEach(cb => {
        if (!cb.checked && cb.dataset.filename) {
            disabled.push(cb.dataset.filename);
        }
    });
    localStorage.setItem('got_disabled_mods', JSON.stringify(disabled));
    const serverInput = $('settings-server-input');
    if (serverInput) {
        localStorage.setItem('got_server', serverInput.value.trim());
    }
    fetchCardDefs().then(() => {
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
                const resp = await fetch('/api/mods', {
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
    console.log('[INIT] game init start');

    document.addEventListener('contextmenu', (e) => {
        if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
        }
    });
    const savedTheme = localStorage.getItem('got_theme') || 'light';
    applyTheme(savedTheme);
    const savedLang = localStorage.getItem('got_lang') || 'zh';
    applyLang(savedLang);
    bootLoader.step(UI.init_theme_lang, 24);
    bootLoader.step(UI.init_fonts, 36);
    if (document.fonts && document.fonts.ready) {
        try { await document.fonts.ready; } catch (_) {}
    }
    bootLoader.step(UI.init_fonts_done, 48);
    console.log('[INIT] theme/language applied');
    await fetchCardDefs();
    await fetchOpeningEvents();
    bootLoader.step(UI.init_bindings, 90);
    console.log('[INIT] card definitions loaded, count=', Object.keys(CARD_DEFS).length);
    $('btn-connect').addEventListener('click', onLogin);
    $('btn-solo-training').addEventListener('click', showSoloTraining);
    if ($('btn-card-gallery')) $('btn-card-gallery').addEventListener('click', () => showCardGallery());
    if ($('btn-open-about')) $('btn-open-about').addEventListener('click', openAbout);
    const savedNick = localStorage.getItem('got_nickname') || '';
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
    $('btn-open-settings').addEventListener('click', openSettings);
    $('btn-settings-close').addEventListener('click', () => { saveDisabledMods(); closeSettings(); });
    if ($('btn-lobby-settings')) $('btn-lobby-settings').addEventListener('click', openSettings);
    if ($('about-tab-rules')) $('about-tab-rules').addEventListener('click', () => setAboutPage('rules'));
    if ($('about-tab-credits')) $('about-tab-credits').addEventListener('click', () => setAboutPage('credits'));
    if ($('btn-about-close')) $('btn-about-close').addEventListener('click', closeAbout);
    if ($('btn-credit-bilibili')) $('btn-credit-bilibili').addEventListener('click', () => window.open('https://space.bilibili.com/1490695733', '_blank', 'noopener'));
    if ($('btn-credit-github')) $('btn-credit-github').addEventListener('click', () => window.open('https://github.com/Stickerbug', '_blank', 'noopener'));
    $('settings-theme-select').addEventListener('change', (e) => { applyTheme(e.target.value); });
    $('settings-lang-select').addEventListener('change', (e) => { applyLang(e.target.value); });
    $('btn-lobby-back').addEventListener('click', () => {
        if (socket) { socket.disconnect(); socket = null; }
        showView('view-login');
        phase = 'login';
    });
    $('btn-surrender').addEventListener('click', onSurrender);
    $('btn-end-turn').addEventListener('click', onEndTurn);
    $('btn-view-deck').addEventListener('click', onViewDeck);
    if ($('btn-urf-replace')) $('btn-urf-replace').addEventListener('click', onUrfReplaceCard);
    if ($('btn-urf-sell')) $('btn-urf-sell').addEventListener('click', onUrfSellEquipment);
    $('btn-solo-next-draw').addEventListener('click', onSoloNextDraw);
    $('btn-solo-edit').addEventListener('click', () => { if (socket) socket.emit('solo_pause', {}); else showSoloTraining(); });
    $('solo-card-search').addEventListener('input', renderSoloBuilder);
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
        if (socket) socket.emit('leave_spectate', {});
    });
    $('btn-lobby-chat-send').addEventListener('click', onLobbyChatSend);
    $('lobby-chat-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') onLobbyChatSend();
    });
    $('btn-game-chat-send').addEventListener('click', onGameChatSend);
    $('game-chat-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') onGameChatSend();
    });
    setupPlayZoneDrop();
    initModEditor();
    showView('view-login');
    setupFullscreenPrompt();
    bootLoader.done();
    document.getElementById('app').style.visibility = 'visible';
    if (!localStorage.getItem('got_seen_intro')) {
        setTimeout(() => openRulesModal({ firstVisit: true }), 250);
    }
}

document.addEventListener('DOMContentLoaded', init);
window.addEventListener('resize', () => {
    const gc = document.querySelector('.game-container');
    if (gc) gc.style.removeProperty('--card-w');
    scheduleAdjust();
});
console.log('[LOAD] game.js loaded, onEndTurn=', typeof onEndTurn);
