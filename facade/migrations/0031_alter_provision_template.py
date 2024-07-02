# Generated by Django 4.2.4 on 2024-07-02 15:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("facade", "0030_alter_reservation_causing_assignation"),
    ]

    operations = [
        migrations.AlterField(
            model_name="provision",
            name="template",
            field=models.ForeignKey(
                blank=True,
                help_text="The Template for this Provision",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="provisions",
                to="facade.template",
            ),
        ),
    ]
