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
        'id="fc-tab-appeal"',
        'id="fc-status-filter"',
        'id="fc-issue-list"',
        'id="fc-detail"',
        'class="fc-split"',
        'class="fc-issue-pane"',
        'class="fc-detail-pane"',
        'id="fc-search"',
        'id="fc-create-dialog"',
        'id="fc-report-dialog"',
        'id="fc-appeal-pane"',
        'id="feedback-thread-list"',
        'id="feedback-message-list"',
        'id="btn-feedback-send"',
        '/static/js/feedback_center.js',
        '/static/css/feedback_center.css',
    ):
        assert marker in TEMPLATE
    assert (ROOT / 'static' / 'js' / 'feedback_center.js').is_file()
    assert (ROOT / 'static' / 'css' / 'feedback_center.css').is_file()


def test_admin_appeal_chat_lives_in_feedback_center_and_home_links_to_it():
    # 「管理员/申诉」对话整体迁入反馈中心；主页不再有独立反馈入口，
    # 工具行只留「反馈中心」与「关于」两个按钮。
    assert 'id="btn-open-feedback"' not in INDEX
    assert 'id="feedback-modal"' not in INDEX
    assert 'id="feedback-thread-list"' not in INDEX
    assert 'id="btn-public-feedback-center"' in INDEX
    assert 'id="btn-open-about"' in INDEX
    # 关联申诉回到主页信誉弹窗内嵌表单（不再走反馈中心）。
    assert 'id="integrity-appeal-form"' in INDEX
    assert 'id="integrity-appeal-link"' not in INDEX
    # 反馈中心承担对话 UI：路由、线程/消息/提交端点与视图渲染。
    assert "/feedback-center/appeal" in JS
    assert '/api/feedback/threads' in JS
    assert '/api/feedback/messages/read' in JS
    assert '/api/feedback/send' in JS
    assert 'renderAppealView' in JS
    assert '.fc-appeal-pane' in CSS


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
