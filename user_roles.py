# -*- coding: utf-8 -*-
"""
Управление ролями пользователей
"""

USER_ROLES = {
    "admin": {
        "name": "👑 Администратор",
        "level": 100,
        "permissions": ["all"]
    },
    "руководитель": {
        "name": "💼 Руководитель", 
        "level": 50,
        "permissions": ["tasks", "templates", "groups_limited"]
    },
    "водитель": {
        "name": "🚗 Водитель",
        "level": 10,
        "permissions": ["tasks_view", "templates_view"]
    },
    "гость": {
        "name": "👤 Гость",
        "level": 0,
        "permissions": ["basic"]
    }
}

def get_role_name(role_key):
    """Получить отображаемое название роли"""
    return USER_ROLES.get(role_key, {}).get("name", "👤 Неизвестно")

def get_role_level(role_key):
    """Получить уровень доступа роли"""
    return USER_ROLES.get(role_key, {}).get("level", 0)

def has_permission(role_key, permission):
    """Проверить наличие разрешения у роли"""
    if role_key == "admin":
        return True
    
    role_data = USER_ROLES.get(role_key, {})
    permissions = role_data.get("permissions", [])
    
    return permission in permissions

def get_all_roles():
    """Получить все доступные роли"""
    return USER_ROLES

def can_manage_users(role_key):
    """Может ли управлять пользователями"""
    return role_key == "admin"

def can_manage_groups(role_key):
    """Может ли управлять группами"""
    return role_key in ["admin", "руководитель"]

def can_create_templates(role_key):
    """Может ли создавать шаблоны"""
    return role_key in ["admin", "руководитель"]

def get_role_key_by_name(role_name):
    """Получить ключ роли по отображаемому имени"""
    for key, data in USER_ROLES.items():
        if data["name"] == role_name:
            return key
    return "гость"
