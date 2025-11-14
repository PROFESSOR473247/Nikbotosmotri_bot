import json
import os
import uuid
import shutil
from datetime import datetime, timedelta
from database import db

# Дни недели для отображения
DAYS_OF_WEEK = {
    '0': 'Понедельник', '1': 'Вторник', '2': 'Среда',
    '3': 'Четверг', '4': 'Пятница', '5': 'Суббота', '6': 'Воскресенье'
}

# Типы периодичности
FREQUENCY_TYPES = {
    "weekly": "1 в неделю",
    "2_per_month": "2 в месяц", 
    "monthly": "1 в месяц"
}

# Директория для изображений задач
TASK_IMAGES_DIR = "task_images"

# ===== ЗАЩИТНЫЕ ФУНКЦИИ =====

def safe_get_day_name(day):
    """Безопасно возвращает название дня недели"""
    try:
        if isinstance(day, int):
            day = str(day)
        return DAYS_OF_WEEK.get(day, f"День {day}")
    except Exception as e:
        print(f"⚠️ Ошибка получения названия дня {day}: {e}")
        return f"День {day}"

def safe_format_days_list(days):
    """Безопасно форматирует список дней"""
    try:
        if not days:
            return []
        if not isinstance(days, list):
            return []
        return [safe_get_day_name(day) for day in days]
    except Exception as e:
        print(f"⚠️ Ошибка форматирования дней {days}: {e}")
        return []

def safe_get_frequency_name(frequency):
    """Безопасно возвращает название периодичности"""
    try:
        return FREQUENCY_TYPES.get(frequency, frequency)
    except Exception as e:
        print(f"⚠️ Ошибка получения периодичности {frequency}: {e}")
        return frequency

def safe_get_task_value(task, key, default=""):
    """Безопасно получает значение из задачи"""
    try:
        return task.get(key, default)
    except Exception as e:
        print(f"⚠️ Ошибка получения значения {key} из задачи: {e}")
        return default

# ===== ОСНОВНЫЕ ФУНКЦИИ =====

def init_task_files():
    """Инициализирует файлы и директории для задач"""
    try:
        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # Создаем директорию для изображений задач
        if not os.path.exists(TASK_IMAGES_DIR):
            os.makedirs(TASK_IMAGES_DIR)
        
        task_files = ['tasks.json']
        for file in task_files:
            file_path = os.path.join(data_dir, file)
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
        
        print("✅ Файлы и директории задач инициализированы")
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации файлов задач: {e}")
        return False

def init_database():
    """Инициализирует базу данных для задач"""
    try:
        print("🔄 Инициализация базы данных в task_manager...")
        return db.init_database()
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")
        return False

def save_task(task_data):
    """Сохраняет задачу в базу данных"""
    try:
        return db.save_task(task_data)
    except Exception as e:
        print(f"❌ Ошибка сохранения задачи: {e}")
        return False

def create_task(task_data):
    """Создает новую задачу"""
    try:
        # Генерируем ID для задачи
        task_id = create_task_id()
        task_data['id'] = task_id
        
        # Сохраняем в базу данных
        success = save_task(task_data)
        
        if success:
            print(f"✅ Задача создана: {task_data.get('template_name', 'Без названия')} (ID: {task_id})")
            return True, task_id
        else:
            print(f"❌ Ошибка создания задачи: {task_data.get('template_name', 'Без названия')}")
            return False, None
    except Exception as e:
        print(f"❌ Ошибка создания задачи: {e}")
        return False, None

def load_tasks():
    """Загружает все задачи из базы данных"""
    try:
        return db.load_tasks()
    except Exception as e:
        print(f"❌ Ошибка загрузки задач: {e}")
        return {}

def get_all_active_tasks():
    """Возвращает все активные задачи"""
    try:
        all_tasks = load_tasks()
        active_tasks = {}
        
        for task_id, task in all_tasks.items():
            if task.get('is_active', True):
                active_tasks[task_id] = task
        
        return active_tasks
    except Exception as e:
        print(f"❌ Ошибка получения активных задач: {e}")
        return {}

def get_task_by_id(task_id):
    """Возвращает задачу по ID"""
    try:
        tasks = load_tasks()
        return tasks.get(task_id)
    except Exception as e:
        print(f"❌ Ошибка получения задачи по ID {task_id}: {e}")
        return None

def delete_task(task_id):
    """Удаляет задачу"""
    try:
        return db.delete_task(task_id)
    except Exception as e:
        print(f"❌ Ошибка удаления задачи {task_id}: {e}")
        return False

def get_user_accessible_tasks(user_id):
    """Возвращает задачи, доступные пользователю"""
    try:
        # Получаем доступные группы пользователя
        from template_manager import get_user_accessible_groups
        accessible_groups = get_user_accessible_groups(user_id)
        
        # Получаем все активные задачи
        all_tasks = get_all_active_tasks()
        
        # Фильтруем задачи по доступным группам
        user_tasks = {}
        for task_id, task in all_tasks.items():
            if task.get('group_name') in accessible_groups:
                user_tasks[task_id] = task
        
        return user_tasks
    except Exception as e:
        print(f"❌ Ошибка получения доступных задач для пользователя {user_id}: {e}")
        return {}

def format_task_info(task):
    """Форматирует информацию о задаче для отображения"""
    try:
        days_names = safe_format_days_list(task.get('days', []))
        frequency = safe_get_frequency_name(task.get('frequency', 'Не указана'))
        
        task_name = safe_get_task_value(task, 'template_name', 'Без названия')
        task_text = safe_get_task_value(task, 'template_text', '')
        task_time = safe_get_task_value(task, 'time', 'Не указано')
        has_image = '✅ Есть' if task.get('template_image') else '❌ Нет'
        is_active = '✅ Активна' if task.get('is_active', True) else '❌ Неактивна'
        
        info = f"**{task_name}**\n"
        info += f"📄 Текст: {task_text[:100]}...\n"
        info += f"🖼️ Изображение: {has_image}\n"
        info += f"⏰ Время: {task_time} (МСК)\n"
        info += f"📅 Дни: {', '.join(days_names) if days_names else 'Не указаны'}\n"
        info += f"🔄 Периодичность: {frequency}\n"
        info += f"📊 Статус: {is_active}\n"
        
        if task.get('last_executed'):
            info += f"⏱️ Последний запуск: {task['last_executed']}\n"
        
        return info
    except Exception as e:
        print(f"❌ Ошибка форматирования информации о задаче: {e}")
        return "❌ Ошибка загрузки информации о задаче"

def get_task_target_chat(task_id):
    """Возвращает ID целевого чата для задачи"""
    try:
        all_tasks = load_tasks_from_db()
        task = all_tasks.get(task_id)
        return task.get('target_chat_id') if task else None
    except Exception as e:
        print(f"❌ Ошибка получения целевого чата для задачи {task_id}: {e}")
        return None

def update_task_execution_time(task_id, next_execution):
    """Обновляет время следующего выполнения задачи"""
    try:
        all_tasks = load_tasks_from_db()
        message = f"**🏷️ Группа: {group_name}**\n\n"

        if task_id in all_tasks:
            task = all_tasks[task_id]
            task['last_executed'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            task['next_execution'] = next_execution
        for i, (template_id, template) in enumerate(templates, 1):
            days_names = safe_format_days_list(template.get('days', []))
            frequency = safe_get_frequency_name(template.get('frequency', 'Не указана'))
            has_image = "✅ Есть" if template.get('image') else "❌ Нет"

            success = update_task_in_db(task_id, task)
            return success
        
        return False
    except Exception as e:
        print(f"❌ Ошибка обновления времени выполнения задачи {task_id}: {e}")
        return False

def init_task_files():
    """Инициализирует файлы задач (для обратной совместимости)"""
    try:
        # Для PostgreSQL файлы не нужны, но оставляем для совместимости
        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        task_files = ['active_tasks.json', 'test_tasks.json']
        for file in task_files:
            file_path = os.path.join(data_dir, file)
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
        
        print("✅ Файлы задач инициализированы")
        return True
            message += f"**{i}. {template['name']}**\n"
            message += f"   📄 Текст: {template['text'][:80]}...\n"
            message += f"   🖼️ Изображение: {has_image}\n"
            message += f"   ⏰ Время: {template.get('time', 'Не указано')}\n"
            message += f"   📅 Дни: {', '.join(days_names) if days_names else 'Не указаны'}\n"
            message += f"   🔄 Периодичность: {frequency}\n\n"
        
        return message
    except Exception as e:
        print(f"❌ Ошибка инициализации файлов задач: {e}")
        return False
        print(f"❌ Ошибка форматирования детальной информации группы {group_id}: {e}")
        return f"❌ Ошибка загрузки информации о группе"
