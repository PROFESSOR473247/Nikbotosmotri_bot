import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from database import load_telegram_groups, save_telegram_groups, add_telegram_group

class GroupTracker:
    def __init__(self):
        self.known_groups = {}

    async def track_group_addition(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отслеживать добавление бота в группы"""
        if update.message and update.message.new_chat_members:
            for user in update.message.new_chat_members:
                if user.id == context.bot.id:
                    await self.add_group(update, context)
                    break

    async def add_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить группу в отслеживание"""
        chat = update.effective_chat
        
        if chat.type in ["group", "supergroup"]:
            group_data = {
                "id": chat.id,
                "title": chat.title,
                "type": chat.type,
                "username": getattr(chat, 'username', None),
                "updated_at": datetime.now().isoformat()
            }
            
            add_telegram_group(str(chat.id), group_data)
            logging.info(f"✅ Бот добавлен в группу: {chat.title} (ID: {chat.id})")

    async def check_user_membership(self, context: ContextTypes.DEFAULT_TYPE, user_id: int, group_id: str) -> bool:
        """Проверить, состоит ли пользователь в группе"""
        try:
            chat_member = await context.bot.get_chat_member(chat_id=group_id, user_id=user_id)
            return chat_member.status in ['member', 'administrator', 'creator']
        except Exception as e:
            logging.error(f"❌ Ошибка проверки членства: {e}")
            return False

    def get_bot_groups(self):
        """Получить все группы, где есть бот"""
        return load_telegram_groups().get("telegram_groups", {})

# Глобальный экземпляр трекера групп
group_tracker = GroupTracker()
