"""State definition hashes are unique per organization.

``StateDefinition.hash`` was globally unique while ``_register_state`` upserts on
``(hash, organization)``: the second organization registering the same port list hit an
IntegrityError. Pure schema change.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Replace the global unique on ``hash`` with ``(organization, hash)``."""

    dependencies = [("facade", "0004_uicatalog_widget_defaults")]

    operations = [
        migrations.AlterField(
            model_name="statedefinition",
            name="hash",
            field=models.CharField(help_text="sha256 over the ports; unique per organization", max_length=2000),
        ),
        migrations.AddConstraint(
            model_name="statedefinition",
            constraint=models.UniqueConstraint(fields=("organization", "hash"), name="unique_state_definition_hash_per_organization"),
        ),
    ]
