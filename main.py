import schedule
import time
from datetime import datetime, timedelta
import pytz
from loguru import logger
from wb_api import WildberriesAPI
from sheets_client import GoogleSheetsClient
from config import TIMEZONE
import random
import os

# Настройка логирования
log_path = os.path.join("logs", "app.log")
os.makedirs("logs", exist_ok=True)

logger.add(
    log_path,
    rotation="1 week",
    retention="1 month",
    compression="zip",
    level="INFO",
    backtrace=True,
    diagnose=True
)

def process_storage_report() -> None:
    """
    Основная функция обработки отчета по платному хранению
    """
    try:
        logger.info("Начало выполнения еженедельного отчета")
        
        # Инициализация клиента Google Sheets
        sheets_client = GoogleSheetsClient()
        
        # Получение API ключей
        api_keys = sheets_client.get_api_keys()
        if not api_keys:
            logger.error("API ключи не найдены в настройках")
            return
            
        # Получение дат
        date_from, date_to = sheets_client.get_date_range()
        if not date_from or not date_to:
            logger.error("Не удалось получить диапазон дат из настроек")
            return
            
        # Форматирование дат для API
        date_from_str = date_from.strftime('%Y-%m-%d')
        date_to_str = date_to.strftime('%Y-%m-%d')
        
        # Обработка для каждого API ключа
        for cell, api_key in api_keys.items():
            logger.info(f"Обработка данных для ключа из ячейки {cell}")
            
            # Инициализация API клиента для текущего ключа
            wb_api = WildberriesAPI(api_key)
            
            # Получение task_id для всего диапазона
            task_id = wb_api.get_task_id(date_from_str, date_to_str)
            if not task_id:
                logger.error(f"Не удалось получить task_id для периода {date_from_str} - {date_to_str} (ключ из {cell})")
                continue
                
            # Получение данных отчета
            report_data = wb_api.get_storage_report(task_id)
            if not report_data:
                logger.error(f"Не удалось получить данные отчета для периода {date_from_str} - {date_to_str} (ключ из {cell})")
                continue
                
            # Форматирование и сохранение данных
            formatted_data = wb_api.format_storage_data(report_data)
            if formatted_data:
                sheets_client.append_report_data(formatted_data, cell)
                logger.info(f"Данные успешно записаны в таблицу для ключа из {cell}")
            else:
                logger.warning(f"Нет данных для записи в таблицу (ключ из {cell})")
        
        # Обновление последней обработанной даты
        sheets_client.update_last_processed_date(date_to)
        
        logger.info(f"Успешно обработаны отчеты за период {date_from_str} - {date_to_str}")
        
    except Exception as e:
        logger.exception(f"Ошибка при обработке отчетов: {e}")

def main():
    """
    Основная функция приложения
    """
    try:
        logger.info("Запуск приложения в контейнере")
        
        # Установка часового пояса
        timezone = pytz.timezone(TIMEZONE)
        current_time = datetime.now(timezone)
        
        # Генерируем случайное время между 6:00 и 7:00
        random_hour = 6
        random_minute = random.randint(0, 59)
        schedule_time = f"{random_hour:02d}:{random_minute:02d}"
        
        logger.info(f"Установлено время выполнения: каждый понедельник в {schedule_time}")
        
        # Планирование выполнения каждый понедельник
        schedule.every().monday.at(schedule_time).do(process_storage_report)
        
        # Если сейчас понедельник и время между 6:00 и 7:00, выполняем сразу
        if current_time.weekday() == 0 and 6 <= current_time.hour < 7:
            logger.info("Текущее время подходит для немедленного выполнения")
            process_storage_report()
        
        logger.info("Переход в режим ожидания следующего запланированного выполнения")
        
        # Бесконечный цикл с обработкой исключений
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except Exception as e:
                logger.exception(f"Ошибка в основном цикле: {e}")
                time.sleep(60)  # Пауза перед следующей попыткой
                
    except Exception as e:
        logger.exception(f"Критическая ошибка в приложении: {e}")
        raise

if __name__ == "__main__":
    main()

