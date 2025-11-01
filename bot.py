import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    JobQueue
)
from telegram.error import Conflict
from config import BOT_TOKEN
from authorized_users import is_authorized, is_admin
from database import init_database, load_groups
from task_manager import task_manager
from group_manager import group_manager
import datetime
import pytz
from datetime import timedelta
import sys
import os
import requests
import threading
import time

# Initialize database on startup
init_database()

# Force reload templates module
if 'templates' in sys.modules:
    del sys.modules['templates']

# Import templates
TEMPLATES = {}
try:
    from templates import TEMPLATES as IMPORTED_TEMPLATES
    TEMPLATES = IMPORTED_TEMPLATES
    print("✅ Templates loaded successfully")
except ImportError as import_error:
    print(f"❌ Error loading templates: {import_error}")
    exit(1)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# States for ConversationHandler
ADD_USER_ID, ADD_USER_NAME = range(2)
SELECT_GROUP, SELECT_TEMPLATE = range(2, 4)

# Authorization decorator
def authorization_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not is_authorized(user_id):
            await update.message.reply_text(
                "❌ INSUFFICIENT PERMISSIONS\n\n"
                "Contact administrator for bot access",
                reply_markup=get_unauthorized_keyboard()
            )
            print(f"🚫 Unauthorized access from user_id: {user_id} to function: {func.__name__}")
            return None
        return await func(update, context, *args, **kwargs)
    return wrapper

# Main menu
def get_main_keyboard():
    keyboard = [
        ["📋 Templates", "🧪 Testing"],
        ["📊 Task Status", "⚙️ MORE"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_unauthorized_keyboard():
    keyboard = [
        ["🆔 Get ID"],
        ["📋 Help"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_templates_keyboard():
    keyboard = [
        ["🚗 Hongqi 476 group", "🚙 Matiz 476 group"],
        ["🔙 Back to Main Menu"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_group_selection_keyboard(user_id):
    """Keyboard for group selection"""
    accessible_groups = group_manager.get_accessible_groups_for_user(user_id)
    keyboard = []
    
    for group_id, group_info in accessible_groups.items():
        keyboard.append([f"📋 {group_info.get('title', f'Group {group_id}')}"])
    
    keyboard.append(["🔙 Back to Main Menu"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # If bot is in group - update group information
    if update.effective_chat.type in ["group", "supergroup", "channel"]:
        await group_manager.update_group_info(update, context)
        return
    
    # Personal chat
    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M:%S")

    if not is_authorized(user_id):
        welcome_text = (
            f'🤖 BOT FOR SCHEDULED MESSAGES\n\n'
            f'Hello! This bot is for creating scheduled messages in Telegram groups and channels.\n\n'
            f'🆔 Your ID: `{user_id}`\n'
            f'🕒 Current time: {current_time} (Moscow)\n\n'
            f'❌ INSUFFICIENT PERMISSIONS\n\n'
            f'To start working with the bot, click "Get ID" and send it to @ProfeSSor471. '
            f'He will add you to the user list and explain further work with the bot.\n\n'
            f'Enjoy!'
        )

        await update.message.reply_text(
            welcome_text,
            reply_markup=get_unauthorized_keyboard(),
            parse_mode='Markdown'
        )
        return

    welcome_text = (
        f'🤖 BOT FOR SCHEDULED MESSAGES\n'
        f'🕒 Current time: {current_time} (Moscow)\n'
        f'🆔 Your ID: {user_id}\n\n'
        f'🎹 Use menu buttons for navigation!'
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard()
    )

@authorization_required
async def handle_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for Templates button"""
    user_id = update.effective_user.id
    
    accessible_groups = group_manager.get_accessible_groups_for_user(user_id)
    if not accessible_groups:
        await update.message.reply_text(
            "❌ You don't have access to any groups\n\n"
            "Contact administrator for access",
            reply_markup=get_main_keyboard()
        )
        return
    
    await update.message.reply_text(
        "🎯 Select group for working with templates:",
        reply_markup=get_group_selection_keyboard(user_id)
    )

@authorization_required 
async def handle_testing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for Testing button"""
    user_id = update.effective_user.id
    
    accessible_groups = group_manager.get_accessible_groups_for_user(user_id)
    if not accessible_groups:
        await update.message.reply_text(
            "❌ You don't have access to any groups",
            reply_markup=get_main_keyboard()
        )
        return
    
    await update.message.reply_text(
        "🧪 TESTING TEMPLATES\n\n"
        "Select group for test sending:",
        reply_markup=get_group_selection_keyboard(user_id)
    )

@authorization_required
async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user task status"""
    user_id = update.effective_user.id
    user_tasks = task_manager.get_user_tasks(user_id)
    
    if not user_tasks:
        status_text = "📊 TASK STATUS\n\n❌ No active tasks"
    else:
        status_text = "📊 YOUR ACTIVE TASKS:\n\n"
        for task_id, task_data in user_tasks.items():
            groups_data = load_groups()
            group_info = groups_data["groups"].get(str(task_data["group_id"]), {})
            group_name = group_info.get('title', f'Group {task_data["group_id"]}')
            
            status_text += f"🔹 {TEMPLATES.get(task_data['template_name'], {}).get('text', 'Template')[:50]}...\n"
            status_text += f"   📍 Group: {group_name}\n"
            status_text += f"   🕒 Created: {task_data['created_at'][:16]}\n"
            status_text += f"   🔧 Type: {'Main' if task_data['task_type'] == 'main' else 'Test'}\n\n"
    
    await update.message.reply_text(
        status_text,
        reply_markup=get_main_keyboard()
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Skip processing if it's a group
    if update.effective_chat.type in ["group", "supergroup", "channel"]:
        return
    
    if text == "📋 Templates":
        await handle_templates(update, context)
    elif text == "🧪 Testing":
        await handle_testing(update, context)
    elif text == "📊 Task Status":
        await handle_status(update, context)
    elif text == "⚙️ MORE":
        await update.message.reply_text(
            "⚙️ ADDITIONAL FUNCTIONS",
            reply_markup=get_more_keyboard(user_id)
        )
    elif text == "🔙 Back to Main Menu":
        await update.message.reply_text(
            "🔙 Back to main menu",
            reply_markup=get_main_keyboard()
        )
    elif text == "🆔 Get ID":
        await my_id(update, context)
    elif text == "📋 Help":
        await help_command(update, context)
    else:
        await update.message.reply_text(
            "❌ Unknown command",
            reply_markup=get_main_keyboard() if is_authorized(user_id) else get_unauthorized_keyboard()
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help - available to everyone"""
    user_id = update.effective_user.id

    help_text = """
🤖 BOT COMMAND HELP:

🎹 AVAILABLE TO ALL:
/start - restart bot
/my_id - show your ID (for access)
/help - this help

🎹 AUTHORIZED ONLY:
📋 Templates - manage main broadcasts
🧪 Testing - test sending
📊 Task Status - task status
⚙️ MORE - additional functions

🔐 For access contact administrator
"""

    # Determine which keyboard to show
    if is_authorized(user_id):
        await update.message.reply_text(help_text, reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text(help_text, reply_markup=get_unauthorized_keyboard())

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user_id - available to everyone"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Determine which keyboard to show based on authorization
    if is_authorized(user_id):
        reply_markup = get_main_keyboard()
        additional_text = "✅ You are authorized and have access to all bot functions"
    else:
        reply_markup = get_unauthorized_keyboard()
        additional_text = "❌ You are not authorized. Contact administrator for access"

    await update.message.reply_text(
        f'🆔 Your ID: `{user_id}`\n'
        f'💬 Chat ID: `{chat_id}`\n\n'
        f'{additional_text}',
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current time"""
    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M:%S")
    await update.message.reply_text(
        f'🕒 Current time: {current_time} (Moscow)',
        reply_markup=get_main_keyboard()
    )

def get_more_keyboard(user_id):
    """Create additional functions menu"""
    keyboard = [
        ["📊 Status", "🕒 Current Time"],
        ["🆔 My ID"]
    ]

    # Add user management button only for administrator
    if is_admin(user_id):
        keyboard.append(["👥 User Management"])

    keyboard.append(["🔙 Back to Main Menu"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Keep alive function for Render
def keep_alive():
    """Periodically ping to keep app awake"""
    def ping():
        while True:
            try:
                # Get URL from Render environment variable
                render_url = os.environ.get('RENDER_EXTERNAL_URL')
                if render_url:
                    response = requests.get(render_url, timeout=10)
                    print(f"🔄 Ping sent: {response.status_code}")
                else:
                    # If no URL, just log
                    print("🔄 Keep-alive: bot active")
            except Exception as e:
                print(f"⚠️ Ping error: {e}")
            time.sleep(300)  # Ping every 5 minutes
    
    # Start in separate thread
    ping_thread = threading.Thread(target=ping, daemon=True)
    ping_thread.start()
    print("✅ Keep-alive system started")

def main():
    """Start bot - with conflict handling"""
    print("🚀 Starting bot...")
    
    # Initialize database
    init_database()

    # Start keep-alive system
    keep_alive()

    try:
        # Create application
        application = (
            Application.builder()
            .token(BOT_TOKEN)
            .build()
        )

        # Command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("my_id", my_id))
        application.add_handler(CommandHandler("now", now))
        application.add_handler(CommandHandler("status", handle_status))

        # Main menu button handlers
        application.add_handler(MessageHandler(filters.Regex("^📋 Templates$"), handle_text))
        application.add_handler(MessageHandler(filters.Regex("^🧪 Testing$"), handle_text))
        application.add_handler(MessageHandler(filters.Regex("^📊 Task Status$"), handle_text))
        application.add_handler(MessageHandler(filters.Regex("^⚙️ MORE$"), handle_text))
        application.add_handler(MessageHandler(filters.Regex("^🔙 Back to Main Menu$"), handle_text))
        application.add_handler(MessageHandler(filters.Regex("^🆔 Get ID$"), handle_text))
        application.add_handler(MessageHandler(filters.Regex("^📋 Help$"), handle_text))

        # Handler for all text messages
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

        print("✅ Bot started and ready!")
        
        # Start the bot with simple polling and conflict handling
        application.run_polling(drop_pending_updates=True)
        
    except Conflict as e:
        print(f"❌ Bot conflict detected: {e}")
        print("💡 Solution: Wait a few minutes for other instances to stop, or restart the service")
        # Exit gracefully to allow Render to restart
        time.sleep(60)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        time.sleep(60)
        sys.exit(1)

if __name__ == '__main__':
    main()
