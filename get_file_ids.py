import sqlite3
import json
from datetime import datetime

def get_all_file_ids():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT file_id, file_type, file_name, category, subject, added_time 
        FROM file_ids 
        ORDER BY added_time DESC
    ''')
    
    files = cursor.fetchall()
    
    print(f"📁 Total Files in Database: {len(files)}\n")
    print("=" * 80)
    
    for file in files:
        file_id, file_type, file_name, category, subject, added_time = file
        timestamp = datetime.fromtimestamp(added_time).strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"📄 File Name: {file_name}")
        print(f"📹 File Type: {file_type.upper()}")
        print(f"📂 Category: {category}")
        print(f"📚 Subject: {subject}")
        print(f"🆔 File ID: {file_id}")
        print(f"⏰ Added: {timestamp}")
        print("-" * 80)
    
    conn.close()

def export_file_ids():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT file_id, file_type, file_name FROM file_ids')
    files = cursor.fetchall()
    
    export_data = {}
    for file_id, file_type, file_name in files:
        if file_type not in export_data:
            export_data[file_type] = []
        
        export_data[file_type].append({
            'file_id': file_id,
            'file_name': file_name
        })
    
    with open('file_ids_export.json', 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"✅ Exported {len(files)} file IDs to 'file_ids_export.json'")
    conn.close()

if __name__ == "__main__":
    print("🤖 MBBS Archive - File ID Manager")
    print("1. View all file IDs")
    print("2. Export file IDs to JSON")
    
    choice = input("\nEnter your choice (1 or 2): ").strip()
    
    if choice == "1":
        get_all_file_ids()
    elif choice == "2":
        export_file_ids()
    else:
        print("❌ Invalid choice!")
