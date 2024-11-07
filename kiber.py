from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

# Tokeningizni kiriting
TOKEN = '5131381239:AAHm0l1BmMt4nIpw3mKBfvOrtK_eZ2pooPc'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Ro'yxatlarni ochish", web_app=WebAppInfo(url="https://2cbc-188-113-229-195.ngrok-free.app"))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Dokonlar ro'yxatiga kirish:", reply_markup=reply_markup)

def main() -> None:
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.run_polling()

if __name__ == '__main__':
    main()