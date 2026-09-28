# -*- coding: utf-8 -*-
"""#235 反馈中心图片附件（严格限制版，设计确认 2026-09-27）：

- 仅登录用户可上传；仅 PNG/JPEG/WebP/GIF
- 单张 ≤ 300KB；每条反馈 ≤ 3 张；每条评论 ≤ 1 张
- 存储为独立文件（static 外部目录 /var/lib/gtn/feedback-attachments/），
  DB 只记元数据；文件名 = 随机 token，无法枚举
- 通过 /feedback-attachments/<token> 提供访问，Content-Disposition: inline，
  响应带 immutable 缓存
- 无外链防盗链需求（同站），但 JSON 里回传的 URL 不暴露文件系统路径
"""

import io
import os
import secrets
from contextlib import closing

import db

ATTACHMENT_MAX_BYTES = 300 * 1024
ATTACHMENT_MAX_PER_ISSUE = 3
ATTACHMENT_MAX_PER_COMMENT = 1
ATTACHMENT_ALLOWED_TYPES = {
    'image/png': '.png',
    'image/jpeg': '.jpg',
    'image/webp': '.webp',
    'image/gif': '.gif',
}
# PNG/JPEG/WebP/GIF 的魔数白名单（不能只信 Content-Type 头）
_MAGIC = (
    (b'\x89PNG\r\n\x1a\n', 'image/png'),
    (b'\xff\xd8\xff', 'image/jpeg'),
    (b'GIF87a', 'image/gif'),
    (b'GIF89a', 'image/gif'),
)


def attachment_dir():
    base = os.environ.get('GTN_FEEDBACK_ATTACHMENTS_DIR', '/var/lib/gtn/feedback-attachments')
    os.makedirs(base, exist_ok=True)
    return base


def sniff_image_type(data):
    """按魔数识别图片类型；非白名单返回 None。"""
    if len(data) > ATTACHMENT_MAX_BYTES:
        return None
    for magic, mime in _MAGIC:
        if data.startswith(magic):
            return mime
    # WebP: RIFF....WEBP
    if len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp'
    return None


def save_attachment(author_user_id, data, *, declared_name=''):
    """校验并保存一张图片。返回 (attachment_id, url) 或抛 PublicFeedbackError。"""
    from public_feedback import PublicFeedbackError
    uid = int(author_user_id)
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise PublicFeedbackError('ATTACHMENT_EMPTY', '附件内容为空')
    data = bytes(data)
    if len(data) > ATTACHMENT_MAX_BYTES:
        raise PublicFeedbackError(
            'ATTACHMENT_TOO_LARGE',
            f'图片不能超过 {ATTACHMENT_MAX_BYTES // 1024}KB',
        )
    mime = sniff_image_type(data)
    if mime is None:
        raise PublicFeedbackError(
            'ATTACHMENT_TYPE_INVALID',
            '仅支持 PNG/JPEG/WebP/GIF 图片（且 ≤300KB）',
        )
    ext = ATTACHMENT_ALLOWED_TYPES[mime]
    token = secrets.token_urlsafe(16).replace('-', '_').replace('_', 'a')
    filename = f'{token}{ext}'
    path = os.path.join(attachment_dir(), filename)
    with open(path, 'wb') as fh:
        fh.write(data)
    now = db.utc_now()
    with closing(db.get_db_connection()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS feedback_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                mime TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                uploader_user_id INTEGER,
                issue_id INTEGER,
                created_at TEXT NOT NULL
            )
            '''
        )
        cursor = conn.execute(
            '''
            INSERT INTO feedback_attachments
                (token, filename, mime, size_bytes, uploader_user_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (token, filename, mime, len(data), uid, now),
        )
        attachment_id = int(cursor.lastrowid)
        conn.commit()
    return attachment_id, f'/feedback-attachments/{token}'


def attach_to_issue(attachment_id, issue_id):
    with closing(db.get_db_connection()) as conn:
        conn.execute(
            'UPDATE feedback_attachments SET issue_id = ? WHERE id = ?',
            (int(issue_id), int(attachment_id)),
        )
        conn.commit()


def attachments_for_issue(issue_id):
    with closing(db.get_db_connection()) as conn:
        rows = conn.execute(
            'SELECT token, mime, size_bytes FROM feedback_attachments WHERE issue_id = ? ORDER BY id',
            (int(issue_id),),
        ).fetchall()
    return [
        {
            'url': f'/feedback-attachments/{row["token"]}',
            'mime': row['mime'],
            'size_bytes': int(row['size_bytes'] or 0),
        }
        for row in rows
    ]


def count_issue_attachments(issue_id):
    with closing(db.get_db_connection()) as conn:
        row = conn.execute(
            'SELECT COUNT(*) AS c FROM feedback_attachments WHERE issue_id = ?',
            (int(issue_id),),
        ).fetchone()
    return int(row['c'] or 0)


def open_attachment_file(token):
    """按 token 打开文件；返回 (path, mime) 或 None。token 格式非法直接拒绝。"""
    import re
    if not re.fullmatch(r'[A-Za-z0-9]{20,24}', str(token or '')):
        return None
    with closing(db.get_db_connection()) as conn:
        # 只读路径不能因缺表而 500：GET 可能先于任何上传发生。
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS feedback_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                mime TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                uploader_user_id INTEGER,
                issue_id INTEGER,
                created_at TEXT NOT NULL
            )
            '''
        )
        conn.commit()
        row = conn.execute(
            'SELECT filename, mime FROM feedback_attachments WHERE token = ?',
            (str(token),),
        ).fetchone()
    if row is None:
        return None
    path = os.path.join(attachment_dir(), str(row['filename']))
    if not os.path.isfile(path):
        return None
    return path, row['mime']
