from django.db import models
from django.contrib.auth.models import User
import uuid

class Users(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    username = models.CharField(max_length=100, blank=True, null=True)
    username_link = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    # Taklif havolasi uchun referal kod
    referral_code = models.UUIDField(default=uuid.uuid4, unique=True)
    referred_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals')

    # OneToOne bog'lanishi orqali User modeliga bog'lash
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_profile')

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    # save metodini o'zgartirib, username'ni telegram_id ga saqlash
    def save(self, *args, **kwargs):
        if not self.username:  # agar username bo'lmasa
            self.username = str(self.telegram_id)
            user = User.objects.create_user(username=self.username, first_name=self.first_name, last_name=self.last_name)
            self.user = user  # User modelini bog'lash
        super().save(*args, **kwargs)

class Link(models.Model):
    TYPE_CHOICES = (
        ('youtube', 'YouTube'),
        ('telegram', 'Telegram'),
        ('instagram', 'Instagram'),
    )

    url = models.URLField()
    link_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    description = models.CharField(max_length=255, blank=True, null=True)
    ball = models.IntegerField()

    def __str__(self):
        return self.description or self.url

class Ball(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    youtube_ball = models.BigIntegerField(default=0)
    telegram_ball = models.BigIntegerField(default=0)
    instagram_ball = models.BigIntegerField(default=0)
    all_ball = models.BigIntegerField(default=0)

    def __str__(self):
        return f"{self.user} - {self.all_ball}"

    def add_ball(self, link_type, points):
        # Link turiga qarab ballarni oshirish
        if link_type == 'youtube':
            self.youtube_ball += points
        elif link_type == 'telegram':
            self.telegram_ball += points
        elif link_type == 'instagram':
            self.instagram_ball += points
        
        # Umumiy ballni hisoblash
        self.all_ball = self.youtube_ball + self.telegram_ball + self.instagram_ball
        self.save()  # Saqlash

class LinkVisit(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    link = models.ForeignKey(Link, on_delete=models.CASCADE)
    visited_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} visited {self.link} at {self.visited_at}"