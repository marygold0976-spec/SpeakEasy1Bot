import os
import io
import re
import asyncio
import aiohttp
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ==================== CONFIGURATION ====================
# Try both possible environment variable names
BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN or TELEGRAM_TOKEN environment variable not set!")

# Multiple translation APIs for reliability
TRANSLATION_APIS = [
    {
        "url": "https://libretranslate.com/translate",
        "name": "LibreTranslate"
    },
    {
        "url": "https://translate.argosopentech.com/translate",
        "name": "Argos Translate"
    }
]

# Supported languages with ISO codes
LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ar": "Arabic",
    "hi": "Hindi",
    "nl": "Dutch",
    "pl": "Polish",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
    "ms": "Malay",
    "sw": "Swahili",
    "ha": "Hausa",
    "yo": "Yoruba",
    "ig": "Igbo",
    "zu": "Zulu",
    "af": "Afrikaans",
    "el": "Greek",
    "he": "Hebrew",
    "hu": "Hungarian",
    "ro": "Romanian",
    "sk": "Slovak",
    "sv": "Swedish",
    "uk": "Ukrainian",
    "da": "Danish",
    "fi": "Finnish",
    "no": "Norwegian",
    "fa": "Persian",
    "ur": "Urdu",
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "ml": "Malayalam"
}

# User sessions
user_sessions = {}

# ==================== KEYBOARD FUNCTIONS ====================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🌍 Translate", callback_data="translate")],
        [InlineKeyboardButton("🔁 Swap Languages", callback_data="swap")],
        [InlineKeyboardButton("📋 Language List", callback_data="languages")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_language_keyboard(action: str, selected: str = None):
    """Generate language selection keyboard with pagination"""
    keyboard = []
    row = []
    count = 0
    
    # Sort languages by name
    sorted_langs = sorted(LANGUAGES.items(), key=lambda x: x[1])
    
    # Group languages in rows of 2
    for code, name in sorted_langs:
        # Show selection indicator
        display = f"✅ {name}" if code == selected else name
        row.append(InlineKeyboardButton(display, callback_data=f"{action}_{code}"))
        count += 1
        
        if count % 2 == 0:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Add navigation buttons
    keyboard.append([
        InlineKeyboardButton("🔄 Auto-Detect", callback_data="auto_detect"),
        InlineKeyboardButton("🔙 Back", callback_data="back")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def get_quick_action_keyboard():
    keyboard = [
        [InlineKeyboardButton("📝 Text", callback_data="quick_text"),
         InlineKeyboardButton("🔊 Voice", callback_data="quick_voice")],
        [InlineKeyboardButton("📄 Document", callback_data="quick_document"),
         InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== COMMAND HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    # Initialize user session
    user_id = str(user.id)
    user_sessions[user_id] = {
        "source": "auto",
        "target": "en",
        "action": None
    }
    
    welcome_message = (
        f"🌍 Welcome {user.first_name} to **SpeakEasyBot**!\n\n"
        "🔗 Your friendly translation companion!\n\n"
        "**✨ Features:**\n"
        "• 🌍 Translate between 40+ languages\n"
        "• 🔁 Swap languages instantly\n"
        "• 🎤 Voice message translation\n"
        "• 📄 Document translation\n"
        "• 🔄 Auto-detect source language\n"
        "• 📋 Quick language selection\n\n"
        "**📖 How to use:**\n"
        "1. Choose your source and target languages\n"
        "2. Send text, voice, or document\n"
        "3. Get translation instantly!\n\n"
        "⬇️ Click 'Translate' to get started!"
    )
    
    await update.message.reply_text(
        welcome_message,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "📖 **SpeakEasyBot User Guide**\n\n"
        "**🌍 Translate**\n"
        "• Click 'Translate'\n"
        "• Choose source language (or auto-detect)\n"
        "• Choose target language\n"
        "• Send text, voice, or document\n\n"
        "**🔄 Quick Commands**\n"
        "• `/swap` - Swap languages\n"
        "• `/languages` - List all languages\n"
        "• `/cancel` - Cancel action\n"
        "• `/help` - Show this help\n\n"
        "**💡 Tips:**\n"
        "• Use auto-detect for unknown languages\n"
        "• Voice messages should be clear\n"
        "• Documents must be plain text (.txt)\n"
        "• Max 5000 characters per translation\n\n"
        "**Support:**\n"
        "For issues, contact bot owner"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def languages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /languages command"""
    lang_list = "🌍 **Supported Languages**\n\n"
    
    # Group languages by first letter for better organization
    current_letter = ""
    for code, name in sorted(LANGUAGES.items(), key=lambda x: x[1]):
        first_letter = name[0].upper()
        if first_letter != current_letter:
            current_letter = first_letter
            lang_list += f"\n**{current_letter}**\n"
        lang_list += f"• {name} (`{code}`)\n"
    
    # Truncate if too long
    if len(lang_list) > 4000:
        lang_list = lang_list[:3900] + "\n\n... and more"
    
    await update.message.reply_text(
        lang_list,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def swap_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /swap command"""
    user_id = str(update.effective_user.id)
    
    if user_id in user_sessions:
        # Swap languages
        temp = user_sessions[user_id].get("source", "auto")
        user_sessions[user_id]["source"] = user_sessions[user_id].get("target", "en")
        user_sessions[user_id]["target"] = temp
        
        source_display = "Auto-detect" if user_sessions[user_id]["source"] == "auto" else LANGUAGES.get(user_sessions[user_id]["source"], "Unknown")
        target_display = LANGUAGES.get(user_sessions[user_id]["target"], "English")
        
        await update.message.reply_text(
            f"🔄 **Languages swapped!**\n\n"
            f"🔹 Source: {source_display}\n"
            f"🔹 Target: {target_display}\n\n"
            "Send me text to translate! 🌍",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "Please start the bot with /start first.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command"""
    user_id = str(update.effective_user.id)
    if user_id in user_sessions:
        user_sessions[user_id]["action"] = None
    
    await update.message.reply_text(
        "✅ **Action cancelled**\n\n"
        "You can start over using the buttons below.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def current_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /current command"""
    user_id = str(update.effective_user.id)
    
    if user_id in user_sessions:
        source_display = "Auto-detect" if user_sessions[user_id]["source"] == "auto" else LANGUAGES.get(user_sessions[user_id]["source"], "Unknown")
        target_display = LANGUAGES.get(user_sessions[user_id]["target"], "English")
        
        await update.message.reply_text(
            f"📊 **Current Language Settings**\n\n"
            f"🔹 Source: {source_display}\n"
            f"🔹 Target: {target_display}\n\n"
            f"Send me text to translate!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "Please start the bot with /start first.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

# ==================== CALLBACK HANDLERS ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "source": "auto",
            "target": "en",
            "action": None
        }
    
    if data == "translate":
        await query.edit_message_text(
            "🌍 **Select source language:**\n\n"
            "Choose the language of your text, or use auto-detect:",
            parse_mode="Markdown",
            reply_markup=get_language_keyboard("source", user_sessions[user_id].get("source", "auto"))
        )
    
    elif data == "swap":
        # Swap languages
        temp = user_sessions[user_id].get("source", "auto")
        user_sessions[user_id]["source"] = user_sessions[user_id].get("target", "en")
        user_sessions[user_id]["target"] = temp
        
        source_display = "Auto-detect" if user_sessions[user_id]["source"] == "auto" else LANGUAGES.get(user_sessions[user_id]["source"], "Unknown")
        target_display = LANGUAGES.get(user_sessions[user_id]["target"], "English")
        
        await query.edit_message_text(
            f"🔄 **Languages swapped!**\n\n"
            f"🔹 Source: {source_display}\n"
            f"🔹 Target: {target_display}\n\n"
            "Send me text to translate! 🌍",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
    elif data == "auto_detect":
        user_sessions[user_id]["source"] = "auto"
        await query.edit_message_text(
            "🔁 **Auto-detect enabled!**\n\n"
            "Now choose the target language:",
            parse_mode="Markdown",
            reply_markup=get_language_keyboard("target", user_sessions[user_id].get("target", "en"))
        )
    
    elif data.startswith("source_"):
        lang_code = data.replace("source_", "")
        user_sessions[user_id]["source"] = lang_code
        
        lang_display = LANGUAGES.get(lang_code, "Unknown")
        await query.edit_message_text(
            f"✅ Source language set to **{lang_display}**\n\n"
            "Now choose the target language:",
            parse_mode="Markdown",
            reply_markup=get_language_keyboard("target", user_sessions[user_id].get("target", "en"))
        )
    
    elif data.startswith("target_"):
        lang_code = data.replace("target_", "")
        user_sessions[user_id]["target"] = lang_code
        
        source_display = "Auto-detect" if user_sessions[user_id]["source"] == "auto" else LANGUAGES.get(user_sessions[user_id]["source"], "Unknown")
        target_display = LANGUAGES.get(lang_code, "English")
        
        await query.edit_message_text(
            f"✅ **Ready to translate!**\n\n"
            f"🔹 From: {source_display}\n"
            f"🔹 To: {target_display}\n\n"
            "📝 **Send me text, voice, or document**\n"
            "or click the buttons below for options:",
            parse_mode="Markdown",
            reply_markup=get_quick_action_keyboard()
        )
        user_sessions[user_id]["action"] = "translate"
    
    elif data == "quick_text":
        await query.edit_message_text(
            "📝 **Send me text to translate**\n\n"
            "I'll translate it for you instantly! 🌍",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        user_sessions[user_id]["action"] = "translate"
    
    elif data == "quick_voice":
        await query.edit_message_text(
            "🎤 **Send me a voice message**\n\n"
            "I'll translate your voice to text! 🌍\n\n"
            "⚠️ Note: Voice translation requires speech-to-text API.\n"
            "For now, please use the voice-to-text feature in Telegram\n"
            "and then send the text for translation.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        user_sessions[user_id]["action"] = "voice"
    
    elif data == "quick_document":
        await query.edit_message_text(
            "📄 **Send me a document**\n\n"
            "I'll translate the content for you! 🌍\n\n"
            "Supported: .txt files only",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        user_sessions[user_id]["action"] = "document"
    
    elif data == "languages":
        lang_list = "🌍 **Supported Languages**\n\n"
        for code, name in sorted(LANGUAGES.items(), key=lambda x: x[1])[:25]:
            lang_list += f"• **{name}** (`{code}`)\n"
        lang_list += f"\n... and {len(LANGUAGES) - 25} more languages\n"
        lang_list += "\nUse /languages to see all languages"
        
        await query.edit_message_text(
            lang_list,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
    elif data == "help":
        await help_command(update, context)
    
    elif data == "back":
        await query.edit_message_text(
            "🏠 **Main Menu**\n\n"
            "What would you like to do?",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        user_sessions[user_id]["action"] = None

# ==================== TRANSLATION FUNCTIONS ====================
async def translate_with_api(api_url: str, text: str, source: str, target: str):
    """Try translation with a specific API"""
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
    """Translate text using multiple API fallbacks"""
    
    # Validation
    if not text or len(text.strip()) < 1:
        return None
    
    if len(text) > 5000:
        return None
    
    # Try each API in order
    for api in TRANSLATION_APIS:
        try:
            result = await translate_with_api(api["url"], text, source, target)
            if result:
                print(f"✅ Translation successful using {api['name']}")
                return result
        except Exception as e:
            print(f"❌ {api['name']} failed: {e}")
            continue
    
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
        print(f"Fallback translation error: {e}")
    
    return None

async def detect_language(text: str):
    """Detect language using LibreTranslate"""
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
        print(f"Language detection error: {e}")
        return None

# ==================== MESSAGE HANDLERS ====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "source": "auto",
            "target": "en",
            "action": None
        }
    
    action = user_sessions[user_id].get("action", "")
    
    if action in ["translate", None]:
        source = user_sessions[user_id].get("source", "auto")
        target = user_sessions[user_id].get("target", "en")
        
        source_display = "Auto-detect" if source == "auto" else LANGUAGES.get(source, "Unknown")
        target_display = LANGUAGES.get(target, "English")
        
        # Validate text length
        if len(text) > 5000:
            await update.message.reply_text(
                "❌ **Text too long**\n\n"
                "Please send shorter text (max 5000 characters).",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            f"🔄 **Translating...**\n\n"
            f"🔹 From: {source_display}\n"
            f"🔹 To: {target_display}\n\n"
            f"⏳ Processing...",
            parse_mode="Markdown"
        )
        
        # Translate
        translated = await translate_text(text, source, target)
        
        if translated:
            await processing_msg.delete()
            
            # Detect language if auto was used
            if source == "auto":
                detected = await detect_language(text)
                if detected and detected in LANGUAGES:
                    source_display = LANGUAGES.get(detected, "Unknown")
            
            # Truncate long translations for display
            display_text = text[:300] + "..." if len(text) > 300 else text
            display_translated = translated[:300] + "..." if len(translated) > 300 else translated
            
            await update.message.reply_text(
                f"✅ **Translation Complete**\n\n"
                f"📝 **Original ({source_display}):**\n"
                f"_{display_text}_\n\n"
                f"🌍 **Translated ({target_display}):**\n"
                f"_{display_translated}_\n\n"
                f"📊 Length: {len(text)} → {len(translated)} characters",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        else:
            await processing_msg.edit_text(
                "❌ **Translation failed**\n\n"
                "I couldn't translate this text. Please try:\n"
                "• Using a different language combination\n"
                "• Sending shorter text\n"
                "• Checking if the language is supported\n\n"
                "Try swapping languages or using auto-detect.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
    
    elif action == "voice":
        await update.message.reply_text(
            "🎤 **Please send a voice message**\n\n"
            "I'm ready to translate!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
    elif action == "document":
        await update.message.reply_text(
            "📄 **Please send a document (.txt)**\n\n"
            "I'm ready to translate!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
    else:
        await update.message.reply_text(
            "👋 **Send me text to translate!**\n\n"
            "Click 'Translate' to set languages first, or just send text\n"
            "and I'll use your current settings.\n\n"
            "Current settings:\n"
            f"🔹 From: {LANGUAGES.get(user_sessions[user_id].get('source', 'auto'), 'Auto-detect')}\n"
            f"🔹 To: {LANGUAGES.get(user_sessions[user_id].get('target', 'en'), 'English')}",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "source": "auto",
            "target": "en",
            "action": None
        }
    
    action = user_sessions[user_id].get("action", "")
    
    if action == "voice":
        source = user_sessions[user_id].get("source", "auto")
        target = user_sessions[user_id].get("target", "en")
        
        source_display = "Auto-detect" if source == "auto" else LANGUAGES.get(source, "Unknown")
        target_display = LANGUAGES.get(target, "English")
        
        await update.message.reply_text(
            f"🎤 **Voice Message Received**\n\n"
            f"🔹 From: {source_display}\n"
            f"🔹 To: {target_display}\n\n"
            "⚠️ **Voice Translation**\n"
            "Voice translation requires speech-to-text API integration.\n\n"
            "**Alternative:**\n"
            "1. Use Telegram's built-in voice-to-text\n"
            "2. Copy the transcribed text\n"
            "3. Send it as text for translation\n\n"
            "I'll translate text instantly! 🌍",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "🎤 **Voice message received!**\n\n"
            "Click 'Translate' and set languages first.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document messages"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "source": "auto",
            "target": "en",
            "action": None
        }
    
    action = user_sessions[user_id].get("action", "")
    document = update.message.document
    
    if action == "document" or action == "translate":
        # Check if it's a text file
        if document.mime_type and document.mime_type.startswith("text/"):
            try:
                file = await document.get_file()
                content = await file.download_as_bytearray()
                text = content.decode('utf-8')
                
                if len(text) > 5000:
                    await update.message.reply_text(
                        "❌ **Document too large**\n\n"
                        "Please send a document with less than 5000 characters.",
                        parse_mode="Markdown",
                        reply_markup=get_main_keyboard()
                    )
                    return
                
                source = user_sessions[user_id].get("source", "auto")
                target = user_sessions[user_id].get("target", "en")
                
                source_display = "Auto-detect" if source == "auto" else LANGUAGES.get(source, "Unknown")
                target_display = LANGUAGES.get(target, "English")
                
                # Send processing message
                processing_msg = await update.message.reply_text(
                    f"🔄 **Translating document...**\n\n"
                    f"🔹 From: {source_display}\n"
                    f"🔹 To: {target_display}\n\n"
                    f"📄 File: {document.file_name}\n"
                    f"📊 Size: {len(text)} characters\n\n"
                    f"⏳ Processing...",
                    parse_mode="Markdown"
                )
                
                # Translate document content
                translated = await translate_text(text, source, target)
                
                if translated:
                    await processing_msg.delete()
                    
                    # Send translated text
                    display_translated = translated[:1000] + "..." if len(translated) > 1000 else translated
                    
                    await update.message.reply_text(
                        f"✅ **Document Translation Complete**\n\n"
                        f"📄 File: {document.file_name}\n"
                        f"🌍 Translated to: {target_display}\n"
                        f"📊 Length: {len(text)} → {len(translated)} characters\n\n"
                        f"{display_translated}",
                        parse_mode="Markdown",
                        reply_markup=get_main_keyboard()
                    )
                else:
                    await processing_msg.edit_text(
                        "❌ **Translation failed**\n\n"
                        "Please try again with a different document.",
                        parse_mode="Markdown",
                        reply_markup=get_main_keyboard()
                    )
            except Exception as e:
                print(f"Document translation error: {e}")
                await update.message.reply_text(
                    "❌ **Error reading document**\n\n"
                    "Please make sure it's a text file (.txt).",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
        else:
            await update.message.reply_text(
                "📄 **Unsupported document type**\n\n"
                "Please send a .txt file for translation.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
    else:
        await update.message.reply_text(
            "📄 **Document received!**\n\n"
            "Click 'Translate' and set languages first.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

# ==================== MAIN FUNCTION ====================
def main():
    """Start the bot"""
    print("🚀 Starting SpeakEasyBot...")
    print(f"🌍 Supported languages: {len(LANGUAGES)}")
    print(f"🔗 Translation APIs: {len(TRANSLATION_APIS)}")
    print("🔗 Ready to translate!")
    
    # Build application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .build()
    )
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("languages", languages_command))
    application.add_handler(CommandHandler("swap", swap_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("current", current_command))
    
    # Add callback handler for buttons
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Start the bot
    print("✅ Bot is running! Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
