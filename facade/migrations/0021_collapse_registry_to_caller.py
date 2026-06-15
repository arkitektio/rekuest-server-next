"""Decouple Agent from Registry and rename Registry -> Caller.

`Registry` was the (client, user, organization) identity that *requests* work, but `Agent`
1:1-depended on it and duplicated user/organization. This migration renames the model to
`Caller` (its real role), gives `Agent` its own `client` FK so it stands alone, drops
`Agent.registry`, and renames the `registry` FK -> `caller` on the assignation/reservation
models that record the requestor.

Order matters: backfill `Agent.client` from the (still-present) `agent.registry.client` before
dropping `Agent.registry`.
"""

import django.db.models.deletion
from django.db import migrations, models


def backfill_agent_client(apps, schema_editor):
    Agent = apps.get_model("facade", "Agent")
    for agent in Agent.objects.exclude(registry__isnull=True).select_related("registry"):
        agent.client_id = agent.registry.client_id
        agent.save(update_fields=["client"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0020_remove_implementation_extensions"),
        ("authentikate", "0005_alter_client_client_id"),
    ]

    operations = [
        # 1. Rename the model (DB table + every FK target follows automatically).
        migrations.RenameModel(old_name="Registry", new_name="Caller"),
        # 2. Rename the requestor FK on the records that store it.
        migrations.RenameField(model_name="assignation", old_name="registry", new_name="caller"),
        migrations.RenameField(model_name="assignationinstruct", old_name="registry", new_name="caller"),
        migrations.RenameField(model_name="reservation", old_name="registry", new_name="caller"),
        # 3. Give Agent its own client identity (nullable first so we can backfill).
        migrations.AddField(
            model_name="agent",
            name="client",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="agents",
                to="authentikate.client",
                help_text="The client (app instance) this Agent runs as",
            ),
        ),
        migrations.RunPython(backfill_agent_client, noop_reverse),
        # 4. Drop the old 1:1 registry link + its unique constraint.
        migrations.RemoveConstraint(model_name="agent", name="one_agent_per_registry"),
        migrations.RemoveField(model_name="agent", name="registry"),
        # 5. Lock the new identity in.
        migrations.AlterField(
            model_name="agent",
            name="client",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="agents",
                to="authentikate.client",
                help_text="The client (app instance) this Agent runs as",
            ),
        ),
        migrations.AddConstraint(
            model_name="agent",
            constraint=models.UniqueConstraint(
                fields=["client", "user", "organization"],
                name="one_agent_per_client_user_organization",
            ),
        ),
    ]
