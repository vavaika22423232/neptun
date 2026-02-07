"""
GeoResolver — main orchestrator.

Pipeline:
  1. Gazetteer lookup (instant, all candidates)
  2. If no hits, cascade to external geocoders
  3. Score all candidates
  4. Apply polygon/bbox validation rules
  5. Pick winner, compute confidence
"""

import logging
from typing import Optional

from geo.gazetteer import LocationCandidate, ResolvedLocation, find_candidates
from geo import scoring
from geo import rules
from geo import feedback

log = logging.getLogger(__name__)

# ── Confidence computation ───────────────────────────────────────────────────

def _compute_confidence(candidates: list[LocationCandidate]) -> tuple[float, str]:
    """
    Compute confidence (0.0-1.0) and status from scored candidates.
    
    Returns (confidence, status) where status is one of:
      "ok"             - high confidence, clear winner
      "ambiguous"      - two candidates too close in score
      "low_confidence" - best score is low
      "rejected"       - no valid candidates
    """
    if not candidates:
        return 0.0, "rejected"

    best = candidates[0]

    # Absolute score thresholds
    if best.score < -5:
        return 0.05, "rejected"

    if best.score < 0:
        return 0.15, "low_confidence"

    # Check if there's a close second
    if len(candidates) >= 2:
        second = candidates[1]
        gap = best.score - second.score
        if gap < 2.0 and best.score < 8:
            # Close race → ambiguous
            conf = min(0.5, 0.3 + best.score * 0.02)
            return conf, "ambiguous"

    # Confidence based on absolute score
    if best.score >= 12:
        return 0.95, "ok"
    elif best.score >= 8:
        return 0.85, "ok"
    elif best.score >= 5:
        return 0.70, "ok"
    elif best.score >= 3:
        return 0.55, "ok"
    elif best.score >= 1:
        return 0.40, "low_confidence"
    else:
        return 0.25, "low_confidence"


# ── External geocoder cascade ────────────────────────────────────────────────

def _try_external_geocoders(
    place_name: str,
    oblast_hint: Optional[str] = None,
) -> Optional[tuple[float, float]]:
    """
    Try external geocoders in cascade: Nominatim → OpenCage → Visicom.
    Returns (lat, lng) or None.
    """
    # Try Nominatim (free, no key required)
    try:
        from nominatim_geocoder import get_coordinates_nominatim
        result = get_coordinates_nominatim(place_name, oblast_hint)
        if result:
            log.info(f"[GEOCODE] Nominatim hit: {place_name} -> {result}")
            return result
    except Exception as e:
        log.debug(f"Nominatim failed: {e}")

    # Try OpenCage
    try:
        from opencage_geocoder import geocode_city
        result = geocode_city(place_name, oblast_hint)
        if result:
            log.info(f"[GEOCODE] OpenCage hit: {place_name} -> {result}")
            return result
    except Exception as e:
        log.debug(f"OpenCage failed: {e}")

    # Try Visicom
    try:
        from visicom_geocoder import geocode as visicom_geocode
        result = visicom_geocode(place_name, oblast_hint)
        if result:
            log.info(f"[GEOCODE] Visicom hit: {place_name} -> {result}")
            return result
    except Exception as e:
        log.debug(f"Visicom failed: {e}")

    return None


# ── Main resolve ─────────────────────────────────────────────────────────────

def resolve(
    entities: dict,
    channel: Optional[str] = None,
    prev_events: Optional[list] = None,
) -> ResolvedLocation:
    """
    Main resolution pipeline.
    
    Args:
        entities: {
            'place_name': str,       # e.g. "Васильківка"
            'oblast': str | None,    # e.g. "Дніпропетровська область"
            'direction': str | None, # e.g. "напрямок на Павлоград"
            'near': str | None,      # e.g. "поблизу Миргорода"
            'raion': str | None,
            'threat_type': str,
        }
        channel: Telegram channel name
        prev_events: Recent events for proximity scoring
    
    Returns:
        ResolvedLocation with confidence, status, and top candidates
    """
    place_name = entities.get('place_name', '')
    oblast_hint = entities.get('oblast')

    if not place_name:
        return ResolvedLocation(
            lat=0.0, lng=0.0, oblast=oblast_hint or '', raion=None,
            place_name='Unknown', confidence=0.0, status='rejected', chosen_from=[],
        )

    # ── 1. Gazetteer lookup ──
    candidates = find_candidates(place_name, oblast_hint)
    log.info(f"[RESOLVE] Gazetteer: '{place_name}' (oblast={oblast_hint}) -> {len(candidates)} candidates")

    # ── 2. If no gazetteer results, try external geocoders ──
    if not candidates:
        ext_coords = _try_external_geocoders(place_name, oblast_hint)
        if ext_coords:
            candidates = [LocationCandidate(
                name=place_name,
                lat=ext_coords[0],
                lng=ext_coords[1],
                oblast=oblast_hint,
                raion=None,
                source='external_geocoder',
            )]

    # ── 3. Also try "near" and "direction" targets as supplementary candidates ──
    near_place = entities.get('near', '')
    if near_place and near_place != place_name:
        near_candidates = find_candidates(near_place, oblast_hint, limit=3)
        for nc in near_candidates:
            nc.source = 'gazetteer_near_ref'
            nc.score -= 1  # slight penalty: it's the "near" target, not the primary
        candidates.extend(near_candidates)

    # ── 4. Get channel priors ──
    channel_priors = {}
    if channel:
        try:
            channel_priors = feedback.get_channel_priors(channel)
        except Exception:
            pass

    # ── 5. Score all candidates ──
    for c in candidates:
        s, r = scoring.score_candidate(c, entities, channel, prev_events, channel_priors)
        c.score += s
        c.reasons.extend(r)

    # ── 6. Apply rules (polygon/bbox validation) ──
    for c in candidates:
        penalties = rules.validate_candidate(c, oblast_hint)
        for delta, reason in penalties:
            c.score += delta
            c.reasons.append(reason)

    # ── 7. Sort by score descending ──
    candidates.sort(key=lambda c: c.score, reverse=True)

    # ── 8. Compute confidence ──
    confidence, status = _compute_confidence(candidates)

    # ── 9. Pick winner ──
    if candidates and status != 'rejected':
        best = candidates[0]

        # Update channel prior
        if channel and best.oblast:
            try:
                feedback.update_channel_prior(channel, best.oblast)
            except Exception:
                pass

        return ResolvedLocation(
            lat=best.lat,
            lng=best.lng,
            oblast=best.oblast or oblast_hint or '',
            raion=best.raion,
            place_name=best.name,
            confidence=confidence,
            status=status,
            chosen_from=candidates[:5],
        )

    # ── Fallback: no candidates at all ──
    return ResolvedLocation(
        lat=0.0,
        lng=0.0,
        oblast=oblast_hint or '',
        raion=None,
        place_name=place_name,
        confidence=0.0,
        status='rejected',
        chosen_from=candidates[:5],
    )
