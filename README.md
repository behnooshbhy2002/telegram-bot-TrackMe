# Telegram Task Management Bot

A comprehensive Persian Telegram bot for daily task management and tracking with persistent SQLite storage, automated reminders, and multi-user collaboration features.

## Features

### 📋 Task Management

- Add daily tasks for today or specific dates (Jalali/Gregorian support)
- Interactive task completion with checkboxes
- Mark individual tasks as done/undone
- Complete entire days with options to mark all tasks as done
- View tasks for specific dates or recent history

### 🔔 Smart Notifications

- Daily task reminder at 9:00 AM (only if no tasks entered)
- Sleep reminder at 10:00 AM with Samsung Health integration
- Cross-user notifications when teammates add or complete tasks
- All notifications use Iran timezone

### 📊 Progress Tracking

- Real-time completion percentages
- 5-day history summary with color-coded status
- Daily completion tracking separate from individual task status
- Visual progress indicators (🎉🟢🟡🔴)

### 🗓️ Date Support

- Full Jalali (Persian) calendar support
- Automatic conversion between Jalali and Gregorian dates
- Flexible date input formats (YYYY-MM-DD, DD/MM/YYYY)
- Persian date display

### 💾 Data Persistence

- SQLite database with persistent storage
- Separate tracking for tasks and daily completion status
- Data survives bot restarts and system reboots
- Organized data and logs directories

## Setup

### Prerequisites

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Docker (optional, for containerized deployment)

### Local Development

1. **Clone the repository:**

```bash
git clone <your-repo-url>
cd telegram-task-bot
```

2. **Create virtual environment:**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**

```bash
cp .env.example .env
# Edit .env file with your configuration
```

5. **Configure users in .env:**

```bash
BOT_TOKEN=your_bot_token_here

# Add users (you can add as many as needed)
USER1_ID=123456789
USER1_NAME=John Doe
USER2_ID=987654321
USER2_NAME=Jane Smith
```

6. **Run the bot:**

```bash
python main.py
```

## Deployment Options

### Option 1: Docker Compose (Recommended)

1. **Create environment file:**

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
BOT_TOKEN=your_bot_token_here
USER1_ID=123456789
USER1_NAME=Alice
USER2_ID=987654321
USER2_NAME=Bob
```

2. **Build and run:**

```bash
docker-compose up -d
```

3. **View logs:**

```bash
docker-compose logs -f telegram-bot
```

4. **Stop the bot:**

```bash
docker-compose down
```

The Docker setup includes:

- Automatic restart policy
- Persistent data and logs volumes
- Health checks for monitoring
- Asia/Tehran timezone configuration
- Isolated network for security

### Option 2: Systemd Service (Linux)

1. **Create service file:**

```bash
sudo nano /etc/systemd/system/telegram-task-bot.service
```

```ini
[Unit]
Description=Telegram Task Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/telegram-task-bot
Environment=BOT_TOKEN=your_token_here
Environment=USER1_ID=123456789
Environment=USER1_NAME=User Name
ExecStart=/path/to/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. **Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-task-bot.service
sudo systemctl start telegram-task-bot.service
```

## Bot Commands

### Main Commands

- `/start` - Welcome message and bot introduction
- `/tasks [date] <task1>\n<task2>\n...` - Add tasks for today or specific date
- `/today` - Show today's tasks with interactive buttons
- `/date YYYY-MM-DD` - Show tasks for specific date
- `/last5` - Show 5-day progress summary

### Task Entry Examples

**Add tasks for today:**

```
/tasks Buy groceries
Exercise for 30 minutes
Read a book chapter
```

**Add tasks for specific date:**

```
/tasks 1403-05-15
Meeting with team
Complete project report
Call dentist
```

**Mixed Gregorian/Jalali support:**

```
/tasks 2024-08-15
Review code
/tasks 15/08/2024
Write documentation
```

### Interactive Features

- ✅/⬜ Click to toggle task completion
- 📊 Real-time progress percentages
- 🎯 "Complete Day" options:
  - Mark all remaining tasks as done
  - Complete day with current progress
- 🔄 Live status updates

## Configuration

### Adding Users

Users are configured via environment variables. Each user needs an ID and name:

```bash
# Format: USER{N}_ID and USER{N}_NAME
USER1_ID=123456789
USER1_NAME=Alice
USER2_ID=987654321
USER2_NAME=Bob
USER3_ID=456789123
USER3_NAME=Charlie
```

### Getting Your Telegram Chat ID

1. Start the bot and send `/start`
2. If you're not authorized, the bot will display your Chat ID
3. Add your Chat ID to the environment variables
4. Restart the bot

### Sleep Reminder Integration

The bot includes Samsung Health sleep tracking integration. Users receive a reminder at 10:00 AM with a deep link to Samsung Health's sleep tracking feature.

## File Structure

```
telegram-task-bot/
├── main.py                 # Main bot application
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose setup
├── .env.example          # Environment template
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## Data Persistence

### Database Schema

The bot uses SQLite with two main tables:

**tasks table:**

- `id` - Primary key
- `user_id` - Telegram user ID
- `date` - Task date (YYYY-MM-DD)
- `task_text` - Task description
- `is_done` - Completion status (0/1)
- `created_at` - Timestamp

**daily_entries table:**

- `id` - Primary key
- `user_id` - Telegram user ID
- `date` - Entry date (YYYY-MM-DD)
- `total_tasks` - Total tasks for the day
- `is_completed` - Day completion status (0/1)
- `created_at` - Timestamp

### Health Monitoring

The Docker setup includes health checks that verify database connectivity:

```bash
# Check health status
docker-compose ps

# View health check logs
docker inspect telegram-task-bot --format='{{range .State.Health.Log}}{{.Output}}{{end}}'
```

## Notifications & Reminders

### Automatic Reminders

- **9:00 AM**: Task entry reminder (only for users without tasks)
- **10:00 AM**: Sleep tracking reminder (all users)

### Cross-User Notifications

- When someone adds tasks: "📝 [User] added X tasks for [date]"
- When someone completes a day: "📢 [User] completed their day with X/Y tasks (Z%)"

### Timezone Support

All times use Asia/Tehran timezone for consistent Iranian user experience.

## Troubleshooting

### Common Issues

**Bot not responding:**

```bash
# Check logs
docker-compose logs telegram-bot
```

**Database issues:**

```bash
# Debug command
/debug
```

**Permission errors:**

```bash
# Check user authorization
# Verify USER_ID environment variables
```

### Debug Command

The `/debug` command provides:

- Database file existence
- Total task count
- Today's task count
- Recent task samples

## Development

### Adding New Features

1. **Database changes:** Update `init_database()` function
2. **New commands:** Add command handlers in `main()`
3. **Callbacks:** Extend `handle_callback()` function
4. **Notifications:** Add to existing notification functions

### Code Structure

- **Database operations:** Functions prefixed with `save_`, `get_`, `mark_`
- **Command handlers:** Functions matching command names
- **Callback handlers:** Pattern matching in `handle_callback()`
- **Notifications:** Separate async functions for different reminder types

## License

This project is open source. Feel free to modify and distribute according to your needs.

## Support

For issues or feature requests, please check the logs first:

```bash
docker-compose logs -f telegram-bot
```

The bot includes comprehensive logging for troubleshooting and monitoring.
