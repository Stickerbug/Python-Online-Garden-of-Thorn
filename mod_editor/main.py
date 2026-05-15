import os
import sys
import json
import webview

if sys.platform == 'win32':
    os.environ['PYWEBVIEW_GUI'] = 'edgechromium'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, 'dist')


class Api:
    def __init__(self):
        self.window = None

    def save_file(self, content):
        result = self.window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename='mod.json',
            file_types=('JSON Files (*.json)', 'All Files (*.*)'),
        )
        if result:
            filepath = result if isinstance(result, str) else result[0]
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                return {'success': True, 'path': filepath}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        return {'success': False, 'error': 'cancelled'}

    def open_file(self):
        result = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=('JSON Files (*.json)', 'All Files (*.*)'),
        )
        if result:
            filepath = result if isinstance(result, str) else result[0]
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {'success': True, 'content': content}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        return {'success': False, 'error': 'cancelled'}

    def get_version(self):
        return '1.0.0'


def main():
    index_path = os.path.join(DIST_DIR, 'index.html')
    if not os.path.exists(index_path):
        print(f"[错误] 未找到构建输出: {index_path}")
        print("请先运行: cd mod_editor && npm install && npm run build")
        sys.exit(1)

    api = Api()
    window = webview.create_window(
        '荆棘花园 - 卡牌积木编辑器',
        index_path,
        js_api=api,
        width=1400,
        height=900,
        min_size=(900, 600),
        text_select=True,
    )
    api.window = window
    webview.start(debug='--debug' in sys.argv)


if __name__ == '__main__':
    main()
