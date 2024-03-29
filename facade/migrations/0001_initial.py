# Generated by Django 4.2.4 on 2023-08-03 19:14

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_choices_field.fields
import facade.enums
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("authentikate", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Agent",
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
                    "installed_at",
                    models.DateTimeField(auto_created=True, auto_now_add=True),
                ),
                (
                    "name",
                    models.CharField(
                        default="Nana", help_text="This providers Name", max_length=2000
                    ),
                ),
                ("instance_id", models.CharField(default="main", max_length=1000)),
                (
                    "unique",
                    models.CharField(
                        default=uuid.uuid4,
                        help_text="The Channel we are listening to",
                        max_length=1000,
                    ),
                ),
                (
                    "on_instance",
                    models.CharField(
                        default="all",
                        help_text="The Instance this Agent is running on",
                        max_length=1000,
                    ),
                ),
                (
                    "status",
                    django_choices_field.fields.TextChoicesField(
                        choices=[
                            ("ACTIVE", "Active"),
                            ("KICKED", "Just kicked"),
                            ("DISCONNECTED", "Disconnected"),
                            (
                                "VANILLA",
                                "Complete Vanilla Scenario after a forced restart of",
                            ),
                        ],
                        choices_enum=facade.enums.AgentStatusChoices,
                        default="VANILLA",
                        help_text="The Status of this Agent",
                        max_length=1000,
                    ),
                ),
                (
                    "blocked",
                    models.BooleanField(
                        default=False,
                        help_text="If this Agent is blocked, it will not be used for provision, nor will it be able to provide",
                    ),
                ),
            ],
            options={
                "permissions": [("can_provide_on", "Can provide on this Agent")],
            },
        ),
        migrations.CreateModel(
            name="Collection",
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
                    "defined_at",
                    models.DateTimeField(auto_created=True, auto_now_add=True),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="The name of this Collection",
                        max_length=1000,
                        unique=True,
                    ),
                ),
                (
                    "description",
                    models.TextField(help_text="A description for the Collection"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Node",
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
                    "pure",
                    models.BooleanField(
                        default=False,
                        help_text="Is this function pure. e.g can we cache the result?",
                    ),
                ),
                (
                    "idempotent",
                    models.BooleanField(
                        default=False,
                        help_text="Is this function pure. e.g can we cache the result?",
                    ),
                ),
                (
                    "kind",
                    django_choices_field.fields.TextChoicesField(
                        choices=[("FUNCTION", "Function"), ("GENERATOR", "Generator")],
                        choices_enum=facade.enums.NodeKindChoices,
                        default="FUNCTION",
                        help_text="Function, generator? Check async Programming Textbook",
                        max_length=1000,
                    ),
                ),
                (
                    "interfaces",
                    models.JSONField(
                        default=list,
                        help_text="Intercae that we use to interpret the meta data",
                    ),
                ),
                (
                    "port_groups",
                    models.JSONField(
                        default=list,
                        help_text="Intercae that we use to interpret the meta data",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="The cleartext name of this Node", max_length=1000
                    ),
                ),
                (
                    "meta",
                    models.JSONField(
                        blank=True, help_text="Meta data about this Node", null=True
                    ),
                ),
                (
                    "description",
                    models.TextField(help_text="A description for the Node"),
                ),
                (
                    "scope",
                    models.CharField(
                        default="GLOBAL",
                        help_text="The scope of this Node. e.g. does the data it needs or produce live only in the scope of this Node or is it global or does it bridge data?",
                        max_length=1000,
                    ),
                ),
                (
                    "hash",
                    models.CharField(
                        help_text="The hash of the Node (completely unique)",
                        max_length=1000,
                        unique=True,
                    ),
                ),
                (
                    "args",
                    models.JSONField(default=list, help_text="Inputs for this Node"),
                ),
                (
                    "returns",
                    models.JSONField(default=list, help_text="Outputs for this Node"),
                ),
                (
                    "collections",
                    models.ManyToManyField(
                        help_text="The collections this Node belongs to",
                        related_name="nodes",
                        to="facade.collection",
                    ),
                ),
                (
                    "is_test_for",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The users that have pinned the position",
                        related_name="tests",
                        to="facade.node",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Protocol",
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
                    "name",
                    models.CharField(
                        help_text="The name of this Protocol",
                        max_length=1000,
                        unique=True,
                    ),
                ),
                (
                    "description",
                    models.TextField(help_text="A description for the Protocol"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Template",
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
                    "interface",
                    models.CharField(
                        help_text="Interface (think Function)", max_length=1000
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        default="Unnamed",
                        help_text="A name for this Template",
                        max_length=1000,
                    ),
                ),
                (
                    "extensions",
                    models.JSONField(
                        default=list,
                        help_text="The attached extensions for this Template",
                        max_length=2000,
                    ),
                ),
                (
                    "policy",
                    models.JSONField(
                        default=dict,
                        help_text="The attached policy for this template",
                        max_length=2000,
                    ),
                ),
                (
                    "params",
                    models.JSONField(
                        default=dict, help_text="Params for this Template"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "agent",
                    models.ForeignKey(
                        help_text="The associated registry for this Template",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="templates",
                        to="facade.agent",
                    ),
                ),
                (
                    "node",
                    models.ForeignKey(
                        help_text="The node this template is implementatig",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="templates",
                        to="facade.node",
                    ),
                ),
            ],
            options={
                "permissions": [("providable", "Can provide this template")],
            },
        ),
        migrations.CreateModel(
            name="Registry",
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
                    "app",
                    models.ForeignKey(
                        help_text="The Associated App",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="authentikate.app",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="The Associatsed User",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="node",
            name="protocols",
            field=models.ManyToManyField(
                blank=True,
                help_text="The protocols this Node implements (e.g. Predicate)",
                related_name="nodes",
                to="facade.protocol",
            ),
        ),
        migrations.AddField(
            model_name="agent",
            name="registry",
            field=models.ForeignKey(
                help_text="The provide might be limited to a instance like ImageJ belonging to a specific person. Is nullable for backend users",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="agents",
                to="facade.registry",
            ),
        ),
        migrations.AddConstraint(
            model_name="template",
            constraint=models.UniqueConstraint(
                fields=("interface", "agent"),
                name="A template has unique versions for every node it trys to implement",
            ),
        ),
        migrations.AddConstraint(
            model_name="registry",
            constraint=models.UniqueConstraint(
                fields=("app", "user"),
                name="No multiple Clients for same App and User allowed",
            ),
        ),
        migrations.AddConstraint(
            model_name="agent",
            constraint=models.UniqueConstraint(
                fields=("registry", "instance_id"),
                name="No multiple Agents for same App and User allowed on same identifier",
            ),
        ),
    ]
