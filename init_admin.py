#!/usr/bin/env python3
"""
Script to initialize or reset admin user
"""
from database import init_database, set_user_role
from authorized_users import load_users, save_users

def init_admin():
    """Initialize admin user"""
    init_database()
    
    users_data = load_users()
    
    # Set admin user
    admin_id = 812934047
    users_data['users'] = {
        str(admin_id): {
            "name": "Никита",
            "role": "admin",
            "groups": ["all"]
        }
    }
    users_data['admin_id'] = admin_id
    
    # Save to authorized_users
    success, message = save_users(users_data)
    
    # Save to user_roles
    set_user_role(admin_id, "admin")
    
    if success:
        print(f"✅ Admin user {admin_id} initialized successfully!")
        print(f"Message: {message}")
    else:
        print(f"❌ Error initializing admin: {message}")

if __name__ == '__main__':
    init_admin()
