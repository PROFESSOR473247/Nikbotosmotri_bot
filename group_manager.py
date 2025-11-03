# -*- coding: utf-8 -*-
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, CommandHandler
from datetime import datetime

from database import (
    is_authorized, is_admin, get_user_role, get_all_groups, get_user_accessible_groups,
    add_group, remove_group, add_subgroup, remove_subgroup, get_authorized_users_list,
    add_user_to_group, remove_user_from_group, save_groups
)
from menu_manager import (
    get_groups_keyboard, get_confirmation_keyboard, get_back_button
)
from user_roles import can_manage_groups, can_manage_groups_limited, can_create_subgroups, can_delete_subgroups

# Состояния для создания группы
CREATE_GROUP_NAME, CREATE_GROUP_USERS, CREATE_GROUP_CONFIRM = range(3)

# Состояния для создания подгруппы
CREATE_SUBGROUP_GROUP, CREATE_SUBGROUP_NAME, CREATE_SUBGROUP_CONFIRM = range(3)

# Состояния для удаления группы
DELETE_GROUP_SELECT, DELETE_GROUP_CONFIRM = range(2)

# Состояния для удаления подгруппы
DELETE_SUBGROUP_GROUP, DELETE_SUBGROUP_SELECT, DELETE_SUBGROUP_CONFIRM = range(3)

class GroupManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def show_groups_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню групп"""
        user_id = update.effective_user.id
        
        if not is_authorized(user_id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        from menu_manager import get_groups_menu
        keyboard = get_groups_menu(user_id)
        await update.message.reply_text("🏘️ УПРАВЛЕНИЕ ГРУППАМИ", reply_markup=keyboard)

    # =============================================================================
    # СПИСОК ГРУПП
    # =============================================================================

    async def show_groups_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список групп с информацией"""
        user_id = update.effective_user.id
        
        if not is_authorized(user_id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        accessible_groups = get_user_accessible_groups(user_id)
        if not accessible_groups:
            await update.message.reply_text("📭 *У вас нет доступа к каким-либо группам*", parse_mode='Markdown')
            return
        
        user_role = get_user_role(user_id)
        
        response = "📋 *СПИСОК ГРУПП И ПОДГРУПП*\n\n"
        
        for group_id, group_info in accessible_groups.items():
            group_name = group_info.get('name', group_id)
            subgroups = group_info.get('subgroups', {})
            
            response += f"🏘️ *{group_name}* (ID: {group_id})\n"
            
            if subgroups:
                response += "📁 *Подгруппы:*\n"
                for subgroup_id, subgroup_name in subgroups.items():
                    response += f"  • {subgroup_name}\n"
            else:
                response += "  📭 *Нет подгрупп*\n"
            
            # Для администратора показываем участников
            if user_role == "admin":
                users_in_group = self._get_users_in_group(group_id)
                if users_in_group:
                    response += "👥 *Участники:*\n"
                    for user_name in users_in_group:
                        response += f"  • {user_name}\n"
                else:
                    response += "  👥 *Нет участников*\n"
            
            response += "───────\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')

    def _get_users_in_group(self, group_id):
        """Получить список пользователей в группе"""
        users = get_authorized_users_list()
        users_in_group = []
        
        for user_id, user_data in users.items():
            user_groups = user_data.get('groups', [])
            if group_id in user_groups:
                users_in_group.append(user_data.get('name', f"User_{user_id}"))
        
        return users_in_group

    # =============================================================================
    # СОЗДАНИЕ ГРУППЫ (только для администратора)
    # =============================================================================

    async def start_create_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать создание новой группы"""
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            await update.message.reply_text("❌ Только для администратора")
            return ConversationHandler.END
        
        context.user_data['group_creation'] = {
            'admin_id': user_id
        }
        
        await update.message.reply_text(
            "🏘️ *ШАГ 1/3: ВВЕДИТЕ НАЗВАНИЕ ГРУППЫ*\n\n"
            "ℹ️ Используйте понятное название для идентификации",
            parse_mode='Markdown'
        )
        
        return CREATE_GROUP_NAME

    # =============================================================================
    # СОЗДАНИЕ ПОДГРУППЫ
    # =============================================================================

    async def start_create_subgroup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать создание новой подгруппы"""
        user_id = update.effective_user.id
        
        user_role = get_user_role(user_id)
        if not can_create_subgroups(user_role):
            await update.message.reply_text("❌ Недостаточно прав для создания подгрупп")
            return ConversationHandler.END
        
        accessible_groups = get_user_accessible_groups(user_id)
        if not accessible_groups:
            await update.message.reply_text("❌ У вас нет доступа к каким-либо группам")
            return ConversationHandler.END
        
        context.user_data['subgroup_creation'] = {
            'user_id': user_id
        }
        
        keyboard = get_groups_keyboard(accessible_groups)
        await update.message.reply_text(
            "🏘️ *ВЫБЕРИТЕ ГРУППУ ДЛЯ СОЗДАНИЯ ПОДГРУППЫ*",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return CREATE_SUBGROUP_GROUP

    # =============================================================================
    # УДАЛЕНИЕ ПОДГРУППЫ
    # =============================================================================

    async def start_delete_subgroup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать удаление подгруппы"""
        user_id = update.effective_user.id
        
        user_role = get_user_role(user_id)
        if not can_delete_subgroups(user_role):
            await update.message.reply_text("❌ Недостаточно прав для удаления подгрупп")
            return ConversationHandler.END
        
        accessible_groups = get_user_accessible_groups(user_id)
        if not accessible_groups:
            await update.message.reply_text("❌ У вас нет доступа к каким-либо группам")
            return ConversationHandler.END
        
        # Фильтруем группы, которые имеют подгруппы
        groups_with_subgroups = {}
        all_groups = get_all_groups()
        for group_id in accessible_groups:
            group_info = all_groups.get(group_id, {})
            subgroups = group_info.get('subgroups', {})
            if subgroups:
                groups_with_subgroups[group_id] = group_info
        
        if not groups_with_subgroups:
            await update.message.reply_text("📭 *В доступных группах нет подгрупп для удаления*", parse_mode='Markdown')
            return ConversationHandler.END
        
        context.user_data['subgroup_deletion'] = {
            'user_id': user_id,
            'step': 'select_group'
        }
        
        keyboard = get_groups_keyboard(groups_with_subgroups)
        await update.message.reply_text(
            "🏘️ *ВЫБЕРИТЕ ГРУППУ ДЛЯ УДАЛЕНИЯ ПОДГРУППЫ*",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return DELETE_SUBGROUP_GROUP

    # =============================================================================
    # ОБРАБОТЧИКИ КНОПОК
    # =============================================================================

    async def handle_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки групп"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        if not is_authorized(user_id):
            await query.edit_message_text("❌ Недостаточно прав")
            return
        
        try:
            if data == "back":
                from menu_manager import get_groups_menu
                keyboard = get_groups_menu(user_id)
                await query.message.reply_text(
                    "🏘️ УПРАВЛЕНИЕ ГРУППАМИ",
                    reply_markup=keyboard
                )
                await query.message.delete()
            
            elif data.startswith("select_group_"):
                # Обработка выбора группы
                await self.show_group_info(update, context)
            elif data.startswith("groups_page_"):
                page = int(data.replace("groups_page_", ""))
                accessible_groups = get_user_accessible_groups(user_id)
                from menu_manager import get_groups_keyboard
                keyboard = get_groups_keyboard(accessible_groups, page)
                await query.edit_message_reply_markup(reply_markup=keyboard)
            else:
                await query.edit_message_text(
                    "🛠️ *Функция в разработке*",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]]),
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка в обработчике групп: {e}")
            await query.edit_message_text(
                "❌ *Ошибка при обработке группы*",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]]),
                parse_mode='Markdown'
            )

    async def show_group_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать информацию о выбранной группе"""
        query = update.callback_query
        data = query.data
        
        if data.startswith("select_group_"):
            group_id = data.replace("select_group_", "")
            
            groups_data = get_all_groups()
            group_info = groups_data.get(group_id, {})
            group_name = group_info.get('name', group_id)
            subgroups = group_info.get('subgroups', {})
            
            response = f"🏘️ *Информация о группе: {group_name}*\n\n"
            
            if subgroups:
                response += "📁 *Подгруппы:*\n"
                for subgroup_id, subgroup_name in subgroups.items():
                    response += f"  • {subgroup_name}\n"
            else:
                response += "📭 *Подгруппы: Нет*\n"
            
            # Показываем участников
            users_in_group = self._get_users_in_group(group_id)
            if users_in_group:
                response += "👥 *Участники:*\n"
                for user_name in users_in_group:
                    response += f"  • {user_name}\n"
            else:
                response += "👥 *Участники: Нет*\n"
            
            from menu_manager import get_back_button
            keyboard = InlineKeyboardMarkup([get_back_button()])
            
            await query.edit_message_text(
                response,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

    def get_conversation_handler(self):
        """Получить ConversationHandler для групп"""
        return ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex("^📋 Список групп$"), self.show_groups_list),
                MessageHandler(filters.Regex("^➕ Создать группу$"), self.start_create_group),
                MessageHandler(filters.Regex("^📁 Создать подгруппу$"), self.start_create_subgroup),
                MessageHandler(filters.Regex("^🗑️ Удалить подгруппу$"), self.start_delete_subgroup),
            ],
            states={
                # States будут добавлены по мере реализации
            },
            fallbacks=[CommandHandler("cancel", self.cancel_group_operation)],
            name="group_conversation"
        )

    async def cancel_group_operation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена операции с группой"""
        user_id = update.effective_user.id
        
        # Очищаем временные данные
        for key in list(context.user_data.keys()):
            if 'group' in key or 'subgroup' in key:
                context.user_data.pop(key, None)
        
        from menu_manager import get_main_menu
        await update.message.reply_text(
            "❌ Операция с группой отменена",
            reply_markup=get_main_menu(user_id)
        )
        return ConversationHandler.END

# Глобальный экземпляр менеджера групп
group_manager = GroupManager()
