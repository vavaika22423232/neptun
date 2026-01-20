import re

# Test message
test_msg = """⚠️Миколаївщина:
9х БпЛА пролетіли Радушне курсом на Новий Буг

⚠️Черкащина:
1х БПЛА в напрямку Мошни
1х БПЛА в районі Корсунь-Шевченківського
1х БПЛА на Гельмязів

Український | ППОшник"""

print("Testing message parsing:")
print("=" * 50)
print(test_msg)
print("=" * 50)

# Test pattern matching
pat_count_course = re.compile(
    r'^(\d+)\s*[xх]?\s*бпла(?:\s+пролетіли)?.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?'
    r'([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)',
    re.IGNORECASE
)

pat_napramku = re.compile(
    r'(\d+)?[xх]?\s*бпла\s+(?:в|у)\s+напрямку\s+'
    r'([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)',
    re.IGNORECASE
)

pat_area = re.compile(
    r'(\d+)?[xх]?\s*бпла\s+в\s+районі\s+'
    r'([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)',
    re.IGNORECASE
)

pat_simple = re.compile(
    r'(\d+)?[xх]?\s*бпла\s+на\s+'
    r'([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)',
    re.IGNORECASE
)

lines = test_msg.split('\n')
for i, line in enumerate(lines, 1):
    line_lower = line.lower()
    if 'бпла' in line_lower:
        print(f"\nLine {i}: {line}")

        m1 = pat_count_course.search(line_lower)
        if m1:
            print(f"  ✓ pat_count_course: count={m1.group(1)}, city='{m1.group(2)}'")

        m2 = pat_napramku.search(line_lower)
        if m2:
            count_str = m2.group(1) if m2.group(1) else 'None'
            print(f"  ✓ pat_napramku: count={count_str}, city='{m2.group(2)}'")

        m3 = pat_area.search(line_lower)
        if m3:
            count_str = m3.group(1) if m3.group(1) else 'None'
            print(f"  ✓ pat_area: count={count_str}, city='{m3.group(2)}'")

        m4 = pat_simple.search(line_lower)
        if m4:
            count_str = m4.group(1) if m4.group(1) else 'None'
            print(f"  ✓ pat_simple: count={count_str}, city='{m4.group(2)}'")

print("\n" + "=" * 50)
print("Pattern matching test complete")
