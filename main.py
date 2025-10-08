from telegram.ext import Application
from config import BOT_TOKEN, USERS
from database import init_database
from handlers import setup_handlers
from scheduler import setup_scheduler
from notifications import set_bot_commands

def main():
    if not BOT_TOKEN:
        logger.error("Please set BOT_TOKEN environment variable!")
        return
    
    if not USERS:
        logger.error("No users configured! Please set USER1_ID, USER1_NAME, etc. environment variables")
        return

    logger.info(f"Loaded {len(USERS)} users: {list(USERS.values())}")

    os.makedirs('/app/logs', exist_ok=True)
    init_database()

    app = Application.builder().token(BOT_TOKEN).build()
    setup_handlers(app)
    app.job_queue.run_once(set_bot_commands, when=1)
    setup_scheduler(app)

    logger.info(f"Starting bot with {len(USERS)} configured users...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()