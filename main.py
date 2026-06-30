import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from googletrans import Translator
import requests

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token from Railway environment variable
TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Initialize translator
translator = Translator()

# Supported languages dictionary
LANGUAGES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ja': 'Japanese',
    'ko': 'Korean',
    'zh-cn': 'Chinese (Simplified)',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'bn': 'Bengali',
    'ur': 'Urdu',
    'fa': 'Persian',
    'tr': 'Turkish',
    'nl': 'Dutch',
    'pl': 'Polish',
    'vi': 'Vietnamese',
    'th': 'Thai',
}

# Store user preferences (in memory - resets on bot restart)
user_preferences = {}

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued."""
    user = update.effective_user
    welcome_message = (
        f"👋 Hello {user.first_name}!\n\n"
        f"I'm SpeakEasyBot, your language translation assistant.\n\n"
        f"📌 **How to use me:**\n"
        f"• Send me any text and I'll translate it to your preferred language\n"
        f"• Use /translate to translate text to a specific language\n"
        f"• Use /setlang to set your default translation language\n"
        f"• Use /languages to see all supported languages\n"
        f"• Use /help for more commands\n\n"
        f"Your current default language is: {user_preferences.get(user.id, {}).get('target_lang', 'English')}"
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message."""
    help_text = (
        "🆘 **Available Commands:**\n\n"
        "/start - Start the bot and see welcome message\n"
        "/help - Show this help message\n"
        "/translate [text] - Translate text to your default language\n"
        "/setlang [language_code] - Set your default translation language\n"
        "/languages - Show all supported languages\n"
        "/detect - Detect the language of the text you send\n\n"
        "**Usage Examples:**\n"
        "• /setlang es  → Set default language to Spanish\n"
        "• /translate Hello, how are you? → Translates to your default language\n"
        "• Just send any text → Auto-translates to your default language"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def languages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all supported languages."""
    lang_list = "\n".join([f"• `{code}` - {name}" for code, name in LANGUAGES.items()])
    message = f"🌍 **Supported Languages:**\n\n{lang_list}\n\nTo set a language, use:\n`/setlang language_code`\n\nExample: `/setlang es`"
    await update.message.reply_text(message, parse_mode='Markdown')

async def setlang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user's default translation language."""
    user_id = update.effective_user.id
    
    # Check if language code was provided
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a language code.\n\n"
            "Example: `/setlang es`\n"
            "Use /languages to see all available codes.",
            parse_mode='Markdown'
        )
        return
    
    lang_code = context.args[0].lower()
    
    # Validate language code
    if lang_code not in LANGUAGES:
        await update.message.reply_text(
            f"❌ Language code '{lang_code}' not supported.\n"
            "Use /languages to see all available codes."
        )
        return
    
    # Save user preference
    if user_id not in user_preferences:
        user_preferences[user_id] = {}
    user_preferences[user_id]['target_lang'] = lang_code
    
    await update.message.reply_text(
        f"✅ Default language set to: **{LANGUAGES[lang_code]}**",
        parse_mode='Markdown'
    )

async def detect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detect language of provided text."""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide text to detect.\n\n"
            "Example: `/detect Bonjour tout le monde`",
            parse_mode='Markdown'
        )
        return
    
    text = " ".join(context.args)
    try:
        detection = translator.detect(text)
        lang_name = LANGUAGES.get(detection.lang, detection.lang)
        confidence = f"{detection.confidence * 100:.1f}%"
        
        await update.message.reply_text(
            f"🔍 **Language Detection:**\n\n"
            f"• Language: {lang_name}\n"
            f"• Code: `{detection.lang}`\n"
            f"• Confidence: {confidence}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Detection error: {e}")
        await update.message.reply_text("❌ Sorry, I couldn't detect the language. Please try again.")

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Translate text to user's default language or specified language."""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide text to translate.\n\n"
            "Example: `/translate Hello, how are you?`",
            parse_mode='Markdown'
        )
        return
    
    text = " ".join(context.args)
    
    # Get user's default language or fallback to English
    target_lang = user_preferences.get(user_id, {}).get('target_lang', 'en')
    
    try:
        translated = translator.translate(text, dest=target_lang)
        source_lang = LANGUAGES.get(translated.src, translated.src)
        target_lang_name = LANGUAGES.get(target_lang, target_lang)
        
        response = (
            f"🔄 **Translation:**\n\n"
            f"📝 **Original:** {text}\n"
            f"🌍 **From:** {source_lang}\n"
            f"🎯 **To:** {target_lang_name}\n\n"
            f"✨ **Translation:** {translated.text}"
        )
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Translation error: {e}")
        await update.message.reply_text("❌ Sorry, translation failed. Please try again later.")

# --- Message Handler (Auto-Translate) ---

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Automatically translate any text message to user's default language."""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Skip if text is a command (starts with /)
    if text.startswith('/'):
        return
    
    # Get user's default language or fallback to English
    target_lang = user_preferences.get(user_id, {}).get('target_lang', 'en')
    
    # Show typing indicator
    await update.message.chat.send_action(action="typing")
    
    try:
        translated = translator.translate(text, dest=target_lang)
        source_lang = LANGUAGES.get(translated.src, translated.src)
        target_lang_name = LANGUAGES.get(target_lang, target_lang)
        
        # Only translate if source and target are different
        if translated.src != target_lang:
            response = (
                f"🌐 **Translation to {target_lang_name}:**\n\n"
                f"{translated.text}\n\n"
                f"_Detected source: {source_lang}_"
            )
        else:
            response = (
                f"💡 This text appears to be already in **{target_lang_name}**.\n\n"
                f"To translate to another language, use:\n"
                f"`/translate [text]` or change your default language with `/setlang`"
            )
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Auto-translation error: {e}")
        await update.message.reply_text("❌ Sorry, translation failed. Please try again later.")

# --- Main Function ---

def main():
    """Start the bot."""
    if not TOKEN:
        logger.error("No TELEGRAM_TOKEN found in environment variables!")
        return
    
    # Create the Application
    app = Application.builder().token(TOKEN).build()
    
    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("languages", languages_command))
    app.add_handler(CommandHandler("setlang", setlang_command))
    app.add_handler(CommandHandler("detect", detect_command))
    app.add_handler(CommandHandler("translate", translate_command))
    
    # Register message handler for auto-translation
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Log startup
    logger.info("SpeakEasyBot is starting...")
    logger.info(f"Supported languages: {len(LANGUAGES)}")
    
    # Start the bot with long polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
