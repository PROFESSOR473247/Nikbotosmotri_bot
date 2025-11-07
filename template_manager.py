import json
import os
import uuid
from datetime import datetime

TEMPLATES_FILE = 'data/templates.json'
GROUPS_FILE = 'data/groups.json'
IMAGES_DIR = 'data/images'

# Дни недели для отображения
DAYS_OF_WEEK = {
    0: "📅 Понедельник",
    1: "📅 Вторник", 
    2: "📅 Среда",
    3: "📅 Четверг",
    4: "📅 Пятница",
    5: "📅 Суббота",
    6: "📅 Воскресенье"
}

FREQUENCY_TYPES = {
    "weekly": "📅 1 в неделю", 
    "2_per_month": "🗓️ 2 в месяц",
    "monthly": "📆 1 в месяц"
}

def ensure_data_directory():
    """Создает необходимые директории если их нет"""
    os.makedirs('data', exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)

def init_files():
    """Инициализирует необходимые файлы если их нет"""
    ensure_data_directory()
    
    # Инициализация файла шаблонов
    if not os.path.exists(TEMPLATES_FILE):
        with open(TEMPLATES_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        print("✅ Файл шаблонов создан")
    
    # Инициализация файла групп
    if not os.path.exists(GROUPS_FILE):
        default_groups = {
            "groups": {
                "hongqi": {
                    "name": "🚗 Hongqi",
                    "allowed_users": ["812934047"]
                },
                "turbomatiz": {
                    "name": "🚙 TurboMatiz", 
                    "allowed_users": ["812934047"]
                }
            }
        }
        with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_groups, f, ensure_ascii=False, indent=4)
        print("✅ Файл групп создан")

def load_templates():
    """Загружает шаблоны из файла"""
    try:
        if os.path.exists(TEMPLATES_FILE):
            with open(TEMPLATES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"✅ Загружено {len(data)} шаблонов из файла")
                return data
        print("⚠️ Файл шаблонов не существует, возвращаю пустой словарь")
        return {}
    except Exception as e:
        print(f"❌ Ошибка загрузки шаблонов: {e}")
        return {}

def save_templates(templates_data):
    """Сохраняет шаблоны в файл"""
    try:
        with open(TEMPLATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(templates_data, f, ensure_ascii=False, indent=4)
        print(f"✅ Шаблоны сохранены в файл ({len(templates_data)} записей)")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения шаблонов: {e}")
        return False

def load_groups():
    """Загружает группы из файла"""
    try:
        if os.path.exists(GROUPS_FILE):
            with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"groups": {}}
    except Exception as e:
        print(f"❌ Ошибка загрузки групп: {e}")
        return {"groups": {}}

def get_user_accessible_groups(user_id):
    """Возвращает группы доступные пользователю"""
    from authorized_users import get_user_groups
    user_groups = get_user_groups(user_id)
    groups_data = load_groups()
    
    accessible_groups = {}
    for group_id, group_data in groups_data.get('groups', {}).items():
        if group_id in user_groups or str(user_id) in group_data.get('allowed_users', []):
            accessible_groups[group_id] = group_data
    
    return accessible_groups

def create_template(template_data):
    """Создает новый шаблон"""
    templates_data = load_templates()
    template_id = str(uuid.uuid4())[:8]
    
    print(f"🔧 Создание шаблона с ID: {template_id}")
    
    # Убедимся, что subgroup всегда None (убрали подгруппы)
    template_data['subgroup'] = None
    template_data['id'] = template_id
    template_data['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    templates_data[template_id] = template_data
    
    if save_templates(templates_data):
        print(f"✅ Шаблон {template_id} успешно создан и сохранен")
        return True, template_id
    
    print(f"❌ Ошибка сохранения шаблона {template_id}")
    return False, None

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
    """Сохраняет изображение и возвращает путь"""
    try:
        # Создаем уникальное имя файла
        file_ext = os.path.splitext(filename)[1]
        new_filename = f"{uuid.uuid4().hex}{file_ext}"
        filepath = os.path.join(IMAGES_DIR, new_filename)
        
        with open(filepath, 'wb') as f:
            f.write(file_content)
        
        print(f"✅ Изображение сохранено: {filepath}")
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
    templates_data = load_templates()
    
    if template_id not in templates_data:
        return False, "Шаблон не найден"
    
    # Удаляем изображение если есть
    template = templates_data[template_id]
    if template.get('image') and os.path.exists(template['image']):
        try:
            os.remove(template['image'])
            print(f"✅ Изображение шаблона {template_id} удалено")
        except Exception as e:
            print(f"⚠️ Ошибка удаления изображения: {e}")
    
    del templates_data[template_id]
    
    if save_templates(templates_data):
        print(f"✅ Шаблон {template_id} удален")
        return True, "Шаблон удален"
    
    print(f"❌ Ошибка удаления шаблона {template_id}")
    return False, "Ошибка удаления"

def get_template_by_id(template_id):
    """Возвращает шаблон по ID"""
    templates_data = load_templates()
    template = templates_data.get(template_id)
    
    if template:
        print(f"✅ Шаблон {template_id} найден")
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
    
    templates_data[template_id] = updated_data
    
    if save_templates(templates_data):
        print(f"✅ Шаблон {template_id} полностью обновлен")
        return True, "Шаблон обновлен"
    
    print(f"❌ Ошибка обновления шаблона {template_id}")
    return False, "Ошибка обновления"

# Инициализация при импорте
print("🔄 Инициализация template_manager...")
init_files()
print("✅ Template_manager инициализирован")