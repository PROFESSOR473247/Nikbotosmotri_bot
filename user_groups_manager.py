import json
import os
from authorized_users import load_users, save_users, get_users_list
from template_manager import load_groups

def get_available_groups():
    """Возвращает список всех доступных групп"""
    groups_data = load_groups()
    return groups_data.get('groups', {})

def get_user_groups_keyboard():
    """Создает клавиатуру для выбора групп пользователя"""
    groups = get_available_groups()
    keyboard = []
    
    for group_id, group_data in groups.items():
        keyboard.append([f"🎯 {group_data['name']}"])
    
    keyboard.append(["✅ Сохранить"])
    keyboard.append(["🔙 Назад"])
    
    return keyboard

def update_user_groups_interactive(user_id, selected_groups):
    """Обновляет группы пользователя в интерактивном режиме"""
    users_data = load_users()
    user_id_str = str(user_id)
    
    if user_id_str not in users_data.get('users', {}):
        return False, "Пользователь не найден"
    
    users_data['users'][user_id_str]['groups'] = selected_groups
    success, message = save_users(users_data)
    
    return success, message

def format_user_groups_info(user_id):
    """Форматирует информацию о группах пользователя"""
    users_data = load_users()
    user_data = users_data['users'].get(str(user_id), {})
    user_groups = user_data.get('groups', [])
    
    groups_data = load_groups()
    
    if not user_groups:
        return "❌ Пользователь не состоит ни в одной группе"
    
    info = f"🎯 **Группы пользователя {user_data.get('name', '')}:**\n\n"
    
    for group_id in user_groups:
        group_name = groups_data['groups'].get(group_id, {}).get('name', group_id)
        info += f"• {group_name}\n"
    
    return info
