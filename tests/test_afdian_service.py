# -*- coding: utf-8 -*-
"""爱发电赞助兑换：签名向量（官方文档示例）、绑定码、幂等入账、补结、webhook 路由。"""

from __future__ import annotations

import gc
import os
import tempfile
import unittest
from unittest import mock

import afdian_service
import db


def _app_available():
    try:
        import app as gtn
        return gtn, ''
    except Exception as exc:  # pragma: no cover
        return None, str(exc)


class AfdianServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'afdian.sqlite3')
        db.init_db()
        self.user, error = db.create_user('AfdianTester', 'Aa1!aaaa')
        self.assertIsNone(error)

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        gc.collect()          # sqlite 连接靠 GC 关闭，先收再删临时库（Windows 文件锁）
        self.temp_dir.cleanup()

    def _order(self, **kwargs):
        payload = {
            'out_trade_no': 'AFD20260924NO1',
            'user_id': 'afd-user-1',
            'user_private_id': 'union-1',
            'plan_id': 'plan_small',
            'month': 1,
            'total_amount': '10.00',
            'show_amount': '10.00',
            'status': 2,
            'remark': '',
        }
        payload.update(kwargs)
        return payload

    def test_api_sign_official_vector(self):
        # 官方文档示例：token=123、params={"a":333}、ts=1624339905、user_id=abc
        sign = afdian_service.api_sign('{"a":333}', 1624339905, 'abc', '123')
        self.assertEqual(sign, 'a4acc28b81598b7e5d84ebdc3e91710c')

    def test_bind_code_get_reset(self):
        code = afdian_service.bind_code_for(self.user['id'])
        self.assertRegex(code, r'^[A-Z2-9]{8}$')
        self.assertEqual(afdian_service.bind_code_for(self.user['id']), code)
        new_code = afdian_service.reset_bind_code(self.user['id'])
        self.assertNotEqual(new_code, code)
        self.assertEqual(afdian_service.bind_code_for(self.user['id']), new_code)

    def test_ingest_credits_paid_dew_idempotently(self):
        code = afdian_service.bind_code_for(self.user['id'])
        with mock.patch.object(afdian_service, 'requery_recent', lambda **kw: {'ok': False}):
            afdian_service.admin_set_plan('plan_small', 1000, '¥10 档')
        result = afdian_service.ingest_order(self._order(remark=f'赞助！绑定码 {code}'))
        self.assertEqual(result['status'], 'credited')
        self.assertEqual(result['dew'], 1000)
        dew = db.get_user_thorn_dew(self.user['id'])
        self.assertEqual(dew['paid'], 1000)
        self.assertEqual(dew['free'], 0)
        with db.get_db_connection() as conn:
            tx = conn.execute(
                "SELECT * FROM user_currency_transactions WHERE source_type='afdian' "
                'AND source_id=?', ('AFD20260924NO1',)).fetchone()
        self.assertIsNotNone(tx)
        self.assertEqual(int(tx['paid_delta']), 1000)
        # 同一订单再推一次：duplicate，不重复入账
        again = afdian_service.ingest_order(self._order(remark=f'绑定码 {code}'))
        self.assertEqual(again['status'], 'duplicate')
        self.assertEqual(db.get_user_thorn_dew(self.user['id'])['paid'], 1000)

    def test_month_multiplier(self):
        code = afdian_service.bind_code_for(self.user['id'])
        with mock.patch.object(afdian_service, 'requery_recent', lambda **kw: {'ok': False}):
            afdian_service.admin_set_plan('plan_small', 1000, '¥10 档')
        result = afdian_service.ingest_order(
            self._order(out_trade_no='AFD-M3', remark=code, month=3))
        self.assertEqual(result['status'], 'credited')
        self.assertEqual(result['dew'], 3000)
        self.assertEqual(db.get_user_thorn_dew(self.user['id'])['paid'], 3000)

    def test_unmatched_then_unmapped_then_settle_after_mapping(self):
        # 没填绑定码 → unmatched
        result = afdian_service.ingest_order(self._order(remark='没有码'))
        self.assertEqual(result['status'], 'unmatched')
        self.assertEqual(db.get_user_thorn_dew(self.user['id'])['paid'], 0)
        # 填了码但方案未配置 → unmapped
        code = afdian_service.bind_code_for(self.user['id'])
        result = afdian_service.ingest_order(
            self._order(out_trade_no='AFD-UNMAP', remark=f'码 {code}'))
        self.assertEqual(result['status'], 'unmapped')
        self.assertEqual(db.get_user_thorn_dew(self.user['id'])['paid'], 0)
        # 配置映射后再推同单 → 自动补结
        with mock.patch.object(afdian_service, 'requery_recent', lambda **kw: {'ok': False}):
            afdian_service.admin_set_plan('plan_small', 500, '¥10 档')
        result = afdian_service.ingest_order(
            self._order(out_trade_no='AFD-UNMAP', remark=f'码 {code}'))
        self.assertEqual(result['status'], 'credited')
        self.assertEqual(db.get_user_thorn_dew(self.user['id'])['paid'], 500)

    def test_non_success_order_is_ignored(self):
        result = afdian_service.ingest_order(self._order(status=1))
        self.assertEqual(result['status'], 'ignored')

    def test_admin_credit_manual(self):
        code = afdian_service.bind_code_for(self.user['id'])
        afdian_service.ingest_order(self._order(out_trade_no='AFD-BAD', remark='忘了写码'))
        with mock.patch.object(afdian_service, 'requery_recent', lambda **kw: {'ok': False}):
            result = afdian_service.admin_credit('AFD-BAD', 800, self.user['id'])
        self.assertTrue(result.get('ok'))
        self.assertEqual(db.get_user_thorn_dew(self.user['id'])['paid'], 800)
        with db.get_db_connection() as conn:
            row = conn.execute(
                "SELECT status FROM afdian_orders WHERE out_trade_no='AFD-BAD'").fetchone()
        self.assertEqual(row['status'], 'manual')


@unittest.skipIf(not _app_available()[0], f'无法导入 app（{_app_available()[1]}）')
class AfdianWebhookRouteTests(unittest.TestCase):
    def setUp(self):
        self._app, _ = _app_available()
        self.client = self._app.app.test_client()
        self.old_db_path = db.DB_PATH
        self.old_available = self._app.DB_AVAILABLE
        self.temp_dir = tempfile.TemporaryDirectory()
        db.DB_PATH = os.path.join(self.temp_dir.name, 'afdian-route.sqlite3')
        db.init_db()
        self._app.DB_AVAILABLE = True
        self.user, error = db.create_user('AfdianRoute', 'Bb2!bbbb')
        self.assertIsNone(error)

    def tearDown(self):
        self._app.DB_AVAILABLE = self.old_available
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def test_webhook_secret_and_ingest(self):
        code = afdian_service.bind_code_for(self.user['id'])
        with mock.patch.object(afdian_service, 'requery_recent', lambda **kw: {'ok': False}):
            afdian_service.admin_set_plan('plan_small', 1000, '¥10 档')
        with mock.patch.dict(os.environ, {'GTN_AFDIAN_WEBHOOK_SECRET': 's3cret'}):
            wrong = self.client.post('/api/afdian/webhook/nope', json={})
            self.assertEqual(wrong.status_code, 403)
            payload = {'ec': 200, 'em': 'ok', 'data': {'type': 'order', 'order': {
                'out_trade_no': 'AFD-WH1', 'plan_id': 'plan_small', 'month': 1,
                'status': 2, 'remark': f'绑定码 {code}', 'total_amount': '10.00'}}}
            ok = self.client.post('/api/afdian/webhook/s3cret', json=payload)
            self.assertEqual(ok.status_code, 200)
            self.assertEqual(ok.get_json()['ec'], 200)
        self.assertEqual(db.get_user_thorn_dew(self.user['id'])['paid'], 1000)


if __name__ == '__main__':
    unittest.main()
