import os
from dotenv import load_dotenv

load_dotenv()

# Токен из переменных окружения (безопасно)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8373568269:AAGSBjS57tRHXumLRPWBAe2lUeFq7NNzhl0")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Убедитесь, что переменная окружения установлена.")
