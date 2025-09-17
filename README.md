# Telegram Task Bot

A Persian Telegram bot for daily task management and tracking.

## Features

- Add daily tasks using `/tasks` command
- Interactive task completion with checkboxes
- Daily progress tracking with `/done` command
- Cross-user notifications
- Persistent data storage

## Setup

### Prerequisites

- Python 3.11+
- Telegram Bot Token (from @BotFather)

### Local Development

1. Clone the repository:
```bash
git clone <your-repo-url>
cd telegram-bot
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env file and add your BOT_TOKEN
```

5. Run the bot:
```bash
python main.py
```

## Deployment Options

### Option 1: Docker (Recommended)

1. Build and run with Docker Compose:
```bash
docker-compose up -d
```

2. View logs:
```bash
docker-compose logs -f
```

3. Stop the bot:
```bash
docker-compose down
```

### Option 2: Systemd Service (Ubuntu/Debian)

1. Copy the service file:
```bash
sudo cp telegram-bot.service /etc/systemd/system/
```

2. Edit the service file with your paths and token:
```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

3. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot.service
sudo systemctl start telegram-bot.service
```

4. Check status:
```bash
sudo systemctl status telegram-bot.service
```

## Bot Commands

- `/start` - Welcome message
- `/tasks <task1>\n<task2>\n...` - Add daily tasks
- `/done` - Show completion summary and notify others

## Configuration

### Adding Users

The bot now loads user configuration from environment variables. Edit your `.env` file:

```bash
# Bot Token
BOT_TOKEN=your_bot_token_here


# Add users:
# USER_1_ID=another_chat_id
# USER_1_NAME=Another Name
```

### Getting Your Chat ID

1. Start the bot and send `/start`
2. If you're not configured, the bot will show your Chat ID
3. Add your Chat ID to the `.env` file
4. Restart the bot

### User Authorization

Only users configured in the environment variables can use the bot. Unauthorized users will see their Chat ID and be instructed to contact the admin.

## File Structure

```
telegram-bot/
├── main.py              # Main bot application
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker configuration
├── docker-compose.yml  # Docker Compose configuration
├── .env.example        # Environment variables template
├── .gitignore         # Git ignore rules
├── telegram-bot.service # Systemd service file
└── README.md          # This file
```

## Data Persistence

Task data is stored in `tasks_data.json` file, which persists between bot restarts.