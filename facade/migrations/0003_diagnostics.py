"""Stored registration warnings.

``Implementation`` and ``Blok`` gain ``diagnostics``: the non-fatal findings of validating their
effect/validator/util calls against the base catalog plus the named UI catalog (an operation
neither provides is a warning, not a rejection). Pure schema change, no data step.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("facade", "0002_blok_registry")]

    operations = [
        migrations.AddField(
            model_name="implementation",
            name="diagnostics",
            field=models.JSONField(default=list, help_text="Non-fatal registration findings (rekuest_core Diagnostic), e.g. validator/effect calls naming operations that neither the base catalog nor the definition's catalog provides. Replaced on every registration."),
        ),
        migrations.AddField(
            model_name="blok",
            name="diagnostics",
            field=models.JSONField(default=list, help_text="Non-fatal registration findings (rekuest_core Diagnostic), e.g. manifest util calls naming operations that neither the base catalog nor this blok's catalog provides. Replaced on every write."),
        ),
    ]
