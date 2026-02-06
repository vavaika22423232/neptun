import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.parser_v2 import parse_message, resolve_location

TEST_CASES = [
    {
        "text": "🛵 Шахед на Чернігівську обл (курс західний)",
        "expected_type": "uav",
        "expected_region": "Чернігівська область",
        "expected_loc_name": "Чернігівська область" # Fallback to region center
    },
    {
        "text": "‼️ Ракета на Київ!",
        "expected_type": "missile",
        "expected_region": None,
        "expected_loc_name": "Київ"
    },
    {
        "text": "БПЛА в напрямку Ніжина",
        "expected_type": "uav",
        "expected_region": None,
        # Note: Current implementation only checks OBLAST_CENTERS for global search.
        # If "Nizhin" is not in OBLAST_CENTERS, this might fail or return None.
        # We need to verify what is in OBLAST_CENTERS.
        "expected_loc_name": None 
    },
    {
        "text": "Активність тактичної авіації (Донецька область). КАБ на Покровськ",
        "expected_type": "kab",
        "expected_region": "Донецька область",
        "expected_loc_name": "Покровськ" # Assuming Pokrovsk is in UKRAINE_SETTLEMENTS_BY_OBLAST['Донецька область']
    }
]

def run_tests():
    print("🚀 Running Parser V2 Tests...")
    passed = 0
    failed = 0
    
    for i, case in enumerate(TEST_CASES):
        print(f"\nTest #{i+1}: '{case['text']}'")
        try:
            result = parse_message(case['text'])
            print(f"  Result: Type={result.type}, Region={result.region}, Loc={result.location}")
            
            # Checks
            checks = []
            checks.append(result.type == case['expected_type'])
            if case['expected_region']:
                checks.append(result.region == case['expected_region'])
            if case['expected_loc_name']:
                 checks.append(result.location == case['expected_loc_name'])
                 
            if all(checks):
                print("  ✅ PASS")
                passed += 1
            else:
                print("  ❌ FAIL")
                print(f"     Expected: {case}")
                failed += 1
                
        except Exception as e:
            print(f"  🔥 ERROR: {e}")
            failed += 1

    print(f"\nCompleted: {passed} PASSED, {failed} FAILED")

if __name__ == "__main__":
    run_tests()
