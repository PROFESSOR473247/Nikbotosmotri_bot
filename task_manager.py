import logging
import os
import json
import uuid
from datetime import datetime
from database import db

logger = logging.getLogger(__name__)

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
    print(f"💾 Попытка сохранения задачи в базу данных: {task_data.get('template_name')}")
    
    conn = db.get_connection()
    if not conn:
        print("❌ Не удалось подключиться к базе данных для сохранения задачи")
        return False
        
    try:
        cursor = conn.cursor()
        
        # Подготавливаем данные
        task_id = task_data.get('id')
        template_id = task_data.get('template_id')
        template_name = task_data.get('template_name', '')
        template_text = task_data.get('template_text', '')
        template_image = task_data.get('template_image')
        group_name = task_data.get('group_name', '')
        time_str = task_data.get('time', '')
        
        # Обрабатываем дни - гарантируем что это JSON строка
        days_data = task_data.get('days', [])
        if isinstance(days_data, list):
            days_json = json.dumps(days_data, ensure_ascii=False)
        else:
            days_json = '[]'
            
        frequency = task_data.get('frequency', '')
        created_by = task_data.get('created_by')
        is_active = task_data.get('is_active', True)
        is_test = task_data.get('is_test', False)
        last_executed = task_data.get('last_executed')
        next_execution = task_data.get('next_execution')
        target_chat_id = task_data.get('target_chat_id')
        
        print(f"📊 Данные задачи для сохранения:")
        print(f"   ID: {task_id}")
        print(f"   Name: {template_name}")
        print(f"   Group: {group_name}")
        print(f"   Time: {time_str}")
        print(f"   Target Chat: {target_chat_id}")
        
        cursor.execute('''
            INSERT INTO tasks (id, template_id, template_name, template_text, template_image, 
                             group_name, time, days, frequency, created_by, is_active, is_test, 
                             last_executed, next_execution, target_chat_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                template_id = EXCLUDED.template_id,
                template_name = EXCLUDED.template_name,
                template_text = EXCLUDED.template_text,
                template_image = EXCLUDED.template_image,
                group_name = EXCLUDED.group_name,
                time = EXCLUDED.time,
                days = EXCLUDED.days,
                frequency = EXCLUDED.frequency,
                created_by = EXCLUDED.created_by,
                is_active = EXCLUDED.is_active,
                is_test = EXCLUDED.is_test,
                last_executed = EXCLUDED.last_executed,
                next_execution = EXCLUDED.next_execution,
                target_chat_id = EXCLUDED.target_chat_id
        ''', (
            task_id,
            template_id,
            template_name,
            template_text,
            template_image,
            group_name,
            time_str,
            days_json,
            frequency,
            created_by,
            is_active,
            is_test,
            last_executed,
            next_execution,
            target_chat_id
        ))
        
        conn.commit()
        
        # Проверим что действительно сохранилось
        cursor.execute('SELECT COUNT(*) FROM tasks WHERE id = %s', (task_id,))
        count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        if count > 0:
            print(f"✅ Задача {task_id} успешно сохранена в базе данных (проверено: {count} записей)")
            return True
        else:
            print(f"❌ Задача {task_id} не была сохранена в базу данных")
            return False
        
    except Exception as e:
        print(f"❌ Ошибка сохранения задачи: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        return False

def load_tasks():
    """Загружает все задачи из базы данных"""
    print("📂 Загрузка задач из базы данных...")
    
    conn = db.get_connection()
    if not conn:
        print("❌ Не удалось подключиться к базе данных для загрузки задач")
        return {}
        
    try:
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
        rows = cursor.fetchall()
        
        tasks = {}
        for row in rows:
            try:
                # Обрабатываем дни
                days_data = []
                if row[7]:  # days field
                    try:
                        if isinstance(row[7], (str, bytes, bytearray)):
                            days_data = json.loads(row[7])
                        else:
                            days_data = row[7]
                    except Exception as e:
                        print(f"⚠️ Ошибка парсинга дней для задачи {row[0]}: {e}")
                        days_data = []
                
                task = {
                    'id': row[0],
                    'template_id': row[1],
                    'template_name': row[2],
                    'template_text': row[3],
                    'template_image': row[4],
                    'group_name': row[5],
                    'time': row[6],
                    'days': days_data,
                    'frequency': row[8],
                    'created_by': row[9],
                    'created_at': row[10].strftime("%Y-%m-%d %H:%M:%S") if row[10] else None,
                    'is_active': row[11],
                    'is_test': row[12],
                    'last_executed': row[13].strftime("%Y-%m-%d %H:%M:%S") if row[13] else None,
                    'next_execution': row[14].strftime("%Y-%m-%d %H:%M:%S") if row[14] else None,
                    'target_chat_id': row[15]
                }
                tasks[task['id']] = task
                print(f"📥 Загружена задача: {task['template_name']} (ID: {task['id']})")
                
            except Exception as e:
                print(f"❌ Ошибка обработки строки задачи: {e}")
                continue
        
        cursor.close()
        conn.close()
        
        print(f"✅ Загружено {len(tasks)} задач из базы данных")
        return tasks
        
    except Exception as e:
        print(f"❌ Ошибка загрузки задач: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.close()
        except:
            pass
        return {}

def create_task(task_data):
    """Создает новую задачу"""
    try:
        # Генерируем ID для задачи
        task_id = create_task_id()
        task_data['id'] = task_id
        
        print(f"🆔 Сгенерирован ID задачи: {task_id}")
        print(f"📦 Данные для сохранения: {task_data}")
        
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
        import traceback
        traceback.print_exc()
        return False, None

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
        conn = db.get_connection()
        if not conn:
            return False
            
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE id = %s', (task_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Задача {task_id} удалена из базы данных")
        return True
        
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
            if task.get('group_name') == group_id:
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
            if task.get('group_name') == group_id:
                group_tasks[task_id] = task
        
        return group_tasks
    except Exception as e:
        print(f"❌ Ошибка получения активных задач группы {group_id}: {e}")
        return {}

def create_task_from_template(template_data, created_by, target_chat_id=None, is_test=False):
    """Создает задачу из шаблона"""
    logger.info("🔄 Начало создания задачи из шаблона...")
    try:
        print(f"🔄 Создание задачи из шаблона: {template.get('name')}")
        print(f"📊 Данные шаблона: {template}")
        print(f"👤 Создатель: {created_by}")
        print(f"💬 Целевой чат: {target_chat_id}")
        print(f"🧪 Тестовая: {is_test}")
        
        # Для тестовых задач устанавливаем специальные параметры
        if is_test:
            # Тестовые задачи выполняются через 5 секунд
            task_data = {
                'template_id': template.get('id'),
                'template_name': template.get('name', 'Без названия'),
                'template_text': template.get('text', ''),
                'template_image': template.get('image'),
                'group_name': template.get('group', ''),
                'time': None,  # Для тестовых задач время не важно
                'days': [],    # Для тестовых задач дни не важны
                'frequency': 'once',  # Однократное выполнение
                'created_by': created_by,
                'is_active': True,
                'is_test': True,
                'target_chat_id': target_chat_id,
                'test_execution_time': (datetime.now() + timedelta(seconds=5)).strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            # Обычные задачи используют настройки из шаблона
            task_data = {
                'template_id': template.get('id'),
                'template_name': template.get('name', 'Без названия'),
                'template_text': template.get('text', ''),
                'template_image': template.get('image'),
                'group_name': template.get('group', ''),
                'time': template.get('time', ''),
                'days': template.get('days', []),
                'frequency': template.get('frequency', 'weekly'),
                'created_by': created_by,
                'is_active': True,
                'is_test': False,
                'target_chat_id': target_chat_id
            }
        
        print(f"📦 Данные для сохранения задачи: {task_data}")
        
        # Создаем задачу
        success, task_id = create_task(task_data)
        
        if success and is_test:
            # Для тестовых задач сразу планируем выполнение через 5 секунд
            from task_scheduler import schedule_test_task
            schedule_test_task(task_id, task_data)
        
        if success:
            print(f"✅ Задача успешно создана: {task_id}")
        else:
            print("❌ Ошибка при вызове create_task")
            
        return success, task_id
        
    except Exception as e:
        print(f"❌ Критическая ошибка в create_task_from_template: {e}")
        import traceback
        traceback.print_exc()
        return False, None
        
        # ===== ФУНКЦИИ ДЛЯ ПЛАНИРОВЩИКА =====

def update_task_execution_time(task_id):
    """Обновляет время последнего выполнения задачи"""
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return update_task_field(task_id, 'last_executed', current_time)
    except Exception as e:
        print(f"❌ Ошибка обновления времени выполнения задачи {task_id}: {e}")
        return False

def calculate_next_execution(task):
    """Рассчитывает следующее время выполнения задачи"""
    try:
        from datetime import datetime, timedelta
        
        if not task.get('days') or not task.get('time'):
            return None
            
        current_time = datetime.now()
        current_weekday = current_time.weekday()
        task_days = [int(day) for day in task['days']]
        
        # Находим следующий день выполнения
        for day_offset in range(1, 8):
            next_day = (current_weekday + day_offset) % 7
            if str(next_day) in task_days:
                next_date = current_time + timedelta(days=day_offset)
                
                # Устанавливаем время выполнения
                hour, minute = map(int, task['time'].split(':'))
                next_execution = next_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                return next_execution.strftime("%Y-%m-%d %H:%M:%S")
        
        return None
    except Exception as e:
        print(f"❌ Ошибка расчета следующего выполнения задачи: {e}")
        return None

# Инициализация при импорте
print("📥 Task_manager загружен")
init_task_files()
init_database()
print("✅ Task_manager инициализирован")
