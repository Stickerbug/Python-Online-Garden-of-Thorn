# -*- coding: utf-8 -*-
"""Print the engine implementations of one or more card-specific atoms."""

import io
import sys
import pathlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

FILES = ("game_engine.py", "game_engine_2v2.py", "game_engine_urf.py")


def show(name):
    print("=" * 78)
    print("ATOM", name)
    for filename in FILES:
        src = open(filename, encoding="utf-8").read()
        lines = src.splitlines()
        for index, line in enumerate(lines):
            if line.strip().startswith("def _atomic_%s(" % name):
                print("--- %s:%d" % (filename, index + 1))
                for offset in range(index, min(len(lines), index + 120)):
                    text = lines[offset]
                    print("%5d %s" % (offset + 1, text))
                    if offset > index and text.startswith("    def "):
                        break
                print()


if __name__ == "__main__":
    for atom in sys.argv[1:]:
        show(atom)
