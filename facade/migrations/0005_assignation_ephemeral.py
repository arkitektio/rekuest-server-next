# Generated by Django 4.2.4 on 2024-11-28 11:20

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0004_alter_assignationevent_message"),
    ]

    operations = [
        migrations.AddField(
            model_name="assignation",
            name="ephemeral",
            field=models.BooleanField(
                default=False,
                help_text="Is this Assignation ephemeral (e.g. should it be deleted after its done or should it be kept for future reference)",
            ),
        ),
    ]
