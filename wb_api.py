from typing import Optional, Dict, Any, List
import requests
from loguru import logger
from config import WB_API_BASE_URL, RETRY_DELAY, MAX_RETRIES
import time
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import random

class WildberriesAPI:
    """Класс для работы с API Wildberries"""
    
    def __init__(self, api_key: str):
        """
        Инициализация клиента API
        
        Args:
            api_key (str): API ключ Wildberries
        """
        self.api_key = api_key
        self.headers = {"Authorization": api_key}
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """
        Создание сессии с настройками повторных попыток
        
        Returns:
            requests.Session: Настроенная сессия
        """
        session = requests.Session()
        
        # Настройка стратегии повторных попыток
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=2,  # Увеличили фактор для большего интервала между попытками
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True  # Учитываем заголовок Retry-After
        )
        
        # Настройка адаптера с увеличенными таймаутами
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=1,  # Уменьшаем пул соединений
            pool_maxsize=1
        )
        
        # Применение адаптера ко всем URL
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _handle_rate_limit(self, response: requests.Response) -> int:
        """
        Обработка ограничения частоты запросов
        
        Args:
            response: Ответ от сервера
            
        Returns:
            int: Время ожидания в секундах
        """
        # Проверяем заголовок Retry-After
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                pass
        
        # Если заголовка нет, используем прогрессивное время ожидания
        return random.randint(60, 120)
    
    def get_task_id(self, date_from: str, date_to: str) -> Optional[str]:
        """
        Получение task_id для запроса данных о платном хранении за период
        
        Args:
            date_from (str): Дата начала в формате YYYY-MM-DD
            date_to (str): Дата окончания в формате YYYY-MM-DD
            
        Returns:
            Optional[str]: ID задачи или None в случае ошибки
        """
        try:
            url = f"{WB_API_BASE_URL}/paid_storage"
            params = {"dateFrom": date_from, "dateTo": date_to}
            
            logger.info(f"Запрос данных за период: {date_from} - {date_to}")
            
            response = self.session.get(
                url,
                headers=self.headers,
                params=params,
                timeout=(30, 60)  # Увеличенные таймауты
            )
            
            if response.status_code == 429:
                wait_time = self._handle_rate_limit(response)
                logger.warning(f"Превышен лимит запросов. Ожидание {wait_time} секунд...")
                time.sleep(wait_time)
                return self.get_task_id(date_from, date_to)
            
            response.raise_for_status()
            
            data = response.json()
            task_id = data.get("data", {}).get("taskId")
            
            if task_id:
                logger.info(f"Получен task_id: {task_id}")
            else:
                logger.error("task_id не найден в ответе API")
                
            return task_id
            
        except requests.exceptions.Timeout:
            logger.error("Превышено время ожидания при получении task_id")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении task_id: {e}")
            return None
    
    def get_storage_report(self, task_id: str) -> Optional[list]:
        """
        Получение отчета по платному хранению
        
        Args:
            task_id (str): ID задачи
            
        Returns:
            Optional[list]: Список данных отчета или None в случае ошибки
        """
        max_attempts = 5  # Увеличиваем количество попыток
        current_attempt = 0
        
        while current_attempt < max_attempts:
            try:
                url = f"{WB_API_BASE_URL}/paid_storage/tasks/{task_id}/download"
                
                # Прогрессивное увеличение времени ожидания
                wait_time = RETRY_DELAY * (2 ** current_attempt)
                logger.info(f"Ожидание {wait_time} секунд перед запросом отчета (попытка {current_attempt + 1}/{max_attempts})...")
                time.sleep(wait_time)
                
                response = self.session.get(
                    url,
                    headers=self.headers,
                    timeout=(30, 600)  # Увеличиваем таймаут для больших отчетов
                )
                
                if response.status_code == 429:
                    wait_time = self._handle_rate_limit(response)
                    logger.warning(f"Превышен лимит запросов. Ожидание {wait_time} секунд...")
                    time.sleep(wait_time)
                    current_attempt += 1
                    continue
                
                response.raise_for_status()
                
                data = response.json()
                if data:
                    logger.info(f"Получены данные отчета: {len(data)} записей")
                    return data
                else:
                    logger.warning("Получен пустой отчет")
                    current_attempt += 1
                    continue
                
            except requests.exceptions.Timeout:
                logger.warning(f"Превышено время ожидания при получении отчета (попытка {current_attempt + 1}/{max_attempts})")
                current_attempt += 1
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Ошибка соединения при получении отчета (попытка {current_attempt + 1}/{max_attempts}): {e}")
                # Увеличиваем время ожидания при ошибке соединения
                time.sleep(random.randint(30, 60))
                current_attempt += 1
            except requests.exceptions.RequestException as e:
                logger.error(f"Ошибка при получении отчета: {e}")
                if "too many 429 error responses" in str(e):
                    # При превышении лимита делаем большую паузу
                    wait_time = random.randint(180, 300)
                    logger.warning(f"Превышен лимит запросов. Ожидание {wait_time} секунд...")
                    time.sleep(wait_time)
                    current_attempt += 1
                    continue
                return None
        
        logger.error(f"Не удалось получить отчет после {max_attempts} попыток")
        return None
            
    def format_storage_data(self, data: list) -> list:
        """
        Форматирование данных отчета
        
        Args:
            data (list): Список данных от API
            
        Returns:
            list: Отформатированный список данных
        """
        if not data:
            return []
            
        formatted_rows = []
        for item in data:
            row = [
                item.get("date", ""),
                item.get("logWarehouseCoef", 0),
                item.get("officeId", ""),
                item.get("warehouse", ""),
                item.get("warehouseCoef", 0),
                item.get("giId", ""),
                item.get("chrtId", ""),
                item.get("size", ""),
                item.get("barcode", ""),
                item.get("subject", ""),
                item.get("brand", ""),
                item.get("vendorCode", ""),
                item.get("nmId", ""),
                item.get("volume", 0),
                item.get("calcType", ""),
                item.get("warehousePrice", 0),
                item.get("barcodesCount", 0),
                item.get("palletPlaceCode", ""),
                item.get("palletCount", 0),
                item.get("originalDate", ""),
                item.get("loyaltyDiscount", 0),
                item.get("tariffFixDate", ""),
                item.get("tariffLowerDate", "")
            ]
            formatted_rows.append(row)
            
        logger.info(f"Отформатировано {len(formatted_rows)} строк данных")
        return formatted_rows 