import re
import jdatetime
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def parse_date_from_text(text):
    text = text.replace("/tasks", "").strip()
    
    date_patterns = [
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            
            if '/' in date_str:
                parts = date_str.split('/')
                separator = '/'
            else:
                parts = date_str.split('-')
                separator = '-'
            
            if len(parts) != 3:
                continue
                
            converted_date = convert_date_to_jalali(parts, separator, date_str)
            
            if converted_date:
                remaining_text = re.sub(pattern, '', text).strip()
                return converted_date, remaining_text
    
    return None, text

def convert_date_to_jalali(parts, separator, original_date_str):
    try:
        if len(parts[0]) == 4:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            if year >= 1300:
                try:
                    jalali_date = jdatetime.date(year, month, day)
                    return jalali_date.strftime("%Y-%m-%d")
                except (ValueError, jdatetime.InvalidJalaliDate):
                    return None
            else:
                try:
                    gregorian_date = datetime(year, month, day).date()
                    jalali_date = jdatetime.date.fromgregorian(date=gregorian_date)
                    return jalali_date.strftime("%Y-%m-%d")
                except ValueError:
                    return None
        
        elif len(parts[2]) == 4:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            if year >= 1300:
                try:
                    jalali_date = jdatetime.date(year, month, day)
                    return jalali_date.strftime("%Y-%m-%d")
                except (ValueError, jdatetime.InvalidJalaliDate):
                    return None
            else:
                try:
                    gregorian_date = datetime(year, month, day).date()
                    jalali_date = jdatetime.date.fromgregorian(date=gregorian_date)
                    return jalali_date.strftime("%Y-%m-%d")
                except ValueError:
                    return None
                    
    except (ValueError, IndexError):
        return None
    
    return None

async def show_tasks_for_date(update_or_callback, context, user_id, date):
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
            if len(button_text) > 60:
                button_text = button_text[:57] + "..."
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"toggle:{task_id}:{date}")])

        total, done, is_daily_completed = get_all_task_status(user_id, date)
        
        if is_daily_completed:
            keyboard.append([InlineKeyboardButton("🎉 روز تکمیل شده", callback_data=f"completed:{date}")])
        else:
            keyboard.append([InlineKeyboardButton("✅ اتمام روز", callback_data=f"complete_day_confirm:{date}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        
        percentage = int((done / total) * 100) if total > 0 else 0
        status_emoji = "🎉" if is_daily_completed else "🟢" if percentage >= 80 else "🟡" if percentage >= 50 else "🔴"
        
        try:
            persian_date = jdatetime.datetime.strptime(date, "%Y-%m-%d").strftime("%Y/%m/%d")
        except:
            persian_date = date
            
        message = f"{status_emoji} تسک‌های {persian_date}:\n({done}/{total} تسک - {percentage}%)"

        if isinstance(update_or_callback, Update):
            await update_or_callback.message.reply_text(message, reply_markup=reply_markup)
        else:
            await update_or_callback.edit_message_text(message, reply_markup=reply_markup)
            
    except Exception as e:
        logger.error(f"Error in show_tasks_for_date: {e}")
        error_message = f"خطا در نمایش تسک‌ها: {str(e)}"
        if isinstance(update_or_callback, Update):
            await update_or_callback.message.reply_text(error_message)
        else:
            await update_or_callback.edit_message_text(error_message)

async def show_complete_day_confirmation(query, date):
    keyboard = [
        [InlineKeyboardButton("❌ انصراف", callback_data=f"cancel_complete:{date}")],
        [InlineKeyboardButton("✅ انتخاب همه تسک‌ها", callback_data=f"complete_with_all:{date}")],
        [InlineKeyboardButton("🎯 فقط اتمام روز", callback_data=f"complete_day_only:{date}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        persian_date = jdatetime.datetime.strptime(date, "%Y-%m-%d").strftime("%Y/%m/%d")
    except:
        persian_date = date
        
    message = f"🤔 نحوه اتمام روز {persian_date} را انتخاب کنید:"
    
    await query.edit_message_text(message, reply_markup=reply_markup)