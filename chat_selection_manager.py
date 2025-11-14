import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from user_chat_manager import user_chat_manager

logger = logging.getLogger(__name__)

class ChatSelectionManager:
    def __init__(self):
        pass
    
    def get_user_accessible_chats_for_selection(self, user_id):
        """Возвращает чаты, доступные пользователю, в формате для выбора"""
        accessible_chats = user_chat_manager.get_user_chat_access(user_id)
        
        if not accessible_chats:
            return None, "❌ У вас нет доступа ни к одному Telegram чату"
        
        formatted_chats = []
        for i, chat in enumerate(accessible_chats, 1):
            formatted_chats.append(f"{i}. {chat['chat_name']} (ID: {chat['chat_id']})")
        
        message = "💬 **Выберите Telegram чат для отправки:**\n\n"
        message += "\n".join(formatted_chats)
        message += "\n\nВведите номер чата:"
        
        return accessible_chats, message
    
    def validate_chat_selection(self, user_input, accessible_chats):
        """Проверяет выбор чата пользователем"""
        try:
            chat_number = int(user_input)
            if 1 <= chat_number <= len(accessible_chats):
                return True, accessible_chats[chat_number - 1]
            else:
                return False, "❌ Неверный номер чата. Введите номер из списка:"
        except ValueError:
            return False, "❌ Пожалуйста, введите номер чата (цифру):"
    
    async def handle_chat_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, next_state):
        """Обрабатывает выбор чата пользователем"""
        user_id = update.effective_user.id
        user_text = update.message.text
        
        # Если нажата кнопка "Назад"
        if user_text == "🔙 Назад":
            return await self.go_back_to_template_selection(update, context)
        
        accessible_chats = context.user_data.get('accessible_chats')
        if not accessible_chats:
            # Если чаты не загружены, загружаем заново
            accessible_chats, message = self.get_user_accessible_chats_for_selection(user_id)
            if not accessible_chats:
                await update.message.reply_text(
                    message,
                    reply_markup=self.get_back_keyboard()
                )
                return next_state - 1  # Возвращаемся к предыдущему состоянию
            context.user_data['accessible_chats'] = accessible_chats
        
        # Проверяем выбор пользователя
        is_valid, result = self.validate_chat_selection(user_text, accessible_chats)
        
        if not is_valid:
            await update.message.reply_text(
                result,
                reply_markup=self.get_back_keyboard()
            )
            return next_state - 1  # Остаемся в том же состоянии
        
        # Сохраняем выбранный чат
        selected_chat = result
        context.user_data['task_creation']['target_chat_id'] = selected_chat['chat_id']
        context.user_data['task_creation']['target_chat_name'] = selected_chat['chat_name']
        
        # Переходим к подтверждению
        from task_handlers import format_task_confirmation
        task_data = context.user_data['task_creation']
        template = task_data['template']
        info = format_task_confirmation(template, selected_chat['chat_name'])
        
        await update.message.reply_text(
            info,
            parse_mode='Markdown',
            reply_markup=self.get_task_confirmation_keyboard()
        )
        return next_state  # Переходим к следующему состоянию
    
    async def go_back_to_template_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возврат к выбору шаблона"""
        group_id = context.user_data['task_creation']['group']
        from template_manager import get_templates_by_group
        templates = get_templates_by_group(group_id)
        
        keyboard = []
        for template_id, template in templates:
            keyboard.append([f"📝 {template['name']}"])
        keyboard.append(["🔙 Назад"])
        
        await update.message.reply_text(
            "🔄 **Выберите шаблон:**",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        
        # Возвращаем состояние выбора шаблона
        from task_handlers import CREATE_TASK_SELECT, TEST_TASK_SELECT
        if context.user_data['task_creation'].get('is_test'):
            return TEST_TASK_SELECT
        else:
            return CREATE_TASK_SELECT
    
    def get_back_keyboard(self):
        """Клавиатура с кнопкой назад"""
        keyboard = [["🔙 Назад"]]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def get_task_confirmation_keyboard(self):
        """Клавиатура подтверждения задачи"""
        keyboard = [
            ["✅ Подтвердить", "✏️ Изменить"],
            ["🔙 Назад"]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Глобальный экземпляр
chat_selection_manager = ChatSelectionManager()