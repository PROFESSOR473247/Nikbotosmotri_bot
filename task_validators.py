"""
Валидаторы для данных задач
"""

import re
from typing import List, Tuple

class TaskValidator:
    """Валидатор данных задач"""
    
    @staticmethod
    def validate_time_input(time_text: str) -> Tuple[bool, List[str]]:
        """
        Валидирует ввод времени
        Возвращает (успех, список времени или сообщение об ошибке)
        """
        if not time_text.strip():
            return False, ["Время не может быть пустым"]
        
        times = [t.strip() for t in time_text.split(',')]
        valid_times = []
        errors = []
        
        for time_str in times:
            if not time_str:
                continue
                
            # Проверяем формат ЧЧ:ММ
            if not re.match(r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$', time_str):
                errors.append(f"Неверный формат времени: {time_str}")
                continue
            
            valid_times.append(time_str)
        
        if errors:
            return False, errors
        
        if not valid_times:
            return False, ["Не указано ни одного корректного времени"]
        
        return True, valid_times
    
    @staticmethod
    def validate_month_days_input(days_text: str) -> Tuple[bool, List[int]]:
        """
        Валидирует ввод чисел месяца
        Возвращает (успех, список чисел или сообщение об ошибке)
        """
        if not days_text.strip():
            return False, ["Числа месяца не могут быть пустыми"]
        
        days = []
        errors = []
        
        for day_str in days_text.split(','):
            day_str = day_str.strip()
            if not day_str:
                continue
                
            try:
                day = int(day_str)
                if 1 <= day <= 31:
                    days.append(day)
                else:
                    errors.append(f"Число должно быть от 1 до 31: {day_str}")
            except ValueError:
                errors.append(f"Неверный формат числа: {day_str}")
        
        if errors:
            return False, errors
        
        if not days:
            return False, ["Не указано ни одного корректного числа"]
        
        # Убираем дубликаты и сортируем
        days = sorted(list(set(days)))
        return True, days
    
    @staticmethod
    def validate_week_days(days: List[int]) -> Tuple[bool, str]:
        """Валидирует дни недели"""
        if not days:
            return False, "Не выбрано ни одного дня недели"
        
        for day in days:
            if day not in range(7):
                return False, f"Неверный день недели: {day}"
        
        return True, ""
    
    @staticmethod
    def validate_frequency(frequency: str) -> Tuple[bool, str]:
        """Валидирует периодичность"""
        valid_frequencies = ['weekly', 'biweekly', 'monthly']
        if frequency not in valid_frequencies:
            return False, f"Неверная периодичность. Допустимо: {', '.join(valid_frequencies)}"
        
        return True, ""
    
    @staticmethod
    def validate_schedule_type(schedule_type: str) -> Tuple[bool, str]:
        """Валидирует тип расписания"""
        if schedule_type not in ['week_days', 'month_days']:
            return False, "Неверный тип расписания"
        
        return True, ""

class TimeCalculator:
    """Калькулятор времени для задач"""
    
    @staticmethod
    def parse_time(time_str: str) -> Tuple[int, int]:
        """Парсит время из строки в (часы, минуты)"""
        hours, minutes = map(int, time_str.split(':'))
        return hours, minutes
    
    @staticmethod
    def format_time_until_next_execution(next_execution) -> str:
        """Форматирует время до следующего выполнения"""
        if not next_execution:
            return "Не запланировано"
        
        from datetime import datetime
        now = datetime.now()
        
        if next_execution <= now:
            return "Сейчас"
        
        delta = next_execution - now
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}д {hours}ч {minutes}м"
        elif hours > 0:
            return f"{hours}ч {minutes}м"
        else:
            return f"{minutes}м"
