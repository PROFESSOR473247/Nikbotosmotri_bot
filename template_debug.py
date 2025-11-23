"""
Отладочные функции для шаблонов
"""

from database import db

def debug_delete_template(template_id):
    """Детальная отладка удаления шаблона"""
    print(f"🔍 ДЕТАЛЬНАЯ ОТЛАДКА УДАЛЕНИЯ ШАБЛОНА {template_id}")
    
    try:
        # 1. Проверяем подключение к БД
        print("1. Проверка подключения к базе данных...")
        conn = db.get_connection()
        if not conn:
            print("❌ Не удалось подключиться к базе данных")
            return False
        print("✅ Подключение к БД успешно")
        
        # 2. Проверяем существование шаблона в БД
        print("2. Проверка существования шаблона в БД...")
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM templates WHERE id = %s', (template_id,))
        template_row = cursor.fetchone()
        
        if not template_row:
            print(f"❌ Шаблон {template_id} не найден в базе данных")
            cursor.close()
            conn.close()
            return False
        
        template_name = template_row[1]
        print(f"✅ Шаблон найден: ID={template_id}, Name={template_name}")
        
        # 3. Пробуем удалить
        print("3. Попытка удаления шаблона...")
        cursor.execute('DELETE FROM templates WHERE id = %s', (template_id,))
        deleted_count = cursor.rowcount
        
        if deleted_count > 0:
            print(f"✅ Удалено записей: {deleted_count}")
            conn.commit()
            result = True
        else:
            print("❌ Не удалось удалить запись (rowcount = 0)")
            conn.rollback()
            result = False
        
        cursor.close()
        conn.close()
        return result
        
    except Exception as e:
        print(f"💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

def debug_list_all_templates():
    """Показывает все шаблоны в базе данных"""
    print("📋 ВСЕ ШАБЛОНЫ В БАЗЕ ДАННЫХ:")
    
    try:
        conn = db.get_connection()
        if not conn:
            print("❌ Не удалось подключиться к базе данных")
            return
        
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, group_name FROM templates ORDER BY created_at DESC')
        templates = cursor.fetchall()
        
        if not templates:
            print("📭 В базе данных нет шаблонов")
        else:
            for i, (template_id, name, group_name) in enumerate(templates, 1):
                print(f"{i}. ID: {template_id}, Name: {name}, Group: {group_name}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка получения списка шаблонов: {e}")
