from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from authorized_users import add_user, get_user_role, is_admin
from database import add_user_to_group, set_user_role, get_all_users, load_groups, get_user_accessible_groups
from menu_manager import get_days_keyboard, get_frequency_keyboard, get_edit_template_keyboard, get_image_options_keyboard, get_confirmation_keyboard, get_main_menu
import logging
from datetime import datetime

# States for various conversations
ADD_USER_ID, ADD_USER_NAME, ADD_USER_ROLE, ADD_USER_GROUPS = range(4)
CREATE_TEMPLATE_GROUP, CREATE_TEMPLATE_SUBGROUP, CREATE_TEMPLATE_NAME = range(4, 7)
CREATE_TEMPLATE_IMAGE, CREATE_TEMPLATE_TIME, CREATE_TEMPLATE_DAY = range(7, 10)
CREATE_TEMPLATE_FREQUENCY, CREATE_TEMPLATE_CONFIRM = range(10, 12)

async def start_add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the process of adding a user"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Только администраторы могут добавлять пользователей.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "👥 ДОБАВЛЕНИЕ НОВОГО ПОЛЬЗОВАТЕЛЯ\n\n"
        "Пожалуйста, введите ID пользователя:",
        reply_markup=ReplyKeyboardRemove()
    )
    return ADD_USER_ID

async def process_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the user ID"""
    user_id_text = update.message.text
    
    # Validate user ID
    if not user_id_text.isdigit():
        await update.message.reply_text("❌ ID пользователя должен быть числом. Пожалуйста, попробуйте снова:")
        return ADD_USER_ID
    
    context.user_data['new_user_id'] = user_id_text
    
    await update.message.reply_text(
        "✅ ID пользователя принят.\n\n"
        "Теперь введите имя пользователя:"
    )
    return ADD_USER_NAME

async def process_user_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the user name"""
    user_name = update.message.text
    context.user_data['new_user_name'] = user_name
    
    # Show role selection keyboard
    keyboard = [["Админ", "Руководитель"], ["Водитель", "Гость"]]
    await update.message.reply_text(
        "✅ Имя пользователя принято.\n\n"
        "Теперь выберите роль пользователя:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ADD_USER_ROLE

async def process_user_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the user role"""
    user_role = update.message.text
    role_mapping = {
        "Админ": "admin",
        "Руководитель": "руководитель", 
        "Водитель": "водитель",
        "Гость": "гость"
    }
    
    if user_role not in role_mapping:
        await update.message.reply_text("❌ Неверная роль. Пожалуйста, выберите из клавиатуры:")
        return ADD_USER_ROLE
    
    context.user_data['new_user_role'] = role_mapping[user_role]
    
    # Show groups for selection
    groups_data = load_groups()
    groups_list = list(groups_data.get("groups", {}).items())
    
    if not groups_list:
        await update.message.reply_text(
            "❌ Нет доступных групп. Сначала создайте группы.",
            reply_markup=get_main_menu(update.effective_user.id)
        )
        return ConversationHandler.END
    
    # Create groups selection message
    groups_text = "🏘️ ДОСТУПНЫЕ ГРУППЫ:\n\n"
    for i, (group_id, group_info) in enumerate(groups_list, 1):
        groups_text += f"{i}. {group_info.get('title', f'Группа {group_id}')}\n"
    
    groups_text += "\nВведите номера групп через запятую (например, 1,3):"
    
    await update.message.reply_text(
        groups_text,
        reply_markup=ReplyKeyboardRemove()
    )
    return ADD_USER_GROUPS

async def process_user_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the user groups"""
    groups_text = update.message.text
    
    user_id = context.user_data['new_user_id']
    user_name = context.user_data['new_user_name']
    user_role = context.user_data['new_user_role']
    
    groups_data = load_groups()
    groups_list = list(groups_data.get("groups", {}).items())
    
    selected_groups = []
    try:
        group_numbers = [int(num.strip()) for num in groups_text.split(',')]
        for num in group_numbers:
            if 1 <= num <= len(groups_list):
                group_id = groups_list[num-1][0]
                selected_groups.append(group_id)
    except:
        await update.message.reply_text(
            "❌ Неверный ввод. Пожалуйста, введите номера через запятую:",
            reply_markup=ReplyKeyboardRemove()
        )
        return ADD_USER_GROUPS
    
    # Add the user
    success, message = add_user(user_id, user_name, user_role, selected_groups)
    
    if success:
        await update.message.reply_text(
            f"✅ Пользователь успешно добавлен!\n\n{message}",
            reply_markup=get_main_menu(update.effective_user.id)
        )
    else:
        await update.message.reply_text(
            f"❌ Ошибка добавления пользователя: {message}",
            reply_markup=get_main_menu(update.effective_user.id)
        )
    
    return ConversationHandler.END

async def cancel_add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the add user process"""
    await update.message.reply_text(
        "❌ Добавление пользователя отменено.",
        reply_markup=get_main_menu(update.effective_user.id)
    )
    return ConversationHandler.END

# Template creation conversation
async def start_create_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start template creation process"""
    user_id = update.effective_user.id
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ Нет доступных групп.",
            reply_markup=get_main_menu(user_id)
        )
        return ConversationHandler.END
    
    # Create groups selection keyboard
    keyboard = []
    for group_id, group_info in accessible_groups.items():
        keyboard.append([f"🏘️ {group_info.get('title', f'Группа {group_id}')}"])
    
    keyboard.append(["🔙 Отмена"])
    
    await update.message.reply_text(
        "📝 СОЗДАНИЕ НОВОГО ШАБЛОНА\n\n"
        "Шаг 1: Выберите группу:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return CREATE_TEMPLATE_GROUP

async def process_template_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process template group selection"""
    group_text = update.message.text
    
    if group_text == "🔙 Отмена":
        await update.message.reply_text(
            "Создание шаблона отменено.",
            reply_markup=get_main_menu(update.effective_user.id)
        )
        return ConversationHandler.END
    
    user_id = update.effective_user.id
    
    # Extract group ID from selection
    accessible_groups = get_user_accessible_groups(user_id)
    selected_group = None
    
    for group_id, group_info in accessible_groups.items():
        if group_text.endswith(group_info.get('title', f'Группа {group_id}')):
            selected_group = group_id
            break
    
    if not selected_group:
        await update.message.reply_text("❌ Неверный выбор группы. Пожалуйста, попробуйте снова:")
        return CREATE_TEMPLATE_GROUP
    
    context.user_data['template_group'] = selected_group
    context.user_data['template_group_name'] = group_text.replace("🏘️ ", "")
    
    await update.message.reply_text(
        "✅ Группа выбрана.\n\n"
        "Шаг 2: Введите название шаблона:",
        reply_markup=ReplyKeyboardRemove()
    )
    return CREATE_TEMPLATE_NAME

async def process_template_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process template name"""
    template_name = update.message.text
    context.user_data['template_name'] = template_name
    
    await update.message.reply_text(
        "✅ Название шаблона сохранено.\n\n"
        "Шаг 3: Добавить изображение (опционально):",
        reply_markup=get_image_options_keyboard()
    )
    return CREATE_TEMPLATE_IMAGE

async def process_template_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process template image"""
    if update.message.text == "⏭️ Пропустить":
        context.user_data['template_image'] = None
        await update.message.reply_text(
            "✅ Шаг с изображением пропущен.\n\n"
            "Шаг 4: Введите время активации (ЧЧ:ММ, московское время):",
            reply_markup=ReplyKeyboardRemove()
        )
        return CREATE_TEMPLATE_TIME
    elif update.message.text == "📎 Прикрепить изображение":
        await update.message.reply_text(
            "Пожалуйста, отправьте изображение:",
            reply_markup=ReplyKeyboardMarkup([["🔙 Назад"]], resize_keyboard=True)
        )
        return CREATE_TEMPLATE_IMAGE
    elif update.message.text == "🔙 Назад":
        await update.message.reply_text(
            "Шаг 2: Введите название шаблона:",
            reply_markup=ReplyKeyboardRemove()
        )
        return CREATE_TEMPLATE_NAME
    else:
        # Handle image file
        if update.message.photo:
            # For now, just acknowledge the image
            context.user_data['template_image'] = "image_received"
            await update.message.reply_text(
                "✅ Изображение получено.\n\n"
                "Шаг 4: Введите время активации (ЧЧ:ММ, московское время):",
                reply_markup=ReplyKeyboardRemove()
            )
            return CREATE_TEMPLATE_TIME
        else:
            await update.message.reply_text(
                "Пожалуйста, используйте кнопки или отправьте изображение:",
                reply_markup=get_image_options_keyboard()
            )
            return CREATE_TEMPLATE_IMAGE

async def process_template_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process template time"""
    if update.message.text == "🔙 Назад":
        await update.message.reply_text(
            "Шаг 3: Добавить изображение (опционально):",
            reply_markup=get_image_options_keyboard()
        )
        return CREATE_TEMPLATE_IMAGE
    
    time_text = update.message.text
    
    # Validate time format
    try:
        hours, minutes = map(int, time_text.split(':'))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError
        context.user_data['template_time'] = time_text
    except:
        await update.message.reply_text("❌ Неверный формат времени. Пожалуйста, используйте формат ЧЧ:ММ:")
        return CREATE_TEMPLATE_TIME
    
    await update.message.reply_text(
        "✅ Время сохранено.\n\n"
        "Шаг 5: Выберите день недели:",
        reply_markup=get_days_keyboard()
    )
    return CREATE_TEMPLATE_DAY

async def process_template_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process template day"""
    day_text = update.message.text
    valid_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    
    if day_text not in valid_days:
        await update.message.reply_text("❌ Неверный день. Пожалуйста, выберите из клавиатуры:")
        return CREATE_TEMPLATE_DAY
    
    if day_text == "🔙 Назад":
        await update.message.reply_text(
            "Шаг 4: Введите время активации (ЧЧ:ММ, московское время):",
            reply_markup=ReplyKeyboardRemove()
        )
        return CREATE_TEMPLATE_TIME
    
    day_mapping = {"Пн": 0, "Вт": 1, "Ср": 2, "Чт": 3, "Пт": 4, "Сб": 5, "Вс": 6}
    context.user_data['template_day'] = day_mapping[day_text]
    context.user_data['template_day_name'] = day_text
    
    await update.message.reply_text(
        "✅ День выбран.\n\n"
        "Шаг 6: Выберите периодичность:",
        reply_markup=get_frequency_keyboard()
    )
    return CREATE_TEMPLATE_FREQUENCY

async def process_template_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process template frequency"""
    frequency = update.message.text
    valid_frequencies = ["2 в неделю", "1 в неделю", "2 в месяц", "1 в месяц"]
    
    if frequency not in valid_frequencies:
        await update.message.reply_text("❌ Неверная периодичность. Пожалуйста, выберите из клавиатуры:")
        return CREATE_TEMPLATE_FREQUENCY
    
    if frequency == "🔙 Назад":
        await update.message.reply_text(
            "Шаг 5: Выберите день недели:",
            reply_markup=get_days_keyboard()
        )
        return CREATE_TEMPLATE_DAY
    
    context.user_data['template_frequency'] = frequency
    
    # Show confirmation
    confirmation_text = (
        "📋 ПОДТВЕРЖДЕНИЕ ШАБЛОНА\n\n"
        f"🏘️ Группа: {context.user_data.get('template_group_name', 'Н/Д')}\n"
        f"📝 Название: {context.user_data.get('template_name', 'Н/Д')}\n"
        f"🕒 Время: {context.user_data.get('template_time', 'Н/Д')}\n"
        f"📅 День: {context.user_data.get('template_day_name', 'Н/Д')}\n"
        f"🔄 Периодичность: {frequency}\n"
        f"🖼️ Изображение: {'Да' if context.user_data.get('template_image') else 'Нет'}\n\n"
        "Пожалуйста, подтвердите:"
    )
    
    await update.message.reply_text(
        confirmation_text,
        reply_markup=get_confirmation_keyboard()
    )
    return CREATE_TEMPLATE_CONFIRM

async def process_template_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process template confirmation"""
    choice = update.message.text
    
    if choice == "✅ Да":
        # Save template to database
        template_id = f"template_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        template_data = {
            "name": context.user_data.get('template_name'),
            "group": context.user_data.get('template_group'),
            "time": context.user_data.get('template_time'),
            "day": context.user_data.get('template_day'),
            "frequency": context.user_data.get('template_frequency'),
            "image": context.user_data.get('template_image'),
            "created_at": datetime.now().isoformat(),
            "created_by": update.effective_user.id
        }
        
        # Here you would save to database
        # For now, just confirm
        await update.message.reply_text(
            "✅ Шаблон успешно создан!",
            reply_markup=get_main_menu(update.effective_user.id)
        )
        return ConversationHandler.END
        
    elif choice == "✏️ Изменить":
        await update.message.reply_text(
            "Какой пункт вы хотите изменить?",
            reply_markup=get_edit_template_keyboard()
        )
        return CREATE_TEMPLATE_CONFIRM
    elif choice == "❌ Нет":
        await update.message.reply_text(
            "Создание шаблона отменено.",
            reply_markup=get_main_menu(update.effective_user.id)
        )
        return ConversationHandler.END
    elif choice == "🔙 Назад":
        await update.message.reply_text(
            "Шаг 6: Выберите периодичность:",
            reply_markup=get_frequency_keyboard()
        )
        return CREATE_TEMPLATE_FREQUENCY
    else:
        await update.message.reply_text(
            "Пожалуйста, используйте кнопки для выбора:",
            reply_markup=get_confirmation_keyboard()
        )
        return CREATE_TEMPLATE_CONFIRM

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel any conversation"""
    await update.message.reply_text(
        "Действие отменено.",
        reply_markup=get_main_menu(update.effective_user.id)
    )
    return ConversationHandler.END

# Conversation handler for adding users
add_user_conversation = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^➕ Добавить$"), start_add_user)],
    states={
        ADD_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_user_id)],
        ADD_USER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_user_name)],
        ADD_USER_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_user_role)],
        ADD_USER_GROUPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_user_groups)],
    },
    fallbacks=[MessageHandler(filters.Regex("^🔙"), cancel_conversation)]
)

# Conversation handler for creating templates
create_template_conversation = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^➕ Добавить новый$"), start_create_template)],
    states={
        CREATE_TEMPLATE_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_template_group)],
        CREATE_TEMPLATE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_template_name)],
        CREATE_TEMPLATE_IMAGE: [MessageHandler(filters.TEXT | filters.PHOTO, process_template_image)],
        CREATE_TEMPLATE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_template_time)],
        CREATE_TEMPLATE_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_template_day)],
        CREATE_TEMPLATE_FREQUENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_template_frequency)],
        CREATE_TEMPLATE_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_template_confirmation)],
    },
    fallbacks=[MessageHandler(filters.Regex("^🔙"), cancel_conversation)]
)
