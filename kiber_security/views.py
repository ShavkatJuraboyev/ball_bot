from django.shortcuts import render
from kiber_security.models import Users


def index(request):
    if request.user.is_authenticated:
        telegram_id = request.user.username
        print(telegram_id)
    else:
        print("Foydalanuvchi tizimga kirmagan")
    return render(request, 'users/index.html')

def friends(request):
    return render(request, 'users/friends.html')

def share(request):
    return render(request, 'users/share.html')

def style(request):
    return render(request, 'users/style.html')

def style2(request):
    return render(request, 'users/style2.html')