# -*- coding: utf-8 -*-
"""Play every official mod card once in 1v1 and 2v2 and report failures.

Rebuilt after the scratch directory was lost. It exercises the real engine
entry points (``play_card`` / ``resolve_choice`` / ``handle_response`` /
``handle_v2_ui_response``) with engine-generated default choices, so an
unknown op, a broken ``card_ref`` or a crashed handler shows up as a failure.
"""

from __future__ import annotations

import io
import pathlib
import random
import sys
import traceback

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app  # noqa: E402
import mod_loader  # noqa: E402
import mod_runtime_v2 as v2_rt  # noqa: E402
from cards import CARD_DEFS, CardInstance  # noqa: E402
from game_engine import EquipmentInstance, GameEngine  # noqa: E402
from game_engine_2v2 import GameEngine2v2  # noqa: E402

FILLER = "Sewage"
MAX_STEPS = 60
_TYPE_SAMPLES = {}


def type_samples(exclude_id):
    """One cheap vanilla card per card type, so pickers always have candidates."""
    if not _TYPE_SAMPLES:
        for card_id, card_def in CARD_DEFS.items():
            card_type = str(getattr(card_def, "card_type", "") or "")
            if not card_type or card_type in _TYPE_SAMPLES:
                continue
            if getattr(card_def, "cost_e", 0) or getattr(card_def, "cost_m", 0):
                continue
            _TYPE_SAMPLES[card_type] = card_id
    return [card_id for card_id in _TYPE_SAMPLES.values() if card_id != exclude_id]


def auto_v2_ui_values(engine, pending):
    """Build a valid response for every interactive control of a v2 UI pause."""
    component = pending.get("component") if isinstance(pending.get("component"), dict) else {}
    context = pending.get("context") if isinstance(pending.get("context"), dict) else {}
    values = {}
    for control in component.get("controls") or []:
        if not isinstance(control, dict):
            continue
        cid = str(control.get("id") or "").strip()
        if not cid:
            continue
        ctype = str(control.get("type") or "text")
        if ctype in ("text", "rich_text", "stat_display", "card_preview"):
            continue
        default = control.get("default")
        if ctype in ("slider", "number", "number_input"):
            minimum = v2_rt._to_number(v2_rt.eval_v2_value(engine, context, control.get("min", 0)))
            maximum = v2_rt._to_number(v2_rt.eval_v2_value(engine, context, control.get("max", minimum)))
            value = default if isinstance(default, (int, float)) else minimum
            values[cid] = int(max(minimum, min(maximum, value)))
        elif ctype in ("select", "card_catalog_picker"):
            options = v2_rt._control_options(control)
            allowed = [str(opt.get("value")) for opt in options]
            chosen = str(default) if default is not None else (allowed[0] if allowed else "")
            values[cid] = chosen
        elif ctype in ("card_picker", "equipment_picker", "multi_card_picker", "multi_equipment_picker"):
            multi = ctype.startswith("multi_")
            zone = str(control.get("zone") or ("equipment" if "equipment" in ctype else "hand"))
            target_id = v2_rt._player_id(
                engine, v2_rt.resolve_v2_target(engine, context, control.get("target", "source"))
            )
            picker_type = "equipment_picker" if "equipment" in ctype else "card_picker"
            allowed_ids = v2_rt._picker_instance_ids(engine, target_id, zone, picker_type)
            explicit = control.get("allowed_instance_ids")
            if isinstance(explicit, list):
                normalized = {int(v) for v in explicit if str(v).strip().lstrip("-").isdigit()}
                allowed_ids = [i for i in allowed_ids if i in normalized]
            minimum = max(0, v2_rt._to_int(control.get("min_select", 0 if multi else 1)))
            picked = allowed_ids[:minimum]
            values[cid] = picked if multi else (picked[0] if picked else None)
        elif ctype in ("player_picker", "target_picker"):
            allowed = control.get("allowed_player_ids")
            if isinstance(allowed, list) and allowed:
                first = None
                for candidate in allowed:
                    try:
                        first = int(candidate)
                        break
                    except Exception:
                        continue
                values[cid] = first if first is not None else 0
            elif isinstance(default, int):
                values[cid] = default
            else:
                values[cid] = v2_rt._player_id(
                    engine, v2_rt.resolve_v2_target(engine, context, control.get("target", "source"))
                )
        else:
            values[cid] = default
    buttons = component.get("buttons") if isinstance(component.get("buttons"), list) else []
    allowed_buttons = [str(btn.get("id")) for btn in buttons if isinstance(btn, dict) and btn.get("id")]
    return {"button": allowed_buttons[0] if allowed_buttons else "", "values": values}


def repair_choice(engine, pending, choice):
    """Fill in the card picks that the engine's default generator leaves empty."""
    if not isinstance(choice, dict):
        return choice
    choice_type = str(pending.get("choice_type") or "")
    params = pending.get("choice_params") if isinstance(pending.get("choice_params"), dict) else {}
    if choice_type not in ("choose_cards_from_hand", "choose_same_attacks_from_hand"):
        return choice
    player_id = int(pending.get("player_id", 0) or 0)
    target = str(params.get("target") or "self")
    owner_id = player_id if target in ("self", "source", "owner") else 1 - player_id
    owner_id = max(0, min(len(engine.players) - 1, owner_id))
    zone_name = str(params.get("zone") or "hand")
    zone = getattr(engine.players[owner_id], zone_name, None) or []
    card_type = str(params.get("card_type") or "")
    played = pending.get("card") if isinstance(pending.get("card"), dict) else {}
    played_iid = played.get("instance_id")
    picked = []
    for candidate in zone:
        if getattr(candidate, "instance_id", None) == played_iid:
            continue
        if card_type and str(getattr(candidate, "card_type", "")) != card_type:
            continue
        if not engine._card_selectable_by_action(candidate):
            continue
        picked.append(candidate.instance_id)
    minimum = max(1, v2_rt._to_int(params.get("min_count", 1)))
    current = [iid for iid in choice.get("target_instance_ids") or [] if iid in picked]
    if params.get("same_name") and len(current) >= 2:
        defs = {engine_card_def_id(engine, owner_id, iid) for iid in current}
        if len(defs) > 1:
            current = []
    if len(current) >= minimum:
        return choice
    choice = dict(choice)
    choice["target_instance_ids"] = picked[:minimum]
    return choice


def engine_card_def_id(engine, owner_id, instance_id):
    for candidate in engine.players[owner_id].hand:
        if getattr(candidate, "instance_id", None) == instance_id:
            return getattr(candidate, "def_id", "")
    return ""


def build_player_meta():
    loadout = app.build_mod_loadout()
    return {
        "v2_loadout": loadout["v2_loadout"],
        "v2_ui_components": loadout["v2_ui_components"],
        "allowed_card_ids": loadout["allowed_card_ids"],
    }


def prepare_player(player):
    player.hand = []
    player.deck = []
    player.discard = []
    player.exile = []
    player.equipment = []
    player.health = 100
    player.max_health = 100
    player.base_max_health = 100
    player.elixir = 99
    player.magic = 99
    player.armor = 0
    player.fire = 0
    player.poison = 0
    player.fracture = 0
    player.heal_block = 0
    player.custom_statuses = {}
    player.custom_vars = {}


def make_engine(engine_cls, player_meta):
    engine = engine_cls()
    app.apply_v2_loadout_to_engine(engine, player_meta)
    engine.phase = "action"
    engine.current_player = 0
    engine.game_over = False
    for player in engine.players:
        prepare_player(player)
    me = engine.players[0]
    me.deck = [CardInstance(FILLER) for _ in range(6)]
    me.discard = [CardInstance(FILLER) for _ in range(3)]
    me.exile = [CardInstance(FILLER) for _ in range(2)]
    me.equipment = [EquipmentInstance(CardInstance(FILLER), owner=0)]
    for other in engine.players[1:]:
        other.hand = [CardInstance(FILLER) for _ in range(3)]
        other.deck = [CardInstance(FILLER) for _ in range(4)]
        other.discard = [CardInstance(FILLER) for _ in range(2)]
        other.equipment = [EquipmentInstance(CardInstance(FILLER), owner=other.player_id)]
    return engine


def drain(engine, player_id, notes):
    """Answer engine-generated prompts until the engine is idle again."""
    for _ in range(MAX_STEPS):
        if getattr(engine, "pending_v2_ui", None):
            pending = engine.pending_v2_ui
            result = engine.handle_v2_ui_response(
                int(pending.get("player_id", player_id)),
                pending.get("request_id"),
                auto_v2_ui_values(engine, pending),
            )
            if not isinstance(result, dict) or not result.get("success", True):
                notes.append("v2ui-rejected:%s" % (result,))
                return False
            continue
        if getattr(engine, "pending_choice", None) is not None:
            pending = engine.pending_choice
            choice = engine._default_choice_for_pending(pending)
            if not isinstance(choice, dict):
                notes.append("no-default-choice:%s" % pending.get("choice_type"))
                engine.pending_choice = None
                return False
            choice = repair_choice(engine, pending, choice)
            result = engine.resolve_choice(int(pending.get("player_id", player_id)), choice)
            if not isinstance(result, dict) or result.get("success") is False:
                # Retry once with an empty (cancel) answer before giving up.
                retry = engine.resolve_choice(
                    int(pending.get("player_id", player_id)),
                    {"target_instance_ids": [], "cancelled": True},
                )
                if not isinstance(retry, dict) or retry.get("success") is False:
                    notes.append("choice-rejected:%s:%s" % (pending.get("choice_type"), result.get("error")))
                    engine.pending_choice = None
                    return False
            continue
        if getattr(engine, "pending_response", None) is not None:
            engine.handle_response(1 - int(player_id), None)
            continue
        return True
    notes.append("drain-step-limit")
    return False


def run_card(card_id, engine_cls, player_meta):
    notes = []
    engine = make_engine(engine_cls, player_meta)
    card = CardInstance(card_id)
    # Two copies of every type so "same name" choosers have a valid pair.
    samples = [CardInstance(sample) for sample in type_samples(card_id) for _ in range(2)]
    engine.players[0].hand = [card] + samples + [CardInstance(FILLER)]
    try:
        result = engine.play_card(0, card.instance_id, {})
    except Exception:
        return ["play-exception:" + traceback.format_exc(limit=4).strip().replace("\n", " | ")]
    if isinstance(result, dict) and result.get("success") is False:
        notes.append("play-failed:" + str(result.get("error")))
    if not drain(engine, 0, notes):
        pass
    # Let the end-of-turn / start-of-turn hooks for this card run as well.
    try:
        engine.end_turn(0)
    except Exception:
        notes.append("end-turn-exception:" + traceback.format_exc(limit=4).strip().replace("\n", " | "))
    drain(engine, 1, notes)
    return notes


def main():
    random.seed(20260910)
    mod_loader.merge_mod_cards_to_card_defs()
    player_meta = build_player_meta()
    if FILLER not in CARD_DEFS:
        raise SystemExit("filler card %s missing from CARD_DEFS" % FILLER)
    card_ids = sorted({
        card.id
        for mod in mod_loader.load_all_mods()
        if not mod.errors
        for card in mod.cards
        if card.id in CARD_DEFS
    })
    print("cards:", len(card_ids))
    failures = {}
    for index, card_id in enumerate(card_ids, 1):
        for engine_cls in (GameEngine, GameEngine2v2):
            notes = run_card(card_id, engine_cls, player_meta)
            hard = [
                note for note in notes
                if not note.startswith("play-failed:")
                and not note.startswith("no-default-choice:")
                and not note.startswith("choice-rejected:")
            ]
            if hard:
                failures["%s/%s" % (engine_cls.__name__, card_id)] = notes
        if index % 25 == 0:
            print("  ... %d/%d" % (index, len(card_ids)))
    print("=" * 70)
    if not failures:
        print("SMOKE OK: 0 failures across %d cards" % len(card_ids))
        return 0
    print("SMOKE FAILURES: %d" % len(failures))
    for key, notes in sorted(failures.items()):
        print("-", key)
        for note in notes[:3]:
            print("     ", note[:400])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
