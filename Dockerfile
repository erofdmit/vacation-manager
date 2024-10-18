# Используем официальный базовый образ Python 3.12-slim
FROM python:3.12-slim

# Устанавливаем системные зависимости для Poetry и работы с базой данных SQLite
RUN apt-get update && apt-get install -y \
    gcc \
    libsqlite3-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Обновление pip, setuptools и wheel
RUN pip install --upgrade pip setuptools wheel

# Установка Poetry
RUN pip install poetry

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Копируем pyproject.toml и poetry.lock для установки зависимостей
COPY pyproject.toml poetry.lock /app/

# Устанавливаем зависимости через Poetry
RUN python -m poetry config virtualenvs.create false \
    && python -m poetry install

# Копируем остальные файлы проекта в контейнер
COPY . /app

EXPOSE 8081 

# Указываем команду для запуска бота
CMD ["python", "main.py"]
