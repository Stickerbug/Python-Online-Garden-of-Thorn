from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
OPS = (ROOT / 'templates' / 'community_ops.html').read_text(encoding='utf-8')
PUBLIC_JS = (ROOT / 'static' / 'js' / 'community.js').read_text(encoding='utf-8')
OPS_JS = (ROOT / 'static' / 'js' / 'community_ops.js').read_text(encoding='utf-8')


def test_main_page_has_public_announcement_and_poll_surface():
    required = (
        'id="btn-community-top"',
        'id="community-popover"',
        'id="community-feed"',
        'id="community-manage-link"',
        '/static/assets/ui-icons/announcement.svg',
        '/static/js/community.js',
        '/static/css/community.css',
    )
    for marker in required:
        assert marker in INDEX
    assert (ROOT / 'static' / 'assets' / 'ui-icons' / 'announcement.svg').is_file()


def test_public_client_uses_safe_dom_and_private_vote_results_contract():
    assert "requestJson('/api/community/feed')" in PUBLIC_JS
    assert "'X-Community-CSRF': state.csrfToken" in PUBLIC_JS
    assert "item.effective_state === 'closed'" in PUBLIC_JS
    assert "option.vote_count" in PUBLIC_JS
    assert 'textContent' in PUBLIC_JS
    assert '.innerHTML' not in PUBLIC_JS


def test_ops_page_and_client_cover_all_operations():
    required_ids = (
        'announcement-create-form',
        'poll-create-form',
        'announcement-list',
        'poll-list',
        'draft-list',
        'audit-list',
    )
    for item in required_ids:
        assert f'id="{item}"' in OPS
    for endpoint in (
        '/api/community/ops/workspace',
        '/api/community/ops/announcements',
        '/api/community/ops/polls',
        '/api/community/ops/changelog-drafts/',
    ):
        assert endpoint in OPS_JS
    assert "'X-Community-Ops-CSRF'" in OPS_JS
    assert '.innerHTML' not in OPS_JS


def test_runtime_changelog_sync_is_explicitly_draft_only():
    assert '需人工整理进 CHANGELOG.txt' in OPS
    assert '网页不会改写仓库文件' in OPS
