#!/usr/bin/env python3
"""
Quality tests for UAV marker region fix:
- Visicom-only geocoding
- Region conversion (сумщина -> Сумська область)
- Visicom OBLAST_KEYS and cache key normalization
- Coords validation and cache invalidation
- UA_CITY_NORMALIZE (зіньки -> зіньків)
- Per-line "БПЛА Місто (Обл.)" parsing
"""
import re
import sys
import unittest
from unittest.mock import patch


# --- 1. Parser: OBLAST_HDR_TO_FULL_REGION and _region_for_geocode ---
class TestRegionForGeocode(unittest.TestCase):
    def test_region_for_geocode_щина_to_full_region(self):
        """Парсер: перетворення сумщина/полтавщина на повну назву області для Visicom."""
        from parser_service import _region_for_geocode

        self.assertEqual(_region_for_geocode("сумщина"), "Сумська область")
        self.assertEqual(_region_for_geocode("полтавщина"), "Полтавська область")
        self.assertEqual(_region_for_geocode("харківщина"), "Харківська область")
        self.assertEqual(_region_for_geocode("вінниччина"), "Вінницька область")
        self.assertEqual(_region_for_geocode("київщина"), "Київська область")
        self.assertIsNone(_region_for_geocode(None))
        self.assertIsNone(_region_for_geocode(""))
        self.assertEqual(_region_for_geocode("сумська область"), "сумська область")

    def test_oblast_hdr_to_full_region_coverage(self):
        """У словнику є всі основні області з -щина/-ччина."""
        from parser_service import OBLAST_HDR_TO_FULL_REGION

        expected = [
            "сумщина", "полтавщина", "харківщина", "чернігівщина", "київщина",
            "дніпропетровщина", "миколаївщина", "одещина", "херсонщина",
            "запоріжжя", "донеччина", "луганщина", "черкащина", "вінниччина",
            "житомирщина", "рівненщина", "волинщина", "львівщина",
            "тернопільщина", "хмельниччина", "івано-франківщина", "кіровоградщина",
        ]
        for key in expected:
            self.assertIn(key, OBLAST_HDR_TO_FULL_REGION, msg=f"Missing: {key}")
            self.assertIn("область", OBLAST_HDR_TO_FULL_REGION[key], msg=f"Value: {OBLAST_HDR_TO_FULL_REGION[key]}")


# --- 2. Visicom: OBLAST_KEYS -щина, _get_oblast_key ---
class TestVisicomOblastKey(unittest.TestCase):
    def test_get_oblast_key_щина(self):
        """Visicom: _get_oblast_key повертає правильний ключ для сумщина/полтавщина."""
        from visicom_geocoder import _get_oblast_key

        self.assertEqual(_get_oblast_key("сумщина"), "сум")
        self.assertEqual(_get_oblast_key("полтавщина"), "полтав")
        self.assertEqual(_get_oblast_key("Сумська область"), "сум")
        self.assertEqual(_get_oblast_key("Полтавська обл."), "полтав")
        self.assertEqual(_get_oblast_key("харківщина"), "харків")
        self.assertEqual(_get_oblast_key("вінниччина"), "вінниц")

    def test_normalize_key_same_for_щина_and_ська(self):
        """Visicom: ключ кешу однаковий для "Сумська область" і "сумщина"."""
        from visicom_geocoder import _normalize_key

        key_oblast = _normalize_key("улянівка", "Сумська область")
        key_щина = _normalize_key("улянівка", "сумщина")
        self.assertEqual(key_oblast, key_щина, f"Cache keys should match: {key_oblast!r} vs {key_щина!r}")
        self.assertEqual(key_oblast, "улянівка|сумська")

        key_pol = _normalize_key("зіньків", "Полтавська область")
        key_pol_щ = _normalize_key("зіньків", "полтавщина")
        self.assertEqual(key_pol, key_pol_щ)
        self.assertEqual(key_pol, "зіньків|полтавська")


# --- 3. Parser: _coords_in_region ---
class TestCoordsInRegion(unittest.TestCase):
    def test_sumy_poltava_bounds(self):
        """Координати в межах Сумської/Полтавської перевіряються коректно."""
        from parser_service import _coords_in_region

        self.assertTrue(_coords_in_region(50.97, 34.29, "Сумська область"))
        self.assertTrue(_coords_in_region(51.0, 34.0, "сумщина"))
        self.assertFalse(_coords_in_region(49.0, 34.0, "Сумська область"))
        self.assertFalse(_coords_in_region(51.0, 37.0, "Сумська область"))

        self.assertTrue(_coords_in_region(49.67, 34.0, "Полтавська область"))
        self.assertTrue(_coords_in_region(49.59, 34.55, "полтавщина"))
        self.assertFalse(_coords_in_region(50.97, 34.29, "Полтавська область"))


# --- 4. UA_CITY_NORMALIZE: зіньки, іванки ---
class TestUACityNormalize(unittest.TestCase):
    def test_зиньки_іванки(self):
        """Парсер: зіньки -> зіньків, іванки -> іванків для коректного геокоду."""
        from parser_service import UA_CITY_NORMALIZE

        self.assertEqual(UA_CITY_NORMALIZE.get("зіньки"), "зіньків")
        self.assertEqual(UA_CITY_NORMALIZE.get("іванки"), "іванків")
        self.assertEqual(UA_CITY_NORMALIZE.get("броварки"), "бровари")


# --- 5. App: opencage_geocode тільки Visicom (без OpenCage) ---
class TestAppVisicomOnly(unittest.TestCase):
    def test_opencage_geocode_visicom_only(self):
        """app.opencage_geocode викликає лише Visicom і не робить fallback на OpenCage."""
        try:
            import app as app_module
        except Exception as e:
            self.skipTest(f"Cannot import app (missing deps): {e}")

        with patch.object(app_module, '_visicom_available', True):
            with patch.object(app_module, '_visicom_geocode') as mock_visicom:
                with patch.object(app_module, '_opencage_available', True):
                    with patch.object(app_module, '_opencage_geocode') as mock_oc:
                        mock_visicom.return_value = (50.5, 34.0)
                        result = app_module.opencage_geocode("улянівка", "Сумська область")
                        self.assertEqual(result, (50.5, 34.0))
                        mock_visicom.assert_called_once_with("улянівка", "Сумська область")
                        mock_oc.assert_not_called()

                        mock_visicom.return_value = None
                        result = app_module.opencage_geocode("невідоме_місто", "Сумська область")
                        self.assertIsNone(result)
                        mock_oc.assert_not_called()


# --- 6. Mapstransler pattern: перший рядок і обл. в дужках ---
class TestMapstranslerPattern(unittest.TestCase):
    def test_pattern_matches(self):
        """Патерн mapstransler збігається з повідомленнями БПЛА Місто (Обл.)."""
        threat_type_pattern = r'(?:БПЛА|КАБ|Ракета|Ракети|Шахед|Дрон|Дрони)'
        p_with_count = re.compile(
            rf'^[^\w]*(\d+)[xх×]?\s*{threat_type_pattern}\s+([А-ЯІЇЄЁа-яіїєё\'\-\s/]+)[^(]*\(([^)]+обл[^)]*)\)',
            re.IGNORECASE
        )
        p_no_count = re.compile(
            rf'^[^\w]*{threat_type_pattern}\s+([А-ЯІЇЄЁа-яіїєё\'\-\s/]+)[^(]*\(([^)]+обл[^)]*)\)',
            re.IGNORECASE
        )

        messages = [
            "БПЛА Зіньки (Полтавська обл.)",
            "БПЛА Заводське (Полтавська обл.)",
            "БПЛА Улянівка (Сумська обл.)",
            "2х БПЛА Барвінкове (Харківська обл.)",
        ]
        for msg in messages:
            m = p_with_count.search(msg) or p_no_count.search(msg)
            self.assertTrue(m, msg=f"Pattern should match: {msg!r}")
            if m.lastindex >= 3:
                city = m.group(2).strip()
                oblast = m.group(3).strip()
            else:
                city = m.group(1).strip()
                oblast = m.group(2).strip()
            self.assertTrue(city and oblast)
            self.assertTrue("обл" in oblast.lower() or "область" in oblast.lower())


# --- 7. Process_message з mock геокодером: координати в правильній області ---
class TestProcessMessageUavRegion(unittest.TestCase):
    """process_message з підставним геокодером повертає треки з координатами у вказаній області."""

    def setUp(self):
        from parser_service import bind_dependencies

        def mock_opencage_geocode(city, region=None):
            city = (city or "").lower().strip()
            region = (region or "").lower()
            if "улянівка" in city and "сум" in region:
                return (50.972007, 34.294672)
            if "зіньків" in city and "полтав" in region:
                return (49.67, 34.0)
            if "заводське" in city and "полтав" in region:
                return (49.5, 34.2)
            return None

        def mock_extract_oblast(text):
            if not text:
                return None
            text = str(text)
            if "Сумська" in text or "сумська" in text:
                return "Сумська область"
            if "Полтавська" in text or "полтавська" in text:
                return "Полтавська область"
            return None

        bind_dependencies({
            "opencage_geocode": mock_opencage_geocode,
            "_extract_oblast_from_text": mock_extract_oblast,
            "ensure_city_coords_with_message_context": lambda c, t=None: mock_opencage_geocode(c, mock_extract_oblast(t) if t else None),
            "add_debug_log": lambda *a, **k: None,
            "CITY_COORDS": {},
            "SETTLEMENTS_INDEX": {},
            "GEOCODER_AVAILABLE": True,
        })

    def test_улянівка_сумська(self):
        from parser_service import _coords_in_region, process_message

        tracks = process_message(
            "БПЛА Улянівка (Сумська обл.)",
            "test_1", "2025-02-06 12:00:00", "test",
            _disable_multiline=True,
        )
        self.assertTrue(tracks, "Should return at least one track")
        track = tracks[0]
        self.assertIn("lat", track)
        self.assertIn("lng", track)
        self.assertTrue(_coords_in_region(track["lat"], track["lng"], "Сумська область"),
                        f"Улянівка should be in Sumy: got ({track['lat']}, {track['lng']})")
        self.assertIn("Улянівка", track.get("place", ""))

    def test_зіньки_полтавська(self):
        from parser_service import _coords_in_region, process_message

        tracks = process_message(
            "БПЛА Зіньки (Полтавська обл.)",
            "test_2", "2025-02-06 12:00:00", "test",
            _disable_multiline=True,
        )
        self.assertTrue(tracks, "Should return at least one track")
        t = tracks[0]
        self.assertTrue(_coords_in_region(t["lat"], t["lng"], "Полтавська область"),
                        f"Зіньків should be in Poltava: got ({t['lat']}, {t['lng']})")


# --- 8. Per-line: кілька рядків БПЛА Місто (Обл.) ---
class TestProcessMessageMultiline(unittest.TestCase):
    """Повідомлення з кількома рядками БПЛА Місто (Обл.) дає по одному треку на рядок."""

    def setUp(self):
        from parser_service import bind_dependencies

        def mock_geocode(city, region=None):
            c = (city or "").lower()
            r = (region or "").lower()
            if "улянівка" in c and "сум" in r:
                return (50.97, 34.29)
            if "зіньки" in c or "зіньків" in c:
                if "полтав" in r:
                    return (49.67, 34.0)
            if "заводське" in c and "полтав" in r:
                return (49.5, 34.2)
            return None

        def mock_extract(t):
            if not t:
                return None
            t = str(t).lower()
            if "сумська" in t or "сумщина" in t:
                return "Сумська область"
            if "полтавська" in t or "полтавщина" in t:
                return "Полтавська область"
            return None

        def _ensure_city_coords(city, region=None, context=None):
            return mock_geocode(city, region or (mock_extract(context) if context else None))

        bind_dependencies({
            "opencage_geocode": mock_geocode,
            "_extract_oblast_from_text": mock_extract,
            "ensure_city_coords_with_message_context": lambda c, t=None: mock_geocode(c, mock_extract(t)),
            "ensure_city_coords": _ensure_city_coords,
            "add_debug_log": lambda *a, **k: None,
            "CITY_COORDS": {},
            "SETTLEMENTS_INDEX": {},
            "GEOCODER_AVAILABLE": True,
        })

    def test_multiline_bpla_obl(self):
        from parser_service import _coords_in_region, process_message

        msg = "БПЛА Зіньки (Полтавська обл.)\nБПЛА Заводське (Полтавська обл.)\nБПЛА Улянівка (Сумська обл.)"
        tracks = process_message(msg, "test_multi", "2025-02-06 12:00:00", "test", _disable_multiline=False)
        self.assertGreaterEqual(len(tracks), 2, f"Expected at least 2 tracks for 3 lines, got {len(tracks)}")
        for t in tracks:
            lat, lng = t["lat"], t["lng"]
            place = t.get("place", "")
            if "Улянівка" in place:
                self.assertTrue(_coords_in_region(lat, lng, "Сумська область"), f"Улянівка in Sumy: ({lat}, {lng})")
            if "Зіньк" in place or "Заводське" in place:
                self.assertTrue(_coords_in_region(lat, lng, "Полтавська область"), f"Poltava: ({lat}, {lng})")


def run_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestRegionForGeocode))
    suite.addTests(loader.loadTestsFromTestCase(TestVisicomOblastKey))
    suite.addTests(loader.loadTestsFromTestCase(TestCoordsInRegion))
    suite.addTests(loader.loadTestsFromTestCase(TestUACityNormalize))
    suite.addTests(loader.loadTestsFromTestCase(TestAppVisicomOnly))
    suite.addTests(loader.loadTestsFromTestCase(TestMapstranslerPattern))
    suite.addTests(loader.loadTestsFromTestCase(TestProcessMessageUavRegion))
    suite.addTests(loader.loadTestsFromTestCase(TestProcessMessageMultiline))
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    sys.path.insert(0, ".")
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
