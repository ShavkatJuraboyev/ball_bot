# Generated by Django 5.1.3 on 2024-11-08 08:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kiber_security', '0002_link_ball'),
    ]

    operations = [
        migrations.AddField(
            model_name='ball',
            name='instagram_ball',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='ball',
            name='telegram_ball',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='ball',
            name='youtube_ball',
            field=models.BigIntegerField(default=0),
        ),
    ]
