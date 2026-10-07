# -*- coding: utf-8 -*-
"""GB-391：客户端设置账号侧备份——表、get/save 与 GET/PUT 接口。"""

import json
from unittest import mock

import pytest

import app as gtn
import db


@pytest.fixture
def settings_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'client-settings.sqlite3'))
    db.init_db()
    user, error = db.create_user('SettingsUser', 'Aa1!aaaa')
    assert error is None
    return user


def test_save_and_get_roundtrip(settings_db):
    assert db.save_client_settings(settings_db['id'], {
        'gtn_theme': 'dark',
        'gtn_lang': 'zh',
        'not_gtn_key': 'dropped',
    })
    stored = db.get_client_settings(settings_db['id'])
    assert stored['settings'] == {'gtn_theme': 'dark', 'gtn_lang': 'zh'}
    assert stored['updated_at']


def test_missing_settings_returns_none(settings_db):
    assert db.get_client_settings(settings_db['id']) is None


def test_save_overwrites_and_filters(settings_db):
    db.save_client_settings(settings_db['id'], {'gtn_theme': 'dark'})
    db.save_client_settings(settings_db['id'], {'gtn_theme': 'light', 'bad': 'x'})
    stored = db.get_client_settings(settings_db['id'])
    assert stored['settings'] == {'gtn_theme': 'light'}


def test_api_get_and_put(settings_db):
    client = gtn.app.test_client()
    with mock.patch.object(
        gtn, '_require_account_json', return_value=(settings_db['id'], 'SettingsUser', None)
    ):
        put = client.put('/api/client-settings', json={
            'settings': {'gtn_touch_dblclick_intro': '1', 'gtn_theme': 'dark'},
        })
        assert put.status_code == 200
        assert put.get_json()['success'] is True

        got = client.get('/api/client-settings')
        assert got.status_code == 200
        body = got.get_json()
        assert body['settings']['gtn_theme'] == 'dark'
        assert body['updated_at']


def test_api_rejects_invalid_payload(settings_db):
    client = gtn.app.test_client()
    with mock.patch.object(
        gtn, '_require_account_json', return_value=(settings_db['id'], 'SettingsUser', None)
    ):
        bad = client.put('/api/client-settings', json={'settings': 'not-a-dict'})
        assert bad.status_code == 400
        assert bad.get_json()['code'] == 'INVALID_CLIENT_SETTINGS'


def test_api_requires_auth():
    client = gtn.app.test_client()
    response = client.get('/api/client-settings')
    assert response.status_code == 401
