# -*- coding: utf-8 -*-
import json
import os
import logging
from datetime import datetime, timedelta
import pytz

# ... (остальной код остается таким же)

def get_group_templates(group_id):
    """Получить все шаблоны для конкретной группы"""
    templates_data = load_templates()
    group_templates = {}
    
    for template_id, template in templates_data.get("templates", {}).items():
        if template.get('group') == group_id:
            group_templates[template_id] = template
    
    return group_templates

def get_subgroup_templates(group_id, subgroup_id):
    """Получить шаблоны для конкретной подгруппы"""
    templates_data = load_templates()
    subgroup_templates = {}
    
    for template_id, template in templates_data.get("templates", {}).items():
        if (template.get('group') == group_id and 
            template.get('subgroup') == subgroup_id):
            subgroup_templates[template_id] = template
    
    return subgroup_templates

def add_template(template_id, template_data):
    """Добавить новый шаблон в базу данных"""
    templates_data = load_templates()
    
    # Добавляем метаданные
    template_data['template_id'] = template_id
    template_data['created_at'] = datetime.now().isoformat()
    template_data['created_by'] = template_data.get('created_by', 'unknown')
    
    templates_data["templates"][template_id] = template_data
    return save_templates(templates_data)

def update_template(template_id, template_data):
    """Обновить существующий шаблон"""
    templates_data = load_templates()
    
    if template_id in templates_data["templates"]:
        # Сохраняем некоторые метаданные
        original_data = templates_data["templates"][template_id]
        template_data['template_id'] = template_id
        template_data['created_at'] = original_data.get('created_at')
        template_data['updated_at'] = datetime.now().isoformat()
        template_data['created_by'] = original_data.get('created_by')
        
        templates_data["templates"][template_id] = template_data
        return save_templates(templates_data)
    return False

def remove_template(template_id):
    """Удалить шаблон из базы данных"""
    templates_data = load_templates()
    
    if template_id in templates_data["templates"]:
        # Удаляем связанное изображение, если оно существует
        template = templates_data["templates"][template_id]
        if template.get("image") and os.path.exists(template["image"]):
            try:
                os.remove(template["image"])
                logging.info(f"🗑️ Удалено изображение шаблона: {template['image']}")
            except Exception as e:
                logging.error(f"❌ Ошибка при удалении изображения: {e}")
        
        del templates_data["templates"][template_id]
        return save_templates(templates_data)
    return False

def add_subgroup(group_id, subgroup_id, subgroup_name):
    """Добавить подгруппу в существующую группу"""
    groups_data = load_groups()
    
    if group_id in groups_data["groups"]:
        if 'subgroups' not in groups_data["groups"][group_id]:
            groups_data["groups"][group_id]['subgroups'] = {}
        
        groups_data["groups"][group_id]['subgroups'][subgroup_id] = subgroup_name
        return save_groups(groups_data)
    return False

def remove_subgroup(group_id, subgroup_id):
    """Удалить подгруппу из группы"""
    groups_data = load_groups()
    
    if (group_id in groups_data["groups"] and 
        subgroup_id in groups_data["groups"][group_id].get('subgroups', {})):
        
        # Удаляем все шаблоны в этой подгруппе
        templates_data = load_templates()
        templates_to_remove = []
        
        for template_id, template in templates_data.get("templates", {}).items():
            if (template.get('group') == group_id and 
                template.get('subgroup') == subgroup_id):
                templates_to_remove.append(template_id)
        
        for template_id in templates_to_remove:
            remove_template(template_id)
        
        # Удаляем подгруппу
        del groups_data["groups"][group_id]['subgroups'][subgroup_id]
        return save_groups(groups_data)
    return False

# =============================================================================
# USER-GROUP MANAGEMENT FUNCTIONS
# =============================================================================

def load_user_groups():
    """Load user-group mappings from JSON file"""
    try:
        with open(USER_GROUPS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure the structure is correct
            if "user_groups" not in data:
                data = {"user_groups": {}}
            return data
    except Exception as e:
        logging.error(f"❌ Error loading user_groups: {e}")
        return {"user_groups": {}}

def save_user_groups(user_groups_data):
    """Save user-group mappings to JSON file"""
    try:
        # Ensure we have the correct structure
        if "user_groups" not in user_groups_data:
            user_groups_data = {"user_groups": user_groups_data}
            
        with open(USER_GROUPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_groups_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"❌ Error saving user_groups: {e}")
        return False

def add_user_to_group(user_id, group_id):
    """Add user to template group"""
    user_groups_data = load_user_groups()
    user_id_str = str(user_id)
    
    if "user_groups" not in user_groups_data:
        user_groups_data["user_groups"] = {}
    
    if user_id_str not in user_groups_data["user_groups"]:
        user_groups_data["user_groups"][user_id_str] = []
    
    if group_id not in user_groups_data["user_groups"][user_id_str]:
        user_groups_data["user_groups"][user_id_str].append(group_id)
    
    return save_user_groups(user_groups_data)

def remove_user_from_group(user_id, group_id):
    """Remove user from template group"""
    user_groups_data = load_user_groups()
    user_id_str = str(user_id)
    
    if (user_id_str in user_groups_data.get("user_groups", {}) and 
        group_id in user_groups_data["user_groups"][user_id_str]):
        
        user_groups_data["user_groups"][user_id_str].remove(group_id)
        
        # Remove user entry if no groups left
        if not user_groups_data["user_groups"][user_id_str]:
            del user_groups_data["user_groups"][user_id_str]
        
        return save_user_groups(user_groups_data)
    return False

def remove_user_from_all_groups(user_id):
    """Remove user from all groups"""
    user_groups_data = load_user_groups()
    user_id_str = str(user_id)
    
    if user_id_str in user_groups_data.get("user_groups", {}):
        del user_groups_data["user_groups"][user_id_str]
        return save_user_groups(user_groups_data)
    return True  # Return True if user wasn't in any groups

def get_user_accessible_groups(user_id):
    """Get template groups accessible to user"""
    user_groups_data = load_user_groups()
    groups_data = load_groups()
    
    accessible_groups = {}
    user_id_str = str(user_id)
    
    # Admin has access to all groups
    if is_admin(user_id):
        return groups_data.get("groups", {})
    
    if user_id_str in user_groups_data.get("user_groups", {}):
        for group_id in user_groups_data["user_groups"][user_id_str]:
            if group_id in groups_data.get("groups", {}):
                accessible_groups[group_id] = groups_data["groups"][group_id]
    
    return accessible_groups

# =============================================================================
# USER ROLE MANAGEMENT FUNCTIONS (for backward compatibility)
# =============================================================================

def load_user_roles():
    """Load user roles from JSON file (for backward compatibility)"""
    try:
        with open(USER_ROLES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure the structure is correct
            if "user_roles" not in data:
                data = {"user_roles": {}}
            return data
    except Exception as e:
        logging.error(f"❌ Error loading user_roles: {e}")
        return {"user_roles": {}}

def save_user_roles(user_roles_data):
    """Save user roles to JSON file (for backward compatibility)"""
    try:
        # Ensure we have the correct structure
        if "user_roles" not in user_roles_data:
            user_roles_data = {"user_roles": user_roles_data}
            
        with open(USER_ROLES_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_roles_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"❌ Error saving user_roles: {e}")
        return False

def set_user_role(user_id, role):
    """Set user role (for backward compatibility)"""
    # This function updates both authorized_users and user_roles for compatibility
    user_roles_data = load_user_roles()
    if "user_roles" not in user_roles_data:
        user_roles_data["user_roles"] = {}
    
    user_roles_data["user_roles"][str(user_id)] = role
    
    # Also update authorized_users
    users_data = load_authorized_users()
    if str(user_id) in users_data.get('users', {}):
        users_data['users'][str(user_id)]['role'] = role
        save_authorized_users(users_data)
    
    return save_user_roles(user_roles_data)

def get_all_users():
    """Get all users with roles (for backward compatibility)"""
    return load_user_roles().get("user_roles", {})

# =============================================================================
# TELEGRAM GROUP MANAGEMENT FUNCTIONS
# =============================================================================

def load_telegram_groups():
    """Load Telegram groups where bot is present"""
    try:
        with open(TELEGRAM_GROUPS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure the structure is correct
            if "telegram_groups" not in data:
                data = {"telegram_groups": {}}
            return data
    except Exception as e:
        logging.error(f"❌ Error loading telegram groups: {e}")
        return {"telegram_groups": {}}

def save_telegram_groups(groups_data):
    """Save Telegram groups to JSON file"""
    try:
        # Ensure we have the correct structure
        if "telegram_groups" not in groups_data:
            groups_data = {"telegram_groups": groups_data}
            
        with open(TELEGRAM_GROUPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(groups_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"❌ Error saving telegram groups: {e}")
        return False

def add_telegram_group(group_id, group_data):
    """Add Telegram group to database"""
    telegram_groups_data = load_telegram_groups()
    
    # Add metadata
    group_data['id'] = str(group_id)
    group_data['added_at'] = datetime.now().isoformat()
    group_data['last_checked'] = datetime.now().isoformat()
    
    telegram_groups_data["telegram_groups"][str(group_id)] = group_data
    return save_telegram_groups(telegram_groups_data)

def remove_telegram_group(group_id):
    """Remove Telegram group from database"""
    telegram_groups_data = load_telegram_groups()
    
    if str(group_id) in telegram_groups_data["telegram_groups"]:
        del telegram_groups_data["telegram_groups"][str(group_id)]
        return save_telegram_groups(telegram_groups_data)
    return False

def get_user_telegram_groups(user_id):
    """Get Telegram groups where both bot and user are present"""
    telegram_groups_data = load_telegram_groups()
    
    # This function would ideally check Telegram API for user membership
    # For now, we return all groups where bot is present
    # In production, this should be enhanced with actual membership checks
    
    user_groups = {}
    for group_id, group_info in telegram_groups_data.get("telegram_groups", {}).items():
        user_groups[group_id] = group_info
    
    return user_groups

def update_telegram_group_info(group_id, group_info):
    """Update Telegram group information"""
    telegram_groups_data = load_telegram_groups()
    
    if str(group_id) in telegram_groups_data["telegram_groups"]:
        # Update existing info but preserve some fields
        existing_data = telegram_groups_data["telegram_groups"][str(group_id)]
        group_info['id'] = existing_data.get('id', str(group_id))
        group_info['added_at'] = existing_data.get('added_at', datetime.now().isoformat())
        group_info['last_checked'] = datetime.now().isoformat()
        
        telegram_groups_data["telegram_groups"][str(group_id)] = group_info
        return save_telegram_groups(telegram_groups_data)
    return False

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_all_groups():
    """Get all template groups"""
    return load_groups().get("groups", {})

def get_group_subgroups(group_id):
    """Get all subgroups for a group"""
    groups_data = load_groups()
    if group_id in groups_data.get("groups", {}):
        return groups_data["groups"][group_id].get("subgroups", {})
    return {}

def user_has_group_access(user_id, group_id):
    """Check if user has access to specific group"""
    accessible_groups = get_user_accessible_groups(user_id)
    return group_id in accessible_groups

def get_task_by_id(task_id):
    """Get specific task by ID"""
    tasks_data = load_tasks()
    return tasks_data.get("tasks", {}).get(task_id)

def get_template_by_id(template_id):
    """Get specific template by ID"""
    templates_data = load_templates()
    return templates_data.get("templates", {}).get(template_id)

def get_telegram_group_by_id(group_id):
    """Get specific Telegram group by ID"""
    telegram_groups_data = load_telegram_groups()
    return telegram_groups_data.get("telegram_groups", {}).get(str(group_id))

def ensure_admin_user():
    """Гарантировать, что пользователь 812934047 является администратором"""
    try:
        users_data = load_authorized_users()
        admin_id = 812934047
        admin_id_str = str(admin_id)
        
        # Если администратор не установлен, устанавливаем
        if users_data.get('admin_id') != admin_id:
            print(f"🔄 Устанавливаем администратора: {admin_id}")
            users_data['admin_id'] = admin_id
            save_authorized_users(users_data)
        
        # Если пользователь администратора не существует, создаем
        if admin_id_str not in users_data.get('users', {}):
            print(f"🔄 Создаем пользователя администратора: {admin_id}")
            users_data['users'][admin_id_str] = {
                "name": "Никита",
                "role": "admin",
                "groups": ["hongqi_476", "matiz_476"]
            }
            save_authorized_users(users_data)
        
        # Если пользователь существует, но не администратор - исправляем
        elif users_data['users'][admin_id_str].get('role') != 'admin':
            print(f"🔄 Исправляем роль пользователя {admin_id} на администратора")
            users_data['users'][admin_id_str]['role'] = 'admin'
            save_authorized_users(users_data)
            
        print(f"✅ Администратор {admin_id} настроен корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при настройке администратора: {e}")
        return False
        # Initialize database when module is imported
init_database()
ensure_admin_user()  # Добавьте эту строку
