import os
import psycopg2
from database import db

def update_database_structure():
    """Обновляет структуру базы данных, добавляя недостающие столбцы"""
    print("🔄 Проверка и обновление структуры базы данных...")
    
    conn = db.get_connection()
    if not conn:
        print("❌ Не удалось подключиться к базе данных для обновления")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Проверяем существование столбца target_chat_id в таблице tasks
        cursor.execute('''
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'tasks' AND column_name = 'target_chat_id'
        ''')
        
        if not cursor.fetchone():
            print("📝 Добавляем столбец target_chat_id в таблицу tasks...")
            cursor.execute('''
                ALTER TABLE tasks 
                ADD COLUMN target_chat_id BIGINT
            ''')
            print("✅ Столбец target_chat_id добавлен в таблицу tasks")
        else:
            print("✅ Столбец target_chat_id уже существует в таблице tasks")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Структура базы данных обновлена")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка обновления структуры базы данных: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        return False

# Запускаем обновление при импорте
if __name__ == "__main__":
    update_database_structure()
