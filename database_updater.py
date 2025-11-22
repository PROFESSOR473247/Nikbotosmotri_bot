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
        
        # Проверяем существование новых столбцов в таблице tasks
        new_columns = [
            'schedule_type',
            'times', 
            'week_days',
            'month_days',
            'frequency'
        ]
        
        for column in new_columns:
            cursor.execute('''
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'tasks' AND column_name = %s
            ''', (column,))
            
            if not cursor.fetchone():
                print(f"📝 Добавляем столбец {column} в таблицу tasks...")
                
                if column == 'schedule_type':
                    cursor.execute('''
                        ALTER TABLE tasks 
                        ADD COLUMN schedule_type TEXT CHECK (schedule_type IN ('week_days', 'month_days'))
                    ''')
                elif column == 'times':
                    cursor.execute('''
                        ALTER TABLE tasks 
                        ADD COLUMN times JSONB DEFAULT '[]'::jsonb
                    ''')
                elif column == 'week_days':
                    cursor.execute('''
                        ALTER TABLE tasks 
                        ADD COLUMN week_days JSONB DEFAULT '[]'::jsonb
                    ''')
                elif column == 'month_days':
                    cursor.execute('''
                        ALTER TABLE tasks 
                        ADD COLUMN month_days JSONB DEFAULT '[]'::jsonb
                    ''')
                elif column == 'frequency':
                    cursor.execute('''
                        ALTER TABLE tasks 
                        ADD COLUMN frequency TEXT DEFAULT 'weekly' CHECK (frequency IN ('weekly', 'biweekly', 'monthly'))
                    ''')
                
                print(f"✅ Столбец {column} добавлен в таблицу tasks")
            else:
                print(f"✅ Столбец {column} уже существует в таблице tasks")
        
        # Удаляем старые столбцы из таблицы templates (time, days, frequency)
        old_columns = ['time', 'days', 'frequency']
        for column in old_columns:
            cursor.execute('''
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'templates' AND column_name = %s
            ''', (column,))
            
            if cursor.fetchone():
                print(f"📝 Удаляем старый столбец {column} из таблицы templates...")
                cursor.execute(f'ALTER TABLE templates DROP COLUMN {column}')
                print(f"✅ Столбец {column} удален из таблицы templates")
            else:
                print(f"✅ Столбец {column} уже удален из таблицы templates")
        
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