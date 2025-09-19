import os
import json
import logging
import sqlite3
from datetime import datetime, time, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio
import jdatetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Sleep reminder URL
SLEEP_REMINDER_URL = "https://shealth.samsung.com/deepLink?sc_id=tracker.medication&action=view&destination=home.sleep"

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

# Database setup
DB_FILE = "tasks.db"

def init_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            task_text TEXT,
            is_done INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            total_tasks INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, date)
        )
    ''')
    
    conn.commit()
    conn.close()

# Database operations
def save_daily_tasks(user_id, date, tasks):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Remove existing tasks for this user and date
    cursor.execute('DELETE FROM tasks WHERE user_id = ? AND date = ?', (user_id, date))
    
    # Insert new tasks
    for task in tasks:
        cursor.execute(
            'INSERT INTO tasks (user_id, date, task_text, is_done) VALUES (?, ?, ?, 0)',
            (user_id, date, task)
        )
    
    # Update or insert daily entry
    cursor.execute(
        'INSERT OR REPLACE INTO daily_entries (user_id, date, total_tasks) VALUES (?, ?, ?)',
        (user_id, date, len(tasks))
    )
    
    conn.commit()
    conn.close()

def get_tasks_by_date(user_id, date):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT id, task_text, is_done FROM tasks WHERE user_id = ? AND date = ? ORDER BY id',
        (user_id, date)
    )
    
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def toggle_task_status(task_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('UPDATE tasks SET is_done = NOT is_done WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()

def get_task_summary(user_id, date):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT COUNT(*) as total, SUM(is_done) as done FROM tasks WHERE user_id = ? AND date = ?',
        (user_id, date)
    )
    
    result = cursor.fetchone()
    conn.close()
    return result[0], result[1] or 0

def get_last_n_days(user_id, n=5):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT date, COUNT(*) as total, SUM(is_done) as done 
        FROM tasks 
        WHERE user_id = ? 
        GROUP BY date 
        ORDER BY date DESC 
        LIMIT ?
    ''', (user_id, n))
    
    results = cursor.fetchall()
    conn.close()
    return results

def has_tasks_for_date(user_id, date):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ? AND date = ?', (user_id, date))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

# Global scheduler
scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Tehran'))

# Start command with menu
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
    
    welcome_message = f"""
🎯 سلام {USERS[user_id]}! به ربات مدیریت تسک‌ها خوش آمدید.

📋 دستورات موجود:
/tasks - افزودن تسک‌های امروز
/today - نمایش تسک‌های امروز
/date - نمایش تسک‌های روز مشخص
/last5 - نمایش 5 روز گذشته
/done - گزارش پیشرفت امروز

⏰ یادآوری‌ها:
• ساعت 9 صبح: یادآوری ثبت تسک‌ها
• ساعت 10 صبح: یادآوری خواب

برای شروع، تسک‌های امروزتان را با دستور /tasks وارد کنید.
    """
    
    await update.message.reply_text(welcome_message)

# Add tasks
async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    today = jdatetime.date.today().strftime("%Y-%m-%d")
    
    # Check if user is authorized
    if user_id not in USERS:
        await update.message.reply_text("❌ شما مجاز به استفاده از این ربات نیستید.")
        return
    
    logger.info(f"User {user_id} ({USERS[user_id]}) adding tasks for {today}")

    # Get text after /tasks
    task_text = update.message.text.replace("/tasks", "").strip()
    if not task_text:
        await update.message.reply_text("❌ لطفاً بعد از /tasks لیست تسک‌ها رو بنویس (هر خط یک تسک).\n\nمثال:\n/tasks تمرین ورزشی\nخرید مواد غذایی\nمطالعه کتاب")
        return

    task_list = [task.strip() for task in task_text.split("\n") if task.strip()]

    # Save to database
    save_daily_tasks(user_id, today, task_list)

    # Notify partners about task entry
    await notify_task_entry(context, user_id, today, len(task_list))

    await show_tasks_for_date(update, context, user_id, today)

# Show today's tasks
async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    today = jdatetime.date.today().strftime("%Y-%m-%d")
    
    if user_id not in USERS:
        await update.message.reply_text("❌ شما مجاز به استفاده از این ربات نیستید.")
        return
    
    await show_tasks_for_date(update, context, user_id, today)

# Show tasks for specific date
async def date_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    
    if user_id not in USERS:
        await update.message.reply_text("❌ شما مجاز به استفاده از این ربات نیستید.")
        return
    
    # Get date from command
    args = context.args
    if not args:
        await update.message.reply_text("❌ لطفاً تاریخ را به فرمت YYYY-MM-DD وارد کنید.\n\nمثال:\n/date 2024-01-15")
        return
    
    date_str = args[0]
    try:
        # Validate date format
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("❌ فرمت تاریخ اشتباه است. لطفاً به فرمت YYYY-MM-DD وارد کنید.\n\nمثال: 2024-01-15")
        return
    
    await show_tasks_for_date(update, context, user_id, date_str)

# Show tasks with checkboxes for a specific date
async def show_tasks_for_date(update_or_callback, context: ContextTypes.DEFAULT_TYPE, user_id, date):
    tasks = get_tasks_by_date(user_id, date)
    
    if not tasks:
        message = f"❌ هیچ تسکی برای تاریخ {date} ثبت نشده."
        if isinstance(update_or_callback, Update):
            await update_or_callback.message.reply_text(message)
        else:
            await update_or_callback.edit_message_text(message)
        return

    keyboard = []
    for task_id, task_text, is_done in tasks:
        status = "✅" if is_done else "⬜"
        keyboard.append([InlineKeyboardButton(f"{status} {task_text}", callback_data=f"toggle:{task_id}:{date}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    message = f"📋 تسک‌های تاریخ {date}:"

    if isinstance(update_or_callback, Update):
        await update_or_callback.message.reply_text(message, reply_markup=reply_markup)
    else:  # CallbackQuery
        await update_or_callback.edit_message_text(message, reply_markup=reply_markup)

# Toggle task completion
async def toggle_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.message.chat_id
    
    if user_id not in USERS:
        await query.edit_message_text("❌ شما مجاز به استفاده از این ربات نیستید.")
        return

    try:
        _, task_id, date = query.data.split(":")
        task_id = int(task_id)
    except (ValueError, IndexError):
        await query.edit_message_text("❌ خطا در پردازش درخواست.")
        return

    # Toggle task status
    toggle_task_status(task_id)

    await show_tasks_for_date(query, context, user_id, date)

# Show last 5 days summary
async def last5_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    
    if user_id not in USERS:
        await update.message.reply_text("❌ شما مجاز به استفاده از این ربات نیستید.")
        return
    
    results = get_last_n_days(user_id, 5)
    
    if not results:
        await update.message.reply_text("❌ هیچ تسکی در 5 روز گذشته ثبت نشده.")
        return
    
    message = "📊 گزارش 5 روز گذشته:\n\n"
    
    for date, total, done in results:
        percentage = int((done / total) * 100) if total > 0 else 0
        status_emoji = "🟢" if percentage >= 80 else "🟡" if percentage >= 50 else "🔴"
        
        # Convert to Persian date if needed
        try:
            persian_date = jdatetime.datetime.strptime(date, "%Y-%m-%d").strftime("%Y/%m/%d")
        except:
            persian_date = date
            
        message += f"{status_emoji} {persian_date}: {done}/{total} تسک ({percentage}%)\n"
    
    await update.message.reply_text(message)

# Done command
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    today = jdatetime.date.today().strftime("%Y-%m-%d")

    # Check if user is authorized
    if user_id not in USERS:
        await update.message.reply_text("❌ شما مجاز به استفاده از این ربات نیستید.")
        return

    total, done_count = get_task_summary(user_id, today)
    
    if total == 0:
        await update.message.reply_text("❌ هیچ تسکی برای امروز ثبت نکردی.")
        return

    percentage = int((done_count / total) * 100) if total > 0 else 0
    
    # Report to self
    status_emoji = "🎉" if percentage >= 80 else "👍" if percentage >= 50 else "💪"
    await update.message.reply_text(
        f"{status_emoji} امروز ({today}) {done_count} از {total} تسک رو انجام دادی ({percentage}%)."
    )

    # Notify the other users
    other_users = [uid for uid in USERS if uid != user_id]
    for other_user in other_users:
        try:
            await context.bot.send_message(
                chat_id=other_user,
                text=f"📢 {USERS[user_id]} امروز ({today}) {done_count} از {total} تسک خودش رو انجام داد ({percentage}%)."
            )
        except Exception as e:
            logger.error(f"Error sending notification to {other_user}: {e}")

# Notification functions
async def notify_task_entry(context: ContextTypes.DEFAULT_TYPE, user_id, date, task_count):
    """Notify partners when someone enters tasks"""
    other_users = [uid for uid in USERS if uid != user_id]
    for other_user in other_users:
        try:
            await context.bot.send_message(
                chat_id=other_user,
                text=f"📝 {USERS[user_id]} برای تاریخ {date} تعداد {task_count} تسک ثبت کرد."
            )
        except Exception as e:
            logger.error(f"Error sending task entry notification to {other_user}: {e}")

async def send_daily_task_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send reminder at 9 AM to users who haven't entered tasks"""
    today = jdatetime.date.today().strftime("%Y-%m-%d")
    
    for user_id in USERS:
        if not has_tasks_for_date(user_id, today):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"⏰ صبح بخیر {USERS[user_id]}!\n\nهنوز تسک‌های امروزت رو وارد نکردی. لطفاً با دستور /tasks تسک‌هات رو ثبت کن."
                )
            except Exception as e:
                logger.error(f"Error sending daily reminder to {user_id}: {e}")

async def send_sleep_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send sleep reminder at 10 AM"""
    for user_id in USERS:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"😴 {USERS[user_id]} عزیز، وقت ثبت ساعات خوابت رسیده!\n\n{SLEEP_REMINDER_URL}"
            )
        except Exception as e:
            logger.error(f"Error sending sleep reminder to {user_id}: {e}")

# Error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}")

# Set bot commands menu
async def set_bot_commands(application):
    commands = [
        BotCommand("start", "شروع و راهنما"),
        BotCommand("tasks", "افزودن تسک‌های امروز"),
        BotCommand("today", "نمایش تسک‌های امروز"),
        BotCommand("date", "نمایش تسک‌های روز مشخص"),
        BotCommand("last5", "نمایش 5 روز گذشته"),
        BotCommand("done", "گزارش پیشرفت امروز"),
    ]
    
    await application.bot.set_my_commands(commands)

def main():
    # Check if bot token is provided
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is required!")
        return
    
    # Check if users are configured
    if not USERS:
        logger.error("No users configured! Please set USER_1_ID, USER_1_NAME, etc.")
        return

    # Initialize database
    init_database()

    # Create application
    app = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tasks", tasks))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("date", date_tasks))
    app.add_handler(CommandHandler("last5", last5_days))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CallbackQueryHandler(toggle_task))
    
    # Add error handler
    app.add_error_handler(error_handler)

    # Set bot commands menu
    app.job_queue.run_once(set_bot_commands, when=1)

    # Schedule reminders
    # Daily task reminder at 9:00 AM Iran time
    app.job_queue.run_daily(
        send_daily_task_reminder,
        time=time(hour=9, minute=0),
        name="daily_task_reminder"
    )
    
    # Sleep reminder at 10:00 AM Iran time
    app.job_queue.run_daily(
        send_sleep_reminder,
        time=time(hour=10, minute=0),
        name="sleep_reminder"
    )

    logger.info(f"Starting bot with {len(USERS)} configured users...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()