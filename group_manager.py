import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from database import load_groups, save_groups, get_user_accessible_groups

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
            
            logging.info(f"✅ Updated group info: {chat.title} (ID: {chat.id})")

    def get_accessible_groups_for_user(self, user_id):
        """Get groups accessible to user - simplified for now"""
        # For now, return all groups until user-group system is fully implemented
        groups_data = load_groups()
        return groups_data.get("groups", {})

# Global group manager instance
group_manager = GroupManager()
