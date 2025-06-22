# Документация проекта

## Структура документации

- `api/` - Документация API
- `user_guide/` - Руководство пользователя
- `specs/` - OpenAPI спецификации
- `source/` - Исходники документации (Sphinx)
- `README.md` - Этот файл

## Быстрый старт

1. **Установка**: `pip install -e .`
2. **Запуск основного генератора**: `python main.py`
3. **Генерация спецификаций**: `python scripts/maintenance/generate_specs.py`
4. **CLI команды**: `python -m tv_generator.cli --help`

## Основные команды

### Генерация спецификаций
```bash
# Генерация всех спецификаций
python scripts/maintenance/generate_specs.py

# Программный вызов
python -c "from tv_generator.core import generate_all_specifications; generate_all_specifications()"
```

### CLI интерфейс
```bash
# Информация о проекте
python -m tv_generator.cli info

# Валидация конфигурации
python -m tv_generator.cli validate

# Сбор данных
python -m tv_generator.cli fetch-data

# Тестирование
python -m tv_generator.cli test-specs
```

### Обслуживание проекта
```bash
# Очистка проекта
python scripts/maintenance/cleanup.py

# Оптимизация структуры
python scripts/maintenance/optimize_structure.py
```

## Структура проекта

```
tv-generator/
├── src/tv_generator/           # Основной пакет
├── scripts/                    # Скрипты обслуживания
├── docs/                       # Документация
├── tests/                      # Тесты
├── data/                       # Данные
├── reports/                    # Отчеты и логи
├── backups/                    # Резервные копии
├── main.py                     # Основная точка входа
└── generate_openapi.py         # Генератор OpenAPI
```

## Подробная документация

См. соответствующие разделы в поддиректориях:

- **API документация** (`api/`) - Подробное описание API
- **Руководство пользователя** (`user_guide/`) - Пошаговые инструкции
- **OpenAPI спецификации** (`specs/`) - Генерируемые спецификации
- **Sphinx документация** (`source/`) - Автоматически генерируемая документация

## Сборка документации

```bash
# Установка зависимостей для документации
pip install sphinx sphinx-rtd-theme

# Сборка HTML документации
cd docs
make html

# Просмотр документации
open build/html/index.html
```
