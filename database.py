import os
import psycopg2
import json
from datetime import datetime
import logging

class DatabaseManager:
    def __init__(self):
        self.connection_string = os.environ.get('DATABASE_URL')
        if not self.connection_string:
            logging.error("❌ DATABASE_URL не найден в переменных окружения")
            print("❌ DATABASE_URL не найден в переменных окружения")
        
    def get_connection(self):
        """Возвращает соединение с базой данных"""
        try:
            conn = psycopg2.connect(self.connection_string)
            return conn
        except Exception as e:
            logging.error(f"❌ Ошибка подключения к базе данных: {e}")
            print(f"❌ Ошибка подключения к базе данных: {e}")
            return None
    
    def init_database(self):
        """Инициализирует таблицы в базе данных"""
        print("🔄 Инициализация базы данных...")
        
        conn = self.get_connection()
        if not conn:
            print("❌ Не удалось подключиться к базе данных для инициализации")
            return False
        
        try:
            cursor = conn.cursor()
            
            # Таблица шаблонов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS templates (
                    id VARCHAR(20) PRIMARY KEY,
                    name TEXT NOT NULL,
                    group_name TEXT NOT NULL,
                    text TEXT,
                    image_path TEXT,
                    time TEXT,
                    days JSONB,
                    frequency TEXT,
                    created_by BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    subgroup TEXT
                )
            ''')
            
            # Таблица групп
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS groups (
                    id VARCHAR(50) PRIMARY KEY,
                    name TEXT NOT NULL,
                    allowed_users JSONB DEFAULT '[]'::jsonb
                )
            ''')
            
            # Вставляем группы по умолчанию (если их еще нет)
            cursor.execute('''
                INSERT INTO groups (id, name, allowed_users) 
                VALUES 
                ('hongqi', '🚗 Hongqi', '["812934047"]'::jsonb),
                ('turbomatiz', '🚙 TurboMatiz', '["812934047"]'::jsonb)
                ON CONFLICT (id) DO NOTHING
            ''')
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print("✅ База данных инициализирована")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка инициализации базы данных: {e}")
            try:
                conn.close()
            except:
                pass
            return False
    
    def save_template(self, template_data):
        """Сохраняет шаблон в базу данных"""
        print(f"💾 Попытка сохранения шаблона в базу данных: {template_data.get('name')}")
        
        conn = self.get_connection()
        if not conn:
            print("❌ Не удалось подключиться к базе данных для сохранения шаблона")
            return False
            
        try:
            cursor = conn.cursor()
            
            # Подготавливаем данные
            template_id = template_data.get('id')
            name = template_data.get('name', '')
            group_name = template_data.get('group', '')
            text = template_data.get('text', '')
            image_path = template_data.get('image')
            time_str = template_data.get('time', '')
            
            # Обрабатываем дни - гарантируем что это JSON строка
            days_data = template_data.get('days', [])
            if isinstance(days_data, list):
                days_json = json.dumps(days_data, ensure_ascii=False)
            else:
                days_json = '[]'
                
            frequency = template_data.get('frequency', '')
            created_by = template_data.get('created_by')
            subgroup = template_data.get('subgroup')
            
            print(f"📊 Данные для сохранения:")
            print(f"   ID: {template_id}")
            print(f"   Name: {name}")
            print(f"   Group: {group_name}")
            print(f"   Text: {text[:50]}...")
            print(f"   Time: {time_str}")
            print(f"   Days: {days_data}")
            print(f"   Frequency: {frequency}")
            print(f"   Created_by: {created_by}")
            
            cursor.execute('''
                INSERT INTO templates (id, name, group_name, text, image_path, time, days, frequency, created_by, subgroup)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    group_name = EXCLUDED.group_name,
                    text = EXCLUDED.text,
                    image_path = EXCLUDED.image_path,
                    time = EXCLUDED.time,
                    days = EXCLUDED.days,
                    frequency = EXCLUDED.frequency,
                    subgroup = EXCLUDED.subgroup
            ''', (
                template_id,
                name,
                group_name,
                text,
                image_path,
                time_str,
                days_json,
                frequency,
                created_by,
                subgroup
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
    
    def load_templates(self):
        """Загружает все шаблоны из базы данных"""
        print("📂 Загрузка шаблонов из базы данных...")
        
        conn = self.get_connection()
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
                    # Обрабатываем дни
                    days_data = []
                    if row[6]:  # days field
                        try:
                            if isinstance(row[6], (str, bytes, bytearray)):
                                days_data = json.loads(row[6])
                            else:
                                days_data = row[6]
                        except Exception as e:
                            print(f"⚠️ Ошибка парсинга дней для шаблона {row[0]}: {e}")
                            days_data = []
                    
                    template = {
                        'id': row[0],
                        'name': row[1],
                        'group': row[2],
                        'text': row[3],
                        'image': row[4],
                        'time': row[5],
                        'days': days_data,
                        'frequency': row[7],
                        'created_by': row[8],
                        'created_at': row[9].strftime("%Y-%m-%d %H:%M:%S") if row[9] else None,
                        'subgroup': row[10]
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
    
    def delete_template(self, template_id):
        """Удаляет шаблон из базы данных"""
        print(f"🗑️ Попытка удаления шаблона {template_id}")
        
        conn = self.get_connection()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM templates WHERE id = %s', (template_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Шаблон {template_id} удален из базы данных")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка удаления шаблона: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False
    
    def load_groups(self):
        """Загружает группы из базы данных"""
        print("📂 Загрузка групп из базы данных...")
        
        conn = self.get_connection()
        if not conn:
            print("❌ Не удалось подключиться к базе данных для загрузки групп")
            return {"groups": {}}
            
        try:
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM groups')
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

# Глобальный экземпляр менеджера базы данных
db = DatabaseManager()