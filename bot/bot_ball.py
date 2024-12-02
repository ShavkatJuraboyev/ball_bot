from aiogram.types import FSInputFile
from pytube import YouTube
import yt_dlp

async def download_youtube_video(message: types.Message, url: str):
    from pytube import YouTube

    yt = YouTube(url)
    stream = yt.streams.get_highest_resolution()
    file_path = stream.download()

    video = FSInputFile(file_path)  # Faylni FSInputFile ga o'girish
    await bot.send_video(message.chat.id, video)
    await message.answer("Video muvaffaqiyatli yuklandi!")

async def download_instagram_facebook_video(bot, chat_id, url):
    ydl_opts = {
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'format': 'best',
        'socket_timeout': 30,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

            video = FSInputFile(file_path)
            await bot.send_video(chat_id=chat_id, video=video)
            return "Video muvaffaqiyatli yuklandi!"
    except Exception as e:
        return f"Xato yuz berdi: {e}"
