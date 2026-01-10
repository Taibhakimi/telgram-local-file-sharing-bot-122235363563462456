import os
import logging
import datetime
import sqlite3
import random
import string
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# ========== CONFIGURATION ==========
BOT_TOKEN = "your token here"
ADMIN_ID = your telgram id
FILES_DIR = "TelegramFiles"
DB_FILE = "file_bot.db"

# ========== SETUP ==========
Path(FILES_DIR).mkdir(exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store temporary data for file renaming
user_rename_context = {}


# ========== GLASS-STYLE BUTTONS ==========
def create_glass_button(text, callback_data, emoji=""):
    """Create glass-style button"""
    return InlineKeyboardButton(f"{emoji} {text}", callback_data=callback_data)


def create_main_keyboard(user_id, is_admin=False, is_approved=False):
    """Create main glass-style keyboard"""
    keyboard = []

    if is_approved or is_admin:
        keyboard.append([
            create_glass_button("Browse Files", "browse_files", "📁"),
            create_glass_button("Search", "search_info", "🔍")
        ])

        keyboard.append([
            create_glass_button("My Stats", "my_stats", "📊"),
            create_glass_button("My ID", "my_id", "🆔")
        ])

        if is_admin:
            keyboard.append([
                create_glass_button("Admin Panel", "admin_panel", "👑")
            ])
    else:
        keyboard.append([
            create_glass_button("Get My ID", "my_id", "🆔"),
            create_glass_button("Help", "show_help", "❓")
        ])

    return InlineKeyboardMarkup(keyboard)


def create_admin_keyboard():
    """Create admin glass-style keyboard"""
    keyboard = [
        [
            create_glass_button("Upload File", "upload_info", "➕"),
            create_glass_button("Manage Users", "manage_users", "👥")
        ],
        [
            create_glass_button("Pending Users", "pending_users", "⏳"),
            create_glass_button("Delete File", "delete_info", "🗑️")
        ],
        [
            create_glass_button("All Files", "admin_files", "📋"),
            create_glass_button("Statistics", "admin_stats", "📊")
        ],
        [
            create_glass_button("Back to Main", "main_menu", "🏠")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_back_keyboard(back_to="main_menu"):
    """Create simple back button keyboard"""
    return InlineKeyboardMarkup([[
        create_glass_button("Back", back_to, "🔙")
    ]])


def create_rename_keyboard():
    """Create beautiful rename keyboard"""
    keyboard = [
        [
            create_glass_button("✨ Rename File", "rename_file", "✏️"),
            create_glass_button("✅ Keep Original", "keep_original", "📝")
        ],
        [
            create_glass_button("🔙 Cancel Upload", "cancel_upload", "❌")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# ========== DATABASE FUNCTIONS ==========
def init_database():
    """Initialize database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            is_allowed INTEGER DEFAULT 0,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            file_id TEXT PRIMARY KEY,
            display_name TEXT,
            original_name TEXT,
            filepath TEXT,
            file_size INTEGER,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uploaded_by INTEGER
        )
    ''')

    conn.commit()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, is_allowed) VALUES (?, ?, ?, 1)',
                   (ADMIN_ID, "Admin", "Admin"))
    conn.commit()
    conn.close()
    print("✅ Database initialized")


def is_admin(user_id):
    """Check if user is admin"""
    return user_id == ADMIN_ID


def is_user_approved(user_id):
    """Check if user is approved to use the bot"""
    if user_id == ADMIN_ID:
        return True

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT is_allowed FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result is None:
        return False
    return result[0] == 1


def add_or_update_user(user_id, username, first_name, is_allowed=None):
    """Add or update user in database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT is_allowed FROM users WHERE user_id = ?', (user_id,))
    existing = cursor.fetchone()

    if existing:
        if is_allowed is not None:
            cursor.execute('UPDATE users SET username = ?, first_name = ?, is_allowed = ? WHERE user_id = ?',
                           (username, first_name, is_allowed, user_id))
        else:
            cursor.execute('UPDATE users SET username = ?, first_name = ? WHERE user_id = ?',
                           (username, first_name, user_id))
    else:
        if is_allowed is None:
            is_allowed = 0
        cursor.execute('INSERT INTO users (user_id, username, first_name, is_allowed) VALUES (?, ?, ?, ?)',
                       (user_id, username, first_name, is_allowed))
    conn.commit()
    conn.close()


def approve_user_in_db(user_id):
    """Approve a user in database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_allowed = 1 WHERE user_id = ?', (user_id,))
    updated = cursor.rowcount
    conn.commit()
    conn.close()
    return updated > 0


def get_pending_users():
    """Get all pending users"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, first_name, join_date FROM users WHERE is_allowed = 0 ORDER BY join_date')
    users = cursor.fetchall()
    conn.close()
    return users


def get_all_users():
    """Get all users"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, first_name, is_allowed, join_date FROM users ORDER BY join_date DESC')
    users = cursor.fetchall()
    conn.close()
    return users


def generate_file_id():
    """Generate simple file ID"""
    letters = string.ascii_lowercase + string.digits
    return f"file_{''.join(random.choices(letters, k=6))}"


def save_file(file_id, display_name, original_name, filepath, file_size, uploaded_by):
    """Save file to database with display name"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO files (file_id, display_name, original_name, filepath, file_size, uploaded_by) VALUES (?, ?, ?, ?, ?, ?)',
        (file_id, display_name, original_name, filepath, file_size, uploaded_by))
    conn.commit()
    conn.close()


def get_all_files():
    """Get all files"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT file_id, display_name, original_name, file_size FROM files ORDER BY upload_date DESC')
    files = cursor.fetchall()
    conn.close()
    return files


def get_file(file_id):
    """Get file by ID"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM files WHERE file_id = ?', (file_id,))
    file = cursor.fetchone()
    conn.close()
    return file


def delete_file_from_db(file_id):
    """Delete file from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM files WHERE file_id = ?', (file_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted > 0


def update_file_display_name(file_id, display_name):
    """Update display name of a file"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE files SET display_name = ? WHERE file_id = ?', (display_name, file_id))
    conn.commit()
    conn.close()


# ========== COMMAND HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user = update.effective_user
    add_or_update_user(user.id, user.username, user.first_name)
    user_is_admin = is_admin(user.id)
    user_is_approved = is_user_approved(user.id)

    if user_is_admin:
        message = "👑 *Welcome Admin!*\n\n"
        message += "You have full access to all features.\n"
        message += "Use the beautiful buttons below to navigate ✨"
    elif user_is_approved:
        message = f"✨ *Welcome {user.first_name}!*\n\n"
        message += "You can browse and download files.\n"
        message += "Use the glass buttons below to navigate 📱"
    else:
        message = f"👋 *Hello {user.first_name}!*\n\n"
        message += "🌟 *You need approval to use this bot.*\n\n"
        message += f"*Your User ID:* `{user.id}`\n\n"
        message += "Send this ID to the admin for approval.\n"
        message += "Once approved, use /start again 💫"

    await update.message.reply_text(
        message,
        reply_markup=create_main_keyboard(user.id, user_is_admin, user_is_approved),
        parse_mode="Markdown"
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data
    user_is_admin = is_admin(user.id)
    user_is_approved = is_user_approved(user.id)

    # Handle main menu
    if data == "main_menu":
        if user_is_admin:
            await query.edit_message_text(
                "👑 *Admin Mode*\n\n✨ Select an option:",
                reply_markup=create_main_keyboard(user.id, True, True),
                parse_mode="Markdown"
            )
        elif user_is_approved:
            await query.edit_message_text(
                f"✨ *Welcome {user.first_name}!*\n\n🌟 Select an option:",
                reply_markup=create_main_keyboard(user.id, False, True),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                f"⏳ *Approval Needed*\n\nYour ID: `{user.id}`\n\n💫 Send this to admin.",
                reply_markup=create_main_keyboard(user.id, False, False),
                parse_mode="Markdown"
            )

    # Handle browse files
    elif data == "browse_files":
        if not user_is_approved and not user_is_admin:
            await query.answer("❌ You need approval first!", show_alert=True)
            return

        files = get_all_files()
        if not files:
            await query.edit_message_text(
                "📭 *No Files Yet*\n\n💫 Admin hasn't uploaded any files yet.",
                reply_markup=create_back_keyboard("main_menu"),
                parse_mode="Markdown"
            )
            return

        message = "📁 *Available Files*\n\n"
        for idx, (file_id, display_name, original_name, file_size) in enumerate(files[:10], 1):
            size_mb = file_size / (1024 * 1024) if file_size else 0
            if len(display_name) > 25:
                display = display_name[:22] + "..."
            else:
                display = display_name

            message += f"{idx}. *{file_id}*\n"
            message += f"   📄 {display}\n"
            message += f"   📦 {size_mb:.1f}MB\n"
            message += f"   ⬇️ `/get {file_id}`\n\n"

        if len(files) > 10:
            message += f"✨ Showing 10 of {len(files)} files\n\n"
        message += "💡 *Tip:* Tap `/get file_id` to copy the command!"

        await query.edit_message_text(
            message,
            reply_markup=create_back_keyboard("main_menu"),
            parse_mode="Markdown"
        )

    # Handle rename options
    elif data == "rename_file":
        user_id = user.id
        if user_id in user_rename_context:
            file_data = user_rename_context[user_id]
            await query.edit_message_text(
                "✏️ *Rename File*\n\n"
                "✨ Please send me the new name for this file.\n\n"
                f"📄 Current name: `{file_data['original_name']}`\n\n"
                "*Examples:*\n"
                "• `Vacation Photo.jpg`\n"
                "• `Meeting Notes.pdf`\n"
                "• `Music Album.mp3`\n\n"
                "💫 *Type the new name and send it...*",
                parse_mode="Markdown"
            )

    elif data == "keep_original":
        user_id = user.id
        if user_id in user_rename_context:
            file_data = user_rename_context[user_id]
            file_id = generate_file_id()
            display_name = file_data['original_name']
            filepath = os.path.join(FILES_DIR, display_name)

            # Save the file
            await file_data['file_obj'].download_to_drive(filepath)
            file_size = os.path.getsize(filepath)
            save_file(file_id, display_name, file_data['original_name'], filepath, file_size, user.id)

            size_mb = file_size / (1024 * 1024)

            # Clear the context
            del user_rename_context[user_id]

            await query.edit_message_text(
                f"✅ *File Uploaded Successfully!*\n\n"
                f"📄 Name: {display_name}\n"
                f"🆔 ID: `{file_id}`\n"
                f"📦 Size: {size_mb:.1f} MB\n\n"
                f"💫 Download with: `/get {file_id}`\n\n"
                f"✨ *Original name kept as requested*",
                reply_markup=create_back_keyboard("admin_panel"),
                parse_mode="Markdown"
            )

    elif data == "cancel_upload":
        user_id = user.id
        if user_id in user_rename_context:
            del user_rename_context[user_id]
        await query.edit_message_text(
            "❌ *Upload Cancelled*\n\n"
            "💫 File upload has been cancelled.\n"
            "You can try again anytime!",
            reply_markup=create_back_keyboard("admin_panel"),
            parse_mode="Markdown"
        )

    # Handle search info
    elif data == "search_info":
        await query.edit_message_text(
            "🔍 *Search Files*\n\n"
            "✨ To search for files, use the command:\n"
            "`/search keyword`\n\n"
            "*Examples:*\n"
            "`/search music` 🎵\n"
            "`/search photo` 📸\n"
            "`/search document` 📄",
            reply_markup=create_back_keyboard("main_menu"),
            parse_mode="Markdown"
        )

    # Handle my stats
    elif data == "my_stats":
        files = get_all_files()
        user_files = [f for f in files if f[0].startswith(f"user_{user.id}_")]

        message = f"📊 *Your Statistics*\n\n"
        message += f"👤 Name: {user.first_name}\n"
        message += f"🆔 ID: `{user.id}`\n"
        message += f"📅 Joined: Today\n"
        message += f"📁 Files Downloaded: {len(user_files)}\n"
        message += f"✅ Status: {'Approved' if user_is_approved or user_is_admin else 'Pending'}"

        await query.edit_message_text(
            message,
            reply_markup=create_back_keyboard("main_menu"),
            parse_mode="Markdown"
        )

    # Handle my ID
    elif data == "my_id":
        await query.edit_message_text(
            f"🆔 *Your User ID*\n\n"
            f"`{user.id}`\n\n"
            f"✨ Send this to admin for approval.",
            reply_markup=create_back_keyboard("main_menu"),
            parse_mode="Markdown"
        )

    # Handle admin panel
    elif data == "admin_panel":
        if not user_is_admin:
            await query.answer("❌ Admin only!", show_alert=True)
            return

        await query.edit_message_text(
            "👑 *Admin Panel*\n\n✨ Select an option:",
            reply_markup=create_admin_keyboard(),
            parse_mode="Markdown"
        )

    # Handle upload info
    elif data == "upload_info":
        if not user_is_admin:
            await query.answer("❌ Admin only!", show_alert=True)
            return

        await query.edit_message_text(
            "➕ *Upload File*\n\n"
            "✨ *How to upload:*\n"
            "1. Send any file to this bot 📁\n"
            "2. Reply to it with `/add` ✨\n"
            "3. Choose to rename or keep original ✏️\n"
            "4. File gets ID like `file_abc123` 🆔\n\n"
            "💫 Users can download with:\n"
            "`/get file_abc123`",
            reply_markup=create_back_keyboard("admin_panel"),
            parse_mode="Markdown"
        )

    # Handle manage users
    elif data == "manage_users":
        if not user_is_admin:
            await query.answer("❌ Admin only!", show_alert=True)
            return

        users = get_all_users()
        if not users:
            message = "📭 *No Users Yet*"
        else:
            message = "👥 *All Users*\n\n"
            for user_id, username, first_name, is_allowed, join_date in users:
                status = "✅" if is_allowed else "❌"
                message += f"{status} *{first_name or 'User'}*\n"
                message += f"   🆔 ID: `{user_id}`\n"
                message += f"   📊 Status: {'Approved' if is_allowed else 'Pending'}\n"
                message += f"   ✨ Approve: `/approve {user_id}`\n\n"

        await query.edit_message_text(
            message,
            reply_markup=create_back_keyboard("admin_panel"),
            parse_mode="Markdown"
        )

    # Handle pending users
    elif data == "pending_users":
        if not user_is_admin:
            await query.answer("❌ Admin only!", show_alert=True)
            return

        pending = get_pending_users()
        if not pending:
            await query.edit_message_text(
                "✅ *All users are approved!* ✨",
                reply_markup=create_back_keyboard("admin_panel"),
                parse_mode="Markdown"
            )
            return

        message = "⏳ *Pending Users*\n\n"
        for user_id, username, first_name, join_date in pending:
            message += f"👤 *{first_name or 'User'}*\n"
            message += f"   🆔 ID: `{user_id}`\n"
            message += f"   📱 Username: @{username or 'none'}\n"
            message += f"   📅 Joined: {join_date[:10] if join_date else 'Today'}\n"
            message += f"   ✨ Approve: `/approve {user_id}`\n\n"

        await query.edit_message_text(
            message,
            reply_markup=create_back_keyboard("admin_panel"),
            parse_mode="Markdown"
        )

    # Handle delete info
    elif data == "delete_info":
        if not user_is_admin:
            await query.answer("❌ Admin only!", show_alert=True)
            return

        await query.edit_message_text(
            "🗑️ *Delete File*\n\n"
            "✨ To delete a file, use:\n"
            "`/delete file_id`\n\n"
            "*Example:*\n"
            "`/delete file_abc123`\n\n"
            "⚠️ *Warning:* This cannot be undone!",
            reply_markup=create_back_keyboard("admin_panel"),
            parse_mode="Markdown"
        )

    # Handle admin files
    elif data == "admin_files":
        if not user_is_admin:
            await query.answer("❌ Admin only!", show_alert=True)
            return

        files = get_all_files()
        if not files:
            await query.edit_message_text(
                "📭 *No Files Yet*",
                reply_markup=create_back_keyboard("admin_panel"),
                parse_mode="Markdown"
            )
            return

        message = "📋 *All Files*\n\n"
        for file_id, display_name, original_name, file_size in files[:15]:
            size_mb = file_size / (1024 * 1024) if file_size else 0
            message += f"• `{file_id}`\n"
            message += f"  📄 {display_name[:25]}{'...' if len(display_name) > 25 else ''}\n"
            message += f"  📦 {size_mb:.1f}MB\n"
            message += f"  🗑️ Delete: `/delete {file_id}`\n\n"

        if len(files) > 15:
            message += f"✨ ... and {len(files) - 15} more files\n"

        await query.edit_message_text(
            message,
            reply_markup=create_back_keyboard("admin_panel"),
            parse_mode="Markdown"
        )

    # Handle admin stats
    elif data == "admin_stats":
        if not user_is_admin:
            await query.answer("❌ Admin only!", show_alert=True)
            return

        files = get_all_files()
        users = get_all_users()
        total_size = sum(f[3] for f in files if f[3])
        approved_users = sum(1 for u in users if u[3] == 1)
        pending_users = sum(1 for u in users if u[3] == 0)

        message = "📊 *Bot Statistics*\n\n"
        message += f"📁 Total Files: {len(files)}\n"
        message += f"💾 Total Size: {total_size / (1024 * 1024):.1f} MB\n"
        message += f"👥 Total Users: {len(users)}\n"
        message += f"✅ Approved Users: {approved_users}\n"
        message += f"⏳ Pending Users: {pending_users}\n"
        message += f"👑 Admin: Fyodor ✨"

        await query.edit_message_text(
            message,
            reply_markup=create_back_keyboard("admin_panel"),
            parse_mode="Markdown"
        )

    # Handle help
    elif data == "show_help":
        if user_is_admin:
            help_text = "❓ *Admin Help*\n\n"
            help_text += "✨ *Commands:*\n"
            help_text += "• `/add` - Upload file (reply to file)\n"
            help_text += "• `/approve ID` - Approve user\n"
            help_text += "• `/delete ID` - Delete file\n"
            help_text += "• `/search` - Search files\n"
            help_text += "• `/get ID` - Download file\n\n"
            help_text += "💫 *Use beautiful buttons for easy navigation!*"
        else:
            help_text = "❓ *Help Center*\n\n"
            help_text += "1. Get your ID from 'My ID' button 🆔\n"
            help_text += "2. Send it to admin for approval ✨\n"
            help_text += "3. Once approved, you can:\n"
            help_text += "   • Browse files 📁\n"
            help_text += "   • Download files ⬇️\n"
            help_text += "   • Search files 🔍\n\n"
            help_text += "✨ *Commands after approval:*\n"
            help_text += "• `/get file_id` - Download\n"
            help_text += "• `/search keyword` - Search"

        await query.edit_message_text(
            help_text,
            reply_markup=create_back_keyboard("main_menu"),
            parse_mode="Markdown"
        )


# ========== MESSAGE HANDLER FOR RENAMING ==========
async def handle_rename_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle rename file name input"""
    user = update.effective_user

    if user.id not in user_rename_context:
        return

    new_name = update.message.text.strip()

    if not new_name or len(new_name) > 100:
        await update.message.reply_text(
            "❌ *Invalid Name*\n\n"
            "✨ Please provide a valid name (1-100 characters).\n"
            "Try again with a shorter name.",
            parse_mode="Markdown"
        )
        return

    file_data = user_rename_context[user.id]

    # Add extension if missing
    original_ext = os.path.splitext(file_data['original_name'])[1]
    if not new_name.lower().endswith(original_ext.lower()):
        new_name = new_name + original_ext

    file_id = generate_file_id()
    filepath = os.path.join(FILES_DIR, new_name)

    try:
        # Save the file
        await file_data['file_obj'].download_to_drive(filepath)
        file_size = os.path.getsize(filepath)

        # Save to database with custom display name
        save_file(file_id, new_name, file_data['original_name'], filepath, file_size, user.id)

        size_mb = file_size / (1024 * 1024)

        # Clear the context
        del user_rename_context[user.id]

        await update.message.reply_text(
            f"✅ *File Uploaded Successfully!*\n\n"
            f"📄 Name: {new_name}\n"
            f"🆔 ID: `{file_id}`\n"
            f"📦 Size: {size_mb:.1f} MB\n\n"
            f"💫 Download with: `/get {file_id}`\n\n"
            f"✨ *File renamed as requested*",
            parse_mode="Markdown"
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ *Error saving file:*\n`{str(e)[:100]}`",
            parse_mode="Markdown"
        )
        if user.id in user_rename_context:
            del user_rename_context[user.id]


# ========== TEXT COMMANDS ==========
async def get_file_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download file command"""
    user = update.effective_user

    if not is_user_approved(user.id) and not is_admin(user.id):
        await update.message.reply_text(
            "❌ *You need approval to download files.*\n\n"
            f"Your ID: `{user.id}`\n"
            "✨ Send this to admin for approval.",
            parse_mode="Markdown"
        )
        return

    if not context.args:
        await update.message.reply_text(
            "📥 *Usage:* `/get file_id`\n\n"
            "*Example:* `/get file_abc123`\n\n"
            "💫 Use /start and click 'Browse Files' to see available files.",
            parse_mode="Markdown"
        )
        return

    file_id = context.args[0]
    file_data = get_file(file_id)

    if not file_data:
        await update.message.reply_text(
            f"❌ *File not found:* `{file_id}`\n\n"
            "✨ Check the file ID and try again.",
            parse_mode="Markdown"
        )
        return

    filepath = file_data[3]
    display_name = file_data[1]

    if not os.path.exists(filepath):
        await update.message.reply_text(
            f"❌ *File missing on server:* `{display_name}`\n"
            "💫 Admin needs to re-upload this file.",
            parse_mode="Markdown"
        )
        return

    try:
        await update.message.reply_text(f"⏬ Downloading `{display_name}`... ✨")

        with open(filepath, 'rb') as file:
            ext = os.path.splitext(filepath)[1].lower()

            if ext in ['.jpg', '.jpeg', '.png', '.gif']:
                await update.message.reply_photo(photo=file, caption=f"📸 {display_name}")
            elif ext in ['.mp3', '.m4a', '.wav', '.flac']:
                await update.message.reply_audio(audio=file, title=display_name, caption=f"🎵 {display_name}")
            elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
                await update.message.reply_video(video=file, caption=f"🎬 {display_name}")
            else:
                await update.message.reply_document(document=file, filename=display_name)

    except Exception as e:
        await update.message.reply_text(f"❌ *Error:* `{str(e)[:100]}`")


async def add_file_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Upload file command with rename option"""
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("❌ Admin only command.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ *Reply to a file with `/add`*\n\n"
            "✨ *How to upload:*\n"
            "1. Send any file to bot 📁\n"
            "2. Reply to it with `/add`\n"
            "3. Choose rename option ✏️",
            parse_mode="Markdown"
        )
        return

    msg = update.message.reply_to_message

    # Get file
    file_obj = None
    original_name = ""

    if msg.document:
        file_obj = msg.document
        original_name = msg.document.file_name or "file.bin"
    elif msg.photo:
        file_obj = msg.photo[-1]
        original_name = f"photo_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    elif msg.video:
        file_obj = msg.video
        original_name = msg.video.file_name or "video.mp4"
    elif msg.audio:
        file_obj = msg.audio
        original_name = f"{msg.audio.performer or 'Unknown'} - {msg.audio.title or 'Unknown'}.mp3"
    elif msg.voice:
        file_obj = msg.voice
        original_name = "voice.ogg"
    else:
        await update.message.reply_text("❌ Unsupported file type.")
        return

    # Store file data for renaming
    user_rename_context[user.id] = {
        'file_obj': await file_obj.get_file(),
        'original_name': original_name,
        'message_id': update.message.message_id
    }

    # Show rename options
    await update.message.reply_text(
        f"📁 *File Received!*\n\n"
        f"📄 Original name: `{original_name}`\n\n"
        f"✨ *What would you like to do?*\n\n"
        f"1. **Rename File** ✏️ - Choose a new display name\n"
        f"2. **Keep Original** 📝 - Use the original filename\n"
        f"3. **Cancel** ❌ - Cancel the upload",
        reply_markup=create_rename_keyboard(),
        parse_mode="Markdown"
    )


async def approve_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve user command"""
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("❌ Admin only command.")
        return

    if not context.args:
        await update.message.reply_text(
            "✅ *Usage:* `/approve user_id`\n\n"
            "*Example:* `/approve 123456789`",
            parse_mode="Markdown"
        )
        return

    try:
        user_id = int(context.args[0])
        success = approve_user_in_db(user_id)

        if success:
            await update.message.reply_text(
                f"✅ *User approved!* ✨\n\n"
                f"User ID: `{user_id}`\n"
                f"They can now use the bot.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"⚠️ *User not found*\n\n"
                f"ID: `{user_id}`\n"
                f"They need to use /start first.",
                parse_mode="Markdown"
            )

    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Must be a number.")


async def delete_file_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete file command"""
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("❌ Admin only command.")
        return

    if not context.args:
        await update.message.reply_text(
            "🗑️ *Usage:* `/delete file_id`\n\n"
            "*Example:* `/delete file_abc123`",
            parse_mode="Markdown"
        )
        return

    file_id = context.args[0]
    file_data = get_file(file_id)

    if not file_data:
        await update.message.reply_text(f"❌ File `{file_id}` not found.")
        return

    filepath = file_data[3]
    display_name = file_data[1]

    try:
        if os.path.exists(filepath):
            os.remove(filepath)

        success = delete_file_from_db(file_id)

        if success:
            await update.message.reply_text(
                f"🗑️ *File deleted!* ✨\n\n"
                f"Name: {display_name}\n"
                f"ID: `{file_id}`",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"❌ Failed to delete file.")

    except Exception as e:
        await update.message.reply_text(f"❌ *Error:* `{str(e)}`")


async def search_files_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search files command"""
    user = update.effective_user

    if not is_user_approved(user.id) and not is_admin(user.id):
        await update.message.reply_text(
            "❌ *You need approval to search files.*\n\n"
            f"Your ID: `{user.id}`",
            parse_mode="Markdown"
        )
        return

    if not context.args:
        await update.message.reply_text(
            "🔍 *Usage:* `/search keyword`\n\n"
            "*Examples:*\n"
            "`/search music` 🎵\n"
            "`/search photo` 📸\n"
            "`/search document` 📄",
            parse_mode="Markdown"
        )
        return

    query = " ".join(context.args).lower()
    files = get_all_files()

    results = []
    for file_id, display_name, original_name, file_size in files:
        if query in display_name.lower() or query in original_name.lower():
            results.append((file_id, display_name, file_size))

    if not results:
        await update.message.reply_text(
            f"🔍 *No results for:* `{query}`",
            parse_mode="Markdown"
        )
        return

    message = f"🔍 *Results for '{query}':* ✨\n\n"
    for file_id, display_name, file_size in results[:10]:
        size_mb = file_size / (1024 * 1024) if file_size else 0
        display = display_name[:22] + "..." if len(display_name) > 25 else display_name
        message += f"• `{file_id}`\n"
        message += f"  📄 {display}\n"
        message += f"  📦 {size_mb:.1f}MB\n"
        message += f"  ⬇️ `/get {file_id}`\n\n"

    if len(results) > 10:
        message += f"✨ ... and {len(results) - 10} more results\n"

    await update.message.reply_text(message, parse_mode="Markdown")


# ========== MAIN ==========
def main():
    """Start the bot"""
    # Initialize database
    init_database()

    print("=" * 60)
    print("🤖 TELEGRAM FILE BOT WITH GLASS BUTTONS")
    print(f"📁 Folder: {os.path.abspath(FILES_DIR)}")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print("=" * 60)
    print("✅ Feature: File Renaming during upload")
    print("✅ Feature: Beautiful glass-style UI")
    print("✅ Feature: User approval system")
    print("=" * 60)

    # Create bot
    app = Application.builder().token(BOT_TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("get", get_file_cmd))
    app.add_handler(CommandHandler("add", add_file_cmd))
    app.add_handler(CommandHandler("approve", approve_user_cmd))
    app.add_handler(CommandHandler("delete", delete_file_cmd))
    app.add_handler(CommandHandler("search", search_files_cmd))

    # Add callback handler for buttons
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Add message handler for rename input
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rename_message))

    print("🔄 Starting bot...")
    print("📱 Send /start to your bot")
    print("powered by fyodor")
    print("=" * 60)

    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == '__main__':

    main()
