import logging
from database import db
from config import ADMIN_USER_ID

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self):
        self.db = db
    
    def is_admin(self, user_id):
        """Проверяет, является ли пользователь администратором"""
        # Суперадмин из config.py всегда имеет права
        if user_id == ADMIN_USER_ID:
            return True
        
        # Проверяем в базе данных
        users = self.db.get_all_users()
        for user in users:
            if user['user_id'] == user_id and user['role'] == 'admin':
                return True
        
        return False
    
    def ensure_admin_access(self, user_id):
        """Гарантирует, что указанный пользователь имеет админские права"""
        if not self.is_admin(user_id):
            # Если пользователь не админ, но это суперадмин из config - добавляем его
            if user_id == ADMIN_USER_ID:
                self.db.add_user(
                    user_id=user_id,
                    username="admin",
                    full_name="Administrator", 
                    role="admin"
                )
                return True
        return self.is_admin(user_id)
    
    def get_user_role(self, user_id):
        """Возвращает роль пользователя"""
        users = self.db.get_all_users()
        for user in users:
            if user['user_id'] == user_id:
                return user['role']
        
        # Если пользователь не найден, но это суперадмин
        if user_id == ADMIN_USER_ID:
            return "admin"
        
        return None
    
    def update_user_role_if_needed(self, user_id):
        """Обновляет роль пользователя если это суперадмин"""
        if user_id == ADMIN_USER_ID:
            self.db.add_user(
                user_id=user_id,
                username="admin",
                full_name="Administrator",
                role="admin"
            )
            return True
        return False

# Глобальный экземпляр
auth_manager = AuthManager()
