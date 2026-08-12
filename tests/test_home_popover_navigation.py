from pathlib import Path


GAME_JS = (
    Path(__file__).resolve().parents[1] / 'static' / 'js' / 'game.js'
).read_text(encoding='utf-8')


def test_leaving_home_closes_every_home_popover():
    start = GAME_JS.index('function showView(viewId)')
    end = GAME_JS.index('\nfunction ', start + 1)
    show_view = GAME_JS[start:end]
    close_block = show_view.split("if (viewId !== 'view-login') {", 1)[1].split('}', 1)[0]

    expected = (
        'toggleAccountPopover(false);',
        'toggleFriendsPopover(false);',
        'toggleStatsPopover(false);',
        'toggleChangelogPopover(false);',
        'toggleAchievementsPopover(false);',
        'toggleLeaderboardPopover(false);',
    )
    for call in expected:
        assert call in close_block
