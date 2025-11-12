import os
import psycopg2
import json
from datetime import datetime
import logging

class TaskDatabaseManager:
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
    
    def init_tasks_table(self):
        """Инициализирует таблицу задач в базе данных"""
        print("🔄 Инициализация таблицы задач...")
        
        conn = self.get_connection()
        if not conn:
            print("❌ Не удалось подключиться к базе данных для инициализации задач")
            return False
        
        try:
            cursor = conn.cursor()
            
            # Таблица задач
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
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print("✅ Таблица задач инициализирована")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка инициализации таблицы задач: {e}")
            try:
                conn.close()
            except:
                pass
            return False
    
    def save_task(self, task_data):
        """Сохраняет задачу в базу данных"""
        print(f"💾 Попытка сохранения задачи в базу данных: {task_data.get('template_name')}")
        
        conn = self.get_connection()
        if not conn:
            print("❌ Не удалось подключиться к базе данных для сохранения задачи")
            return False
            
        try:
            cursor = conn.cursor()
            
            # Подготавливаем данные
            task_id = task_data.get('id')
            template_id = task_data.get('template_id')
            template_name = task_data.get('template_name', '')
            template_text = task_data.get('template_text', '')
            template_image = task_data.get('template_image')
            group_name = task_data.get('group', '')
            time_str = task_data.get('time', '')
            
            # Обрабатываем дни - гарантируем что это JSON строка
            days_data = task_data.get('days', [])
            if isinstance(days_data, list):
                days_json = json.dumps(days_data, ensure_ascii=False)
            else:
                days_json = '[]'
                
            frequency = task_data.get('frequency', '')
            created_by = task_data.get('created_by')
            is_active = task_data.get('is_active', True)
            is_test = task_data.get('is_test', False)
            
            # Обрабатываем даты
            last_executed = task_data.get('last_executed')
            next_execution = task_data.get('next_execution')
            
            if last_executed:
                try:
                    last_executed = datetime.strptime(last_executed, "%Y-%m-%d %H:%M:%S")
                except:
                    last_executed = None
            
            if next_execution:
                try:
                    next_execution = datetime.strptime(next_execution, "%Y-%m-%d %H:%M:%S")
                except:
                    next_execution = None
            
            print(f"📊 Данные задачи для сохранения:")
            print(f"   ID: {task_id}")
            print(f"   Template: {template_name}")
            print(f"   Group: {group_name}")
            print(f"   Time: {time_str}")
            print(f"   Active: {is_active}")
            print(f"   Test: {is_test}")
            
            cursor.execute('''
                INSERT INTO tasks (id, template_id, template_name, template_text, template_image, 
                                 group_name, time, days, frequency, created_by, is_active, is_test,
                                 last_executed, next_execution)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    template_id = EXCLUDED.template_id,
                    template_name = EXCLUDED.template_name,
                    template_text = EXCLUDED.template_text,
                    template_image = EXCLUDED.template_image,
                    group_name = EXCLUDED.group_name,
                    time = EXCLUDED.time,
                    days = EXCLUDED.days,
                    frequency = EXCLUDED.frequency,
                    is_active = EXCLUDED.is_active,
                    is_test = EXCLUDED.is_test,
                    last_executed = EXCLUDED.last_executed,
                    next_execution = EXCLUDED.next_execution
            ''', (
                task_id,
                template_id,
                template_name,
                template_text,
                template_image,
                group_name,
                time_str,
                days_json,
                frequency,
                created_by,
                is_active,
                is_test,
                last_executed,
                next_execution
            ))
            
            conn.commit()
            
            # Проверим что действительно сохранилось
            cursor.execute('SELECT COUNT(*) FROM tasks WHERE id = %s', (task_id,))
            count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            if count > 0:
                print(f"✅ Задача {task_id} успешно сохранена в базе данных (проверено: {count} записей)")
                return True
            else:
                print(f"❌ Задача {task_id} не была сохранена в базу данных")
                return False
            
        except Exception as e:
            print(f"❌ Ошибка сохранения задачи: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False
    
    def load_tasks(self):
        """Загружает все задачи из базы данных"""
        print("📂 Загрузка задач из базы данных...")
        
        conn = self.get_connection()
        if not conn:
            print("❌ Не удалось подключиться к базе данных для загрузки задач")
            return {}
            
        try:
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
            rows = cursor.fetchall()
            
            tasks = {}
            for row in rows:
                try:
                    # Обрабатываем дни
                    days_data = []
                    if row[7]:  # days field
                        try:
                            if isinstance(row[7], (str, bytes, bytearray)):
                                days_data = json.loads(row[7])
                            else:
                                days_data = row[7]
                        except Exception as e:
                            print(f"⚠️ Ошибка парсинга дней для задачи {row[0]}: {e}")
                            days_data = []
                    
                    # Обрабатываем даты
                    last_executed = row[12].strftime("%Y-%m-%d %H:%M:%S") if row[12] else None
                    next_execution = row[13].strftime("%Y-%m-%d %H:%M:%S") if row[13] else None
                    
                    task = {
                        'id': row[0],
                        'template_id': row[1],
                        'template_name': row[2],
                        'template_text': row[3],
                        'template_image': row[4],
                        'group': row[5],
                        'time': row[6],
                        'days': days_data,
                        'frequency': row[8],
                        'created_by': row[9],
                        'created_at': row[10].strftime("%Y-%m-%d %H:%M:%S") if row[10] else None,
                        'is_active': row[11],
                        'is_test': row[12],
                        'last_executed': last_executed,
                        'next_execution': next_execution
                    }
                    tasks[task['id']] = task
                    print(f"📥 Загружена задача: {task['template_name']} (ID: {task['id']})")
                    
                except Exception as e:
                    print(f"❌ Ошибка обработки строки задачи: {e}")
                    continue
            
            cursor.close()
            conn.close()
            
            print(f"✅ Загружено {len(tasks)} задач из базы данных")
            return tasks
            
        except Exception as e:
            print(f"❌ Ошибка загрузки задач: {e}")
            import traceback
            traceback.print_exc()
            try:
                conn.close()
            except:
                pass
            return {}
    
    def deactivate_task(self, task_id):
        """Деактивирует задачу в базе данных"""
        print(f"🗑️ Попытка деактивации задачи {task_id}")
        
        conn = self.get_connection()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            
            cursor.execute('UPDATE tasks SET is_active = FALSE WHERE id = %s', (task_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Задача {task_id} деактивирована в базе данных")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка деактивации задачи: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False

# Глобальный экземпляр менеджера базы данных задач
task_db = TaskDatabaseManager()
