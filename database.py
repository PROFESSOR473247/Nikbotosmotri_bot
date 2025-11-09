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
        
    def get_connection(self):
        """Возвращает соединение с базой данных"""
        try:
            conn = psycopg2.connect(self.connection_string)
            return conn
        except Exception as e:
            logging.error(f"❌ Ошибка подключения к базе данных: {e}")
            return None
    
    def init_database(self):
        """Инициализирует таблицы в базе данных"""
        print("🔄 Инициализация базы данных...")
        
        conn = self.get_connection()
        if not conn:
            print("❌ Не удалось подключиться к базе данных")
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
        conn = self.get_connection()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            
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
                template_data['id'],
                template_data['name'],
                template_data['group'],
                template_data.get('text'),
                template_data.get('image'),
                template_data.get('time'),
                json.dumps(template_data.get('days', [])),
                template_data.get('frequency'),
                template_data.get('created_by'),
                template_data.get('subgroup')
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Шаблон {template_data['id']} сохранен в базе данных")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка сохранения шаблона: {e}")
            try:
                conn.close()
            except:
                pass
            return False
    
    def load_templates(self):
        """Загружает все шаблоны из базы данных"""
        conn = self.get_connection()
        if not conn:
            return {}
            
        try:
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM templates ORDER BY created_at DESC')
            rows = cursor.fetchall()
            
            templates = {}
            for row in rows:
                template = {
                    'id': row[0],
                    'name': row[1],
                    'group': row[2],
                    'text': row[3],
                    'image': row[4],
                    'time': row[5],
                    'days': json.loads(row[6]) if row[6] else [],
                    'frequency': row[7],
                    'created_by': row[8],
                    'created_at': row[9].strftime("%Y-%m-%d %H:%M:%S") if row[9] else None,
                    'subgroup': row[10]
                }
                templates[template['id']] = template
            
            cursor.close()
            conn.close()
            
            print(f"✅ Загружено {len(templates)} шаблонов из базы данных")
            return templates
            
        except Exception as e:
            print(f"❌ Ошибка загрузки шаблонов: {e}")
            try:
                conn.close()
            except:
                pass
            return {}
    
    def delete_template(self, template_id):
        """Удаляет шаблон из базы данных"""
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
                conn.close()
            except:
                pass
            return False
    
    def load_groups(self):
        """Загружает группы из базы данных"""
        conn = self.get_connection()
        if not conn:
            return {"groups": {}}
            
        try:
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM groups')
            rows = cursor.fetchall()
            
            groups = {"groups": {}}
            for row in rows:
                groups["groups"][row[0]] = {
                    "name": row[1],
                    "allowed_users": json.loads(row[2]) if row[2] else []
                }
            
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
