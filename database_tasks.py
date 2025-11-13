import os
import json
from datetime import datetime
import logging
from database import db

logger = logging.getLogger(__name__)

def save_task_to_db(task_data):
    """Сохраняет задачу в базу данных"""
    print(f"💾 Попытка сохранения задачи в базу данных: {task_data.get('template_name')}")
    
    conn = db.get_connection()
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
        group_name = task_data.get('group_name', '')
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
        last_executed = task_data.get('last_executed')
        next_execution = task_data.get('next_execution')
        target_chat_id = task_data.get('target_chat_id')
        
        print(f"📊 Данные задачи для сохранения:")
        print(f"   ID: {task_id}")
        print(f"   Name: {template_name}")
        print(f"   Group: {group_name}")
        print(f"   Time: {time_str}")
        print(f"   Target Chat: {target_chat_id}")
        
        cursor.execute('''
            INSERT INTO tasks (id, template_id, template_name, template_text, template_image, 
                             group_name, time, days, frequency, created_by, is_active, is_test, 
                             last_executed, next_execution, target_chat_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                template_id = EXCLUDED.template_id,
                template_name = EXCLUDED.template_name,
                template_text = EXCLUDED.template_text,
                template_image = EXCLUDED.template_image,
                group_name = EXCLUDED.group_name,
                time = EXCLUDED.time,
                days = EXCLUDED.days,
                frequency = EXCLUDED.frequency,
                created_by = EXCLUDED.created_by,
                is_active = EXCLUDED.is_active,
                is_test = EXCLUDED.is_test,
                last_executed = EXCLUDED.last_executed,
                next_execution = EXCLUDED.next_execution,
                target_chat_id = EXCLUDED.target_chat_id
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
            next_execution,
            target_chat_id
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

def load_tasks_from_db():
    """Загружает все задачи из базы данных"""
    print("📂 Загрузка задач из базы данных...")
    
    conn = db.get_connection()
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
                
                task = {
                    'id': row[0],
                    'template_id': row[1],
                    'template_name': row[2],
                    'template_text': row[3],
                    'template_image': row[4],
                    'group_name': row[5],
                    'time': row[6],
                    'days': days_data,
                    'frequency': row[8],
                    'created_by': row[9],
                    'created_at': row[10].strftime("%Y-%m-%d %H:%M:%S") if row[10] else None,
                    'is_active': row[11],
                    'is_test': row[12],
                    'last_executed': row[13].strftime("%Y-%m-%d %H:%M:%S") if row[13] else None,
                    'next_execution': row[14].strftime("%Y-%m-%d %H:%M:%S") if row[14] else None,
                    'target_chat_id': row[15]  # Новое поле
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

def update_task_in_db(task_id, task_data):
    """Обновляет задачу в базе данных"""
    print(f"🔄 Обновление задачи {task_id} в базе данных")
    
    conn = db.get_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # Обрабатываем дни
        days_data = task_data.get('days', [])
        if isinstance(days_data, list):
            days_json = json.dumps(days_data, ensure_ascii=False)
        else:
            days_json = '[]'
        
        cursor.execute('''
            UPDATE tasks SET
                template_id = %s,
                template_name = %s,
                template_text = %s,
                template_image = %s,
                group_name = %s,
                time = %s,
                days = %s,
                frequency = %s,
                created_by = %s,
                is_active = %s,
                is_test = %s,
                last_executed = %s,
                next_execution = %s,
                target_chat_id = %s
            WHERE id = %s
        ''', (
            task_data.get('template_id'),
            task_data.get('template_name'),
            task_data.get('template_text'),
            task_data.get('template_image'),
            task_data.get('group_name'),
            task_data.get('time'),
            days_json,
            task_data.get('frequency'),
            task_data.get('created_by'),
            task_data.get('is_active', True),
            task_data.get('is_test', False),
            task_data.get('last_executed'),
            task_data.get('next_execution'),
            task_data.get('target_chat_id'),
            task_id
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Задача {task_id} обновлена в базе данных")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка обновления задачи: {e}")
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        return False

def delete_task_from_db(task_id):
    """Удаляет задачу из базы данных"""
    print(f"🗑️ Попытка удаления задачи {task_id}")
    
    conn = db.get_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM tasks WHERE id = %s', (task_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Задача {task_id} удалена из базы данных")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка удаления задачи: {e}")
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        return False

def get_active_tasks():
    """Возвращает только активные задачи"""
    all_tasks = load_tasks_from_db()
    active_tasks = {}
    
    for task_id, task in all_tasks.items():
        if task.get('is_active', True):
            active_tasks[task_id] = task
    
    return active_tasks

def get_test_tasks():
    """Возвращает тестовые задачи"""
    all_tasks = load_tasks_from_db()
    test_tasks = {}
    
    for task_id, task in all_tasks.items():
        if task.get('is_test', False):
            test_tasks[task_id] = task
    
    return test_tasks
