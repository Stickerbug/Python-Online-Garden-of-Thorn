# -*- coding: utf-8 -*-
"""爱发电赞助 → 付费荆露兑换（绑定码 + Webhook 自动到账 + query-order 补单）。

流程：玩家在游戏内 /afdian 页拿到个人绑定码（8 位，可重置）→ 在爱发电选择方案赞助、
付款时把绑定码填进**订单留言** → 爱发电 webhook 把订单 POST 到
``/api/afdian/webhook/<密钥>`` → 按 out_trade_no 幂等登记 ``afdian_orders``，并给绑定码
对应的账号加 ``thorn_dew_paid``（走 ``db.adjust_user_thorn_dew``，
``source_type='afdian'``、``source_id=订单号``，流水可审计）。

webhook 官方文档明说可能漏推：玩家在兑换页点「查询补单」（或管理员
``afdian reconcile``），用爱发电开放平台 ``query-order`` 拉最近订单，走同一条入账路径。

兑换率是数据驱动的：``afdian_plans`` 按 ``plan_id`` 配荆露数（管理端 ``afdian plan set``）。
未映射的方案先记 ``unmapped``，配置后对账/补单会自动补上；绑定码对不上的记
``unmatched``（玩家改绑后旧码失效，由管理员 ``afdian credit`` 兜底）。
按月订阅一次买多个月的，荆露按 ``plan 荆露 × month`` 结算。

爱发电开发者文档：https://guide.afdian.com/creator/developer.md
（后台 https://afdian.com/dashboard/dev 取 user_id / API Token / 配 Webhook。）
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import db

AFDIAN_API_BASE = 'https://afdian.com/api/open/'
BIND_CODE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'   # 去掉 I/O/0/1 防误读
BIND_CODE_LEN = 8
BIND_CODE_RE = re.compile(r'\b([A-Z2-9]{8})\b')
LEDGER_LIMIT = 20
REQUERY_MAX_PAGES = 5          # 补单/对账最多翻 5 页（每页 50 条）

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS afdian_plans (
    plan_id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    dew_amount INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS afdian_orders (
    out_trade_no TEXT PRIMARY KEY,
    afdian_user_id TEXT NOT NULL DEFAULT '',
    user_private_id TEXT NOT NULL DEFAULT '',
    plan_id TEXT NOT NULL DEFAULT '',
    plan_name TEXT NOT NULL DEFAULT '',
    month INTEGER NOT NULL DEFAULT 1,
    total_amount TEXT NOT NULL DEFAULT '0.00',
    show_amount TEXT NOT NULL DEFAULT '0.00',
    remark TEXT NOT NULL DEFAULT '',
    bind_code TEXT NOT NULL DEFAULT '',
    game_user_id INTEGER,
    dew_amount INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'unmatched',   -- credited / unmatched / unmapped / manual
    via TEXT NOT NULL DEFAULT 'webhook',        -- webhook / requery / admin
    order_created_at TEXT NOT NULL DEFAULT '',
    received_at TEXT NOT NULL,
    credited_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_afdian_orders_user ON afdian_orders(game_user_id);
CREATE INDEX IF NOT EXISTS idx_afdian_orders_bind ON afdian_orders(bind_code);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def ensure_schema(conn) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def config() -> Dict[str, str]:
    """爱发电对接配置（生产放 /etc/gtn/shared.env；都为空时 webhook/补单禁用，
    兑换页仍可看绑定码与说明）。"""
    return {
        'user_id': str(os.environ.get('GTN_AFDIAN_USER_ID', '') or '').strip(),
        'token': str(os.environ.get('GTN_AFDIAN_TOKEN', '') or '').strip(),
        'webhook_secret': str(os.environ.get('GTN_AFDIAN_WEBHOOK_SECRET', '') or '').strip(),
    }


# ---------------------------------------------------------------- 绑定码

def bind_code_for(user_id: int) -> str:
    uid = int(user_id)
    with db.get_db_connection() as conn:
        ensure_schema(conn)
        for _ in range(8):
            row = conn.execute(
                'SELECT afdian_bind_code FROM users WHERE id = ?', (uid,)).fetchone()
            current = str(row['afdian_bind_code'] or '').strip() if row else ''
            if current:
                return current
            code = ''.join(secrets.choice(BIND_CODE_ALPHABET) for _ in range(BIND_CODE_LEN))
            conn.execute(
                'UPDATE users SET afdian_bind_code = ? WHERE id = ? AND '
                "(afdian_bind_code IS NULL OR afdian_bind_code = '')", (code, uid))
            conn.commit()
            verify = conn.execute(
                'SELECT 1 FROM users WHERE afdian_bind_code = ? AND id = ?', (code, uid)).fetchone()
            if verify:
                return code
        raise RuntimeError('绑定码生成失败，请稍后重试')


def reset_bind_code(user_id: int) -> str:
    uid = int(user_id)
    with db.get_db_connection() as conn:
        ensure_schema(conn)
        for _ in range(8):
            code = ''.join(secrets.choice(BIND_CODE_ALPHABET) for _ in range(BIND_CODE_LEN))
            cursor = conn.execute(
                'UPDATE users SET afdian_bind_code = ? WHERE id = ?', (code, uid))
            conn.commit()
            if cursor.rowcount:
                return code
        raise RuntimeError('绑定码重置失败，请稍后重试')


def extract_bind_code(remark: str) -> str:
    match = BIND_CODE_RE.search(str(remark or '').upper())
    return match.group(1) if match else ''


# ---------------------------------------------------------------- 入账（幂等核心）

def _plan_dew(conn, plan_id: str) -> Tuple[Optional[int], str]:
    if not plan_id:
        return None, ''
    row = conn.execute(
        'SELECT dew_amount, name FROM afdian_plans WHERE plan_id = ? AND active = 1',
        (str(plan_id),)).fetchone()
    if row is None:
        return None, ''
    return int(row['dew_amount'] or 0), str(row['name'] or '')


def _user_id_for_code(conn, code: str) -> Optional[int]:
    if not code:
        return None
    row = conn.execute('SELECT id FROM users WHERE afdian_bind_code = ?', (code,)).fetchone()
    return int(row['id']) if row else None


def ingest_order(order: Dict[str, Any], *, via: str = 'webhook') -> Dict[str, Any]:
    """登记一条爱发电订单并尽量入账。返回 {status, out_trade_no, detail}。
    幂等：同一订单号只入账一次；unmapped/unmatched 的旧单在条件满足时补结。"""
    out_trade_no = str(order.get('out_trade_no') or '').strip()
    if not out_trade_no:
        return {'status': 'invalid', 'out_trade_no': '', 'detail': '缺少订单号'}
    status_code = int(order.get('status') or 0)
    if status_code != 2:
        return {'status': 'ignored', 'out_trade_no': out_trade_no,
                'detail': f'订单状态非交易成功（status={status_code}）'}
    plan_id = str(order.get('plan_id') or '').strip()
    month = max(1, int(order.get('month') or 1))
    remark = str(order.get('remark') or '').strip()
    code = extract_bind_code(remark)
    now = _now_iso()
    with db.get_db_connection() as conn:
        ensure_schema(conn)
        existing = conn.execute(
            'SELECT * FROM afdian_orders WHERE out_trade_no = ?', (out_trade_no,)).fetchone()
        if existing is None:
            game_user_id = _user_id_for_code(conn, code)
            conn.execute(
                '''INSERT INTO afdian_orders (
                    out_trade_no, afdian_user_id, user_private_id, plan_id, plan_name, month,
                    total_amount, show_amount, remark, bind_code, game_user_id, dew_amount,
                    status, via, order_created_at, received_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (out_trade_no,
                 str(order.get('user_id') or ''), str(order.get('user_private_id') or ''),
                 plan_id, '', month,
                 str(order.get('total_amount') or '0.00'),
                 str(order.get('show_amount') or '0.00'),
                 remark, code, game_user_id, 0,
                 'pending', via, str(order.get('created_at') or ''), now))
            conn.commit()
        elif str(existing['status']) == 'credited':
            return {'status': 'duplicate', 'out_trade_no': out_trade_no, 'detail': '已入账'}
    return _settle(out_trade_no, via=via)


def _settle(out_trade_no: str, *, via: str) -> Dict[str, Any]:
    """尝试入账：事务里**先占位**（判定结果与荆露数写回 ledger 并置 credited），
    提交后再走 ``adjust_user_thorn_dew``（它自开连接，外层不能持锁跨调用）；
    加款失败则把占位回滚，单子留待重试/人工。"""
    with db.get_db_connection() as conn:
        ensure_schema(conn)
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute(
            'SELECT * FROM afdian_orders WHERE out_trade_no = ?', (out_trade_no,)).fetchone()
        if row is None:
            conn.rollback()
            return {'status': 'missing', 'out_trade_no': out_trade_no, 'detail': '订单不存在'}
        if str(row['status']) == 'credited':
            conn.rollback()
            return {'status': 'duplicate', 'out_trade_no': out_trade_no, 'detail': '已入账'}
        game_user_id = row['game_user_id']
        if game_user_id is None:
            game_user_id = _user_id_for_code(conn, str(row['bind_code'] or ''))
        dew_per, plan_name = _plan_dew(conn, str(row['plan_id'] or ''))
        month = max(1, int(row['month'] or 1))
        if game_user_id is None:
            conn.execute(
                "UPDATE afdian_orders SET status='unmatched', plan_name=? WHERE out_trade_no=?",
                (plan_name, out_trade_no))
            conn.commit()
            return {'status': 'unmatched', 'out_trade_no': out_trade_no,
                    'detail': f"留言里没有可识别的绑定码（remark={row['remark']!r}）"}
        if not dew_per:
            conn.execute(
                "UPDATE afdian_orders SET status='unmapped', plan_name=?, game_user_id=? "
                "WHERE out_trade_no=?",
                (plan_name, int(game_user_id), out_trade_no))
            conn.commit()
            return {'status': 'unmapped', 'out_trade_no': out_trade_no,
                    'detail': f"方案未配置荆露（plan_id={row['plan_id']}），配置后对账自动补"}
        dew = int(dew_per) * month
        # 先占位再出账：占位提交后并发的 ingest 只会看到 credited（幂等），
        # 出账失败再回滚为 pending 等下次补。
        conn.execute(
            "UPDATE afdian_orders SET status='credited', game_user_id=?, dew_amount=?, "
            "plan_name=?, credited_at=?, via=? WHERE out_trade_no=?",
            (int(game_user_id), dew, plan_name, _now_iso(), via, out_trade_no))
        conn.commit()
    payload, error = db.adjust_user_thorn_dew(
        int(game_user_id), free_delta=0, paid_delta=dew,
        reason=f'爱发电赞助到账 {out_trade_no}（{plan_name or row["plan_id"]}×{month}）',
        source_type='afdian', source_id=out_trade_no)
    if error:
        with db.get_db_connection() as conn:
            conn.execute(
                "UPDATE afdian_orders SET status='pending', dew_amount=0, credited_at=NULL "
                "WHERE out_trade_no=?", (out_trade_no,))
            conn.commit()
        return {'status': 'error', 'out_trade_no': out_trade_no, 'detail': str(error)}
    return {'status': 'credited', 'out_trade_no': out_trade_no,
            'dew': dew, 'user_id': int(game_user_id)}


# ---------------------------------------------------------------- 开放平台 API（补单/对账）

def api_sign(params_json: str, ts: int, user_id: str, token: str) -> str:
    """官方签名：md5(token + 'params' + params + 'ts' + ts + 'user_id' + user_id)，
    无分隔符。文档示例：token=123、params={"a":333}、ts=1624339905、user_id=abc
    → a4acc28b81598b7e5d84ebdc3e91710c。"""
    raw = f"{token}params{params_json}ts{ts}user_id{user_id}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


def _api_post(path: str, params: Dict[str, Any], *, timeout: float = 10.0) -> Dict[str, Any]:
    cfg = config()
    if not (cfg['user_id'] and cfg['token']):
        raise RuntimeError('爱发电 API 未配置（GTN_AFDIAN_USER_ID / GTN_AFDIAN_TOKEN）')
    ts = int(datetime.now(timezone.utc).timestamp())
    params_json = json.dumps(params, separators=(',', ':'), ensure_ascii=False)
    form = urllib.parse.urlencode({
        'user_id': cfg['user_id'],
        'params': params_json,
        'ts': ts,
        'sign': api_sign(params_json, ts, cfg['user_id'], cfg['token']),
    }).encode('utf-8')
    request = urllib.request.Request(
        AFDIAN_API_BASE + path, data=form,
        headers={'Content-Type': 'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


def requery_recent(pages: int = 2) -> Dict[str, Any]:
    """拉最近的订单（默认 2 页 = 100 条）走同一入账路径；返回逐条结果摘要。
    漏推的 webhook、以及配置了方案映射后待补的 unmapped 单都在这里补上。"""
    cfg = config()
    if not (cfg['user_id'] and cfg['token']):
        return {'ok': False, 'error': '爱发电 API 未配置'}
    pages = max(1, min(int(pages or 2), REQUERY_MAX_PAGES))
    summary: List[Dict[str, Any]] = []
    for page in range(1, pages + 1):
        data = _api_post('query-order', {'page': page})
        if int(data.get('ec') or 0) != 200:
            return {'ok': False, 'error': f"query-order 第 {page} 页失败：{data.get('em')}"}
        payload = data.get('data') or {}
        for order in (payload.get('list') or []):
            summary.append(ingest_order(order, via='requery'))
        if page >= int(payload.get('total_page') or 1):
            break
    counted: Dict[str, int] = {}
    for item in summary:
        key = str(item.get('status') or '?')
        counted[key] = counted.get(key, 0) + 1
    return {'ok': True, 'total': len(summary), 'counted': counted, 'items': summary}


# ---------------------------------------------------------------- 查询 / 管理端

def ledger_for_user(user_id: int, limit: int = LEDGER_LIMIT) -> List[Dict[str, Any]]:
    with db.get_db_connection() as conn:
        ensure_schema(conn)
        rows = conn.execute(
            'SELECT * FROM afdian_orders WHERE game_user_id = ? '
            'ORDER BY received_at DESC LIMIT ?', (int(user_id), int(limit))).fetchall()
        return [dict(row) for row in rows]


def public_plans() -> List[Dict[str, Any]]:
    """兑换页展示的档位（name+荆露数；价格写在 name 里，如「¥10 档」）。"""
    with db.get_db_connection() as conn:
        ensure_schema(conn)
        rows = conn.execute(
            'SELECT plan_id, name, dew_amount FROM afdian_plans '
            'WHERE active = 1 ORDER BY dew_amount ASC').fetchall()
        return [dict(row) for row in rows]


def admin_set_plan(plan_id: str, dew_amount: int, name: str = '') -> Dict[str, Any]:
    plan_id = str(plan_id or '').strip()
    dew = max(0, int(dew_amount or 0))
    if not plan_id:
        return {'ok': False, 'error': '缺少 plan_id'}
    now = _now_iso()
    with db.get_db_connection() as conn:
        ensure_schema(conn)
        conn.execute(
            '''INSERT INTO afdian_plans (plan_id, name, dew_amount, active, created_at, updated_at)
               VALUES (?,?,?,1,?,?)
               ON CONFLICT(plan_id) DO UPDATE SET
                 name=excluded.name, dew_amount=excluded.dew_amount, updated_at=excluded.updated_at''',
            (plan_id, str(name or ''), dew, now, now))
        conn.commit()
    # 配置/修改映射后顺手把待补的 unmapped 单结掉（未配置 API 时只是拉不到，无副作用）
    requery_recent(pages=2)
    return {'ok': True, 'plan_id': plan_id, 'dew_amount': dew}


def admin_list_plans() -> List[Dict[str, Any]]:
    with db.get_db_connection() as conn:
        ensure_schema(conn)
        rows = conn.execute('SELECT * FROM afdian_plans ORDER BY dew_amount ASC').fetchall()
        return [dict(row) for row in rows]


def admin_list_orders(limit: int = 20) -> List[Dict[str, Any]]:
    with db.get_db_connection() as conn:
        ensure_schema(conn)
        rows = conn.execute(
            'SELECT * FROM afdian_orders ORDER BY received_at DESC LIMIT ?',
            (max(1, min(int(limit or 20), 100)),)).fetchall()
        return [dict(row) for row in rows]


def admin_credit(out_trade_no: str, dew: int, user_id: int, reason: str = '') -> Dict[str, Any]:
    """兜底手动入账（unmatched / 金额有争议等）：指定账号与荆露数，记 manual。"""
    out_trade_no = str(out_trade_no or '').strip()
    dew = int(dew or 0)
    if not out_trade_no or dew <= 0:
        return {'ok': False, 'error': '需要订单号与正数荆露'}
    payload, error = db.adjust_user_thorn_dew(
        int(user_id), free_delta=0, paid_delta=dew,
        reason=reason or f'爱发电赞助手动入账 {out_trade_no}',
        source_type='afdian', source_id=out_trade_no)
    if error:
        return {'ok': False, 'error': str(error)}
    with db.get_db_connection() as conn:
        ensure_schema(conn)
        conn.execute(
            "UPDATE afdian_orders SET status='manual', game_user_id=?, dew_amount=?, "
            "credited_at=?, via='admin' WHERE out_trade_no=?", (int(user_id), dew, _now_iso(), out_trade_no))
        conn.commit()
    return {'ok': True, 'out_trade_no': out_trade_no, 'dew': dew}
