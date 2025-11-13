import json
import os
from user_chat_manager import user_chat_manager

def is_authorized(user_id):
    """Проверяет, авторизован ли пользователь"""
    # В режиме открытого доступа все пользователи авторизованы
    from config import REQUIRE_AUTHORIZATION
    if not REQUIRE_AUTHORIZATION:
        return True
    
    # Проверяем в базе данных
    users = user_chat_manager.get_all_users()
    user_ids = [user['user_id'] for user in users if user['is_active']]
    
    return user_id in user_ids

def is_admin(user_id):
    """Проверяет, является ли пользователь администратором"""
    users = user_chat_manager.get_all_users()
    for user in users:
        if user['user_id'] == user_id and user['role'] == 'admin':
            return True
    return False

def get_user_access_groups(user_id):
    """Возвращает группы шаблонов, к которым у пользователя есть доступ"""
    return user_chat_manager.get_user_template_group_access(user_id)

def get_user_access_chats(user_id):
    """Возвращает Telegram чаты, к которым у пользователя есть доступ"""
    return user_chat_manager.get_user_chat_access(user_id)

# Добавляем алиас для обратной совместимости
get_user_groups = get_user_access_groups