import unittest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.parser_v2 import parse_message

class TestNightmareScenarios(unittest.TestCase):
    """
    Testing against 'Nightmare' datasets: Russian, Translit, Negations, Ambiguity.
    """
    
    DATASET = [
        # 1. Russian Language (High probability in some channels)
        ("Ракета на Киев!", "missile", "Київ"),
        ("Взрывы в Харькове", "explosion", "Харків"),
        ("Днепр - укрытие!", "unknown", "Дніпро"), # 'укрытие' might not be a keyword yet
        
        # 2. Transliteration (Rare but possible from Western sources or auto-translate)
        ("Shahed headed to Kyiv", "uav", "Київ"),
        
        # 3. False Positives / Negation
        # "Explosions NOT recorded" - naive parser might see "Explosion" and trigger.
        ("Інформація про вибухи не підтвердилась.", "info", "Unknown"), 
        # We don't have 'info' type, so maybe 'explosion' is acceptable but undesirable?
        # Ideally parsing logic should detect negation or specific "Fake/Refutal" keywords.
        
        # 4. Hashtag Spam
        ("#Київ #повітряна_тривога #ракета", "missile", "Київ"),
        
        # 5. Typos in major cities
        ("Ракта на Киїїв", "missile", "Київ"), # "Ракта" (typo), "Киїїв" (typo)
        
        # 6. Multiple targets in one message
        ("Ракети на Вінницю та Житомир", "missile", "Вінниця"), # Should pick at least one
        
        # 7. Hidden Context (Replied message)
        # "Forwarded from Monitor: ... Kyiv ..."
        ("Forwarded message:\nШахед вектором на Бровари", "uav", "Бровари"),
    ]

    def test_nightmare_dataset(self):
        print(f"\nrunning {len(self.DATASET)} NIGHTMARE scenarios...")
        failures = []
        for text, exp_type, exp_loc in self.DATASET:
            e = parse_message(text)
            
            # Relaxed Type Check for 'info'/'unknown' mismatch usually meant for negation
            if exp_type == "info":
                # If we expect INFO (ignore), but got EXPLOSION, that is a False Positive.
                if e.type in ['launch', 'missile', 'explosion']:
                    failures.append(f"FALSE POSITIVE: '{text}' -> Got {e.type}, Expected Ignore/Info")
                continue

            # Standard Checks
            if exp_type != "unknown" and e.type != exp_type:
                 failures.append(f"TYPE MISMATCH: '{text}' -> Got {e.type}, Expected {exp_type}")
                 continue
            
            # Location Check
            if exp_loc != "Unknown":
                if exp_loc.lower() not in e.location.lower():
                     failures.append(f"LOC MISMATCH: '{text}' -> Got '{e.location}', Expected '{exp_loc}'")
        
        if failures:
            print("\n".join(failures))
            # forcing failure if significant
            self.fail(f"Failed {len(failures)} scenarios.")

if __name__ == '__main__':
    unittest.main()
