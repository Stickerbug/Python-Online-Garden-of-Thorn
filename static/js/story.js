(() => {
    'use strict';

    const $ = (id) => document.getElementById(id);
    const SVG_NS = 'http://www.w3.org/2000/svg';
    const STORY_MAP_NODE_RADIUS = 25;
    const STORY_MAP_EDGE_INSET = STORY_MAP_NODE_RADIUS + 4;
    const STORY_MAP_ROOM_ICON_URLS = Object.freeze({
        blessing: '/static/assets/story-room-icons/blessing.svg',
        combat: '/static/assets/story-room-icons/combat.svg',
        elite: '/static/assets/story-room-icons/elite.svg',
        event: '/static/assets/story-room-icons/event.svg',
        rest: '/static/assets/story-room-icons/rest.svg',
        shop: '/static/assets/story-room-icons/shop.svg',
        chest: '/static/assets/story-room-icons/chest.svg',
    });
    const VIEWS = [
        'story-loading', 'story-empty', 'story-version-old', 'story-blessing', 'story-run',
        'story-combat', 'story-room', 'story-reward', 'story-terminal',
    ];
    let activeRun = null;
    let storyContent = null;
    let storyProgress = null;
    let contentVersion = '';
    let selectedStoryCharacterId = 'common_flower';
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
    let storyCardTermNavigation = null;
    let storyCardTermWheelLockedUntil = 0;
    let storyCardTermPointerStart = null;
    let storyCombatEntranceAnimating = false;
    let storyMapPreviewOpen = false;
    let storyPlaybackRate = document.documentElement.classList.contains('story-speed-2x') ? 2 : 1;
    let pendingStorySaveId = 0;
    let storyManualSaveInFlight = false;
    let storyDiscoveries = [];
    let storyCodexMode = 'cards';
    let storyCodexSearch = '';
    let storyCodexSelectedId = '';
    let storyCodexTalentKind = 'relic';
    let storyCodexTermKind = 'status';
    let storyCodexHistory = [];
    let storyCodexCardFiltersReady = false;
    let storySkinMouthAnimation = null;
    let storySkinDamageTimer = 0;
    let storySkinDamageUntil = 0;
    let storyMechanicalTrackFrame = 0;
    let storyCoopPartyBundle = { party: null, viewer: null, run: null };
    let storyCoopPartyLoaded = false;
    let storyCoopInviteCode = '';
    let storyCoopPartyPollTimer = 0;
    let storyCoopPartyLoadPromise = null;
    let storyCoopPartyLoadEpoch = 0;
    let storyCoopLobbyEpoch = 0;
    let storyCoopMemberSignature = '';
    let storyCoopMutationInFlight = false;
    let storyCoopConfirmationInFlight = false;
    let storyCoopBootstrapLoaded = false;
    let selectedStoryCoopCharacterId = 'common_flower';
    let storyCoopCombatSession = null;
    let storyCoopCombatEpoch = 0;
    const storyMechanicalTrackMotions = new Map();
    const storyActiveMechanicalTrackCards = new Map();
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
    const STORY_MECHANICAL_TRACK_PERIOD_MS = 22000;
    const STORY_MECHANICAL_TRACK_TRIGGER_ANGLE = -90;
    const STORY_COOP_PARTY_POLL_MS = 2500;
    const STORY_COOP_COMBAT_POLL_MS = 1200;
    const STORY_MANUAL_SAVE_STABLE_PHASES = new Set([
        'journey_setup', 'easy_relic', 'blessing', 'map', 'combat',
        'room', 'reward', 'stage_choice', 'complete', 'game_over',
    ]);
    const STORY_BACKDROP_LAYOUT_VERSION = 'story-backdrop-v3';
    const STORY_BACKDROP_BIOMES = Object.freeze(['garden', 'desert', 'ocean', 'jungle', 'factory']);
    const STORY_BACKDROP_LANDMARKS = Object.freeze({
        garden: Object.freeze([
            Object.freeze({ className: 'is-sunflower', src: '/static/assets/story-backgrounds/garden-sunflower.svg', rotation: [-165, 165] }),
            Object.freeze({ className: 'is-rock', src: '/static/assets/story-backgrounds/garden-rock.svg', rotation: [-165, 165] }),
        ]),
        jungle: Object.freeze([
            Object.freeze({ className: 'is-jungle-branch', src: '/static/assets/story-backgrounds/jungle-branch.svg', rotation: [-180, 180] }),
            Object.freeze({ className: 'is-jungle-leaf', src: '/static/assets/story-backgrounds/jungle-leaf.svg', rotation: [-180, 180] }),
        ]),
        ocean: Object.freeze([
            Object.freeze({ className: 'is-ocean-bubble', src: '/static/assets/story-backgrounds/ocean-bubble.svg', rotation: [-24, 24] }),
            Object.freeze({ className: 'is-ocean-lily', src: '/static/assets/story-backgrounds/ocean-lily.svg', rotation: [-28, 28] }),
        ]),
        factory: Object.freeze([
            Object.freeze({ className: 'is-factory-plate', src: '/static/assets/story-backgrounds/factory-plate.svg', rotation: [-180, 180] }),
            Object.freeze({ className: 'is-factory-gear', src: '/static/assets/story-backgrounds/factory-gear.svg', rotation: [-180, 180] }),
        ]),
    });
    const storyBackdropSignatures = new WeakMap();
    const STORY_SKIN_MOUTH_NORMAL_POINTS = Object.freeze([20, 18, 36, 32, 64, 32, 80, 18]);
    const STORY_SKIN_MOUTH_HURT_POINTS = Object.freeze([20, 26, 36, 12, 64, 12, 80, 26]);

    function storyBackdropHash(value) {
        let hash = 0x811c9dc5;
        const text = String(value || '');
        for (let index = 0; index < text.length; index += 1) {
            hash ^= text.charCodeAt(index);
            hash = Math.imul(hash, 0x01000193);
        }
        return hash >>> 0;
    }

    function storyBackdropUnit(seed, key) {
        return storyBackdropHash(`${seed}:${key}`) / 0x100000000;
    }

    function storyBackdropRange(seed, key, minimum, maximum) {
        return minimum + storyBackdropUnit(seed, key) * (maximum - minimum);
    }

    function clearStorySeededBackdrop(container) {
        if (container) storyBackdropSignatures.delete(container);
        container?.replaceChildren();
        container?.classList.remove('is-active');
        if (container) delete container.dataset.biome;
    }

    function appendStoryBackdropBase(container, seed, biome) {
        if (biome === 'garden') return;
        const sizeRanges = {
            desert: [112, 158],
            jungle: [142, 192],
            ocean: [176, 232],
            factory: [126, 176],
        };
        const range = sizeRanges[biome];
        if (!range) return;
        const base = document.createElement('span');
        const size = storyBackdropRange(seed, 'base:size', range[0], range[1]);
        const offsetX = storyBackdropRange(seed, 'base:x', -size, 0);
        const offsetY = storyBackdropRange(seed, 'base:y', -size, 0);
        base.className = `story-seeded-backdrop-base is-${biome}`;
        base.style.backgroundSize = `${size.toFixed(2)}px ${size.toFixed(2)}px`;
        base.style.backgroundPosition = `${offsetX.toFixed(2)}px ${offsetY.toFixed(2)}px`;
        container.append(base);
    }

    function appendGardenBackdropPatches(container, seed) {
        const fragment = document.createDocumentFragment();
        const columns = 10;
        const rows = 7;
        for (let row = 0; row < rows; row += 1) {
            for (let column = 0; column < columns; column += 1) {
                const key = `patch:${column}:${row}`;
                if (storyBackdropUnit(seed, `${key}:present`) > .92) continue;
                const patch = document.createElement('span');
                const dark = storyBackdropUnit(seed, `${key}:tone`) < .58;
                patch.className = `story-seeded-backdrop-patch ${dark ? 'is-dark' : 'is-light'}`;
                const left = ((column + storyBackdropRange(seed, `${key}:x`, .12, .88)) / columns) * 100;
                const top = ((row + storyBackdropRange(seed, `${key}:y`, .12, .88)) / rows) * 100;
                const width = storyBackdropRange(seed, `${key}:width`, 3.2, 7.2);
                const height = width * storyBackdropRange(seed, `${key}:ratio`, .68, 1.18);
                const rotation = storyBackdropRange(seed, `${key}:rotation`, -80, 80);
                patch.style.left = `${left.toFixed(3)}%`;
                patch.style.top = `${top.toFixed(3)}%`;
                patch.style.width = `${width.toFixed(3)}vmin`;
                patch.style.height = `${height.toFixed(3)}vmin`;
                patch.style.transform = `translate(-50%, -50%) rotate(${rotation.toFixed(2)}deg)`;
                fragment.append(patch);
            }
        }
        container.append(fragment);
    }

    function appendDesertBackdropPatches(container, seed) {
        const fragment = document.createDocumentFragment();
        const columns = 10;
        const rows = 7;
        for (let row = 0; row < rows; row += 1) {
            for (let column = 0; column < columns; column += 1) {
                const key = `desert:${column}:${row}`;
                if (storyBackdropUnit(seed, `${key}:present`) > .9) continue;
                const patch = document.createElement('span');
                const dune = storyBackdropUnit(seed, `${key}:kind`) < .68;
                const left = ((column + storyBackdropRange(seed, `${key}:x`, .12, .88)) / columns) * 100;
                const top = ((row + storyBackdropRange(seed, `${key}:y`, .12, .88)) / rows) * 100;
                const width = storyBackdropRange(seed, `${key}:width`, 3.4, 7.8);
                const height = width * storyBackdropRange(seed, `${key}:ratio`, .28, .62);
                const rotation = storyBackdropRange(seed, `${key}:rotation`, -24, 24);
                patch.className = `story-seeded-backdrop-patch ${dune ? 'is-desert-dune' : 'is-desert-stone'}`;
                patch.style.left = `${left.toFixed(3)}%`;
                patch.style.top = `${top.toFixed(3)}%`;
                patch.style.width = `${width.toFixed(3)}vmin`;
                patch.style.height = `${height.toFixed(3)}vmin`;
                patch.style.transform = `translate(-50%, -50%) rotate(${rotation.toFixed(2)}deg)`;
                fragment.append(patch);
            }
        }
        container.append(fragment);
    }

    function appendStoryBackdropLandmarks(container, seed, biome) {
        const assets = STORY_BACKDROP_LANDMARKS[biome];
        if (!assets?.length) return;
        const fragment = document.createDocumentFragment();
        const columns = 5;
        const rows = 3;
        for (let row = 0; row < rows; row += 1) {
            for (let column = 0; column < columns; column += 1) {
                const key = `landmark:${column}:${row}`;
                if (storyBackdropUnit(seed, `${key}:present`) > .76) continue;
                const assetIndex = Math.min(
                    assets.length - 1,
                    Math.floor(storyBackdropUnit(seed, `${key}:kind`) * assets.length),
                );
                const asset = assets[assetIndex];
                const image = document.createElement('img');
                const left = ((column + storyBackdropRange(seed, `${key}:x`, .18, .82)) / columns) * 100;
                const top = ((row + storyBackdropRange(seed, `${key}:y`, .18, .82)) / rows) * 100;
                const size = storyBackdropRange(seed, `${key}:size`, 5.5, 9.5);
                const rotation = storyBackdropRange(seed, `${key}:rotation`, asset.rotation[0], asset.rotation[1]);
                image.className = `story-seeded-backdrop-landmark ${asset.className}`;
                image.src = asset.src;
                image.alt = '';
                image.draggable = false;
                image.style.left = `${left.toFixed(3)}%`;
                image.style.top = `${top.toFixed(3)}%`;
                image.style.width = `clamp(36px, ${size.toFixed(3)}vmin, 96px)`;
                image.style.transform = `translate(-50%, -50%) rotate(${rotation.toFixed(2)}deg)`;
                fragment.append(image);
            }
        }
        container.append(fragment);
    }

    function renderStorySeededBackdrop(run, containerId = 'story-seeded-backdrop') {
        const container = typeof containerId === 'string' ? $(containerId) : containerId;
        if (!container) return;
        const mainBackdrop = container.id === 'story-seeded-backdrop';
        const state = run?.state;
        const biome = String(state?.biome || '');
        const visualSeed = String(run?.visual_seed || run?.seed || run?.id || '');
        if (!state || !STORY_BACKDROP_BIOMES.includes(biome) || !visualSeed) {
            clearStorySeededBackdrop(container);
            if (mainBackdrop) delete document.body.dataset.storyBiome;
            return;
        }
        if (mainBackdrop) document.body.dataset.storyBiome = biome;
        const signature = [
            STORY_BACKDROP_LAYOUT_VERSION,
            visualSeed,
            Number(state.stage || 1),
            biome,
        ].join(':');
        if (signature === storyBackdropSignatures.get(container)) return;
        storyBackdropSignatures.set(container, signature);
        container.replaceChildren();
        container.dataset.biome = biome;
        appendStoryBackdropBase(container, signature, biome);
        if (biome === 'garden') appendGardenBackdropPatches(container, signature);
        if (biome === 'desert') appendDesertBackdropPatches(container, signature);
        appendStoryBackdropLandmarks(container, signature, biome);
        container.classList.add('is-active');
    }

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
        attack_blocked: 'attack_blocked',
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
            saveManager: 'Save / Load', saveCopy: 'Available after the server finishes the current action. The latest 3 saves are kept.',
            saveCurrent: 'Save Current Progress', loadSave: 'Load', noSaves: 'No manual saves yet',
            deleteSave: 'Delete', deleteSaveTitle: 'Delete this save?', deleteSaveCopy: 'This manual save will be removed.', saveDeleted: 'Save deleted',
            saveCurrentSlot: 'Current', savePreviousSlot: (value) => `Previous ${value}`,
            saveSucceeded: 'Journey saved', loadSucceeded: 'Journey loaded',
            loadSaveTitle: 'Load this save?', loadSaveCopy: 'Your current journey state will be replaced.',
            saveOnlyOnMap: 'Wait for the current story action to finish before saving or loading',
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
            codexCards: 'Cards', codexEnemies: 'Enemies', codexTalents: 'Talents', codexBooks: 'Enchantment Books', codexTerms: 'Terms',
            codexSearch: 'Search discovered content', codexRarity: 'Rarity', codexType: 'Type',
            codexAll: 'All', codexClear: 'Clear', codexResults: (count) => `${count} result(s)`,
            codexDiscovered: (found, total) => `Discovered ${found}/${total}`,
            codexEmpty: 'No matching discoveries', codexUnknownTalent: 'Unnamed blessing',
            codexRelics: 'Talents', codexBlessings: 'Blessings', codexStatuses: 'Statuses',
            codexTags: 'Tags', codexTraits: 'Enemy effects', codexResources: 'Resources',
            codexHealth: 'Health', codexObservedIntents: (count) => `${count} observed intent(s)`,
            codexBack: 'Back to previous entry', codexRelated: 'Related discoveries', codexViewRelated: 'View in compendium',
            codexNew: 'New compendium entry', codexNewCount: (count) => `${count} new compendium entries`,
            battleWon: 'Battle won', chooseCard: 'Choose a card', skip: 'Skip card',
            rewards: 'Battle rewards', rewardCopy: 'Claim each reward before continuing.',
            claim: 'Claim', claimed: 'Claimed', cardReward: 'Card reward', talentReward: 'Talent',
            enchantmentBooks: 'Enchantment Books', enchantmentBookReward: 'Enchantment Book',
            enchantmentBookCopy: 'Up to 3. Discard anywhere; use during your combat turn.',
            useBook: 'Use', discardBook: 'Discard', replaceBook: 'Replace', bookSlotsFull: 'Choose a book to replace.',
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
            journeyCompleteCopy: 'You crossed every stage of the journey.', journeyFailed: 'Journey ended',
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
            previousCard: 'Previous card', nextCard: 'Next card', cardPosition: (current, total) => `${current}/${total}`,
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
            saveManager: '存读档', saveCopy: '服务器完成当前操作后即可保存或读取，最多保留最近3份。',
            saveCurrent: '保存当前进度', loadSave: '读取', noSaves: '暂无手动存档',
            deleteSave: '删除', deleteSaveTitle: '删除此存档？', deleteSaveCopy: '该手动存档将被移除。', saveDeleted: '存档已删除',
            saveCurrentSlot: '当前存档', savePreviousSlot: (value) => `前 ${value} 次存档`,
            saveSucceeded: '旅程进度已保存', loadSucceeded: '旅程进度已读取',
            loadSaveTitle: '读取此存档？', loadSaveCopy: '当前旅程状态将被所选存档覆盖。',
            saveOnlyOnMap: '请等待当前故事操作完成后再存读档',
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
            codexCards: '卡牌', codexEnemies: '生物', codexTalents: '天赋', codexBooks: '附魔书', codexTerms: '术语',
            codexSearch: '搜索已发现内容', codexRarity: '稀有度', codexType: '类型',
            codexAll: '全选', codexClear: '清空', codexResults: (count) => `${count} 项`,
            codexDiscovered: (found, total) => `已发现 ${found}/${total}`,
            codexEmpty: '没有符合条件的已发现内容', codexUnknownTalent: '未命名赐福',
            codexRelics: '天赋', codexBlessings: '赐福', codexStatuses: '状态',
            codexTags: '标签', codexTraits: '生物特殊效果', codexResources: '资源',
            codexHealth: '生命', codexObservedIntents: (count) => `已观察 ${count} 个意图`,
            codexBack: '返回上一个图鉴条目', codexRelated: '相关图鉴', codexViewRelated: '在图鉴中查看',
            codexNew: '发现了新的图鉴内容', codexNewCount: (count) => `发现了 ${count} 项新的图鉴内容`,
            battleWon: '战斗胜利', chooseCard: '选择一张牌',
            skip: '跳过卡牌', rewards: '战斗奖励', rewardCopy: '逐项领取奖励后继续前进。',
            claim: '领取', claimed: '已领取', cardReward: '卡牌奖励', talentReward: '天赋',
            enchantmentBooks: '附魔书', enchantmentBookReward: '附魔书',
            enchantmentBookCopy: '最多持有3本；可随时丢弃，战斗中的玩家回合可使用。',
            useBook: '使用', discardBook: '丢弃', replaceBook: '替换', bookSlotsFull: '附魔书槽已满，请选择要替换的一本。',
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
            journeyComplete: '旅程完成', journeyCompleteCopy: '你已经穿过了旅程的全部阶段。', journeyFailed: '旅程结束',
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
            previousCard: '上一张卡牌', nextCard: '下一张卡牌', cardPosition: (current, total) => `第${current}/${total}张`,
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
            saveManager: 'Sauvegarder / Charger', saveCopy: 'Disponible une fois l’action courante validée par le serveur. Les 3 sauvegardes les plus récentes sont conservées.',
            saveCurrent: 'Sauvegarder', loadSave: 'Charger', noSaves: 'Aucune sauvegarde manuelle',
            deleteSave: 'Supprimer', deleteSaveTitle: 'Supprimer cette sauvegarde ?', deleteSaveCopy: 'Cette sauvegarde manuelle sera retirée.', saveDeleted: 'Sauvegarde supprimée',
            saveCurrentSlot: 'Actuelle', savePreviousSlot: (value) => `Précédente ${value}`,
            saveSucceeded: 'Progression sauvegardée', loadSucceeded: 'Progression chargée',
            loadSaveTitle: 'Charger cette sauvegarde ?', loadSaveCopy: 'L’état actuel du voyage sera remplacé.',
            saveOnlyOnMap: 'Attendez la fin de l’action courante avant de sauvegarder ou charger',
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
            codexCards: 'Cartes', codexEnemies: 'Ennemis', codexTalents: 'Talents', codexBooks: 'Livres enchantés', codexTerms: 'Termes',
            codexSearch: 'Rechercher le contenu découvert', codexRarity: 'Rareté', codexType: 'Type',
            codexAll: 'Tout', codexClear: 'Effacer', codexResults: (count) => `${count} résultat(s)`,
            codexDiscovered: (found, total) => `Découvert ${found}/${total}`,
            codexEmpty: 'Aucune découverte correspondante', codexUnknownTalent: 'Bénédiction sans nom',
            codexRelics: 'Talents', codexBlessings: 'Bénédictions', codexStatuses: 'États',
            codexTags: 'Étiquettes', codexTraits: 'Effets ennemis', codexResources: 'Ressources',
            codexHealth: 'Vie', codexObservedIntents: (count) => `${count} intention(s) observée(s)`,
            codexBack: 'Revenir à l’entrée précédente', codexRelated: 'Découvertes liées', codexViewRelated: 'Voir dans le compendium',
            codexNew: 'Nouvelle entrée du compendium', codexNewCount: (count) => `${count} nouvelles entrées du compendium`,
            chooseCard: 'Choisissez une carte', skip: 'Passer la carte', room: 'Salle', newJourney: 'Nouveau voyage',
            rewards: 'Récompenses du combat', rewardCopy: 'Récupérez chaque récompense avant de continuer.',
            claim: 'Récupérer', claimed: 'Récupéré', cardReward: 'Carte', talentReward: 'Talent',
            enchantmentBooks: 'Livres enchantés', enchantmentBookReward: 'Livre enchanté',
            enchantmentBookCopy: 'Maximum 3. Jetables partout, utilisables pendant votre tour de combat.',
            useBook: 'Utiliser', discardBook: 'Jeter', replaceBook: 'Remplacer', bookSlotsFull: 'Choisissez un livre à remplacer.',
            directLeave: 'Partir sans rien prendre de plus', claimChestGold: 'Prendre l’or', claimChestTalent: 'Prendre le talent',
            continueJourney: 'Continuer', goldReward: (value) => `${value} G`,
            summon: 'Invocation', allies: 'Toutes les créatures', playerSide: 'Camp joueur', self: 'Soi', addCard: 'Ajouter une carte', consume: 'Absorber',
            developerMode: 'Mode développeur', devJump: 'Changer de niveau', devFloor: 'Étage', devRoom: 'Salle',
            devValues: 'Modifier les valeurs', devApply: 'Appliquer', devJumpButton: 'Aller',
            devValuesUpdated: 'Valeurs mises à jour', devJumped: 'Niveau chargé',
            cardTerms: 'Termes de carte', statusTerms: 'Terme d’état', actionTerms: 'Terme d’action', traitTerms: 'Terme d’effet', talentTerms: 'Détails du talent', noCardTerms: 'Aucun terme supplémentaire',
            previousCard: 'Carte précédente', nextCard: 'Carte suivante', cardPosition: (current, total) => `${current}/${total}`,
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
            saveManager: 'セーブ / ロード', saveCopy: '現在の操作がサーバーで完了すると利用できます。最新3件を保存します。',
            saveCurrent: '現在の進行を保存', loadSave: 'ロード', noSaves: '手動セーブはありません',
            deleteSave: '削除', deleteSaveTitle: 'このセーブを削除しますか？', deleteSaveCopy: 'この手動セーブは削除されます。', saveDeleted: 'セーブを削除しました',
            saveCurrentSlot: '最新', savePreviousSlot: (value) => `${value}つ前`,
            saveSucceeded: '進行を保存しました', loadSucceeded: '進行を読み込みました',
            loadSaveTitle: 'このセーブを読み込みますか？', loadSaveCopy: '現在の旅の状態は上書きされます。',
            saveOnlyOnMap: '現在の操作が完了してからセーブまたはロードしてください',
            easyRelicTitle: 'イージー天賦を選択', easyRelicCopy: '3つから1つ選び、その後に初期祝福を選択します。',
            blessingChooseCard: 'デッキのカードを選択', blessingBack: '祝福選択に戻る',
            transform: '変化', blessingRewardCopy: '各カード報酬から1枚選びます。',
            blessingCardReward: (index, total) => `カード報酬 ${index}/${total}`,
            intent: '意図', endTurn: 'ターン終了', drawPile: '山札', discardPile: '捨て札', exilePile: '追放',
            talentOverview: '天賦一覧', viewTalentOverview: '天賦一覧を見る',
            talentTotal: (count) => `天賦 ${count}個`, noTalents: '天賦を獲得していません',
            runDeck: '全デッキ', viewRunDeck: '全デッキを見る',
            codexTitle: '物語図鑑', viewCodex: '物語図鑑を見る',
            codexCards: 'カード', codexEnemies: '敵', codexTalents: '天賦', codexBooks: 'エンチャント本', codexTerms: '用語',
            codexSearch: '発見済みを検索', codexRarity: 'レア度', codexType: 'タイプ',
            codexAll: 'すべて', codexClear: '解除', codexResults: (count) => `${count}件`,
            codexDiscovered: (found, total) => `発見 ${found}/${total}`,
            codexEmpty: '一致する発見はありません', codexUnknownTalent: '名前のない祝福',
            codexRelics: '天賦', codexBlessings: '祝福', codexStatuses: '状態',
            codexTags: 'タグ', codexTraits: '敵の特殊効果', codexResources: 'リソース',
            codexHealth: '生命', codexObservedIntents: (count) => `確認済み意図 ${count}個`,
            codexBack: '前の図鑑項目に戻る', codexRelated: '関連する発見', codexViewRelated: '図鑑で見る',
            codexNew: '図鑑に新しい項目を発見', codexNewCount: (count) => `図鑑に${count}件を新発見`,
            battleWon: '戦闘勝利', chooseCard: 'カードを選択', skip: 'カードをスキップ', room: '部屋',
            rewards: '戦闘報酬', rewardCopy: 'すべての報酬を受け取ってから先へ進みます。',
            claim: '受け取る', claimed: '受取済み', cardReward: 'カード報酬', talentReward: '天賦',
            enchantmentBooks: 'エンチャント本', enchantmentBookReward: 'エンチャント本',
            enchantmentBookCopy: '最大3冊。いつでも破棄でき、戦闘中の自分のターンに使用できます。',
            useBook: '使用', discardBook: '破棄', replaceBook: '交換', bookSlotsFull: '交換する本を選んでください。',
            directLeave: '残りを受け取らず退出', claimChestGold: 'ゴールドを受け取る', claimChestTalent: '天賦を受け取る',
            continueJourney: '進む', goldReward: (value) => `${value} G`,
            summon: '召喚', allies: '全生物', playerSide: 'プレイヤー側', self: '自身', addCard: 'カード追加', consume: '吸収',
            developerMode: '開発者モード', devJump: 'ステージ移動', devFloor: '階', devRoom: '部屋',
            devValues: '数値設定', devApply: '適用', devJumpButton: '移動',
            devValuesUpdated: '数値を更新しました', devJumped: 'ステージを読み込みました',
            cardTerms: 'カード用語', statusTerms: '状態用語', actionTerms: '行動用語', traitTerms: '特殊効果用語', talentTerms: '天賦の説明', noCardTerms: '追加用語なし',
            previousCard: '前のカード', nextCard: '次のカード', cardPosition: (current, total) => `${current}/${total}`,
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
            'story-hud-map-label': t.viewMap,
            'story-hud-deck-label': t.runDeck,
            'story-hud-books-label': `${t.enchantmentBooks} 0/3`,
            'story-hud-save-label': t.saveManager,
            'story-hud-settings-label': ({ zh: '设置', en: 'Settings', fr: 'Réglages', ja: '設定' }[lang] || '设置'),
            'story-hud-surrender-label': t.surrender,
            'story-settings-cancel': t.cancel,
            'story-settings-confirm': t.confirm,
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
            'story-codex-back': t.codexBack,
            'story-codex-tab-cards': t.codexCards,
            'story-codex-tab-enemies': t.codexEnemies,
            'story-codex-tab-talents': t.codexTalents,
            'story-codex-tab-enchantment-books': t.codexBooks,
            'story-codex-tab-terms': t.codexTerms,
            'story-enchantment-books-title': t.enchantmentBooks,
            'story-enchantment-books-copy': t.enchantmentBookCopy,
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
        updateStorySettingsControls();
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

    function storyCoopDialogOpen() {
        return Boolean(window.__STORY_COOP_ACCESS__ && $('story-coop-preview-dialog')?.open);
    }

    function storyCoopSetStatus(message, tone = '') {
        const status = $('story-coop-lobby-status');
        if (!status) return;
        status.textContent = String(message || '');
        if (tone) status.dataset.tone = tone;
        else delete status.dataset.tone;
    }

    function storyCoopErrorMessage(error) {
        return String(
            error?.payload?.error
            || error?.message
            || '协作队伍请求失败，请稍后重试。',
        );
    }

    function storyCoopHasBundle(payload) {
        return Boolean(
            payload
            && typeof payload === 'object'
            && Object.prototype.hasOwnProperty.call(payload, 'party')
        );
    }

    function applyStoryCoopPartyPayload(payload) {
        if (!storyCoopHasBundle(payload)) return false;
        const previousPartyId = String(storyCoopPartyBundle.party?.id || '');
        const nextParty = payload.party && typeof payload.party === 'object'
            ? payload.party
            : null;
        const nextPartyId = String(nextParty?.id || '');
        if (previousPartyId !== nextPartyId) storyCoopInviteCode = '';
        storyCoopPartyBundle = {
            party: nextParty,
            viewer: payload.viewer && typeof payload.viewer === 'object' ? payload.viewer : null,
            run: payload.run && typeof payload.run === 'object' ? payload.run : null,
        };
        storyCoopPartyLoaded = true;
        const revealedCode = String(payload.invite_code || '').trim();
        if (revealedCode) storyCoopInviteCode = revealedCode;
        if (!nextParty || String(nextParty.status || '') !== 'forming') storyCoopInviteCode = '';
        renderStoryCoopParty();
        return true;
    }

    function renderStoryCoopMembers(party, viewer) {
        const list = $('story-coop-members');
        if (!list) return;
        const members = Array.isArray(party?.members) ? party.members : [];
        const maxPlayers = Math.min(4, Math.max(2, Number(party?.max_players) || 2));
        const viewerSeat = Number(viewer?.seat);
        const signature = JSON.stringify({
            maxPlayers,
            viewerSeat: Number.isFinite(viewerSeat) ? viewerSeat : null,
            members: members.map((member) => ({
                seat: member?.seat,
                username: member?.username,
                display_name: member?.display_name,
                party_role: member?.party_role,
            })),
        });
        if (storyCoopMemberSignature === signature) return;
        storyCoopMemberSignature = signature;
        const fragment = document.createDocumentFragment();

        for (let seat = 0; seat < maxPlayers; seat += 1) {
            const member = members.find((item) => Number(item?.seat) === seat);
            const row = document.createElement('li');
            row.className = `story-coop-member${member ? '' : ' is-empty'}`;

            const seatLabel = document.createElement('span');
            seatLabel.className = 'story-coop-seat';
            seatLabel.textContent = `席位 ${seat + 1}`;
            row.appendChild(seatLabel);

            const identity = document.createElement('span');
            identity.className = 'story-coop-member-identity';
            const name = document.createElement('strong');
            if (!member) {
                name.textContent = '等待成员加入';
                identity.appendChild(name);
                row.appendChild(identity);
                fragment.appendChild(row);
                continue;
            }

            const displayName = String(member.display_name || member.username || `玩家 ${seat + 1}`);
            const username = String(member.username || '');
            name.textContent = displayName;
            identity.appendChild(name);
            if (username && username !== displayName) {
                const account = document.createElement('small');
                account.textContent = `@${username}`;
                identity.appendChild(account);
            }
            row.appendChild(identity);

            const badges = document.createElement('span');
            badges.className = 'story-coop-member-badges';
            if (Number.isFinite(viewerSeat) && viewerSeat === seat) {
                const self = document.createElement('span');
                self.className = 'story-coop-member-badge';
                self.textContent = '你';
                badges.appendChild(self);
            }
            if (String(member.party_role || '') === 'leader') {
                const leader = document.createElement('span');
                leader.className = 'story-coop-member-badge is-leader';
                leader.textContent = '队长';
                badges.appendChild(leader);
            }
            row.appendChild(badges);
            fragment.appendChild(row);
        }
        list.replaceChildren(fragment);
    }

    function renderStoryCoopCharacterSelect() {
        const select = $('story-coop-character-select');
        if (!select) return;
        const characters = storyContent?.characters || {};
        const playable = Object.entries(characters).filter(([, definition]) => (
            String(definition?.implementation_status || '') === 'playable'
        ));
        const isUnlocked = (characterId) => characterId === 'common_flower'
            || Boolean(storyProgress?.characters?.[characterId]?.unlocked);
        if (!playable.some(([characterId]) => (
            characterId === selectedStoryCoopCharacterId && isUnlocked(characterId)
        ))) {
            selectedStoryCoopCharacterId = playable.find(
                ([characterId]) => isUnlocked(characterId),
            )?.[0] || 'common_flower';
        }
        const fragment = document.createDocumentFragment();
        playable.forEach(([characterId, definition]) => {
            const option = document.createElement('option');
            option.value = characterId;
            option.disabled = !isUnlocked(characterId);
            option.textContent = `${localize(definition?.name) || characterId}${
                option.disabled ? '（尚未解锁）' : ''
            }`;
            fragment.appendChild(option);
        });
        select.replaceChildren(fragment);
        select.value = selectedStoryCoopCharacterId;
        const selected = characters[selectedStoryCoopCharacterId];
        setText(
            'story-coop-character-help',
            `${localize(selected?.name) || selectedStoryCoopCharacterId}；服务器会要求两名成员都已解锁该角色，并只开放共同解锁的难度。`,
        );
    }

    function updateStoryCoopControls() {
        const party = storyCoopPartyBundle.party;
        const viewer = storyCoopPartyBundle.viewer;
        const run = storyCoopPartyBundle.run;
        const inviteInput = $('story-coop-invite-input');
        const isLeader = String(viewer?.party_role || '') === 'leader';
        const canStart = Boolean(
            party
            && String(party.status || '') === 'forming'
            && isLeader
            && viewer?.can_start
        );
        const disabled = storyCoopMutationInFlight || storyCoopConfirmationInFlight;
        const create = $('story-coop-create');
        const join = $('story-coop-join');
        const rotate = $('story-coop-rotate-invite');
        const start = $('story-coop-start');
        const characterSelect = $('story-coop-character-select');
        const leave = $('story-coop-leave');
        const abandon = $('story-coop-abandon');
        const enterCombat = $('story-coop-enter-combat');
        const copy = $('story-coop-copy-invite');
        if (create) create.disabled = disabled;
        if (inviteInput) inviteInput.disabled = disabled;
        if (join) join.disabled = disabled || !String(inviteInput?.value || '').trim();
        if (rotate) rotate.disabled = disabled;
        if (start) {
            start.disabled = disabled || !canStart;
            start.textContent = canStart ? '开始协作旅程' : '等待成员到齐';
        }
        if (characterSelect) characterSelect.disabled = disabled || !canStart;
        if (leave) leave.disabled = disabled;
        if (abandon) abandon.disabled = disabled;
        if (enterCombat) {
            enterCombat.disabled = disabled || !run || String(run.status || '') !== 'active';
        }
        if (copy) copy.disabled = disabled || !storyCoopInviteCode;
        const form = $('story-coop-lobby-form');
        if (form) form.setAttribute('aria-busy', disabled ? 'true' : 'false');
    }

    function renderStoryCoopParty() {
        const party = storyCoopPartyBundle.party;
        const viewer = storyCoopPartyBundle.viewer;
        const run = storyCoopPartyBundle.run;
        const status = String(party?.status || '');
        const noParty = $('story-coop-no-party');
        const forming = $('story-coop-forming');
        const active = $('story-coop-active');
        noParty?.classList.toggle('hidden', !storyCoopPartyLoaded || Boolean(party));
        forming?.classList.toggle('hidden', status !== 'forming');
        active?.classList.toggle('hidden', status !== 'active');

        if (status === 'forming') {
            const memberCount = Array.isArray(party?.members) ? party.members.length : 0;
            setText('story-coop-party-revision', `${memberCount} / ${Number(party?.max_players) || 2} 人`);
            renderStoryCoopMembers(party, viewer);
            renderStoryCoopCharacterSelect();
            const isLeader = String(viewer?.party_role || '') === 'leader';
            $('story-coop-rotate-invite')?.classList.toggle('hidden', !isLeader);
            $('story-coop-start')?.classList.toggle('hidden', !isLeader);
            const reveal = $('story-coop-invite-reveal');
            reveal?.classList.toggle('hidden', !storyCoopInviteCode);
            setText('story-coop-invite-code', storyCoopInviteCode);
        } else {
            $('story-coop-invite-reveal')?.classList.add('hidden');
            setText('story-coop-invite-code', '');
        }

        if (status === 'active') {
            setText('story-coop-active-party-revision', '双人队伍 · 进行中');
            setText('story-coop-run-id', storyCoopProgressLabel(run?.snapshot));
            setText('story-coop-run-revision', storyCoopSnapshotDifficultyLabel(run?.snapshot));
            setText('story-coop-run-status', storyCoopPhaseLabel(run?.snapshot));
        }
        updateStoryCoopControls();
    }

    function stopStoryCoopPolling() {
        clearTimeout(storyCoopPartyPollTimer);
        storyCoopPartyPollTimer = 0;
    }

    function scheduleStoryCoopPolling() {
        stopStoryCoopPolling();
        if (!storyCoopDialogOpen() || storyCoopMutationInFlight) return;
        storyCoopPartyPollTimer = setTimeout(() => {
            storyCoopPartyPollTimer = 0;
            loadStoryCoopParty({ silent: true }).catch(() => {});
        }, STORY_COOP_PARTY_POLL_MS);
    }

    function loadStoryCoopParty({ silent = false } = {}) {
        if (!storyCoopDialogOpen() || storyCoopMutationInFlight) return Promise.resolve(null);
        const requestedEpoch = storyCoopLobbyEpoch;
        if (storyCoopPartyLoadPromise) {
            if (storyCoopPartyLoadEpoch === requestedEpoch) return storyCoopPartyLoadPromise;
        }
        stopStoryCoopPolling();
        let loadPromise;
        loadPromise = (async () => {
            try {
                const payload = await requestJson('/api/story/coop/party');
                if (!storyCoopDialogOpen() || storyCoopLobbyEpoch !== requestedEpoch) return payload;
                applyStoryCoopPartyPayload(payload);
                if (!silent) storyCoopSetStatus('队伍状态已同步。', 'success');
                return payload;
            } catch (error) {
                if (storyCoopDialogOpen() && storyCoopLobbyEpoch === requestedEpoch) {
                    storyCoopSetStatus(
                        silent
                            ? `${storyCoopErrorMessage(error)}；大厅会继续重试。`
                            : storyCoopErrorMessage(error),
                        'error',
                    );
                }
                throw error;
            } finally {
                if (storyCoopPartyLoadPromise === loadPromise) storyCoopPartyLoadPromise = null;
                if (storyCoopLobbyEpoch === requestedEpoch) scheduleStoryCoopPolling();
            }
        })();
        storyCoopPartyLoadEpoch = requestedEpoch;
        storyCoopPartyLoadPromise = loadPromise;
        return loadPromise;
    }

    async function loadStoryCoopBootstrap() {
        if (!storyCoopDialogOpen() || storyCoopBootstrapLoaded) return;
        const requestedEpoch = storyCoopLobbyEpoch;
        try {
            const result = await requestJson('/api/story/coop/bootstrap');
            if (!storyCoopDialogOpen() || storyCoopLobbyEpoch !== requestedEpoch) return;
            storyCoopBootstrapLoaded = true;
            setText('story-coop-schema-value', '路线 / 事件');
            setText('story-coop-mvp-value', `${Number(result.mvp_player_count) || 2} 人`);
            setText('story-coop-max-value', '奖励 / 休息 / 宝箱 / 商店');
            setText(
                'story-coop-preview-copy',
                result.message || 'Staff / Admin 双人协作队伍实验已就绪。',
            );
        } catch (error) {
            if (!storyCoopDialogOpen() || storyCoopLobbyEpoch !== requestedEpoch) return;
            setText(
                'story-coop-preview-copy',
                `${storyCoopErrorMessage(error)}（队伍大厅仍可单独重试。）`,
            );
        }
    }

    async function performStoryCoopMutation(url, bodyFactory, pendingMessage, successMessage) {
        if (!storyCoopDialogOpen() || storyCoopMutationInFlight) return null;
        const mutationEpoch = storyCoopLobbyEpoch;
        storyCoopMutationInFlight = true;
        stopStoryCoopPolling();
        updateStoryCoopControls();
        storyCoopSetStatus(pendingMessage, 'busy');
        try {
            if (storyCoopPartyLoadPromise) {
                try {
                    await storyCoopPartyLoadPromise;
                } catch (_) {
                    // A mutation may still succeed even if the preceding poll failed.
                }
            }
            if (!storyCoopDialogOpen() || storyCoopLobbyEpoch !== mutationEpoch) return null;
            const body = typeof bodyFactory === 'function' ? bodyFactory() : (bodyFactory || {});
            const payload = await requestJson(url, {
                method: 'POST',
                body: JSON.stringify(body),
            });
            if (storyCoopDialogOpen() && storyCoopLobbyEpoch === mutationEpoch) {
                applyStoryCoopPartyPayload(payload);
                const message = typeof successMessage === 'function'
                    ? successMessage(payload)
                    : successMessage;
                storyCoopSetStatus(message, 'success');
            }
            return payload;
        } catch (error) {
            if (
                storyCoopDialogOpen()
                && storyCoopLobbyEpoch === mutationEpoch
                && Number(error?.status) === 409
                && storyCoopHasBundle(error?.payload)
            ) {
                applyStoryCoopPartyPayload(error.payload);
            }
            if (storyCoopDialogOpen() && storyCoopLobbyEpoch === mutationEpoch) {
                storyCoopSetStatus(storyCoopErrorMessage(error), 'error');
            }
            return null;
        } finally {
            storyCoopMutationInFlight = false;
            if (storyCoopDialogOpen() && storyCoopLobbyEpoch === mutationEpoch) {
                renderStoryCoopParty();
                scheduleStoryCoopPolling();
            } else if (storyCoopDialogOpen()) {
                loadStoryCoopParty().catch(() => {});
            }
        }
    }

    async function confirmStoryCoopAction(title, message) {
        if (storyCoopConfirmationInFlight || storyCoopMutationInFlight) return false;
        const confirmationEpoch = storyCoopLobbyEpoch;
        const confirmationPartyId = String(storyCoopPartyBundle.party?.id || '');
        const confirmationRevision = Number(storyCoopPartyBundle.party?.revision || 0);
        storyCoopConfirmationInFlight = true;
        updateStoryCoopControls();
        try {
            const confirmHandler = window.GTN_SHORTCUT_HOST?.confirm;
            let accepted = false;
            if (typeof confirmHandler === 'function') {
                accepted = Boolean(await confirmHandler(title, message));
            } else {
                accepted = window.confirm([title, message].filter(Boolean).join('\n\n'));
            }
            return Boolean(
                accepted
                && storyCoopDialogOpen()
                && storyCoopLobbyEpoch === confirmationEpoch
                && String(storyCoopPartyBundle.party?.id || '') === confirmationPartyId
                && Number(storyCoopPartyBundle.party?.revision || 0) === confirmationRevision
            );
        } finally {
            storyCoopConfirmationInFlight = false;
            updateStoryCoopControls();
        }
    }

    function storyCoopPartyMutationTarget() {
        const party = storyCoopPartyBundle.party;
        return {
            party_id: String(party?.id || ''),
            party_revision: Number(party?.revision),
        };
    }

    async function createStoryCoopParty() {
        await performStoryCoopMutation(
            '/api/story/coop/party',
            {},
            '正在创建双人队伍...',
            (payload) => payload?.invite_code
                ? '队伍已创建。请立即复制本次显示的邀请码。'
                : '已恢复你现有的队伍；邀请码不会重复显示，丢失时请由队长轮换。',
        );
    }

    async function joinStoryCoopParty() {
        const input = $('story-coop-invite-input');
        const inviteCode = String(input?.value || '').trim();
        if (!inviteCode) {
            storyCoopSetStatus('请输入邀请码。', 'error');
            input?.focus();
            return;
        }
        const result = await performStoryCoopMutation(
            '/api/story/coop/party/join',
            { invite_code: inviteCode },
            '正在加入队伍...',
            '已加入协作队伍。',
        );
        if (result && input) input.value = '';
        updateStoryCoopControls();
    }

    async function rotateStoryCoopInvite() {
        const target = storyCoopPartyMutationTarget();
        const accepted = await confirmStoryCoopAction(
            '轮换邀请码？',
            '旧邀请码会立即失效。新邀请码也只会在本次响应中显示一次。',
        );
        if (!accepted) return;
        await performStoryCoopMutation(
            '/api/story/coop/party/invite',
            target,
            '正在轮换邀请码...',
            '邀请码已轮换。请立即复制新邀请码。',
        );
    }

    async function startStoryCoopRun() {
        await performStoryCoopMutation(
            '/api/story/coop/party/start',
            () => ({
                party_id: storyCoopPartyBundle.party?.id,
                party_revision: storyCoopPartyBundle.party?.revision,
                character_id: selectedStoryCoopCharacterId,
            }),
            '正在建立协作旅程...',
            '协作旅程已建立。',
        );
    }

    async function leaveStoryCoopParty() {
        const target = storyCoopPartyMutationTarget();
        const accepted = await confirmStoryCoopAction(
            '解散当前队伍？',
            '任一成员执行后，当前大厅会对全队关闭。',
        );
        if (!accepted) return;
        await performStoryCoopMutation(
            '/api/story/coop/party/leave',
            target,
            '正在解散队伍...',
            '队伍已解散。',
        );
    }

    async function abandonStoryCoopRun() {
        const target = storyCoopPartyMutationTarget();
        const accepted = await confirmStoryCoopAction(
            '放弃协作旅程并释放全队？',
            '这会立即结束协作旅程，让所有成员离开队伍；现有协作存档不可恢复。',
        );
        if (!accepted) return;
        await performStoryCoopMutation(
            '/api/story/coop/party/abandon',
            target,
            '正在放弃协作旅程...',
            '协作旅程已放弃，全队已释放。',
        );
    }

    async function copyStoryCoopInvite() {
        if (!storyCoopInviteCode || storyCoopMutationInFlight) return;
        try {
            if (navigator.clipboard?.writeText) {
                await navigator.clipboard.writeText(storyCoopInviteCode);
            } else {
                const helper = document.createElement('textarea');
                helper.value = storyCoopInviteCode;
                helper.setAttribute('readonly', '');
                helper.className = 'story-coop-copy-helper';
                document.body.appendChild(helper);
                let copied = false;
                try {
                    helper.select();
                    copied = document.execCommand('copy');
                } finally {
                    helper.remove();
                }
                if (!copied) throw new Error('COPY_FAILED');
            }
            storyCoopSetStatus('邀请码已复制。', 'success');
        } catch (_) {
            storyCoopSetStatus('复制失败，请手动选择邀请码复制。', 'error');
        }
    }

    function closeStoryCoopLobby() {
        storyCoopLobbyEpoch += 1;
        stopStoryCoopPolling();
        storyCoopInviteCode = '';
        storyCoopMemberSignature = '';
        storyCoopPartyBundle = { party: null, viewer: null, run: null };
        storyCoopPartyLoaded = false;
        const input = $('story-coop-invite-input');
        if (input) input.value = '';
        renderStoryCoopParty();
    }

    function openCooperativeStoryPreview() {
        if (!window.__STORY_COOP_ACCESS__) return;
        const dialog = $('story-coop-preview-dialog');
        if (!dialog) return;
        storyCoopLobbyEpoch += 1;
        stopStoryCoopPolling();
        storyCoopInviteCode = '';
        storyCoopMemberSignature = '';
        storyCoopPartyBundle = { party: null, viewer: null, run: null };
        storyCoopPartyLoaded = false;
        const selectedCharacter = storyContent?.characters?.[selectedStoryCharacterId];
        const selectedUnlocked = selectedStoryCharacterId === 'common_flower'
            || Boolean(storyProgress?.characters?.[selectedStoryCharacterId]?.unlocked);
        selectedStoryCoopCharacterId = (
            selectedCharacter?.implementation_status === 'playable' && selectedUnlocked
        ) ? selectedStoryCharacterId : 'common_flower';
        storyCoopSetStatus('正在读取队伍状态...', 'busy');
        renderStoryCoopParty();
        if (!dialog.open) dialog.showModal();
        loadStoryCoopBootstrap();
        loadStoryCoopParty().catch(() => {});
    }

    function renderStoryCharacterOptions() {
        const container = $('story-character-options');
        if (!container) return;
        container.replaceChildren();
        const characters = storyContent?.characters || {};
        if (!characters[selectedStoryCharacterId]) {
            selectedStoryCharacterId = Object.keys(characters)[0] || 'common_flower';
        }
        Object.entries(characters).forEach(([characterId, definition]) => {
            const status = String(definition?.implementation_status || 'planned');
            const playable = status === 'playable';
            const unlocked = characterId === 'common_flower'
                || Boolean(storyProgress?.characters?.[characterId]?.unlocked);
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'story-character-option';
            button.classList.toggle('is-selected', characterId === selectedStoryCharacterId);
            button.classList.toggle('is-planned', !playable);
            button.classList.toggle('is-locked', playable && !unlocked);
            button.dataset.characterId = characterId;
            button.setAttribute('role', 'listitem');
            const name = document.createElement('strong');
            name.textContent = localize(definition?.name) || characterId;
            const statusText = document.createElement('small');
            statusText.textContent = playable && unlocked
                ? (lang === 'zh' ? '可游玩' : 'Playable')
                : (playable
                    ? (lang === 'zh' ? '尚未解锁' : 'Locked')
                    : (lang === 'zh' ? '开发中' : 'In development'));
            button.append(name, statusText);
            button.addEventListener('click', () => {
                selectedStoryCharacterId = characterId;
                renderStoryCharacterOptions();
                if (!playable) {
                    const message = localize(definition?.unavailable_message)
                        || '这名角色还没准备好呢\n请期待开发组更新';
                    setText('story-character-not-ready', message);
                    $('story-character-not-ready')?.classList.remove('hidden');
                    showToast(message);
                    return;
                }
                if (!unlocked) {
                    const message = lang === 'zh'
                        ? '请先使用前一名角色以任意难度通关全部阶段'
                        : 'Complete all stages with the previous character on any difficulty.';
                    setText('story-character-not-ready', message);
                    $('story-character-not-ready')?.classList.remove('hidden');
                    showToast(message);
                    return;
                }
                $('story-character-not-ready')?.classList.add('hidden');
            });
            container.append(button);
        });
        const selected = characters[selectedStoryCharacterId];
        setText('story-character-detail-name', localize(selected?.name) || selectedStoryCharacterId);
        setText('story-character-detail-design', String(selected?.design || ''));
        setText(
            'story-character-unlock',
            localize(selected?.unlock?.description)
                || (lang === 'zh' ? '尚未公布' : 'Not announced'),
        );
        setText('story-character-unlock-label', lang === 'zh' ? '解锁条件' : 'Unlock');
        setText('story-character-deck-label', lang === 'zh' ? '初始牌组' : 'Starter deck');
        setText('story-character-talent-label', lang === 'zh' ? '初始天赋' : 'Starting talent');

        const renderDetailItems = (containerId, items, resolveLabel) => {
            const detailContainer = $(containerId);
            if (!detailContainer) return;
            detailContainer.replaceChildren();
            if (!items.length) {
                const empty = document.createElement('span');
                empty.className = 'story-character-detail-empty';
                empty.textContent = lang === 'zh' ? '尚未公布' : 'Not announced';
                detailContainer.append(empty);
                return;
            }
            items.forEach((item) => {
                const chip = document.createElement('span');
                chip.className = 'story-character-detail-item';
                chip.textContent = resolveLabel(item);
                detailContainer.append(chip);
            });
        };
        renderDetailItems(
            'story-character-deck',
            Array.isArray(selected?.starter_deck) ? selected.starter_deck : [],
            (item) => {
                const card = item?.character_card_id
                    ? storyContent?.character_cards?.[item.character_card_id]
                    : storyContent?.cards?.[item?.card_id];
                const name = localize(card?.name) || item?.character_card_id || item?.card_id || '?';
                return `${name} × ${Math.max(1, Number(item?.count) || 1)}`;
            },
        );
        renderDetailItems(
            'story-character-talents',
            Array.isArray(selected?.starter_relics) ? selected.starter_relics : [],
            (relicId) => {
                const relic = storyContent?.character_relics?.[relicId]
                    || storyContent?.relics?.[relicId];
                const name = localize(relic?.name) || relicId;
                const description = localize(relic?.description)
                    || String(relic?.effect_text || '');
                return description ? `${name}：${description}` : name;
            },
        );
        const start = $('story-start');
        const selectedUnlocked = selectedStoryCharacterId === 'common_flower'
            || Boolean(storyProgress?.characters?.[selectedStoryCharacterId]?.unlocked);
        if (start) {
            start.disabled = selected?.implementation_status !== 'playable'
                || !selectedUnlocked;
        }
    }

    function storyCoopCombatDialogOpen() {
        return Boolean(window.__STORY_COOP_ACCESS__ && $('story-coop-combat-dialog')?.open);
    }

    function storyCoopCombatSetStatus(message, tone = '') {
        const status = $('story-coop-combat-status');
        if (!status) return;
        status.textContent = String(message || '');
        if (tone) status.dataset.tone = tone;
        else delete status.dataset.tone;
    }

    function stopStoryCoopCombatPolling(session = storyCoopCombatSession) {
        if (!session) return;
        clearTimeout(session.pollTimer);
        session.pollTimer = 0;
    }

    function storyCoopCombatSnapshot(session = storyCoopCombatSession) {
        return session?.run?.snapshot || null;
    }

    function storyCoopCombatViewer(session = storyCoopCombatSession) {
        const snapshot = storyCoopCombatSnapshot(session);
        return (snapshot?.players || []).find(
            (player) => Number(player?.seat) === Number(snapshot?.viewer_seat),
        ) || null;
    }

    function storyCoopCombatMemberName(snapshot, seat) {
        const member = (snapshot?.party?.members || []).find(
            (item) => Number(item?.seat) === Number(seat),
        );
        return String(member?.display_name || member?.username || `席位 ${Number(seat) + 1}`);
    }

    function storyCoopDifficultyLabel(difficulty) {
        return ({
            easy: '简单',
            normal: '普通',
            hard: '困难',
            lunatic: '疯狂',
        })[String(difficulty || '').toLowerCase()] || '尚未选择';
    }

    function storyCoopSnapshotDifficultyLabel(snapshot) {
        return String(snapshot?.phase || '') === 'journey_setup'
            ? '尚未选择'
            : storyCoopDifficultyLabel(snapshot?.difficulty);
    }

    function storyCoopProgressLabel(snapshot) {
        if (!snapshot) return '正在建立旅程';
        const floor = Math.max(1, Number(snapshot.current_floor) || 1);
        const maximum = Math.max(floor, Number(snapshot.progression?.max_floor) || floor);
        if (String(snapshot.phase || '') === 'journey_setup') return '花园 · 准备中';
        const biome = ({ garden: '花园', jungle: '丛林', factory: '工厂' })[
            String(snapshot.biome || '')
        ] || '未知区域';
        const stage = Math.max(1, Number(snapshot.stage) || 1);
        return `第 ${stage} 阶段 · ${biome} · 第 ${floor} / ${maximum} 层`;
    }

    function storyCoopPhaseLabel(snapshot) {
        const phase = String(snapshot?.phase || '');
        const roomType = String(snapshot?.room?.type || '');
        if (phase === 'journey_setup') return '选择难度';
        if (phase === 'combat') return snapshot?.combat?.turn === 'enemies' ? '敌人行动' : '共同战斗';
        if (phase === 'reward') return '领取个人奖励';
        if (phase === 'map') return '全队路线投票';
        if (phase === 'stage_complete') return `第${Math.max(1, Number(snapshot?.stage) || 1)}阶段完成`;
        if (phase === 'complete') return '完整旅程完成';
        if (phase === 'game_over') return '旅程失败';
        if (phase === 'room') {
            return ({
                opening: '选择个人赐福',
                rest: '处理个人休息',
                chest: '领取个人宝箱',
                shop: '浏览个人商店',
                event: '全队事件表决',
            })[roomType] || '处理当前房间';
        }
        return '同步中';
    }

    function storyCoopWaitingNames(snapshot, seats, completedKey) {
        return (Array.isArray(seats) ? seats : [])
            .filter((item) => !Boolean(item?.[completedKey]))
            .map((item) => storyCoopCombatMemberName(snapshot, item?.seat));
    }

    function storyCoopWaitingMessage(snapshot, seats, completedKey, fallback = '队友') {
        const names = storyCoopWaitingNames(snapshot, seats, completedKey);
        return names.length ? names.join('、') : fallback;
    }

    function storyCoopCombatCanAct(session = storyCoopCombatSession) {
        const snapshot = storyCoopCombatSnapshot(session);
        const viewer = storyCoopCombatViewer(session);
        return Boolean(
            session
            && session.compatible !== false
            && !session.loadPromise
            && !session.actionPromise
            && String(session.run?.status || '') === 'active'
            && snapshot?.phase === 'combat'
            && snapshot?.combat?.turn === 'heroes'
            && !snapshot?.combat?.outcome
            && viewer
            && !viewer.down
            && !viewer.ready
        );
    }

    function storyCoopRunCanSubmit(session = storyCoopCombatSession) {
        return Boolean(
            session
            && session.compatible !== false
            && !session.loadPromise
            && !session.actionPromise
            && String(session.run?.status || '') === 'active'
            && storyCoopCombatSnapshot(session)
        );
    }

    function storyCoopSetupDifficultySet(session = storyCoopCombatSession) {
        const snapshot = storyCoopCombatSnapshot(session);
        const supported = new Set(['normal', 'hard', 'lunatic']);
        return new Set(
            (Array.isArray(snapshot?.room?.difficulties) ? snapshot.room.difficulties : [])
                .map((difficulty) => String(difficulty || '').trim().toLowerCase())
                .filter((difficulty) => supported.has(difficulty)),
        );
    }

    function storyCoopSetupViewerIsLeader(session = storyCoopCombatSession) {
        const snapshot = storyCoopCombatSnapshot(session);
        return Boolean(
            snapshot
            && Number(snapshot.viewer_seat) === Number(snapshot.party?.leader_seat)
        );
    }

    function storyCoopSetupCanChoose(session = storyCoopCombatSession) {
        const snapshot = storyCoopCombatSnapshot(session);
        return Boolean(
            storyCoopRunCanSubmit(session)
            && snapshot?.phase === 'journey_setup'
            && storyCoopSetupViewerIsLeader(session)
            && storyCoopSetupDifficultySet(session).size
        );
    }

    function storyCoopOpeningRoomState(session = storyCoopCombatSession) {
        const snapshot = storyCoopCombatSnapshot(session);
        const room = snapshot?.room;
        const roomState = snapshot?.room_state;
        const roomId = String(roomState?.room_id || '');
        if (
            snapshot?.phase !== 'room'
            || String(room?.type || '') !== 'opening'
            || String(roomState?.type || '') !== 'opening'
            || String(roomState?.stage || '') !== 'blessing'
            || !roomId
            || (room?.id && roomId !== String(room.id))
        ) return null;
        return roomState;
    }

    function storyCoopOpeningCanChoose(session = storyCoopCombatSession) {
        const roomState = storyCoopOpeningRoomState(session);
        return Boolean(
            storyCoopRunCanSubmit(session)
            && roomState?.status === 'pending'
        );
    }

    function storyCoopRewardCanChoose(session = storyCoopCombatSession) {
        const snapshot = storyCoopCombatSnapshot(session);
        return Boolean(
            storyCoopRunCanSubmit(session)
            && snapshot?.phase === 'reward'
            && snapshot?.reward?.status === 'pending'
        );
    }

    function storyCoopViewerBooks(session = storyCoopCombatSession) {
        const viewer = storyCoopCombatViewer(session);
        return Array.isArray(viewer?.enchantment_books) ? viewer.enchantment_books : [];
    }

    function storyCoopBookDefinition(book) {
        const bookId = String(book?.book_id || book || '');
        return storyContent?.enchantment_books?.[bookId] || {};
    }

    function chooseStoryCoopBookReplacement(session = storyCoopCombatSession) {
        const books = storyCoopViewerBooks(session);
        if (books.length < Number(storyContent?.rules?.enchantment_book_slots || 3)) return '';
        const labels = books.map((book, index) => {
            const definition = storyCoopBookDefinition(book);
            return `${index + 1}. ${localize(definition.name) || book.book_id}`;
        });
        const raw = window.prompt(`附魔书槽已满，请输入要替换的序号：\n${labels.join('\n')}`);
        if (raw == null) return null;
        const selected = books[Number.parseInt(raw, 10) - 1];
        return selected ? String(selected.instance_id || '') : null;
    }

    function chooseStoryCoopCards(cards, { minimum = 1, maximum = 1, label = '卡牌' } = {}) {
        const source = Array.isArray(cards) ? cards : [];
        const lines = source.map((card, index) => (
            `${index + 1}. ${String(card?.label || '') || storyCoopCombatCardLabel(card)}`
        ));
        const promptText = minimum === maximum
            ? `请选择${minimum}张${label}，输入序号（多张用逗号分隔）：`
            : `请选择${minimum}至${maximum}张${label}，输入序号（可留空）：`;
        const raw = window.prompt(`${promptText}\n${lines.join('\n')}`);
        if (raw == null) return null;
        const indexes = String(raw).trim()
            ? [...new Set(String(raw).split(/[,，\s]+/).map((item) => Number.parseInt(item, 10) - 1))]
            : [];
        const selected = indexes.map((index) => source[index]).filter(Boolean);
        if (selected.length !== indexes.length || selected.length < minimum || selected.length > maximum) {
            storyCoopCombatSetStatus('附魔书的卡牌选择无效，请重新操作。', 'error');
            return null;
        }
        return selected;
    }

    function useStoryCoopEnchantmentBook(book) {
        const session = storyCoopCombatSession;
        const snapshot = storyCoopCombatSnapshot(session);
        const viewer = storyCoopCombatViewer(session);
        if (!session || snapshot?.phase !== 'combat' || !storyCoopCombatCanAct(session)) return;
        const definition = storyCoopBookDefinition(book);
        const target = String(definition?.target || '');
        const payload = { book_instance_id: String(book?.instance_id || '') };
        if (target === 'book') {
            const candidates = storyCoopViewerBooks(session).filter(
                (item) => String(item?.instance_id || '') !== String(book?.instance_id || ''),
            );
            const selected = chooseStoryCoopCards(
                candidates.map((item) => ({
                    ...item,
                    def_id: '',
                    label: localize(storyCoopBookDefinition(item).name) || item.book_id,
                })),
                { label: '附魔书' },
            );
            if (!selected) return;
            const original = candidates.find(
                (item) => String(item?.instance_id || '') === String(selected[0]?.instance_id || ''),
            );
            if (!original) return;
            payload.target_book_instance_id = String(original.instance_id || '');
        } else if (target) {
            const hand = Array.isArray(viewer?.hand) ? viewer.hand : [];
            const eligible = hand.filter((card) => {
                const values = cardValues(card);
                const tags = new Set(values?.tags || []);
                if (target === 'attack_card') return values?.type === 'thorn';
                if (target === 'skill_card') return values?.type === 'bloom';
                if (target === 'exile_card') return tags.has('exile');
                if (target === 'cost_card') return Number(values?.cost_e || 0) + Number(values?.cost_m || 0) > 0;
                return true;
            });
            const minimum = target === 'three_cards' ? 3 : (target === 'any_cards' ? 0 : 1);
            const maximum = target === 'any_cards' ? eligible.length : minimum;
            const selected = chooseStoryCoopCards(eligible, { minimum, maximum });
            if (selected == null) return;
            payload.selected_card_ids = selected.map((card) => String(card.instance_id || ''));
        }
        storyCoopCombatAction('use_enchantment_book', payload);
    }

    function discardStoryCoopEnchantmentBook(book) {
        const session = storyCoopCombatSession;
        const snapshot = storyCoopCombatSnapshot(session);
        if (!session || !snapshot || !storyCoopRunCanSubmit(session)) return;
        const definition = storyCoopBookDefinition(book);
        if (!window.confirm(`确定丢弃“${localize(definition.name) || book.book_id}”吗？`)) return;
        storyCoopCombatAction(
            snapshot.phase === 'combat'
                ? 'discard_combat_enchantment_book'
                : 'discard_enchantment_book',
            { book_instance_id: String(book?.instance_id || '') },
        );
    }

    function storyCoopMapCanVote(session = storyCoopCombatSession) {
        const snapshot = storyCoopCombatSnapshot(session);
        const viewerVote = snapshot?.map_vote?.seats?.find(
            (item) => Number(item?.seat) === Number(snapshot?.viewer_seat),
        );
        return Boolean(
            storyCoopRunCanSubmit(session)
            && snapshot?.phase === 'map'
            && snapshot?.map_vote
            && !viewerVote?.submitted
        );
    }

    function storyCoopStageCanReady(session = storyCoopCombatSession) {
        const snapshot = storyCoopCombatSnapshot(session);
        return Boolean(
            storyCoopRunCanSubmit(session)
            && snapshot?.phase === 'stage_complete'
            && snapshot?.room_state?.type === 'stage_complete'
            && snapshot?.room_state?.status === 'pending'
            && snapshot?.room_state?.room_id
        );
    }

    function storyCoopRoomState(session = storyCoopCombatSession, expectedType = '') {
        const snapshot = storyCoopCombatSnapshot(session);
        const room = snapshot?.room;
        const roomState = snapshot?.room_state;
        const roomType = String(room?.type || '');
        if (
            snapshot?.phase !== 'room'
            || !['rest', 'chest', 'shop', 'event'].includes(roomType)
            || (expectedType && roomType !== expectedType)
            || String(roomState?.type || '') !== roomType
            || String(roomState?.room_id || '') !== String(room?.id || '')
        ) return null;
        return roomState;
    }

    function storyCoopRestRoomState(session = storyCoopCombatSession) {
        return storyCoopRoomState(session, 'rest');
    }

    function storyCoopChestRoomState(session = storyCoopCombatSession) {
        return storyCoopRoomState(session, 'chest');
    }

    function storyCoopShopRoomState(session = storyCoopCombatSession) {
        return storyCoopRoomState(session, 'shop');
    }

    function storyCoopEventRoomState(session = storyCoopCombatSession) {
        return storyCoopRoomState(session, 'event');
    }

    function storyCoopRoomOptionSet(roomState = storyCoopRoomState()) {
        return new Set(
            (Array.isArray(roomState?.options) ? roomState.options : [])
                .map((option) => String(option || '').toLowerCase()),
        );
    }

    function storyCoopRoomCanChoose(session = storyCoopCombatSession, expectedType = '') {
        const roomState = storyCoopRoomState(session, expectedType);
        return Boolean(
            storyCoopRunCanSubmit(session)
            && roomState
            && roomState.status === 'pending'
        );
    }

    function storyCoopRestCanChoose(session = storyCoopCombatSession) {
        return storyCoopRoomCanChoose(session, 'rest');
    }

    function storyCoopRestOptionSet(roomState = storyCoopRestRoomState()) {
        return storyCoopRoomOptionSet(roomState);
    }

    function storyCoopShopCanBuy(session = storyCoopCombatSession) {
        const roomState = storyCoopShopRoomState(session);
        const options = storyCoopRoomOptionSet(roomState);
        return Boolean(
            storyCoopRoomCanChoose(session, 'shop')
            && (
                options.has('buy_card')
                || options.has('buy_relic')
                || options.has('buy_enchantment_book')
            )
        );
    }

    function chooseStoryCoopRoomOption(session, expectedType, choice) {
        const roomState = storyCoopRoomState(session, expectedType);
        const normalizedChoice = String(choice || '').toLowerCase();
        if (
            !roomState
            || !storyCoopRoomCanChoose(session, expectedType)
            || !storyCoopRoomOptionSet(roomState).has(normalizedChoice)
        ) return null;
        return storyCoopCombatAction('room_choose', {
            room_id: String(roomState.room_id || ''),
            choice: normalizedChoice,
        });
    }

    function storyCoopRoomSeatStatus(roomType, resolved) {
        const labels = {
            opening: resolved ? '赐福已选择' : '选择赐福中',
            rest: resolved ? '休息完成' : '选择休息方式',
            chest: resolved ? '宝箱已处理' : '处理个人宝箱',
            shop: resolved ? '已离开商店' : '浏览个人商店',
            event: resolved ? '已提交事件选择' : '选择事件中',
            stage_complete: resolved ? '已确认继续' : '等待确认继续',
        };
        return labels[String(roomType || '')] || (resolved ? '已完成' : '处理中');
    }

    function storyCoopCombatCardLabel(card) {
        const values = cardValues(card);
        return `${storyCardUpgradePrefix(card)}${localize(values?.name) || card?.def_id || '?'}`;
    }

    function storyCoopCombatDiscardRequirement(card) {
        const effects = cardValues(card)?.effects || [];
        return effects.reduce((result, effect) => {
            if (String(effect?.type || '') !== 'active_discard') return result;
            const amount = Math.max(0, Number(effect?.amount || 0));
            return {
                minimum: result.minimum + (effect?.exact ? amount : 0),
                maximum: result.maximum + amount,
            };
        }, { minimum: 0, maximum: 0 });
    }

    function storyCoopCombatCardNeedsEnemy(card) {
        const values = cardValues(card);
        if ((values?.tags || []).includes('wide')) return false;
        return (values?.effects || []).some(
            (effect) => ['damage', 'electric_damage'].includes(String(effect?.type || '')),
        );
    }

    function storyCoopCombatActionId() {
        if (globalThis.crypto?.randomUUID) return `coop-${crypto.randomUUID()}`;
        return `coop-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }

    function cloneStoryCoopActionPayload(payload) {
        const value = payload && typeof payload === 'object' ? payload : {};
        if (typeof structuredClone === 'function') return structuredClone(value);
        return JSON.parse(JSON.stringify(value));
    }

    function storyCoopCombatApplyRun(session, run, compatible = true) {
        if (
            !session
            || session !== storyCoopCombatSession
            || !run
            || String(run.id || '') !== session.runId
        ) return false;
        const incomingRevision = Number(run.revision || 0);
        const currentRevision = Number(session.run?.revision || 0);
        if (currentRevision && incomingRevision < currentRevision) return false;
        const incomingPhase = String(run.snapshot?.phase || '');
        if (
            session.notice?.sticky
            && (
                incomingRevision > Number(session.notice.runRevision || 0)
                || incomingPhase !== String(session.notice.phase || '')
            )
        ) {
            session.notice = null;
        }
        session.run = run;
        session.compatible = compatible !== false;
        const living = (run.snapshot?.combat?.enemies || []).filter(
            (enemy) => Number(enemy?.health || 0) > 0,
        );
        if (!living.some((enemy) => String(enemy.id) === session.selectedEnemyId)) {
            session.selectedEnemyId = String(living[0]?.id || '');
        }
        const viewer = storyCoopCombatViewer(session);
        const handIds = new Set((viewer?.hand || []).map((card) => String(card?.instance_id || '')));
        if (!handIds.has(session.pendingCardId)) {
            session.pendingCardId = '';
            session.discardSelection.clear();
        } else {
            session.discardSelection = new Set(
                [...session.discardSelection].filter((id) => handIds.has(id) && id !== session.pendingCardId),
            );
        }
        const roomState = storyCoopRestRoomState(session);
        const restOptions = storyCoopRestOptionSet(roomState);
        const eligibleRestCardIds = new Set(
            (Array.isArray(roomState?.deck) ? roomState.deck : [])
                .filter((card) => !card?.upgraded && Number(card?.upgrade_level || 0) <= 0)
                .map((card) => String(card?.instance_id || '')),
        );
        if (
            roomState?.status !== 'pending'
            || !restOptions.has('upgrade')
            || !eligibleRestCardIds.has(session.selectedRestCardId)
        ) session.selectedRestCardId = '';
        renderStoryCoopCombat();
        return true;
    }

    function storyCoopCombatEventText(event, snapshot) {
        const seatName = (seat) => storyCoopCombatMemberName(snapshot, seat);
        const enemyName = (enemyId) => {
            const enemy = (snapshot?.combat?.enemies || []).find((item) => String(item?.id) === String(enemyId));
            return localize(storyContent?.enemies?.[enemy?.def_id]?.name) || enemy?.def_id || enemyId || '敌人';
        };
        switch (String(event?.type || '')) {
        case 'coop_opening_started':
            return '全队开始选择各自的开局赐福';
        case 'coop_opening_resolved':
            return `${seatName(event.actor_seat)}已完成个人开局赐福`;
        case 'coop_combat_started':
            return `第${Number(event.round) || 1}回合协作战斗开始`;
        case 'coop_card_played':
            return `${seatName(event.actor_seat)}打出${localize(storyContent?.cards?.[event.def_id]?.name) || event.def_id}`;
        case 'enemy_damage':
            return `${enemyName(event.enemy_id)}受到${Number(event.amount) || 0}点伤害`;
        case 'enemy_defeated':
            return `${enemyName(event.enemy_id)}被击败`;
        case 'coop_shield_gained':
            return `${seatName(event.actor_seat)}获得${Number(event.amount) || 0}层护盾`;
        case 'coop_shield_cleared':
            return `${seatName(event.actor_seat)}的${Number(event.amount) || 0}层护盾在回合开始时清除`;
        case 'coop_card_discarded':
            return `${seatName(event.actor_seat)}主动丢弃1张牌`;
        case 'coop_hand_discarded':
            return `${seatName(event.actor_seat)}将${Number(event.count) || 0}张剩余手牌置入弃牌堆`;
        case 'coop_discard_shuffled':
            return `${seatName(event.actor_seat)}将弃牌堆洗回抽牌堆`;
        case 'combat_seat_ready':
            return `${seatName(event.actor_seat)}已结束本回合`;
        case 'enemy_phase_started':
            return '所有存活成员均已准备，敌人开始行动';
        case 'enemy_action':
            return `${enemyName(event.enemy_id)}开始行动`;
        case 'enemy_idle':
            return `${enemyName(event.enemy_id)}本回合没有行动`;
        case 'enemy_target_locked':
            return `${enemyName(event.enemy_id)}锁定${seatName(event.target_seat)}`;
        case 'enemy_target_reassigned':
            return `${enemyName(event.enemy_id)}改为攻击${seatName(event.target_seat)}`;
        case 'enemy_shield_gained':
            return `${enemyName(event.enemy_id)}获得${Number(event.amount) || 0}层护盾`;
        case 'enemy_power_gained':
            return `${enemyName(event.enemy_id)}获得${Number(event.amount) || 0}层力量`;
        case 'enemy_self_damage':
            return `${enemyName(event.enemy_id)}受到${Number(event.amount) || 0}点自身伤害`;
        case 'player_damage':
            return `${seatName(event.target_seat)}受到${Number(event.amount) || 0}点伤害`;
        case 'player_down':
            return `${seatName(event.target_seat)}倒下了`;
        case 'coop_cards_drawn':
            return `${seatName(event.actor_seat)}抽取${Number(event.count) || 0}张牌`;
        case 'coop_elixir_gained':
            return `${seatName(event.actor_seat)}回复${Number(event.amount) || 0}E`;
        case 'coop_magic_gained':
            return `${seatName(event.actor_seat)}获得${Number(event.amount) || 0}M`;
        case 'coop_static_applied':
            return `${enemyName(event.enemy_id)}被施加${Number(event.amount) || 0}层静电`;
        case 'coop_static_triggered':
            return `${enemyName(event.enemy_id)}触发${Number(event.amount) || 0}层静电`;
        case 'coop_enemy_intent_advanced':
            return `${enemyName(event.enemy_id)}准备了新的行动`;
        case 'coop_seat_turn_started':
            return `${seatName(event.actor_seat)}已进入第${Number(event.round) || '?'}回合`;
        case 'hero_phase_started':
            return `第${Number(event.round) || '?'}回合英雄阶段开始`;
        case 'combat_victory':
            return '协作战斗胜利';
        case 'player_revived':
            return `${seatName(event.target_seat)}以${Number(event.amount) || 0}H复苏`;
        case 'coop_rewards_started':
            return `每位成员获得${Number(event.amount) || 0}金币并开始个人选卡`;
        case 'coop_reward_resolved':
            return `${seatName(event.actor_seat)}已完成个人奖励`;
        case 'coop_route_vote_started':
            return `第${Number(event.floor) || '?'}层路线投票开始`;
        case 'coop_route_vote_cast':
            return `${seatName(event.actor_seat)}已提交路线投票`;
        case 'coop_route_vote_resolved':
            return `队伍路线已确定，前往${storyCoopProgressLabel(snapshot)}`;
        case 'coop_room_started': {
            const labels = {
                rest: '协作休息处',
                chest: '个人补给箱',
                shop: '个人商店',
                event: '共享事件',
            };
            return `${labels[String(event.room_type || '')] || '协作房间'}已开启`;
        }
        case 'coop_player_healed':
            return `${seatName(event.actor_seat)}恢复${Number(event.amount) || 0}H`;
        case 'coop_card_upgraded':
            return `${seatName(event.actor_seat)}已升级1张个人卡牌`;
        case 'coop_chest_gold_claimed':
            return `${seatName(event.actor_seat)}已领取个人补给箱`;
        case 'coop_shop_purchase_completed':
            return `${seatName(event.actor_seat)}已在个人商店购买商品`;
        case 'coop_relic_gained':
            return `${seatName(event.actor_seat)}获得了个人遗物`;
        case 'coop_rest_gold_gained':
            return `${seatName(event.actor_seat)}在休息处获得了金币`;
        case 'coop_room_seat_resolved':
            return `${seatName(event.actor_seat)}已完成当前房间选择`;
        case 'coop_event_vote_cast':
            return `${seatName(event.actor_seat)}已提交事件选择`;
        case 'coop_event_consensus_required':
            return '事件选择不一致，本轮不结算并重新表决';
        case 'coop_event_resolved': {
            const eventDefinition = storyContent?.events?.[String(event.content_id || '')];
            const option = (eventDefinition?.options || []).find(
                (item) => String(item?.id || '') === String(event.choice || ''),
            );
            return `队伍事件结果：${localize(option?.label) || '已结算'}`;
        }
        case 'coop_stage_completed':
            return `协作第${Math.max(1, Number(event.stage) || 1)}阶段完成`;
        case 'coop_stage_ready':
            return `${seatName(event.actor_seat)}已确认阶段结算`;
        case 'coop_stage_started':
            return `协作第${Math.max(1, Number(event.stage) || 1)}阶段开始`;
        case 'coop_journey_completed':
            return '协作完整旅程完成';
        case 'coop_chapter_completed':
            return '协作试玩章节完成';
        case 'party_defeated':
            return '全队倒下，协作旅程结束';
        default:
            return String(event?.type || '战斗状态已更新');
        }
    }

    function storyCoopCombatSeatActor(seat) {
        return document.querySelector(
            `.story-coop-combat-player[data-seat="${Number(seat)}"]`,
        );
    }

    function storyCoopCombatMotionTarget(event, body) {
        const enemyId = String(
            event?.target_enemy_id
            || body?.payload?.target_enemy_id
            || '',
        );
        if (enemyId) {
            return document.querySelector(
                `.story-coop-combat-enemy[data-enemy-id="${CSS.escape(enemyId)}"]`,
            );
        }
        const seat = Number(event?.actor_seat);
        if (Number.isInteger(seat)) {
            return storyCoopCombatSeatActor(seat);
        }
        return $('story-coop-combat-board');
    }

    async function playStoryCoopActionPresentation(events, body, previousSnapshot) {
        if (!storyCoopCombatDialogOpen() || previousSnapshot?.phase !== 'combat') return;
        const sequence = Array.isArray(events) ? events : [];
        const viewerSeat = Number(previousSnapshot?.viewer_seat);
        const discardedIds = Array.isArray(body?.payload?.discard_card_instance_ids)
            ? [...body.payload.discard_card_instance_ids]
            : [];
        for (const event of sequence) {
            const eventType = String(event?.type || '');
            const actorSeat = Number(event?.actor_seat);
            if (eventType === 'coop_card_played') {
                const instanceId = actorSeat === viewerSeat
                    ? String(body?.payload?.card_instance_id || '')
                    : '';
                const source = instanceId
                    ? document.querySelector(
                        `.story-coop-combat-hand .story-card[data-instance-id="${CSS.escape(instanceId)}"]`,
                    )
                    : document.querySelector(
                        `.story-coop-combat-player[data-seat="${actorSeat}"]`,
                    );
                await animateStoryCardFlight(
                    source,
                    storyCoopCombatMotionTarget(event, body),
                    'play',
                    0,
                    Boolean(instanceId),
                );
            } else if (eventType === 'coop_card_discarded' && actorSeat === viewerSeat) {
                const instanceId = String(discardedIds.shift() || '');
                const source = instanceId
                    ? document.querySelector(
                        `.story-coop-combat-hand .story-card[data-instance-id="${CSS.escape(instanceId)}"]`,
                    )
                    : null;
                await animateStoryCardFlight(
                    source,
                    storyCoopCombatSeatActor(actorSeat),
                    'discard',
                );
            } else if (eventType === 'coop_cards_drawn') {
                const source = storyCoopCombatSeatActor(actorSeat);
                const target = actorSeat === viewerSeat
                    ? $('story-coop-combat-hand')
                    : source;
                await animateStoryCardFlight(source, target, 'draw', event?.count, false);
            }
        }
    }

    function renderStoryCoopCombatPlayers(snapshot) {
        const list = $('story-coop-combat-players');
        if (!list) return;
        const fragment = document.createDocumentFragment();
        (snapshot?.players || []).forEach((player) => {
            const row = document.createElement('li');
            row.className = [
                'story-coop-combat-player',
                Number(player.seat) === Number(snapshot.viewer_seat) ? 'is-viewer' : '',
                player.ready ? 'is-ready' : '',
                player.down ? 'is-down' : '',
            ].filter(Boolean).join(' ');
            row.dataset.seat = String(player.seat);
            const name = document.createElement('strong');
            name.textContent = storyCoopCombatMemberName(snapshot, player.seat);
            const state = document.createElement('span');
            const rewardStatus = snapshot?.reward?.seats?.find(
                (item) => Number(item?.seat) === Number(player.seat),
            );
            const voteStatus = snapshot?.map_vote?.seats?.find(
                (item) => Number(item?.seat) === Number(player.seat),
            );
            const roomStatus = snapshot?.room_state?.seats?.find(
                (item) => Number(item?.seat) === Number(player.seat),
            );
            const phase = String(snapshot?.phase || '');
            const roomType = String(snapshot?.room?.type || '');
            const isLeader = Number(player.seat) === Number(snapshot?.party?.leader_seat);
            if (player.down) state.textContent = '倒地 · 战斗胜利后复苏';
            else if (phase === 'journey_setup') state.textContent = isLeader ? '选择难度中' : '等待队长';
            else if (phase === 'reward') state.textContent = rewardStatus?.resolved ? '个人奖励已完成' : '选择个人奖励';
            else if (phase === 'map') state.textContent = voteStatus?.submitted ? '路线投票已提交' : '选择希望路线';
            else if (phase === 'room' && ['opening', 'rest', 'chest', 'shop', 'event'].includes(roomType)) {
                state.textContent = storyCoopRoomSeatStatus(
                    roomType,
                    Boolean(roomStatus?.submitted ?? roomStatus?.resolved),
                );
            } else if (phase === 'stage_complete') state.textContent = roomStatus?.resolved ? '已确认继续' : '等待确认继续';
            else if (phase === 'complete') state.textContent = '完整旅程完成';
            else if (phase === 'game_over') state.textContent = '旅程失败';
            else state.textContent = player.ready ? '已结束本回合' : '本回合行动中';
            const stats = document.createElement('div');
            stats.className = 'story-coop-combat-player-stats';
            const statLabels = [
                `${Number(player.health) || 0}/${Number(player.max_health) || 0}H`,
                `${Number(player.gold) || 0}G`,
            ];
            if (phase === 'combat') {
                statLabels.push(
                    `${Number(player.elixir) || 0}E`,
                    `${Number(player.magic) || 0}M`,
                    `${Number(player.shield) || 0}护盾`,
                    `手牌${Number(player.hand_count) || 0}`,
                    `抽牌${Number(player.draw_count) || 0}`,
                    `弃牌${Array.isArray(player.discard_pile) ? player.discard_pile.length : 0}`,
                    `放逐${Array.isArray(player.exile_pile) ? player.exile_pile.length : 0}`,
                );
            }
            if (Array.isArray(player.enchantment_books)) {
                statLabels.push(`附魔书${player.enchantment_books.length}/3`);
            }
            statLabels.forEach((text) => {
                const badge = document.createElement('span');
                badge.textContent = text;
                stats.appendChild(badge);
            });
            row.append(name, state, stats);
            if (phase === 'combat' && Array.isArray(player.hand) && player.hand.length) {
                const hand = document.createElement('details');
                hand.className = 'story-coop-combat-player-hand';
                const summary = document.createElement('summary');
                summary.textContent = Number(player.seat) === Number(snapshot.viewer_seat)
                    ? '查看你的手牌名称'
                    : `查看${storyCoopCombatMemberName(snapshot, player.seat)}的手牌`;
                const cards = document.createElement('span');
                cards.textContent = player.hand.map(storyCoopCombatCardLabel).join('、');
                hand.append(summary, cards);
                row.appendChild(hand);
            }
            if (Array.isArray(player.enchantment_books)) {
                const inventory = document.createElement('details');
                inventory.className = 'story-coop-enchantment-books';
                const summary = document.createElement('summary');
                summary.textContent = `你的附魔书（${player.enchantment_books.length}/3）`;
                const books = document.createElement('div');
                books.className = 'story-coop-enchantment-book-list';
                player.enchantment_books.forEach((book) => {
                    const definition = storyCoopBookDefinition(book);
                    const item = document.createElement('article');
                    item.className = `story-coop-enchantment-book is-${String(definition?.rarity || 'common')}`;
                    const imageUrl = String(definition?.image_url || '');
                    if (imageUrl) {
                        const image = document.createElement('img');
                        image.src = imageUrl;
                        image.alt = '';
                        item.appendChild(image);
                    }
                    const content = document.createElement('div');
                    const title = document.createElement('strong');
                    title.textContent = localize(definition?.name) || String(book?.book_id || '附魔书');
                    const copy = document.createElement('small');
                    copy.textContent = localize(definition?.description) || '';
                    const actions = document.createElement('span');
                    actions.className = 'story-coop-enchantment-book-actions';
                    if (phase === 'combat' && String(definition?.script || '') !== 'lethal_guard') {
                        const use = document.createElement('button');
                        use.type = 'button';
                        use.className = 'story-command story-command-primary';
                        use.textContent = '使用';
                        use.disabled = !storyCoopCombatCanAct(storyCoopCombatSession);
                        use.addEventListener('click', () => useStoryCoopEnchantmentBook(book));
                        actions.appendChild(use);
                    }
                    const discard = document.createElement('button');
                    discard.type = 'button';
                    discard.className = 'story-command story-command-danger';
                    discard.textContent = '丢弃';
                    discard.disabled = phase === 'combat'
                        ? !storyCoopCombatCanAct(storyCoopCombatSession)
                        : !storyCoopRunCanSubmit(storyCoopCombatSession);
                    discard.addEventListener('click', () => discardStoryCoopEnchantmentBook(book));
                    actions.appendChild(discard);
                    content.append(title, copy, actions);
                    item.appendChild(content);
                    books.appendChild(item);
                });
                if (!player.enchantment_books.length) {
                    const empty = document.createElement('small');
                    empty.textContent = '尚未获得附魔书。';
                    books.appendChild(empty);
                }
                inventory.append(summary, books);
                row.appendChild(inventory);
            }
            fragment.appendChild(row);
        });
        list.replaceChildren(fragment);
    }

    function renderStoryCoopCombatEnemies(session, snapshot) {
        const container = $('story-coop-combat-enemies');
        if (!container) return;
        const fragment = document.createDocumentFragment();
        (snapshot?.combat?.enemies || []).forEach((enemy) => {
            const button = document.createElement('button');
            const living = Number(enemy.health || 0) > 0;
            button.type = 'button';
            button.className = `story-coop-combat-enemy${String(enemy.id) === session.selectedEnemyId ? ' is-selected' : ''}`;
            button.dataset.enemyId = String(enemy.id || '');
            button.disabled = !living || Boolean(session.actionPromise);
            button.setAttribute('role', 'listitem');
            const top = document.createElement('span');
            top.className = 'story-coop-combat-enemy-top';
            const name = document.createElement('strong');
            name.textContent = localize(enemy.name)
                || localize(storyContent?.enemies?.[enemy.def_id]?.name)
                || enemy.def_id
                || enemy.id;
            const health = document.createElement('span');
            health.className = 'story-coop-combat-enemy-health';
            health.textContent = `${Number(enemy.health) || 0}/${Number(enemy.max_health) || 0}H`;
            top.append(name, health);
            const imageUrl = String(
                enemy.image_url
                || storyContent?.enemies?.[enemy.def_id]?.image_url
                || '',
            ).trim();
            if (imageUrl) {
                const image = document.createElement('img');
                image.className = 'story-coop-combat-enemy-image';
                image.src = imageUrl;
                image.alt = '';
                image.loading = 'eager';
                button.appendChild(image);
            }
            const intent = document.createElement('span');
            intent.className = 'story-coop-combat-enemy-intent';
            const target = enemy.intent?.target_seat;
            const targetText = Number.isInteger(Number(target))
                ? ` → ${storyCoopCombatMemberName(snapshot, target)}`
                : '';
            const hits = Math.max(1, Number(enemy.intent?.hits || 1));
            const moveName = localize(enemy.intent?.move_name);
            const intentPrefix = moveName ? `${moveName} · ` : '';
            const enemyEffects = [
                Number(enemy.shield) > 0 ? `${Number(enemy.shield)}S` : '',
                Number(enemy.power) > 0 ? `${Number(enemy.power)}力量` : '',
                Number(enemy.statuses?.weak) > 0 ? `${Number(enemy.statuses.weak)}虚弱` : '',
                Number(enemy.statuses?.vulnerable) > 0 ? `${Number(enemy.statuses.vulnerable)}易伤` : '',
                Number(enemy.statuses?.fire) > 0 ? `${Number(enemy.statuses.fire)}烈火` : '',
            ].filter(Boolean);
            const effectText = enemyEffects.length ? ` · ${enemyEffects.join(' / ')}` : '';
            intent.textContent = enemy.intent?.kind === 'attack'
                ? `意图：${intentPrefix}${Number(enemy.intent?.amount) || 0}D${hits > 1 ? ` × ${hits}` : ''}${targetText}${effectText}`
                : (
                    enemy.intent?.kind === 'attack_all'
                        ? `意图：${intentPrefix}对全队${Number(enemy.intent?.amount) || 0}D${hits > 1 ? ` × ${hits}` : ''}${effectText}`
                        : `意图：${moveName || String(enemy.intent?.kind || '未知')}${effectText}`
                );
            button.append(top, intent);
            button.addEventListener('click', () => {
                if (!living || session !== storyCoopCombatSession) return;
                session.selectedEnemyId = String(enemy.id || '');
                renderStoryCoopCombat();
            });
            fragment.appendChild(button);
        });
        container.replaceChildren(fragment);
    }

    function renderStoryCoopCombatHand(session, snapshot) {
        const container = $('story-coop-combat-hand');
        if (!container) return;
        const viewer = storyCoopCombatViewer(session);
        const canAct = storyCoopCombatCanAct(session);
        const fragment = document.createDocumentFragment();
        (viewer?.hand || []).forEach((card) => {
            const values = cardValues(card);
            const affordable = Number(viewer.elixir || 0) >= Number(values?.cost_e || 0)
                && Number(viewer.magic || 0) >= Number(values?.cost_m || 0)
                && Number(viewer.health || 0) > Number(card?.modifiers?.enchantment_health_cost || 0);
            const instanceId = String(card?.instance_id || '');
            const button = createStoryCard(card, {
                compact: true,
                interactive: true,
                disabled: !canAct || !affordable,
                onClick: () => selectStoryCoopCombatCard(instanceId),
            });
            button.dataset.instanceId = instanceId;
            if (instanceId === session.pendingCardId) button.classList.add('is-pending-play');
            if (session.discardSelection.has(instanceId)) button.classList.add('is-selected-discard');
            fragment.appendChild(button);
        });
        if (!viewer?.hand?.length) {
            const empty = document.createElement('p');
            empty.textContent = viewer?.ready ? '你已准备完毕，正在等待队友。' : '当前没有手牌。';
            fragment.appendChild(empty);
        }
        container.replaceChildren(fragment);
    }

    function renderStoryCoopCombatEvents(snapshot) {
        const list = $('story-coop-combat-event-list');
        if (!list) return;
        const events = Array.isArray(snapshot?.last_events) ? snapshot.last_events.slice(-12) : [];
        const fragment = document.createDocumentFragment();
        events.forEach((event) => {
            const item = document.createElement('li');
            item.textContent = storyCoopCombatEventText(event, snapshot);
            fragment.appendChild(item);
        });
        if (!events.length) {
            const item = document.createElement('li');
            item.textContent = '等待首个协作动作。';
            fragment.appendChild(item);
        }
        list.replaceChildren(fragment);
    }

    function replaceStoryCoopProgressionOptions(container, fragment) {
        if (!container) return;
        const focusedKey = document.activeElement?.dataset?.coopChoiceKey || '';
        container.replaceChildren(fragment);
        if (focusedKey) {
            const escaped = globalThis.CSS?.escape
                ? CSS.escape(focusedKey)
                : focusedKey.replace(/["\\]/g, '\\$&');
            container.querySelector(`[data-coop-choice-key="${escaped}"]`)?.focus({ preventScroll: true });
        }
    }

    function renderStoryCoopSetup(session, snapshot) {
        const options = $('story-coop-setup-options');
        if (!options) return;
        const viewerIsLeader = storyCoopSetupViewerIsLeader(session);
        const canChoose = storyCoopSetupCanChoose(session);
        const available = storyCoopSetupDifficultySet(session);
        const definitions = {
            normal: {
                title: '普通',
                description: '标准花园路线、奖励和敌人强度。',
            },
            hard: {
                title: '困难',
                description: '危险路线更多；奖励金币为普通难度的75%；商店价格为110%。',
            },
            lunatic: {
                title: '疯狂',
                description: '继承困难规则；敌人H和伤害提升至125%。',
            },
        };
        const fragment = document.createDocumentFragment();
        if (!viewerIsLeader) {
            const waiting = document.createElement('p');
            waiting.className = 'story-coop-setup-waiting';
            waiting.setAttribute('role', 'status');
            waiting.textContent = '正在等待队长选择花园难度。';
            fragment.appendChild(waiting);
        } else {
            ['normal', 'hard', 'lunatic'].forEach((difficulty) => {
                if (!available.has(difficulty)) return;
                const definition = definitions[difficulty];
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'story-coop-progression-choice';
                button.dataset.coopChoiceKey = `setup:${difficulty}`;
                button.disabled = !canChoose;
                const title = document.createElement('strong');
                title.textContent = definition.title;
                const copy = document.createElement('small');
                copy.textContent = definition.description;
                button.append(title, copy);
                button.addEventListener('click', () => {
                    if (
                        !storyCoopSetupCanChoose(session)
                        || !storyCoopSetupDifficultySet(session).has(difficulty)
                    ) return;
                    storyCoopCombatAction('setup_start', { difficulty });
                });
                fragment.appendChild(button);
            });
            if (!fragment.childNodes.length) {
                const unavailable = document.createElement('p');
                unavailable.className = 'story-coop-setup-waiting';
                unavailable.textContent = '服务器暂未返回可用的花园难度。';
                fragment.appendChild(unavailable);
            }
        }
        replaceStoryCoopProgressionOptions(options, fragment);
    }

    function renderStoryCoopOpening(session, snapshot) {
        const roomState = storyCoopOpeningRoomState(session);
        const options = $('story-coop-opening-options');
        if (!roomState || !options) return;
        const canChoose = storyCoopOpeningCanChoose(session);
        const available = new Set(
            (Array.isArray(roomState.options) ? roomState.options : [])
                .map((option) => String(option || '').trim().toLowerCase()),
        );
        const fragment = document.createDocumentFragment();
        (Array.isArray(roomState.options) ? roomState.options : []).forEach((rawOptionId) => {
            const optionId = String(rawOptionId || '').trim().toLowerCase();
            if (!available.has(optionId)) return;
            const definition = storyContent?.blessings?.[optionId] || {};
            const contentName = localize(definition.name);
            const contentDescription = localize(definition.description);
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'story-coop-progression-choice';
            button.dataset.coopChoiceKey = `opening:${optionId}`;
            button.disabled = !canChoose;
            button.setAttribute('aria-pressed', String(roomState.selected_option === optionId));
            const title = document.createElement('strong');
            title.textContent = contentName || contentDescription || optionId;
            button.appendChild(title);
            if (contentDescription && contentDescription !== title.textContent) {
                const copy = document.createElement('small');
                copy.textContent = contentDescription;
                button.appendChild(copy);
            }
            button.addEventListener('click', () => {
                const current = storyCoopOpeningRoomState(session);
                const currentOptions = new Set(
                    (Array.isArray(current?.options) ? current.options : [])
                        .map((option) => String(option || '').trim().toLowerCase()),
                );
                if (!storyCoopOpeningCanChoose(session) || !currentOptions.has(optionId)) return;
                storyCoopCombatAction('opening_choose', {
                    room_id: String(current.room_id || ''),
                    option_id: optionId,
                });
            });
            fragment.appendChild(button);
        });
        if (!fragment.childNodes.length) {
            const empty = document.createElement('p');
            empty.className = 'story-coop-setup-waiting';
            empty.textContent = roomState.status === 'resolved'
                ? '你的开局赐福已经完成。'
                : '服务器暂未返回可用的开局赐福。';
            fragment.appendChild(empty);
        }
        replaceStoryCoopProgressionOptions(options, fragment);
        renderStoryCoopRoomPartyStatuses('story-coop-opening-party-status', snapshot, roomState);
    }

    function renderStoryCoopReward(session, snapshot) {
        const reward = snapshot?.reward;
        const options = $('story-coop-reward-options');
        const statuses = $('story-coop-reward-party-status');
        if (!options || !statuses) return;
        const canChoose = storyCoopRewardCanChoose(session);
        const canChooseCard = canChoose && reward?.card_status === 'pending';
        const canChooseBook = canChoose && reward?.book_status === 'pending';
        setText(
            'story-coop-reward-title',
            Number(reward?.card_round_total || 1) > 1
                ? `选择第${Number(reward?.card_round_index || 1)}/${Number(reward?.card_round_total || 1)}张卡牌${reward?.enchantment_book_id ? '并处理附魔书' : ''}`
                : (reward?.enchantment_book_id ? '选择卡牌并处理附魔书' : '选择1张卡牌'),
        );
        const fragment = document.createDocumentFragment();
        (reward?.options || []).forEach((option) => {
            const cardId = String(option?.card_id || '');
            const values = storyContent?.cards?.[cardId] || {};
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'story-coop-progression-choice';
            button.dataset.coopChoiceKey = `reward:${cardId}`;
            button.disabled = !canChooseCard;
            button.setAttribute('aria-pressed', String(reward?.selected_card_id === cardId));
            const name = document.createElement('strong');
            name.textContent = `${option?.upgraded ? '+' : ''}${localize(values.name) || cardId}`;
            const description = document.createElement('small');
            description.textContent = localize(
                option?.upgraded ? (values.upgrade?.description || values.description) : values.description,
            ) || `获得卡牌 ${cardId}`;
            const cost = document.createElement('small');
            cost.textContent = `${Number(values.cost_e) || 0}E · ${Number(values.cost_m) || 0}M`;
            button.append(name, description, cost);
            button.addEventListener('click', () => {
                if (!storyCoopRewardCanChoose(session) || reward?.card_status !== 'pending') return;
                storyCoopCombatAction('reward_choose', {
                    reward_id: String(reward.reward_id || ''),
                    choice_kind: 'card',
                    card_id: cardId,
                });
            });
            fragment.appendChild(button);
        });
        const skip = document.createElement('button');
        skip.type = 'button';
        skip.className = 'story-coop-progression-choice is-skip';
        skip.dataset.coopChoiceKey = 'reward:skip';
        skip.disabled = !canChooseCard;
        skip.setAttribute('aria-pressed', String(Boolean(reward?.skipped)));
        const skipName = document.createElement('strong');
        skipName.textContent = '跳过选卡';
        const skipDescription = document.createElement('small');
        skipDescription.textContent = '不获得卡牌，保持当前卡组规模。';
        skip.append(skipName, skipDescription);
        skip.addEventListener('click', () => {
            if (!storyCoopRewardCanChoose(session) || reward?.card_status !== 'pending') return;
            storyCoopCombatAction('reward_choose', {
                reward_id: String(reward?.reward_id || ''),
                choice_kind: 'card',
                card_id: '',
            });
        });
        fragment.appendChild(skip);

        const bookId = String(reward?.enchantment_book_id || '');
        if (bookId) {
            const definition = storyCoopBookDefinition(bookId);
            const book = document.createElement('article');
            book.className = `story-coop-enchantment-book story-coop-enchantment-book-reward is-${String(definition?.rarity || 'common')}`;
            const imageUrl = String(definition?.image_url || '');
            if (imageUrl) {
                const image = document.createElement('img');
                image.src = imageUrl;
                image.alt = '';
                book.appendChild(image);
            }
            const content = document.createElement('div');
            const name = document.createElement('strong');
            name.textContent = localize(definition?.name) || bookId;
            const description = document.createElement('small');
            description.textContent = localize(definition?.description) || '故事模式附魔书';
            const actions = document.createElement('span');
            actions.className = 'story-coop-enchantment-book-actions';
            const take = document.createElement('button');
            take.type = 'button';
            take.className = 'story-command story-command-primary';
            take.textContent = reward?.book_status === 'resolved' ? '已处理' : '收下附魔书';
            take.disabled = !canChooseBook;
            take.addEventListener('click', () => {
                if (!storyCoopRewardCanChoose(session) || reward?.book_status !== 'pending') return;
                const replacement = chooseStoryCoopBookReplacement(session);
                if (replacement == null) return;
                storyCoopCombatAction('reward_choose', {
                    reward_id: String(reward?.reward_id || ''),
                    choice_kind: 'enchantment_book',
                    book_id: bookId,
                    ...(replacement ? { replace_book_instance_id: replacement } : {}),
                });
            });
            const skipBook = document.createElement('button');
            skipBook.type = 'button';
            skipBook.className = 'story-command';
            skipBook.textContent = '放弃附魔书';
            skipBook.disabled = !canChooseBook;
            skipBook.addEventListener('click', () => {
                if (!storyCoopRewardCanChoose(session) || reward?.book_status !== 'pending') return;
                storyCoopCombatAction('reward_choose', {
                    reward_id: String(reward?.reward_id || ''),
                    choice_kind: 'enchantment_book',
                    book_id: '',
                });
            });
            actions.append(take, skipBook);
            content.append(name, description, actions);
            book.appendChild(content);
            fragment.appendChild(book);
        }
        replaceStoryCoopProgressionOptions(options, fragment);

        const statusFragment = document.createDocumentFragment();
        (reward?.seats || []).forEach((item) => {
            const row = document.createElement('li');
            row.className = item?.resolved ? 'is-complete' : '';
            row.textContent = `${storyCoopCombatMemberName(snapshot, item?.seat)}：${item?.resolved ? '已完成' : '选择中'}`;
            statusFragment.appendChild(row);
        });
        statuses.replaceChildren(statusFragment);
    }

    function renderStoryCoopMapVote(session, snapshot) {
        const vote = snapshot?.map_vote;
        const options = $('story-coop-map-options');
        const statuses = $('story-coop-map-party-status');
        if (!options || !statuses) return;
        const canVote = storyCoopMapCanVote(session);
        const fragment = document.createDocumentFragment();
        (vote?.options || []).forEach((option, index) => {
            const nodeId = String(option?.node_id || '');
            const routeType = String(option?.type || '');
            const button = document.createElement('button');
            button.type = 'button';
            button.className = `story-coop-progression-choice story-coop-map-choice is-${routeType || 'unknown'}`;
            button.dataset.coopChoiceKey = `route:${nodeId}`;
            button.disabled = !canVote;
            button.setAttribute('aria-pressed', String(vote?.viewer_node_id === nodeId));
            const iconUrl = String(STORY_MAP_ROOM_ICON_URLS[routeType] || '').trim();
            if (iconUrl) {
                const icon = document.createElement('img');
                icon.className = 'story-coop-map-choice-icon';
                icon.src = iconUrl;
                icon.alt = '';
                button.appendChild(icon);
            } else {
                const icon = document.createElement('span');
                icon.className = 'story-coop-map-choice-symbol';
                icon.setAttribute('aria-hidden', 'true');
                icon.textContent = routeType === 'chest' ? '🎁' : (routeType === 'boss' ? '♛' : '◆');
                button.appendChild(icon);
            }
            const name = document.createElement('strong');
            name.textContent = `第${Number(option?.floor) || '?'}层 · 路线 ${index + 1}`;
            const description = document.createElement('small');
            const routeLabels = {
                combat: '战斗节点',
                elite: '精英战斗',
                rest: '休息节点',
                chest: '宝箱节点',
                shop: '商店节点',
                event: '事件节点',
                boss: '首领战斗',
            };
            description.textContent = routeLabels[routeType] || '未知节点';
            button.append(name, description);
            button.addEventListener('click', () => {
                if (!storyCoopMapCanVote(session)) return;
                storyCoopCombatAction('map_vote', {
                    vote_id: String(vote?.vote_id || ''),
                    node_id: nodeId,
                });
            });
            fragment.appendChild(button);
        });
        replaceStoryCoopProgressionOptions(options, fragment);

        const statusFragment = document.createDocumentFragment();
        (vote?.seats || []).forEach((item) => {
            const row = document.createElement('li');
            row.className = item?.submitted ? 'is-complete' : '';
            row.textContent = `${storyCoopCombatMemberName(snapshot, item?.seat)}：${item?.submitted ? '已投票' : '等待投票'}`;
            statusFragment.appendChild(row);
        });
        statuses.replaceChildren(statusFragment);
    }

    function renderStoryCoopRoomPartyStatuses(containerId, snapshot, roomState) {
        const statuses = $(containerId);
        if (!statuses) return;
        const fragment = document.createDocumentFragment();
        (Array.isArray(roomState?.seats) ? roomState.seats : []).forEach((item) => {
            const submitted = Boolean(item?.submitted ?? item?.resolved);
            const row = document.createElement('li');
            row.className = submitted ? 'is-complete' : '';
            row.textContent = `${storyCoopCombatMemberName(snapshot, item?.seat)}：${storyCoopRoomSeatStatus(roomState?.type, submitted)}`;
            fragment.appendChild(row);
        });
        statuses.replaceChildren(fragment);
    }

    function renderStoryCoopRest(session, snapshot) {
        const roomState = storyCoopRestRoomState(session);
        const optionsContainer = $('story-coop-rest-options');
        const deckContainer = $('story-coop-rest-deck');
        if (!roomState || !optionsContainer || !deckContainer) return;
        const canChoose = storyCoopRestCanChoose(session);
        const availableOptions = storyCoopRestOptionSet(roomState);
        const actionFragment = document.createDocumentFragment();
        const addAction = (choice, title, description, skipStyle = false) => {
            if (!availableOptions.has(choice)) return;
            const button = document.createElement('button');
            button.type = 'button';
            button.className = `story-coop-progression-choice${skipStyle ? ' is-skip' : ''}`;
            button.dataset.coopChoiceKey = `rest:${choice}`;
            button.disabled = !canChoose;
            const name = document.createElement('strong');
            name.textContent = title;
            const copy = document.createElement('small');
            copy.textContent = description;
            button.append(name, copy);
            button.addEventListener('click', () => {
                chooseStoryCoopRoomOption(session, 'rest', choice);
            });
            actionFragment.appendChild(button);
        };
        addAction('heal', '恢复生命', '按服务器规则恢复你的生命值，并完成本次休息。');
        const restGold = Math.max(0, Math.floor(Number(roomState.rest_gold) || 0));
        addAction(
            'gold',
            `获得 ${restGold}G`,
            '由你持有的贪婪遗物提供；领取后完成本次休息。',
        );
        addAction('leave', '直接离开', '不恢复也不升级，立即完成本次休息。', true);
        if (!actionFragment.childNodes.length) {
            const message = document.createElement('p');
            message.className = 'story-coop-rest-empty';
            message.textContent = availableOptions.has('upgrade')
                ? '请从右侧选择1张卡牌升级。'
                : '当前没有可执行的休息选项。';
            actionFragment.appendChild(message);
        }
        replaceStoryCoopProgressionOptions(optionsContainer, actionFragment);

        const upgrade = $('story-coop-rest-upgrade');
        const canUpgrade = availableOptions.has('upgrade');
        upgrade?.classList.toggle('hidden', !canUpgrade);
        const eligibleDeck = (Array.isArray(roomState.deck) ? roomState.deck : []).filter(
            (card) => !card?.upgraded && Number(card?.upgrade_level || 0) <= 0,
        );
        const eligibleIds = new Set(
            eligibleDeck.map((card) => String(card?.instance_id || '')),
        );
        if (!eligibleIds.has(session.selectedRestCardId)) session.selectedRestCardId = '';
        const deckFragment = document.createDocumentFragment();
        if (canUpgrade) {
            eligibleDeck.forEach((card) => {
                const instanceId = String(card?.instance_id || '');
                const selected = instanceId === session.selectedRestCardId;
                const button = createStoryCard(card, {
                    compact: true,
                    interactive: true,
                    disabled: !canChoose,
                    previewUpgradeOnHover: true,
                    onClick: () => {
                        if (!storyCoopRestCanChoose(session)) return;
                        session.selectedRestCardId = selected ? '' : instanceId;
                        renderStoryCoopCombat();
                    },
                });
                button.dataset.coopChoiceKey = `rest:upgrade:${instanceId}`;
                button.setAttribute('role', 'option');
                button.setAttribute('aria-selected', String(selected));
                if (selected) button.classList.add('is-selected-upgrade');
                deckFragment.appendChild(button);
            });
            if (!eligibleDeck.length) {
                const empty = document.createElement('p');
                empty.className = 'story-coop-rest-empty';
                empty.textContent = '你的卡组中没有可升级卡牌，请选择其他休息方式。';
                deckFragment.appendChild(empty);
            }
        }
        replaceStoryCoopProgressionOptions(deckContainer, deckFragment);
        const confirm = $('story-coop-rest-upgrade-confirm');
        if (confirm) {
            confirm.disabled = !canChoose || !canUpgrade || !session.selectedRestCardId;
        }

        renderStoryCoopRoomPartyStatuses('story-coop-rest-party-status', snapshot, roomState);
    }

    function renderStoryCoopChest(session, snapshot) {
        const roomState = storyCoopChestRoomState(session);
        const optionsContainer = $('story-coop-chest-options');
        if (!roomState || !optionsContainer) return;
        const gold = Math.max(0, Math.floor(Number(roomState.gold) || 0));
        setText('story-coop-chest-gold', `${gold}G`);
        const canChoose = storyCoopRoomCanChoose(session, 'chest');
        const availableOptions = storyCoopRoomOptionSet(roomState);
        const fragment = document.createDocumentFragment();
        const addChoice = (choice, title, description, skipStyle = false) => {
            if (!availableOptions.has(choice)) return;
            const button = document.createElement('button');
            button.type = 'button';
            button.className = `story-coop-progression-choice${skipStyle ? ' is-skip' : ''}`;
            button.dataset.coopChoiceKey = `chest:${choice}`;
            button.disabled = !canChoose;
            const name = document.createElement('strong');
            name.textContent = title;
            const copy = document.createElement('small');
            copy.textContent = description;
            button.append(name, copy);
            button.addEventListener('click', () => {
                chooseStoryCoopRoomOption(session, 'chest', choice);
            });
            fragment.appendChild(button);
        };
        addChoice('claim_gold', `领取 ${gold}G`, '金币将由服务器加入你的个人旅程资源。');
        const relicId = String(roomState.relic_id || '');
        const relic = storyContent?.relics?.[relicId] || {};
        addChoice(
            'claim_relic',
            `领取 ${localize(relic.name) || relicId || '遗物'}`,
            localize(relic.description) || '遗物将由服务器加入你的个人旅程状态。',
        );
        addChoice('leave', '放弃并离开', '不领取金币或遗物，立即完成你的宝箱选择。', true);
        if (!fragment.childNodes.length) {
            const empty = document.createElement('p');
            empty.className = 'story-coop-rest-empty';
            empty.textContent = '当前没有可执行的宝箱选项。';
            fragment.appendChild(empty);
        }
        replaceStoryCoopProgressionOptions(optionsContainer, fragment);
        renderStoryCoopRoomPartyStatuses('story-coop-chest-party-status', snapshot, roomState);
    }

    function renderStoryCoopShop(session, snapshot) {
        const roomState = storyCoopShopRoomState(session);
        const offersContainer = $('story-coop-shop-offers');
        if (!roomState || !offersContainer) return;
        const viewerGold = Math.max(0, Math.floor(Number(roomState.gold) || 0));
        const availableOptions = storyCoopRoomOptionSet(roomState);
        const canChoose = storyCoopRoomCanChoose(session, 'shop');
        const canBuy = storyCoopShopCanBuy(session);
        setText('story-coop-shop-gold', `${viewerGold}G`);
        const leave = $('story-coop-shop-leave');
        if (leave) leave.disabled = !canChoose || !availableOptions.has('leave');

        const fragment = document.createDocumentFragment();
        (Array.isArray(roomState.offers) ? roomState.offers : []).forEach((offer) => {
            const offerId = String(offer?.offer_id || '');
            const kind = String(offer?.kind || 'card');
            const cardId = String(offer?.card_id || '');
            const relicId = String(offer?.relic_id || '');
            const bookId = String(offer?.book_id || '');
            const status = String(offer?.status || '');
            const rawPrice = Number(offer?.price);
            const validPrice = Number.isFinite(rawPrice) && rawPrice >= 0;
            const price = validPrice ? Math.floor(rawPrice) : 0;
            const purchased = status === 'purchased';
            const available = status === 'available';
            const affordable = validPrice && viewerGold >= price;
            const note = purchased
                ? '已购买'
                : (validPrice ? `${price}G${affordable ? '' : ' · 金币不足'}` : '价格不可用');
            const buyOffer = () => {
                const current = storyCoopShopRoomState(session);
                const currentOffer = (Array.isArray(current?.offers) ? current.offers : []).find(
                    (item) => String(item?.offer_id || '') === offerId,
                );
                const currentPrice = Number(currentOffer?.price);
                const currentGold = Number(current?.gold);
                if (
                    !current
                    || !storyCoopShopCanBuy(session)
                    || String(currentOffer?.status || '') !== 'available'
                    || !Number.isFinite(currentPrice)
                    || !Number.isFinite(currentGold)
                    || currentPrice < 0
                    || currentGold < currentPrice
                ) return;
                const replacement = kind === 'enchantment_book'
                    ? chooseStoryCoopBookReplacement(session)
                    : '';
                if (replacement == null) return;
                storyCoopCombatAction('shop_buy', {
                    room_id: String(current.room_id || ''),
                    offer_id: String(currentOffer.offer_id || ''),
                    ...(replacement ? { replace_book_instance_id: replacement } : {}),
                });
            };
            let button;
            if (kind === 'relic') {
                const definition = storyContent?.relics?.[relicId] || {};
                button = document.createElement('button');
                button.type = 'button';
                button.className = 'story-coop-progression-choice story-coop-shop-relic';
                button.disabled = !canBuy || !available || !affordable;
                const name = document.createElement('strong');
                name.textContent = localize(definition.name) || relicId || '遗物';
                const description = document.createElement('small');
                description.textContent = localize(definition.description) || '个人旅程遗物';
                const priceLabel = document.createElement('span');
                priceLabel.className = 'story-coop-shop-offer-price';
                priceLabel.textContent = note;
                button.append(name, description, priceLabel);
                button.addEventListener('click', buyOffer);
            } else if (kind === 'enchantment_book') {
                const definition = storyCoopBookDefinition(bookId);
                button = document.createElement('button');
                button.type = 'button';
                button.className = `story-coop-enchantment-book story-coop-shop-book is-${String(definition?.rarity || 'common')}`;
                button.disabled = !canBuy || !available || !affordable;
                const imageUrl = String(definition?.image_url || '');
                if (imageUrl) {
                    const image = document.createElement('img');
                    image.src = imageUrl;
                    image.alt = '';
                    button.appendChild(image);
                }
                const content = document.createElement('span');
                const name = document.createElement('strong');
                name.textContent = localize(definition?.name) || bookId || '附魔书';
                const description = document.createElement('small');
                description.textContent = localize(definition?.description) || '故事模式附魔书';
                const priceLabel = document.createElement('span');
                priceLabel.className = 'story-coop-shop-offer-price';
                priceLabel.textContent = note;
                content.append(name, description, priceLabel);
                button.appendChild(content);
                button.addEventListener('click', buyOffer);
            } else {
                button = createStoryCard({
                    def_id: cardId,
                    upgraded: Boolean(offer?.upgraded),
                    upgrade_level: offer?.upgraded ? 1 : 0,
                }, {
                    compact: true,
                    interactive: true,
                    disabled: !canBuy || !available || !affordable,
                    note,
                    onClick: buyOffer,
                });
            }
            button.dataset.coopChoiceKey = `shop:${offerId}`;
            button.classList.toggle('is-purchased', purchased);
            button.classList.toggle('is-unaffordable', available && !affordable);
            fragment.appendChild(button);
        });
        if (!fragment.childNodes.length) {
            const empty = document.createElement('p');
            empty.className = 'story-coop-rest-empty';
            empty.textContent = '当前没有可购买的商品。';
            fragment.appendChild(empty);
        }
        replaceStoryCoopProgressionOptions(offersContainer, fragment);
        renderStoryCoopRoomPartyStatuses('story-coop-shop-party-status', snapshot, roomState);
    }

    function renderStoryCoopEvent(session, snapshot) {
        const roomState = storyCoopEventRoomState(session);
        const optionsContainer = $('story-coop-event-options');
        if (!roomState || !optionsContainer) return;
        const title = localize(roomState?.title || snapshot?.room?.title) || '协作事件';
        const description = localize(roomState?.description || snapshot?.room?.description)
            || '双方分别提交选择；未决前只显示提交状态。';
        setText('story-coop-event-title', title);
        setText('story-coop-event-description', description);
        const availableOptions = storyCoopRoomOptionSet(roomState);
        const canChoose = storyCoopRoomCanChoose(session, 'event');
        const definitions = Array.isArray(roomState?.option_definitions)
            ? roomState.option_definitions
            : [];
        const fragment = document.createDocumentFragment();
        definitions.forEach((definition) => {
            const choice = String(definition?.id || '');
            if (!availableOptions.has(choice)) return;
            const button = document.createElement('button');
            button.type = 'button';
            button.className = `story-coop-progression-choice${definition?.risky ? ' is-risk' : ''}`;
            button.dataset.coopChoiceKey = `event:${choice}`;
            button.disabled = !canChoose;
            const name = document.createElement('strong');
            name.textContent = localize(definition?.label) || choice;
            const copy = document.createElement('small');
            copy.textContent = localize(definition?.description);
            button.append(name, copy);
            button.addEventListener('click', async () => {
                const targetRoomId = String(roomState?.room_id || '');
                const targetRevision = Number(session?.run?.revision || 0);
                if (definition?.requires_confirmation) {
                    button.disabled = true;
                    const title = localize(definition?.label) || '确认事件选择';
                    const message = localize(definition?.description) || '该选择可能带来损失。';
                    const confirmHandler = window.GTN_SHORTCUT_HOST?.confirm;
                    const accepted = typeof confirmHandler === 'function'
                        ? Boolean(await confirmHandler(title, message))
                        : window.confirm([title, message].filter(Boolean).join('\n\n'));
                    const currentRoom = storyCoopEventRoomState(session);
                    if (
                        !accepted
                        || session !== storyCoopCombatSession
                        || String(currentRoom?.room_id || '') !== targetRoomId
                        || Number(session?.run?.revision || 0) !== targetRevision
                    ) {
                        renderStoryCoopCombat();
                        return;
                    }
                }
                chooseStoryCoopRoomOption(session, 'event', choice);
            });
            fragment.appendChild(button);
        });
        if (!fragment.childNodes.length) {
            const empty = document.createElement('p');
            empty.className = 'story-coop-rest-empty';
            empty.textContent = '当前没有可提交的事件选项。';
            fragment.appendChild(empty);
        }
        replaceStoryCoopProgressionOptions(optionsContainer, fragment);
        renderStoryCoopRoomPartyStatuses('story-coop-event-party-status', snapshot, roomState);
    }

    function renderStoryCoopCombat() {
        const session = storyCoopCombatSession;
        if (!session || !storyCoopCombatDialogOpen()) return;
        const run = session.run;
        const snapshot = storyCoopCombatSnapshot(session);
        renderStorySeededBackdrop(
            snapshot ? { id: run?.id, visual_seed: run?.visual_seed, state: snapshot } : null,
            'story-coop-seeded-backdrop',
        );
        const combat = snapshot?.combat;
        const viewer = storyCoopCombatViewer(session);
        const phase = String(snapshot?.phase || '');
        const inSetup = phase === 'journey_setup';
        const inOpening = phase === 'room'
            && snapshot?.room?.type === 'opening'
            && Boolean(storyCoopOpeningRoomState(session));
        const inCombat = phase === 'combat' && Boolean(combat);
        const inReward = phase === 'reward' && Boolean(snapshot?.reward);
        const onMap = phase === 'map' && Boolean(snapshot?.map_vote);
        const inRest = phase === 'room'
            && snapshot?.room?.type === 'rest'
            && Boolean(storyCoopRestRoomState(session));
        const inChest = phase === 'room'
            && snapshot?.room?.type === 'chest'
            && Boolean(storyCoopChestRoomState(session));
        const inShop = phase === 'room'
            && snapshot?.room?.type === 'shop'
            && Boolean(storyCoopShopRoomState(session));
        const inEvent = phase === 'room'
            && snapshot?.room?.type === 'event'
            && Boolean(storyCoopEventRoomState(session));
        const complete = phase === 'complete';
        const stageComplete = phase === 'stage_complete';
        const failed = phase === 'game_over' || combat?.outcome === 'defeat';
        const lastEvents = Array.isArray(snapshot?.last_events) ? snapshot.last_events : [];
        const lastEventType = String(lastEvents[lastEvents.length - 1]?.type || '');
        const biomeLabel = ({ garden: '花园', jungle: '丛林', factory: '工厂' })[
            String(snapshot?.biome || '')
        ] || '未知区域';
        setText('story-coop-combat-eyebrow', `双人协作 · ${biomeLabel}`);
        let dialogTitle = '协作战斗';
        if (inSetup) dialogTitle = '协作旅程设置';
        else if (inOpening) dialogTitle = '协作开局赐福';
        else if (inRest) dialogTitle = '协作休息点';
        else if (inChest) dialogTitle = '协作补给箱';
        else if (inShop) dialogTitle = '协作个人商店';
        else if (inEvent) dialogTitle = '协作事件';
        else if (inReward) dialogTitle = '协作奖励';
        else if (onMap) dialogTitle = '协作路线投票';
        else if (stageComplete) dialogTitle = `协作第${Math.max(1, Number(snapshot?.stage) || 1)}阶段完成`;
        else if (complete) dialogTitle = '协作完整旅程完成';
        else if (failed) dialogTitle = '协作旅程失败';
        setText(
            'story-coop-combat-title',
            dialogTitle,
        );
        setText('story-coop-combat-revision', storyCoopProgressLabel(snapshot));
        setText('story-coop-combat-sequence', storyCoopSnapshotDifficultyLabel(snapshot));
        setText('story-coop-combat-round', String(combat?.round ?? '--'));
        setText('story-coop-combat-turn', storyCoopPhaseLabel(snapshot));
        renderStoryCoopCombatPlayers(snapshot);
        $('story-coop-combat-board')?.classList.toggle('hidden', !inCombat);
        $('story-coop-setup-panel')?.classList.toggle('hidden', !inSetup);
        $('story-coop-opening-panel')?.classList.toggle('hidden', !inOpening);
        $('story-coop-reward-panel')?.classList.toggle('hidden', !inReward);
        $('story-coop-map-panel')?.classList.toggle('hidden', !onMap);
        $('story-coop-rest-panel')?.classList.toggle('hidden', !inRest);
        $('story-coop-chest-panel')?.classList.toggle('hidden', !inChest);
        $('story-coop-shop-panel')?.classList.toggle('hidden', !inShop);
        $('story-coop-event-panel')?.classList.toggle('hidden', !inEvent);
        $('story-coop-complete-panel')?.classList.toggle('hidden', !complete && !stageComplete);
        setText(
            'story-coop-complete-title',
            stageComplete
                ? (localize(snapshot?.room?.title) || `协作第${Math.max(1, Number(snapshot?.stage) || 1)}阶段完成`)
                : '协作完整旅程完成',
        );
        setText(
            'story-coop-complete-copy',
            stageComplete
                ? (localize(snapshot?.room?.description) || '双方确认后继续旅程。')
                : '你们已经通关全部三个阶段；通关与角色解锁进度已分别记入双方账号。',
        );
        const stageReady = $('story-coop-stage-ready');
        stageReady?.classList.toggle('hidden', !stageComplete);
        if (stageReady) {
            stageReady.disabled = !storyCoopStageCanReady(session);
            stageReady.textContent = snapshot?.room_state?.status === 'resolved'
                ? '已确认，等待队友...'
                : (Number(snapshot?.stage) >= 3 ? '确认完成旅程' : '确认并进入下一阶段');
        }
        const stagePartyStatus = $('story-coop-stage-party-status');
        stagePartyStatus?.classList.toggle('hidden', !stageComplete);
        if (stageComplete) {
            renderStoryCoopRoomPartyStatuses(
                'story-coop-stage-party-status',
                snapshot,
                snapshot.room_state,
            );
        } else {
            stagePartyStatus?.replaceChildren();
        }
        if (inCombat) {
            renderStoryCoopCombatEnemies(session, snapshot);
            renderStoryCoopCombatHand(session, snapshot);
        } else {
            $('story-coop-combat-enemies')?.replaceChildren();
            $('story-coop-combat-hand')?.replaceChildren();
        }
        if (inSetup) renderStoryCoopSetup(session, snapshot);
        if (inOpening) renderStoryCoopOpening(session, snapshot);
        if (inReward) renderStoryCoopReward(session, snapshot);
        if (onMap) renderStoryCoopMapVote(session, snapshot);
        if (inRest) renderStoryCoopRest(session, snapshot);
        if (inChest) renderStoryCoopChest(session, snapshot);
        if (inShop) renderStoryCoopShop(session, snapshot);
        if (inEvent) renderStoryCoopEvent(session, snapshot);
        renderStoryCoopCombatEvents(snapshot);

        const canAct = storyCoopCombatCanAct(session);
        const pendingCard = (viewer?.hand || []).find(
            (card) => String(card?.instance_id || '') === session.pendingCardId,
        );
        const requirement = storyCoopCombatDiscardRequirement(pendingCard);
        const selectionValid = Boolean(
            pendingCard
            && session.discardSelection.size >= requirement.minimum
            && session.discardSelection.size <= requirement.maximum
        );
        const confirm = $('story-coop-combat-play-selected');
        confirm?.classList.toggle('hidden', !inCombat || !pendingCard);
        if (confirm) confirm.disabled = !canAct || !selectionValid;
        const ready = $('story-coop-combat-ready');
        if (ready) {
            ready.classList.toggle('hidden', !inCombat);
            ready.disabled = !canAct || Boolean(pendingCard);
            ready.textContent = viewer?.ready ? '等待队友...' : '本回合准备完毕';
        }
        const refresh = $('story-coop-combat-refresh');
        if (refresh) refresh.disabled = Boolean(session.loadPromise || session.actionPromise);

        if (session.notice) {
            storyCoopCombatSetStatus(session.notice.message, session.notice.tone);
        } else if (session.compatible === false) {
            storyCoopCombatSetStatus('此协作存档的内容版本与当前服务器不兼容。', 'error');
        } else if (!run || !snapshot) {
            storyCoopCombatSetStatus('正在读取协作旅程...', 'busy');
        } else if (session.actionPromise) {
            storyCoopCombatSetStatus('正在提交权威动作...', 'busy');
        } else if (inSetup && !storyCoopSetupViewerIsLeader(session)) {
            storyCoopCombatSetStatus('正在等待队长选择花园难度。', 'busy');
        } else if (inSetup) {
            storyCoopCombatSetStatus('请选择普通、困难或疯狂难度。简单难度尚未接入协作故事。', 'success');
        } else if (inOpening && snapshot.room_state.status === 'resolved') {
            storyCoopCombatSetStatus(
                `你已选择开局赐福，正在等待${storyCoopWaitingMessage(snapshot, snapshot.room_state.seats, 'resolved')}。`,
                'busy',
            );
        } else if (inOpening) {
            storyCoopCombatSetStatus('请选择一项只属于你的开局赐福。', 'success');
        } else if (complete) {
            storyCoopCombatSetStatus('协作完整旅程已完成，双方通关进度已分别结算。', 'success');
        } else if (stageComplete) {
            if (snapshot.room_state?.status === 'resolved') {
                storyCoopCombatSetStatus(
                    `你已确认，正在等待${storyCoopWaitingMessage(snapshot, snapshot.room_state?.seats, 'resolved')}。`,
                    'busy',
                );
            } else {
                storyCoopCombatSetStatus(
                    Number(snapshot?.stage) >= 3
                        ? '请确认最终结算；双方确认后才会记录完整通关。'
                        : '请确认继续；双方确认后进入下一阶段并分别选择新赐福。',
                    'success',
                );
            }
        } else if (failed) {
            storyCoopCombatSetStatus('全队已经倒下，本次协作旅程结束。', 'error');
        } else if (inReward && snapshot.reward.status === 'resolved') {
            storyCoopCombatSetStatus(
                `你已完成奖励选择，正在等待${storyCoopWaitingMessage(snapshot, snapshot.reward.seats, 'resolved')}。`,
                'busy',
            );
        } else if (inReward) {
            const pendingParts = [
                snapshot.reward.card_status === 'pending' ? '选择1张卡牌或跳过' : '',
                snapshot.reward.book_status === 'pending' ? '收下或放弃附魔书' : '',
            ].filter(Boolean);
            storyCoopCombatSetStatus(
                `已获得${Number(snapshot.reward.gold) || 0}金币；请${pendingParts.join('，并')}。`,
                'success',
            );
        } else if (onMap && snapshot.map_vote.viewer_node_id) {
            storyCoopCombatSetStatus(
                `你已提交路线投票，正在等待${storyCoopWaitingMessage(snapshot, snapshot.map_vote.seats, 'submitted')}。`,
                'busy',
            );
        } else if (onMap) {
            storyCoopCombatSetStatus('请选择你希望进入的下一个路线节点。', 'success');
        } else if (inRest && snapshot.room_state.status === 'resolved') {
            storyCoopCombatSetStatus(
                `你已完成休息选择，正在等待${storyCoopWaitingMessage(snapshot, snapshot.room_state.seats, 'resolved')}。`,
                'busy',
            );
        } else if (inRest && session.selectedRestCardId) {
            storyCoopCombatSetStatus('已选择1张未升级卡牌；确认后将由服务器执行升级。', 'busy');
        } else if (inRest) {
            storyCoopCombatSetStatus('请选择恢复、升级1张自己的卡牌，或直接离开。', 'success');
        } else if (inChest && snapshot.room_state.status === 'resolved') {
            storyCoopCombatSetStatus(
                `你已处理个人宝箱，正在等待${storyCoopWaitingMessage(snapshot, snapshot.room_state.seats, 'resolved')}。`,
                'busy',
            );
        } else if (inChest) {
            storyCoopCombatSetStatus('请选择领取你的宝箱金币，或放弃并离开。', 'success');
        } else if (inShop && snapshot.room_state.status === 'resolved') {
            storyCoopCombatSetStatus(
                `你已离开个人商店，正在等待${storyCoopWaitingMessage(snapshot, snapshot.room_state.seats, 'resolved')}。`,
                'busy',
            );
        } else if (inShop) {
            storyCoopCombatSetStatus('你可以连续购买自己的商品；完成后请选择离开商店。', 'success');
        } else if (inEvent && snapshot.room_state.status === 'resolved') {
            storyCoopCombatSetStatus(
                `你已提交事件选择，正在等待${storyCoopWaitingMessage(snapshot, snapshot.room_state.seats, 'submitted')}；双方选项在决议前保持隐藏。`,
                'busy',
            );
        } else if (inEvent && lastEventType === 'coop_event_consensus_required') {
            storyCoopCombatSetStatus('双方选择不一致：本轮没有产生任何效果，请沟通后重新选择同一方案。', 'error');
        } else if (inEvent) {
            storyCoopCombatSetStatus('请选择一项团队事件方案；这里只显示队友是否已提交。', 'success');
        } else if (inCombat && pendingCard) {
            storyCoopCombatSetStatus(
                `请选择${requirement.minimum === requirement.maximum ? requirement.minimum : `至多${requirement.maximum}`}张其他手牌作为主动丢弃，然后确认。`,
                'busy',
            );
        } else if (inCombat && viewer?.ready) {
            const waiting = (snapshot.players || [])
                .filter((player) => !player?.down && !player?.ready)
                .map((player) => storyCoopCombatMemberName(snapshot, player?.seat));
            storyCoopCombatSetStatus(`你已结束本回合，正在等待${waiting.join('、') || '其他存活成员'}。`, 'busy');
        } else if (inCombat) {
            storyCoopCombatSetStatus('战斗状态已同步。你可以出牌或结束本回合。', 'success');
        } else {
            storyCoopCombatSetStatus('正在同步协作旅程阶段...', 'busy');
        }
    }

    function scheduleStoryCoopCombatPolling(session = storyCoopCombatSession) {
        stopStoryCoopCombatPolling(session);
        if (
            !session
            || session !== storyCoopCombatSession
            || !storyCoopCombatDialogOpen()
            || session.loadPromise
            || session.actionPromise
            || ['complete', 'game_over'].includes(String(storyCoopCombatSnapshot(session)?.phase || ''))
            || String(session.run?.status || '') !== 'active'
        ) return;
        session.pollTimer = setTimeout(() => {
            session.pollTimer = 0;
            loadStoryCoopCombat({ silent: true }).catch(() => {});
        }, STORY_COOP_COMBAT_POLL_MS);
    }

    function loadStoryCoopCombat({ silent = false } = {}) {
        const session = storyCoopCombatSession;
        if (!session || !storyCoopCombatDialogOpen()) return Promise.resolve(null);
        if (session.loadPromise) return session.loadPromise;
        stopStoryCoopCombatPolling(session);
        const epoch = session.epoch;
        let loadPromise;
        loadPromise = (async () => {
            try {
                const payload = await requestJson(
                    `/api/story/coop/run/${encodeURIComponent(session.runId)}`,
                );
                if (session !== storyCoopCombatSession || session.epoch !== epoch) return payload;
                if (!session.notice?.sticky || !silent) {
                    session.notice = silent
                        ? null
                        : { message: '协作战斗状态已刷新。', tone: 'success', sticky: false };
                }
                storyCoopCombatApplyRun(session, payload.run, payload.compatible !== false);
                return payload;
            } catch (error) {
                if (session === storyCoopCombatSession && session.epoch === epoch) {
                    session.notice = {
                        message: silent
                            ? `${storyCoopErrorMessage(error)}；战斗界面会继续重试。`
                            : storyCoopErrorMessage(error),
                        tone: 'error',
                        sticky: false,
                    };
                }
                throw error;
            } finally {
                if (session === storyCoopCombatSession && session.loadPromise === loadPromise) {
                    session.loadPromise = null;
                    renderStoryCoopCombat();
                    scheduleStoryCoopCombatPolling(session);
                }
            }
        })();
        session.loadPromise = loadPromise;
        renderStoryCoopCombat();
        return loadPromise;
    }

    async function storyCoopCombatAction(actionType, payload = {}) {
        const session = storyCoopCombatSession;
        const run = session?.run;
        const snapshot = storyCoopCombatSnapshot(session);
        const combat = snapshot?.combat;
        const normalizedType = String(actionType || '');
        const combatAction = [
            'play_card', 'combat_ready', 'use_enchantment_book',
            'discard_combat_enchantment_book',
        ].includes(normalizedType);
        const allowed = combatAction
            ? storyCoopCombatCanAct(session)
            : (
                normalizedType === 'discard_enchantment_book'
                    ? Boolean(storyCoopRunCanSubmit(session) && snapshot?.phase !== 'combat')
                    : normalizedType === 'setup_start'
                    ? storyCoopSetupCanChoose(session)
                    : (
                        normalizedType === 'opening_choose'
                            ? storyCoopOpeningCanChoose(session)
                            : (
                                normalizedType === 'reward_choose'
                                    ? storyCoopRewardCanChoose(session)
                                    : (
                                        normalizedType === 'map_vote'
                                            ? storyCoopMapCanVote(session)
                                            : (
                                                normalizedType === 'room_choose'
                                                    ? storyCoopRoomCanChoose(session)
                                                    : (
                                                        normalizedType === 'shop_buy'
                                                            ? storyCoopShopCanBuy(session)
                                                            : (normalizedType === 'stage_ready' && storyCoopStageCanReady(session))
                                                    )
                                            )
                                    )
                            )
                    )
            );
        if (!session || !run || session.actionPromise || !allowed) return null;
        const epoch = session.epoch;
        const body = {
            party_id: session.partyId,
            run_id: session.runId,
            run_revision: Number(run.revision),
            action_id: storyCoopCombatActionId(),
            action_type: normalizedType,
            expected_sequence: Number(snapshot.action_sequence || 0),
            payload: cloneStoryCoopActionPayload(payload),
        };
        if (combatAction) {
            body.combat_id = String(combat?.id || '');
            body.combat_round = Number(combat?.round);
        }
        session.notice = null;
        stopStoryCoopCombatPolling(session);
        let actionPromise;
        actionPromise = (async () => {
            let lastError = null;
            for (let attempt = 0; attempt < 2; attempt += 1) {
                try {
                    return await requestJson(
                        `/api/story/coop/run/${encodeURIComponent(session.runId)}/action`,
                        { method: 'POST', body: JSON.stringify(body) },
                    );
                } catch (error) {
                    lastError = error;
                    const status = Number(error?.status);
                    const retryable = !Number.isFinite(status)
                        || [408, 502, 503, 504].includes(status);
                    if (!retryable || attempt > 0) throw error;
                    if (
                        session !== storyCoopCombatSession
                        || session.epoch !== epoch
                        || !storyCoopCombatDialogOpen()
                    ) throw error;
                    await storySleep(350);
                    if (
                        session !== storyCoopCombatSession
                        || session.epoch !== epoch
                        || !storyCoopCombatDialogOpen()
                    ) throw error;
                }
            }
            throw lastError;
        })();
        session.actionPromise = actionPromise;
        renderStoryCoopCombat();
        try {
            const result = await actionPromise;
            if (session !== storyCoopCombatSession || session.epoch !== epoch) return result;
            session.notice = null;
            await playStoryCoopActionPresentation(result.events, body, snapshot);
            if (session !== storyCoopCombatSession || session.epoch !== epoch) return result;
            storyCoopCombatApplyRun(session, result.run, true);
            session.pendingCardId = '';
            session.discardSelection.clear();
            return result;
        } catch (error) {
            if (session === storyCoopCombatSession && session.epoch === epoch) {
                if (error?.payload?.run) {
                    storyCoopCombatApplyRun(
                        session,
                        error.payload.run,
                        String(error?.payload?.code || '') !== 'COOP_CONTENT_VERSION_OLD',
                    );
                }
                session.notice = {
                    message: storyCoopErrorMessage(error),
                    tone: 'error',
                    sticky: true,
                    runRevision: Number(session.run?.revision || 0),
                    phase: String(storyCoopCombatSnapshot(session)?.phase || ''),
                };
            }
            return null;
        } finally {
            if (session === storyCoopCombatSession && session.actionPromise === actionPromise) {
                session.actionPromise = null;
                renderStoryCoopCombat();
                scheduleStoryCoopCombatPolling(session);
            }
        }
    }

    function addStoryCoopRetrieveSelections(card, viewer, payload) {
        if (!card?.modifiers?.enchantment_retrieve_once) return true;
        const drawChoices = Array.isArray(viewer?.rapids_draw_choices)
            ? viewer.rapids_draw_choices
            : [];
        const discardChoices = Array.isArray(viewer?.discard_pile)
            ? viewer.discard_pile
            : [];
        if (drawChoices.length) {
            const selected = chooseStoryCoopCards(drawChoices, { label: '抽牌堆卡牌' });
            if (!selected) return false;
            payload.retrieve_draw_card_id = String(selected[0]?.instance_id || '');
        }
        if (discardChoices.length) {
            const selected = chooseStoryCoopCards(discardChoices, { label: '弃牌堆卡牌' });
            if (!selected) return false;
            payload.retrieve_discard_card_id = String(selected[0]?.instance_id || '');
        }
        return true;
    }

    function selectStoryCoopCombatCard(instanceId) {
        const session = storyCoopCombatSession;
        const viewer = storyCoopCombatViewer(session);
        if (!session || !storyCoopCombatCanAct(session)) return;
        const card = (viewer?.hand || []).find(
            (item) => String(item?.instance_id || '') === String(instanceId || ''),
        );
        if (!card) return;
        if (session.pendingCardId) {
            if (String(instanceId) === session.pendingCardId) {
                session.pendingCardId = '';
                session.discardSelection.clear();
            } else {
                const requirement = storyCoopCombatDiscardRequirement(
                    (viewer.hand || []).find((item) => String(item?.instance_id || '') === session.pendingCardId),
                );
                if (session.discardSelection.has(String(instanceId))) {
                    session.discardSelection.delete(String(instanceId));
                } else if (session.discardSelection.size < requirement.maximum) {
                    session.discardSelection.add(String(instanceId));
                }
            }
            renderStoryCoopCombat();
            return;
        }
        const requirement = storyCoopCombatDiscardRequirement(card);
        if (requirement.maximum > 0) {
            session.pendingCardId = String(instanceId);
            session.discardSelection.clear();
            renderStoryCoopCombat();
            return;
        }
        const payload = { card_instance_id: String(instanceId) };
        if (storyCoopCombatCardNeedsEnemy(card)) {
            if (!session.selectedEnemyId) {
                storyCoopCombatSetStatus('请先选择一个存活敌人。', 'error');
                return;
            }
            payload.target_enemy_id = session.selectedEnemyId;
        }
        if (!addStoryCoopRetrieveSelections(card, viewer, payload)) return;
        storyCoopCombatAction('play_card', payload);
    }

    function confirmStoryCoopCombatCard() {
        const session = storyCoopCombatSession;
        const viewer = storyCoopCombatViewer(session);
        const card = (viewer?.hand || []).find(
            (item) => String(item?.instance_id || '') === session?.pendingCardId,
        );
        if (!session || !card || !storyCoopCombatCanAct(session)) return;
        const requirement = storyCoopCombatDiscardRequirement(card);
        if (
            session.discardSelection.size < requirement.minimum
            || session.discardSelection.size > requirement.maximum
        ) return;
        const payload = {
            card_instance_id: session.pendingCardId,
            discard_card_instance_ids: [...session.discardSelection],
        };
        if (storyCoopCombatCardNeedsEnemy(card)) {
            if (!session.selectedEnemyId) {
                storyCoopCombatSetStatus('请先选择一个存活敌人。', 'error');
                return;
            }
            payload.target_enemy_id = session.selectedEnemyId;
        }
        if (!addStoryCoopRetrieveSelections(card, viewer, payload)) return;
        storyCoopCombatAction('play_card', payload);
    }

    function readyStoryCoopCombatSeat() {
        storyCoopCombatAction('combat_ready', {});
    }

    function readyStoryCoopStage() {
        const roomState = storyCoopCombatSnapshot(storyCoopCombatSession)?.room_state;
        if (!storyCoopStageCanReady(storyCoopCombatSession)) return;
        storyCoopCombatAction('stage_ready', {
            room_id: String(roomState?.room_id || ''),
        });
    }

    function confirmStoryCoopRestUpgrade() {
        const session = storyCoopCombatSession;
        const roomState = storyCoopRestRoomState(session);
        if (!session || !roomState || !storyCoopRestCanChoose(session)) return;
        if (!storyCoopRestOptionSet(roomState).has('upgrade')) return;
        const card = (Array.isArray(roomState.deck) ? roomState.deck : []).find(
            (item) => (
                String(item?.instance_id || '') === session.selectedRestCardId
                && !item?.upgraded
                && Number(item?.upgrade_level || 0) <= 0
            ),
        );
        if (!card) return;
        storyCoopCombatAction('room_choose', {
            room_id: String(roomState.room_id || ''),
            choice: 'upgrade',
            card_instance_id: String(card.instance_id || ''),
        });
    }

    function leaveStoryCoopShop() {
        chooseStoryCoopRoomOption(storyCoopCombatSession, 'shop', 'leave');
    }

    function openStoryCoopCombat() {
        if (!window.__STORY_COOP_ACCESS__) return;
        const party = storyCoopPartyBundle.party;
        const run = storyCoopPartyBundle.run;
        if (!party || !run || String(party.status || '') !== 'active') {
            storyCoopSetStatus('当前没有可进入的协作旅程。', 'error');
            return;
        }
        const partyId = String(party.id || '');
        const runId = String(run.id || '');
        const lobby = $('story-coop-preview-dialog');
        if (lobby?.open) lobby.close();
        const dialog = $('story-coop-combat-dialog');
        if (!dialog) return;
        storyCoopCombatEpoch += 1;
        const session = {
            epoch: storyCoopCombatEpoch,
            partyId,
            runId,
            run: null,
            compatible: true,
            selectedEnemyId: '',
            pendingCardId: '',
            discardSelection: new Set(),
            selectedRestCardId: '',
            pollTimer: 0,
            loadPromise: null,
            actionPromise: null,
            notice: null,
        };
        storyCoopCombatSession = session;
        storyCoopCombatSetStatus('正在同步协作战斗状态...', 'busy');
        if (!dialog.open) dialog.showModal();
        storyCoopCombatApplyRun(session, run, true);
        loadStoryCoopCombat().catch(() => {});
    }

    function closeStoryCoopCombat() {
        const dialog = $('story-coop-combat-dialog');
        if (dialog?.open) dialog.close();
    }

    function handleStoryCoopCombatClosed() {
        const session = storyCoopCombatSession;
        if (session) stopStoryCoopCombatPolling(session);
        storyCoopCombatEpoch += 1;
        storyCoopCombatSession = null;
        clearStorySeededBackdrop($('story-coop-seeded-backdrop'));
        setTimeout(() => {
            if (!storyCoopCombatDialogOpen()) openCooperativeStoryPreview();
        }, 0);
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
        const button = $('story-hud-surrender');
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
        common: '#7EEF6D',
        unusual: '#FFE65D',
        rare: '#4D52E3',
        epic: '#861FDE',
        legendary: '#DE1F1F',
        mythic: '#1FDBDE',
        ultra: '#FF2B75',
        super: '#2BFFA3',
        omega: '#F329D9',
        eternal: '#EEEEEE',
        unique: '#555555',
        milestone: '#5AA469',
        hidden: '#7257A8',
        neutral: 'var(--text-secondary)',
        spectator: 'var(--text-muted)',
    });

    function storyChatColorCss(value) {
        const raw = String(value || '').trim();
        const key = raw.toLowerCase();
        if (STORY_CHAT_TITLE_COLORS[key]) return STORY_CHAT_TITLE_COLORS[key];
        if (/^#[0-9a-f]{6}(?:[0-9a-f]{2})?$/i.test(raw)) return raw;
        if (
            globalThis.CSS?.supports?.('color', raw)
            && /^(?:rgb|hsl)a?\([^;{}]+\)$/i.test(raw)
        ) {
            return raw;
        }
        return '';
    }

    function normalizeStoryTitlePaint(paint, fallbackColor = 'neutral') {
        if (!paint || typeof paint !== 'object') {
            return {
                kind: 'solid',
                color: storyChatColorCss(paint || fallbackColor)
                    || storyChatColorCss(fallbackColor),
            };
        }
        const kind = String(paint.kind || '').toLowerCase();
        if (kind === 'solid') {
            return {
                kind,
                color: storyChatColorCss(paint.color) || storyChatColorCss(fallbackColor),
            };
        }
        if (kind === 'gradient' || kind === 'rainbow') {
            const colors = (Array.isArray(paint.colors) ? paint.colors : [])
                .map(storyChatColorCss)
                .filter(Boolean)
                .slice(0, 12);
            if (colors.length < 2) {
                return { kind: 'solid', color: storyChatColorCss(fallbackColor) };
            }
            const numericAngle = Number(paint.angle);
            const angle = Number.isFinite(numericAngle)
                ? ((numericAngle % 360) + 360) % 360
                : 90;
            return { kind, colors, angle };
        }
        if (kind === 'theme') {
            return {
                kind,
                light: normalizeStoryTitlePaint(paint.light, fallbackColor),
                dark: normalizeStoryTitlePaint(paint.dark, fallbackColor),
            };
        }
        return { kind: 'solid', color: storyChatColorCss(fallbackColor) };
    }

    function applyStoryTitlePaint(element, rawPaint) {
        if (!element) return;
        const paint = normalizeStoryTitlePaint(rawPaint);
        element.classList.remove('title-paint-solid', 'title-paint-gradient', 'title-paint-theme');
        element.style.removeProperty('color');
        element.style.removeProperty('background-image');
        element.style.removeProperty('background-clip');
        element.style.removeProperty('-webkit-background-clip');
        element.style.removeProperty('-webkit-text-fill-color');
        element.style.removeProperty('--title-paint-gradient');
        element.style.removeProperty('--title-paint-light');
        element.style.removeProperty('--title-paint-dark');
        if (paint.kind === 'gradient' || paint.kind === 'rainbow') {
            element.classList.add('title-paint-gradient');
            element.style.setProperty(
                '--title-paint-gradient',
                `linear-gradient(${paint.angle}deg,${paint.colors.join(',')})`,
            );
            return;
        }
        if (paint.kind === 'theme') {
            element.classList.add('title-paint-theme');
            element.style.setProperty(
                '--title-paint-light',
                paint.light?.color || storyChatColorCss('neutral'),
            );
            element.style.setProperty(
                '--title-paint-dark',
                paint.dark?.color || storyChatColorCss('neutral'),
            );
            return;
        }
        element.classList.add('title-paint-solid');
        element.style.color = paint.color || storyChatColorCss('neutral');
        element.style.backgroundImage = 'none';
        element.style.webkitTextFillColor = 'currentColor';
    }

    function storyTitleSegments(title = {}) {
        const rawSegments = title?.style?.segments;
        if (Array.isArray(rawSegments) && rawSegments.some((item) => item && item.text != null)) {
            return rawSegments.slice(0, 24).map((item, index) => ({
                id: String(item.id || `s${index + 1}`),
                text: String(item.text || ''),
                paint: normalizeStoryTitlePaint(item.paint, title.color || 'neutral'),
            }));
        }
        return [{
            id: 'legacy',
            text: String(title.name || ''),
            paint: normalizeStoryTitlePaint(
                { kind: 'solid', color: title.color || 'neutral' },
            ),
        }];
    }

    function appendStoryStyledTitle(
        parent,
        title,
        bracketed = true,
        className = 'story-chat-player-title',
    ) {
        const segments = storyTitleSegments(title);
        segments.forEach((segment, index) => {
            const element = document.createElement('span');
            element.className = `${className} player-title-inline title-style-segment`;
            element.dataset.titleSegment = segment.id;
            element.textContent = `${bracketed && index === 0 ? '[' : ''}${segment.text}${bracketed && index === segments.length - 1 ? ']' : ''}`;
            applyStoryTitlePaint(element, segment.paint);
            parent.appendChild(element);
        });
    }

    function storyEquippedTitles(identity = {}) {
        return Array.isArray(identity.equipped_titles)
            ? identity.equipped_titles.filter((item) => item?.name).slice(0, 3)
            : [];
    }

    function storyPlayerNamePaint(identity = {}) {
        if (identity?.name_style?.paint) {
            return normalizeStoryTitlePaint(identity.name_style.paint);
        }
        if (identity?.name_color) {
            return normalizeStoryTitlePaint({ kind: 'solid', color: identity.name_color });
        }
        return null;
    }

    function renderStoryPlayerIdentity() {
        const container = $('story-player-name');
        if (!container) return;
        const account = window.__STORY_ACCOUNT__ || {};
        container.replaceChildren();
        storyEquippedTitles(account).forEach((title) => {
            appendStoryStyledTitle(container, title, true, 'story-player-title');
        });
        const name = document.createElement('span');
        name.className = 'player-name-value story-player-name-value';
        name.textContent = String(account.display_name || account.username || '?');
        const paint = storyPlayerNamePaint(account);
        if (paint) applyStoryTitlePaint(name, paint);
        container.appendChild(name);
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

        const titles = storyEquippedTitles(entry);
        titles.forEach((title) => {
            appendStoryStyledTitle(parent, title);
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
        let namePaint = storyPlayerNamePaint(entry);
        if (!namePaint && entry.special_role_color) {
            namePaint = normalizeStoryTitlePaint({
                kind: 'solid',
                color: entry.special_role_color,
            });
        }
        if (namePaint) applyStoryTitlePaint(name, namePaint);
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
        element.style.animationDuration = `${Math.max(1, duration / storyPlaybackRate)}ms`;
        return new Promise((resolve) => {
            let finished = false;
            let fallbackTimer = 0;
            const complete = () => {
                if (finished) return;
                finished = true;
                window.clearTimeout(fallbackTimer);
                element.removeEventListener('animationend', complete);
                element.classList.remove(className);
                element.style.removeProperty('animation-duration');
                resolve();
            };
            element.addEventListener('animationend', complete, { once: true });
            fallbackTimer = window.setTimeout(complete, duration / storyPlaybackRate + 80);
        });
    }

    function storySleep(duration) {
        return new Promise((resolve) => window.setTimeout(
            resolve,
            Math.max(0, Number(duration) || 0) / storyPlaybackRate,
        ));
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

    function storyCardMotionTarget(event) {
        const targetIds = Array.isArray(event?.target_ids) ? event.target_ids : [];
        const targetId = String(targetIds[0] || event?.target_id || '');
        if (targetId === 'player') return $('story-player-target');
        if (targetId) return storyEnemyActor(targetId);
        return $('story-enemy-group') || $('story-combat-stage');
    }

    function storyCardFlightDimensions(sourceRect) {
        const defaultAspect = .72;
        const measuredAspect = Number(sourceRect?.width) / Number(sourceRect?.height);
        const sourceLooksLikeCard = Number.isFinite(measuredAspect)
            && measuredAspect >= .54
            && measuredAspect <= .86;
        const aspect = sourceLooksLikeCard ? measuredAspect : defaultAspect;
        let width = sourceLooksLikeCard
            ? Math.max(42, Math.min(132, Number(sourceRect.width) || 84))
            : 84;
        let height = width / aspect;
        if (height > 184) {
            height = 184;
            width = height * aspect;
        } else if (height < 58) {
            height = 58;
            width = height * aspect;
        }
        return { width, height, aspect };
    }

    // Solo and cooperative story presentations deliberately share this path.
    // A non-card source (for example a teammate rail) receives a normal card
    // silhouette instead of inheriting the source element's flattened ratio.
    async function animateStoryCardFlight(
        source,
        target,
        mode = 'play',
        count = 0,
        useSourceVisual = true,
    ) {
        if (!target) return;
        const sourceRect = source?.getBoundingClientRect()
            || $('story-player-target')?.getBoundingClientRect();
        const targetRect = target.getBoundingClientRect();
        if (!sourceRect) return;
        const dimensions = storyCardFlightDimensions(sourceRect);
        const sourceCenterX = sourceRect.left + sourceRect.width / 2;
        const sourceCenterY = sourceRect.top + sourceRect.height / 2;
        const targetCenterX = targetRect.left + targetRect.width / 2;
        const targetCenterY = targetRect.top + targetRect.height / 2;
        const ghost = useSourceVisual && source
            ? source.cloneNode(true)
            : document.createElement('span');
        ghost.classList.add('story-card-flight', `is-${mode}`);
        if (!useSourceVisual || !source) ghost.classList.add('story-pile-motion-back');
        if (Number(count) > 1) ghost.dataset.count = String(count);
        ghost.style.left = `${sourceCenterX - dimensions.width / 2}px`;
        ghost.style.top = `${sourceCenterY - dimensions.height / 2}px`;
        ghost.style.width = `${dimensions.width}px`;
        ghost.style.height = `${dimensions.height}px`;
        ghost.style.setProperty('--story-card-flight-aspect', String(dimensions.aspect));
        ghost.style.setProperty(
            '--story-card-flight-x',
            `${targetCenterX - sourceCenterX}px`,
        );
        ghost.style.setProperty(
            '--story-card-flight-y',
            `${targetCenterY - sourceCenterY}px`,
        );
        document.body.append(ghost);
        await waitForStoryAnimation(ghost, 'is-flying', 380);
        ghost.remove();
    }

    async function animateStoryCardPlayed(event) {
        const instanceId = String(event?.card_instance_id || event?.source_card_instance_id || '');
        const source = instanceId
            ? document.querySelector(
                `.story-hand-card[data-instance-id="${CSS.escape(instanceId)}"] .story-card`,
            )
            : null;
        await animateStoryCardFlight(source, storyCardMotionTarget(event), 'play');
    }

    async function animateStoryCardInserted(event) {
        const destination = String(event?.destination || 'hand');
        const target = destination === 'draw_pile'
            ? $('story-draw-pile')
            : destination === 'discard_pile'
                ? $('story-discard-pile')
                : destination === 'exile_pile'
                    ? $('story-exile-pile')
                    : $('story-hand');
        const actorId = String(event?.actor_id || 'player');
        const source = actorId === 'player'
            ? $('story-player-target')
            : storyEnemyActor(actorId);
        await animateStoryCardFlight(source, target, 'insert', event?.count, false);
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
            await settleAllStoryMechanicalTrackActivations();
            if (event?.track_card || event?.source_card_instance_id) {
                await animateStoryMechanicalTrackActivation(event);
            }
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
            const lethal = event?.lethal === true || (
                Number.isFinite(Number(event?.before))
                && Number(event.before) > 0
                && Number.isFinite(Number(event?.after))
                && Number(event.after) <= 0
            );
            if (lethal) {
                updateAnimatedEnemyHealth(event, nextRun);
                return;
            }
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
        } else if (eventType === 'card_played') {
            await animateStoryCardPlayed(event);
        } else if (eventType === 'draw') {
            await animateStoryDraw(event);
        } else if (eventType === 'card_discarded') {
            await animateStoryPileMove(event, 'discard');
        } else if (eventType === 'card_exiled') {
            await animateStoryPileMove(event, 'exile');
        } else if (['card_created', 'cards_created', 'enemy_card_added'].includes(eventType)) {
            await animateStoryCardInserted(event);
        } else if (eventType === 'equipment_added') {
            spawnStoryFloat($('story-player-target'), localize(storyContent?.cards?.[event.def_id]?.name), 'equipment');
        } else if (eventType === 'mechanical_track_captured') {
            addStoryMechanicalTrackEventCard(event, 'start');
        } else if (eventType === 'mechanical_track_card_created') {
            addStoryMechanicalTrackEventCard(event);
        } else if (eventType === 'mechanical_track_recycled') {
            await settleStoryMechanicalTrackActivation(event.enemy_id);
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
            await settleAllStoryMechanicalTrackActivations();
            delete document.body.dataset.enemyAnimating;
        }
    }

    async function storyAction(actionType, payload = {}) {
        if (!activeRun || actionInFlight) return null;
        actionInFlight = true;
        document.body.dataset.actionInFlight = 'true';
        updateStoryManualSaveControls();
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
            renderStoryPersistentHud(activeRun);
            updateStoryManualSaveControls();
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

    function storyMapFloorBounds(map) {
        const floorNumbers = (map?.floors || [])
            .flatMap((floor) => (floor?.nodes || []).map((node) => Number(node?.floor)))
            .filter(Number.isFinite);
        if (!floorNumbers.length) return { minimum: 1, span: 15 };
        const minimum = Math.min(...floorNumbers);
        const maximum = Math.max(...floorNumbers);
        return {
            minimum,
            span: Math.max(1, maximum - minimum),
        };
    }

    function mapPoint(node, floorBounds = { minimum: 1, span: 15 }) {
        const width = 760;
        const height = 1040;
        const horizontalPadding = 56;
        const verticalPadding = 48;
        const normalizedFloor = (Number(node.floor) - floorBounds.minimum) / floorBounds.span;
        return {
            x: horizontalPadding + node.x * (width - horizontalPadding * 2),
            y: height - verticalPadding - normalizedFloor * (height - verticalPadding * 2),
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
        const floorBounds = storyMapFloorBounds(map);
        const nodes = new Map();
        map.floors.forEach((floor) => floor.nodes.forEach((node) => nodes.set(node.id, node)));
        const edgeGroup = svgElement('g', { 'aria-hidden': 'true' });
        (map.edges || []).forEach((edge) => {
            const from = nodes.get(edge.from);
            const to = nodes.get(edge.to);
            if (!from || !to) return;
            const start = mapPoint(from, floorBounds);
            const end = mapPoint(to, floorBounds);
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
            const point = mapPoint(node, floorBounds);
            const actionable = !options.readOnly && node.status === 'available';
            const routeCurrent = String(node.id) === String(currentNodeId);
            const bossDefinition = node.type === 'boss'
                ? storyContent?.enemies?.[String(node.boss_def_id || '')]
                : null;
            const bossName = localize(bossDefinition?.name);
            const bossImageUrl = String(bossDefinition?.image_url || '').trim();
            const roomIconUrl = String(STORY_MAP_ROOM_ICON_URLS[node.type] || '').trim();
            const roomLabel = [
                t.floor(node.floor),
                t.rooms[node.type] || node.type,
                bossName,
            ].filter(Boolean).join(' · ');
            const group = svgElement('g', {
                class: `story-map-node${actionable ? ' is-actionable' : ''}${routeCurrent ? ' is-route-current' : ''}`,
                transform: `translate(${point.x} ${point.y})`,
                'data-room-type': node.type,
                'data-status': node.status || 'locked',
                role: actionable ? 'button' : 'img',
                tabindex: actionable ? '0' : '-1',
                'aria-label': roomLabel,
            });
            const title = svgElement('title');
            title.textContent = roomLabel;
            group.append(title);
            if (!roomIconUrl) {
                group.append(svgElement('circle', {
                    cx: 0,
                    cy: 0,
                    r: STORY_MAP_NODE_RADIUS,
                }));
            }
            const nodeImageUrl = bossImageUrl || roomIconUrl;
            if (nodeImageUrl) {
                const nodeImageSize = bossImageUrl ? 40 : STORY_MAP_NODE_RADIUS * 2;
                group.append(svgElement('image', {
                    class: bossImageUrl ? 'story-map-boss-icon' : 'story-map-room-icon',
                    href: nodeImageUrl,
                    x: -nodeImageSize / 2,
                    y: -nodeImageSize / 2,
                    width: nodeImageSize,
                    height: nodeImageSize,
                    preserveAspectRatio: 'xMidYMid meet',
                    'aria-hidden': 'true',
                }));
                if (actionable) {
                    group.append(svgElement('circle', {
                        class: 'story-map-node-hitbox',
                        cx: 0,
                        cy: 0,
                        r: STORY_MAP_NODE_RADIUS,
                        'aria-hidden': 'true',
                    }));
                }
            } else {
                const text = svgElement('text', { x: 0, y: 1 });
                text.textContent = t.roomMarks[node.type] || '?';
                group.append(text);
            }
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
            const targetY = mapPoint(focusNode, floorBounds).y * scale;
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
            const damage = 14 + 5 * upgradeLevel;
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
        boostEffects(['shield'], Number(modifiers.enchantment_shield_bonus_once || 0));
        if (values.rarity === 'primary' && Number(modifiers.primary_multiplier || 0) > 1) {
            const multiplier = Math.max(
                1,
                Number(storyContent?.relics?.return_to_origin?.amount || 1),
            );
            values.effects = values.effects.map((effect) => (
                ['damage', 'shield'].includes(String(effect.type || ''))
                    ? { ...effect, amount: Math.max(0, Math.floor(Number(effect.amount || 0) * multiplier)) }
                    : effect
            ));
        }
        const tags = new Set(Array.isArray(values.tags) ? values.tags : []);
        if (modifiers.remove_exile) {
            tags.delete('exile');
            tags.delete('void');
        }
        if (modifiers.force_exile) tags.add('exile');
        if (modifiers.force_void) tags.add('void');
        if (modifiers.retain) tags.add('retain');
        (modifiers.extra_tags || []).forEach((tag) => tags.add(String(tag)));
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
            openStoryCardTermsFromElement(chip);
        });
        chip.addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            if ($('story-codex-dialog')?.open && storyCodexTargetIsDiscovered('cards', cardId)) {
                closeStoryCardTerms();
                navigateStoryCodex('cards', cardId, { push: true });
                return;
            }
            openStoryCardTermsFromElement(chip);
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
        const minimumReadableScale = 0.76;
        const minimumSpacingScale = 0.9;
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
            const minimumScale = !overflowed && !predictionTooTall
                ? minimumSpacingScale
                : minimumReadableScale;
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
        if (
            targetKind === 'enemy'
            && !storyCursorCardMode(card)
            && !storyEnemyIsSelectable(card, targetId, state)
        ) return;
        cardPlayInFlight = true;
        updateStoryManualSaveControls();
        destroyStoryCursorCard();
        selectedCombatCardId = '';
        try {
            await storyAction('play_card', {
                card_instance_id: card.instance_id,
                ...(targetId ? { target_id: targetId } : {}),
                ...extraPayload,
            });
        } finally {
            cardPlayInFlight = false;
            renderStoryPersistentHud(activeRun);
            updateStoryManualSaveControls();
        }
    }

    function playSelectedCombatCard(targetKind, targetId = '') {
        if (cardPlayInFlight || actionInFlight || !activeRun) return;
        const card = selectedCombatCard(activeRun.state);
        if (!card || cardTargetKind(card) !== targetKind) return;
        if (
            targetKind === 'enemy'
            && !storyCursorCardMode(card)
            && !storyEnemyIsSelectable(card, targetId, activeRun.state)
        ) return;
        if (openCardSelection(card, targetKind, targetId)) return;
        performSelectedCombatCard(targetKind, targetId);
    }

    function storyPileCardIdentity(card) {
        if (!card || typeof card !== 'object') return '';
        const normalize = (value) => {
            if (Array.isArray(value)) return value.map(normalize);
            if (!value || typeof value !== 'object') return value;
            return Object.keys(value).sort().reduce((result, key) => {
                if (key !== 'instance_id') result[key] = normalize(value[key]);
                return result;
            }, {});
        };
        return JSON.stringify(normalize(card));
    }

    function storyPileCardGroups(cards) {
        const groups = new Map();
        cards.forEach((card) => {
            const key = storyPileCardIdentity(card);
            const group = groups.get(key) || { card, count: 0 };
            group.count += 1;
            groups.set(key, group);
        });
        return [...groups.values()].sort((left, right) => {
            const leftValues = cardValues(left.card);
            const rightValues = cardValues(right.card);
            const leftRarity = STORY_RARITY_ORDER.indexOf(String(leftValues?.rarity || 'common'));
            const rightRarity = STORY_RARITY_ORDER.indexOf(String(rightValues?.rarity || 'common'));
            const rarityCompare = (leftRarity < 0 ? 999 : leftRarity)
                - (rightRarity < 0 ? 999 : rightRarity);
            if (rarityCompare) return rarityCompare;
            const typeOrder = Object.keys(storyContent?.card_types || {});
            const typeCompare = typeOrder.indexOf(leftValues?.type) - typeOrder.indexOf(rightValues?.type);
            if (typeCompare) return typeCompare;
            return localize(leftValues?.name).localeCompare(localize(rightValues?.name), lang);
        });
    }

    function createStoryPileTile(card, count = 1) {
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
        const countLabel = document.createElement('span');
        countLabel.className = 'story-pile-count';
        countLabel.textContent = `×${count}`;
        inner.append(costs, name, art);
        tile.append(inner);
        entry.append(tile, countLabel);
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
            storyPileCardGroups(cards).forEach(({ card, count }) => {
                grid?.append(createStoryPileTile(card, count));
            });
        }
        const dialog = $('story-pile-dialog');
        if (dialog) {
            dialog.dataset.pileKind = kind;
            dialog.showModal();
        }
    }

    function storyEnchantmentBookDefinition(bookOrId) {
        const bookId = typeof bookOrId === 'string'
            ? bookOrId
            : String(bookOrId?.book_id || '');
        return storyContent?.enchantment_books?.[bookId] || null;
    }

    function storyEnchantmentEligibleHand(definition, state) {
        const hand = Array.isArray(state?.combat?.hand) ? state.combat.hand : [];
        const target = String(definition?.target || 'none');
        return hand.filter((card) => {
            const values = cardValues(card);
            if (!values) return false;
            if (target === 'attack_card') return values.type === 'thorn';
            if (target === 'skill_card') return values.type === 'bloom';
            if (target === 'exile_card') return (values.tags || []).includes('exile');
            if (target === 'cost_card') {
                return Number(values.cost_e === 'X' ? 0 : values.cost_e || 0)
                    + Number(values.cost_m || 0) > 0;
            }
            return true;
        });
    }

    function openEnchantmentCardSelection(book) {
        const definition = storyEnchantmentBookDefinition(book);
        const dialog = $('story-card-choice-dialog');
        const grid = $('story-card-choice-grid');
        if (!definition || !dialog || !grid || dialog.open) return false;
        const target = String(definition.target || 'none');
        const source = storyEnchantmentEligibleHand(definition, activeRun?.state);
        const minimum = target === 'three_cards' ? 3 : (target === 'any_cards' ? 0 : 1);
        const maximum = target === 'three_cards' ? 3 : (target === 'any_cards' ? source.length : 1);
        if (source.length < minimum) {
            showToast(lang === 'zh' ? '当前没有足够的合适手牌' : 'Not enough eligible cards');
            return false;
        }
        if (!source.length && minimum === 0) {
            storyAction('use_enchantment_book', {
                book_instance_id: book.instance_id,
                selected_card_ids: [],
            });
            return true;
        }
        setStoryCardChoiceRequired(false);
        cardChoiceContext = {
            mode: 'enchantment_book',
            bookInstanceId: String(book.instance_id || ''),
            spec: { source, payloadKey: 'selected_card_ids', minimum, maximum },
            selected: new Set(),
        };
        setText('story-card-choice-title', localize(definition.name) || t.enchantmentBooks);
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
        $('story-enchantment-books-dialog')?.close();
        dialog.showModal();
        return true;
    }

    function createStoryEnchantmentBookTile(book, options = {}) {
        const definition = storyEnchantmentBookDefinition(book);
        const article = document.createElement('article');
        article.className = `story-enchantment-book story-enchantment-book-${String(definition?.rarity || 'common')}`;
        if (!definition) return article;
        const image = document.createElement('img');
        image.src = String(definition.image_url || '');
        image.alt = '';
        const copy = document.createElement('div');
        const title = document.createElement('h3');
        title.textContent = localize(definition.name) || String(book.book_id || '');
        const rarity = document.createElement('small');
        rarity.textContent = localize(storyContent?.rarities?.[definition.rarity]?.name)
            || String(definition.rarity || '');
        const description = document.createElement('p');
        appendStoryRichText(description, localize(definition.description));
        copy.append(title, rarity, description);
        article.append(image, copy);
        if (options.actions !== false) {
            const actions = document.createElement('div');
            actions.className = 'story-enchantment-book-actions';
            const canUse = activeRun?.state?.phase === 'combat'
                && activeRun?.state?.combat?.turn === 'player'
                && !activeRun?.state?.combat?.pending_card_choice
                && definition.script !== 'lethal_guard'
                && (!definition.character_id
                    || definition.character_id === activeRun?.state?.player?.character_id);
            if (definition.script === 'copy_book') {
                const select = document.createElement('select');
                (activeRun?.state?.player?.enchantment_books || [])
                    .filter((item) => item.instance_id !== book.instance_id)
                    .forEach((item) => {
                        const option = document.createElement('option');
                        option.value = item.instance_id;
                        option.textContent = localize(storyEnchantmentBookDefinition(item)?.name) || item.book_id;
                        select.append(option);
                    });
                select.disabled = !canUse || !select.options.length;
                actions.append(select);
                const use = document.createElement('button');
                use.type = 'button';
                use.textContent = t.useBook;
                use.disabled = select.disabled;
                use.addEventListener('click', () => {
                    $('story-enchantment-books-dialog')?.close();
                    storyAction('use_enchantment_book', {
                        book_instance_id: book.instance_id,
                        target_book_instance_id: select.value,
                    });
                });
                actions.append(use);
            } else {
                const use = document.createElement('button');
                use.type = 'button';
                use.textContent = definition.script === 'lethal_guard'
                    ? (lang === 'zh' ? '自动触发' : 'Automatic')
                    : t.useBook;
                use.disabled = !canUse;
                use.addEventListener('click', () => {
                    if (definition.target && definition.target !== 'none') {
                        openEnchantmentCardSelection(book);
                        return;
                    }
                    $('story-enchantment-books-dialog')?.close();
                    storyAction('use_enchantment_book', { book_instance_id: book.instance_id });
                });
                actions.append(use);
            }
            const discard = document.createElement('button');
            discard.type = 'button';
            discard.className = 'is-danger';
            discard.textContent = t.discardBook;
            discard.disabled = actionInFlight;
            discard.addEventListener('click', async () => {
                await storyAction('discard_enchantment_book', {
                    book_instance_id: book.instance_id,
                });
                renderStoryEnchantmentBooks();
            });
            actions.append(discard);
            article.append(actions);
        }
        return article;
    }

    function renderStoryEnchantmentBooks() {
        const grid = $('story-enchantment-books-grid');
        if (!grid) return;
        grid.replaceChildren();
        const books = activeRun?.state?.player?.enchantment_books || [];
        if (!books.length) {
            const empty = document.createElement('p');
            empty.className = 'story-codex-empty';
            empty.textContent = lang === 'zh' ? '尚未获得附魔书' : 'No enchantment books acquired';
            grid.append(empty);
            return;
        }
        books.forEach((book) => grid.append(createStoryEnchantmentBookTile(book)));
    }

    function openStoryEnchantmentBooks() {
        if (!activeRun?.state?.player) return;
        setText('story-enchantment-books-copy', t.enchantmentBookCopy);
        renderStoryEnchantmentBooks();
        $('story-enchantment-books-dialog')?.showModal();
    }

    function chooseStoryEnchantmentBookReplacement(callback) {
        const books = activeRun?.state?.player?.enchantment_books || [];
        if (books.length < 3) {
            callback('');
            return;
        }
        const grid = $('story-enchantment-books-grid');
        if (!grid) return;
        setText('story-enchantment-books-copy', t.bookSlotsFull);
        grid.replaceChildren();
        books.forEach((book) => {
            const tile = createStoryEnchantmentBookTile(book, { actions: false });
            const replace = document.createElement('button');
            replace.type = 'button';
            replace.className = 'story-command story-command-primary';
            replace.textContent = t.replaceBook;
            replace.addEventListener('click', () => {
                $('story-enchantment-books-dialog')?.close();
                setText('story-enchantment-books-copy', t.enchantmentBookCopy);
                callback(String(book.instance_id || ''));
            });
            tile.append(replace);
            grid.append(tile);
        });
        $('story-enchantment-books-dialog')?.showModal();
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
        if (['tag', 'resource', 'status', 'trait'].includes(item.kind)) {
            const reference = { mode: 'terms', kind: item.kind, id: item.id };
            const currentReference = {
                mode: storyCodexMode,
                kind: storyCodexMode === 'terms' ? storyCodexTermKind : '',
                id: storyCodexSelectedId,
            };
            const isCurrent = $('story-codex-dialog')?.open
                && storyCodexReferenceKey(reference) === storyCodexReferenceKey(currentReference);
            if (!isCurrent && storyCodexTargetIsDiscovered(reference.mode, reference.id, reference.kind)) {
                const link = document.createElement('button');
                link.type = 'button';
                link.className = 'story-term-codex-link';
                link.title = t.codexViewRelated;
                while (heading.firstChild) link.append(heading.firstChild);
                const arrow = document.createElement('span');
                arrow.className = 'story-term-codex-arrow';
                arrow.textContent = '→';
                link.append(arrow);
                link.addEventListener('click', () => {
                    const codexWasOpen = Boolean($('story-codex-dialog')?.open);
                    closeStoryCardTerms();
                    if (!codexWasOpen) openStoryCodex();
                    navigateStoryCodex(reference.mode, reference.id, {
                        kind: reference.kind,
                        push: codexWasOpen,
                    });
                });
                heading.append(link);
            }
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

    function clearStoryCardTermNavigation() {
        storyCardTermNavigation = null;
        storyCardTermPointerStart = null;
        storyCardTermWheelLockedUntil = 0;
    }

    function storyCardTermNavigationFromElement(sourceElement, options = {}) {
        if (!sourceElement || !storyCardElementData.has(sourceElement)) return null;
        const scope = sourceElement.closest?.(
            '#story-hand, #story-pile-grid, #story-card-choice-grid, '
            + '#story-blessing-options, #story-room-options, #story-reward-options, '
            + '#story-player-equipment, .story-codex-card-grid, .story-mechanical-track-cards',
        ) || sourceElement.parentElement;
        if (!scope) return null;
        const selector = [
            '.story-card.card', '.story-pile-tile', '.story-card-choice-select-item',
            '.story-event-card-chip', '.story-equipment', '.story-mechanical-track-card',
        ].join(', ');
        const candidates = [
            ...(storyCardElementData.has(scope) ? [scope] : []),
            ...scope.querySelectorAll(selector),
        ].filter((element) => storyCardElementData.has(element));
        const roots = candidates.filter((element) => !candidates.some((parent) => (
            parent !== element && parent.contains(element)
        )));
        const entries = roots.map((element) => {
            const storedOptions = storyCardTermOptions.get(element) || {};
            return {
                element,
                card: storyCardElementData.get(element),
                options: {
                    ...(Array.isArray(storedOptions.allowedUpgradeStates)
                        ? { allowedUpgradeStates: [...storedOptions.allowedUpgradeStates] }
                        : {}),
                },
            };
        }).filter((entry) => cardValues(entry.card));
        const index = entries.findIndex((entry) => (
            entry.element === sourceElement || entry.element.contains(sourceElement)
        ));
        if (index < 0) return null;
        if (Array.isArray(options.allowedUpgradeStates)) {
            entries[index].options.allowedUpgradeStates = [...options.allowedUpgradeStates];
        }
        return { entries, index };
    }

    function openStoryCardTermsFromElement(sourceElement, options = {}) {
        const card = sourceElement ? storyCardElementData.get(sourceElement) : null;
        if (!cardValues(card)) return false;
        const navigation = storyCardTermNavigationFromElement(sourceElement, options);
        openStoryCardTerms(card, {
            ...options,
            ...(navigation ? {
                navigationEntries: navigation.entries,
                navigationIndex: navigation.index,
            } : {}),
        });
        return true;
    }

    function navigateStoryCardTerms(direction, options = {}) {
        const navigation = storyCardTermNavigation;
        const count = navigation?.entries?.length || 0;
        if (count < 2) return false;
        const step = Number(direction) < 0 ? -1 : 1;
        const nextIndex = (Number(navigation.index || 0) + step + count) % count;
        const entry = navigation.entries[nextIndex];
        if (!entry || !cardValues(entry.card)) return false;
        navigation.index = nextIndex;
        openStoryCardTerms(entry.card, {
            ...(entry.options || {}),
            navigationEntries: navigation.entries,
            navigationIndex: nextIndex,
            fromNavigation: true,
        });
        if (options.focusButton) {
            requestAnimationFrame(() => {
                $('story-term-content')?.querySelector(
                    `[data-story-card-nav-direction="${step < 0 ? 'previous' : 'next'}"]`,
                )?.focus();
            });
        }
        return true;
    }

    function createStoryCardTermNavigationControls() {
        const navigation = storyCardTermNavigation;
        const count = navigation?.entries?.length || 0;
        if (count < 2) return null;
        const controls = document.createElement('div');
        controls.className = 'story-card-terms-navigation';
        const previous = document.createElement('button');
        previous.type = 'button';
        previous.className = 'story-card-terms-nav-button';
        previous.dataset.storyCardNavDirection = 'previous';
        previous.setAttribute('aria-label', t.previousCard);
        previous.title = t.previousCard;
        previous.textContent = '←';
        previous.addEventListener('click', () => navigateStoryCardTerms(-1, { focusButton: true }));
        const position = document.createElement('span');
        position.className = 'story-card-terms-nav-position';
        position.setAttribute('aria-live', 'polite');
        position.textContent = t.cardPosition(Number(navigation.index || 0) + 1, count);
        const next = document.createElement('button');
        next.type = 'button';
        next.className = 'story-card-terms-nav-button';
        next.dataset.storyCardNavDirection = 'next';
        next.setAttribute('aria-label', t.nextCard);
        next.title = t.nextCard;
        next.textContent = '→';
        next.addEventListener('click', () => navigateStoryCardTerms(1, { focusButton: true }));
        controls.append(previous, position, next);
        return controls;
    }

    function storyCardTermNavigationAvailable() {
        return (storyCardTermNavigation?.entries?.length || 0) > 1;
    }

    function handleStoryCardTermWheel(event) {
        if (!storyCardTermNavigationAvailable()) return;
        if (!event.target?.closest?.('.story-card-terms-preview-column')) return;
        const delta = Math.abs(Number(event.deltaY || 0)) >= Math.abs(Number(event.deltaX || 0))
            ? Number(event.deltaY || 0)
            : Number(event.deltaX || 0);
        if (!Number.isFinite(delta) || Math.abs(delta) < 4) return;
        event.preventDefault();
        event.stopPropagation();
        const now = performance.now();
        if (now < storyCardTermWheelLockedUntil) return;
        if (navigateStoryCardTerms(delta < 0 ? -1 : 1)) {
            storyCardTermWheelLockedUntil = now + 220;
        }
    }

    function handleStoryCardTermKeydown(event) {
        if (!storyCardTermNavigationAvailable()) return;
        if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
        if (event.target?.closest?.(
            '.story-card-version-tabs, input, textarea, select, [contenteditable="true"]',
        )) return;
        event.preventDefault();
        event.stopPropagation();
        navigateStoryCardTerms(event.key === 'ArrowLeft' ? -1 : 1);
    }

    function handleStoryCardTermPointerDown(event) {
        if (!storyCardTermNavigationAvailable()) return;
        if (!['touch', 'pen'].includes(String(event.pointerType || ''))) return;
        if (event.button != null && event.button !== 0) return;
        if (!event.target?.closest?.('.story-card-terms-preview-column')) return;
        storyCardTermPointerStart = {
            pointerId: event.pointerId,
            x: Number(event.clientX),
            y: Number(event.clientY),
        };
    }

    function handleStoryCardTermPointerUp(event) {
        const start = storyCardTermPointerStart;
        storyCardTermPointerStart = null;
        if (!start || start.pointerId !== event.pointerId) return;
        const deltaX = Number(event.clientX) - start.x;
        const deltaY = Number(event.clientY) - start.y;
        if (Math.abs(deltaX) < 42 || Math.abs(deltaX) <= Math.abs(deltaY) * 1.15) return;
        event.preventDefault();
        event.stopPropagation();
        navigateStoryCardTerms(deltaX < 0 ? 1 : -1);
    }

    function closeStoryCardTerms() {
        const dialog = $('story-term-dialog');
        if (!dialog) return;
        if (dialog.open) dialog.close();
        delete dialog.dataset.storyTermKey;
        delete dialog.dataset.storyTermUpgrade;
        clearStoryCardTermNavigation();
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
        clearStoryCardTermNavigation();
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
        clearStoryCardTermNavigation();
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
        if (Array.isArray(options.navigationEntries)) {
            const entries = options.navigationEntries.filter((entry) => cardValues(entry?.card));
            const requestedIndex = Number(options.navigationIndex);
            storyCardTermNavigation = {
                entries,
                index: Number.isInteger(requestedIndex)
                    ? Math.max(0, Math.min(entries.length - 1, requestedIndex))
                    : 0,
            };
        } else if (!options.fromNavigation) {
            clearStoryCardTermNavigation();
        }
        const termKey = storyCardTermKey(card);
        if (
            dialog.open
            && dialog.dataset.storyTermKey === termKey
            && !options.fromNavigation
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
            const previewColumn = document.createElement('div');
            previewColumn.className = 'story-card-terms-preview-column';
            const preview = document.createElement('div');
            preview.className = 'story-card-terms-preview';
            preview.append(createStoryCard(displayCard, {
                interactive: false,
                predictionTargetId: '',
            }));
            previewColumn.append(preview);
            const navigationControls = createStoryCardTermNavigationControls();
            if (navigationControls) previewColumn.append(navigationControls);

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
            appendStoryCodexRelated(copy, storyCodexBacklinksForCard(displayCard.def_id));
            layout.append(previewColumn, copy);
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
        if (contentType === 'enchantment_book') {
            return localize(storyContent?.enchantment_books?.[contentId]?.name) || contentId;
        }
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
        if (payload.progress && typeof payload.progress === 'object') {
            storyProgress = payload.progress;
            if ($('story-character-options')) renderStoryCharacterOptions();
        }
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

    function storyCodexSnapshot() {
        return {
            mode: storyCodexMode,
            selectedId: storyCodexSelectedId,
            talentKind: storyCodexTalentKind,
            termKind: storyCodexTermKind,
            search: storyCodexSearch,
            rarities: [...storyCodexRarities],
            types: [...storyCodexTypes],
        };
    }

    function restoreStoryCodexSnapshot(snapshot) {
        if (!snapshot || typeof snapshot !== 'object') return;
        storyCodexMode = String(snapshot.mode || 'cards');
        storyCodexSelectedId = String(snapshot.selectedId || '');
        storyCodexTalentKind = String(snapshot.talentKind || 'relic');
        storyCodexTermKind = String(snapshot.termKind || 'status');
        storyCodexSearch = String(snapshot.search || '');
        storyCodexRarities.clear();
        (snapshot.rarities || []).forEach((value) => storyCodexRarities.add(String(value)));
        storyCodexTypes.clear();
        (snapshot.types || []).forEach((value) => storyCodexTypes.add(String(value)));
        const input = $('story-codex-search');
        if (input) input.value = storyCodexSearch;
    }

    function storyCodexTargetIsDiscovered(mode, id, kind = '') {
        const targetId = String(id || '');
        if (!targetId) return true;
        if (mode === 'cards') return storyCodexDiscoveredIds('card').has(targetId);
        if (mode === 'enemies') return storyCodexDiscoveredIds('enemy').has(targetId);
        if (mode === 'talents') {
            const contentType = kind === 'blessing' ? 'blessing' : 'relic';
            return storyCodexDiscoveredIds(contentType).has(targetId);
        }
        if (mode === 'enchantment_books') {
            return storyCodexDiscoveredIds('enchantment_book').has(targetId);
        }
        if (mode === 'terms') {
            return storyCodexDiscoveredIds('term').has(`${String(kind || '')}:${targetId}`);
        }
        return false;
    }

    function navigateStoryCodex(mode, id = '', options = {}) {
        const targetMode = ['cards', 'enemies', 'talents', 'enchantment_books', 'terms'].includes(mode) ? mode : 'cards';
        const targetId = String(id || '');
        const targetKind = String(options.kind || '');
        if (!storyCodexTargetIsDiscovered(targetMode, targetId, targetKind)) return false;
        if (options.push !== false && $('story-codex-dialog')?.open) {
            storyCodexHistory.push(storyCodexSnapshot());
            if (storyCodexHistory.length > 24) storyCodexHistory.shift();
        }
        storyCodexMode = targetMode;
        storyCodexSelectedId = targetId;
        if (targetMode === 'talents' && targetKind) storyCodexTalentKind = targetKind;
        if (targetMode === 'terms' && targetKind) storyCodexTermKind = targetKind;
        if (!options.preserveSearch) {
            storyCodexSearch = '';
            const input = $('story-codex-search');
            if (input) input.value = '';
        }
        if (targetMode === 'cards' && targetId) {
            const definition = storyContent?.cards?.[targetId];
            if (definition) {
                storyCodexRarities.add(String(definition.rarity || 'common'));
                storyCodexTypes.add(String(definition.type || ''));
            }
        }
        renderStoryCodex();
        return true;
    }

    function returnStoryCodexHistory() {
        const snapshot = storyCodexHistory.pop();
        if (!snapshot) return false;
        restoreStoryCodexSnapshot(snapshot);
        renderStoryCodex();
        return true;
    }

    function storyCodexReferenceKey(reference) {
        return [reference?.mode, reference?.kind, reference?.id].map((value) => String(value || '')).join(':');
    }

    function storyCodexReferenceLabel(reference) {
        const id = String(reference?.id || '');
        if (reference?.mode === 'cards') return localize(storyContent?.cards?.[id]?.name) || id;
        if (reference?.mode === 'enemies') return localize(storyContent?.enemies?.[id]?.name) || id;
        if (reference?.mode === 'talents') {
            const catalog = reference.kind === 'blessing' ? storyContent?.blessings : storyContent?.relics;
            return localize(catalog?.[id]?.name) || localize(catalog?.[id]?.description) || id;
        }
        if (reference?.mode === 'enchantment_books') {
            return localize(storyContent?.enchantment_books?.[id]?.name) || id;
        }
        if (reference?.mode === 'terms') {
            return localize(storyCodexTermDefinition(reference.kind, id)?.name) || id;
        }
        return id;
    }

    function createStoryCodexReferenceButton(reference) {
        if (!reference || !storyCodexTargetIsDiscovered(reference.mode, reference.id, reference.kind)) return null;
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `story-codex-reference story-codex-reference-${String(reference.mode || 'entry')}`;
        button.dataset.storyCodexReference = storyCodexReferenceKey(reference);
        const marker = document.createElement('span');
        marker.className = 'story-codex-reference-marker';
        if (reference.mode === 'terms' && reference.kind === 'status') {
            const icon = document.createElement('img');
            icon.src = storyStatusIconUrl(reference.id);
            icon.alt = '';
            marker.append(icon);
        } else if (reference.mode === 'terms' && reference.kind === 'trait') {
            const icon = document.createElement('img');
            icon.src = storyTraitIconUrl(reference.id);
            icon.alt = '';
            marker.append(icon);
        } else if (reference.mode === 'enemies' && storyContent?.enemies?.[reference.id]?.image_url) {
            const icon = document.createElement('img');
            icon.src = storyContent.enemies[reference.id].image_url;
            icon.alt = '';
            marker.append(icon);
        } else {
            marker.textContent = reference.mode === 'cards'
                ? '▣'
                : (reference.mode === 'talents' ? '★' : (reference.mode === 'enchantment_books' ? '◆' : '•'));
        }
        const label = document.createElement('span');
        label.textContent = storyCodexReferenceLabel(reference);
        button.append(marker, label);
        button.title = `${t.codexViewRelated}：${label.textContent}`;
        button.addEventListener('click', () => {
            const codexWasOpen = Boolean($('story-codex-dialog')?.open);
            closeStoryCardTerms();
            if (!codexWasOpen) openStoryCodex();
            navigateStoryCodex(reference.mode, reference.id, {
                kind: reference.kind,
                push: codexWasOpen,
            });
        });
        return button;
    }

    function appendStoryCodexRelated(container, references) {
        if (!container) return false;
        const currentKey = storyCodexReferenceKey({
            mode: storyCodexMode,
            kind: storyCodexMode === 'terms'
                ? storyCodexTermKind
                : (storyCodexMode === 'talents' ? storyCodexTalentKind : ''),
            id: storyCodexSelectedId,
        });
        const unique = new Map();
        (references || []).forEach((reference) => {
            const key = storyCodexReferenceKey(reference);
            if (!key || key === currentKey || unique.has(key)) return;
            if (!storyCodexTargetIsDiscovered(reference.mode, reference.id, reference.kind)) return;
            unique.set(key, reference);
        });
        const buttons = [...unique.values()]
            .map(createStoryCodexReferenceButton)
            .filter(Boolean);
        if (!buttons.length) return false;
        const section = document.createElement('section');
        section.className = 'story-codex-related';
        const title = document.createElement('h4');
        title.textContent = t.codexRelated;
        const list = document.createElement('div');
        list.className = 'story-codex-related-list';
        list.append(...buttons);
        section.append(title, list);
        container.append(section);
        return true;
    }

    function storyCodexWalkDefinition(value, visitor) {
        if (Array.isArray(value)) {
            value.forEach((item) => storyCodexWalkDefinition(item, visitor));
            return;
        }
        if (!value || typeof value !== 'object') return;
        Object.entries(value).forEach(([key, item]) => {
            visitor(key, item);
            storyCodexWalkDefinition(item, visitor);
        });
    }

    function storyCodexDefinitionReferences(definition) {
        if (!definition || typeof definition !== 'object') return [];
        const references = new Map();
        const add = (reference) => {
            const key = storyCodexReferenceKey(reference);
            if (key) references.set(key, reference);
        };
        (definition.tags || []).forEach((id) => add({ mode: 'terms', kind: 'tag', id }));
        const statusIds = new Set();
        collectStoryStatusIds(definition.effects, statusIds);
        statusIds.forEach((id) => add({ mode: 'terms', kind: 'status', id }));

        const textValues = ['name', 'description', 'flavor']
            .flatMap((field) => {
                const value = definition[field];
                return value && typeof value === 'object' ? Object.values(value) : [value];
            })
            .map((value) => String(value || ''));
        Object.entries(storyContent?.statuses || {}).forEach(([id, term]) => {
            const names = Object.values(term?.name || {}).map((value) => String(value || '')).filter(Boolean);
            if (names.some((name) => textValues.some((text) => text.includes(name)))) {
                add({ mode: 'terms', kind: 'status', id });
            }
        });
        Object.entries(storyContent?.tags || {}).forEach(([id, term]) => {
            const names = Object.values(term?.name || {}).map((value) => String(value || '')).filter(Boolean);
            if (names.some((name) => textValues.some((text) => text.includes(name)))) {
                add({ mode: 'terms', kind: 'tag', id });
            }
        });
        textValues.forEach((text) => {
            const cardPattern = /\[\[card:([a-z0-9_-]+)\]\]/gi;
            let cardMatch = null;
            while ((cardMatch = cardPattern.exec(text))) add({ mode: 'cards', id: cardMatch[1] });
            Object.keys(STORY_RESOURCE_TERMS).forEach((unit) => {
                const marker = new RegExp(`\\[\\[icon:${unit}\\]\\]|(?:^|[^A-Za-z])${unit}(?:$|[^A-Za-z])`, 'i');
                if (marker.test(text)) add({ mode: 'terms', kind: 'resource', id: unit });
            });
        });
        if (definition.cost_e != null) add({ mode: 'terms', kind: 'resource', id: 'E' });
        if (definition.cost_m != null) add({ mode: 'terms', kind: 'resource', id: 'M' });

        const damageTypes = new Set([
            'damage', 'damage_per_status', 'damage_from_shield', 'damage_from_player_status',
            'consume_status_damage', 'consume_magic_damage', 'self_damage', 'consume_pearls_damage',
        ]);
        const healTypes = new Set(['heal', 'self_heal', 'allies_heal', 'heal_to_full']);
        storyCodexWalkDefinition(definition.effects || [], (key, value) => {
            if (key === 'status' && typeof value === 'string') add({ mode: 'terms', kind: 'status', id: value });
            if (key === 'card_id' && typeof value === 'string') add({ mode: 'cards', id: value });
            if (key === 'enemy_id' && typeof value === 'string') add({ mode: 'enemies', id: value });
            if (key !== 'type' || typeof value !== 'string') return;
            if (damageTypes.has(value)) add({ mode: 'terms', kind: 'resource', id: 'D' });
            if (healTypes.has(value)) add({ mode: 'terms', kind: 'resource', id: 'H' });
            if (['elixir', 'turn_elixir'].includes(value)) add({ mode: 'terms', kind: 'resource', id: 'E' });
            if (['magic', 'turn_magic', 'gain_magic', 'consume_magic_damage'].includes(value)) {
                add({ mode: 'terms', kind: 'resource', id: 'M' });
            }
        });
        return [...references.values()];
    }

    function storyCodexCardReferences(card) {
        const references = storyCardTermItems(card).map((item) => ({
            mode: 'terms', kind: item.kind, id: item.id,
        }));
        return [...references, ...storyCodexDefinitionReferences(cardValues(card))];
    }

    function storyCodexEnemyReferences(record) {
        if (!record?.definition) return [];
        const references = (record.definition.traits || []).map((id) => ({
            mode: 'terms', kind: 'trait', id,
        }));
        [...(record.intents || [])].forEach((index) => {
            const move = record.definition.moves?.[index];
            if (move) references.push(...storyCodexDefinitionReferences(move));
        });
        return references;
    }

    function storyCodexTalentReferences(record) {
        return storyCodexDefinitionReferences(record?.definition);
    }

    function storyCodexReferenceMatchesTerm(reference, record) {
        return reference?.mode === 'terms'
            && String(reference.kind || '') === String(record?.kind || '')
            && String(reference.id || '') === String(record?.id || '');
    }

    function storyCodexBacklinksForTerm(record) {
        if (!record?.definition) return [];
        const references = [];
        storyCodexCardRecords().forEach((cardRecord) => {
            const states = [
                ...(cardRecord.variants.has('base') ? [false] : []),
                ...(cardRecord.variants.has('upgraded') ? [true] : []),
            ];
            if (states.some((upgraded) => storyCodexCardReferences({
                instance_id: `codex-related:${cardRecord.id}:${upgraded ? 'upgraded' : 'base'}`,
                def_id: cardRecord.id,
                upgraded,
            }).some((reference) => storyCodexReferenceMatchesTerm(reference, record)))) {
                references.push({ mode: 'cards', id: cardRecord.id });
            }
        });
        storyCodexEnemyRecords().forEach((enemyRecord) => {
            if (storyCodexEnemyReferences(enemyRecord).some((reference) => storyCodexReferenceMatchesTerm(reference, record))) {
                references.push({ mode: 'enemies', id: enemyRecord.id });
            }
        });
        ['relic', 'blessing'].forEach((kind) => {
            const catalog = kind === 'blessing' ? storyContent?.blessings : storyContent?.relics;
            const contentType = kind === 'blessing' ? 'blessing' : 'relic';
            storyCodexDiscoveredIds(contentType).forEach((id) => {
                const talentRecord = { id, kind, definition: catalog?.[id] };
                if (storyCodexTalentReferences(talentRecord).some((reference) => storyCodexReferenceMatchesTerm(reference, record))) {
                    references.push({ mode: 'talents', kind, id });
                }
            });
        });
        return references;
    }

    function storyCodexBacklinksForCard(cardId) {
        const references = [];
        storyCodexEnemyRecords().forEach((enemyRecord) => {
            if (storyCodexEnemyReferences(enemyRecord).some((reference) => (
                reference.mode === 'cards' && String(reference.id) === String(cardId)
            ))) references.push({ mode: 'enemies', id: enemyRecord.id });
        });
        ['relic', 'blessing'].forEach((kind) => {
            const catalog = kind === 'blessing' ? storyContent?.blessings : storyContent?.relics;
            const contentType = kind === 'blessing' ? 'blessing' : 'relic';
            storyCodexDiscoveredIds(contentType).forEach((id) => {
                const record = { id, kind, definition: catalog?.[id] };
                if (storyCodexTalentReferences(record).some((reference) => (
                    reference.mode === 'cards' && String(reference.id) === String(cardId)
                ))) references.push({ mode: 'talents', kind, id });
            });
        });
        return references;
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
            let cardElement = null;
            cardElement = createStoryCard(card, {
                onClick: () => {
                    storyCodexSelectedId = record.id;
                    openStoryCardTermsFromElement(cardElement, { allowedUpgradeStates });
                },
            });
            cardElement.classList.add('story-codex-card-tile');
            cardElement.classList.toggle('is-related-target', storyCodexSelectedId === record.id);
            cardElement.dataset.storyCodexCardId = record.id;
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
        if (type === 'damage_from_shield') {
            const divisor = Math.max(1, Number(effect.divisor) || 1);
            return {
                kind: 'special', effect_type: type, target: 'player',
                label: {
                    zh: `造成(${amount}+护盾层数/${divisor})D`,
                    en: `Deal (${amount} + Shield/${divisor}) D`,
                },
            };
        }
        if (type === 'damage_from_player_status') {
            const status = storyIntentStatusLabel(effect.status);
            return {
                kind: 'special', effect_type: type, target: 'player',
                label: {
                    zh: `造成(${amount}+玩家${status}层数)D`,
                    en: `Deal (${amount} + player ${status} stacks) D`,
                },
            };
        }
        if (type === 'consume_status_damage') {
            const status = storyIntentStatusLabel(effect.status);
            const divisor = Math.max(1, Number(effect.divisor) || 1);
            return {
                kind: 'special', effect_type: type, target: 'player',
                label: {
                    zh: `清除自身${status}，造成(层数/${divisor})D`,
                    en: `Clear own ${status}; deal stacks/${divisor} D`,
                },
            };
        }
        if (type === 'consume_magic_damage') {
            const multiplier = Math.max(0, Number(effect.multiplier) || 0);
            return {
                kind: 'special', effect_type: type, target: 'player',
                label: {
                    zh: `消耗全部M，造成(${amount}+消耗量×${multiplier})D`,
                    en: `Spend all M; deal (${amount} + spent × ${multiplier}) D`,
                },
            };
        }
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
        if (type === 'allies_status') {
            return { kind: 'status', status: effect.status, amount, target: 'all_enemies' };
        }
        if (type === 'named_allies_power') {
            return {
                kind: 'buff', stat: 'power', amount, target: 'named_enemy',
                enemy_id: effect.enemy_id,
                enemy_name: storyContent?.enemies?.[effect.enemy_id]?.name,
            };
        }
        if (type === 'heal_named_ally_percent') {
            return {
                kind: 'heal', amount, percent: true, target: 'named_enemy',
                enemy_id: effect.enemy_id,
                enemy_name: storyContent?.enemies?.[effect.enemy_id]?.name,
            };
        }
        if (type === 'allies_shield' || type === 'lowest_ally_shield' || type === 'adjacent_shield') {
            return { kind: 'defend', stat: 'shield', amount, target: type === 'allies_shield' ? 'all_enemies' : type };
        }
        if (type === 'summon_to_ant_count') {
            return {
                kind: 'special', effect_type: type, amount, target: 'self',
                label: {
                    zh: `补充蚂蚁至${amount}只`,
                    en: `Fill the ant group to ${amount}`,
                },
            };
        }
        if (type === 'summon_wreckage') {
            return {
                kind: 'summon', enemy_id: 'wreckage',
                enemy_name: storyContent?.enemies?.wreckage?.name,
                amount: amount || 1, target: 'self',
                details: {
                    zh: '死后依次召唤螃蟹、睡莲与海胆',
                    en: 'Their deaths summon Crab, Lily Pad, and Urchin in order',
                },
            };
        }
        if (type === 'summon') {
            const enemyId = String(effect.enemy_id || (type === 'summon_wreckage' ? 'wreckage' : ''));
            return {
                kind: 'summon', enemy_id: enemyId,
                enemy_name: storyContent?.enemies?.[enemyId]?.name,
                amount: amount || 1, target: 'self',
            };
        }
        if (type === 'add_draw_card' || type === 'delayed_hand_charge') {
            return {
                kind: 'card', effect_type: type, card_id: effect.card_id,
                amount: amount || 1, target: 'player',
            };
        }
        if (type === 'consume_allies') return { kind: 'consume', target: 'all_enemies' };
        if (type === 'consume_status') {
            return { kind: 'consume_status', status: effect.status, amount, target: 'self' };
        }
        if (type === 'gain_magic') {
            return { kind: 'resource', resource: 'magic', amount, target: 'self' };
        }
        if (type === 'disable_magic_shield') {
            return {
                kind: 'special', effect_type: type, amount, target: 'self',
                label: {
                    zh: '下回合魔力护盾失效',
                    en: 'Magic Shield is disabled next turn',
                },
            };
        }
        if (type === 'stun_if_player_shield') {
            return { kind: 'status', status: 'stun', amount: 1, target: 'player', conditional: 'shield' };
        }
        if (type === 'consume_pearls_damage' || type === 'lose_max_health_percent') {
            return { kind: 'special', effect_type: type, amount, target: type === 'lose_max_health_percent' ? 'self' : 'player' };
        }
        if (type === 'self_kill') return { kind: 'self_damage', target: 'self', lethal: true };
        return {
            kind: 'special', effect_type: type, amount,
            label: { zh: '执行特殊行动', en: 'Perform a special action' },
        };
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
                button.title = t.codexViewRelated;
                button.addEventListener('click', () => navigateStoryCodex('terms', traitId, {
                    kind: 'trait',
                    push: true,
                }));
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
        appendStoryCodexRelated(intents, storyCodexEnemyReferences(record));
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
            appendStoryCodexRelated(list, storyCodexTalentReferences(record));
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
        appendStoryCodexRelated(copy, storyCodexTalentReferences(record));
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

    function storyCodexEnchantmentBookRecords() {
        const discovered = storyCodexDiscoveredIds('enchantment_book');
        return [...discovered]
            .map((id) => ({ id, definition: storyContent?.enchantment_books?.[id] }))
            .filter((record) => (
                record.definition
                && storyCodexSearchMatches(record.id, record.definition)
            ))
            .sort((left, right) => {
                const rarityOrder = STORY_RARITY_ORDER.indexOf(String(left.definition.rarity || 'common'))
                    - STORY_RARITY_ORDER.indexOf(String(right.definition.rarity || 'common'));
                return rarityOrder || localize(left.definition.name)
                    .localeCompare(localize(right.definition.name), lang);
            });
    }

    function renderStoryCodexEnchantmentBooks(sidebar, detail) {
        const records = storyCodexEnchantmentBookRecords();
        const list = document.createElement('div');
        list.className = 'story-codex-entry-list';
        list.dataset.storyScrollKey = 'codex-enchantment-book-list';
        records.forEach((record) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = `story-codex-entry-row${storyCodexSelectedId === record.id ? ' is-active' : ''}`;
            const image = document.createElement('img');
            image.src = String(record.definition.image_url || '');
            image.alt = '';
            const copy = document.createElement('span');
            const name = document.createElement('strong');
            name.textContent = localize(record.definition.name) || record.id;
            const rarity = document.createElement('small');
            rarity.textContent = localize(storyContent?.rarities?.[record.definition.rarity]?.name)
                || String(record.definition.rarity || '');
            copy.append(name, rarity);
            button.append(image, copy);
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
        if (!records.some((record) => record.id === storyCodexSelectedId)) {
            storyCodexSelectedId = records[0].id;
        }
        const record = records.find((item) => item.id === storyCodexSelectedId);
        const wrapper = document.createElement('article');
        wrapper.className = 'story-codex-enchantment-book-detail';
        wrapper.append(createStoryEnchantmentBookTile({ book_id: record.id }, { actions: false }));
        appendStoryCodexRelated(wrapper, storyCodexDefinitionReferences(record.definition));
        detail.append(wrapper);
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
        appendStoryCodexRelated(list, storyCodexBacklinksForTerm(record));
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
        if (mode === 'enchantment_books') {
            return [
                storyCodexDiscoveredIds('enchantment_book').size,
                Object.keys(storyContent?.enchantment_books || {}).length,
            ];
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
        const back = $('story-codex-back');
        if (back) {
            back.classList.toggle('hidden', storyCodexHistory.length === 0);
            back.disabled = storyCodexHistory.length === 0;
        }
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
        else if (storyCodexMode === 'enchantment_books') renderStoryCodexEnchantmentBooks(sidebar, detail);
        else renderStoryCodexTerms(sidebar, detail);
        const subtype = storyCodexMode === 'talents'
            ? storyCodexTalentKind
            : (storyCodexMode === 'terms' ? storyCodexTermKind : '');
        sidebar.dataset.storyScrollKey = `codex-sidebar:${storyCodexMode}:${subtype}`;
        detail.dataset.storyScrollKey = `codex-detail:${storyCodexMode}:${subtype}:${storyCodexSelectedId}`;
        scheduleVisibleStoryCardEffectFits();
        restoreStoryScrollPositions(scrollPositions);
        if (storyCodexMode === 'cards' && storyCodexSelectedId) {
            requestAnimationFrame(() => {
                const target = [...detail.querySelectorAll('[data-story-codex-card-id]')]
                    .find((element) => element.dataset.storyCodexCardId === storyCodexSelectedId);
                target?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
            });
        }
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
        if (!dialog.open) storyCodexHistory = [];
        renderStoryCodex();
        if (!dialog.open) dialog.showModal();
        markStoryCodexViewed();
    }

    function closeStoryCodex() {
        const dialog = $('story-codex-dialog');
        if (dialog?.open) dialog.close();
        storyCodexHistory = [];
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
                .filter((card) => (
                    !['remove_card', 'transform_card'].includes(blessing.script)
                    || !cardValues(card)?.tags?.includes('eternal')
                ))
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

    function storySoloProgressForState(state) {
        const characterId = String(
            state?.character_id || state?.player?.character_id || 'common_flower'
        );
        return storyProgress?.characters?.[characterId] || null;
    }

    function storyJourneyDifficultyUnlocked(state, difficulty) {
        const progress = storySoloProgressForState(state);
        if (!progress) return ['easy', 'normal'].includes(String(difficulty));
        return Boolean(progress.difficulties?.[difficulty]);
    }

    function storyJourneyModeUnlocked(state, mode) {
        const progress = storySoloProgressForState(state);
        if (!progress) return String(mode) === 'standard';
        return Boolean(progress.modes?.[mode]);
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
                ? '标准旅程包含3个阶段；Boss Rush 将不断生成新的11房间固定路线。'
                : 'Standard journeys have 3 stages; Boss Rush repeats a fixed 11-room route.',
        );

        let selectedBiome = String(room.biomes?.[0] || 'garden');
        let selectedDifficulty = String(
            (room.difficulties || []).find(
                (difficulty) => storyJourneyDifficultyUnlocked(state, String(difficulty)),
            ) || 'normal'
        );
        let selectedMode = String(
            (room.modes || ['standard']).find(
                (mode) => storyJourneyModeUnlocked(state, String(mode)),
            ) || 'standard'
        );
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
                    ? '仅以护身符开局，先获得10次卡牌奖励与1项天赋；每轮依次经过赐福、3名首领、休息、宝箱与商店。'
                    : 'Start with only Amulet, then gain 10 card rewards and 1 talent. Each loop follows Blessing, 3 Bosses, Rest, Chests, and Shop.',
            },
        };
        appendStoryChoiceHeading(container, lang === 'zh' ? '模式' : 'Mode');
        (room.modes || ['standard']).forEach((modeId) => {
            const copy = modeCopy[modeId] || { name: String(modeId), description: '' };
            const unlocked = storyJourneyModeUnlocked(state, String(modeId));
            const button = choiceButton(
                copy.name,
                () => {
                    if (!unlocked) return;
                    selectedMode = String(modeId);
                    refreshSelections();
                },
                {
                    description: unlocked
                        ? copy.description
                        : `${copy.description}${copy.description ? ' · ' : ''}${lang === 'zh' ? '以困难难度通关后解锁' : 'Complete Hard to unlock'}`,
                },
            );
            button.disabled = !unlocked;
            button.classList.toggle('is-locked', !unlocked);
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
            const unlocked = storyJourneyDifficultyUnlocked(state, String(difficultyId));
            const button = choiceButton(
                difficultyLabel,
                () => {
                    if (!unlocked) return;
                    selectedDifficulty = String(difficultyId);
                    refreshSelections();
                },
                {
                    description: unlocked
                        ? localize(definition.description)
                        : `${localize(definition.description)} · ${lang === 'zh' ? '尚未解锁' : 'Locked'}`,
                },
            );
            button.disabled = !unlocked;
            button.classList.toggle('is-locked', !unlocked);
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
            { primary: true },
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
        if (combatPreview) {
            setText(
                'story-map-return',
                state.phase === 'combat'
                    ? t.returnToCombat
                    : ({ zh: '返回旅程', en: 'Return to Journey', fr: 'Retour au voyage', ja: '旅に戻る' }[lang] || t.close),
            );
        }
        renderMap(state.map, state.current_node_id, { readOnly: combatPreview });
        showView('story-run');
        renderStoryPersistentHud(activeRun);
    }

    function openStoryCombatMap() {
        const state = activeRun?.state;
        if (!state?.map || actionInFlight || cardPlayInFlight) return;
        if (storyMapPreviewOpen) {
            returnToStoryCombat();
            return;
        }
        if (state.phase === 'map') {
            renderMapView(state);
            return;
        }
        storyMapPreviewOpen = true;
        renderMapView(state, { combatPreview: true });
    }

    function returnToStoryCombat() {
        if (!storyMapPreviewOpen || !activeRun?.state) return;
        storyMapPreviewOpen = false;
        renderRun(activeRun);
    }

    function renderStoryPersistentHud(run) {
        const hud = $('story-persistent-hud');
        const state = run?.state;
        const visible = Boolean(
            run
            && run.compatible !== false
            && state
            && !['journey_setup', 'easy_relic', 'blessing'].includes(String(state.phase || ''))
        );
        hud?.classList.toggle('hidden', !visible);
        if (!visible) return;
        const player = state.player || {};
        const combat = state.combat || {};
        const difficulty = storyContent?.difficulties?.[String(state.difficulty || '')];
        setText('story-hud-difficulty', localize(difficulty?.name) || String(state.difficulty || ''));
        setText('story-hud-health', `${stateValue(player.health)}/${stateValue(player.max_health)}`);
        setText('story-hud-elixir', stateValue(combat.elixir ?? player.elixir ?? player.max_elixir));
        setText('story-hud-magic', stateValue(combat.magic ?? player.magic));
        setText('story-hud-gold', stateValue(player.gold ?? 0));
        setText(
            'story-hud-location',
            `${t.stage} ${stateValue(state.stage || 1)} · ${t.floor(state.current_floor || currentNode(state)?.floor || 1)}`,
        );
        const mapButton = $('story-hud-map');
        const deckButton = $('story-hud-deck');
        const booksButton = $('story-hud-books');
        const settingsButton = $('story-hud-settings');
        const mapOpen = storyMapPreviewOpen || String(state.phase || '') === 'map';
        if (mapButton) mapButton.disabled = !state.map || actionInFlight || cardPlayInFlight;
        mapButton?.classList.toggle('is-map-open', mapOpen);
        mapButton?.setAttribute('aria-expanded', mapOpen ? 'true' : 'false');
        if (deckButton) deckButton.disabled = !Array.isArray(player.deck) || actionInFlight || cardPlayInFlight;
        const bookCount = Array.isArray(player.enchantment_books) ? player.enchantment_books.length : 0;
        setText('story-hud-books-label', `${t.enchantmentBooks} ${bookCount}/3`);
        if (booksButton) booksButton.disabled = actionInFlight || cardPlayInFlight;
        if (settingsButton) settingsButton.disabled = actionInFlight || cardPlayInFlight;
        updateStoryManualSaveControls(run);
        updateStorySurrenderControl(run);
        updateStorySettingsControls(run);
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

    function storyMechanicalTrackMotionKey(enemyId) {
        return `${activeRun?.id || 'story'}:${String(enemyId || '')}`;
    }

    function storyMechanicalTrackMotion(enemyId) {
        const key = storyMechanicalTrackMotionKey(enemyId);
        if (!storyMechanicalTrackMotions.has(key)) {
            storyMechanicalTrackMotions.set(key, {
                angle: STORY_MECHANICAL_TRACK_TRIGGER_ANGLE,
                lastTimestamp: performance.now(),
                animating: false,
                paused: false,
            });
        }
        return storyMechanicalTrackMotions.get(key);
    }

    function advanceStoryMechanicalTrackMotion(motion, timestamp = performance.now()) {
        if (!motion) return;
        const elapsed = Math.max(0, Math.min(80, timestamp - Number(motion.lastTimestamp || timestamp)));
        if (!motion.animating && !motion.paused && !storyMechanicalTrackReducedMotion()) {
            motion.angle += elapsed / STORY_MECHANICAL_TRACK_PERIOD_MS * 360;
            if (Math.abs(motion.angle) > 36000) motion.angle %= 360;
        }
        motion.lastTimestamp = timestamp;
    }

    function applyStoryMechanicalTrackMotion(enemyId, motion = storyMechanicalTrackMotion(enemyId)) {
        const actor = storyEnemyActor(enemyId);
        const wheel = actor?.querySelector('.story-mechanical-track-wheel');
        if (!wheel || !motion) return;
        wheel.style.setProperty('--story-mechanical-track-rotation', `${motion.angle.toFixed(3)}deg`);
    }

    function tickStoryMechanicalTracks(timestamp) {
        storyMechanicalTrackFrame = 0;
        const wheels = [...document.querySelectorAll('.story-mechanical-track-wheel')];
        if (!wheels.length) return;
        wheels.forEach((wheel) => {
            const enemyId = String(wheel.dataset.enemyId || '');
            const motion = storyMechanicalTrackMotion(enemyId);
            advanceStoryMechanicalTrackMotion(motion, timestamp);
            wheel.style.setProperty('--story-mechanical-track-rotation', `${motion.angle.toFixed(3)}deg`);
        });
        storyMechanicalTrackFrame = window.requestAnimationFrame(tickStoryMechanicalTracks);
    }

    function ensureStoryMechanicalTrackFrame() {
        if (storyMechanicalTrackFrame) return;
        storyMechanicalTrackFrame = window.requestAnimationFrame(tickStoryMechanicalTracks);
    }

    function setStoryMechanicalTrackPaused(enemyId, paused) {
        const motion = storyMechanicalTrackMotion(enemyId);
        advanceStoryMechanicalTrackMotion(motion);
        motion.paused = Boolean(paused);
        applyStoryMechanicalTrackMotion(enemyId, motion);
    }

    function layoutStoryMechanicalTrackCards(wheel) {
        if (!wheel) return;
        const cards = [...wheel.querySelectorAll('.story-mechanical-track-card:not(.is-leaving)')];
        const count = Math.max(1, cards.length);
        const size = count > 12 ? 28 : (count > 8 ? 32 : 40);
        wheel.style.setProperty('--story-mechanical-track-count', String(count));
        wheel.style.setProperty('--story-mechanical-track-card-size', `${size}px`);
        cards.forEach((item, index) => {
            const angle = 360 / count * index;
            item.dataset.trackIndex = String(index);
            item.dataset.trackAngle = String(angle);
            item.style.setProperty('--story-mechanical-track-card-angle', `${angle}deg`);
        });
    }

    function createStoryMechanicalTrackCard(card, enemyId) {
        const values = cardValues(card);
        if (!values) return null;
        const item = document.createElement('button');
        item.type = 'button';
        item.className = 'story-mechanical-track-card';
        item.dataset.instanceId = String(card.instance_id || '');
        item.dataset.trackPersistent = card.track_persistent ? '1' : '0';
        item.setAttribute(
            'aria-label',
            `${localize(values.name)}：${localize(values.description)}`,
        );
        const visual = document.createElement('span');
        visual.className = 'story-mechanical-track-visual';
        const icon = document.createElement('span');
        icon.className = 'story-mechanical-track-icon';
        const imageUrl = card.upgraded
            ? (values.upgraded_image_url || values.image_url || '')
            : (values.image_url || '');
        if (imageUrl) {
            const image = document.createElement('img');
            image.className = 'story-mechanical-track-image';
            image.src = imageUrl;
            image.alt = '';
            image.draggable = false;
            image.setAttribute('aria-hidden', 'true');
            icon.append(image);
        } else {
            const fallback = document.createElement('span');
            fallback.className = 'story-mechanical-track-fallback';
            fallback.textContent = localize(values.name).slice(0, 1);
            icon.append(fallback);
        }
        visual.append(icon);
        item.append(visual);
        storyCardElementData.set(item, card);
        attachStoryEquipmentPreview(item, card);
        item.addEventListener('pointerenter', () => setStoryMechanicalTrackPaused(enemyId, true));
        item.addEventListener('pointerleave', () => setStoryMechanicalTrackPaused(enemyId, false));
        item.addEventListener('focus', () => setStoryMechanicalTrackPaused(enemyId, true));
        item.addEventListener('blur', () => setStoryMechanicalTrackPaused(enemyId, false));
        return item;
    }

    function renderStoryMechanicalTrack(portrait, enemy) {
        const cards = Array.isArray(enemy?.mechanical_track) ? enemy.mechanical_track : [];
        if (!portrait || !cards.length) return;
        const shell = document.createElement('div');
        shell.className = 'story-mechanical-track';
        shell.setAttribute('aria-label', lang === 'zh' ? '机械轨道' : 'Mechanical Track');
        const wheel = document.createElement('div');
        wheel.className = 'story-mechanical-track-wheel';
        wheel.dataset.enemyId = String(enemy.id || '');
        cards.forEach((card) => {
            const item = createStoryMechanicalTrackCard(card, enemy.id);
            if (item) wheel.append(item);
        });
        layoutStoryMechanicalTrackCards(wheel);
        const motion = storyMechanicalTrackMotion(enemy.id);
        motion.paused = false;
        motion.lastTimestamp = performance.now();
        wheel.style.setProperty('--story-mechanical-track-rotation', `${motion.angle.toFixed(3)}deg`);
        shell.append(wheel);
        portrait.append(shell);
        ensureStoryMechanicalTrackFrame();
    }

    function storyMechanicalTrackCardElement(enemyId, instanceId) {
        if (!instanceId) return null;
        return storyEnemyActor(enemyId)?.querySelector(
            `.story-mechanical-track-card[data-instance-id="${CSS.escape(String(instanceId))}"]`,
        ) || null;
    }

    function addStoryMechanicalTrackEventCard(event, placement = 'end') {
        const enemyId = String(event?.enemy_id || '');
        const actor = storyEnemyActor(enemyId);
        const wheel = actor?.querySelector('.story-mechanical-track-wheel');
        const instanceId = String(
            event?.card_instance_id || event?.source_card_instance_id
            || event?.track_card?.instance_id || '',
        );
        if (!wheel || !instanceId || storyMechanicalTrackCardElement(enemyId, instanceId)) return;
        const card = event?.track_card || {
            instance_id: instanceId,
            def_id: String(event?.def_id || ''),
            track_persistent: false,
        };
        const item = createStoryMechanicalTrackCard(card, enemyId);
        if (!item) return;
        item.classList.add('is-entering');
        if (placement === 'start') wheel.prepend(item);
        else wheel.append(item);
        layoutStoryMechanicalTrackCards(wheel);
        window.requestAnimationFrame(() => item.classList.remove('is-entering'));
    }

    function storyMechanicalTrackReducedMotion() {
        return Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
    }

    function animateStoryMechanicalTrackRotation(enemyId, motion, targetAngle, duration) {
        if (storyMechanicalTrackReducedMotion() || duration <= 1) {
            motion.angle = targetAngle;
            applyStoryMechanicalTrackMotion(enemyId, motion);
            return Promise.resolve();
        }
        const startAngle = Number(motion.angle || 0);
        const startedAt = performance.now();
        return new Promise((resolve) => {
            const step = (timestamp) => {
                const progress = Math.max(0, Math.min(1, (timestamp - startedAt) / duration));
                const eased = 1 - ((1 - progress) ** 3);
                motion.angle = startAngle + (targetAngle - startAngle) * eased;
                motion.lastTimestamp = timestamp;
                applyStoryMechanicalTrackMotion(enemyId, motion);
                if (progress < 1) window.requestAnimationFrame(step);
                else resolve();
            };
            window.requestAnimationFrame(step);
        });
    }

    async function settleStoryMechanicalTrackActivation(enemyId) {
        const key = storyMechanicalTrackMotionKey(enemyId);
        const active = storyActiveMechanicalTrackCards.get(key);
        if (!active) return;
        storyActiveMechanicalTrackCards.delete(key);
        const { item, wheel, event } = active;
        const motion = storyMechanicalTrackMotion(enemyId);
        const recycled = String(event?.presentation?.motion || '') === 'gain';
        const persistent = Boolean(event?.track_card?.track_persistent)
            || item?.dataset.trackPersistent === '1';
        item?.classList.remove('is-at-trigger');
        if (item?.isConnected && (recycled || !persistent)) {
            item.classList.add('is-leaving');
            await storySleep(storyMechanicalTrackReducedMotion() ? 1 : 150);
            item.remove();
            layoutStoryMechanicalTrackCards(wheel);
            await storySleep(storyMechanicalTrackReducedMotion() ? 1 : 130);
        } else if (item?.isConnected) {
            item.classList.remove('is-activating');
            wheel.append(item);
            layoutStoryMechanicalTrackCards(wheel);
            await storySleep(storyMechanicalTrackReducedMotion() ? 1 : 220);
        }
        item?.classList.remove('is-activating', 'is-leaving');
        wheel?.classList.remove('is-resolving');
        motion.animating = false;
        motion.lastTimestamp = performance.now();
    }

    async function settleAllStoryMechanicalTrackActivations() {
        const enemyIds = [...storyActiveMechanicalTrackCards.values()]
            .map((active) => String(active?.event?.enemy_id || ''))
            .filter(Boolean);
        await Promise.all(enemyIds.map((enemyId) => settleStoryMechanicalTrackActivation(enemyId)));
    }

    async function animateStoryMechanicalTrackActivation(event) {
        const enemyId = String(event?.enemy_id || '');
        const instanceId = String(
            event?.source_card_instance_id || event?.track_card?.instance_id || '',
        );
        if (!enemyId || !instanceId) return;
        await settleStoryMechanicalTrackActivation(enemyId);
        addStoryMechanicalTrackEventCard(event);
        const item = storyMechanicalTrackCardElement(enemyId, instanceId);
        const wheel = item?.closest('.story-mechanical-track-wheel');
        if (!item || !wheel) return;
        const motion = storyMechanicalTrackMotion(enemyId);
        advanceStoryMechanicalTrackMotion(motion);
        motion.animating = true;
        const cardAngle = Number(item.dataset.trackAngle || 0);
        const absoluteAngle = cardAngle + Number(motion.angle || 0);
        let delta = STORY_MECHANICAL_TRACK_TRIGGER_ANGLE - absoluteAngle;
        delta = ((delta + 540) % 360) - 180;
        const targetAngle = Number(motion.angle || 0) + delta;
        const duration = Math.max(300, Math.min(620, 280 + Math.abs(delta) * 1.7));
        wheel.classList.add('is-resolving');
        item.classList.add('is-activating');
        await animateStoryMechanicalTrackRotation(enemyId, motion, targetAngle, duration);
        item.classList.add('is-at-trigger');
        storyActiveMechanicalTrackCards.set(storyMechanicalTrackMotionKey(enemyId), {
            item,
            wheel,
            event,
        });
        await storySleep(storyMechanicalTrackReducedMotion() ? 1 : 110);
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
            toxic_poison: lang === 'zh' ? '剧毒' : 'Toxic Poison',
            stagnation: lang === 'zh' ? '滞留' : 'Stagnation',
            bleed: lang === 'zh' ? '流血' : 'Bleed',
            fire: lang === 'zh' ? '灼烧' : 'Burn',
            blockade: lang === 'zh' ? '封锁' : 'Blockade',
            attack_blocked: lang === 'zh' ? '禁攻' : 'Attack Blocked',
            fragment: lang === 'zh' ? '碎片' : 'Fragment',
            evil_eye: lang === 'zh' ? '邪眼' : 'Evil Eye',
            bulb: lang === 'zh' ? '灯泡' : 'Bulb',
            hard_shell: lang === 'zh' ? '坚硬' : 'Hard Shell',
            magic_reflection: lang === 'zh' ? '魔力反射' : 'Magic Reflection',
            disc: lang === 'zh' ? '圆盘' : 'Disc',
            toxic_pressure: lang === 'zh' ? '剧毒压力' : 'Toxic Pressure',
            magic: 'M',
        }[key] || (lang === 'zh' ? '特殊效果' : key.replaceAll('_', ' '));
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
            if (entry?.conditional === 'pearls') {
                label = lang === 'zh' ? `每颗珍珠 ${label}` : `${label} per Pearl`;
            }
            if (kind === 'self_damage') label = `${t.self} ${label}`;
        } else if (kind === 'heal') {
            iconUrl = STORY_INLINE_ICONS.H;
            label = entry?.full
                ? (lang === 'zh' ? '回满' : 'Full')
                : `+${amount}${entry?.percent ? '%' : ''}`;
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
            if (entry?.effect_type === 'delayed_hand_charge') {
                label = lang === 'zh'
                    ? `下回合手牌电荷 +${amount}`
                    : `Next turn hand Charge +${amount}`;
            } else if (entry?.effect_type === 'all_cards_charge') {
                label = lang === 'zh'
                    ? `所有牌电荷 +${amount}`
                    : `All cards gain ${amount} Charge`;
            } else if (entry?.effect_type === 'mechanical_track') {
                label = localize(entry?.label)
                    || (lang === 'zh' ? '触发机械轨道顶牌' : 'Resolve the top Mechanical Track card');
            } else {
                const cardName = localize(storyContent?.cards?.[entry?.card_id]?.name);
                label = cardName
                    ? (lang === 'zh'
                        ? `向抽牌堆加入${amount}张${cardName}`
                        : `Add ${amount} ${cardName} to the draw pile`)
                    : t.addCard;
            }
        } else if (kind === 'consume') {
            label = localize(entry?.label)
                || (lang === 'zh' ? '吞噬其他生物' : 'Consume other creatures');
        } else if (kind === 'consume_status') {
            label = lang === 'zh'
                ? `消耗${amount}层${storyIntentStatusLabel(entry.status)}`
                : `Consume ${amount} ${storyIntentStatusLabel(entry.status)}`;
        } else if (kind === 'resource') {
            label = `+${amount}${storyIntentStatusLabel(entry.resource)}`;
        } else {
            const effectType = String(entry?.effect_type || '');
            if (effectType === 'lose_max_health_percent') {
                label = lang === 'zh' ? `自身H上限-${amount}%` : `Own max H -${amount}%`;
            } else if (effectType === 'consume_pearls_damage') {
                label = lang === 'zh' ? `每颗珍珠造成${amount}D` : `${amount}D per Pearl`;
            } else {
                label = localize(entry?.label)
                    || String(entry?.summary || (lang === 'zh' ? '执行特殊行动' : 'Perform a special action'));
            }
        }
        const details = localize(entry?.details);
        if (details) label = `${label} · ${details}`;
        if (entry?.target === 'all_enemies') label = `${t.allies} · ${label}`;
        else if (entry?.target === 'player') label = `${t.playerSide || (lang === 'zh' ? '玩家方' : 'Player side')} · ${label}`;
        else if (entry?.target === 'named_enemy') {
            const targetName = localize(entry?.enemy_name) || (lang === 'zh' ? '指定生物' : 'Named creature');
            label = `${targetName} · ${label}`;
        } else if (entry?.target === 'lowest_ally_shield') {
            label = `${lang === 'zh' ? 'H最低的生物' : 'Lowest-H creature'} · ${label}`;
        } else if (entry?.target === 'adjacent_shield') {
            label = `${lang === 'zh' ? '相邻生物' : 'Adjacent creatures'} · ${label}`;
        }
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
        actor.classList.toggle(
            'has-mechanical-track',
            Array.isArray(enemy?.mechanical_track) && enemy.mechanical_track.length > 0,
        );
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
        renderStoryMechanicalTrack(portrait, enemy);

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
            { key: 'attack_blocked', label: '禁攻', value: combat.attack_blocked },
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

    function storyRoomFooterButton(label, onClick, options = {}) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `story-command${options.primary ? ' story-command-primary' : ''}`;
        if (options.primary) button.dataset.storyConfirmAction = '1';
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
                        ? `选择下一区域，随后进入第 ${floorStart}-${floorEnd} 层。`
                        : `Choose the next region, then enter Floors ${floorStart}-${floorEnd}.`)
                    : (lang === 'zh'
                        ? '选择下一区域，随后生成新的16层路线。'
                        : 'Choose the next region, then generate a new 16-floor route.'),
            );
            let selectedBiome = String(room.biomes?.[0] || 'garden');
            const selectionButtons = [];
            const refreshSelections = () => {
                selectionButtons.forEach(({ button, id }) => {
                    button.classList.toggle('is-selected', id === selectedBiome);
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
                selectionButtons.push({ button, id: String(biome) });
                container?.append(button);
            });
            refreshSelections();
            footer?.append(storyRoomFooterButton(
                t.confirm,
                () => storyAction('choose_stage', {
                    biome: selectedBiome,
                }),
                { primary: true },
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
                    id: 'shop-enchantment-books',
                    label: t.enchantmentBooks,
                    mode: 'choices',
                    render: (target) => {
                        const available = (room.enchantment_books || []).filter((item) => !item.sold);
                        if (!available.length) appendStoryRoomEmpty(target, t.codexEmpty);
                        available.forEach((item) => {
                            const tile = createStoryEnchantmentBookTile(
                                { book_id: item.book_id },
                                { actions: false },
                            );
                            const buy = document.createElement('button');
                            buy.type = 'button';
                            buy.className = 'story-command story-command-primary';
                            buy.textContent = `${t.claim} · ${Number(item.price || 0)}G`;
                            buy.disabled = Number(player.gold || 0) < Number(item.price || 0);
                            buy.addEventListener('click', () => chooseStoryEnchantmentBookReplacement(
                                (replaceId) => storyAction('resolve_room', {
                                    option: 'buy_enchantment_book',
                                    item_id: item.id,
                                    ...(replaceId ? { replace_book_instance_id: replaceId } : {}),
                                }),
                            ));
                            tile.append(buy);
                            target.append(tile);
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
                enchantment_book: Boolean(claims.enchantment_book) || !reward.enchantment_book,
            };
        }
        return {
            gold: true,
            card: !(reward?.cards || []).length,
            relic: !(reward?.relics || []).length && !reward?.relic,
            enchantment_book: !reward?.enchantment_book,
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
        if (reward.enchantment_book) {
            const bookDefinition = storyEnchantmentBookDefinition(reward.enchantment_book);
            if (claims.enchantment_book) {
                const claimedBook = storyEnchantmentBookDefinition(
                    reward.selected_enchantment_book_id || reward.enchantment_book,
                );
                claimContainer?.append(rewardClaimButton(
                    `${t.enchantmentBookReward} · ${localize(claimedBook?.name) || reward.enchantment_book}`,
                    reward.selected_enchantment_book_id ? t.claimed : t.skip,
                    true,
                    () => {},
                ));
            } else {
                const claimBook = rewardClaimButton(
                    `${t.enchantmentBookReward} · ${localize(bookDefinition?.name) || reward.enchantment_book}`,
                    localize(bookDefinition?.description),
                    false,
                    () => chooseStoryEnchantmentBookReplacement((replaceId) => storyAction(
                        'choose_reward',
                        {
                            reward_type: 'enchantment_book',
                            book_id: reward.enchantment_book,
                            ...(replaceId ? { replace_book_instance_id: replaceId } : {}),
                        },
                    )),
                );
                if (bookDefinition?.image_url) {
                    const image = document.createElement('img');
                    image.className = 'story-reward-book-image';
                    image.src = bookDefinition.image_url;
                    image.alt = '';
                    claimBook.prepend(image);
                }
                claimContainer?.append(claimBook);
            }
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
        const isMandatoryBossRushCard = reward.source === 'boss_rush_start_cards';
        const mustTakeCard = isMandatoryBossRushCard
            || (state?.player?.relics || []).includes('grab_every_card');
        skip?.classList.toggle('hidden', claims.card || mustTakeCard);
        const canContinue = Object.values(claims).every(Boolean);
        const continueButton = $('story-reward-continue');
        continueButton?.classList.toggle('hidden', !canContinue);
        if (continueButton) continueButton.disabled = !canContinue;
        const leaveButton = $('story-reward-leave');
        if (leaveButton) {
            leaveButton.textContent = t.directLeave;
            leaveButton.classList.toggle('hidden', canContinue || isMandatoryBossRushCard);
        }
        showView('story-reward');
    }

    function renderTerminal(state) {
        const complete = state.phase === 'complete';
        setText('story-terminal-mark', complete ? '✓' : '×');
        setText('story-terminal-title', complete ? t.journeyComplete : t.journeyFailed);
        setText('story-terminal-copy', complete ? t.journeyCompleteCopy : t.journeyFailedCopy);
        $('story-terminal-mark')?.classList.toggle('is-failure', !complete);
        setText('story-terminal-new', ({
            zh: '返回角色选择', en: 'Return to Character Select',
            fr: 'Retour au choix du personnage', ja: 'キャラクター選択へ戻る',
        })[lang] || '返回角色选择');
        showView('story-terminal');
    }

    function renderRun(run) {
        const scrollPositions = captureStoryScrollPositions();
        activeRun = run;
        renderStorySeededBackdrop(run);
        storyMapPreviewOpen = false;
        updateStoryStatusBar();
        updateStorySurrenderControl(run);
        if (window.__STORY_DEV_TOOLS__) {
            renderDeveloperPanel(run?.state || null, { syncValues: developerModeOpen });
        }
        if (!run) {
            selectedCombatCardId = '';
            renderStoryPersistentHud(null);
            destroyStoryCursorCard();
            $('story-aim-layer')?.classList.add('hidden');
            renderStoryCharacterOptions();
            showView('story-empty');
            restoreStoryScrollPositions(scrollPositions);
            return;
        }
        const incompatible = run.compatible === false
            || Boolean(contentVersion && run.content_version !== contentVersion);
        if (incompatible) {
            selectedCombatCardId = '';
            renderStoryPersistentHud(null);
            destroyStoryCursorCard();
            $('story-aim-layer')?.classList.add('hidden');
            $('story-hud-surrender')?.classList.add('hidden');
            const copy = {
                zh: '这段旅程不会被自动重置。结束旧旅程后，才能按当前内容版本开始新旅程。',
                en: 'This journey will not be reset automatically. End it explicitly before starting with the current content version.',
                fr: 'Ce voyage ne sera pas réinitialisé automatiquement. Terminez-le explicitement avant de commencer avec la version actuelle.',
                ja: 'この旅は自動的にリセットされません。現在の内容で始める前に、明示的に終了してください。',
            }[lang];
            setText('story-version-old-copy', copy);
            setText(
                'story-version-old-detail',
                `${run.content_version || '--'} → ${run.expected_content_version || contentVersion || '--'}`,
            );
            showView('story-version-old');
            restoreStoryScrollPositions(scrollPositions);
            return;
        }
        const state = run.state || {};
        renderStoryPersistentHud(run);
        const hasFloorCheckpoint = Boolean(state.floor_entry_checkpoint?.state);
        updateStoryManualSaveControls(run);
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
            renderRun(runPayload.run || null);
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
            const payload = await requestJson('/api/story/run', {
                method: 'POST',
                body: JSON.stringify({ character_id: selectedStoryCharacterId }),
            });
            ingestStoryDiscoveryPayload(payload);
            renderRun(payload.run || null);
        } catch (error) {
            if (error.message !== 'AUTH_REQUIRED') showToast(error.message);
        } finally {
            if (button) button.disabled = false;
        }
    }

    async function replaceLegacyRun() {
        if (!activeRun || !(
            activeRun.compatible === false
            || Boolean(contentVersion && activeRun.content_version !== contentVersion)
        )) return;
        const message = {
            zh: '确定结束这段旧版本旅程并开始新旅程吗？旧旅程会保留为已结束记录。',
            en: 'End this old-version journey and start a new one? The old journey remains as an ended record.',
            fr: 'Terminer cet ancien voyage et en commencer un nouveau ? L’ancien restera archivé comme terminé.',
            ja: '旧バージョンの旅を終了して新しい旅を始めますか？旧旅は終了記録として残ります。',
        }[lang];
        if (!window.confirm(message)) return;
        const button = $('story-version-old-restart');
        if (button) button.disabled = true;
        try {
            if (await abandonRun(false)) await startRun();
        } finally {
            if (storyContent) renderStoryCharacterOptions();
            else if (button) button.disabled = false;
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
            renderRun(null);
            if (!silent) showToast(t.mapReset);
        } catch (error) {
            if (error.message !== 'AUTH_REQUIRED') showToast(error.message);
        } finally {
            if (button) button.disabled = false;
        }
    }

    function storyManualSavePhaseIsStable(run = activeRun) {
        if (!run || run.compatible === false || !run.state) return false;
        if (contentVersion && run.content_version !== contentVersion) return false;
        return STORY_MANUAL_SAVE_STABLE_PHASES.has(String(run.state.phase || ''));
    }

    function storyStorePreference(key, value) {
        try {
            (window.GTN_STORAGE || window.localStorage)?.setItem(key, String(value));
        } catch (_) {}
    }

    function storySettingsStrings() {
        return ({
            zh: {
                title: '旅程设置', copy: '界面偏好仅影响当前设备。',
                fullscreenEnter: '进入全屏', fullscreenExit: '退出全屏',
                hideBorders: '隐藏界面与卡牌边框', speed: '2倍演出速度',
            },
            en: {
                title: 'Journey Settings', copy: 'Display preferences only affect this device.',
                fullscreenEnter: 'Enter Fullscreen', fullscreenExit: 'Exit Fullscreen',
                hideBorders: 'Hide UI and Card Borders', speed: '2× Presentation Speed',
            },
            fr: {
                title: 'Réglages du voyage', copy: "Les préférences d'affichage ne concernent que cet appareil.",
                fullscreenEnter: 'Plein écran', fullscreenExit: 'Quitter le plein écran',
                hideBorders: "Masquer les bordures de l'interface et des cartes", speed: 'Vitesse de présentation ×2',
            },
            ja: {
                title: '旅の設定', copy: '表示設定はこの端末にのみ適用されます。',
                fullscreenEnter: '全画面表示', fullscreenExit: '全画面を終了',
                hideBorders: 'UIとカードの枠を隠す', speed: '演出速度2倍',
            },
        })[lang] || null;
    }

    function updateStorySettingsControls(run = activeRun) {
        const copy = storySettingsStrings();
        if (copy) {
            setText('story-settings-title', copy.title);
            setText('story-settings-copy', copy.copy);
            setText(
                'story-settings-fullscreen-label',
                document.fullscreenElement ? copy.fullscreenExit : copy.fullscreenEnter,
            );
            setText('story-settings-hide-borders-label', copy.hideBorders);
            setText('story-settings-speed-label', copy.speed);
        }
    }

    function syncStorySettingsDraft() {
        const hideBorders = $('story-settings-hide-borders');
        if (hideBorders) {
            hideBorders.checked = document.documentElement.classList.contains('story-hide-card-borders');
        }
        const speed = $('story-settings-speed');
        if (speed) speed.checked = storyPlaybackRate === 2;
    }

    function openStorySettings() {
        if (!activeRun || actionInFlight || cardPlayInFlight) return;
        updateStorySettingsControls(activeRun);
        syncStorySettingsDraft();
        const dialog = $('story-settings-dialog');
        if (!dialog) return;
        dialog.returnValue = 'cancel';
        dialog.showModal();
    }

    async function toggleStoryFullscreen() {
        try {
            if (document.fullscreenElement) await document.exitFullscreen();
            else await document.documentElement.requestFullscreen();
        } catch (_) {
            showToast(lang === 'zh' ? '当前浏览器无法切换全屏' : 'Fullscreen is unavailable');
        } finally {
            updateStorySettingsControls(activeRun);
        }
    }

    function setStoryBordersHidden(hidden) {
        document.documentElement.classList.toggle('story-hide-card-borders', hidden);
        document.documentElement.classList.toggle('story-hide-ui-borders', hidden);
        storyStorePreference('gtn_story_hide_card_borders', hidden ? '1' : '0');
    }

    function setStoryPlaybackRate(fast) {
        storyPlaybackRate = fast ? 2 : 1;
        document.documentElement.classList.toggle('story-speed-2x', fast);
        storyStorePreference('gtn_story_speed_2x', fast ? '1' : '0');
    }

    function commitStorySettingsDraft() {
        setStoryBordersHidden(Boolean($('story-settings-hide-borders')?.checked));
        setStoryPlaybackRate(Boolean($('story-settings-speed')?.checked));
    }

    function storyManualSaveOperationBlocked(run = activeRun) {
        return (
            !storyManualSavePhaseIsStable(run)
            || actionInFlight
            || cardPlayInFlight
            || storyCombatEntranceAnimating
            || storyManualSaveInFlight
            || document.body.dataset.actionInFlight === 'true'
            || document.body.dataset.enemyAnimating === 'true'
        );
    }

    function updateStoryManualSaveControls(run = activeRun) {
        const blocked = storyManualSaveOperationBlocked(run);
        const hudButton = $('story-hud-save');
        const label = `${t.saveManager} · S ${Math.max(0, Number(run?.manual_save_count) || 0)} · L ${Math.max(0, Number(run?.manual_load_count) || 0)}`;
        setText('story-hud-save-label', label);
        if (hudButton) {
            hudButton.disabled = blocked;
            hudButton.title = label;
            hudButton.setAttribute('aria-label', label);
        }
        const createButton = $('story-save-create');
        if (createButton) createButton.disabled = blocked;
        document.querySelectorAll('.story-save-load').forEach((button) => {
            button.disabled = blocked;
        });
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

    function renderManualStorySaves(saves, allowLoad = !storyManualSaveOperationBlocked()) {
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
            const phase = String(save.phase || '');
            const phaseLabel = {
                journey_setup: t.rooms?.journey_setup,
                easy_relic: t.easyRelicTitle,
                blessing: t.rooms?.blessing,
                map: t.route,
                combat: t.rooms?.combat,
                room: t.room,
                reward: t.rewards,
                stage_choice: t.rooms?.stage_choice || t.room,
                complete: t.journeyComplete,
                game_over: t.journeyFailed,
            }[phase];
            summary.textContent = [
                `${t.stage} ${stateValue(save.stage)}`,
                t.floor(stateValue(save.floor)),
                phaseLabel,
            ].filter(Boolean).join(' · ');
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
        if (!activeRun) return;
        if (storyManualSaveOperationBlocked()) {
            showToast(t.saveOnlyOnMap);
            return;
        }
        const canRestart = Boolean(activeRun.state?.floor_entry_checkpoint?.state);
        $('story-save-create')?.classList.remove('hidden');
        $('story-restart-floor')?.classList.toggle('hidden', !canRestart);
        setText('story-save-copy', t.saveCopy);
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
            if (payload.run) activeRun = payload.run;
            renderManualStorySaves(payload.saves);
            updateStorySettingsControls(activeRun);
        } catch (error) {
            if (error.message !== 'AUTH_REQUIRED') showToast(error.message || t.requestFailed);
            renderManualStorySaves([], false);
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
        if (storyManualSaveOperationBlocked()) {
            showToast(t.saveOnlyOnMap);
            return;
        }
        storyManualSaveInFlight = true;
        updateStoryManualSaveControls();
        try {
            const payload = await requestJson('/api/story/run/save', {
                method: 'POST',
                body: JSON.stringify({
                    run_id: activeRun.id,
                    state_version: activeRun.state_version,
                }),
            });
            if (payload.run) activeRun = payload.run;
            renderManualStorySaves(payload.saves);
            updateStorySettingsControls(activeRun);
            showToast(t.saveSucceeded);
        } catch (error) {
            if (error.payload?.run) renderRun(error.payload.run);
            if (error.message !== 'AUTH_REQUIRED') showToast(error.message || t.requestFailed);
        } finally {
            storyManualSaveInFlight = false;
            updateStoryManualSaveControls();
        }
    }

    async function loadManualStorySave(saveId) {
        if (!saveId || storyManualSaveOperationBlocked()) {
            showToast(t.saveOnlyOnMap);
            return;
        }
        storyManualSaveInFlight = true;
        updateStoryManualSaveControls();
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
        } finally {
            storyManualSaveInFlight = false;
            updateStoryManualSaveControls();
        }
    }

    async function deleteManualStorySave(saveId) {
        if (!activeRun || !saveId || storyManualSaveInFlight) return;
        const button = $('story-save-delete-confirm');
        storyManualSaveInFlight = true;
        updateStoryManualSaveControls();
        if (button) button.disabled = true;
        try {
            const payload = await requestJson('/api/story/run/save/delete', {
                method: 'POST',
                body: JSON.stringify({
                    run_id: activeRun.id,
                    save_id: saveId,
                }),
            });
            renderManualStorySaves(payload.saves, false);
            showToast(t.saveDeleted);
        } catch (error) {
            if (error.payload?.saves) {
                renderManualStorySaves(error.payload.saves, false);
            }
            if (error.message !== 'AUTH_REQUIRED') showToast(error.message || t.requestFailed);
        } finally {
            storyManualSaveInFlight = false;
            updateStoryManualSaveControls();
            if (button) button.disabled = false;
        }
    }

    async function startNewJourney() {
        const button = $('story-terminal-new');
        if (button) button.disabled = true;
        await abandonRun(true);
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
                 + '.story-choice-screen:not(.hidden) [data-story-confirm-action="1"]:not(:disabled), '
                 + '.story-choice-screen:not(.hidden) .story-reward-actions button:not(:disabled), '
                 + '#story-room:not(.hidden) .story-room-footer button:not(:disabled), '
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

    function focusedStoryKeyboardItem(container = null) {
        if (
            storyKeyboardFocus
            && storyElementVisible(storyKeyboardFocus)
            && (!container || container.contains(storyKeyboardFocus))
        ) return storyKeyboardFocus;
        const active = document.activeElement;
        if (
            active
            && storyElementVisible(active)
            && (!container || container.contains(active))
            && storyKeyboardItems().includes(active)
        ) return active;
        return null;
    }

    function toggleFocusedStoryItem() {
        return activateStoryElement(focusedStoryKeyboardItem());
    }

    function confirmStorySurface() {
        const shortcutModal = $('modal');
        if (shortcutModal?.classList.contains('active')) {
            const primary = shortcutModal.querySelector(
                '.modal-buttons .btn-primary:not(:disabled), button:not(:disabled)',
            );
            if (activateStoryElement(primary)) return true;
            return activateStoryElement(focusedStoryKeyboardItem(shortcutModal));
        }
        const dialog = topmostStoryDialog();
        if (dialog) {
            const confirm = dialog.querySelector(
                '[value="confirm"]:not(:disabled), .story-command-primary:not(:disabled)',
            );
            if (activateStoryElement(confirm)) return true;
            // An incomplete selection must not turn Enter into another option toggle.
            if (dialog.querySelector('[value="confirm"], .story-command-primary')) return true;
            return activateStoryElement(focusedStoryKeyboardItem(dialog));
        }
        const explicitConfirm = document.querySelector(
            '.story-choice-screen:not(.hidden) [data-story-confirm-action="1"]:not(:disabled), '
            + '#story-reward-continue:not(.hidden):not(:disabled)',
        );
        if (activateStoryElement(explicitConfirm)) return true;
        const focused = focusedStoryKeyboardItem();
        if (focused && activateStoryElement(focused)) return true;
        const blockedConfirm = document.querySelector(
            '.story-choice-screen:not(.hidden) [data-story-confirm-action="1"], '
            + '#story-reward-continue:not(.hidden)',
        );
        if (blockedConfirm) return true;
        const card = selectedCombatCard(activeRun?.state);
        if (card && storyCursorCardMode(card)) {
            playSelectedCombatCard(cardTargetKind(card));
            return true;
        }
         const primary = document.querySelector(
             '.story-choice-screen:not(.hidden) [data-story-confirm-action="1"]:not(:disabled), '
             + '#story-reward-continue:not(.hidden):not(:disabled), '
             + '.story-choice-screen:not(.hidden) .is-primary:not(:disabled), '
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
            '.story-choice-screen:not(.hidden) [data-story-confirm-action="1"]:not(:disabled), '
            + '.story-choice-screen:not(.hidden) .is-primary:not(:disabled), '
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
            return confirmStorySurface();
        case 'toggle_focused':
            return toggleFocusedStoryItem();
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
        shouldOverrideNativeActivation(actionId) {
            if (actionId !== 'confirm') return false;
            const dialog = topmostStoryDialog();
            if (dialog?.querySelector('[value="confirm"], .story-command-primary')) return true;
            return Boolean(document.querySelector(
                '.story-choice-screen:not(.hidden) [data-story-confirm-action="1"], '
                + '#story-reward-continue:not(.hidden)',
            ));
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
        $('story-version-old-restart')?.addEventListener('click', replaceLegacyRun);
        if (window.__STORY_COOP_ACCESS__) {
            $('story-coop-entry')?.addEventListener('click', openCooperativeStoryPreview);
            $('story-coop-preview-dialog')?.addEventListener('close', closeStoryCoopLobby);
            $('story-coop-create')?.addEventListener('click', createStoryCoopParty);
            $('story-coop-join')?.addEventListener('click', joinStoryCoopParty);
            $('story-coop-rotate-invite')?.addEventListener('click', rotateStoryCoopInvite);
            $('story-coop-copy-invite')?.addEventListener('click', copyStoryCoopInvite);
            $('story-coop-start')?.addEventListener('click', startStoryCoopRun);
            $('story-coop-character-select')?.addEventListener('change', (event) => {
                selectedStoryCoopCharacterId = String(
                    event.currentTarget?.value || 'common_flower'
                );
                renderStoryCoopCharacterSelect();
            });
            $('story-coop-leave')?.addEventListener('click', leaveStoryCoopParty);
            $('story-coop-abandon')?.addEventListener('click', abandonStoryCoopRun);
            $('story-coop-enter-combat')?.addEventListener('click', openStoryCoopCombat);
            $('story-coop-combat-dialog')?.addEventListener('close', handleStoryCoopCombatClosed);
            $('story-coop-combat-close')?.addEventListener('click', closeStoryCoopCombat);
            $('story-coop-combat-refresh')?.addEventListener('click', () => {
                loadStoryCoopCombat().catch(() => {});
            });
            $('story-coop-combat-play-selected')?.addEventListener('click', confirmStoryCoopCombatCard);
            $('story-coop-combat-ready')?.addEventListener('click', readyStoryCoopCombatSeat);
            $('story-coop-stage-ready')?.addEventListener('click', readyStoryCoopStage);
            $('story-coop-rest-upgrade-confirm')?.addEventListener('click', confirmStoryCoopRestUpgrade);
            $('story-coop-shop-leave')?.addEventListener('click', leaveStoryCoopShop);
            $('story-coop-invite-input')?.addEventListener('input', updateStoryCoopControls);
            $('story-coop-invite-input')?.addEventListener('keydown', (event) => {
                if (event.key !== 'Enter' || event.isComposing) return;
                event.preventDefault();
                joinStoryCoopParty();
            });
        }
        $('story-end-turn')?.addEventListener('click', () => storyAction('end_turn'));
        $('story-codex-open')?.addEventListener('click', openStoryCodex);
        $('story-codex-close')?.addEventListener('click', closeStoryCodex);
        $('story-codex-back')?.addEventListener('click', returnStoryCodexHistory);
        $('story-codex-dialog')?.addEventListener('click', (event) => {
            if (event.target === event.currentTarget) closeStoryCodex();
        });
        document.querySelectorAll('[data-story-codex-mode]').forEach((tab) => {
            tab.addEventListener('click', () => {
                navigateStoryCodex(String(tab.dataset.storyCodexMode || 'cards'), '', {
                    push: false,
                });
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
        $('story-draw-pile')?.addEventListener('click', () => openStoryPile('draw'));
        $('story-discard-pile')?.addEventListener('click', () => openStoryPile('discard'));
        $('story-exile-pile')?.addEventListener('click', () => openStoryPile('exile'));
        $('story-hud-map')?.addEventListener('click', openStoryCombatMap);
        $('story-hud-deck')?.addEventListener('click', () => openStoryPile('deck'));
        $('story-hud-books')?.addEventListener('click', openStoryEnchantmentBooks);
        $('story-enchantment-books-close')?.addEventListener('click', () => {
            $('story-enchantment-books-dialog')?.close();
        });
        $('story-enchantment-books-dialog')?.addEventListener('click', (event) => {
            if (event.target === event.currentTarget) event.currentTarget.close();
        });
        $('story-hud-settings')?.addEventListener('click', openStorySettings);
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
            if (context.mode === 'enchantment_book') {
                setStoryCardChoiceRequired(false);
                if (event.target.returnValue !== 'confirm') return;
                if (selected.length < context.spec.minimum || selected.length > context.spec.maximum) return;
                storyAction('use_enchantment_book', {
                    book_instance_id: context.bookInstanceId,
                    selected_card_ids: selected,
                });
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
        $('story-hud-surrender')?.addEventListener('click', () => {
            if (actionInFlight || !activeRun) return;
            const dialog = $('story-surrender-dialog');
            if (!dialog) return;
            dialog.returnValue = 'cancel';
            dialog.showModal();
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
        $('story-hud-save')?.addEventListener('click', openManualStorySaves);
        $('story-settings-fullscreen')?.addEventListener('click', toggleStoryFullscreen);
        $('story-settings-dialog')?.addEventListener('click', (event) => {
            if (event.target === event.currentTarget) event.currentTarget.close('cancel');
        });
        $('story-settings-dialog')?.addEventListener('close', (event) => {
            if (event.target.returnValue === 'confirm') commitStorySettingsDraft();
            syncStorySettingsDraft();
            updateStorySettingsControls(activeRun);
        });
        document.addEventListener('fullscreenchange', () => updateStorySettingsControls(activeRun));
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
        $('story-term-dialog')?.addEventListener('wheel', handleStoryCardTermWheel, { passive: false });
        $('story-term-dialog')?.addEventListener('keydown', handleStoryCardTermKeydown);
        $('story-term-dialog')?.addEventListener('pointerdown', handleStoryCardTermPointerDown);
        $('story-term-dialog')?.addEventListener('pointerup', handleStoryCardTermPointerUp);
        $('story-term-dialog')?.addEventListener('pointercancel', () => {
            storyCardTermPointerStart = null;
        });
        $('story-term-dialog')?.addEventListener('close', (event) => {
            delete event.currentTarget.dataset.storyTermKey;
            delete event.currentTarget.dataset.storyTermUpgrade;
            clearStoryCardTermNavigation();
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
            const equipmentElement = event.target?.closest?.('.story-equipment')
                || event.target?.closest?.('.story-mechanical-track-card');
            const cardSourceElement = cardElement || equipmentElement;
            if (cardSourceElement?.dataset.storyBlind === '1') return;
            const card = cardSourceElement ? storyCardElementData.get(cardSourceElement) : null;
            if (card) {
                const termOptions = storyCardTermOptions.get(cardSourceElement);
                openStoryCardTermsFromElement(cardSourceElement, termOptions || {});
                return;
            }
        });
    }

    loadStoryMainFont();
    applyText();
    renderStoryPlayerIdentity();
    renderPlayerSkin();
    bind();
    startStoryChat();
    startStoryPresence();
    loadRun();
})();
