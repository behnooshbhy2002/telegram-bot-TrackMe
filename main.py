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
import re

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('/app/logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Sleep reminder URL
SLEEP_REMINDER_URL = "https://shealth.samsung.com/deepLink?sc_id=tracker.medication&action=view&destination=home.sleep"

# Configure users from environment variables
def load_users_from_env():
    users = {}
    i = 1
    while True:
        user_id_key = f"USER{i}_ID"
        user_name_key = f"USER{i}_NAME"
        
        user_id = os.getenv(user_id_key)
        user_name = os.getenv(user_name_key)
        
        if user_id and user_name:
            try:
                users[int(user_id)] = user_name
                i += 1
            except ValueError:
                logger.error(f"Invalid user ID format for {user_id_key}: {user_id}")
                break
        else:
            break
    
    return users

USERS = load_users_from_env()

# Database setup with persistent path
DB_FILE = "/app/data/tasks.db"

def init_database():
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    
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
            is_completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, date)
        )
    ''')
    
    conn.commit()
    conn.close()

# Database operations
def save_daily_tasks(user_id, date, tasks):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        logger.info(f"Saving {len(tasks)} tasks for user {user_id} on {date}")
        
        # Remove existing tasks for this user and date
        cursor.execute('DELETE FROM tasks WHERE user_id = ? AND date = ?', (user_id, date))
        deleted_count = cursor.rowcount
        logger.info(f"Deleted {deleted_count} existing tasks")
        
        # Insert new tasks
        for i, task in enumerate(tasks):
            if task.strip():  # Only insert non-empty tasks
                cursor.execute(
                    'INSERT INTO tasks (user_id, date, task_text, is_done) VALUES (?, ?, ?, 0)',
                    (user_id, date, task.strip())
                )
                logger.info(f"Inserted task {i+1}: {task.strip()[:50]}...")
        
        # Update or insert daily entry
        cursor.execute(
            'INSERT OR REPLACE INTO daily_entries (user_id, date, total_tasks, is_completed) VALUES (?, ?, ?, 0)',
            (user_id, date, len([t for t in tasks if t.strip()]))
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully saved {len(tasks)} tasks for user {user_id} on {date}")
        
    except Exception as e:
        logger.error(f"Error saving daily tasks: {e}")
        raise

def get_tasks_by_date(user_id, date):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT id, task_text, is_done FROM tasks WHERE user_id = ? AND date = ? ORDER BY id',
            (user_id, date)
        )
        
        tasks = cursor.fetchall()
        conn.close()
        
        logger.info(f"Found {len(tasks)} tasks for user {user_id} on {date}")
        return tasks
        
    except Exception as e:
        logger.error(f"Error getting tasks by date: {e}")
        return []

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

def is_daily_completed(user_id, date):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT is_completed FROM daily_entries WHERE user_id = ? AND date = ?', (user_id, date))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1

def mark_daily_completed(user_id, date):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('UPDATE daily_entries SET is_completed = 1 WHERE user_id = ? AND date = ?', (user_id, date))
    conn.commit()
    conn.close()

def get_all_task_status(user_id, date):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT COUNT(*) as total, SUM(is_done) as done FROM tasks WHERE user_id = ? AND date = ?',
        (user_id, date)
    )
    
    result = cursor.fetchone()
    total, done = result[0], result[1] or 0
    
    cursor.execute('SELECT is_completed FROM daily_entries WHERE user_id = ? AND date = ?', (user_id, date))
    completed_result = cursor.fetchone()
    is_completed = completed_result and completed_result[0] == 1
    
    conn.close()
    return total, done, is_completed

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
/tasks - افزودن تسک‌های امروز یا روز مشخص
/today - نمایش تسک‌های امروز
/date - نمایش تسک‌های روز مشخص
/last5 - نمایش 5 روز گذشته

⏰ یادآوری‌ها:
• ساعت 9 صبح: یادآوری ثبت تسک‌ها (فقط اگر ثبت نکرده باشید)
• ساعت 10 صبح: یادآوری خواب

💡 نکته: در انتهای لیست تسک‌های هر روز، گزینه "✅ اتمام روز" برای تکمیل روز وجود دارد.

برای شروع، تسک‌های امروزتان را با دستور /tasks وارد کنید.
    """
    
    await update.message.reply_text(welcome_message)

def parse_date_from_text(text):
    """Extract date from text in various formats"""
    # Remove /tasks command
    text = text.replace("/tasks", "").strip()
    
    # Look for date patterns at the beginning or end
    date_patterns = [
        r'(\d{4}-\d{1,2}-\d{1,2})',  # YYYY-MM-DD or YYYY-M-D
        r'(\d{1,2}/\d{1,2}/\d{4})',  # DD/MM/YYYY or D/M/YYYY
        r'(\d{1,2}-\d{1,2}-\d{4})',  # DD-MM-YYYY or D-M-YYYY
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            # Convert different formats to YYYY-MM-DD
            if '/' in date_str:
                parts = date_str.split('/')
                if len(parts) == 3:
                    day, month, year = parts
                    date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            elif '-' in date_str and not date_str.startswith('20'):  # DD-MM-YYYY format
                parts = date_str.split('-')
                if len(parts) == 3:
                    day, month, year = parts
                    date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
            # Validate the date
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
                # Remove the date from the original text
                remaining_text = re.sub(pattern, '', text).strip()
                return date_str, remaining_text
            except ValueError:
                continue
    
    return None, text

# Add tasks
async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    
    # Check if user is authorized
    if user_id not in USERS:
        await update.message.reply_text("❌ شما مجاز به استفاده از این ربات نیستید.")
        return
    
    # Get text after /tasks
    task_text = update.message.text.replace("/tasks", "").strip()
    if not task_text:
        await update.message.reply_text(
            "❌ لطفاً بعد از /tasks لیست تسک‌ها رو بنویس (هر خط یک تسک).\n\n"
            "مثال:\n"
            "/tasks تمرین ورزشی\nخرید مواد غذایی\nمطالعه کتاب\n\n"
            "یا برای روز مشخص:\n"
            "/tasks 2024-01-15\nتمرین ورزشی\nخرید مواد غذایی"
        )
        return

    # Try to parse date from the text
    date_from_text, remaining_text = parse_date_from_text(update.message.text)
    
    if date_from_text:
        target_date = date_from_text
        task_content = remaining_text
    else:
        target_date = jdatetime.date.today().strftime("%Y-%m-%d")
        task_content = task_text

    if not task_content.strip():
        await update.message.reply_text("❌ لطفاً حداقل یک تسک وارد کنید.")
        return

    task_list = [task.strip() for task in task_content.split("\n") if task.strip()]

    logger.info(f"User {user_id} ({USERS[user_id]}) adding {len(task_list)} tasks for {target_date}")

    # Save to database
    save_daily_tasks(user_id, target_date, task_list)
    
    # Send confirmation message first
    await update.message.reply_text(f"✅ {len(task_list)} تسک برای تاریخ {target_date} ثبت شد.")

    # Notify partners about task entry
    await notify_task_entry(context, user_id, target_date, len(task_list))

    # Show the tasks
    try:
        await show_tasks_for_date(update, context, user_id, target_date)
    except Exception as e:
        logger.error(f"Error showing tasks: {e}")
        await update.message.reply_text("خطا در نمایش تسک‌ها. از دستور /today استفاده کنید.")

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
    try:
        tasks = get_tasks_by_date(user_id, date)
        logger.info(f"Retrieved {len(tasks)} tasks for user {user_id} on date {date}")
        
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
            button_text = f"{status} {task_text}"
            # Truncate long task names for button display
            if len(button_text) > 60:
                button_text = button_text[:57] + "..."
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"toggle:{task_id}:{date}")])

        # Get completion status
        total, done, is_daily_completed = get_all_task_status(user_id, date)
        
        if is_daily_completed:
            keyboard.append([InlineKeyboardButton("🎉 روز تکمیل شده", callback_data=f"completed:{date}")])
        else:
            keyboard.append([InlineKeyboardButton("✅ اتمام روز", callback_data=f"complete_day:{date}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Create status message
        percentage = int((done / total) * 100) if total > 0 else 0
        status_emoji = "🎉" if is_daily_completed else "🟢" if percentage >= 80 else "🟡" if percentage >= 50 else "🔴"
        
        # Convert date to Persian if possible
        try:
            persian_date = jdatetime.datetime.strptime(date, "%Y-%m-%d").strftime("%Y/%m/%d")
        except:
            persian_date = date
            
        message = f"{status_emoji} تسک‌های {persian_date}:\n({done}/{total} تسک - {percentage}%)"

        if isinstance(update_or_callback, Update):
            await update_or_callback.message.reply_text(message, reply_markup=reply_markup)
        else:  # CallbackQuery
            await update_or_callback.edit_message_text(message, reply_markup=reply_markup)
            
    except Exception as e:
        logger.error(f"Error in show_tasks_for_date: {e}")
        error_message = f"خطا در نمایش تسک‌ها: {str(e)}"
        if isinstance(update_or_callback, Update):
            await update_or_callback.message.reply_text(error_message)
        else:
            await update_or_callback.edit_message_text(error_message)

# Handle button callbacks
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.message.chat_id
    
    if user_id not in USERS:
        await query.edit_message_text("❌ شما مجاز به استفاده از این ربات نیستید.")
        return

    try:
        action, *params = query.data.split(":")
        
        if action == "toggle":
            task_id, date = int(params[0]), params[1]
            # Toggle task status
            toggle_task_status(task_id)
            await show_tasks_for_date(query, context, user_id, date)
            
        elif action == "complete_day":
            date = params[0]
            # Mark the day as completed
            mark_daily_completed(user_id, date)
            
            # Get final statistics
            total, done_count, _ = get_all_task_status(user_id, date)
            percentage = int((done_count / total) * 100) if total > 0 else 0
            
            # Update the message
            await show_tasks_for_date(query, context, user_id, date)
            
            # Send completion message
            status_emoji = "🎉" if percentage >= 80 else "👍" if percentage >= 50 else "💪"
            await query.message.reply_text(
                f"{status_emoji} روز {date} تکمیل شد!\n"
                f"تعداد {done_count} از {total} تسک انجام شد ({percentage}%)."
            )

            # Notify the other users
            other_users = [uid for uid in USERS if uid != user_id]
            for other_user in other_users:
                try:
                    await context.bot.send_message(
                        chat_id=other_user,
                        text=f"📢 {USERS[user_id]} روز {date} خودش رو تکمیل کرد!\n"
                             f"تعداد {done_count} از {total} تسک انجام داد ({percentage}%)."
                    )
                except Exception as e:
                    logger.error(f"Error sending completion notification to {other_user}: {e}")
                    
        elif action == "completed":
            # Already completed, just show info
            await query.answer("این روز قبلاً تکمیل شده است! 🎉")
            
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing callback data: {query.data}, error: {e}")
        await query.edit_message_text("❌ خطا در پردازش درخواست.")
        return

# Debug command to check database status
async def debug_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    
    if user_id not in USERS:
        await update.message.reply_text("❌ شما مجاز به استفاده از این ربات نیستید.")
        return
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if database file exists
        db_exists = os.path.exists(DB_FILE)
        
        # Count total tasks for this user
        cursor.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ?', (user_id,))
        total_tasks = cursor.fetchone()[0]
        
        # Count today's tasks
        today = jdatetime.date.today().strftime("%Y-%m-%d")
        cursor.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ? AND date = ?', (user_id, today))
        today_tasks = cursor.fetchone()[0]
        
        # Get recent tasks
        cursor.execute(
            'SELECT date, task_text FROM tasks WHERE user_id = ? ORDER BY created_at DESC LIMIT 5',
            (user_id,)
        )
        recent_tasks = cursor.fetchall()
        
        conn.close()
        
        message = f"🔧 اطلاعات دیباگ:\n\n"
        message += f"📁 دیتابیس موجود: {'✅' if db_exists else '❌'}\n"
        message += f"📊 کل تسک‌ها: {total_tasks}\n"
        message += f"📅 تسک‌های امروز ({today}): {today_tasks}\n\n"
        
        if recent_tasks:
            message += "📝 آخرین تسک‌ها:\n"
            for date, task_text in recent_tasks:
                message += f"• {date}: {task_text[:30]}...\n"
        else:
            message += "❌ هیچ تسکی یافت نشد\n"
            
        await update.message.reply_text(message)
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در دیباگ: {str(e)}")

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
        is_completed = is_daily_completed(user_id, date)
        
        if is_completed:
            status_emoji = "🎉"
        else:
            status_emoji = "🟢" if percentage >= 80 else "🟡" if percentage >= 50 else "🔴"
        
        # Convert to Persian date if needed
        try:
            persian_date = jdatetime.datetime.strptime(date, "%Y-%m-%d").strftime("%Y/%m/%d")
        except:
            persian_date = date
            
        completion_text = " (تکمیل شده)" if is_completed else ""
        message += f"{status_emoji} {persian_date}: {done}/{total} تسک ({percentage}%){completion_text}\n"
    
    await update.message.reply_text(message)

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
    """Send reminder at 9 AM only to users who haven't entered tasks for today"""
    today = jdatetime.date.today().strftime("%Y-%m-%d")
    
    for user_id in USERS:
        if not has_tasks_for_date(user_id, today):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"⏰ صبح بخیر {USERS[user_id]}!\n\n"
                         f"هنوز تسک‌های امروزت رو وارد نکردی. "
                         f"لطفاً با دستور /tasks تسک‌هات رو ثبت کن."
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
        BotCommand("tasks", "افزودن تسک‌های امروز یا روز مشخص"),
        BotCommand("today", "نمایش تسک‌های امروز"),
        BotCommand("date", "نمایش تسک‌های روز مشخص"),
        BotCommand("last5", "نمایش 5 روز گذشته"),
    ]
    
    await application.bot.set_my_commands(commands)

def main():
    if not BOT_TOKEN:
        logger.error("Please set BOT_TOKEN environment variable!")
        return
    
    # Check if users are configured
    if not USERS:
        logger.error("No users configured! Please set USER1_ID, USER1_NAME, etc. environment variables")
        return

    logger.info(f"Loaded {len(USERS)} users: {list(USERS.values())}")

    # Ensure log directory exists
    os.makedirs('/app/logs', exist_ok=True)

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
    app.add_handler(CommandHandler("debug", debug_info))  # Add debug command
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    # Add error handler
    app.add_error_handler(error_handler)

    # Set bot commands menu
    app.job_queue.run_once(set_bot_commands, when=1)

    # Schedule reminders with Iran timezone
    iran_tz = pytz.timezone('Asia/Tehran')
    
    # Daily task reminder at 9:00 AM Iran time (only for users who haven't entered tasks)
    app.job_queue.run_daily(
        send_daily_task_reminder,
        time=time(hour=9, minute=0, tzinfo=iran_tz),
        name="daily_task_reminder"
    )
    
    # Sleep reminder at 10:00 AM Iran time
    app.job_queue.run_daily(
        send_sleep_reminder,
        time=time(hour=10, minute=0, tzinfo=iran_tz),
        name="sleep_reminder"
    )

    logger.info(f"Starting bot with {len(USERS)} configured users...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()