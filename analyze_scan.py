#!/usr/bin/env python3
import sys
import json
from collections import Counter

def iterate_json(path):
    """Поддерживает два формата:
       1) Один большой JSON-массив: [ {...}, {...}, ... ]
       2) NDJSON — по одной JSON-записи в строке.
    """
    with open(path, 'r', encoding='utf-8') as f:
        first = f.read(1)
        f.seek(0)
        if first == '[':
            # большой массив
            arr = json.load(f)
            for obj in arr:
                yield obj
        else:
            # предполагаем NDJSON
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)

def main():
    if len(sys.argv) != 2:
        print("Usage: python analyze_scan.py path/to/scan.json")
        sys.exit(1)

    path = sys.argv[1]
    total = 0
    key_counter = Counter()
    len_counter = Counter()
    sample = None

    for obj in iterate_json(path):
        total += 1
        # структура ответов TV: { "totalCount": N, "data": [ { "s": "...", "d": [v1, v2,...] }, ... ] }
        if total == 1:
            sample = obj
        data = obj.get("data", [])
        for row in data:
            d = row.get("d", [])
            len_counter[len(d)] += 1
        # пределимся по первым 10000 записям
        if total >= 10000:
            break

    print(f"Всего объектов (проверено первых {total}): {obj.get('totalCount', '—')} (поле totalCount из последнего объекта)")
    print("Число значений в поле d (первые 10 000 объектов):")
    for length, cnt in len_counter.most_common():
        print(f"  {length} полей → {cnt} раз")

    print("\nПример структуры первого объекта:")
    print(json.dumps(sample, ensure_ascii=False, indent=2)[:1000] + "…")

if __name__ == '__main__':
    main()
