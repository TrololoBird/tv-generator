# PROJECT_STRUCTURE_OPTIMIZATION_REPORT.md

## Отчет об оптимизации структуры проекта
**Дата:** 2025-06-22 04:03:55
**Проект:** tv-generator

## 🏗️ Выполненные оптимизации

- ✅ Создана директория: src
- ✅ Создана директория: src/tv_generator
- ✅ Создана директория: scripts/maintenance
- ✅ Создана директория: docs/api
- ✅ Создана директория: docs/user_guide
- ✅ Создана директория: data/raw
- ✅ Создана директория: data/processed
- ✅ Создана директория: reports
- ✅ Создана директория: backups
- ✅ Создан файл: C:\tradingview_openapi\TV-generator\tv-generator\src\tv_generator\__init__.py
- ✅ Перемещен скрипт cleanup.py в scripts/maintenance/
- ✅ Перемещен скрипт optimize_structure.py в scripts/maintenance/
- ✅ Перемещены спецификации в docs/specs/
- ✅ Создан README в docs/
- ✅ Перемещены логи в reports/
- ✅ Создан главный CLI: main.py
- ✅ Создан скрипт генерации: scripts/maintenance/generate_specs.py
- ✅ Обновлен pyproject.toml для новой структуры
- ✅ Создан .env.example
- ✅ Создан setup.cfg

## 📁 Новая структура проекта

```
tv-generator/
├── src/
│   └── tv_generator/          # Основной пакет
│       ├── __init__.py
│       ├── api.py
│       ├── cli.py
│       ├── config.py
│       ├── core.py
│       └── simple_cli.py
├── scripts/
│   ├── maintenance/           # Скрипты обслуживания
│   │   ├── cleanup.py
│   │   ├── optimize_structure.py
│   │   └── generate_specs.py
│   └── utils/                 # Утилиты
│       ├── validation_and_ci.py
│       └── openapi_updater.py
├── tests/                     # Тесты
├── docs/
│   ├── api/                   # Документация API
│   ├── user_guide/            # Руководство пользователя
│   ├── specs/                 # OpenAPI спецификации
│   └── README.md
├── data/
│   ├── raw/                   # Сырые данные
│   └── processed/             # Обработанные данные
├── reports/                   # Отчеты и логи
├── backups/                   # Резервные копии
├── main.py                    # Главная точка входа
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── README.md
└── .env.example
```

## 🚀 Точки входа

### Основные команды:
- `python main.py` - Главный CLI
- `python scripts/maintenance/generate_specs.py` - Генерация спецификаций
- `python scripts/maintenance/cleanup.py` - Очистка проекта

### Установка и разработка:
- `pip install -e .` - Установка в режиме разработки
- `pytest` - Запуск тестов
- `black .` - Форматирование кода
- `flake8` - Проверка стиля

## 📋 Следующие шаги

1. **Обновить импорты** в коде для новой структуры
2. **Обновить тесты** для работы с новой структурой
3. **Обновить документацию** с новыми путями
4. **Протестировать** все точки входа
5. **Обновить CI/CD** конфигурацию
