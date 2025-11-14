import logging
from database import db

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self):
        self.admin_user_id = 812934047  # Ваш ID администратора
    
    def get_user_role(self, user_id):
        """Возвращает роль пользователя"""
        try:
            # Получаем всех пользователей и ищем нужного
            users = db.get_all_users()
            for user in users:
                if user['user_id'] == user_id:
                    return user.get('role', 'guest')
            
            # Если пользователь не найден, создаем его как гостя
            return self._create_guest_user(user_id)
            
        except Exception as e:
            print(f"❌ Ошибка получения роли пользователя {user_id}: {e}")
            return 'guest'
    
    def _create_guest_user(self, user_id):
        """Создает гостевого пользователя при первом обращении"""
        try:
            # В реальной реализации здесь нужно получить информацию о пользователе из Telegram
            # Пока создаем пользователя с базовыми данными
            success, message = db.add_user(
                user_id=user_id,
                username='unknown',
                full_name='Новый пользователь',
                role='guest'
            )
            
            if success:
                print(f"✅ Создан новый пользователь: {user_id} (гость)")
                return 'guest'
            else:
                print(f"❌ Ошибка создания пользователя {user_id}: {message}")
                return 'guest'
                
        except Exception as e:
            print(f"❌ Ошибка создания гостевого пользователя: {e}")
            return 'guest'
    
    def is_authorized(self, user_id):
        """Проверяет, авторизован ли пользователь"""
        # В текущей реализации все пользователи авторизованы
        # Можно добавить логику бана или ограничений
        return True
    
    def is_admin(self, user_id):
        """Проверяет, является ли пользователь администратором"""
        role = self.get_user_role(user_id)
        return role in ['admin', 'superadmin']
    
    def update_user_role_if_needed(self, user_id):
        """Гарантирует, что указанный пользователь имеет права администратора"""
        try:
            if user_id == self.admin_user_id:
                users = db.get_all_users()
                user_found = False
                
                for user in users:
                    if user['user_id'] == user_id:
                        user_found = True
                        if user.get('role') not in ['admin', 'superadmin']:
                            # Обновляем роль на администратора
                            success, message = db.update_user_role(user_id, 'admin')
                            if success:
                                print(f"✅ Права администратора восстановлены для {user_id}")
                            else:
                                print(f"❌ Ошибка обновления прав: {message}")
                        break
                
                if not user_found:
                    # Создаем администратора
                    success, message = db.add_user(
                        user_id=user_id,
                        username='admin',
                        full_name='Administrator',
                        role='admin'
                    )
                    if success:
                        print(f"✅ Администратор создан: {user_id}")
                    else:
                        print(f"❌ Ошибка создания администратора: {message}")
                        
        except Exception as e:
            print(f"❌ Ошибка проверки прав администратора: {e}")

# Глобальный экземпляр
auth_manager = AuthManager()
