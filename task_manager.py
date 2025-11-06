import json
import os
import uuid
from datetime import datetime, timedelta
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TASKS_FILE = 'data/active_tasks.json'
TEST_TASKS_FILE = 'data/test_tasks.json'

def ensure_data_directory():
    """Создает необходимые директории если их нет"""
    os.makedirs('data', exist_ok=True)

def init_task_files():
    """Инициализирует файлы задач если их нет"""
    ensure_data_directory()
    
    if not os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
    
    if not os.path.exists(TEST_TASKS_FILE):
        with open(TEST_TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)

def load_active_tasks():
    """Загружает активные задачи"""
    try:
        if os.path.exists(TASKS_FILE):
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Ошибка загрузки активных задач: {e}")
        return {}

def save_active_tasks(tasks_data):
    """Сохраняет активные задачи"""
    try:
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tasks_data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения активных задач: {e}")
        return False

def load_test_tasks():
    """Загружает тестовые задачи"""
    try:
        if os.path.exists(TEST_TASKS_FILE):
            with open(TEST_TASKS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Ошибка загрузки тестовых задач: {e}")
        return {}

def create_task_from_template(template_data, created_by, is_test=False):
    """Создает задачу из шаблона"""
    tasks_data = load_active_tasks() if not is_test else load_test_tasks()
    task_id = str(uuid.uuid4())[:8]
    
    task_data = {
        'id': task_id,
        'template_id': template_data.get('id'),
        'template_name': template_data.get('name'),
        'template_text': template_data.get('text'),
        'template_image': template_data.get('image'),
        'group': template_data.get('group'),
        'time': template_data.get('time'),
        'days': template_data.get('days', []),
        'frequency': template_data.get('frequency'),
        'created_by': created_by,
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'is_active': True,
        'is_test': is_test,
        'last_executed': None,
        'next_execution': calculate_next_execution(template_data)
    }
    
    tasks_data[task_id] = task_data
    
    if is_test:
        # Для тестовых задач сохраняем в отдельный файл
        try:
            with open(TEST_TASKS_FILE, 'w', encoding='utf-8') as f:
                json.dump(tasks_data, f, ensure_ascii=False, indent=4)
            return True, task_id
        except Exception as e:
            logger.error(f"Ошибка сохранения тестовой задачи: {e}")
            return False, None
    else:
        if save_active_tasks(tasks_data):
            return True, task_id
        return False, None

def calculate_next_execution(template_data):
    """Вычисляет следующее время выполнения задачи"""
    now = datetime.now()
    time_str = template_data.get('time', '00:00')
    
    try:
        hours, minutes = map(int, time_str.split(':'))
        # Базовое время на сегодня
        base_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
        
        # Если время уже прошло сегодня, планируем на завтра
        if base_time < now:
            base_time += timedelta(days=1)
        
        return base_time.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return now.strftime("%Y-%m-%d %H:%M:%S")

def get_active_tasks_by_group(group_id):
    """Возвращает активные задачи по группе"""
    tasks_data = load_active_tasks()
    tasks = []
    
    for task_id, task in tasks_data.items():
        if task.get('group') == group_id and task.get('is_active', False):
            tasks.append((task_id, task))
    
    return tasks

def get_task_by_id(task_id):
    """Возвращает задачу по ID"""
    tasks_data = load_active_tasks()
    return tasks_data.get(task_id)

def deactivate_task(task_id):
    """Деактивирует задачу"""
    tasks_data = load_active_tasks()
    
    if task_id not in tasks_data:
        return False, "Задача не найдена"
    
    tasks_data[task_id]['is_active'] = False
    tasks_data[task_id]['deactivated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if save_active_tasks(tasks_data):
        return True, "Задача деактивирована"
    return False, "Ошибка деактивации"

def format_task_info(task_data):
    """Форматирует информацию о задаче для отображения"""
    days_names = []
    if task_data.get('days'):
        from template_manager import DAYS_OF_WEEK
        days_names = [DAYS_OF_WEEK[day] for day in task_data['days']]
    
    frequency_map = {
        "weekly": "1 в неделю",
        "2_per_month": "2 в месяц",
        "monthly": "1 в месяц"
    }
    frequency = frequency_map.get(task_data.get('frequency'), task_data.get('frequency', 'Не указана'))
    
    info = f"📋 **Задача: {task_data['template_name']}**\n\n"
    info += f"🏷️ **Группа:** {task_data.get('group', 'Не указана')}\n"
    info += f"⏰ **Время:** {task_data.get('time', 'Не указано')} (МСК)\n"
    info += f"📅 **Дни:** {', '.join(days_names) if days_names else 'Не указаны'}\n"
    info += f"🔄 **Периодичность:** {frequency}\n"
    info += f"📄 **Текст:** {task_data.get('template_text', '')[:100]}...\n"
    info += f"🖼️ **Изображение:** {'✅ Есть' if task_data.get('template_image') else '❌ Нет'}\n"
    info += f"🔧 **Тип:** {'🧪 Тестовая' if task_data.get('is_test') else '📅 Регулярная'}\n"
    info += f"📊 **Статус:** {'✅ Активна' if task_data.get('is_active') else '❌ Неактивна'}\n"
    
    if task_data.get('next_execution'):
        info += f"⏱️ **Следующее выполнение:** {task_data['next_execution']}\n"
    
    return info

def get_all_active_tasks():
    """Возвращает все активные задачи"""
    tasks_data = load_active_tasks()
    active_tasks = {}
    
    for task_id, task in tasks_data.items():
        if task.get('is_active', False):
            active_tasks[task_id] = task
    
    return active_tasks

# Инициализация при импорте
init_task_files()