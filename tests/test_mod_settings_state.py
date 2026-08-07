import ast
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
APP_PY = (ROOT / 'app.py').read_text(encoding='utf-8')


def source_between(source, start, end):
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


def load_standalone_python_function(source, function_name):
    tree = ast.parse(source)
    function_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    )
    module = ast.Module(body=[function_node], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {}
    exec(compile(module, '<isolated-function>', 'exec'), namespace)
    return namespace[function_name]


class ModSettingsStateTests(unittest.TestCase):
    def test_invite_accept_does_not_rebuild_preferences_from_hidden_checkboxes(self):
        section = source_between(
            GAME_JS,
            'async function syncModSelectionBeforeInviteAccept()',
            'function buildModQueryString()',
        )
        self.assertNotIn('syncCurrentSettingsModSelectionToLocal()', section)

    def test_only_correlated_update_path_emits_mod_settings(self):
        self.assertEqual(GAME_JS.count("socket.emit('update_mod_settings'"), 1)
        request_section = source_between(
            GAME_JS,
            'function requestModSettingsUpdate(',
            'async function saveDisabledMods()',
        )
        self.assertIn("socket.emit('update_mod_settings'", request_section)
        self.assertIn('client_revision', request_section)

    def test_failed_or_unknown_response_cannot_replace_local_preferences(self):
        handler = source_between(
            GAME_JS,
            "bindSocketEvent('mod_settings_updated'",
            "bindSocketEvent('mod_mismatch'",
        )
        self.assertIn('if (!pending)', handler)
        self.assertIn('pending.preferenceRevision !== modSettingsPreferenceRevision', handler)
        failure_branch = handler[handler.index('const message = formatModSettingsResultMessage(data);'):]
        self.assertNotIn("gtn_disabled_mods", failure_branch)
        self.assertNotIn('writeDisabledModsPreference(', failure_branch)

    def test_new_bundled_mods_are_disabled_until_explicitly_selected(self):
        reconcile = source_between(
            GAME_JS,
            'function reconcileKnownBundledMods()',
            'function getDefaultDisabledMods()',
        )
        self.assertIn('newlyAdded', reconcile)
        self.assertIn('writeDisabledModsPreference([...getDisabledMods(), ...newlyAdded])', reconcile)
        self.assertIn("'Jurassic Cards Addition.gtnmod'", GAME_JS)
        self.assertIn("'Bio Cards Addition.gtnmod'", GAME_JS)

    def test_split_dlc_mods_are_disabled_before_the_first_settings_open(self):
        section = source_between(
            GAME_JS,
            'function getDisabledMods()',
            'function writeDisabledModsPreference(',
        )
        self.assertIn('if (!Array.isArray(disabled)) disabled = getDefaultDisabledMods()', section)
        self.assertIn('V11_DLC_DEFAULT_MIGRATION_KEY', section)
        self.assertIn('...V11_DLC_MOD_FILENAMES', section)
        self.assertIn("localStorage.setItem('gtn_disabled_mods'", section)

    def test_server_rejects_out_of_order_mod_setting_revisions(self):
        self.assertIn('MOD_SETTINGS_STALE_REQUEST', APP_PY)
        self.assertIn('_mod_settings_latest_requested_revision', APP_PY)
        self.assertIn("client_revision < int(player.get('_mod_settings_latest_requested_revision', -1))", APP_PY)

    def test_client_revision_validation(self):
        normalize = load_standalone_python_function(
            APP_PY,
            '_normalize_mod_settings_client_revision',
        )
        self.assertIsNone(normalize(None))
        self.assertIsNone(normalize(''))
        self.assertEqual(normalize('17'), 17)
        for value in (True, -1, 2_147_483_648, 'invalid'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize(value)

    def test_missing_disabled_mods_never_means_enable_every_mod(self):
        tree = ast.parse(APP_PY)
        function_node = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == 'resolve_disabled_mods_payload'
        )
        module = ast.Module(body=[function_node], type_ignores=[])
        ast.fix_missing_locations(module)
        namespace = {
            'normalize_disabled_mods': lambda value: list(value or []),
            'default_disabled_mods': lambda: ['default-disabled.gtnmod'],
        }
        exec(compile(module, '<isolated-function>', 'exec'), namespace)
        resolve = namespace['resolve_disabled_mods_payload']
        self.assertEqual(resolve({}), ['default-disabled.gtnmod'])
        self.assertEqual(resolve({}, fallback=['saved.gtnmod']), ['saved.gtnmod'])
        with self.assertRaises(ValueError):
            resolve({}, require_explicit=True)
        with self.assertRaises(ValueError):
            resolve({'disabled_mods': None})

    def test_peer_matching_rejects_an_incomplete_payload(self):
        section = source_between(
            GAME_JS,
            'async function applyPeerModSettings(',
            'function syncCurrentSettingsModSelectionToLocal(',
        )
        validation = section.index("Object.prototype.hasOwnProperty.call(peerMods, 'disabled_mods')")
        write = section.index('writeDisabledModsPreference(disabled)')
        self.assertLess(validation, write)
        self.assertNotIn(': [];', section[:write])

    def test_new_matches_revalidate_the_official_card_pool(self):
        helper = source_between(
            APP_PY,
            'def validated_match_allowed_card_ids(',
            'def player_loadout_hash(',
        )
        self.assertIn('expected = set(get_allowed_card_ids(disabled_mods))', helper)
        self.assertIn('stored = expected', helper)


if __name__ == '__main__':
    unittest.main()
