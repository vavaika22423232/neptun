#!/usr/bin/env python3
import re

def test_clean_subscription():
    text = """🚨Повітряна тривога

В зв'язку з активністю ворожої авіації, повітряна тривога оголошена в наступних областях:

🔺Харківська область
🔺Полтавська область


➡Підписатися
@ukraine_in_alarm_official_bot"""

    print("=== ORIGINAL TEXT ===")
    print(repr(text))
    
    # Clean subscription links
    cleaned_text = text
    if text:
        # markdown links [text](url)
        cleaned_text = re.sub(r'\*\*','', cleaned_text)
        cleaned_text = re.sub(r'\[([^\]]{0,80})\]\((https?://|t\.me/)[^\)]+\)', lambda m: (m.group(1) or '').strip(), cleaned_text, flags=re.IGNORECASE)
        # bare urls
        cleaned_text = re.sub(r'(https?://\S+|t\.me/\S+)', '', cleaned_text, flags=re.IGNORECASE)
        # collapse whitespace and drop empty lines
        cleaned = []
        for ln in cleaned_text.splitlines():
            ln2 = ln.strip()
            if not ln2:
                continue
            # pure decoration (arrows, bullets) or subscribe call to action lines
            if re.fullmatch(r'[>➡→\-\s·•]*', ln2):
                continue
            # remove any line that is just a subscribe CTA or starts with arrow+subscribe
            if re.search(r'(підписатись|підписатися|підписатися|подписаться|подпишись|subscribe)', ln2, re.IGNORECASE):
                continue
            # remove arrow+subscribe pattern specifically
            if re.search(r'[➡→>]\s*підписатися', ln2, re.IGNORECASE):
                continue
            cleaned.append(ln2)
        cleaned_text = '\n'.join(cleaned)
    
    print("\n=== CLEANED TEXT ===")
    print(repr(cleaned_text))
    print("\n=== CLEANED TEXT DISPLAY ===")
    print(cleaned_text)

if __name__ == "__main__":
    test_clean_subscription()
