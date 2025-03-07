# Generated by Django 4.2.4 on 2025-03-06 16:13

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("facade", "0006_agentevent"),
    ]

    operations = [
        migrations.CreateModel(
            name="Toolbox",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=1000)),
                ("description", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "creator",
                    models.ForeignKey(
                        help_text="The user that created this Shortcut",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="toolboxes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Shortcut",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=1000)),
                ("description", models.TextField()),
                ("saved_args", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "creator",
                    models.ForeignKey(
                        help_text="The user that created this Shortcut",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="shortcuts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "node",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="shortcuts",
                        to="facade.node",
                    ),
                ),
                (
                    "template",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="shortcuts",
                        to="facade.template",
                    ),
                ),
                (
                    "toolbox",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="shortcuts",
                        to="facade.toolbox",
                    ),
                ),
            ],
        ),
    ]
