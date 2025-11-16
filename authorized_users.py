"""
Модуль для управления авторизованными пользователями и их доступом к группам
"""

from database import db
from auth_manager import auth_manager

def is_admin(user_id):
    """Проверяет, является ли пользователь администратором"""
    return auth_manager.is_admin(user_id)

def get_user_access_groups(user_id):
    """Возвращает список ID групп, к которым у пользователя есть доступ"""
    try:
        user_groups = db.get_user_template_group_access(user_id)
        return [group['id'] for group in user_groups]
    except Exception as e:
        print(f"❌ Ошибка получения групп доступа пользователя {user_id}: {e}")
        return []

def get_user_accessible_chats(user_id):
    """Возвращает список чатов, к которым у пользователя есть доступ"""
    try:
        user_chats = db.get_user_chat_access(user_id)
        return [chat['chat_id'] for chat in user_chats]
    except Exception as e:
        print(f"❌ Ошибка получения чатов доступа пользователя {user_id}: {e}")
        return []

def can_user_access_group(user_id, group_id):
    """Проверяет, есть ли у пользователя доступ к группе"""
    accessible_groups = get_user_access_groups(user_id)
    return group_id in accessible_groups

def can_user_access_chat(user_id, chat_id):
    """Проверяет, есть ли у пользователя доступ к чату"""
    accessible_chats = get_user_accessible_chats(user_id)
    return chat_id in accessible_chats

def get_all_authorized_users():
    """Возвращает всех авторизованных пользователей"""
    try:
        return db.get_all_users()
    except Exception as e:
        print(f"❌ Ошибка получения авторизованных пользователей: {e}")
        return []

def check_duplicate_user(user_id):
    """Проверяет, существует ли пользователь с таким ID"""
    users = get_all_authorized_users()
    for user in users:
        if user['user_id'] == user_id:
            return True
    return False

def get_user_role(user_id):
    """Возвращает роль пользователя"""
    return auth_manager.get_user_role(user_id)