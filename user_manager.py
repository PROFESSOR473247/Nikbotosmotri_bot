# -*- coding: utf-8 -*-
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, CommandHandler

from database import (
    is_authorized, is_admin, get_user_role, get_authorized_users_list,
    add_authorized_user, remove_authorized_user, get_all_groups,
    add_user_to_group, remove_user_from_group, get_user_accessible_groups
)
from menu_manager import (
    get_roles_keyboard, get_test_roles_keyboard, get_groups_keyboard,
    get_confirmation_keyboard, get_back_button, get_users_list_keyboard
)
from user_roles import get_role_name, get_all_roles, get_available_roles_for_assignment

# Состояния для добавления пользователя
ADD_USER_ID, ADD_USER_NAME, ADD_USER_ROLE, ADD_USER_GROUPS, ADD_USER_CONFIRM = range(5)

# Состояния для редактирования пользователя
EDIT_USER_SELECT, EDIT_USER_FIELD, EDIT_USER_ROLE, EDIT_USER_GROUPS, EDIT_USER_CONFIRM = range(5)

# Состояния для удаления пользователя
DELETE_USER_SELECT, DELETE_USER_CONFIRM = range(2)

# Состояния для тестирования прав
TEST_ROLE_SELECT = range(1)

class UserManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def show_users_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню пользователей"""
        user_id = update.effective_user.id
        
        if not is_authorized(user_id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if not is_admin(user_id):
            await update.message.reply_text("❌ Только для администратора")
            return
            
        from menu_manager import get_users_menu
        keyboard = get_users_menu(user_id)
        await update.message.reply_text("👥 УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ", reply_markup=keyboard)

    # =============================================================================
    # ДОБАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯ
    # =============================================================================

    async def start_add_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать добавление нового пользователя"""
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            await update.message.reply_text("❌ Только для администратора")
            return ConversationHandler.END
        
        context.user_data['user_creation'] = {
            'admin_id': user_id
        }
        
        await update.message.reply_text(
            "🆔 *ШАГ 1/4: ВВЕДИТЕ ID ПОЛЬЗОВАТЕЛЯ*\n\n"
            "ℹ️ Пользователь может получить свой ID через команду /my_id в боте",
            parse_mode='Markdown'
        )
        
        return ADD_USER_ID

    async def add_user_id_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода ID пользователя"""
        user_id_input = update.message.text.strip()
        
        try:
            user_id = int(user_id_input)
        except ValueError:
            await update.message.reply_text("❌ ID должен состоять только из цифр. Введите еще раз:")
            return ADD_USER_ID
        
        # Проверяем, не существует ли уже пользователь
        existing_users = get_authorized_users_list()
        if str(user_id) in existing_users:
            await update.message.reply_text("❌ Пользователь с таким ID уже существует. Введите другой ID:")
            return ADD_USER_ID
        
        # Проверяем, не пытаемся ли добавить самого себя
        if user_id == update.effective_user.id:
            await update.message.reply_text("❌ Нельзя добавить самого себя. Введите другой ID:")
            return ADD_USER_ID
        
        context.user_data['user_creation']['new_user_id'] = user_id
        
        await update.message.reply_text(
            "👤 *ШАГ 2/4: ВВЕДИТЕ ИМЯ ПОЛЬЗОВАТЕЛЯ*\n\n"
            "ℹ️ Используйте понятное имя для идентификации",
            parse_mode='Markdown'
        )
        
        return ADD_USER_NAME

    async def add_user_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода имени пользователя"""
        user_name = update.message.text.strip()
        
        if len(user_name) < 2:
            await update.message.reply_text("❌ Имя слишком короткое. Введите еще раз:")
            return ADD_USER_NAME
        
        context.user_data['user_creation']['new_user_name'] = user_name
        
        keyboard = get_roles_keyboard()
        await update.message.reply_text(
            "🎭 *ШАГ 3/4: ВЫБЕРИТЕ УРОВЕНЬ ДОСТУПА*",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return ADD_USER_ROLE

    async def add_user_role_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора роли пользователя"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            await query.edit_message_text(
                "👤 *ШАГ 2/4: ВВЕДИТЕ ИМЯ ПОЛЬЗОВАТЕЛЯ*\n\n"
                "ℹ️ Используйте понятное имя для идентификации",
                parse_mode='Markdown'
            )
            return ADD_USER_NAME
        
        if data.startswith("select_role_"):
            role_key = data.replace("select_role_", "")
            context.user_data['user_creation']['new_user_role'] = role_key
            
            # Получаем список всех групп
            all_groups = get_all_groups()
            if not all_groups:
                await query.edit_message_text("❌ В системе нет групп. Сначала создайте группы.")
                return ConversationHandler.END
            
            # Формируем список групп для выбора
            groups_list = "📋 *СПИСОК ГРУПП:*\n\n"
            group_ids = list(all_groups.keys())
            
            for i, group_id in enumerate(group_ids, 1):
                group_name = all_groups[group_id].get('name', group_id)
                groups_list += f"{i}. {group_name}\n"
            
            groups_list += "\n🔢 *УКАЖИТЕ НОМЕРА ГРУПП ЧЕРЕЗ ЗАПЯТУЮ* (например: 1,3,5)"
            
            context.user_data['user_creation']['all_groups'] = all_groups
            context.user_data['user_creation']['group_ids'] = group_ids
            
            await query.edit_message_text(
                f"🏘️ *ШАГ 4/4: ВЫБЕРИТЕ ГРУППЫ ДОСТУПА*\n\n{groups_list}",
                parse_mode='Markdown'
            )
            
            return ADD_USER_GROUPS

    async def add_user_groups_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода групп доступа"""
        groups_input = update.message.text.strip()
        
        try:
            # Парсим номера групп
            group_numbers = [int(num.strip()) for num in groups_input.split(',')]
        except ValueError:
            await update.message.reply_text("❌ Неверный формат. Используйте номера через запятую (например: 1,3,5):")
            return ADD_USER_GROUPS
        
        all_groups = context.user_data['user_creation']['all_groups']
        group_ids = context.user_data['user_creation']['group_ids']
        
        # Проверяем валидность номеров
        selected_groups = []
        for num in group_numbers:
            if 1 <= num <= len(group_ids):
                group_id = group_ids[num - 1]
                selected_groups.append(group_id)
            else:
                await update.message.reply_text(f"❌ Неверный номер группы: {num}. Введите номера от 1 до {len(group_ids)}:")
                return ADD_USER_GROUPS
        
        if not selected_groups:
            await update.message.reply_text("❌ Не выбрано ни одной группы. Введите номера групп:")
            return ADD_USER_GROUPS
        
        context.user_data['user_creation']['user_groups'] = selected_groups
        
        # Показываем подтверждение
        return await self.show_add_user_confirmation(update, context)

    async def show_add_user_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать подтверждение добавления пользователя"""
        user_data = context.user_data['user_creation']
        
        confirmation_text = self._format_user_confirmation(user_data)
        
        keyboard = get_confirmation_keyboard("confirm_add_user", "cancel_add_user")
        
        await update.message.reply_text(
            confirmation_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return ADD_USER_CONFIRM

    def _format_user_confirmation(self, user_data):
        """Форматирование подтверждения пользователя"""
        text = "✅ *ПОДТВЕРЖДЕНИЕ ДОБАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯ*\n\n"
        
        text += f"🆔 *ID:* {user_data.get('new_user_id')}\n"
        text += f"👤 *Имя:* {user_data.get('new_user_name')}\n"
        text += f"🎭 *Роль:* {get_role_name(user_data.get('new_user_role'))}\n"
        
        all_groups = user_data.get('all_groups', {})
        user_groups = user_data.get('user_groups', [])
        
        text += "🏘️ *Группы доступа:*\n"
        for group_id in user_groups:
            group_name = all_groups.get(group_id, {}).get('name', group_id)
            text += f"  • {group_name}\n"
        
        text += "\n❓ *Все верно?*"
        
        return text

    async def add_user_confirmation_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения добавления пользователя"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "confirm_add_user":
            user_data = context.user_data['user_creation']
            
            # Добавляем пользователя
            success, message = add_authorized_user(
                user_data['new_user_id'],
                user_data['new_user_name'],
                user_data['new_user_role'],
                user_data['user_groups']
            )
            
            if success:
                await query.edit_message_text(
                    f"✅ *{message}*",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    f"❌ *{message}*",
                    parse_mode='Markdown'
                )
        
        else:
            await query.edit_message_text("❌ Добавление пользователя отменено")
        
        # Очищаем временные данные
        context.user_data.pop('user_creation', None)
        return ConversationHandler.END

    # =============================================================================
    # СПИСОК ПОЛЬЗОВАТЕЛЕЙ
    # =============================================================================

    async def show_users_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список пользователей"""
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            await update.message.reply_text("❌ Только для администратора")
            return
        
        users = get_authorized_users_list()
        if not users:
            await update.message.reply_text("📭 *В системе нет пользователей*", parse_mode='Markdown')
            return
        
        users_text = "👥 *СПИСОК ПОЛЬЗОВАТЕЛЕЙ:*\n\n"
        
        for user_id_str, user_data in users.items():
            users_text += f"👤 *{user_data.get('name', 'Без имени')}*\n"
            users_text += f"   🆔 ID: `{user_id_str}`\n"
            users_text += f"   🎭 Роль: {get_role_name(user_data.get('role', 'гость'))}\n"
            
            groups = user_data.get('groups', [])
            if groups:
                groups_text = ", ".join(groups)
                users_text += f"   🏘️ Группы: {groups_text}\n"
            else:
                users_text += f"   🏘️ Группы: Нет\n"
            
            users_text += "───────\n"
        
        await update.message.reply_text(users_text, parse_mode='Markdown')

    # =============================================================================
    # ТЕСТИРОВАНИЕ ПРАВ
    # =============================================================================

    async def start_test_roles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать тестирование прав"""
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            await update.message.reply_text("❌ Только для администратора")
            return
        
        keyboard = get_test_roles_keyboard()
        await update.message.reply_text(
            "🎭 *ВЫБЕРИТЕ РОЛЬ ДЛЯ ТЕСТИРОВАНИЯ*\n\n"
            "ℹ️ Вы временно получите права выбранной роли",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return TEST_ROLE_SELECT

    async def test_role_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора роли для тестирования"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            from menu_manager import get_users_menu
            keyboard = get_users_menu(query.from_user.id)
            await query.edit_message_text(
                "👥 УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ",
                reply_markup=keyboard
            )
            return ConversationHandler.END
        
        if data.startswith("test_role_"):
            role_key = data.replace("test_role_", "")
            
            # Сохраняем тестовую роль
            context.user_data['testing_role'] = role_key
            context.user_data['original_role'] = get_user_role(query.from_user.id)
            
            from menu_manager import get_testing_role_keyboard
            keyboard = get_testing_role_keyboard("admin")
            
            await query.edit_message_text(
                f"🎭 *Теперь вы тестируете роль: {get_role_name(role_key)}*\n\n"
                f"📋 Доступны только функции этой роли.\n"
                f"👑 Для возврата к роли администратора используйте кнопку '👑 Назад к админ' в главном меню.",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            return ConversationHandler.END

    # =============================================================================
    # ОБРАБОТЧИКИ КНОПОК
    # =============================================================================

    async def handle_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки пользователей"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        if not is_authorized(user_id):
            await query.edit_message_text("❌ Недостаточно прав")
            return
        
        if not is_admin(user_id):
            await query.edit_message_text("❌ Только для администратора")
            return
        
        try:
            if data == "back":
                from menu_manager import get_users_menu
                keyboard = get_users_menu(user_id)
                await query.message.reply_text(
                    "👥 УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ",
                    reply_markup=keyboard
                )
                await query.message.delete()
            
            elif data.startswith("select_role_"):
                await self.add_user_role_selected(update, context)
            elif data.startswith("test_role_"):
                await self.test_role_selected(update, context)
            elif data == "confirm_add_user":
                await self.add_user_confirmation_handler(update, context)
            elif data == "cancel_add_user":
                await query.edit_message_text("❌ Добавление пользователя отменено")
                context.user_data.pop('user_creation', None)
                return ConversationHandler.END
            else:
                await query.edit_message_text(
                    "🛠️ *Функция в разработке*",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]]),
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка в обработчике пользователей: {e}")
            await query.edit_message_text(
                "❌ *Ошибка при обработке пользователя*",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]]),
                parse_mode='Markdown'
            )

    def get_conversation_handler(self):
        """Получить ConversationHandler для пользователей"""
        return ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex("^➕ Добавить$"), self.start_add_user),
                MessageHandler(filters.Regex("^📋 Список пользователей$"), self.show_users_list),
                MessageHandler(filters.Regex("^🧪 Тест прав$"), self.start_test_roles),
            ],
            states={
                # States for adding user
                ADD_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_user_id_input)],
                ADD_USER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_user_name_input)],
                ADD_USER_ROLE: [CallbackQueryHandler(self.add_user_role_selected, pattern="^(select_role_|back)")],
                ADD_USER_GROUPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_user_groups_input)],
                ADD_USER_CONFIRM: [CallbackQueryHandler(self.add_user_confirmation_handler, pattern="^(confirm_add_user|cancel_add_user)")],
                
                # States for testing roles
                TEST_ROLE_SELECT: [CallbackQueryHandler(self.test_role_selected, pattern="^(test_role_|back)")],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_user_operation)],
            name="user_conversation"
        )

    async def cancel_user_operation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена операции с пользователем"""
        user_id = update.effective_user.id
        
        # Очищаем временные данные
        context.user_data.pop('user_creation', None)
        context.user_data.pop('user_edit', None)
        context.user_data.pop('user_delete', None)
        
        from menu_manager import get_main_menu
        await update.message.reply_text(
            "❌ Операция с пользователем отменена",
            reply_markup=get_main_menu(user_id)
        )
        return ConversationHandler.END

# Глобальный экземпляр менеджера пользователей
user_manager = UserManager()
