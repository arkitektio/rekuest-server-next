# Generated by Django 4.2.4 on 2024-05-06 13:18

from django.db import migrations, models
import django_choices_field.fields
import facade.enums


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0018_alter_assignation_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="provision",
            name="dependencies_met",
            field=models.BooleanField(
                default=False,
                help_text="Are all dependencies met for this provision. Should change to True if all dependencies are met (potential sync error)",
            ),
        ),
        migrations.AddField(
            model_name="provision",
            name="provided",
            field=models.BooleanField(
                default=False,
                help_text="Is the provision provided (e.g. is the template available on the agent). This does NOT mean that the provision is assignable. Only if all the dependencies are met, the provision is assignable",
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="happy",
            field=models.BooleanField(
                default=False,
                help_text="Is this reservation happily connected. E.g does it have enough links according to its policy",
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="viable",
            field=models.BooleanField(
                default=False,
                help_text="Is this reservation viable. E.g. does it have a viable amount of connections",
            ),
        ),
        migrations.AlterField(
            model_name="provision",
            name="status",
            field=django_choices_field.fields.TextChoicesField(
                choices=[
                    ("DENIED", "Denied (Provision was rejected by the platform)"),
                    (
                        "PENDING",
                        "Pending (Request has been created and waits for its initial creation)",
                    ),
                    ("BOUND", "Bound (Provision was bound to an Agent)"),
                    (
                        "PROVIDING",
                        "Providing (Request has been send to its Agent and waits for Result",
                    ),
                    ("LOG", "Log (Provision logged a message)"),
                    ("ACTIVE", "Active (Provision is currently active)"),
                    ("REFUSED", "Denied (Provision was rejected by the App)"),
                    ("INACTIVE", "Inactive (Provision is currently not active)"),
                    (
                        "CANCELING",
                        "Cancelling (Provisions is currently being cancelled)",
                    ),
                    (
                        "LOST",
                        "Lost (Subscribers to this Topic have lost their connection)",
                    ),
                    (
                        "RECONNECTING",
                        "Reconnecting (We are trying to Reconnect to this Topic)",
                    ),
                    ("UNHAPPY", "Unhappy"),
                    (
                        "ERROR",
                        "Error (Reservation was not able to be performed (See StatusMessage)",
                    ),
                    (
                        "CRITICAL",
                        "Critical (Provision resulted in an critical system error)",
                    ),
                    (
                        "ENDED",
                        "Ended (Provision was cancelled by the Platform and will no longer create Topics)",
                    ),
                    (
                        "CANCELLED",
                        "Cancelled (Provision was cancelled by the User and will no longer create Topics)",
                    ),
                ],
                choices_enum=facade.enums.ProvisionEventChoices,
                default="INACTIVE",
                help_text="The Status of this Provision",
                max_length=1000,
            ),
        ),
    ]