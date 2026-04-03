import sqlite3
import json
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "market_cache.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_cache (
                cache_key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ttl_hours INTEGER DEFAULT 168
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idea TEXT NOT NULL,
                country TEXT NOT NULL,
                city TEXT NOT NULL DEFAULT '',
                timeframe TEXT NOT NULL,
                score INTEGER,
                verdict TEXT,
                result_json TEXT,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(idea, country, city, timeframe)
            )
        """)
        existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(analysis_history)").fetchall()]
        if "city" not in existing_cols:
            conn.execute("ALTER TABLE analysis_history ADD COLUMN city TEXT NOT NULL DEFAULT ''")
        conn.commit()


def get_cached(key: str):
    init_db()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT value, created_at, ttl_hours FROM api_cache WHERE cache_key = ?",
            (key,)
        ).fetchone()

    if not row:
        return None

    value, created_at, ttl_hours = row
    try:
        created_dt = datetime.fromisoformat(created_at)
    except ValueError:
        return None

    if datetime.now() > created_dt + timedelta(hours=ttl_hours):
        return None

    return json.loads(value)


def set_cached(key: str, value: dict, ttl_hours: int = 168):
    init_db()
    with _get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO api_cache
               (cache_key, value, created_at, ttl_hours)
               VALUES (?, ?, ?, ?)""",
            (key, json.dumps(value, ensure_ascii=False),
             datetime.now().isoformat(), ttl_hours)
        )
        conn.commit()


def save_analysis(idea: str, country: str, city: str, timeframe: str,
                  score: int, verdict: str, result_json: str):
    init_db()
    with _get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO analysis_history
            (idea, country, city, timeframe, score, verdict, result_json, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (idea.strip().lower(), country.strip().lower(), city.strip().lower(),
              timeframe, score, verdict, result_json, datetime.now().isoformat()))
        conn.commit()


def get_history(limit: int = 20):
    init_db()
    with _get_conn() as conn:
        rows = conn.execute(
            """SELECT id, idea, country, city, timeframe, score, verdict, result_json, analyzed_at
               FROM analysis_history
               ORDER BY analyzed_at DESC
               LIMIT ?""",
            (limit,)
        ).fetchall()

    columns = ["id", "idea", "country", "city", "timeframe",
               "score", "verdict", "result_json", "analyzed_at"]
    return [dict(zip(columns, row)) for row in rows]


def clear_api_cache():
    init_db()
    with _get_conn() as conn:
        conn.execute("DELETE FROM api_cache")
        conn.commit()


def clear_all():
    with _get_conn() as conn:
        conn.execute("DROP TABLE IF EXISTS api_cache")
        conn.execute("DROP TABLE IF EXISTS analysis_history")
        conn.commit()
