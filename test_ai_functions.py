#!/usr/bin/env python3
"""Test all AI functions in the NEPTUN app."""

import os
import sys

# Set API key from .env if not already set
if not os.environ.get('GROQ_API_KEY'):
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith('GROQ_API_KEY='):
                    os.environ['GROQ_API_KEY'] = line.split('=', 1)[1].strip()
                    break

# Import AI functions from app
sys.path.insert(0, os.path.dirname(__file__))
from app import (
    GROQ_ENABLED,
    analyze_message_comprehensive_ai,
    classify_threat_with_ai,
    extract_location_with_groq_ai,
    extract_trajectory_with_ai,
    moderate_chat_message_with_ai,
    summarize_message_with_ai,
)


def test_location_extraction():
    """Test AI location extraction."""
    print("\n" + "="*60)
    print("🗺️  TEST: extract_location_with_groq_ai()")
    print("="*60)

    test_cases = [
        "Дніпропетровщина: БпЛА маневрує в районі Юріївки",
        "БпЛА в Павлоградському районі курсом на Тернівку",
        "Харків: вибухи в Київському районі",
    ]

    for msg in test_cases:
        result = extract_location_with_groq_ai(msg)
        print(f"\n📝 {msg[:50]}...")
        if result:
            print(f"   ✅ city={result.get('city')}, oblast={result.get('oblast')}, district={result.get('district')}")
        else:
            print("   ❌ No result")

def test_trajectory():
    """Test AI trajectory extraction."""
    print("\n" + "="*60)
    print("🛤️  TEST: extract_trajectory_with_ai()")
    print("="*60)

    test_cases = [
        "БпЛА з півночі на Суми",
        "Група Шахедів над Вінницькою областю летять на Київ",
        "5 БпЛА в районі Умані, курс на Черкаси",
    ]

    for msg in test_cases:
        result = extract_trajectory_with_ai(msg)
        print(f"\n📝 {msg[:50]}...")
        if result:
            print(f"   ✅ {result.get('source_name')} → {result.get('target_name')}")
        else:
            print("   ❌ No result")

def test_threat_classification():
    """Test AI threat classification."""
    print("\n" + "="*60)
    print("⚠️  TEST: classify_threat_with_ai()")
    print("="*60)

    test_cases = [
        "🛵 Група ударних БпЛА (Шахеди) на Полтавщині",
        "🚀 Балістична загроза з півдня! Час підльоту 2 хвилини",
        "💣 КАБи по Харкову з Бєлгородського напрямку",
        "Вибухи в Одесі, працює ППО",
    ]

    for msg in test_cases:
        result = classify_threat_with_ai(msg)
        print(f"\n📝 {msg[:50]}...")
        if result:
            print(f"   {result.get('emoji')} {result.get('threat_type')} (priority {result.get('priority')})")
            print(f"   📋 {result.get('description_short')}")
        else:
            print("   ❌ No result")

def test_summarization():
    """Test AI message summarization."""
    print("\n" + "="*60)
    print("📋 TEST: summarize_message_with_ai()")
    print("="*60)

    long_message = """
    ⚠️ УВАГА! Масований обстріл!
    Зафіксовано пуск балістичних ракет з Криму.
    Ймовірні цілі: Одеська, Миколаївська, Херсонська області.
    Час підльоту орієнтовно 5-7 хвилин.
    Всім перебувати в укриттях до відбою тривоги!
    Слідкуйте за офіційними повідомленнями.
    """

    result = summarize_message_with_ai(long_message)
    print(f"\n📝 Original ({len(long_message)} chars):")
    print(f"   {long_message[:100]}...")
    if result:
        print(f"\n✅ Summary: {result.get('summary')}")
        print(f"   Urgency: {result.get('urgency')}")
        print(f"   Key info: {result.get('key_info')}")
    else:
        print("   ❌ No result")

def test_chat_moderation():
    """Test AI chat moderation."""
    print("\n" + "="*60)
    print("🛡️  TEST: moderate_chat_message_with_ai()")
    print("="*60)

    test_cases = [
        ("Всім безпеки!", "Kyivan"),  # Safe
        ("Де вибухи?", "Curious"),  # Safe question
        ("Слава Україні!", "Patriot"),  # Safe
        ("Купіть біткоїн тут: spam.com", "Spammer"),  # Spam
    ]

    for msg, nickname in test_cases:
        result = moderate_chat_message_with_ai(msg, nickname)
        print(f"\n📝 [{nickname}]: {msg}")
        if result:
            if result.get('is_safe'):
                print("   ✅ Safe")
            else:
                print(f"   🚫 Blocked: {result.get('reason')} [{result.get('category')}]")
        else:
            print("   ✅ Default safe (no AI)")

def test_comprehensive():
    """Test comprehensive AI analysis."""
    print("\n" + "="*60)
    print("🔬 TEST: analyze_message_comprehensive_ai()")
    print("="*60)

    msg = "🛵 Група з 5 Шахедів над Вінницькою областю, курс на Київ"

    result = analyze_message_comprehensive_ai(msg)
    print(f"\n📝 {msg}")

    if result:
        print("\n✅ COMPREHENSIVE ANALYSIS:")
        loc = result.get('location', {})
        print(f"   📍 Location: city={loc.get('city')}, oblast={loc.get('oblast')}")

        traj = result.get('trajectory', {})
        print(f"   🛤️  Trajectory: {traj.get('source_name')} → {traj.get('target_name')}")

        threat = result.get('threat', {})
        print(f"   ⚠️  Threat: {threat.get('emoji')} {threat.get('threat_type')} (priority {threat.get('priority')})")

        summ = result.get('summary', {})
        print(f"   📋 Summary: {summ.get('text')} [{summ.get('urgency')}]")
    else:
        print("   ❌ No result")

def main():
    print("="*60)
    print("🤖 NEPTUN AI FUNCTIONS TEST")
    print("="*60)

    if GROQ_ENABLED:
        print("✅ Groq AI is ENABLED")
    else:
        print("❌ Groq AI is DISABLED - tests will return None")
        print("   Set GROQ_API_KEY environment variable to enable")
        return

    # Run all tests
    test_location_extraction()
    test_trajectory()
    test_threat_classification()
    test_summarization()
    test_chat_moderation()
    test_comprehensive()

    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETED")
    print("="*60)

if __name__ == '__main__':
    main()
