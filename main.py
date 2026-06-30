import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from googletrans import Translator

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token from Railway environment variable
TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Initialize translator
translator = Translator()

# Supported languages
LANGUAGES = {
    'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
    'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian', 'ja': 'Japanese',
    'ko': 'Korean', 'zh-cn': 'Chinese (Simplified)', 'ar': 'Arabic',
    'hi': 'Hindi', 'bn': 'Bengali', 'ur': 'Urdu', 'fa': 'Persian',
    'tr': 'Turkish', 'nl': 'Dutch', 'pl': 'Polish', 'vi': 'Vietnamese',
    'th': 'Thai'
}

# Store user preferences
user_preferences = {}

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    default_lang = user_preferences.get(user.id, {}).get('target_lang', 'en')
    default_lang_name = LANGUAGES.get(default_lang, 'English')
    
    welcome = (
        f"👋 Hello {user.first_name}!\n\n"
        f"I'm SpeakEasyBot, your language translation assistant.\n\n"
        f"📌 **Commands:**\n"
        f"• /setlang [code] - Set your default language\n"
        f"• /languages - See all supported languages\n"
        f"• /detect [text] - Detect language of text\n"
        f"• /translate [text] - Translate text\n"
        f"• /help - Show all commands\n\n"
        f"🎯 Your default language: **{default_lang_name}**\n\n"
        f"💡 Just send any text and I'll auto-translate it!"
    )
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🆘 **Available Commands:**\n\n"
        "/start - Welcome message\n"
        "/help - Show this help\n"
        "/setlang [code] - Set default language\n"
        "/languages - Show all languages\n"
        "/detect [text] - Detect language\n"
        "/translate [text] - Translate text\n\n"
        "**Examples:**\n"
        "• `/setlang es` → Set default to Spanish\n"
        "• `/translate Hello` → Translate to your default\n"
        "• Send any text → Auto-translate!"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def languages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_list = "\n".join([f"• `{code}` - {name}" for code, name in LANGUAGES.items()])
    await update.message.reply_text(
        f"🌍 **Supported Languages:**\n\n{lang_list}\n\nUse `/setlang [code]` to change your default.",
        parse_mode='Markdown'
    )

async def setlang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a language code.\n"
            "Example: `/setlang es`\n"
            "Use /languages to see all codes.",
            parse_mode='Markdown'
        )
        return
    
    lang_code = context.args[0].lower()
    
    if lang_code not in LANGUAGES:
        await update.message.reply_text(
            f"❌ '{lang_code}' is not supported.\n"
            "Use /languages to see all codes."
        )
        return
    
    if user_id not in user_preferences:
        user_preferences[user_id] = {}
    user_preferences[user_id]['target_lang'] = lang_code
    
    await update.message.reply_text(
        f"✅ Default language set to: **{LANGUAGES[lang_code]}**",
        parse_mode='Markdown'
    )

async def detect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide text to detect.\n"
            "Example: `/detect Bonjour`",
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
        await update.message.reply_text("❌ Detection failed. Please try again.")

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide text to translate.\n"
            "Example: `/translate Hello world`",
            parse_mode='Markdown'
        )
        return
    
    text = " ".join(context.args)
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
        await update.message.reply_text("❌ Translation failed. Please try again.")

# --- Auto-Translation Handler ---

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if text.startswith('/'):
        return
    
    target_lang = user_preferences.get(user_id, {}).get('target_lang', 'en')
    
    try:
        translated = translator.translate(text, dest=target_lang)
        target_lang_name = LANGUAGES.get(target_lang, target_lang)
        
        if translated.src != target_lang:
            response = f"🌐 **Translation to {target_lang_name}:**\n\n{translated.text}"
        else:
            response = f"💡 This text is already in **{target_lang_name}**.\n\nUse `/translate` for other languages or `/setlang` to change your default."
        
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Auto-translation error: {e}")
        await update.message.reply_text("❌ Translation failed. Please try again.")

# --- Main Function ---

def main():
    if not TOKEN:
        logger.error("❌ TELEGRAM_TOKEN not found in environment variables!")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("languages", languages_command))
    app.add_handler(CommandHandler("setlang", setlang_command))
    app.add_handler(CommandHandler("detect", detect_command))
    app.add_handler(CommandHandler("translate", translate_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("✅ SpeakEasyBot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
