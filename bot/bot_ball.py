import os
import sys
import django
import logging
import instaloader
from pytube import YouTube
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, 
    ReplyKeyboardMarkup, WebAppInfo, Bot
)
from telegram.ext import (
    Application, CallbackContext, CommandHandler, MessageHandler, filters, 
    ContextTypes, CallbackQueryHandler
)
from telegram.error import BadRequest
from asgiref.sync import sync_to_async
from django.conf import settings

# Logger sozlash
logger = logging.getLogger(__name__)

# Django sozlamalarini yuklash
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Django modellarini import qilish
from kiber_security.models import Users, Ball, Link, UserChannels

# --- Asosiy funksiyalar ---
@sync_to_async
def get_user_by_telegram_id(telegram_id):
    return Users.objects.filter(telegram_id=telegram_id).first()

@sync_to_async
def get_or_create_user(user_data):
    return Users.objects.get_or_create(**user_data)

@sync_to_async
def get_or_create_ball(user):
    return Ball.objects.get_or_create(user=user)

@sync_to_async
def get_telegram_links():
    return list(Link.objects.filter(link_type='telegram').values_list('url', flat=True))

# Foydalanuvchini Telegram kanallariga qo‘shilganligini tekshirish
async def check_user_in_channels(user_id, channels):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    channels = [link.split("/")[-1] for link in channels]

    for channel_username in channels:
        try:
            chat = await bot.get_chat(f"@{channel_username}")
            member = await bot.get_chat_member(chat_id=chat.id, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except BadRequest as e:
            logger.error(f"Channelda xatolik: {channel_username}, xato: {e}")
            return False
    return True

# Foydalanuvchiga ball berish
async def award_points_if_joined_all(user):
    channels = await get_telegram_links()
    if await check_user_in_channels(user.telegram_id, channels):
        for channel_username in channels:
            user_channel, created = await sync_to_async(UserChannels.objects.get_or_create)(
                user=user, channel_username=channel_username
            )
            if created:
                user_ball, _ = await get_or_create_ball(user)
                user_ball.telegram_ball += 200
                user_ball.all_ball = (
                    user_ball.youtube_ball + user_ball.telegram_ball +
                    user_ball.instagram_ball + user_ball.friends_ball
                )
                await sync_to_async(user_ball.save)()
    else:
        logger.info(f"Foydalanuvchi barcha kanallarga qo‘shilmagan: {user.telegram_id}")

# Video yuklash funksiyalari
def download_instagram_video(url):
    loader = instaloader.Instaloader()
    post = instaloader.Post.from_shortcode(loader.context, url.split("/")[-2])
    return post.video_url

def download_youtube_video(url):
    yt = YouTube(url)
    stream = yt.streams.filter(progressive=True, file_extension='mp4').first()
    return stream.url

# --- Telegram bot funksiyalari ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = {
        'telegram_id': update.message.from_user.id,
        'first_name': update.message.from_user.first_name or '',
        'last_name': update.message.from_user.last_name or '',
        'username_link': update.message.from_user.username or '',
    }
    user, _ = await get_or_create_user(user_data)
    await award_points_if_joined_all(user)

    if not user.phone_number:
        contact_button = KeyboardButton("Telefon raqamni yuborish", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "Telefon raqamingizni yuboring:",
            reply_markup=reply_markup
        )
    else:
        keyboard = [
            [InlineKeyboardButton("Video yuklash", callback_data="video_download")],
            [InlineKeyboardButton("O'rganishni boshlash", web_app=WebAppInfo(url="https://library.samtuit.uz"))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Quyidagi tugmalardan birini tanlang:", reply_markup=reply_markup)

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.message.contact.user_id
    user = await get_user_by_telegram_id(telegram_id)
    if user:
        user.phone_number = update.message.contact.phone_number
        await sync_to_async(user.save)()
        await update.message.reply_text("Telefon raqamingiz saqlandi.")

async def video_download_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Video linkni yuboring.")
    context.user_data["waiting_for_video_url"] = True

async def handle_user_message(update: Update, context: CallbackContext):
    if context.user_data.get("waiting_for_video_url"):
        text = update.message.text
        try:
            if "instagram.com" in text:
                video_url = download_instagram_video(text)
                await update.message.reply_text(f"Instagram video link: {video_url}")
            elif "youtube.com" in text or "youtu.be" in text:
                video_url = download_youtube_video(text)
                await update.message.reply_text(f"YouTube video link: {video_url}")
            else:
                await update.message.reply_text("Faqat Instagram yoki YouTube linkini yuboring.")
        except Exception as e:
            await update.message.reply_text(f"Xatolik: {str(e)}")
        context.user_data["waiting_for_video_url"] = False
    else:
        await update.message.reply_text("Avval \"Video yuklash\" tugmasini bosing.")

# --- Bot dasturini ishga tushirish ---
async def main() -> None:
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(video_download_callback, pattern="^video_download$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))

    await application.run_polling()

if __name__ == '__main__':
    # Directly run the bot without manually creating the event loop
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Run the bot using the bot's internal event loop
    application.run_polling()
