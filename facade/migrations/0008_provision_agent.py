# Generated by Django 4.2.4 on 2023-09-07 16:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0007_node_defined_at_alter_provisionevent_provision"),
    ]

    operations = [
        migrations.AddField(
            model_name="provision",
            name="agent",
            field=models.ForeignKey(
                default=1,
                help_text="The associated agent for this Provision",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="provisions",
                to="facade.agent",
            ),
            preserve_default=False,
        ),
    ]
