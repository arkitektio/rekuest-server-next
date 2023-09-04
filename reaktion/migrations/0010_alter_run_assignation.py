# Generated by Django 4.2.4 on 2023-09-03 11:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0007_node_defined_at_alter_provisionevent_provision"),
        ("reaktion", "0009_alter_trace_flow_alter_trace_provision"),
    ]

    operations = [
        migrations.AlterField(
            model_name="run",
            name="assignation",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="run",
                to="facade.assignation",
            ),
        ),
    ]