#!/usr/bin/env python3
# market.py  –  полный обход рынков TV  (батчи 20 полей)

import os, sys, json, time, argparse, itertools, csv, random, requests
from tqdm import tqdm

MARKETS = ["crypto", "forex", "stocks", "futures",
           "index", "economic", "cfd", "bond"]

BASE = "https://scanner.tradingview.com"
UA   = "tv-fullscan/2025"
BATCH = 20                       # ← только 20 полей за раз
PAUSE = 0.08                     # базовая задержка между батчами
RESULTS = "results"

session = requests.Session()
session.headers.update({"User-Agent": UA})

# ─ helpers ───────────────────────────────────────────────────────────
def fetch_json(url, method="GET", payload=None, timeout=20):
    for _ in range(4):
        try:
            r = session.get(url, timeout=timeout) if method == "GET" \
                else session.post(url, json=payload or {}, timeout=timeout)
            if r.status_code == 429:
                time.sleep(5); continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = {"error": str(e)}
            time.sleep(5)
    return last                            # после 4-х попыток

def split_field(name):
    return name.split("|", 1) if "|" in name else (name, "")

def chunked(seq, n):
    it = iter(seq)
    while True:
        batch = list(itertools.islice(it, n))
        if not batch: break
        yield batch

# ─ основной скан по рынку ────────────────────────────────────────────
def scan_market(market, ticker_hint, delay, resume):
    path = os.path.join(RESULTS, market)
    os.makedirs(path, exist_ok=True)
    out_tsv = os.path.join(path, "field_status.tsv")

    meta = fetch_json(f"{BASE}/{market}/metainfo")
    if "error" in meta:
        print(f"  ⨯ metainfo error: {meta['error']}"); return None

    scan0 = fetch_json(f"{BASE}/{market}/scan", method="POST", payload={})
    if "error" in scan0 or not scan0.get("data"):
        print("  ⨯ scan {} пуст"); return None
    ticker = ticker_hint or scan0["data"][0]["s"]
    exchange = ticker.split(":", 1)[0]

    fields_arr  = meta.get("body", {}).get("fields") or meta.get("fields", [])
    all_fields  = [f["n"] for f in fields_arr]

    done = set()
    if resume and os.path.exists(out_tsv):
        with open(out_tsv, encoding="utf-8") as f:
            next(f)
            for line in f:
                done.add(line.split("\t", 3)[3])      # full_field

    ok=null=empty=err=0
    mode = "a" if done else "w"
    with open(out_tsv, mode, encoding="utf-8", newline="") as f:
        if mode == "w":
            f.write("market\tticker\texchange\tfield\ttimeframe\tfull_field\tstatus\tvalue\n")

        for batch in tqdm(list(chunked(all_fields, BATCH)), desc=f"{market:8s}", leave=False):
            batch = [fld for fld in batch if fld not in done]
            if not batch: continue
            js = fetch_json(f"{BASE}/{market}/scan", method="POST",
                            payload={"symbols":{"tickers":[ticker]},
                                     "columns": batch})
            if "error" in js:
                # помечаем весь батч как error
                for fld in batch:
                    base, tf = split_field(fld)
                    f.write(f"{market}\t{ticker}\t{exchange}\t{base}\t{tf}\t{fld}\terror\t\n")
                    err+=1
                time.sleep(delay+random.uniform(0,delay)); continue

            row = js["data"][0]["d"]
            for fld, val in zip(batch, row):
                base, tf = split_field(fld)
                if val is None:
                    status="null"; null+=1
                else:
                    status="ok";   ok+=1
                f.write(f"{market}\t{ticker}\t{exchange}\t{base}\t{tf}\t{fld}\t{status}\t{val}\n")
            time.sleep(delay+random.uniform(0,delay))

    return {"market":market,"ticker":ticker,
            "total_fields":len(all_fields),
            "ok":ok,"null":null,"empty":empty,"error":err}

# ─ точка входа ───────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", help="фиксированный тикер для всех рынков")
    ap.add_argument("--delay",  type=float, default=PAUSE)
    ap.add_argument("--resume", action="store_true",
                    help="дописывать, пропуская уже обработанные поля")
    args = ap.parse_args()

    os.makedirs(RESULTS, exist_ok=True)
    summaries=[]
    for m in MARKETS:
        print(f"\n▶ {m.upper()}")
        s = scan_market(m, args.ticker, args.delay, args.resume)
        if s: summaries.append(s)

    with open(os.path.join(RESULTS, "markets_summary.tsv"), "w", encoding="utf-8") as f:
        f.write("market\tticker\ttotal_fields\tok\tnull\terror\n")
        for s in summaries:
            f.write(f"{s['market']}\t{s['ticker']}\t{s['total_fields']}\t"
                    f"{s['ok']}\t{s['null']}\t{s['error']}\n")
    print("\n✓ Полный скан завершён. Файлы — в папке 'results'.")

if __name__ == "__main__":
    try:
        import requests   # проверка зависимостей
    except ImportError:
        sys.exit("pip install requests tqdm")
    main()
