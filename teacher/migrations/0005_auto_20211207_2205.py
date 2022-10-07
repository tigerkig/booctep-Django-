# Generated by Django 3.2.6 on 2021-12-07 13:05

import datetime
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('teacher', '0004_auto_20211122_1718'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transactions',
            name='course_id',
        ),
        migrations.RemoveField(
            model_name='transactions',
            name='fees',
        ),
        migrations.RemoveField(
            model_name='transactions',
            name='revenue',
        ),
        migrations.AddField(
            model_name='transactions',
            name='amount',
            field=models.FloatField(default=0, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name='transactions',
            name='date_time',
            field=models.DateTimeField(blank=True, default=datetime.datetime.now),
        ),
        migrations.AddField(
            model_name='transactions',
            name='payment_method',
            field=models.CharField(default='', max_length=255),
        ),
        migrations.AddField(
            model_name='transactions',
            name='teacher',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]