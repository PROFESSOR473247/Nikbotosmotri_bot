"""
Тестовый скрипт для проверки создания задачи
"""

import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from debug_task_creation import debug_task_creation

if __name__ == "__main__":
    print("🧪 ТЕСТИРОВАНИЕ СОЗДАНИЯ ЗАДАЧИ")
    success, task_id = debug_task_creation()
    
    if success:
        print("🎉 ТЕСТ ПРОЙДЕН УСПЕШНО!")
    else:
        print("💥 ТЕСТ ПРОВАЛЕН!")
