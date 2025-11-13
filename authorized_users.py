from auth_manager import auth_manager

# Прокси-функции для обратной совместимости
def is_authorized(user_id):
    """Все пользователи авторизованы"""
    return True

def is_admin(user_id):
    """Проверяет, является ли пользователь администратором"""
    return auth_manager.is_admin(user_id)

def get_user_role(user_id):
    """Возвращает роль пользователя"""
    return auth_manager.get_user_role(user_id)

def check_duplicate_user(user_id):
    """Проверяет, существует ли пользователь с таким ID"""
    return auth_manager.check_duplicate_user(user_id)

def get_user_access_groups(user_id):
    """Возвращает группы, к которым у пользователя есть доступ"""
    # Для обратной совместимости, возвращаем все группы для админа
    if is_admin(user_id):
        from template_manager import load_groups
        groups_data = load_groups()
        return list(groups_data.get('groups', {}).keys())
    
    # Для обычных пользователей используем новую систему доступа
    from user_chat_manager import user_chat_manager
    user_groups = user_chat_manager.get_user_template_group_access(user_id)
    return [group['id'] for group in user_groups]