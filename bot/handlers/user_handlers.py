import os
import sys
import django
import logging
import shutil
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import timedelta, datetime
from aiogram import F
from asgiref.sync import sync_to_async
from django.conf import settings
from yt_dlp import YoutubeDL
import instaloader
from handlers.database import get_telegram_links, get_or_create_ball, get_or_create_user, get_user_by_telegram_id, get_bad_words
from utils.membership import check_user_in_channels
from asyncio import sleep
from aiohttp import ClientSession
router = Router()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from kiber_security.models import Users, UserChannels

# Logger sozlash
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class VideoDownloadStates(StatesGroup):
    waiting_for_video_link = State()

async def award_points_if_joined_all(user):
    """
    Foydalanuvchini barcha kerakli kanallarda borligini tekshiradi va ball beradi.
    Agar foydalanuvchi yangi kanalga qo'shilgan bo'lsa, ball qo'shadi.

    :param user: Foydalanuvchi obyekti.
    """
    # Telegram kanallari ro'yxatini olish
    channels = await get_telegram_links()
    logger.info(f"Foydalanuvchi {user.telegram_id} uchun barcha kerakli kanallarni tekshirish.")
    print(channels)
    # Foydalanuvchini barcha kanallarda borligini tekshirish
    is_member = await check_user_in_channels(user.telegram_id, channels)

    if is_member:
        for channel_username, ball in channels:
            # Kanalda yangi foydalanuvchini ro'yxatdan o'tkazish
            user_channel, created = await sync_to_async(UserChannels.objects.get_or_create)(
                user=user, channel_username=channel_username
            )
            if created:
                # Foydalanuvchining ballarini yangilash
                user_ball, _ = await get_or_create_ball(user)
                user_ball.telegram_ball += ball # Ball qo'shish
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

@router.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id  # Foydalanuvchi ID
    await state.update_data(user_id=user_id)
    web_app_url = f"https://9edf-195-158-8-30.ngrok-free.app"
    # if message.chat.type == "private":
    user_data = {
        'telegram_id': user_id,
        'first_name': message.from_user.first_name or ' ',
        'last_name': message.from_user.last_name or ' ',
        'username_link': message.from_user.username or ' '
    }

    # Taklif kodini olish (start komandasidan keyingi parametr)
    args = message.text.split()
    referral_code = args[1] if len(args) > 1 else None

    # Foydalanuvchini yaratish yoki topish
    user, created = await get_or_create_user(user_data)

    # Foydalanuvchining profil rasmlarini olish
    user_photos = await bot.get_user_profile_photos(user_id=user_id)
    if user_photos.total_count > 0:
        # Birinchi rasmning birinchi variantini olish
        file_id = user_photos.photos[0][0].file_id
        file = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}/{file.file_path}"

        # Rasmni yuklab olish va saqlash
        async with ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status == 200:
                    file_name = f"profile_{user_id}.jpg"
                    file_path = os.path.join(settings.MEDIA_ROOT, "users/image/", file_name)

                    with open(file_path, "wb") as f:
                        f.write(await response.read())

                    @sync_to_async
                    def save_profile_image():
                        user.profile_img = f"users/image/{file_name}"
                        user.save()

                    await save_profile_image()

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

    await award_points_if_joined_all(user)
    # Telefon raqami mavjudligini tekshirish
    if user.phone_number:
        # Telefon raqami avval yuborilgan bo'lsa, inline tugmalarni ko'rsatish
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Video yuklash ⏳", callback_data="video_download")],
                [InlineKeyboardButton(text="Ilovaga o'tish 🌐", web_app=WebAppInfo(url=web_app_url))]
            ]
        )
        await message.answer("Endi siz ilova orqali sovg'alar yutub olishingiz mumkin. \nVieo yuklashda siz Youtube va Instagram dan videolarni qiyinchiliksiz yuklash imkoniyati bor:", reply_markup=keyboard)
    else:
        # Telefon raqami hali yuborilmagan bo'lsa, so'rash
        contact_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📞Telefon raqamni ulashish", request_contact=True)]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer("""👋 Assalomu alaykum! Botga xush kelibsiz.\nSamarqand viloyat Ichki ishlar boshqarmasi Kiberxavfsizlik bo'limi, Kiberjinoyatchilika qarshi birga kurashamiz! \n📞Iltimos, telefon raqamingizni yuboring: """, reply_markup=contact_keyboard)


@router.message(lambda msg: msg.contact)
async def handle_contact(message: types.Message, state: FSMContext):
    telegram_id = message.contact.user_id
    user = await get_user_by_telegram_id(telegram_id)
    await state.update_data(user_id=telegram_id)
    web_app_url = f"https://9edf-195-158-8-30.ngrok-free.app?user_id={telegram_id}"
    if user:
        user.phone_number = message.contact.phone_number
        await sync_to_async(user.save)()
        await message.answer("Ajoyib 👍")

    # Web app tugmasini yuborish
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Video yuklash ⏳", callback_data="video_download")],
            [InlineKeyboardButton(text="Ilovaga o'tish 🌐", web_app=WebAppInfo(url=web_app_url))]
        ]
    )
    await message.answer("Endi siz ilova orqali sovg'alar yutub olishingiz mumkin. \nVieo yuklashda siz Youtube va Instagram dan videolarni qiyinchiliksiz yuklash imkoniyati bor", reply_markup=keyboard)


# Video yuklash tugmasi uchun handler
@router.callback_query(lambda c: c.data and c.data.startswith("video_download"))
async def video_download_handler(callback: CallbackQuery):
    
    if callback.message.chat.type == "private":
        await callback.message.edit_text("Videoning platformasini tanlang:")
        platform_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ YouTube", callback_data="platform_youtube")],
                [InlineKeyboardButton(text="✅ Instagram", callback_data="platform_instagram")],
                #[InlineKeyboardButton(text="✅ Facebook", callback_data="platform_facebook")],
                [InlineKeyboardButton(text="🔙 Ortga", callback_data="go_back")]
            ]
        )
        await callback.message.edit_reply_markup(reply_markup=platform_keyboard)


@router.callback_query(lambda callback_query: callback_query.data == "go_back")
async def go_back_handler(callback: CallbackQuery, state: FSMContext):
    chat_id = callback.message.from_user.id
    await state.update_data(user_id=chat_id)
    web_app_url = f"https://9edf-195-158-8-30.ngrok-free.app?user_id={chat_id}"
    # Ortga tugmasi bosilganda foydalanuvchiga Web app tugmalari bilan qaytish
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Video yuklash ⏳", callback_data="video_download")],
            [InlineKeyboardButton(text="Ilovaga o'tish 🌐", web_app=WebAppInfo(url=web_app_url))]
        ]
    )
    await callback.message.edit_text("Quyidagi tugmalardan birini tanlang:", reply_markup=keyboard)


# Asinxron yuklab olish funksiyasi
async def download_youtube_video(url: str, platform: str, message: types.Message):
    ydl_opts = {
        'ffmpeg_location': r'C:\ffmpeg\bin',  # Ensure this is correct path to your FFmpeg bin folder
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'format': 'mp4[height<=720]/best',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }
    try:
        os.makedirs("downloads", exist_ok=True)
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info).replace('.webm', '.mp4').replace('.m4a', '.mp4')

        # Faylni foydalanuvchiga yuborish
        video = FSInputFile(file_path)
        await message.bot.send_video(chat_id=message.chat.id, video=video, caption=f"🎬 {platform}\n✅ Yuklab olindi!")

        # Faylni o'chirish
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Downloads papkasini o'chirish
        if os.path.exists("downloads"):
            shutil.rmtree("downloads")
    
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {e}")
            
async def download_instagram_video(message: types.Message, url: str):
    try:
        # Instaloader sozlash
        loader = instaloader.Instaloader()
        
        # URL'dan post shortcode ni ajratib olish
        shortcode = url.split("/")[4]
        
        # Postni yuklash vaqtinchalik papkaga
        temp_folder = "downloads"
        os.makedirs(temp_folder, exist_ok=True)
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        loader.download_post(post, target=temp_folder)

        # Yuklangan faylni topish va nomini o‘zgartirish
        final_file_path = None
        for file_name in os.listdir(temp_folder):
            if file_name.endswith(".mp4"):  # Faqat video fayllarni izlash
                original_file_path = os.path.join(temp_folder, file_name)
                final_file_path = os.path.join("downloads", f"{shortcode}.mp4")
                shutil.move(original_file_path, final_file_path)
                break

        # Agar fayl yuklanmagan bo‘lsa
        if not final_file_path:
            await message.answer("❌ Video yuklashda xatolik yuz berdi.")
            return

        # Fayl hajmini tekshirish
        file_size = os.path.getsize(final_file_path) / (1024 * 1024)  # MB ga o'tkazish
        if file_size > 2000:
            await message.answer("Video hajmi juda katta (2 GB dan ortiq). Uni Telegram orqali yuborishning iloji yo'q.")
            await message.answer(f"Yuklab olish uchun havola: {url}")
        else:
            # Faylni foydalanuvchiga yuborish
            video = FSInputFile(final_file_path)
            await message.answer_video(video, caption="🎬 Yuklab olindi!")

        # Faylni o‘chirish
        if os.path.exists(final_file_path):
            os.remove(final_file_path)
        shutil.rmtree(temp_folder)  # Vaqtinchalik papkani o‘chirish

    except Exception as e:
        await message.answer(f"❌ Xato yuz berdi: {e}")

@router.callback_query(lambda c: c.data and c.data.startswith("platform_"))
async def platform_selected_handler(callback: CallbackQuery, state: FSMContext):  # `state` qo'shildi
    platform = callback.data.split("_")[1].capitalize()
    await callback.answer(f"🎯 {platform} tanlandi. Endi videoning linkini yuboring.")
    await callback.message.edit_text(f"🎯 Endi {platform} uchun videoning linkini yuboring:")

    # FSM holatini o‘rnatish
    await state.set_state(VideoDownloadStates.waiting_for_video_link)


@router.message(F.text.startswith("http"))
async def process_link(message: types.Message, state: FSMContext):
    if message.chat.type == "private":
        url = message.text
        platform = "Aniqlanmagan"

        # Platformani aniqlash
        if "youtube.com" in url or "youtu.be" in url:
            platform = "YouTube"
        elif "instagram.com" in url:
            platform = "Instagram"
        elif "facebook.com" in url:
            platform = "Facebook"

        await message.answer(f"{platform} videosi yuklanmoqda... 🚀")
        if "youtube.com" in url or "youtu.be" in url:
            platform = "YouTube"
            await download_youtube_video(url, platform, message)
        elif "instagram.com" in url:
            platform = "Instagram"
            await download_instagram_video(message, url)
        elif "facebook.com" in url:
            platform = "Facebook"
            await download_youtube_video(url, platform, message)
        else:
            await message.answer("❌ Faqat YouTube, Instagram yoki Facebook linklarini yuboring.")


@router.callback_query(lambda callback_query: callback_query.data.startswith("check_membership_"))
async def check_membership_handler(callback: CallbackQuery):
    try:
        # Tugmadan foydalanuvchi ID ni ajratib olish
        parts = callback.data.split("_")  # Callback data ni ajratish
        if len(parts) != 3 or not parts[2].isdigit():
            raise ValueError("Invalid callback data format")  # Format noto‘g‘ri bo‘lsa xatolik
        callback_user_id = int(parts[2])  # User ID ni olish
    except Exception as e:
        logger.error(f"Invalid callback data: {callback.data}. Error: {e}")
        await callback.answer("❌ Noto‘g‘ri tugma ma’lumotlari!", show_alert=True)
        return

    user_id = callback.from_user.id
    if callback_user_id != user_id:
        await callback.answer("❌ Bu tugma siz uchun emas!", show_alert=True)
        return

    channels = await get_telegram_links()
    is_member = await check_user_in_channels(user_id, channels)

    if is_member:
        await callback.message.edit_text(
            "✅ Kanallarga muvaffaqiyatli a’zo bo‘ldingiz! Endi guruhda yozishingiz mumkin."
        )
         # 5 soniyadan keyin xabarni o‘chirish
        await sleep(5)
        try:
            await callback.message.delete()
        except Exception as e:
            logger.error(f"Xabarni o‘chirishda xatolik: {e}")
    else:
        await callback.answer(
            "❌ Siz hali barcha kanallarga a’zo bo‘lmagansiz. Iltimos, avval kanallarga qo‘shiling.",
            show_alert=True
        )
        await sleep(5)


@router.message()
async def handle_group_messages(message: types.Message, bot: Bot):

    user_id = message.from_user.id
    channels = await get_telegram_links()

    # Foydalanuvchi kanallarga a'zo ekanligini tekshirish
    is_member = await check_user_in_channels(user_id, channels)
    first_name = message.from_user.first_name

    # Agar admin bo'lsa yoki foydalanuvchi kanal nomidan yozayotgan bo'lsa, bot "kanallarga qo'shiling" deb javob bermasligi kerak
    
    if not is_member and first_name not in ["Channel", "Telegram", "Group"]:
        try:
            await message.delete()

            # Foydalanuvchi uchun tugmalar
            buttons = [
                [InlineKeyboardButton(text=f"📢 {channel.split('/')[-1]}", url=channel)]
                for channel in channels
            ]
            buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data=f"check_membership_{user_id}")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            await message.answer(
                f"👋 Salom {first_name}\n❌ Siz ushbu guruhda yoza olmaysiz.\n👇 Guruhda yozish uchun pastdagi barcha kanallarga a’zo bo‘lishingiz kerak!",
                reply_markup=keyboard
            )
            await sleep(10)
        except Exception as e:
            logger.error(f"Xabarni o'chirishda xatolik: {e}")
        await sleep(10)

    # Nojo'ya so'zlarni tekshirish
    chat_id = message.chat.id
    text = message.text.lower().split()
    BAD_WORDS = await get_bad_words()  # Xabar matnini kichik harfga o‘tkazamiz
    # Nojo'ya so'zlarni tekshirish
    if any(word in text for word in BAD_WORDS):
        try:
            # Xabarni o'chirish
            await message.delete()
            # Foydalanuvchini vaqtincha bloklash
            block_time = datetime.now() + timedelta(minutes=15)  # 1 soatga bloklash
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=types.ChatPermissions(can_send_messages=False),
                until_date=block_time
            )

            # Foydalanuvchiga ogohlantirish
            await message.answer(
                f"❌ Hurmatli {message.from_user.first_name}, siz nomaqbul so‘zlar ishlatdingiz. "
                f"Siz 15 minut davomida guruhda yozishdan mahrum bo‘ldingiz!"
            )
        except Exception as e:
            logger.error(f"Xabarni o'chirish yoki foydalanuvchini bloklashda xatolik: {e}")

def register_user_handlers(dp: Dispatcher, bot: Bot):
    dp.include_router(router)
