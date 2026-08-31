import inspect
import re
import time
from pathlib import Path
from unittest import mock

import app as gtn
import db
import security


def _clear_security_buckets():
    with security._LOCK:
        security._RATE_BUCKETS.clear()


def test_client_ip_uses_the_proxy_nearest_forwarded_hop():
    with gtn.app.test_request_context(
        '/',
        headers={'X-Forwarded-For': '198.51.100.77, 203.0.113.9'},
        environ_base={'REMOTE_ADDR': '127.0.0.1'},
    ):
        assert gtn._client_ip() == '203.0.113.9'


def test_client_ip_ignores_forwarded_headers_from_untrusted_peers():
    with gtn.app.test_request_context(
        '/',
        headers={'X-Forwarded-For': '203.0.113.9'},
        environ_base={'REMOTE_ADDR': '198.51.100.25'},
    ):
        assert gtn._client_ip() == '198.51.100.25'


def test_rate_limiter_does_not_allocate_for_a_read_only_probe():
    _clear_security_buckets()
    assert security.rate_limiter('missing-probe', limit=2, window=60, consume=False)
    assert security.rate_limit_bucket_count() == 0


def test_rate_limiter_has_a_bounded_keyspace():
    _clear_security_buckets()
    original_max = security.MAX_RATE_BUCKET_KEYS
    security.MAX_RATE_BUCKET_KEYS = 16
    try:
        for index in range(100):
            assert security.rate_limiter(f'attacker-{index}', limit=2, window=60)
        assert security.rate_limit_bucket_count() <= 16
    finally:
        security.MAX_RATE_BUCKET_KEYS = original_max
        _clear_security_buckets()


def test_global_http_budget_cannot_be_bypassed_by_changing_routes():
    _clear_security_buckets()
    gtn.app.config.update(TESTING=True, GTN_TEST_HTTP_RATE_LIMITS=True)
    client = gtn.app.test_client()
    try:
        with (
            mock.patch.object(gtn, 'HTTP_GLOBAL_IP_LIMIT', 2),
            mock.patch.object(gtn, 'DB_AVAILABLE', False),
        ):
            environ = {'REMOTE_ADDR': '198.51.100.88'}
            assert client.get('/security-probe-a', environ_base=environ).status_code == 404
            assert client.get('/security-probe-b', environ_base=environ).status_code == 404
            response = client.get('/security-probe-c', environ_base=environ)
        assert response.status_code == 429
        assert response.get_json()['rate_limited'] is True
        assert response.headers['Retry-After']
    finally:
        gtn.app.config.pop('GTN_TEST_HTTP_RATE_LIMITS', None)
        _clear_security_buckets()


def test_global_limit_rejects_before_ip_ban_database_work():
    gtn.app.config.update(TESTING=True, GTN_TEST_HTTP_RATE_LIMITS=True)
    client = gtn.app.test_client()
    try:
        with (
            mock.patch.object(gtn, 'rate_limiter', return_value=False),
            mock.patch.object(gtn, '_get_ip_ban_status_cached') as ban_lookup,
        ):
            response = client.get('/api/social/unread')
        assert response.status_code == 429
        ban_lookup.assert_not_called()
    finally:
        gtn.app.config.pop('GTN_TEST_HTTP_RATE_LIMITS', None)


def test_unread_counts_are_cached_and_force_refreshable():
    with gtn._SOCIAL_UNREAD_CACHE_LOCK:
        gtn._SOCIAL_UNREAD_CACHE.clear()
    with mock.patch.object(
        gtn,
        'social_unread_counts',
        return_value=({'dm_unread_count': 2, 'friend_unread_count': 1}, None),
    ) as load_counts:
        first, first_error = gtn._social_unread_counts_cached(41)
        second, second_error = gtn._social_unread_counts_cached(41)
        refreshed, refreshed_error = gtn._social_unread_counts_cached(41, force=True)
    assert first_error is second_error is refreshed_error is None
    assert first == second == refreshed
    assert load_counts.call_count == 2


def test_ip_ban_lookup_is_cached():
    gtn._clear_ip_ban_status_cache()
    with mock.patch.object(gtn, 'get_ip_ban_status', return_value={'banned': False}) as lookup:
        assert gtn._get_ip_ban_status_cached('203.0.113.55') == {'banned': False}
        assert gtn._get_ip_ban_status_cached('203.0.113.55') == {'banned': False}
    lookup.assert_called_once_with('203.0.113.55')
    gtn._clear_ip_ban_status_cache()


def test_account_failure_budget_survives_ip_rotation():
    _clear_security_buckets()
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    with mock.patch.object(gtn, 'verify_user', return_value=(None, '用户名或密码错误')) as verify:
        for index in range(10):
            response = client.post(
                '/api/auth/login',
                json={'username': 'TargetAccount', 'password': 'wrong-password'},
                environ_base={'REMOTE_ADDR': f'198.51.100.{index + 1}'},
            )
            assert response.status_code == 401
        blocked = client.post(
            '/api/auth/login',
            json={'username': 'TargetAccount', 'password': 'wrong-password'},
            environ_base={'REMOTE_ADDR': '203.0.113.250'},
        )
    assert blocked.status_code == 429
    assert verify.call_count == 10
    _clear_security_buckets()


def test_user_login_lookup_is_indexed_and_missing_users_take_hash_path():
    source = inspect.getsource(db._find_user_row_by_username_key)
    assert 'username_lower = ?' in source
    assert "SELECT * FROM users').fetchall" not in source
    with (
        mock.patch.object(db, 'get_db_connection') as get_connection,
        mock.patch.object(db, 'check_password_hash', return_value=False) as check_hash,
    ):
        connection = get_connection.return_value.__enter__.return_value
        connection.execute.return_value.fetchone.return_value = None
        user, error = db.verify_user('MissingAccount', 'invalid-password')
    assert user is None
    assert error == '用户名或密码错误'
    check_hash.assert_called_once()


def test_database_connections_do_not_renegotiate_wal_mode():
    source = inspect.getsource(db.get_db_connection)
    assert 'journal_mode=WAL' not in source
    assert 'DB_BUSY_TIMEOUT_MS' in source


def test_session_identity_lookup_is_read_only():
    source = inspect.getsource(db.get_user_by_id_for_session)
    assert "SELECT * FROM users WHERE id = ?" in source
    assert 'ensure_current_gr_season_for_conn' not in source
    assert '.commit()' not in source
    current_user_source = inspect.getsource(gtn._current_account_user)
    assert 'get_user_by_id_for_session' in current_user_source


def test_socket_origin_and_nginx_edge_contracts():
    assert gtn.SOCKET_ALLOWED_ORIGINS is None or '*' not in gtn.SOCKET_ALLOWED_ORIGINS
    root = Path(__file__).resolve().parents[1]
    nginx = (root / 'scripts' / 'nginx-blue-green-gtn.conf.template').read_text(encoding='utf-8')
    assert '$proxy_add_x_forwarded_for' not in nginx
    assert 'proxy_set_header X-Forwarded-For $remote_addr;' in nginx
    assert 'limit_req_zone $binary_remote_addr' in nginx
    assert 'limit_conn_zone $binary_remote_addr' in nginx
    assert 'client_max_body_size 1m;' in nginx


def test_security_critical_runtime_dependencies_are_pinned():
    root = Path(__file__).resolve().parents[1]
    requirements = (root / 'requirements.txt').read_text(encoding='utf-8').splitlines()
    active = [line.strip() for line in requirements if line.strip() and not line.lstrip().startswith('#')]
    assert active and all('==' in line for line in active)
    assert 'python-socketio==5.16.2' in active
    assert 'python-engineio==4.13.5' in active


def test_security_headers_and_cookie_defaults():
    gtn.app.config.update(TESTING=True)
    response = gtn.app.test_client().get('/api/healthz')
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'SAMEORIGIN'
    assert response.headers['Referrer-Policy'] == 'same-origin'
    csp = response.headers['Content-Security-Policy']
    assert "default-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "img-src 'self' data: blob:" in csp
    assert 'https:' not in csp
    script_policy = next(part.strip() for part in csp.split(';') if part.strip().startswith('script-src '))
    assert "'unsafe-inline'" not in script_policy
    assert "'nonce-" in script_policy
    assert "script-src-attr 'none'" in csp
    assert gtn.app.config['SESSION_COOKIE_HTTPONLY'] is True
    assert gtn.app.config['SESSION_COOKIE_SECURE'] is True


def test_inline_scripts_use_the_response_nonce_and_inline_handlers_are_absent():
    gtn.app.config.update(TESTING=True)
    response = gtn.app.test_client().get('/')
    assert response.status_code == 200
    csp = response.headers['Content-Security-Policy']
    nonce_match = re.search(r"'nonce-([^']+)'", csp)
    assert nonce_match
    assert f'nonce="{nonce_match.group(1)}"' in response.get_data(as_text=True)

    root = Path(__file__).resolve().parents[1]
    for template in (root / 'templates').glob('*.html'):
        source = template.read_text(encoding='utf-8')
        inline_tags = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>', source, flags=re.I)
        assert all('nonce="{{ csp_nonce }}"' in tag for tag in inline_tags), template.name
        assert not re.search(r'\son[a-z]+\s*=', source, flags=re.I), template.name

    game_source = (root / 'static/js/game.js').read_text(encoding='utf-8')
    lowered_game_source = game_source.lower()
    for attribute in ('onerror', 'onload', 'onclick', 'onchange', 'onsubmit'):
        assert f' {attribute}="' not in lowered_game_source
        assert f" {attribute}='" not in lowered_game_source


def test_community_font_generation_requires_an_account():
    gtn.app.config.update(TESTING=True)
    response = gtn.app.test_client().post('/api/font-subsets/community', json={})
    assert response.status_code == 401


def test_cross_site_mutations_are_rejected_before_route_work():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    with mock.patch.object(gtn, 'verify_user') as verify:
        response = client.post(
            '/api/auth/login',
            json={'username': 'Player', 'password': 'password'},
            headers={'Origin': 'https://attacker.example', 'Sec-Fetch-Site': 'cross-site'},
            base_url='https://game.example',
        )
    assert response.status_code == 403
    assert response.get_json()['error'] == 'cross-site request rejected'
    verify.assert_not_called()


def test_same_origin_mutation_is_not_blocked_by_origin_guard():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    with mock.patch.object(gtn, 'verify_user', return_value=(None, '用户名或密码错误')):
        response = client.post(
            '/api/auth/login',
            json={'username': 'Player', 'password': 'password'},
            headers={'Origin': 'https://game.example', 'Sec-Fetch-Site': 'same-origin'},
            base_url='https://game.example',
        )
    assert response.status_code == 401


def test_trusted_proxy_https_origin_is_treated_as_same_origin():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    with mock.patch.object(gtn, 'verify_user', return_value=(None, '用户名或密码错误')):
        response = client.post(
            '/api/auth/login',
            json={'username': 'Player', 'password': 'password'},
            headers={
                'Origin': 'https://game.example',
                'Sec-Fetch-Site': 'same-origin',
                'X-Forwarded-Proto': 'https',
            },
            base_url='http://game.example',
            environ_base={'REMOTE_ADDR': '127.0.0.1'},
        )
    assert response.status_code == 401


def test_untrusted_peer_cannot_forge_forwarded_https_origin():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    with mock.patch.object(gtn, 'verify_user') as verify:
        response = client.post(
            '/api/auth/login',
            json={'username': 'Player', 'password': 'password'},
            headers={
                'Origin': 'https://game.example',
                'Sec-Fetch-Site': 'same-origin',
                'X-Forwarded-Proto': 'https',
            },
            base_url='http://game.example',
            environ_base={'REMOTE_ADDR': '198.51.100.25'},
        )
    assert response.status_code == 403
    assert response.get_json()['error'] == 'cross-site request rejected'
    verify.assert_not_called()


def test_legacy_admin_session_expires_and_clears_privileged_state():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    old = time.time() - gtn.ADMIN_MAX_SESSION_SECONDS - 1
    with client.session_transaction() as session:
        session['admin_authenticated'] = True
        session['admin_login_time'] = old
        session['admin_last_seen'] = old
        session['admin_csrf'] = 'expired-token'
    response = client.get('/api/admin/me', base_url='https://localhost')
    assert response.status_code == 200
    assert response.get_json()['authenticated'] is False
    with client.session_transaction() as session:
        assert 'admin_authenticated' not in session
        assert 'admin_csrf' not in session


def test_legacy_admin_mutation_requires_csrf_token():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    now = time.time()
    with client.session_transaction() as session:
        session['admin_authenticated'] = True
        session['admin_login_time'] = now
        session['admin_last_seen'] = now
        session['admin_csrf'] = 'admin-test-token'
    rejected = client.post('/api/admin/logout', json={}, base_url='https://localhost')
    assert rejected.status_code == 403
    accepted = client.post(
        '/api/admin/logout',
        json={},
        headers={'X-Admin-CSRF': 'admin-test-token'},
        base_url='https://localhost',
    )
    assert accepted.status_code == 200


def test_admin_orphan_upload_cleanup_defaults_to_preview_and_requires_confirmation():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    now = time.time()
    with client.session_transaction() as session:
        session['admin_authenticated'] = True
        session['admin_login_time'] = now
        session['admin_last_seen'] = now
        session['admin_csrf'] = 'admin-test-token'
    headers = {'X-Admin-CSRF': 'admin-test-token'}

    with mock.patch.object(
        gtn,
        'cleanup_orphaned_community_uploads',
        return_value={'dry_run': True, 'candidate_count': 0, 'deleted_count': 0},
    ) as cleanup:
        preview = client.post(
            '/api/admin/community-mods/storage/cleanup-uploads',
            json={},
            headers=headers,
            base_url='https://localhost',
        )
    assert preview.status_code == 200
    cleanup.assert_called_once_with(min_age_seconds=3600, dry_run=True)

    rejected = client.post(
        '/api/admin/community-mods/storage/cleanup-uploads',
        json={'dry_run': False},
        headers=headers,
        base_url='https://localhost',
    )
    assert rejected.status_code == 400


def test_admin_orphan_upload_cleanup_ui_has_separate_preview_and_execute_controls():
    root = Path(__file__).resolve().parents[1]
    template = (root / 'templates' / 'adminpage.html').read_text(encoding='utf-8')
    source = (root / 'static' / 'js' / 'admin.js').read_text(encoding='utf-8')
    assert 'data-community-storage-action="preview-orphans"' in template
    assert 'data-community-storage-action="cleanup-orphans"' in template
    assert 'id="community-storage-result"' in template
    assert '/api/admin/community-mods/storage/cleanup-uploads' in source
    assert 'confirm: execute' in source
    assert 'button.disabled = true' in source


def test_message_get_routes_never_mark_read_even_with_legacy_query_flag():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    with (
        mock.patch.object(gtn, 'DB_AVAILABLE', True),
        mock.patch.object(gtn, '_require_account_json', return_value=(41, 'Player', None)),
        mock.patch.object(gtn, 'get_feedback_messages', return_value=({'messages': []}, None)) as feedback,
        mock.patch.object(gtn, 'get_dm_messages', return_value=({'messages': []}, None)) as dm,
    ):
        assert client.get('/api/feedback/messages?thread_id=1&mark_read=1').status_code == 200
        assert client.get('/api/social/dm/messages?thread_id=1&mark_read=1').status_code == 200
    assert feedback.call_args.kwargs['mark_read'] is False
    assert dm.call_args.kwargs['mark_read'] is False


def test_account_deletion_requires_password_reauthentication():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    with (
        mock.patch.object(gtn, 'DB_AVAILABLE', True),
        mock.patch.object(gtn, '_current_account_user', return_value={'id': 41}),
        mock.patch.object(gtn, 'soft_delete_user') as delete_user,
    ):
        response = client.post('/api/auth/delete-account', json={})
    assert response.status_code == 400
    delete_user.assert_not_called()


def test_public_health_does_not_expose_deployment_or_capacity_details():
    gtn.app.config.update(TESTING=True)
    response = gtn.app.test_client().get(
        '/api/healthz',
        headers={'X-Forwarded-For': '203.0.113.10'},
        environ_base={'REMOTE_ADDR': '127.0.0.1'},
    )
    payload = response.get_json()
    assert payload['success'] is True
    assert set(payload) == {'success', 'draining'}


def test_feedback_handling_mutations_require_page_csrf_token():
    gtn.app.config.update(TESTING=True)
    client = gtn.app.test_client()
    with client.session_transaction() as session:
        session['user_id'] = 41
        session['feedback_handling_csrf'] = 'handling-test-token'
    with mock.patch.object(gtn, 'feedback_is_staff', return_value=True):
        rejected = client.patch(
            '/api/feedback/handling/warnings/1',
            json={'resolved': True},
            base_url='https://localhost',
        )
        page = client.get('/feedback/handling-pane', base_url='https://localhost')
    assert rejected.status_code == 403
    assert b'gtn-feedback-handling-csrf' in page.data
    assert b'handling-test-token' in page.data


def test_soft_delete_verifies_current_password_before_mutation():
    source = inspect.getsource(db.soft_delete_user)
    assert 'check_password_hash' in source
    assert source.index('check_password_hash') < source.index('UPDATE users')
