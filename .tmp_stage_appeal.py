# -*- coding: utf-8 -*-
"""Hunk-level staging for the appeal-to-feedback-center migration.

Keeps only this task's hunks from the two files that also carry a parallel
session's uncommitted changes (game.js battle-log/chat work, app.py story/log
work) and feeds each filtered patch to `git apply --cached` via stdin.
"""
import re
import subprocess

REPO = r'E:/Garden of Thorn 荆棘花园/Python联机版'


def filter_patch(path, keep_patterns):
    diff = subprocess.run(
        ['git', 'diff', '--', path],
        capture_output=True, text=True, encoding='utf-8', cwd=REPO,
    ).stdout
    lines = diff.splitlines(keepends=True)
    header, hunks, cur = [], [], None
    for ln in lines:
        if ln.startswith('@@'):
            if cur:
                hunks.append(cur)
            cur = [ln]
        elif cur is not None:
            cur.append(ln)
        else:
            header.append(ln)
    if cur:
        hunks.append(cur)
    kept = [h for h in hunks if any(re.search(p, ''.join(h)) for p in keep_patterns)]
    patch = ''.join(header) + ''.join(''.join(h) for h in kept)
    return patch, len(hunks), len(kept)


def stage_filtered(path, keep_patterns):
    patch, total, kept = filter_patch(path, keep_patterns)
    result = subprocess.run(
        ['git', 'apply', '--cached', '--whitespace=nowarn', '-'],
        input=patch.encode('utf-8'), capture_output=True, cwd=REPO,
    )
    if result.returncode != 0:
        print(f'FAILED {path}:\n{result.stderr}')
        raise SystemExit(1)
    print(f'{path}: staged {kept}/{total} hunks')


stage_filtered(
    'static/js/game.js',
    [r'feedback_appeal_entry', r'申诉表单在反馈中心', r'integrity-appeal-form'],
)
stage_filtered(
    'app.py',
    [r'feedback_center_appeal'],
)
