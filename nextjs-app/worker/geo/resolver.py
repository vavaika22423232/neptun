"""
GeoResolver — main orchestrator.

Pipeline:
  1. Normalize place name (accusative → nominative)
  2. Gazetteer lookup (instant, all candidates)
  3. If no hits, cascade to external geocoders
  4. Auto-learn external results into gazetteer (self-learning loop)
  5. Score all candidates
  6. Apply polygon/bbox validation rules
  7. Sort; oblast context gate (explicit oblast_gate_hint vs coords, not channel-default alone)
  8. Pick winner, compute confidence
"""

import logging
import re
from typing import Optional

from geo.gazetteer import LocationCandidate, ResolvedLocation, find_candidates, learn_from_external, learn_alias
from geo.place_normalize import (
    disambiguate_homonym_place,
    place_variants,
    primary_place_token,
    strip_settlement_prefix,
)
from geo import scoring
from geo import rules
from geo import feedback

try:
    from geo_bounds import is_plausible_threat_coord
except ImportError:
    def is_plausible_threat_coord(lat, lng, manual=False):  # type: ignore[misc]
        return True

log = logging.getLogger(__name__)

REGIONAL_CENTERS = {
    'Київська область': (50.4501, 30.5234),
    'Київ': (50.4501, 30.5234),
    'Харківська область': (49.9935, 36.2304),
    'Одеська область': (46.4825, 30.7233),
    'Дніпропетровська область': (48.4647, 35.0462),
    'Запорізька область': (47.8388, 35.1396),
    'Львівська область': (49.8397, 24.0297),
    'Миколаївська область': (46.9750, 31.9946),
    'Херсонська область': (46.6354, 32.6169),
    'Полтавська область': (49.5883, 34.5514),
    'Чернігівська область': (51.4981, 31.2893),
    'Сумська область': (50.9077, 34.7981),
    'Житомирська область': (50.2547, 28.6587),
    'Вінницька область': (49.2331, 28.4682),
    'Черкаська область': (49.4444, 32.0597),
    'Хмельницька область': (49.4230, 26.9871),
    'Чернівецька область': (48.2921, 25.9358),
    'Рівненська область': (50.6199, 26.2516),
    'Івано-Франківська область': (48.9226, 24.7111),
    'Тернопільська область': (49.5535, 25.5948),
    'Волинська область': (50.7472, 25.3254),
    'Закарпатська область': (48.6208, 22.2879),
    'Кіровоградська область': (48.5079, 32.2623),
}

# ── Accusative → Nominative normalization (reuse from parser) ────────────────

try:
    from core.parser_v2 import normalize_place_case, CARDINAL_DIRECTIONS
    _has_normalizer = True
except ImportError:
    _has_normalizer = False
    CARDINAL_DIRECTIONS = {}
    def normalize_place_case(name: str) -> str:
        return name

try:
    from geo.place_guardrails import is_garbage_place_token
except ImportError:
    def is_garbage_place_token(place: Optional[str]) -> bool:  # type: ignore[misc]
        return False

# Strip leading "напрямок на / курсом на / на " from direction field to get a toponym
_DIRECTION_TOKEN_STRIP = re.compile(
    r'^(?:➡️\s*)?(?:(?:напрям(?:ок|ку)|курс(?:ом)?|рух|вектор|йдуть|йде|летять|летить|прямують|прямує)\s+)?'
    r'(?:на|до|в|у)\s+',
    re.IGNORECASE,
)


def _direction_target_token(direction: str) -> str:
    if not direction or not direction.strip():
        return ''
    d = _DIRECTION_TOKEN_STRIP.sub('', direction.strip())
    d = d.split(',')[0].split('(')[0].strip()
    return d


def _first_word_is_cardinal(token: str) -> bool:
    """True if direction names only a compass sector, not a settlement."""
    if not token:
        return True
    parts = token.lower().strip().split()
    if not parts:
        return True
    if parts[0] in CARDINAL_DIRECTIONS:
        return True
    if len(parts) >= 2:
        bigram = f"{parts[0]} {parts[1]}"
        if bigram in CARDINAL_DIRECTIONS:
            return True
    return False

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


# ── External geocoder cascade (Local Photon → Visicom API) ───────────────────

def _try_external_geocoders(
    place_name: str,
    oblast_hint: Optional[str] = None,
    city_hint: Optional[str] = None,
) -> Optional[tuple[float, float, str]]:
    """
    Query external geocoders as fallback when local gazetteer has no results.
    Cascade: Photon (local) → Visicom (API, authoritative for Ukraine).
    city_hint: optional city anchor for Photon (e.g. «Херсон» for microdistricts).
    """
    # 1. Try local Photon first (free, no API cost)
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        from photon_geocoder import get_coordinates_photon
        
        result = get_coordinates_photon(place_name, oblast_hint, city_hint)
        if result:
            log.info(f"[GEOCODE] Photon: {place_name} -> {result}")
            return (result[0], result[1], 'photon')
    except Exception as e:
        log.debug(f"Photon geocoder failed: {e}")

    # 2. Fallback to Visicom API (authoritative Ukrainian geocoder, 28k+ settlements)
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        from visicom_geocoder import visicom_geocode

        result = visicom_geocode(place_name, oblast_hint)
        if result and len(result) == 2:
            lat, lng = result
            if lat and lng:
                log.info(f"[GEOCODE] Visicom: {place_name} -> ({lat}, {lng})")
                return (lat, lng, 'visicom')
    except Exception as e:
        log.debug(f"Visicom geocoder failed: {e}")

    return None


def _external_learn_allowed(lat: float, lng: float, oblast_gate_hint: Optional[str]) -> bool:
    """Only persist external geocoder hits when they satisfy explicit oblast context."""
    ob_key = rules.resolve_oblast_bbox_key(oblast_gate_hint)
    if not ob_key:
        return True
    return rules.point_in_expanded_oblast_bbox(lat, lng, ob_key)


# ── Main resolve ─────────────────────────────────────────────────────────────

def resolve(
    entities: dict,
    channel: Optional[str] = None,
    prev_events: Optional[list] = None,
    oblast_gate_hint: Optional[str] = None,
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
        oblast_gate_hint: If set, hard bbox gate + demotion of far homonyms uses ONLY this hint
            (parser / explicit text). Omit when oblast comes solely from channel default —
            avoids locking the winner to the wrong oblast.
    
    Returns:
        ResolvedLocation with confidence, status, and top candidates
    """
    raw_place = entities.get('place_name') or ''
    target_city = entities.get('target_city') or ''
    place_name = raw_place or target_city or ''
    is_predictive = bool(not raw_place and target_city)

    oblast_hint = entities.get('oblast')
    city_hint = entities.get('geo_city_hint') or None
    if isinstance(city_hint, str):
        city_hint = city_hint.strip() or None

    if not place_name:
        return ResolvedLocation(
            lat=0.0, lng=0.0, oblast=oblast_hint or '', raion=None,
            place_name='Unknown', confidence=0.0, status='rejected', chosen_from=[],
            is_predictive=is_predictive,
        )

    # ── 0. Normalize case (accusative → nominative) ──
    original_name = place_name
    place_name = normalize_place_case(place_name)
    if place_name != original_name:
        log.debug(f"[RESOLVE] Normalized: '{original_name}' -> '{place_name}'")

    if is_garbage_place_token(place_name) or is_garbage_place_token(original_name):
        log.info(f"[RESOLVE] Rejected garbage place token: {original_name!r}")
        return ResolvedLocation(
            lat=0.0, lng=0.0, oblast=oblast_hint or '', raion=None,
            place_name=place_name or original_name, confidence=0.0, status='rejected', chosen_from=[],
            is_predictive=is_predictive,
        )

    _hom_fix = disambiguate_homonym_place(place_name, oblast_hint)
    if _hom_fix != place_name:
        log.info(f"[RESOLVE] Homonym disambiguation: '{place_name}' → '{_hom_fix}' (oblast={oblast_hint})")
        place_name = _hom_fix

    def _is_black_sea_toponym(t: str) -> bool:
        x = (t or '').lower().strip()
        if not x:
            return False
        if 'чорноморськ' in x:
            return False
        # АЧМ = азово-чорноморська акваторія (той самий морський пін, що «Чорне море»)
        if x in (
            'ачм',
            'а/чм',
            'а.ч.м.',
            'а ч м',
        ):
            return True
        if x in (
            'чорне море', 'чорного моря', 'чорному морю', 'чорним морем',
            'чорне морю',
            'море', 'морі', 'в морі',
        ):
            return True
        if 'чорне мор' in x or 'чорного мор' in x or 'чорному мор' in x or 'чорним мор' in x:
            return True
        if 'черное мор' in x or 'чёрное мор' in x or 'черного мор' in x:
            return True
        return False

    # Чорне море → точка в акваторії на підльоті до Одещини (не центр Одеси на суші)
    if _is_black_sea_toponym(place_name) or _is_black_sea_toponym(original_name):
        lat_bs, lng_bs = 46.14, 30.96
        oh = (oblast_hint or '').strip()
        disp_oblast = oh if 'одес' in oh.lower() else 'Одеська область'
        sea_c = LocationCandidate(
            name='Чорне море',
            lat=lat_bs,
            lng=lng_bs,
            oblast=disp_oblast,
            raion=None,
            source='synthetic_black_sea_odesa_approach',
            score=12.0,
            place_type='water',
            population=0,
        )
        log.info(
            f"[RESOLVE] Black Sea (Odesa approach) → ({lat_bs},{lng_bs}), display_oblast={disp_oblast}"
        )
        return ResolvedLocation(
            lat=lat_bs,
            lng=lng_bs,
            oblast=disp_oblast,
            raion=None,
            place_name='Чорне море',
            confidence=0.82,
            status='ok',
            chosen_from=[sea_c],
            is_predictive=is_predictive,
        )

    # Variants: "м. X", RU spellings, "City / oblast" → improve gazetteer + geocoder hit rate
    variant_list: list[str] = []
    seen_variant: set[str] = set()

    def _push_variants(raw: str) -> None:
        for v in place_variants(raw):
            k = v.lower()
            if k in seen_variant:
                continue
            seen_variant.add(k)
            variant_list.append(v)

    _push_variants(place_name)
    if original_name != place_name:
        _push_variants(original_name)

    # ── 1. Gazetteer lookup (merge unique coordinates across variants) ──
    candidates: list[LocationCandidate] = []
    seen_pos: set[tuple[float, float]] = set()

    def _absorb_gazetteer(hits: list[LocationCandidate]) -> None:
        for c in hits:
            key = (round(c.lat, 4), round(c.lng, 4))
            if key in seen_pos:
                continue
            seen_pos.add(key)
            candidates.append(c)

    for v in variant_list:
        hits = find_candidates(v, oblast_hint)
        if hits:
            log.debug(f"[RESOLVE] Gazetteer variant '{v}': {len(hits)} hits")
            _absorb_gazetteer(hits)

    log.info(
        f"[RESOLVE] Gazetteer: {len(candidates)} unique candidates "
        f"from {len(variant_list)} name variant(s), oblast={oblast_hint}"
    )

    # ── 2. If no gazetteer results OR best hit is a tiny village, inject external geocoders ──
    best_pop = max((c.population for c in candidates), default=0)
    if not candidates or best_pop < 15000:
        ext_result = None
        ext_used = place_name
        for v in variant_list:
            ext_result = _try_external_geocoders(v, oblast_hint, city_hint)
            if ext_result:
                ext_used = v
                break
        if ext_result:
            lat, lng, api_source = ext_result
            c_ext = LocationCandidate(
                name=ext_used,
                lat=lat,
                lng=lng,
                oblast=oblast_hint,
                raion=None,
                source=f'geocoder_{api_source}',
                population=0,
            )
            # Add to list rather than replacement! The score engine will pick the winner.
            candidates.append(c_ext)
            if _external_learn_allowed(lat, lng, oblast_gate_hint):
                learn_from_external(ext_used, lat, lng, oblast_hint, api_source)
            if ext_used != place_name:
                learn_alias(place_name, ext_used)
            if original_name != place_name and original_name.lower() != ext_used.lower():
                learn_alias(original_name, ext_used)

    # ── 3. "near" reference: gazetteer + external (small places often missing from DB) ──
    near_raw = entities.get('near', '') or ''
    near_place = ''
    if near_raw:
        near_place = normalize_place_case(
            strip_settlement_prefix(primary_place_token(near_raw))
        )
    if near_place and near_place.lower() not in (place_name.lower(), original_name.lower()):
        near_hits = find_candidates(near_place, oblast_hint, limit=5)
        for nc in near_hits:
            nc.source = 'gazetteer_near_ref'
            nc.score -= 1
        candidates.extend(near_hits)
        if not near_hits:
            ext_near = None
            ext_used_near = near_place
            for nv in place_variants(near_place):
                ext_near = _try_external_geocoders(nv, oblast_hint, city_hint)
                if ext_near:
                    ext_used_near = nv
                    break
            if ext_near:
                lat, lng, api_source = ext_near
                nc = LocationCandidate(
                    name=ext_used_near,
                    lat=lat,
                    lng=lng,
                    oblast=oblast_hint,
                    raion=None,
                    source=f'geocoder_near_{api_source}',
                )
                nc.score -= 2
                candidates.append(nc)
                if _external_learn_allowed(lat, lng, oblast_gate_hint):
                    learn_from_external(ext_used_near, lat, lng, oblast_hint, api_source)
                log.info(f"[RESOLVE] External geocode for near-reference '{near_place}' → ({lat:.4f},{lng:.4f})")

    # ── 3b. Direction field may name a different settlement than place_name ──
    dir_raw = (entities.get('direction') or '').strip()
    if dir_raw:
        dir_tok = normalize_place_case(
            strip_settlement_prefix(primary_place_token(_direction_target_token(dir_raw)))
        )
        if (
            len(dir_tok) >= 3
            and not _first_word_is_cardinal(dir_tok)
            and not is_garbage_place_token(dir_tok)
            and not is_garbage_place_token(dir_raw)
            and dir_tok.lower() not in seen_variant
        ):
            dir_lower = dir_tok.lower()
            if dir_lower not in (place_name.lower(), original_name.lower(), near_place.lower() if near_place else ''):
                dir_hits = find_candidates(dir_tok, oblast_hint, limit=5)
                for dc in dir_hits:
                    dc.source = 'gazetteer_direction_ref'
                    dc.score -= 1.5
                candidates.extend(dir_hits)
                if not dir_hits:
                    ext_dir = None
                    ext_used_dir = dir_tok
                    for dv in place_variants(dir_tok):
                        ext_dir = _try_external_geocoders(dv, oblast_hint, city_hint)
                        if ext_dir:
                            ext_used_dir = dv
                            break
                    if ext_dir:
                        lat, lng, api_source = ext_dir
                        dc = LocationCandidate(
                            name=ext_used_dir,
                            lat=lat,
                            lng=lng,
                            oblast=oblast_hint,
                            raion=None,
                            source=f'geocoder_direction_{api_source}',
                        )
                        dc.score -= 2.5
                        candidates.append(dc)
                        if _external_learn_allowed(lat, lng, oblast_gate_hint):
                            learn_from_external(ext_used_dir, lat, lng, oblast_hint, api_source)
                        log.info(
                            f"[RESOLVE] External geocode for direction-target '{dir_tok}' → ({lat:.4f},{lng:.4f})"
                        )

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

    # ── 7b. Глобальний «oblast gate»: не брати переможця з іншого кінця України,
    # лише коли є явний контекст області (парсер / дужки в тексті), не channel-default сам по собі.
    ob_key = rules.resolve_oblast_bbox_key(oblast_gate_hint)
    if ob_key and candidates:
        in_region: list[LocationCandidate] = []
        for c in candidates:
            src = (getattr(c, 'source', '') or '')
            if 'synthetic_black_sea' in src:
                in_region.append(c)
            elif rules.point_in_expanded_oblast_bbox(c.lat, c.lng, ob_key):
                in_region.append(c)
        if in_region:
            in_region.sort(key=lambda c: c.score, reverse=True)
            in_ids = {id(x) for x in in_region}
            tail = [c for c in candidates if id(c) not in in_ids]
            candidates = in_region + tail
            log.info(
                f"[RESOLVE] Oblast context gate [{ob_key}]: {len(in_region)} in expanded bbox, "
                f"{len(tail)} demoted"
            )
        else:
            fb = rules.oblast_bbox_center_latlng(ob_key)
            if fb:
                log.warning(
                    f"[RESOLVE] Oblast gate [{ob_key}]: no candidate in expanded bbox → bbox center fallback"
                )
                return ResolvedLocation(
                    lat=fb[0],
                    lng=fb[1],
                    oblast=ob_key,
                    raion=None,
                    place_name=place_name,
                    confidence=0.32,
                    status='low_confidence',
                    chosen_from=candidates[:5],
                    is_predictive=is_predictive,
                )

    # ── 8. Compute confidence ──
    confidence, status = _compute_confidence(candidates)

    # ── 9. Pick winner ──
    if candidates and status != 'rejected':
        best = candidates[0]

        # Geocoder/gazetteer can return a homonym outside the UA threat map — prefer in-bbox alt.
        if not is_plausible_threat_coord(best.lat, best.lng):
            alt = next(
                (
                    c
                    for c in candidates[1:]
                    if is_plausible_threat_coord(c.lat, c.lng) and c.score >= best.score - 4.0
                ),
                None,
            )
            if alt:
                log.warning(
                    f"[RESOLVE] Top pick outside threat bbox ({best.lat:.3f},{best.lng:.3f}) "
                    f"'{best.name}' → in-bbox '{alt.name}' (score gap ≤4)"
                )
                best = alt
                confidence = max(0.22, min(confidence * 0.88, 0.82))
            else:
                log.warning(
                    f"[RESOLVE] Rejected: no in-bbox candidate (best was {best.lat:.3f},{best.lng:.3f} '{best.name}')"
                )
                return ResolvedLocation(
                    lat=0.0,
                    lng=0.0,
                    oblast=oblast_hint or '',
                    raion=None,
                    place_name=place_name,
                    confidence=0.0,
                    status='rejected',
                    chosen_from=candidates[:5],
                    is_predictive=is_predictive,
                )

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
            is_predictive=is_predictive,
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
        is_predictive=is_predictive,
    )


def point_along_great_circle(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
    fraction: float,
    apply_jitter: bool = True,
    jitter_seed: str = '',
) -> tuple[float, float]:
    """
    Interpolate a point along the great circle between two WGS84 coordinates.
    fraction=0 → (lat1,lng1), fraction=1 → (lat2,lng2).
    Used for trajectory-aware placement (origin → target).
    Includes optional *deterministic* jitter to prevent markers stacking.
    jitter_seed should be a stable string (e.g. threat_id or marker_id)
    so the offset doesn't change between refreshes.
    """
    import math

    def _seeded_rand(seed_val: int) -> float:
        """Mulberry32-style seeded PRNG — returns 0..1."""
        seed_val = (seed_val + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((seed_val ^ (seed_val >> 15)) * (1 | seed_val)) & 0xFFFFFFFF
        t = ((t + ((t ^ (t >> 7)) * (61 | t))) ^ t) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0

    fraction = max(0.0, min(1.0, fraction))
    if fraction <= 0:
        return lat1, lng1
    if fraction >= 1:
        if apply_jitter:
            s = hash(f"{lat2:.4f}_{lng2:.4f}_{jitter_seed}") & 0xFFFFFFFF
            angle = _seeded_rand(s) * 2 * math.pi
            r = math.sqrt(_seeded_rand(s + 1)) * 0.015  # ~1.5 km
            return lat2 + math.cos(angle) * r, lng2 + math.sin(angle) * r
        return lat2, lng2
    φ1 = math.radians(lat1)
    λ1 = math.radians(lng1)
    φ2 = math.radians(lat2)
    λ2 = math.radians(lng2)
    x1 = math.cos(φ1) * math.cos(λ1)
    y1 = math.cos(φ1) * math.sin(λ1)
    z1 = math.sin(φ1)
    x2 = math.cos(φ2) * math.cos(λ2)
    y2 = math.cos(φ2) * math.sin(λ2)
    z2 = math.sin(φ2)
    x = (1.0 - fraction) * x1 + fraction * x2
    y = (1.0 - fraction) * y1 + fraction * y2
    z = (1.0 - fraction) * z1 + fraction * z2
    h = math.sqrt(x * x + y * y + z * z)
    if h < 1e-12:
        return lat1, lng1
    x, y, z = x / h, y / h, z / h
    lat = math.degrees(math.asin(max(-1.0, min(1.0, z))))
    lng = math.degrees(math.atan2(y, x))

    if apply_jitter:
        s = hash(f"{lat1:.4f}_{lng1:.4f}_{fraction:.3f}_{jitter_seed}") & 0xFFFFFFFF
        jitter_amount = 0.012 * fraction  # ~1.3 km max
        angle = _seeded_rand(s) * 2 * math.pi
        r = math.sqrt(_seeded_rand(s + 1)) * jitter_amount
        lat += math.cos(angle) * r
        lng += math.sin(angle) * r

    return lat, lng
