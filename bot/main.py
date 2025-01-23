from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from django.conf import settings
from handlers.user_handlers import register_user_handlers
from handlers.admin_handlers import register_admin_handlers
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot va Dispatcher obyektlarini yaratish
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

async def main():
    # Handlerlarni ro'yxatga olish
    # register_user_handlers(dp, bot)
    register_admin_handlers(dp, bot)
    

    print("Bot ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
