# Generated by Django 5.1.4 on 2024-12-12 05:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_otptoken_otp_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='is_google_user',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='otptoken',
            name='otp_code',
            field=models.CharField(default='b7a924', max_length=6),
        ),
    ]
