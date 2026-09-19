import json
import zipfile
from pathlib import Path

import official_statuses


ROOT = Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / "static" / "js" / "game.js").read_text(encoding="utf-8")
BIO_MOD = ROOT / "mods" / "Bio Cards Addition.gtnmod"


def test_bio_statuses_define_their_display_colors():
    """Round 107 / 批次 DE：颜色改由内置表提供（包内声明已删）。"""

    assert official_statuses.get_status("bio:debt")["color"] == "#B36B32"
    assert official_statuses.get_status("bio:extra_healing")["color"] == "#D56A9B"
    assert official_statuses.get_status("bio:shield_conversion")["color"] == "#2E7D7D"
    with zipfile.ZipFile(BIO_MOD) as archive:
        manifest = json.loads(archive.read("mod.json").decode("utf-8"))
    declared = {status.get("id") for status in (manifest.get("registries") or {}).get("statuses") or []}
    assert "bio:debt" not in declared
    assert "bio:extra_healing" not in declared


def test_all_custom_statuses_join_card_and_log_coloring_rules():
    assert "Object.entries(CUSTOM_STATUS_DEFS || {}).forEach(([statusKey, customDef]) => {" in GAME_JS
    assert "termKey: `status:${statusKey}`" in GAME_JS
    assert "color: item.color || ''" in GAME_JS
    assert "iconKey," in GAME_JS
    assert "explicitIconKey || getCardTextTokenIconKey(cls, text)" in GAME_JS
    assert "iconKey: rule.iconKey" in GAME_JS
    assert "const registeredStatusIconUrl = getStatusIconUrl(key);" in GAME_JS


def test_short_or_localized_status_keys_resolve_only_unique_custom_statuses():
    assert "normalizedId.split(':').pop() === comparable" in GAME_JS
    assert "Object.values((def && def.name_i18n) || {})" in GAME_JS
    assert "return matches.length === 1 ? matches[0][1] : null;" in GAME_JS


def test_extra_healing_term_requires_an_explicit_status_stack_reference():
    assert "if (normalizedId === 'extra_healing')" in GAME_JS
    assert "explicitStatusToken || explicitStack" in GAME_JS
