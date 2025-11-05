from telegram import ReplyKeyboardMarkup

def get_testing_keyboard():
    """Создает меню тестирования"""
    keyboard = [
        ["🚗 Тест Hongqi", "🚙 Тест TurboMatiz"],
        ["🛑 Остановить все тестирования"],
        ["🔙 Главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
