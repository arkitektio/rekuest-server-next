# Generated by Django 4.2.4 on 2024-08-31 17:33

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="stateschema",
            old_name="state_hash",
            new_name="hash",
        ),
    ]
