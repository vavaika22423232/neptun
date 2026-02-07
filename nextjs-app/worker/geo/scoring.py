"""
Weighted scoring for location candidates.

Each candidate gets a score based on multiple factors:
  +5 oblast polygon match
  +3 oblast bbox match / channel prior
  +2 raion match / direction match / near previous event
  +1 rare name / population bonus
  -2 common name
  -5 outside expected oblast
  -999 blacklisted
"""

import logging
import math
from typing import Optional

from geo.gazetteer import LocationCandidate, count_by_name, is_blacklisted

log = logging.getLogger(__name__)


# ── Haversine distance ───────────────────────────────────────────────────────

def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in km between two points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Scoring ──────────────────────────────────────────────────────────────────

def score_candidate(
    candidate: LocationCandidate,
    entities: dict,
    channel: Optional[str] = None,
    prev_events: Optional[list] = None,
    channel_priors: Optional[dict] = None,
) -> tuple[float, list[str]]:
    """
    Compute score for a candidate.
    
    Args:
        candidate: The location candidate
        entities: Parsed entities from text {'place_name', 'oblast', 'direction', ...}
        channel: Telegram channel name
        prev_events: Recent events for proximity check
        channel_priors: {oblast: count} from feedback
    
    Returns:
        (score, reasons)
    """
    score = 0.0
    reasons: list[str] = []

    # ── 1. Blacklist check (instant reject) ──
    if is_blacklisted(candidate.name, candidate.oblast):
        return -999.0, ["-999 blacklisted"]

    # ── 2. Source quality bonus ──
    if candidate.source == 'gazetteer_exact':
        score += 2.0
        reasons.append("+2 exact gazetteer match")
    elif candidate.source == 'gazetteer_alias':
        score += 1.0
        reasons.append("+1 alias match")
    elif candidate.source == 'gazetteer_stem':
        score += 0.5
        reasons.append("+0.5 stem match")

    # ── 3. Name uniqueness ──
    name_count = count_by_name(candidate.name)
    if name_count == 1:
        score += 1.0
        reasons.append("+1 unique name in Ukraine")
    elif name_count >= 3:
        score -= 2.0
        reasons.append(f"-2 common name ({name_count} settlements)")

    # ── 4. Population bonus (big cities are more likely targets) ──
    if candidate.population >= 100000:
        score += 2.0
        reasons.append("+2 major city (100k+)")
    elif candidate.population >= 30000:
        score += 1.0
        reasons.append("+1 city (30k+)")

    # ── 5. Channel prior ──
    if channel_priors and candidate.oblast:
        prior_count = channel_priors.get(candidate.oblast, 0)
        if prior_count >= 10:
            score += 3.0
            reasons.append(f"+3 channel often reports {candidate.oblast}")
        elif prior_count >= 3:
            score += 1.5
            reasons.append(f"+1.5 channel sometimes reports {candidate.oblast}")

    # ── 6. Raion match ──
    text_raion = entities.get('raion', '')
    if text_raion and candidate.raion:
        if text_raion.lower() in candidate.raion.lower() or candidate.raion.lower() in text_raion.lower():
            score += 2.0
            reasons.append("+2 raion match")

    # ── 7. Direction / "near" check ──
    direction = entities.get('direction', '')
    if direction and candidate.name:
        # If text says "напрямок на X" and X matches candidate → bonus
        if candidate.name.lower() in direction.lower():
            score += 2.0
            reasons.append("+2 direction target match")

    # ── 8. Proximity to previous events ──
    if prev_events:
        for evt in prev_events[-5:]:  # check last 5
            evt_lat = evt.get('lat')
            evt_lng = evt.get('lng')
            if evt_lat and evt_lng:
                dist = haversine_km(candidate.lat, candidate.lng, evt_lat, evt_lng)
                if dist < 100:
                    score += 2.0
                    reasons.append(f"+2 within {dist:.0f}km of recent event")
                    break  # one bonus is enough
                elif dist > 500:
                    score -= 1.0
                    reasons.append(f"-1 {dist:.0f}km from recent events")
                    break

    return score, reasons
