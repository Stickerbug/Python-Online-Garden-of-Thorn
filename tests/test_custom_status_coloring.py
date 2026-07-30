import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / "static" / "js" / "game.js").read_text(encoding="utf-8")
BIO_MOD = ROOT / "mods" / "Bio Cards Addition.gtnmod"


def test_bio_statuses_define_their_display_colors():
    with zipfile.ZipFile(BIO_MOD) as archive:
        manifest = json.loads(archive.read("mod.json").decode("utf-8"))

    statuses = {
        status["id"]: status
        for status in manifest["registries"]["statuses"]
    }
    assert statuses["bio:debt"]["color"] == "#B36B32"
    assert statuses["bio:extra_healing"]["color"] == "#D56A9B"


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
