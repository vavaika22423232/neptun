"""
Feedback / corrections system.

- Stores admin corrections in SQLite
- Tracks channel → oblast priors
- Periodic learning: generates aliases and blacklist from patterns
"""

import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

log = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'settlements.db')


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ── Corrections ──────────────────────────────────────────────────────────────

def save_correction(
    event_id: str,
    place_name: str,
    channel: str,
    predicted_lat: float,
    predicted_lng: float,
    predicted_oblast: str,
    correct_lat: float,
    correct_lng: float,
    correct_oblast: str,
    reason: str = '',
) -> None:
    """Save a human correction for later learning."""
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT INTO corrections
               (event_id, place_name, channel, predicted_lat, predicted_lng, predicted_oblast,
                correct_lat, correct_lng, correct_oblast, reason, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (event_id, place_name, channel,
             predicted_lat, predicted_lng, predicted_oblast,
             correct_lat, correct_lng, correct_oblast,
             reason, datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


# ── Channel Priors ───────────────────────────────────────────────────────────

def update_channel_prior(channel: str, oblast: str) -> None:
    """Increment channel → oblast count."""
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT INTO channel_priors (channel, oblast, count, last_seen)
               VALUES (?, ?, 1, ?)
               ON CONFLICT(channel, oblast)
               DO UPDATE SET count = count + 1, last_seen = ?""",
            (channel, oblast, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_channel_priors(channel: str) -> dict:
    """Get {oblast: count} for a channel."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT oblast, count FROM channel_priors WHERE channel = ?",
            (channel,)
        ).fetchall()
        return {r['oblast']: r['count'] for r in rows}
    finally:
        conn.close()


# ── Learning loop ────────────────────────────────────────────────────────────

def learn_from_corrections() -> dict:
    """
    Analyze corrections and auto-generate:
      - Aliases (if same name corrected 3+ times to same oblast)
      - Blacklist entries (if geocoder consistently wrong)
    
    Returns stats dict.
    """
    conn = _get_conn()
    stats = {'new_aliases': 0, 'new_blacklist': 0}

    try:
        # 1. Find place names corrected 3+ times to the same oblast
        rows = conn.execute(
            """SELECT place_name, correct_oblast, COUNT(*) as cnt
               FROM corrections
               WHERE created_at > ?
               GROUP BY place_name, correct_oblast
               HAVING cnt >= 3""",
            ((datetime.utcnow() - timedelta(days=30)).isoformat(),)
        ).fetchall()

        for row in rows:
            place_name = row['place_name']
            correct_oblast = row['correct_oblast']

            # Check if we already have a matching place in that oblast
            existing = conn.execute(
                "SELECT id FROM places WHERE name_lower = ? AND oblast = ? LIMIT 1",
                (place_name.lower(), correct_oblast)
            ).fetchone()

            if not existing:
                # Check if the place exists in wrong oblast → add alias pointing to correct one
                correct_place = conn.execute(
                    "SELECT id FROM places WHERE oblast = ? AND name_lower LIKE ? LIMIT 1",
                    (correct_oblast, place_name.lower()[:3] + '%')
                ).fetchone()

                if correct_place:
                    # Add alias
                    conn.execute(
                        "INSERT OR IGNORE INTO aliases (alias, canonical_id, priority) VALUES (?, ?, 10)",
                        (place_name.lower(), correct_place['id'])
                    )
                    stats['new_aliases'] += 1
                    log.info(f"[LEARN] Added alias: {place_name} -> place#{correct_place['id']} ({correct_oblast})")

        # 2. Find geocoder patterns that consistently fail
        bad_patterns = conn.execute(
            """SELECT place_name, predicted_oblast, COUNT(*) as cnt
               FROM corrections
               WHERE predicted_oblast != correct_oblast
               AND created_at > ?
               GROUP BY place_name, predicted_oblast
               HAVING cnt >= 3""",
            ((datetime.utcnow() - timedelta(days=30)).isoformat(),)
        ).fetchall()

        for row in bad_patterns:
            # Blacklist: don't pick this place_name in predicted_oblast
            conn.execute(
                "INSERT OR IGNORE INTO blacklist (place_name, oblast, reason) VALUES (?, ?, ?)",
                (row['place_name'].lower(), row['predicted_oblast'],
                 f"Auto-learned: wrong {row['cnt']} times")
            )
            stats['new_blacklist'] += 1
            log.info(f"[LEARN] Blacklisted: {row['place_name']} in {row['predicted_oblast']}")

        # 3. Refresh channel priors from recent successful events
        # (This happens implicitly via update_channel_prior during normal processing)

        conn.commit()
    except Exception as e:
        log.error(f"Learning error: {e}", exc_info=True)
    finally:
        conn.close()

    log.info(f"[LEARN] Results: {stats}")
    return stats


def get_correction_stats() -> dict:
    """Get summary stats for admin panel."""
    conn = _get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM corrections").fetchone()[0]
        recent = conn.execute(
            "SELECT COUNT(*) FROM corrections WHERE created_at > ?",
            ((datetime.utcnow() - timedelta(days=7)).isoformat(),)
        ).fetchone()[0]

        # Top problem places
        top_problems = conn.execute(
            """SELECT place_name, COUNT(*) as cnt
               FROM corrections
               GROUP BY place_name
               ORDER BY cnt DESC
               LIMIT 10"""
        ).fetchall()

        return {
            'total_corrections': total,
            'recent_7d': recent,
            'top_problems': [{'name': r['place_name'], 'count': r['cnt']} for r in top_problems],
        }
    finally:
        conn.close()
