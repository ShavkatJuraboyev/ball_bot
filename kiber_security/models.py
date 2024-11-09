from django.db import models
import uuid

class Users(models.Model):
    telegram_id = models.CharField(max_length=100, unique=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    username_link = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    referral_code = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    referred_by = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)
    referred = models.BooleanField(default=False)
    is_first_start = models.BooleanField(default=True)  # Foydalanuvchi botga birinchi marta start bosganligini belgilaydi

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.first_name} {self.last_name}"



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
    friends_ball = models.BigIntegerField(default=0)
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

    def add_friend_points(self, points_per_friend=200):
        # Do'stlar soniga qarab friends_ballni yangilash
        friends_count = self.user.referrals.count()  # Taklif qilingan do'stlar soni
        self.friends_ball = friends_count * points_per_friend
        self.all_ball = self.youtube_ball + self.telegram_ball + self.instagram_ball + self.friends_ball
        self.save()

class LinkVisit(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    link = models.ForeignKey(Link, on_delete=models.CASCADE)
    visited_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} visited {self.link} at {self.visited_at}"