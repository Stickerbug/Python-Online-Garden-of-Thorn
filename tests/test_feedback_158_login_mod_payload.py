"""反馈 #158：从天梯回主页再进多人时，登录包里必须带「要进的那个模式」的模组选择。

``getModLoginPayload()`` 默认拿 ``getSettingsModMatchMode()``，而它在多人流程之外
恒为 casual_1v1；``emitSocketLogin`` 又用 localStorage 的 preferred_mode 去申请
（可能是天梯），于是服务端按娱乐那份选择建了天梯 loadout —— 玩家看到的
「选择的模组炸掉」。
"""

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')


def _function_source(name: str, next_name: str) -> str:
    body = GAME_JS.split(f'function {name}(', 1)[1].split(f'function {next_name}(', 1)[0]
    return f'function {name}({body}'


def test_login_uses_the_mode_being_entered():
    emit_login = GAME_JS.split('function emitSocketLogin(', 1)[1].split('\n}', 1)[0]
    assert '...getModLoginPayload(preferredMode),' in emit_login
    assert 'function getModLoginPayload(matchMode = getSettingsModMatchMode())' in GAME_JS
    assert 'getDisabledMods(matchMode)' in GAME_JS
    assert 'hasSavedDisabledModsPreference(matchMode)' in GAME_JS
    assert 'function hasSavedDisabledModsPreference(mode = getSettingsModMatchMode())' in GAME_JS
    assert 'const storageKey = disabledModsStorageKey(mode);' in GAME_JS


def test_storage_keys_follow_the_requested_mode():
    node = shutil.which('node')
    assert node, 'node is required for this behaviour test'
    storage_keys = (
        "const DISABLED_MODS_STORAGE_KEYS = "
        "{ casual: 'gtn_disabled_mods', ranked: 'gtn_disabled_mods_ranked' };"
    )
    helpers = "\n".join([
        storage_keys,
        _function_source('isRankedMatchMode', 'getCurrentPvpMatchMode'),
        _function_source('disabledModsStorageKey', 'hasSavedDisabledModsPreference'),
        _function_source('hasSavedDisabledModsPreference', 'getDisabledMods'),
    ])
    script = f'''
function normalizeMatchModeKey(mode) {{
    return String(mode || 'casual_1v1');
}}
const store = {{ 'gtn_disabled_mods_ranked': JSON.stringify(['Void Cards DLC.gtnmod']) }};
const localStorage = {{
    getItem: (key) => (key in store ? store[key] : null),
    setItem: (key, value) => {{ store[key] = String(value); }},
}};
function getSettingsModMatchMode() {{ return 'casual_1v1'; }}
{helpers}
console.log(JSON.stringify({{
    defaultKey: disabledModsStorageKey(),
    rankedKey: disabledModsStorageKey('ranked_1v1'),
    defaultSaved: hasSavedDisabledModsPreference(),
    rankedSaved: hasSavedDisabledModsPreference('ranked_1v1'),
}}));
'''
    result = subprocess.run(
        [node, '-e', script],
        capture_output=True,
        text=True,
        encoding='utf-8',
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip())
    assert payload == {
        'defaultKey': 'gtn_disabled_mods',
        'rankedKey': 'gtn_disabled_mods_ranked',
        'defaultSaved': False,
        'rankedSaved': True,
    }
