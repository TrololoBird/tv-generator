# TradingView OpenAPI Generator

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Автоматизированный генератор OpenAPI 3.1.0 спецификаций для TradingView Scanner API.

## 🚀 Возможности

- **Модульная архитектура** - чистая структура кода с разделением ответственности
- **Асинхронные запросы** - быстрая обработка данных через `httpx`
- **Rate limiting** - автоматическое ограничение частоты запросов
- **Retry логика** - устойчивость к временным сбоям сети
- **Современный CLI** - интуитивный интерфейс с `typer` и `rich`
- **Полное логирование** - детальные логи с `loguru`
- **Типизация** - полная поддержка type hints
- **Тестирование** - покрытие тестами с `pytest`

## 📦 Установка

### Из исходного кода

```bash
git clone https://github.com/your-username/tv-generator.git
cd tv-generator
pip install -e .
```

### Для разработки

```bash
pip install -e ".[dev]"
```

## 🛠️ Использование

### CLI команды

```bash
# Информация о проекте
tvgen info

# Валидация конфигурации
tvgen validate

# Сбор данных со всех рынков
tvgen fetch-data

# Сбор данных с конкретного рынка
tvgen fetch-data --market us_stocks

# Сбор данных с подробным выводом
tvgen fetch-data --verbose

# Тестирование спецификаций
tvgen test-specs

# Генерация OpenAPI спецификаций
tvgen generate

# Справка
tvgen --help
```

### Программное использование

```python
import asyncio
from tv_generator import Pipeline, TradingViewAPI

# Создание и запуск пайплайна
async def main():
    pipeline = Pipeline()
    await pipeline.run()

# Проверка здоровья API
async def health_check():
    api = TradingViewAPI()
    async with api:
        health = await api.health_check()
        print(health)

asyncio.run(main())
```

## ⚙️ Конфигурация

Настройки проекта находятся в `tv_generator/config.py`:

```python
from tv_generator.config import settings

# API настройки
print(settings.tradingview_base_url)  # https://scanner.tradingview.com
print(settings.request_timeout)       # 30
print(settings.max_retries)          # 3
print(settings.requests_per_second)  # 10

# Поддерживаемые рынки
for market_name, config in settings.markets.items():
    print(f"{market_name}: {config['description']}")
```

### Переменные окружения

Создайте файл `.env` для переопределения настроек:

```env
TRADINGVIEW_BASE_URL=https://scanner.tradingview.com
REQUEST_TIMEOUT=30
MAX_RETRIES=3
REQUESTS_PER_SECOND=10
LOG_LEVEL=INFO
```

## 🏗️ Архитектура

```
tv_generator/
├── __init__.py          # Основной модуль
├── config.py           # Конфигурация через pydantic-settings
├── api.py              # API клиент с httpx
├── core.py             # Бизнес-логика пайплайна
├── cli.py              # Расширенный CLI
└── simple_cli.py       # Простой CLI с typer

tests/
├── conftest.py         # Фикстуры pytest
├── test_config.py      # Тесты конфигурации
├── test_api.py         # Тесты API
├── test_core.py        # Тесты бизнес-логики
└── test_cli.py         # Тесты CLI
```

## 🧪 Тестирование

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=tv_generator --cov-report=html

# Конкретный тест
pytest tests/test_api.py::test_get_metainfo

# Асинхронные тесты
pytest --asyncio-mode=auto
```

### Проверка качества кода

```bash
# Форматирование
black .

# Линтинг
flake8 .

# Типизация
mypy tv_generator/

# Безопасность
bandit -r tv_generator/
safety check
```

## 📊 Поддерживаемые рынки

| Рынок | Описание | Эндпоинт |
|-------|----------|----------|
| `us_stocks` | US Stocks | america |
| `us_etfs` | US ETFs | america |
| `global_stocks` | Global Stocks | global |
| `crypto_cex` | Crypto CEX | crypto |
| `crypto_dex` | Crypto DEX | crypto |
| `crypto_coins` | Cryptocurrency Coins | coin |
| `bonds` | Bonds | bond |

## 🔧 Разработка

### Установка для разработки

```bash
# Клонирование
git clone https://github.com/your-username/tv-generator.git
cd tv-generator

# Создание виртуального окружения
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -e ".[dev]"

# Pre-commit hooks
pre-commit install
```

### Структура разработки

1. **Fork** репозитория
2. Создайте **feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit** изменения (`git commit -m 'Add amazing feature'`)
4. **Push** в branch (`git push origin feature/amazing-feature`)
5. Откройте **Pull Request**

### Коммиты

Используйте [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new market support
fix: resolve API timeout issue
docs: update README with new examples
test: add integration tests for crypto markets
refactor: improve error handling in API client
```

## 📝 Логирование

Логи сохраняются в директории `logs/`:

- `logs/pipeline.log` - логи пайплайна
- `logs/tvgen.log` - логи CLI

Уровни логирования:
- `DEBUG` - детальная отладочная информация
- `INFO` - общая информация о процессе
- `WARNING` - предупреждения
- `ERROR` - ошибки

## 🚨 Обработка ошибок

Проект использует иерархию исключений:

```python
from tv_generator.api import TradingViewAPIError
from tv_generator.core import PipelineError

try:
    # API операции
    pass
except TradingViewAPIError as e:
    # Ошибки API (сетевые, HTTP)
    logger.error(f"API error: {e}")
except PipelineError as e:
    # Ошибки бизнес-логики
    logger.error(f"Pipeline error: {e}")
```

## 📈 Производительность

- **Асинхронные запросы** - параллельная обработка
- **Rate limiting** - 10 запросов/сек по умолчанию
- **Batch processing** - обработка полей батчами по 50
- **Retry с exponential backoff** - устойчивость к сбоям

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта! Пожалуйста, ознакомьтесь с:

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Contributing Guidelines](CONTRIBUTING.md)
- [Issue Templates](.github/ISSUE_TEMPLATE/)

## 📄 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 🙏 Благодарности

- [TradingView](https://www.tradingview.com/) за предоставление API
- [httpx](https://www.python-httpx.org/) за отличную HTTP библиотеку
- [typer](https://typer.tiangolo.com/) за современный CLI фреймворк
- [rich](https://rich.readthedocs.io/) за красивые терминальные интерфейсы

## 📞 Поддержка

- 📧 Email: support@tradingview-generator.com
- 🐛 Issues: [GitHub Issues](https://github.com/your-username/tv-generator/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/your-username/tv-generator/discussions)

---

**TradingView OpenAPI Generator** - автоматизируйте работу с TradingView API! 🚀
