import copy
import base64
import hashlib
import io
import json
import mimetypes
import os
import posixpath
import secrets
import time
import zipfile
import copy
from collections import deque
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import quote, urlparse

try:
    import boto3
    from botocore.config import Config as BotoConfig
    from botocore.exceptions import ClientError
except Exception:  # pragma: no cover - dependency may be absent in local dev before pip install
    boto3 = None
    BotoConfig = None
    ClientError = None
try:
    import requests
except Exception:  # pragma: no cover
    requests = None

from mod_loader import load_mod_from_data
from mod_validator_v2 import validate_mod_v2
from font_subsets import community_font_report_for_data


MAX_COMMUNITY_MOD_BYTES = 150_000
MAX_COMMUNITY_PACKAGE_BYTES = int(os.environ.get('MAX_COMMUNITY_PACKAGE_BYTES', str(1024 * 1024)))
MAX_COMMUNITY_CARDS = 120
MAX_COMMUNITY_EVENTS = 30
COMMUNITY_INDEX_KEY = 'community/index.json'
COMMUNITY_TRASH_INDEX_KEY = 'community/trash/index.json'
COMMUNITY_MOD_CACHE: Dict[str, Any] = {}
COMMUNITY_INDEX_CACHE = {'ts': 0.0, 'data': None}
COMMUNITY_INDEX_CACHE_SECONDS = int(os.environ.get('R2_INDEX_CACHE_SECONDS', '30'))
R2_HEALTH = {
    'index_reads': deque(maxlen=100),
    'failures': {},
    'last_error': '',
    'last_success_at': '',
    'last_mod_count': None,
}


class R2ConfigError(RuntimeError):
    pass


def _record_r2_index_read(duration_ms: float, ok: bool, mod_count: Optional[int] = None, error: str = '') -> None:
    R2_HEALTH['index_reads'].append({
        'ts': time.time(),
        'duration_ms': round(float(duration_ms), 2),
        'ok': bool(ok),
    })
    if ok:
        R2_HEALTH['last_success_at'] = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
        R2_HEALTH['last_error'] = ''
        if mod_count is not None:
            R2_HEALTH['last_mod_count'] = int(mod_count)
    elif error:
        R2_HEALTH['last_error'] = str(error)[:300]


def record_r2_failure(kind: str, exc: Any = '') -> None:
    kind = str(kind or 'unknown')[:40]
    failures = R2_HEALTH.setdefault('failures', {})
    failures[kind] = int(failures.get(kind, 0)) + 1
    if exc:
        R2_HEALTH['last_error'] = str(exc)[:300]


def get_r2_health_snapshot() -> Dict[str, Any]:
    reads = list(R2_HEALTH.get('index_reads') or [])
    ok_reads = [item for item in reads if item.get('ok')]
    errors = [item for item in reads if not item.get('ok')]
    durations = [item.get('duration_ms') for item in ok_reads if item.get('duration_ms') is not None]
    avg_ms = round(sum(durations) / len(durations), 2) if durations else None
    latest = reads[-1] if reads else None
    return {
        'configured': bool(_env('R2_PUBLIC_BASE_URL') and _env('R2_BUCKET')),
        'mod_count': R2_HEALTH.get('last_mod_count'),
        'index_reads': len(reads),
        'index_errors': len(errors),
        'index_avg_ms': avg_ms,
        'index_latest_ms': latest.get('duration_ms') if latest else None,
        'index_latest_ok': latest.get('ok') if latest else None,
        'failures': dict(R2_HEALTH.get('failures') or {}),
        'upload_failures': sum(int(v) for k, v in dict(R2_HEALTH.get('failures') or {}).items() if 'upload' in k or 'register' in k),
        'last_error': R2_HEALTH.get('last_error') or '',
        'last_success_at': R2_HEALTH.get('last_success_at') or '',
    }


def _env(name: str) -> str:
    return os.environ.get(name, '').strip()


def r2_public_base_url() -> str:
    return _env('R2_PUBLIC_BASE_URL').rstrip('/')


def _required_env() -> Dict[str, str]:
    values = {
        'R2_ACCOUNT_ID': _env('R2_ACCOUNT_ID'),
        'R2_BUCKET': _env('R2_BUCKET'),
        'R2_ACCESS_KEY_ID': _env('R2_ACCESS_KEY_ID'),
        'R2_SECRET_ACCESS_KEY': _env('R2_SECRET_ACCESS_KEY'),
        'R2_PUBLIC_BASE_URL': r2_public_base_url(),
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise R2ConfigError('社区模组未配置 R2 环境变量: ' + ', '.join(missing))
    account_id = values['R2_ACCOUNT_ID']
    if len(account_id) != 32:
        raise R2ConfigError(
            f'R2_ACCOUNT_ID 格式错误：应为 Cloudflare Account ID（32 位），当前长度 {len(account_id)}'
        )
    access_key = values['R2_ACCESS_KEY_ID']
    if len(access_key) != 32:
        raise R2ConfigError(
            'R2_ACCESS_KEY_ID 格式错误：应填写 Cloudflare R2 的 S3 Access Key ID（32 位），'
            f'不是 API Token 或 Secret Access Key；当前长度 {len(access_key)}'
        )
    return values


def _client():
    global boto3, BotoConfig, ClientError
    if boto3 is None:
        try:
            import boto3 as _boto3
            from botocore.config import Config as _BotoConfig
            from botocore.exceptions import ClientError as _ClientError
            boto3 = _boto3
            BotoConfig = _BotoConfig
            ClientError = _ClientError
        except Exception as exc:
            raise R2ConfigError('社区模组依赖 boto3 未安装，请执行 python -m pip install -r requirements.txt') from exc
    values = _required_env()
    endpoint = f"https://{values['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com"
    connect_timeout = float(os.environ.get('R2_CONNECT_TIMEOUT', '3'))
    read_timeout = float(os.environ.get('R2_READ_TIMEOUT', '6'))
    max_attempts = int(os.environ.get('R2_MAX_ATTEMPTS', '2'))
    config = BotoConfig(
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
        retries={'max_attempts': max_attempts, 'mode': 'standard'},
    ) if BotoConfig is not None else None
    return boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=values['R2_ACCESS_KEY_ID'],
        aws_secret_access_key=values['R2_SECRET_ACCESS_KEY'],
        region_name='auto',
        config=config,
    )


def _bucket() -> str:
    return _required_env()['R2_BUCKET']


def _safe_filename(filename: str) -> str:
    base = os.path.basename(str(filename or '').strip()).replace('\\', '/').split('/')[-1]
    if not base:
        base = 'community_mod.json'
    keep = []
    for ch in base:
        if ch.isalnum() or ch in ('-', '_', '.', ' '):
            keep.append(ch)
    safe = ''.join(keep).strip().replace(' ', '_') or 'community_mod.json'
    if not safe.lower().endswith(('.json', '.gtnmod')):
        raise ValueError('只允许上传 .json 模组文件')
    return safe[:96]


def _content_type_for_filename(filename: str) -> str:
    return 'application/zip' if str(filename or '').lower().endswith('.gtnmod') else 'application/json'


def _safe_zip_member(name: str) -> str:
    normalized = posixpath.normpath(str(name or '').replace('\\', '/')).lstrip('/')
    if not normalized or normalized == '.' or normalized.startswith('../') or '/..' in normalized:
        return ''
    return normalized


def _find_gtnmod_main_file(zf: zipfile.ZipFile) -> str:
    members = {_safe_zip_member(name).lower(): _safe_zip_member(name) for name in zf.namelist()}
    for name in ('mod.json', 'gtnmod.json'):
        if name in members:
            return members[name]
    for lowered, original in members.items():
        if lowered.endswith('.json') and '/' not in lowered:
            return original
    return ''


def _candidate_asset_names(card: Dict[str, Any]) -> list:
    raw_ids = []
    for key in ('legacy_id', 'runtime_id', 'id', 'name_en'):
        value = str(card.get(key) or '').strip()
        if value:
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
            for folder in ('assets/cards', 'assets/card-art', 'card-art', 'cards'):
                for ext in ('.svg', '.webp', '.png', '.jpg', '.jpeg'):
                    path = f'{folder}/{form}{ext}'
                    key = path.lower()
                    if key not in seen:
                        seen.add(key)
                        candidates.append(path)
    return candidates


def _asset_data_url(zf: zipfile.ZipFile, member: str) -> str:
    raw = zf.read(member)
    mime, _ = mimetypes.guess_type(member)
    if not mime:
        mime = 'image/svg+xml' if member.lower().endswith('.svg') else 'application/octet-stream'
    return f'data:{mime};base64,{base64.b64encode(raw).decode("ascii")}'


def _is_stale_mod_asset_url(value: str) -> bool:
    text = str(value or '').strip()
    return text.startswith('/api/mod-assets/') or text.startswith('/static/assets/mod-card-art/')


def _attach_gtnmod_data_urls(data: Dict[str, Any], zf: zipfile.ZipFile) -> Dict[str, Any]:
    out = copy.deepcopy(data)
    member_lookup = {_safe_zip_member(name).lower(): _safe_zip_member(name) for name in zf.namelist()}

    def attach(card: Dict[str, Any]) -> None:
        if not isinstance(card, dict):
            return
        explicit = str(card.get('image_url') or card.get('image') or '').strip()
        assets = card.get('assets') if isinstance(card.get('assets'), dict) else {}
        if not explicit:
            explicit = str(assets.get('image') or assets.get('card_image') or '').strip()
        if _is_stale_mod_asset_url(explicit):
            explicit = ''
        if explicit.startswith(('http://', 'https://', '/static/', '/api/', 'data:')):
            card.setdefault('image_url', explicit)
            return
        candidates = [explicit] if explicit else []
        candidates.extend(_candidate_asset_names(card))
        for candidate in candidates:
            safe = _safe_zip_member(candidate)
            if not safe:
                continue
            member = member_lookup.get(safe.lower())
            if member:
                url = _asset_data_url(zf, member)
                card['image_url'] = url
                card.setdefault('image', url)
                return

    registries = out.get('registries') if isinstance(out.get('registries'), dict) else {}
    cards = registries.get('cards', []) if isinstance(registries.get('cards'), list) else []
    for card in cards:
        attach(card)
    return out


def _public_url_for_key(key: str) -> str:
    base = r2_public_base_url()
    quoted = '/'.join(quote(part) for part in key.split('/'))
    return f'{base}/{quoted}'


def create_presigned_mod_upload(filename: str) -> Dict[str, Any]:
    safe = _safe_filename(filename)
    now = int(time.time())
    token = secrets.token_hex(8)
    key = f'community/uploads/{now}-{token}-{safe}'
    expires_in = 300
    content_type = _content_type_for_filename(safe)
    put_url = _client().generate_presigned_url(
        ClientMethod='put_object',
        Params={
            'Bucket': _bucket(),
            'Key': key,
            'ContentType': content_type,
        },
        ExpiresIn=expires_in,
        HttpMethod='PUT',
    )
    return {
        'key': key,
        'put_url': put_url,
        'public_url': _public_url_for_key(key),
        'expires_in': expires_in,
        'content_type': content_type,
    }


def fetch_json_from_public_url(url: str, max_bytes: int = MAX_COMMUNITY_MOD_BYTES) -> Dict[str, Any]:
    global requests
    if requests is None:
        try:
            import requests as _requests
            requests = _requests
        except Exception as exc:
            raise R2ConfigError('社区模组依赖 requests 未安装，请执行 python -m pip install -r requirements.txt') from exc
    url = str(url or '').strip()
    if not url:
        raise ValueError('缺少 public_url')
    base = r2_public_base_url()
    if not base:
        raise R2ConfigError('社区模组未配置 R2_PUBLIC_BASE_URL')
    if url.lower().split('?', 1)[0].endswith('.gtnmod') and max_bytes == MAX_COMMUNITY_MOD_BYTES:
        max_bytes = MAX_COMMUNITY_PACKAGE_BYTES
    if not url.startswith(base + '/'):
        raise ValueError('public_url 不属于当前 R2 公开域名')
    connect_timeout = float(os.environ.get('R2_PUBLIC_CONNECT_TIMEOUT', '3'))
    read_timeout = float(os.environ.get('R2_PUBLIC_READ_TIMEOUT', '8'))
    with requests.get(url, stream=True, timeout=(connect_timeout, read_timeout)) as resp:
        resp.raise_for_status()
        length = resp.headers.get('Content-Length')
        if length and int(length) > max_bytes:
            raise ValueError(f'模组文件过大，最大允许 {max_bytes} 字节')
        chunks = []
        total = 0
        for chunk in resp.iter_content(chunk_size=16384):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(f'模组文件过大，最大允许 {max_bytes} 字节')
            chunks.append(chunk)
    raw = b''.join(chunks)
    package_sha256 = hashlib.sha256(raw).hexdigest()
    is_gtnmod = url.lower().split('?', 1)[0].endswith('.gtnmod') or raw[:4] == b'PK\x03\x04'
    if is_gtnmod:
        try:
            with zipfile.ZipFile(io.BytesIO(raw), 'r') as zf:
                main_file = _find_gtnmod_main_file(zf)
                if not main_file:
                    raise ValueError('GTNMOD 包缺少根目录 mod.json')
                main_info = zf.getinfo(main_file)
                if main_info.file_size > MAX_COMMUNITY_MOD_BYTES:
                    raise ValueError(f'mod.json 过大，最大允许 {MAX_COMMUNITY_MOD_BYTES} 字节')
                for info in zf.infolist():
                    member = _safe_zip_member(info.filename)
                    if not member:
                        raise ValueError('GTNMOD 包包含不安全路径')
                    ext = os.path.splitext(member)[1].lower()
                    if ext and ext not in ('.json', '.svg', '.webp', '.png', '.jpg', '.jpeg'):
                        raise ValueError(f'GTNMOD 包包含不允许的文件类型: {ext}')
                raw_json = zf.read(main_file)
        except zipfile.BadZipFile as exc:
            raise ValueError(f'GTNMOD 压缩包读取失败: {exc}') from exc
        try:
            data = json.loads(raw_json.decode('utf-8-sig'))
        except Exception as exc:
            raise ValueError(f'GTNMOD mod.json 解析错误: {exc}') from exc
        if not isinstance(data, dict):
            raise ValueError('模组根节点必须是对象')
        with zipfile.ZipFile(io.BytesIO(raw), 'r') as zf:
            data = _attach_gtnmod_data_urls(data, zf)
        data['_package_sha256'] = package_sha256
        return data
    try:
        data = json.loads(raw.decode('utf-8-sig'))
    except Exception as exc:
        raise ValueError(f'JSON解析错误: {exc}') from exc
    if not isinstance(data, dict):
        raise ValueError('模组根节点必须是对象')
    return data


def get_community_index(force: bool = False) -> Dict[str, Any]:
    now = time.time()
    cached = COMMUNITY_INDEX_CACHE.get('data')
    if not force and cached is not None and now - float(COMMUNITY_INDEX_CACHE.get('ts') or 0) < COMMUNITY_INDEX_CACHE_SECONDS:
        return copy.deepcopy(cached)
    start = time.perf_counter()
    try:
        obj = _client().get_object(Bucket=_bucket(), Key=COMMUNITY_INDEX_KEY)
        raw = obj['Body'].read()
    except Exception as exc:
        if ClientError is not None and isinstance(exc, ClientError):
            code = exc.response.get('Error', {}).get('Code')
            if code in ('NoSuchKey', '404', 'NotFound'):
                _record_r2_index_read((time.perf_counter() - start) * 1000, True, 0)
                data = {'mods': []}
                COMMUNITY_INDEX_CACHE['ts'] = now
                COMMUNITY_INDEX_CACHE['data'] = copy.deepcopy(data)
                return data
        _record_r2_index_read((time.perf_counter() - start) * 1000, False, error=exc)
        raise
    try:
        data = json.loads(raw.decode('utf-8-sig') or '{}')
        if not isinstance(data, dict):
            data = {'mods': []}
        mods = data.get('mods')
        if not isinstance(mods, list):
            data['mods'] = []
        _record_r2_index_read((time.perf_counter() - start) * 1000, True, len(data.get('mods') or []))
        COMMUNITY_INDEX_CACHE['ts'] = now
        COMMUNITY_INDEX_CACHE['data'] = copy.deepcopy(data)
        return data
    except Exception as exc:
        _record_r2_index_read((time.perf_counter() - start) * 1000, False, error=exc)
        raise


def put_community_index(index: Dict[str, Any]) -> None:
    data = index if isinstance(index, dict) else {'mods': []}
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    _client().put_object(
        Bucket=_bucket(),
        Key=COMMUNITY_INDEX_KEY,
        Body=payload.encode('utf-8'),
        ContentType='application/json; charset=utf-8',
    )
    COMMUNITY_INDEX_CACHE['ts'] = time.time()
    COMMUNITY_INDEX_CACHE['data'] = copy.deepcopy(data)


def get_community_trash_index() -> Dict[str, Any]:
    try:
        obj = _client().get_object(Bucket=_bucket(), Key=COMMUNITY_TRASH_INDEX_KEY)
        raw = obj['Body'].read()
    except Exception as exc:
        if ClientError is not None and isinstance(exc, ClientError):
            code = exc.response.get('Error', {}).get('Code')
            if code in ('NoSuchKey', '404', 'NotFound'):
                return {'mods': []}
        raise
    data = json.loads(raw.decode('utf-8-sig') or '{}')
    if not isinstance(data, dict):
        return {'mods': []}
    if not isinstance(data.get('mods'), list):
        data['mods'] = []
    return data


def put_community_trash_index(index: Dict[str, Any]) -> None:
    payload = json.dumps(index if isinstance(index, dict) else {'mods': []}, ensure_ascii=False, indent=2)
    _client().put_object(
        Bucket=_bucket(),
        Key=COMMUNITY_TRASH_INDEX_KEY,
        Body=payload.encode('utf-8'),
        ContentType='application/json; charset=utf-8',
    )


def _is_v2_mod_data(data: Dict[str, Any]) -> bool:
    return isinstance(data, dict) and data.get('format_version') == 2


def _validate_community_mod_data(data: Dict[str, Any], source: str = ''):
    validation = validate_mod_v2(data if isinstance(data, dict) else {}, source=source, allow_reserved_namespaces=False)
    if not _is_v2_mod_data(data):
        validation.errors.append('社区模组只接受 GTN Mod Spec v2（format_version 必须为 2）')
        return validation
    registries = data.get('registries') if isinstance(data.get('registries'), dict) else {}
    cards = registries.get('cards', []) if isinstance(registries.get('cards', []), list) else []
    events = registries.get('opening_events', []) if isinstance(registries.get('opening_events', []), list) else []
    if len(cards) > MAX_COMMUNITY_CARDS:
        validation.errors.append(f'社区模组卡牌数量过多，最多 {MAX_COMMUNITY_CARDS} 张')
    if len(events) > MAX_COMMUNITY_EVENTS:
        validation.errors.append(f'社区模组开局事件数量过多，最多 {MAX_COMMUNITY_EVENTS} 个')
    return validation


def _community_validation_input(data: Dict[str, Any]) -> tuple:
    return data, []


def _community_mod_info(data: Dict[str, Any]) -> Dict[str, Any]:
    if _is_v2_mod_data(data):
        manifest = data.get('manifest') if isinstance(data.get('manifest'), dict) else {}
        registries = data.get('registries') if isinstance(data.get('registries'), dict) else {}
        return {
            'name': manifest.get('name') or 'Community Mod',
            'version': manifest.get('version') or '1.0.0',
            'author': manifest.get('author') or '',
            'description': manifest.get('description') or '',
            'cards_count': len(registries.get('cards', [])) if isinstance(registries.get('cards'), list) else 0,
            'events_count': len(registries.get('opening_events', [])) if isinstance(registries.get('opening_events'), list) else 0,
            'format_version': 2,
            'manifest': manifest,
        }
    return {
        'name': 'Invalid Community Mod',
        'version': '',
        'author': '',
        'description': '',
        'cards_count': 0,
        'events_count': 0,
        'format_version': data.get('format_version', None) if isinstance(data, dict) else None,
        'manifest': {},
    }


def _community_metadata(data: Dict[str, Any], public_url: str, key: str, sha256: str, uploader_name: Optional[str]):
    info = _community_mod_info(data)
    return {
        'sha256': sha256,
        'key': key,
        'public_url': public_url,
        'name': info.get('name') or 'Community Mod',
        'version': info.get('version') or '1.0.0',
        'author': info.get('author') or '',
        'description': info.get('description') or '',
        'uploader_name': str(uploader_name or '')[:40],
        'uploaded_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'cards_count': info.get('cards_count', 0),
        'events_count': info.get('events_count', 0),
        'format_version': info.get('format_version', 1),
        'manifest': info.get('manifest') or {},
        'scripts_disabled': True,
    }


def _community_font_report(data: Dict[str, Any], sha256: str = '', generate: bool = False) -> Dict[str, Any]:
    try:
        return community_font_report_for_data(data, hash_key=sha256, generate=generate)
    except Exception as exc:
        return {
            'success': False,
            'url': '',
            'missing_count': 0,
            'missing_chars': [],
            'unsupported_count': 0,
            'unsupported_chars': [],
            'warnings': [f'社区模组字体检查失败：{type(exc).__name__}: {exc}'],
        }


def _append_unique_warnings(warnings, extra_warnings) -> list:
    result = list(warnings or [])
    seen = set(result)
    for warning in extra_warnings or []:
        text = str(warning or '').strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def _community_item_owned_by(item: Dict[str, Any], uploader_user_id: Optional[int] = None,
                             uploader_name: Optional[str] = None) -> bool:
    if not isinstance(item, dict):
        return False
    if uploader_user_id is not None and str(item.get('uploader_user_id') or '') == str(uploader_user_id):
        return True
    item_user_id = str(item.get('uploader_user_id') or '').strip()
    if item_user_id:
        return False
    expected_name = str(uploader_name or '').strip().lower()
    item_name = str(item.get('uploader_name') or '').strip().lower()
    return bool(expected_name and item_name and expected_name == item_name)


def _delete_object_key(key: str) -> bool:
    key = str(key or '').strip()
    if not key:
        return False
    try:
        _client().delete_object(Bucket=_bucket(), Key=key)
        return True
    except Exception:
        return False


def _move_object_to_trash(key: str, sha256: str = '') -> Optional[str]:
    key = str(key or '').strip()
    if not key:
        return None
    safe_name = posixpath.basename(key) or f'{sha256 or secrets.token_hex(8)}.json'
    stamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    trash_key = f'community/trash/{stamp}-{sha256[:12] or secrets.token_hex(6)}-{safe_name}'
    try:
        _client().copy_object(
            Bucket=_bucket(),
            CopySource={'Bucket': _bucket(), 'Key': key},
            Key=trash_key,
            ContentType='application/json',
            MetadataDirective='COPY',
        )
        _client().delete_object(Bucket=_bucket(), Key=key)
        return trash_key
    except Exception:
        return None


def validate_community_mod_url(public_url: str) -> Dict[str, Any]:
    data = fetch_json_from_public_url(public_url)
    package_sha256 = str(data.pop('_package_sha256', '') or '').strip().lower() if isinstance(data, dict) else ''
    candidate, strip_warnings = _community_validation_input(data)
    validation = _validate_community_mod_data(candidate, source=public_url)
    warnings = list(validation.warnings) + strip_warnings
    normalized = validation.normalized if validation.normalized else candidate
    sha256 = hashlib.sha256(
        json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    font_report = _community_font_report(normalized, sha256=sha256, generate=False)
    warnings = _append_unique_warnings(warnings, font_report.get('warnings'))
    info = _community_mod_info(normalized)
    return {
        'ok': not validation.errors,
        'info': {
            'name': info.get('name') or 'Community Mod',
            'version': info.get('version') or '1.0.0',
            'author': info.get('author') or '',
            'description': info.get('description') or '',
        },
        'sha256': sha256,
        'errors': validation.errors,
        'warnings': warnings,
        'font_subset': font_report,
        'cards_count': info.get('cards_count', 0),
        'events_count': info.get('events_count', 0),
        'format_version': info.get('format_version', 1),
        'manifest': info.get('manifest') or {},
    }


def register_community_mod(public_url: str, key: str, uploader_name: Optional[str] = None,
                           uploader_user_id: Optional[int] = None,
                           replace_sha256: Optional[str] = None) -> Dict[str, Any]:
    data = fetch_json_from_public_url(public_url)
    package_sha256 = str(data.pop('_package_sha256', '') or '').strip().lower() if isinstance(data, dict) else ''
    candidate, strip_warnings = _community_validation_input(data)
    validation = _validate_community_mod_data(candidate, source=public_url)
    warnings = list(validation.warnings) + strip_warnings
    if validation.errors:
        return {'success': False, 'errors': validation.errors, 'warnings': warnings}
    normalized = validation.normalized if validation.normalized else candidate
    sha256 = package_sha256 or hashlib.sha256(
        json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    font_report = _community_font_report(normalized, sha256=sha256, generate=True)
    warnings = _append_unique_warnings(warnings, font_report.get('warnings'))
    index = get_community_index(force=True)
    mods = index.setdefault('mods', [])
    replace_sha256 = str(replace_sha256 or '').strip().lower()
    replace_item = None
    if replace_sha256:
        for item in mods:
            if isinstance(item, dict) and str(item.get('sha256') or '').strip().lower() == replace_sha256:
                replace_item = item
                break
        if replace_item is None:
            return {'success': False, 'errors': ['要更新的社区模组不存在'], 'warnings': warnings}
        if not _community_item_owned_by(replace_item, uploader_user_id, uploader_name):
            return {'success': False, 'errors': ['只能更新自己上传的社区模组'], 'warnings': warnings}
    for item in mods:
        if isinstance(item, dict) and item.get('sha256') == sha256:
            if replace_item is not None and item is replace_item:
                item.update(_community_metadata(normalized, public_url, key, sha256, uploader_name))
                if uploader_user_id is not None:
                    item['uploader_user_id'] = int(uploader_user_id)
                item['warnings'] = warnings
                item['font_subset'] = font_report
                put_community_index(index)
            elif replace_item is not None:
                mods.remove(replace_item)
                put_community_index(index)
                _move_object_to_trash(replace_item.get('key'), replace_sha256)
            item.setdefault('warnings', warnings)
            item.setdefault('font_subset', font_report)
            return {'success': True, 'mod': item, 'duplicate': True, 'warnings': warnings}
    if replace_item is not None:
        mods.remove(replace_item)
    meta = _community_metadata(normalized, public_url, key, sha256, uploader_name)
    if uploader_user_id is not None:
        meta['uploader_user_id'] = int(uploader_user_id)
    meta['warnings'] = warnings
    meta['font_subset'] = font_report
    mods.append(meta)
    mods.sort(key=lambda item: (str(item.get('uploaded_at', '')), str(item.get('sha256', ''))))
    put_community_index(index)
    if replace_item is not None:
        _move_object_to_trash(replace_item.get('key'), replace_sha256)
    return {'success': True, 'mod': meta, 'duplicate': False, 'warnings': warnings}


def delete_community_mod(sha256: str, uploader_user_id: Optional[int] = None,
                         uploader_name: Optional[str] = None,
                         allow_any: bool = False) -> Dict[str, Any]:
    sha256 = str(sha256 or '').strip().lower()
    if not sha256:
        return {'success': False, 'error': '缺少社区模组 hash'}
    index = get_community_index(force=True)
    mods = index.setdefault('mods', [])
    target = None
    for item in mods:
        if isinstance(item, dict) and str(item.get('sha256') or '').strip().lower() == sha256:
            target = item
            break
    if target is None:
        return {'success': False, 'error': '社区模组不存在'}
    if not allow_any and not _community_item_owned_by(target, uploader_user_id, uploader_name):
        return {'success': False, 'error': '只能删除自己上传的社区模组'}
    key = str(target.get('key') or '').strip()
    trash_key = _move_object_to_trash(key, sha256)
    if key and not trash_key:
        return {'success': False, 'error': '移动到回收站失败，未删除模组'}
    mods.remove(target)
    put_community_index(index)
    trash_indexed = False
    if trash_key:
        try:
            trash = get_community_trash_index()
            row = dict(target)
            row['deleted_at'] = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
            row['deleted_by'] = str(uploader_name or '')
            row['original_key'] = key
            row['trash_key'] = trash_key
            row['trash_public_url'] = _public_url_for_key(trash_key)
            trash.setdefault('mods', []).append(row)
            put_community_trash_index(trash)
            trash_indexed = True
        except Exception:
            trash_indexed = False
    COMMUNITY_MOD_CACHE.pop(sha256, None)
    public_url = str(target.get('public_url') or '').strip()
    if public_url:
        COMMUNITY_MOD_CACHE.pop(public_url, None)
    return {
        'success': True,
        'mod': target,
        'trash_key': trash_key,
        'moved_to_trash': bool(trash_key),
        'trash_indexed': trash_indexed,
    }


def list_repository_objects(prefix: str = 'community/', max_keys: int = 300) -> Dict[str, Any]:
    prefix = str(prefix or 'community/').strip()
    if not prefix.startswith('community/'):
        prefix = 'community/'
    max_keys = max(1, min(int(max_keys or 300), 1000))
    response = _client().list_objects_v2(Bucket=_bucket(), Prefix=prefix, MaxKeys=max_keys)
    objects = []
    for item in response.get('Contents', []) or []:
        key = str(item.get('Key') or '')
        objects.append({
            'key': key,
            'size': int(item.get('Size') or 0),
            'last_modified': item.get('LastModified').isoformat() if item.get('LastModified') else '',
            'public_url': _public_url_for_key(key),
            'is_index': key in (COMMUNITY_INDEX_KEY, COMMUNITY_TRASH_INDEX_KEY),
            'is_trash': key.startswith('community/trash/'),
        })
    trash = {'mods': []}
    try:
        trash = get_community_trash_index()
    except Exception:
        trash = {'mods': []}
    return {
        'objects': objects,
        'is_truncated': bool(response.get('IsTruncated')),
        'trash': trash.get('mods', []) if isinstance(trash, dict) and isinstance(trash.get('mods'), list) else [],
    }


def permanently_delete_repository_object(key: str) -> Dict[str, Any]:
    key = str(key or '').strip()
    if not key.startswith('community/'):
        return {'success': False, 'error': '只能删除 community/ 下的对象'}
    if key in (COMMUNITY_INDEX_KEY, COMMUNITY_TRASH_INDEX_KEY):
        return {'success': False, 'error': '不能删除社区模组索引'}
    deleted = _delete_object_key(key)
    if not deleted:
        return {'success': False, 'error': '删除失败'}
    if key.startswith('community/trash/'):
        try:
            trash = get_community_trash_index()
            mods = trash.setdefault('mods', [])
            trash['mods'] = [
                item for item in mods
                if not isinstance(item, dict) or str(item.get('trash_key') or '') != key
            ]
            put_community_trash_index(trash)
        except Exception:
            pass
    return {'success': True, 'key': key}


def _find_community_index_entry(sha256: str = '', public_url: str = '') -> Optional[Dict[str, Any]]:
    try:
        index = get_community_index()
    except Exception:
        return None
    mods = index.get('mods', []) if isinstance(index, dict) else []
    if not isinstance(mods, list):
        return None
    sha256 = str(sha256 or '').strip().lower()
    public_url = str(public_url or '').strip()
    for item in mods:
        if not isinstance(item, dict):
            continue
        if sha256 and str(item.get('sha256', '')).strip().lower() == sha256:
            return item
        if public_url and str(item.get('public_url', '')).strip() == public_url:
            return item
    return None


def load_community_mod(public_url: str, expected_hash: Optional[str] = None):
    expected_hash = str(expected_hash or '').strip()
    cache_key = expected_hash or public_url
    if cache_key in COMMUNITY_MOD_CACHE:
        return COMMUNITY_MOD_CACHE[cache_key]
    data = fetch_json_from_public_url(public_url)
    package_sha256 = str(data.pop('_package_sha256', '') or '').strip().lower() if isinstance(data, dict) else ''
    candidate, strip_warnings = _community_validation_input(data)
    validation = _validate_community_mod_data(candidate, source=public_url)
    warnings = list(validation.warnings) + strip_warnings
    if validation.errors:
        raise ValueError('; '.join(validation.errors))
    normalized = validation.normalized if validation.normalized else candidate
    sha256 = package_sha256 or hashlib.sha256(
        json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    if expected_hash and sha256 != expected_hash:
        raise ValueError('社区模组 hash 不一致')
    mod = load_mod_from_data(normalized, source=public_url, allow_scripts=False)
    if mod.errors:
        raise ValueError('; '.join(mod.errors))
    if warnings:
        mod.warnings.extend(warnings)
    mod.community_sha256 = sha256
    mod.community_url = public_url
    mod.community_data = normalized
    mod.community_uploaded_at = ''
    mod.community_key = ''
    COMMUNITY_MOD_CACHE[sha256] = mod
    COMMUNITY_MOD_CACHE[public_url] = mod
    return mod
