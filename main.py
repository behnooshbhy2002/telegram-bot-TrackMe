import os
import json
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import datetime
import jdatetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Load users from environment variables
def load_users():
    users = {}
    i = 1
    while True:
        user_id = os.getenv(f"USER_{i}_ID")
        user_name = os.getenv(f"USER_{i}_NAME")
        
        if not user_id or not user_name:
            break
            
        try:
            users[int(user_id)] = user_name
        except ValueError:
            logger.error(f"Invalid user ID format for USER_{i}_ID: {user_id}")
        
        i += 1
    
    if not users:
        logger.warning("No users configured! Please set USER_1_ID, USER_1_NAME, etc. in environment variables")
    
    return users

USERS = load_users()

# File to store tasks data
DATA_FILE = "tasks_data.json"

# Load tasks data from file
def load_tasks_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert done sets back from lists
                for date in data:
                    for user_id in data[date]:
                        if 'done' in data[date][user_id]:
                            data[date][user_id]['done'] = set(data[date][user_id]['done'])
                return data
    except Exception as e:
        logger.error(f"Error loading tasks data: {e}")
    return {}

# Save tasks data to file
def save_tasks_data(data):
    try:
        # Convert sets to lists for JSON serialization
        data_to_save = {}
        for date in data:
            data_to_save[date] = {}
            for user_id in data[date]:
                data_to_save[date][user_id] = {
                    "tasks": data[date][user_id]["tasks"],
                    "done": list(data[date][user_id]["done"])
                }
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving tasks data: {e}")

# Storage for daily tasks
tasks_data = load_tasks_data()

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    logger.info(f"User {user_id} started the bot")
    
    if user_id not in USERS:
        await update.message.reply_text(
            f"❌ شما مجاز به استفاده از این ربات نیستید.\n"
            f"Chat ID شما: {user_id}\n"
            f"لطفاً این ID را به مدیر ربات اطلاع دهید."
        )
        return
    
    await update.message.reply_text(f"سلام {USERS[user_id]}! با دستور /tasks تسک‌های امروزتو وارد کن (هر خط یک تسک).")

# Add tasks
async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    today = jdatetime.date.today().strftime("%Y-%m-%d")
    
    # Check if user is authorized
    if user_id not in USERS:
        await update.message.reply_text("❌ شما مجاز به استفاده از این ربات نیستید.")
        return
    
    logger.info(f"User {user_id} ({USERS[user_id]}) adding tasks for {today}")

    # گرفتن متن بعد از /tasks
    task_text = update.message.text.replace("/tasks", "").strip()
    if not task_text:
        await update.message.reply_text("❌ لطفاً بعد از /tasks لیست تسک‌ها رو بنویس (هر خط یک تسک).")
        return

    task_list = [task.strip() for task in task_text.split("\n") if task.strip()]

    if today not in tasks_data:
        tasks_data[today] = {}

    tasks_data[today][user_id] = {"tasks": task_list, "done": set()}
    save_tasks_data(tasks_data)

    await show_tasks(update, context, user_id, today)

# Show tasks with checkboxes
async def show_tasks(update_or_callback, context: ContextTypes.DEFAULT_TYPE, user_id, today):
    if today not in tasks_data or user_id not in tasks_data[today]:
        if isinstance(update_or_callback, Update):
            await update_or_callback.message.reply_text("❌ هیچ تسکی برای امروز ثبت نشده.")
        else:
            await update_or_callback.edit_message_text("❌ هیچ تسکی برای امروز ثبت نشده.")
        return

    user_tasks = tasks_data[today][user_id]["tasks"]
    done_set = tasks_data[today][user_id]["done"]

    keyboard = []
    for i, task in enumerate(user_tasks, start=1):
        status = "✅" if i in done_set else "⬜"
        keyboard.append([InlineKeyboardButton(f"{status} {task}", callback_data=f"toggle:{i}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if isinstance(update_or_callback, Update):
        await update_or_callback.message.reply_text("📋 تسک‌های امروز:", reply_markup=reply_markup)
    else:  # CallbackQuery
        await update_or_callback.edit_message_text("📋 تسک‌های امروز:", reply_markup=reply_markup)

# Toggle task completion
async def toggle_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.message.chat_id
    today = jdatetime.date.today().strftime("%Y-%m-%d")

    if today not in tasks_data or user_id not in tasks_data[today]:
        await query.edit_message_text("❌ هیچ تسکی برای امروز ثبت نشده.")
        return

    task_index = int(query.data.split(":")[1])

    done_set = tasks_data[today][user_id]["done"]
    if task_index in done_set:
        done_set.remove(task_index)
    else:
        done_set.add(task_index)

    save_tasks_data(tasks_data)
    await show_tasks(query, context, user_id, today)

# Done command
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    today = jdatetime.date.today().strftime("%Y-%m-%d")

    # Check if user is authorized
    if user_id not in USERS:
        await update.message.reply_text("❌ شما مجاز به استفاده از این ربات نیستید.")
        return

    if today not in tasks_data or user_id not in tasks_data[today]:
        await update.message.reply_text("❌ هیچ تسکی برای امروز ثبت نکردی.")
        return

    total = len(tasks_data[today][user_id]["tasks"])
    done_count = len(tasks_data[today][user_id]["done"])

    # Report to self
    await update.message.reply_text(
        f"🎉 امروز ({today}) {done_count} از {total} تسک رو انجام دادی."
    )

    # Notify the other users
    other_users = [uid for uid in USERS if uid != user_id]
    for other_user in other_users:
        try:
            await context.bot.send_message(
                chat_id=other_user,
                text=f"📢 {USERS[user_id]} امروز ({today}) {done_count} از {total} تسک خودش رو انجام داد."
            )
        except Exception as e:
            logger.error(f"Error sending notification to {other_user}: {e}")

# Error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    # Check if bot token is provided
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is required!")
        return
    
    # Check if users are configured
    if not USERS:
        logger.error("No users configured! Please set USER_1_ID, USER_1_NAME, etc.")
        return

    # Create application
    app = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tasks", tasks))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CallbackQueryHandler(toggle_task))
    
    # Add error handler
    app.add_error_handler(error_handler)

    logger.info(f"Starting bot with {len(USERS)} configured users...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()