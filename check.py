import json

# === Загрузка исходного файла ===
with open("supported.json", "r", encoding="utf-8") as f:
    supported = json.load(f)

# === Деление на 2 группы ===
base_indicators = {}
timeframe_indicators = {}

for key, value in supported.items():
    if "|" in key:
        timeframe_indicators[key] = value
    else:
        base_indicators[key] = value

# === Сохранение ===
with open("base_indicators.json", "w", encoding="utf-8") as f:
    json.dump(base_indicators, f, indent=2)

with open("indicators_with_timeframe.json", "w", encoding="utf-8") as f:
    json.dump(timeframe_indicators, f, indent=2)

# === Результат ===
print(f"✅ Готово.")
print(f"• Без таймфрейма: {len(base_indicators)} полей → base_indicators.json")
print(f"• С таймфреймом: {len(timeframe_indicators)} полей → indicators_with_timeframe.json")
