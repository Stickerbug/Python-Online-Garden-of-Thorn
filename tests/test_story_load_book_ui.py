from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORY_JS = (ROOT / 'static/js/story.js').read_text(encoding='utf-8')
STORY_CSS = (ROOT / 'static/css/story.css').read_text(encoding='utf-8')


def test_story_book_slot_ui_uses_the_relic_scaled_limit():
    assert 'function storyEnchantmentBookLimit(playerLike)' in STORY_JS
    assert "String(relicId || '') === 'book_slots'" in STORY_JS
    assert 'renderStoryBookSlots' in STORY_JS
    assert 'story-hud-books-label' in STORY_JS


def test_foresight_reward_cards_auto_fit_instead_of_breaking_the_third_column():
    assert '#story-reward-options.story-card-choice-grid' in STORY_CSS
    assert 'repeat(auto-fit, minmax(150px, 1fr))' in STORY_CSS


def test_story_book_descriptions_reuse_the_card_rich_text_renderer():
    assert "appendStoryRichText(copy, localize(definition?.description) || '');" in STORY_JS
    assert "appendStoryRichText(description, localize(definition?.description) || '故事模式附魔书');" in STORY_JS


def test_story_book_references_reuse_card_term_row_style():
    references = STORY_JS[STORY_JS.index('function appendStoryInlineReferences('):]
    assert "list.className = 'story-card-terms-list';" in references
    assert 'appendStoryTermRow(list, {' in references
