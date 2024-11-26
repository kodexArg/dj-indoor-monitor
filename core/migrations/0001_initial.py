# Generated by Django 5.1.3 on 2024-11-26 08:41

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SensorData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('sensor', models.CharField(max_length=255)),
                ('t', models.FloatField()),
                ('h', models.FloatField()),
            ],
        ),
    ]
