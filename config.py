import os
import logging
import jdatetime

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