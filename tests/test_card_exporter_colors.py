import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPORTER_CSS = (ROOT / 'static' / 'css' / 'card_exporter.css').read_text(encoding='utf-8')
EXPORTER_JS = (ROOT / 'static' / 'js' / 'card_exporter.js').read_text(encoding='utf-8')
EXPORTER_HTML = (ROOT / 'templates' / 'card_exporter.html').read_text(encoding='utf-8')


class CardExporterColorTests(unittest.TestCase):
    def test_exporter_does_not_override_shared_card_type_palette(self):
        for card_type in ('thorn', 'bloom', 'root', 'guard'):
            self.assertIsNone(
                re.search(rf'--{card_type}\s*:', EXPORTER_CSS),
                f'card exporter must inherit --{card_type} from style.css',
            )

    def test_card_list_uses_shared_card_type_variables(self):
        self.assertIn("return `var(--${TYPE_META[type] ? type : 'thorn'})`;", EXPORTER_JS)
        for stale_color in ('#ff8fb3', '#4d4d4d', '#5b8f48'):
            self.assertNotIn(stale_color, EXPORTER_JS.lower())

    def test_shared_stylesheet_loads_before_exporter_overrides(self):
        shared_index = EXPORTER_HTML.index('/static/css/style.css')
        exporter_index = EXPORTER_HTML.index('/static/css/card_exporter.css')
        self.assertLess(shared_index, exporter_index)

    def test_exporter_assets_have_updated_cache_versions(self):
        self.assertIn('style.css?v=card-exporter-renderer-24', EXPORTER_HTML)
        self.assertIn('card_exporter.css?v=card-exporter-renderer-22', EXPORTER_HTML)
        self.assertIn('game.js?v=card-exporter-renderer-23', EXPORTER_HTML)
        self.assertIn('card_exporter.js?v=card-exporter-renderer-22', EXPORTER_HTML)


if __name__ == '__main__':
    unittest.main()
