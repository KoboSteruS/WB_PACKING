import os
from dotenv import load_dotenv
from typing import Dict, Any

# Загрузка переменных окружения
load_dotenv()

# Конфигурация Google Sheets
CREDENTIALS_FILE = "credentials.json"
SPREADSHEET_NAME = "Storage Table"
SETTINGS_SHEET = "Настройки"

# Конфигурация отчетов
REPORTS_CONFIG = {
    'B1': {
        'name': 'Отчет Кузнецова',
        'api_key_cell': 'B1'
    },
    'C1': {
        'name': 'Отчет Царева',
        'api_key_cell': 'C1'
    }
}

# Конфигурация WB API
WB_API_BASE_URL = "https://seller-analytics-api.wildberries.ru/api/v1"
PAID_STORAGE_ENDPOINT = f"{WB_API_BASE_URL}/paid_storage"

# Временные настройки
TIMEZONE = "Europe/Moscow"
RETRY_DELAY = 60  # секунды между попытками
MAX_RETRIES = 3   # максимальное количество попыток

# Названия колонок
HEADERS = [
    "Дата расчёта", "Коэф. логистики", "ID склада", "Склад", "Коэф. склада",
    "ID поставки", "ID размера", "Размер", "Баркод", "Предмет", "Бренд",
    "Артикул продавца", "Артикул WB", "Объём", "Способ расчёта", "Сумма хранения",
    "Кол-во товаров", "Код паллетоместа", "Кол-во паллет", "Дата первонач. расчёта",
    "Скидка лояльности", "Дата фиксации тарифа", "Дата понижения тарифа"
] 