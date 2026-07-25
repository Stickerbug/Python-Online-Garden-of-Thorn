(() => {
    'use strict';

    const $ = (id) => document.getElementById(id);
    const SVG_NS = 'http://www.w3.org/2000/svg';
    const VIEWS = [
        'story-loading', 'story-empty', 'story-blessing', 'story-run',
        'story-combat', 'story-room', 'story-reward', 'story-terminal',
    ];
    let activeRun = null;
    let storyContent = null;
    let contentVersion = '';
    let actionInFlight = false;
    let selectedCombatCardId = '';
    let cardPlayInFlight = false;
    let storyAimPointer = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    let storyAimFrame = 0;
    let storyCursorCard = null;
    let toastTimer = null;
    let developerModeOpen = false;
    let cardChoiceContext = null;

    const TEXT = {
        en: {
            title: 'Story Mode', account: 'Player', back: 'Back', loading: 'Loading journey',
            emptyTitle: 'A new journey', start: 'Start', stage: 'Stage', biome: 'Region', gold: 'Gold',
            route: 'Route', abandon: 'End Journey', abandonTitle: 'End this journey?',
            abandonMessage: 'This run will be marked as ended.', resetMap: 'Reset Map',
            resetTitle: 'Reset the map?', resetMessage: 'A new route will be generated from Floor 1.',
            mapReset: 'Map reset', cancel: 'Cancel', confirm: 'Confirm', garden: 'Garden',
            blessingTitle: 'Choose a starting blessing', blessingCopy: 'Choose one for this journey.',
            intent: 'Intent', endTurn: 'End Turn', playerTurn: 'Your Turn', enemyTurn: 'Enemy Turn', close: 'Close',
            drawPile: 'Draw', discardPile: 'Discard', exilePile: 'Exile',
            battleWon: 'Battle won', chooseCard: 'Choose a card', skip: 'Skip',
            gainedGold: (value) => `Gained ${value} G.`, room: 'Room', restTitle: 'Rest Site',
            restCopy: 'Recover H or upgrade one card.', heal: 'Recover H', upgrade: 'Upgrade',
            chestTitle: 'Chest', chestCopy: 'Open the chest and continue.', openChest: 'Open',
            eventTitle: 'Garden Event', eventCopy: 'Choose one outcome.', takeGold: 'Take 20 Gold',
            recoverHealth: 'Recover 15 H', shopTitle: 'Shop', shopCopy: 'Spend Gold or leave.',
            buy: (value) => `Buy · ${value}`, leave: 'Leave', journeyComplete: 'Journey complete',
            journeyCompleteCopy: 'You crossed the Garden route.', journeyFailed: 'Journey ended',
            journeyFailedCopy: 'Your route ends here, but the next map is waiting.', newJourney: 'New Journey',
            requestFailed: 'Story data is temporarily unavailable', stateUpdated: 'State synchronized',
            upgraded: 'Upgraded', shield: 'Shield', power: 'Power', weak: 'Weak', vulnerable: 'Vulnerable',
            developerMode: 'Developer Mode', devJump: 'Jump to Level', devFloor: 'Floor', devRoom: 'Room',
            devValues: 'Set Values', devApply: 'Apply Values', devJumpButton: 'Jump',
            devValuesUpdated: 'Values updated', devJumped: 'Level loaded',
            pileEmpty: 'No cards here', chooseEnemy: 'Choose the enemy', chooseSelf: 'Choose yourself',
            playSelfAnywhere: 'Click anywhere to play on yourself', playAnywhere: 'Click anywhere to play',
            chooseCardHint: 'Choose a card', damagePrediction: 'Damage',
            chooseCards: 'Choose cards', chooseExact: (value) => `Choose ${value} card(s).`,
            chooseUpTo: (value) => `Choose up to ${value} card(s).`,
            cardTypes: { thorn: 'Thorn', bloom: 'Bloom', root: 'Root', guard: 'Guard', curse: 'Curse', infect: 'Infect' },
            pileTotal: (label, count) => `${label}: ${count} cards`,
            floor: (value) => `Floor ${value}`,
            rooms: { blessing: 'Blessing', combat: 'Battle', elite: 'Elite', event: 'Event', rest: 'Rest', shop: 'Shop', chest: 'Chest', boss: 'Boss' },
            roomMarks: { blessing: 'B', combat: 'C', elite: 'E', event: '?', rest: 'R', shop: '$', chest: 'T', boss: 'X' },
        },
        zh: {
            title: '故事模式', account: '玩家', back: '返回', loading: '载入旅程', emptyTitle: '一段新的旅程',
            start: '开始', stage: '阶段', biome: '区域', gold: '金币', route: '路线', abandon: '结束旅程',
            abandonTitle: '结束旅程？', abandonMessage: '当前进度将被记录为已结束。', resetMap: '重置地图',
            resetTitle: '重置地图？', resetMessage: '将重新生成路线并返回第一层。', mapReset: '地图已重置',
            cancel: '取消', confirm: '确定', garden: '花园', blessingTitle: '选择初始赐福',
            blessingCopy: '本次旅程只能选择一项。', intent: '意图', endTurn: '结束回合', playerTurn: '玩家回合', enemyTurn: '敌方回合', close: '关闭', drawPile: '抽牌堆',
            discardPile: '弃牌堆', exilePile: '放逐区', battleWon: '战斗胜利', chooseCard: '选择一张牌',
            skip: '跳过', gainedGold: (value) => `获得 ${value}G。`, room: '房间', restTitle: '休息区',
            restCopy: '回复生命，或升级一张牌。', heal: '回复生命', upgrade: '升级', chestTitle: '宝箱',
            chestCopy: '打开宝箱后继续前进。', openChest: '打开', eventTitle: '花园事件',
            eventCopy: '选择一种结果。', takeGold: '获得20金币', recoverHealth: '回复15H', shopTitle: '商店',
            shopCopy: '消耗金币购买物品，也可以直接离开。', buy: (value) => `购买 · ${value}`, leave: '离开',
            journeyComplete: '旅程完成', journeyCompleteCopy: '你已经穿过了花园路线。', journeyFailed: '旅程结束',
            journeyFailedCopy: '本次路线止步于此，下一张地图仍在等待。', newJourney: '开始新旅程',
            requestFailed: '故事记录暂时不可用', stateUpdated: '状态已同步', upgraded: '已升级',
            shield: '护盾', power: '力量', weak: '虚弱', vulnerable: '易损', floor: (value) => `第 ${value} 层`,
            developerMode: '开发人员模式', devJump: '关卡跳转', devFloor: '层数', devRoom: '房间',
            devValues: '数值设置', devApply: '应用数值', devJumpButton: '跳转',
            devValuesUpdated: '数值已更新', devJumped: '已载入所选关卡',
            pileEmpty: '这里没有牌', chooseEnemy: '点击敌方头像以选择目标', chooseSelf: '点击自己的头像以选择目标',
            playSelfAnywhere: '点击场地任意位置对自己使用', playAnywhere: '点击场地任意位置打出',
            chooseCardHint: '选择一张手牌', damagePrediction: '伤害预测',
            chooseCards: '选择卡牌', chooseExact: (value) => `选择 ${value} 张牌。`,
            chooseUpTo: (value) => `选择至多 ${value} 张牌。`,
            cardTypes: { thorn: '攻击', bloom: '技能', root: '装备', guard: '反制', curse: '诅咒', infect: '状态牌' },
            pileTotal: (label, count) => `${label}：${count} 张`,
            rooms: { blessing: '赐福', combat: '战斗', elite: '精英', event: '事件', rest: '休息', shop: '商店', chest: '宝箱', boss: '首领' },
            roomMarks: { blessing: '赐', combat: '战', elite: '精', event: '事', rest: '息', shop: '店', chest: '宝', boss: '首' },
        },
        fr: {
            title: 'Mode histoire', account: 'Joueur', back: 'Retour', loading: 'Chargement du voyage',
            emptyTitle: 'Un nouveau voyage', start: 'Commencer', stage: 'Étape', biome: 'Région', gold: 'Or',
            route: 'Route', abandon: 'Terminer le voyage', blessingTitle: 'Choisir une bénédiction',
            blessingCopy: 'Choisissez-en une pour ce voyage.', intent: 'Intention', endTurn: 'Fin du tour',
            drawPile: 'Pioche', discardPile: 'Défausse', exilePile: 'Exil', battleWon: 'Victoire',
            chooseCard: 'Choisissez une carte', skip: 'Passer', room: 'Salle', newJourney: 'Nouveau voyage',
            developerMode: 'Mode développeur', devJump: 'Changer de niveau', devFloor: 'Étage', devRoom: 'Salle',
            devValues: 'Modifier les valeurs', devApply: 'Appliquer', devJumpButton: 'Aller',
            devValuesUpdated: 'Valeurs mises à jour', devJumped: 'Niveau chargé',
            garden: 'Jardin', floor: (value) => `Étage ${value}`,
            rooms: { blessing: 'Bénédiction', combat: 'Combat', elite: 'Élite', event: 'Événement', rest: 'Repos', shop: 'Boutique', chest: 'Coffre', boss: 'Boss' },
            roomMarks: { blessing: 'B', combat: 'C', elite: 'É', event: '?', rest: 'R', shop: '$', chest: 'T', boss: 'X' },
        },
        ja: {
            title: 'ストーリーモード', account: 'プレイヤー', back: '戻る', loading: '旅を読み込み中',
            emptyTitle: '新しい旅', start: '開始', stage: 'ステージ', biome: '地域', gold: 'ゴールド',
            route: 'ルート', abandon: '旅を終了', blessingTitle: '祝福を選択', blessingCopy: '今回の旅で一つ選択します。',
            intent: '意図', endTurn: 'ターン終了', drawPile: '山札', discardPile: '捨て札', exilePile: '追放',
            battleWon: '戦闘勝利', chooseCard: 'カードを選択', skip: 'スキップ', room: '部屋',
            developerMode: '開発者モード', devJump: 'ステージ移動', devFloor: '階', devRoom: '部屋',
            devValues: '数値設定', devApply: '適用', devJumpButton: '移動',
            devValuesUpdated: '数値を更新しました', devJumped: 'ステージを読み込みました',
            newJourney: '新しい旅', garden: 'ガーデン', floor: (value) => `${value}階`,
            rooms: { blessing: '祝福', combat: '戦闘', elite: 'エリート', event: 'イベント', rest: '休憩', shop: 'ショップ', chest: '宝箱', boss: 'ボス' },
            roomMarks: { blessing: '祝', combat: '戦', elite: '精', event: '？', rest: '休', shop: '店', chest: '宝', boss: '首' },
        },
    };

    function language() {
        let value = 'zh';
        try { value = String(localStorage.getItem('gtn_lang') || 'zh').toLowerCase(); } catch (_) {}
        return Object.prototype.hasOwnProperty.call(TEXT, value) ? value : 'zh';
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

    function renderPlayerSkin() {
        const portrait = $('story-player-portrait');
        if (!portrait) return;
        const skin = normalizeSkin(window.__STORY_ACCOUNT__?.skin);
        const avatar = document.createElement('div');
        avatar.className = `skin-avatar skin-eye-shape-${skin.eyeShape}${skinIsDark(skin.primaryColor) ? ' is-inverted' : ''}`;
        avatar.style.setProperty('--skin-main', skin.primaryColor);
        avatar.style.setProperty('--skin-border', skinBorderColor(skin.primaryColor));
        avatar.innerHTML = `
            <div class="skin-eye skin-eye-left"><span class="skin-pupil"></span></div>
            <div class="skin-eye skin-eye-right"><span class="skin-pupil"></span></div>
            <svg class="skin-mouth" viewBox="0 0 100 56" aria-hidden="true" focusable="false">
                <path class="skin-mouth-line" d="M 20 18 C 36 32 64 32 80 18"></path>
            </svg>
        `;
        portrait.replaceChildren(avatar);
    }

    function applyText() {
        document.documentElement.lang = lang === 'zh' ? 'zh-CN' : lang;
        document.title = `${t.title} | Garden of Thorn`;
        const values = {
            'story-title': t.title, 'story-account-label': t.account, 'story-loading-label': t.loading,
            'story-empty-title': t.emptyTitle, 'story-start': t.start, 'story-stage-label': t.stage,
            'story-biome-label': t.biome, 'story-gold-label': t.gold, 'story-map-title': t.route,
            'story-reset-map': t.resetMap,
            'story-reset-title': t.resetTitle, 'story-reset-message': t.resetMessage,
            'story-reset-cancel': t.cancel, 'story-reset-confirm': t.confirm,
            'story-blessing-title': t.blessingTitle, 'story-blessing-copy': t.blessingCopy,
            'story-intent-label': t.intent, 'story-end-turn': t.endTurn,
            'story-pile-close': t.close,
            'story-reward-skip': t.skip, 'story-terminal-new': t.newJourney,
            'story-dev-toggle': t.developerMode, 'story-dev-title': t.developerMode,
            'story-dev-jump-label': t.devJump, 'story-dev-floor-label': t.devFloor,
            'story-dev-node-label': t.devRoom, 'story-dev-values-label': t.devValues,
            'story-dev-jump': t.devJumpButton, 'story-dev-apply': t.devApply,
            'story-dev-gold-label': t.gold,
        };
        Object.entries(values).forEach(([id, value]) => setText(id, value));
        const back = $('story-back');
        if (back) {
            back.title = t.back;
            back.setAttribute('aria-label', t.back);
        }
        const devClose = $('story-dev-close');
        if (devClose) devClose.setAttribute('aria-label', t.close);
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
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 10000);
        try {
            const response = await fetch(url, {
                credentials: 'same-origin',
                ...options,
                headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
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

    function showView(name) {
        VIEWS.forEach((id) => $(id)?.classList.toggle('hidden', id !== name));
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

    async function animateEnemyLunge() {
        await waitForStoryAnimation($('story-enemy-group'), 'is-lunging', 420);
    }

    async function animateEnemyGain() {
        const group = $('story-enemy-group');
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

    async function playEnemyEventSequence(events, nextRun) {
        const sequence = Array.isArray(events) ? events : [];
        const relevant = sequence.filter((event) => (
            event?.type === 'player_damage'
            || (event?.type === 'enemy_gain' && Number(event.amount) > 0)
        ));
        if (!relevant.length || !$('story-enemy-group') || $('story-combat')?.classList.contains('hidden')) return;

        selectedCombatCardId = '';
        $('story-aim-layer')?.classList.add('hidden');
        $('story-player-target')?.classList.remove('is-play-target', 'is-aim-hover');
        $('story-enemy-target')?.classList.remove('is-play-target', 'is-aim-hover');
        $('story-hand')?.replaceChildren();
        setText('story-play-hint', '');
        setText('story-phase', t.enemyTurn);
        const endTurn = $('story-end-turn');
        if (endTurn) endTurn.disabled = true;
        document.body.dataset.enemyAnimating = 'true';

        try {
            for (const event of relevant) {
                if (event.type === 'player_damage') {
                    await animateEnemyLunge();
                    const history = Array.isArray(event.history) ? event.history : [];
                    const finalHit = history[history.length - 1];
                    if (finalHit && Number.isFinite(Number(finalHit.after))) {
                        setHealthBar(
                            'story-combat-player',
                            Number(finalHit.after),
                            nextRun?.state?.player?.max_health || activeRun?.state?.player?.max_health,
                        );
                    }
                } else if (event.type === 'enemy_gain') {
                    await animateEnemyGain();
                }
                await new Promise((resolve) => window.setTimeout(resolve, 45));
            }
        } finally {
            delete document.body.dataset.enemyAnimating;
        }
    }

    async function storyAction(actionType, payload = {}) {
        if (!activeRun || actionInFlight) return null;
        actionInFlight = true;
        document.body.dataset.actionInFlight = 'true';
        try {
            const result = await requestJson('/api/story/run/action', {
                method: 'POST',
                body: JSON.stringify({
                    run_id: activeRun.id,
                    state_version: activeRun.state_version,
                    action_id: createActionId(),
                    action_type: actionType,
                    payload,
                }),
            });
            const nextRun = result.run || activeRun;
            if (actionType === 'end_turn') await playEnemyEventSequence(result.events, nextRun);
            renderRun(nextRun);
            return result;
        } catch (error) {
            if (error.message === 'AUTH_REQUIRED') return null;
            if (error.payload?.run) renderRun(error.payload.run);
            showToast(error.message || t.requestFailed);
            return null;
        } finally {
            actionInFlight = false;
            delete document.body.dataset.actionInFlight;
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

    function renderMap(map, currentNodeId) {
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
            edgeGroup.append(svgElement('line', {
                class: 'story-map-edge', x1: start.x, y1: start.y, x2: end.x, y2: end.y,
            }));
        });
        svg.append(edgeGroup);

        map.floors.forEach((floor) => floor.nodes.forEach((node) => {
            const point = mapPoint(node);
            const actionable = node.status === 'available';
            const group = svgElement('g', {
                class: `story-map-node${actionable ? ' is-actionable' : ''}`,
                transform: `translate(${point.x} ${point.y})`,
                'data-room-type': node.type,
                'data-status': node.status || 'locked',
                role: actionable ? 'button' : 'img',
                tabindex: actionable ? '0' : '-1',
                'aria-label': `${t.floor(node.floor)} ${t.rooms[node.type] || node.type}`,
            });
            group.append(svgElement('circle', { cx: 0, cy: 0, r: 25 }));
            const text = svgElement('text', { x: 0, y: 1 });
            text.textContent = t.roomMarks[node.type] || '?';
            group.append(text);
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
        const values = card.upgraded ? { ...definition, ...(definition.upgrade || {}) } : { ...definition };
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
        const tags = new Set(Array.isArray(values.tags) ? values.tags : []);
        if (modifiers.force_exile) tags.add('exile');
        if (modifiers.retain) tags.add('retain');
        values.tags = [...tags];
        return values;
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

    function renderResourceOrbs(containerId, current, maximum, spend, kind) {
        const container = $(containerId);
        if (!container) return;
        const now = Math.max(0, Math.floor(Number(current) || 0));
        const max = Math.max(1, Math.floor(Number(maximum) || now || 1));
        const slots = Math.min(15, max);
        const cost = Math.max(0, Math.floor(Number(spend) || 0));
        container.style.setProperty('--story-resource-slots', String(slots));
        container.setAttribute('aria-label', `${kind.toUpperCase()} ${now}/${max}`);
        container.title = `${kind.toUpperCase()} ${now}/${max}`;
        container.replaceChildren();
        const chunks = [];
        if (now > 15) {
            for (let count = Math.floor(now / 10); count > 0; count -= 1) chunks.push(10);
            for (let count = now % 10; count > 0; count -= 1) chunks.push(1);
        } else {
            for (let count = 0; count < now; count += 1) chunks.push(1);
        }
        while (chunks.length < slots) chunks.push(0);
        chunks.slice(0, slots).forEach((value, index) => {
            const orb = document.createElement('span');
            orb.className = `story-resource-orb story-resource-orb-${kind}`;
            if (!value) orb.classList.add('is-empty');
            if (value >= 10) {
                orb.classList.add('is-grouped');
                orb.dataset.groupValue = String(value);
            }
            const spendStart = Math.max(0, now - cost);
            if (value && now <= 15 && index >= spendStart && index < now) orb.classList.add('will-spend');
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
        if (hovered?.dataset.targetKind === targetKind) hovered.classList.add('is-aim-hover');
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
        if (event && Number.isFinite(event.clientX) && Number.isFinite(event.clientY)) {
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

    function cardSelectionSpec(card) {
        const values = cardValues(card);
        const effects = values?.effects || [];
        const combat = activeRun?.state?.combat || {};
        for (const effect of effects) {
            const type = String(effect?.type || '');
            if (type === 'choose_exile' || type === 'copy_hand_card') {
                const exact = type === 'copy_hand_card' || Boolean(effect.exact);
                return {
                    source: (combat.hand || []).filter((item) => String(item.instance_id) !== String(card.instance_id)),
                    payloadKey: 'selected_card_ids',
                    maximum: Math.max(1, Number(effect.amount || 1)),
                    minimum: exact ? Math.max(1, Number(effect.amount || 1)) : 0,
                };
            }
            if (type === 'discard_to_draw_top' && (combat.discard_pile || []).length) {
                return {
                    source: [...combat.discard_pile],
                    payloadKey: 'selected_discard_ids',
                    maximum: 1,
                    minimum: 1,
                };
            }
        }
        return null;
    }

    function openCardSelection(card, targetKind, targetId) {
        const spec = cardSelectionSpec(card);
        if (!spec) return false;
        const dialog = $('story-card-choice-dialog');
        const grid = $('story-card-choice-grid');
        if (!dialog || !grid) return false;
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
                if (cardChoiceContext?.selected.has(id)) {
                    cardChoiceContext.selected.delete(id);
                    wrapper.classList.remove('is-selected');
                } else if ((cardChoiceContext?.selected.size || 0) < spec.maximum) {
                    cardChoiceContext?.selected.add(id);
                    wrapper.classList.add('is-selected');
                }
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

    async function performSelectedCombatCard(targetKind, targetId = '', extraPayload = {}) {
        if (cardPlayInFlight || actionInFlight || !activeRun) return;
        const state = activeRun.state || {};
        const card = selectedCombatCard(state);
        if (!card || cardTargetKind(card) !== targetKind) return;
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
        tile.style.setProperty('--tile-color', `var(--${values.type || 'story-line'})`);
        const inner = document.createElement('span');
        inner.className = 'story-pile-tile-inner';
        const costs = document.createElement('div');
        costs.className = 'story-pile-tile-costs';
        costs.innerHTML = `<span class="story-pile-tile-cost cost-e">${Number(values.cost_e || 0)}</span><span class="story-pile-tile-cost cost-m">${Number(values.cost_m || 0)}</span>`;
        const name = document.createElement('div');
        name.className = 'story-pile-tile-name';
        name.textContent = `${card.upgraded ? '+' : ''}${localize(values.name)}`;
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
        return entry;
    }

    function openStoryPile(kind) {
        const combat = activeRun?.state?.combat;
        if (!combat) return;
        const config = {
            draw: { key: 'draw_pile', title: t.drawPile },
            discard: { key: 'discard_pile', title: t.discardPile },
            exile: { key: 'exile_pile', title: t.exilePile },
        }[kind];
        if (!config) return;
        const source = Array.isArray(combat[config.key]) ? combat[config.key] : [];
        const cards = kind === 'draw' ? [...source].reverse() : [...source].reverse();
        setText('story-pile-title', config.title);
        setText('story-pile-total', t.pileTotal(config.title, cards.length));
        const grid = $('story-pile-grid');
        grid?.replaceChildren();
        if (!cards.length) {
            const empty = document.createElement('div');
            empty.className = 'story-pile-empty';
            empty.textContent = t.pileEmpty;
            grid?.append(empty);
        } else {
            cards.forEach((card, index) => grid?.append(createStoryPileTile(card, index + 1)));
        }
        $('story-pile-dialog')?.showModal();
    }

    function createStoryCard(card, options = {}) {
        const values = cardValues(card);
        const element = document.createElement(options.interactive === false ? 'article' : 'button');
        const cardType = values?.type || 'unknown';
        element.className = `story-card card ${cardType}${options.compact ? ' is-compact' : ''}`;
        if (element.tagName === 'BUTTON') element.type = 'button';
        if (!values) {
            element.textContent = card?.def_id || '?';
            element.disabled = true;
            return element;
        }
        const displayName = `${card.upgraded ? '+' : ''}${localize(values.name)}`;
        const englishName = lang === 'en' ? '' : String(values.name?.en || '');
        const imageUrl = card.upgraded
            ? (values.upgraded_image_url || values.image_url || '')
            : (values.image_url || '');
        element.classList.add(englishName ? 'card-has-english' : 'card-no-english');
        element.classList.add(imageUrl ? 'card-has-art' : 'card-no-art');
        element.dataset.instanceId = String(card.instance_id || '');
        element.dataset.defId = String(card.def_id || '');

        const costs = document.createElement('div');
        costs.className = 'card-costs';
        const costE = document.createElement('span');
        costE.className = 'cost-e';
        costE.textContent = String(values.cost_e ?? 0);
        const name = document.createElement('span');
        name.className = 'card-name';
        name.textContent = displayName;
        const costM = document.createElement('span');
        costM.className = 'cost-m';
        costM.textContent = String(values.cost_m ?? 0);
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
        typeLabel.textContent = t.cardTypes?.[cardType] || cardType;
        typeWrap.append(typeLabel);
        const tags = document.createElement('div');
        tags.className = 'story-card-tags';
        (values.tags || []).forEach((tagId) => {
            const definition = storyContent?.tags?.[tagId];
            if (!definition) return;
            const tag = document.createElement('span');
            tag.textContent = localize(definition.name);
            tag.title = localize(definition.description);
            tags.append(tag);
        });
        const description = document.createElement('div');
        description.className = 'card-effect';
        description.textContent = localize(values.description);
        element.append(typeWrap, tags, description);
        const prediction = activeRun?.state?.combat?.damage_predictions?.[String(card.instance_id || '')];
        if (cardType === 'thorn' && prediction?.summary) {
            const damagePrediction = document.createElement('div');
            damagePrediction.className = 'story-card-damage-prediction';
            damagePrediction.setAttribute('aria-label', `${t.damagePrediction}: ${prediction.summary}`);
            const label = document.createElement('span');
            label.textContent = t.damagePrediction;
            const value = document.createElement('strong');
            value.textContent = String(prediction.summary);
            damagePrediction.append(label, value);
            element.append(damagePrediction);
        }
        if (options.note) {
            const note = document.createElement('span');
            note.className = 'story-card-note';
            note.textContent = options.note;
            element.append(note);
        }
        if (options.disabled) element.disabled = true;
        if (typeof options.onClick === 'function') element.addEventListener('click', options.onClick);
        return element;
    }

    function renderBlessing(state) {
        setText('story-blessing-kicker', t.floor(state.current_floor || 1));
        const container = $('story-blessing-options');
        container?.replaceChildren();
        const expected = Number(state.stage || 1) === 1 ? 'titan' : 'oracle';
        Object.entries(storyContent?.blessings || {}).filter(([id]) => id === expected).forEach(([id, blessing]) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'story-choice-option story-blessing-option';
            const mark = document.createElement('span');
            mark.className = 'story-choice-mark';
            mark.textContent = localize(blessing.name).slice(0, 1);
            const name = document.createElement('strong');
            name.textContent = localize(blessing.name);
            const description = document.createElement('span');
            description.textContent = localize(blessing.description);
            button.append(mark, name, description);
            button.addEventListener('click', () => storyAction('choose_blessing', { blessing_id: id }));
            container?.append(button);
        });
        showView('story-blessing');
    }

    function renderMapView(state) {
        const player = state.player || {};
        const node = currentNode(state);
        setText('story-stage-value', state.stage || 1);
        setText('story-biome-value', state.biome === 'garden' ? t.garden : state.biome || t.garden);
        setText('story-health-value', `${stateValue(player.health)}/${stateValue(player.max_health)}`);
        setText('story-elixir-value', `${stateValue(player.max_elixir)} E`);
        setText('story-magic-value', `${stateValue(player.magic)}/${stateValue(player.max_magic)}`);
        setText('story-gold-value', stateValue(player.gold ?? 0));
        setText('story-floor-value', t.floor(state.current_floor || node?.floor || 1));
        setText('story-room-value', t.rooms[node?.type] || node?.type || '');
        renderLegend();
        renderMap(state.map, state.current_node_id);
        showView('story-run');
    }

    function renderEffects(containerId, values) {
        const container = $(containerId);
        renderEffectsInto(container, values);
    }

    function renderEffectsInto(container, values) {
        if (!container) return;
        container.replaceChildren();
        const icons = {
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
        };
        values.filter((item) => Number(item.value) > 0).forEach((item) => {
            const chip = document.createElement('span');
            chip.className = `story-effect story-effect-${item.key}`;
            chip.title = `${item.label}: ${item.value}`;
            chip.setAttribute('aria-label', chip.title);
            const icon = document.createElement('img');
            icon.src = `/static/assets/status-icons/${icons[item.key] || item.key}.svg`;
            icon.alt = '';
            icon.setAttribute('aria-hidden', 'true');
            const value = document.createElement('strong');
            value.textContent = String(item.value);
            chip.append(icon, value);
            container.append(chip);
        });
    }

    function canSatisfyCardSelection(card, combat) {
        const values = cardValues(card);
        for (const effect of values?.effects || []) {
            const type = String(effect?.type || '');
            if ((type === 'choose_exile' && effect.exact) || type === 'copy_hand_card') {
                const needed = Math.max(1, Number(effect.amount || 1));
                const available = (combat.hand || []).filter((item) => String(item.instance_id) !== String(card.instance_id)).length;
                if (available < needed) return false;
            }
        }
        return true;
    }

    function createEnemyActor(enemy, selectedTargetKind) {
        const actor = document.createElement('article');
        actor.className = 'story-actor story-actor-enemy';
        actor.dataset.targetKind = 'enemy';
        actor.dataset.targetId = String(enemy.id || '');
        actor.classList.toggle('is-play-target', selectedTargetKind === 'enemy');

        const name = document.createElement('div');
        name.className = 'story-actor-name';
        name.textContent = localize(enemy.name) || (lang === 'zh' ? '敌人' : 'Enemy');
        const portrait = document.createElement('div');
        portrait.className = 'story-portrait story-enemy-placeholder';
        portrait.setAttribute('aria-label', name.textContent);
        portrait.textContent = '?';

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
        fill.style.width = `${Math.max(0, Math.min(100, Number(enemy.health || 0) / Math.max(1, Number(enemy.max_health || 1)) * 100))}%`;
        track.append(fill);
        const healthValue = document.createElement('b');
        healthValue.textContent = `${Math.max(0, Number(enemy.health || 0))}/${Math.max(1, Number(enemy.max_health || 1))}`;
        healthBody.append(track, healthValue);
        health.append(healthIcon, healthBody);

        const effects = document.createElement('div');
        effects.className = 'story-effect-list';
        renderEffectsInto(effects, [
            { key: 'shield', label: t.shield, value: enemy.shield },
            { key: 'power', label: t.power, value: enemy.power },
            { key: 'temporary_power', label: t.power, value: enemy.temporary_power },
            { key: 'weak', label: t.weak, value: enemy.weak },
            { key: 'vulnerable', label: t.vulnerable, value: enemy.vulnerable },
            { key: 'fragile', label: '脆弱', value: enemy.fragile },
            { key: 'stun', label: '眩晕', value: enemy.stun },
            { key: 'reflection', label: '反射', value: enemy.reflection },
            { key: 'wither', label: '凋萎', value: enemy.wither },
            { key: 'rockfall', label: '落石', value: enemy.rockfall },
        ]);

        const intent = document.createElement('div');
        intent.className = 'story-intent';
        const intentLabel = document.createElement('span');
        intentLabel.textContent = t.intent;
        const intentValue = document.createElement('strong');
        const intentName = localize(enemy.intent?.name);
        intentValue.textContent = [intentName, enemy.intent?.summary].filter(Boolean).join(' · ') || '--';
        intent.append(intentLabel, intentValue);
        actor.append(name, portrait, health, effects, intent);
        return actor;
    }

    function renderCombat(state) {
        const combat = state.combat || {};
        const player = state.player || {};
        const livingEnemies = (combat.enemies || []).filter((item) => Number(item.health) > 0);
        const enemy = livingEnemies[0] || (combat.enemies || [])[0] || {};
        if (selectedCombatCardId && !selectedCombatCard(state)) selectedCombatCardId = '';
        const selected = selectedCombatCard(state);
        const selectedValues = cardValues(selected);
        const selectedTargetKind = selected && !storyCursorCardMode(selected) ? cardTargetKind(selected) : '';
        setText('story-round', `R${combat.round || 1}`);
        setText('story-phase', combat.turn === 'player' ? t.playerTurn : t.enemyTurn);
        setHealthBar('story-combat-player', player.health, player.max_health);
        renderResourceOrbs(
            'story-combat-player-elixir',
            combat.elixir,
            player.max_elixir,
            selectedValues?.cost_e,
            'e',
        );
        renderResourceOrbs(
            'story-combat-player-magic',
            combat.magic,
            player.max_magic,
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
        ]);
        const enemyGroup = $('story-enemy-group');
        enemyGroup?.replaceChildren();
        enemyGroup?.style.setProperty('--story-enemy-count', String(Math.max(1, livingEnemies.length)));
        enemyGroup?.style.setProperty('--story-enemy-scale', String(Math.max(.48, Math.min(.82, 1.03 - livingEnemies.length * .13))));
        livingEnemies.forEach((enemyItem) => {
            enemyGroup?.append(createEnemyActor(enemyItem, selectedTargetKind));
        });
        const hand = $('story-hand');
        hand?.replaceChildren();
        hand?.classList.toggle('has-selected-card', Boolean(selected));
        const cards = combat.hand || [];
        cards.forEach((card, index) => {
            const values = cardValues(card);
            const tags = new Set(values?.tags || []);
            const costE = values?.cost_e === 'X' ? 0 : Number(values?.cost_e || 0);
            const playable = values
                && !tags.has('unplayable')
                && Number(combat.elixir) >= costE
                && Number(combat.magic) >= Number(values.cost_m || 0)
                && combat.turn === 'player'
                && !combat.opening_redraw_pending
                && (combat.card_play_limit == null || Number(combat.cards_played_this_turn || 0) < Number(combat.card_play_limit))
                && canSatisfyCardSelection(card, combat);
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
                onClick: (event) => selectCombatCard(state, card, event),
            }));
            hand?.append(wrapper);
        });
        syncStoryCursorCard(state);
        const targetKind = selected ? cardTargetKind(selected) : '';
        const cursorMode = selected ? storyCursorCardMode(selected) : '';
        $('story-player-target')?.classList.toggle('is-play-target', !cursorMode && targetKind === 'self');
        document.querySelectorAll('.story-actor-enemy').forEach((actor) => {
            actor.classList.toggle('is-play-target', !cursorMode && targetKind === 'enemy');
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
        if (endTurn) endTurn.disabled = combat.turn !== 'player' || Boolean(combat.opening_redraw_pending);
        showView('story-combat');
        scheduleStoryAimUpdate(state);
        if (combat.opening_redraw_pending) {
            queueMicrotask(() => openOpeningRedraw(state));
        }
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
            description.textContent = options.description;
            button.append(description);
        }
        button.disabled = Boolean(options.disabled);
        button.addEventListener('click', onClick);
        return button;
    }

    function renderRoom(state) {
        const room = state.room || {};
        const player = state.player || {};
        const container = $('story-room-options');
        container?.replaceChildren();
        setText('story-room-kicker', `${t.floor(state.current_floor || 1)} · ${t.rooms[room.type] || t.room}`);
        if (room.type === 'stage_choice') {
            setText('story-room-title', lang === 'zh' ? `选择第 ${room.stage || ''} 阶段区域` : `Choose Stage ${room.stage || ''} region`);
            setText('story-room-copy', lang === 'zh' ? '进入后将生成新的16层路线。' : 'A new 16-floor route will be generated.');
            (room.biomes || []).forEach((biome) => {
                container?.append(choiceButton(String(biome), () => storyAction('choose_stage', { biome }), { primary: true }));
            });
        } else if (room.type === 'rest') {
            setText('story-room-title', t.restTitle);
            setText('story-room-copy', t.restCopy);
            const amount = Math.ceil(Number(player.max_health || 0) * 0.3);
            container?.append(choiceButton(`${t.heal} ${amount}H`, () => storyAction('resolve_room', { option: 'heal' }), { primary: true }));
            (player.deck || []).forEach((card) => container?.append(createStoryCard(card, {
                compact: true,
                disabled: Boolean(card.upgraded),
                note: card.upgraded ? t.upgraded : t.upgrade,
                onClick: () => storyAction('resolve_room', { option: 'upgrade', card_instance_id: card.instance_id }),
            })));
            if ((room.options || []).includes('gold')) {
                container?.append(choiceButton(lang === 'zh' ? '获得150G' : 'Gain 150 G', () => storyAction('resolve_room', { option: 'gold' })));
            }
        } else if (room.type === 'chest') {
            setText('story-room-title', t.chestTitle);
            const relic = storyContent?.relics?.[room.relic];
            setText('story-room-copy', [
                `${Number(room.gold || 0)}G`,
                relic ? `${localize(relic.name)}：${localize(relic.description)}` : '',
            ].filter(Boolean).join(' · '));
            container?.append(choiceButton(t.openChest, () => storyAction('resolve_room', { option: 'claim' }), { primary: true }));
        } else if (room.type === 'shop') {
            setText('story-room-title', t.shopTitle);
            setText('story-room-copy', t.shopCopy);
            (room.cards || []).filter((item) => !item.sold).forEach((item) => {
                const card = { instance_id: item.id, def_id: item.card_id, upgraded: false };
                container?.append(createStoryCard(card, {
                    compact: true,
                    disabled: Number(player.gold || 0) < Number(item.price || 0),
                    note: `${Number(item.price || 0)}G`,
                    onClick: () => storyAction('resolve_room', { option: 'buy_card', item_id: item.id }),
                }));
            });
            (room.relics || []).filter((item) => !item.sold).forEach((item) => {
                const relic = storyContent?.relics?.[item.relic_id];
                container?.append(choiceButton(`${localize(relic?.name) || item.relic_id} · ${item.price}G`, () => {
                    storyAction('resolve_room', { option: 'buy_relic', item_id: item.id });
                }, {
                    description: localize(relic?.description),
                    disabled: Number(player.gold || 0) < Number(item.price || 0),
                }));
            });
            (player.deck || []).forEach((card) => {
                container?.append(createStoryCard(card, {
                    compact: true,
                    disabled: Number(player.gold || 0) < Number(room.remove_price || 0),
                    note: `${lang === 'zh' ? '移除' : 'Remove'} · ${room.remove_price}G`,
                    onClick: () => storyAction('resolve_room', { option: 'remove_card', card_instance_id: card.instance_id }),
                }));
                container?.append(createStoryCard(card, {
                    compact: true,
                    disabled: Boolean(card.upgraded) || Number(player.gold || 0) < Number(room.upgrade_price || 0),
                    note: `${t.upgrade} · ${room.upgrade_price}G`,
                    onClick: () => storyAction('resolve_room', { option: 'upgrade_card', card_instance_id: card.instance_id }),
                }));
            });
            container?.append(choiceButton(t.leave, () => storyAction('resolve_room', { option: 'leave' })));
        } else {
            setText('story-room-title', localize(room.title) || t.eventTitle);
            const eventCopy = [
                localize(room.description) || t.eventCopy,
                localize(room.last_result),
                room.event_id === 'mystery_lottery'
                    ? (lang === 'zh' ? `已抽奖 ${Number(room.attempts || 0)}/4 次` : `${Number(room.attempts || 0)}/4 attempts`)
                    : '',
            ].filter(Boolean).join(' ');
            setText('story-room-copy', eventCopy);
            (room.options || []).forEach((rawOption) => {
                const option = typeof rawOption === 'string'
                    ? { id: rawOption, label: rawOption, description: '' }
                    : rawOption;
                const optionId = String(option.id || '');
                if (optionId === 'lottery_inspect') {
                    (player.deck || [])
                        .filter((card) => !card.upgraded && storyContent?.cards?.[card.def_id]?.upgrade)
                        .forEach((card) => container?.append(createStoryCard(card, {
                            compact: true,
                            note: localize(option.label),
                            onClick: () => storyAction('resolve_room', {
                                option: optionId,
                                card_instance_id: card.instance_id,
                            }),
                        })));
                    return;
                }
                const disabled = (
                    (optionId === 'event_buy' && Number(player.gold || 0) < 35)
                    || (optionId === 'lottery_draw' && Number(player.gold || 0) < 50)
                );
                container?.append(choiceButton(
                    localize(option.label) || optionId,
                    () => storyAction('resolve_room', { option: optionId }),
                    {
                        primary: optionId !== 'leave' && optionId !== 'fight_leave',
                        description: localize(option.description),
                        disabled,
                    },
                ));
            });
        }
        showView('story-room');
    }

    function renderReward(state) {
        const reward = state.reward || {};
        setText('story-reward-kicker', t.battleWon);
        setText('story-reward-title', t.chooseCard);
        const relic = reward.relic ? storyContent?.relics?.[reward.relic] : null;
        const details = [t.gainedGold(reward.gold || 0)];
        if (relic) details.push(`${localize(relic.name)}：${localize(relic.description)}`);
        setText('story-reward-copy', details.join(' '));
        const container = $('story-reward-options');
        container?.replaceChildren();
        (reward.cards || []).forEach((choice) => {
            const defId = typeof choice === 'string' ? choice : choice.card_id;
            const upgraded = Boolean(typeof choice === 'object' && choice.upgraded);
            const card = { instance_id: `reward-${defId}`, def_id: defId, upgraded };
            container?.append(createStoryCard(card, {
                onClick: () => storyAction('choose_reward', { card_id: defId }),
            }));
        });
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
        activeRun = run;
        if (window.__STORY_DEV_TOOLS__) {
            renderDeveloperPanel(run?.state || null, { syncValues: developerModeOpen });
        }
        if (!run) {
            selectedCombatCardId = '';
            destroyStoryCursorCard();
            $('story-aim-layer')?.classList.add('hidden');
            showView('story-empty');
            return;
        }
        const state = run.state || {};
        if (state.phase === 'blessing') renderBlessing(state);
        else if (state.phase === 'combat' && state.combat) renderCombat(state);
        else {
            selectedCombatCardId = '';
            destroyStoryCursorCard();
            $('story-aim-layer')?.classList.add('hidden');
            if (state.phase === 'room' || state.phase === 'stage_choice') renderRoom(state);
            else if (state.phase === 'reward') renderReward(state);
            else if (state.phase === 'complete' || state.phase === 'game_over') renderTerminal(state);
            else renderMapView(state);
        }
    }

    async function loadRun() {
        showView('story-loading');
        try {
            const [contentPayload, runPayload] = await Promise.all([
                requestJson('/api/story/content'),
                requestJson('/api/story/run'),
            ]);
            storyContent = contentPayload.content || {};
            contentVersion = contentPayload.content_version || '';
            const run = runPayload.run || null;
            if (run && contentVersion && run.content_version !== contentVersion && window.__STORY_DEV_TOOLS__) {
                activeRun = run;
                await resetMap(true);
                return;
            }
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
                const contentPayload = await requestJson('/api/story/content');
                storyContent = contentPayload.content || {};
                contentVersion = contentPayload.content_version || '';
            }
            const payload = await requestJson('/api/story/run', { method: 'POST', body: '{}' });
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
            renderRun(payload.run || null);
            if (!silent) showToast(t.mapReset);
        } catch (error) {
            if (error.message !== 'AUTH_REQUIRED') showToast(error.message);
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

    function bind() {
        $('story-start')?.addEventListener('click', startRun);
        $('story-end-turn')?.addEventListener('click', () => storyAction('end_turn'));
        $('story-draw-pile')?.addEventListener('click', () => openStoryPile('draw'));
        $('story-discard-pile')?.addEventListener('click', () => openStoryPile('discard'));
        $('story-exile-pile')?.addEventListener('click', () => openStoryPile('exile'));
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
        $('story-card-choice-dialog')?.addEventListener('close', (event) => {
            const context = cardChoiceContext;
            cardChoiceContext = null;
            if (!context) return;
            const selected = [...context.selected];
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
        $('story-reward-skip')?.addEventListener('click', () => storyAction('choose_reward'));
        $('story-terminal-new')?.addEventListener('click', startNewJourney);
        $('story-dev-toggle')?.addEventListener('click', () => setDeveloperMode(!developerModeOpen));
        $('story-dev-close')?.addEventListener('click', () => setDeveloperMode(false));
        $('story-dev-floor')?.addEventListener('change', () => renderDeveloperNodes(activeRun?.state || null));
        $('story-dev-jump')?.addEventListener('click', jumpDeveloperNode);
        $('story-dev-apply')?.addEventListener('click', applyDeveloperValues);
        $('story-reset-map')?.addEventListener('click', () => $('story-reset-dialog')?.showModal());
        $('story-reset-dialog')?.addEventListener('close', (event) => {
            if (event.target.returnValue === 'confirm') resetMap();
        });
        const moveAim = (event) => {
            storyAimPointer = { x: event.clientX, y: event.clientY };
            positionStoryCursorCard(event.clientX, event.clientY);
            if (selectedCombatCardId) scheduleStoryAimUpdate();
        };
        document.addEventListener('mousemove', moveAim);
        document.addEventListener('pointermove', moveAim);
        window.addEventListener('resize', () => scheduleStoryAimUpdate());
        window.addEventListener('keydown', (event) => {
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
            if (!selectedCombatCardId || !activeRun?.state) return;
            event.preventDefault();
            cancelStoryCombatSelection(true);
        });
    }

    applyText();
    renderPlayerSkin();
    bind();
    loadRun();
})();
