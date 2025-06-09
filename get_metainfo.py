import requests
import json

# URL эндпойнта
url = "https://scanner.tradingview.com/crypto/metainfo"

# Заголовки запроса
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Cookie": ""
}

try:
    # Отправка GET-запроса
    response = requests.get(url, headers=headers)

    # Подготовка данных для сохранения
    response_data = {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "body": response.text
    }

    # Попытка разобрать JSON, если ответ валидный
    try:
        response_data["body"] = response.json()
    except ValueError:
        pass  # Сохраняем как текст, если не JSON

    # Сохранение ответа в файл
    with open("metainfo_response.json", "w", encoding="utf-8") as f:
        json.dump(response_data, f, indent=2, ensure_ascii=False)

    print(f"Ответ сохранен в metainfo_response.json (статус: {response.status_code})")

except requests.exceptions.RequestException as e:
    # Сохранение ошибки в файл
    error_data = {
        "error": str(e)
    }
    with open("metainfo_response.json", "w", encoding="utf-8") as f:
        json.dump(error_data, f, indent=2)
    print(f"Ошибка при запросе, детали сохранены в metainfo_response.json: {e}")