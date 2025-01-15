import os
import sys
import django
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db.models import Sum

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from kiber_security.models import Users, Ball, Link, BadWord, GroupId, UserTest

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
    return list(Link.objects.filter(link_type='telegram').values_list('url', 'ball'))

@sync_to_async
def get_bad_words():
    return list(BadWord.objects.values_list('word', flat=True))

@sync_to_async
def get_groupid():
    return list(GroupId.objects.values_list('groupid', flat=True))

@sync_to_async
def get_all_users_ball():
    # Foydalanuvchilar ro'yxatini chiqaramiz
    users = Users.objects.all()

    user_balls = []
    for user in users:
        # Ball obyekti mavjudligini tekshiramiz
        ball = Ball.objects.filter(user=user).aggregate(all_ball=Sum('all_ball'))
        
        # Agar `score` obyekti mavjud bo'lmasa, `score` 0 bo'ladi
        ball1 = UserTest.objects.filter(user=user).aggregate(score=Sum('score'))

        # Agar `Ball` obyekti mavjud bo'lmasa, `all_ball` 0 bo'ladi
        all_ball = ((ball['all_ball'] or 0) + (ball1['score'] or 0))

        # Har bir foydalanuvchi va uning umumiy ballini ro'yxatga qo'shamiz
        user_balls.append({
            "id":user.id,
            "telegram_id": user.telegram_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "all_ball": all_ball
        })

    return user_balls

@sync_to_async
def get_all_link():
    return list(Link.objects.filter(link_type='telegram'))