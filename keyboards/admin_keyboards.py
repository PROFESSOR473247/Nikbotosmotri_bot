from telegram import ReplyKeyboardMarkup

def get_admin_main_keyboard():
    """Главное меню администрирования"""
    keyboard = [
        ["👥 Пользователи", "💬 Тг чаты"],
        ["🔧 Тест прав", "📋 Справка"],
        ["🔙 Главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_users_management_keyboard():
    """Меню управления пользователями"""
    keyboard = [
        ["➕ Добавить пользователя", "✏️ Изменить доступ"],
        ["📋 Список пользователей", "🗑️ Удалить пользователя"],
        ["🔙 К администрированию"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_chats_management_keyboard():
    """Меню управления Telegram чатами"""
    keyboard = [
        ["➕ Добавить чат", "✏️ Изменить доступ"],
        ["📋 Список чатов", "🗑️ Удалить чат"],
        ["🔙 К администрированию"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_user_edit_keyboard():
    """Меню редактирования пользователя"""
    keyboard = [
        ["👑 Изменить должность", "📝 Группы шаблонов"],
        ["💬 Telegram чаты", "✅ Завершить редактирование"],
        ["🔙 К пользователям"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_chat_edit_keyboard():
    """Меню редактирования чата"""
    keyboard = [
        ["👥 Добавить пользователя", "🚫 Исключить пользователя"],
        ["✅ Завершить редактирование"],
        ["🔙 К чатам"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_roles_keyboard():
    """Клавиатура выбора ролей"""
    keyboard = [
        ["👑 Руководитель", "🚗 Водитель"],
        ["👥 Гость", "🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_keep_name_keyboard():
    """Клавиатура для сохранения названия чата"""
    keyboard = [
        ["✅ Оставить название", "✏️ Ввести новое"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_confirmation_keyboard():
    """Клавиатура подтверждения"""
    keyboard = [
        ["✅ Да", "❌ Нет"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_back_keyboard():
    """Простая кнопка назад"""
    keyboard = [
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
