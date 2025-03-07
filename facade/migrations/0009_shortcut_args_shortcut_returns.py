# Generated by Django 4.2.4 on 2025-03-07 07:52

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0008_alter_shortcut_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="shortcut",
            name="args",
            field=models.JSONField(default=list, help_text="Inputs for this Node"),
        ),
        migrations.AddField(
            model_name="shortcut",
            name="returns",
            field=models.JSONField(default=list, help_text="Outputs for this Node"),
        ),
    ]
