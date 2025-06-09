import json
import requests
from time import sleep

API_URL = "https://scanner.tradingview.com/crypto/scan"
HEADERS = {"Content-Type": "application/json"}
TICKER = "BINANCE:BTCUSDT"
BATCH_SIZE = 10
DELAY = 0.5

# === Загрузка: поле-список из всех категорий ===
with open("field_categories.json", "r", encoding="utf-8") as f:
    raw_categories = json.load(f)

# === Извлечение всех полей из всех категорий ===
fields_to_check = []
for category, items in raw_categories.items():
    fields_to_check.extend(items)

# Убираем дубликаты
fields_to_check = sorted(set(fields_to_check))

# === Результаты ===
supported = {}
nulls = []
unsupported = []

print(f"🧪 Всего полей для проверки: {len(fields_to_check)}")

# === Пакетная отправка ===
for i in range(0, len(fields_to_check), BATCH_SIZE):
    batch = fields_to_check[i:i + BATCH_SIZE]

    payload = {
        "symbols": {"tickers": [TICKER]},
        "columns": batch
    }

    try:
        res = requests.post(API_URL, headers=HEADERS, json=payload)
        data = res.json()

        if "data" in data and data["data"]:
            values = data["data"][0]["d"]
            for field, value in zip(batch, values):
                if value is None:
                    print(f"⚠️ {field}: null")
                    nulls.append(field)
                else:
                    print(f"✅ {field}: {value}")
                    supported[field] = value
        elif "error" in data:
            print(f"❌ Ошибка: {data['error']}")
            unsupported.extend(batch)
        else:
            print("❌ Неизвестный формат ответа")
            unsupported.extend(batch)

    except Exception as e:
        print(f"🔥 Ошибка сети: {e}")
        unsupported.extend(batch)

    sleep(DELAY)

# === Сохраняем ===
with open("supported.json", "w", encoding="utf-8") as f:
    json.dump(supported, f, indent=2)

with open("nulls.json", "w", encoding="utf-8") as f:
    json.dump(nulls, f, indent=2)

with open("unsupported.json", "w", encoding="utf-8") as f:
    json.dump(unsupported, f, indent=2)

print("\n✅ Готово.")
print(f"Поддерживаются: {len(supported)}")
print(f"Null: {len(nulls)}")
print(f"Неизвестны: {len(unsupported)}")
