import os
from dotenv import load_dotenv

load_dotenv()

# Получаем токен из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Если токен не найден, используем запасной вариант
if not BOT_TOKEN:
    BOT_TOKEN = "8373568269:AAGSBjS57tRHXumLRPWBAe2lUeFq7NNzhl0"  # ЗАМЕНИТЕ НА ВАШ ТОКЕН
    print("⚠️  BOT_TOKEN не найден в переменных окружения, используется значение по умолчанию")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не настроен! Установите переменную окружения BOT_TOKEN.")

print("✅ BOT_TOKEN загружен успешно")
