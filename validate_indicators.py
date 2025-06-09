import json
import requests
import time

SYMBOL = "BINANCE:BTCUSDT.P"
BATCH_SIZE = 20
DELAY = 0.8  # seconds

with open("numeric_fields.json") as f:
    all_fields = json.load(f)

with open("supported_numeric.json") as f:
    supported_fields = set(json.load(f))

fields_to_check = [f for f in all_fields if f in supported_fields]
valid_fields = []

for i in range(0, len(fields_to_check), BATCH_SIZE):
    batch = fields_to_check[i:i + BATCH_SIZE]
    payload = {
        "symbols": {
            "tickers": [SYMBOL]
        },
        "columns": batch
    }

    try:
        res = requests.post("https://scanner.tradingview.com/crypto/scan", json=payload)
        res.raise_for_status()
        data = res.json()

        if data["data"] and data["data"][0]["s"] == SYMBOL:
            values = data["data"][0]["d"]
            for f, val in zip(batch, values):
                if val not in [None, 0, 0.0, "", "null", "NaN"]:
                    valid_fields.append(f)
    except Exception as e:
        print(f"[ERROR] Batch {i // BATCH_SIZE}: {e}")

    time.sleep(DELAY)

with open("filtered_valid_active_numeric.json", "w") as out:
    json.dump(valid_fields, out, indent=2)

print(f"[DONE] Valid fields found: {len(valid_fields)}")
