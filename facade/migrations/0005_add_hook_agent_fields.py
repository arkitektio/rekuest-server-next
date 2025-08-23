# Generated manually for hook agent fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facade', '0004_toolbox_client'),
    ]

    operations = [
        migrations.AddField(
            model_name='agent',
            name='is_hook_agent',
            field=models.BooleanField(default=False, help_text='If true, this is a hook agent that receives tasks via HTTP POST instead of WebSocket'),
        ),
        migrations.AddField(
            model_name='agent',
            name='hook_endpoint',
            field=models.URLField(blank=True, help_text='The HTTP endpoint to send task assignments to for hook agents', null=True),
        ),
        migrations.AddField(
            model_name='agent',
            name='hook_secret_token',
            field=models.CharField(blank=True, help_text='Secret token used to authenticate requests to hook agent endpoint', max_length=512, null=True),
        ),
    ]