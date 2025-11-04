import json
import os

USERS_FILE = 'authorized_users.json'

def load_users():
    """Загружает список пользователей из файла"""
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Создаем файл с администратором по умолчанию
            default_users = {
                "users": {
                    "812934047": "Никита"  # Ваш user_id
                },
                "admin_id": 812934047  # Ваш user_id
            }
            save_users(default_users)
            return default_users
    except Exception as e:
        print(f"❌ Ошибка загрузки пользователей: {e}")
        return {"users": {}, "admin_id": None}

def save_users(users_data):
    """Сохраняет список пользователей в файл"""
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=4)
        return True, "Пользователи сохранены"
    except Exception as e:
        print(f"❌ Ошибка сохранения пользователей: {e}")
        return False, f"Ошибка сохранения: {e}"

def is_authorized(user_id):
    """Проверяет, авторизован ли пользователь"""
    users_data = load_users()
    return str(user_id) in users_data.get('users', {})

def is_admin(user_id):
    """Проверяет, является ли пользователь администратором"""
    users_data = load_users()
    return user_id == users_data.get('admin_id')

def add_user(user_id, username):
    """Добавляет пользователя"""
    users_data = load_users()
    
    if str(user_id) in users_data.get('users', {}):
        return False, "Пользователь уже существует"
    
    users_data['users'][str(user_id)] = username
    success, message = save_users(users_data)
    
    if success:
        return True, f"Пользователь {username} (ID: {user_id}) добавлен"
    else:
        return False, message

def remove_user(user_id):
    """Удаляет пользователя"""
    users_data = load_users()
    user_id_str = str(user_id)
    
    if user_id_str not in users_data.get('users', {}):
        return False, "Пользователь не найден"
    
    if user_id == users_data.get('admin_id'):
        return False, "Нельзя удалить администратора"
    
    username = users_data['users'][user_id_str]
    del users_data['users'][user_id_str]
    
    success, message = save_users(users_data)
    
    if success:
        return True, f"Пользователь {username} (ID: {user_id}) удален"
    else:
        return False, message

def get_users_list():
    """Возвращает список всех пользователей"""
    users_data = load_users()
    return users_data.get('users', {})

def get_admin_id():
    """Возвращает ID администратора"""
    users_data = load_users()
    return users_data.get('admin_id')
