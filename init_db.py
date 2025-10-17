import sqlite3
import json

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Create tables
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        premium INTEGER DEFAULT 0,
        login_time INTEGER,
        last_seen INTEGER,
        created_at INTEGER
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS file_ids (
        file_id TEXT PRIMARY KEY,
        file_type TEXT,
        category TEXT,
        subject TEXT,
        file_name TEXT,
        added_time INTEGER
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS file_categories (
        file_id TEXT PRIMARY KEY,
        is_video BOOLEAN DEFAULT 0,
        is_book BOOLEAN DEFAULT 0
    )
''')

# Create user_stats.json if not exists
try:
    with open('user_stats.json', 'r') as f:
        pass
except FileNotFoundError:
    with open('user_stats.json', 'w') as f:
        json.dump({}, f)

print("✅ Database and files initialized successfully!")
conn.commit()
conn.close()
