# Generated by Django 5.1.3 on 2024-12-07 06:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kiber_security', '0009_badword'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupId',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('groupid', models.IntegerField(null=True, unique=True)),
            ],
        ),
    ]