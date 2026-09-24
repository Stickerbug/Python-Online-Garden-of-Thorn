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
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import db

AFDIAN_API_BASE = 'https://afdian.com/api/open/'
BIND_CODE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'   # 去掉 I/O/0/1 防误读
BIND_CODE_LEN = 8
# 留言识别要扛住随意书写（反馈：前缀/后缀其他字符或空格、大小写混淆）：
# - 先 NFKC 归一（全角字母/数字 → 半角）再 upper()（小写 → 大写）；
# - 边界用 ASCII 字母数字的 lookaround 而不是 \b——\b 认为 CJK 也是"单词字符"，
#   "绑定码ABCD2345"这种紧贴中文的写法会匹配失败；改用 (?<![A-Z0-9]) / (?![A-Z0-9])
#   后紧贴中文、紧贴标点、带空格都能识别，而 9 位以上连续字母数字串仍不会误切。
BIND_CODE_RE = re.compile(r'(?<![A-Z0-9])([A-Z2-9]{8})(?![A-Z0-9])')
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
CREATE TABLE IF NOT EXISTS afdian_skus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT NOT NULL DEFAULT '',
    sku_id TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL DEFAULT '',
    name_norm TEXT NOT NULL DEFAULT '',
    dew_amount INTEGER NOT NULL,
    price TEXT NOT NULL DEFAULT '',      -- 归一化价格（'3.00'）：无 SKU 明细订单按总价兜底
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_afdian_skus_plan ON afdian_skus(plan_id);
CREATE INDEX IF NOT EXISTS idx_afdian_skus_name ON afdian_skus(name_norm);
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
    # 增量列（生产库已建表后的迁移）：售卖订单的 SKU 明细存 JSON
    for table, column, decl in (
        ('afdian_orders', 'sku_json', "TEXT NOT NULL DEFAULT ''"),
        ('afdian_skus', 'price', "TEXT NOT NULL DEFAULT ''"),
    ):
        cols = [r[1] for r in conn.execute(f'PRAGMA table_info({table})')]
        if column not in cols:
            conn.execute(f'ALTER TABLE {table} ADD COLUMN {column} {decl}')
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
    text = unicodedata.normalize('NFKC', str(remark or '')).upper()
    match = BIND_CODE_RE.search(text)
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


def _user_id_for_afdian_history(conn, afdian_user_id: str) -> Optional[int]:
    """老客自动认领：按月赞助的自动续费单**不带留言**（拿不到绑定码），但订单里有
    爱发电 user_id——该账号此前有一笔到账记录时，后续订单自动入同一游戏账号。"""
    if not afdian_user_id:
        return None
    row = conn.execute(
        'SELECT game_user_id FROM afdian_orders '
        'WHERE afdian_user_id = ? AND game_user_id IS NOT NULL '
        'ORDER BY credited_at DESC LIMIT 1',
        (str(afdian_user_id),)).fetchone()
    return int(row['game_user_id']) if row else None


def _sku_norm(name: str) -> str:
    return unicodedata.normalize('NFKC', str(name or '')).upper().strip()


def _parse_skus(order: Dict[str, Any]) -> List[Dict[str, Any]]:
    """售卖订单的价格方案明细（webhook 与 query-order 都在 sku_detail 数组里）。
    每项：{sku_id, name, count}；订阅订单通常没有这个字段。"""
    skus: List[Dict[str, Any]] = []
    for entry in (order.get('sku_detail') or []):
        if not isinstance(entry, dict):
            continue
        sku_id = str(entry.get('sku_id') or '').strip()
        name = str(entry.get('name') or '').strip()
        try:
            count = max(1, int(entry.get('count') or 1))
        except (TypeError, ValueError):
            count = 1
        if sku_id or name:
            skus.append({'sku_id': sku_id, 'name': name, 'count': count})
    return skus


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
    skus = _parse_skus(order)
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
                    status, via, order_created_at, received_at, sku_json
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (out_trade_no,
                 str(order.get('user_id') or ''), str(order.get('user_private_id') or ''),
                 plan_id, '', month,
                 str(order.get('total_amount') or '0.00'),
                 str(order.get('show_amount') or '0.00'),
                 remark, code, game_user_id, 0,
                 'pending', via, str(order.get('created_at') or ''), now,
                 json.dumps(skus, separators=(',', ':'), ensure_ascii=False)))
            conn.commit()
        elif str(existing['status']) == 'credited':
            return {'status': 'duplicate', 'out_trade_no': out_trade_no, 'detail': '已入账'}
    return _settle(out_trade_no, via=via)


def _sku_dew(conn, plan_id: str, sku_id: str, name: str) -> Tuple[Optional[int], str]:
    """SKU 级映射：先精确 sku_id，再按名称（NFKC+大写归一）。plan_id='' 为全局条目。
    命中后顺带把 sku_id 记入该条（老客后续订单精确匹配）。返回 (荆露/份, 名称)。"""
    candidates = []
    if sku_id:
        candidates.append({'sku_id': str(sku_id)})
    if name:
        candidates.append({'name_norm': _sku_norm(name)})
    for cond in candidates:
        clause = ' AND '.join([f'{k} = ?' for k in cond])
        row = conn.execute(
            f'SELECT id, dew_amount, name, sku_id FROM afdian_skus '
            f'WHERE active = 1 AND ({clause}) AND (plan_id = ? OR plan_id = "") '
            f'ORDER BY (plan_id = ?) DESC LIMIT 1',
            (*cond.values(), str(plan_id or ''), str(plan_id or ''))).fetchone()
        if row is not None:
            learned = str(row['sku_id'] or '')
            if sku_id and not learned:
                conn.execute('UPDATE afdian_skus SET sku_id = ?, updated_at = ? WHERE id = ?',
                             (str(sku_id), _now_iso(), int(row['id'])))
                conn.commit()
            return int(row['dew_amount'] or 0), str(row['name'] or '')
    return None, ''


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
        if game_user_id is None:
            # 无绑定码（如按月方案的自动续费单）：同一爱发电账号此前到账过则自动认领
            game_user_id = _user_id_for_afdian_history(conn, str(row['afdian_user_id'] or ''))
        dew_per, plan_name = _plan_dew(conn, str(row['plan_id'] or ''))
        month = max(1, int(row['month'] or 1))
        if game_user_id is None:
            conn.execute(
                "UPDATE afdian_orders SET status='unmatched', plan_name=? WHERE out_trade_no=?",
                (plan_name, out_trade_no))
            conn.commit()
            return {'status': 'unmatched', 'out_trade_no': out_trade_no,
                    'detail': f"留言里没有可识别的绑定码（remark={row['remark']!r}）"}
        # 售卖订单（带 sku_detail）只走 SKU 级映射：一个购买项多个价格方案，
        # 各方案荆露数不同，整包映射会错发。未配置的 SKU 安全挂起等补结。
        sku_entries = []
        try:
            sku_entries = json.loads(row['sku_json'] or '[]')
        except Exception:
            sku_entries = []
        label = plan_name or str(row['plan_id'] or '')
        if sku_entries:
            dew = 0
            missing = []
            sku_labels = []
            for entry in sku_entries:
                amount, sku_label = _sku_dew(conn, str(row['plan_id'] or ''),
                                             str(entry.get('sku_id') or ''),
                                             str(entry.get('name') or ''))
                count = max(1, int(entry.get('count') or 1))
                if amount is None:
                    missing.append(str(entry.get('name') or entry.get('sku_id') or '?'))
                    continue
                dew += amount * count
                sku_labels.append(f'{sku_label}×{count}')
            if missing:
                conn.execute(
                    "UPDATE afdian_orders SET status='unmapped', plan_name=?, game_user_id=? "
                    "WHERE out_trade_no=?",
                    (label, int(game_user_id), out_trade_no))
                conn.commit()
                return {'status': 'unmapped', 'out_trade_no': out_trade_no,
                        'detail': f"价格方案未配置荆露（{','.join(missing)}），配置后对账自动补"}
            label = '+'.join(sku_labels) or label
        else:
            # 无 SKU 明细（部分订单/接口不回传 sku_detail）：先按订阅方案映射，
            # 再按订单总价匹配 SKU 价格兜底（售卖项固定价：¥3→800 这类）。
            if not dew_per:
                amount_dew, amount_name = _dew_for_amount(conn, row['total_amount'])
                if amount_dew:
                    dew = amount_dew
                    label = plan_name or amount_name
                    plan_name = amount_name
                else:
                    conn.execute(
                        "UPDATE afdian_orders SET status='unmapped', plan_name=?, game_user_id=? "
                        "WHERE out_trade_no=?",
                        (plan_name, int(game_user_id), out_trade_no))
                    conn.commit()
                    return {'status': 'unmapped', 'out_trade_no': out_trade_no,
                            'detail': f"方案未配置荆露（plan_id={row['plan_id']}，总价 {row['total_amount']} 无匹配档），配置后对账自动补"}
            else:
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
        reason=f'爱发电赞助到账 {out_trade_no}（{label}）',
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
    """兑换页展示的档位：SKU（售卖项价格方案，按份）+ 订阅方案（按月）合并，
    各带 kind 字段（'sku' / 'plan'）。此前只读 afdian_plans，六个真实档位
    （配在 afdian_skus）在页面上看不到（反馈：可见档位只有 Y1）。"""
    out: List[Dict[str, Any]] = []
    with db.get_db_connection() as conn:
        ensure_schema(conn)
        for row in conn.execute(
                'SELECT name, sku_id, dew_amount, price FROM afdian_skus '
                'WHERE active = 1 ORDER BY dew_amount ASC').fetchall():
            out.append({'plan_id': str(row['sku_id'] or ''),
                        'name': str(row['name'] or ''),
                        'dew_amount': int(row['dew_amount'] or 0),
                        'price': _price_key(row['price']),
                        'kind': 'sku'})
        for row in conn.execute(
                'SELECT plan_id, name, dew_amount FROM afdian_plans '
                'WHERE active = 1 ORDER BY dew_amount ASC').fetchall():
            out.append({'plan_id': str(row['plan_id'] or ''),
                        'name': str(row['name'] or row['plan_id'] or ''),
                        'dew_amount': int(row['dew_amount'] or 0),
                        'price': '',
                        'kind': 'plan'})
    return out


def _price_key(value: Any) -> str:
    """价格归一成 '3.00' 形式，写库与匹配都用同一口径。"""
    try:
        return '%.2f' % float(str(value or '').strip().replace(',', '.'))
    except (TypeError, ValueError):
        return ''


def _dew_for_amount(conn, amount: Any) -> Tuple[Optional[int], str]:
    """无 SKU 明细订单的兜底：按订单总价精确匹配 SKU 档价格（¥3→800 这类
    固定价售卖项）。匹配不上返回 (None, '')，单子安全挂起等人工。"""
    key = _price_key(amount)
    if not key:
        return None, ''
    row = conn.execute(
        "SELECT dew_amount, name, price FROM afdian_skus "
        "WHERE active = 1 AND price <> ''").fetchall()
    for candidate in row:
        if _price_key(candidate['price']) == key:
            return int(candidate['dew_amount'] or 0), str(candidate['name'] or '')
    return None, ''


def admin_set_sku(dew_amount: int, name: str, plan_id: str = '', sku_id: str = '',
                  price: str = '') -> Dict[str, Any]:
    """价格方案（SKU）级映射：按名称（归一）或 sku_id 命中；plan_id 空 = 全局。
    price 为该档售价（'3' 或 '3.00'），供无 SKU 明细订单按总价兜底；不传则保留原值。"""
    dew = max(0, int(dew_amount or 0))
    name = str(name or '').strip()
    name_norm = _sku_norm(name)
    sku_id = str(sku_id or '').strip()
    plan_id = str(plan_id or '').strip()
    price_key = _price_key(price)
    if dew <= 0 or not (name_norm or sku_id):
        return {'ok': False, 'error': '需要正数荆露与（名称或 sku_id）至少其一'}
    now = _now_iso()
    with db.get_db_connection() as conn:
        ensure_schema(conn)
        if sku_id:
            existing = conn.execute(
                'SELECT id FROM afdian_skus WHERE sku_id = ? AND (plan_id = ? OR plan_id = "")',
                (sku_id, plan_id)).fetchone()
        else:
            existing = conn.execute(
                'SELECT id FROM afdian_skus WHERE name_norm = ? AND (plan_id = ? OR plan_id = "")',
                (name_norm, plan_id)).fetchone()
        if existing is not None:
            conn.execute(
                'UPDATE afdian_skus SET dew_amount = ?, name = ?, name_norm = ?, '
                'sku_id = CASE WHEN ? <> "" THEN ? ELSE sku_id END, '
                'price = CASE WHEN ? <> "" THEN ? ELSE price END, '
                'updated_at = ? WHERE id = ?',
                (dew, name, name_norm, sku_id, sku_id, price_key, price_key, now, int(existing['id'])))
        else:
            conn.execute(
                '''INSERT INTO afdian_skus (plan_id, sku_id, name, name_norm, dew_amount,
                                            price, active, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,1,?,?)''',
                (plan_id, sku_id, name, name_norm, dew, price_key, now, now))
        conn.commit()
    requery_recent(pages=1)
    return {'ok': True, 'name': name, 'dew_amount': dew, 'price': price_key}


def admin_list_skus() -> List[Dict[str, Any]]:
    with db.get_db_connection() as conn:
        ensure_schema(conn)
        rows = conn.execute(
            'SELECT plan_id, sku_id, name, dew_amount, price, active FROM afdian_skus '
            'ORDER BY dew_amount ASC').fetchall()
        return [dict(row) for row in rows]


def admin_set_plan(plan_id: str, dew_amount: int, name: str = '') -> Dict[str, Any]:
    """订阅方案映射；荆露数 0 = 停用该方案（active=0，订单走别的映射或挂起）。"""
    plan_id = str(plan_id or '').strip()
    dew = max(0, int(dew_amount or 0))
    if not plan_id:
        return {'ok': False, 'error': '缺少 plan_id'}
    now = _now_iso()
    active = 1 if dew > 0 else 0
    with db.get_db_connection() as conn:
        ensure_schema(conn)
        conn.execute(
            '''INSERT INTO afdian_plans (plan_id, name, dew_amount, active, created_at, updated_at)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(plan_id) DO UPDATE SET
                 name=excluded.name, dew_amount=excluded.dew_amount,
                 active=excluded.active, updated_at=excluded.updated_at''',
            (plan_id, str(name or ''), dew, active, now, now))
        conn.commit()
    # 配置/修改映射后顺手把待补的 unmapped 单结掉（未配置 API 时只是拉不到，无副作用）
    if active:
        requery_recent(pages=2)
    return {'ok': True, 'plan_id': plan_id, 'dew_amount': dew, 'active': active}


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
