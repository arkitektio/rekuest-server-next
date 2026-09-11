"""Per-catalog default widgets.

``UICatalog.widget_defaults`` lets a UI app declare which widget to render for ports of a kind
and/or structure identifier that declare no widget themselves. Pure schema change.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Add ``UICatalog.widget_defaults``."""

    dependencies = [("facade", "0003_diagnostics")]

    operations = [
        migrations.AddField(
            model_name="uicatalog",
            name="widget_defaults",
            field=models.JSONField(default=list, help_text="Default widgets per port kind and/or structure identifier (rekuest_core WidgetDefault), applied by the UI to ports that declare no widget."),
        ),
    ]
