import os
import sqlite3
import logging
from src.config import logger

DB_FILE = "/app/data/tasks.db"

def init_database():
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

def save_daily_tasks(user_id, date, tasks):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        logger.info(f"Saving {len(tasks)} tasks for user {user_id} on {date}")
        
        cursor.execute('DELETE FROM tasks WHERE user_id = ? AND date = ?', (user_id, date))
        deleted_count = cursor.rowcount
        logger.info(f"Deleted {deleted_count} existing tasks")
        
        for i, task in enumerate(tasks):
            if task.strip():
                cursor.execute(
                    'INSERT INTO tasks (user_id, date, task_text, is_done) VALUES (?, ?, ?, 0)',
                    (user_id, date, task.strip())
                )
                logger.info(f"Inserted task {i+1}: {task.strip()[:50]}...")
        
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

def mark_all_tasks_done(user_id, date):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('UPDATE tasks SET is_done = 1 WHERE user_id = ? AND date = ?', (user_id, date))
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