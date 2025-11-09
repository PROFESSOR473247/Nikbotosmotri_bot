import json
import os
import uuid
from datetime import datetime

# Константы путей - используем абсолютные пути для надежности
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
TEMPLATES_FILE = os.path.join(DATA_DIR, 'templates.json')
GROUPS_FILE = os.path.join(DATA_DIR, 'groups.json')
IMAGES_DIR = os.path.join(DATA_DIR, 'images')

# Дни недели для отображения
DAYS_OF_WEEK = {
    0: "📅 Понедельник",
    1: "📅 Вторник", 
    2: "📅 Среда",
    3: "📅 Четверг",
    4: "📅 Пятница",
    5: "📅 Суббота",
    6: "📅 Воскресеньe"
}

FREQUENCY_TYPES = {
    "weekly": "📅 1 в неделю", 
    "2_per_month": "🗓️ 2 в месяц",
    "monthly": "📆 1 в месяц"
}

def ensure_data_directory():
    """Создает необходимые директории если их нет"""
    try:
        if not os.path.exists(DATA_DIR):
            print("📁 Создаю директорию 'data'...")
            os.makedirs(DATA_DIR, exist_ok=True)
            print("✅ Директория 'data' создана")
        
        if not os.path.exists(IMAGES_DIR):
            print("📁 Создаю директорию 'data/images'...")
            os.makedirs(IMAGES_DIR, exist_ok=True)
            print("✅ Директория 'data/images' создана")
            
        return True
    except Exception as e:
        print(f"❌ Ошибка создания директорий: {e}")
        return False

def init_files():
    """Инициализирует необходимые файлы если их нет"""
    print("🔄 Инициализация файлов...")
    
    if not ensure_data_directory():
        return False
    
    # Инициализация файла шаблонов
    try:
        if not os.path.exists(TEMPLATES_FILE):
            print("📄 Создаю файл шаблонов...")
            with open(TEMPLATES_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
            print("✅ Файл шаблонов создан")
        else:
            # Проверяем, что файл читается
            with open(TEMPLATES_FILE, 'r', encoding='utf-8') as f:
                json.load(f)
            print("✅ Файл шаблонов уже существует и валиден")
    except Exception as e:
        print(f"❌ Ошибка файла шаблонов: {e}. Пересоздаю...")
        try:
            with open(TEMPLATES_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
            print("✅ Файл шаблонов пересоздан")
        except Exception as e2:
            print(f"❌ Критическая ошибка создания файла шаблонов: {e2}")
            return False
    
    # Инициализация файла групп
    try:
        if not os.path.exists(GROUPS_FILE):
            print("📄 Создаю файл групп...")
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
        else:
            # Проверяем, что файл читается
            with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
                json.load(f)
            print("✅ Файл групп уже существует и валиден")
    except Exception as e:
        print(f"❌ Ошибка файла групп: {e}. Пересоздаю...")
        try:
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
            print("✅ Файл групп пересоздан")
        except Exception as e2:
            print(f"❌ Критическая ошибка создания файла групп: {e2}")
            return False
    
    print("✅ Все файлы инициализированы")
    return True

def load_templates():
    """Загружает шаблоны из файла"""
    print("📂 Загрузка шаблонов из файла...")
    
    # Гарантируем что файл существует
    if not init_files():
        print("❌ Не удалось инициализировать файлы")
        return {}
    
    try:
        if os.path.exists(TEMPLATES_FILE) and os.path.getsize(TEMPLATES_FILE) > 0:
            with open(TEMPLATES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"✅ Загружено {len(data)} шаблонов")
                return data
        else:
            print("📭 Файл шаблонов пуст или не существует")
            return {}
    except Exception as e:
        print(f"❌ Ошибка загрузки шаблонов: {e}")
        return {}

def save_templates(templates_data):
    """Сохраняет шаблоны в файл"""
    print(f"💾 Сохранение {len(templates_data)} шаблонов в файл...")
    
    # Гарантируем что файл существует
    if not init_files():
        print("❌ Не удалось инициализировать файлы перед сохранением")
        return False
    
    try:
        # Создаем временный файл для безопасного сохранения
        temp_file = TEMPLATES_FILE + '.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(templates_data, f, ensure_ascii=False, indent=4)
        
        # Заменяем оригинальный файл
        os.replace(temp_file, TEMPLATES_FILE)
        print(f"✅ Успешно сохранено {len(templates_data)} шаблонов")
        
        # Проверяем, что действительно сохранилось
        verify_data = load_templates()
        if len(verify_data) == len(templates_data):
            print("✅ ПРОВЕРКА: данные корректно сохранены")
        else:
            print(f"⚠️ ПРОВЕРКА: расхождение в данных. Ожидалось: {len(templates_data)}, получилось: {len(verify_data)}")
            
        return True
    except Exception as e:
        print(f"❌ Критическая ошибка сохранения шаблонов: {e}")
        return False

def load_groups():
    """Загружает группы из файла"""
    print("📂 Загрузка групп из файла...")
    
    # Гарантируем что файл существует
    if not init_files():
        print("❌ Не удалось инициализировать файлы")
        return {"groups": {}}
    
    try:
        if os.path.exists(GROUPS_FILE) and os.path.getsize(GROUPS_FILE) > 0:
            with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"✅ Загружено {len(data.get('groups', {}))} групп")
                return data
        else:
            print("📭 Файл групп пуст или не существует")
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
    
    print(f"👤 Пользователь {user_id} имеет доступ к {len(accessible_groups)} группам")
    return accessible_groups

def create_template(template_data):
    """Создает новый шаблон"""
    print("🔧 === НАЧАЛО СОЗДАНИЯ ШАБЛОНА ===")
    
    # Гарантируем что файлы существуют
    if not init_files():
        print("❌ Не удалось инициализировать файлы для создания шаблона")
        return False, None
    
    templates_data = load_templates()
    template_id = str(uuid.uuid4())[:8]
    
    print(f"📝 Создание шаблона с ID: {template_id}")
    print(f"📋 Данные шаблона: {json.dumps(template_data, ensure_ascii=False, default=str)}")
    
    # Добавляем системные поля
    template_data['id'] = template_id
    template_data['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    template_data['subgroup'] = None
    
    templates_data[template_id] = template_data
    
    print(f"💾 Сохраняем {len(templates_data)} шаблонов в файл...")
    
    if save_templates(templates_data):
        print(f"✅ Шаблон '{template_data['name']}' успешно создан (ID: {template_id})")
        return True, template_id
    else:
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
        # Гарантируем что директория существует
        if not ensure_data_directory():
            return None
            
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