from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import time
from pytz import timezone
from notifications import send_daily_task_reminder, send_sleep_reminder

scheduler = AsyncIOScheduler(timezone=timezone('Asia/Tehran'))

def setup_scheduler(app):
    iran_tz = timezone('Asia/Tehran')
    
    app.job_queue.run_daily(
        send_daily_task_reminder,
        time=time(hour=9, minute=0, tzinfo=iran_tz),
        name="daily_task_reminder"
    )
    
    app.job_queue.run_daily(
        send_sleep_reminder,
        time=time(hour=10, minute=0, tzinfo=iran_tz),
        name="sleep_reminder"
    )