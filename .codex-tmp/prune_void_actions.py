# -*- coding: utf-8 -*-
"""Delete the ``_run_simple_action`` branches whose actions are now data steps."""

import io, re, sys, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import json
import zipfile

CONVERTED = (
    "bomb_attack", "fire_bomb_attack", "magic_bomb_attack", "pipe_bomb_attack",
    "dvd_attack", "dvd_return", "fan_turn_start", "schizo_turn_start",
    "add_void_to_hand", "apply_status", "one_ring", "comb_statuses",
    "magic_slime_ball", "blood_scythe", "hexagram", "magic_blood_scythe",
    "plasma_attack", "charge_hand",
    "fan_play", "horn_response", "magic_nut_attack", "magic_blood_scythe_exile",
)

# Safety: refuse to delete an action that some card data still calls.
still_used = set()
for package in (ROOT / "mods").glob("*.gtnmod"):
    with zipfile.ZipFile(package) as archive:
        spec = json.loads(archive.read("mod.json"))
    text = json.dumps(spec, ensure_ascii=False)
    for action in CONVERTED:
        if '"action": "%s"' % action in text:
            still_used.add(action)
if still_used:
    print("still referenced by card data, skipping:", sorted(still_used))

targets = [action for action in CONVERTED if action not in still_used]
path = ROOT / "void_dlc_runtime.py"
source = path.read_text(encoding="utf-8")
lines = source.splitlines(keepends=True)
removed, skipped = [], []
for action in targets:
    pattern = re.compile(r"\n(\s*)(?:el)?if action (?:==|in) [^\n]*%s[^\n]*:\n" % re.escape(action))
    match = pattern.search(source)
    if not match:
        skipped.append(action)
        continue
    start = match.start() + 1
    indent = len(match.group(1))
    end = len(source)
    cursor = match.end()
    for line in source[match.end():].splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith(("elif action", "else:")) and (len(line) - len(line.lstrip())) <= indent:
            end = cursor
            break
        cursor += len(line)
    # also drop a leading blank line that separated the branches
    if source[:start].rstrip("\n").endswith(":") is False and source[start - 2:start] == "\n\n":
        start += 1
    source = source[:start] + source[end:]
    removed.append(action)
path.write_text(source, encoding="utf-8")
print("removed:", removed)
print("not found:", skipped)

# Removing the first branch leaves the next one starting with ``elif``.
source = path.read_text(encoding="utf-8")
start = source.find("def _run_simple_action")
body_end = source.find("\ndef ", start + 10)
body = source[start:body_end]
head_end = body.find("targets = _action_targets")
tail = body[head_end:]
if tail.lstrip().startswith("elif action"):
    index = tail.index("elif action")
    tail = tail[:index] + "if action" + tail[index + len("elif action"):]
    source = source[:start + head_end] + tail + source[body_end:]
    path.write_text(source, encoding="utf-8")
    print("promoted first elif -> if")
