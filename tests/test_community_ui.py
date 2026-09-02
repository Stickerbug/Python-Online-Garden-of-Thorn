from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
OPS = (ROOT / 'templates' / 'community_ops.html').read_text(encoding='utf-8')
PUBLIC_JS = (ROOT / 'static' / 'js' / 'community.js').read_text(encoding='utf-8')
OPS_JS = (ROOT / 'static' / 'js' / 'community_ops.js').read_text(encoding='utf-8')
STYLE = (ROOT / 'static' / 'css' / 'style.css').read_text(encoding='utf-8')


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
    assert '.community-top-btn::before { --ui-icon-url: url("/static/assets/ui-icons/announcement.svg"); }' in STYLE


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
        'audit-list',
    )
    for item in required_ids:
        assert f'id="{item}"' in OPS
    for endpoint in (
        '/api/community/ops/workspace',
        '/api/community/ops/announcements',
        '/api/community/ops/polls',
    ):
        assert endpoint in OPS_JS
    assert "'X-Community-Ops-CSRF'" in OPS_JS
    assert '.innerHTML' not in OPS_JS


def test_ops_page_has_no_changelog_controls():
    assert 'announcement-changelog' not in OPS
    assert 'draft-list' not in OPS
    assert '更新日志草稿' not in OPS
    assert 'changelog_draft' not in OPS_JS
    assert '/api/community/ops/changelog-drafts/' not in OPS_JS


def test_new_announcements_and_polls_have_a_persistent_unread_dot():
    assert 'gtn_community_announcement_reads_v1' in PUBLIC_JS
    assert 'function pollReceipt(item)' in PUBLIC_JS
    assert '...polls.map(pollReceipt)' in PUBLIC_JS
    assert 'function updateAnnouncementBadge()' in PUBLIC_JS
    assert "button.classList.toggle('has-unread', hasUnread)" in PUBLIC_JS
    assert 'function markCommunityItemsRead()' in PUBLIC_JS
    assert '.community-top-btn.has-unread::after' in STYLE
