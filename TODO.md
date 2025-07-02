# TODO: Технический долг

## 🧪 Исправление тестов

### Проблема
Тесты не работают из-за проблем с импортами:
```
ModuleNotFoundError: No module named 'tv_generator'
```

### Решение
1. Исправить импорты в `tests/conftest.py` и других тестовых файлах
2. Обновить пути импорта для совместимости с новой архитектурой
3. Убедиться, что тесты используют правильные классы из `main.py`

### Файлы для исправления
- `tests/conftest.py`
- `tests/test_core.py`
- `tests/test_integration.py`
- `tests/test_cli_commands.py`
- `tests/test_cli.py`
- `tests/test_regression.py`
- `tests/test_metadata.py`
- `tests/test_enum_fields.py`
- `tests/test_descriptions_examples.py`
- `tests/test_ref_schemas.py`

### Команда для запуска тестов
```bash
python -m pytest tests/ -v
```

## 🔧 Другие улучшения

### Линтинг
- Исправить ошибки flake8 в коде
- Убрать неиспользуемые импорты
- Исправить длинные строки

### Документация
- Обновить README.md с актуальными инструкциями
- Добавить примеры использования
- Создать документацию по API

### Производительность
- Оптимизировать генерацию спецификаций
- Добавить кэширование
- Улучшить обработку ошибок 