from django.db import models
from django.contrib.auth.models import User

class Users(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    username = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

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

