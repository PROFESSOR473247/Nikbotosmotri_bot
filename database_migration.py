"""
Миграция для удаления старых полей из таблицы templates
"""

from database import db

def migrate_templates_table():
    """Удаляет старые поля времени, дней и периодичности из таблицы templates"""
    print("🔄 Миграция таблицы templates...")
    
    conn = db.get_connection()
    if not conn:
        print("❌ Не удалось подключиться к базе данных для миграции")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Проверяем существование старых столбцов
        old_columns = ['time', 'days', 'frequency']
        
        for column in old_columns:
            cursor.execute('''
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'templates' AND column_name = %s
            ''', (column,))
            
            if cursor.fetchone():
                print(f"🗑️ Удаляем старый столбец {column} из таблицы templates...")
                cursor.execute(f'ALTER TABLE templates DROP COLUMN {column}')
                print(f"✅ Столбец {column} удален из таблицы templates")
            else:
                print(f"✅ Столбец {column} уже удален из таблицы templates")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Миграция таблицы templates завершена")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка миграции таблицы templates: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        return False

# Запускаем миграцию при импорте
if __name__ == "__main__":
    migrate_templates_table()
