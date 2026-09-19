"""反馈修复批次：日志占位符（#150）、魔法叶可选中自己（#146）、生化状态中文（#159）。"""

import json
import re
import unittest
import zipfile
from pathlib import Path

from game_engine import GameEngine
from mod_loader import load_mod

import official_statuses


ROOT = Path(__file__).resolve().parents[1]
VANILLA_PACKAGE = ROOT / 'mods' / 'Vanilla Cards.gtnmod'
BIO_PACKAGE = ROOT / 'mods' / 'Bio Cards Addition.gtnmod'


class LogPlaceholderGuardTests(unittest.TestCase):
    def test_unresolved_placeholder_never_reaches_the_battle_log(self):
        """反馈 #150：模板占位符没被替换时，战报里不该出现 `{target}`。"""
        engine = GameEngine()
        engine.log_msg('{target}将1张[[card:Void]]加入手中')
        self.assertTrue(engine.log)
        self.assertFalse(any('{' in line for line in engine.log))
        self.assertIn('将1张', engine.log[-1])

    def test_move_card_give_formats_its_log_template(self):
        source = (ROOT / 'game_engine.py').read_text(encoding='utf-8')
        # move_card(mode:"give") 与 give_card_to_hand 都必须走 _format_step_log。
        self.assertNotIn('            if log and card_def.id != ERROR_CARD_ID:\n                self.log_msg(log)',
                         source)
        self.assertIn('name=card_def.name_cn,', source)

    def test_official_mod_logs_have_no_raw_braces_left(self):
        pattern = re.compile(r'\{[A-Za-z_][A-Za-z0-9_]*\}')
        for package in sorted((ROOT / 'mods').glob('*.gtnmod')):
            with zipfile.ZipFile(package) as archive:
                data = json.loads(archive.read('mod.json').decode('utf-8'))
            engine = GameEngine()
            for text in _iter_log_templates(data):
                engine.log_msg(text)
            for line in engine.log:
                self.assertIsNone(pattern.search(line), f'{package.name}: {line}')


def _iter_log_templates(node):
    if isinstance(node, dict):
        for key in ('log', 'message'):
            value = node.get(key)
            if isinstance(value, str) and value:
                yield value
        for value in node.values():
            yield from _iter_log_templates(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_log_templates(value)


class MagicLeafSelfTargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_mod(str(VANILLA_PACKAGE))
        if cls.mod.errors:
            raise AssertionError(cls.mod.errors)
        cls.card_defs = {card.id: card.to_card_def() for card in cls.mod.cards}

    def test_equipment_trigger_allows_self_target(self):
        """反馈 #146：魔法叶牌面写「选择一个目标」，就不能只允许敌方。"""
        leaf = self.card_defs['MagicLeaf']
        self.assertTrue((leaf.v2_resource or {}).get('trigger_allow_self'))
        engine = GameEngine()
        self.assertFalse(engine._equipment_trigger_forbids_self_target(leaf))

    def test_english_text_matches_the_numbers(self):
        with zipfile.ZipFile(VANILLA_PACKAGE) as archive:
            data = json.loads(archive.read('mod.json').decode('utf-8'))
        leaf = next(
            card for card in (data.get('registries') or {}).get('cards') or []
            if str(card.get('legacy_id')) == 'MagicLeaf'
        )
        text = str(leaf.get('effect_text_en') or '')
        self.assertIn('8D', text)
        self.assertNotIn('12D', text)
        self.assertIn('3M', text)
        self.assertNotIn('4M', text)


class BioStatusLocaleTests(unittest.TestCase):
    def test_chinese_locale_covers_every_bio_status(self):
        """反馈 #159 + Round 107 / 批次 DE：生化状态的中文文案由内置表提供。

        以前靠包内 `registries.statuses` + `locales/zh.json`；现在这两处都不再声明，
        文案统一在 `official_statuses.py`（客户端同步表由 sync_core_status_defs 生成）。
        """

        for status_id in ('bio:debt', 'bio:extra_healing', 'bio:shield_conversion'):
            entry = official_statuses.get_status(status_id)
            self.assertIsNotNone(entry)
            for lang in ('zh', 'en', 'fr', 'ja'):
                self.assertTrue(entry['name_i18n'].get(lang), f'{status_id} 缺 {lang} 名字')
                self.assertTrue(entry['desc_i18n'].get(lang), f'{status_id} 缺 {lang} 描述')
        with zipfile.ZipFile(BIO_PACKAGE) as archive:
            data = json.loads(archive.read('mod.json').decode('utf-8'))
        ids = [str(item.get('id')) for item in (data.get('registries') or {}).get('statuses') or []]
        self.assertEqual(ids, [])


if __name__ == '__main__':
    unittest.main()
