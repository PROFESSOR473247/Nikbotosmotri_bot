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
        TELEGRAM_GROUPS_FILE: {"telegram_groups": {}}
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
