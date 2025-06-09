#!/usr/bin/env python3
# script3_v3.py — полный обход полей → TSV с табами

import json, time, sys, requests, pathlib
from tqdm import tqdm

TICKER    = sys.argv[1] if len(sys.argv) > 1 else "BINANCE:BTCUSDT"
META_FILE = "metainfo_response_raw.json"
OUT_TSV   = "field_status_structured.tsv"
DELAY     = 0.08
BASE      = "https://scanner.tradingview.com/crypto"
HEADERS   = {"User-Agent": "tv-scan/tsv/2025"}

# ─── Чтение полей ───────────────────────────────────────────────────
raw = json.loads(pathlib.Path(META_FILE).read_text(encoding="utf-8"))
fields_arr = raw.get("body", {}).get("fields") or raw.get("fields")
ALL_FIELDS = [f["n"] for f in fields_arr]

def split_field(full_field):
    if "|" in full_field:
        base, tf = full_field.split("|", 1)
        return base, tf
    return full_field, ""

def probe(column: str):
    payload = {
        "symbols": {"tickers": [TICKER]},
        "columns": [column]
    }
    try:
        r = requests.post(f"{BASE}/scan", json=payload, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            if r.status_code == 400 and "invalid range" in r.text.lower():
                return "empty", ""
            return "error", ""
        data = r.json().get("data")
        if not data or not data[0]["d"]:
            return "empty", ""
        val = data[0]["d"][0]
        return ("ok" if val is not None else "null"), val
    except Exception:
        return "error", ""

# ─── Сканирование и запись TSV ───────────────────────────────────────
with open(OUT_TSV, "w", encoding="utf-8") as f:
    f.write("ticker\tfield\ttimeframe\tfull_field\tstatus\tvalue\n")
    for fld in tqdm(ALL_FIELDS, desc=f"Scanning {TICKER}"):
        base, tf = split_field(fld)
        status, val = probe(fld)
        f.write(f"{TICKER}\t{base}\t{tf}\t{fld}\t{status}\t{val}\n")
        time.sleep(DELAY)

print(f"✓ TSV сохранён: {OUT_TSV}")
