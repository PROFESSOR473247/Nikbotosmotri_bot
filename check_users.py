#!/usr/bin/env python3
"""
Скрипт для проверки и исправления структуры authorized_users.json
"""
import json
import os

def check_and_fix_users():
    """Проверить и исправить структуру authorized_users.json"""
    filename = 'authorized_users.json'
    
    if not os.path.exists(filename):
        print("❌ Файл authorized_users.json не существует")
        return False
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("📊 Текущая структура authorized_users.json:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Проверяем структуру
        needs_fix = False
        
        if 'users' not in data:
            print("❌ Отсутствует ключ 'users'")
            data['users'] = {}
            needs_fix = True
        
        if 'admin_id' not in data:
            print("❌ Отсутствует ключ 'admin_id'")
            data['admin_id'] = 812934047
            needs_fix = True
        
        # Проверяем, что users - это словарь
        if not isinstance(data['users'], dict):
            print(f"❌ 'users' не является словарем: {type(data['users'])}")
            data['users'] = {}
            needs_fix = True
        
        # Проверяем наличие администратора
        if '812934047' not in data['users']:
            print("❌ Отсутствует администратор")
            data['users']['812934047'] = {
                "name": "Никита",
                "role": "admin",
                "groups": ["hongqi_476", "matiz_476"]
            }
            needs_fix = True
        
        # Проверяем структуру каждого пользователя
        for user_id, user_data in data['users'].items():
            if not isinstance(user_data, dict):
                print(f"❌ Данные пользователя {user_id} не являются словарем: {type(user_data)}")
                data['users'][user_id] = {
                    "name": f"User_{user_id}",
                    "role": "гость",
                    "groups": []
                }
                needs_fix = True
            else:
                # Проверяем обязательные поля
                if 'name' not in user_data:
                    print(f"❌ У пользователя {user_id} отсутствует поле 'name'")
                    user_data['name'] = f"User_{user_id}"
                    needs_fix = True
                
                if 'role' not in user_data:
                    print(f"❌ У пользователя {user_id} отсутствует поле 'role'")
                    user_data['role'] = "гость"
                    needs_fix = True
                
                if 'groups' not in user_data:
                    print(f"❌ У пользователя {user_id} отсутствует поле 'groups'")
                    user_data['groups'] = []
                    needs_fix = True
        
        if needs_fix:
            print("🔄 Исправляем структуру...")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print("✅ Структура исправлена")
        else:
            print("✅ Структура корректна")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при проверке файла: {e}")
        return False

if __name__ == '__main__':
    check_and_fix_users()
