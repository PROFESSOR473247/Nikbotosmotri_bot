#!/usr/bin/env python3
"""
Скрипт для полного сброса и создания администратора
"""
import os
import json
from database import init_database, set_user_role, save_user_roles
from authorized_users import save_users

def reset_admin():
    """Полный сброс и создание администратора"""
    print("🚀 Начинаем полный сброс системы...")
    
    # Удаляем все файлы данных
    files_to_remove = [
        'authorized_users.json',
        'active_tasks.json', 
        'bot_groups.json',
        'user_groups.json',
        'templates.json',
        'user_roles.json'
    ]
    
    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)
            print(f"🗑️ Удален файл: {file}")
    
    # Инициализируем базу данных заново
    init_database()
    print("✅ База данных переинициализирована")
    
    # Создаем администратора
    admin_id = 812934047
    admin_data = {
        "users": {
            str(admin_id): {
                "name": "Никита",
                "role": "admin",
                "groups": ["all"]
            }
        },
        "admin_id": admin_id
    }
    
    # Сохраняем в authorized_users.json
    with open('authorized_users.json', 'w', encoding='utf-8') as f:
        json.dump(admin_data, f, ensure_ascii=False, indent=4)
    print("✅ Администратор создан в authorized_users.json")
    
    # Сохраняем в user_roles.json
    user_roles_data = {"user_roles": {str(admin_id): "admin"}}
    with open('user_roles.json', 'w', encoding='utf-8') as f:
        json.dump(user_roles_data, f, ensure_ascii=False, indent=2)
    print("✅ Роль администратора установлена в user_roles.json")
    
    print("\n🎉 Сброс завершен!")
    print(f"👤 Администратор: ID {admin_id}")
    print("🔑 Роль: admin")
    print("📋 Доступ: все функции")

if __name__ == '__main__':
    reset_admin()
