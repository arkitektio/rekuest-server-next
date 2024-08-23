# Generated by Django 4.2.4 on 2024-08-23 09:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0008_dashboard_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="Panel",
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
                ("kind", models.CharField(max_length=2000)),
                (
                    "reservation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="panels",
                        to="facade.reservation",
                    ),
                ),
                (
                    "state",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="panels",
                        to="facade.state",
                    ),
                ),
            ],
        ),
        migrations.DeleteModel(
            name="Control",
        ),
        migrations.AddField(
            model_name="dashboard",
            name="panels",
            field=models.ManyToManyField(related_name="dashboard", to="facade.panel"),
        ),
    ]
