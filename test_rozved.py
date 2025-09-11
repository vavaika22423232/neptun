#!/usr/bin/env python3

"""
Test reconnaissance UAV detection
"""

def test_rozved_logic():
    """Test the logic that should detect reconnaissance UAVs"""
    
    def test_classify(th: str):
        """Simplified version of the classify function for testing"""
        l = th.lower()
        # Recon / розвід дрони -> use pvo icon (rozved.png) per user request
        if 'розвід' in l or 'розвідуваль' in l or 'развед' in l:
            return 'rozved', 'rozved.png'
        # Default fallback
        return 'default', 'default.png'
    
    test_messages = [
        "👁️ Хотінь (Сумська обл.)\nАктивність розвідувальних БПЛА. Можлива робота ППО.",
        "👁️ Суми (Сумська обл.)\nАктивність розвідувальних БПЛА. Можлива робота ППО.",
        "Активність розвідувальних БпЛА у напрямку Чернігова",
        "Розвідувальний дрон зафіксований над Київщиною",
        "розвід БпЛА над областю"
    ]
    
    print("🔍 Testing reconnaissance UAV detection logic...")
    print("-" * 60)
    
    for i, message in enumerate(test_messages, 1):
        print(f"Test {i}: {message[:50]}...")
        threat_type, icon_file = test_classify(message)
        print(f"   Result: threat_type='{threat_type}', icon='{icon_file}'")
        
        if threat_type == 'rozved':
            print(f"   ✅ Correctly detected as reconnaissance UAV")
        else:
            print(f"   ❌ Expected 'rozved', got '{threat_type}'")
        print()

def test_frontend_support():
    """Test if frontend has rozved support"""
    print("🖥️ Testing frontend rozved support...")
    print("-" * 60)
    
    # Check if rozved.png files exist
    import os
    
    files_to_check = [
        "static/rozved.png",
        "static/placeholders/rozved.png"
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path} exists")
            # Check file info
            result = os.popen(f'file "{file_path}"').read().strip()
            print(f"      {result}")
        else:
            print(f"   ❌ {file_path} missing")
        
    print()

if __name__ == "__main__":
    test_rozved_logic()
    test_frontend_support()
