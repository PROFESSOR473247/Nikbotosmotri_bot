import json
import os
import logging
from datetime import datetime, timedelta
import pytz

# Files for data storage
TASKS_FILE = 'active_tasks.json'
GROUPS_FILE = 'bot_groups.json'
USER_GROUPS_FILE = 'user_groups.json'
TEMPLATES_FILE = 'templates.json'
USER_ROLES_FILE = 'user_roles.json'
TELEGRAM_GROUPS_FILE = 'telegram_groups.json'
AUTHORIZED_USERS_FILE = 'authorized_users.json'

def init_database():
    """Initialize all database files with default data"""
    files_config = {
        TASKS_FILE: {"tasks": {}},
        GROUPS_FILE: {
            "groups": {
                "hongqi_476": {
                    "id": "hongqi_476",
                    "name": "Hongqi 476 Group",
                    "subgroups": {
                        "inspections": "Осмотры",
                        "payments": "Платежи",
                        "cleaning": "Чистка"
                    },
                    "created_at": datetime.now().isoformat()
                },
                "matiz_476": {
                    "id": "matiz_476", 
                    "name": "Matiz 476 Group",
                    "subgroups": {
                        "inspections": "Осмотры",
                        "payments": "Платежи", 
                        "cleaning": "Чистка"
                    },
                    "created_at": datetime.now().isoformat()
                }
            }
        },
        USER_GROUPS_FILE: {"user_groups": {}},
        TEMPLATES_FILE: {"templates": {}},
        USER_ROLES_FILE: {"user_roles": {}},
        TELEGRAM_GROUPS_FILE: {"telegram_groups": {}},
        AUTHORIZED_USERS_FILE: {
            "users": {
                "812934047": {
                    "name": "Никита",
                    "role": "admin",
                    "groups": ["hongqi_476", "matiz_476"]
                }
            },
            "admin_id": 812934047
        }
    }
    
    for file, default_data in files_config.items():
        if not os.path.exists(file):
            with open(file, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)
            print(f"✅ Created file: {file}")
        else:
            # If file exists but is empty, initialize with default data
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        with open(file, 'w', encoding='utf-8') as f_write:
                            json.dump(default_data, f_write, ensure_ascii=False, indent=2)
                        print(f"🔄 Reinitialized empty file: {file}")
            except:
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, ensure_ascii=False, indent=2)
                print(f"🔄 Recreated corrupted file: {file}")

# =============================================================================
# AUTHORIZED USERS MANAGEMENT (заменяет authorized_users.py)
# =============================================================================

def load_authorized_users():
    """Load authorized users from JSON file"""
    try:
        with open(AUTHORIZED_USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure the structure is correct
            if "users" not in data:
                data = {"users": {}, "admin_id": None}
            return data
    except Exception as e:
        logging.error(f"❌ Error loading authorized users: {e}")
        return {"users": {}, "admin_id": None}

def save_authorized_users(users_data):
    """Save authorized users to JSON file"""
    try:
        with open(AUTHORIZED_USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logging.error(f"❌ Error saving authorized users: {e}")
        return False

def is_authorized(user_id):
    """Check if user is authorized"""
    users_data = load_authorized_users()
    return str(user_id) in users_data.get('users', {})

def is_admin(user_id):
    """Check if user is administrator"""
    users_data = load_authorized_users()
    return user_id == users_data.get('admin_id')

def get_user_role(user_id):
    """Get user role"""
    users_data = load_authorized_users()
    user_data = users_data.get('users', {}).get(str(user_id), {})
    return user_data.get('role', 'гость')

def add_authorized_user(user_id, username, role='гость', groups=None):
    """Add authorized user"""
    users_data = load_authorized_users()
    
    if str(user_id) in users_data.get('users', {}):
        return False, "User already exists"
    
    users_data['users'][str(user_id)] = {
        "name": username,
        "role": role,
        "groups": groups or []
    }
    
    # Also add to user_groups system for backward compatibility
    if groups:
        for group_id in groups:
            add_user_to_group(user_id, group_id)
    
    success = save_authorized_users(users_data)
    
    if success:
        return True, f"User {username} (ID: {user_id}) added as {role}"
    else:
        return False, "Error saving user"

def remove_authorized_user(user_id):
    """Remove authorized user"""
    users_data = load_authorized_users()
    user_id_str = str(user_id)
    
    if user_id_str not in users_data.get('users', {}):
        return False, "User not found"
    
    if user_id == users_data.get('admin_id'):
        return False, "Cannot remove administrator"
    
    username = users_data['users'][user_id_str]['name']
    del users_data['users'][user_id_str]
    
    success = save_authorized_users(users_data)
    
    if success:
        # Also remove from user_groups
        remove_user_from_all_groups(user_id)
        return True, f"User {username} (ID: {user_id}) removed"
    else:
        return False, "Error removing user"

def get_authorized_users_list():
    """Return list of all authorized users"""
    users_data = load_authorized_users()
    return users_data.get('users', {})

def get_admin_id():
    """Return administrator ID"""
    users_data = load_authorized_users()
    return users_data.get('admin_id')

# =============================================================================
# TASK MANAGEMENT FUNCTIONS
# =============================================================================

def load_tasks():
    """Load active tasks from JSON file"""
    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure the structure is correct
            if "tasks" not in data:
                data = {"tasks": {}}
            return data
    except Exception as e:
        logging.error(f"❌ Error loading tasks: {e}")
        return {"tasks": {}}

def save_tasks(tasks_data):
    """Save tasks to JSON file"""
    try:
        # Ensure we have the correct structure
        if "tasks" not in tasks_data:
            tasks_data = {"tasks": tasks_data}
            
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tasks_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"❌ Error saving tasks: {e}")
        return False

def add_task(task_id, task_data):
    """Add new task to database"""
    tasks_data = load_tasks()
    
    # Add metadata
    task_data['task_id'] = task_id
    task_data['created_at'] = datetime.now().isoformat()
    task_data['created_by'] = task_data.get('created_by', 'unknown')
    task_data['active'] = task_data.get('active', True)
    task_data['last_executed'] = None
    task_data['execution_count'] = 0
    
    tasks_data["tasks"][task_id] = task_data
    return save_tasks(tasks_data)

def remove_task(task_id):
    """Remove task from database"""
    tasks_data = load_tasks()
    if task_id in tasks_data["tasks"]:
        del tasks_data["tasks"][task_id]
        return save_tasks(tasks_data)
    return False

def deactivate_task(task_id):
    """Deactivate task (keep in database but mark as inactive)"""
    tasks_data = load_tasks()
    if task_id in tasks_data["tasks"]:
        tasks_data["tasks"][task_id]['active'] = False
        tasks_data["tasks"][task_id]['deactivated_at'] = datetime.now().isoformat()
        return save_tasks(tasks_data)
    return False

def get_active_tasks():
    """Get all active tasks"""
    tasks_data = load_tasks()
    active_tasks = {}
    
    for task_id, task_data in tasks_data.get("tasks", {}).items():
        if task_data.get('active', True):
            active_tasks[task_id] = task_data
    
    return active_tasks

def get_user_tasks(user_id):
    """Get tasks accessible to specific user"""
    user_groups = get_user_accessible_groups(user_id)
    user_group_ids = list(user_groups.keys())
    
    tasks_data = load_tasks()
    user_tasks = {}
    
    for task_id, task_data in tasks_data.get("tasks", {}).items():
        if (task_data.get('active', True) and 
            task_data.get('template_group') in user_group_ids):
            user_tasks[task_id] = task_data
    
    return user_tasks

# =============================================================================
# TEMPLATE MANAGEMENT FUNCTIONS
# =============================================================================

def load_templates():
    """Load templates from JSON file"""
    try:
        with open(TEMPLATES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure the structure is correct
            if "templates" not in data:
                data = {"templates": {}}
            return data
    except Exception as e:
        logging.error(f"❌ Error loading templates: {e}")
        return {"templates": {}}

def save_templates(templates_data):
    """Save templates to JSON file"""
    try:
        # Ensure we have the correct structure
        if "templates" not in templates_data:
            templates_data = {"templates": templates_data}
            
        with open(TEMPLATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(templates_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"❌ Error saving templates: {e}")
        return False

def add_template(template_id, template_data):
    """Add new template to database"""
    templates_data = load_templates()
    
    # Add metadata
    template_data['template_id'] = template_id
    template_data['created_at'] = datetime.now().isoformat()
    template_data['created_by'] = template_data.get('created_by', 'unknown')
    
    templates_data["templates"][template_id] = template_data
    return save_templates(templates_data)

def update_template(template_id, template_data):
    """Update existing template"""
    templates_data = load_templates()
    
    if template_id in templates_data["templates"]:
        # Preserve some metadata
        template_data['template_id'] = template_id
        template_data['created_at'] = templates_data["templates"][template_id].get('created_at')
        template_data['updated_at'] = datetime.now().isoformat()
        template_data['created_by'] = templates_data["templates"][template_id].get('created_by')
        
        templates_data["templates"][template_id] = template_data
        return save_templates(templates_data)
    return False

def remove_template(template_id):
    """Remove template from database"""
    templates_data = load_templates()
    if template_id in templates_data["templates"]:
        # Remove associated image if exists
        template = templates_data["templates"][template_id]
        if "image" in template and template["image"] and os.path.exists(template["image"]):
            try:
                os.remove(template["image"])
                logging.info(f"🗑️ Removed template image: {template['image']}")
            except Exception as e:
                logging.error(f"❌ Error removing template image: {e}")
        
        del templates_data["templates"][template_id]
        return save_templates(templates_data)
    return False

def get_group_templates(group_id):
    """Get all templates for a specific group"""
    templates_data = load_templates()
    group_templates = {}
    
    for template_id, template in templates_data.get("templates", {}).items():
        if template.get('group') == group_id:
            group_templates[template_id] = template
    
    return group_templates

def get_subgroup_templates(group_id, subgroup_id):
    """Get templates for a specific subgroup"""
    templates_data = load_templates()
    subgroup_templates = {}
    
    for template_id, template in templates_data.get("templates", {}).items():
        if (template.get('group') == group_id and 
            template.get('subgroup') == subgroup_id):
            subgroup_templates[template_id] = template
    
    return subgroup_templates

# =============================================================================
# GROUP MANAGEMENT FUNCTIONS (Template Groups)
# =============================================================================

def load_groups():
    """Load template groups from JSON file"""
    try:
        with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure the structure is correct
            if "groups" not in data:
                data = {"groups": {}}
            return data
    except Exception as e:
        logging.error(f"❌ Error loading groups: {e}")
        return {"groups": {}}

def save_groups(groups_data):
    """Save template groups to JSON file"""
    try:
        # Ensure we have the correct structure
        if "groups" not in groups_data:
            groups_data = {"groups": groups_data}
            
        with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(groups_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"❌ Error saving groups: {e}")
        return False

def add_group(group_id, group_data):
    """Add new template group"""
    groups_data = load_groups()
    
    # Add metadata
    group_data['id'] = group_id
    group_data['created_at'] = datetime.now().isoformat()
    group_data['subgroups'] = group_data.get('subgroups', {})
    
    groups_data["groups"][group_id] = group_data
    return save_groups(groups_data)

def add_subgroup(group_id, subgroup_id, subgroup_name):
    """Add subgroup to existing group"""
    groups_data = load_groups()
    
    if group_id in groups_data["groups"]:
        if 'subgroups' not in groups_data["groups"][group_id]:
            groups_data["groups"][group_id]['subgroups'] = {}
        
        groups_data["groups"][group_id]['subgroups'][subgroup_id] = subgroup_name
        return save_groups(groups_data)
    return False

def remove_group(group_id):
    """Remove template group and all its templates"""
    groups_data = load_groups()
    
    if group_id in groups_data["groups"]:
        # Remove all templates in this group
        templates_data = load_templates()
        templates_to_remove = []
        
        for template_id, template in templates_data.get("templates", {}).items():
            if template.get('group') == group_id:
                templates_to_remove.append(template_id)
        
        for template_id in templates_to_remove:
            remove_template(template_id)
        
        # Remove the group
        del groups_data["groups"][group_id]
        return save_groups(groups_data)
    return False

def remove_subgroup(group_id, subgroup_id):
    """Remove subgroup and all its templates"""
    groups_data = load_groups()
    
    if (group_id in groups_data["groups"] and 
        subgroup_id in groups_data["groups"][group_id].get('subgroups', {})):
        
        # Remove all templates in this subgroup
        templates_data = load_templates()
        templates_to_remove = []
        
        for template_id, template in templates_data.get("templates", {}).items():
            if (template.get('group') == group_id and 
                template.get('subgroup') == subgroup_id):
                templates_to_remove.append(template_id)
        
        for template_id in templates_to_remove:
            remove_template(template_id)
        
        # Remove the subgroup
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

# Initialize database when module is imported
init_database()
