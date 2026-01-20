import re

# Test message
test_msg = """⚠️Кіровоградщина:
2х БпЛА в напрямку Рівного
1х БПЛА на Помічну

⚠️Миколаївщина:
12х БпЛА від Володимирівки до Братського

⚠️Одещина:
2х БпЛА на околицях Березівки
5х БпЛА в напрямку Ширяєвого та Троїцького

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
print(f"'в бік' in message: {'в бік' in lower}")

# Check regex pattern for simple "на"
has_simple_na = bool(re.search(r'\d+\s*[xх]?\s*бпла\s+на\s+', lower))
print(f"Has simple 'на' pattern: {has_simple_na}")

should_trigger = 'бпла' in lower and ('курс' in lower or 'в районі' in lower or 'в напрямку' in lower or 'в бік' in lower or has_simple_na)
print(f"\nShould trigger UAV course parser: {should_trigger}")

# Test patterns
pat_napramku = re.compile(r'(\d+)?[xх]?\s*бпла\s+(?:в|у)\s+напрямку\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
pat_simple_na = re.compile(r'(\d+)?[xх]?\s*бпла\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
pat_vid_do = re.compile(r'(\d+)?[xх]?\s*бпла\s+від\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)\s+до\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
pat_okolytsi = re.compile(r'(\d+)?[xх]?\s*бпла\s+на\s+околицях\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
pat_ta = re.compile(r'(\d+)?[xх]?\s*бпла\s+в\s+напрямку\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)\s+та\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)

lines = test_msg.split('\n')
print("\n" + "=" * 70)
for i, line in enumerate(lines, 1):
    line_lower = line.lower()
    if 'бпла' in line_lower:
        print(f"\nLine {i}: {line}")
        print(f"Line lower: {line_lower}")

        matched = False

        m1 = pat_napramku.search(line_lower)
        if m1:
            print(f"  ✓ pat_napramku: count={m1.group(1)}, city='{m1.group(2)}'")
            matched = True

        m2 = pat_simple_na.search(line_lower)
        if m2:
            print(f"  ✓ pat_simple_na: count={m2.group(1)}, city='{m2.group(2)}'")
            matched = True

        m3 = pat_vid_do.search(line_lower)
        if m3:
            print(f"  ✓ pat_vid_do: count={m3.group(1)}, city1='{m3.group(2)}', city2='{m3.group(3)}'")
            matched = True

        m4 = pat_okolytsi.search(line_lower)
        if m4:
            print(f"  ✓ pat_okolytsi: count={m4.group(1)}, city='{m4.group(2)}'")
            matched = True

        m5 = pat_ta.search(line_lower)
        if m5:
            print(f"  ✓ pat_ta: count={m5.group(1)}, city1='{m5.group(2)}', city2='{m5.group(3)}'")
            matched = True

        if not matched:
            print("  ✗ NO PATTERN MATCHED!")
            if 'від' in line_lower and 'до' in line_lower:
                print("    Hint: Line has 'від ... до' pattern")
            if 'околиц' in line_lower:
                print("    Hint: Line has 'околицях' pattern")
            if ' та ' in line_lower:
                print("    Hint: Line has 'та' (and) pattern for multiple cities")

print("\n" + "=" * 70)
