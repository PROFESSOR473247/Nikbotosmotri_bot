import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    JobQueue  # ← ДОБАВЛЕНО ЗДЕСЬ
)
from config import BOT_TOKEN
from authorized_users import is_authorized, is_admin, add_user, remove_user, get_users_list, get_admin_id
import datetime
import pytz
from datetime import timedelta
import sys
import os

# Принудительно перезагружаем модуль templates
if 'templates' in sys.modules:
    del sys.modules['templates']

# Импортируем шаблоны
TEMPLATES = {}
try:
    from templates import TEMPLATES as IMPORTED_TEMPLATES
    TEMPLATES = IMPORTED_TEMPLATES

    print("✅ Шаблоны загружены успешно")

    # Проверяем наличие обязательных шаблонов
    required_templates = ['hongqi_template1', 'hongqi_template2', 'turbomatiz_template1', 'turbomatiz_template2',
                          'turbomatiz_template3']
    missing_templates = []

    for template in required_templates:
        if template not in TEMPLATES:
            missing_templates.append(template)

    if missing_templates:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Отсутствуют шаблоны: {missing_templates}")
        print("❌ Проверьте файл templates.py")
        exit(1)

    print(f"🔧 Загруженные шаблоны: {list(TEMPLATES.keys())}")

except ImportError as import_error:
    print(f"❌ Ошибка загрузки шаблонов: {import_error}")
    print("❌ Создайте файл templates.py с необходимыми шаблонами!")
    exit(1)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Храним активные задания для каждого чата
active_jobs = {}
test_jobs = {}


async def send_template_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, template_name: str):
    """Отправляет сообщение по шаблону с изображением"""
    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M:%S")
    print(f"📨 [{current_time}] Отправка {template_name} в чат {chat_id}")

    try:
        # Для turbomatiz_template3 проверяем четность недели (раз в 2 недели)
        if template_name == 'turbomatiz_template3':
            week_number = datetime.datetime.now().isocalendar()[1]
            if week_number % 2 != 0:  # Отправляем только по четным неделям
                print(f"⏭️ Пропуск отправки {template_name} (нечетная неделя)")
                return

        template_data = TEMPLATES[template_name]

        # Проверяем структуру данных
        if isinstance(template_data, dict):
            text = template_data["text"]
            image_path = template_data.get("image")
        else:
            # Для обратной совместимости, если шаблон - просто строка
            text = template_data
            image_path = None

        print(f"🔍 Текст для отправки: {text[:100]}...")
        print(f"🔍 Путь к изображению: {image_path}")

        # ДИАГНОСТИКА: добавляем информацию о путях
        if image_path:
            absolute_path = os.path.abspath(image_path)
            print(f"🔍 Абсолютный путь к изображению: {absolute_path}")
            print(f"🔍 Файл существует: {os.path.exists(absolute_path)}")
            if os.path.exists(absolute_path):
                print(f"🔍 Размер файла: {os.path.getsize(absolute_path)} байт")

        if image_path and os.path.exists(image_path):
            print(f"🖼️ Отправка с изображением: {image_path}")
            try:
                # Отправляем изображение с подписью
                with open(image_path, 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=text
                    )
                print(f"✅ [{current_time}] {template_name} с изображением отправлен в чат {chat_id}")
            except Exception as img_error:
                print(f"❌ Ошибка отправки изображения: {img_error}")
                # Отправляем только текст если изображение не загружается
                await context.bot.send_message(chat_id, text=text)
                print(f"✅ [{current_time}] {template_name} отправлен в чат {chat_id} (только текст)")
        else:
            if image_path:
                print(f"⚠️ Изображение не найдено: {image_path}")
            # Если изображения нет, отправляем только текст
            await context.bot.send_message(chat_id, text=text)
            print(f"✅ [{current_time}] {template_name} отправлен в чат {chat_id} (только текст)")

    except Exception as send_error:
        print(f"❌ [{current_time}] Ошибка отправки {template_name}: {send_error}")


async def send_test_template_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, template_name: str):
    """Отправляет тестовое сообщение по шаблону с изображением"""
    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M:%S")
    print(f"🧪 [{current_time}] Тестовая отправка {template_name} в чат {chat_id}")

    try:
        template_data = TEMPLATES[template_name]

        if isinstance(template_data, dict):
            text = template_data["text"]
            image_path = template_data.get("image")
        else:
            text = template_data
            image_path = None

        print(f"🔍 Текст для тестовой отправки: {text[:100]}...")
        print(f"🔍 Путь к изображению: {image_path}")

        # ДИАГНОСТИКА: добавляем информацию о путях
        if image_path:
            absolute_path = os.path.abspath(image_path)
            print(f"🔍 Абсолютный путь к изображению: {absolute_path}")
            print(f"🔍 Файл существует: {os.path.exists(absolute_path)}")
            if os.path.exists(absolute_path):
                print(f"🔍 Размер файла: {os.path.getsize(absolute_path)} байт")

        if image_path and os.path.exists(image_path):
            print(f"🖼️ Тестовая отправка с изображением: {image_path}")
            try:
                with open(image_path, 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=text
                    )
                print(f"✅ [{current_time}] Тест {template_name} с изображением отправлен в чат {chat_id}")
            except Exception as img_error:
                print(f"❌ Ошибка отправки изображения: {img_error}")
                await context.bot.send_message(chat_id, text=text)
                print(f"✅ [{current_time}] Тест {template_name} отправлен в чат {chat_id} (только текст)")
        else:
            if image_path:
                print(f"⚠️ Изображение для теста не найдено: {image_path}")
            await context.bot.send_message(chat_id, text=text)
            print(f"✅ [{current_time}] Тест {template_name} отправлен в чат {chat_id} (только текст)")

        # Удаляем задание из тестовых после выполнения
        if chat_id in test_jobs and template_name in test_jobs[chat_id]:
            del test_jobs[chat_id][template_name]

    except Exception as test_error:
        print(f"❌ [{current_time}] Ошибка тестовой отправки {template_name}: {test_error}")


# Состояния для ConversationHandler
ADD_USER_ID, ADD_USER_NAME = range(2)


# Декоратор для проверки авторизации
def authorization_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not is_authorized(user_id):
            await update.message.reply_text(
                "❌ У ВАС НЕДОСТАТОЧНО ПРАВ\n\n"
                "Для доступа к функциям бота обратитесь к администратору",
                reply_markup=get_unauthorized_keyboard()
            )
            print(f"🚫 Неавторизованный доступ от user_id: {user_id} к функции: {func.__name__}")
            return None
        return await func(update, context, *args, **kwargs)

    return wrapper


# Декоратор для проверки прав администратора
def admin_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            await update.message.reply_text(
                "❌ Эта функция доступна только администратору",
                reply_markup=get_main_keyboard()
            )
            print(f"🚫 Попытка доступа к админ-функции от user_id: {user_id}")
            return None
        return await func(update, context, *args, **kwargs)

    return wrapper


def get_main_keyboard():
    """Создает главное меню для авторизованных пользователей"""
    keyboard = [
        ["📋 Шаблоны"],
        ["🧪 Тестирование"],
        ["⚙️ ЕЩЕ"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, input_field_placeholder="Выберите раздел...")


def get_unauthorized_keyboard():
    """Создает меню для неавторизованных пользователей"""
    keyboard = [
        ["🆔 Получить ID"],
        ["📋 Справка"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True,
                               input_field_placeholder="Для доступа обратитесь к администратору")


def get_templates_keyboard():
    """Создает меню выбора бренда"""
    keyboard = [
        ["🚗 Осмотры Hongqi", "🚙 Осмотры TurboMatiz"],
        ["🔙 Главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_hongqi_keyboard():
    """Создает меню Hongqi"""
    keyboard = [
        ["🔍 Дистанционный осмотр Н5", "⏰ Напоминание осмотра Н5"],
        ["🛑 Остановить все шаблоны Hongqi"],
        ["🔙 К выбору бренда", "🔙 Главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_turbomatiz_keyboard():
    """Создает меню TurboMatiz"""
    keyboard = [
        ["💳 Оплата", "🔍 Осмотр"],
        ["🧼 Чистый кузов"],
        ["🛑 Остановить все шаблоны TurboMatiz"],
        ["🔙 К выбору бренда", "🔙 Главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_testing_keyboard():
    """Создает меню тестирования"""
    keyboard = [
        ["🚗 Тест Hongqi", "🚙 Тест TurboMatiz"],
        ["🛑 Остановить все тестирования"],
        ["🔙 Главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_test_hongqi_keyboard():
    """Создает меню тестирования Hongqi"""
    keyboard = [
        ["🔍 Тест осмотр Н5", "⏰ Тест напоминание Н5"],
        ["🔙 К тестированию", "🔙 Главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_test_turbomatiz_keyboard():
    """Создает меню тестирования TurboMatiz"""
    keyboard = [
        ["💳 Тест оплата", "🔍 Тест осмотр"],
        ["🧼 Тест чистый кузов"],
        ["🔙 К тестированию", "🔙 Главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_more_keyboard(user_id):
    """Создает меню дополнительных функций"""
    keyboard = [
        ["📊 Статус команд", "🕒 Текущее время"],
        ["🆔 Мой ID"]
    ]

    # Добавляем кнопку управления пользователями только для администратора
    if is_admin(user_id):
        keyboard.append(["👥 Управление пользователями"])

    keyboard.append(["🔙 Главное меню"])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_user_management_keyboard():
    """Создает меню управления пользователями"""
    keyboard = [
        ["➕ Добавить пользователя", "➖ Удалить пользователя"],
        ["📋 Список пользователей"],
        ["🔙 Назад к ЕЩЕ"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_remove_user_keyboard():
    """Создает клавиатуру для удаления пользователей"""
    users = get_users_list()
    admin_id = get_admin_id()

    keyboard = []
    for user_id_str, username in users.items():
        user_id = int(user_id_str)
        # Пропускаем администратора
        if user_id == admin_id:
            continue
        keyboard.append([f"❌ {username} (ID: {user_id})"])

    keyboard.append(["🔙 Назад к управлению"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_confirmation_keyboard(user_id):
    """Создает клавиатуру подтверждения удаления"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_remove_{user_id}"),
            InlineKeyboardButton("❌ Нет, отмена", callback_data="cancel_remove")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_to_management_keyboard():
    """Создает кнопку возврата к управлению пользователями"""
    keyboard = [["🔙 Назад к управлению"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def moscow_to_utc(time_str):
    """Конвертирует время из московского в UTC"""
    try:
        hours, minutes = map(int, time_str.split(':'))
        moscow_tz = pytz.timezone('Europe/Moscow')
        now = datetime.datetime.now(moscow_tz)
        moscow_time = moscow_tz.localize(datetime.datetime(now.year, now.month, now.day, hours, minutes))
        utc_time = moscow_time.astimezone(pytz.utc)
        return utc_time.time()
    except Exception as time_error:
        raise ValueError(f"Ошибка конвертации времени: {time_error}")


def format_time_delta(delta):
    """Форматирует разницу времени в читаемый вид"""
    if delta.total_seconds() < 0:
        return "уже прошло"

    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days} дн")
    if hours > 0:
        parts.append(f"{hours} час")
    if minutes > 0:
        parts.append(f"{minutes} мин")
    if seconds > 0 and days == 0 and hours == 0:
        parts.append(f"{seconds} сек")

    return " ".join(parts) if parts else "менее секунды"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M:%S")

    # Проверяем авторизацию
    if not is_authorized(user_id):
        welcome_text = (
            f'🤖 БОТ С МНОГОУРОВНЕВЫМ МЕНЮ\n'
            f'Текущее время: {current_time} (МСК)\n'
            f'ID чата: {chat_id}\n'
            f'Ваш ID: {user_id}\n\n'
            '❌ У ВАС НЕДОСТАТОЧНО ПРАВ\n\n'
            'Для доступа к функциям бота обратитесь к администратору\n\n'
            '🎹 Доступные функции:\n'
            '• 🆔 Получить ID - узнать ваш идентификатор\n'
            '• /help - справка по командам'
        )

        await update.message.reply_text(
            welcome_text,
            reply_markup=get_unauthorized_keyboard()
        )
        print(f"🚫 Неавторизованный доступ от user_id: {user_id}")
        return

    # Если пользователь авторизован - показываем полное меню
    welcome_text = (
        f'🤖 БОТ С МНОГОУРОВНЕВЫМ МЕНЮ\n'
        f'Текущее время: {current_time} (МСК)\n'
        f'ID чата: {chat_id}\n'
        f'Ваш ID: {user_id}\n\n'
        '🎹 Используйте кнопки меню для навигации!\n\n'
        '💡 Также доступны текстовые команды:\n'
        '/help - справка по командам\n'
        '/update_menu - обновить меню\n'
        '/my_id - показать ваш ID'
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard()
    )
    print(f"✅ Отправлено главное меню в чат {chat_id} для user_id: {user_id}")


@authorization_required
async def update_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принудительно обновляет меню на новую версию"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    print(f"🔄 Принудительное обновление на новое меню для чата {chat_id}, user_id: {user_id}")

    await update.message.reply_text(
        "🔄 Удаляю старое меню...",
        reply_markup=ReplyKeyboardRemove()
    )

    await asyncio.sleep(1)

    await update.message.reply_text(
        "✅ Новое меню загружено!\n\n"
        "🎹 Теперь у вас:\n"
        "• 📋 Шаблоны - управление рассылками\n"
        "• 🧪 Тестирование - тестовые отправки\n"
        "• ⚙️ ЕЩЕ - дополнительные функции",
        reply_markup=get_main_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать справку по командам - доступно всем"""
    user_id = update.effective_user.id

    help_text = """
🤖 СПРАВКА ПО КОМАНДАМ:

🎹 ДОСТУПНЫЕ ВСЕМ:
/start - перезапустить бота
/my_id - показать ваш ID (для получения доступа)
/help - эта справка

🎹 ТОЛЬКО ДЛЯ АВТОРИЗОВАННЫХ:
📋 Шаблоны - управление основными рассылками
🧪 Тестирование - тестовые отправки
⚙️ ЕЩЕ - дополнительные функции
/update_menu - обновить меню
/status - статус шаблонов
/now - текущее время

🔐 Для получения доступа обратитесь к администратору
"""

    # Определяем какую клавиатуру показывать
    if is_authorized(user_id):
        await update.message.reply_text(help_text, reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text(help_text, reply_markup=get_unauthorized_keyboard())


@authorization_required
async def now(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Показывает текущее время"""
    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M:%S")
    await update.message.reply_text(
        f'🕒 Текущее время: {current_time} (МСК)',
        reply_markup=get_main_keyboard()
    )


# Эта функция должна быть БЕЗ декоратора @authorization_required
async def my_id(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Показывает user_id пользователя - доступно всем"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Определяем какую клавиатуру показывать в зависимости от авторизации
    if is_authorized(user_id):
        reply_markup = get_main_keyboard()
        additional_text = "✅ Вы авторизованы и имеете доступ ко всем функциям бота"
    else:
        reply_markup = get_unauthorized_keyboard()
        additional_text = "❌ Вы не авторизованы. Обратитесь к администратору для получения доступа"

    await update.message.reply_text(
        f'🆔 Ваш ID: `{user_id}`\n'
        f'💬 ID чата: `{chat_id}`\n\n'
        f'{additional_text}',
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    print(f"📋 Показан ID для user_id: {user_id}")


@authorization_required
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow'))
    status_text = "📊 СТАТУС АКТИВНЫХ ШАБЛОНОВ:\n\n"

    # Основные шаблоны
    status_text += "🔹 ОСНОВНЫЕ ШАБЛОНЫ:\n"
    if chat_id in active_jobs:
        template_names = {
            'hongqi_template1': '🚗 Дистанционный осмотр Н5 (воскресенье 16:00)',
            'hongqi_template2': '⏰ Напоминание осмотра Н5 (понедельник 07:00)',
            'turbomatiz_template1': '💳 Оплата TurboMatiz (воскресенье 16:00)',
            'turbomatiz_template2': '🔍 Осмотр TurboMatiz (вторник/пятница 16:00)',
            'turbomatiz_template3': '🧼 Чистый кузов TurboMatiz (понедельник 15:00, раз в 2 недели)'
        }

        for template_name, job in active_jobs[chat_id].items():
            next_run = job.next_run_time
            if next_run:
                next_run_moscow = next_run.astimezone(pytz.timezone('Europe/Moscow'))
                time_left = next_run_moscow - current_time
                display_name = template_names.get(template_name, template_name)
                status_text += f"✅ {display_name}\n   📅 Следующая отправка: {next_run_moscow.strftime('%d.%m.%Y %H:%M')}\n   ⏰ Осталось: {format_time_delta(time_left)}\n\n"
            else:
                display_name = template_names.get(template_name, template_name)
                status_text += f"✅ {display_name}: АКТИВЕН (время не установлено)\n\n"
    else:
        status_text += "❌ Нет активных основных шаблонов\n\n"

    # Тестовые шаблоны
    status_text += "🔹 ТЕСТОВЫЕ ОТПРАВКИ:\n"
    if chat_id in test_jobs:
        for template_name, job in test_jobs[chat_id].items():
            next_run = job.next_run_time
            if next_run:
                next_run_moscow = next_run.astimezone(pytz.timezone('Europe/Moscow'))
                time_left = next_run_moscow - current_time
                status_text += f"🧪 Тест {template_name}: АКТИВЕН\n   📅 Время отправки: {next_run_moscow.strftime('%d.%m.%Y %H:%M:%S')}\n   ⏰ Осталось: {format_time_delta(time_left)}\n\n"
            else:
                status_text += f"🧪 Тест {template_name}: АКТИВЕН (время не установлено)\n\n"
    else:
        status_text += "❌ Нет активных тестов\n"

    await update.message.reply_text(status_text, reply_markup=get_main_keyboard())


# Функции управления пользователями
@admin_required
async def user_management(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Меню управления пользователями"""
    await update.message.reply_text(
        "👥 Управление пользователями\n\n"
        "Выберите действие:",
        reply_markup=get_user_management_keyboard()
    )


@admin_required
async def add_user_start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Начало процесса добавления пользователя"""
    await update.message.reply_text(
        "➕ ДОБАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯ\n\n"
        "Шаг 1 из 2:\n"
        "Введите ID пользователя (только цифры):\n\n"
        "❌ Для отмены введите /cancel",
        reply_markup=ReplyKeyboardRemove()
    )
    return ADD_USER_ID


@admin_required
async def add_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ID пользователя"""
    user_id_text = update.message.text.strip()

    try:
        user_id = int(user_id_text)
        # Сохраняем user_id в контексте
        context.user_data['add_user_id'] = user_id
        
        await update.message.reply_text(
            "Шаг 2 из 2:\n"
            "Введите имя пользователя (для отображения в списке):\n\n"
            "❌ Для отмены введите /cancel"
        )
        return ADD_USER_NAME
        
    except ValueError:
        await update.message.reply_text(
            "❌ Ошибка: ID должен состоять только из цифр!\n"
            "Пожалуйста, введите корректный ID:"
        )
        return ADD_USER_ID


@admin_required
async def add_user_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка имени пользователя"""
    username = update.message.text.strip()
    user_id = context.user_data.get('add_user_id')

    if not user_id:
        await update.message.reply_text(
            "❌ Ошибка: не найден ID пользователя",
            reply_markup=get_user_management_keyboard()
        )
        return ConversationHandler.END

    # Добавляем пользователя
    success, message = add_user(user_id, username)

    if success:
        await update.message.reply_text(
            f"✅ Пользователь успешно добавлен!\n👤 {username}\n🆔 {user_id}",
            reply_markup=get_user_management_keyboard()
        )
    else:
        await update.message.reply_text(
            f"❌ Ошибка при добавлении: {message}",
            reply_markup=get_user_management_keyboard()
        )

    # Очищаем временные данные
    context.user_data.clear()
    return ConversationHandler.END


@admin_required
async def remove_user_start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Начало процесса удаления пользователя"""
    users = get_users_list()
    admin_id = get_admin_id()

    # Проверяем, есть ли пользователи для удаления (кроме администратора)
    removable_users = [uid for uid in users.keys() if int(uid) != admin_id]

    if not removable_users:
        await update.message.reply_text(
            "❌ Нет пользователей для удаления",
            reply_markup=get_user_management_keyboard()
        )
        return

    await update.message.reply_text(
        "➖ УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ\n\n"
        "Выберите пользователя для удаления:",
        reply_markup=get_remove_user_keyboard()
    )


@admin_required
async def remove_user_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора пользователя для удаления"""
    text = update.message.text
    user_id = None

    # Извлекаем ID из текста кнопки
    try:
        if "ID:" in text:
            user_id = int(text.split("ID:")[1].split(")")[0].strip())
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Ошибка при обработке выбора",
            reply_markup=get_user_management_keyboard()
        )
        return

    if user_id:
        users = get_users_list()
        username = users.get(str(user_id), "Неизвестный пользователь")

        # Сохраняем данные для подтверждения
        context.user_data['remove_user_id'] = user_id
        context.user_data['remove_username'] = username

        await update.message.reply_text(
            f"⚠️ ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ\n\n"
            f"Вы действительно хотите удалить пользователя:\n"
            f"👤 {username}\n"
            f"🆔 {user_id}\n\n"
            f"Это действие нельзя отменить!",
            reply_markup=get_confirmation_keyboard(user_id)
        )


async def remove_user_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подтверждения удаления"""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("confirm_remove_"):
        user_id = int(query.data.split("_")[2])

        # Удаляем пользователя
        success, message = remove_user(user_id)

        if success:
            await query.edit_message_text(
                f"✅ {message}",
                reply_markup=None
            )
            # Отправляем новое сообщение с клавиатурой
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Выберите действие:",
                reply_markup=get_user_management_keyboard()
            )
        else:
            await query.edit_message_text(
                f"❌ {message}",
                reply_markup=None
            )
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Выберите действие:",
                reply_markup=get_user_management_keyboard()
            )

    elif query.data == "cancel_remove":
        await query.edit_message_text(
            "❌ Удаление отменено",
            reply_markup=None
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Выберите действие:",
            reply_markup=get_user_management_keyboard()
        )


@admin_required
async def list_users(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Показывает список пользователей"""
    users = get_users_list()
    admin_id = get_admin_id()

    if not users:
        users_list_text = "❌ Нет добавленных пользователей"
    else:
        users_list_text = "📋 СПИСОК ПОЛЬЗОВАТЕЛЕЙ:\n\n"
        for user_id_str, username in users.items():
            user_id = int(user_id_str)
            role = "👑 АДМИНИСТРАТОР" if user_id == admin_id else "👤 ПОЛЬЗОВАТЕЛЬ"
            users_list_text += f"{role}\n👤 {username}\n🆔 {user_id}\n\n"

    await update.message.reply_text(
        users_list_text,
        reply_markup=get_back_to_management_keyboard()
    )


async def cancel(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Отмена любого действия"""
    user_id = update.effective_user.id
    await update.message.reply_text(
        "❌ Действие отменено",
        reply_markup=get_user_management_keyboard() if is_admin(user_id) else get_main_keyboard()
    )
    return ConversationHandler.END


# Hongqi шаблоны
@authorization_required
async def start_hongqi_template1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запускает Hongqi шаблон 1: каждое воскресенье в 16:00 МСК"""
    chat_id = update.effective_chat.id
    print(f"🚀 Запуск Hongqi шаблона 1 для чата {chat_id}")

    # Останавливаем предыдущее задание если есть
    if chat_id in active_jobs and 'hongqi_template1' in active_jobs[chat_id]:
        active_jobs[chat_id]['hongqi_template1'].schedule_removal()

    # Конвертируем время: воскресенье 16:00 МСК -> UTC
    utc_time = moscow_to_utc("16:00")

    # Создаем задание (воскресенье = 6)
    job = context.job_queue.run_daily(
        lambda ctx: send_template_message(ctx, chat_id, "hongqi_template1"),
        time=utc_time,
        days=(6,),  # Воскресенье (0=понедельник, 6=воскресенье)
        chat_id=chat_id,
        name=f"hongqi_template1_{chat_id}"
    )

    # Сохраняем задание
    if chat_id not in active_jobs:
        active_jobs[chat_id] = {}
    active_jobs[chat_id]['hongqi_template1'] = job

    print(f"✅ Hongqi шаблон 1 активирован для чата {chat_id}")
    await update.message.reply_text(
        f'✅ Дистанционный осмотр Н5 активирован!\n'
        f'📅 Расписание: каждое воскресенье\n'
        f'⏰ Время: 16:00 (МСК)\n'
        f'✉️ Текст: проверка автомобиля Hongqi',
        reply_markup=get_hongqi_keyboard()
    )


@authorization_required
async def start_hongqi_template2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запускает Hongqi шаблон 2: каждый понедельник в 07:00 МСК"""
    chat_id = update.effective_chat.id
    print(f"🚀 Запуск Hongqi шаблона 2 для чата {chat_id}")

    # Останавливаем предыдущее задание если есть
    if chat_id in active_jobs and 'hongqi_template2' in active_jobs[chat_id]:
        active_jobs[chat_id]['hongqi_template2'].schedule_removal()

    # Конвертируем время: понедельник 07:00 МСК -> UTC
    utc_time = moscow_to_utc("07:00")

    # Создаем задание (понедельник = 0)
    job = context.job_queue.run_daily(
        lambda ctx: send_template_message(ctx, chat_id, "hongqi_template2"),
        time=utc_time,
        days=(0,),  # Понедельник
        chat_id=chat_id,
        name=f"hongqi_template2_{chat_id}"
    )

    # Сохраняем задание
    if chat_id not in active_jobs:
        active_jobs[chat_id] = {}
    active_jobs[chat_id]['hongqi_template2'] = job

    print(f"✅ Hongqi шаблон 2 активирован для чата {chat_id}")
    await update.message.reply_text(
        f'✅ Напоминание осмотра Н5 активировано!\n'
        f'📅 Расписание: каждый понедельник\n'
        f'⏰ Время: 07:00 (МСК)\n'
        f'✉️ Текст: напоминание об осмотре',
        reply_markup=get_hongqi_keyboard()
    )


@authorization_required
async def stop_hongqi_templates(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Останавливает все Hongqi шаблоны"""
    chat_id = update.effective_chat.id
    print(f"🛑 Остановка всех Hongqi шаблонов для чата {chat_id}")

    stopped_count = 0

    # Останавливаем Hongqi шаблоны
    if chat_id in active_jobs:
        for template_name in ['hongqi_template1', 'hongqi_template2']:
            if template_name in active_jobs[chat_id]:
                active_jobs[chat_id][template_name].schedule_removal()
                stopped_count += 1
                del active_jobs[chat_id][template_name]

    await update.message.reply_text(
        f'❌ Остановлено Hongqi шаблонов: {stopped_count}',
        reply_markup=get_hongqi_keyboard()
    )


# TurboMatiz шаблоны
@authorization_required
async def start_turbomatiz_template1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запускает TurboMatiz шаблон 1: каждое воскресенье в 16:00 МСК"""
    chat_id = update.effective_chat.id
    print(f"🚀 Запуск TurboMatiz шаблона 1 для чата {chat_id}")

    # Останавливаем предыдущее задание если есть
    if chat_id in active_jobs and 'turbomatiz_template1' in active_jobs[chat_id]:
        active_jobs[chat_id]['turbomatiz_template1'].schedule_removal()

    # Конвертируем время: воскресенье 16:00 МСК -> UTC
    utc_time = moscow_to_utc("16:00")

    # Создаем задание (воскресенье = 6)
    job = context.job_queue.run_daily(
        lambda ctx: send_template_message(ctx, chat_id, "turbomatiz_template1"),
        time=utc_time,
        days=(6,),  # Воскресенье
        chat_id=chat_id,
        name=f"turbomatiz_template1_{chat_id}"
    )

    # Сохраняем задание
    if chat_id not in active_jobs:
        active_jobs[chat_id] = {}
    active_jobs[chat_id]['turbomatiz_template1'] = job

    print(f"✅ TurboMatiz шаблон 1 активирован для чата {chat_id}")
    await update.message.reply_text(
        f'✅ Оплата TurboMatiz активирована!\n'
        f'📅 Расписание: каждое воскресенье\n'
        f'⏰ Время: 16:00 (МСК)\n'
        f'✉️ Текст: напоминание об оплате',
        reply_markup=get_turbomatiz_keyboard()
    )


@authorization_required
async def start_turbomatiz_template2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запускает TurboMatiz шаблон 2: каждый вторник и пятницу в 16:00 МСК"""
    chat_id = update.effective_chat.id
    print(f"🚀 Запуск TurboMatiz шаблона 2 для чата {chat_id}")

    # Останавливаем предыдущее задание если есть
    if chat_id in active_jobs and 'turbomatiz_template2' in active_jobs[chat_id]:
        active_jobs[chat_id]['turbomatiz_template2'].schedule_removal()

    # Конвертируем время: 16:00 МСК -> UTC
    utc_time = moscow_to_utc("16:00")

    # Создаем задание (вторник=1, пятница=4)
    job = context.job_queue.run_daily(
        lambda ctx: send_template_message(ctx, chat_id, "turbomatiz_template2"),
        time=utc_time,
        days=(1, 4),  # Вторник и пятница
        chat_id=chat_id,
        name=f"turbomatiz_template2_{chat_id}"
    )

    # Сохраняем задание
    if chat_id not in active_jobs:
        active_jobs[chat_id] = {}
    active_jobs[chat_id]['turbomatiz_template2'] = job

    print(f"✅ TurboMatiz шаблон 2 активирован для чата {chat_id}")
    await update.message.reply_text(
        f'✅ Осмотр TurboMatiz активирован!\n'
        f'📅 Расписание: каждый вторник и пятницу\n'
        f'⏰ Время: 16:00 (МСК)\n'
        f'✉️ Текст: напоминание об осмотре',
        reply_markup=get_turbomatiz_keyboard()
    )


@authorization_required
async def start_turbomatiz_template3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запускает TurboMatiz шаблон 3: каждый второй понедельник в 15:00 МСК"""
    chat_id = update.effective_chat.id
    print(f"🚀 Запуск TurboMatiz шаблона 3 для чата {chat_id}")

    # Останавливаем предыдущее задание если есть
    if chat_id in active_jobs and 'turbomatiz_template3' in active_jobs[chat_id]:
        active_jobs[chat_id]['turbomatiz_template3'].schedule_removal()

    # Конвертируем время: понедельник 15:00 МСК -> UTC
    utc_time = moscow_to_utc("15:00")

    # Создаем задание (понедельник = 0)
    job = context.job_queue.run_daily(
        lambda ctx: send_template_message(ctx, chat_id, "turbomatiz_template3"),
        time=utc_time,
        days=(0,),  # Понедельник
        chat_id=chat_id,
        name=f"turbomatiz_template3_{chat_id}"
    )

    # Сохраняем задание
    if chat_id not in active_jobs:
        active_jobs[chat_id] = {}
    active_jobs[chat_id]['turbomatiz_template3'] = job

    print(f"✅ TurboMatiz шаблон 3 активирован для чата {chat_id}")
    await update.message.reply_text(
        f'✅ Чистый кузов TurboMatiz активирован!\n'
        f'📅 Расписание: каждый второй понедельник\n'
        f'⏰ Время: 15:00 (МСК)\n'
        f'✉️ Текст: напоминание о мойке автомобиля',
        reply_markup=get_turbomatiz_keyboard()
    )


@authorization_required
async def stop_turbomatiz_templates(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Останавливает все TurboMatiz шаблоны"""
    chat_id = update.effective_chat.id
    print(f"🛑 Остановка всех TurboMatiz шаблонов для чата {chat_id}")

    stopped_count = 0

    # Останавливаем TurboMatiz шаблоны
    if chat_id in active_jobs:
        for template_name in ['turbomatiz_template1', 'turbomatiz_template2', 'turbomatiz_template3']:
            if template_name in active_jobs[chat_id]:
                active_jobs[chat_id][template_name].schedule_removal()
                stopped_count += 1
                del active_jobs[chat_id][template_name]

    await update.message.reply_text(
        f'❌ Остановлено TurboMatiz шаблонов: {stopped_count}',
        reply_markup=get_turbomatiz_keyboard()
    )


@authorization_required
async def stop_all(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Останавливает все шаблоны"""
    chat_id = update.effective_chat.id
    print(f"🛑 Остановка всех шаблонов для чата {chat_id}")

    stopped_count = 0

    # Останавливаем основные шаблоны
    if chat_id in active_jobs:
        for template_name, job in active_jobs[chat_id].items():
            job.schedule_removal()
            stopped_count += 1
        active_jobs[chat_id] = {}

    # Останавливаем тестовые шаблоны
    if chat_id in test_jobs:
        for template_name, job in test_jobs[chat_id].items():
            job.schedule_removal()
            stopped_count += 1
        test_jobs[chat_id] = {}

    await update.message.reply_text(
        f'❌ Остановлено шаблонов: {stopped_count}',
        reply_markup=get_main_keyboard()
    )


@authorization_required
async def cancel_tests(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Отменяет все тестовые отправки"""
    chat_id = update.effective_chat.id
    print(f"🛑 Отмена всех тестов для чата {chat_id}")

    stopped_count = 0
    if chat_id in test_jobs:
        for template_name, job in test_jobs[chat_id].items():
            job.schedule_removal()
            stopped_count += 1
        test_jobs[chat_id] = {}

    await update.message.reply_text(
        f'❌ Отменено тестов: {stopped_count}',
        reply_markup=get_testing_keyboard()
    )


# Тестовые функции для Hongqi
@authorization_required
async def test_hongqi_template1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестирует Hongqi шаблон 1 (отправка через 10 секунд)"""
    chat_id = update.effective_chat.id
    print(f"🧪 Тест Hongqi шаблона 1 для чата {chat_id}")

    # Создаем задание на 10 секунд
    job = context.job_queue.run_once(
        lambda ctx: send_test_template_message(ctx, chat_id, "hongqi_template1"),
        when=10,
        chat_id=chat_id,
        name=f"test_hongqi_template1_{chat_id}"
    )

    # Сохраняем тестовое задание
    if chat_id not in test_jobs:
        test_jobs[chat_id] = {}
    test_jobs[chat_id]['hongqi_template1'] = job

    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow'))
    send_time = current_time + timedelta(seconds=10)

    await update.message.reply_text(
        f'✅ Тест "Дистанционный осмотр Н5" запущен!\n'
        f'📅 Отправка в: {send_time.strftime("%H:%M:%S")}\n'
        f'⏰ Осталось: 10 секунд',
        reply_markup=get_test_hongqi_keyboard()
    )


@authorization_required
async def test_hongqi_template2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестирует Hongqi шаблон 2 (отправка через 10 секунд)"""
    chat_id = update.effective_chat.id
    print(f"🧪 Тест Hongqi шаблона 2 для чата {chat_id}")

    # Создаем задание на 10 секунд
    job = context.job_queue.run_once(
        lambda ctx: send_test_template_message(ctx, chat_id, "hongqi_template2"),
        when=10,
        chat_id=chat_id,
        name=f"test_hongqi_template2_{chat_id}"
    )

    # Сохраняем тестовое задание
    if chat_id not in test_jobs:
        test_jobs[chat_id] = {}
    test_jobs[chat_id]['hongqi_template2'] = job

    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow'))
    send_time = current_time + timedelta(seconds=10)

    await update.message.reply_text(
        f'✅ Тест "Напоминание осмотра Н5" запущен!\n'
        f'📅 Отправка в: {send_time.strftime("%H:%M:%S")}\n'
        f'⏰ Осталось: 10 секунд',
        reply_markup=get_test_hongqi_keyboard()
    )


# Тестовые функции для TurboMatiz
@authorization_required
async def test_turbomatiz_template1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестирует TurboMatiz шаблон 1 (отправка через 10 секунд)"""
    chat_id = update.effective_chat.id
    print(f"🧪 Тест TurboMatiz шаблона 1 для чата {chat_id}")

    # Создаем задание на 10 секунд
    job = context.job_queue.run_once(
        lambda ctx: send_test_template_message(ctx, chat_id, "turbomatiz_template1"),
        when=10,
        chat_id=chat_id,
        name=f"test_turbomatiz_template1_{chat_id}"
    )

    # Сохраняем тестовое задание
    if chat_id not in test_jobs:
        test_jobs[chat_id] = {}
    test_jobs[chat_id]['turbomatiz_template1'] = job

    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow'))
    send_time = current_time + timedelta(seconds=10)

    await update.message.reply_text(
        f'✅ Тест "Оплата TurboMatiz" запущен!\n'
        f'📅 Отправка в: {send_time.strftime("%H:%M:%S")}\n'
        f'⏰ Осталось: 10 секунд',
        reply_markup=get_test_turbomatiz_keyboard()
    )


@authorization_required
async def test_turbomatiz_template2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестирует TurboMatiz шаблон 2 (отправка через 10 секунд)"""
    chat_id = update.effective_chat.id
    print(f"🧪 Тест TurboMatiz шаблона 2 для чата {chat_id}")

    # Создаем задание на 10 секунд
    job = context.job_queue.run_once(
        lambda ctx: send_test_template_message(ctx, chat_id, "turbomatiz_template2"),
        when=10,
        chat_id=chat_id,
        name=f"test_turbomatiz_template2_{chat_id}"
    )

    # Сохраняем тестовое задание
    if chat_id not in test_jobs:
        test_jobs[chat_id] = {}
    test_jobs[chat_id]['turbomatiz_template2'] = job

    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow'))
    send_time = current_time + timedelta(seconds=10)

    await update.message.reply_text(
        f'✅ Тест "Осмотр TurboMatiz" запущен!\n'
        f'📅 Отправка в: {send_time.strftime("%H:%M:%S")}\n'
        f'⏰ Осталось: 10 секунд',
        reply_markup=get_test_turbomatiz_keyboard()
    )


@authorization_required
async def test_turbomatiz_template3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестирует TurboMatiz шаблон 3 (отправка через 10 секунд)"""
    chat_id = update.effective_chat.id
    print(f"🧪 Тест TurboMatiz шаблона 3 для чата {chat_id}")

    # Создаем задание на 10 секунд
    job = context.job_queue.run_once(
        lambda ctx: send_test_template_message(ctx, chat_id, "turbomatiz_template3"),
        when=10,
        chat_id=chat_id,
        name=f"test_turbomatiz_template3_{chat_id}"
    )

    # Сохраняем тестовое задание
    if chat_id not in test_jobs:
        test_jobs[chat_id] = {}
    test_jobs[chat_id]['turbomatiz_template3'] = job

    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow'))
    send_time = current_time + timedelta(seconds=10)

    await update.message.reply_text(
        f'✅ Тест "Чистый кузов TurboMatiz" запущен!\n'
        f'📅 Отправка в: {send_time.strftime("%H:%M:%S")}\n'
        f'⏰ Осталось: 10 секунд',
        reply_markup=get_test_turbomatiz_keyboard()
    )


# Обработчики текстовых сообщений
@authorization_required
async def handle_text(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения для навигации по меню"""
    text = update.message.text
    user_id = update.effective_user.id

    if text == "📋 Шаблоны":
        await update.message.reply_text(
            "🎯 Выберите бренд:",
            reply_markup=get_templates_keyboard()
        )

    elif text == "🧪 Тестирование":
        await update.message.reply_text(
            "🧪 ТЕСТИРОВАНИЕ ШАБЛОНОВ\n\n"
            "Тестовые отправки работают так же как основные,\n"
            "но отправляются через 10 секунд после активации\n"
            "и выполняются только один раз",
            reply_markup=get_testing_keyboard()
        )

    elif text == "⚙️ ЕЩЕ":
        await update.message.reply_text(
            "⚙️ ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ",
            reply_markup=get_more_keyboard(user_id)
        )

    elif text == "🔙 Главное меню":
        await update.message.reply_text(
            "🔙 Возврат в главное меню",
            reply_markup=get_main_keyboard()
        )

    elif text == "🚗 Осмотры Hongqi":
        await update.message.reply_text(
            "🚗 УПРАВЛЕНИЕ ШАБЛОНАМИ HONGQI\n\n"
            "Выберите шаблон для управления:",
            reply_markup=get_hongqi_keyboard()
        )

    elif text == "🚙 Осмотры TurboMatiz":
        await update.message.reply_text(
            "🚙 УПРАВЛЕНИЕ ШАБЛОНАМИ TURBOMATIZ\n\n"
            "Выберите шаблон для управления:",
            reply_markup=get_turbomatiz_keyboard()
        )

    elif text == "🔙 К выбору бренда":
        await update.message.reply_text(
            "🔙 Возврат к выбору бренда",
            reply_markup=get_templates_keyboard()
        )

    elif text == "🚗 Тест Hongqi":
        await update.message.reply_text(
            "🧪 ТЕСТИРОВАНИЕ ШАБЛОНОВ HONGQI\n\n"
            "Тестовые отправки выполняются через 10 секунд\n"
            "и работают только один раз",
            reply_markup=get_test_hongqi_keyboard()
        )

    elif text == "🚙 Тест TurboMatiz":
        await update.message.reply_text(
            "🧪 ТЕСТИРОВАНИЕ ШАБЛОНОВ TURBOMATIZ\n\n"
            "Тестовые отправки выполняются через 10 секунд\n"
            "и работают только один раз",
            reply_markup=get_test_turbomatiz_keyboard()
        )

    elif text == "🔙 К тестированию":
        await update.message.reply_text(
            "🔙 Возврат к тестированию",
            reply_markup=get_testing_keyboard()
        )

    elif text == "📊 Статус команд":
        await status(update, _)

    elif text == "🕒 Текущее время":
        await now(update, _)

    elif text == "🆔 Мой ID":
        await my_id(update, _)

    elif text == "👥 Управление пользователями" and is_admin(user_id):
        await user_management(update, _)

    elif text == "🔙 Назад к ЕЩЕ":
        await update.message.reply_text(
            "🔙 Возврат к дополнительным функциям",
            reply_markup=get_more_keyboard(user_id)
        )

    elif text == "🔙 Назад к управлению":
        await user_management(update, _)

    elif text == "🆔 Получить ID":
        await my_id(update, _)

    elif text == "📋 Справка":
        await help_command(update, _)

    else:
        await update.message.reply_text(
            "❌ Неизвестная команда\n"
            "Используйте кнопки меню или /help для справки",
            reply_markup=get_main_keyboard() if is_authorized(user_id) else get_unauthorized_keyboard()
        )


def main():
    """Запуск бота"""
    print("🚀 Запуск бота...")

    # Явно создаем event loop для Python 3.14
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Создаем приложение
    application = (
    Application.builder()
    .token(BOT_TOKEN)
    .job_queue(JobQueue())
    .build()
)

    # ConversationHandler для добавления пользователя
    add_user_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Добавить пользователя$"), add_user_start)],
        states={
            ADD_USER_ID: [MessageHandler(filters.TEXT& ~filters.COMMAND, add_user_id)],
            ADD_USER_NAME: [MessageHandler(filters.TEXT& ~filters.COMMAND, add_user_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("my_id", my_id))
    application.add_handler(CommandHandler("now", now))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("update_menu", update_menu))

    # Обработчики кнопок
    application.add_handler(MessageHandler(filters.Regex("^📋 Шаблоны$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🧪 Тестирование$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^⚙️ ЕЩЕ$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🔙 Главное меню$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🚗 Осмотры Hongqi$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🚙 Осмотры TurboMatiz$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🔙 К выбору бренда$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🚗 Тест Hongqi$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🚙 Тест TurboMatiz$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🔙 К тестированию$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^📊 Статус команд$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🕒 Текущее время$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🆔 Мой ID$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^👥 Управление пользователями$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🔙 Назад к ЕЩЕ$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🔙 Назад к управлению$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🆔 Получить ID$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^📋 Справка$"), handle_text))

    # Hongqi шаблоны
    application.add_handler(MessageHandler(filters.Regex("^🔍 Дистанционный осмотр Н5$"), start_hongqi_template1))
    application.add_handler(MessageHandler(filters.Regex("^⏰ Напоминание осмотра Н5$"), start_hongqi_template2))
    application.add_handler(MessageHandler(filters.Regex("^🛑 Остановить все шаблоны Hongqi$"), stop_hongqi_templates))

    # TurboMatiz шаблоны
    application.add_handler(MessageHandler(filters.Regex("^💳 Оплата$"), start_turbomatiz_template1))
    application.add_handler(MessageHandler(filters.Regex("^🔍 Осмотр$"), start_turbomatiz_template2))
    application.add_handler(MessageHandler(filters.Regex("^🧼 Чистый кузов$"), start_turbomatiz_template3))
    application.add_handler(MessageHandler(filters.Regex("^🛑 Остановить все шаблоны TurboMatiz$"), stop_turbomatiz_templates))

    # Тестирование Hongqi
    application.add_handler(MessageHandler(filters.Regex("^🔍 Тест осмотр Н5$"), test_hongqi_template1))
    application.add_handler(MessageHandler(filters.Regex("^⏰ Тест напоминание Н5$"), test_hongqi_template2))

    # Тестирование TurboMatiz
    application.add_handler(MessageHandler(filters.Regex("^💳 Тест оплата$"), test_turbomatiz_template1))
    application.add_handler(MessageHandler(filters.Regex("^🔍 Тест осмотр$"), test_turbomatiz_template2))
    application.add_handler(MessageHandler(filters.Regex("^🧼 Тест чистый кузов$"), test_turbomatiz_template3))

    # Остановка всех тестов
    application.add_handler(MessageHandler(filters.Regex("^🛑 Остановить все тестирования$"), cancel_tests))

    # Управление пользователями
    application.add_handler(add_user_conv_handler)
    application.add_handler(MessageHandler(filters.Regex("^➖ Удалить пользователя$"), remove_user_start))
    application.add_handler(MessageHandler(filters.Regex("^📋 Список пользователей$"), list_users))
    application.add_handler(CallbackQueryHandler(remove_user_confirm, pattern="^(confirm_remove_|cancel_remove)"))

    # Удаление пользователей по кнопкам
    application.add_handler(MessageHandler(filters.Regex("^❌ .* \\(ID: \\d+\\)$"), remove_user_selected))

    # Обработчик для всех текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT& ~filters.COMMAND, handle_text))

    # Запуск бота
    print("✅ Бот запущен и готов к работе!")
    application.run_polling()


if __name__ == '__main__':

    main()



