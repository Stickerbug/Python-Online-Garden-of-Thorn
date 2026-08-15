import gc
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

import db
from title_styles import parse_title_style, title_style_plain_text


BEIJING = timezone(timedelta(hours=8))


class TitleShopTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        self.old_shop_now = db._title_shop_now
        db.DB_PATH = os.path.join(self.temp_dir.name, 'title-shop.sqlite3')
        db.init_db()
        self.user_a, error = db.create_user('ShopTesterA', 'Aa1!aaaa')
        self.assertIsNone(error)
        self.user_b, error = db.create_user('ShopTesterB', 'Aa1!aaaa')
        self.assertIsNone(error)
        db.adjust_user_thorn_dew(self.user_a['id'], free_delta=300000, reason='test')
        db.adjust_user_thorn_dew(self.user_b['id'], free_delta=300000, reason='test')
        db._title_shop_now = lambda: datetime(2026, 8, 15, 10, 0, tzinfo=BEIJING)

    def tearDown(self):
        db._title_shop_now = self.old_shop_now
        db.DB_PATH = self.old_db_path
        gc.collect()
        self.temp_dir.cleanup()

    def test_daily_offers_are_shared_unique_and_refresh_cost_increases(self):
        first, error = db.get_user_title_shop(self.user_a['id'])
        self.assertIsNone(error)
        other, error = db.get_user_title_shop(self.user_b['id'])
        self.assertIsNone(error)
        self.assertEqual(first['set_id'], other['set_id'])
        self.assertEqual(len(first['offers']), 8)
        self.assertEqual(len({item['id'] for item in first['offers']}), 8)
        self.assertEqual(first['refresh_cost'], 1000)

        refreshed, error = db.refresh_user_title_shop(self.user_a['id'])
        self.assertIsNone(error)
        self.assertNotEqual(refreshed['set_id'], first['set_id'])
        self.assertEqual(refreshed['refresh_cost'], 1500)
        self.assertEqual(refreshed['balance']['total'], first['balance']['total'] - 1000)

    def test_lock_survives_daily_rollover_and_unlock_uses_current_daily_set(self):
        refreshed, error = db.refresh_user_title_shop(self.user_a['id'])
        self.assertIsNone(error)
        locked, error = db.set_user_title_shop_locked(self.user_a['id'], True)
        self.assertIsNone(error)
        locked_set_id = locked['set_id']

        db._title_shop_now = lambda: datetime(2026, 8, 16, 0, 1, tzinfo=BEIJING)
        next_day_locked, error = db.get_user_title_shop(self.user_a['id'])
        self.assertIsNone(error)
        next_day_daily, error = db.get_user_title_shop(self.user_b['id'])
        self.assertIsNone(error)
        self.assertEqual(next_day_locked['set_id'], locked_set_id)
        self.assertEqual(next_day_locked['refresh_cost'], 1000)

        unlocked, error = db.set_user_title_shop_locked(self.user_a['id'], False)
        self.assertIsNone(error)
        self.assertFalse(unlocked['locked'])
        self.assertEqual(unlocked['set_id'], next_day_daily['set_id'])

    def test_offer_can_only_be_bought_once_per_set(self):
        shop, error = db.get_user_title_shop(self.user_a['id'])
        self.assertIsNone(error)
        offer = shop['offers'][0]
        result, error = db.purchase_user_title_shop_offer(
            self.user_a['id'], shop['set_id'], offer['slot'],
        )
        self.assertIsNone(error)
        self.assertEqual(result['shop']['balance']['total'], shop['balance']['total'] - offer['price'])
        owned = next(item for item in result['titles']['items'] if item['id'] == offer['id'])
        self.assertEqual(owned['quantity'], 1)

        result, error = db.purchase_user_title_shop_offer(
            self.user_a['id'], shop['set_id'], offer['slot'],
        )
        self.assertIsNone(result)
        self.assertIn('本轮已购买', error)

    def test_theme_and_alpha_title_styles_are_normalized(self):
        style = parse_title_style(
            '{color:#FF0000|id=left}Test{/}'
            '{rainbow|id=middle}Rainbow{/}'
            '{theme:light=#0000FF@50%;dark=#00FFFF@50%|id=right}Title{/}'
        )
        self.assertEqual(title_style_plain_text(style), 'TestRainbowTitle')
        self.assertEqual(style['segments'][1]['paint']['kind'], 'rainbow')
        self.assertEqual(style['segments'][2]['paint']['light']['color'], '#0000FF80')
        self.assertEqual(style['segments'][2]['paint']['dark']['color'], '#00FFFF80')


if __name__ == '__main__':
    unittest.main()
