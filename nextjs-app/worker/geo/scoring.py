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
from core.threat_families import threat_family

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
    elif 'geocoder_' in candidate.source:
        score += 1.5
        reasons.append("+1.5 external oracle geocoder")

    # ── 3. Name uniqueness ──
    name_count = count_by_name(candidate.name)
    if name_count == 1:
        score += 1.0
        reasons.append("+1 unique name in Ukraine")
    elif name_count >= 5:
        score -= 2.0
        reasons.append(f"-2 very common name ({name_count} settlements)")
    elif name_count >= 3:
        score -= 1.0
        reasons.append(f"-1 common name ({name_count} settlements)")

    # ── 4. Population bonus (big cities are more likely targets) ──
    if candidate.population >= 100000:
        score += 2.0
        reasons.append("+2 major city (100k+)")
    elif candidate.population >= 30000:
        score += 1.0
        reasons.append("+1 city (30k+)")
    elif candidate.population > 0 and candidate.population < 5000 and candidate.source.startswith('gazetteer'):
        score -= 1.0
        reasons.append(f"-1 tiny village ({candidate.population} pop)")
        
    # Micro Tie-Breaker
    if candidate.population and candidate.population > 0:
        pfac = candidate.population / 1_000_000.0
        score += pfac
        reasons.append(f"+{pfac:.5f} pop micro-tiebreaker")

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

    # ── 6b. Explicit place_name match (strong disambiguation for homonyms) ──
    place_ent = (entities.get('place_name') or '').strip().lower()
    cand_name = (candidate.name or '').strip().lower()
    if place_ent and cand_name and len(place_ent) >= 3:
        if place_ent == cand_name:
            score += 3.0
            reasons.append("+3 exact place_name match")
        elif place_ent in cand_name or cand_name in place_ent:
            # «Нова Одеса» ⊃ «одеса» — не підсилювати велику Одесу замість Нової Одеси (Миколаївщина)
            compound_nova = (
                place_ent.startswith('нова ')
                and len(place_ent) > 5
                and place_ent[5:].strip() == cand_name
            )
            if not compound_nova:
                score += 1.5
                reasons.append("+1.5 place_name substring match")

    # ── 7. Direction / "near" / target_city check ──
    direction = entities.get('direction', '')
    target_city = entities.get('target_city', '')
    if direction and candidate.name:
        # If text says "напрямок на X" and X matches candidate → bonus
        if candidate.name.lower() in direction.lower():
            score += 2.0
            reasons.append("+2 direction target match")
    if target_city and candidate.name:
        tc = target_city.lower().strip()
        cn = candidate.name.lower()
        nova_tail = tc.startswith('нова ') and len(tc) > 5 and tc[5:].strip() == cn
        if not nova_tail and (
                cn == tc or cn in tc or tc in cn):
            score += 2.0
            reasons.append("+2 target_city match")

    near_txt = (entities.get('near') or '').strip().lower()
    if near_txt and candidate.name:
        cn = candidate.name.lower()
        if cn in near_txt or near_txt in cn:
            score += 2.0
            reasons.append("+2 near-reference text match")

    # ── 7c. Parser oblast string matches gazetteer oblast (disambiguation on borders)
    hint_oblast = (entities.get('oblast') or '').strip()
    cand_oblast = (candidate.oblast or '').strip()
    if hint_oblast and cand_oblast and hint_oblast.lower() == cand_oblast.lower():
        score += 1.5
        reasons.append("+1.5 parser oblast matches candidate oblast")

    # ── 8. Proximity to previous events ──
    ent_family = threat_family(entities.get('threat_type'))
    if prev_events:
        for evt in prev_events[-5:]:  # check last 5
            evt_lat = evt.get('lat')
            evt_lng = evt.get('lng')
            if evt_lat and evt_lng:
                dist = haversine_km(candidate.lat, candidate.lng, evt_lat, evt_lng)
                evt_type = evt.get('event_type') or evt.get('threat_type') or evt.get('type')
                same_family = threat_family(evt_type) == ent_family
                evt_region = (evt.get('region') or '').strip()
                same_oblast = bool(
                    cand_oblast and evt_region
                    and evt_region.lower() == cand_oblast.lower()
                )
                if dist < 100:
                    bonus = 2.5 if same_family else 2.0
                    if same_oblast:
                        bonus += 0.5
                    score += bonus
                    reasons.append(
                        f"+{bonus:.1f} within {dist:.0f}km of recent event"
                        + (" (same threat family)" if same_family else "")
                    )
                    break
                if dist < 180 and same_family and same_oblast:
                    score += 1.5
                    reasons.append(f"+1.5 {dist:.0f}km same-oblast same-family trail")
                    break
                if dist > 500:
                    score -= 1.0
                    reasons.append(f"-1 {dist:.0f}km from recent events")
                    break

    return score, reasons
