import pathlib
import unittest

from cards import (
    CARD_DEFS,
    CardDef,
    fixed_same_type_draw_ratio,
    same_type_draw_probabilities,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]


def make_card(def_id, card_type, count):
    return CardDef(
        def_id,
        def_id,
        def_id,
        1,
        0,
        card_type,
        count,
        'Common',
        '',
        '',
    )


class SameTypeDrawProbabilityTests(unittest.TestCase):
    def setUp(self):
        self.added_ids = []

    def tearDown(self):
        for def_id in self.added_ids:
            CARD_DEFS.pop(def_id, None)

    def add_card(self, def_id, card_type, count):
        self.added_ids.append(def_id)
        CARD_DEFS[def_id] = make_card(def_id, card_type, count)

    def test_weights_are_normalized_within_each_card_type(self):
        self.add_card('TestProbabilityThornA', 'thorn', 1)
        self.add_card('TestProbabilityThornB', 'thorn', 3)
        self.add_card('TestProbabilityBloom', 'bloom', 2)
        allowed = set(self.added_ids)

        probabilities = same_type_draw_probabilities(allowed)

        self.assertAlmostEqual(probabilities['TestProbabilityThornA'], 0.25)
        self.assertAlmostEqual(probabilities['TestProbabilityThornB'], 0.75)
        self.assertAlmostEqual(probabilities['TestProbabilityBloom'], 1.0)

    def test_fixed_sewage_ratio_matches_real_draft_weighting(self):
        self.add_card('TestProbabilityBloomOther', 'bloom', 86)

        probabilities = same_type_draw_probabilities({
            'Sewage',
            'TestProbabilityBloomOther',
        })

        self.assertAlmostEqual(probabilities['Sewage'], 0.14)
        self.assertAlmostEqual(probabilities['TestProbabilityBloomOther'], 0.86)
        self.assertAlmostEqual(fixed_same_type_draw_ratio('Sewage'), 0.14)
        self.assertIsNone(fixed_same_type_draw_ratio('Rose'))


class CardSourceProbabilityUiContractTests(unittest.TestCase):
    def test_card_api_and_shared_term_panel_expose_metadata(self):
        app_source = (ROOT / 'app.py').read_text(encoding='utf-8')
        game_source = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
        style_source = (ROOT / 'static' / 'css' / 'style.css').read_text(encoding='utf-8')

        self.assertIn("'same_type_draw_probability': round(", app_source)
        self.assertIn(
            "'fixed_same_type_draw_ratio': fixed_same_type_draw_ratio(def_id)",
            app_source,
        )
        self.assertIn('function buildCardSourceMetaHtml(cardDef)', game_source)
        self.assertIn('function getGallerySameTypeDrawProbability(cardDef)', game_source)
        self.assertIn('gallerySelectedModKeys.has(item.key)', game_source)
        self.assertIn('来源模组', game_source)
        self.assertIn('同类型牌抽到概率', game_source)
        self.assertIn("zh: '无法抽到'", game_source)
        self.assertIn('(probability * 100).toFixed(2)', game_source)
        self.assertIn(
            '`${buildCardSourceMetaHtml(cardDef)}${buildCardIntroSummaryHtml(cardDef)}',
            game_source,
        )
        self.assertIn('def hidden_disabled_entertainment_card_ids', app_source)
        self.assertIn('disabled_entertainment_mod_filenames(disabled_mods)', app_source)
        self.assertIn('def get_all_mod_shared_card_memberships(excluded_mod_filenames=None)', app_source)
        self.assertIn('entertainment_disabled if include_all_mods else None', app_source)
        self.assertIn("params.set('disabled_mods', getDisabledMods().join(','))", game_source)
        self.assertIn('const previousListScrollTop = list.scrollTop || 0;', game_source)
        self.assertIn('list.scrollTop = previousListScrollTop;', game_source)
        self.assertIn('Math.min(previousListScrollTop, Math.max(0, list.scrollHeight - list.clientHeight))', game_source)
        self.assertIn('.term-intro-card-meta {', style_source)
        self.assertIn('.term-intro-card-meta-probability', style_source)


if __name__ == '__main__':
    unittest.main()
