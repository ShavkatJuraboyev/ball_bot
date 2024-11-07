from django.shortcuts import render

def index(request):
    return render(request, 'users/index.html')

def friends(request):
    return render(request, 'users/friends.html')

def share(request):
    return render(request, 'users/share.html')

def style(request):
    return render(request, 'users/style.html')

def style2(request):
    return render(request, 'users/style2.html')