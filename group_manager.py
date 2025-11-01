import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import load_groups, save_groups, load_user_groups, save_user_groups, get_user_accessible_groups

class GroupManager:
    def __init__(self):
        self.known_groups = {}

    async def update_group_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обновление информации о группе когда бот добавляется в нее"""
        chat = update.effective_chat
        
        if chat.type in ["group", "supergroup", "channel"]:
            group_data = {
                "id": chat.id,
                "title": chat.title,
                "type": chat.type,
                "username": getattr(chat, 'username', None),
                "updated_at": datetime.now().isoformat()
            }
            
            groups_data = load_groups()
            groups_data["groups"][str(chat.id)] = group_data
            save_groups(groups_data)
            
            logging.info(f"✅ Обновлена информация о группе: {chat.title} (ID: {chat.id})")

    async def get_bot_groups(self, context: ContextTypes.DEFAULT_TYPE):
        """Получение списка групп где есть бот (ограниченно в Telegram Bot API)"""
        # В реальности этот метод ограничен, поэтому полагаемся на ручное добавление
        # и отслеживание когда бота добавляют в группы
        groups_data = load_groups()
        return groups_data.get("groups", {})

    async def check_user_membership(self, context: ContextTypes.DEFAULT_TYPE, user_id, group_id):
        """Проверка состоит ли пользователь в группе"""
        try:
            # Пытаемся получить информацию о пользователе в группе
            chat_member = await context.bot.get_chat_member(group_id, user_id)
            return chat_member.status in ['member', 'administrator', 'creator']
        except Exception as e:
            logging.error(f"Ошибка проверки membership: {e}")
            return False

    def get_accessible_groups_for_user(self, user_id):
        """Получение групп доступных пользователю"""
        return get_user_accessible_groups(user_id)

# Глобальный экземпляр менеджера групп
group_manager = GroupManager()
