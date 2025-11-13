import json
import os
import uuid
from datetime import datetime
from database import db

# Дни недели для отображения
DAYS_OF_WEEK = {
    '0': 'Понедельник', '1': 'Вторник', '2': 'Среда',
    '3': 'Четверг', '4': 'Пятница', '5': 'Суббота', '6': 'Воскресенье'
}

def init_files():
    """Инициализирует файлы шаблонов (для обратной совместимости)"""
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    template_files = ['templates.json']
    for file in template_files:
        file_path = os.path.join(data_dir, file)
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    
    print("✅ Файлы шаблонов инициализированы")

def init_database():
    """Инициализирует базу данных для шаблонов"""
    print("🔄 Инициализация базы данных в template_manager...")
    return db.init_database()

def save_template(template_data):
    """Сохраняет шаблон в базу данных"""
    return db.save_template(template_data)

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

def create_template_id():
    """Создает уникальный ID для шаблона"""
    return str(uuid.uuid4())[:8]

# Инициализация при импорте
print("📥 Template_manager загружен")
init_files()
init_database()
print("✅ Template_manager инициализирован")