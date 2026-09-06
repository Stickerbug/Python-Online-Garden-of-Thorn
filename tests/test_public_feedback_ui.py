from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
TEMPLATE = (ROOT / 'templates' / 'feedback_center.html').read_text(encoding='utf-8')
JS = (ROOT / 'static' / 'js' / 'feedback_center.js').read_text(encoding='utf-8')
CSS = (ROOT / 'static' / 'css' / 'feedback_center.css').read_text(encoding='utf-8')


def test_main_page_opens_feedback_center_in_new_tab():
    assert 'id="btn-public-feedback-center"' in INDEX
    assert 'href="/feedback-center"' in INDEX
    assert 'target="_blank"' in INDEX
    assert '/static/js/public_feedback.js' not in INDEX
    assert '/static/css/public_feedback.css' not in INDEX


def test_standalone_page_has_all_surfaces_and_account_bar():
    for marker in (
        '<title>反馈中心 · 荆棘花园</title>',
        'class="fc-topbar"',
        'id="fc-account"',
        'id="fc-account-popover"',
        'id="fc-tab-bug"',
        'id="fc-tab-suggestion"',
        'id="fc-status-filter"',
        'id="fc-issue-list"',
        'id="fc-detail"',
        'class="fc-split"',
        'class="fc-issue-pane"',
        'class="fc-detail-pane"',
        'id="fc-search"',
        'id="fc-create-dialog"',
        'id="fc-report-dialog"',
        '/static/js/feedback_center.js',
        '/static/css/feedback_center.css',
    ):
        assert marker in TEMPLATE
    assert (ROOT / 'static' / 'js' / 'feedback_center.js').is_file()
    assert (ROOT / 'static' / 'css' / 'feedback_center.css').is_file()


def test_standalone_client_uses_all_core_endpoints():
    for endpoint in (
        '/api/auth/me',
        '/api/public-feedback/summary',
        '/api/public-feedback/issues?',
        '/api/public-feedback/issues/${',
        '/api/public-feedback/comments/',
        '/api/public-feedback/admin/issues/',
        '/api/report',
    ):
        assert endpoint in JS
    assert 'data-open-issue' in JS
    assert 'data-action' in JS
    assert 'fc-skin-avatar' in JS
    assert 'toggleAccountPopover' in JS
    assert "loadNotifications" in JS
    assert '.fc-skin-avatar' in CSS
