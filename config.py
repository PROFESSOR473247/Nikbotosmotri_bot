import os
from dotenv import load_dotenv

load_dotenv()

# Токен из переменных окружения (безопасно)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8373568269:AAGSBjS57tRHXumLRPWBAe2lUeFq7NNzhl0")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Убедитесь, что переменная окружения установлена.")

# Настройки базы данных
DATABASE_URL = os.environ.get('DATABASE_URL')

# Настройки доступа (ВРЕМЕННО ОТКЛЮЧЕНО)
REQUIRE_AUTHORIZATION = False  # Все пользователи имеют доступ
ADMIN_USER_ID = 812934047

# Настройки времени
TIMEZONE = 'Europe/Moscow'

print("⚙️ Конфигурация загружена:")
print(f"   • REQUIRE_AUTHORIZATION: {REQUIRE_AUTHORIZATION}")
print(f"   • ADMIN_USER_ID: {ADMIN_USER_ID}")