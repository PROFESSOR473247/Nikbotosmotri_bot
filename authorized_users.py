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
