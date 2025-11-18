"""
Простой менеджер для проверки доступа пользователей к Telegram чатам
"""

import logging
from user_chat_manager import user_chat_manager

logger = logging.getLogger(__name__)

class ChatAccessManager:
    def __init__(self):
        pass
    
    async def is_user_member_of_chat(self, user_id, chat_id):
        """Проверяет, является ли пользователь участником чата"""
        try:
            # Временно возвращаем True для тестирования
            # В реальной реализации здесь будет проверка через Bot.get_chat_member()
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки участника чата {chat_id} для пользователя {user_id}: {e}")
            return False
    
    async def get_user_accessible_chats_with_membership(self, user_id):
        """Возвращает чаты, к которым у пользователя есть доступ"""
        try:
            # Получаем чаты, к которым у пользователя есть доступ в системе
            accessible_chats = user_chat_manager.get_user_chat_access(user_id)
            
            if not accessible_chats:
                return []
            
            # Временно возвращаем все доступные чаты
            # В реальной реализации здесь будет проверка членства
            return accessible_chats
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения доступных чатов для пользователя {user_id}: {e}")
            return []
    
    async def can_user_send_to_chat(self, user_id, chat_id):
        """Проверяет, может ли пользователь отправлять сообщения в указанный чат"""
        try:
            # Проверяем доступ в системе
            has_system_access = any(
                chat['chat_id'] == chat_id 
                for chat in user_chat_manager.get_user_chat_access(user_id)
            )
            
            if not has_system_access:
                return False
            
            # Временно возвращаем True
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки доступа к чату {chat_id} для пользователя {user_id}: {e}")
            return False

# Глобальный экземпляр
chat_access_manager = ChatAccessManager()
