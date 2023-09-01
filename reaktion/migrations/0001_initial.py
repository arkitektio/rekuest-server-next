# Generated by Django 4.2.4 on 2023-09-01 10:43

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_choices_field.fields
import reaktion.enums
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Flow",
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
                (
                    "restrict",
                    models.JSONField(
                        default=list,
                        help_text="Restrict access to specific nodes for this diagram",
                    ),
                ),
                ("version", models.CharField(default="1.0alpha", max_length=100)),
                ("name", models.CharField(max_length=100, null=True)),
                ("nodes", models.JSONField(blank=True, default=list, null=True)),
                ("edges", models.JSONField(blank=True, default=list, null=True)),
                ("graph", models.JSONField(blank=True, null=True)),
                ("hash", models.CharField(default=uuid.uuid4, max_length=4000)),
                (
                    "description",
                    models.CharField(
                        blank=True,
                        default="Add a Desssscription",
                        max_length=50000,
                        null=True,
                    ),
                ),
                (
                    "brittle",
                    models.BooleanField(
                        default=False,
                        help_text="Is this a brittle flow? aka. should the flow fail on any exception?",
                    ),
                ),
                (
                    "creator",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "pinned_by",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The users that have pinned the position",
                        related_name="pinned_flows",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ReactiveTemplate",
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
                ("name", models.CharField(blank=True, max_length=100, null=True)),
                (
                    "description",
                    models.CharField(blank=True, max_length=1000, null=True),
                ),
                (
                    "kind",
                    django_choices_field.fields.TextChoicesField(
                        choices=[
                            ("ZIP", "ZIP (Zip the data)"),
                            (
                                "COMBINELATEST",
                                "COMBINELATEST (Combine values with latest value from each stream)",
                            ),
                            (
                                "WITHLATEST",
                                "WITHLATEST (Combine a leading value with the latest value)",
                            ),
                            (
                                "BUFFER_COMPLETE",
                                "BUFFER_COMPLETE (Buffer values until complete is retrieved)",
                            ),
                            (
                                "BUFFER_UNTIL",
                                "BUFFER_UNTIL (Buffer values until signal is send)",
                            ),
                            ("DELAY", "DELAY (Delay the data)"),
                            (
                                "DELAY_UNTIL",
                                "DELAY_UNTIL (Delay the data until signal is send)",
                            ),
                            ("CHUNK", "CHUNK (Chunk the data)"),
                            ("SPLIT", "SPLIT (Split the data)"),
                            ("OMIT", "OMIT (Omit the data)"),
                            (
                                "ENSURE",
                                "ENSURE (Ensure the data (discards None in the stream))",
                            ),
                            ("ADD", "ADD (Add a number to the data)"),
                            ("SUBTRACT", "SUBTRACT (Subtract a number from the data)"),
                            ("MULTIPLY", "MULTIPLY (Multiply the data with a number)"),
                            ("DIVIDE", "DIVIDE (Divide the data with a number)"),
                            ("MODULO", "MODULO (Modulo the data with a number)"),
                            ("POWER", "POWER (Power the data with a number)"),
                            ("PREFIX", "PREFIX (Prefix the data with a string)"),
                            ("SUFFIX", "SUFFIX (Suffix the data with a string)"),
                            ("FILTER", "FILTER (Filter the data of a union)"),
                            (
                                "GATE",
                                "GATE (Gate the data, first value is gated, second is gate)",
                            ),
                            ("TO_LIST", "TO_LIST (Convert to list)"),
                            ("FOREACH", "FOREACH (Foreach element in list)"),
                            ("IF", "IF (If condition is met)"),
                            ("AND", "AND (AND condition)"),
                            ("ALL", "ALL (establish if all values are Trueish)"),
                        ],
                        choices_enum=reaktion.enums.ReactiveKindChoices,
                        default="ZIP",
                        help_text="Check async Programming Textbook",
                        max_length=1000,
                    ),
                ),
                ("instream", models.JSONField(blank=True, default=list, null=True)),
                ("outstream", models.JSONField(blank=True, default=list, null=True)),
                ("constream", models.JSONField(blank=True, default=list, null=True)),
                ("defaults", models.JSONField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Run",
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
                (
                    "assignation",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                ("status", models.CharField(blank=True, max_length=100, null=True)),
                ("snapshot_interval", models.IntegerField(blank=True, null=True)),
                (
                    "flow",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="runs",
                        to="reaktion.flow",
                    ),
                ),
                (
                    "pinned_by",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The users that have pinned the position",
                        related_name="pinned_runs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Trace",
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
                ("provision", models.CharField(blank=True, max_length=100, null=True)),
                ("snapshot_interval", models.IntegerField(blank=True, null=True)),
                (
                    "flow",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conditions",
                        to="reaktion.flow",
                    ),
                ),
                (
                    "pinned_by",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The users that have pinned the position",
                        related_name="pinned_conditions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Workspace",
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
                (
                    "restrict",
                    models.JSONField(
                        default=list,
                        help_text="Restrict access to specific nodes for this diagram",
                    ),
                ),
                ("name", models.CharField(max_length=100, null=True)),
                (
                    "creator",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "pinned_by",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The users that have pinned the position",
                        related_name="pinned_workspaces",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TraceSnapshot",
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
                (
                    "created_at",
                    models.DateTimeField(auto_created=True, auto_now_add=True),
                ),
                ("status", models.CharField(blank=True, max_length=100, null=True)),
                (
                    "trace",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="snapshots",
                        to="reaktion.trace",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TraceEvent",
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
                (
                    "created_at",
                    models.DateTimeField(auto_created=True, auto_now_add=True),
                ),
                ("source", models.CharField(max_length=1000)),
                ("value", models.CharField(blank=True, max_length=1000)),
                ("state", models.CharField(blank=True, max_length=1000)),
                (
                    "snapshot",
                    models.ManyToManyField(
                        related_name="events", to="reaktion.tracesnapshot"
                    ),
                ),
                (
                    "trace",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="reaktion.trace",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="RunSnapshot",
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
                (
                    "created_at",
                    models.DateTimeField(auto_created=True, auto_now_add=True),
                ),
                ("t", models.IntegerField()),
                ("status", models.CharField(blank=True, max_length=100, null=True)),
                (
                    "run",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="snapshots",
                        to="reaktion.run",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="RunEvent",
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
                (
                    "created_at",
                    models.DateTimeField(auto_created=True, auto_now_add=True),
                ),
                (
                    "kind",
                    django_choices_field.fields.TextChoicesField(
                        choices=[
                            ("NEXT", "NEXT (Value represent Item)"),
                            ("ERROR", "Error (Value represent Exception)"),
                            ("COMPLETE", "COMPLETE (Value is none)"),
                            ("UNKNOWN", "UNKNOWN (Should never be used)"),
                        ],
                        choices_enum=reaktion.enums.RunEventKindChoices,
                        default="NEXT",
                        help_text="The type of event",
                        max_length=1000,
                    ),
                ),
                ("t", models.IntegerField()),
                ("caused_by", models.JSONField(blank=True, default=list)),
                ("source", models.CharField(max_length=1000)),
                ("handle", models.CharField(max_length=1000)),
                ("value", models.JSONField(blank=True, null=True)),
                (
                    "run",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="reaktion.run",
                    ),
                ),
                (
                    "snapshot",
                    models.ManyToManyField(
                        related_name="events", to="reaktion.runsnapshot"
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="flow",
            name="workspace",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="flows",
                to="reaktion.workspace",
            ),
        ),
        migrations.AddConstraint(
            model_name="flow",
            constraint=models.UniqueConstraint(
                fields=("workspace", "hash"),
                name="Equal Reservation on this App by this Waiter is already in place",
            ),
        ),
    ]
