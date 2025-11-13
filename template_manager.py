import json
import os
import uuid
import shutil
from datetime import datetime
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

# Дни недели для выбора
WEEK_DAYS = {
    '0': 'Понедельник',
    '1': 'Вторник', 
    '2': 'Среда',
    '3': 'Четверг',
    '4': 'Пятница',
    '5': 'Суббота',
    '6': 'Воскресенье'
}

# Директория для изображений
IMAGES_DIR = "images"

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

def safe_get_template_value(template, key, default=""):
    """Безопасно получает значение из шаблона"""
    try:
        return template.get(key, default)
    except Exception as e:
        print(f"⚠️ Ошибка получения значения {key} из шаблона: {e}")
        return default

# ===== ОСНОВНЫЕ ФУНКЦИИ =====

def init_files():
    """Инициализирует файлы шаблонов и директории"""
    try:
        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # Создаем директорию для изображений
        if not os.path.exists(IMAGES_DIR):
            os.makedirs(IMAGES_DIR)
        
        template_files = ['templates.json']
        for file in template_files:
            file_path = os.path.join(data_dir, file)
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
        
        print("✅ Файлы шаблонов и директории инициализированы")
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации файлов: {e}")
        return False

def init_database():
    """Инициализирует базу данных для шаблонов"""
    try:
        print("🔄 Инициализация базы данных в template_manager...")
        return db.init_database()
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")
        return False

def save_template(template_data):
    """Сохраняет шаблон в базу данных"""
    try:
        return db.save_template(template_data)
    except Exception as e:
        print(f"❌ Ошибка сохранения шаблона: {e}")
        return False

def create_template(template_data):
    """Создает новый шаблон"""
    try:
        # Генерируем ID для шаблона
        template_id = create_template_id()
        template_data['id'] = template_id
        
        # Сохраняем в базу данных
        success = save_template(template_data)
        
        if success:
            print(f"✅ Шаблон создан: {template_data['name']} (ID: {template_id})")
            return True, template_id
        else:
            print(f"❌ Ошибка создания шаблона: {template_data['name']}")
            return False, None
    except Exception as e:
        print(f"❌ Ошибка создания шаблона: {e}")
        return False, None

def load_templates():
    """Загружает все шаблоны из базы данных"""
    try:
        return db.load_templates()
    except Exception as e:
        print(f"❌ Ошибка загрузки шаблонов: {e}")
        return {}

def get_all_templates():
    """Возвращает все шаблоны"""
    return load_templates()

def load_groups():
    """Загружает группы из базы данных"""
    try:
        return db.load_groups()
    except Exception as e:
        print(f"❌ Ошибка загрузки групп: {e}")
        return {"groups": {}}

def get_template_by_id(template_id):
    """Возвращает шаблон по ID"""
    try:
        templates = load_templates()
        return templates.get(template_id)
    except Exception as e:
        print(f"❌ Ошибка получения шаблона по ID {template_id}: {e}")
        return None

def delete_template(template_id):
    """Удаляет шаблон"""
    try:
        return db.delete_template(template_id)
    except Exception as e:
        print(f"❌ Ошибка удаления шаблона {template_id}: {e}")
        return False

def delete_template_by_id(template_id):
    """Удаляет шаблон по ID (алиас для delete_template)"""
    return delete_template(template_id)

def get_user_accessible_groups(user_id):
    """Возвращает группы, доступные пользователю"""
    try:
        from authorized_users import get_user_access_groups
        accessible_group_ids = get_user_access_groups(user_id)
        
        groups_data = load_groups()
        accessible_groups = {}
        
        for group_id in accessible_group_ids:
            if group_id in groups_data.get('groups', {}):
                accessible_groups[group_id] = groups_data['groups'][group_id]
        
        return accessible_groups
    except Exception as e:
        print(f"❌ Ошибка получения доступных групп для пользователя {user_id}: {e}")
        return {}

def get_templates_by_group(group_id):
    """Возвращает шаблоны определенной группы"""
    try:
        templates = load_templates()
        group_templates = []
        
        for template_id, template in templates.items():
            if template.get('group') == group_id:
                group_templates.append((template_id, template))
        
        return group_templates
    except Exception as e:
        print(f"❌ Ошибка получения шаблонов группы {group_id}: {e}")
        return []

def format_template_info(template):
    """Форматирует информацию о шаблоне для отображения"""
    try:
        days_names = safe_format_days_list(template.get('days', []))
        frequency = safe_get_frequency_name(template.get('frequency', 'Не указана'))
        
        template_name = safe_get_template_value(template, 'name', 'Без названия')
        template_text = safe_get_template_value(template, 'text', '')
        template_time = safe_get_template_value(template, 'time', 'Не указано')
        has_image = '✅ Есть' if template.get('image') else '❌ Нет'
        
        info = f"**{template_name}**\n"
        info += f"📄 Текст: {template_text[:100]}...\n"
        info += f"🖼️ Изображение: {has_image}\n"
        info += f"⏰ Время: {template_time} (МСК)\n"
        info += f"📅 Дни: {', '.join(days_names) if days_names else 'Не указаны'}\n"
        info += f"🔄 Периодичность: {frequency}\n"
        
        return info
    except Exception as e:
        print(f"❌ Ошибка форматирования информации о шаблоне: {e}")
        return "❌ Ошибка загрузки информации о шаблоне"

def format_template_list_info(templates):
    """Форматирует список шаблонов для отображения"""
    try:
        if not templates:
            return "📭 Шаблонов нет"
        
        message = "📋 **Список шаблонов:**\n\n"
        
        for i, (template_id, template) in enumerate(templates.items(), 1):
            days_count = len(safe_get_template_value(template, 'days', []))
            has_image = "🖼️" if template.get('image') else "❌"
            template_name = safe_get_template_value(template, 'name', 'Без названия')
            template_group = safe_get_template_value(template, 'group', 'Не указана')
            template_time = safe_get_template_value(template, 'time', 'Не указано')
            template_text = safe_get_template_value(template, 'text', '')
            
            message += f"{i}. **{template_name}** {has_image}\n"
            message += f"   🏷️ Группа: {template_group}\n"
            message += f"   ⏰ Время: {template_time}\n"
            message += f"   📅 Дней: {days_count}\n"
            message += f"   📄 Текст: {template_text[:50]}...\n\n"
        
        return message
    except Exception as e:
        print(f"❌ Ошибка форматирования списка шаблонов: {e}")
        return "❌ Ошибка загрузки списка шаблонов"

def format_template_preview(template):
    """Форматирует превью шаблона"""
    try:
        days_names = safe_format_days_list(template.get('days', []))
        frequency = safe_get_frequency_name(template.get('frequency', 'Не указана'))
        
        template_name = safe_get_template_value(template, 'name', 'Без названия')
        template_text = safe_get_template_value(template, 'text', '')
        template_time = safe_get_template_value(template, 'time', '')
        
        preview = f"📝 **{template_name}**\n\n"
        preview += f"📄 {template_text}\n\n"
        
        if template.get('image'):
            preview += "🖼️ *Есть изображение*\n"
        
        if template_time:
            preview += f"⏰ Время отправки: {template_time} (МСК)\n"
        
        if days_names:
            preview += f"📅 Дни: {', '.join(days_names)}\n"
        
        preview += f"🔄 Периодичность: {frequency}"
        
        return preview
    except Exception as e:
        print(f"❌ Ошибка форматирования превью шаблона: {e}")
        return "❌ Ошибка загрузки превью шаблона"

def create_template_id():
    """Создает уникальный ID для шаблона"""
    try:
        return str(uuid.uuid4())[:8]
    except Exception as e:
        print(f"❌ Ошибка создания ID шаблона: {e}")
        return str(int(datetime.now().timestamp()))[-8:]

def get_template_groups():
    """Возвращает все группы шаблонов"""
    try:
        groups_data = load_groups()
        return groups_data.get('groups', {})
    except Exception as e:
        print(f"❌ Ошибка получения групп шаблонов: {e}")
        return {}

def update_template(template_id, template_data):
    """Обновляет шаблон"""
    try:
        template_data['id'] = template_id
        return save_template(template_data)
    except Exception as e:
        print(f"❌ Ошибка обновления шаблона {template_id}: {e}")
        return False

def update_template_field(template_id, field_name, field_value):
    """Обновляет конкретное поле шаблона"""
    try:
        template = get_template_by_id(template_id)
        if not template:
            return False, "Шаблон не найден"
        
        template[field_name] = field_value
        return update_template(template_id, template)
    except Exception as e:
        print(f"❌ Ошибка обновления поля {field_name} шаблона {template_id}: {e}")
        return False, f"Ошибка обновления: {e}"

# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С ИЗОБРАЖЕНИЯМИ =====

def save_image(image_file, template_id):
    """Сохраняет изображение для шаблона"""
    try:
        # Создаем уникальное имя файла
        file_extension = os.path.splitext(image_file.filename)[1]
        image_filename = f"{template_id}{file_extension}"
        image_path = os.path.join(IMAGES_DIR, image_filename)
        
        # Сохраняем файл
        with open(image_path, 'wb') as f:
            f.write(image_file.getvalue())
        
        print(f"✅ Изображение сохранено: {image_path}")
        return image_path
        
    except Exception as e:
        print(f"❌ Ошибка сохранения изображения: {e}")
        return None

def delete_image(image_path):
    """Удаляет изображение"""
    try:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
            print(f"✅ Изображение удалено: {image_path}")
            return True
        return False
    except Exception as e:
        print(f"❌ Ошибка удаления изображения: {e}")
        return False

def get_image_path(template_id):
    """Возвращает путь к изображению шаблона"""
    try:
        # Ищем файл с любым расширением
        if not os.path.exists(IMAGES_DIR):
            return None
        
        for filename in os.listdir(IMAGES_DIR):
            if filename.startswith(template_id):
                return os.path.join(IMAGES_DIR, filename)
        
        return None
    except Exception as e:
        print(f"❌ Ошибка получения пути изображения для шаблона {template_id}: {e}")
        return None

def validate_template_data(template_data):
    """Проверяет данные шаблона на валидность"""
    try:
        required_fields = ['name', 'group', 'text']
        for field in required_fields:
            if not template_data.get(field):
                return False, f"Отсутствует обязательное поле: {field}"
        
        # Проверяем время
        if template_data.get('time'):
            try:
                hour, minute = map(int, template_data['time'].split(':'))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    return False, "Неверный формат времени"
            except ValueError:
                return False, "Неверный формат времени"
        
        return True, "OK"
    except Exception as e:
        print(f"❌ Ошибка валидации данных шаблона: {e}")
        return False, f"Ошибка валидации: {e}"

def get_template_by_name(template_name):
    """Возвращает шаблон по имени"""
    try:
        templates = load_templates()
        for template_id, template in templates.items():
            if template.get('name') == template_name:
                return template
        return None
    except Exception as e:
        print(f"❌ Ошибка поиска шаблона по имени {template_name}: {e}")
        return None

def template_exists(template_name, group_id):
    """Проверяет, существует ли шаблон с таким именем в группе"""
    try:
        templates = get_templates_by_group(group_id)
        for template_id, template in templates:
            if template.get('name') == template_name:
                return True
        return False
    except Exception as e:
        print(f"❌ Ошибка проверки существования шаблона {template_name}: {e}")
        return False

def get_templates_count():
    """Возвращает количество шаблонов"""
    try:
        templates = load_templates()
        return len(templates)
    except Exception as e:
        print(f"❌ Ошибка получения количества шаблонов: {e}")
        return 0

def get_templates_by_user(user_id):
    """Возвращает шаблоны, созданные пользователем"""
    try:
        templates = load_templates()
        user_templates = {}
        
        for template_id, template in templates.items():
            if template.get('created_by') == user_id:
                user_templates[template_id] = template
        
        return user_templates
    except Exception as e:
        print(f"❌ Ошибка получения шаблонов пользователя {user_id}: {e}")
        return {}

def get_template_subgroups(group_id):
    """Возвращает подгруппы для группы (для обратной совместимости)"""
    # В текущей реализации подгрупп нет, возвращаем пустой список
    return []

def format_group_templates_info(group_id):
    """Форматирует информацию о шаблонах группы"""
    try:
        templates = get_templates_by_group(group_id)
        
        if not templates:
            return f"📭 В этой группе нет шаблонов"
        
        groups_data = load_groups()
        group_name = groups_data['groups'].get(group_id, {}).get('name', group_id)
        
        message = f"📋 **Шаблоны группы '{group_name}':**\n\n"
        
        for i, (template_id, template) in enumerate(templates, 1):
            days_count = len(safe_get_template_value(template, 'days', []))
            has_image = "🖼️" if template.get('image') else "❌"
            template_name = safe_get_template_value(template, 'name', 'Без названия')
            template_time = safe_get_template_value(template, 'time', 'Не указано')
            template_text = safe_get_template_value(template, 'text', '')
            
            message += f"{i}. **{template_name}** {has_image}\n"
            message += f"   ⏰ {template_time} | 📅 {days_count} дней\n"
            message += f"   📄 {template_text[:60]}...\n\n"
        
        return message
    except Exception as e:
        print(f"❌ Ошибка форматирования информации о группе {group_id}: {e}")
        return f"❌ Ошибка загрузки информации о группе"

def get_frequency_types():
    """Возвращает доступные типы периодичности"""
    return FREQUENCY_TYPES

def get_week_days():
    """Возвращает дни недели для выбора"""
    return WEEK_DAYS

def get_template_stats():
    """Возвращает статистику по шаблонам"""
    try:
        templates = load_templates()
        groups = get_template_groups()
        
        stats = {
            'total_templates': len(templates),
            'groups_count': len(groups),
            'templates_with_images': 0,
            'templates_with_schedule': 0
        }
        
        for template in templates.values():
            if template.get('image'):
                stats['templates_with_images'] += 1
            if template.get('time') and template.get('days'):
                stats['templates_with_schedule'] += 1
        
        return stats
    except Exception as e:
        print(f"❌ Ошибка получения статистики шаблонов: {e}")
        return {
            'total_templates': 0,
            'groups_count': 0,
            'templates_with_images': 0,
            'templates_with_schedule': 0
        }

def search_templates(search_term):
    """Ищет шаблоны по названию или тексту"""
    try:
        templates = load_templates()
        results = {}
        
        search_term_lower = search_term.lower()
        
        for template_id, template in templates.items():
            name_match = search_term_lower in template.get('name', '').lower()
            text_match = search_term_lower in template.get('text', '').lower()
            
            if name_match or text_match:
                results[template_id] = template
        
        return results
    except Exception as e:
        print(f"❌ Ошибка поиска шаблонов по запросу '{search_term}': {e}")
        return {}

def delete_template_and_image(template_id):
    """Удаляет шаблон и связанное с ним изображение"""
    try:
        # Получаем информацию о шаблоне
        template = get_template_by_id(template_id)
        if not template:
            return False, "Шаблон не найден"
        
        # Удаляем изображение если есть
        if template.get('image'):
            delete_image(template['image'])
        
        # Удаляем шаблон из базы данных
        success = delete_template(template_id)
        
        if success:
            return True, f"Шаблон '{template['name']}' успешно удален"
        else:
            return False, "Ошибка при удалении шаблона"
    except Exception as e:
        print(f"❌ Ошибка удаления шаблона и изображения {template_id}: {e}")
        return False, f"Ошибка удаления: {e}"

# Инициализация при импорте
print("📥 Template_manager загружен")
init_files()
init_database()
print("✅ Template_manager инициализирован")