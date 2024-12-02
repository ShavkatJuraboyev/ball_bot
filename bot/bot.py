import os
import sys
import django
import logging
import yt_dlp
from aiogram import Bot, Dispatcher, types
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, CallbackQuery, FSInputFile, ContentType
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import F
from asgiref.sync import sync_to_async
from django.conf import settings

# Django sozlamalarini yuklash
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from kiber_security.models import Users, Ball, Link, UserChannels

# Logger sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot va Dispatcher obyektlarini yaratish
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

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

# Holatlar uchun FSM
class VideoDownloadStates(StatesGroup):
    waiting_for_video_link = State()

async def check_user_in_channels(user_id: int, channels: list) -> bool:
    """
    Foydalanuvchini berilgan kanallarda bor yoki yo'qligini tekshirish.
    
    :param user_id: Telegram foydalanuvchi ID.
    :param channels: Kanal linklarining ro'yxati.
    :return: Agar barcha kanallarda bor bo'lsa True, aks holda False.
    """
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    channel_usernames = [link.split("/")[-1] for link in channels]  # Kanal username'larini olish

    for channel_username in channel_usernames:
        try:
            # Kanal haqida ma'lumot olish
            chat = await bot.get_chat(f"@{channel_username}")
            # Foydalanuvchini kanalda bor yoki yo'qligini tekshirish
            member = await bot.get_chat_member(chat_id=chat.id, user_id=user_id)
            
            if member.status not in ['member', 'administrator', 'creator']:
                # Agar foydalanuvchi kanalda bo'lmasa
                return False
        except TelegramBadRequest as e:
            logger.error(f"TelegramBadRequest: Kanal {channel_username} uchun xato: {e}")
            return False  # Kanalga ulanishda xato bo'lsa ham, False qaytariladi

    # Agar foydalanuvchi barcha kanallarda bo'lsa
    return True


async def award_points_if_joined_all(user):
    """
    Foydalanuvchini barcha kerakli kanallarda borligini tekshiradi va ball beradi.
    Agar foydalanuvchi yangi kanalga qo'shilgan bo'lsa, ball qo'shadi.

    :param user: Foydalanuvchi obyekti.
    """
    # Telegram kanallari ro'yxatini olish
    channels = await get_telegram_links()
    logger.info(f"Foydalanuvchi {user.telegram_id} uchun barcha kerakli kanallarni tekshirish.")

    # Foydalanuvchini barcha kanallarda borligini tekshirish
    is_member = await check_user_in_channels(user.telegram_id, channels)

    if is_member:
        for channel_username in channels:
            # Kanalda yangi foydalanuvchini ro'yxatdan o'tkazish
            user_channel, created = await sync_to_async(UserChannels.objects.get_or_create)(
                user=user, channel_username=channel_username
            )

            if created:
                logger.info(f"Foydalanuvchi {user.telegram_id} {channel_username} kanalga qo'shildi. Ball berilmoqda.")
                
                # Foydalanuvchining ballarini yangilash
                user_ball, _ = await get_or_create_ball(user)
                user_ball.telegram_ball += 200 # Ball qo'shish
                user_ball.all_ball = (
                    user_ball.youtube_ball +
                    user_ball.telegram_ball +
                    user_ball.instagram_ball +
                    user_ball.friends_ball
                )
                await sync_to_async(user_ball.save)()
            else:
                logger.info(f"Foydalanuvchi {user.telegram_id} {channel_username} kanalga avvaldan qo'shilgan.")
    else:
        logger.info(f"Foydalanuvchi {user.telegram_id} barcha kerakli kanallarda mavjud emas.")


# /start komandasini ishlovchi funksiya
@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    user_data = {
        'telegram_id': message.from_user.id,
        'first_name': message.from_user.first_name or ' ',
        'last_name': message.from_user.last_name or ' ',
        'username_link': message.from_user.username or ' ',
    }

    # Taklif kodini olish (start komandasidan keyingi parametr)
    args = message.text.split()
    referral_code = args[1] if len(args) > 1 else None

    # Foydalanuvchini yaratish yoki topish
    user, created = await get_or_create_user(user_data)

    # Foydalanuvchi hali botga birinchi marta kirgan bo'lsa va taklif kodi berilgan bo'lsa
    if created and referral_code and not user.referred_by:
        referrer = await sync_to_async(Users.objects.filter(referral_code=referral_code).first)()
        if referrer:
            user.referred_by = referrer
            user.is_first_start = False
            await sync_to_async(user.save)()

            referrer_ball, _ = await get_or_create_ball(referrer)
            referrer_ball.friends_ball += 1000
            referrer_ball.all_ball = (
                referrer_ball.youtube_ball + referrer_ball.telegram_ball +
                referrer_ball.instagram_ball + referrer_ball.friends_ball
            )
            await sync_to_async(referrer_ball.save)()
            # Taklif qilgan foydalanuvchiga 1000 ball qo'shilgani haqida xabar yuborish
            await dp.bot.send_message(chat_id=referrer.telegram_id, text="Siz yangi do'stingizni taklif qildingiz va 1000 ball qo'shildi!")

    await award_points_if_joined_all(user)
    # Telefon raqami mavjudligini tekshirish
    if user.phone_number:
        # Telefon raqami avval yuborilgan bo'lsa, inline tugmalarni ko'rsatish
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Video yuklash 🔽", callback_data="video_download")],
                [InlineKeyboardButton(text="Ilovaga o'tish 🌐", web_app=WebAppInfo(url="https://1cb8-195-158-8-30.ngrok-free.app"))]
            ]
        )
        await message.answer("Quyidagi tugmalardan birini tanlang:", reply_markup=keyboard)
    else:
        # Telefon raqami hali yuborilmagan bo'lsa, so'rash
        contact_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📞Telefon raqamni ulashish", request_contact=True)]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer("Samarqand viloyat Ichki ishlar boshqarmasi Kiberxavfsizlik bo'limi, Kiberjinoyatchilika qarshi birga kurashamiz! \n🤳Iltimos, telefon raqamingizni yuboring:", reply_markup=contact_keyboard)

@dp.message(F.contact)
async def handle_contact(message: types.Message, state: FSMContext):
    telegram_id = message.contact.user_id
    user = await get_user_by_telegram_id(telegram_id)

    if user:
        user.phone_number = message.contact.phone_number
        await sync_to_async(user.save)()
        await message.answer("Telefon raqamingiz saqlandi.")

    # Web app tugmasini yuborish
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Video yuklash 🔽", callback_data="video_download")],
            [InlineKeyboardButton(text="Ilovaga o'tish 🌐", web_app=WebAppInfo(url="https://1cb8-195-158-8-30.ngrok-free.app"))]
        ]
    )
    await message.answer("Quyidagi tugmalardan birini tanlang:", reply_markup=keyboard)


# Video yuklash tugmasi uchun handler
@dp.callback_query(lambda callback_query: callback_query.data.startswith("video_download"))
async def video_download_handler(callback: CallbackQuery):
    await callback.message.edit_text("Videoning platformasini tanlang:")
    platform_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ YouTube", callback_data="platform_youtube")],
            [InlineKeyboardButton(text="✅ Instagram", callback_data="platform_instagram")],
            [InlineKeyboardButton(text="✅ Facebook", callback_data="platform_facebook")],
            [InlineKeyboardButton(text="🔙 Ortga", callback_data="go_back")]
        ]
    )
    await callback.message.edit_reply_markup(reply_markup=platform_keyboard)

# Ortga qaytish tugmasi uchun handler
@dp.callback_query(lambda callback_query: callback_query.data == "go_back")
async def go_back_handler(callback: CallbackQuery):
    # Ortga tugmasi bosilganda foydalanuvchiga Web app tugmalari bilan qaytish
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Video yuklash 🔽", callback_data="video_download")],
            [InlineKeyboardButton(text="Ilovaga o'tish 🌐", web_app=WebAppInfo(url="https://1cb8-195-158-8-30.ngrok-free.app"))]
        ]
    )
    await callback.message.edit_text("Quyidagi tugmalardan birini tanlang:", reply_markup=keyboard)


# Platforma tanlash handler
@dp.callback_query(lambda callback_query: callback_query.data.startswith("platform_"))
async def platform_selected_handler(callback: CallbackQuery, state: FSMContext):  # `state` qo'shildi
    platform = callback.data.split("_")[1].capitalize()
    await callback.answer(f"{platform} tanlandi. Endi videoning linkini yuboring.")
    await callback.message.edit_text(f"Endi {platform} uchun videoning linkini yuboring:")

    # FSM holatini o‘rnatish
    await state.set_state(VideoDownloadStates.waiting_for_video_link)


# Linkni qayta ishlash uchun handler (faqat oddiy foydalanuvchilar uchun)
@dp.message(F.text.startswith("http"))
async def process_link(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == VideoDownloadStates.waiting_for_video_link.state:
        url = message.text
        platform = None

        # Platformani aniqlash
        if "youtube.com" in url or "youtu.be" in url:
            platform = "YouTube"
        elif "instagram.com" in url:
            platform = "Instagram"
        elif "facebook.com" in url:
            platform = "Facebook"

        if not platform:
            await message.answer("Noto'g'ri platforma yoki link. Iltimos, qayta tekshirib yuboring.")
            return

        await message.answer(f"Video yuklanmoqda... ({platform})")
        try:
            if platform == "YouTube":
                await download_youtube_video(message, url)
            else:
                await download_instagram_facebook_video(message, url)
        except Exception as e:
            await message.answer(f"Xato yuz berdi: {e}")

        # Holatni tozalash
        await state.clear()
    else:
        await message.answer("Iltimos, avval platformani tanlang va linkni yuboring.")


# YouTube uchun yuklash funksiyasi
async def download_youtube_video(message: types.Message, url: str):
    import yt_dlp

    ydl_opts = {
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'format': 'best',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)

    video = FSInputFile(file_path)
    await message.bot.send_video(message.chat.id, video)
    await message.answer("Video muvaffaqiyatli yuklandi!")


# Instagram va Facebook uchun yuklash funksiyasi
async def download_instagram_facebook_video(message: types.Message, url: str):
    ydl_opts = {
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'format': 'best',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)

    video = FSInputFile(file_path)  # Faylni FSInputFile ga o'girish
    await bot.send_video(message.chat.id, video)
    await message.answer("Video muvaffaqiyatli yuklandi!")


ADMIN_ID = 1421622919  # Admin ID

# Media turidagi xabarlarni yuborish
async def send_advertisement(bot: Bot, message: str, media=None):
    users = await sync_to_async(list)(Users.objects.all())  # Foydalanuvchilarni olish
    for user in users:
        try:
            if media:
                if media['type'] == 'photo':
                    await bot.send_photo(user.telegram_id, media['file_id'], caption=message)
                elif media['type'] == 'video':
                    await bot.send_video(user.telegram_id, media['file_id'], caption=message)
            else:
                await bot.send_message(user.telegram_id, message)
        except Exception as e:
            logger.error(f"Foydalanuvchi {user.telegram_id} uchun reklama yuborishda xatolik: {e}")

# Adminning /broadcast buyrug'i uchun handler
@dp.message(Command("broadcast"))
async def start_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await state.set_state("broadcast")  # Holatni "broadcast"ga o'rnatish
        await message.answer("Iltimos, reklama matni yoki media fayl yuboring.")
    else:
        await message.answer("Sizda ushbu amalni bajarish uchun ruxsat yo'q.")

@dp.message(StateFilter("broadcast"), F.content_type.in_([ContentType.TEXT, ContentType.PHOTO, ContentType.VIDEO]))
async def handle_broadcast_media(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return

    # Matn yoki media turiga qarab xabar yuborish
    if message.text:
        await send_advertisement(bot, message.text)
        await message.answer("Reklama barcha foydalanuvchilarga yuborildi.")
    elif message.photo:
        media = {'type': 'photo', 'file_id': message.photo[-1].file_id}
        await send_advertisement(bot, message.caption or "Reklama", media)
        await message.answer("Rasmli reklama barcha foydalanuvchilarga yuborildi.")
    elif message.video:
        media = {'type': 'video', 'file_id': message.video.file_id}
        await send_advertisement(bot, message.caption or "Reklama", media)
        await message.answer("Videoli reklama barcha foydalanuvchilarga yuborildi.")
    else:
        await message.answer("Noto'g'ri format. Faqat matn, rasm yoki video yuboring.")

    await state.clear()

# Asosiy bot funksiyasini ishga tushirish
async def main():
    # Dispatcherni ishga tushirish
    print("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())