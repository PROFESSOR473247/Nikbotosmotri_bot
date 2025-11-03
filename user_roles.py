# -*- coding: utf-8 -*-
"""
Управление ролями пользователей
"""

USER_ROLES = {
    "admin": {
        "name": "👑 Администратор",
        "level": 100,
        "permissions": [
            "all", "manage_users", "manage_groups", "create_templates", 
            "edit_templates", "delete_templates", "create_tasks", 
            "cancel_tasks", "test_tasks", "view_all_tasks"
        ]
    },
    "руководитель": {
        "name": "💼 Руководитель", 
        "level": 50,
        "permissions": [
            "create_templates", "edit_templates", "delete_templates", 
            "create_tasks", "cancel_tasks", "test_tasks", "view_tasks",
            "manage_groups_limited", "create_subgroups", "delete_subgroups"
        ]
    },
    "водитель": {
        "name": "🚗 Водитель",
        "level": 10,
        "permissions": [
            "view_tasks", "view_templates"
        ]
    },
    "гость": {
        "name": "👤 Гость",
        "level": 0,
        "permissions": [
            "basic"
        ]
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
    return has_permission(role_key, "manage_users")

def can_manage_groups(role_key):
    """Может ли управлять группами"""
    return has_permission(role_key, "manage_groups")

def can_manage_groups_limited(role_key):
    """Может ли управлять группами (ограниченно)"""
    return has_permission(role_key, "manage_groups_limited")

def can_create_templates(role_key):
    """Может ли создавать шаблоны"""
    return has_permission(role_key, "create_templates")

def can_edit_templates(role_key):
    """Может ли редактировать шаблоны"""
    return has_permission(role_key, "edit_templates")

def can_delete_templates(role_key):
    """Может ли удалять шаблоны"""
    return has_permission(role_key, "delete_templates")

def can_create_tasks(role_key):
    """Может ли создавать задачи"""
    return has_permission(role_key, "create_tasks")

def can_cancel_tasks(role_key):
    """Может ли отменять задачи"""
    return has_permission(role_key, "cancel_tasks")

def can_test_tasks(role_key):
    """Может ли тестировать задачи"""
    return has_permission(role_key, "test_tasks")

def can_view_tasks(role_key):
    """Может ли просматривать задачи"""
    return has_permission(role_key, "view_tasks")

def can_view_all_tasks(role_key):
    """Может ли просматривать все задачи"""
    return has_permission(role_key, "view_all_tasks")

def can_create_subgroups(role_key):
    """Может ли создавать подгруппы"""
    return has_permission(role_key, "create_subgroups")

def can_delete_subgroups(role_key):
    """Может ли удалять подгруппы"""
    return has_permission(role_key, "delete_subgroups")

def get_role_key_by_name(role_name):
    """Получить ключ роли по отображаемому имени"""
    for key, data in USER_ROLES.items():
        if data["name"] == role_name:
            return key
    return "гость"

def get_available_roles_for_assignment():
    """Получить роли, доступные для назначения"""
    return {k: v for k, v in USER_ROLES.items() if k != "admin"}
