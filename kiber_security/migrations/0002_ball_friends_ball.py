# Generated by Django 5.1.3 on 2024-11-09 04:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kiber_security', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ball',
            name='friends_ball',
            field=models.BigIntegerField(default=0),
        ),
    ]