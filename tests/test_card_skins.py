# -*- coding: utf-8 -*-
"""卡牌皮肤：目录、购买、装备、商店三槽不重复、刷新计价。"""

import gc
import os
import tempfile
import unittest

import card_skins
import db


class CardSkinTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.temp_dir.name, 'skins.sqlite3')
        db.init_db()
        self.user, err = db.create_user('SkinOwner1', 'Passw0rd!xyz')
        assert self.user, err
        with db.get_db_connection() as conn:
            conn.execute('UPDATE users SET thorn_dew_free = 999999 WHERE id = ?', (self.user['id'],))
            conn.commit()

    def tearDown(self):
        db.release_wal_keeper()
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def _give(self, skin_id):
        with db.get_db_connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute(
                "INSERT OR IGNORE INTO user_card_skins (user_id, skin_id, acquired_source, acquired_at) VALUES (?, ?, 'shop', datetime('now'))",
                (self.user['id'], skin_id),
            )
            conn.commit()

    def test_catalog_has_all_eight(self):
        with db.get_db_connection() as conn:
            card_skins.ensure_card_skin_schema(conn)
            rows = conn.execute('SELECT skin_id, price, shop_weight FROM card_skin_catalog').fetchall()
            conn.commit()
        prices = {row['skin_id']: (int(row['price']), int(row['shop_weight'])) for row in rows}
        self.assertEqual(prices['区'], (50000, 1))
        self.assertEqual(prices['叶框'], (10000, 10))
        self.assertEqual(prices['金叶框'], (20000, 5))
        self.assertEqual(prices['绷带'], (30000, 5))
        self.assertEqual(prices['标靶'], (15000, 3))
        self.assertEqual(prices['蠕虫'], (25000, 5))
        self.assertEqual(prices['阴阳'], (10000, 10))
        self.assertEqual(prices['阴阳玉'], (30000, 3))

    def test_equip_requires_ownership(self):
        with db.get_db_connection() as conn:
            card_skins.ensure_card_skin_schema(conn)
            conn.commit()
            self.assertEqual(card_skins.equip_card_skin(conn, self.user['id'], '叶框'), '尚未拥有该皮肤')
            self._give('叶框')
            self.assertIsNone(card_skins.equip_card_skin(conn, self.user['id'], '叶框'))
            self.assertEqual(card_skins.get_equipped_card_skin(conn, self.user['id']), '叶框')
            self.assertEqual(card_skins.equip_card_skin(conn, self.user['id'], '不存在'), '未知皮肤')
            self.assertIsNone(card_skins.equip_card_skin(conn, self.user['id'], ''))
            self.assertEqual(card_skins.get_equipped_card_skin(conn, self.user['id']), '')

    def test_shop_three_unique_offers_and_purchase(self):
        shop, error = db.get_card_skin_shop(self.user['id'])
        self.assertIsNone(error)
        self.assertEqual(len(shop['offers']), 3)
        self.assertEqual(len({offer['skin_id'] for offer in shop['offers']}), 3)
        self.assertEqual(shop['refresh_cost'], 700)
        target = shop['offers'][0]
        result, error = db.purchase_card_skin_offer(self.user['id'], shop['set_id'], target['slot'])
        self.assertIsNone(error)
        self.assertTrue(any(item['skin_id'] == target['skin_id'] and item['owned'] for item in result['items']))
        # 同槽再买被拒
        _, error = db.purchase_card_skin_offer(self.user['id'], shop['set_id'], target['slot'])
        self.assertEqual(error, '本轮已购买该商品')
        # 装备成功
        payload, error = db.set_user_card_skin(self.user['id'], target['skin_id'])
        self.assertIsNone(error)
        self.assertEqual(payload['equipped'], target['skin_id'])

    def test_cross_day_duplicate_skin_purchase_blocked(self):
        """跨天刷新后同一皮肤再次上架：已拥有 → 禁止购买，文案「你已经拥有这个卡牌皮肤了！」"""
        shop, _ = db.get_card_skin_shop(self.user['id'])
        target = shop['offers'][0]
        result, error = db.purchase_card_skin_offer(self.user['id'], shop['set_id'], target['slot'])
        self.assertIsNone(error)
        # 模拟跨天：新建下一日的全局 set 并把用户 active_set 切过去（等价于每日 rollover）
        with db.get_db_connection() as conn:
            card_skins.ensure_card_skin_schema(conn)
            import secrets as _secrets
            new_set = f'daily:next-day:{_secrets.token_hex(4)}'
            conn.execute(
                "INSERT INTO card_skin_shop_sets (set_id, shop_date, scope_key, kind, created_at) VALUES (?, date('now'), 'global', 'daily', datetime('now'))",
                (new_set,),
            )
            conn.execute(
                'INSERT INTO card_skin_shop_offers (set_id, slot, skin_id, price) VALUES (?, 1, ?, ?)',
                (new_set, target['skin_id'], 10000),
            )
            conn.execute(
                "UPDATE card_skin_shop_user_state SET active_set_id = ? WHERE user_id = ?",
                (new_set, self.user['id']),
            )
            conn.commit()
        _, error = db.purchase_card_skin_offer(self.user['id'], new_set, 1)
        self.assertEqual(error, '你已经拥有这个卡牌皮肤了！')

    def test_refresh_cost_increments(self):
        shop, _ = db.get_card_skin_shop(self.user['id'])
        self.assertEqual(shop['refresh_cost'], 700)
        shop, error = db.refresh_card_skin_shop(self.user['id'])
        self.assertIsNone(error)
        self.assertEqual(shop['refresh_cost'], 1000)
        shop, error = db.refresh_card_skin_shop(self.user['id'])
        self.assertIsNone(error)
        self.assertEqual(shop['refresh_cost'], 1300)


if __name__ == '__main__':
    unittest.main()
