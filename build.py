import subprocess
import sys
import os

def build_exe(script, name, console=True, extra_data=None, use_pyside=False):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.abspath(os.path.join(base_dir, '..', 'Python运行版'))
    work_dir = os.path.abspath(os.path.join(base_dir, 'build_temp'))
    lang_dir = os.path.join(base_dir, 'lang')

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        f"--name={name}",
        "--distpath", dist_dir,
        "--workpath", work_dir,
        "--specpath", work_dir,
        "--noconfirm",
        "--hidden-import", "client",
        "--hidden-import", "wcwidth",
        "--hidden-import", "_tkinter",
        "--hidden-import", "tkinter",
        "--hidden-import", "mod_loader",
    ]

    if use_pyside:
        cmd += [
            "--hidden-import", "PySide6",
            "--hidden-import", "PySide6.QtCore",
            "--hidden-import", "PySide6.QtGui",
            "--hidden-import", "PySide6.QtWidgets",
        ]

    if os.path.isdir(lang_dir):
        cmd += ["--add-data", f"{lang_dir}{os.pathsep}lang"]

    if extra_data:
        for src, dst in extra_data:
            if os.path.exists(src):
                cmd += ["--add-data", f"{src}{os.pathsep}{dst}"]

    if not console:
        cmd.append("--windowed")
    cmd.append(script)

    try:
        subprocess.check_call(cmd)
        print(f"打包完成：{os.path.join(dist_dir, name + '.exe')}")
    except subprocess.CalledProcessError:
        print("打包失败，请检查上方错误信息")
        sys.exit(1)

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    build_exe("server.py", "server", console=True)
    fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
    build_exe("main.py", "game", console=False,
              extra_data=[(fonts_dir, 'fonts')] if os.path.isdir(fonts_dir) else None)
    build_exe("gtmod_editor.py", "mod_editor", console=False, use_pyside=True)
