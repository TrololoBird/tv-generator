# Руководство пользователя

## Быстрый старт

### 1. Установка

```bash
# Клонирование репозитория
git clone https://github.com/your-username/tv-generator.git
cd tv-generator

# Создание виртуального окружения
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -e .
```

### 2. Первый запуск

```bash
# Проверка установки
python -m tv_generator.cli info

# Валидация конфигурации
python -m tv_generator.cli validate

# Генерация спецификаций
python scripts/maintenance/generate_specs.py
```

### 3. Проверка результатов

```bash
# Просмотр сгенерированных спецификаций
ls docs/specs/

# Тестирование спецификаций
python -m tv_generator.cli test-specs
```

## Основные операции

### Генерация спецификаций

#### Автоматическая генерация всех спецификаций
```bash
python scripts/maintenance/generate_specs.py
```

Этот скрипт:
- Генерирует OpenAPI спецификации для всех поддерживаемых рынков
- Сохраняет результаты в `docs/specs/`
- Логирует процесс в `reports/`

#### Программная генерация
```python
from tv_generator.core import generate_all_specifications

# Генерация всех спецификаций
generate_all_specifications()
```

### Сбор данных

#### Сбор данных со всех рынков
```bash
python -m tv_generator.cli fetch-data
```

#### Сбор данных с конкретного рынка
```bash
python -m tv_generator.cli fetch-data --market us_stocks
python -m tv_generator.cli fetch-data --market crypto
python -m tv_generator.cli fetch-data --market forex
```

#### Подробный вывод
```bash
python -m tv_generator.cli fetch-data --verbose
```

### CLI команды

#### Информация о проекте
```bash
python -m tv_generator.cli info
```

#### Валидация конфигурации
```bash
python -m tv_generator.cli validate
```

#### Тестирование спецификаций
```bash
python -m tv_generator.cli test-specs
```

#### Справка
```bash
python -m tv_generator.cli --help
python -m tv_generator.cli fetch-data --help
```

## Конфигурация

### Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
# API настройки
TRADINGVIEW_BASE_URL=https://scanner.tradingview.com
REQUEST_TIMEOUT=30
MAX_RETRIES=3
REQUESTS_PER_SECOND=10

# Логирование
LOG_LEVEL=INFO
LOG_FILE=reports/tvgen.log

# Пути к данным
DATA_DIR=data
SPECS_DIR=docs/specs
```

### Программная настройка

```python
from tv_generator.config import settings

# Изменение настроек
settings.request_timeout = 60
settings.requests_per_second = 5

# Проверка настроек
print(f"Base URL: {settings.tradingview_base_url}")
print(f"Timeout: {settings.request_timeout}")
print(f"Rate limit: {settings.requests_per_second} req/s")
```

## Поддерживаемые рынки

| Рынок | Описание | Статус |
|-------|----------|--------|
| `us_stocks` | US Stocks | ✅ |
| `us_etfs` | US ETFs | ✅ |
| `america` | America Markets | ✅ |
| `forex` | Forex | ✅ |
| `crypto` | Cryptocurrency | ✅ |
| `crypto_dex` | Crypto DEX | ✅ |
| `coin` | Cryptocurrency Coins | ✅ |
| `futures` | Futures | ✅ |
| `cfd` | CFDs | ✅ |
| `bonds` | Bonds | ✅ |

## Обработка ошибок

### Типичные ошибки и решения

#### Ошибка сети
```
TradingViewAPIError: Connection timeout
```
**Решение**: Проверьте интернет-соединение и настройки прокси.

#### Rate limiting
```
TradingViewAPIError: Too many requests
```
**Решение**: Уменьшите `REQUESTS_PER_SECOND` в настройках.

#### Неверный рынок
```
ValueError: Unknown market: invalid_market
```
**Решение**: Используйте один из поддерживаемых рынков из таблицы выше.

### Логирование

Логи сохраняются в `reports/`:

```bash
# Просмотр логов
tail -f reports/tvgen.log

# Поиск ошибок
grep ERROR reports/tvgen.log
```

## Обслуживание проекта

### Очистка проекта
```bash
python scripts/maintenance/cleanup.py
```

### Оптимизация структуры
```bash
python scripts/maintenance/optimize_structure.py
```

### Резервное копирование
```bash
# Создание резервной копии спецификаций
cp -r docs/specs backups/specs_$(date +%Y%m%d_%H%M%S)
```

## Интеграция с CI/CD

### GitHub Actions

```yaml
name: Generate OpenAPI Specs

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  generate:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -e .
    
    - name: Generate specifications
      run: |
        python scripts/maintenance/generate_specs.py
    
    - name: Run tests
      run: |
        pytest
    
    - name: Upload specs
      uses: actions/upload-artifact@v3
      with:
        name: openapi-specs
        path: docs/specs/
```

## Примеры использования

### Программное использование

```python
import asyncio
from tv_generator import Pipeline, TradingViewAPI

async def main():
    # Создание пайплайна
    pipeline = Pipeline()
    
    # Запуск сбора данных
    await pipeline.run()
    
    # Проверка здоровья API
    api = TradingViewAPI()
    async with api:
        health = await api.health_check()
        print(f"API Health: {health}")

# Запуск
asyncio.run(main())
```

### Генерация спецификаций программно

```python
from tv_generator.core import generate_all_specifications

def generate_specs():
    try:
        generate_all_specifications()
        print("✅ Спецификации успешно сгенерированы")
    except Exception as e:
        print(f"❌ Ошибка генерации: {e}")

generate_specs()
```

## Поддержка

- 📧 Email: support@tradingview-generator.com
- 🐛 Issues: [GitHub Issues](https://github.com/your-username/tv-generator/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/your-username/tv-generator/discussions)
- 📖 Документация: [docs/](docs/)
