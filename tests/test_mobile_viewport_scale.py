from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("template_name", ["index.html", "story.html"])
def test_player_pages_use_seventy_percent_initial_mobile_scale(template_name):
    source = (ROOT / "templates" / template_name).read_text(encoding="utf-8")

    viewport_line = next(
        line for line in source.splitlines() if 'name="viewport"' in line
    )

    assert "width=device-width" in viewport_line
    assert "initial-scale=0.7" in viewport_line
    assert "maximum-scale" not in viewport_line
