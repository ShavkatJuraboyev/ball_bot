import os
import sys
import django
import logging
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import Message, ContentType
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram import F
from asgiref.sync import sync_to_async
from django.conf import settings
from handlers.database import get_all_users_ball, get_all_link, get_telegram_links
from handlers.auth import is_admin
from aiogram.fsm.context import FSMContext
import os, sys, django, logging
from asgiref.sync import sync_to_async

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from kiber_security.models import Users

router = Router()

class PostStates(StatesGroup):
    waiting_for_post = State()

def generate_admin_buttons():
    buttons = [
        [types.InlineKeyboardButton(text=f"👥 Foydalanuvchilar", callback_data=f"all_users"),
         types.InlineKeyboardButton(text=f"📢 Telgram kanallar", callback_data=f"all_channels")],
        [types.InlineKeyboardButton(text=f"👥 Post yuborish", callback_data=f"post_users"),
         types.InlineKeyboardButton(text=f"📢 Post yuborish", callback_data=f"post_channels")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(Command("start_admin"))
async def admin_start_commad(message: types.Message, bot: Bot):
    # if message.chat.type == "private":
    if not is_admin(message.from_user.id):
        await message.reply("❌ Ushbu buyruq faqat adminlar uchun!")
        await message.delete()
        return
    
    keyboard = generate_admin_buttons()
    await message.answer(text="Quydagilardan birini tanlang", reply_markup=keyboard)


async def admin_start_back(callback: types.CallbackQuery):
    if not is_admin(callback.message.chat.id):
        await callback.answer("❌ Ushbu buyruq faqat adminlar uchun!")
        await callback.message.delete()
        return

    keyboard = generate_admin_buttons()
    await callback.message.answer(text="Quydagilardan birini tanlang", reply_markup=keyboard)
    await callback.message.delete()

async def users_all(callback: types.CallbackQuery, page: int = 1):
    if not is_admin(callback.message.chat.id):
        await callback.answer("❌ Ushbu buyruq faqat adminlar uchun!")
        await callback.message.delete()
        return

    users = await get_all_users_ball()

    if not users:
        button = [[types.InlineKeyboardButton(text="🔙 Ortga", callback_data="back_admin")]]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=button)
        await callback.message.answer(text="❌ Hech qanday foydalanuvchi mavjud emas", reply_markup=keyboard)
        await callback.message.delete()
        return

    # Foydalanuvchilarni all_ball bo'yicha kamayish tartibida saralash
    users = sorted(users, key=lambda user: user['all_ball'], reverse=True)

    # Har sahifada ko'rsatiladigan foydalanuvchilar
    users_per_page = 10
    start_index = (page - 1) * users_per_page
    end_index = start_index + users_per_page
    users_to_display = users[start_index:end_index]

    buttons = [
        [
            types.InlineKeyboardButton(
                text=f"👤 {user['first_name']} {user['last_name']} - ⭐️{user['all_ball']}", url=f"http://127.0.0.1:8000/admin/kiber_security/users/{user['id']}/change/" )
        ]
        for user in users_to_display
    ]
    
    # Sahifalarni ko'rsatish uchun "keyingi" va "oldingi" tugmalari
    buttons.append([
        types.InlineKeyboardButton(text="⬅️", callback_data=f"oldingi_{page-1}" if page > 1 else "oldingi_1"),
        types.InlineKeyboardButton(text="➡️", callback_data=f"keyingi_{page+1}" if end_index < len(users) else f"keyingi_{page}")
    ])
    buttons.append([types.InlineKeyboardButton(text="🔙 Ortga", callback_data="back_admin")])
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer(text=f"📊 Telegram foydalanuvchilari statistikas- Sahifa {page}", reply_markup=keyboard)
    await callback.message.delete()


async def next_page(callback: types.CallbackQuery):
    page = int(callback.data.split('_')[1])  # keyingi_{page} dan sahifa raqamini olish
    await users_all(callback, page)


async def prev_page(callback: types.CallbackQuery):
    page = int(callback.data.split('_')[1])  # oldingi_{page} dan sahifa raqamini olish
    await users_all(callback, page)

async def channels_all(callback: types.CallbackQuery):
    if not is_admin(callback.message.chat.id):
        await callback.answer("❌ Ushbu buyruq faqat adminlar uchun!")
        await callback.message.delete()
        return

    channels = await get_all_link()
    if not channels:
        button = [[
            types.InlineKeyboardButton(text=f"⬅️ Ortga", callback_data="back_admin")
            ]]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=button)
        await callback.message.answer(text="❌ Hech qanday Kanal mavjud emas", reply_markup=keyboard)
        await callback.message.delete()
        return
    buttons = [
        [types.InlineKeyboardButton(text=f"📢 {channel.description}", url=channel.url)]
        for channel in channels
    ]
    buttons.append(
        [types.InlineKeyboardButton(text=f"🔙 Ortga", callback_data="back_admin")
        ])
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer(text="Barcha telegram kannallar", reply_markup=keyboard)
    await callback.message.delete()

async def users_post(callback: types.CallbackQuery):
    if not is_admin(callback.message.chat.id):
        await callback.answer("❌ Ushbu buyruq faqat adminlar uchun!")
        await callback.message.delete()
        return
    
    button = [[
            types.InlineKeyboardButton(text=f"👥 Foydalanuvchilar", callback_data=f"all_users"),
            types.InlineKeyboardButton(text=f"🔙 Bosh saxifa", callback_data="back_admin")
        ]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=button)
    await callback.message.answer(
        f"Barcha foydalanuvchilarga reklama yuborish uchun format:\n`/broadcast` ni yuboring\n\n"
        f"Masalan:\n/broadcast",
        parse_mode="Markdown", reply_markup=keyboard
    )

async def chanels_post(callback: types.CallbackQuery):
    if not is_admin(callback.message.chat.id):
        await callback.answer("❌ Ushbu buyruq faqat adminlar uchun!")
        await callback.message.delete()
        return
    
    button = [[
            types.InlineKeyboardButton(text=f"📢 Telgram kanallar", callback_data=f"all_channels"),
            types.InlineKeyboardButton(text=f"🔙 Bosh saxifa", callback_data="back_admin")
        ]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=button)
    await callback.message.answer(
        f"Barcha Kanal va guruhlarga post yuborish uchun format:\n`/post` ni yuboring\n\n"
        f"Masalan:\n/post",
        parse_mode="Markdown", reply_markup=keyboard
    )

registered_channels = {}

@router.message(Command('register'))
async def register_channel(message: Message):
    # Kanalning turi "group" yoki "supergroup" ekanligini tekshiramiz
    if message.chat.type in ['group', 'supergroup', 'channel']:  # message.chat.type orqali tekshiramiz
        chat_id = message.chat.id
        chat_title = message.chat.title
        if chat_id not in registered_channels:
            registered_channels[chat_id] = chat_title
            await message.answer(f"✅ Kanal '{chat_title}' ro'yxatdan o'tkazildi!")
        else:
            await message.answer("⚠️ Bu kanal allaqachon ro'yxatdan o'tgan.")
    else:
        await message.answer("❌ Bu buyruq faqat guruhlar va superguruhlar uchun ishlaydi.")

@router.message(Command("channels"))
async def show_registered_channels(message: Message):
    # if message.chat.type == "private":
    if not is_admin(message.chat.id):
        await message.reply("❌ Ushbu buyruq faqat adminlar uchun!")
        await message.delete()
        return
    if not registered_channels:
        await message.answer("Hech qanday kanal ro'yxatdan o'tmagan.")
    else:
        channels_list = "\n".join([f"{title} (ID: {chat_id})" for chat_id, title in registered_channels.items()])
        await message.answer(f"Ro'yxatdagi kanallar ({len(registered_channels)} ta):\n{channels_list}")


ADMIN_ID = 1421622919 

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
@router.message(Command("broadcast"))
async def start_broadcast(message: types.Message, state: FSMContext):
    # if message.chat.type == "private":
    if not is_admin(message.from_user.id):
        await message.reply("❌ Ushbu buyruq faqat adminlar uchun!")
        await message.delete()
        return
    
    if message.from_user.id == ADMIN_ID:
        await state.set_state("broadcast")  # Holatni "broadcast"ga o'rnatish
        await message.answer("Iltimos, reklama matni yoki media fayl yuboring.")
    else:
        await message.answer("Sizda ushbu amalni bajarish uchun ruxsat yo'q.")
    

@router.message(StateFilter("broadcast"), F.content_type.in_([ContentType.TEXT, ContentType.PHOTO, ContentType.VIDEO]))
async def handle_broadcast_media(message: types.Message, state: FSMContext, bot: Bot):
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

@router.message(Command("post"))
async def start_posting(message: types.Message, state: FSMContext):
    # if message.chat.type == "private":
    if not is_admin(message.from_user.id):
        await message.reply("❌ Ushbu buyruq faqat adminlar uchun!")
        await message.delete()
        return
        
    if message.from_user.id != ADMIN_ID:
        await message.reply("Sizda ushbu buyruqni bajarish huquqi yo'q.")
        return
    await state.set_state(PostStates.waiting_for_post)
    await message.reply("Xabarni yuboring: Matn, rasm, video yoki gif.")

# Fayl yoki matnni qabul qilish va yuborish
@router.message(F.content_type.in_({"photo", "video", "animation", "text"}))
async def handle_post_content(message: types.Message, state: FSMContext, bot: Bot):
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

def register_admin_handlers(dp: Dispatcher, bot: Bot):
    dp.include_router(router)

    router.callback_query.register(
        admin_start_back,
        lambda c: c.data and c.data.startswith('back_admin')
    )

    router.callback_query.register(
        users_all,
        lambda c: c.data and c.data.startswith("all_users") 
    )

    router.callback_query.register(
        channels_all,
        lambda c: c.data and c.data.startswith("all_channels") 
    )

    router.callback_query.register(
        next_page,
        lambda c: c.data and c.data.startswith("keyingi_")
    )
    router.callback_query.register(
        prev_page,
        lambda c: c.data and c.data.startswith("oldingi_")
    )

    router.callback_query.register(
        users_post,
        lambda c: c.data and c.data.startswith("post_users") 
    )
    router.callback_query.register(
        chanels_post,
        lambda c: c.data and c.data.startswith("post_channels") 
    )