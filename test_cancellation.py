#!/usr/bin/env python3

"""
Test threat cancellation message detection
"""

def test_cancellation_patterns():
    """Test various cancellation message patterns"""
    
    test_messages = [
        "🟢 Очаків (Миколаївська обл.)\nВідбій загрози застосування БПЛА. Будьте обережні!",
        "Відбій тривоги у Миколаївській області",
        "Відбій загрози обстрілу у Харківській області", 
        "🔴 Очаків (Миколаївська обл.)\nЗагроза застосування БПЛА. Негайно прямуйте в укриття!",
        "🟢 Київ\nВідбій повітряної тривоги",
    ]
    
    print("🔍 Testing threat cancellation detection...")
    print("-" * 70)
    
    for i, message in enumerate(test_messages, 1):
        print(f"Test {i}: {message[:50]}...")
        
        # Check for cancellation patterns
        message_lower = message.lower()
        
        is_cancellation = False
        cancellation_reasons = []
        
        # Check various cancellation patterns
        if 'відбій загрози застосування' in message_lower:
            is_cancellation = True
            cancellation_reasons.append("відбій загрози застосування")
        
        if 'відбій загрози обстр' in message_lower:
            is_cancellation = True
            cancellation_reasons.append("відбій загрози обстр")
            
        if 'відбій загрози бпла' in message_lower:
            is_cancellation = True
            cancellation_reasons.append("відбій загрози бпла")
        
        if 'відбій тривоги' in message_lower or 'відбій повітряної тривоги' in message_lower:
            is_cancellation = True  
            cancellation_reasons.append("відбій тривоги")
        
        # General pattern: відбій + (загрози | тривоги)
        if ('відбій' in message_lower and 
            any(cancel_word in message_lower for cancel_word in ['загрози', 'тривоги'])):
            if not is_cancellation:  # Don't double-count
                is_cancellation = True
                cancellation_reasons.append("відбій + (загрози|тривоги)")
        
        if '🟢' in message:
            cancellation_reasons.append("green circle emoji")
        
        if is_cancellation:
            print(f"   ✅ CANCELLATION detected: {', '.join(cancellation_reasons)}")
            print(f"   → Should be list_only=True, no map marker")
        else:
            print(f"   ❌ NOT cancellation - should create marker")
        
        print()

def test_message_processing():
    """Test the specific message processing logic"""
    
    test_message = "🟢 Очаків (Миколаївська обл.)\nВідбій загрози застосування БПЛА. Будьте обережні!"
    
    print("🔍 Testing specific message processing...")
    print("-" * 70)
    print(f"Message: {test_message}")
    print()
    
    # Extract components
    import re
    
    # Test the priority emoji pattern
    head = test_message.split('\n', 1)[0][:160]
    print(f"Head: {head}")
    
    general_emoji_pattern = r'^[^\w\s]*\s*([А-ЯІЇЄЁа-яіїєё\'\-\s]+)\s*\(([^)]*обл[^)]*)\)'
    general_emoji_match = re.search(general_emoji_pattern, head, re.IGNORECASE)
    
    if general_emoji_match:
        city = general_emoji_match.group(1).strip()
        oblast = general_emoji_match.group(2).strip()
        print(f"✅ Emoji pattern matched: city='{city}', oblast='{oblast}'")
    else:
        print("❌ Emoji pattern did not match")
    
    # Check UAV words
    uav_words = ['бпла', 'дрон', 'шахед', 'активність', 'загроза', 'тривога']
    found_uav_words = [word for word in uav_words if word in test_message.lower()]
    if found_uav_words:
        print(f"✅ UAV words found: {found_uav_words}")
    else:
        print("❌ No UAV words found")
    
    # Check cancellation logic
    text_lower = test_message.lower()
    is_cancellation = ('відбій загрози' in text_lower or 
                      'відбій тривоги' in text_lower or
                      ('відбій' in text_lower and 
                       any(cancel_word in text_lower for cancel_word in ['загрози', 'тривоги'])))
    
    if is_cancellation:
        print("✅ Cancellation logic triggered")
        print("   Expected result: list_only=True, threat_type='alarm_cancel', no map marker")
    else:
        print("❌ Cancellation logic not triggered - would create marker!")
    
    print()

def test_both_types():
    """Test both threat and cancellation messages side by side"""
    
    print("🔍 Comparing threat vs cancellation messages...")
    print("-" * 70)
    
    threat_message = "🔴 Очаків (Миколаївська обл.)\nЗагроза застосування БПЛА. Негайно прямуйте в укриття!"
    cancel_message = "🟢 Очаків (Миколаївська обл.)\nВідбій загрози застосування БПЛА. Будьте обережні!"
    
    for msg_type, message in [("THREAT", threat_message), ("CANCEL", cancel_message)]:
        print(f"{msg_type}: {message[:50]}...")
        
        text_lower = message.lower()
        is_cancellation = ('відбій загрози' in text_lower or 
                          'відбій тривоги' in text_lower or
                          ('відбій' in text_lower and 
                           any(cancel_word in text_lower for cancel_word in ['загрози', 'тривоги'])))
        
        if is_cancellation:
            print(f"   → list_only=True, threat_type='alarm_cancel', NO map marker")
        else:
            print(f"   → regular marker with coordinates, threat classification")
        print()

if __name__ == "__main__":
    test_cancellation_patterns()
    test_message_processing()
    test_both_types()
