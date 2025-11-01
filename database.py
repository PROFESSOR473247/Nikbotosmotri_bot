import json
import os
from datetime import datetime, timedelta
import logging

# Files for data storage
TASKS_FILE = 'active_tasks.json'
GROUPS_FILE = 'bot_groups.json'
USER_GROUPS_FILE = 'user_groups.json'

def init_database():
    """Initialize database"""
    for file in [TASKS_FILE, GROUPS_FILE, USER_GROUPS_FILE]:
        if not os.path.exists(file):
            with open(file, 'w', encoding='utf-8') as f:
                if file == TASKS_FILE:
                    json.dump({"tasks": {}}, f, ensure_ascii=False, indent=2)
                elif file == GROUPS_FILE:
                    json.dump({"groups": {}}, f, ensure_ascii=False, indent=2)
                else:
                    json.dump({"user_groups": {}}, f, ensure_ascii=False, indent=2)
            print(f"Created file: {file}")

def load_tasks():
    """Load active tasks"""
    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading tasks: {e}")
        return {"tasks": {}}

def save_tasks(tasks_data):
    """Save tasks"""
    try:
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tasks_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"Error saving tasks: {e}")
        return False

def load_groups():
    """Load group information"""
    try:
        with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading groups: {e}")
        return {"groups": {}}

def save_groups(groups_data):
    """Save group information"""
    try:
        with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(groups_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"Error saving groups: {e}")
        return False

def load_user_groups():
    """Load user-group mappings"""
    try:
        with open(USER_GROUPS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading user_groups: {e}")
        return {"user_groups": {}}

def save_user_groups(user_groups_data):
    """Save user-group mappings"""
    try:
        with open(USER_GROUPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_groups_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"Error saving user_groups: {e}")
        return False

def add_task(task_id, task_data):
    """Add new task"""
    tasks_data = load_tasks()
    tasks_data["tasks"][task_id] = task_data
    return save_tasks(tasks_data)

def remove_task(task_id):
    """Remove task"""
    tasks_data = load_tasks()
    if task_id in tasks_data["tasks"]:
        del tasks_data["tasks"][task_id]
        return save_tasks(tasks_data)
    return False

def get_user_accessible_groups(user_id):
    """Get groups accessible to user"""
    user_groups_data = load_user_groups()
    groups_data = load_groups()
    
    accessible_groups = {}
    user_id_str = str(user_id)
    
    if user_id_str in user_groups_data.get("user_groups", {}):
        for group_id in user_groups_data["user_groups"][user_id_str]:
            if group_id in groups_data.get("groups", {}):
                accessible_groups[group_id] = groups_data["groups"][group_id]
    
    return accessible_groups

def add_group(group_id, group_data):
    """Add new group"""
    groups_data = load_groups()
    groups_data["groups"][group_id] = group_data
    return save_groups(groups_data)

def add_user_to_group(user_id, group_id):
    """Add user to group"""
    user_groups_data = load_user_groups()
    user_id_str = str(user_id)
    
    if "user_groups" not in user_groups_data:
        user_groups_data["user_groups"] = {}
    
    if user_id_str not in user_groups_data["user_groups"]:
        user_groups_data["user_groups"][user_id_str] = []
    
    if group_id not in user_groups_data["user_groups"][user_id_str]:
        user_groups_data["user_groups"][user_id_str].append(group_id)
    
    return save_user_groups(user_groups_data)
