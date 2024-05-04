# Generated by Django 4.2.4 on 2024-04-30 11:37

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0011_alter_dependency_node"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dependency",
            name="binds",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="The binds for this dependency (Determines which templates can be used for this dependency)",
                max_length=2000,
                null=True,
            ),
        ),
    ]
