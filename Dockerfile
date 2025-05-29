FROM python:3.9-slim

# Установка рабочей директории
WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование файлов проекта
COPY . .

# Создание директории для логов
RUN mkdir -p /app/logs

# Установка временной зоны
ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Запуск приложения
CMD ["python", "main.py"] 