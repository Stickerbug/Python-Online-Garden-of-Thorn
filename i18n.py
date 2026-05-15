import json
import os

_lang_data = {}
_current_lang = 'zh_CN'
_lang_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lang')
_available_langs = ['zh_CN', 'en_US']


def get_available_langs():
    return _available_langs


def get_lang_display_name(lang_code):
    names = {'zh_CN': '简体中文', 'en_US': 'English'}
    return names.get(lang_code, lang_code)


def load_lang(lang_code):
    global _lang_data, _current_lang
    path = os.path.join(_lang_dir, f'{lang_code}.json')
    if not os.path.exists(path):
        path = os.path.join(_lang_dir, 'zh_CN.json')
    with open(path, 'r', encoding='utf-8') as f:
        _lang_data = json.load(f)
    _current_lang = lang_code


def t(key, **kwargs):
    text = _lang_data.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


def current_lang():
    return _current_lang


load_lang('zh_CN')
