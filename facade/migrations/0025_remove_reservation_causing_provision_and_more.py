# Generated by Django 4.2.4 on 2024-06-23 11:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0024_alter_agent_last_seen"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="reservation",
            name="causing_provision",
        ),
        migrations.RemoveField(
            model_name="reservation",
            name="happy",
        ),
        migrations.RemoveField(
            model_name="reservation",
            name="viable",
        ),
        migrations.AddField(
            model_name="agent",
            name="health_check_interval",
            field=models.IntegerField(
                default=300,
                help_text="How often should this agent be checked for its health. Defaults to 5 mins",
            ),
        ),
        migrations.AddField(
            model_name="assignation",
            name="hooks",
            field=models.JSONField(
                default=list,
                help_text="hooks that are tight to the lifecycle of this assignation",
            ),
        ),
        migrations.AddField(
            model_name="assignation",
            name="interfaces",
            field=models.JSONField(
                default=list,
                help_text="Which interfaces does this fullfill (e.g. is this on the fly download? This is dynamic and can change from app to app)",
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="causing_assignation",
            field=models.ForeignKey(
                default=1,
                help_text="The assignation that created this reservation",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="caused_reservations",
                to="facade.assignation",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="reservation",
            name="saved_args",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="template",
            name="dynamic",
            field=models.BooleanField(
                default=True,
                help_text="Dynamic Templates will be able to create new reservations on runtime",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="testresult",
            name="assignation",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="test_result",
                to="facade.assignation",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="assignation",
            name="args",
            field=models.JSONField(
                blank=True, default=dict, help_text="The Args", null=True
            ),
        ),
        migrations.AlterField(
            model_name="assignation",
            name="provision",
            field=models.ForeignKey(
                blank=True,
                help_text="Which Provision did we end up being assigned to (will be set after a bound)",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="assignations",
                to="facade.provision",
            ),
        ),
    ]
