import json

# Шаг 1: Загрузка всех полей из supported_numeric.json
with open("supported_numeric.json") as f:
    all_keys = json.load(f).keys()

with_timeframe_set = set()
without_timeframe_set = set()

# Шаг 2: Разделение
for key in all_keys:
    if "|1" in key or "|5" in key or "|15" in key or "|30" in key or "|60" in key or "|120" in key or "|240" in key or "|1W" in key or "|1M" in key or "|D" in key:
        indicator_base = key.split("|")[0]
        with_timeframe_set.add(indicator_base)
    else:
        without_timeframe_set.add(key)

# Шаг 3: Очистка перекрытий (удаляем из безтаймфреймовых те, что есть в таймфреймовых)
cleaned_without_timeframe = sorted(without_timeframe_set - with_timeframe_set)
cleaned_with_timeframe = sorted(with_timeframe_set)

# Шаг 4: Сохранение
with open("filtered_indicators_without_timeframes.json", "w") as f:
    json.dump(cleaned_without_timeframe, f, indent=2)

with open("filtered_indicators_with_timeframes.json", "w") as f:
    json.dump(cleaned_with_timeframe, f, indent=2)

print("✅ Обработка завершена.")
