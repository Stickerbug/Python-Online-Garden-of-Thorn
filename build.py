import subprocess
import sys
import os

def build_exe(script, name, console=True):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.abspath(os.path.join(base_dir, '..', 'Python运行版'))
    work_dir = os.path.abspath(os.path.join(base_dir, 'build_temp'))
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        f"--name={name}",
        "--distpath", dist_dir,
        "--workpath", work_dir,
        "--specpath", work_dir,
        "--noconfirm",
    ]
    if not console:
        cmd.append("--windowed")
    cmd.append(script)
    subprocess.check_call(cmd)
    print(f"打包完成：{os.path.join(dist_dir, name + '.exe')}")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    build_exe("server.py", "server", console=True)
    build_exe("main.py", "game", console=False)
    print("所有打包完成！")