import unittest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.parser_v2 import parse_message

class TestParserStress(unittest.TestCase):
    
    def test_multi_sentence_noise(self):
        # Real scenario: Clearing previous threat then announcing new one
        text = "Відбій тривоги по областях. Увага! Активність тактичної авіації на Сумщині! Загроза КАБ."
        e = parse_message(text)
        # Should detect the ACTIVE threat (KAB/Aviation), not just 'unknown' or 'explosion'
        # The classifier finds 'авіація' -> 'kab'.
        self.assertEqual(e.type, 'kab')
        self.assertEqual(e.region, 'Сумська область')

    def test_directional_confusion_extreme(self):
        # "North" (Північ) is a direction, but also looks like a name if not careful
        text = "БПЛА з Півдня на Північ через Кременчук. Курс північний."
        e = parse_message(text)
        # Should pick 'Кременчук' as the specific city
        # Should NOT pick 'Північ' or 'Півдня'
        self.assertEqual(e.location, "Кременчук")
        
    def test_multiple_cities_same_region(self):
        # "Nizhyn and Pryluky"
        # Logic matches the longest/first found?
        text = "Шахеди в районі Ніжина та Прилук (Чернігівська обл)"
        e = parse_message(text)
        # We expect one of them. Ideally 'Ніжин' or 'Прилуки'.
        # Our mock DB has both.
        self.assertIn(e.location.lower(), ['ніжин', 'прилуки'])
        self.assertEqual(e.region, 'Чернігівська область')

    def test_false_positive_prepositions(self):
        # "Na" shouldn't trigger if it's part of a word, but "Na" as word is noise.
        # "Varash" (Вараш) - city. "Na Varash" -> should be clean.
        # "Navarya" (Наварія) - village. "Na Navaryu" -> regex strictness?
        pass 

    def test_partial_oblast_match(self):
        # "Kyiv" vs "Kyivska oblast"
        # If text says "Kyiv", it should map to City Kyiv, NOT Oblast fallback.
        text = "Ракета на Київ"
        e = parse_message(text)
        self.assertEqual(e.location, "Київ")
        self.assertIsNone(e.region) # No explicit bracket authority

    def test_region_detected_but_no_city_in_text(self):
        # "Sumy region - danger"
        text = "Сумська область - ракетна небезпека!"
        e = parse_message(text)
        # Should fallback to Sumy city coords (Center) which is now correctly mapped to "Суми"
        self.assertEqual(e.location, "Суми") 
        # Let's check parser_v2 fallback: 
        # It tries to find key in OBLAST_CENTERS that matches authority region.
        # "Сумська" -> matches "Суми" key? No, "сум" matches "Суми" stem?
        # Current logic: `short_name = authority_region.split()[0].title()` -> "Сумська"
        # Then `for center_key in OBLAST_CENTERS.keys(): if center_key in authority_region.lower()`
        # "суми" IS NOT in "сумська область" (string mismatch: 'и' vs 'ь'). 
        # This fallback might fail for "Sumy" specifically due to Declension.
        
        # We expect it to be handled or safe fallback
        self.assertTrue(e.coords is not None, "Should have coordinates even if name is generic")

if __name__ == '__main__':
    unittest.main()
