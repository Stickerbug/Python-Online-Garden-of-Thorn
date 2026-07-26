(() => {
    'use strict';

    const host = window.GTN_SHORTCUT_HOST;
    const storage = window.GTN_STORAGE;
    if (!host || !storage) {
        console.warn('[keybindings] host or storage is unavailable');
        return;
    }

    const SCHEMA = 1;
    const CHANNEL_NAME = 'gtn-keybindings-v1';
    const GROUPS = ['selection', 'battle', 'view', 'training'];
    const ACTIONS = [
        { id: 'confirm', group: 'selection', defaultBinding: 'Enter' },
        { id: 'cancel', group: 'selection', defaultBinding: 'Escape' },
        { id: 'refresh', group: 'selection', defaultBinding: 'KeyR' },
        { id: 'navigate_left', group: 'selection', defaultBinding: 'ArrowLeft' },
        { id: 'navigate_right', group: 'selection', defaultBinding: 'ArrowRight' },
        { id: 'navigate_up', group: 'selection', defaultBinding: 'ArrowUp' },
        { id: 'navigate_down', group: 'selection', defaultBinding: 'ArrowDown' },
        { id: 'toggle_focused', group: 'selection', defaultBinding: 'Space' },
        { id: 'target_self', group: 'battle', defaultBinding: 'KeyE' },
        { id: 'target_enemy', group: 'battle', defaultBinding: 'KeyQ' },
        { id: 'target_teammate', group: 'battle', defaultBinding: 'Shift+KeyE' },
        { id: 'target_enemy_2', group: 'battle', defaultBinding: 'Shift+KeyQ' },
        { id: 'end_turn', group: 'battle', defaultBinding: 'KeyF' },
        { id: 'pass_response', group: 'battle', defaultBinding: 'KeyV' },
        { id: 'view_log', group: 'view', defaultBinding: 'KeyX' },
        { id: 'view_spectators', group: 'view', defaultBinding: 'KeyC' },
        { id: 'view_draw', group: 'view', defaultBinding: 'KeyA' },
        { id: 'view_discard', group: 'view', defaultBinding: 'KeyS' },
        { id: 'view_exile', group: 'view', defaultBinding: 'KeyD' },
        { id: 'focus_chat', group: 'view', defaultBinding: 'KeyT' },
        { id: 'shortcut_help', group: 'view', defaultBinding: 'Slash' },
        { id: 'solo_undo', group: 'training', defaultBinding: 'Ctrl+KeyZ' },
        { id: 'solo_redo', group: 'training', defaultBinding: 'Ctrl+KeyY' },
    ];
    const FIXED_HELP_ACTIONS = [
        { id: 'fixed_slots_1_10', group: 'selection', displayBinding: '1–0' },
        { id: 'fixed_slots_11_20', group: 'selection', displayBinding: '` + 1–0' },
        { id: 'fixed_hint_preview', group: 'view', displayBinding: 'Alt' },
    ];
    const ACTION_BY_ID = new Map(ACTIONS.map(action => [action.id, action]));
    const DEFAULT_BINDINGS = new Map(ACTIONS.map(action => [action.id, action.defaultBinding]));
    const MODIFIER_ORDER = ['Ctrl', 'Alt', 'Shift', 'Meta'];
    const MODIFIER_CODES = new Set([
        'ControlLeft', 'ControlRight', 'AltLeft', 'AltRight',
        'ShiftLeft', 'ShiftRight', 'MetaLeft', 'MetaRight',
    ]);
    const RESERVED_BINDINGS = new Set([
        'F5', 'Alt+F4',
        'Ctrl+KeyL', 'Ctrl+KeyN', 'Ctrl+KeyP', 'Ctrl+KeyR',
        'Ctrl+KeyS', 'Ctrl+KeyT', 'Ctrl+KeyW',
        'Meta+KeyL', 'Meta+KeyN', 'Meta+KeyP', 'Meta+KeyR',
        'Meta+KeyS', 'Meta+KeyT', 'Meta+KeyW',
    ]);
    const FIXED_SELECTION_BINDINGS = new Set([
        'Backquote',
        ...Array.from({ length: 10 }, (_, index) => 'Digit' + index),
    ]);

    const LABELS_ZH = {
        selection: '选择与操作',
        battle: '对局',
        view: '查看与交流',
        training: '单人训练场',
        fixed_slots_1_10: '选择第 1-10 项或手牌',
        fixed_slots_11_20: '选择第 11-20 项或手牌',
        fixed_hint_preview: '临时显示当前快捷键',
        confirm: '确认',
        cancel: '取消',
        refresh: '刷新当前操作',
        navigate_left: '向左移动选择',
        navigate_right: '向右移动选择',
        navigate_up: '向上移动选择',
        navigate_down: '向下移动选择',
        toggle_focused: '选择或取消当前项',
        target_self: '选择自己',
        target_enemy: '选择敌方 1',
        target_teammate: '选择队友（2v2）',
        target_enemy_2: '选择敌方 2（2v2）',
        end_turn: '结束回合',
        pass_response: '不反制',
        view_log: '切换到战斗日志',
        view_spectators: '切换到观战列表',
        view_draw: '查看或关闭抽牌堆',
        view_discard: '查看或关闭弃牌堆',
        view_exile: '查看或关闭放逐区',
        focus_chat: '输入聊天',
        shortcut_help: '打开或关闭快捷键总览',
        solo_undo: '撤销',
        solo_redo: '重做',
    };

    const ACTION_LABELS = {
        zh: LABELS_ZH,
        en: {
            selection: 'Selection and actions', battle: 'Battle', view: 'View and chat', training: 'Solo Training',
            fixed_slots_1_10: 'Select items or cards 1-10', fixed_slots_11_20: 'Select items or cards 11-20',
            fixed_hint_preview: 'Temporarily show current shortcuts', confirm: 'Confirm', cancel: 'Cancel',
            refresh: 'Refresh current action',
            navigate_left: 'Move selection left', navigate_right: 'Move selection right',
            navigate_up: 'Move selection up', navigate_down: 'Move selection down',
            toggle_focused: 'Select or deselect focused item',
            target_self: 'Target self', target_enemy: 'Target enemy 1',
            target_teammate: 'Target teammate (2v2)', target_enemy_2: 'Target enemy 2 (2v2)',
            end_turn: 'End turn', pass_response: 'Pass response',
            view_log: 'Show battle log', view_spectators: 'Show spectator list',
            view_draw: 'Toggle draw pile', view_discard: 'Toggle discard pile', view_exile: 'Toggle exile pile',
            focus_chat: 'Focus chat', shortcut_help: 'Toggle shortcut overview',
            solo_undo: 'Undo', solo_redo: 'Redo',
        },
        fr: {
            selection: 'Sélection et actions', battle: 'Combat', view: 'Affichage et discussion', training: 'Entraînement solo',
            fixed_slots_1_10: 'Sélectionner les éléments ou cartes 1 à 10',
            fixed_slots_11_20: 'Sélectionner les éléments ou cartes 11 à 20',
            fixed_hint_preview: 'Afficher temporairement les raccourcis', confirm: 'Confirmer', cancel: 'Annuler',
            refresh: 'Actualiser l’action',
            navigate_left: 'Déplacer la sélection à gauche', navigate_right: 'Déplacer la sélection à droite',
            navigate_up: 'Déplacer la sélection vers le haut', navigate_down: 'Déplacer la sélection vers le bas',
            toggle_focused: 'Sélectionner ou désélectionner l’élément',
            target_self: 'Se cibler', target_enemy: 'Cibler l’ennemi 1',
            target_teammate: 'Cibler le coéquipier (2v2)', target_enemy_2: 'Cibler l’ennemi 2 (2v2)',
            end_turn: 'Terminer le tour', pass_response: 'Ne pas contrer',
            view_log: 'Afficher le journal de combat', view_spectators: 'Afficher les spectateurs',
            view_draw: 'Afficher ou masquer la pioche', view_discard: 'Afficher ou masquer la défausse', view_exile: 'Afficher ou masquer l’exil',
            focus_chat: 'Écrire dans le chat', shortcut_help: 'Afficher ou masquer les raccourcis',
            solo_undo: 'Annuler', solo_redo: 'Rétablir',
        },
        ja: {
            selection: '選択と操作', battle: '対戦', view: '表示とチャット', training: 'ソロトレーニング',
            fixed_slots_1_10: '1～10番の項目またはカードを選択',
            fixed_slots_11_20: '11～20番の項目またはカードを選択',
            fixed_hint_preview: '現在のショートカットを一時表示', confirm: '決定', cancel: 'キャンセル',
            refresh: '現在の操作を更新',
            navigate_left: '選択を左へ移動', navigate_right: '選択を右へ移動',
            navigate_up: '選択を上へ移動', navigate_down: '選択を下へ移動',
            toggle_focused: '現在の項目を選択・解除',
            target_self: '自分を選択', target_enemy: '敵1を選択',
            target_teammate: '味方を選択（2v2）', target_enemy_2: '敵2を選択（2v2）',
            end_turn: 'ターン終了', pass_response: 'カウンターしない',
            view_log: 'バトルログを表示', view_spectators: '観戦者一覧を表示',
            view_draw: '山札を開閉', view_discard: '捨て札を開閉', view_exile: '追放を開閉',
            focus_chat: 'チャットを入力', shortcut_help: 'ショートカット一覧を開閉',
            solo_undo: '元に戻す', solo_redo: 'やり直す',
        },
    };

    const UI_TEXT = {
        zh: {
            tab: '快捷键', title: '快捷键', help: '查看全部',
            show_hints: '按住 Alt 显示快捷键提示', device_override: '仅此设备使用不同键位',
            reset_all: '恢复全部默认', change: '更改', clear: '清除', reset: '恢复默认',
            press_key: '请按新按键', unbound: '未设置', default_mark: '默认',
            account_storage: '键位已与账号同步。', device_storage: '当前使用此设备的独立键位。',
            guest_storage: '游客键位保存在本机。', session_storage: '浏览器禁止本地存储；本次页面内仍可使用。',
            saved: '快捷键已保存', save_failed: '快捷键暂未同步，当前页面仍保留修改',
            conflict_title: '键位冲突', conflict_message: '此键已用于“{0}”。是否交换两个动作的键位？',
            reserved: '该组合由浏览器、系统或固定选牌键占用，请使用其他按键。', capture_cancelled: '已取消改键',
            reset_confirm: '确定恢复全部默认快捷键吗？',
            help_title: '快捷键总览', current_shortcuts: '当前可用快捷键', close: '关闭',
        },
        en: {
            tab: 'Shortcuts', title: 'Keyboard shortcuts', help: 'View all',
            show_hints: 'Show shortcut hints while holding Alt', device_override: 'Use different bindings on this device',
            reset_all: 'Reset all', change: 'Change', clear: 'Clear', reset: 'Reset',
            press_key: 'Press a new key', unbound: 'Unbound', default_mark: 'Default',
            account_storage: 'Bindings are synced with your account.', device_storage: 'Device-specific bindings are active.',
            guest_storage: 'Guest bindings are stored on this device.', session_storage: 'Local storage is blocked; bindings remain available for this page.',
            saved: 'Shortcuts saved', save_failed: 'Sync failed; changes remain active on this page',
            conflict_title: 'Binding conflict', conflict_message: 'This key is used by “{0}”. Swap the two bindings?',
            reserved: 'This shortcut is reserved by the browser, system, or fixed card selection keys.', capture_cancelled: 'Binding change cancelled',
            reset_confirm: 'Reset all shortcuts to defaults?',
            help_title: 'Shortcut overview', current_shortcuts: 'Available shortcuts', close: 'Close',
        },
        fr: {
            tab: 'Raccourcis', title: 'Raccourcis clavier', help: 'Tout afficher',
            show_hints: 'Afficher les raccourcis en maintenant Alt', device_override: 'Utiliser des touches propres à cet appareil',
            reset_all: 'Tout réinitialiser', change: 'Modifier', clear: 'Effacer', reset: 'Réinitialiser',
            press_key: 'Appuyez sur une touche', unbound: 'Non défini', default_mark: 'Par défaut',
            account_storage: 'Les touches sont synchronisées avec votre compte.', device_storage: 'Les touches propres à cet appareil sont actives.',
            guest_storage: 'Les touches invité sont enregistrées sur cet appareil.', session_storage: 'Le stockage local est bloqué ; les touches restent actives sur cette page.',
            saved: 'Raccourcis enregistrés', save_failed: 'Échec de la synchronisation ; les changements restent actifs',
            conflict_title: 'Conflit de touches', conflict_message: 'Cette touche sert déjà à « {0} ». Échanger les deux touches ?',
            reserved: 'Cette combinaison est réservée par le navigateur, le système ou la sélection fixe des cartes.', capture_cancelled: 'Modification annulée',
            reset_confirm: 'Rétablir tous les raccourcis par défaut ?',
            help_title: 'Aperçu des raccourcis', current_shortcuts: 'Raccourcis disponibles', close: 'Fermer',
        },
        ja: {
            tab: 'キー設定', title: 'キーボードショートカット', help: '一覧を見る',
            show_hints: 'Altを押している間ショートカットを表示', device_override: 'この端末だけ別のキー設定を使う',
            reset_all: 'すべて初期化', change: '変更', clear: '解除', reset: '初期化',
            press_key: '新しいキーを押してください', unbound: '未設定', default_mark: '既定',
            account_storage: 'キー設定はアカウントと同期されます。', device_storage: 'この端末専用のキー設定を使用中です。',
            guest_storage: 'ゲストのキー設定はこの端末に保存されます。', session_storage: 'ローカル保存が禁止されています。このページ内では使用できます。',
            saved: 'ショートカットを保存しました', save_failed: '同期できませんでした。変更はこのページで維持されます',
            conflict_title: 'キーの競合', conflict_message: 'このキーは「{0}」で使用中です。2つのキーを交換しますか？',
            reserved: 'このキーはブラウザー、システム、または固定カード選択で使用されています。', capture_cancelled: 'キー変更をキャンセルしました',
            reset_confirm: 'すべてのショートカットを初期設定に戻しますか？',
            help_title: 'ショートカット一覧', current_shortcuts: '現在使用できるショートカット', close: '閉じる',
        },
    };

    function language() {
        const value = String(host.getLang() || 'zh').toLowerCase();
        return ['zh', 'en', 'fr', 'ja'].includes(value) ? value : 'en';
    }

    function text(key) {
        const lang = language();
        return (UI_TEXT[lang] && UI_TEXT[lang][key]) || UI_TEXT.en[key] || UI_TEXT.zh[key] || key;
    }

    function actionLabel(actionId) {
        const lang = language();
        const table = ACTION_LABELS[lang] || ACTION_LABELS.en;
        return table[actionId] || ACTION_LABELS.en[actionId] || LABELS_ZH[actionId] || actionId;
    }

    function canonicalBinding(value) {
        const token = String(value || '').trim();
        if (!token || token.length > 64) return null;
        const parts = token.split('+');
        const base = parts.pop();
        if (!/^[A-Za-z][A-Za-z0-9]{0,31}$/.test(base)) return null;
        const modifiers = [...new Set(parts)];
        if (modifiers.length !== parts.length || modifiers.some(mod => !MODIFIER_ORDER.includes(mod))) return null;
        modifiers.sort((a, b) => MODIFIER_ORDER.indexOf(a) - MODIFIER_ORDER.indexOf(b));
        return [...modifiers, base].join('+');
    }

    function bindingFromEvent(event) {
        if (!event || MODIFIER_CODES.has(event.code)) return null;
        const base = String(event.code || '');
        if (!/^[A-Za-z][A-Za-z0-9]{0,31}$/.test(base)) return null;
        const modifiers = [];
        if (event.ctrlKey) modifiers.push('Ctrl');
        if (event.altKey) modifiers.push('Alt');
        if (event.shiftKey) modifiers.push('Shift');
        if (event.metaKey) modifiers.push('Meta');
        return [...modifiers, base].join('+');
    }

    function displayBinding(binding, compact = false) {
        if (!binding) return text('unbound');
        const names = {
            Backquote: String.fromCharCode(96), Escape: compact ? 'Esc' : 'Escape', Enter: 'Enter',
            Slash: '/', Space: compact ? '␠' : 'Space', Tab: 'Tab',
            ArrowUp: '↑', ArrowDown: '↓', ArrowLeft: '←', ArrowRight: '→',
        };
        return binding.split('+').map(part => {
            if (/^Key[A-Z]$/.test(part)) return part.slice(3);
            if (/^Digit\d$/.test(part)) return part.slice(5);
            if (/^Numpad\d$/.test(part)) return compact ? part.slice(6) : 'Num ' + part.slice(6);
            if (/^F\d{1,2}$/.test(part)) return part;
            return names[part] || part;
        }).join(compact ? '+' : ' + ');
    }

    function emptyConfig(showHints = true) {
        return { schema: SCHEMA, overrides: {}, unbound: [], show_hints: showHints, revision: 0 };
    }

    function sanitizeConfig(value, options = {}) {
        const source = value && typeof value === 'object' ? value : {};
        const overrides = {};
        if (source.overrides && typeof source.overrides === 'object') {
            Object.entries(source.overrides).forEach(([actionId, rawBinding]) => {
                const binding = canonicalBinding(rawBinding);
                if (
                    ACTION_BY_ID.has(actionId)
                    && binding
                    && !FIXED_SELECTION_BINDINGS.has(binding)
                ) {
                    overrides[actionId] = binding;
                }
            });
        }
        const unbound = Array.isArray(source.unbound)
            ? [...new Set(source.unbound.filter(actionId => ACTION_BY_ID.has(actionId)))].sort()
            : [];
        unbound.forEach(actionId => { delete overrides[actionId]; });
        return {
            schema: SCHEMA,
            overrides,
            unbound,
            show_hints: source.show_hints !== false,
            revision: Math.max(0, Number(source.revision || options.revision || 0) || 0),
        };
    }

    function materializeConfig(config, base = DEFAULT_BINDINGS) {
        const result = new Map(base);
        const safe = sanitizeConfig(config);
        safe.unbound.forEach(actionId => result.set(actionId, null));
        Object.entries(safe.overrides).forEach(([actionId, binding]) => result.set(actionId, binding));
        return result;
    }

    function configFromBindings(bindings, base, showHints, revision = 0) {
        const overrides = {};
        const unbound = [];
        ACTIONS.forEach(action => {
            const binding = bindings.get(action.id) || null;
            const baseBinding = base.get(action.id) || null;
            if (!binding) unbound.push(action.id);
            else if (binding !== baseBinding) overrides[action.id] = binding;
        });
        return sanitizeConfig({ schema: SCHEMA, overrides, unbound, show_hints: showHints, revision });
    }

    function readStoredConfig(key, fallbackHints = true) {
        try {
            const raw = storage.getItem(key);
            return raw ? sanitizeConfig(JSON.parse(raw)) : emptyConfig(fallbackHints);
        } catch (_) {
            return emptyConfig(fallbackHints);
        }
    }

    function writeStoredConfig(key, config) {
        try {
            storage.setItem(key, JSON.stringify(sanitizeConfig(config)));
            return true;
        } catch (_) {
            return false;
        }
    }

    function accountStorageKey(userId) {
        return 'gtn_keybindings_device_' + String(userId || 'guest');
    }

    function deviceToggleKey(userId) {
        return 'gtn_keybindings_device_enabled_' + String(userId || 'guest');
    }

    let initialized = false;
    let account = null;
    let accountConfig = emptyConfig(true);
    let guestConfig = readStoredConfig('gtn_keybindings_guest', true);
    let deviceConfig = emptyConfig(true);
    let deviceOverrideEnabled = false;
    let effectiveBindings = new Map(DEFAULT_BINDINGS);
    let effectiveShowHints = true;
    let capturingActionId = '';
    let saveStatus = '';

    let accountSaveTimer = null;
    let accountSaveInFlight = false;
    let accountChangeGeneration = 0;
    let dirtyAccountActions = new Set();
    let dirtyAccountHints = false;
    let renderScheduled = false;
    let hintsScheduled = false;
    let suppressHintObserver = false;
    let suppressHintObserverTimer = 0;
    const heldActionCodes = new Map();
    const heldAltCodes = new Set();
    let fixedSecondPageHeld = false;
    const channel = typeof BroadcastChannel === 'function' ? new BroadcastChannel(CHANNEL_NAME) : null;

    function accountBindings() {
        return materializeConfig(accountConfig, DEFAULT_BINDINGS);
    }

    function activeBaseBindings() {
        return account && deviceOverrideEnabled ? accountBindings() : DEFAULT_BINDINGS;
    }

    function activeConfig() {
        if (!account) return guestConfig;
        return deviceOverrideEnabled ? deviceConfig : accountConfig;
    }

    function bindingFor(actionId) {
        return effectiveBindings.get(actionId) || null;
    }

    function recomputeEffective(options = {}) {
        if (!account) {
            effectiveBindings = materializeConfig(guestConfig, DEFAULT_BINDINGS);
            effectiveShowHints = guestConfig.show_hints !== false;
        } else if (deviceOverrideEnabled) {
            const base = accountBindings();
            effectiveBindings = materializeConfig(deviceConfig, base);
            effectiveShowHints = deviceConfig.show_hints !== false;
        } else {
            effectiveBindings = accountBindings();
            effectiveShowHints = accountConfig.show_hints !== false;
        }
        scheduleRenderSettings();
        scheduleRefreshHints();
        if (options.broadcast) broadcastActiveConfig();
    }

    function persistActiveBindings(bindings, changedActionIds = []) {
        const changed = changedActionIds.filter(actionId => ACTION_BY_ID.has(actionId));
        effectiveBindings = new Map(bindings);
        if (!account) {
            guestConfig = configFromBindings(effectiveBindings, DEFAULT_BINDINGS, effectiveShowHints, guestConfig.revision);
            writeStoredConfig('gtn_keybindings_guest', guestConfig);
            recomputeEffective({ broadcast: true });
            return;
        }
        if (deviceOverrideEnabled) {
            deviceConfig = configFromBindings(effectiveBindings, accountBindings(), effectiveShowHints, deviceConfig.revision);
            writeStoredConfig(accountStorageKey(account.id), deviceConfig);
            recomputeEffective({ broadcast: true });
            return;
        }
        accountConfig = configFromBindings(effectiveBindings, DEFAULT_BINDINGS, effectiveShowHints, accountConfig.revision);
        changed.forEach(actionId => dirtyAccountActions.add(actionId));
        accountChangeGeneration += 1;
        host.patchAccountKeybindings(accountConfig);
        recomputeEffective();
        scheduleAccountSave();
    }

    function persistShowHints(value) {
        effectiveShowHints = value !== false;
        if (!account) {
            guestConfig.show_hints = effectiveShowHints;
            writeStoredConfig('gtn_keybindings_guest', guestConfig);
            recomputeEffective({ broadcast: true });
            return;
        }
        if (deviceOverrideEnabled) {
            deviceConfig.show_hints = effectiveShowHints;
            writeStoredConfig(accountStorageKey(account.id), deviceConfig);
            recomputeEffective({ broadcast: true });
            return;
        }
        accountConfig.show_hints = effectiveShowHints;
        dirtyAccountHints = true;
        accountChangeGeneration += 1;
        host.patchAccountKeybindings(accountConfig);
        recomputeEffective();
        scheduleAccountSave();
    }

    function broadcastActiveConfig() {
        if (!channel) return;
        const scope = !account ? 'guest' : (deviceOverrideEnabled ? 'device' : 'account');
        try {
            channel.postMessage({
                type: 'config', scope,
                user_id: account ? String(account.id) : '',
                config: activeConfig(),
            });
        } catch (error) {
            console.warn('[keybindings] cross-tab sync unavailable', error);
        }
    }

    function setDeviceOverride(enabled) {
        if (!account) return;
        deviceOverrideEnabled = !!enabled;
        storage.setItem(deviceToggleKey(account.id), deviceOverrideEnabled ? '1' : '0');
        if (deviceOverrideEnabled && !storage.getItem(accountStorageKey(account.id))) {
            deviceConfig = emptyConfig(accountConfig.show_hints !== false);
            writeStoredConfig(accountStorageKey(account.id), deviceConfig);
        }
        recomputeEffective({ broadcast: true });
    }

    function scheduleAccountSave(delay = 500) {
        if (!account || deviceOverrideEnabled) return;
        if (accountSaveTimer) clearTimeout(accountSaveTimer);
        accountSaveTimer = setTimeout(() => {
            accountSaveTimer = null;
            flushAccountSave();
        }, delay);
    }

    async function flushAccountSave() {
        if (accountSaveInFlight || !account || deviceOverrideEnabled) return;
        if (!dirtyAccountActions.size && !dirtyAccountHints) return;
        if (accountSaveTimer) {
            clearTimeout(accountSaveTimer);
            accountSaveTimer = null;
        }
        accountSaveInFlight = true;
        const userId = String(account.id);
        const generation = accountChangeGeneration;
        const payload = sanitizeConfig(accountConfig);
        payload.revision = accountConfig.revision;
        let shouldRetry = false;
        try {
            const response = await fetch('/api/account/keybindings', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ keybindings: payload, expected_revision: accountConfig.revision }),
                keepalive: true,
            });
            const data = await response.json().catch(() => ({}));
            if (!account || String(account.id) !== userId) return;
            const latestDesiredBindings = new Map(effectiveBindings);
            const latestDesiredHints = effectiveShowHints;
            if (response.status === 409 && data.keybindings) {
                const remote = sanitizeConfig(data.keybindings);
                const merged = materializeConfig(remote, DEFAULT_BINDINGS);
                dirtyAccountActions.forEach(actionId => merged.set(actionId, latestDesiredBindings.get(actionId) || null));
                const mergedHints = dirtyAccountHints ? latestDesiredHints : remote.show_hints !== false;
                accountConfig = configFromBindings(merged, DEFAULT_BINDINGS, mergedHints, remote.revision);
                host.patchAccountKeybindings(accountConfig);
                saveStatus = '';
                recomputeEffective();
                shouldRetry = true;
                return;
            }
            if (!response.ok || data.success === false || !data.keybindings) {
                throw new Error(data.error || 'save_failed');
            }
            const serverConfig = sanitizeConfig(data.keybindings);
            if (generation === accountChangeGeneration) {
                saveStatus = '';
                accountConfig = serverConfig;
                dirtyAccountActions.clear();
                dirtyAccountHints = false;
                host.patchAccountKeybindings(accountConfig);
                recomputeEffective();
                broadcastActiveConfig();
                host.toast(text('saved'));
            } else {
                accountConfig = configFromBindings(
                    latestDesiredBindings,
                    DEFAULT_BINDINGS,
                    latestDesiredHints,
                    serverConfig.revision,
                );
                host.patchAccountKeybindings(accountConfig);
                shouldRetry = true;
            }
        } catch (error) {
            console.warn('[keybindings] account save failed', error);
            saveStatus = text('save_failed');
            scheduleRenderSettings();
        } finally {
            accountSaveInFlight = false;
            if (shouldRetry || accountChangeGeneration > generation) scheduleAccountSave(100);
        }
    }

    function syncAccount(nextAccount) {
        const previousId = account && String(account.id);
        const nextId = nextAccount && nextAccount.id != null ? String(nextAccount.id) : '';
        account = nextAccount && nextAccount.id != null ? nextAccount : null;
        if (!account) {
            if (accountSaveTimer) clearTimeout(accountSaveTimer);
            accountSaveTimer = null;
            dirtyAccountActions.clear();
            dirtyAccountHints = false;
            accountConfig = emptyConfig(true);
            deviceOverrideEnabled = false;
            recomputeEffective();
            return;
        }
        const incoming = sanitizeConfig(account.keybindings || {});
        if (previousId !== nextId) {
            if (accountSaveTimer) clearTimeout(accountSaveTimer);
            accountSaveTimer = null;
            dirtyAccountActions.clear();
            dirtyAccountHints = false;
            accountChangeGeneration = 0;
            accountConfig = incoming;
            deviceOverrideEnabled = storage.getItem(deviceToggleKey(account.id)) === '1';
            deviceConfig = readStoredConfig(accountStorageKey(account.id), incoming.show_hints !== false);
        } else if (!dirtyAccountActions.size && !dirtyAccountHints && incoming.revision >= accountConfig.revision) {
            accountConfig = incoming;
        }
        recomputeEffective();
    }

    function handleChannelMessage(event) {
        const message = event && event.data;
        if (!message || message.type !== 'config') return;
        const myId = account ? String(account.id) : '';
        if (String(message.user_id || '') !== myId) return;
        if (message.scope === 'guest' && !account) {
            guestConfig = sanitizeConfig(message.config);
        } else if (message.scope === 'device' && account && deviceOverrideEnabled) {
            deviceConfig = sanitizeConfig(message.config);
        } else if (message.scope === 'account' && account && !deviceOverrideEnabled && !dirtyAccountActions.size && !dirtyAccountHints) {
            const incoming = sanitizeConfig(message.config);
            if (incoming.revision >= accountConfig.revision) accountConfig = incoming;
        } else {
            return;
        }
        recomputeEffective();
    }

    function actionForBinding(binding) {
        return ACTIONS.find(action => bindingFor(action.id) === binding) || null;
    }

    function isReservedBinding(binding) {
        if (!binding) return false;
        if (
            binding === 'Tab'
            || RESERVED_BINDINGS.has(binding)
            || FIXED_SELECTION_BINDINGS.has(binding)
        ) {
            return true;
        }
        return /^(Ctrl|Alt|Shift|Meta)$/.test(binding);
    }

    function setCaptureState(actionId) {
        capturingActionId = ACTION_BY_ID.has(actionId) ? actionId : '';
        scheduleRenderSettings();
    }

    async function assignBinding(actionId, binding) {
        if (!ACTION_BY_ID.has(actionId)) return false;
        const normalized = binding ? canonicalBinding(binding) : null;
        if (binding && !normalized) return false;
        if (normalized && isReservedBinding(normalized)) {
            host.toast(text('reserved'), 'error');
            return false;
        }
        const oldBinding = bindingFor(actionId);
        if (oldBinding === normalized) {
            setCaptureState('');
            return true;
        }
        const conflict = normalized ? actionForBinding(normalized) : null;
        if (conflict && conflict.id !== actionId) {
            const message = text('conflict_message').replace('{0}', actionLabel(conflict.id));
            const accepted = await host.confirm(text('conflict_title'), message);
            if (!accepted) return false;
            const swapped = new Map(effectiveBindings);
            swapped.set(actionId, normalized);
            swapped.set(conflict.id, oldBinding || null);
            persistActiveBindings(swapped, [actionId, conflict.id]);
        } else {
            const next = new Map(effectiveBindings);
            next.set(actionId, normalized);
            persistActiveBindings(next, [actionId]);
        }
        setCaptureState('');
        return true;
    }

    function resetAction(actionId) {
        return assignBinding(actionId, DEFAULT_BINDINGS.get(actionId) || null);
    }

    async function resetAllBindings() {
        const accepted = await host.confirm(text('title'), text('reset_confirm'));
        if (!accepted) return;
        effectiveShowHints = true;
        persistActiveBindings(new Map(DEFAULT_BINDINGS), ACTIONS.map(action => action.id));
        persistShowHints(true);
    }

    function handleCaptureKeydown(event) {
        if (!capturingActionId) return false;
        event.preventDefault();
        event.stopImmediatePropagation();
        if (MODIFIER_CODES.has(event.code)) return true;
        if (event.code === 'Escape') {
            setCaptureState('');
            host.toast(text('capture_cancelled'));
            return true;
        }
        if (event.code === 'Backspace' || event.code === 'Delete') {
            assignBinding(capturingActionId, null);
            return true;
        }
        const binding = bindingFromEvent(event);
        if (binding) assignBinding(capturingActionId, binding);
        return true;
    }

    function handleFixedKeydown(event) {
        if (event.code === 'AltLeft' || event.code === 'AltRight') {
            if (!event.repeat) {
                heldAltCodes.add(event.code);
                scheduleRefreshHints();
            }
            event.preventDefault();
            event.stopPropagation();
            return true;
        }
        if (event.repeat || event.ctrlKey || event.altKey || event.shiftKey || event.metaKey) return false;
        if (event.code === 'Backquote') {
            fixedSecondPageHeld = true;
            host.dispatch('hand_second_page', event, { active: true });
            event.preventDefault();
            event.stopPropagation();
            return true;
        }
        const match = /^Digit([0-9])$/.exec(event.code);
        if (!match) return false;
        const slot = match[1] === '0' ? 10 : Number(match[1]);
        const handled = host.dispatch('select_slot_' + slot, event, {
            secondPage: fixedSecondPageHeld,
        });
        if (handled) {
            event.preventDefault();
            event.stopPropagation();
        }
        return handled;
    }

    function handleKeydown(event) {
        if (handleCaptureKeydown(event)) return;
        if (event.code === 'AltLeft' || event.code === 'AltRight') {
            handleFixedKeydown(event);
            return;
        }
        if (host.isTypingTarget(event.target)) return;
        const focusedButton = event.target && event.target.closest
            ? event.target.closest('button, [role="button"]')
            : null;
        if (
            focusedButton
            && ['Enter', 'NumpadEnter', 'Space'].includes(event.code)
            && !host.hasVirtualFocus?.()
        ) return;
        if (handleFixedKeydown(event)) return;
        const binding = bindingFromEvent(event);
        if (!binding || event.repeat) return;
        const action = actionForBinding(binding);
        if (!action) return;
        const options = { secondPage: fixedSecondPageHeld };
        if (action.hold) {
            heldActionCodes.set(action.id, event.code);
            options.active = true;
        }
        const handled = host.dispatch(action.id, event, options);
        if (handled) {
            event.preventDefault();
            event.stopPropagation();
        }
    }

    function handleKeyup(event) {
        if (event.code === 'AltLeft' || event.code === 'AltRight') {
            heldAltCodes.delete(event.code);
            scheduleRefreshHints();
        }
        if (event.code === 'Backquote' && fixedSecondPageHeld) {
            fixedSecondPageHeld = false;
            host.dispatch('hand_second_page', event, { active: false });
        }
        heldActionCodes.forEach((code, actionId) => {
            if (code !== event.code) return;
            heldActionCodes.delete(actionId);
            host.dispatch(actionId, event, { active: false });
        });
    }

    function releaseHeldActions() {
        heldActionCodes.forEach((_, actionId) => host.dispatch(actionId, null, { active: false }));
        heldActionCodes.clear();
        heldAltCodes.clear();
        if (fixedSecondPageHeld) host.dispatch('hand_second_page', null, { active: false });
        fixedSecondPageHeld = false;
        scheduleRefreshHints();
    }

    function byId(id) {
        return document.getElementById(id);
    }

    function setElementText(id, value) {
        const element = byId(id);
        if (element) element.textContent = value;
    }

    function refreshText() {
        setElementText('settings-tab-controls', text('tab'));
        setElementText('settings-section-controls', text('title'));
        setElementText('settings-label-show-shortcut-hints', text('show_hints'));
        setElementText('settings-label-device-keybindings', text('device_override'));
        setElementText('btn-keybindings-help', text('help'));
        setElementText('btn-keybindings-reset-all', text('reset_all'));
        scheduleRenderSettings();
        scheduleRefreshHints();
    }

    function scheduleRenderSettings() {
        if (!initialized || renderScheduled) return;
        renderScheduled = true;
        requestAnimationFrame(() => {
            renderScheduled = false;
            renderSettings();
        });
    }

    function storageStatusText() {
        if (!account) {
            return storage.isPersistent('gtn_keybindings_guest')
                ? text('guest_storage')
                : text('session_storage');
        }
        if (deviceOverrideEnabled) {
            return storage.isPersistent(accountStorageKey(account.id))
                ? text('device_storage')
                : text('session_storage');
        }
        return text('account_storage');
    }

    function makeIconButton(symbol, title, handler) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'keybind-icon-button';
        button.textContent = symbol;
        button.title = title;
        button.setAttribute('aria-label', title);
        button.addEventListener('click', handler);
        return button;
    }

    function renderSettings() {
        const list = byId('settings-keybind-list');
        if (!list) return;
        const showHints = byId('settings-show-shortcut-hints');
        if (showHints) showHints.checked = effectiveShowHints;
        const deviceRow = byId('settings-device-keybindings-row');
        const deviceToggle = byId('settings-device-keybindings');
        if (deviceRow) deviceRow.classList.toggle('hidden', !account);
        if (deviceToggle) deviceToggle.checked = !!(account && deviceOverrideEnabled);
        const status = byId('settings-keybindings-storage-status');
        if (status) {
            status.textContent = saveStatus || storageStatusText();
            status.classList.toggle('is-error', saveStatus === text('save_failed'));
        }

        list.innerHTML = '';
        GROUPS.forEach(groupId => {
            const section = document.createElement('section');
            section.className = 'keybind-group';
            const heading = document.createElement('h5');
            heading.textContent = actionLabel(groupId);
            section.appendChild(heading);

            ACTIONS.filter(action => action.group === groupId).forEach(action => {
                const row = document.createElement('div');
                row.className = 'keybind-row';
                row.dataset.actionId = action.id;
                const label = document.createElement('span');
                label.className = 'keybind-action-label';
                label.textContent = actionLabel(action.id);
                const capture = document.createElement('button');
                capture.type = 'button';
                capture.className = 'keybind-capture-button';
                capture.classList.toggle('is-capturing', capturingActionId === action.id);
                capture.textContent = capturingActionId === action.id
                    ? text('press_key')
                    : displayBinding(bindingFor(action.id));
                capture.title = text('change');
                capture.addEventListener('click', () => setCaptureState(action.id));
                const defaultBinding = DEFAULT_BINDINGS.get(action.id) || null;
                if (bindingFor(action.id) === defaultBinding) capture.dataset.default = text('default_mark');
                const controls = document.createElement('span');
                controls.className = 'keybind-row-controls';
                controls.appendChild(makeIconButton('↺', text('reset'), () => resetAction(action.id)));
                controls.appendChild(makeIconButton('×', text('clear'), () => assignBinding(action.id, null)));
                row.append(label, capture, controls);
                section.appendChild(row);
            });
            list.appendChild(section);
        });
    }

    function bindSettingsControls() {
        const showHints = byId('settings-show-shortcut-hints');
        if (showHints && !showHints.dataset.keybindingsBound) {
            showHints.dataset.keybindingsBound = '1';
            showHints.addEventListener('change', () => persistShowHints(showHints.checked));
        }
        const deviceToggle = byId('settings-device-keybindings');
        if (deviceToggle && !deviceToggle.dataset.keybindingsBound) {
            deviceToggle.dataset.keybindingsBound = '1';
            deviceToggle.addEventListener('change', () => setDeviceOverride(deviceToggle.checked));
        }
        const reset = byId('btn-keybindings-reset-all');
        if (reset && !reset.dataset.keybindingsBound) {
            reset.dataset.keybindingsBound = '1';
            reset.addEventListener('click', resetAllBindings);
        }
        const help = byId('btn-keybindings-help');
        if (help && !help.dataset.keybindingsBound) {
            help.dataset.keybindingsBound = '1';
            help.addEventListener('click', showHelp);
        }
    }

    function elementIsVisible(element) {
        if (!element || element.classList.contains('hidden')) return false;
        const style = window.getComputedStyle ? window.getComputedStyle(element) : null;
        if (style && (style.display === 'none' || style.visibility === 'hidden')) return false;
        const rect = element.getBoundingClientRect();
        return rect.width > 1 && rect.height > 1;
    }

    function appendHint(element, label, extraClass = '') {
        if (!element || !label) return;
        const hintHost = element.matches?.('input, textarea, select, option, img')
            ? element.parentElement
            : element;
        if (!hintHost) return;
        const existing = Array.from(hintHost.children || []).find(child => (
            child.classList?.contains('shortcut-hint-badge')
        ));
        if (existing) {
            const labels = existing.textContent.split(' / ').map(value => value.trim());
            if (!labels.includes(label)) existing.textContent += ` / ${label}`;
            if (extraClass) existing.classList.add(extraClass);
            return;
        }
        hintHost.classList.add('shortcut-hint-host');
        const position = window.getComputedStyle
            ? window.getComputedStyle(hintHost).position
            : '';
        if (!position || position === 'static') {
            hintHost.classList.add('shortcut-hint-host-static');
        }
        const badge = document.createElement('kbd');
        badge.className = 'shortcut-hint-badge' + (extraClass ? ' ' + extraClass : '');
        badge.textContent = label;
        badge.setAttribute('aria-hidden', 'true');
        hintHost.appendChild(badge);
    }

    function slotHint(index) {
        const slot = (index % 10) + 1;
        const slotBinding = String(slot === 10 ? 0 : slot);
        if (index < 10) return slotBinding;
        return '`+' + slotBinding;
    }

    function decorateSequence(selector) {
        const elements = Array.from(document.querySelectorAll(selector)).filter(elementIsVisible);
        elements.slice(0, 20).forEach((element, index) => {
            appendHint(element, slotHint(index), 'shortcut-hint-slot');
        });
    }

    function decorateAction(selector, actionId) {
        const rawBinding = bindingFor(actionId);
        if (!rawBinding) return;
        const binding = displayBinding(rawBinding, true);
        document.querySelectorAll(selector).forEach(element => {
            if (elementIsVisible(element)) appendHint(element, binding, 'shortcut-hint-action');
        });
    }

    function normalizeContextElements(value) {
        const raw = Array.isArray(value) ? value : (value ? [value] : []);
        const elements = [];
        raw.forEach(item => {
            if (typeof item === 'string') {
                document.querySelectorAll(item).forEach(element => elements.push(element));
            } else if (item && item.nodeType === 1) {
                elements.push(item);
            }
        });
        return [...new Set(elements)].filter(elementIsVisible);
    }

    function activeShortcutContext() {
        if (typeof host.getShortcutContext !== 'function') return null;
        try {
            const context = host.getShortcutContext();
            if (!context || typeof context !== 'object') return null;
            return {
                id: String(context.id || ''),
                slots: normalizeContextElements(context.slots).slice(0, 20),
                slotLabel: String(context.slotLabel || ''),
                slotLabels: Array.isArray(context.slotLabels)
                    ? context.slotLabels.map(label => String(label || ''))
                    : [],
                actions: Array.isArray(context.actions) ? context.actions : [],
            };
        } catch (error) {
            console.warn('[keybindings] shortcut context failed', error);
            return null;
        }
    }

    function appendContextPanelItem(panel, binding, label) {
        if (!binding || !label) return;
        const item = document.createElement('span');
        item.className = 'shortcut-context-hint-item';
        const key = document.createElement('kbd');
        key.textContent = binding;
        const textNode = document.createElement('span');
        textNode.textContent = label;
        item.append(key, textNode);
        panel.appendChild(item);
    }

    function renderContextHints(context) {
        if (!context) return false;
        const panel = document.createElement('div');
        panel.id = 'shortcut-context-hints';
        panel.className = 'shortcut-context-hints';
        panel.setAttribute('aria-hidden', 'true');
        const heading = document.createElement('strong');
        heading.className = 'shortcut-context-hints-title';
        heading.textContent = text('current_shortcuts');
        panel.appendChild(heading);

        if (context.slots.length) {
            context.slots.forEach((element, index) => {
                const binding = slotHint(index);
                appendHint(element, binding, 'shortcut-hint-slot');
                const explicitLabel = context.slotLabels[index] || '';
                if (explicitLabel) appendContextPanelItem(panel, binding, explicitLabel);
            });
            if (!context.slotLabels.some(Boolean)) {
                const firstRange = context.slots.length <= 10
                    ? `1–${context.slots.length === 10 ? 0 : context.slots.length}`
                    : '1–0';
                appendContextPanelItem(
                    panel,
                    firstRange,
                    context.slotLabel || actionLabel('fixed_slots_1_10'),
                );
                if (context.slots.length > 10) {
                    appendContextPanelItem(
                        panel,
                        '`+1–0',
                        context.slotLabel || actionLabel('fixed_slots_11_20'),
                    );
                }
            }
        }

        const renderedActions = new Set();
        context.actions.forEach(raw => {
            const entry = typeof raw === 'string' ? { id: raw } : (raw || {});
            const actionId = String(entry.id || '');
            if (!ACTION_BY_ID.has(actionId) || renderedActions.has(actionId)) return;
            const rawBinding = bindingFor(actionId);
            if (!rawBinding) return;
            renderedActions.add(actionId);
            const binding = displayBinding(rawBinding, true);
            const label = String(entry.label || actionLabel(actionId));
            normalizeContextElements(entry.elements).forEach(element => {
                appendHint(element, binding, 'shortcut-hint-action');
            });
            appendContextPanelItem(panel, binding, label);
        });

        if (!renderedActions.has('shortcut_help') && bindingFor('shortcut_help')) {
            appendContextPanelItem(
                panel,
                displayBinding(bindingFor('shortcut_help'), true),
                actionLabel('shortcut_help'),
            );
        }
        if (!panel.querySelector('.shortcut-context-hint-item')) return true;
        document.body.appendChild(panel);
        return true;
    }

    function refreshHints() {
        if (suppressHintObserverTimer) {
            clearTimeout(suppressHintObserverTimer);
            suppressHintObserverTimer = 0;
        }
        suppressHintObserver = true;
        document.querySelectorAll('.shortcut-hint-badge').forEach(badge => badge.remove());
        document.querySelectorAll('.shortcut-hint-host').forEach(element => {
            element.classList.remove('shortcut-hint-host', 'shortcut-hint-host-static');
        });
        const oldPanel = byId('shortcut-context-hints');
        if (oldPanel) oldPanel.remove();
        const previewActive = effectiveShowHints && heldAltCodes.size > 0;
        if (previewActive) {
            const context = activeShortcutContext();
            if (!renderContextHints(context)) {
                decorateSequence('#response-panel .counter-card-btn, #response-panel .response-btn-row .btn');
                decorateSequence('#game-prompt.active #game-prompt-options .game-prompt-option');
                decorateSequence('#modal.active .v2-ui-picker-option');
                decorateSequence('#modal.active .reorder-deck-entry:not(.reorder-clone)');
                decorateSequence('#draft-options .card');
                decorateSequence('#event-options .event-card');
                decorateSequence('#classic-hand-fan .classic-hand-card');
                decorateSequence('#you-hand > .card');
                decorateSequence('#story-hand .story-hand-card');
                decorateSequence('#story-card-choice-dialog[open] .story-card-choice-select-item');
                decorateSequence('#story-blessing:not(.hidden) .story-choice-option');
                decorateSequence('#story-room:not(.hidden) .story-choice-option, #story-room:not(.hidden) .story-card');
                decorateSequence('#story-reward:not(.hidden) .story-card');
                decorateSequence('#story-run:not(.hidden) .story-map-node.is-actionable');
                decorateAction('#btn-end-turn, #classic-end-turn, #story-end-turn', 'end_turn');
                decorateAction('#btn-view-deck, #classic-view-deck, #btn-spectate-view-deck, #story-draw-pile', 'view_draw');
                decorateAction('#btn-view-discard, #classic-view-discard, #btn-spectate-view-discard, #story-discard-pile', 'view_discard');
                decorateAction('#btn-view-exile, #classic-view-exile, #btn-spectate-view-exile, #story-exile-pile', 'view_exile');
                decorateAction('[data-battle-panel-tab="log"]', 'view_log');
                decorateAction('[data-battle-panel-tab="spectators"]', 'view_spectators');
                decorateAction('#pass-btn', 'pass_response');
                decorateAction('#game-prompt-cancel', 'cancel');
                decorateAction('#btn-draft-reroll, #btn-event-reroll', 'refresh');
                decorateAction('#btn-game-chat-send, #btn-classic-game-chat-send, #btn-phase-chat-send', 'focus_chat');
                decorateAction('#btn-keybindings-help', 'shortcut_help');
            }
        }
        const chatBinding = previewActive && bindingFor('focus_chat')
            ? displayBinding(bindingFor('focus_chat'), true)
            : '';
        ['game-chat-input', 'classic-game-chat-input', 'phase-chat-input', 'lobby-chat-input'].forEach(id => {
            const input = byId(id);
            if (!input) return;
            if (chatBinding) input.dataset.shortcut = chatBinding;
            else delete input.dataset.shortcut;
        });
        suppressHintObserverTimer = window.setTimeout(() => {
            suppressHintObserver = false;
            suppressHintObserverTimer = 0;
        }, 0);
    }

    function scheduleRefreshHints() {
        if (!initialized || hintsScheduled) return;
        hintsScheduled = true;
        requestAnimationFrame(() => {
            hintsScheduled = false;
            refreshHints();
        });
    }

    function mutationContainsOnlyHints(mutation) {
        const nodes = [...mutation.addedNodes, ...mutation.removedNodes].filter(node => node.nodeType === 1);
        return nodes.length > 0 && nodes.every(node => (
            node.classList.contains('shortcut-hint-badge')
            || node.classList.contains('shortcut-context-hints')
        ));
    }

    function observeActionSurfaces() {
        const observer = new MutationObserver(mutations => {
            if (
                suppressHintObserver
                || !effectiveShowHints
                || heldAltCodes.size === 0
                || mutations.every(mutationContainsOnlyHints)
            ) return;
            scheduleRefreshHints();
        });
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['class', 'disabled', 'aria-hidden', 'open'],
        });
    }

    function closeHelp() {
        const modal = byId('modal');
        if (modal) {
            modal.classList.remove('shortcut-help-active');
            modal.classList.remove('active');
            modal.classList.add('hidden');
            modal.setAttribute('aria-hidden', 'true');
        }
    }

    function showHelp() {
        const modal = byId('modal');
        const content = byId('modal-content');
        if (!modal || !content) return;
        if (modal.classList.contains('active') && content.classList.contains('shortcut-help-modal')) {
            closeHelp();
            return;
        }
        content.className = 'modal-inner shortcut-help-modal';
        content.innerHTML = '';
        const title = document.createElement('h3');
        title.textContent = text('help_title');
        content.appendChild(title);
        const groups = document.createElement('div');
        groups.className = 'shortcut-help-groups';
        GROUPS.forEach(groupId => {
            const section = document.createElement('section');
            section.className = 'shortcut-help-group';
            const heading = document.createElement('h4');
            heading.textContent = actionLabel(groupId);
            section.appendChild(heading);
            [
                ...FIXED_HELP_ACTIONS.filter(action => action.group === groupId),
                ...ACTIONS.filter(action => action.group === groupId),
            ].forEach(action => {
                const row = document.createElement('div');
                row.className = 'shortcut-help-row';
                const label = document.createElement('span');
                label.textContent = actionLabel(action.id);
                const key = document.createElement('kbd');
                key.textContent = action.displayBinding || displayBinding(bindingFor(action.id));
                row.append(label, key);
                section.appendChild(row);
            });
            groups.appendChild(section);
        });
        content.appendChild(groups);
        const buttons = document.createElement('div');
        buttons.className = 'modal-buttons';
        const close = document.createElement('button');
        close.type = 'button';
        close.className = 'btn btn-primary';
        close.textContent = text('close');
        close.addEventListener('click', closeHelp);
        buttons.appendChild(close);
        content.appendChild(buttons);
        modal.classList.add('shortcut-help-active');
        modal.classList.remove('hidden');
        modal.classList.add('active');
        modal.setAttribute('aria-hidden', 'false');
    }

    function init() {
        if (initialized) return;
        initialized = true;
        bindSettingsControls();
        document.addEventListener('keydown', handleKeydown, true);
        document.addEventListener('keyup', handleKeyup, true);
        window.addEventListener('blur', releaseHeldActions);
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) flushAccountSave();
        });
        window.addEventListener('beforeunload', () => {
            flushAccountSave();
        });
        if (channel) {
            channel.addEventListener('message', handleChannelMessage);
        }
        syncAccount(host.getAccount());
        refreshText();
        observeActionSurfaces();
        renderSettings();
        refreshHints();
    }

    window.GTN_KEYBINDINGS = {
        init,
        syncAccount,
        refreshText,
        renderSettings,
        refreshHints: scheduleRefreshHints,
        showHelp,
        text,
        getBinding(actionId) {
            return bindingFor(actionId);
        },
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }
})();
