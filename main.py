import os
import asyncio
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN or TELEGRAM_TOKEN environment variable not set!")

# Translation APIs
TRANSLATION_APIS = [
    {"url": "https://libretranslate.com/translate", "name": "LibreTranslate"},
    {"url": "https://translate.argosopentech.com/translate", "name": "Argos Translate"}
]

# Supported languages (40+ languages)
LANGUAGES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "ru": "Russian", "ja": "Japanese",
    "ko": "Korean", "zh": "Chinese", "ar": "Arabic", "hi": "Hindi",
    "nl": "Dutch", "pl": "Polish", "tr": "Turkish", "vi": "Vietnamese",
    "th": "Thai", "id": "Indonesian", "ms": "Malay", "sw": "Swahili",
    "ha": "Hausa", "yo": "Yoruba", "ig": "Igbo", "zu": "Zulu",
    "af": "Afrikaans", "el": "Greek", "he": "Hebrew", "hu": "Hungarian",
    "ro": "Romanian", "sk": "Slovak", "sv": "Swedish", "uk": "Ukrainian",
    "da": "Danish", "fi": "Finnish", "no": "Norwegian", "fa": "Persian",
    "ur": "Urdu", "bn": "Bengali", "ta": "Tamil", "te": "Telugu", "ml": "Malayalam"
}

user_sessions = {}

# ==================== KEYBOARDS ====================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🌍 Translate", callback_data="translate")],
        [InlineKeyboardButton("🔁 Swap Languages", callback_data="swap")],
        [InlineKeyboardButton("📋 Language List", callback_data="languages")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_language_keyboard(action: str, selected: str = None):
    keyboard = []
    row = []
    for code, name in sorted(LANGUAGES.items(), key=lambda x: x[1]):
        display = f"✅ {name}" if code == selected else name
        row.append(InlineKeyboardButton(display, callback_data=f"{action}_{code}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([
        InlineKeyboardButton("🔄 Auto-Detect", callback_data="auto_detect"),
        InlineKeyboardButton("🔙 Back", callback_data="back")
    ])
    return InlineKeyboardMarkup(keyboard)

# ==================== COMMAND HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    user_sessions[user_id] = {"source": "auto", "target": "en"}
    
    welcome = (
        f"🌍 Welcome {user.first_name} to **SpeakEasyBot**!\n\n"
        "🔗 Your friendly translation companion!\n\n"
        "**✨ Features:**\n"
        "• 🌍 Translate between 40+ languages\n"
        "• 🔁 Swap languages instantly\n"
        "• 🔄 Auto-detect source language\n"
        "• 📋 40+ languages supported\n\n"
        "**📖 How to use:**\n"
        "1. Click 'Translate'\n"
        "2. Choose source language (or auto-detect)\n"
        "3. Choose target language\n"
        "4. Send any text!\n\n"
        "⬇️ Click 'Translate' to get started!"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 **SpeakEasyBot - Help Guide**\n\n"
        "**🌍 How to Translate:**\n"
        "1. Click 'Translate' button\n"
        "2. Select source language (or auto-detect)\n"
        "3. Select target language\n"
        "4. Send any text\n\n"
        "**🔧 Commands:**\n"
        "• `/start` - Start the bot\n"
        "• `/help` - Show this help\n"
        "• `/languages` - List all languages\n"
        "• `/swap` - Swap languages\n\n"
        "**💡 Tips:**\n"
        "• Use auto-detect for unknown languages\n"
        "• Supports 40+ languages\n"
        "• Max 5000 characters per translation\n\n"
        "**Example:**\n"
        "1. Set source: English\n"
        "2. Set target: Spanish\n"
        "3. Send: 'Hello world'\n"
        "4. Get: '¡Hola mundo!'"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def languages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_list = "🌍 **Supported Languages**\n\n"
    for code, name in sorted(LANGUAGES.items(), key=lambda x: x[1]):
        lang_list += f"• {name} (`{code}`)\n"
    await update.message.reply_text(lang_list, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def swap_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in user_sessions:
        temp = user_sessions[user_id].get("source", "auto")
        user_sessions[user_id]["source"] = user_sessions[user_id].get("target", "en")
        user_sessions[user_id]["target"] = temp
        
        source = "Auto-detect" if user_sessions[user_id]["source"] == "auto" else LANGUAGES.get(user_sessions[user_id]["source"], "Unknown")
        target = LANGUAGES.get(user_sessions[user_id]["target"], "English")
        
        await update.message.reply_text(
            f"🔄 **Languages Swapped!**\n\n"
            f"🔹 From: {source}\n"
            f"🔹 To: {target}\n\n"
            "Send me text to translate! 🌍",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text("Please start the bot with /start first.", reply_markup=get_main_keyboard())

# ==================== CALLBACK HANDLERS ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {"source": "auto", "target": "en"}
    
    if data == "translate":
        await query.edit_message_text(
            "🌍 **Select Source Language:**\n\n"
            "Choose the language of your text, or use auto-detect:",
            parse_mode="Markdown",
            reply_markup=get_language_keyboard("source", user_sessions[user_id].get("source", "auto"))
        )
    
    elif data == "swap":
        temp = user_sessions[user_id].get("source", "auto")
        user_sessions[user_id]["source"] = user_sessions[user_id].get("target", "en")
        user_sessions[user_id]["target"] = temp
        
        source = "Auto-detect" if user_sessions[user_id]["source"] == "auto" else LANGUAGES.get(user_sessions[user_id]["source"], "Unknown")
        target = LANGUAGES.get(user_sessions[user_id]["target"], "English")
        
        await query.edit_message_text(
            f"🔄 **Languages Swapped!**\n\n"
            f"🔹 From: {source}\n"
            f"🔹 To: {target}\n\n"
            "Send me text to translate! 🌍",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
    elif data == "auto_detect":
        user_sessions[user_id]["source"] = "auto"
        await query.edit_message_text(
            "🔁 **Auto-Detect Enabled!**\n\n"
            "Now choose your target language:",
            parse_mode="Markdown",
            reply_markup=get_language_keyboard("target", user_sessions[user_id].get("target", "en"))
        )
    
    elif data.startswith("source_"):
        lang_code = data.replace("source_", "")
        user_sessions[user_id]["source"] = lang_code
        await query.edit_message_text(
            f"✅ **Source Language Set:** {LANGUAGES.get(lang_code, 'Unknown')}\n\n"
            "Now choose your target language:",
            parse_mode="Markdown",
            reply_markup=get_language_keyboard("target", user_sessions[user_id].get("target", "en"))
        )
    
    elif data.startswith("target_"):
        lang_code = data.replace("target_", "")
        user_sessions[user_id]["target"] = lang_code
        
        source = "Auto-detect" if user_sessions[user_id]["source"] == "auto" else LANGUAGES.get(user_sessions[user_id]["source"], "Unknown")
        target = LANGUAGES.get(lang_code, "English")
        
        await query.edit_message_text(
            f"✅ **Ready to Translate!**\n\n"
            f"🔹 From: {source}\n"
            f"🔹 To: {target}\n\n"
            "📝 Send me any text and I'll translate it instantly!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
    elif data == "languages":
        lang_list = "🌍 **Supported Languages**\n\n"
        for code, name in sorted(LANGUAGES.items(), key=lambda x: x[1]):
            lang_list += f"• {name} (`{code}`)\n"
        await query.edit_message_text(lang_list, parse_mode="Markdown", reply_markup=get_main_keyboard())
    
    elif data == "help":
        help_text = (
            "📖 **SpeakEasyBot - Help Guide**\n\n"
            "**🌍 How to Translate:**\n"
            "1. Click 'Translate' button\n"
            "2. Select source language (or auto-detect)\n"
            "3. Select target language\n"
            "4. Send any text\n\n"
            "**🔧 Commands:**\n"
            "• `/start` - Start the bot\n"
            "• `/help` - Show this help\n"
            "• `/languages` - List all languages\n"
            "• `/swap` - Swap languages\n\n"
            "**💡 Tips:**\n"
            "• Use auto-detect for unknown languages\n"
            "• Supports 40+ languages\n"
            "• Max 5000 characters per translation"
        )
        await query.edit_message_text(help_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
    
    elif data == "back":
        await query.edit_message_text(
            "🏠 **Main Menu**\n\n"
            "What would you like to do?",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

# ==================== TRANSLATION FUNCTIONS ====================
async def translate_with_api(api_url: str, text: str, source: str, target: str):
    try:
        payload = {
            "q": text,
            "source": source,
            "target": target,
            "format": "text"
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("translatedText")
                return None
    except asyncio.TimeoutError:
        return None
    except Exception as e:
        print(f"API error ({api_url}): {e}")
        return None

async def translate_text(text: str, source: str = "auto", target: str = "en"):
    if not text or len(text.strip()) < 1:
        return None
    if len(text) > 5000:
        return None
    
    # Try LibreTranslate first
    result = await translate_with_api("https://libretranslate.com/translate", text, source, target)
    if result:
        return result
    
    # Try Argos Translate
    result = await translate_with_api("https://translate.argosopentech.com/translate", text, source, target)
    if result:
        return result
    
    # Fallback to MyMemory API
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {
            "q": text,
            "langpair": f"{source}|{target}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("responseStatus") == 200:
                        return data.get("responseData", {}).get("translatedText")
    except Exception as e:
        print(f"Fallback error: {e}")
    
    return None

async def detect_language(text: str):
    try:
        url = "https://libretranslate.com/detect"
        payload = {"q": text}
        headers = {"Content-Type": "application/json"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        return data[0].get("language")
        return None
    except Exception as e:
        print(f"Detection error: {e}")
        return None

# ==================== MESSAGE HANDLER ====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {"source": "auto", "target": "en"}
    
    source = user_sessions[user_id].get("source", "auto")
    target = user_sessions[user_id].get("target", "en")
    
    source_display = "Auto-detect" if source == "auto" else LANGUAGES.get(source, "Unknown")
    target_display = LANGUAGES.get(target, "English")
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        f"🔄 **Translating...**\n\n"
        f"🔹 From: {source_display}\n"
        f"🔹 To: {target_display}\n\n"
        f"⏳ Please wait...",
        parse_mode="Markdown"
    )
    
    translated = await translate_text(text, source, target)
    
    if translated:
        await processing_msg.delete()
        
        # Detect language if auto was used
        if source == "auto":
            detected = await detect_language(text)
            if detected and detected in LANGUAGES:
                source_display = LANGUAGES.get(detected, "Unknown")
        
        await update.message.reply_text(
            f"✅ **Translation Complete**\n\n"
            f"📝 **Original ({source_display}):**\n"
            f"_{text[:300]}{'...' if len(text) > 300 else ''}_\n\n"
            f"🌍 **Translated ({target_display}):**\n"
            f"_{translated[:300]}{'...' if len(translated) > 300 else ''}_\n\n"
            f"📊 Length: {len(text)} → {len(translated)} characters",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    else:
        await processing_msg.edit_text(
            "❌ **Translation Failed**\n\n"
            "I couldn't translate this text. Please try:\n"
            "• Using a different language combination\n"
            "• Sending shorter text (max 5000 chars)\n"
            "• Checking if the language is supported\n\n"
            "Try swapping languages or using auto-detect.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

# ==================== MAIN FUNCTION ====================
def main():
    print("🚀 Starting SpeakEasyBot...")
    print(f"🌍 Supported languages: {len(LANGUAGES)}")
    print(f"🔗 Translation APIs: {len(TRANSLATION_APIS)}")
    print("✅ Bot is ready!")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("languages", languages_command))
    application.add_handler(CommandHandler("swap", swap_command))
    
    # Add callback handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("✅ Bot is running! Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
