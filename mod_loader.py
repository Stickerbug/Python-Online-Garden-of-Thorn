import json
import os
import sys
import base64
import copy
import hashlib
import mimetypes
import posixpath
import zipfile
from typing import Dict, List, Optional, Any
from mod_validator_v2 import validate_mod_v2
from cards import normalize_card_flag, normalize_card_flags

def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

MODS_DIR = os.path.join(_get_base_dir(), 'mods')
GAME_VERSION = 'v0.5.17'
_MODS_CACHE_SIGNATURE = None
_MODS_CACHE: List['Mod'] = []

# Canonical display order for bundled mods. New bundled mods should be
# appended here so every list keeps the same stable order.
OFFICIAL_MOD_DISPLAY_ORDER = (
    'Vanilla Cards.gtnmod',
    'Garden Cards Addition.gtnmod',
    'Factory Cards Addition.gtnmod',
    'Desert Cards Addition.gtnmod',
    'Jungle Cards Addition.gtnmod',
    'Ocean Cards Addition.gtnmod',
    'Void Card Addition.gtnmod',
    'Hel Cards Addition.gtnmod',
    'Sewers Cards Addition.gtnmod',
)
_OFFICIAL_MOD_DISPLAY_RANK = {
    filename.casefold(): index for index, filename in enumerate(OFFICIAL_MOD_DISPLAY_ORDER)
}


def mod_display_order_key(value):
    filename = str(getattr(value, 'filename', value) or '').strip()
    normalized = filename.casefold()
    rank = _OFFICIAL_MOD_DISPLAY_RANK.get(normalized)
    if rank is not None:
        return (0, rank, '')
    return (1, len(OFFICIAL_MOD_DISPLAY_ORDER), normalized)


def sort_mods_for_display(mods):
    return sorted(list(mods or []), key=mod_display_order_key)

GTNMOD_MAIN_FILES = ('mod.json', 'gtnmod.json')
GTNMOD_ASSET_DIRS = ('assets/cards', 'assets/card-art', 'card-art', 'cards')
GTNMOD_ASSET_EXTS = ('.svg', '.webp', '.png', '.jpg', '.jpeg')
STATIC_MOD_ASSET_DIR = os.path.join(_get_base_dir(), 'static', 'assets', 'mod-card-art')
STATIC_MOD_ASSET_URL = '/static/assets/mod-card-art'
_MOD_ASSET_REGISTRY: Dict[str, dict] = {}


def _is_url_or_public_path(value: str) -> bool:
    text = str(value or '').strip()
    if _is_stale_mod_asset_url(text):
        return False
    return text.startswith(('http://', 'https://', 'data:image/', '/static/', '/api/'))


def _is_stale_mod_asset_url(value: str) -> bool:
    return str(value or '').strip().startswith('/api/mod-assets/')


def _safe_zip_member(name: str) -> str:
    normalized = posixpath.normpath(str(name or '').replace('\\', '/')).lstrip('/')
    if not normalized or normalized == '.' or normalized.startswith('../') or '/..' in normalized:
        return ''
    return normalized


def _gtnmod_package_key(filepath: str) -> str:
    try:
        digest = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                digest.update(chunk)
        return digest.hexdigest()[:16]
    except OSError:
        return hashlib.sha256(os.path.abspath(filepath).encode('utf-8')).hexdigest()[:16]


def _register_gtnmod_asset(filepath: str, member: str, package_key: str) -> str:
    safe_member = _safe_zip_member(member)
    if not safe_member:
        return ''
    asset_id = hashlib.sha256(f'{package_key}|{safe_member}'.encode('utf-8')).hexdigest()[:32]
    mime, _ = mimetypes.guess_type(safe_member)
    if not mime:
        mime = 'image/svg+xml' if safe_member.lower().endswith('.svg') else 'application/octet-stream'
    _MOD_ASSET_REGISTRY[asset_id] = {
        'zip_path': filepath,
        'member': safe_member,
        'mime': mime,
        'filename': os.path.basename(safe_member),
    }
    static_url = _extract_gtnmod_asset_to_static(filepath, safe_member, asset_id)
    if static_url:
        return static_url
    data_url = _gtnmod_asset_data_url(filepath, safe_member, mime)
    if data_url:
        return data_url
    return f'/api/mod-assets/{asset_id}'


def _extract_gtnmod_asset_to_static(filepath: str, member: str, asset_id: str) -> str:
    ext = os.path.splitext(member)[1].lower()
    if ext not in GTNMOD_ASSET_EXTS:
        return ''
    filename = f'{asset_id}{ext}'
    target = os.path.join(STATIC_MOD_ASSET_DIR, filename)
    try:
        os.makedirs(STATIC_MOD_ASSET_DIR, exist_ok=True)
        if not os.path.exists(target) or os.path.getsize(target) <= 0:
            with zipfile.ZipFile(filepath, 'r') as zf:
                data = zf.read(member)
            with open(target, 'wb') as f:
                f.write(data)
        return f'{STATIC_MOD_ASSET_URL}/{filename}'
    except Exception:
        return ''


def _gtnmod_asset_data_url(filepath: str, member: str, mime: str = '') -> str:
    ext = os.path.splitext(member)[1].lower()
    if ext not in GTNMOD_ASSET_EXTS:
        return ''
    try:
        with zipfile.ZipFile(filepath, 'r') as zf:
            data = zf.read(member)
        if not mime:
            mime, _ = mimetypes.guess_type(member)
        if not mime:
            mime = 'image/svg+xml' if ext == '.svg' else 'application/octet-stream'
        encoded = base64.b64encode(data).decode('ascii')
        return f'data:{mime};base64,{encoded}'
    except Exception:
        return ''


def get_mod_asset(asset_id: str) -> Optional[dict]:
    requested = str(asset_id or '').strip()
    entry = _MOD_ASSET_REGISTRY.get(requested)
    if not entry:
        entry = _find_gtnmod_asset_entry(requested)
    if not entry:
        return None
    try:
        with zipfile.ZipFile(entry['zip_path'], 'r') as zf:
            data = zf.read(entry['member'])
    except Exception:
        entry = _find_gtnmod_asset_entry(requested)
        if not entry:
            return None
        try:
            with zipfile.ZipFile(entry['zip_path'], 'r') as zf:
                data = zf.read(entry['member'])
        except Exception:
            return None
    return {
        'data': data,
        'mime': entry.get('mime') or 'application/octet-stream',
        'filename': entry.get('filename') or 'asset',
    }


def _find_gtnmod_asset_entry(asset_id: str) -> Optional[dict]:
    requested = str(asset_id or '').strip()
    if not requested or not os.path.isdir(MODS_DIR):
        return None
    for entry in os.scandir(MODS_DIR):
        if not entry.name.lower().endswith('.gtnmod') or not entry.is_file():
            continue
        filepath = entry.path
        package_key = _gtnmod_package_key(filepath)
        try:
            with zipfile.ZipFile(filepath, 'r') as zf:
                for raw_member in zf.namelist():
                    safe_member = _safe_zip_member(raw_member)
                    lowered = safe_member.lower()
                    if not safe_member or not lowered.endswith(GTNMOD_ASSET_EXTS):
                        continue
                    if not any(lowered.startswith(f'{folder}/') for folder in GTNMOD_ASSET_DIRS):
                        continue
                    candidate_id = hashlib.sha256(f'{package_key}|{safe_member}'.encode('utf-8')).hexdigest()[:32]
                    if candidate_id != requested:
                        continue
                    _register_gtnmod_asset(filepath, safe_member, package_key)
                    return _MOD_ASSET_REGISTRY.get(candidate_id)
        except Exception:
            continue
    return None


def _find_gtnmod_main_file(zf: zipfile.ZipFile) -> str:
    members = {_safe_zip_member(name).lower(): _safe_zip_member(name) for name in zf.namelist()}
    for name in GTNMOD_MAIN_FILES:
        if name in members:
            return members[name]
    for lowered, original in members.items():
        if lowered.endswith('.json') and '/' not in lowered:
            return original
    return ''


def _candidate_asset_names(card: dict) -> List[str]:
    raw_ids = []
    for key in ('legacy_id', 'runtime_id', 'id', 'name_en'):
        value = str(card.get(key) or '').strip()
        if not value:
            continue
        raw_ids.append(value.split(':', 1)[-1])
    candidates = []
    seen = set()
    for raw_id in raw_ids:
        forms = {
            raw_id,
            raw_id.replace(' ', ''),
            raw_id.replace('_', ''),
            raw_id.replace('-', ''),
            raw_id.lower(),
            raw_id.lower().replace(' ', ''),
            raw_id.lower().replace('_', ''),
            raw_id.lower().replace('-', ''),
        }
        for form in forms:
            if not form:
                continue
            for folder in GTNMOD_ASSET_DIRS:
                for ext in GTNMOD_ASSET_EXTS:
                    path = f'{folder}/{form}{ext}'
                    key = path.lower()
                    if key not in seen:
                        seen.add(key)
                        candidates.append(path)
    return candidates


def _resolve_gtnmod_asset(filepath: str, member_lookup: Dict[str, str], package_key: str, value: str) -> str:
    explicit = str(value or '').strip()
    if explicit and _is_url_or_public_path(explicit):
        return explicit
    if not explicit or _is_stale_mod_asset_url(explicit):
        return ''
    safe = _safe_zip_member(explicit)
    if not safe:
        return ''
    member = member_lookup.get(safe.lower())
    if not member:
        return ''
    return _register_gtnmod_asset(filepath, member, package_key)


def _attach_gtnmod_asset_urls(data: dict, filepath: str, zf: zipfile.ZipFile) -> dict:
    out = copy.deepcopy(data)
    package_key = _gtnmod_package_key(filepath)
    member_lookup = {_safe_zip_member(name).lower(): _safe_zip_member(name) for name in zf.namelist()}

    def attach(card: dict):
        if not isinstance(card, dict):
            return
        explicit = str(card.get('image_url') or card.get('image') or '').strip()
        assets = card.get('assets') if isinstance(card.get('assets'), dict) else {}
        if not explicit:
            explicit = str(assets.get('image') or assets.get('card_image') or '').strip()
        upgraded_explicit = str(
            card.get('upgraded_image_url')
            or card.get('upgraded_image')
            or assets.get('upgraded_image')
            or assets.get('upgraded_card_image')
            or ''
        ).strip()
        upgraded_url = _resolve_gtnmod_asset(filepath, member_lookup, package_key, upgraded_explicit)
        if upgraded_url:
            card['upgraded_image_url'] = upgraded_url
            card.setdefault('upgraded_image', upgraded_url)
        if explicit and _is_url_or_public_path(explicit):
            card.setdefault('image_url', explicit)
            return
        candidates = [] if _is_stale_mod_asset_url(explicit) else ([explicit] if explicit else [])
        candidates.extend(_candidate_asset_names(card))
        for candidate in candidates:
            safe = _safe_zip_member(candidate)
            if not safe:
                continue
            member = member_lookup.get(safe.lower())
            if member:
                card['image_url'] = _register_gtnmod_asset(filepath, member, package_key)
                card.setdefault('image', card['image_url'])
                return

    registries = out.get('registries') if isinstance(out.get('registries'), dict) else {}
    for card in registries.get('cards', []) if isinstance(registries.get('cards', []), list) else []:
        attach(card)
    for card in out.get('cards', []) if isinstance(out.get('cards', []), list) else []:
        attach(card)
    return out


class ModCard:
    def __init__(self, data: dict):
        self.id = data.get('id', '')
        self.name_cn = data.get('name_cn', '')
        self.name_en = data.get('name_en', '')
        self.cost_e = data.get('cost_e', 0)
        self.cost_m = data.get('cost_m', 0)
        self.card_type = data.get('card_type', 'thorn')
        try:
            self.count = max(0, int(data.get('count', data.get('weight', 3))))
        except (TypeError, ValueError):
            self.count = 3
        self.quality = data.get('quality', 'Common')
        self.description = data.get('description', '')
        self.effect_text = data.get('effect_text', '')
        self.flags = normalize_card_flags(data.get('flags', []))
        self.effects = data.get('effects', [])
        self.scripts = data.get('scripts', {}) if isinstance(data.get('scripts', {}), dict) else {}
        self.trigger_cost_e = data.get('trigger_cost_e', -1)
        self.trigger_cost_m = data.get('trigger_cost_m', 0)
        self.trigger_effect_text = data.get('trigger_effect_text', '')
        self.trigger_effects = data.get('trigger_effects', [])
        self.damage = data.get('damage', 0)
        self.hits = data.get('hits', 1)
        self.heal = data.get('heal', 0)
        self.draw = data.get('draw', 0)
        self.gain_e = data.get('gain_e', 0)
        self.gain_m = data.get('gain_m', 0)
        self.armor = data.get('armor', 0)
        self.dodge = data.get('dodge', 0)
        self.poison = data.get('poison', 0)
        self.burn = data.get('burn', 0)
        self.response_trigger = data.get('response_trigger', '')
        self.response_title = data.get('response_title', '')
        self.response_content = data.get('response_content', '')
        self.v2_events = data.get('v2_events', {}) if isinstance(data.get('v2_events', {}), dict) else {}
        self.v2_resource = data.get('v2_resource', {}) if isinstance(data.get('v2_resource', {}), dict) else {}
        self.v2_mod_id = data.get('v2_mod_id', '')
        self.image = data.get('image', '')
        self.image_url = data.get('image_url', self.image)
        self.upgraded_image = data.get('upgraded_image', '')
        self.upgraded_image_url = data.get('upgraded_image_url', self.upgraded_image)
        self.copy_count = max(0, int(data.get('copy_count', 0)))
        self.swift_value = max(0, int(data.get('swift_value', 0)))
        self.magic_swift_value = max(0, int(data.get('magic_swift_value', 0)))
        self.fission_level = max(1, int(data.get('fission_level', data.get('fission_count', 0) + 1) or 1))
        self.fusion_level = max(1, int(data.get('fusion_level', data.get('fusion_multiplier', 1)) or 1))
        self.ui_effect_size = str(data.get('ui_effect_size', '') or '').strip()

    def to_dict(self) -> dict:
        return {
            'id': self.id, 'name_cn': self.name_cn, 'name_en': self.name_en,
            'cost_e': self.cost_e, 'cost_m': self.cost_m,
            'card_type': self.card_type, 'count': self.count,
            'quality': self.quality, 'description': self.description,
            'effect_text': self.effect_text, 'flags': list(self.flags),
            'effects': self.effects, 'damage': self.damage, 'hits': self.hits,
            'scripts': self.scripts,
            'heal': self.heal, 'draw': self.draw, 'gain_e': self.gain_e,
            'gain_m': self.gain_m, 'armor': self.armor, 'dodge': self.dodge,
            'poison': self.poison, 'burn': self.burn,
            'trigger_cost_e': self.trigger_cost_e,
            'trigger_cost_m': self.trigger_cost_m,
            'trigger_effect_text': self.trigger_effect_text,
            'trigger_effects': self.trigger_effects,
            'response_trigger': self.response_trigger,
            'response_title': self.response_title,
            'response_content': self.response_content,
            'v2_events': self.v2_events,
            'v2_resource': self.v2_resource,
            'v2_mod_id': self.v2_mod_id,
            'image': self.image,
            'image_url': self.image_url,
            'upgraded_image': self.upgraded_image,
            'upgraded_image_url': self.upgraded_image_url,
            'copy_count': self.copy_count,
            'swift_value': self.swift_value,
            'magic_swift_value': self.magic_swift_value,
            'fission_level': self.fission_level,
            'fusion_level': self.fusion_level,
            'ui_effect_size': self.ui_effect_size,
        }

    def to_card_def(self):
        from cards import CardDef
        return CardDef(
            id=self.id,
            name_en=self.name_en,
            name_cn=self.name_cn,
            cost_e=self.cost_e,
            cost_m=self.cost_m,
            card_type=self.card_type,
            count=self.count,
            quality=self.quality,
            description=self.description,
            effect_text=self.effect_text,
            flags=self.flags,
            trigger_cost_e=self.trigger_cost_e,
            trigger_effect_text=self.trigger_effect_text,
            response_trigger=self.response_trigger,
            effects=self.effects,
            scripts=self.scripts,
            response_title=self.response_title,
            response_content=self.response_content,
            v2_events=self.v2_events,
            v2_resource=self.v2_resource,
            v2_mod_id=self.v2_mod_id,
            image=self.image,
            image_url=self.image_url,
            upgraded_image=self.upgraded_image,
            upgraded_image_url=self.upgraded_image_url,
            copy_count=self.copy_count,
            swift_value=self.swift_value,
            magic_swift_value=self.magic_swift_value,
            fission_level=self.fission_level,
            fusion_level=self.fusion_level,
            damage=self.damage,
            hits=self.hits,
            trigger_cost_m=self.trigger_cost_m,
            ui_effect_size=self.ui_effect_size,
        )


class ModEvent:
    def __init__(self, data: dict):
        self.id = data.get('id', 0)
        self.name_cn = data.get('name_cn', '')
        self.name_en = data.get('name_en', '')
        self.desc = data.get('desc', '')
        self.position = data.get('position', 3)
        self.effects = data.get('effects', [])
        self.params = data.get('params', {})

    def to_dict(self) -> dict:
        return {
            'id': self.id, 'name_cn': self.name_cn, 'name_en': self.name_en,
            'desc': self.desc, 'position': self.position,
            'effects': self.effects, 'params': self.params,
        }


class ModVariable:
    def __init__(self, data: dict):
        self.id = data.get('id', '')
        self.name = data.get('name', self.id)
        self.scope = data.get('scope', 'player')
        self.initial = data.get('initial', 0)
        self.desc = data.get('desc', '')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'scope': self.scope,
            'initial': self.initial,
            'desc': self.desc,
        }


class ModInfo:
    def __init__(self, data: dict):
        self.name = data.get('name', '')
        self.name_cn = data.get('name_cn', '')
        self.name_en = data.get('name_en', '') or data.get('name', '')
        self.version = data.get('version', '1.0.0')
        self.author = data.get('author', '')
        self.description = data.get('description', '')
        self.description_cn = data.get('description_cn', '') or data.get('description', '')
        self.description_en = data.get('description_en', '') or data.get('description', '')
        self.game_version = data.get('game_version', '')

    def to_dict(self) -> dict:
        return {
            'name': self.name, 'name_cn': self.name_cn, 'name_en': self.name_en,
            'version': self.version,
            'author': self.author, 'description': self.description,
            'description_cn': self.description_cn, 'description_en': self.description_en,
            'game_version': self.game_version,
        }


class Mod:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.format_version = 1
        self.editor: Dict[str, Any] = {}
        self.info: Optional[ModInfo] = None
        self.cards: List[ModCard] = []
        self.events: List[ModEvent] = []
        self.variables: List[ModVariable] = []
        self.custom_statuses: List[dict] = []
        self.custom_tags: List[dict] = []
        self.scripts: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.validation_hash = ''
        self.enabled = True

    def to_dict(self, include_validation: bool = False) -> dict:
        data = {
            'format_version': self.format_version,
            'editor': self.editor,
            'info': self.info.to_dict() if self.info else {},
            'cards': [c.to_dict() for c in self.cards],
            'events': [e.to_dict() for e in self.events],
            'variables': [v.to_dict() for v in self.variables],
            'custom_statuses': self.custom_statuses,
            'custom_tags': self.custom_tags,
            'scripts': self.scripts,
        }
        if include_validation:
            data['errors'] = list(self.errors)
            data['warnings'] = list(self.warnings)
            data['validation_hash'] = self.validation_hash
        return data


class V2Manifest:
    def __init__(self, data: dict):
        self.data = dict(data or {})
        self.id = self.data.get('id', '')
        self.name = self.data.get('name', '')
        self.version = self.data.get('version', '')
        self.api_version = self.data.get('api_version', '')
        self.author = self.data.get('author', '')
        self.description = self.data.get('description', '')

    def to_dict(self) -> dict:
        return dict(self.data)


class V2Resource:
    def __init__(self, registry: str, data: dict):
        self.registry = registry
        self.data = dict(data or {})
        self.id = self.data.get('id', '')

    def to_dict(self) -> dict:
        return dict(self.data)


class V2Mod(Mod):
    def __init__(self, filepath: str):
        super().__init__(filepath)
        self.format_version = 2
        self.manifest: Optional[V2Manifest] = None
        self.registries: Dict[str, List[V2Resource]] = {}
        self.patches: List[dict] = []
        self.compatibility: List[dict] = []
        self.event_hooks: List[dict] = []
        self.content_hash = ''

    def resource_counts(self) -> dict:
        return {key: len(value) for key, value in self.registries.items()}

    def to_dict(self, include_validation: bool = False) -> dict:
        data = {
            'format_version': 2,
            'manifest': self.manifest.to_dict() if self.manifest else {},
            'registries': {
                key: [resource.to_dict() for resource in resources]
                for key, resources in self.registries.items()
            },
            'patches': self.patches,
            'compatibility': self.compatibility,
            'event_hooks': self.event_hooks,
            'content_hash': self.content_hash,
            'resource_counts': self.resource_counts(),
            'editor': self.editor,
            'info': self.info.to_dict() if self.info else {},
            'cards': [c.to_dict() for c in self.cards],
            'events': [e.to_dict() for e in self.events],
            'variables': [],
            'custom_statuses': self.custom_statuses,
            'custom_tags': self.custom_tags,
            'scripts': {},
        }
        if include_validation:
            data['errors'] = list(self.errors)
            data['warnings'] = list(self.warnings)
            data['validation_hash'] = self.validation_hash
        return data


def validate_mod(data: dict) -> List[str]:
    if not isinstance(data, dict) or data.get('format_version') != 2:
        return ['只接受 GTN Mod Spec v2（format_version 必须为 2）']
    return validate_mod_v2(data).errors


def _v2_event_steps(event_def: Any) -> List[dict]:
    if isinstance(event_def, dict):
        steps = event_def.get('steps', [])
    else:
        steps = event_def
    return copy.deepcopy(steps) if isinstance(steps, list) else []


def _v2_card_to_legacy_data(resource: dict) -> dict:
    card = copy.deepcopy(resource or {})
    runtime_id = str(card.get('legacy_id') or card.get('runtime_id') or card.get('id') or '').strip()
    card['id'] = runtime_id
    cost = card.get('cost') if isinstance(card.get('cost'), dict) else {}
    if 'cost_e' not in card:
        card['cost_e'] = cost.get('e', 0)
    if 'cost_m' not in card:
        card['cost_m'] = cost.get('m', 0)
    flags = normalize_card_flags(card.get('flags', []) if isinstance(card.get('flags', []), list) else [])
    for tag in card.get('tags', []) if isinstance(card.get('tags', []), list) else []:
        tag_text = str(tag)
        if tag_text.startswith('gtn:'):
            tag_text = tag_text.split(':', 1)[1]
        flags.add(normalize_card_flag(tag_text))
    card['flags'] = list(flags)
    events = card.get('events') if isinstance(card.get('events'), dict) else {}
    card['v2_events'] = copy.deepcopy(events)
    card['v2_resource'] = copy.deepcopy(resource or {})
    card['v2_mod_id'] = str(card.get('_mod_id') or '')
    card['effects'] = []
    card['trigger_effects'] = []
    card['scripts'] = {}
    return card


def load_mod_from_data(data: dict, source: str = "memory", allow_scripts: bool = True) -> Mod:
    mod = Mod(source or 'memory')
    if not isinstance(data, dict):
        mod.errors.append('模组根节点必须是对象')
        return mod
    if data.get('format_version') == 2:
        return load_v2_mod_from_data(
            data,
            source=source,
            allow_reserved_namespaces=allow_scripts,
        )
    mod.format_version = data.get('format_version', None)
    mod.errors.append('只接受 GTN Mod Spec v2（format_version 必须为 2）')
    return mod


def load_v2_mod_from_data(data: dict, source: str = "memory", allow_reserved_namespaces: bool = False) -> V2Mod:
    mod = V2Mod(source or 'memory')
    if not isinstance(data, dict):
        mod.errors.append('模组根节点必须是对象')
        return mod
    validation = validate_mod_v2(
        data,
        source=mod.filename,
        allow_reserved_namespaces=allow_reserved_namespaces,
    )
    mod.errors = validation.errors
    mod.warnings = validation.warnings
    mod.validation_hash = validation.content_hash
    mod.content_hash = validation.content_hash
    normalized = validation.normalized if validation.normalized else copy.deepcopy(data)
    mod.editor = normalized.get('editor', {}) if isinstance(normalized.get('editor', {}), dict) else {}
    manifest_data = normalized.get('manifest') if isinstance(normalized.get('manifest'), dict) else {}
    mod.manifest = V2Manifest(manifest_data)
    if manifest_data:
        mod.info = ModInfo({
            'name': manifest_data.get('name', ''),
            'name_cn': manifest_data.get('name_cn', ''),
            'name_en': manifest_data.get('name_en', '') or manifest_data.get('name', ''),
            'version': manifest_data.get('version', '1.0.0'),
            'author': manifest_data.get('author', ''),
            'description': manifest_data.get('description', ''),
            'description_cn': manifest_data.get('description_cn', '') or manifest_data.get('description', ''),
            'description_en': manifest_data.get('description_en', '') or manifest_data.get('description', ''),
            'game_version': manifest_data.get('api_version', ''),
        })
    registries = normalized.get('registries') if isinstance(normalized.get('registries'), dict) else {}
    for key, resources in registries.items():
        if not isinstance(resources, list):
            continue
        mod.registries[key] = [
            V2Resource(key, resource)
            for resource in resources
            if isinstance(resource, dict)
        ]
    for resource in mod.registries.get('cards', []):
        card_data = _v2_card_to_legacy_data(resource.to_dict())
        if card_data.get('id'):
            mod.cards.append(ModCard(card_data))
    for resource in mod.registries.get('opening_events', []):
        event_data = resource.to_dict()
        effects = _v2_event_steps((event_data.get('events') or {}).get('on_apply') if isinstance(event_data.get('events'), dict) else [])
        mod.events.append(ModEvent({
            'id': event_data.get('legacy_id', event_data.get('id', '')),
            'name_cn': event_data.get('name_cn', event_data.get('name', '')),
            'name_en': event_data.get('name_en', event_data.get('name', '')),
            'desc': event_data.get('desc', event_data.get('description', '')),
            'position': event_data.get('position', 3),
            'effects': effects,
            'params': event_data.get('params', {}),
        }))
    mod.custom_statuses = [resource.to_dict() for resource in mod.registries.get('statuses', [])]
    mod.custom_tags = [resource.to_dict() for resource in mod.registries.get('tags', [])]
    mod.patches = normalized.get('patches', []) if isinstance(normalized.get('patches', []), list) else []
    mod.compatibility = normalized.get('compatibility', []) if isinstance(normalized.get('compatibility', []), list) else []
    mod.event_hooks = normalized.get('event_hooks', []) if isinstance(normalized.get('event_hooks', []), list) else []
    return mod


def load_mod(filepath: str) -> Mod:
    mod = Mod(filepath)
    try:
        if filepath.lower().endswith('.gtnmod'):
            with zipfile.ZipFile(filepath, 'r') as zf:
                main_file = _find_gtnmod_main_file(zf)
                if not main_file:
                    mod.errors.append('GTNMOD包缺少根目录 mod.json')
                    return mod
                data = json.loads(zf.read(main_file).decode('utf-8-sig'))
                data = _attach_gtnmod_asset_urls(data, filepath, zf)
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
    except json.JSONDecodeError as e:
        mod.errors.append(f'JSON解析错误: {e}')
        return mod
    except zipfile.BadZipFile as e:
        mod.errors.append(f'GTNMOD压缩包读取失败: {e}')
        return mod
    except Exception as e:
        mod.errors.append(f'读取失败: {e}')
        return mod
    return load_mod_from_data(data, source=filepath, allow_scripts=True)


def _mods_signature():
    if not os.path.isdir(MODS_DIR):
        return ()
    items = []
    for entry in os.scandir(MODS_DIR):
        if not entry.name.endswith(('.json', '.gtnmod')):
            continue
        try:
            stat = entry.stat()
            items.append((entry.name, stat.st_mtime_ns, stat.st_size))
        except OSError:
            items.append((entry.name, 0, 0))
    return tuple(sorted(items))


def invalidate_mod_cache():
    global _MODS_CACHE_SIGNATURE, _MODS_CACHE
    _MODS_CACHE_SIGNATURE = None
    _MODS_CACHE = []


def load_all_mods(force: bool = False) -> List[Mod]:
    global _MODS_CACHE_SIGNATURE, _MODS_CACHE
    signature = _mods_signature()
    if not force and _MODS_CACHE_SIGNATURE == signature:
        return copy.deepcopy(_MODS_CACHE)
    mods = []
    if not os.path.isdir(MODS_DIR):
        return mods
    for fname in os.listdir(MODS_DIR):
        if fname.endswith(('.json', '.gtnmod')):
            mod = load_mod(os.path.join(MODS_DIR, fname))
            mods.append(mod)
    mods = sort_mods_for_display(mods)
    _MODS_CACHE_SIGNATURE = signature
    _MODS_CACHE = copy.deepcopy(mods)
    return mods


def save_mod(mod: Mod):
    os.makedirs(MODS_DIR, exist_ok=True)
    data = mod.to_dict()
    with open(mod.filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    invalidate_mod_cache()


def delete_mod(filepath: str):
    if os.path.exists(filepath):
        os.remove(filepath)
    invalidate_mod_cache()


def check_conflicts(mods: List[Mod]) -> List[str]:
    conflicts = []
    card_ids = {}
    event_ids = {}
    for mod in mods:
        if not mod.enabled or mod.errors:
            continue
        for card in mod.cards:
            if card.id in card_ids:
                conflicts.append(f'卡牌ID冲突: {card.id} (来自 {card_ids[card.id]} 和 {mod.info.name if mod.info else mod.filename})')
            else:
                card_ids[card.id] = mod.info.name if mod.info else mod.filename
        for event in mod.events:
            key = f"event_{event.id}"
            if key in event_ids:
                conflicts.append(f'事件ID冲突: {event.id} (来自 {event_ids[key]} 和 {mod.info.name if mod.info else mod.filename})')
            else:
                event_ids[key] = mod.info.name if mod.info else mod.filename
    return conflicts


def get_enabled_mods() -> List[Mod]:
    mods = load_all_mods()
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\GardenOfThorn', 0, winreg.KEY_READ)
        disabled_list, _ = winreg.QueryValueEx(key, 'DisabledMods')
        winreg.CloseKey(key)
        disabled = set(disabled_list.split(',')) if disabled_list else set()
    except Exception:
        disabled = set()
    for mod in mods:
        if mod.filename in disabled:
            mod.enabled = False
    return mods


def compute_mods_hash() -> str:
    enabled = get_enabled_mods()
    hasher = hashlib.sha256()
    for mod in sorted(enabled, key=lambda m: m.filename):
        if not mod.enabled or mod.errors:
            continue
        try:
            with open(mod.filepath, 'rb') as f:
                hasher.update(f.read())
        except Exception:
            hasher.update(mod.filename.encode('utf-8'))
    return hasher.hexdigest()


def get_mods_summary() -> dict:
    enabled = get_enabled_mods()
    active = [m for m in enabled if m.enabled and not m.errors]
    return {
        'hash': compute_mods_hash(),
        'mods': [m.info.name if m.info else m.filename for m in active],
        'count': len(active),
    }


def get_active_mod_variables() -> List[dict]:
    variables = []
    for mod in get_enabled_mods():
        if not mod.enabled or mod.errors:
            continue
        for variable in mod.variables:
            variables.append(variable.to_dict())
    return variables


def merge_mod_cards_to_card_defs() -> List[str]:
    from cards import CARD_DEFS, ERROR_CARD_ID
    # CARD_DEFS is the global definition registry used for rendering, logs,
    # previews, images, and card lookup. It should contain every valid local
    # mod card; per-player/per-room mod selection is enforced separately by
    # allowed_card_ids when building draft/deck pools.
    mods = load_all_mods()
    active = [m for m in mods if not m.errors]
    for mod in mods:
        if mod.errors:
            print(f'[模组] 跳过模组 {mod.info.name if mod.info else mod.filename}，验证错误: {mod.errors}')
    merged = []
    for mod in active:
        for mc in mod.cards:
            if mc.id == ERROR_CARD_ID:
                continue
            card_def = mc.to_card_def()
            CARD_DEFS[mc.id] = card_def
            merged.append(mc.id)
        print(f'[模组] 已加载模组 {mod.info.name if mod.info else mod.filename}: {len(mod.cards)} 张卡牌')
    if merged:
        print(f'[模组] 共合并 {len(merged)} 张模组卡牌到 CARD_DEFS')
    else:
        print('[模组] 没有模组卡牌被合并（可能没有启用的模组，或所有模组都有验证错误）')
    return merged
