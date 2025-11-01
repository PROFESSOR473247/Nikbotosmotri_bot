import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from database import load_groups, save_groups, load_user_groups, save_user_groups, get_user_accessible_groups

class GroupManager:
    def __init__(self):
        self.known_groups = {}

    async def update_group_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Update group information when bot is added to it"""
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
            
            logging.info(f"Updated group info: {chat.title} (ID: {chat.id})")

    async def get_bot_groups(self, context: ContextTypes.DEFAULT_TYPE):
        """Get list of groups where bot is present (limited in Telegram Bot API)"""
        # In reality this method is limited, so we rely on manual addition
        # and tracking when bot is added to groups
        groups_data = load_groups()
        return groups_data.get("groups", {})

    async def check_user_membership(self, context: ContextTypes.DEFAULT_TYPE, user_id, group_id):
        """Check if user is member of group"""
        try:
            # Try to get user information in group
            chat_member = await context.bot.get_chat_member(group_id, user_id)
            return chat_member.status in ['member', 'administrator', 'creator']
        except Exception as e:
            logging.error(f"Error checking membership: {e}")
            return False

    def get_accessible_groups_for_user(self, user_id):
        """Get groups accessible to user"""
        return get_user_accessible_groups(user_id)

# Global group manager instance
group_manager = GroupManager()
