import json
from datetime import datetime, timezone

import db


NOW = datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc)


def _insert_match(conn, match_id, mode, rounds, ended_at, event_ids, valid=True):
    conn.execute(
        """
        INSERT INTO matches(
            id, mode, started_at, ended_at, rounds, result, summary_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            match_id,
            mode,
            ended_at,
            ended_at,
            rounds,
            'win',
            json.dumps({
                'valid_for_stats': bool(valid),
                'opening_event_ids_by_player': event_ids,
            }),
        ),
    )


def test_average_round_stats_total_and_recent_split(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'stats.sqlite3'))
    db.init_db()
    monkeypatch.setattr(db, 'utc_now_dt', lambda: NOW)
    with db.get_db_connection() as conn:
        _insert_match(conn, 1, '2v2', 10, '2026-09-06T10:00:00Z', ['7', '8'])
        _insert_match(conn, 2, '1v1', 6, '2026-09-05T10:00:00Z', ['1', '2'])
        _insert_match(conn, 3, '1v1', 20, '2026-08-20T10:00:00Z', ['9'], valid=False)
        conn.commit()

    total = db.list_average_round_stats(scope='total')
    assert total['total']['observations'] == 4
    assert total['total']['rounds_sum'] == 32
    assert total['total']['avg_rounds'] == 8.0
    assert {item['event_id']: item['avg_rounds'] for item in total['items']} == {
        '7': 10.0,
        '8': 10.0,
        '1': 6.0,
        '2': 6.0,
    }

    recent = db.list_average_round_stats(scope='recent', recent_days=7)
    assert recent['total']['observations'] == 4
    assert recent['total']['rounds_sum'] == 32

    old_only = db.list_average_round_stats(scope='recent', recent_days=1)
    assert old_only['total']['observations'] == 2
    assert old_only['total']['rounds_sum'] == 20
