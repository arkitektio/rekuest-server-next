# Generated by Django 4.2.4 on 2025-03-06 16:36

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0007_toolbox_shortcut"),
    ]

    operations = [
        migrations.AlterField(
            model_name="shortcut",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
    ]
