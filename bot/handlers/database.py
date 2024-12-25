import os
import sys
import django
from aiogram import F
from asgiref.sync import sync_to_async
from django.conf import settings

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from kiber_security.models import Users, Ball, Link, BadWord, GroupId

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