import json
import os
import uuid
from datetime import datetime, timedelta
from database import db
from database_tasks import save_task_to_db, load_tasks_from_db, update_task_in_db, delete_task_from_db
# ===== ФУНКЦИИ ДЛЯ НОВОГО МЕНЮ ШАБЛОНОВ =====

# ===== ЗАЩИТНЫЕ ФУНКЦИИ =====

def safe_get_task_value(task, key, default=""):
    """Безопасно получает значение из задачи"""
    try:
        return task.get(key, default)
    except Exception as e:
        print(f"⚠️ Ошибка получения значения {key} из задачи: {e}")
        return default

def safe_format_days_list(days):
    """Безопасно форматирует список дней"""
def get_user_template_access(user_id):
    """Возвращает информацию о доступе пользователя к шаблонам"""
    try:
        if not days:
            return []
        if not isinstance(days, list):
            return []
        accessible_groups = get_user_accessible_groups(user_id)
        all_templates = get_all_templates()

        DAYS_OF_WEEK = {
            '0': 'Понедельник', '1': 'Вторник', '2': 'Среда',
            '3': 'Четверг', '4': 'Пятница', '5': 'Суббота', '6': 'Воскресенье'
        }
        user_templates = {}
        templates_by_group = {}

        return [DAYS_OF_WEEK.get(str(day), f"День {day}") for day in days]
    except Exception as e:
        print(f"⚠️ Ошибка форматирования дней {days}: {e}")
        return []

def safe_get_frequency_name(frequency):
    """Безопасно возвращает название периодичности"""
    try:
        frequency_map = {
            "weekly": "1 в неделю",
            "2_per_month": "2 в месяц", 
            "monthly": "1 в месяц"
        # Фильтруем шаблоны по доступным группам
        for template_id, template in all_templates.items():
            template_group = template.get('group')
            if template_group in accessible_groups:
                user_templates[template_id] = template
                
                # Группируем по группам
                if template_group not in templates_by_group:
                    templates_by_group[template_group] = []
                templates_by_group[template_group].append((template_id, template))
        
        return {
            'accessible_groups': accessible_groups,
            'user_templates': user_templates,
            'templates_by_group': templates_by_group,
            'total_templates': len(user_templates),
            'total_groups': len(accessible_groups)
        }
        return frequency_map.get(frequency, frequency)
    except Exception as e:
        print(f"⚠️ Ошибка получения периодичности {frequency}: {e}")
        return frequency

# ===== ОСНОВНЫЕ ФУНКЦИИ =====

def create_task_from_template(template, created_by, is_test=False, target_chat_id=None):
    """Создает задачу из шаблона с указанием целевого чата"""
    try:
        task_id = str(uuid.uuid4())[:8]
        
        # Рассчитываем следующее выполнение
        next_execution = calculate_next_execution(template.get('time'), template.get('days', []))
        
        task_data = {
            'id': task_id,
            'template_id': template.get('id'),
            'template_name': safe_get_task_value(template, 'name', 'Без названия'),
            'template_text': safe_get_task_value(template, 'text', ''),
            'template_image': template.get('image'),
            'group_name': safe_get_task_value(template, 'group', ''),
            'time': template.get('time'),
            'days': template.get('days', []),
            'frequency': template.get('frequency'),
            'created_by': created_by,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'is_active': True,
            'is_test': is_test,
            'target_chat_id': target_chat_id,
            'last_executed': None,
            'next_execution': next_execution
        print(f"❌ Ошибка получения доступа пользователя {user_id} к шаблонам: {e}")
        return {
            'accessible_groups': {},
            'user_templates': {},
            'templates_by_group': {},
            'total_templates': 0,
            'total_groups': 0
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
    except Exception as e:
        print(f"❌ Ошибка создания задачи из шаблона: {e}")
        return False, None

def calculate_next_execution(time_str, days):
    """Рассчитывает следующее время выполнения задачи"""
    if not time_str or not days:
        return None
    
def format_all_templates_info(user_id):
    """Форматирует информацию о всех шаблонах пользователя"""
    try:
        from datetime import datetime
        import pytz
        
        # Текущее время в Москве
        tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(tz)
        access_info = get_user_template_access(user_id)

        # Парсим время
        hour, minute = map(int, time_str.split(':'))
        if not access_info['user_templates']:
            return "📭 У вас нет доступных шаблонов"

        # Находим следующий подходящий день
        current_weekday = now.weekday()  # 0-понедельник, 6-воскресенье
        message = "📋 **Все ваши шаблоны:**\n\n"

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
        # Группируем по группам для лучшего отображения
        for group_id, templates in access_info['templates_by_group'].items():
            group_name = access_info['accessible_groups'].get(group_id, {}).get('name', group_id)
            message += f"**🏷️ {group_name}:**\n"
            
            for i, (template_id, template) in enumerate(templates, 1):
                days_count = len(safe_get_template_value(template, 'days', []))
                has_image = "🖼️" if template.get('image') else ""
                template_name = safe_get_template_value(template, 'name', 'Без названия')
                template_time = safe_get_template_value(template, 'time', 'Не указано')

                return target_datetime.strftime("%Y-%m-%d %H:%M:%S")
                message += f"  {i}. **{template_name}** {has_image}\n"
                message += f"     ⏰ {template_time} | 📅 {days_count} дней\n"
                message += f"     📄 {template['text'][:50]}...\n\n"

        return None
        message += f"**Всего:** {access_info['total_templates']} шаблонов в {access_info['total_groups']} группах"

        return message
    except Exception as e:
        print(f"❌ Ошибка расчета следующего выполнения: {e}")
        return None

def get_all_active_tasks():
    """Возвращает все активные задачи"""
    try:
        return load_tasks_from_db()
    except Exception as e:
        print(f"❌ Ошибка получения активных задач: {e}")
        return {}
        print(f"❌ Ошибка форматирования всех шаблонов: {e}")
        return "❌ Ошибка загрузки информации о шаблонах"

def get_active_tasks_by_group(group_id):
    """Возвращает активные задачи по группе"""
def format_group_templates_detailed(group_id):
    """Детальная информация о шаблонах группы"""
    try:
        all_tasks = load_tasks_from_db()
        group_tasks = []
        templates = get_templates_by_group(group_id)

        for task_id, task in all_tasks.items():
            if (task.get('group_name') == group_id or task.get('group') == group_id) and task.get('is_active', True):
                group_tasks.append((task_id, task))
        if not templates:
            return f"📭 В этой группе нет шаблонов"

        return group_tasks
    except Exception as e:
        print(f"❌ Ошибка получения задач группы {group_id}: {e}")
        return []

def deactivate_task(task_id):
    """Деактивирует задачу"""
    try:
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
    except Exception as e:
        print(f"❌ Ошибка деактивации задачи {task_id}: {e}")
        return False, f"Ошибка деактивации: {e}"

def format_task_info(task):
    """Форматирует информацию о задаче для отображения"""
    try:
        days_names = safe_format_days_list(task.get('days', []))
        frequency = safe_get_frequency_name(task.get('frequency', 'Не указана'))
        
        task_name = safe_get_task_value(task, 'template_name', 'Без названия')
        task_group = safe_get_task_value(task, 'group_name', 'Не указана')
        task_text = safe_get_task_value(task, 'template_text', '')
        task_time = safe_get_task_value(task, 'time', 'Не указано')
        has_image = '✅ Есть' if task.get('template_image') else '❌ Нет'
        task_type = "🧪 Тестовая" if task.get('is_test') else "📅 Регулярная"
        status = "✅ Активна" if task.get('is_active', True) else "❌ Неактивна"
        
        info = f"**{task_name}** ({task_type})\n"
        info += f"🏷️ Группа: {task_group}\n"
        info += f"📄 Текст: {task_text[:100]}...\n"
        info += f"🖼️ Изображение: {has_image}\n"
        info += f"⏰ Время: {task_time} (МСК)\n"
        info += f"📅 Дни: {', '.join(days_names) if days_names else 'Не указаны'}\n"
        info += f"🔄 Периодичность: {frequency}\n"
        
        # Добавляем информацию о целевом чате
        if task.get('target_chat_id'):
            info += f"💬 Чат отправки: {task['target_chat_id']}\n"
        
        if task.get('next_execution'):
            info += f"⏱️ Следующее выполнение: {task['next_execution']}\n"
        
        info += f"📊 Статус: {status}\n"
        groups_data = load_groups()
        group_name = groups_data['groups'].get(group_id, {}).get('name', group_id)

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