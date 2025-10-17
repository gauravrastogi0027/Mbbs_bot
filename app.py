from flask import Flask
import os
import asyncio
import threading
import time

app = Flask(__name__)

# Health check route for Render
@app.route('/')
def home():
    return "🤖 MBBS Archive Bot is running! 🎓"

# Health check endpoint
@app.route('/health')
def health():
    return {"status": "healthy", "bot": "running"}

# Import and run bot in background
def run_bot():
    try:
        print("🚀 Starting Telegram Bot...")
        time.sleep(5)  # Wait for Flask to start
        
        # Import and run the bot
        from mbbs_bot import main
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Bot error: {e}")
        import traceback
        traceback.print_exc()

# Start bot when app starts
if __name__ == '__main__':
    # Start bot in separate thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    print("🌐 Flask server starting...")
    
    # Start Flask app
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
