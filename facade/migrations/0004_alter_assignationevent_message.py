# Generated by Django 4.2.4 on 2024-11-11 13:11

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0003_agent_pinned_by_node_pinned_by_template_pinned_by"),
    ]

    operations = [
        migrations.AlterField(
            model_name="assignationevent",
            name="message",
            field=models.CharField(blank=True, max_length=30000, null=True),
        ),
    ]
