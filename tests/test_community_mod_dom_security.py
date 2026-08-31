from pathlib import Path


GAME_JS = Path(__file__).resolve().parents[1] / 'static' / 'js' / 'game.js'


def _function_source(source: str, name: str, next_name: str) -> str:
    return source.split(f'function {name}(', 1)[1].split(f'function {next_name}(', 1)[0]


def test_mod_card_names_tags_and_labels_are_html_escaped():
    source = GAME_JS.read_text(encoding='utf-8')
    builder = _function_source(source, 'renderSoloBuilder', 'renderSoloDeck')
    deck = _function_source(source, 'renderSoloDeck', 'clearSoloDeck')
    tags = _function_source(source, 'renderTagGallery', 'renderOpeningEventGallery')

    assert '${escapeHtml(getCardName(cd))}' in builder
    assert '${escapeHtml(getCardTypeLabel(cd.card_type))}' in builder
    assert '${cd ? escapeHtml(getCardName(cd))' in deck
    assert '${escapeHtml(flagText)}' in deck
    assert '${getCardName(cd)}' not in builder + deck
    assert '${escapeHtml(getFlagLabel(flag))}' in tags
    assert 'usedBy.map(getCardName).map(escapeHtml)' in tags
    assert '<h3>${getFlagLabel(' not in tags


def test_mod_opening_event_and_status_fields_are_html_escaped():
    source = GAME_JS.read_text(encoding='utf-8')
    events = _function_source(source, 'renderOpeningEventGallery', 'getAllStatusDefs')
    statuses = _function_source(source, 'renderStatusGallery', 'openRulesModal')
    selection = _function_source(source, 'renderEventSelect', 'renderEventReveal')

    assert '${escapeHtml(getLocalizedEventText(ev, \'name\') || \'?\')}' in events
    assert '<p><b>ID：</b>${escapeHtml(ev.id)}</p>' in events
    assert '${escapeHtml(s.source)}' in statuses
    assert '<p><b>ID：</b>${escapeHtml(s.key)}</p>' in statuses
    assert 'safeRegistryColor(ev.color || borderColors[ev.id], COLORS.magic)' in selection
    assert '${escapeHtml(getLocalizedEventText(ev, \'name\') || \'?\')}' in selection
    assert '${getLocalizedEventText(ev, \'name\') || \'?\'}' not in events + selection


def test_gallery_flag_badges_escape_builtin_and_unknown_labels():
    source = GAME_JS.read_text(encoding='utf-8')
    badge = _function_source(source, 'makeGalleryFlagHtml', 'getGalleryFlagDescription')
    assert badge.count('${escapeHtml(label)}') == 2
    assert '>${label}</span>' not in badge
