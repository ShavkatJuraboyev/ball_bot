# Generated by Django 5.1.3 on 2024-11-09 05:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('kiber_security', '0002_ball_friends_ball'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='users',
            name='user',
        ),
    ]
