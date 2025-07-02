# Тестирование TradingView OpenAPI Generator

## Запуск тестов с реальным API

```bash
pytest --real-api --maxfail=3 -v
pytest --cov=src/tv_generator --cov-report=term-missing --real-api
```

- Все тесты используют реальные TradingView API и реальные файлы.
- Моки и патчи запрещены.
- Для запуска требуется наличие всех файлов в data/metainfo/ и data/scan/ для рынков из data/markets.json.
