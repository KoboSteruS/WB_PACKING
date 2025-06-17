from typing import Optional, List, Any, Dict, Tuple
import gspread
from datetime import datetime
from loguru import logger
from config import (
    CREDENTIALS_FILE,
    SPREADSHEET_NAME,
    SETTINGS_SHEET,
    HEADERS,
    REPORTS_CONFIG
)

class GoogleSheetsClient:
    """Класс для работы с Google Sheets"""
    
    def __init__(self):
        """Инициализация клиента Google Sheets"""
        try:
            self.gc = gspread.service_account(filename=CREDENTIALS_FILE)
            self.spreadsheet = self.gc.open(SPREADSHEET_NAME)
            self.settings_sheet = self.spreadsheet.worksheet(SETTINGS_SHEET)
            self.reports_sheets = self._get_or_create_reports_sheets()
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации Google Sheets: {e}")
            raise
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Парсинг даты из различных форматов
        
        Args:
            date_str (str): Строка с датой в формате YYYY-MM-DD или DD.MM.YYYY
            
        Returns:
            Optional[datetime]: Объект datetime или None в случае ошибки
        """
        if not date_str:
            return None
            
        formats = ['%Y-%m-%d', '%d.%m.%Y']
        
        for date_format in formats:
            try:
                return datetime.strptime(date_str, date_format)
            except ValueError:
                continue
                
        logger.error(f"Не удалось распознать формат даты: {date_str}")
        return None
    
    def _get_or_create_reports_sheets(self) -> Dict[str, gspread.Worksheet]:
        """
        Получение или создание листов отчетов для каждого ключа API
        
        Returns:
            Dict[str, gspread.Worksheet]: Словарь с листами отчетов
        """
        reports_sheets = {}
        
        for cell, config in REPORTS_CONFIG.items():
            sheet_name = config['name']
            try:
                # Пытаемся получить существующий лист
                sheet = self.spreadsheet.worksheet(sheet_name)
                logger.info(f"Найден существующий лист {sheet_name}")
                # Проверяем и восстанавливаем заголовки в существующем листе
                self._ensure_headers_exists(sheet)
            except gspread.exceptions.WorksheetNotFound:
                # Создаем новый лист если не существует
                sheet = self.spreadsheet.add_worksheet(sheet_name, 1000, len(HEADERS))
                sheet.append_row(HEADERS)
                logger.info(f"Создан новый лист {sheet_name}")
            
            reports_sheets[cell] = sheet
            
        return reports_sheets
    
    def _ensure_headers_exists(self, sheet: gspread.Worksheet) -> None:
        """
        Проверяет наличие заголовков при инициализации листа
        
        Args:
            sheet (gspread.Worksheet): Лист для проверки
        """
        try:
            # Получаем первую строку
            first_row = sheet.row_values(1)
            
            # Если первая строка пустая или заголовки неправильные
            if not first_row or len(first_row) < len(HEADERS) or first_row[0] != HEADERS[0]:
                # Обновляем заголовки
                range_name = f'A1:{chr(ord("A") + len(HEADERS) - 1)}1'
                sheet.update(range_name, [HEADERS])
                logger.info(f"Установлены заголовки в листе {sheet.title}")
        except Exception as e:
            logger.error(f"Ошибка при установке заголовков в листе {sheet.title}: {e}")
    
    def _clear_sheet_data(self, sheet: gspread.Worksheet) -> None:
        """
        Очистка данных в листе, сохраняя заголовки
        
        Args:
            sheet (gspread.Worksheet): Лист для очистки
        """
        try:
            # Получаем все значения
            all_values = sheet.get_all_values()
            row_count = len(all_values)
            
            if row_count > 1:  # Если есть данные кроме заголовков
                # Определяем диапазон для очистки (от 2-й строки до последней)
                max_col = chr(ord("A") + len(HEADERS) - 1)
                clear_range = f'A2:{max_col}{row_count}'
                sheet.batch_clear([clear_range])
                logger.info(f"Очищены старые данные в листе {sheet.title} (диапазон {clear_range})")
            elif row_count == 0:
                # Если лист полностью пустой, добавляем заголовки
                sheet.append_row(HEADERS)
                logger.info(f"Добавлены заголовки в пустой лист {sheet.title}")
        except Exception as e:
            logger.error(f"Ошибка при очистке данных в листе {sheet.title}: {e}")
    
    def get_api_keys(self) -> Dict[str, str]:
        """
        Получение всех API ключей из настроек
        
        Returns:
            Dict[str, str]: Словарь с API ключами
        """
        api_keys = {}
        try:
            for cell, config in REPORTS_CONFIG.items():
                key = self.settings_sheet.acell(config['api_key_cell']).value
                if key:
                    api_keys[cell] = key
                    logger.info(f"Получен API ключ из ячейки {config['api_key_cell']}")
                else:
                    logger.warning(f"API ключ не найден в ячейке {config['api_key_cell']}")
        except Exception as e:
            logger.error(f"Ошибка при получении API ключей: {e}")
        
        return api_keys
    
    def get_date_range(self) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Получение диапазона дат из настроек
        
        Returns:
            tuple[Optional[datetime], Optional[datetime]]: Кортеж с датами начала и конца
        """
        try:
            date_from = self.settings_sheet.acell('B3').value
            date_to = self.settings_sheet.acell('C3').value
            
            if not date_from or not date_to:
                return None, None
                
            parsed_from = self._parse_date(date_from)
            parsed_to = self._parse_date(date_to)
            
            if not parsed_from or not parsed_to:
                return None, None
                
            return parsed_from, parsed_to
            
        except Exception as e:
            logger.error(f"Ошибка при получении диапазона дат: {e}")
            return None, None
    
    def get_last_processed_date(self, api_key_cell: str) -> Optional[datetime]:
        """
        Получение последней обработанной даты для конкретного отчета
        
        Args:
            api_key_cell (str): Ячейка с API ключом (например, 'B1' или 'C1')
            
        Returns:
            Optional[datetime]: Последняя обработанная дата или None
        """
        try:
            last_date = self.settings_sheet.acell('B4').value
            return self._parse_date(last_date) if last_date else None
        except Exception as e:
            logger.error(f"Ошибка при получении последней обработанной даты: {e}")
            return None
    
    def update_last_processed_date(self, date: datetime) -> None:
        """
        Обновление последней обработанной даты
        
        Args:
            date (datetime): Дата для сохранения
        """
        try:
            # Сохраняем в том же формате, что и исходная дата
            original_format = self._get_original_date_format()
            date_str = date.strftime(original_format or '%Y-%m-%d')
            self.settings_sheet.update('B4', date_str)
        except Exception as e:
            logger.error(f"Ошибка при обновлении последней обработанной даты: {e}")
    
    def _get_original_date_format(self) -> Optional[str]:
        """
        Определение исходного формата даты из таблицы
        
        Returns:
            Optional[str]: Формат даты или None
        """
        try:
            date_from = self.settings_sheet.acell('B3').value
            if not date_from:
                return None
                
            if '.' in date_from:
                return '%d.%m.%Y'
            return '%Y-%m-%d'
        except Exception:
            return None
    
    def _ensure_headers(self, sheet: gspread.Worksheet) -> None:
        """
        Проверяет наличие заголовков и добавляет их при необходимости
        
        Args:
            sheet (gspread.Worksheet): Лист для проверки
        """
        try:
            # Получаем первую строку
            first_row = sheet.row_values(1)
            
            # Проверяем, есть ли заголовки
            if not first_row:
                # Если лист полностью пустой - добавляем заголовки
                sheet.append_row(HEADERS)
                logger.info(f"Добавлены заголовки в пустой лист {sheet.title}")
            elif len(first_row) < len(HEADERS) or first_row[0] != HEADERS[0]:
                # Если заголовки неполные или неправильные - обновляем только первую строку
                range_name = f'A1:{chr(ord("A") + len(HEADERS) - 1)}1'
                sheet.update(range_name, [HEADERS])
                logger.info(f"Восстановлены заголовки в листе {sheet.title}")
        except Exception as e:
            logger.error(f"Ошибка при проверке заголовков в листе {sheet.title}: {e}")
    
    def append_report_data(self, data: List[List[Any]], api_key_cell: str) -> None:
        """
        Добавление данных в отчет с предварительной очисткой
        
        Args:
            data (List[List[Any]]): Список строк с данными
            api_key_cell (str): Ячейка с API ключом (например, 'B1' или 'C1')
        """
        if not data:
            return
            
        try:
            sheet = self.reports_sheets.get(api_key_cell)
            if not sheet:
                logger.error(f"Не найден лист для ключа из ячейки {api_key_cell}")
                return
            
            # Проверяем и восстанавливаем заголовки
            self._ensure_headers(sheet)
            
            # Очищаем старые данные (кроме заголовков)
            self._clear_sheet_data(sheet)
            
            # Записываем новые данные
            if len(data) > 0:
                sheet.append_rows(data)
                logger.info(f"Данные обновлены в листе {REPORTS_CONFIG[api_key_cell]['name']} ({len(data)} строк)")
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении данных в отчете: {e}") 