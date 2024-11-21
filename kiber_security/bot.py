import os
import sys
import django
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo, Bot
from telegram.ext import Application, CallbackContext, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from telegram.error import BadRequest
from django.conf import settings
from asgiref.sync import sync_to_async
import logging

logger = logging.getLogger(__name__)

# Django sozlamalarini yuklash
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Modelni import qilish
from kiber_security.models import Users, Ball, Link, UserChannels

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

@sync_to_async
def get_telegram_links():
    return list(Link.objects.filter(link_type='telegram').values_list('url', flat=True))



async def check_user_in_channels(user_id, channels):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    channels = [link.split("/")[-1] for link in channels]

    for channel_username in channels:
        try:
            chat = await bot.get_chat(f"@{channel_username}")
            member = await bot.get_chat_member(chat_id=chat.id, user_id=user_id)
            if member.status in ['member', 'administrator', 'creator']:
                continue  # Agar foydalanuvchi kanalda bo'lsa, keyingi kanalga o'tish
            else:
                return False  # Foydalanuvchi kanalda yo'q
        except BadRequest as e:
            logger.error(f"BadRequest error for channel {channel_username}: {e}")
            return False
    return True


async def award_points_if_joined_all(user):
    # Telegram kanallari ro'yxatini olish
    channels = await get_telegram_links()
    logger.info(f"Checking if user {user.telegram_id} is in all required channels.")

    # Foydalanuvchi barcha kanallarda borligini tekshirish
    if await check_user_in_channels(user.telegram_id, channels):
        for channel_username in channels:
            # Foydalanuvchi kanalda bormi yoki yo'qligini tekshirish
            user_channel, created = await sync_to_async(UserChannels.objects.get_or_create)(user=user, channel_username=channel_username)

            # Agar foydalanuvchi kanalda yangi bo'lsa
            if created:
                logger.info(f"User {user.telegram_id} joined {channel_username}. Awarding points.")
                
                # Ballarni yangilash
                user_ball, _ = await get_or_create_ball(user)
                user_ball.telegram_ball += 200  # Ball qo'shish
                user_ball.all_ball = (
                    user_ball.youtube_ball
                    + user_ball.telegram_ball
                    + user_ball.instagram_ball
                    + user_ball.friends_ball
                )
                await sync_to_async(user_ball.save)()  # Ballni saqlash
            else:
                logger.info(f"User {user.telegram_id} already joined {channel_username}. No points awarded.")
    else:
        logger.info(f"User {user.telegram_id} is not in all required channels.")

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
            user.is_first_start = False
            await sync_to_async(user.save)()

            # Taklif qilgan foydalanuvchining ballini yangilash
            referrer_ball, _ = await get_or_create_ball(referrer)
            referrer_ball.friends_ball += 1000
            referrer_ball.all_ball = (
                referrer_ball.youtube_ball + referrer_ball.telegram_ball + 
                referrer_ball.instagram_ball + referrer_ball.friends_ball
            )
            await sync_to_async(referrer_ball.save)()

            # Referrerni xabardor qilish
            await context.bot.send_message(chat_id=referrer.telegram_id, text="Siz yangi do'stingizni taklif qildingiz va 1000 ball qo'shildi!")

    # Foydalanuvchini kanalda borligini tekshirib, 200 ball berish
    await award_points_if_joined_all(user)

    # Telefon raqami mavjud emasligini tekshiriladi
    if not user.phone_number:
        contact_button = KeyboardButton("Telefon raqamni yuborish", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Samarqand viloyat Ichki ishlar boshqarmasi Kiberxavfsizlik bo'limi, Kiberjinoyatchilika qarshi birga kurashamiz! \nIltimos, telefon raqamingizni yuboring:", reply_markup=reply_markup)
    else:
        # Web app tugmasini yuborish
        keyboard = [
            [InlineKeyboardButton("O'rganishni boshlash", web_app=WebAppInfo(url="https://4225-188-113-251-193.ngrok-free.app"))]
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
        [InlineKeyboardButton("O'rganishni boshlash", web_app=WebAppInfo(url="https://4225-188-113-251-193.ngrok-free.app"))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Kiber xavfsizlikni o'rganing:", reply_markup=reply_markup)

# Foydalanuvchilarni yuborish funksiyasi
async def send_advertisement(bot: Bot, message: str, media=None):
    users = await sync_to_async(list)(Users.objects.all())  # Foydalanuvchilarni olish
    for user in users:
        try:
            if media:
                if media['type'] == 'photo':
                    await bot.send_photo(chat_id=user.telegram_id, photo=media['file'], caption=message)
                elif media['type'] == 'video':
                    await bot.send_video(chat_id=user.telegram_id, video=media['file'], caption=message)
                elif media['type'] == 'gif':
                    await bot.send_animation(chat_id=user.telegram_id, animation=media['file'], caption=message)
            else:
                await bot.send_message(chat_id=user.telegram_id, text=message)
        except Exception as e:
            logger.warning(f"Xabar yuborib bo'lmadi: {user.telegram_id}, sabab: {e}")


# Adminni reklama yuborish uchun kutish
ASK_MEDIA, WAIT_FOR_MEDIA = range(2)

ADMIN_ID = 1421622919  # Admin ID
# Adminni reklama yuborish uchun kutish bosqichi
async def start_broadcast(update: Update, context: CallbackContext):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("Iltimos, reklama matni yoki fayl yuboring.")
        return ASK_MEDIA
    else:
        await update.message.reply_text("Sizda ushbu amalni bajarish uchun ruxsat yo'q.")
        return ConversationHandler.END

# Admin matn yoki fayl yuborganda
async def handle_broadcast_media(update: Update, context: CallbackContext):
    admin_id = 1421622919  # Admin Telegram ID
    if update.message.from_user.id != admin_id:
        return ConversationHandler.END
    # Agar matn yuborilgan bo'lsa
    if update.message.text:
        message = update.message.text
        await send_advertisement(context.bot, message)  # Matnli xabar yuborish
        await update.message.reply_text("Reklama barcha foydalanuvchilarga yuborildi.")
    
    # Agar rasm yuborilgan bo'lsa
    elif update.message.photo:
        try:
            photo = update.message.photo[-1].file_id
            media = {'type': 'photo', 'file': photo}

            # Admin yuborgan xabar matni sifatida caption (izoh) olinadi
            message = update.message.caption if update.message.caption else "Adminning yuborgan rasmli reklama xabari"
            
            # Rasmlarni foydalanuvchilarga yuborish
            await send_advertisement(context.bot, message, media)
            
            # Adminga tasdiq xabari yuborish
            await update.message.reply_text("Rasmli reklama barcha foydalanuvchilarga yuborildi.")
        except Exception as e:
            logger.error(f"Rasmni yuborishda xatolik: {e}")
            await update.message.reply_text("Rasmni yuborishda muammo yuzaga keldi.")

    
    # Agar video yuborilgan bo'lsa
    elif update.message.video:
        try:
            message = "Adminning yuborgan videoli reklama xabari"
            video = update.message.video.file_id
            media = {'type': 'video', 'file': video}

            # Admin yuborgan xabar matni sifatida caption (izoh) olinadi
            message = update.message.caption if update.message.caption else "Adminning yuborgan rasmli reklama xabari"

            await send_advertisement(context.bot, message, media)  # Video yuborish

            # Adminga tasdiq xabari yuborish
            await update.message.reply_text("Videoli reklama barcha foydalanuvchilarga yuborildi.")
        except Exception as e:
            logger.error(f"Rasmni yuborishda xatolik: {e}")
            await update.message.reply_text("Videoni yuborishda muammo yuzaga keldi.")
    
    # Agar GIF yuborilgan bo'lsa
    elif update.message.animation:
        try:
            message = "Adminning yuborgan GIF reklama xabari"
            gif = update.message.animation.file_id
            media = {'type': 'gif', 'file': gif}

            # Admin yuborgan xabar matni sifatida caption (izoh) olinadi
            message = update.message.caption if update.message.caption else "Adminning yuborgan rasmli reklama xabari"

            await send_advertisement(context.bot, message, media)  # GIF yuborish
            # Adminga tasdiq xabari yuborish
            await update.message.reply_text("GIF reklama barcha foydalanuvchilarga yuborildi.")
        except Exception as e:
            logger.error(f"Rasmni yuborishda xatolik: {e}")
            await update.message.reply_text("Rasmni yuborishda muammo yuzaga keldi.")
    
    # Agar hech narsa yuborilmasa
    else:
        await update.message.reply_text("Iltimos, reklama matni yoki fayl yuboring.")

    return ConversationHandler.END



# Asosiy bot funksiyasini yaratish
def main() -> None:
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('broadcast', start_broadcast)],
        states={
            ASK_MEDIA: [MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO | filters.ANIMATION, handle_broadcast_media)],
            WAIT_FOR_MEDIA: [MessageHandler(filters.TEXT, handle_broadcast_media)],
        },
        fallbacks=[],
    )
    application.add_handler(conversation_handler)
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.run_polling()

if __name__ == '__main__':
    main()
