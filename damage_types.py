"""Shared damage type definitions for GTN combat engines.

Damage type is intentionally separate from resource cost. A card that costs M can
still deal physical damage. Poison and burn tick damage are magic damage.
"""

DAMAGE_TYPE_PHYSICAL = "physical"
DAMAGE_TYPE_MAGIC = "magic"

DAMAGE_TAG_PHYSICAL = "gtn:physical"
DAMAGE_TAG_MAGIC = "gtn:magic"
DAMAGE_TAG_DIRECT = "gtn:direct"
DAMAGE_TAG_POISON = "gtn:poison"
DAMAGE_TAG_FIRE = "gtn:fire"
DAMAGE_TAG_BATTERY = "gtn:battery"

_MAGIC_SOURCE_TEXT = {
    "poison",
    "fire",
    "burn",
    "battery",
    "\u4e2d\u6bd2",
    "\u707c\u70e7",
    "\u7535\u6c60",
    "\u96fb\u6c60",
    "\u7535\u6c60\u7535\u51fb",
    "\u96fb\u6c60\u96fb\u64ca",
    DAMAGE_TAG_POISON,
    DAMAGE_TAG_FIRE,
    DAMAGE_TAG_BATTERY,
}

_FIRE_SOURCE_TEXT = {"fire", "burn", "\u707c\u70e7", DAMAGE_TAG_FIRE}
_POISON_SOURCE_TEXT = {"poison", "\u4e2d\u6bd2", DAMAGE_TAG_POISON}
_BATTERY_SOURCE_TEXT = {
    "battery",
    "\u7535\u6c60",
    "\u96fb\u6c60",
    "\u7535\u6c60\u7535\u51fb",
    "\u96fb\u6c60\u96fb\u64ca",
    DAMAGE_TAG_BATTERY,
}


def normalize_damage_type(value: str | None) -> str:
    text = str(value or "").strip().lower()
    if text in {DAMAGE_TYPE_MAGIC, "magical", "spell"}:
        return DAMAGE_TYPE_MAGIC
    return DAMAGE_TYPE_PHYSICAL


def infer_damage_type(source: str = "", damage_kind: str = "", damage_tag: str = "", damage_type: str | None = None) -> str:
    if damage_type:
        return normalize_damage_type(damage_type)
    values = {str(source or "").strip(), str(damage_kind or "").strip(), str(damage_tag or "").strip()}
    lowered = {v.lower() for v in values}
    if lowered.intersection(_MAGIC_SOURCE_TEXT) or values.intersection(_MAGIC_SOURCE_TEXT):
        return DAMAGE_TYPE_MAGIC
    return DAMAGE_TYPE_PHYSICAL


def is_magic_damage(*, source: str = "", damage_kind: str = "", damage_tag: str = "", damage_type: str | None = None) -> bool:
    return infer_damage_type(source, damage_kind, damage_tag, damage_type) == DAMAGE_TYPE_MAGIC


def status_damage_tag(source: str = "", damage_tag: str = "") -> str:
    values = {str(source or "").strip(), str(damage_tag or "").strip()}
    lowered = {v.lower() for v in values}
    if lowered.intersection(_FIRE_SOURCE_TEXT) or values.intersection(_FIRE_SOURCE_TEXT):
        return DAMAGE_TAG_FIRE
    if lowered.intersection(_POISON_SOURCE_TEXT) or values.intersection(_POISON_SOURCE_TEXT):
        return DAMAGE_TAG_POISON
    if lowered.intersection(_BATTERY_SOURCE_TEXT) or values.intersection(_BATTERY_SOURCE_TEXT):
        return DAMAGE_TAG_BATTERY
    return DAMAGE_TAG_MAGIC


def damage_type_tag(damage_type: str) -> str:
    return DAMAGE_TAG_MAGIC if normalize_damage_type(damage_type) == DAMAGE_TYPE_MAGIC else DAMAGE_TAG_PHYSICAL
