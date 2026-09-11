"""魔法邪眼日志标签 + 沉重标签显示（文案/颜色）的回归契约。"""

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME_JS = (ROOT / 'static' / 'js' / 'game.js').read_text(encoding='utf-8')
STYLE_CSS = (ROOT / 'static' / 'css' / 'style.css').read_text(encoding='utf-8')


def test_magic_nazar_has_a_chinese_battle_log_label():
    # 反馈 #64 的残留：运行时侧有映射，引擎侧 _status_log_label 没有，
    # 走引擎路径时日志原样显示 magic_nazar。
    import game_engine

    engine = game_engine.GameEngine()
    assert engine._status_log_label('magic_nazar') == '魔法邪眼'
    assert engine._status_log_label('magicNazar') == '魔法邪眼'


def test_heavy_flag_has_label_colour_and_correct_description():
    import game_engine

    # 服务器侧标签
    assert game_engine.CARD_FLAG_LABELS_ZH.get('heavy') == '沉重'
    # 客户端四语言标签（UI 是 Proxy：缺键会原样显示 tag_heavy）
    assert GAME_JS.count('tag_heavy:') == 4
    # 卡牌 chip 的颜色
    assert '.card-flag.heavy {' in STYLE_CSS
    # 描述不再抄迅捷的"最少为0"
    assert "heavy: lt({ zh: 'E花费增加X。'" in GAME_JS
    assert "heavy: lt({ zh: 'E花费增加X，最少为0。'" not in GAME_JS
