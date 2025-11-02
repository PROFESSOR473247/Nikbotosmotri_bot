"""
This file is now DEPRECATED and kept for backward compatibility only.
All user management functions have been moved to database.py
"""

from database import (
    is_authorized,
    is_admin, 
    get_user_role,
    add_authorized_user as add_user,
    remove_authorized_user as remove_user,
    get_authorized_users_list as get_users_list,
    get_admin_id
)

# These functions are now just aliases to database.py functions
# This maintains backward compatibility with existing code

__all__ = [
    'is_authorized',
    'is_admin',
    'get_user_role', 
    'add_user',
    'remove_user',
    'get_users_list',
    'get_admin_id'
]
