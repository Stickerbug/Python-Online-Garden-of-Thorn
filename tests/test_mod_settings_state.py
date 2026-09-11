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
    def test_ranked_and_casual_mod_selection_use_separate_storage_keys(self):
        """建议 #82：天梯与娱乐各存一套官方模组选择，互不覆盖。"""
        helper = source_between(
            GAME_JS,
            'const DISABLED_MODS_STORAGE_KEYS',
            'function getDisabledMods(',
        )
        self.assertIn("casual: 'gtn_disabled_mods'", helper)
        self.assertIn("ranked: 'gtn_disabled_mods_ranked'", helper)
        self.assertIn('isRankedMatchMode(mode)', helper)
        self.assertIn('function hasSavedDisabledModsPreference()', helper)

        getter = source_between(
            GAME_JS,
            'function getDisabledMods(',
            'function writeDisabledModsPreference(',
        )
        self.assertIn('disabledModsStorageKey(', getter)
        # 天梯键还没写过时回退读娱乐键（一次性迁移），但不能把娱乐键当写入目标。
        self.assertIn('DISABLED_MODS_STORAGE_KEYS.casual', getter)
        self.assertNotIn("localStorage.setItem('gtn_disabled_mods'", getter)

        writer = source_between(
            GAME_JS,
            'function writeDisabledModsPreference(',
            'function reconcileKnownBundledMods(',
        )
        self.assertIn('disabledModsStorageKey()', writer)
        self.assertNotIn("localStorage.setItem('gtn_disabled_mods'", writer)

        login_payload = source_between(
            GAME_JS,
            'function getModLoginPayload()',
            'function getModSettingsUpdatePayload()',
        )
        self.assertIn('hasSavedDisabledModsPreference()', login_payload)

    def test_mode_switch_syncs_that_modes_selection_before_set_mode(self):
        """建议 #82：切模式前先把目标模式那份模组选择推给服务端，set_mode 才会用它重建 loadout。"""
        handler = source_between(
            GAME_JS,
            'tab.onclick = async () => {',
            "socket.emit('set_mode'",
        )
        self.assertIn('requestModSettingsUpdate(', handler)
        self.assertIn('getDisabledMods(newMode)', handler)

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

    def test_login_payload_omits_disabled_mods_until_a_preference_is_saved(self):
        login_payload = source_between(
            GAME_JS,
            'function getModLoginPayload()',
            'function getModSettingsUpdatePayload()',
        )
        # 建议 #82 起按当前模式取键（娱乐 gtn_disabled_mods / 天梯 gtn_disabled_mods_ranked）。
        self.assertIn('hasSavedDisabledModsPreference()', login_payload)
        self.assertIn('...(hasSavedPreference ? { disabled_mods: getDisabledMods() } : {})', login_payload)

    def test_settings_update_still_sends_an_explicit_disabled_list(self):
        settings_payload = source_between(
            GAME_JS,
            'function getModSettingsUpdatePayload()',
            'function getBundledModCheckboxes()',
        )
        self.assertIn('disabled_mods: getDisabledMods(),', settings_payload)
        self.assertIn('client_revision: modSettingsPreferenceRevision', settings_payload)

    def test_new_player_default_is_not_baked_into_disabled_preference(self):
        section = source_between(
            GAME_JS,
            'function getDisabledMods(',
            'function writeDisabledModsPreference(',
        )
        self.assertIn('const hasSavedPreference = raw !== null;', section)
        self.assertIn('if (hasSavedPreference) {', section)

    def test_bundled_mod_list_is_applied_before_hidden_settings_guard(self):
        loader = source_between(
            GAME_JS,
            'async function loadSettingsMods()',
            'function settingsModDetailKey(',
        )
        data_index = loader.index('settingsMods = mods || [];')
        reconcile_index = loader.index('reconcileKnownBundledMods();')
        hidden_guard = loader.index("classList.contains('hidden'))) return")
        self.assertLess(data_index, hidden_guard)
        self.assertLess(reconcile_index, hidden_guard)

    def test_baked_default_list_is_repaired_after_real_mod_list_arrives(self):
        reconcile = source_between(
            GAME_JS,
            'function reconcileKnownBundledMods()',
            'function getDefaultDisabledMods()',
        )
        self.assertIn('missingDefaults', reconcile)
        self.assertIn('markExplicit: false', reconcile)
        self.assertIn('hasSavedDisabledModsPreference()', reconcile)
        self.assertIn('localStorage.getItem(\'gtn_known_official_mods\')', reconcile)
        self.assertIn('localStorage.getItem(disabledModsStorageKey())', reconcile)

    def test_split_dlc_mods_are_disabled_before_the_first_settings_open(self):
        section = source_between(
            GAME_JS,
            'function getDisabledMods(',
            'function writeDisabledModsPreference(',
        )
        self.assertIn('if (!Array.isArray(disabled)) disabled = getDefaultDisabledMods()', section)
        self.assertIn('V11_DLC_DEFAULT_MIGRATION_KEY', section)
        self.assertIn('...V11_DLC_MOD_FILENAMES', section)
        self.assertIn('localStorage.setItem(storageKey,', section)
        self.assertIn('disabledModsStorageKey(', section)

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
