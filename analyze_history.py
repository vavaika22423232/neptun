# Анализ истории сообщений и меток для ML/AI
# Использование: python analyze_history.py
import json
from collections import Counter, defaultdict

messages = []
with open('history.jsonl', encoding='utf-8') as f:
    for line in f:
        try:
            messages.append(json.loads(line))
        except Exception:
            continue

print(f"Всего сообщений: {len(messages)}")

# Частота топонимов
places = Counter()
for m in messages:
    text = m.get('text', '')
    for word in text.split():
        if word.istitle() and len(word) > 2:
            places[word] += 1
print("\nТоп-10 топонимов:")
for place, cnt in places.most_common(10):
    print(f"{place}: {cnt}")

# Распределение confidence
conf_hist = defaultdict(int)
for m in messages:
    conf = round(m.get('confidence', 0), 2)
    conf_hist[conf] += 1
print("\nРаспределение confidence:")
for conf in sorted(conf_hist):
    print(f"{conf}: {conf_hist[conf]}")

# Пример подготовки данных для ML (X, y)
X = [m['text'] for m in messages]
y = [(m['lat'], m['lng']) for m in messages]
print(f"\nПример X[0]: {X[0] if X else ''}")
print(f"Пример y[0]: {y[0] if y else ''}")

# Можно использовать X, y для обучения ML-модели (например, CatBoost, sklearn, LLM)
