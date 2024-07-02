# Generated by Django 4.2.4 on 2024-07-02 13:09

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0028_node_is_dev"),
    ]

    operations = [
        migrations.AddField(
            model_name="agent",
            name="extensions",
            field=models.JSONField(
                default=list, help_text="The extensions for this Agent", max_length=2000
            ),
        ),
    ]
