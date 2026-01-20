import re

# Test message
test_msg = """⚠️Чернігівщина:
2х БпЛА на Бобровицю

Український | ППОшник"""

print("Testing message parsing:")
print("=" * 60)
print(test_msg)
print("=" * 60)

# Check if it matches UAV course trigger
lower = test_msg.lower()
print(f"\n'бпла' in message: {'бпла' in lower}")
print(f"'курс' in message: {'курс' in lower}")
print(f"'в районі' in message: {'в районі' in lower}")
print(f"\nShould trigger UAV course parser: {('бпла' in lower and ('курс' in lower or 'в районі' in lower))}")

# Test simple "на" pattern
pat_simple = re.compile(r'(\d+)?[xх]?\s*бпла\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)

lines = test_msg.split('\n')
for i, line in enumerate(lines, 1):
    line_lower = line.lower()
    if 'бпла' in line_lower:
        print(f"\nLine {i}: {line}")
        print(f"Line lower: {line_lower}")

        m = pat_simple.search(line_lower)
        if m:
            print(f"  ✓ pat_simple matched: count={m.group(1)}, city='{m.group(2)}'")
        else:
            print("  ✗ pat_simple did NOT match")
            print("  Trying to understand why...")
            if 'бпла' in line_lower and 'на' in line_lower:
                print("  Both 'бпла' and 'на' are present")
                # Check what's between them
                bpla_pos = line_lower.find('бпла')
                na_pos = line_lower.find('на')
                if na_pos > bpla_pos:
                    between = line_lower[bpla_pos:na_pos+2]
                    print(f"  Text from 'бпла' to 'на': '{between}'")

print("\n" + "=" * 60)
