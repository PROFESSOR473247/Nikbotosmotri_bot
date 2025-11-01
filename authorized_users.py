import json
import os
from database import add_user_to_group, get_user_role, set_user_role, get_all_users

USERS_FILE = 'authorized_users.json'

def load_users():
    """Load user list from file"""
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Create file with default administrator
            default_users = {
                "users": {
                    "812934047": {
                        "name": "Nikita",
                        "role": "admin",
                        "groups": []  # Admin has access to all groups
                    }
                },
                "admin_id": 812934047
            }
            save_users(default_users)
            return default_users
    except Exception as e:
        print(f"Error loading users: {e}")
        return {"users": {}, "admin_id": None}

def save_users(users_data):
    """Save user list to file"""
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=4)
        return True, "Users saved"
    except Exception as e:
        print(f"Error saving users: {e}")
        return False, f"Save error: {e}"

def is_authorized(user_id):
    """Check if user is authorized"""
    users_data = load_users()
    return str(user_id) in users_data.get('users', {})

def is_admin(user_id):
    """Check if user is administrator"""
    users_data = load_users()
    return user_id == users_data.get('admin_id')

def get_user_access_level(user_id):
    """Get user access level based on role"""
    role = get_user_role(user_id)
    role_levels = {
        "admin": 4,
        "руководитель": 3,
        "водитель": 2,
        "гость": 1
    }
    return role_levels.get(role, 1)

def add_user(user_id, username, role='guest', groups=None):
    """Add user with role and groups"""
    users_data = load_users()
    
    if str(user_id) in users_data.get('users', {}):
        return False, "User already exists"
    
    users_data['users'][str(user_id)] = {
        "name": username,
        "role": role,
        "groups": groups or []
    }
    
    # Set role in roles database
    set_user_role(user_id, role)
    
    # Add user to groups in group system
    if groups:
        for group_id in groups:
            add_user_to_group(user_id, group_id)
    
    success, message = save_users(users_data)
    
    if success:
        return True, f"User {username} (ID: {user_id}) added as {role}"
    else:
        return False, message

def remove_user(user_id):
    """Remove user"""
    users_data = load_users()
    user_id_str = str(user_id)
    
    if user_id_str not in users_data.get('users', {}):
        return False, "User not found"
    
    if user_id == users_data.get('admin_id'):
        return False, "Cannot remove administrator"
    
    username = users_data['users'][user_id_str]['name']
    del users_data['users'][user_id_str]
    
    success, message = save_users(users_data)
    
    if success:
        return True, f"User {username} (ID: {user_id}) removed"
    else:
        return False, message

def get_users_list():
    """Return list of all users"""
    users_data = load_users()
    return users_data.get('users', {})

def get_admin_id():
    """Return administrator ID"""
    users_data = load_users()
    return users_data.get('admin_id')

def update_user_role(user_id, new_role):
    """Update user role"""
    users_data = load_users()
    user_id_str = str(user_id)
    
    if user_id_str in users_data.get('users', {}):
        users_data['users'][user_id_str]['role'] = new_role
        set_user_role(user_id, new_role)
        return save_users(users_data)
    return False
