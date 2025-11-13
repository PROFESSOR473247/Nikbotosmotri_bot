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

def init_files():
    """Инициализирует файлы шаблонов и директории"""
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

def init_database():
    """Инициализирует базу данных для шаблонов"""
    print("🔄 Инициализация базы данных в template_manager...")
    return db.init_database()

def save_template(template_data):
    """Сохраняет шаблон в базу данных"""
    return db.save_template(template_data)

def create_template(template_data):
    """Создает новый шаблон"""
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

def load_templates():
    """Загружает все шаблоны из базы данных"""
    return db.load_templates()

def get_all_templates():
    """Возвращает все шаблоны"""
    return load_templates()

def load_groups():
    """Загружает группы из базы данных"""
    return db.load_groups()

def get_template_by_id(template_id):
    """Возвращает шаблон по ID"""
    templates = load_templates()
    return templates.get(template_id)

def delete_template(template_id):
    """Удаляет шаблон"""
    return db.delete_template(template_id)

def get_user_accessible_groups(user_id):
    """Возвращает группы, доступные пользователю"""
    from authorized_users import get_user_access_groups
    accessible_group_ids = get_user_access_groups(user_id)
    
    groups_data = load_groups()
    accessible_groups = {}
    
    for group_id in accessible_group_ids:
        if group_id in groups_data.get('groups', {}):
            accessible_groups[group_id] = groups_data['groups'][group_id]
    
    return accessible_groups

def get_templates_by_group(group_id):
    """Возвращает шаблоны определенной группы"""
    templates = load_templates()
    group_templates = []
    
    for template_id, template in templates.items():
        if template.get('group') == group_id:
            group_templates.append((template_id, template))
    
    return group_templates

def format_template_info(template):
    """Форматирует информацию о шаблоне для отображения"""
    days_names = []
    if template.get('days'):
        days_names = [DAYS_OF_WEEK[day] for day in template['days']]
    
    frequency_map = {
        "weekly": "1 в неделю",
        "2_per_month": "2 в месяц", 
        "monthly": "1 в месяц"
    }
    frequency = frequency_map.get(template.get('frequency'), template.get('frequency', 'Не указана'))
    
    info = f"**{template['name']}**\n"
    info += f"📄 Текст: {template.get('text', '')[:100]}...\n"
    info += f"🖼️ Изображение: {'✅ Есть' if template.get('image') else '❌ Нет'}\n"
    info += f"⏰ Время: {template.get('time', 'Не указано')} (МСК)\n"
    info += f"📅 Дни: {', '.join(days_names) if days_names else 'Не указаны'}\n"
    info += f"🔄 Периодичность: {frequency}\n"
    
    return info

def format_template_list_info(templates):
    """Форматирует список шаблонов для отображения"""
    if not templates:
        return "📭 Шаблонов нет"
    
    message = "📋 **Список шаблонов:**\n\n"
    
    for i, (template_id, template) in enumerate(templates.items(), 1):
        days_count = len(template.get('days', []))
        has_image = "🖼️" if template.get('image') else "❌"
        
        message += f"{i}. **{template['name']}** {has_image}\n"
        message += f"   🏷️ Группа: {template.get('group', 'Не указана')}\n"
        message += f"   ⏰ Время: {template.get('time', 'Не указано')}\n"
        message += f"   📅 Дней: {days_count}\n"
        message += f"   📄 Текст: {template.get('text', '')[:50]}...\n\n"
    
    return message

def format_template_preview(template):
    """Форматирует превью шаблона"""
    days_names = []
    if template.get('days'):
        days_names = [DAYS_OF_WEEK[day] for day in template['days']]
    
    preview = f"📝 **{template['name']}**\n\n"
    preview += f"📄 {template.get('text', '')}\n\n"
    
    if template.get('image'):
        preview += "🖼️ *Есть изображение*\n"
    
    if template.get('time'):
        preview += f"⏰ Время отправки: {template['time']} (МСК)\n"
    
    if days_names:
        preview += f"📅 Дни: {', '.join(days_names)}\n"
    
    frequency_map = {
        "weekly": "1 в неделю",
        "2_per_month": "2 в месяц", 
        "monthly": "1 в месяц"
    }
    frequency = frequency_map.get(template.get('frequency'), template.get('frequency', 'Не указана'))
    preview += f"🔄 Периодичность: {frequency}"
    
    return preview

def create_template_id():
    """Создает уникальный ID для шаблона"""
    return str(uuid.uuid4())[:8]

def get_template_groups():
    """Возвращает все группы шаблонов"""
    groups_data = load_groups()
    return groups_data.get('groups', {})

def update_template(template_id, template_data):
    """Обновляет шаблон"""
    template_data['id'] = template_id
    return save_template(template_data)

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
    # Ищем файл с любым расширением
    if not os.path.exists(IMAGES_DIR):
        return None
    
    for filename in os.listdir(IMAGES_DIR):
        if filename.startswith(template_id):
            return os.path.join(IMAGES_DIR, filename)
    
    return None

def validate_template_data(template_data):
    """Проверяет данные шаблона на валидность"""
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

def get_template_by_name(template_name):
    """Возвращает шаблон по имени"""
    templates = load_templates()
    for template_id, template in templates.items():
        if template.get('name') == template_name:
            return template
    return None

def template_exists(template_name, group_id):
    """Проверяет, существует ли шаблон с таким именем в группе"""
    templates = get_templates_by_group(group_id)
    for template_id, template in templates:
        if template.get('name') == template_name:
            return True
    return False

def get_templates_count():
    """Возвращает количество шаблонов"""
    templates = load_templates()
    return len(templates)

def get_templates_by_user(user_id):
    """Возвращает шаблоны, созданные пользователем"""
    templates = load_templates()
    user_templates = {}
    
    for template_id, template in templates.items():
        if template.get('created_by') == user_id:
            user_templates[template_id] = template
    
    return user_templates

def get_template_subgroups(group_id):
    """Возвращает подгруппы для группы (для обратной совместимости)"""
    # В текущей реализации подгрупп нет, возвращаем пустой список
    return []

def format_group_templates_info(group_id):
    """Форматирует информацию о шаблонах группы"""
    templates = get_templates_by_group(group_id)
    
    if not templates:
        return f"📭 В этой группе нет шаблонов"
    
    groups_data = load_groups()
    group_name = groups_data['groups'].get(group_id, {}).get('name', group_id)
    
    message = f"📋 **Шаблоны группы '{group_name}':**\n\n"
    
    for i, (template_id, template) in enumerate(templates, 1):
        days_count = len(template.get('days', []))
        has_image = "🖼️" if template.get('image') else "❌"
        
        message += f"{i}. **{template['name']}** {has_image}\n"
        message += f"   ⏰ {template.get('time', 'Не указано')} | 📅 {days_count} дней\n"
        message += f"   📄 {template.get('text', '')[:60]}...\n\n"
    
    return message

def get_frequency_types():
    """Возвращает доступные типы периодичности"""
    return FREQUENCY_TYPES

def get_week_days():
    """Возвращает дни недели для выбора"""
    return WEEK_DAYS

# Инициализация при импорте
print("📥 Template_manager загружен")
init_files()
init_database()
print("✅ Template_manager инициализирован")