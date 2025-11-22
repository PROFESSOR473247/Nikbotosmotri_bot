"""
Калькуляторы для расчета времени выполнения задач
"""

from datetime import datetime, timedelta
from typing import List, Optional
from task_models import TaskData

class TaskScheduleCalculator:
    """Калькулятор расписания задач"""
    
    @staticmethod
    def calculate_next_execution(task: TaskData) -> Optional[datetime]:
        """
        Рассчитывает следующее время выполнения задачи
        """
        if not task.schedule.times:
            return None
        
        now = datetime.now()
        
        if task.schedule.schedule_type == 'week_days':
            return TaskScheduleCalculator._calculate_week_days_schedule(task, now)
        elif task.schedule.schedule_type == 'month_days':
            return TaskScheduleCalculator._calculate_month_days_schedule(task, now)
        else:
            return None
    
    @staticmethod
    def _calculate_week_days_schedule(task: TaskData, now: datetime) -> Optional[datetime]:
        """Рассчитывает расписание для дней недели"""
        if not task.schedule.week_days:
            return None
        
        # Получаем текущий день недели (0-пн, 6-вс)
        current_weekday = now.weekday()
        current_time = now.time()
        
        # Проверяем выполнения на сегодня
        for time_str in task.schedule.times:
            task_time = TaskScheduleCalculator._parse_time_string(time_str)
            if task_time > current_time:
                # Если есть время сегодня и сегодня подходящий день
                if current_weekday in task.schedule.week_days:
                    candidate = datetime.combine(now.date(), task_time)
                    if TaskScheduleCalculator._is_week_valid(task, candidate):
                        return candidate
        
        # Ищем следующий подходящий день
        for day_offset in range(1, 8):  # Проверяем следующие 7 дней
            next_date = now + timedelta(days=day_offset)
            next_weekday = next_date.weekday()
            
            if next_weekday in task.schedule.week_days:
                # Берем первое время в этот день
                if task.schedule.times:
                    task_time = TaskScheduleCalculator._parse_time_string(task.schedule.times[0])
                    candidate = datetime.combine(next_date.date(), task_time)
                    if TaskScheduleCalculator._is_week_valid(task, candidate):
                        return candidate
        
        return None
    
    @staticmethod
    def _calculate_month_days_schedule(task: TaskData, now: datetime) -> Optional[datetime]:
        """Рассчитывает расписание для чисел месяца"""
        if not task.schedule.month_days:
            return None
        
        current_time = now.time()
        current_day = now.day
        current_month = now.month
        current_year = now.year
        
        # Получаем все возможные даты выполнения в текущем и следующем месяце
        all_dates = []
        
        for month_offset in [0, 1]:  # Текущий и следующий месяц
            year = current_year
            month = current_month + month_offset
            
            if month > 12:
                month = 1
                year += 1
            
            for day in task.schedule.month_days:
                try:
                    date_candidate = datetime(year, month, day)
                    # Исключаем прошедшие даты в текущем месяце
                    if month_offset == 0 and (date_candidate.date() < now.date() or 
                                            (date_candidate.date() == now.date() and 
                                             TaskScheduleCalculator._parse_time_string(task.schedule.times[0]) <= current_time)):
                        continue
                    all_dates.append(date_candidate)
                except ValueError:
                    # Некорректная дата (например, 31 февраля)
                    continue
        
        # Сортируем даты и находим первую подходящую
        all_dates.sort()
        
        for date_candidate in all_dates:
            for time_str in task.schedule.times:
                task_time = TaskScheduleCalculator._parse_time_string(time_str)
                candidate = datetime.combine(date_candidate.date(), task_time)
                
                # Для текущего дня проверяем время
                if candidate.date() == now.date() and task_time <= current_time:
                    continue
                
                if candidate > now:
                    return candidate
        
        return None
    
    @staticmethod
    def _is_week_valid(task: TaskData, execution_date: datetime) -> bool:
        """Проверяет, подходит ли неделя для выполнения по периодичности"""
        if task.schedule.frequency == 'weekly':
            return True
        elif task.schedule.frequency == 'biweekly':
            # Раз в 2 недели - считаем с начала года
            week_number = execution_date.isocalendar()[1]
            return week_number % 2 == 1  # Нечетные недели
        elif task.schedule.frequency == 'monthly':
            # Раз в месяц - только первая неделя месяца
            return execution_date.day <= 7
        else:
            return True
    
    @staticmethod
    def _parse_time_string(time_str: str) -> datetime.time:
        """Парсит строку времени в объект time"""
        from datetime import time
        hours, minutes = map(int, time_str.split(':'))
        return time(hours, minutes)
    
    @staticmethod
    def get_all_execution_times(task: TaskData, start_date: datetime, end_date: datetime) -> List[datetime]:
        """
        Возвращает все времена выполнения задачи в указанном периоде
        """
        execution_times = []
        current_date = start_date
        
        while current_date <= end_date:
            if task.schedule.schedule_type == 'week_days':
                if current_date.weekday() in task.schedule.week_days:
                    if TaskScheduleCalculator._is_week_valid(task, current_date):
                        for time_str in task.schedule.times:
                            task_time = TaskScheduleCalculator._parse_time_string(time_str)
                            execution_time = datetime.combine(current_date.date(), task_time)
                            if start_date <= execution_time <= end_date:
                                execution_times.append(execution_time)
            
            elif task.schedule.schedule_type == 'month_days':
                if current_date.day in task.schedule.month_days:
                    for time_str in task.schedule.times:
                        task_time = TaskScheduleCalculator._parse_time_string(time_str)
                        execution_time = datetime.combine(current_date.date(), task_time)
                        if start_date <= execution_time <= end_date:
                            execution_times.append(execution_time)
            
            current_date += timedelta(days=1)
        
        return sorted(execution_times)

class TaskFormatter:
    """Форматировщик информации о задачах"""
    
    DAYS_OF_WEEK = {
        0: 'Понедельник', 1: 'Вторник', 2: 'Среда',
        3: 'Четверг', 4: 'Пятница', 5: 'Суббота', 6: 'Воскресенье'
    }
    
    FREQUENCY_NAMES = {
        'weekly': '1 раз в неделю',
        'biweekly': '1 раз в 2 недели', 
        'monthly': '1 раз в месяц'
    }
    
    @staticmethod
    def format_task_info(task: TaskData) -> str:
        """Форматирует полную информацию о задаче"""
        lines = []
        
        lines.append(f"**{task.template_name}**")
        lines.append(f"📄 Текст: {task.template_text[:100]}...")
        lines.append(f"🖼️ Изображение: {'✅ Есть' if task.template_image else '❌ Нет'}")
        lines.append(f"💬 Чат: {task.target_chat_id}")
        
        # Информация о расписании
        schedule_info = TaskFormatter._format_schedule_info(task)
        lines.extend(schedule_info)
        
        # Статус
        status = "✅ Активна" if task.is_active else "❌ Неактивна"
        task_type = "🧪 Тестовая" if task.is_test else "📅 Регулярная"
        lines.append(f"📊 Статус: {status} ({task_type})")
        
        if task.last_executed:
            lines.append(f"⏱️ Последний запуск: {task.last_executed}")
        
        if task.next_execution:
            from task_validators import TimeCalculator
            time_until = TimeCalculator.format_time_until_next_execution(task.next_execution)
            lines.append(f"⏰ Следующий запуск: через {time_until}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_schedule_info(task: TaskData) -> List[str]:
        """Форматирует информацию о расписании"""
        lines = []
        
        # Время отправки
        times_str = ", ".join(task.schedule.times)
        lines.append(f"⏰ Время: {times_str} (МСК)")
        
        # Тип расписания
        if task.schedule.schedule_type == 'week_days':
            days_names = [TaskFormatter.DAYS_OF_WEEK[day] for day in task.schedule.week_days]
            lines.append(f"📅 Дни недели: {', '.join(days_names)}")
        elif task.schedule.schedule_type == 'month_days':
            days_str = ", ".join(map(str, task.schedule.month_days))
            lines.append(f"📅 Числа месяца: {days_str}")
        
        # Периодичность
        freq_name = TaskFormatter.FREQUENCY_NAMES.get(task.schedule.frequency, task.schedule.frequency)
        lines.append(f"🔄 Периодичность: {freq_name}")
        
        return lines
    
    @staticmethod
    def format_task_list_info(tasks: List[TaskData]) -> str:
        """Форматирует список задач для отображения"""
        if not tasks:
            return "📭 Активных задач нет"
        
        message = "📋 **Список активных задач:**\n\n"
        
        for i, task in enumerate(tasks, 1):
            has_image = "🖼️" if task.template_image else ""
            task_type = "🧪" if task.is_test else "📅"
            
            message += f"{i}. **{task.template_name}** {has_image} {task_type}\n"
            
            # Краткая информация о расписании
            if task.schedule.schedule_type == 'week_days':
                days_count = len(task.schedule.week_days)
                message += f"   📅 {days_count} дней/неделю"
            else:
                days_count = len(task.schedule.month_days)
                message += f"   📅 {days_count} чисел/месяц"
            
            times_count = len(task.schedule.times)
            message += f" | ⏰ {times_count} времени\n"
            
            if task.next_execution:
                from task_validators import TimeCalculator
                time_until = TimeCalculator.format_time_until_next_execution(task.next_execution)
                message += f"   ⏰ Следующий: через {time_until}\n"
            
            message += "\n"
        
        return message
