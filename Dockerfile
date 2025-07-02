FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY pyproject.toml requirements.txt ./

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY src/ ./src/
COPY main.py ./

# Создание необходимых директорий
RUN mkdir -p results specs logs

# Установка переменных окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Точка входа
ENTRYPOINT ["python", "-m", "tv_generator.cli"]
