(() => {
    'use strict';

    const $ = (id) => document.getElementById(id);
    const SVG_NS = 'http://www.w3.org/2000/svg';
    const STORY_MAP_NODE_RADIUS = 25;
    const STORY_MAP_EDGE_INSET = STORY_MAP_NODE_RADIUS + 4;
    const VIEWS = [
        'story-loading', 'story-empty', 'story-blessing', 'story-run',
        'story-combat', 'story-room', 'story-reward', 'story-terminal',
    ];
    let activeRun = null;
    let storyContent = null;
    let contentVersion = '';
    let actionInFlight = false;
    let selectedCombatCardId = '';
    let hoveredCombatCardId = '';
    let cardPlayInFlight = false;
    let storyAimPointer = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    let storyAimFrame = 0;
    let storyCursorCard = null;
    let toastTimer = null;
    let developerModeOpen = false;
    let cardChoiceContext = null;
    let hoveredPredictionTargetId = '';
    let storyKeyboardFocus = null;
    let storySecondHandPage = false;
    let activeStoryRoomTabKey = '';
    let activeStoryRoomTabId = '';
    let pendingStoryDeckChange = null;
    let pendingStoryEventAction = null;
    let storyOnlineCount = null;
    let storyPresenceTimer = 0;
    let storyPresenceInFlight = false;
    let storyPresenceIntervalMs = 25000;
    let storyPresenceActivityPending = false;
    let lastStoryAfkActivityReportAt = 0;
    let activeStoryAfkCheck = null;
    let storyAfkCheckTimer = 0;
    let storyAfkHoldFrame = 0;
    let storyAfkRedirectTimer = 0;
    let storyChatSocket = null;
    let storyChatOpen = false;
    let storyChatConnected = false;
    let storyChatInitialized = false;
    let storyChatEntries = [];
    let storyChatHistorySignature = '';
    let storyChatUnreadCount = 0;
    let storyMentionDirectory = [];
    let storyMentionCandidates = [];
    let storyMentionMenu = null;
    let storyMentionActiveRange = null;
    const readStoryMentionIds = new Set();
    let storyEquipmentPreview = null;
    let storyCardHoverPreview = null;
    let storyCombatEntranceAnimating = false;
    let storyMapPreviewOpen = false;
    let pendingStorySaveId = 0;
    let storyDiscoveries = [];
    let storyCodexMode = 'cards';
    let storyCodexSearch = '';
    let storyCodexSelectedId = '';
    let storyCodexTalentKind = 'relic';
    let storyCodexTermKind = 'status';
    let storyCodexCardFiltersReady = false;
    let storySkinMouthAnimation = null;
    let storySkinDamageTimer = 0;
    let storySkinDamageUntil = 0;
    const storyCodexRarities = new Set();
    const storyCodexTypes = new Set();
    const STORY_AFK_ACTIVITY_REPORT_INTERVAL_MS = 20000;
    const STORY_PRESERVED_SCROLL_SELECTORS = Object.freeze([
        '.story-map-scroll',
        '.story-dev-panel',
        '#story-blessing',
        '#story-blessing-options',
        '#story-room-tabs',
        '#story-room-options',
        '#story-reward',
        '#story-reward-options',
        '#story-hand',
        '#story-pile-grid',
        '#story-save-list',
        '#story-card-choice-grid',
        '#story-codex-tabs',
        '#story-codex-sidebar',
        '#story-codex-detail',
        '[data-story-scroll-key]',
    ]);
    const storyCardElementData = new WeakMap();
    const storyCardTermOptions = new WeakMap();
    const STORY_PRESENCE_CLIENT_ID = globalThis.crypto?.randomUUID
        ? crypto.randomUUID()
        : `story-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const STORY_SKIN_LOOK_OFFSET_X_PERCENT = 38;
    const STORY_SKIN_LOOK_OFFSET_Y_PERCENT = 56;
    const STORY_SKIN_DAMAGE_HOLD_MS = 3000;
    const STORY_SKIN_MOUTH_NORMAL_POINTS = Object.freeze([20, 18, 36, 32, 64, 32, 80, 18]);
    const STORY_SKIN_MOUTH_HURT_POINTS = Object.freeze([20, 26, 36, 12, 64, 12, 80, 26]);

    const STORY_TAG_STYLES = Object.freeze({
        precise: { className: 'precision', color: '#546E7A' },
        exile: { className: 'exile', color: '#6C3483' },
        ready: { className: 'custom story-ready', color: '#B9770E' },
        unplayable: { className: 'custom story-unplayable', color: '#922B21' },
        retain: { className: 'custom story-retain', color: '#2874A6' },
        void: { className: 'void', color: '#37474F' },
        wide: { className: 'wide-strike', color: '#1F9D8A' },
        eternal: { className: 'custom story-eternal', color: '#8E44AD' },
        charge: { className: 'custom story-charge', color: '#2471A3' },
    });

    const STORY_INLINE_ICONS = Object.freeze({
        D: '/static/assets/ui-icons/damage.svg',
        H: '/static/assets/ui-icons/hit-point.svg',
        E: '/static/assets/ui-icons/elixir.svg',
        M: '/static/assets/ui-icons/magic.svg',
    });

    const STORY_STATUS_ICONS = Object.freeze({
        shield: 'shield',
        power: 'triangle',
        temporary_power: 'triangle',
        endurance: 'armor',
        weak: 'weakness',
        vulnerable: 'fragile',
        fragile: 'fragile',
        evade: 'dodge',
        poison: 'poison',
        stun: 'stunned',
        reflection: 'nazar',
        wither: 'stagnation',
        broken: 'fracture',
        rockfall: 'root_status',
    });
    const STORY_TERM_LONG_PRESS_MS = 430;
    const STORY_TERM_MOVE_CANCEL_PX = 12;

    const STORY_RESOURCE_TERMS = Object.freeze({
        D: {
            name: { zh: '物理伤害', en: 'Physical Damage' },
            description: { zh: '物理伤害会减少目标的H', en: 'Physical damage reduces the target’s H' },
        },
        H: {
            name: { zh: '生命', en: 'Health' },
            description: { zh: 'H降至0时阵亡', en: 'A unit is defeated when its H reaches 0' },
        },
        E: {
            name: { zh: '能量', en: 'Elixir' },
            description: { zh: '打出牌时消耗的基础资源', en: 'The primary resource spent to play cards' },
        },
        M: {
            name: { zh: '魔力', en: 'Magic' },
            description: { zh: '部分牌打出时消耗的魔力资源', en: 'The magic resource spent by some cards' },
        },
    });

    const STORY_CARD_TYPE_LABELS = Object.freeze({
        thorn: 'Thorn',
        bloom: 'Bloom',
        root: 'Root',
        guard: 'Guard',
        curse: 'Curse',
        infect: 'Infect',
    });

    const STORY_RARITY_ORDER = Object.freeze([
        'primary',
        'common',
        'rare',
        'ultra',
        'super',
        'special',
    ]);

    const STORY_CARD_TYPE_COLORS = Object.freeze({
        thorn: 'var(--thorn)',
        bloom: 'var(--bloom)',
        root: 'var(--root)',
        guard: 'var(--guard)',
        curse: 'var(--curse)',
        infect: 'var(--infect)',
    });

    const TEXT = {
        en: {
            title: 'Story Mode', account: 'Player', back: 'Back', loading: 'Loading journey',
            onlinePlayers: (value) => `Online Players: ${value}`,
            afkTitle: 'AFK Check',
            afkPrompt: (countdown) => `Hold the round button and release it when it glows. Time left: ${countdown}.`,
            afkHold: 'Hold', afkReady: 'Hold the button when ready.', afkHolding: 'Keep holding...',
            afkVerifying: 'Verifying...', afkPassed: 'AFK check passed',
            afkTooShort: 'Held too briefly. Try again.', afkTooLong: 'Held too long. Try again.',
            afkTimedOut: 'AFK check timed out. Returning to the home page...',
            afkFailed: 'The check failed. Try again.',
            chatTitle: 'Chat', chatConnecting: 'Connecting...', chatConnected: 'Lobby chat',
            chatDisconnected: 'Disconnected. Reconnecting...', chatPlaceholder: 'Type a message...',
            chatSend: 'Send', chatCollapse: 'Collapse chat',
            chatOriginMultiplayer: 'Multiplayer', chatOriginStory: 'Story',
            chatSpectator: 'Spectating', chatYesterday: 'Yesterday', chatBeforeYesterday: 'The day before yesterday',
            chatConsole: 'Console',
            chatUnread: (count) => `${count} unread message(s)`,
            emptyTitle: 'A new journey', start: 'Start', stage: 'Stage', biome: 'Region', gold: 'Gold',
            route: 'Route', abandon: 'End Journey', abandonTitle: 'End this journey?',
            abandonMessage: 'This run will be marked as ended.', resetMap: 'Reset Map',
            surrender: 'Surrender', surrenderTitle: 'Surrender?', surrenderCopy: 'This journey will end in defeat immediately.',
            resetTitle: 'Reset the map?', resetMessage: 'A new route will be generated from Floor 1.',
            mapReset: 'Map reset', cancel: 'Cancel', confirm: 'Confirm', garden: 'Garden',
            saveManager: 'Save / Load', saveCopy: 'Available on the route map. The latest 3 saves are kept.',
            saveCurrent: 'Save Current Progress', loadSave: 'Load', noSaves: 'No manual saves yet',
            deleteSave: 'Delete', deleteSaveTitle: 'Delete this save?', deleteSaveCopy: 'This manual save will be removed.', saveDeleted: 'Save deleted',
            saveCurrentSlot: 'Current', savePreviousSlot: (value) => `Previous ${value}`,
            saveSucceeded: 'Journey saved', loadSucceeded: 'Journey loaded',
            loadSaveTitle: 'Load this save?', loadSaveCopy: 'Your current route progress will be replaced.',
            saveOnlyOnMap: 'Manual saves are only available on the route map',
            viewMap: 'View Map', returnToCombat: 'Return to Battle',
            restartFloor: 'Restart Floor', restartFloorTitle: 'Restart this floor?',
            restartFloorCopy: 'All actions on this floor will be undone. The same random results will be used.',
            restartFloorSucceeded: 'Floor restarted', shopServiceUsed: 'This shop’s deck service has already been used',
            easyRelicTitle: 'Choose an Easy talent', easyRelicCopy: 'Choose 1 of 3 talents, then choose your starting blessing.',
            blessingTitle: 'Choose a starting blessing', blessingCopy: 'Choose one for this journey.',
            blessingChooseCard: 'Choose a deck card', blessingBack: 'Back to blessings',
            transform: 'Transform', blessingRewardCopy: 'Choose one card from each reward.',
            blessingCardReward: (index, total) => `Card reward ${index}/${total}`,
            intent: 'Intent', endTurn: 'End Turn', playerTurn: 'Your Turn', enemyTurn: 'Enemy Turn', close: 'Close',
            drawPile: 'Draw', discardPile: 'Discard', exilePile: 'Exile',
            talentOverview: 'Talents', viewTalentOverview: 'View Talents',
            talentTotal: (count) => `${count} talent(s)`, noTalents: 'No talents acquired',
            runDeck: 'Full Deck', viewRunDeck: 'View Full Deck',
            codexTitle: 'Story Compendium', viewCodex: 'View Story Compendium',
            codexCards: 'Cards', codexEnemies: 'Enemies', codexTalents: 'Talents', codexTerms: 'Terms',
            codexSearch: 'Search discovered content', codexRarity: 'Rarity', codexType: 'Type',
            codexAll: 'All', codexClear: 'Clear', codexResults: (count) => `${count} result(s)`,
            codexDiscovered: (found, total) => `Discovered ${found}/${total}`,
            codexEmpty: 'No matching discoveries', codexUnknownTalent: 'Unnamed blessing',
            codexRelics: 'Talents', codexBlessings: 'Blessings', codexStatuses: 'Statuses',
            codexTags: 'Tags', codexTraits: 'Enemy effects', codexResources: 'Resources',
            codexHealth: 'Health', codexObservedIntents: (count) => `${count} observed intent(s)`,
            codexNew: 'New compendium entry', codexNewCount: (count) => `${count} new compendium entries`,
            battleWon: 'Battle won', chooseCard: 'Choose a card', skip: 'Skip card',
            rewards: 'Battle rewards', rewardCopy: 'Claim each reward before continuing.',
            claim: 'Claim', claimed: 'Claimed', cardReward: 'Card reward', talentReward: 'Talent',
            directLeave: 'Leave without taking more', claimChestGold: 'Take Gold', claimChestTalent: 'Take Talent',
            cannotRemove: 'Cannot be removed',
            continueJourney: 'Continue', gainedGold: (value) => `Gained ${value} G.`,
            goldReward: (value) => `${value} G`, room: 'Room', restTitle: 'Rest Site',
            restCopy: 'Recover H or upgrade one card.', heal: 'Recover H', upgrade: 'Upgrade',
            shopCards: 'Cards', shopTalents: 'Talents', remove: 'Remove',
            roomActions: 'Actions', restGold: 'Gold', plantDandelion: 'Plant Dandelion',
            noShopCards: 'No cards are available', noShopTalents: 'No talents are available',
            noUpgradableCards: 'No cards can be upgraded',
            confirmUpgradeTitle: 'Confirm upgrade', confirmRemoveTitle: 'Confirm removal',
            permanentDeckChange: 'This change lasts for the rest of this journey.',
            removedFromDeck: 'Removed from the deck', beforeChange: 'Before', afterChange: 'After',
            confirmEventTitle: 'Confirm this choice',
            confirmEventCopy: 'This result takes effect immediately and cannot be undone in this room.',
            chestTitle: 'Chest', chestCopy: 'Take any rewards you want, or leave them behind.', openChest: 'Open',
            currentHealth: 'Current H', restRecovery: 'Recovery', chestGold: 'Gold',
            chestTalent: 'Talent', shopWallet: 'Available Gold', removePrice: 'Removal',
            upgradePrice: 'Upgrade', none: 'None',
            eventTitle: 'Garden Event', eventCopy: 'Choose one outcome.', takeGold: 'Take 20 Gold',
            recoverHealth: 'Recover 15 H', shopTitle: 'Shop', shopCopy: 'Spend Gold or leave.',
            buy: (value) => `Buy · ${value}`, leave: 'Leave', journeyComplete: 'Journey complete',
            journeyCompleteCopy: 'You crossed the Garden route.', journeyFailed: 'Journey ended',
            journeyFailedCopy: 'Your route ends here, but the next map is waiting.', newJourney: 'New Journey',
            requestFailed: 'Story data is temporarily unavailable', stateUpdated: 'State synchronized',
            upgraded: 'Upgraded', shield: 'Shield', power: 'Power', weak: 'Weak', vulnerable: 'Vulnerable',
            summon: 'Summon', defeated: 'Defeated', allies: 'All creatures', playerSide: 'Player side', self: 'Self', addCard: 'Add card', consume: 'Consume',
            developerMode: 'Developer Mode', devJump: 'Jump to Level', devFloor: 'Floor', devRoom: 'Room',
            devValues: 'Set Values', devApply: 'Apply Values', devJumpButton: 'Jump',
            devValuesUpdated: 'Values updated', devJumped: 'Level loaded',
            pileEmpty: 'No cards here', chooseEnemy: 'Choose the enemy', chooseSelf: 'Choose yourself',
            playSelfAnywhere: 'Click anywhere to play on yourself', playAnywhere: 'Click anywhere to play',
            chooseCardHint: 'Choose a card', damagePrediction: 'Damage',
            chooseCards: 'Choose cards', chooseExact: (value) => `Choose ${value} card(s).`,
            chooseUpTo: (value) => `Choose up to ${value} card(s).`,
            cardTerms: 'Card Terms', statusTerms: 'Status Term', actionTerms: 'Action Term', traitTerms: 'Effect Term', talentTerms: 'Talent Details', noCardTerms: 'No additional terms',
            beforeUpgrade: 'Before Upgrade', afterUpgrade: 'After Upgrade',
            cardTypes: { thorn: 'Thorn', bloom: 'Bloom', root: 'Root', guard: 'Guard', curse: 'Curse', infect: 'Infect' },
            pileTotal: (label, count) => `${label}: ${count} cards`,
            floor: (value) => `Floor ${value}`,
            rooms: { journey_setup: 'New Journey', blessing: 'Blessing', combat: 'Battle', elite: 'Elite', event: 'Event', rest: 'Rest', shop: 'Shop', chest: 'Chest', boss: 'Boss' },
            roomMarks: { blessing: 'B', combat: 'C', elite: 'E', event: '?', rest: 'R', shop: '$', chest: 'T', boss: 'X' },
        },
        zh: {
            title: '故事模式', account: '玩家', back: '返回', loading: '载入旅程', emptyTitle: '一段新的旅程',
            onlinePlayers: (value) => `在线玩家：${value}`,
            afkTitle: 'AFK Check',
            afkPrompt: (countdown) => `请在 ${countdown} 内按住圆形按钮，按钮明显发光后松开。`,
            afkHold: '按住', afkReady: '准备好了就按住按钮。', afkHolding: '保持按住...',
            afkVerifying: '正在验证...', afkPassed: '挂机检测已通过',
            afkTooShort: '按得太短了，请重试', afkTooLong: '按得太久了，请重试',
            afkTimedOut: '挂机检测已超时，正在返回主页...',
            afkFailed: '检测失败，请重试',
            chatTitle: '聊天', chatConnecting: '正在连接...', chatConnected: '大厅聊天',
            chatDisconnected: '连接已断开，正在重连...', chatPlaceholder: '输入消息...',
            chatSend: '发送', chatCollapse: '收起聊天',
            chatOriginMultiplayer: '多人', chatOriginStory: '故事',
            chatSpectator: '观战', chatYesterday: '昨天', chatBeforeYesterday: '前天', chatConsole: '控制台',
            chatUnread: (count) => `${count} 条未读消息`,
            start: '开始', stage: '阶段', biome: '区域', gold: '金币', route: '路线', abandon: '结束旅程',
            abandonTitle: '结束旅程？', abandonMessage: '当前进度将被记录为已结束。', resetMap: '重置地图',
            surrender: '投降', surrenderTitle: '确认投降？', surrenderCopy: '本次旅程会立即失败。',
            resetTitle: '重置地图？', resetMessage: '将重新生成路线并返回第一层。', mapReset: '地图已重置',
            cancel: '取消', confirm: '确定', garden: '花园', blessingTitle: '选择初始赐福',
            saveManager: '存读档', saveCopy: '仅可在路线选择界面保存或读取，最多保留最近3份。',
            saveCurrent: '保存当前进度', loadSave: '读取', noSaves: '暂无手动存档',
            deleteSave: '删除', deleteSaveTitle: '删除此存档？', deleteSaveCopy: '该手动存档将被移除。', saveDeleted: '存档已删除',
            saveCurrentSlot: '当前存档', savePreviousSlot: (value) => `前 ${value} 次存档`,
            saveSucceeded: '旅程进度已保存', loadSucceeded: '旅程进度已读取',
            loadSaveTitle: '读取此存档？', loadSaveCopy: '当前路线进度将被所选存档覆盖。',
            saveOnlyOnMap: '只能在路线选择界面使用手动存读档',
            viewMap: '查看地图', returnToCombat: '返回战斗',
            restartFloor: '重新开始本层', restartFloorTitle: '重新开始本层？',
            restartFloorCopy: '本层内的全部操作将被撤销，并以相同随机结果重新开始。',
            restartFloorSucceeded: '已重新开始本层', shopServiceUsed: '本店的牌组服务已经使用',
            easyRelicTitle: '选择简单难度天赋', easyRelicCopy: '从3项天赋中选择1项，然后继续选择初始赐福。',
            blessingCopy: '本次旅程只能选择一项。', blessingChooseCard: '选择一张牌组中的牌',
            blessingBack: '返回赐福选择', transform: '变化',
            blessingRewardCopy: '每次卡牌奖励选择1张牌。',
            blessingCardReward: (index, total) => `卡牌奖励 ${index}/${total}`,
            intent: '意图', endTurn: '结束回合', playerTurn: '玩家回合', enemyTurn: '生物回合', close: '关闭', drawPile: '抽牌堆',
            discardPile: '弃牌堆', exilePile: '放逐区',
            talentOverview: '天赋总览', viewTalentOverview: '查看天赋总览',
            talentTotal: (count) => `共 ${count} 项天赋`, noTalents: '尚未获得天赋',
            runDeck: '总牌库', viewRunDeck: '查看总牌库',
            codexTitle: '故事图鉴', viewCodex: '查看故事图鉴',
            codexCards: '卡牌', codexEnemies: '生物', codexTalents: '天赋', codexTerms: '术语',
            codexSearch: '搜索已发现内容', codexRarity: '稀有度', codexType: '类型',
            codexAll: '全选', codexClear: '清空', codexResults: (count) => `${count} 项`,
            codexDiscovered: (found, total) => `已发现 ${found}/${total}`,
            codexEmpty: '没有符合条件的已发现内容', codexUnknownTalent: '未命名赐福',
            codexRelics: '天赋', codexBlessings: '赐福', codexStatuses: '状态',
            codexTags: '标签', codexTraits: '生物特殊效果', codexResources: '资源',
            codexHealth: '生命', codexObservedIntents: (count) => `已观察 ${count} 个意图`,
            codexNew: '发现了新的图鉴内容', codexNewCount: (count) => `发现了 ${count} 项新的图鉴内容`,
            battleWon: '战斗胜利', chooseCard: '选择一张牌',
            skip: '跳过卡牌', rewards: '战斗奖励', rewardCopy: '逐项领取奖励后继续前进。',
            claim: '领取', claimed: '已领取', cardReward: '卡牌奖励', talentReward: '天赋',
            directLeave: '直接离开', claimChestGold: '领取金币', claimChestTalent: '领取天赋',
            cannotRemove: '无法删除',
            continueJourney: '继续前进', gainedGold: (value) => `获得 ${value}G。`,
            goldReward: (value) => `${value}G`, room: '房间', restTitle: '休息区',
            restCopy: '回复生命，或升级一张牌。', heal: '回复生命', upgrade: '升级', chestTitle: '宝箱',
            shopCards: '卡牌', shopTalents: '天赋', remove: '移除',
            roomActions: '选项', restGold: '金币', plantDandelion: '种植蒲公英',
            noShopCards: '暂无可购买卡牌', noShopTalents: '暂无可购买天赋',
            noUpgradableCards: '暂无可升级卡牌',
            confirmUpgradeTitle: '确认升级', confirmRemoveTitle: '确认移除',
            permanentDeckChange: '此变化将在本次旅程中永久生效。',
            removedFromDeck: '从牌组中移除', beforeChange: '变化前', afterChange: '变化后',
            confirmEventTitle: '确认事件选择',
            confirmEventCopy: '此结果将立即生效，且无法在当前节点内撤回。',
            chestCopy: '可以分别领取想要的奖励，也可以直接离开。', openChest: '打开', eventTitle: '花园事件',
            currentHealth: '当前生命', restRecovery: '本次回复', chestGold: '金币',
            chestTalent: '天赋', shopWallet: '可用金币', removePrice: '移除费用',
            upgradePrice: '升级费用', none: '无',
            eventCopy: '选择一种结果。', takeGold: '获得20金币', recoverHealth: '回复15H', shopTitle: '商店',
            shopCopy: '消耗金币购买物品，也可以直接离开。', buy: (value) => `购买 · ${value}`, leave: '离开',
            journeyComplete: '旅程完成', journeyCompleteCopy: '你已经穿过了花园路线。', journeyFailed: '旅程结束',
            journeyFailedCopy: '本次路线止步于此，下一张地图仍在等待。', newJourney: '开始新旅程',
            requestFailed: '故事记录暂时不可用', stateUpdated: '状态已同步', upgraded: '已升级',
            shield: '护盾', power: '力量', weak: '虚弱', vulnerable: '易损', floor: (value) => `第 ${value} 层`,
            summon: '召唤', defeated: '阵亡', allies: '全体生物', playerSide: '玩家方', self: '自己', addCard: '加入卡牌', consume: '吞噬',
            developerMode: '开发人员模式', devJump: '关卡跳转', devFloor: '层数', devRoom: '房间',
            devValues: '数值设置', devApply: '应用数值', devJumpButton: '跳转',
            devValuesUpdated: '数值已更新', devJumped: '已载入所选关卡',
            pileEmpty: '这里没有牌', chooseEnemy: '点击生物头像以选择目标', chooseSelf: '点击自己的头像以选择目标',
            playSelfAnywhere: '点击场地任意位置对自己使用', playAnywhere: '点击场地任意位置打出',
            chooseCardHint: '选择一张手牌', damagePrediction: '伤害预测',
            chooseCards: '选择卡牌', chooseExact: (value) => `选择 ${value} 张牌。`,
            chooseUpTo: (value) => `选择至多 ${value} 张牌。`,
            cardTerms: '卡牌术语', statusTerms: '状态术语', actionTerms: '行动术语', traitTerms: '特殊效果术语', talentTerms: '天赋说明', noCardTerms: '没有额外术语',
            beforeUpgrade: '升级前', afterUpgrade: '升级后',
            cardTypes: { thorn: '攻击', bloom: '技能', root: '装备', guard: '反制', curse: '诅咒', infect: '状态牌' },
            pileTotal: (label, count) => `${label}：${count} 张`,
            rooms: { journey_setup: '新旅程', blessing: '赐福', combat: '战斗', elite: '精英', event: '事件', rest: '休息', shop: '商店', chest: '宝箱', boss: '首领' },
            roomMarks: { blessing: '赐', combat: '战', elite: '精', event: '事', rest: '息', shop: '店', chest: '宝', boss: '首' },
        },
        fr: {
            title: 'Mode histoire', account: 'Joueur', back: 'Retour', loading: 'Chargement du voyage',
            onlinePlayers: (value) => `Joueurs en ligne : ${value}`,
            afkTitle: 'Contrôle AFK',
            afkPrompt: (countdown) => `Maintenez le bouton rond, puis relâchez-le lorsqu’il brille. Temps restant : ${countdown}.`,
            afkHold: 'Maintenir', afkReady: 'Maintenez le bouton quand vous êtes prêt.',
            afkHolding: 'Continuez à maintenir...', afkVerifying: 'Vérification...',
            afkPassed: 'Contrôle AFK réussi', afkTooShort: 'Maintien trop court. Réessayez.',
            afkTooLong: 'Maintien trop long. Réessayez.',
            afkTimedOut: 'Délai du contrôle AFK dépassé. Retour à l’accueil...',
            afkFailed: 'Échec du contrôle. Réessayez.',
            chatTitle: 'Chat', chatConnecting: 'Connexion...', chatConnected: 'Chat du salon',
            chatDisconnected: 'Déconnecté. Reconnexion...', chatPlaceholder: 'Écrire un message...',
            chatSend: 'Envoyer', chatCollapse: 'Réduire le chat',
            chatOriginMultiplayer: 'Multijoueur', chatOriginStory: 'Histoire',
            chatSpectator: 'Spectateur', chatYesterday: 'Hier', chatBeforeYesterday: 'Avant-hier',
            chatConsole: 'Console',
            chatUnread: (count) => `${count} message(s) non lu(s)`,
            emptyTitle: 'Un nouveau voyage', start: 'Commencer', stage: 'Étape', biome: 'Région', gold: 'Or',
            route: 'Route', abandon: 'Terminer le voyage', blessingTitle: 'Choisir une bénédiction',
            surrender: 'Abandonner', surrenderTitle: 'Abandonner ?', surrenderCopy: 'Ce voyage se soldera immédiatement par un échec.',
            saveManager: 'Sauvegarder / Charger', saveCopy: 'Disponible sur la carte. Les 3 sauvegardes les plus récentes sont conservées.',
            saveCurrent: 'Sauvegarder', loadSave: 'Charger', noSaves: 'Aucune sauvegarde manuelle',
            deleteSave: 'Supprimer', deleteSaveTitle: 'Supprimer cette sauvegarde ?', deleteSaveCopy: 'Cette sauvegarde manuelle sera retirée.', saveDeleted: 'Sauvegarde supprimée',
            saveCurrentSlot: 'Actuelle', savePreviousSlot: (value) => `Précédente ${value}`,
            saveSucceeded: 'Progression sauvegardée', loadSucceeded: 'Progression chargée',
            loadSaveTitle: 'Charger cette sauvegarde ?', loadSaveCopy: 'La progression actuelle sera remplacée.',
            saveOnlyOnMap: 'La sauvegarde manuelle est disponible uniquement sur la carte',
            easyRelicTitle: 'Choisir un talent facile', easyRelicCopy: 'Choisissez 1 talent parmi 3, puis votre bénédiction initiale.',
            blessingCopy: 'Choisissez-en une pour ce voyage.', blessingChooseCard: 'Choisissez une carte du paquet',
            blessingBack: 'Retour aux bénédictions', transform: 'Transformer',
            blessingRewardCopy: 'Choisissez une carte pour chaque récompense.',
            blessingCardReward: (index, total) => `Récompense de carte ${index}/${total}`,
            intent: 'Intention', endTurn: 'Fin du tour',
            drawPile: 'Pioche', discardPile: 'Défausse', exilePile: 'Exil',
            talentOverview: 'Talents', viewTalentOverview: 'Voir les talents',
            talentTotal: (count) => `${count} talent(s)`, noTalents: 'Aucun talent obtenu',
            runDeck: 'Deck complet', viewRunDeck: 'Voir le deck complet', battleWon: 'Victoire',
            codexTitle: 'Compendium', viewCodex: 'Voir le compendium',
            codexCards: 'Cartes', codexEnemies: 'Ennemis', codexTalents: 'Talents', codexTerms: 'Termes',
            codexSearch: 'Rechercher le contenu découvert', codexRarity: 'Rareté', codexType: 'Type',
            codexAll: 'Tout', codexClear: 'Effacer', codexResults: (count) => `${count} résultat(s)`,
            codexDiscovered: (found, total) => `Découvert ${found}/${total}`,
            codexEmpty: 'Aucune découverte correspondante', codexUnknownTalent: 'Bénédiction sans nom',
            codexRelics: 'Talents', codexBlessings: 'Bénédictions', codexStatuses: 'États',
            codexTags: 'Étiquettes', codexTraits: 'Effets ennemis', codexResources: 'Ressources',
            codexHealth: 'Vie', codexObservedIntents: (count) => `${count} intention(s) observée(s)`,
            codexNew: 'Nouvelle entrée du compendium', codexNewCount: (count) => `${count} nouvelles entrées du compendium`,
            chooseCard: 'Choisissez une carte', skip: 'Passer la carte', room: 'Salle', newJourney: 'Nouveau voyage',
            rewards: 'Récompenses du combat', rewardCopy: 'Récupérez chaque récompense avant de continuer.',
            claim: 'Récupérer', claimed: 'Récupéré', cardReward: 'Carte', talentReward: 'Talent',
            directLeave: 'Partir sans rien prendre de plus', claimChestGold: 'Prendre l’or', claimChestTalent: 'Prendre le talent',
            continueJourney: 'Continuer', goldReward: (value) => `${value} G`,
            summon: 'Invocation', allies: 'Toutes les créatures', playerSide: 'Camp joueur', self: 'Soi', addCard: 'Ajouter une carte', consume: 'Absorber',
            developerMode: 'Mode développeur', devJump: 'Changer de niveau', devFloor: 'Étage', devRoom: 'Salle',
            devValues: 'Modifier les valeurs', devApply: 'Appliquer', devJumpButton: 'Aller',
            devValuesUpdated: 'Valeurs mises à jour', devJumped: 'Niveau chargé',
            cardTerms: 'Termes de carte', statusTerms: 'Terme d’état', actionTerms: 'Terme d’action', traitTerms: 'Terme d’effet', talentTerms: 'Détails du talent', noCardTerms: 'Aucun terme supplémentaire',
            beforeUpgrade: 'Avant amélioration', afterUpgrade: 'Après amélioration',
            shopCards: 'Cartes', shopTalents: 'Talents', remove: 'Retirer',
            roomActions: 'Choix', restGold: 'Or', plantDandelion: 'Planter le pissenlit',
            noShopCards: 'Aucune carte disponible', noShopTalents: 'Aucun talent disponible',
            noUpgradableCards: 'Aucune carte ne peut être améliorée',
            confirmUpgradeTitle: 'Confirmer l’amélioration', confirmRemoveTitle: 'Confirmer le retrait',
            permanentDeckChange: 'Ce changement dure pendant tout ce voyage.',
            removedFromDeck: 'Retirée du paquet', beforeChange: 'Avant', afterChange: 'Après',
            confirmEventTitle: 'Confirmer ce choix',
            confirmEventCopy: 'Ce résultat prend effet immédiatement et ne peut pas être annulé dans cette salle.',
            currentHealth: 'H actuels', restRecovery: 'Récupération', chestGold: 'Or',
            chestTalent: 'Talent', shopWallet: 'Or disponible', removePrice: 'Retrait',
            upgradePrice: 'Amélioration', none: 'Aucun', defeated: 'Vaincu',
            garden: 'Jardin', floor: (value) => `Étage ${value}`,
            rooms: { journey_setup: 'Nouveau voyage', blessing: 'Bénédiction', combat: 'Combat', elite: 'Élite', event: 'Événement', rest: 'Repos', shop: 'Boutique', chest: 'Coffre', boss: 'Boss' },
            roomMarks: { blessing: 'B', combat: 'C', elite: 'É', event: '?', rest: 'R', shop: '$', chest: 'T', boss: 'X' },
        },
        ja: {
            title: 'ストーリーモード', account: 'プレイヤー', back: '戻る', loading: '旅を読み込み中',
            onlinePlayers: (value) => `オンラインプレイヤー：${value}`,
            afkTitle: 'AFKチェック',
            afkPrompt: (countdown) => `残り${countdown}以内に丸いボタンを長押しし、光ったら離してください。`,
            afkHold: '長押し', afkReady: '準備ができたら長押ししてください。',
            afkHolding: 'そのまま長押し...', afkVerifying: '確認中...',
            afkPassed: 'AFKチェックに成功しました',
            afkTooShort: '押す時間が短すぎます。もう一度お試しください。',
            afkTooLong: '押す時間が長すぎます。もう一度お試しください。',
            afkTimedOut: 'AFKチェックが時間切れです。ホームへ戻ります...',
            afkFailed: '確認に失敗しました。もう一度お試しください。',
            chatTitle: 'チャット', chatConnecting: '接続中...', chatConnected: 'ロビーチャット',
            chatDisconnected: '切断されました。再接続中...', chatPlaceholder: 'メッセージを入力...',
            chatSend: '送信', chatCollapse: 'チャットを閉じる',
            chatOriginMultiplayer: 'マルチ', chatOriginStory: 'ストーリー',
            chatSpectator: '観戦', chatYesterday: '昨日', chatBeforeYesterday: '一昨日', chatConsole: 'コンソール',
            chatUnread: (count) => `未読メッセージ ${count}件`,
            emptyTitle: '新しい旅', start: '開始', stage: 'ステージ', biome: '地域', gold: 'ゴールド',
            route: 'ルート', abandon: '旅を終了', blessingTitle: '祝福を選択', blessingCopy: '今回の旅で一つ選択します。',
            surrender: '降参', surrenderTitle: '降参しますか？', surrenderCopy: 'この旅はすぐに敗北として終了します。',
            saveManager: 'セーブ / ロード', saveCopy: 'ルート画面でのみ利用できます。最新3件を保存します。',
            saveCurrent: '現在の進行を保存', loadSave: 'ロード', noSaves: '手動セーブはありません',
            deleteSave: '削除', deleteSaveTitle: 'このセーブを削除しますか？', deleteSaveCopy: 'この手動セーブは削除されます。', saveDeleted: 'セーブを削除しました',
            saveCurrentSlot: '最新', savePreviousSlot: (value) => `${value}つ前`,
            saveSucceeded: '進行を保存しました', loadSucceeded: '進行を読み込みました',
            loadSaveTitle: 'このセーブを読み込みますか？', loadSaveCopy: '現在のルート進行は上書きされます。',
            saveOnlyOnMap: '手動セーブはルート画面でのみ利用できます',
            easyRelicTitle: 'イージー天賦を選択', easyRelicCopy: '3つから1つ選び、その後に初期祝福を選択します。',
            blessingChooseCard: 'デッキのカードを選択', blessingBack: '祝福選択に戻る',
            transform: '変化', blessingRewardCopy: '各カード報酬から1枚選びます。',
            blessingCardReward: (index, total) => `カード報酬 ${index}/${total}`,
            intent: '意図', endTurn: 'ターン終了', drawPile: '山札', discardPile: '捨て札', exilePile: '追放',
            talentOverview: '天賦一覧', viewTalentOverview: '天賦一覧を見る',
            talentTotal: (count) => `天賦 ${count}個`, noTalents: '天賦を獲得していません',
            runDeck: '全デッキ', viewRunDeck: '全デッキを見る',
            codexTitle: '物語図鑑', viewCodex: '物語図鑑を見る',
            codexCards: 'カード', codexEnemies: '敵', codexTalents: '天賦', codexTerms: '用語',
            codexSearch: '発見済みを検索', codexRarity: 'レア度', codexType: 'タイプ',
            codexAll: 'すべて', codexClear: '解除', codexResults: (count) => `${count}件`,
            codexDiscovered: (found, total) => `発見 ${found}/${total}`,
            codexEmpty: '一致する発見はありません', codexUnknownTalent: '名前のない祝福',
            codexRelics: '天賦', codexBlessings: '祝福', codexStatuses: '状態',
            codexTags: 'タグ', codexTraits: '敵の特殊効果', codexResources: 'リソース',
            codexHealth: '生命', codexObservedIntents: (count) => `確認済み意図 ${count}個`,
            codexNew: '図鑑に新しい項目を発見', codexNewCount: (count) => `図鑑に${count}件を新発見`,
            battleWon: '戦闘勝利', chooseCard: 'カードを選択', skip: 'カードをスキップ', room: '部屋',
            rewards: '戦闘報酬', rewardCopy: 'すべての報酬を受け取ってから先へ進みます。',
            claim: '受け取る', claimed: '受取済み', cardReward: 'カード報酬', talentReward: '天賦',
            directLeave: '残りを受け取らず退出', claimChestGold: 'ゴールドを受け取る', claimChestTalent: '天賦を受け取る',
            continueJourney: '進む', goldReward: (value) => `${value} G`,
            summon: '召喚', allies: '全生物', playerSide: 'プレイヤー側', self: '自身', addCard: 'カード追加', consume: '吸収',
            developerMode: '開発者モード', devJump: 'ステージ移動', devFloor: '階', devRoom: '部屋',
            devValues: '数値設定', devApply: '適用', devJumpButton: '移動',
            devValuesUpdated: '数値を更新しました', devJumped: 'ステージを読み込みました',
            cardTerms: 'カード用語', statusTerms: '状態用語', actionTerms: '行動用語', traitTerms: '特殊効果用語', talentTerms: '天賦の説明', noCardTerms: '追加用語なし',
            beforeUpgrade: 'アップグレード前', afterUpgrade: 'アップグレード後',
            shopCards: 'カード', shopTalents: '天賦', remove: '削除',
            roomActions: '選択肢', restGold: 'ゴールド', plantDandelion: 'タンポポを植える',
            noShopCards: '購入できるカードはありません', noShopTalents: '購入できる天賦はありません',
            noUpgradableCards: 'アップグレードできるカードはありません',
            confirmUpgradeTitle: 'アップグレード確認', confirmRemoveTitle: '削除確認',
            permanentDeckChange: 'この旅の間、変更は元に戻せません。',
            removedFromDeck: 'デッキから削除', beforeChange: '変更前', afterChange: '変更後',
            confirmEventTitle: 'イベント選択の確認',
            confirmEventCopy: '結果は直ちに適用され、この部屋では取り消せません。',
            currentHealth: '現在のH', restRecovery: '回復量', chestGold: 'ゴールド',
            chestTalent: '天賦', shopWallet: '所持ゴールド', removePrice: '削除費用',
            upgradePrice: '強化費用', none: 'なし', defeated: '撃破',
            newJourney: '新しい旅', garden: 'ガーデン', floor: (value) => `${value}階`,
            rooms: { journey_setup: '新しい旅', blessing: '祝福', combat: '戦闘', elite: 'エリート', event: 'イベント', rest: '休憩', shop: 'ショップ', chest: '宝箱', boss: 'ボス' },
            roomMarks: { blessing: '祝', combat: '戦', elite: '精', event: '？', rest: '休', shop: '店', chest: '宝', boss: '首' },
        },
    };

    function language() {
        let value = 'zh';
        try {
            const storage = window.GTN_STORAGE || window.localStorage;
            value = String(storage.getItem('gtn_lang') || 'zh').toLowerCase();
        } catch (_) {}
        return Object.prototype.hasOwnProperty.call(TEXT, value) ? value : 'zh';
    }

    function loadStoryMainFont() {
        if (!('FontFace' in window)) return;
        const fonts = [
            new FontFace(
                'Kreadon',
                "url('/fonts/Kreadon-Regular.subset.woff2?v=3') format('woff2')",
                { weight: '400', style: 'normal' },
            ),
            new FontFace(
                'Kreadon Demi',
                "url('/fonts/Kreadon-Demi.subset.woff2?v=3') format('woff2')",
                { weight: '700', style: 'normal' },
            ),
        ];
        Promise.all(fonts.map((font) => font.load())).then((loadedFonts) => {
            loadedFonts.forEach((loaded) => document.fonts.add(loaded));
            document.documentElement.classList.add('fonts-loaded-main');
            scheduleVisibleStoryCardEffectFits();
        }).catch(() => {});
    }

    const lang = language();
    const t = {
        ...TEXT.en,
        ...(TEXT[lang] || {}),
        rooms: { ...TEXT.en.rooms, ...((TEXT[lang] || {}).rooms || {}) },
        roomMarks: { ...TEXT.en.roomMarks, ...((TEXT[lang] || {}).roomMarks || {}) },
        cardTypes: { ...TEXT.en.cardTypes, ...((TEXT[lang] || {}).cardTypes || {}) },
    };

    class StoryApiError extends Error {
        constructor(message, status, payload) {
            super(message);
            this.status = status;
            this.payload = payload || {};
        }
    }

    function setText(id, value) {
        const element = $(id);
        if (element) element.textContent = value;
    }

    function localize(value) {
        if (!value || typeof value !== 'object') return String(value || '');
        return String(value[lang] || value.en || value.zh || '');
    }

    function normalizeSkin(raw) {
        const source = raw && typeof raw === 'object' ? raw : {};
        const color = /^#[0-9a-f]{6}$/i.test(String(source.primary_color || ''))
            ? String(source.primary_color).toUpperCase()
            : '#FFE763';
        const eyeShape = ['oval', 'rectangle', 'diamond', 'hexagon'].includes(String(source.eye_shape || '').toLowerCase())
            ? String(source.eye_shape).toLowerCase()
            : 'oval';
        return { primaryColor: color, eyeShape };
    }

    function skinBorderColor(color) {
        const hex = String(color || '#FFE763').slice(1);
        const channels = [0, 2, 4].map((offset) => Math.round(parseInt(hex.slice(offset, offset + 2), 16) * 0.81));
        return `#${channels.map((value) => value.toString(16).padStart(2, '0')).join('')}`.toUpperCase();
    }

    function skinIsDark(color) {
        const hex = String(color || '#FFE763').slice(1);
        const channels = [0, 2, 4].map((offset) => parseInt(hex.slice(offset, offset + 2), 16) / 255)
            .map((value) => value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
        return (0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]) < 0.22;
    }

    function storySkinMouthPathAt(t) {
        const amount = Math.max(0, Math.min(1, Number(t) || 0));
        const values = STORY_SKIN_MOUTH_NORMAL_POINTS.map((base, index) => {
            const next = STORY_SKIN_MOUTH_HURT_POINTS[index];
            return Number((base + (next - base) * amount).toFixed(2));
        });
        return `M ${values[0]} ${values[1]} C ${values[2]} ${values[3]} ${values[4]} ${values[5]} ${values[6]} ${values[7]}`;
    }

    function setStorySkinMouthT(avatar, t) {
        if (!avatar) return;
        const amount = Math.max(0, Math.min(1, Number(t) || 0));
        avatar.querySelector('.skin-mouth-line')?.setAttribute('d', storySkinMouthPathAt(amount));
        avatar.dataset.skinMouthT = String(amount);
    }

    function storySkinMouthT(avatar) {
        const stored = Number(avatar?.dataset.skinMouthT);
        return Number.isFinite(stored) ? Math.max(0, Math.min(1, stored)) : 0;
    }

    function animateStorySkinMouthTo(avatar, targetT) {
        if (!avatar) return;
        const target = Math.max(0, Math.min(1, Number(targetT) || 0));
        if (storySkinMouthAnimation?.raf) cancelAnimationFrame(storySkinMouthAnimation.raf);
        const start = storySkinMouthT(avatar);
        if (Math.abs(start - target) < 0.01) {
            setStorySkinMouthT(avatar, target);
            storySkinMouthAnimation = null;
            return;
        }
        const duration = 360;
        const startTime = performance.now();
        const animation = { raf: 0 };
        const step = (now) => {
            const raw = Math.max(0, Math.min(1, (now - startTime) / duration));
            const eased = raw < 0.5 ? 4 * raw * raw * raw : 1 - Math.pow(-2 * raw + 2, 3) / 2;
            setStorySkinMouthT(avatar, start + (target - start) * eased);
            if (raw < 1) {
                animation.raf = requestAnimationFrame(step);
            } else {
                setStorySkinMouthT(avatar, target);
                storySkinMouthAnimation = null;
            }
        };
        animation.raf = requestAnimationFrame(step);
        storySkinMouthAnimation = animation;
    }

    function triggerStoryPlayerDamageMood() {
        if (storySkinDamageTimer) clearTimeout(storySkinDamageTimer);
        storySkinDamageUntil = Date.now() + STORY_SKIN_DAMAGE_HOLD_MS;
        const avatar = $('story-player-portrait')?.querySelector('.skin-avatar');
        avatar?.classList.add('skin-mouth-hurt');
        animateStorySkinMouthTo(avatar, 1);
        storySkinDamageTimer = window.setTimeout(() => {
            storySkinDamageTimer = 0;
            storySkinDamageUntil = 0;
            const renderedAvatar = $('story-player-portrait')?.querySelector('.skin-avatar');
            renderedAvatar?.classList.remove('skin-mouth-hurt');
            animateStorySkinMouthTo(renderedAvatar, 0);
        }, STORY_SKIN_DAMAGE_HOLD_MS);
    }

    function renderPlayerSkin() {
        const portrait = $('story-player-portrait');
        if (!portrait) return;
        const skin = normalizeSkin(window.__STORY_ACCOUNT__?.skin);
        const avatar = document.createElement('div');
        const damageMood = storySkinDamageUntil > Date.now();
        avatar.className = `skin-avatar skin-eye-shape-${skin.eyeShape}${skinIsDark(skin.primaryColor) ? ' is-inverted' : ''}${damageMood ? ' skin-mouth-hurt' : ''}`;
        avatar.style.setProperty('--skin-main', skin.primaryColor);
        avatar.style.setProperty('--skin-border', skinBorderColor(skin.primaryColor));
        avatar.innerHTML = `
            <div class="skin-eye skin-eye-left"><span class="skin-pupil"></span></div>
            <div class="skin-eye skin-eye-right"><span class="skin-pupil"></span></div>
            <svg class="skin-mouth" viewBox="0 0 100 56" aria-hidden="true" focusable="false">
                <path class="skin-mouth-line" d="${storySkinMouthPathAt(damageMood ? 1 : 0)}"></path>
            </svg>
        `;
        avatar.dataset.skinMouthT = damageMood ? '1' : '0';
        portrait.replaceChildren(avatar);
    }

    function updateStorySkinEyeTracking(clientX, clientY) {
        const avatar = $('story-player-portrait')?.querySelector('.skin-avatar');
        if (!avatar) return;
        const rect = avatar.getBoundingClientRect();
        if (!rect || rect.width <= 0 || rect.height <= 0) return;
        const dx = Number(clientX) - (rect.left + rect.width / 2);
        const dy = Number(clientY) - (rect.top + rect.height / 2);
        const distance = Math.hypot(dx, dy);
        if (!Number.isFinite(distance) || distance < 1.5) return;
        const lookX = Math.max(-1, Math.min(1, dx / distance));
        const lookY = Math.max(-1, Math.min(1, dy / distance));
        avatar.style.setProperty(
            '--skin-look-x',
            `${(lookX * STORY_SKIN_LOOK_OFFSET_X_PERCENT).toFixed(1)}%`,
        );
        avatar.style.setProperty(
            '--skin-look-y',
            `${(lookY * STORY_SKIN_LOOK_OFFSET_Y_PERCENT).toFixed(1)}%`,
        );
    }

    function applyText() {
        document.documentElement.lang = lang;
        document.title = `${t.title} | Garden of Thorn`;
        const values = {
            'story-title': t.title, 'story-loading-label': t.loading,
            'story-empty-title': t.emptyTitle, 'story-start': t.start, 'story-stage-label': t.stage,
            'story-biome-label': t.biome, 'story-gold-label': t.gold, 'story-map-title': t.route,
            'story-save-open': t.saveManager,
            'story-save-open-global-label': t.saveManager,
            'story-combat-map': t.viewMap,
            'story-map-return': t.returnToCombat,
            'story-save-title': t.saveManager,
            'story-save-copy': t.saveCopy,
            'story-save-create': t.saveCurrent,
            'story-save-load-title': t.loadSaveTitle,
            'story-save-load-copy': t.loadSaveCopy,
            'story-save-load-cancel': t.cancel,
            'story-save-load-confirm': t.loadSave,
            'story-save-delete-title': t.deleteSaveTitle,
            'story-save-delete-copy': t.deleteSaveCopy,
            'story-save-delete-cancel': t.cancel,
            'story-save-delete-confirm': t.deleteSave,
            'story-restart-floor': t.restartFloor,
            'story-restart-floor-title': t.restartFloorTitle,
            'story-restart-floor-copy': t.restartFloorCopy,
            'story-restart-floor-cancel': t.cancel,
            'story-restart-floor-confirm': t.restartFloor,
            'story-surrender': t.surrender,
            'story-surrender-title': t.surrenderTitle,
            'story-surrender-copy': t.surrenderCopy,
            'story-surrender-cancel': t.cancel,
            'story-surrender-confirm': t.surrender,
            'story-talent-overview-label': t.talentOverview,
            'story-run-deck-label': t.runDeck,
            'story-codex-open-label': t.codexTitle,
            'story-codex-title': t.codexTitle,
            'story-codex-tab-cards': t.codexCards,
            'story-codex-tab-enemies': t.codexEnemies,
            'story-codex-tab-talents': t.codexTalents,
            'story-codex-tab-terms': t.codexTerms,
            'story-reset-map': t.resetMap,
            'story-reset-title': t.resetTitle, 'story-reset-message': t.resetMessage,
            'story-reset-cancel': t.cancel, 'story-reset-confirm': t.confirm,
            'story-blessing-title': t.blessingTitle, 'story-blessing-copy': t.blessingCopy,
            'story-intent-label': t.intent, 'story-end-turn': t.endTurn,
            'story-pile-close': t.close,
            'story-reward-skip': t.skip, 'story-reward-leave': t.directLeave,
            'story-reward-continue': t.continueJourney,
            'story-terminal-new': t.newJourney,
            'story-dev-toggle': t.developerMode, 'story-dev-title': t.developerMode,
            'story-dev-jump-label': t.devJump, 'story-dev-floor-label': t.devFloor,
            'story-dev-node-label': t.devRoom, 'story-dev-values-label': t.devValues,
            'story-dev-jump': t.devJumpButton, 'story-dev-apply': t.devApply,
            'story-dev-gold-label': t.gold,
            'story-deck-change-before-label': t.beforeChange,
            'story-deck-change-after-label': t.afterChange,
            'story-deck-change-cancel': t.cancel,
            'story-deck-change-confirm': t.confirm,
            'story-event-confirm-cancel': t.cancel,
            'story-event-confirm-submit': t.confirm,
            'story-chat-toggle-label': t.chatTitle,
            'story-chat-title': t.chatTitle,
            'story-chat-send': t.chatSend,
        };
        Object.entries(values).forEach(([id, value]) => setText(id, value));
        updateStoryPresenceDisplay();
        updateStoryStatusBar();
        updateStorySurrenderControl();
        const back = $('story-back');
        if (back) {
            back.title = t.back;
            back.setAttribute('aria-label', t.back);
        }
        const runDeck = $('story-run-deck');
        if (runDeck) {
            runDeck.title = t.viewRunDeck;
            runDeck.setAttribute('aria-label', t.viewRunDeck);
        }
        const codex = $('story-codex-open');
        if (codex) {
            codex.title = t.viewCodex;
            codex.setAttribute('aria-label', t.viewCodex);
        }
        const codexSearch = $('story-codex-search');
        if (codexSearch) {
            codexSearch.placeholder = t.codexSearch;
            codexSearch.setAttribute('aria-label', t.codexSearch);
        }
        $('story-codex-close')?.setAttribute('aria-label', t.close);
        const talentOverview = $('story-talent-overview');
        if (talentOverview) {
            talentOverview.title = t.viewTalentOverview;
            talentOverview.setAttribute('aria-label', t.viewTalentOverview);
        }
        const devClose = $('story-dev-close');
        if (devClose) devClose.setAttribute('aria-label', t.close);
        const chatClose = $('story-chat-close');
        if (chatClose) chatClose.setAttribute('aria-label', t.chatCollapse);
        const chatInput = $('story-chat-input');
        if (chatInput) {
            chatInput.placeholder = t.chatPlaceholder;
            chatInput.setAttribute('aria-label', t.chatPlaceholder);
        }
        updateStoryChatConnectionUi();
        updateStoryChatUnreadBadge();
    }

    function showToast(message) {
        const toast = $('story-toast');
        if (!toast) return;
        toast.textContent = String(message || t.requestFailed);
        toast.classList.remove('hidden');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => toast.classList.add('hidden'), 2400);
    }

    function developerFloors(state) {
        return (state?.map?.floors || []).filter((floor) => Number(floor?.floor) > 1);
    }

    function renderDeveloperNodes(state, preferredNodeId = '') {
        const floorSelect = $('story-dev-floor');
        const nodeSelect = $('story-dev-node');
        if (!floorSelect || !nodeSelect) return;
        const floor = Number(floorSelect.value || 0);
        const floorData = developerFloors(state).find((item) => Number(item.floor) === floor);
        nodeSelect.replaceChildren();
        (floorData?.nodes || []).forEach((node, index) => {
            const option = document.createElement('option');
            option.value = String(node.id || '');
            option.textContent = `${index + 1}. ${t.rooms[node.type] || node.type || t.room}`;
            nodeSelect.append(option);
        });
        const targetId = String(preferredNodeId || '');
        if (targetId && Array.from(nodeSelect.options).some((option) => option.value === targetId)) {
            nodeSelect.value = targetId;
        }
        nodeSelect.disabled = !nodeSelect.options.length || !activeRun;
    }

    function syncDeveloperValues(state) {
        const player = state?.player || {};
        const combat = state?.combat || null;
        const values = {
            'story-dev-health': player.health,
            'story-dev-elixir': combat ? combat.elixir : player.elixir,
            'story-dev-magic': combat ? combat.magic : player.magic,
            'story-dev-gold': player.gold,
        };
        Object.entries(values).forEach(([id, value]) => {
            const input = $(id);
            if (input) input.value = Number.isFinite(Number(value)) ? String(Math.max(0, Number(value))) : '0';
        });
    }

    function renderDeveloperPanel(state, options = {}) {
        const floorSelect = $('story-dev-floor');
        if (!floorSelect) return;
        const previousFloor = Number(floorSelect.value || 0);
        const floors = developerFloors(state);
        floorSelect.replaceChildren();
        floors.forEach((floor) => {
            const option = document.createElement('option');
            option.value = String(floor.floor);
            option.textContent = t.floor(floor.floor);
            floorSelect.append(option);
        });
        const currentFloor = Math.max(2, Number(state?.current_floor || 2));
        const desiredFloor = floors.some((floor) => Number(floor.floor) === previousFloor)
            ? previousFloor
            : currentFloor;
        if (floors.some((floor) => Number(floor.floor) === desiredFloor)) {
            floorSelect.value = String(desiredFloor);
        }
        floorSelect.disabled = !floors.length || !activeRun;
        const currentNodeId = Number(floorSelect.value) === Number(state?.current_floor)
            ? state?.current_node_id
            : '';
        renderDeveloperNodes(state, currentNodeId);
        ['story-dev-jump', 'story-dev-apply', 'story-reset-map'].forEach((id) => {
            const control = $(id);
            if (control) control.disabled = !activeRun;
        });
        if (options.syncValues) syncDeveloperValues(state);
    }

    function setDeveloperMode(open) {
        if (!window.__STORY_DEV_TOOLS__) return;
        developerModeOpen = !!open;
        $('story-dev-panel')?.classList.toggle('hidden', !developerModeOpen);
        $('story-dev-toggle')?.classList.toggle('is-active', developerModeOpen);
        $('story-dev-toggle')?.setAttribute('aria-expanded', developerModeOpen ? 'true' : 'false');
        if (developerModeOpen) renderDeveloperPanel(activeRun?.state || null, { syncValues: true });
    }

    function readDeveloperValue(id) {
        const input = $(id);
        const raw = String(input?.value ?? '').trim();
        const value = Number(raw);
        if (!raw || !Number.isInteger(value) || value < 0) return null;
        return value;
    }

    async function applyDeveloperValues() {
        if (!activeRun || actionInFlight) return;
        const payload = {
            health: readDeveloperValue('story-dev-health'),
            elixir: readDeveloperValue('story-dev-elixir'),
            magic: readDeveloperValue('story-dev-magic'),
            gold: readDeveloperValue('story-dev-gold'),
        };
        if (Object.values(payload).some((value) => value === null)) {
            showToast(t.requestFailed);
            return;
        }
        const button = $('story-dev-apply');
        if (button) button.disabled = true;
        const result = await storyAction('dev_set_values', payload);
        if (result) {
            syncDeveloperValues(result.run?.state || activeRun?.state);
            showToast(t.devValuesUpdated);
        }
        if (button) button.disabled = !activeRun;
    }

    async function jumpDeveloperNode() {
        if (!activeRun || actionInFlight) return;
        const nodeId = String($('story-dev-node')?.value || '');
        if (!nodeId) return;
        const button = $('story-dev-jump');
        if (button) button.disabled = true;
        const result = await storyAction('dev_jump_node', { node_id: nodeId });
        if (result) {
            renderDeveloperPanel(result.run?.state || activeRun?.state, { syncValues: true });
            showToast(t.devJumped);
        }
        if (button) button.disabled = !activeRun;
    }

    async function requestJson(url, options = {}) {
        const { timeoutMs = 10000, ...fetchOptions } = options;
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), Math.max(1000, Number(timeoutMs) || 10000));
        try {
            const response = await fetch(url, {
                credentials: 'same-origin',
                ...fetchOptions,
                headers: { 'Content-Type': 'application/json', ...(fetchOptions.headers || {}) },
                signal: controller.signal,
            });
            const payload = await response.json().catch(() => ({}));
            if (response.status === 401) {
                window.location.replace('/?story=login_required');
                throw new StoryApiError('AUTH_REQUIRED', 401, payload);
            }
            if (!response.ok || !payload.success) {
                throw new StoryApiError(payload.error || t.requestFailed, response.status, payload);
            }
            return payload;
        } catch (error) {
            if (error?.name === 'AbortError') throw new StoryApiError(t.requestFailed, 408, {});
            throw error;
        } finally {
            clearTimeout(timeout);
        }
    }

    async function requestStoryLoadJson(url) {
        const retryDelays = [350, 1000];
        for (let attempt = 0; ; attempt += 1) {
            try {
                return await requestJson(url, { timeoutMs: 25000 });
            } catch (error) {
                if (error?.message === 'AUTH_REQUIRED') throw error;
                const retryable = !Number.isFinite(Number(error?.status))
                    || [408, 429, 502, 503, 504].includes(Number(error.status));
                if (!retryable || attempt >= retryDelays.length) throw error;
                await storySleep(retryDelays[attempt]);
            }
        }
    }

    function storyStatusText(run = activeRun) {
        const state = run?.state;
        if (!state) return t.title;
        const parts = [t.title, t.floor(state.current_floor || 1)];
        if (state.phase === 'combat' && state.combat) {
            parts.push(state.combat.turn === 'player' ? t.playerTurn : t.enemyTurn);
        } else if (state.phase === 'easy_relic') {
            parts.push(t.easyRelicTitle);
        } else if (state.phase === 'blessing') {
            parts.push(t.rooms.blessing);
        } else if (state.phase === 'reward') {
            parts.push(state.reward?.source === 'blessing' ? t.rooms.blessing : t.rewards);
        } else if (state.phase === 'complete') {
            parts.push(t.journeyComplete);
        } else if (state.phase === 'game_over') {
            parts.push(t.journeyFailed);
        } else {
            const roomType = state.room?.type || currentNode(state)?.type;
            if (roomType) parts.push(t.rooms[roomType] || roomType);
        }
        return parts.filter(Boolean).join(' · ');
    }

    function updateStoryPresenceDisplay() {
        const value = storyOnlineCount == null ? '--' : String(storyOnlineCount);
        const label = t.onlinePlayers(value);
        setText('story-status-online', label);
    }

    function updateStoryStatusBar() {
        setText('story-status-text', storyStatusText());
    }

    function updateStorySurrenderControl(run = activeRun) {
        const button = $('story-surrender');
        if (!button) return;
        const phase = String(run?.state?.phase || '');
        const visible = Boolean(run)
            && phase
            && !['journey_setup', 'complete', 'game_over'].includes(phase);
        button.classList.toggle('hidden', !visible);
        button.disabled = !visible || actionInFlight;
        button.title = t.surrender;
        button.setAttribute('aria-label', t.surrender);
    }

    const STORY_CHAT_AUTO_SCROLL_THRESHOLD = 28;
    const STORY_CHAT_TITLE_COLORS = Object.freeze({
        admin: '#C0392B',
        thorn: 'var(--thorn)',
        bloom: 'var(--bloom)',
        root: 'var(--root)',
        guard: 'var(--guard)',
        curse: '#704B87',
        infect: '#7E9638',
        health: '#2ECC71',
        elixir: '#F1C40F',
        energy: '#F1C40F',
        magic: '#3498DB',
        damage: '#C0392B',
        electric: '#4BA3FF',
        poison: '#8E44AD',
        fire: '#E67E22',
        armor: '#95A5A6',
        precision: '#546E7A',
        banish: '#6C3483',
        indestructible: '#D4AC0D',
        critical: '#D4AC0D',
        primary: '#7EEF6D',
        common: '#FFE65D',
        rare: '#861FDE',
        ultra: '#FF2B75',
        super: '#2BFFA3',
        milestone: '#5AA469',
        hidden: '#7257A8',
        neutral: 'var(--story-muted)',
    });

    function storyChatColorCss(value) {
        const raw = String(value || '').trim();
        const key = raw.toLowerCase();
        if (STORY_CHAT_TITLE_COLORS[key]) return STORY_CHAT_TITLE_COLORS[key];
        if (/^#[0-9a-f]{6}$/i.test(raw)) return raw;
        if (
            globalThis.CSS?.supports?.('color', raw)
            && /^(?:rgb|hsl)a?\([^;{}]+\)$/i.test(raw)
        ) {
            return raw;
        }
        return '';
    }

    function storyChatEntryKey(entry = {}) {
        return String(
            entry.message_id
            || entry.messageId
            || entry.id
            || `${entry.time || ''}:${entry.nickname || ''}:${entry.text || ''}`,
        );
    }

    function storyChatRepeatKey(entry = {}) {
        if (!entry || entry.type !== 'chat') return '';
        return JSON.stringify([
            storyChatEntryKey(entry),
            entry.nickname || entry.sender_name || '',
            entry.text || '',
            entry.chat_channel || entry.channel || '',
            entry.chat_origin || entry.chatOrigin || '',
            Boolean(entry.system),
        ]);
    }

    function mergeStoryChatEntries(incoming, previous) {
        const previousByKey = new Map();
        (previous || []).forEach((entry) => {
            const key = storyChatRepeatKey(entry);
            if (key) previousByKey.set(key, entry);
        });
        return (incoming || []).map((entry) => {
            if (!entry || typeof entry !== 'object') return entry;
            const copy = { ...entry };
            const old = previousByKey.get(storyChatRepeatKey(copy));
            if (!old) return copy;
            const oldCount = Math.max(1, Number(old.repeat_count || old.repeatCount || 1));
            const newCount = Math.max(1, Number(copy.repeat_count || copy.repeatCount || 1));
            if (oldCount > newCount) {
                copy.repeat_count = oldCount;
                copy.time = old.time || copy.time;
                copy.ts = old.ts || copy.ts;
            }
            return copy;
        });
    }

    function countNewStoryChatMessages(nextEntries, previousEntries) {
        const previousCounts = new Map();
        (previousEntries || []).forEach((entry) => {
            if (!entry || entry.type !== 'chat') return;
            previousCounts.set(
                storyChatRepeatKey(entry),
                Math.max(1, Number(entry.repeat_count || entry.repeatCount || 1)),
            );
        });
        return (nextEntries || []).reduce((count, entry) => {
            if (!entry || entry.type !== 'chat') return count;
            const nextCount = Math.max(1, Number(entry.repeat_count || entry.repeatCount || 1));
            const previousCount = previousCounts.get(storyChatRepeatKey(entry));
            return count + (previousCount == null ? nextCount : Math.max(0, nextCount - previousCount));
        }, 0);
    }

    function storyChatLocale() {
        if (lang === 'zh') return 'zh-CN';
        if (lang === 'ja') return 'ja-JP';
        if (lang === 'fr') return 'fr-FR';
        return 'en-US';
    }

    function storyChatLocalDateKey(date) {
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    }

    function storyChatDayStart(date) {
        return new Date(date.getFullYear(), date.getMonth(), date.getDate());
    }

    function formatStoryChatDate(date) {
        if (lang === 'zh' || lang === 'ja') {
            return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
        }
        return date.toLocaleDateString(storyChatLocale(), {
            year: 'numeric',
            month: lang === 'fr' ? '2-digit' : 'short',
            day: 'numeric',
        });
    }

    function formatStoryChatTime(entry = {}) {
        const value = entry.time || entry.created_at || entry.createdAt;
        const date = value ? new Date(value) : null;
        if (!date || Number.isNaN(date.getTime())) {
            return String(entry.display_time || entry.displayTime || '');
        }
        const now = new Date();
        const time = date.toLocaleTimeString(storyChatLocale(), {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
        });
        if (storyChatLocalDateKey(date) === storyChatLocalDateKey(now)) return time;
        const daysAgo = Math.round(
            (storyChatDayStart(now).getTime() - storyChatDayStart(date).getTime()) / 86400000,
        );
        if (daysAgo === 1) return `${t.chatYesterday} ${time}`;
        if (daysAgo === 2) return `${t.chatBeforeYesterday} ${time}`;
        return `${formatStoryChatDate(date)} ${time}`;
    }

    function storyCurrentMentionKeys() {
        const account = window.__STORY_ACCOUNT__ || {};
        const keys = new Set();
        if (account.id != null) keys.add(`user:${account.id}`);
        if (account.username) keys.add(`name:${String(account.username).toLowerCase()}`);
        if (account.display_name) keys.add(`name:${String(account.display_name).toLowerCase()}`);
        if (account.player_id) keys.add(`pid:${String(account.player_id).toUpperCase()}`);
        return keys;
    }

    function storyCurrentUserMentionTokens(entry = {}) {
        const tokens = new Set();
        const keys = storyCurrentMentionKeys();
        (Array.isArray(entry.mentions) ? entry.mentions : []).forEach((item) => {
            if (!item) return;
            const matches = (
                (item.user_id != null && keys.has(`user:${item.user_id}`))
                || (item.nickname && keys.has(`name:${String(item.nickname).toLowerCase()}`))
                || (item.player_id && keys.has(`pid:${String(item.player_id).toUpperCase()}`))
            );
            if (!matches) return;
            if (item.nickname) tokens.add(String(item.nickname).toLowerCase());
            if (item.player_id) tokens.add(String(item.player_id).toUpperCase());
        });
        return tokens;
    }

    function appendStoryChatTextWithMentions(
        parent,
        text,
        mentions = [],
        ownMentionTokens = new Set(),
        shouldFlashOwnMention = false,
    ) {
        const raw = String(text || '');
        const mentionNames = [];
        (Array.isArray(mentions) ? mentions : []).forEach((item) => {
            if (!item) return;
            if (item.nickname) mentionNames.push(String(item.nickname));
            if (item.player_id) mentionNames.push(String(item.player_id));
        });
        const unique = [...new Set(mentionNames.filter(Boolean))].sort((left, right) => right.length - left.length);
        if (!unique.length) {
            parent.appendChild(document.createTextNode(raw));
            return;
        }
        const escaped = unique.map((name) => name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
        const pattern = new RegExp(`(@(?:${escaped.join('|')}))(?![\\w\\u4e00-\\u9fff\\u3040-\\u30ff\\uac00-\\ud7af-])`, 'gi');
        let last = 0;
        raw.replace(pattern, (match, token, offset) => {
            if (offset > last) parent.appendChild(document.createTextNode(raw.slice(last, offset)));
            const span = document.createElement('span');
            span.className = 'chat-mention-token';
            const tokenName = String(match || '').replace(/^@/, '');
            const mentionsCurrentUser = ownMentionTokens.has(tokenName.toLowerCase())
                || ownMentionTokens.has(tokenName.toUpperCase());
            if (mentionsCurrentUser) span.classList.add('mention-self');
            if (shouldFlashOwnMention && mentionsCurrentUser) span.classList.add('mention-flash');
            span.textContent = match;
            parent.appendChild(span);
            last = offset + match.length;
            return match;
        });
        if (last < raw.length) parent.appendChild(document.createTextNode(raw.slice(last)));
    }

    function appendStoryChatIdentity(parent, entry = {}) {
        const originKey = String(entry.chat_origin || entry.chatOrigin || '').toLowerCase();
        if (originKey === 'multiplayer' || originKey === 'story') {
            const origin = document.createElement('span');
            origin.className = `story-chat-origin story-chat-origin-${originKey} chat-origin-prefix chat-origin-${originKey}`;
            origin.textContent = `[${originKey === 'story'
                ? t.chatOriginStory
                : t.chatOriginMultiplayer}]`;
            parent.appendChild(origin);
        }

        if (entry.system) {
            const systemName = document.createElement('span');
            systemName.className = 'story-chat-system-name';
            systemName.textContent = String(
                entry.nickname || entry.sender_name || (lang === 'zh' ? '系统' : 'System'),
            );
            parent.appendChild(systemName);
            return;
        }

        if (entry.is_spectator) {
            const spectator = document.createElement('span');
            spectator.className = 'chat-spectator-prefix';
            spectator.textContent = `[${t.chatSpectator}]`;
            parent.appendChild(spectator);
        }

        const titles = Array.isArray(entry.equipped_titles)
            ? entry.equipped_titles.filter((item) => item?.name).slice(0, 3)
            : [];
        titles.forEach((title) => {
            const titleElement = document.createElement('span');
            titleElement.className = 'story-chat-player-title';
            titleElement.textContent = `[${String(title.name)}]`;
            const color = storyChatColorCss(title.color);
            if (color) titleElement.style.color = color;
            parent.appendChild(titleElement);
        });
        if (!titles.length && (entry.console_player || entry.special_role === 'console')) {
            const titleElement = document.createElement('span');
            titleElement.className = 'story-chat-player-title player-title-inline';
            titleElement.textContent = `[${t.chatConsole}]`;
            const color = storyChatColorCss(entry.special_role_color || 'admin');
            if (color) titleElement.style.color = color;
            parent.appendChild(titleElement);
        }

        const name = document.createElement('span');
        name.className = 'story-chat-player-name chat-player-name player-name-value';
        name.textContent = String(
            entry.nickname
            || entry.sender_name
            || entry.display_name
            || entry.username
            || '?',
        );
        const nameColor = storyChatColorCss(
            entry.name_color
            || titles[0]?.color
            || entry.special_role_color,
        );
        if (nameColor) name.style.color = nameColor;
        parent.appendChild(name);
    }

    function isStoryChatNearBottom(container) {
        if (!container) return true;
        return container.scrollHeight - container.scrollTop - container.clientHeight
            <= STORY_CHAT_AUTO_SCROLL_THRESHOLD;
    }

    function appendStoryChatEntry(container, entry = {}) {
        if (!container) return;
        if (entry.type === 'time') {
            const separator = document.createElement('div');
            separator.className = 'story-chat-time chat-time-separator';
            separator.textContent = formatStoryChatTime(entry);
            container.appendChild(separator);
            return;
        }
        if (entry.type !== 'chat') return;

        const row = document.createElement('div');
        row.className = `story-chat-message chat-msg${entry.system ? ' is-system' : ''}`;
        const identity = document.createElement('span');
        identity.className = `story-chat-identity chat-nick${entry.system ? ' system-name' : ''}`;
        appendStoryChatIdentity(identity, entry);
        identity.appendChild(document.createTextNode(entry.system ? ' ' : ': '));
        row.appendChild(identity);

        const message = document.createElement('span');
        message.className = 'story-chat-message-text';
        const mentionKey = storyChatEntryKey(entry);
        const ownMentionTokens = storyCurrentUserMentionTokens(entry);
        const shouldFlashOwnMention = ownMentionTokens.size > 0 && !readStoryMentionIds.has(mentionKey);
        if (shouldFlashOwnMention) row.dataset.mentionId = mentionKey;
        appendStoryChatTextWithMentions(
            message,
            entry.text || '',
            entry.mentions || [],
            ownMentionTokens,
            shouldFlashOwnMention,
        );
        row.appendChild(message);

        const repeatCount = Math.max(1, Number(entry.repeat_count || entry.repeatCount || 1));
        if (repeatCount > 1) {
            const repeat = document.createElement('span');
            repeat.className = 'story-chat-repeat chat-repeat-count';
            repeat.textContent = ` ×${repeatCount}`;
            row.appendChild(repeat);
        }
        container.appendChild(row);
    }

    function clearStoryMentionFlash() {
        document.querySelectorAll('#story-chat-log [data-mention-id]').forEach((element) => {
            if (element.dataset.mentionId) readStoryMentionIds.add(element.dataset.mentionId);
            element.removeAttribute('data-mention-id');
        });
        document.querySelectorAll('#story-chat-log .mention-flash').forEach((element) => {
            element.classList.remove('mention-flash');
        });
    }

    function ensureStoryMentionMenu() {
        if (storyMentionMenu) return storyMentionMenu;
        storyMentionMenu = document.createElement('div');
        storyMentionMenu.id = 'story-mention-menu';
        storyMentionMenu.className = 'mention-menu hidden';
        document.body.appendChild(storyMentionMenu);
        storyMentionMenu.addEventListener('mousedown', (event) => {
            const item = event.target.closest('[data-mention-index]');
            if (!item) return;
            event.preventDefault();
            const candidate = storyMentionCandidates[Number(item.dataset.mentionIndex)];
            if (candidate) insertStoryMention(candidate);
        });
        return storyMentionMenu;
    }

    function getStoryMentionCandidates() {
        const selfKeys = storyCurrentMentionKeys();
        const seen = new Set();
        return storyMentionDirectory
            .map((item) => ({
                nickname: String(item?.nickname || ''),
                player_id: String(item?.player_id || ''),
                user_id: item?.user_id ?? '',
            }))
            .filter((item) => {
                const nameKey = `name:${item.nickname.toLowerCase()}`;
                const userKey = item.user_id !== '' ? `user:${item.user_id}` : '';
                const identity = userKey || nameKey;
                if (!item.nickname || selfKeys.has(nameKey) || (userKey && selfKeys.has(userKey)) || seen.has(identity)) {
                    return false;
                }
                seen.add(identity);
                return true;
            });
    }

    function findStoryMentionRange(input) {
        if (!input) return null;
        const value = input.value || '';
        const position = input.selectionStart ?? value.length;
        const before = value.slice(0, position);
        const match = before.match(/(^|\s)@([^\s@]*)$/);
        if (!match) return null;
        const start = before.length - match[0].length + match[1].length;
        return { start, end: position, query: match[2] || '' };
    }

    function updateStoryMentionMenu() {
        const input = $('story-chat-input');
        const menu = ensureStoryMentionMenu();
        const range = findStoryMentionRange(input);
        storyMentionActiveRange = range;
        if (!storyChatOpen || !input || !range) {
            menu.classList.add('hidden');
            return;
        }
        const query = String(range.query || '').toLowerCase();
        storyMentionCandidates = getStoryMentionCandidates()
            .filter((item) => (
                !query
                || item.nickname.toLowerCase().includes(query)
                || item.player_id.toLowerCase().includes(query)
            ))
            .slice(0, 8);
        if (!storyMentionCandidates.length) {
            menu.classList.add('hidden');
            return;
        }
        menu.replaceChildren(...storyMentionCandidates.map((candidate, index) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'mention-menu-item';
            button.dataset.mentionIndex = String(index);
            const name = document.createElement('span');
            name.textContent = `@${candidate.nickname}`;
            button.appendChild(name);
            if (candidate.player_id) {
                const playerId = document.createElement('small');
                playerId.textContent = candidate.player_id;
                button.appendChild(playerId);
            }
            return button;
        }));
        const rect = input.getBoundingClientRect();
        menu.style.left = `${Math.max(8, rect.left)}px`;
        menu.style.top = `${Math.max(8, rect.top - Math.min(220, menu.offsetHeight || 180) - 6)}px`;
        menu.style.width = `${Math.min(260, Math.max(180, rect.width))}px`;
        menu.classList.remove('hidden');
    }

    function insertStoryMention(candidate) {
        const input = $('story-chat-input');
        if (!input || !storyMentionActiveRange) return;
        const value = input.value || '';
        const token = `@${candidate.nickname} `;
        input.value = value.slice(0, storyMentionActiveRange.start)
            + token
            + value.slice(storyMentionActiveRange.end);
        const position = storyMentionActiveRange.start + token.length;
        input.focus();
        input.setSelectionRange(position, position);
        storyMentionMenu?.classList.add('hidden');
        updateStoryChatConnectionUi();
    }

    function updateStoryChatConnectionUi() {
        const status = $('story-chat-status');
        if (status) {
            if (storyChatConnected) {
                status.textContent = t.chatConnected;
            } else if (storyChatInitialized) {
                status.textContent = t.chatDisconnected;
            } else {
                status.textContent = t.chatConnecting;
            }
        }
        const input = $('story-chat-input');
        const send = $('story-chat-send');
        if (send) {
            send.disabled = !storyChatConnected || !String(input?.value || '').trim();
        }
    }

    function updateStoryChatUnreadBadge() {
        const badge = $('story-chat-unread');
        if (!badge) return;
        const count = Math.max(0, Number(storyChatUnreadCount) || 0);
        badge.textContent = count > 99 ? '99+' : String(count);
        badge.classList.toggle('hidden', count <= 0);
        badge.setAttribute('aria-label', t.chatUnread(count));
    }

    function setStoryChatOpen(open) {
        storyChatOpen = Boolean(open);
        const panel = $('story-chat-panel');
        const toggle = $('story-chat-toggle');
        if (!storyChatOpen && panel?.contains(document.activeElement)) {
            document.activeElement?.blur?.();
        }
        panel?.classList.toggle('hidden', !storyChatOpen);
        toggle?.classList.toggle('hidden', storyChatOpen);
        toggle?.setAttribute('aria-expanded', storyChatOpen ? 'true' : 'false');
        if (storyChatOpen) {
            storyChatUnreadCount = 0;
            clearStoryMentionFlash();
            updateStoryChatUnreadBadge();
            requestAnimationFrame(() => {
                const log = $('story-chat-log');
                if (log) log.scrollTop = log.scrollHeight;
                $('story-chat-input')?.focus();
            });
        } else {
            storyMentionMenu?.classList.add('hidden');
        }
    }

    function renderStoryChatHistory(data = {}) {
        const log = $('story-chat-log');
        if (!log) return;
        storyMentionDirectory = Array.isArray(data.mention_candidates)
            ? data.mention_candidates.map((item) => ({ ...item }))
            : [];
        const incoming = Array.isArray(data.items) ? data.items : [];
        const entries = mergeStoryChatEntries(incoming, storyChatEntries);
        if (storyChatInitialized && !storyChatOpen) {
            storyChatUnreadCount += countNewStoryChatMessages(entries, storyChatEntries);
            updateStoryChatUnreadBadge();
        }
        const signature = JSON.stringify([lang, entries.map((entry) => [
            entry?.type,
            entry?.id,
            entry?.message_id,
            entry?.time,
            entry?.nickname,
            entry?.text,
            entry?.repeat_count,
            entry?.chat_origin,
            entry?.system,
            entry?.is_spectator,
            entry?.name_color,
            entry?.equipped_titles,
            entry?.special_role,
            entry?.special_role_color,
            entry?.console_player,
            entry && JSON.stringify(entry.mentions || []),
        ])]);
        storyChatInitialized = true;
        storyChatConnected = true;
        updateStoryChatConnectionUi();
        if (signature === storyChatHistorySignature) return;
        storyChatHistorySignature = signature;
        const stayAtBottom = isStoryChatNearBottom(log);
        const previousScrollTop = log.scrollTop;
        storyChatEntries = entries;
        log.replaceChildren();
        entries.forEach((entry) => appendStoryChatEntry(log, entry));
        if (storyChatOpen && stayAtBottom) {
            log.scrollTop = log.scrollHeight;
        } else {
            const maximum = Math.max(0, log.scrollHeight - log.clientHeight);
            log.scrollTop = Math.min(previousScrollTop, maximum);
        }
    }

    function startStoryChat() {
        if (typeof globalThis.io !== 'function') {
            storyChatInitialized = true;
            storyChatConnected = false;
            updateStoryChatConnectionUi();
            return;
        }
        storyChatSocket = globalThis.io({
            transports: ['websocket', 'polling'],
            timeout: 12000,
            reconnection: true,
            reconnectionAttempts: Infinity,
            reconnectionDelay: 500,
            reconnectionDelayMax: 5000,
            withCredentials: true,
        });
        storyChatSocket.on('connect', () => {
            storyChatConnected = false;
            updateStoryChatConnectionUi();
            storyChatSocket.emit('story_chat_join', {
                client_id: STORY_PRESENCE_CLIENT_ID,
            });
        });
        storyChatSocket.on('story_chat_ready', () => {
            storyChatConnected = true;
            storyChatInitialized = true;
            updateStoryChatConnectionUi();
        });
        storyChatSocket.on('lobby_chat_history', renderStoryChatHistory);
        storyChatSocket.on('server_error', (data = {}) => {
            showToast(data.message || t.requestFailed);
        });
        storyChatSocket.on('story_chat_auth_required', () => {
            storyChatConnected = false;
            updateStoryChatConnectionUi();
            window.location.replace('/?story=login_required');
        });
        storyChatSocket.on('disconnect', () => {
            storyChatConnected = false;
            storyChatInitialized = true;
            updateStoryChatConnectionUi();
        });
        storyChatSocket.on('connect_error', () => {
            storyChatConnected = false;
            storyChatInitialized = true;
            updateStoryChatConnectionUi();
        });
        window.addEventListener('pagehide', () => {
            storyChatSocket?.disconnect();
        }, { once: true });
    }

    function sendStoryChat() {
        const input = $('story-chat-input');
        const text = String(input?.value || '').trim();
        if (!text || !storyChatConnected || !storyChatSocket) return;
        storyChatSocket.emit('story_chat_send', {
            text: text.slice(0, 200),
            client_id: STORY_PRESENCE_CLIENT_ID,
        });
        input.value = '';
        storyMentionMenu?.classList.add('hidden');
        updateStoryChatConnectionUi();
    }

    function scheduleStoryPresence(delayMs = storyPresenceIntervalMs) {
        clearTimeout(storyPresenceTimer);
        if (storyAfkRedirectTimer) return;
        const delay = Math.max(250, Number(delayMs) || storyPresenceIntervalMs);
        storyPresenceTimer = window.setTimeout(() => {
            void sendStoryPresence();
        }, delay);
    }

    function closeStoryAfkCheckOverlay() {
        if (storyAfkCheckTimer) {
            clearInterval(storyAfkCheckTimer);
            storyAfkCheckTimer = 0;
        }
        if (storyAfkHoldFrame) {
            cancelAnimationFrame(storyAfkHoldFrame);
            storyAfkHoldFrame = 0;
        }
        if (storyAfkRedirectTimer) {
            clearTimeout(storyAfkRedirectTimer);
            storyAfkRedirectTimer = 0;
        }
        $('story-afk-check-overlay')?.remove();
        activeStoryAfkCheck = null;
    }

    function setStoryAfkCheckStatus(message, tone = '') {
        const element = $('story-afk-check-status');
        if (!element) return;
        element.textContent = message || '';
        element.classList.toggle('afk-check-error', tone === 'error');
        element.classList.toggle('afk-check-ok', tone === 'ok');
    }

    function storyAfkResultText(result) {
        if (result === 'passed') return t.afkPassed;
        if (result === 'too_short') return t.afkTooShort;
        if (result === 'too_long') return t.afkTooLong;
        if (result === 'timed_out') return t.afkTimedOut;
        return t.afkFailed;
    }

    function ensureStoryAfkTimeoutOverlay() {
        if ($('story-afk-check-overlay')) return;
        const overlay = document.createElement('div');
        overlay.id = 'story-afk-check-overlay';
        overlay.className = 'afk-check-overlay';
        overlay.innerHTML = `
            <div class="afk-check-dialog" role="alertdialog" aria-modal="true">
                <div class="afk-check-title"></div>
                <div class="afk-check-desc"></div>
                <div id="story-afk-check-status" class="afk-check-status afk-check-error"></div>
            </div>
        `;
        overlay.querySelector('.afk-check-title').textContent = t.afkTitle;
        overlay.querySelector('.afk-check-desc').textContent = t.afkTimedOut;
        document.body.appendChild(overlay);
    }

    function expireStoryAfkCheck() {
        if (storyAfkCheckTimer) {
            clearInterval(storyAfkCheckTimer);
            storyAfkCheckTimer = 0;
        }
        if (storyAfkHoldFrame) {
            cancelAnimationFrame(storyAfkHoldFrame);
            storyAfkHoldFrame = 0;
        }
        if (activeStoryAfkCheck) {
            activeStoryAfkCheck.holding = false;
            activeStoryAfkCheck.sent = true;
        }
        ensureStoryAfkTimeoutOverlay();
        $('story-afk-check-button')?.setAttribute('disabled', 'disabled');
        setStoryAfkCheckStatus(t.afkTimedOut, 'error');
        if (!storyAfkRedirectTimer) {
            storyAfkRedirectTimer = window.setTimeout(() => {
                window.location.replace('/');
            }, 900);
        }
    }

    async function submitStoryAfkCheck(holdMs) {
        const check = activeStoryAfkCheck;
        if (!check?.id) return;
        try {
            const payload = await requestJson('/api/story/afk-check', {
                method: 'POST',
                body: JSON.stringify({
                    client_id: STORY_PRESENCE_CLIENT_ID,
                    id: check.id,
                    hold_ms: Math.max(0, Math.round(Number(holdMs) || 0)),
                }),
            });
            if (activeStoryAfkCheck?.id !== check.id) return;
            const result = String(payload.result || '');
            if (result === 'passed') {
                setStoryAfkCheckStatus(storyAfkResultText(result), 'ok');
                window.setTimeout(closeStoryAfkCheckOverlay, 650);
                return;
            }
            if (payload.timed_out || result === 'timed_out' || payload.retry === false) {
                expireStoryAfkCheck();
                return;
            }
            activeStoryAfkCheck.sent = false;
            setStoryAfkCheckStatus(storyAfkResultText(result), 'error');
        } catch (error) {
            if (error.message === 'AUTH_REQUIRED') return;
            if (!activeStoryAfkCheck || Date.now() >= check.expiresAt) {
                expireStoryAfkCheck();
                return;
            }
            activeStoryAfkCheck.sent = false;
            setStoryAfkCheckStatus(t.afkFailed, 'error');
        }
    }

    function updateStoryAfkCheckCountdown() {
        if (!activeStoryAfkCheck) return;
        const left = Math.max(0, Math.ceil((activeStoryAfkCheck.expiresAt - Date.now()) / 1000));
        const description = $('story-afk-check-desc');
        if (description) description.textContent = t.afkPrompt(`${left}s`);
        if (left > 0) return;
        const check = activeStoryAfkCheck;
        if (!check.sent) {
            check.sent = true;
            void submitStoryAfkCheck(0);
        }
        expireStoryAfkCheck();
    }

    function showStoryAfkCheckOverlay(data = {}) {
        const requestId = String(data.id || '');
        if (!requestId) return;
        if (activeStoryAfkCheck?.id === requestId && $('story-afk-check-overlay')) return;
        closeStoryAfkCheckOverlay();
        const timeoutSeconds = Math.max(1, Number(data.timeout_seconds || 60));
        const minMs = Math.max(100, Number(data.min_ms || 750));
        const maxMs = Math.max(minMs + 100, Number(data.max_ms || 2200));
        const serverExpiry = Number(data.expires_at || 0) * 1000;
        const expiresAt = serverExpiry > 0 ? serverExpiry : Date.now() + timeoutSeconds * 1000;
        activeStoryAfkCheck = {
            id: requestId,
            minMs,
            maxMs,
            expiresAt,
            holding: false,
            holdStart: 0,
            sent: false,
        };

        const overlay = document.createElement('div');
        overlay.id = 'story-afk-check-overlay';
        overlay.className = 'afk-check-overlay';
        overlay.innerHTML = `
            <div class="afk-check-dialog" role="dialog" aria-modal="true">
                <div class="afk-check-title"></div>
                <div id="story-afk-check-desc" class="afk-check-desc"></div>
                <button id="story-afk-check-button" class="afk-check-button" type="button">
                    <span class="afk-check-core"></span>
                </button>
                <div id="story-afk-check-status" class="afk-check-status"></div>
            </div>
        `;
        overlay.querySelector('.afk-check-title').textContent = t.afkTitle;
        overlay.querySelector('.afk-check-core').textContent = t.afkHold;
        const button = overlay.querySelector('.afk-check-button');
        button.setAttribute('aria-label', t.afkHold);
        document.body.appendChild(overlay);
        setStoryAfkCheckStatus(t.afkReady);

        const updateHold = () => {
            const check = activeStoryAfkCheck;
            if (!check?.holding || !button) return;
            const elapsed = Date.now() - check.holdStart;
            button.classList.toggle('afk-check-ready', elapsed >= check.minMs && elapsed <= check.maxMs);
            storyAfkHoldFrame = requestAnimationFrame(updateHold);
        };
        const startHold = (event) => {
            event.preventDefault();
            const check = activeStoryAfkCheck;
            if (!check || check.sent || check.holding) return;
            check.holding = true;
            check.holdStart = Date.now();
            button.classList.add('afk-check-holding');
            setStoryAfkCheckStatus(t.afkHolding);
            updateHold();
        };
        const endHold = (event) => {
            event?.preventDefault();
            const check = activeStoryAfkCheck;
            if (!check?.holding || check.sent) return;
            check.holding = false;
            if (storyAfkHoldFrame) {
                cancelAnimationFrame(storyAfkHoldFrame);
                storyAfkHoldFrame = 0;
            }
            button.classList.remove('afk-check-holding', 'afk-check-ready');
            check.sent = true;
            setStoryAfkCheckStatus(t.afkVerifying);
            void submitStoryAfkCheck(Date.now() - check.holdStart);
        };
        button.addEventListener('pointerdown', startHold);
        ['pointerup', 'pointercancel', 'pointerleave'].forEach((name) => {
            button.addEventListener(name, endHold);
        });
        button.addEventListener('contextmenu', (event) => event.preventDefault());
        updateStoryAfkCheckCountdown();
        storyAfkCheckTimer = window.setInterval(updateStoryAfkCheckCountdown, 250);
    }

    function reportStoryAfkActivity(event) {
        if (document.hidden || activeStoryAfkCheck) return;
        if (event?.type === 'keydown' && event.repeat) return;
        if (event?.target?.closest?.('#story-afk-check-overlay')) return;
        const now = Date.now();
        if (now - lastStoryAfkActivityReportAt < STORY_AFK_ACTIVITY_REPORT_INTERVAL_MS) return;
        lastStoryAfkActivityReportAt = now;
        storyPresenceActivityPending = true;
        void sendStoryPresence({ activity: true });
    }

    function bindStoryAfkActivityReporting() {
        document.addEventListener('pointerdown', reportStoryAfkActivity, {
            passive: true,
            capture: true,
        });
        document.addEventListener('touchstart', reportStoryAfkActivity, {
            passive: true,
            capture: true,
        });
        document.addEventListener('wheel', reportStoryAfkActivity, {
            passive: true,
            capture: true,
        });
        document.addEventListener('keydown', reportStoryAfkActivity, {
            capture: true,
        });
    }

    async function sendStoryPresence(options = {}) {
        const reportActivity = Boolean(options.activity || storyPresenceActivityPending);
        if (storyPresenceInFlight) {
            if (reportActivity) storyPresenceActivityPending = true;
            return;
        }
        clearTimeout(storyPresenceTimer);
        storyPresenceInFlight = true;
        if (reportActivity) storyPresenceActivityPending = false;
        let nextDelay = storyPresenceIntervalMs;
        try {
            const payload = await requestJson('/api/story/presence', {
                method: 'POST',
                body: JSON.stringify({
                    client_id: STORY_PRESENCE_CLIENT_ID,
                    activity: reportActivity,
                }),
            });
            storyOnlineCount = Math.max(0, Number(payload.story_online_count) || 0);
            const requestedInterval = Number(payload.heartbeat_interval_seconds) * 1000;
            if (Number.isFinite(requestedInterval) && requestedInterval >= 10000) {
                storyPresenceIntervalMs = requestedInterval;
                nextDelay = requestedInterval;
            }
            const nextCheckSeconds = Number(payload.afk_next_check_seconds);
            if (!payload.afk_check && Number.isFinite(nextCheckSeconds) && nextCheckSeconds >= 0) {
                nextDelay = Math.min(nextDelay, Math.max(250, nextCheckSeconds * 1000 + 50));
            }
            updateStoryPresenceDisplay();
            if (payload.afk_timed_out) {
                expireStoryAfkCheck();
            } else if (payload.afk_check) {
                showStoryAfkCheckOverlay(payload.afk_check);
            }
        } catch (error) {
            if (error.message === 'AUTH_REQUIRED') return;
            if (reportActivity) storyPresenceActivityPending = true;
            nextDelay = Math.min(nextDelay, 5000);
        } finally {
            storyPresenceInFlight = false;
            if (storyPresenceActivityPending && !activeStoryAfkCheck && !storyAfkRedirectTimer) {
                scheduleStoryPresence(250);
            } else {
                scheduleStoryPresence(nextDelay);
            }
        }
    }

    function startStoryPresence() {
        clearTimeout(storyPresenceTimer);
        void sendStoryPresence();
    }

    function showView(name) {
        if (name !== 'story-combat') removeStoryEquipmentPreview();
        removeStoryCardHoverPreview();
        VIEWS.forEach((id) => $(id)?.classList.toggle('hidden', id !== name));
        const runDeck = $('story-run-deck');
        const runDeckUnavailable = !activeRun?.state;
        runDeck?.classList.toggle('hidden', runDeckUnavailable);
        $('story-talent-overview')?.classList.toggle('hidden', runDeckUnavailable);
        if (storyKeyboardFocus && !storyElementVisible(storyKeyboardFocus)) clearStoryKeyboardFocus();
        window.GTN_KEYBINDINGS?.refreshHints?.();
    }

    function storyRunScrollContext(run = activeRun) {
        const state = run?.state || {};
        const room = state.room || {};
        const reward = state.reward || {};
        const combat = state.combat || {};
        const phaseDetail = state.phase === 'combat'
            ? `${combat.round || 0}:${combat.turn || ''}`
            : (state.phase === 'reward'
                ? `${reward.source || ''}:${reward.round_index || 0}`
                : `${room.type || ''}:${room.event_id || ''}`);
        return [
            String(run?.id || ''),
            String(state.phase || ''),
            String(state.stage || ''),
            String(state.current_node_id || ''),
            phaseDetail,
        ].join(':');
    }

    function storyScrollElementKey(element) {
        if (!(element instanceof HTMLElement)) return '';
        const identity = String(element.dataset.storyScrollKey || element.id || '').trim();
        if (!identity) return '';
        if (identity.startsWith('codex-')) return identity;
        if (identity === 'story-codex-tabs') return identity;
        if (identity.startsWith('story-codex')) {
            const subtype = storyCodexMode === 'talents'
                ? storyCodexTalentKind
                : (storyCodexMode === 'terms' ? storyCodexTermKind : '');
            const selected = identity === 'story-codex-detail' ? storyCodexSelectedId : '';
            return `codex:${storyCodexMode}:${subtype}:${selected}:${identity}`;
        }
        if (identity === 'story-room-options' || identity === 'story-room-tabs') {
            return `${storyRunScrollContext()}:room-tab:${activeStoryRoomTabId}:${identity}`;
        }
        if (identity === 'story-pile-grid') {
            return `${storyRunScrollContext()}:pile:${$('story-pile-dialog')?.dataset.pileKind || ''}`;
        }
        if (identity === 'story-card-choice-grid') {
            const choiceId = cardChoiceContext?.operationId
                || cardChoiceContext?.cardId
                || cardChoiceContext?.mode
                || '';
            return `${storyRunScrollContext()}:choice:${choiceId}:${identity}`;
        }
        return `${storyRunScrollContext()}:${identity}`;
    }

    function captureStoryScrollPositions() {
        const seen = new Set();
        const positions = [];
        document.querySelectorAll(STORY_PRESERVED_SCROLL_SELECTORS.join(',')).forEach((element) => {
            if (seen.has(element)) return;
            seen.add(element);
            const key = storyScrollElementKey(element);
            if (!key) return;
            positions.push({
                key,
                top: Number(element.scrollTop) || 0,
                left: Number(element.scrollLeft) || 0,
            });
        });
        return positions;
    }

    function restoreStoryScrollPositions(positions) {
        if (!Array.isArray(positions) || !positions.length) return;
        const saved = new Map(positions.map((position) => [position.key, position]));
        const restore = () => {
            const seen = new Set();
            document.querySelectorAll(STORY_PRESERVED_SCROLL_SELECTORS.join(',')).forEach((element) => {
                if (seen.has(element)) return;
                seen.add(element);
                const position = saved.get(storyScrollElementKey(element));
                if (!position) return;
                element.scrollTop = position.top;
                element.scrollLeft = position.left;
            });
        };
        restore();
        requestAnimationFrame(restore);
    }

    function stateValue(value) {
        return value === null || value === undefined ? '--' : String(value);
    }

    function createActionId() {
        if (globalThis.crypto?.randomUUID) return crypto.randomUUID();
        return `story-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }

    function waitForStoryAnimation(element, className, duration) {
        if (!element) return Promise.resolve();
        element.classList.remove(className);
        void element.offsetWidth;
        element.classList.add(className);
        return new Promise((resolve) => {
            let finished = false;
            let fallbackTimer = 0;
            const complete = () => {
                if (finished) return;
                finished = true;
                window.clearTimeout(fallbackTimer);
                element.removeEventListener('animationend', complete);
                element.classList.remove(className);
                resolve();
            };
            element.addEventListener('animationend', complete, { once: true });
            fallbackTimer = window.setTimeout(complete, duration + 80);
        });
    }

    function storySleep(duration) {
        return new Promise((resolve) => window.setTimeout(resolve, duration));
    }

    function storyNextPaint() {
        return new Promise((resolve) => {
            window.requestAnimationFrame(() => window.requestAnimationFrame(resolve));
        });
    }

    function createStoryCombatEntranceRun(run, events) {
        const sequence = Array.isArray(events) ? events : [];
        if (!sequence.some(
            (event) => event?.type === 'enemy_damage'
                && String(event?.source || '') === 'opening_lightning',
        )) return null;
        const stagedRun = typeof structuredClone === 'function'
            ? structuredClone(run)
            : JSON.parse(JSON.stringify(run));
        const enemies = stagedRun?.state?.combat?.enemies || [];
        [...sequence].reverse().forEach((event) => {
            if (event?.type !== 'enemy_damage') return;
            const enemy = enemies.find((item) => String(item.id) === String(event.enemy_id));
            if (!enemy) return;
            const before = Number(event.before);
            if (Number.isFinite(before)) enemy.health = before;
            const blocked = (Array.isArray(event.history) ? event.history : [])
                .reduce((total, hit) => total + Math.max(0, Number(hit?.blocked) || 0), 0);
            if (blocked > 0) enemy.shield = Math.max(0, Number(enemy.shield) || 0) + blocked;
        });
        return stagedRun;
    }

    function storyEnemyActor(enemyId) {
        if (!enemyId) return null;
        return document.querySelector(
            `.story-actor-enemy[data-target-id="${CSS.escape(String(enemyId))}"]`,
        );
    }

    function storyEnemyFromRun(run, enemyId) {
        return run?.state?.combat?.enemies?.find(
            (item) => String(item.id) === String(enemyId),
        ) || null;
    }

    function syncStoryEnemyGroupLayout() {
        const group = $('story-enemy-group');
        if (!group) return;
        const actors = [...group.querySelectorAll('.story-actor-enemy')]
            .filter((actor) => !actor.classList.contains('is-defeated-complete'));
        const count = Math.max(1, actors.length);
        group.classList.toggle('has-multiple-enemies', count > 1);
        group.style.setProperty('--story-enemy-count', String(count));
        group.style.setProperty(
            '--story-enemy-scale',
            String(Math.max(.48, Math.min(.82, 1.03 - count * .13))),
        );
    }

    function ensureStorySummonedActor(event, nextRun) {
        const enemyId = String(event?.enemy_id || '');
        if (!enemyId) return null;
        const existing = storyEnemyActor(enemyId);
        if (existing) return existing;
        const nextEnemy = storyEnemyFromRun(nextRun, enemyId);
        const eventEnemy = event?.enemy && typeof event.enemy === 'object'
            ? event.enemy
            : null;
        if (!nextEnemy && !eventEnemy) return null;
        const enemy = {
            ...(nextEnemy || {}),
            ...(eventEnemy || {}),
            intent: eventEnemy?.intent || nextEnemy?.intent,
        };
        const actor = createEnemyActor(enemy, '');
        actor.classList.add('is-presentation-spawn');
        $('story-enemy-group')?.append(actor);
        syncStoryEnemyGroupLayout();
        return actor;
    }

    function spawnStoryFloat(target, message, kind = '') {
        const layer = $('story-float-layer');
        if (!layer || !target || !message) return;
        const rect = target.getBoundingClientRect();
        const item = document.createElement('span');
        item.className = `story-combat-float${kind ? ` story-combat-float-${kind}` : ''}`;
        item.textContent = String(message);
        item.style.left = `${rect.left + rect.width / 2}px`;
        item.style.top = `${rect.top + Math.max(18, rect.height * .28)}px`;
        layer.append(item);
        item.addEventListener('animationend', () => item.remove(), { once: true });
        window.setTimeout(() => item.remove(), 1100);
    }

    function storyEventAmount(value) {
        const amount = Math.floor(Number(value) || 0);
        return amount > 0 ? `+${amount}` : String(amount);
    }

    async function animateEnemyLunge(enemyId) {
        const actor = storyEnemyActor(enemyId) || $('story-enemy-group');
        await waitForStoryAnimation(actor, 'is-lunging', 420);
    }

    async function animateEnemyGain(enemyId) {
        const group = storyEnemyActor(enemyId) || $('story-enemy-group');
        if (!group) return;
        const direction = Math.random() < .5 ? -1 : 1;
        const x = direction * (3 + Math.random() * 4);
        const y = (Math.random() - .5) * 5;
        const rotate = direction * (1.2 + Math.random() * 1.8);
        group.style.setProperty('--story-shake-x', `${x.toFixed(2)}px`);
        group.style.setProperty('--story-shake-y', `${y.toFixed(2)}px`);
        group.style.setProperty('--story-shake-x-reverse', `${(-x * .72).toFixed(2)}px`);
        group.style.setProperty('--story-shake-y-reverse', `${(-y * .72).toFixed(2)}px`);
        group.style.setProperty('--story-shake-rotate', `${rotate.toFixed(2)}deg`);
        group.style.setProperty('--story-shake-rotate-reverse', `${(-rotate * .72).toFixed(2)}deg`);
        await waitForStoryAnimation(group, 'is-gaining', 330);
    }

    async function animateOpeningLightning(target) {
        const layer = $('story-float-layer');
        if (!layer || !target) return;
        const rect = target.getBoundingClientRect();
        const strike = document.createElement('span');
        strike.className = 'story-opening-lightning';
        strike.style.left = `${rect.left + rect.width / 2}px`;
        strike.style.top = `${Math.max(-24, rect.top - 104)}px`;
        strike.style.height = `${Math.max(160, rect.height + 118)}px`;
        const bolt = document.createElement('span');
        bolt.className = 'story-opening-lightning-bolt';
        const flash = document.createElement('span');
        flash.className = 'story-opening-lightning-flash';
        strike.append(bolt, flash);
        layer.append(strike);
        try {
            await Promise.all([
                waitForStoryAnimation(strike, 'is-striking', 520),
                waitForStoryAnimation(target, 'is-opening-lightning-hit', 520),
            ]);
        } finally {
            strike.remove();
        }
    }

    async function animateEnemySummon(event, nextRun) {
        const actor = ensureStorySummonedActor(event, nextRun);
        if (!actor) return;
        spawnStoryFloat(actor, t.summon, 'gain');
        await waitForStoryAnimation(actor, 'is-summoning', 520);
        actor.classList.remove('is-presentation-spawn');
    }

    async function animateEnemyDefeat(event) {
        const actor = storyEnemyActor(event?.enemy_id);
        if (!actor || actor.classList.contains('is-defeated-complete')) return;
        spawnStoryFloat(actor, t.defeated, 'damage');
        await waitForStoryAnimation(actor, 'is-defeating', 460);
        actor.classList.add('is-defeated-complete');
        actor.setAttribute('aria-hidden', 'true');
        actor.tabIndex = -1;
        syncStoryEnemyGroupLayout();
    }

    async function animateStoryPileMove(event, destination) {
        const source = event?.card_instance_id
            ? document.querySelector(
                `.story-hand-card[data-instance-id="${CSS.escape(String(event.card_instance_id))}"] .story-card`,
            )
            : null;
        const target = destination === 'draw'
            ? $('story-draw-pile')
            : destination === 'exile'
                ? $('story-exile-pile')
                : $('story-discard-pile');
        if (!target) return;
        const sourceRect = source?.getBoundingClientRect() || $('story-hand')?.getBoundingClientRect();
        const targetRect = target.getBoundingClientRect();
        if (!sourceRect) return;
        const ghost = source?.cloneNode(true) || document.createElement('span');
        ghost.classList.add('story-pile-motion');
        if (!source) ghost.classList.add('story-pile-motion-back');
        ghost.style.left = `${sourceRect.left}px`;
        ghost.style.top = `${sourceRect.top}px`;
        ghost.style.width = `${Math.max(34, sourceRect.width)}px`;
        ghost.style.height = `${Math.max(48, sourceRect.height)}px`;
        ghost.style.setProperty('--story-pile-x', `${targetRect.left + targetRect.width / 2 - sourceRect.left - sourceRect.width / 2}px`);
        ghost.style.setProperty('--story-pile-y', `${targetRect.top + targetRect.height / 2 - sourceRect.top - sourceRect.height / 2}px`);
        document.body.append(ghost);
        await waitForStoryAnimation(ghost, 'is-moving', 300);
        ghost.remove();
    }

    async function animateStoryDraw(event) {
        const source = $('story-draw-pile');
        const target = $('story-hand');
        if (!source || !target) return;
        const sourceRect = source.getBoundingClientRect();
        const targetRect = target.getBoundingClientRect();
        const ghost = document.createElement('span');
        ghost.className = 'story-pile-motion story-pile-motion-back';
        ghost.style.left = `${sourceRect.left + sourceRect.width / 2 - 22}px`;
        ghost.style.top = `${sourceRect.top + sourceRect.height / 2 - 31}px`;
        ghost.style.width = '44px';
        ghost.style.height = '62px';
        ghost.style.setProperty('--story-pile-x', `${targetRect.left + targetRect.width / 2 - sourceRect.left - sourceRect.width / 2}px`);
        ghost.style.setProperty('--story-pile-y', `${targetRect.top + targetRect.height * .58 - sourceRect.top - sourceRect.height / 2}px`);
        if (Number(event?.count) > 1) ghost.dataset.count = String(event.count);
        document.body.append(ghost);
        await waitForStoryAnimation(ghost, 'is-moving', 300);
        ghost.remove();
    }

    function enemyMoveHasDamage(event) {
        const enemy = activeRun?.state?.combat?.enemies?.find(
            (item) => String(item.id) === String(event?.enemy_id),
        );
        const definition = storyContent?.enemies?.[enemy?.def_id];
        const move = definition?.moves?.[Number(event?.move_index) || 0];
        return (move?.effects || []).some((effect) => effect?.type === 'damage');
    }

    function updateAnimatedEnemyHealth(event, nextRun) {
        const history = Array.isArray(event?.history) ? event.history : [];
        const finalHit = history[history.length - 1];
        const after = Number.isFinite(Number(event?.after))
            ? Number(event.after)
            : Number(finalHit?.after);
        if (!Number.isFinite(after)) return;
        const enemy = nextRun?.state?.combat?.enemies?.find(
            (item) => String(item.id) === String(event.enemy_id),
        ) || activeRun?.state?.combat?.enemies?.find(
            (item) => String(item.id) === String(event.enemy_id),
        );
        updateAnimatedEnemyHealthValue(event.enemy_id, after, enemy?.max_health);
    }

    function updateAnimatedPlayerHealth(event, nextRun) {
        const after = Number(event?.after);
        if (!Number.isFinite(after)) return;
        setHealthBar(
            'story-combat-player',
            after,
            nextRun?.state?.player?.max_health || activeRun?.state?.player?.max_health,
        );
    }

    function updateAnimatedEnemyHealthValue(enemyId, health, maximum) {
        const actor = storyEnemyActor(enemyId);
        const current = Number(health);
        const maxHealth = Math.max(1, Number(maximum) || 1);
        if (!actor || !Number.isFinite(current)) return;
        const fill = actor.querySelector('[data-enemy-health-fill]');
        const value = actor.querySelector('[data-enemy-health-value]');
        if (fill) fill.style.width = `${Math.max(0, Math.min(100, current / maxHealth * 100))}%`;
        if (value) value.textContent = `${Math.max(0, current)}/${maxHealth}`;
    }

    function storyPresentationEffectContainer(targetId) {
        if (String(targetId || '') === 'player') return $('story-player-effects');
        return storyEnemyActor(targetId)?.querySelector('.story-effect-list') || null;
    }

    function syncStoryPresentationPatch(patch, nextRun) {
        if (!patch || typeof patch !== 'object') return;
        const player = patch.player;
        if (player && typeof player === 'object') {
            const health = Number(player.health);
            if (Number.isFinite(health)) {
                setHealthBar(
                    'story-combat-player',
                    health,
                    player.max_health ?? nextRun?.state?.player?.max_health
                        ?? activeRun?.state?.player?.max_health,
                );
            }
        }
        const combat = patch.combat;
        if (combat && typeof combat === 'object') {
            if (Number.isFinite(Number(combat.elixir))) {
                renderResourceOrbs('story-combat-player-elixir', Number(combat.elixir), 0, 'e');
            }
            if (Number.isFinite(Number(combat.magic))) {
                renderResourceOrbs('story-combat-player-magic', Number(combat.magic), 0, 'm');
            }
            Object.entries(combat.effects || {}).forEach(([key, amount]) => {
                updateStoryEffectValue($('story-player-effects'), key, amount);
            });
        }
        Object.entries(patch.enemies || {}).forEach(([enemyId, enemy]) => {
            if (!enemy || typeof enemy !== 'object') return;
            if (Number.isFinite(Number(enemy.health))) {
                const fallback = nextRun?.state?.combat?.enemies?.find(
                    (item) => String(item.id) === String(enemyId),
                );
                updateAnimatedEnemyHealthValue(
                    enemyId,
                    Number(enemy.health),
                    enemy.max_health ?? fallback?.max_health,
                );
            }
            Object.entries(enemy.effects || {}).forEach(([key, amount]) => {
                updateStoryEffectValue(storyPresentationEffectContainer(enemyId), key, amount);
            });
        });
    }

    function syncStoryPresentationEvent(event, nextRun) {
        const eventType = String(event?.type || event?.kind || '');
        if (!eventType) return;
        if (eventType === 'player_damage' || eventType === 'heal') {
            updateAnimatedPlayerHealth(event, nextRun);
        } else if (['enemy_damage', 'enemy_heal', 'enemy_revived'].includes(eventType)) {
            updateAnimatedEnemyHealth(event, nextRun);
        }

        if (eventType === 'enemy_gain') {
            updateStoryEffectValue(
                storyPresentationEffectContainer(event.enemy_id),
                String(event.effect_kind || ''),
                event.after,
            );
        } else if (eventType === 'status') {
            updateStoryEffectValue(
                storyPresentationEffectContainer(event.target_id),
                String(event.status || ''),
                event.after,
            );
        } else if (eventType === 'status_cleared') {
            updateStoryEffectValue(
                storyPresentationEffectContainer(event.target_id),
                String(event.status || ''),
                0,
            );
        } else if (eventType === 'shield') {
            updateStoryEffectValue($('story-player-effects'), 'shield', event.after);
        } else if (eventType === 'elixir' && Number.isFinite(Number(event.after))) {
            renderResourceOrbs('story-combat-player-elixir', Number(event.after), 0, 'e');
        } else if (eventType === 'magic' && Number.isFinite(Number(event.after))) {
            renderResourceOrbs('story-combat-player-magic', Number(event.after), 0, 'm');
        }
        syncStoryPresentationPatch(event.presentation_patch, nextRun);
    }

    function storyEventBatches(sequence) {
        const groups = new Map();
        sequence.forEach((event) => {
            const group = String(event?.parallel_group || '');
            if (!group) return;
            if (!groups.has(group)) groups.set(group, []);
            groups.get(group).push(event);
        });
        const emitted = new Set();
        const batches = [];
        sequence.forEach((event) => {
            const group = String(event?.parallel_group || '');
            if (!group) {
                batches.push([event]);
                return;
            }
            if (emitted.has(group)) return;
            emitted.add(group);
            batches.push(groups.get(group) || [event]);
        });
        return batches;
    }

    async function playStoryPresentationEvent(event, nextRun) {
        const eventType = String(event?.type || event?.kind || '');
        if (!eventType) return;
        if (eventType === 'enemy_action') {
            const motion = String(event.presentation?.motion || '');
            if (motion === 'attack' || (!motion && enemyMoveHasDamage(event))) {
                await animateEnemyLunge(event.enemy_id);
            } else {
                await animateEnemyGain(event.enemy_id);
            }
        } else if (eventType === 'player_damage') {
            const target = $('story-player-target');
            if (Number(event.amount) > 0) triggerStoryPlayerDamageMood();
            await waitForStoryAnimation(target, 'is-taking-hit', 280);
            const history = Array.isArray(event.history) ? event.history : [];
            const finalHit = history[history.length - 1];
            const after = Number.isFinite(Number(event.after))
                ? Number(event.after)
                : Number(finalHit?.after);
            if (Number.isFinite(after)) {
                setHealthBar(
                    'story-combat-player',
                    after,
                    nextRun?.state?.player?.max_health || activeRun?.state?.player?.max_health,
                );
            }
            spawnStoryFloat(target, `-${Math.max(0, Number(event.amount) || 0)}H`, 'damage');
        } else if (eventType === 'enemy_damage') {
            const target = storyEnemyActor(event.enemy_id);
            if (String(event.source || '') === 'opening_lightning') {
                const strike = animateOpeningLightning(target);
                await storySleep(105);
                updateAnimatedEnemyHealth(event, nextRun);
                spawnStoryFloat(target, `-${Math.max(0, Number(event.amount) || 0)}H`, 'damage');
                await strike;
            } else {
                updateAnimatedEnemyHealth(event, nextRun);
                await waitForStoryAnimation(target, 'is-taking-hit', 280);
                spawnStoryFloat(target, `-${Math.max(0, Number(event.amount) || 0)}H`, 'damage');
            }
        } else if (eventType === 'enemy_gain') {
            const target = storyEnemyActor(event.enemy_id);
            const effectKind = event.effect_kind || (
                event.kind !== event.type ? event.kind : ''
            );
            await animateEnemyGain(event.enemy_id);
            spawnStoryFloat(
                target,
                `${storyEventAmount(event.amount)} ${storyIntentStatusLabel(effectKind)}`,
                'gain',
            );
        } else if (eventType === 'enemy_heal') {
            const target = storyEnemyActor(event.enemy_id);
            spawnStoryFloat(target, `${storyEventAmount(event.amount)}H`, 'heal');
            await waitForStoryAnimation(target, 'is-recovering', 260);
        } else if (eventType === 'heal') {
            const target = $('story-player-target');
            spawnStoryFloat(target, `${storyEventAmount(event.amount)}H`, 'heal');
            await waitForStoryAnimation(target, 'is-recovering', 260);
        } else if (eventType === 'shield') {
            spawnStoryFloat($('story-player-target'), `${storyEventAmount(event.amount)} ${t.shield}`, 'shield');
        } else if (eventType === 'status') {
            const target = String(event.target_id || '') === 'player'
                ? $('story-player-target')
                : storyEnemyActor(event.target_id);
            spawnStoryFloat(
                target,
                `${storyEventAmount(event.amount)} ${storyIntentStatusLabel(event.status)}`,
                'status',
            );
        } else if (eventType === 'elixir') {
            spawnStoryFloat($('story-player-target'), `${storyEventAmount(event.amount)}E`, 'elixir');
        } else if (eventType === 'magic') {
            spawnStoryFloat($('story-player-target'), `${storyEventAmount(event.amount)}M`, 'magic');
        } else if (eventType === 'draw') {
            await animateStoryDraw(event);
        } else if (eventType === 'card_discarded') {
            await animateStoryPileMove(event, 'discard');
        } else if (eventType === 'card_exiled') {
            await animateStoryPileMove(event, 'exile');
        } else if (eventType === 'equipment_added') {
            spawnStoryFloat($('story-player-target'), localize(storyContent?.cards?.[event.def_id]?.name), 'equipment');
        } else if (eventType === 'enemy_summoned') {
            await animateEnemySummon(event, nextRun);
        } else if (eventType === 'enemy_withered') {
            spawnStoryFloat(storyEnemyActor(event.enemy_id), storyIntentStatusLabel('wither'), 'status');
        } else if (eventType === 'enemy_defeated') {
            await animateEnemyDefeat(event);
        }
    }

    async function playStoryEventSequence(events, nextRun, actionType) {
        const sequence = (Array.isArray(events) ? events : [])
            .map((event, index) => ({ event, index }))
            .sort((left, right) => {
                const leftSequence = Number(left.event?.sequence);
                const rightSequence = Number(right.event?.sequence);
                if (Number.isFinite(leftSequence) && Number.isFinite(rightSequence)) {
                    return leftSequence - rightSequence || left.index - right.index;
                }
                if (Number.isFinite(leftSequence)) return -1;
                if (Number.isFinite(rightSequence)) return 1;
                return left.index - right.index;
            })
            .map((item) => item.event);
        if (!sequence.length || !$('story-enemy-group') || $('story-combat')?.classList.contains('hidden')) return;

        selectedCombatCardId = '';
        destroyStoryCursorCard();
        $('story-aim-layer')?.classList.add('hidden');
        $('story-player-target')?.classList.remove('is-play-target', 'is-aim-hover');
        document.querySelectorAll('.story-actor-enemy').forEach((actor) => {
            actor.classList.remove('is-play-target', 'is-aim-hover');
        });
        setText('story-play-hint', '');
        if (actionType === 'end_turn') setText('story-phase', t.enemyTurn);
        const endTurn = $('story-end-turn');
        if (endTurn) endTurn.disabled = true;
        document.body.dataset.enemyAnimating = 'true';

        try {
            for (const batch of storyEventBatches(sequence)) {
                await Promise.all(
                    batch.map(async (event) => {
                        try {
                            syncStoryPresentationEvent(event, nextRun);
                            await playStoryPresentationEvent(event, nextRun);
                        } catch (error) {
                            console.warn('[story] presentation event failed', event?.type || event?.kind, error);
                        } finally {
                            syncStoryPresentationEvent(event, nextRun);
                        }
                    }),
                );
                await storySleep(32);
            }
        } finally {
            delete document.body.dataset.enemyAnimating;
        }
    }

    async function storyAction(actionType, payload = {}) {
        if (!activeRun || actionInFlight) return null;
        actionInFlight = true;
        document.body.dataset.actionInFlight = 'true';
        updateStorySurrenderControl();
        try {
            const previousPhase = String(activeRun?.state?.phase || '');
            const result = await requestJson('/api/story/run/action', {
                method: 'POST',
                body: JSON.stringify({
                    run_id: activeRun.id,
                    state_version: activeRun.state_version,
                    action_id: createActionId(),
                    action_type: actionType,
                    payload,
                    client_id: STORY_PRESENCE_CLIENT_ID,
                }),
            });
            const nextRun = result.run || activeRun;
            const enteringCombat = previousPhase !== 'combat'
                && String(nextRun?.state?.phase || '') === 'combat';
            const entranceRun = enteringCombat
                ? createStoryCombatEntranceRun(nextRun, result.events)
                : null;
            if (entranceRun) {
                storyCombatEntranceAnimating = true;
                renderRun(entranceRun);
                await storyNextPaint();
            }
            try {
                await playStoryEventSequence(result.events, nextRun, actionType);
            } finally {
                storyCombatEntranceAnimating = false;
                renderRun(nextRun);
            }
            ingestStoryDiscoveryPayload(result, { notify: true });
            return result;
        } catch (error) {
            if (error.message === 'AUTH_REQUIRED') return null;
            if (error.payload?.run) renderRun(error.payload.run);
            showToast(error.message || t.requestFailed);
            return null;
        } finally {
            actionInFlight = false;
            delete document.body.dataset.actionInFlight;
            updateStorySurrenderControl();
        }
    }

    function renderLegend() {
        const legend = $('story-map-legend');
        if (!legend) return;
        legend.replaceChildren();
        ['combat', 'elite', 'event', 'rest', 'shop', 'chest', 'boss'].forEach((type) => {
            const item = document.createElement('span');
            item.className = 'story-map-legend-item';
            const dot = document.createElement('i');
            dot.className = 'story-map-legend-dot';
            dot.dataset.roomType = type;
            const label = document.createElement('span');
            label.textContent = t.rooms[type];
            item.append(dot, label);
            legend.append(item);
        });
    }

    function mapPoint(node) {
        const width = 760;
        const height = 1040;
        const horizontalPadding = 56;
        const verticalPadding = 48;
        return {
            x: horizontalPadding + node.x * (width - horizontalPadding * 2),
            y: height - verticalPadding - ((node.floor - 1) / 15) * (height - verticalPadding * 2),
        };
    }

    function svgElement(tag, attributes = {}) {
        const element = document.createElementNS(SVG_NS, tag);
        Object.entries(attributes).forEach(([name, value]) => element.setAttribute(name, String(value)));
        return element;
    }

    function mapEdgeSegment(start, end) {
        const dx = Number(end.x) - Number(start.x);
        const dy = Number(end.y) - Number(start.y);
        const distance = Math.hypot(dx, dy);
        if (!Number.isFinite(distance) || distance <= STORY_MAP_EDGE_INSET * 2) return null;
        const unitX = dx / distance;
        const unitY = dy / distance;
        return {
            start: {
                x: Number(start.x) + unitX * STORY_MAP_EDGE_INSET,
                y: Number(start.y) + unitY * STORY_MAP_EDGE_INSET,
            },
            end: {
                x: Number(end.x) - unitX * STORY_MAP_EDGE_INSET,
                y: Number(end.y) - unitY * STORY_MAP_EDGE_INSET,
            },
        };
    }

    function renderMap(map, currentNodeId, options = {}) {
        const svg = $('story-map');
        if (!svg || !map || !Array.isArray(map.floors)) return;
        svg.replaceChildren();
        const nodes = new Map();
        map.floors.forEach((floor) => floor.nodes.forEach((node) => nodes.set(node.id, node)));
        const edgeGroup = svgElement('g', { 'aria-hidden': 'true' });
        (map.edges || []).forEach((edge) => {
            const from = nodes.get(edge.from);
            const to = nodes.get(edge.to);
            if (!from || !to) return;
            const start = mapPoint(from);
            const end = mapPoint(to);
            const segment = mapEdgeSegment(start, end);
            if (!segment) return;
            const traversed = from.status === 'completed'
                && (to.status === 'completed' || String(to.id) === String(currentNodeId));
            const next = String(from.id) === String(currentNodeId) && to.status === 'available';
            edgeGroup.append(svgElement('line', {
                class: `story-map-edge${traversed ? ' is-traversed' : ''}${next ? ' is-next' : ''}`,
                x1: segment.start.x,
                y1: segment.start.y,
                x2: segment.end.x,
                y2: segment.end.y,
            }));
        });
        svg.append(edgeGroup);

        map.floors.forEach((floor) => floor.nodes.forEach((node) => {
            const point = mapPoint(node);
            const actionable = !options.readOnly && node.status === 'available';
            const routeCurrent = String(node.id) === String(currentNodeId);
            const group = svgElement('g', {
                class: `story-map-node${actionable ? ' is-actionable' : ''}${routeCurrent ? ' is-route-current' : ''}`,
                transform: `translate(${point.x} ${point.y})`,
                'data-room-type': node.type,
                'data-status': node.status || 'locked',
                role: actionable ? 'button' : 'img',
                tabindex: actionable ? '0' : '-1',
                'aria-label': `${t.floor(node.floor)} ${t.rooms[node.type] || node.type}`,
            });
            group.append(svgElement('circle', {
                cx: 0,
                cy: 0,
                r: STORY_MAP_NODE_RADIUS,
            }));
            const text = svgElement('text', { x: 0, y: 1 });
            text.textContent = t.roomMarks[node.type] || '?';
            group.append(text);
            if (routeCurrent) {
                group.append(svgElement('circle', {
                    class: 'story-map-current-marker',
                    cx: 0,
                    cy: -37,
                    r: 5,
                }));
            }
            if (actionable) {
                const choose = () => storyAction('enter_node', { node_id: node.id });
                group.addEventListener('click', choose);
                group.addEventListener('keydown', (event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        choose();
                    }
                });
            }
            svg.append(group);
        }));

        const focusNode = nodes.get(currentNodeId)
            || Array.from(nodes.values()).find((node) => node.status === 'available');
        const scroller = document.querySelector('.story-map-scroll');
        if (focusNode && scroller) requestAnimationFrame(() => {
            const renderedHeight = svg.getBoundingClientRect().height;
            const scale = renderedHeight > 0 ? renderedHeight / 1040 : 1;
            const targetY = mapPoint(focusNode).y * scale;
            scroller.scrollTop = Math.max(0, targetY - scroller.clientHeight / 2);
        });
    }

    function currentNode(state) {
        for (const floor of state?.map?.floors || []) {
            const found = floor.nodes.find((node) => node.id === state.current_node_id);
            if (found) return found;
        }
        return null;
    }

    function cardValues(card) {
        const definition = storyContent?.cards?.[card?.def_id];
        if (!definition) return null;
        const upgradeLevel = Math.max(
            Number(card?.upgrade_level || 0),
            card?.upgraded ? 1 : 0,
        );
        const values = upgradeLevel
            ? { ...definition, ...(definition.upgrade || {}) }
            : { ...definition };
        values.effects = (values.effects || []).map((effect) => ({ ...effect }));
        if (definition.upgrade?.infinite) {
            const damage = Math.ceil(14 + 3 * upgradeLevel + (upgradeLevel ** 2) / 2);
            values.effects = values.effects.map((effect) => (
                effect.type === 'damage' ? { ...effect, amount: damage } : effect
            ));
            values.description = {
                zh: `对目标造成${damage}D；此牌可无限升级。`,
                en: `Deal ${damage} D. This card can be upgraded indefinitely.`,
            };
        }
        const modifiers = card?.modifiers && typeof card.modifiers === 'object' ? card.modifiers : {};
        if (Number.isFinite(Number(values.cost_e))) {
            values.cost_e = Math.max(0,
                Number(values.cost_e)
                + Number(modifiers.cost_e_delta || 0)
                - Number(modifiers.swift || 0));
        }
        if (Number.isFinite(Number(values.cost_m))) {
            values.cost_m = Math.max(0,
                Number(values.cost_m)
                + Number(modifiers.cost_m_delta || 0)
                - Number(modifiers.magic_swift || 0));
        }
        if (modifiers.free_play) {
            values.cost_e = 0;
            values.cost_m = 0;
        } else if (modifiers.temporary_free_e) {
            values.cost_e = 0;
        }
        const boostEffects = (types, amount, multiplier = 1) => {
            if (!Number(amount)) return;
            values.effects = values.effects.map((effect) => (
                types.includes(String(effect.type || ''))
                    ? {
                        ...effect,
                        amount: Math.max(
                            0,
                            (Number(effect.amount || 0) + Number(amount)) * multiplier,
                        ),
                    }
                    : effect
            ));
        };
        boostEffects(['damage', 'shield'], Number(modifiers.primary_bonus || 0));
        boostEffects(['damage'], Number(modifiers.damage_bonus || 0));
        if (values.rarity === 'primary' && Number(modifiers.primary_multiplier || 0) > 1) {
            const multiplier = Math.max(1, Number(modifiers.primary_multiplier || 1));
            values.effects = values.effects.map((effect) => (
                ['damage', 'shield'].includes(String(effect.type || ''))
                    ? { ...effect, amount: Math.max(0, Number(effect.amount || 0) * multiplier) }
                    : effect
            ));
        }
        const tags = new Set(Array.isArray(values.tags) ? values.tags : []);
        if (modifiers.force_exile) tags.add('exile');
        if (modifiers.force_void) tags.add('void');
        if (modifiers.retain) tags.add('retain');
        values.tags = [...tags];
        return values;
    }

    function storyCardUpgradePrefix(card) {
        const level = Math.max(Number(card?.upgrade_level || 0), card?.upgraded ? 1 : 0);
        if (!level) return '';
        return storyContent?.cards?.[card?.def_id]?.upgrade?.infinite && level > 1
            ? `+${level} `
            : '+';
    }

    function storyCardTypeColor(type) {
        return STORY_CARD_TYPE_COLORS[String(type || '').toLowerCase()] || 'var(--story-line)';
    }

    function storyCardHasUpgrade(card) {
        return Boolean(storyContent?.cards?.[card?.def_id]?.upgrade);
    }

    function storyCardIsUpgradable(card) {
        const upgrade = storyContent?.cards?.[card?.def_id]?.upgrade;
        return Boolean(upgrade && (upgrade.infinite || !card?.upgraded));
    }

    function storyCardAtUpgradeState(card, upgraded) {
        if (upgraded && storyContent?.cards?.[card?.def_id]?.upgrade?.infinite) {
            const currentLevel = Math.max(
                Number(card?.upgrade_level || 0),
                card?.upgraded ? 1 : 0,
            );
            return { ...card, upgraded: true, upgrade_level: currentLevel + 1 };
        }
        return { ...card, upgraded: Boolean(upgraded) };
    }

    function createStoryInlineIcon(unit) {
        const normalizedUnit = String(unit || '').toUpperCase();
        const wrapper = document.createElement('span');
        wrapper.className = 'story-inline-token-icon-wrap';
        const icon = document.createElement('img');
        icon.className = 'story-inline-token-icon';
        icon.src = STORY_INLINE_ICONS[normalizedUnit] || '';
        icon.alt = normalizedUnit;
        const fallback = document.createElement('span');
        fallback.className = 'story-inline-token-icon-fallback';
        fallback.textContent = normalizedUnit;
        icon.addEventListener('error', () => wrapper.classList.add('icon-load-failed'), { once: true });
        wrapper.append(icon, fallback);
        return wrapper;
    }

    function appendStoryValueRichText(container, value) {
        if (!container) return;
        const text = String(value || '');
        const pattern = /(\d+(?:\.\d+)?)\s*(?:(?:\[\[icon:([DHEM])\]\]|([DHEM]))\s*([×xX*])\s*(\d+)|([×xX*])\s*(\d+)\s*(?:\[\[icon:([DHEM])\]\]|([DHEM]))|(?:\[\[icon:([DHEM])\]\]|([DHEM])))(?![A-Za-z])/gi;
        let cursor = 0;
        let match = null;
        while ((match = pattern.exec(text))) {
            if (match.index > cursor) container.append(document.createTextNode(text.slice(cursor, match.index)));
            const unit = String(match[2] || match[3] || match[8] || match[9] || match[10] || match[11] || '').toUpperCase();
            const token = document.createElement('span');
            token.className = `story-inline-token story-inline-token-${unit.toLowerCase()}`;
            const amount = document.createElement('span');
            amount.textContent = match[1];
            token.append(amount);
            if (match[6] && match[7]) {
                const multiplier = document.createElement('span');
                multiplier.textContent = `×${match[7]}`;
                token.append(multiplier, createStoryInlineIcon(unit));
            } else {
                token.append(createStoryInlineIcon(unit));
                if (match[4] && match[5]) {
                    const multiplier = document.createElement('span');
                    multiplier.textContent = `×${match[5]}`;
                    token.append(multiplier);
                }
            }
            container.append(token);
            cursor = pattern.lastIndex;
        }
        if (cursor < text.length) container.append(document.createTextNode(text.slice(cursor)));
    }

    function createStoryInlineCardChip(defId) {
        const cardId = String(defId || '').trim();
        const card = {
            instance_id: `story-inline:${cardId}`,
            def_id: cardId,
            upgraded: false,
        };
        const values = cardValues(card);
        if (!values) return null;
        const chip = document.createElement('span');
        chip.className = 'story-event-card-chip';
        chip.style.setProperty('--story-chip-color', storyCardTypeColor(values.type));
        chip.textContent = localize(values.name) || cardId;
        chip.setAttribute('role', 'button');
        chip.setAttribute('aria-label', `${chip.textContent} · ${t.cardTerms}`);
        chip.tabIndex = 0;
        chip.addEventListener('keydown', (event) => {
            if (event.key !== 'ContextMenu' && !(event.shiftKey && event.key === 'F10')) return;
            event.preventDefault();
            event.stopPropagation();
            openStoryCardTerms(card);
        });
        storyCardElementData.set(chip, card);
        return chip;
    }

    function appendStoryRichText(container, value) {
        if (!container) return;
        const text = String(value || '');
        const pattern = /\[\[card:([a-z0-9_-]+)\]\]/gi;
        let cursor = 0;
        let match = null;
        while ((match = pattern.exec(text))) {
            if (match.index > cursor) appendStoryValueRichText(container, text.slice(cursor, match.index));
            const chip = createStoryInlineCardChip(match[1]);
            if (chip) container.append(chip);
            else appendStoryValueRichText(container, match[1]);
            cursor = pattern.lastIndex;
        }
        if (cursor < text.length) appendStoryValueRichText(container, text.slice(cursor));
    }

    const pendingStoryCardEffectFits = new Set();
    let pendingStoryCardEffectFitFrame = 0;

    function resetStoryCardEffectFit(effect) {
        if (!effect) return;
        effect.style.removeProperty('font-size');
        effect.style.removeProperty('padding-top');
        effect.style.removeProperty('padding-right');
        effect.style.removeProperty('padding-bottom');
        effect.style.removeProperty('padding-left');
    }

    function fitStoryCardEffect(cardElement) {
        if (!cardElement?.isConnected) return;
        const effect = cardElement.querySelector(':scope > .card-effect');
        if (!effect) return;
        resetStoryCardEffectFit(effect);
        cardElement.dataset.effectFitScale = '1';
        const cardRect = cardElement.getBoundingClientRect();
        if (cardRect.width < 20 || cardRect.height < 20 || effect.getClientRects().length === 0) return;

        const baseStyle = getComputedStyle(effect);
        const baseFontSize = parseFloat(baseStyle.fontSize) || 1;
        const baseLineHeight = parseFloat(baseStyle.lineHeight) || (baseFontSize * 1.2);
        const basePadding = {
            top: parseFloat(baseStyle.paddingTop) || 0,
            right: parseFloat(baseStyle.paddingRight) || 0,
            bottom: parseFloat(baseStyle.paddingBottom) || 0,
            left: parseFloat(baseStyle.paddingLeft) || 0,
        };
        const predictionHeightLimit = cardElement.classList.contains('card-effect-fit-prediction')
            ? baseLineHeight * 3.7
            : Infinity;
        const minimumScale = 0.6;
        let scale = 1;

        for (let pass = 0; pass < 14; pass += 1) {
            const style = getComputedStyle(effect);
            const paddingY = (parseFloat(style.paddingTop) || 0) + (parseFloat(style.paddingBottom) || 0);
            const naturalTextHeight = Math.max(0, effect.scrollHeight - paddingY);
            const overflowed = effect.scrollHeight > effect.clientHeight + 0.75;
            const nextElement = effect.nextElementSibling;
            const effectRect = effect.getBoundingClientRect();
            const nextTop = nextElement
                ? nextElement.getBoundingClientRect().top
                : cardElement.getBoundingClientRect().bottom;
            const spareGap = Math.max(0, nextTop - effectRect.bottom);
            const needsBreathingRoom = spareGap + 0.5 < baseLineHeight * 0.18;
            const predictionTooTall = naturalTextHeight > predictionHeightLimit + 0.5;
            if (!overflowed && !needsBreathingRoom && !predictionTooTall) break;
            if (scale <= minimumScale + 0.001) break;

            let nextScale = scale - 0.04;
            if (predictionTooTall && naturalTextHeight > 0) {
                nextScale = Math.min(
                    nextScale,
                    scale * predictionHeightLimit / naturalTextHeight * 0.985,
                );
            }
            scale = Math.max(minimumScale, nextScale);
            effect.style.fontSize = `${baseFontSize * scale}px`;
            effect.style.paddingTop = `${basePadding.top * scale}px`;
            effect.style.paddingRight = `${basePadding.right * scale}px`;
            effect.style.paddingBottom = `${basePadding.bottom * scale}px`;
            effect.style.paddingLeft = `${basePadding.left * scale}px`;
            cardElement.dataset.effectFitScale = scale.toFixed(3);
        }
    }

    function scheduleStoryCardEffectFit(cardElement) {
        if (!cardElement) return;
        pendingStoryCardEffectFits.add(cardElement);
        if (pendingStoryCardEffectFitFrame) return;
        pendingStoryCardEffectFitFrame = requestAnimationFrame(() => {
            pendingStoryCardEffectFitFrame = 0;
            const cards = [...pendingStoryCardEffectFits];
            pendingStoryCardEffectFits.clear();
            cards.forEach(fitStoryCardEffect);
        });
    }

    function scheduleVisibleStoryCardEffectFits() {
        document.querySelectorAll('.story-card.card').forEach(scheduleStoryCardEffectFit);
    }

    function livingStoryEnemies(state = activeRun?.state) {
        return (state?.combat?.enemies || []).filter((enemy) => Number(enemy.health) > 0);
    }

    function selectableStoryEnemies(card, state = activeRun?.state) {
        const values = cardValues(card);
        let enemies = livingStoryEnemies(state);
        const bulbs = enemies.filter((enemy) => Number(enemy.bulb) > 0);
        if (bulbs.length) enemies = bulbs;
        if (values?.type === 'thorn' && Number(state?.combat?.locked) > 0) {
            enemies = enemies.filter((enemy) => String(enemy.def_id || '') === 'stick');
        }
        return enemies;
    }

    function storyEnemyIsSelectable(card, enemyId, state = activeRun?.state) {
        const expected = String(enemyId || '');
        return selectableStoryEnemies(card, state).some(
            (enemy) => String(enemy.id || '') === expected,
        );
    }

    function storyPredictionTargetId(state = activeRun?.state) {
        const selected = selectedCombatCard(state);
        const living = selected && cardTargetKind(selected) === 'enemy'
            ? selectableStoryEnemies(selected, state)
            : livingStoryEnemies(state);
        if (living.length === 1) return String(living[0].id || '');
        if (living.some((enemy) => String(enemy.id) === String(hoveredPredictionTargetId))) {
            return String(hoveredPredictionTargetId);
        }
        return '';
    }

    function storyCardPrediction(card, targetId = storyPredictionTargetId()) {
        if (!targetId) return null;
        const prediction = activeRun?.state?.combat?.damage_predictions?.[String(card?.instance_id || '')];
        if (!prediction) return null;
        return prediction.by_target?.[String(targetId)] || null;
    }

    function storyTagElement(tagId) {
        const definition = storyContent?.tags?.[tagId];
        if (!definition) return null;
        const style = STORY_TAG_STYLES[String(tagId || '').toLowerCase()] || {
            className: 'custom',
            color: '#34495E',
        };
        const tag = document.createElement('span');
        tag.className = `card-flag ${style.className}`;
        tag.textContent = localize(definition.name);
        tag.title = localize(definition.description);
        if (style.className.includes('custom')) tag.style.setProperty('--custom-tag-color', style.color);
        return tag;
    }

    function createStoryCardBottom(
        card,
        values,
        targetId = storyPredictionTargetId(),
        enablePrediction = false,
    ) {
        const supportsPrediction = enablePrediction && values?.type === 'thorn';
        const prediction = supportsPrediction ? storyCardPrediction(card, targetId) : null;
        const flags = document.createElement('div');
        flags.className = 'card-flags';
        (values?.tags || []).forEach((tagId) => {
            const tag = storyTagElement(tagId);
            if (tag) flags.append(tag);
        });
        const charge = Math.max(0, Number(card?.modifiers?.charge) || 0);
        if (charge) {
            const tag = storyTagElement('charge');
            if (tag) {
                tag.textContent = `${localize(storyContent?.tags?.charge?.name) || 'Charge'}: ${charge}`;
                flags.append(tag);
            }
        }
        if (!flags.childElementCount) flags.classList.add('card-flags-empty');
        if (!supportsPrediction && !flags.childElementCount) return null;

        const bottom = document.createElement('div');
        bottom.className = `card-bottom-zone${supportsPrediction ? ' supports-prediction' : ''}${prediction?.summary ? ' has-prediction' : ''}`;
        if (prediction?.summary) {
            const predictionBox = document.createElement('div');
            predictionBox.className = 'card-prediction';
            predictionBox.setAttribute('aria-label', `${t.damagePrediction}: ${prediction.summary}`);
            const section = document.createElement('span');
            section.className = 'card-prediction-section';
            const label = document.createElement('span');
            label.className = 'card-prediction-label';
            label.textContent = t.damagePrediction;
            const value = document.createElement('span');
            value.className = 'card-prediction-part damage';
            value.textContent = String(prediction.summary);
            section.append(label, value);
            predictionBox.append(section);
            bottom.append(predictionBox);
        }
        if (prediction?.summary || flags.childElementCount) bottom.append(flags);
        return bottom;
    }

    function refreshStoryCardPredictions() {
        if (!activeRun?.state?.combat) return;
        const targetId = storyPredictionTargetId(activeRun.state);
        document.querySelectorAll('#story-hand .story-card.card[data-instance-id]').forEach((element) => {
            const instanceId = String(element.dataset.instanceId || '');
            const card = activeRun.state.combat.hand.find((item) => String(item.instance_id) === instanceId);
            if (!card) return;
            const values = cardValues(card);
            element.querySelector('.card-bottom-zone')?.remove();
            const bottom = createStoryCardBottom(card, values, targetId, true);
            if (bottom) element.append(bottom);
        });
    }

    function setStoryPredictionTarget(targetId) {
        const next = String(targetId || '');
        if (next === hoveredPredictionTargetId) return;
        hoveredPredictionTargetId = next;
        document.querySelectorAll('.story-actor-enemy').forEach((actor) => {
            actor.classList.toggle('is-prediction-hover', String(actor.dataset.targetId || '') === next);
        });
        refreshStoryCardPredictions();
    }

    function cardTargetKind(card) {
        const values = cardValues(card);
        return values?.target === 'enemy' ? 'enemy' : 'self';
    }

    function storyCursorCardMode(card) {
        const values = cardValues(card);
        if (!values) return '';
        const tags = new Set((Array.isArray(values.tags) ? values.tags : [])
            .map((tag) => String(tag || '').trim().toLowerCase()));
        if (tags.has('wide')) return 'untargeted';
        return cardTargetKind(card) === 'self' ? 'self' : '';
    }

    function destroyStoryCursorCard() {
        if (!storyCursorCard) return;
        if (storyCursorCard.timer) window.clearTimeout(storyCursorCard.timer);
        storyCursorCard.source?.classList.remove('has-cursor-follower');
        storyCursorCard.element?.remove();
        storyCursorCard = null;
    }

    function positionStoryCursorCard(clientX, clientY, immediate = false) {
        if (!storyCursorCard || storyCursorCard.returning) return;
        const { element, width, height } = storyCursorCard;
        if (immediate) element.classList.add('is-immediate');
        element.style.transform = `translate3d(${clientX - width / 2}px, ${clientY - height / 2}px, 0)`;
        if (immediate) {
            void element.offsetWidth;
            element.classList.remove('is-immediate');
        }
    }

    function syncStoryCursorCard(state = activeRun?.state) {
        const card = selectedCombatCard(state);
        if (!card || !storyCursorCardMode(card)) {
            destroyStoryCursorCard();
            return;
        }
        const source = document.querySelector(`.story-hand-card[data-instance-id="${CSS.escape(String(card.instance_id))}"]`);
        const cardElement = source?.querySelector('.story-card.card');
        if (!source || !cardElement) {
            destroyStoryCursorCard();
            return;
        }
        if (storyCursorCard?.cardId === String(card.instance_id) && storyCursorCard.source === source) return;
        destroyStoryCursorCard();
        const rect = cardElement.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return;
        const follower = document.createElement('div');
        follower.className = 'story-cursor-card';
        follower.setAttribute('aria-hidden', 'true');
        follower.style.width = `${rect.width}px`;
        follower.style.height = `${rect.height}px`;
        const visual = cardElement.cloneNode(true);
        visual.removeAttribute('id');
        visual.removeAttribute('tabindex');
        visual.disabled = true;
        follower.append(visual);
        $('story-combat')?.append(follower);
        source.classList.add('has-cursor-follower');
        storyCursorCard = {
            cardId: String(card.instance_id),
            element: follower,
            source,
            width: rect.width,
            height: rect.height,
            originX: rect.left + rect.width / 2,
            originY: rect.top + rect.height / 2,
            returning: false,
            timer: 0,
        };
        positionStoryCursorCard(storyCursorCard.originX, storyCursorCard.originY, true);
        requestAnimationFrame(() => positionStoryCursorCard(storyAimPointer.x, storyAimPointer.y));
    }

    function returnStoryCursorCard(onReturned) {
        if (!storyCursorCard) {
            onReturned?.();
            return;
        }
        const motion = storyCursorCard;
        if (motion.returning) return;
        motion.returning = true;
        motion.element.classList.add('is-returning');
        motion.element.style.transform = `translate3d(${motion.originX - motion.width / 2}px, ${motion.originY - motion.height / 2}px, 0)`;
        motion.timer = window.setTimeout(() => {
            if (storyCursorCard === motion) destroyStoryCursorCard();
            onReturned?.();
        }, 190);
    }

    function cancelStoryCombatSelection(withReturn = false) {
        if (!selectedCombatCardId || !activeRun?.state) return false;
        const finish = () => {
            selectedCombatCardId = '';
            renderCombat(activeRun.state);
        };
        if (withReturn && storyCursorCardMode(selectedCombatCard(activeRun.state))) returnStoryCursorCard(finish);
        else finish();
        return true;
    }

    function setHealthBar(prefix, current, maximum) {
        const now = Math.max(0, Number(current) || 0);
        const max = Math.max(1, Number(maximum) || 1);
        setText(`${prefix}-health`, `${now}/${max}`);
        const fill = $(`${prefix}-health-fill`);
        if (fill) fill.style.width = `${Math.max(0, Math.min(100, now / max * 100))}%`;
    }

    const STORY_RESOURCE_SLOT_COUNT = 10;

    function renderResourceOrbs(containerId, current, spend, kind) {
        const container = $(containerId);
        if (!container) return;
        const now = Math.max(0, Math.floor(Number(current) || 0));
        const cost = Math.max(0, Math.floor(Number(spend) || 0));
        const slots = STORY_RESOURCE_SLOT_COUNT;
        container.style.setProperty('--story-resource-slots', String(STORY_RESOURCE_SLOT_COUNT));
        container.setAttribute('aria-label', `${kind.toUpperCase()} ${now}`);
        container.title = `${kind.toUpperCase()} ${now}`;
        setText(`${containerId}-total`, String(now));
        container.replaceChildren();
        const previewChunks = globalThis.GTN_RESOURCE_ORBS.buildPreviewChunks(
            now,
            cost,
            slots,
            10,
            true,
        );
        const stationaryChunks = previewChunks.filter((chunk) => !chunk.willSpend);
        const spendingChunks = previewChunks.filter((chunk) => chunk.willSpend);
        const emptySlotCount = Math.max(0, slots - stationaryChunks.length - spendingChunks.length);
        const emptyChunks = Array.from({ length: emptySlotCount }, () => ({ value: 1, empty: true }));
        const visibleChunks = stationaryChunks.concat(emptyChunks, spendingChunks);
        visibleChunks.forEach((chunk) => {
            const orb = document.createElement('span');
            orb.className = `story-resource-orb story-resource-orb-${kind}`;
            const value = Math.max(1, Number(chunk.value) || 1);
            if (chunk.empty) orb.classList.add('is-empty');
            else if (chunk.missing) orb.classList.add('is-missing');
            else orb.classList.add('is-filled');
            if (value >= 10 || chunk.grouped) {
                orb.classList.add('is-grouped');
                orb.dataset.groupValue = String(value);
            }
            if (chunk.willSpend) orb.classList.add('will-spend');
            container.append(orb);
        });
    }

    function selectedCombatCard(state) {
        const hand = state?.combat?.hand || [];
        return hand.find((card) => String(card.instance_id) === String(selectedCombatCardId)) || null;
    }

    function storyAimPathData(x1, y1, x2, y2) {
        const dx = x2 - x1;
        const dy = y2 - y1;
        const distance = Math.hypot(dx, dy);
        if (distance < 6) return `M ${x1.toFixed(1)} ${y1.toFixed(1)} L ${x2.toFixed(1)} ${y2.toFixed(1)}`;
        const points = [];
        const bend = Math.max(-90, Math.min(90, dx * .12));
        for (let index = 0; index <= 30; index += 1) {
            const progress = index / 30;
            const eased = Math.log1p(progress * 11) / Math.log(12);
            const bow = Math.sin(Math.PI * progress) * bend;
            const x = x1 + dx * progress + bow * .18;
            const y = y1 + dy * eased - Math.sin(Math.PI * progress) * Math.min(42, distance * .16);
            points.push(`${index ? 'L' : 'M'} ${x.toFixed(1)} ${y.toFixed(1)}`);
        }
        return points.join(' ');
    }

    function updateStoryAimHover(card) {
        const targetKind = cardTargetKind(card);
        const hoveredPortrait = document.elementFromPoint(storyAimPointer.x, storyAimPointer.y)?.closest?.('.story-portrait');
        const hovered = hoveredPortrait?.closest?.('.story-actor[data-target-kind]');
        document.querySelectorAll('.story-actor.is-aim-hover').forEach((element) => {
            element.classList.remove('is-aim-hover');
        });
        const validEnemy = targetKind !== 'enemy'
            || storyEnemyIsSelectable(card, hovered?.dataset.targetId, activeRun?.state);
        if (hovered?.dataset.targetKind === targetKind && validEnemy) {
            hovered.classList.add('is-aim-hover');
        }
    }

    function updateAimArrow(state) {
        const layer = $('story-aim-layer');
        const path = $('story-aim-path');
        const outline = $('story-aim-outline');
        const tip = $('story-aim-tip');
        const card = selectedCombatCard(state);
        if (!layer || !path || !outline || !card || storyCursorCardMode(card)) {
            layer?.classList.add('hidden');
            document.querySelectorAll('.story-actor.is-aim-hover').forEach((element) => {
                element.classList.remove('is-aim-hover');
            });
            return;
        }
        const source = document.querySelector(`.story-hand-card[data-instance-id="${CSS.escape(String(card.instance_id))}"]`);
        if (!source) {
            layer.classList.add('hidden');
            return;
        }
        const sourceRect = source.getBoundingClientRect();
        const startX = sourceRect.left + sourceRect.width / 2;
        const startY = sourceRect.top + sourceRect.height / 2;
        const curve = storyAimPathData(startX, startY, storyAimPointer.x, storyAimPointer.y);
        layer.setAttribute('viewBox', `0 0 ${window.innerWidth} ${window.innerHeight}`);
        layer.setAttribute('width', String(window.innerWidth));
        layer.setAttribute('height', String(window.innerHeight));
        path.setAttribute('d', curve);
        outline.setAttribute('d', curve);
        if (tip) {
            tip.setAttribute('cx', storyAimPointer.x.toFixed(1));
            tip.setAttribute('cy', storyAimPointer.y.toFixed(1));
        }
        layer.classList.remove('hidden');
        updateStoryAimHover(card);
    }

    function scheduleStoryAimUpdate(state = activeRun?.state) {
        if (storyAimFrame || !state) return;
        storyAimFrame = requestAnimationFrame(() => {
            storyAimFrame = 0;
            updateAimArrow(state);
        });
    }

    function selectCombatCard(state, card, event = null) {
        if (cardPlayInFlight || actionInFlight) return;
        if (
            event
            && Number(event.detail) > 0
            && Number.isFinite(event.clientX)
            && Number.isFinite(event.clientY)
        ) {
            storyAimPointer = { x: event.clientX, y: event.clientY };
        }
        if (String(selectedCombatCardId) === String(card.instance_id)) {
            if (storyCursorCardMode(card)) {
                returnStoryCursorCard(() => {
                    selectedCombatCardId = '';
                    renderCombat(state);
                });
                return;
            }
            selectedCombatCardId = '';
        } else {
            selectedCombatCardId = String(card.instance_id);
        }
        renderCombat(state);
    }

    function isStoryCardChoiceCandidate(item, sourceCard) {
        if (!item || String(item.instance_id) === String(sourceCard?.instance_id)) return false;
        return !(cardValues(item)?.tags || []).includes('sublime');
    }

    function previewedCombatCard(state) {
        const hand = state?.combat?.hand || [];
        return hand.find((card) => (
            String(card.instance_id) === String(hoveredCombatCardId)
        )) || selectedCombatCard(state);
    }

    function renderCombatResourcePreview(state = activeRun?.state) {
        const combat = state?.combat;
        if (!combat) return;
        const values = cardValues(previewedCombatCard(state));
        renderResourceOrbs(
            'story-combat-player-elixir',
            combat.elixir,
            values?.cost_e,
            'e',
        );
        renderResourceOrbs(
            'story-combat-player-magic',
            combat.magic,
            values?.cost_m,
            'm',
        );
    }

    function cardSelectionSpec(card, combatState = activeRun?.state?.combat || {}) {
        const values = cardValues(card);
        const effects = values?.effects || [];
        const combat = combatState || {};
        for (const effect of effects) {
            const type = String(effect?.type || '');
            if (['choose_exile', 'copy_hand_card', 'make_card_free', 'active_discard'].includes(type)) {
                const exact = ['copy_hand_card', 'make_card_free'].includes(type) || Boolean(effect.exact);
                const source = (combat.hand || []).filter((item) => isStoryCardChoiceCandidate(item, card));
                const requested = Math.max(1, Number(effect.amount || 1));
                const maximum = Math.min(source.length, requested);
                return {
                    source,
                    payloadKey: 'selected_card_ids',
                    maximum,
                    minimum: exact && !(type === 'choose_exile' && source.length === 0)
                        ? requested
                        : 0,
                };
            }
            if (type === 'recover_exiled') {
                const source = (combat.exile_pile || []).filter((item) => (
                    isStoryCardChoiceCandidate(item, null)
                ));
                const requested = Math.max(1, Number(effect.amount || 1));
                const maximum = Math.min(source.length, requested);
                return {
                    source,
                    payloadKey: 'selected_exile_ids',
                    maximum,
                    minimum: requested,
                };
            }
            if (type === 'discard_to_draw_top' && (combat.discard_pile || []).length) {
                return {
                    source: (combat.discard_pile || []).filter((item) => isStoryCardChoiceCandidate(item, null)),
                    payloadKey: 'selected_discard_ids',
                    maximum: 1,
                    minimum: 1,
                };
            }
        }
        return null;
    }

    function setStoryCardChoiceRequired(required) {
        const dialog = $('story-card-choice-dialog');
        if (dialog) dialog.dataset.required = required ? '1' : '0';
        $('story-card-choice-close')?.classList.toggle('hidden', required);
        $('story-card-choice-cancel')?.classList.toggle('hidden', required);
    }

    function toggleStoryCardChoice(wrapper, id, maximum) {
        if (!cardChoiceContext) return;
        const selected = cardChoiceContext.selected;
        if (selected.has(id)) {
            selected.delete(id);
            wrapper.classList.remove('is-selected');
            return;
        }
        if (maximum === 1) {
            selected.clear();
            $('story-card-choice-grid')?.querySelectorAll('.story-card-choice-select-item.is-selected')
                .forEach((item) => item.classList.remove('is-selected'));
        }
        if (selected.size >= maximum) return;
        selected.add(id);
        wrapper.classList.add('is-selected');
    }

    function openCardSelection(card, targetKind, targetId) {
        const spec = cardSelectionSpec(card);
        if (!spec) return false;
        if (!spec.source.length && spec.minimum === 0) return false;
        const dialog = $('story-card-choice-dialog');
        const grid = $('story-card-choice-grid');
        if (!dialog || !grid) return false;
        setStoryCardChoiceRequired(false);
        cardChoiceContext = {
            cardId: String(card.instance_id),
            targetKind,
            targetId: String(targetId || ''),
            spec,
            selected: new Set(),
        };
        setText('story-card-choice-title', t.chooseCards);
        setText('story-card-choice-copy',
            spec.minimum === spec.maximum
                ? t.chooseExact(spec.maximum)
                : t.chooseUpTo(spec.maximum));
        grid.replaceChildren();
        spec.source.forEach((choiceCard) => {
            const wrapper = document.createElement('button');
            wrapper.type = 'button';
            wrapper.className = 'story-card-choice-select-item';
            wrapper.dataset.instanceId = String(choiceCard.instance_id);
            wrapper.append(createStoryCard(choiceCard, { interactive: false, compact: true }));
            wrapper.addEventListener('click', () => {
                const id = String(choiceCard.instance_id);
                toggleStoryCardChoice(wrapper, id, spec.maximum);
                const count = cardChoiceContext?.selected.size || 0;
                $('story-card-choice-confirm').disabled = count < spec.minimum || count > spec.maximum;
            });
            grid.append(wrapper);
        });
        $('story-card-choice-confirm').disabled = spec.minimum > 0;
        dialog.showModal();
        return true;
    }

    function openOpeningRedraw(state) {
        const combat = state?.combat || {};
        const dialog = $('story-card-choice-dialog');
        const grid = $('story-card-choice-grid');
        if (!combat.opening_redraw_pending || !dialog || !grid || dialog.open) return;
        setStoryCardChoiceRequired(false);
        const source = [...(combat.hand || [])];
        const spec = {
            source,
            payloadKey: 'selected_card_ids',
            maximum: source.length,
            minimum: 0,
        };
        cardChoiceContext = {
            mode: 'opening_redraw',
            spec,
            selected: new Set(),
        };
        setText('story-card-choice-title', lang === 'zh' ? '冷却' : 'Cooldown');
        setText(
            'story-card-choice-copy',
            lang === 'zh'
                ? '选择任意张手牌丢弃，然后抽取等量牌。'
                : 'Discard any number of cards, then draw the same number.',
        );
        grid.replaceChildren();
        source.forEach((choiceCard) => {
            const wrapper = document.createElement('button');
            wrapper.type = 'button';
            wrapper.className = 'story-card-choice-select-item';
            wrapper.dataset.instanceId = String(choiceCard.instance_id);
            wrapper.append(createStoryCard(choiceCard, { interactive: false, compact: true }));
            wrapper.addEventListener('click', () => {
                const id = String(choiceCard.instance_id);
                if (cardChoiceContext?.selected.has(id)) {
                    cardChoiceContext.selected.delete(id);
                    wrapper.classList.remove('is-selected');
                } else {
                    cardChoiceContext?.selected.add(id);
                    wrapper.classList.add('is-selected');
                }
            });
            grid.append(wrapper);
        });
        $('story-card-choice-confirm').disabled = false;
        dialog.showModal();
    }

    function openPendingStoryCardChoice(state) {
        const pending = state?.combat?.pending_card_choice;
        const dialog = $('story-card-choice-dialog');
        const grid = $('story-card-choice-grid');
        if (!pending || !dialog || !grid) return false;
        if (
            dialog.open
            && cardChoiceContext?.mode === 'pending_card'
            && String(cardChoiceContext.choiceKind) === String(pending.kind)
        ) return true;
        if (dialog.open) return false;
        const source = Array.isArray(pending.cards) ? pending.cards : [];
        const maximum = Math.min(
            source.length,
            Math.max(0, Number(pending.maximum || 0)),
        );
        const minimum = Math.min(
            maximum,
            Math.max(0, Number(pending.minimum || 0)),
        );
        const spec = {
            source,
            payloadKey: 'selected_card_ids',
            minimum,
            maximum,
        };
        cardChoiceContext = {
            mode: 'pending_card',
            choiceKind: String(pending.kind || ''),
            spec,
            selected: new Set(),
        };
        setStoryCardChoiceRequired(true);
        setText('story-card-choice-title', localize(pending.title) || t.chooseCards);
        setText(
            'story-card-choice-copy',
            minimum === maximum ? t.chooseExact(maximum) : t.chooseUpTo(maximum),
        );
        grid.replaceChildren();
        source.forEach((choiceCard) => {
            const wrapper = document.createElement('button');
            wrapper.type = 'button';
            wrapper.className = 'story-card-choice-select-item';
            wrapper.dataset.instanceId = String(choiceCard.instance_id || '');
            wrapper.append(createStoryCard(choiceCard, { interactive: false, compact: true }));
            wrapper.addEventListener('click', () => {
                toggleStoryCardChoice(wrapper, String(choiceCard.instance_id || ''), maximum);
                const count = cardChoiceContext?.selected.size || 0;
                $('story-card-choice-confirm').disabled = count < minimum || count > maximum;
            });
            grid.append(wrapper);
        });
        $('story-card-choice-confirm').disabled = minimum > 0;
        dialog.showModal();
        return true;
    }

    function openPendingStoryDeckOperation(state) {
        const operation = state?.pending_deck_operations?.[0];
        const dialog = $('story-card-choice-dialog');
        const grid = $('story-card-choice-grid');
        if (!operation || !dialog || !grid) return false;
        if (
            dialog.open
            && cardChoiceContext?.mode === 'deck_operation'
            && String(cardChoiceContext.operationId) === String(operation.id)
        ) return true;
        if (dialog.open) return false;
        const allowed = new Set((operation.candidate_ids || []).map(String));
        const source = (state?.player?.deck || []).filter((card) => (
            allowed.has(String(card.instance_id))
        ));
        const maximum = Math.max(0, Number(operation.maximum ?? operation.count) || 0);
        const minimum = Math.min(
            maximum,
            Math.max(0, Number(operation.minimum ?? maximum) || 0),
        );
        const labels = {
            upgrade: t.upgrade,
            remove: t.remove,
            enchant_amulet: lang === 'zh' ? '附魔护身符' : 'Enchant Amulet',
        };
        const spec = {
            source,
            payloadKey: 'selected_card_ids',
            minimum,
            maximum,
        };
        cardChoiceContext = {
            mode: 'deck_operation',
            operationId: String(operation.id || ''),
            spec,
            selected: new Set(),
        };
        setStoryCardChoiceRequired(true);
        setText('story-card-choice-title', labels[operation.kind] || t.chooseCards);
        setText(
            'story-card-choice-copy',
            minimum === maximum ? t.chooseExact(maximum) : t.chooseUpTo(maximum),
        );
        grid.replaceChildren();
        source.forEach((choiceCard) => {
            const wrapper = document.createElement('button');
            wrapper.type = 'button';
            wrapper.className = 'story-card-choice-select-item';
            wrapper.dataset.instanceId = String(choiceCard.instance_id);
            wrapper.append(createStoryCard(choiceCard, {
                interactive: false,
                compact: true,
                previewUpgradeOnHover: operation.kind === 'upgrade',
            }));
            wrapper.addEventListener('click', () => {
                const id = String(choiceCard.instance_id);
                toggleStoryCardChoice(wrapper, id, maximum);
                $('story-card-choice-confirm').disabled = (
                    (cardChoiceContext?.selected.size || 0) < minimum
                    || (cardChoiceContext?.selected.size || 0) > maximum
                );
            });
            grid.append(wrapper);
        });
        $('story-card-choice-confirm').disabled = minimum > 0;
        dialog.showModal();
        return true;
    }

    async function performSelectedCombatCard(targetKind, targetId = '', extraPayload = {}) {
        if (cardPlayInFlight || actionInFlight || !activeRun) return;
        const state = activeRun.state || {};
        const card = selectedCombatCard(state);
        if (!card || cardTargetKind(card) !== targetKind) return;
        if (targetKind === 'enemy' && !storyEnemyIsSelectable(card, targetId, state)) return;
        const wrapper = document.querySelector(`.story-hand-card[data-instance-id="${CSS.escape(String(card.instance_id))}"]`);
        const target = targetKind === 'enemy'
            ? document.querySelector(`.story-actor-enemy[data-target-id="${CSS.escape(String(targetId || ''))}"]`)
            : $('story-player-target');
        cardPlayInFlight = true;
        destroyStoryCursorCard();
        if (wrapper && target) {
            const sourceRect = wrapper.getBoundingClientRect();
            const targetRect = target.querySelector('.story-portrait')?.getBoundingClientRect() || target.getBoundingClientRect();
            wrapper.style.setProperty('--play-x', `${targetRect.left + targetRect.width / 2 - sourceRect.left - sourceRect.width / 2}px`);
            wrapper.style.setProperty('--play-y', `${targetRect.top + targetRect.height / 2 - sourceRect.top - sourceRect.height / 2}px`);
            wrapper.classList.add('is-playing');
            await new Promise((resolve) => setTimeout(resolve, 210));
        }
        selectedCombatCardId = '';
        try {
            await storyAction('play_card', {
                card_instance_id: card.instance_id,
                ...(targetId ? { target_id: targetId } : {}),
                ...extraPayload,
            });
        } finally {
            cardPlayInFlight = false;
        }
    }

    function playSelectedCombatCard(targetKind, targetId = '') {
        if (cardPlayInFlight || actionInFlight || !activeRun) return;
        const card = selectedCombatCard(activeRun.state);
        if (!card || cardTargetKind(card) !== targetKind) return;
        if (targetKind === 'enemy' && !storyEnemyIsSelectable(card, targetId, activeRun.state)) return;
        if (openCardSelection(card, targetKind, targetId)) return;
        performSelectedCombatCard(targetKind, targetId);
    }

    function createStoryPileTile(card, order) {
        const values = cardValues(card);
        if (!values) return document.createTextNode('');
        const entry = document.createElement('div');
        entry.className = 'story-pile-entry';
        const tile = document.createElement('span');
        tile.className = 'story-pile-tile';
        tile.style.setProperty('--tile-color', storyCardTypeColor(values.type));
        const inner = document.createElement('span');
        inner.className = 'story-pile-tile-inner';
        const costs = document.createElement('div');
        costs.className = 'story-pile-tile-costs';
        costs.innerHTML = `<span class="story-pile-tile-cost cost-e">${Number(values.cost_e || 0)}</span><span class="story-pile-tile-cost cost-m">${Number(values.cost_m || 0)}</span>`;
        const name = document.createElement('div');
        name.className = 'story-pile-tile-name';
        name.textContent = `${storyCardUpgradePrefix(card)}${localize(values.name)}`;
        const art = document.createElement('div');
        art.className = 'story-pile-tile-art';
        const imageUrl = card.upgraded ? (values.upgraded_image_url || values.image_url) : values.image_url;
        if (imageUrl) {
            const image = document.createElement('img');
            image.src = imageUrl;
            image.alt = '';
            image.addEventListener('error', () => image.remove());
            art.append(image);
        }
        const orderLabel = document.createElement('span');
        orderLabel.className = 'story-pile-order';
        orderLabel.textContent = `#${order}`;
        inner.append(costs, name, art);
        tile.append(inner);
        entry.append(tile, orderLabel);
        storyCardElementData.set(tile, card);
        return entry;
    }

    function createStoryTalentOverviewItem(relicKey, order, count = 1) {
        const key = String(relicKey || '');
        const definition = storyRelicDefinition(key);
        if (!definition) return null;
        const color = storyRelicRarityColor(definition);
        const item = document.createElement('div');
        item.className = 'story-talent-overview-item';
        item.style.setProperty('--story-relic-color', color);

        const marker = document.createElement('span');
        marker.className = 'story-talent-overview-marker';
        marker.textContent = '★';
        marker.setAttribute('aria-hidden', 'true');

        const copy = document.createElement('span');
        copy.className = 'story-talent-overview-copy';
        const name = document.createElement('strong');
        name.textContent = `${localize(definition.name)}${count > 1 ? ` ×${count}` : ''}`;
        const description = document.createElement('span');
        description.className = 'story-talent-overview-description';
        appendStoryRichText(description, localize(definition.description));
        copy.append(name, description);

        const index = document.createElement('span');
        index.className = 'story-talent-overview-order';
        index.textContent = String(order);
        item.append(marker, copy, index);
        return item;
    }

    function openStoryTalentOverview() {
        const state = activeRun?.state;
        if (!state) return;
        const relics = Array.isArray(state.player?.relics) ? state.player.relics : [];
        setText('story-pile-title', t.talentOverview);
        setText('story-pile-total', t.talentTotal(relics.length));
        const grid = $('story-pile-grid');
        grid?.replaceChildren();
        grid?.classList.add('is-talents');
        if (!relics.length) {
            const empty = document.createElement('div');
            empty.className = 'story-pile-empty';
            empty.textContent = t.noTalents;
            grid?.append(empty);
        } else {
            const groupedRelics = new Map();
            relics.forEach((relicKey) => {
                groupedRelics.set(relicKey, (groupedRelics.get(relicKey) || 0) + 1);
            });
            [...groupedRelics.entries()].forEach(([relicKey, count], index) => {
                const item = createStoryTalentOverviewItem(relicKey, index + 1, count);
                if (item) grid?.append(item);
            });
        }
        const dialog = $('story-pile-dialog');
        if (dialog) {
            dialog.dataset.pileKind = 'talents';
            dialog.showModal();
        }
    }

    function openStoryPile(kind) {
        const state = activeRun?.state;
        const combat = state?.combat;
        const config = {
            deck: { source: state?.player?.deck, title: t.runDeck, reverse: false },
            draw: { source: combat?.draw_pile, title: t.drawPile, reverse: true },
            discard: { source: combat?.discard_pile, title: t.discardPile, reverse: true },
            exile: { source: combat?.exile_pile, title: t.exilePile, reverse: true },
        }[kind];
        if (!config) return;
        if (kind !== 'deck' && !combat) return;
        const source = Array.isArray(config.source) ? config.source : [];
        const cards = config.reverse ? [...source].reverse() : [...source];
        setText('story-pile-title', config.title);
        setText('story-pile-total', t.pileTotal(config.title, cards.length));
        const grid = $('story-pile-grid');
        grid?.replaceChildren();
        grid?.classList.remove('is-talents');
        if (!cards.length) {
            const empty = document.createElement('div');
            empty.className = 'story-pile-empty';
            empty.textContent = t.pileEmpty;
            grid?.append(empty);
        } else {
            cards.forEach((card, index) => grid?.append(createStoryPileTile(card, index + 1)));
        }
        const dialog = $('story-pile-dialog');
        if (dialog) {
            dialog.dataset.pileKind = kind;
            dialog.showModal();
        }
    }

    function createStoryCard(card, options = {}) {
        const values = cardValues(card);
        const element = document.createElement(options.interactive === false ? 'article' : 'button');
        const cardType = values?.type || 'unknown';
        const blinded = options.blinded === true;
        element.className = `story-card card ${cardType}${options.compact ? ' is-compact' : ''}`;
        if (element.tagName === 'BUTTON') element.type = 'button';
        if (!values) {
            element.textContent = card?.def_id || '?';
            element.disabled = true;
            return element;
        }
        const rarityDefinition = storyCardRarityDefinition(values);
        element.style.setProperty(
            '--story-card-rarity-color',
            blinded ? '#7F8C8D' : rarityDefinition.color,
        );
        element.style.setProperty(
            '--story-card-type-color',
            blinded ? '#7F8C8D' : storyCardTypeColor(cardType),
        );
        if (blinded) {
            element.classList.add('card-blinded', 'card-blinded-deep');
            element.dataset.storyBlind = '1';
        }
        const displayName = blinded
            ? '?'
            : `${storyCardUpgradePrefix(card)}${localize(values.name)}`;
        const englishName = blinded || lang === 'en' ? '' : String(values.name?.en || '');
        const imageUrl = blinded ? '' : (card.upgraded
            ? (values.upgraded_image_url || values.image_url || '')
            : (values.image_url || ''));
        const enablePrediction = !blinded && options.enablePrediction === true;
        if (enablePrediction && cardType === 'thorn') {
            element.classList.add('card-effect-fit-prediction');
        }
        element.classList.add(englishName ? 'card-has-english' : 'card-no-english');
        element.classList.add(imageUrl ? 'card-has-art' : 'card-no-art');
        element.dataset.instanceId = String(card.instance_id || '');
        element.dataset.defId = String(card.def_id || '');
        storyCardElementData.set(element, card);

        const costs = document.createElement('div');
        costs.className = 'card-costs';
        const costE = document.createElement('span');
        costE.className = 'cost-e';
        costE.textContent = blinded ? '?' : String(values.cost_e ?? 0);
        const name = document.createElement('span');
        name.className = 'card-name';
        name.textContent = displayName;
        const costM = document.createElement('span');
        costM.className = 'cost-m';
        costM.textContent = blinded ? '?' : String(values.cost_m ?? 0);
        costs.append(costE, name, costM);
        element.append(costs);

        if (englishName) {
            const english = document.createElement('div');
            english.className = 'card-english-name';
            english.textContent = englishName;
            element.append(english);
        }
        if (imageUrl) {
            const art = document.createElement('div');
            art.className = 'card-art';
            const image = document.createElement('img');
            image.src = imageUrl;
            image.alt = '';
            image.decoding = 'async';
            image.addEventListener('error', () => art.classList.add('hidden'));
            art.append(image);
            element.append(art);
        }
        const typeWrap = document.createElement('div');
        typeWrap.className = 'card-type-label-wrap';
        const typeLabel = document.createElement('span');
        typeLabel.className = 'card-type-label';
        typeLabel.textContent = blinded ? '?' : (STORY_CARD_TYPE_LABELS[cardType] || cardType);
        typeWrap.append(typeLabel);
        const description = document.createElement('div');
        description.className = 'card-effect';
        appendStoryRichText(description, blinded ? '?' : localize(values.description));
        element.append(typeWrap, description);
        const bottom = blinded ? null : createStoryCardBottom(
            card,
            values,
            options.predictionTargetId,
            enablePrediction,
        );
        if (bottom) element.append(bottom);
        if (options.note) {
            const note = document.createElement('span');
            note.className = 'story-card-note';
            note.textContent = options.note;
            element.append(note);
        }
        if (options.disabled) element.disabled = true;
        if (typeof options.onClick === 'function') element.addEventListener('click', options.onClick);
        if (!blinded && options.previewUpgradeOnHover && storyCardIsUpgradable(card)) {
            let pointerPreview = false;
            let focusPreview = false;
            let previewing = false;
            const renderPreview = () => {
                const shouldPreview = pointerPreview || focusPreview;
                if (shouldPreview === previewing) return;
                previewing = shouldPreview;
                const displayCard = storyCardAtUpgradeState(card, shouldPreview);
                const visual = createStoryCard(displayCard, {
                    ...options,
                    interactive: false,
                    onClick: undefined,
                    previewUpgradeOnHover: false,
                });
                element.replaceChildren(...visual.childNodes);
                element.dataset.previewUpgraded = shouldPreview ? '1' : '0';
                storyCardElementData.set(element, displayCard);
                scheduleStoryCardEffectFit(element);
            };
            element.addEventListener('pointerenter', () => {
                pointerPreview = true;
                renderPreview();
            });
            element.addEventListener('pointerleave', () => {
                pointerPreview = false;
                renderPreview();
            });
            element.addEventListener('focus', () => {
                focusPreview = true;
                renderPreview();
            });
            element.addEventListener('blur', () => {
                focusPreview = false;
                renderPreview();
            });
        }
        scheduleStoryCardEffectFit(element);
        return element;
    }

    function storyCardTermKey(card) {
        return [
            String(card?.instance_id || ''),
            String(card?.def_id || ''),
            card?.upgraded ? '1' : '0',
        ].join(':');
    }

    function collectStoryStatusIds(value, result) {
        if (Array.isArray(value)) {
            value.forEach((item) => collectStoryStatusIds(item, result));
            return;
        }
        if (!value || typeof value !== 'object') return;
        if (typeof value.status === 'string' && storyContent?.statuses?.[value.status]) {
            result.add(value.status);
        }
        Object.values(value).forEach((item) => collectStoryStatusIds(item, result));
    }

    function storyCardTermItems(card) {
        const values = cardValues(card);
        if (!values) return [];
        const items = [];
        const seen = new Set();
        const add = (kind, id, definition) => {
            const key = `${kind}:${id}`;
            if (!definition || seen.has(key)) return;
            seen.add(key);
            items.push({ kind, id, definition });
        };
        (values.tags || []).forEach((tagId) => {
            add('tag', tagId, storyContent?.tags?.[tagId]);
        });
        if (Number(card?.modifiers?.charge) > 0) {
            add('tag', 'charge', storyContent?.tags?.charge);
        }

        const statusIds = new Set();
        collectStoryStatusIds(values.effects, statusIds);
        const description = localize(values.description);
        Object.entries(storyContent?.statuses || {}).forEach(([statusId, definition]) => {
            const names = Object.values(definition?.name || {})
                .map((name) => String(name || '').trim())
                .filter(Boolean);
            if (names.some((name) => description.includes(name))) statusIds.add(statusId);
        });
        statusIds.forEach((statusId) => {
            add('status', statusId, storyContent?.statuses?.[statusId]);
        });

        Object.entries(STORY_RESOURCE_TERMS).forEach(([unit, definition]) => {
            const markerPattern = new RegExp(`\\[\\[icon:${unit}\\]\\]`, 'i');
            const unitPattern = new RegExp(`\\d+(?:\\.\\d+)?(?:\\s*[×xX*]\\s*\\d+)?\\s*${unit}(?![A-Za-z])`, 'i');
            if (markerPattern.test(description) || unitPattern.test(description)) {
                add('resource', unit, definition);
            }
        });
        return items;
    }

    function appendStoryTermRow(container, item) {
        const row = document.createElement('section');
        row.className = `story-term-row story-term-row-${item.kind}`;
        const heading = document.createElement('h3');
        if (item.kind === 'tag') {
            const badge = storyTagElement(item.id);
            if (badge) heading.append(badge);
        } else if (item.kind === 'resource') {
            const badge = document.createElement('span');
            badge.className = `story-term-resource story-inline-token-${item.id.toLowerCase()}`;
            badge.append(createStoryInlineIcon(item.id));
            const name = document.createElement('span');
            name.textContent = localize(item.definition.name);
            badge.append(name);
            heading.append(badge);
        } else if (item.kind === 'relic') {
            const badge = document.createElement('span');
            const color = storyRelicRarityColor(item.definition);
            row.style.setProperty('--story-relic-color', color);
            badge.className = 'story-term-relic';
            badge.style.setProperty('--story-relic-color', color);
            badge.textContent = localize(item.definition.name);
            heading.append(badge);
        } else {
            const badge = document.createElement('span');
            badge.className = 'story-term-status';
            const icon = document.createElement('img');
            icon.src = item.kind === 'trait'
                ? storyTraitIconUrl(item.id)
                : storyStatusIconUrl(item.id);
            icon.alt = '';
            icon.setAttribute('aria-hidden', 'true');
            const name = document.createElement('span');
            name.textContent = localize(item.definition.name);
            badge.append(icon, name);
            heading.append(badge);
        }
        const description = document.createElement('p');
        appendStoryRichText(description, localize(item.definition.description));
        row.append(heading, description);
        container.append(row);
    }

    function closeStoryOverlayModal() {
        const modal = $('modal');
        if (!modal) return;
        modal.classList.remove('shortcut-help-active', 'active');
        modal.classList.add('hidden');
        modal.setAttribute('aria-hidden', 'true');
    }

    function closeStoryCardTerms() {
        const dialog = $('story-term-dialog');
        if (!dialog) return;
        if (dialog.open) dialog.close();
        delete dialog.dataset.storyTermKey;
        delete dialog.dataset.storyTermUpgrade;
    }

    function storyStatusDefinition(statusKey) {
        return storyContent?.statuses?.[String(statusKey || '')] || null;
    }

    function storyStatusIconUrl(statusKey) {
        const key = String(statusKey || '');
        const imageUrl = String(storyStatusDefinition(key)?.image_url || '').trim();
        if (imageUrl) return imageUrl;
        return `/static/assets/status-icons/${STORY_STATUS_ICONS[key] || key}.svg`;
    }

    function storyTraitDefinition(traitKey) {
        return storyContent?.traits?.[String(traitKey || '')] || null;
    }

    function storyTraitIconUrl(traitKey) {
        return String(storyTraitDefinition(traitKey)?.image_url || '').trim();
    }

    const STORY_TRAIT_VALUE_KEYS_FALLBACK = Object.freeze({
        sturdy: 'sturdy',
        shelter: 'shelter',
        hidden: 'hidden',
        turn_shield: 'turn_shield',
        charging_up: 'charging',
        charged: 'charged',
        frenzied: 'frenzy',
        vampire: 'vampire',
        limb_survival: 'regenerations',
        bandage: 'bandage',
        miracle: 'miracle',
        psionic_connection: 'psionic_connection',
        psionic_sustain: 'psionic_sustain',
        endurance_shell: 'endurance_shell',
        bulb: 'bulb',
        hard_shell: 'hard_shell',
        segments: 'segments',
        magic_shield: 'magic_shield',
        magic_blessing: 'magic',
        magic_reflection: 'magic_reflection',
        electric_web: 'electric_web',
        super_beam: 'super_beam',
        toxic_reflection: 'toxic_reflection',
        disc: 'disc',
    });

    function storyTraitValueKeys() {
        const configured = storyContent?.trait_value_keys;
        return configured && typeof configured === 'object'
            ? configured
            : STORY_TRAIT_VALUE_KEYS_FALLBACK;
    }

    function storyTraitKeyForEffectKey(effectKey) {
        const expected = String(effectKey || '');
        return Object.entries(storyTraitValueKeys()).find(
            ([, valueKey]) => String(valueKey || '') === expected,
        )?.[0] || '';
    }

    function storyRelicDefinition(relicKey) {
        return storyContent?.relics?.[String(relicKey || '')] || null;
    }

    function storyRelicRarityColor(definition) {
        const rarity = String(definition?.rarity || 'common');
        return String(
            storyContent?.rarities?.[rarity]?.color
            || (rarity === 'special' ? '#D4AC0D' : '#FFE65D'),
        );
    }

    function storyCardRarityDefinition(definition) {
        const rarityId = String(definition?.rarity || 'special');
        const fallback = rarityId === 'special'
            ? { name: { zh: '特殊', en: 'Special' }, color: '#D4AC0D' }
            : { name: { zh: rarityId, en: rarityId }, color: '#FFE65D' };
        return {
            id: rarityId,
            ...(storyContent?.rarities?.[rarityId] || fallback),
        };
    }

    function openStoryStatusTerms(statusKey) {
        removeStoryCardHoverPreview();
        const key = String(statusKey || '');
        const definition = storyStatusDefinition(key);
        const dialog = $('story-term-dialog');
        const content = $('story-term-content');
        if (!key || !definition || !dialog || !content) return false;
        const termKey = `status:${key}`;
        if (dialog.open && dialog.dataset.storyTermKey === termKey) {
            closeStoryCardTerms();
            return true;
        }

        content.className = 'modal-inner story-card-terms-modal story-status-terms-modal';
        content.replaceChildren();

        const close = document.createElement('button');
        close.type = 'button';
        close.className = 'story-term-close';
        close.setAttribute('aria-label', t.close);
        close.textContent = '×';
        close.addEventListener('click', closeStoryCardTerms);

        const layout = document.createElement('div');
        layout.className = 'story-status-terms-layout';
        const iconWrap = document.createElement('div');
        iconWrap.className = 'story-status-terms-icon';
        const icon = document.createElement('img');
        icon.src = storyStatusIconUrl(key);
        icon.alt = '';
        icon.setAttribute('aria-hidden', 'true');
        const iconName = document.createElement('span');
        iconName.className = 'story-status-terms-name';
        iconName.textContent = localize(definition.name);
        iconWrap.append(icon, iconName);

        const copy = document.createElement('div');
        copy.className = 'story-status-terms-copy';
        const title = document.createElement('h2');
        title.textContent = definition.category === 'action'
            ? (t.actionTerms || (lang === 'zh' ? '行动说明' : 'Action Details'))
            : t.statusTerms;
        const terms = document.createElement('div');
        terms.className = 'story-card-terms-list';
        appendStoryTermRow(terms, {
            kind: 'status',
            id: key,
            definition,
        });
        copy.append(title, terms);
        layout.append(iconWrap, copy);
        content.append(close, layout);

        dialog.dataset.storyTermKey = termKey;
        delete dialog.dataset.storyTermUpgrade;
        if (!dialog.open) dialog.showModal();
        return true;
    }

    function attachStoryStatusTermAccess(element, statusKey) {
        if (!element || !storyStatusDefinition(statusKey)) return;
        element.dataset.storyStatusKey = String(statusKey);
        element.setAttribute('role', 'button');
        element.tabIndex = 0;
        let timer = 0;
        let start = null;
        const cancel = () => {
            if (timer) window.clearTimeout(timer);
            timer = 0;
            start = null;
        };
        element.addEventListener('pointerdown', (event) => {
            if (event.button != null && event.button !== 0) return;
            cancel();
            start = { x: event.clientX, y: event.clientY };
            timer = window.setTimeout(() => {
                timer = 0;
                start = null;
                if (selectedCombatCardId && activeRun?.state) {
                    cancelStoryCombatSelection(true);
                    return;
                }
                element.dataset.storyTermLongPress = '1';
                window.setTimeout(() => {
                    delete element.dataset.storyTermLongPress;
                }, 1200);
                openStoryStatusTerms(statusKey);
            }, STORY_TERM_LONG_PRESS_MS);
        });
        element.addEventListener('pointermove', (event) => {
            if (!timer || !start) return;
            if (Math.hypot(event.clientX - start.x, event.clientY - start.y) > STORY_TERM_MOVE_CANCEL_PX) {
                cancel();
            }
        });
        ['pointerup', 'pointercancel', 'pointerleave', 'lostpointercapture'].forEach((eventName) => {
            element.addEventListener(eventName, cancel);
        });
        element.addEventListener('keydown', (event) => {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            event.preventDefault();
            event.stopPropagation();
            openStoryStatusTerms(statusKey);
        });
    }

    function openStoryTraitTerms(traitKey) {
        removeStoryCardHoverPreview();
        const key = String(traitKey || '');
        const definition = storyTraitDefinition(key);
        const dialog = $('story-term-dialog');
        const content = $('story-term-content');
        if (!key || !definition || !dialog || !content) return false;
        const termKey = `trait:${key}`;
        if (dialog.open && dialog.dataset.storyTermKey === termKey) {
            closeStoryCardTerms();
            return true;
        }

        content.className = 'modal-inner story-card-terms-modal story-status-terms-modal';
        content.replaceChildren();

        const close = document.createElement('button');
        close.type = 'button';
        close.className = 'story-term-close';
        close.setAttribute('aria-label', t.close);
        close.textContent = '×';
        close.addEventListener('click', closeStoryCardTerms);

        const layout = document.createElement('div');
        layout.className = 'story-status-terms-layout';
        const iconWrap = document.createElement('div');
        iconWrap.className = 'story-status-terms-icon';
        const icon = document.createElement('img');
        icon.src = storyTraitIconUrl(key);
        icon.alt = '';
        icon.setAttribute('aria-hidden', 'true');
        const iconName = document.createElement('span');
        iconName.className = 'story-status-terms-name';
        iconName.textContent = localize(definition.name);
        iconWrap.append(icon, iconName);

        const copy = document.createElement('div');
        copy.className = 'story-status-terms-copy';
        const title = document.createElement('h2');
        title.textContent = t.traitTerms;
        const terms = document.createElement('div');
        terms.className = 'story-card-terms-list';
        appendStoryTermRow(terms, {
            kind: 'trait',
            id: key,
            definition,
        });
        copy.append(title, terms);
        layout.append(iconWrap, copy);
        content.append(close, layout);

        dialog.dataset.storyTermKey = termKey;
        delete dialog.dataset.storyTermUpgrade;
        if (!dialog.open) dialog.showModal();
        return true;
    }

    function attachStoryTraitTermAccess(element, traitKey) {
        if (!element || !storyTraitDefinition(traitKey)) return;
        element.dataset.storyTraitKey = String(traitKey);
        element.setAttribute('role', 'button');
        element.tabIndex = 0;
        let timer = 0;
        let start = null;
        const cancel = () => {
            if (timer) window.clearTimeout(timer);
            timer = 0;
            start = null;
        };
        element.addEventListener('pointerdown', (event) => {
            if (event.button != null && event.button !== 0) return;
            cancel();
            start = { x: event.clientX, y: event.clientY };
            timer = window.setTimeout(() => {
                timer = 0;
                start = null;
                if (selectedCombatCardId && activeRun?.state) {
                    cancelStoryCombatSelection(true);
                    return;
                }
                element.dataset.storyTermLongPress = '1';
                window.setTimeout(() => {
                    delete element.dataset.storyTermLongPress;
                }, 1200);
                openStoryTraitTerms(traitKey);
            }, STORY_TERM_LONG_PRESS_MS);
        });
        element.addEventListener('pointermove', (event) => {
            if (!timer || !start) return;
            if (Math.hypot(event.clientX - start.x, event.clientY - start.y) > STORY_TERM_MOVE_CANCEL_PX) {
                cancel();
            }
        });
        ['pointerup', 'pointercancel', 'pointerleave', 'lostpointercapture'].forEach((eventName) => {
            element.addEventListener(eventName, cancel);
        });
        element.addEventListener('keydown', (event) => {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            event.preventDefault();
            event.stopPropagation();
            openStoryTraitTerms(traitKey);
        });
    }

    function openStoryCardTerms(card, options = {}) {
        removeStoryCardHoverPreview();
        const dialog = $('story-term-dialog');
        const content = $('story-term-content');
        if (!cardValues(card) || !dialog || !content) return;
        const termKey = storyCardTermKey(card);
        if (
            dialog.open
            && dialog.dataset.storyTermKey === termKey
        ) {
            closeStoryCardTerms();
            return;
        }

        const hasUpgrade = storyCardHasUpgrade(card);
        const requestedStates = Array.isArray(options.allowedUpgradeStates)
            ? options.allowedUpgradeStates.map(Boolean)
            : null;
        const availableStates = hasUpgrade
            ? [...new Set(requestedStates?.length ? requestedStates : [false, true])]
            : [false];
        const initialState = availableStates.includes(Boolean(card.upgraded))
            ? Boolean(card.upgraded)
            : availableStates[0];
        const renderVersion = (upgraded) => {
            const requestedUpgrade = hasUpgrade && Boolean(upgraded);
            const showUpgraded = availableStates.includes(requestedUpgrade)
                ? requestedUpgrade
                : availableStates[0];
            const displayCard = storyCardAtUpgradeState(card, showUpgraded);
            const values = cardValues(displayCard);
            content.className = 'modal-inner story-card-terms-modal';
            content.replaceChildren();

            const close = document.createElement('button');
            close.type = 'button';
            close.className = 'story-term-close';
            close.setAttribute('aria-label', t.close);
            close.textContent = '×';
            close.addEventListener('click', closeStoryCardTerms);

            const layout = document.createElement('div');
            layout.className = 'story-card-terms-layout';
            const preview = document.createElement('div');
            preview.className = 'story-card-terms-preview';
            preview.append(createStoryCard(displayCard, {
                interactive: false,
                predictionTargetId: '',
            }));

            const copy = document.createElement('div');
            copy.className = 'story-card-terms-copy';
            const title = document.createElement('h2');
            title.textContent = `${showUpgraded ? '+' : ''}${localize(values.name)}`;
            const rarityDefinition = storyCardRarityDefinition(values);
            const rarity = document.createElement('span');
            rarity.className = 'story-card-terms-rarity';
            rarity.style.setProperty('--story-card-rarity', rarityDefinition.color);
            rarity.textContent = `${t.codexRarity} · ${localize(rarityDefinition.name) || rarityDefinition.id}`;
            copy.append(title, rarity);

            if (availableStates.length > 1) {
                const tabs = document.createElement('div');
                tabs.className = 'story-card-version-tabs';
                tabs.setAttribute('role', 'tablist');
                [
                    { upgraded: false, label: t.beforeUpgrade },
                    { upgraded: true, label: t.afterUpgrade },
                ].filter((version) => availableStates.includes(version.upgraded)).forEach((version) => {
                    const active = version.upgraded === showUpgraded;
                    const tab = document.createElement('button');
                    tab.type = 'button';
                    tab.className = `story-card-version-tab${active ? ' is-active' : ''}`;
                    tab.dataset.storyUpgradeState = version.upgraded ? '1' : '0';
                    tab.setAttribute('role', 'tab');
                    tab.setAttribute('aria-selected', active ? 'true' : 'false');
                    tab.tabIndex = active ? 0 : -1;
                    tab.textContent = version.label;
                    tab.addEventListener('click', () => renderVersion(version.upgraded));
                    tab.addEventListener('keydown', (event) => {
                        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
                        event.preventDefault();
                        const nextUpgraded = event.key === 'ArrowRight' || event.key === 'End';
                        renderVersion(nextUpgraded);
                        requestAnimationFrame(() => {
                            content.querySelector(
                                `[data-story-upgrade-state="${nextUpgraded ? '1' : '0'}"]`,
                            )?.focus();
                        });
                    });
                    tabs.append(tab);
                });
                copy.append(tabs);
            }

            const effect = document.createElement('p');
            effect.className = 'story-card-terms-effect';
            appendStoryRichText(effect, localize(values.description));
            const flavorText = localize(values.flavor).trim();
            const flavor = flavorText ? document.createElement('p') : null;
            if (flavor) {
                flavor.className = 'story-card-terms-flavor';
                flavor.textContent = flavorText;
            }
            const termTitle = document.createElement('h3');
            termTitle.className = 'story-card-terms-heading';
            termTitle.textContent = t.cardTerms;
            const terms = document.createElement('div');
            terms.className = 'story-card-terms-list';
            const termItems = storyCardTermItems(displayCard);
            if (termItems.length) {
                termItems.forEach((item) => appendStoryTermRow(terms, item));
            } else {
                const empty = document.createElement('p');
                empty.className = 'story-card-terms-empty';
                empty.textContent = t.noCardTerms;
                terms.append(empty);
            }
            copy.append(effect);
            if (flavor) copy.append(flavor);
            copy.append(termTitle, terms);
            layout.append(preview, copy);
            content.append(close, layout);
            dialog.dataset.storyTermUpgrade = showUpgraded ? '1' : '0';
            scheduleStoryCardEffectFit(preview.querySelector('.story-card.card'));
        };

        dialog.dataset.storyTermKey = termKey;
        if (availableStates.includes(Boolean(card.upgraded))) {
            renderVersion(Boolean(card.upgraded));
        } else {
            renderVersion(initialState);
        }
        if (!dialog.open) dialog.showModal();
    }

    function storyDiscoveryKey(discovery) {
        return [
            String(discovery?.content_type || '').toLowerCase(),
            String(discovery?.content_id || ''),
            String(discovery?.variant || 'base').toLowerCase(),
        ].join(':');
    }

    function storyDiscoveryLabel(discovery) {
        const contentType = String(discovery?.content_type || '');
        const contentId = String(discovery?.content_id || '');
        if (contentType === 'card') return localize(storyContent?.cards?.[contentId]?.name) || contentId;
        if (contentType === 'enemy') return localize(storyContent?.enemies?.[contentId]?.name) || contentId;
        if (contentType === 'relic') return localize(storyContent?.relics?.[contentId]?.name) || contentId;
        if (contentType === 'blessing') {
            return localize(storyContent?.blessings?.[contentId]?.name)
                || localize(storyContent?.blessings?.[contentId]?.description)
                || t.codexUnknownTalent;
        }
        if (contentType === 'term') {
            const [kind, ...rest] = contentId.split(':');
            const termId = rest.join(':');
            const definition = storyCodexTermDefinition(kind, termId);
            return localize(definition?.name) || termId;
        }
        return contentId;
    }

    function updateStoryCodexBadge() {
        const badge = $('story-codex-badge');
        if (!badge) return;
        const unread = storyDiscoveries.filter((item) => !item.viewed_at).length;
        badge.textContent = unread > 99 ? '99+' : String(unread);
        badge.classList.toggle('hidden', unread <= 0);
        badge.setAttribute('aria-hidden', unread > 0 ? 'false' : 'true');
    }

    function mergeStoryDiscoveries(items, options = {}) {
        const incoming = Array.isArray(items) ? items : [];
        if (!incoming.length) return [];
        const byKey = new Map(storyDiscoveries.map((item) => [storyDiscoveryKey(item), item]));
        const added = [];
        incoming.forEach((raw) => {
            if (!raw || typeof raw !== 'object') return;
            const normalized = {
                ...raw,
                content_type: String(raw.content_type || '').toLowerCase(),
                content_id: String(raw.content_id || ''),
                variant: String(raw.variant || 'base').toLowerCase(),
            };
            if (!normalized.content_type || !normalized.content_id) return;
            const key = storyDiscoveryKey(normalized);
            const existing = byKey.get(key);
            if (!existing) {
                byKey.set(key, normalized);
                added.push(normalized);
                return;
            }
            byKey.set(key, {
                ...existing,
                ...normalized,
                viewed_at: normalized.viewed_at || existing.viewed_at || null,
            });
        });
        storyDiscoveries = [...byKey.values()].sort((left, right) => (
            String(left.first_seen_at || '').localeCompare(String(right.first_seen_at || ''))
            || storyDiscoveryKey(left).localeCompare(storyDiscoveryKey(right))
        ));
        updateStoryCodexBadge();
        if ($('story-codex-dialog')?.open) renderStoryCodex();
        if (options.notify && added.length) {
            const message = added.length === 1
                ? `${t.codexNew}：${storyDiscoveryLabel(added[0])}`
                : t.codexNewCount(added.length);
            showToast(message);
        }
        return added;
    }

    function ingestStoryDiscoveryPayload(payload, options = {}) {
        if (!payload || typeof payload !== 'object') return;
        const newItems = Array.isArray(payload.new_discoveries) ? payload.new_discoveries : [];
        if (newItems.length) mergeStoryDiscoveries(newItems, { notify: Boolean(options.notify) });
        mergeStoryDiscoveries(payload.discoveries, { notify: false });
    }

    function storyCodexDiscoveredIds(contentType) {
        return new Set(
            storyDiscoveries
                .filter((item) => item.content_type === contentType)
                .map((item) => item.content_id),
        );
    }

    function storyCodexSearchMatches(id, definition, extra = '') {
        const query = storyCodexSearch.trim().toLocaleLowerCase();
        if (!query) return true;
        const values = [id, extra];
        ['name', 'description', 'flavor'].forEach((field) => {
            const value = definition?.[field];
            if (value && typeof value === 'object') values.push(...Object.values(value));
            else values.push(value);
        });
        return values.some((value) => String(value || '').toLocaleLowerCase().includes(query));
    }

    function storyCodexCardRecords() {
        const records = new Map();
        storyDiscoveries.forEach((item) => {
            if (item.content_type !== 'card' || !storyContent?.cards?.[item.content_id]) return;
            if (!records.has(item.content_id)) {
                records.set(item.content_id, {
                    id: item.content_id,
                    definition: storyContent.cards[item.content_id],
                    variants: new Set(),
                });
            }
            records.get(item.content_id).variants.add(item.variant === 'upgraded' ? 'upgraded' : 'base');
        });
        const typeOrder = Object.keys(storyContent?.card_types || {});
        return [...records.values()].sort((left, right) => {
            const leftRarity = STORY_RARITY_ORDER.indexOf(String(left.definition.rarity || 'common'));
            const rightRarity = STORY_RARITY_ORDER.indexOf(String(right.definition.rarity || 'common'));
            const rarityCompare = (leftRarity < 0 ? 999 : leftRarity) - (rightRarity < 0 ? 999 : rightRarity);
            if (rarityCompare) return rarityCompare;
            const typeCompare = typeOrder.indexOf(left.definition.type) - typeOrder.indexOf(right.definition.type);
            if (typeCompare) return typeCompare;
            return localize(left.definition.name).localeCompare(localize(right.definition.name), lang);
        });
    }

    function storyCodexFilterActions(onAll, onClear) {
        const actions = document.createElement('div');
        actions.className = 'story-codex-filter-actions';
        [
            { label: t.codexAll, action: onAll },
            { label: t.codexClear, action: onClear },
        ].forEach((config) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'story-codex-filter-action';
            button.textContent = config.label;
            button.addEventListener('click', config.action);
            actions.append(button);
        });
        return actions;
    }

    function storyCodexFilterOption(key, definition, count, selectedSet, onChange, options = {}) {
        const label = document.createElement('label');
        label.className = `story-codex-filter-option${selectedSet.has(key) ? ' is-active' : ''}`;
        if (options.color) label.style.setProperty('--story-filter-color', options.color);
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = selectedSet.has(key);
        const name = document.createElement('span');
        name.textContent = localize(definition?.name) || String(options.fallback || key);
        const total = document.createElement('small');
        total.textContent = String(count);
        checkbox.addEventListener('change', () => {
            if (checkbox.checked) selectedSet.add(key);
            else selectedSet.delete(key);
            onChange();
        });
        label.append(checkbox, name, total);
        return label;
    }

    function ensureStoryCodexCardFilters(records) {
        if (storyCodexCardFiltersReady) return;
        Object.keys(storyContent?.rarities || {}).forEach((key) => storyCodexRarities.add(key));
        Object.keys(storyContent?.card_types || {}).forEach((key) => storyCodexTypes.add(key));
        records.forEach((record) => {
            storyCodexRarities.add(String(record.definition.rarity || 'common'));
            storyCodexTypes.add(String(record.definition.type || ''));
        });
        storyCodexCardFiltersReady = true;
    }

    function renderStoryCodexCards(sidebar, detail) {
        const records = storyCodexCardRecords();
        ensureStoryCodexCardFilters(records);
        const rarityCounts = new Map();
        const typeCounts = new Map();
        records.forEach((record) => {
            const rarity = String(record.definition.rarity || 'common');
            const type = String(record.definition.type || '');
            rarityCounts.set(rarity, (rarityCounts.get(rarity) || 0) + 1);
            typeCounts.set(type, (typeCounts.get(type) || 0) + 1);
        });

        const rarityTitle = document.createElement('strong');
        rarityTitle.className = 'story-codex-filter-title';
        rarityTitle.textContent = t.codexRarity;
        sidebar.append(rarityTitle, storyCodexFilterActions(
            () => {
                rarityCounts.forEach((_, key) => storyCodexRarities.add(key));
                renderStoryCodex();
            },
            () => {
                storyCodexRarities.clear();
                renderStoryCodex();
            },
        ));
        const rarityOptions = document.createElement('div');
        rarityOptions.className = 'story-codex-filter-options';
        rarityOptions.dataset.storyScrollKey = 'codex-card-rarity-options';
        [...rarityCounts.entries()].sort(([left], [right]) => {
            const leftIndex = STORY_RARITY_ORDER.indexOf(left);
            const rightIndex = STORY_RARITY_ORDER.indexOf(right);
            const orderCompare = (leftIndex < 0 ? 999 : leftIndex) - (rightIndex < 0 ? 999 : rightIndex);
            return orderCompare || left.localeCompare(right);
        }).forEach(([key, count]) => {
            const definition = storyContent?.rarities?.[key] || {
                name: { zh: '特殊', en: 'Special' },
                color: '#D4AC0D',
            };
            rarityOptions.append(storyCodexFilterOption(
                key,
                definition,
                count,
                storyCodexRarities,
                renderStoryCodex,
                { color: definition.color },
            ));
        });
        sidebar.append(rarityOptions);

        const shell = document.createElement('div');
        shell.className = 'story-codex-card-shell';
        const main = document.createElement('div');
        main.className = 'story-codex-card-main';
        const resultCount = document.createElement('div');
        resultCount.className = 'story-codex-result-count';
        const grid = document.createElement('div');
        grid.className = 'story-codex-card-grid';
        grid.dataset.storyScrollKey = 'codex-card-grid';
        const typeSidebar = document.createElement('aside');
        typeSidebar.className = 'story-codex-type-filter';
        const typeTitle = document.createElement('strong');
        typeTitle.className = 'story-codex-filter-title';
        typeTitle.textContent = t.codexType;
        typeSidebar.append(typeTitle, storyCodexFilterActions(
            () => {
                typeCounts.forEach((_, key) => storyCodexTypes.add(key));
                renderStoryCodex();
            },
            () => {
                storyCodexTypes.clear();
                renderStoryCodex();
            },
        ));
        const typeOptions = document.createElement('div');
        typeOptions.className = 'story-codex-filter-options';
        typeOptions.dataset.storyScrollKey = 'codex-card-type-options';
        typeCounts.forEach((count, key) => {
            const definition = storyContent?.card_types?.[key] || { name: { en: key } };
            typeOptions.append(storyCodexFilterOption(
                key,
                definition,
                count,
                storyCodexTypes,
                renderStoryCodex,
                { color: definition.color || `var(--${key})` },
            ));
        });
        typeSidebar.append(typeOptions);

        const visible = records.filter((record) => (
            storyCodexRarities.has(String(record.definition.rarity || 'common'))
            && storyCodexTypes.has(String(record.definition.type || ''))
            && storyCodexSearchMatches(record.id, record.definition)
        ));
        resultCount.textContent = t.codexResults(visible.length);
        visible.forEach((record) => {
            const upgraded = !record.variants.has('base') && record.variants.has('upgraded');
            const card = {
                instance_id: `codex:${record.id}:${upgraded ? 'upgraded' : 'base'}`,
                def_id: record.id,
                upgraded,
            };
            const allowedUpgradeStates = [
                ...(record.variants.has('base') ? [false] : []),
                ...(record.variants.has('upgraded') ? [true] : []),
            ];
            const cardElement = createStoryCard(card, {
                onClick: () => openStoryCardTerms(card, { allowedUpgradeStates }),
            });
            cardElement.classList.add('story-codex-card-tile');
            storyCardTermOptions.set(cardElement, { allowedUpgradeStates });
            grid.append(cardElement);
        });
        if (!visible.length) grid.append(storyCodexEmpty());
        main.append(resultCount, grid);
        shell.append(main, typeSidebar);
        detail.append(shell);
    }

    function storyCodexEnemyRecords() {
        const records = new Map();
        storyDiscoveries.forEach((item) => {
            if (item.content_type !== 'enemy' || !storyContent?.enemies?.[item.content_id]) return;
            if (!records.has(item.content_id)) {
                records.set(item.content_id, {
                    id: item.content_id,
                    definition: storyContent.enemies[item.content_id],
                    intents: new Set(),
                });
            }
            if (item.variant.startsWith('intent:')) {
                const index = Number(item.variant.slice(7));
                if (Number.isInteger(index) && index >= 0) records.get(item.content_id).intents.add(index);
            }
        });
        return [...records.values()].sort((left, right) => (
            localize(left.definition.name).localeCompare(localize(right.definition.name), lang)
        ));
    }

    function storyCodexIntentFromEffect(effect) {
        const type = String(effect?.type || '');
        const amount = Math.max(0, Number(effect?.amount) || 0);
        const hits = Math.max(1, Number(effect?.hits) || 1);
        if (type === 'damage') return { kind: 'attack', amount, hits, target: 'player' };
        if (type === 'self_damage') return { kind: 'self_damage', amount, hits, target: 'self' };
        if (type === 'gain_power') return { kind: 'buff', stat: 'power', amount, target: 'self' };
        if (type === 'gain_shield') return { kind: 'defend', stat: 'shield', amount, target: 'self' };
        if (type === 'gain_status') return { kind: 'status', status: effect.status, amount, target: 'self' };
        if (type === 'clear_status') return { kind: 'clear_status', status: effect.status, target: 'self' };
        if (['gain_charged', 'gain_charging', 'gain_frenzy', 'gain_hidden', 'gain_sturdy'].includes(type)) {
            const status = {
                gain_charged: 'charged', gain_charging: 'charging', gain_frenzy: 'frenzy',
                gain_hidden: 'hidden', gain_sturdy: 'sturdy',
            }[type];
            return { kind: 'status', status, amount, target: 'self' };
        }
        if (type === 'player_status' || type === 'delayed_player_status') {
            return {
                kind: 'status', status: effect.status, amount, target: 'player',
                delayed: type === 'delayed_player_status',
            };
        }
        if (type === 'self_heal') return { kind: 'heal', amount, target: 'self' };
        if (type === 'heal_to_full') return { kind: 'heal', full: true, target: 'self' };
        if (type === 'allies_heal') return { kind: 'heal', amount, target: 'all_enemies' };
        if (type === 'allies_power') return { kind: 'buff', stat: 'power', amount, target: 'all_enemies' };
        if (type === 'allies_shield' || type === 'lowest_ally_shield' || type === 'adjacent_shield') {
            return { kind: 'defend', stat: 'shield', amount, target: type === 'allies_shield' ? 'all_enemies' : type };
        }
        if (type.startsWith('summon')) {
            const enemyId = String(effect.enemy_id || (type === 'summon_wreckage' ? 'wreckage' : ''));
            return {
                kind: 'summon', enemy_id: enemyId,
                enemy_name: storyContent?.enemies?.[enemyId]?.name,
                amount: amount || 1, target: 'self',
            };
        }
        if (type === 'add_draw_card' || type === 'delayed_hand_charge') {
            return { kind: 'card', effect_type: type, amount: amount || 1, target: 'player' };
        }
        if (type === 'consume_allies') return { kind: 'consume', target: 'all_enemies' };
        if (type === 'stun_if_player_shield') {
            return { kind: 'status', status: 'stun', amount: 1, target: 'player', conditional: 'shield' };
        }
        if (type === 'consume_pearls_damage' || type === 'lose_max_health_percent') {
            return { kind: 'special', effect_type: type, amount, target: type === 'lose_max_health_percent' ? 'self' : 'player' };
        }
        if (type === 'self_kill') return { kind: 'self_damage', target: 'self', lethal: true };
        return { kind: 'special', effect_type: type, amount };
    }

    function renderStoryCodexEnemyDetail(record, detail) {
        const definition = record?.definition;
        if (!definition) {
            detail.append(storyCodexEmpty());
            return;
        }
        const layout = document.createElement('article');
        layout.className = 'story-codex-enemy-detail';
        const portrait = document.createElement('div');
        portrait.className = 'story-codex-enemy-portrait';
        if (definition.image_url) {
            const image = document.createElement('img');
            image.src = definition.image_url;
            image.alt = '';
            portrait.append(image);
        } else {
            portrait.textContent = '?';
        }
        const copy = document.createElement('div');
        copy.className = 'story-codex-enemy-copy';
        const name = document.createElement('h3');
        name.textContent = localize(definition.name) || record.id;
        const health = document.createElement('p');
        const normalHealth = Number(definition.max_health || 0);
        const lunaticHealth = Number(definition.lunatic_max_health || normalHealth);
        health.className = 'story-codex-enemy-health';
        health.textContent = `${t.codexHealth}：${normalHealth}${lunaticHealth !== normalHealth ? ` / ${lunaticHealth}` : ''}H`;
        copy.append(name, health);
        if ((definition.traits || []).length) {
            const traits = document.createElement('div');
            traits.className = 'story-codex-enemy-traits';
            definition.traits.forEach((traitId) => {
                const traitDefinition = storyTraitDefinition(traitId);
                if (!traitDefinition) return;
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'story-codex-trait';
                const icon = document.createElement('img');
                icon.src = storyTraitIconUrl(traitId);
                icon.alt = '';
                const label = document.createElement('span');
                label.textContent = localize(traitDefinition.name);
                button.append(icon, label);
                attachStoryTraitTermAccess(button, traitId);
                button.addEventListener('click', () => openStoryTraitTerms(traitId));
                traits.append(button);
            });
            copy.append(traits);
        }
        layout.append(portrait, copy);

        const intents = document.createElement('section');
        intents.className = 'story-codex-intents';
        const intentTitle = document.createElement('h4');
        intentTitle.textContent = t.codexObservedIntents(record.intents.size);
        intents.append(intentTitle);
        [...record.intents].sort((a, b) => a - b).forEach((index) => {
            const move = definition.moves?.[index];
            if (!move) return;
            const row = document.createElement('div');
            row.className = 'story-codex-intent-row';
            const moveName = document.createElement('strong');
            moveName.textContent = localize(move.name) || `${t.intent} ${index + 1}`;
            const entries = document.createElement('div');
            entries.className = 'story-codex-intent-entries';
            (move.effects || []).forEach((effect) => {
                entries.append(createStoryIntentEntry(storyCodexIntentFromEffect(effect)));
            });
            row.append(moveName, entries);
            intents.append(row);
        });
        if (!record.intents.size) intents.append(storyCodexEmpty());
        detail.append(layout, intents);
    }

    function renderStoryCodexEnemies(sidebar, detail) {
        const records = storyCodexEnemyRecords().filter((record) => (
            storyCodexSearchMatches(record.id, record.definition)
        ));
        const list = document.createElement('div');
        list.className = 'story-codex-entry-list';
        list.dataset.storyScrollKey = 'codex-enemy-list';
        records.forEach((record) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = `story-codex-entry-row${storyCodexSelectedId === record.id ? ' is-active' : ''}`;
            if (record.definition.image_url) {
                const image = document.createElement('img');
                image.src = record.definition.image_url;
                image.alt = '';
                button.append(image);
            }
            const copy = document.createElement('span');
            const name = document.createElement('strong');
            name.textContent = localize(record.definition.name) || record.id;
            const meta = document.createElement('small');
            meta.textContent = t.codexObservedIntents(record.intents.size);
            copy.append(name, meta);
            button.append(copy);
            button.addEventListener('click', () => {
                storyCodexSelectedId = record.id;
                renderStoryCodex();
            });
            list.append(button);
        });
        sidebar.append(list);
        if (!records.length) {
            detail.append(storyCodexEmpty());
            return;
        }
        if (!records.some((record) => record.id === storyCodexSelectedId)) storyCodexSelectedId = records[0].id;
        renderStoryCodexEnemyDetail(records.find((record) => record.id === storyCodexSelectedId), detail);
    }

    function storyCodexTalentRecords(kind) {
        const contentType = kind === 'blessing' ? 'blessing' : 'relic';
        const catalog = contentType === 'blessing' ? storyContent?.blessings : storyContent?.relics;
        return [...storyCodexDiscoveredIds(contentType)]
            .map((id) => ({ id, kind: contentType, definition: catalog?.[id] }))
            .filter((item) => item.definition && storyCodexSearchMatches(item.id, item.definition))
            .sort((left, right) => (
                (Number(left.definition.order) || 999) - (Number(right.definition.order) || 999)
                || (localize(left.definition.name) || localize(left.definition.description))
                    .localeCompare(localize(right.definition.name) || localize(right.definition.description), lang)
            ));
    }

    function storyCodexSegmented(options, current, onChange) {
        const controls = document.createElement('div');
        controls.className = 'story-codex-segmented';
        options.forEach((option) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = option.id === current ? 'is-active' : '';
            button.textContent = option.label;
            button.addEventListener('click', () => onChange(option.id));
            controls.append(button);
        });
        return controls;
    }

    function renderStoryCodexTalentDetail(record, detail) {
        if (!record?.definition) {
            detail.append(storyCodexEmpty());
            return;
        }
        if (record.kind === 'relic') {
            const wrapper = document.createElement('article');
            wrapper.className = 'story-codex-talent-detail';
            const marker = document.createElement('span');
            marker.className = 'story-codex-talent-marker';
            marker.style.setProperty('--story-relic-color', storyRelicRarityColor(record.definition));
            marker.textContent = '★';
            const list = document.createElement('div');
            list.className = 'story-card-terms-list';
            appendStoryTermRow(list, {
                kind: 'relic', id: record.id, definition: record.definition,
            });
            wrapper.append(marker, list);
            detail.append(wrapper);
            return;
        }
        const wrapper = document.createElement('article');
        wrapper.className = 'story-codex-blessing-detail';
        const mark = document.createElement('span');
        mark.textContent = '✦';
        const copy = document.createElement('div');
        const nameText = localize(record.definition.name).trim();
        const description = document.createElement('p');
        appendStoryRichText(description, localize(record.definition.description));
        if (nameText) {
            const title = document.createElement('h3');
            title.textContent = nameText;
            copy.append(title);
        }
        copy.append(description);
        wrapper.append(mark, copy);
        detail.append(wrapper);
    }

    function renderStoryCodexTalents(sidebar, detail) {
        sidebar.append(storyCodexSegmented([
            { id: 'relic', label: t.codexRelics },
            { id: 'blessing', label: t.codexBlessings },
        ], storyCodexTalentKind, (kind) => {
            storyCodexTalentKind = kind;
            storyCodexSelectedId = '';
            renderStoryCodex();
        }));
        const records = storyCodexTalentRecords(storyCodexTalentKind);
        const list = document.createElement('div');
        list.className = 'story-codex-entry-list';
        list.dataset.storyScrollKey = `codex-talent-list:${storyCodexTalentKind}`;
        records.forEach((record) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = `story-codex-entry-row is-text${storyCodexSelectedId === record.id ? ' is-active' : ''}`;
            const name = document.createElement('strong');
            name.textContent = localize(record.definition.name)
                || localize(record.definition.description)
                || t.codexUnknownTalent;
            button.append(name);
            button.addEventListener('click', () => {
                storyCodexSelectedId = record.id;
                renderStoryCodex();
            });
            list.append(button);
        });
        sidebar.append(list);
        if (!records.length) {
            detail.append(storyCodexEmpty());
            return;
        }
        if (!records.some((record) => record.id === storyCodexSelectedId)) storyCodexSelectedId = records[0].id;
        renderStoryCodexTalentDetail(records.find((record) => record.id === storyCodexSelectedId), detail);
    }

    function storyCodexTermDefinition(kind, id) {
        if (kind === 'status') return storyContent?.statuses?.[id] || null;
        if (kind === 'tag') return storyContent?.tags?.[id] || null;
        if (kind === 'trait') return storyContent?.traits?.[id] || null;
        if (kind === 'resource') return STORY_RESOURCE_TERMS[id] || null;
        return null;
    }

    function storyCodexTermRecords(kind) {
        const prefix = `${kind}:`;
        return storyDiscoveries
            .filter((item) => item.content_type === 'term' && item.content_id.startsWith(prefix))
            .map((item) => {
                const id = item.content_id.slice(prefix.length);
                return { id, kind, definition: storyCodexTermDefinition(kind, id) };
            })
            .filter((item) => item.definition && storyCodexSearchMatches(item.id, item.definition))
            .sort((left, right) => (
                localize(left.definition.name).localeCompare(localize(right.definition.name), lang)
            ));
    }

    function renderStoryCodexTermDetail(record, detail) {
        if (!record?.definition) {
            detail.append(storyCodexEmpty());
            return;
        }
        const list = document.createElement('div');
        list.className = 'story-card-terms-list story-codex-term-detail';
        appendStoryTermRow(list, record);
        detail.append(list);
    }

    function renderStoryCodexTerms(sidebar, detail) {
        sidebar.append(storyCodexSegmented([
            { id: 'status', label: t.codexStatuses },
            { id: 'tag', label: t.codexTags },
            { id: 'trait', label: t.codexTraits },
            { id: 'resource', label: t.codexResources },
        ], storyCodexTermKind, (kind) => {
            storyCodexTermKind = kind;
            storyCodexSelectedId = '';
            renderStoryCodex();
        }));
        const records = storyCodexTermRecords(storyCodexTermKind);
        const list = document.createElement('div');
        list.className = 'story-codex-entry-list';
        list.dataset.storyScrollKey = `codex-term-list:${storyCodexTermKind}`;
        records.forEach((record) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = `story-codex-entry-row is-term${storyCodexSelectedId === record.id ? ' is-active' : ''}`;
            if (record.kind === 'status' || record.kind === 'trait') {
                const icon = document.createElement('img');
                icon.src = record.kind === 'status'
                    ? storyStatusIconUrl(record.id)
                    : storyTraitIconUrl(record.id);
                icon.alt = '';
                button.append(icon);
            } else if (record.kind === 'resource') {
                button.append(createStoryInlineIcon(record.id));
            }
            const name = document.createElement('strong');
            name.textContent = localize(record.definition.name) || record.id;
            button.append(name);
            button.addEventListener('click', () => {
                storyCodexSelectedId = record.id;
                renderStoryCodex();
            });
            list.append(button);
        });
        sidebar.append(list);
        if (!records.length) {
            detail.append(storyCodexEmpty());
            return;
        }
        if (!records.some((record) => record.id === storyCodexSelectedId)) storyCodexSelectedId = records[0].id;
        renderStoryCodexTermDetail(records.find((record) => record.id === storyCodexSelectedId), detail);
    }

    function storyCodexEmpty() {
        const empty = document.createElement('p');
        empty.className = 'story-codex-empty';
        empty.textContent = t.codexEmpty;
        return empty;
    }

    function storyCodexProgress(mode) {
        if (mode === 'cards') {
            return [storyCodexDiscoveredIds('card').size, Object.keys(storyContent?.cards || {}).length];
        }
        if (mode === 'enemies') {
            return [storyCodexDiscoveredIds('enemy').size, Object.keys(storyContent?.enemies || {}).length];
        }
        if (mode === 'talents') {
            const found = storyCodexDiscoveredIds('relic').size + storyCodexDiscoveredIds('blessing').size;
            const total = Object.keys(storyContent?.relics || {}).length + Object.keys(storyContent?.blessings || {}).length;
            return [found, total];
        }
        const found = storyCodexDiscoveredIds('term').size;
        const total = Object.keys(storyContent?.statuses || {}).length
            + Object.keys(storyContent?.tags || {}).length
            + Object.keys(storyContent?.traits || {}).length
            + Object.keys(STORY_RESOURCE_TERMS).length;
        return [found, total];
    }

    function renderStoryCodex() {
        const sidebar = $('story-codex-sidebar');
        const detail = $('story-codex-detail');
        if (!sidebar || !detail || !storyContent) return;
        const scrollPositions = captureStoryScrollPositions();
        sidebar.replaceChildren();
        detail.replaceChildren();
        detail.classList.toggle('is-card-browser', storyCodexMode === 'cards');
        document.querySelectorAll('[data-story-codex-mode]').forEach((tab) => {
            const active = tab.dataset.storyCodexMode === storyCodexMode;
            tab.classList.toggle('is-active', active);
            tab.setAttribute('aria-selected', active ? 'true' : 'false');
            tab.tabIndex = active ? 0 : -1;
        });
        const [found, total] = storyCodexProgress(storyCodexMode);
        setText('story-codex-progress', t.codexDiscovered(found, total));
        if (storyCodexMode === 'cards') renderStoryCodexCards(sidebar, detail);
        else if (storyCodexMode === 'enemies') renderStoryCodexEnemies(sidebar, detail);
        else if (storyCodexMode === 'talents') renderStoryCodexTalents(sidebar, detail);
        else renderStoryCodexTerms(sidebar, detail);
        const subtype = storyCodexMode === 'talents'
            ? storyCodexTalentKind
            : (storyCodexMode === 'terms' ? storyCodexTermKind : '');
        sidebar.dataset.storyScrollKey = `codex-sidebar:${storyCodexMode}:${subtype}`;
        detail.dataset.storyScrollKey = `codex-detail:${storyCodexMode}:${subtype}:${storyCodexSelectedId}`;
        scheduleVisibleStoryCardEffectFits();
        restoreStoryScrollPositions(scrollPositions);
    }

    async function markStoryCodexViewed() {
        const unread = storyDiscoveries.some((item) => !item.viewed_at);
        if (!unread) return;
        const viewedAt = new Date().toISOString();
        storyDiscoveries = storyDiscoveries.map((item) => (
            item.viewed_at ? item : { ...item, viewed_at: viewedAt }
        ));
        updateStoryCodexBadge();
        try {
            await requestJson('/api/story/discoveries/read', {
                method: 'POST',
                body: '{}',
            });
        } catch (_) {
            // Reading the compendium must not interrupt the active journey.
        }
    }

    function openStoryCodex() {
        const dialog = $('story-codex-dialog');
        if (!dialog || !storyContent) return;
        renderStoryCodex();
        if (!dialog.open) dialog.showModal();
        markStoryCodexViewed();
    }

    function closeStoryCodex() {
        const dialog = $('story-codex-dialog');
        if (dialog?.open) dialog.close();
    }

    function renderBlessing(state) {
        const screen = $('story-blessing');
        screen?.classList.remove('is-card-selection');
        setText('story-blessing-kicker', t.floor(state.current_floor || 1));
        setText('story-blessing-title', t.blessingTitle);
        setText('story-blessing-copy', t.blessingCopy);
        const container = $('story-blessing-options');
        container?.replaceChildren();
        container?.classList.remove('story-card-choice-grid');
        const offered = new Set(
            Array.isArray(state.blessing_options) ? state.blessing_options : [],
        );
        const blessings = Object.entries(storyContent?.blessings || {})
            .filter(([id]) => !offered.size || offered.has(id))
            .sort(
            ([firstId, first], [secondId, second]) => (
                (Number(first.order) || 999) - (Number(second.order) || 999)
                || firstId.localeCompare(secondId)
            ),
        );

        const chooseDeckCard = (id, blessing) => {
            screen?.classList.add('is-card-selection');
            setText('story-blessing-title', t.blessingChooseCard);
            setText('story-blessing-copy', localize(blessing.description));
            container?.replaceChildren();
            container?.classList.add('story-card-choice-grid');
            (state.player?.deck || [])
                .filter((card) => blessing.script !== 'remove_card' || !cardValues(card)?.tags?.includes('eternal'))
                .forEach((card) => {
                    container?.append(createStoryCard(card, {
                        compact: true,
                        note: blessing.script === 'remove_card' ? t.remove : t.transform,
                        onClick: () => storyAction('choose_blessing', {
                            blessing_id: id,
                            card_instance_id: card.instance_id,
                        }),
                    }));
                });
            container?.append(choiceButton(
                t.blessingBack,
                () => renderBlessing(state),
            ));
        };

        blessings.forEach(([id, blessing], index) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'story-choice-option story-blessing-option';
            button.dataset.blessingId = id;
            const mark = document.createElement('span');
            mark.className = 'story-choice-mark';
            mark.textContent = String(index + 1);
            const nameText = localize(blessing.name).trim();
            const description = document.createElement('span');
            description.textContent = localize(blessing.description);
            button.append(mark);
            if (nameText) {
                const name = document.createElement('strong');
                name.textContent = nameText;
                button.append(name);
            } else {
                button.classList.add('is-unnamed');
            }
            button.append(description);
            button.addEventListener('click', () => {
                if (blessing.selection === 'deck_card') {
                    chooseDeckCard(id, blessing);
                    return;
                }
                storyAction('choose_blessing', { blessing_id: id });
            });
            container?.append(button);
        });
        showView('story-blessing');
    }

    function renderEasyRelicChoice(state) {
        const screen = $('story-blessing');
        screen?.classList.remove('is-card-selection');
        setText('story-blessing-kicker', t.floor(state.current_floor || 1));
        setText('story-blessing-title', t.easyRelicTitle);
        setText('story-blessing-copy', t.easyRelicCopy);
        const container = $('story-blessing-options');
        container?.replaceChildren();
        container?.classList.remove('story-card-choice-grid');
        const options = Array.isArray(state.easy_relic_options)
            ? state.easy_relic_options
            : [];
        options.forEach((id, index) => {
            const relic = storyContent?.relics?.[id] || {};
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'story-choice-option story-blessing-option';
            button.dataset.relicId = id;
            const mark = document.createElement('span');
            mark.className = 'story-choice-mark';
            mark.textContent = String(index + 1);
            const name = document.createElement('strong');
            name.textContent = localize(relic.name) || id;
            const description = document.createElement('span');
            description.textContent = localize(relic.description);
            button.append(mark, name, description);
            button.addEventListener('click', () => {
                storyAction('choose_easy_relic', { relic_id: id });
            });
            container?.append(button);
        });
        showView('story-blessing');
    }

    function appendStoryChoiceHeading(container, text) {
        const heading = document.createElement('h3');
        heading.className = 'story-choice-section-title';
        heading.textContent = text;
        container?.append(heading);
    }

    function renderJourneySetup(state) {
        const room = state.room || {};
        const container = $('story-room-options');
        const tabs = $('story-room-tabs');
        const footer = $('story-room-footer');
        container?.replaceChildren();
        tabs?.replaceChildren();
        tabs?.classList.add('hidden');
        footer?.replaceChildren();
        setStoryRoomGridMode(container);
        container?.classList.add('is-journey-setup');
        setText('story-room-kicker', lang === 'zh' ? '新旅程' : 'New Journey');
        setText('story-room-title', lang === 'zh' ? '选择旅程模式、起始区域与难度' : 'Choose a journey mode, region, and difficulty');
        setText(
            'story-room-copy',
            lang === 'zh'
                ? '标准旅程包含3个阶段；Boss Rush 将不断生成新的10层路线。'
                : 'Standard journeys have 3 stages; Boss Rush keeps generating new 10-floor routes.',
        );

        let selectedBiome = String(room.biomes?.[0] || 'garden');
        let selectedDifficulty = String(room.difficulties?.[0] || 'normal');
        let selectedMode = String(room.modes?.[0] || 'standard');
        const selectionButtons = [];
        const refreshSelections = () => {
            selectionButtons.forEach(({ button, kind, id }) => {
                const selectedId = kind === 'biome'
                    ? selectedBiome
                    : (kind === 'difficulty' ? selectedDifficulty : selectedMode);
                button.classList.toggle(
                    'is-selected',
                    id === selectedId,
                );
            });
        };

        const modeCopy = {
            standard: {
                name: lang === 'zh' ? '标准旅程' : 'Standard Journey',
                description: lang === 'zh'
                    ? '穿越3个阶段，每个阶段拥有一条16层路线。'
                    : 'Cross 3 stages, each with a 16-floor route.',
            },
            boss_rush: {
                name: 'Boss Rush',
                description: lang === 'zh'
                    ? '先获得10次卡牌奖励与1项天赋；每10层选择区域与可叠加诅咒，无限推进。'
                    : 'Begin with 10 card rewards and 1 talent; every 10 floors, choose a region and a stackable curse and continue endlessly.',
            },
        };
        appendStoryChoiceHeading(container, lang === 'zh' ? '模式' : 'Mode');
        (room.modes || ['standard']).forEach((modeId) => {
            const copy = modeCopy[modeId] || { name: String(modeId), description: '' };
            const button = choiceButton(
                copy.name,
                () => {
                    selectedMode = String(modeId);
                    refreshSelections();
                },
                { description: copy.description },
            );
            selectionButtons.push({ button, kind: 'mode', id: String(modeId) });
            container?.append(button);
        });
        appendStoryChoiceHeading(container, lang === 'zh' ? '区域' : 'Region');
        (room.biomes || []).forEach((biomeId) => {
            const definition = storyContent?.biomes?.[biomeId] || {};
            const button = choiceButton(
                localize(definition.name) || String(biomeId),
                () => {
                    selectedBiome = String(biomeId);
                    refreshSelections();
                },
            );
            selectionButtons.push({ button, kind: 'biome', id: String(biomeId) });
            container?.append(button);
        });
        appendStoryChoiceHeading(container, lang === 'zh' ? '难度' : 'Difficulty');
        (room.difficulties || []).forEach((difficultyId) => {
            const definition = storyContent?.difficulties?.[difficultyId] || {};
            const localizedName = localize(definition.name) || String(difficultyId);
            const englishName = String(definition.name?.en || '').trim();
            const difficultyLabel = lang !== 'en' && englishName && englishName !== localizedName
                ? `${localizedName} ${englishName}`
                : localizedName;
            const button = choiceButton(
                difficultyLabel,
                () => {
                    selectedDifficulty = String(difficultyId);
                    refreshSelections();
                },
                { description: localize(definition.description) },
            );
            selectionButtons.push({ button, kind: 'difficulty', id: String(difficultyId) });
            container?.append(button);
        });
        refreshSelections();
        footer?.append(storyRoomFooterButton(
            lang === 'zh' ? '开始旅程' : 'Start Journey',
            () => storyAction('start_journey', {
                biome: selectedBiome,
                difficulty: selectedDifficulty,
                mode: selectedMode,
            }),
        ));
        showView('story-room');
    }

    function renderMapView(state, options = {}) {
        const player = state.player || {};
        const node = currentNode(state);
        setText('story-stage-value', state.stage || 1);
        setText('story-biome-value', state.biome === 'garden' ? t.garden : state.biome || t.garden);
        setText('story-health-value', `${stateValue(player.health)}/${stateValue(player.max_health)}`);
        setText('story-elixir-value', `${stateValue(player.elixir ?? player.max_elixir)} E`);
        setText('story-magic-value', `${stateValue(player.magic)} M`);
        setText('story-gold-value', stateValue(player.gold ?? 0));
        setText('story-floor-value', t.floor(state.current_floor || node?.floor || 1));
        setText('story-room-value', t.rooms[node?.type] || node?.type || '');
        renderLegend();
        const combatPreview = Boolean(options.combatPreview);
        $('story-map-return')?.classList.toggle('hidden', !combatPreview);
        renderMap(state.map, state.current_node_id, { readOnly: combatPreview });
        showView('story-run');
    }

    function openStoryCombatMap() {
        const state = activeRun?.state;
        if (!state?.combat || state.phase !== 'combat') return;
        storyMapPreviewOpen = true;
        renderMapView(state, { combatPreview: true });
    }

    function returnToStoryCombat() {
        const state = activeRun?.state;
        if (!state?.combat || state.phase !== 'combat') return;
        storyMapPreviewOpen = false;
        renderCombat(state, false);
    }

    function renderEffects(containerId, values) {
        const container = $(containerId);
        renderEffectsInto(container, values);
    }

    function removeStoryEquipmentPreview() {
        if (!storyEquipmentPreview) return;
        storyEquipmentPreview.remove();
        storyEquipmentPreview = null;
    }

    function removeStoryCardHoverPreview() {
        if (!storyCardHoverPreview) return;
        storyCardHoverPreview.remove();
        storyCardHoverPreview = null;
    }

    function positionStoryEquipmentPreview(anchor) {
        if (!storyEquipmentPreview || !anchor?.isConnected) return;
        const anchorRect = anchor.getBoundingClientRect();
        const previewRect = storyEquipmentPreview.getBoundingClientRect();
        const gap = 14;
        let left = anchorRect.right + gap;
        let top = anchorRect.top + anchorRect.height / 2 - previewRect.height / 2;
        if (left + previewRect.width > window.innerWidth - 8) {
            left = anchorRect.left - previewRect.width - gap;
        }
        left = Math.max(8, Math.min(window.innerWidth - previewRect.width - 8, left));
        top = Math.max(8, Math.min(window.innerHeight - previewRect.height - 8, top));
        storyEquipmentPreview.style.left = `${left}px`;
        storyEquipmentPreview.style.top = `${top}px`;
    }

    function showStoryEquipmentPreview(anchor, card) {
        if (!anchor || !cardValues(card)) return;
        removeStoryCardHoverPreview();
        removeStoryEquipmentPreview();
        const preview = document.createElement('div');
        preview.className = 'story-equipment-preview';
        preview.setAttribute('aria-hidden', 'true');
        const previewCard = createStoryCard(card, {
            interactive: false,
            predictionTargetId: '',
            hoverPreview: false,
        });
        preview.append(previewCard);
        document.body.append(preview);
        storyEquipmentPreview = preview;
        positionStoryEquipmentPreview(anchor);
        scheduleStoryCardEffectFit(previewCard);
        requestAnimationFrame(() => {
            positionStoryEquipmentPreview(anchor);
            preview.classList.add('is-visible');
        });
    }

    function attachStoryEquipmentPreview(anchor, card) {
        if (!anchor || !cardValues(card)) return;
        anchor.addEventListener('pointerenter', () => {
            if (window.matchMedia?.('(hover: none), (pointer: coarse)').matches) return;
            showStoryEquipmentPreview(anchor, card);
        });
        anchor.addEventListener('pointermove', () => positionStoryEquipmentPreview(anchor));
        anchor.addEventListener('pointerleave', removeStoryEquipmentPreview);
        anchor.addEventListener('focus', () => showStoryEquipmentPreview(anchor, card));
        anchor.addEventListener('blur', removeStoryEquipmentPreview);
    }

    function renderStoryEquipment(cards) {
        const container = $('story-player-equipment');
        if (!container) return;
        removeStoryEquipmentPreview();
        container.replaceChildren();
        const equipment = Array.isArray(cards) ? cards : [];
        container.style.setProperty('--story-equipment-count', String(Math.max(1, equipment.length)));
        const nowSeconds = Date.now() / 1000;
        const orbitDelay = -(nowSeconds % 20);
        const spinDelay = -(nowSeconds % 17.333);
        equipment.forEach((card, index) => {
            const values = cardValues(card);
            if (!values) return;
            const item = document.createElement('button');
            item.type = 'button';
            item.className = 'story-equipment';
            item.dataset.instanceId = String(card.instance_id || '');
            item.style.setProperty('--story-equipment-index', String(index));
            const angle = 360 / Math.max(1, equipment.length) * index;
            item.style.setProperty('--story-equipment-angle', `${angle}deg`);
            item.style.setProperty('--story-equipment-orbit-delay', `${orbitDelay.toFixed(3)}s`);
            item.style.setProperty('--story-equipment-spin-delay', `${spinDelay.toFixed(3)}s`);
            item.setAttribute(
                'aria-label',
                `${localize(values.name)}：${localize(values.description)}`,
            );
            const visual = document.createElement('span');
            visual.className = 'story-equipment-visual';
            const icon = document.createElement('span');
            icon.className = 'story-equipment-icon';
            const imageUrl = card.upgraded
                ? (values.upgraded_image_url || values.image_url || '')
                : (values.image_url || '');
            if (imageUrl) {
                const image = document.createElement('img');
                image.className = 'story-equipment-image';
                image.src = imageUrl;
                image.alt = '';
                image.setAttribute('aria-hidden', 'true');
                icon.append(image);
            } else {
                const fallback = document.createElement('span');
                fallback.className = 'story-equipment-fallback';
                fallback.textContent = localize(values.name).slice(0, 1);
                icon.append(fallback);
            }
            visual.append(icon);
            item.append(visual);
            storyCardElementData.set(item, card);
            attachStoryEquipmentPreview(item, card);
            container.append(item);
        });
    }

    function createStoryEffectChip(item, amount) {
        const chip = document.createElement('span');
        const definition = storyStatusDefinition(item.key);
        const categoryClass = definition?.category === 'action' ? 'story-action' : 'story-status';
        chip.className = `story-effect ${categoryClass} story-effect-${item.key}`;
        chip.dataset.storyEffectKey = String(item.key || '');
        const label = definition ? localize(definition.name) : (item.label || storyIntentStatusLabel(item.key));
        chip.title = `${label}: ${amount}`;
        chip.setAttribute('aria-label', chip.title);
        const icon = document.createElement('img');
        icon.src = storyStatusIconUrl(item.key);
        icon.alt = '';
        icon.setAttribute('aria-hidden', 'true');
        const value = document.createElement('strong');
        value.textContent = String(amount);
        chip.append(icon, value);
        attachStoryStatusTermAccess(chip, item.key);
        return chip;
    }

    function createStoryTraitChip(traitKey, rawAmount = 0, isStatic = false) {
        const key = String(traitKey || '');
        const definition = storyTraitDefinition(key);
        if (!definition) return null;
        const effectKey = storyTraitValueKeys()[key];
        const amount = Math.max(0, Number(rawAmount) || 0);
        const chip = document.createElement('span');
        chip.className = `story-effect story-trait story-trait-${key.replaceAll('_', '-')}`;
        if (effectKey) chip.dataset.storyEffectKey = effectKey;
        if (isStatic) chip.dataset.storyEffectStatic = 'true';
        const name = localize(definition.name);
        const description = localize(definition.description);
        chip.title = [name, description].filter(Boolean).join('\n');
        chip.setAttribute('aria-label', chip.title);
        const icon = document.createElement('img');
        icon.src = storyTraitIconUrl(key);
        icon.alt = '';
        icon.setAttribute('aria-hidden', 'true');
        chip.append(icon);
        if (amount > 0 || key === 'miracle' || key === 'bandage') {
            const counter = document.createElement('strong');
            counter.textContent = String(amount);
            chip.append(counter);
        }
        attachStoryTraitTermAccess(chip, key);
        return chip;
    }

    function updateStoryEffectValue(container, key, rawAmount) {
        if (!container || !key) return;
        const amount = Number(rawAmount);
        if (!Number.isFinite(amount)) return;
        const chip = [...container.querySelectorAll('[data-story-effect-key]')]
            .find((item) => item.dataset.storyEffectKey === key);
        const traitKey = storyTraitKeyForEffectKey(key);
        if (amount === 0) {
            const zeroVisible = new Set(storyContent?.trait_zero_visible || ['bandage', 'miracle']);
            if (
                chip?.dataset.storyEffectStatic === 'true'
                && zeroVisible.has(traitKey)
            ) {
                let value = chip.querySelector('strong');
                if (!value) {
                    value = document.createElement('strong');
                    chip.append(value);
                }
                value.textContent = '0';
            } else chip?.remove();
            return;
        }
        if (!chip) {
            const traitChip = traitKey ? createStoryTraitChip(traitKey, amount) : null;
            container.append(traitChip || createStoryEffectChip({
                key,
                label: storyIntentStatusLabel(key),
            }, amount));
            return;
        }
        let value = chip.querySelector('strong');
        if (!value) {
            value = document.createElement('strong');
            chip.append(value);
        }
        value.textContent = String(amount);
        const definition = storyStatusDefinition(key) || storyTraitDefinition(traitKey);
        const label = definition ? localize(definition.name) : storyIntentStatusLabel(key);
        chip.title = `${label}: ${amount}`;
        chip.setAttribute('aria-label', chip.title);
    }

    function renderEffectsInto(container, values) {
        if (!container) return;
        container.replaceChildren();
        values.forEach((item) => {
            const amount = Number(item.value);
            if (!Number.isFinite(amount) || amount === 0) return;
            const traitKey = storyTraitKeyForEffectKey(item.key);
            const traitChip = traitKey ? createStoryTraitChip(traitKey, amount) : null;
            container.append(traitChip || createStoryEffectChip(item, amount));
        });
    }

    function renderTraitsInto(container, traitIds, actor = null) {
        if (!container) return;
        const staticTraitKeys = new Set((traitIds || []).map((traitId) => String(traitId || '')));
        const visibleTraitKeys = new Set(staticTraitKeys);
        Object.entries(storyTraitValueKeys()).forEach(([traitKey, effectKey]) => {
            if (Number(actor?.[effectKey]) > 0 && storyTraitDefinition(traitKey)) {
                visibleTraitKeys.add(traitKey);
            }
        });
        visibleTraitKeys.forEach((key) => {
            const definition = storyTraitDefinition(key);
            if (!definition || (key === 'nourish' && actor?.nourished)) return;
            const effectKey = storyTraitValueKeys()[key];
            const value = Math.max(0, Number(actor?.[effectKey]) || 0);
            const zeroVisible = new Set(storyContent?.trait_zero_visible || ['bandage', 'miracle']);
            if (effectKey && value <= 0 && !zeroVisible.has(key)) return;
            const chip = createStoryTraitChip(key, value, staticTraitKeys.has(key));
            if (chip) container.append(chip);
        });
    }

    function canSatisfyCardSelection(card, combat) {
        const spec = cardSelectionSpec(card, combat);
        return !spec || spec.source.length >= spec.minimum;
    }

    function storyIntentStatusLabel(status) {
        const key = String(status || '');
        const definition = storyStatusDefinition(key);
        if (definition) return localize(definition.name) || key;
        return {
            power: t.power,
            shield: t.shield,
            weak: t.weak,
            vulnerable: t.vulnerable,
            fragile: lang === 'zh' ? '脆弱' : 'Fragile',
            broken: lang === 'zh' ? '破损' : 'Broken',
            stun: lang === 'zh' ? '眩晕' : 'Stun',
            reflection: lang === 'zh' ? '反射' : 'Reflection',
            wither: lang === 'zh' ? '凋萎' : 'Wither',
            charged: lang === 'zh' ? '带电' : 'Charged',
            charging: lang === 'zh' ? '蓄力' : 'Charging Up',
            frenzy: lang === 'zh' ? '狂暴' : 'Frenzied',
            hidden: lang === 'zh' ? '隐形' : 'Hidden',
            sturdy: lang === 'zh' ? '坚固' : 'Sturdy',
            blind: lang === 'zh' ? '失明' : 'Blind',
            poison: lang === 'zh' ? '中毒' : 'Poison',
            entangle: lang === 'zh' ? '缠绕' : 'Entangle',
        }[key] || key;
    }

    function createStoryIntentEntry(entry) {
        const item = document.createElement('span');
        const kind = String(entry?.kind || 'special');
        item.className = `story-intent-entry is-${kind}`;
        item.dataset.intentKind = kind;
        const amount = Math.max(0, Number(entry?.amount) || 0);
        const hits = Math.max(1, Number(entry?.hits) || 1);
        let label = '';
        let iconUrl = '';
        if (kind === 'attack' || kind === 'self_damage') {
            iconUrl = STORY_INLINE_ICONS.D;
            label = entry?.lethal
                ? (lang === 'zh' ? '死亡' : 'Defeat self')
                : `${amount}${hits > 1 ? `×${hits}` : ''}`;
            if (kind === 'self_damage') label = `${t.self} ${label}`;
        } else if (kind === 'heal') {
            iconUrl = STORY_INLINE_ICONS.H;
            label = entry?.full ? (lang === 'zh' ? '回满' : 'Full') : `+${amount}`;
        } else if (kind === 'defend') {
            label = `${storyIntentStatusLabel(entry.stat || 'shield')} +${amount}`;
        } else if (kind === 'buff') {
            label = `${storyIntentStatusLabel(entry.stat || 'power')} +${amount}`;
        } else if (kind === 'status') {
            label = `${storyIntentStatusLabel(entry.status)} +${amount}`;
            if (entry?.delayed) label = lang === 'zh' ? `下回合 ${label}` : `Next turn ${label}`;
            if (entry?.conditional === 'shield') {
                label = lang === 'zh' ? `若仍有护盾：${label}` : `If Shield remains: ${label}`;
            }
        } else if (kind === 'clear_status') {
            const statusLabel = storyIntentStatusLabel(entry.status);
            label = lang === 'zh' ? `清除${statusLabel}` : `Clear ${statusLabel}`;
        } else if (kind === 'summon') {
            const summonedName = localize(entry?.enemy_name) || String(entry?.enemy_id || '');
            label = [t.summon, amount > 1 ? `${amount}×` : '', summonedName]
                .filter(Boolean)
                .join(' ');
        } else if (kind === 'card') {
            label = entry?.effect_type === 'delayed_hand_charge'
                ? (lang === 'zh' ? `下回合手牌电荷 +${amount}` : `Next turn hand Charge +${amount}`)
                : t.addCard;
        } else if (kind === 'consume') {
            label = t.consume;
        } else {
            const effectType = String(entry?.effect_type || '');
            if (effectType === 'lose_max_health_percent') {
                label = lang === 'zh' ? `自身H上限-${amount}%` : `Own max H -${amount}%`;
            } else if (effectType === 'consume_pearls_damage') {
                label = lang === 'zh' ? `每颗珍珠造成${amount}D` : `${amount}D per Pearl`;
            } else {
                label = String(entry?.summary || effectType || '--');
            }
        }
        if (entry?.target === 'all_enemies') label = `${t.allies} · ${label}`;
        else if (entry?.target === 'player') label = `${t.playerSide || (lang === 'zh' ? '玩家方' : 'Player side')} · ${label}`;
        if (iconUrl) {
            const icon = document.createElement('img');
            icon.src = iconUrl;
            icon.alt = '';
            icon.setAttribute('aria-hidden', 'true');
            item.append(icon);
        }
        const value = document.createElement('strong');
        value.textContent = label;
        item.append(value);
        return item;
    }

    function createEnemyActor(enemy, selectedTargetKind, selectableTargetIds = null) {
        const definition = storyContent?.enemies?.[enemy?.def_id] || {};
        const actor = document.createElement('article');
        actor.className = 'story-actor story-actor-enemy classic-fighter';
        actor.dataset.targetKind = 'enemy';
        actor.dataset.targetId = String(enemy.id || '');
        actor.tabIndex = 0;
        actor.classList.toggle(
            'is-play-target',
            selectedTargetKind === 'enemy' && selectableTargetIds?.has(String(enemy.id || '')),
        );

        const name = document.createElement('div');
        name.className = 'story-actor-name classic-fighter-name';
        name.textContent = localize(enemy.name) || (lang === 'zh' ? '生物' : 'Creature');
        const portrait = document.createElement('div');
        const imageUrl = String(enemy?.image_url || definition.image_url || '').trim();
        portrait.className = `story-portrait ${imageUrl ? 'story-enemy-portrait' : 'story-enemy-placeholder'}`;
        portrait.setAttribute('aria-label', name.textContent);
        if (imageUrl) {
            const image = document.createElement('img');
            image.src = imageUrl;
            image.alt = '';
            image.draggable = false;
            image.setAttribute('aria-hidden', 'true');
            portrait.append(image);
        } else {
            portrait.textContent = '?';
        }

        const health = document.createElement('div');
        health.className = 'story-health-wrap';
        const healthIcon = document.createElement('img');
        healthIcon.src = '/static/assets/ui-icons/hit-point.svg';
        healthIcon.alt = '';
        healthIcon.setAttribute('aria-hidden', 'true');
        const healthBody = document.createElement('div');
        healthBody.className = 'story-health-body';
        const track = document.createElement('div');
        track.className = 'story-health-track';
        const fill = document.createElement('div');
        fill.className = 'story-health-fill';
        fill.dataset.enemyHealthFill = String(enemy.id || '');
        fill.style.width = `${Math.max(0, Math.min(100, Number(enemy.health || 0) / Math.max(1, Number(enemy.max_health || 1)) * 100))}%`;
        track.append(fill);
        const healthValue = document.createElement('b');
        healthValue.dataset.enemyHealthValue = String(enemy.id || '');
        healthValue.textContent = `${Math.max(0, Number(enemy.health || 0))}/${Math.max(1, Number(enemy.max_health || 1))}`;
        healthBody.append(track, healthValue);
        health.append(healthIcon, healthBody);

        const effects = document.createElement('div');
        effects.className = 'story-effect-list';
        renderEffectsInto(effects, [
            { key: 'shield', label: t.shield, value: enemy.shield },
            { key: 'power', label: t.power, value: enemy.power },
            { key: 'temporary_power', label: t.power, value: enemy.temporary_power },
            { key: 'endurance', label: '耐力', value: enemy.endurance },
            { key: 'weak', label: t.weak, value: enemy.weak },
            { key: 'vulnerable', label: t.vulnerable, value: enemy.vulnerable },
            { key: 'fragile', label: '脆弱', value: enemy.fragile },
            { key: 'evade', label: '闪避', value: enemy.evade },
            { key: 'poison', label: '中毒', value: enemy.poison },
            { key: 'stun', label: '眩晕', value: enemy.stun },
            { key: 'reflection', label: '反射', value: enemy.reflection },
            { key: 'wither', label: '凋萎', value: enemy.wither },
            { key: 'broken', label: '破损', value: enemy.broken },
            { key: 'rockfall', label: '落石', value: enemy.rockfall },
            { key: 'blind', label: '失明', value: enemy.blind },
            { key: 'entangle', label: '缠绕', value: enemy.entangle },
            { key: 'negative_status_immunity', label: '负面状态免疫', value: enemy.negative_status_immunity },
            { key: 'evil_eye', label: '邪眼', value: enemy.evil_eye },
            { key: 'toxic_poison', label: '剧毒', value: enemy.toxic_poison },
            { key: 'stagnation', label: '滞留', value: enemy.stagnation },
            { key: 'bleed', label: '流血', value: enemy.bleed },
            { key: 'fire', label: '灼烧', value: enemy.fire },
            { key: 'fragment', label: '碎片', value: enemy.fragment },
            { key: 'magic_shield_disabled', label: '魔力护盾失效', value: enemy.magic_shield_disabled },
        ]);
        renderTraitsInto(effects, definition.traits, enemy);

        const intent = document.createElement('div');
        intent.className = 'story-intent';
        const intentLabel = document.createElement('span');
        const intentName = localize(enemy.intent?.name);
        intentLabel.className = 'story-intent-title';
        intentLabel.textContent = [t.intent, intentName].filter(Boolean).join(' · ');
        const intentEntries = document.createElement('div');
        intentEntries.className = 'story-intent-entries';
        const structuredEntries = Array.isArray(enemy.intent?.entries) ? enemy.intent.entries : [];
        structuredEntries.forEach((entry) => intentEntries.append(createStoryIntentEntry(entry)));
        if (!structuredEntries.length) {
            const fallback = document.createElement('strong');
            fallback.textContent = enemy.intent?.summary || '--';
            intentEntries.append(fallback);
        }
        intent.append(intentLabel, intentEntries);
        actor.append(name, portrait, health, effects, intent);
        const previewPrediction = () => setStoryPredictionTarget(enemy.id);
        const clearPrediction = (event) => {
            if (event?.relatedTarget && actor.contains(event.relatedTarget)) return;
            if (livingStoryEnemies().length > 1) setStoryPredictionTarget('');
        };
        actor.addEventListener('pointerenter', previewPrediction);
        actor.addEventListener('pointerleave', clearPrediction);
        actor.addEventListener('focusin', previewPrediction);
        actor.addEventListener('focusout', clearPrediction);
        actor.addEventListener('pointerdown', () => {
            if (!selectedCombatCardId && livingStoryEnemies().length > 1) previewPrediction();
        });
        return actor;
    }

    function renderCombat(state, preserveScroll = true) {
        const scrollPositions = preserveScroll ? captureStoryScrollPositions() : [];
        const combat = state.combat || {};
        const player = state.player || {};
        const livingEnemies = (combat.enemies || []).filter((item) => Number(item.health) > 0);
        if (livingEnemies.length <= 1) hoveredPredictionTargetId = '';
        else if (!livingEnemies.some((item) => String(item.id) === String(hoveredPredictionTargetId))) {
            hoveredPredictionTargetId = '';
        }
        if (selectedCombatCardId && !selectedCombatCard(state)) selectedCombatCardId = '';
        const selected = selectedCombatCard(state);
        const selectedValues = cardValues(previewedCombatCard(state));
        const blindActive = Boolean(combat.blind_active);
        const selectedTargetKind = selected && !storyCursorCardMode(selected) ? cardTargetKind(selected) : '';
        const selectableTargetIds = new Set(
            selectedTargetKind === 'enemy'
                ? selectableStoryEnemies(selected, state).map((enemy) => String(enemy.id || ''))
                : [],
        );
        setText('story-round', `R${combat.round || 1}`);
        setText('story-phase', combat.turn === 'player' ? t.playerTurn : t.enemyTurn);
        setHealthBar('story-combat-player', player.health, player.max_health);
        renderResourceOrbs(
            'story-combat-player-elixir',
            combat.elixir,
            selectedValues?.cost_e,
            'e',
        );
        renderResourceOrbs(
            'story-combat-player-magic',
            combat.magic,
            selectedValues?.cost_m,
            'm',
        );
        renderEffects('story-player-effects', [
            { key: 'shield', label: t.shield, value: combat.shield },
            { key: 'power', label: t.power, value: combat.power },
            { key: 'temporary_power', label: t.power, value: combat.temporary_power },
            { key: 'endurance', label: '耐力', value: combat.endurance },
            { key: 'weak', label: t.weak, value: combat.weak },
            { key: 'vulnerable', label: t.vulnerable, value: combat.vulnerable },
            { key: 'fragile', label: '脆弱', value: combat.fragile },
            { key: 'evade', label: '闪避', value: combat.evade },
            { key: 'poison', label: '中毒', value: combat.poison },
            { key: 'stun', label: '眩晕', value: combat.stun },
            { key: 'broken', label: '破损', value: combat.broken },
            { key: 'reflection', label: '反射', value: combat.reflection },
            { key: 'wither', label: '凋萎', value: combat.wither },
            { key: 'rockfall', label: '落石', value: combat.rockfall },
            {
                key: 'blind',
                label: '失明',
                value: Math.max(Number(combat.blind) || 0, blindActive ? 1 : 0),
            },
            { key: 'entangle', label: '缠绕', value: combat.entangle },
            { key: 'negative_status_immunity', label: '负面状态免疫', value: combat.negative_status_immunity },
            { key: 'evil_eye', label: '邪眼', value: combat.evil_eye },
            { key: 'sturdy', label: '坚固', value: combat.sturdy },
            { key: 'toxic_poison', label: '剧毒', value: combat.toxic_poison },
            { key: 'stagnation', label: '滞留', value: combat.stagnation },
            { key: 'bleed', label: '流血', value: combat.bleed },
            { key: 'fire', label: '灼烧', value: combat.fire },
            { key: 'blockade', label: '封锁', value: combat.blockade },
            { key: 'locked', label: '锁定', value: combat.locked },
        ]);
        renderStoryEquipment(combat.equipment);
        const enemyGroup = $('story-enemy-group');
        enemyGroup?.replaceChildren();
        livingEnemies.forEach((enemyItem) => {
            enemyGroup?.append(createEnemyActor(enemyItem, selectedTargetKind, selectableTargetIds));
        });
        syncStoryEnemyGroupLayout();
        const hand = $('story-hand');
        hand?.replaceChildren();
        hand?.classList.toggle('has-selected-card', Boolean(selected));
        const cards = combat.hand || [];
        const frenzyForcesAttack = (state.player?.relics || []).includes('frenzy_relic')
            && cards.some((handCard) => cardValues(handCard)?.type === 'thorn');
        cards.forEach((card, index) => {
            const values = cardValues(card);
            const tags = new Set(values?.tags || []);
            const costE = values?.cost_e === 'X' ? 0 : Number(values?.cost_e || 0);
            const authoritativePlayableIds = Array.isArray(combat.playable_card_ids)
                ? new Set(combat.playable_card_ids.map(String))
                : null;
            const fallbackPlayable = values
                && !tags.has('unplayable')
                && Number(combat.elixir) >= costE
                && Number(combat.magic) >= Number(values.cost_m || 0)
                && combat.turn === 'player'
                && !combat.opening_redraw_pending
                && !combat.pending_card_choice
                && (!frenzyForcesAttack || values.type === 'thorn')
                && (combat.card_play_limit == null || Number(combat.cards_played_this_turn || 0) < Number(combat.card_play_limit))
                && canSatisfyCardSelection(card, combat);
            const playable = authoritativePlayableIds
                ? authoritativePlayableIds.has(String(card.instance_id || ''))
                : fallbackPlayable;
            const wrapper = document.createElement('div');
            wrapper.className = 'story-hand-card';
            wrapper.dataset.instanceId = String(card.instance_id || '');
            const center = (cards.length - 1) / 2;
            const distance = index - center;
            const rotation = Math.max(-13, Math.min(13, distance * 4.2));
            const lift = Math.max(0, 18 - Math.abs(distance) * 4);
            wrapper.style.setProperty('--fan-rot', `${rotation}deg`);
            wrapper.style.setProperty('--fan-rot-inverse', `${-rotation}deg`);
            wrapper.style.setProperty('--fan-y', `${-lift}px`);
            wrapper.style.setProperty('--fan-z', String(100 + Math.round(20 - Math.abs(distance))));
            if (String(card.instance_id) === String(selectedCombatCardId)) wrapper.classList.add('is-selected');
            wrapper.append(createStoryCard(card, {
                disabled: !playable,
                blinded: blindActive,
                enablePrediction: true,
                predictionTargetId: storyPredictionTargetId(state),
                onClick: (event) => selectCombatCard(state, card, event),
            }));
            wrapper.addEventListener('pointerenter', () => {
                hoveredCombatCardId = String(card.instance_id || '');
                renderCombatResourcePreview(state);
            });
            wrapper.addEventListener('pointerleave', () => {
                if (hoveredCombatCardId === String(card.instance_id || '')) {
                    hoveredCombatCardId = '';
                    renderCombatResourcePreview(state);
                }
            });
            hand?.append(wrapper);
        });
        syncStoryCursorCard(state);
        const targetKind = selected ? cardTargetKind(selected) : '';
        const cursorMode = selected ? storyCursorCardMode(selected) : '';
        $('story-player-target')?.classList.toggle('is-play-target', !cursorMode && targetKind === 'self');
        document.querySelectorAll('.story-actor-enemy').forEach((actor) => {
            actor.classList.toggle(
                'is-play-target',
                !cursorMode
                    && targetKind === 'enemy'
                    && selectableTargetIds.has(String(actor.dataset.targetId || '')),
            );
        });
        $('story-play-lane')?.classList.toggle('is-armed', Boolean(selected));
        setText('story-play-hint', selected
            ? (cursorMode
                ? (cursorMode === 'self' ? t.playSelfAnywhere : t.playAnywhere)
                : (targetKind === 'enemy' ? t.chooseEnemy : t.chooseSelf))
            : t.chooseCardHint);
        setText('story-hand-count', combat.hand?.length || 0);
        setText('story-draw-pile-count', combat.draw_pile?.length || 0);
        setText('story-discard-pile-count', combat.discard_pile?.length || 0);
        setText('story-exile-pile-count', combat.exile_pile?.length || 0);
        [
            ['story-draw-pile', t.drawPile],
            ['story-discard-pile', t.discardPile],
            ['story-exile-pile', t.exilePile],
        ].forEach(([id, label]) => {
            const button = $(id);
            if (!button) return;
            const title = lang === 'zh' ? `查看${label}` : `View ${label}`;
            button.title = title;
            button.setAttribute('aria-label', title);
            const labelNode = $(`${id}-label`);
            if (labelNode) labelNode.textContent = title.trim();
        });
        const endTurn = $('story-end-turn');
        if (endTurn) endTurn.disabled = (
            combat.turn !== 'player'
            || Boolean(combat.opening_redraw_pending)
            || Boolean(combat.pending_card_choice)
        );
        showView('story-combat');
        scheduleStoryAimUpdate(state);
        if (combat.opening_redraw_pending) {
            queueMicrotask(() => {
                if (!storyCombatEntranceAnimating) openOpeningRedraw(state);
            });
        } else if (combat.pending_card_choice) {
            queueMicrotask(() => {
                if (!storyCombatEntranceAnimating) openPendingStoryCardChoice(state);
            });
        }
        if (preserveScroll) restoreStoryScrollPositions(scrollPositions);
    }

    function choiceButton(label, onClick, options = {}) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `story-choice-option${options.primary ? ' is-primary' : ''}`;
        const title = document.createElement('strong');
        title.textContent = label;
        button.append(title);
        if (options.description) {
            const description = document.createElement('span');
            appendStoryRichText(description, options.description);
            button.append(description);
        }
        button.disabled = Boolean(options.disabled);
        button.addEventListener('click', onClick);
        return button;
    }

    function storyRoomTabKey(state, room) {
        return [
            String(state?.stage || ''),
            String(state?.current_node_id || ''),
            String(room?.type || ''),
            String(room?.event_id || ''),
        ].join(':');
    }

    function setStoryRoomGridMode(container, mode = 'choices') {
        if (!container) return;
        container.classList.remove('is-journey-setup');
        container.classList.toggle('story-room-card-grid', mode === 'cards');
    }

    function appendStoryRoomEmpty(container, message) {
        const empty = document.createElement('p');
        empty.className = 'story-room-empty';
        empty.textContent = message;
        container?.append(empty);
    }

    function storyRoomFooterButton(label, onClick) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'story-command';
        button.textContent = label;
        button.addEventListener('click', onClick);
        return button;
    }

    function renderStoryRoomTabs(state, definitions) {
        const tabs = $('story-room-tabs');
        const container = $('story-room-options');
        if (!tabs || !container || !definitions.length) return;
        const key = storyRoomTabKey(state, state.room || {});
        const availableIds = new Set(definitions.map((definition) => definition.id));
        if (activeStoryRoomTabKey !== key || !availableIds.has(activeStoryRoomTabId)) {
            activeStoryRoomTabKey = key;
            activeStoryRoomTabId = definitions[0].id;
        }

        tabs.replaceChildren();
        tabs.classList.toggle('hidden', definitions.length < 2);
        tabs.setAttribute('aria-label', t.roomActions);
        const buttons = new Map();
        const activate = (tabId, focus = false) => {
            const definition = definitions.find((item) => item.id === tabId) || definitions[0];
            activeStoryRoomTabId = definition.id;
            buttons.forEach((button, id) => {
                const active = id === definition.id;
                button.classList.toggle('is-active', active);
                button.setAttribute('aria-selected', active ? 'true' : 'false');
                button.tabIndex = active ? 0 : -1;
            });
            container.replaceChildren();
            container.setAttribute('role', 'tabpanel');
            container.setAttribute('aria-labelledby', `story-room-tab-${definition.id}`);
            setStoryRoomGridMode(container, definition.mode);
            definition.render(container);
            scheduleVisibleStoryCardEffectFits();
            if (focus) buttons.get(definition.id)?.focus();
        };

        definitions.forEach((definition, index) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.id = `story-room-tab-${definition.id}`;
            button.className = 'story-room-tab';
            button.setAttribute('role', 'tab');
            button.setAttribute('aria-controls', 'story-room-options');
            button.textContent = definition.label;
            button.addEventListener('click', () => activate(definition.id));
            button.addEventListener('keydown', (event) => {
                let nextIndex = null;
                if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
                    nextIndex = (index - 1 + definitions.length) % definitions.length;
                } else if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
                    nextIndex = (index + 1) % definitions.length;
                } else if (event.key === 'Home') {
                    nextIndex = 0;
                } else if (event.key === 'End') {
                    nextIndex = definitions.length - 1;
                }
                if (nextIndex == null) return;
                event.preventDefault();
                activate(definitions[nextIndex].id, true);
            });
            buttons.set(definition.id, button);
            tabs.append(button);
        });
        activate(activeStoryRoomTabId);
    }

    function openStoryDeckChange({ kind, card, payload, price = 0 }) {
        const dialog = $('story-deck-change-dialog');
        const before = $('story-deck-change-before');
        const after = $('story-deck-change-after');
        if (!dialog || !before || !after || !card) return;
        pendingStoryDeckChange = { actionType: 'resolve_room', payload: { ...payload } };
        dialog.returnValue = '';
        setText(
            'story-deck-change-title',
            kind === 'remove'
                ? t.confirmRemoveTitle
                : (kind === 'transform'
                    ? (lang === 'zh' ? '确认变化卡牌' : 'Confirm card transformation')
                    : t.confirmUpgradeTitle),
        );
        setText(
            'story-deck-change-copy',
            [
                Number(price) > 0 ? `${Number(price)}G` : '',
                t.permanentDeckChange,
            ].filter(Boolean).join(' · '),
        );
        before.replaceChildren(createStoryCard(
            storyCardAtUpgradeState(card, Boolean(card.upgraded)),
            { compact: true },
        ));
        after.replaceChildren();
        if (kind === 'remove') {
            const removed = document.createElement('div');
            removed.className = 'story-deck-change-removed';
            removed.textContent = t.removedFromDeck;
            after.append(removed);
        } else if (kind === 'transform') {
            const transformed = document.createElement('div');
            transformed.className = 'story-deck-change-removed';
            transformed.textContent = lang === 'zh' ? '随机变化为另一张牌' : 'Transform into another random card';
            after.append(transformed);
        } else {
            after.append(createStoryCard(
                storyCardAtUpgradeState(card, true),
                { compact: true },
            ));
        }
        if (!dialog.open) dialog.showModal();
    }

    function openStoryEventConfirmation(option, onConfirm) {
        const dialog = $('story-event-confirm-dialog');
        if (!dialog || typeof onConfirm !== 'function') return;
        pendingStoryEventAction = onConfirm;
        dialog.returnValue = '';
        setText('story-event-confirm-title', t.confirmEventTitle);
        setText('story-event-confirm-copy', t.confirmEventCopy);
        setText('story-event-confirm-label', localize(option?.label) || String(option?.id || ''));
        const description = $('story-event-confirm-description');
        description?.replaceChildren();
        appendStoryRichText(description, localize(option?.description));
        if (!dialog.open) dialog.showModal();
    }

    function renderStoryEventContext(room) {
        const context = $('story-event-context');
        if (!context) return;
        const isEvent = room?.type === 'event';
        context.classList.toggle('hidden', !isEvent);
        if (!isEvent) return;
        const scene = room.scene || {};
        const sceneElement = $('story-event-scene');
        if (sceneElement) {
            sceneElement.textContent = String(scene.mark || '?');
            sceneElement.dataset.sceneId = String(scene.id || room.event_id || '');
        }
        setText('story-event-speaker', localize(room.speaker));
        const body = $('story-event-body');
        body?.replaceChildren();
        appendStoryRichText(
            body,
            localize(room.body) || localize(room.description) || t.eventCopy,
        );
        const history = $('story-event-history');
        history?.replaceChildren();
        const historyEntries = Array.isArray(room.history) ? room.history : [];
        historyEntries.slice(0, -1).slice(-4).forEach((entry) => {
            const result = localize(entry?.result);
            if (!result) return;
            const item = document.createElement('li');
            appendStoryRichText(item, result);
            history?.append(item);
        });
    }

    function renderStoryRoomContext(state, room) {
        renderStoryEventContext(room);
        const roomView = $('story-room');
        if (roomView) roomView.dataset.roomType = String(room?.type || '');
        const player = state?.player || {};
        const rest = $('story-rest-context');
        const chest = $('story-chest-context');
        const shop = $('story-shop-context');
        const isRest = room?.type === 'rest';
        const isChest = room?.type === 'chest';
        const isShop = room?.type === 'shop';
        rest?.classList.toggle('hidden', !isRest);
        chest?.classList.toggle('hidden', !isChest);
        shop?.classList.toggle('hidden', !isShop);

        if (isRest) {
            const health = Math.max(0, Number(player.health) || 0);
            const maximum = Math.max(0, Number(player.max_health) || 0);
            const recovery = Math.min(
                Math.max(0, maximum - health),
                Math.ceil(maximum * .3),
            );
            setText('story-rest-health-label', t.currentHealth);
            setText('story-rest-health-value', `${health}/${maximum}`);
            setText('story-rest-heal-label', t.restRecovery);
            setText('story-rest-heal-value', `+${recovery}H`);
        }
        if (isChest) {
            const relic = storyContent?.relics?.[room.relic];
            const relicDescription = localize(relic?.description);
            setText('story-chest-mark', t.roomMarks.chest || 'T');
            setText('story-chest-gold-label', t.chestGold);
            setText('story-chest-gold-value', `${Math.max(0, Number(room.gold) || 0)}G`);
            setText('story-chest-relic-label', t.chestTalent);
            setText('story-chest-relic-name', localize(relic?.name) || t.none);
            setText('story-chest-relic-description', relicDescription);
            $('story-chest-relic-description')?.classList.toggle('hidden', !relicDescription);
        }
        if (isShop) {
            setText('story-shop-gold-label', t.shopWallet);
            setText('story-shop-gold-value', `${Math.max(0, Number(player.gold) || 0)}G`);
            setText('story-shop-remove-label', t.removePrice);
            setText('story-shop-remove-value', `${Math.max(0, Number(room.remove_price) || 0)}G`);
            setText('story-shop-upgrade-label', t.upgradePrice);
            setText('story-shop-upgrade-value', `${Math.max(0, Number(room.upgrade_price) || 0)}G`);
        }
    }

    function renderRoom(state) {
        const room = state.room || {};
        const player = state.player || {};
        const upgradableCards = (player.deck || [])
            .filter((card) => storyCardIsUpgradable(card));
        const container = $('story-room-options');
        const tabs = $('story-room-tabs');
        const footer = $('story-room-footer');
        container?.replaceChildren();
        container?.removeAttribute('role');
        container?.removeAttribute('aria-labelledby');
        setStoryRoomGridMode(container);
        tabs?.replaceChildren();
        tabs?.classList.add('hidden');
        footer?.replaceChildren();
        renderStoryRoomContext(state, room);
        setText('story-room-kicker', `${t.floor(state.current_floor || 1)} · ${t.rooms[room.type] || t.room}`);
        if (room.type === 'stage_choice') {
            const bossRush = Boolean(room.boss_rush || state.journey_mode === 'boss_rush');
            const block = Math.max(1, Number(room.stage) || 1);
            const floorStart = (block - 1) * 10 + 1;
            const floorEnd = block * 10;
            setText(
                'story-room-title',
                bossRush
                    ? (lang === 'zh' ? `Boss Rush：选择第 ${block} 轮区域` : `Boss Rush: Choose Block ${block} Region`)
                    : (lang === 'zh' ? `选择第 ${room.stage || ''} 阶段区域` : `Choose Stage ${room.stage || ''} region`),
            );
            setText(
                'story-room-copy',
                bossRush
                    ? (lang === 'zh'
                        ? `选择下一区域和1项可叠加的诅咒，随后进入第 ${floorStart}-${floorEnd} 层。`
                        : `Choose the next region and 1 stackable curse, then enter Floors ${floorStart}-${floorEnd}.`)
                    : (lang === 'zh'
                        ? '选择下一区域和1项诅咒；随后生成新的16层路线。'
                        : 'Choose the next region and 1 curse, then generate a new 16-floor route.'),
            );
            let selectedBiome = String(room.biomes?.[0] || 'garden');
            const availableCurses = Array.isArray(room.curses)
                ? room.curses
                : Object.keys(storyContent?.curses || {});
            let selectedCurse = String(availableCurses[0] || '');
            const selectionButtons = [];
            const refreshSelections = () => {
                selectionButtons.forEach(({ button, kind, id }) => {
                    button.classList.toggle(
                        'is-selected',
                        kind === 'biome' ? id === selectedBiome : id === selectedCurse,
                    );
                });
            };
            appendStoryChoiceHeading(container, lang === 'zh' ? '区域' : 'Region');
            (room.biomes || []).forEach((biome) => {
                const definition = storyContent?.biomes?.[biome] || {};
                const button = choiceButton(
                    localize(definition.name) || String(biome),
                    () => {
                        selectedBiome = String(biome);
                        refreshSelections();
                    },
                );
                selectionButtons.push({ button, kind: 'biome', id: String(biome) });
                container?.append(button);
            });
            appendStoryChoiceHeading(container, lang === 'zh' ? '诅咒' : 'Curse');
            availableCurses.forEach((curseId) => {
                const definition = storyContent?.curses?.[curseId] || {};
                const button = choiceButton(
                    localize(definition.name) || String(curseId),
                    () => {
                        selectedCurse = String(curseId);
                        refreshSelections();
                    },
                    { description: localize(definition.description) },
                );
                selectionButtons.push({ button, kind: 'curse', id: String(curseId) });
                container?.append(button);
            });
            refreshSelections();
            footer?.append(storyRoomFooterButton(
                t.confirm,
                () => storyAction('choose_stage', {
                    biome: selectedBiome,
                    curse_id: selectedCurse,
                }),
            ));
        } else if (room.type === 'rest') {
            setText('story-room-title', t.restTitle);
            setText('story-room-copy', t.restCopy);
            const amount = Math.ceil(Number(player.max_health || 0) * 0.3);
            const restTabs = [
                {
                    id: 'rest-heal',
                    label: t.heal,
                    mode: 'choices',
                    render: (target) => target.append(choiceButton(
                        `${t.heal} ${amount}H`,
                        () => storyAction('resolve_room', { option: 'heal' }),
                        { primary: true },
                    )),
                },
                {
                    id: 'rest-upgrade',
                    label: t.upgrade,
                    mode: 'cards',
                    render: (target) => {
                        if (!upgradableCards.length) appendStoryRoomEmpty(target, t.noUpgradableCards);
                        upgradableCards.forEach((card) => target.append(createStoryCard(card, {
                            compact: true,
                            note: t.upgrade,
                            previewUpgradeOnHover: true,
                            onClick: () => openStoryDeckChange({
                                kind: 'upgrade',
                                card,
                                payload: {
                                    option: 'upgrade',
                                    card_instance_id: card.instance_id,
                                },
                            }),
                        })));
                    },
                },
            ];
            if ((room.options || []).includes('gold')) {
                restTabs.push({
                    id: 'rest-gold',
                    label: t.restGold,
                    mode: 'choices',
                    render: (target) => target.append(choiceButton(
                        t.gainedGold(150),
                        () => storyAction('resolve_room', { option: 'gold' }),
                    )),
                });
            }
            if ((room.options || []).includes('plant_dandelion')) {
                restTabs.push({
                    id: 'rest-plant-dandelion',
                    label: t.plantDandelion,
                    mode: 'choices',
                    render: (target) => target.append(choiceButton(
                        t.plantDandelion,
                        () => storyAction('resolve_room', { option: 'plant_dandelion' }),
                        { primary: true },
                    )),
                });
            }
            renderStoryRoomTabs(state, restTabs);
            footer?.append(storyRoomFooterButton(
                t.directLeave,
                () => storyAction('resolve_room', { option: 'leave' }),
            ));
        } else if (room.type === 'chest') {
            setText('story-room-title', t.chestTitle);
            setText('story-room-copy', t.chestCopy);
            const claims = room.claims && typeof room.claims === 'object'
                ? room.claims
                : { gold: false, relic: false };
            const relic = storyContent?.relics?.[room.relic];
            if (Number(room.gold || 0) > 0) {
                container?.append(choiceButton(
                    `${t.claimChestGold} · ${Number(room.gold)}G`,
                    () => storyAction('resolve_room', { option: 'claim_gold' }),
                    { disabled: Boolean(claims.gold), description: claims.gold ? t.claimed : t.claim },
                ));
            }
            if (room.relic) {
                container?.append(choiceButton(
                    `${t.claimChestTalent} · ${localize(relic?.name) || room.relic}`,
                    () => storyAction('resolve_room', { option: 'claim_relic' }),
                    {
                        disabled: Boolean(claims.relic),
                        description: claims.relic ? t.claimed : localize(relic?.description),
                    },
                ));
            }
            footer?.append(storyRoomFooterButton(
                t.directLeave,
                () => storyAction('resolve_room', { option: 'leave' }),
            ));
        } else if (room.type === 'shop') {
            setText('story-room-title', t.shopTitle);
            setText('story-room-copy', t.shopCopy);
            renderStoryRoomTabs(state, [
                {
                    id: 'shop-cards',
                    label: t.shopCards,
                    mode: 'cards',
                    render: (target) => {
                        const available = (room.cards || []).filter((item) => !item.sold);
                        if (!available.length) appendStoryRoomEmpty(target, t.noShopCards);
                        available.forEach((item) => {
                            const card = { instance_id: item.id, def_id: item.card_id, upgraded: false };
                            target.append(createStoryCard(card, {
                                compact: true,
                                disabled: Number(player.gold || 0) < Number(item.price || 0),
                                note: `${Number(item.price || 0)}G`,
                                onClick: () => storyAction('resolve_room', {
                                    option: 'buy_card',
                                    item_id: item.id,
                                }),
                            }));
                        });
                    },
                },
                {
                    id: 'shop-talents',
                    label: t.shopTalents,
                    mode: 'choices',
                    render: (target) => {
                        const available = (room.relics || []).filter((item) => !item.sold);
                        if (!available.length) appendStoryRoomEmpty(target, t.noShopTalents);
                        available.forEach((item) => {
                            const relic = storyContent?.relics?.[item.relic_id];
                            target.append(choiceButton(
                                `${localize(relic?.name) || item.relic_id} · ${item.price}G`,
                                () => storyAction('resolve_room', {
                                    option: 'buy_relic',
                                    item_id: item.id,
                                }),
                                {
                                    description: localize(relic?.description),
                                    disabled: Number(player.gold || 0) < Number(item.price || 0),
                                },
                            ));
                        });
                    },
                },
                {
                    id: 'shop-remove',
                    label: t.remove,
                    mode: 'cards',
                    render: (target) => {
                        if (room.service_used) {
                            appendStoryRoomEmpty(target, t.shopServiceUsed);
                            return;
                        }
                        (player.deck || []).forEach((card) => {
                            const eternal = cardValues(card)?.tags?.includes('eternal');
                            target.append(createStoryCard(card, {
                                compact: true,
                                disabled: eternal || Number(player.gold || 0) < Number(room.remove_price || 0),
                                note: eternal ? t.cannotRemove : `${t.remove} · ${room.remove_price}G`,
                                onClick: () => openStoryDeckChange({
                                    kind: 'remove',
                                    card,
                                    price: room.remove_price,
                                    payload: {
                                        option: 'remove_card',
                                        card_instance_id: card.instance_id,
                                    },
                                }),
                            }));
                        });
                    },
                },
                {
                    id: 'shop-upgrade',
                    label: t.upgrade,
                    mode: 'cards',
                    render: (target) => {
                        if (room.service_used) {
                            appendStoryRoomEmpty(target, t.shopServiceUsed);
                            return;
                        }
                        if (!upgradableCards.length) appendStoryRoomEmpty(target, t.noUpgradableCards);
                        upgradableCards.forEach((card) => target.append(createStoryCard(card, {
                            compact: true,
                            disabled: Number(player.gold || 0) < Number(room.upgrade_price || 0),
                            note: `${t.upgrade} · ${room.upgrade_price}G`,
                            previewUpgradeOnHover: true,
                            onClick: () => openStoryDeckChange({
                                kind: 'upgrade',
                                card,
                                price: room.upgrade_price,
                                payload: {
                                    option: 'upgrade_card',
                                    card_instance_id: card.instance_id,
                                },
                            }),
                        })));
                    },
                },
            ].filter((definition) => (
                definition.id !== 'shop-remove'
                || (room.options || []).includes('remove_card')
            )));
            footer?.append(storyRoomFooterButton(
                t.leave,
                () => storyAction('resolve_room', { option: 'leave' }),
            ));
        } else {
            setText('story-room-title', localize(room.title) || t.eventTitle);
            const eventCopy = [
                room.event_id === 'mystery_lottery'
                    ? (lang === 'zh' ? `已抽奖 ${Number(room.attempts || 0)}/4 次` : `${Number(room.attempts || 0)}/4 attempts`)
                    : '',
            ].filter(Boolean).join(' ');
            setText('story-room-copy', eventCopy);
            const options = (room.choices || room.options || []).map((rawOption) => (
                typeof rawOption === 'string'
                    ? { id: rawOption, label: rawOption, description: '' }
                    : rawOption
            ));
            const renderEventActions = (target, actionOptions) => actionOptions.forEach((option) => {
                const optionId = String(option.id || '');
                const disabled = (
                    Number(player.gold || 0) < Number(option.cost_gold || 0)
                    || (optionId === 'event_buy' && Number(player.gold || 0) < 35)
                    || (optionId === 'lottery_draw' && (
                        Number(player.gold || 0) < 50
                        || Number(room.attempts || 0) >= 4
                    ))
                );
                const resolveOption = () => storyAction('resolve_room', { option: optionId });
                target.append(choiceButton(
                    localize(option.label) || optionId,
                    () => {
                        if (option.requires_confirmation) {
                            openStoryEventConfirmation(option, resolveOption);
                        } else {
                            resolveOption();
                        }
                    },
                    {
                        primary: optionId !== 'leave' && optionId !== 'fight_leave',
                        description: localize(option.description),
                        disabled,
                    },
                ));
            });
            const selectionOptions = options.filter((option) => option.selection);
            if (selectionOptions.length) {
                const eventTabs = [];
                const eventTabIds = {
                    upgrade: { id: 'event-upgrade' }.id,
                    remove: { id: 'event-remove' }.id,
                    trade: { id: 'event-trade' }.id,
                };
                const usedEventTabIds = new Set();
                const actionOptions = options.filter((option) => !option.selection);
                if (actionOptions.length) {
                    eventTabs.push({
                        id: 'event-actions',
                        label: t.roomActions,
                        mode: 'choices',
                        render: (target) => renderEventActions(target, actionOptions),
                    });
                }
                selectionOptions.forEach((option) => {
                    const selection = String(option.selection || '');
                    const allowed = new Set((option.candidate_ids || []).map(String));
                    let source = [...(player.deck || [])];
                    if (selection === 'upgrade') {
                        source = upgradableCards;
                    } else {
                        if (allowed.size) {
                            source = source.filter((card) => allowed.has(String(card.instance_id)));
                        }
                        if (selection === 'remove') {
                            source = source.filter((card) => !cardValues(card)?.tags?.includes('eternal'));
                        }
                    }
                    const baseTabId = eventTabIds[selection]
                        || `event-${String(option.id || selection)}`;
                    let tabId = baseTabId;
                    let duplicateIndex = 2;
                    while (usedEventTabIds.has(tabId)) {
                        tabId = `${baseTabId}-${duplicateIndex}`;
                        duplicateIndex += 1;
                    }
                    usedEventTabIds.add(tabId);
                    eventTabs.push({
                        id: tabId,
                        label: localize(option.label) || t.chooseCards,
                        mode: 'cards',
                        render: (target) => {
                            if (!source.length) {
                                if (selection === 'upgrade') {
                                    appendStoryRoomEmpty(target, t.noUpgradableCards);
                                } else {
                                    appendStoryRoomEmpty(target, t.none);
                                }
                                return;
                            }
                            source.forEach((card) => {
                                const isPrimary = storyContent?.cards?.[card.def_id]?.rarity === 'primary';
                                const price = selection === 'trade'
                                    ? (isPrimary ? 50 : 0)
                                    : Number(option.cost_gold || 0);
                                const disabled = Number(player.gold || 0) < price;
                                const cardOptions = {
                                    compact: true,
                                    disabled,
                                    note: [localize(option.label), price > 0 ? `${price}G` : '']
                                        .filter(Boolean)
                                        .join(' · '),
                                    onClick: () => openStoryDeckChange({
                                        kind: selection === 'trade' ? 'transform' : selection,
                                        card,
                                        price,
                                        payload: {
                                            option: String(option.id || ''),
                                            card_instance_id: card.instance_id,
                                        },
                                    }),
                                };
                                if (selection === 'upgrade') {
                                    target.append(createStoryCard(card, {
                                        ...cardOptions,
                                        previewUpgradeOnHover: true,
                                    }));
                                } else {
                                    target.append(createStoryCard(card, cardOptions));
                                }
                            });
                        },
                    });
                });
                renderStoryRoomTabs(state, eventTabs);
            } else {
                renderEventActions(container, options);
            }
        }
        showView('story-room');
    }

    function normalizedRewardClaims(reward) {
        const claims = reward?.claims;
        if (claims && typeof claims === 'object') {
            return {
                gold: Boolean(claims.gold) || Number(reward.gold || 0) <= 0,
                card: Boolean(claims.card) || !(reward.cards || []).length,
                relic: Boolean(claims.relic) || !(reward.relics || []).length && !reward.relic,
            };
        }
        return {
            gold: true,
            card: !(reward?.cards || []).length,
            relic: !(reward?.relics || []).length && !reward?.relic,
        };
    }

    function rewardClaimButton(label, description, claimed, onClick) {
        const button = choiceButton(
            label,
            onClick,
            {
                description: claimed ? t.claimed : description,
                disabled: claimed,
            },
        );
        button.classList.add('story-reward-claim');
        button.classList.toggle('is-claimed', claimed);
        return button;
    }

    function renderReward(state) {
        const reward = state.reward || {};
        const claims = normalizedRewardClaims(reward);
        const isBlessingReward = reward.source === 'blessing';
        const rewardRound = Math.max(1, Number(reward.round_index) || 1);
        const rewardTotal = Math.max(rewardRound, Number(reward.round_total) || 1);
        const isSequentialReward = rewardTotal > 1;
        setText('story-reward-kicker', isBlessingReward ? t.rooms.blessing : t.battleWon);
        setText(
            'story-reward-title',
            isSequentialReward ? t.blessingCardReward(rewardRound, rewardTotal) : t.rewards,
        );
        setText('story-reward-copy', isSequentialReward ? t.blessingRewardCopy : t.rewardCopy);
        const relicIds = (reward.relics || []).length
            ? reward.relics
            : (reward.relic ? [reward.relic] : []);
        const claimContainer = $('story-reward-claims');
        claimContainer?.replaceChildren();
        if (Number(reward.gold || 0) > 0) {
            claimContainer?.append(rewardClaimButton(
                t.goldReward(reward.gold),
                t.claim,
                claims.gold,
                () => storyAction('choose_reward', { reward_type: 'gold' }),
            ));
        }
        if (claims.relic && reward.selected_relic_id) {
            const relic = storyContent?.relics?.[reward.selected_relic_id];
            claimContainer?.append(rewardClaimButton(
                `${t.talentReward} · ${localize(relic?.name) || reward.selected_relic_id}`,
                t.claimed,
                true,
                () => {},
            ));
        } else if (!claims.relic) {
            relicIds.forEach((relicId) => {
                const relic = storyContent?.relics?.[relicId];
                claimContainer?.append(rewardClaimButton(
                    `${t.talentReward} · ${localize(relic?.name) || relicId}`,
                    localize(relic?.description),
                    false,
                    () => storyAction('choose_reward', {
                        reward_type: 'relic',
                        relic_id: relicId,
                    }),
                ));
            });
        }
        if (claims.card) {
            const selected = (reward.cards || []).find((choice) => {
                const defId = typeof choice === 'string' ? choice : choice.card_id;
                return defId === reward.selected_card_id;
            });
            const selectedDefId = typeof selected === 'string' ? selected : selected?.card_id;
            const selectedName = selectedDefId
                ? localize(storyContent?.cards?.[selectedDefId]?.name)
                : t.skip;
            claimContainer?.append(rewardClaimButton(
                `${t.cardReward} · ${selectedName}`,
                t.claimed,
                true,
                () => {},
            ));
        }
        const container = $('story-reward-options');
        container?.replaceChildren();
        container?.classList.toggle('hidden', claims.card);
        if (!claims.card) {
            (reward.cards || []).forEach((choice) => {
                const defId = typeof choice === 'string' ? choice : choice.card_id;
                const upgraded = Boolean(typeof choice === 'object' && choice.upgraded);
                const card = { instance_id: `reward-${defId}`, def_id: defId, upgraded };
                container?.append(createStoryCard(card, {
                    onClick: () => storyAction('choose_reward', {
                        reward_type: 'card',
                        card_id: defId,
                    }),
                }));
            });
        }
        const skip = $('story-reward-skip');
        const mustTakeCard = (state?.player?.relics || []).includes('grab_every_card');
        skip?.classList.toggle('hidden', claims.card || mustTakeCard);
        const canContinue = Object.values(claims).every(Boolean);
        const continueButton = $('story-reward-continue');
        continueButton?.classList.toggle('hidden', !canContinue);
        if (continueButton) continueButton.disabled = !canContinue;
        const leaveButton = $('story-reward-leave');
        if (leaveButton) {
            leaveButton.textContent = t.directLeave;
            leaveButton.classList.toggle('hidden', canContinue);
        }
        showView('story-reward');
    }

    function renderTerminal(state) {
        const complete = state.phase === 'complete';
        setText('story-terminal-mark', complete ? '✓' : '×');
        setText('story-terminal-title', complete ? t.journeyComplete : t.journeyFailed);
        setText('story-terminal-copy', complete ? t.journeyCompleteCopy : t.journeyFailedCopy);
        $('story-terminal-mark')?.classList.toggle('is-failure', !complete);
        showView('story-terminal');
    }

    function renderRun(run) {
        const scrollPositions = captureStoryScrollPositions();
        activeRun = run;
        storyMapPreviewOpen = false;
        updateStoryStatusBar();
        updateStorySurrenderControl(run);
        if (window.__STORY_DEV_TOOLS__) {
            renderDeveloperPanel(run?.state || null, { syncValues: developerModeOpen });
        }
        if (!run) {
            selectedCombatCardId = '';
            $('story-save-open-global')?.classList.add('hidden');
            $('story-map-return')?.classList.add('hidden');
            destroyStoryCursorCard();
            $('story-aim-layer')?.classList.add('hidden');
            showView('story-empty');
            restoreStoryScrollPositions(scrollPositions);
            return;
        }
        const state = run.state || {};
        const hasFloorCheckpoint = Boolean(state.floor_entry_checkpoint?.state);
        $('story-save-open-global')?.classList.toggle(
            'hidden',
            state.phase === 'map' || !hasFloorCheckpoint,
        );
        $('story-restart-floor')?.classList.toggle('hidden', !hasFloorCheckpoint);
        if (state.phase === 'journey_setup') renderJourneySetup(state);
        else if (state.phase === 'easy_relic') renderEasyRelicChoice(state);
        else if (state.phase === 'blessing') renderBlessing(state);
        else if (state.phase === 'combat' && state.combat) renderCombat(state, false);
        else {
            selectedCombatCardId = '';
            destroyStoryCursorCard();
            $('story-aim-layer')?.classList.add('hidden');
            if (state.phase === 'room' || state.phase === 'stage_choice') renderRoom(state);
            else if (state.phase === 'reward') renderReward(state);
            else if (state.phase === 'complete' || state.phase === 'game_over') renderTerminal(state);
            else renderMapView(state);
        }
        openPendingStoryDeckOperation(state);
        restoreStoryScrollPositions(scrollPositions);
    }

    async function resumeRunFromCheckpoint(run) {
        const checkpoint = run?.state?.recovery_checkpoint;
        const phase = String(run?.state?.phase || '');
        if (!checkpoint?.state || !['combat', 'room', 'reward'].includes(phase)) return run;
        try {
            const result = await requestJson('/api/story/run/action', {
                method: 'POST',
                body: JSON.stringify({
                    run_id: run.id,
                    state_version: run.state_version,
                    action_id: createActionId(),
                    action_type: 'resume_node',
                    payload: {},
                }),
            });
            ingestStoryDiscoveryPayload(result);
            return result.run || run;
        } catch (error) {
            if (error.payload?.run) return error.payload.run;
            throw error;
        }
    }

    async function loadRun() {
        showView('story-loading');
        try {
            const [contentPayload, runPayload] = await Promise.all([
                requestStoryLoadJson('/api/story/content'),
                requestStoryLoadJson('/api/story/run'),
            ]);
            storyContent = contentPayload.content || {};
            contentVersion = contentPayload.content_version || '';
            ingestStoryDiscoveryPayload(contentPayload);
            ingestStoryDiscoveryPayload(runPayload);
            let run = runPayload.run || null;
            if (run && contentVersion && run.content_version !== contentVersion && window.__STORY_DEV_TOOLS__) {
                activeRun = run;
                await resetMap(true);
                return;
            }
            run = await resumeRunFromCheckpoint(run);
            renderRun(run);
        } catch (error) {
            if (error.message === 'AUTH_REQUIRED') return;
            showView('story-empty');
            showToast(error.message);
        }
    }

    async function startRun() {
        const button = $('story-start');
        if (button) button.disabled = true;
        try {
            if (!storyContent) {
                const contentPayload = await requestStoryLoadJson('/api/story/content');
                storyContent = contentPayload.content || {};
                contentVersion = contentPayload.content_version || '';
                ingestStoryDiscoveryPayload(contentPayload);
            }
            const payload = await requestJson('/api/story/run', { method: 'POST', body: '{}' });
            ingestStoryDiscoveryPayload(payload);
            renderRun(payload.run || null);
        } catch (error) {
            if (error.message !== 'AUTH_REQUIRED') showToast(error.message);
        } finally {
            if (button) button.disabled = false;
        }
    }

    async function abandonRun(renderEmpty = true) {
        if (!activeRun) return true;
        try {
            await requestJson('/api/story/run/abandon', {
                method: 'POST',
                body: JSON.stringify({ run_id: activeRun.id }),
            });
            activeRun = null;
            if (renderEmpty) renderRun(null);
            return true;
        } catch (error) {
            if (error.message !== 'AUTH_REQUIRED') showToast(error.message);
            return false;
        }
    }

    async function resetMap(silent = false) {
        if (!activeRun) return;
        const button = $('story-reset-map');
        if (button) button.disabled = true;
        try {
            const payload = await requestJson('/api/story/run/reset-map', {
                method: 'POST',
                body: JSON.stringify({ run_id: activeRun.id }),
            });
            ingestStoryDiscoveryPayload(payload);
            renderRun(payload.run || null);
            if (!silent) showToast(t.mapReset);
        } catch (error) {
            if (error.message !== 'AUTH_REQUIRED') showToast(error.message);
        } finally {
            if (button) button.disabled = false;
        }
    }

    function storySaveDate(value) {
        const date = new Date(String(value || ''));
        if (!Number.isFinite(date.getTime())) return '--';
        const locale = { zh: 'zh-CN', en: 'en-US', fr: 'fr-FR', ja: 'ja-JP' }[lang] || 'zh-CN';
        return new Intl.DateTimeFormat(locale, {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        }).format(date);
    }

    function renderManualStorySaves(saves, allowLoad = activeRun?.state?.phase === 'map') {
        const list = $('story-save-list');
        if (!list) return;
        const scrollPositions = captureStoryScrollPositions();
        list.replaceChildren();
        const entries = Array.isArray(saves) ? saves : [];
        if (!entries.length) {
            const empty = document.createElement('p');
            empty.className = 'story-save-empty';
            empty.textContent = t.noSaves;
            list.append(empty);
            restoreStoryScrollPositions(scrollPositions);
            return;
        }
        entries.forEach((save) => {
            const row = document.createElement('article');
            row.className = 'story-save-row';
            const details = document.createElement('div');
            details.className = 'story-save-details';
            const title = document.createElement('strong');
            const slotIndex = Math.max(0, Number(save.slot_index) || 0);
            title.textContent = slotIndex === 0
                ? t.saveCurrentSlot
                : t.savePreviousSlot(slotIndex);
            const summary = document.createElement('span');
            summary.textContent = `${t.stage} ${stateValue(save.stage)} · ${t.floor(stateValue(save.floor))}`;
            const timestamp = document.createElement('time');
            timestamp.dateTime = String(save.created_at || '');
            timestamp.textContent = storySaveDate(save.created_at);
            details.append(title, summary, timestamp);
            const loadButton = document.createElement('button');
            loadButton.type = 'button';
            loadButton.className = 'story-command story-save-load';
            loadButton.textContent = t.loadSave;
            loadButton.disabled = !allowLoad;
            loadButton.addEventListener('click', () => {
                pendingStorySaveId = Number(save.id) || 0;
                $('story-save-load-dialog')?.showModal();
            });
            const actions = document.createElement('div');
            actions.className = 'story-save-row-actions';
            const deleteButton = document.createElement('button');
            deleteButton.type = 'button';
            deleteButton.className = 'story-command story-command-danger story-save-delete';
            deleteButton.textContent = t.deleteSave;
            deleteButton.addEventListener('click', () => {
                pendingStorySaveId = Number(save.id) || 0;
                $('story-save-delete-dialog')?.showModal();
            });
            actions.append(loadButton, deleteButton);
            row.append(details, actions);
            list.append(row);
        });
        restoreStoryScrollPositions(scrollPositions);
    }

    async function openManualStorySaves() {
        if (!activeRun) {
            return;
        }
        const onMap = activeRun.state?.phase === 'map';
        const canRestart = Boolean(activeRun.state?.floor_entry_checkpoint?.state);
        if (!onMap && !canRestart) {
            showToast(t.saveOnlyOnMap);
            return;
        }
        $('story-save-create')?.classList.toggle('hidden', !onMap);
        $('story-restart-floor')?.classList.toggle('hidden', !canRestart);
        setText('story-save-copy', onMap ? t.saveCopy : t.restartFloorCopy);
        const dialog = $('story-save-dialog');
        const list = $('story-save-list');
        if (list) {
            const loading = document.createElement('p');
            loading.className = 'story-save-empty';
            loading.textContent = t.loading;
            list.replaceChildren(loading);
        }
        dialog?.showModal();
        try {
            const payload = await requestJson(
                `/api/story/run/saves?run_id=${encodeURIComponent(activeRun.id)}`,
            );
            renderManualStorySaves(payload.saves, onMap);
        } catch (error) {
            if (error.message !== 'AUTH_REQUIRED') showToast(error.message || t.requestFailed);
            renderManualStorySaves([], onMap);
        }
    }

    async function restartStoryFloor() {
        if (!activeRun?.state?.floor_entry_checkpoint?.state) return;
        const button = $('story-restart-floor-confirm');
        if (button) button.disabled = true;
        try {
            $('story-restart-floor-dialog')?.close();
            $('story-save-dialog')?.close();
            await storyAction('restart_floor', {});
            showToast(t.restartFloorSucceeded);
        } finally {
            if (button) button.disabled = false;
        }
    }

    async function createManualStorySave() {
        if (!activeRun || activeRun.state?.phase !== 'map') {
            showToast(t.saveOnlyOnMap);
            return;
        }
        const button = $('story-save-create');
        if (button) button.disabled = true;
        try {
            const payload = await requestJson('/api/story/run/save', {
                method: 'POST',
                body: JSON.stringify({
                    run_id: activeRun.id,
                    state_version: activeRun.state_version,
                }),
            });
            renderManualStorySaves(payload.saves);
            showToast(t.saveSucceeded);
        } catch (error) {
            if (error.payload?.run) renderRun(error.payload.run);
            if (error.message !== 'AUTH_REQUIRED') showToast(error.message || t.requestFailed);
        } finally {
            if (button) button.disabled = false;
        }
    }

    async function loadManualStorySave(saveId) {
        if (!activeRun || activeRun.state?.phase !== 'map' || !saveId) {
            showToast(t.saveOnlyOnMap);
            return;
        }
        try {
            const payload = await requestJson('/api/story/run/load', {
                method: 'POST',
                body: JSON.stringify({
                    run_id: activeRun.id,
                    state_version: activeRun.state_version,
                    save_id: saveId,
                }),
            });
            $('story-save-dialog')?.close();
            ingestStoryDiscoveryPayload(payload);
            renderRun(payload.run || activeRun);
            showToast(t.loadSucceeded);
        } catch (error) {
            if (error.payload?.run) renderRun(error.payload.run);
            if (error.message !== 'AUTH_REQUIRED') showToast(error.message || t.requestFailed);
        }
    }

    async function deleteManualStorySave(saveId) {
        if (!activeRun || !saveId) return;
        const button = $('story-save-delete-confirm');
        if (button) button.disabled = true;
        try {
            const payload = await requestJson('/api/story/run/save/delete', {
                method: 'POST',
                body: JSON.stringify({
                    run_id: activeRun.id,
                    save_id: saveId,
                }),
            });
            renderManualStorySaves(payload.saves, activeRun.state?.phase === 'map');
            showToast(t.saveDeleted);
        } catch (error) {
            if (error.payload?.saves) {
                renderManualStorySaves(error.payload.saves, activeRun.state?.phase === 'map');
            }
            if (error.message !== 'AUTH_REQUIRED') showToast(error.message || t.requestFailed);
        } finally {
            if (button) button.disabled = false;
        }
    }

    async function startNewJourney() {
        const button = $('story-terminal-new');
        if (button) button.disabled = true;
        const ended = await abandonRun(false);
        if (ended) await startRun();
        if (button) button.disabled = false;
    }

    function storyElementRendered(element) {
        if (!element || !element.isConnected) return false;
        if (element.closest('.hidden')) return false;
        const rect = element.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    }

    function storyElementVisible(element) {
        return storyElementRendered(element) && !element.disabled;
    }

    function topmostStoryDialog() {
        const dialogs = [...document.querySelectorAll('dialog[open]')];
        return dialogs.length ? dialogs[dialogs.length - 1] : null;
    }

    function storyKeyboardItems() {
        const shortcutModal = $('modal');
        if (shortcutModal?.classList.contains('active')) {
            return [...shortcutModal.querySelectorAll('button:not(:disabled)')]
                .filter(storyElementVisible);
        }
        const dialog = topmostStoryDialog();
        if (dialog) {
            return [...dialog.querySelectorAll(
                '.story-card-choice-select-item:not(:disabled), button:not(:disabled)',
            )].filter(storyElementVisible);
        }
        const selected = selectedCombatCard(activeRun?.state);
        if (
            selected
            && !storyCursorCardMode(selected)
            && !$('story-combat')?.classList.contains('hidden')
        ) {
            const targetKind = cardTargetKind(selected);
            const selector = targetKind === 'enemy'
                ? '.story-actor-enemy.is-play-target[data-target-id]'
                : '#story-player-target';
            return [...document.querySelectorAll(selector)].filter(storyElementVisible);
        }
        return [
            ...document.querySelectorAll(
                '#story-hand .story-card:not(:disabled), '
                + '.story-choice-screen:not(.hidden) .story-choice-option:not(:disabled), '
                + '.story-choice-screen:not(.hidden) .story-card:not(:disabled), '
                + '.story-map-node.is-actionable, '
                + '#story-terminal:not(.hidden) button:not(:disabled), '
                + '#story-empty:not(.hidden) button:not(:disabled)',
            ),
        ].filter(storyElementVisible);
    }

    function clearStoryKeyboardFocus() {
        document.querySelectorAll('.keyboard-nav-focus').forEach((element) => {
            element.classList.remove('keyboard-nav-focus');
        });
        storyKeyboardFocus = null;
        window.GTN_KEYBINDINGS?.refreshHints?.();
    }

    function focusStoryKeyboardItem(element) {
        if (!storyElementVisible(element)) return false;
        clearStoryKeyboardFocus();
        storyKeyboardFocus = element;
        element.classList.add('keyboard-nav-focus');
        try {
            element.focus?.({ preventScroll: true });
        } catch (_) {
            element.focus?.();
        }
        element.scrollIntoView?.({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
        window.GTN_KEYBINDINGS?.refreshHints?.();
        return true;
    }

    function moveStoryKeyboardFocus(delta) {
        const items = storyKeyboardItems();
        if (!items.length) return false;
        let index = items.indexOf(storyKeyboardFocus);
        if (index < 0) index = delta > 0 ? -1 : 0;
        return focusStoryKeyboardItem(items[(index + delta + items.length) % items.length]);
    }

    function activateStoryElement(element) {
        if (!storyElementVisible(element)) return false;
        const actor = element.matches?.('.story-actor[data-target-kind]')
            ? element
            : element.closest?.('.story-actor[data-target-kind]');
        if (actor) {
            const targetKind = String(actor.dataset.targetKind || '');
            const card = selectedCombatCard(activeRun?.state);
            if (card && cardTargetKind(card) === targetKind) {
                if (
                    targetKind === 'enemy'
                    && !storyEnemyIsSelectable(card, actor.dataset.targetId, activeRun?.state)
                ) return false;
                playSelectedCombatCard(targetKind, actor.dataset.targetId || '');
                return true;
            }
            if (!card && targetKind === 'enemy') {
                setStoryPredictionTarget(actor.dataset.targetId || '');
                return true;
            }
            return false;
        }
        element.dispatchEvent(new MouseEvent('click', {
            bubbles: true,
            cancelable: true,
            view: window,
        }));
        return true;
    }

    function storySelectSlot(slot, options = {}) {
        const index = Number(slot) - 1 + ((options.secondPage || storySecondHandPage) ? 10 : 0);
        const context = getStoryShortcutContext();
        const items = Array.isArray(context?.slots) ? context.slots : [];
        if (index < 0 || index >= items.length) return false;
        if (!storyElementVisible(items[index])) return true;
        return activateStoryElement(items[index]);
    }

    function toggleStoryPile(kind) {
        const dialog = $('story-pile-dialog');
        if (dialog?.open && dialog.dataset.pileKind === kind) {
            dialog.close('cancel');
            return true;
        }
        if (document.querySelector('dialog[open]')) return false;
        if (!activeRun?.state?.combat) return false;
        openStoryPile(kind);
        return true;
    }

    function cancelStorySurface() {
        const shortcutModal = $('modal');
        if (shortcutModal?.classList.contains('active')) {
            closeStoryOverlayModal();
            return true;
        }
        const dialog = topmostStoryDialog();
        if (dialog) {
            dialog.close('cancel');
            return true;
        }
        if (developerModeOpen) {
            setDeveloperMode(false);
            return true;
        }
        return cancelStoryCombatSelection(true);
    }

    function confirmStorySurface() {
        const shortcutModal = $('modal');
        if (shortcutModal?.classList.contains('active')) {
            const focused = shortcutModal.querySelector('.keyboard-nav-focus');
            if (focused && activateStoryElement(focused)) return true;
            return activateStoryElement(shortcutModal.querySelector(
                '.modal-buttons .btn-primary:not(:disabled), button:not(:disabled)',
            ));
        }
        const dialog = topmostStoryDialog();
        if (dialog) {
            const focused = dialog.querySelector('.keyboard-nav-focus');
            if (focused && activateStoryElement(focused)) return true;
            const confirm = dialog.querySelector(
                '[value="confirm"]:not(:disabled), .story-command-primary:not(:disabled)',
            );
            return activateStoryElement(confirm);
        }
        if (storyKeyboardFocus && activateStoryElement(storyKeyboardFocus)) return true;
        const card = selectedCombatCard(activeRun?.state);
        if (card && storyCursorCardMode(card)) {
            playSelectedCombatCard(cardTargetKind(card));
            return true;
        }
        const primary = document.querySelector(
            '.story-choice-screen:not(.hidden) .is-primary:not(:disabled), '
            + '#story-terminal:not(.hidden) .story-command-primary:not(:disabled), '
            + '#story-empty:not(.hidden) .story-command-primary:not(:disabled)',
        );
        return activateStoryElement(primary);
    }

    function createStoryShortcutContext(id) {
        return {
            id: String(id || ''),
            slots: [],
            slotLabels: [],
            slotLabel: '',
            actions: [],
        };
    }

    function addStoryShortcutAction(context, id, elements = [], label = '') {
        const actionId = String(id || '');
        if (!actionId) return;
        const targets = [...new Set(
            (Array.isArray(elements) ? elements : [elements]).filter(storyElementVisible),
        )];
        const existing = context.actions.find((action) => action.id === actionId);
        if (existing) {
            existing.elements = [...new Set([...(existing.elements || []), ...targets])];
            if (!existing.label && label) existing.label = String(label);
            return;
        }
        context.actions.push({ id: actionId, elements: targets, label: String(label || '') });
    }

    function addStoryNavigationActions(context, elements, options = {}) {
        const controls = [...new Set((elements || []).filter(storyElementVisible))];
        if (!controls.length) return;
        addStoryShortcutAction(context, 'navigate_left');
        addStoryShortcutAction(context, 'navigate_right');
        addStoryShortcutAction(context, 'navigate_up');
        addStoryShortcutAction(context, 'navigate_down');
        addStoryShortcutAction(context, 'confirm');
        if (options.toggle) addStoryShortcutAction(context, 'toggle_focused');
    }

    function finalizeStoryShortcutContext(context) {
        if (
            storyKeyboardFocus
            && storyElementVisible(storyKeyboardFocus)
            && storyKeyboardItems().includes(storyKeyboardFocus)
        ) {
            addStoryShortcutAction(context, 'confirm', [storyKeyboardFocus]);
            if (context.actions.some((action) => action.id === 'toggle_focused')) {
                addStoryShortcutAction(context, 'toggle_focused', [storyKeyboardFocus]);
            }
        }
        const chatControl = storyChatOpen ? $('story-chat-input') : $('story-chat-toggle');
        if (storyElementVisible(chatControl)) {
            addStoryShortcutAction(context, 'focus_chat', [chatControl]);
        }
        addStoryShortcutAction(context, 'shortcut_help');
        return context;
    }

    function getStoryShortcutContext() {
        const shortcutModal = $('modal');
        if (shortcutModal?.classList.contains('active') && storyElementVisible(shortcutModal)) {
            const context = createStoryShortcutContext('story-shortcut-help');
            const buttons = [...shortcutModal.querySelectorAll('button:not(:disabled)')]
                .filter(storyElementVisible);
            addStoryNavigationActions(context, buttons);
            if (buttons.length) {
                addStoryShortcutAction(context, 'confirm', buttons);
                addStoryShortcutAction(context, 'cancel', buttons);
            }
            return finalizeStoryShortcutContext(context);
        }
        const dialog = topmostStoryDialog();
        if (dialog) {
            const context = createStoryShortcutContext(`dialog-${dialog.id || 'story'}`);
            const choices = [...dialog.querySelectorAll(
                '.story-card-choice-select-item',
            )].filter(storyElementRendered);
            context.slots = choices.slice(0, 20);
            context.slotLabel = t.chooseCard || '选择卡牌';
            addStoryNavigationActions(context, storyKeyboardItems(), { toggle: choices.length > 0 });
            const confirm = dialog.querySelector(
                '[value="confirm"]:not(:disabled), .story-command-primary:not(:disabled)',
            );
            const cancel = dialog.querySelector(
                '[value="cancel"]:not(:disabled), .story-pile-close:not(:disabled)',
            );
            if (storyElementVisible(confirm)) addStoryShortcutAction(context, 'confirm', [confirm]);
            if (storyElementVisible(cancel)) addStoryShortcutAction(context, 'cancel', [cancel]);
            if (dialog.id === 'story-pile-dialog') {
                const pileKind = String(dialog.dataset.pileKind || '');
                const actionId = { draw: 'view_draw', discard: 'view_discard', exile: 'view_exile' }[pileKind];
                if (actionId) addStoryShortcutAction(context, actionId, cancel ? [cancel] : []);
            }
            return finalizeStoryShortcutContext(context);
        }

        const combat = $('story-combat');
        if (combat && !combat.classList.contains('hidden')) {
            const context = createStoryShortcutContext('story-combat');
            const hand = [...document.querySelectorAll(
                '#story-hand .story-card',
            )].filter(storyElementRendered);
            context.slots = hand.slice(0, 20);
            context.slotLabel = t.hand || '手牌';
            const card = selectedCombatCard(activeRun?.state);
            if (card && !storyCursorCardMode(card)) {
                const targetKind = cardTargetKind(card);
                if (targetKind === 'self') {
                    addStoryShortcutAction(context, 'target_self', [$('story-player-target')]);
                } else {
                    const enemies = selectableStoryEnemies(card);
                    const enemyElements = [...document.querySelectorAll(
                        '.story-actor-enemy.is-play-target[data-target-id]',
                    )].filter(storyElementVisible);
                    if (enemies[0] && enemyElements[0]) {
                        addStoryShortcutAction(context, 'target_enemy', [enemyElements[0]]);
                    }
                    if (enemies[1] && enemyElements[1]) {
                        addStoryShortcutAction(context, 'target_enemy_2', [enemyElements[1]]);
                    }
                }
                addStoryNavigationActions(context, storyKeyboardItems());
                addStoryShortcutAction(context, 'cancel');
                return finalizeStoryShortcutContext(context);
            }

            addStoryNavigationActions(context, hand.filter(storyElementVisible));
            if (card) addStoryShortcutAction(context, 'cancel');
            const endTurn = $('story-end-turn');
            if (storyElementVisible(endTurn)) addStoryShortcutAction(context, 'end_turn', [endTurn]);
            [
                ['view_draw', $('story-draw-pile')],
                ['view_discard', $('story-discard-pile')],
                ['view_exile', $('story-exile-pile')],
            ].forEach(([actionId, element]) => {
                if (storyElementVisible(element)) addStoryShortcutAction(context, actionId, [element]);
            });
            addStoryShortcutAction(context, 'refresh');
            return finalizeStoryShortcutContext(context);
        }

        const context = createStoryShortcutContext('story-page');
        const choices = [...document.querySelectorAll(
            '.story-choice-screen:not(.hidden) .story-choice-option, '
            + '.story-choice-screen:not(.hidden) .story-card, '
            + '#story-run:not(.hidden) .story-map-node.is-actionable',
        )].filter(storyElementRendered);
        context.slots = choices.slice(0, 20);
        context.slotLabel = t.choose || '选择';
        const controls = storyKeyboardItems();
        addStoryNavigationActions(context, controls);
        const primary = document.querySelector(
            '.story-choice-screen:not(.hidden) .is-primary:not(:disabled), '
            + '#story-terminal:not(.hidden) .story-command-primary:not(:disabled), '
            + '#story-empty:not(.hidden) .story-command-primary:not(:disabled)',
        );
        if (storyElementVisible(primary)) addStoryShortcutAction(context, 'confirm', [primary]);
        if (developerModeOpen) addStoryShortcutAction(context, 'cancel', [$('story-dev-close')]);
        addStoryShortcutAction(context, 'refresh');
        return finalizeStoryShortcutContext(context);
    }

    function dispatchStoryShortcut(actionId, event = null, options = {}) {
        const slotMatch = /^select_slot_(\d+)$/.exec(String(actionId || ''));
        if (slotMatch) return storySelectSlot(Number(slotMatch[1]), options);
        if (
            actionId !== 'hand_second_page'
            && !getStoryShortcutContext().actions.some((action) => action.id === actionId)
        ) {
            return false;
        }
        switch (actionId) {
        case 'hand_second_page':
            storySecondHandPage = options.active !== false;
            return true;
        case 'confirm':
        case 'toggle_focused':
            return confirmStorySurface();
        case 'cancel':
            return cancelStorySurface();
        case 'refresh':
            loadRun();
            return true;
        case 'navigate_left':
        case 'navigate_up':
            return moveStoryKeyboardFocus(-1);
        case 'navigate_right':
        case 'navigate_down':
            return moveStoryKeyboardFocus(1);
        case 'target_self': {
            const card = selectedCombatCard(activeRun?.state);
            if (!card || cardTargetKind(card) !== 'self') return false;
            playSelectedCombatCard('self');
            return true;
        }
        case 'target_enemy':
        case 'target_enemy_2': {
            const card = selectedCombatCard(activeRun?.state);
            const enemies = card
                ? selectableStoryEnemies(card)
                : livingStoryEnemies();
            const index = actionId === 'target_enemy_2' ? 1 : 0;
            const enemy = enemies[index];
            if (!enemy) return false;
            if (!card) {
                setStoryPredictionTarget(enemy.id);
                return true;
            }
            if (cardTargetKind(card) !== 'enemy') return false;
            playSelectedCombatCard('enemy', enemy.id);
            return true;
        }
        case 'end_turn': {
            const button = $('story-end-turn');
            return activateStoryElement(button);
        }
        case 'view_draw':
            return toggleStoryPile('draw');
        case 'view_discard':
            return toggleStoryPile('discard');
        case 'view_exile':
            return toggleStoryPile('exile');
        case 'focus_chat': {
            const input = $('story-chat-input');
            if (storyChatOpen && input && document.activeElement === input) return false;
            setStoryChatOpen(!storyChatOpen);
            return true;
        }
        case 'shortcut_help':
            window.GTN_KEYBINDINGS?.showHelp?.();
            return true;
        default:
            return false;
        }
    }

    window.GTN_SHORTCUT_HOST = {
        dispatch: dispatchStoryShortcut,
        getShortcutContext: getStoryShortcutContext,
        hasVirtualFocus() {
            return Boolean(storyKeyboardFocus?.isConnected);
        },
        getAccount() {
            return window.__STORY_ACCOUNT__ || null;
        },
        getLang() {
            return lang;
        },
        isTypingTarget(target) {
            return Boolean(target?.closest?.('input, textarea, select, [contenteditable="true"]'));
        },
        confirm(title, message) {
            return Promise.resolve(window.confirm([title, message].filter(Boolean).join('\n\n')));
        },
        toast(message) {
            showToast(message);
        },
        patchAccountKeybindings(config) {
            if (!window.__STORY_ACCOUNT__ || !config || typeof config !== 'object') return;
            window.__STORY_ACCOUNT__ = { ...window.__STORY_ACCOUNT__, keybindings: config };
        },
    };

    function bind() {
        bindStoryAfkActivityReporting();
        const storyApp = $('story-app');
        $('story-chat-toggle')?.addEventListener('click', () => setStoryChatOpen(true));
        $('story-chat-close')?.addEventListener('click', () => setStoryChatOpen(false));
        $('story-chat-send')?.addEventListener('click', sendStoryChat);
        $('story-chat-input')?.addEventListener('input', () => {
            updateStoryChatConnectionUi();
            updateStoryMentionMenu();
        });
        $('story-chat-input')?.addEventListener('focus', () => {
            clearStoryMentionFlash();
            updateStoryMentionMenu();
        });
        $('story-chat-input')?.addEventListener('blur', () => {
            setTimeout(() => storyMentionMenu?.classList.add('hidden'), 120);
        });
        $('story-chat-input')?.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && storyMentionMenu && !storyMentionMenu.classList.contains('hidden')) {
                event.preventDefault();
                event.stopPropagation();
                storyMentionMenu.classList.add('hidden');
                return;
            }
            if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return;
            event.preventDefault();
            if (storyMentionMenu && !storyMentionMenu.classList.contains('hidden') && storyMentionCandidates[0]) {
                insertStoryMention(storyMentionCandidates[0]);
                return;
            }
            sendStoryChat();
        });
        storyApp?.addEventListener('selectstart', (event) => {
            if (event.target?.closest?.('input, textarea, select, [contenteditable="true"]')) return;
            event.preventDefault();
        });
        storyApp?.addEventListener('dragstart', (event) => {
            if (event.target?.closest?.('img')) event.preventDefault();
        });
        $('story-start')?.addEventListener('click', startRun);
        $('story-end-turn')?.addEventListener('click', () => storyAction('end_turn'));
        $('story-codex-open')?.addEventListener('click', openStoryCodex);
        $('story-codex-close')?.addEventListener('click', closeStoryCodex);
        $('story-codex-dialog')?.addEventListener('click', (event) => {
            if (event.target === event.currentTarget) closeStoryCodex();
        });
        document.querySelectorAll('[data-story-codex-mode]').forEach((tab) => {
            tab.addEventListener('click', () => {
                storyCodexMode = String(tab.dataset.storyCodexMode || 'cards');
                storyCodexSelectedId = '';
                storyCodexSearch = '';
                const input = $('story-codex-search');
                if (input) input.value = '';
                renderStoryCodex();
            });
            tab.addEventListener('keydown', (event) => {
                if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
                const tabs = [...document.querySelectorAll('[data-story-codex-mode]')];
                const index = tabs.indexOf(tab);
                if (index < 0) return;
                event.preventDefault();
                let next = index;
                if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
                else if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
                else if (event.key === 'Home') next = 0;
                else next = tabs.length - 1;
                tabs[next]?.click();
                tabs[next]?.focus();
            });
        });
        $('story-codex-search')?.addEventListener('input', (event) => {
            storyCodexSearch = String(event.target?.value || '');
            storyCodexSelectedId = '';
            renderStoryCodex();
        });
        $('story-talent-overview')?.addEventListener('click', openStoryTalentOverview);
        $('story-run-deck')?.addEventListener('click', () => openStoryPile('deck'));
        $('story-draw-pile')?.addEventListener('click', () => openStoryPile('draw'));
        $('story-discard-pile')?.addEventListener('click', () => openStoryPile('discard'));
        $('story-exile-pile')?.addEventListener('click', () => openStoryPile('exile'));
        $('story-combat-map')?.addEventListener('click', openStoryCombatMap);
        $('story-map-return')?.addEventListener('click', returnToStoryCombat);
        $('story-player-target')?.addEventListener('click', (event) => {
            if (event.target?.closest?.('.story-portrait')) playSelectedCombatCard('self');
        });
        $('story-enemy-group')?.addEventListener('click', (event) => {
            const actor = event.target?.closest?.('.story-actor-enemy[data-target-id]');
            if (actor && event.target?.closest?.('.story-portrait')) {
                playSelectedCombatCard('enemy', actor.dataset.targetId || '');
            }
        });
        $('story-combat')?.addEventListener('click', (event) => {
            const card = selectedCombatCard(activeRun?.state);
            const cursorMode = storyCursorCardMode(card);
            if (!card || !cursorMode || cardPlayInFlight || actionInFlight) return;
            const hand = event.target?.closest?.('#story-hand');
            if (hand) {
                if (!event.target?.closest?.('.story-hand-card')) {
                    event.preventDefault();
                    event.stopImmediatePropagation();
                    returnStoryCursorCard(() => {
                        selectedCombatCardId = '';
                        renderCombat(activeRun.state);
                    });
                }
                return;
            }
            event.preventDefault();
            event.stopImmediatePropagation();
            playSelectedCombatCard(cardTargetKind(card));
        }, true);
        $('story-card-choice-dialog')?.addEventListener('cancel', (event) => {
            if (event.currentTarget.dataset.required === '1') event.preventDefault();
        });
        $('story-card-choice-dialog')?.addEventListener('close', (event) => {
            const context = cardChoiceContext;
            cardChoiceContext = null;
            if (!context) return;
            const selected = [...context.selected];
            if (context.mode === 'deck_operation') {
                if (event.target.returnValue !== 'confirm') {
                    requestAnimationFrame(() => openPendingStoryDeckOperation(activeRun?.state));
                    return;
                }
                if (
                    selected.length < context.spec.minimum
                    || selected.length > context.spec.maximum
                ) {
                    requestAnimationFrame(() => openPendingStoryDeckOperation(activeRun?.state));
                    return;
                }
                setStoryCardChoiceRequired(false);
                storyAction('resolve_deck_operation', { selected_card_ids: selected });
                return;
            }
            if (context.mode === 'pending_card') {
                if (
                    event.target.returnValue !== 'confirm'
                    || selected.length < context.spec.minimum
                    || selected.length > context.spec.maximum
                ) {
                    requestAnimationFrame(() => openPendingStoryCardChoice(activeRun?.state));
                    return;
                }
                setStoryCardChoiceRequired(false);
                storyAction('resolve_card_choice', { selected_card_ids: selected });
                return;
            }
            setStoryCardChoiceRequired(false);
            if (context.mode === 'opening_redraw') {
                storyAction('opening_redraw', {
                    selected_card_ids: event.target.returnValue === 'confirm' ? selected : [],
                });
                return;
            }
            if (event.target.returnValue !== 'confirm') return;
            if (selected.length < context.spec.minimum || selected.length > context.spec.maximum) return;
            performSelectedCombatCard(context.targetKind, context.targetId, {
                [context.spec.payloadKey]: selected,
            });
        });
        $('story-deck-change-dialog')?.addEventListener('close', (event) => {
            const pending = pendingStoryDeckChange;
            pendingStoryDeckChange = null;
            if (!pending || event.target.returnValue !== 'confirm') return;
            storyAction(pending.actionType, pending.payload);
        });
        $('story-event-confirm-dialog')?.addEventListener('close', (event) => {
            const pending = pendingStoryEventAction;
            pendingStoryEventAction = null;
            if (!pending || event.target.returnValue !== 'confirm') return;
            pending();
        });
        $('story-reward-skip')?.addEventListener('click', () => storyAction('choose_reward', {
            reward_type: 'card',
        }));
        $('story-reward-leave')?.addEventListener('click', () => storyAction('choose_reward', {
            reward_type: 'leave',
        }));
        $('story-reward-continue')?.addEventListener('click', () => storyAction('choose_reward', {
            reward_type: 'continue',
        }));
        $('story-terminal-new')?.addEventListener('click', startNewJourney);
        $('story-surrender')?.addEventListener('click', () => {
            if (actionInFlight || !activeRun) return;
            $('story-surrender-dialog')?.showModal();
        });
        $('story-surrender-dialog')?.addEventListener('close', (event) => {
            if (event.target.returnValue !== 'confirm') return;
            selectedCombatCardId = '';
            cardChoiceContext = null;
            pendingStoryDeckChange = null;
            pendingStoryEventAction = null;
            ['story-card-choice-dialog', 'story-deck-change-dialog', 'story-event-confirm-dialog'].forEach((id) => {
                const dialog = $(id);
                if (dialog?.open) dialog.close('cancel');
            });
            storyAction('surrender');
        });
        $('story-dev-toggle')?.addEventListener('click', () => setDeveloperMode(!developerModeOpen));
        $('story-dev-close')?.addEventListener('click', () => setDeveloperMode(false));
        $('story-dev-floor')?.addEventListener('change', () => renderDeveloperNodes(activeRun?.state || null));
        $('story-dev-jump')?.addEventListener('click', jumpDeveloperNode);
        $('story-dev-apply')?.addEventListener('click', applyDeveloperValues);
        $('story-reset-map')?.addEventListener('click', () => $('story-reset-dialog')?.showModal());
        $('story-reset-dialog')?.addEventListener('close', (event) => {
            if (event.target.returnValue === 'confirm') resetMap();
        });
        $('story-save-open')?.addEventListener('click', openManualStorySaves);
        $('story-save-open-global')?.addEventListener('click', openManualStorySaves);
        $('story-save-create')?.addEventListener('click', createManualStorySave);
        $('story-restart-floor')?.addEventListener('click', () => {
            $('story-restart-floor-dialog')?.showModal();
        });
        $('story-restart-floor-dialog')?.addEventListener('close', (event) => {
            if (event.target.returnValue === 'confirm') restartStoryFloor();
        });
        $('story-save-dialog')?.addEventListener('close', () => {
            pendingStorySaveId = 0;
        });
        $('story-save-load-dialog')?.addEventListener('close', (event) => {
            const saveId = pendingStorySaveId;
            pendingStorySaveId = 0;
            if (event.target.returnValue === 'confirm') loadManualStorySave(saveId);
        });
        $('story-save-delete-dialog')?.addEventListener('close', (event) => {
            const saveId = pendingStorySaveId;
            pendingStorySaveId = 0;
            if (event.target.returnValue === 'confirm') deleteManualStorySave(saveId);
        });
        $('modal')?.addEventListener('click', (event) => {
            if (event.target !== event.currentTarget) return;
            closeStoryOverlayModal();
        });
        $('story-term-dialog')?.addEventListener('click', (event) => {
            if (event.target === event.currentTarget) closeStoryCardTerms();
        });
        $('story-term-dialog')?.addEventListener('close', (event) => {
            delete event.currentTarget.dataset.storyTermKey;
            delete event.currentTarget.dataset.storyTermUpgrade;
        });
        const moveAim = (event) => {
            storyAimPointer = { x: event.clientX, y: event.clientY };
            updateStorySkinEyeTracking(event.clientX, event.clientY);
            positionStoryCursorCard(event.clientX, event.clientY);
            if (selectedCombatCardId) scheduleStoryAimUpdate();
        };
        document.addEventListener('mousemove', moveAim);
        document.addEventListener('pointermove', moveAim);
        window.addEventListener('resize', () => {
            scheduleStoryAimUpdate();
            scheduleVisibleStoryCardEffectFits();
        });
        window.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && storyChatOpen) {
                event.preventDefault();
                setStoryChatOpen(false);
                return;
            }
            if (event.key === 'Escape' && developerModeOpen) {
                event.preventDefault();
                setDeveloperMode(false);
                return;
            }
            if (event.key !== 'Escape' || !selectedCombatCardId || !activeRun?.state) return;
            event.preventDefault();
            cancelStoryCombatSelection(true);
        });
        document.addEventListener('contextmenu', (event) => {
            event.preventDefault();
            const cardChoiceDialog = $('story-card-choice-dialog');
            if (cardChoiceDialog?.open) {
                event.stopImmediatePropagation();
                if (cardChoiceDialog.dataset.required !== '1') {
                    cardChoiceDialog.close('cancel');
                }
                return;
            }
            if ($('story-term-dialog')?.open) {
                event.stopImmediatePropagation();
                closeStoryCardTerms();
                return;
            }
            if (selectedCombatCardId && activeRun?.state) {
                event.stopImmediatePropagation();
                cancelStoryCombatSelection(true);
                return;
            }
            const statusElement = event.target?.closest?.('[data-story-status-key]');
            if (statusElement) {
                if (statusElement.dataset.storyTermLongPress === '1') {
                    delete statusElement.dataset.storyTermLongPress;
                    return;
                }
                openStoryStatusTerms(statusElement.dataset.storyStatusKey);
                return;
            }
            const traitElement = event.target?.closest?.('[data-story-trait-key]');
            if (traitElement) {
                if (traitElement.dataset.storyTermLongPress === '1') {
                    delete traitElement.dataset.storyTermLongPress;
                    return;
                }
                openStoryTraitTerms(traitElement.dataset.storyTraitKey);
                return;
            }
            const cardElement = event.target?.closest?.(
                '.story-card.card, .story-pile-tile, .story-event-card-chip',
            );
            const equipmentElement = event.target?.closest?.('.story-equipment');
            const cardSourceElement = cardElement || equipmentElement;
            if (cardSourceElement?.dataset.storyBlind === '1') return;
            const card = cardSourceElement ? storyCardElementData.get(cardSourceElement) : null;
            if (card) {
                const termOptions = storyCardTermOptions.get(cardSourceElement);
                if (termOptions) openStoryCardTerms(card, termOptions);
                else openStoryCardTerms(card);
                return;
            }
        });
    }

    loadStoryMainFont();
    applyText();
    renderPlayerSkin();
    bind();
    startStoryChat();
    startStoryPresence();
    loadRun();
})();
