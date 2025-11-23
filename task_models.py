"""
Модели данных для задач с новой структурой
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

class TaskSchedule:
    """Модель расписания задачи"""
    
    def __init__(self):
        self.schedule_type = None  # 'week_days' или 'month_days'
        self.times = []  # список времени в формате ['10:00', '14:30']
        self.week_days = []  # дни недели [0,1,2,3,4,5,6]
        self.month_days = []  # числа месяца [1,10,15,28]
        self.frequency = 'weekly'  # weekly, biweekly, monthly

class TaskData:
    """Модель данных задачи"""
    
    def __init__(self):
        self.id = None
        self.template_id = None
        self.template_name = ""
        self.template_text = ""
        self.template_image = None
        self.group_name = ""
        self.created_by = None
        self.created_at = None
        self.is_active = True
        self.is_test = False
        self.last_executed = None
        self.next_execution = None
        self.target_chat_id = None
        self.schedule = TaskSchedule()
    
    def to_dict(self) -> Dict[str, Any]:
    """Конвертирует в словарь для сохранения в БД"""
    return {
        'id': self.id,
        'template_id': self.template_id,
        'template_name': self.template_name,
        'template_text': self.template_text,
        'template_image': self.template_image,
        'group_name': self.group_name,
        'created_by': self.created_by,
        'created_at': self.created_at,
        'is_active': self.is_active,
        'is_test': self.is_test,
        'last_executed': self.last_executed,
        'next_execution': self.next_execution,
        'target_chat_id': self.target_chat_id,
        'schedule_type': self.schedule.schedule_type,
        'times': json.dumps(self.schedule.times),
        'week_days': json.dumps(self.schedule.week_days),
        'month_days': json.dumps(self.schedule.month_days),
        'frequency': self.schedule.frequency
    }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskData':
        """Создает объект из словаря БД"""
        task = cls()
        task.id = data.get('id')
        task.template_id = data.get('template_id')
        task.template_name = data.get('template_name', '')
        task.template_text = data.get('template_text', '')
        task.template_image = data.get('template_image')
        task.group_name = data.get('group_name', '')
        task.created_by = data.get('created_by')
        task.created_at = data.get('created_at')
        task.is_active = data.get('is_active', True)
        task.is_test = data.get('is_test', False)
        task.last_executed = data.get('last_executed')
        task.next_execution = data.get('next_execution')
        task.target_chat_id = data.get('target_chat_id')
        
        # Загружаем расписание
        task.schedule.schedule_type = data.get('schedule_type')
        task.schedule.times = json.loads(data.get('times', '[]'))
        task.schedule.week_days = json.loads(data.get('week_days', '[]'))
        task.schedule.month_days = json.loads(data.get('month_days', '[]'))
        task.schedule.frequency = data.get('frequency', 'weekly')
        
        return task

class TemplateData:
    """Модель данных шаблона (упрощенная)"""
    
    def __init__(self):
        self.id = None
        self.name = ""
        self.group = ""
        self.text = ""
        self.image = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TemplateData':
        """Создает объект из словаря шаблона"""
        template = cls()
        template.id = data.get('id')
        template.name = data.get('name', '')
        template.group = data.get('group', '')
        template.text = data.get('text', '')
        template.image = data.get('image')
        return template
