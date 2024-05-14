from django.contrib import admin
from facade import models
# Register your models here.


admin.site.register(models.Node)
admin.site.register(models.HardwareRecord)
admin.site.register(models.Template)
admin.site.register(models.Reservation)
admin.site.register(models.Provision)
admin.site.register(models.Registry)
admin.site.register(models.Waiter)
admin.site.register(models.ProvisionEvent)
admin.site.register(models.AssignationEvent)
admin.site.register(models.Agent)
admin.site.register(models.Assignation)
