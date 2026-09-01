from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
STORY = (ROOT / 'templates' / 'story.html').read_text(encoding='utf-8')
COMPAT_JS = (ROOT / 'static' / 'js' / 'card_compat.js').read_text(encoding='utf-8')
COMPAT_CSS = (ROOT / 'static' / 'css' / 'card_compat.css').read_text(encoding='utf-8')
STYLE_CSS = (ROOT / 'static' / 'css' / 'style.css').read_text(encoding='utf-8')
STORY_CSS = (ROOT / 'static' / 'css' / 'story.css').read_text(encoding='utf-8')


def test_shared_compatibility_assets_load_after_card_styles_and_before_renderers():
    assert INDEX.index('/static/css/style.css') < INDEX.index('/static/css/card_compat.css')
    assert STORY.index('/static/css/story.css') < STORY.index('/static/css/card_compat.css')
    assert INDEX.index('/static/js/card_compat.js') < INDEX.index('/static/js/game.js')
    assert STORY.index('/static/js/card_compat.js') < STORY.index('/static/js/story.js')


def test_modern_card_css_values_remain_the_source_of_truth():
    assert '--card-cost-size: 16cqi;' in STYLE_CSS
    assert '--card-name-font-scale: 9.5cqi;' in STYLE_CSS
    assert '--card-effect-font-scale: 9cqi;' in STYLE_CSS
    assert '--card-cost-size: 16cqi;' in STORY_CSS
    assert '--card-name-font-scale: 9.5cqi;' in STORY_CSS
    assert '--card-effect-font-scale: 9cqi;' in STORY_CSS


def test_compatibility_mode_requires_real_feature_or_layout_failure():
    assert "window.CSS.supports('container-type', 'inline-size')" in COMPAT_JS
    assert "window.CSS.supports('width', '1cqi')" in COMPAT_JS
    assert 'nestedFlexCenterWorks()' in COMPAT_JS
    assert 'legacyActive = !containerUnitsWork || flexFallbackActive;' in COMPAT_JS
    assert "classList.add(ROOT_CLASS)" in COMPAT_JS
    assert "classList.add(FLEX_CLASS)" in COMPAT_JS
    assert 'if (!legacyActive) return;' in COMPAT_JS


def test_legacy_metrics_follow_each_rendered_card_width():
    assert 'var unitPx = width / 100;' in COMPAT_JS
    assert "'--card-cost-size'" in COMPAT_JS
    assert "'--card-name-font-scale'" in COMPAT_JS
    assert "'--card-effect-font-scale'" in COMPAT_JS
    assert "'--card-english-font'" in COMPAT_JS
    assert "'--card-border-width'" in COMPAT_JS
    assert "width * 88 / 63" in COMPAT_JS
    assert 'MutationObserver' in COMPAT_JS
    assert 'ResizeObserver' in COMPAT_JS


def test_all_compatibility_rules_are_scoped_away_from_supported_devices():
    selectors = [
        line.strip()
        for line in COMPAT_CSS.splitlines()
        if line.strip().endswith('{') and not line.lstrip().startswith('/*')
    ]
    assert selectors
    assert all(
        selector.startswith('html.gtn-card-layout-legacy')
        or selector.startswith('html.gtn-card-flex-legacy')
        for selector in selectors
    )
    assert 'html.gtn-card-flex-legacy .card .card-costs .card-name' in COMPAT_CSS
    assert 'text-align: center;' in COMPAT_CSS
    assert '.card-effect {' not in COMPAT_CSS
