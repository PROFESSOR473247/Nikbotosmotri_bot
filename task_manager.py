"""
Менеджер шаблонов с упрощенной структурой
Шаблоны теперь содержат только базовую информацию без расписания
"""

import json
import os
import uuid
import shutil
from datetime import datetime
from database import db

# Директория для изображений
IMAGES_DIR = "images"

# ===== ЗАЩИТНЫЕ ФУНКЦИИ =====

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
    """Сохраняет шаблон в базу данных (упрощенный)"""
    print(f"💾 Попытка сохранения шаблона в базу данных: {template_data.get('name')}")
    
    conn = db.get_connection()
    if not conn:
        print("❌ Не удалось подключиться к базе данных для сохранения шаблона")
        return False
        
    try:
        cursor = conn.cursor()
        
        # Подготавливаем данные (упрощенные)
        template_id = template_data.get('id')
        name = template_data.get('name', '')
        group_name = template_data.get('group', '')
        text = template_data.get('text', '')
        image_path = template_data.get('image')
        created_by = template_data.get('created_by')
        
        print(f"📊 Данные для сохранения шаблона:")
        print(f"   ID: {template_id}")
        print(f"   Name: {name}")
        print(f"   Group: {group_name}")
        print(f"   Text: {text[:50]}...")
        print(f"   Created_by: {created_by}")
        
        cursor.execute('''
            INSERT INTO templates (id, name, group_name, text, image_path, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                group_name = EXCLUDED.group_name,
                text = EXCLUDED.text,
                image_path = EXCLUDED.image_path,
                created_by = EXCLUDED.created_by
        ''', (
            template_id,
            name,
            group_name,
            text,
            image_path,
            created_by
        ))
        
        conn.commit()
        
        # Проверим что действительно сохранилось
        cursor.execute('SELECT COUNT(*) FROM templates WHERE id = %s', (template_id,))
        count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        if count > 0:
            print(f"✅ Шаблон {template_id} успешно сохранен в базе данных (проверено: {count} записей)")
            return True
        else:
            print(f"❌ Шаблон {template_id} не был сохранен в базу данных")
            return False
        
    except Exception as e:
        print(f"❌ Ошибка сохранения шаблона: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        return False

def load_templates():
    """Загружает все шаблоны из базы данных"""
    print("📂 Загрузка шаблонов из базы данных...")
    
    conn = db.get_connection()
    if not conn:
        print("❌ Не удалось подключиться к базе данных для загрузки шаблонов")
        return {}
        
    try:
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM templates ORDER BY created_at DESC')
        rows = cursor.fetchall()
        
        templates = {}
        for row in rows:
            try:
                template = {
                    'id': row[0],
                    'name': row[1],
                    'group': row[2],
                    'text': row[3],
                    'image': row[4],
                    'created_by': row[5],
                    'created_at': row[6].strftime("%Y-%m-%d %H:%M:%S") if row[6] else None
                }
                templates[template['id']] = template
                print(f"📥 Загружен шаблон: {template['name']} (ID: {template['id']})")
                
            except Exception as e:
                print(f"❌ Ошибка обработки строки шаблона: {e}")
                continue
        
        cursor.close()
        conn.close()
        
        print(f"✅ Загружено {len(templates)} шаблонов из базы данных")
        return templates
        
    except Exception as e:
        print(f"❌ Ошибка загрузки шаблонов: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.close()
        except:
            pass
        return {}

def get_all_templates():
    """Возвращает все шаблоны"""
    return load_templates()

def load_groups():
    """Загружает группы из базы данных"""
    print("📂 Загрузка групп из базы данных...")
    
    conn = db.get_connection()
    if not conn:
        print("❌ Не удалось подключиться к базе данных для загрузки групп")
        return {"groups": {}}
        
    try:
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM template_groups')
        rows = cursor.fetchall()
        
        groups = {"groups": {}}
        for row in rows:
            # Исправляем обработку JSON данных
            allowed_users = []
            if row[2]:
                try:
                    if isinstance(row[2], (str, bytes, bytearray)):
                        allowed_users = json.loads(row[2])
                    else:
                        allowed_users = row[2]  # Уже список
                except:
                    allowed_users = []
            
            groups["groups"][row[0]] = {
                "name": row[1],
                "allowed_users": allowed_users
            }
            print(f"📥 Загружена группа: {row[1]} (ID: {row[0]})")
        
        cursor.close()
        conn.close()
        
        print(f"✅ Загружено {len(groups['groups'])} групп из базы данных")
        return groups
        
    except Exception as e:
        print(f"❌ Ошибка загрузки групп: {e}")
        try:
            conn.close()
        except:
            pass
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
        template_name = safe_get_template_value(template, 'name', 'Без названия')
        template_text = safe_get_template_value(template, 'text', '')
        has_image = '✅ Есть' if template.get('image') else '❌ Нет'
        
        info = f"**{template_name}**\n"
        info += f"📄 Текст: {template_text[:100]}...\n"
        info += f"🖼️ Изображение: {has_image}\n"
        info += f"🏷️ Группа: {template.get('group', 'Не указана')}\n"
        
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
            has_image = "🖼️" if template.get('image') else "❌"
            template_name = safe_get_template_value(template, 'name', 'Без названия')
            template_group = safe_get_template_value(template, 'group', 'Не указана')
            template_text = safe_get_template_value(template, 'text', '')
            
            message += f"{i}. **{template_name}** {has_image}\n"
            message += f"   🏷️ Группа: {template_group}\n"
            message += f"   📄 Текст: {template_text[:50]}...\n\n"
        
        return message
    except Exception as e:
        print(f"❌ Ошибка форматирования списка шаблонов: {e}")
        return "❌ Ошибка загрузки списка шаблонов"

def format_template_preview(template):
    """Форматирует превью шаблона"""
    try:
        template_name = safe_get_template_value(template, 'name', 'Без названия')
        template_text = safe_get_template_value(template, 'text', '')
        
        preview = f"📝 **{template_name}**\n\n"
        preview += f"📄 {template_text}\n\n"
        
        if template.get('image'):
            preview += "🖼️ *Есть изображение*\n"
        
        preview += f"🏷️ Группа: {template.get('group', 'Не указана')}"
        
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

def get_template_by_name_and_group(template_name, group_id):
    """Возвращает шаблон по имени и группе"""
    try:
        templates = get_templates_by_group(group_id)
        for template_id, template in templates:
            if template.get('name') == template_name:
                return template_id, template
        return None, None
    except Exception as e:
        print(f"❌ Ошибка поиска шаблона по имени {template_name} в группе {group_id}: {e}")
        return None, None

def get_template_groups_for_user(user_id):
    """Возвращает группы шаблонов с шаблонами для пользователя"""
    try:
        accessible_groups = get_user_accessible_groups(user_id)
        groups_with_templates = {}
        
        for group_id in accessible_groups:
            templates = get_templates_by_group(group_id)
            if templates:
                groups_with_templates[group_id] = {
                    'group_data': accessible_groups[group_id],
                    'templates': templates
                }
        
        return groups_with_templates
    except Exception as e:
        print(f"❌ Ошибка получения групп с шаблонами для пользователя {user_id}: {e}")
        return {}

# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С ИЗОБРАЖЕНИЯМИ =====

def save_image(image_bytes, template_id):
    """Сохраняет изображение для шаблона"""
    try:
        # Создаем уникальное имя файла
        file_extension = '.jpg'  # По умолчанию jpg
        image_filename = f"{template_id}{file_extension}"
        image_path = os.path.join(IMAGES_DIR, image_filename)
        
        # Сохраняем файл
        with open(image_path, 'wb') as f:
            f.write(image_bytes)
        
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
            has_image = "🖼️" if template.get('image') else "❌"
            template_name = safe_get_template_value(template, 'name', 'Без названия')
            template_text = safe_get_template_value(template, 'text', '')
            
            message += f"{i}. **{template_name}** {has_image}\n"
            message += f"   📄 {template_text[:60]}...\n\n"
        
        return message
    except Exception as e:
        print(f"❌ Ошибка форматирования информации о группе {group_id}: {e}")
        return f"❌ Ошибка загрузки информации о группе"

def get_template_stats():
    """Возвращает статистику по шаблонам"""
    try:
        templates = load_templates()
        groups = get_template_groups()
        
        stats = {
            'total_templates': len(templates),
            'groups_count': len(groups),
            'templates_with_images': 0
        }
        
        for template in templates.values():
            if template.get('image'):
                stats['templates_with_images'] += 1
        
        return stats
    except Exception as e:
        print(f"❌ Ошибка получения статистики шаблонов: {e}")
        return {
            'total_templates': 0,
            'groups_count': 0,
            'templates_with_images': 0
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

def get_user_template_access(user_id):
    """Возвращает информацию о доступе пользователя к шаблонам"""
    try:
        accessible_groups = get_user_accessible_groups(user_id)
        all_templates = get_all_templates()
        
        user_templates = {}
        templates_by_group = {}
        
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
    except Exception as e:
        print(f"❌ Ошибка получения доступа пользователя {user_id} к шаблонам: {e}")
        return {
            'accessible_groups': {},
            'user_templates': {},
            'templates_by_group': {},
            'total_templates': 0,
            'total_groups': 0
        }

def format_all_templates_info(user_id):
    """Форматирует информацию о всех шаблонах пользователя"""
    try:
        access_info = get_user_template_access(user_id)
        
        if not access_info['user_templates']:
            return "📭 У вас нет доступных шаблонов"
        
        message = "📋 **Все ваши шаблоны:**\n\n"
        
        # Группируем по группам для лучшего отображения
        for group_id, templates in access_info['templates_by_group'].items():
            group_name = access_info['accessible_groups'].get(group_id, {}).get('name', group_id)
            message += f"**🏷️ {group_name}:**\n"
            
            for i, (template_id, template) in enumerate(templates, 1):
                has_image = "🖼️" if template.get('image') else ""
                template_name = safe_get_template_value(template, 'name', 'Без названия')
                
                message += f"  {i}. **{template_name}** {has_image}\n"
                message += f"     📄 {template['text'][:50]}...\n\n"
        
        message += f"**Всего:** {access_info['total_templates']} шаблонов в {access_info['total_groups']} группах"
        
        return message
    except Exception as e:
        print(f"❌ Ошибка форматирования всех шаблонов: {e}")
        return "❌ Ошибка загрузки информации о шаблонах"

def format_group_templates_detailed(group_id):
    """Детальная информация о шаблонах группы"""
    try:
        templates = get_templates_by_group(group_id)
        
        if not templates:
            return f"📭 В этой группе нет шаблонов"
        
        groups_data = load_groups()
        group_name = groups_data['groups'].get(group_id, {}).get('name', group_id)
        
        message = f"**🏷️ Группа: {group_name}**\n\n"
        
        for i, (template_id, template) in enumerate(templates, 1):
            has_image = "✅ Есть" if template.get('image') else "❌ Нет"
            
            message += f"**{i}. {template['name']}**\n"
            message += f"   📄 Текст: {template['text'][:80]}...\n"
            message += f"   🖼️ Изображение: {has_image}\n\n"
        
        return message
    except Exception as e:
        print(f"❌ Ошибка форматирования детальной информации группы {group_id}: {e}")
        return f"❌ Ошибка загрузки информации о группе"

# Инициализация при импорте
print("📥 Template_manager загружен")
init_files()
init_database()
print("✅ Template_manager инициализирован")