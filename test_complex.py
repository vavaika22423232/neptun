import re

# Test message
test_msg = """⚠️Одещина:
4х БПЛА в напрямку Буялика

⚠️Миколаївщина:
8х БПЛА на/через Баштанку в напрямку Дорошівки
4х БПЛА на Возсіятське
2х БпЛА в бік Володимирівки з Херсонщини

Український | ППОшник"""

print("Testing message parsing:")
print("=" * 70)
print(test_msg)
print("=" * 70)

# Check if it matches UAV course trigger
lower = test_msg.lower()
print(f"\n'бпла' in message: {'бпла' in lower}")
print(f"'курс' in message: {'курс' in lower}")
print(f"'в районі' in message: {'в районі' in lower}")
print(f"'в напрямку' in message: {'в напрямку' in lower}")

# Check regex pattern for simple "на"
has_simple_na = bool(re.search(r'\d+\s*[xх]?\s*бпла\s+на\s+', lower))
print(f"Has simple 'на' pattern: {has_simple_na}")

should_trigger = 'бпла' in lower and ('курс' in lower or 'в районі' in lower or 'в напрямку' in lower or has_simple_na)
print(f"\nShould trigger UAV course parser: {should_trigger}")

# Test patterns
pat_napramku = re.compile(r'(\d+)?[xх]?\s*бпла\s+(?:в|у)\s+напрямку\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
pat_simple_na = re.compile(r'(\d+)?[xх]?\s*бпла\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
pat_vik = re.compile(r'(\d+)?[xх]?\s*бпла\s+в\s+бік\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)

lines = test_msg.split('\n')
print("\n" + "=" * 70)
for i, line in enumerate(lines, 1):
    line_lower = line.lower()
    if 'бпла' in line_lower:
        print(f"\nLine {i}: {line}")
        print(f"Line lower: {line_lower}")

        m1 = pat_napramku.search(line_lower)
        if m1:
            print(f"  ✓ pat_napramku: count={m1.group(1)}, city='{m1.group(2)}'")

        m2 = pat_simple_na.search(line_lower)
        if m2:
            print(f"  ✓ pat_simple_na: count={m2.group(1)}, city='{m2.group(2)}'")

        m3 = pat_vik.search(line_lower)
        if m3:
            print(f"  ✓ pat_vik: count={m3.group(1)}, city='{m3.group(2)}'")

        if not (m1 or m2 or m3):
            print("  ✗ NO PATTERN MATCHED!")
            print("  Problem: Complex line with 'на/через' or other complex pattern")

print("\n" + "=" * 70)
