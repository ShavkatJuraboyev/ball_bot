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
from kiber_security.models import Users, Ball

# Telegram ID bo'yicha foydalanuvchini olish
@sync_to_async
def get_user_by_telegram_id(telegram_id):
    return Users.objects.filter(telegram_id=telegram_id).first()

# Foydalanuvchini yaratish yoki mavjudini olish
@sync_to_async
def get_or_create_user(user_data):
    return Users.objects.get_or_create(**user_data)

# Ball yaratish yoki mavjudini olish
@sync_to_async
def get_or_create_ball(user):
    return Ball.objects.get_or_create(user=user)

# /start komandasini ishlovchi funksiya
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = {
        'telegram_id': update.message.from_user.id,
        'first_name': update.message.from_user.first_name or ' ',
        'last_name': update.message.from_user.last_name or ' ',
        'username_link': update.message.from_user.username or ' ',
    }

    # Taklif kodini olish (start komandasidan keyingi parametr)
    args = context.args
    referral_code = args[0] if args else None

    # Foydalanuvchini yaratish yoki topish
    user, created = await get_or_create_user(user_data)

    # Foydalanuvchi hali botga birinchi marta kirgan bo'lsa va taklif kodi berilgan bo'lsa
    if user.is_first_start and referral_code and not user.referred_by:
        referrer = await sync_to_async(Users.objects.filter(referral_code=referral_code).first)()
        if referrer:
            # Taklif qilgan foydalanuvchiga ball berish
            user.referred_by = referrer
            user.is_first_start = False  # Foydalanuvchi botga endi birinchi marta kirgan bo'lmaydi
            await sync_to_async(user.save)()

            # Taklif qilgan foydalanuvchining ballini yangilash
            referrer_ball, _ = await get_or_create_ball(referrer)
            referrer_ball.friends_ball += 200
            referrer_ball.all_ball = referrer_ball.youtube_ball + referrer_ball.telegram_ball + referrer_ball.instagram_ball + referrer_ball.friends_ball
            await sync_to_async(referrer_ball.save)()

            # Referrerni xabardor qilish
            await context.bot.send_message(chat_id=referrer.telegram_id, text="Siz yangi do'stingizni taklif qildingiz va 200 ball qo'shildi!")

    # Telefon raqami mavjud emasligini tekshiriladi
    if not user.phone_number:
        contact_button = KeyboardButton("Telefon raqamni yuborish", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Iltimos, telefon raqamingizni yuboring:", reply_markup=reply_markup)
    else:
        # Web app tugmasini yuborish
        keyboard = [
            [InlineKeyboardButton("O'rganishni boshlash", web_app=WebAppInfo(url="https://f2a2-84-54-70-55.ngrok-free.app"))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Kiber xavfsizlikni o'rganing:", reply_markup=reply_markup)

# Telefon raqamini qabul qilish
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.message.contact.user_id
    user = await get_user_by_telegram_id(telegram_id)
    
    if user:
        user.phone_number = update.message.contact.phone_number
        await sync_to_async(user.save)()
        await update.message.reply_text("Telefon raqamingiz saqlandi.")
    
    # Web app tugmasini yuborish
    keyboard = [
        [InlineKeyboardButton("O'rganishni boshlash", web_app=WebAppInfo(url="https://f2a2-84-54-70-55.ngrok-free.app"))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Kiber xavfsizlikni o'rganing:", reply_markup=reply_markup)

# Asosiy bot funksiyasini yaratish
def main() -> None:
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.run_polling()

if __name__ == '__main__':
    main()
