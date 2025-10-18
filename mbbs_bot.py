import os
import asyncio
import sqlite3
import time
import json
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.enums import ParseMode

# Bot Configuration
API_ID = 23208887
API_HASH = "16e19adb7c4199f88810c9339ce9aaac"
BOT_TOKEN = "8267217639:AAFm_VSLGMjwhqEMilB0FmUlbWlwlRoj04A"
ADMIN_ID = 1421077551

# Database setup with better connection handling
class Database:
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        try:
            self.conn = sqlite3.connect('users.db', check_same_thread=False, timeout=30)
            self.cursor = self.conn.cursor()
            self.create_tables()
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
    
    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                premium INTEGER DEFAULT 0,
                login_time INTEGER,
                last_seen INTEGER,
                created_at INTEGER,
                warning_count INTEGER DEFAULT 0,
                is_blocked INTEGER DEFAULT 0
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_ids (
                file_id TEXT PRIMARY KEY,
                file_type TEXT,
                category TEXT,
                subject TEXT,
                file_name TEXT,
                added_time INTEGER,
                is_premium INTEGER DEFAULT 0
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_categories (
                file_id TEXT PRIMARY KEY,
                is_video BOOLEAN DEFAULT 0,
                is_book BOOLEAN DEFAULT 0,
                is_free_video BOOLEAN DEFAULT 0,
                is_premium_video BOOLEAN DEFAULT 0,
                is_free_book BOOLEAN DEFAULT 0,
                is_premium_book BOOLEAN DEFAULT 0
            )
        ''')
        self.conn.commit()
    
    def execute(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
    
    def fetchone(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None
    
    def fetchall(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []

# Initialize database
db = Database()

# Initialize bot with fresh session
app = Client("mbbs_bot_final_fixed", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Auto caption function
def add_caption(filename=""):
    caption = f"""🎓 MBBS ARCHIVE 📚
High-quality MBBS Videos & PDFs for all subjects!
👩‍⚕️ Bot Owner: SUSHMA GANGWAR
🤖 Access the Bot for learning resources

Bot Owner: https://t.me/Sush11112222
Bot Link: http://t.me/MBBS_Archive_Bot

✨ Learn smarter, not harder!"""
    
    if filename:
        caption = f"**{filename}**\n\n" + caption
    return caption

# User management functions
def update_user(user_id, username, first_name, last_name):
    current_time = int(time.time())
    db.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, username, first_name, last_name, last_seen, created_at)
        VALUES (?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM users WHERE user_id = ?), ?))
    ''', (user_id, username, first_name, last_name, current_time, user_id, current_time))

def set_premium(user_id, premium_status):
    db.execute('UPDATE users SET premium = ? WHERE user_id = ?', (premium_status, user_id))

def block_user(user_id):
    db.execute('UPDATE users SET is_blocked = 1 WHERE user_id = ?', (user_id,))

def unblock_user(user_id):
    db.execute('UPDATE users SET is_blocked = 0, warning_count = 0 WHERE user_id = ?', (user_id,))

def get_user(user_id):
    return db.fetchone('SELECT * FROM users WHERE user_id = ?', (user_id,))

def get_user_by_username(username):
    return db.fetchone('SELECT * FROM users WHERE username = ?', (username,))

def get_all_users():
    return db.fetchall('SELECT * FROM users ORDER BY created_at DESC')

def is_premium(user_id):
    user = get_user(user_id)
    return user and user[4] == 1

def is_admin(user_id):
    return user_id == ADMIN_ID

def is_user_blocked(user_id):
    user = get_user(user_id)
    return user and user[9] == 1

def increment_warning(user_id):
    user = get_user(user_id)
    if user:
        current_warnings = user[8] if user[8] else 0
        new_warnings = current_warnings + 1
        db.execute('UPDATE users SET warning_count = ? WHERE user_id = ?', (new_warnings, user_id))
        
        # Block user if warnings exceed 10
        if new_warnings >= 10:
            db.execute('UPDATE users SET is_blocked = 1 WHERE user_id = ?', (user_id,))
            return True  # User blocked
    return False  # User not blocked

# Get file counts for subjects
def get_subject_file_counts(subject, content_type="free"):
    """Get file counts for a subject (free or premium)"""
    is_premium_filter = 1 if content_type == "premium" else 0
    
    video_count = db.fetchone(
        'SELECT COUNT(*) FROM file_ids WHERE subject = ? AND category = ? AND is_premium = ?', 
        (subject, "video", is_premium_filter)
    )[0] or 0
    
    book_count = db.fetchone(
        'SELECT COUNT(*) FROM file_ids WHERE subject = ? AND category = ? AND is_premium = ?', 
        (subject, "book", is_premium_filter)
    )[0] or 0
    
    return video_count, book_count

# Common inline keyboard with owner button
def get_owner_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("SUSHMA GANGWAR (Bot Owner)", url="https://t.me/Sush11112222")]
    ])

# Subjects lists
subjects = [
    "anatomy", "biochemistry", "physiology", "pharmacology", "microbiology", 
    "pathology", "psm", "fmt", "ophthalmology", "ent", "anesthesia", 
    "dermatology", "psychiatry", "radiology", "medicine", "surgery", 
    "orthopedics", "pediatrics", "obsgyne", "rr", "mcq"
]

# Admin warning function
async def admin_warning(message):
    if not is_admin(message.from_user.id):
        warning_text = "🚫 **Access Denied!**\n\nThis command is only for Bot Administrators.\n\nIf you need assistance, contact the bot owner."
        await message.reply_text(
            warning_text,
            reply_markup=get_owner_button(),
            parse_mode=ParseMode.MARKDOWN
        )
        return True
    return False

# Blocked user check function
async def blocked_user_check(user_id, message=None, callback_query=None):
    if is_user_blocked(user_id):
        block_message = """⚠️ Access Denied!
You have been blocked from using this bot. 🚫

If you think this is a mistake or want to regain access,
please contact the bot owner for review and unblocking.

🕵️‍♂️ Unauthorized or repeated violations may lead to a permanent ban."""
        
        if message:
            await message.reply_text(
                block_message,
                reply_markup=get_owner_button(),
                parse_mode=ParseMode.MARKDOWN
            )
        elif callback_query:
            await callback_query.answer(block_message, show_alert=True)
        return True
    return False
# Start command - FIXED: Proper blocking check
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    user = message.from_user
    update_user(user.id, user.username, user.first_name, user.last_name)
    
    # Check if user is blocked
    if await blocked_user_check(user.id, message=message):
        return
    
    welcome_text = """🎓 Welcome to the MBBS Learning Bot! 📚  
Unlock premium access to exclusive **MBBS Videos & Books**  
and take your medical journey to the next level! 💉🩺  

💰 To get full access, contact the Bot Owner for Subscription:  
👩‍⚕️ **SUSHMA GANGWAR**  
🔗 https://t.me/Sush11112222  

🚀 Start learning smarter — not harder!"""
    
    await message.reply_text(
        welcome_text,
        reply_markup=get_owner_button(),
        parse_mode=ParseMode.MARKDOWN
    )

# Help command - FIXED: Blocking check
@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    user_id = message.from_user.id
    if await blocked_user_check(user_id, message=message):
        return
    
    help_text = """🤖 **MBBS ARCHIVE BOT - Complete Guide** 📚

**Available Commands:**

🔹 `/start` - Start the bot and view welcome message
🔹 `/videos` - Access all MBBS video lectures  
🔹 `/books` - Get textbooks, notes, and study materials
🔹 `/login` - Login to your account
🔹 `/logout` - Logout from your account
🔹 `/premium_user` - Check premium features and subscription
🔹 `/upi_id` - Get admin UPI ID for payment
🔹 `/send_screenshot` - Send payment screenshot to owner
🔹 `/premium_content` - Access exclusive premium materials
🔹 `/myplan` - Check your premium plan details
🔹 `/transfer` - Gift premium to friends
🔹 `/speedtest` - Check server speed
🔹 `/get_username` - Get your Telegram username
🔹 `/get_id` - Get your Telegram user ID
🔹 `/get_file_ids` - Get all saved file IDs (Admin only)
🔹 `/help` - View this help message

**Admin Only Commands:**
🔸 `/add_user_premium` - Add premium access to user
🔸 `/remove_user_premium` - Remove premium access
🔸 `/block_user` - Block a user from using bot
🔸 `/unblock_user` - Unblock a blocked user
🔸 `/broadcast` - Broadcast message to all users
🔸 `/stats` - View bot statistics
🔸 `/user_info` - Get user information
🔸 `/clear_database` - Clear complete database (Admin only)
🔸 `/clear_subject` - Clear specific subject data (Admin only)
🔸 `/remove_via_file_id` - Remove file using file ID (Admin only)
🔸 `/blocked_user_list` - Show all blocked users (Admin only)

**How to Use:**
1. Use `/start` to begin
2. Browse free content with `/videos` and `/books`
3. For premium access, use `/premium_user`
4. Make payment and send screenshot with `/send_screenshot`
5. Enjoy unlimited access! 🎉

**Need Help?** Contact: @Sush11112222"""
    
    await message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

# Videos command with file counts - FIXED: Blocking check
@app.on_message(filters.command("videos"))
async def videos_command(client, message: Message):
    user_id = message.from_user.id
    if await blocked_user_check(user_id, message=message):
        return
    
    keyboard = []
    row = []
    for subject in subjects:
        video_count, book_count = get_subject_file_counts(subject, "free")
        if video_count > 0:
            button_text = f"{subject.upper()} ({video_count})"
            row.append(InlineKeyboardButton(button_text, callback_data=f"v_{subject}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("SUSHMA GANGWAR (Bot Owner)", url="https://t.me/Sush11112222")])
    
    if not keyboard or len(keyboard) == 1:  # Only owner button
        await message.reply_text("📭 No video content available yet!")
        return
    
    await message.reply_text(
        "🎬 **Select Subject for Videos:**\n\n📊 Numbers show available video counts",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Books command with file counts - FIXED: Blocking check
@app.on_message(filters.command("books"))
async def books_command(client, message: Message):
    user_id = message.from_user.id
    if await blocked_user_check(user_id, message=message):
        return
    
    keyboard = []
    row = []
    for subject in subjects:
        video_count, book_count = get_subject_file_counts(subject, "free")
        if book_count > 0:
            button_text = f"{subject.upper()} ({book_count})"
            row.append(InlineKeyboardButton(button_text, callback_data=f"b_{subject}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("SUSHMA GANGWAR (Bot Owner)", url="https://t.me/Sush11112222")])
    
    if not keyboard or len(keyboard) == 1:  # Only owner button
        await message.reply_text("📭 No book content available yet!")
        return
    
    await message.reply_text(
        "📚 **Select Subject for Books:**\n\n📊 Numbers show available book counts",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Premium user command - FIXED: Blocking check
@app.on_message(filters.command("premium_user"))
async def premium_command(client, message: Message):
    user_id = message.from_user.id
    if await blocked_user_check(user_id, message=message):
        return
    
    premium_text = """🎓 Upgrade to Premium Now!

Unlock exclusive access to all MBBS Video Lectures and Medical Books & Notes 📚✨

✅ High-quality MBBS video lectures
✅ Premium study materials & textbooks
✅ Exclusive access — only for Premium Members

💰 Subscription Fee: ₹100 only
📅 Validity: Lifetime Access

To become a Premium User, please make a payment of ₹100 using the UPI link below 👇
👉 UPI ID: `111kuldeep222-4@okicici`

Once payment is done, send a screenshot of your transaction to our support chat to activate your Premium Membership instantly 🔥

📩 Join Now & Boost Your MBBS Journey!
Start learning smarter — not harder 💪"""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Send Screenshot", callback_data="send_ss")],
        [InlineKeyboardButton("SUSHMA GANGWAR (Bot Owner)", url="https://t.me/Sush11112222")]
    ])
    
    await message.reply_text(
        premium_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# NEW Premium Content command with file counts - FIXED: Blocking check
@app.on_message(filters.command("premium_content"))
async def premium_content_command(client, message: Message):
    user_id = message.from_user.id
    if await blocked_user_check(user_id, message=message):
        return
    
    if not is_premium(user_id):
        await message.reply_text(
            "❌ **Premium Access Required!**\n\n"
            "This content is only available for premium members.\n"
            "Use `/premium_user` to upgrade your account.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    premium_content_text = """💎 You are a Premium Member!
Your ₹100 Premium Plan is active 🎉

🔓 You now have access to:
📚 MBBS Books
🎥 HD Video Lectures
🧠 Notes & QBank

⚠️ Please don't share these links publicly — access is for premium members only.

Enjoy your learning journey with us! ✨"""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 PREMIUM VIDEOS", callback_data="premium_videos")],
        [InlineKeyboardButton("📚 PREMIUM BOOKS", callback_data="premium_books")],
        [InlineKeyboardButton("SUSHMA GANGWAR (Bot Owner)", url="https://t.me/Sush11112222")]
    ])
    
    await message.reply_text(
        premium_content_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# Send screenshot command - FIXED: Blocking check
@app.on_message(filters.command("send_screenshot"))
async def screenshot_command(client, message: Message):
    user_id = message.from_user.id
    if await blocked_user_check(user_id, message=message):
        return
    
    ss_text = """🎉 Thank you for your payment of ₹100! 💰  
You're just one step away from unlocking your Premium MBBS Videos & Books 📚✨  

📸 Please send your payment screenshot to the Bot Owner now 👇  

👩‍⚕️ SUSHMA GANGWAR  
🔗 https://t.me/Sush11112222  

Once your payment is verified, your Premium Access will be activated instantly 🚀  
Stay tuned for exclusive medical learning content! 🩺🎓"""
    
    await message.reply_text(
        ss_text,
        reply_markup=get_owner_button(),
        parse_mode=ParseMode.MARKDOWN
    )

# UPI ID command - FIXED: Blocking check
@app.on_message(filters.command("upi_id"))
async def upi_command(client, message: Message):
    user_id = message.from_user.id
    if await blocked_user_check(user_id, message=message):
        return
    
    await message.reply_text(
        "💳 **UPI ID for Payment:**\n\n`111kuldeep222-4@okicici`\n\nCopy this UPI ID and make payment of ₹100",
        parse_mode=ParseMode.MARKDOWN
    )

# Login command - FIXED: Blocking check
@app.on_message(filters.command("login"))
async def login_command(client, message: Message):
    user_id = message.from_user.id
    if await blocked_user_check(user_id, message=message):
        return
    
    user = message.from_user
    update_user(user.id, user.username, user.first_name, user.last_name)
    db.execute('UPDATE users SET login_time = ? WHERE user_id = ?', (int(time.time()), user.id))
    
    await message.reply_text("✅ Login successful! You can now access bot features.")

# Logout command - FIXED: Blocking check
@app.on_message(filters.command("logout"))
async def logout_command(client, message: Message):
    user_id = message.from_user.id
    if await blocked_user_check(user_id, message=message):
        return
    
    db.execute('UPDATE users SET login_time = NULL WHERE user_id = ?', (message.from_user.id,))
    await message.reply_text("✅ Logout successful!")

# Myplan command - FIXED: Premium users stay premium
@app.on_message(filters.command("myplan"))
async def myplan_command(client, message: Message):
    user_id = message.from_user.id
    if await blocked_user_check(user_id, message=message):
        return
    
    user = get_user(user_id)
    
    if user and user[4] == 1:
        plan_text = """🎉 **Premium Plan Active**

✅ You have **LIFETIME PREMIUM ACCESS**!
📚 Unlimited access to all MBBS videos & books
🚀 Full features unlocked
⭐ Priority support

💎 **You're enjoying the best learning experience!**"""
    else:
        plan_text = """🔒 **Free Plan**

📖 Limited access available
🎬 Only basic books accessible
🚫 Videos are premium only

💎 **UPGRADE TO PREMIUM NOW!**
💰 Special Discount: Only ₹100 for LIFETIME!
🎁 Get unlimited videos + premium books
⚡ Instant activation

👉 Use `/premium_user` to upgrade now!"""
    
    await message.reply_text(plan_text, parse_mode=ParseMode.MARKDOWN)
# NEW Block User command - FIXED: Proper blocking
@app.on_message(filters.command("block_user"))
async def block_user_command(client, message: Message):
    if await admin_warning(message):
        return
        
    if len(message.command) > 1:
        user_input = message.command[1].strip()
        
        # Check if input is user ID or username
        if user_input.isdigit():
            user_id = int(user_input)
            user = get_user(user_id)
        else:
            username = user_input.lstrip('@')
            user = get_user_by_username(username)
        
        if user:
            if user[0] == ADMIN_ID:
                await message.reply_text("❌ You cannot block the bot owner!")
                return
            
            block_user(user[0])
            await message.reply_text(
                f"✅ User **{user[2]}** (ID: `{user[0]}`) has been blocked!\n\n"
                f"They will no longer be able to use the bot until unblocked.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await message.reply_text("❌ User not found! Please check the user ID or username.")
    else:
        await message.reply_text(
            "🚫 **Block User**\n\n"
            "Usage: `/block_user <user_id_or_username>`\n\n"
            "Examples:\n"
            "• `/block_user 123456789`\n"
            "• `/block_user @username`",
            parse_mode=ParseMode.MARKDOWN
        )

# NEW Unblock User command - FIXED: Proper unblocking
@app.on_message(filters.command("unblock_user"))
async def unblock_user_command(client, message: Message):
    if await admin_warning(message):
        return
        
    if len(message.command) > 1:
        user_input = message.command[1].strip()
        
        # Check if input is user ID or username
        if user_input.isdigit():
            user_id = int(user_input)
            user = get_user(user_id)
        else:
            username = user_input.lstrip('@')
            user = get_user_by_username(username)
        
        if user:
            unblock_user(user[0])
            
            unblock_message = f"""✅ **ACCOUNT UNBLOCKED SUCCESSFULLY** ✅

Dear **{user[2]}**,

Your account has been successfully unblocked. You can now use the bot again.

⚠️ **IMPORTANT WARNING:**
- This is your **FINAL CHANCE**
- Any further policy violations will result in **PERMANENT BAN**
- Use the bot responsibly and follow all guidelines

We hope you have a better experience this time! ✨"""

            # Send message to admin
            await message.reply_text(
                f"✅ User **{user[2]}** (ID: `{user[0]}`) has been unblocked!",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Send message to unblocked user
            try:
                await client.send_message(
                    user[0],
                    unblock_message,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await message.reply_text("ℹ️ Could not send unblock notification to user (they might have blocked the bot).")
        else:
            await message.reply_text("❌ User not found! Please check the user ID or username.")
    else:
        await message.reply_text(
            "✅ **Unblock User**\n\n"
            "Usage: `/unblock_user <user_id_or_username>`\n\n"
            "Examples:\n"
            "• `/unblock_user 123456789`\n"
            "• `/unblock_user @username`",
            parse_mode=ParseMode.MARKDOWN
        )

# NEW Blocked User List command
@app.on_message(filters.command("blocked_user_list"))
async def blocked_user_list_command(client, message: Message):
    if await admin_warning(message):
        return
    
    blocked_users = db.fetchall('SELECT * FROM users WHERE is_blocked = 1 ORDER BY created_at DESC')
    
    if not blocked_users:
        await message.reply_text("✅ No blocked users found!")
        return
    
    blocked_text = "🚫 **Blocked Users List** 🚫\n\n"
    
    for user in blocked_users[:50]:  # Show first 50 blocked users
        user_id, username, first_name, last_name, premium, login_time, last_seen, created_at, warnings, blocked = user
        
        username_display = f"@{username}" if username else "No Username"
        join_date = datetime.fromtimestamp(created_at).strftime('%d-%m-%Y') if created_at else "Unknown"
        
        blocked_text += f"**{first_name} {last_name or ''}**\n"
        blocked_text += f"🆔 ID: `{user_id}`\n"
        blocked_text += f"👤 Username: {username_display}\n"
        blocked_text += f"⚠️ Warnings: {warnings if warnings else 0}/10\n"
        blocked_text += f"📅 Joined: {join_date}\n"
        blocked_text += "─" * 30 + "\n"
    
    if len(blocked_users) > 50:
        blocked_text += f"\n📋 Showing 50 out of {len(blocked_users)} blocked users"
    
    await message.reply_text(blocked_text, parse_mode=ParseMode.MARKDOWN)

# Get username command - FIXED: Blocking check
@app.on_message(filters.command("get_username"))
async def username_command(client, message: Message):
    user_id = message.from_user.id
    if await blocked_user_check(user_id, message=message):
        return
    
    user = message.from_user
    username = f"@{user.username}" if user.username else "Not set"
    await message.reply_text(f"👤 **Your Username:** {username}")

# Get ID command - FIXED: Blocking check
@app.on_message(filters.command("get_id"))
async def id_command(client, message: Message):
    user_id = message.from_user.id
    if await blocked_user_check(user_id, message=message):
        return
    
    await message.reply_text(f"🆔 **Your User ID:** `{message.from_user.id}`", parse_mode=ParseMode.MARKDOWN)

# Speedtest command - FIXED: Blocking check
@app.on_message(filters.command("speedtest"))
async def speedtest_command(client, message: Message):
    user_id = message.from_user.id
    if await blocked_user_check(user_id, message=message):
        return
    
    start_time = time.time()
    msg = await message.reply_text("🚀 Testing server speed...")
    end_time = time.time()
    response_time = round((end_time - start_time) * 1000, 2)
    
    await msg.edit_text(f"📊 **Server Speed Test:**\n\n⏱ Response Time: {response_time}ms\n✅ Bot is running smoothly!")

# ADVANCED Get File IDs command with complete file IDs and timestamps
@app.on_message(filters.command("get_file_ids"))
async def get_file_ids_command(client, message: Message):
    if await admin_warning(message):
        return
    
    total_files = db.fetchone('SELECT COUNT(*) FROM file_ids')[0] or 0
    file_stats = db.fetchall('SELECT file_type, COUNT(*) FROM file_ids GROUP BY file_type')
    
    files_text = f"📁 **File Database Statistics**\n\n📊 Total Files: {total_files}\n\n"
    
    for file_type, count in file_stats:
        if file_type and count:
            files_text += f"📹 {file_type.upper()} Files: {count}\n"
    
    # Get all files with complete details
    all_files = db.fetchall('SELECT file_id, file_type, file_name, category, subject, is_premium, added_time FROM file_ids ORDER BY added_time DESC')
    
    if all_files:
        files_text += f"\n📋 **All Files ({len(all_files)}):**\n\n"
        for file_id, file_type, file_name, category, subject, is_premium, added_time in all_files:
            if file_id:
                # Format timestamp
                timestamp = datetime.fromtimestamp(added_time).strftime('%Y-%m-%d %H:%M:%S') if added_time else "Unknown"
                
                # Determine content type
                content_type = "💎 PREMIUM" if is_premium else "🆓 FREE"
                file_type_display = file_type.upper() if file_type else "UNKNOWN"
                category_display = category.upper() if category else "UNKNOWN"
                subject_display = subject.upper() if subject else "UNKNOWN"
                name = file_name if file_name else "No Name"
                
                files_text += f"**{content_type} {file_type_display}**\n"
                files_text += f"📝 Name: {name}\n"
                files_text += f"📂 Category: {category_display}\n"
                files_text += f"📚 Subject: {subject_display}\n"
                files_text += f"🕒 Added: {timestamp}\n"
                files_text += f"🆔 File ID: `{file_id}`\n"
                files_text += "─" * 40 + "\n\n"
    
    if len(files_text) > 4000:
        # If message is too long, send as multiple messages
        parts = [files_text[i:i+4000] for i in range(0, len(files_text), 4000)]
        for i, part in enumerate(parts):
            if i == 0:
                await message.reply_text(part, parse_mode=ParseMode.MARKDOWN)
            else:
                await message.reply_text(part, parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply_text(files_text, parse_mode=ParseMode.MARKDOWN)

# NEW Remove via File ID command
@app.on_message(filters.command("remove_via_file_id"))
async def remove_via_file_id_command(client, message: Message):
    if await admin_warning(message):
        return
        
    if len(message.command) > 1:
        file_id = message.command[1].strip()
        
        # Check if file exists
        file_data = db.fetchone('SELECT file_name, file_type, subject, category, is_premium FROM file_ids WHERE file_id = ?', (file_id,))
        
        if file_data:
            file_name, file_type, subject, category, is_premium = file_data
            
            # Delete the file
            db.execute('DELETE FROM file_ids WHERE file_id = ?', (file_id,))
            db.execute('DELETE FROM file_categories WHERE file_id = ?', (file_id,))
            
            content_type = "Premium" if is_premium else "Free"
            await message.reply_text(
                f"✅ **File Successfully Removed!**\n\n"
                f"📝 File Name: {file_name}\n"
                f"📁 Type: {file_type.upper()}\n"
                f"📚 Subject: {subject.upper()}\n"
                f"🎯 Category: {content_type} {category.upper()}\n"
                f"🆔 File ID: `{file_id}`",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await message.reply_text("❌ File not found! Please check the file ID.")
    else:
        await message.reply_text(
            "🗑️ **Remove File via File ID**\n\n"
            "Usage: `/remove_via_file_id <file_id>`\n\n"
            "Example:\n"
            "• `/remove_via_file_id BAACAgUAAxkBAAIFB2jw9jPCxqevMaIynV2jP20JfYDlAAI`\n\n"
            "💡 Use `/get_file_ids` to get file IDs",
            parse_mode=ParseMode.MARKDOWN
        )
# IMPROVED Clear Database command - FIXED: All buttons working properly
@app.on_message(filters.command("clear_database"))
async def clear_database_command(client, message: Message):
    if await admin_warning(message):
        return
    
    # First ask what type of content to clear
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 Free VIDEOS", callback_data="clear_db_free_videos"),
            InlineKeyboardButton("💎 Premium VIDEOS", callback_data="clear_db_premium_videos")
        ],
        [
            InlineKeyboardButton("📚 Free BOOKS", callback_data="clear_db_free_books"),
            InlineKeyboardButton("💎 Premium BOOKS", callback_data="clear_db_premium_books")
        ],
        [
            InlineKeyboardButton("🗑️ Clear ALL Content", callback_data="clear_db_all_content"),
            InlineKeyboardButton("❌ Cancel", callback_data="clear_cancel")
        ]
    ])
    
    free_videos = db.fetchone('SELECT COUNT(*) FROM file_ids WHERE category = ? AND is_premium = ?', ("video", 0))[0] or 0
    premium_videos = db.fetchone('SELECT COUNT(*) FROM file_ids WHERE category = ? AND is_premium = ?', ("video", 1))[0] or 0
    free_books = db.fetchone('SELECT COUNT(*) FROM file_ids WHERE category = ? AND is_premium = ?', ("book", 0))[0] or 0
    premium_books = db.fetchone('SELECT COUNT(*) FROM file_ids WHERE category = ? AND is_premium = ?', ("book", 1))[0] or 0
    
    warning_text = f"""🚨 **Clear Content Database** 🚨

⚠️ **WARNING:** This will only delete CONTENT files, NOT user data or premium subscriptions!
📊 **Current Content Stats:**
• 🎬 Free Videos: {free_videos}
• 💎 Premium Videos: {premium_videos}
• 📚 Free Books: {free_books}
• 💎 Premium Books: {premium_books}

🔒 **What type of content do you want to clear?**"""
    
    await message.reply_text(
        warning_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# IMPROVED Clear Subject command - FIXED: Working properly
@app.on_message(filters.command("clear_subject"))
async def clear_subject_command(client, message: Message):
    if await admin_warning(message):
        return
    
    # First ask Free or Premium content
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🆓 FREE Content", callback_data="clear_subject_free"),
            InlineKeyboardButton("💎 PREMIUM Content", callback_data="clear_subject_premium")
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="clear_cancel")]
    ])
    
    await message.reply_text(
        "🗑️ **Clear Subject Content**\n\n"
        "First, select the type of content you want to clear:",
        reply_markup=keyboard
    )

# TRANSFER command - FIXED: Premium stays until removed
@app.on_message(filters.command("transfer"))
async def transfer_command(client, message: Message):
    user_id = message.from_user.id
    if await blocked_user_check(user_id, message=message):
        return
    
    current_user = get_user(user_id)
    
    if not current_user:
        await message.reply_text("❌ Please use `/start` command first!")
        return
    
    if not is_premium(user_id):
        await message.reply_text(
            "❌ **You need to be a Premium User to transfer premium!**\n\n"
            "Upgrade to premium first using `/premium_user` command.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if len(message.command) > 1:
        target_input = message.command[1].strip()
        
        # Check if input is user ID or username
        if target_input.isdigit():
            target_id = int(target_input)
            target_user = get_user(target_id)
        else:
            username = target_input.lstrip('@')
            target_user = get_user_by_username(username)
        
        if not target_user:
            await message.reply_text("❌ User not found! Please check the user ID or username.")
            return
        
        if target_user[0] == user_id:
            await message.reply_text("❌ You cannot transfer premium to yourself!")
            return
        
        if is_premium(target_user[0]):
            await message.reply_text(f"❌ User **{target_user[2]}** is already a premium user!")
            return
        
        # Confirmation keyboard for transfer
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ YES, Transfer Premium", callback_data=f"transfer_confirm_{target_user[0]}"),
                InlineKeyboardButton("❌ NO, Cancel", callback_data="transfer_cancel")
            ]
        ])
        
        confirmation_text = f"""🔄 **Transfer Premium Membership**

⚠️ **Please Confirm Transfer:**
• From: **You** ({current_user[2]})
• To: **{target_user[2]}** (@{target_user[1] or 'No Username'})
• User ID: `{target_user[0]}`

📝 **After Transfer:**
✅ Target user will get **PREMIUM ACCESS**
❌ You will become **FREE USER**

🔒 **Are you sure you want to transfer your premium membership?**"""
        
        await message.reply_text(
            confirmation_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.reply_text(
            "🔄 **Transfer Premium to Another User**\n\n"
            "Usage: `/transfer <user_id_or_username>`\n\n"
            "Examples:\n"
            "• `/transfer 123456789`\n"
            "• `/transfer @username`\n\n"
            "⚠️ **Note:** After transfer, you will lose your premium access and the target user will get it.",
            parse_mode=ParseMode.MARKDOWN
        )

# Admin commands with protection
@app.on_message(filters.command("add_user_premium"))
async def add_premium_command(client, message: Message):
    if await admin_warning(message):
        return
        
    if len(message.command) > 1:
        user_input = message.command[1].strip()
        
        # Check if input is user ID or username
        if user_input.isdigit():
            # It's a user ID
            user_id = int(user_input)
            user = get_user(user_id)
        else:
            # It's a username (remove @ if present)
            username = user_input.lstrip('@')
            user = get_user_by_username(username)
        
        if user:
            set_premium(user[0], 1)
            await message.reply_text(f"✅ User **{user[2]}** (ID: `{user[0]}`) added to premium!", parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply_text("❌ User not found! Please check the user ID or username.")
    else:
        await message.reply_text("Usage: `/add_user_premium <user_id_or_username>`\n\nExample:\n`/add_user_premium 123456789`\n`/add_user_premium @username`", parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("remove_user_premium"))
async def remove_premium_command(client, message: Message):
    if await admin_warning(message):
        return
        
    if len(message.command) > 1:
        user_input = message.command[1].strip()
        
        # Check if input is user ID or username
        if user_input.isdigit():
            # It's a user ID
            user_id = int(user_input)
            user = get_user(user_id)
        else:
            # It's a username (remove @ if present)
            username = user_input.lstrip('@')
            user = get_user_by_username(username)
        
        if user:
            set_premium(user[0], 0)
            await message.reply_text(f"✅ User **{user[2]}** (ID: `{user[0]}`) removed from premium!", parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply_text("❌ User not found! Please check the user ID or username.")
    else:
        await message.reply_text("Usage: `/remove_user_premium <user_id_or_username>`\n\nExample:\n`/remove_user_premium 123456789`\n`/remove_user_premium @username`", parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("stats"))
async def stats_command(client, message: Message):
    if await admin_warning(message):
        return
    
    total_users = db.fetchone('SELECT COUNT(*) FROM users')[0] or 0
    premium_users = db.fetchone('SELECT COUNT(*) FROM users WHERE premium = 1')[0] or 0
    blocked_users = db.fetchone('SELECT COUNT(*) FROM users WHERE is_blocked = 1')[0] or 0
    total_files = db.fetchone('SELECT COUNT(*) FROM file_ids')[0] or 0
    
    stats_text = f"""📊 **Bot Statistics**

👥 Total Users: {total_users}
⭐ Premium Users: {premium_users}
🆓 Free Users: {total_users - premium_users}
🚫 Blocked Users: {blocked_users}
📁 Total Files: {total_files}

🤖 Bot Status: ✅ Running
🎯 Admin: @Sush11112222"""
    
    await message.reply_text(stats_text)
# IMPROVED USER INFO COMMAND - FIXED: Shows all users list
@app.on_message(filters.command("user_info"))
async def user_info_command(client, message: Message):
    if await admin_warning(message):
        return
        
    if len(message.command) > 1:
        # Show specific user info
        user_input = message.command[1].strip()
        
        # Check if input is user ID or username
        if user_input.isdigit():
            # It's a user ID
            user_id = int(user_input)
            user = get_user(user_id)
        else:
            # It's a username (remove @ if present)
            username = user_input.lstrip('@')
            user = get_user_by_username(username)
        
        if user:
            premium_status = "✅ Premium" if user[4] == 1 else "❌ Free"
            login_time = datetime.fromtimestamp(user[5]).strftime('%Y-%m-%d %H:%M:%S') if user[5] else "Never"
            last_seen = datetime.fromtimestamp(user[6]).strftime('%Y-%m-%d %H:%M:%S') if user[6] else "Never"
            join_date = datetime.fromtimestamp(user[7]).strftime('%Y-%m-%d %H:%M:%S') if user[7] else "Unknown"
            warnings = user[8] if user[8] else 0
            blocked_status = "🚫 BLOCKED" if user[9] == 1 else "✅ Active"
            
            info_text = f"""👤 **User Information**

🆔 User ID: `{user[0]}`
👤 Username: @{user[1] if user[1] else 'N/A'}
📛 Name: {user[2]} {user[3] or ''}
🎯 Plan: {premium_status}
⚠️ Warnings: {warnings}/10
🔐 Status: {blocked_status}
🔐 Login Time: {login_time}
👀 Last Seen: {last_seen}
📅 Join Date: {join_date}"""
            
            await message.reply_text(info_text, parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply_text("❌ User not found! Please check the user ID or username.")
    else:
        # Show all users list
        users = get_all_users()
        
        if not users:
            await message.reply_text("📭 No users found in database!")
            return
        
        users_text = "👥 **All Bot Users**\n\n"
        
        for user in users[:50]:  # Show first 50 users
            user_id, username, first_name, last_name, premium, login_time, last_seen, created_at, warnings, blocked = user
            
            premium_status = "⭐ Premium" if premium == 1 else "🆓 Free"
            username_display = f"@{username}" if username else "No Username"
            join_date = datetime.fromtimestamp(created_at).strftime('%d-%m-%Y') if created_at else "Unknown"
            blocked_status = "🚫" if blocked == 1 else "✅"
            
            users_text += f"**{first_name} {last_name or ''}** {blocked_status}\n"
            users_text += f"🆔 ID: `{user_id}`\n"
            users_text += f"👤 Username: {username_display}\n"
            users_text += f"🎯 Status: {premium_status}\n"
            users_text += f"⚠️ Warnings: {warnings if warnings else 0}/10\n"
            users_text += f"📅 Joined: {join_date}\n"
            users_text += "─" * 30 + "\n"
        
        if len(users) > 50:
            users_text += f"\n📋 Showing 50 out of {len(users)} users"
        
        await message.reply_text(users_text, parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("broadcast"))
async def broadcast_command(client, message: Message):
    if await admin_warning(message):
        return
        
    if len(message.command) > 1:
        broadcast_text = " ".join(message.command[1:])
        users = db.fetchall('SELECT user_id FROM users WHERE is_blocked = 0')
        
        success = 0
        failed = 0
        
        broadcast_msg = await message.reply_text("📢 Starting broadcast...")
        
        for user in users:
            try:
                await client.send_message(user[0], f"📢 **Broadcast Message:**\n\n{broadcast_text}")
                success += 1
            except:
                failed += 1
            await asyncio.sleep(0.1)
        
        await broadcast_msg.edit_text(f"✅ Broadcast Complete!\n\n✅ Success: {success}\n❌ Failed: {failed}")
    else:
        await message.reply_text("Usage: /broadcast <message>")

# IMPROVED File handling for admin - FIXED: Working properly
@app.on_message(filters.user(ADMIN_ID) & (filters.video | filters.document | filters.audio | filters.photo))
async def handle_files(client, message: Message):
    file_id = None
    file_type = None
    file_name = None
    
    if message.video:
        file_type = "video"
        file_id = message.video.file_id
        file_name = message.video.file_name or "Video File"
    elif message.document:
        file_type = "document"
        file_id = message.document.file_id
        file_name = message.document.file_name or "Document File"
    elif message.audio:
        file_type = "audio"
        file_id = message.audio.file_id
        file_name = getattr(message.audio, 'file_name', 'Audio File') or "Audio File"
    elif message.photo:
        file_type = "photo"
        file_id = message.photo.file_id
        file_name = "Photo"
    
    if file_id:
        # Save file to database temporarily
        db.execute('''
            INSERT OR REPLACE INTO file_ids (file_id, file_type, category, subject, file_name, added_time, is_premium)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (file_id, file_type, "pending", "pending", file_name, int(time.time()), 0))
        
        # Show 4 category options
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎬 Save as VIDEOS", callback_data=f"cat_free_v_{file_id[:30]}"),
                InlineKeyboardButton("💎 Save as PREMIUM VIDEOS", callback_data=f"cat_premium_v_{file_id[:30]}")
            ],
            [
                InlineKeyboardButton("📚 Save as BOOKS", callback_data=f"cat_free_b_{file_id[:30]}"),
                InlineKeyboardButton("💎 Save as PREMIUM BOOKS", callback_data=f"cat_premium_b_{file_id[:30]}")
            ]
        ])
        
        await message.reply_text(
            f"💾 **File Received!**\n\n"
            f"📁 Type: {file_type.upper()}\n"
            f"📝 Name: {file_name}\n\n"
            f"Select the category for this file:",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )

# File handling for non-admin users - FIXED: Warning system
@app.on_message(~filters.user(ADMIN_ID) & (filters.video | filters.document | filters.audio | filters.photo))
async def handle_unauthorized_files(client, message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        return
    
    # Increment warning count
    is_blocked = increment_warning(user_id)
    current_warnings = user[8] if user[8] else 0
    new_warnings = current_warnings + 1
    
    if is_blocked:
        await message.reply_text(
            f"🚫 **You are permanently blocked from using this bot!**\n\n"
            f"You have exceeded the maximum warning limit ({new_warnings}/10).\n"
            f"Contact the bot owner if you think this is a mistake.",
            reply_markup=get_owner_button()
        )
    else:
        remaining_warnings = 10 - new_warnings
        await message.reply_text(
            f"⚠️ **WARNING: Unauthorized File Upload**\n\n"
            f"You are not authorized to send files to this bot!\n"
            f"**Warning Count:** {new_warnings}/10\n"
            f"**Remaining Attempts:** {remaining_warnings}\n\n"
            f"🚫 If you reach 10 warnings, you will be permanently blocked!\n"
            f"Please contact the bot owner for assistance.",
            reply_markup=get_owner_button()
        )

# Function to create subject keyboard with file counts - FIXED
def create_subject_keyboard(file_id_short, category_prefix, content_type="free"):
    keyboard = []
    row = []
    
    for subject in subjects:
        video_count, book_count = get_subject_file_counts(subject, content_type)
        
        if category_prefix.startswith("cat_free_v") or category_prefix.startswith("cat_premium_v"):
            # For videos, show video count
            count = video_count
            button_text = f"{subject.upper()} ({count})"
        else:
            # For books, show book count
            count = book_count
            button_text = f"{subject.upper()} ({count})"
            
        row.append(InlineKeyboardButton(button_text, callback_data=f"{category_prefix}_{subject}_{file_id_short}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

# Function to create premium content keyboard with counts - FIXED
def create_premium_content_keyboard(callback_prefix, content_type):
    keyboard = []
    row = []
    
    for subject in subjects:
        video_count, book_count = get_subject_file_counts(subject, "premium")
        
        if content_type == "video":
            count = video_count
            button_text = f"{subject.upper()} ({count})" if count > 0 else f"{subject.upper()} (0)"
        else:
            count = book_count
            button_text = f"{subject.upper()} ({count})" if count > 0 else f"{subject.upper()} (0)"
        
        if count > 0:  # Only show subjects with content
            row.append(InlineKeyboardButton(button_text, callback_data=f"{callback_prefix}_{subject}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
    
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)
# IMPROVED Callback query handler - FIXED: All callbacks working with blocked user check
@app.on_callback_query()
async def handle_callbacks(client, callback_query: CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    # Check if user is blocked for all callbacks
    if await blocked_user_check(user_id, callback_query=callback_query):
        return
    
    # Handle premium content selection with counts - FIXED
    if data == "premium_videos":
        if not is_premium(user_id) and not is_admin(user_id):
            await callback_query.answer("❌ Premium content! Upgrade to access videos.", show_alert=True)
            return
        
        keyboard = create_premium_content_keyboard("pv", "video")
        
        if not keyboard.inline_keyboard:
            await callback_query.answer("❌ No premium videos available yet!", show_alert=True)
            return
        
        await callback_query.message.edit_text(
            "🎬 **Select Subject for Premium Videos:**\n\n📊 Numbers show available video counts",
            reply_markup=keyboard
        )
        return
    
    elif data == "premium_books":
        if not is_premium(user_id) and not is_admin(user_id):
            await callback_query.answer("❌ Premium content! Upgrade to access books.", show_alert=True)
            return
        
        keyboard = create_premium_content_keyboard("pb", "book")
        
        if not keyboard.inline_keyboard:
            await callback_query.answer("❌ No premium books available yet!", show_alert=True)
            return
        
        await callback_query.message.edit_text(
            "📚 **Select Subject for Premium Books:**\n\n📊 Numbers show available book counts",
            reply_markup=keyboard
        )
        return
    
    # Handle premium video and book subject selection - FIXED
    elif data.startswith("pv_") or data.startswith("pb_"):
        subject = data.split("_")[1]
        file_type = "video" if data.startswith("pv_") else "book"
        
        # Check premium access
        if not is_premium(user_id) and not is_admin(user_id):
            await callback_query.answer("❌ Premium content! Upgrade to access.", show_alert=True)
            return
        
        files = db.fetchall('SELECT file_id, file_name FROM file_ids WHERE category = ? AND subject = ? AND is_premium = ?', 
                          (file_type, subject, 1))
        
        if files:
            sent_count = 0
            for file_id, file_name in files:
                try:
                    if file_type == "video":
                        await client.send_video(user_id, file_id, caption=add_caption(file_name))
                    else:
                        await client.send_document(user_id, file_id, caption=add_caption(file_name))
                    sent_count += 1
                    await asyncio.sleep(0.5)  # Reduced delay
                except Exception as e:
                    print(f"Error sending file: {e}")
                    continue
            
            if sent_count > 0:
                await callback_query.answer(f"✅ Sent {sent_count} premium {file_type}s!")
            else:
                await callback_query.answer("❌ Failed to send files!", show_alert=True)
        else:
            await callback_query.answer("❌ No premium files available for this subject yet!", show_alert=True)
        return
    
    # Handle free video and book subject selection - FIXED
    elif data.startswith("v_") or data.startswith("b_"):
        subject = data.split("_")[1]
        file_type = "video" if data.startswith("v_") else "book"
        
        files = db.fetchall('SELECT file_id, file_name FROM file_ids WHERE category = ? AND subject = ? AND is_premium = ?', 
                          (file_type, subject, 0))
        
        if files:
            sent_count = 0
            for file_id, file_name in files:
                try:
                    if file_type == "video":
                        await client.send_video(user_id, file_id, caption=add_caption(file_name))
                    else:
                        await client.send_document(user_id, file_id, caption=add_caption(file_name))
                    sent_count += 1
                    await asyncio.sleep(0.5)  # Reduced delay
                except Exception as e:
                    print(f"Error sending file: {e}")
                    continue
            
            if sent_count > 0:
                await callback_query.answer(f"✅ Sent {sent_count} {file_type}s!")
            else:
                await callback_query.answer("❌ Failed to send files!", show_alert=True)
        else:
            await callback_query.answer("❌ No files available for this subject yet!", show_alert=True)
        return
    
    # Handle category selection with 4 options - FIXED
    elif data.startswith("cat_"):
        parts = data.split("_")
        if len(parts) >= 4:
            content_type = parts[1]  # free or premium
            file_type = parts[2]     # v or b
            short_file_id = parts[3]
            
            # Find the complete file ID from database
            file_data = db.fetchone('SELECT file_id FROM file_ids WHERE file_id LIKE ?', (f"{short_file_id}%",))
            
            if file_data:
                file_id = file_data[0]
                
                # Determine category and premium status
                category = "video" if file_type == "v" else "book"
                is_premium_content = 1 if content_type == "premium" else 0
                
                # Store category temporarily
                db.execute('UPDATE file_ids SET category = ?, is_premium = ? WHERE file_id = ?', 
                         (f"{category}_pending", is_premium_content, file_id))
                
                # Show subject selection keyboard
                subject_keyboard = create_subject_keyboard(short_file_id, "subj", content_type)
                
                category_name = "Premium" if is_premium_content else "Free"
                file_type_name = "Videos" if file_type == "v" else "Books"
                
                await callback_query.message.edit_text(
                    f"📂 **Select Subject for {category_name} {file_type_name}:**\n\n"
                    f"Choose the subject where this file should be saved:",
                    reply_markup=subject_keyboard
                )
            else:
                await callback_query.answer("❌ File not found in database!", show_alert=True)
        return
    
    # Handle subject selection for file categorization - FIXED
    elif data.startswith("subj_"):
        parts = data.split("_")
        if len(parts) >= 3:
            subject_name = parts[1]
            short_file_id = parts[2]
            
            # Find the complete file ID from database
            file_data = db.fetchone('SELECT file_id, category, is_premium FROM file_ids WHERE file_id LIKE ?', (f"{short_file_id}%",))
            
            if file_data:
                file_id, current_category, is_premium_content = file_data
                
                # Extract category from current_category (e.g., "video_pending" -> "video")
                category = current_category.split("_")[0] if "_" in current_category else "general"
                
                # Finalize file categorization
                db.execute('UPDATE file_ids SET category = ?, subject = ?, is_premium = ? WHERE file_id = ?', 
                         (category, subject_name, is_premium_content, file_id))
                
                # Also update categories table
                db.execute('''
                    INSERT OR REPLACE INTO file_categories (file_id, is_video, is_book, is_free_video, is_premium_video, is_free_book, is_premium_book)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (file_id, 
                      1 if category == "video" else 0, 
                      1 if category == "book" else 0,
                      1 if category == "video" and is_premium_content == 0 else 0,
                      1 if category == "video" and is_premium_content == 1 else 0,
                      1 if category == "book" and is_premium_content == 0 else 0,
                      1 if category == "book" and is_premium_content == 1 else 0))
                
                # SUCCESS CONFIRMATION MESSAGE
                content_type = "Premium" if is_premium_content else "Free"
                await callback_query.answer(
                    f"✅ {content_type} {category.upper()} successfully saved to {subject_name.upper()}!",
                    show_alert=True
                )
                
                file_name = "Unknown"
                if callback_query.message.reply_to_message:
                    if callback_query.message.reply_to_message.video:
                        file_name = callback_query.message.reply_to_message.video.file_name or "Video"
                    elif callback_query.message.reply_to_message.document:
                        file_name = callback_query.message.reply_to_message.document.file_name or "Document"
                    elif callback_query.message.reply_to_message.audio:
                        file_name = callback_query.message.reply_to_message.audio.file_name or "Audio"
                    elif callback_query.message.reply_to_message.photo:
                        file_name = "Photo"
                
                await callback_query.message.edit_text(
                    f"✅ **File Successfully Saved!**\n\n"
                    f"📁 Category: {content_type} {category.upper()}\n"
                    f"📚 Subject: {subject_name.upper()}\n"
                    f"📝 File: {file_name}\n\n"
                    f"🎉 **File has been perfectly saved to {subject_name.upper()} {content_type} section!**"
                )
            else:
                await callback_query.answer("❌ File not found!", show_alert=True)
        return
    # Handle clear subject type selection (Free or Premium) - FIXED
    elif data.startswith("clear_subject_"):
        if not is_admin(user_id):
            await callback_query.answer("❌ Admin only command!", show_alert=True)
            return
        
        parts = data.split("_")
        if len(parts) >= 3:
            content_type = parts[2]  # free or premium
            
            # Show Free Videos/Books or Premium Videos/Books options
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎬 VIDEOS", callback_data=f"clear_sub_{content_type}_videos"),
                    InlineKeyboardButton("📚 BOOKS", callback_data=f"clear_sub_{content_type}_books")
                ],
                [InlineKeyboardButton("❌ Cancel", callback_data="clear_cancel")]
            ])
            
            content_type_name = "Free" if content_type == "free" else "Premium"
            await callback_query.message.edit_text(
                f"🗑️ **Clear {content_type_name} Content**\n\n"
                f"Select which type of {content_type.lower()} content you want to delete:",
                reply_markup=keyboard
            )
        return
    
    # Handle clear subject content type (Videos or Books) - FIXED
    elif data.startswith("clear_sub_") and (data.endswith("_videos") or data.endswith("_books")):
        if not is_admin(user_id):
            await callback_query.answer("❌ Admin only command!", show_alert=True)
            return
        
        parts = data.split("_")
        if len(parts) >= 4:
            content_type = parts[2]  # free or premium
            file_type = parts[3]     # videos or books
            
            # Show subject selection for the chosen content type and file type
            keyboard = []
            row = []
            for subject in subjects:
                video_count, book_count = get_subject_file_counts(subject, content_type)
                
                if file_type == "videos":
                    count = video_count
                else:
                    count = book_count
                
                if count > 0:
                    button_text = f"{subject.upper()} ({count})"
                    row.append(InlineKeyboardButton(button_text, callback_data=f"clear_sub_{content_type}_{file_type}_{subject}"))
                    if len(row) == 2:
                        keyboard.append(row)
                        row = []
            
            if row:
                keyboard.append(row)
            
            if not keyboard:
                await callback_query.answer(f"ℹ️ No {content_type} {file_type} found in any subject!", show_alert=True)
                return
            
            keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="clear_cancel")])
            
            content_type_name = "Free" if content_type == "free" else "Premium"
            file_type_name = "Videos" if file_type == "videos" else "Books"
            await callback_query.message.edit_text(
                f"🗑️ **Clear {content_type_name} {file_type_name}**\n\n"
                f"Select which subject's {content_type.lower()} {file_type.lower()} you want to delete:\n\n"
                f"📊 Numbers show file counts",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    # Handle subject selection for clearing with final warning - FIXED
    elif data.startswith("clear_sub_") and len(data.split("_")) >= 5:
        if not is_admin(user_id):
            await callback_query.answer("❌ Admin only command!", show_alert=True)
            return
        
        parts = data.split("_")
        if len(parts) >= 5:
            content_type = parts[2]  # free or premium
            file_type = parts[3]     # videos or books
            subject_name = parts[4]
            
            video_count, book_count = get_subject_file_counts(subject_name, content_type)
            
            if file_type == "videos":
                count = video_count
            else:
                count = book_count
            
            if count == 0:
                await callback_query.answer(f"ℹ️ No {content_type} {file_type} found in {subject_name.upper()}!", show_alert=True)
                return
            
            # Final confirmation for subject clearing
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ YES, Delete", callback_data=f"confirm_clear_sub_{content_type}_{file_type}_{subject_name}"),
                    InlineKeyboardButton("❌ NO, Cancel", callback_data="clear_cancel")
                ]
            ])
            
            content_type_name = "Free" if content_type == "free" else "Premium"
            file_type_name = "Videos" if file_type == "videos" else "Books"
            warning_text = f"""🚨 **FINAL WARNING - Delete {content_type_name} {subject_name.upper()} {file_type_name}** 🚨

⚠️ **This will delete permanently:**
• {count} {content_type.lower()} {file_type.lower()}

❌ **This action cannot be undone!**

🔒 **Are you absolutely sure?**"""
            
            await callback_query.message.edit_text(warning_text, reply_markup=keyboard)
        return
    
    # Handle clear database category selection - FIXED: All buttons working
    elif data.startswith("clear_db_"):
        if not is_admin(user_id):
            await callback_query.answer("❌ Admin only command!", show_alert=True)
            return
        
        parts = data.split("_")
        if len(parts) >= 3:
            clear_type = parts[2]
            
            if clear_type == "free_videos":
                file_count = db.fetchone('SELECT COUNT(*) FROM file_ids WHERE category = ? AND is_premium = ?', ("video", 0))[0] or 0
                if file_count == 0:
                    await callback_query.answer("ℹ️ No free video files found to delete!", show_alert=True)
                    return
                
                # Final confirmation for free videos
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ YES, Delete FREE Videos", callback_data="confirm_clear_free_videos"),
                        InlineKeyboardButton("❌ NO, Cancel", callback_data="clear_cancel")
                    ]
                ])
                
                await callback_query.message.edit_text(
                    f"🚨 **FINAL WARNING - Delete ALL Free Videos** 🚨\n\n"
                    f"⚠️ **This will delete {file_count} FREE video files permanently!**\n"
                    f"❌ **This action cannot be undone!**\n\n"
                    f"🔒 **Are you absolutely sure?**",
                    reply_markup=keyboard
                )
                return
            
            elif clear_type == "premium_videos":
                file_count = db.fetchone('SELECT COUNT(*) FROM file_ids WHERE category = ? AND is_premium = ?', ("video", 1))[0] or 0
                if file_count == 0:
                    await callback_query.answer("ℹ️ No premium video files found to delete!", show_alert=True)
                    return
                
                # Final confirmation for premium videos
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ YES, Delete PREMIUM Videos", callback_data="confirm_clear_premium_videos"),
                        InlineKeyboardButton("❌ NO, Cancel", callback_data="clear_cancel")
                    ]
                ])
                
                await callback_query.message.edit_text(
                    f"🚨 **FINAL WARNING - Delete ALL Premium Videos** 🚨\n\n"
                    f"⚠️ **This will delete {file_count} PREMIUM video files permanently!**\n"
                    f"❌ **This action cannot be undone!**\n\n"
                    f"🔒 **Are you absolutely sure?**",
                    reply_markup=keyboard
                )
                return
            
            elif clear_type == "free_books":
                file_count = db.fetchone('SELECT COUNT(*) FROM file_ids WHERE category = ? AND is_premium = ?', ("book", 0))[0] or 0
                if file_count == 0:
                    await callback_query.answer("ℹ️ No free book files found to delete!", show_alert=True)
                    return
                
                # Final confirmation for free books
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ YES, Delete FREE Books", callback_data="confirm_clear_free_books"),
                        InlineKeyboardButton("❌ NO, Cancel", callback_data="clear_cancel")
                    ]
                ])
                
                await callback_query.message.edit_text(
                    f"🚨 **FINAL WARNING - Delete ALL Free Books** 🚨\n\n"
                    f"⚠️ **This will delete {file_count} FREE book files permanently!**\n"
                    f"❌ **This action cannot be undone!**\n\n"
                    f"🔒 **Are you absolutely sure?**",
                    reply_markup=keyboard
                )
                return
            
            elif clear_type == "premium_books":
                file_count = db.fetchone('SELECT COUNT(*) FROM file_ids WHERE category = ? AND is_premium = ?', ("book", 1))[0] or 0
                if file_count == 0:
                    await callback_query.answer("ℹ️ No premium book files found to delete!", show_alert=True)
                    return
                
                # Final confirmation for premium books
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ YES, Delete PREMIUM Books", callback_data="confirm_clear_premium_books"),
                        InlineKeyboardButton("❌ NO, Cancel", callback_data="clear_cancel")
                    ]
                ])
                
                await callback_query.message.edit_text(
                    f"🚨 **FINAL WARNING - Delete ALL Premium Books** 🚨\n\n"
                    f"⚠️ **This will delete {file_count} PREMIUM book files permanently!**\n"
                    f"❌ **This action cannot be undone!**\n\n"
                    f"🔒 **Are you absolutely sure?**",
                    reply_markup=keyboard
                )
                return
            
            elif clear_type == "all_content":
                total_files = db.fetchone('SELECT COUNT(*) FROM file_ids')[0] or 0
                if total_files == 0:
                    await callback_query.answer("ℹ️ No files found to delete!", show_alert=True)
                    return
                
                # Final confirmation for all content
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ YES, Delete ALL Content", callback_data="confirm_clear_all_content"),
                        InlineKeyboardButton("❌ NO, Cancel", callback_data="clear_cancel")
                    ]
                ])
                
                await callback_query.message.edit_text(
                    f"🚨 **FINAL WARNING - Delete ALL Content** 🚨\n\n"
                    f"⚠️ **This will delete {total_files} files permanently!**\n"
                    f"❌ **This action cannot be undone!**\n\n"
                    f"🔒 **Are you absolutely sure?**",
                    reply_markup=keyboard
                )
                return
        return
    # Handle final confirmations for clearing - FIXED: All working
    elif data.startswith("confirm_clear_"):
        if not is_admin(user_id):
            await callback_query.answer("❌ Admin only command!", show_alert=True)
            return
        
        if data == "confirm_clear_free_videos":
            db.execute('DELETE FROM file_ids WHERE category = ? AND is_premium = ?', ("video", 0))
            await callback_query.message.edit_text("✅ **All Free Video Files Deleted Successfully!**")
            return
        
        elif data == "confirm_clear_premium_videos":
            db.execute('DELETE FROM file_ids WHERE category = ? AND is_premium = ?', ("video", 1))
            await callback_query.message.edit_text("✅ **All Premium Video Files Deleted Successfully!**")
            return
        
        elif data == "confirm_clear_free_books":
            db.execute('DELETE FROM file_ids WHERE category = ? AND is_premium = ?', ("book", 0))
            await callback_query.message.edit_text("✅ **All Free Book Files Deleted Successfully!**")
            return
        
        elif data == "confirm_clear_premium_books":
            db.execute('DELETE FROM file_ids WHERE category = ? AND is_premium = ?', ("book", 1))
            await callback_query.message.edit_text("✅ **All Premium Book Files Deleted Successfully!**")
            return
        
        elif data == "confirm_clear_all_content":
            db.execute('DELETE FROM file_ids')
            await callback_query.message.edit_text("🗑️ **All Content Deleted Successfully!**\n\nAll files have been removed from database!")
            return
        
        elif data.startswith("confirm_clear_sub_"):
            parts = data.split("_")
            if len(parts) >= 6:
                content_type = parts[3]
                file_type = parts[4]
                subject_name = parts[5]
                
                is_premium_filter = 1 if content_type == "premium" else 0
                category = "video" if file_type == "videos" else "book"
                
                db.execute('DELETE FROM file_ids WHERE subject = ? AND category = ? AND is_premium = ?', 
                         (subject_name, category, is_premium_filter))
                
                content_type_name = "Free" if content_type == "free" else "Premium"
                file_type_name = "Videos" if file_type == "videos" else "Books"
                await callback_query.message.edit_text(f"✅ **{content_type_name} {subject_name.upper()} {file_type_name} Deleted Successfully!**")
                return
        return
    
    # Handle transfer confirmation - FIXED
    elif data.startswith("transfer_confirm_"):
        parts = data.split("_")
        if len(parts) >= 3:
            target_user_id = int(parts[2])
            current_user_id = user_id
            
            # Transfer premium: remove from current user, add to target user
            set_premium(current_user_id, 0)  # Current user becomes free
            set_premium(target_user_id, 1)   # Target user becomes premium
            
            target_user = get_user(target_user_id)
            
            await callback_query.message.edit_text(
                f"🔄 **Premium Transfer Successful!**\n\n"
                f"✅ **{target_user[2]}** is now a **PREMIUM USER**\n"
                f"❌ You are now a **FREE USER**\n\n"
                f"💎 Premium membership has been transferred successfully!"
            )
        return
    
    elif data == "transfer_cancel":
        await callback_query.message.edit_text("✅ **Transfer Cancelled!**\n\nNo changes were made to premium membership.")
        return
    
    elif data == "clear_cancel":
        await callback_query.message.edit_text("✅ **Operation Cancelled!**\n\nNo changes were made to the database.")
        return
    
    elif data == "send_ss":
        await callback_query.answer()
        await client.send_message(
            user_id,
            "📸 Please send your payment screenshot to the Bot Owner:\n\n@Sush11112222",
            reply_markup=get_owner_button()
        )

print("🤖 MBBS Archive Bot is starting...")
app.run()
