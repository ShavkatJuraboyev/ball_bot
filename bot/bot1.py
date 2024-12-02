from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
import yt_dlp
import asyncio
from aiogram.fsm.storage.memory import MemoryStorage

# Bot tokeningizni kiriting
BOT_TOKEN = "6155323455:AAHYj4rVaIIiTAQhESrP3lWT16LtJXNZxlg"

# Bot va Dispatcher obyektlari
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Asosiy menyu uchun InlineKeyboard
main_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="YouTube", callback_data="platform_youtube")],
        [InlineKeyboardButton(text="Instagram", callback_data="platform_instagram")],
        [InlineKeyboardButton(text="Facebook", callback_data="platform_facebook")],
    ]
)

# /start komandasi uchun handler
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.answer("Quyidagi platformani tanlang:", reply_markup=main_menu)

# Tugma bosilganda ishlovchi handler
@dp.callback_query(lambda callback_query: callback_query.data.startswith("platform_"))
async def platform_selected(callback_query: types.CallbackQuery):
    platform = callback_query.data.split("_")[1].capitalize()
    await callback_query.message.answer(f"Iltimos, {platform} video linkini yuboring.")
    await callback_query.answer()  # Callback'dan foydalanilgani haqida tasdiq yuborish

# Linkni qayta ishlash uchun handler
@dp.message(lambda message: message.text.startswith("http"))
async def process_link(message: types.Message):
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
        else:  # Instagram va Facebook uchun
            await download_instagram_facebook_video(message, url)
    except Exception as e:
        await message.answer(f"Xato yuz berdi: {e}")

# YouTube uchun yuklash funksiyasi
async def download_youtube_video(message: types.Message, url: str):
    from pytube import YouTube

    yt = YouTube(url)
    stream = yt.streams.get_highest_resolution()
    file_path = stream.download()

    video = FSInputFile(file_path)  # Faylni FSInputFile ga o'girish
    await bot.send_video(message.chat.id, video)
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

# Botni ishga tushirish
async def main():
    print("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
