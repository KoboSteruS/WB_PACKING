from datetime import datetime, timedelta
import pytz
from typing import Tuple

def get_previous_week_dates(timezone_name: str) -> Tuple[datetime, datetime]:
    """
    Вычисляет даты начала и конца прошлой недели.
    
    Args:
        timezone_name (str): Название временной зоны
        
    Returns:
        Tuple[datetime, datetime]: Кортеж с датами начала и конца прошлой недели
    """
    tz = pytz.timezone(timezone_name)
    current_date = datetime.now(tz)
    
    # Находим понедельник текущей недели
    current_week_monday = current_date - timedelta(days=current_date.weekday())
    # Находим понедельник прошлой недели (начало периода)
    previous_week_monday = current_week_monday - timedelta(days=7)
    # Находим воскресенье прошлой недели (конец периода)
    previous_week_sunday = current_week_monday - timedelta(days=1)
    
    # Устанавливаем время на начало и конец дня соответственно
    start_date = previous_week_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = previous_week_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return start_date, end_date

def get_specific_week_dates(year: int, month: int, start_day: int, end_day: int, timezone_name: str) -> Tuple[datetime, datetime]:
    """
    Получает даты для конкретной недели.
    
    Args:
        year (int): Год
        month (int): Месяц
        start_day (int): День начала недели
        end_day (int): День окончания недели
        timezone_name (str): Название временной зоны
        
    Returns:
        Tuple[datetime, datetime]: Кортеж с датами начала и конца указанной недели
    """
    tz = pytz.timezone(timezone_name)
    
    # Создаем даты начала и конца
    start_date = datetime(year, month, start_day, 0, 0, 0, 0, tz)
    end_date = datetime(year, month, end_day, 23, 59, 59, 999999, tz)
    
    return start_date, end_date 