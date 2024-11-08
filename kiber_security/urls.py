from django.urls import path
from .views import index, friends, share, style, style2, verify_user, add_link_ball

urlpatterns = [
    path('', index, name='index'),
    path('friends/', friends, name='friends'),
    path('share/', share, name='share'),
    path('style', style, name='style'),
    path('style2', style2, name='style2'),
    path('verify-user/', verify_user, name='verify_user'),
    path('add-link-ball/<int:link_id>/<int:telegram_id>/', add_link_ball, name='add_link_ball')
]