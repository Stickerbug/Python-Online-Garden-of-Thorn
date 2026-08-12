import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReplayVideoExportBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "static" / "js" / "game.js").read_text(encoding="utf-8")

    def test_bridge_version_matches_current_exporter(self):
        self.assertIn("window.GTNReplayVideoBridge = {\n    version: 13,", self.source)

    def test_export_loads_all_bundled_mods_independent_of_browser_settings(self):
        self.assertIn("function buildReplayExportModQueryString", self.source)
        self.assertIn("params.set('disabled_mods', '');", self.source)
        self.assertIn("fetchReplayExportCardDefs(accountReplayData)", self.source)

    def test_export_preserves_replay_community_mod_selection(self):
        self.assertIn("params.set('community_mods', JSON.stringify(communityMods));", self.source)


if __name__ == "__main__":
    unittest.main()
