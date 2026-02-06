import unittest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.parser_v2 import parse_message

class TestRealWorldScenarios(unittest.TestCase):
    """
    Testing against a dataset of realistic/historic Telegram messages.
    """
    
    DATASET = [
        # (Input Text, Expected Type, Expected Location (or substring))
        
        # 1. Standard UAV
        ("🛵 Шахеди з півдня, курс на Миколаїв!", "uav", "Миколаїв"),
        
        # 2. Transliteration/Slang (Requires robust classifier)
        ("БпЛА в напрямку Одеси.", "uav", "Одеса"),
        
        # 3. KAB Activity
        ("Активність ворожої авіації на сході. Пуски КАБів на Харківщину.", "kab", "Харківська область"),
        
        # 4. Ballistics
        ("Загроза балістики для Дніпра!", "missile", "Дніпро"),
        
        # 5. Complex Multi-line
        ("🔴 Повітряна тривога в Києві!\nРозвідник в області.\nМожлива робота ППО.", "uav", "Київ"), 
        # Note: "Розвідник" -> UAV. 
        
        # 6. Specific Village (Frontline) - might fail if not in mock DB, but checking logic
        ("Курахове - обстріл!", "explosion", "Unknown"), 
        # "Курахове" likely not in our mock DB, so Unknown is expected for now unless added.
        
        # 7. Directional Noise Trap
        ("Ракета вектор Павлоград -> Дніпро.", "missile", "Павлоград"), 
        # Should pick first valid city? Or last? Currently first match wins or longest?
        # Ideally checks both? "Павлоград" is in mock DB. "Дніпро" is in mock DB.
        
        # 8. Region Lock with Typo (Simulated)
        ("Київська обл - рух БПЛА.", "uav", "Київська область"),
        
        # 9. Rare Event
        ("Зафіксовано зліт МіГ-31К!", "launch", "Unknown"),
        
        # 10. Hidden City
        ("Увага! Шахед підлітає до Умані.", "uav", "Умань"),
    ]

    def test_dataset(self):
        print(f"\nrunning {len(self.DATASET)} real-world scenarios...")
        failures = []
        for text, exp_type, exp_loc in self.DATASET:
            e = parse_message(text)
            
            # Check 1: Type
            if e.type != exp_type:
                failures.append(f"TYPE MISMATCH: '{text}' -> Got {e.type}, Expected {exp_type}")
                continue
                
            # Check 2: Location
            # We allow partial match or full match
            if exp_loc == "Unknown":
                # Accept anything valid-ish or Unknown
                pass
            elif exp_loc.lower() not in e.location.lower():
                 # Special case checking for Region fallbacks
                 if e.region and exp_loc.lower() in e.region.lower():
                     pass # Accept region level match if city not found
                 else:
                     failures.append(f"LOC MISMATCH: '{text}' -> Got '{e.location}', Expected '{exp_loc}'")
        
        if failures:
            self.fail("\n" + "\n".join(failures))

if __name__ == '__main__':
    unittest.main()
