import json
import os
import uuid
from datetime import datetime
from database import db

# Дни недели для отображения
DAYS_OF_WEEK = {
    0: "Понедельник",
    1: "Вторник", 
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресеньe"
}

FREQUENCY_TYPES = {
    "weekly": "1 в неделю", 
    "2_per_month": "2 в месяц",
    "monthly": "1 в месяц"
}

def init_files():
    """Инициализирует базу данных"""
    print("🔄 Инициализация базы данных в template_manager...")
    success = db.init_database()
    if success:
        print("✅ База данных успешно инициализирована")
    else:
        print("❌ Не удалось инициализировать базу данных")
    return success

def load_templates():
    """Загружает шаблоны из базы данных"""
    print("📂 Загрузка шаблонов из базы данных...")
    templates = db.load_templates()
    print(f"📊 Загружено {len(templates)} шаблонов")
    return templates

def save_templates(templates_data):
    """Сохраняет шаблоны в базу данных"""
    print(f"💾 Попытка сохранения {len(templates_data)} шаблонов в базу данных...")
    
    success_count = 0
    for template_id, template_data in templates_data.items():
        if db.save_template(template_data):
            success_count += 1
    
    print(f"✅ Успешно сохранено {success_count}/{len(templates_data)} шаблонов")
    return success_count == len(templates_data)

def load_groups():
    """Загружает группы из базы данных"""
    print("📂 Загрузка групп из базы данных...")
    groups = db.load_groups()
    print(f"📊 Загружено {len(groups.get('groups', {}))} групп")
    return groups

def get_user_accessible_groups(user_id):
    """Возвращает группы, доступные пользователю"""
    from authorized_users import get_user_access_groups
    
    # Если отключена авторизация - все группы доступны
    from config import REQUIRE_AUTHORIZATION
    if not REQUIRE_AUTHORIZATION:
        groups_data = load_groups()
        return groups_data.get('groups', {})
    
    # Получаем группы пользователя
    user_groups = get_user_access_groups(user_id)
    all_groups = load_groups().get('groups', {})
    
    # Фильтруем группы по доступу
    accessible_groups = {}
    for group_id, group_data in all_groups.items():
        # Проверяем доступ через систему прав
        user_has_access = any(ug['id'] == group_id for ug in user_groups)
        
        # Для обратной совместимости проверяем старую систему allowed_users
        old_system_access = False
        allowed_users = group_data.get('allowed_users', [])
        if isinstance(allowed_users, list) and user_id in allowed_users:
            old_system_access = True
        
        if user_has_access or old_system_access:
            accessible_groups[group_id] = group_data
    
    return accessible_groups

def create_template(template_data):
    """Создает новый шаблон"""
    print("🔧 === НАЧАЛО СОЗДАНИЯ ШАБЛОНА ===")
    print(f"📊 Полученные данные: {template_data}")
    
    # Гарантируем что база данных инициализирована
    if not init_files():
        print("❌ Не удалось инициализировать базу данных для создания шаблона")
        return False, None
    
    template_id = str(uuid.uuid4())[:8]
    
    print(f"📝 Создание шаблона с ID: {template_id}")
    
    # Добавляем системные поля
    template_data['id'] = template_id
    template_data['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    template_data['subgroup'] = None
    
    print(f"📦 Данные для сохранения: {template_data}")
    
    if db.save_template(template_data):
        print(f"✅ Шаблон '{template_data['name']}' успешно создан (ID: {template_id})")
        return True, template_id
    else:
        print(f"❌ Ошибка сохранения шаблона {template_id}")
        return False, None

# ... остальные функции остаются без изменений ...

# Убираем автоматическую инициализацию при импорте чтобы избежать конфликта
print("📥 Template_manager загружен")

def get_templates_by_group(group_id):
    """Возвращает шаблоны по группе"""
    templates_data = load_templates()
    templates = []
    
    for template_id, template in templates_data.items():
        if template.get('group') == group_id:
            templates.append((template_id, template))
    
    print(f"📋 Найдено {len(templates)} шаблонов для группы {group_id}")
    return templates

def save_image(file_content, filename):
    """Сохраняет изображение - в Render это временное хранилище"""
    try:
        # В Render файловая система ephemeral, поэтому просто возвращаем путь
        file_ext = os.path.splitext(filename)[1]
        new_filename = f"{uuid.uuid4().hex}{file_ext}"
        
        # Сохраняем во временную директорию
        temp_dir = '/tmp/images'
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        filepath = os.path.join(temp_dir, new_filename)
        
        with open(filepath, 'wb') as f:
            f.write(file_content)
        
        print(f"✅ Изображение сохранено во временное хранилище: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Ошибка сохранения изображения: {e}")
        return None

def format_template_info(template):
    """Форматирует информацию о шаблоне для отображения"""
    days_names = []
    if template.get('days'):
        days_names = [DAYS_OF_WEEK[day] for day in template.get('days', [])]
    
    frequency_map = {
        "weekly": "1 в неделю",
        "2_per_month": "2 в месяц", 
        "monthly": "1 в месяц"
    }
    frequency = frequency_map.get(template.get('frequency'), template.get('frequency', 'Не указана'))
    
    info = f"📝 **{template['name']}**\n\n"
    info += f"🏷️ **Группа:** {template.get('group', 'Не указана')}\n"
    info += f"⏰ **Время:** {template.get('time', 'Не указано')} (МСК)\n"
    info += f"📅 **Дни:** {', '.join(days_names) if days_names else 'Не указаны'}\n"
    info += f"🔄 **Периодичность:** {frequency}\n"
    info += f"📄 **Текст:** {template.get('text', '')[:100]}...\n"
    info += f"🖼️ **Изображение:** {'✅ Есть' if template.get('image') else '❌ Нет'}\n"
    
    return info

def format_template_list_info(template):
    """Форматирует краткую информацию о шаблоне для списка"""
    days_names = []
    if template.get('days'):
        days_names = [DAYS_OF_WEEK[day] for day in template.get('days', [])]
    
    frequency_map = {
        "weekly": "1 в неделю",
        "2_per_month": "2 в месяц", 
        "monthly": "1 в месяц"
    }
    frequency = frequency_map.get(template.get('frequency'), template.get('frequency', 'Не указана'))
    
    info = f"📝 **{template['name']}**\n"
    info += f"⏰ Время: {template.get('time', 'Не указано')} | "
    info += f"📅 Дни: {len(days_names)} | "
    info += f"🔄 {frequency} | "
    info += f"🖼️ {'✅' if template.get('image') else '❌'}\n"
    info += f"📄 {template.get('text', '')[:80]}...\n"
    
    return info

def get_all_templates():
    """Возвращает все шаблоны"""
    return load_templates()

def delete_template_by_id(template_id):
    """Удаляет шаблон по ID"""
    if db.delete_template(template_id):
        print(f"✅ Шаблон {template_id} удален")
        return True, "Шаблон удален"
    
    print(f"❌ Ошибка удаления шаблона {template_id}")
    return False, "Ошибка удаления"

def get_template_by_id(template_id):
    """Возвращает шаблон по ID"""
    templates_data = load_templates()
    template = templates_data.get(template_id)
    
    if template:
        print(f"✅ Шаблон {template_id} найден: {template.get('name')}")
    else:
        print(f"❌ Шаблон {template_id} не найден")
    
    return template

def update_template_field(template_id, field, value):
    """Обновляет конкретное поле шаблона"""
    templates_data = load_templates()
    
    if template_id not in templates_data:
        return False, "Шаблон не найден"
    
    templates_data[template_id][field] = value
    
    if save_templates(templates_data):
        print(f"✅ Поле {field} шаблона {template_id} обновлено")
        return True, f"Поле {field} обновлено"
    
    print(f"❌ Ошибка обновления поля {field} шаблона {template_id}")
    return False, "Ошибка обновления"

def update_template(template_id, updated_data):
    """Полностью обновляет шаблон"""
    templates_data = load_templates()
    
    if template_id not in templates_data:
        return False, "Шаблон не найден"
    
    # Сохраняем ID и дату создания
    updated_data['id'] = template_id
    updated_data['created_at'] = templates_data[template_id].get('created_at', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    if db.save_template(updated_data):
        print(f"✅ Шаблон {template_id} полностью обновлен")
        return True, "Шаблон обновлен"
    
    print(f"❌ Ошибка обновления шаблона {template_id}")
    return False, "Ошибка обновления"

# Инициализация при импорте
print("🔄 Инициализация template_manager...")
init_files()
print("✅ Template_manager инициализирован")