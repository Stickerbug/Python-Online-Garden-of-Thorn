from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / "static" / "js" / "game.js").read_text(encoding="utf-8")
STYLE_CSS = (ROOT / "static" / "css" / "style.css").read_text(encoding="utf-8")


def test_pvp_gallery_freezes_filtered_card_order_for_term_navigation():
    assert "function openGalleryTermIntro(cardIds, index, sourceEl = null)" in GAME_JS
    assert "galleryTermNavigation = { cards, index: normalizedIndex };" in GAME_JS
    assert "openGalleryTermIntro(ids, i, wrap);" in GAME_JS
    assert "function navigateGalleryTermIntro(offset, options = {})" in GAME_JS
    assert "navigation.index = (navigation.index + Number(offset || 0) + total) % total;" in GAME_JS


def test_pvp_gallery_term_overlay_supports_buttons_wheel_keys_and_swipe():
    assert "className = 'term-intro-navigation'" in GAME_JS
    assert "className = 'term-intro-nav-button'" in GAME_JS
    assert "cardWrap?.addEventListener('wheel'" in GAME_JS
    assert "galleryTermWheelLockedUntil = now + 220;" in GAME_JS
    assert "Number(event.deltaX || 0)" in GAME_JS
    assert "event.key === 'ArrowLeft' || event.key === 'ArrowRight'" in GAME_JS
    assert "cardWrap?.addEventListener('pointerdown'" in GAME_JS
    assert "Math.abs(dx) < 42 || Math.abs(dx) <= Math.abs(dy) * 1.15" in GAME_JS


def test_pvp_gallery_navigation_is_not_retained_for_battle_or_status_previews():
    show_card = GAME_JS.split("function showTermIntroForCard", 1)[1].split(
        "function showTermIntroForStatus", 1
    )[0]
    show_status = GAME_JS.split("function showTermIntroForStatus", 1)[1].split(
        "function showTermIntroForTokenKey", 1
    )[0]
    assert "if (cardOptions.galleryNavigation)" in show_card
    assert "else clearGalleryTermNavigation();" in show_card
    assert "clearGalleryTermNavigation();" in show_status
    assert "clearGalleryTermNavigation();" in GAME_JS.split(
        "function hideTermIntroOverlay", 1
    )[1].split("function isTermIntroOverlayVisible", 1)[0]


def test_pvp_gallery_navigation_has_accessible_responsive_styling():
    assert ".term-intro-navigation {" in STYLE_CSS
    assert "grid-template-columns: 42px minmax(0, 1fr) 42px;" in STYLE_CSS
    assert ".term-intro-nav-button:focus-visible" in STYLE_CSS
    assert ".term-intro-nav-progress {" in STYLE_CSS
