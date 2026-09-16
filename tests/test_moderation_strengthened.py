"""反馈：辱骂、色情、政治、广告、非法交易、隐私词都没被拦住。

锁住新的分级（色情/政治/黑名单网址升到 L3 打码）与手动词表
（static/data/moderation_manual.json，改文件即热加载）。
"""

import json
import os
import time
from pathlib import Path

import moderation


ROOT = Path(__file__).resolve().parents[1]


def _level(text):
    return int(moderation.check_message_risk(text).get('risk_level') or 0)


def test_manual_term_file_covers_every_category():
    doc = json.loads(
        (ROOT / 'static' / 'data' / 'moderation_manual.json').read_text(encoding='utf-8')
    )
    categories = set(doc.get('categories') or {})
    assert {
        'abusive_common', 'abusive_severe',
        'sexual_common', 'sexual_severe',
        'political_common', 'political_severe',
        'advertising_common', 'advertising_severe',
        'illegal_common', 'illegal_severe',
        'privacy_terms', 'privacy_patterns',
    } <= categories


def test_abusive_and_sexual_terms_are_blocked():
    assert _level('傻逼') >= 3
    assert _level('你这个智障') >= 3
    assert _level('滚蛋吧') >= 3
    assert _level('死全家') == 4
    assert _level('操你妈') == 4
    assert _level('母狗') == 4
    assert _level('黄片') >= 3
    assert _level('涩涩') >= 3
    assert _level('裸聊') == 4
    assert _level('约炮') == 4
    assert _level('福利姬') == 4


def test_political_advertising_illegal_and_privacy_are_blocked():
    assert _level('习近平') >= 3
    assert _level('法轮功') == 4
    assert _level('疆独') == 4
    assert _level('代练') >= 3
    assert _level('卖号加微信') >= 3
    assert _level('出售外挂') == 4
    assert _level('出售毒品') == 4
    assert _level('冰毒') == 4
    assert _level('出售银行卡') == 4
    assert _level('身份证号') >= 3
    assert _level('我的手机号是13800138000') >= 3
    assert _level('身份证11010119900307721X') >= 3


def test_third_party_lists_now_mask_instead_of_only_flagging():
    doc = json.loads(
        (ROOT / 'static' / 'data' / 'moderation_rules.json').read_text(encoding='utf-8')
    )
    levels = {
        str(rule.get('id')): int(rule.get('level') or 0)
        for rule in doc.get('rules') or []
    }
    assert levels.get('third_party.sexual') == 3
    assert levels.get('third_party.political') == 3
    assert levels.get('third_party.url_blacklist') == 3


def test_common_game_chat_is_not_masked():
    for text in (
        '操作很简单', '颜色不见了', '属性加成', '我在网络游戏里玩', '客服很热情',
        '王小姐你好', '大麻袋', '加群了吗', '看电影去了', '我家的野狗', '这局刷分',
        '+1E 能量够吗', '这张牌有点废物',
    ):
        assert _level(text) < 3, text


def test_matching_terms_are_masked_in_output():
    result = moderation.check_message_risk('你这个傻逼')
    assert result.get('risk_level') >= 3
    assert '傻逼' not in str(result.get('sanitized_text') or '')


def test_traditional_characters_are_normalized():
    for text in ('賤人', '傻屄', '強姦', '賣淫', '代練'):
        assert _level(text) >= 3, text
    result = moderation.check_message_risk('賤人')
    assert result.get('sanitized_text') == '***'


def test_pinyin_and_abbreviation_variants_are_caught():
    assert _level('shabi') >= 3
    assert _level('nmsl') == 4
    assert _level('cnm') == 4
    assert _level('mdzz') >= 3
    assert _level('2b') >= 3
    assert _level('yuepao') == 4
    assert _level('luoliao') == 4


def test_homoglyph_evasion_is_folded_before_matching():
    assert _level('sh\u0430bi') >= 3   # 西里尔字母 а
    assert _level('sh\u03b1bi') >= 3   # 希腊字母 α
    assert _level('f\u03c5ck') >= 3    # 希腊字母 υ


def test_traditional_to_simplified_table_is_generated():
    doc = json.loads(
        (ROOT / 'static' / 'data' / 'moderation_t2s.json').read_text(encoding='utf-8')
    )
    mapping = doc.get('map') or {}
    assert mapping.get('賤') == '贱'
    assert mapping.get('強') == '强'
    assert len(mapping) > 100


def test_nickname_blocks_abusive_terms():
    assert moderation.check_nickname_risk('傻逼玩家').get('blocked') is True
    assert moderation.check_nickname_risk('法轮功学员').get('blocked') is True


def test_manual_terms_hot_reload(tmp_path, monkeypatch):
    manual_path = tmp_path / 'manual.json'
    manual_path.write_text(
        json.dumps(
            {'categories': {'probe': {'category': 'abusive', 'level': 3, 'terms': ['探针违禁词一']}}},
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    monkeypatch.setenv('GTN_MODERATION_MANUAL_PATH', str(manual_path))
    monkeypatch.setattr(moderation, '_RULE_CACHE', None)
    monkeypatch.setattr(moderation, '_RULE_CACHE_MTIME', None)

    assert _level('探针违禁词一') >= 3

    manual_path.write_text(
        json.dumps(
            {'categories': {'probe': {'category': 'abusive', 'level': 3, 'terms': ['探针违禁词二']}}},
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    bumped = time.time() + 5
    os.utime(manual_path, (bumped, bumped))

    assert _level('探针违禁词二') >= 3
    assert _level('探针违禁词一') == 0
