from telegram.ext import CommandHandler, CallbackQueryHandler
from config import USERS, logger, SLEEP_REMINDER_URL
from database import (save_daily_tasks, get_tasks_by_date, toggle_task_status, 
                     mark_all_tasks_done, mark_daily_completed, get_all_task_status, 
                     get_last_n_days, has_tasks_for_date, is_daily_completed)
from utils import parse_date_from_text, show_tasks_for_date, show_complete_day_confirmation
from notifications import notify_task_entry
import jdatetime

async def start(update, context):
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

async def tasks(update, context):
    user_id = update.message.chat_id
    
    if user_id not in USERS:
        await update.message.reply_text("❌ شما مجاز به استفاده از این ربات نیستید.")
        return
    
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

    save_daily_tasks(user_id, target_date, task_list)
    
    await update.message.reply_text(f"✅ {len(task_list)} تسک برای تاریخ {target_date} ثبت شد.")
    await notify_task_entry(context, user_id, target_date, len(task_list))
    await show_tasks_for_date(update, context, user_id, target_date)

async def today(update, context):
    user_id = update.message.chat_id
    today = jdatetime.date.today().strftime("%Y-%m-%d")
    
    if user_id not in USERS:
        await update.message.reply_text("❌ شما مجاز به استفاده از این ربات نیستید.")
        return
    
    await show_tasks_for_date(update, context, user_id, today)

async def date_tasks(update, context):
    user_id = update.message.chat_id
    
    if user_id not in USERS:
        await update.message.reply_text("❌ شما مجاز به استفاده از این ربات نیستید.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("❌ لطفاً تاریخ را به فرمت YYYY-MM-DD (جلالی) وارد کنید.\n\nمثال:\n/date 1404-07-01")
        return
    
    date_str = args[0]
    try:
        jdatetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("❌ فرمت تاریخ اشتباه است. لطفاً به فرمت YYYY-MM-DD (جلالی) وارد کنید.\n\nمثال: 1404-07-01")
        return
    
    await show_tasks_for_date(update, context, user_id, date_str)

async def last5_days(update, context):
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
        
        try:
            persian_date = jdatetime.datetime.strptime(date, "%Y-%m-%d").strftime("%Y/%m/%d")
        except:
            persian_date = date
            
        completion_text = " (تکمیل شده)" if is_completed else ""
        message += f"{status_emoji} {persian_date}: {done}/{total} تسک ({percentage}%){completion_text}\n"
    
    await update.message.reply_text(message)

async def debug_info(update, context):
    user_id = update.message.chat_id
    
    if user_id not in USERS:
        await update.message.reply_text("❌ شما مجاز به استفاده از این ربات نیستید.")
        return
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        db_exists = os.path.exists(DB_FILE)
        
        cursor.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ?', (user_id,))
        total_tasks = cursor.fetchone()[0]
        
        today = jdatetime.date.today().strftime("%Y-%m-%d")
        cursor.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ? AND date = ?', (user_id, today))
        today_tasks = cursor.fetchone()[0]
        
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

async def handle_callback(update, context):
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
            toggle_task_status(task_id)
            await show_tasks_for_date(query, context, user_id, date)
            
        elif action == "complete_day_confirm":
            date = params[0]
            await show_complete_day_confirmation(query, date)
            
        elif action == "cancel_complete":
            date = params[0]
            await show_tasks_for_date(query, context, user_id, date)
            
        elif action == "complete_with_all":
            date = params[0]
            mark_all_tasks_done(user_id, date)
            mark_daily_completed(user_id, date)
            total, done_count, _ = get_all_task_status(user_id, date)
            percentage = int((done_count / total) * 100) if total > 0 else 0
            
            await show_tasks_for_date(query, context, user_id, date)
            await query.message.reply_text(
                f"🎉 روز {date} با انتخاب همه تسک‌ها تکمیل شد!\n"
                f"تعداد {done_count} از {total} تسک انجام شد ({percentage}%)."
            )

            other_users = [uid for uid in USERS if uid != user_id]
            for other_user in other_users:
                try:
                    await context.bot.send_message(
                        chat_id=other_user,
                        text=f"📢 {USERS[user_id]} روز {date} خودش رو با انتخاب همه تسک‌ها تکمیل کرد!\n"
                             f"تعداد {done_count} از {total} تسک انجام داد ({percentage}%)."
                    )
                except Exception as e:
                    logger.error(f"Error sending completion notification to {other_user}: {e}")
                    
        elif action == "complete_day_only":
            date = params[0]
            mark_daily_completed(user_id, date)
            total, done_count, _ = get_all_task_status(user_id, date)
            percentage = int((done_count / total) * 100) if total > 0 else 0
            
            await show_tasks_for_date(query, context, user_id, date)
            status_emoji = "🎉" if percentage >= 80 else "👍" if percentage >= 50 else "💪"
            await query.message.reply_text(
                f"{status_emoji} روز {date} تکمیل شد!\n"
                f"تعداد {done_count} از {total} تسک انجام شد ({percentage}%)."
            )

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
            await query.answer("این روز قبلاً تکمیل شده است! 🎉")
            
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing callback data: {query.data}, error: {e}")
        await query.edit_message_text("❌ خطا در پردازش درخواست.")
        return

async def error_handler(update, context) -> None:
    logger.error(f"Exception while handling an update: {context.error}")

def setup_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tasks", tasks))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("date", date_tasks))
    app.add_handler(CommandHandler("last5", last5_days))
    app.add_handler(CommandHandler("debug", debug_info))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(error_handler)