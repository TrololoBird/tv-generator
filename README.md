# TV Generator

Генератор OpenAPI спецификаций для TradingView API на основе справочников tv-screener.

## 📦 Генерация OpenAPI спецификаций

```bash
python -m src.tv_generator generate --market=russia --output-dir=docs/specs --validate
```

* Требует файл: `data/metainfo/russia.json`
* Результат: `docs/specs/russia_openapi.json`
* Совместимость: OpenAPI 3.1.0 + GPT Builder Custom Actions

### Поддерживаемые параметры:
- `--market`: рынок для генерации (russia, crypto, forex, etc.)
- `--output-dir`: директория для сохранения спецификаций
- `--validate`: валидация сгенерированной спецификации

## Источники данных

Все данные о рынках, полях, типах и метаинформации берутся из справочников библиотеки [tv-screener](https://github.com/mariostoev/tv-screener):

- **Справочник рынков**: `data/markets.json` - список всех поддерживаемых рынков
- **Отображаемые имена полей**: `data/column_display_names.json` - человекочитаемые названия полей
- **Метаинформация рынков**: `data/metainfo/*.json` - типы полей, enum'ы, описания для каждого рынка

## Структура проекта

```
tv-generator/
├── data/                          # Справочники из tv-screener
│   ├── markets.json              # Список рынков
│   ├── column_display_names.json # Отображаемые имена полей
│   └── metainfo/                 # Метаинформация по рынкам
│       ├── stocks.json
│       ├── crypto.json
│       ├── forex.json
│       └── ...
├── src/tv_generator/             # Основной код генератора
├── scripts/                      # CLI интерфейс
│   └── tv_generator_cli.py       # Единая точка входа
├── docs/                         # Документация и OpenAPI specs
└── tests/                        # Тесты
```

## Поддерживаемые рынки

### Страны (countries)
america, argentina, australia, austria, bahrain, bangladesh, belgium, brazil, canada, chile, china, colombia, cyprus, czech, denmark, egypt, estonia, finland, france, germany, greece, hongkong, hungary, iceland, india, indonesia, ireland, israel, italy, japan, kenya, korea, ksa, kuwait, latvia, lithuania, luxembourg, malaysia, mexico, morocco, netherlands, newzealand, nigeria, norway, pakistan, peru, philippines, poland, portugal, qatar, romania, rsa, russia, serbia, singapore, slovakia, spain, srilanka, sweden, switzerland, taiwan, thailand, tunisia, turkey, uae, uk, venezuela, vietnam

### Другие рынки (other)
bond, bonds, cfd, coin, crypto, economics2, forex, futures, options

## Использование

### Единая точка входа

Проект использует единую точку входа через CLI:

```bash
# Генерация OpenAPI спецификации для конкретного рынка
python -m src.tv_generator generate --market=russia --output-dir=docs/specs --validate

# Генерация для всех доступных рынков
python -m src.tv_generator

# Помощь по командам
python -m src.tv_generator --help
```

### Make команды

```bash
# Полный CI пайплайн
make ci

# Генерация спецификаций
make generate

# Обновление данных
make update

# Валидация данных
make validate-data

# Тестирование
make test
```

## Синхронизация с tv-screener

Для обновления справочников:

```bash
# Копирование актуальных справочников
copy tv-screener\data\markets.json data\markets.json
copy tv-screener\data\column_display_names.json data\column_display_names.json
copy tv-screener\data\metainfo\*.json data\metainfo\
```

## Разработка

```bash
# Установка зависимостей
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Запуск тестов
pytest

# Линтинг
flake8 src/ tests/
```
