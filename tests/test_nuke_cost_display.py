from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')


def test_multiplayer_nuke_displays_x_without_changing_numeric_cost_logic():
    helper = GAME_JS.split(
        'function getCardDisplayCostELabel',
        1,
    )[1].split(
        'function getFlagLabel',
        1,
    )[0]

    assert "if (isArcticNukeCard(cardDict, cardDef)) return 'X';" in helper
    assert 'const displayCostE = getCardDisplayCostELabel(cardDict, cardDef, totalE);' in GAME_JS
    assert 'const displayCostE = getCardDisplayCostELabel(cardDict, cardDef, costs.totalE);' in GAME_JS
    assert 'getCardDisplayCostELabel({ def_id: defId }, cd, cd.cost_e)' in GAME_JS
    assert 'const { totalE, totalM } = getCardDisplayCosts(cardDict, cardDef, you);' in GAME_JS
