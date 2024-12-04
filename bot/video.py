import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
import yt_dlp
import os

# Bot tokenini kiritish
BOT_TOKEN = "6253459858:AAFBUL4Lzam7PSjoOq8t7NdwKwvWLUHANUg"

# Log sozlamalari
logging.basicConfig(level=logging.INFO)

# Bot va Dispatcher obyektlari
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Video yuklash funksiyasi
def download_video(video_url: str, output_path: str = "downloads") -> str:
    """
    Berilgan URL orqali videoni yuklab oladi.
    :param video_url: Yuklash kerak bo'lgan video havolasi
    :param output_path: Faylni saqlash joyi
    :return: Yuklangan faylning to'liq yo'li yoki None
    """
    try:
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        # yt-dlp sozlamalari
        ydl_opts = {
            'format': 'best[filesize<1G]',  # Eng yaxshi format (1GB cheklov bilan)
            'outtmpl': f'{output_path}/%(title)s.%(ext)s',  # Fayl nomi va formati
            'noplaylist': True,  # Faqat bitta videoni yuklash
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            return ydl.prepare_filename(info)
    except Exception as e:
        logging.error(f"Video yuklashda xatolik: {e}")
        return None

# /start komandasi
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.reply(
            "👋 Salom!\n\n"
            "🎥 Men video yuklab beruvchi botman.\n\n"
            "🎯 Video havolasini yuboring va men uni yuklab beraman!"
        )

# Video yuklash komandasi
@dp.message(F.text)
async def download_video_command(message: Message):
    video_url = message.text

    # URL validatsiyasi
    if not video_url.startswith("http"):
        await message.reply("Iltimos, to'g'ri URL havolani kiriting!")
        return

    await message.reply("Videoni yuklashni boshlayapman. Iltimos, kuting...")

    file_path = download_video(video_url)
    if file_path:
        try:
            # Yuklangan videoni yuborish
            await message.reply("Video yuklandi. Sizga yuborilmoqda...")
            with open(file_path, "rb") as video:
                await message.answer_document(video)

            # Faylni o'chirish
            os.remove(file_path)
        except Exception as e:
            logging.error(f"Videoni yuborishda xatolik: {e}")
            await message.reply("Videoni yuborishda xatolik yuz berdi.")
    else:
        await message.reply("Videoni yuklab bo'lmadi. Havolani tekshirib, qaytadan urinib ko'ring.")

# Botni ishga tushirish
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())



# import os
# import asyncio
# from aiogram import Bot, Dispatcher
# from aiogram.types import InputFile, Message
# from aiogram.filters import Command
# from yt_dlp import YoutubeDL
# from aiogram import F

# # Bot sozlamalari
# API_TOKEN = "6253459858:AAFBUL4Lzam7PSjoOq8t7NdwKwvWLUHANUg"
# bot = Bot(token=API_TOKEN)
# dp = Dispatcher()

# # Video yuklab olish funksiyasi
# async def download_and_send_video(message: Message, video_url: str):
#     try:
#         # YT-DLP video yuklash
#         ydl_opts = {
#             "outtmpl": "downloads/%(title)s.%(ext)s",  # Fayl saqlash yo'li va nomi
#             "format": "best",  # Eng yaxshi format
#             "merge_output_format": "mp4",  # Birlashtirish uchun format
#             "quiet": True,  # Loglarni o'chirish
#             "no_warnings": True,  # Ogohlantirishlarni o'chirish
#         }

#         with YoutubeDL(ydl_opts) as ydl:
#             info_dict = ydl.extract_info(video_url, download=True)
#             video_filename = f"downloads/{info_dict['id']}.{info_dict['ext']}"  # Yuklangan video fayli

#         # Video faylni yuborish
#         video = InputFile(video_filename)
#         await message.reply("Video yuklanmoqda...", video=video)
#     except Exception as e:
#         await message.reply(f"Xatolik yuz berdi: {e}")

# # /start komandasi
# @dp.message(Command("start"))
# async def cmd_start(message: Message):
#     await message.answer(
#         "👋 Salom!\n\n"
#         "🎥 Men video yuklab beruvchi botman.\n\n"
#         "🎯 Video havolasini yuboring va men uni yuklab beraman!"
#     )

# # Video havolani qayta ishlash
# @dp.message(F.text)
# async def handle_video_request(message: Message):
#     url = message.text
#     if not url.startswith("http"):
#         await message.answer("❌ Iltimos, haqiqiy video havolasini yuboring!")
#         return

#     await message.answer("⏳ Yuklanmoqda, biroz kuting...")
#     try:
#         file_path, title = download_video(url)

#         # Video faylni jo'natish
#         with open(file_path, "rb") as video_file:
#             video = InputFile(video_file, filename=os.path.basename(file_path))
#             await bot.send_video(
#                 chat_id=message.chat.id,
#                 video=video,
#                 caption=f"🎬 {title}\n✅ Yuklab olindi!"
#             )

#         os.remove(file_path)  # Faylni o'chirish
#     except Exception as e:
#         await message.answer(f"❌ Xatolik yuz berdi: {e}")

# # # /download komandasi
# @dp.message_handler(commands=["download"])
# async def download_video(message: Message):
#     # Foydalanuvchidan video URL olish
#     video_url = message.get_args()
#     if not video_url:
#         await message.reply("Iltimos, video URL manzilini kiriting!")
#         return
#     await download_and_send_video(message, video_url)


# # Botni ishga tushirish
# async def on_start():
#     os.makedirs("downloads", exist_ok=True)  # Yuklash katalogini yaratish
#     await dp.start_polling(bot)

# if __name__ == "__main__":
#     asyncio.run(on_start())
