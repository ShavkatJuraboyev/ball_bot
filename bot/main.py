import os, sys, django
import asyncio, logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from django.conf import settings
from handlers.user_handlers import register_user_handlers

# Django sozlamalarini yuklash
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Bot va Dispatcher obyektlarini yaratish
session = AiohttpSession(timeout=600) 
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, session=session)
dp = Dispatcher(storage=MemoryStorage())






# Asosiy funksiyani yangilash
async def main():
    register_user_handlers(dp, bot)
    
    try:
        print("Bot ishga tushmoqda...")
        await dp.start_polling(bot)
        
    finally:
        print("Shutting down bot...")
        await session.close()

if __name__ == "__main__":
    asyncio.run(main())