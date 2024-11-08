import os
import sys
import django

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from django.conf import settings
from asgiref.sync import sync_to_async

# Django sozlamalarini yuklash
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Modelni import qilish
from kiber_security.models import Users

# Telegram ID bo'yicha foydalanuvchini olish
@sync_to_async
def get_user_by_telegram_id(telegram_id):
    return Users.objects.filter(telegram_id=telegram_id).first()

# /start buyrug'ini qabul qilish va telefon raqamini so'rash
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = {
        'telegram_id': update.message.from_user.id,
        'first_name': update.message.from_user.first_name or ' ',
        'last_name': update.message.from_user.last_name or ' ',
    }
    print(update.message)
    user, created = await sync_to_async(Users.objects.get_or_create)(**user_data)
    
    if created:
        await update.message.reply_text("Assalomu alaykum! Ma'lumotlaringiz saqlandi.")
   
    # Foydalanuvchi allaqachon ro'yxatdan o'tgan, telefon raqami borligini tekshirish
    if not user.phone_number:
         # Telefon raqamini so'rash tugmasini yaratish
        contact_button = KeyboardButton("Telefon raqamni yuborish", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Iltimos, telefon raqamingizni yuboring:", reply_markup=reply_markup)
    else:
        # Telefon raqami mavjud bo'lsa, web app tugmasini yuborish
        keyboard = [
            [InlineKeyboardButton("O'rganishni boshlash", web_app=WebAppInfo(url="https://d421-195-158-8-30.ngrok-free.app"))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Kiber xavfsizlikni o'rganing:", reply_markup=reply_markup)

# Telefon raqamini qabul qilish
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.message.contact.user_id  # Telegram IDni olish
    user = await get_user_by_telegram_id(telegram_id)
    
    if user:
        user.phone_number = update.message.contact.phone_number  # Telefon raqamini olish
        await sync_to_async(user.save)()  # Foydalanuvchini saqlash
        await update.message.reply_text("Telefon raqamingiz saqlandi.")
    
    # Web app uchun kirish tugmasini yuborish
    keyboard = [
        [InlineKeyboardButton("O'rganishni boshlash", web_app=WebAppInfo(url="https://d421-195-158-8-30.ngrok-free.app"))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Kiber xavfsizlikni o'rganing:", reply_markup=reply_markup)

# Asosiy bot funksiyasini yaratish
def main() -> None:
    # Botni ishga tushirish
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.run_polling()

if __name__ == '__main__':
    main()
