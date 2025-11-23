"""
Упрощенный менеджер шаблонов без времени, дней и периодичности
"""

import json
import os
import uuid
import shutil
from datetime import datetime
from database import db

# Директория для изображений
IMAGES_DIR = "images"

class SimplifiedTemplateManager:
    def __init__(self):
        self.images_dir = IMAGES_DIR
    
    def init_files(self):
        """Инициализирует файлы шаблонов и директории"""
        try:
            data_dir = "data"
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            
            # Создаем директорию для изображений
            if not os.path.exists(self.images_dir):
                os.makedirs(self.images_dir)
            
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

    def save_template(self, template_data):
        """Сохраняет упрощенный шаблон в базу данных"""
        print(f"💾 Сохранение упрощенного шаблона: {template_data.get('name')}")
        
        conn = db.get_connection()
        if not conn:
            print("❌ Не удалось подключиться к базе данных")
            return False
            
        try:
            cursor = conn.cursor()
            
            # Подготавливаем данные (только основные поля)
            template_id = template_data.get('id')
            name = template_data.get('name', '')
            group_name = template_data.get('group', '')
            text = template_data.get('text', '')
            image_path = template_data.get('image')
            created_by = template_data.get('created_by')
            
            print(f"📊 Данные упрощенного шаблона:")
            print(f"   ID: {template_id}")
            print(f"   Name: {name}")
            print(f"   Group: {group_name}")
            print(f"   Text: {text[:50]}...")
            print(f"   Image: {image_path}")
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
                print(f"✅ Упрощенный шаблон {template_id} успешно сохранен")
                return True
            else:
                print(f"❌ Упрощенный шаблон {template_id} не был сохранен")
                return False
            
        except Exception as e:
            print(f"❌ Ошибка сохранения упрощенного шаблона: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False

    def load_templates(self):
        """Загружает все упрощенные шаблоны из базы данных"""
        print("📂 Загрузка упрощенных шаблонов из базы данных...")
        
        conn = db.get_connection()
        if not conn:
            print("❌ Не удалось подключиться к базе данных")
            return {}
            
        try:
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, name, group_name, text, image_path, created_by, created_at FROM templates ORDER BY created_at DESC')
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
                    print(f"📥 Загружен упрощенный шаблон: {template['name']}")
                    
                except Exception as e:
                    print(f"❌ Ошибка обработки упрощенного шаблона: {e}")
                    continue
            
            cursor.close()
            conn.close()
            
            print(f"✅ Загружено {len(templates)} упрощенных шаблонов")
            return templates
            
        except Exception as e:
            print(f"❌ Ошибка загрузки упрощенных шаблонов: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.close()
            except:
                pass
            return {}

    def create_template(self, template_data):
        """Создает новый упрощенный шаблон"""
        try:
            # Генерируем ID для шаблона
            template_id = self.create_template_id()
            template_data['id'] = template_id
            
            # Сохраняем в базу данных
            success = self.save_template(template_data)
            
            if success:
                print(f"✅ Упрощенный шаблон создан: {template_data['name']} (ID: {template_id})")
                return True, template_id
            else:
                print(f"❌ Ошибка создания упрощенного шаблона: {template_data['name']}")
                return False, None
        except Exception as e:
            print(f"❌ Ошибка создания упрощенного шаблона: {e}")
            return False, None

    def create_template_id(self):
        """Создает уникальный ID для шаблона"""
        try:
            return str(uuid.uuid4())[:8]
        except Exception as e:
            print(f"❌ Ошибка создания ID шаблона: {e}")
            return str(int(datetime.now().timestamp()))[-8:]

    def format_template_info(self, template):
        """Форматирует информацию об упрощенном шаблоне"""
        try:
            template_name = template.get('name', 'Без названия')
            template_text = template.get('text', '')
            has_image = '✅ Есть' if template.get('image') else '❌ Нет'
            
            info = f"**{template_name}**\n"
            info += f"📄 Текст: {template_text[:100]}...\n"
            info += f"🖼️ Изображение: {has_image}\n"
            info += f"🏷️ Группа: {template.get('group', 'Не указана')}\n"
            
            return info
        except Exception as e:
            print(f"❌ Ошибка форматирования упрощенного шаблона: {e}")
            return "❌ Ошибка загрузки информации о шаблоне"

    def format_template_preview(self, template):
        """Форматирует превью упрощенного шаблона"""
        try:
            template_name = template.get('name', 'Без названия')
            template_text = template.get('text', '')
            
            preview = f"📝 **{template_name}**\n\n"
            preview += f"📄 {template_text}\n\n"
            
            if template.get('image'):
                preview += "🖼️ *Есть изображение*\n"
            
            preview += f"🏷️ Группа: {template.get('group', 'Не указана')}"
            
            return preview
        except Exception as e:
            print(f"❌ Ошибка форматирования превью упрощенного шаблона: {e}")
            return "❌ Ошибка загрузки превью шаблона"

    def save_image(self, image_bytes, template_id):
        """Сохраняет изображение для шаблона"""
        try:
            # Создаем уникальное имя файла
            file_extension = '.jpg'
            image_filename = f"{template_id}{file_extension}"
            image_path = os.path.join(self.images_dir, image_filename)
            
            # Сохраняем файл
            with open(image_path, 'wb') as f:
                f.write(image_bytes)
            
            print(f"✅ Изображение сохранено: {image_path}")
            return image_path
            
        except Exception as e:
            print(f"❌ Ошибка сохранения изображения: {e}")
            return None

    def delete_image(self, image_path):
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

# Глобальный экземпляр
simplified_template_manager = SimplifiedTemplateManager()
