import json

# Подгружаем исходный файл с валидными индикаторами
with open('filtered_valid_active_numeric.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Если это список строк:
if isinstance(data, list) and isinstance(data[0], str):
    all_fields = data
# Если это список объектов ({"name": "RSI|60", ...}):
elif isinstance(data, list) and isinstance(data[0], dict) and "name" in data[0]:
    all_fields = [item["name"] for item in data]
else:
    raise ValueError("Unknown format for input file")

# Разделяем поля по наличию таймфрейма
no_timeframe = [field for field in all_fields if '|' not in field]
with_timeframe = [field for field in all_fields if '|' in field]

# Сохраняем результаты в отдельные JSON-файлы
with open('numeric_fields_no_timeframe.json', 'w', encoding='utf-8') as f:
    json.dump(sorted(no_timeframe), f, indent=2, ensure_ascii=False)

with open('numeric_fields_with_timeframe.json', 'w', encoding='utf-8') as f:
    json.dump(sorted(with_timeframe), f, indent=2, ensure_ascii=False)

print("Saved:")
print("numeric_fields_no_timeframe.json:", len(no_timeframe), "fields")
print("numeric_fields_with_timeframe.json:", len(with_timeframe), "fields")
