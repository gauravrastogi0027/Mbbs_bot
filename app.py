from flask import Flask
import os
import asyncio
import threading
from mbbs_bot import main as bot_main

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 MBBS Archive Bot is running! 🎓"

@app.route('/health')
def health():
    return {"status": "healthy", "bot": "running"}

def run_bot():
    try:
        print("🚀 Starting Telegram Bot...")
        asyncio.run(bot_main())
    except Exception as e:
        print(f"❌ Bot error: {e}")

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
