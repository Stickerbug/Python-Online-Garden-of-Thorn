from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (PROJECT_ROOT / 'templates' / 'story.html').read_text(encoding='utf-8')
SCRIPT = (PROJECT_ROOT / 'static' / 'js' / 'story.js').read_text(encoding='utf-8')
STYLES = (PROJECT_ROOT / 'static' / 'css' / 'story.css').read_text(encoding='utf-8')


def test_coop_lobby_template_contains_each_party_state_and_action():
    required_ids = {
        'story-coop-no-party',
        'story-coop-create',
        'story-coop-invite-input',
        'story-coop-join',
        'story-coop-forming',
        'story-coop-members',
        'story-coop-party-revision',
        'story-coop-invite-reveal',
        'story-coop-copy-invite',
        'story-coop-rotate-invite',
        'story-coop-start',
        'story-coop-character-select',
        'story-coop-character-help',
        'story-coop-leave',
        'story-coop-active',
        'story-coop-run-id',
        'story-coop-run-revision',
        'story-coop-run-status',
        'story-coop-enter-combat',
        'story-coop-abandon',
        'story-coop-combat-dialog',
        'story-coop-seeded-backdrop',
        'story-coop-combat-status',
        'story-coop-combat-revision',
        'story-coop-combat-sequence',
        'story-coop-combat-round',
        'story-coop-combat-turn',
        'story-coop-combat-players',
        'story-coop-combat-enemies',
        'story-coop-combat-hand',
        'story-coop-combat-event-list',
        'story-coop-combat-refresh',
        'story-coop-combat-play-selected',
        'story-coop-combat-ready',
        'story-coop-combat-close',
        'story-coop-combat-board',
        'story-coop-combat-events',
        'story-coop-setup-panel',
        'story-coop-setup-title',
        'story-coop-setup-options',
        'story-coop-setup-easy-note',
        'story-coop-opening-panel',
        'story-coop-opening-title',
        'story-coop-opening-options',
        'story-coop-opening-party-status',
        'story-coop-reward-panel',
        'story-coop-reward-options',
        'story-coop-reward-party-status',
        'story-coop-map-panel',
        'story-coop-map-options',
        'story-coop-map-party-status',
        'story-coop-rest-panel',
        'story-coop-rest-options',
        'story-coop-rest-deck',
        'story-coop-rest-upgrade-confirm',
        'story-coop-rest-party-status',
        'story-coop-chest-panel',
        'story-coop-chest-gold',
        'story-coop-chest-options',
        'story-coop-chest-party-status',
        'story-coop-shop-panel',
        'story-coop-shop-gold',
        'story-coop-shop-offers',
        'story-coop-shop-leave',
        'story-coop-shop-party-status',
        'story-coop-event-panel',
        'story-coop-event-title',
        'story-coop-event-description',
        'story-coop-event-options',
        'story-coop-event-party-status',
        'story-coop-complete-panel',
        'story-coop-complete-copy',
    }

    for element_id in required_ids:
        assert f'id="{element_id}"' in TEMPLATE
    assert '邀请码只在创建或轮换响应中显示一次' in TEMPLATE
    assert '此操作不可恢复' in TEMPLATE


def test_coop_lobby_script_keeps_the_declared_api_and_polling_contract():
    endpoints = {
        '/api/story/coop/party',
        '/api/story/coop/party/join',
        '/api/story/coop/party/leave',
        '/api/story/coop/party/start',
        '/api/story/coop/party/invite',
        '/api/story/coop/party/abandon',
    }

    for endpoint in endpoints:
        assert f"'{endpoint}'" in SCRIPT
    assert 'const STORY_COOP_PARTY_POLL_MS = 2500;' in SCRIPT
    assert 'if (window.__STORY_COOP_ACCESS__) {' in SCRIPT
    assert "Number(error?.status) === 409" in SCRIPT
    assert "addEventListener('close', closeStoryCoopLobby)" in SCRIPT
    assert "setText('story-coop-invite-code', '');" in SCRIPT
    assert 'storyCoopPartyLoadPromise' in SCRIPT
    assert 'character_id: selectedStoryCoopCharacterId' in SCRIPT
    assert "$('story-coop-character-select')?.addEventListener('change'" in SCRIPT
    assert '.story-coop-character-picker {' in STYLES


def test_coop_combat_uses_an_independent_authoritative_transport_namespace():
    combat_block = SCRIPT[
        SCRIPT.index('function storyCoopCombatDialogOpen()'):
        SCRIPT.index('function storyStatusText(')
    ]
    for forbidden in ('activeRun', 'renderRun(', 'renderCombat(', 'storyAction('):
        assert forbidden not in combat_block

    assert 'const STORY_COOP_COMBAT_POLL_MS = 1200;' in SCRIPT
    assert '`/api/story/coop/run/${encodeURIComponent(session.runId)}`' in combat_block
    assert '`/api/story/coop/run/${encodeURIComponent(session.runId)}/action`' in combat_block
    assert "$('story-coop-enter-combat')?.addEventListener('click', openStoryCoopCombat);" in SCRIPT
    assert "addEventListener('close', handleStoryCoopCombatClosed)" in SCRIPT
    assert "$('story-coop-combat-close')?.addEventListener('click', closeStoryCoopCombat);" in SCRIPT
    assert "$('story-coop-combat-refresh')?.addEventListener('click', () => {" in SCRIPT
    assert "$('story-coop-combat-play-selected')?.addEventListener('click', confirmStoryCoopCombatCard);" in SCRIPT
    assert "$('story-coop-combat-ready')?.addEventListener('click', readyStoryCoopCombatSeat);" in SCRIPT
    assert "$('story-coop-rest-upgrade-confirm')?.addEventListener('click', confirmStoryCoopRestUpgrade);" in SCRIPT
    assert "$('story-coop-shop-leave')?.addEventListener('click', leaveStoryCoopShop);" in SCRIPT
    assert 'payload: cloneStoryCoopActionPayload(payload)' in combat_block
    assert "typeof structuredClone === 'function'" in combat_block
    assert "storyCoopCombatAction('reward_choose'" in combat_block
    assert "storyCoopCombatAction('map_vote'" in combat_block
    assert "storyCoopCombatAction('room_choose'" in combat_block
    assert "storyCoopCombatAction('shop_buy'" in combat_block
    assert "storyCoopCombatAction('setup_start'" in combat_block
    assert "storyCoopCombatAction('opening_choose'" in combat_block
    assert "if (combatAction) {" in combat_block
    assert "body.combat_id =" in combat_block
    assert "body.combat_round =" in combat_block


def test_coop_opening_setup_is_leader_only_and_uses_server_difficulties():
    combat_block = SCRIPT[
        SCRIPT.index('function storyCoopCombatDialogOpen()'):
        SCRIPT.index('function storyStatusText(')
    ]
    setup_block = SCRIPT[
        SCRIPT.index('function renderStoryCoopSetup('):
        SCRIPT.index('function renderStoryCoopOpening(')
    ]
    setup_action_start = setup_block.index("storyCoopCombatAction('setup_start', {")
    setup_action_end = setup_block.index('                });', setup_action_start) + len('                });')
    setup_action = setup_block[setup_action_start:setup_action_end]

    assert "new Set(['normal', 'hard', 'lunatic'])" in combat_block
    assert 'Number(snapshot.viewer_seat) === Number(snapshot.party?.leader_seat)' in combat_block
    assert "snapshot?.phase === 'journey_setup'" in combat_block
    assert "['normal', 'hard', 'lunatic'].forEach" in setup_block
    assert 'if (!viewerIsLeader)' in setup_block
    assert '正在等待队长选择花园难度。' in setup_block
    assert '标准花园路线、奖励和敌人强度。' in setup_block
    assert '危险路线更多；奖励金币为普通难度的75%；商店价格为110%。' in setup_block
    assert '继承困难规则；敌人H和伤害提升至125%。' in setup_block
    assert '简单难度及其专属开局天赋尚未接入协作故事' in TEMPLATE
    assert 'difficulty' in setup_action
    for forbidden in ('actor_seat:', 'actor_user_id:', 'health:', 'gold:', 'amount:', 'price:'):
        assert forbidden not in setup_action
    assert "normalizedType === 'setup_start'" in combat_block
    assert "$('story-coop-setup-panel')?.classList.toggle('hidden', !inSetup);" in combat_block


def test_coop_opening_blessing_renders_only_viewer_options_and_identifier_payload():
    combat_block = SCRIPT[
        SCRIPT.index('function storyCoopCombatDialogOpen()'):
        SCRIPT.index('function storyStatusText(')
    ]
    opening_block = SCRIPT[
        SCRIPT.index('function renderStoryCoopOpening('):
        SCRIPT.index('function renderStoryCoopReward(')
    ]
    opening_action_start = opening_block.index("storyCoopCombatAction('opening_choose', {")
    opening_action_end = opening_block.index('                });', opening_action_start) + len('                });')
    opening_action = opening_block[opening_action_start:opening_action_end]

    assert "String(room?.type || '') !== 'opening'" in combat_block
    assert "String(roomState?.stage || '') !== 'blessing'" in combat_block
    assert '(Array.isArray(roomState.options) ? roomState.options : [])' in opening_block
    assert 'snapshot?.players' not in opening_block
    assert 'storyContent?.blessings?.[optionId]' in opening_block
    assert '(Array.isArray(roomState.options) ? roomState.options : []).forEach' in opening_block
    assert "['max_health', 'rare_card', 'gold', 'wealth_and_basics'].forEach" not in opening_block
    assert 'const contentName = localize(definition.name);' in opening_block
    assert 'const contentDescription = localize(definition.description);' in opening_block
    assert 'title.textContent = contentName || contentDescription || optionId;' in opening_block
    assert '最大生命值+15' not in opening_block
    assert "renderStoryCoopRoomPartyStatuses('story-coop-opening-party-status'" in opening_block
    assert "room_id: String(current.room_id || '')" in opening_action
    assert 'option_id: optionId' in opening_action
    for forbidden in ('actor_seat:', 'actor_user_id:', 'health:', 'gold:', 'amount:', 'effect:'):
        assert forbidden not in opening_action
    assert "normalizedType === 'opening_choose'" in combat_block
    assert "$('story-coop-opening-panel')?.classList.toggle('hidden', !inOpening);" in combat_block
    assert "$('story-coop-combat-board')?.classList.toggle('hidden', !inCombat);" in combat_block
    assert '.story-coop-opening-options { grid-template-columns: repeat(2, minmax(0, 1fr)); }' in STYLES


def test_coop_combat_polling_and_actions_keep_epoch_and_idempotency_guards():
    combat_block = SCRIPT[
        SCRIPT.index('function storyCoopCombatDialogOpen()'):
        SCRIPT.index('function storyStatusText(')
    ]
    assert 'if (session.loadPromise) return session.loadPromise;' in combat_block
    assert '&& !session.loadPromise' in combat_block
    assert combat_block.count('session !== storyCoopCombatSession') >= 5
    assert combat_block.count('session.epoch !== epoch') >= 4
    assert 'const body = {' in combat_block
    assert combat_block.index('const body = {') < combat_block.index('for (let attempt = 0; attempt < 2; attempt += 1)')
    assert combat_block.count('action_id: storyCoopCombatActionId()') == 1
    assert '!Number.isFinite(status)' in combat_block
    assert 'session.notice = {' in combat_block
    assert 'if (session.notice)' in combat_block
    assert '.story-coop-combat-hand .story-card.is-pending-play' in STYLES
    assert '.story-coop-progression-choice:focus-visible' in STYLES
    assert '.story-coop-progression-options { grid-template-columns: 1fr;' in STYLES


def test_coop_combat_reuses_card_motion_without_exposing_private_card_ids():
    combat_block = SCRIPT[
        SCRIPT.index('function storyCoopCombatDialogOpen()'):
        SCRIPT.index('function storyStatusText(')
    ]
    assert 'async function playStoryCoopActionPresentation(events, body, previousSnapshot)' in combat_block
    assert "eventType === 'coop_card_played'" in combat_block
    assert "eventType === 'coop_card_discarded'" in combat_block
    assert "eventType === 'coop_cards_drawn'" in combat_block
    assert 'body?.payload?.card_instance_id' in combat_block
    assert 'await playStoryCoopActionPresentation(result.events, body, snapshot);' in combat_block
    assert 'await animateStoryCardFlight(' in combat_block
    assert 'async function animateStoryCardPlayed(event)' in SCRIPT
    assert SCRIPT.count('async function animateStoryCardFlight(') == 1
    assert combat_block.index('await playStoryCoopActionPresentation(') < combat_block.index('storyCoopCombatApplyRun(session, result.run, true);')
    assert 'button.dataset.instanceId = instanceId;' in combat_block
    assert "button.dataset.enemyId = String(enemy.id || '');" in combat_block


def test_coop_terminal_rendering_uses_the_authoritative_phase_not_completed_status():
    combat_block = SCRIPT[
        SCRIPT.index('function storyCoopCombatDialogOpen()'):
        SCRIPT.index('function storyStatusText(')
    ]
    assert "const complete = phase === 'complete';" in combat_block
    assert "const stageComplete = phase === 'stage_complete';" in combat_block
    assert "const failed = phase === 'game_over' || combat?.outcome === 'defeat';" in combat_block
    assert "complete = phase === 'complete' ||" not in combat_block
    assert "'协作旅程失败'" in combat_block
    assert '`协作第${Math.max(1, Number(snapshot?.stage) || 1)}阶段完成`' in combat_block
    assert "['complete', 'game_over'].includes" in combat_block
    assert "['complete', 'stage_complete', 'game_over'].includes" not in combat_block
    assert "normalizedType === 'stage_ready' && storyCoopStageCanReady(session)" in combat_block
    assert "storyCoopCombatAction('stage_ready'" in combat_block
    assert 'id="story-coop-stage-ready"' in TEMPLATE
    assert 'incomingRevision > Number(session.notice.runRevision || 0)' in combat_block
    assert "incomingPhase !== String(session.notice.phase || '')" in combat_block


def test_coop_reward_and_route_views_keep_personal_choices_private():
    combat_block = SCRIPT[
        SCRIPT.index('function storyCoopCombatDialogOpen()'):
        SCRIPT.index('function storyStatusText(')
    ]
    assert 'snapshot?.reward?.status === \'pending\'' in combat_block
    assert 'snapshot?.map_vote?.seats?.find(' in combat_block
    assert 'reward_id: String(reward.reward_id || \'\')' in combat_block
    assert 'vote_id: String(vote?.vote_id || \'\')' in combat_block
    assert 'node_id: nodeId' in combat_block
    assert 'item?.submitted' in combat_block
    assert 'item?.resolved' in combat_block
    for forbidden in ('votes_by_seat', 'rng_streams', 'selected_card_id: leader'):
        assert forbidden not in combat_block


def test_coop_rest_room_uses_only_the_viewer_deck_and_shared_action_transport():
    combat_block = SCRIPT[
        SCRIPT.index('function storyCoopCombatDialogOpen()'):
        SCRIPT.index('function storyStatusText(')
    ]
    rest_block = SCRIPT[
        SCRIPT.index('function renderStoryCoopRest('):
        SCRIPT.index('function renderStoryCoopChest(')
    ]
    upgrade_block = SCRIPT[
        SCRIPT.index('function confirmStoryCoopRestUpgrade()'):
        SCRIPT.index('function openStoryCoopCombat()')
    ]

    assert "snapshot?.phase !== 'room'" in combat_block
    assert "!['rest', 'chest', 'shop', 'event'].includes(roomType)" in combat_block
    assert '(expectedType && roomType !== expectedType)' in combat_block
    assert "String(roomState?.type || '') !== roomType" in combat_block
    assert "roomState.status === 'pending'" in combat_block
    assert '(Array.isArray(roomState.deck) ? roomState.deck : [])' in rest_block
    assert 'snapshot?.players' not in rest_block
    assert '!card?.upgraded && Number(card?.upgrade_level || 0) <= 0' in combat_block
    assert "addAction('heal'" in rest_block
    assert "addAction('leave'" in rest_block
    assert "storyCoopCombatAction('room_choose', {" in combat_block
    assert "room_id: String(roomState.room_id || '')" in combat_block
    assert "choice: 'upgrade'" in combat_block
    assert "card_instance_id: String(card.instance_id || '')" in combat_block
    for forbidden in ('actor_seat:', 'actor_user_id:', 'amount:', 'health:', 'upgrade_level:'):
        assert forbidden not in rest_block
        assert forbidden not in upgrade_block
    assert '.story-coop-rest-deck .story-card.is-selected-upgrade' in STYLES
    assert '.story-coop-rest-layout { grid-template-columns: 1fr;' in STYLES


def test_coop_chest_and_shop_render_only_viewer_private_values_and_identifier_payloads():
    combat_block = SCRIPT[
        SCRIPT.index('function storyCoopCombatDialogOpen()'):
        SCRIPT.index('function storyStatusText(')
    ]
    chest_block = SCRIPT[
        SCRIPT.index('function renderStoryCoopChest('):
        SCRIPT.index('function renderStoryCoopShop(')
    ]
    shop_block = SCRIPT[
        SCRIPT.index('function renderStoryCoopShop('):
        SCRIPT.index('function renderStoryCoopCombat()')
    ]
    room_action_start = combat_block.index("return storyCoopCombatAction('room_choose', {")
    room_action_end = combat_block.index('        });', room_action_start) + len('        });')
    room_action = combat_block[room_action_start:room_action_end]
    shop_action_start = shop_block.index("storyCoopCombatAction('shop_buy', {")
    shop_action_end = shop_block.index('                });', shop_action_start) + len('                });')
    shop_action = shop_block[shop_action_start:shop_action_end]

    assert "storyCoopRoomState(session, 'chest')" in combat_block
    assert "storyCoopRoomState(session, 'shop')" in combat_block
    assert "Math.floor(Number(roomState.gold) || 0)" in chest_block
    assert "addChoice('claim_gold'" in chest_block
    assert "'claim_relic'" in chest_block
    assert 'storyContent?.relics?.[relicId]' in chest_block
    assert "addChoice('leave'" in chest_block
    assert "chooseStoryCoopRoomOption(session, 'chest', choice)" in chest_block
    assert 'snapshot?.players' not in chest_block
    assert '(Array.isArray(roomState.offers) ? roomState.offers : [])' in shop_block
    assert "const viewerGold = Math.max(0, Math.floor(Number(roomState.gold) || 0));" in shop_block
    assert "const purchased = status === 'purchased';" in shop_block
    assert "const available = status === 'available';" in shop_block
    assert 'const affordable = validPrice && viewerGold >= price;' in shop_block
    assert 'disabled: !canBuy || !available || !affordable' in shop_block
    assert "kind === 'relic'" in shop_block
    assert 'story-coop-shop-relic' in shop_block
    assert "String(currentOffer?.status || '') !== 'available'" in shop_block
    assert 'currentGold < currentPrice' in shop_block
    assert 'snapshot?.players' not in shop_block
    assert "normalizedType === 'shop_buy'" in combat_block
    assert 'storyCoopShopCanBuy(session)' in combat_block
    assert "chooseStoryCoopRoomOption(storyCoopCombatSession, 'shop', 'leave')" in combat_block
    assert "room_id: String(roomState.room_id || '')" in room_action
    assert 'choice: normalizedChoice' in room_action
    assert "room_id: String(current.room_id || '')" in shop_action
    assert "offer_id: String(currentOffer.offer_id || '')" in shop_action
    for forbidden in ('actor_seat:', 'actor_user_id:', 'price:', 'card_id:', 'gold:', 'amount:'):
        assert forbidden not in room_action
        assert forbidden not in shop_action
    assert '.story-coop-shop-offers .story-card.is-purchased' in STYLES
    assert '.story-coop-shop-offers .story-coop-shop-relic.is-purchased' in STYLES
    assert '.story-coop-private-room-layout { grid-template-columns: 1fr;' in STYLES


def test_coop_route_copy_covers_noncombat_nodes():
    assert '投票选择下一个路线节点' in TEMPLATE
    assert '路线可能通往战斗、休息处、宝箱、商店或事件' in TEMPLATE
    assert "chest: '宝箱节点'" in SCRIPT
    assert "shop: '商店节点'" in SCRIPT
    assert '请选择你希望进入的下一个路线节点。' in SCRIPT
    assert 'STORY_MAP_ROOM_ICON_URLS[routeType]' in SCRIPT
    assert "routeType === 'chest' ? '🎁'" in SCRIPT
    assert 'id.textContent = nodeId' not in SCRIPT
    assert '.story-coop-map-choice-icon' in STYLES


def test_coop_event_uses_public_copy_and_submission_status_without_leaking_votes():
    combat_block = SCRIPT[
        SCRIPT.index('function storyCoopCombatDialogOpen()'):
        SCRIPT.index('function storyStatusText(')
    ]
    event_block = SCRIPT[
        SCRIPT.index('function renderStoryCoopEvent('):
        SCRIPT.index('function renderStoryCoopCombat()')
    ]
    room_action_start = combat_block.index("return storyCoopCombatAction('room_choose', {")
    room_action_end = combat_block.index('        });', room_action_start) + len('        });')
    room_action = combat_block[room_action_start:room_action_end]

    assert "storyCoopRoomState(session, 'event')" in combat_block
    assert "roomState?.title || snapshot?.room?.title" in event_block
    assert "roomState?.description || snapshot?.room?.description" in event_block
    assert 'roomState?.option_definitions' in event_block
    assert 'definitions.forEach((definition)' in event_block
    assert 'localize(definition?.label) || choice' in event_block
    assert 'localize(definition?.description)' in event_block
    assert 'definition?.risky' in event_block
    assert 'definition?.requires_confirmation' in event_block
    assert "String(currentRoom?.room_id || '') !== targetRoomId" in event_block
    assert "Number(session?.run?.revision || 0) !== targetRevision" in event_block
    assert "title: '修整工具'" not in event_block
    assert "['mend', 'supplies', 'risk'].forEach" not in event_block
    assert "chooseStoryCoopRoomOption(session, 'event', choice)" in event_block
    assert 'Boolean(item?.submitted ?? item?.resolved)' in combat_block
    assert "renderStoryCoopRoomPartyStatuses('story-coop-event-party-status'" in event_block
    assert 'selected_option' not in event_block
    assert 'votes_by_seat' not in event_block
    assert 'item?.choice' not in event_block
    for forbidden in ('actor_seat:', 'actor_user_id:', 'health:', 'gold:', 'amount:', 'effect:'):
        assert forbidden not in room_action
    assert '.story-coop-event-options .story-coop-progression-choice.is-risk' in STYLES
    assert "case 'coop_event_vote_cast':" in combat_block
    assert "case 'coop_event_consensus_required':" in combat_block
    assert "case 'coop_event_resolved':" in combat_block
    assert 'storyContent?.events?.[String(event.content_id' in combat_block
    assert "case 'coop_stage_completed':" in combat_block
    assert '只有选择一致时才会结算' in TEMPLATE
    assert "lastEventType === 'coop_event_consensus_required'" in combat_block


def test_coop_player_facing_hud_uses_progress_labels_and_collapsible_party_hands():
    combat_block = SCRIPT[
        SCRIPT.index('function storyCoopCombatDialogOpen()'):
        SCRIPT.index('function storyStatusText(')
    ]

    assert '<dt>旅程进度</dt><dd id="story-coop-combat-revision">' in TEMPLATE
    assert '<dt>难度</dt><dd id="story-coop-combat-sequence">' in TEMPLATE
    assert '<dt>当前步骤</dt><dd id="story-coop-combat-turn">' in TEMPLATE
    assert 'id="story-coop-combat-eyebrow"' in TEMPLATE
    assert "setText('story-coop-combat-eyebrow', `双人协作 · ${biomeLabel}`);" in SCRIPT
    assert 'storyCoopProgressLabel(snapshot)' in combat_block
    assert 'storyCoopSnapshotDifficultyLabel(snapshot)' in combat_block
    assert 'storyCoopPhaseLabel(snapshot)' in combat_block
    assert "['opening', 'rest', 'chest', 'shop', 'event'].includes(roomType)" in combat_block
    assert "document.createElement('details')" in combat_block
    assert 'story-coop-combat-enemy-image' in combat_block
    assert '.story-coop-combat-enemy-image' in STYLES
    assert '.story-coop-combat-shell > * { flex: 0 0 auto; }' in STYLES
    assert "return `队伍路线已确定，前往${storyCoopProgressLabel(snapshot)}`;" in combat_block
    assert "String(event.node_id || '未知节点')" not in combat_block


def test_coop_lobby_explains_player_decisions_without_internal_contract_jargon():
    assert '<dt>队伍人数</dt><dd id="story-coop-mvp-value">' in TEMPLATE
    assert '<dt>共同决定</dt><dd id="story-coop-schema-value">路线 / 事件</dd>' in TEMPLATE
    assert '<dt>共同承担</dt><dd>战斗结果</dd>' in TEMPLATE
    assert '<dt>个人决定</dt><dd id="story-coop-max-value">奖励 / 休息 / 宝箱 / 商店</dd>' in TEMPLATE
    assert '<dt>状态结构</dt>' not in TEMPLATE
    assert '<dt>目标人数</dt>' not in TEMPLATE
    assert '正在同步权威战斗状态' not in TEMPLATE
    assert '权威状态已同步' not in SCRIPT


def test_lobby_close_reopen_invalidates_old_confirmations_and_loads():
    assert 'const confirmationEpoch = storyCoopLobbyEpoch;' in SCRIPT
    assert 'storyCoopLobbyEpoch === confirmationEpoch' in SCRIPT
    assert "String(storyCoopPartyBundle.party?.id || '') === confirmationPartyId" in SCRIPT
    assert 'Number(storyCoopPartyBundle.party?.revision || 0) === confirmationRevision' in SCRIPT
    assert 'if (storyCoopPartyLoadEpoch === requestedEpoch) return storyCoopPartyLoadPromise;' in SCRIPT


def test_destructive_confirmations_keep_the_pre_confirm_party_revision():
    assert 'function storyCoopPartyMutationTarget()' in SCRIPT
    assert SCRIPT.count('const target = storyCoopPartyMutationTarget();') == 3
    assert "'/api/story/coop/party/invite',\n            target," in SCRIPT
    assert "'/api/story/coop/party/leave',\n            target," in SCRIPT
    assert "'/api/story/coop/party/abandon',\n            target," in SCRIPT


def test_single_player_story_start_contract_is_unchanged():
    assert 'id="story-start"' in TEMPLATE
    assert "$('story-start')?.addEventListener('click', startRun);" in SCRIPT
