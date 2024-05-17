# Generated by Django 4.2.4 on 2024-05-17 11:24

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0022_alter_reservation_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="agent",
            name="connected",
            field=models.BooleanField(
                default=False, help_text="Is this Agent connected to the backend"
            ),
        ),
        migrations.AddField(
            model_name="agent",
            name="last_seen",
            field=models.DateTimeField(
                auto_created=True,
                auto_now_add=True,
                default=django.utils.timezone.now,
                help_text="The last time this Agent was seen",
            ),
            preserve_default=False,
        ),
    ]
