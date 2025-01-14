import os
import sys
import django
import logging
import shutil
import asyncio
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, CallbackQuery, FSInputFile, ContentType
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram import F
from asgiref.sync import sync_to_async
from django.conf import settings
from yt_dlp import YoutubeDL
import instaloader
from asyncio import sleep
from datetime import timedelta, datetime

# Django sozlamalarini yuklash
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from kiber_security.models import Users, Ball, Link, UserChannels, BadWord, GroupId
user_messages = {}
# Logger sozlash
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Bot va Dispatcher obyektlarini yaratish
session = AiohttpSession(timeout=600) 
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, session=session)
dp = Dispatcher(storage=MemoryStorage())
router = Router()


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

@sync_to_async
def get_bad_words():
    return list(BadWord.objects.values_list('word', flat=True))

@sync_to_async
def get_groupid():
    return list(GroupId.objects.values_list('groupid', flat=True))

# Holatlar uchun FSM
class VideoDownloadStates(StatesGroup):
    waiting_for_video_link = State()

class PostStates(StatesGroup):
    waiting_for_post = State()

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
                logger.info(f"Foydalanuvchi {user_id} kanal {channel_username} ga aʼzo emas.")
                # Agar foydalanuvchi kanalda bo'lmasa
                return False
        except TelegramBadRequest as e:
            logger.error(f"TelegramBadRequest: Kanal {channel_username} uchun xato: {e}")
            return False  # Kanalga ulanishda xato bo'lsa ham, False qaytariladi

    # Agar foydalanuvchi barcha kanallarda bo'lsa
    logger.info(f"Foydalanuvchi {user_id} barcha kanallarga aʼzo.")
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
                [InlineKeyboardButton(text="Video yuklash ⏳", callback_data="video_download")],
                [InlineKeyboardButton(text="Ilovaga o'tish 🌐", web_app=WebAppInfo(url="https://4b55-195-158-8-30.ngrok-free.app"))]
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
        await message.answer("""👋 Assalomu alaykum! Botga xush kelibsiz.\nSamarqand viloyat Ichki ishlar boshqarmasi Kiberxavfsizlik bo'limi, Kiberjinoyatchilika qarshi birga kurashamiz! \n📞Iltimos, telefon raqamingizni yuboring: """, reply_markup=contact_keyboard)

@dp.message(F.contact)
async def handle_contact(message: types.Message, state: FSMContext):
    telegram_id = message.contact.user_id
    user = await get_user_by_telegram_id(telegram_id)

    if user:
        user.phone_number = message.contact.phone_number
        await sync_to_async(user.save)()
        await message.answer("Ajoyib 👍.")

    # Web app tugmasini yuborish
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Video yuklash ⏳", callback_data="video_download")],
            [InlineKeyboardButton(text="Ilovaga o'tish 🌐", web_app=WebAppInfo(url="https://4b55-195-158-8-30.ngrok-free.app"))]
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
            #[InlineKeyboardButton(text="✅ Facebook", callback_data="platform_facebook")],
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
            [InlineKeyboardButton(text="Video yuklash ⏳", callback_data="video_download")],
            [InlineKeyboardButton(text="Ilovaga o'tish 🌐", web_app=WebAppInfo(url="https://4b55-195-158-8-30.ngrok-free.app"))]
        ]
    )
    await callback.message.edit_text("Quyidagi tugmalardan birini tanlang:", reply_markup=keyboard)


# Asinxron yuklab olish funksiyasi
async def download_youtube_video(url: str, platform: str, message: types.Message):
    ydl_opts = {
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'format': 'mp4[height<=720]/best',
    }
    try:
        os.makedirs("downloads", exist_ok=True)
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

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

# Platforma tanlash handler
@dp.callback_query(lambda callback_query: callback_query.data.startswith("platform_"))
async def platform_selected_handler(callback: CallbackQuery, state: FSMContext):  # `state` qo'shildi
    platform = callback.data.split("_")[1].capitalize()
    await callback.answer(f"🎯 {platform} tanlandi. Endi videoning linkini yuboring.")
    await callback.message.edit_text(f"🎯 Endi {platform} uchun videoning linkini yuboring:")

    # FSM holatini o‘rnatish
    await state.set_state(VideoDownloadStates.waiting_for_video_link)


@dp.message(F.text.startswith("http"))
async def process_link(message: types.Message, state: FSMContext):
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


@dp.message(Command("post"))
async def start_posting(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.reply("Sizda ushbu buyruqni bajarish huquqi yo'q.")
        return
    await state.set_state(PostStates.waiting_for_post)
    await message.reply("Xabarni yuboring: Matn, rasm, video yoki gif.")

# Fayl yoki matnni qabul qilish va yuborish
@router.message(F.content_type.in_({"photo", "video", "animation", "text"}))
async def handle_post_content(message: types.Message, state: FSMContext):
    current_state = await state.get_state()

    # Faqat post rejimida ishlaydi
    if current_state != PostStates.waiting_for_post:
        return

    channels = await get_telegram_links()
    channel_ids = [link.split("/")[-1] for link in channels]

    for channel_id in channel_ids:
        if message.photo:
            file_id = message.photo[-1].file_id
            caption = message.caption or "Rasm yuborildi."
            await bot.send_photo(chat_id=f"@{channel_id}", photo=file_id, caption=caption)
        elif message.video:
            file_id = message.video.file_id
            caption = message.caption or "Video yuborildi."
            await bot.send_video(chat_id=f"@{channel_id}", video=file_id, caption=caption)
        elif message.animation:  # Gif (animation)
            file_id = message.animation.file_id
            caption = message.caption or "GIF yuborildi."
            await bot.send_animation(chat_id=f"@{channel_id}", animation=file_id, caption=caption)
        elif message.text:
            await bot.send_message(chat_id=f"@{channel_id}", text=message.text)
        else:
            await message.reply("Yuborilgan fayl turini aniqlab bo'lmadi.")
            return

    await message.reply("Xabar muvaffaqiyatli yuborildi!")


@dp.callback_query(lambda callback_query: callback_query.data.startswith("check_membership_"))
async def check_membership_handler(callback: CallbackQuery):
    logger.info(f"Callback data: {callback.data}")  # Log ma’lumotlarini chiqarish

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


@router.message()
async def handle_group_messages(message: types.Message):
    # if message.chat.type not in ["group", "supergroup"]:
    #     return  
    user_id = message.from_user.id
    channels = await get_telegram_links()

    # Foydalanuvchi kanallarga a'zo ekanligini tekshirish
    is_member = await check_user_in_channels(user_id, channels)
    first_name = message.from_user.first_name
    if not is_member:
        try:
            await message.delete()

            # Foydalanuvchi uchun tugmalar
            buttons = [
                [InlineKeyboardButton(text=f"📢 {channel.split('/')[-1]}", url=channel)]
                for channel in channels
            ]
            buttons.append([
                InlineKeyboardButton(text="✅ Tekshirish", callback_data=f"check_membership_{user_id}")
            ])
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            await message.answer(
                f"👋 Salom {first_name}\n❌ Siz ushbu guruhda yoza olmaysiz.\n👇 Guruhda yozish uchun pastagi barcha kanallarga a’zo bo‘lishingiz kerak!",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Xabarni o'chirishda xatolik: {e}")

    chat_id = message.chat.id
    text = message.text.lower().split()
    BAD_WORDS = await get_bad_words()  # Xabar matnini kichik harfga o‘tkazamiz
    # Nojo'ya so'zlarni tekshirish
    if any(word in text for word in BAD_WORDS):
        try:
            # Xabarni o'chirish
            await message.delete()
            # Foydalanuvchini vaqtincha bloklash
            block_time = datetime.now() + timedelta(hours=1)  # 1 soatga bloklash
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=types.ChatPermissions(can_send_messages=False),
                until_date=block_time
            )

            # Foydalanuvchiga ogohlantirish
            await message.answer(
                f"❌ Hurmatli {message.from_user.first_name}, siz nomaqbul so‘zlar ishlatdingiz. "
                f"Siz 1 soat davomida guruhda yozishdan mahrum bo‘ldingiz!"
            )
        except Exception as e:
            logger.error(f"Xabarni o'chirish yoki foydalanuvchini bloklashda xatolik: {e}")


# # Guruhga yangi foydalanuvchi qo'shilganda salomlashish
# @dp.message(F.new_chat_members)
# async def welcome_new_member(message: Message):
#     new_members = ", ".join([user.first_name for user in message.new_chat_members])
#     await message.answer(f"Xush kelibsiz, {new_members}! 😊")


# Asosiy funksiyani yangilash
async def main():
    dp.include_router(router)
    print("Bot ishga tushmoqda...")
    try:
        await dp.start_polling(bot)
    finally:
        await session.close()  # Sessiyani yopish
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())