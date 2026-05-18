"""
SQLite-backed gazetteer for Ukrainian settlements.

Provides find_candidates() which returns ALL matching settlements
for a given name, ordered by relevance (exact > alias > fuzzy).
"""

import logging
import os
import re
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'settlements.db')

# Live regional Telegram channels often use tiny villages / resort names that are
# missing from the bundled seed DB. Keep a narrow curated layer for observed
# tracker vocabulary so parsing does not depend on an external geocoder.
_MANUAL_PLACES: dict[str, tuple[str, float, float, str, Optional[str], str, int]] = {
    'есмань': ('Есмань', 51.7672310, 34.0634500, 'Сумська область', 'Шосткинський', 'селище', 1500),
    'середина-буда': ('Середина-Буда', 52.1886906, 34.0306022, 'Сумська область', 'Шосткинський', 'місто', 7000),
    'середина буда': ('Середина-Буда', 52.1886906, 34.0306022, 'Сумська область', 'Шосткинський', 'місто', 7000),
    'береза': ('Береза', 51.7311446, 33.8753315, 'Сумська область', 'Шосткинський', 'село', 1000),
    'санжійка': ('Санжійка', 46.2352710, 30.6072200, 'Одеська область', 'Одеський', 'село', 800),
    'грибівка': ('Грибівка', 46.2085082, 30.5645436, 'Одеська область', 'Одеський', 'село', 1000),
    'рибаківка': ('Рибаківка', 46.6195586, 31.3511191, 'Миколаївська область', 'Миколаївський', 'село', 1600),
    'морське': ('Морське', 46.6168020, 31.2660580, 'Миколаївська область', 'Миколаївський', 'село', 700),
    'залізний порт': ('Залізний Порт', 46.1234725, 32.2955068, 'Херсонська область', 'Скадовський', 'село', 1500),
    'тендрівська коса': ('Тендрівська коса', 46.2530, 31.6900, 'Херсонська область', None, 'locality', 0),
    'обознівка': ('Обознівка', 49.2881154, 33.4296800, 'Полтавська область', 'Кременчуцький', 'село', 1000),
    'обозновка': ('Обознівка', 49.2881154, 33.4296800, 'Полтавська область', 'Кременчуцький', 'село', 1000),
    'пустовійтове': ('Пустовійтове', 49.3365978, 33.3800289, 'Полтавська область', 'Кременчуцький', 'село', 1000),
    'пустовойтовое': ('Пустовійтове', 49.3365978, 33.3800289, 'Полтавська область', 'Кременчуцький', 'село', 1000),
    'потоки': ('Потоки', 49.1038250, 33.5782649, 'Полтавська область', 'Кременчуцький', 'село', 3000),
    'поток': ('Потоки', 49.1038250, 33.5782649, 'Полтавська область', 'Кременчуцький', 'село', 3000),
    'кияшки': ('Кияшки', 49.1274109, 33.6182189, 'Полтавська область', 'Кременчуцький', 'село', 1000),
    'кияшек': ('Кияшки', 49.1274109, 33.6182189, 'Полтавська область', 'Кременчуцький', 'село', 1000),
    'царичанка': ('Царичанка', 48.9434000, 34.4898600, 'Дніпропетровська область', 'Дніпровський', 'селище', 7000),
    'царичанки': ('Царичанка', 48.9434000, 34.4898600, 'Дніпропетровська область', 'Дніпровський', 'селище', 7000),
    'славгород': ('Славгород', 48.1126480, 35.5144248, 'Дніпропетровська область', 'Синельниківський', 'селище', 2000),
    'синельникове': ('Синельникове', 48.3269304, 35.5246984, 'Дніпропетровська область', 'Синельниківський', 'місто', 30000),
    'велика бурімка': ('Велика Бурімка', 49.6077215, 32.6401483, 'Черкаська область', 'Золотоніський', 'село', 1000),
    'новоселиця': ('Новоселиця', 49.6512589, 32.5393326, 'Черкаська область', 'Золотоніський', 'село', 1000),
    'лящівка': ('Лящівка', 49.5413873, 32.6711380, 'Черкаська область', 'Золотоніський', 'село', 800),
}

# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class LocationCandidate:
    name: str
    lat: float
    lng: float
    oblast: Optional[str] = None
    raion: Optional[str] = None
    source: str = "gazetteer"
    score: float = 0.0
    reasons: list = field(default_factory=list)
    place_type: Optional[str] = None
    population: int = 0

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'lat': self.lat,
            'lng': self.lng,
            'oblast': self.oblast,
            'raion': self.raion,
            'source': self.source,
            'score': round(self.score, 2),
            'reasons': self.reasons[:5],  # keep top 5 reasons for logging
        }


@dataclass
class ResolvedLocation:
    lat: float
    lng: float
    oblast: str
    raion: Optional[str]
    place_name: str
    confidence: float  # 0.0 - 1.0
    status: str  # "ok" / "ambiguous" / "low_confidence" / "rejected"
    chosen_from: list  # list of LocationCandidate
    is_predictive: bool = False  # True if resolved solely from target_city

    def to_dict(self) -> dict:
        return {
            'lat': self.lat,
            'lng': self.lng,
            'oblast': self.oblast,
            'raion': self.raion,
            'place_name': self.place_name,
            'confidence': round(self.confidence, 3),
            'status': self.status,
            'is_predictive': self.is_predictive,
            'candidates': [c.to_dict() for c in self.chosen_from[:3]],
        }


# ── Connection pool ──────────────────────────────────────────────────────────

_conn: Optional[sqlite3.Connection] = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        if not os.path.exists(DB_PATH):
            log.warning(f"Gazetteer DB not found at {DB_PATH}, building...")
            from geo.data.build_gazetteer import build_db
            build_db(DB_PATH)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


# ── Ukrainian declension helpers ─────────────────────────────────────────────

# Common Ukrainian suffixes to strip for base-form matching
_SUFFIXES_RE = re.compile(
    r'(ою|ам|ів|ом|ей|ів|ці|ку|ка|ки|ці|ку|ий|ій|ої|ім|ій|ом|ів|ин|ів'
    r'|а|у|і|е|и|о|ю|ь)$',
    re.IGNORECASE
)


def _stem(name: str) -> str:
    """Rough Ukrainian stemming: strip common suffixes."""
    s = name.lower().strip()
    if len(s) > 3:
        s = _SUFFIXES_RE.sub('', s)
    return s


def _common_prefix_len(a: str, b: str) -> int:
    count = 0
    for ca, cb in zip(a.lower().strip(), b.lower().strip()):
        if ca != cb:
            break
        count += 1
    return count


def _safe_broad_oblast_match(query: str, candidate_name: str) -> bool:
    """Prevent oblast prefix fallback from turning arbitrary prose into a place.

    The broad fallback exists for declined forms like "Харкову" → "Харків", but
    a 3-letter prefix alone also maps words like "через" → "Черкаська Лозова".
    Require a longer shared prefix than the SQL lookup itself.
    """
    q = query.lower().strip()
    c = candidate_name.lower().strip()
    if len(q) < 5 or len(c) < 4:
        return False
    if q == c or q in c or c in q:
        return True
    return _common_prefix_len(q, c) >= 4


# ── Public API ───────────────────────────────────────────────────────────────

def find_candidates(
    name: str,
    oblast_hint: Optional[str] = None,
    limit: int = 20,
) -> list[LocationCandidate]:
    """
    Return ALL matching settlements for `name`, not just the first.
    
    Search order: exact match > alias match > stem/fuzzy match.
    If oblast_hint is provided, results in that oblast are boosted.
    """
    if not name or len(name) < 2:
        return []

    conn = _get_conn()
    name_lower = name.lower().strip()
    candidates: list[LocationCandidate] = []
    seen_ids: set[int] = set()

    manual = _MANUAL_PLACES.get(name_lower)
    if manual and (not oblast_hint or manual[3] == oblast_hint):
        m_name, m_lat, m_lng, m_oblast, m_raion, m_type, m_population = manual
        candidates.append(LocationCandidate(
            name=m_name,
            lat=m_lat,
            lng=m_lng,
            oblast=m_oblast,
            raion=m_raion,
            source='manual_regional_channel',
            place_type=m_type,
            population=m_population,
        ))

    def _add(row: sqlite3.Row, source_tag: str):
        pid = row['id']
        if pid in seen_ids:
            return
        seen_ids.add(pid)
        candidates.append(LocationCandidate(
            name=row['name'],
            lat=row['lat'],
            lng=row['lng'],
            oblast=row['oblast'],
            raion=row['raion'],
            source=source_tag,
            place_type=row['place_type'],
            population=row['population'] or 0,
        ))

    # 1. Exact match on name_lower
    rows = conn.execute(
        "SELECT * FROM places WHERE name_lower = ? LIMIT ?",
        (name_lower, limit)
    ).fetchall()
    for r in rows:
        _add(r, 'gazetteer_exact')

    # 2. Alias match
    alias_rows = conn.execute(
        """SELECT p.* FROM aliases a
           JOIN places p ON a.canonical_id = p.id
           WHERE a.alias = ?
           ORDER BY a.priority DESC
           LIMIT ?""",
        (name_lower, limit)
    ).fetchall()
    for r in alias_rows:
        _add(r, 'gazetteer_alias')

    # 3. Stem/prefix match (if few or no results yet)
    if len(candidates) < 3:
        stem = _stem(name_lower)
        if len(stem) >= 3:
            stem_rows = conn.execute(
                "SELECT * FROM places WHERE name_lower LIKE ? LIMIT ?",
                (stem + '%', limit)
            ).fetchall()
            for r in stem_rows:
                _add(r, 'gazetteer_stem')

    # 3b. Multi-word declension: stem each word and try LIKE match
    #     "Руську Лозову" → stems ["руськ", "лозов"] → LIKE 'руськ%лозов%'
    if len(candidates) < 3 and ' ' in name_lower:
        words = name_lower.split()
        stems = [_stem(w) for w in words if len(w) > 2]
        if len(stems) >= 2 and all(len(s) >= 3 for s in stems):
            pattern = '%'.join(s + '%' for s in stems)
            multi_rows = conn.execute(
                "SELECT * FROM places WHERE name_lower LIKE ? LIMIT ?",
                (pattern, limit)
            ).fetchall()
            for r in multi_rows:
                _add(r, 'gazetteer_stem_multi')

    # 3c. Stem-based alias search (handles declined forms registered as aliases)
    if len(candidates) < 3:
        stem = _stem(name_lower)
        if len(stem) >= 3:
            alias_stem_rows = conn.execute(
                """SELECT p.* FROM aliases a
                   JOIN places p ON a.canonical_id = p.id
                   WHERE a.alias LIKE ?
                   ORDER BY a.priority DESC
                   LIMIT ?""",
                (stem + '%', limit)
            ).fetchall()
            for r in alias_stem_rows:
                _add(r, 'gazetteer_alias_stem')

    # 4. If oblast_hint, also search within that oblast (broader)
    if oblast_hint and len(candidates) < 3:
        oblast_rows = conn.execute(
            "SELECT * FROM places WHERE oblast = ? AND name_lower LIKE ? LIMIT ?",
            (oblast_hint, name_lower[:3] + '%', limit)
        ).fetchall()
        for r in oblast_rows:
            if not _safe_broad_oblast_match(name_lower, r['name_lower']):
                continue
            _add(r, 'gazetteer_oblast_search')

    # Підказка області: однойменні НП в різних областях — спочатку ті, що в hint
    if oblast_hint and len(candidates) > 1:
        oh = oblast_hint.strip()

        def _oblast_sort_key(c: LocationCandidate) -> tuple:
            in_hint = 0 if (c.oblast or '').strip() == oh else 1
            return (in_hint, -(c.population or 0))

        candidates.sort(key=_oblast_sort_key)

    return candidates[:limit]


def count_by_name(name: str) -> int:
    """How many settlements in Ukraine have this name?"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT COUNT(*) FROM places WHERE name_lower = ?",
        (name.lower().strip(),)
    ).fetchone()
    return row[0] if row else 0


def is_blacklisted(name: str, oblast: Optional[str] = None) -> bool:
    """Check if a place name is blacklisted (known bad match)."""
    conn = _get_conn()
    if oblast:
        row = conn.execute(
            "SELECT 1 FROM blacklist WHERE place_name = ? AND (oblast = ? OR oblast IS NULL) LIMIT 1",
            (name.lower(), oblast)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT 1 FROM blacklist WHERE place_name = ? LIMIT 1",
            (name.lower(),)
        ).fetchone()
    return row is not None


# ── Self-learning: auto-insert from external geocoders ───────────────────────

_learned_names: set[str] = set()  # Prevent duplicate inserts per session


def learn_from_external(
    name: str,
    lat: float,
    lng: float,
    oblast: Optional[str] = None,
    source_tag: str = 'nominatim',
) -> bool:
    """
    Auto-add a place to the gazetteer when an external geocoder resolves it.
    Returns True if inserted, False if already known.
    
    This creates a feedback loop: Nominatim resolves once → gazetteer hits instantly next time.
    """
    if not name or len(name) < 2:
        return False

    name_lower = name.lower().strip()

    # Skip if already learned this session
    if name_lower in _learned_names:
        return False

    conn = _get_conn()

    # Check if already exists in gazetteer
    existing = conn.execute(
        "SELECT id FROM places WHERE name_lower = ? AND ABS(lat - ?) < 0.1 AND ABS(lng - ?) < 0.1 LIMIT 1",
        (name_lower, lat, lng)
    ).fetchone()
    if existing:
        _learned_names.add(name_lower)
        return False

    # Insert new place
    try:
        conn.execute(
            """INSERT INTO places (name, name_lower, oblast, raion, lat, lng, place_type, population)
               VALUES (?, ?, ?, NULL, ?, ?, ?, 0)""",
            (name, name_lower, oblast or '', lat, lng, f'learned_{source_tag}')
        )
        conn.commit()
        _learned_names.add(name_lower)
        log.info(f"[GAZETTEER] Learned new place: {name} ({lat:.4f}, {lng:.4f}) oblast={oblast} from {source_tag}")
        return True
    except Exception as e:
        log.warning(f"[GAZETTEER] Failed to learn {name}: {e}")
        return False


def learn_alias(alias: str, canonical_name: str) -> bool:
    """
    Add an alias for an existing place (e.g. accusative form → nominative).
    """
    if not alias or not canonical_name:
        return False

    alias_lower = alias.lower().strip()
    conn = _get_conn()

    # Find the canonical place
    place = conn.execute(
        "SELECT id FROM places WHERE name_lower = ? LIMIT 1",
        (canonical_name.lower().strip(),)
    ).fetchone()
    if not place:
        return False

    # Check if alias already exists
    existing = conn.execute(
        "SELECT id FROM aliases WHERE alias = ? AND canonical_id = ? LIMIT 1",
        (alias_lower, place['id'])
    ).fetchone()
    if existing:
        return False

    try:
        conn.execute(
            "INSERT INTO aliases (alias, canonical_id, priority) VALUES (?, ?, 5)",
            (alias_lower, place['id'])
        )
        conn.commit()
        log.info(f"[GAZETTEER] Learned alias: '{alias}' -> '{canonical_name}' (id={place['id']})")
        return True
    except Exception as e:
        log.warning(f"[GAZETTEER] Failed to add alias {alias}: {e}")
        return False
