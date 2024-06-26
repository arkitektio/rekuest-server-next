# Generated by Django 4.2.4 on 2024-05-03 08:59

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0015_template_extension"),
    ]

    operations = [
        migrations.AddField(
            model_name="provision",
            name="active",
            field=models.BooleanField(
                default=False,
                help_text="Is this provision active (e.g. should the agent provide the associated template)",
            ),
        ),
    ]
