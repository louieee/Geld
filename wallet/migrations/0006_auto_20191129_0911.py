# Generated by Django 2.2.4 on 2019-11-29 08:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0005_auto_20191114_1140'),
    ]

    operations = [
        migrations.AddField(
            model_name='investor',
            name='login_retries',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='investor',
            name='login_timer',
            field=models.IntegerField(default=0),
        ),
    ]
