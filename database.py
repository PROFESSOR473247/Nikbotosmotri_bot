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
        """Инициализирует все таблицы в базе данных"""
        print("🔄 Инициализация базы данных...")
        
        conn = self.get_connection()
        if not conn:
            print("❌ Не удалось подключиться к базе данных для инициализации")
            return False
        
        try:
            cursor = conn.cursor()
            
            # ===== ТАБЛИЦА ШАБЛОНОВ =====
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
            print("✅ Таблица 'templates' создана/проверена")
            
            # ===== ТАБЛИЦА ГРУПП ШАБЛОНОВ =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS template_groups (
                    id VARCHAR(50) PRIMARY KEY,
                    name TEXT NOT NULL,
                    allowed_users JSONB DEFAULT '[]'::jsonb
                )
            ''')
            print("✅ Таблица 'template_groups' создана/проверена")
            
            # ===== ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    full_name TEXT NOT NULL,
                    role TEXT DEFAULT 'guest',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            print("✅ Таблица 'users' создана/проверена")
            
            # ===== ТАБЛИЦА TELEGRAM ЧАТОВ =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS telegram_chats (
                    chat_id BIGINT PRIMARY KEY,
                    chat_name TEXT NOT NULL,
                    original_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            print("✅ Таблица 'telegram_chats' создана/проверена")
            
            # ===== ТАБЛИЦА СВЯЗИ ПОЛЬЗОВАТЕЛЕЙ И TELEGRAM ЧАТОВ =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_chat_access (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                    chat_id BIGINT REFERENCES telegram_chats(chat_id) ON DELETE CASCADE,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, chat_id)
                )
            ''')
            print("✅ Таблица 'user_chat_access' создана/проверена")
            
            # ===== ТАБЛИЦА СВЯЗИ ПОЛЬЗОВАТЕЛЕЙ И ГРУПП ШАБЛОНОВ =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_template_group_access (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                    group_id VARCHAR(50) REFERENCES template_groups(id) ON DELETE CASCADE,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, group_id)
                )
            ''')
            print("✅ Таблица 'user_template_group_access' создана/проверена")
            
            # ===== ТАБЛИЦА ЗАДАЧ =====
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id VARCHAR(20) PRIMARY KEY,
                    template_id VARCHAR(20),
                    template_name TEXT NOT NULL,
                    template_text TEXT,
                    template_image TEXT,
                    group_name TEXT NOT NULL,
                    time TEXT,
                    days JSONB,
                    frequency TEXT,
                    created_by BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_test BOOLEAN DEFAULT FALSE,
                    last_executed TIMESTAMP,
                    next_execution TIMESTAMP
                )
            ''')
            print("✅ Таблица 'tasks' создана/проверена")
            
            # ===== ДАННЫЕ ПО УМОЛЧАНИЮ =====
            
            # Группы шаблонов по умолчанию
            cursor.execute('''
                INSERT INTO template_groups (id, name, allowed_users) 
                VALUES 
                ('hongqi', '🚗 Hongqi', '[]'::jsonb),
                ('turbomatiz', '🚙 TurboMatiz', '[]'::jsonb)
                ON CONFLICT (id) DO NOTHING
            ''')
            print("✅ Группы шаблонов по умолчанию добавлены")
            
            # Администратор по умолчанию
            cursor.execute('''
                INSERT INTO users (user_id, username, full_name, role) 
                VALUES (812934047, 'admin', 'Administrator', 'admin')
                ON CONFLICT (user_id) DO NOTHING
            ''')
            print("✅ Администратор по умолчанию добавлен")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print("✅ База данных полностью инициализирована")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка инициализации базы данных: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False
    
    # ===== МЕТОДЫ ДЛЯ ШАБЛОНОВ =====
    
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
    
    # ===== МЕТОДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ =====
    
    def add_user(self, user_id, username, full_name, role='guest'):
        """Добавляет нового пользователя"""
        conn = self.get_connection()
        if not conn:
            return False, "Ошибка подключения к базе данных"
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO users (user_id, username, full_name, role)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    full_name = EXCLUDED.full_name,
                    role = EXCLUDED.role
            ''', (user_id, username, full_name, role))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Пользователь {user_id} добавлен/обновлен")
            return True, "Пользователь успешно добавлен"
            
        except Exception as e:
            print(f"❌ Ошибка добавления пользователя: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False, f"Ошибка добавления пользователя: {e}"
    
    def get_all_users(self):
        """Возвращает всех пользователей"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT u.user_id, u.username, u.full_name, u.role, u.created_at, u.is_active
                FROM users u
                ORDER BY u.created_at DESC
            ''')
            
            rows = cursor.fetchall()
            users = []
            
            for row in rows:
                user = {
                    'user_id': row[0],
                    'username': row[1],
                    'full_name': row[2],
                    'role': row[3],
                    'created_at': row[4].strftime("%Y-%m-%d %H:%M:%S") if row[4] else None,
                    'is_active': row[5]
                }
                users.append(user)
            
            cursor.close()
            conn.close()
            
            return users
            
        except Exception as e:
            print(f"❌ Ошибка получения пользователей: {e}")
            try:
                conn.close()
            except:
                pass
            return []
    
    def delete_user(self, user_id):
        """Удаляет пользователя"""
        conn = self.get_connection()
        if not conn:
            return False, "Ошибка подключения к базе данных"
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM users WHERE user_id = %s', (user_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Пользователь {user_id} удален")
            return True, "Пользователь успешно удален"
            
        except Exception as e:
            print(f"❌ Ошибка удаления пользователя: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False, f"Ошибка удаления пользователя: {e}"
    
    def update_user_role(self, user_id, new_role):
        """Обновляет роль пользователя"""
        conn = self.get_connection()
        if not conn:
            return False, "Ошибка подключения к базе данных"
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('UPDATE users SET role = %s WHERE user_id = %s', (new_role, user_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Роль пользователя {user_id} обновлена на {new_role}")
            return True, "Роль пользователя обновлена"
            
        except Exception as e:
            print(f"❌ Ошибка обновления роли пользователя: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False, f"Ошибка обновления роли: {e}"
    
    # ===== МЕТОДЫ ДЛЯ TELEGRAM ЧАТОВ =====
    
    def add_telegram_chat(self, chat_id, chat_name, original_name=None):
        """Добавляет новый Telegram чат"""
        conn = self.get_connection()
        if not conn:
            return False, "Ошибка подключения к базе данных"
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO telegram_chats (chat_id, chat_name, original_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (chat_id) DO UPDATE SET
                    chat_name = EXCLUDED.chat_name,
                    original_name = EXCLUDED.original_name
            ''', (chat_id, chat_name, original_name))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Telegram чат {chat_id} добавлен/обновлен")
            return True, "Telegram чат успешно добавлен"
            
        except Exception as e:
            print(f"❌ Ошибка добавления Telegram чата: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False, f"Ошибка добавления чата: {e}"
    
    def get_all_chats(self):
        """Возвращает все Telegram чаты"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM telegram_chats ORDER BY created_at DESC')
            
            rows = cursor.fetchall()
            chats = []
            
            for row in rows:
                chat = {
                    'chat_id': row[0],
                    'chat_name': row[1],
                    'original_name': row[2],
                    'created_at': row[3].strftime("%Y-%m-%d %H:%M:%S") if row[3] else None,
                    'is_active': row[4]
                }
                chats.append(chat)
            
            cursor.close()
            conn.close()
            
            return chats
            
        except Exception as e:
            print(f"❌ Ошибка получения чатов: {e}")
            try:
                conn.close()
            except:
                pass
            return []
    
    def delete_chat(self, chat_id):
        """Удаляет Telegram чат"""
        conn = self.get_connection()
        if not conn:
            return False, "Ошибка подключения к базе данных"
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM telegram_chats WHERE chat_id = %s', (chat_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Telegram чат {chat_id} удален")
            return True, "Telegram чат успешно удален"
            
        except Exception as e:
            print(f"❌ Ошибка удаления чата: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False, f"Ошибка удаления чата: {e}"
    
    # ===== МЕТОДЫ ДЛЯ УПРАВЛЕНИЯ ДОСТУПОМ =====
    
    def grant_chat_access(self, user_id, chat_id):
        """Предоставляет доступ пользователю к чату"""
        conn = self.get_connection()
        if not conn:
            return False, "Ошибка подключения к базе данных"
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_chat_access (user_id, chat_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, chat_id) DO NOTHING
            ''', (user_id, chat_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Пользователю {user_id} предоставлен доступ к чату {chat_id}")
            return True, "Доступ к чату предоставлен"
            
        except Exception as e:
            print(f"❌ Ошибка предоставления доступа к чату: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False, f"Ошибка предоставления доступа: {e}"
    
    def revoke_chat_access(self, user_id, chat_id):
        """Отзывает доступ пользователя к чату"""
        conn = self.get_connection()
        if not conn:
            return False, "Ошибка подключения к базе данных"
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM user_chat_access WHERE user_id = %s AND chat_id = %s', (user_id, chat_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ У пользователя {user_id} отозван доступ к чату {chat_id}")
            return True, "Доступ к чату отозван"
            
        except Exception as e:
            print(f"❌ Ошибка отзыва доступа к чату: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False, f"Ошибка отзыва доступа: {e}"
    
    def grant_template_group_access(self, user_id, group_id):
        """Предоставляет доступ пользователю к группе шаблонов"""
        conn = self.get_connection()
        if not conn:
            return False, "Ошибка подключения к базе данных"
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_template_group_access (user_id, group_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, group_id) DO NOTHING
            ''', (user_id, group_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Пользователю {user_id} предоставлен доступ к группе {group_id}")
            return True, "Доступ к группе предоставлен"
            
        except Exception as e:
            print(f"❌ Ошибка предоставления доступа к группе: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False, f"Ошибка предоставления доступа: {e}"
    
    def revoke_template_group_access(self, user_id, group_id):
        """Отзывает доступ пользователя к группе шаблонов"""
        conn = self.get_connection()
        if not conn:
            return False, "Ошибка подключения к базе данных"
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM user_template_group_access WHERE user_id = %s AND group_id = %s', (user_id, group_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ У пользователя {user_id} отозван доступ к группе {group_id}")
            return True, "Доступ к группе отозван"
            
        except Exception as e:
            print(f"❌ Ошибка отзыва доступа к группе: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False, f"Ошибка отзыва доступа: {e}"
    
    def get_user_chat_access(self, user_id):
        """Возвращает чаты, к которым у пользователя есть доступ"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT tc.chat_id, tc.chat_name 
                FROM telegram_chats tc
                JOIN user_chat_access uc ON tc.chat_id = uc.chat_id
                WHERE uc.user_id = %s AND tc.is_active = TRUE
            ''', (user_id,))
            
            rows = cursor.fetchall()
            chats = [{'chat_id': row[0], 'chat_name': row[1]} for row in rows]
            
            cursor.close()
            conn.close()
            
            return chats
            
        except Exception as e:
            print(f"❌ Ошибка получения доступа к чатам: {e}")
            try:
                conn.close()
            except:
                pass
            return []
    
    def get_user_template_group_access(self, user_id):
        """Возвращает группы шаблонов, к которым у пользователя есть доступ"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT tg.id, tg.name 
                FROM template_groups tg
                JOIN user_template_group_access ut ON tg.id = ut.group_id
                WHERE ut.user_id = %s
            ''', (user_id,))
            
            rows = cursor.fetchall()
            groups = [{'id': row[0], 'name': row[1]} for row in rows]
            
            cursor.close()
            conn.close()
            
            return groups
            
        except Exception as e:
            print(f"❌ Ошибка получения доступа к группам: {e}")
            try:
                conn.close()
            except:
                pass
            return []
    
    def get_chat_users(self, chat_id):
        """Возвращает пользователей, имеющих доступ к чату"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT u.user_id, u.username, u.full_name, u.role
                FROM users u
                JOIN user_chat_access uc ON u.user_id = uc.user_id
                WHERE uc.chat_id = %s AND u.is_active = TRUE
            ''', (chat_id,))
            
            rows = cursor.fetchall()
            users = [{'user_id': row[0], 'username': row[1], 'full_name': row[2], 'role': row[3]} for row in rows]
            
            cursor.close()
            conn.close()
            
            return users
            
        except Exception as e:
            print(f"❌ Ошибка получения пользователей чата: {e}")
            try:
                conn.close()
            except:
                pass
            return []
    
    def get_group_users(self, group_id):
        """Возвращает пользователей, имеющих доступ к группе шаблонов"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT u.user_id, u.username, u.full_name, u.role
                FROM users u
                JOIN user_template_group_access ut ON u.user_id = ut.user_id
                WHERE ut.group_id = %s AND u.is_active = TRUE
            ''', (group_id,))
            
            rows = cursor.fetchall()
            users = [{'user_id': row[0], 'username': row[1], 'full_name': row[2], 'role': row[3]} for row in rows]
            
            cursor.close()
            conn.close()
            
            return users
            
        except Exception as e:
            print(f"❌ Ошибка получения пользователей группы: {e}")
            try:
                conn.close()
            except:
                pass
            return []

# Глобальный экземпляр менеджера базы данных
db = DatabaseManager()
