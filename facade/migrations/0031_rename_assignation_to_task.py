"""Rename the Assignation domain model family to Task.

The work-item formerly called an "assignation" is now a "task". These are RenameModel /
RenameField operations (NOT delete+create) so existing rows and FK columns are preserved:
``facade_assignation``→``facade_task``, ``facade_assignationevent``→``facade_taskevent``,
``facade_assignationinstruct``→``facade_taskinstruct``, and the ``assignation`` FK columns
(on TaskEvent, TaskInstruct, and Patch) → ``task``.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("facade", "0030_rename_event_kinds"),
    ]

    operations = [
        migrations.RenameModel(old_name="Assignation", new_name="Task"),
        migrations.RenameModel(old_name="AssignationEvent", new_name="TaskEvent"),
        migrations.RenameModel(old_name="AssignationInstruct", new_name="TaskInstruct"),
        migrations.RenameField(model_name="taskevent", old_name="assignation", new_name="task"),
        migrations.RenameField(model_name="taskinstruct", old_name="assignation", new_name="task"),
        migrations.RenameField(model_name="patch", old_name="assignation", new_name="task"),
    ]
