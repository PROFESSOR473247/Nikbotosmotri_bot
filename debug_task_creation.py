"""
Отладочный скрипт для создания задачи
"""

from task_manager import create_task_from_template
from template_manager import get_template_by_name_and_group

def debug_task_creation():
    print("🔍 ОТЛАДКА СОЗДАНИЯ ЗАДАЧИ")
    
    # Имитируем данные, которые приходят из бота
    template_name = "Тестовый шаблон для размещения задачи"
    group_id = "hongqi"  # ID группы Hongqi
    
    print(f"📝 Поиск шаблона: {template_name} в группе {group_id}")
    
    # Ищем шаблон
    template_id, template_data = get_template_by_name_and_group(template_name, group_id)
    
    if not template_data:
        print("❌ Шаблон не найден")
        return
    
    print(f"✅ Шаблон найден: {template_data.get('name')}")
    print(f"📊 Данные шаблона: {template_data}")
    
    # Пробуем создать задачу
    print("🔄 Попытка создания задачи...")
    
    success, task_id = create_task_from_template(
        template_data,
        created_by=812934047,  # Ваш user_id
        target_chat_id=-1002123456789,  # Тестовый chat_id
        is_test=False
    )
    
    if success:
        print(f"✅ Задача создана успешно! ID: {task_id}")
    else:
        print("❌ Ошибка создания задачи")
        
    return success, task_id

if __name__ == "__main__":
    debug_task_creation()
