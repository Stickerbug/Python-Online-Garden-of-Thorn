const I18N = {
    zh: {
        round: '回合', your_turn: '你的回合', opponent_turn: '对手回合',
        draw_phase: '抽牌阶段', game_over: '游戏结束',
        invite: '邀请', accept: '接受', decline: '拒绝', return_lobby: '返回大厅',
        draft_phase: '选牌阶段', draft_reroll: '重选', draft_selected: '已选',
        select_event: '选择事件', waiting_opponent: '等待对手',
        play_card: '出牌', end_turn: '结束回合', surrender: '投降', view_deck: '查看牌堆',
        counter: '反制', no_counter: '不反制', waiting_response: '等待响应',
        victory: '胜利', defeat: '失败', rematch: '再来一局',
        connecting: '连接中...', disconnected: '已断开连接',
        login_failed: '登录失败', nickname: '昵称', enter_lobby: '进入大厅',
        online_players: '在线玩家', no_other_players: '暂无其他玩家',
        invite_sent: '邀请已发送', invite_received: '收到邀请',
        invite_message: '邀请你进行对局', invite_declined: '邀请被拒绝',
        ongoing_games: '进行中的对局', spectate: '观战',
        draft_info: '选牌', draft_complete: '选牌完成', draft_waiting: '等待对手完成选牌',
        draft_cost: '费用', select_this_event: '选择此事件',
        event_selected: '已选择事件', event_waiting: '等待对手选择事件',
        drag_to_play: '拖拽出牌', cannot_play: '无法出牌',
        enemy_attack: '敌方攻击', enemy_skill: '敌方技能', enemy_destroy_equip: '敌方摧毁装备',
        use_card: '使用', insufficient_resources: '资源不足',
        choose_attack_for: '选择攻击牌', choose_equip_for: '选择装备',
        choose_discard_for: '选择弃牌', choose_from_deck_for: '从牌堆选择',
        choose_from_discard_for: '从弃牌堆选择', choose_hand_for: '从手牌选择',
        choose_from_enemy_hand_for: '从敌方手牌选择',
        choose_attack_group_for: '选择攻击牌组',
        no_attack_cards: '没有攻击牌', no_enemy_equipment: '没有敌方装备',
        no_enemy_hand: '没有敌方手牌', deck_empty: '牌堆为空', discard_empty: '弃牌堆为空',
        no_same_attack: '没有相同的攻击牌',
        confirm_surrender: '确认投降?', request_rematch: '请求重赛',
        opponent_rematch: '对手请求重赛', rematch_sent: '重赛请求已发送',
        rematch_waiting: '等待对手确认', rematch_agreed: '双方同意重赛',
        agree_rematch: '同意重赛', you_win: '胜利!', you_lose: '失败!',
        send: '发送', cancel: '取消', ok: '确定', close: '关闭', notice: '提示',
        opponent_disconnected: '对手已断开连接', opponent_reconnected: '对手已重连',
        reconnect_title: '重连', reconnect_prompt: '是否重连到之前的对局?',
        reconnecting: '重连中...', reconnect_timeout: '重连超时',
        mod_mismatch_title: '模组不匹配', mod_mismatch_msg: '模组不一致，无法开始对局',
        switch_perspective: '切换视角', leave_spectate: '离开观战',
        switch_to_perspective: '切换到{0}视角',
        battle_log: '战斗日志', equip_info: '{0}({1}回合)', equip_corruption: '[腐化]',
        equip_trigger_cost: '{0} 触发:{1}E', status_poison: '中毒', status_fire: '灼烧',
        status_toxic: '淬毒', status_triangle: '三角形', status_dodge: '闪避',
        status_nazar: '邪眼', status_equip_protect: '装备保护', status_invincible: '无敌',
        status_stunned: '眩晕', status_attack_blocked: '禁攻', status_attack_only: '仅攻',
        status_untargetable: '不可选', status_bandage: '绷带', status_sponge: '海绵',
        status_shovel: '铲子',
        flag_precision: '精准', flag_exile: '放逐', flag_non_stackable: '不可叠加',
        flag_indestructible: '不可被摧毁', flag_sprout: '萌芽', flag_symbiosis: '共生',
        choose_convert_count: '选择转换次数', choose_magic_card_n: '选择第{0}张魔法牌',
        choose_source_card_n: '选择第{0}张源牌', choose_light_cards: '选择光明转换牌',
        choose_yggdrasil_card: '选择世界树转换牌', convert_label: '转换', convert_per_type: '每种最多{0}张',
        selected_count: '已选{0}/{1}', max_selection_warning: '选择数量不能超过{0}',
        deck_total: '牌堆共{0}张', view_deck_title: '查看牌堆',
        hand_deck_info_opp: '手牌:{0} 牌堆:{1}',
        hand_deck_discard_info: '手牌:{0} 牌堆:{1} 弃牌:{2}',
        round_status: '第{0}回合 - {1}',
        server_broadcast: '服务器广播: {0}', error_msg: '错误: {0}',
        lobby_status: '大厅 - {0}', no_counter_countdown: '不反制({0})',
        select_event_desc: '选择一个开局事件',
        opponent_selected: '对手已选择', opponent_selecting: '对手选择中...',
        card_type_thorn: 'Thorn', card_type_bloom: 'Bloom', card_type_root: 'Root', card_type_guard: 'Guard',
        settings_title: '设置', settings_appearance: '外观', settings_theme: '主题',
        settings_lang: '语言', settings_mods: '模组', settings_theme_light: '明亮',
        settings_theme_dark: '黑暗', no_games: '暂无进行中的对局',
        back_to_home: '返回主页', settings_btn: '设置',
        settings_server: '服务器', settings_server_addr: '地址',
    },
    en: {
        round: 'Round', your_turn: 'Your Turn', opponent_turn: "Opponent's Turn",
        draw_phase: 'Draw Phase', game_over: 'Game Over',
        invite: 'Invite', accept: 'Accept', decline: 'Decline', return_lobby: 'Return to Lobby',
        draft_phase: 'Draft Phase', draft_reroll: 'Reroll', draft_selected: 'Selected',
        select_event: 'Select Event', waiting_opponent: 'Waiting for Opponent',
        play_card: 'Play Card', end_turn: 'End Turn', surrender: 'Surrender', view_deck: 'View Deck',
        counter: 'Counter', no_counter: 'No Counter', waiting_response: 'Waiting for Response',
        victory: 'Victory', defeat: 'Defeat', rematch: 'Rematch',
        connecting: 'Connecting...', disconnected: 'Disconnected',
        login_failed: 'Login Failed', nickname: 'Nickname', enter_lobby: 'Enter Lobby',
        online_players: 'Online Players', no_other_players: 'No other players',
        invite_sent: 'Invite Sent', invite_received: 'Invite Received',
        invite_message: 'invites you to a match', invite_declined: 'Invite Declined',
        ongoing_games: 'Ongoing Games', spectate: 'Spectate',
        draft_info: 'Draft', draft_complete: 'Draft Complete', draft_waiting: 'Waiting for opponent to finish drafting',
        draft_cost: 'Cost', select_this_event: 'Select This Event',
        event_selected: 'Event Selected', event_waiting: 'Waiting for opponent to select event',
        drag_to_play: 'Drag to Play', cannot_play: 'Cannot Play',
        enemy_attack: 'Enemy Attack', enemy_skill: 'Enemy Skill', enemy_destroy_equip: 'Enemy Destroy Equipment',
        use_card: 'Use', insufficient_resources: 'Insufficient Resources',
        choose_attack_for: 'Choose Attack for', choose_equip_for: 'Choose Equipment',
        choose_discard_for: 'Choose Discard', choose_from_deck_for: 'Choose from Deck',
        choose_from_discard_for: 'Choose from Discard Pile', choose_hand_for: 'Choose from Hand',
        choose_from_enemy_hand_for: 'Choose from Enemy Hand',
        choose_attack_group_for: 'Choose Attack Group',
        no_attack_cards: 'No Attack Cards', no_enemy_equipment: 'No Enemy Equipment',
        no_enemy_hand: 'No Enemy Hand', deck_empty: 'Deck Empty', discard_empty: 'Discard Pile Empty',
        no_same_attack: 'No Same Attack Cards',
        confirm_surrender: 'Confirm Surrender?', request_rematch: 'Request Rematch',
        opponent_rematch: 'Opponent Requests Rematch', rematch_sent: 'Rematch Request Sent',
        rematch_waiting: 'Waiting for Opponent', rematch_agreed: 'Rematch Agreed',
        agree_rematch: 'Agree to Rematch', you_win: 'You Win!', you_lose: 'You Lose!',
        send: 'Send', cancel: 'Cancel', ok: 'OK', close: 'Close', notice: 'Notice',
        opponent_disconnected: 'Opponent Disconnected', opponent_reconnected: 'Opponent Reconnected',
        reconnect_title: 'Reconnect', reconnect_prompt: 'Reconnect to previous match?',
        reconnecting: 'Reconnecting...', reconnect_timeout: 'Reconnect Timeout',
        mod_mismatch_title: 'Mod Mismatch', mod_mismatch_msg: 'Mods are inconsistent, cannot start match',
        switch_perspective: 'Switch Perspective', leave_spectate: 'Leave Spectate',
        switch_to_perspective: 'Switch to {0} perspective',
        battle_log: 'Battle Log', equip_info: '{0}({1} turns)', equip_corruption: '[Corrupted]',
        equip_trigger_cost: '{0} Trigger:{1}E', status_poison: 'Poison', status_fire: 'Burn',
        status_toxic: 'Toxic', status_triangle: 'Triangle', status_dodge: 'Dodge',
        status_nazar: 'Nazar', status_equip_protect: 'Equip Protect', status_invincible: 'Invincible',
        status_stunned: 'Stunned', status_attack_blocked: 'Atk Blocked', status_attack_only: 'Atk Only',
        status_untargetable: 'Untargetable', status_bandage: 'Bandage', status_sponge: 'Sponge',
        status_shovel: 'Shovel',
        flag_precision: 'Precision', flag_exile: 'Exile', flag_non_stackable: 'Non-Stack',
        flag_indestructible: 'Indestructible', flag_sprout: 'Sprout', flag_symbiosis: 'Symbiosis',
        choose_convert_count: 'Choose Convert Count', choose_magic_card_n: 'Choose Magic Card #{0}',
        choose_source_card_n: 'Choose Source Card #{0}', choose_light_cards: 'Choose Light Convert Cards',
        choose_yggdrasil_card: 'Choose Yggdrasil Convert Card', convert_label: 'Convert', convert_per_type: 'Max {0} per type',
        selected_count: 'Selected {0}/{1}', max_selection_warning: 'Cannot exceed {0}',
        deck_total: 'Deck: {0} cards', view_deck_title: 'View Deck',
        hand_deck_info_opp: 'Hand:{0} Deck:{1}',
        hand_deck_discard_info: 'Hand:{0} Deck:{1} Discard:{2}',
        round_status: 'Round {0} - {1}',
        server_broadcast: 'Server: {0}', error_msg: 'Error: {0}',
        lobby_status: 'Lobby - {0}', no_counter_countdown: 'No Counter({0})',
        select_event_desc: 'Select an opening event',
        opponent_selected: 'Opponent Selected', opponent_selecting: 'Opponent Selecting...',
        card_type_thorn: 'Thorn', card_type_bloom: 'Bloom', card_type_root: 'Root', card_type_guard: 'Guard',
        settings_title: 'Settings', settings_appearance: 'Appearance', settings_theme: 'Theme',
        settings_lang: 'Language', settings_mods: 'Mods', settings_theme_light: 'Light',
        settings_theme_dark: 'Dark', no_games: 'No ongoing games',
        back_to_home: 'Back to Home', settings_btn: 'Settings',
        settings_server: 'Server', settings_server_addr: 'Address',
    }
};

let currentLang = localStorage.getItem('got_lang') || 'zh';
function t(key) { return (I18N[currentLang] && I18N[currentLang][key]) || (I18N.zh[key]) || key; }
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

function getCardName(cardDef) {
    if (!cardDef) return '?';
    return currentLang === 'en' ? cardDef.name_en : cardDef.name_cn;
}

const CARD_TYPE_LABELS = {
    thorn: () => t('card_type_thorn'), bloom: () => t('card_type_bloom'),
    root: () => t('card_type_root'), guard: () => t('card_type_guard'),
};

function getCardTypeLabel(cardType) {
    return CARD_TYPE_LABELS[cardType] ? CARD_TYPE_LABELS[cardType]() : cardType;
}

const CARD_FLAG_STYLES = {
    precision: { label: UI.flag_precision, fg: COLORS.precise, bg: COLORS.precise_bg },
    exile: { label: UI.flag_exile, fg: COLORS.banish, bg: COLORS.banish_bg },
    non_stackable: { label: UI.flag_non_stackable, fg: COLORS.non_stack, bg: COLORS.non_stack_bg },
    indestructible: { label: UI.flag_indestructible, fg: COLORS.indestructible, bg: COLORS.indestructible_bg },
    sprout: { label: UI.flag_sprout, fg: '#2ecc71', bg: '#27ae60' },
    symbiosis: { label: UI.flag_symbiosis, fg: '#3498db', bg: '#2980b9' },
};

let CARD_DEFS = {};
let socket = null;
let gameState = {};
let draftState = {};
let eventSelectData = {};
let lobbyPlayers = [];
let lobbyOngoingGames = [];
let playerId = -1;
let mySid = '';
let nickname = '';
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
let pendingPlayCard = null;

function gameAlert(title, message, buttons) {
    const el = $('game-alert');
    if (!el) return;
    $('game-alert-icon').textContent = '⚠';
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
    const sel = $('settings-lang-select');
    if (sel) sel.value = lang;
    updateStaticText();
}

function updateStaticText() {
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
        langSelect.options[0].textContent = '简体中文';
        langSelect.options[1].textContent = 'English';
    }
    const btnSettings = $('btn-open-settings');
    if (btnSettings) btnSettings.textContent = UI.settings_btn;
    const btnLobbyBack = $('btn-lobby-back');
    if (btnLobbyBack) btnLobbyBack.textContent = UI.back_to_home;
    const btnConnect = $('btn-connect');
    if (btnConnect) btnConnect.textContent = UI.enter_lobby;
    const noMods = $('settings-no-mods');
    if (noMods) noMods.textContent = currentLang === 'zh' ? '未找到模组文件' : 'No mod files found';
    const btnSettingsClose = $('btn-settings-close');
    if (btnSettingsClose) btnSettingsClose.textContent = UI.ok;
    const settingsServer = $('settings-section-server');
    if (settingsServer) settingsServer.textContent = UI.settings_server;
    const settingsLabelServer = $('settings-label-server');
    if (settingsLabelServer) settingsLabelServer.textContent = UI.settings_server_addr;
    const serverInput = $('settings-server-input');
    if (serverInput) serverInput.placeholder = currentLang === 'zh' ? '留空使用默认服务器' : 'Leave empty for default';
}

function $(id) { return document.getElementById(id); }

function showView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
    const el = $(viewId);
    if (el) el.classList.remove('hidden');
}

function updateStatus(text) {
    const s = $('status-text');
    if (s) s.textContent = text;
}

function showModal(html) {
    const content = $('modal-content');
    const modal = $('modal');
    if (content) content.innerHTML = html;
    if (modal) { modal.classList.remove('hidden'); modal.classList.add('active'); }
}

function hideModal() {
    const modal = $('modal');
    if (modal) { modal.classList.add('hidden'); modal.classList.remove('active'); }
}

async function fetchCardDefs() {
    try {
        const resp = await fetch('/api/cards');
        CARD_DEFS = await resp.json();
    } catch (e) {
        console.error('Failed to fetch card defs:', e);
        CARD_DEFS = {};
    }
}

function getCardDef(defId) {
    return CARD_DEFS[defId] || null;
}

function createCardElement(cardDict, options = {}) {
    const { faceDown = false, small = false, draggable = false, onClick = null } = options;
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
    const flags = new Set([...(cardDef.flags || []), ...(cardDict.instance_flags || [])]);
    const dup = (gameState.you && gameState.you.cards_played_this_turn && gameState.you.cards_played_this_turn[defId]) || 0;
    const symbiosis = flags.has('symbiosis');
    const totalE = (cardDict.cost_e_override != null ? cardDict.cost_e_override : cardDef.cost_e) - (cardDict.mimic_discount || 0) + (symbiosis ? 0 : dup);
    const totalM = cardDict.cost_m_override != null ? cardDict.cost_m_override : cardDef.cost_m;
    el.style.borderColor = typeColor;
    el.dataset.instanceId = cardDict.instance_id;
    el.dataset.defId = defId;
    let flagsHtml = '';
    for (const flag of flags) {
        const style = CARD_FLAG_STYLES[flag];
        if (style) {
            flagsHtml += `<span class="card-flag" style="color:${style.fg};background:${style.bg}">${style.label}</span>`;
        }
    }
    el.innerHTML = `
        <div class="card-costs">
            <span class="cost-e">${totalE}</span>
            <span class="card-name" style="color:${typeColor}">${getCardName(cardDef)}</span>
            <span class="cost-m">${totalM}</span>
        </div>
        <div class="card-type-label-wrap"><span class="card-type-label" style="color:${typeColor}">${typeLabel}</span></div>
        <div class="card-effect">${cardDef.effect_text || ''}</div>
        ${cardDef.description ? `<div class="card-description">${cardDef.description}</div>` : ''}
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
    e.preventDefault();
    const pos = getPointerPos(e);
    const instanceId = cardEl.dataset.instanceId;
    if (!instanceId) return;
    const rect = cardEl.getBoundingClientRect();
    const ghost = cardEl.cloneNode(true);
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

function onDocumentPointerUp(e) {
    if (!dragState) return;
    const pos = getPointerPos(e);
    const playZone = document.getElementById('play-zone');
    if (playZone) {
        const r = playZone.getBoundingClientRect();
        if (pos.x >= r.left && pos.x <= r.right && pos.y >= r.top && pos.y <= r.bottom) {
            onPlayCard(parseInt(dragState.instanceId));
        }
        playZone.classList.remove('drag-over');
    }
    dragState.originalCard.style.opacity = '';
    dragState.ghost.remove();
    dragState = null;
}

document.addEventListener('mousemove', onDocumentPointerMove);
document.addEventListener('mouseup', onDocumentPointerUp);
document.addEventListener('touchmove', onDocumentPointerMove, { passive: false });
document.addEventListener('touchend', onDocumentPointerUp);
document.addEventListener('touchcancel', onDocumentPointerUp);

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
        console.log('[客户端] Socket已连接, 发送login: nickname=', nickname);
        const disabledMods = getDisabledMods();
        socket.emit('login', { nickname, disabled_mods: disabledMods });
    });
    socket.on('disconnect', () => {
        console.log('[客户端] Socket已断开');
        updateStatus(UI.disconnected);
        phase = 'connecting';
    });
    socket.on('login_ok', (data) => {
        console.log('[客户端] 登录成功: sid=', data.sid, 'nickname=', data.nickname);
        mySid = data.sid || '';
        nickname = data.nickname || nickname;
        phase = 'lobby';
        updateStatus(UI.lobby_status.replace('{0}', nickname));
    });
    socket.on('login_fail', (data) => {
        showView('view-login');
        const err = $('login-error');
        if (err) err.textContent = data.reason || UI.login_failed;
    });
    socket.on('lobby_update', (data) => {
        console.log('[客户端] 收到lobby_update: players=', (data.players || []).length);
        lobbyPlayers = data.players || [];
        lobbyOngoingGames = data.ongoing_games || [];
        mySid = data.your_sid || mySid;
        phase = 'lobby';
        renderLobby(data);
    });
    socket.on('invite_received', (data) => {
        console.log('[客户端] 收到invite_received:', data);
        showModal(`
            <h3>${UI.invite_received}</h3>
            <p>${data.inviter_name} ${UI.invite_message}</p>
            <div class="modal-buttons">
                <button class="btn btn-primary" id="invite-accept">${UI.accept}</button>
                <button class="btn btn-danger" id="invite-decline">${UI.decline}</button>
            </div>
        `);
        $('invite-accept').onclick = () => {
            console.log('[客户端] 发送accept_invite: inviter_sid=', data.inviter_sid);
            socket.emit('accept_invite', { inviter_sid: data.inviter_sid });
            hideModal();
        };
        $('invite-decline').onclick = () => {
            console.log('[客户端] 发送decline_invite: inviter_sid=', data.inviter_sid);
            socket.emit('decline_invite', { inviter_sid: data.inviter_sid });
            hideModal();
        };
    });
    socket.on('invite_declined', () => {
        updateStatus(UI.invite_declined);
    });
    socket.on('game_phase', (data) => {
        console.log('[客户端] 收到game_phase:', data.phase);
        phase = data.phase;
        if (phase === 'draft') {
            rematchRequestedByOpponent = false;
            showView('view-draft');
        } else if (phase === 'event_select') {
            showView('view-event-select');
            updateStatus(UI.select_event);
        } else if (phase === 'playing') {
            showView('view-game');
            updateStatus(UI.game_loading || '游戏加载中...');
        } else if (phase === 'game_over') {
            showView('view-gameover');
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
        console.log('[客户端] 收到event_select');
        phase = 'event_select';
        eventSelectData = data;
        renderEventSelect(data);
    });
    socket.on('state_update', (data) => {
        console.log('[客户端] 收到state_update: phase=', data.phase, 'current_player=', data.current_player, 'your_id=', data.your_id, 'pending_response=', data.pending_response != null);
        gameState = data;
        phase = data.phase || phase;
        if (data.your_id != null) playerId = data.your_id;
        if (data.pending_response != null) {
            pendingPlayCard = pendingPlayCard || data.pending_response;
        } else if (!responsePending) {
            pendingPlayCard = null;
        }
        if (phase === 'game_over') {
            renderGameOver(data);
        } else {
            renderGame(data);
        }
    });
    socket.on('response_request', (data) => {
        responsePending = true;
        responseData = data;
        showResponseUI(data);
    });
    socket.on('choice_request', (data) => {
        choicePending = true;
        choiceData = data;
        pendingPlayCard = null;
        showChoiceUI(data);
    });
    socket.on('chat', (data) => {
        console.log('[客户端] 收到chat:', data.nickname, data.text);
        if (phase === 'lobby') {
            appendLobbyChat(data.nickname, data.text);
        } else {
            appendGameChat(data.nickname, data.text);
        }
    });
    socket.on('server_error', (data) => {
        console.log('[客户端] 收到server_error:', data.message);
        updateStatus(UI.error_msg.replace('{0}', data.message || ''));
        gameAlert(UI.notice, data.message || '');
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
        updateStatus(UI.opponent_reconnected);
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
        updateStatus(UI.reconnect_timeout);
        phase = 'lobby';
    });
    socket.on('rematch_requested', () => {
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
        updateStatus(UI.server_broadcast.replace('{0}', data.message || ''));
    });
}

function onLogin() {
    const nick = $('input-nickname').value.trim();
    const err = $('login-error');
    if (!nick) {
        if (err) err.textContent = currentLang === 'zh' ? '请输入昵称' : 'Please enter a nickname';
        return;
    }
    if (/^\d+$/.test(nick)) {
        if (err) err.textContent = currentLang === 'zh' ? '昵称不能为纯数字' : 'Nickname cannot be pure numbers';
        return;
    }
    if (/^[\-_]+$/.test(nick)) {
        if (err) err.textContent = currentLang === 'zh' ? '昵称不能为纯符号' : 'Nickname cannot be pure symbols';
        return;
    }
    if (/[\-_]{2,}/.test(nick)) {
        if (err) err.textContent = currentLang === 'zh' ? '-和_不能连续出现' : '- and _ cannot appear consecutively';
        return;
    }
    const server = getServerAddress();
    nickname = nick;
    if (err) err.textContent = '';
    updateStatus(UI.connecting);
    connectSocket(server);
}

function getServerAddress() {
    const custom = localStorage.getItem('got_server') || '';
    return custom.trim() || DEFAULT_SERVER;
}

function renderLobby(data) {
    showView('view-lobby');
    const players = data.players || [];
    const games = data.ongoing_games || [];
    console.log('[客户端] renderLobby: players=', players.length, 'mySid=', mySid);
    players.forEach(p => console.log('  player:', p.nickname, 'sid=', p.sid, 'isMe=', p.sid === mySid));
    const onlineCount = $('lobby-online-count');
    if (onlineCount) onlineCount.textContent = `${UI.online_players}: ${players.length}`;
    const list = $('lobby-players');
    if (!list) return;
    list.innerHTML = '';
    if (players.length === 0) {
        list.innerHTML = `<div class="empty-hint">${UI.no_other_players}</div>`;
    } else {
        players.forEach(p => {
            const row = document.createElement('div');
            row.className = 'lobby-player-row';
            const isMe = p.sid === mySid;
            if (isMe) {
                row.innerHTML = `<span class="player-name player-self">${p.nickname}</span>`;
            } else {
                row.innerHTML = `<span class="player-name">${p.nickname}</span>`;
                const btn = document.createElement('button');
                btn.textContent = UI.invite;
                btn.className = 'btn btn-primary';
                btn.onclick = () => {
                    console.log('[客户端] 发送invite: target_sid=', p.sid);
                    socket.emit('invite', { target_sid: p.sid });
                    updateStatus(UI.invite_sent);
                };
                row.appendChild(btn);
            }
            list.appendChild(row);
        });
    }
    const gamesList = $('lobby-games');
    if (gamesList) {
        gamesList.innerHTML = '';
        const visibleGames = games.filter(g => !g.both_disconnected);
        if (visibleGames.length > 0) {
            visibleGames.forEach(g => {
                const row = document.createElement('div');
                row.className = 'lobby-game-row';
                row.innerHTML = `<span>${g.player1} vs ${g.player2} (${UI.round}${g.round})</span>`;
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
    const oppPicksCount = data.opponent_picks_count || 0;
    const prevPicks = draftState ? (draftState.picks || []).length : -1;
    const iJustPicked = picks.length > prevPicks;
    const shouldAnimate = isReroll || iJustPicked;
    const info = $('draft-info');
    if (info) {
        if (picks.length >= totalRounds) {
            info.textContent = `${UI.draft_complete} | ${UI.waiting_opponent}: ${oppPicksCount}`;
        } else {
            info.textContent = `${UI.draft_info} ${round}/${totalRounds} | ${UI.draft_reroll}: ${rerolls} | ${UI.waiting_opponent}: ${oppPicksCount}`;
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
    const container = $('event-options');
    if (!container) return;
    container.innerHTML = '';
    if (myPick != null) {
        let eventName = '?';
        for (const ev of events) {
            if (ev && ev.id === myPick) { eventName = ev.name || '?'; break; }
        }
        container.innerHTML = `
            <div class="event-selected">${UI.event_selected.replace('{0}', eventName)}</div>
            ${!oppSelected ? `<div class="waiting-msg">${UI.waiting_opponent}</div>` : `<div class="waiting-msg">${UI.opponent_selected}</div>`}
        `;
        return;
    }
    const oppStatus = document.createElement('div');
    oppStatus.className = 'waiting-msg';
    oppStatus.textContent = oppSelected ? UI.opponent_selected : UI.opponent_selecting;
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
        const posLabels = ['Ⅰ', 'Ⅱ', 'Ⅲ'];
        card.innerHTML = `
            <div class="event-header" style="background:${bc}"><span>${posLabels[i] || '?'} ${ev.name || '?'}</span></div>
            <div class="event-desc">${ev.desc || ''}</div>
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
            return cd ? `${getCardName(cd)} (${cd.cost_e}E/${cd.cost_m}M) ${cd.effect_text}` : did;
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
            input.max = String(Math.min(cnt, 5));
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
            inputs[did] = input;
            row.appendChild(label);
            row.appendChild(input);
            optsEl.appendChild(row);
        });
        const cancelBtn = $('game-prompt-cancel');
        cancelBtn.textContent = UI.ok;
        cancelBtn.onclick = () => {
            el.classList.remove('active');
            const convertDefIds = [];
            let total = 0;
            entries.forEach(([did, cnt]) => {
                const val = Math.min(parseInt(inputs[did].value) || 0, Math.min(cnt, 5 - total));
                for (let i = 0; i < val; i++) convertDefIds.push(did);
                total += val;
            });
            resolve(convertDefIds.length ? { convert_def_ids: convertDefIds } : null);
        };
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

function isMyTurn() {
    if (!gameState) return false;
    if (playerId < 0) return false;
    return gameState.phase === 'action' && gameState.current_player === playerId;
}

function renderGame(data) {
    showView('view-game');
    const gs = data || gameState;
    const you = gs.you || {};
    const opp = gs.opponent || {};
    const myTurn = isMyTurn();
    console.log('[RENDER] renderGame: phase=', gs.phase, 'current_player=', gs.current_player, 'playerId=', playerId, 'myTurn=', myTurn);
    renderPlayerBars('opp-bars', opp);
    renderPlayerBars('you-bars', you);
    renderStatusTags('opp-status', opp);
    renderStatusTags('you-status', you);
    renderOppHand(opp);
    renderPlayerHand(you);
    renderEquipment('opp-equip', opp, false);
    renderEquipment('you-equip', you, true);
    renderLog(gs.log || []);
    const phaseText = gs.phase === 'action' ? (myTurn ? UI.your_turn : UI.opponent_turn)
        : gs.phase === 'draw' ? UI.draw_phase
        : gs.phase === 'game_over' ? UI.game_over : '';
    updateStatus(UI.round_status.replace('{0}', gs.round_num || 0).replace('{1}', phaseText));
    const endTurnBtn = $('btn-end-turn');
    if (endTurnBtn) {
        endTurnBtn.disabled = false;
        endTurnBtn.removeAttribute('disabled');
        endTurnBtn.style.opacity = myTurn ? '1' : '0.5';
        endTurnBtn.style.cursor = 'pointer';
        endTurnBtn.onclick = onEndTurn;
    }
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
    const spectateControls = $('spectate-controls');
    const gameControls = $('game-controls');
    if (isSpectating) {
        if (spectateControls) spectateControls.classList.remove('hidden');
        if (gameControls) gameControls.style.display = 'none';
        if (playZone) playZone.style.display = 'none';
        const p1Name = gs.player1_name || 'P1';
        const p2Name = gs.player2_name || 'P2';
        const switchBtn = $('btn-switch-perspective');
        if (switchBtn) switchBtn.textContent = UI.switch_to_perspective.replace('{0}', spectatePerspective === 0 ? p2Name : p1Name);
    } else {
        if (spectateControls) spectateControls.classList.add('hidden');
        if (gameControls) gameControls.style.display = '';
        if (playZone) playZone.style.display = '';
    }
    const oppInfo = $('opp-info');
    if (oppInfo) oppInfo.textContent = UI.hand_deck_info_opp.replace('{0}', opp.hand_count || 0).replace('{1}', opp.deck_count || 0);
    const youInfo = $('you-info');
    if (youInfo) youInfo.textContent = UI.hand_deck_discard_info.replace('{0}', you.hand_count || 0).replace('{1}', you.deck_count || 0).replace('{2}', you.discard_count || 0);
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

function renderOppHand(oppData) {
    const container = $('opp-hand');
    if (!container) return;
    container.innerHTML = '';
    const revealedHand = oppData.revealed_hand;
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
            draggable: canPlay && cardDef && cardDef.card_type !== 'guard',
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
    const dup = (you.cards_played_this_turn || {})[cardDict.def_id] || 0;
    const flags = new Set([...(cardDef.flags || []), ...(cardDict.instance_flags || [])]);
    const symbiosis = flags.has('symbiosis');
    const totalE = (cardDict.cost_e_override != null ? cardDict.cost_e_override : cardDef.cost_e) - (cardDict.mimic_discount || 0) + (symbiosis ? 0 : dup);
    const totalM = cardDict.cost_m_override != null ? cardDict.cost_m_override : cardDef.cost_m;
    if (totalE > elixir) return false;
    if (totalM > magic) return false;
    return true;
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
        let text = UI.equip_info.replace('{0}', getCardName(cardDef)).replace('{1}', turns);
        if (corruption) text += UI.equip_corruption;
        if (cardDef.trigger_cost_e >= 0 && isMyEquipment && turns >= 1) {
            const btn = document.createElement('button');
            btn.className = 'btn btn-small btn-equip-trigger';
            btn.textContent = UI.equip_trigger_cost.replace('{0}', text).replace('{1}', cardDef.trigger_cost_e);
            btn.onclick = () => socket.emit('use_trigger', { equipment_instance_id: cardInst.instance_id });
            container.appendChild(btn);
        } else {
            el.textContent = text;
            container.appendChild(el);
        }
    });
}

function renderLog(log) {
    const container = $('battle-log');
    if (!container) return;
    let content = container.querySelector('.log-content');
    if (!content) {
        content = document.createElement('div');
        content.className = 'log-content';
        container.appendChild(content);
    }
    const wasAtBottom = content.scrollTop + content.clientHeight >= content.scrollHeight - 30;
    content.innerHTML = '';
    log.forEach(line => {
        const el = document.createElement('div');
        el.className = 'log-entry';
        if (line.includes('伤害') || line.includes('D')) el.classList.add('log-damage');
        else if (line.includes('+H') || line.includes('回复')) el.classList.add('log-heal');
        else if (line.includes('中毒')) el.classList.add('log-poison');
        else if (line.includes('灼烧')) el.classList.add('log-fire');
        else if (line.includes('+E') || line.includes('能量')) el.classList.add('log-elixir');
        else if (line.includes('+M') || line.includes('魔力')) el.classList.add('log-magic');
        else if (line.includes('===')) el.classList.add('log-round');
        el.textContent = line;
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
    const container = $('battle-log');
    if (!container) return;
    let content = container.querySelector('.log-content');
    if (!content) {
        content = document.createElement('div');
        content.className = 'log-content';
        container.appendChild(content);
    }
    const el = document.createElement('div');
    el.className = 'log-entry log-chat';
    const nameSpan = document.createElement('span');
    nameSpan.className = 'chat-nick';
    nameSpan.textContent = `${nick}: `;
    el.appendChild(nameSpan);
    el.appendChild(document.createTextNode(text));
    content.appendChild(el);
    content.scrollTop = content.scrollHeight;
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
        updateStatus(UI.cannot_play);
        return;
    }
    const choice = await getCardChoice(cardDict);
    if (choice === false) return;
    pendingPlayCard = cardDict;
    renderPendingCard();
    socket.emit('play_card', { card_instance_id: cardInstanceId, choice });
}

async function getCardChoice(cardDict) {
    const defId = cardDict.def_id;
    const hand = (gameState.you || {}).hand || [];
    if (defId === 'Fission') {
        const attacks = hand.filter(c => {
            const cd = getCardDef(c.def_id);
            return cd && cd.card_type === 'thorn' && c.instance_id !== cardDict.instance_id;
        });
        if (!attacks.length) { gameAlert(UI.notice, UI.no_attack_cards); return false; }
        const options = attacks.map(a => getCardDef(a.def_id) ? getCardName(getCardDef(a.def_id)) : a.def_id);
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
        const group = validGroups[sel][1].slice(0, 3);
        return { target_instance_ids: group.map(c => c.instance_id) };
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
        const oppEq = (gameState.opponent || {}).equipment || [];
        const destroyable = oppEq.filter(e => {
            const cd = getCardDef((e.card_instance || {}).def_id);
            return cd && !(cd.flags || []).includes('indestructible');
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
    let hasAffordable = false;
    counterCards.forEach(cc => {
        const ccDef = getCardDef(cc.def_id);
        if (ccDef && ccDef.cost_e <= myElixir && ccDef.cost_m <= myMagic) hasAffordable = true;
    });
    if (!counterCards.length || !hasAffordable) {
        onRespond(null);
        return;
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
    label.innerHTML = `⚠ ${triggerDesc}：${cardName}`;
    container.appendChild(label);
    counterCards.forEach(cc => {
        const ccDef = getCardDef(cc.def_id);
        if (!ccDef) return;
        const canAfford = ccDef.cost_e <= myElixir && ccDef.cost_m <= myMagic;
        const costStr = ccDef.cost_m === 0 ? `${ccDef.cost_e}E` : `${ccDef.cost_e}E/${ccDef.cost_m}M`;
        const btn = document.createElement('button');
        btn.className = 'btn ' + (canAfford ? 'btn-primary' : 'btn-counter-disabled');
        btn.textContent = `${UI.use_card.replace('{0}', getCardName(ccDef)).replace('{1}', costStr)}${canAfford ? '' : ' ' + UI.insufficient_resources}`;
        btn.disabled = !canAfford;
        btn.onclick = () => onRespond(cc.instance_id);
        container.appendChild(btn);
    });
    responseCountdown = 5;
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
    socket.emit('response', { card_instance_id: cardInstanceId });
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
            const options = attacks.map(a => getCardDef(a.def_id) ? getCardName(getCardDef(a.def_id)) : a.def_id);
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
                const group = validGroups[sel][1].slice(0, 3);
                choiceResult = { target_instance_ids: group.map(c => c.instance_id) };
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
        const oppHand = (gameState.opponent || {}).hand || [];
        if (!oppHand.length) { gameAlert(UI.notice, UI.no_enemy_hand); }
        else {
            const options = oppHand.map(c => getCardDef(c.def_id) ? getCardName(getCardDef(c.def_id)) : c.def_id);
            const sel = await simpleChoice(UI.choose_from_enemy_hand_for.replace('{0}', cardName), options);
            if (sel >= 0 && sel < oppHand.length) choiceResult = { target_instance_id: oppHand[sel].instance_id };
            else if (oppHand.length) choiceResult = { target_instance_id: oppHand[0].instance_id };
        }
    }
    socket.emit('resolve_choice', { choice: choiceResult });
    choicePending = false;
}

let rematchRequestedByOpponent = false;

function renderGameOver(data) {
    showView('view-gameover');
    const gs = data || gameState;
    const winner = gs.winner;
    const isWin = winner === playerId;
    const title = $('gameover-title');
    if (title) {
        title.textContent = isWin ? UI.victory : UI.defeat;
        title.style.color = isWin ? COLORS.health : COLORS.damage;
        title.style.background = isWin ? COLORS.health_bg : COLORS.damage_bg;
    }
    const logContainer = $('gameover-log');
    if (logContainer) {
        logContainer.innerHTML = '';
        (gs.log || []).forEach(line => {
            const el = document.createElement('div');
            el.className = 'log-entry';
            el.textContent = line;
            logContainer.appendChild(el);
        });
    }
    const rematchBtn = $('btn-rematch');
    if (rematchBtn) {
        if (rematchRequestedByOpponent) {
            rematchBtn.textContent = UI.agree_rematch;
            rematchBtn.disabled = false;
            rematchBtn.onclick = () => {
                if (!socket) return;
                socket.emit('rematch');
                rematchBtn.textContent = UI.rematch_sent;
                rematchBtn.disabled = true;
            };
        } else {
            rematchBtn.textContent = UI.rematch;
            rematchBtn.disabled = false;
            rematchBtn.onclick = () => {
                if (!socket) return;
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
        <h3>${UI.opponent_disconnected}</h3>
        <p id="dc-countdown">${oppName} ${remaining}s</p>
    `);
    const timer = setInterval(() => {
        remaining--;
        const el = $('dc-countdown');
        if (el) el.textContent = `${oppName} ${remaining}s`;
        if (remaining <= 0) { clearInterval(timer); hideModal(); }
    }, 1000);
}

function onEndTurn() {
    console.log('[END_TURN] ===== onEndTurn被调用 =====');
    console.log('[END_TURN] gameState=', JSON.stringify(gameState).substring(0, 200));
    console.log('[END_TURN] playerId=', playerId, 'isMyTurn=', isMyTurn());
    console.log('[END_TURN] socket=', !!socket, 'socket.id=', socket ? socket.id : 'N/A');
    console.log('[END_TURN] socket.connected=', socket ? socket.connected : 'N/A');
    if (!isMyTurn()) {
        let reason = '';
        if (gameState.phase !== 'action') reason = '当前阶段: ' + gameState.phase;
        else if (gameState.current_player !== playerId) reason = '不是你的回合';
        else reason = '未知原因';
        console.log('[END_TURN] 不是你的回合, reason=', reason);
        gameAlert(UI.notice, reason);
        return;
    }
    if (socket) {
        console.log('[END_TURN] 发送end_turn事件, socket.id=', socket.id, 'connected=', socket.connected);
        socket.emit('end_turn', {}, (ack) => {
            console.log('[END_TURN] 服务器ack:', ack);
        });
        const oldPhase = gameState.phase;
        const oldPlayer = gameState.current_player;
        setTimeout(() => {
            if (gameState.phase === oldPhase && gameState.current_player === oldPlayer) {
                console.log('[END_TURN] 3秒后状态未变化，可能服务端未处理');
                gameAlert(UI.notice, '服务器未响应，请检查网络连接或刷新页面重试');
            }
        }, 3000);
    } else {
        console.log('[END_TURN] socket为空!');
        updateStatus('未连接到服务器');
    }
}

function onSurrender() {
    console.log('[客户端] onSurrender called, socket=', !!socket);
    gameAlert(UI.confirm_surrender, '', [
        { text: UI.ok, cls: 'btn-danger', action: () => {
            console.log('[客户端] 发送surrender事件');
            if (socket) {
                socket.emit('surrender', {});
            }
        }},
        { text: UI.cancel, cls: 'btn-secondary', action: () => {} }
    ]);
}

function onViewDeck() {
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
        html += `<div>${name} ×${cnt}</div>`;
    });
    html += `<div class="modal-buttons"><button class="btn btn-danger" onclick="hideModal()">${UI.close}</button></div>`;
    content.innerHTML = html;
    modal.classList.remove('hidden');
    modal.classList.add('active');
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
        serverHint.textContent = currentLang === 'zh'
            ? `默认: ${DEFAULT_SERVER}（留空使用默认）`
            : `Default: ${DEFAULT_SERVER} (leave empty for default)`;
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
        const name = info.name || mod.filename || `模组${i + 1}`;
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
                if (statusEl) statusEl.textContent = '加载成功';
            } catch (e) {
                if (editorArea) editorArea.value = '';
                if (statusEl) statusEl.textContent = '加载失败';
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
                if (statusEl) statusEl.textContent = result.message || '保存成功';
            } catch (e) {
                if (statusEl) statusEl.textContent = '保存失败: ' + e.message;
            }
        };
    }
    if (validateBtn) {
        validateBtn.onclick = () => {
            try {
                JSON.parse(editorArea ? editorArea.value : '');
                if (statusEl) statusEl.textContent = 'JSON格式正确';
            } catch (e) {
                if (statusEl) statusEl.textContent = 'JSON格式错误: ' + e.message;
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
    if (!isMobile) return;
    const dismissed = sessionStorage.getItem('got_fullscreen_dismissed');
    if (dismissed) return;
    const prompt = document.getElementById('fullscreen-prompt');
    if (!prompt) return;
    prompt.classList.remove('hidden');
    const btnFs = document.getElementById('btn-fullscreen');
    const btnDismiss = document.getElementById('btn-dismiss-fullscreen');
    if (btnFs) {
        btnFs.onclick = () => {
            const el = document.documentElement;
            if (el.requestFullscreen) el.requestFullscreen();
            else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
            prompt.classList.add('hidden');
            sessionStorage.setItem('got_fullscreen_dismissed', '1');
        };
    }
    if (btnDismiss) {
        btnDismiss.onclick = () => {
            prompt.classList.add('hidden');
            sessionStorage.setItem('got_fullscreen_dismissed', '1');
        };
    }
}

async function init() {
    console.log('[INIT] === 游戏初始化开始 ===');

    document.addEventListener('contextmenu', (e) => {
        if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
        }
    });
    const savedTheme = localStorage.getItem('got_theme') || 'light';
    applyTheme(savedTheme);
    const savedLang = localStorage.getItem('got_lang') || 'zh';
    applyLang(savedLang);
    console.log('[INIT] 主题/语言已设置');
    await fetchCardDefs();
    console.log('[INIT] 卡牌定义已加载, 数量=', Object.keys(CARD_DEFS).length);
    $('btn-connect').addEventListener('click', onLogin);
    $('input-nickname').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') onLogin();
    });
    $('btn-open-settings').addEventListener('click', openSettings);
    $('btn-settings-close').addEventListener('click', () => { saveDisabledMods(); closeSettings(); });
    $('settings-theme-select').addEventListener('change', (e) => { applyTheme(e.target.value); });
    $('settings-lang-select').addEventListener('change', (e) => { applyLang(e.target.value); });
    $('btn-lobby-back').addEventListener('click', () => {
        if (socket) { socket.disconnect(); socket = null; }
        showView('view-login');
        phase = 'login';
    });
    $('btn-surrender').addEventListener('click', onSurrender);
    $('btn-view-deck').addEventListener('click', onViewDeck);
    $('btn-rematch').addEventListener('click', () => { if (socket) socket.emit('rematch'); });
    $('btn-return-lobby').addEventListener('click', () => {
        if (socket) socket.emit('return_lobby');
        showView('view-lobby');
        phase = 'lobby';
    });
    $('btn-leave-spectate').addEventListener('click', () => { if (socket) socket.emit('leave_spectate'); });
    $('btn-switch-perspective').addEventListener('click', () => {
        spectatePerspective = 1 - spectatePerspective;
        if (socket) socket.emit('switch_spectate_perspective');
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
    console.log('[INIT] === 游戏初始化完成 ===');
    console.log('[INIT] btn-end-turn element=', !!$('btn-end-turn'));
    console.log('[INIT] onEndTurn function=', typeof onEndTurn);
}

document.addEventListener('DOMContentLoaded', init);
console.log('[LOAD] game.js 已加载, onEndTurn=', typeof onEndTurn);
