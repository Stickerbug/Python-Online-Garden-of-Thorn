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

    def test_extract_bind_code_tolerates_messy_remarks(self):
        """留言识别：大小写/空格/前后缀标点与中文/全角字符都不影响；9 位串不误切。"""
        f = afdian_service.extract_bind_code
        self.assertEqual(f('ABCD2345'), 'ABCD2345')
        self.assertEqual(f('abcd2345'), 'ABCD2345')                      # 小写
        self.assertEqual(f('  ABCD2345  '), 'ABCD2345')                  # 空格
        self.assertEqual(f('赞助！ABCD2345，谢谢'), 'ABCD2345')          # 全角标点
        self.assertEqual(f('绑定码ABCD2345'), 'ABCD2345')                # 紧贴中文无空格
        self.assertEqual(f('ABCD2345谢谢投喂'), 'ABCD2345')              # 尾贴中文
        self.assertEqual(f('ＡＢＣＤ２３４５'), 'ABCD2345')              # 全角字母数字
        self.assertEqual(f('我的码是 abcd2345 感谢'), 'ABCD2345')        # 混合随意书写
        self.assertEqual(f('ABCD23456'), '')                             # 9 位串不误切
        self.assertEqual(f('XABCD2345'), '')                             # 前面多一位同理
        self.assertEqual(f(''), '')
        self.assertEqual(f('没有码'), '')

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

    def test_renewal_without_remark_follows_afdian_user(self):
        """按月方案的自动续费单不带留言：同一爱发电账号此前到账过则自动认领入同一账号。"""
        code = afdian_service.bind_code_for(self.user['id'])
        with mock.patch.object(afdian_service, 'requery_recent', lambda **kw: {'ok': False}):
            afdian_service.admin_set_plan('plan_monthly', 500, '月档')
        first = afdian_service.ingest_order(
            self._order(out_trade_no='AFD-M1', remark=f'码 {code}',
                        plan_id='plan_monthly', user_id='afd-sub-1'))
        self.assertEqual(first['status'], 'credited')
        renewal = afdian_service.ingest_order(
            self._order(out_trade_no='AFD-M2', remark='',
                        plan_id='plan_monthly', user_id='afd-sub-1'))
        self.assertEqual(renewal['status'], 'credited')
        self.assertEqual(renewal['dew'], 500)
        self.assertEqual(db.get_user_thorn_dew(self.user['id'])['paid'], 1000)
        # 陌生爱发电账号的无留言单仍是 unmatched
        stranger = afdian_service.ingest_order(
            self._order(out_trade_no='AFD-M3', remark='',
                        plan_id='plan_monthly', user_id='afd-stranger'))
        self.assertEqual(stranger['status'], 'unmatched')

    def test_sale_order_sku_mapping_and_combos(self):
        """售卖项多价格方案：按 SKU 名称映射；单项多次/多项组合都按 份数×荆露 求和；
        未配置的 SKU 安全挂起；到账一次后自动学会 sku_id。"""
        code = afdian_service.bind_code_for(self.user['id'])
        with mock.patch.object(afdian_service, 'requery_recent', lambda **kw: {'ok': False}):
            afdian_service.admin_set_sku(250, 'Y1 档')
            afdian_service.admin_set_sku(800, 'Y3 档')
        order = {
            'out_trade_no': 'AFD-SKU1', 'plan_id': 'plan_shop', 'month': 1, 'status': 2,
            'remark': f'码 {code}', 'total_amount': '3.00',
            'sku_detail': [{'sku_id': 'sku-aaa', 'name': 'Y3 档', 'count': 2}],
        }
        result = afdian_service.ingest_order(order)
        self.assertEqual(result['status'], 'credited')
        self.assertEqual(result['dew'], 1600)          # 800 × 2 份
        # 组合：两项各不同份数
        combo = afdian_service.ingest_order({
            'out_trade_no': 'AFD-SKU2', 'plan_id': 'plan_shop', 'month': 1, 'status': 2,
            'remark': f'码 {code}', 'total_amount': '7.00',
            'sku_detail': [
                {'sku_id': 'sku-aaa', 'name': 'Y3 档', 'count': 1},
                {'sku_id': 'sku-bbb', 'name': 'Y1 档', 'count': 3},
            ],
        })
        self.assertEqual(combo['status'], 'credited')
        self.assertEqual(combo['dew'], 800 + 250 * 3)  # 1550
        # sku_id 已自学：改名后仍按 sku_id 命中
        renamed = afdian_service.ingest_order({
            'out_trade_no': 'AFD-SKU3', 'plan_id': 'plan_shop', 'month': 1, 'status': 2,
            'remark': f'码 {code}', 'total_amount': '3.00',
            'sku_detail': [{'sku_id': 'sku-aaa', 'name': '新名字了', 'count': 1}],
        })
        self.assertEqual(renamed['status'], 'credited')
        self.assertEqual(renamed['dew'], 800)
        # 未配置的 SKU：安全挂起，不发
        unknown = afdian_service.ingest_order({
            'out_trade_no': 'AFD-SKU4', 'plan_id': 'plan_shop', 'month': 1, 'status': 2,
            'remark': f'码 {code}', 'total_amount': '68.00',
            'sku_detail': [{'sku_id': 'sku-zzz', 'name': 'Y68 档', 'count': 1}],
        })
        self.assertEqual(unknown['status'], 'unmapped')
        total = db.get_user_thorn_dew(self.user['id'])['paid']
        self.assertEqual(total, 1600 + 1550 + 800)

    def test_public_plans_lists_sku_tiers_with_price(self):
        """兑换页档位要包含 SKU 档（此前只读方案表，六个真实档位看不到）。"""
        with mock.patch.object(afdian_service, 'requery_recent', lambda **kw: {'ok': False}):
            afdian_service.admin_set_sku(250, '一滴荆露(250荆露)', price='1')
            afdian_service.admin_set_sku(800, '小瓶荆露(800荆露)', price='3')
            afdian_service.admin_set_plan('plan_monthly', 500, '月度订阅')
        plans = afdian_service.public_plans()
        names = [(p['name'], p['kind'], p['price']) for p in plans]
        self.assertIn(('一滴荆露(250荆露)', 'sku', '1.00'), names)
        self.assertIn(('小瓶荆露(800荆露)', 'sku', '3.00'), names)
        self.assertTrue(any(kind == 'plan' for _, kind, _ in names))

    def test_no_sku_order_settles_by_price_fallback(self):
        """无 SKU 明细的订单按总价匹配档位兜底（替代危险的平底方案映射）。"""
        code = afdian_service.bind_code_for(self.user['id'])
        with mock.patch.object(afdian_service, 'requery_recent', lambda **kw: {'ok': False}):
            afdian_service.admin_set_sku(800, '小瓶荆露(800荆露)', price='3')
        result = afdian_service.ingest_order(self._order(
            out_trade_no='AFD-NOSKU', remark=f'码 {code}',
            total_amount='3.00', plan_id='plan_shop'))   # 无 sku_detail
        self.assertEqual(result['status'], 'credited')
        self.assertEqual(result['dew'], 800)
        # 总价没有对应档位 → 安全挂起
        other = afdian_service.ingest_order(self._order(
            out_trade_no='AFD-NOSKU2', remark=f'码 {code}',
            total_amount='68.00', plan_id='plan_shop'))
        self.assertEqual(other['status'], 'unmapped')
        self.assertEqual(db.get_user_thorn_dew(self.user['id'])['paid'], 800)

    def test_plan_set_zero_disables_mapping(self):
        with mock.patch.object(afdian_service, 'requery_recent', lambda **kw: {'ok': False}):
            r1 = afdian_service.admin_set_plan('plan_x', 500, '测试')
            self.assertEqual(r1.get('active'), 1)
            r2 = afdian_service.admin_set_plan('plan_x', 0)
            self.assertEqual(r2.get('active'), 0)
        plans = [p for p in afdian_service.public_plans() if p['kind'] == 'plan']
        self.assertFalse(any(p['plan_id'] == 'plan_x' for p in plans))

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



    def test_entry_open_to_all_accounts(self):
        """赞助入口对全员开放（2026-09-24）：任意登录账号页面 200、API 可用、主页渲染赞助 tab。"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user['id']
            sess['username'] = 'AfdianRoute'
        with mock.patch.object(self._app, 'feedback_is_staff', lambda uid: False):
            page = self.client.get('/afdian')
            self.assertEqual(page.status_code, 200)
            api = self.client.get('/api/afdian/status')
            self.assertEqual(api.status_code, 200)
            self.assertIn('bind_code', api.get_json())
        home = self.client.get('/')
        self.assertEqual(home.status_code, 200)
        self.assertIn('title-shop-tab-afdian', home.get_data(as_text=True))
        self.assertIn('title-shop-afdian-panel', home.get_data(as_text=True))

if __name__ == '__main__':
    unittest.main()
