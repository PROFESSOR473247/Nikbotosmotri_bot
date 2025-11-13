import logging
from database import db  # Используем обновленную базу данных

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserChatManager:
    def __init__(self):
        self.db = db
    
    def get_connection(self):
        return self.db.get_connection()
    
    # Все методы остаются без изменений, так как они теперь в database.py
    # Но если нужно, можно оставить их здесь как прокси-методы
    
    def add_user(self, user_id, username, full_name, role='guest'):
        """Добавляет нового пользователя"""
        return self.db.add_user(user_id, username, full_name, role)
    
    def get_all_users(self):
        """Возвращает всех пользователей"""
        return self.db.get_all_users()
    
    def delete_user(self, user_id):
        """Удаляет пользователя"""
        return self.db.delete_user(user_id)
    
    def update_user_role(self, user_id, new_role):
        """Обновляет роль пользователя"""
        return self.db.update_user_role(user_id, new_role)
    
    def add_telegram_chat(self, chat_id, chat_name, original_name=None):
        """Добавляет новый Telegram чат"""
        return self.db.add_telegram_chat(chat_id, chat_name, original_name)
    
    def get_all_chats(self):
        """Возвращает все Telegram чаты"""
        return self.db.get_all_chats()
    
    def delete_chat(self, chat_id):
        """Удаляет Telegram чат"""
        return self.db.delete_chat(chat_id)
    
    def grant_chat_access(self, user_id, chat_id):
        """Предоставляет доступ пользователю к чату"""
        return self.db.grant_chat_access(user_id, chat_id)
    
    def revoke_chat_access(self, user_id, chat_id):
        """Отзывает доступ пользователя к чату"""
        return self.db.revoke_chat_access(user_id, chat_id)
    
    def grant_template_group_access(self, user_id, group_id):
        """Предоставляет доступ пользователю к группе шаблонов"""
        return self.db.grant_template_group_access(user_id, group_id)
    
    def revoke_template_group_access(self, user_id, group_id):
        """Отзывает доступ пользователя к группе шаблонов"""
        return self.db.revoke_template_group_access(user_id, group_id)
    
    def get_user_chat_access(self, user_id):
        """Возвращает чаты, к которым у пользователя есть доступ"""
        return self.db.get_user_chat_access(user_id)
    
    def get_user_template_group_access(self, user_id):
        """Возвращает группы шаблонов, к которым у пользователя есть доступ"""
        return self.db.get_user_template_group_access(user_id)
    
    def get_chat_users(self, chat_id):
        """Возвращает пользователей, имеющих доступ к чату"""
        return self.db.get_chat_users(chat_id)
    
    def get_group_users(self, group_id):
        """Возвращает пользователей, имеющих доступ к группе шаблонов"""
        return self.db.get_group_users(group_id)

# Глобальный экземпляр менеджера
user_chat_manager = UserChatManager()