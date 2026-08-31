from pathlib import Path
from datetime import datetime, timedelta, timezone
import io
import json
import zipfile

import pytest

import r2_mods


class _PresignClient:
    def __init__(self):
        self.calls = []

    def generate_presigned_url(self, **kwargs):
        self.calls.append(kwargs)
        return 'https://upload.invalid/signed-put'


class _Response:
    def __init__(self, raw=b'', status_code=200, headers=None):
        self.raw = raw
        self.status_code = status_code
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')

    def iter_content(self, chunk_size=16384):
        for offset in range(0, len(self.raw), chunk_size):
            yield self.raw[offset:offset + chunk_size]


class _StorageClient:
    def __init__(self, objects):
        self.objects = list(objects)
        self.deleted = []

    def list_objects_v2(self, **kwargs):
        start = int(kwargs.get('ContinuationToken') or 0)
        stop = min(len(self.objects), start + int(kwargs.get('MaxKeys') or 1000))
        truncated = stop < len(self.objects)
        return {
            'Contents': list(self.objects[start:stop]),
            'IsTruncated': truncated,
            'NextContinuationToken': str(stop) if truncated else None,
        }

    def delete_object(self, *, Bucket, Key):
        self.deleted.append((Bucket, Key))


class _Requests:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def _gtnmod_bytes(entries):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for name, value in entries:
            zf.writestr(name, value)
    return output.getvalue()


@pytest.fixture
def upload_context(monkeypatch):
    client = _PresignClient()
    monkeypatch.setattr(r2_mods, '_client', lambda: client)
    monkeypatch.setattr(r2_mods, '_bucket', lambda: 'test-bucket')
    monkeypatch.setattr(r2_mods, 'r2_public_base_url', lambda: 'https://mods.example.test')
    return 'receipt-secret-for-community-mod-tests', client


def test_upload_receipt_binds_user_key_url_and_expiry(upload_context):
    receipt_secret, client = upload_context
    result = r2_mods.create_presigned_mod_upload(
        'example.gtnmod',
        expected_size=1234,
        uploader_user_id=41,
        receipt_secret=receipt_secret,
    )

    verified = r2_mods.verify_mod_upload_receipt(
        result['upload_receipt'],
        uploader_user_id=41,
        receipt_secret=receipt_secret,
        now=result['expires_at'],
    )
    assert verified['key'] == result['key']
    assert verified['public_url'] == result['public_url']
    assert verified['expires_at'] == result['expires_at']
    assert verified['expected_size'] == 1234
    assert client.calls[0]['Params']['ContentLength'] == 1234

    with pytest.raises(ValueError, match='不属于当前账号'):
        r2_mods.verify_mod_upload_receipt(
            result['upload_receipt'],
            uploader_user_id=42,
            receipt_secret=receipt_secret,
            now=result['expires_at'],
        )
    with pytest.raises(ValueError, match='已过期'):
        r2_mods.verify_mod_upload_receipt(
            result['upload_receipt'],
            uploader_user_id=41,
            receipt_secret=receipt_secret,
            now=result['expires_at'] + 1,
        )


def test_presigned_upload_rejects_unbounded_or_empty_files(upload_context):
    receipt_secret, _client = upload_context
    with pytest.raises(ValueError, match='文件大小无效'):
        r2_mods.create_presigned_mod_upload(
            'empty.json', expected_size=0, uploader_user_id=41, receipt_secret=receipt_secret,
        )
    with pytest.raises(ValueError, match='文件大小无效'):
        r2_mods.create_presigned_mod_upload(
            'huge.gtnmod',
            expected_size=r2_mods.MAX_COMMUNITY_PACKAGE_BYTES + 1,
            uploader_user_id=41,
            receipt_secret=receipt_secret,
        )

    game_source = Path(__file__).resolve().parents[1].joinpath('static/js/game.js').read_text(encoding='utf-8')
    assert "JSON.stringify({ filename: file.name, size_bytes: file.size })" in game_source


def test_tampered_upload_receipt_and_request_binding_are_rejected(upload_context, monkeypatch):
    receipt_secret, _client = upload_context
    result = r2_mods.create_presigned_mod_upload(
        'example.json',
        expected_size=321,
        uploader_user_id=7,
        receipt_secret=receipt_secret,
    )
    tampered = result['upload_receipt'][:-1] + ('A' if result['upload_receipt'][-1] != 'A' else 'B')
    with pytest.raises(ValueError, match='签名无效'):
        r2_mods.verify_mod_upload_receipt(
            tampered,
            uploader_user_id=7,
            receipt_secret=receipt_secret,
        )

    monkeypatch.setattr(
        r2_mods,
        'fetch_json_from_public_url',
        lambda _url: pytest.fail('binding mismatch must be rejected before any fetch'),
    )
    response = r2_mods.register_community_mod(
        result['public_url'],
        'community/uploads/victim-object.json',
        uploader_user_id=7,
        upload_receipt=result['upload_receipt'],
        receipt_secret=receipt_secret,
    )
    assert response['success'] is False
    assert '不一致' in response['errors'][0]


def test_poisoned_index_key_cannot_be_deleted_with_server_credentials(monkeypatch):
    target = {
        'sha256': 'a' * 64,
        'key': 'private/victim-object.json',
        'public_url': 'https://mods.example.test/private/victim-object.json',
        'uploader_user_id': 9,
    }
    monkeypatch.setattr(r2_mods, 'get_community_index', lambda force=False: {'mods': [target]})
    monkeypatch.setattr(
        r2_mods,
        '_move_object_to_trash',
        lambda *_args, **_kwargs: pytest.fail('unsafe object key must never reach R2 mutation'),
    )

    response = r2_mods.delete_community_mod('a' * 64, uploader_user_id=9)
    assert response == {'success': False, 'error': '模组对象绑定异常，已拒绝自动删除'}


def test_public_community_index_does_not_expose_storage_key():
    app_source = Path(__file__).resolve().parents[1].joinpath('app.py').read_text(encoding='utf-8')
    route_source = app_source.split("@app.route('/api/community-mods')", 1)[1].split(
        "@app.route('/api/community-mods/upload-url'", 1
    )[0]
    assert "row.pop('key', None)" in route_source


def test_r2_fetch_rejects_cross_origin_and_redirects(monkeypatch):
    monkeypatch.setattr(r2_mods, 'r2_public_base_url', lambda: 'https://mods.example.test/public')
    fake_requests = _Requests(_Response(status_code=302, headers={'Location': 'http://127.0.0.1/'}))
    monkeypatch.setattr(r2_mods, 'requests', fake_requests)

    with pytest.raises(ValueError, match='公开域名'):
        r2_mods.fetch_json_from_public_url('https://mods.example.test.evil/public/mod.json')
    assert not fake_requests.calls

    with pytest.raises(ValueError, match='不允许重定向'):
        r2_mods.fetch_json_from_public_url('https://mods.example.test/public/mod.json')
    assert fake_requests.calls[0][1]['allow_redirects'] is False


def test_gtnmod_rejects_high_ratio_assets_before_decompression(monkeypatch):
    raw = _gtnmod_bytes([
        ('mod.json', json.dumps({'format_version': 2, 'registries': {'cards': []}})),
        ('assets/cards/bomb.png', b'0' * (1024 * 1024)),
    ])
    monkeypatch.setattr(r2_mods, 'r2_public_base_url', lambda: 'https://mods.example.test')
    monkeypatch.setattr(r2_mods, 'requests', _Requests(_Response(raw=raw)))

    with pytest.raises(ValueError, match='压缩比过高'):
        r2_mods.fetch_json_from_public_url('https://mods.example.test/community/uploads/bomb.gtnmod')


def test_gtnmod_rejects_too_many_archive_entries(monkeypatch):
    entries = [('mod.json', '{}')]
    entries.extend((f'assets/cards/{index}.png', b'x') for index in range(r2_mods.MAX_COMMUNITY_PACKAGE_FILES))
    raw = _gtnmod_bytes(entries)
    monkeypatch.setattr(r2_mods, 'r2_public_base_url', lambda: 'https://mods.example.test')
    monkeypatch.setattr(r2_mods, 'requests', _Requests(_Response(raw=raw)))

    with pytest.raises(ValueError, match='文件数量过多'):
        r2_mods.fetch_json_from_public_url('https://mods.example.test/community/uploads/many.gtnmod')


def test_orphan_upload_cleanup_only_deletes_old_unreferenced_safe_keys(monkeypatch):
    now = datetime.now(timezone.utc)
    referenced_key = 'community/uploads/1700000000-ref-mod.json'
    orphan_key = 'community/uploads/1700000000-orphan-mod.gtnmod'
    fresh_key = 'community/uploads/1700000001-fresh-mod.json'
    client = _StorageClient([
        {'Key': referenced_key, 'Size': 100, 'LastModified': now - timedelta(hours=2)},
        {'Key': orphan_key, 'Size': 200, 'LastModified': now - timedelta(hours=2)},
        {'Key': fresh_key, 'Size': 300, 'LastModified': now - timedelta(minutes=5)},
        {'Key': 'community/uploads/unsafe.exe', 'Size': 400, 'LastModified': now - timedelta(days=2)},
    ])
    monkeypatch.setattr(r2_mods, '_client', lambda: client)
    monkeypatch.setattr(r2_mods, '_bucket', lambda: 'test-bucket')
    monkeypatch.setattr(
        r2_mods,
        'get_community_index',
        lambda force=False: {'mods': [{'key': referenced_key}]},
    )

    preview = r2_mods.cleanup_orphaned_community_uploads(min_age_seconds=3600, dry_run=True)
    assert [item['key'] for item in preview['candidates']] == [orphan_key]
    assert preview['scan_truncated'] is False
    assert client.deleted == []

    result = r2_mods.cleanup_orphaned_community_uploads(min_age_seconds=3600, dry_run=False)
    assert result['deleted_keys'] == [orphan_key]
    assert client.deleted == [('test-bucket', orphan_key)]


def test_orphan_upload_cleanup_reports_scan_limit_without_false_positive(monkeypatch):
    now = datetime.now(timezone.utc) - timedelta(hours=2)
    objects = [
        {'Key': f'community/uploads/170000000{index}-orphan-{index}.json', 'Size': 10, 'LastModified': now}
        for index in range(2)
    ]
    client = _StorageClient(objects)
    monkeypatch.setattr(r2_mods, '_client', lambda: client)
    monkeypatch.setattr(r2_mods, '_bucket', lambda: 'test-bucket')
    monkeypatch.setattr(r2_mods, 'get_community_index', lambda force=False: {'mods': []})

    limited = r2_mods.cleanup_orphaned_community_uploads(
        min_age_seconds=3600,
        dry_run=True,
        max_scan=1,
    )
    complete = r2_mods.cleanup_orphaned_community_uploads(
        min_age_seconds=3600,
        dry_run=True,
        max_scan=2,
    )
    assert limited['scanned'] == 1
    assert limited['scan_truncated'] is True
    assert complete['scanned'] == 2
    assert complete['scan_truncated'] is False
