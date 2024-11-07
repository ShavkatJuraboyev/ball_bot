from django.urls import path
from .views import index, friends, share, style, style2

urlpatterns = [
    path('', index, name='index'),
    path('friends/', friends, name='friends'),
    path('share/', share, name='share'),
    path('style', style, name='style'),
    path('style2', style2, name='style2'),
]