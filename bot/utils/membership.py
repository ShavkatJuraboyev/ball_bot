from aiogram.exceptions import TelegramBadRequest
from django.conf import settings
from aiogram import Bot

async def check_user_in_channels(user_id: int, channels: list) -> bool:
    """
    Foydalanuvchini berilgan kanallarda bor yoki yo'qligini tekshirish.
    
    :param user_id: Telegram foydalanuvchi ID.
    :param channels: Kanal linklarining ro'yxati.
    :return: Agar barcha kanallarda bor bo'lsa True, aks holda False.
    """
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    channel_usernames = [link.split("/")[-1] for link, _ in channels]  # Kanal username'larini olish

    for channel_username in channel_usernames:
        try:
            # Kanal haqida ma'lumot olish
            chat = await bot.get_chat(f"@{channel_username}")
            # Foydalanuvchini kanalda bor yoki yo'qligini tekshirish
            member = await bot.get_chat_member(chat_id=chat.id, user_id=user_id)
            
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except TelegramBadRequest as e:
            return False  # Kanalga ulanishda xato bo'lsa ham, False qaytariladi
    return True
