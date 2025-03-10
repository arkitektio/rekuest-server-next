# Generated by Django 4.2.4 on 2025-03-07 09:19

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0009_shortcut_args_shortcut_returns"),
    ]

    operations = [
        migrations.AddField(
            model_name="shortcut",
            name="allow_quick",
            field=models.BooleanField(
                default=False,
                help_text="Allow quick execution of this Shortcut (e.g. run without confirmation)",
            ),
        ),
        migrations.AlterField(
            model_name="shortcut",
            name="args",
            field=models.JSONField(default=list, help_text="Inputs for this Shortcut"),
        ),
        migrations.AlterField(
            model_name="shortcut",
            name="returns",
            field=models.JSONField(default=list, help_text="Outputs for this Shortcut"),
        ),
    ]
