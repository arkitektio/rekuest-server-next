# Generated by Django 4.2.4 on 2024-05-03 08:17

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0014_reservation_causing_dependency_alter_dependency_node"),
    ]

    operations = [
        migrations.AddField(
            model_name="template",
            name="extension",
            field=models.CharField(
                default="global", max_length=1000, verbose_name="Extension"
            ),
        ),
    ]
