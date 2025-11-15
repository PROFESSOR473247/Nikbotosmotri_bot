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
    """Загружает все задачи из базу данных"""
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

def format_task_list_info(tasks):
    """Форматирует список задач для отображения"""
    try:
        if not tasks:
            return "📭 Активных задач нет"
        
        message = "📋 **Список активных задач:**\n\n"
        
        for i, (task_id, task) in enumerate(tasks.items(), 1):
            days_count = len(safe_get_task_value(task, 'days', []))
            has_image = "🖼️" if task.get('template_image') else ""
            task_name = safe_get_task_value(task, 'template_name', 'Без названия')
            task_group = safe_get_task_value(task, 'group_name', 'Не указана')
            task_time = safe_get_task_value(task, 'time', 'Не указано')
            task_text = safe_get_task_value(task, 'template_text', '')
            
            message += f"{i}. **{task_name}** {has_image}\n"
            message += f"   🏷️ Группа: {task_group}\n"
            message += f"   ⏰ Время: {task_time}\n"
            message += f"   📅 Дней: {days_count}\n"
            message += f"   📄 Текст: {task_text[:50]}...\n\n"
        
        return message
    except Exception as e:
        print(f"❌ Ошибка форматирования списка задач: {e}")
        return "❌ Ошибка загрузки списка задач"

def format_task_preview(task):
    """Форматирует превью задачи"""
    try:
        days_names = safe_format_days_list(task.get('days', []))
        frequency = safe_get_frequency_name(task.get('frequency', 'Не указана'))
        
        task_name = safe_get_task_value(task, 'template_name', 'Без названия')
        task_text = safe_get_task_value(task, 'template_text', '')
        task_time = safe_get_task_value(task, 'time', '')
        
        preview = f"📝 **{task_name}**\n\n"
        preview += f"📄 {task_text}\n\n"
        
        if task.get('template_image'):
            preview += "🖼️ *Есть изображение*\n"
        
        if task_time:
            preview += f"⏰ Время отправки: {task_time} (МСК)\n"
        
        if days_names:
            preview += f"📅 Дни: {', '.join(days_names)}\n"
        
        preview += f"🔄 Периодичность: {frequency}"
        
        return preview
    except Exception as e:
        print(f"❌ Ошибка форматирования превью задачи: {e}")
        return "❌ Ошибка загрузки превью задачи"

def create_task_id():
    """Создает уникальный ID для задачи"""
    try:
        return str(uuid.uuid4())[:8]
    except Exception as e:
        print(f"❌ Ошибка создания ID задачи: {e}")
        return str(int(datetime.now().timestamp()))[-8:]

def update_task(task_id, task_data):
    """Обновляет задачу"""
    try:
        task_data['id'] = task_id
        return save_task(task_data)
    except Exception as e:
        print(f"❌ Ошибка обновления задачи {task_id}: {e}")
        return False

def update_task_field(task_id, field_name, field_value):
    """Обновляет конкретное поле задачи"""
    try:
        task = get_task_by_id(task_id)
        if not task:
            return False, "Задача не найдена"
        
        task[field_name] = field_value
        return update_task(task_id, task)
    except Exception as e:
        print(f"❌ Ошибка обновления поля {field_name} задачи {task_id}: {e}")
        return False, f"Ошибка обновления: {e}"

def activate_task(task_id):
    """Активирует задачу"""
    try:
        return update_task_field(task_id, 'is_active', True)
    except Exception as e:
        print(f"❌ Ошибка активации задачи {task_id}: {e}")
        return False, f"Ошибка активации: {e}"

def deactivate_task(task_id):
    """Деактивирует задачу"""
    try:
        return update_task_field(task_id, 'is_active', False)
    except Exception as e:
        print(f"❌ Ошибка деактивации задачи {task_id}: {e}")
        return False, f"Ошибка деактивации: {e}"

def get_tasks_by_group(group_id):
    """Возвращает задачи определенной группы"""
    try:
        tasks = get_all_active_tasks()
        group_tasks = {}
        
        for task_id, task in tasks.items():
            if task.get('group_name') == group_id:
                group_tasks[task_id] = task
        
        return group_tasks
    except Exception as e:
        print(f"❌ Ошибка получения задач группы {group_id}: {e}")
        return {}

# Добавить в task_manager.py в раздел основных функций

def get_active_tasks_by_group(group_id):
    """Возвращает активные задачи определенной группы"""
    try:
        active_tasks = get_all_active_tasks()
        group_tasks = {}
        
        for task_id, task in active_tasks.items():
            if task.get('group_name') == group_id:
                group_tasks[task_id] = task
        
        return group_tasks
    except Exception as e:
        print(f"❌ Ошибка получения активных задач группы {group_id}: {e}")
        return {}

def get_tasks_for_user_by_group(user_id, group_id):
    """Возвращает задачи группы, доступные пользователю"""
    try:
        # Проверяем доступ пользователя к группе
        from template_manager import get_user_accessible_groups
        accessible_groups = get_user_accessible_groups(user_id)
        
        if group_id not in accessible_groups:
            return {}
        
        return get_active_tasks_by_group(group_id)
    except Exception as e:
        print(f"❌ Ошибка получения задач группы {group_id} для пользователя {user_id}: {e}")
        return {}

def format_group_tasks_info(group_id):
    """Форматирует информацию о задачах группы"""
    try:
        tasks = get_active_tasks_by_group(group_id)
        
        if not tasks:
            return f"📭 В этой группе нет активных задач"
        
        # Получаем название группы
        from template_manager import load_groups
        groups_data = load_groups()
        group_name = groups_data['groups'].get(group_id, {}).get('name', group_id)
        
        message = f"📋 **Активные задачи группы '{group_name}':**\n\n"
        
        for i, (task_id, task) in enumerate(tasks.items(), 1):
            days_count = len(safe_get_task_value(task, 'days', []))
            has_image = "🖼️" if task.get('template_image') else ""
            task_name = safe_get_task_value(task, 'template_name', 'Без названия')
            task_time = safe_get_task_value(task, 'time', 'Не указано')
            task_text = safe_get_task_value(task, 'template_text', '')
            
            message += f"{i}. **{task_name}** {has_image}\n"
            message += f"   ⏰ {task_time} | 📅 {days_count} дней\n"
            message += f"   📄 {task_text[:60]}...\n\n"
        
        return message
    except Exception as e:
        print(f"❌ Ошибка форматирования информации о группе задач {group_id}: {e}")
        return f"❌ Ошибка загрузки информации о группе"

def get_user_tasks_by_groups(user_id):
    """Возвращает задачи пользователя, сгруппированные по группам"""
    try:
        from template_manager import get_user_accessible_groups
        accessible_groups = get_user_accessible_groups(user_id)
        
        tasks_by_groups = {}
        for group_id in accessible_groups:
            group_tasks = get_active_tasks_by_group(group_id)
            if group_tasks:
                tasks_by_groups[group_id] = group_tasks
        
        return tasks_by_groups
    except Exception as e:
        print(f"❌ Ошибка получения задач по группам для пользователя {user_id}: {e}")
        return {}

def format_user_tasks_by_groups(user_id):
    """Форматирует информацию о задачах пользователя по группам"""
    try:
        tasks_by_groups = get_user_tasks_by_groups(user_id)
        
        if not tasks_by_groups:
            return "📭 У вас нет активных задач"
        
        from template_manager import load_groups
        groups_data = load_groups()
        
        message = "📋 **Ваши активные задачи по группам:**\n\n"
        
        for group_id, tasks in tasks_by_groups.items():
            group_name = groups_data['groups'].get(group_id, {}).get('name', group_id)
            message += f"**🏷️ {group_name}:**\n"
            
            for i, (task_id, task) in enumerate(tasks.items(), 1):
                task_name = safe_get_task_value(task, 'template_name', 'Без названия')
                task_time = safe_get_task_value(task, 'time', 'Не указано')
                
                message += f"  {i}. **{task_name}**\n"
                message += f"      ⏰ {task_time}\n"
            
            message += "\n"
        
        total_tasks = sum(len(tasks) for tasks in tasks_by_groups.values())
        message += f"**Всего активных задач:** {total_tasks}"
        
        return message
    except Exception as e:
        print(f"❌ Ошибка форматирования задач по группам: {e}")
        return "❌ Ошибка загрузки информации о задачах"
        
def get_task_stats():
    """Возвращает статистику по задачам"""
    try:
        all_tasks = load_tasks()
        active_tasks = get_all_active_tasks()
        
        stats = {
            'total_tasks': len(all_tasks),
            'active_tasks': len(active_tasks),
            'inactive_tasks': len(all_tasks) - len(active_tasks),
            'tasks_with_images': 0,
            'tasks_with_schedule': 0
        }
        
        for task in all_tasks.values():
            if task.get('template_image'):
                stats['tasks_with_images'] += 1
            if task.get('time') and task.get('days'):
                stats['tasks_with_schedule'] += 1
        
        return stats
    except Exception as e:
        print(f"❌ Ошибка получения статистики задач: {e}")
        return {
            'total_tasks': 0,
            'active_tasks': 0,
            'inactive_tasks': 0,
            'tasks_with_images': 0,
            'tasks_with_schedule': 0
        }

# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С ИЗОБРАЖЕНИЯМИ =====

def save_task_image(image_file, task_id):
    """Сохраняет изображение для задачи"""
    try:
        # Создаем уникальное имя файла
        file_extension = os.path.splitext(image_file.filename)[1] if hasattr(image_file, 'filename') else '.jpg'
        image_filename = f"{task_id}{file_extension}"
        image_path = os.path.join(TASK_IMAGES_DIR, image_filename)
        
        # Сохраняем файл
        with open(image_path, 'wb') as f:
            if hasattr(image_file, 'getvalue'):
                f.write(image_file.getvalue())
            else:
                f.write(image_file)
        
        print(f"✅ Изображение задачи сохранено: {image_path}")
        return image_path
        
    except Exception as e:
        print(f"❌ Ошибка сохранения изображения задачи: {e}")
        return None

def delete_task_image(image_path):
    """Удаляет изображение задачи"""
    try:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
            print(f"✅ Изображение задачи удалено: {image_path}")
            return True
        return False
    except Exception as e:
        print(f"❌ Ошибка удаления изображения задачи: {e}")
        return False

def get_task_image_path(task_id):
    """Возвращает путь к изображению задачи"""
    try:
        # Ищем файл с любым расширением
        if not os.path.exists(TASK_IMAGES_DIR):
            return None
        
        for filename in os.listdir(TASK_IMAGES_DIR):
            if filename.startswith(task_id):
                return os.path.join(TASK_IMAGES_DIR, filename)
        
        return None
    except Exception as e:
        print(f"❌ Ошибка получения пути изображения для задачи {task_id}: {e}")
        return None

# ===== ФУНКЦИИ ДЛЯ ПЛАНИРОВЩИКА =====

def get_tasks_for_execution():
    """Возвращает задачи, готовые к выполнению"""
    try:
        active_tasks = get_all_active_tasks()
        tasks_to_execute = {}
        
        current_time = datetime.now()
        current_weekday = str(current_time.weekday())  # 0-6, где 0 - понедельник
        
        for task_id, task in active_tasks.items():
            # Проверяем, сегодня ли день выполнения
            if current_weekday in task.get('days', []):
                tasks_to_execute[task_id] = task
        
        return tasks_to_execute
    except Exception as e:
        print(f"❌ Ошибка получения задач для выполнения: {e}")
        return {}

def update_task_execution_time(task_id):
    """Обновляет время последнего выполнения задачи"""
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return update_task_field(task_id, 'last_executed', current_time)
    except Exception as e:
        print(f"❌ Ошибка обновления времени выполнения задачи {task_id}: {e}")
        return False
        
        # Добавить в конец task_manager.py перед последними строками инициализации

def create_task_from_template(template, target_chat_id=None, is_test=False):
    """Создает задачу на основе шаблона"""
    try:
        task_data = {
            'template_id': template.get('id'),
            'template_name': template.get('name', 'Без названия'),
            'template_text': template.get('text', ''),
            'template_image': template.get('image'),
            'group_name': template.get('group', ''),
            'time': template.get('time', ''),
            'days': template.get('days', []),
            'frequency': template.get('frequency', 'weekly'),
            'created_by': template.get('created_by'),
            'is_active': True,
            'is_test': is_test,
            'target_chat_id': target_chat_id
        }
        
        success, task_id = create_task(task_data)
        return success, task_id
        
    except Exception as e:
        print(f"❌ Ошибка создания задачи из шаблона: {e}")
        return False, None

def get_tasks_by_template(template_id):
    """Возвращает задачи, созданные на основе указанного шаблона"""
    try:
        all_tasks = load_tasks()
        template_tasks = {}
        
        for task_id, task in all_tasks.items():
            if task.get('template_id') == template_id:
                template_tasks[task_id] = task
        
        return template_tasks
    except Exception as e:
        print(f"❌ Ошибка получения задач по шаблону {template_id}: {e}")
        return {}

def format_template_tasks_info(template_id):
    """Форматирует информацию о задачах, созданных из шаблона"""
    try:
        tasks = get_tasks_by_template(template_id)
        
        if not tasks:
            return "📭 Нет задач, созданных из этого шаблона"
        
        message = f"📋 **Задачи, созданные из шаблона:**\n\n"
        
        for i, (task_id, task) in enumerate(tasks.items(), 1):
            is_active = "✅ Активна" if task.get('is_active', True) else "❌ Неактивна"
            is_test = "🧪 Тестовая" if task.get('is_test', False) else "📤 Рабочая"
            task_name = safe_get_task_value(task, 'template_name', 'Без названия')
            
            message += f"{i}. **{task_name}**\n"
            message += f"   📊 Статус: {is_active} | {is_test}\n"
            message += f"   🆔 ID задачи: `{task_id}`\n"
            
            if task.get('target_chat_id'):
                message += f"   💬 Целевой чат: {task['target_chat_id']}\n"
            
            if task.get('last_executed'):
                message += f"   ⏱️ Последний запуск: {task['last_executed']}\n"
            
            message += "\n"
        
        return message
    except Exception as e:
        print(f"❌ Ошибка форматирования информации о задачах шаблона: {e}")
        return "❌ Ошибка загрузки информации о задачах"

def validate_task_data(task_data):
    """Проверяет данные задачи на валидность"""
    try:
        required_fields = ['template_name', 'group_name']
        for field in required_fields:
            if not task_data.get(field):
                return False, f"Отсутствует обязательное поле: {field}"
        
        # Проверяем время
        if task_data.get('time'):
            try:
                hour, minute = map(int, task_data['time'].split(':'))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    return False, "Неверный формат времени"
            except ValueError:
                return False, "Неверный формат времени"
        
        return True, "OK"
    except Exception as e:
        print(f"❌ Ошибка валидации данных задачи: {e}")
        return False, f"Ошибка валидации: {e}"

def get_frequency_types():
    """Возвращает доступные типы периодичности"""
    return FREQUENCY_TYPES

def get_week_days():
    """Возвращает дни недели для выбора"""
    return DAYS_OF_WEEK

def delete_task_and_image(task_id):
    """Удаляет задачу и связанное с ней изображение"""
    try:
        # Получаем информацию о задаче
        task = get_task_by_id(task_id)
        if not task:
            return False, "Задача не найдена"
        
        # Удаляем изображение если есть
        if task.get('template_image'):
            delete_task_image(task['template_image'])
        
        # Удаляем задачу из базы данных
        success = delete_task(task_id)
        
        if success:
            return True, f"Задача '{task['template_name']}' успешно удалена"
        else:
            return False, "Ошибка при удалении задачи"
    except Exception as e:
        print(f"❌ Ошибка удаления задачи и изображения {task_id}: {e}")
        return False, f"Ошибка удаления: {e}"

# Инициализация при импорте
print("📥 Task_manager загружен")
init_task_files()
init_database()
print("✅ Task_manager инициализирован")

# Инициализация при импорте
print("📥 Task_manager загружен")
init_task_files()
init_database()
print("✅ Task_manager инициализирован")