import json
import requests
from time import sleep

API_URL = "https://scanner.tradingview.com/crypto/scan"
HEADERS = {"Content-Type": "application/json"}
TICKER = "BINANCE:BTCUSDT"
BATCH_SIZE = 10
DELAY = 0.5

with open("field_categories.json", "r", encoding="utf-8") as f:
    raw_categories = json.load(f)

fields_to_check = []
for category, items in raw_categories.items():
    fields_to_check.extend(items)
fields_to_check = sorted(set(fields_to_check))

numeric_fields = []
supported = {}
unsupported = []
nulls = []

print(f"🧪 Total fields to check: {len(fields_to_check)}")

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
                elif isinstance(value, (int, float)):
                    print(f"✅ {field}: {value} (numeric)")
                    numeric_fields.append(field)
                    supported[field] = value
                else:
                    print(f"⏩ {field}: {type(value).__name__} — SKIP")
        elif "error" in data:
            print(f"❌ Error: {data['error']}")
            unsupported.extend(batch)
        else:
            print("❌ Unknown response format")
            unsupported.extend(batch)
    except Exception as e:
        print(f"🔥 Network error: {e}")
        unsupported.extend(batch)

    sleep(DELAY)

# Save only numeric fields
with open("numeric_fields.json", "w", encoding="utf-8") as f:
    json.dump(numeric_fields, f, indent=2)

with open("supported_numeric.json", "w", encoding="utf-8") as f:
    json.dump(supported, f, indent=2)

with open("nulls.json", "w", encoding="utf-8") as f:
    json.dump(nulls, f, indent=2)

with open("unsupported.json", "w", encoding="utf-8") as f:
    json.dump(unsupported, f, indent=2)

print("\n✅ Done.")
print(f"Numeric: {len(numeric_fields)}")
print(f"Null: {len(nulls)}")
print(f"Unsupported: {len(unsupported)}")
