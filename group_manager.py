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
from user_roles import get_role_name

# Состояния для создания группы
CREATE_GROUP_NAME, CREATE_GROUP_USERS, CREATE_GROUP_CONFIRM = range(3)

# Состояния для создания подгруппы
CREATE_SUBGROUP_GROUP, CREATE_SUBGROUP_NAME, CREATE_SUBGROUP_CONFIRM = range(3)

# Состояния для изменения доступа к группе
EDIT_GROUP_ACCESS_SELECT, EDIT_GROUP_ACCESS_ACTION, EDIT_GROUP_ACCESS_ADD, EDIT_GROUP_ACCESS_REMOVE = range(4)

# Состояния для удаления группы
DELETE_GROUP_SELECT, DELETE_GROUP_CONFIRM = range(2)

# Состояния для удаления подгруппы
DELETE_SUBGROUP_GROUP, DELETE_SUBGROUP_SELECT, DELETE_SUBGROUP_CONFIRM = range(3)

class GroupManager:
    def __init__(self):
        self.temp_data = {}

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
        
        all_groups = get_all_groups()
        if not all_groups:
            await update.message.reply_text("📭 В системе пока нет групп")
            return
        
        user_role = get_user_role(user_id)
        accessible_groups = get_user_accessible_groups(user_id)
        
        response = "📋 *СПИСОК ГРУПП И ПОДГРУПП*\n\n"
        
        for group_id, group_info in all_groups.items():
            group_name = group_info.get('name', group_id)
            subgroups = group_info.get('subgroups', {})
            
            # Проверяем доступ пользователя к группе
            if group_id in accessible_groups or user_role == "admin":
                response += f"🏘️ *{group_name}* (ID: {group_id})\n"
                
                if subgroups:
                    response += "📁 *Подгруппы:*\n"
                    for subgroup_id, subgroup_name in subgroups.items():
                        response += f"  • {subgroup_name}\n"
                else:
                    response += "  📭 Нет подгрупп\n"
                
                # Для администратора показываем участников
                if user_role == "admin":
                    users_in_group = self._get_users_in_group(group_id)
                    if users_in_group:
                        response += "👥 *Участники:*\n"
                        for user_name in users_in_group:
                            response += f"  • {user_name}\n"
                    else:
                        response += "  👥 Нет участников\n"
                
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
    # СОЗДАНИЕ ГРУППЫ
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

    async def create_group_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода названия группы"""
        group_name = update.message.text.strip()
        
        if len(group_name) < 2:
            await update.message.reply_text("❌ Название слишком короткое. Введите еще раз:")
            return CREATE_GROUP_NAME
        
        context.user_data['group_creation']['group_name'] = group_name
        
        # Получаем список всех пользователей
        all_users = get_authorized_users_list()
        if not all_users:
            await update.message.reply_text("❌ В системе нет пользователей. Сначала добавьте пользователей.")
            return ConversationHandler.END
        
        # Формируем список пользователей для выбора
        users_list = "👥 *СПИСОК ПОЛЬЗОВАТЕЛЕЙ:*\n\n"
        user_ids = list(all_users.keys())
        
        for i, user_id in enumerate(user_ids, 1):
            user_data = all_users[user_id]
            user_name = user_data.get('name', f"User_{user_id}")
            users_list += f"{i}. {user_name} (ID: {user_id})\n"
        
        users_list += "\n🔢 *УКАЖИТЕ НОМЕРА ПОЛЬЗОВАТЕЛЕЙ ЧЕРЕЗ ЗАПЯТУЮ* (например: 1,3,5)"
        
        context.user_data['group_creation']['all_users'] = all_users
        context.user_data['group_creation']['user_ids'] = user_ids
        
        await update.message.reply_text(
            f"👥 *ШАГ 2/3: ВЫБЕРИТЕ ПОЛЬЗОВАТЕЛЕЙ ДЛЯ ДОБАВЛЕНИЯ В ГРУППУ*\n\n{users_list}",
            parse_mode='Markdown'
        )
        
        return CREATE_GROUP_USERS

    async def create_group_users_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода пользователей для группы"""
        users_input = update.message.text.strip()
        
        try:
            # Парсим номера пользователей
            user_numbers = [int(num.strip()) for num in users_input.split(',')]
        except ValueError:
            await update.message.reply_text("❌ Неверный формат. Используйте номера через запятую (например: 1,3,5):")
            return CREATE_GROUP_USERS
        
        all_users = context.user_data['group_creation']['all_users']
        user_ids = context.user_data['group_creation']['user_ids']
        
        # Проверяем валидность номеров
        selected_users = []
        for num in user_numbers:
            if 1 <= num <= len(user_ids):
                user_id = user_ids[num - 1]
                user_data = all_users[user_id]
                selected_users.append({
                    'id': user_id,
                    'name': user_data.get('name', f"User_{user_id}")
                })
            else:
                await update.message.reply_text(f"❌ Неверный номер пользователя: {num}. Введите номера от 1 до {len(user_ids)}:")
                return CREATE_GROUP_USERS
        
        context.user_data['group_creation']['selected_users'] = selected_users
        
        # Показываем подтверждение
        return await self.show_create_group_confirmation(update, context)

    async def show_create_group_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать подтверждение создания группы"""
        group_data = context.user_data['group_creation']
        
        confirmation_text = self._format_group_confirmation(group_data)
        
        keyboard = get_confirmation_keyboard("confirm_create_group", "edit_create_group")
        
        await update.message.reply_text(
            confirmation_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return CREATE_GROUP_CONFIRM

    def _format_group_confirmation(self, group_data):
        """Форматирование подтверждения группы"""
        text = "✅ *ПОДТВЕРЖДЕНИЕ СОЗДАНИЯ ГРУППЫ*\n\n"
        
        text += f"🏘️ *Название:* {group_data.get('group_name')}\n"
        
        selected_users = group_data.get('selected_users', [])
        if selected_users:
            text += "👥 *Участники:*\n"
            for user in selected_users:
                text += f"  • {user['name']} (ID: {user['id']})\n"
        else:
            text += "👥 *Участники:* Нет\n"
        
        text += "\n❓ *Все верно?*"
        
        return text

    async def create_group_confirmation_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения создания группы"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "confirm_create_group":
            group_data = context.user_data['group_creation']
            
            # Создаем ID группы
            group_id = f"group_{len(get_all_groups()) + 1}"
            
            # Создаем группу
            group_info = {
                'id': group_id,
                'name': group_data['group_name'],
                'subgroups': {},
                'created_at': datetime.now().isoformat()
            }
            
            success = add_group(group_id, group_info)
            
            if success:
                # Добавляем пользователей в группу
                for user in group_data.get('selected_users', []):
                    add_user_to_group(int(user['id']), group_id)
                
                await query.edit_message_text(
                    f"✅ Группа '{group_data['group_name']}' успешно создана!\n\n"
                    f"🆔 ID группы: `{group_id}`",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    f"❌ Ошибка при создании группы '{group_data['group_name']}'",
                    parse_mode='Markdown'
                )
        
        elif data == "edit_create_group":
            # Здесь будет логика редактирования
            await query.edit_message_text("✏️ Редактирование создания группы\n\nЭта функция в разработке...")
        
        # Очищаем временные данные
        context.user_data.pop('group_creation', None)
        return ConversationHandler.END

    # =============================================================================
    # СОЗДАНИЕ ПОДГРУППЫ
    # =============================================================================

    async def start_create_subgroup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать создание новой подгруппы"""
        user_id = update.effective_user.id
        
        user_role = get_user_role(user_id)
        if user_role not in ["admin", "руководитель"]:
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

    async def create_subgroup_group_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора группы для подгруппы"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            from menu_manager import get_groups_menu
            keyboard = get_groups_menu(query.from_user.id)
            await query.edit_message_text(
                "🏘️ УПРАВЛЕНИЕ ГРУППАМИ",
                reply_markup=keyboard
            )
            return ConversationHandler.END
        
        if data.startswith("select_group_"):
            group_id = data.replace("select_group_", "")
            context.user_data['subgroup_creation']['group_id'] = group_id
            
            groups_data = get_all_groups()
            group_name = groups_data.get(group_id, {}).get('name', group_id)
            
            await query.edit_message_text(
                f"📁 *ВВЕДИТЕ НАЗВАНИЕ ПОДГРУППЫ ДЛЯ ГРУППЫ '{group_name}'*\n\n"
                f"ℹ️ Используйте понятное название для идентификации",
                parse_mode='Markdown'
            )
            
            return CREATE_SUBGROUP_NAME

    async def create_subgroup_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода названия подгруппы"""
        subgroup_name = update.message.text.strip()
        
        if len(subgroup_name) < 2:
            await update.message.reply_text("❌ Название слишком короткое. Введите еще раз:")
            return CREATE_SUBGROUP_NAME
        
        context.user_data['subgroup_creation']['subgroup_name'] = subgroup_name
        
        # Показываем подтверждение
        return await self.show_create_subgroup_confirmation(update, context)

    async def show_create_subgroup_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать подтверждение создания подгруппы"""
        subgroup_data = context.user_data['subgroup_creation']
        
        groups_data = get_all_groups()
        group_id = subgroup_data['group_id']
        group_name = groups_data.get(group_id, {}).get('name', group_id)
        
        confirmation_text = (
            f"✅ *ПОДТВЕРЖДЕНИЕ СОЗДАНИЯ ПОДГРУППЫ*\n\n"
            f"🏘️ *Группа:* {group_name}\n"
            f"📁 *Подгруппа:* {subgroup_data['subgroup_name']}\n\n"
            f"❓ *Все верно?*"
        )
        
        keyboard = get_confirmation_keyboard("confirm_create_subgroup", "edit_create_subgroup")
        
        await update.message.reply_text(
            confirmation_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return CREATE_SUBGROUP_CONFIRM

    async def create_subgroup_confirmation_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения создания подгруппы"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "confirm_create_subgroup":
            subgroup_data = context.user_data['subgroup_creation']
            
            # Создаем ID подгруппы
            subgroup_id = f"subgroup_{len(get_all_groups().get(subgroup_data['group_id'], {}).get('subgroups', {})) + 1}"
            
            # Добавляем подгруппу
            success = add_subgroup(
                subgroup_data['group_id'],
                subgroup_id,
                subgroup_data['subgroup_name']
            )
            
            if success:
                groups_data = get_all_groups()
                group_name = groups_data.get(subgroup_data['group_id'], {}).get('name', subgroup_data['group_id'])
                
                await query.edit_message_text(
                    f"✅ Подгруппа '{subgroup_data['subgroup_name']}' успешно создана в группе '{group_name}'!",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    f"❌ Ошибка при создании подгруппы '{subgroup_data['subgroup_name']}'",
                    parse_mode='Markdown'
                )
        
        elif data == "edit_create_subgroup":
            # Здесь будет логика редактирования
            await query.edit_message_text("✏️ Редактирование создания подгруппы\n\nЭта функция в разработке...")
        
        # Очищаем временные данные
        context.user_data.pop('subgroup_creation', None)
        return ConversationHandler.END

    # =============================================================================
    # УДАЛЕНИЕ ГРУППЫ
    # =============================================================================

    async def start_delete_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать удаление группы"""
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            await update.message.reply_text("❌ Только для администратора")
            return ConversationHandler.END
        
        all_groups = get_all_groups()
        if not all_groups:
            await update.message.reply_text("📭 В системе нет групп для удаления")
            return ConversationHandler.END
        
        # Инициализируем group_deletion
        context.user_data['group_deletion'] = {
            'user_id': user_id
        }
        
        keyboard = get_groups_keyboard(all_groups)
        await update.message.reply_text(
            "🗑️ *ВЫБЕРИТЕ ГРУППУ ДЛЯ УДАЛЕНИЯ*",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return DELETE_GROUP_SELECT

    async def delete_group_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора группы для удаления"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Проверяем, инициализирован ли group_deletion в user_data
        if 'group_deletion' not in context.user_data:
            context.user_data['group_deletion'] = {}
        
        if data.startswith("select_group_"):
            group_id = data.replace("select_group_", "")
            context.user_data['group_deletion']['group_id'] = group_id
            
            groups_data = get_all_groups()
            group_info = groups_data.get(group_id, {})
            group_name = group_info.get('name', group_id)
            subgroups = group_info.get('subgroups', {})
            
            warning_text = (
                f"⚠️ *ВЫ УВЕРЕНЫ, ЧТО ХОТИТЕ УДАЛИТЬ ГРУППУ?*\n\n"
                f"🏘️ *Группа:* {group_name}\n"
                f"📁 *Подгруппы:* {len(subgroups)}\n"
                f"👥 *Участники:* {len(self._get_users_in_group(group_id))}\n\n"
            )
            
            if subgroups:
                warning_text += f"❌ *ПРИ УДАЛЕНИИ ДАННОЙ ГРУППЫ ВСЕ ПОДГРУППЫ И ШАБЛОНЫ В НИХ ТАКЖЕ УДАЛЯТСЯ!*\n\n"
            
            warning_text += f"🚫 *Это действие нельзя отменить!*"
            
            keyboard = get_confirmation_keyboard("confirm_delete_group", "cancel_delete_group")
            
            await query.edit_message_text(
                warning_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            return DELETE_GROUP_CONFIRM

    async def delete_group_confirmation_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения удаления группы"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Проверяем, инициализирован ли group_deletion в user_data
        if 'group_deletion' not in context.user_data:
            await query.edit_message_text("❌ Ошибка: данные удаления не найдены")
            return ConversationHandler.END
        
        if data == "confirm_delete_group":
            group_data = context.user_data['group_deletion']
            group_id = group_data['group_id']
            
            groups_data = get_all_groups()
            group_name = groups_data.get(group_id, {}).get('name', group_id)
            
            # Удаляем группу
            success = remove_group(group_id)
            
            if success:
                await query.edit_message_text(
                    f"✅ Группа '{group_name}' успешно удалена!",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    f"❌ Ошибка при удалении группы '{group_name}'",
                    parse_mode='Markdown'
                )
        else:
            await query.edit_message_text("❌ Удаление группы отменено")
        
        # Очищаем временные данные
        context.user_data.pop('group_deletion', None)
        return ConversationHandler.END

    # =============================================================================
    # УДАЛЕНИЕ ПОДГРУППЫ
    # =============================================================================

    async def start_delete_subgroup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать удаление подгруппы"""
        user_id = update.effective_user.id
        
        user_role = get_user_role(user_id)
        if user_role not in ["admin", "руководитель"]:
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
            await update.message.reply_text("📭 В доступных группах нет подгрупп для удаления")
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

    async def delete_subgroup_group_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора группы для удаления подгруппы"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Проверяем наличие subgroup_deletion в context.user_data
        if 'subgroup_deletion' not in context.user_data:
            await query.edit_message_text("❌ Ошибка сессии. Пожалуйста, начните заново.")
            return ConversationHandler.END
            
        if data == "back":
            from menu_manager import get_groups_menu
            keyboard = get_groups_menu(query.from_user.id)
            await query.edit_message_text(
                "🏘️ УПРАВЛЕНИЕ ГРУППАМИ",
                reply_markup=keyboard
            )
            return ConversationHandler.END
        
        if data.startswith("select_group_"):
            group_id = data.replace("select_group_", "")
            context.user_data['subgroup_deletion']['group_id'] = group_id
            context.user_data['subgroup_deletion']['step'] = 'select_subgroup'
            
            groups_data = get_all_groups()
            group_info = groups_data.get(group_id, {})
            group_name = group_info.get('name', group_id)
            subgroups = group_info.get('subgroups', {})
            
            if not subgroups:
                await query.edit_message_text(
                    f"❌ В группе '{group_name}' нет подгрупп для удаления",
                    reply_markup=InlineKeyboardMarkup([get_back_button()])
                )
                return ConversationHandler.END
            
            # Создаем клавиатуру с подгруппами
            keyboard = self._get_subgroups_keyboard(subgroups, group_id)
            
            await query.edit_message_text(
                f"📁 *ВЫБЕРИТЕ ПОДГРУППУ ДЛЯ УДАЛЕНИЯ ИЗ ГРУППЫ '{group_name}'*",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            return DELETE_SUBGROUP_SELECT

    def _get_subgroups_keyboard(self, subgroups, group_id):
        """Создать клавиатуру с подгруппами"""
        buttons = []
        for subgroup_id, subgroup_name in subgroups.items():
            buttons.append([
                InlineKeyboardButton(
                    f"📁 {subgroup_name}",
                    callback_data=f"select_subgroup_{group_id}_{subgroup_id}"
                )
            ])
        
        # Добавляем кнопку "Назад"
        buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_groups")])
        
        return InlineKeyboardMarkup(buttons)

    async def delete_subgroup_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора подгруппы для удаления"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Проверяем наличие subgroup_deletion в context.user_data
        if 'subgroup_deletion' not in context.user_data:
            await query.edit_message_text("❌ Ошибка сессии. Пожалуйста, начните заново.")
            return ConversationHandler.END
            
        if data == "back_to_groups":
            # Возвращаемся к выбору группы
            user_id = query.from_user.id
            accessible_groups = get_user_accessible_groups(user_id)
            
            # Фильтруем группы, которые имеют подгруппы
            groups_with_subgroups = {}
            all_groups = get_all_groups()
            for group_id in accessible_groups:
                group_info = all_groups.get(group_id, {})
                subgroups = group_info.get('subgroups', {})
                if subgroups:
                    groups_with_subgroups[group_id] = group_info
            
            keyboard = get_groups_keyboard(groups_with_subgroups)
            await query.edit_message_text(
                "🏘️ *ВЫБЕРИТЕ ГРУППУ ДЛЯ УДАЛЕНИЯ ПОДГРУППЫ*",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            return DELETE_SUBGROUP_GROUP
        
        if data.startswith("select_subgroup_"):
            # Формат: select_subgroup_{group_id}_{subgroup_id}
            parts = data.replace("select_subgroup_", "").split("_")
            if len(parts) >= 2:
                group_id = parts[0]
                subgroup_id = "_".join(parts[1:])  # На случай, если в ID есть подчеркивания
                
                context.user_data['subgroup_deletion']['subgroup_id'] = subgroup_id
                context.user_data['subgroup_deletion']['step'] = 'confirm'
                
                groups_data = get_all_groups()
                group_info = groups_data.get(group_id, {})
                group_name = group_info.get('name', group_id)
                subgroup_name = group_info.get('subgroups', {}).get(subgroup_id, subgroup_id)
                
                warning_text = (
                    f"⚠️ *ВЫ УВЕРЕНЫ, ЧТО ХОТИТЕ УДАЛИТЬ ПОДГРУППУ?*\n\n"
                    f"🏘️ *Группа:* {group_name}\n"
                    f"📁 *Подгруппа:* {subgroup_name}\n\n"
                    f"🚫 *Это действие нельзя отменить!*"
                )
                
                keyboard = get_confirmation_keyboard("confirm_delete_subgroup", "cancel_delete_subgroup")
                
                await query.edit_message_text(
                    warning_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                
                return DELETE_SUBGROUP_CONFIRM

    async def delete_subgroup_confirmation_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения удаления подгруппы"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if 'subgroup_deletion' not in context.user_data:
            await query.edit_message_text("❌ Ошибка: данные удаления не найдены")
            return ConversationHandler.END
        
        if data == "confirm_delete_subgroup":
            subgroup_data = context.user_data['subgroup_deletion']
            group_id = subgroup_data['group_id']
            subgroup_id = subgroup_data['subgroup_id']
            
            groups_data = get_all_groups()
            group_info = groups_data.get(group_id, {})
            group_name = group_info.get('name', group_id)
            subgroup_name = group_info.get('subgroups', {}).get(subgroup_id, subgroup_id)
            
            # Удаляем подгруппу
            success = remove_subgroup(group_id, subgroup_id)
            
            if success:
                await query.edit_message_text(
                    f"✅ Подгруппа '{subgroup_name}' успешно удалена из группы '{group_name}'!",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    f"❌ Ошибка при удалении подгруппы '{subgroup_name}'",
                    parse_mode='Markdown'
                )
        else:
            await query.edit_message_text("❌ Удаление подгруппы отменено")
        
        # Очищаем временные данные
        context.user_data.pop('subgroup_deletion', None)
        return ConversationHandler.END

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
                    "🛠️ Функция групп в разработке",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]])
                )
                
        except Exception as e:
            logging.error(f"❌ Ошибка в обработчике групп: {e}")
            await query.edit_message_text(
                "❌ Ошибка при обработке группы",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]])
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
                response += "📭 *Подгруппы:* Нет\n"
            
            # Показываем участников
            users_in_group = self._get_users_in_group(group_id)
            if users_in_group:
                response += "👥 *Участники:*\n"
                for user_name in users_in_group:
                    response += f"  • {user_name}\n"
            else:
                response += "👥 *Участники:* Нет\n"
            
            from menu_manager import get_back_button
            keyboard = InlineKeyboardMarkup([get_back_button()])
            
            await query.edit_message_text(
                response,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

    async def handle_unexpected_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка неожиданных callback-ов"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "❌ Произошла ошибка. Сессия была сброшена.\n\n"
            "Пожалуйста, начните операцию заново.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]])
        )
        return ConversationHandler.END

    def get_conversation_handler(self):
        """Получить ConversationHandler для групп"""
        return ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex("^📋 Список групп$"), self.show_groups_list),
                MessageHandler(filters.Regex("^➕ Создать группу$"), self.start_create_group),
                MessageHandler(filters.Regex("^📁 Создать подгруппу$"), self.start_create_subgroup),
                MessageHandler(filters.Regex("^🗑️ Удалить группу$"), self.start_delete_group),
                MessageHandler(filters.Regex("^🗑️ Удалить подгруппу$"), self.start_delete_subgroup),
            ],
            states={
                # States for creating group
                CREATE_GROUP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.create_group_name_input)],
                CREATE_GROUP_USERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.create_group_users_input)],
                CREATE_GROUP_CONFIRM: [
                    CallbackQueryHandler(self.create_group_confirmation_handler, pattern="^(confirm_create_group|edit_create_group)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                
                # States for creating subgroup
                CREATE_SUBGROUP_GROUP: [
                    CallbackQueryHandler(self.create_subgroup_group_selected, pattern="^(select_group_|back)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                CREATE_SUBGROUP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.create_subgroup_name_input)],
                CREATE_SUBGROUP_CONFIRM: [
                    CallbackQueryHandler(self.create_subgroup_confirmation_handler, pattern="^(confirm_create_subgroup|edit_create_subgroup)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                
                # States for deleting group
                DELETE_GROUP_SELECT: [
                    CallbackQueryHandler(self.delete_group_selected, pattern="^(select_group_|back)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                DELETE_GROUP_CONFIRM: [
                    CallbackQueryHandler(self.delete_group_confirmation_handler, pattern="^(confirm_delete_group|cancel_delete_group)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                
                # States for deleting subgroup
                DELETE_SUBGROUP_GROUP: [
                    CallbackQueryHandler(self.delete_subgroup_group_selected, pattern="^(select_group_|back)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                DELETE_SUBGROUP_SELECT: [
                    CallbackQueryHandler(self.delete_subgroup_selected, pattern="^(select_subgroup_|back_to_groups)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                DELETE_SUBGROUP_CONFIRM: [
                    CallbackQueryHandler(self.delete_subgroup_confirmation_handler, pattern="^(confirm_delete_subgroup|cancel_delete_subgroup)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_group_operation)],
            name="group_conversation"
        )

    async def cancel_group_operation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена операции с группой"""
        user_id = update.effective_user.id
        
        # Очищаем временные данные
        context.user_data.pop('group_creation', None)
        context.user_data.pop('subgroup_creation', None)
        context.user_data.pop('group_deletion', None)
        context.user_data.pop('subgroup_deletion', None)
        
        from menu_manager import get_main_menu
        await update.message.reply_text(
            "❌ Операция с группой отменена",
            reply_markup=get_main_menu(user_id)
        )
        return ConversationHandler.END

# Глобальный экземпляр менеджера групп
group_manager = GroupManager()
