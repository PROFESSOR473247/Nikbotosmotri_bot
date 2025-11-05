import json
import os
import uuid
from datetime import datetime

TEMPLATES_FILE = 'templates_data.json'
GROUPS_FILE = 'template_groups.json'
IMAGES_DIR = 'images'

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
    "2_per_week": "🔄 2 в неделю",
    "weekly": "📅 1 в неделю", 
    "2_per_month": "🗓️ 2 в месяц",
    "monthly": "📆 1 в месяц"
}

def init_files():
    """Инициализирует необходимые файлы если их нет"""
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)
    
    if not os.path.exists(TEMPLATES_FILE):
        with open(TEMPLATES_FILE, 'w', encoding='utf-8') as f:
            json.dump({"templates": {}}, f, ensure_ascii=False, indent=4)
    
    if not os.path.exists(GROUPS_FILE):
        default_groups = {
            "groups": {
                "hongqi": {
                    "name": "🚗 Hongqi",
                    "subgroups": {
                        "inspection": "🔍 Осмотры",
                        "reminders": "⏰ Напоминания"
                    },
                    "allowed_users": ["812934047"]
                },
                "turbomatiz": {
                    "name": "🚙 TurboMatiz",
                    "subgroups": {
                        "payments": "💳 Оплаты", 
                        "inspections": "🔍 Осмотры",
                        "cleaning": "🧼 Чистка"
                    },
                    "allowed_users": ["812934047"]
                }
            }
        }
        with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_groups, f, ensure_ascii=False, indent=4)

def load_templates():
    """Загружает шаблоны из файла"""
    try:
        if os.path.exists(TEMPLATES_FILE):
            with open(TEMPLATES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"templates": {}}
    except Exception as e:
        print(f"❌ Ошибка загрузки шаблонов: {e}")
        return {"templates": {}}

def save_templates(templates_data):
    """Сохраняет шаблоны в файл"""
    try:
        with open(TEMPLATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(templates_data, f, ensure_ascii=False, indent=4)
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
    
    template_data['id'] = template_id
    template_data['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    templates_data['templates'][template_id] = template_data
    
    if save_templates(templates_data):
        return True, template_id
    return False, None

def get_templates_by_group(group_id, subgroup_id=None):
    """Возвращает шаблоны по группе и подгруппе"""
    templates_data = load_templates()
    templates = []
    
    for template_id, template in templates_data['templates'].items():
        if template.get('group') == group_id:
            if subgroup_id is None or template.get('subgroup') == subgroup_id:
                templates.append((template_id, template))
    
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
        
        return filepath
    except Exception as e:
        print(f"❌ Ошибка сохранения изображения: {e}")
        return None

def format_template_info(template):
    """Форматирует информацию о шаблоне для отображения"""
    days_names = [DAYS_OF_WEEK[day] for day in template.get('days', [])]
    frequency = FREQUENCY_TYPES.get(template.get('frequency'), template.get('frequency', 'Не указана'))
    
    info = f"📝 **{template['name']}**\n\n"
    info += f"🏷️ **Группа:** {template.get('group', 'Не указана')}\n"
    if template.get('subgroup'):
        info += f"📂 **Подгруппа:** {template.get('subgroup', 'Не указана')}\n"
    info += f"⏰ **Время:** {template.get('time', 'Не указано')} (МСК)\n"
    info += f"📅 **Дни:** {', '.join(days_names)}\n"
    info += f"🔄 **Периодичность:** {frequency}\n"
    info += f"📄 **Текст:** {template.get('text', '')[:100]}...\n"
    info += f"🖼️ **Изображение:** {'✅ Есть' if template.get('image') else '❌ Нет'}\n"
    
    return info

# НОВЫЕ ФУНКЦИИ ДЛЯ РЕДАКТИРОВАНИЯ И УДАЛЕНИЯ

def get_all_templates():
    """Возвращает все шаблоны"""
    templates_data = load_templates()
    return templates_data.get('templates', {})

def delete_template_by_id(template_id):
    """Удаляет шаблон по ID"""
    templates_data = load_templates()
    
    if template_id not in templates_data['templates']:
        return False, "Шаблон не найден"
    
    # Удаляем изображение если есть
    template = templates_data['templates'][template_id]
    if template.get('image') and os.path.exists(template['image']):
        try:
            os.remove(template['image'])
        except Exception as e:
            print(f"⚠️ Ошибка удаления изображения: {e}")
    
    del templates_data['templates'][template_id]
    
    if save_templates(templates_data):
        return True, "Шаблон удален"
    return False, "Ошибка удаления"

def get_template_by_id(template_id):
    """Возвращает шаблон по ID"""
    templates_data = load_templates()
    return templates_data['templates'].get(template_id)

def update_template_field(template_id, field, value):
    """Обновляет конкретное поле шаблона"""
    templates_data = load_templates()
    
    if template_id not in templates_data['templates']:
        return False, "Шаблон не найден"
    
    templates_data['templates'][template_id][field] = value
    
    if save_templates(templates_data):
        return True, f"Поле {field} обновлено"
    return False, "Ошибка обновления"

# Инициализация при импорте
init_files()
