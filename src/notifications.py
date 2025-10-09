from telegram import BotCommand
import jdatetime
from .config import logger, USERS, SLEEP_REMINDER_URL
from .database import has_tasks_for_date

async def notify_task_entry(context, user_id, date, task_count):
    other_users = [uid for uid in USERS if uid != user_id]
    for other_user in other_users:
        try:
            await context.bot.send_message(
                chat_id=other_user,
                text=f"📝 {USERS[user_id]} برای تاریخ {date} تعداد {task_count} تسک ثبت کرد."
            )
        except Exception as e:
            logger.error(f"Error sending task entry notification to {other_user}: {e}")

async def send_daily_task_reminder(context):
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

async def send_sleep_reminder(context):
    for user_id in USERS:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"😴 {USERS[user_id]} عزیز، وقت ثبت ساعات خوابت رسیده!\n\n{SLEEP_REMINDER_URL}"
            )
        except Exception as e:
            logger.error(f"Error sending sleep reminder to {user_id}: {e}")

async def set_bot_commands(application):
    commands = [
        BotCommand("start", "شروع و راهنما"),
        BotCommand("tasks", "افزودن تسک‌های امروز یا روز مشخص"),
        BotCommand("today", "نمایش تسک‌های امروز"),
        BotCommand("date", "نمایش تسک‌های روز مشخص"),
        BotCommand("last5", "نمایش 5 روز گذشته"),
    ]
    
    await application.bot.set_my_commands(commands)