import os
import subprocess
import re
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ==================== CONFIG ====================
API_TOKEN = "8623604914:AAHcYGcf9a2YNUppB9QGLYJ9FLegcE0JHCA"
ADMIN_ID = 8623604914

# Absolute path setup to fix [Errno 2]
BASE_DIR = os.path.join(os.getcwd(), "hosted_bots")
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# Dictionary to track running processes
running_processes = {}

# ==================== UTILS ====================

def detect_packages(filepath):
    """Scans code for imports and maps to pip packages."""
    packages = set()
    package_mapping = {
        'telegram': 'python-telegram-bot',
        'telebot': 'pyTelegramBotAPI',
        'discord': 'discord.py',
        'requests': 'requests',
        'flask': 'flask',
        'bs4': 'beautifulsoup4',
        'PIL': 'Pillow',
    }
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    found_imports = re.findall(r'^\s*(?:import|from)\s+(\w+)', content, re.MULTILINE)
    for imp in found_imports:
        if imp in package_mapping:
            packages.add(package_mapping[imp])
        elif imp not in sys.builtin_module_names:
            packages.add(imp)
    return list(packages)

# ==================== BOT LOGIC ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        "🤖 **PrimeTGHost v2.1**\n\n"
        "✅ **Status:** Online\n"
        "📁 **Path:** `"+BASE_DIR+"`\n\n"
        "**To host a bot:** Just send me the `.py` file.",
        parse_mode="Markdown"
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    doc = update.message.document
    if not doc.file_name.endswith(".py"):
        await update.message.reply_text("❌ Error: Please send only `.py` files.")
        return

    # SAVE FILE
    file_path = os.path.join(BASE_DIR, doc.file_name)
    file = await context.bot.get_file(doc.file_id)
    await file.download_to_drive(file_path)

    # AUTO-INSTALL DEPS
    await update.message.reply_text(f"🔍 Analyzing `{doc.file_name}`...")
    pkgs = detect_packages(file_path)
    if pkgs:
        await update.message.reply_text(f"📦 Installing: {', '.join(pkgs)}")
        for pkg in pkgs:
            subprocess.run([sys.executable, "-m", "pip", "install", pkg])

    keyboard = [
        [InlineKeyboardButton("🚀 Start Bot", callback_data=f"start_{doc.file_name}")],
        [InlineKeyboardButton("🗑 Delete File", callback_data=f"del_{doc.file_name}")]
    ]
    await update.message.reply_text(f"✅ `{doc.file_name}` uploaded and ready.", 
                                   reply_markup=InlineKeyboardMarkup(keyboard))

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    # Split action and filename correctly
    action, filename = data.split("_", 1)
    file_path = os.path.join(BASE_DIR, filename)
    log_path = f"{file_path}.log"

    if action == "start":
        # Check if already running
        if filename in running_processes and running_processes[filename].poll() is None:
            await query.edit_message_text(f"⚠️ `{filename}` is already running.")
            return

        # Start Process
        log_file = open(log_path, "w")
        proc = subprocess.Popen(
            [sys.executable, file_path],
            stdout=log_file,
            stderr=log_file,
            text=True
        )
        running_processes[filename] = proc
        
        keyboard = [
            [InlineKeyboardButton("🛑 Stop Bot", callback_data=f"stop_{filename}")],
            [InlineKeyboardButton("📄 View Logs", callback_data=f"logs_{filename}")]
        ]
        await query.edit_message_text(f"🚀 `{filename}` is now RUNNING.", 
                                       reply_markup=InlineKeyboardMarkup(keyboard))

    elif action == "stop":
        if filename in running_processes:
            running_processes[filename].terminate()
            del running_processes[filename]
        
        keyboard = [[InlineKeyboardButton("🚀 Restart", callback_data=f"start_{filename}")]]
        await query.edit_message_text(f"🛑 Stopped `{filename}`.", reply_markup=InlineKeyboardMarkup(keyboard))

    elif action == "logs":
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                logs = f.read()[-1000:] # Show last 1000 chars
            await query.message.reply_text(f"📝 **Logs for {filename}:**\n\n`{logs or 'No output yet...'}`", parse_mode="Markdown")
        else:
            await query.message.reply_text("❌ No log file found.")

    elif action == "del":
        if filename in running_processes:
            running_processes[filename].terminate()
            del running_processes[filename]
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(log_path):
            os.remove(log_path)
        await query.edit_message_text(f"🗑 `{filename}` and its logs have been deleted.")

# ==================== MAIN ====================

if __name__ == "__main__":
    print(f"--- PrimeTGHost is Starting (Admin: {ADMIN_ID}) ---")
    app = Application.builder().token(API_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(menu_callback))
    
    app.run_polling(drop_pending_updates=True)
