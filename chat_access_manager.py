"""
Менеджер для проверки доступа пользователей к Telegram чатам
"""

import logging
from telegram import Bot
from user_chat_manager import user_chat_manager
from auth_manager import auth_manager

logger = logging.getLogger(__name__)

class ChatAccessManager:
    def __init__(self, bot_token):
        self.bot = Bot(token=bot_token)
    
    async def is_user_member_of_chat(self, user_id, chat_id):
        """Проверяет, является ли пользователь участником чата"""
        try:
            # Получаем информацию о участнике чата
            chat_member = await self.bot.get_chat_member(chat_id, user_id)
            
            # Проверяем, что пользователь не покинул чат и не забанен
            if chat_member.status in ['left', 'kicked', 'banned']:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки участника чата {chat_id} для пользователя {user_id}: {e}")
            return False
    
    async def get_user_accessible_chats_with_membership(self, user_id):
        """Возвращает чаты, к которым у пользователя есть доступ И в которых он состоит"""
        try:
            # Получаем чаты, к которым у пользователя есть доступ в системе
            accessible_chats = user_chat_manager.get_user_chat_access(user_id)
            
            if not accessible_chats:
                return []
            
            # Проверяем членство в каждом чате
            valid_chats = []
            for chat in accessible_chats:
                chat_id = chat['chat_id']
                is_member = await self.is_user_member_of_chat(user_id, chat_id)
                
                if is_member:
                    valid_chats.append(chat)
                else:
                    logger.warning(f"⚠️ Пользователь {user_id} не состоит в чате {chat_id} ({chat['chat_name']})")
            
            return valid_chats
            
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
            
            # Проверяем членство в чате
            return await self.is_user_member_of_chat(user_id, chat_id)
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки доступа к чату {chat_id} для пользователя {user_id}: {e}")
            return False

# Глобальный экземпляр будет инициализирован в bot.py
chat_access_manager = None

def init_chat_access_manager(bot_token):
    """Инициализирует глобальный менеджер доступа к чатам"""
    global chat_access_manager
    chat_access_manager = ChatAccessManager(bot_token)
    return chat_access_manager
