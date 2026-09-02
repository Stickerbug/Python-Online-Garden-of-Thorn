import gc
import os
import shlex
import tempfile
import time
import unittest
from unittest import mock

import app
import db


class AdminCredentialConfigurationTests(unittest.TestCase):
    def test_console_uses_shared_admin_hash_when_its_own_hash_is_missing(self):
        with mock.patch.object(app.os, 'environ', {'ADMIN_PASSWORD_HASH': 'shared-hash'}):
            configured = app._configured_credential_hash(
                'ADMIN_CONSOLE_PASSWORD_HASH',
                fallback_name='ADMIN_PASSWORD_HASH',
            )

        self.assertEqual(configured, 'shared-hash')

    def test_console_specific_hash_takes_precedence(self):
        with mock.patch.object(app.os, 'environ', {
            'ADMIN_PASSWORD_HASH': 'shared-hash',
            'ADMIN_CONSOLE_PASSWORD_HASH': 'console-hash',
        }):
            configured = app._configured_credential_hash(
                'ADMIN_CONSOLE_PASSWORD_HASH',
                fallback_name='ADMIN_PASSWORD_HASH',
            )

        self.assertEqual(configured, 'console-hash')

    def test_missing_shared_and_console_hashes_still_fail_closed(self):
        with (
            mock.patch.object(app.os, 'environ', {}),
            mock.patch.object(app.secrets, 'token_urlsafe', return_value='disabled-secret'),
            mock.patch.object(app, 'generate_password_hash', return_value='disabled-hash') as hasher,
        ):
            configured = app._configured_credential_hash(
                'ADMIN_CONSOLE_PASSWORD_HASH',
                fallback_name='ADMIN_PASSWORD_HASH',
            )

        self.assertEqual(configured, 'disabled-hash')
        hasher.assert_called_once_with('disabled-secret')


class AdminSurfaceAuthenticationTests(unittest.TestCase):
    def setUp(self):
        app.app.config.update(TESTING=True)
        self.client = app.app.test_client()
        shared_hash = app.generate_password_hash('shared-admin-password')
        self.patchers = [
            mock.patch.object(app, 'ADMIN_PASSWORD_HASH', shared_hash),
            mock.patch.object(app, 'ADMIN_CONSOLE_PASSWORD_HASH', shared_hash),
            mock.patch.object(app, 'should_rate_limit_admin_login', return_value=False),
            mock.patch.object(app, 'record_admin_login_failure'),
            mock.patch.object(app, 'clear_admin_login_failures'),
            mock.patch.object(app, 'admin_event'),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()

    def test_shared_password_authenticates_both_surfaces_and_runs_commands(self):
        admin_login = self.client.post(
            '/api/admin/login',
            json={'password': 'shared-admin-password'},
        )
        self.assertEqual(admin_login.status_code, 200)
        admin_csrf = admin_login.get_json()['csrf_token']

        console_login = self.client.post(
            '/api/adminconsole/login',
            json={'password': 'shared-admin-password'},
        )
        self.assertEqual(console_login.status_code, 200)
        console_csrf = console_login.get_json()['csrf_token']

        self.assertTrue(self.client.get('/api/admin/me').get_json()['authenticated'])
        self.assertTrue(self.client.get('/api/adminconsole/me').get_json()['authenticated'])

        admin_command = self.client.post(
            '/api/admin/command',
            json={'line': 'help'},
            headers={'X-Admin-CSRF': admin_csrf},
        )
        self.assertEqual(admin_command.status_code, 200)
        self.assertTrue(admin_command.get_json()['success'])

        console_command = self.client.post(
            '/api/adminconsole/command',
            json={'line': 'help', 'request_id': 'shared-auth-test'},
            headers={'X-Admin-Console-CSRF': console_csrf},
        )
        self.assertEqual(console_command.status_code, 200)
        self.assertTrue(console_command.get_json()['success'])


class AdminConsoleCommandTests(unittest.TestCase):
    def test_every_visible_leaf_has_an_execution_mapping(self):
        missing = []

        def walk(node, path=()):
            for name, meta in node.items():
                if meta.get('hidden'):
                    continue
                current = path + (name,)
                children = {
                    child_name: child
                    for child_name, child in (meta.get('children') or {}).items()
                    if not child.get('hidden')
                }
                if children:
                    walk(children, current)
                elif (
                    current != ('help',)
                    and not meta.get('internal_parts')
                    and current[:2] != ('game', 'player')
                ):
                    missing.append(current)

        walk(app.ADMIN_COMMAND_TREE)
        self.assertEqual(missing, [])

    def test_structured_commands_translate_to_existing_handlers(self):
        cases = {
            'player list': 'players',
            'account dew get Alice': 'dew get Alice',
            'account identity set Alice staff': 'identity set Alice staff',
            'account title equip Alice a,b': 'title equip Alice a,b',
            'account title namecolor Alice styled left': 'title namecolor Alice styled left',
            'account title catalog style styled {rainbow}Title{/}': "title catalog style styled '{rainbow}Title{/}'",
            'account title preview {color:#FF0000}Title{/}': "title preview '{color:#FF0000}Title{/}'",
            'game action draftfill 7': 'draftfill 7',
            'game pending get 7': 'gamepending 7',
            'game player 7 1 status add poison 3': 'gamestatus 7 1 add poison 3',
            'moderation warning edit 4 3600 test': 'warningedit 4 3600 test',
            'moderation report get 5': 'reportget 5',
            'data cardsbackfill preview all': 'cardsbackfill preview all',
            'data storage vacuum confirm': 'storage-vacuum confirm',
            'data storage community-delete community/trash/a.zip confirm':
                'storage-community-delete community/trash/a.zip confirm',
            'server pull confirm': 'gitpull confirm',
        }
        for line, expected in cases.items():
            with self.subTest(line=line):
                translated, help_text = app._translate_structured_admin_command(shlex.split(line))
                self.assertEqual(translated, expected)
                self.assertIsNone(help_text)

    def test_report_resolution_options_are_strict_and_preserve_notes(self):
        options = app.parse_report_resolution_options([
            'target=warn',
            'reporter=none',
            'duration=3600',
            '重复骚扰',
        ])
        self.assertEqual(options['target_action'], 'warn')
        self.assertEqual(options['reporter_action'], 'none')
        self.assertEqual(options['duration_seconds'], 3600)
        self.assertEqual(options['note'], '重复骚扰')

        with self.assertRaises(ValueError):
            app.parse_report_resolution_options(['target=erase'])
        with self.assertRaises(ValueError):
            app.parse_report_resolution_options(['duration=tomorrow'])

    def test_sensitive_commands_are_redacted_and_not_backgrounded(self):
        line = 'account password Bob Secret123!'
        self.assertNotIn('Secret123!', app.redact_admin_command_line(line))
        self.assertFalse(app.admin_console_command_runs_in_background(line))
        self.assertTrue(
            app.admin_console_command_runs_in_background(
                'data storage community-delete community/trash/a.zip confirm'
            )
        )


class AdminConsoleRouteTests(unittest.TestCase):
    def setUp(self):
        app.app.config.update(TESTING=True)
        self.client = app.app.test_client()
        self.console_session_id = f'test-console-{time.time_ns()}'
        self.csrf = 'test-csrf-token'
        self._authenticate()

    def tearDown(self):
        with app._ADMIN_CONSOLE_JOBS_GUARD:
            stale_ids = [
                job_id
                for job_id, job in app._ADMIN_CONSOLE_JOBS.items()
                if job.get('session_id') == self.console_session_id
            ]
            for job_id in stale_ids:
                app._ADMIN_CONSOLE_JOBS.pop(job_id, None)
        with app._ADMIN_CONSOLE_COMMAND_LOCKS_GUARD:
            app._ADMIN_CONSOLE_COMMAND_LOCKS.pop(self.console_session_id, None)

    def _authenticate(self, login_time=None, last_seen=None):
        now = time.time()
        with self.client.session_transaction() as session:
            session['admin_console_authenticated'] = True
            session['admin_console_login_time'] = now if login_time is None else login_time
            session['admin_console_last_seen'] = now if last_seen is None else last_seen
            session['admin_console_session_id'] = self.console_session_id
            session['admin_console_csrf'] = self.csrf

    def test_command_requires_csrf(self):
        response = self.client.post(
            '/api/adminconsole/command',
            json={'line': 'help', 'request_id': 'csrf-test'},
        )
        self.assertEqual(response.status_code, 403)

    def test_command_returns_trace_and_elapsed_time(self):
        response = self.client.post(
            '/api/adminconsole/command',
            json={'line': 'help', 'request_id': 'trace-test'},
            headers={'X-Admin-Console-CSRF': self.csrf},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['request_id'], 'trace-test')
        self.assertGreaterEqual(payload['elapsed_ms'], 0)

    def test_busy_session_rejects_parallel_command(self):
        command_lock = app.admin_console_command_lock_for_session(self.console_session_id)
        command_lock.acquire()
        try:
            response = self.client.post(
                '/api/adminconsole/command',
                json={'line': 'help', 'request_id': 'busy-test'},
                headers={'X-Admin-Console-CSRF': self.csrf},
            )
        finally:
            command_lock.release()
        self.assertEqual(response.status_code, 409)

    def test_expired_session_is_cleared(self):
        expired = time.time() - app.ADMIN_CONSOLE_MAX_SESSION_SECONDS - 5
        self._authenticate(login_time=expired, last_seen=expired)
        response = self.client.get('/api/adminconsole/me')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()['authenticated'])
        with self.client.session_transaction() as session:
            self.assertNotIn('admin_console_authenticated', session)

    def test_completion_returns_structured_items(self):
        response = self.client.get('/api/adminconsole/complete?line=moderation%20warning%20')
        self.assertEqual(response.status_code, 200)
        items = response.get_json()['items']
        self.assertTrue(items)
        self.assertTrue(all(isinstance(item, dict) for item in items))
        self.assertIn('list', [item['value'] for item in items])

    def test_background_job_is_scoped_and_can_be_cancelled_while_queued(self):
        with mock.patch.object(app.socketio, 'start_background_task') as starter:
            response = self.client.post(
                '/api/adminconsole/command',
                json={
                    'line': 'data storage community-delete community/trash/test.zip confirm',
                    'request_id': 'background-test',
                },
                headers={'X-Admin-Console-CSRF': self.csrf},
            )
        self.assertEqual(response.status_code, 202)
        payload = response.get_json()
        self.assertTrue(payload['accepted'])
        self.assertEqual(payload['status'], 'queued')
        starter.assert_called_once()

        job_id = payload['job_id']
        status = self.client.get(f'/api/adminconsole/jobs/{job_id}')
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.get_json()['status'], 'queued')

        cancelled = self.client.post(
            f'/api/adminconsole/jobs/{job_id}/cancel',
            json={},
            headers={'X-Admin-Console-CSRF': self.csrf},
        )
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.get_json()['status'], 'cancelled')


class AdminWarningPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'warnings.sqlite3')
        db.init_db()
        self.user, error = db.create_user('WarningTester', 'Aa1!aaaa')
        self.assertIsNone(error)
        now = db.utc_now()
        with db.get_db_connection() as connection:
            cursor = connection.execute(
                '''
                INSERT INTO moderation_actions (
                    admin_username, target_user_id, target_username, action_type,
                    reason, duration_seconds, created_at, expires_at
                ) VALUES (?, ?, ?, 'warn', ?, 3600, ?, ?)
                ''',
                (
                    'test',
                    self.user['id'],
                    self.user['username'],
                    '原始警告原因',
                    now,
                    '2999-01-01T00:00:00Z',
                ),
            )
            self.warning_id = cursor.lastrowid
            connection.commit()

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def test_ending_warning_preserves_reason(self):
        item, error = db.update_user_warning(
            self.warning_id,
            reason='',
            duration_seconds=0,
            active=False,
        )
        self.assertIsNone(error)
        self.assertEqual(item['reason'], '原始警告原因')
        self.assertFalse(item['active'])


if __name__ == '__main__':
    unittest.main()
