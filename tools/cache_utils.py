"""
Shared caching layer for GoldBot's tool functions.
Caches fetched factor data (not LLM scores) per unique call signature,
with a configurable TTL. This makes repeat analyses within the TTL
window reproducible and fast, while still refreshing naturally once
the cache expires.
"""

import sqlite3
import os
import time
import hashlib
import functools


def _get_cache_db_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'factor_cache.db')


def _init_cache_table():
    conn = sqlite3.connect(_get_cache_db_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS factor_cache (
            cache_key TEXT PRIMARY KEY,
            value TEXT,
            cached_at REAL
        )
    """)
    conn.commit()
    conn.close()


_init_cache_table()


# Strings that indicate a failed fetch — we skip caching these so a transient
# rate limit or API hiccup doesn't poison the cache for 24 hours.
_ERROR_MARKERS = (
    "Data unavailable", "Too Many Requests", "Rate limited", "Cannot specify",
    "N/A for ", "Not enough", "out-of-bounds", "Data temporarily unavailable",
    "did not return",
)


def _looks_like_error(value: str) -> bool:
    if not isinstance(value, str) or not value:
        return True
    return any(m in value for m in _ERROR_MARKERS)


def cached_tool(ttl_seconds):
    """
    Decorator for caching a tool function's return value.
    Apply UNDER @tool (i.e. @tool goes on top, @cached_tool goes below).

    Error responses are NOT cached — previously a single rate-limit error
    poisoned the cache for 24h and users kept seeing the same stale error.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key_raw = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            cache_key = hashlib.md5(key_raw.encode()).hexdigest()

            conn = sqlite3.connect(_get_cache_db_path())
            cursor = conn.execute(
                "SELECT value, cached_at FROM factor_cache WHERE cache_key = ?",
                (cache_key,)
            )
            row = cursor.fetchone()
            now = time.time()

            # Serve from cache ONLY if the cached value isn't an error string
            if row and (now - row[1]) < ttl_seconds and not _looks_like_error(row[0]):
                conn.close()
                return row[0]

            result = func(*args, **kwargs)

            if _looks_like_error(result):
                conn.execute("DELETE FROM factor_cache WHERE cache_key = ?", (cache_key,))
                conn.commit()
                conn.close()
                return result

            conn.execute(
                "INSERT OR REPLACE INTO factor_cache (cache_key, value, cached_at) VALUES (?, ?, ?)",
                (cache_key, result, now)
            )
            conn.commit()
            conn.close()
            return result

        return wrapper
    return decorator


def purge_error_cache():
    """Wipe any cached error rows left over from before error-skipping existed."""
    try:
        conn = sqlite3.connect(_get_cache_db_path())
        cursor = conn.execute("SELECT cache_key, value FROM factor_cache")
        bad = [row[0] for row in cursor.fetchall() if _looks_like_error(row[1])]
        for key in bad:
            conn.execute("DELETE FROM factor_cache WHERE cache_key = ?", (key,))
        conn.commit()
        conn.close()
        return len(bad)
    except Exception:
        return 0


# Standard TTLs used across GoldBot's tools
TTL_SLOW = 86400   # 24 hours — Real Yields, Fed Rate, 2Y Treasury, Inflation Exp., USD Index, Central Bank Buying
TTL_FAST = 900      # 15 minutes — VIX, S&P 500 Growth, Geopolitical Risk