import requests
import json
from pathlib import Path
from collections import Counter

# Файл с описанием обнаруженных эндпоинтов
discovered_file = Path("discovered_all.json")
# Папка для сохранения результатов
output_dir = Path("responses")
output_dir.mkdir(exist_ok=True)

# Загрузка списка эндпоинтов
with discovered_file.open(encoding="utf-8") as f:
    endpoints = json.load(f)

# Общие заголовки
headers = {
    "User-Agent": "tv-endpoint-checker/2025",
    "Accept": "application/json",
}

results = []

# Проверяем каждый эндпоинт
for ep in endpoints:
    url = ep.get("url")
    method = ep.get("method", "GET").upper()
    scope = ep.get("scope", "root") or "root"
    name = ep.get("endpoint")
    print(f"Checking {method} {url}...")
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=15)
        else:
            resp = requests.post(url, json={}, headers=headers, timeout=15)

        # Попытка разобрать JSON
        try:
            body = resp.json()
        except ValueError:
            body = resp.text

        record = {
            "scope": scope,
            "endpoint": name,
            "method": method,
            "url": url,
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "body": body
        }
    except requests.RequestException as e:
        record = {
            "scope": scope,
            "endpoint": name,
            "method": method,
            "url": url,
            "error": str(e)
        }

    # Сохраняем JSON-ответ для данного эндпоинта
    out_file = output_dir / f"{scope}_{name}.json"
    with out_file.open("w", encoding="utf-8") as wf:
        json.dump(record, wf, ensure_ascii=False, indent=2)
    results.append(record)

# Сохраняем сводный файл
summary_file = output_dir / "summary.json"
with summary_file.open("w", encoding="utf-8") as sf:
    json.dump(results, sf, ensure_ascii=False, indent=2)

# Печать краткого отчета по статусам
status_counter = Counter(rec.get('status_code', 'error') for rec in results)
print("\nSummary by status:")
for status, count in status_counter.items():
    print(f"  {status}: {count}")

# Анализ топ-уровневых ключей тел ответов
keys_per_endpoint = {}
for rec in results:
    body = rec.get('body')
    if isinstance(body, dict):
        keys_per_endpoint.setdefault(rec['endpoint'], set()).update(body.keys())

print("\nTop-level keys per endpoint:")
for ep, keys in keys_per_endpoint.items():
    print(f"  {ep}: {sorted(keys)}")

print(f"\nDone. Detailed responses saved in '{output_dir.resolve()}', краткий отчет выше.")
