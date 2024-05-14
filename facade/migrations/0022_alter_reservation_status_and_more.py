# Generated by Django 4.2.4 on 2024-05-14 13:06

from django.db import migrations, models
import django.db.models.deletion
import django_choices_field.fields
import facade.enums


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0021_alter_assignationevent_level_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="reservation",
            name="status",
            field=django_choices_field.fields.TextChoicesField(
                choices=[
                    ("PENDING", "Pending (Reservation is pending)"),
                    ("CREATE", "Create"),
                    ("RESCHEDULE", "Reschedule"),
                    ("DELETED", "Deleted"),
                    ("CHANGE", "Change"),
                    ("ACTIVE", "Active"),
                    ("INACTIVE", "Inactive"),
                    ("UNCONNECTED", "Unconnected"),
                    ("ENDED", "Ended"),
                    ("UNHAPPY", "Unhappy"),
                    ("HAPPY", "Happy"),
                    ("LOG", "Log"),
                ],
                choices_enum=facade.enums.ReservationEventChoices,
                default="PENDING",
                help_text="The Status of this Provision",
                max_length=1000,
            ),
        ),
        migrations.AlterField(
            model_name="reservation",
            name="statusmessage",
            field=models.CharField(
                blank=True,
                help_text="Clear Text status of the ssssssProvision as for now",
                max_length=1000,
            ),
        ),
        migrations.CreateModel(
            name="HardwareRecord",
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("cpu_count", models.IntegerField(default=0)),
                (
                    "cpu_vendor_name",
                    models.CharField(default="Unknown", max_length=1000),
                ),
                ("cpu_frequency", models.FloatField(default=0)),
                (
                    "agent",
                    models.ForeignKey(
                        help_text="The associated agent for this HardwareRecord",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hardware_records",
                        to="facade.agent",
                    ),
                ),
            ],
        ),
    ]
