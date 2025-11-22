import logging
import os
import json
import uuid
from datetime import datetime
from database import db
from task_models import TaskData, TemplateData
from task_calculators import TaskScheduleCalculator, TaskFormatter
from task_validators import TaskValidator

logger = logging.getLogger(__name__)

# Директория для изображений задач
TASK_IMAGES_DIR = "task_images"

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
        if isinstance(task_data, TaskData):
            return db.save_task(task_data)
        else:
            # Конвертируем старый формат в новый
            task = TaskData()
            task.id = task_data.get('id')
            task.template_id = task_data.get('template_id')
            task.template_name = task_data.get('template_name', '')
            task.template_text = task_data.get('template_text', '')
            task.template_image = task_data.get('template_image')
            task.group_name = task_data.get('group_name', '')
            task.created_by = task_data.get('created_by')
            task.created_at = task_data.get('created_at')
            task.is_active = task_data.get('is_active', True)
            task.is_test = task_data.get('is_test', False)
            task.last_executed = task_data.get('last_executed')
            task.next_execution = task_data.get('next_execution')
            task.target_chat_id = task_data.get('target_chat_id')
            
            # Старые поля расписания конвертируем в новые
            if task_data.get('time'):
                task.schedule.times = [task_data['time']]
            if task_data.get('days'):
                task.schedule.week_days = task_data['days']
                task.schedule.schedule_type = 'week_days'
            if task_data.get('frequency'):
                task.schedule.frequency = task_data['frequency']
            
            return db.save_task(task)
    except Exception as e:
        print(f"❌ Ошибка сохранения задачи: {e}")
        return False

def load_tasks():
    """Загружает все задачи из базы данных"""
    try:
        return db.load_tasks()
    except Exception as e:
        print(f"❌ Ошибка загрузки задач: {e}")
        return {}

def create_task(task_data):
    """Создает новую задачу"""
    try:
        # Генерируем ID для задачи
        task_id = create_task_id()
        
        if isinstance(task_data, TaskData):
            task_data.id = task_id
        else:
            task_data['id'] = task_id
        
        print(f"🆔 Сгенерирован ID задачи: {task_id}")
        
        # Сохраняем в базу данных
        success = save_task(task_data)
        
        if success:
            print(f"✅ Задача создана: {task_data.template_name if isinstance(task_data, TaskData) else task_data.get('template_name', 'Без названия')} (ID: {task_id})")
            
            # Рассчитываем следующее выполнение
            if isinstance(task_data, TaskData):
                update_task_next_execution(task_id)
            
            return True, task_id
        else:
            print(f"❌ Ошибка создания задачи")
            return False, None
    except Exception as e:
        print(f"❌ Ошибка создания задачи: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def get_all_active_tasks():
    """Возвращает все активные задачи"""
    try:
        all_tasks = load_tasks()
        active_tasks = {}
        
        for task_id, task in all_tasks.items():
            if task.is_active:
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
            if task.group_name in accessible_groups:
                user_tasks[task_id] = task
        
        return user_tasks
    except Exception as e:
        print(f"❌ Ошибка получения доступных задач для пользователя {user_id}: {e}")
        return {}

def format_task_info(task):
    """Форматирует информацию о задаче для отображения"""
    try:
        return TaskFormatter.format_task_info(task)
    except Exception as e:
        print(f"❌ Ошибка форматирования информации о задаче: {e}")
        return "❌ Ошибка загрузки информации о задаче"

def format_task_list_info(tasks):
    """Форматирует список задач для отображения"""
    try:
        if not tasks:
            return "📭 Активных задач нет"
        
        # Конвертируем словарь в список если нужно
        if isinstance(tasks, dict):
            tasks_list = list(tasks.values())
        else:
            tasks_list = tasks
            
        return TaskFormatter.format_task_list_info(tasks_list)
    except Exception as e:
        print(f"❌ Ошибка форматирования списка задач: {e}")
        return "❌ Ошибка загрузки списка задач"

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
        if isinstance(task_data, TaskData):
            task_data.id = task_id
        else:
            task_data['id'] = task_id
            
        success = db.update_task(task_id, task_data)
        
        if success:
            # Обновляем следующее выполнение
            update_task_next_execution(task_id)
        
        return success
    except Exception as e:
        print(f"❌ Ошибка обновления задачи {task_id}: {e}")
        return False

def update_task_field(task_id, field_name, field_value):
    """Обновляет конкретное поле задачи"""
    try:
        task = get_task_by_id(task_id)
        if not task:
            return False, "Задача не найдена"
        
        setattr(task, field_name, field_value)
        success = update_task(task_id, task)
        if success:
            return True, f"Поле {field_name} успешно обновлено"
        else:
            return False, f"Ошибка обновления поля {field_name}"
    except Exception as e:
        print(f"❌ Ошибка обновления поля {field_name} задачи {task_id}: {e}")
        return False, f"Ошибка обновления: {e}"

def activate_task(task_id):
    """Активирует задачу"""
    try:
        success = update_task_field(task_id, 'is_active', True)
        if success:
            return True, f"Задача {task_id} успешно активирована"
        else:
            return False, f"Ошибка активации задачи {task_id}"
    except Exception as e:
        print(f"❌ Ошибка активации задачи {task_id}: {e}")
        return False, f"Ошибка активации: {e}"

def deactivate_task(task_id):
    """Деактивирует задачу"""
    try:
        success = update_task_field(task_id, 'is_active', False)
        if success:
            return True, f"Задача {task_id} успешно деактивирована"
        else:
            return False, f"Ошибка деактивации задачи {task_id}"
    except Exception as e:
        print(f"❌ Ошибка деактивации задачи {task_id}: {e}")
        return False, f"Ошибка деактивации: {e}"

def get_tasks_by_group(group_id):
    """Возвращает задачи определенной группы"""
    try:
        tasks = get_all_active_tasks()
        group_tasks = {}
        
        for task_id, task in tasks.items():
            if task.group_name == group_id:
                group_tasks[task_id] = task
        
        return group_tasks
    except Exception as e:
        print(f"❌ Ошибка получения задач группы {group_id}: {e}")
        return {}

def get_active_tasks_by_group(group_id):
    """Возвращает активные задачи определенной группы"""
    try:
        active_tasks = get_all_active_tasks()
        group_tasks = {}
        
        for task_id, task in active_tasks.items():
            if task.group_name == group_id:
                group_tasks[task_id] = task
        
        return group_tasks
    except Exception as e:
        print(f"❌ Ошибка получения активных задач группы {group_id}: {e}")
        return {}

def create_task_from_template(template_data, created_by, target_chat_id=None, is_test=False):
    """Создает задачу из шаблона (для обратной совместимости)"""
    logger.info("🔄 Начало создания задачи из шаблона...")
    try:
        print(f"🔄 Создание задачи из шаблона: {template_data.get('name')}")
        
        # Создаем объект задачи
        task = TaskData()
        task.template_id = template_data.get('id')
        task.template_name = template_data.get('name', 'Без названия')
        task.template_text = template_data.get('text', '')
        task.template_image = template_data.get('image')
        task.group_name = template_data.get('group', '')
        task.created_by = created_by
        task.is_active = True
        task.is_test = is_test
        task.target_chat_id = target_chat_id
        
        # Для тестовых задач устанавливаем специальные параметры
        if is_test:
            task.schedule.times = ['12:00']  # Время по умолчанию для тестов
            task.schedule.schedule_type = 'week_days'
            task.schedule.week_days = [0]  # Понедельник по умолчанию
            task.schedule.frequency = 'weekly'
        else:
            # Обычные задачи - расписание будет установлено позже
            pass
        
        print(f"📦 Данные для сохранения задачи: {task.template_name}")
        
        # Создаем задачу
        success, task_id = create_task(task)
        
        if success:
            if is_test:
                # Для тестовых задач сразу планируем выполнение
                from task_scheduler import schedule_test_task
                schedule_success = schedule_test_task(task_id, task)
                if schedule_success:
                    print(f"✅ Тестовая задача запланирована на выполнение")
                else:
                    print(f"❌ Ошибка планирования тестовой задачи")
            else:
                # Для обычных задач планируем по расписанию
                from task_scheduler import schedule_task
                schedule_success = schedule_task(task_id, task)
                if schedule_success:
                    print(f"✅ Обычная задача запланирована по расписанию")
                else:
                    print(f"❌ Ошибка планирования обычной задачи")
            
            print(f"✅ Задача успешно создана: {task_id}")
        else:
            print("❌ Ошибка при вызове create_task")
            
        return success, task_id
        
    except Exception as e:
        print(f"❌ Критическая ошибка в create_task_from_template: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def update_task_execution_time(task_id):
    """Обновляет время последнего выполнения задачи"""
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return update_task_field(task_id, 'last_executed', current_time)
    except Exception as e:
        print(f"❌ Ошибка обновления времени выполнения задачи {task_id}: {e}")
        return False

def update_task_next_execution(task_id):
    """Обновляет следующее время выполнения задачи"""
    try:
        task = get_task_by_id(task_id)
        if not task:
            return False
        
        next_execution = TaskScheduleCalculator.calculate_next_execution(task)
        if next_execution:
            task.next_execution = next_execution.strftime("%Y-%m-%d %H:%M:%S")
            return update_task(task_id, task)
        
        return False
    except Exception as e:
        print(f"❌ Ошибка обновления следующего выполнения задачи {task_id}: {e}")
        return False

def create_task_with_schedule(template_data, created_by, target_chat_id, schedule_data):
    """Создает задачу с полным расписанием"""
    try:
        # Создаем объект задачи
        task = TaskData()
        task.template_id = template_data.get('id')
        task.template_name = template_data.get('name', 'Без названия')
        task.template_text = template_data.get('text', '')
        task.template_image = template_data.get('image')
        task.group_name = template_data.get('group', '')
        task.created_by = created_by
        task.is_active = True
        task.is_test = False
        task.target_chat_id = target_chat_id
        
        # Устанавливаем расписание
        task.schedule.schedule_type = schedule_data.get('schedule_type')
        task.schedule.times = schedule_data.get('times', [])
        task.schedule.week_days = schedule_data.get('week_days', [])
        task.schedule.month_days = schedule_data.get('month_days', [])
        task.schedule.frequency = schedule_data.get('frequency', 'weekly')
        
        print(f"📦 Создание задачи с расписанием: {task.template_name}")
        print(f"   Тип расписания: {task.schedule.schedule_type}")
        print(f"   Время: {task.schedule.times}")
        print(f"   Частота: {task.schedule.frequency}")
        
        # Создаем задачу
        success, task_id = create_task(task)
        
        if success:
            # Планируем задачу
            from task_scheduler import schedule_task
            schedule_success = schedule_task(task_id, task)
            if schedule_success:
                print(f"✅ Задача запланирована по расписанию")
            else:
                print(f"❌ Ошибка планирования задачи")
        
        return success, task_id
        
    except Exception as e:
        print(f"❌ Ошибка создания задачи с расписанием: {e}")
        import traceback
        traceback.print_exc()
        return False, None

# Инициализация при импорте
print("📥 Task_manager загружен")
init_task_files()
init_database()
print("✅ Task_manager инициализирован")