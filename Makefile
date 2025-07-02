.PHONY: generate test lint format install dev-install ci pre-commit-hooks clean-specs sync validate update validate-data

clean-specs: ## Очистить спецификации перед генерацией
	@echo "🧹 Очистка спецификаций..."
	rm -f docs/specs/*.json
	@echo "✅ Спецификации очищены"

sync: ## Синхронизировать данные из tv-screener
	@echo "🔄 Синхронизация данных..."
	python scripts/tv_generator_cli.py sync --force
	@echo "✅ Данные синхронизированы"

update: ## Обновить данные TradingView
	@echo "🔄 Обновление данных TradingView..."
	python scripts/tv_generator_cli.py update
	@echo "✅ Данные обновлены"

validate-data: ## Валидировать данные
	@echo "🔍 Валидация данных..."
	python scripts/tv_generator_cli.py validate-data
	@echo "✅ Данные валидированы"

generate: clean-specs ## Сгенерировать спецификации OpenAPI
	@echo "🔧 Генерация спецификаций OpenAPI..."
	python scripts/tv_generator_cli.py generate --validate --auto-update
	@echo "✅ Спецификации сгенерированы"

validate: ## Валидировать спецификации OpenAPI
	@echo "🔍 Валидация спецификаций..."
	python scripts/tv_generator_cli.py validate
	@echo "✅ Спецификации валидированы"

test: ## Запустить тесты (требует предварительно сгенерированных спецификаций)
	@echo "🧪 Запуск тестов..."
	python scripts/tv_generator_cli.py test
	pytest --maxfail=1 --disable-warnings -v
	@echo "✅ Тесты завершены"

lint: ## Проверить код линтерами
	@echo "🔍 Проверка кода линтерами..."
	python -m flake8 src/ tests/
	python -m mypy src/
	python -m bandit -r src/
	@echo "✅ Линтеры пройдены"

format: ## Форматировать код
	@echo "🎨 Форматирование кода..."
	python -m black src/ tests/
	python -m isort src/ tests/
	@echo "✅ Код отформатирован"

install: ## Установить зависимости
	@echo "📦 Установка зависимостей..."
	pip install -r requirements.txt
	@echo "✅ Зависимости установлены"

dev-install: ## Установить зависимости для разработки
	@echo "📦 Установка зависимостей для разработки..."
	pip install -r requirements-dev.txt
	pre-commit install
	@echo "✅ Зависимости для разработки установлены"

ci: update generate test lint ## Полный CI пайплайн
	@echo "🚀 CI пайплайн завершен успешно"

pre-commit-hooks: ## Установить pre-commit хуки
	@echo "🔧 Установка pre-commit хуков..."
	pre-commit install
	pre-commit install --hook-type pre-push
	@echo "✅ Pre-commit хуки установлены"

info: ## Показать информацию о проекте
	@echo "📊 Информация о проекте..."
	python scripts/tv_generator_cli.py info
	@echo "✅ Информация показана"
