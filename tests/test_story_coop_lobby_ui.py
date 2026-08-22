from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (PROJECT_ROOT / 'templates' / 'story.html').read_text(encoding='utf-8')
SCRIPT = (PROJECT_ROOT / 'static' / 'js' / 'story.js').read_text(encoding='utf-8')


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
        'story-coop-leave',
        'story-coop-active',
        'story-coop-run-id',
        'story-coop-run-revision',
        'story-coop-run-status',
        'story-coop-abandon',
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


def test_destructive_confirmations_keep_the_pre_confirm_party_revision():
    assert 'function storyCoopPartyMutationTarget()' in SCRIPT
    assert SCRIPT.count('const target = storyCoopPartyMutationTarget();') == 3
    assert "'/api/story/coop/party/invite',\n            target," in SCRIPT
    assert "'/api/story/coop/party/leave',\n            target," in SCRIPT
    assert "'/api/story/coop/party/abandon',\n            target," in SCRIPT


def test_single_player_story_start_contract_is_unchanged():
    assert 'id="story-start"' in TEMPLATE
    assert "$('story-start')?.addEventListener('click', startRun);" in SCRIPT
