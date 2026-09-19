"""反馈 #153：老引擎不认 ``dvh`` 时故事布局会塌掉；#138：反馈中心弹键盘会把背景滚走。

两条都是移动端表现，代码层的确认如下：

* #153 ``.story-app`` 的整屏高度只写了 ``100dvh``，而 ``body`` 是 ``overflow: hidden``；
  一旦引擎不支持 ``dvh``（部分安卓 WebView/Edge），布局没有高度、地图最后几行就再也
  滚不到。修法是每个 ``dvh`` 声明前面补一条 ``vh`` 兜底。
* #138 反馈中心完全没有键盘/滚动处理，手机端软键盘弹起时浏览器会滚动文档露出输入框，
  收起后背景就停在滚动后的位置。修法是打开对话框时锁住文档滚动、全部关闭后还原。
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORY_CSS = (ROOT / 'static' / 'css' / 'story.css').read_text(encoding='utf-8')
FC_CSS = (ROOT / 'static' / 'css' / 'feedback_center.css').read_text(encoding='utf-8')
FC_JS = (ROOT / 'static' / 'js' / 'feedback_center.js').read_text(encoding='utf-8')


def test_every_dvh_declaration_has_a_vh_fallback():
    lines = STORY_CSS.splitlines()
    missing = []
    for index, line in enumerate(lines):
        if '100dvh' not in line:
            continue
        previous = lines[index - 1].strip() if index else ''
        if '100vh' not in previous:
            missing.append(line.strip())
    assert missing == []


def test_story_app_keeps_a_vh_fallback_height():
    assert '.story-app {' in STORY_CSS
    block = STORY_CSS.split('.story-app {', 1)[1].split('}', 1)[0]
    assert 'height: 100vh;' in block
    assert 'height: 100dvh;' in block


def test_feedback_center_locks_the_background_while_a_dialog_is_open():
    assert 'html.fc-scroll-locked,' in FC_CSS
    assert 'html.fc-scroll-locked body {' in FC_CSS
    assert 'html.fc-scroll-locked body {\n  position: fixed;' in FC_CSS
    assert 'function lockFeedbackBackgroundScroll()' in FC_JS
    assert 'function releaseFeedbackBackgroundScroll()' in FC_JS
    assert 'function bindDialogScrollLock()' in FC_JS
    assert "document.addEventListener('toggle', (event) => {" in FC_JS
    assert 'window.scrollTo(0, restoreY);' in FC_JS
    assert 'bindDialogScrollLock();' in FC_JS
