import logging
from telegram import Update
from user_chat_manager import user_chat_manager

logger = logging.getLogger(__name__)

class ChatContextManager:
    def __init__(self):
        pass
    
    def is_private_chat(self, update: Update):
        """Проверяет, является ли чат личным сообщением"""
        return update.effective_chat.type == 'private'
    
    def is_group_chat(self, update: Update):
        """Проверяет, является ли чат группой/каналом/супергруппой"""
        return update.effective_chat.type in ['group', 'supergroup', 'channel']
    
    def get_user_accessible_chats(self, user_id):
        """Возвращает чаты, доступные пользователю"""
        return user_chat_manager.get_user_chat_access(user_id)
    
    def can_user_access_chat(self, user_id, chat_id):
        """Проверяет, имеет ли пользователь доступ к указанному чату"""
        user_chats = self.get_user_accessible_chats(user_id)
        return any(chat['chat_id'] == chat_id for chat in user_chats)
    
    def format_chats_for_selection(self, user_id):
        """Форматирует список чатов для выбора"""
        accessible_chats = self.get_user_accessible_chats(user_id)
        
        if not accessible_chats:
            return None, "❌ У вас нет доступа ни к одному Telegram чату"
        
        formatted_chats = []
        for i, chat in enumerate(accessible_chats, 1):
            formatted_chats.append(f"{i}. {chat['chat_name']} (ID: {chat['chat_id']})")
        
        message = "💬 **Выберите Telegram чат для отправки:**\n\n"
        message += "\n".join(formatted_chats)
        message += "\n\nВведите номер чата:"
        
        return accessible_chats, message

# Глобальный экземпляр
chat_context_manager = ChatContextManager()
