# -*- coding: utf-8 -*-
"""Round 1 rules for ``mods/Ocean Cards Addition.gtnmod``.

Converts the ocean card-specific engine atoms that can be expressed with the
generic mod-runtime ops:

* ``ocean_for_each_selectable_target`` -> ``all_enemies`` (the cards without
  ``self_target``), which is exactly the list ``_wide_strike_target_ids`` builds
  for the wide-strike cards that wrap their body in this atom.  The body is kept
  verbatim so the damage/hit semantics stay per target.
* ``ocean_magic_coral_tick`` -> ``var_add`` on the ``ocean_action_skip_turns``
  player var, gated by ``last_damage`` like the engine atom did.
* ``ocean_spikeball_damage`` -> a data-side ``if`` on the boosted instance flag
  that grants ``precision`` / ``wide_strike`` and switches the damage mode
  (single target vs. ``all_players``, matching ``_ocean_selectable_targets``
  with ``allow_self=True, enemies_only=False``).

The two remaining ocean atoms (``ocean_mark_auto_play`` / ``ocean_sapphire_mark``)
are intentionally left alone: they feed the engine's turn-start auto-play queue,
which is a missing generic capability.  See the Round 1 report.
"""

from __future__ import annotations

#: Instance flag written by the engine while the spikeball effect resolves.
SPIKEBALL_BOOSTED_FLAG = "ocean_spikeball_boosted"


def _spikeball_steps(params: dict) -> list:
    """``ocean_spikeball_damage``: boosted copies hit every selectable player."""
    base_amount = params.get("amount", 6)
    boosted_amount = params.get("boosted_amount", 20)
    return [
        {
            "op": "if",
            "condition": {
                "op": "card_has_tag",
                "card": "current_card",
                "tag": SPIKEBALL_BOOSTED_FLAG,
            },
            "then": [
                {
                    "op": "add_tag",
                    "card": "current_card",
                    "tag": "precision",
                    "silent": True,
                    "log": False,
                },
                {
                    "op": "add_tag",
                    "card": "current_card",
                    "tag": "wide_strike",
                    "silent": True,
                    "log": False,
                },
                {
                    "op": "deal_damage",
                    "target": "all_players",
                    "amount": boosted_amount,
                },
            ],
            "else": [
                {
                    "op": "deal_damage",
                    "target": params.get("target", "target"),
                    "amount": base_amount,
                },
            ],
        },
    ]


def _flatten_step(step: dict, target: str | None) -> dict:
    """Normalise a legacy ``{"type": name, "params": {...}}`` step.

    Older packages (``Hel Cards Addition``) still store steps in the legacy
    shape, so a rule that only looked at top-level keys silently produced a
    step that kept ``target: "target"``.  Flattening keeps the rewrite honest
    for both shapes and lets the target selector be replaced.
    """

    if "params" in step or "type" in step:
        name = step.get("op") or step.get("type")
        body = dict(step.get("params") or {})
        for key, value in step.items():
            if key in ("op", "type", "params"):
                continue
            body.setdefault(key, value)
        new_step = dict(body)
        new_step["op"] = name
    else:
        new_step = dict(step)
    if target is not None and new_step.get("target") == "target":
        new_step["target"] = target
    return new_step


def _for_each_selectable_steps(params: dict, target: str = "wide_strike_targets") -> list:
    """Fan a legacy ``body`` out over the card's wide-strike targets.

    ``_atomic_ocean_for_each_selectable_target`` iterated
    ``_wide_strike_target_ids``, which depends on the card's ``self_target``
    flag (and on the play-time target snapshot).  ``all_enemies`` /
    ``all_selectable`` only approximate that list, so the data steps use the
    ``wide_strike_targets`` selector, which the v2 runtime resolves through the
    same engine helper.
    """

    body = params.get("body") or params.get("steps") or []
    steps = []
    for step in body:
        if not isinstance(step, dict):
            continue
        flat = _flatten_step(step, None)
        if flat.get("op") == "apply_burn":
            # ``apply_burn`` resolves a single player, so it has to become the
            # multi-target ``status_add_named`` for the selector to fan out.
            steps.append(
                {
                    "op": "status_add_named",
                    "status": "fire",
                    "amount": flat.get("amount", 1),
                    "target": target,
                    "log": "{target}+{amount}层灼烧",
                }
            )
            continue
        steps.append(_flatten_step(step, target))
    return steps


def _magic_coral_tick_steps(params: dict) -> list:
    """``ocean_magic_coral_tick``: only ticks when the coral damage connected."""
    return [
        {
            "op": "if",
            "condition": {
                "op": "compare",
                "a": {"op": "last_damage"},
                "operator": ">",
                "b": 0,
            },
            "then": [
                {
                    "op": "var_add",
                    "target": "all_players",
                    "name": "ocean_action_skip_turns",
                    "value": params.get("times", 1),
                },
                {"op": "log", "message": params.get("log") or "全体玩家下回合跳过"},
            ],
        },
    ]


REWRITES = {
    # NOTE: `ocean_for_each_selectable_target` 的规则**暂时下架**：
    # 它在 2v2 下与旧原子不等价（旧原子按 `_wide_strike_target_ids` 取目标，
    # `all_enemies`/`all_selectable` 都只是近似；`wide_strike_targets` 选择器又受
    # play 快照影响、实测与旧原子不一致）。在拿到"28/28 组合等价"的证明之前，
    # 相关 9 张卡保持调用旧 op（Hel lava/magma、Arctic 4 张、jurassic:elixir、
    # ocean ink/hot_water）。见 `.codex-tmp/round2/rd2_verify_r1.md`。
    "ocean_magic_coral_tick": _magic_coral_tick_steps,
    "ocean_spikeball_damage": _spikeball_steps,
}
