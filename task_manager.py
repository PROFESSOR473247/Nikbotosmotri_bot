import json
import os
import uuid
from datetime import datetime, timedelta
from database import db
from database_tasks import save_task_to_db, load_tasks_from_db, update_task_in_db, delete_task_from_db

def create_task_from_template(template, created_by, is_test=False, target_chat_id=None):
    """Создает задачу из шаблона с указанием целевого чата"""
    task_id = str(uuid.uuid4())[:8]
    
    # Рассчитываем следующее выполнение
    next_execution = calculate_next_execution(template.get('time'), template.get('days', []))
    
    task_data = {
        'id': task_id,
        'template_id': template.get('id'),
        'template_name': template['name'],
        'template_text': template.get('text'),
        'template_image': template.get('image'),
        'group_name': template.get('group'),
        'time': template.get('time'),
        'days': template.get('days', []),
        'frequency': template.get('frequency'),
        'created_by': created_by,
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'is_active': True,
        'is_test': is_test,
        'target_chat_id': target_chat_id,  # НОВОЕ ПОЛЕ - ID чата для отправки
        'last_executed': None,
        'next_execution': next_execution
    }
    
    # Сохраняем в базу данных
    success = save_task_to_db(task_data)
    
    if success:
        print(f"✅ Задача создана: {task_data['template_name']} (ID: {task_id})")
        if target_chat_id:
            print(f"💬 Целевой чат: {target_chat_id}")
        return True, task_id
    else:
        print(f"❌ Ошибка создания задачи: {task_data['template_name']}")
        return False, None

def calculate_next_execution(time_str, days):
    """Рассчитывает следующее время выполнения задачи"""
    if not time_str or not days:
        return None
    
    try:
        from datetime import datetime
        import pytz
        
        # Текущее время в Москве
        tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(tz)
        
        # Парсим время
        hour, minute = map(int, time_str.split(':'))
        
        # Находим следующий подходящий день
        current_weekday = now.weekday()  # 0-понедельник, 6-воскресенье
        
        # Ищем следующий день из списка дней
        for day_offset in range(8):  # Проверяем текущую неделю + следующий день
            check_day = (current_weekday + day_offset) % 7
            if str(check_day) in days:
                target_date = now + timedelta(days=day_offset)
                # Устанавливаем время
                target_datetime = target_date.replace(
                    hour=hour, 
                    minute=minute, 
                    second=0, 
                    microsecond=0
                )
                
                # Если время уже прошло сегодня, берем следующий подходящий день
                if day_offset == 0 and target_datetime <= now:
                    continue
                
                return target_datetime.strftime("%Y-%m-%d %H:%M:%S")
        
        return None
        
    except Exception as e:
        print(f"❌ Ошибка расчета следующего выполнения: {e}")
        return None

def get_all_active_tasks():
    """Возвращает все активные задачи"""
    return load_tasks_from_db()

def get_active_tasks_by_group(group_id):
    """Возвращает активные задачи по группе"""
    all_tasks = load_tasks_from_db()
    group_tasks = []
    
    for task_id, task in all_tasks.items():
        if (task.get('group_name') == group_id or task.get('group') == group_id) and task.get('is_active', True):
            group_tasks.append((task_id, task))
    
    return group_tasks

def deactivate_task(task_id):
    """Деактивирует задачу"""
    all_tasks = load_tasks_from_db()
    
    if task_id in all_tasks:
        task = all_tasks[task_id]
        task['is_active'] = False
        task['deactivated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        success = update_task_in_db(task_id, task)
        
        if success:
            print(f"✅ Задача деактивирована: {task_id}")
            return True, f"Задача '{task['template_name']}' деактивирована"
        else:
            print(f"❌ Ошибка деактивации задачи: {task_id}")
            return False, "Ошибка деактивации задачи"
    else:
        return False, "Задача не найдена"

def format_task_info(task):
    """Форматирует информацию о задаче для отображения"""
    days_names = []
    if task.get('days'):
        DAYS_OF_WEEK = {
            '0': 'Понедельник', '1': 'Вторник', '2': 'Среда',
            '3': 'Четверг', '4': 'Пятница', '5': 'Суббота', '6': 'Воскресенье'
        }
        days_names = [DAYS_OF_WEEK.get(day, day) for day in task['days']]
    
    frequency_map = {
        "weekly": "1 в неделю",
        "2_per_month": "2 в месяц", 
        "monthly": "1 в месяц"
    }
    frequency = frequency_map.get(task.get('frequency'), task.get('frequency', 'Не указана'))
    
    task_type = "🧪 Тестовая" if task.get('is_test') else "📅 Регулярная"
    status = "✅ Активна" if task.get('is_active', True) else "❌ Неактивна"
    
    info = f"**{task['template_name']}** ({task_type})\n"
    info += f"🏷️ Группа: {task.get('group_name', 'Не указана')}\n"
    info += f"📄 Текст: {task.get('template_text', '')[:100]}...\n"
    info += f"🖼️ Изображение: {'✅ Есть' if task.get('template_image') else '❌ Нет'}\n"
    info += f"⏰ Время: {task.get('time', 'Не указано')} (МСК)\n"
    info += f"📅 Дни: {', '.join(days_names) if days_names else 'Не указаны'}\n"
    info += f"🔄 Периодичность: {frequency}\n"
    
    # Добавляем информацию о целевом чате
    if task.get('target_chat_id'):
        info += f"💬 Чат отправки: {task.get('target_chat_id')}\n"
    
    if task.get('next_execution'):
        info += f"⏱️ Следующее выполнение: {task['next_execution']}\n"
    
    info += f"📊 Статус: {status}\n"
    
    return info

def get_task_target_chat(task_id):
    """Возвращает ID целевого чата для задачи"""
    all_tasks = load_tasks_from_db()
    task = all_tasks.get(task_id)
    return task.get('target_chat_id') if task else None

def update_task_execution_time(task_id, next_execution):
    """Обновляет время следующего выполнения задачи"""
    all_tasks = load_tasks_from_db()
    
    if task_id in all_tasks:
        task = all_tasks[task_id]
        task['last_executed'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task['next_execution'] = next_execution
        
        success = update_task_in_db(task_id, task)
        return success
    
    return False

def init_task_files():
    """Инициализирует файлы задач (для обратной совместимости)"""
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